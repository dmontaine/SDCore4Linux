#!/usr/bin/env python3
#
# verify-grants.py - did queue 14 (GRANT / REVOKE / LIST.GRANTS) actually reach
#                    the installed system?
#
#   python3 gplbld/verify-grants.py               check, print every row
#   python3 gplbld/verify-grants.py --quiet       print only failures
#   python3 gplbld/verify-grants.py --sdsys DIR   point at another install
#
# No sudo.  It only reads /usr/local/sdsys.
#
# Exit 0 everything queue 14 ships is present, 1 something is MISSING, 2 the
# question CANNOT BE ANSWERED (no install there to ask about).  Three answers,
# as assert-current.py has three, and for the same reason: "there is no install"
# is not the same finding as "the install lacks the verbs".
#
# WHY THIS EXISTS.  CLAUDE.md: "The two-stage bootstrap is where BASIC changes
# actually land.  installsdai.sh runs sd -i twice; a GPL.BP change that compiles
# is not thereby installed."  Every other check in this session was static - the
# programs compiled, the VOC records are well formed - and NONE of that says the
# install took them.  The two halves fail separately and look identical from the
# source tree, which is what this separates.
#
# ***THE LOAD-BEARING ROW IS A, THE CATALOGUE.***  Copying files into
# /usr/local/sdsys is what "cp -R sdsys" does and proves nothing about the
# bootstrap.  A name in gcat is there because SD COMPILED the program and
# executed its $catalog directive.  Rows B-F can all pass on an install whose
# bootstrap silently did nothing; row A cannot.
#
# ***AND ROW F IS THE ONE THAT CATCHES A SILENT SKIP.***  CREATEA:644 reads each
# name in TIER.ADD.ADMINISTRATOR out of VOC_TEMPLATE with a bare "read ... then
# write", no else - so a name with no record behind it is skipped without a
# word, and the account is created missing a verb nobody asked about.  That is
# not a queue 14 invariant; it is the file's invariant, so this checks all of
# them and not only the three added.
#
# THE TWO CONTROLS AT THE END ARE NOT DECORATION.  A probe that looked in the
# wrong directory would report every row missing and read exactly like a failed
# install.  $MODIFYA must be found (it ships in every install since the tier
# work) and a name that cannot exist must not be, so an all-FAIL run is
# distinguishable from a broken probe.

import argparse
import os
import sys

SDSYS_DEFAULT = "/usr/local/sdsys"

# The three catalogued names, as the catalogue spells them.  $catalog is written
# lower case in the sources (!tier_allows) and gcat holds it upper - checked
# against !IS_GRP_MEMBER, which has shipped for far longer than this work.
CATALOGUED = ["$GRANTA", "!TIER_ALLOWS", "!GRP_MEMBERS"]

SOURCES = ["GRANTA", "TIERGATE", "GRP_MEMBERS"]

VERBS = ["GRANT", "REVOKE", "LIST.GRANTS"]
VERB_RECORD = "V\nCA\n$GRANTA\n"

MESSAGES = [str(n) for n in range(10041, 10051)] + \
           [str(n) for n in range(10126, 10130)] + ["10911"]

TIER_LIST = "TIER.ADD.ADMINISTRATOR"


