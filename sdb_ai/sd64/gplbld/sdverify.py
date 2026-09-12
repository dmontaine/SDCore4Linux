#!/usr/bin/env python3
#
# sdverify.py - the shared half of every verify-*.py in this directory.
#               PORT_ADOPTION queue 22 ("verifier intent").
#
#   import sdverify as V                       # it is a module, not a script
#   python3 gplbld/sdverify.py --selftest      # the pure half, no sd, no files
#
# Exit codes every verifier built on this module uses, and they are the port's:
#   0  every decisive check passed
#   1  a decisive check failed
#   2  the test could not be run  (a precondition, not a verdict)
#
# WHY THIS FILE EXISTS AT ALL, AND IT IS THE WHOLE OF QUEUE 22'S FIRST STEP.
# SD Core for Windows has 51 verify-*.ps1 and 28 test-*-units.ps1.  Each
# verifier carries its OWN copy of the result table, the verdict line, the two
# text helpers and the sd driver, and the port needs test-verdict-units.ps1 to
# assert that the verdict line has stayed byte-for-byte identical across four
# of those copies.  That is a check on a smell.  Here the block is imported, so
# the drift it polices cannot happen, and test-sdverify-units.py tests ONE
# implementation instead of asserting that N copies still agree.
#
# WHAT WAS TAKEN FROM THE PORT UNCHANGED (intent, not code):
#   * Note/verdict with a DECISIVE flag, so a run of only informational rows
#     cannot report success.
#   * "NO DECISIVE CHECK RAN" is a FAILURE, not a pass.  CLAUDE.md: a test that
#     passes because it did nothing must fail.
#   * The text helpers are PURE and take a REGULAR EXPRESSION, never a bare
#     string.  They print nothing: a function that both prints and returns
#     hands the caller its own narration joined to the tool's output, and a
#     check on "the output" then quietly becomes a check on the narration.
#   * MATCHING IS CASE-SENSITIVE.  Several fixes here ARE case behaviour, so a
#     case-insensitive match would let a disqualifier match its own success
#     wording and fail a working build.
#   * The raw session output is printed unconditionally.  A conditional print
#     cannot show a subtle refusal, because the condition is the thing that was
#     wrong.
#   * The commands are echoed from the LIST THAT WAS PASSED, not from sd's echo
#     of them: the port has a transcript in which sd's own erase-line sequences
#     rendered a command that executed correctly as a different command.
#
# WHAT IS DIFFERENT HERE, AND EACH DIFFERENCE IS A MEASUREMENT SOMEBODY PAID
# FOR (PROJECT_STATUS "START HERE", 11 Sep 2026):
#   1. EVERY SESSION ENDS IN "OFF" AND build_session() REFUSES TO BUILD ONE
#      THAT DOES NOT.  On an install older than c2b375d the ":" prompt
#      busy-loops at end of input - 369 207 BEL bytes in 10 s, exit 124.  The
#      fix is installed, but an instrument that only works on a current install
#      is the wrong shape for a project whose installs go stale.
#   2. A TIMEOUT IS NOT OPTIONAL AND A TIMED-OUT RUN IS FATAL, NOT EMPTY.  Any
#      verb that prompts eats the next line down a pipe, OFF included.
#   3. NAME EVERY OPTIONAL ARGUMENT.  A verb whose argument is optional prompts
#      for it, and the prompt swallows the following line.  The tell is a
#      transcript whose last line is a prompt and where the next command never
#      appears.
#   4. IT REFUSES TO RUN AS ROOT unless the caller says root is what is being
#      measured.  CLAUDE.md, hand-over rule 3: some measurements here are only
#      valid as an ordinary user, so the wrong shell does not merely fail - it
#      produces a clean-looking wrong answer.
#   5. The account is the CALLER'S OWN, not SDSYS.  The port runs elevated
#      because its fixtures live in SDSYS; on Linux the same fixtures live in
#      /home/sd/user_accounts/<user>, so a verifier built on this module needs
#      no sudo - which is what makes it runnable at all, since the agent
#      maintaining this system cannot sudo.
#
import argparse
import os
import re
import subprocess
import sys
import time

