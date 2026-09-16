#!/usr/bin/env python3
# test-tls-relay.py - compiles and runs gplbld/verify-tls.c against
# gplsrc/sd_tls.c and gplsrc/sd_tlssrv.c: the API's TLS relay and client, in a
# sandbox.  S.19, 15 Sep 2026.
#
#   python3 /home/don/Projects/SDCoreLinuxProject/sdcore4linux/sdb_ai/sd64/gplbld/test-tls-relay.py
#
# No sudo, no install, no sd.  Exit 0 every check passed, 1 a check failed,
# 2 it could not run (no compiler, no OpenSSL headers, a compile error).
#
# OPENSSL HEADERS: the system's (/usr/include/openssl, package libssl-dev,
# which installsdai.sh installs) when present.  Otherwise SD_OPENSSL_INC
# (directories, ':'-separated) and SD_OPENSSL_LIBS (link arguments) must both
# be set, and the run says loudly that it did not use the system headers.
#
# THE NULL CASE IS REFUSED: the program's summary line must count more than
# zero checks, and verify-tls itself refuses a directory that already holds an
# identity, since "the first connection creates it" could not then be seen.

import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.dirname(HERE)
INC = os.path.join(SD64, "gplsrc")
SOURCES = [os.path.join(HERE, "verify-tls.c"),
           os.path.join(INC, "sd_tls.c"),
           os.path.join(INC, "sd_tlssrv.c")]


def openssl_flags():
    if os.path.isfile("/usr/include/openssl/ssl.h"):
        return [], ["-lssl", "-lcrypto"], "system (/usr/include/openssl)"
    inc = os.environ.get("SD_OPENSSL_INC", "")
    libs = os.environ.get("SD_OPENSSL_LIBS", "")
    if inc and libs:
        return (["-I" + d for d in inc.split(":") if d], libs.split(),
                "SD_OPENSSL_INC/SD_OPENSSL_LIBS - NOT the system headers")
    return None


def main():
    print("test-tls-relay: sources  %s" % " ".join(SOURCES))
    for path in SOURCES:
        if not os.path.isfile(path):
            print("CANNOT RUN - missing %s" % path)
            return 2

    cc = shutil.which("gcc") or shutil.which("cc")
    if cc is None:
        print("CANNOT RUN - no C compiler")
        return 2

    flags = openssl_flags()
    if flags is None:
        print("CANNOT RUN - no OpenSSL headers.  Install libssl-dev (the "
              "installer does), or set SD_OPENSSL_INC and SD_OPENSSL_LIBS.")
        return 2
    inc_flags, lib_flags, source = flags
    print("test-tls-relay: openssl  %s" % source)

    tmp = tempfile.mkdtemp(prefix="sdtls.")
    try:
        exe = os.path.join(tmp, "verify-tls")
        identity = os.path.join(tmp, "identity")
        cmd = ([cc, "-std=gnu17", "-Wall", "-Wextra", "-O2", "-o", exe] +
               SOURCES + ["-I" + INC] + inc_flags + lib_flags)
        print("test-tls-relay: command  %s" % " ".join(cmd))
        build = subprocess.run(cmd, capture_output=True, text=True)
        if build.stdout or build.stderr:
            print("--- compiler output ---")
            sys.stdout.write(build.stdout + build.stderr)
        if build.returncode != 0:
            print("CANNOT RUN - compile failed (exit %d)." % build.returncode)
            return 2
        if "warning" in (build.stdout + build.stderr).lower():
            print("FAILED - the compile produced a warning.")
            return 1

        run_cmd = [exe, identity]
        print("test-tls-relay: run      %s" % " ".join(run_cmd))
        run = subprocess.run(run_cmd, capture_output=True, text=True,
                             timeout=180)
        print("--- output (exit %d) ---" % run.returncode)
        sys.stdout.write(run.stdout + run.stderr)

        m = re.search(r"^(\d+) checks, (\d+) failed$", run.stdout, re.M)
        if m is None:
            print("FAILED - no summary line, so no checks can be counted.")
            return 1
        ran, failed = int(m.group(1)), int(m.group(2))
        if ran == 0:
            print("FAILED - zero checks ran.")
            return 1
        if failed or run.returncode != 0:
            print("FAILED - %d of %d checks failed (exit %d)."
                  % (failed, ran, run.returncode))
            return 1
        print("PASSED - %d of %d checks." % (ran, ran))
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
