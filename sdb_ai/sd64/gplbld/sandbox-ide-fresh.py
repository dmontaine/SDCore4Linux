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
#   P2   home's Editor tile does not stop at "File name?"; the IDE tile opens the IDE (control).  The Record editor tile's rows (P2r) were removed on 29 Oct 26 with the tile (S.88 g-P1)
#   L    (28 Oct 26, Phase 4, plan 4.9) the whole loop from a bare start in an ordinary account with the edit gates on: type a program with an error, F8 (compile) names it in the
#        name form and shows the error and its line, fix it, Ctrl-S, F8 clean, F9 (build) catalogues, and the program runs from the account's command line by its name; and in
#        an account whose bp edit gate is off the same flow stops at the save with the reason in the form (rows L1-L8)
#   K    (28 Oct 26, Phase 4, the owner's keys of 20 Oct, D28 / D31 / D32 / D33) F2 does not save (Ctrl-S is the only save key, with its control); Ctrl-W closes the record
#        (asks Save / Discard / Cancel when changed, closes at once when not, and no longer asks for the name of a copy); Write a copy is a File menu entry (rows K1-K9)
#   T    the tree no longer lists the $ entries ($acc, $hold, $map, $release), with a control that it lists the files (row T1)
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
F8, F9 = E + "[19~", E + "[20~"          # compile, build (compile and catalogue): the owner's keys of 20 Oct, S.88 Phase 4 (F7 is debug now)
X_F2 = E + "OQ"                          # F2 in terminfo's xterm: it saved before Phase 4 and does nothing now (Ctrl-S is the only save key)
RET, TAB, ESC = "\r", "\t", E
CTRL_Q, CTRL_S, CTRL_N, CTRL_W = "\x11", "\x13", "\x0e", "\x17"
DOWN_SAVEAS, DOWN_COPY = 3, 4            # File menu: New record, Open record, Save, Save as, Write a copy, Close record, Quit - Down this many times from New record
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
        return self.row(self.rows - 3)         # 28 Oct 26: the status line is three rows above the last (then the border and the function-key row); it was the last row

    def editor(self):
        """the editor's part of the screen: below the title and right of the tree"""
        return "\n".join(l[28:].rstrip() for l in self.lines()[3:39])          # row 39 is the form's bottom border since the IDE's foot (28 Oct 26)

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
    s.show("after naming %s" % n1, rows=[0, 1, 2, 3, 40])
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
    s.show("after Ctrl-S", rows=[0, 1, 2, 3, 40])
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
    inbody = any("bp.edit" in l for l in L[1:s.rows - 3])
    s.wait(4.0)
    inbody2 = any("bp.edit" in l for l in s.lines()[1:s.rows - 3])
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
    s.show("after Down and QQ", rows=[2, 3, 4, 40])
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
    s.type(X_DOWN * DOWN_SAVEAS, wait=0.8, show="Down x%d (to Save as: New record, Open record, Save, Save as)" % DOWN_SAVEAS)
    s.type(RET, wait=1.5, show="RET (Save as)")
    asked = "Name of the new record" in s.text()
    s.type(c5, wait=0.6, show=repr(c5))
    s.type(RET, wait=2.0, show="RET")
    s.show("after Save as", rows=[0, 1, 2, 3, 40])
    s.type("MORE", wait=1.2, show="'MORE'")
    s.type(CTRL_S, wait=2.0, show="Ctrl-S")
    s.show("after the Ctrl-S that follows", rows=[0, 1, 2, 3, 40])
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
    # 30 Oct 26 (CED in the IDE, stage 2a): the fields view is drawn INSIDE the IDE's form, so the IDE's menu bar stays on row 0 and the view's path line ('Path: /') is on the screen
    R.row("I8 control: F12 stays bound: the fields view opens on the record inside the IDE (the menu bar on row 0, 'Path: /' and the 'Name Type Value' header on the screen)",
          title.startswith("File") and "Path: /" in s.text() and "Name" in s.text() and "Value" in s.text(), repr(title))
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

    # 29 Oct 26, S.88 g-P1: the Record editor tile (P2r) is gone with the ced verb; its two rows are removed, not rewritten - there is no tile to start.


