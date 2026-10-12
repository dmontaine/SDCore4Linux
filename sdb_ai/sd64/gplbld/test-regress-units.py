#!/usr/bin/env python3
#
# test-regress-units.py - regress.sh's verdicts, on STUB suites.  No install, no sudo, no sd, a second or two.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-regress-units.py            the cases
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-regress-units.py --selftest the cases against 7 broken copies
#
# Exit 0 all passed, 1 a case failed.
#
# START-HISTORY:
# 12 Oct 26 dm  New with regress.sh.
# END-HISTORY
#
# WHY.  regress.sh is the instrument that says the tree is fine.  An instrument that reports a pass for a suite that
# printed nothing, or for one that passed no row, or that exited non-zero, is worse than none (CLAUDE.md: it must refuse
# the null case out loud).  So it is run here on a tree of stub suites whose behaviour is known, and the verdict, the
# exit status and the lines it prints are read.  The stubs are:
#   okay    prints "sandbox-okay: 3 passed, 0 failed", exits 0                      -> PASS
#   bad     prints a [FAIL] row and "2 passed, 1 failed", exits 1                    -> FAIL
#   badzero prints "2 passed, 1 failed" but exits 0                                  -> FAIL (the count is the count)
#   liar    prints "5 passed, 0 failed" but exits 1                                  -> FAIL (the exit status is the status)
#   silent  prints nothing, exits 0                                                  -> FAIL (no verdict line)
#   zero    prints "0 passed, 0 failed", exits 0                                     -> FAIL (a run that passed nothing)
#   cannot  prints "CANNOT RUN - ..." and exits 2                                    -> NOT RUN, exit 2
#   echo    writes the arguments it was given, and whether its directory existed, to a file, then passes
# The shared memory keys are read with ipcs; the cases put a fake ipcs first on PATH, so the result does not depend
# on whether a real sandbox is running while this check does.
#
# --selftest breaks a copy of regress.sh seven ways, each by one replacement that must match exactly once, and runs the
# cases against it: every broken copy must FAIL a case, or the cases do not test what they claim.

import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "regress.sh")
passed = failed = 0
quiet = False       # during a mutant's pass its own rows are counted, not shown: only whether it was caught is a result


