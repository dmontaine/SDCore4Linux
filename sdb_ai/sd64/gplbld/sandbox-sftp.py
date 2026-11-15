#!/usr/bin/env python3
# sandbox-sftp.py - S.242 stage 3: the file transfer server inside sd (gplsrc/sd_sftp.c, gpl.bp/xfersrv), run for real.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-sftp.py <dir> [--build] [--only=NAME,...] [--mutant=NAME]
#
# No sudo, no install.  <dir> is a sandbox directory (a SHORT path: sftp -D takes the server command as words).  --build makes
# the sandbox from the tree first; without it <dir> must hold a built one.
#
# WHAT RUNS.  The REAL OpenSSH client, `sftp -b - -D <sandbox>/sys/bin/sd`, with SSH_ORIGINAL_COMMAND set to the Subsystem path
# and SSH_CONNECTION set - what sshd's ForceCommand gives sd for an sftp request - so no sshd is needed; and, for what that client
# never sends, a raw speaker of the protocol on the same command.  The slot is opened by a LIVE ordinary session of the sandbox
# user in its own account (a pipe kept open; the slot dies with its session), through a $internal probe, zzxslot, since RECEIVE and
# SEND are stage 4.
#
# THE ORACLE IS THE DISK AND THE AUDIT FILE, never what the client printed alone: a file's bytes and SHA-256 (hashlib) against the
# audit line's, a listing of the directory before and after, the bytes of a file that must not have changed.  A refusal row wants
# three things: the client failed, the disk is as it was, and the audit line (or the server's words) names the reason.
#
# SECTIONS (--only=): gate in wall text limits out raw life timers.  `gate` is the control for all the others (its row G7 is the
# transfer that works); every section builds what it needs.
#
# MUTANTS (--mutant=, on the sandbox's own copy of gpl.bp/xfersrv, recompiled there): no-account-gate (the register's xfer-on is
# not asked: G2 G3 fail), no-system-switch (XFER is not asked: G1 fails), no-kind-check (a group account is taken: G5 fails).
# The C has no runtime mutant here; gplbld/test-sftp-units.py holds its text.
#
# NEEDS: the sandbox user in the Linux groups sdusers and sdu_<user> (the account named after the user is a USER account only by
# that group's name), and /usr/bin/sftp.  Without them: CANNOT RUN, exit 2.

import hashlib
import importlib.util
import os
import re
import select
import shutil
import signal
import stat
import struct
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("gates", os.path.join(HERE, "sandbox-gates.py"))
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

USER = g.USER
UGROUP = "sdu_" + USER
SUBSYS = "/usr/local/sdsys/bin/sd-sftp"
MARK = "# sandbox-sftp below"
SECTIONS = ["gate", "in", "wall", "text", "limits", "out", "raw", "life", "timers", "verbs"]
MUTANTS = {
    "no-account-gate": ("   if upcase(trim(acc.rec<ACC$XFER>)) # 'YES' then", "   if @false then"),
    "no-system-switch": ("   if config('XFER') # 1 then", "   if @false then"),
    "no-kind-check": ("   if acc.rec<ACC$GROUP>[1,4] # 'sdu_' then", "   if @false then"),
}
BOX = SYS = SD = ACCT = LOCAL = XIN = XOUT = None
STDOUT = ""
lives = []


def say(s=""):
    print(s, flush=True)


def row(name, ok, detail=""):
    g.row(name, ok, detail)


def bail(msg):
    for lv in lives:
        lv.kill()
    say("sandbox-sftp: CANNOT RUN - " + msg)
    sys.exit(2)


# ---------------------------------------------------------------------------------------------------------------------
# the sandbox's sd.conf, the register, the audit file

def conf(**kw):
    """Rewrite the lines below the marker in sd.conf.  XFER and the limits are read by each process as it starts."""
    path = os.path.join(BOX, "sd.conf")
    with open(path) as f:
        base = f.read().split(MARK)[0].rstrip("\n") + "\n"
    lines = "".join("%s=%s\n" % (k, v) for k, v in kw.items())
    with open(path, "w") as f:
        f.write(base + MARK + "\n" + lines)
    say("    sd.conf: " + (" ".join("%s=%s" % kv for kv in kw.items()) or "(no transfer line)"))


def reg(name, path, group, xfer, suspended=""):
    """A register record: path, group, suspension, the edit gates on, and field 22 (ACC$XFER)."""
    fields = [path, "", group, "", suspended, "", "no", "no", "", "yes", "yes", "yes"] + [""] * 9 + [xfer]
    assert len(fields) == 22
    g.put(os.path.join(SYS, "accounts", name), "\n".join(fields) + "\n")
    say("    register %s: group=%s xfer=%r suspended=%r" % (name, group, xfer, suspended))


def audit_off():
    return os.path.getsize(os.path.join(SYS, "audit"))


def audit_new(off):
    with open(os.path.join(SYS, "audit"), "rb") as f:
        f.seek(off)
        return [ln for ln in f.read().decode("utf-8", "replace").splitlines() if " xfer " in ln or ln.endswith(" xfer")]


def has(lines, pattern):
    return any(re.search(pattern, ln) for ln in lines)


def xenv(cmd=SUBSYS):
    e = g.env(False)
    e["SSH_CONNECTION"] = "192.0.2.7 50000 192.0.2.1 22"
    if cmd is not None:
        e["SSH_ORIGINAL_COMMAND"] = cmd
    return e


def listing(d):
    return sorted(os.listdir(d))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def local(name, data):
    p = os.path.join(LOCAL, name)
    with open(p, "wb") as f:
        f.write(data)
    return p


def disk(d, name):
    try:
        with open(os.path.join(d, name), "rb") as f:
            return f.read()
    except OSError:
        return None


# ---------------------------------------------------------------------------------------------------------------------
# a live ordinary session that holds the slot

class Live:
    def __init__(self, cwd, account=None):
        argv = [SD] + (["-a" + account] if account else [])
        self.p = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=cwd,
                                  env=g.env(False))
        os.set_blocking(self.p.stdout.fileno(), False)
        self.text = ""
        lives.append(self)
        self.send("")
        self.send("TERM 200,9999")

    def send(self, line):
        self.p.stdin.write((line + "\n").encode())
        self.p.stdin.flush()

    def cmd(self, line, pattern, timeout=30):
        """Type a line; wait for a line of output that matches (the echo of the command begins with a colon and cannot)."""
        mark = len(self.text)
        self.send(line)
        end = time.time() + timeout
        while time.time() < end:
            m = re.search(pattern, self.text[mark:], re.M)
            if m:
                return m
            r, _, _ = select.select([self.p.stdout], [], [], 0.5)
            if r:
                chunk = self.p.stdout.read()
                if chunk == b"":
                    break
                if chunk:
                    self.text += g.ANSI.sub("", chunk.decode("utf-8", "replace")).replace("\r", "")
        return re.search(pattern, self.text[mark:], re.M)

    def open(self, direction, flags=0):
        m = self.cmd("ZZXSLOT open %d %d" % (direction, flags), r"^XSLOT open (\S+)$")
        say("    holder pid %d: ZZXSLOT open %d %d -> %s" % (self.p.pid, direction, flags, m.group(1) if m else "NO ANSWER"))
        return m.group(1) if m else None

    def ask(self, op):
        m = self.cmd("ZZXSLOT " + op, r"^XSLOT %s (\S+)$" % op)
        say("    holder pid %d: ZZXSLOT %s -> %s" % (self.p.pid, op, m.group(1) if m else "NO ANSWER"))
        return m.group(1).split("|") if m else []

    def end(self):
        if self.p.poll() is None:
            try:
                self.send("OFF")
                self.p.wait(15)
            except Exception:
                self.kill()
        if self in lives:
            lives.remove(self)

    def kill(self):
        if self.p.poll() is None:
            self.p.kill()
            self.p.wait(10)
        if self in lives:
            lives.remove(self)


