#!/usr/bin/env python3
#
# test-sdverify-units.py - drive every arm of sdverify.py, INCLUDING THE ARMS
#                          THAT MUST FAIL.  PORT_ADOPTION queue 22.
#
#   python3 /home/don/Projects/sdcore4linux/sdb_ai/sd64/gplbld/test-sdverify-units.py
#
# No sudo.  No install.  It never runs the real sd.  Exit 0 all cases passed,
# 1 a case failed.
#
# WHY IT IS SEPARATE FROM sdverify.py --selftest.  The selftest covers the PURE
# half - text matching and the verdict - and a verifier can call it in one line
# to assert its own harness is sane.  This file covers THE DRIVER, which is the
# half that can lie: run_sd can return empty text on a hang, swallow the
# session body, or hand back sd's escape sequences, and every one of those
# turns into a check that passes having measured nothing.
#
# HOW THE DRIVER IS TESTED WITHOUT AN INSTALL.  Each case writes a THROWAWAY
# SHELL SCRIPT that stands in for sd - one that echoes the stdin it was given,
# one that emits ANSI and BEL, one that sleeps past the timeout - so the arm
# under test is the driver's handling of what a real sd could do, measured
# rather than argued.  A real-sd case would need a current install and would
# test sd, not this file.
#
# ***THE LOAD-BEARING CASES ARE THE RED ONES.***  "The driver reports a timeout
# as a timeout" and "a run with no decisive row FAILS" are the two properties
# that separate this harness from a block of code that always says PASS; a
# green suite that omits them proves nothing about either.
#
import io
import os
import re
import stat
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sdverify as V                                    # noqa: E402

FAILS = []
CASES = [0]


def ck(name, got, want):
    CASES[0] += 1
    if got != want:
        FAILS.append("%s\n      got  %r\n      want %r" % (name, got, want))
        print("  FAIL %s" % name)
    else:
        print("  pass %s" % name)


def stub(tmp, name, body):
    """Write a throwaway executable standing in for sd, and return its path."""
    p = os.path.join(tmp, name)
    with open(p, "w") as f:
        f.write("#!/bin/sh\n" + body)
    os.chmod(p, os.stat(p).st_mode | stat.S_IXUSR)
    return p


def quiet_run(name="t"):
    return V.Run(name, out=io.StringIO())


# ---------------------------------------------------------------- the driver

def driver_cases(tmp):
    print("--- the driver (a stub stands in for sd) ---")

    # 1. THE SESSION BODY REALLY REACHES THE PROCESS.  A driver that built the
    #    right string and piped the wrong one would pass every text check
    #    below by accident, so this is measured on the process's own stdin.
    echo = stub(tmp, "sd-echo", 'cat\n')
    s = V.run_sd(["WHO"], cwd=tmp, sd=echo, timeout=10)
    ck("stdin delivered verbatim", s.text, "\nTERM 200,9999\nWHO\nOFF\n")
    ck("stdin ends in OFF", s.text.rstrip("\n").split("\n")[-1], "OFF")
    ck("exit code reported", s.rc, 0)
    ck("not a timeout", s.timed_out, False)
    ck("cwd is the one passed", s.cwd, tmp)
    ck("argv names the binary used", s.argv, [echo])

    # 2. LOGTO GOES FIRST, before TERM - a TERM issued in the old account is
    #    not the one the measured account runs under.
    s = V.run_sd(["WHO"], cwd=tmp, sd=echo, timeout=10, logto="SDSYS")
    ck("logto precedes term", s.text, "\nLOGTO SDSYS\nTERM 200,9999\nWHO\nOFF\n")

    # 3. ESCAPE SEQUENCES ARE STRIPPED AND BEL IS COUNTED, NOT STRIPPED.  The
    #    port has a transcript where sd's own erase-line sequences rendered a
    #    command that executed correctly as a different command; and a BEL
    #    count is how the ":"-prompt busy-loop (PROJECT_STATUS, queue 26) shows
    #    up as a number instead of as a hung run.
    noisy = stub(tmp, "sd-noisy",
                 "printf 'a\\033[2Kb\\033[0m\\007\\007c\\n'\n")
    s = V.run_sd(["WHO"], cwd=tmp, sd=noisy, timeout=10)
    ck("ansi stripped, bel left in place", s.text, "ab\x07\x07c\n")
    ck("bel counted", s.bel, 2)

    # 4. ***A TIMEOUT IS REPORTED AS A TIMEOUT.***  This is the case that stops
    #    a hang becoming a green run: the text may be empty, but timed_out must
    #    be true and the caller's session_ok row must FAIL.
    hang = stub(tmp, "sd-hang", "printf 'starting\\n'; sleep 30\n")
    s = V.run_sd(["WHO"], cwd=tmp, sd=hang, timeout=2)
    ck("timeout flagged", s.timed_out, True)
    ck("timeout has no exit code", s.rc, None)
    ck("timeout bounded by the timeout", s.seconds < 10, True)

    r = quiet_run()
    V.session_ok(r, "hung", s)
    ck("session_ok fails a timeout", r.verdict(), 1)

    r = quiet_run()
    V.session_ok(r, "fine", V.run_sd(["WHO"], cwd=tmp, sd=echo, timeout=10))
    ck("session_ok passes a finished run", r.verdict(), 0)

    # 5. A NON-ZERO EXIT IS NOT A TIMEOUT.  Conflating them would report a
    #    refusal as a hang and send the next session chasing locks.
    bad = stub(tmp, "sd-bad", "printf 'no\\n'; exit 3\n")
    s = V.run_sd(["WHO"], cwd=tmp, sd=bad, timeout=10)
    ck("non-zero exit kept", s.rc, 3)
    ck("non-zero exit is not a timeout", s.timed_out, False)

    # 6. show_sd PRINTS THE REAL INPUTS AND THE RAW OUTPUT, unconditionally.
    buf = io.StringIO()
    r = V.Run("t", out=buf)
    V.show_sd(r, "titled", ["WHO"], cwd=tmp, sd=echo, timeout=10)
    shown = buf.getvalue()
    ck("shows the binary", V.says(shown, re.escape("binary : " + echo)), True)
    ck("shows the cwd", V.says(shown, re.escape("cwd    : " + tmp)), True)
    ck("echoes the command as passed", V.says(shown, r"^    > WHO$"), True)
    ck("prints the raw output", V.says(shown, r"^    \| TERM 200,9999$"), True)

    buf = io.StringIO()
    r = V.Run("t", out=buf)
    V.show_sd(r, "hung", ["WHO"], cwd=tmp, sd=hang, timeout=2)
    ck("a timeout says so in the transcript",
       V.says(buf.getvalue(), r"did not finish in 2 s"), True)


