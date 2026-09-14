#!/usr/bin/env python3
# test-staleleads-units.py - drives check-stale-leads.py against fixture
# documents, one injected defect at a time.  Added 14 Sep 2026 with the task
# table and phase 2; modelled on the port's test of the same name.
#
#   python3 gplbld/test-staleleads-units.py
#
# No sudo, no install, no sd.  Exit 0 all cases passed, 1 a case failed.
#
# Case 0 is a POSITIVE control: the clean fixture must pass, or every injected
# failure after it proves nothing.  Every mutation must match its fixture text,
# or the case fails - an injection that changed nothing is not a test.  The
# mutant at the end copies the checker, disables its "NO ROW" guard lines, and
# requires case 3 to go GREEN against the copy, so that case is shown to rest
# on the guard and not on something incidental.

import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKER = os.path.join(HERE, "check-stale-leads.py")

TICK, PART, OPEN, GONE = "✅", "◐", "⬜", "➖"
DASH = "—"

ROWS = ("| %s | **P.2** | S | fix two | %s |\n" % (OPEN, DASH)
        + "| %s | **Q.5** | M | queue five; left: the other half | %s |\n" % (PART, DASH)
        + "| %s | **S.1** | XL | the library | %s |\n" % (OPEN, DASH)
        + "| %s | **W.1** | M | the ruling | %s |\n" % (OPEN, DASH)
        + "| %s | **P.1** | XS | fixed one | 14 Sep 2026 |\n" % TICK)

FIXTURE = {
    "PROJECT_STATUS.md": (
        "# PROJECT_STATUS.md\n\n"
        "## THE TASK TABLE %s READ THIS BEFORE ANSWERING \"WHAT IS LEFT\"\n\n" % DASH
        + "| | ID | cost | what | settled |\n|---|---|---|---|---|\n"
        + ROWS
        + "\n## START HERE\n\n"
        "- A bullet that makes no status claim at all.\n\n"
        "### [S.1] The library (PROPOSED; NOT STARTED)\n"),
    "PRE_RELEASE_FIXES.md": (
        "# PRE-RELEASE FIXES\n\n"
        "| | SEV | What | Where |\n|---|---|---|---|\n"
        "| ~~1~~ | **S** | ***FIXED 14 Sep.*** one | x |\n"
        "| 2 | **S** | two, nothing done yet | y |\n"),
    "PORT_ADOPTION.md": (
        "# PORT_ADOPTION.md\n\n"
        "## Waiting for the owner\n\n"
        "1. [W.1] **A question** nobody has answered.\n\n"
        "## Queue %s adoptable, not yet done (suggested order)\n\n" % DASH
        + "| # | Feature | Port code | Linux adaptation |\n|---|---|---|---|\n"
        + "| ~~4~~ | ~~done thing~~ %s **BUILT 11 Sep** | x | |\n" % DASH
        + "| 5 | half thing %s WITNESSED one half; the other half UNWITNESSED | x | |\n" % DASH),
}

PS, PR, PA = "PROJECT_STATUS.md", "PRE_RELEASE_FIXES.md", "PORT_ADOPTION.md"
BULLET = "- A bullet that makes no status claim at all.\n"

# (name, [(file, old, new)], wanted exit, text the output must contain)
CASES = [
    ("clean fixture passes (positive control)", [], 0, "0 disagreement(s)"),
    ("open row, struck entry",
     [(PR, "| 2 | **S** |", "| ~~2~~ | **S** |")], 1, "is struck"),
    ("ticked row, entry not struck",
     [(PR, "| ~~1~~ |", "| 1 |")], 1, "is not struck"),
    ("open entry with no row",
     [(PR, "| 2 | **S** | two, nothing done yet | y |\n",
       "| 2 | **S** | two, nothing done yet | y |\n| 3 | **M** | three | z |\n")],
     1, "NO ROW"),
    ("row with no entry",
     [(PS, ROWS, ROWS + "| %s | **P.9** | S | nine | %s |\n" % (OPEN, DASH))],
     1, "has no entry"),
    ("partly-closed row names nothing left",
     [(PS, "; left: the other half", "")], 1, "('left:')"),
    ("partly-closed entry with no open claim",
     [(PA, "UNWITNESSED", "pending")], 1, "both a closure and an open claim"),
    ("tag with no row",
     [(PS, "(PROPOSED; NOT STARTED)\n",
       "(PROPOSED; NOT STARTED)\n### [S.2] Another (NOT STARTED)\n")], 1, "NO ROW"),
    ("ticked row whose own words read open",
     [(PS, "| fixed one |", "| fixed one, NOT RUN |")], 1, "own words read as open"),
    ("open row, tagged entry leads with a closure",
     [(PS, "(PROPOSED; NOT STARTED)", "(DONE 14 Sep 2026)")],
     1, "FINISHED WORK NEVER TICKED OFF"),
    ("no task table heading",
     [(PS, "## THE TASK TABLE", "## A TABLE")], 2, "CANNOT ANSWER"),
    ("task table with no rows", [(PS, ROWS, "")], 2, "no task table rows"),
    ("queue table missing",
     [(PA, "## Queue %s adoptable" % DASH, "## Queue %s elsewhere" % DASH)],
     2, "no PORT_ADOPTION.md queue rows"),
    ("phase 1 still decides",
     [(PS, BULLET, BULLET + "- Opens PENDING a ruling. " + "x " * 170
       + "Then the body says it is DONE.\n")], 1, "STALE LEAD"),
    ("a tag used twice",
     [(PA, "nobody has answered.\n",
       "nobody has answered.\nA note that repeats [S.1] by mistake.\n")],
     1, "found 2"),
    ("unknown mark",
     [(PS, "| %s | **W.1** |" % OPEN, "| O | **W.1** |")], 1, "unknown mark"),
]


