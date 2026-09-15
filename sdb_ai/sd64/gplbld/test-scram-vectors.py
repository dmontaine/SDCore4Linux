#!/usr/bin/env python3
# test-scram-vectors.py - compiles gplbld/verify-scram.c with gplsrc/sd_scram.c
# against libsodium and runs it: the RFC 7677 section 3 vectors, the server-side
# verification path and the guards.  Added 14 Sep 2026 with W.4 phase 1, the
# Windows port's SCRAM primitives.
#
#   python3 /home/don/Projects/sdcore4linux/sdb_ai/sd64/gplbld/test-scram-vectors.py
#
# No sudo, no install, no sd.  Exit 0 every check passed, 1 a check failed,
# 2 it could not run (no compiler, no libsodium, a compile error).
#
# THE NULL CASE IS REFUSED: the program's own summary line must say how many
# checks ran, the count must be above zero, and "0 failed" must be the whole
# of the failure count - a program that compiled and printed nothing, or ran
# no checks, is not a pass.

import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.dirname(HERE)
SRC = os.path.join(HERE, "verify-scram.c")
LIB = os.path.join(SD64, "gplsrc", "sd_scram.c")
INC = os.path.join(SD64, "gplsrc")


def main():
    cc = shutil.which("cc") or shutil.which("gcc")
    print("test-scram-vectors")
    print("  compiler : %s" % (cc or "(none found)"))
    print("  test     : %s" % SRC)
    print("  library  : %s" % LIB)
    if cc is None:
        print("test-scram-vectors: CANNOT RUN - no C compiler on PATH.")
        return 2
    for path in (SRC, LIB):
        if not os.path.isfile(path):
            print("test-scram-vectors: CANNOT RUN - missing %s" % path)
            return 2

    tmp = tempfile.mkdtemp(prefix="scram-vectors-")
    try:
        exe = os.path.join(tmp, "verify-scram")
        cmd = [cc, "-Wall", "-Wextra", "-O2", "-o", exe, SRC, LIB,
               "-I" + INC, "-lsodium"]
        print("  command  : %s" % " ".join(cmd))
        build = subprocess.run(cmd, capture_output=True, text=True)
        if build.stdout or build.stderr:
            print("  --- compiler output ---")
            sys.stdout.write(build.stdout + build.stderr)
        if build.returncode != 0:
            print("test-scram-vectors: CANNOT RUN - compile failed (exit %d)."
                  % build.returncode)
            return 2
        if "warning" in (build.stdout + build.stderr).lower():
            print("test-scram-vectors: FAILED - the compile produced a warning.")
            return 1

        run = subprocess.run([exe], capture_output=True, text=True, timeout=120)
        print("  --- verify-scram output (exit %d) ---" % run.returncode)
        sys.stdout.write(run.stdout + run.stderr)

        m = re.search(r"^(\d+) checks, (\d+) failed$", run.stdout, re.M)
        if m is None:
            print("test-scram-vectors: FAILED - no summary line, so no checks "
                  "can be counted.")
            return 1
        ran, failed = int(m.group(1)), int(m.group(2))
        if ran == 0:
            print("test-scram-vectors: FAILED - zero checks ran.")
            return 1
        if run.returncode != 0 or failed != 0:
            print("test-scram-vectors: FAILED - %d of %d checks failed "
                  "(exit %d)." % (failed, ran, run.returncode))
            return 1
        print("test-scram-vectors: PASSED - %d of %d checks." % (ran, ran))
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
