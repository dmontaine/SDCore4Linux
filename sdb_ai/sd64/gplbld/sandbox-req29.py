#!/usr/bin/env python3
#
# sandbox-req29.py - API request 29 (open an 'account;file' file, the SDNet request of apisrvr's vb.open.sdnet), S.65 follow-up, 18 Oct 26.
#                    No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-req29.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or absent).
# Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 18 Oct 26 dm  Written.  The claim, read from apisrvr and never run: with bit 2 of NETFILES set in sd.conf, any API login can open the VOC-named file of ANY
#               account through request 29, because the request is gated by the bit alone - not by the LOGTO rule (a member of the account's group, the account not
#               suspended), not by the account's NET gate, and not by SDCLIENT (which vb.open honours).  This suite RUNS it: a real `sd -Q` server on pipes, the
#               wire protocol spoken from here, and the evidence is the record that comes back, compared with the one planted in the account's file on the disk.
# END-HISTORY
#
# THE INSTRUMENT.  A local API session without the client library: the suite starts the sandbox's own `sd -Q -C<out>!<in>` (what SDConnectLocal does), writes packets
# (length int32 LE including the 6-byte header, type int16 LE, data) and reads replies (length int32, error int16, status int32, data).  Every request and every reply
# is printed.  The rows' expected values come from the register records and files this suite writes, never from the server's answer.
#
#   NULL CASES REFUSED OUT LOUD.  The suite stops (exit 2) unless: the sandbox user is in sdusers (the local login needs it); the user is NOT in the group written in the
#   register for the account it must not enter; each fixture file really holds the record planted in it (read in an ordinary session of that account BEFORE the register
#   is changed); the request-3 (LOGTO) control really refuses that account; and with NETFILES unset request 29 is refused (so a request that opens a file at all is
#   known to need the bit).  A row that "opens" must also READ BACK the planted record: the file number alone proves nothing.
#
#   THE ROWS ARE WRITTEN FOR THE SECURE BEHAVIOUR: red on a tree whose request 29 asks only the bit, green once it also asks the LOGTO rule, the NET gate and SDCLIENT.
#
#   A  default sd.conf (no NETFILES): request 29 is refused, so the later rows measure the bit
#   B  NETFILES=2 (bit 2 set): an account that holds the NET gate, entered by a member: the control that 29 works at all; the account's own file is read back
#   C  the LOGTO rule: an account whose register group the user is not in (request 3 refuses it with 10003), a suspended one, and an account named by a path
#   D  the NET gate: a member of the account, NETFILES=2, the account's NET gate off
#   E  SDCLIENT=1 with NETFILES=2: request 4 is refused (the control), and so must request 29 be

import getpass
import grp
import importlib.util
import os
import re
import select
import struct
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("q3", os.path.join(HERE, "sandbox-stmt-q3.py"))
q3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q3)
say, row, has, tag, put = q3.say, q3.row, q3.has, q3.tag, q3.put

SV = {0: "OK", 1: "ON.ERROR", 2: "ELSE", 3: "ERROR", 4: "LOCKED"}
NOT_MEMBER_GROUP = "root"          # a group that exists on every Linux machine and that the user running this is not in (checked)
USER_PROGS = {
    # writes one record into the account's file zzsec and reads it back, so the oracle is what the DISK holds
    "zzmk": ("   open 'zzsec' to f else crt 'MK nofile' ; stop\n"
             "   who = field(@sentence, ' ', 4)\n"
             "   write 'secret of ' : who on f, 'k1'\n"
             "   read r from f, 'k1' else r = '<missing>'\n"
             "   crt 'MK[' : r : ']'\n"),
}


