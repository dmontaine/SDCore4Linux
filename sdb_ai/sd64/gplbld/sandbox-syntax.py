#!/usr/bin/env python3
#
# sandbox-syntax.py - SED's syntax colour, on a pseudo-terminal.  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-syntax.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or
# absent).  Exit 0 every row passed, 1 a row failed, 2 it could not run.  Only one private SD can exist on a machine
# (shared memory keys 0x53434c91/92): stop the sandbox afterwards with sandbox-fromtree.py <dir> stop.
#
# START-HISTORY:
# 13 Oct 26 dm  Written with the wiring of $sl_syntax into SED.
# 18 Oct 26 dm  SED is 140 by 42 (terminal 140x42, phase 2): the window here is 140 by 42.
# END-HISTORY
#
# HOW IT DRIVES SED.  On a PSEUDO-TERMINAL (ptydrive.py), the screen read from the emulator in termscreen.py, whose
# style(row, col) is the foreground, the background and the flags of a cell.  A row compares a cell with another or with
# what the same cell was before a key: no colour is assumed to be one in particular, because the theme may change.  Each
# row that turns something on has a control row (the same screen before), and a record that never reached the screen
# makes its rows fail, not pass.

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
F = "zzsy" + RUN                                    # the fixture file
passed = failed = 0

RIGHT, F10, RET, DEL = "\x1bOC", "\x1b[21~", "\r", "\x1b[3~"
ESC_X = "\x1bx"

C_SRC = ["/* demo.c - a comment */", "#include <stdio.h>", "", "static int count = 0;", "int main(void)", "{",
         "    printf(\"hi\\n\");", "    return count;", "}"]
OPEN_C = ["/* starts here", "int x = 1;", "ends here */", "int y = 2;", "return y;"]
BAS = ["* a comment line", "   crt 'text' : 12", "   for i = 1 to 3", "   next i", "end"]


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
    say("sandbox-syntax: CANNOT RUN - " + msg)
    sys.exit(2)


def sess(box, *cmds):
    say("    > " + " | ".join(cmds))
    p = subprocess.run([sys.executable, TOOL, box, "sess", os.path.join(box, "user_accounts")] + list(cmds),
                       capture_output=True, text=True, errors="replace", timeout=600)
    out = ANSI.sub("", p.stdout + p.stderr)
    return out.split(":TERM 200,9999", 1)[-1]


class Term:
    def __init__(self, box, cmd, cols=140, rows=42, term="xterm"):       # SED is 140 by 42 always (18 Oct 26; 120 by 36 on 13 Oct)
        env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"), TERM="xterm")
        self.s = PtySession([os.path.join(box, "sys", "bin", "sd")], os.path.join(box, "user_accounts"), env, cols, rows)
        self.s.settle(1.0)
        self.s.type("TERM %s\r" % term)
        self.s.type("TERM %d,%d\r" % (cols, rows))
        self.s.type(cmd + "\r", idle=1.5)

    def keys(self, *chunks, idle=0.6):
        for c in chunks:
            self.s.type(c, idle=idle)
        return self.lines()

    def lines(self):
        return self.s.screen.lines()

    def fg(self, r, c):
        return self.s.screen.style(r, c)[0]

    def style(self, r, c):
        return self.s.screen.style(r, c)

    def command(self, text):
        self.keys(ESC_X)
        L = self.keys(text + "\r", idle=1.2)
        if os.environ.get("SYDEBUG"):
            say("    [screen after %s]" % text)
            for l in L[:12]:
                say("      | " + l.rstrip())
        return L

    def end(self):
        self.s.type("\x11", idle=0.5)                 # Ctrl-Q
        self.s.type("\rOFF\r", idle=0.5)
        self.s.finish()


def where(L, text):
    for r, l in enumerate(L):
        c = l.find(text)
        if c >= 0:
            return r, c
    return None


def coloured(t, r, c0, n):
    """True if every one of the n cells from (r, c0) has a foreground colour of its own."""
    return all(t.fg(r, c0 + k) is not None for k in range(n))


