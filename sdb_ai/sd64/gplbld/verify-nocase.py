#!/usr/bin/env python3
#
# verify-nocase.py - the §M scope meter: every name in the SOURCE tree that is
#                    still upper case, by category.  PORT_ADOPTION queue 18; the
#                    owner's ruling of 11 Sep 2026, "everything lowercase so we
#                    don't have commands, files or record ids that differ only
#                    in casing."
#
#   python3 /home/don/Projects/sdcore4linux/sdb_ai/sd64/gplbld/verify-nocase.py
#   python3 .../verify-nocase.py --list        also print every remnant name
#   python3 .../verify-nocase.py --strict      exit 1 unless the name half is COMPLETE
#
# NO SUDO, NO INSTALL, NO sd.  It reads the source tree only, because §M is a
# change to what ships, and the migration is verified by reinstall afterwards.
# Exit 0 the audit ran (whatever it found), 1 only under --strict with remnants
# left, 2 it could not run (a path it measures is missing).
#
# ***THIS INSTRUMENT IS RED BY DESIGN UNTIL §M IS DONE, AND THAT IS THE POINT.***
# It does not "pass" today - nothing of §M is built.  It measures the scope and
# names what is left, and it reads zero when the name half of §M is complete.
# So it is a gate for a migration, not a check of finished behaviour: the number
# it reports going to 0 IS the definition of done for the part it covers.
#
# WHAT COUNTS AS "STILL UPPER CASE", AND WHY THE ESCAPES ARE NOT.  A record id
# containing a restricted character is stored as a filename of "%" plus a
# substitute letter - sd.h:113-114 maps each of  *,=><%/+:;?\"  to  ACEGLPSVXYZBQ
# and a leading "." or "~" to %d / %t.  So "%E" on disk is the record "=", not a
# name called E; "#" and "&" are symbol record ids with no letters at all.  The
# test therefore STRIPS every "%<letter>" escape and only then looks for [A-Z]:
# a name needs lowercasing only if a real, unescaped upper-case letter survives.
# Measured 12 Sep 2026: this correctly passes over %E %E%G %P %t # & and flags
# ACCOUNTS, $ACC, INT$KEYS.H.
#
# ***WHAT IT DELIBERATELY DOES NOT MEASURE, BECAUSE THE OWNER HAS NOT RULED IT.***
# Two categories are open (PORT_ADOPTION queue 18), and guessing either way
# would be a false positive with a check's name on it:
#   * ACCOUNT NAMES - KEYS.H:263 "forced to uppercase"; the gap table marks this
#     RE-RULE.  Lowercasing account ids is not assumed.
#   * RECORD IDS IN A USER'S OWN DATA FILES - on ext4 "SUE" and "sue" are two
#     files, so forcing an application's data ids to lower case would change its
#     data.  Out of scope until ruled.
# They are printed as DEFERRED so the reader sees they were considered, not
# missed.
#
# ***AND IT MEASURES NAMES, NOT THE ON-THE-FLY UPCASING HALF OF §M.***  The
# ruling has two halves: names lowercased, AND input upper-cased on the fly so a
# command typed in caps still resolves.  A static name audit cannot prove the
# second; the known code sites that must change are listed as a checklist
# (CREATEF's upcase(file.name), LOGIN's PT$INVERT), not asserted green.
#
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SDSYS_SRC = os.path.normpath(os.path.join(HERE, os.pardir, "sdsys"))

# sd.h:113-114 - the escape a restricted character becomes on disk.
_ESCAPE = re.compile(r"%[A-Za-z]")


def needs_lowercasing(name):
    """True if NAME still carries a real upper-case letter once the on-disk
    "%<letter>" escapes are removed.  So %E (the record "=") and # (a symbol)
    are NOT names to lowercase, while ACCOUNTS and $ACC are."""
    return bool(re.search(r"[A-Z]", _ESCAPE.sub("", name)))


def scan_dir(path):
    """(remnants, total) for the record-id names directly in PATH."""
    names = sorted(os.listdir(path))
    remnants = [n for n in names if needs_lowercasing(n)]
    return remnants, len(names)


# The name categories, all ruled in scope.  (label, path, what it holds)
NAME_CATEGORIES = [
    ("GPL.BP source records", "GPL.BP", "program and include records"),
    ("SYSCOM include records", "SYSCOM", "include records"),
    ("NEWVOC record ids", "NEWVOC", "the shipped VOC"),
    ("VOC_TEMPLATE record ids", "VOC_TEMPLATE", "the per-account VOC template"),
]

# The behavioural sites §M must also change - a checklist, not a name scan.
# (file, a regex that matches the site while it is still WRONG, why)
CODE_SITES = [
    ("GPL.BP/CREATEF", r"upcase\(file\.name\)",
     "the OS filename CREATE.FILE makes is upper-cased (:306,:379)"),
    ("GPL.BP/LOGIN", r"pterm\(PT\$INVERT",
     "case inversion at sign-on (:302)"),
]

# Open, unruled - printed so they are seen to be deferred, not missed.
DEFERRED = [
    ("account names", "SYSCOM/KEYS.H:263 'forced to uppercase' - RE-RULE"),
    ("record ids in users' own data files",
     "SUE vs sue are two files on ext4; ruling would change app data"),
]


