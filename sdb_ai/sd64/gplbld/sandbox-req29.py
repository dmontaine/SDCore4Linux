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
# 20 Oct 26 dm  S.72b (owner, 20 Oct 2026: of the five S.72 loosenings only RECORDLOCKED() is tightened; request 34 joins gpl.bp/apifilesok's change set, so a files-only login WITHOUT
#               the group sdfileswrite is refused it with message 11521 and the audit line `api refused request=34 route=sdfiles write=off user=<name>`).  ***THIS SUITE'S LOGIN IS NOT A
#               FILES-ONLY LOGIN***: the local door (request 25, then 3) never sets apisrvr's files.only, which only the SCRAM final does for a user who is in sdfiles and not in sdapi (needs
#               TLS, a credential and the Linux groups: the VM witness).  So no row of F (22, 27, 28, 32 ask request 34) can flip: they are the sdapi login, which the change leaves UNTOUCHED, and
#               they stay green.  What this suite CAN do is run the REAL gate for request 34: (I) the sandbox's apisrvr gets a TEST DEVICE - two lines before the gate that make request 27 mark the
#               calling session files-only and request 28 mark it files-only AND in the group (it sets the two common variables the SCRAM final sets, nothing else) - so the production gate, the
#               production !apifilesok, message 11521/11480 and the audit line are what answer.  Three sessions of one account: H stays an ordinary session holding a record lock, N is marked
#               files-only without the group, G files-only with it.  The rows were written from the spec and run on the unchanged tree (f64e7ff) first: 135 passed, 4 failed - exactly I4, I5, I6
#               and I13, because request 34 was SERVED to N (code -2 with H's user number in STATUS(), no refusal, no audit line); on the S.72b tree 139 passed, 0 failed.
#               --mutant=wall-gone (the sandbox's apifilesok loses `files.chg := '34,'`: I4 I5 I6 I13), wall-too-wide (the gate also takes an ordinary login's request 34: I1a I2 I6 I8 I10
#               I12 I13) and group-ignored (the gate passes write flag 0 whatever the session: I9 I10 I10a I13) are judged by section I (after A to E, which must pass); each failed exactly the
#               rows listed with it.  Not covered: files.only being set by the SCRAM final from the Linux groups (the VM witness).
# 20 Oct 26 dm  S.72 (QMNet parity, tier B).  (F) F20 to F49 MEASURE what netfake.py's requests 32 and 33 (FILELOCK, FILEUNLOCK) now claim about the real server; they pass on the
#               server as it was, they are the controls that hold the fake to it.  FILEUNLOCK answers SV$OK with STATUS() 0 (the holder's), 3012 (nobody holds the lock) or 3011 (another
#               session does, and the lock stays); a no-wait FILELOCK that finds the file locked answers LOCKED with STATUS() the holder's user number (found by request 50, getvar USERNO)
#               - whether the holder has the file lock or a record lock in the file; a file lock makes another session's record lock (30, READU, READL) LOCKED with the same number and
#               RECORDLOCKED (34) answer 3 to the holder and -3 to the other session; the lock belongs to the file NUMBER that took it (request 5 on another number of the same file
#               leaves it, on that number lets it go; a second FILELOCK through another number succeeds and moves nothing; FILEUNLOCK goes by the session); RELEASE (15) with an empty id
#               through that number, or with file number 0, lets it go and with one record's id does not; a session that quits (1) or whose pipes just close lets it go.  Request bytes
#               are printed with every request that is named in words (Wire.req).  The mutant list is untouched: the new rows use only the wait flag 0 and none of them is a row the
#               filelock-wait mutant kills (run 20 Oct 26 with the new rows present: 73 passed, 6 failed, exactly F11 F13 F14 F15 F18 F19).  119 passed, 0 failed on the unchanged server
#               (36 new rows, F20 to F49 with F38 to F40 twice, once for each order of the two file numbers).
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
import shutil
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
        sent = "" if shown is None else " [sent bytes %s]" % data[:40].hex(" ")       # 20 Oct 26 (S.72): a row that names the request in words shows the bytes that crossed as well
        try:
            err, st, body = self._answer(secs)
        except (TimeoutError, EOFError) as e:
            say("      %s request %d %r%s -> %s" % (self.tag, ptype, what, sent, e))
            return None
        say("      %s request %d %r%s -> error %d (%s) status %d data %r" % (self.tag, ptype, what, sent, err, SV.get(err, "?"), st, body[:70]))
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

    # ---- S.72 (20 Oct 26): the requests around a file lock, each printed with the bytes sent (req) ----
    def userno(self):
        """Request 50 (getvar) 'USERNO': this session's @userno, the number the kernel knows it by (a lock holder is reported by it).  None when the answer is not a number."""
        r = self.req(50, "USERNO", shown="getvar @USERNO")
        return int(r[2]) if r is not None and r[0] == 0 and r[2].isdigit() else None

    def reclocked(self, fno, rid):
        """Request 34: fno and the id.  Returns (RECORDLOCKED() code as the signed 32 bit integer the 4 data bytes hold or None, STATUS(), the reply)."""
        r = self.req(34, struct.pack("<h", fno) + rid, shown="recordlocked fno %r id %r" % (fno, rid))
        code = struct.unpack("<i", r[2])[0] if r is not None and r[0] == 0 and len(r[2]) == 4 else None
        return code, (r[1] if r is not None else None), r

    def lockrec(self, fno, flags, rid):
        """Request 30: fno, flags (1 = update lock, 2 = no wait: so 3 is an update lock with a LOCKED clause), the id."""
        return self.req(30, struct.pack("<hh", fno, flags) + rid, shown="lock record fno %r flags %d id %r" % (fno, flags, rid))

    def readlock(self, fno, rid, update=True):
        """Request 9 (READU with a LOCKED clause) or 7 (READL with a LOCKED clause): fno and the id."""
        return self.req(9 if update else 7, struct.pack("<h", fno) + rid, shown="%s fno %r id %r" % ("readu" if update else "readl", fno, rid))

    def release(self, fno, rid=b""):
        """Request 15: fno and the id; the id empty releases the file's locks, fno 0 every lock of the session."""
        return self.req(15, struct.pack("<h", fno) + rid, shown="release fno %r id %r" % (fno, rid))

    def close_fno(self, fno):
        """Request 5: close the file number."""
        return self.req(5, struct.pack("<h", fno), shown="close fno %r" % (fno,))

    def end(self, how):
        """End the session and wait until its process is gone, so that whatever the end releases is released when this returns.  how 'quit': request 1, then the pipes closed;
        'pipe': the pipes closed with no request 1 (the server reads end of file).  Returns True when the process ended on its own within 20 seconds (it is killed otherwise)."""
        if how == "quit":
            try:
                self.req(1)
            except OSError:
                pass
        else:
            say("      %s the pipes are closed with no quit request" % self.tag)
        for fd in (self.rd, self.wr):
            try:
                os.close(fd)
            except OSError:
                pass
        try:
            self.p.wait(timeout=20)
            return True
        except subprocess.TimeoutExpired:
            self.p.kill()
            self.p.wait()
            return False

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


