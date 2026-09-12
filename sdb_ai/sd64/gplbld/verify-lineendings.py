#!/usr/bin/env python3
#
# verify-lineendings.py - does READSEQ treat a CRLF as one terminator, keep a
#                         LONE CR as data, and get both right when the CRLF
#                         STRADDLES the 2048-byte buffer boundary?
#                         PORT_ADOPTION queue 22; intent from the port's
#                         gplbld/verify-lineendings.ps1.
#
#   python3 /home/don/Projects/sdcore4linux/sdb_ai/sd64/gplbld/verify-lineendings.py
#   python3 .../verify-lineendings.py --allow-stale
#
# NO SUDO.  Exit 0 / 1 / 2 as the others.
#
# ***THE STRADDLE CHECK IS THE REASON THIS IS A FILE AND NOT A ONE-LINER, AND
# IT IS THE PORT'S SENTENCE:*** every one of these readers is CHUNKED -
# `SEQ_BUFFER_SIZE` is 2048 (`op_seqio.c:67`) - so a CRLF can land with the CR
# ending one buffer and the LF starting the next.  ***A FIX THAT INSPECTS "THE
# BYTE BEFORE THE LF" IS CORRECT ON EVERY SMALL FIXTURE AND WRONG ABOUT ONCE
# PER 2 KB OF REAL DATA***, and the failure presents as stray CRs with no
# pattern.  No other check here would catch it.
#
# ***AND A LONE CR MUST SURVIVE, BECAUSE IT IS DATA AND NOT A TERMINATOR.***  A
# fix that stripped every CR would pass every other row in this file.  Fixture
# f5 puts a lone CR exactly AT the buffer boundary, which is where the
# straddle logic is holding a CR back and has to decide what it was: that is
# the subtlest case in the file and the one the two fixes can break together.
#
# ***WHAT IS DELIBERATELY NOT HERE, AND IT IS HALF THE PORT'S SCRIPT.***  The
# port also tests a DIRECTORY-FILE record written with CRLF, because on Windows
# external editors write CRLF and directory files exist to be edited by them.
# ***THIS TREE DOES NOT FOLD CR IN DIRECTORY FILES, ON PURPOSE*** -
# `op_dio3.c:1309`: *"there is nothing to fold on a bare-LF file, so that logic
# is deliberately not carried over"*.  Testing it here would assert behaviour
# the project has decided against.  ***THE ASSUMPTION IS ABOUT USERS RATHER
# THAN ABOUT THE PLATFORM*** - a Linux user can still hand a record CRLF, by an
# editor setting or by copying a file in from Windows - so it is logged in
# PROJECT_STATUS as wanting a ruling, not silently inherited.
#
# ***THE FIXTURES ARE WRITTEN BY THIS FILE, BYTE BY BYTE, AND THEN CHECKED
# BEFORE THEY ARE TRUSTED.***  No BASIC statement can place a byte at a precise
# offset, so the probe only exercises the READER.  Rows F3a/F3b/F5a read the
# bytes back off the disk and assert the CR really is the 2048th byte: ***an
# off-by-one fixture would make the straddle rows pass without testing a
# straddle at all***, which is the null case this file is most exposed to.
#
import argparse
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sdverify as V                                    # noqa: E402

NAME = "verify-lineendings"
PROBE_SRC = os.path.join(HERE, "verify-lineendings.bp")
PROBE = "ZZLE"
FIXDIR = "ZZLE"

# op_seqio.c:67.  If this ever changes, f3 and f5 stop straddling anything and
# rows F3a/F5a fail - which is the right outcome, loudly.
SEQ_BUFFER_SIZE = 2048

A = b"A" * (SEQ_BUFFER_SIZE - 1)          # 2047 bytes: CR then lands at 2047

FIXTURES = {
    # name: (bytes, what it is for)
    "f1": (b"ALPHA\r\nBETA\r\n", "CRLF, small"),
    "f2": (b"ALPHA\nBETA\n", "LF, the control"),
    "f3": (A + b"\r\nBETA\n", "CRLF straddling the buffer boundary"),
    "f4": (b"AL\rPHA\n", "a lone CR mid-line: data, not a terminator"),
    "f5": (A + b"\rB\n", "a lone CR AS the last byte of the buffer"),
    "f6": (b"a1,b1\r\na2,b2\r\n", "CSV with RFC 4180 CRLF rows"),
}


def tag(text, name):
    m = re.search(r"^%s=(.*)$" % re.escape(name), text, re.MULTILINE)
    return m.group(1).strip() if m else None


