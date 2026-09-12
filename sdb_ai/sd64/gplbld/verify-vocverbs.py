#!/usr/bin/env python3
#
# verify-vocverbs.py - exercise the VOC-verb fixes that need no account and no
#                      sudo: PORT_ADOPTION queue 1 (QSELECT names its list),
#                      queue 3 (NO.QUERY does not prompt on an @SDSYS part) and
#                      queue 3's lower-case half (DELETE.FILE does not prompt
#                      for a file that is exactly where it should be).
#
#   python3 /home/don/Projects/sdcore4linux/sdb_ai/sd64/gplbld/verify-vocverbs.py
#   python3 .../verify-vocverbs.py --prefix zzvvb      use a different name set
#   python3 .../verify-vocverbs.py --allow-stale       measure a stale install
#
# NO SUDO, and that is a Linux divergence from the port worth stating.  SD Core
# for Windows runs its verify-vocverbs.ps1 ELEVATED because every session there
# starts with LOGTO SDSYS and the fixtures live in the SDSYS account directory.
# Here the same fixtures live in the caller's OWN account under
# /home/sd/user_accounts/<user>, so this runs as an ordinary user - which is
# also the only way it can run at all, since the agent maintaining this system
# cannot sudo.  It REFUSES a root shell: a root session answers a different
# question and answers it cleanly.
#
# Exit 0 every decisive check passed, 1 a decisive check failed, 2 the test
# could not be run.
#
# ***WHAT IT TOUCHES, AND IT IS ALL ITS OWN.***  Two file names and one VOC
# pointer, all under --prefix, all created and removed by this run.  The
# @SDSYS fixture is a COPY of the account's own SYSCOM pointer rather than a
# real system file, and the run asserts /usr/local/sdsys/SYSCOM is still on
# disk afterwards - before and after, so "it was already gone" cannot pass.
#
# ***EVERY CHECK ANCHORS ON WORDING THE VERB PRINTS ONLY ON THE PATH UNDER
# TEST, AND NAMES A DISQUALIFIER.***  CLAUDE.md: a pattern shared by the
# success and failure outputs is not a check.
#
#   queue 1   3261 must end in a select list NUMBER.  The defect printed the
#             SAME message with one argument, so the text was identical up to a
#             dangling "select list ".  Matching "select list" would have
#             passed on the defect; the check is that a number follows it.
#   queue 3   10117's own sentence, which only check.sdsys.file's NO.QUERY
#             branch prints, AND the absence of 6146 (the prompt it replaced),
#             AND THE ABSENCE OF 6135.  The third of those was added 12 Sep
#             2026 because this file found the defect it catches, and it is the
#             row the port's own verifier does not have - see below.
#   queue 3b  6136/6141/6144 present and 6135/6140 ABSENT, for a file whose
#             name was typed in lower case.  6135 is guarded by not(force), NOT
#             by no.query, so NO.QUERY does not suppress it: only the
#             case-insensitive path comparison keeps it quiet.  A test that
#             passed FORCE here could not fail.
#
# ***WHY ROW B4 EXISTS, AND IT IS THE WHOLE ARGUMENT FOR QUEUE 22.***  The
# port's verify-vocverbs.ps1 checks 10117 and the absence of 6146 on this
# fixture, and both were true here - while DELETE.FILE went on to print "OK to
# delete DATA portion '' (y/<n>)?" three times and eat the two commands that
# followed.  The VOC record still went and the system file was still left
# alone, so the OUTCOME was right and only the route was wrong.  A check on the
# outcome cannot see that; a check on the ABSENCE of the prompt can.  Measured
# 12 Sep 2026 on install 06d3a4a as don; cause and fix at DELETEF:229-246.
#
# ***MATCHING IS CASE-SENSITIVE.***  Two of the three fixes ARE case behaviour,
# so an insensitive match would let a disqualifier match its own success
# wording and report a broken build as a working one.
#
# ***ONE SESSION PER CHECK, AND THE SESSIONS ARE NOT COMBINED.***  A verb that
# prompts eats the line after it, so a combined session would lose the very
# command that reads the result back, and the transcript would show the check
# as "not found" rather than as the prompt it really was.  Reading the result
# back in a FRESH session also means the read cannot be eaten by the thing it
# is measuring.
#
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sdverify as V                                    # noqa: E402

