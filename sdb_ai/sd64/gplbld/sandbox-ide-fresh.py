#!/usr/bin/env python3
#
# sandbox-ide-fresh.py - the IDE and home's editor tiles seen as a person meets them for the first time (S.88, Phase 0; defects I1-I5, I8, D1, D2, P2 of
#                        ~/Documents/Audits/TUI/Opus_TUI_Plan.txt, section 4).  No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-ide-fresh.py <dir> [--build] [--strict]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 every row
# that counts passed, 1 a row failed, 2 it could not run.  Rows are counted by tuirows.py: a row whose fault a LATER phase fixes is PENDING (not failed) until that
# phase has landed; --strict counts every row at its face value, which is how the red run on the unmodified tree is made.
#
# START-HISTORY:
# 28 Oct 26 dm  New (S.88 Phase 0).  Built from the probes of the evaluation (Opus_TUI_Evidence/rt0: pa_bare, pb_home, pd_new, pe_fix, pe2_gate, pf_ced,
#               pf2_tiles) and its runtime.json.
# END-HISTORY
#
# WHAT RUNS.  The administrator's sandbox session (the sandbox user plays SDSYS: `sd` in user_accounts, TERM xterm typed, then TERM 140,43) and, for the gate rows, an
# ORDINARY fixture account zzfl2 whose bp edit gate is off (made as sandbox-tool-files.py makes zzfl2; its LOGIN paragraph says TERM LINUX, so its keys are the linux
# forms).  Everything is on a PSEUDO-TERMINAL at 140 by 43.  A write is judged from the DISK (the record files of the directory files), never from what the IDE said.
#
#   I0   control   a bare IDE asks nothing before its page and draws it (the bytes before the first clear hold no question)
#   I1   bare IDE: File, New record must name a file in its question, and must not make the record in the account directory ($acc)
#   I2   bare IDE: typed text reaches an editable Untitled buffer (today the letters are tree jumps and the editor is read-only and silent)
#   I3   a one-line record: Down, then typing, stays in the editor
#   I4   Save as writes a copy AND switches the editor to it, so the next Ctrl-S saves the new record
#   I5   a refusal by the edit gate is shown where it stays (not on the status line only) and a Save refusal is not cut at 140 columns
#   I8   Ctrl-N opens a new-record form; F12 (Edit as fields) stays bound (control)
#   N3   a new record named and abandoned (Discard) leaves nothing on disk
#   D1   a pre-write trigger that refuses: Ctrl-S must not end the IDE; the buffer stays changed and the record is unchanged
#   D2   a hang-up with a changed buffer: the session ends in under 3 s, the record is as it was, and with the recovery gate off (as delivered) no copy is made
#   P2   home's Editor tile does not stop at "File name?" and the Record editor tile shows something that stays; the IDE tile opens the IDE (control)
#
# THE RECOVERY COPY (D2, plan 2.9) DOES NOT EXIST YET, so there is no red row for "the text can be got back": with its gate off, as delivered, nothing is kept and the row
# says so.  When the copy is built (Phase 2) the gate-on row is written beside it.  ROWS THAT PIN A FLOW (I1 N3, I4, I8) MAY NEED THEIR KEYS REWRITTEN when Phase 4 lands,
# red-first, in that commit; what they judge (the disk, the place a message is shown) does not change.
#
# Key-decoding rows are NOT here: sandbox-realkeys.py owns them.

import importlib.util
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ptydrive import PtySession  # noqa: E402
from tuirows import Rows  # noqa: E402


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sh = _load("sandbox_home_for_fresh", "sandbox-home.py")
say, bail, adm, g = sh.say, sh.bail, sh.adm, sh.g
R = Rows("ide-fresh")

E = "\x1b"
# the administrator's session types TERM xterm: terminfo's xterm keys.  An ordinary account's LOGIN says TERM LINUX: the linux keys.
X_UP, X_DOWN = E + "OA", E + "OB"
L_DOWN = E + "[B"
F10, F12 = E + "[21~", E + "[24~"
RET, TAB, ESC = "\r", "\t", E
CTRL_Q, CTRL_S, CTRL_N = "\x11", "\x13", "\x0e"
A1, A2 = "zzfl1", "zzfl2"
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
RUN = "%05d" % (os.getpid() % 100000)


