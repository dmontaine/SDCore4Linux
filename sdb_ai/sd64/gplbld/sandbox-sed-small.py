#!/usr/bin/env python3
#
# sandbox-sed-small.py - SED at 140 by 42, refused below it, survived when the window shrinks, and the cursor lock.  No install,
# no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-sed-small.py <dir> [--build] [--only=a,b,c,d,e]
#                                                                                                     [--mutant=NAME]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or absent);
# without it <dir> must already be built, which is how the same script is run against an OLD tree to prove it can fail.  Exit 0
# every row passed, 1 a row failed, 2 it could not run.  The sandbox is stopped when the suite ends; remove its directory
# afterwards (each run leaves ~14,000 files).
#
# START-HISTORY:
# 18 Oct 26 dm  New (plan-terminal-140x42.md phases 2, 4 and 6 for SED): SED is laid out for 140 by 42 (it was 120 by 36); a window
#               smaller than that is refused, with one message the library owns; a window made smaller after SED has started shows
#               the upper left corner of the layout and nothing past the edge; and while the cursor is off the screen the keys are
#               ignored and a warning is shown until the window is made bigger or the user leaves with Ctrl-Q.
# END-HISTORY
#
# HOW IT DRIVES SED.  On a PSEUDO-TERMINAL (ptydrive.py), the window size set BEFORE SD starts (it asks the tty when it starts) and
# changed afterwards with TIOCSWINSZ, which is what dragging the corner of a terminal does (SIGWINCH).  The screen is read from the
# emulator in termscreen.py.
#
# THE INSTRUMENT, AND WHAT IT REFUSES.  The emulator KEEPS what it shows when the window is resized (a terminal does not reflow a
# full-screen program's picture), so a SED that never drew again after a shrink would still LOOK right.  Every row that compares a
# screen after a resize therefore compares a REPLAY: a blank emulator of the new size fed only the bytes SED wrote after the
# resize.  Every cell the replay shows, SED drew itself.  A row that finds nothing to compare fails, a replay of no bytes fails, and
# the emulator wraps text that runs off the right edge and clamps a cursor move below the bottom, so a SED that draws past the
# edge disturbs the rows the corner is compared with.  Each shrink has a control: the same keys at the full size.
#
# MUTANTS.  --mutant=NAME edits the SANDBOX's copy of a program (never the tree), compiles it and runs the parts that matter for it;
# the rows it should break are listed with it below (MUTANTS).  Nothing is run from the tree.

import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ptydrive import PtySession  # noqa: E402
from termscreen import Screen  # noqa: E402

TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
RUN = "%05d" % (os.getpid() % 100000)
F = os.environ.get("SMFILE") or "zzsm" + RUN         # the fixture file (SMFILE names it by hand, with --keep, for a debugging session)
passed = failed = 0
BOX = SYS = None

LAY_W, LAY_H = 140, 42                              # what SED is laid out for
UP, DOWN, LEFT, RIGHT = "\x1bOA", "\x1bOB", "\x1bOD", "\x1bOC"
F10 = "\x1b[21~"
ESC, RET, BS = "\x1b", "\r", "\x7f"
CTRL = lambda ch: chr(ord(ch.upper()) - 64)         # noqa: E731
END = CTRL("e")


def click(x, y, b=0, rel=False):
    """A mouse report as an xterm sends it in SGR mode; x and y count from 1."""
    return "\x1b[<%d;%d;%d%s" % (b, x, y, "m" if rel else "M")


def mkline(i):
    if i == 2:
        return ("L02 " + "0123456789" * 20)[:146] + ">>END2"          # 152 characters: wider than the layout
    if i == 3:
        return ("L03 " + "abcdefghij" * 20)[:124] + ">>END3"          # 130 characters: past a window of 100
    return "L%02d the quick brown fox jumps over the lazy dog" % i


