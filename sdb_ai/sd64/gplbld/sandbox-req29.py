#!/usr/bin/env python3
#
# sandbox-req29.py - API request 29 (open an 'account;file' file, the SDNet request of apisrvr's vb.open.sdnet), S.65 follow-up, 18 Oct 26.
#                    No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-req29.py <dir> [--build] [--mutant=NAME]
#
# Besides request 29 it holds the rows that need a REAL `sd -Q` spoken to over the wire: sections F (filelock, fileunlock) and G (the text and status of an ON ERROR reply).
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or absent).
# Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 19 Oct 26 dm  Finish 2 (verifier findings).  (F) The BLOCKING form of request 32 (the wait flag set) had no row: the stale `files(i)` could be put back on that branch alone and everything stayed
#               green.  F10 to F19 hold S1's file lock and send S2 the request with the flag and no answer is read for 3 seconds (the stale index would lock the file S2 opened last and answer
#               at once), then release and read the answer, then look at which file is locked; --mutant=filelock-wait puts the stale index back on that branch only and exactly F11, F13, F14,
#               F15, F18 and F19 fail (Wire.send / recv hold a request back).  (G) G8: ids with a high byte - 247 to 250 are written and read back, the five marks 251 to 255 each take the ON ERROR of
#               an id that is not valid (+3000, no text) and COUNT afterwards says four records; netfake.py had refused 248 to 255 and its notes said the real server accepted 250.  (H) H4 asserted
#               nothing about the CR (it stripped it before comparing) and User page 42 says it is KEPT: it asserts x CR, field mark, y CR now; H5b asserts that D1 is NOT found in a directory file
#               written as d1 (the page says so; the evidence line was all there was).
# 19 Oct 26 dm  K8a, K1 (server half) and K8g.  (F) API requests 32 and 33, filelock and fileunlock, used `files(i)`, the scratch variable of the last open, instead of
#               files(fno): a lock or an unlock went to whichever file had been opened last.  Three files are opened, the first is locked by number, and a SECOND session on the
#               same account asks for the file lock on each (no wait): LOCKED says where the first session's lock is.  Red on the apisrvr of HEAD: F4, F5 and F6.  (G) The text
#               of an ON ERROR reply: apisrvr sent @abort.message, which a refusal sets and nothing cleared, so a WRITE with an over-long id answered 'Invalid call name' after
#               a call with no name (red on HEAD: G2); the SDNet client now shows that text, so apisrvr empties the message at the top of every request.  Also section G holds
#               gplbld/netfake.py to the real server: the kind, the signed STATUS() and the text of the ON ERROR replies it imitates (netfake.REAL_ON_ERROR) are each measured
#               here - an id that is not valid, a read only file (chmod a-w, as the server's user), MAXRLOCK=1 for a locking read and for request 30; the first fake had
#               -3000 / -3018 / -3060 and invented texts, the real server answers +3000 / +3018 / +3060 or STATUS() 0 with the kernel's text.  (K8g) The audit lines of
#               request 29's refusals are read after each refusal (B2 and C6a are the controls: a good open adds none), and --mutant=NAME takes one rule of request 29 out of the
#               sandbox's copy of apisrvr and says whether exactly the rows listed for it failed: entry-group, entry-suspended, register, netgate, sdclient (5 of 5 killed by
#               exactly their rows, 19 Oct 26).  Not covered: the audit line of the SDCLIENT refusal (there is none), a files-only login (needs SCRAM and TLS: the VM witness).
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
sys.path.insert(0, HERE)
import netfake                      # its REAL_ON_ERROR table: the facts about the real server that section G holds the fake to
spec = importlib.util.spec_from_file_location("q3", os.path.join(HERE, "sandbox-stmt-q3.py"))
q3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q3)
say, row, has, tag, put = q3.say, q3.row, q3.has, q3.tag, q3.put

FAILED_IDS = []


def row(name, ok, detail=""):
    """q3.row, and the id of a failed row (its first word: C3, G6 ...) is kept, so that a mutant run can say which rows it killed."""
    q3.row(name, ok, detail)
    if not ok:
        FAILED_IDS.append(name.split()[0])


def audit_off():
    """Size of the sandbox's audit file, which SD appends to and never creates: it is made, empty, when it is missing.  None when it cannot be."""
    path = os.path.join(q3.SYS, "audit")
    try:
        if not os.path.exists(path):
            with open(path, "ab"):
                pass
        return os.path.getsize(path)
    except OSError:
        return None


def audit_new(off):
    """What the audit trail gained since OFF; None when it cannot be read (a row that needs it then FAILS, it does not pass for want of a line to look at)."""
    if off is None:
        return None
    try:
        with open(os.path.join(q3.SYS, "audit"), "rb") as f:
            f.seek(off)
            return f.read().decode("utf-8", errors="replace")
    except OSError:
        return None


