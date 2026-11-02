#!/usr/bin/env python3
#
# sandbox-idebrk.py - the IDE's breakpoints handed to the debugger (S.98 H2), on a PSEUDO-TERMINAL at 140 by 43 on a private SD.  No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-idebrk.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent).  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# THE INSTRUMENT.  The editor's mark is read from the IDE's screen (the gutter's first cell, column 29, on the row of the line); where the debugger stopped is read from the DEBUGGER'S
# OWN SCREEN (its source pane: > the line about to run, * a line with a breakpoint, `sandbox-dbgui.py`'s srcrow); what came back is read from the IDE's gutter after the debugger
# ended.  The program's records are written to the disk by this suite and the IDE saves before it compiles, so the disk is the text the marks are counted in.
#
#   B0   setup: the programs and the IDE on one of them; a mark cell in the gutter and nothing in it
#   B1   Shift-F7 sets and clears the cursor line's mark (11719 / 11786); a click in the gutter sets one; a tab that is not a program says 11788 (the control)
#   B2   an inserted line moves the mark down with its line
#   B3   F7 with marks runs to the first mark and stops there (no > above it); BRK in the debugger, then Q: the IDE shows the debugger's list as its marks
#   B4   Build / Debug from the first line stops at the first statement with the marks set (11715)
#   B5   marks on lines that begin no statement: nothing set, the run stops at the first statement and says so (11716), and the marks do not come back
#   B6   twenty marks, and the twenty-first is refused (11787)
#   B7   a program that ends before its mark: the IDE is back with the mark kept
#   B8   the control: no marks, F7 stops at the first statement as it always did
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
spec = importlib.util.spec_from_file_location("sandbox_ide_for_idebrk", os.path.join(HERE, "sandbox-ide.py"))
ide = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ide)
Ide, say, bail, RET, F7, DOWN, UP = ide.Ide, ide.say, ide.bail, ide.RET, ide.F7, ide.DOWN, ide.UP

SHIFT_F7 = "\x1b[18;2~"          # xterm's kf19
F10, RIGHT = ide.F10, ide.RIGHT
# the Build menu (message 11228) is the fourth: F10 opens File, Right three times; its seventh entry is Debug from the first line, its ninth Clear breakpoints
DEBUG1 = (F10, RIGHT * 3, DOWN * 6, RET)
BPCLEAR = (F10, RIGHT * 3, DOWN * 8, RET)
CTRL_HOME = "\x1b[1;5H"
MARKCOL = 29                      # the gutter's first cell: the editor's border is column 28
SRC_LAST = 32                     # the debugger's source pane: rows 1 to 32, its mark in column 0, the Autos pane from column 92
AUTOX = 92
DBG_KEYS = "F1 help  F2 abort  F3 stop  F4 screen  F5 run  F7 step  F8 line  ^F7 parent  ^F8 program"
RUN = "%05d" % (os.getpid() % 100000)
P, L, E, C = ("zzk%s%s" % (RUN, c) for c in "plec")

PROG = ["crt 'L1'", "x = 1", "* a comment line", "crt 'L4'", "x = 2", "end"]
LONG = ["x = %d" % i for i in range(1, 25)] + ["end"]
ENDS = ["crt 'E1'", "stop", "crt 'E3'", "end"]
CTRL = ["crt 'C1'", "x = 1", "end"]


def row(rid, name, ok, detail=""):
    ide.row("%s %s" % (rid, name), ok, detail)


def put(box, rid, lines):
    with open(os.path.join(box, "sys", "bp", rid), "w") as f:
        f.write("\n".join(lines))


def mark(e, n, top=1):
    """the editor's mark cell of line n (the editor shows line top on row 3)"""
    r = 3 + n - top
    l = e.lines()[r]
    return l[MARKCOL] if len(l) > MARKCOL else " "


def marked(e, count):
    return [n for n in range(1, count + 1) if mark(e, n) == "*"]


def in_debugger(L):
    return any(l.rstrip() == DBG_KEYS for l in L[-3:])


def srcrow(L, n):
    for r in range(1, SRC_LAST + 1):
        if r < len(L) and re.match(r"^[ *>]\s*%d: " % n, L[r][:AUTOX - 1]):
            return r
    return None


def dmark(L, n):
    r = srcrow(L, n)
    return L[r][0] if r is not None else None


def arrows(L):
    """the source lines the debugger marks with > (the line about to run when it has no breakpoint)"""
    out = []
    for r in range(1, SRC_LAST + 1):
        m = re.match(r"^>\s*(\d+): ", L[r][:AUTOX - 1]) if r < len(L) else None
        if m:
            out.append(int(m.group(1)))
    return out


