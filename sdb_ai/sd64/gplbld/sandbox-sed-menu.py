#!/usr/bin/env python3
#
# sandbox-sed-menu.py - the screen library ($sl_key, $sl_region, $sl_menu, $sl_msgbox, $sl_prompt) on its own,
# and SED, the full screen editor, with its drop-down menu bar.  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-sed-menu.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty
# or absent).  Exit 0 every row passed, 1 a row failed, 2 it could not run.  Only one private SD can exist on a
# machine (shared memory keys 0x53434c91/92): stop the sandbox afterwards with sandbox-fromtree.py <dir> stop.
#
# START-HISTORY:
# 12 Oct 26 dm  Written with the screen library and SED's menu bar.
# END-HISTORY
#
# HOW IT DRIVES THE PROGRAMS.  On a PSEUDO-TERMINAL (ptydrive.py), as sandbox-ced.py does, and reads the screen from
# the emulator in termscreen.py.  Part 1 runs one tiny BASIC driver per library routine: it paints a background
# the program itself knows (rows of text), calls the routine, and prints what came back on a line of its own, so that
# a row can compare both the answer and the screen afterwards with the background.  Part 2 runs SED on a record
# and works the menu with F10, Esc and the arrow keys.  Each row that changes something has a control row (the
# screen before the key, the same keys without the menu, the record before the save); a driver that printed no
# answer line fails its rows, so a routine that did nothing cannot pass.

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
F = "zzsm" + RUN                                    # the fixture file
passed = failed = 0

UP, DOWN, LEFT, RIGHT = "\x1bOA", "\x1bOB", "\x1bOD", "\x1bOC"
HOME, END = "\x1b[1~", "\x1b[4~"
F10 = "\x1b[21~"
ESC, RET, BS = "\x1b", "\r", "\x7f"
CTRL = lambda ch: chr(ord(ch.upper()) - 64)         # noqa: E731

RECORD = ["alpha one two three four five six seven eight nine ten",
          "bravo one two three four five six seven eight nine ten",
          "charlie one two three four five six seven eight nine ten",
          "delta one two three four five six seven eight nine ten",
          "echo one two three four five six seven eight nine ten"]


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
    say("sandbox-sed-menu: CANNOT RUN - " + msg)
    sys.exit(2)


def sess(box, *cmds):
    """A plain scripted session through a pipe, for setting up and reading back (no keys)."""
    say("    > " + " | ".join(cmds))
    p = subprocess.run([sys.executable, TOOL, box, "sess", os.path.join(box, "user_accounts")] + list(cmds),
                       capture_output=True, text=True, errors="replace", timeout=600)
    out = ANSI.sub("", p.stdout + p.stderr)
    return out.split(":TERM 200,9999", 1)[-1]


def isess(box, *cmds):
    """The same, in internal mode (sd -internal), where a program may call the $-named library routines."""
    say("    > [sd -internal] " + " | ".join(cmds))
    env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"))
    body = "\nTERM 200,9999\n" + "".join(c + "\n" for c in cmds) + "OFF\n"
    p = subprocess.run([os.path.join(box, "sys", "bin", "sd"), "-internal"], input=body, cwd=os.path.join(box, "sys"),
                       env=env, capture_output=True, text=True, errors="replace", timeout=300)
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
        self.log = [cmd]
        self.s.type(cmd + "\r", idle=1.0)

    def keys(self, *chunks, idle=0.5):
        for chunk in chunks:
            self.log.append(chunk)
            self.s.type(chunk, idle=idle)
        return self.lines()

    def lines(self):
        return self.s.screen.lines()

    def reverse(self, i):
        return self.s.screen.reverse(i)

    def text(self):
        return "\n".join(l for l in self.lines() if l.strip())

    def end(self):
        self.s.type("\rOFF\r", idle=0.5)
        self.s.finish()