def rid(tag):
    """a record id of this suite's own: a killed session keeps its lock, so no two rows share one"""
    return "zzif%s%s" % (tag, RUN[-3:])


class Sess:
    """One session on a pseudo-terminal.  Every key is printed (the instrument rule); waits are deadline loops, since PtySession._pump returns at the first byte."""

    def __init__(self, label, argv, cwd, term, settle=1.5, cols=140, rows=43, admin=False):
        env = dict(os.environ, SD_CONFIG=os.path.join(sh.BOX, "sd.conf"), TERM=term, LC_ALL="C", LANG="C")
        for k in ("SSH_CONNECTION", "SSH_TTY", "SDTEST_ADMIN"):
            env.pop(k, None)
        if admin:
            env["SDTEST_ADMIN"] = "1"      # the sandbox user is the administrator only with this (sandbox-gates.py prepare() patched cproc)
        self.label, self.cols, self.rows = label, cols, rows
        say("    [%s] START argv=%r cwd=%s TERM(env)=%s LC_ALL=C window=%dx%d SDBOX_KEYSET=%s SD_CONFIG=%s" % (
            label, argv, cwd, term, cols, rows, env.get("SDBOX_KEYSET"), env["SD_CONFIG"]))
        self.p = PtySession(argv, cwd, env, cols, rows)
        self.wait(settle)

    def wait(self, secs):
        end = time.time() + secs
        while time.time() < end and not self.p.exited:
            self.p._pump(min(0.2, max(0.01, end - time.time())))

    def type(self, data, wait=1.0, show=None):
        say("    [%s] KEYS %s" % (self.label, show or repr(data)))
        mark = len(self.p.raw)
        self.p.type(data, settle=False)
        self.wait(wait)
        return bytes(self.p.raw[mark:])

    def lines(self):
        return self.p.screen.lines()

    def row(self, r):
        L = self.lines()
        return L[r].rstrip() if r < len(L) else ""

    def text(self):
        return "\n".join(l.rstrip() for l in self.lines())

    def status(self):
        return self.row(self.rows - 1)

    def editor(self):
        """the editor's part of the screen: below the title and right of the tree"""
        return "\n".join(l[28:].rstrip() for l in self.lines()[3:40])

    def in_ide(self):
        return "IDE: " in self.row(1) and not self.p.exited

    def alive(self):
        self.p._pump(0.2)
        return not self.p.exited

    def show(self, title, rows=None):
        say("    --- screen: %s ---" % title)
        for i, l in enumerate(self.lines()):
            if l.strip() and (rows is None or i in rows):
                say("    %2d|%s" % (i, l.rstrip()[:140]))
        say("    ---")

    def hangup_timed(self):
        """close the master side as closing a terminal window does; returns (seconds until the process is gone, whether it went)"""
        t = time.time()
        try:
            os.close(self.p.fd)
        except OSError:
            pass
        self.p.fd = -1
        ok = self.p._reap(8.0)
        el = time.time() - t
        if not ok:
            try:
                os.kill(self.p.pid, 9)
            except OSError:
                pass
            self.p._reap(5.0)
        self.p.exited = True
        return el, ok

    def end(self):
        if self.p.exited:
            return
        if any(l.startswith(":") for l in self.lines()) and not self.in_ide():
            self.type("OFF\r", wait=1.0)
        self.p.finish(limit=3.0)


def admin(label, cmd=None, settle=1.5):
    s = Sess(label, [os.path.join(sh.SYS, "bin", "sd")], sh.SYS, "xterm", settle=settle, admin=True)
    s.type("TERM xterm\r", wait=0.6)
    s.type("TERM 140,43\r", wait=0.6)
    if cmd:
        s.type(cmd + "\r", wait=3.0, show=repr(cmd) + " RET")
    return s


def acct_dir(a):
    return os.path.join(sh.BOX, "user_accounts", a)


def ordinary(label, account, cmd):
    s = Sess(label, [os.path.join(sh.SYS, "bin", "sd"), "-a" + account], acct_dir(account), "xterm-256color", settle=3.0)
    s.type(cmd + "\r", wait=3.0, show=repr(cmd) + " RET")
    return s


