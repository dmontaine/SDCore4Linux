#!/usr/bin/env python3
#
# sandbox-apispin.py - S.71, 20 Oct 26: an API client that closes its connection (or declares a packet it will never send) must not
#                      leave the server process running at 100% of a processor.  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-apispin.py <dir> [--build] [--only=A,B,C,K,D,E] [--mutants]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or absent).
# Exit 0 every row passed, 1 a row failed, 2 it could not run.  --only runs the parts named.  --mutants adds part M, which takes one
# part of the repair at a time out of the SANDBOX'S OWN copy of the source (never the tree), rebuilds its sd, and requires the rows
# of that part to FAIL (about 4 minutes more).  It is not in the default run, which regress.sh makes.
#
# START-HISTORY:
# 20 Oct 26 dm  Written for S.71.  The defect, measured on the Debian 13 VM `sdsrv` 19-20 Oct: a client that finishes the TLS 1.3
#               handshake and closes leaves `sd -n -q` (root, before any login) polling at 100% of a processor about half the time.
# END-HISTORY
#
# THE INSTRUMENT.  Parts A and B start `sd -n -q` as sdclient@.service does (descriptors 0, 1 and 2 the accepted connection) in the
# sandbox, so the REAL relay (sd_tlssrv.c) does a REAL TLS 1.3 handshake with Python's ssl, and the process under test is the real API
# server, apisrvr, behind it.  What a row looks at is the server's own process family (/proc: its session id): is anything of it
# still there N seconds after the client has gone, and how many CPU ticks did the survivor use in one second (100 is a whole
# processor).  Parts C and K talk the API's own framing (a 4-byte length that counts itself, a 2-byte request, the body) to a
# `sd -Q -C` server over pipes, as the client library does.  Part D uses the sandbox's own sdclilib.so with a real local session (the
# legitimate use, which must not be harmed).  Part E compiles the length test (gplsrc/apipkt.h) in a small C program, because a
# sandbox cannot run as root and the 64 KB limit before login applies to a root process (the VM witness runs that for real).
#
#   A  controls: the null case (the instrument must have SEEN a server process alive; if it never did, exit 2), a client that stays
#      connected leaves an idle, alive server, which ends when the client closes
#   B  the defect: a TLS client that closes at once (hard, or with close_notify), one that sends a newline and closes, one that sends
#      four bytes that read as a huge length (past the limit, then one under it) and closes: the server process ends within 6 s and
#      does not spin.  The race is in the
#      server's own start-up and the window is under 5 ms on a fast machine, so the close follows the handshake with nothing between
#   C  a declared length the server cannot accept (below the header, negative, 2 GB, 'garb', one past the largest string) is refused
#      with the client still connected: the server ends the session at once, where it used to wait for bytes that will not come;
#      the same for the second reader (the reply to an INPUT prompt)
#   K  CLEARINPUT after the connection has gone ends the session (the loop that used to turn for ever)
#   D  legitimate large packets still work: a 20 MB record written and read back through a real local session; a prompt answered
#   E  the length test, boundary by boundary, for a process before login (64 KB) and after it (the largest string + 10)
#   M  (--mutants) keyin: the lost connection is no longer final; readsock: read_socket ignores what keyin says; limit1 and limit2:
#      the length test of op_readpkt / of the reply to a prompt is off; keyready: CLEARINPUT's test is off.  Each must fail its rows.

import ctypes
import importlib.util
import os
import re
import select
import shutil
import signal
import socket
import ssl
import struct
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("q3", os.path.join(HERE, "sandbox-stmt-q3.py"))
q3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q3)
say, has, tag, put = q3.say, q3.has, q3.tag, q3.put

MAX_STRING_SIZE = 1073741822          # sddefs.h; part E checks that apipkt.h agrees
PROMPT = 5                            # SV_PROMPT
RESPOND = 22                          # SrvrRespond

USER_PROGS = {
    # a command that waits for input (part C's second reader, part D's prompt)
    "zzprmp": "   input x\n   crt 'GOT[':x:']'\nend\n",
    # part K: waits in a shell (while one runs the input signal is not acted on), then clears the input: if the client has gone,
    # CLEARINPUT is the first thing to find it out
    "zzclr": "   execute 'SH sleep 2'\n   clearinput\n   crt 'CLEARED'\nend\n",
}