SD = "/usr/local/sdsys/bin/sd"
SDSYS = "/usr/local/sdsys"
ACCOUNTS = "/home/sd/user_accounts"

# Every escape sequence sd writes for cursor and colour control.  Left in the
# transcript they defeat a "^" anchor and hide a line behind an erase.
_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


# ------------------------------------------------------------ pure text tests
#
# Callers escape their own literals - re.escape - because a message id or a
# file name is a literal and a pattern is not, and the port has a check that
# reported a present string as absent by mixing the two.

def says(text, pattern):
    """True if PATTERN matches anywhere in TEXT.  Case-sensitive, multiline."""
    if not text:
        return False
    return re.search(pattern, text, re.MULTILINE) is not None


def say_count(text, pattern):
    """How many times PATTERN matches TEXT.  Case-sensitive, multiline."""
    if not text:
        return 0
    return len(re.findall(pattern, text, re.MULTILINE))


def strip_ansi(text):
    return _ANSI.sub("", text or "")


# --------------------------------------------------------------- the verdict

class Row(object):
    __slots__ = ("check", "expected", "observed", "decisive")

    def __init__(self, check, expected, observed, decisive):
        self.check = check
        self.expected = expected
        self.observed = observed
        self.decisive = decisive

    @property
    def passed(self):
        return self.expected == self.observed


class Run(object):
    """The result table, the verdict and the exit code for one verifier."""

    def __init__(self, name, out=None):
        self.name = name
        self.rows = []
        self.blocked = None          # set by refuse(): the exit-2 reason
        self._out = out or sys.stdout

    # --- narration -------------------------------------------------------
    def say(self, line=""):
        self._out.write(line + "\n")
        self._out.flush()

    def heading(self, title):
        self.say("")
        self.say("=== %s %s" % (title, "=" * max(0, 70 - len(title))))

    # --- rows ------------------------------------------------------------
    def note(self, check, expected, observed, decisive=True):
        """Record one check.  DECISIVE rows decide the exit code; the rest are
        context, and a run made only of them reports FAILED, not PASSED."""
        row = Row(check, expected, observed, decisive)
        self.rows.append(row)
        self.say("  [%s] %s: expected %r, got %r%s"
                 % ("PASS" if row.passed else "FAIL", check,
                    expected, observed, "" if decisive else "   (context)"))
        return row.passed

    # --- verdict ---------------------------------------------------------
    def verdict(self):
        """Print the verdict and return the exit code.  THE NULL CASE IS A
        FAILURE: a run that recorded no decisive check measured nothing, and
        must not be reported as a pass."""
        decisive = [r for r in self.rows if r.decisive]
        failed = [r for r in decisive if not r.passed]
        self.say("")
        if self.blocked is not None:
            self.say("%s: COULD NOT RUN - %s" % (self.name, self.blocked))
            self.say("  %d row(s) recorded; a precondition failed, so none of them"
                     " is a verdict." % len(self.rows))
            return 2
        if not decisive:
            self.say("%s: FAILED - NO DECISIVE CHECK RAN, so this run proves"
                     " nothing." % self.name)
            self.say("  %d row(s) recorded, none of them decisive." % len(self.rows))
            return 1
        if failed:
            self.say("%s: FAILED - %d of %d decisive checks failed:"
                     % (self.name, len(failed), len(decisive)))
            for r in failed:
                self.say("    %s: expected %r, got %r"
                         % (r.check, r.expected, r.observed))
            return 1
        self.say("%s: PASSED - %d of %d decisive checks passed, %d row(s) in all."
                 % (self.name, len(decisive), len(decisive), len(self.rows)))
        return 0

    # --- preconditions ---------------------------------------------------
    def refuse(self, reason, *detail):
        """A precondition failed.  The run is exit 2 whatever the rows say."""
        self.blocked = reason
        self.say("%s: CANNOT RUN - %s" % (self.name, reason))
        for d in detail:
            self.say("  " + d)
        return 2


# -------------------------------------------------------- preconditions (2)

def require_not_root(run, why):
    """Refuse a root shell.  WHY says what the measurement would mean instead,
    because 'it needs no sudo' is not the reason - a root session answers a
    DIFFERENT question and answers it cleanly."""
    if os.geteuid() == 0:
        return run.refuse("this must run as an ordinary user and this shell is root",
                          why,
                          "Re-run it as the account whose access is being measured.")
    return 0