# ---- L: the whole loop inside the IDE (plan 4.9) ---------------------------------------------------------------------------------------------------------------
def section_loop():
    say("\n--- L: edit, compile, see the errors, fix, save and catalogue, from a bare start (plan 4.9) ---------------------------------------")
    rid1 = rid("lp")
    g.FIXTURES[A1] = ("no", "no")
    g.build_account(A1)             # the edit gates are on (the fixture default); the account has bp and cat directories
    fl = g.flags(g.plain(A1, ["zzkf"]))
    say("    (zzfl1 pipe session flags admin, sh, osx, user: %r)" % (fl,))
    if fl is None or fl[0] != "0":
        bail("zzfl1 is not shown to be an ordinary account (flags %r)" % (fl,))
    os.makedirs(os.path.join(acct_dir(A1), "bp"), exist_ok=True)
    rec = os.path.join(acct_dir(A1), "bp", rid1)
    s = ordinary("L1", A1, "IDE")
    ok_ide = s.in_ide()
    s.type('crt "LOOPOK"' + RET + "x = = 1" + RET + "end", wait=1.5, show="the program: three lines, line 2 wrong")
    typed = 'x = = 1' in s.editor()
    s.type(F8, wait=2.0, show="F8 (compile) on the untitled buffer")
    asked = "Name of the new record" in s.text()
    s.show("the first-save form", rows=range(8, 30))
    R.row("L1 control: a bare IDE took the program into its Untitled buffer, and F8 on it asked for the file and the record in the name form",
          ok_ide and typed and asked, "ok_ide=%r typed=%r asked=%r" % (ok_ide, typed, asked))
    s.type(rid1 + RET, wait=4.0, show=repr(rid1) + " RET")
    s.show("after the name: the compile", rows=[0, 1, 2, 3, 4, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42])
    st = s.status()
    R.row("L2 the record was written by the first save, in bp (the form's default file), and the compile shows its error with the line: '1 error(s) in bp %s' and the cursor on line 2" % rid1,
          readf(rec) is not None and re.search(r"1 error\(s\) in bp %s" % rid1, st) is not None and "Line 2," in st, "disk=%s status=%r" % (disk(rec), st[:120]))
    s.type("\x1b[3~" * 7 + "x = 1", wait=1.2, show="Delete x7, then 'x = 1' (the fix, at the error's line)")
    s.type(CTRL_S, wait=2.0, show="Ctrl-S")
    saved = readf(rec)
    R.row("L3 the fix is saved to the same record with Ctrl-S (no second question)", saved is not None and "x = 1" in saved and "x = = 1" not in saved and "Name of the new record" not in s.text(),
          "disk=%s status=%r" % (disk(rec), s.status()[:100]))
    s.type(F8, wait=3.0, show="F8 (compile)")
    R.row("L4 a clean compile (F8) says so and names the record", ("Compiled bp %s with no errors" % rid1) in s.status(), s.status()[:120])
    s.type(F9, wait=3.0, show="F9 (build: compile and catalogue)")
    R.row("L5 F9 catalogues and says so only after CATALOG said it did: 'Catalogued bp %s'" % rid1, ("Catalogued bp %s" % rid1) in s.status(), s.status()[:120])
    s.type(CTRL_Q, wait=1.5, show="Ctrl-Q")
    s.end()
    out = g.plain(A1, [rid1])
    R.row("L6 the program runs from the command line of the account by its name (it printed LOOPOK)", any("LOOPOK" in ln for ln in out), repr(out[-4:]))

    say("\n--- L: the same flow in an account whose bp edit gate is off: it stops at the save, with the reason in the form -------------------")
    rid2 = rid("lq")
    rec2 = os.path.join(acct_dir(A2), "bp", rid2)
    s = ordinary("L7", A2, "IDE")
    s.type('crt "NO"', wait=1.0, show="a program")
    s.type(CTRL_S, wait=2.0, show="Ctrl-S on the untitled buffer")
    s.type(rid2 + RET, wait=2.0, show=repr(rid2) + " RET")
    s.show("the form after the refusal", rows=range(8, 30))
    R.row("L7 the form stays open and says why (bp.edit is named), and nothing was written", "bp.edit" in s.text() and "Name of the new record" in s.text() and readf(rec2) is None and s.in_ide(),
          "disk=%s in_ide=%r" % (disk(rec2), s.in_ide()))
    s.type(ESC, wait=1.0, show="Esc (Cancel)")
    R.row("L8 Esc leaves the form: the IDE goes on with its buffer, which is still marked changed or untitled, and the disk has nothing", s.in_ide() and readf(rec2) is None and "Name of the new record" not in s.text(),
          "in_ide=%r status=%r" % (s.in_ide(), s.status()[:100]))
    discard_all(s, L_DOWN)
    s.end()