RECORD = [mkline(i) for i in range(1, 61)]


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
    say("sandbox-sed-small: CANNOT RUN - " + msg)
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

    def __init__(self, box, cmd, cols=LAY_W, rows=LAY_H, pre=()):
        """pre: commands typed first (TERM 100,30, AUTOLOGOUT 30 ...)."""
        self.cols = cols
        self.rows = rows
        env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"), TERM="xterm")
        self.s = PtySession([os.path.join(box, "sys", "bin", "sd")], os.path.join(box, "user_accounts"), env, cols, rows)
        self.s.settle(1.0)
        self.s.type("TERM xterm\r")
        for p in pre:
            self.s.type(p + "\r", idle=0.6)
        self.s.type(cmd + "\r", idle=1.0)

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
        """Make the window cols by rows (SIGWINCH) and give SED time to notice: it looks about once a second.  Returns the mark
        taken just BEFORE, for replay()."""
        m = self.mark()
        self.s.resize(cols, rows, idle=0.8)
        time.sleep(wait)
        self.s.settle(0.8)
        self.cols, self.rows = cols, rows
        return m

    def replay(self, mark, cols=None, rows=None):
        """What a blank terminal of the current size shows when given only the bytes SED wrote since mark."""
        scr = Screen(cols or self.cols, rows or self.rows)
        data = self.s.raw[mark:].decode("latin-1")
        scr.feed(data)
        return scr.lines(), len(data)

    def end(self):
        self.s.type("\rOFF\r", idle=0.5)
        self.s.finish()


def at(e):
    """(line, column) from the status line (the last row of a 140 by 42 window)."""
    t = "\n".join(e.lines()[-3:])
    m = re.search(r"\|\s*(\d+)\.(\d+)", t)
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


def rec(rid="r1"):
    out = sess("RUN bp zzsmprobe")
    m = re.search(r"(?m)^REC %s (.*)$" % re.escape(rid), out)
    return m.group(1).split("|") if m else ["<absent>"]


def locked():
    """True if another session finds the record r1 locked."""
    out = sess("RUN bp zzsmlock")
    m = re.search(r"(?m)^SMLOCK (HELD|FREE|ABSENT)$", out)
    return None if not m else m.group(1) == "HELD"


def leave_asking(e):
    """Leave SED whatever state it is in (Ctrl-Q, then Yes to 'Quit without saving?' if it asks), and the session."""
    e.keys(CTRL("q"))
    e.keys("y")
    e.end()


def prompt_shown(e):
    return any(l.startswith(":") for l in e.lines())


# ------------------------------------------------------------------------------------------------------------------------------
def part_a():
    say("\n--- A: SED is laid out for 140 by 42 ---------------------------------------------------------------------------------")
    e = Term(BOX, "SED %s r1" % F)
    base = e.lines()
    row("control: the record is on the screen (line 1 first, 1.1 of 60 lines)",
        base[1].startswith("L01") and at(e) == (1, 1) and "60 lines" in "\n".join(base[-3:]), repr(base[1][:40]) + repr(at(e)))
    row("the window the session has is 140 by 42, as the instrument believes", len(base) == 42, "%d rows" % len(base))
    row("the menu bar is row 0", "File" in base[0] and "Tools" in base[0], repr(base[0][:60]))
    row("the record starts on row 1 and its 39th line is on row 39", base[1].startswith("L01") and base[39].startswith("L39"),
        repr(base[39][:40]))
    row("the file line is row 40 and holds the file and the record", F in base[40] and "r1" in base[40], repr(base[40][:60]))
    row("the status line is row 41", "60 lines" in base[41] and "1.1" in base[41], repr(base[41][:60]))
    row("a line wider than the layout is cut at 140 columns: line 2 is 140 characters and ends at column 140",
        len(base[2]) == LAY_W and base[2] == RECORD[1][:LAY_W], "%d: %r" % (len(base[2]), base[2][-30:]))
    row("the line that is 130 wide is whole", base[3] == RECORD[2] and base[3].endswith(">>END3"), repr(base[3][-30:]))
    row("a row of the record never reaches past column 140", max(len(l) for l in base) <= LAY_W, str(max(len(l) for l in base)))
    quit_ok = leave_asking
    quit_ok(e)

    say("\n--- A: a bigger window is laid out as 140 by 42 and the rest is blank ------------------------------------------------")
    e = Term(BOX, "SED %s r1" % F, 200, 60)
    L = e.lines()
    row("200 by 60: rows 0 to 41 are the 140 by 42 layout, as at 140 by 42", L[:42] == base and not any(l.strip() for l in L[42:]),
        "\n".join(l[:60] for l in L[38:44]))
    row("...and nothing is drawn right of column 140", max(len(l) for l in L) <= LAY_W, str(max(len(l) for l in L)))
    leave_asking(e)


