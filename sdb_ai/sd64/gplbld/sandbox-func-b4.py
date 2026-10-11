#!/usr/bin/env python3
#
# sandbox-func-b4.py - 1.2-0 bundle B-4 (openQM new and extended BASIC functions).  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-func-b4.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (needs a `make`d bin/sd).  With --build it is built first from
# THIS tree (it must be empty or absent).  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 11 Oct 26 dm  Written for 1.2-0 bundle B-4: ADDS SUBS MULS DIVS (207), QUOTES DQUOTES (11).
# END-HISTORY
#
# THE INSTRUMENT IS THE VALUE A BASIC PROGRAM PRINTED between brackets, value marks shown as |.  Each new
# function has a CONTROL on the line before it: the single-value function it is the multivalued form of.

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
passed = failed = 0

# (label, BASIC statements one per line leaving the value in x, wanted)
CASES = [
    ("CONTROL: MODS, an existing multivalued function, on two lists", "x = change(mods('7':@vm:'9', '4':@vm:'5'), @vm, '|')", "3|4"),
    ("207 ADDS adds element by element", "x = change(adds('1':@vm:'2', '10':@vm:'20'), @vm, '|')", "11|22"),
    ("207 SUBS subtracts element by element", "x = change(subs('10':@vm:'20', '1':@vm:'2'), @vm, '|')", "9|18"),
    ("207 MULS multiplies element by element", "x = change(muls('2':@vm:'3', '5':@vm:'7'), @vm, '|')", "10|21"),
    ("207 DIVS divides element by element", "x = change(divs('10':@vm:'20', '2':@vm:'5'), @vm, '|')", "5|4"),
    ("207 ADDS with a shorter second list treats the missing element as zero",
     "x = change(adds('1':@vm:'2':@vm:'3', '10'), @vm, '|')", "11|2|3"),
    ("207 ADDS works on field marks too", "x = change(adds('1':@fm:'2', '5':@fm:'6'), @fm, '|')", "6|8"),
    ("CONTROL: QUOTE of one string uses double quotes", "x = quote('a')", '"a"'),
    ("11 QUOTES quotes every element", "x = change(quotes('a':@vm:'b'), @vm, '|')", '"a"|"b"'),
    ("11 DQUOTES is the same", "x = change(dquotes('a':@vm:'b'), @vm, '|')", '"a"|"b"'),
]


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
    say("sandbox-func-b4: CANNOT RUN - " + msg)
    sys.exit(2)


def sess(box, *cmds):
    say("    > %d commands" % len(cmds))
    p = subprocess.run([sys.executable, TOOL, box, "sess", os.path.join(box, "user_accounts")] + list(cmds),
                       capture_output=True, text=True, timeout=900)
    out = ANSI.sub("", p.stdout + p.stderr)
    return out.split(":TERM 200,9999", 1)[-1]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-func-b4.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-func-b4: sandbox %s" % box)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-func-b4: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    cmds, names = [], []
    for i, (_, body, _w) in enumerate(CASES):
        nm = "zzb4%02d" % i
        names.append(nm)
        with open(os.path.join(sysd, "bp", nm), "w") as f:
            f.write("   x = ''\n" + "".join("   %s\n" % ln for ln in body.split("\n")) + "   crt 'C%02d[':x:']'\nend\n" % i)
        cmds += ["BASIC bp %s" % nm, "RUN bp %s" % nm]
    try:
        out = sess(box, *cmds)
        say("\n--- the functions -------------------------------------------------------------")
        for i, (label, _body, want) in enumerate(CASES):
            m = re.search(r"(?m)^C%02d\[(.*)\]\s*$" % i, out)
            got = m.group(1) if m else None
            row("%s: wanted %r" % (label, want), got == want, "got %r" % got if m else "no output")
    finally:
        for nm in names:
            for d in ("bp", "bp.out"):
                pth = os.path.join(sysd, d, nm)
                if os.path.exists(pth):
                    os.remove(pth)

    say("\nsandbox-func-b4: %d passed, %d failed" % (passed, failed))
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
