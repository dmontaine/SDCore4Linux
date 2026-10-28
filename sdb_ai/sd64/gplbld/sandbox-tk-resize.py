#!/usr/bin/env python3
#
# sandbox-tk-resize.py - the toolkit pages, home and the editors across a RESIZE of the window (S.88, Phase 0: rows R1-R5, F1, P2 of
# ~/Documents/Audits/TUI/Opus_TUI_Plan.txt, section 4), driven on a PSEUDO-TERMINAL.  No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-tk-resize.py <dir> [--build] [--strict]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 no row
# failed, 1 a row failed, 2 it could not run.  The result counter is tuirows.py: a failing row whose phase has not landed is PENDING; --strict counts every row at face value,
# which is how the red run on the unmodified tree is made.
#
# START-HISTORY:
# 28 Oct 26 dm  New (S.88, Phase 0), from the probes rt1/resize.py and rt1/ailine.py of the evaluation (Opus_TUI_Evidence/runtime.json R1-R13).
# END-HISTORY
#
# THE INSTRUMENT (plan 7.4).  The emulator keeps the cells it had before a resize, so a row never reads them.  Every resize is judged on the BYTES THE PROGRAM WROTE
# AFTER IT: a FRESH emulator of the new size is fed only those bytes (Win.fresh), and the foot of the screen, the width of the border and the lock message are read from
# that.  Keys are judged on what they change (reverse-video rows, bytes written) and a record on the DISK (CT through a pipe session).  Every session prints its argv, TERM,
# window size and the keys it is sent.  Every group opens with a CONTROL that passes on today's tree and proves the page was reached (a footer at 140 by 43, keys that move
# the selection, a menu that opens, an undo that works before any resize); when the control fails the rows that depend on it fail as NULL CASE and carry no phase.
#
#   R1   a page follows a window that GROWS (140x43 -> 180x55): footer on rows 53-55, border 180 wide [tool.files, tool.config, tool.query phase 3; home already does]
#   R2   a page started at 180x55 and shrunk to 150x45 keeps working and follows the shrink, and 120x43 locks with the message naming 140 by 43 (R3 of the register)
#   R3   a 41-row window (140x41) locks every page (the cursor lock is keyed to the status line, which still fits)
#   R4   a resize while a menu (home F10) or a tk_confirm box (tool.files C) is open is delivered after it closes (R2 of the register)
#   R5   home's AI line keeps its text and its focus across a resize (R4 of the register)
#   R6   the IDE: Ctrl-Z after a resize undoes typing made before it (I7); the disk is the evidence
#   R7   below the minimum (120x36) the IDE, SED and CED lock with a message like the pages (R5 of the register)
#   R8   tool.files with the N dialog open: a resize keeps the dialog and its typed name (a control: passes today)
import importlib.util
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ptydrive import PtySession  # noqa: E402
from termscreen import Screen  # noqa: E402
from tuirows import Rows  # noqa: E402

TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


al = _load("sandbox_ailine_for_tkresize", "sandbox-ai-line.py")      # the AI line's own setup (a fake provider, the real helper); its `sh` is sandbox-home.py
sh = al.sh
R = Rows("tk-resize")

E = "\x1b"
DOWN, ESC, F10, F2, CTRL_Q, CTRL_Z = E + "OB", E, E + "[21~", E + "OQ", "\x11", "\x1a"
CTRL_S = "\x13"                      # the IDE's only save key since S.88 Phase 4 (F2 was its extra save key; the owner's D28)
BOX = SYS = UA = None
TEXT = "show me the files"
PAGES = (("files", "tool.files", 3), ("config", "tool.config", 3), ("query", "tool.query", 3), ("home", "home", None))
LOCK = re.compile(r"140 by 4[23]")


def say(s=""):
    print(s, flush=True)


def bail(msg):
    say("sandbox-tk-resize: CANNOT RUN - " + msg)
    sys.exit(2)