def part_b():
    say("\n--- B: a window under 140 by 42 at the start is refused, in words, and SED draws nothing --------------------------------")
    for (c, r) in ((80, 24), (100, 30), (120, 36), (139, 42), (140, 41)):
        e = Term(BOX, "SED %s r1" % F, c, r)
        L = e.lines()
        want = "SED needs a window of at least 140 columns by 42 lines; this one is %d by %d" % (c, r)
        row("%dx%d: refused with the message, which names the size the window is" % (c, r), any(want in l for l in L), "\n".join(L[:6]))
        row("%dx%d: no bar and no record are drawn, and SD is at its prompt" % (c, r),
            not any(l.startswith("L01") for l in L) and "File" not in L[0] and prompt_shown(e), "\n".join(l[:60] for l in L[:6]))
        e.end()
    e = Term(BOX, "SED %s r1" % F, 140, 42)
    row("control: exactly 140 by 42 starts", e.lines()[1].startswith("L01") and at(e) == (1, 1), repr(e.lines()[1][:30]))
    leave_asking(e)
    e = Term(BOX, "SED %s r1" % F, 140, 42, pre=("TERM 100,30",))
    L = e.lines()
    row("a 140 by 42 window whose display was set to 100 by 30 with TERM is refused: the display is what SED can draw on",
        any("this one is 100 by 30" in l for l in L) and not any(l.startswith("L01") for l in L), "\n".join(l[:70] for l in L[:6]))
    e.end()
    e = Term(BOX, "SED %s r1" % F, 80, 24, pre=("TERM 200,60",))
    L = e.lines()
    row("an 80 by 24 window whose display was set to 200 by 60 is refused too: the window is what there is to draw on",
        any("this one is 80 by 24" in l for l in L) and not any(l.startswith("L01") for l in L), "\n".join(l[:70] for l in L[:6]))
    e.end()


def check_corner(e, mark, w, h, base, what):
    got, n = e.replay(mark, w, h)
    d = corner_diff(got, base, w, h)
    row("%s: SED drew the upper left corner again, cell for cell as at 140 by 42 (replayed on a blank %dx%d screen)" % (what, w, h),
        n > 0 and d is None, d or "no bytes written")
    live = e.lines()
    d2 = corner_diff(live, base, w, h)
    row("%s: ...and the screen shows the same" % what, d2 is None, d2 or "")
    row("%s: ...and SED cleared the screen before it drew" % what, "\x1b[H\x1b[2J" in e.s.raw[mark:].decode("latin-1"),
        repr(e.s.raw[mark:][:60]))