def plain(t, r, c0, n):
    return all(t.fg(r, c0 + k) is None for k in range(n))


def lit(s):
    return "'" + s.replace("'", "''") + "'"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-syntax.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-syntax: sandbox %s" % box)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-syntax: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    prog = "   execute 'DELETE.FILE %s' capturing j0\n   execute 'CREATE.FILE %s' capturing j1\n   open '%s' to f else stop 'no file'\n" % (F, F, F)
    for rid, lines in (("demo.c", C_SRC), ("open.c", OPEN_C), ("prog.b", BAS), ("note.txt", ["plain text", "int main"])):
        prog += "   rec = %s\n   write rec on f, '%s'\n" % (" : @fm : ".join(lit(l) for l in lines), rid)
    prog += "   crt 'FIXTURE DONE'\nend\n"
    with open(os.path.join(sysd, "bp", "zzsyfix"), "w") as fh:
        fh.write(prog)
    try:
        say("\n--- fixture --------------------------------------------------------------------------------------")
        out = sess(box, "BASIC bp zzsyfix", "RUN bp zzsyfix")
        row("setup: the fixture file was made with four records", "FIXTURE DONE" in out, out[-600:])
        if "FIXTURE DONE" not in out:
            bail("the fixture was not made:\n" + out[-800:])

        say("\n--- colour is off until it is asked for ---------------------------------------------------------")
        t = Term(box, "SED %s demo.c" % F)
        L = t.keys()
        p = where(L, "static int count")
        row("setup: the record is on the screen", p is not None, "\n".join(L[:12]))
        r0, c0 = p if p else (4, 0)
        row("by default nothing on the screen has a colour: the keyword, the comment, the string are as plain as the rest",
            plain(t, r0, c0, 6) and plain(t, 1, 0, 24) and all(t.fg(r, c) is None for r in range(1, 10) for c in range(0, 40)), "")
        L = t.keys(F10, RIGHT, RIGHT, RIGHT, RIGHT, RIGHT)
        sc = where(L, "Syntax colour")
        row("control: the Tools menu has the item, not checked (a blank before it)", sc is not None and L[sc[0]][sc[1] - 1] == " ", "\n".join(L[:20]))
        t.keys("\x1b", idle=1.0)

        say("\n--- SYNTAX turns it on, per language -----------------------------------------------------------")
        L = t.command("SYNTAX ON")
        p = where(L, "static int count")
        r0, c0 = p if p else (4, 0)
        row("the comment line is coloured (each of its cells has a foreground)", coloured(t, 1, 0, 24), repr([t.fg(1, c) for c in range(0, 24, 4)]))
        row("the keyword static is coloured, the variable count (after it and int) is not",
            coloured(t, r0, c0, 6) and plain(t, r0, c0 + 11, 5), repr([t.fg(r0, c0 + k) for k in range(0, 18, 2)]))
        row("the directive #include is coloured, and a keyword and a comment differ in colour",
            coloured(t, 2, 0, 8) and t.fg(1, 0) != t.fg(r0, c0), repr((t.fg(2, 0), t.fg(1, 0), t.fg(r0, c0))))
        sr = where(L, "printf")
        row("a string is coloured: the quoted text after printf", sr is not None and t.fg(sr[0], sr[1] + 8) is not None, repr(sr))
        L = t.keys(F10, RIGHT, RIGHT, RIGHT, RIGHT, RIGHT)
        sc = where(L, "Syntax colour")
        row("the Tools menu shows it checked: a * before Syntax colour", sc is not None and L[sc[0]][sc[1] - 1] == "*", "\n".join(L[:20]))
        t.keys("\x1b", idle=1.0)
        L = t.command("SYNTAX OFF")
        row("SYNTAX OFF takes the colour away again: the same cells are plain", plain(t, 1, 0, 24) and plain(t, r0, c0, 6), repr(t.fg(1, 0)))
        L = t.command("SYNTAX LIGHT")
        light = t.fg(r0, c0)
        L = t.command("SYNTAX DARK")
        row("LIGHT and DARK are different themes: the keyword's colour differs between them", light is not None and t.fg(r0, c0) is not None and light != t.fg(r0, c0), repr((light, t.fg(r0, c0))))
        t.end()

        say("\n--- a comment that runs on, and a change that recolours the rows below ---------------------------")
        t = Term(box, "SED %s open.c" % F)
        t.keys()
        L = t.command("SYNTAX ON")
        com = t.fg(1, 0)
        row("the opening line of a comment is coloured", com is not None, repr(com))
        row("so are the lines the comment runs through, in the same colour: 'int x = 1;' and 'ends here */'",
            t.fg(2, 0) == com and t.fg(3, 0) == com and t.fg(2, 4) == com, repr((t.fg(2, 0), t.fg(3, 0))))
        row("control: the line after the comment is code: its keyword is coloured otherwise", t.fg(4, 0) is not None and t.fg(4, 0) != com, repr(t.fg(4, 0)))
        L = t.keys("\x04", "\x04")                     # Ctrl-D twice: the /* is gone, line 1 is no longer a comment
        row("deleting the /* of line 1 recolours the rows below: 'int x = 1;' is code now, not comment", t.fg(2, 0) != com, repr((t.fg(2, 0), com, L[1:4])))
        t.end()

        say("\n--- the language comes from the record id -----------------------------------------------------")
        t = Term(box, "SED %s prog.b" % F)
        t.keys()
        L = t.command("SYNTAX ON")
        row("an SD BASIC record: the * comment is coloured and the keyword for is coloured", coloured(t, 1, 0, 16) and coloured(t, 3, 3, 3), repr((t.fg(1, 0), t.fg(3, 3))))
        t.end()
        t = Term(box, "SED %s note.txt" % F)
        t.keys()
        L = t.command("SYNTAX ON")
        row("a record whose id says no language (note.txt) is left plain, whatever it says: 'int main'", plain(t, 1, 0, 10) and plain(t, 2, 0, 8), repr((t.fg(1, 0), t.fg(2, 0))))
        t.end()

        say("\n--- the window split in two ------------------------------------------------------------------")
        t = Term(box, "SED %s demo.c" % F)
        t.keys()
        t.command("SYNTAX ON")
        L = t.keys(F10, RIGHT, RIGHT, RIGHT, RIGHT, RET, idle=1.0)     # the Window menu's first item is Split window
        n = sum(1 for l in L if "static int count" in l)
        rows = [i for i, l in enumerate(L) if "static int count" in l]
        row("Window, Split window: the record is on the screen twice", n == 2, "\n".join(L[:30]))
        row("both windows are coloured: the keyword static in each", n == 2 and all(coloured(t, r, L[r].find("static"), 6) for r in rows), repr(rows))
        t.end()

        say("\n--- a terminal that cannot show colour, and the theme after SED ---------------------------------")
        t = Term(box, "SED %s demo.c" % F, term="vt100")
        t.keys()
        L = t.command("SYNTAX ON")
        row("on a vt100 the colour is refused and the text stays plain", plain(t, 1, 0, 24), repr(t.fg(1, 0)))
        row("...and the message says so (this terminal cannot show colour)", any("cannot show colour" in l for l in L), "\n".join(l for l in L if l.strip()))
        t.end()
        t = Term(box, "SED %s demo.c" % F)
        t.keys()
        t.command("SYNTAX ON")
        t.s.type("\x11", idle=1.0)
        L = t.lines()
        last = max(i for i, l in enumerate(L) if l.strip())
        row("after SED has ended the theme is mono again: the next prompt is as plain as before", plain(t, last, 0, 1), repr((last, L[last], t.fg(last, 0))))
        t.s.type("\rOFF\r", idle=0.5)
        t.s.finish()
    finally:
        say("\n--- cleanup ---------------------------------------------------------------------------------------")
        sess(box, "DELETE.FILE %s" % F)
        for d in ("bp", "bp.out"):
            pth = os.path.join(sysd, d, "zzsyfix")
            if os.path.exists(pth):
                os.remove(pth)

    say("\nsandbox-syntax: %d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        bail("no row ran - a broken test, not a pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