def register(name, group, susp="", net="yes", os_exec="no"):
    path = os.path.join(q3.BOX, "user_accounts", name)
    # 1 path, 3 group, 5 suspended, 7 sh, 8 os.exec, 9 sd.accounts, 10-12 the edit gates, 13-14 shared (blank), 15 net
    fields = [path, "", group, "", susp, "", "no", os_exec, "no", "yes", "yes", "yes", "", "", net]
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
    section_f_s72()


def section_f_s72():
    """F20 to F49. S.72 (20 Oct 26): the facts gplbld/netfake.py's FILELOCK / FILEUNLOCK (requests 32 and 33) claim about the REAL server, MEASURED, so that the fake the client
    rows run against is held to the server.  Written from the spec (the S.72 spec, gpl.bp/apisrvr vb.filelock and vb.fileunlock, gplsrc/op_lock.c op_filelock() and
    op_flunlock(), op_dio1.c dio_close(), op_lock.c unlock_record()) BEFORE the first run; every row passes on the unchanged server - these are measurements, and a row that
    fails means the spec is wrong.  Every request is printed with the bytes sent and the reply.  A user number is found by request 50 (getvar) 'USERNO' on each session (F21) and is
    what every STATUS() below is compared with; request 34's owner number for a record lock (F32) is a second route to the same number.  Every fact has a CONTROL row: the same
    request answered differently when nothing is in the way, so a server that answered LOCKED (or OK) to everything fails there.  Only the form with the wait flag 0 is used (the
    S.72 client never sends the other): the F10 to F19 rows above hold the blocking form, and the mutant filelock-wait puts the stale index on that branch only, so none of
    these rows is touched by it.  (20 Oct 26, S.72b: the sessions here are the LOCAL door, not a files-only login, so the wall that now refuses request 34 to a files-only login without the
    write group does not reach F22, F27, F28 and F32: they are the sdapi login and stay as they were.  Section I runs request 34 through the real files-only gate.)"""
    say("\n  -- S.72 (20 Oct 26): FILELOCK / FILEUNLOCK / RECORDLOCKED around a file lock, measured on the real server (what netfake.py claims) --")

    def ok(r):
        return r is not None and r[0] == 0

    def locked_by(r, u):
        return r is not None and r[0] == 4 and r[1] == u

    s1, s2 = Wire("F3"), Wire("F4")
    e1, t1 = s1.login("zzad")
    e2, t2 = s2.login("zzad")
    row("F20 two fresh members sign on to zzad (OK both): the holder S1 and the rival S2 - the earlier sessions ended, so no file lock is held by anybody", e1 == 0 and e2 == 0, repr(((e1, t1), (e2, t2))))
    if e1 != 0 or e2 != 0:
        q3.bail("the control logins did not work, so no row below can be believed")
    u1, u2 = s1.userno(), s2.userno()
    row("F21 the user numbers, asked of each session by request 50 (getvar USERNO): two different positive integers - the numbers the rows below expect in STATUS()",
        u1 is not None and u2 is not None and u1 > 0 and u2 > 0 and u1 != u2, repr((u1, u2)))
    if u1 is None or u2 is None:
        q3.bail("request 50 gave no user number, so no STATUS() below can be compared")
    fa1, fa2 = s1.open4("zzsec")[0], s2.open4("zzsec")[0]
    fb1, fb2 = s1.open4("zzsec2")[0], s2.open4("zzsec2")[0]
    if None in (fa1, fa2, fb1, fb2):
        q3.bail("a file did not open, so no lock row can be believed")

    # ---- the null state, then FILEUNLOCK when nobody holds the lock
    c1, c2 = s1.reclocked(fa1, b"k1"), s2.reclocked(fa2, b"k1")
    row("F22 CONTROL (the null state): nothing is locked - RECORDLOCKED of zzsec/k1 is code 0 with STATUS() 0 for both sessions, so a 'held' or 'locked' answer below is not a pass over nothing",
        c1[:2] == (0, 0) and c2[:2] == (0, 0), repr((c1[:2], c2[:2])))
    r = s1.fileunlock(fa1)
    row("F23 FILEUNLOCK when nobody holds the file lock: SV$OK (error 0) with STATUS() 3012 (ER$NLK), no data", r is not None and r[0] == 0 and r[1] == 3012 and r[2] == b"", repr(r))

    # ---- FILELOCK, the holder's number in the LOCKED reply, FILEUNLOCK 3011
    r = s1.filelock(fa1, 0)
    row("F24 S1 FILELOCK zzsec, wait 0, nobody in the way: SV$OK (error 0, no data)", ok(r) and r[2] == b"", repr(r))
    r = s1.filelock(fa1, 0)
    row("F24a S1 asks again for the lock it already holds: SV$OK (op_filelock: file_lock is mine)", ok(r) and r[2] == b"", repr(r))
    r = s2.filelock(fa2, 0)
    row("F25 S2 FILELOCK zzsec, wait 0, while S1 holds it: SV$LOCKED (error 4), no data, STATUS() = S1's user number %r (from request 50) and not S2's own %r" % (u1, u2),
        locked_by(r, u1) and r[2] == b"" and r[1] != u2, repr(r))
    r = s2.fileunlock(fa2)
    row("F26 S2 FILEUNLOCK zzsec while S1 holds the lock: SV$OK (error 0) with STATUS() 3011 (ER$LCK), no data", r is not None and r[0] == 0 and r[1] == 3011 and r[2] == b"", repr(r))
    r = s2.filelock(fa2, 0)
    row("F26a ...and the lock stayed S1's: S2 FILELOCK is still LOCKED with STATUS() %r" % u1, locked_by(r, u1), repr(r))

    # ---- RECORDLOCKED while S1 holds the file lock
    c1, c2 = s1.reclocked(fa1, b"k1"), s2.reclocked(fa2, b"k1")
    row("F27 RECORDLOCKED zzsec/k1 while S1 holds the file lock: code 3 (my file lock) to S1 and code -3 (another user's file lock) to S2, STATUS() = S1's number %r for both" % u1,
        c1[:2] == (3, u1) and c2[:2] == (-3, u1), repr((c1[:2], c2[:2])))
    c1, c2 = s1.reclocked(fb1, b"k1"), s2.reclocked(fb2, b"k1")
    row("F28 CONTROL: RECORDLOCKED zzsec2/k1 (a file nobody locked) is code 0 with STATUS() 0 for both - the file lock is on zzsec only", c1[:2] == (0, 0) and c2[:2] == (0, 0), repr((c1[:2], c2[:2])))

    # ---- the file lock blocks another session's record locks
    rl = s2.lockrec(fa2, 3, b"k1")
    ru = s2.readlock(fa2, b"k1", True)
    rr = s2.readlock(fa2, b"k1", False)
    row("F29 S1's file lock blocks S2's record lock: request 30 (flags 3, update, no wait), READU (9) and READL (7) on zzsec/k1 are each SV$LOCKED with STATUS() = S1's number %r" % u1,
        locked_by(rl, u1) and locked_by(ru, u1) and locked_by(rr, u1), repr((rl, ru, rr)))
    rc = s2.lockrec(fb2, 3, b"k1")
    row("F30 CONTROL: the same request 30 (flags 3) on zzsec2/k1, a file nobody has locked, is granted (error 0)", ok(rc), repr(rc))
    if ok(rc):
        s2.release(fb2, b"k1")
    r = s1.fileunlock(fa1)
    row("F31 S1 FILEUNLOCK zzsec (it holds it): SV$OK (error 0) with STATUS() 0, no data", r is not None and r[0] == 0 and r[1] == 0 and r[2] == b"", repr(r))
    rl = s2.lockrec(fa2, 3, b"k1")
    cs2, cs1 = s2.reclocked(fa2, b"k1"), s1.reclocked(fa1, b"k1")
    row("F32 CONTROL for F29: with the file lock let go the same request 30 by S2 is granted (error 0); RECORDLOCKED then says code 2 (my update lock) to S2 and -2 (another user's update lock) to "
        "S1, STATUS() = S2's number %r for both" % u2, ok(rl) and cs2[:2] == (2, u2) and cs1[:2] == (-2, u2), repr((rl, cs2[:2], cs1[:2])))

    # ---- a record lock held by ANOTHER user blocks the file lock; the user's own does not
    r = s1.filelock(fa1, 0)
    row("F33 S2 holds an UPDATE lock on zzsec/k1: S1 FILELOCK zzsec (wait 0) is SV$LOCKED (error 4), no data, STATUS() = S2's number %r - the owner of the record lock" % u2,
        locked_by(r, u2) and r[2] == b"", repr(r))
    s2.release(fa2, b"k1")
    r = s1.filelock(fa1, 0)
    row("F34 CONTROL: S2 lets the record lock go (request 15, id k1) and the same FILELOCK by S1 is granted (error 0)", ok(r), repr(r))
    s1.fileunlock(fa1)
    rr = s2.readlock(fa2, b"k1", False)
    r = s1.filelock(fa1, 0)
    row("F35 S2 holds a READ lock on zzsec/k1 (READL, error 0): S1 FILELOCK zzsec is SV$LOCKED with STATUS() = S2's number %r too" % u2, ok(rr) and locked_by(r, u2), repr((rr, r)))
    s2.release(fa2, b"k1")
    ru = s1.readlock(fa1, b"k1", True)
    r = s1.filelock(fa1, 0)
    row("F36 S1's OWN record lock does not block its own file lock: S1 READU zzsec/k1 (error 0) then FILELOCK zzsec is granted (error 0)", ok(ru) and ok(r), repr((ru, r)))
    s1.fileunlock(fa1)
    s1.release(fa1, b"k1")
    r = s2.filelock(fa2, 0)
    row("F36a ...and with S1's record lock and file lock both let go, S2 FILELOCK zzsec is granted (the state before the next rows is the null state)", ok(r), repr(r))
    s2.fileunlock(fa2)

    # ---- the lock belongs to the FILE NUMBER that took it (op_dio1.c dio_close): S1 has zzsec open twice
    def reopen(w):
        a_, b_ = w.open4("zzsec")[0], w.open4("zzsec")[0]
        if None in (a_, b_) or a_ == b_:
            q3.bail("zzsec did not open twice with two file numbers, so no close row can be believed")
        return a_, b_
    x1, x2 = reopen(s1)
    row("F37 S1 opens zzsec twice and is given two different file numbers (%r and %r)" % (x1, x2), x1 != x2, repr((x1, x2)))
    for first, second, label, sx in ((x1, x2, "the first, then through the second", ""), (x2, x1, "the second, then through the first", "b")):      # F38 to F40, then F38b to F40b
        ra = s1.filelock(first, 0)
        rb = s1.filelock(second, 0)
        rv = s2.filelock(fa2, 0)
        row("F38%s S1 FILELOCK through %s file number of zzsec: both SV$OK (the second finds the lock already its own); S2 is SV$LOCKED with STATUS() %r" % (sx, label, u1),
            ok(ra) and ok(rb) and locked_by(rv, u1), repr((ra, rb, rv)))
        rc = s1.close_fno(second)
        rv = s2.filelock(fa2, 0)
        row("F39%s S1 closes the file number that did NOT take the lock (request 5, number %r): SV$OK, and the lock is still S1's - S2 is SV$LOCKED with STATUS() %r" % (sx, second, u1),
            ok(rc) and locked_by(rv, u1), repr((rc, rv)))
        rc = s1.close_fno(first)
        rv = s2.filelock(fa2, 0)
        row("F40%s S1 closes the file number that TOOK it (request 5, number %r): SV$OK, and the lock is released - S2 FILELOCK is granted (error 0)" % (sx, first), ok(rc) and ok(rv), repr((rc, rv)))
        s2.fileunlock(fa2)
        x1, x2 = reopen(s1)
    ra = s1.filelock(x1, 0)
    rx = s1.fileunlock(x2)
    rv = s2.filelock(fa2, 0)
    row("F41 S1 FILELOCK through one file number and FILEUNLOCK through the OTHER (the same file): SV$OK with STATUS() 0 - an unlock goes by the user, not the file number - and S2 then gets "
        "the lock (error 0)", ok(ra) and rx is not None and rx[:2] == (0, 0) and ok(rv), repr((ra, rx, rv)))
    s2.fileunlock(fa2)
    ra = s1.filelock(x2, 0)
    rc = s1.close_fno(x1)
    rv = s2.filelock(fa2, 0)
    row("F42 ...and S1 locking again through the second number after that unlock, closing the FIRST number leaves the lock held (S2 is SV$LOCKED with STATUS() %r): it belongs to the number "
        "that took it last" % u1, ok(ra) and ok(rc) and locked_by(rv, u1), repr((ra, rc, rv)))
    rc = s1.close_fno(x2)
    rv = s2.filelock(fa2, 0)
    row("F43 ...and closing the second number lets it go: S2 FILELOCK is granted (error 0)", ok(rc) and ok(rv), repr((rc, rv)))
    s2.fileunlock(fa2)

    # ---- request 15, RELEASE: file number 0, an empty id, one record's id (what the fake's r_release does since S.72)
    y1, y2 = reopen(s1)
    ra = s1.filelock(y1, 0)
    rr = s1.release(y2, b"")
    rv = s2.filelock(fa2, 0)
    row("F44 RELEASE of zzsec (empty id, request 15) through a file number that did NOT take the lock: SV$OK, and the file lock is still S1's - S2 is SV$LOCKED with STATUS() %r" % u1,
        ok(ra) and ok(rr) and locked_by(rv, u1), repr((ra, rr, rv)))
    rr = s1.release(y1, b"")
    rv = s2.filelock(fa2, 0)
    row("F45 RELEASE of zzsec (empty id) through the file number that TOOK the lock: SV$OK, the file lock is let go - S2 FILELOCK is granted (error 0)", ok(rr) and ok(rv), repr((rr, rv)))
    s2.fileunlock(fa2)
    ra = s1.filelock(y1, 0)
    rr = s1.release(y1, b"k1")
    rv = s2.filelock(fa2, 0)
    row("F46 RELEASE of one record's id (zzsec/k1) does not touch the file lock: SV$OK, and S2 is still SV$LOCKED with STATUS() %r" % u1, ok(ra) and ok(rr) and locked_by(rv, u1), repr((ra, rr, rv)))
    rb2 = s2.filelock(fb2, 0)
    rb1 = s1.filelock(fb1, 0)
    rr = s1.release(0, b"")
    rv = s2.filelock(fa2, 0)
    rb1b = s1.filelock(fb1, 0)
    row("F47 RELEASE with file number 0 lets go of every file lock S1 holds (zzsec: S2 is granted it) and of nobody else's (S2 holds zzsec2 first: S1 is SV$LOCKED on it with STATUS() %r before "
        "and after)" % u2, ok(rb2) and locked_by(rb1, u2) and ok(rr) and ok(rv) and locked_by(rb1b, u2), repr((rb2, rb1, rr, rv, rb1b)))
    s2.fileunlock(fa2)
    s2.fileunlock(fb2)

    # ---- the end of the session: a quit request, then the pipes closing with no quit
    y1, y2 = reopen(s1)
    ra = s1.filelock(y1, 0)
    rv = s2.filelock(fa2, 0)
    gone = s1.end("quit")
    rv2 = s2.filelock(fa2, 0)
    row("F48 S1 holds the file lock and ends with a quit request (request 1; its process ended: %s): S2 was SV$LOCKED with STATUS() %r before and is granted the lock (error 0) after"
        % (gone, u1), ok(ra) and locked_by(rv, u1) and gone and ok(rv2), repr((ra, rv, gone, rv2)))
    s2.fileunlock(fa2)
    s3 = Wire("F5")
    e3, t3 = s3.login("zzad")
    z3 = s3.open4("zzsec")[0]
    u3 = s3.userno()
    ra = s3.filelock(z3, 0) if z3 is not None else None
    rv = s2.filelock(fa2, 0)
    gone = s3.end("pipe")
    rv2 = s2.filelock(fa2, 0)
    row("F49 a session whose pipes close with no quit request (its process ended: %s) lets go of its file lock too: S2 was SV$LOCKED with STATUS() %r before and is granted it after"
        % (gone, u3), e3 == 0 and ok(ra) and u3 is not None and locked_by(rv, u3) and gone and ok(rv2), repr((e3, ra, rv, gone, rv2)))
    s2.fileunlock(fa2)
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