def require_paths(run, *paths):
    missing = [p for p in paths if not os.path.exists(p)]
    if missing:
        return run.refuse("a path it measures does not exist",
                          *["missing: " + m for m in missing])
    return 0


def require_current(run, repo=None):
    """Run assert-current.py and refuse on anything but 0.

    A RESULT FROM A STALE TREE IS WORSE THAN NO RESULT: IT LOOKS LIKE
    EVIDENCE.  Exit 2 from assert-current ("the question cannot be answered")
    is refused for the same reason as exit 1."""
    here = os.path.dirname(os.path.abspath(__file__))
    script = os.path.join(here, "assert-current.py")
    if not os.path.exists(script):
        return run.refuse("assert-current.py is not next to this script",
                          "looked for: " + script)
    p = subprocess.run([sys.executable, script],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       universal_newlines=True)
    run.say("  assert-current exit %d" % p.returncode)
    for line in p.stdout.rstrip("\n").split("\n"):
        run.say("    | " + line)
    if p.returncode != 0:
        return run.refuse(
            "the installed system does not match the source (assert-current %d)"
            % p.returncode,
            "A measurement from a stale install looks like evidence and is not.",
            "Run a delete->install cycle, or state the commit the install was"
            " built from and why the delta cannot affect this check.")
    return 0


# --------------------------------------------------------------- the driver

class Session(object):
    """What one piped sd session did.  Everything a caller needs to say what it
    measured, not just what it concluded."""

    __slots__ = ("commands", "argv", "cwd", "text", "rc", "seconds",
                 "timed_out", "bel")

    def __init__(self, commands, argv, cwd, text, rc, seconds, timed_out, bel):
        self.commands = commands
        self.argv = argv
        self.cwd = cwd
        self.text = text
        self.rc = rc
        self.seconds = seconds
        self.timed_out = timed_out
        self.bel = bel


def build_session(commands, logto=None):
    """The exact bytes fed to sd's stdin.

    A LEADING NEWLINE is the sink for anything the terminal emits before the
    first prompt.  TERM 200,9999 stops pagination, which down a pipe is a
    prompt like any other.  OFF ends the session.

    IT REFUSES A SESSION THAT DOES NOT END IN OFF, rather than appending one
    quietly: a caller who wrote their own OFF in the middle of the list has a
    different bug, and silently fixing the end of the list would hide it."""
    if not commands:
        raise ValueError("build_session: no commands - there is nothing to measure")
    for c in commands:
        if c.strip().upper() == "OFF":
            raise ValueError("build_session: OFF is added by this function; "
                             "a caller's own OFF ends the session early and "
                             "every command after it is silently not run")
    lines = []
    if logto:
        lines.append("LOGTO " + logto)
    lines.append("TERM 200,9999")
    lines.extend(commands)
    lines.append("OFF")
    return "\n" + "\n".join(lines) + "\n"


def run_sd(commands, cwd, timeout=60, logto=None, sd=SD):
    """Drive sd down a pipe from CWD and return a Session.

    A TIMEOUT IS ALWAYS SET AND A TIMED-OUT RUN SAYS SO.  Returning empty text
    on a timeout is how a hang becomes a passed check that measured nothing."""
    body = build_session(commands, logto=logto)
    argv = [sd]
    t0 = time.time()
    timed_out = False
    try:
        p = subprocess.run(argv, cwd=cwd, input=body,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           universal_newlines=True, timeout=timeout)
        out, rc = p.stdout, p.returncode
    except subprocess.TimeoutExpired as e:
        timed_out = True
        out = e.stdout if isinstance(e.stdout, str) else (
            e.stdout.decode("utf-8", "replace") if e.stdout else "")
        rc = None
    seconds = time.time() - t0
    bel = (out or "").count("\a")
    return Session(list(commands), argv, cwd, strip_ansi(out), rc, seconds,
                   timed_out, bel)