def holder(direction, flags=0, must=True):
    lv = Live(ACCT)
    ans = lv.open(direction, flags)
    if must and ans != "OK":
        lv.kill()
        bail("the holder session could not open a slot (answer %r):\n%s" % (ans, lv.text[-600:]))
    return lv


# ---------------------------------------------------------------------------------------------------------------------
# the real client

def sftp(lines, env=None, timeout=120):
    """Run OpenSSH sftp in batch mode against the sandbox's sd.  A line that begins with '-' may fail without ending the batch.
    Returns (exit status, stdout + stderr)."""
    say("    sftp> " + " ; ".join(lines))
    p = subprocess.run(["sftp", "-b", "-", "-D", SD], input="\n".join(lines) + "\n", capture_output=True, text=True,
                       errors="replace", cwd=LOCAL, env=env or xenv(), timeout=timeout)
    global STDOUT
    STDOUT = p.stdout                 # what the client printed, without the errors (a listing is read from this)
    out = p.stdout + p.stderr
    for ln in out.splitlines():
        if ln.strip() and not ln.startswith("sftp> "):
            say("      | " + ln[:200])
    return p.returncode, out


# ---------------------------------------------------------------------------------------------------------------------
# a raw speaker of SFTP version 3

def s(b):
    if isinstance(b, str):
        b = b.encode()
    return struct.pack(">I", len(b)) + b


class Raw:
    def __init__(self, env=None):
        self.p = subprocess.Popen([SD], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=LOCAL,
                                  env=env or xenv())
        self.id = 0

    def put(self, data):
        try:
            self.p.stdin.write(data)
            self.p.stdin.flush()
            return True
        except (BrokenPipeError, OSError):
            return False

    def send(self, typ, payload):
        body = bytes([typ]) + payload
        return self.put(struct.pack(">I", len(body)) + body)

    def _read(self, n, timeout):
        buf = b""
        end = time.time() + timeout
        fd = self.p.stdout.fileno()
        while len(buf) < n:
            left = end - time.time()
            if left <= 0:
                return None
            r, _, _ = select.select([fd], [], [], left)
            if not r:
                return None
            chunk = os.read(fd, n - len(buf))
            if chunk == b"":
                return b"" if buf == b"" else None
            buf += chunk
        return buf

    def recv(self, timeout=15):
        """(type, payload); 'EOF' when the server closed; None when nothing came in time."""
        head = self._read(4, timeout)
        if head is None:
            return None
        if head == b"":
            return "EOF"
        body = self._read(struct.unpack(">I", head)[0], timeout)
        if not body:
            return None
        return body[0], body[1:]

    def init(self):
        self.send(1, struct.pack(">I", 3))
        return self.recv()

    def req(self, typ, body, timeout=15):
        self.id += 1
        self.send(typ, struct.pack(">I", self.id) + body)
        return self.recv(timeout)

    @staticmethod
    def status(r):
        """(code, message) of a STATUS answer, else (None, repr)."""
        if isinstance(r, tuple) and r[0] == 101:
            code = struct.unpack(">I", r[1][4:8])[0]
            n = struct.unpack(">I", r[1][8:12])[0]
            return code, r[1][12:12 + n].decode("utf-8", "replace")
        return None, repr(r)[:80]

    @staticmethod
    def handle(r):
        if isinstance(r, tuple) and r[0] == 102:
            n = struct.unpack(">I", r[1][4:8])[0]
            return r[1][8:8 + n]
        return None

    def open(self, name, pflags):
        return self.req(3, s(name) + struct.pack(">II", pflags, 0))

    def write(self, h, offset, data):
        return self.req(6, s(h) + struct.pack(">Q", offset) + s(data))

    def close(self, h):
        return self.req(4, s(h))

    def wait_eof(self, timeout):
        """Seconds until the server closed its end, or None."""
        t0 = time.time()
        while time.time() - t0 < timeout:
            r = self.recv(timeout - (time.time() - t0))
            if r == "EOF":
                return time.time() - t0
            if r is None:
                break
        return None

    def end(self):
        try:
            self.p.stdin.close()
        except OSError:
            pass
        try:
            self.p.wait(15)
        except subprocess.TimeoutExpired:
            self.p.kill()
            self.p.wait(10)
        err = self.p.stderr.read().decode("utf-8", "replace")
        self.p.stdout.close()
        self.p.stderr.close()
        return err


WRITE, READ, CREAT, TRUNC, APPEND = 0x02, 0x01, 0x08, 0x10, 0x04


# ---------------------------------------------------------------------------------------------------------------------
# preparation

def prepare(mutant):
    global ACCT, LOCAL, XIN, XOUT
    g.prepare()
    g.put(os.path.join(SYS, "gpl.bp", "zzxslot"), "\n".join([
        "$internal", "program zzxslot", "$catalog $zzxslot", "$include keys.h", "$include int$keys.h",
        "   s = trim(@sentence)",
        "   op = field(s, ' ', 2)",
        "   if op = 'open' then",
        "      crt 'XSLOT open ' : convert(@fm, '|', kernel(K$XFER, 'open' : @fm : field(s, ' ', 3) : @fm : field(s, ' ', 4)))",
        "   end else",
        "      crt 'XSLOT ' : op : ' ' : convert(@fm, '|', kernel(K$XFER, op))",
        "   end",
        "end", ""]))
    # The sandbox's xfersrv is always the tree's as it stands now (a mutant run before this one changed the sandbox's copy), then the mutant
    progs = "zzxslot xfersrv"
    path = os.path.join(SYS, "gpl.bp", "xfersrv")
    with open(os.path.join(os.path.dirname(HERE), "sdsys", "gpl.bp", "xfersrv"), encoding="utf-8") as f:
        text = f.read()
    if mutant:
        old, new = MUTANTS[mutant]
        if text.count(old) != 1:
            bail("mutant %s: its line occurs %d times in the tree's xfersrv" % (mutant, text.count(old)))
        text = text.replace(old, new)
        say("  MUTANT %s: %r -> %r in the sandbox's gpl.bp/xfersrv" % (mutant, old.strip(), new.strip()))
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    out = g.adm(["BASIC gpl.bp " + progs], internal=True)
    if not g.has(out, r"^Compiled %d program\(s\) with no errors" % len(progs.split())):
        bail("the probe did not compile:\n" + "\n".join(out[-10:]))

    for name in (USER, "zzxoth"):
        g.EXTRA_FIXTURES[name] = ("no", "no")
        path = g.build_account(name)
        g.put(os.path.join(SYS, "bp", "zzxvoc"), "\n".join([
            "$internal",
            "   openpath '%s/voc' to v else crt 'XVOC no voc' ; stop" % path,
            "   write 'V':@fm:'CA':@fm:'$zzxslot' to v, 'zzxslot'",
            "   crt 'XVOC done'", "end", ""]))
        out = g.adm(["BASIC bp zzxvoc", "RUN bp zzxvoc"], internal=True)
        if not g.has(out, r"^XVOC done$"):
            bail("the verb zzxslot was not written to %s's VOC:\n%s" % (name, "\n".join(out[-6:])))
    ACCT = os.path.join(BOX, "user_accounts", USER)
    XIN = os.path.join(ACCT, "xfer.in")
    XOUT = os.path.join(ACCT, "xfer.out")
    LOCAL = os.path.join(BOX, "zzxlocal")
    for d in (XIN, XOUT, LOCAL):
        if os.path.isdir(d) and not os.path.islink(d):
            shutil.rmtree(d)
        elif os.path.lexists(d):
            os.unlink(d)
        os.makedirs(d)
    reg(USER, ACCT, UGROUP, "yes")
    reg("zzxoth", os.path.join(BOX, "user_accounts", "zzxoth"), g.GROUP, "yes")
    audit = os.path.join(SYS, "audit")
    if not os.path.exists(audit):
        open(audit, "w").close()
    conf(XFER=1)