# ------------------------------------------------------------------------------------------------------------------------ a session on a pty
class Win:
    def __init__(self, label, s, cols, rows):
        self.label, self.s, self.cols, self.rows = label, s, cols, rows

    def pump(self, secs):
        """a deadline loop: _pump returns at the FIRST byte, so a wait of N seconds is made here"""
        end = time.time() + secs
        while time.time() < end and not self.s.exited:
            self.s._pump(min(0.2, max(0.01, end - time.time())))
        self.s.settle(0.4)

    def send(self, data, idle=0.6):
        say("   [%s] keys %r" % (self.label, data))
        self.s.type(data, idle=idle)

    def mark(self):
        return len(self.s.raw)

    def resize(self, cols, rows, secs=1.5):
        """the window is resized (TIOCSWINSZ and SIGWINCH); returns the offset of the bytes the program writes in answer"""
        off = self.mark()
        say("   [%s] resize pty %dx%d -> %dx%d (wait %.1f s)" % (self.label, self.cols, self.rows, cols, rows, secs))
        self.s.resize(cols, rows, idle=0.05)
        self.cols, self.rows = cols, rows
        self.pump(secs)
        return off

    def post(self, off):
        return self.s.raw[off:].decode("latin-1")

    def fresh(self, off):
        """a FRESH emulator of the current size fed only the bytes written since `off`: what the program drew for this size"""
        f = Screen(self.cols, self.rows)
        f.feed(self.post(off))
        return f

    def lines(self):
        return [l.rstrip() for l in self.s.screen.lines()]

    def text(self):
        return "\n".join(self.lines())

    def end(self):
        if not self.s.exited:
            self.s.type(CTRL_Q, idle=0.8)
        self.s.finish(limit=2.0)
        say("   [%s] finished: exited=%s killed=%s" % (self.label, self.s.exited, getattr(self.s, "killed", False)))


def launch(label, cmd, cols=140, rows=43, account=None):
    """The sandbox user's own session (the sandbox's SDSYS: cwd user_accounts, no -a, not SDTEST_ADMIN) or an ordinary fixture account's; TERM xterm; the command typed."""
    env = dict(os.environ, SD_CONFIG=os.path.join(BOX, "sd.conf"), TERM="xterm", LC_ALL="C", LANG="C")
    for k in ("SSH_CONNECTION", "SSH_TTY", "SDTEST_ADMIN", "LINES", "COLUMNS"):
        env.pop(k, None)
    if not account:
        env["SDTEST_ADMIN"] = "1"                          # the administrator's session (sandbox-home.H(admin=True)): the sandbox user is not registered as SDSYS once the fixtures exist
    argv = [os.path.join(SYS, "bin", "sd")] + (["-a" + account] if account else [])
    cwd = os.path.join(UA, account) if account else SYS
    say("== %s: argv=%r cwd=%s TERM=xterm LC_ALL=C SD_CONFIG=%s SDBOX_KEYSET=%s pty=%dx%d command=%r" % (label, argv, cwd, env["SD_CONFIG"], env.get("SDBOX_KEYSET"), cols, rows, cmd))
    w = Win(label, PtySession(argv, cwd, env, cols, rows), cols, rows)
    w.s.settle(1.0)
    w.send("TERM xterm\r", 0.4)
    w.send("TERM %d,%d\r" % (cols, rows), 0.4)
    w.send(cmd + "\r", 1.5)
    w.pump(2.5)
    return w


def sess(*cmds):
    """a plain PIPE session of the administrator (sandbox-home.adm) for setting up and reading back from the disk (no pages)"""
    return "\n".join(sh.adm(*cmds))


# ------------------------------------------------------------------------------------------------------------------------ what a screen shows
def rev_rows(scr):
    return [(r, scr.reverse(r)[:50]) for r in range(scr.rows) if scr.reverse(r)]


def foot(lines, cols, rows):
    """The foot of a toolkit page or home: the status line '[Pane] ...' on row rows-2 (1-based), the border on rows-1, the function keys on the last row."""
    L = [l.rstrip() for l in lines] + [""] * rows
    st, bd, ky = L[rows - 3], L[rows - 2], L[rows - 1]
    bd_w = len(bd) if bd and not re.search(r"[A-Za-z0-9]", bd) else 0
    d = dict(st_ok=st.startswith("["), key_ok="^Q" in ky, bd_w=bd_w, st=st[:34], bd="%d wide" % len(bd), ky=ky[:34])
    d["ok"] = d["st_ok"] and d["key_ok"] and bd_w > 0
    return d


