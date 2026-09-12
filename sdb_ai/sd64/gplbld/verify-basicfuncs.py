#!/usr/bin/env python3
#
# verify-basicfuncs.py - do SD BASIC's intrinsic functions and operators return
#                        the RIGHT ANSWERS?  PORT_ADOPTION queue 22, ranked
#                        item 5; intent from the port's verify-basicfuncs.ps1.
#
#   python3 /home/don/Projects/sdcore4linux/sdb_ai/sd64/gplbld/verify-basicfuncs.py
#   python3 .../verify-basicfuncs.py --allow-stale     measure a stale install
#
# NO SUDO.  Exit 0 every decisive check passed, 1 a decisive check failed,
# 2 the test could not be run.
#
# ***WHY IT EXISTS: IT ASKS THE QUESTION UNDERNEATH THE OTHER VERIFIERS.***
# They ask whether a status was discarded, a lock stranded, a tier enforced.
# This one asks whether the language answers correctly at all - every report,
# every VOC verb, every one of those other verifiers is built out of these
# functions.  Nothing else in this tree checks that ABS, OCONV, LOCATE or the
# comparison operators return correct values, so a pcode or opcode regression
# would surface as a wrong report from a user rather than as a red step.
#
# THREE THINGS IT DOES THAT THE PORT'S SCRIPT DOES NOT, EACH FOR A REASON THAT
# WAS MEASURED RATHER THAN ARGUED:
#
#   1. ***PYTHON DERIVES THE VERDICT; THE PROBE ONLY REPORTS.***  The port's
#      probe prints OK| or FAIL| from its own "if sg = sw", which makes a BASIC
#      program the judge of a language whose EQUALITY OPERATOR IS ONE OF THE
#      THINGS UNDER TEST.  A broken "=" would print OK for every case and the
#      run would go green.  Here each case prints CASE|name|got|want on ONE
#      path, every case becomes its own decisive row in sdverify's table, and
#      the probe's own tally is reconciled against Python's as a SECOND
#      instrument rather than as the verdict.
#      ***THAT RECONCILIATION ROW (Q1) FIRED ON THE VERY FIRST RUN, AND WHAT
#      IT CAUGHT WAS A DEFECT IN THIS FILE.***  12 Sep 2026: the probe counted
#      0 failures, Python derived 2, and Python was wrong - its own rstrip()
#      had trimmed the trailing spaces off the TRIMF and FMT.L expectations.
#      A verifier that trusted the probe would have gone green; one that
#      trusted only itself would have reported two defects SD does not have.
#      Reporting the DISAGREEMENT is what made the fault findable, and the
#      terminator described in cases_from() is the fix.
#
#   2. ***THE COVERAGE CLAIM IS MEASURED.***  The probe's NOT.TESTED: comment
#      lines are machine-readable.  This script reads the intrinsics table out
#      of the SOURCE tree's sdsys/GPL.BP/BCOMP and FAILS if any intrinsic is
#      neither exercised by the probe nor named as excluded.  Running that
#      arithmetic against the port, 12 Sep 2026, is what found the gap this
#      probe closes: of the same 176 intrinsics, the port's file accounts for
#      175 - DELETE is both tested and declared excluded, CHANGE is excluded
#      under "change the process" when gplsrc/op_chnge.c is a substring
#      replace, and SWAP, ASSIGNED and UNASSIGNED appear on neither list.
#      ***SO THE PORT'S "everything else is exercised below" WAS FIVE NAMES
#      OPTIMISTIC, AND NOTHING THERE COULD HAVE TOLD IT.***
#
#   3. ***THE CASE COUNT IS RECONCILED AGAINST THE PROBE SOURCE, NOT AGAINST A
#      CONSTANT.***  A number in this file would go stale the first time a case
#      was added.  The probe is straight-line code, so the number of "gosub
#      check" sites in the staged source is exactly the number of cases that
#      must print; fewer means it stopped part way, and that is exit 2 rather
#      than "no failures found".
#
# RUN IT UNELEVATED, and that is not a preference.  The probe is compiled and
# run in the CALLER'S OWN account; a root session lands in SDSYS, where the
# probe is not, so it would measure the wrong account or nothing at all.
#
# NOT INSTALLED AND NOT SHIPPED.  verify-basicfuncs.bp lives next to this file
# and is staged into the account's BP only for the run.
#
import argparse
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sdverify as V                                    # noqa: E402

