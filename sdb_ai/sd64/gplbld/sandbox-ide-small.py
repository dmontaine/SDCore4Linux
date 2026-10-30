#!/usr/bin/env python3
#
# sandbox-ide-small.py - the IDE, CED and the debugger at 140 by 42: refused (the debugger: line mode) below it, survived when the
# window shrinks, and the cursor lock.  No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-ide-small.py <dir> [--build]
#                                                       [--only=a,b,c,d,e,f] [--mutant=NAME] [--keep]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or absent);
# without it <dir> must already be built, which is how the same script is run against an OLD tree to prove it can fail.  Exit 0
# every row passed, 1 a row failed, 2 it could not run.  The sandbox is stopped when the suite ends; remove its directory
# afterwards (each run leaves ~14,000 files).
#
# START-HISTORY:
# 18 Oct 26 dm  New (plan-terminal-140x42.md phase 3 and 6, the second half of what sandbox-sed-small.py is for SED): the IDE and
#               CED are laid out for 140 by 42 and refuse a smaller window with the library's one message ($sl_need); the debugger
#               prints a message and uses line mode; a window made smaller after the start shows the upper left corner of the layout
#               and nothing past the edge; and while the cursor is off the screen the keys are ignored behind a warning until the
#               window is made bigger or the user leaves with Ctrl-Q, y ($sl_guardmode, $sl_key, $sl_guard).
# 18 Oct 26 dm  Phase 3 checked: the message box puts the cursor on its button while a guarded program has it up (a box below the rows
#               the window shows is locked, not typed into blind), the menu and the box close on the lock's way out, and the mutant
#               "nomap" was aimed at a program the IDE's question does not use (it survived); it is $screen_ask now.
# 28 Oct 26 dm  S.88 handoff step 1 (WRITTEN, NOT RUN): the IDE is laid out for 140 by 43 and its lock is the WINDOW's (the layout mode of $sl_guardmode): the foot is the status
#               line (row 40), a border and the function-key row; below 140 by 43 the keyboard is held behind a warning that names both sizes and says unsaved text is lost
#               unless a recovery copy is on, in the longest of three wordings that fits the window's rows; part C's IDE rows and part D are rewritten for that (the old
#               cursor-lock rows - 45 Downs leaving the screen, a window of 24 lines being fine - are gone); CED and the debugger keep 140 by 42 and the cursor lock.
# 28 Oct 26 dm  S.88 Phase 4: the File menu has seven entries (New, Open, Save, Save as, Write a copy, Close, Quit), so Close record is five Downs
#               from New record and Quit six; no other key of these rows changed meaning (Ctrl-S, Ctrl-Q, Ctrl-L, F10 and the Downs are as before).
# END-HISTORY
#
# HOW IT DRIVES THEM.  On a PSEUDO-TERMINAL (ptydrive.py), the window size set BEFORE SD starts (it asks the tty when it starts) and
# changed afterwards with TIOCSWINSZ, which is what dragging the corner of a terminal does (SIGWINCH).  The screen is read from the
# emulator in termscreen.py.
#
# THE INSTRUMENT, AND WHAT IT REFUSES.  As in sandbox-sed-small.py: the emulator KEEPS what it shows when the window is resized, so a
# program that never drew again after a shrink would still LOOK right.  Every row that compares a screen after a resize therefore
# compares a REPLAY: a blank emulator of the new size fed only the bytes the program wrote after the resize.  A row that finds nothing
# to compare fails, a replay of no bytes fails.  Every shrink has a control: the same keys at the full size.  What a program did to
# its data is read from the data afterwards (a probe program in a pipe session), never from what it said.
#
# MUTANTS.  --mutant=NAME edits the SANDBOX's copy of a program (never the tree), compiles it and runs the parts that matter for it;
# the rows it should break are listed with it below (MUTANTS).  Nothing is run from the tree.

import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ptydrive import PtySession  # noqa: E402
from termscreen import Screen  # noqa: E402
import cedverb  # noqa: E402  (29 Oct 26, S.88 g-P1: the `ced` verb is no longer shipped; the run writes the VOC record itself)

TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
RUN = "%05d" % (os.getpid() % 100000)
F = os.environ.get("ISFILE") or "zzis" + RUN         # the fixture file (ISFILE names it by hand, with --keep, for a debugging session)
DBG = "zzisdbg" + RUN                                # the program the debugger is run on
SCR = "zzisscr" + RUN                                # a user's SCREEN OPEN program
passed = failed = 0
BOX = SYS = None

LAY_W, LAY_H = 140, 42                              # what CED and the debugger are laid out for
IDE_H = 43                                          # what the IDE is laid out for since the window lock (28 Oct 26): 140 by 43, its foot is the status line (row 40), a border and the key row
UP, DOWN, LEFT, RIGHT = "\x1bOA", "\x1bOB", "\x1bOD", "\x1bOC"
F10 = "\x1b[21~"
ESC, RET, BS = "\x1b", "\r", "\x7f"
CTRL = lambda ch: chr(ord(ch.upper()) - 64)         # noqa: E731


def mkline(i):
    if i == 2:
        return ("L02 " + "0123456789" * 20)[:146] + ">>END2"
    return "L%02d the quick brown fox jumps over the lazy dog" % i


RECORD = [mkline(i) for i in range(1, 61)]
JSONREC = json.dumps({"k%02d" % i: "value %02d" % i for i in range(1, 61)}, separators=(",", ":"))


def say(s=""):
    print(s)
    sys.stdout.flush()