def _selftest():
    """Guard needs_lowercasing(), the load-bearing classifier.  A wrong answer
    here is a silent miscount, not a visible error - the reason it is tested.
    The escape cases are the red control: drop the _ESCAPE.sub and %E flags,
    a false positive."""
    fails = []

    def ck(name, got, want):
        if got != want:
            fails.append("%s: got %r want %r" % (name, got, want))

    # real upper-case names -> flagged
    for n in ("ACCOUNTS", "$ACC", "$RELEASE", "INT$KEYS.H", "A%E", "SD.VOCLIB"):
        ck(n, needs_lowercasing(n), True)
    # escaped restricted-char / leading-char records -> NOT names
    for n in ("%E", "%E%G", "%G%L", "%P", "%t", "%d"):
        ck(n, needs_lowercasing(n), False)
    # symbol record ids with no letters -> NOT names
    for n in ("#", "&", "!"):
        ck(n, needs_lowercasing(n), False)
    # already lower case -> done, not a remnant
    for n in ("define_install.h", "sdclilib.h", "zzak", "a%e"):
        ck(n, needs_lowercasing(n), False)

    print("verify-nocase selftest: %d cases, %d failed" % (19, len(fails)))
    for f in fails:
        print("  FAIL " + f)
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(description="§M lower-case scope meter")
    ap.add_argument("--selftest", action="store_true",
                    help="check the name classifier and exit")
    ap.add_argument("--sdsys", default=SDSYS_SRC,
                    help="source sdsys directory (default %s)" % SDSYS_SRC)
    ap.add_argument("--list", action="store_true",
                    help="print every remnant name, not just the counts")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 unless the name half is COMPLETE (0 remnants)")
    a = ap.parse_args()

    if a.selftest:
        return _selftest()

    def say(s=""):
        print(s)

    say("verify-nocase: §M lower-case scope meter")
    say("  source   %s" % a.sdsys)
    say("  reads the SOURCE tree only (no install, no sd, no sudo)")
    say("")

    if not os.path.isdir(a.sdsys):
        say("verify-nocase: CANNOT RUN - %s is not a directory." % a.sdsys)
        return 2

    total_remnants = 0
    scanned_any = False

    say("=== names still upper case (0 = that category is done) ===")
    for label, rel, holds in NAME_CATEGORIES:
        path = os.path.join(a.sdsys, rel)
        if not os.path.isdir(path):
            say("  %-26s MISSING (%s)" % (label, path))
            return 2
        remnants, total = scan_dir(path)
        # ***NULL-CASE GUARD.***  An empty directory would report 0 remnants
        # and read as "done" when it is really "measured nothing".
        if total == 0:
            say("  %-26s 0 files - refusing: nothing measured" % label)
            return 2
        scanned_any = True
        total_remnants += len(remnants)
        say("  %-26s %4d of %4d still upper  (%s)"
            % (label, len(remnants), total, holds))
        if a.list and remnants:
            for i in range(0, len(remnants), 6):
                say("        " + "  ".join(remnants[i:i + 6]))

    say("")
    say("=== sdsys directory names ===")
    dirs = sorted(d for d in os.listdir(a.sdsys)
                  if os.path.isdir(os.path.join(a.sdsys, d)))
    dir_remnants = [d for d in dirs if needs_lowercasing(d)]
    total_remnants += len(dir_remnants)
    say("  %d of %d directory names still upper" % (len(dir_remnants), len(dirs)))
    if dir_remnants:
        say("        " + "  ".join(dir_remnants))
    say("  (build/runtime dirs - BP.OUT, GPL.BP.OUT, PCODE.OUT - follow from the")
    say("   code that creates them, so they change with that code, not by rename)")

    say("")
    say("=== the on-the-fly upcasing half: code sites to change (checklist) ===")
    say("  a name audit cannot prove these; they are listed, not scored green")
    code_open = 0
    for rel, pat, why in CODE_SITES:
        path = os.path.join(a.sdsys, rel)
        hits = 0
        if os.path.exists(path):
            with open(path, encoding="latin-1") as f:
                for line in f:
                    if re.search(pat, line):
                        hits += 1
        else:
            say("  %-18s MISSING (%s)" % (rel, path))
            continue
        code_open += 1 if hits else 0
        say("  [%s] %-18s %s" % ("open" if hits else " ok ", rel, why))

    say("")
    say("=== deferred: unruled, NOT measured (PORT_ADOPTION queue 18) ===")
    for what, why in DEFERRED:
        say("  - %s: %s" % (what, why))

    say("")
    say("--- summary ------------------------------------------------------")
    say("  name remnants (ruled categories) : %d" % total_remnants)
    say("  code sites still to change       : %d of %d"
        % (code_open, len(CODE_SITES)))
    done = (total_remnants == 0 and code_open == 0)
    if done:
        say("  §M NAME HALF: COMPLETE - every ruled name is lower case.")
        say("  (the on-the-fly upcasing behaviour is witnessed elsewhere, by")
        say("   an install that resolves an upper-case command.)")
    else:
        say("  §M NAME HALF: NOT COMPLETE - the counts above are the work left.")
        say("  This instrument is RED BY DESIGN until they reach 0; that is the")
        say("  gate, not a regression.")

    if not scanned_any:
        return 2
    if a.strict and not done:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
