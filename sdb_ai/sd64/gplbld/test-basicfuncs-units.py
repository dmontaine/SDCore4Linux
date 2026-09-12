#!/usr/bin/env python3
#
# test-basicfuncs-units.py - the pure logic verify-basicfuncs.py grew of its
#                            own, driven through the cases that have already
#                            caught it out.  PORT_ADOPTION queue 22.
#
#   python3 /home/don/Projects/sdcore4linux/sdb_ai/sd64/gplbld/test-basicfuncs-units.py
#
# No sudo, no install, no sd.  Exit 0 all cases passed, 1 a case failed.
#
# ***WHY THIS EXISTS: THE VERIFIER'S FIRST RUN REPORTED TWO DEFECTS SD DOES NOT
# HAVE, AND THE FAULT WAS IN THE PARSER ON THIS SIDE.***  Measured 12 Sep 2026.
# cases_from() ended each line with line.rstrip(), "want" was the last field,
# and the two cases whose expectation ENDS IN SPACES - TRIMF and FMT.L - came
# back as "expected 'ab', got 'ab  '".  TRIMB passed in the same run because
# its spaces are LEADING, which is what pinned the fault to the instrument
# rather than to the product.  Cases 1-8 are that parser, and case 4 is the
# exact shape that failed.
#
# ***AND THE COVERAGE ARITHMETIC IS WORTH MORE TESTING THAN THE PARSER, BECAUSE
# ITS FAILURE MODE IS SILENT.***  A parser fault shows up as a red row somebody
# investigates.  An exercised() that matched too loosely would report a
# function as covered when nothing calls it, and the run would go green - the
# claim "every intrinsic is either exercised or declared" would be false and
# nothing would say so.  Cases 12-19 are that direction: the substring traps
# (INDEX inside INDEXS, SUM inside SUMMATION, NOT inside NOTS) and the one that
# matters most, a function name appearing ONLY as a case label in a string
# literal.
#
import argparse
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# ***--module IS THE RED CONTROL, AND IT IS HERE FOR THE REASON --probe IS ON
# THE VERIFIERS.***  A units file that has only ever been seen green is
# evidence that it is quiet.  Measured 12 Sep 2026: pointed at a copy of
# verify-basicfuncs.py whose cases_from() takes the pre-fix "len(parts) < 4"
# branch, it goes 3 of 25 red - cases 6, 7 and 8 - and exits 1.
#
# ***CASE 4 STAYS GREEN IN THAT CONTROL, AND THAT IS THE HONEST READING RATHER
# THAN A GAP.***  The trailing spaces are protected by the PROBE emitting the
# terminator, not by this parser refusing lines that lack it: given a line that
# has one, even the pre-fix code reads the fields correctly.  The two halves of
# the fix guard different failures - the terminator stops the loss, the refusal
# stops a lost line being read as a good one - and only the second is this
# file's to test.
_AP = argparse.ArgumentParser(description="units for verify-basicfuncs.py")
_AP.add_argument("--module", default=os.path.join(HERE, "verify-basicfuncs.py"),
                 metavar="FILE",
                 help="load a different verify-basicfuncs.py (RED CONTROL)")
_ARGS = _AP.parse_args()

import importlib.util                                    # noqa: E402
_spec = importlib.util.spec_from_file_location("verify_basicfuncs", _ARGS.module)
VB = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(VB)

FAILS = []
CASES = [0]


def ck(name, got, want):
    CASES[0] += 1
    if got != want:
        FAILS.append("%s:\n      got  %r\n      want %r" % (name, got, want))
        print("  FAIL %s" % name)
    else:
        print("  pass %s" % name)


def in_temp(text, suffix=".bp"):
    """Write TEXT to a throwaway file and return its path."""
    fd, path = tempfile.mkstemp(suffix=suffix, prefix="zzbfu-")
    with os.fdopen(fd, "w", encoding="latin-1") as f:
        f.write(text)
    return path


