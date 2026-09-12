#!/usr/bin/env python3
#
# verify-txn.py - does COMMIT end the transaction it commits, does a NESTED
#                 commit keep the outer transaction's writes, and does a
#                 directory file's record id get MAPPED inside a transaction?
#                 PORT_ADOPTION queue 22; intent from the port's verify-txn.ps1.
#
#   python3 /home/don/Projects/sdcore4linux/sdb_ai/sd64/gplbld/verify-txn.py
#   python3 .../verify-txn.py --allow-stale       measure a stale install
#
# NO SUDO.  Exit 0 every decisive check passed, 1 a decisive check failed,
# 2 the test could not be run.
#
# ***WHY IT EXISTS, IN THE PORT'S WORDS: PART OF A TRANSACTION LANDING AND PART
# NOT IS THE ONE OUTCOME A TRANSACTION EXISTS TO PREVENT, AND NOTHING REPORTED
# IT*** - not an error, not a status, not a log line.  A silent data-loss
# regression is exactly the kind that comes back unnoticed, so it belongs in a
# standing suite rather than in a probe somebody remembers to run.
#
# THREE QUESTIONS, AND THE THIRD IS THE ONE THAT NEEDS TWO INSTRUMENTS.
#
#   1. SYSTEM(1008) after COMMIT.  op_txnbgn() incremented the level and
#      op_txncmt() decremented nothing, so the level climbed for ever and a
#      program could not ask "am I in a transaction".  Row T3 is the check;
#      T1 and T2 are what stop T3 being a zero that was never anything else.
#   2. A nested commit must not orphan the OUTER transaction's cache.  Row T7
#      is the data-loss row: S2 is written by the outer transaction BEFORE the
#      inner one runs, so it is exactly the write that went missing.
#   3. A directory file's record id becomes a FILENAME and is mapped -
#      "*,=><%/+:;?\\\"" -> "ACEGLPSVXYZBQ" (sd.h:113-114), so "," is "%C".
#      op_txncmt() handed the RAW id to dir_write() and to the delete path, so
#      a WRITE inside a transaction created a file the matching READ could
#      never find, and a DELETE removed a path that had never existed,
#      tolerated the ENOENT and reported success.
#
# ***SECTION 3 NEEDS BOTH INSTRUMENTS BECAUSE EITHER ALONE CAN BE SATISFIED BY
# THE WRONG THING.***  What SD reads back and what is actually on disk have to
# agree: a raw-id write followed by a raw-id read would satisfy SD, and a file
# of the right name with the wrong content would satisfy the directory listing.
# Rows D1-D3 are SD's answer; rows E1-E6 are the filesystem's.
#
# ***AND ON LINUX THE WHOLE CLASS IS SILENT, WHICH IS WORSE THAN IN THE PORT.***
# The port chose ids that are legal Windows filenames in BOTH forms so that the
# failure would be silent rather than loud - ">" and "*" are illegal there and
# would have failed noisily, proving nothing about the silent case.  Here every
# one of the thirteen characters is a legal Linux filename character, so an
# unmapped write ALWAYS succeeds under the wrong name.  Rows E4-E6 are what
# catch that: they assert the RAW-id files are absent, which is the only sign
# an unmapped write leaves on this platform.
#
# RUN IT UNELEVATED, and that is not a preference.  The probe is compiled and
# run in the CALLER'S OWN account; a root session lands in SDSYS instead, where
# the probe is not, so it would measure the wrong account or nothing at all.
#
# NOT INSTALLED AND NOT SHIPPED.  verify-txn.bp lives next to this file and is
# staged into the account's BP only for the run.
#
import argparse
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sdverify as V                                    # noqa: E402

NAME = "verify-txn"
PROBE_SRC = os.path.join(HERE, "verify-txn.bp")
PROBE = "ZZTXN"
DIRF = "zztxnd"

# id -> the filename map_dir_ids must produce (sd.h:113-114).
IDMAP = {",": "%C", "=": "%E", ";": "%Y"}


def tag(text, name):
    """The value of a TAG=value line, or None if the tag never appeared.

    None is not the empty string and the callers never conflate them: a tag
    that is absent means the probe did not reach that line, which is a
    different fact from a line that printed nothing."""
    m = re.search(r"^%s=(.*)$" % re.escape(name), text, re.MULTILINE)
    return m.group(1).strip() if m else None