def part_c():
    say("\n--- C: a window made smaller after SED has started shows the upper left corner and nothing past the edge ----------------")
    e = Term(BOX, "SED %s r1" % F)
    base = list(e.lines())
    row("control: the full-size picture is there to compare with", base[1].startswith("L01") and base[39].startswith("L39"), "")
    e.end()
    for (w, h) in ((100, 30), (80, 24), (139, 41), (139, 42), (140, 41), (60, 20)):
        e = Term(BOX, "SED %s r1" % F)
        m = e.resize(w, h)
        check_corner(e, m, w, h, base, "%dx%d" % (w, h))
        if w >= 100 and h >= 30:
            e.keys("ab")
            L = e.lines()
            row("%dx%d: the cursor is on the screen, so typing works (ab in front of line 1)" % (w, h), L[1].startswith("abL01"), repr(L[1][:30]))
        m2 = e.resize(LAY_W, LAY_H)
        got, n = e.replay(m2, LAY_W, LAY_H)
        want = list(base)
        if w >= 100 and h >= 30:
            want[1] = "ab" + base[1]
        # the status line shows 1.3 after "ab"; compare the rows above it, which are the record
        d = corner_diff(got[:40], want[:40], LAY_W, 40)
        row("%dx%d: made 140 by 42 again, SED draws the whole layout again (replayed)" % (w, h), n > 0 and d is None, d or "no bytes")
        e.end()

    say("\n--- C: a key typed just as the window changes is read whole ----------------------------------------------------------------")
    e = Term(BOX, "SED %s r1" % F)
    e.s.resize(100, 30, idle=0.05)           # no wait: SED has not looked at the window yet when the arrow key arrives
    e.s.type(DOWN, idle=0.2)
    time.sleep(1.8)
    e.s.settle(0.8)
    e.s.type("Q", idle=0.6)
    L = e.lines()
    row("the Down typed with the resize moved the cursor to line 2 (Q goes in at the start of line 2) and no OB was typed",
        L[2].startswith("QL02") and L[1].startswith("L01"), repr(L[1][:20]) + " " + repr(L[2][:20]))
    leave_asking(e)

    say("\n--- C: a window bigger than the layout, after the start -------------------------------------------------------------------")
    e = Term(BOX, "SED %s r1" % F)
    m = e.resize(200, 60)
    L = e.lines()
    row("grown to 200 by 60: the layout is as it was in the upper left and the rest is blank",
        L[:42] == base and not any(l.strip() for l in L[42:]) and max(len(l) for l in L) <= LAY_W, "\n".join(l[:50] for l in L[38:44]))
    e.keys(DOWN, "Q")
    row("...and SED goes on working: Down, then Q goes in at the start of line 2", e.lines()[2].startswith("QL02"), repr(e.lines()[2][:20]))
    leave_asking(e)


