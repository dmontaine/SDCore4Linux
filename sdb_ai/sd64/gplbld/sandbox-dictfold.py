#!/usr/bin/env python3
#
# sandbox-dictfold.py - does a dictionary read fold case?  RELEASE_1.1 5 stage 2a (PAL-1).
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-dictfold.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (a private SD built from a tree, no sudo, its own
# IPC keys: never the live system).  With --build the sandbox is built first from THIS tree; <dir>
# must then be empty or absent.  Without it <dir> must already be built, which is how the same
# script is run against an OLD build to prove it can fail.  The fixture files have a name unique to
# the run, so a sandbox that was used before is fine.
#
# Exit 0 every row passed, 1 a row failed, 2 it could not run (setup is not what the rows assume).
#
# WHAT IT MEASURES.  The Windows port's stage 2a (its verify-dictfold.ps1, 14 Sep 2026): a dictionary
# item stored in lower case is found when a query, CD or an I-type names it in upper case, and the
# other way round.  Every DECISIVE row is red on a build without the fold; the names are read from
# what SD printed, case-sensitively, because ext4 does not hide a miss the way NTFS did.
#
# THE INSTRUMENT.  It prints the commands it sent and what came back.  Every no-error row also
# requires the "Compiling" line, because a COPY can carry a compiled object across and a row that only
# looks for the absence of an error passes when nothing was compiled.

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
RUN = "%05d" % (os.getpid() % 100000)
F = "ZZF" + RUN          # dictionary stores f1, f3, xtype in LOWER case
G = "ZZG" + RUN          # dictionary stores F1 in UPPER case
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
    say("sandbox-dictfold: CANNOT RUN - " + msg)
    sys.exit(2)


def sess(box, *cmds):
    say("    > " + " | ".join(cmds))
    p = subprocess.run([sys.executable, TOOL, box, "sess", os.path.join(box, "user_accounts")] + list(cmds),
                       capture_output=True, text=True, timeout=300)
    out = ANSI.sub("", p.stdout + p.stderr)
    out = out.split(":TERM 200,9999", 1)[-1]
    for line in out.splitlines():
        if line.strip() and not line.startswith(":") and not line.startswith("exit "):
            say("      | " + line.rstrip()[:110])
    return out


def heads(text, file):
    """The column headings printed by LIST <file> <field>: 'zzf00001.......   F1...' -> 'F1...'."""
    return re.findall(r"(?m)^" + re.escape(file.lower()) + r"\.*\s+(\S+)\s*$", text)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-dictfold.py <dir> [--build]")
    box = os.path.abspath(args[0])
    say("sandbox-dictfold: sandbox  %s" % box)
    say("sandbox-dictfold: tree     %s" % os.path.dirname(HERE))
    say("sandbox-dictfold: files    %s (lower-case dictionary), %s (upper-case dictionary)" % (F, G))
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-dictfold: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(box, "sys", "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, timeout=120)
    xt = "zzxt" + RUN
    # the I-type: its expression names F1 and F3 in UPPER case, the dictionary stores f1 and f3 lower
    with open(os.path.join(box, "sys", "bp", xt), "wb") as f:
        f.write(b"I\nF1 : '-' : F3\n\nXtype\n12L\nS\n")
    try:
        say("\n--- setup: %s stores f1, f3 and xtype in LOWER case; %s stores F1 in UPPER case ----------" % (F, G))
        out = sess(box,
                   "CREATE.FILE " + F, "COPY FROM DICT VOC TO DICT %s F1,f1" % F, "COPY FROM DICT VOC TO DICT %s F3,f3" % F,
                   "COPY FROM BP TO DICT %s %s,xtype" % (F, xt), "COPY FROM VOC TO %s who,r1" % F, "LIST DICT " + F,
                   "CREATE.FILE " + G, "COPY FROM DICT VOC TO DICT %s F1,F1" % G, "COPY FROM VOC TO %s who,r1" % G,
                   "LIST DICT " + G)
        copied = len(re.findall(r"(?m)^1 record\(s\) copied\.", out))
        row("setup: all six COPY commands each copied one record", copied == 6, "copied lines: %d" % copied)
        for ident in ("f1", "f3", "xtype"):
            row("setup: %s's dictionary holds '%s' in lower case" % (F, ident),
                re.search(r"(?m)^" + ident + r"\s{2,}[DI]\s", out) is not None, "no LIST DICT row for " + ident)
        row("setup: %s's dictionary holds 'F1' in upper case" % G,
            re.search(r"(?m)^F1\s{2,}D\s", out) is not None, "no upper-case F1 row")
        if failed:
            bail("the fixture is not what the rows assume - nothing below would measure the fold")

        say("\n--- leg 1: LIST names the field in upper case; the dictionary stores it lower case ----------")
        out = sess(box, "LIST %s F1" % F, "LIST %s f1" % F)
        h = heads(out, F)
        say("    column headings, in order: %s" % " | ".join(h))
        row("leg 1: both LISTs printed a column heading", len(h) == 2, "got %d" % len(h))
        row("CONTROL leg 1: f1 typed lower uses the dictionary item (heading 'F1...')",
            len(h) == 2 and h[1] == "F1...", " | ".join(h))
        row("leg 1: F1 typed UPPER uses the same dictionary item (heading 'F1...')",
            len(h) == 2 and h[0] == "F1...", " | ".join(h))

        say("\n--- leg 2: CD of an I-type whose expression names F1 and F3 in upper case --------------------")
        out = sess(box, "CD %s xtype" % F)
        compiled = re.search(r"(?m)^Compiling xtype\s*$", out) is not None
        row("leg 2: CD reached the compiler ('Compiling xtype')", compiled, "no Compiling line: nothing below is measured")
        row("leg 2: the expression's F1 and F3 resolved to f1 and f3 (no error)",
            compiled and "is not defined" not in out and "Compilation error" not in out,
            "a field name in the expression was not found")
        out = sess(box, "LIST %s xtype" % F)
        row("leg 2: LIST xtype evaluates it (field 1 and 3 of VOC's WHO, joined by '-')",
            re.search(r"(?m)^r1\s+\S.*-\s*\S", out) is not None, "no r1 row with a '-' in it")

        say("\n--- leg 3: the other way round - %s stores F1 in upper case, the query names f1 in lower ---" % G)
        out = sess(box, "LIST %s f1" % G, "LIST %s F1" % G)
        h = heads(out, G)
        say("    column headings, in order: %s" % " | ".join(h))
        row("leg 3: both LISTs printed a column heading", len(h) == 2, "got %d" % len(h))
        row("CONTROL leg 3: F1 typed UPPER uses the stored item (heading 'F1...')",
            len(h) == 2 and h[1] == "F1...", " | ".join(h))
        row("leg 3: f1 typed lower uses the same stored item (heading 'F1...')",
            len(h) == 2 and h[0] == "F1...", " | ".join(h))
    finally:
        subprocess.run([sys.executable, TOOL, box, "stop"], capture_output=True, text=True, timeout=120)
    say("\nsandbox-dictfold: %d passed, %d failed" % (passed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