def bp(name):
    return os.path.join(sh.SYS, "bp", name)


def readf(p):
    try:
        with open(p, "rb") as f:
            return f.read().decode("latin-1")
    except OSError:
        return None


def disk(p):
    t = readf(p)
    return "ABSENT" if t is None else "PRESENT %r" % t[:80]


def mk(path, text):
    with open(path, "w") as f:
        f.write(text)


def discard_all(s, down):
    """Ctrl-Q, and Discard to every 'has changes' question"""
    s.type(CTRL_Q, wait=1.5)
    n = 0
    while "has changes" in s.text() and n < 4:
        s.type(down + RET, wait=1.5, show="Down RET (Discard)")
        n += 1
    return n


# ----------------------------------------------------------------------------------------------------------------------------------------------------------------
def setup_all():
    sh.setup("sandbox-ide-fresh.py")
    if sh.tkb.failed:
        bail("the setup row failed: an ordinary session is not shown to be one, so no row below can be believed")
    R.row("SETUP control: the sandbox is built, started, and an ordinary fixture session is not an administrator", sh.tkb.passed > 0 and sh.tkb.failed == 0, "")
    g.FIXTURES[A2] = ("no", "no")
    g.build_account(A2)
    # bp edit gate OFF (fields 10 to 12 no / no / no), as sandbox-tool-files.py's zzfl2
    g.reg_write(A2, [acct_dir(A2), "", g.GROUP, "", "", "", "no", "no", "no", "no", "no", "no", "", "", "no", "", "", ""])
    fl = g.flags(g.plain(A2, ["zzkf"]))
    say("    (zzfl2 pipe session flags admin, sh, osx, user: %r)" % (fl,))
    if fl is None or fl[0] != "0":
        bail("zzfl2 is not shown to be an ordinary account (flags %r)" % (fl,))
    os.makedirs(os.path.join(acct_dir(A2), "bp"), exist_ok=True)


# ---- I0, I1, I2: the bare start -------------------------------------------------------------------------------------------------------------------------------
def section_bare():
    say("\n--- I0 / I2: a bare IDE ------------------------------------------------------------------------------------------")
    s = admin("I0")
    mark = len(s.p.raw)
    s.type("IDE\r", wait=3.0, show="'IDE' RET")
    first = bytes(s.p.raw[mark:])
    pre = ANSI.sub("", first.split(b"\x1b[2J")[0].decode("latin-1"))
    say("    bytes written before the first clear, escapes removed: %r" % pre[:160])
    R.row("I0 control: a bare IDE asks no question before its page, and the page is drawn (menu bar on row 0, 'IDE:' on row 1)",
          b"\x1b[2J" in first and "?" not in pre and re.search(r"File\s+Go\s+Search", s.row(0)) is not None and s.in_ide(),
          "pre=%r row0=%r row1=%r" % (pre[:80], s.row(0)[:60], s.row(1)[:60]))
    s.show("bare IDE", rows=range(0, 8))
    before = s.editor()
    s.type("hello", wait=1.2, show="'hello' (typed with the focus where the IDE put it)")
    e1 = s.editor()
    s.type(TAB, wait=0.8)
    s.type(TAB, wait=0.8)
    s.type("abc", wait=1.2, show="'abc' (after Tab Tab)")
    e2 = s.editor()
    s.show("after hello, Tab Tab, abc")
    R.row("I2 control: the instrument saw the editor part of the screen before and after (the page is there to type into)", s.in_ide() and "File" in s.row(0), "row1=%r" % s.row(1)[:60])
    ok = ("hello" in e2) or ("abc" in e2)
    R.row("I2 a bare IDE has an editable buffer: 'hello' typed at the start or 'abc' typed after Tab Tab shows in the editor (today the letters are tree jumps and the editor is silent)",
          ok, "editor before=%r after=%r status=%r" % (before.strip()[:60], e2.strip()[:100], s.status()[:100]), phase=4)
    s.end()