# ---- K: the keys that changed meaning (the owner's keys of 20 Oct, D28 / D31 / D32 / D33) ---------------------------------------------------------------------------
def tab_row(s):
    """the tab row (row 2): the record tabs, each as [id], or the Untitled buffer's label"""
    return s.row(2)


def section_oldkeys():
    say("\n--- K: F2 no longer saves; Ctrl-W closes the record; Write a copy is a menu entry -------------------------------------------------")
    r10 = rid("k2")
    mk(bp(r10), "ten\n")
    s = admin("K2", "IDE bp %s" % r10)
    s.type("ZZ", wait=1.2, show="'ZZ'")
    changed = " *" in s.status() and "ZZten" in s.editor()
    R.row("K1 control: with the record open 'ZZ' reaches the editor and the record is marked changed (the buffer F2 is pressed in has something to save)",
          changed, "status=%r editor=%r" % (s.status()[:80], s.editor().strip()[:60]))
    s.type(X_F2, wait=2.0, show="F2 (it saved before Phase 4)")
    after_f2 = readf(bp(r10))
    still = " *" in s.status() and s.in_ide()
    s.show("after F2", rows=[0, 1, 2, 3, 40])
    R.row("K2 F2 does not save: the record on disk is as it was and the buffer is still marked changed (Ctrl-S is the only save key)",
          after_f2 == "ten\n" and still, "disk=%s still_changed=%r status=%r" % (disk(bp(r10)), still, s.status()[:80]))
    s.type(CTRL_S, wait=2.0, show="Ctrl-S")
    after_cs = readf(bp(r10))
    R.row("K3 control: Ctrl-S saves the very same buffer ('ZZten' reaches the disk), so K2 was judged on a buffer that could be saved",
          after_cs is not None and "ZZten" in after_cs, "disk=%s" % disk(bp(r10)))
    s.end()

    r11 = rid("k4")
    mk(bp(r11), "eleven\n")
    s = admin("K4", "IDE bp %s" % r11)
    tab_before = ("[%s]" % r11) in tab_row(s)
    s.type("ZZ", wait=1.2, show="'ZZ'")
    s.type(CTRL_W, wait=1.5, show="Ctrl-W (close the record; it was Write a copy)")
    asked = "has changes" in s.text()
    named = "Name of the new record" in s.text()
    s.show("after Ctrl-W on a changed record", rows=range(0, 30))
    R.row("K4 control: before Ctrl-W the record is open in the editor (its tab [%s] is on the tab row)" % r11, tab_before, "tab row=%r" % tab_row(s)[:80])
    R.row("K5 Ctrl-W on a changed record asks what to do with the changes ('has changes') and does not ask for the name of a copy (it used to be Write a copy)",
          asked and not named, "asked=%r name_form=%r" % (asked, named))
    s.type(X_DOWN + RET, wait=1.5, show="Down RET (Discard)")
    s.show("after Discard", rows=[0, 1, 2, 3, 40])
    gone = ("[%s]" % r11) not in tab_row(s) and re.search(r"Untitled \d", s.text()) is not None
    R.row("K6 Discard closes the record: its tab is gone, an Untitled buffer takes its place, the IDE is still up and the record on disk is as it was",
          gone and s.in_ide() and readf(bp(r11)) == "eleven\n", "tab row=%r in_ide=%r disk=%s" % (tab_row(s)[:80], s.in_ide(), disk(bp(r11))))
    s.end()

    r12 = rid("k7")
    mk(bp(r12), "twelve\n")
    s = admin("K7", "IDE bp %s" % r12)
    tab_before = ("[%s]" % r12) in tab_row(s)
    s.type(CTRL_W, wait=1.5, show="Ctrl-W on an unchanged record")
    s.show("after Ctrl-W", rows=[0, 1, 2, 3, 40])
    closed = ("[%s]" % r12) not in tab_row(s) and re.search(r"Untitled \d", s.text()) is not None
    R.row("K7 Ctrl-W on an unchanged record closes it at once: no question, no name form, its tab gone, an Untitled buffer in its place (the tab was there before: %r)" % tab_before,
          tab_before and closed and "has changes" not in s.text() and "Name of the new record" not in s.text() and s.in_ide() and readf(bp(r12)) == "twelve\n",
          "tab row=%r in_ide=%r disk=%s" % (tab_row(s)[:80], s.in_ide(), disk(bp(r12))))
    s.end()

    r13, c13 = rid("k8"), rid("c8")
    mk(bp(r13), "thirteen\n")
    s = admin("K8", "IDE bp %s" % r13)
    s.type("ZZ", wait=1.2, show="'ZZ'")
    s.type(F10, wait=1.0, show="F10")
    s.type(X_DOWN * DOWN_COPY, wait=0.8, show="Down x%d (to Write a copy: New record, Open record, Save, Save as, Write a copy)" % DOWN_COPY)
    s.type(RET, wait=1.5, show="RET (Write a copy)")
    asked = "Name of the new record" in s.text()
    s.show("the Write a copy form", rows=range(8, 30))
    s.type(c13, wait=0.6, show=repr(c13))
    s.type(RET, wait=2.0, show="RET")
    cp = readf(bp(c13))
    orig = readf(bp(r13))
    R.row("K8 File, Write a copy asked for a name and wrote the copy with the buffer's text ('ZZthirteen'), and the record being edited is as it was on the disk",
          asked and cp is not None and "ZZthirteen" in cp and orig == "thirteen\n", "asked=%r copy=%s original=%s" % (asked, disk(bp(c13)), disk(bp(r13))))
    s.type(CTRL_S, wait=2.0, show="Ctrl-S")
    orig2 = readf(bp(r13))
    R.row("K9 Write a copy does not switch the editor to the copy (that is Save as): the next Ctrl-S saves the ORIGINAL ('ZZthirteen' in it)",
          orig2 is not None and "ZZthirteen" in orig2 and ("[%s]" % r13) in tab_row(s), "original=%s tab row=%r" % (disk(bp(r13)), tab_row(s)[:80]))
    s.end()


