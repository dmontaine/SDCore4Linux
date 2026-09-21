#!/usr/bin/env python3
"""test-batchgate-units.py - the batch-job command-line gate, as invariants.

  python3 /home/don/Projects/SDCoreLinuxProject/sdcore4linux/sdb_ai/sd64/gplbld/test-batchgate-units.py
  python3 .../test-batchgate-units.py --selftest

No sudo, no install, no sd.  Exit 0 all checks passed, 1 a check failed, 2 it
could not run.  Written 20 Sep 26 for S.40 (parity with the Windows port,
owner's ruling: a behavior prevented on one port must be prevented on both).

***WHAT THIS IS AND WHAT IT IS NOT.*** It reads sdsys/gpl.bp/login and the two
installer scripts as TEXT.  ***IT CANNOT SAY THE GATE REFUSES ANYBODY*** - only
that the gate is still written, still ordered correctly, and still shaped the
way S.40 needs.  GPL.BP cannot be compiled without an install (the two-stage
bootstrap, CLAUDE.md "Testing"), so a reader is the only guard on this between
cycles - exactly the shape test-apiroute-units.py already established for
S.29's sdapi gate, and this test follows the same pattern for the same reason.
The refusal itself is owed a witness row on the next cycle: a session invoked
as a single command line, unlisted and unelevated, must be refused 11000/11001/
11002 and never reach proc.sentence.

***AND THE CHECKS ARE THEMSELVES CHECKED.*** --selftest mutates the source in
the ways this gate could plausibly be broken and requires each mutation to be
CAUGHT - a structural test nobody has driven against a broken input is the
"test that passes because it did nothing" CLAUDE.md names.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir, os.pardir))
SD64 = os.path.abspath(os.path.join(HERE, os.pardir))
LOGIN = os.path.join(SD64, "sdsys", "gpl.bp", "login")
MESSAGES = os.path.join(SD64, "sdsys", "messages")
INSTALLSDAI = os.path.join(REPO, "installsdai.sh")
DELETESDAI = os.path.join(REPO, "deletesdai.sh")

# The anchors, each written once so a check and its mutant cannot drift apart.
GATE_CALL = "gosub batch.permitted"
GATE_GUARD_MODE = "mode = 0 and not(is.phantom) and not(kernel(K$INTERNAL,-1))"
GATE_GUARD_ADMIN = "not(kernel(K$ADMINISTRATOR,-1))"
GATE_ABORT = "if not(batch.ok) then goto terminate.connection"
SUCCESS_LINE = "ok = @true"
LABEL = "batch.permitted:"
NO_ARGS_TEST = "index(batch.command, ' ', 1)"
OPEN_LIST = "openpath @sdsys:@ds:'batch.jobs' to batch.f"
KEYED_READ = "read batch.rec from batch.f, downcase(initial.account)"
FOLD_LIST = "change(batch.rec, @fm, @vm)"
NOT_LISTED = "if not(batch.listed) then"
THREE_CASE_1 = "read batch.voc.rec from voc, batch.command else"
THREE_CASE_2 = "read batch.voc.rec from voc, downcase(batch.command) else"
THREE_CASE_3 = "read batch.voc.rec from voc, upcase(batch.command) else"
TYPE_TEST = "batch.type[1,2] # 'PA' and batch.type[1,1] # 'S'"
OK_TRUE = "batch.ok = @true"


def code_lines(src):
    """The source with full-line comments dropped, line numbers kept.

    A gate written only inside a comment is not a gate - the comments above
    this file quote most of these anchor strings, so a raw-text search would
    pass against a file whose code had been deleted entirely.
    """
    out = []
    for i, line in enumerate(src.splitlines(), 1):
        if line.lstrip().startswith("*"):
            continue
        out.append((i, line))
    return out


def find(lines, needle, start=0):
    for n, line in lines:
        if n < start:
            continue
        if needle in line:
            return n
    return None


def find_all(lines, needle):
    return [n for n, line in lines if needle in line]


def find_exact_line_last(lines, exact):
    """Line number of the LAST line whose stripped text equals exact, or None.

    Used for "ok = @true" - login has several early-return branches that also
    say exactly that for their own local success, so the FIRST match is not
    the routine's final declaration; the plain substring match also matches
    inside "batch.ok = @true", which a naive find() would confuse for it.
    """
    hit = None
    for n, line in lines:
        if line.strip() == exact:
            hit = n
    return hit


def checks(src, messages=MESSAGES, installsdai=None, deletesdai=None):
    """[(name, ok, detail)] - every invariant S.40 rests on."""
    lines = code_lines(src)
    out = []

    def ck(name, ok, detail):
        out.append((name, bool(ok), detail))

    label = find(lines, LABEL)
    call = find(lines, GATE_CALL)
    guard_mode = find(lines, GATE_GUARD_MODE)
    # 20 Sep 26 - ***B3 ORIGINALLY MATCHED THE WRONG LINE, AND THE SELF-TEST
    #   IS WHAT CAUGHT IT.***  A bare find() for "not(kernel(K$ADMINISTRATOR,
    #   -1))" found line 344 - login's own unrelated SDSYS-restriction check,
    #   which happens to share the same substring - so a mutant that deleted
    #   the elevation exemption from the gate's own guard still "passed" B3,
    #   because the check was reading a DIFFERENT line's coincidental match.
    #   Same trap as a success/failure wording collision, generalised to any
    #   anchor string.  Fixed: search starts at guard_mode and stops a few
    #   lines later, where the gate's own admin check must be.
    guard_admin = find(lines, GATE_GUARD_ADMIN, start=(guard_mode or 0))
    if guard_admin is not None and guard_mode is not None and guard_admin - guard_mode > 3:
        guard_admin = None  # too far away to be the gate's own guard line
    abort = find(lines, GATE_ABORT)
    success = find_exact_line_last(lines, SUCCESS_LINE)

    ck("B1 the gate is called (gosub batch.permitted)", call is not None,
       f"line {call}")
    ck("B2 the call is guarded by mode/phantom/internal", guard_mode is not None,
       f"line {guard_mode}")
    ck("B3 the call is guarded by elevation (an administrator skips it)",
       guard_admin is not None, f"line {guard_admin}")
    ck("B4 a refusal aborts the connection", abort is not None,
       f"line {abort}")

    # ORDERING: the gate must run BEFORE login declares success, or a session
    # is admitted and only asked afterwards - which is not a gate at all.
    ck("B5 the gate runs BEFORE 'ok = @true' (login's success line)",
       call is not None and success is not None and call < success,
       f"gate {call}, success {success}")

    ck("B6 the batch.permitted label exists", label is not None,
       f"line {label}")

    no_args = find(lines, NO_ARGS_TEST, start=(label or 0))
    ck("B7 arguments on the command line are refused",
       no_args is not None and (label is None or no_args > label),
       f"line {no_args}")

    open_list = find(lines, OPEN_LIST, start=(label or 0))
    ck("B8 the list is opened at @sdsys:@ds:'batch.jobs'", open_list is not None,
       f"line {open_list}")

    keyed = find(lines, KEYED_READ, start=(label or 0))
    ck("B9 the list is read keyed by the account just proven (initial.account)",
       keyed is not None, f"line {keyed}")

    fold = find(lines, FOLD_LIST, start=(label or 0))
    ck("B10 field-mark and value-mark entries are folded into one list",
       fold is not None, f"line {fold}")

    not_listed = find(lines, NOT_LISTED, start=(label or 0))
    ck("B11 an unlisted command is refused", not_listed is not None,
       f"line {not_listed}")

    t1 = find(lines, THREE_CASE_1, start=(label or 0))
    t2 = find(lines, THREE_CASE_2, start=(t1 or 0))
    t3 = find(lines, THREE_CASE_3, start=(t2 or 0))
    ck("B12 the VOC lookup tries as-typed, lower, then upper (CPROC's own order)",
       t1 is not None and t2 is not None and t3 is not None and t1 < t2 < t3,
       f"lines {t1}, {t2}, {t3}")

    type_test = find(lines, TYPE_TEST, start=(t3 or 0))
    ck("B13 only VOC type PA or S is accepted", type_test is not None,
       f"line {type_test}")

    ok_true_all = [n for n in find_all(lines, OK_TRUE) if label is None or n > label]
    ck("B14 batch.ok is set true EXACTLY ONCE, and it is the routine's last act",
       len(ok_true_all) == 1, f"occurrences at {ok_true_all}")
    if len(ok_true_all) == 1 and type_test is not None:
        ck("B14b and that line comes AFTER the type test (nothing falls through)",
           ok_true_all[0] > type_test, f"ok_true {ok_true_all[0]}, type test {type_test}")

    # The messages the gate calls.  A call to a missing message errors at run
    # time; each must exist, and 11000/11002 must carry the %1 the caller
    # substitutes (11001 takes no argument - a fixed sentence).
    for num, wants_arg, what in (
        ("11000", True, "not on the account's list / list unreadable"),
        ("11001", False, "arguments on the command line"),
        ("11002", True, "not a paragraph or sentence"),
    ):
        path = os.path.join(messages, num)
        try:
            with open(path) as f:
                body = f.read().strip()
        except OSError as exc:
            ck(f"B15 message {num} exists ({what})", False, str(exc))
            continue
        ck(f"B15 message {num} exists and is not empty ({what})", body != "",
           repr(body[:60]))
        if wants_arg:
            ck(f"B16 message {num} carries the %1 the caller substitutes",
               "%1" in body, repr(body[:60]))

    # The installer side: batch.jobs is made, protected, and preserved.
    if installsdai is not None:
        ck("B17 installsdai.sh creates batch.jobs", "batch.jobs" in installsdai,
           "mkdir/restore block present" if "batch.jobs" in installsdai else "absent")
        ck("B18 installsdai.sh chowns it sdsys:sdusers",
           "chown -R sdsys:sdusers \"$sdsysdir/batch.jobs\"" in installsdai,
           "found" if "chown -R sdsys:sdusers \"$sdsysdir/batch.jobs\"" in installsdai else "absent")
        mode_m = re.search(r'chmod\s+([0-7]{3,4})\s+"\$sdsysdir/batch\.jobs"', installsdai)
        group_no_write = bool(mode_m) and int(mode_m.group(1)[-2]) & 2 == 0
        ck("B19 installsdai.sh's chmod on batch.jobs gives the group no write bit",
           group_no_write,
           f"chmod {mode_m.group(1)}" if mode_m else "no chmod on batch.jobs found")
    if deletesdai is not None:
        ck("B20 deletesdai.sh preserves batch.jobs on a keep cycle",
           "batch.jobs" in deletesdai,
           "preserve block present" if "batch.jobs" in deletesdai else "absent")

    return out


# --------------------------------------------------------------- self-test
MUTANTS = [
    ("the gate call is deleted outright",
     lambda s: s.replace("         gosub batch.permitted\n", "")),
    ("the elevation exemption is dropped (nobody, even an admin, is exempt)",
     lambda s: s.replace(
         "      if batch.command # '' and not(kernel(K$ADMINISTRATOR,-1)) then",
         "      if batch.command # '' then")),
    ("the no-arguments test is deleted",
     lambda s: s.replace(
         "   if index(batch.command, ' ', 1) then\n"
         "      display sysmsg(11001) ;* A command run this way takes no arguments\n"
         "      audit.reason = 'command line carried arguments'\n"
         "      return\n"
         "   end\n\n",
         "")),
    ("the PA/S type test is deleted (any VOC type is accepted)",
     lambda s: s.replace(
         "   if batch.type[1,2] # 'PA' and batch.type[1,1] # 'S' then\n"
         "      display sysmsg(11002, batch.command)\n"
         "      audit.reason = 'VOC type is not PA or S'\n"
         "      return\n"
         "   end\n\n",
         "")),
    ("batch.ok is set true a second time, earlier (a fall-through)",
     lambda s: s.replace(
         "   batch.listed = @false\n",
         "   batch.listed = @false\n   batch.ok = @true\n")),
    ("the gate call moves to AFTER login declares success",
     lambda s: _move_gate_after_success(s)),
]


def _move_gate_after_success(src):
    """Move the whole mode/admin-guarded gate block to after 'ok = @true'.

    Textual and crude on purpose: it only has to produce a file where the
    call to batch.permitted is present but ordered wrong.  THE INSERTION
    POINT MUST BE THE ROUTINE'S REAL, FINAL SUCCESS LINE - login has an
    earlier, unrelated "ok = @true" of its own (an early-return branch's
    local success), and the first draft of this mutant landed there by
    mistake, which produced a file B5 correctly read as still-in-order.
    """
    lines = src.splitlines(keepends=True)
    start = end = None
    success_i = None
    for i, line in enumerate(lines):
        if GATE_GUARD_MODE in line and start is None:
            start = i
        if start is not None and end is None and line.rstrip() == "   end":
            # the first bare "   end" after start closes the outer if
            end = i
        if line.strip() == SUCCESS_LINE:
            success_i = i  # keep overwriting: the LAST match wins
    if start is None or end is None or success_i is None or success_i <= end:
        return src
    block = lines[start:end + 1]
    rest = lines[:start] + lines[end + 1:]
    # success_i's index shifted by removing the block, if the block was
    # before it (it is, here) - find the SAME (last) success line in rest.
    at = None
    for i, line in enumerate(rest):
        if line.strip() == SUCCESS_LINE:
            at = i
    return "".join(rest[:at + 1] + block + rest[at + 1:])


def selftest(src):
    print("--- self-test: each mutation must be CAUGHT by at least one check ---")
    base = checks(src, installsdai="chown -R sdsys:sdusers \"$sdsysdir/batch.jobs\"\n"
                                    "chmod 750 \"$sdsysdir/batch.jobs\"\nbatch.jobs",
                  deletesdai="batch.jobs")
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
    if not os.path.isfile(LOGIN):
        print(f"CANNOT RUN - no {LOGIN}", file=sys.stderr)
        return 2
    with open(LOGIN) as f:
        src = f.read()

    print(f"reading  {LOGIN} ({len(src.splitlines())} lines)")
    print(f"messages {MESSAGES}\n")

    if "--selftest" in argv:
        return selftest(src)

    installsdai = deletesdai = None
    if os.path.isfile(INSTALLSDAI):
        with open(INSTALLSDAI) as f:
            installsdai = f.read()
    if os.path.isfile(DELETESDAI):
        with open(DELETESDAI) as f:
            deletesdai = f.read()

    rows = checks(src, installsdai=installsdai, deletesdai=deletesdai)
    failed = 0
    for name, ok, detail in rows:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")
        if not ok:
            failed += 1
    if not rows:
        print("REFUSING - no checks ran", file=sys.stderr)
        return 2
    print(f"\n{len(rows) - failed} passed, {failed} failed")
    print("NOT MEASURED HERE: whether the gate refuses anybody.  That needs "
          "a witness row on the next install cycle.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