# ------------------------------------------------------------------------------------------------------------------------------
def part_d():
    say("\n--- D: the cursor lock ----------------------------------------------------------------------------------------------")
    burst = DOWN * 45
    # the control: the same keys at the full size are accepted, and nothing warns
    e = Term(BOX, "SED %s r1" % F)
    L = e.keys(burst, idle=1.0)
    row("control, 140x42: 45 Downs are all accepted (line 46) and no warning shows", at(e) == (46, 1) and not any("off the screen" in l for l in L),
        repr(at(e)))
    e.end()

    e = Term(BOX, "SED %s r1" % F)
    base = list(e.lines())
    e.keys("QQ")
    row("setup: QQ typed at 1.1 (a change nobody has saved)", e.lines()[1].startswith("QQL01"), repr(e.lines()[1][:20]))
    held = locked()
    row("control: while SED has the record, another session finds it locked", held is True, repr(held))
    m = e.resize(100, 30)
    L = e.keys(burst, idle=1.2)
    warn = "\n".join(L[:8])
    row("100x30: 45 Downs in one burst: the cursor leaves the screen and SED shows the warning in the upper left",
        "The window is 100 by 30" in warn and "SED is laid out for 140 by 42" in warn and "Ctrl-Q" in warn, warn)
    row("...the warning is a few rows at the top and the rest of the screen is blank (nothing of the record shows)",
        not any(l.startswith("L") or "QQL" in l for l in L) and not any(l.strip() for l in L[8:]), "\n".join(l[:50] for l in L[:12]))
    row("...the warning fits the window (no row wider than 100)", max(len(l) for l in L) <= 100, str(max(len(l) for l in L)))
    rev = e.s.screen.reverse(0)
    row("...and it is in reverse video", rev.startswith("The window"), repr(rev[:40]))
    # keys while locked
    L = e.keys("zzz", RET, DOWN, DOWN, click(5, 20), click(5, 20, rel=True), UP, CTRL("f"), idle=0.6)
    row("keys and a mouse click while locked are ignored: the warning is still there, nothing was typed",
        "The window is 100 by 30" in "\n".join(L[:8]) and not any("zzz" in l for l in L), "\n".join(l[:60] for l in L[:6]))
    # the window changes but the cursor is still off the screen: the warning is for the new size
    e.resize(100, 29)
    L = e.lines()
    row("the window made 100 by 29 (the cursor is still off): the warning is drawn again for that size",
        "The window is 100 by 29" in "\n".join(L[:8]), "\n".join(l[:60] for l in L[:6]))
    # enlarge: lifted without a key
    m2 = e.resize(LAY_W, LAY_H, wait=2.2)
    got, n = e.replay(m2, LAY_W, LAY_H)
    want = list(base)
    want[1] = "QQ" + base[1]
    d = corner_diff(got[:40], want[:40], LAY_W, 40)
    row("made 140 by 42 again: the lock is lifted without a key and SED draws the whole layout (replayed), text as it was",
        n > 0 and d is None, d or "no bytes")
    row("...the Downs after the first off-screen one were dropped: the cursor is on line 30 (column 3, after the QQ), not 46", at(e) == (30, 3), repr(at(e)))
    row("...the zzz typed while locked is not in the record", not any("zzz" in l for l in e.lines()), "")
    row("...the click while locked did not move the cursor (still on line 30)", at(e) == (30, 3), repr(at(e)))
    e.keys("Z")
    row("...and SED takes keys again: Z goes in at line 30, column 3", e.lines()[30].startswith("L3Z0 the"), repr(e.lines()[30][:20]))
    e.keys(BS)
    # leave from the lock
    e.resize(100, 30)           # the cursor is on line 30, which is row 30: the first row a 30-row window does not show
    L = e.lines()
    row("shrunk to 100x30 with the cursor on line 30 (row 30): locked at once, with no key typed",
        "The window is 100 by 30" in "\n".join(L[:8]), "\n".join(l[:50] for l in L[:4]))
    L = e.keys(CTRL("q"))
    row("Ctrl-Q asks 'Leave? (changes are NOT saved) y/n' in the same box", any("Leave? (changes are NOT saved) y/n" in l for l in L[:4]),
        "\n".join(l[:60] for l in L[:4]))
    row("...and the warning is gone while it asks", not any("The window is" in l for l in L), "")
    L = e.keys("n")
    row("n goes back to the warning", "The window is 100 by 30" in "\n".join(L[:8]) and not any("Leave?" in l for l in L), "\n".join(l[:60] for l in L[:4]))
    L = e.keys(CTRL("q"))
    L = e.keys("x")
    row("any other key than y goes back to the warning too", "The window is 100 by 30" in "\n".join(L[:8]), "\n".join(l[:60] for l in L[:4]))
    still = locked()
    row("control: SED still has the record locked", still is True, repr(still))
    e.keys(CTRL("q"))
    m = e.mark()
    L = e.keys("y", idle=1.0)
    row("y leaves SED: the screen is cleared and SD is at its prompt", prompt_shown(e) and not any("Leave?" in l or "The window is" in l for l in L),
        "\n".join(l[:60] for l in L[:6]))
    tail = e.s.raw[m:].decode("latin-1")
    row("...the terminal's modes are given back: mouse reporting is switched off (ESC [ ? 1000 l) on the way out", "\x1b[?1000l" in tail, repr(tail[-80:]))
    row("...the record lock is given back", locked() is False, repr(locked()))
    row("...the changes were NOT saved: the record on disk is as it was", rec("r1") == RECORD, repr(rec("r1"))[:100])
    e.end()