def row(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        if not quiet:
            print("  [PASS] " + name)
    else:
        failed += 1
        if not quiet:
            print("  [FAIL] " + name + ("   <- " + detail if detail else ""))


STUBS = {
    "okay": 'print("sandbox-okay: 3 passed, 0 failed")',
    "bad": 'print("  [FAIL] a row that failed"); print("sandbox-bad: 2 passed, 1 failed"); sys.exit(1)',
    "badzero": 'print("sandbox-badzero: 2 passed, 1 failed")',
    "liar": 'print("sandbox-liar: 5 passed, 0 failed"); sys.exit(1)',
    "silent": "pass",
    "zero": 'print("sandbox-zero: 0 passed, 0 failed")',
    "cannot": 'print("sandbox-cannot: CANNOT RUN - no sandbox"); sys.exit(2)',
    "echo": ('open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "echo.args"), "w").write('
             '" ".join(sys.argv[1:]) + " | existed=" + str(os.path.exists(sys.argv[1])))\n'
             'print("sandbox-echo: 1 passed, 0 failed")'),
}


def make_tree(root, script_text):
    """A tree of stub suites with a copy of regress.sh (the real one, or a broken one) and a fake ipcs."""
    gb = os.path.join(root, "gplbld")
    os.makedirs(gb)
    for name, body in STUBS.items():
        with open(os.path.join(gb, "sandbox-%s.py" % name), "w") as f:
            f.write("import os, sys\n%s\n" % body)
    with open(os.path.join(gb, "regress.sh"), "w") as f:
        f.write(script_text)
    os.chmod(os.path.join(gb, "regress.sh"), 0o755)
    for kind, out in (("none", ""), ("held", "0x53434c91 1 don 666 102272 1\n")):
        bindir = os.path.join(root, "bin-" + kind)
        os.makedirs(bindir)
        with open(os.path.join(bindir, "ipcs"), "w") as f:
            f.write("#!/bin/sh\nprintf '%s' '" + out + "'\n")
        os.chmod(os.path.join(bindir, "ipcs"), 0o755)
    return gb


def run(root, args, held=False):
    env = dict(os.environ, PATH=os.path.join(root, "bin-held" if held else "bin-none") + ":" + os.environ["PATH"], TMPDIR=root)
    p = subprocess.run(["bash", os.path.join(root, "gplbld", "regress.sh"), "--tree", root] + args, capture_output=True, text=True, env=env, timeout=60)
    return p.returncode, p.stdout + p.stderr


def cases(label, script_text):
    """Run every case on a tree using script_text.  Returns the number of cases that failed."""
    before = failed
    root = tempfile.mkdtemp(prefix="regress-units.")
    try:
        make_tree(root, script_text)

        def verdict(out, suite):
            m = re.search(r"(?m)^\[\s*\d+/\d+\] %s\s+(PASS|FAIL|NOT RUN)\b" % re.escape(suite), out)
            return m.group(1) if m else None

        rc, out = run(root, ["--only", "okay"])
        row(label + "a suite that passes is PASS and the run exits 0", rc == 0 and verdict(out, "okay") == "PASS", "rc %d  %s" % (rc, out[-200:]))
        rc, out = run(root, ["--only", "okay,bad"])
        row(label + "a suite with a failed row is FAIL, its [FAIL] row is shown, the run exits 1",
            rc == 1 and verdict(out, "bad") == "FAIL" and "a row that failed" in out and verdict(out, "okay") == "PASS", "rc %d  %s" % (rc, out[-300:]))
        rc, out = run(root, ["--only", "badzero"])
        row(label + "a suite that exits 0 but says 1 failed is FAIL", rc == 1 and verdict(out, "badzero") == "FAIL", "rc %d  %s" % (rc, out[-200:]))
        rc, out = run(root, ["--only", "liar"])
        row(label + "a suite that says 0 failed but exits 1 is FAIL", rc == 1 and verdict(out, "liar") == "FAIL", "rc %d  %s" % (rc, out[-200:]))
        rc, out = run(root, ["--only", "silent"])
        row(label + "a suite that printed no verdict line is FAIL, and the line says so",
            rc == 1 and verdict(out, "silent") == "FAIL" and "no verdict line" in out, "rc %d  %s" % (rc, out[-200:]))
        rc, out = run(root, ["--only", "zero"])
        row(label + "a suite that passed no row is FAIL (the null case)", rc == 1 and verdict(out, "zero") == "FAIL", "rc %d  %s" % (rc, out[-200:]))
        rc, out = run(root, ["--only", "cannot"])
        row(label + "a suite that said CANNOT RUN is NOT RUN and the run exits 2", rc == 2 and verdict(out, "cannot") == "NOT RUN", "rc %d  %s" % (rc, out[-200:]))
        rc, out = run(root, ["--only", "cannot,bad"])
        row(label + "a failure outranks a suite that could not run: exit 1", rc == 1, "rc %d  %s" % (rc, out[-200:]))
        rc, out = run(root, ["--only", "nosuchsuite"])
        row(label + "an unknown suite is refused (exit 2), not skipped", rc == 2 and "no suite 'nosuchsuite'" in out, "rc %d  %s" % (rc, out[-200:]))
        rc, out = run(root, ["--only", "okay,bad", "--skip", "bad"])
        row(label + "--skip leaves a suite out: only the one left runs, and passes", rc == 0 and verdict(out, "bad") is None and verdict(out, "okay") == "PASS", "rc %d  %s" % (rc, out[-200:]))
        rc, out = run(root, ["--only", "okay"], held=True)
        row(label + "a sandbox already holding the shared memory keys is refused (exit 2) before any suite runs",
            rc == 2 and "already holds the shared memory keys" in out and verdict(out, "okay") is None, "rc %d  %s" % (rc, out[-200:]))
        rc, out = run(root, ["--only", "echo"])
        try:
            with open(os.path.join(root, "echo.args")) as f:
                seen = f.read()
        except OSError:
            seen = ""
        m = re.match(r"^(\S+) --build \| existed=False$", seen)
        row(label + "each suite is given a fresh directory that does not exist yet, and --build",
            rc == 0 and bool(m) and "sbx-echo" in seen, "rc %d  args %r" % (rc, seen))
        row(label + "...and that directory is gone afterwards", bool(m) and not os.path.exists(m.group(1)), repr(seen))
        rc, out = run(root, ["--list", "--only", "okay,bad", "--skip", "bad"])
        row(label + "--list prints the suites that would run and runs none", rc == 0 and out.split() == ["okay"], "rc %d  %r" % (rc, out))
    finally:
        shutil.rmtree(root, ignore_errors=True)
    return failed - before


# The seven breakages: (name, the text to find - exactly once - and what to put in its place)
MUTANTS = [
    ("the exit status is ignored", 'elif [ "$rc" -ne 0 ]; then', "elif false; then"),
    ("a failed count is ignored", 'elif [ "$failed" -ne 0 ]; then', "elif false; then"),
    ("a missing verdict line is not a failure", 'elif [ -z "$verdict" ]; then', "elif false; then"),
    ("a suite that passed no row is not a failure", 'elif [ "$passed" -eq 0 ]; then', "elif false; then"),
    ("CANNOT RUN is not recognised", 'if [ "$rc" -eq 2 ] || grep -q \'CANNOT RUN\' "$log"; then', "if false; then"),
    ("the held-keys refusal is gone", 'if [ -n "$held" ]; then', "if false; then"),
    ("a failed suite does not make the run exit 1", 'if [ "$failed_suites" -gt 0 ] || [ "$free_failed" -gt 0 ]; then exit 1; fi', "if false; then exit 1; fi"),
]


def main():
    with open(SCRIPT) as f:
        real = f.read()
    print("test-regress-units: %s" % SCRIPT)
    cases("", real)
    if "--selftest" in sys.argv:
        print("\n--selftest: seven broken copies of regress.sh, each of which must fail a case")
        global passed, failed, quiet
        for name, find, put in MUTANTS:
            if real.count(find) != 1:
                row("mutant '%s': the text to break occurs once in regress.sh" % name, False, "found %d times" % real.count(find))
                continue
            keep = (passed, failed)
            quiet = True
            broken = cases("", real.replace(find, put))
            quiet = False
            caught = broken > 0
            passed, failed = keep
            row("mutant '%s' is caught by a case" % name, caught, "every case passed on the broken copy")
    print("\ntest-regress-units: %d passed, %d failed" % (passed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