NAME = "verify-basicfuncs"
PROBE_SRC = os.path.join(HERE, "verify-basicfuncs.bp")
PROBE = "ZZBF"
BCOMP = os.path.join(HERE, os.pardir, "sdsys", "GPL.BP", "BCOMP")

# The variable the probe deliberately never assigns.  BCOMP warns about it
# (message 2825), and that warning is the null-case guard for the three cases
# that ask what an unassigned variable looks like.
UNSET_VAR = "ZZ.UNSET"


# --------------------------------------------------------------- probe source
#
# Every caller below passes probe_src - the file this run actually stages -
# and never PROBE_SRC: under --probe the coverage arithmetic and the case count
# must describe the red control that ran, not the shipped probe that did not.

def check_sites(path):
    """How many cases the probe source says it will print.

    Every case is one "gosub check" on a non-comment line, and the probe is
    straight-line code with no loop, so each site runs exactly once."""
    code = _code_only(path)
    return len(re.findall(r"(?<![A-Za-z0-9.])gosub\s+check(?![A-Za-z0-9.])",
                          code, re.IGNORECASE))


def _code_only(path):
    """The probe's code with comment lines and string literals removed.

    STRING LITERALS GO TOO, AND THAT IS NOT TIDINESS.  Every case carries its
    own name as a literal - n = 'ABS' - so a scan of the raw text would count
    ABS as exercised because its NAME appears, even if the call beside it were
    deleted.  Stripping the literals means only a real call can match."""
    with open(path, encoding="latin-1") as f:
        text = f.read()
    code = "\n".join(l for l in text.split("\n") if not l.strip().startswith("*"))
    return re.sub(r"'[^']*'|\"[^\"]*\"", " ", code)


def not_tested(path):
    """The names the probe declares it does not exercise."""
    names = set()
    with open(path, encoding="latin-1") as f:
        for line in f:
            m = re.match(r"\*\s*NOT\.TESTED:(.*)", line.strip())
            if m:
                names.update(re.findall(r"[A-Z][A-Z0-9.]*", m.group(1)))
    return names


def intrinsics(path):
    """The intrinsic function names BCOMP itself knows.

    ***THE COMPILER'S OWN TABLE, NOT A TYPED-OUT LIST.***  Same extraction as
    gplbld/mkbasicsyntax.py, and for the same reason: a hand-kept list of 176
    names drifts from the language and nobody notices."""
    with open(path, encoding="latin-1", newline="") as f:
        src = f.read()
    word = re.compile(r'"([A-Z][A-Z0-9.$]*)"')
    names = set()
    for line in src.split("\n"):
        s = line.strip()
        if s.startswith("*"):
            continue
        if re.match(r"intrinsics\s*(<[^>]*>)?\s*:?=", s):
            names.update(word.findall(s))
    return names


def exercised(names, code):
    """Which of NAMES the probe's code actually calls.

    The boundaries matter: without them INDEX matches inside INDEXS, SUM inside
    SUMMATION and NOT inside NOTS, and the coverage claim becomes a claim that
    the longer name was tested."""
    hit = set()
    for n in names:
        pat = (r"(?<![A-Za-z0-9._$])" + re.escape(n) + r"(?![A-Za-z0-9.$])")
        if re.search(pat, code, re.IGNORECASE):
            hit.add(n)
    return hit


# ------------------------------------------------------------ probe transcript

