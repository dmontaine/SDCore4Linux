#!/usr/bin/env python3
#
# sandbox-auditwriter.py - W.11 F4, option C1 (24 Oct 2026, the owner: "b then c"): the audit trail's writer.  A session hands each audit record to the daemon over a Unix
#                          datagram socket and the daemon stamps the user and the pid from the credentials the kernel attaches.  A private SD, no install, no sudo.
#
#   SDBOX_KEYSET=<n> python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-auditwriter.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or absent).  Exit 0 every row passed, 1 a row failed,
# 2 it could not run (the daemon did not start, the socket never appeared, the audited event never reached the file).
#
# START-HISTORY:
# 24 Oct 26 dm  New.  sdlnxd.c, k_error.c audit_to_daemon().  Plan: .claude/design-audit-trail-writer-24oct.md, option C.
# END-HISTORY
#
# WHAT IT DOES.  The sandbox kills its own sdlnxd right after -start (so its periodic clean-up cannot interfere), and a build of the tree carries a socket path of its own
# (sandbox-txnfail.py SANDBOX_PATCHES: /tmp/sdbox-audit-<keyset>/audit.sock, never the live /run/sd).  This suite starts the sandbox's daemon ITSELF, as the sandbox
# user, and then:
#   W0 the socket exists, is a socket, mode 0660, in a directory of ours at 0755
#   W1 a real audited event from an `sd -internal` session becomes exactly one line in the shape the readers take (verify-auditwords.py's RECORD)
#   W2 a datagram made by THIS process that claims "user=root pid=1" in its text and another SD user number: the line says the real user, THIS process's pid, the claimed
#      number, and the claim stays in the text after the stamped fields
#   W3 datagrams that must not become lines: no magic, no number, no text, a too-long number, one over the limit; and the daemon is still serving afterwards
#   W4 control characters (a newline, an escape, a high byte) become ? and one datagram is one line; a long text is cut at 1900; a ? number is kept
#   W5 the daemon says in the error log that it dropped datagrams
#   W6 the daemon stopped (SIGTERM): the socket is gone, and an audited event still reaches the file, appended by the session (the fallback)
#   W7 the daemon killed (SIGKILL): the socket file is left, the event still reaches the file, a new daemon replaces the socket and takes records again
# NOT HELD: that a DIFFERENT uid is stamped truly, that the root checks of the socket's directory refuse a group-writable one, and that the file refuses a member of
# sdusers once the installer has made it 0600 - a sandbox is one non-root user; those are the VM witness.

import getpass
import importlib.util
import os
import re
import secrets
import signal
import socket
import stat
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
sys.path.insert(0, HERE)


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


g = _load("sandbox_gates_for_auditwriter", "sandbox-gates.py")
aj = _load("sandbox_auditjournal_for_auditwriter", "sandbox-auditjournal.py")
say, row, bail = g.say, g.row, g.bail
USER = getpass.getuser()
UID = os.getuid()
BOX = SYS = SD = None
RECORD = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) user=(\S+?)(?: sudo=(\S+))? uid=(\S+) pid=(\S+) (.+)$")      # verify-auditwords.py's
KEYSET = int(os.environ.get("SDBOX_KEYSET", "0"))
SOCK_DIR = "/tmp/sdbox-audit-%d" % KEYSET
SOCK = SOCK_DIR + "/audit.sock"
DAEMON = None


def trail():
    return os.path.join(SYS, "audit")


def lines_since(off):
    with open(trail(), "rb") as f:
        f.seek(off)
        return [x for x in f.read().decode("utf-8", "replace").split("\n") if x]


def size():
    return os.path.getsize(trail())


def start_daemon():
    global DAEMON
    log = open(os.path.join(BOX, "sdlnxd-%d.out" % time.time_ns()), "w")
    DAEMON = subprocess.Popen([os.path.join(SYS, "bin", "sdlnxd")], stdout=log, stderr=subprocess.STDOUT, cwd=SYS)
    for _ in range(100):
        if DAEMON.poll() is not None:
            break
        if listening():
            return True
        time.sleep(0.1)
    return False


def listening():
    """True when something answers at the socket: a left-over file from a daemon that was killed is a file, not a listener"""
    s = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        s.connect(SOCK)
        return True
    except OSError:
        return False
    finally:
        s.close()


def stop_daemon(sig=signal.SIGTERM):
    global DAEMON
    if DAEMON is not None and DAEMON.poll() is None:
        DAEMON.send_signal(sig)
        try:
            DAEMON.wait(timeout=15)
        except Exception:
            DAEMON.kill()
            DAEMON.wait()
    DAEMON = None


def send(payload):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        s.sendto(payload, SOCK)
    finally:
        s.close()


def wait_lines(off, n, seconds=4):
    end = time.time() + seconds
    while time.time() < end:
        ls = lines_since(off)
        if len(ls) >= n:
            return ls
        time.sleep(0.1)
    return lines_since(off)


