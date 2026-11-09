#!/usr/bin/env python3
#
# sandbox-dbgui.py - the debugger's full-screen display, on the screen library, on a pseudo-terminal.  No install,
# no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-dbgui.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or
# absent).  Exit 0 every row passed, 1 a row failed, 2 it could not run.  Only one private SD can exist on a machine
# (shared memory keys 0x53434c91/92): stop the sandbox afterwards with sandbox-fromtree.py <dir> stop.
#
# START-HISTORY:
# 13 Oct 26 dm  Written when the debugger's drawing moved onto the screen library (owner: "use the TUI on ced and
#               debugger").  The debugger's own command-by-command suite is sandbox-dbgcoll.py, which has no terminal and
#               so never reaches the full-screen code.
# 18 Oct 26 dm  The window is 140 by 42 (the full-screen display is laid out for it and uses line mode below it, plan-terminal-140x42.md
#               phase 3): the size of Term(), and every row number that follows from it (the command line is row 41, the data area
#               rows 36 to 40).  The line mode, the shrink and the cursor lock are sandbox-ide-small.py's.
# 1 Nov 26 dm   S.98 H1, the debugger in the IDE's style.  The window is 140 by 43 and the display has the toolkit's frame: the bar with
#               the app name and the audience at the right of row 0; the source (rows 1 to 32) with a gutter (* a breakpoint, > the line
#               about to run) and, at its right from column 92, the Autos pane; the rule above the messages (row 33); the messages (rows 34
#               to 38); the command line (row 39); the status line (40), the border (41) and the function-key row (42).  Rewritten row by row
#               for those places; new sections: the foot and the gutter, the Autos pane (its order and its refresh), and the site's
#               theme with the colours of SD BASIC (SCREENTHEME=blue written to the sandbox's sd.conf for that section only).
# END-HISTORY
#
# HOW IT DRIVES THE DEBUGGER.  A program compiled with BASIC ... DEBUGGING and holding a DEBUG statement is run on a
# pseudo-terminal (ptydrive.py) and stops at the debugger, which on a terminal with a scrolling region (xterm's)
# takes the whole screen.  The screen is read from the emulator in termscreen.py: its text and the colours of its cells.
# Each row that turns something on has a control row; a program that never reached the debugger makes its rows fail, not pass.

import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ptydrive import PtySession  # noqa: E402

TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
PROG = "zzdu" + "%05d" % (os.getpid() % 100000)
PROG2 = PROG + "b"
passed = failed = 0
RET, F1 = "\r", "\x1bOP"
F2, ESC, CTRL_Q = "\x1bOQ", "\x1b", "\x11"            # 9 Nov 26 (S.186): F2 is Find an action and Ctrl-Q stops and leaves, as on every page

COLS, ROWS = 140, 43
CMD, STATUS, BORDER, KEYS = 39, 40, 41, 42           # the command line and the three rows of the foot
RULE, DATA0, DATA1 = 33, 34, 38                      # the rule above the messages, and the messages (five rows)
SRC_LAST = 32                                        # the last row of the source and of the Autos pane
AUTOX = 92                                           # the Autos pane's first column; the rule between it and the source is column 91
KEYTEXT = "F1 help  F2 find  F3 stop  F4 screen  F5 refresh  F7 step  F8 line  F9 run  F10 menu  ^F7 parent  ^F8 program"     # S.179, 8 Nov 26: F5 refresh, F9 run, F10 the menu bar

SOURCE = """   s = 'plain' ; t = 'a':char(9):'b'
   n = 5
   debug
   crt 'AFTER-ONE'
   crt 'AFTER-TWO'
end
"""

# the Autos pane's order: the names on the line about to run first, then those of the line the debugger last stopped at, then the rest
SOURCE2 = """   a = 1 ; b = 'text' ; c = 3
   debug
   crt c + a
   debug
   crt b
end
"""


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
    say("sandbox-dbgui: CANNOT RUN - " + msg)
    sys.exit(2)


def sess(box, *cmds):
    say("    > " + " | ".join(cmds))
    p = subprocess.run([sys.executable, TOOL, box, "sess", os.path.join(box, "user_accounts")] + list(cmds),
                       capture_output=True, text=True, errors="replace", timeout=600)
    out = ANSI.sub("", p.stdout + p.stderr)
    return out.split(":TERM 200,9999", 1)[-1]


