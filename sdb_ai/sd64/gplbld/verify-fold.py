#!/usr/bin/env python3
#
# verify-fold.py - does a name resolve "as typed, then lower, then upper"?
#                  Plan section M1, the case fold that must be INSTALLED AND
#                  WITNESSED before anything in the tree is renamed.  Intent
#                  from the port's verify-fold.ps1 and verify-lcnames.ps1 s.8.
#
#   python3 /home/don/Projects/sdcore4linux/sdb_ai/sd64/gplbld/verify-fold.py
#   python3 .../verify-fold.py --allow-stale       measure a stale install
#
# NO SUDO.  Exit 0 every decisive check passed, 1 a decisive check failed,
# 2 the test could not be run.
#
# ***WHY IT HAS TO MAKE LOWER-CASE RECORDS: NOTHING SD SHIPS IS LOWER CASE, SO
# NO ORDINARY SESSION EVER EXERCISES THE DOWNWARD HALF OF THE FOLD.***  The
# port learned it at the verb dispatch (its 8f808a3): reading PARSER said
# dispatch already folded three ways, and the verb never reaches PARSER - a
# VOC id 'zzprobev' dispatched when typed lower and answered "ZZPROBEV is not
# in your VOC" when typed upper.  So every row here MAKES a lower-case id and
# reaches it by its UPPER-case name.
#
# THREE ROUTES, BECAUSE THE FOLD LIVES IN THREE DIFFERENT PLACES:
#   V  the verb dispatch, CPROC            a lower-case VERB typed in upper case
#   C  a verb that opens a file, QPROC     COUNT of a lower-case FILE, typed upper
#   O  the BASIC OPEN statement, _VOC_REF  only a program reaches it (see .bp)
# and each has a control that must answer the same before and after (the name
# as spelled) and a control that must STILL fail (a name in no case at all), so
# the fold cannot pass by making everything resolve.
#
# ***MEASURED BEFORE THE FOLD, 12 Sep 2026, install f14919c (the same shipped
# code as 38dafd2):*** zzfoldv -> "9 DON"; ZZFOLDV -> "ZZFOLDV is not in your
# VOC"; COUNT zzfoldf -> "0 record(s) counted"; COUNT ZZFOLDF -> "File not
# found".  So on that install V2 and C2 must FAIL - this file's red control is
# the pre-fold install itself, and a run there that passed them would mean the
# instrument cannot see the defect.
#
# ***WHAT IT TOUCHES, AND IT IS ALL ITS OWN.***  zzfoldv (a copy of WHO),
# zzfoldf (CREATE.FILE), zzfoldq (a Q-pointer the probe writes) and BP/ZZFOLD.
# It refuses to run if any of them already exists, and removes them after.
# BP.OUT is removed only if this run created it.
#
import argparse
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sdverify as V                                    # noqa: E402

NAME = "verify-fold"
PROBE_SRC = os.path.join(HERE, "verify-fold.bp")
PROBE = "ZZFOLD"
VERB = "zzfoldv"
FILE = "zzfoldf"
QPTR = "zzfoldq"
ABSENT = "ZZFOLDNONE"

# Wording, measured on the pre-fold install (header).  Each is printed only on
# the path it names.
NOT_IN_VOC = r"^%s is not in your VOC$"
COUNTED = r"^0 record\(s\) counted$"
FNF = r"^File not found$"


def tag(text, name):
    """The value of a TAG=value line, or None if the tag never appeared."""
    m = re.search(r"^%s=(.*)$" % re.escape(name), text, re.MULTILINE)
    return m.group(1).strip() if m else None


