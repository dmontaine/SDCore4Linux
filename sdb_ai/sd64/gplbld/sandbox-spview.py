#!/usr/bin/env python3
#
# sandbox-spview.py - SP.VIEW's record view in the full-screen pages' look (S.99), on a pseudo-terminal.  No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-spview.py <dir> [--build] [--only=look,keys,theme,resize,small,nocolour,gate]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or absent).  Exit 0
# every row passed, 1 a row failed, 2 it could not run.  Stop the sandbox afterwards with sandbox-fromtree.py <dir> stop.  About a minute.
#
# START-HISTORY:
# 2 Nov 26 dm   Written for S.99 (the owner, 2 Nov 26: "sp.view yes ed no").  The sections, each of which may be run alone with --only:
#                 look    the frame at 140 by 43 in the classic theme (the sandbox's sd.conf names no site theme): the bar with the file and
#                         the record at the left and "sp.view  user@account" at the right of row 0, the record from row 1, the prompt line
#                         (row 39), the status line (40, reverse), the border (41) and the function-key row (42), and each row's style
#                 keys    every key SP.VIEW had before still works in the look: the paging keys and their Ctrl and Esc forms, Return, the
#                         letters, the pan across a long line, a key it does not know (a bell, nothing moves), S (the spool form, left
#                         with Q), X answered N and Y (the record on the disk is the evidence), Q answered with another key and with Return,
#                         and the terminal's own colours given back at TCL
#                 theme   SCREENTHEME=blue written to the sandbox's sd.conf for this section only: the bar is the blue theme's
#                 resize  the window made bigger (the frame uses it whole), smaller than 140 by 43 (the old layout, not a refusal), and back
#                 small   a window of 120 by 36 and a session with no terminal (a pipe) keep the old layout exactly: lines from row 0, the
#                         status and prompt lines at the foot of the display, no bar, no key row; and the old keys work there
# 2 Nov 26 dm   After review: theme also has SCREENTHEME=mono (drawn as classic, the debugger's rule); resize ends with TCL in the
#               terminal's own colours (the theme given back after the resizes); and two sections:
#                 nocolour  TERM vt100 at 140 by 43: the look is drawn, no cell has a colour, the status line is reverse
#                 gate      X in an ORDINARY session of a fixture account without voc.edit: the refusal (11405) on the prompt row of the
#                           look, the record still in the VOC (CT in a separate session); the account with voc.edit is the control (the
#                           question is asked).  It uses sandbox-gates.py's prepare() and build_account(), which patch the sandbox's
#                           CPROC (only SDTEST_ADMIN=1 elevates), so it runs last
# END-HISTORY
#
# HOW IT DRIVES SP.VIEW.  A directory file zzspvf is made in the sandbox's SDSYS account and its records are written on the disk:
# `big`, 100 numbered lines of which line 5 is 300 characters long, and two short ones for the delete rows.  SP.VIEW is run on a
# pseudo-terminal (ptydrive.py) and the screen is read from the emulator in termscreen.py: its text and the colours of its cells.  The
# status line's own words (sysmsg 7138, "top = N, left = M") are the evidence of where SP.VIEW is in the record; a row whose session never
# reached SP.VIEW fails, it does not pass.

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ptydrive import PtySession  # noqa: E402

TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
FILE = "zzspvf"
SECTIONS = ("look", "keys", "theme", "resize", "small", "nocolour", "gate")
passed = failed = 0

COLS, ROWS = 140, 43
PROMPT, STATUS, BORDER, KEYS = 39, 40, 41, 42
PER_PAGE = ROWS - 5                                  # 38 lines of the record, rows 1 to 38
KEYTEXT = "PgDn next  PgUp previous  Home top  End bottom  Left scroll left  Right scroll right  S spool  X delete  Q quit"
RET, ESC = "\r", "\x1b"
PGDN, PGUP, HOME, END = "\x1b[6~", "\x1b[5~", "\x1b[1~", "\x1b[4~"           # xterm's terminfo, as sandbox-ide.py sends them
UP, DOWN, LEFT, RIGHT = "\x1bOA", "\x1bOB", "\x1bOD", "\x1bOC"
LONG5 = "line 005 " + "A" * 111 + "B" * 140 + "C" * 40          # 300 characters: the 121st on is the B part


def say(s=""):
    print(s, flush=True)


