#!/usr/bin/env python3
#
# test-editors-units.py - the two pieces of verify-editors.py that contain real
#                         logic, driven through the cases that must FAIL.
#                         PORT_ADOPTION queue 22.
#
#   python3 /home/don/Projects/sdcore4linux/sdb_ai/sd64/gplbld/test-editors-units.py
#
# No sudo, no install, no sd.  Exit 0 all cases passed, 1 a case failed.
#
# ***WHY THIS FILE EXISTS AND THE OTHER VERIFIERS DO NOT ALL HAVE ONE.***
# verify-vocverbs and verify-txn can be shown to go red against the SYSTEM - an
# older install, or a deliberately broken probe.  verify-editors cannot: every
# row it checks is a root-owned file (/etc/nanorc, /usr/share/nano, the
# installed sdsys tree), and breaking one to watch the check fail would mean
# editing the machine's own configuration.  ***SO THE RED IS DEMONSTRATED
# AGAINST THE LOGIC INSTEAD***, with the inputs the real files would have if
# they regressed.
#
# ***THE LOAD-BEARING CASE IS THE COMMENTED-OUT include.***  Debian's shipped
# /etc/nanorc carries the live include on line 257 and THREE COMMENTED ONES
# immediately below it.  A substring search for the filename - the obvious way
# to write that check - finds a commented line and reports the highlighting as
# reachable when nano never reads it.  That is a false "current" in the same
# shape as every other one this project has paid for, and it is the reason A2
# parses the line rather than searching it.
#
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# The module name has a hyphen, so it cannot be imported by name.
import importlib.util                                    # noqa: E402
_spec = importlib.util.spec_from_file_location(
    "verify_editors", os.path.join(HERE, "verify-editors.py"))
VE = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(VE)

FAILS = []
CASES = [0]


def ck(name, got, want):
    CASES[0] += 1
    if got != want:
        FAILS.append("%s: got %r want %r" % (name, got, want))
        print("  FAIL %s" % name)
    else:
        print("  pass %s" % name)


TARGET = "/usr/share/nano/sdbasic.nanorc"

# The real shape of Debian's file: one live include, three commented.
DEBIAN = '''\
## To include most of the existing syntax definitions, you can do:
include "/usr/share/nano/*.nanorc"

## Or you can select just the ones you need.  For example:
# include "/usr/share/nano/html.nanorc"
# include "/usr/share/nano/python.nanorc"
# include "/usr/share/nano/sh.nanorc"
'''

# The regression this whole check exists to catch: somebody comments the live
# one out, or a distribution upgrade ships it commented.
REGRESSED = DEBIAN.replace('include "/usr/share/nano/*.nanorc"',
                           '# include "/usr/share/nano/*.nanorc"')


def include_cases():
    print("--- active_includes: a commented include is NOT an include ---")
    ck("debian: one live include", VE.active_includes(DEBIAN),
       ["/usr/share/nano/*.nanorc"])
    # ***THE RED CASE.***
    ck("regressed: none at all", VE.active_includes(REGRESSED), [])
    ck("empty file", VE.active_includes(""), [])
    ck("none text", VE.active_includes(None), [])
    ck("leading whitespace is still live",
       VE.active_includes('   include "/a/b.nanorc"'), ["/a/b.nanorc"])
    ck("a hash anywhere before it comments it",
       VE.active_includes('  # include "/a/b.nanorc"'), [])

    print("--- include_covers ---")
    ck("glob in the same directory covers it",
       VE.include_covers(["/usr/share/nano/*.nanorc"], TARGET), True)
    ck("the exact path covers it",
       VE.include_covers([TARGET], TARGET), True)
    # ***nano's include GLOB DOES NOT RECURSE***, so a subdirectory glob must
    # not be accepted - Debian really does ship /usr/share/nano/extra.
    ck("a glob in a SUBdirectory does not",
       VE.include_covers(["/usr/share/nano/extra/*.nanorc"], TARGET), False)
    ck("a glob in an unrelated directory does not",
       VE.include_covers(["/etc/nano/*.nanorc"], TARGET), False)
    ck("a different exact file does not",
       VE.include_covers(["/usr/share/nano/sh.nanorc"], TARGET), False)
    ck("no includes at all", VE.include_covers([], TARGET), False)
    # END TO END: the regressed file must not cover the target.
    ck("REGRESSED /etc/nanorc does not cover the file",
       VE.include_covers(VE.active_includes(REGRESSED), TARGET), False)
    ck("and the real one does",
       VE.include_covers(VE.active_includes(DEBIAN), TARGET), True)


def regex_cases():
    print("--- grep_e_compiles ---")
    # A real line out of the generated nanorc.
    ck("a real colour regex compiles",
       VE.grep_e_compiles(r"\<(PRINT|CRT|DISPLAY)\>"), True)
    ck("a plain word compiles", VE.grep_e_compiles("hello"), True)
    # ***THE RED CASE: grep -E must REJECT this, and the checker must notice.***
    ck("an unclosed bracket is rejected",
       VE.grep_e_compiles("[unclosed"), False)
    ck("an unclosed paren is rejected",
       VE.grep_e_compiles(r"\<(ONE|TWO"), False)
    # A regex that matches nothing is still a COMPILING regex: grep exits 1 for
    # "no match", and conflating that with 2 would reject good rules.
    ck("a valid regex that matches nothing still compiles",
       VE.grep_e_compiles("zzzznomatchzzzz"), True)


def main():
    print("test-editors-units.py - verify-editors.py's logic under test")
    print("  module : %s" % os.path.join(HERE, "verify-editors.py"))
    print("")
    include_cases()
    regex_cases()
    print("")
    print("test-editors-units: %d cases, %d failed" % (CASES[0], len(FAILS)))
    for f in FAILS:
        print("  FAIL %s" % f)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