PLANT_OUT = "outside every account"
PLANT_SIB = "next door, and a prefix is not inside"
X_POINTER_ERR = 3035      # ER$PERM: the status the os rule answers with (error ELSE), as DIR / OPENSEQ answer a path they may not reach


def x_pointer_program(acc, out, sib):
    """The text of the internal program that writes the F-pointers of section X into the VOC of the account whose directory is ACC (the VOC is the administrator's: an ordinary session
    of the account cannot write it).  Returns (the text, [(id, path, dictionary path)])."""
    pointers = [
        ("zzpabs", out, ""),                      # an absolute path outside every account directory
        ("zzprel", "../../zzoutside", ""),        # a relative path that climbs out of the account (acc/../../zzoutside is the same directory)
        ("zzplnk", "zzlink", ""),                 # a name inside the account that is a symbolic link to the outside directory
        ("zzpsib", sib, ""),                      # the directory next to the account whose name begins with the account's own name
        ("zzpsys", "@SDSYS/newvoc", ""),          # a system file: the stock VOC's own pointers lead there (newvoc, syscom)
        ("zzpdic", "zzsec", out),                 # the data half is the account's own file, the DICTIONARY half is outside
        ("zzpin", "zzsec", ""),                   # the control: a file of the account, by a relative path
        ("zzpinab", acc + "/zzsec", ""),          # the control: the same file by an absolute path inside the account
    ]
    lines = ["$internal", "   openpath '%s/voc' to v else crt 'FIX no voc' ; stop" % acc]
    for pid, path, dpath in pointers:
        lines.append("   write 'F':@fm:'%s':@fm:'%s' to v, '%s'" % (path, dpath, pid))
    lines += ["   crt 'FIX done'", "end", ""]
    return "\n".join(lines), pointers