def audit_has(new, pattern):
    return new is not None and re.search(pattern, new, re.M) is not None


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
        self.pending = None         # what send() last sent, for the line recv() prints
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

    def _write(self, ptype, data):
        """Send one request packet (length int32 LE including the 6 byte header, type int16 LE, data); returns the data as bytes."""
        if isinstance(data, str):
            data = data.encode("latin-1")
        os.write(self.wr, struct.pack("<iH", len(data) + 6, ptype) + data)
        return data

    def _answer(self, secs):
        """Read one reply: (error, status, body).  Raises TimeoutError when nothing (or not the whole of it) comes within SECS, EOFError when the server closes the pipe."""
        h = self._read(10, secs)
        n, err, st = struct.unpack("<ihi", h)
        return err, st, (self._read(n - 10, secs) if n > 10 else b"")

    def req(self, ptype, data=b"", shown=None, secs=30):
        data = self._write(ptype, data)
        what = shown if shown is not None else data[:60]
        try:
            err, st, body = self._answer(secs)
        except (TimeoutError, EOFError) as e:
            say("      %s request %d %r -> %s" % (self.tag, ptype, what, e))
            return None
        say("      %s request %d %r -> error %d (%s) status %d data %r" % (self.tag, ptype, what, err, SV.get(err, "?"), st, body[:70]))
        return err, st, body

    def send(self, ptype, data=b"", shown=None):
        """Send a request and do NOT wait for its answer: recv() reads it.  For a request the server is meant to hold back (a file lock with the wait flag)."""
        data = self._write(ptype, data)
        self.pending = shown if shown is not None else data[:60]
        say("      %s request %d %r -> (sent; the answer is read later)" % (self.tag, ptype, self.pending))

    def recv(self, secs):
        """The answer to the request sent with send(), or None when nothing came within SECS seconds (the request is then still pending and a later recv() can read its answer)."""
        try:
            err, st, body = self._answer(secs)
        except (TimeoutError, EOFError) as e:
            say("      %s answer to %r -> %s (within %s s)" % (self.tag, self.pending, e, secs))
            return None
        say("      %s answer to %r -> error %d (%s) status %d data %r" % (self.tag, self.pending, err, SV.get(err, "?"), st, body[:70]))
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

    def open4(self, name):
        """Request 4, open a file of the account by its VOC name.  Returns (file number or None, the reply)."""
        r = self.req(4, name)
        if r and r[0] == 0 and len(r[2]) == 2:
            return struct.unpack("<h", r[2])[0], r
        return None, r

    def filelock(self, fno, wait=0):
        """Request 32: fno and the wait flag, two short integers.  wait 0 is the form with a LOCKED clause (error 4 when another user holds the file lock)."""
        return self.req(32, struct.pack("<hh", fno, wait), shown="filelock fno %r wait %d" % (fno, wait))

    def filelock_wait(self, fno):
        """Request 32 with the wait flag set, sent and NOT answered here: the server holds it back until the lock is free.  Read the answer with recv()."""
        self.send(32, struct.pack("<hh", fno, 1), shown="filelock fno %r wait 1" % (fno,))

    def fileunlock(self, fno):
        """Request 33: fno, a short integer."""
        return self.req(33, struct.pack("<h", fno), shown="fileunlock fno %r" % (fno,))

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


