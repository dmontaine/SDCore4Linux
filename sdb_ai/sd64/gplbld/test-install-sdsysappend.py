#!/usr/bin/env python3
# test-install-sdsysappend.py - the installer must not strip the sdsys user's groups (26 Oct 2026, found on the VM by a kept-accounts install: sdg_shared held only root afterwards,
# witness-accounts.sh S4).  `usermod -g sdusers -G sdusers sdsys` REPLACES the supplementary group list; with -a it appends.  Run on every install, the replacing form took an
# existing sdsys user out of the group of every kept group account (sdg_shared, sdg_<name>) and out of every sdu_ group the up-front question had been told to keep.  FREE CHECK: the
# installer read as text; no install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-sdsysappend.py
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-sdsysappend.py --selftest
#
#   A1  the installer's one command that sets the sdsys user's groups is `sudo usermod -g sdusers -a -G sdusers sdsys`, once
#   A2  no `usermod` of the installer names sdsys with -G and without -a (nor `gpasswd -M`, `usermod -G` in any shape that replaces the list)
#   A3  that line comes before the ruling's call and after the user is created or found
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
INST = os.environ.get("INSTALLER", os.path.normpath(os.path.join(HERE, "..", "..", "..", "installsdcore.sh")))


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def checks(text):
    rows = []
    lines = text.split("\n")
    code = [(i, l) for i, l in enumerate(lines) if not l.lstrip().startswith("#")]
    good = [i for i, l in code if l.strip() == "sudo usermod -g sdusers -a -G sdusers sdsys"]
    rows.append(("A1 the sdsys user's groups are set once, by appending (line %s)" % (good and good[0] + 1), len(good) == 1, "found at %s" % good))
    replacing = [i + 1 for i, l in code if re.search(r"\busermod\b", l) and re.search(r"\bsdsys\b", l) and re.search(r"(^|\s)-G\b", l) and not re.search(r"(^|\s)-a\b|(^|\s)-aG\b", l)]
    gp = [i + 1 for i, l in code if re.search(r"\bgpasswd\s+-M\b", l)]
    rows.append(("A2 no usermod of the installer replaces the sdsys user's supplementary groups, and no gpasswd -M (%s, %s)" % (replacing, gp), not replacing and not gp, ""))
    made = [i for i, l in code if "useradd -g sdusers -G sdusers" in l and l.strip().endswith("sdsys; then") or "useradd -g sdusers -G sdusers" in l]
    ruling = [i for i, l in code if re.match(r"\s*sdsys_groups_ruling\b", l) and "()" not in l]
    rows.append(("A3 the line is after the user is created (%s) and before the ruling is called (%s)" % (made and made[0] + 1, ruling and ruling[0] + 1),
                 bool(good and made and ruling and made[0] < good[0] < ruling[0]), "good %s made %s ruling %s" % (good, made, ruling)))
    return rows


def run():
    rows = checks(read(INST))
    bad = 0
    for name, ok, detail in rows:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, "" if ok else "   <- " + detail))
        bad += 0 if ok else 1
    print("test-install-sdsysappend: %d passed, %d failed" % (len(rows) - bad, bad))
    return 1 if bad else 0


def selftest():
    text = read(INST)
    if not all(ok for _, ok, _ in checks(text)):
        print("  [FAIL] the real installer does not pass")
        return 1
    print("  [ok] the real installer passes")
    caught = missed = 0
    GOOD = "sudo usermod -g sdusers -a -G sdusers sdsys"

    def mutant(name, expect, new):
        nonlocal caught, missed
        if new == text:
            print("  [MISSED] %s: the mutation changed nothing" % name)
            missed += 1
            return
        failing = [n for n, ok, _ in checks(new) if not ok]
        if any(f.startswith(expect + " ") for f in failing):
            print("  [caught] %s by %s" % (name, expect))
            caught += 1
        else:
            print("  [MISSED] %s: failed %s, wanted %s" % (name, [f[:2] for f in failing], expect))
            missed += 1

    mutant("append-flag-gone", "A1", text.replace("\n" + GOOD + "\n", "\nsudo usermod -g sdusers -G sdusers sdsys\n", 1))
    mutant("append-flag-gone-is-a-replacing-usermod", "A2", text.replace("\n" + GOOD + "\n", "\nsudo usermod -g sdusers -G sdusers sdsys\n", 1))
    mutant("line-gone", "A1", text.replace("\n" + GOOD + "\n", "\n", 1))
    mutant("second-replacing-usermod", "A2", text.replace("\n" + GOOD + "\n", "\n" + GOOD + "\nsudo usermod -G sdusers sdsys\n", 1))
    mutant("gpasswd-M", "A2", text.replace("\n" + GOOD + "\n", "\n" + GOOD + "\nsudo gpasswd -M root sdg_shared\n", 1))
    CALL = '\nsdsys_groups_ruling "$ACCT_PATH/\\$groups.ruled" "$sdsys_keep"\n'
    mutant("line-after-the-ruling", "A3", text.replace("\n" + GOOD + "\n", "\n", 1).replace(CALL, CALL + GOOD + "\n", 1))
    print("selftest: %d of %d mutants caught, %d missed" % (caught, caught + missed, missed))
    return 0 if missed == 0 else 1


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else run())