class Term:
    def __init__(self, box, cmd, cols=COLS, rows=ROWS):
        env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"), TERM="xterm")
        self.s = PtySession([os.path.join(box, "sys", "bin", "sd")], os.path.join(box, "user_accounts"), env, cols, rows)
        self.s.settle(1.5)
        self.s.type("TERM xterm\r", idle=0.8)
        self.s.type("TERM %d,%d\r" % (cols, rows), idle=0.8)
        self.s.type(cmd + "\r", idle=2.5)

    def keys(self, *chunks, idle=0.6):
        for c in chunks:
            self.s.type(c, idle=idle)
        return self.lines()

    def lines(self):
        return self.s.screen.lines()

    def style(self, r, c):
        return self.s.screen.style(r, c)

    def end(self):
        self.s.type("\rOFF\r", idle=0.5)
        self.s.finish()


def where(L, text, first=0, last=None):
    """(row, column) of the first row from first to last (default: all) that holds text"""
    for r, l in enumerate(L):
        if r < first or (last is not None and r > last):
            continue
        c = l.find(text)
        if c >= 0:
            return r, c
    return None


def srcrow(L, n):
    """The row of the source pane that shows line n: a mark, a blank, the number and a colon"""
    for r in range(1, SRC_LAST + 1):
        if re.match(r"^[ *>]\s*%d: " % n, L[r][:AUTOX - 1]):
            return r
    return None


def autos(L):
    """The Autos pane's rows under its title (the right-hand part of rows 2 to 32, cut at the end of the text)"""
    return [L[r][AUTOX:].strip() for r in range(2, SRC_LAST + 1)]


