#!/usr/bin/env python3
# test-scram-vectors.py - compiles and runs both SCRAM vector tests: the SERVER
# primitives (gplbld/verify-scram.c with gplsrc/sd_scram.c, against libsodium)
# and the CLIENT primitives (gplbld/verify-scramclient.c with
# gplsrc/scram_client.h, no library).  RFC 7677 section 3 vectors, the
# verification path and the guards.  Added 14 Sep 2026 with W.4 phase 1; the
# client half joined with phase 4, the same day.
#
#   python3 /home/don/Projects/SDCoreLinuxProject/sdcore4linux/sdb_ai/sd64/gplbld/test-scram-vectors.py
#
# No sudo, no install, no sd.  Exit 0 every check passed, 1 a check failed,
# 2 it could not run (no compiler, no libsodium, a compile error).
#
# THE NULL CASE IS REFUSED, per program: each one's own summary line must say
# how many checks ran, the count must be above zero, and none may have failed -
# a program that compiled and printed nothing, or ran no checks, is not a pass.

import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.dirname(HERE)
INC = os.path.join(SD64, "gplsrc")

# (name, sources, extra link flags, summary regex -> (ran, failed))
PROGRAMS = [
    ("verify-scram (server, sd_scram.c)",
     [os.path.join(HERE, "verify-scram.c"), os.path.join(INC, "sd_scram.c")],
     ["-lsodium"],
     lambda out: _counts(r"^(\d+) checks, (\d+) failed$", out, lambda a, b: (a, b))),
    ("verify-scramclient (client, scram_client.h)",
     [os.path.join(HERE, "verify-scramclient.c")],
     [],
     lambda out: _counts(r"^(\d+) of (\d+) checks passed$", out, lambda p, t: (t, t - p))),
]


def _counts(pattern, text, convert):
    m = re.search(pattern, text, re.M)
    if m is None:
        return None
    return convert(int(m.group(1)), int(m.group(2)))


def run_one(cc, tmp, name, sources, libs, summary):
    print("")
    print("== %s" % name)
    for path in sources:
        if not os.path.isfile(path):
            print("  CANNOT RUN - missing %s" % path)
            return 2, 0
    exe = os.path.join(tmp, "prog%d" % len(os.listdir(tmp)))
    cmd = [cc, "-std=gnu17", "-Wall", "-Wextra", "-O2", "-o", exe] + sources + ["-I" + INC] + libs
    print("  command  : %s" % " ".join(cmd))
    build = subprocess.run(cmd, capture_output=True, text=True)
    if build.stdout or build.stderr:
        print("  --- compiler output ---")
        sys.stdout.write(build.stdout + build.stderr)
    if build.returncode != 0:
        print("  CANNOT RUN - compile failed (exit %d)." % build.returncode)
        return 2, 0
    if "warning" in (build.stdout + build.stderr).lower():
        print("  FAILED - the compile produced a warning.")
        return 1, 0

    run = subprocess.run([exe], capture_output=True, text=True, timeout=300)
    print("  --- output (exit %d) ---" % run.returncode)
    sys.stdout.write(run.stdout + run.stderr)
    counts = summary(run.stdout)
    if counts is None:
        print("  FAILED - no summary line, so no checks can be counted.")
        return 1, 0
    ran, failed = counts
    if ran == 0:
        print("  FAILED - zero checks ran.")
        return 1, 0
    if run.returncode != 0 or failed != 0:
        print("  FAILED - %d of %d checks failed (exit %d)." % (failed, ran, run.returncode))
        return 1, ran
    print("  PASSED - %d of %d checks." % (ran, ran))
    return 0, ran


def main():
    cc = shutil.which("cc") or shutil.which("gcc")
    print("test-scram-vectors")
    print("  compiler : %s" % (cc or "(none found)"))
    if cc is None:
        print("test-scram-vectors: CANNOT RUN - no C compiler on PATH.")
        return 2

    tmp = tempfile.mkdtemp(prefix="scram-vectors-")
    worst = 0
    total = 0
    try:
        for name, sources, libs, summary in PROGRAMS:
            rc, ran = run_one(cc, tmp, name, sources, libs, summary)
            total += ran
            worst = max(worst, rc)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("")
    if worst == 2:
        print("test-scram-vectors: CANNOT RUN - a program did not build.")
    elif worst == 1:
        print("test-scram-vectors: FAILED - see above.")
    else:
        print("test-scram-vectors: PASSED - %d checks across %d programs." % (total, len(PROGRAMS)))
    return worst


if __name__ == "__main__":
    sys.exit(main())
