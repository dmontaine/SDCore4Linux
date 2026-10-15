#!/usr/bin/env python3
#
# sandbox-inputtrap.py - 1.2-0 bundle B-5, sheet 408: INPUTNULL expr and INPUTTRAP expr GOTO / GOSUB label{,label...}.
#                        A single character typed as the whole answer to INPUT @ or INPUTFIELD is made a null string (INPUTNULL), or
#                        sends the program to the label of its position (INPUTTRAP; the last label for a character past the end;
#                        INPUTNULL wins when both name it).  A GOSUB continues at the statement after the INPUTTRAP when the
#                        subroutine returns.  A null expression cancels.  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-inputtrap.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (needs a `make`d bin/sd).  With --build it is built first from
# THIS tree (it must be empty or absent).  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 14 Oct 26 dm  Written for sheet 408.
# END-HISTORY
#
# THE INSTRUMENT.  A session on a pseudo-terminal with an emulated screen (as sandbox-inputfill.py).  Each probe prints tags that
# only the path it took can print: HELP, QUIT, SUB, NORMAL[value]; the screen is read after the keys.  Controls: ordinary answers
# and INPUT (not INPUT @) are untouched, and a program with no INPUTTRAP is as it was.

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
    say("sandbox-inputtrap: CANNOT RUN - " + msg)
    sys.exit(2)


def internal(box, *cmds):
    env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"))
    body = "\nTERM 200,9999\n" + "".join(c + "\n" for c in cmds) + "OFF\n"
    p = subprocess.run([os.path.join(box, "sys", "bin", "sd"), "-internal"], input=body, cwd=os.path.join(box, "sys"), env=env,
                       capture_output=True, text=True, errors="replace", timeout=180)
    return ANSI.sub("", p.stdout + p.stderr)


class Run:
    def __init__(self, box, prog, keep=None):
        if keep is None:
            env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"), TERM="xterm")
            self.s = PtySession([os.path.join(box, "sys", "bin", "sd")], os.path.join(box, "sys"), env, 100, 30)
            self.s.settle(1.0)
            self.s.type("TERM xterm\r")
            self.s.type("TERM 100,30\r")
        else:
            self.s = keep.s
        self.s.type("RUN bp %s\r" % prog, idle=1.0)

    def type(self, keys):
        self.s.type(keys, idle=0.6)

    def text(self):
        return "\n".join(ln.rstrip() for ln in self.s.screen.lines())

    def count(self, word):
        return self.text().count(word)

    def done(self):
        self.s.finish()