BOX = SYS = SD = None
REC = None            # part M: a list that collects the rows instead of printing them


def row(name, ok, detail=""):
    if REC is not None:
        REC.append((name, ok, detail))
    else:
        q3.row(name, ok, detail)


def env():
    e = dict(os.environ, SD_CONFIG=os.path.join(BOX, "sd.conf"))
    e.pop("SSH_CONNECTION", None)
    e.pop("SSH_TTY", None)
    return e


# ---------------------------------------------------------------------------------------------------------------------
# What a process family is doing.  The family is every process in the server's session (it is started as a session leader; the TLS
# relay it forks is in it).

def read_stat(pid):
    try:
        with open("/proc/%d/stat" % pid) as f:
            s = f.read()
        rest = s[s.rindex(")") + 2:].split()
        return {"state": rest[0], "sid": int(rest[3]), "ticks": int(rest[11]) + int(rest[12]),
                "rss": int(rest[21]) * os.sysconf("SC_PAGE_SIZE") // 1024}
    except (OSError, ValueError, IndexError):
        return None


def family(sid):
    """{pid: stat} of every live (not zombie) process of the session."""
    out = {}
    for d in os.listdir("/proc"):
        if d.isdigit():
            st = read_stat(int(d))
            if st is not None and st["sid"] == sid and st["state"] != "Z":
                out[int(d)] = st
    return out


class Watch:
    """Poll a server family every 0.1 s until it is gone or `seconds` have passed."""

    def __init__(self, srv, seconds):
        self.ended = False
        self.saw_alive = False
        self.secs = None
        self.peak_ticks = 0           # the most CPU ticks any one process of the family had used
        self.peak_rss = 0
        self.spin = 0                 # CPU ticks used in the last second by the busiest survivor (when it did not end)
        t0 = time.time()
        while time.time() - t0 < seconds:
            srv.reap()
            fam = family(srv.sid)
            self.saw_alive = self.saw_alive or bool(fam)
            for st in fam.values():
                self.peak_ticks = max(self.peak_ticks, st["ticks"])
                self.peak_rss = max(self.peak_rss, st["rss"])
            if not fam:
                self.ended = True
                self.secs = round(time.time() - t0, 2)
                return
            time.sleep(0.1)
        before = family(srv.sid)
        time.sleep(1.0)
        after = family(srv.sid)
        for pid, st in after.items():
            self.spin = max(self.spin, st["ticks"] - before.get(pid, st)["ticks"])
            self.peak_rss = max(self.peak_rss, st["rss"])
        self.ended = not after
        if self.ended:
            self.secs = seconds

    def text(self):
        return "ended" if self.ended else "SURVIVED (%d ticks of CPU in 1 s, %d KB)" % (self.spin, self.peak_rss)


SEEN_ALIVE = [0]          # the null case: server processes the instrument has seen alive


class Srv:
    """A server process, in a session of its own."""

    def __init__(self, argv, **kw):
        self.p = subprocess.Popen(argv, start_new_session=True, env=env(), cwd=SYS, **kw)
        self.sid = self.p.pid

    def reap(self):
        self.p.poll()

    def kill(self):
        """Ends the family: SIGHUP first (a graceful end, so that the sandbox's user table is not left with a dead slot), then KILL."""
        for sig, wait in ((signal.SIGHUP, 2.0), (signal.SIGKILL, 2.0)):
            fam = family(self.sid)
            if not fam:
                break
            for pid in fam:
                try:
                    os.kill(pid, sig)
                except OSError:
                    pass
            t0 = time.time()
            while time.time() - t0 < wait and family(self.sid):
                self.reap()
                time.sleep(0.1)
        self.reap()


def cleanup_users():
    """A process that was killed keeps its user slot; sd -cleanup frees them."""
    subprocess.run([SD, "-cleanup"], env=env(), capture_output=True, timeout=60)


def watch_and_end(srv, seconds, was_alive=None):
    """Watch the family; a survivor is ended (and counted for the null case).  Returns the Watch.  `was_alive` is whether the server
    process was running when the client acted (a server that ends at once may be gone before the first scan of /proc finishes, which
    takes some milliseconds, so the Watch alone cannot always say it was ever there)."""
    if was_alive is None:
        was_alive = srv.p.poll() is None
    w = Watch(srv, seconds)
    w.saw_alive = w.saw_alive or was_alive
    if w.saw_alive:
        SEEN_ALIVE[0] += 1
    if not w.ended:
        srv.kill()
    return w


# ---------------------------------------------------------------------------------------------------------------------
# Parts A and B: the TLS path, as the socket-activated service runs it.

def tls_context():
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    return ctx


def tls_server():
    """Accept one connection as the socket activator does and start `sd -n -q` on it; returns (Srv, the client's TLS socket, why not)."""
    os.makedirs(os.path.join(BOX, "sd-tls"), mode=0o700, exist_ok=True)
    lst = socket.socket()
    lst.bind(("127.0.0.1", 0))
    lst.listen(4)
    cli = socket.create_connection(lst.getsockname())
    conn, _ = lst.accept()
    lst.close()
    srv = Srv([SD, "-n", "-q"], stdin=conn, stdout=conn, stderr=conn)
    conn.close()
    cli.settimeout(20)
    try:
        tls = tls_context().wrap_socket(cli)
    except (ssl.SSLError, OSError) as e:
        srv.kill()
        cli.close()
        return srv, None, str(e)
    return srv, tls, ""


def close_tls(tls, notify):
    try:
        if notify:
            tls.settimeout(2)
            tls.unwrap()
    except (ssl.SSLError, OSError, ValueError):
        pass
    try:
        tls.close()
    except OSError:
        pass


def tls_trial(shape, notify, seconds):
    """One client: handshake, then `shape`, then close.  Returns the Watch of the server family (a survivor is ended afterwards)."""
    srv, tls, why = tls_server()
    if tls is None:
        return None, why
    # NOTHING between the handshake and the close that takes time: the server's own start-up races the close, and on a fast machine
    # the window is shorter than 5 ms (measured: a close 5 ms later never left a process, one at once did 3 times in 3).
    if shape == "newline":
        tls.sendall(b"\n")
    elif shape == "garb":
        tls.sendall(b"garb")
    elif shape == "big":
        tls.sendall(struct.pack("<I", 1000000000))      # under the limit (a 1 GB record is allowed), so it is read for: and never sent
    elif shape == "idle1":
        time.sleep(1)
    was_alive = srv.p.poll() is None
    close_tls(tls, notify)
    return watch_and_end(srv, seconds, was_alive), ""


def part_a():
    say("\n--- A. controls: the instrument sees a healthy server ---------------------------------------------------------")
    srv, tls, why = tls_server()
    row("A0: a TLS 1.3 client completes the handshake with the real relay of a real `sd -n -q`", tls is not None, why)
    if tls is None:
        q3.bail("no TLS handshake with the sandbox's server (%s); nothing below can run" % why)
    time.sleep(2)
    fam1 = family(srv.sid)
    if fam1:
        SEEN_ALIVE[0] += 1
    t1 = {p: s["ticks"] for p, s in fam1.items()}
    time.sleep(2)
    fam2 = family(srv.sid)
    used = max([s["ticks"] - t1.get(p, s["ticks"]) for p, s in fam2.items()] or [0])
    row("A1: a client that stays connected and says nothing: its server is alive and idle (at most 10 ticks of CPU in 2 s)",
        bool(fam2) and used <= 10, "alive %s, %d ticks in 2 s" % (bool(fam2), used))
    close_tls(tls, True)
    w = watch_and_end(srv, 8)
    row("A2: ... and when that client then closes (the server has long since started) the server ends within 8 s", w.ended, w.text())
    cleanup_users()


B_PLAN = [("B1", "silent", 16, 6.0), ("B2", "newline", 8, 6.0), ("B3", "garb", 4, 6.0), ("B5", "big", 4, 6.0), ("B4", "idle1", 3, 6.0)]


def part_b(plan=None, quiet_head=False):
    if not quiet_head:
        say("\n--- B. the defect: a client closes at once ---------------------------------------------------------------------")
    for label, shape, n, secs in plan or B_PLAN:
        alive = []
        seen = 0
        peak = 0
        for i in range(n):
            w, why = tls_trial(shape, notify=(i >= n * 5 // 8), seconds=secs)
            if w is None:
                row("%s: trial %d, the handshake" % (label, i), False, why)
                continue
            seen += 1 if w.saw_alive else 0
            peak = max(peak, w.peak_rss)
            if not w.ended:
                alive.append("trial %d: %s" % (i, w.text()))
        cleanup_users()
        what = {"silent": "completes the TLS handshake and closes at once (%d trials, the last %d with a close_notify first)" % (n, n - n * 5 // 8),
                "newline": "completes the handshake, sends a newline and closes (%d trials)" % n,
                "garb": "sends the four bytes 'garb' (read as a length of 1,651,663,207) and closes (%d trials)" % n,
                "big": "sends a length of 1,000,000,000 (under the limit, so the server reads for it) and no more, and closes (%d trials)" % n,
                "idle1": "completes the handshake, waits 1 s and closes (%d trials; the control that always passed)" % n}[shape]
        # the memory: a server that reads for a length it was given allocates as it goes, and a loop that does not wait does it fast
        # (a process that ignored the lost connection read zeros at 250 MB/s); a normal one stays under 20 MB
        row("%s: a client that %s: every server process ends within %d s, none is left spinning, none grows past 200 MB" % (label, what, int(secs)),
            not alive and seen > 0 and peak < 200000,
            "; ".join(alive[:3]) + (" ... %d of %d left a process" % (len(alive), n) if alive else "") +
            ("" if seen else "no trial saw the server process: the instrument saw nothing") + ("; peak %d KB" % peak if peak >= 200000 else ""))


# ---------------------------------------------------------------------------------------------------------------------
# Parts C and K: the API framing over pipes (sd -Q -C, the local transport of sdclilib.c)

class PipeSrv(Srv):
    def __init__(self):
        rx_r, rx_w = os.pipe()     # server -> client
        tx_r, tx_w = os.pipe()     # client -> server
        Srv.__init__(self, [SD, "-Q", "-C%d!%d" % (rx_w, tx_r)], pass_fds=(rx_w, tx_r),
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.close(rx_w)
        os.close(tx_r)
        self.r, self.w = rx_r, tx_w

    def send(self, action, body=b""):
        self.send_raw(struct.pack("<IH", 6 + len(body), action) + body)

    def send_raw(self, data):
        try:
            os.write(self.w, data)
        except OSError:
            pass

    def recv(self, seconds=15):
        """One reply: (server_error, status, data) or None when none comes."""
        buf = b""
        end = time.time() + seconds
        need = 10
        while len(buf) < need and time.time() < end:
            if select.select([self.r], [], [], 0.2)[0]:
                chunk = os.read(self.r, need - len(buf))
                if not chunk:
                    return None
                buf += chunk
                if len(buf) >= 4:
                    need = struct.unpack("<I", buf[:4])[0]
        if len(buf) < need or need < 10:
            return None
        err, status = struct.unpack("<hi", buf[4:10])
        return err, status, buf[10:]

    def close(self):
        for fd in (self.r, self.w):
            try:
                os.close(fd)
            except OSError:
                pass


def pipe_login(account=b"zzaa"):
    """A pipe server logged in (the local login) and in an account; None if it did not get that far."""
    srv = PipeSrv()
    srv.send(25)
    a = srv.recv()
    srv.send(3, account)
    b = srv.recv()
    if a is None or b is None or a[0] != 0 or b[0] != 0:
        srv.kill()
        srv.close()
        return None
    SEEN_ALIVE[0] += 1
    return srv


C1_CASES = [("0", struct.pack("<I", 0)), ("3, below the header", struct.pack("<I", 3)), ("5, one below the header", struct.pack("<I", 5)),
            ("-1", struct.pack("<i", -1)), ("-2^31", struct.pack("<i", -2 ** 31)), ("2^31-1", struct.pack("<I", 2 ** 31 - 1)),
            ("'garb' = 1,651,663,207", b"garb"), ("largest string + 11", struct.pack("<I", MAX_STRING_SIZE + 11))]
# this reader takes the whole 6-byte header, length and function (SrvrRespond), before it looks at the length
C2_CASES = [("'garb' = 1,651,663,207", b"garb" + struct.pack("<H", RESPOND)),
            ("5, below the header", struct.pack("<I", 5) + struct.pack("<H", RESPOND))]


def part_c1(cases=None, secs=6.0):
    for name, raw in cases or C1_CASES:
        srv = PipeSrv()
        time.sleep(0.5)            # let it start and wait for its first request
        was_alive = srv.p.poll() is None
        srv.send_raw(raw)
        w = watch_and_end(srv, secs, was_alive)
        srv.close()
        cleanup_users()
        row("C1: a first packet that declares %s: the server refuses it and ends the session (client still connected)" % name,
            w.ended and w.saw_alive and w.peak_rss < 200000, w.text() + ", peak %d KB" % w.peak_rss)


def part_c2(cases=None, secs=6.0):
    for name, raw in cases or C2_CASES:
        srv = pipe_login()
        if srv is None:
            row("C2: the pipe server logs in (local login, account zzaa)", False, "no login")
            continue
        srv.send(21, b"RUN bp zzprmp")
        rp = srv.recv()
        prompted = rp is not None and rp[0] == PROMPT
        srv.send_raw(raw)
        w = watch_and_end(srv, secs)
        srv.close()
        cleanup_users()
        row("C2: the reply to an INPUT prompt declares %s: the server refuses it and ends the session" % name,
            prompted and w.ended, "prompted %s, %s" % (prompted, w.text()))


def part_c():
    say("\n--- C. a declared length the server cannot accept, the client still connected --------------------------------")
    part_c1()
    part_c2()


def part_k(secs=8.0):
    """The command waits in SH sleep (while a shell runs the input signal is not acted on), the client goes, and CLEARINPUT is then the
    first thing to find the connection gone: while keyready() said something was waiting (a hung-up descriptor is always readable) and
    keyin() gave back a character, CLEARINPUT turned for ever."""
    if REC is None:
        say("\n--- K. CLEARINPUT after the connection has gone ---------------------------------------------------------------")
        srv = pipe_login(b"zzsh")
        if srv is None:
            row("K0: the pipe server logs in to the account that holds the SH gate", False, "no login")
        else:
            srv.send(21, b"RUN bp zzclr")
            rp = srv.recv(20)
            row("K0: CONTROL: with the client still connected the command runs through (SH sleep 2, CLEARINPUT) and says CLEARED",
                rp is not None and b"CLEARED" in rp[2], repr(rp)[:120])
            srv.send(1)
            watch_and_end(srv, 6)
            srv.close()
            cleanup_users()
    srv = pipe_login(b"zzsh")
    if srv is None:
        row("K1: the pipe server logs in to the account that holds the SH gate", False, "no login")
        return
    srv.send(21, b"RUN bp zzclr")
    time.sleep(0.7)            # the command is in SH sleep 2
    srv.close()                # the client goes
    w = watch_and_end(srv, secs)
    cleanup_users()
    row("K1: the client closes while the command waits in SH sleep; CLEARINPUT then runs: the server ends within %d s and does not spin"
        % int(secs), w.ended and w.saw_alive, w.text())


# ---------------------------------------------------------------------------------------------------------------------
# Part D: a real local session

def part_d():
    say("\n--- D. legitimate use is not harmed ----------------------------------------------------------------------------")
    os.environ["SD_CONFIG"] = os.path.join(BOX, "sd.conf")
    lib = ctypes.CDLL(os.path.join(SYS, "bin", "sdclilib.so"))
    for fn in ("SDRead", "SDExecute", "SDRespond"):
        getattr(lib, fn).restype = ctypes.c_void_p
    lib.SDOpen.restype = ctypes.c_int
    lib.SDConnectLocal.restype = ctypes.c_int

    def text(ptr):
        if not ptr:
            return None
        b = ctypes.string_at(ptr)
        lib.SDFree(ctypes.c_void_p(ptr))
        return b

    ok = lib.SDConnectLocal(b"zzaa")
    row("D0: a real local API session connects (sdclilib.so, SDConnectLocal)", ok == 1, str(ok))
    if ok != 1:
        q3.bail("no API session; the rest of part D cannot run")
    fno = lib.SDOpen(b"zzcl")
    big = (b"0123456789abcdef" * 64 + b"\xfe") * 20480        # 20 MB
    e = ctypes.c_int(-1)
    lib.SDWrite(fno, b"big", big)            # a C string: the record has no NUL in it
    back = text(lib.SDRead(fno, b"big", ctypes.byref(e)))
    row("D1: a record of %d bytes (20 MB) is written and read back through the local API, byte for byte" % len(big),
        back == big, "got %s bytes" % (len(back) if back is not None else None))
    perr = ctypes.c_int(-1)
    lib.SDExecute(b"RUN bp zzprmp", ctypes.byref(perr))
    rerr = ctypes.c_int(-1)
    out = text(lib.SDRespond(b"hello", ctypes.byref(rerr)))
    row("D2: an INPUT prompt is answered: the server asks (status %d) and the reply reaches the command" % perr.value,
        perr.value == PROMPT and out is not None and b"GOT[hello]" in out, "%r, %r" % (perr.value, out))
    lib.SDDisconnect()
    time.sleep(1)
    cleanup_users()


# ---------------------------------------------------------------------------------------------------------------------
# Part E: apipkt.h

E_C = r'''
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include "apipkt.h"
int main(int argc, char **argv) {
  int i;
  printf("CONST %d %d %d\n", API_PKT_HDR_BYTES, API_PKT_MAX_PRELOGIN, API_PKT_MAX_STRING);
  for (i = 1; i + 1 < argc; i += 2) {
    long long v = atoll(argv[i]);
    printf("ROW %lld %d %d\n", v, atoi(argv[i + 1]), api_packet_length_ok((int32_t)v, atoi(argv[i + 1])));
  }
  return 0;
}
'''


def part_e():
    """apipkt.h's test, compiled apart and put through the boundaries, against an oracle written here from the numbers the rules give."""
    say("\n--- E. the length test, boundary by boundary (gplsrc/apipkt.h) ------------------------------------------------")
    gpl = os.path.join(BOX, "tree", "gplsrc")
    if not os.path.isfile(os.path.join(gpl, "apipkt.h")):
        row("E0: gplsrc/apipkt.h exists and compiles in a small C program", False, "%s/apipkt.h is not there" % gpl)
        return
    tmp = tempfile.mkdtemp(prefix="apispin-e.")
    try:
        with open(os.path.join(tmp, "e.c"), "w") as f:
            f.write(E_C)
        cc = subprocess.run(["gcc", "-std=gnu17", "-Wall", "-Wextra", "-Werror", "-I" + gpl, "-o", os.path.join(tmp, "e"),
                             os.path.join(tmp, "e.c")], capture_output=True, text=True)
        row("E0: gplsrc/apipkt.h compiles in a small C program with -Wall -Wextra -Werror", cc.returncode == 0, (cc.stdout + cc.stderr)[-300:])
        if cc.returncode != 0:
            return
        values = [-2 ** 31, -1, 0, 3, 5, 6, 7, 100, 65535, 65536, 65537, 1000000, MAX_STRING_SIZE + 9, MAX_STRING_SIZE + 10,
                  MAX_STRING_SIZE + 11, 2 ** 31 - 1]
        argv = []
        for v in values:
            argv += [str(v), "0", str(v), "1"]
        out = subprocess.run([os.path.join(tmp, "e")] + argv, capture_output=True, text=True).stdout
        const = re.search(r"^CONST (\d+) (\d+) (\d+)$", out, re.M)
        rows = re.findall(r"^ROW (-?\d+) (\d) (\d)$", out, re.M)
        row("E1: the constants: a 6-byte header (4 for the length that counts itself, 2 for the request), 65,536 before login, "
            "the largest string after",
            const is not None and tuple(int(x) for x in const.groups()) == (6, 65536, MAX_STRING_SIZE), repr(const and const.groups()))
        with open(os.path.join(gpl, "sddefs.h")) as f:
            m = re.search(r"#define\s+MAX_STRING_SIZE\s+(\d+)", f.read())
        row("E2: ... and MAX_STRING_SIZE in sddefs.h is the number this suite's oracle uses (so the limit follows the string maximum)",
            m is not None and int(m.group(1)) == MAX_STRING_SIZE, repr(m and m.group(1)))
        bad = []
        for v, pre, got in rows:
            v, pre, got = int(v), int(pre), int(got)
            want = int(6 <= v <= (65536 if pre else MAX_STRING_SIZE + 10))
            if got != want:
                bad.append("%d %s: %d, wanted %d" % (v, "before login" if pre else "after login", got, want))
        row("E3: %d boundary cases, before login and after it (below 6, 6, 65,536, 65,537, the largest string + 10 and + 11, negative, 2^31-1) "
            "all as the rules say" % len(rows), len(rows) == 2 * len(values) and not bad, "; ".join(bad[:4]) or "only %d rows" % len(rows))
        with open(os.path.join(gpl, "op_tio.c"), encoding="utf-8", errors="replace") as f:
            tio = f.read()
        n_calls = len(re.findall(r"api_packet_length_ok\(", tio))
        n_root = len(re.findall(r"is_sdApiSrvr\s*&&\s*\(?geteuid\(\)\s*==\s*0", tio))
        row("E4: SOURCE CHECK, not a run (a sandbox cannot be root): op_tio.c asks the test in both packet readers, and the 'before login' "
            "argument is a root API server (is_sdApiSrvr && geteuid() == 0), which the VM witness runs for real",
            n_calls >= 2 and n_root >= 1, "%d calls, %d root tests" % (n_calls, n_root))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------------------------------------------------
# Part M: the mutants.  Each is one exact text of the sandbox's own copy of the source, taken out; the sandbox's sd is rebuilt from it,
# the rows of the part it breaks are run again, and at least one of them must fail.

MUTANTS = [
    # name, file, old text (must be there exactly once), new text, what is run, the label its rows must fail under, what it takes out
    ("keyin", "linuxio.c",
     "      if (connection_lost) {\n        k_exit_cause = K_TERMINATE;\n        input_handler_enabled = TRUE;\n        return 0;\n      }\n", "",
     lambda: part_b([("B1", "silent", 10, 4.0)], True), "B1", "keyin() no longer treats a lost connection as final"),
    ("readsock", "linuxio.c",
     "    if ((c < 0) || ((c == 0) && (k_exit_cause & K_INTERRUPT))) {", "    if (0) {",
     lambda: part_b([("B5", "big", 2, 4.0)], True), "B5", "read_socket() ignores what keyin() says again"),
    ("limit1", "op_tio.c",
     "  if (!api_packet_length_ok(packet_bytes, is_sdApiSrvr && (geteuid() == 0))) {\n    api_packet_refused(packet_bytes);\n    goto exit_op_readpkt;",
     "  if (0) {\n    api_packet_refused(packet_bytes);\n    goto exit_op_readpkt;",
     lambda: part_c1([C1_CASES[2], C1_CASES[4], C1_CASES[6]], 4.0), "C1", "op_readpkt() believes any declared length"),
    ("limit2", "op_tio.c",
     "  if (!api_packet_length_ok(packet_bytes, is_sdApiSrvr && (geteuid() == 0))) {\n    api_packet_refused(packet_bytes);\n    k_exit_cause = K_TERMINATE;",
     "  if (0) {\n    api_packet_refused(packet_bytes);\n    k_exit_cause = K_TERMINATE;",
     lambda: part_c2(None, 4.0), "C2", "the reader of the reply to a prompt believes any declared length"),
    ("keyready", "linuxio.c",
     "  if (connection_lost && (ring_in == ring_out)) {\n    k_exit_cause = K_TERMINATE;\n    return FALSE;\n  }\n", "",
     lambda: part_k(5.0), "K1", "keyready() says there is something to read on a connection that has gone"),
]


def swap_sd(new_binary):
    """Stop the sandbox, put the binary in place (renamed over, not written into a running file), start it."""
    subprocess.run([sys.executable, q3.TOOL, BOX, "stop"], capture_output=True, text=True, errors="replace", timeout=120)
    tmp = SD + ".new"
    shutil.copy2(new_binary, tmp)
    os.replace(tmp, SD)
    subprocess.run([sys.executable, q3.TOOL, BOX, "start"], capture_output=True, text=True, errors="replace", timeout=180)


def part_m():
    global REC
    say("\n--- M. the mutants: each part of the repair taken out of the sandbox's own copy, and its rows must fail ------------")
    tree = os.path.join(BOX, "tree")
    good = SD + ".apispin-good"
    shutil.copy2(SD, good)
    try:
        for name, fname, old, new, run, label, what in MUTANTS:
            path = os.path.join(tree, "gplsrc", fname)
            with open(path, encoding="utf-8", errors="replace") as f:
                src = f.read()
            if src.count(old) != 1:
                row("M-%s: the text to take out is in %s exactly once" % (name, fname), False, "found %d times" % src.count(old))
                continue
            with open(path, "w", encoding="utf-8") as f:
                f.write(src.replace(old, new))
            try:
                mk = subprocess.run(["make"], cwd=tree, capture_output=True, text=True, errors="replace", timeout=600)
                if mk.returncode != 0:
                    row("M-%s: the mutant builds" % name, False, (mk.stdout + mk.stderr)[-300:])
                    continue
                swap_sd(os.path.join(tree, "bin", "sd"))
                REC = []
                try:
                    run()
                finally:
                    got, REC = REC, None
                failed = [n for n, ok, d in got if not ok and n.startswith(label)]
                row("M-%s: %s: its %s rows FAIL (%d of %d)" % (name, what, label, len(failed), len([1 for n, ok, d in got if n.startswith(label)])),
                    bool(failed), "no row of %s failed: %s" % (label, "; ".join(n[:60] for n, ok, d in got)))
            finally:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(src)
                cleanup_users()
    finally:
        REC = None
        subprocess.run([sys.executable, q3.TOOL, BOX, "stop"], capture_output=True, text=True, errors="replace", timeout=120)
        os.replace(good, SD)
        subprocess.run([sys.executable, q3.TOOL, BOX, "start"], capture_output=True, text=True, errors="replace", timeout=180)
        # the tree is put back as it was; its objects are rebuilt from the restored source so that the sandbox is whole again
        subprocess.run(["make"], cwd=tree, capture_output=True, text=True, errors="replace", timeout=600)
    # the repaired sd is back: one row that says so
    w, why = tls_trial("silent", False, 6.0)
    row("M-restore: the repaired sd is back in place: a client that closes at once leaves nothing", w is not None and w.ended, why or w.text())


PARTS = "ABCKDE"


def main():
    global BOX, SYS, SD
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        q3.bail("usage: sandbox-apispin.py <dir> [--build] [--only=A,B,C,K,D,E] [--mutants]")
    only = PARTS
    for a in sys.argv[1:]:
        if a.startswith("--only="):
            only = "".join(x for x in a[7:].upper().split(",") if x in PARTS) or q3.bail("--only names no part of %s" % PARTS)
    q3.BOX = BOX = os.path.abspath(args[0])
    q3.SYS = SYS = os.path.join(BOX, "sys")
    q3.SD = SD = os.path.join(SYS, "bin", "sd")
    q3.USER_PROGS = USER_PROGS
    say("sandbox-apispin: sandbox  %s" % BOX)
    if "--build" in sys.argv:
        if os.path.exists(BOX) and os.listdir(BOX):
            q3.bail("%s is not empty" % BOX)
        r = subprocess.run([sys.executable, q3.TOOL, BOX, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            q3.bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-apispin: built, bootstrap passed")
    elif not os.path.isfile(SD):
        q3.bail("%s holds no built sandbox (use --build, or point it at one)" % BOX)
    subprocess.run([sys.executable, q3.TOOL, BOX, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    say("\n--- preparation ------------------------------------------------------------------------------------------------")
    q3.prepare()
    q3.build_account("zzaa")
    q3.plain("zzaa", ["CREATE.FILE zzcl DYNAMIC"])
    # part K's account: the same, with the SH gate (field 7 of its register record) on, because the command it runs asks for a shell
    acct_sh = q3.build_account("zzsh")
    put(os.path.join(SYS, "accounts", "zzsh"), "\n".join([acct_sh, "", q3.GROUP, "", "", "", "yes", "", "", "yes", "yes", "yes"]) + "\n")
    say("sandbox-apispin: %d CPUs; the trials are sequential; parts run: %s%s" % (os.cpu_count() or 1, only, " + M" if "--mutants" in sys.argv else ""))

    try:
        for p in only:
            {"A": part_a, "B": part_b, "C": part_c, "K": part_k, "D": part_d, "E": part_e}[p]()
        if any(p in only for p in "ABCK") and SEEN_ALIVE[0] == 0:
            q3.bail("the instrument never saw a server process alive: nothing above could mean anything")
        if "--mutants" in sys.argv:
            part_m()
    finally:
        for nm in USER_PROGS:
            for d in ("bp", "bp.out"):
                p = os.path.join(SYS, d, nm)
                if os.path.exists(p):
                    os.remove(p)

    say("\nsandbox-apispin: %d passed, %d failed" % (q3.passed, q3.failed))
    if q3.passed + q3.failed == 0:
        q3.bail("no row ran - a broken test, not a pass")
    return 1 if q3.failed else 0


if __name__ == "__main__":
    sys.exit(main())