def where(lines):
    """the 1-based rows that hold a '[' status line and the '^Q' key row, for the detail of a failing row"""
    st = [i + 1 for i, l in enumerate(lines) if l.startswith("[")]
    ky = [i + 1 for i, l in enumerate(lines) if "^Q" in l]
    return "status-like rows %r, ^Q rows %r" % (st[-3:], ky[-3:])


def row(rid, name, ok, detail="", phase=None, ctrl=True):
    """One result.  `ctrl` False means the control of the group failed: the instrument did not reach the page, so the row cannot be believed either way (NULL CASE)."""
    if not ctrl:
        R.row("%s %s" % (rid, name), False, "NULL CASE: the control of this group failed, the rows below it say nothing. " + detail, phase=None)
        return False
    return R.row("%s %s" % (rid, name), ok, detail, phase=phase)


def moves(w):
    """Down twice: do the reverse-video rows change (the selection or the focus moved)?"""
    before = rev_rows(w.s.screen)
    w.send(DOWN, 0.6)
    w.send(DOWN, 0.6)
    w.pump(0.8)
    after = rev_rows(w.s.screen)
    return before != after, len(after)


def bytes_for_down(w):
    off = w.mark()
    w.send(DOWN, 0.6)
    w.send(DOWN, 0.6)
    w.pump(0.8)
    return len(w.s.raw) - off


# ------------------------------------------------------------------------------------------------------------------------ fixture
def fixture():
    prog = r"""   open 'bp' to f else stop 'no bp'
   s = ''
   for i = 1 to 80
      s<i> = '* line ' : i : ' of the resize probe record ' : str('x', 20)
   next i
   write s on f, 'zzrrec'
   for k = 0 to 2
      write '* undo probe line 1' : @fm : '* undo probe line 2' : @fm : '* undo probe line 3' on f, 'zzru' : k
   next k
   execute 'CREATE.FILE zzrj' capturing j
   execute 'CREATE.FILE zzrf1' capturing j
   open 'zzrj' to o else stop 'no zzrj'
   write '{"title": "resize probe", "count": 3, "items": [1, 2, 3], "nested": {"a": 1, "b": "two"}}' on o, 'j1'
   crt 'FIXTURE DONE'
end
"""
    with open(os.path.join(SYS, "bp", "zzrfx"), "w") as fh:
        fh.write(prog)
    out = sess("BASIC bp zzrfx", "RUN bp zzrfx")
    if "FIXTURE DONE" not in out:
        bail("the fixture was not made:\n" + out[-600:])
    chk = sess('COUNT bp WITH @ID = "zzrrec" OR @ID LIKE "zzru..."', "COUNT zzrj", "COUNT zzrf1", "CT zzrj j1")
    say(chk[-500:])
    if "title" not in chk:
        bail("the fixture record zzrj j1 is not there:\n" + chk[-400:])


# ------------------------------------------------------------------------------------------------------------------------ R1
def sec_grow():
    say("\n--- R1: a page follows a window that grows (140x43 -> 180x55)")
    for key, cmd, ph in PAGES:
        w = launch("R1-" + key, cmd, 140, 43)
        f0 = foot(w.lines(), 140, 43)
        c = R.row("R1c %s at 140x43 the footer is on rows 41-43 (status line, border 140 wide, keys)" % cmd, f0["ok"] and f0["bd_w"] == 140, repr(f0) + " " + where(w.lines()), phase=None)
        mv, nrev = moves(w)
        c2 = R.row("R1c2 %s at 140x43 Down twice changes the reverse-video rows (the keys reach the page)" % cmd, mv, "reverse rows: %d" % nrev, phase=None)
        ctrl = c and c2
        off = w.resize(180, 55, 2.0)
        fr = w.fresh(off)
        f = foot(fr.lines(), 180, 55)
        row("R1a", "%s at 180x55 the program writes the footer on rows 53-55 (status, border, keys)" % cmd, f["ok"], "%r; %s; bytes written: %d" % (f, where([l.rstrip() for l in fr.lines()]), len(w.post(off))), phase=ph, ctrl=ctrl)
        row("R1b", "%s at 180x55 the frame is 180 wide: the border is 180 cells (columns 141-180 used)" % cmd, f["bd_w"] == 180, "border width written: %d" % f["bd_w"], phase=ph, ctrl=ctrl)
        w.end()


