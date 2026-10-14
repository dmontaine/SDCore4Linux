#!/usr/bin/env python3
#
# sandbox-sed-edit.py - SED's undo and redo, and SED's mouse.  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-sed-edit.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty
# or absent).  Exit 0 every row passed, 1 a row failed, 2 it could not run.  Only one private SD can exist on a
# machine (shared memory keys 0x53434c91/92): stop the sandbox afterwards with sandbox-fromtree.py <dir> stop.
#
# START-HISTORY:
# 13 Oct 26 dm  Written for SED's undo and redo (Ctrl-Z, Ctrl-Y, Edit > Undo and Redo) and its mouse (a click on the text, on
#               the bar, the wheel; MOUSE ON / OFF and NO.MOUSE in &sed.options&).
# END-HISTORY
#
# HOW IT DRIVES SED.  On a PSEUDO-TERMINAL (ptydrive.py), as sandbox-sed-menu.py does, and reads the screen from the emulator
# in termscreen.py.  A mouse report is typed as the terminal would send it: ESC [ < b ; x ; y M (x and y count from 1).  What the
# record holds on DISK is read back by a BASIC probe through an ordinary session, because an undo changes the screen and not the
# file until the record is saved.  A row that changes something has a control row (the screen before the key); an instrument that
# printed nothing fails its rows rather than passing them.

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ptydrive import PtySession  # noqa: E402

TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
RUN = "%05d" % (os.getpid() % 100000)
F = "zzsu" + RUN                                    # the fixture file
passed = failed = 0

UP, DOWN, LEFT, RIGHT = "\x1bOA", "\x1bOB", "\x1bOD", "\x1bOC"
F10 = "\x1b[21~"
ESC, RET, BS = "\x1b", "\r", "\x7f"
CTRL = lambda ch: chr(ord(ch.upper()) - 64)         # noqa: E731
UNDO, REDO = CTRL("z"), CTRL("y")


def click(x, y, b=0, rel=False):
    """A mouse report as an xterm sends it in SGR mode; x and y count from 1."""
    return "\x1b[<%d;%d;%d%s" % (b, x, y, "m" if rel else "M")


RECORD = ["alpha one two three four five six seven eight nine ten",
          "bravo one two three four five six seven eight nine ten",
          "charlie one two three four five six seven eight nine ten",
          "delta one two three four five six seven eight nine ten",
          "echo one two three four five six seven eight nine ten"]
TABBED = ["tab\tin the middle", "second line", "third line"]


def say(s=""):
    print(s)