PROGS = {
    "zzitg": ("   inputtrap '?!#' goto help.label, quit.label\n"
              "   input @(0,5) : a, 10\n"
              "   crt @(0,8) : 'NORMAL[':a:']'\n   stop\n"
              "help.label: crt @(0,8) : 'HELP' ; stop\n"
              "quit.label: crt @(0,8) : 'QUIT' ; stop\nend\n"),
    "zzits": ("   cnt = 0\n   inputtrap '?' gosub h\n"
              "   cnt += 1\n   crt @(0,7) : 'AFTER-INPUTTRAP ':cnt\n"
              "   input @(0,5) : a, 10\n"
              "   crt @(0,9) : 'GOT[':a:']'\n   stop\n"
              "h: crt @(0,8) : 'IN-SUB' ; return\nend\n"),
    "zzitf": ("   inputtrap '?' goto help.label\n"
              "   inputfield @(0,5) : a, 10\n"
              "   crt @(0,8) : 'NORMAL[':a:']'\n   stop\n"
              "help.label: crt @(0,8) : 'HELP' ; stop\nend\n"),
    "zzite": ("   inputtrap '?' goto help.label\n"
              "   input @(0,5) : a, 10 then crt @(0,8) : 'THEN[':a:']' else crt @(0,8) : 'ELSE'\n   stop\n"
              "help.label: crt @(0,8) : 'HELP' ; stop\nend\n"),
    "zzitn": ("   inputnull '*'\n"
              "   a = 'old'\n   input @(0,5) : a, 10\n"
              "   crt @(0,8) : 'NULL[':a:']'\n   stop\nend\n"),
    "zzitc": ("   inputnull '*'\n   inputnull ''\n"
              "   input @(0,5) : a, 10\n"
              "   crt @(0,8) : 'CAN[':a:']'\n   stop\nend\n"),
    "zzitp": ("   inputnull '?'\n   inputtrap '?' goto help.label\n"
              "   input @(0,5) : a, 10\n"
              "   crt @(0,8) : 'PREC[':a:']'\n   stop\n"
              "help.label: crt @(0,8) : 'HELP' ; stop\nend\n"),
    "zzitl": ("   input @(0,5) : a, 10\n   crt @(0,8) : 'LATER[':a:']'\n   stop\nend\n"),
    "zzitsub": ("   subroutine zzitsub\n   input @(0,5) : a, 10\n   crt @(0,8) : 'SUB[':a:']'\n   return\nend\n"),
    "zzitm": ("   inputtrap '?' goto help.label\n   call zzitsub\n   crt @(0,9) : 'BACK'\n   stop\n"
              "help.label: crt @(0,8) : 'HELP' ; stop\nend\n"),
    "zzitq": ("   inputtrap '?' goto help.label\n   input a\n   crt @(0,8) : 'PLAIN[':a:']'\n   stop\n"
              "help.label: crt @(0,8) : 'HELP' ; stop\nend\n"),
    "zzitx": ("   inputtrap '?' goto help.label\n   inputtrap '' goto help.label\n"
              "   input @(0,5) : a, 10\n   crt @(0,8) : 'CANTRAP[':a:']'\n   stop\n"
              "help.label: crt @(0,8) : 'HELP' ; stop\nend\n"),
    "zzitbad": "   inputtrap '?'\nend\n",
}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-inputtrap.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-inputtrap: sandbox %s" % box)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-inputtrap: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    made = []
    try:
        for nm, text in PROGS.items():
            with open(os.path.join(sysd, "bp", nm), "w") as f:
                f.write(text)
            made.append(nm)
        good = [n for n in PROGS if n != "zzitbad"]
        out = internal(box, "BASIC bp " + " ".join(good), "CATALOG bp zzitsub LOCAL")
        row("setup: the probes compile with no errors", re.search(r"(?m)^Compiled %d program\(s\) with no errors" % len(good), out) is not None, out[-700:])
        out = internal(box, "BASIC bp zzitbad")
        row("408: INPUTTRAP without GOTO or GOSUB is a compile error", "Compiled 1 program(s) with no errors" not in out, out[-300:])

        say("\n--- INPUTTRAP ... GOTO ---")
        for typed, want, label in (("?", "HELP", "the first character takes the first label"),
                                   ("!", "QUIT", "the second the second"),
                                   ("#", "QUIT", "a character past the labels takes the last label")):
            r = Run(box, "zzitg")
            r.type(typed + "\r")
            row("408: '%s' alone: %s (%s)" % (typed, want, label), r.count(want) >= 1 and "NORMAL" not in r.text(), r.text()[-300:])
            r.done()
        r = Run(box, "zzitg")
        r.type("x\r")
        row("CONTROL: an ordinary character is an ordinary answer", "NORMAL[x]" in r.text() and "HELP" not in r.text(), r.text()[-300:])
        r.done()
        r = Run(box, "zzitg")
        r.type("?!\r")
        row("CONTROL: two characters, even trapped ones, are an ordinary answer", "NORMAL[?!]" in r.text(), r.text()[-300:])
        r.done()

        say("\n--- GOSUB: the subroutine returns to the statement after the INPUTTRAP ---")
        r = Run(box, "zzits")
        r.type("?\r")
        row("408: the subroutine ran, and execution came back AFTER THE INPUTTRAP (the statement after it ran again: counter 2)",
            "IN-SUB" in r.text() and "AFTER-INPUTTRAP 2" in r.text(), r.text()[-400:])
        r.type("z\r")
        row("408: ... and the asking goes on: the next answer is read normally", "GOT[z]" in r.text(), r.text()[-300:])
        r.done()

        say("\n--- INPUTFIELD and a THEN / ELSE clause ---")
        r = Run(box, "zzitf")
        r.type("?\r")
        row("408: INPUTFIELD takes the trap too", "HELP" in r.text() and "NORMAL" not in r.text(), r.text()[-300:])
        r.done()
        r = Run(box, "zzite")
        r.type("?\r")
        row("408: with a THEN / ELSE clause the trap is taken and neither clause runs", "HELP" in r.text() and "THEN[" not in r.text() and "ELSE" not in r.text(),
            r.text()[-300:])
        r.done()
        r = Run(box, "zzite")
        r.type("ok\r")
        row("CONTROL: ... and an ordinary answer still takes THEN", "THEN[ok]" in r.text(), r.text()[-300:])
        r.done()

        say("\n--- INPUTNULL ---")
        r = Run(box, "zzitn")
        r.type("*\r")
        row("408: INPUTNULL: the character alone makes the variable null (the old value is gone)", "NULL[]" in r.text(), r.text()[-300:])
        r.done()
        r = Run(box, "zzitn")
        r.type("x\r")
        row("CONTROL: another character is an ordinary answer", "NULL[x]" in r.text(), r.text()[-300:])
        r.done()
        r = Run(box, "zzitn")
        r.type("**\r")
        row("CONTROL: two of the character are an ordinary answer", "NULL[**]" in r.text(), r.text()[-300:])
        r.done()
        r = Run(box, "zzitc")
        r.type("*\r")
        row("408: a null INPUTNULL cancels it", "CAN[*]" in r.text(), r.text()[-300:])
        r.done()
        r = Run(box, "zzitp")
        r.type("?\r")
        row("408: both naming the same character: INPUTNULL wins (null, no jump)", "PREC[]" in r.text() and "HELP" not in r.text(), r.text()[-300:])
        r.done()
        r = Run(box, "zzitn")
        r.type("*\r")
        r2 = Run(box, "zzitl", keep=r)
        r2.type("*\r")
        row("408: INPUTNULL ends on return to the command prompt (the next program's INPUT @ gets '*')", "LATER[*]" in r2.text(), r2.text()[-300:])
        r2.done()

        say("\n--- scope and cancel ---")
        r = Run(box, "zzitm")
        r.type("?\r")
        row("408: an INPUT @ in a called subroutine does not see the caller's trap (SUB[?], then back in the caller)",
            "SUB[?]" in r.text() and "HELP" not in r.text() and "BACK" in r.text(), r.text()[-300:])
        r.done()
        r = Run(box, "zzitq")
        r.type("?\r")
        row("CONTROL: plain INPUT is not trapped", "PLAIN[?]" in r.text() and "HELP" not in r.text(), r.text()[-300:])
        r.done()
        r = Run(box, "zzitx")
        r.type("?\r")
        row("408: a null INPUTTRAP expression cancels the trap", "CANTRAP[?]" in r.text() and "HELP" not in r.text(), r.text()[-300:])
        r.done()
    finally:
        for nm in made:
            for d in ("bp", "bp.out"):
                pth = os.path.join(sysd, d, nm)
                if os.path.exists(pth):
                    os.remove(pth)
        internal(box, "DELETE.CATALOG zzitsub LOCAL")

    say("\nsandbox-inputtrap: %d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        bail("no row ran - a broken test, not a pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