# ------------------------------------------------------------------------------------------------------------------------ R2, R3, R7 (pages)
def sec_shrink_start_big():
    say("\n--- R2: a page started at 180x55 and shrunk to 150x45 (above the minimum) keeps working")
    for key, cmd, ph in PAGES:
        w = launch("R2-" + key, cmd, 180, 55)
        drew = "^Q" in w.text()
        c = R.row("R2c %s started at 180x55 it drew its page (a '^Q' key row is on the screen)" % cmd, drew, w.text()[-300:], phase=None)
        f0 = foot(w.lines(), 180, 55)
        R.row("R2c2 %s started at 180x55 it uses the whole window: footer on rows 53-55" % cmd, f0["ok"], "%r; %s" % (f0, where(w.lines())), phase=None) if c else row("R2c2", cmd, False, "", ctrl=False)
        off = w.resize(150, 45, 2.0)
        txt = w.text()
        fr = w.fresh(off)
        f = foot(fr.lines(), 150, 45)
        mv, nrev = moves(w)
        locked = bool(LOCK.search(w.text()))
        row("R2a", "%s shrunk to 150x45 (above 140x43) keeps working: no lock message, and Down moves the selection" % cmd, (not locked) and mv,
            "lock message on screen: %s; Down changed the reverse rows: %s" % (locked, mv), phase=3, ctrl=c)
        row("R2a2", "%s shrunk to 150x45 follows the shrink: the program writes the footer on rows 43-45 with a border 150 wide" % cmd, f["ok"] and f["bd_w"] == 150,
            "%r; bytes written: %d" % (f, len(w.post(off))), phase=3, ctrl=c)
        w.end()


def sec_small():
    say("\n--- R2b, R3 and the pages' half of R7: 120x43 and 140x41 lock a page, 120x36 is the control")
    for key, cmd, ph in PAGES:
        w = launch("R3-" + key, cmd, 140, 43)
        f0 = foot(w.lines(), 140, 43)
        c = R.row("R3c %s at 140x43 the page is up (footer on rows 41-43)" % cmd, f0["ok"], repr(f0), phase=None)
        off = w.resize(120, 43, 2.0)
        t = w.post(off)
        fr = w.fresh(off)
        row("R2b", "%s at 120x43 (too narrow) locks: the program writes a message naming 140 by 43" % cmd, bool(LOCK.search("\n".join(fr.lines()))),
            "what was written: %d bytes; rows: %r" % (len(t), [l.strip()[:60] for l in fr.lines() if l.strip()][:3]), phase=3, ctrl=c)
        off = w.resize(140, 43, 2.5)
        back = foot(w.fresh(off).lines(), 140, 43)
        c2 = R.row("R3c2 %s back at 140x43 the page is drawn again (the control for the next row: a lock is left by a bigger window)" % cmd, back["ok"] or foot(w.lines(), 140, 43)["ok"],
                   repr(back), phase=None)
        off = w.resize(140, 41, 2.0)
        fr = w.fresh(off)
        row("R3", "%s at 140x41 (41 rows) locks: the program writes a message naming 140 by 43" % cmd, bool(LOCK.search("\n".join(fr.lines()))),
            "what was written: %d bytes; rows: %r" % (len(w.post(off)), [l.strip()[:60] for l in fr.lines() if l.strip()][:3]), phase=3, ctrl=c and c2)
        off = w.resize(140, 43, 2.5)
        off = w.resize(120, 36, 2.0)
        fr = w.fresh(off)
        msg = bool(LOCK.search("\n".join(fr.lines())))
        nb = bytes_for_down(w)
        row("R7p", "%s at 120x36 locks with a message naming 140 by 43 and takes no key (Down writes %d bytes)" % (cmd, nb), msg and nb <= 16, "message: %s; bytes after Down: %d" % (msg, nb),
            phase=None, ctrl=c and c2)
        w.end()