def row(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        say("  [PASS] " + name)
    else:
        failed += 1
        say("  [FAIL] " + name + ("   <- " + detail if detail else ""))


def bail(msg):
    say("sandbox-sed-edit: CANNOT RUN - " + msg)
    sys.exit(2)


def sess(box, *cmds):
    """A plain scripted session through a pipe, for setting up and reading back (no keys)."""
    say("    > " + " | ".join(cmds))
    p = subprocess.run([sys.executable, TOOL, box, "sess", os.path.join(box, "user_accounts")] + list(cmds),
                       capture_output=True, text=True, errors="replace", timeout=600)
    out = ANSI.sub("", p.stdout + p.stderr)
    return out.split(":TERM 200,9999", 1)[-1]


class Term:
    """One run of a command on a pseudo-terminal: type to it, read its screen."""

    def __init__(self, box, cmd, cols=120, rows=36):          # SED is 120 by 36 always, and refuses a smaller window
        self.cols = cols
        self.rows = rows
        env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"), TERM="xterm")
        self.s = PtySession([os.path.join(box, "sys", "bin", "sd")], os.path.join(box, "user_accounts"), env, cols, rows)
        self.s.settle(1.0)
        self.s.type("TERM xterm\r")
        self.s.type("TERM %d,%d\r" % (cols, rows))
        self.s.type(cmd + "\r", idle=1.0)

    def keys(self, *chunks, idle=0.5):
        for chunk in chunks:
            self.s.type(chunk, idle=idle)
        return self.lines()

    def lines(self):
        return self.s.screen.lines()

    def end(self):
        self.s.type("\rOFF\r", idle=0.5)
        self.s.finish()


def at(e):
    """(line, column) from the status line."""
    t = "\n".join(e.lines()[-3:])
    m = re.search(r"\|\s*(\d+)\.(\d+)", t)
    return (int(m.group(1)), int(m.group(2))) if m else None


def nlines(e):
    t = "\n".join(e.lines()[-3:])
    m = re.search(r"(\d+) lines?", t)
    return int(m.group(1)) if m else None


def said(e, text):
    return any(text in l for l in e.lines()[-3:])


def rec(box, rid):
    out = sess(box, "RUN bp zzseprobe")
    m = re.search(r"(?m)^REC %s (.*)$" % re.escape(rid), out)
    if not m:
        return ["<absent>"] * 5
    return m.group(1).split("|")


def quit_asking(e):
    """Leave SED whatever state the record is in: Ctrl-Q, and Yes to 'Quit without saving?' if it asks."""
    e.keys(CTRL("q"))
    e.keys("y")
    e.end()


def part_undo(box):
    say("\n--- SED: undo and redo --------------------------------------------------------------------------------")
    e = Term(box, "SED %s r1" % F)
    base = list(e.lines())
    row("control: the record is on the screen, line 1 first, at 1.1 of 5 lines",
        base[1].startswith("alpha") and at(e) == (1, 1) and nlines(e) == 5, "\n".join(base[:3]) + " | " + repr(base[-1]))
    e.keys(UNDO)
    row("Ctrl-Z on a record nobody has changed says Nothing to undo", said(e, "Nothing to undo"), "\n".join(e.lines()[-3:]))
    row("...and the text is as it was", e.lines()[1:6] == base[1:6], "")
    e.keys(REDO)
    row("Ctrl-Y with nothing undone says Nothing to redo", said(e, "Nothing to redo"), "\n".join(e.lines()[-3:]))

    L = e.keys("ab")
    row("control: typing put ab in front of line 1", L[1].startswith("abalpha") and at(e) == (1, 3), repr(L[1]) + " " + repr(at(e)))
    L = e.keys(UNDO)
    row("Ctrl-Z takes the whole run of typing out in one step", L[1] == base[1], repr(L[1]))
    row("...and the cursor is back where the typing began, 1.1", at(e) == (1, 1), repr(at(e)))
    L = e.keys(REDO)
    row("Ctrl-Y puts it back, and the cursor after it", L[1].startswith("abalpha") and at(e) == (1, 3), repr(L[1]) + " " + repr(at(e)))
    e.keys(REDO)
    row("a second Ctrl-Y says Nothing to redo", said(e, "Nothing to redo"), "\n".join(e.lines()[-3:]))
    L = e.keys(UNDO)
    row("Ctrl-Z again takes it out", L[1] == base[1], repr(L[1]))
    e.keys(UNDO)
    row("...and there is nothing left to undo", said(e, "Nothing to undo"), "\n".join(e.lines()[-3:]))

    say("\n--- SED: one step for each run of typing, on each line ------------------------------------------------")
    e.keys("ab", DOWN, CTRL("a"), "cd")
    L = e.lines()
    row("control: ab on line 1 and cd on line 2", L[1].startswith("abalpha") and L[2].startswith("cdbravo"), repr(L[1:3]))
    L = e.keys(UNDO)
    row("Ctrl-Z takes out the cd only: line 2 is as it was, line 1 still has ab", L[2] == base[2] and L[1].startswith("abalpha"), repr(L[1:3]))
    row("...with the cursor back on line 2", at(e) == (2, 1), repr(at(e)))
    L = e.keys(UNDO)
    row("the next Ctrl-Z takes out the ab", L[1] == base[1] and L[2] == base[2], repr(L[1:3]))
    L = e.keys(REDO, REDO)
    row("two Ctrl-Y put both back", L[1].startswith("abalpha") and L[2].startswith("cdbravo"), repr(L[1:3]))
    e.keys(UNDO, UNDO)

    say("\n--- SED: a new change after an undo ends the redo -----------------------------------------------------")
    e.keys("ab")
    e.keys(UNDO)
    L = e.keys("xy")
    row("control: after the undo, typing xy goes in at 1.1", L[1].startswith("xyalpha"), repr(L[1]))
    e.keys(REDO)
    row("Ctrl-Y now says Nothing to redo: the undone ab is gone", said(e, "Nothing to redo") and e.lines()[1].startswith("xyalpha"), "\n".join(e.lines()[-3:]))
    e.keys(UNDO)
    row("and Ctrl-Z takes out the xy", e.lines()[1] == base[1], repr(e.lines()[1]))
    quit_asking(e)

    say("\n--- SED: lines, regions, deletes ----------------------------------------------------------------------")
    e = Term(box, "SED %s r1" % F)
    L = e.keys(CTRL("e"), RET)
    row("control: End then Return splits nothing and adds a line: 6 lines, cursor on 2.1", nlines(e) == 6 and at(e) == (2, 1), repr(at(e)) + " " + repr(nlines(e)))
    L = e.keys(UNDO)
    row("Ctrl-Z takes the new line away: 5 lines, line 2 is bravo again", nlines(e) == 5 and L[2] == base[2], repr(L[1:4]) + " " + repr(nlines(e)))
    e.keys(REDO)
    row("Ctrl-Y makes it again: 6 lines", nlines(e) == 6, repr(nlines(e)))
    e.keys(UNDO)
    L = e.keys(CTRL("a"), CTRL("k"))
    row("control: Home, Ctrl-K kills the whole of line 1", L[1].strip() == "" or not L[1].startswith("alpha"), repr(L[1]))
    L = e.keys(UNDO)
    row("Ctrl-Z gives the line back", L[1] == base[1], repr(L[1]))
    L = e.keys(CTRL("a"), ESC + ".", CTRL("e"), CTRL("x"), idle=0.8)
    row("control: Home, mark, End, Ctrl-X cuts line 1's text", not L[1].startswith("alpha"), repr(L[1]))
    L = e.keys(UNDO)
    row("Ctrl-Z puts the cut text back", L[1] == base[1], repr(L[1]))
    L = e.keys(REDO)
    row("Ctrl-Y cuts it again", not L[1].startswith("alpha"), repr(L[1]))
    L = e.keys(UNDO, CTRL("e"), BS, BS)
    row("control: End, then two backspaces take the last two characters off line 1", L[1] == base[1][:-2], repr(L[1]))
    L = e.keys(UNDO)
    row("Ctrl-Z puts both back in one step", L[1] == base[1], repr(L[1]))
    L = e.keys(CTRL("a"), ESC + ".", CTRL("e"), CTRL("c"), CTRL("v"), idle=0.8)
    row("control: Home, mark, End, copy and paste make line 1 twice as long (the cursor is 1.%d)" % (2 * len(RECORD[0]) + 1),
        at(e) == (1, 2 * len(RECORD[0]) + 1), repr(at(e)))
    L = e.keys(UNDO)
    row("Ctrl-Z takes the pasted text out", L[1] == base[1], repr(L[1]))
    quit_asking(e)

    say("\n--- SED: the menu, and the keys it shows -----------------------------------------------------------------")
    e = Term(box, "SED %s r1" % F)
    L = e.keys(F10, RIGHT)
    row("Edit > Undo shows Ctrl-Z and Edit > Redo shows Ctrl-Y, at the top of the menu",
        any("Undo" in l and "Ctrl-Z" in l for l in L[1:6]) and any("Redo" in l and "Ctrl-Y" in l for l in L[1:6]), "\n".join(L[:8]))
    e.keys(ESC, idle=0.9)
    e.keys("ab")
    L = e.keys(F10, RIGHT)
    L = e.keys("u", idle=0.9)
    row("Edit > Undo, chosen with u, takes the typing out", L[1] == base[1] and not any("Redo" in l for l in L[1:6]), repr(L[1]))
    L = e.keys(F10, RIGHT, "e", idle=0.9)
    row("Edit > Redo, chosen with e, puts it back", L[1].startswith("abalpha"), repr(L[1]))
    e.keys(UNDO)

    say("\n--- SED: undo changes the screen, not the file; saving writes what is on the screen --------------------")
    row("control: the record on disk is as written", rec(box, "r1") == RECORD, repr(rec(box, "r1")))
    e.keys("ab", CTRL("s"))
    row("control: Ctrl-S wrote ab to disk", rec(box, "r1")[0] == "ab" + RECORD[0], repr(rec(box, "r1")[:1]))
    e.keys(UNDO)
    row("Ctrl-Z after a save takes the typing out of the screen", e.lines()[1] == base[1], repr(e.lines()[1]))
    row("...and the disk still holds ab until the record is saved again", rec(box, "r1")[0] == "ab" + RECORD[0], repr(rec(box, "r1")[:1]))
    e.keys(CTRL("s"))
    row("Ctrl-S now writes the undone text", rec(box, "r1") == RECORD, repr(rec(box, "r1")))
    e.keys(CTRL("q"))
    e.end()

    say("\n--- SED: a command from the menu is a step of its own -------------------------------------------------")
    e = Term(box, "SED %s r2" % F)
    L = e.lines()
    e.keys(F10, RIGHT, RIGHT, RIGHT, RIGHT, RIGHT, "x", idle=1.0)
    e.keys(CTRL("s"))
    row("control: Tools > Expand tabs replaced the tab character: the record on disk has none", "\t" not in rec(box, "r2")[0], repr(rec(box, "r2")[:1]))
    e.keys(UNDO)
    e.keys(CTRL("s"))
    row("Ctrl-Z after it brings the tab back (saved again, the record on disk has it)", "\t" in rec(box, "r2")[0], repr(rec(box, "r2")[:1]))
    e.keys(CTRL("q"))
    e.end()


def part_mouse(box):
    say("\n--- SED: the mouse ------------------------------------------------------------------------------------")
    e = Term(box, "SED %s r1" % F)
    base = list(e.lines())
    raw = e.s.raw.decode("latin-1")
    row("SED asks the terminal for mouse reports while it waits for a key: ESC [ ? 1000 h and 1006 h were sent",
        "\x1b[?1000h" in raw and "\x1b[?1006h" in raw, repr(raw[-200:]))
    L = e.keys(click(10, 4))
    row("a click on the text puts the cursor there: line 3, column 10", at(e) == (3, 10), repr(at(e)))
    row("...and nothing was typed into the record (the report is not text)",
        all(e.lines()[i + 1] == base[i + 1] for i in range(5)) and "0;10" not in "\n".join(e.lines()), "\n".join(e.lines()[:6]))
    L = e.keys(click(500, 2))
    row("a click far to the right of a line puts the cursor at its end: line 1, one past the last character",
        at(e) == (1, len(RECORD[0]) + 1), repr(at(e)))
    L = e.keys(click(3, 20))
    row("a click below the last line (in the blank rows) puts the cursor on the last line", at(e)[0] in (5, 6), repr(at(e)))
    e.keys(click(4, 3, b=32), click(4, 3, rel=True))
    row("a drag report and a release change nothing", at(e)[0] in (5, 6), repr(at(e)))
    e.keys(click(1, 2))
    L = e.keys(click(1, 2, b=65))
    row("the wheel down moves the cursor three lines: 1 to 4", at(e)[0] == 4, repr(at(e)))
    L = e.keys(click(1, 2, b=64))
    row("the wheel up moves it three back: 4 to 1", at(e)[0] == 1, repr(at(e)))
    row("control: the bar has no menu open", not any("Save as" in l for l in e.lines()[1:12]), "")

    L = e.keys(click(8, 1))
    row("a click on Edit in the bar opens the Edit menu (the first line of it is Undo, with Ctrl-Z)",
        any("Undo" in l and "Ctrl-Z" in l for l in L[1:6]) and not any("Save as" in l for l in L[1:12]), "\n".join(L[:8]))
    ki = [i for i, l in enumerate(L) if "Kill line" in l]
    if ki:
        xk = L[ki[0]].index("Kill line")
        L = e.keys(click(xk + 2, ki[0] + 1), idle=0.9)
        row("a click on an item of the open menu chooses it: Kill line takes the rest of line 1 away", not L[1].startswith("alpha") and not any("Kill line" in l for l in L[1:25]),
            "\n".join(L[:6]))
    else:
        row("the Edit menu shows a Kill line item to click", False, "\n".join(L[:25]))
    e.keys(UNDO)
    L = e.keys(click(3, 1))
    row("a click on File opens the File menu", any("Save as" in l for l in L[1:12]), "\n".join(L[:8]))
    L = e.keys(click(40, 15), idle=0.9)
    row("a click outside the menu closes it, and puts nothing in the text", not any("Save as" in l for l in L[1:12]) and L[1] == base[1], "\n".join(L[:8]))

    say("\n--- SED: a split window: a click in the other window goes there first -----------------------------------------")
    e.keys(click(1, 2))
    e.keys(F10, RIGHT, RIGHT, RIGHT, RIGHT, "s", idle=0.9)
    L = e.lines()
    srow = [i for i, l in enumerate(L) if i > 2 and F in l and i < 35]
    row("control: Window > Split window cuts the screen in two: the file name is on a line in the middle", bool(srow) and 10 < srow[0] < 30, repr(srow))
    L = e.keys(click(10, 21))
    row("a click in the lower window (row 21) makes it the live one and puts the cursor on its line 3", at(e) is not None and at(e)[0] == 3, repr(at(e)))
    L = e.keys(click(10, 4))
    row("a click back in the upper window (row 4) goes there and puts the cursor on line 3 of it", at(e) is not None and at(e)[0] == 3, repr(at(e)))
    e.keys(F10, RIGHT, RIGHT, RIGHT, RIGHT, "u", idle=0.9)
    row("Window > Unsplit window puts the one window back", not any(F in l for l in e.lines()[3:33]), "")

    say("\n--- SED: a prompt takes no mouse report as an answer --------------------------------------------------------")
    e.keys(click(1, 2))
    e.keys(CTRL("l"))
    e.keys(click(5, 3))                                    # a report that got to the prompt line
    L = e.keys("2", RET)
    row("a report at the Goto line prompt is not part of the answer: '2' goes to line 2", at(e) == (2, 1) and not any("0;5" in l for l in e.lines()), repr(at(e)))
    e.keys(CTRL("q"))
    row("control: the terminal was told to stop reporting when SED ended", e.s.raw.decode("latin-1").rfind("\x1b[?1000l") > e.s.raw.decode("latin-1").rfind("\x1b[?1000h"), "")
    e.end()

    say("\n--- SED: MOUSE OFF and the Tools menu ----------------------------------------------------------------------")
    e = Term(box, "SED %s r1" % F)
    L = e.keys(F10, RIGHT, RIGHT, RIGHT, RIGHT, RIGHT)
    mi = [i for i, l in enumerate(L) if "Mouse" in l]
    row("Tools > Mouse is on the menu, and checked: it is on", bool(mi) and "*" in L[mi[0]].split("Mouse")[0], "\n".join(L[:20]))
    e.keys(ESC, idle=0.9)
    e.keys(ESC + "x")
    e.keys("mouse off", RET)
    n0 = len(e.s.raw)
    e.keys("a")
    L = e.keys(F10, RIGHT, RIGHT, RIGHT, RIGHT, RIGHT)
    mi = [i for i, l in enumerate(L) if "Mouse" in l]
    row("after MOUSE OFF the Tools menu item is not checked", bool(mi) and "*" not in L[mi[0]].split("Mouse")[0], "\n".join(L[:20]))
    e.keys(ESC, idle=0.9)
    seen = e.s.raw[n0:].decode("latin-1")
    row("...and SED no longer asks for reports while it waits (no ESC [ ? 1000 h after the command)", "\x1b[?1000h" not in seen, repr(seen[-120:]))
    p0 = at(e)
    L = e.keys(click(10, 4))
    row("...so a report that reaches it anyway moves nothing, and is not typed", at(e) == p0 and "0;10" not in "\n".join(e.lines()), repr(p0) + " " + repr(at(e)))
    e.keys(ESC + "x")
    e.keys("mouse", RET)
    L = e.keys(click(10, 4))
    row("MOUSE with no word turns it on again, and a click moves the cursor: line 3", at(e)[0] == 3, repr(at(e)))
    e.keys(ESC + "x")
    e.keys("mouse sideways", RET)
    row("MOUSE with another word says what it takes", said(e, "MOUSE takes ON or OFF"), "\n".join(e.lines()[-3:]))
    quit_asking(e)

    say("\n--- SED: the option NO.MOUSE in &sed.options& -------------------------------------------------------------")
    out = sess(box, "BASIC bp zzseopt", "RUN bp zzseopt")
    row("setup: the option record was written", "OPT DONE" in out, out[-300:])
    e = Term(box, "SED %s r1" % F)
    raw = e.s.raw.decode("latin-1")
    row("NO.MOUSE: SED never asks the terminal for reports", "\x1b[?1000h" not in raw, repr(raw[-120:]))
    L = e.keys(F10, RIGHT, RIGHT, RIGHT, RIGHT, RIGHT)
    mi = [i for i, l in enumerate(L) if "Mouse" in l]
    row("...and the Tools menu shows Mouse unchecked", bool(mi) and "*" not in L[mi[0]].split("Mouse")[0][-3:], "\n".join(L[:20]))
    e.keys(ESC, idle=0.9)
    quit_asking(e)
    sess(box, "RUN bp zzseopt0")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-sed-edit.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-sed-edit: sandbox %s" % box)
    say("sandbox-sed-edit: tree    %s" % os.path.dirname(HERE))
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-sed-edit: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    fixture = """   execute 'DELETE.FILE %(f)s' capturing j0
   execute 'CREATE.FILE %(f)s' capturing j1
   open '%(f)s' to f else stop 'no file'
   write %(rec)s on f, 'r1'
   write %(tab)s on f, 'r2'
   crt 'FIXTURE DONE'
end
""" % {"f": F, "rec": " : @fm : ".join("'%s'" % x for x in RECORD),
       "tab": " : @fm : ".join(("'tab' : char(9) : 'in the middle'" if i == 0 else "'%s'" % x) for i, x in enumerate(TABBED))}
    probe = """   open '%(f)s' to f else stop 'no file'
   for n = 1 to 2
      id = 'r' : n
      read r from f, id then
         crt 'REC ' : id : ' ' : convert(@fm, '|', r)
      end else
         crt 'REC ' : id : ' <none>'
      end
   next n
end
""" % {"f": F}
    opt = """   write 'X' : @fm : 'NO.MOUSE' on @voc, '&sed.options&'
   crt 'OPT DONE'
end
"""
    opt0 = """   delete @voc, '&sed.options&'
   crt 'OPT GONE'
end
"""
    progs = {"zzsefix": fixture, "zzseprobe": probe, "zzseopt": opt, "zzseopt0": opt0}
    for nm, body in progs.items():
        with open(os.path.join(sysd, "bp", nm), "w") as fh:
            fh.write(body)
    try:
        say("\n--- fixture --------------------------------------------------------------------------------------")
        out = sess(box, *(["BASIC bp %s" % n for n in progs] + ["RUN bp zzsefix"]))
        row("setup: the programs compiled and the fixture file was made",
            len(re.findall(r"(?m)^Compiled 1 program\(s\) with no errors", out)) == len(progs) and "FIXTURE DONE" in out, out[-900:])
        if "FIXTURE DONE" not in out:
            bail("the fixture was not made:\n" + out[-800:])
        row("setup: control - the record is as written", rec(box, "r1") == RECORD, repr(rec(box, "r1")))
        if "--only=mouse" not in sys.argv:
            part_undo(box)
        if "--only=undo" not in sys.argv:
            part_mouse(box)
    finally:
        say("\n--- cleanup ---------------------------------------------------------------------------------------")
        sess(box, "RUN bp zzseopt0", "DELETE.FILE %s" % F)
        for nm in progs:
            for d in ("bp", "bp.out"):
                pth = os.path.join(sysd, d, nm)
                if os.path.exists(pth):
                    os.remove(pth)

    say("\nsandbox-sed-edit: %d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        bail("no row ran - a broken test, not a pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