def main():
    ap = argparse.ArgumentParser(description="the plan M1 name fold")
    ap.add_argument("--account", default=None, help="account directory")
    ap.add_argument("--allow-stale", action="store_true",
                    help="measure an install assert-current calls stale")
    ap.add_argument("--timeout", type=int, default=60,
                    help="seconds per sd session (default 60)")
    a = ap.parse_args()

    run = V.Run(NAME)
    user = os.environ.get("USER") or "?"
    acct = a.account or os.path.join(V.ACCOUNTS, user)
    bp = os.path.join(acct, "bp")           # plan M3 D3
    bpout = os.path.join(acct, "bp.out")    # plan M3 D4: CREATE.FILE makes it lower
    # WHO prints "<user number> <ACCOUNT>"; the account id is upper case today.
    # @WHO is the account name, lower case since 13 Sep 2026 (was upper).
    who = r"^[0-9]+ %s$" % re.escape(os.path.basename(acct).lower())

    run.say("%s: as %s (uid %d), NOT elevated" % (NAME, user, os.geteuid()))
    run.say("  sd        %s" % V.SD)
    run.say("  account   %s" % acct)
    run.say("  probe     %s  ->  %s" % (PROBE_SRC, os.path.join(bp, PROBE)))
    run.say("  fixtures  VOC %s (verb), %s (file), %s (Q-pointer)"
            % (VERB, FILE, QPTR))
    run.say("")

    run.heading("0. preconditions")
    if V.require_not_root(
            run,
            "The fixtures and the probe live in the CALLER'S own account; a"
            " root session lands in SDSYS, where they are not."):
        return run.verdict()
    if V.require_paths(run, V.SD, V.SDSYS, acct, PROBE_SRC):
        return run.verdict()
    if a.allow_stale:
        run.say("  *** --allow-stale: assert-current is NOT being enforced.")
        run.say("  *** Say which commit the install was built from when quoting")
        run.say("  *** any row below.")
        V.require_current(run)
        run.blocked = None
    elif V.require_current(run):
        return run.verdict()
    if V.require_running(run, acct):
        return run.verdict()

    # ***REFUSE IF THE GROUND IS NOT CLEAR, IN EITHER CASE.***  A surviving
    # fixture - under its own spelling OR its upper-case one - belongs to
    # something else, and an upper-case twin would let the "fold" rows pass by
    # exact match.
    run.heading("1. the ground is clear")
    names = [VERB, FILE, QPTR, VERB.upper(), FILE.upper(), QPTR.upper()]
    s = V.show_sd(run, "readback", ["CT VOC %s" % " ".join(names)],
                  cwd=acct, timeout=a.timeout)
    # GATED: the check below reads an ABSENCE as "exists" (see sdverify.reached_off).
    if not V.session_ok(run, "G session", s):
        run.refuse("the ground-check session did not run, so nothing is known"
                   " about the fixtures")
        return run.verdict()
    for n in names:
        if not V.says(s.text, r"^Record '%s' not found$" % re.escape(n)):
            run.refuse("VOC %s already exists" % n,
                       "It is this run's fixture name and this run has not made"
                       " it, so it belongs to something else.")
            return run.verdict()
    # 13 Sep 26 - plan M3 D4: CREATE.FILE makes the directory lower case now, so
    # the fixture's directory is FILE; the upper spelling is refused too, since
    # a leftover from before D4 would be a second casing of the same file.
    for p in (os.path.join(bp, PROBE), os.path.join(acct, FILE),
              os.path.join(acct, FILE.upper())):
        if os.path.exists(p):
            run.refuse("%s already exists" % p)
            return run.verdict()
    bpout_before = os.path.exists(bpout)
    run.say("  BP.OUT existed before this run: %s" % bpout_before)

    # ----------------------------------------------------------- 2. fixtures
    run.heading("2. fixtures - lower-case ids, made the ordinary way")
    os.makedirs(bp, exist_ok=True)
    shutil.copyfile(PROBE_SRC, os.path.join(bp, PROBE))
    run.say("  staged %s" % os.path.join(bp, PROBE))
    s = V.show_sd(run, "make the fixtures and compile the probe",
                  # COPY reads the SOURCE record id exactly, and plan M3
                  # renamed WHO to who: try both spellings.  Exactly one
                  # copies, so F1's "1 record(s) copied." still means one.
                  ["COPY FROM VOC who,%s" % VERB,
                   "COPY FROM VOC WHO,%s" % VERB,
                   "CREATE.FILE %s" % FILE,
                   "BASIC BP %s" % PROBE],
                  cwd=acct, timeout=a.timeout)
    V.session_ok(run, "F session", s)
    run.note("F1 the verb fixture was copied", True,
             V.says(s.text, r"^1 record\(s\) copied\.$"))
    run.note("F2 the file fixture was created", True,
             V.says(s.text, r"^Created DATA part as %s$" % FILE))
    run.note("F3 the probe compiled with 0 errors", True,
             V.says(s.text, r"^0 error\(s\)"))
    run.note("F4 and no error summary followed it", True,
             not V.says(s.text, r"with errors in"))

    # ------------------------------------------------------ 3. V: dispatch
    run.heading("3. V - the verb dispatch (CPROC)")
    s = V.show_sd(run, "as spelled", [VERB], cwd=acct, timeout=a.timeout)
    V.session_ok(run, "V1 session", s)
    run.note("V1 control: %s as spelled dispatches" % VERB, True,
             V.says(s.text, who))
    s = V.show_sd(run, "upper case", [VERB.upper()], cwd=acct, timeout=a.timeout)
    V.session_ok(run, "V2 session", s)
    run.note("V2 THE ROW: %s dispatches the lower-case verb" % VERB.upper(),
             True, V.says(s.text, who))
    run.note("V3 and it did not say 'not in your VOC'", True,
             not V.says(s.text, NOT_IN_VOC % re.escape(VERB.upper())))
    s = V.show_sd(run, "absent", [ABSENT], cwd=acct, timeout=a.timeout)
    V.session_ok(run, "V4 session", s)
    run.note("V4 control: a name in no case is still refused", True,
             V.says(s.text, NOT_IN_VOC % re.escape(ABSENT)))

    # ------------------------------------------------- 4. C: a verb's open
    run.heading("4. C - a verb that opens a file (QPROC)")
    s = V.show_sd(run, "as spelled", ["COUNT %s" % FILE], cwd=acct,
                  timeout=a.timeout)
    V.session_ok(run, "C1 session", s)
    run.note("C1 control: COUNT %s counts" % FILE, True, V.says(s.text, COUNTED))
    s = V.show_sd(run, "upper case", ["COUNT %s" % FILE.upper()], cwd=acct,
                  timeout=a.timeout)
    V.session_ok(run, "C2 session", s)
    run.note("C2 THE ROW: COUNT %s counts the lower-case file" % FILE.upper(),
             True, V.says(s.text, COUNTED))
    run.note("C3 and it did not say 'File not found'", True,
             not V.says(s.text, FNF))
    s = V.show_sd(run, "absent", ["COUNT %s" % ABSENT], cwd=acct,
                  timeout=a.timeout)
    V.session_ok(run, "C4 session", s)
    run.note("C4 control: COUNT of a name in no case is still refused", True,
             V.says(s.text, FNF))

    # ----------------------------------------------- 5. O: BASIC OPEN
    run.heading("5. O - the BASIC OPEN statement (_VOC_REF)")
    s = V.show_sd(run, "RUN BP %s" % PROBE, ["RUN BP %s" % PROBE],
                  cwd=acct, timeout=a.timeout)
    V.session_ok(run, "P session", s)
    t = s.text
    run.note("P1 the probe started", "1", tag(t, "ZZFOLD.BEGIN"))
    run.note("P2 the probe RAN TO THE END", "1", tag(t, "ZZFOLD.END"))
    run.note("P3 it could open VOC", None, tag(t, "ZZFOLD.FATAL"))
    run.note("P4 it wrote the Q-pointer fixture", "1", tag(t, "Q.WRITTEN"))
    run.note("O1 control: open '%s' as spelled" % FILE, "Y", tag(t, "OPEN.EXACT"))
    run.note("O2 THE ROW: open '%s' reaches the lower-case file" % FILE.upper(),
             "Y", tag(t, "OPEN.UPPER"))
    run.note("O3 the upward half: open 'voc' reaches VOC", "Y",
             tag(t, "OPEN.VOCLOWER"))
    run.note("O4 control: open of a name in no case still fails", "N",
             tag(t, "OPEN.ABSENT"))
    run.note("O5 a Q-pointer naming %s reaches the lower-case target"
             % FILE.upper(), "Y", tag(t, "OPEN.QTARGET"))

    s = V.show_sd(run, "the Q-pointer, read back in a fresh session",
                  ["CT VOC %s" % QPTR], cwd=acct, timeout=a.timeout)
    V.session_ok(run, "Q session", s)
    run.note("Q1 the Q-pointer fixture is what the probe says it wrote", True,
             V.says(s.text, r"^1: Q$") and V.says(s.text, r"^3: %s$" % FILE.upper()))

    # ------------------------------------------------------------ 6. tidy up
    run.heading("6. tidy up")
    V.show_sd(run, "post-clean",
              ["DELETE.FILE %s FORCE NO.QUERY" % FILE,
               "DELETE VOC %s" % VERB,
               "DELETE VOC %s" % QPTR],
              cwd=acct, timeout=a.timeout)
    for p in [os.path.join(bp, PROBE)]:
        if os.path.exists(p):
            os.remove(p)
    if not bpout_before:
        V.show_sd(run, "BP.OUT was made by this run", ["DELETE VOC bp.out"],
                  cwd=acct, timeout=a.timeout)
        shutil.rmtree(bpout, ignore_errors=True)
    elif os.path.exists(os.path.join(bpout, PROBE)):
        os.remove(os.path.join(bpout, PROBE))
    s = V.show_sd(run, "nothing of ours is left",
                  ["CT VOC %s" % " ".join([VERB, FILE, QPTR])],
                  cwd=acct, timeout=a.timeout)
    V.session_ok(run, "cleanup readback", s)
    run.note("Z1 no fixture is left in the VOC", 3,
             V.say_count(s.text, r"^Record 'zzfold[vfq]' not found$"))
    run.note("Z2 the file fixture is gone from disk", False,
             os.path.exists(os.path.join(acct, FILE)))

    rc = run.verdict()
    if a.allow_stale:
        run.say("  (measured with --allow-stale: the install is NOT current.)")
    return rc


if __name__ == "__main__":
    sys.exit(main())