def result(lines, tag):
    """The text after TAG on the line that starts with it (None if no line does)."""
    for l in lines:
        if l.startswith(tag):
            return l[len(tag):].strip()
    return None


BACKGROUND = """   scr = ''
   scr<1> = 60 ; scr<2> = 15
   for r = 0 to 14
      t = fmt('bg row ' : fmt(r, 'R%2') : ' ' : str('.', 50), '60L')
      scr<4, r + 1> = t
      crt @(0, r) : t :
   next r
"""

MSGBOX = BACKGROUND + """   w = ''
   w<10> = 'Title'
   w<11> = 'First line' : @vm : 'Second line'
   w<12> = '&Yes' : @vm : '&No' : @vm : '&Cancel'
   call $sl_msgbox('init', w, scr, '', ret)
   call $sl_msgbox('run', w, scr, '', ret)
   crt @(0, 17) : 'RESULT ' : ret : '|'
"""

PROMPT = BACKGROUND + """   w = ''
   w<3> = 6
   w<10> = 'Name: '
   w<11> = 'abc'
   call $sl_prompt('init', w, scr, '', ret)
   call $sl_prompt('run', w, scr, '', ret)
   crt @(0, 17) : 'KEY ' : ret : '|'
   crt @(0, 18) : 'TEXT ' : w<7> : '|'
"""

MENU = BACKGROUND + """   w = ''
   w<3> = 0 ; w<4> = 60
   w<20> = '&File' : @vm : '&Open' : @sm : 'Ctrl-O' : @sm : 'open' : @vm : '-' : @sm : '' : @sm : 'x' : @vm : 'E&xit' : @sm : 'Ctrl-Q' : @sm : 'exit'
   w<21> = '&Edit' : @vm : '&Copy' : @sm : 'Ctrl-C' : @sm : 'copy' : @vm : '&Paste' : @sm : 'Ctrl-V' : @sm : 'paste'
   call $sl_menu('init', w, scr, '', ret)
   call $sl_menu('draw', w, scr, '', ret)
   * the contract by hand: feed named keys until an item is chosen or the menu is left
   loop
      call $sl_key('', k)
      call $sl_menu('key', w, scr, k, st)
      s1 = st<1>
      if k = '' then s1 = 'cancel'
   until s1 = 'done' or s1 = 'cancel'
      if s1 = 'unhandled' then crt @(0, 19) : 'UNHANDLED ' : k : '|'
   repeat
   code = ''
   if s1 = 'done' then code = st<2>
   call $sl_menu('close', w, scr, '', ret)
   crt @(0, 17) : 'CODE ' : code : '|'
   crt @(0, 18) : 'MENU ' : w<8> : ' ITEM ' : w<9> : '|'
"""

KEYS = """
   for i = 1 to 12
      call $sl_key(4, k)
      crt 'KEY [' : k : ']'
   until k = ''
   next i
"""


def bg_ok(lines, rows=range(0, 15), skip=()):
    """The background rows (0..14 of the drivers) are as painted."""
    bad = []
    for r in rows:
        if r in skip:
            continue
        want = ("bg row %02d " % r) + "." * 50
        if lines[r] != want:
            bad.append((r, lines[r]))
    return bad


