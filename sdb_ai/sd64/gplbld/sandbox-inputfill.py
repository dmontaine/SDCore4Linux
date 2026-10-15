#!/usr/bin/env python3
#
# sandbox-inputfill.py - 1.2-0 bundle B-5, sheet 389: INPUT var, length, fill and INPUT @(x,y) : var, length, fill.  The first fill
#                        character shows the width of the field while it is typed in, the second (a blank when only one is given)
#                        fills what is left when the entry is finished, a third leaves the cursor at the end of the field.  Not
#                        with HIDDEN.  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-inputfill.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (needs a `make`d bin/sd).  With --build it is built first from
# THIS tree (it must be empty or absent).  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 14 Oct 26 dm  Written for sheet 389.
# END-HISTORY
#
# THE INSTRUMENT.  A session on a pseudo-terminal with an emulated screen (ptydrive.py, termscreen.py): the row the INPUT is on and
# the cursor are read after every key, so the field is seen as a person sees it.  After the entry a program prints a tag with the
# value it got, and with a trailing colon (no new line) an E that lands where the cursor was left.  Controls: the same INPUT without a
# fill leaves the field blank as it always did.

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
sys.path.insert(0, HERE)
from ptydrive import PtySession  # noqa: E402

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
passed = failed = 0


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
    say("sandbox-inputfill: CANNOT RUN - " + msg)
    sys.exit(2)


def compile_in(box, names):
    env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"))
    body = "\nTERM 200,9999\nBASIC bp " + " ".join(names) + "\nOFF\n"
    p = subprocess.run([os.path.join(box, "sys", "bin", "sd"), "-internal"], input=body, cwd=os.path.join(box, "sys"), env=env,
                       capture_output=True, text=True, errors="replace", timeout=180)
    return ANSI.sub("", p.stdout + p.stderr)


class Run:
    """A program run on a pty; keys are typed one chunk at a time and the screen is read after each."""

    def __init__(self, box, prog):
        env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"), TERM="xterm")
        self.s = PtySession([os.path.join(box, "sys", "bin", "sd")], os.path.join(box, "sys"), env, 100, 30)
        self.s.settle(1.0)
        self.s.type("TERM xterm\r")
        self.s.type("TERM 100,30\r")
        self.s.type("RUN bp %s\r" % prog, idle=1.0)

    def type(self, keys):
        self.s.type(keys, idle=0.5)

    def row_with(self, pattern):
        for i, ln in enumerate(self.s.screen.lines()):
            if re.search(pattern, ln):
                return i, ln.rstrip()
        return None, None

    def cursor(self):
        return self.s.screen.r, self.s.screen.c

    def text(self):
        return "\n".join(ln.rstrip() for ln in self.s.screen.lines())

    def done(self):
        self.s.finish()