def section_x():
    """X. a VOC pointer OUTSIDE the account (20 Oct 26, the owner delegated the choice: close it).  Request 29 opens the file the account's VOC names with `openpath` from an
    internal program, so the OS switch was never asked of a path that leads out of the account (DIR, OPENSEQ, the OSCOPY verbs and every OPEN in a program ask it).  Two accounts, the
    same eight F-pointers in each: zzae holds NO os switch, zzaf holds it.  The oracle is the disk: the planted record in the outside directory, read back over the wire."""
    me = getpass.getuser()
    say("\n--- X. an F-pointer OUTSIDE the account: refused unless the account holds the os switch (S.63 rule, closed in request 29 on 20 Oct 26) ------------")
    if not q3.restart("NETFILES=2"):
        q3.bail("SD does not start with NETFILES=2 in sd.conf")
    box = q3.BOX
    out = os.path.join(box, "zzoutside")
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    put(os.path.join(out, "k1"), PLANT_OUT)
    for n in ("zzae", "zzaf"):
        q3.build_account(n)
        o = q3.plain(n, ["CREATE.FILE zzsec DYNAMIC", "RUN bp zzmk " + n])
        if tag(o, "MK") != ["secret of " + n]:
            q3.bail("the fixture file of %s does not hold the planted record: %r" % (n, o[-4:]))
    for n, os_exec in (("zzae", "no"), ("zzaf", "yes")):
        acc = os.path.join(box, "user_accounts", n)
        sib = acc + "-sib"
        shutil.rmtree(sib, ignore_errors=True)
        os.makedirs(sib)
        put(os.path.join(sib, "k1"), PLANT_SIB)
        link = os.path.join(acc, "zzlink")
        if os.path.lexists(link):
            os.remove(link)
        os.symlink(out, link)
        text, pointers = x_pointer_program(acc, out, sib)
        put(os.path.join(q3.SYS, "bp", "zzptrfix"), text)
        o = q3.adm(["BASIC bp zzptrfix", "RUN bp zzptrfix"], internal=True)
        row("X0 %s: the eight F-pointers are written into its VOC by an internal program" % n, has(o, r"^FIX done$"), repr(o[-4:]))
        if not has(o, r"^FIX done$"):
            q3.bail("the pointers were not written into the VOC of %s, so no row below can be believed" % n)
        register(n, q3.GROUP, net="yes", os_exec=os_exec)
        with open(os.path.join(q3.SYS, "accounts", n), encoding="ascii") as f:
            fields = f.read().split("\n")
        say("    [evidence] register record of %s: field 8 (os) %r, field 15 (net) %r, path %r; outside directory %s holds k1 = %r; link %s -> %s; sibling %s holds k1 = %r"
            % (n, fields[7], fields[14], fields[0], out, open(os.path.join(out, "k1")).read(), link, os.readlink(link), sib, open(os.path.join(sib, "k1")).read()))
        row("X0a %s: the register record says os %r (the row below is only meaningful if it says what this account is meant to be)" % (n, os_exec), fields[7] == os_exec and fields[14] == "yes", repr(fields[:15]))
        if fields[7] != os_exec:
            q3.bail("the register record of %s does not say os %s" % (n, os_exec))

    cases = [    # (what the request names, what it is, the record the disk holds in what it leads to; None: only the file number is judged)
        ("zzpabs", "an absolute path outside every account directory", PLANT_OUT),
        ("zzprel", "a relative path that climbs out of the account (../../zzoutside)", PLANT_OUT),
        ("zzplnk", "a name inside the account that is a symbolic link to the outside directory", PLANT_OUT),
        ("zzpsib", "the directory next to the account whose name begins with the account's own name", PLANT_SIB),
        ("zzpsys", "a system file of the installation (@SDSYS/newvoc)", None),
        ("DICT zzpdic", "a pointer whose DICTIONARY half is outside (its data half is the account's own file)", PLANT_OUT),
    ]
    controls = [    # (what the request names, what it is): inside the account, they must open whatever the os switch says
        ("zzpin", "the account's own file by a relative path"),
        ("zzpinab", "the account's own file by an absolute path inside the account"),
        ("zzpdic", "the data half of the dictionary pointer (the account's own file)"),
    ]

    # ---- zzae: NO os switch -------------------------------------------------------------------------------------------------------
    w = Wire("Xa")
    e, t = w.login("zzae")
    row("X1a a member signs on to zzae (OK)", e == 0, repr((e, t)))
    if e != 0:
        q3.bail("the control login did not work, so no row below can be believed")
    off = audit_off()
    fno, r = w.open29("zzae;zzsec")
    back = w.read_back(fno) if fno is not None else None
    new = audit_new(off)
    row("X1b CONTROL: request 29 'zzae;zzsec' (the account's own file, no pointer) opens and reads 'secret of zzae', and adds no refusal to the audit trail",
        fno is not None and back == "secret of zzae" and new is not None and "request=29" not in new, repr((fno, back, r, new)))
    for i, (name, what, planted) in enumerate(cases):
        off = audit_off()
        fno, r = w.open29("zzae;" + name)
        back = w.read_back(fno) if fno is not None else None
        new = audit_new(off)
        say("      [evidence] request 29 'zzae;%s' (%s): file number %r, READ k1 %r, the disk holds %r" % (name, what, fno, back, planted))
        row("X%d request 29 'zzae;%s' - %s: refused with error ELSE and status %d (permission), no file number, and the planted record is not read" % (2 + i, name, what, X_POINTER_ERR),
            fno is None and r is not None and r[0] == 2 and r[1] == X_POINTER_ERR and (planted is None or back != planted),
            "OPENED fno %r and READ %r  <- the claim is true; reply %r" % (fno, back, r))
        if i in (0, 5):
            row("X%da ...and the refusal is on the audit trail, in lower case: 'api refused request=29 reason=os gate off user=%s account=zzae path=<the path the pointer names>'" % (2 + i, me),
                audit_has(new, r"api refused request=29 reason=os gate off user=%s account=zzae path=/.+$" % re.escape(me)), repr(new))
    for i, (name, what) in enumerate(controls):
        off = audit_off()
        fno, r = w.open29("zzae;" + name)
        back = w.read_back(fno) if fno is not None else None
        new = audit_new(off)
        row("X8%s CONTROL (inside the account): request 29 'zzae;%s' - %s - opens and reads 'secret of zzae', and the audit trail gains no refusal" % ("abc"[i], name, what),
            fno is not None and back == "secret of zzae" and new is not None and "request=29" not in new, repr((fno, back, r, new)))
    fno, r = w.open29("zzae;zzsec")
    back = w.read_back(fno) if fno is not None else None
    row("X9 CONTROL AFTER THE REFUSALS: 'zzae;zzsec' still opens and reads 'secret of zzae' (so the refusals above are the rule and not a broken session)",
        fno is not None and back == "secret of zzae", repr((fno, back)))
    w.close()

    # ---- zzaf: the os switch ON ---------------------------------------------------------------------------------------------------
    w = Wire("Xb")
    e, t = w.login("zzaf")
    row("X10 a member signs on to zzaf (OK)", e == 0, repr((e, t)))
    if e != 0:
        q3.bail("the control login did not work, so no row below can be believed")
    off = audit_off()
    for i, (name, what, planted) in enumerate(cases):
        fno, r = w.open29("zzaf;" + name)
        back = w.read_back(fno) if fno is not None else None
        say("      [evidence] request 29 'zzaf;%s' (%s): file number %r, READ k1 %r, the disk holds %r" % (name, what, fno, back, planted))
        if planted is None:
            row("X%d request 29 'zzaf;%s' - %s - with the os switch ON: opens (a file number comes back)" % (11 + i, name, what), fno is not None, repr((fno, r)))
        else:
            row("X%d request 29 'zzaf;%s' - %s - with the os switch ON: opens and reads the planted %r" % (11 + i, name, what, planted), fno is not None and back == planted, repr((fno, back, r)))
    new = audit_new(off)
    row("X17 ...and no refusal is on the audit trail for any of them", new is not None and "request=29" not in new, repr(new))
    for i, (name, what) in enumerate(controls):
        fno, r = w.open29("zzaf;" + name)
        back = w.read_back(fno) if fno is not None else None
        row("X18%s CONTROL: request 29 'zzaf;%s' - %s - opens and reads 'secret of zzaf'" % ("abc"[i], name, what), fno is not None and back == "secret of zzaf", repr((fno, back, r)))
    w.close()

    # ---- the os switch is read when the request is made, not when the session signed on -------------------------------------------
    w = Wire("Xc")
    e, t = w.login("zzaf")
    register("zzaf", q3.GROUP, net="yes", os_exec="no")
    fno, r = w.open29("zzaf;zzpabs")
    back = w.read_back(fno) if fno is not None else None
    row("X19 the os switch is taken off zzaf's register record AFTER the session signed on: request 29 'zzaf;zzpabs' is refused now (the register is read at each request, as the NET gate is)",
        fno is None and r is not None and r[0] == 2 and r[1] == X_POINTER_ERR and back != PLANT_OUT, "OPENED fno %r and READ %r; reply %r" % (fno, back, r))
    w.close()
    register("zzaf", q3.GROUP, net="yes", os_exec="yes")
    for p_ in ("bp", "bp.out"):
        fp_ = os.path.join(q3.SYS, p_, "zzptrfix")
        if os.path.exists(fp_):
            os.remove(fp_)
    shutil.rmtree(out, ignore_errors=True)
    for n in ("zzae", "zzaf"):
        shutil.rmtree(os.path.join(box, "user_accounts", n + "-sib"), ignore_errors=True)


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
# 20 Oct 26: the OS switch asked of a pointer that leads out of the account (section X).  The rows that must fail were written BEFORE the first run of each mutant.
#   os-path    the geometry test never refuses: every pointer outside opens for a restricted account (X2 to X7 and their audit rows, and X19, which takes the switch off after sign-on)
#   os-free    nobody is free of the test: an account with os ON is refused too (X11 to X16 and X17, the audit row that says nothing was refused)
#   os-audit   the refusal is not on the audit trail under its own words (X2a, X7a)
#   os-status  the refusal answers with another status (X2 to X7: the status is part of what they judge)
MUTANTS.update({
    "os-path": ("if not(kernel(K$PATH.IN, acc : @fm : path)) then", "if 0 then", ("X2", "X2a", "X3", "X4", "X5", "X6", "X7", "X7a", "X19")),
    "os-free": ("net.free = (upcase(trim(net.rec<ACC$OS.EXEC>)) = 'YES' or (downcase(@logname) = 'sdsys' and net.acct = 'sdsys'))", "net.free = @false",
                ("X11", "X12", "X13", "X14", "X15", "X16", "X17")),
    "os-audit": ("'api refused request=29 reason=os gate off user=' : @logname", "'api refused request=29 reason=changed user=' : @logname", ("X2a", "X7a")),
    "os-status": ("set.status ER$PERM", "set.status ER$XREMOTE", ("X2", "X3", "X4", "X5", "X6", "X7", "X19")),
})
X_MUTANTS = ("os-path", "os-free", "os-audit", "os-status")    # the mutants judged by section X (20 Oct 26), which runs for them after A to E
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