def fresh(d):
    for n in os.listdir(d):
        p = os.path.join(d, n)
        if os.path.isdir(p) and not os.path.islink(p):
            shutil.rmtree(p)
        else:
            os.unlink(p)


# ---------------------------------------------------------------------------------------------------------------------
# G  the gates: every one of them refuses, in words, with an audit line, and nothing reaches the disk

def refused_put(tag, what, msg_pat, reason_pat, name="g.txt"):
    local(name, b"gate probe\n")
    before = listing(XIN)
    off = audit_off()
    rc, out = sftp(["put %s" % name])
    a = audit_new(off)
    row("%s: %s - the client fails, nothing is in xfer.in, the server says why and the audit trail has the reason" % (tag, what),
        rc != 0 and listing(XIN) == before and re.search(msg_pat, out) is not None and has(a, r"xfer refused reason=" + reason_pat),
        "exit %d, xfer.in %s, words %s, audit %r" % (rc, listing(XIN), bool(re.search(msg_pat, out)), a[-2:]))


def sec_gate():
    say("\n--- G. the gates ---------------------------------------------------------------------------------------------")
    fresh(XIN)
    lv = holder(1)
    conf()
    refused_put("G1", "XFER is not 1 in sd.conf (a slot is open, the account has xfer-on)", r"not turned on for this system",
                r"xfer is off")
    conf(XFER=1)
    for tag, val in (("G2", ""), ("G3", "no")):
        reg(USER, ACCT, UGROUP, val)
        refused_put(tag, "the register's xfer field is %r" % val, r"may not move files over its ssh login", r"xfer-on is not set")
    reg(USER, ACCT, UGROUP, "yes", suspended="SUSPENDED")
    refused_put("G4", "the account is suspended", r"is suspended", r"the account is suspended")
    reg(USER, ACCT, g.GROUP, "yes")
    refused_put("G5", "the account is not a user account (its register group is %s)" % g.GROUP, r"only for a user account",
                r"not a user account")
    reg(USER, ACCT, UGROUP, "yes")
    lv.end()

    refused_put("G6", "no slot is open (XFER=1, xfer-on)", r"No transfer is open", r"no slot is open")

    lv = holder(1)
    data = b"10 PRINT 'HELLO'\n20 END\n"
    local("g7.bas", data)
    off = audit_off()
    rc, out = sftp(["put g7.bas"])
    a = audit_new(off)
    got = disk(XIN, "g7.bas")
    row("G7: CONTROL - with XFER=1, xfer-on and a slot the same put arrives: the bytes on disk are the bytes sent",
        rc == 0 and got == data, "exit %d, disk %r" % (rc, got))
    row("G7a: ...the audit trail has the connection, the file with its size and SHA-256 (hashlib's), and the disconnect",
        has(a, r"xfer connect dir=in holder=\d+ from=192\.0\.2\.7 account=%s" % USER)
        and has(a, r"xfer file dir=in bytes=%d sha256=%s name=g7\.bas" % (len(data), sha(data)))
        and has(a, r"xfer disconnect dir=in why=eof files=1 bytes=%d refusals=0" % len(data)), "audit %r" % a)
    st = lv.ask("state")
    row("G7b: ...and the holder's slot counts it (1 file, %d bytes, connected, live)" % len(data),
        st[:4] == ["OK", "1", "0", "live"] and st[5:8] == ["1", str(len(data)), "1"], "state %r" % st)
    mode = stat.S_IMODE(os.stat(os.path.join(XIN, "g7.bas")).st_mode)
    row("G7c: ...the file's mode is 0664, what a session of the account gives a file (umask 002)", mode == 0o664, oct(mode))
    lv.end()

    # the slot of another account is not this account's
    lv = Live(os.path.join(BOX, "user_accounts", "zzxoth"), account="zzxoth")
    ans = lv.open(1)
    if ans != "OK":
        bail("the session in zzxoth could not open a slot (%r)" % ans)
    refused_put("G8", "the only open slot is the same user's session in ANOTHER account (zzxoth)", r"No transfer is open",
                r"no slot is open")
    row("G8a: a session's own program cannot run the server's side of the key (serve -> ERR|server)",
        lv.ask("serve")[:2] == ["ERR", "server"])
    lv.end()

    # only the exact Subsystem path makes sd a transfer server
    lv = holder(1)
    before = listing(XIN)
    off = audit_off()
    local("g9.txt", b"x\n")
    try:
        rc, out = sftp(["put g9.txt"], env=xenv("/usr/lib/openssh/sftp-server"), timeout=40)
    except subprocess.TimeoutExpired:
        rc, out = -1, "(timed out)"
    row("G9: SSH_ORIGINAL_COMMAND with another path (the machine's own sftp-server) is not a transfer: no file, no xfer audit line",
        rc != 0 and listing(XIN) == before and audit_new(off) == [], "exit %d, audit %r" % (rc, audit_new(off)))
    lv.end()
    subprocess.run([SD, "-cleanup"], env=g.env(False), capture_output=True, timeout=60)


# ---------------------------------------------------------------------------------------------------------------------
# I  files coming in