PROGS = {
    "zzfil1": "   input a, 5, '.-'\n   crt 'A[':a:']'\nend\n",
    "zzfil2": "   input a, 5, '.'\n   crt 'A[':a:']'\nend\n",
    "zzfil3": "   input a, 5, '.-<' :\n   crt 'E':\n   crt ''\nend\n",
    "zzfil4": "   input a, 5, '.-' :\n   crt 'E':\n   crt ''\nend\n",
    "zzfil5": "   input @(0,3) : b, 6, '.-'\n   crt 'B[':b:']'\nend\n",
    "zzfil6": "   input @(0,3) : b, 6, '.-<' :\n   crt 'E':\n   crt ''\nend\n",
    "zzfil7": "   input a, 5\n   crt 'A[':a:']'\nend\n",
    "zzfilbad": "   input a, 5, '.' hidden\nend\n",
}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-inputfill.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-inputfill: sandbox %s" % box)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-inputfill: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    made = []
    try:
        for nm, text in PROGS.items():
            with open(os.path.join(sysd, "bp", nm), "w") as f:
                f.write(text)
            made.append(nm)
        good = [n for n in PROGS if n != "zzfilbad"]
        out = compile_in(box, good)
        row("setup: the probes compile with no errors", re.search(r"(?m)^Compiled %d program\(s\) with no errors" % len(good), out) is not None, out[-600:])
        out = compile_in(box, ["zzfilbad"])
        row("389: a fill expression with HIDDEN is a compile error",
            "cannot be used with HIDDEN" in out and "Compiled 1 program(s) with no errors" not in out, out[-400:])

        say("\n--- INPUT var, 5, '.-' : fill while typing, second fill when done ---")
        r = Run(box, "zzfil1")
        i, ln = r.row_with(r"^\?")
        row("389: before anything is typed the field shows its width in the first fill character, the cursor at its start",
            ln == "?....." and r.cursor() == (i, 1), "%r cursor %r" % (ln, r.cursor()))
        r.type("ab")
        i, ln = r.row_with(r"^\?")
        row("389: after 'ab' the unused part is still fill 1 and the cursor follows the text", ln == "?ab..." and r.cursor() == (i, 3),
            "%r cursor %r" % (ln, r.cursor()))
        r.type("\x7f")
        i, ln = r.row_with(r"^\?")
        row("389: the erase key puts a fill character back in the cell it clears", ln == "?a...." and r.cursor() == (i, 2),
            "%r cursor %r" % (ln, r.cursor()))
        r.type("\r")
        i, ln = r.row_with(r"^\?")
        row("389: on Return what is left of the field takes the second fill character", ln == "?a----", repr(ln))
        row("389: the program got 'a'", "A[a]" in r.text(), r.text()[-300:])
        r.done()

        r = Run(box, "zzfil2")
        r.type("ab\r")
        i, ln = r.row_with(r"^\?")
        row("389: a one character fill is fill 1, and fill 2 is a blank: '?ab' and nothing after it", ln == "?ab", repr(ln))
        r.done()

        say("\n--- the cursor, with a trailing colon so that no new line moves it ---")
        r = Run(box, "zzfil4")
        r.type("ab\r")
        i, ln = r.row_with(r"^\?")
        row("389: two fill characters: the cursor comes back to the end of the entry (E lands after 'ab')", ln is not None and ln.startswith("?abE"),
            repr(ln))
        r.done()
        r = Run(box, "zzfil3")
        r.type("ab\r")
        i, ln = r.row_with(r"^\?")
        row("389: three fill characters: the cursor stays at the end of the field (E lands after the five cells)",
            ln is not None and ln.startswith("?ab---E"), repr(ln))
        r.done()

        say("\n--- INPUT @ ---")
        r = Run(box, "zzfil5")
        i, ln = r.row_with(r"^\.{6}")
        row("389: INPUT @ paints the field with fill 1 at once", ln is not None and ln.startswith("......") and i == 3, "%r row %r" % (ln, i))
        r.type("abc")
        i, ln = r.row_with(r"^abc")
        row("389: after 'abc' the unused three cells are still fill 1 (the field overlays the banner text beyond its six cells)",
            ln is not None and ln.startswith("abc...") and not ln.startswith("abc....."), repr(ln))
        r.type("\x7f")
        i, ln = r.row_with(r"^ab")
        row("389: the erase key puts fill 1 back", ln is not None and ln.startswith("ab...."), repr(ln))
        r.type("\r")
        i, ln = r.row_with(r"^ab")
        row("389: on Return the rest takes fill 2", ln is not None and ln.startswith("ab----"), repr(ln))
        row("389: the program got 'ab'", "B[ab]" in r.text(), r.text()[-300:])
        r.done()
        r = Run(box, "zzfil6")
        r.type("ab\r")
        i, ln = r.row_with(r"^ab")
        row("389: INPUT @ with a third fill character leaves the cursor at the end of the field", ln is not None and ln.startswith("ab----E"), repr(ln))
        r.done()

        say("\n--- control ---")
        r = Run(box, "zzfil7")
        i, ln = r.row_with(r"^\?")
        row("CONTROL: INPUT var, 5 with no fill shows no field", ln == "?" and r.cursor() == (i, 1), "%r cursor %r" % (ln, r.cursor()))
        r.type("ab\r")
        i, ln = r.row_with(r"^\?")
        row("CONTROL: ... and ends as it always did", ln == "?ab" and "A[ab]" in r.text(), repr(ln))
        r.done()
    finally:
        for nm in made:
            for d in ("bp", "bp.out"):
                pth = os.path.join(sysd, d, nm)
                if os.path.exists(pth):
                    os.remove(pth)

    say("\nsandbox-inputfill: %d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        bail("no row ran - a broken test, not a pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
