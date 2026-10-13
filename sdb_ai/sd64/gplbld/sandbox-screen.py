#!/usr/bin/env python3
#
# sandbox-screen.py - the SCREEN statement of the screen library, through USER programs.  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-screen.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty
# or absent).  Exit 0 every row passed, 1 a row failed, 2 it could not run.  Only one private SD can exist on a
# machine (shared memory keys 0x53434c91/92): stop the sandbox afterwards with sandbox-fromtree.py <dir> stop.
#
# START-HISTORY:
# 12 Oct 26 dm  Written with the spike: SCREEN MSGBOX compiled by bcomp's ST.SCREEN into a call of !screen_msgbox.
# END-HISTORY
#
# HOW IT DRIVES THE PROGRAMS.  Every program here is an ordinary USER program, compiled by a plain session (not
# sd -internal): the point of the SCREEN statement is that a user program needs no $-named routine.  It runs on a
# PSEUDO-TERMINAL (ptydrive.py) and the screen is read from the emulator in termscreen.py, as sandbox-sed-menu.py
# does.  Each program paints a background it knows, runs one SCREEN statement, and prints what came back on a line
# of its own, so a row can compare the answer and the screen with the background.  Every row that changes something
# has a control (the screen before the key, the same program without the clause); a program that printed no answer
# line fails its rows, so a statement that did nothing cannot pass.

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ptydrive import PtySession  # noqa: E402

TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
passed = failed = 0

UP, DOWN, LEFT, RIGHT = "\x1bOA", "\x1bOB", "\x1bOD", "\x1bOC"
ESC, RET = "\x1b", "\r"
CTRL_A = "\x01"


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
    say("sandbox-screen: CANNOT RUN - " + msg)
    sys.exit(2)


def sess(box, *cmds):
    """A plain scripted session through a pipe, for compiling and setting up (no keys)."""
    say("    > " + " | ".join(cmds))
    p = subprocess.run([sys.executable, TOOL, box, "sess", os.path.join(box, "user_accounts")] + list(cmds),
                       capture_output=True, text=True, errors="replace", timeout=600)
    out = ANSI.sub("", p.stdout + p.stderr)
    return out.split(":TERM 200,9999", 1)[-1]


class Term:
    """One run of a command on a pseudo-terminal: type to it, read its screen."""

    def __init__(self, box, cmd, cols=100, rows=30):
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

    def reverse(self, i):
        return self.s.screen.reverse(i)

    def underline(self, i):
        return self.s.screen.underline(i)

    def attrs(self, i):
        return self.s.screen.attrs(i)

    def cursor(self):
        """(column, row) of the terminal's cursor, from 0."""
        return (self.s.screen.c, self.s.screen.r)

    def cursor_visible(self):
        return self.s.screen.cursor_visible

    def end(self):
        self.s.type("\rOFF\r", idle=0.5)
        self.s.finish()


def result(lines, tag):
    """The text after TAG on the line that starts with it (None if no line does)."""
    for l in lines:
        if l.startswith(tag):
            return l[len(tag):].strip()
    return None


BG = """   crt @(-1) :
   for r = 0 to 14
      crt @(0, r) : fmt('bg row ' : fmt(r, 'R%2') : ' ' : str('.', 50), '60L') :
   next r
"""


def bg_ok(lines, rows=range(0, 15)):
    """The background rows are as painted; the rows that differ."""
    bad = []
    for r in rows:
        want = ("bg row %02d " % r) + "." * 50
        if lines[r] != want:
            bad.append((r, lines[r]))
    return bad


def hole(line, r):
    """How many cells of background row r are blanks where the painted row has dots (None if anything else differs)."""
    want = ("bg row %02d " % r) + "." * 50
    got = line.ljust(len(want))[:len(want)]
    n = 0
    for g, w in zip(got, want):
        if g == w:
            continue
        if g != " ":
            return None
        n += 1
    return n