# ----------------------------------------------------------- preconditions

def precondition_cases(tmp):
    print("--- preconditions (exit 2 is not a verdict) ---")

    r = quiet_run()
    ck("require_paths passes on a real path", V.require_paths(r, tmp), 0)
    ck("  and leaves the run unblocked", r.blocked, None)

    r = quiet_run()
    missing = os.path.join(tmp, "no-such-thing")
    ck("require_paths refuses a missing path", V.require_paths(r, missing), 2)
    ck("  and blocks the run", r.blocked is not None, True)
    ck("  so a passing row cannot rescue it",
       (r.note("c", 1, 1, True), r.verdict())[1], 2)

    # require_not_root: this suite runs as an ordinary user, so the root arm
    # cannot be reached honestly.  Say so rather than skipping it silently -
    # an unreachable arm reported as a pass is the null case.
    r = quiet_run()
    if os.geteuid() == 0:
        ck("require_not_root refuses root", V.require_not_root(r, "why"), 2)
    else:
        ck("require_not_root admits an ordinary user",
           V.require_not_root(r, "why"), 0)
        print("  note  the root arm is NOT covered: this suite runs as uid %d."
              % os.geteuid())

    # require_current is not stubbed: it shells out to assert-current.py, and
    # what it must do is refuse anything but 0.  Whether it refuses depends on
    # the install, so assert on the SHAPE both ways.
    r = quiet_run()
    rc = V.require_current(r)
    ck("require_current returns 0 or 2 only", rc in (0, 2), True)
    ck("require_current blocks exactly when it returns 2",
       (r.blocked is not None), rc == 2)


# ------------------------------------------------------------ the pure half

def pure_cases():
    print("--- the pure half (the selftest's ground, re-run here) ---")
    ck("sdverify --selftest exits 0",
       subprocess.run([sys.executable, os.path.join(HERE, "sdverify.py"),
                       "--selftest"],
                      stdout=subprocess.PIPE).returncode, 0)

    # The properties the selftest asserts that this file depends on, restated
    # as this file's own cases so a change to one is caught by both.
    ck("no decisive row is a FAILURE, not a pass", quiet_run().verdict(), 1)

    r = quiet_run()
    r.note("context", 1, 1, False)
    ck("context rows alone are still a FAILURE", r.verdict(), 1)

    r = quiet_run()
    r.note("real", 1, 1, True)
    ck("one decisive pass is a pass", r.verdict(), 0)

    ck("matching is case-sensitive",
       V.says("Deleted index F1", "Deleted index f1"), False)


def main():
    print("test-sdverify-units.py - sdverify.py under test")
    print("  module : %s" % os.path.join(HERE, "sdverify.py"))
    print("  uid    : %d (%s)" % (os.geteuid(), os.environ.get("USER", "?")))
    print("")
    with tempfile.TemporaryDirectory(prefix="sdverify-units-") as tmp:
        driver_cases(tmp)
        precondition_cases(tmp)
    pure_cases()
    print("")
    print("test-sdverify-units: %d cases, %d failed" % (CASES[0], len(FAILS)))
    for f in FAILS:
        print("  FAIL %s" % f)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