def sec_in():
    say("\n--- I. files in ----------------------------------------------------------------------------------------------")
    fresh(XIN)
    lv = holder(1)
    big = (b"".join(b"line %07d of a large plain text file, with the bytes \x80 and \xf7 that SD stores\n" % i for i in range(60000)))
    local("big.txt", big)
    off = audit_off()
    rc, out = sftp(["put big.txt"])
    got = disk(XIN, "big.txt")
    row("I1: a %d byte file (many requests, sent ahead of their answers) arrives whole: SHA-256 on disk = SHA-256 sent = the audit line's"
        % len(big), rc == 0 and got is not None and sha(got) == sha(big)
        and has(audit_new(off), r"xfer file dir=in bytes=%d sha256=%s name=big\.txt" % (len(big), sha(big))),
        "exit %d, disk %s" % (rc, "absent" if got is None else len(got)))

    local("p.txt", b"kept times\n")
    rc, out = sftp(["put -p p.txt"])
    row("I2: put -p (the client asks to set the times and mode afterwards) succeeds, and the mode stays SD's 0664",
        rc == 0 and disk(XIN, "p.txt") == b"kept times\n" and stat.S_IMODE(os.stat(os.path.join(XIN, "p.txt")).st_mode) == 0o664,
        "exit %d" % rc)

    local("p.txt", b"A SECOND VERSION\n")
    off = audit_off()
    rc, out = sftp(["put p.txt"])
    row("I3: a name that is already there is refused and the file on disk is unchanged (no overwrite was asked for)",
        rc != 0 and disk(XIN, "p.txt") == b"kept times\n" and has(audit_new(off), r"xfer refused reason=name is there name=p\.txt"),
        "exit %d, disk %r, audit %r" % (rc, disk(XIN, "p.txt"), audit_new(off)))

    off = audit_off()
    rc, out = sftp(["put p.txt q.txt", "rename q.txt r.txt", "-rename big.txt z.txt", "-rm big.txt", "rm r.txt", "ls -1"])
    names = listing(XIN)
    a = audit_new(off)
    row("I4: this connection may rename and remove the file it has just sent (q.txt -> r.txt, then gone), and the audit trail has both",
        rc == 0 and "q.txt" not in names and "r.txt" not in names and has(a, r"xfer rename to=r\.txt from=q\.txt")
        and has(a, r"xfer remove name=r\.txt"), "exit %d, xfer.in %s, audit %r" % (rc, names, a))
    row("I4a: ...and not a file that was there before it (big.txt is still there, whole, under its own name)",
        "z.txt" not in names and disk(XIN, "big.txt") is not None and sha(disk(XIN, "big.txt")) == sha(big)
        and len([x for x in a if "reason=not a file this connection sent name=/big.txt" in x]) == 2, "xfer.in %s, audit %r" % (names, a))

    off = audit_off()
    rc, out = sftp(["-mkdir sub", "-rmdir sub", "-get big.txt back.txt", "-symlink big.txt l.txt", "-ln big.txt h.txt", "ls -1"])
    row("I5: no directory is made, no link, and nothing is read out of a RECEIVE slot (no local copy with anything in it)",
        listing(XIN) == names and disk(LOCAL, "back.txt") in (None, b"")
        and has(audit_new(off), r"xfer refused reason=receive slot gives nothing out name=big\.txt"),
        "xfer.in %s, local %s, audit %r" % (listing(XIN), listing(LOCAL), audit_new(off)))
    lv.end()

    lv = holder(1, flags=1)
    off = audit_off()
    rc, out = sftp(["put p.txt"])
    row("I6: with a slot opened for overwrite the same put replaces the file",
        rc == 0 and disk(XIN, "p.txt") == b"A SECOND VERSION\n" and lv.ask("state")[2] == "1", "exit %d, disk %r" % (rc, disk(XIN, "p.txt")))
    lv.end()


# ---------------------------------------------------------------------------------------------------------------------
# W  the wall: one directory, no path, no link

def sec_wall():
    say("\n--- W. the wall ----------------------------------------------------------------------------------------------")
    fresh(XIN)
    outside = os.path.join(ACCT, "zzoutside.txt")
    g.put(outside, "a file of the account, outside the transfer directory\n")
    os.symlink(outside, os.path.join(XIN, "link.txt"))
    os.symlink("/etc", os.path.join(XIN, "etc"))
    os.makedirs(os.path.join(XIN, "subdir"))
    g.put(os.path.join(XIN, "plain.txt"), "plain\n")
    g.put(os.path.join(XIN, ".dot"), "hidden\n")
    gone = 4194000                     # a process id nothing has: the part file of a server that died
    while True:
        try:
            os.kill(gone, 0)
            gone -= 1
        except ProcessLookupError:
            break
        except PermissionError:
            gone -= 1
    dead_part, live_part = ".part.%d.1" % gone, ".part.%d.1" % os.getpid()
    g.put(os.path.join(XIN, dead_part), "left by a server that is gone\n")
    g.put(os.path.join(XIN, live_part), "the part file of a process that is running (this suite)\n")
    acct_before = listing(ACCT)
    held = sorted([".dot", "etc", "link.txt", "plain.txt", "subdir", live_part])
    lv = holder(1, flags=1)            # overwrite ON: the wall must hold even then
    local("w.txt", b"wall probe\n")
    bad = ["../w.txt", "/etc/w.txt", "subdir/w.txt", ".hidden", "~w.txt", "a%b.txt", "a:b.txt", "a=b.txt", "etc/w.txt", "link.txt",
           "/../../tmp/zzxw.txt", live_part]
    off = audit_off()
    rc, out = sftp(["-put w.txt %s" % n for n in bad])
    after = listing(XIN)
    a = audit_new(off)
    row("W1: %d names that are a path, a link, hidden, a part file or not a record id are each refused with overwrite ON: xfer.in "
        "holds what it held, and each refusal is in the audit trail" % len(bad), after == held
        and listing(os.path.join(XIN, "subdir")) == [] and len([x for x in a if "xfer refused reason=" in x]) == len(bad),
        "xfer.in %s, %d refusals in the audit trail" % (after, len([x for x in a if "xfer refused reason=" in x])))
    row("W1a: ...the file the link points at is unchanged, the account's directory has no new entry, /tmp/zzxw.txt does not exist",
        disk(ACCT, "zzoutside.txt") == b"a file of the account, outside the transfer directory\n" and listing(ACCT) == acct_before
        and not os.path.exists("/tmp/zzxw.txt")
        and disk(XIN, live_part) == b"the part file of a process that is running (this suite)\n", "account %s" % listing(ACCT))
    row("W1b: ...the part file of a process that is gone (pid %d) was swept as the connection began; the running process's was not" % gone,
        dead_part not in after and live_part in after)
    sftp(["ls -1a"])
    shown = [ln.strip() for ln in STDOUT.split("sftp> ls -1a", 1)[-1].splitlines() if ln.strip()]
    row("W2: the listing shows the plain file and nothing else: no link, no directory, no dot file, no part file (%s)" % shown,
        shown == ["plain.txt"], "listing %r" % shown)
    rc, out = sftp(["-cd subdir", "-cd ..", "-cd /etc", "-ls /etc", "-ls ..", "pwd"])
    row("W3: cd and ls outside the one directory fail, and the working directory is still /",
        "Remote working directory: /" in out and "passwd" not in out, out[-200:])
    lv.end()

    # the directory itself is a link
    shutil.rmtree(XIN)
    target = os.path.join(BOX, "zzxtarget")
    os.makedirs(target, exist_ok=True)
    os.symlink(target, XIN)
    lv = holder(1)
    off = audit_off()
    rc, out = sftp(["put w.txt"])
    row("W4: xfer.in that is a LINK to a directory is not followed: refused, the target directory stays empty",
        rc != 0 and listing(target) == [] and "not a plain directory" in out and has(audit_new(off), r"xfer refused reason=no transfer directory"),
        "exit %d, target %s" % (rc, listing(target)))
    lv.end()
    os.unlink(XIN)
    os.makedirs(XIN)


# ---------------------------------------------------------------------------------------------------------------------
# T  plain text by content