def part_e():
    say("\n--- E: a prompt on a row that cannot be seen locks, and the way out is not SED's prompt -------------------------------")
    e = Term(BOX, "SED %s r1" % F)
    e.resize(100, 30)
    L = e.keys(CTRL("f"), idle=1.0)
    row("100x30, Ctrl-F (search): the prompt is on the file line, row 39, which this window does not show: locked",
        "The window is 100 by 30" in "\n".join(L[:8]), "\n".join(l[:60] for l in L[:6]))
    L = e.keys("L05", RET, idle=0.6)
    row("what is typed at a prompt nobody can see is ignored", "The window is 100 by 30" in "\n".join(L[:8]), "\n".join(l[:60] for l in L[:6]))
    e.resize(LAY_W, LAY_H, wait=2.2)
    L = e.lines()
    row("made 140 by 42: the prompt is on the screen (file line, row 40) and the screen is whole again",
        L[1].startswith("L01") and "earch" in L[40], repr(L[40][:60]))
    L = e.keys("L05", RET, idle=0.8)
    row("...the prompt works: searching for L05 puts the cursor on line 5", at(e) is not None and at(e)[0] == 5, repr(at(e)))
    # the same, left through the guard's own question
    e.resize(100, 30)
    e.keys(CTRL("f"), idle=1.0)
    L = e.keys(CTRL("q"))
    row("locked at the prompt: Ctrl-Q asks in the guard's box (SED's own question is on a row nobody can see)",
        any("Leave? (changes are NOT saved) y/n" in l for l in L[:4]), "\n".join(l[:60] for l in L[:4]))
    L = e.keys("y", idle=1.0)
    row("...y leaves", prompt_shown(e), "\n".join(l[:60] for l in L[:6]))
    row("...with the record lock given back", locked() is False, repr(locked()))
    e.end()

    say("\n--- E: the cursor off the right edge locks too ----------------------------------------------------------------------")
    e = Term(BOX, "SED %s r1" % F)
    e.keys(DOWN, DOWN, END, idle=0.6)
    row("control, 140x42: End on line 3 puts the cursor at 3.131", at(e) == (3, 131), repr(at(e)))
    e.keys(CTRL("a"), UP, UP, idle=0.5)
    e.resize(100, 30)
    L = e.keys(DOWN, DOWN, END, idle=1.0)
    row("100x30: End on line 3 (130 wide) puts the cursor in column 131: off the screen, locked",
        "The window is 100 by 30" in "\n".join(L[:8]), "\n".join(l[:60] for l in L[:4]))
    e.resize(140, 42, wait=2.2)
    row("...made 140 by 42, the cursor is where End put it (3.131) and the layout is whole",
        at(e) == (3, 131) and e.lines()[3] == RECORD[2], repr(at(e)))
    leave_asking(e)

    say("\n--- E: the library's boxes fit the window ---------------------------------------------------------------------------")
    e = Term(BOX, "SED %s r1" % F)
    e.resize(100, 30)
    e.keys("ab")
    L = e.keys(CTRL("q"), idle=0.8)
    box_rows = [i for i, l in enumerate(L) if "Yes" in l and "No" in l]
    row("100x30, Ctrl-Q with a change: the 'Quit without saving?' box is inside the window (its buttons are on a row under 30)",
        bool(box_rows) and box_rows[0] < 30 and max(len(l) for l in L) <= 100, "\n".join(l[:60] for l in L[8:24]))
    e.keys(RET)             # No is the default
    L = e.keys(F10, idle=0.8)
    row("100x30, F10: the File menu drops down inside the window", any("Exit" in l or "Save" in l for l in L[:30]) and max(len(l) for l in L) <= 100,
        "\n".join(l[:60] for l in L[:12]))
    e.keys(ESC, idle=0.8)
    L = e.lines()
    row("...and Esc closes it: the record is back and the cursor still shows (typing goes in)", L[1].startswith("abL01"), repr(L[1][:20]))
    leave_asking(e)