def cases_from(text):
    """Every CASE|name|got|want|END line, in order, as (name, got, want).

    ***THE "END" TERMINATOR IS WHY THE WANT FIELD CAN CONTAIN TRAILING SPACES,
    AND IT WAS PAID FOR BY THE FIRST RUN OF THIS FILE.***  The expectations for
    TRIMF and FMT.L both END IN SPACES.  Without a terminator "want" is the
    last field on the line, this function's own line.rstrip() ate the spaces
    off its own input, and both cases were reported as SD returning the wrong
    answer - "expected 'ab', got 'ab  '" - when SD had returned exactly the
    right one.  TRIMB passed in the same run because its spaces are LEADING,
    which is what pinned the fault to the instrument.

    A LINE THAT DOES NOT SPLIT INTO FIVE, OR WHOSE LAST FIELD IS NOT "END", IS
    REFUSED RATHER THAN GUESSED AT.  The two ways to produce one are a value
    containing "|" and something downstream trimming the line; silently taking
    the fields that are there would turn a mangled case into a passing one."""
    good, bad = [], []
    for line in text.split("\n"):
        line = line.rstrip()
        if not line.startswith("CASE|"):
            continue
        parts = line.split("|")
        if len(parts) != 5 or parts[4] != "END":
            bad.append(line)
        else:
            good.append((parts[1], parts[2], parts[3]))
    return good, bad