# ---- S.72b (20 Oct 26): section I, request 34 behind the REAL files-only gate -------------------------------------------------------------------------------------------------------
# THE TEST DEVICE.  Two lines put before apisrvr's gate in the SANDBOX's copy (never the tree's): request 27 (which apisrvr has no use for) sets files.only for the calling session, request 28
# sets files.only and files.write.  Those are the two common variables vb.scram.final sets from the user's Linux groups (sdfiles / sdapi, sdfileswrite); everything after is the production code:
# the gate, !apifilesok, messages 11480 and 11521, the audit line.  The marker request is itself refused by the gate (it is not in the table) with 11480: the first row after it is the proof that the
# device took.  What it does NOT do is read a group: that is the SCRAM final, covered only by the VM witness.
GATE_OLD = "   if files.only then\n      if not(apifilesok(action, master.login.done, files.write, files.admin)) then"      # 21 Oct 26, S.73 item 3: the fourth argument
DEVICE = ("   if action = 27 then files.only = @true      ;* TEST DEVICE (sandbox-req29.py section I): request 27 marks this session files-only, without the write group\n"
          "   if action = 28 then                         ;* TEST DEVICE: request 28 marks it files-only AND in the group sdfileswrite\n"
          "      files.only = @true\n"
          "      files.write = @true\n"
          "   end\n")