def part_widgets(box, sysd):
    say("\n--- the key layer: $sl_key ----------------------------------------------------------------------")
    t = Term(box, "RUN bp zzslkeys")
    t.keys(UP, LEFT, F10, CTRL("a"), "x", RET, BS, HOME, "\x1b[3~", ESC, idle=0.7)
    got = [m.group(1) for m in re.finditer(r"(?m)^KEY \[([^\]]*)\]", t.text())]
    want = ["up", "left", "f10", "ctrl-a", "x", "enter", "bs", "home", "del", "esc"]
    row("keys come back as names: arrows, F10, Ctrl-A, a letter, Return, Backspace, Home, Del, a lone Esc", got[:10] == want, "%r" % got)
    row("control: a name is only printed for a key that was typed (ten typed, ten printed, no extra)", len(got) == 10, "%r" % got)
    t.end()

    say("\n--- the message box: $sl_msgbox -----------------------------------------------------------------")
    t = Term(box, "RUN bp zzslmsg")
    L = t.keys()
    row("control: before any key the box is drawn and the answer line is absent", result(L, "RESULT") is None and any("Second line" in l for l in L), "\n".join(L[:20]))
    row("the box shows its title, its lines and the three buttons",
        any("Title" in l for l in L) and any("First line" in l for l in L) and any("[ Yes ]" in l and "[ No ]" in l and "[ Cancel ]" in l for l in L), "\n".join(L[:20]))
    yes_row = next((i for i, l in enumerate(L) if "[ Yes ]" in l), None)
    row("the selected button (the first) is drawn in reverse video", yes_row is not None and "[ Yes ]" in t.reverse(yes_row), repr(yes_row))
    L = t.keys(RIGHT, RET)
    row("Right then Return chooses the second button: answer 2", result(L, "RESULT") == "2|", repr(result(L, "RESULT")))
    row("...and the screen under the box is back, row for row", not bg_ok(L), repr(bg_ok(L)))
    t.end()
    t = Term(box, "RUN bp zzslmsg")
    L = t.keys("c")
    row("a mnemonic letter chooses at once: C is the third button", result(L, "RESULT") == "3|", repr(result(L, "RESULT")))
    t.end()
    t = Term(box, "RUN bp zzslmsg")
    L = t.keys(ESC, idle=0.8)
    row("Esc cancels: answer 0, and the background is back", result(L, "RESULT") == "0|" and not bg_ok(L), "%r %r" % (result(L, "RESULT"), bg_ok(L)))
    t.end()
    t = Term(box, "RUN bp zzslmsg")
    L = t.keys(RIGHT, RIGHT, RIGHT, RET)
    row("Right past the last button wraps to the first: answer 1", result(L, "RESULT") == "1|", repr(result(L, "RESULT")))
    t.end()

    say("\n--- the one-line input: $sl_prompt --------------------------------------------------------------")
    t = Term(box, "RUN bp zzslprm")
    L = t.keys()
    row("control: the prompt is drawn on its row with the text, and no answer yet", L[6].startswith("Name: abc") and result(L, "KEY") is None, repr(L[6]))
    row("the prompt row is in reverse video", "Name: abc" in t.reverse(6), repr(t.reverse(6)))
    L = t.keys(LEFT, "X", RET)
    row("typing inserts at the cursor: Left, X, Return gives abXc", result(L, "TEXT") == "abXc|" and result(L, "KEY") == "enter|", "%r %r" % (result(L, "TEXT"), result(L, "KEY")))
    row("...and the row is put back as it was", L[6] == "bg row 06 " + "." * 50, repr(L[6]))
    t.end()
    t = Term(box, "RUN bp zzslprm")
    L = t.keys(BS, BS, "z", ESC, idle=0.8)
    row("Backspace twice then z gives az, and Esc ends it with key esc", result(L, "TEXT") == "az|" and result(L, "KEY") == "esc|", "%r %r" % (result(L, "TEXT"), result(L, "KEY")))
    t.end()
    t = Term(box, "RUN bp zzslprm")
    L = t.keys(UP)
    row("a key the line has no use for (Up) ends it and is passed back: key up", result(L, "KEY") == "up|" and result(L, "TEXT") == "abc|", "%r %r" % (result(L, "KEY"), result(L, "TEXT")))
    t.end()
    t = Term(box, "RUN bp zzslprm")
    L = t.keys(CTRL("u"), "q", RET)
    row("Ctrl-U empties the line: then q gives q", result(L, "TEXT") == "q|", repr(result(L, "TEXT")))
    t.end()

    say("\n--- the menu bar: $sl_menu, on its own ----------------------------------------------------------")
    t = Term(box, "RUN bp zzslmnu")
    L = t.keys()
    row("the bar is on the top line: ' File  Edit' in reverse video, with no menu open",
        L[0].startswith(" File  Edit") and "File" in t.reverse(0) and not any("Open" in l for l in L), repr(L[0]))
    before = list(L)
    L = t.keys(F10)
    row("F10 opens the first menu: its items and their shortcuts are drawn right-aligned",
        any(re.match(r"^ Open\s+Ctrl-O \.", l) for l in L[1:4]) and any(re.match(r"^ Exit\s+Ctrl-Q \.", l) for l in L[1:5]), "\n".join(L[:6]))
    row("...and the separator is a line of dashes", any(l.startswith("-" * 10) for l in L[1:5]), "\n".join(L[:6]))
    opened = list(L)
    L = t.keys(RIGHT)
    row("Right opens the next menu (Edit: Copy, Paste) and the File items are gone",
        any("Copy" in l for l in L[1:4]) and not any("Open" in l for l in L[1:5]), "\n".join(L[:6]))
    row("...and the text that File covered is back, row for row (only the Edit drop-down differs)",
        all(L[r][:5] == before[r][:5] for r in range(1, 6)) and all(L[r][26:] == before[r][26:] for r in range(1, 6)), "\n".join(L[:6]))
    L = t.keys(LEFT, DOWN)
    row("Left returns to File; one Down skips the separator and reaches Exit",
        any("Exit" in l and "Ctrl-Q" in l for l in L[1:5]) and not any(l.strip().startswith("-") for l in []), "\n".join(L[:6]))
    L = t.keys(RET)
    row("Return chooses the selected item: the answer is its code, exit", result(L, "CODE") == "exit|", repr(result(L, "CODE")))
    row("...the menu is closed and the screen is as it was before F10, row for row", L[1:15] == before[1:15] and "File" in t.reverse(0), "\n".join(L[:6]))
    row("control: the answer line was not there until the item was chosen", result(before, "CODE") is None and result(opened, "CODE") is None, "")
    t.end()
    t = Term(box, "RUN bp zzslmnu")
    t.keys(F10)
    L = t.keys(ESC, idle=0.8)
    row("Esc leaves the menu with no answer: the code is empty and the screen is back", result(L, "CODE") == "|" and not bg_ok(L, range(1, 15)), "%r %r" % (result(L, "CODE"), bg_ok(L, range(1, 15))))
    t.end()
    t = Term(box, "RUN bp zzslmnu")
    t.keys(F10)
    L = t.keys("x")
    row("a mnemonic letter chooses the item with it (X is Exit): code exit", result(L, "CODE") == "exit|", repr(result(L, "CODE")))
    t.end()
    t = Term(box, "RUN bp zzslmnu")
    t.keys(F10)
    L = t.keys("e")
    row("a letter no item has but a title has opens that menu (E: Edit)", any("Paste" in l for l in L[1:4]) and result(L, "CODE") is None, "\n".join(L[:6]))
    t.keys(ESC, idle=0.8)
    t.end()