def main():
    ap = argparse.ArgumentParser(description="transaction behaviour under SD")
    ap.add_argument("--account", default=None, help="account directory")
    ap.add_argument("--allow-stale", action="store_true",
                    help="measure an install assert-current calls stale")
    ap.add_argument("--timeout", type=int, default=90,
                    help="seconds per sd session (default 90)")
    ap.add_argument("--keep", action="store_true",
                    help="leave the fixtures behind for inspection")
    # ***THIS EXISTS FOR THE RED CONTROL AND SAYS SO.***  A suite that has
    # never been seen to FAIL is not evidence that the system is right, only
    # that the suite is quiet.  Pointing it at a deliberately broken probe is
    # how this file is shown to go red; the run announces the substitution so
    # a red-control transcript can never be mistaken for a real one.
    ap.add_argument("--probe", default=None, metavar="FILE",
                    help="use a different probe source (for the RED CONTROL)")
    a = ap.parse_args()

    run = V.Run(NAME)
    probe_src = a.probe or PROBE_SRC
    user = os.environ.get("USER") or "?"
    acct = a.account or os.path.join(V.ACCOUNTS, user)
    dirpath = os.path.join(acct, DIRF.upper())
    bp = os.path.join(acct, "BP")

    run.say("%s: as %s (uid %d), NOT elevated" % (NAME, user, os.geteuid()))
    run.say("  sd        %s" % V.SD)
    run.say("  account   %s" % acct)
    run.say("  probe     %s  ->  %s" % (probe_src, os.path.join(bp, PROBE)))
    run.say("  dirfile   %s" % dirpath)
    if a.probe:
        run.say("")
        run.say("  *** RED CONTROL: this is NOT the shipped probe.")
        run.say("  *** Rows below describe %s, not verify-txn.bp." % a.probe)
    run.say("")

    run.heading("0. preconditions")
    if V.require_not_root(
            run,
            "The probe is compiled and run in the CALLER'S own account; a root"
            " session lands in SDSYS, where the probe is not."):
        return run.verdict()
    if V.require_paths(run, V.SD, V.SDSYS, acct, probe_src):
        return run.verdict()
    if a.allow_stale:
        run.say("  *** --allow-stale: assert-current is NOT being enforced.")
        V.require_current(run)
        run.blocked = None
    elif V.require_current(run):
        return run.verdict()

    # ***REFUSE IF THE GROUND IS NOT CLEAR.***  Every record read back below is
    # written by this run.  A surviving ZZTXND belongs to something else, and
    # every row after it would describe records this file did not write.
    if os.path.exists(dirpath):
        run.refuse("%s already exists" % dirpath,
                   "It is this run's fixture and this run has not made it yet,"
                   " so it belongs to something else.",
                   "Remove it (and DELETE VOC %s) and run again." % DIRF)
        return run.verdict()

    # ------------------------------------------------------------- 1. fixture
    run.heading("1. build the fixture and compile the probe")
    os.makedirs(bp, exist_ok=True)
    shutil.copyfile(probe_src, os.path.join(bp, PROBE))
    run.say("  staged %s" % os.path.join(bp, PROBE))

    s = V.show_sd(run, "create the directory file and compile",
                  ["CREATE.FILE %s DIRECTORY" % DIRF,
                   "BASIC BP %s" % PROBE],
                  cwd=acct, timeout=a.timeout)
    V.session_ok(run, "F session", s)
    run.note("F1 the directory file was created", True,
             V.says(s.text, r"Created DATA part as %s" % DIRF.upper()))
    # ANCHOR ON THE COUNT, NOT ON THE WORD "Compiled".  "Compiled 1 program(s)
    # with errors in:" contains "Compiled" too.
    run.note("F2 the probe compiled with 0 errors", True,
             V.says(s.text, r"^0 error\(s\)"))
    run.note("F3 and no error summary followed it", True,
             not V.says(s.text, r"with errors in"))

    # --------------------------------------------------------------- 2. probe
    run.heading("2. run the probe")
    s = V.show_sd(run, "RUN BP %s" % PROBE, ["RUN BP %s" % PROBE],
                  cwd=acct, timeout=a.timeout)
    V.session_ok(run, "P session", s)
    t = s.text

    # ***THE NULL-CASE GUARD.***  Every row below reads a tag, and a tag that
    # never printed reads as None.  If the probe faulted after section 1 the
    # later rows would each fail for their own reason and the transcript would
    # be read as three separate defects; P1/P2 say plainly that it did not
    # finish.
    run.note("P1 the probe started", "1", tag(t, "ZZTXN.BEGIN"))
    run.note("P2 the probe RAN TO THE END (no fault part way)",
             "1", tag(t, "ZZTXN.END"))
    run.note("P3 it did not fail to open the directory file",
             None, tag(t, "ZZTXN.FATAL"))

    run.heading("3. does COMMIT end the transaction it commits?")
    run.note("T1 level is 0 before any transaction", "0", tag(t, "L0"))
    run.note("T2 level is 1 inside one (so T3 is not a zero that never moved)",
             "1", tag(t, "L1"))
    run.note("T3 level is 0 again AFTER COMMIT", "0", tag(t, "L2"))
    run.note("T4 and the committed record reads back", "one", tag(t, "S1"))

    run.heading("4. does a NESTED commit keep the outer transaction's writes?")
    run.note("T5 after the inner COMMIT the OUTER is still open (level 1)",
             "1", tag(t, "L3"))
    run.note("T6 level is 0 after the outer COMMIT", "0", tag(t, "L4"))
    # ***T7 IS THE DATA-LOSS ROW.***
    run.note("T7 the OUTER transaction's write survived the inner commit",
             "two", tag(t, "S2"))
    run.note("T8 the inner transaction's write landed too",
             "three", tag(t, "S3"))

    run.heading("5. directory-file ids inside a transaction - SD's answer")
    run.note("D0 level is 0 after section 3's commit", "0", tag(t, "L5"))
    run.note("D1 control: the id written OUTSIDE a transaction reads back",
             "ctl", tag(t, "CTL"))
    run.note("D2 the id written INSIDE a transaction reads back",
             "wrt", tag(t, "WRT"))
    run.note("D3 the id deleted INSIDE a transaction is gone",
             "NOTFOUND", tag(t, "DEL"))

    # ------------------------------------------- 6. the SECOND instrument
    run.heading("6. the same three ids - what is actually ON DISK")
    try:
        onset = set(os.listdir(dirpath))
    except OSError as e:
        run.refuse("cannot list %s (%s)" % (dirpath, e))
        return run.verdict()
    run.say("  %s contains: %s" % (dirpath, sorted(onset)))

    run.note("E1 the transaction's write is the MAPPED name %s" % IDMAP[","],
             True, IDMAP[","] in onset)
    run.note("E2 the control's mapped name %s is there too" % IDMAP["="],
             True, IDMAP["="] in onset)
    run.note("E3 the deleted record's mapped name %s is GONE" % IDMAP[";"],
             True, IDMAP[";"] not in onset)
    # E4-E6: the only sign an unmapped write leaves on Linux, where every one
    # of those characters is a legal filename character.
    run.note("E4 no RAW ',' file was created", True, "," not in onset)
    run.note("E5 no RAW ';' file was left behind", True, ";" not in onset)
    run.note("E6 no RAW '=' file was created", True, "=" not in onset)

    # ------------------------------------------------------------ 7. tidy up
    if a.keep:
        run.heading("7. --keep: fixtures left behind")
        run.say("  %s and BP/%s are still there." % (dirpath, PROBE))
    else:
        run.heading("7. tidy up")
        V.show_sd(run, "post-clean",
                  ["DELETE.FILE %s FORCE NO.QUERY" % DIRF,
                   "DELETE VOC BP.OUT"],
                  cwd=acct, timeout=a.timeout)
        for p in (os.path.join(bp, PROBE), os.path.join(acct, "BP.OUT")):
            if os.path.isdir(p):
                shutil.rmtree(p, ignore_errors=True)
            elif os.path.exists(p):
                os.remove(p)
        s = V.show_sd(run, "nothing of ours is left",
                      ["CT VOC %s" % DIRF, "COUNT VOC"],
                      cwd=acct, timeout=a.timeout)
        V.session_ok(run, "cleanup readback", s)
        run.note("Z1 the VOC entry is gone", True,
                 V.says(s.text, r"Record '%s' not found" % re.escape(DIRF)))
        run.note("Z2 the directory is gone from disk", False,
                 os.path.exists(dirpath))

    return run.verdict()


if __name__ == "__main__":
    sys.exit(main())
