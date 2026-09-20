#!/usr/bin/env python3
"""test-apiroute-units.py - the sdapi gate in APISRVR, as invariants.

  python3 /home/don/Projects/SDCoreLinuxProject/sdcore4linux/sdb_ai/sd64/gplbld/test-apiroute-units.py
  python3 .../test-apiroute-units.py --selftest

No sudo, no install, no sd.  Exit 0 all checks passed, 1 a check failed, 2 it
could not run.  Written 20 Sep 26 for S.29 part 3.

***WHAT THIS IS AND, MORE IMPORTANTLY, WHAT IT IS NOT.***  It reads
sdsys/gpl.bp/apisrvr as text.  ***IT DOES NOT RUN BASIC, SO IT CANNOT SAY THE
GATE REFUSES ANYBODY*** - only that the gate is still written, still in the
right place, and still shaped the way S.29 needs.  The refusal itself is
measured on an install, by witness-release-run.sh section 13f, which drives a
real SCRAM login for an account whose route has been taken away.  A green run
here is not evidence that the API is gated; it is evidence that nothing has
quietly deleted or reordered the gate since the cycle that measured it.

WHY A TEXT CHECK IS WORTH HAVING ANYWAY.  There is no way to compile or run
GPL.BP without an install (the two-stage bootstrap, CLAUDE.md "Testing"), so
between cycles the only guard on this code is a reader.  Three of these
invariants are ORDERING, which is exactly the kind of thing a later edit breaks
silently: a gate moved below K$SET.USERNAME still compiles, still looks right in
a diff, and admits a session that has already become the user.

***AND THE CHECKS ARE THEMSELVES CHECKED.***  --selftest mutates the source in
the ways this gate could plausibly be broken and requires each mutation to be
CAUGHT.  A structural test nobody has driven against a broken input is the
"test that passes because it did nothing" CLAUDE.md names: it would pass just as
happily against a file it had failed to understand.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SDSYS = os.path.abspath(os.path.join(HERE, os.pardir, "sdsys"))
APISRVR = os.path.join(SDSYS, "gpl.bp", "apisrvr")
MESSAGES = os.path.join(SDSYS, "messages")

# The anchors, each written once so a check and its mutant cannot drift apart.
GATE = "is_grp_member(scram.user, 'sdapi')"
SDUSERS = "is_grp_member(scram.user, 'sdusers')"
REFUSAL = "sysmsg(10073, scram.user)"
EXEMPT = "not(downcase(scram.user) = 'sdsys')"
IDENTITY = "kernel(K$SET.USERNAME, scram.user)"


def code_lines(src):
    """The source with full-line comments dropped.

    A gate that exists only inside a comment is not a gate, and the comments
    above this one quote every anchor string - so a check reading the raw text
    would pass against a file whose code had been deleted entirely.  Line
    numbers are kept so the ordering checks still report something a reader can
    open.
    """
    out = []
    for i, line in enumerate(src.splitlines(), 1):
        if line.lstrip().startswith("*"):
            continue
        out.append((i, line))
    return out


def find(lines, needle):
    """Line number of the first code line containing needle, or None."""
    for n, line in lines:
        if needle in line:
            return n
    return None


def checks(src, messages=MESSAGES):
    """[(name, ok, detail)] - every invariant S.29 part 3 rests on."""
    lines = code_lines(src)
    out = []

    def ck(name, ok, detail):
        out.append((name, bool(ok), detail))

    gate = find(lines, GATE)
    sdusers = find(lines, SDUSERS)
    refusal = find(lines, REFUSAL)
    exempt = find(lines, EXEMPT)
    identity = find(lines, IDENTITY)

    ck("A1 the sdapi membership test is in the code", gate is not None,
       f"{GATE} at line {gate}")
    ck("A2 it refuses with 10073, the port's number", refusal is not None,
       f"{REFUSAL} at line {refusal}")

    # status() has to be read straight after the lookup, or "could not tell"
    # arrives as "not a member" and the audit trail says the wrong thing.
    near = None
    if gate is not None:
        near = any("status()" in line for n, line in lines
                   if gate < n <= gate + 3)
    ck("A3 status() is read within 3 lines of the lookup", near,
       "so a register that cannot be read is not reported as 'not a member'")

    ck("A4 sdsys is exempt by name", exempt is not None,
       f"{EXEMPT} at line {exempt}")

    ck("A5 the gate comes AFTER the sdusers test (5009 keeps first word)",
       gate is not None and sdusers is not None and sdusers < gate,
       f"sdusers {sdusers}, sdapi {gate}")
    ck("A6 the gate comes BEFORE the identity is taken",
       gate is not None and identity is not None and gate < identity,
       f"sdapi {gate}, K$SET.USERNAME {identity}")
    ck("A7 the refusal comes BEFORE the identity is taken",
       refusal is not None and identity is not None and refusal < identity,
       f"10073 {refusal}, K$SET.USERNAME {identity}")

    # The messages the two enforcement points call.  A call to a missing
    # message errors at run time; both numbers are the pair S.29 restored.
    for num, what in (("10073", "the API refusal"), ("10074", "the ssh refusal")):
        path = os.path.join(messages, num)
        try:
            with open(path) as f:
                body = f.read().strip()
        except OSError as exc:
            ck(f"A8 message {num} exists ({what})", False, str(exc))
            continue
        ck(f"A8 message {num} exists and is not empty ({what})", body != "",
           repr(body[:60]))
        ck(f"A9 message {num} carries the %1 the caller substitutes", "%1" in body,
           repr(body[:60]))

    return out


# --------------------------------------------------------------- self-test
#
# Each mutant is (name, transform).  A mutant that no check catches is a hole
# in this file, reported as a FAILURE of the self-test - the point is not that
# the mutants are broken, it is that the checks notice.
MUTANTS = [
    ("the gate is deleted outright",
     lambda s: s.replace("                  api.in.sdapi = " + GATE,
                         "                  api.in.sdapi = @true")),
    ("status() is no longer read",
     lambda s: s.replace("                  api.route.stat = status()",
                         "                  api.route.stat = 0")),
    ("the refusal is renumbered",
     lambda s: s.replace(REFUSAL, "sysmsg(10003, scram.user)")),
    ("the sdsys exemption is dropped",
     lambda s: s.replace("if " + EXEMPT + " then", "if @true then")),
    ("the gate moves below K$SET.USERNAME",
     lambda s: _move_gate_after_identity(s)),
]


def _move_gate_after_identity(src):
    """Move the whole gate block to just after the identity is taken.

    Textual and crude on purpose: it only has to produce a file in which the
    gate is present, compiles to the eye, and sits in the wrong place.
    """
    lines = src.splitlines(keepends=True)
    start = end = ident = None
    for i, line in enumerate(lines):
        if EXEMPT in line and line.lstrip().startswith("if "):
            start = i
        if start is not None and end is None and line.rstrip() == " " * 15 + "end":
            end = i
        if IDENTITY in line:
            ident = i
    if start is None or end is None or ident is None or ident <= end:
        return src
    block = lines[start:end + 1]
    rest = lines[:start] + lines[end + 1:]
    at = next(i for i, line in enumerate(rest) if IDENTITY in line)
    return "".join(rest[:at + 1] + block + rest[at + 1:])


def selftest(src):
    print("--- self-test: each mutation must be CAUGHT by at least one check ---")
    base = checks(src)
    base_bad = [n for n, ok, _ in base if not ok]
    if base_bad:
        print("REFUSING - the unmutated source already fails: %s" % ", ".join(base_bad),
              file=sys.stderr)
        return 2
    holes = 0
    for name, fn in MUTANTS:
        mutated = fn(src)
        if mutated == src:
            print(f"  [FAIL] {name}: the mutation did not change the file "
                  f"(this test no longer understands the source)")
            holes += 1
            continue
        caught = [n for n, ok, _ in checks(mutated) if not ok]
        if caught:
            print(f"  [pass] {name}: caught by {', '.join(caught)}")
        else:
            print(f"  [FAIL] {name}: NOT CAUGHT by any check")
            holes += 1
    print(f"\n{len(MUTANTS) - holes} of {len(MUTANTS)} mutants caught")
    return 1 if holes else 0


def main(argv):
    if not os.path.isfile(APISRVR):
        print(f"CANNOT RUN - no {APISRVR}", file=sys.stderr)
        return 2
    with open(APISRVR) as f:
        src = f.read()

    print(f"reading  {APISRVR} ({len(src.splitlines())} lines)")
    print(f"messages {MESSAGES}\n")

    if "--selftest" in argv:
        return selftest(src)

    rows = checks(src)
    failed = 0
    for name, ok, detail in rows:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")
        if not ok:
            failed += 1
    if not rows:
        print("REFUSING - no checks ran", file=sys.stderr)
        return 2
    print(f"\n{len(rows) - failed} passed, {failed} failed")
    print("NOT MEASURED HERE: whether the gate refuses anybody.  That is "
          "witness-release-run.sh section 13f, on an install.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