def write_fixture(directory, mutations):
    texts = dict(FIXTURE)
    for name, old, new in mutations:
        if old not in texts[name]:
            return None, "mutation matched nothing in %s: %r" % (name, old[:50])
        texts[name] = texts[name].replace(old, new, 1)
    paths = []
    for name in (PS, PR, PA):
        path = os.path.join(directory, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(texts[name])
        paths.append(path)
    return paths, None


def run(checker, docs):
    proc = subprocess.run([sys.executable, checker] + docs,
                          capture_output=True, text=True, timeout=60)
    return proc.returncode, proc.stdout + proc.stderr


def report(ok, label, detail, out=None):
    print("[%s] %s: %s" % ("PASS" if ok else "FAIL", label, detail))
    if not ok and out:
        for line in out.splitlines()[-12:]:
            print("       | " + line)


def main():
    print("test-staleleads-units")
    print("checker : %s" % CHECKER)
    print("python  : %s" % sys.executable)
    if not os.path.isfile(CHECKER):
        print("CANNOT RUN: no checker at that path.")
        return 1
    base = tempfile.mkdtemp(prefix="staleleads-")
    print("fixtures: %s" % base)
    ran = failed = 0
    try:
        for i, (name, mutations, want, needle) in enumerate(CASES):
            case_dir = os.path.join(base, "case%02d" % i)
            os.mkdir(case_dir)
            docs, why = write_fixture(case_dir, mutations)
            ran += 1
            if docs is None:
                failed += 1
                report(False, "%2d %s" % (i, name), why)
                continue
            code, out = run(CHECKER, docs)
            ok = code == want and needle in out
            failed += not ok
            report(ok, "%2d %s" % (i, name),
                   "exit %d (wanted %d), %r %s" % (code, want, needle,
                                                   "found" if needle in out else "MISSING"),
                   out)

        # The live documents: the shapes must still parse (exit 0 or 1, not 2).
        code, out = run(CHECKER, [])
        ok = code in (0, 1) and "table rows:" in out
        ran += 1
        failed += not ok
        report(ok, "live documents parse",
               "exit %d (wanted 0 or 1), table rows line %s"
               % (code, "found" if "table rows:" in out else "MISSING"), out)

        # The mutant: the "NO ROW" guard disabled must turn case 3 green.
        with open(CHECKER, encoding="utf-8") as fh:
            source = fh.read().splitlines(True)
        disabled = 0
        for n, line in enumerate(source):
            if "NO ROW" in line and "problems.append(" in line:
                source[n] = line.replace("problems.append(", "(lambda *a: None)(")
                disabled += 1
        mutant = os.path.join(base, "check-stale-leads-mutant.py")
        with open(mutant, "w", encoding="utf-8") as fh:
            fh.write("".join(source))
        mutant_dir = os.path.join(base, "mutant")
        os.mkdir(mutant_dir)
        docs, why = write_fixture(mutant_dir, CASES[3][1])
        code, out = run(mutant, docs) if docs else (-1, why)
        ok = disabled >= 1 and code == 0
        ran += 1
        failed += not ok
        report(ok, "mutant control",
               "%d guard line(s) disabled; case 3 against the mutant exits %d "
               "(wanted 0 - the guard is what catches it)" % (disabled, code), out)
    finally:
        shutil.rmtree(base, ignore_errors=True)

    if ran == 0:
        print("NOTHING RAN - that is a failure, not a pass.")
        return 1
    print("test-staleleads-units: %d cases, %d failed" % (ran, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