def sec_text():
    say("\n--- T. plain text by content ---------------------------------------------------------------------------------")
    fresh(XIN)
    lv = holder(1)
    ok = b"caf\xe9 \x80\xf7 and tabs\tand CR\r\n"          # bytes 128-247 are stored, not interpreted
    cases = [("nul.txt", b"abc\x00def\n", False), ("mark.txt", b"abc\xfedef\n", False), ("f8.txt", b"\xf8\n", False),
             ("ff.txt", b"x" * 70000 + b"\xff", False), ("high.txt", ok, True)]
    off = audit_off()
    for name, data, _ in cases:
        local(name, data)
    rc, out = sftp(["-put %s" % c[0] for c in cases])
    names = listing(XIN)
    row("T1: a file with a NUL, a mark (254), byte 248 or byte 255 - the last after 70,000 good bytes - is not taken and leaves nothing "
        "behind, not even a part file", names == ["high.txt"], "xfer.in %s" % names)
    row("T1a: ...each of the four refusals is in the audit trail as 'not plain text', with the file's name",
        len([a for a in audit_new(off) if "reason=not plain text" in a]) == 4 and has(audit_new(off), r"reason=not plain text bytes=\d+ name=ff\.txt"),
        "audit %r" % audit_new(off))
    row("T2: CONTROL - bytes 128 to 247, a tab and a CR are plain text: stored as sent", disk(XIN, "high.txt") == ok)
    lv.end()


# ---------------------------------------------------------------------------------------------------------------------
# L  the limits

def sec_limits():
    say("\n--- L. the limits --------------------------------------------------------------------------------------------")
    fresh(XIN)
    conf(XFER=1, XFERFILE=1, XFERSLOT=2)
    lv = holder(1)
    local("k1024.txt", b"a" * 1023 + b"\n")
    local("k1025.txt", b"a" * 1024 + b"\n")
    off = audit_off()
    rc, out = sftp(["put k1024.txt", "-put k1025.txt"])
    row("L1: XFERFILE=1: a file of 1,024 bytes is taken and one of 1,025 is not (nothing of it is left)",
        listing(XIN) == ["k1024.txt"] and has(audit_new(off), r"reason=file over xferfile name=k1025\.txt"),
        "xfer.in %s, audit %r" % (listing(XIN), audit_new(off)))
    local("s2.txt", b"b" * 1023 + b"\n")
    local("s3.txt", b"c\n")
    off = audit_off()
    rc, out = sftp(["put s2.txt", "-put s3.txt"])
    st = lv.ask("state")
    row("L2: XFERSLOT=2: a second 1,024 byte file fills the slot (2,048 bytes) and a third file of 2 bytes is refused",
        listing(XIN) == ["k1024.txt", "s2.txt"] and has(audit_new(off), r"reason=slot over xferslot name=s3\.txt")
        and st[5:7] == ["2", "2048"], "xfer.in %s, state %r, audit %r" % (listing(XIN), st, audit_new(off)))
    lv.end()

    fresh(XIN)
    conf(XFER=1, XFERKIND="bas, .txt")
    lv = holder(1)
    for n in ("a.bas", "B.TXT", "c.exe", "noext", "d.bas.exe"):
        local(n, b"kind\n")
    off = audit_off()
    rc, out = sftp(["put a.bas", "put B.TXT", "-put c.exe", "-put noext", "-put d.bas.exe", "put a.bas e.txt", "-rename e.txt e.exe"])
    kinds = [x for x in audit_new(off) if "reason=not a kind of file taken" in x]
    row("L3: XFERKIND=bas, .txt: a.bas and B.TXT are taken; c.exe, a name with no extension and d.bas.exe are not; a taken file "
        "cannot be renamed to .exe (four refusals in the audit trail)", listing(XIN) == ["B.TXT", "a.bas", "e.txt"] and len(kinds) == 4,
        "xfer.in %s, audit %r" % (listing(XIN), kinds))
    lv.end()
    conf(XFER=1)


# ---------------------------------------------------------------------------------------------------------------------
# O  files going out

def sec_out():
    say("\n--- O. files out ---------------------------------------------------------------------------------------------")
    fresh(XOUT)
    fresh(LOCAL)
    data = b"".join(b"record %06d\n" % i for i in range(30000))
    with open(os.path.join(XOUT, "report.txt"), "wb") as f:
        f.write(data)
    with open(os.path.join(XOUT, "binary.dat"), "wb") as f:
        f.write(b"text\x00more\n")
    os.symlink("/etc/hostname", os.path.join(XOUT, "host.txt"))
    lv = holder(2)
    off = audit_off()
    rc, out = sftp(["get report.txt", "-get binary.dat", "-get host.txt", "-get /etc/hostname h2.txt", "ls -1"])
    got = disk(LOCAL, "report.txt")
    a = audit_new(off)
    row("O1: a SEND slot gives a file out: the local copy's SHA-256 is the file's, and the audit trail has it",
        got is not None and sha(got) == sha(data) and has(a, r"xfer file dir=out bytes=%d name=report\.txt" % len(data)),
        "local %s" % ("absent" if got is None else len(got)))
    row("O2: a file that is not plain text, a link, and a path outside are not given (no local host.txt or h2.txt; binary.dat is empty or absent)",
        not os.path.exists(os.path.join(LOCAL, "host.txt")) and not os.path.exists(os.path.join(LOCAL, "h2.txt"))
        and (disk(LOCAL, "binary.dat") in (None, b"")) and has(a, r"reason=not plain text dir=out name=binary\.dat"),
        "local %s" % listing(LOCAL))
    local("up.txt", b"up\n")
    before = listing(XOUT)
    off = audit_off()
    rc, out = sftp(["-put up.txt", "-rm report.txt", "-rename report.txt x.txt", "-mkdir d"])
    row("O3: nothing is written, removed, renamed or made in a SEND slot (xfer.out is as it was; the refused put is in the audit trail)",
        listing(XOUT) == before and has(audit_new(off), r"xfer refused reason=send slot takes nothing in name=up\.txt"),
        "xfer.out %s, audit %r" % (listing(XOUT), audit_new(off)))
    row("O3a: ...and xfer.in was not touched by any of it", "up.txt" not in listing(XIN))
    lv.end()


# ---------------------------------------------------------------------------------------------------------------------
# R  what the OpenSSH client never sends

