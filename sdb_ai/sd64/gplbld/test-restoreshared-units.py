#!/usr/bin/env python3
# test-restoreshared-units.py - RESTORE.ACCOUNT of the shared account (26 Oct 2026, found on the VM by the owner-run witness chain: witness-accounts.sh section 2e failed three rows on an
# install on which witness-backup.sh had restored every account first; a fresh install passed all 84).
#
# The shared account is registered with the group sdg_shared (who may sign on to it), but its DIRECTORY is sdusers (every SD user's process reads it through the kernel; create.account
# and the installer give it that).  !acc_os_place sent the register group to "sd-elevate restore-place", so a restore left the directory sdsys:sdg_shared and no ordinary user could read
# the shared account afterwards.  Now !acc_os_place sends sdusers for the account called shared, and restore_place in the helper accepts sdusers for that account and sdg_<name> for every
# other group account.  FREE CHECK: the two sources read as text (the helper's behaviour is test-accelevate-units.py's rows); no install, no sd.  The VM row is
# `RESTORE.ACCOUNT LATEST shared` and `stat` of the directory.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-restoreshared-units.py
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-restoreshared-units.py --selftest
#
#   P1  !acc_os_place sets the group sent to the helper to sdusers for the account called shared whose owner is sdsys, after the register group has chosen the owner and before the
#       quote test and the call, and only there
#   P2  the call sends that variable (grp) as the group
#   P3  the helper's restore_place holds the shared account to sdusers and every other group account to sdg_<name>
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.normpath(os.path.join(HERE, ".."))
PLACE = os.environ.get("ACC_OS_PLACE", os.path.join(SD64, "sdsys", "gpl.bp", "acc_os_place"))
HELPER = os.environ.get("HELPER", os.path.join(HERE, "sd-elevate"))


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def checks(place, helper):
    rows = []

    def row(name, ok, detail=""):
        rows.append((name, bool(ok), detail))

    lines = [l for l in place.split("\n")]

    def at(pred):
        return [i for i, l in enumerate(lines) if not l.lstrip().startswith("*") and pred(l)]

    case_end = at(lambda l: l.strip() == "end case")
    ovr = at(lambda l: l.strip() == "if acc.name = 'shared' and owner = 'sdsys' then grp = 'sdusers'")
    quote = at(lambda l: l.strip().startswith("if index(owner:grp:staged.path:target.path"))
    call = at(lambda l: "restore-place '\":owner:\"' '\":grp:\"'" in l)
    grp_sets = at(lambda l: re.search(r"\bgrp\s*=[^=]", l) is not None)
    row("P1 the shared account's group is set to sdusers (line %s), after the owner is chosen from the register group (end case %s) and before the quote test (%s); grp is assigned only there "
        "and from the register" % (ovr and ovr[0] + 1, case_end and case_end[0] + 1, quote and quote[0] + 1),
        len(ovr) == 1 and case_end and quote and case_end[0] < ovr[0] < quote[0] and len(grp_sets) == 2, "grp assigned at %s" % [i + 1 for i in grp_sets])
    row("P2 the helper is called with the owner and grp (line %s), after the override (%s)" % (call and call[0] + 1, ovr and ovr[0] + 1),
        len(call) == 1 and ovr and ovr[0] < call[0], "")

    m = re.search(r"^restore_place\(\) \{.*?^}\n", helper, re.S | re.M)
    body = m.group(0) if m else ""
    row("P3 restore_place: want is sdusers for shared and sdg_<name> for any other, and the group sent must equal it",
        'if [[ $tname == shared ]]; then want=sdusers; else want=sdg_$tname; fi' in body and '[[ $group == "$want" ]] || die' in body
        and body.index("want=sdusers") < body.index('[[ $group == "$want" ]] || die'), "")
    return rows


def run():
    rows = checks(read(PLACE), read(HELPER))
    bad = 0
    for name, ok, detail in rows:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, "" if ok else "   <- " + detail))
        bad += 0 if ok else 1
    print("test-restoreshared-units: %d passed, %d failed" % (len(rows) - bad, bad))
    return 1 if bad else 0


def selftest():
    place, helper = read(PLACE), read(HELPER)
    if not all(ok for _, ok, _ in checks(place, helper)):
        print("  [FAIL] the real files do not pass")
        return 1
    print("  [ok] the real files pass")
    caught = missed = 0

    def mutant(name, expect, fn, which="place"):
        nonlocal caught, missed
        p, h = place, helper
        if which == "place":
            p = fn(place)
        else:
            h = fn(helper)
        if (p, h) == (place, helper):
            print("  [MISSED] %s: the mutation changed nothing" % name)
            missed += 1
            return
        failing = [n for n, ok, _ in checks(p, h) if not ok]
        if any(f.startswith(expect + " ") for f in failing):
            print("  [caught] %s by %s" % (name, expect))
            caught += 1
        else:
            print("  [MISSED] %s: failed %s, wanted %s" % (name, [f[:2] for f in failing], expect))
            missed += 1

    OVR = "   if acc.name = 'shared' and owner = 'sdsys' then grp = 'sdusers'\n"
    mutant("override-gone", "P1", lambda s: s.replace(OVR, "", 1))
    mutant("override-for-every-group-account", "P1", lambda s: s.replace("if acc.name = 'shared' and owner = 'sdsys' then", "if owner = 'sdsys' then", 1))
    mutant("override-gives-the-register-group", "P1", lambda s: s.replace("then grp = 'sdusers'", "then grp = 'sdg_shared'", 1))
    mutant("override-after-the-call", "P2", lambda s: s.replace(OVR, "", 1).replace("   stat = os.error()\n", OVR + "   stat = os.error()\n", 1))
    mutant("helper-holds-shared-to-sdg", "P3", lambda s: s.replace("if [[ $tname == shared ]]; then want=sdusers; else want=sdg_$tname; fi", "want=sdg_$tname", 1), "helper")
    mutant("helper-group-not-compared", "P3", lambda s: s.replace('    [[ $group == "$want" ]] || die "group account', '    true || die "group account', 1), "helper")
    print("selftest: %d of %d mutants caught, %d missed" % (caught, caught + missed, missed))
    return 0 if missed == 0 else 1


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else run())