def section_new():
    say("\n--- I1: New record from a bare start ----------------------------------------------------------------------------")
    n1 = rid("n1")
    s = admin("I1", "IDE")
    ok_ide = s.in_ide()
    s.type(F10, wait=1.0, show="F10")
    s.type(RET, wait=1.5, show="RET (File, New record)")
    T = s.text()
    ql = next((i for i, l in enumerate(s.lines()) if re.search(r"(?i)name of the new|new record", l) and i > 1), None)
    box = ""
    if ql is not None:
        box = "\n".join(l[max(0, l.lower().find("name of")-12):] for l in s.lines()[max(0, ql - 3):ql + 4])
    s.show("the New record question", rows=range(max(0, (ql or 12) - 4), (ql or 12) + 5))
    R.row("I1 control: File, New record asks for a name from a bare start", ok_ide and ql is not None, "ok_ide=%r row=%r" % (ok_ide, ql))
    R.row("I1 the question names the file the record will be made in (a word 'bp' in the box; today it names nothing)",
          re.search(r"\bbp\b", box) is not None, "box=%r" % box[:200], phase=4)
    s.type(n1, wait=0.6, show=repr(n1))
    s.type(RET, wait=2.5, show="RET")
    s.show("after naming %s" % n1, rows=[0, 1, 2, 3, 42])
    in_acc = readf(os.path.join(sh.SYS, n1))
    say("    disk: account directory %s: %s   bp: %s" % (os.path.join(sh.SYS, n1), disk(os.path.join(sh.SYS, n1)), disk(bp(n1))))
    R.row("I1 a New record from a bare start does NOT make the record in the account directory ($acc) (today it does, empty)", in_acc is None, "the file %s exists in the account directory" % n1, phase=4)
    discard_all(s, X_DOWN)
    s.end()
    if in_acc is not None:
        os.remove(os.path.join(sh.SYS, n1))

    say("\n--- I1 control: New record with a bp record open goes into bp ----------------------------------------------------")
    r2, n2 = rid("r2"), rid("n2")
    mk(bp(r2), "base\n")
    s = admin("I1c", "IDE bp %s" % r2)
    open_ok = ("bp %s" % r2) in s.status()
    s.type(F10, wait=1.0, show="F10")
    s.type(RET, wait=1.5, show="RET (File, New record)")
    s.type(n2, wait=0.6, show=repr(n2))
    s.type(RET, wait=2.0, show="RET")
    s.type("fresh text", wait=1.2, show="'fresh text'")
    s.type(CTRL_S, wait=2.0, show="Ctrl-S")
    s.show("after Ctrl-S", rows=[0, 1, 2, 3, 42])
    t = readf(bp(n2))
    say("    disk: bp/%s: %s   account directory: %s" % (n2, disk(bp(n2)), disk(os.path.join(sh.SYS, n2))))
    R.row("I1 control: with a bp record open, New record then typed text and Ctrl-S leave the record in the bp file (and not in the account directory)",
          open_ok and t is not None and "fresh text" in t and readf(os.path.join(sh.SYS, n2)) is None, "open_ok=%r bp=%r" % (open_ok, t))
    discard_all(s, X_DOWN)
    s.end()


def section_abandon():
    say("\n--- N3: a new record named and abandoned ------------------------------------------------------------------------")
    r3, n3 = rid("r3"), rid("n3")
    mk(bp(r3), "base\n")
    s = admin("N3", "IDE bp %s" % r3)
    s.type(F10, wait=1.0, show="F10")
    s.type(RET, wait=1.5, show="RET (File, New record)")
    s.type(n3, wait=0.6, show=repr(n3))
    s.type(RET, wait=2.0, show="RET")
    s.type("temp", wait=1.2, show="'temp'")
    typed = "temp" in s.editor()
    s.type(CTRL_Q, wait=1.5, show="Ctrl-Q")
    asked = "has changes" in s.text()
    s.show("the quit question", rows=range(10, 30))
    n = 0
    while "has changes" in s.text() and n < 4:
        s.type(X_DOWN + RET, wait=1.5, show="Down RET (Discard)")
        n += 1
    s.wait(1.0)
    say("    disk after Discard: bp/%s: %s   account directory: %s" % (n3, disk(bp(n3)), disk(os.path.join(sh.SYS, n3))))
    R.row("N3 control: the name was taken, the text 'temp' reached the editor, and Ctrl-Q asked what to do with the changes", typed and asked, "typed=%r asked=%r" % (typed, asked))
    gone = readf(bp(n3)) is None and readf(os.path.join(sh.SYS, n3)) is None
    R.row("N3 a new record named and then abandoned with Discard leaves nothing on disk (today an empty record stays)", gone,
          "bp=%s acc=%s" % (disk(bp(n3)), disk(os.path.join(sh.SYS, n3))), phase=4)
    s.end()
    for p in (bp(n3), os.path.join(sh.SYS, n3)):
        if os.path.isfile(p):
            os.remove(p)