def section_f():
    """F. requests 32 and 33 act on the file number the client names (K8a, 19 Oct 26).  Both used `files(i)`, a scratch variable, so a lock or an unlock went to
    whichever file `i` happened to index (the file opened last), not to the one asked for.  The evidence is a SECOND session on the same account: it asks for the
    file lock on each file with the no-wait form, and LOCKED (error 4) or OK says where the first session's lock really is."""
    say("\n--- F. file locks, requests 32 and 33: the lock goes to the file NUMBER asked for (K8a) -------------------------------------")
    if not q3.restart():
        q3.bail("SD does not start with the sandbox's own sd.conf")
    for extra in ("zzsec2", "zzsec3"):
        out = q3.plain("zzad", ["CREATE.FILE %s DYNAMIC" % extra])
        say("    [setup] CREATE.FILE %s -> %r" % (extra, out[-2:]))
    s1, s2 = Wire("F1"), Wire("F2")
    e1, t1 = s1.login("zzad")
    e2, t2 = s2.login("zzad")
    row("F0 two members sign on to zzad (OK both): the holder S1 and the observer S2", e1 == 0 and e2 == 0, repr(((e1, t1), (e2, t2))))
    if e1 != 0 or e2 != 0:
        q3.bail("the control logins did not work, so no row below can be believed")
    names = ("zzsec", "zzsec2", "zzsec3")
    n1 = [s1.open4(n)[0] for n in names]
    n2 = [s2.open4(n)[0] for n in names]
    row("F1 each session opens zzsec, zzsec2 and zzsec3 in that order and is given three different file numbers; the LAST file opened (zzsec3) is not the one the first "
        "lock asks for, which is what makes the stale `files(i)` show", None not in n1 + n2 and len(set(n1)) == 3 and len(set(n2)) == 3, repr((n1, n2)))
    if None in n1 + n2:
        q3.bail("a file did not open, so no lock row can be believed")
    a1, b1, c1 = n1
    a2, b2, c2 = n2
    r = s1.filelock(a1, 0)
    row("F2 S1 takes the file lock on zzsec by its number (no wait): OK", r is not None and r[0] == 0, repr(r))
    r = s2.filelock(a2, 0)
    row("F3 S2 asks for the file lock on zzsec (no wait): LOCKED (error 4) - the lock S1 took is on zzsec", r is not None and r[0] == 4, repr(r))
    r = s2.filelock(b2, 0)
    row("F4 CONTROL: S2 asks for the file lock on zzsec2 (no wait): granted (OK) - S1 did not lock it, and a server that answered LOCKED to everything fails here", r is not None and r[0] == 0, repr(r))
    if r is not None and r[0] == 0:
        s2.fileunlock(b2)
    r = s2.filelock(c2, 0)
    row("F5 CONTROL: S2 asks for the file lock on zzsec3, the file opened last: granted (OK) - the bug put S1's lock here", r is not None and r[0] == 0, repr(r))
    if r is not None and r[0] == 0:
        s2.fileunlock(c2)
    s1.fileunlock(b1)
    r = s2.filelock(a2, 0)
    row("F6 S1 releases zzsec2, which it never locked: zzsec is STILL locked (S2: LOCKED) - an unlock goes to the file named, not to the last one opened", r is not None and r[0] == 4, repr(r))
    r = s1.fileunlock(a1)
    row("F7 S1 releases zzsec by its number: OK", r is not None and r[0] == 0, repr(r))
    r = s2.filelock(a2, 0)
    row("F8 S2 now gets the file lock on zzsec (OK): the unlock released the file that was named", r is not None and r[0] == 0, repr(r))
    if r is not None and r[0] == 0:
        s2.fileunlock(a2)
    r = s1.filelock(99, 0)
    row("F9 CONTROL: a file number that is not open (99) is the invalid-file-number error (error ERROR 3), not a lock", r is not None and r[0] == 3, repr(r))

    # ---- the BLOCKING form, request 32 with the wait flag set.  The verifier of 19 Oct 26 found that nothing sent it: the stale `files(i)` could be put back on that branch alone
    #      and every row above stayed green.  S1 holds zzsec; S2 asks for it WITH the wait flag, which the server must hold back until S1 lets go.  The stale index would lock
    #      S2's last-opened file (zzsec3) and answer at once - which is what the 3 second wait is the evidence against.
    say("\n  -- the blocking form: the wait flag set (the server holds the request until the lock is free) --")
    r = s1.filelock(a1, 0)
    row("F10 S1 takes the file lock on zzsec (no wait): OK - S2 has something to wait for", r is not None and r[0] == 0, repr(r))
    s2.filelock_wait(a2)
    held = s2.recv(3)
    row("F11 S2 asks for the file lock on zzsec WITH the wait flag: NO answer in 3 seconds - the server holds the request while S1 has the lock (the stale `files(i)` would lock zzsec3, the "
        "file S2 opened last, and answer at once)", held is None, repr(held))
    r = s1.fileunlock(a1)
    row("F12 S1 releases zzsec: OK", r is not None and r[0] == 0, repr(r))
    got = s2.recv(15)
    row("F13 ...and the request S2 was held back on is then answered, OK (error 0) - S2 has the lock on zzsec now", got is not None and got[0] == 0, repr(got))
    r = s1.filelock(a1, 0)
    row("F14 S1 asks for the file lock on zzsec (no wait): LOCKED (error 4) - it is S2 that holds it, and zzsec is the file the wait was for", r is not None and r[0] == 4, repr(r))
    r = s1.filelock(c1, 0)
    row("F15 CONTROL: S1 asks for the file lock on zzsec3, the file S2 opened last (no wait): granted (OK) - the wait did not lock the stale index's file", r is not None and r[0] == 0, repr(r))
    if r is not None and r[0] == 0:
        s1.fileunlock(c1)
    s2.fileunlock(a2)
    r = s1.filelock(a1, 0)
    row("F16 S2 let go of zzsec: S1 gets it (OK); S1 holds zzsec again for the next rows", r is not None and r[0] == 0, repr(r))
    s2.filelock_wait(b2)
    free = s2.recv(3)
    row("F17 S2 asks WITH the wait flag for zzsec2, which nobody holds, while S1 holds zzsec: granted at once (error 0, inside 3 seconds) - waiting is only for a lock that is taken",
        free is not None and free[0] == 0, repr(free))
    r = s1.filelock(b1, 0)
    row("F18 ...and the lock S2 was granted is on zzsec2: S1 asking for it (no wait) is LOCKED (error 4)", r is not None and r[0] == 4, repr(r))
    r = s1.filelock(c1, 0)
    row("F19 CONTROL: S1 asks for zzsec3 (no wait): granted (OK) - the wait on a free file did not lock the stale index's file either", r is not None and r[0] == 0, repr(r))
    if r is not None and r[0] == 0:
        s1.fileunlock(c1)
    s2.fileunlock(b2)
    s1.fileunlock(a1)
    s1.close()
    s2.close()