class Report:
    """Rows with a verdict each, and a tally that cannot be talked up."""

    def __init__(self, quiet):
        self.quiet = quiet
        self.passed = 0
        self.failed = 0

    def row(self, ok, label, detail):
        if ok:
            self.passed += 1
            if not self.quiet:
                print("PASS  %-46s %s" % (label, detail))
        else:
            self.failed += 1
            print("FAIL  %-46s %s" % (label, detail))


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError as exc:
        return None if exc.errno != 0 else None


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--sdsys", default=SDSYS_DEFAULT)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    sdsys = os.path.abspath(args.sdsys)

    # THE INPUTS IT ACTUALLY USED, not the ones it meant to use.
    print("verify-grants.py - queue 14 (GRANT / REVOKE / LIST.GRANTS)")
    print("install under test : %s" % sdsys)

    gcat = os.path.join(sdsys, "gcat")
    if not os.path.isdir(sdsys) or not os.path.isdir(gcat):
        print("")
        print("CANNOT ANSWER: %s has no gcat directory, so there is no install"
              % sdsys)
        print("here to ask about.  This is not the same as 'the verbs are")
        print("missing' and is deliberately not reported as though it were.")
        return 2

    # The same stamp assert-current.py reads, and read the same way: key=value.
    # Printed rather than tested - WHICH install this was is the reader's half
    # of every row below, and a probe that does not say what it measured is the
    # thing CLAUDE.md's instrument rule is about.
    stamp = read_text(os.path.join(sdsys, ".sdcore-install")) or ""
    fields = {}
    for line in stamp.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            fields[key.strip()] = value.strip()
    if fields.get("commit"):
        print("install stamp      : %s  (%s)"
              % (fields["commit"][:12], fields.get("installed", "time unrecorded")))
    else:
        print("install stamp      : none found - assert-current.py explains why")
    print("")

    rep = Report(args.quiet)

    # ---- A. the catalogue.  The bootstrap ran, or it did not.
    for name in CATALOGUED:
        path = os.path.join(gcat, name)
        rep.row(os.path.exists(path), "A catalogue %s" % name, path)

    # ---- B. the sources shipped
    for name in SOURCES:
        path = os.path.join(sdsys, "GPL.BP", name)
        rep.row(os.path.exists(path), "B source GPL.BP/%s" % name, path)

    # ---- C. the VOC_TEMPLATE records, contents and all
    for name in VERBS:
        path = os.path.join(sdsys, "VOC_TEMPLATE", name)
        body = read_text(path)
        if body is None:
            rep.row(False, "C VOC_TEMPLATE/%s" % name, "%s - absent" % path)
        else:
            rep.row(body == VERB_RECORD, "C VOC_TEMPLATE/%s" % name,
                    "%r" % body)

    # ---- D. the tier list names them
    tier_path = os.path.join(sdsys, "NEWVOC", TIER_LIST)
    tier_body = read_text(tier_path)
    if tier_body is None:
        rep.row(False, "D %s" % TIER_LIST, "%s - absent" % tier_path)
        tier_names = []
    else:
        # Field 1 is the description, never a VOC id - the same skip CREATEA
        # and LOGIN's update.voc both make.
        tier_names = [line.strip() for line in tier_body.splitlines()[1:]
                      if line.strip()]
        for name in VERBS:
            rep.row(name in tier_names, "D %s lists %s" % (TIER_LIST, name),
                    "%d names in the list" % len(tier_names))

    # ---- E. the messages
    missing = []
    for num in MESSAGES:
        path = os.path.join(sdsys, "MESSAGES", num)
        body = read_text(path)
        if not body or not body.strip():
            missing.append(num)
    rep.row(not missing, "E messages %s" % ", ".join([MESSAGES[0], "...",
                                                      MESSAGES[-1]]),
            "%d checked, missing/empty: %s"
            % (len(MESSAGES), ", ".join(missing) if missing else "none"))

    # ---- F. EVERY tier-list name resolves, not only the three added.
    #         CREATEA:644 skips a name with no record and says nothing.
    unresolved = [n for n in tier_names
                  if not os.path.exists(os.path.join(sdsys, "VOC_TEMPLATE", n))]
    rep.row(not unresolved, "F every %s name resolves" % TIER_LIST,
            "%d names, unresolved: %s"
            % (len(tier_names),
               ", ".join(unresolved) if unresolved else "none"))

    # ---- controls.  An all-FAIL run must be distinguishable from a probe
    #      that is looking in the wrong place.
    print("")
    rep.row(os.path.exists(os.path.join(gcat, "$MODIFYA")),
            "control + $MODIFYA is catalogued",
            "must be true on any install; if this FAILS the probe is wrong")
    rep.row(not os.path.exists(os.path.join(gcat, "$NO.SUCH.VERB")),
            "control - $NO.SUCH.VERB is not",
            "must be false; if this FAILS the probe cannot say no")

    print("")
    print("%d passed, %d failed" % (rep.passed, rep.failed))
    if rep.failed:
        print("")
        print("Queue 14 is NOT fully present in this install.  If row A failed")
        print("while B-F passed, the files were copied and the two-stage")
        print("bootstrap did not compile them - rerun installsdai.sh rather")
        print("than copying anything by hand.")
        return 1

    print("Queue 14 is present in this install.  That is all this says: none of")
    print("the verbs has been RUN, and the witness plan is PORT_ADOPTION 14.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