# name -> (program changed, text, what it becomes, the rows that must fail and nothing else).  Every one starts with the device above in the sandbox's apisrvr.
I_MUTANTS = {
    # the wall disappears: request 34 leaves the change set in the sandbox's apifilesok.  N is then told what H holds: its refusal, the audit line, the repeat on a free record and the exact audit list.
    "wall-gone": ("apifilesok", "files.chg := '34,'", "files.chg := ''", ("I4", "I5", "I6", "I13")),
    # the gate reaches an ORDINARY login's request 34 (the "sdapi login is untouched" half): H is refused before and after, N (still unmarked) is refused too, and the audit list grows.
    # Written before the first run, from the rows: H's own request 34 is refused (I1a, and I6, I8, I10, I12 which ask it again), N before its marker (I2), and the audit list grows (I13).
    "wall-too-wide": ("apisrvr", GATE_OLD, "   if files.only or action = 34 then\n      if not(apifilesok(action, master.login.done, files.write, files.admin)) then", ("I1a", "I2", "I6", "I8", "I10", "I12", "I13")),
    # the gate ignores the group: a session marked in the group is refused as one that is not: G is not served request 34 (I9) or request 30 (I10), is not told 0 after its release (I10a: its 34 is
    # refused), and the audit list differs (I13).  H, N and the marker rows do not change.
    "group-ignored": ("apisrvr", "if not(apifilesok(action, master.login.done, files.write, files.admin)) then", "if not(apifilesok(action, master.login.done, 0, files.admin)) then", ("I9", "I10", "I10a", "I13")),
}


def set_prog(name, edits):
    """Write the sandbox's gpl.bp/<name> from the TREE's with each (old, new) of EDITS applied in turn (each old must occur exactly once at its turn) and compile it there.  No edits: the tree's own."""
    with open(os.path.join(os.path.dirname(HERE), "sdsys", "gpl.bp", name), encoding="utf-8", errors="replace") as f:
        src = f.read()
    for old, new in edits:
        if src.count(old) != 1:
            q3.bail("section I: the text to change in %s is found %d times, not once: %r" % (name, src.count(old), old[:70]))
        src = src.replace(old, new)
    with open(os.path.join(q3.SYS, "gpl.bp", name), "w", encoding="utf-8") as f:
        f.write(src)
    out = q3.adm(["BASIC gpl.bp " + name], internal=True)
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        q3.bail("the sandbox's %s did not compile:\n%s" % (name, "\n".join(out[-8:])))