def section_g():
    """G. THE TEXT OF AN ON ERROR REPLY (K1, 19 Oct 26).  The SDNet client now shows an ON ERROR reply's text, so the text must belong to THIS reply.  apisrvr answers
    SV$ON.ERROR with @abort.message, which a refusal sets and nothing cleared: a later ON ERROR clause that had nothing to say (write ... on error) sent the earlier
    refusal's text.  The server empties its message at the top of every request now.  Also the facts gplbld/netfake.py claims about the REAL server's ON ERROR replies,
    so that the fake the client rows run against is held to the server: the kind, the (signed) status and whether there is a text."""
    say("\n--- G. the text of an ON ERROR reply belongs to the request that got it (K1) -----------------------------------------------")
    if not q3.restart():
        q3.bail("SD does not start with the sandbox's own sd.conf")
    w = Wire("G")
    e, t = w.login("zzad")
    row("G0 a member signs on to zzad (OK)", e == 0, repr((e, t)))
    if e != 0:
        q3.bail("the control login did not work, so no row below can be believed")
    fno, r = w.open4("zzsec")
    row("G0b the file zzsec opens (a file number comes back)", fno is not None, repr(r))
    if fno is None:
        q3.bail("the file did not open")
    bad_call = struct.pack("<h", 0)                         # a call name of length 0: refused with 5263 (abort.message set, SV$ON.ERROR)
    long_id = b"x" * 100                                    # longer than MAXIDLEN (63): the WRITE statement takes its ON ERROR clause
    write_long = struct.pack("<hh", fno, len(long_id)) + long_id + b"data"
    r1 = w.req(20, bad_call, shown="call, name length 0")
    row("G1 CONTROL: request 20 with a call name of length 0 is refused with ON ERROR and the text of 5263 (%r): a refusal's text is sent" % msg(5263),
        r1 is not None and r1[0] == 1 and r1[2].decode("latin-1") == msg(5263), repr(r1))
    r2 = w.req(16, write_long, shown="write fno %d, an id of %d characters" % (fno, len(long_id)))
    say("      [evidence] the WRITE of a 100 character id answered error %r status %r data %r" % (r2 and r2[0], r2 and r2[1], r2 and r2[2]))
    row("G2 a WRITE that takes its ON ERROR clause (an id over MAXIDLEN) right after that refusal is ON ERROR with NO text: the refusal's text is not repeated",
        r2 is not None and r2[0] == 1 and r2[2] == b"", repr(r2))
    r3 = w.req(20, bad_call, shown="call, name length 0")
    row("G3 CONTROL: the same refusal again sends its text again (emptying the message at the top of a request does not touch a refusal)",
        r3 is not None and r3[0] == 1 and r3[2].decode("latin-1") == msg(5263), repr(r3))
    w.close()
    w = Wire("G2")
    e, t = w.login("zzad")
    fno, r = w.open4("zzsec")
    r4 = w.req(16, struct.pack("<hh", fno, len(long_id)) + long_id + b"data", shown="write fno %r, an id of %d characters" % (fno, len(long_id)))
    row("G4 CONTROL: in a NEW session, with no refusal before it, the same WRITE is ON ERROR with no text (the same answer as G2)", r4 is not None and r4[0] == 1 and r4[2] == b"", repr(r4))
    row("G5 ...and the status is the same in both sessions (the clearing did not touch STATUS())", r2 is not None and r4 is not None and r2[1] == r4[1], repr((r2 and r2[1], r4 and r4[1])))
    w.close()

    # ---- the facts gplbld/netfake.py claims about the REAL server (netfake.REAL_ON_ERROR): each one measured here, so that the fake the client rows run against cannot be wrong
    #      about the server again.  A row compares the server with the table, never the table with itself.
    say("\n  -- what netfake.py claims the real server answers (REAL_ON_ERROR): an id that is not valid, a read only file, MAXRLOCK")

    def real(key, got, label, extra_ok=True, tag="G6"):
        kind, status, pat = netfake.REAL_ON_ERROR[key]
        text = got[2].decode("latin-1") if got is not None else None
        row("%s %s: ON ERROR (error %d), STATUS() %d and %s" % (tag, label, kind, status, ("the text matching " + pat) if pat else "NO text"),
            got is not None and got[0] == kind and got[1] == status and re.fullmatch(pat, text) is not None and extra_ok, repr(got))
    if os.geteuid() == 0:
        q3.bail("this is root: a file mode does not stop root, so the read only file below would prove nothing")
    w = Wire("Gid")
    e, t = w.login("zzad")
    f1, _r = w.open4("zzsec")
    rr = w.req(16, struct.pack("<hh", f1, 63) + b"a" * 63 + b"x", shown="write, an id of 63 characters")
    row("G6a CONTROL: a record whose id has 63 characters (the longest) is written (OK, STATUS() 0): the rows below are about ids that are NOT valid", rr is not None and rr[0] == 0, repr(rr))
    real("write_bad_id", w.req(16, struct.pack("<hh", f1, 0) + b"x", shown="write, an EMPTY id"), "a WRITE with an empty id")
    real("write_bad_id", w.req(16, struct.pack("<hh", f1, 64) + b"a" * 64 + b"x", shown="write, an id of 64 characters"), "a WRITE with an id of 64 characters (MAXIDLEN is 63)")
    real("delete_bad_id", w.req(18, struct.pack("<h", f1) + b"a" * 64, shown="delete, an id of 64 characters"), "a DELETE with an id of 64 characters")
    w.close()

    # ---- ids with a high byte (verifier finding of 19 Oct 26).  netfake.py refused every id holding a byte of 248 to 255, and its notes said the real server had accepted 250; the marks are
    #      251 to 255 (sddefs.h).  Measured here, in a file of its own so that the disk can be counted: 247 to 250 are written and read back, 251 to 255 each take the ON ERROR of an id that
    #      is not valid, and COUNT afterwards says four records - the refused ids were not stored.
    say("\n  -- ids with a high byte: 247 to 250 are ordinary characters, the five marks 251 to 255 are not an id (netfake.py is held to this) --")
    out = q3.plain("zzad", ["CREATE.FILE zzmk DYNAMIC"])
    say("    [setup] CREATE.FILE zzmk DYNAMIC -> %r" % (out[-2:],))
    w = Wire("Gmk")
    e, t = w.login("zzad")
    fmk, _r = w.open4("zzmk")
    row("G8a the file zzmk opens (a file number comes back)", fmk is not None, repr(_r))
    if fmk is None:
        q3.bail("the file zzmk did not open")
    seen = {}
    for x in (247, 248, 249, 250):
        ident = b"m" + bytes([x])
        wrote = w.req(16, struct.pack("<hh", fmk, len(ident)) + ident + b"d%d" % x, shown="write id 'm' + byte %d" % x)
        back = w.req(6, struct.pack("<h", fmk) + ident, shown="read id 'm' + byte %d" % x)
        seen[x] = (wrote, back)
    row("G8b an id holding byte 247, 248, 249 or 250 is written (OK, STATUS() 0) and READ gives its data back: ordinary characters, the real server accepted 250 and the fake refused 248 to 255 "
        "until 19 Oct 26", all(v[0] is not None and v[0][:2] == (0, 0) and v[1] is not None and v[1][0] == 0 and v[1][2] == b"d%d" % x for x, v in seen.items()), repr(seen))
    for x in range(251, 256):
        ident = b"m" + bytes([x])
        real("write_bad_id", w.req(16, struct.pack("<hh", fmk, len(ident)) + ident + b"data", shown="write id 'm' + byte %d" % x), "a WRITE with byte %d (a mark) in the id" % x, tag="G8c")
    w.close()
    out = q3.plain("zzad", ["COUNT zzmk"])
    say("      [evidence] COUNT zzmk (the disk) -> %r" % (out[-3:],))
    row("G8d ...and COUNT in an ordinary session says 4 records are in zzmk (247 to 250): none of the five refused ids was stored", has(out, r"^4 record\(s\) counted"), repr(out[-3:]))

    out = q3.plain("zzad", ["CREATE.FILE zzsecro DYNAMIC"])
    w = Wire("Gro")
    e, t = w.login("zzad")
    fro, _r = w.open4("zzsecro")
    rr = w.req(16, struct.pack("<hh", fro, 2) + b"k1" + b"first", shown="write k1 (the file is still writable)")
    row("G6b CONTROL: zzsecro is written while it is writable (OK) - the read only rows below are the mode and not a file that never worked", fro is not None and rr is not None and rr[0] == 0, repr((fro, rr)))
    w.close()
    ro = os.path.join(q3.BOX, "user_accounts", "zzad", "zzsecro")
    subprocess.run(["chmod", "-R", "a-w", ro], check=True)
    try:
        w = Wire("Gro2")
        e, t = w.login("zzad")
        fro, _r = w.open4("zzsecro")
        real("write_readonly", w.req(16, struct.pack("<hh", fro, 2) + b"k1" + b"second", shown="write k1 to the read only file"), "a WRITE to a file the server's user cannot write")
        real("delete_readonly", w.req(18, struct.pack("<h", fro) + b"k1", shown="delete k1 from the read only file"), "a DELETE from it")
        real("clearfile_readonly", w.req(31, struct.pack("<h", fro), shown="clearfile of the read only file"), "a CLEARFILE of it (no ON ERROR clause: an abort, with the kernel's text)")
        w.close()
    finally:
        subprocess.run(["chmod", "-R", "u+w", ro])
    w = Wire("Gro3")
    e, t = w.login("zzad")
    fro, _r = w.open4("zzsecro")
    rr = w.req(6, struct.pack("<h", fro) + b"k1", shown="read k1 after the mode is given back")
    row("G6c CONTROL: the record k1 of zzsecro is still there, unchanged ('first'), after the refused WRITE, DELETE and CLEARFILE - the disk is the evidence", rr is not None and rr[0] == 0 and rr[2] == b"first", repr(rr))
    w.close()

    if not q3.restart("MAXRLOCK=1"):
        q3.bail("SD does not start with MAXRLOCK=1")
    w = Wire("Gml")
    e, t = w.login("zzad")
    f1, _r = w.open4("zzsec")
    l1 = w.req(30, struct.pack("<hh", f1, 1) + b"l1", shown="lock record l1 (update)")
    row("G7a CONTROL: with MAXRLOCK=1 the first lock (request 30, update) is granted (OK)", l1 is not None and l1[0] == 0, repr(l1))
    real("lockrecord_maxrlock", w.req(30, struct.pack("<hh", f1, 1) + b"l2", shown="lock record l2 (update)"), "a SECOND, new lock by request 30 (no ON ERROR clause: an abort, with the kernel's text)")
    l1b = w.req(30, struct.pack("<hh", f1, 1) + b"l1", shown="lock record l1 again")
    row("G7b CONTROL: a lock the session already holds is not a new one: asking for l1 again is granted (OK)", l1b is not None and l1b[0] == 0, repr(l1b))
    real("readu_maxrlock", w.req(7, struct.pack("<h", f1) + b"l3", shown="readl of a new record l3"), "a READL of a new record")
    real("readu_maxrlock", w.req(9, struct.pack("<h", f1) + b"l3", shown="readu of a new record l3"), "a READU of a new record")
    real("readu_maxrlock", w.req(41, struct.pack("<hhI", f1, 1, 1) + b"l3", shown="readv of l3, flags 1"), "a READV with a lock flag")
    w.close()
    q3.restart()