# The programs.  The message box is 6 rows high and centred on a 30 row screen, so it covers rows 12 to 17.
PROGS = {
    # the whole statement: a text, a title from a variable, buttons as a comma list, a default, RETURNING, THEN / ELSE
    "zzscmsg": BG + """   t = 'Confirm'
   screen msgbox 'Delete the record?' title t buttons '&Yes,&No' default 2 returning n then
      crt @(0, 20) : 'THEN ' : n : '|'
   end else
      crt @(0, 20) : 'ELSE ' : n : '|'
   end
   crt @(0, 21) : 'TITLE ' : t : '|'
   crt @(0, 22) : 'DONE'
end
""",
    # the same box with the clauses written the other way round, and buttons as values
    "zzscord": BG + """   screen msgbox 'Delete the record?' default 2 buttons '&Yes':@vm:'&No' title 'Confirm' returning n then
      crt @(0, 20) : 'THEN ' : n : '|'
   end else
      crt @(0, 20) : 'ELSE ' : n : '|'
   end
end
""",
    # no clauses at all: one OK button, no THEN / ELSE, the statement is just a statement
    "zzscmin": BG + """   screen msgbox 'Done.'
   crt @(0, 20) : 'AFTER'
end
""",
    # a line of text is ended by a field mark; RETURNING left out
    "zzsclin": BG + """   screen msgbox 'First line':@fm:'Second line' title 'Two'
   crt @(0, 20) : 'AFTER'
end
""",
    # names the statement uses as words are still variables: SCREEN, TITLE, BUTTONS, DEFAULT, RETURNING
    "zzscvar": """   crt @(-1) :
   screen = ''
   screen<2> = 'a'
   crt @(0, 0) : 'ARR ' : convert(@fm, '/', screen) : '|'
   screen = 5
   title = 'T' ; buttons = 'OK' ; default = 1 ; returning = 7
   crt @(0, 1) : 'VARS ' : screen : '|' : title : '|' : buttons : '|' : default : '|' : returning : '|'
   screen msgbox 'hi' title title buttons buttons default default returning n
   crt @(0, 20) : 'GOT ' : n : '|' : title : '|' : buttons : '|' : default : '|'
end
""",
}

PROGS.update({
    # the owned screen: text with styles, a continued text, a padded text, a clipped text, a box with a title
    "zzscown": """   screen open clear else crt @(0, 28) : 'NOTERM' ; stop
   screen text 'plain text' at 2,1
   screen text 'REVERSE' at 2,3 attr 'reverse'
   screen text 'under' at 12,3 attr 'underline'
   screen text 'cont' at 30,5
   screen text 'next'
   screen text 'ab' at 10,7 width 6
   screen text 'xyzzy-long-text' at 5,8 width 5
   screen text '0123456789' at 95,9
   screen box at 2,11 size 20,5 title 'Box' fill
   screen box at 30,11 size 12,4
   screen text 'inside' at 33,12
   screen size returning dims
   crt @(0, 20) : 'SIZE ' : dims<1> : 'x' : dims<2> : '|'
   screen key returning k
end
""",
    # a background of styled rows, then a dialogue over it, then the key that ends the program
    "zzscund": """   screen open clear else crt @(0, 28) : 'NOTERM' ; stop
   for r = 0 to 19
      screen text 'row ':fmt(r, 'R%2'):' ':str('.', 30) at 0,r
      if mod(r, 2) = 1 then
         screen text ' REV ' at 6,r attr 'reverse'
      end else
         screen text ' UL ' at 22,r attr 'underline'
      end
   next r
   screen cursor at 7,9
   screen key returning k1
   screen msgbox 'Replace it?' title 'Ask' buttons '&Yes,&No' returning n
   screen key returning k2
   crt @(0, 25) : 'ANSWER ' : n : ' ' : k1 : ' ' : k2 : '|'
end
""",
    # the terminal is cleared behind the library's back, and SCREEN REFRESH paints the shadow again
    "zzscref": """   screen open clear else crt @(0, 28) : 'NOTERM' ; stop
   screen text 'kept text' at 3,2
   screen text 'kept reverse' at 3,4 attr 'reverse'
   screen key returning k
   crt @(-1) :
   crt @(0, 20) : 'CLEARED'
   screen key returning k
   screen refresh returning r
   crt @(0, 21) : 'REFRESH [' : r : ']'
   screen key returning k
end
""",
    # the cursor: hidden, placed, shown, and put back after a dialogue
    "zzsccur": """   screen open clear nocursor else crt @(0, 28) : 'NOTERM' ; stop
   screen text 'x' at 0,0
   screen cursor at 7,9
   screen key returning k
   screen cursor on
   screen key returning k
   screen msgbox 'Hi'
   screen key returning k
   screen cursor off
   screen key returning k
end
""",
    # keys by name, a timeout, and a screen too small for the program
    "zzsckey": """   crt @(-1) :
   screen open minsize 300,100 else crt @(0, 0) : 'SMALL' ; goto next1
   crt @(0, 0) : 'BIG'
next1:
   for i = 1 to 3
      screen key timeout 3 returning k then
         crt @(0, i) : 'KEY [' : k : ']'
      end else
         crt @(0, i) : 'NOKEY'
      end
   next i
   screen key timeout 1 returning k else crt @(0, 5) : 'TIMEOUT [' : k : ']'
end
""",
})