def sec_raw():
    say("\n--- R. the protocol, raw -------------------------------------------------------------------------------------")
    fresh(XIN)
    lv = holder(1)

    c = Raw()
    r = c.req(16, s("."))                                # a request before INIT
    row("R1: a request before INIT ends the conversation (the server closes; no answer)", r == "EOF" or c.wait_eof(5) is not None, repr(r)[:60])
    c.end()

    c = Raw()
    v = c.init()
    row("R2: INIT is answered with version 3 and no extension", isinstance(v, tuple) and v[0] == 2 and v[1] == struct.pack(">I", 3), repr(v)[:60])
    h = Raw.handle(c.open("order.txt", WRITE | CREAT | TRUNC))
    code1, _ = Raw.status(c.write(h, 0, b"first\n"))
    code2, msg2 = Raw.status(c.write(h, 100, b"hole\n"))
    code3, _ = Raw.status(c.write(h, 6, b"late\n"))
    code4, _ = Raw.status(c.close(h))
    row("R3: a write that is not at the end of what was sent (a hole) refuses the file: later writes and the close fail, nothing is kept",
        (code1, code2, code3, code4) == (0, 4, 4, 4) and "from its start" in msg2 and listing(XIN) == [],
        "codes %r, xfer.in %s" % ((code1, code2, code3, code4), listing(XIN)))

    answers = [Raw.status(c.open("ap.txt", fl)) for fl in (WRITE | APPEND | CREAT, WRITE, READ, READ | WRITE | CREAT)]
    codes = [x[0] for x in answers]
    row("R4: an open to append, to write without creating, to read, or to read and write is refused in a RECEIVE slot (codes %r), and "
        "the status carries the reason in words" % codes, codes == [8, 8, 3, 3] and listing(XIN) == []
        and "cannot be resumed" in answers[0][1] and "nothing can be read" in answers[2][1], repr(answers))

    code, _ = Raw.status(c.write(b"\x00\x00\x00\x07", 0, b"x"))
    code_b, _ = Raw.status(c.close(b"junk"))
    row("R5: a handle that was never given is refused (write %r, close %r)" % (code, code_b), code == 4 and code_b == 4)

    hs = [Raw.handle(c.open("h%d.txt" % i, WRITE | CREAT | TRUNC)) for i in range(9)]
    row("R6: the ninth file open at once is refused (eight handles)", all(hs[:8]) and hs[8] is None, repr(hs[8]))
    parts = [n for n in listing(XIN) if n.startswith(".part.")]
    h = hs[0]
    c.write(h, 0, b"half a file\n")
    c.p.stdin.close()                                    # the connection is lost with files open
    c.p.wait(15)
    row("R7: a connection lost with %d files open and one half sent leaves nothing: no file and no part file" % len(parts),
        len(parts) == 8 and listing(XIN) == [], "xfer.in %s" % listing(XIN))
    c.end()

    c = Raw()
    c.init()
    c.put(struct.pack(">I", 0x7FFFFFFF) + b"\x03")       # a length no request may have
    row("R8: a request that says it is 2 gigabytes long ends the conversation", c.wait_eof(8) is not None)
    c.end()

    c = Raw()
    c.init()
    names = ["/..", "..", "a/..", "/a/b", "x\x00y", "a\\b", ""]
    codes = []
    for n in names:
        r = c.req(17, s(n))
        codes.append("attrs" if isinstance(r, tuple) and r[0] == 105 else Raw.status(r)[0])
    row("R9: STAT of '..', a path with '..', a path of two parts, a name with a NUL and one with a backslash are refused; '' is the "
        "directory (%r)" % codes, codes == [3, 3, 3, 2, 3, 3, "attrs"])
    r = c.req(16, s("/a/../.."))
    row("R10: REALPATH never answers a place outside: '/a/../..' is refused", Raw.status(r)[0] == 3, repr(r)[:60])
    c.end()
    lv.end()


# ---------------------------------------------------------------------------------------------------------------------
# F  the life of the server process and of the slot

def sec_life():
    say("\n--- F. the server process and the slot -----------------------------------------------------------------------")
    fresh(XIN)
    lv = holder(1)
    c = Raw()
    c.init()
    c.req(16, s("."))
    out = g.adm(["LISTU"])
    line = next((ln for ln in out if re.search(r"\bsftp\b", ln)), "")
    say("    LISTU: " + line)
    m = re.match(r"\s*\*?\s*(\d+)", line)
    row("F1: the transfer server is a process in LISTU, with the client's address, 'sftp' where a terminal would be, the user and the account",
        m is not None and re.search(r"192\.0\.2\.7 sftp: %s, %s\b" % (USER, USER), line) is not None, "LISTU %r" % out[-6:])
    if m:
        off = audit_off()
        g.adm(["LOGOUT " + m.group(1)])
        t = c.wait_eof(15)
        row("F2: LOGOUT of that user number ends the connection (the server closed after %s s) and the audit trail says why=logout"
            % ("%.1f" % t if t is not None else "never"), t is not None and has(audit_new(off), r"xfer disconnect dir=in why=logout"),
            "audit %r" % audit_new(off))
    c.end()

    c = Raw()
    c.init()
    h = Raw.handle(c.open("gone.txt", WRITE | CREAT | TRUNC))
    c.write(h, 0, b"the session will close its slot\n")
    off = audit_off()
    lv.ask("close")
    t = c.wait_eof(10)
    row("F3: the session closes its slot with a file half sent: the connection ends (%s s), why=closed, and nothing is kept"
        % ("%.1f" % t if t is not None else "never"), t is not None and has(audit_new(off), r"why=closed") and listing(XIN) == [],
        "xfer.in %s audit %r" % (listing(XIN), audit_new(off)))
    c.end()
    lv.end()

    lv = holder(1)
    c = Raw()
    c.init()
    off = audit_off()
    os.kill(lv.p.pid, signal.SIGKILL)
    lv.p.wait(10)
    t = c.wait_eof(10)
    row("F4: the session that holds the slot is KILLED (its user table cell stays until reaped): the connection ends (%s s), why=closed"
        % ("%.1f" % t if t is not None else "never"), t is not None and has(audit_new(off), r"why=closed"), "audit %r" % audit_new(off))
    c.end()
    refused_put("F5", "the only slot is the killed session's, still in the user table", r"No transfer is open", r"no slot is open")
    if lv in lives:
        lives.remove(lv)
    subprocess.run([SD, "-cleanup"], env=g.env(False), capture_output=True, timeout=60)

    lv = holder(1)
    c1, c2 = Raw(), Raw()
    c1.init()
    c2.init()
    h1 = Raw.handle(c1.open("one.txt", WRITE | CREAT | TRUNC))
    h2 = Raw.handle(c2.open("two.txt", WRITE | CREAT | TRUNC))
    c1.write(h1, 0, b"from the first connection\n")
    c2.write(h2, 0, b"from the second\n")
    r1 = Raw.status(c1.close(h1))[0]
    r2 = Raw.status(c2.close(h2))[0]
    st = lv.ask("state")
    row("F6: two connections at once to one slot each deliver a file, and the slot counts both (2 files, 42 bytes)",
        (r1, r2) == (0, 0) and listing(XIN) == ["one.txt", "two.txt"] and st[5:7] == ["2", "42"], "state %r" % st)
    code = Raw.status(c2.req(13, s("one.txt")))[0]
    row("F6a: ...and one connection cannot remove the file the other sent", code == 3 and "one.txt" in listing(XIN))
    c1.end()
    c2.end()
    cl = lv.ask("close")
    row("F7: closing the slot answers what it moved (OK|2|42) and the state is then none", cl == ["OK", "2", "42"] and lv.ask("state")[3] == "none",
        repr(cl))
    lv.end()


# ---------------------------------------------------------------------------------------------------------------------
# M  time