# ---- T: the tree and the $ entries ------------------------------------------------------------------------------------------------------------------------------------
def section_tree():
    say("\n--- T: the tree does not list $acc, $hold, $map, $release -----------------------------------------------------------------------")
    s = admin("T1", "IDE")
    left = [l[:28].rstrip() for l in s.lines()[3:39]]
    shown = [l for l in left if l.strip()]
    s.show("the tree (left 28 columns)", rows=range(2, 40))
    dollars = [l for l in shown if "$" in l]
    R.row("T1 control: the tree is drawn and lists files (at least 3 rows of the left pane are not empty)", s.in_ide() and len(shown) >= 3, "rows=%d first=%r" % (len(shown), shown[:4]))
    R.row("T1 the tree lists no entry that starts with a dollar sign ($acc, $hold, $map, $release are SD's own, not files of records)", not dollars, "dollar rows=%r" % dollars[:6])
    s.end()


def main():
    try:
        setup_all()
        section_loop()
        section_bare()
        section_new()
        section_abandon()
        section_gate()
        section_edge()
        section_saveas()
        section_keys()
        section_oldkeys()
        section_tree()
        section_trigger()
        section_hangup()
        section_home()
    finally:
        sh.teardown()
    sys.exit(R.finish())


if __name__ == "__main__":
    main()