def show_sd(run, title, commands, cwd, timeout=60, logto=None, sd=SD):
    """Run a session and print EVERYTHING it did before anything reads it.

    The inputs printed are the ones actually used - the resolved binary, the
    resolved working directory, the command list as passed.  CLAUDE.md: an
    instrument shows what it DID, not just what it concluded."""
    run.say("  --- sd session: %s ---" % title)
    run.say("    binary : %s" % sd)
    run.say("    cwd    : %s" % cwd)
    if logto:
        run.say("    logto  : %s" % logto)
    for c in commands:
        run.say("    > " + c)
    s = run_sd(commands, cwd, timeout=timeout, logto=logto, sd=sd)
    run.say("    --- sd said (exit %s, %.2f s, %d BEL) ---"
            % ("TIMEOUT" if s.timed_out else s.rc, s.seconds, s.bel))
    for line in s.text.rstrip("\n").split("\n"):
        run.say("    | " + line.rstrip())
    if s.timed_out:
        run.say("    *** sd did not finish in %d s - it is waiting for input." % timeout)
        run.say("    *** A verb that prompts eats the next line down a pipe,")
        run.say("    *** OFF included.  Name every optional argument.")
        run.say("    *** The session's user-table slot and any locks it holds")
        run.say("    *** are left behind; check LISTU and LIST.READU.")
    run.say("")
    return s


def session_ok(run, step, s, decisive=True):
    """One decisive row per session: it finished.  Every later row reads text
    that only means anything if this one passed."""
    return run.note(step + ": session ended (not a timeout)",
                    True, not s.timed_out, decisive)


# ------------------------------------------------------------------ selftest
#
# The PURE half only: no sd, no install, no files.  It is here rather than in
# test-sdverify-units.py so that a verifier can assert its own harness is sane
# in one call; the units file is the fuller set.

def _selftest():
    import io
    fails = []

    def ck(name, got, want):
        if got != want:
            fails.append("%s: got %r want %r" % (name, got, want))

    # says / say_count are case-SENSITIVE and multiline
    ck("says hit", says("Deleted index F1", re.escape("Deleted index F1")), True)
    ck("says case", says("Deleted index F1", re.escape("deleted index f1")), False)
    ck("says empty", says("", "x"), False)
    ck("says none-text", says(None, "x"), False)
    ck("count 2", say_count("a\nb\na\n", "^a$"), 2)
    ck("count 0", say_count("", "^a$"), 0)
    ck("anchor multiline", says("x\nDeleted index F1\n", "^Deleted index F1$"), True)
    ck("ansi", strip_ansi("a\x1b[2Kb\x1b[0mc"), "abc")

    # the verdict, including the null case
    def run_of(rows, blocked=None):
        r = Run("t", out=io.StringIO())
        for (e, o, d) in rows:
            r.note("c", e, o, d)
        if blocked:
            r.refuse(blocked)
        return r.verdict()

    ck("no rows at all", run_of([]), 1)
    ck("context rows only", run_of([(1, 1, False), (2, 2, False)]), 1)
    ck("one decisive pass", run_of([(1, 1, True)]), 0)
    ck("one decisive fail", run_of([(1, 2, True)]), 1)
    ck("mixed, decisive fails", run_of([(1, 1, False), (1, 2, True)]), 1)
    ck("mixed, decisive passes", run_of([(1, 2, False), (1, 1, True)]), 0)
    ck("blocked outranks pass", run_of([(1, 1, True)], blocked="no install"), 2)

    # build_session
    ck("session shape", build_session(["WHO"]), "\nTERM 200,9999\nWHO\nOFF\n")
    ck("session logto", build_session(["WHO"], logto="SDSYS"),
       "\nLOGTO SDSYS\nTERM 200,9999\nWHO\nOFF\n")
    for bad, label in ((["WHO", "OFF"], "caller's own OFF"),
                       (["WHO", " off "], "caller's own off, spaced"),
                       ([], "empty command list")):
        try:
            build_session(bad)
            fails.append("build_session accepted %s" % label)
        except ValueError:
            pass

    print("sdverify selftest: %d cases, %d failed" % (26, len(fails)))
    for f in fails:
        print("  FAIL " + f)
    return 1 if fails else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true",
                    help="run the pure half's checks and exit")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(_selftest())
    print(__doc__ or "sdverify.py - import it; --selftest runs the pure checks.")
    sys.exit(2)
