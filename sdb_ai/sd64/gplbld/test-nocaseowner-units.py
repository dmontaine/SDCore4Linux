#!/usr/bin/env python3
# test-nocaseowner-units.py - upgrade_nocase reads the flag of a file outside the account under the walk's OWN identity (S.296, found by the VM
# witness of 22 Nov 2026), read off the source as text.  Free: no install, no sudo, no sd.
#
#   python3 /home/don/SDCoreProject/SDCore4Linux/sdb_ai/sd64/gplbld/test-nocaseowner-units.py [--selftest]
#
# WHY.  The install runs upgrade_nocase as root and walks each account as its OWNER (!euid_set).  dh_open asks access() whether a file may be
# written, which answers for the REAL user (root), and then opens it read-write as the EFFECTIVE user (the owner), who cannot write SDSYS's files:
# the open failed, the flag was never read, and every SDSYS file a VOC names was counted and named on every Keep reinstall.  No sandbox shows it
# (real and effective user are the same there), so these rows hold the order of the fix:
#
#   N1  in the outside-the-account branch, the identity is given back (euid_restore) BEFORE the read only open and taken again (euid_set) AFTER it,
#       both only when the walk had switched
#   N2  the flag is read inside that window, from the read only open, and the file is never converted from there
#   N3  an owner's identity that cannot be taken again sets owner.lost; convert.one returns at once while it is set; the account is then reported
#       skipped (11029), counted, and its identity given back before the next account
#   N4  every name the routine reads is assigned before any walk
#   N5  the history line says why
#
# It cannot say the warning is gone on a real install: that is the VM witness (a Keep reinstall's /var/tmp/sdcore-install-nocase.log).
# Exit 0 every check held, 1 one did not, 2 it could not run.

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, os.pardir, "sdsys", "gpl.bp", "upgrade_nocase")
ME = "test-nocaseowner-units"


def read():
    try:
        with open(SRC, encoding="latin-1") as f:
            return f.read()
    except OSError:
        print("%s: CANNOT RUN - no %s" % (ME, SRC))
        sys.exit(2)


def code(src):
    return "\n".join(re.sub(r"\s*;\*.*$", "", ln) for ln in src.split("\n") if not ln.lstrip().startswith("*"))


def ordered(text, *needles):
    at = 0
    for n in needles:
        at = text.find(n, at)
        if at < 0:
            return False
        at += len(n)
    return True


def block(text, label):
    m = re.search(r"(?m)^" + re.escape(label) + r":\s*$", text)
    if not m:
        return ""
    n = re.search(r"(?m)^[a-z][a-z0-9.]*:\s*$", text[m.end():])
    return text[m.start(): m.end() + (n.start() if n else len(text))]


def checks(raw):
    out = []

    def ck(n, what, ok):
        out.append((n, what, bool(ok)))

    c = code(raw)
    co = block(c, "convert.one")
    br = co[co.find("if in.sds or not(in.acct) then"):co.find("openpath one.path to old.fu on error")]
    ck("N1", "the identity is given back before the read only open and taken again after it, only when the walk had switched",
       ordered(br, "if switched then call !euid_restore(rc.back)", "openpath one.path readonly to chk.fu on error", "end then", "end else", "end",
               "if switched then", "call !euid_set(owner, rc.again)", "if rc.again # 0 then owner.lost = @true", "end", "if is.nc then return")
       and br.count("!euid_restore(") == 1 and br.count("!euid_set(") == 1)
    ck("N2", "the flag is read in that window, from the read only open; nothing in the branch converts or writes",
       ordered(br, "!euid_restore(rc.back)", "is.nc = bitand(fileinfo(chk.fu, FL$FLAGS), FL$FLAGS.NOCASE)", "close chk.fu", "!euid_set(owner, rc.again)")
       and not re.search(r"\b(create\.file|write|delete|clearfile|osdelete)\b", br) and "readonly" in br)
    da = block(c, "do.account.as.owner")
    ck("N3", "owner.lost stops the account: convert.one returns at once, the account is reported (11029) and counted, the identity given back",
       re.search(r"convert\.one:\s*\n\s*if owner\.lost then return", c) is not None
       and ordered(da, "owner.lost = @false", "gosub do.account.at", "if owner.lost then", "crt sysmsg(11029, reg.name, owner, rc.again)", "acct.skipped += 1",
                   "owner.lost = @false", "if switched then call !euid_restore(rc)", "return", "end", "gosub fix.cat.names"))
    top = c[:c.find("\ndo.account.as.owner:")]
    ck("N4", "switched, owner, owner.lost and rc.again are assigned before any walk",
       re.search(r"switched = @false ; owner = '' ; owner\.lost = @false ; rc\.again = 0", top) is not None)
    ck("N5", "the history says why (the real and the effective user)", "22 Nov 26 dm  S.296, from the VM witness" in raw)
    return out


MUTANTS = [
    ("the open made as the owner again (no give-back)", "      if switched then call !euid_restore(rc.back)\n", ""),
    ("the identity not taken again", "         call !euid_set(owner, rc.again)\n", ""),
    ("given back after the open", "      if switched then call !euid_restore(rc.back)\n      openpath one.path readonly to chk.fu on error",
     "      openpath one.path readonly to chk.fu on error"),
    ("a lost owner not noticed", "         if rc.again # 0 then owner.lost = @true", "         null"),
    ("convert.one goes on as the walk's own user", "   if owner.lost then return          ;*", "   null          ;*"),
    ("a lost owner's account not reported", "      crt sysmsg(11029, reg.name, owner, rc.again)", "      null"),
    ("the flag read when the walk had not switched (unconditional give-back)", "      if switched then call !euid_restore(rc.back)", "      call !euid_restore(rc.back)"),
    ("owner.lost unassigned at the start", "switched = @false ; owner = '' ; owner.lost = @false ; rc.again = 0", "switched = @false"),
]


def main():
    raw = read()
    if "--selftest" in sys.argv:
        if not all(ok for _, _, ok in checks(raw)):
            print("%s: the real tree does not pass" % ME)
            return 1
        missed = 0
        for label, old, new in MUTANTS:
            if raw.count(old) != 1:
                print("  [MISSED] %s: the text is found %d times, not once" % (label, raw.count(old)))
                missed += 1
                continue
            caught = not all(ok for _, _, ok in checks(raw.replace(old, new, 1)))
            print("  [%s] %s" % ("caught" if caught else "MISSED", label))
            missed += not caught
        print("selftest: %d caught, %d missed" % (len(MUTANTS) - missed, missed))
        return 1 if missed else 0
    print("%s: %s" % (ME, os.path.normpath(SRC)))
    res = checks(raw)
    for n, what, ok in res:
        print("  [%s] %s %s" % ("PASS" if ok else "FAIL", n, what))
    bad = sum(1 for r in res if not r[2])
    print("%s: %d passed, %d failed" % (ME, len(res) - bad, bad))
    return 1 if bad or not res else 0


if __name__ == "__main__":
    sys.exit(main())