# ---- I5: the edit gate off -------------------------------------------------------------------------------------------------------------------------------
def section_gate():
    say("\n--- I5: an ordinary account whose bp edit gate is off -----------------------------------------------------------")
    old = os.path.join(acct_dir(A2), "bp", "zzold")
    mk(old, "old text\n")
    ng = rid("g")
    pg = os.path.join(acct_dir(A2), "bp", ng)
    s = ordinary("I5a", A2, "IDE bp zzold")
    s.type(F10, wait=1.0, show="F10")
    s.type(RET, wait=1.5, show="RET (File, New record)")
    s.type(ng, wait=0.6, show=repr(ng))
    s.type(RET, wait=2.0, show="RET")
    L = s.lines()
    s.show("after the name was given", rows=range(0, 6))
    say("    status row: %r" % s.status())
    refused = "bp.edit" in s.text()
    R.row("I5 control: the IDE page is up in the ordinary account, nothing is written (%s) and the refusal is said somewhere (the words bp.edit are on the screen)" % ng,
          s.in_ide() and readf(pg) is None and refused, "in_ide=%r disk=%s refused=%r" % (s.in_ide(), disk(pg), refused))
    inbody = any("bp.edit" in l for l in L[1:s.rows - 1])
    s.wait(4.0)
    inbody2 = any("bp.edit" in l for l in s.lines()[1:s.rows - 1])
    R.row("I5 the refusal of New record is shown in a box or form that stays (on a row above the status line, and still there 4 s later), not on the status line only",
          inbody and inbody2, "above status now=%r after 4 s=%r status=%r" % (inbody, inbody2, s.status()[:100]), phase=4)
    s.end()

    s = ordinary("I5b", A2, "IDE bp zzold")
    s.type("NEW ", wait=1.2, show="'NEW '")
    changed = " *" in s.status()
    s.type(CTRL_S, wait=2.0, show="Ctrl-S")
    s.show("after Ctrl-S", rows=range(0, 6))
    say("    status row: %r" % s.status())
    flat = " ".join(l.strip() for l in s.lines())
    R.row("I5 control: the buffer was marked changed, Ctrl-S was refused (bp.edit is named) and the record on disk is as it was",
          changed and "bp.edit" in flat and readf(old) == "old text\n", "changed=%r disk=%s" % (changed, disk(old)))
    R.row("I5 the Save refusal is whole on the screen, not cut at 140 columns (its last words 'bp-on)' are shown; today the status line ends at 'modify.accou')",
          "bp-on)" in flat, "status=%r" % s.status()[:140], phase=4)
    s.end()


# ---- I3: Down at the edge of the editor ------------------------------------------------------------------------------------------------------------------
def section_edge():
    say("\n--- I3: Down in a one-line record ------------------------------------------------------------------------------")
    r6 = rid("r6")
    mk(bp(r6), "single\n")
    s = admin("I3", "IDE bp %s" % r6)
    s.type("ZZ", wait=1.2, show="'ZZ'")
    e1 = s.editor()
    R.row("I3 control: with the record open the letters reach the editor ('ZZ' is in front of the text and the record is marked changed)",
          "ZZsingle" in e1 and " *" in s.status(), "editor=%r status=%r" % (e1.strip()[:60], s.status()[:80]))
    s.type(X_DOWN, wait=1.0, show="Down")
    say("    status row after Down: %r" % s.status())
    s.type("QQ", wait=1.2, show="'QQ'")
    e2 = s.editor()
    s.show("after Down and QQ", rows=[2, 3, 4, 42])
    R.row("I3 Down in a one-line record, then typing: 'QQ' reaches the editor (today the focus moves to Messages and the letters are dropped)",
          "QQ" in e2, "status=%r editor=%r" % (s.status()[:80], e2.strip()[:80]), phase=4)
    s.end()