def row(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        say("  [PASS] " + name)
    else:
        failed += 1
        say("  [FAIL] " + name + ("   <- " + detail if detail else ""))


def bail(msg):
    say("sandbox-ide-small: CANNOT RUN - " + msg)
    sys.exit(2)


def sess(*cmds):
    """A plain scripted session through a pipe, for setting up and reading back (no keys)."""
    say("    > " + " | ".join(cmds))
    p = subprocess.run([sys.executable, TOOL, BOX, "sess", os.path.join(BOX, "user_accounts")] + list(cmds),
                       capture_output=True, text=True, errors="replace", timeout=600)
    out = ANSI.sub("", p.stdout + p.stderr)
    return out.split(":TERM 200,9999", 1)[-1]


def internal(*cmds):
    """sd -internal in the sandbox's sys directory (the sandbox user is its administrator): for compiling the mutants."""
    env = dict(os.environ, SD_CONFIG=os.path.join(BOX, "sd.conf"))
    say("    > [internal] " + " | ".join(cmds))
    body = "\nTERM 200,9999\n" + "".join(c + "\n" for c in cmds) + "OFF\n"
    p = subprocess.run([os.path.join(SYS, "bin", "sd"), "-internal"], input=body, cwd=SYS, env=env, capture_output=True,
                       text=True, errors="replace", timeout=600)
    return ANSI.sub("", p.stdout + p.stderr)


class Term:
    """One run of a command on a pseudo-terminal: type to it, read its screen.  The window is the tty's, set before SD starts."""

    def __init__(self, box, cmd, cols=LAY_W, rows=None, pre=(), idle=1.2):
        """pre: commands typed first (TERM 100,30, AUTOLOGOUT 30 ...).  rows left out: the height the program is laid out for (the IDE's, else CED's and the debugger's)."""
        if rows is None:
            rows = IDE_H if cmd.split()[0].upper() == "IDE" else LAY_H
        self.cols = cols
        self.rows = rows
        env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"), TERM="xterm", LC_ALL="C", LANG="C")
        self.s = PtySession([os.path.join(box, "sys", "bin", "sd")], os.path.join(box, "user_accounts"), env, cols, rows)
        self.s.settle(1.0)
        self.s.type("TERM xterm\r")
        for p in pre:
            self.s.type(p + "\r", idle=0.6)
        self.s.type(cmd + "\r", idle=idle)

    def keys(self, *chunks, idle=0.5):
        for chunk in chunks:
            self.s.type(chunk, idle=idle)
        return self.lines()

    def lines(self):
        return self.s.screen.lines()

    def mark(self):
        """Where the bytes written from now on begin."""
        return len(self.s.raw)

    def resize(self, cols, rows, wait=1.8):
        """Make the window cols by rows (SIGWINCH) and give the program time to notice: they look about once a second.  Returns
        the mark taken just BEFORE, for replay()."""
        m = self.mark()
        self.s.resize(cols, rows, idle=0.8)
        time.sleep(wait)
        self.s.settle(0.8)
        self.cols, self.rows = cols, rows
        return m

    def replay(self, mark, cols=None, rows=None):
        """What a blank terminal of the current size shows when given only the bytes written since mark."""
        scr = Screen(cols or self.cols, rows or self.rows)
        data = self.s.raw[mark:].decode("latin-1")
        scr.feed(data)
        return scr.lines(), len(data)

    def end(self):
        self.s.type("\rOFF\r", idle=0.5)
        self.s.finish()


def text(L, n=8):
    return "\n".join(l[:100] for l in L[:n])


def warn_shown(L, w, h, name):
    """The cursor lock's warning is in the first rows, for a window w by h and the program called name."""
    t = " ".join(l.strip() for l in L[:6])
    return ("The window is %d by %d and %s is laid out for 140 by 42" % (w, h, name)) in t and "Ctrl-Q" in t


def ide_warn(L, w, h):
    """The IDE's window lock (layout mode) is up for a window w by h, in whichever of the three wordings fits: the window's size and the floor's are both in the first rows,
    and Ctrl-Q is named (the shortest wording has it as '^Q'-less 'Ctrl-Q leaves')."""
    t = " ".join(l.strip() for l in L[:6])
    return re.search(r"\b%d by %d(?!\d)" % (w, h), t) is not None and "140 by 43" in t and "Ctrl-Q" in t


def ide_at(e):
    """(line, column) from the IDE's status line (three rows above the last of a window at the full size: the status line, the border, the key row)."""
    t = "\n".join(e.lines()[IDE_H - 4:IDE_H - 2])
    m = re.search(r"Line (\d+), column (\d+)", t)
    return (int(m.group(1)), int(m.group(2))) if m else None


def corner_diff(got, base, w, h):
    """None if the w by h upper left corner of base (the screen at the full size) is what got shows, else the first difference."""
    if not any(l.strip() for l in got):
        return "nothing is on the screen"
    for r in range(h):
        want = (base[r] if r < len(base) else "")[:w].rstrip()
        have = (got[r] if r < len(got) else "").rstrip()
        if have != want:
            return "row %d: got %r want %r" % (r, have[:90], want[:90])
    return None


def rec(name="r1"):
    out = sess("RUN bp zzisprobe")
    m = re.search(r"(?m)^REC %s (.*)$" % re.escape(name), out)
    return m.group(1).split("|") if m else ["<absent>"]


def locked(name):
    """True if another session finds the record locked."""
    out = sess("RUN bp zzislock")
    m = re.search(r"(?m)^ISLOCK %s (HELD|FREE|ABSENT)$" % re.escape(name), out)
    return None if not m else m.group(1) == "HELD"


def prompt_shown(e):
    return any(l.startswith(":") for l in e.lines())


def leave(e):
    """Leave whatever is running (Ctrl-Q, then n/y to a question if one comes) and the session."""
    e.keys(CTRL("q"))
    e.keys("n")
    e.s.type("\r", idle=0.5)
    e.end()


# ------------------------------------------------------------------------------------------------------------------------------
def part_a():
    say("\n--- A: the IDE is laid out for 140 by 43, CED for 140 by 42, and both use a bigger window whole -----------------------------")
    e = Term(BOX, "IDE %s r1" % F)
    base = list(e.lines())
    row("control: the IDE is up at 140 by 43 with the record in the editor (status line on row 40, then the border, then the key row)",
        base[40].startswith("[Editor]  " + F + " r1") and "L01 the quick" in base[3] and ide_at(e) == (1, 1), repr(base[40][:50]) + repr(base[3][:50]))
    row("the menu bar is row 0 and the frame starts on row 1", " File" in base[0] and base[1].startswith("+- IDE"), repr(base[0][:40]) + repr(base[1][:20]))
    row("the form's bottom edge is row 39, the row above the status line (the form is 39 rows: 1 to 39)", base[39].startswith("+-") and base[39].rstrip().endswith("+"), repr(base[39][:20]))
    row("the border is row 41 and the function-key row is row 42: Esc menu, F1 help, ^S save and ^Q quit are on it (the toolkit's frame, plan 5.1)",
        base[41].strip() != "" and set(base[41].strip()) <= set("-") | {"─"} and all(w in base[42] for w in ("Esc menu", "F1 help", "^S save", "^Q quit")),
        repr(base[41][:30]) + repr(base[42][:80]))
    row("...the key row is within the layout (no more than 140 columns) and names no key the IDE does not act on (F2 is not on it: Ctrl-S is the one save key)",
        len(base[42].rstrip()) <= LAY_W and "F2" not in base[42], repr(base[42][-40:]))
    row("the frame's right edge is column 139 (the layout is 140 wide)", len(base[1].rstrip()) == 140 and base[1].rstrip().endswith("+"), repr(base[1][-8:]))
    row("a row never reaches past column 140", max(len(l) for l in base) <= LAY_W, str(max(len(l) for l in base)))
    e.end()
    e = Term(BOX, "IDE %s r1" % F, 200, 60)
    L = e.lines()
    row("200 by 60: the IDE uses the whole window: the status line is row 57, the border row 58, the key row row 59, and the frame is 200 wide",
        L[57].startswith("[Editor]  " + F + " r1") and len(L[1].rstrip()) == 200 and "Esc menu" in L[59] and L[58].strip() != "", repr(L[57][:40]) + str(len(L[1].rstrip())) + repr(L[59][:30]))
    leave(e)

    e = Term(BOX, "CED %s j1" % F)
    base = list(e.lines())
    row("control: CED is up at 140 by 42 with the record's members in the table (the first at row 2)",
        "k01" in base[2] and "value 01" in base[2], text(base, 4))
    row("...the path is on row 40 and the message line on row 41", base[40].strip() != "" and base[41].strip() != "",
        repr(base[40][:40]) + repr(base[41][:40]))
    e.end()
    e = Term(BOX, "CED %s j1" % F, 200, 60)
    L = e.lines()
    row("200 by 60: CED uses the whole window: the path is on row 58 and the message line on row 59", L[59].strip() != "" and L[58].strip() != "",
        repr(L[58][:40]) + repr(L[59][:40]))
    leave(e)


def part_b():
    say("\n--- B: a window under the floor at the start (the IDE 140 by 43, CED and the debugger 140 by 42): refused, the debugger uses line mode ---")
    for (cmd, name, fh, sizes) in (("IDE", "IDE", IDE_H, ((80, 24), (100, 30), (120, 36), (139, 43), (140, 42))),
                                   ("CED %s j1" % F, "CED", LAY_H, ((80, 24), (100, 30), (120, 36), (139, 42), (140, 41)))):
        for (c, r) in sizes:
            e = Term(BOX, cmd, c, r)
            L = e.lines()
            want = "%s needs a window of at least 140 columns by %d lines; this one is %d by %d" % (name, fh, c, r)
            row("%s at %dx%d: refused with the message, which names the floor and the size the window is" % (name, c, r), any(want in l for l in L), text(L, 12))
            row("%s at %dx%d: nothing is drawn (no menu bar, no frame) and SD is at its prompt" % (name, c, r),
                not any(" File  Go" in l or l.startswith("+- IDE") or "k01" in l for l in L) and prompt_shown(e), text(L, 12))
            e.end()
    held = locked("j1")
    row("a refused CED touched nothing: the record is not locked", held is False, repr(held))
    row("a refused IDE and CED changed nothing: the records are as they were", rec("r1") == RECORD and rec("j1") == [JSONREC], repr(rec("j1"))[:60])
    e = Term(BOX, "IDE %s r1" % F, 140, IDE_H, pre=("TERM 100,30",))
    L = e.lines()
    row("a 140 by 43 window whose display was set to 100 by 30 with TERM is refused: the display is what they can draw on",
        any("this one is 100 by 30" in l for l in L) and not any(l.startswith("+- IDE") for l in L), text(L, 12))
    e.end()
    e = Term(BOX, "CED %s j1" % F, 80, 24, pre=("TERM 200,60",))
    L = e.lines()
    row("an 80 by 24 window whose display was set to 200 by 60 is refused too: the window is what there is to draw on",
        any("this one is 80 by 24" in l for l in L), text(L, 12))
    e.end()
    e = Term(BOX, "IDE %s r1" % F, 140, IDE_H)
    row("control: exactly 140 by 43 starts the IDE", e.lines()[1].startswith("+- IDE"), repr(e.lines()[1][:20]))
    e.end()
    e = Term(BOX, "CED %s j1" % F, 140, 42)
    row("control: exactly 140 by 42 starts CED", "k01" in e.lines()[2], repr(e.lines()[2][:40]))
    leave(e)

    say("\n--- B: !CED() from a user's program is refused the same way, with the program going on --------------------------------")
    e = Term(BOX, "RUN bp zzisced", 100, 30)
    L = e.lines()
    row("100x30: !CED() prints the message and returns; the program goes on (CEDBACK) and nothing was drawn",
        any("CED needs a window of at least 140 columns by 42 lines; this one is 100 by 30" in l for l in L) and any("CEDBACK" in l for l in L)
        and not any("k01" in l for l in L), text(L, 12))
    e.end()
    e = Term(BOX, "RUN bp zzisced", 140, 42)
    L = e.lines()
    row("control: at 140x42 the same program shows the editor", any("k01" in l for l in L) and not any("CEDBACK" in l for l in L), text(L, 6))
    leave(e)

    say("\n--- B: the debugger on a window under 140 by 42: the message once, then line mode (not a refusal) ---------------------")
    for (c, r) in ((100, 30), (80, 24), (139, 42), (140, 41)):
        e = Term(BOX, "RUN bp %s" % DBG, c, r, idle=2.0)
        L = e.lines()
        want = "The debugger needs a window of at least 140 columns by 42 lines for its full-screen display; this one is %d by %d, so it is " % (c, r)
        joined = re.sub(r"\s+", "", "".join(L))          # the terminal wraps the message at its edge, so spaces are not compared
        row("%dx%d: the debugger says why it is in line mode (message 11602, the size named)" % (c, r),
            re.sub(r"\s+", "", want) in joined, text(L, 12))
        row("%dx%d: ...once only" % (c, r), joined.count("Thedebuggerneedsawindow") == 1, joined[:200])
        row("%dx%d: ...it is line mode: no numbered source frame, no title bar, the stop is reported on a line (4:) and the prompt is >" % (c, r),
            not any(re.match(r"^\s*1:\s+s = 'plain'", l) for l in L) and any(re.match(r"^4:\s+crt 'AFTER-ONE'", l) for l in L)
            and any(l.startswith(">") for l in L), text(L, 14))
        L = e.keys("/s", RET)
        row("%dx%d: ...and a debug session works in it: /s shows the variable" % (c, r), any('String (5 bytes)' in l and "plain" in l for l in L), text(L, 14))
        L = e.keys("r", RET, idle=1.0)
        row("%dx%d: ...and R runs the program on: AFTER-ONE, and SD is at its prompt" % (c, r), any(l.strip() == "AFTER-ONE" for l in L) and prompt_shown(e), text(L, 14))
        e.end()
    e = Term(BOX, "RUN bp %s" % DBG, 140, 42, idle=2.0)
    L = e.lines()
    row("control: at 140 by 42 the debugger is full screen (numbered source, command line on the last row) and says nothing about line mode",
        any(re.match(r"^\s*1:\s+s = 'plain'", l) for l in L) and L[41].startswith(">") and not any("line mode" in l for l in L), text(L, 6) + repr(L[41][:20]))
    e.keys("r", RET, idle=1.0)
    e.end()
    e = Term(BOX, "RUN bp %s" % DBG, 140, 42, pre=("TERM 100,30",), idle=2.0)
    L = e.lines()
    row("a 140 by 42 window whose display was set to 100 by 30 with TERM: the debugger is in line mode, with the message",
        any("this one is 100 by 30" in l for l in L) and not any(re.match(r"^\s*1:\s+s = 'plain'", l) for l in L), text(L, 12))
    e.keys("r", RET, idle=1.0)
    e.end()


def check_corner(e, mark, w, h, base, what):
    got, n = e.replay(mark, w, h)
    d = corner_diff(got, base, w, h)
    row("%s: the upper left corner is drawn again, cell for cell as at 140 by 42 (replayed on a blank %dx%d screen)" % (what, w, h),
        n > 0 and d is None, d or "no bytes written")
    d2 = corner_diff(e.lines(), base, w, h)
    row("%s: ...and the screen shows the same" % what, d2 is None, d2 or "")


def part_c():
    say("\n--- C: a window made smaller after the start shows the upper left corner and nothing past the edge ------------------")
    e = Term(BOX, "IDE %s r1" % F)
    base_ide = list(e.lines())
    e.end()
    # 28 Oct 26: the IDE's lock is the WINDOW's (the layout mode of $sl_guardmode): any window under 140 by 43 holds the keyboard behind the warning, wherever the cursor is -
    #   the editor's cursor is on line 1, row 2, and it shows in every one of these, which used to leave the IDE usable in a corner.  So there is no corner to compare; what must be
    #   true is the lock, and the whole layout, foot included, drawn again the moment the window is big enough.
    for (w, h) in ((100, 30), (80, 24), (139, 42), (139, 43), (140, 42)):
        e = Term(BOX, "IDE %s r1" % F)
        e.resize(w, h)
        L = e.lines()
        row("IDE %dx%d: locked at once although the cursor (line 1) shows: the warning names both sizes" % (w, h), ide_warn(L, w, h), text(L, 6))
        L = e.keys("qzx")
        row("IDE %dx%d: ...and typing does nothing: the warning is still up and qzx is on no row" % (w, h),
            ide_warn(L, w, h) and not any("qzx" in l for l in L), text(L, 6))
        m2 = e.resize(LAY_W, IDE_H)
        got, n = e.replay(m2, LAY_W, IDE_H)
        row("IDE %dx%d: made 140 by 43 again, it draws the whole layout again (replayed: the menu bar, the frame, the status line on row 40, the border and the key row)" % (w, h),
            n > 0 and got[1].startswith("+- IDE") and " File" in got[0] and got[40].startswith("[Editor]") and got[41].strip() != "" and "Esc menu" in got[42],
            "no bytes" if n == 0 else repr(got[40][:30]) + repr(got[42][:30]))
        row("IDE %dx%d: ...the keys typed while locked did not reach the record (line 1 reads L01 the quick, as at the start)" % (w, h),
            "qzx" not in e.lines()[3][:20] and ide_at(e) == (1, 1), repr(e.lines()[3][:30]) + repr(ide_at(e)))
        e.end()

    e = Term(BOX, "CED %s j1" % F)
    base_ced = list(e.lines())
    e.end()
    for (w, h) in ((100, 30), (80, 24), (139, 41), (140, 41)):
        e = Term(BOX, "CED %s j1" % F)
        m = e.resize(w, h)
        check_corner(e, m, w, h, base_ced, "CED %dx%d" % (w, h))
        e.keys("x")
        m2 = e.resize(LAY_W, LAY_H)
        got, n = e.replay(m2, LAY_W, LAY_H)
        d = corner_diff(got, base_ced, LAY_W, LAY_H)
        row("CED %dx%d: made 140 by 42 again, it draws the whole layout again (replayed), as at the start" % (w, h), n > 0 and d is None, d or "no bytes")
        e.end()

    say("\n--- C: a bigger window after the start --------------------------------------------------------------------------------")
    e = Term(BOX, "IDE %s r1" % F)
    e.resize(200, 60)
    L = e.lines()
    row("IDE grown to 200 by 60: the layout takes the window (status line on row 57, the border and the key row below it, frame 200 wide), nothing is lost",
        L[57].startswith("[Editor]  " + F + " r1") and len(L[1].rstrip()) == 200 and "L01 the quick" in L[3] and "Esc menu" in L[59], repr(L[57][:30]) + str(len(L[1].rstrip())))
    leave(e)

    say("\n--- C: the debugger, shrunk in width only (the command line is still on the screen) ---------------------------------")
    e = Term(BOX, "RUN bp %s" % DBG, idle=2.0)
    base_dbg = list(e.lines())
    row("setup: the debugger is up full screen at 140 by 42", any(re.match(r"^\s*1:\s+s = 'plain'", l) for l in base_dbg) and base_dbg[41].startswith(">"),
        text(base_dbg, 4))
    m = e.resize(100, 42)
    check_corner(e, m, 100, 42, base_dbg, "debugger 100x42")
    L = e.keys("/s", RET)
    row("debugger 100x42: no warning (the cursor is on the screen), and a command works: /s shows the variable",
        "The window is" not in text(L, 6) and any('String (5 bytes)' in l and "plain" in l for l in L), text(L[30:], 12))
    m2 = e.resize(LAY_W, LAY_H)
    got, n = e.replay(m2, LAY_W, LAY_H)
    d = corner_diff(got[:34], base_dbg[:34], LAY_W, 34)
    row("debugger 100x42 -> 140x42: it lays out and draws the whole screen again (replayed: the title and the source)", n > 0 and d is None, d or "no bytes")
    e.keys("r", RET, idle=1.0)
    e.end()


def part_d():
    say("\n--- D: the window lock (the layout mode): the IDE ------------------------------------------------------------------")
    burst = DOWN * 45
    e = Term(BOX, "IDE %s r1" % F)
    L = e.keys(burst, idle=1.0)
    # 19 Oct 26: the IDE writes its status line one second after the last key (the timeout of its wait), and the screen library now writes
    # so little for a key that the terminal is quiet for a second BEFORE that: the row waits for the line, not for the silence
    time.sleep(1.5)
    e.s.settle(0.4)
    L = e.lines()
    row("control, 140x43: 45 Downs are all accepted (line 46) and no warning shows", ide_at(e) == (46, 1) and "The window is" not in text(L, 6), repr(ide_at(e)))
    leave(e)

    e = Term(BOX, "IDE %s r1" % F)
    base = list(e.lines())
    e.keys("Z")
    row("setup: Z typed at 1.1 (a change nobody has saved)", "ZL01" in e.lines()[3], repr(e.lines()[3][:50]))
    m = e.resize(100, 30)
    row("100x30: locked at once, with no key typed: the cursor (line 1, row 3) shows, and it is the WINDOW that decides, against 140 by 43",
        ide_warn(e.lines(), 100, 30), text(e.lines(), 8))
    L = e.keys(burst, idle=1.2)
    row("...45 Downs in one burst change nothing: the warning is still in the upper left", ide_warn(L, 100, 30), text(L, 8))
    row("...it says that text not saved is lost unless a recovery copy is on (the person must know before choosing Ctrl-Q)",
        "recovery copy" in " ".join(l.strip() for l in L[:6]), text(L, 6))
    row("...the rest of the screen is blank (nothing of the IDE shows)", not any("L01" in l or "ZL" in l or "File" in l for l in L) and not any(l.strip() for l in L[8:]),
        text(L, 12))
    row("...the warning fits the window (no row wider than 100)", max(len(l) for l in L) <= 100, str(max(len(l) for l in L)))
    row("...and it is in reverse video", e.s.screen.reverse(0).startswith("The window"), repr(e.s.screen.reverse(0)[:30]))
    L = e.keys("xyz", RET, DOWN, UP, CTRL("s"), F10, idle=0.6)
    row("keys while locked are ignored: the warning is still there, nothing was typed, the menu did not open",
        ide_warn(L, 100, 30) and not any("xyz" in l for l in L), text(L, 6))
    m2 = e.resize(LAY_W, IDE_H, wait=2.2)
    got, n = e.replay(m2, LAY_W, IDE_H)
    row("made 140 by 43 again: the lock is lifted without a key and the IDE draws the whole layout (replayed: the menu bar, the frame, the foot)",
        n > 0 and got[1].startswith("+- IDE") and " File" in got[0] and got[40].startswith("[Editor]") and "Esc menu" in got[42], "no bytes" if n == 0 else text(got, 3))
    L = e.lines()
    at = ide_at(e)
    row("...all 45 Downs were dropped: the cursor is still on line 1 (column 2, after the Z)", at == (1, 2), repr(at))
    row("...the xyz typed while locked is not in the record", not any("xyz" in l for l in L), "")
    row("...and the editor takes keys again: Q goes in at line 1", "Q" in e.keys("Q")[3][:60], repr(e.lines()[3][:60]))
    e.keys(BS)
    e.resize(100, 30)
    L = e.lines()
    row("shrunk to 100x30 again: locked at once, with no key typed", ide_warn(L, 100, 30), text(L, 4))
    L = e.keys(CTRL("q"))
    row("Ctrl-Q asks 'Leave? (changes are NOT saved) y/n' in the same box", any("Leave? (changes are NOT saved) y/n" in l for l in L[:4]), text(L, 4))
    row("...and the warning is gone while it asks", not any("The window is" in l for l in L), "")
    L = e.keys("n")
    row("n goes back to the warning", ide_warn(L, 100, 30) and not any("Leave?" in l for l in L), text(L, 4))
    e.keys(CTRL("q"))
    L = e.keys("x")
    row("any other key than y goes back to the warning too", ide_warn(L, 100, 30), text(L, 4))
    e.keys(CTRL("q"))
    mk = e.mark()
    L = e.keys("y", idle=1.2)
    row("y leaves the IDE: the screen is cleared and SD is at its prompt", prompt_shown(e) and not any("Leave?" in l or "The window is" in l for l in L), text(L, 6))
    tail = e.s.raw[mk:].decode("latin-1")
    row("...the terminal's modes are given back: mouse reporting is switched off (ESC [ ? 1000 l) on the way out", "\x1b[?1000l" in tail, repr(tail[-80:]))
    row("...nothing was saved: the record on disk is as it was", rec("r1") == RECORD, repr(rec("r1"))[:100])
    e.end()

    say("\n--- D: the warning fits whatever window it is shown in: the longest of three wordings whose rows fit, the sizes always in the first ---")
    for (w, h) in ((100, 30), (70, 5), (60, 4), (40, 3), (30, 2), (20, 1)):
        e = Term(BOX, "IDE %s r1" % F)
        e.resize(w, h)
        L = e.lines()
        t = " ".join(l.strip() for l in L[:h])
        row("%dx%d: the first row names the window's size" % (w, h), re.search(r"\b%d by %d(?!\d)" % (w, h), L[0]) is not None, text(L, h))
        row("%dx%d: ...nothing is wider than the window, and the rows below the warning are blank" % (w, h),
            max(len(l.rstrip()) for l in L) <= w and not any(l.strip() for l in L[min(h, 6):]), text(L, h))
        if w >= 30:
            row("%dx%d: ...it says Ctrl-Q leaves" % (w, h), "Ctrl-Q" in t, text(L, h))
        if w >= 40 and h >= 3:
            row("%dx%d: ...and that unsaved text is lost" % (w, h), "lost" in t, text(L, h))
        e.keys(CTRL("q"))
        e.keys("y", idle=1.2)                       # the IDE is locked: Ctrl-Q, y is its way out
        e.end()

    say("\n--- D: a question the IDE asks while the window is made smaller: the lock's way out closes it as Esc does --------------")
    e = Term(BOX, "IDE %s r1" % F)
    e.keys(DOWN * 20, idle=0.8)
    L = e.keys(CTRL("l"), idle=0.8)
    row("setup: Ctrl-L opens the go-to-line question (its box is on rows 19 to 22)",
        any("Go to (a line" in l for l in L[18:24]), text(L[16:26], 10))        # 29 Oct 26: message 11209 reads "Go to (a line; line,column; ..." ("Line number:" was the first wording)
    e.resize(100, 16)
    L = e.lines()
    row("100x16 with the question open: locked (the question's own cursor is on row 20, which this window does not show, but the window decides)", ide_warn(L, 100, 16), text(L, 6))
    e.keys(CTRL("q"))
    L = e.keys("y", idle=1.2)
    row("...Ctrl-Q, y leaves: the question was closed as Esc and the IDE was left (SD at its prompt)", prompt_shown(e) and not any("Go to (a line" in l for l in L),
        text(L, 8))
    e.end()

    say("\n--- D: a menu open, and a message box open (Save them?), while the window is made smaller ---------------------------")
    e = Term(BOX, "IDE %s r1" % F)
    e.keys(F10)
    L = e.keys(DOWN * 6)
    row("setup: F10 opens the File menu and six Downs select its last item, Quit (the seventh entry since S.88 Phase 4; menu rows 1 to 9)", any(l.lstrip().startswith("Quit") for l in L[1:11]), text(L, 11))
    e.resize(140, 4)
    L = e.lines()
    row("140x4 with the menu open: locked, with whichever wording fits four rows", ide_warn(L, 140, 4), text(L, 5))
    L = e.keys("xyz", RET, idle=0.6)
    row("...keys are ignored (a Return would have chosen Quit and left the IDE)", ide_warn(L, 140, 4), text(L, 5))
    e.keys(CTRL("q"))
    L = e.keys("y", idle=1.2)
    row("...Ctrl-Q, y closes the menu as Esc does and leaves the IDE (SD at its prompt, not looping in the menu)", prompt_shown(e), text(L, 6))
    e.end()

    e = Term(BOX, "IDE %s r1" % F)
    e.keys("Z")
    e.keys(F10)
    L = e.keys(DOWN * 5, RET, idle=0.8)                 # Close record is the sixth entry (New, Open, Save, Save as, Write a copy, Close, Quit; S.88 Phase 4)
    row("setup: Close record on a changed record asks 'Save them?' in a box over the editor (its buttons are on row 19)",
        any("[ Save ]" in l for l in L[17:22]), text(L[15:24], 9))
    e.resize(140, 10)
    L = e.lines()
    row("140x10 with the box open: locked at once", ide_warn(L, 140, 10), text(L, 5))
    L = e.keys("d", "s", RET, idle=0.6)
    row("...keys are ignored: Discard, Save and Return were not taken (the warning is still up)", ide_warn(L, 140, 10), text(L, 5))
    e.keys(CTRL("q"))
    L = e.keys("y", idle=1.2)
    row("...Ctrl-Q, y closes the box as Esc does and leaves the IDE (SD at its prompt)", prompt_shown(e), text(L, 6))
    row("...nothing was saved: the record on disk is as it was", rec("r1") == RECORD, repr(rec("r1"))[:100])
    e.end()
    e = Term(BOX, "IDE %s r1" % F)
    e.keys("Z")
    e.keys(F10)
    e.keys(DOWN * 5, RET, idle=0.8)                     # Close record, the sixth entry
    L = e.lines()
    row("control: the same box at the full size (140 by 43; a window of 24 lines would be locked now, the cursor is no longer the test): no warning, the box is up",
        "The window is" not in text(L, 6) and any("[ Save ]" in l for l in L[17:22]), text(L[15:24], 9))
    L = e.keys("c", idle=1.0)
    row("...and its keys work: c chooses Cancel, the box closes and the record is still open with its change (line 1 reads ZL01)",
        "[ Save ]" not in "\n".join(L) and "ZL01" in L[3], text(L[2:5], 3))
    e.keys(CTRL("q"), idle=0.8)
    e.keys("d", idle=1.0)                       # Discard: the change must not reach the record for the parts that follow
    row("...Ctrl-Q, d leaves without saving: the record on disk is as it was", rec("r1") == RECORD, repr(rec("r1"))[:100])
    e.end()


def part_e():
    say("\n--- E: the cursor lock: CED ---------------------------------------------------------------------------------------------")
    burst = DOWN * 45
    e = Term(BOX, "CED %s j1" % F)
    L = e.keys(burst, idle=1.0)
    row("control, 140x42: 45 Downs are all accepted (the '>' is on the 46th member, row 47 is off; the table scrolled) and no warning shows",
        "The window is" not in text(L, 6) and any(l.startswith(">") and "k46" in l for l in L), text(L, 6))
    leave(e)

    e = Term(BOX, "CED %s j1" % F)
    base = list(e.lines())
    held = locked("j1")
    row("control: while CED has the record, another session finds it locked", held is True, repr(held))
    e.resize(100, 30)
    L = e.keys(burst, idle=1.2)
    row("100x30: 45 Downs in one burst: the selected row leaves the screen and CED shows the warning in the upper left",
        warn_shown(L, 100, 30, "CED"), text(L, 8))
    row("...the rest of the screen is blank", not any("k0" in l for l in L) and not any(l.strip() for l in L[8:]), text(L, 12))
    L = e.keys("xyz", RET, DOWN, "d", CTRL("s"), idle=0.6)
    row("keys while locked are ignored (a Return would have opened the element, d... nothing was done)",
        warn_shown(L, 100, 30, "CED") and not any("xyz" in l for l in L), text(L, 6))
    m2 = e.resize(LAY_W, LAY_H, wait=2.2)
    got, n = e.replay(m2, LAY_W, LAY_H)
    L = e.lines()
    row("made 140 by 42 again: the lock is lifted without a key and CED draws the whole layout (replayed)",
        n > 0 and "k01" in got[2] and "The window is" not in text(L, 6), "no bytes" if n == 0 else text(got, 3))
    row("...the Downs after the first off-screen one were dropped: the selected member is k29 (the '>' is on it)",
        any(l.startswith(">") and "k29" in l for l in L), "\n".join(l[:40] for l in L[26:34]))
    e.resize(100, 30)
    L = e.lines()
    row("shrunk to 100x30 with the selection on member 29 (row 30): locked at once", warn_shown(L, 100, 30, "CED"), text(L, 4))
    L = e.keys(CTRL("q"))
    row("Ctrl-Q asks 'Leave? (changes are NOT saved) y/n' in the same box", any("Leave? (changes are NOT saved) y/n" in l for l in L[:4]), text(L, 4))
    L = e.keys("n")
    row("n goes back to the warning", warn_shown(L, 100, 30, "CED"), text(L, 4))
    held = locked("j1")
    row("control: CED still has the record locked", held is True, repr(held))
    e.keys(CTRL("q"))
    mk = e.mark()
    L = e.keys("y", idle=1.2)
    row("y leaves CED: the screen is cleared and SD is at its prompt", prompt_shown(e) and not any("Leave?" in l or "The window is" in l for l in L), text(L, 6))
    tail = e.s.raw[mk:].decode("latin-1")
    row("...the terminal's modes are given back: mouse reporting is switched off (ESC [ ? 1000 l) on the way out", "\x1b[?1000l" in tail, repr(tail[-80:]))
    row("...the record lock is given back", locked("j1") is False, repr(locked("j1")))
    row("...the record on disk is as it was", rec("j1") == [JSONREC], repr(rec("j1"))[:60])
    e.end()


def part_f():
    say("\n--- F: the debugger: the cursor lock, and a user's SCREEN OPEN program, which SD imposes nothing on ---------------------")
    e = Term(BOX, "RUN bp %s" % DBG, idle=2.0)
    base = list(e.lines())
    e.keys("/n", RET)
    row("setup: the debugger is full screen at 140x42 and answers a command", any("Integer" in l or "5" in l for l in e.lines()[34:41]), text(e.lines()[34:], 8))
    e.resize(140, 30)
    L = e.lines()
    row("140x30: the command line (row 41) is off the screen: locked at once, with no key typed", warn_shown(L, 140, 30, "the debugger"), text(L, 6))
    L = e.keys("/s", RET, "r", RET, idle=0.6)
    row("keys while locked are ignored: nothing was run, the warning is still there", warn_shown(L, 140, 30, "the debugger") and not any(l.strip() == "AFTER-ONE" for l in L), text(L, 6))
    m2 = e.resize(LAY_W, LAY_H, wait=2.2)
    got, n = e.replay(m2, LAY_W, LAY_H)
    L = e.lines()
    row("made 140 by 42 again: the lock is lifted without a key and the debugger draws its whole screen (replayed)",
        n > 0 and corner_diff(got[:34], base[:34], LAY_W, 34) is None and "The window is" not in text(L, 6), "no bytes" if n == 0 else text(got, 3))
    row("...the keys typed while locked did not reach the command line (it is empty) or the program (not run)",
        L[41].rstrip() == ">" and not any(l.strip() == "AFTER-ONE" for l in L) and not any('String (5 bytes)' in l for l in L[34:41]), repr(L[41][:30]))
    L = e.keys("/s", RET)
    row("...and the debugger takes commands again", any('String (5 bytes)' in l and "plain" in l for l in L[34:41]), text(L[34:], 8))
    e.resize(140, 30)
    L = e.keys(CTRL("q"))
    row("locked again: Ctrl-Q asks 'Leave? (changes are NOT saved) y/n'", any("Leave? (changes are NOT saved) y/n" in l for l in L[:4]), text(L, 4))
    L = e.keys("n")
    row("n goes back to the warning", warn_shown(L, 140, 30, "the debugger"), text(L, 4))
    e.keys(CTRL("q"))
    L = e.keys("y", idle=1.5)
    row("y leaves the debugger the way F3 does: 'Debugging terminated', the program did not run on, SD is at its prompt",
        any("Debugging terminated" in l for l in L) and not any(l.strip() == "AFTER-ONE" for l in L) and prompt_shown(e), text([l for l in L if l.strip()], 8))
    e.end()

    say("\n--- F: controls - a user's SCREEN OPEN program is not refused, not locked, and keeps the keys -------------------------")
    for (c, r) in ((100, 30), (80, 24)):
        e = Term(BOX, "RUN bp %s" % SCR, c, r)
        L = e.lines()
        row("%dx%d: the program opens its screen and draws (USERSCR on row 0): SD imposes no size on it" % (c, r), L[0].startswith("USERSCR"), text(L, 3))
        L = e.keys("a")
        row("%dx%d: ...it gets keys: a gives KEY a" % (c, r), L[2].startswith("KEY a"), text(L, 4))
        e.resize(60, 20)
        L = e.keys("b")
        row("%dx%d -> 60x20: made smaller still, no warning is ever shown for it and it still gets keys: b gives KEY b" % (c, r),
            "The window is" not in text(L, 6) and L[2].startswith("KEY b"), text(L, 4))
        e.keys("q", idle=1.0)
        row("%dx%d: ...and it ends the way it chose (USERDONE)" % (c, r), any("USERDONE" in l for l in e.lines()), text(e.lines(), 8))
        e.end()
    say("\n--- F: the lock does not outlive the program that asked for it ---------------------------------------------------------")
    e = Term(BOX, "IDE %s r1" % F)
    e.resize(100, 30)
    e.keys(DOWN * 45, idle=1.0)
    e.keys(CTRL("q"))
    e.keys("y", idle=1.2)
    row("setup: the IDE was left from the lock", prompt_shown(e), text(e.lines(), 4))
    e.s.type("RUN bp %s\r" % SCR, idle=1.2)
    e.keys("a")
    L = e.lines()
    row("a user's SCREEN OPEN program run afterwards in the same session is not guarded: keys reach it (KEY a), no warning",
        any(l.startswith("KEY a") for l in L) and "The window is" not in text(L, 6), text(L, 4))
    e.keys("q", idle=1.0)
    e.end()


# ------------------------------------------------------------------------------------------------------------------------------
# MUTANTS.  Each edits the sandbox's copy of one program, compiles it, runs the parts named, and the rows listed must FAIL.
#   noguard      $sl_key never asks for the cursor lock: the IDE and CED take keys with the cursor off the screen.     D, E
#   nocurat      $sl_curat does not remember where the cursor is: the lock has nothing to ask.                           D, E
#   noquit       $sl_key takes the user's y for a lift: the user cannot leave from the lock.                             D, E
#   nowindowlock the IDE asks for the old cursor lock, not the window's (the layout mode): a window under 140 by 43 with the
#                cursor on screen is not locked.                                                                       C, D
#   nokeyrow     the IDE's function-key row is blank.                                                                    A, C
#   noneed       the IDE does not ask for the size at the start.                                                         B
#   ceduneed     CED (ced_edit) does not ask for the size: !CED() draws on any window.                                  B
#   dbgnoneed    the debugger does not fall back to line mode: it is full screen on any window.                         B
#   dbgnoguard   the debugger's wait.key never calls $sl_guard.                                                         F
#   dbgnoquit    the debugger's wait.key takes the user's y for a lift.                                                 F
#   nomap        the question box (screen ask) does not read guardquit as Esc.                                         D (the question)
#   nomapmenu    the menu does not read guardquit as Esc.                                                               D (the menu)
#   nomapbox     the message box does not read guardquit as Esc.                                                        D (the box)
#   nomsgcur     the message box does not tell the cursor lock where its button is.                                     D (the box)
MUTANTS = {
    "noguard": ("sl_key", "      if not(g.quit) then gosub guard.cursor\n", "      null\n", "d,e"),
    "nocurat": ("sl_curat", "         cu.has = 1\n", "         cu.has = 0\n", "d,e"),
    "noquit": ("sl_key", "   if gres = 'quit' then\n      g.quit = 1\n   end else\n",
               "   if gres = 'quit' then\n      sz.last = 'x'\n   end else\n", "d,e"),
    "nowindowlock": ("ide", "$sl_guardmode('IDE', LAYW, LAYH, 'layout', LAYW, LAYH)", "$sl_guardmode('IDE', LAYW, LAYH)", "c,d"),
    "nokeyrow": ("ide", "   call $tk_fkeys(fk.ctx, ide.keys, '', fk.text)\n", "   fk.text = ''\n", "a,c"),
    "noneed": ("ide", "   if need.msg # '' then\n      break on\n", "   if 0 then\n      break on\n", "b"),
    "cednoneed": ("ced_edit", "   if need.msg # '' then\n      display need.msg\n", "   if 0 then\n      display need.msg\n", "b"),
    "dbgnoneed": ("debug", "      if need.msg # '' then\n         full.screen = @false\n", "      if 0 then\n         full.screen = @false\n", "b"),
    "dbgnoguard": ("debug", "      if cur.x >= win.w or command.line >= win.h then\n", "      if 0 then\n", "f"),
    "dbgnoquit": ("debug", "         if guard.result = 'quit' then\n            key.quit = @true\n            return\n         end\n",
                  "         if guard.result = 'quit' then\n            null\n         end\n", "f"),
    "nomap": ("screen_ask", "      if k = '' or k = 'guardquit' then k = 'esc'", "      if k = '' then k = 'esc'", "d"),
    "nomapmenu": ("sl_menu", "            if key = '' or key = 'guardquit' then key = 'esc'", "            if key = '' then key = 'esc'", "d"),
    "nomapbox": ("sl_msgbox", "            if key = '' or key = 'guardquit' then key = 'esc'", "            if key = '' then key = 'esc'", "d"),
    "nomsgcur": ("sl_msgbox", "   if g.on then call $sl_curat(bx + sx + 1, by + nl + 2)", "   if 0 then call $sl_curat(bx + sx + 1, by + nl + 2)", "d"),
}


def apply_mutant(name):
    prog, old, new, parts = MUTANTS[name]
    path = os.path.join(SYS, "gpl.bp", prog)
    with open(path, encoding="utf-8", errors="replace") as fh:
        t = fh.read()
    if t.count(old) != 1:
        bail("mutant %s: the text to change is in %d places in the sandbox's %s, not 1" % (name, t.count(old), prog))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(t.replace(old, new))
    out = internal("BASIC gpl.bp " + prog)
    if "Compiled 1 program(s) with no errors" not in out:
        bail("mutant %s did not compile:\n%s" % (name, out[-600:]))
    say("sandbox-ide-small: MUTANT %s applied to %s in the sandbox (parts %s); rows that fail below are the ones it breaks" % (name, prog, parts))
    return parts


def main():
    global BOX, SYS
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        print(__doc__ or "usage: sandbox-ide-small.py <dir> [--build] [--only=a,b,c,d,e,f] [--mutant=NAME]")
        return 2
    BOX = os.path.abspath(args[0])
    SYS = os.path.join(BOX, "sys")
    only = next((set(a.split("=", 1)[1].split(",")) for a in sys.argv[1:] if a.startswith("--only=")), None)
    mutant = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mutant=")), None)
    if "--build" in sys.argv:
        if os.path.exists(BOX) and os.listdir(BOX):
            bail("%s is not empty" % BOX)
        r = subprocess.run([sys.executable, TOOL, BOX, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-ide-small: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(SYS, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % BOX)
    subprocess.run([sys.executable, TOOL, BOX, "start"], capture_output=True, text=True, errors="replace", timeout=120)
    if not cedverb.install(BOX):
        bail("the VOC record ced could not be written; the rows that type CED would be red for that reason")
    if mutant:
        if mutant not in MUTANTS:
            bail("no mutant %s (%s)" % (mutant, ", ".join(MUTANTS)))
        parts = apply_mutant(mutant)
        if only is None:
            only = set(parts.split(","))

    fixture = """   execute 'DELETE.FILE %(f)s' capturing j0
   execute 'CREATE.FILE %(f)s' capturing j1
   open '%(f)s' to f else stop 'no file'
   write %(rec)s on f, 'r1'
   write '%(json)s' on f, 'j1'
   crt 'FIXTURE DONE'
end
""" % {"f": F, "rec": " : @fm : ".join("'%s'" % x for x in RECORD), "json": JSONREC}
    probe = """   open '%(f)s' to f else stop 'no file'
   read r from f, 'r1' then
      crt 'REC r1 ' : convert(@fm, '|', r)
   end else
      crt 'REC r1 <none>'
   end
   read r from f, 'j1' then
      crt 'REC j1 ' : convert(@fm, '|', r)
   end else
      crt 'REC j1 <none>'
   end
end
""" % {"f": F}
    lock = """   open '%(f)s' to f else stop 'no file'
   for k = 1 to 2
      id = if k = 1 then 'r1' else 'j1'
      readu r from f, id locked
         crt 'ISLOCK ' : id : ' HELD'
      end then
         crt 'ISLOCK ' : id : ' FREE'
         release f, id
      end else
         crt 'ISLOCK ' : id : ' ABSENT'
      end
   next k
end
""" % {"f": F}
    dbg = """   s = 'plain'
   n = 5
   debug
   crt 'AFTER-ONE'
end
"""
    scr = """   screen open clear then
      screen text 'USERSCR' at 0,0
      screen text 'FAR' at 130,10
      loop
         screen key timeout 30 returning k else k = 'q'
         screen text 'KEY ' : k : '        ' at 0,2
      until k = 'q'
      repeat
      screen close
   end else
      crt 'NOSCREEN'
   end
   crt 'USERDONE'
end
"""
    ced = """   c = jparse('%s')
   call !ced(c)
   crt 'CEDBACK'
end
""" % JSONREC
    progs = {"zzisfix": fixture, "zzisprobe": probe, "zzislock": lock, "zzisced": ced}
    progs_dbg = {DBG: dbg, SCR: scr}
    for nm, body in list(progs.items()) + list(progs_dbg.items()):
        with open(os.path.join(SYS, "bp", nm), "w") as fh:
            fh.write(body)
    try:
        say("\n--- fixture --------------------------------------------------------------------------------------")
        names = list(progs) + [SCR]
        out = sess(*(["BASIC bp %s" % n for n in names] + ["BASIC bp %s DEBUGGING" % DBG, "RUN bp zzisfix"]))
        row("setup: the programs compiled and the fixture file was made",
            len(re.findall(r"(?m)^Compiled 1 program\(s\) with no errors", out)) == len(names) + 1 and "FIXTURE DONE" in out, out[-900:])
        if "FIXTURE DONE" not in out:
            bail("the fixture was not made:\n" + out[-800:])
        row("setup: control - the records are as written", rec("r1") == RECORD and rec("j1") == [JSONREC], repr(rec("j1"))[:80])
        row("setup: control - nobody has the records locked", locked("r1") is False and locked("j1") is False, "")
        for key, fn in (("a", part_a), ("b", part_b), ("c", part_c), ("d", part_d), ("e", part_e), ("f", part_f)):
            if only is None or key in only:
                fn()
    finally:
        if "--keep" in sys.argv:
            say("\nsandbox-ide-small: --keep: the sandbox is left running with the fixture file %s" % F)
        else:
            say("\n--- cleanup ---------------------------------------------------------------------------------------")
            sess("DELETE.FILE %s" % F)
            for nm in list(progs) + list(progs_dbg):
                for d in ("bp", "bp.out"):
                    pth = os.path.join(SYS, d, nm)
                    if os.path.exists(pth):
                        os.remove(pth)
            subprocess.run([sys.executable, TOOL, BOX, "stop"], capture_output=True, text=True, errors="replace", timeout=120)

    say("\nsandbox-ide-small: %d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        bail("no row ran - a broken test, not a pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
