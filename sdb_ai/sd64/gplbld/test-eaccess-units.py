#!/usr/bin/env python3
# test-eaccess-units.py - the kernel decides whether a file may be written for the EFFECTIVE user, the one the open is made as (S.308, found by
# S.296's VM witness of 22 Nov 2026), read off gplsrc as text.  Free: no install, no sudo, no sd.
#
#   python3 /home/don/SDCoreProject/SDCore4Linux/sdb_ai/sd64/gplbld/test-eaccess-units.py [--selftest]
#
#   E1  no write test with access() is left in gplsrc (access(p, 2) or access(p, W_OK)): access() answers for the REAL user, and after an
#       identity switch (root running SD, !euid_set to an account's owner) a file the owner may only read was opened read-write and failed
#   E2  dh_open's two subfile opens choose read-only by faccessat(AT_FDCWD, ..., W_OK, AT_EACCESS) right before the dio_open they decide
#   E3  OPENSEQ's read-write choice and DELETESEQ's write check use the same call
#   E4  both files include <fcntl.h> (AT_FDCWD, AT_EACCESS) and <unistd.h>
#
# It cannot say an open after an identity switch now succeeds read-only: no sandbox switches identity (it is not root).  Existence tests
# (access(p, 0)) are left alone: they do not decide what the open may do.  Exit 0 every check held, 1 one did not, 2 it could not run.

import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
G = os.path.join(HERE, os.pardir, "gplsrc")
ME = "test-eaccess-units"
EA = "faccessat(AT_FDCWD, %s, W_OK, AT_EACCESS)"


def load():
    raw = {}
    for p in sorted(glob.glob(os.path.join(G, "*.c"))):
        with open(p, encoding="latin-1") as f:
            raw[os.path.basename(p)] = f.read()
    if "dh_open.c" not in raw or "op_seqio.c" not in raw:
        print("%s: CANNOT RUN - no gplsrc/dh_open.c or op_seqio.c under %s" % (ME, G))
        sys.exit(2)
    return raw


def code(src):
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    return re.sub(r"//[^\n]*", "", src)


def checks(raw):
    out = []

    def ck(n, what, ok, detail=""):
        out.append((n, what, bool(ok), detail))

    bad = []
    for name, src in raw.items():
        for m in re.finditer(r"(?<![a-z_])access\(\s*([^,()]+),\s*(2|W_OK)\s*\)", code(src)):
            bad.append("%s: %s" % (name, m.group(0)))
    ck("E1", "no write test with access() is left in gplsrc (it answers for the real user)", not bad, bad)
    dh = code(raw["dh_open.c"])
    ck("E2", "dh_open: both subfile opens choose read-only by the effective user, right before the open they decide",
       re.search(re.escape("if (" + EA % "pathname" + ")") + r"\s*read_only = TRUE;\s*fu = dio_open\(pathname,", dh) is not None
       and re.search(re.escape("if (" + EA % "pathname" + ")") + r"\s*read_only = TRUE;\s*ofu = dio_open\(pathname,", dh) is not None)
    sq = code(raw["op_seqio.c"])
    ck("E3", "OPENSEQ's read-write choice and DELETESEQ's write check ask the effective user",
       ("if (" + EA % "file_name" + ") {") in sq and ("(op_flags & P_READONLY) || " + EA % "fullpathname" + " || edit_blocked") in sq)
    ck("E4", "dh_open.c and op_seqio.c include <fcntl.h> and <unistd.h>",
       all("#include <fcntl.h>" in raw[n] and "#include <unistd.h>" in raw[n] for n in ("dh_open.c", "op_seqio.c")))
    return out


MUTANTS = [
    ("dh_open's primary subfile asks the real user again", "dh_open.c",
     "  if (faccessat(AT_FDCWD, pathname, W_OK, AT_EACCESS))     /* S.308: the user the open is made as, not the real one */",
     "  if (access(pathname, 2))"),
    ("dh_open's overflow subfile asks the real user again", "dh_open.c",
     "  if (faccessat(AT_FDCWD, pathname, W_OK, AT_EACCESS))     /* S.308: as above */", "  if (access(pathname, W_OK))"),
    ("OPENSEQ asks the real user again", "op_seqio.c", "faccessat(AT_FDCWD, fullpathname, W_OK, AT_EACCESS) || edit_blocked", "access(fullpathname, 2) || edit_blocked"),
    ("DELETESEQ asks the real user again", "op_seqio.c", "  if (faccessat(AT_FDCWD, file_name, W_OK, AT_EACCESS)) {", "  if (access(file_name, 2)) {"),
    ("the effective flag dropped", "op_seqio.c", "faccessat(AT_FDCWD, fullpathname, W_OK, AT_EACCESS) || edit_blocked", "faccessat(AT_FDCWD, fullpathname, W_OK, 0) || edit_blocked"),
    ("the include dropped", "dh_open.c", "#include <fcntl.h>      /* 22 Nov 26 - S.308", "/* 22 Nov 26 - S.308"),
]


def main():
    raw = load()
    if "--selftest" in sys.argv:
        if not all(r[2] for r in checks(raw)):
            print("%s: the real tree does not pass" % ME)
            return 1
        missed = 0
        for label, name, old, new in MUTANTS:
            if raw[name].count(old) != 1:
                print("  [MISSED] %s: the text is found %d times, not once" % (label, raw[name].count(old)))
                missed += 1
                continue
            changed = dict(raw)
            changed[name] = raw[name].replace(old, new, 1)
            caught = not all(r[2] for r in checks(changed))
            print("  [%s] %s" % ("caught" if caught else "MISSED", label))
            missed += not caught
        print("selftest: %d caught, %d missed" % (len(MUTANTS) - missed, missed))
        return 1 if missed else 0
    print("%s: %s" % (ME, os.path.normpath(G)))
    res = checks(raw)
    for n, what, ok, detail in res:
        print("  [%s] %s %s%s" % ("PASS" if ok else "FAIL", n, what, "" if ok or not detail else "   <- %s" % detail))
    bad = sum(1 for r in res if not r[2])
    print("%s: %d passed, %d failed" % (ME, len(res) - bad, bad))
    return 1 if bad or not res else 0


if __name__ == "__main__":
    sys.exit(main())