def row(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        say("  [PASS] " + name)
    else:
        failed += 1
        say("  [FAIL] " + name + ("   <- " + str(detail)[:400] if detail else ""))


def bail(msg):
    say("sandbox-spview: CANNOT RUN - " + msg)
    sys.exit(2)


def sess(box, *cmds):
    say("    > [pipe] " + " | ".join(repr(c) for c in cmds))
    # SDTEST_ADMIN=1: after the gate section has patched CPROC (sandbox-gates.py's prepare()) only it elevates, and the cleanup's DELETE.FILE
    # needs the administrator; before the patch it changes nothing
    p = subprocess.run([sys.executable, TOOL, box, "sess", os.path.join(box, "user_accounts")] + list(cmds),
                       capture_output=True, text=True, errors="replace", timeout=300, env=dict(os.environ, SDTEST_ADMIN="1"))
    out = ANSI.sub("", p.stdout + p.stderr)
    return out.split(":TERM 200,9999", 1)[-1]


class Term:
    def __init__(self, box, cmd, cols=COLS, rows=ROWS, term="xterm", account=None):
        say("    > [pty %dx%d, TERM %s%s] %s" % (cols, rows, term, ", -a" + account if account else "", cmd))
        env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"), TERM=term)
        env.pop("SDTEST_ADMIN", None)
        env.pop("SSH_CONNECTION", None)
        argv = [os.path.join(box, "sys", "bin", "sd")] + (["-a" + account] if account else [])
        cwd = os.path.join(box, "user_accounts", account) if account else os.path.join(box, "user_accounts")
        self.s = PtySession(argv, cwd, env, cols, rows)
        self.s.settle(1.5)
        self.s.type("TERM %s\r" % term, idle=0.8)
        if term != "xterm":
            self.s.type("TERM %d,%d\r" % (cols, rows), idle=0.8)
        self.s.type(cmd + "\r", idle=2.0)

    def keys(self, *chunks, idle=0.6):
        for c in chunks:
            self.s.type(c, idle=idle)
        return self.lines()

    def lines(self):
        return self.s.screen.lines()

    def style(self, r, c):
        return self.s.screen.style(r, c)

    def resize(self, cols, rows):
        say("    > [resize to %dx%d]" % (cols, rows))
        self.s.resize(cols, rows, idle=1.8)
        return self.lines()

    def end(self):
        self.s.type("\rOFF\r", idle=0.5)
        self.s.finish()


def top(L):
    """(top, left) from the status line's words wherever it is on the screen, or None when SP.VIEW's status line is not shown"""
    for l in L:
        m = re.search(r"top = (\d+), left = (\d+)", l)
        if m:
            return int(m.group(1)), int(m.group(2))
    return None


def isrule(line, width):
    s = line.rstrip()
    return len(s) == width and set(s) <= set("-+")


def onscreen(L, text):
    return any(text in l for l in L)


def write_records(fdir):
    os.makedirs(fdir, exist_ok=True)
    lines = []
    for n in range(1, 101):
        lines.append(LONG5 if n == 5 else "line %03d of the record big" % n)
    with open(os.path.join(fdir, "big"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    for nm in ("del1", "del2"):
        with open(os.path.join(fdir, nm), "w") as fh:
            fh.write("a record to delete\n")


def sec_look(box, conf_note):
    say("\n--- look: the frame at 140 by 43, classic theme (%s) ---------------------------------------------" % conf_note)
    t = Term(box, "SP.VIEW %s big" % FILE)
    L = t.lines()
    row("setup: SP.VIEW is up on the record (its status line says top = 1, left = 1)", top(L) == (1, 1), "\n".join(L[-5:]))
    row("the bar on row 0 names the file and the record at its left", L[0].startswith("%s  big" % FILE), repr(L[0][:40]))
    row("...and 'sp.view  user@account' at its right end, as the pages have their app name", re.search(r"sp\.view  \S+@\S+$", L[0]) is not None
        and len(L[0].rstrip()) == COLS - 1, repr(L[0][-40:]))          # the tag ends with a blank, as SED's and the IDE's do
    row("the bar is in the bar style of the classic theme (black on white), at the left and under the tag",
        t.style(0, 2)[:2] == (0, 7) and t.style(0, COLS - 3) == t.style(0, 2), repr((t.style(0, 2), t.style(0, COLS - 3))))
    row("the record starts on row 1, under the bar", L[1].startswith("line 001 ") and L[2].startswith("line 002 "), repr(L[1][:30]))
    row("the record's lines are in the text style (white on blue), not the bar's", t.style(1, 2)[1] == 4 and t.style(1, 2) != t.style(0, 2),
        repr(t.style(1, 2)))
    row("38 lines to a page: row 38 is line 038 and row 39 is the prompt line, not line 039",
        L[38].startswith("line 038 ") and not L[PROMPT].startswith("line 039"), repr((L[38][:20], L[PROMPT][:20])))
    row("the prompt line (row 39) has SP.VIEW's prompt, in the bar style", L[PROMPT].startswith("Next/Right/Top/Bottom/Spool/X-delete/Quit:")
        and t.style(PROMPT, 0)[:2] == (0, 7), repr((L[PROMPT][:60], t.style(PROMPT, 0))))
    row("the status line (row 40) says the record, its lines and where the view is, in reverse video",
        L[STATUS].startswith("big (100 lines, top = 1, left = 1)") and "r" in t.style(STATUS, 2)[2], repr((L[STATUS][:50], t.style(STATUS, 2))))
    row("the border (row 41) is a line across the window", isrule(L[BORDER], COLS), repr(L[BORDER][:30]))
    row("the function-key row (row 42) lists the keys SP.VIEW acts on, in the bar style", L[KEYS].rstrip() == KEYTEXT
        and t.style(KEYS, 2)[:2] == (0, 7), repr((L[KEYS][:120], t.style(KEYS, 2))))
    row("a long line is cut at the window's edge (line 5 shows its first 140 characters)", L[5] == LONG5[:COLS], repr(L[5][-20:]))
    t.keys("q", RET, idle=1.0)
    t.end()


def sec_keys(box, fdir):
    say("\n--- keys: every key SP.VIEW had still works in the look ------------------------------------------------")
    t = Term(box, "SP.VIEW %s big" % FILE)
    row("setup: SP.VIEW is up at top = 1", top(t.lines()) == (1, 1), "\n".join(t.lines()[-4:]))
    nxt = PER_PAGE + 1
    last = 100 - ((100 - 1) % PER_PAGE)
    steps = [
        ("PgDn goes a page on", [PGDN], (nxt, 1)),
        ("PgUp goes a page back", [PGUP], (1, 1)),
        ("N goes a page on", ["n"], (nxt, 1)),
        ("P goes a page back", ["p"], (1, 1)),
        ("Down goes a page on (D)", [DOWN], (nxt, 1)),
        ("Up goes a page back (U)", [UP], (1, 1)),
        ("D goes a page on", ["d"], (nxt, 1)),
        ("U goes a page back", ["u"], (1, 1)),
        ("Return goes a page on", [RET], (nxt, 1)),
        ("Esc-Z goes a page back", [ESC + "z"], (1, 1)),
        ("Ctrl-V goes a page on", ["\x16"], (nxt, 1)),
        ("Esc-V goes a page back", [ESC + "v"], (1, 1)),
        ("Ctrl-N goes a page on", ["\x0e"], (nxt, 1)),
        ("Ctrl-P goes a page back", ["\x10"], (1, 1)),
        ("End goes to the last page", [END], (last, 1)),
        ("Home goes to the top", [HOME], (1, 1)),
        ("B goes to the last page", ["b"], (last, 1)),
        ("T goes to the top", ["t"], (1, 1)),
        ("Esc-> goes to the last page", [ESC + ">"], (last, 1)),
        ("Esc-< goes to the top", [ESC + "<"], (1, 1)),
        ("Ctrl-Z goes a page back from the second page", ["\x16", "\x1a"], (1, 1)),
        ("Right moves the view across by the window less 20 (left = 121)", [RIGHT], (1, COLS - 19)),
        ("Left moves it back", [LEFT], (1, 1)),
        ("R moves across", ["r"], (1, COLS - 19)),
        ("L moves back", ["l"], (1, 1)),
        ("Ctrl-F moves across", ["\x06"], (1, COLS - 19)),
        ("Ctrl-B moves back", ["\x02"], (1, 1)),
    ]
    for name, ks, want in steps:
        L = t.keys(*ks)
        row("%s: %s" % (name, "top = %d, left = %d" % want), top(L) == want, repr((top(L), L[1][:24])))
    L = t.keys("\x16")
    row("...and a page on, the first row under the bar is line %03d" % nxt, L[1].startswith("line %03d " % nxt), repr(L[1][:20]))
    L = t.keys(HOME, RIGHT)
    row("across: line 5 now shows from its 121st character (the B part) on row 5", L[5].startswith("B" * 10), repr(L[5][:20]))
    t.keys(LEFT)
    mark = len(t.s.raw)
    L = t.keys("z")
    row("a key SP.VIEW does not know moves nothing (z: still top = 1, left = 1)", top(L) == (1, 1) and L[KEYS].rstrip() == KEYTEXT, repr(top(L)))
    row("control: the bell for it was sent", b"\x07" in t.s.raw[mark:], repr(t.s.raw[mark:mark + 60]))

    L = t.keys("s", idle=1.0)
    row("S opens the spool form (Preparing to print ... Printer)", onscreen(L, "Preparing to print") and onscreen(L, "Printer"), "\n".join(x for x in L if x.strip())[:300])
    L = t.keys(RET, RET, idle=0.8)
    row("...which asks 'OK to print' after the printer and the numbering", onscreen(L, "OK to print"), "\n".join(x for x in L if x.strip())[-300:])
    L = t.keys("q", idle=1.0)
    if onscreen(L, "OK to print") and not onscreen(L, "big (100 lines"):
        L = t.keys(RET, idle=1.0)
    row("...Q leaves it and the frame is drawn again: bar, record, key row", L[1].startswith("line 001 ") and L[KEYS].rstrip() == KEYTEXT
        and L[0].startswith(FILE), "\n".join(L[:2] + L[-3:]))

    L = t.keys("q", idle=0.8)
    row("Q asks first, on the prompt line (Press return to quit)", "return to quit" in L[PROMPT].lower(), repr(L[PROMPT][:60]))
    L = t.keys("x", idle=0.8)
    row("...a key that is not Return goes on with the record (the status line is back)", top(L) == (1, 1) and L[PROMPT].startswith("Next/"), repr(L[PROMPT][:60]))
    L = t.keys("q", RET, idle=1.2)
    row("...Q and Return leave SP.VIEW: the frame is gone", not any(l.startswith(FILE + "  big") for l in L) and top(L) is None,
        "\n".join(x for x in L if x.strip())[-200:])
    t.s.type("WHO\r", idle=0.8)
    L = t.lines()
    w = [(i, l) for i, l in enumerate(L) if l.strip() and not l.startswith(":") and "WHO" not in l]
    row("...and TCL is in the terminal's own colours again (the theme was given back)",
        w and t.style(w[-1][0], 0)[:2] == (None, None), repr([(i, l[:30], t.style(i, 0)) for i, l in w[-2:]]))
    t.end()

    p1 = os.path.join(fdir, "del1")
    t = Term(box, "SP.VIEW %s del1" % FILE)
    L = t.keys("x", idle=0.8)
    row("X asks on the prompt line (row 39) whether to delete the record", "Delete del1 from %s" % FILE in L[PROMPT], repr(L[PROMPT][:70]))
    L = t.keys("n", idle=0.8)
    row("...N keeps it: the record is still on the disk and the view is back", os.path.exists(p1) and top(L) == (1, 1), repr((os.path.exists(p1), top(L))))
    L = t.keys("x", "y", idle=1.0)
    row("...X and Y delete it: the record is gone from the disk and SP.VIEW has left", not os.path.exists(p1) and top(L) is None,
        repr((os.path.exists(p1), "\n".join(x for x in L if x.strip())[-200:])))
    t.end()


def sec_theme(box, conf, original_conf):
    say("\n--- theme: SCREENTHEME=blue in the sandbox's sd.conf (this section only) --------------------------------")
    with open(conf, "w") as fh:
        fh.write(original_conf.rstrip("\n") + "\nSCREENTHEME=blue\n")
    try:
        t = Term(box, "SP.VIEW %s big" % FILE)
        L = t.lines()
        row("setup: SP.VIEW is up", top(L) == (1, 1), "\n".join(L[-4:]))
        row("the bar is the blue theme's (black on cyan), not classic's (black on white)", t.style(0, 2)[:2] == (0, 6), repr(t.style(0, 2)))
        row("the key row is the bar's style too", t.style(KEYS, 2) == t.style(0, 2), repr((t.style(KEYS, 2), t.style(0, 2))))
        row("the record's lines are in the blue theme's text style (white on black), not the bar's and not the terminal's own",
            t.style(1, 2)[:2] == (7, 0) and t.style(1, 2) != t.style(0, 2), repr(t.style(1, 2)))
        row("the status line is in reverse video", "r" in t.style(STATUS, 2)[2], repr(t.style(STATUS, 2)))
        t.keys("q", RET, idle=1.0)
        t.end()
        # 2 Nov 26: SCREENTHEME=mono is taken as no site theme (the debugger's rule, documented): the classic theme is drawn
        say("    (SCREENTHEME=mono in the sandbox's sd.conf)")
        with open(conf, "w") as fh:
            fh.write(original_conf.rstrip("\n") + "\nSCREENTHEME=mono\n")
        t = Term(box, "SP.VIEW %s big" % FILE)
        L = t.lines()
        row("setup: SP.VIEW is up with SCREENTHEME=mono", top(L) == (1, 1), "\n".join(L[-4:]))
        row("SCREENTHEME=mono draws the classic theme, as the debugger does: the bar black on white, the record white on blue",
            t.style(0, 2)[:2] == (0, 7) and t.style(1, 2)[1] == 4, repr((t.style(0, 2), t.style(1, 2))))
        t.keys("q", RET, idle=1.0)
        t.end()
    finally:
        with open(conf, "w") as fh:
            fh.write(original_conf)


def sec_resize(box):
    say("\n--- resize: bigger (used whole), smaller than 140 by 43 (the old layout), and back ----------------------")
    t = Term(box, "SP.VIEW %s big" % FILE)
    row("setup: SP.VIEW is up in the look at 140 by 43", top(t.lines()) == (1, 1) and t.lines()[KEYS].rstrip() == KEYTEXT, "\n".join(t.lines()[-3:]))
    L = t.resize(160, 50)
    row("a window of 160 by 50: the key row is the last row (49) and the bar's tag ends at column 159",
        len(L) == 50 and L[49].rstrip() == KEYTEXT and re.search(r"sp\.view  \S+@\S+$", L[0]) is not None and len(L[0].rstrip()) == 159,
        repr((len(L), L[-1][:40], L[0][-30:])))
    row("...and the status line is row 47, the prompt line row 46, 45 lines of the record (row 45 is line 045)",
        L[47].startswith("big (100 lines, top = 1,") and L[46].startswith("Next/") and L[45].startswith("line 045 "),
        repr((L[47][:30], L[46][:20], L[45][:20])))
    L = t.keys(PGDN)
    row("...a page on is 45 lines: top = 46", top(L) == (46, 1), repr(top(L)))
    L = t.keys(HOME)
    L = t.resize(100, 30)
    row("a window of 100 by 30, smaller than 140 by 43: the old layout, not a refusal - line 1 on row 0, no bar, no key row",
        L[0].startswith("line 001 ") and not onscreen(L, "sp.view  ") and not onscreen(L, "PgDn next"), "\n".join(L[:2] + L[-3:]))
    row("...the status line is row 28 and the prompt row 29 (the foot of the display), in reverse video as before",
        L[28].startswith("big (100 lines, top = 1,") and L[29].startswith("Next/") and "r" in t.style(28, 2)[2], repr((L[28][:30], L[29][:20], t.style(28, 2))))
    L = t.keys(PGDN)
    row("...and the keys work there: a page on is 26 lines (top = 27)", top(L) == (27, 1), repr(top(L)))
    L = t.keys(HOME)
    L = t.resize(COLS, ROWS)
    row("back to 140 by 43: the look again (bar, record from row 1, key row on row 42)",
        L[0].startswith(FILE) and L[1].startswith("line 001 ") and L[KEYS].rstrip() == KEYTEXT, "\n".join(L[:2] + L[-2:]))
    L = t.keys("q", RET, idle=1.2)
    # 2 Nov 26: the theme is given back after the look was left and taken again by the resizes (theme.out)
    row("...Q and Return after the resizes: SP.VIEW has left, and TCL is in the terminal's own colours (row 0 and a cell mid-screen)",
        top(L) is None and t.style(0, 0)[:2] == (None, None) and t.style(20, 60)[:2] == (None, None),
        repr((top(L), t.style(0, 0), t.style(20, 60), L[0][:40])))
    t.end()


def sec_small(box):
    say("\n--- small: a window of 120 by 36, and a session with no terminal, keep the old layout ----------------------")
    t = Term(box, "SP.VIEW %s big" % FILE, 120, 36)
    L = t.lines()
    row("setup: SP.VIEW is up in a 120 by 36 window (not refused)", top(L) == (1, 1), "\n".join(L[-4:]))
    row("the old layout: line 1 on row 0, no bar, no app name, no key row", L[0].startswith("line 001 ") and not onscreen(L, "sp.view  ")
        and not onscreen(L, "PgDn next"), "\n".join(L[:2] + L[-3:]))
    row("the status line on row 34 and the prompt on row 35, both in reverse video, as before",
        L[34].startswith("big (100 lines, top = 1,") and L[35].startswith("Next/") and "r" in t.style(34, 2)[2] and "r" in t.style(35, 2)[2],
        repr((L[34][:30], L[35][:20], t.style(34, 2), t.style(35, 2))))
    row("the record is in the terminal's own colours (no theme drawn)", t.style(0, 2)[:2] == (None, None), repr(t.style(0, 2)))
    L = t.keys(PGDN)
    row("PgDn goes a page of 32 lines on (top = 33)", top(L) == (33, 1), repr(top(L)))
    L = t.keys(HOME, RIGHT)
    row("Right moves across by 100 (left = 101: line 5, on the first page, is longer than the window)", top(L) == (1, 101), repr(top(L)))
    t.keys("q", RET, idle=1.0)
    t.end()
    out = sess(box, "SP.VIEW %s big" % FILE, "t", "q", "")
    row("a session with no terminal (a pipe): SP.VIEW shows its status line and no frame", "top = 1," in out and "sp.view  " not in out
        and "PgDn next" not in out, out[-300:])


def sec_nocolour(box):
    say("\n--- nocolour: TERM vt100 (no colours, but cup) at 140 by 43 - the look, in mono ------------------------------")
    t = Term(box, "SP.VIEW %s big" % FILE, term="vt100")
    L = t.lines()
    row("setup: SP.VIEW is up on a vt100 (its status line says top = 1, left = 1)", top(L) == (1, 1), "\n".join(L[-5:]))
    row("the look is drawn: the bar on row 0, the record from row 1, the key row on row 42",
        L[0].startswith("%s  big" % FILE) and L[1].startswith("line 001 ") and L[KEYS].rstrip() == KEYTEXT, "\n".join(L[:2] + L[-2:]))
    cells = [(0, 2), (1, 2), (PROMPT, 0), (STATUS, 2), (BORDER, 2), (KEYS, 2)]
    row("no cell has a colour (the theme stays mono on a terminal with no colour): the bar, the record, the prompt, the status, the border, the keys",
        all(t.style(r, c)[:2] == (None, None) for r, c in cells), repr([t.style(r, c) for r, c in cells]))
    row("...and the status line is in reverse video", "r" in t.style(STATUS, 2)[2], repr(t.style(STATUS, 2)))
    t.keys("q", RET, idle=1.0)
    t.end()


def sec_gate(box):
    """X on a record of a kind whose edit gate the account does not hold: the refusal (11405) on the prompt row of the look, the record
    still on the disk.  Ordinary sessions in fixture accounts made the way sandbox-gates.py makes them (its prepare() patches the sandbox's
    CPROC so that only SDTEST_ADMIN=1 elevates, which is why this section runs last)."""
    import importlib.util
    say("\n--- gate: X in the look, in an account without voc.edit (refused, 11405) and with it (the question, the control) -------")
    spec = importlib.util.spec_from_file_location("sandbox_gates", os.path.join(HERE, "sandbox-gates.py"))
    g = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g)
    g.BOX = box
    g.SYS = os.path.join(box, "sys")
    g.SD = os.path.join(g.SYS, "bin", "sd")
    g.prepare()
    paths = {}
    for name, voc in (("zzspoff", "no"), ("zzspon", "yes")):
        g.EXTRA_FIXTURES[name] = ("no", "no")
        paths[name] = g.build_account(name)
        g.reg_write(name, [paths[name], "", g.GROUP, "", "", "", "no", "no", "", voc, "no", "no"])
    g.put(os.path.join(g.SYS, "bp", "zzspfix"), "\n".join([
        "$internal",
        "   for each a in '%s':@fm:'%s'" % (paths["zzspoff"], paths["zzspon"]),
        "      openpath a:'/voc' to v else crt 'SPFIX no voc ':a ; stop",
        "      write 'X':@fm:'a voc record for sp.view' to v, 'zzspvx'",
        "      close v",
        "   next a",
        "   crt 'SPFIX done'",
        "end", ""]))
    out = g.adm(["BASIC bp zzspfix", "RUN bp zzspfix"], internal=True)
    row("setup: the VOC record zzspvx was written in both fixture accounts", g.has(out, r"^SPFIX done$"), repr(out[-4:]))
    msg = "The VOC can only be changed by an account that has voc.edit"

    def on_disk(name):
        return g.has(g.plain(name, ["CT VOC zzspvx"]), r"a voc record for sp\.view")

    t = Term(box, "SP.VIEW VOC zzspvx", account="zzspoff")
    L = t.lines()
    row("setup: SP.VIEW is up in the look in zzspoff (voc.edit off)", top(L) == (1, 1) and L[KEYS].rstrip() == KEYTEXT, "\n".join(L[-5:]))
    L = t.keys("x", idle=1.0)
    row("zzspoff: X is refused on the prompt row (row 39) with the gate's own words (11405), and no question is asked",
        msg in L[PROMPT] and not onscreen(L, "Delete zzspvx") and L[KEYS].rstrip() == KEYTEXT, repr(L[PROMPT][:120]))
    L = t.keys(" ", idle=1.0)
    row("...a key goes back to the record: the status line and the prompt are back", top(L) == (1, 1) and "Quit:" in L[PROMPT],
        repr(L[PROMPT][:80]))
    t.keys("q", RET, idle=1.0)
    t.end()
    row("...and zzspvx is still in zzspoff's VOC (read by CT in a separate session)", on_disk("zzspoff"), "")

    t = Term(box, "SP.VIEW VOC zzspvx", account="zzspon")
    L = t.keys("x", idle=1.0)
    row("control: in zzspon (voc.edit on) X asks the question on the prompt row, and the refusal is not shown",
        "Delete zzspvx from VOC" in L[PROMPT] and not onscreen(L, msg), repr(L[PROMPT][:80]))
    t.keys("n", idle=0.8)
    t.keys("q", RET, idle=1.0)
    t.end()
    row("...answered N, zzspvx is still in zzspon's VOC", on_disk("zzspon"), "")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-spview.py <dir> [--build] [--only=%s]" % ",".join(SECTIONS))
    only = list(SECTIONS)
    for a in sys.argv[1:]:
        if a.startswith("--only="):
            only = [s for s in a.split("=", 1)[1].split(",") if s]
            bad = [s for s in only if s not in SECTIONS]
            if bad or not only:
                bail("unknown section(s) %r (known: %s)" % (bad, ",".join(SECTIONS)))
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-spview: sandbox %s, keyset %s, sections %s" % (box, os.environ.get("SDBOX_KEYSET", "0"), ",".join(only)))
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-spview: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    conf = os.path.join(box, "sd.conf")
    with open(conf) as fh:
        original_conf = fh.read()
    if re.search(r"(?m)^SCREENTHEME=", original_conf):
        bail("the sandbox's sd.conf already has a SCREENTHEME line, so the classic rows cannot be measured")
    fdir = os.path.join(sysd, FILE)
    try:
        say("\n--- setup -------------------------------------------------------------------------------------------")
        if not os.path.isdir(fdir):
            out = sess(box, "CREATE.FILE %s DIRECTORY" % FILE)
            row("setup: the directory file %s was made in the SDSYS account" % FILE, os.path.isdir(fdir), out[-200:])
        write_records(fdir)
        if "look" in only:
            sec_look(box, "no SCREENTHEME line")
        if "keys" in only:
            sec_keys(box, fdir)
        if "theme" in only:
            sec_theme(box, conf, original_conf)
        if "resize" in only:
            sec_resize(box)
        if "small" in only:
            sec_small(box)
        if "nocolour" in only:
            sec_nocolour(box)
        if "gate" in only:
            sec_gate(box)               # last: its preparation patches the sandbox's CPROC
    finally:
        say("\n--- cleanup ---------------------------------------------------------------------------------------")
        with open(conf, "w") as fh:
            fh.write(original_conf)
        out = sess(box, "DELETE.FILE %s" % FILE)
        say("    %s removed: %s" % (FILE, not os.path.exists(fdir)))

    say("\nsandbox-spview: %d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        bail("no row ran - a broken test, not a pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
