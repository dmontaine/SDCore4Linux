#!/usr/bin/env python3
#
# sandbox-inputif.py - 1.2-0 bundle B-5, sheet 584: INPUTIF and INPUTIF @ take input only if the DATA queue or the type-ahead holds
#                      some, and otherwise take the ELSE clause without waiting, without a prompt.  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-inputif.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (needs a `make`d bin/sd).  With --build it is built first from
# THIS tree (it must be empty or absent).  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 14 Oct 26 dm  Written for sheet 584.
# END-HISTORY
#
# THE INSTRUMENT.  A session piped to `sd -internal` (as sandbox-input.py).  The type-ahead is the rest of the pipe: a probe run
# as the LAST line of the pipe, with the pipe then closed, has no type-ahead (the ELSE case); one with a line after it has some.
# The DATA queue is filled by a DATA statement in the probe.  Every outcome is a tag, A[value] or A[none], so that the
# prompt character, which INPUT writes before it reads, shows as ?A[none] if it was written.  Controls: INPUT, which does read.

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
    say("sandbox-inputif: CANNOT RUN - " + msg)
    sys.exit(2)


def session(box, cmds, end=True):
    """cmds are piped to sd -internal; with end=False no OFF follows, so the pipe closes after the last line."""
    say("    > [sd -internal] " + " | ".join(repr(c) for c in cmds) + ("" if end else "   (then end of input)"))
    env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"))
    body = "\nTERM 200,9999\n" + "".join(c + "\n" for c in cmds) + ("OFF\n" if end else "")
    p = subprocess.run([os.path.join(box, "sys", "bin", "sd"), "-internal"], input=body,
                       cwd=os.path.join(box, "sys"), env=env, capture_output=True, text=True, errors="replace", timeout=180)
    out = ANSI.sub("", p.stdout + p.stderr)
    return out.split(":TERM 200,9999", 1)[-1]


def live(box, cmds):
    """A session on a pseudo-terminal, and what is on its screen after the commands are typed.  KEYREADY is always true on a
    pipe (linuxio.c: `if (piped_input) return TRUE`, since a read there returns at once with end of file), so whether
    anything is waiting can only be tested on a terminal.  An element of cmds may hold a Return and more text: it is
    typed in one write, which is type-ahead for the program the first part starts."""
    say("    > [pty] " + " | ".join(repr(c) for c in cmds))
    env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"), TERM="xterm")
    s = PtySession([os.path.join(box, "sys", "bin", "sd")], os.path.join(box, "sys"), env, 120, 30)
    s.settle(1.0)
    s.type("TERM xterm\r")
    s.type("TERM 120,30\r")
    for c in cmds:
        s.type(c + "\r", idle=1.2)
    out = "\n".join(ln.rstrip() for ln in s.screen.lines())
    s.finish()
    return out


def line(out, name):
    m = re.search(r"(?m)^(\??)%s\[(.*)\]\s*$" % name, out)
    return None if m is None else (m.group(1), m.group(2))


PROGS = {
    "zziifa": "   inputif a then crt 'A[':a:']' else crt 'A[none]'\n   crt 'END'\nend\n",
    "zziifb": "   data 'queued'\n   inputif a then crt 'A[':a:']' else crt 'A[none]'\n   crt 'END'\nend\n",
    "zziifc": "   a = 'old'\n   inputif @(0,5) : a, 10 then crt 'A[':a:']' else crt 'A[none':a:']'\n   crt 'END'\nend\n",
    "zziifd": "   data 'queued'\n   inputif @(0,5) : a, 10 then crt 'A[':a:']' else crt 'A[none]'\n   crt 'END'\nend\n",
    "zziife": "   a = 'old'\n   inputif a else crt 'A[else only ':a:']'\n   crt 'END'\nend\n",
    "zziifi": "   input a\n   crt 'A[':a:']'\n   crt 'END'\nend\n",
}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-inputif.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-inputif: sandbox %s" % box)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-inputif: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    made = []
    try:
        for nm, text in PROGS.items():
            with open(os.path.join(sysd, "bp", nm), "w") as f:
                f.write(text)
            made.append(nm)
        out = session(box, ["BASIC bp " + " ".join(PROGS)])
        n = len(re.findall(r"(?m)^Compiled %d program\(s\) with no errors" % len(PROGS), out))
        row("setup: INPUTIF, INPUTIF @ and the controls compile with no errors", n == 1, out[-500:])
        if n != 1:
            bail("the probes did not compile")

        out = live(box, ["RUN bp zziifa"])
        row("584: INPUTIF with nothing waiting takes the ELSE clause and does not wait (the run reaches END)",
            line(out, "A") == ("", "none") and re.search(r"(?m)^END\s*$", out) is not None, out[-300:])
        row("584: ... and wrote no prompt (the tag is not preceded by ?)", line(out, "A") is not None and line(out, "A")[0] == "", repr(line(out, "A")))

        out = live(box, ["RUN bp zziifa\rtyped ahead"])
        row("584: INPUTIF with a line typed ahead reads it", line(out, "A") is not None and line(out, "A")[1] == "typed ahead", out[-300:])

        out = live(box, ["RUN bp zziifb"])
        row("584: INPUTIF with the DATA queue filled reads from it", line(out, "A") is not None and line(out, "A")[1] == "queued", out[-300:])

        out = live(box, ["RUN bp zziifc"])
        row("584: INPUTIF @ with nothing waiting takes the ELSE clause and leaves the variable alone",
            re.search(r"(?m)^A\[noneold\]\s*$", out) is not None and re.search(r"(?m)^END\s*$", out) is not None,
            out[-300:])
        out = live(box, ["RUN bp zziifd"])
        row("584: INPUTIF @ with the DATA queue filled reads from it", line(out, "A") is not None and line(out, "A")[1] == "queued", out[-300:])
        out = live(box, ["RUN bp zziifc\rahead"])
        row("584: INPUTIF @ with a line typed ahead reads it", line(out, "A") is not None and line(out, "A")[1] == "ahead", out[-300:])

        out = live(box, ["RUN bp zziife"])
        row("584: INPUTIF with only an ELSE clause compiles and runs the ELSE when nothing is waiting",
            re.search(r"(?m)^A\[else only old\]\s*$", out) is not None, out[-300:])

        out = live(box, ["RUN bp zziifi", "plain"])
        row("CONTROL: a plain INPUT still reads the line it is given", line(out, "A") is not None and line(out, "A")[1] == "plain", out[-300:])
    finally:
        for nm in made:
            for d in ("bp", "bp.out"):
                pth = os.path.join(sysd, d, nm)
                if os.path.exists(pth):
                    os.remove(pth)

    say("\nsandbox-inputif: %d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        bail("no row ran - a broken test, not a pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