def sec_timers():
    say("\n--- M. the timers (about 45 seconds) -------------------------------------------------------------------------")
    fresh(XIN)
    conf(XFER=1, XFERWAIT=10, XFERIDLE=10, XFERMAX=0)
    lv = holder(1)
    st = lv.ask("state")
    row("M1: a slot just opened is live with about XFERWAIT (10 s) to go and no connection yet", st[3] == "live" and 7 <= int(st[4]) <= 10
        and st[7] == "0", "state %r" % st)
    time.sleep(11.5)
    st = lv.ask("state")
    refused_put("M2", "XFERWAIT=10 and no connection came for 11.5 s (the session's own state says %r)" % st[3], r"run out of time",
                r"the slot ran out of time")
    row("M2a: ...the session's own view of the slot is 'wait' (ended, no connection came)", st[3] == "wait", "state %r" % st)
    lv.end()

    lv = holder(1)
    c = Raw()
    c.init()
    h = Raw.handle(c.open("idle.txt", WRITE | CREAT | TRUNC))
    c.write(h, 0, b"then nothing more\n")
    off = audit_off()
    t0 = time.time()
    t = c.wait_eof(16)
    row("M3: XFERIDLE=10: a connection that does nothing more is ended after about 10 s (%s s), why=idle, and its half-sent file is gone"
        % ("%.1f" % t if t is not None else "never"), t is not None and 8.5 <= t <= 13 and has(audit_new(off), r"why=idle")
        and listing(XIN) == [], "xfer.in %s audit %r" % (listing(XIN), audit_new(off)))
    c.end()
    lv.end()

    conf(XFER=1, XFERWAIT=10, XFERIDLE=10, XFERMAX=4)
    lv = holder(1)
    c = Raw()
    c.init()
    h = Raw.handle(c.open("max.txt", WRITE | CREAT | TRUNC))
    off = audit_off()
    t0 = time.time()
    n = 0
    ended = None
    while time.time() - t0 < 9:                          # a client that never stops writing
        r = c.write(h, n * 8, b"1234567\n")
        if not isinstance(r, tuple):
            ended = time.time() - t0
            break
        n += 1
        time.sleep(0.25)
    row("M4: XFERMAX=4: a slot in constant use still ends at about 4 s (%s s, %d writes), why=max, nothing kept"
        % ("%.1f" % ended if ended is not None else "never", n), ended is not None and 3 <= ended <= 6.5
        and has(audit_new(off), r"why=max") and listing(XIN) == [], "audit %r" % audit_new(off))
    c.end()
    lv.end()
    conf(XFER=1)


# ---------------------------------------------------------------------------------------------------------------------
# V  the verbs: RECEIVE and SEND (stage 4)

def voc_run(lines, done):
    """Run a few $internal statements as the administrator (they write or delete a VOC record of the fixture account)."""
    g.put(os.path.join(SYS, "bp", "zzxvoc"), "\n".join(["$internal"] + lines + ["   crt '%s'" % done, "end", ""]))
    out = g.adm(["BASIC bp zzxvoc", "RUN bp zzxvoc"], internal=True)
    if not g.has(out, "^%s$" % done):
        bail("the VOC fixture step did not run:\n" + "\n".join(out[-6:]))


def sec_verbs():
    say("\n--- V. receive and send --------------------------------------------------------------------------------------")
    for d in (XIN, XOUT):
        if os.path.isdir(d):
            shutil.rmtree(d)
    voc_run(["   openpath '%s/voc' to v else stop" % ACCT, "   delete v, 'xfer.in'", "   delete v, 'xfer.out'",
             "   write 'X':@fm:'a':@vm:'b' to v, 'zzmv'"], "XVOC clean")
    conf(XFER=1)
    reg(USER, ACCT, UGROUP, "yes")
    closed = r"^Transfer closed \((.*)\): (\d+) file\(s\), (\d+) bytes$"

    lv = Live(ACCT)
    off = audit_off()
    m = lv.cmd("receive", r"^Ready to receive into xfer\.in\.  Connect an sftp client to (\S+) as %s and put the files\." % USER)
    row("V1: receive, typed in the person's own account where there is no xfer.in yet, makes the directory and says it is ready",
        m is not None and os.path.isdir(XIN) and not os.path.islink(XIN), lv.text[-300:])
    data = b"id,name\n1,Ann\n2,Bo\n"
    local("v1.csv", data)
    rc, out = sftp(["put v1.csv"])
    m = lv.cmd("", closed)
    a = audit_new(off)
    row("V1a: ...a file put while it waits arrives; Enter closes the transfer, which says 'closed here', 1 file, %d bytes, and the file "
        "with hashlib's SHA-256" % len(data), rc == 0 and disk(XIN, "v1.csv") == data and m is not None
        and m.groups() == ("closed here", "1", str(len(data))) and lv.cmd("ZZXSLOT state", r"^XSLOT state OK\|0\|") is not None
        and re.search(r"^   v1\.csv   sha256 %s$" % sha(data), lv.text, re.M) is not None, lv.text[-400:])
    row("V1b: ...the audit trail has the opening (dir=in overwrite=no) and the closing (why=done files=1 bytes=%d)" % len(data),
        has(a, r"xfer open dir=in overwrite=no account=%s" % USER) and has(a, r"xfer close dir=in why=done files=1 bytes=%d account=%s" % (len(data), USER)),
        "audit %r" % a)
    out = g.plain(USER, ["CT VOC xfer.in", "CT xfer.in v1.csv"])
    row("V1c: ...and xfer.in is a file of the account: its VOC entry is F / xfer.in and the file that came is a record (CT shows its lines)",
        g.has(out, r"^\s*0*1: F$") and g.has(out, r"^\s*0*2: xfer\.in$") and g.has(out, r"^\s*0*2: 1,Ann$"), "\n".join(out[-12:]))
    refused_put("V2", "the transfer was closed with Enter", r"No transfer is open", r"no slot is open", name="v2.txt")

    local("v1.csv", b"id,name\n9,Zed\n")
    m = lv.cmd("receive overwrite", r"^Ready to receive into xfer\.in\.")
    rc, out = sftp(["put v1.csv"])
    m2 = lv.cmd("", closed)
    row("V3: receive overwrite lets the same name come again and replace the file", m is not None and rc == 0
        and disk(XIN, "v1.csv") == b"id,name\n9,Zed\n" and m2 is not None and m2.group(2) == "1", lv.text[-300:])

    m = lv.cmd("receive everything", r"^Command Syntax: receive \{overwrite\}$")
    row("V4: receive with any other word prints the syntax and opens nothing",
        m is not None and lv.cmd("ZZXSLOT state", r"^XSLOT state OK\|0\|") is not None)
    conf()
    lv.end()
    lv = Live(ACCT)                                       # XFER is read as a process starts
    m = lv.cmd("receive", r"^File transfer is not turned on for this system")
    row("V5: with XFER not 1 in sd.conf receive says so and opens nothing",
        m is not None and lv.cmd("ZZXSLOT state", r"^XSLOT state OK\|0\|") is not None, lv.text[-300:])
    lv.end()
    conf(XFER=1)
    reg(USER, ACCT, UGROUP, "")
    lv = Live(ACCT)
    m = lv.cmd("receive", r"^Account %s may not move files over its ssh login" % USER)
    row("V6: with the account's xfer field blank receive says who allows it and opens nothing",
        m is not None and lv.cmd("ZZXSLOT state", r"^XSLOT state OK\|0\|") is not None, lv.text[-300:])
    reg(USER, ACCT, UGROUP, "yes")
    lv.end()
    lv = Live(os.path.join(BOX, "user_accounts", "zzxoth"), account="zzxoth")
    voc_run(["   openpath '%s/voc' to v else stop" % os.path.join(BOX, "user_accounts", "zzxoth"),
             "   write 'V':@fm:'CA':@fm:'$xfer' to v, 'receive'"], "XVOC oth")
    m = lv.cmd("receive", r"^A transfer is opened from your own account, %s; this session is in zzxoth$" % USER)
    row("V7: receive typed in another account the person may enter is refused: a transfer is opened from one's own account",
        m is not None and lv.cmd("ZZXSLOT state", r"^XSLOT state OK\|0\|") is not None
        and not os.path.exists(os.path.join(BOX, "user_accounts", "zzxoth", "xfer.in")), lv.text[-300:])
    lv.end()

    # SEND
    src = b"program hello\n   crt 'hello'\nend\n"
    with open(os.path.join(ACCT, "bp", "hello.bas"), "wb") as f:
        f.write(src)
    fresh(LOCAL)
    lv = Live(ACCT)
    off = audit_off()
    m = lv.cmd("send bp hello.bas nosuch .dot", r"^Ready to send from xfer\.out\.  Connect an sftp client to (\S+) as %s and get the files\." % USER)
    row("V8: send copies the record that is there to xfer.out, says which were not (no such record; not a name a transfer takes), "
        "and says it is ready", m is not None and listing(XOUT) == ["hello.bas"] and "bp has no record nosuch" in lv.text
        and ".dot is not a name a transfer takes" in lv.text, lv.text[-400:])
    rc, out = sftp(["get hello.bas"])
    m = lv.cmd("", closed)
    got = disk(LOCAL, "hello.bas")
    row("V8a: ...the client gets it with the record's lines as they are in the program file, and Enter closes: 1 file",
        rc == 0 and got is not None and got.rstrip(b"\n") == src.rstrip(b"\n") and m is not None and m.group(2) == "1"
        and has(audit_new(off), r"xfer open dir=out overwrite=no") and has(audit_new(off), r"xfer close dir=out why=done files=1"),
        "local %r, audit %r" % (got, audit_new(off)))
    m = lv.cmd("send voc zzmv", r"^Nothing was copied, so no transfer was opened$")
    row("V9: a record that holds a value mark is not plain text: not copied, and with nothing copied no transfer opens",
        m is not None and "voc zzmv is not plain text" in lv.text and "zzmv" not in listing(XOUT)
        and lv.cmd("ZZXSLOT state", r"^XSLOT state OK\|0\|") is not None, lv.text[-300:])
    m = lv.cmd("send bp", r"^Command Syntax: send <file> <record id> \{<record id> \.\.\.\}$")
    row("V9a: send with no record id prints the syntax", m is not None)
    voc_run(["   openpath '%s/voc' to v else stop" % ACCT, "   write 'F':@fm:'/tmp' to v, 'xfer.out'"], "XVOC wrong")
    m = lv.cmd("send bp hello.bas", r"^xfer\.out is in this account's VOC as something other than the transfer directory")
    row("V10: a VOC entry xfer.out that points somewhere else is left alone and the transfer is refused",
        m is not None and lv.cmd("ZZXSLOT state", r"^XSLOT state OK\|0\|") is not None, lv.text[-300:])
    voc_run(["   openpath '%s/voc' to v else stop" % ACCT, "   delete v, 'xfer.out'"], "XVOC back")
    lv.end()

    # the session's input ends while it waits
    off = audit_off()
    t0 = time.time()
    try:
        p = subprocess.run([SD], input="\nTERM 200,9999\nreceive\n", cwd=ACCT, env=g.env(False), capture_output=True, text=True,
                           errors="replace", timeout=40)
        took, out = time.time() - t0, p.stdout
    except subprocess.TimeoutExpired:
        took, out = None, ""
    row("V11: a session whose input ends while receive waits closes the transfer and ends (%s s): it does not wait for ever or spin"
        % ("%.1f" % took if took is not None else "more than 40"), took is not None and took < 15
        and "Transfer closed (this session's input ended): 0 file(s), 0 bytes" in out
        and has(audit_new(off), r"xfer close dir=in why=input ended files=0 bytes=0"), "audit %r" % audit_new(off))
    subprocess.run([SD, "-cleanup"], env=g.env(False), capture_output=True, timeout=60)


