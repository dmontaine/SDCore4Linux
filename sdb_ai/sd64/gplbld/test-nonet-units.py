#!/usr/bin/env python3
#
# test-nonet-units.py - strip_c_comments, the one piece of verify-nonet.py with
#                       real logic, driven through the case that already caught
#                       it out once.  PORT_ADOPTION queue 22.
#
#   python3 /home/don/Projects/sdcore4linux/sdb_ai/sd64/gplbld/test-nonet-units.py
#
# No sudo, no install, no sd.  Exit 0 all cases passed, 1 a case failed.
#
# ***WHY THIS EXISTS: verify-nonet.py FAILED ITS OWN FIRST RUN, ON PROSE.***
# Measured 12 Sep 2026 - 4 decisive rows red, every one of them a comment.
# `op_dio1.c`'s START-HISTORY says, in words, *"the ';' network-file dispatch
# and net_open() call are gone"* and *"gplsrc/netfiles.c and the NET_FILE type
# are deleted"*.  A search for `net_open(` found the sentence ANNOUNCING the
# removal and reported the removal as incomplete.
#
# ***THAT IS NOT A ONE-OFF, IT IS THE SHAPE OF THE PROBLEM.***  A removal check
# reads a codebase in which the removal is most likely to be DESCRIBED - in a
# history block, right at the top of the file it was removed from.  So the
# corpse and the tombstone sit in the same file, and any check that reads prose
# finds the tombstone first.  The real text is case 1 below, kept verbatim.
#
# ***AND THE RED DIRECTION IS THE DANGEROUS ONE HERE, WHICH IS UNUSUAL.***
# Elsewhere in this project a false "stale" is cheap and a false "current" is
# expensive.  Here it is the other way round: the false positive cost one
# debugging pass, but a strip_c_comments that blanked too much - a "*/" inside
# a string literal, say - would hide REAL code from the search and report a
# live net_open() as removed.  Cases 6 and 7 are that direction.
#
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import importlib.util                                    # noqa: E402
_spec = importlib.util.spec_from_file_location(
    "verify_nonet", os.path.join(HERE, "verify-nonet.py"))
VN = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(VN)

FAILS = []
CASES = [0]


def ck(name, got, want):
    CASES[0] += 1
    if got != want:
        FAILS.append("%s:\n      got  %r\n      want %r" % (name, got, want))
        print("  FAIL %s" % name)
    else:
        print("  pass %s" % name)


def has(text, needle):
    return needle in VN.strip_c_comments(text)


# THE REAL TEXT, verbatim from gplsrc/op_dio1.c:19-25.
TOMBSTONE = """\
 * START-HISTORY:
 *  9 Sep 26 Linux port - SDNet removed (plan G4, UPSTREAM_FIXES SDNet entry).
 *           The ';' network-file dispatch and net_open() call are gone from
 *           op_open(), so a mapped name containing ';' now falls through to
 *           fullpath() and fails like any other bad pathname; the NET_FILE
 *           close arm went too. gplsrc/netfiles.c and the NET_FILE type are
 *           deleted; NETFILES, USR_SDNET, K$SDNET, SrvrOpenSDNet and sdnet.h
"""


def main():
    print("test-nonet-units.py - verify-nonet.py's comment stripper")
    print("  module : %s" % os.path.join(HERE, "verify-nonet.py"))
    print("")

    print("--- the tombstone that caught it out ---")
    # The block is not closed in this excerpt, so it is stripped as an
    # unterminated /* ... which is what a START-HISTORY excerpt really is.
    wrapped = "/*\n" + TOMBSTONE + " */\n"
    ck("1 net_open( in the history block is NOT code",
       has(wrapped, "net_open("), False)
    ck("2 NET_FILE in the history block is NOT code",
       has(wrapped, "NET_FILE"), False)
    ck("3 netfiles.c in the history block is NOT code",
       has(wrapped, "netfiles.c"), False)

    print("--- line numbers must survive, or hits cite the wrong line ---")
    src = "/* a\n   b\n   c */\nint real_code;\n"
    ck("4 the stripper keeps the line count",
       len(VN.strip_c_comments(src).split("\n")), len(src.split("\n")))
    ck("5 and the surviving code is on its original line",
       VN.strip_c_comments(src).split("\n")[3], "int real_code;")

    print("--- THE DANGEROUS DIRECTION: real code must NOT be hidden ---")
    ck("6 a live call is still found",
       has("if (net_open(name)) { }\n", "net_open("), True)
    ck("7 a live call after a comment on the same line is still found",
       has("/* gone */ if (net_open(name)) { }\n", "net_open("), True)
    ck("8 a live call BEFORE a comment is still found",
       has("if (net_open(name)) { } /* still here */\n", "net_open("), True)
    ck("9 a // comment does not eat the next line",
       has("// net_open() was here\nint net_open(char *n);\n", "net_open("),
       True)

    print("--- ordinary shapes ---")
    ck("10 empty input", VN.strip_c_comments(""), "")
    ck("11 code with no comments is untouched",
       VN.strip_c_comments("int x = 1;\n"), "int x = 1;\n")
    ck("12 a comment between two live calls hides only itself",
       VN.strip_c_comments("a();\n/* net_open( */\nb();\n").replace(" ", ""),
       "a();\n\nb();\n")

    print("")
    print("test-nonet-units: %d cases, %d failed" % (CASES[0], len(FAILS)))
    for f in FAILS:
        print("  FAIL %s" % f)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