# ---- I4: Save as -----------------------------------------------------------------------------------------------------------------------------------------
def section_saveas():
    say("\n--- I4: Save as -------------------------------------------------------------------------------------------------")
    r5, c5 = rid("r5"), rid("c5")
    mk(bp(r5), "orig\n")
    s = admin("I4", "IDE bp %s" % r5)
    s.type("NEW", wait=1.0, show="'NEW'")
    s.type(F10, wait=1.0, show="F10")
    s.type(X_DOWN + X_DOWN, wait=0.8, show="Down Down (to Save as)")
    s.type(RET, wait=1.5, show="RET (Save as)")
    asked = "Name of the new record" in s.text()
    s.type(c5, wait=0.6, show=repr(c5))
    s.type(RET, wait=2.0, show="RET")
    s.show("after Save as", rows=[0, 1, 2, 3, 42])
    s.type("MORE", wait=1.2, show="'MORE'")
    s.type(CTRL_S, wait=2.0, show="Ctrl-S")
    s.show("after the Ctrl-S that follows", rows=[0, 1, 2, 3, 42])
    orig, cp = readf(bp(r5)), readf(bp(c5))
    say("    disk: original bp/%s: %s   copy bp/%s: %s" % (r5, disk(bp(r5)), c5, disk(bp(c5))))
    R.row("I4 control: Save as asked for a name and wrote the copy with the first change ('NEW' and 'orig' are in it)",
          asked and cp is not None and "NEW" in cp and "orig" in cp, "asked=%r copy=%r" % (asked, cp))
    R.row("I4 Save as switches the editor to the new record: the next Ctrl-S saves the COPY (it holds 'MORE') and the original is as it was ('orig' only)",
          cp is not None and "MORE" in cp and orig is not None and orig.strip() == "orig", "original=%r copy=%r" % (orig, cp), phase=4)
    discard_all(s, X_DOWN)
    s.end()


# ---- I8: Ctrl-N, and F12 stays ---------------------------------------------------------------------------------------------------------------------------
def section_keys():
    say("\n--- I8: Ctrl-N, F12 ---------------------------------------------------------------------------------------------")
    r9 = rid("r9")
    mk(bp(r9), "nine\n")
    pat = re.compile(r"(?i)new record|name of the")
    s = admin("I8a", "IDE bp %s" % r9)
    before = bool(pat.search(s.text()))
    s.type(F12, wait=2.0, show="F12 (Edit as fields)")
    title = s.row(0).strip()
    say("    row 0 after F12: %r" % title)
    R.row("I8 control: F12 stays bound: CED opens on the record as fields ('Collection editor: bp %s' on row 0)" % r9, title.startswith("Collection editor: bp %s" % r9), repr(title))
    s.end()

    s = admin("I8b", "IDE bp %s" % r9)
    s.type(F10, wait=1.0, show="F10")
    s.type(RET, wait=1.5, show="RET (File, New record)")
    ctl = bool(pat.search(s.text()))
    s.end()
    R.row("I8 control: the marker for a new-record form (the words 'new record' or 'name of the') is not on the screen before and is there after File, New record", ctl and not before,
          "before=%r after the menu=%r" % (before, ctl))

    s = admin("I8c", "IDE bp %s" % r9)
    s.type(CTRL_N, wait=1.5, show="Ctrl-N")
    s.show("after Ctrl-N", rows=range(0, 6))
    got = bool(pat.search(s.text()))
    R.row("I8 Ctrl-N opens a new-record form (today the key does nothing)", got, "status=%r" % s.status()[:100], phase=4)
    s.end()