def main():
    made = []

    if os.path.abspath(_ARGS.module) != os.path.join(HERE, "verify-basicfuncs.py"):
        print("*** RED CONTROL: driving %s, not the shipped verifier."
              % _ARGS.module)
        print("")

    print("--- cases_from: the terminator, which is what the first run cost ---")

    good, bad = VB.cases_from("CASE|ABS|3|3|END\n")
    ck("1 a well-formed line parses", (good, bad), ([("ABS", "3", "3")], []))

    good, bad = VB.cases_from("noise\nCASE|ABS|3|3|END\nmore noise\n")
    ck("2 lines that are not cases are ignored",
       (good, bad), ([("ABS", "3", "3")], []))

    good, bad = VB.cases_from("CASE|A|1|1|END\nCASE|B|2|2|END\n")
    ck("3 order is preserved",
       [c[0] for c in good], ["A", "B"])

    # ***THE EXACT LINE THAT FAILED ON 12 Sep 2026.***  TRIMF's expectation is
    # 'ab  ' and it is the last value on the line.
    good, bad = VB.cases_from("CASE|TRIMF|ab  |ab  |END\n")
    ck("4 TRAILING SPACES SURVIVE IN BOTH FIELDS (the TRIMF case)",
       good, [("TRIMF", "ab  ", "ab  ")])

    good, bad = VB.cases_from("CASE|TRIMB|  ab|  ab|END\n")
    ck("5 leading spaces survive too (TRIMB, which passed even when 4 did not)",
       good, [("TRIMB", "  ab", "  ab")])

    # The pre-fix shape: no terminator.  It must be REFUSED, not parsed - a
    # parser that accepted both shapes would silently go on losing the spaces.
    good, bad = VB.cases_from("CASE|TRIMF|ab  |ab  \n")
    ck("6 a line with NO terminator is refused, not parsed", (good, bad),
       ([], ["CASE|TRIMF|ab  |ab"]))

    good, bad = VB.cases_from("CASE|X|a|b|NOTEND\n")
    ck("7 a wrong terminator is refused", (good, bad),
       ([], ["CASE|X|a|b|NOTEND"]))

    # A value containing "|" over-splits.  Refusing is the point: taking
    # parts[1..3] would turn a mangled case into a passing one.
    good, bad = VB.cases_from("CASE|X|a|b|c|END\n")
    ck("8 a value containing '|' is refused rather than guessed at",
       (good, bad), ([], ["CASE|X|a|b|c|END"]))

    print("--- check_sites: the case count comes from the source, not a constant ---")

    p = in_temp("program x\n   n = 'A' ; gosub check\n   gosub check\nend\n")
    made.append(p)
    ck("9 every live 'gosub check' is counted", VB.check_sites(p), 2)

    p = in_temp("program x\n* gosub check\n   gosub check\nend\n")
    made.append(p)
    ck("10 a commented-out site is NOT counted", VB.check_sites(p), 1)

    p = in_temp("program x\n   gosub checksum\n   gosub check\nend\n")
    made.append(p)
    ck("11 'gosub checksum' is not 'gosub check'", VB.check_sites(p), 1)

    print("--- exercised: the direction that fails SILENTLY ---")

    NAMES = set(["INDEX", "INDEXS", "SUM", "SUMMATION", "NOT", "NOTS",
                 "ABS", "SOUNDEX", "LOCATE", "CHANGE"])

    def used(code):
        return VB.exercised(NAMES, code)

    ck("12 INDEXS does not make INDEX look tested",
       "INDEX" in used(" g = indexs(a, 'b', 1) "), False)
    ck("13 ... and INDEXS itself is tested",
       "INDEXS" in used(" g = indexs(a, 'b', 1) "), True)
    ck("14 SUMMATION does not make SUM look tested",
       "SUM" in used(" g = summation(v) "), False)
    ck("15 NOTS does not make NOT look tested",
       "NOT" in used(" g = nots(v) "), False)
    ck("16 a lower-case call is matched (the source is lower case)",
       "ABS" in used(" g = abs(-3) "), True)
    ck("17 a STATEMENT form with no parentheses is matched (LOCATE)",
       "LOCATE" in used(" locate 'b' in rf<1> setting p then "), True)

    # ***THE LOAD-BEARING ONE.***  Every case in the probe carries its own name
    # as a literal, n = 'ABS'.  If the literals were not stripped, deleting the
    # call and leaving the label would still read as covered.
    p = in_temp("program x\n   n = 'SOUNDEX' ; g = abs(-3) ; gosub check\nend\n")
    made.append(p)
    stripped = VB._code_only(p)
    ck("18 a name that appears ONLY as a case label is NOT counted as tested",
       "SOUNDEX" in used(stripped), False)
    ck("19 ... while the call on the same line still is",
       "ABS" in used(stripped), True)

    print("--- _code_only and not_tested: what the comments are allowed to say ---")

    p = in_temp("* CHANGE(a,b,c) is described here\nprogram x\nend\n")
    made.append(p)
    ck("20 a comment line cannot make a function look tested",
       "CHANGE" in used(VB._code_only(p)), False)

    p = in_temp("program x\n   g = squote('ab')  ;* w is '\"ab\"'\nend\n")
    made.append(p)
    ck("21 a single-quoted literal containing double quotes is stripped whole",
       VB._code_only(p).count("ab"), 0)

    p = in_temp("* NOT.TESTED: KEYIN KEYINC\n*   - they block.\n"
                "* prose naming SOUNDEX is not a declaration\nprogram x\nend\n")
    made.append(p)
    ck("22 only NOT.TESTED lines declare an exclusion",
       VB.not_tested(p), set(["KEYIN", "KEYINC"]))

    print("--- intrinsics: the compiler's own table ---")

    p = in_temp('* intrinsics<-1> = "COMMENTED"\n'
                '   intrinsics<-1> = "ABS"        ; intrinsic.opcodes<-1> = OP.ABS\n'
                '   intrinsics := @fm : "SOUNDEX"\n'
                '   other.table<-1> = "NOTANINTRINSIC"\n')
    made.append(p)
    ck("23 both assignment shapes are read, comments and other tables are not",
       VB.intrinsics(p), set(["ABS", "SOUNDEX"]))

    # And against the real thing, because a parser that returns nothing would
    # make the coverage section vacuously true.  V1 is the row that refuses
    # that; this is the check that it never has to.
    real = VB.intrinsics(VB.BCOMP)
    ck("24 the real BCOMP yields a plausible table", len(real) > 100, True)
    ck("25 ... containing names the probe exercises",
       set(["ABS", "SOUNDEX", "CHANGE", "SWAP", "ASSIGNED", "UNASSIGNED"])
       <= real, True)

    for p in made:
        try:
            os.remove(p)
        except OSError:
            pass

    print("")
    print("test-basicfuncs-units: %d cases, %d failed" % (CASES[0], len(FAILS)))
    for f in FAILS:
        print("  FAIL %s" % f)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