# ------------------------------------------------------------------------------------------------------------------------ R4
def sec_dialog_open():
    say("\n--- R4: a resize while a menu or a confirm box is open is delivered after it closes")
    w = launch("R4-home", "home", 140, 43)
    f0 = foot(w.lines(), 140, 43)
    c = R.row("R4c home at 140x43 is up (footer on rows 41-43)", f0["ok"], repr(f0), phase=None)
    before = w.lines()
    w.send(F10, 1.0)
    opened = any(("Sign out" in l and "^Q" in l) for l in w.lines()[1:9])
    c2 = R.row("R4c2 F10 opens the File menu (an entry 'Sign out  ^Q' appears in the rows under the menu bar)", opened, "\n".join(l for l in w.lines()[:9] if l.strip()), phase=None)
    off = w.resize(180, 55, 1.5)
    w.send(ESC, 1.0)
    w.pump(2.5)
    fr = w.fresh(off)
    f = foot(fr.lines(), 180, 55)
    closed = not any(("Sign out" in l and "^Q" in l) for l in w.lines()[1:9])
    R.row("R4c3 home: the menu is closed by Esc after the resize", closed, "\n".join(l for l in w.lines()[:9] if l.strip()), phase=None) if (c and c2) else None
    row("R4a", "home: resized to 180x55 while the F10 menu was open, after Esc the program writes the footer on rows 53-55 (the border on the new last-but-two row)", f["ok"],
        "%r; %s; bytes since the resize: %d" % (f, where([l.rstrip() for l in fr.lines()]), len(w.post(off))), phase=3, ctrl=c and c2)
    w.end()

    w = launch("R4-files", "tool.files", 140, 43)
    f0 = foot(w.lines(), 140, 43)
    c = R.row("R4c4 tool.files at 140x43 is up (footer on rows 41-43)", f0["ok"], repr(f0), phase=None)
    w.send("/", 0.8)
    w.send("zzrf1\r", 1.0)
    pre_box = "Removes every record" in w.text()
    w.send("c", 1.2)
    box = "Removes every record of zzrf1" in w.text() and "Cancel" in w.text()
    c2 = R.row("R4c5 tool.files: the filter finds zzrf1 and C opens the confirm box (the text 'Removes every record of zzrf1' and a Cancel button; none before the key)", box and not pre_box,
               "box before the key: %s\n%s" % (pre_box, "\n".join(l for l in w.lines()[15:30] if l.strip())), phase=None)
    off = w.resize(180, 55, 1.5)
    w.send(ESC, 1.0)
    w.pump(2.5)
    fr = w.fresh(off)
    f = foot(fr.lines(), 180, 55)
    gone = "Removes every record" not in w.text()
    R.row("R4c6 tool.files: Esc closes the box (Cancel is the default; nothing is run)", gone, w.text()[-300:], phase=None) if (c and c2) else None
    row("R4b", "tool.files: resized to 180x55 while the confirm box was open, after Esc the program writes the footer on rows 53-55", f["ok"],
        "%r; %s; bytes since the resize: %d" % (f, where([l.rstrip() for l in fr.lines()]), len(w.post(off))), phase=3, ctrl=c and c2)
    w.end()


# ------------------------------------------------------------------------------------------------------------------------ R8
def sec_new_file_dialog():
    say("\n--- R8: the N dialog of tool.files across a resize (a control: passes today)")
    w = launch("R8-files", "tool.files", 140, 43)
    c = R.row("R8c tool.files at 140x43 is up (footer on rows 41-43)", foot(w.lines(), 140, 43)["ok"], where(w.lines()), phase=None)
    w.resize(180, 55, 1.5)
    w.send("n", 1.2)
    w.send("zzrsz", 0.8)
    pre = "Name of the new file" in w.text() and "zzrsz" in w.text()
    c2 = R.row("R8c2 N opens 'Name of the new file' and the typed name zzrsz is in its field", pre, w.text()[-400:], phase=None)
    off = w.resize(140, 43, 2.0)
    fr = w.fresh(off)
    ft = "\n".join(fr.lines())
    row("R8a", "a resize (180x55 -> 140x43) with the dialog open: the program redraws the dialog and the typed name zzrsz", "Name of the new file" in ft and "zzrsz" in ft,
        "dialog in the written bytes: %s, name: %s" % ("Name of the new file" in ft, "zzrsz" in ft), phase=None, ctrl=c and c2)
    w.send("q", 0.8)
    row("R8b", "...and typing goes on in the same field: q makes zzrszq", "zzrszq" in w.text(), [l.strip()[:80] for l in w.lines() if "zzrsz" in l][:3], phase=None, ctrl=c and c2)
    for _ in range(3):
        w.send(ESC, 1.0)
    gone = [p for p in (os.path.join(UA, "zzrsz"), os.path.join(UA, "zzrszq"), os.path.join(SYS, "zzrsz"), os.path.join(SYS, "zzrszq")) if os.path.exists(p)]
    row("R8d", "...Esc three times leaves the dialog and nothing was made on the disk (no zzrsz or zzrszq)", not gone and "Name of the new file" not in w.text(), repr(gone), phase=None, ctrl=c and c2)
    w.end()