# ---- D1: a refusing trigger ------------------------------------------------------------------------------------------------------------------------------
def section_trigger():
    say("\n--- D1: a pre-write trigger that refuses -------------------------------------------------------------------------")
    trg = "subroutine zzifttrg(mode, id, data, on.error, fvar)\n   if mode = 1 then @trigger.return.code = 1\nend\n"
    ctl = "   open 'zzift' to f else crt 'ZCTL no zzift' ; stop\n   write 'x' to f, 'r7' on error crt 'ZCTL WERR[':status():']'\n   crt 'ZCTL end'\nend\n"
    mk(bp("zzifttrg"), trg)
    mk(bp("zzift_ctl"), ctl)
    out = adm("DELETE.FILE zzift", "CREATE.FILE zzift DIRECTORY", "BASIC bp zzifttrg", "BASIC bp zzift_ctl", "CATALOG bp zzifttrg LOCAL")
    d = os.path.join(sh.SYS, "zzift")
    if not os.path.isdir(d) or sum(1 for l in out if re.match(r"^Compiled 1 program\(s\) with no errors", l)) != 2:
        bail("the trigger fixture was not made:\n" + "\n".join(out[-8:]))
    mk(os.path.join(d, "r7"), "seven\n")
    out = adm("SET.TRIGGER zzift zzifttrg PRE.WRITE", "RUN bp zzift_ctl")
    say("    control program: %r" % [l for l in out if "ZCTL" in l])
    R.row("D1 control: the trigger refuses a write to zzift (a program's WRITE ... ON ERROR gets status 3022) and the record on disk is as it was",
          any("ZCTL WERR[3022]" in l for l in out) and readf(os.path.join(d, "r7")) == "seven\n", repr(out[-4:]))
    s = admin("D1", "IDE zzift r7")
    opened = "zzift r7" in s.status()
    s.type("ZZ", wait=1.2, show="'ZZ'")
    changed = " *" in s.status()
    R.row("D1 control: the record of the directory file with the trigger opens and 'ZZ' marks it changed", opened and changed, "status=%r" % s.status()[:100])
    s.type(CTRL_S, wait=3.0, show="Ctrl-S (refused by the trigger)")
    s.show("after Ctrl-S", rows=range(0, 6))
    say("    status row: %r  process alive: %r" % (s.status()[:120], s.alive()))
    R.row("D1 the record on disk is unchanged after the refused save", readf(os.path.join(d, "r7")) == "seven\n", disk(os.path.join(d, "r7")))
    # the old page stays drawn under an abort (the process is back at the command line with the error printed over it), so the screen alone proves nothing:
    # the abort's own words must be absent as well
    abort = "Error 3022" in s.text() or "Data validation error" in s.text() or "writing record" in s.text()
    say("    abort words on the screen: %r" % abort)
    R.row("D1 a refused write does not end the IDE: no abort message, the page is still up and the buffer is still marked changed (today the IDE is aborted to the command line with 'Error 3022 ... at line 1161 of $ide' and the text lost)",
          s.alive() and s.in_ide() and " *" in s.status() and not abort, "alive=%r in_ide=%r abort=%r status=%r" % (s.alive(), s.in_ide(), abort, s.status()[:80]), phase=2)
    s.end()
    adm("SET.TRIGGER zzift ''")


# ---- D2: a hang-up with a changed buffer -----------------------------------------------------------------------------------------------------------------
def sigs():
    d = {}
    for base in (sh.SYS, os.path.join(sh.SYS, "bp")):
        for n in os.listdir(base):
            p = os.path.join(base, n)
            if os.path.isfile(p):
                st = os.stat(p)
                d[p] = (st.st_mtime_ns, st.st_size)
    return d


def section_hangup():
    say("\n--- D2: a hang-up with a changed buffer --------------------------------------------------------------------------")
    r8 = rid("r8")
    mk(bp(r8), "kept\n")
    s = admin("D2", "IDE bp %s" % r8)
    s.type("DIRTYMARK", wait=1.5, show="'DIRTYMARK'")
    changed = " *" in s.status() and "DIRTYMARK" in s.editor()
    before = sigs()
    el, went = s.hangup_timed()
    time.sleep(1.0)
    after = sigs()
    moved = [p for p in after if before.get(p) != after[p]]
    holders = []
    for p in moved:
        if after[p][1] < 2000000:
            t = readf(p)
            if t is not None and "DIRTYMARK" in t:
                holders.append(p)
    say("    hang-up: the process was gone after %.2f s (went=%r); files new or changed in the account directory and bp: %r; holding the text: %r" % (el, went, [os.path.basename(p) for p in moved], holders))
    R.row("D2 control: the buffer was changed ('DIRTYMARK' shown, record marked changed) before the hang-up", changed, "status=%r" % s.status()[:80])
    R.row("D2 control: the session ends in under 3 s of the hang-up", went and el < 3.0, "%.2f s went=%r" % (el, went))
    R.row("D2 control: the record on disk is as it was after the hang-up", readf(bp(r8)) == "kept\n", disk(bp(r8)))
    R.row("D2 control: with the recovery gate off (as delivered) no copy of the text is made anywhere in the account directory or bp (the copy is not built yet)", not holders, repr(holders))