def section_h():
    """H. WHICH FILES A REMOTE LOGIN CAN USE, measured at the request layer (19 Oct 26, K5 f).  A remote file is whatever the account's VOC names, opened by the server's own
    OPEN; the SDNet client sends requests 4, 6, 16 ... and nothing else.  These rows are CHARACTERISATIONS: the expected values of the ones that matter (a round trip is exact, ids
    fold case in a file made today) come from the rule, and the rest print what the server did, which the User page 'Programming with a Remote File' quotes.  Not through an N
    pointer and not through the BASIC client: that is sandbox-netfile.py's fake server's job, and the VM's."""
    say("\n--- H. which files a remote login can use: a directory file, ids that differ only in case, a 1 MB and a 20 MB record (measured at the request layer) -------------")
    if not q3.restart():
        q3.bail("SD does not start with the sandbox's own sd.conf")
    out = q3.plain("zzad", ["CREATE.FILE zzdir DIRECTORY", "CREATE.FILE zzbig DYNAMIC"])
    say("    [setup] CREATE.FILE zzdir DIRECTORY / zzbig DYNAMIC -> %r" % (out[-3:],))
    w = Wire("H")
    e, t = w.login("zzad")
    row("H0 a member signs on to zzad (OK)", e == 0, repr((e, t)))
    if e != 0:
        q3.bail("the control login did not work, so no row below can be believed")
    fd, _r = w.open4("zzdir")
    fs, _r2 = w.open4("zzsec")
    fb, _r3 = w.open4("zzbig")
    row("H0b the directory file zzdir, the dynamic file zzsec and zzbig open (three file numbers)", None not in (fd, fs, fb), repr((fd, fs, fb)))
    if None in (fd, fs, fb):
        q3.bail("a file did not open")
    dirpath = os.path.join(q3.BOX, "user_accounts", "zzad", "zzdir")

    def wr(fno, rid, data):
        rid_b = rid if isinstance(rid, bytes) else rid.encode("latin-1")
        return w.req(16, struct.pack("<hh", fno, len(rid_b)) + rid_b + data, shown="write %r (%d bytes)" % (rid, len(data)))

    def rd(fno, rid):
        rid_b = rid if isinstance(rid, bytes) else rid.encode("latin-1")
        return w.req(6, struct.pack("<h", fno) + rid_b, shown="read %r" % (rid,))
    r = wr(fd, "d1", b"alpha\xfebeta")
    row("H1 a record of two fields (alpha, field mark, beta) is written to the DIRECTORY file (OK)", r is not None and r[0] == 0, repr(r))
    try:
        with open(os.path.join(dirpath, "d1"), "rb") as f:
            disk = f.read()
    except OSError as ex:
        disk = None
        say("      [evidence] the file %s/d1 cannot be read: %s" % (dirpath, ex))
    say("      [evidence] on the DISK the directory file's record d1 holds %r" % (disk,))
    row("H2 ...and on the disk it is TEXT, one field to a line: alpha and beta each on a line of their own (the field mark became a line end)",
        disk is not None and disk.split(b"\n")[:2] == [b"alpha", b"beta"], repr(disk))
    r = rd(fd, "d1")
    row("H3 ...and it reads back over the wire as the same two fields (alpha, field mark, beta)", r is not None and r[0] == 0 and r[2] == b"alpha\xfebeta", repr(r))
    with open(os.path.join(dirpath, "d2"), "wb") as f:
        f.write(b"x\r\ny\r\n")
    r = rd(fd, "d2")
    say("      [evidence] a file planted on the disk as 'x CR LF y CR LF' reads over the wire as %r" % (r and r[2],))
    # 19 Oct 26 (verifier, finish 2): this row passed whether the CR was kept or dropped (it stripped the CR before comparing), while User page 42 says the CR is KEPT.  It now asserts what was
    # measured on 19 Oct 26 (x CR, field mark, y CR), so a change in either direction fails it and the page.
    row("H4 a directory file whose lines end CR LF is read as two fields with the CR KEPT at the end of each (what User page 42 says; measured 19 Oct 26): x CR, field mark, y CR",
        r is not None and r[0] == 0 and r[2] == b"x\r\xfey\r", repr(r))
    r = wr(fs, "AbC", b"mixed")
    r2 = rd(fs, "abc")
    row("H5 a DYNAMIC file made today folds the case of ids: a record written as AbC is read as abc", r is not None and r[0] == 0 and r2 is not None and r2[0] == 0 and r2[2] == b"mixed", repr((r, r2)))
    r3 = rd(fd, "D1")
    say("      [evidence] a read of D1 from the directory file (written as d1) answers error %r data %r" % (r3 and r3[0], r3 and r3[2]))
    r3b = rd(fd, "d1")
    row("H5b a directory file keeps ids as given (User page 42): D1 is NOT found (error ELSE 2, no data) although d1 is - the read of d1 right after still gives the two fields",
        r3 is not None and r3[0] == 2 and r3[2] == b"" and r3b is not None and r3b[0] == 0 and r3b[2] == b"alpha\xfebeta", repr((r3, r3b)))
    for label, size in (("1 MB", 1024 * 1024), ("20 MB", 20 * 1024 * 1024)):
        body = (b"0123456789abcdef" * (size // 16))
        r = wr(fb, "big", body)
        r2 = rd(fb, "big")
        row("H6 a record of %s is written and read back over the wire byte for byte (the server accepts a request of that size and returns the whole record)" % label,
            r is not None and r[0] == 0 and r2 is not None and r2[0] == 0 and r2[2] == body, repr((r and r[:2], r2 and r2[:2], r2 and len(r2[2]))))
    w.close()


# MUTANTS (K8g, 19 Oct 26).  --mutant=NAME takes one rule of request 29 out of the SANDBOX's copy of apisrvr (never the tree: the base is the tree's file, rewritten and
# recompiled each time, and put back at the end) and runs sections A to E.  THE ROWS THAT MUST FAIL ARE LISTED HERE, WRITTEN BEFORE THE FIRST RUN, and the run says whether the
# rows that failed are exactly those: a mutant that fails fewer rows is a rule no row guards, one that fails more is a row that guards the wrong thing.
#   name                 the text of apisrvr that is changed, the change                                                      the rows that must fail, and nothing else
MUTANTS = {
    "entry-group": ("if not(is_grp_member(@logname, ent.rec<ACC$GROUP>)) then", "if 0 then", ("C1", "C3", "C3a")),            # the membership rule (shared with request 3: C1 sees it too)
    "entry-suspended": ("if ent.suspended then", "if 0 then", ("C2", "C4", "C4a")),                                              # the suspended rule (shared with request 3: C2)
    "register": ("if not(net.found) then", "if 0 then", ("C5a",)),                                                               # a record is required: the empty record is then refused by the OTHER rule, so only the reason shows
    "netgate": ("if not(upcase(trim(net.rec<ACC$NET>)) = 'YES' or (downcase(@logname) = 'sdsys' and net.acct = 'sdsys')) then", "if 0 then", ("D1", "D1a")),
    "sdclient": ("if config('SDCLIENT') # 0 then", "if 0 then", ("E2",)),                                                       # request 29's own SDCLIENT test (vb.open.sdnet; request 4 has its own)
    # 19 Oct 26 (verifier finding, finish 2): the BLOCKING branch of request 32 with the stale loop variable of K8a put back, and nothing else.  Section F runs after A to E for this one
    # (F_MUTANTS); A to E must all pass.  The rows of F that must fail are listed here BEFORE the first run: F11 (the request is answered at once, on the file S2 opened last), F13 (so
    # there is nothing left to answer), F14 and F15 (the lock is on zzsec3, not zzsec), F18 and F19 (the same for the wait on a free file).  F10, F12, F16 and F17 pass with it.
    "filelock-wait": ("filelock files(fno)   ;* 19 Oct 26 (K8a): was files(i), the stale loop variable of the last open, as vb.clearfile's was",
                      "filelock files(i)   ;* MUTANT: the stale index on the wait branch", ("F11", "F13", "F14", "F15", "F18", "F19")),
}
F_MUTANTS = ("filelock-wait",)         # the mutants judged by section F, which runs for them after A to E
TREE_APISRVR = os.path.join(os.path.dirname(HERE), "sdsys", "gpl.bp", "apisrvr")


def set_apisrvr(old=None, new=None):
    """Write the sandbox's gpl.bp/apisrvr from the TREE's, with `old` replaced by `new` when given (it must occur exactly once), and compile it there as the administrator."""
    with open(TREE_APISRVR, encoding="utf-8", errors="replace") as f:
        src = f.read()
    if old is not None:
        if src.count(old) != 1:
            q3.bail("mutant: the text to change is found %d times, not once: %r" % (src.count(old), old[:70]))
        src = src.replace(old, new)
    with open(os.path.join(q3.SYS, "gpl.bp", "apisrvr"), "w", encoding="utf-8") as f:
        f.write(src)
    out = q3.adm(["BASIC gpl.bp apisrvr"], internal=True)
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        q3.bail("the sandbox's apisrvr did not compile:\n" + "\n".join(out[-8:]))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    mutant = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mutant=")), None)
    if len(args) != 1 or (mutant is not None and mutant not in MUTANTS):
        q3.bail("usage: sandbox-req29.py <dir> [--build] [--mutant=%s]" % "|".join(MUTANTS))
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
    if mutant is not None:
        old, new_, kills = MUTANTS[mutant]
        set_apisrvr(old, new_)
        say("\nsandbox-req29: MUTANT %s: the sandbox's apisrvr has %r changed to %r; the rows that must fail, and nothing else: %s" % (mutant, old[:70], new_, ", ".join(kills)))

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
        off = audit_off()
        row("B0a the audit file can be read (a row that needs a line from it fails, it does not pass for want of one)", off is not None, repr(off))
        fno, r = w.open29("zzad;zzsec")
        back = w.read_back(fno) if fno is not None else None
        row("B1 CONTROL: request 29 'zzad;zzsec' (a member's own account, NET gate on) returns a file number and READ of k1 gives the planted %r" % planted["zzad"],
            fno is not None and back == planted["zzad"], repr((fno, back, r)))
        new = audit_new(off)
        row("B2 CONTROL OF THE AUDIT ROWS: the good open above added NO refusal to the audit trail (no 'request=29' line, no 'account refused' line) - a reading that matched every line would "
            "fail here", new is not None and "request=29" not in new and "account refused" not in new, repr(new))
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

        off = audit_off()
        fno, r = w.open29("zzab;zzsec")
        back = w.read_back(fno) if fno is not None else None
        new = audit_new(off)
        say("      [evidence] on the disk zzab's file holds %r (planted and read back in preparation); request 29 'zzab;zzsec' gave file number %r and READ k1 gave %r" % (planted["zzab"], fno, back))
        row("C3 request 29 'zzab;zzsec' (an account the user is NOT a member of): refused - no file number, and the record %r is not read" % planted["zzab"],
            fno is None and back != planted["zzab"], "OPENED fno %r and READ %r  <- the claim is true" % (fno, back))
        row("C3a ...and the refusal is on the audit trail, in the words of request 3's refusal: 'account refused branch=4 not.in.group user=%s group=%s account=zzab' (the CALLER sees only "
            "10003; the administrator sees why)" % (me, NOT_MEMBER_GROUP),
            audit_has(new, r"account refused branch=4 not\.in\.group user=%s group=%s account=zzab$" % (re.escape(me), re.escape(NOT_MEMBER_GROUP))), repr(new))
        off = audit_off()
        fno, r = w.open29("zzac;zzsec")
        back = w.read_back(fno) if fno is not None else None
        new = audit_new(off)
        row("C4 request 29 'zzac;zzsec' (a SUSPENDED account, the user a member): refused", fno is None and back != planted["zzac"], "OPENED fno %r and READ %r" % (fno, back))
        row("C4a ...audited as 'account refused branch=2 suspended account=zzac'", audit_has(new, r"account refused branch=2 suspended account=zzac$"), repr(new))
        off = audit_off()
        fno, r = w.open29(path_b + ";zzsec")
        back = w.read_back(fno) if fno is not None else None
        new = audit_new(off)
        row("C5 request 29 with the account given as a PATH (%s;zzsec): refused - a path names no register record, so nothing says who may enter it" % path_b,
            fno is None and back != planted["zzab"], "OPENED fno %r and READ %r" % (fno, back))
        row("C5a ...audited as 'api refused request=29 reason=no register record user=%s account=<the path, lower case>' - the register rule, not the membership rule that would refuse an "
            "empty record next" % me,
            audit_has(new, r"api refused request=29 reason=no register record user=%s account=%s$" % (re.escape(me), re.escape(path_b.lower()))), repr(new))
        off = audit_off()
        fno, r = w.open29("zzad;zzsec")
        back = w.read_back(fno) if fno is not None else None
        new = audit_new(off)
        row("C6 CONTROL AFTER THE REFUSALS: 'zzad;zzsec' still opens and reads %r (so the refusals above are the rule and not a broken session)" % planted["zzad"],
            fno is not None and back == planted["zzad"], repr((fno, back)))
        row("C6a CONTROL OF THE AUDIT ROWS: that good open added no refusal line", new is not None and "request=29" not in new and "account refused" not in new, repr(new))
        w.close()

        # ------------------------------------------------------------------------------------------------------------------------
        say("\n--- D. the NET gate: a member of zzaa, whose NET gate is off (register field 15 'no'), asks for its OWN file ---------------")
        w = Wire("D")
        e, t = w.login("zzaa")
        row("D0 a member signs on to zzaa (OK)", e == 0, repr((e, t)))
        off = audit_off()
        fno, r = w.open29("zzaa;zzsec")
        back = w.read_back(fno) if fno is not None else None
        new = audit_new(off)
        row("D1 request 29 'zzaa;zzsec' with the account's NET gate off: refused (the NET gate is the account's permission to use SDNet files)",
            fno is None and back != planted["zzaa"], "OPENED fno %r and READ %r" % (fno, back))
        row("D1a ...audited as 'api refused request=29 reason=net gate off user=%s account=zzaa'" % me,
            audit_has(new, r"api refused request=29 reason=net gate off user=%s account=zzaa$" % re.escape(me)), repr(new))
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

        # ------------------------------------------------------------------------------------------------------------------------
        if mutant is None or mutant in F_MUTANTS:
            section_f()
        if mutant is None:
            section_g()
            section_h()
    finally:
        q3.restart()
        if mutant is not None:
            set_apisrvr()          # the sandbox's apisrvr is the tree's again
        subprocess.run([sys.executable, q3.TOOL, BOX, "stop"], capture_output=True, text=True, errors="replace", timeout=120)

    say("\nsandbox-req29: %d passed, %d failed" % (q3.passed, q3.failed))
    if mutant is not None:
        want, got = sorted(set(MUTANTS[mutant][2])), sorted(set(FAILED_IDS))
        ok = want == got
        say("sandbox-req29: MUTANT %s: the rows that failed are %s; they had to be exactly %s -> %s" % (mutant, got, want, "KILLED BY ITS OWN ROWS" if ok else "NOT AS EXPECTED"))
        return 0 if ok else 1
    return 1 if q3.failed else 0


if __name__ == "__main__":
    sys.exit(main())