def quit_debugger(e):
    """Q at the debugger's command line, then Return at the IDE's pause; True when the IDE is back"""
    e.keys("q", RET)
    e.s.settle(1.0)
    paused = "Press Return to go back to the IDE" in e.text()
    e.keys(RET)
    e.s.settle(1.0)
    return paused and re.search(r"File\s+Go\s+Search", e.lines()[0]) is not None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-idebrk.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = ide.subprocess.run([sys.executable, ide.TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-idebrk: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox" % box)
    ide.subprocess.run([sys.executable, ide.TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)
    try:
        for rid, lines in ((P, PROG), (L, LONG), (E, ENDS), (C, CTRL)):
            put(box, rid, lines)

        say("\n--- B0: setup")
        e = Ide(box, "IDE bp %s" % P)
        e.s.settle(1.0)
        if "crt 'L1'" not in e.text():
            bail("the IDE did not open %s:\n%s" % (P, e.text()[:600]))
        row("B0", "the program is open, its gutter has a mark cell (the line number moved one cell right) and no line is marked",
            re.match(r"^\s*1 crt 'L1'", e.lines()[3][MARKCOL + 1:]) is not None and marked(e, 6) == [], repr(e.lines()[3][26:60]))

        say("\n--- B1: Shift-F7, a click, and a tab that is not a program")
        e.keys(SHIFT_F7)
        st = e.quiet()
        row("B1a", "Shift-F7 marks the cursor's line 1 and says so (11719)", marked(e, 6) == [1] and "Breakpoint set at line 1" in e.status(), repr((marked(e, 6), e.status())))
        e.keys(SHIFT_F7)
        e.quiet()
        row("B1b", "Shift-F7 again clears it (11786)", marked(e, 6) == [] and "Breakpoint cleared at line 1" in e.status(), repr((marked(e, 6), e.status())))
        e.keys(ide.click(MARKCOL, 3 + 4 - 1))
        e.quiet()
        row("B1c", "a click in the gutter of line 4 marks line 4", marked(e, 6) == [4], repr((marked(e, 6), e.lines()[6][26:50])))
        e.end()
        u = Ide(box, "IDE voc date")          # a VOC record is a data tab (the empty Untitled tab is a program tab: it is marked, as its text may be saved as one)
        u.s.settle(1.0)
        u.keys(SHIFT_F7)
        u.quiet()
        row("B1d", "in a tab that is not a program (a VOC record) Shift-F7 says breakpoints are for programs only (11788) and marks nothing (the control)",
            "Breakpoints can be set in a program only" in u.status() and "*" not in "".join(l[MARKCOL:MARKCOL + 1] for l in u.lines()[3:8]), u.status())
        u.end()

        say("\n--- B2: the mark moves with its line")
        e = Ide(box, "IDE bp %s" % P)
        e.s.settle(1.0)
        e.keys(DOWN * 3, SHIFT_F7, CTRL_HOME, RET)
        e.quiet()
        row("B2", "line 4 marked, then a line inserted at the top: the mark is on line 5, the same text", marked(e, 7) == [5] and "crt 'L4'" in e.lines()[3 + 5 - 1], repr((marked(e, 7), e.lines()[7][26:60])))

        say("\n--- B3: F7 runs to the mark; the debugger's list comes back")
        L3 = e.keys(F7)
        e.s.settle(2.0)
        L3 = e.lines()
        row("B3a", "F7 gives the terminal to the debugger, which stopped ON line 5 (marked *), with no line above it marked > (it did not stop at the first statement)",
            in_debugger(L3) and dmark(L3, 5) == "*" and arrows(L3) == [], "\n".join(L3[:9]) + "\n" + L3[-1])
        e.keys("brk 6", RET)
        e.s.settle(1.0)
        L3 = e.lines()
        row("B3b", "BRK 6 in the debugger marks line 6", dmark(L3, 6) == "*", "\n".join(L3[:9]))
        back = quit_debugger(e)
        e.quiet()
        row("B3c", "Q, Return: the IDE is back and its marks are the debugger's list, lines 5 and 6", back and marked(e, 7) == [5, 6], repr((back, marked(e, 7))))

        say("\n--- B4: Debug from the first line")
        e.keys(*DEBUG1)
        e.s.settle(2.0)
        L4 = e.lines()
        row("B4", "Build / Debug from the first line stops at line 2, the first statement (>), with lines 5 and 6 marked and 'Breakpoints set from the editor's marks: 2' said",
            in_debugger(L4) and arrows(L4) == [2] and dmark(L4, 5) == "*" and dmark(L4, 6) == "*" and "Breakpoints set from the editor's marks: 2" in "\n".join(L4),
            "\n".join(L4[:10]) + "\n" + "\n".join(L4[33:40]))
        quit_debugger(e)

        say("\n--- B5: marks on lines that begin no statement")
        e.keys(*BPCLEAR)
        e.quiet()
        cleared = marked(e, 7) == []
        e.keys(CTRL_HOME, SHIFT_F7, DOWN * 3, SHIFT_F7)          # line 1 (now blank) and line 4 (the comment)
        e.quiet()
        before = marked(e, 7)
        e.keys(F7)
        e.s.settle(2.0)
        L5 = e.lines()
        row("B5a", "Clear breakpoints empties the gutter, and lines 1 and 4 are then marked", cleared and before == [1, 4], repr((cleared, before)))
        row("B5b", "F7: no breakpoint set; the debugger stops at the first statement (line 2) and names the two lines (11716)",
            in_debugger(L5) and arrows(L5) == [2] and dmark(L5, 1) != "*" and dmark(L5, 4) != "*" and re.search(r"No breakpoint was set on these marked lines .*: 1 4", "\n".join(L5)) is not None,
            "\n".join(L5[:8]) + "\n" + "\n".join(L5[33:40]))
        back = quit_debugger(e)
        e.quiet()
        row("B5c", "back in the IDE the two marks are gone (only lines the debugger set come back)", back and marked(e, 7) == [], repr((back, marked(e, 7))))
        e.keys(CTRL_HOME, SHIFT_F7, DOWN * 5, SHIFT_F7)           # line 1 (blank: no statement) and line 6 (x = 2: a statement)
        e.quiet()
        two = marked(e, 7)
        e.keys(F7)
        e.s.settle(2.0)
        L5 = e.lines()
        row("B5d", "one good mark and one bad: the run goes straight on and stops ON line 6 (marked *, no >), and says nothing yet",
            two == [1, 6] and in_debugger(L5) and dmark(L5, 6) == "*" and arrows(L5) == [] and "marked lines" not in "\n".join(L5), repr((two, arrows(L5), dmark(L5, 6))))
        back = quit_debugger(e)
        e.quiet()
        row("B5e", "back in the IDE the status line names the line that could not be set (11716), and only line 6 is still marked",
            back and marked(e, 7) == [6] and re.search(r"No breakpoint was set on these marked lines .*: 1$", e.status().rstrip()) is not None, repr((back, marked(e, 7), e.status())))
        e.end()

        say("\n--- B6: twenty marks")
        e = Ide(box, "IDE bp %s" % L)
        e.s.settle(1.0)
        for i in range(20):
            e.keys(SHIFT_F7, DOWN)
        e.quiet()
        twenty = marked(e, 25)
        e.keys(SHIFT_F7)
        e.quiet()
        row("B6", "twenty lines marked, and the twenty-first is refused (11787) and not marked",
            twenty == list(range(1, 21)) and marked(e, 25) == list(range(1, 21)) and "A program can have only 20 breakpoints" in e.status(), repr((twenty, marked(e, 25), e.status())))
        e.end()

        say("\n--- B7: a program that ends before its mark")
        e = Ide(box, "IDE bp %s" % E)
        e.s.settle(1.0)
        e.keys(DOWN * 2, SHIFT_F7)
        e.quiet()
        e.keys(F7)
        e.s.settle(2.0)
        T7 = e.text()
        paused = "Press Return to go back to the IDE" in T7
        e.keys(RET)
        e.quiet()
        row("B7", "the run goes on and the program stops at line 2 without ever stopping in the debugger; Return gives the IDE back with line 3 still marked",
            paused and not in_debugger(e.lines()) and marked(e, 4) == [3], repr((paused, marked(e, 4), T7[-300:])))
        e.end()

        say("\n--- B8: the control, no marks")
        e = Ide(box, "IDE bp %s" % C)
        e.s.settle(1.0)
        e.keys(F7)
        e.s.settle(2.0)
        L8 = e.lines()
        row("B8", "F7 with no marks stops at line 1, the first statement (>), and says nothing about the editor's marks",
            in_debugger(L8) and arrows(L8) == [1] and "editor's marks" not in "\n".join(L8) and "marked lines" not in "\n".join(L8), "\n".join(L8[:6]))
        back = quit_debugger(e)
        row("B8b", "Q, Return: the IDE is back with no mark", back and marked(e, 3) == [], repr((back, marked(e, 3))))
        e.end()
    finally:
        ide.subprocess.run([sys.executable, ide.TOOL, box, "stop"], capture_output=True, text=True, errors="replace", timeout=120)
    say("\nsandbox-idebrk: %d passed, %d failed" % (ide.passed, ide.failed))
    return 0 if ide.failed == 0 and ide.passed > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