def main():
    ap = argparse.ArgumentParser(
        description="do SD BASIC's intrinsics return the right answers?")
    ap.add_argument("--account", default=None, help="account directory")
    ap.add_argument("--allow-stale", action="store_true",
                    help="measure an install assert-current calls stale")
    ap.add_argument("--timeout", type=int, default=90,
                    help="seconds per sd session (default 90)")
    ap.add_argument("--keep", action="store_true",
                    help="leave the staged probe behind for inspection")
    # ***THE RED CONTROL, AND IT SAYS SO IN THE TRANSCRIPT.***  A suite never
    # seen to fail is evidence that the suite is quiet, not that the system is
    # right.  Point this at a probe with a deliberately wrong expectation and
    # the run must go red on exactly that case.
    ap.add_argument("--probe", default=None, metavar="FILE",
                    help="use a different probe source (for the RED CONTROL)")
    a = ap.parse_args()

    run = V.Run(NAME)
    probe_src = a.probe or PROBE_SRC
    user = os.environ.get("USER") or "?"
    acct = a.account or os.path.join(V.ACCOUNTS, user)
    bp = os.path.join(acct, "BP")
    bpout = os.path.join(acct, "BP.OUT")
    staged = os.path.join(bp, PROBE)

    run.say("%s: as %s (uid %d), NOT elevated" % (NAME, user, os.geteuid()))
    run.say("  sd        %s" % V.SD)
    run.say("  account   %s" % acct)
    run.say("  probe     %s  ->  %s" % (probe_src, staged))
    run.say("  compiler  %s" % os.path.normpath(BCOMP))
    if a.probe:
        run.say("")
        run.say("  *** RED CONTROL: this is NOT the shipped probe.")
        run.say("  *** Rows below describe %s, not verify-basicfuncs.bp." % a.probe)
    run.say("")

    # ---------------------------------------------------------- 0. refusals
    run.heading("0. preconditions")
    if V.require_not_root(
            run,
            "The probe is compiled and run in the CALLER'S own account; a root"
            " session lands in SDSYS, where the probe is not."):
        return run.verdict()
    if V.require_paths(run, V.SD, V.SDSYS, acct, probe_src, BCOMP):
        return run.verdict()
    if a.allow_stale:
        run.say("  *** --allow-stale: assert-current is NOT being enforced.")
        V.require_current(run)
        run.blocked = None
    elif V.require_current(run):
        return run.verdict()

    # ***REFUSE IF THE GROUND IS NOT CLEAR.***  A surviving BP/ZZBF belongs to
    # something else - another run, or a --keep - and compiling over it would
    # measure a file this run did not write.
    if os.path.exists(staged):
        run.refuse("%s already exists" % staged,
                   "It is this run's fixture and this run has not staged it"
                   " yet, so it belongs to something else.",
                   "Remove it and run again.")
        return run.verdict()

    expected_cases = check_sites(probe_src)
    run.say("  the probe source has %d 'gosub check' site(s), so it must print"
            " %d case line(s)." % (expected_cases, expected_cases))
    if expected_cases == 0:
        run.refuse("the probe source contains no cases at all",
                   "A run of it would print TALLY|0 and prove nothing.")
        return run.verdict()

    # ---------------------------------------------------- 1. stage and compile
    run.heading("1. stage the probe and compile it")
    bpout_existed = os.path.isdir(bpout)
    os.makedirs(bp, exist_ok=True)
    shutil.copyfile(probe_src, staged)
    run.say("  staged  %s" % staged)
    run.say("  BP.OUT existed before this run: %s" % bpout_existed)

    s = V.show_sd(run, "BASIC BP %s" % PROBE, ["BASIC BP %s" % PROBE],
                  cwd=acct, timeout=a.timeout)
    V.session_ok(run, "C session", s)
    # ANCHOR ON THE COUNT, NOT ON THE WORD "Compiled".  BASIC:330 prints
    # "Compiling ff rr" BEFORE the compile and BCOMP:2612 prints "Compilation
    # error in %1", so the program's name is on both paths and proves nothing.
    # BCOMP:1533 prints message 2995, "%1 error(s)", on the happy path.
    run.note("C1 the probe compiled with 0 errors", True,
             V.says(s.text, r"^0 error\(s\)"))
    run.note("C2 and no error summary followed it", True,
             not V.says(s.text, r"with errors in"))

    # ***THE NULL-CASE GUARD FOR THE UNASSIGNED-VARIABLE CASES.***  The probe
    # never assigns ZZ.UNSET, so BCOMP must warn about it exactly once
    # (message 2825, BCOMP:1497).  No warning would mean the variable acquired
    # a value somewhere and those three cases are asking about the wrong thing;
    # more than one would mean some OTHER variable is accidentally unassigned.
    warn = r"is not assigned a value"
    warn_lines = [l.strip() for l in s.text.split("\n") if re.search(warn, l)]
    for l in warn_lines:
        run.say("      compiler warning: %s" % l)
    run.note("C3 exactly one 'not assigned a value' warning", 1,
             V.say_count(s.text, warn))
    run.note("C4 and it names %s" % UNSET_VAR, True,
             any(re.search(re.escape(UNSET_VAR), l, re.IGNORECASE)
                 for l in warn_lines))

    if not V.says(s.text, r"^0 error\(s\)") or V.says(s.text, r"with errors in"):
        run.refuse("the probe did not compile, so nothing below was measured",
                   "The session transcript above says why.")
        return _finish(run, a, staged, bpout, bpout_existed, acct)

    # ------------------------------------------------------------- 2. run it
    run.heading("2. run the probe")
    s = V.show_sd(run, "RUN BP %s" % PROBE, ["RUN BP %s" % PROBE],
                  cwd=acct, timeout=a.timeout)
    V.session_ok(run, "P session", s)
    t = s.text

    # Every row after this reads the transcript, and a transcript that stopped
    # part way would give each of them its own private reason to fail.  P1-P3
    # say plainly that it did not finish.
    run.note("P1 the probe started", True, V.says(t, r"^PROBE\.BEGIN$"))
    run.note("P2 the probe RAN TO THE END (no fault part way)", True,
             V.says(t, r"^PROBE\.DONE$"))

    m = re.search(r"^TALLY\|(\d+)\|(\d+)$", t, re.MULTILINE)
    run.note("P3 it printed its tally", True, m is not None)
    if m is None or not V.says(t, r"^PROBE\.DONE$"):
        run.refuse("the probe did not finish, so its case lines are a fragment",
                   "A partial run must not be read as 'no failures found'.")
        return _finish(run, a, staged, bpout, bpout_existed, acct)

    probe_cases, probe_fails = int(m.group(1)), int(m.group(2))
    got, malformed = cases_from(t)
    for line in malformed:
        run.say("      MALFORMED case line: %s" % line)
    run.note("P4 no case line was malformed", 0, len(malformed))

    # THE THREE-WAY RECONCILIATION.  The source says how many cases there are,
    # the probe counted how many it ran, and the transcript carries how many it
    # printed.  All three must agree before any of them means anything.
    run.note("P5 the probe ran every case in its source",
             expected_cases, probe_cases)
    run.note("P6 and printed a line for every case it counted",
             probe_cases, len(got))

    names = [c[0] for c in got]
    dupes = sorted(set(n for n in names if names.count(n) > 1))
    run.note("P7 no two cases share a name (a name is how a failure is found)",
             [], dupes)

    # --------------------------------------------------------- 3. the answers
    run.heading("3. every case: the answer SD gave against the one wanted")
    for (case, g, w) in got:
        run.note(case, w, g)

    # ------------------------------------------- 4. the probe's own arithmetic
    run.heading("4. the probe's tally against the verdict derived here")
    mine = sum(1 for (_, g, w) in got if g != w)
    run.say("  cases %d, failures derived here %d, failures the probe counted %d"
            % (len(got), mine, probe_fails))
    # ***THIS ROW IS WHY THE PROBE DOES NOT JUDGE ITSELF.***  The two counts are
    # produced by different equality operators - BASIC's "#" in the probe and
    # Python's "!=" here.  They can only disagree if one of them is wrong, and
    # BASIC's is the one under test.
    run.note("Q1 the probe's failure count agrees with the one derived here",
             mine, probe_fails)

    # ------------------------------------------------------------ 5. coverage
    run.heading("5. coverage: is any intrinsic neither tested nor declared?")
    run.say("  Read from the SOURCE tree's compiler, %s."
            % os.path.normpath(BCOMP))
    if a.allow_stale:
        run.say("  *** --allow-stale is in force, so this section describes the")
        run.say("  *** SOURCE while section 3 describes the INSTALL.")
    known = intrinsics(BCOMP)
    run.note("V1 BCOMP's intrinsics table was readable", True, len(known) > 0)
    if known:
        declared = not_tested(probe_src)
        used = exercised(known, _code_only(probe_src))
        unaccounted = sorted(known - used - declared)
        both = sorted(used & declared)
        stray = sorted(declared - known)
        run.say("  %d intrinsic(s): %d exercised, %d declared not tested."
                % (len(known), len(used), len(known & declared)))
        for u in unaccounted:
            run.say("      UNACCOUNTED: %s" % u)
        for b in both:
            run.say("      BOTH tested and declared not tested: %s" % b)
        for x in stray:
            run.say("      declared not tested but not an intrinsic: %s" % x)
        run.note("V2 every intrinsic is either exercised or declared",
                 [], unaccounted)
        run.note("V3 none is claimed both ways", [], both)
        run.note("V4 the exclusion list names no function that does not exist",
                 [], stray)

    return _finish(run, a, staged, bpout, bpout_existed, acct)