# ---- P2: home's tiles ------------------------------------------------------------------------------------------------------------------------------------
def focus_of(s):
    return [s.p.screen.reverse(r) for r in range(3, 40) if s.p.screen.reverse(r)]


def tile(label, move):
    s = admin(label, "HOME")
    if "Sign out" not in s.text():
        s.show("home did not draw")
        return s, None
    s.type("i", wait=1.0, show="'i' (to the IDE tile)")
    if move:
        s.type(move, wait=1.0)
    return s, focus_of(s)


def section_home():
    say("\n--- P2: home's tiles ---------------------------------------------------------------------------------------------")
    s, f = tile("P2i", None)
    ok_f = f is not None and "IDE" in f
    say("    focus before Enter: %r" % (f,))
    mark = len(s.p.raw)
    if ok_f:
        s.type(RET, wait=3.5, show="RET (start the IDE tile)")
    R.row("P2 control: home draws, the IDE tile has the focus, and Enter starts the IDE", ok_f and s.in_ide(), "focus=%r row1=%r" % (f, s.row(1)[:60]))
    s.end()

    s, f = tile("P2e", E + "OD")
    ok_f = f is not None and "Editor" in f
    say("    focus before Enter: %r" % (f,))
    if not ok_f:
        R.row("P2 control: the Editor tile has the focus before Enter (the instrument reached the tile)", False, "focus=%r" % (f,))
    else:
        R.row("P2 control: the Editor tile has the focus before Enter (the instrument reached the tile)", True, "")
        s.type(RET, wait=3.5, show="RET (start the Editor tile)")
        s.show("3.5 s after the Editor tile", rows=range(0, 4))
        asked = "File name?" in s.text()
        say("    'File name?' on the screen: %r  last row: %r" % (asked, s.status()[:60]))
        R.row("P2 the Editor tile does not stop at a 'File name?' question at the command line", not asked, "the screen asks: %r" % s.status()[:60], phase=5)
        if asked:
            s.type(RET, wait=1.5, show="RET (an empty answer)")
    s.end()

    s, f = tile("P2r", E + "OC")
    ok_f = f is not None and "Record editor" in f
    say("    focus before Enter: %r" % (f,))
    if not ok_f:
        R.row("P2 control: the Record editor tile has the focus before Enter (the instrument reached the tile)", False, "focus=%r" % (f,))
    else:
        R.row("P2 control: the Record editor tile has the focus before Enter (the instrument reached the tile)", True, "")
        beforel = set(l.rstrip() for l in s.lines()[4:] if l.strip())
        mark = len(s.p.raw)
        s.type(RET, wait=3.5, show="RET (start the Record editor tile)")
        got = bytes(s.p.raw[mark:])
        s.show("3.5 s after the Record editor tile", rows=range(0, 6))
        new = [l.rstrip() for l in s.lines()[4:] if l.strip() and l.rstrip() not in beforel]
        say("    bytes written after Enter: %d; lines on the screen that were not there before: %r" % (len(got), new[:6]))
        R.row("P2 control: Enter on the Record editor tile did something (the program wrote to the terminal)", len(got) > 100, "%d bytes" % len(got))
        R.row("P2 the Record editor tile leaves a picker or a message that STAYS on the screen (today a bare ced prints 'File name required' and home redraws over it within the same burst)",
              len(new) > 0, "nothing new 3.5 s later; row 0-2: %r" % [s.row(i)[:50] for i in range(3)], phase=5)
    s.end()


def main():
    try:
        setup_all()
        section_bare()
        section_new()
        section_abandon()
        section_gate()
        section_edge()
        section_saveas()
        section_keys()
        section_trigger()
        section_hangup()
        section_home()
    finally:
        sh.teardown()
    sys.exit(R.finish())


if __name__ == "__main__":
    main()