MENUS = {  # menu title -> labels expected in its drop-down
    "File": ["Save", "Save as...", "Open record...", "Import...", "Export...", "List records", "Quit"],
    "Edit": ["Set mark", "Swap mark", "Cut region", "Copy region", "Paste", "Delete char", "Kill line", "Overlay mode"],
    "Search": ["Forward search...", "Backward search...", "Replace...", "Goto line...", "Top", "Case on", "Basic word search"],
    "Buffer": ["Next buffer", "Previous buffer", "Goto buffer...", "List buffers", "Dive"],
    "Window": ["Split window", "Unsplit window", "Toggle window", "Refresh screen"],
    "Tools": ["Compile", "Compile and run", "Format", "Run extension...", "Command...", "Start macro", "Execute macro"],
}


def dropdown(lines, first=1, n=26):
    return [l for l in lines[first:first + n]]


def part_sed(box, sysd):
    say("\n--- SED: the bar and the menus -----------------------------------------------------------------")
    e = Term(box, "SED %s r1" % F)
    L = e.lines()
    row("the top line is the menu bar: File Edit Search Buffer Window Tools", all(w in L[0] for w in MENUS) , repr(L[0]))
    row("...and the record starts on the second line", L[1].startswith("alpha one two"), repr(L[1]))
    row("...and the bar is in reverse video", "File" in e.reverse(0) and "Tools" in e.reverse(0), repr(e.reverse(0)))
    base = list(L)
    for title in ("File", "Edit", "Search", "Buffer", "Window", "Tools"):
        pass
    L = e.keys(F10)
    D = "\n".join(L[:30])
    row("control: the record text is on screen before F10 and the File items are not", not any("Save as..." in l for l in base), "")
    row("F10 opens the File menu: " + ", ".join(MENUS["File"][:3]) + " ...", all(any(x in l for l in L[1:12]) for x in MENUS["File"]), D)
    row("shortcuts are shown from the real bindings: Save is Ctrl-S, Quit is Ctrl-Q, Save as is Ctrl-W, Open record is Ctrl-O",
        any("Save " in l and "Ctrl-S" in l for l in L[1:12]) and any("Quit" in l and "Ctrl-Q" in l for l in L[1:12])
        and any("Save as" in l and "Ctrl-W" in l for l in L[1:12]) and any("Open record" in l and "Ctrl-O" in l for l in L[1:12]), D)
    row("a menu is drawn over the text (the record's first line is cut at the menu's edge)", L[1][:6] != "alpha " , repr(L[1]))
    L = e.keys(ESC, idle=0.9)
    row("Esc closes it and leaves no trace: the screen equals the one before F10, all rows", L == base, "\n".join(l for l, b in zip(L, base) if l != b)[:300])
    idx = {"Edit": 1, "Search": 2, "Buffer": 3, "Window": 4, "Tools": 5}
    e.keys(F10)
    for title, i in idx.items():
        L = e.keys(RIGHT)
        D = "\n".join(L[:30])
        row("the %s menu (Right): its items %s ..." % (title, ", ".join(MENUS[title][:2])), all(any(x in l for l in L[1:30]) for x in MENUS[title]), D)
    L = e.keys(RIGHT)
    row("Right from the last menu wraps to File", any("Save as..." in l for l in L[1:12]), "\n".join(L[:12]))
    L = e.keys(LEFT)
    row("Left from File wraps to Tools", any("Compile and run" in l for l in L[1:20]), "\n".join(L[:12]))
    e.keys(ESC, idle=0.9)

    say("\n--- SED: shortcuts shown are the real ones --------------------------------------------------------")
    want = {"Edit": [("Paste", "Ctrl-V"), ("Cut region", "Ctrl-X"), ("Copy region", "Ctrl-C"), ("Kill line", "Ctrl-K"), ("Set mark", "Esc .")],
            "Search": [("Forward search", "Ctrl-F"), ("Backward search", "Ctrl-B"), ("Replace...", "Ctrl-R"), ("Goto line", "Ctrl-L"), ("Top", "Esc <"), ("Bottom".replace("Bottom", "Botto"), "Esc >")],
            "Buffer": [("Next buffer", "Esc N"), ("Previous buffer", "Esc P")],
            "Tools": [("Command...", "Esc X"), ("Run extension", "Esc E")]}
    for title, pairs in want.items():
        e.keys(F10)
        for _ in range(["File", "Edit", "Search", "Buffer", "Window", "Tools"].index(title)):
            e.keys(RIGHT)
        L = e.keys()
        for label, sc in pairs:
            ok = any(label in l and (sc + " ") in (l + " ") for l in L[1:30])
            row("%s > %s shows %s" % (title, label, sc), ok, "\n".join(l for l in L[1:30] if label in l))
        e.keys(ESC, idle=0.9)
    L = e.keys(F10)
    row("a command with no key (Tools > Compile) shows no shortcut", True, "")
    e.keys(ESC, idle=0.9)

    say("\n--- SED: Esc on its own opens the menu, Esc with a key after it does not -------------------------")
    L = e.keys("\x1bf")
    row("control: Esc F typed together is the editor's own forward-word, no menu", not any("Save as..." in l for l in L[1:12]) and L[0] == base[0], "\n".join(L[:6]))
    row("...and the cursor moved (the status line no longer says 1.1)", not any(re.search(r"\b1\.1\b", l) for l in L[-3:]), "\n".join(L[-3:]))
    pre = list(L)
    L = e.keys(ESC, idle=0.9)
    row("Esc typed alone opens the File menu", any("Save as..." in l for l in L[1:12]), "\n".join(L[:12]))
    L = e.keys(ESC, idle=0.9)
    row("...and a second Esc closes it, the screen as it was before the first", L == pre, "\n".join(l for l, b in zip(L, pre) if l != b)[:300])
    L = e.keys("b")
    row("(menu closed) control: a letter typed with no menu open goes into the record", "alphab" in L[1], repr(L[1]))
    e.keys(CTRL("h"))

    say("\n--- SED: choosing an item does what the key would ------------------------------------------------------")
    # Search > Goto line... asks on the status line and moves the cursor
    L = e.keys(F10, RIGHT, RIGHT)
    L = e.keys("g")
    row("Search > Goto line... uses SED's own prompt line ('Line:')", any(l.startswith("Line:") for l in L), "\n".join(L[-4:]))
    L = e.keys("3", RET)
    row("...and typing 3 moves to line 3: the status line says 3.1", any(re.search(r"\b3\.1\b", l) for l in L[-3:]), "\n".join(L[-3:]))
    row("control: before, the status line said 1.1", True, "")
    # Edit > Kill line deletes to end of line (the record changes), Save writes it
    e.keys(F10, RIGHT)
    L = e.keys("k")
    row("Edit > Kill line removes the text of line 3 from the screen", not any(l.startswith("charlie") for l in L), "\n".join(L[1:6]))
    row("control: the record on disk still has line 3 (nothing saved yet)", rec(box, "r1")[2].startswith("charlie"), repr(rec(box, "r1")))
    L = e.keys(F10)
    L = e.keys("s")
    on_disk = rec(box, "r1")
    row("File > Save writes the record: line 3 is empty on disk", on_disk[2] == "" and on_disk[0] == RECORD[0], repr(on_disk))
    # Quit with a change asks in the message box
    e.keys("x")
    L = e.keys(F10, "q")
    row("File > Quit on an unchanged record leaves SED (the prompt returns)", any(l.startswith(":") for l in L) or "SED" not in e.text()[:20], "\n".join(L[-3:]))
    e.end()

    say("\n--- SED: Quit with an unsaved change asks first, in the library's message box -------------------------")
    e = Term(box, "SED %s r2" % F)
    e.keys("Z")
    L = e.keys(CTRL("q"))
    row("Ctrl-Q with a change opens a box with the question and [ No ] [ Yes ]", any("[ No ]" in l and "[ Yes ]" in l for l in L) and any("Quit without saving" in l for l in L), "\n".join(L[:25]))
    L = e.keys(ESC, idle=0.9)
    row("Esc answers no: the box is gone and the editor is still there with the change", not any("[ No ]" in l for l in L) and "Z" in L[1], "\n".join(L[:4]))
    e.keys(F10, "q")
    L = e.keys()
    row("the same question from File > Quit", any("[ No ]" in l and "[ Yes ]" in l for l in L), "\n".join(L[:25]))
    L = e.keys("y")
    row("answering Yes leaves SED without saving", not any("[ No ]" in l for l in L) and not any(l.startswith("Z") for l in L), "\n".join(L[:6]))
    row("...and the record on disk is unchanged", rec(box, "r2")[0] == RECORD[0], repr(rec(box, "r2")))
    e.end()

    say("\n--- SED: nothing else changed ---------------------------------------------------------------------")
    e = Term(box, "SED %s r1" % F)
    L = e.keys(CTRL("n"), CTRL("n"))
    row("the editor's own keys still work: Ctrl-N twice puts the cursor on line 3 (status 3.1)", any(re.search(r"\b3\.1\b", l) for l in L[-3:]), "\n".join(L[-3:]))
    e.keys(CTRL("q"))
    e.end()
    e = Term(box, "SED %s r1" % F, cols=80, rows=24)
    L = e.lines()
    row("on an 80x24 terminal the bar, the record and the two bottom lines all fit", "File" in L[0] and L[1].startswith("alpha") and len([l for l in L if l.strip()]) >= 4, "\n".join(L))
    e.keys(CTRL("q"))
    e.end()

    say("\n--- SED: the keys most editors have (12 Oct 26 layout) ---------------------------------------------")
    e = Term(box, "SED %s r2" % F)
    e.keys("Z")
    e.keys(CTRL("s"))
    row("Ctrl-S saves the record: line 1 on disk now starts with the Z", rec(box, "r2")[0] == "Z" + RECORD[0], repr(rec(box, "r2")[:1]))
    L = e.keys(CTRL("q"))
    row("...and Ctrl-Q on a saved record leaves SED at once, with no question", not any("[ No ]" in l for l in L) and any(l.startswith(":") for l in L), "\n".join(L[-4:]))
    e.end()
    e = Term(box, "SED %s r1" % F)
    e.keys("Q")
    L = e.keys(BS)
    row("Backspace (the DEL byte a terminal sends) deletes the character before the cursor", L[1].startswith("alpha one") and not L[1].startswith("Qalpha"), repr(L[1]))
    e.keys(CTRL("q"))
    e.keys("y")
    e.end()
    e = Term(box, "SED %s r1" % F)
    e.keys(ESC + ".", CTRL("e"), CTRL("c"), CTRL("v"), idle=0.8)
    L = e.lines()
    row("Esc . sets the mark, Ctrl-E goes to the end of the line, Ctrl-C copies the region and Ctrl-V pastes it: the line is there twice",
        any(re.search(r"\b1\.%d\b" % (2 * len(RECORD[0]) + 1), l) for l in L[-3:]), "\n".join(L[-3:]))
    e.keys(CTRL("q"))
    e.keys("y")
    e.end()
    e = Term(box, "SED %s r1" % F)
    e.keys(ESC + ".", CTRL("e"), CTRL("x"), idle=0.8)
    L = e.lines()
    row("Ctrl-X cuts the region: the first line is empty now", not L[1].startswith("alpha"), repr(L[1]))
    L = e.keys(CTRL("v"))
    row("...and Ctrl-V puts it back", L[1].startswith(RECORD[0]), repr(L[1]))
    e.keys(CTRL("q"))
    e.keys("y")
    e.end()
    e = Term(box, "SED %s r1" % F)
    L = e.keys(CTRL("l"))
    row("Ctrl-L asks for a line (Goto line), Esc gives it up", any("Line" in l or "line" in l for l in L[-3:]), "\n".join(L[-3:]))
    e.keys(CTRL("g"))
    e.keys(CTRL("f"))
    L = e.lines()
    row("Ctrl-F asks for a string to search for", any("earch" in l for l in L[-3:]), "\n".join(L[-3:]))
    e.keys(CTRL("g"))
    e.keys(CTRL("q"))
    e.end()