# ------------------------------------------------------------------------------------------------------------------------ R5
def sec_ai_line():
    say("\n--- R5: home's AI line keeps its text and its focus across a resize")
    rn = al.STATE.get("runner")
    say("   the AI helper's runner before the section: %s" % ("not started" if rn is None else ("exited %r" % rn.poll() if rn.poll() is not None else "running")))
    al.configure()                                   # as sandbox-ai-line.py's L1 does just before its first AI row: provider, model, key, then a fresh runner
    al.start_runner()
    h = al.home(admin=False)
    w = Win("R5-ai", h.s, 140, 43)
    say("   home started for %s: pty 140x43, TERM=xterm, LC_ALL=C (sandbox-home.H); home drawn: %s" % (al.ACCT, h.home()))
    c = R.row("R5c the ordinary home screen is up and row 40 holds the AI line (AI> ...)", h.home() and "AI>" in h.line(39), repr(h.line(39)[:90]), phase=None)
    h.key("btab", idle=0.8)
    h.typed(TEXT, idle=0.8)
    c2 = R.row("R5c2 Back-tab focuses the line and the request is typed there (not sent): row 40 reads 'AI> %s'" % TEXT, "AI>" in h.line(39) and TEXT in h.line(39), repr(h.line(39)[:90]), phase=None)
    off = w.resize(180, 55, 2.0)
    fr = w.fresh(off)
    ai_row = fr.lines()[51].rstrip() if len(fr.lines()) > 51 else ""
    screen_row = w.lines()[51] if len(w.lines()) > 51 else ""
    row("R5a", "after 140x43 -> 180x55 the program writes the AI row (row 52) WITH the typed text", TEXT in ai_row and "AI>" in ai_row, "written: %r ; on the screen: %r" % (ai_row[:90], screen_row[:90]),
        phase=3, ctrl=c and c2)
    h.typed("X", idle=0.8)
    sr = w.lines()[51] if len(w.lines()) > 51 else ""
    row("R5b", "...and the focus is still on the line: X typed next is appended to the text", (TEXT + "X") in sr, "row 52 after X: %r" % sr[:90], phase=3, ctrl=c and c2)
    reqs = al.requests()
    R.row("R5c3 nothing was sent: the fake provider's request log is empty", len(reqs) == 0, "%d request(s)" % len(reqs), phase=None)
    h.key("esc", idle=0.8)
    w.end()


# ------------------------------------------------------------------------------------------------------------------------ R6, R7 editors
def disk_first_line(rid):
    out = sess("CT bp " + rid)
    return out