def _finish(run, a, staged, bpout, bpout_existed, acct):
    """Tidy up and report what the tidying actually did.

    ***BP.OUT IS REMOVED ONLY IF THIS RUN CREATED IT.***  It is the account's
    own object directory; a run that deleted somebody else's would be a
    destructive instrument, and the account this runs in is a real one."""
    if a.keep:
        run.heading("6. --keep: the staged probe is left behind")
        run.say("  %s is still there." % staged)
        return run.verdict()

    run.heading("6. tidy up")
    obj = os.path.join(bpout, "ZZBF")
    for p in (staged, obj):
        if os.path.exists(p):
            os.remove(p)
            run.say("  removed %s" % p)
    if not bpout_existed and os.path.isdir(bpout):
        shutil.rmtree(bpout, ignore_errors=True)
        run.say("  removed %s (this run created it)" % bpout)
        V.show_sd(run, "drop the VOC entry this run's compile made",
                  ["DELETE VOC BP.OUT"], cwd=acct, timeout=a.timeout)
    elif bpout_existed:
        run.say("  %s predates this run and is left alone." % bpout)

    run.note("Z1 the staged probe is gone", False, os.path.exists(staged))
    run.note("Z2 its object record is gone", False, os.path.exists(obj))
    return run.verdict()


if __name__ == "__main__":
    sys.exit(main())