# ---------------------------------------------------------------------------------------------------------------------

def main():
    global BOX, SYS, SD
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    only = [a.split("=", 1)[1].split(",") for a in sys.argv[1:] if a.startswith("--only=")]
    mutant = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mutant=")), None)
    if len(args) != 1 or (mutant and mutant not in MUTANTS) or (only and not set(only[0]) <= set(SECTIONS)):
        say("usage: sandbox-sftp.py <dir> [--build] [--only=%s] [--mutant=%s]" % (",".join(SECTIONS), "|".join(MUTANTS)))
        sys.exit(2)
    todo = only[0] if only else SECTIONS
    BOX = os.path.abspath(args[0])
    SYS = os.path.join(BOX, "sys")
    SD = os.path.join(SYS, "bin", "sd")
    g.BOX, g.SYS, g.SD = BOX, SYS, SD
    say("sandbox-sftp: sandbox  %s" % BOX)
    say("sandbox-sftp: tree     %s" % os.path.dirname(HERE))
    say("sandbox-sftp: server   %s  (SSH_ORIGINAL_COMMAND=%s, SSH_CONNECTION set)" % (SD, SUBSYS))
    say("sandbox-sftp: user %s, the account %s with register group %s; sections: %s%s"
        % (USER, USER, UGROUP, " ".join(todo), ("; MUTANT " + mutant) if mutant else ""))
    if " " in SD:
        bail("the sandbox path has a space in it (sftp -D takes the server command as words)")
    if shutil.which("sftp") is None:
        bail("there is no sftp client on this machine")
    groups = subprocess.run(["id", "-Gn"], capture_output=True, text=True).stdout.split()
    if "sdusers" not in groups or UGROUP not in groups:
        bail("the user %s is not in the Linux groups sdusers and %s (has: %s)" % (USER, UGROUP, " ".join(groups)))
    if "--build" in sys.argv:
        if os.path.exists(BOX) and os.listdir(BOX):
            bail("%s is not empty" % BOX)
        r = subprocess.run([sys.executable, g.TOOL, BOX, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-sftp: built, bootstrap passed")
    elif not os.path.isfile(SD):
        bail("%s holds no built sandbox (use --build, or point it at one)" % BOX)
    subprocess.run([sys.executable, g.TOOL, BOX, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    try:
        say("\n--- preparation ----------------------------------------------------------------------------------------------")
        prepare(mutant)
        f = g.flags(g.plain(USER, ["ZZKF"]))
        if f is None or f[0] != "0":
            bail("the ordinary session in %s is not shown as a non-administrator (KFLAGS %r)" % (USER, f))
        say("  [done] the account %s, an ordinary session in it (admin=0), xfer.in, xfer.out, XFER=1" % USER)
        for name in todo:
            globals()["sec_" + name]()
    finally:
        for lv in list(lives):
            lv.kill()
        subprocess.run([sys.executable, g.TOOL, BOX, "stop"], capture_output=True, text=True, errors="replace", timeout=120)

    say("\nsandbox-sftp: %d passed, %d failed" % (g.passed, g.failed))
    sys.exit(1 if g.failed else 0)


if __name__ == "__main__":
    main()