BAD = {  # name -> (source, text the compiler must give)
    "zzscbv": ("   screen frob 'x'\nend\n", "Unrecognised screen verb frob"),
    "zzscnv": ("   screen\nend\n", "The screen statement needs a verb after it"),
    "zzsctw": ("   screen msgbox 'x' title 'a' title 'b'\nend\n", "The title clause appears twice in a screen statement"),
    "zzscnt": ("   screen msgbox 'x' colour 5\nend\n", "The screen msgbox statement does not take colour"),
    "zzscnx": ("   screen msgbox title 'a'\nend\n", ""),   # no text: some syntax error, any
}


def part_owned(box):
    say("\n--- SCREEN OPEN, TEXT, BOX, SIZE: the screen the library owns -----------------------------------------")
    t = Term(box, "RUN bp zzscown")
    L = t.keys()
    row("control: the program ran and the screen was cleared first (no NOTERM, no prompt left on row 0)", result(L, "NOTERM") is None and not L[0].startswith(":"), "\n".join(L[:3]))
    row("TEXT at 2,1 puts the line there", L[1][2:12] == "plain text" and L[1][:2].strip() == "", repr(L[1]))
    row("ATTR 'reverse' draws reverse video, and only that text; the text before it is not", t.reverse(3) == "REVERSE" and "plain" not in t.reverse(1), repr((t.reverse(3), t.reverse(1))))
    row("ATTR 'underline' draws underlined text on the same row, in its own cells", t.underline(3) == "under" and t.attrs(3)[2:9] == "r" * 7 and t.attrs(3)[12:17] == "u" * 5, repr(t.attrs(3)[:20]))
    row("TEXT without AT continues where the last one ended: 'cont' then 'next' touch", L[5][30:38] == "contnext", repr(L[5]))
    row("WIDTH 6 pads 'ab' to six cells; WIDTH 5 cuts the long text to its first five", L[7][10:12] == "ab" and L[8][5:10] == "xyzzy" and L[8][10:11] == "", repr((L[7], L[8])))
    row("text that runs past the right edge is cut there and does not wrap (95 + 5 cells)", L[9][95:] == "01234" and L[10].strip() == "", repr((L[9], L[10])))
    row("BOX with a title and FILL: a +-| border exactly 20 wide, the title in the top border",
        L[11][2:22] == "+- Box ------------+" and L[12][2:22] == "|" + " " * 18 + "|" and L[15][2:22] == "+" + "-" * 18 + "+", "\n".join(L[11:16]))
    row("BOX without FILL leaves the inside alone (the text drawn inside it is kept), 12 wide, 4 high",
        L[11][30:42] == "+" + "-" * 10 + "+" and L[12][30:42] == "|  inside  |" and L[14][30:42] == "+" + "-" * 10 + "+", "\n".join(L[11:15]))
    row("SIZE answers the terminal's width and height (100x30)", result(L, "SIZE") == "100x30|", repr(result(L, "SIZE")))
    row("the cursor is left after the last TEXT, not wherever the box ended", t.cursor() != (0, 0), repr(t.cursor()))
    t.keys("q")
    t.end()

    say("\n--- a dialogue over the library's own text: every cell comes back, attribute for attribute -------------")
    t = Term(box, "RUN bp zzscund")
    L0 = t.keys()
    A0 = [t.attrs(r) for r in range(30)]
    row("control: the background is 20 rows of text with reverse and underline spans, recorded", "r" in A0[1] and "u" in A0[0] and "r" not in A0[2] and L0[19].startswith("row 19"), repr((A0[0][:30], A0[1][:30])))
    row("control: the cursor was put at 7,9 and is shown", t.cursor() == (7, 9) and t.cursor_visible(), repr(t.cursor()))
    L1 = t.keys("a")
    row("a key and then the box: it is on the screen, over the background", any("[ Yes ]" in l and "[ No ]" in l for l in L1) and any("Replace it?" in l for l in L1), "\n".join(L1[10:19]))
    row("control: the box really changed rows 12 to 17 (a restore that did nothing cannot pass)", L1[12:18] != L0[12:18], "")
    row("...and left rows 0 to 11 alone", L1[:12] == L0[:12], "")
    L2 = t.keys(RET)
    A2 = [t.attrs(r) for r in range(30)]
    row("Return closes it: every row of the background has its text back", L2[:20] == L0[:20], "\n".join(l for l, m in zip(L2[:20], L0[:20]) if l != m))
    row("...and every cell its style back (reverse and underline spans, 20 rows x 100 cells)", A2[:20] == A0[:20], repr([(i, a, b) for i, (a, b) in enumerate(zip(A2[:20], A0[:20])) if a != b][:2]))
    row("...and the cursor is where SCREEN CURSOR put it (7,9), not where the box ended", t.cursor() == (7, 9) and t.cursor_visible(), repr(t.cursor()))
    L3 = t.keys("z")
    row("the answer, the keys before and after: button 1, a, z", result(L3, "ANSWER") == "1 a z|", repr(result(L3, "ANSWER")))
    t.end()

    say("\n--- SCREEN REFRESH --------------------------------------------------------------------------------------")
    t = Term(box, "RUN bp zzscref")
    L = t.keys()
    row("control: the kept text and the kept reverse text are on the screen", L[2][3:12] == "kept text" and t.reverse(4) == "kept reverse", "\n".join(L[:6]))
    L = t.keys("a")
    row("control: the program cleared the terminal behind the library's back (it says so)", any(l.startswith("CLEARED") for l in L), "\n".join(L[:22]))
    row("...and the kept text really is gone from the screen", not any("kept text" in l for l in L), "\n".join(L[:6]))
    L = t.keys("b")
    row("REFRESH paints the shadow again: the text is back at the same place", L[2][3:12] == "kept text", "\n".join(L[:6]))
    row("...with its style: the reverse text is reverse again", t.reverse(4) == "kept reverse" and "kept text" not in t.reverse(2), repr(t.reverse(4)))
    row("...and the answer is null (the terminal is the size it was)", result(L, "REFRESH") == "[]", repr(result(L, "REFRESH")))
    t.keys("c")
    t.end()

    say("\n--- SCREEN CURSOR ---------------------------------------------------------------------------------------")
    t = Term(box, "RUN bp zzsccur")
    L = t.keys()
    row("NOCURSOR hides the cursor and CURSOR AT places it: hidden, at 7,9", (not t.cursor_visible()) and t.cursor() == (7, 9), repr((t.cursor(), t.cursor_visible())))
    t.keys("a")
    row("CURSOR ON shows it where it was", t.cursor_visible() and t.cursor() == (7, 9), repr((t.cursor(), t.cursor_visible())))
    L = t.keys("b")
    row("control: the next key opens a message box (so the next row is about a cursor that was moved)", any("[ OK ]" in l for l in L), "\n".join(L[10:20]))
    L = t.keys(RET)
    row("after the dialogue the cursor is put back at 7,9 and is shown", t.cursor_visible() and t.cursor() == (7, 9) and not any("[ OK ]" in l for l in L), repr((t.cursor(), t.cursor_visible())))
    t.keys("c")
    row("CURSOR OFF hides it again", not t.cursor_visible(), repr(t.cursor_visible()))
    t.end()

    say("\n--- SCREEN KEY, and MINSIZE ----------------------------------------------------------------------------")
    t = Term(box, "RUN bp zzsckey")
    L = t.keys()
    row("MINSIZE 300,100 on a 100x30 terminal takes the ELSE branch: the screen is not taken", result(L, "SMALL") is not None or any(l.startswith("SMALL") for l in L), "\n".join(L[:3]))
    row("...and the program carried on without the screen (no BIG)", not any(l.startswith("BIG") for l in L), "")
    L = t.keys("x")
    L = t.keys(UP)
    L = t.keys(CTRL_A)
    row("keys come back by name: x, up, ctrl-a", L[1].strip() == "KEY [x]" and L[2].strip() == "KEY [up]" and L[3].strip() == "KEY [ctrl-a]", "\n".join(L[:5]))
    row("control: no TIMEOUT line before the time has run out", not any(l.startswith("TIMEOUT") for l in L), "")
    t.s.settle(1.8)
    L = t.lines()
    row("TIMEOUT 1 with no key: ELSE is taken and RETURNING holds null", any(l.startswith("TIMEOUT []") for l in L), "\n".join(L[:8]))
    t.end()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-screen.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-screen: sandbox %s" % box)
    say("sandbox-screen: tree    %s" % os.path.dirname(HERE))
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-screen: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    for nm, body in PROGS.items():
        with open(os.path.join(sysd, "bp", nm), "w") as fh:
            fh.write(body)
    for nm, (body, _) in BAD.items():
        with open(os.path.join(sysd, "bp", nm), "w") as fh:
            fh.write(body)
    try:
        say("\n--- the programs compile as USER programs ---------------------------------------------------------")
        out = sess(box, *["BASIC bp %s" % n for n in PROGS])
        n_ok = len(re.findall(r"(?m)^Compiled 1 program\(s\) with no errors", out))
        row("setup: all %d programs compile with no errors, in a session that is not internal" % len(PROGS), n_ok == len(PROGS), out[-900:])
        row("control: the library routine is catalogued for user programs (the compile did not need sd -internal)",
            os.path.isfile(os.path.join(sysd, "gpl.bp", "screen_msgbox")), "missing")

        say("\n--- SCREEN MSGBOX ---------------------------------------------------------------------------------")
        t = Term(box, "RUN bp zzscmsg")
        L = t.keys()
        row("control: before any key the box is drawn and there is no answer line",
            any("Delete the record?" in l for l in L) and result(L, "THEN") is None and result(L, "ELSE") is None, "\n".join(L[10:20]))
        row("the box has the title (from a variable), the text, and the two buttons from a comma list",
            any("Confirm" in l for l in L) and any("[ Yes ]" in l and "[ No ]" in l for l in L), "\n".join(L[10:20]))
        btn = next((i for i, l in enumerate(L) if "[ Yes ]" in l), None)
        row("DEFAULT 2: the second button is the one in reverse video, the first is not",
            btn is not None and "[ No ]" in t.reverse(btn) and "[ Yes ]" not in t.reverse(btn), repr(btn))
        row("control: the background above the box is as painted", not bg_ok(L, range(0, 12)), repr(bg_ok(L, range(0, 12))))
        L = t.keys(RET)
        row("Return chooses the default: THEN is taken and RETURNING holds 2", result(L, "THEN") == "2|" and result(L, "ELSE") is None,
            repr((result(L, "THEN"), result(L, "ELSE"))))
        row("...the box is gone (the program runs on to DONE)", not any("[ Yes ]" in l for l in L) and result(L, "DONE") is not None, "\n".join(L[10:24]))
        holes = [hole(L[r], r) for r in (12, 13, 14)]
        row("...rows above the box are untouched; where the box was the rows are blank, and only there (no SCREEN OPEN yet, so the library has no text to put back)",
            not bg_ok(L, range(0, 12)) and all(h is not None and h >= 10 for h in holes), repr((bg_ok(L, range(0, 12)), holes)))
        row("the title variable is as it was (arguments are passed by value)", result(L, "TITLE") == "Confirm|", repr(result(L, "TITLE")))
        t.end()
        t = Term(box, "RUN bp zzscmsg")
        t.keys()
        L = t.keys("y")
        row("a button letter chooses at once: Y is the first button, THEN 1", result(L, "THEN") == "1|", repr((result(L, "THEN"), result(L, "ELSE"))))
        t.end()
        t = Term(box, "RUN bp zzscmsg")
        t.keys()
        L = t.keys(ESC, idle=0.9)
        row("Esc cancels: ELSE is taken, RETURNING holds 0, THEN is not", result(L, "ELSE") == "0|" and result(L, "THEN") is None,
            repr((result(L, "THEN"), result(L, "ELSE"))))
        t.end()
        t = Term(box, "RUN bp zzscmsg")
        t.keys()
        L = t.keys(LEFT, RET)
        row("Left moves to the first button: Return then gives 1", result(L, "THEN") == "1|", repr(result(L, "THEN")))
        t.end()

        say("\n--- the clauses in another order, with values ---------------------------------------------------------")
        t = Term(box, "RUN bp zzscord")
        L = t.keys()
        row("DEFAULT, BUTTONS, TITLE written in the other order give the same box",
            any("Confirm" in l for l in L) and any("[ Yes ]" in l and "[ No ]" in l for l in L)
            and "[ No ]" in t.reverse(next((i for i, l in enumerate(L) if "[ Yes ]" in l), 0)), "\n".join(L[10:20]))
        L = t.keys(RET)
        row("...and the answer is the same: THEN 2", result(L, "THEN") == "2|", repr(result(L, "THEN")))
        t.end()

        say("\n--- the shortest form --------------------------------------------------------------------------------")
        t = Term(box, "RUN bp zzscmin")
        L = t.keys()
        row("control: the box shows its text and one OK button, and the program has not run on",
            any("Done." in l for l in L) and any("[ OK ]" in l for l in L) and result(L, "AFTER") is None, "\n".join(L[10:20]))
        L = t.keys(RET)
        row("Return closes it and the next statement runs (no THEN / ELSE needed)", result(L, "AFTER") is not None and not any("[ OK ]" in l for l in L), "\n".join(L[10:24]))
        t.end()
        t = Term(box, "RUN bp zzsclin")
        L = t.keys()
        row("a field mark ends a line of the text: two lines and the title", any("First line" in l for l in L) and any("Second line" in l for l in L) and any("Two" in l for l in L), "\n".join(L[8:20]))
        t.keys(RET)
        t.end()

        say("\n--- words of the statement stay usable as variables ---------------------------------------------------")
        t = Term(box, "RUN bp zzscvar")
        L = t.keys()
        row("control: SCREEN (also as a dynamic array), TITLE, BUTTONS, DEFAULT, RETURNING as variables keep their values",
            result(L, "ARR") == "/a|" and result(L, "VARS") == "5|T|OK|1|7|", repr((result(L, "ARR"), result(L, "VARS"))))
        L = t.keys(RET)
        row("and the same names used as the statement's values: the box answers 1 and the variables are unchanged",
            result(L, "GOT") == "1|T|OK|1|", repr(result(L, "GOT")))
        t.end()

        part_owned(box)

        say("\n--- compile errors -------------------------------------------------------------------------------------")
        for nm, (_, want) in BAD.items():
            out = sess(box, "BASIC bp %s" % nm)
            ok = ("with no errors" not in out) and (want in out)
            row("%s: refused%s" % (nm, (" with '" + want + "'") if want else ""), ok, out[-400:])
    finally:
        say("\n--- cleanup ---------------------------------------------------------------------------------------")
        for nm in list(PROGS) + list(BAD):
            for d in ("bp", "bp.out"):
                pth = os.path.join(sysd, d, nm)
                if os.path.exists(pth):
                    os.remove(pth)

    say("\nsandbox-screen: %d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        bail("no row ran - a broken test, not a pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