def quiet(off, seconds=1.2):
    """True when nothing was added in a while"""
    time.sleep(seconds)
    return not lines_since(off)


def probe(token):
    out = g.adm(["RUN gpl.bp zzaud token=" + token], internal=True)
    return g.has(out, r"^ZZAUD sent$")


def main():
    global BOX, SYS, SD
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-auditwriter.py <dir> [--build]")
    BOX = os.path.abspath(args[0])
    SYS = os.path.join(BOX, "sys")
    SD = os.path.join(SYS, "bin", "sd")
    g.BOX, g.SYS, g.SD = BOX, SYS, SD
    say("sandbox-auditwriter: sandbox %s, user %s (uid %d), socket %s" % (BOX, USER, UID, SOCK))
    if "--build" in sys.argv:
        if os.path.exists(BOX) and os.listdir(BOX):
            bail("%s is not empty" % BOX)
        r = subprocess.run([sys.executable, TOOL, BOX, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-auditwriter: built, bootstrap passed")
    elif not os.path.isfile(SD):
        bail("%s holds no built sandbox (use --build, or point it at one)" % BOX)
    subprocess.run([sys.executable, TOOL, BOX, "start"], capture_output=True, text=True, errors="replace", timeout=120)
    try:
        run_rows()
    finally:
        stop_daemon()
        subprocess.run(["rm", "-f", SOCK], capture_output=True)
    say("")
    say("sandbox-auditwriter: %d passed, %d failed" % (g.passed, g.failed))
    sys.exit(1 if g.failed else 0)


def run_rows():
    if os.path.exists(SOCK):
        bail("%s exists before the daemon started: another sandbox of this keyset is running" % SOCK)
    g.put(os.path.join(SYS, "gpl.bp", "zzaud"), "\n".join([
        "$internal", "program zzaud", "$catalog $zzaud", "$include keys.h", "$include int$keys.h",
        "   text = field(@sentence, ' ', 4, 99)", "   void kernel(K$AUDIT, 'zzwriter ':text)", "   crt 'ZZAUD sent'", "end", ""]))
    out = g.adm(["BASIC gpl.bp zzaud"], internal=True)
    if not g.has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("the probe did not compile:\n" + "\n".join(out[-8:]))
    if not os.path.exists(trail()):
        open(trail(), "ab").close()

    say("\n--- W0. the daemon and its socket ------------------------------------------------------------------------------")
    up = start_daemon()
    if not up:
        tail = ""
        for f in sorted(os.listdir(BOX)):
            if f.startswith("sdlnxd-"):
                tail = open(os.path.join(BOX, f), errors="replace").read()[-400:]
        bail("the daemon did not start or made no socket at %s: %r" % (SOCK, tail))
    st = os.stat(SOCK)
    ds = os.stat(SOCK_DIR)
    row("W0a: the socket is a socket, mode 0660, and ours", stat.S_ISSOCK(st.st_mode) and stat.S_IMODE(st.st_mode) == 0o660 and st.st_uid == UID,
        "mode %o, owner %d" % (stat.S_IMODE(st.st_mode), st.st_uid))
    row("W0b: its directory is ours and not open to the group or others", stat.S_ISDIR(ds.st_mode) and ds.st_uid == UID and not (ds.st_mode & 0o022), "mode %o" % stat.S_IMODE(ds.st_mode))

    say("\n--- W1. a real event from a session ------------------------------------------------------------------------")
    off = size()
    tok = "tok" + secrets.token_hex(5)
    sent = probe(tok)
    ls = wait_lines(off, 3)
    mine = [x for x in ls if ("zzwriter token=" + tok) in x]
    m = RECORD.match(mine[0]) if mine else None
    row("W1: the event reached the file as exactly one line in the shape the readers take", sent and len(mine) == 1 and m is not None, "sent=%s lines=%r" % (sent, ls))
    if not m:
        bail("the audited event is not in the file: nothing below would mean anything")
    row("W1b: user= is this user, sudo= is absent (the login user is the same), uid= is the session's SD user number, pid= is a number",
        m.group(2) == USER and m.group(3) is None and m.group(4).isdigit() and m.group(5).isdigit(), "line: %s" % mine[0])
    j = aj.find(tok, 6)
    if j is None or not j:
        say("  [SKIPPED] W1c: the journal copy of this event was not found or the journal is unreadable; the pid check against journald's _PID did not run")
    else:
        row("W1c: pid= on the line is the pid journald saw for the session (_PID) - the daemon's stamp and the journal's agree", j[0].get("_PID") == m.group(5),
            "_PID %r, line pid %r" % (j[0].get("_PID"), m.group(5)))

    say("\n--- W2. the sender cannot choose who it is ------------------------------------------------------------------")
    off = size()
    tok2 = "tok" + secrets.token_hex(5)
    send(("SDAUDIT1 77 zzwriter %s user=root pid=1" % tok2).encode())
    ls = wait_lines(off, 1)
    m2 = RECORD.match(ls[0]) if ls else None
    row("W2: the line names the real user, THIS process's pid and the claimed SD user number; the claim stays in the text", m2 is not None and len(ls) == 1 and m2.group(2) == USER
        and m2.group(5) == str(os.getpid()) and m2.group(4) == "77" and m2.group(6) == "zzwriter %s user=root pid=1" % tok2, "lines: %r (this pid %d)" % (ls, os.getpid()))

    say("\n--- W3. datagrams that must not become lines ----------------------------------------------------------------")
    off = size()
    for label, payload in (("no magic", b"hello there"), ("magic but no number", b"SDAUDIT1 zz text"), ("number and nothing else", b"SDAUDIT1 5 "),
                           ("magic alone", b"SDAUDIT1 "), ("a ten digit number", b"SDAUDIT1 1234567890 text"), ("a number with no text", b"SDAUDIT1 12\n"),
                           ("over the limit", b"SDAUDIT1 3 " + b"x" * 3000)):
        send(payload)
    row("W3: seven bad datagrams added no line", quiet(off), "lines: %r" % lines_since(off))
    off = size()
    tok3 = "tok" + secrets.token_hex(5)
    send(("SDAUDIT1 4 zzwriter " + tok3).encode())
    ls = wait_lines(off, 1)
    row("W3b: and the daemon still serves", len(ls) == 1 and tok3 in ls[0], "lines: %r" % ls)

    say("\n--- W4. what is made safe -----------------------------------------------------------------------------------")
    off = size()
    send(b"SDAUDIT1 9 zzwriter one\ntwo\x1b[31mred\x01 caf\xf9 end")
    ls = wait_lines(off, 1)
    row("W4: one datagram is one line; a newline, an escape, a control and a high byte are ?", len(ls) == 1 and "one?two?[31mred? caf? end" in ls[0] and "\x1b" not in ls[0], "lines: %r" % ls)
    off = size()
    send(b"SDAUDIT1 9 " + b"y" * 1990)
    ls = wait_lines(off, 1)
    m4 = RECORD.match(ls[0]) if ls else None
    row("W4b: a long text is cut at 1900 bytes", m4 is not None and len(m4.group(6)) == 1900, "text length %s" % (len(m4.group(6)) if m4 else None))
    off = size()
    send(b"SDAUDIT1 ? zzwriter unknown number")
    ls = wait_lines(off, 1)
    m4c = RECORD.match(ls[0]) if ls else None
    row("W4c: a ? number is kept as ?", m4c is not None and m4c.group(4) == "?", "lines: %r" % ls)

    say("\n--- W5. the daemon says it dropped datagrams ----------------------------------------------------------------")
    errlog = os.path.join(SYS, "errlog")
    found = None
    end = time.time() + 16
    while time.time() < end and not found:
        try:
            txt = open(errlog, errors="replace").read()
        except OSError:
            txt = ""
        m5 = re.search(r"audit: (\d+) datagram\(s\) refused, (\d+) record\(s\) not written", txt)
        found = m5
        if not found:
            time.sleep(1)
    row("W5: the error log carries 'audit: N datagram(s) refused' with N of at least the 7 bad datagrams sent above", found is not None and int(found.group(1)) >= 7,
        "found %r" % (found.group(0) if found else None))

    say("\n--- W6. the daemon stopped: the fallback ---------------------------------------------------------------------")
    stop_daemon(signal.SIGTERM)
    row("W6a: the socket file is gone after SIGTERM", not os.path.exists(SOCK), "still there")
    off = size()
    tok6 = "tok" + secrets.token_hex(5)
    sent = probe(tok6)
    ls = wait_lines(off, 3)
    mine = [x for x in ls if ("zzwriter token=" + tok6) in x]
    row("W6b: with no daemon an audited event still reaches the file (the session appended it) - one line, readable", sent and len(mine) == 1 and RECORD.match(mine[0]) is not None,
        "lines: %r" % ls)

    say("\n--- W7. the daemon killed: a stale socket ---------------------------------------------------------------------")
    if not start_daemon():
        bail("the daemon would not start a second time")
    stop_daemon(signal.SIGKILL)
    row("W7a: SIGKILL leaves the socket file behind (the situation after a crash)", os.path.exists(SOCK), "")
    off = size()
    tok7 = "tok" + secrets.token_hex(5)
    sent = probe(tok7)
    ls = wait_lines(off, 3)
    mine = [x for x in ls if ("zzwriter token=" + tok7) in x]
    row("W7b: a session whose send is refused (nothing listens) falls back to the file: one line", sent and len(mine) == 1, "lines: %r" % ls)
    if not start_daemon():
        bail("the daemon would not start over a stale socket")
    off = size()
    tok8 = "tok" + secrets.token_hex(5)
    send(("SDAUDIT1 6 zzwriter " + tok8).encode())
    ls = wait_lines(off, 1)
    row("W7c: a new daemon replaces the stale socket and takes records again", len(ls) == 1 and tok8 in ls[0], "lines: %r" % ls)


if __name__ == "__main__":
    main()
