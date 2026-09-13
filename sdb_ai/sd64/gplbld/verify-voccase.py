#!/usr/bin/env python3
#
# verify-voccase.py - does the case migration move exactly the records it
#                     should, and refuse the ones it must?  Plan section M2;
#                     GPL.BP/voccase, catalogued !voccase, called by LOGIN's
#                     update.voc before it copies NEWVOC into an account.
#
#   python3 /home/don/Projects/sdcore4linux/sdb_ai/sd64/gplbld/verify-voccase.py
#   python3 .../verify-voccase.py --allow-stale       measure a stale install
#
# NO SUDO.  Exit 0 every decisive check passed, 1 a decisive check failed,
# 2 the test could not be run.
#
# ***WHY FIXTURE FILES AND NOT A REAL VOC.***  The routine only acts on an id
# whose LOWER-case form SD ships, and until section M3 renames something SD
# ships nothing in lower case - so on a real account it is inert, and a test of
# it there passes by doing nothing.  The shipped NEWVOC cannot be given a
# lower-case record without root.  So the probe builds three ordinary files
# standing in for an account VOC, NEWVOC and VOC_TEMPLATE, and calls the
# catalogued routine on them exactly as update.voc does.
#
# WHAT THIS DOES NOT WITNESS: update.voc's CALL of it and its two messages
# (10916, 10917).  Those need a shipped lower-case id and an account that
# predates it - the first M3 rename on a keep-accounts cycle.
#
# ***EVERY RULE HAS A ROW, AND THE ONES THAT MUST NOT MOVE ARE DECISIVE TOO***
# - a migration that renamed everything would pass every "moved" row:
#   LIST -> list            shipped in NEWVOC: moved, content unchanged
#   $HOLD -> $hold          moved WITH its [locked] marker
#   ADMIN.VERB              shipped only in VOC_TEMPLATE: moved
#   MYPARA                  the account's own name: untouched
#   COUNT                   a system name not yet shipped lower: untouched
#   SORT + sort, different  REFUSED: both kept, SORT named in collided
#   SELECT + select, same   no choice to make: upper deleted, counted moved
#   lower                   already lower: untouched
# and a second call moves nothing and refuses SORT again (idempotent).
#
import argparse
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sdverify as V                                    # noqa: E402

NAME = "verify-voccase"
PROBE_SRC = os.path.join(HERE, "verify-voccase.bp")
PROBE = "ZZVCASE"
FILES = ["zzvcv", "zzvcn", "zzvct"]


def tag(text, name):
    """The value of a TAG=value line, or None if the tag never appeared."""
    m = re.search(r"^%s=(.*)$" % re.escape(name), text, re.MULTILINE)
    return m.group(1).strip() if m else None


def idset(value):
    return None if value is None else sorted(value.split())