def sec_ide_undo():
    say("\n--- R6: the IDE, Ctrl-Z after a resize")
    # U0: the control without a resize
    w = launch("R6-ide0", "IDE bp zzru0", 140, 43)
    up = "undo probe line 1" in w.text() and "Line 1, column 1" in w.text()
    w.send("QQQ", 0.6)
    w.pump(1.5)
    typed = "QQQ" in w.text()
    w.send(CTRL_Z, 0.8)
    w.pump(1.0)
    undone = "QQQ" not in w.text()
    w.send(CTRL_S, 1.0)
    w.pump(1.0)
    disk0 = disk_first_line("zzru0")
    c = R.row("R6c IDE (no resize): the record opens, QQQ typed shows on the screen, Ctrl-Z takes it away, the disk never held it",
              up and typed and undone and "QQQ" not in disk0 and "undo probe line 1" in disk0, "opened %s typed %s undone %s; disk: %r" % (up, typed, undone, disk0[-120:]), phase=None)
    w.end()
    # U2: F2 after a resize writes the typed text: the save path works and the text survives the resize (control)
    w = launch("R6-ide2", "IDE bp zzru2", 140, 43)
    w.send("QQQ", 0.6)
    w.pump(1.5)
    w.resize(180, 55, 2.0)
    kept = "QQQ" in w.text()
    w.send(CTRL_S, 1.0)
    w.pump(1.0)
    disk2 = disk_first_line("zzru2")
    c2 = R.row("R6c2 IDE: typed QQQ, resize 180x55, F2 (no undo): the text is still in the editor and the disk holds QQQ (the save path works after a resize)", kept and "QQQ" in disk2,
               "kept on screen %s; disk: %r" % (kept, disk2[-120:]), phase=None)
    w.end()
    # U1: the row
    w = launch("R6-ide1", "IDE bp zzru1", 140, 43)
    w.send("QQQ", 0.6)
    w.pump(1.5)
    w.resize(180, 55, 2.0)
    kept = "QQQ" in w.text()
    w.send(CTRL_Z, 0.8)
    w.pump(1.0)
    gone = "QQQ" not in w.text()
    w.send(CTRL_S, 1.0)
    w.pump(1.0)
    disk1 = disk_first_line("zzru1")
    row("R6", "IDE: typed QQQ, resize 180x55, Ctrl-Z restores the text from before the typing (undo kept): QQQ is gone from the screen and from the saved record",
        gone and "QQQ" not in disk1, "QQQ on the screen before Ctrl-Z: %s; gone after: %s; disk: %r" % (kept, gone, disk1[-120:]), phase=3, ctrl=c and c2 and kept)
    w.end()


def sec_editors_small():
    say("\n--- R7: below the minimum (120x36) the editors lock with a message like the pages")
    for key, cmd, mark in (("ide", "IDE bp zzrrec", "File  Go  Search"), ("sed", "SED bp zzrrec", "File  Edit  Search"), ("ced", "CED zzrj j1", "Collection editor")):
        w = launch("R7-" + key, cmd, 140, 43)
        c = R.row("R7c %s at 140x43 is up (%r on the screen)" % (cmd.split()[0], mark), mark in w.text(), w.text()[:200], phase=None)
        off = w.resize(120, 36, 2.0)
        fr = w.fresh(off)
        msg = bool(LOCK.search("\n".join(fr.lines())))
        nb = bytes_for_down(w)
        row("R7", "%s at 120x36 locks: the program writes a message naming 140 by 43 and takes no key (Down writes %d bytes)" % (cmd.split()[0], nb), msg and nb <= 16,
            "message: %s; bytes written by Down: %d; written rows: %r" % (msg, nb, [l.strip()[:50] for l in fr.lines() if l.strip()][:3]), phase=6, ctrl=c)
        w.end()


# ------------------------------------------------------------------------------------------------------------------------ main
def main():
    global BOX, SYS, UA
    try:
        sh.setup("sandbox-tk-resize.py")
        BOX, SYS = sh.BOX, sh.SYS
        UA = os.path.join(BOX, "user_accounts")
        say("sandbox-tk-resize: sandbox %s, keyset %s, strict %s" % (BOX, os.environ.get("SDBOX_KEYSET"), "--strict" in sys.argv))
        fixture()
        al.setup_ai(None)
        al.configure()
        sh.set_default("terminal")
        sec_grow()
        sec_shrink_start_big()
        sec_small()
        sec_dialog_open()
        sec_new_file_dialog()
        sec_ide_undo()
        sec_editors_small()
        # R5 (home's AI line keeps its draft across a resize) is NOT HELD: on 28 Oct 26 its CONTROL never reached the AI line (the ordinary home screen showed
        # the old hint on row 40, not 'AI>'), so the rows could prove nothing, and a test that proves nothing must not pass.  The fault is measured by hand (the
        # evaluation's probe rt1/ailine.py: the text and the focus are lost) and is plan R4; the section is kept in this file for the phase-3 sitting that makes its
        # setup reach the line (compare with sandbox-ai-line.py's setup).  Run it with --ai to see it.
        if "--ai" in sys.argv:
            sec_ai_line()
        else:
            say("\n--- R5: NOT HELD (its control could not reach the AI line; see the comment above) - run with --ai")
    finally:
        al.stop_runner()
        if "fm" in al.STATE:
            al.STATE["fm"].stop()
        sh.teardown()
    sys.exit(R.finish())


if __name__ == "__main__":
    main()