def main():
    ap = argparse.ArgumentParser(description="READSEQ and CRLF")
    ap.add_argument("--account", default=None)
    ap.add_argument("--allow-stale", action="store_true")
    ap.add_argument("--timeout", type=int, default=90)
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--probe", default=None, metavar="FILE",
                    help="a different probe source (for the RED CONTROL)")
    a = ap.parse_args()

    run = V.Run(NAME)
    probe_src = a.probe or PROBE_SRC
    user = os.environ.get("USER") or "?"
    acct = a.account or os.path.join(V.ACCOUNTS, user)
    fixdir = os.path.join(acct, FIXDIR)
    bp = os.path.join(acct, "BP")

    run.say("%s: as %s (uid %d)" % (NAME, user, os.geteuid()))
    run.say("  account    %s" % acct)
    run.say("  fixtures   %s" % fixdir)
    run.say("  probe      %s" % probe_src)
    run.say("  buffer     SEQ_BUFFER_SIZE = %d (op_seqio.c:67)" % SEQ_BUFFER_SIZE)
    if a.probe:
        run.say("  *** RED CONTROL: this is NOT the shipped probe.")
    run.say("")

    run.heading("0. preconditions")
    if V.require_not_root(
            run,
            "The probe compiles and runs in the CALLER'S own account."):
        return run.verdict()
    if V.require_paths(run, V.SD, V.SDSYS, acct, probe_src):
        return run.verdict()
    if a.allow_stale:
        run.say("  *** --allow-stale: assert-current is NOT being enforced.")
        V.require_current(run)
        run.blocked = None
    elif V.require_current(run):
        return run.verdict()
    if os.path.exists(fixdir):
        run.refuse("%s already exists" % fixdir,
                   "It is this run's fixture directory and this run has not"
                   " made it yet, so it belongs to something else.")
        return run.verdict()

    # ------------------------------------------------ 1. fixtures, byte-exact
    run.heading("1. write the fixtures, then CHECK them before trusting them")
    os.makedirs(fixdir)
    for name, (data, what) in sorted(FIXTURES.items()):
        with open(os.path.join(fixdir, name), "wb") as f:
            f.write(data)
        run.say("      %s  %5d bytes  - %s" % (name, len(data), what))

    # ***THE NULL-CASE GUARD.***  An off-by-one here would make the straddle
    # rows pass without testing a straddle.
    with open(os.path.join(fixdir, "f3"), "rb") as f:
        f3 = f.read()
    run.note("F3a f3's CR really is the LAST byte of the first buffer",
             13, f3[SEQ_BUFFER_SIZE - 1])
    run.note("F3b and its LF really is the FIRST byte of the second",
             10, f3[SEQ_BUFFER_SIZE])
    with open(os.path.join(fixdir, "f5"), "rb") as f:
        f5 = f.read()
    run.note("F5a f5's lone CR is the last byte of the first buffer",
             13, f5[SEQ_BUFFER_SIZE - 1])
    run.note("F5b and it is NOT followed by a LF (that is the point)",
             True, f5[SEQ_BUFFER_SIZE] != 10)

    # --------------------------------------------------- 2. compile the probe
    run.heading("2. compile the probe")
    os.makedirs(bp, exist_ok=True)
    shutil.copyfile(probe_src, os.path.join(bp, PROBE))
    s = V.show_sd(run, "BASIC BP %s" % PROBE, ["BASIC BP %s" % PROBE],
                  cwd=acct, timeout=a.timeout)
    V.session_ok(run, "C session", s)
    run.note("C1 compiled with 0 errors", True, V.says(s.text, r"^0 error\(s\)"))
    run.note("C2 and no error summary followed", True,
             not V.says(s.text, r"with errors in"))

    # -------------------------------------------------------- 3. run it
    run.heading("3. run the probe")
    s = V.show_sd(run, "RUN BP %s" % PROBE, ["RUN BP %s" % PROBE],
                  cwd=acct, timeout=a.timeout)
    V.session_ok(run, "P session", s)
    t = s.text
    run.note("P1 the probe started", "1", tag(t, "ZZLE.BEGIN"))
    run.note("P2 the probe RAN TO THE END", "1", tag(t, "ZZLE.END"))
    for name in sorted(FIXTURES):
        run.note("P3 %s opened" % name, None, tag(t, "%s.OPENFAIL" % name))

    # ------------------------------------------------ 4. a CRLF is ONE ending
    run.heading("4. a CRLF is one terminator, and the LF control")
    run.note("E1 f1 line 1 is 5 characters, not 6", "5", tag(t, "f1.L1.LEN"))
    run.note("E2 f1 line 1 ends in 'A' (65), not CR (13)",
             "65", tag(t, "f1.L1.LAST"))
    run.note("E3 f1 line 1 contains no CR at all", "0", tag(t, "f1.L1.CRS"))
    run.note("E4 f1 has two lines", "2", tag(t, "f1.LINES"))
    # THE CONTROL: the same content with LF endings must read identically.  If
    # f2 differed, the rows above would be measuring the reader's treatment of
    # short lines rather than of CRLF.
    run.note("E5 CONTROL f2 (LF) reads the same length", "5",
             tag(t, "f2.L1.LEN"))
    run.note("E6 CONTROL f2 ends the same way", "65", tag(t, "f2.L1.LAST"))
    run.note("E7 CONTROL f2 has two lines too", "2", tag(t, "f2.LINES"))

    # ------------------------------------------------------- 5. the STRADDLE
    run.heading("5. THE STRADDLE - a CRLF split across the buffer boundary")
    run.note("S1 f3 line 1 is %d characters, NOT %d"
             % (SEQ_BUFFER_SIZE - 1, SEQ_BUFFER_SIZE),
             str(SEQ_BUFFER_SIZE - 1), tag(t, "f3.L1.LEN"))
    run.note("S2 f3 line 1 ends in 'A' (65), not the held CR (13)",
             "65", tag(t, "f3.L1.LAST"))
    run.note("S3 f3 line 1 contains no CR", "0", tag(t, "f3.L1.CRS"))
    run.note("S4 and the line after the boundary is intact", "4",
             tag(t, "f3.L2.LEN"))
    run.note("S5 f3 has two lines", "2", tag(t, "f3.LINES"))

    # ------------------------------------------ 6. a LONE CR is DATA
    run.heading("6. a lone CR is DATA - including at the boundary")
    run.note("D1 f4 keeps its mid-line CR (6 characters)", "6",
             tag(t, "f4.L1.LEN"))
    run.note("D2 f4 line 1 contains exactly one CR", "1", tag(t, "f4.L1.CRS"))
    run.note("D3 f4 is ONE line - the CR did not end it", "1",
             tag(t, "f4.LINES"))
    # ***THE SUBTLEST ROW IN THE FILE.***  The reader is holding this CR back
    # across the buffer boundary precisely because it might have been half of a
    # CRLF.  It was not, so it has to come back as data.
    run.note("D4 f5's boundary CR survived as data (%d characters)"
             % (SEQ_BUFFER_SIZE + 1), str(SEQ_BUFFER_SIZE + 1),
             tag(t, "f5.L1.LEN"))
    run.note("D5 f5 line 1 ends in 'B' (66) - the byte after the CR",
             "66", tag(t, "f5.L1.LAST"))
    run.note("D6 f5 line 1 contains exactly one CR", "1", tag(t, "f5.L1.CRS"))
    run.note("D7 f5 is ONE line", "1", tag(t, "f5.LINES"))

    # ------------------------------------------------------------ 7. READCSV
    run.heading("7. READCSV inherits it - the LAST field is where a CR lands")
    run.note("V1 f6 row 1 first field is 2 characters", "2",
             tag(t, "f6.R1.F1.LEN"))
    run.note("V2 f6 row 1 LAST field is 2 characters, not 3", "2",
             tag(t, "f6.R1.LASTFIELD.LEN"))
    run.note("V3 f6 row 1 last field ends in '1' (49), not CR (13)",
             "49", tag(t, "f6.R1.LASTFIELD.LAST"))
    run.note("V4 f6 row 2 last field is clean too", "2",
             tag(t, "f6.R2.LASTFIELD.LEN"))
    run.note("V5 f6 has two rows", "2", tag(t, "f6.ROWS"))

    # ----------------------------------------------------------- 8. tidy up
    if a.keep:
        run.heading("8. --keep: fixtures left behind")
    else:
        run.heading("8. tidy up")
        V.show_sd(run, "post-clean", ["DELETE VOC BP.OUT"],
                  cwd=acct, timeout=a.timeout)
        shutil.rmtree(fixdir, ignore_errors=True)
        for p in (os.path.join(bp, PROBE), os.path.join(acct, "BP.OUT")):
            if os.path.isdir(p):
                shutil.rmtree(p, ignore_errors=True)
            elif os.path.exists(p):
                os.remove(p)
        run.note("Z1 the fixture directory is gone", False,
                 os.path.exists(fixdir))
        run.note("Z2 the probe source is gone", False,
                 os.path.exists(os.path.join(bp, PROBE)))

    rc = run.verdict()
    run.say("")
    run.say("  NOT COVERED, deliberately: a DIRECTORY-FILE record written with")
    run.say("  CRLF.  This tree does not fold CR there (op_dio3.c:1309) and")
    run.say("  that is a decision, not an omission - but it assumes no Linux")
    run.say("  user hands a record CRLF, which is an assumption about users.")
    run.say("  PROJECT_STATUS logs it as wanting a ruling.")
    if a.allow_stale:
        run.say("  (measured with --allow-stale: the install is NOT current.)")
    return rc


if __name__ == "__main__":
    sys.exit(main())