def section_i(mutant=None):
    """I. S.72b, request 34 (RECORDLOCKED) behind the REAL files-only gate.  Three sessions of zzad: H (ordinary, never marked: the sdapi login), N (request 27: files-only, no group) and G
    (request 28: files-only and in the group).  H holds an update lock on zzsec/k1 and asks for it again and for a free record (k9); N asks the same, before its marker (what the wall must
    hide) and after it; G takes a lock of its own.  Every request is printed with its bytes and reply; the audit trail is read after each step.  The expected audit list is written here, in the
    order the requests are sent: 27 off, 34 off, 34 off, 32 off, 30 off, 28 on, 20 on - and nothing else, so an H that is refused a thing, or a refusal that is not audited, shows."""
    say("\n--- I. S.72b: request 34 behind the real files-only gate (a TEST DEVICE marks sessions files-only: the gate, !apifilesok, the messages and the audit line are the production code) ---")
    if not q3.restart():
        q3.bail("SD does not start with the sandbox's own sd.conf")
    me = getpass.getuser()
    edits = [(GATE_OLD, DEVICE + GATE_OLD)]
    prog_edit = {"apisrvr": [], "apifilesok": []}
    if mutant is not None:
        prog, old, new = I_MUTANTS[mutant][:3]
        prog_edit[prog].append((old, new))
        say("\nsandbox-req29: MUTANT %s: the sandbox's %s has %r changed to %r; the rows that must fail, and nothing else: %s" % (mutant, prog, old[:70], new[:70], ", ".join(I_MUTANTS[mutant][3])))
    try:
        set_prog("apifilesok", prog_edit["apifilesok"])
        set_prog("apisrvr", edits + prog_edit["apisrvr"])
        say("  [device] the sandbox's apisrvr has request 27 (files-only) and 28 (files-only + group) in front of its gate; the account is zzad, the file zzsec, the record k1 (held by H), k9 (free)")
        H, N, G = Wire("IH"), Wire("IN"), Wire("IG")
        logins = [w.login("zzad") for w in (H, N, G)]
        row("I0 three members sign on to zzad (OK all): H stays an ordinary session for the whole section, N will be marked files-only without the write group, G with it",
            all(e == 0 for e, t in logins), repr(logins))
        if not all(e == 0 for e, t in logins):
            q3.bail("the control logins did not work, so no row below can be believed")
        uH, uN, uG = H.userno(), N.userno(), G.userno()
        row("I0a the user numbers, by request 50 on each session before any marker: three different positive integers (the numbers the rows below expect in STATUS())",
            None not in (uH, uN, uG) and len({uH, uN, uG}) == 3 and min(uH, uN, uG) > 0, repr((uH, uN, uG)))
        fno = [w.open4("zzsec")[0] for w in (H, N, G)]
        if None in fno + [uH, uN, uG]:
            q3.bail("a file did not open or a user number was not given, so no row below can be believed")
        fH, fN, fG = fno
        back = N.read_back(fN)
        row("I0b CONTROL: N reads the record planted in zzad's zzsec/k1 (%r) through its open file number - the file is the one the disk holds" % planted_zzad(), back == planted_zzad(), repr(back))
        rH = H.readlock(fH, b"k1", True)
        row("I1 H (ordinary) takes an update lock on zzsec/k1 (READU, request 9): OK", rH is not None and rH[0] == 0, repr(rH))
        h1, h9 = H.reclocked(fH, b"k1"), H.reclocked(fH, b"k9")
        row("I1a H (an sdapi login: never marked, not in any group) asks RECORDLOCKED: k1 is code 2 (its own update lock) with STATUS() its own number %r, the free record k9 is code 0 with STATUS() 0 - served, "
            "the wall does not reach an ordinary login" % uH, h1[:2] == (2, uH) and h9[:2] == (0, 0), repr((h1[:3], h9[:3])))
        n0 = N.reclocked(fN, b"k1")
        row("I2 CONTROL (what the wall must hide): N, still unmarked, is told k1 is locked by ANOTHER user - code -2 with STATUS() H's number %r" % uH, n0[:2] == (-2, uH), repr(n0[:3]))
        off = audit_off()
        row("I2a the audit file can be read (a row that needs a line from it fails, it does not pass for want of one)", off is not None, repr(off))
        # ---- N: marker 27, then request 34
        r27 = N.req(27, shown="TEST DEVICE: mark this session files-only (no group)")
        t27 = msg(11480).replace("%1", "27")
        row("I3 the marker: request 27 is refused by the gate - error ON.ERROR (1) with message 11480 for request 27 (%r) - so N is now a files-only session without the group and the device took" % t27,
            r27 is not None and r27[0] == 1 and r27[2].decode("latin-1") == t27, repr(r27))
        if not (r27 is not None and r27[0] == 1 and r27[2].decode("latin-1") == t27):
            q3.bail("the test device did not take: request 27 was not refused by the files-only gate, so no row below measures the gate")
        c34, s34, raw = N.reclocked(fN, b"k1")
        t34 = msg(11521).replace("%1", "34")
        row("I4 N (files-only, NOT in the group) asks RECORDLOCKED of zzsec/k1, which H holds: refused - error ON.ERROR (1), the text is message 11521 for request 34 (%r), no 4 byte code, and the reply "
            "does not carry H's number %r in STATUS()" % (t34, uH),
            raw is not None and raw[0] == 1 and raw[2].decode("latin-1") == t34 and t34.endswith("(request 34)") and c34 is None and raw[1] != uH, repr(raw))
        new = audit_new(off)
        row("I5 ...and the server audited it: 'api refused request=34 route=sdfiles write=off admin=off user=%s' (the marker's own 'request=27' line is before it; the admin word is S.73 item 3's)" % me,
            audit_has(new, r"api refused request=34 route=sdfiles write=off admin=off user=%s$" % re.escape(me)), repr(new))
        c9, s9, raw9 = N.reclocked(fN, b"k9")
        h_again = H.reclocked(fH, b"k1")
        row("I6 the refusal does not depend on the lock: the same request for the FREE record k9 is refused the same way (%r), N took nothing, and H still holds k1 (code 2, STATUS() %r)" % (t34, uH),
            raw9 is not None and raw9[0] == 1 and raw9[2].decode("latin-1") == t34 and c9 is None and h_again[:2] == (2, uH), repr((raw9, h_again[:3])))
        # ---- N: the reads still work, the neighbours of 34 are refused as before
        back = N.read_back(fN)
        rr = N.release(fN, b"k9")
        row("I7 N still reads (request 6: the planted record) and still releases (request 15, k9): the reads and 15 need sdfiles alone", back == planted_zzad() and rr is not None and rr[0] == 0, repr((back, rr)))
        rfl = N.filelock(fN, 0)
        rlk = N.lockrec(fN, 3, b"k9")
        row("I8 CONTROL: N's FILELOCK (32) and lock record (30) are refused as before - error ON.ERROR with message 11521 for requests 32 and 30; N holds nothing (H asks RECORDLOCKED of k9: code 0)",
            rfl is not None and rfl[0] == 1 and rfl[2].decode("latin-1") == msg(11521).replace("%1", "32") and rlk is not None and rlk[0] == 1
            and rlk[2].decode("latin-1") == msg(11521).replace("%1", "30") and H.reclocked(fH, b"k9")[:2] == (0, 0), repr((rfl, rlk)))
        # ---- G: marker 28 (files-only AND in the group)
        r28 = G.req(28, shown="TEST DEVICE: mark this session files-only and in the group sdfileswrite")
        t28 = msg(11480).replace("%1", "28")
        row("I9a the marker: request 28 is refused too, with message 11480 for request 28 (%r) - G is files-only and in the group" % t28, r28 is not None and r28[0] == 1 and r28[2].decode("latin-1") == t28, repr(r28))
        g1, g9 = G.reclocked(fG, b"k1"), G.reclocked(fG, b"k9")
        row("I9 G (files-only, IN the group) asks RECORDLOCKED: served - k1 is code -2 with STATUS() H's number %r, the free k9 is code 0 with STATUS() 0 (the same answers as N was given before its marker)" % uH,
            g1[:2] == (-2, uH) and g9[:2] == (0, 0), repr((g1[:3], g9[:3])))
        rl = G.lockrec(fG, 3, b"k9")
        g2 = G.reclocked(fG, b"k9")
        h2 = H.reclocked(fH, b"k9")
        row("I10 G takes an update lock on k9 (request 30, flags 3): OK; RECORDLOCKED then says code 2 to G (STATUS() %r) and code -2 to H (STATUS() %r) - the group may lock, and what it is told is real" % (uG, uG),
            rl is not None and rl[0] == 0 and g2[:2] == (2, uG) and h2[:2] == (-2, uG), repr((rl, g2[:3], h2[:3])))
        G.release(fG, b"k9")
        g3 = G.reclocked(fG, b"k9")
        row("I10a ...and after G lets k9 go (request 15) G is told code 0 again - the lock above was G's", g3[:2] == (0, 0), repr(g3[:3]))
        r20 = G.req(20, b"\x00\x00", shown="call (not in the table)")
        row("I11 a request outside the table (20, call) is refused to G as well - message 11480 for request 20: the group lifts the change set only", r20 is not None and r20[0] == 1
            and r20[2].decode("latin-1") == msg(11480).replace("%1", "20"), repr(r20))
        # ---- H: still an ordinary session at the end
        h3, h4 = H.reclocked(fH, b"k1"), H.reclocked(fH, b"k9")
        row("I12 CONTROL AFTER EVERYTHING: H (never marked) is still served RECORDLOCKED - k1 code 2 with STATUS() %r, k9 code 0 - and was not refused once" % uH, h3[:2] == (2, uH) and h4[:2] == (0, 0), repr((h3[:3], h4[:3])))
        new = audit_new(off)
        got = re.findall(r"api refused request=(\d+) route=sdfiles write=(on|off) admin=off user=(\S+)$", new or "", re.M)     # 21 Oct 26: every line carries admin= (off here: the device sets no administration flag)
        want = [("27", "off", me), ("34", "off", me), ("34", "off", me), ("32", "off", me), ("30", "off", me), ("28", "on", me), ("20", "on", me)]
        row("I13 the audit trail gained EXACTLY these 'api refused request=N route=sdfiles write=W user=%s' lines, in this order, and no other (nothing for H, nothing for the reads, the group's "
            "request 34 and 30): %s" % (me, " ".join("%s/%s" % (a, b) for a, b, c in want)), got == want, repr(got))
        for w in (H, N, G):
            w.close()
    finally:
        set_prog("apisrvr", [])
        set_prog("apifilesok", [])