class Wire:
    """One API session on pipes: the sandbox's `sd -Q` server, packets written and read here."""

    def __init__(self, tag_):
        self.tag = tag_
        r1, w1 = os.pipe()          # server -> client
        r2, w2 = os.pipe()          # client -> server
        env = dict(os.environ, SD_CONFIG=os.path.join(q3.BOX, "sd.conf"))
        env.pop("SDTEST_ADMIN", None)
        self.argv = [q3.SD, "-Q", "-C%d!%d" % (w1, r2)]
        self.p = subprocess.Popen(self.argv, pass_fds=(w1, r2), env=env, cwd=q3.BOX, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.close(w1)
        os.close(r2)
        self.rd, self.wr = r1, w2
        say("    > wire %s: started %s (ordinary session, user %s)" % (tag_, " ".join(self.argv[:2]) + " ...", getpass.getuser()))

    def _read(self, n, secs=30):
        buf = b""
        end = time.time() + secs
        while len(buf) < n:
            left = end - time.time()
            if left <= 0:
                raise TimeoutError("no reply")
            r, _, _ = select.select([self.rd], [], [], left)
            if not r:
                raise TimeoutError("no reply")
            chunk = os.read(self.rd, n - len(buf))
            if not chunk:
                raise EOFError("the server closed the pipe")
            buf += chunk
        return buf

    def req(self, ptype, data=b"", shown=None):
        if isinstance(data, str):
            data = data.encode("latin-1")
        os.write(self.wr, struct.pack("<iH", len(data) + 6, ptype) + data)
        try:
            h = self._read(10)
            n, err, st = struct.unpack("<ihi", h)
            body = self._read(n - 10) if n > 10 else b""
        except (TimeoutError, EOFError) as e:
            say("      %s request %d %r -> %s" % (self.tag, ptype, shown if shown is not None else data[:60], e))
            return None
        say("      %s request %d %r -> error %d (%s) status %d data %r" % (self.tag, ptype, shown if shown is not None else data[:60], err, SV.get(err, "?"), st, body[:70]))
        return err, st, body

    def errtext(self):
        r = self.req(2)
        return r[2].decode("latin-1") if r and r[0] == 0 else None

    def login(self, account):
        """Request 25 (local login) then request 3 (the account).  Returns (error, text) of request 3."""
        a = self.req(25)
        if not a or a[0] != 0:
            return None, "local login refused: %r" % (a,)
        r = self.req(3, account)
        if r and r[0] == 3:
            return r[0], self.errtext()
        return (r[0] if r else None), ""

    def open29(self, arg):
        r = self.req(29, arg)
        if r and r[0] == 0 and len(r[2]) == 2:
            return struct.unpack("<h", r[2])[0], r
        return None, r

    def read_back(self, fno, rid=b"k1"):
        r = self.req(6, struct.pack("<h", fno) + rid, shown="fno %d id %r" % (fno, rid))
        return r[2].decode("latin-1") if r and r[0] == 0 else None

    def close(self):
        try:
            self.req(1)
        except OSError:
            pass
        for fd in (self.rd, self.wr):
            try:
                os.close(fd)
            except OSError:
                pass
        try:
            self.p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.p.kill()
            self.p.wait()


def msg(n):
    """The text of message N as this sandbox was built with it."""
    with open(os.path.join(q3.SYS, "messages", str(n)), encoding="utf-8", errors="replace") as f:
        return f.read().strip("\n")


def register(name, group, susp="", net="yes"):
    path = os.path.join(q3.BOX, "user_accounts", name)
    # 1 path, 3 group, 5 suspended, 7 sh, 8 os.exec, 9 sd.accounts, 10-12 the edit gates, 13-14 shared (blank), 15 net
    fields = [path, "", group, "", susp, "", "no", "no", "no", "yes", "yes", "yes", "", "", net]
    put(os.path.join(q3.SYS, "accounts", name), "\n".join(fields) + "\n")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        q3.bail("usage: sandbox-req29.py <dir> [--build]")
    q3.BOX = os.path.abspath(args[0])
    q3.SYS = os.path.join(q3.BOX, "sys")
    q3.SD = os.path.join(q3.SYS, "bin", "sd")
    q3.USER_PROGS = USER_PROGS
    BOX = q3.BOX
    say("sandbox-req29: sandbox  %s" % BOX)
    say("sandbox-req29: tree     %s" % os.path.dirname(HERE))
    if "--build" in sys.argv:
        if os.path.exists(BOX) and os.listdir(BOX):
            q3.bail("%s is not empty" % BOX)
        r = subprocess.run([sys.executable, q3.TOOL, BOX, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            q3.bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-req29: built, bootstrap passed")
    elif not os.path.isfile(q3.SD):
        q3.bail("%s holds no built sandbox (use --build, or point it at one)" % BOX)
    subprocess.run([sys.executable, q3.TOOL, BOX, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    me = getpass.getuser()
    try:
        in_sdusers = me in grp.getgrnam("sdusers").gr_mem
    except KeyError:
        in_sdusers = False
    if not in_sdusers:
        q3.bail("the user running this (%s) is not in the Linux group sdusers, which the local API login needs" % me)
    try:
        other_members = grp.getgrnam(NOT_MEMBER_GROUP).gr_mem
        other_gid = grp.getgrnam(NOT_MEMBER_GROUP).gr_gid
    except KeyError:
        q3.bail("no group %s on this machine" % NOT_MEMBER_GROUP)
    if me in other_members or other_gid == os.getgid():
        q3.bail("the user running this (%s) is in the group %s, so it cannot stand for 'a user who is not a member'" % (me, NOT_MEMBER_GROUP))

    say("\n--- preparation: four fixture accounts, each with a file zzsec holding one record the DISK is read back for ---------------")
    q3.prepare()
    planted = {}
    for n in ("zzaa", "zzab", "zzac", "zzad"):
        q3.build_account(n)
        out = q3.plain(n, ["CREATE.FILE zzsec DYNAMIC", "RUN bp zzmk " + n])
        got = tag(out, "MK")
        planted[n] = "secret of " + n
        if got != [planted[n]]:
            q3.bail("the fixture file of %s does not hold the planted record: %r" % (n, out[-4:]))
    say("  [done] planted and read back in an ordinary session of each account: %r" % planted)
    # only now are the register records changed (the sign-on above needed the user's own group)
    register("zzaa", q3.GROUP, net="no")            # a member, the NET gate OFF
    register("zzab", NOT_MEMBER_GROUP, net="yes")   # NOT a member, the NET gate on: isolates the membership rule
    register("zzac", q3.GROUP, susp="SUSPENDED", net="yes")      # a member, suspended, NET on
    register("zzad", q3.GROUP, net="yes")           # a member, NET on: the control
    path_b = os.path.join(BOX, "user_accounts", "zzab")

    try:
        # ------------------------------------------------------------------------------------------------------------------------
        say("\n--- A. no NETFILES in sd.conf: request 29 is refused whoever asks (the bit is what lets it work at all) ------------------")
        if not q3.restart():
            q3.bail("SD does not start with the sandbox's own sd.conf")
        w = Wire("A")
        e, t = w.login("zzad")
        row("A0 CONTROL: a member of zzad signs on over the pipe (request 25 then 3 'zzad' answers OK)", e == 0, repr((e, t)))
        if e != 0:
            q3.bail("the control login did not work, so no row below can be believed")
        fno, r = w.open29("zzad;zzsec")
        row("A1 request 29 'zzad;zzsec' with NETFILES unset (0): no file number comes back - refused by the bit (error ELSE, status ER$XREMOTE)", fno is None and r is not None and r[0] == 2, repr(r))
        w.close()

        # ------------------------------------------------------------------------------------------------------------------------
        say("\n--- B. NETFILES=2 (bit 2 set): the control that request 29 works for a member whose account holds the NET gate ------------")
        if not q3.restart("NETFILES=2"):
            q3.bail("SD does not start with NETFILES=2 in sd.conf")
        w = Wire("B")
        e, t = w.login("zzad")
        row("B0 a member signs on to zzad (OK)", e == 0, repr((e, t)))
        fno, r = w.open29("zzad;zzsec")
        back = w.read_back(fno) if fno is not None else None
        row("B1 CONTROL: request 29 'zzad;zzsec' (a member's own account, NET gate on) returns a file number and READ of k1 gives the planted %r" % planted["zzad"],
            fno is not None and back == planted["zzad"], repr((fno, back, r)))
        w.close()

        # ------------------------------------------------------------------------------------------------------------------------
        say("\n--- C. the LOGTO rule: the same session, an account it could not LOGTO ---------------------------------------------------")
        w = Wire("C")
        e, t = w.login("zzad")
        row("C0 a member signs on to zzad (OK)", e == 0, repr((e, t)))
        # the account the user may not enter: request 3 is the rule 29 must be held to
        w2 = Wire("C3")
        a = w2.req(25)
        r = w2.req(3, "zzab")
        txt = w2.errtext() if r and r[0] == 3 else None
        row("C1 CONTROL (the rule): request 3 'zzab' - an account whose register group (%s) the user is not in - is refused, error ERROR with the text of 10003 (%r)" % (NOT_MEMBER_GROUP, msg(10003)),
            a is not None and a[0] == 0 and r is not None and r[0] == 3 and txt == msg(10003), repr((a, r, txt)))
        w2.close()
        w3 = Wire("C3b")
        a = w3.req(25)
        rz = w3.req(3, "zzac")
        row("C2 CONTROL (the rule): request 3 'zzac' - a suspended account - is refused too (error ERROR)", a is not None and a[0] == 0 and rz is not None and rz[0] == 3, repr((a, rz)))
        w3.close()

        fno, r = w.open29("zzab;zzsec")
        back = w.read_back(fno) if fno is not None else None
        say("      [evidence] on the disk zzab's file holds %r (planted and read back in preparation); request 29 'zzab;zzsec' gave file number %r and READ k1 gave %r" % (planted["zzab"], fno, back))
        row("C3 request 29 'zzab;zzsec' (an account the user is NOT a member of): refused - no file number, and the record %r is not read" % planted["zzab"],
            fno is None and back != planted["zzab"], "OPENED fno %r and READ %r  <- the claim is true" % (fno, back))
        fno, r = w.open29("zzac;zzsec")
        back = w.read_back(fno) if fno is not None else None
        row("C4 request 29 'zzac;zzsec' (a SUSPENDED account, the user a member): refused", fno is None and back != planted["zzac"], "OPENED fno %r and READ %r" % (fno, back))
        fno, r = w.open29(path_b + ";zzsec")
        back = w.read_back(fno) if fno is not None else None
        row("C5 request 29 with the account given as a PATH (%s;zzsec): refused - a path names no register record, so nothing says who may enter it" % path_b,
            fno is None and back != planted["zzab"], "OPENED fno %r and READ %r" % (fno, back))
        fno, r = w.open29("zzad;zzsec")
        back = w.read_back(fno) if fno is not None else None
        row("C6 CONTROL AFTER THE REFUSALS: 'zzad;zzsec' still opens and reads %r (so the refusals above are the rule and not a broken session)" % planted["zzad"],
            fno is not None and back == planted["zzad"], repr((fno, back)))
        w.close()

        # ------------------------------------------------------------------------------------------------------------------------
        say("\n--- D. the NET gate: a member of zzaa, whose NET gate is off (register field 15 'no'), asks for its OWN file ---------------")
        w = Wire("D")
        e, t = w.login("zzaa")
        row("D0 a member signs on to zzaa (OK)", e == 0, repr((e, t)))
        fno, r = w.open29("zzaa;zzsec")
        back = w.read_back(fno) if fno is not None else None
        row("D1 request 29 'zzaa;zzsec' with the account's NET gate off: refused (the NET gate is the account's permission to use SDNet files)",
            fno is None and back != planted["zzaa"], "OPENED fno %r and READ %r" % (fno, back))
        w.close()

        # ------------------------------------------------------------------------------------------------------------------------
        say("\n--- E. SDCLIENT=1 with NETFILES=2: no open from an API client; request 29 is an open ----------------------------------")
        if not q3.restart("NETFILES=2", "SDCLIENT=1"):
            q3.bail("SD does not start with NETFILES=2 and SDCLIENT=1")
        w = Wire("E")
        e, t = w.login("zzad")
        row("E0 a member signs on to zzad (OK)", e == 0, repr((e, t)))
        r = w.req(4, "zzsec")
        row("E1 CONTROL: request 4 (open) 'zzsec' is refused under SDCLIENT=1 (error ON.ERROR, the 5262 text: file access is disabled)", r is not None and r[0] == 1, repr(r))
        fno, r = w.open29("zzad;zzsec")
        back = w.read_back(fno) if fno is not None else None
        row("E2 request 29 'zzad;zzsec' under SDCLIENT=1 (the member's own account, NET gate on): refused like request 4", fno is None and back != planted["zzad"],
            "OPENED fno %r and READ %r" % (fno, back))
        w.close()
    finally:
        q3.restart()
        subprocess.run([sys.executable, q3.TOOL, BOX, "stop"], capture_output=True, text=True, errors="replace", timeout=120)

    say("\nsandbox-req29: %d passed, %d failed" % (q3.passed, q3.failed))
    return 1 if q3.failed else 0


if __name__ == "__main__":
    sys.exit(main())