NAME = "verify-vocverbs"

# The system file the @SDSYS fixture points at.  It is never deleted by this
# run; it is asserted present before and after.
SYSFILE = os.path.join(V.SDSYS, "SYSCOM")

# Message wording, quoted from sdsys/MESSAGES so a change there fails this file
# rather than silently weakening it.  %n stand-ins are replaced per check.
M3261 = r"record\(s\) selected to select list "
M6135 = r"OK to delete DATA portion '"
M6140 = r"OK to delete DICT portion '"
M6136 = r"DATA portion '%s' deleted"
M6141 = r"DICT portion '%s' deleted"
M6144 = r"VOC entry '%s' deleted"
M6145 = r"WARNING: The data part of this file is in the system account"
M6146 = r"Delete the file from the system account"
M10117 = (r"NO\.QUERY was given and the data part of this file is in the "
          r"system account")


def main():
    ap = argparse.ArgumentParser(
        description="exercise the VOC-verb fixes that need no account")
    ap.add_argument("--prefix", default="zzvv",
                    help="name stem for every fixture (default zzvv)")
    ap.add_argument("--account", default=None,
                    help="account directory to run in "
                         "(default /home/sd/user_accounts/$USER)")
    ap.add_argument("--allow-stale", action="store_true",
                    help="measure an install that assert-current calls stale; "
                         "the verdict says so and the rows are still printed")
    ap.add_argument("--timeout", type=int, default=60,
                    help="seconds per sd session (default 60)")
    a = ap.parse_args()

    run = V.Run(NAME)

    # ------------------------------------------------------- what it will use
    user = os.environ.get("USER") or "?"
    acct = a.account or os.path.join(V.ACCOUNTS, user)
    run.say("%s: as %s (uid %d), NOT elevated" % (NAME, user, os.geteuid()))
    run.say("  sd       %s" % V.SD)
    run.say("  sdsys    %s" % V.SDSYS)
    run.say("  account  %s" % acct)
    run.say("  prefix   %s" % a.prefix)

    # ***THE PREFIX RULE IS ABOUT CASE AND NOTHING ELSE.***  CREATE.FILE
    # upper-cases the name for the PATH and leaves the VOC id as typed, and two
    # of the three checks are ABOUT that difference; a mixed-case prefix would
    # make the two sides of the comparison disagree for a reason that is not
    # the one under test.  There is no length cap: SD's own limit is MAX_ID_LEN
    # 255, and the port's cap of 7 once refused its own runner's prefix and
    # exited 2 before measuring anything.
    if not re.match(r"^[a-z][a-z0-9]{1,14}$", a.prefix):
        run.refuse("--prefix is %r" % a.prefix,
                   "Lower case letters and digits only, starting with a letter,"
                   " 2 to 15 characters.",
                   "CREATE.FILE upper-cases the name for the PATH and leaves"
                   " the VOC id as typed, and the checks here are ABOUT that"
                   " difference.")
        return run.verdict()

    ptr = (a.prefix + "f").upper()      # queue 3   copy of the SYSCOM pointer
    wfile = a.prefix + "w"              # queue 3b  lower: the fold IS the test
    run.say("  names    %s, %s" % (ptr, wfile))
    run.say("")

    # -------------------------------------------------------- preconditions
    run.heading("0. preconditions")
    if V.require_not_root(
            run,
            "Every check here is about what an ORDINARY account's verbs do."):
        return run.verdict()
    if V.require_paths(run, V.SD, V.SDSYS, acct, SYSFILE):
        return run.verdict()

    if a.allow_stale:
        run.say("  *** --allow-stale: assert-current is NOT being enforced.")
        run.say("  *** Every row below describes the INSTALLED system, which")
        run.say("  *** the source has moved past.  Say which commit it was")
        run.say("  *** built from when quoting any of this.")
        V.require_current(run)
        run.blocked = None                  # reported, deliberately not fatal
    elif V.require_current(run):
        return run.verdict()

    # --------------------------------------------- 1. clear the ground, then
    #                                                  REFUSE IF IT IS NOT CLEAR
    #
    # Every fixture below is written by this run.  If one of these names
    # survives the sweep it belongs to something else, and every measurement
    # after it would describe a record this script did not write.  CLAUDE.md: a
    # test that passes because it did nothing must fail.
    run.heading("1. clear the ground")
    V.show_sd(run, "pre-clean",
              ["DELETE.FILE %s FORCE NO.QUERY" % ptr,
               "DELETE.FILE %s FORCE NO.QUERY" % wfile,
               "DELETE VOC %s" % ptr],
              cwd=acct, timeout=a.timeout)
    s = V.show_sd(run, "is the ground clear",
                  ["CT VOC %s" % ptr, "CT VOC %s" % wfile],
                  cwd=acct, timeout=a.timeout)
    V.session_ok(run, "pre-clean readback", s)
    run.note("ground is clear: no %s in VOC" % ptr,
             True, V.says(s.text, r"Record '%s' not found" % re.escape(ptr)))
    run.note("ground is clear: no %s in VOC" % wfile,
             True, V.says(s.text, r"Record '%s' not found" % re.escape(wfile)))

    sysfile_before = os.path.exists(SYSFILE)
    run.note("the system file exists BEFORE (so its survival can mean"
             " something)", True, sysfile_before)

    # ------------------------------------------- 2. queue 3 - the @SDSYS part
    run.heading("2. queue 3 - NO.QUERY on a part in the system account")
    s = V.show_sd(run, "build the @SDSYS fixture",
                  ["COPY FROM VOC SYSCOM,%s" % ptr,
                   "CT VOC %s" % ptr],
                  cwd=acct, timeout=a.timeout)
    V.session_ok(run, "fixture build", s)
    run.note("A1 fixture copied (1 record)", True,
             V.says(s.text, r"^1 record\(s\) copied\."))
    # THE FIXTURE IS DECISIVE, NOT CONTEXT.  Without a VOC record whose data
    # path starts @SDSYS, DELETE.FILE never reaches check.sdsys.file at all and
    # every row below would pass by not being tested.
    run.note("A2 fixture's data path is in the system account", True,
             V.says(s.text, r"^2: @SDSYS/SYSCOM"))

    s = V.show_sd(run, "DELETE.FILE %s NO.QUERY" % ptr,
                  ["DELETE.FILE %s NO.QUERY" % ptr],
                  cwd=acct, timeout=a.timeout)
    V.session_ok(run, "B session", s)
    run.note("B1 6145 warns that the part is in the system account",
             True, V.says(s.text, M6145))
    run.note("B2 10117: NO.QUERY took the safe branch and SAID SO",
             True, V.says(s.text, M10117))
    run.note("B3 6146 (the prompt it replaced) did NOT appear",
             True, not V.says(s.text, M6146))
    # ***B4 IS THIS FILE'S OWN FINDING.***  See the header.
    run.note("B4 6135 did NOT appear - NO.QUERY prompted for nothing",
             True, not V.says(s.text, M6135))
    run.note("B5 the session printed no BEL (a prompt at end of input rings)",
             0, s.bel)

    s = V.show_sd(run, "read the result back in a FRESH session",
                  ["CT VOC %s" % ptr],
                  cwd=acct, timeout=a.timeout)
    V.session_ok(run, "B readback", s)
    run.note("B6 the VOC reference is gone", True,
             V.says(s.text, r"Record '%s' not found" % re.escape(ptr)))
    run.note("B7 the file in the system account is STILL THERE",
             True, os.path.exists(SYSFILE))

    # ------------------------------------- 3. queue 3b - the lower-case name
    run.heading("3. queue 3b - a lower-case name is not queried about")
    s = V.show_sd(run, "CREATE.FILE %s" % wfile,
                  ["CREATE.FILE %s" % wfile],
                  cwd=acct, timeout=a.timeout)
    V.session_ok(run, "C fixture", s)
    run.note("C1 fixture created, path upper-cased as CREATE.FILE does",
             True, V.says(s.text, r"Created DATA part as %s"
                          % re.escape(wfile.upper())))

    s = V.show_sd(run, "DELETE.FILE %s NO.QUERY" % wfile,
                  ["DELETE.FILE %s NO.QUERY" % wfile],
                  cwd=acct, timeout=a.timeout)
    V.session_ok(run, "C session", s)
    run.note("C2 DATA portion deleted", True,
             V.says(s.text, M6136 % re.escape(wfile.upper())))
    run.note("C3 DICT portion deleted", True,
             V.says(s.text, M6141 % re.escape(wfile.upper() + ".DIC")))
    run.note("C4 VOC entry deleted, under the name AS TYPED", True,
             V.says(s.text, M6144 % re.escape(wfile)))
    run.note("C5 6135 did NOT appear (the DATA prompt)",
             True, not V.says(s.text, M6135))
    run.note("C6 6140 did NOT appear (the DICT prompt)",
             True, not V.says(s.text, M6140))
    run.note("C7 no BEL", 0, s.bel)

    # -------------------------------------------- 4. queue 1 - QSELECT's list
    #
    # It runs LAST and on the account's own VOC, because it needs a file with
    # records in it and every fixture above has just been deleted.  "TO 2" is
    # explicit: QSELECT's list number is optional, and an optional argument
    # left off is a prompt waiting to eat the next line.
    run.heading("4. queue 1 - QSELECT names the list it saved to")
    s = V.show_sd(run, "QSELECT VOC ... TO 2",
                  ["QSELECT VOC SYSCOM TO 2"],
                  cwd=acct, timeout=a.timeout)
    V.session_ok(run, "D session", s)
    run.note("D1 3261 was printed at all", True, V.says(s.text, M3261))
    run.note("D2 3261 ends in the list NUMBER that was asked for",
             True, V.says(s.text, M3261 + r"2$"))
    # THE DISQUALIFIER IS THE DEFECT'S OWN OUTPUT: the same message with the
    # argument missing, which matches "select list" just as well as the fix.
    run.note("D3 3261 does not end in a dangling 'select list'",
             True, not V.says(s.text, M3261 + r"\s*$"))
    run.note("D4 the count is not the null case (VOC is not empty)",
             True, V.says(s.text, r"^[1-9][0-9]* " + M3261))

    # ------------------------------------------------------------- 5. tidy up
    run.heading("5. tidy up")
    V.show_sd(run, "post-clean",
              ["DELETE.FILE %s FORCE NO.QUERY" % wfile,
               "DELETE VOC %s" % ptr,
               "DELETE.LIST 2"],
              cwd=acct, timeout=a.timeout)
    s = V.show_sd(run, "nothing of ours is left",
                  ["CT VOC %s" % ptr, "CT VOC %s" % wfile, "COUNT VOC"],
                  cwd=acct, timeout=a.timeout)
    V.session_ok(run, "post-clean readback", s)
    run.note("E1 %s gone" % ptr, True,
             V.says(s.text, r"Record '%s' not found" % re.escape(ptr)))
    run.note("E2 %s gone" % wfile, True,
             V.says(s.text, r"Record '%s' not found" % re.escape(wfile)))
    run.note("E3 the system file survived the whole run",
             True, os.path.exists(SYSFILE))

    rc = run.verdict()
    if a.allow_stale:
        run.say("  (measured with --allow-stale: the install is NOT current.)")
    return rc


if __name__ == "__main__":
    sys.exit(main())