_planted = {}


def planted_zzad():
    """The record the preparation planted in zzad's zzsec/k1 and read back (set in main)."""
    return _planted.get("zzad")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    mutant = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mutant=")), None)
    if len(args) != 1 or (mutant is not None and mutant not in MUTANTS and mutant not in I_MUTANTS):
        q3.bail("usage: sandbox-req29.py <dir> [--build] [--mutant=%s]" % "|".join(list(MUTANTS) + list(I_MUTANTS)))
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
    _planted.update(planted)
    # only now are the register records changed (the sign-on above needed the user's own group)
    register("zzaa", q3.GROUP, net="no")            # a member, the NET gate OFF
    register("zzab", NOT_MEMBER_GROUP, net="yes")   # NOT a member, the NET gate on: isolates the membership rule
    register("zzac", q3.GROUP, susp="SUSPENDED", net="yes")      # a member, suspended, NET on
    register("zzad", q3.GROUP, net="yes")           # a member, NET on: the control
    path_b = os.path.join(BOX, "user_accounts", "zzab")
    if mutant in MUTANTS:
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
        if mutant is None or mutant in X_MUTANTS:
            section_x()
        if mutant is None or mutant in F_MUTANTS:
            section_f()
        if mutant is None:
            section_g()
            section_h()
        if mutant is None or mutant in I_MUTANTS:
            section_i(mutant)
    finally:
        q3.restart()
        if mutant is not None:
            set_apisrvr()          # the sandbox's apisrvr is the tree's again
        subprocess.run([sys.executable, q3.TOOL, BOX, "stop"], capture_output=True, text=True, errors="replace", timeout=120)

    say("\nsandbox-req29: %d passed, %d failed" % (q3.passed, q3.failed))
    if mutant is not None:
        want, got = sorted(set(MUTANTS[mutant][2] if mutant in MUTANTS else I_MUTANTS[mutant][3])), sorted(set(FAILED_IDS))
        ok = want == got
        say("sandbox-req29: MUTANT %s: the rows that failed are %s; they had to be exactly %s -> %s" % (mutant, got, want, "KILLED BY ITS OWN ROWS" if ok else "NOT AS EXPECTED"))
        return 0 if ok else 1
    return 1 if q3.failed else 0


if __name__ == "__main__":
    sys.exit(main())