def isrule(line):
    return len(line.rstrip()) >= 100 and set(line.rstrip()) <= set("-+")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-dbgui.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-dbgui: sandbox %s" % box)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-dbgui: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    conf = os.path.join(box, "sd.conf")
    with open(conf) as fh:
        original_conf = fh.read()
    if re.search(r"(?m)^SCREENTHEME=", original_conf):
        bail("the sandbox's sd.conf already has a SCREENTHEME line, so the classic rows cannot be measured")
    for nm, body in ((PROG, SOURCE), (PROG2, SOURCE2)):
        with open(os.path.join(sysd, "bp", nm), "w") as fh:
            fh.write(body)
    try:
        say("\n--- setup -------------------------------------------------------------------------------------------")
        out = sess(box, "BASIC bp %s DEBUGGING" % PROG, "BASIC bp %s DEBUGGING" % PROG2)
        row("setup: both programs compiled in debug mode", out.count("with no errors") == 2, out[-300:])

        say("\n--- the screen when the debugger takes over (the classic theme: the sandbox's sd.conf names no site theme) ---")
        t = Term(box, "RUN bp %s" % PROG)
        L = t.lines()
        r1 = srcrow(L, 1)
        row("setup: the debugger is up, full screen: the source is on the screen with its line numbers",
            r1 is not None and "s = 'plain'" in L[r1], "\n".join(L[:8]))
        row("S.180: the menu bar's titles (Run View Help) are at the left of the top row, and the title (the program's pathname, cut to the screen: the line number may be off the end) after them",
            L[0].startswith(" Run  View  Help ") and L[0][len(" Run  View  Help "):].startswith("/"), repr(L[0]))
        fg0, bg0, fl0 = t.style(0, 2)
        row("the title bar is black on white (the 'bar' style of the classic theme the debugger uses while it is up)",
            (fg0, bg0) == (0, 7), repr(t.style(0, 2)))
        row("the app and the audience are at the right end of the bar, as the pages have them: 'debugger' and who is signed on",
            re.search(r"debugger  \S+$", L[0]) is not None and t.style(0, 139) == t.style(0, 2), repr(L[0][-40:]) + repr(t.style(0, 139)))
        r4 = srcrow(L, 4)
        r3 = srcrow(L, 3)
        row("the line about to run (4, the one after DEBUG) is in the highlight style (white on green); its neighbour is not",
            r4 is not None and t.style(r4, 10) != t.style(r4 - 1, 10) and t.style(r4, 10)[1] == 2, repr((r4, t.style(r4 or 0, 10), t.style((r4 or 1) - 1, 10))))
        row("the source is white on blue (the 'text' style)", r3 is not None and t.style(r3, 20)[1] == 4, repr(t.style(r3 or 0, 20)))
        row("the line numbers are in the gutter style (cyan on blue), not the text style",
            r3 is not None and t.style(r3, 2)[:2] == (6, 4), repr(t.style(r3 or 0, 2)))
        row("the gutter marks the line about to run with > and no other line", r4 is not None and L[r4][0] == ">" and all(L[r][0] != ">" for r in range(1, SRC_LAST + 1) if r != r4),
            repr([L[r][:3] for r in range(1, 8)]))
        row("the command line is on row 39, with the > prompt, in the bar style",
            L[CMD].startswith(">") and t.style(CMD, 0)[:2] == (0, 7), repr((L[CMD], t.style(CMD, 0))))

        say("\n--- the frame: the rule, the Autos pane, the foot ------------------------------------------------------")
        row("a rule (-) runs across the screen above the messages (row 33)", isrule(L[RULE]) and len(L[RULE].rstrip()) == COLS, repr(L[RULE][:30]))
        row("the rule between the source and the Autos pane is column 91, on every row of the source", all(L[r][AUTOX - 1] == "|" for r in range(1, SRC_LAST + 1)), repr([L[r][AUTOX - 2:AUTOX + 1] for r in (1, 16, 32)]))
        row("the Autos pane has its title (Autos) at the top of its column, in the header style (black on cyan)",
            L[1][AUTOX:AUTOX + 5] == "Autos" and t.style(1, AUTOX + 1)[:2] == (0, 6), repr(L[1][AUTOX:AUTOX + 8]) + repr(t.style(1, AUTOX + 1)))
        a = autos(L)
        row("the Autos pane is not empty: the locals in the order the program declares them (this line uses none of them)",
            a[:4] == ['S = "plain"', 'T = "a?b"', "N = 5", ""], repr(a[:5]))
        row("the status line (row 40) says it is the command pane and how many breakpoints there are, in reverse video",
            L[STATUS].startswith("[Command]  breakpoints 0") and "r" in t.style(STATUS, 3)[2], repr(L[STATUS][:40]) + repr(t.style(STATUS, 3)))
        row("the border (row 41) is a line across the screen", isrule(L[BORDER]) and len(L[BORDER].rstrip()) == COLS, repr(L[BORDER][:30]))
        row("the function-key row (row 42) lists the keys the debugger acts on, in the bar style",
            L[KEYS].rstrip() == KEYTEXT and t.style(KEYS, 3)[:2] == (0, 7), repr(L[KEYS][:100]) + repr(t.style(KEYS, 3)))
        row("nothing scrolled: the title is still on row 0 after the foot was drawn on the last row", L[0][len(" Run  View  Help "):].startswith("/") and srcrow(L, 1) == 1, repr(L[0][:30]))
        row("no syntax colour in the classic theme: a string in the source is in the text style (white on blue), the same as the words round it",
            r1 is not None and t.style(r1, L[r1].find("'plain'")) == t.style(r1, L[r1].find("s = ") + 0), repr((t.style(r1 or 0, L[r1 or 1].find("'plain'")), t.style(r1 or 0, L[r1 or 1].find("s = ")))))

        say("\n--- commands ------------------------------------------------------------------------------------------")
        L = t.keys("/s", RET)
        row("a variable's value appears in the data area, above the command line", any("String (5 bytes)" in l and "plain" in l for l in L[DATA0:CMD]), "\n".join(L[DATA0 - 1:CMD + 1]))
        row("...and the command typed is echoed there with its prompt", any(l.startswith(">/s") for l in L[DATA0:CMD]), "\n".join(L[DATA0 - 1:CMD + 1]))
        # 16 Oct 26: QM4 Fixes 550 (the ^ command) and 193 (WINDOW n)
        L = t.keys("/t", RET)
        row("550: CONTROL: a tab in a string is shown as ?", any('String (3 bytes): "a?b"' in l for l in L[DATA0:CMD]), "\n".join(L[DATA0 - 1:CMD + 1]))
        L = t.keys("^", RET)
        row("550: ^ says the characters are now shown as ^nnn", any("Non-printing characters are shown as ^nnn" in l for l in L[DATA0:CMD]), "\n".join(L[DATA0 - 1:CMD + 1]))
        L = t.keys("/t", RET)
        row("550: ... and the tab is shown as ^9, the length still 3", any('String (3 bytes): "a^9b"' in l for l in L[DATA0:CMD]), "\n".join(L[DATA0 - 1:CMD + 1]))
        L = t.keys("^", RET, "/t", RET)
        row("550: a second ^ puts the ? back", any('String (3 bytes): "a?b"' in l for l in L[DATA0:CMD]), "\n".join(L[DATA0 - 1:CMD + 1]))
        L = t.keys("set n=7", RET)
        a = autos(L)
        row("a command that changes a variable shows in the Autos pane at once: SET N=7 and N = 7", "N = 7" in a and "N = 5" not in a, repr(a[:5]))
        Lb = t.lines()
        row("193: CONTROL: with the usual 5 rows the rule is row 33 (a line across) and row 28 is source", isrule(Lb[RULE]) and not isrule(Lb[28]), repr((Lb[RULE][:20], Lb[28][:20])))
        L = t.keys("window 10", RET)
        row("193: WINDOW 10 makes the data area ten rows: the rule moves up to row 28, and row 33 is now one of the messages' rows",
            isrule(L[28]) and not isrule(L[RULE]) and L[RULE].strip() == "", repr((L[28][:20], L[RULE][:20])))
        row("193: ... the command line is still on row 39", L[CMD].startswith(">"), repr(L[CMD]))
        row("193: ... and the foot is where it was (status 40, border 41, keys 42)", L[STATUS].startswith("[Command]") and isrule(L[BORDER]) and L[KEYS].rstrip() == KEYTEXT, repr((L[STATUS][:20], L[KEYS][:20])))
        L = t.keys("/s", RET)
        row("193: ... and a value shows in the larger area", any("String (5 bytes)" in l and "plain" in l for l in L[29:CMD]), "\n".join(L[28:CMD + 1]))
        row("193: ... the source is still shown above it", srcrow(L, 1) == 1 and "s = 'plain'" in L[1], "\n".join(L[:4]))
        row("193: ... and the Autos pane is shorter: it ends at row 27", L[27][AUTOX - 1] == "|" and L[28][AUTOX - 1] != "|", repr((L[27][AUTOX - 2:AUTOX + 1], L[28][AUTOX - 2:AUTOX + 1])))
        L = t.keys("window 3", RET)
        row("193: WINDOW 3 is refused with the message of the range", any("The data area must be 5 to 15 lines" in l for l in L[29:CMD]), "\n".join(L[28:CMD + 1]))
        L = t.keys("window 5", RET, "/s", RET)
        row("193: WINDOW 5 puts it back: the rule is row 33 again and row 28 is source", isrule(L[RULE]) and not isrule(L[28]), repr((L[RULE][:20], L[28][:20])))
        L = t.keys("brk 5", RET)
        r5 = srcrow(L, 5)
        r6 = srcrow(L, 6)
        r5 = r5 if r5 is not None else 0
        r6 = r6 if r6 is not None else 0
        row("BRK 5 marks line 5 with * in the gutter (in the breakpoint style) and nothing else", r5 > 0 and L[r5][0] == "*" and L[r6][0] == " " and t.style(r5, 0) != t.style(r6, 0),
            repr((r5, r6, L[r5][:3], L[r6][:3], t.style(r5, 0), t.style(r6, 0))))
        row("...the breakpoint's number is in a different colour from an ordinary number", r5 > 0 and t.style(r5, 2)[0] != t.style(r6, 2)[0], repr((t.style(r5, 2), t.style(r6, 2))))
        row("...the status line counts it: breakpoints 1", L[STATUS].startswith("[Command]  breakpoints 1"), repr(L[STATUS][:40]))

        say("\n--- help --------------------------------------------------------------------------------------------")
        L = t.keys(F1)
        row("F1 shows the help in a box with an OK button, over the debugger's screen", "[ OK ]" in "\n".join(L), "\n".join(L[:20]))
        L = t.keys(RET)
        row("Return closes it: the source, the command line and the foot are back", "[ OK ]" not in "\n".join(L) and L[CMD].startswith(">") and L[KEYS].rstrip() == KEYTEXT and isrule(L[RULE]),
            "\n".join(L[:4] + L[38:43]))

        say("\n--- F2, Find an action (9 Nov 26, S.186) ----------------------------------------------------------------")
        L = t.keys(F2, idle=1.0)
        txt = "\n".join(L)
        row("F2 opens the finder over the debugger: its entries are the menu bar's, Run > Abort and Run > Stop the program among them (F2 aborted until 9 Nov 26)",
            "Run > Abort" in txt and "Run > Stop the program" in txt and "Help > Find an action" in txt, "\n".join(L[:25]))
        L = t.keys(ESC, idle=1.5)
        row("Esc closes it and runs nothing: the debugger is up with the command line, the status line and the foot",
            "Run > Abort" not in "\n".join(L) and L[CMD].startswith(">") and L[STATUS].startswith("[Command]") and L[KEYS].rstrip() == KEYTEXT,
            "\n".join(L[:3] + L[38:43]))

        say("\n--- leaving ------------------------------------------------------------------------------------------")
        L = t.keys("r", RET, idle=1.0)
        r5 = srcrow(L, 5)
        row("R with a breakpoint on line 5 runs to it: the program printed AFTER-ONE on its own screen, and the debugger is "
            "up again on the alternate one with line 5 about to run",
            r5 is not None and "crt 'AFTER-TWO'" in L[r5] and t.style(r5, 10)[1] == 2,
            "\n".join(l for l in L if l.strip())[-300:])
        row("...with the whole frame drawn again on the fresh screen: the rule, the Autos pane, the foot with its one breakpoint",
            isrule(L[RULE]) and L[1][AUTOX:AUTOX + 5] == "Autos" and autos(L)[0] == 'S = "plain"' and L[STATUS].startswith("[Command]  breakpoints 1") and L[KEYS].rstrip() == KEYTEXT,
            repr((L[RULE][:10], L[1][AUTOX:AUTOX + 8], autos(L)[:2], L[STATUS][:30], L[KEYS][:30])))
        L = t.keys("clr", RET, "r", RET, idle=1.0)
        row("CLR then R runs on to the end: the debugger's screen is gone and the program's own output is on the terminal's own screen",
            any(l.strip() == "AFTER-TWO" for l in L) and srcrow(L, 1) is None and not any("[Command]" in l for l in L), "\n".join(l for l in L if l.strip())[-300:])
        ra = where(L, "AFTER-ONE")
        row("...and in the terminal's own colours: the debugger's theme was given back",
            ra is not None and t.style(ra[0], ra[1])[:2] == (None, None),
            repr([(i, l.rstrip()[:50], t.style(i, max(l.find("AFTER"), 0))) for i, l in enumerate(L) if "AFTER" in l]))
        t.end()

        say("\n--- the Autos pane: the line about to run first, then the line last stopped at, then the rest -----------")
        u = Term(box, "RUN bp %s" % PROG2)
        L = u.lines()
        row("setup: stopped at line 3, crt c + a (the first DEBUG is line 2)", srcrow(L, 3) is not None and L[srcrow(L, 3)][0] == ">", "\n".join(L[:6]))
        a = autos(L)
        row("the variables the line uses come first, in the order the line names them, then the others: C, A, then B",
            a[:4] == ["C = 3", "A = 1", 'B = "text"', ""], repr(a[:5]))
        L = u.keys("r", RET, idle=1.0)
        a = autos(L)
        row("at the next stop (line 5, crt b) B is first, then the variables of the line it last stopped at (line 3): B, C, A",
            srcrow(L, 5) is not None and L[srcrow(L, 5)][0] == ">" and a[:4] == ['B = "text"', "C = 3", "A = 1", ""], repr(a[:5]) + "\n" + "\n".join(L[:7]))
        L = u.keys(CTRL_Q, idle=1.5)
        row("Ctrl-Q at that stop stops the program and leaves (9 Nov 26, S.186): the debugger's screen is gone and line 5 never ran (no 'text' on its own line)",
            not any("[Command]" in l for l in L) and not any(l.strip() == "text" for l in L) and srcrow(L, 5) is None, "\n".join(l for l in L if l.strip())[-300:])
        u.end()

        say("\n--- the site's theme (SCREENTHEME=blue in sd.conf) and the colours of SD BASIC ---------------------------")
        with open(conf, "w") as fh:
            fh.write(original_conf.rstrip("\n") + "\nSCREENTHEME=blue\n")
        b = Term(box, "RUN bp %s" % PROG)
        L = b.lines()
        r1 = srcrow(L, 1)
        r5 = srcrow(L, 5)
        row("setup: the debugger is up in the blue theme", r1 is not None and "s = 'plain'" in L[r1], "\n".join(L[:6]))
        row("the bar is the blue theme's (black on cyan), not classic's (black on white)", b.style(0, 2)[:2] == (0, 6), repr(b.style(0, 2)))
        qi = L[r1].find("'plain'")
        si = L[r1].find("s = ")
        ci = L[r5].find("crt")
        plain = b.style(r1, si)
        row("a string in the source has the string style: not the style of the words round it", r1 is not None and b.style(r1, qi) != plain and b.style(r1, qi + 2) == b.style(r1, qi), repr((b.style(r1, qi), plain)))
        row("a statement (crt, on a line that is not the one about to run) has the keyword style", r5 is not None and b.style(r5, ci) != plain and b.style(r5, ci) != b.style(r1, qi), repr((b.style(r5, ci), plain)))
        row("what the language leaves plain is the pane's text style, the same as the padding after the line",
            plain == b.style(r1, 80) and plain[:2] != (None, None), repr((plain, b.style(r1, 80))))
        r4 = srcrow(L, 4)
        row("the line about to run is in the highlight style from end to end: the colours of the language do not show on it",
            r4 is not None and b.style(r4, L[r4].find("crt")) == b.style(r4, L[r4].find("ONE")) == b.style(r4, 60), repr((b.style(r4, L[r4].find("crt")), b.style(r4, L[r4].find("ONE")), b.style(r4, 60))))
        row("the breakpoint and current-line marks are still drawn (>)", r4 is not None and L[r4][0] == ">", repr(L[r4][:3] if r4 else None))
        b.keys("r", RET, idle=1.0)
        b.end()
        with open(conf, "w") as fh:
            fh.write(original_conf)

        say("\n--- MESSAGE ... IMMEDIATE (the same alternate screen, once AccuTerm's was gone) ---------------------")
        # The receiver is at the command prompt (the kernel takes the event when the next key arrives, as it always has).
        # 'x' is that key: it is not a button letter, so the box stays up until Return.
        a = Term(box, "WHO")
        before = [l for l in a.lines() if l.strip()]
        sess(box, "MESSAGE ALL IMMEDIATE hello-imm")
        L = a.keys("x", idle=1.0)
        row("control: nothing of the message was on the receiver's screen before a key arrived", not any("hello-imm" in l for l in before), repr(before[-3:]))
        row("a message sent IMMEDIATE is shown in a box over the receiver's screen, with its text and an OK button",
            any("hello-imm" in l for l in L) and any("[ OK ]" in l for l in L), "\n".join(l for l in L if l.strip())[-400:])
        row("...with where it came from (Message from user)", any("Message from user" in l for l in L), "\n".join(l for l in L if l.strip())[-300:])
        row("...on the alternate screen: the receiver's own screen (its WHO) is not under the box", not any("WHO" in l for l in L), "\n".join(l for l in L if l.strip())[-300:])
        L = a.keys(RET, idle=1.0)
        row("Return closes it and the receiver's own screen is back, without the message",
            not any("[ OK ]" in l for l in L) and not any("hello-imm" in l for l in L) and any("WHO" in l for l in L),
            "\n".join(l for l in L if l.strip())[-300:])
        a.end()
    finally:
        say("\n--- cleanup ---------------------------------------------------------------------------------------")
        with open(conf, "w") as fh:
            fh.write(original_conf)
        for d in ("bp", "bp.out"):
            for base in (PROG, PROG2):
                for nm in (base, base + "w"):
                    pth = os.path.join(sysd, d, nm)
                    if os.path.exists(pth):
                        os.remove(pth)

    say("\nsandbox-dbgui: %d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        bail("no row ran - a broken test, not a pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
