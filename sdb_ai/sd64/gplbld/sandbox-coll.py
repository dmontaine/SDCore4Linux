#!/usr/bin/env python3
#
# sandbox-coll.py - 1.2-0 data collections (openQM "Data Collections").  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-coll.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (needs a `make`d bin/sd).  With --build it is built first from
# THIS tree (it must be empty or absent).  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 13 Oct 26 dm  Written for the first slice: COLLECTION(), c{path} get / set / DEL, ELEMENT.EXISTS(), ENUMERATE().
# END-HISTORY
#
# THE INSTRUMENT IS THE VALUE A BASIC PROGRAM PRINTED between brackets (marks shown as F V S).  A row whose program
# is meant to stop with a run time error is read from the whole output instead.  Each feature has a CONTROL row on
# the line before it where there is an existing feature to compare it with.

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
passed = failed = 0

C = "c = collection()\n   "

# (label, BASIC statements one per line leaving the value in x, wanted)   wanted starting with "ERR:" is a text the
# output must hold because the program must stop with a run time error.
CASES = [
    ("CONTROL: a dynamic array field is still read with angle brackets", "a = 'p':@fm:'q'\n   x = a<2>", "q"),
    ("CONTROL: and an ordinary variable still takes a substring", "a = 'hello'\n   x = a[2,3]", "ell"),
    ("COLLECTION() makes a collection that an element can be put in and read from",
     C + "c{'name'} = 'Acme'\n   x = c{'name'}", "Acme"),
    ("a number stays a number", C + "c{'n'} = 5\n   x = c{'n'} + 2", "7"),
    ("a value holding field marks comes back whole",
     C + "c{'v'} = 'a':@fm:'b'\n   x = change(c{'v'}, @fm, 'F')", "aFb"),
    ("setting a name again replaces it", C + "c{'k'} = 'one'\n   c{'k'} = 'two'\n   x = c{'k'}", "two"),
    ("an element that is not there is a null string and STATUS() is ER$NOT.FOUND",
     C + "x = c{'nope'}\n   x = '[':x:'][':status():']'", "[][1004]"),
    ("a name is case sensitive", C + "c{'Name'} = 'upper'\n   x = '[':c{'name'}:']'", "[]"),
    ("ELEMENT.EXISTS() says 1 for a present element", C + "c{'a'} = 1\n   x = element.exists(c, 'a')", "1"),
    ("ELEMENT.EXISTS() says 0 for an absent one", C + "c{'a'} = 1\n   x = element.exists(c, 'b')", "0"),
    ("DEL removes an element", C + "c{'a'} = 1\n   del c{'a'}\n   x = element.exists(c, 'a')", "0"),
    ("DEL of an absent element leaves STATUS() at ER$NOT.FOUND and does nothing else",
     C + "c{'a'} = 1\n   del c{'b'}\n   x = status():'|':element.exists(c, 'a')", "1004|1"),
    ("ENUMERATE() gives the names sorted, left aligned and case sensitive (capitals first)",
     C + "c{'b'} = 1\n   c{'a'} = 1\n   c{'C'} = 1\n   x = change(enumerate(c), @fm, '|')", "C|a|b"),
    ("ENUMERATE() of an empty collection is null", C + "x = '[':enumerate(c):']'", "[]"),
    ("ENUMERATE() lists only the level it is given",
     C + "c{'a/b'} = 1\n   c{'z'} = 1\n   x = change(enumerate(c), @fm, '|')", "a|z"),
    ("{'a','b'}, {'a'}{'b'} and {'a/b'} are the same element",
     C + "c{'a','b'} = 'v'\n   x = c{'a'}{'b'}:'|':c{'a/b'}:'|':c{'a','b'}", "v|v|v"),
    ("the path may be mixed: {'a/b','c'} and {'a'}{'b/c'}",
     C + "c{'a/b','c'} = 'w'\n   x = c{'a'}{'b/c'}:'|':c{'a/b/c'}", "w|w"),
    ("a path made of variables", C + "p = 'a':'/':'b'\n   c{p} = 'q'\n   k = 'a'\n   x = c{k}{'b'}", "q"),
    ("elements missing along the way are made", C + "c{'x/y/z'} = 'deep'\n   x = c{'x'}{'y'}{'z'}", "deep"),
    ("an intermediate level is a collection that can be enumerated",
     C + "c{'x/y/z'} = 'deep'\n   t = c{'x'}\n   x = change(enumerate(t), @fm, '|')", "y"),
    ("DEL of a level removes everything below it",
     C + "c{'x/y/z'} = 'deep'\n   del c{'x'}\n   x = element.exists(c, 'x/y/z'):element.exists(c, 'x')", "00"),
    ("assigning a collection variable makes another reference to the same collection",
     C + "d = c\n   d{'k'} = 'v'\n   x = c{'k'}", "v"),
    ("COLLECTION(c) makes an independent copy",
     C + "c{'k'} = 'one'\n   d = collection(c)\n   d{'k'} = 'two'\n   d{'new'} = 1\n   x = c{'k'}:'|':element.exists(c, 'new')", "one|0"),
    ("a copy is deep: a collection inside is copied too",
     C + "c{'in/k'} = 'one'\n   d = collection(c)\n   d{'in/k'} = 'two'\n   x = c{'in/k'}", "one"),
    ("a collection can be an element of another, and shares",
     C + "d = collection()\n   c{'sub'} = d\n   d{'k'} = 'v'\n   x = c{'sub'}{'k'}", "v"),
    ("a name that is a number is a name in an ordinary collection", C + "c{'7'} = 'seven'\n   c{7} = 'again'\n   x = c{'7'}", "again"),
    ("a value read back from a collection can be changed without changing the collection",
     C + "c{'s'} = 'abc'\n   v = c{'s'}\n   v := 'def'\n   x = c{'s'}", "abc"),
    ("a collection held in a dimensioned array element",
     "dim t(2)\n   t(1) = collection()\n   t(1){'k'} = 'v'\n   x = t(1){'k'}", "v"),
    ("3000 elements go in sorted and come out again (the table grows and shrinks)",
     C + "for i = 1 to 3000\n   c{'k':i} = i\n   next i\n   x = dcount(enumerate(c), @fm)\n"
     "   for i = 1 to 3000 step 2\n   del c{'k':i}\n   next i\n   x := '|':dcount(enumerate(c), @fm):'|':c{'k2998'}:'|':element.exists(c, 'k2999')\n"
     "   for i = 2 to 3000 step 2\n   del c{'k':i}\n   next i\n   x := '|':dcount(enumerate(c), @fm)", "3000|1500|2998|0|0"),
    ("a collection copied again and again, and dropped, leaves the original whole",
     C + "c{'a/b/c'} = 'deep'\n   for i = 1 to 2000\n   d = collection(c)\n   d{'a/b/x'} = i\n   next i\n   x = c{'a/b/c'}:'|':d{'a/b/x'}:'|':element.exists(c, 'a/b/x')", "deep|2000|0"),
    ("ERR: a variable that is not a collection cannot take an element", "n = 5\n   n{'a'} = 1", "ERR:not a data collection"),
    ("ERR: nor can one be read from it", "n = 5\n   x = n{'a'}", "ERR:not a data collection"),
    ("ERR: an element cannot be added below a value that is not a collection",
     C + "c{'a'} = 1\n   c{'a/b'} = 2", "ERR:passes through a value that is not a collection"),
    ("ERR: an empty name is refused", C + "c{''} = 1", "ERR:Invalid data collection element name"),
    ("ERR: so is an empty part of a path", C + "c{'a//b'} = 1", "ERR:Invalid data collection element name"),
    ("ERR: a missing right curly bracket is a compile error", C + "x = c{'a'", "ERR:Right curly bracket"),
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
    say("sandbox-coll: CANNOT RUN - " + msg)
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
        bail("usage: sandbox-coll.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-coll: sandbox %s" % box)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-coll: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    cmds, names = [], []
    for i, (_, body, _w) in enumerate(CASES):
        nm = "zzco%02d" % i
        names.append(nm)
        with open(os.path.join(sysd, "bp", nm), "w") as f:
            f.write("   x = ''\n   " + "".join("%s\n   " % ln for ln in body.split("\n")) + "crt 'C%02d[':x:']'\nend\n" % i)
        cmds += ["BASIC bp %s" % nm, "RUN bp %s" % nm]
    try:
        out = sess(box, *cmds)
        say("\n--- collections -------------------------------------------------------------")
        starts = {}
        for m in re.finditer(r"(?m)^:BASIC bp zzco(\d\d)\s*$", out):
            starts[int(m.group(1))] = m.start()
        for i, (label, _body, want) in enumerate(CASES):
            if i not in starts:
                row(label, False, "its compile was never seen in the output")
                continue
            later = [s for k, s in starts.items() if s > starts[i]]
            seg = out[starts[i]:(min(later) if later else len(out))]
            if want.startswith("ERR:"):
                text = want[4:]
                row("%s: wanted the text %r" % (label, text), text in seg and not re.search(r"(?m)^C%02d\[" % i, seg),
                    "output: %s" % seg[-300:])
            else:
                m = re.search(r"(?m)^C%02d\[(.*)\]\s*$" % i, seg)
                got = m.group(1) if m else None
                row("%s: wanted %r" % (label, want), got == want, "got %r  %s" % (got, seg[-200:]) if not m else "got %r" % got)
    finally:
        for nm in names:
            for d in ("bp", "bp.out"):
                pth = os.path.join(sysd, d, nm)
                if os.path.exists(pth):
                    os.remove(pth)

    say("\nsandbox-coll: %d passed, %d failed" % (passed, failed))
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