def main():
    ap = argparse.ArgumentParser(description="the plan M2 case migration")
    ap.add_argument("--account", default=None, help="account directory")
    ap.add_argument("--allow-stale", action="store_true",
                    help="measure an install assert-current calls stale")
    ap.add_argument("--timeout", type=int, default=60,
                    help="seconds per sd session (default 60)")
    a = ap.parse_args()

    run = V.Run(NAME)
    user = os.environ.get("USER") or "?"
    acct = a.account or os.path.join(V.ACCOUNTS, user)
    bp = os.path.join(acct, "BP")
    bpout = os.path.join(acct, "BP.OUT")

    run.say("%s: as %s (uid %d), NOT elevated" % (NAME, user, os.geteuid()))
    run.say("  sd        %s" % V.SD)
    run.say("  account   %s" % acct)
    run.say("  probe     %s  ->  %s" % (PROBE_SRC, os.path.join(bp, PROBE)))
    run.say("  fixtures  %s (account VOC, NEWVOC, VOC_TEMPLATE stand-ins)"
            % ", ".join(FILES))
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
        V.require_current(run)
        run.blocked = None
    elif V.require_current(run):
        return run.verdict()

    run.heading("1. the ground is clear")
    names = FILES + [f.upper() for f in FILES]
    s = V.show_sd(run, "readback", ["CT VOC %s" % " ".join(names)],
                  cwd=acct, timeout=a.timeout)
    V.session_ok(run, "G session", s)
    for n in names:
        if not V.says(s.text, r"^Record '%s' not found$" % re.escape(n)):
            run.refuse("VOC %s already exists" % n,
                       "It is this run's fixture name, so it belongs to"
                       " something else.")
            return run.verdict()
    for p in [os.path.join(bp, PROBE)] + [os.path.join(acct, f.upper())
                                          for f in FILES]:
        if os.path.exists(p):
            run.refuse("%s already exists" % p)
            return run.verdict()
    bpout_before = os.path.exists(bpout)
    run.say("  BP.OUT existed before this run: %s" % bpout_before)

    run.heading("2. fixture files and the probe")
    os.makedirs(bp, exist_ok=True)
    shutil.copyfile(PROBE_SRC, os.path.join(bp, PROBE))
    run.say("  staged %s" % os.path.join(bp, PROBE))
    s = V.show_sd(run, "create the files and compile",
                  ["CREATE.FILE %s" % f for f in FILES] + ["BASIC BP %s" % PROBE],
                  cwd=acct, timeout=a.timeout)
    V.session_ok(run, "F session", s)
    for f in FILES:
        run.note("F1 %s created" % f, True,
                 V.says(s.text, r"^Created DATA part as %s$" % f.upper()))
    run.note("F2 the probe compiled with 0 errors", True,
             V.says(s.text, r"^0 error\(s\)"))
    run.note("F3 and no error summary followed it", True,
             not V.says(s.text, r"with errors in"))

    run.heading("3. run the probe")
    s = V.show_sd(run, "RUN BP %s" % PROBE, ["RUN BP %s" % PROBE],
                  cwd=acct, timeout=a.timeout)
    V.session_ok(run, "P session", s)
    t = s.text
    run.note("P1 the probe started", "1", tag(t, "ZZVCASE.BEGIN"))
    run.note("P2 its fixtures were written", "1", tag(t, "FIXTURES"))
    run.note("P3 it RAN TO THE END (so !voccase was found and returned)",
             "1", tag(t, "ZZVCASE.END"))
    run.note("P4 no fixture file failed to open", None, tag(t, "ZZVCASE.FATAL"))

    def rec(i):
        return tag(t, "REC." + i)

    run.heading("4. the first call - what moved and what was refused")
    run.note("M1 moved exactly $hold, admin.verb, list, select",
             ["$hold", "admin.verb", "list", "select"], idset(tag(t, "MOVED")))
    run.note("M2 refused exactly SORT", ["SORT"], idset(tag(t, "COLLIDED")))

    run.heading("5. the account VOC afterwards, record by record")
    run.note("R1 list holds LIST's content, unchanged", "PA|LIST ONE", rec("list"))
    run.note("R2 LIST is gone", "ABSENT", rec("LIST"))
    run.note("R3 $hold holds $HOLD's content WITH its [locked] marker",
             "F [locked]|MINE", rec("$hold"))
    run.note("R4 $HOLD is gone", "ABSENT", rec("$HOLD"))
    run.note("R5 admin.verb moved (shipped only in VOC_TEMPLATE)", "V|x",
             rec("admin.verb"))
    run.note("R6 ADMIN.VERB is gone", "ABSENT", rec("ADMIN.VERB"))
    run.note("R7 MYPARA, the account's own name, is untouched", "PA|mine",
             rec("MYPARA"))
    run.note("R8 and no mypara was made", "ABSENT", rec("mypara"))
    run.note("R9 COUNT, not shipped lower, is untouched", "V|c", rec("COUNT"))
    run.note("R10 and no count was made", "ABSENT", rec("count"))
    run.note("R11 the refused twin: SORT kept as it was", "V|upper", rec("SORT"))
    run.note("R12 the refused twin: sort kept as it was", "V|lower", rec("sort"))
    run.note("R13 the identical twin: SELECT deleted", "ABSENT", rec("SELECT"))
    run.note("R14 the identical twin: select kept", "X|same", rec("select"))
    run.note("R15 an id already lower is untouched", "PA|already", rec("lower"))

    run.heading("6. the second call - idempotent")
    run.note("I1 moves nothing", [], idset(tag(t, "MOVED2")))
    run.note("I2 refuses SORT again", ["SORT"], idset(tag(t, "COLLIDED2")))

    run.heading("7. tidy up")
    V.show_sd(run, "post-clean",
              ["DELETE.FILE %s FORCE NO.QUERY" % f for f in FILES],
              cwd=acct, timeout=a.timeout)
    p = os.path.join(bp, PROBE)
    if os.path.exists(p):
        os.remove(p)
    if not bpout_before:
        V.show_sd(run, "BP.OUT was made by this run", ["DELETE VOC BP.OUT"],
                  cwd=acct, timeout=a.timeout)
        shutil.rmtree(bpout, ignore_errors=True)
    elif os.path.exists(os.path.join(bpout, PROBE)):
        os.remove(os.path.join(bpout, PROBE))
    s = V.show_sd(run, "nothing of ours is left",
                  ["CT VOC %s" % " ".join(FILES)], cwd=acct, timeout=a.timeout)
    V.session_ok(run, "cleanup readback", s)
    run.note("Z1 no fixture is left in the VOC", len(FILES),
             V.say_count(s.text, r"^Record 'zzvc[vnt]' not found$"))
    run.note("Z2 no fixture file is left on disk", [],
             [f for f in FILES if os.path.exists(os.path.join(acct, f.upper()))])

    rc = run.verdict()
    if a.allow_stale:
        run.say("  (measured with --allow-stale: the install is NOT current.)")
    return rc


if __name__ == "__main__":
    sys.exit(main())
