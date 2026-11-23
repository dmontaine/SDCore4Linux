#!/usr/bin/env python3
# test-sdsysumask-units.py - S.268 (18 Nov 2026; found by the VM witness: verify-sysperms S1 on a fresh install of ad3b6879).  CPROC starts every session with
# umask 002, which an account needs (its directory's group is the account's own).  SDSYS's group is sdusers - every SD user - so in SDSYS that made what the
# administrator created there (examples.bp and its objects by load.examples, the command stack under stacks/) writable by every SD user.  The rule:
#   L1  login sets the umask from the account it has just entered, after `account.path = ospath("", OS$CWD)`: 022 (18) inside @sdsys, 002 (2) elsewhere
#   C1  cproc has set.account.umask doing the same on account.path
#   C2  ... called after LOGTO's load.account.switches, after RUN.IN's, and by revert.account (three gosubs)
#   C3  the session-start umask(002) is still there (an ordinary account needs it; S.268 does not change it)
#   A1  createa keeps the session's umask before !create_account (which sets 002) and gives it back right after
# FREE CHECK: the BASIC read as text; no install, no sd.  It cannot say a file is made 644 in SDSYS: that is verify-sysperms.py S1 on a real install.
#
#   python3 /home/don/SDCoreProject/SDCore4Linux/sdb_ai/sd64/gplbld/test-sdsysumask-units.py
#   python3 /home/don/SDCoreProject/SDCore4Linux/sdb_ai/sd64/gplbld/test-sdsysumask-units.py --selftest
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BP = os.environ.get("BPDIR", os.path.normpath(os.path.join(HERE, "..", "sdsys", "gpl.bp")))
RULE = re.compile(r"^\s*if kernel\(K\$PATH\.IN, @sdsys : @fm : account\.path\) then void umask\(18\) else void umask\(2\)", re.M)


def read(name):
    with open(os.path.join(BP, name), encoding="latin-1") as f:
        return f.read()


def code(text):
    """whole-line comments removed (they quote the rule)"""
    return "\n".join(l for l in text.split("\n") if not l.lstrip().startswith("*"))


def checks(src):
    rows = []
    login, cproc, createa = code(src["login"]), code(src["cproc"]), code(src["createa"])
    m = re.search(r'^\s*account\.path = ospath\("", OS\$CWD\)\s*$', login, re.M)
    r = RULE.search(login)
    rows.append(("L1 login sets the umask from the account right after account.path is taken (nothing but comments between)",
                 m is not None and r is not None and r.start() > m.start() and login[m.end():r.start()].strip() == ""))
    sub = re.search(r"^set\.account\.umask:\s*\n(.*?)^\s*return\s*$", cproc, re.M | re.S)
    rows.append(("C1 cproc's set.account.umask applies the rule to account.path", sub is not None and RULE.search(sub.group(1)) is not None))
    after_switches = re.findall(r"^\s*gosub load\.account\.switches\b[^\n]*\n\s*gosub set\.account\.umask\b", cproc, re.M)
    rev = re.search(r"^revert\.account:\s*\n(.*?)^\s*return\s*$", cproc, re.M | re.S)
    rows.append(("C2 set.account.umask follows load.account.switches twice (LOGTO, RUN.IN) and is called by revert.account", len(after_switches) == 2
                 and rev is not None and re.search(r"^\s*gosub set\.account\.umask\b", rev.group(1), re.M) is not None))
    rows.append(("C3 the session still starts with umask 002", re.search(r"^\s*if umask\(002\) then null", cproc, re.M) is not None))
    a = re.search(r"^\s*um\.keep = umask\(-1\)\s*\n\s*call !create_account\(.*\)\s*\n\s*void umask\(um\.keep\)\s*$", createa, re.M)
    rows.append(("A1 createa keeps the umask before !create_account and gives it back right after", a is not None))
    return rows


MUTANTS = [
    ("login-no-rule", "login", lambda t: t.replace("then void umask(18) else void umask(2)", "then null else null", 1)),
    ("login-swapped", "login", lambda t: t.replace("then void umask(18) else void umask(2)", "then void umask(2) else void umask(18)", 1)),
    ("cproc-sub-022-everywhere", "cproc", lambda t: t.replace("set.account.umask:\n   if kernel(K$PATH.IN, @sdsys : @fm : account.path) then void umask(18) else void umask(2)",
                                                              "set.account.umask:\n   void umask(18)", 1)),
    ("cproc-logto-no-call", "cproc", lambda t: t.replace("   gosub set.account.umask       ;* 18 Nov 26, S.268\n\n   void kernel(K$AUDIT, 'logto account='", "\n   void kernel(K$AUDIT, 'logto account='", 1)),
    ("cproc-revert-no-call", "cproc", lambda t: t.replace("   gosub set.account.umask                   ;* 18 Nov 26, S.268", "", 1)),
    ("cproc-start-022", "cproc", lambda t: t.replace("      if umask(002) then null", "      if umask(022) then null", 1)),
    ("createa-no-restore", "createa", lambda t: t.replace("   void umask(um.keep)\n", "", 1)),
]


def run(src, quiet=False):
    rows = checks(src)
    bad = [n for n, ok in rows if not ok]
    if not quiet:
        for n, ok in rows:
            print("  [%s] %s" % ("PASS" if ok else "FAIL", n))
    return rows, bad


def main():
    src = {n: read(n) for n in ("login", "cproc", "createa")}
    print("test-sdsysumask-units: gpl.bp = %s" % BP)
    rows, bad = run(src)
    if not rows:
        print("test-sdsysumask-units: FAILED - no row ran"); return 1
    if "--selftest" in sys.argv:
        missed = 0
        for name, prog, f in MUTANTS:
            m = dict(src)
            m[prog] = f(src[prog])
            if m[prog] == src[prog]:
                print("  [MUTANT %s] DID NOT APPLY (the text it changes is gone)" % name); missed += 1; continue
            _, b = run(m, quiet=True)
            print("  [MUTANT %s] %s" % (name, ("killed by " + ", ".join(x.split()[0] for x in b)) if b else "MISSED"))
            missed += 0 if b else 1
        if missed:
            print("test-sdsysumask-units: SELFTEST FAILED - %d mutant(s) missed or not applied" % missed); return 1
        print("test-sdsysumask-units: selftest - %d of %d mutants killed" % (len(MUTANTS), len(MUTANTS)))
    if bad:
        print("test-sdsysumask-units: %d passed, %d failed" % (len(rows) - len(bad), len(bad))); return 1
    print("test-sdsysumask-units: %d passed, 0 failed" % len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