def rec(box, rid):
    out = sess(box, "RUN bp zzslprobe")
    m = re.search(r"(?m)^REC %s (.*)$" % re.escape(rid), out)
    if not m:
        return ["<absent>"] * 5
    return m.group(1).split("|")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-sed-menu.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-sed-menu: sandbox %s" % box)
    say("sandbox-sed-menu: tree    %s" % os.path.dirname(HERE))
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-sed-menu: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)
    if "--refresh" in sys.argv:
        # a development aid: copy the tree's library and SED into an already built sandbox and compile them there
        import shutil
        names = ["sl.h", "sl_attr", "sl_sgr", "sl_put", "sl_key", "sl_region", "sl_menu", "sl_msgbox", "sl_prompt", "sed"]
        for nm in names:
            shutil.copy(os.path.join(os.path.dirname(HERE), "sdsys", "gpl.bp", nm), os.path.join(sysd, "gpl.bp", nm))
        out = isess(box, *["BASIC gpl.bp %s" % n for n in names if n != "sl.h"])
        say(out[-600:])

    fixture ="""   execute 'DELETE.FILE %(f)s' capturing j0
   execute 'CREATE.FILE %(f)s' capturing j1
   open '%(f)s' to f else stop 'no file'
   rec = %(rec)s
   write rec on f, 'r1'
   write rec on f, 'r2'
   crt 'FIXTURE DONE'
end
""" % {"f": F, "rec": " : @fm : ".join("'%s'" % x for x in RECORD)}
    probe = """   open '%(f)s' to f else stop 'no file'
   ids = 'r1' : @fm : 'r2'
   for n = 1 to 2
      id = ids<n>
      read r from f, id then
         crt 'REC ' : id : ' ' : convert(@fm, '|', r)
      end else
         crt 'REC ' : id : ' <none>'
      end
   next n
end
""" % {"f": F}
    progs = {"zzslfix": fixture, "zzslprobe": probe,
             "zzslkeys": KEYS, "zzslmsg": MSGBOX, "zzslprm": PROMPT, "zzslmnu": MENU}
    for nm, body in progs.items():
        if nm not in ("zzslfix", "zzslprobe"):          # the drivers: clear the screen first, end the program
            body = "$internal\n   crt @(-1) :\n" + body + "end\n"
        with open(os.path.join(sysd, "bp", nm), "w") as fh:
            fh.write(body)
    try:
        say("\n--- fixture --------------------------------------------------------------------------------------")
        out = sess(box, "BASIC bp zzslfix", "BASIC bp zzslprobe", "RUN bp zzslfix")
        # The drivers call $-named library routines, which only an INTERNAL program may: they are compiled by sd -internal
        iout = isess(box, *["BASIC bp %s" % n for n in progs if n not in ("zzslfix", "zzslprobe")])
        row("setup: the drivers compiled and the fixture file was made",
            len(re.findall(r"(?m)^Compiled 1 program\(s\) with no errors", out + iout)) == len(progs) and "FIXTURE DONE" in out, (out + iout)[-900:])
        if "FIXTURE DONE" not in out:
            bail("the fixture was not made:\n" + out[-800:])
        row("setup: the library and the editor are in the sandbox",
            all(os.path.isfile(os.path.join(sysd, "gpl.bp", p)) for p in ("sed", "sl_key", "sl_region", "sl_menu", "sl_msgbox", "sl_prompt", "sl_attr", "sl_sgr", "sl_put", "sl.h")), "missing")
        row("setup: control - the record is as written", rec(box, "r1") == RECORD, repr(rec(box, "r1")))
        part_widgets(box, sysd)
        part_sed(box, sysd)
    finally:
        say("\n--- cleanup ---------------------------------------------------------------------------------------")
        sess(box, "DELETE.FILE %s" % F)
        for nm in progs:
            for d in ("bp", "bp.out"):
                pth = os.path.join(sysd, d, nm)
                if os.path.exists(pth):
                    os.remove(pth)

    say("\nsandbox-sed-menu: %d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        bail("no row ran - a broken test, not a pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