def part_f():
    say("\n--- F: a session with AUTOLOGOUT waits for the keyboard alone, so a resize is seen at the next key -------------------")
    e = Term(BOX, "SED %s r1" % F)
    base = list(e.lines())
    e.end()
    e = Term(BOX, "SED %s r1" % F, pre=("AUTOLOGOUT 30",))
    row("control: AUTOLOGOUT 30 is in force and SED has started as usual", e.lines()[1].startswith("L01") and e.lines() == base, repr(e.lines()[1][:30]))
    m = e.resize(100, 30)
    e.keys(DOWN, idle=0.8)
    check_corner(e, m, 100, 30, base, "AUTOLOGOUT, 100x30 after the next key")
    L = e.keys(DOWN * 45, idle=1.2)
    row("...45 Downs: the cursor leaves the screen and the warning is shown (the guard waits on the keyboard alone)",
        "The window is 100 by 30" in "\n".join(L[:8]), "\n".join(l[:60] for l in L[:4]))
    e.resize(LAY_W, LAY_H)
    L = e.lines()
    row("...made 140 by 42 with no key: still locked, the lift waits for the next key (the price of AUTOLOGOUT firing on time)",
        "The window is 100 by 30" in "\n".join(L[:8]), "\n".join(l[:60] for l in L[:4]))
    L = e.keys("x", idle=1.0)
    row("...the next key lifts the lock (and is itself dropped): the layout is whole and the cursor on line 30, with no x typed",
        L[1].startswith("L01") and at(e) == (30, 1) and not any(l.startswith("x") or "xL30" in l for l in L), repr(at(e)))
    e.resize(100, 30)
    e.keys(CTRL("q"))
    L = e.keys("y", idle=1.0)
    row("...and Ctrl-Q, y still leaves", prompt_shown(e), "\n".join(l[:60] for l in L[:6]))
    e.end()


# ------------------------------------------------------------------------------------------------------------------------------
# MUTANTS.  Each edits the sandbox's copy of one program, compiles it, runs the parts named, and the rows listed must FAIL.
#   noclip      read.window believes the window is always the layout: no clip, no lock.      C, D, E  (corner, the lock rows)
#   noguard     wait.key never calls $sl_guard: SED takes keys with the cursor off the screen.   D, E  (the lock rows)
#   nodiscard   wait.key calls $sl_guard only when no key is waiting: a burst of keys reaches    D       (45 Downs: line 46, not 30)
#               SED instead of being dropped at the first one the cursor leaves the screen on.
#   nolift      $sl_guard does not return when the window is made bigger.                     D, E    (made 140 by 42 again)
#   noescape    $sl_guard ignores Ctrl-Q: the user cannot leave.                              D, E    (the Leave? rows)
#   noask       $sl_guard leaves at Ctrl-Q without asking.                                    D, E    (the Leave? rows)
#   cutseq      wait.key hands back the news of a resize while a key is waiting, which cuts   C, F    (the Down typed with the resize)
#               an arrow key's three bytes in two.
MUTANTS = {
    "noclip": ("sed", "   call $sl_window(rw.w, rw.h)\n", "   rw.w = SED.COLS ; rw.h = SED.ROWS\n", "c,d,e"),
    "noguard": ("sed", "      if cur.x >= clip.w or cur.y >= clip.h then\n", "      if 0 then\n", "d,e"),
    "nodiscard": ("sed", "      if cur.x >= clip.w or cur.y >= clip.h then\n",
                  "      if (cur.x >= clip.w or cur.y >= clip.h) and not(keyready()) then\n", "d"),
    "nolift": ("sl_guard", "         if cx < w and cy < h then return           ;* the cursor shows again\n", "         null\n", "d,e"),
    "noescape": ("sl_guard", "            case k = char(17)\n", "            case k = char(17) and 0\n", "d,e"),
    "cutseq": ("sed", "      if win.changed and not(keyready()) then", "      if win.changed then", "c,f"),
    "noask": ("sl_guard", "            case k = char(17)\n               asking = @true\n",
              "            case k = char(17)\n               result = 'quit'\n               return\n", "d,e"),
}


def apply_mutant(name):
    prog, old, new, parts = MUTANTS[name]
    path = os.path.join(SYS, "gpl.bp", prog)
    with open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    if text.count(old) != 1:
        bail("mutant %s: the text to change is in %d places in the sandbox's %s, not 1" % (name, text.count(old), prog))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text.replace(old, new))
    out = internal("BASIC gpl.bp " + prog)
    if "Compiled 1 program(s) with no errors" not in out:
        bail("mutant %s did not compile:\n%s" % (name, out[-600:]))
    say("sandbox-sed-small: MUTANT %s applied to %s in the sandbox (parts %s); rows that fail below are the ones it breaks" % (name, prog, parts))
    return parts


def main():
    global BOX, SYS
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        print(__doc__ or "usage: sandbox-sed-small.py <dir> [--build] [--only=a,b,c,d,e] [--mutant=NAME]")
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
        say("sandbox-sed-small: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(SYS, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % BOX)
    subprocess.run([sys.executable, TOOL, BOX, "start"], capture_output=True, text=True, errors="replace", timeout=120)
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
   crt 'FIXTURE DONE'
end
""" % {"f": F, "rec": " : @fm : ".join("'%s'" % x for x in RECORD)}
    probe = """   open '%(f)s' to f else stop 'no file'
   read r from f, 'r1' then
      crt 'REC r1 ' : convert(@fm, '|', r)
   end else
      crt 'REC r1 <none>'
   end
end
""" % {"f": F}
    lock = """   open '%(f)s' to f else stop 'no file'
   readu r from f, 'r1' locked
      crt 'SMLOCK HELD'
   end then
      crt 'SMLOCK FREE'
      release f, 'r1'
   end else
      crt 'SMLOCK ABSENT'
   end
end
""" % {"f": F}
    progs = {"zzsmfix": fixture, "zzsmprobe": probe, "zzsmlock": lock}
    for nm, body in progs.items():
        with open(os.path.join(SYS, "bp", nm), "w") as fh:
            fh.write(body)
    try:
        say("\n--- fixture --------------------------------------------------------------------------------------")
        out = sess(*(["BASIC bp %s" % n for n in progs] + ["RUN bp zzsmfix"]))
        row("setup: the programs compiled and the fixture file was made",
            len(re.findall(r"(?m)^Compiled 1 program\(s\) with no errors", out)) == len(progs) and "FIXTURE DONE" in out, out[-900:])
        if "FIXTURE DONE" not in out:
            bail("the fixture was not made:\n" + out[-800:])
        row("setup: control - the record is as written", rec("r1") == RECORD, repr(rec("r1"))[:100])
        row("setup: control - nobody has the record locked", locked() is False, repr(locked()))
        for key, fn in (("a", part_a), ("b", part_b), ("c", part_c), ("d", part_d), ("e", part_e), ("f", part_f)):
            if only is None or key in only:
                fn()
    finally:
        if "--keep" in sys.argv:
            say("\nsandbox-sed-small: --keep: the sandbox is left running with the fixture file %s and the programs zzsm*" % F)
        else:
            say("\n--- cleanup ---------------------------------------------------------------------------------------")
            sess("DELETE.FILE %s" % F)
            for nm in progs:
                for d in ("bp", "bp.out"):
                    pth = os.path.join(SYS, d, nm)
                    if os.path.exists(pth):
                        os.remove(pth)
            subprocess.run([sys.executable, TOOL, BOX, "stop"], capture_output=True, text=True, errors="replace", timeout=120)

    say("\nsandbox-sed-small: %d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        bail("no row ran - a broken test, not a pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
