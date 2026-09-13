#!/usr/bin/env python3
#
# verify-lcnames.py - the lower-case renames, category by category (plan
#                     section M3), and the migration that carries an existing
#                     account across each one (section M2).  Intent from the
#                     port's verify-lcnames.ps1; the migration half is Linux's
#                     own, because on NTFS the port had nothing to migrate.
#
#   python3 /home/don/Projects/sdcore4linux/sdb_ai/sd64/gplbld/verify-lcnames.py
#   python3 .../verify-lcnames.py --allow-stale       measure a stale install
#
# NO SUDO.  Exit 0 every decisive check passed, 1 a decisive check failed,
# 2 the test could not be run.
#
# CATEGORIES COVERED: $savedlists (the saved-list VOC id; on disk it is still
# $SVLISTS).  Add a section per category as M3 renames it.
#
# ***"NOT FOUND" CANNOT TEST A RENAME*** - the port's lesson (its 65c681f):
# CT folds the record id, so CT VOC $SAVEDLISTS finds $savedlists either way.
# Two instruments instead: CT's heading echoes the id it MATCHED, and the
# probe's exact READ says which spelling is on disk.
#
# THE MIGRATION IS RUN FOR REAL, ON THE CALLER'S OWN VOC.  The probe moves the
# id back to $SAVEDLISTS - an account from before the rename - and the real
# UPDATE.ACCOUNTS (mode 2, own account, no sudo) must move it forward again and
# say so (10916).  WHATEVER HAPPENS, the last step moves it forward if it is
# still upper case, and the final exact read is decisive, so a failure part way
# cannot leave the account behind unreported.
#
import argparse
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sdverify as V                                    # noqa: E402

NAME = "verify-lcnames"
PROBE_SRC = os.path.join(HERE, "verify-lcnames.bp")
PROBE = "ZZLCN"
LIST = "zzlcl"

M10916 = r"^1 VOC record\(s\) were renamed to the lower-case name SD now uses: \$savedlists$"
M10917 = r"under BOTH an upper-case and a lower-case name"
SAVED = r"^2 records saved to select list 'zzlcl'$"
GOT = r"^2 record\(s\) selected to select list 0$"
FAULT = r"^[0-9A-F]{8}: "


def tag(text, name):
    m = re.search(r"^%s=(.*)$" % re.escape(name), text, re.MULTILINE)
    return m.group(1).strip() if m else None


def main():
    ap = argparse.ArgumentParser(description="plan M3 renames and their migration")
    ap.add_argument("--account", default=None, help="account directory")
    ap.add_argument("--allow-stale", action="store_true",
                    help="measure an install assert-current calls stale")
    ap.add_argument("--timeout", type=int, default=90,
                    help="seconds per sd session (default 90)")
    a = ap.parse_args()

    run = V.Run(NAME)
    user = os.environ.get("USER") or "?"
    acct = a.account or os.path.join(V.ACCOUNTS, user)
    bp = os.path.join(acct, "BP")
    bpout = os.path.join(acct, "BP.OUT")

    run.say("%s: as %s (uid %d), NOT elevated" % (NAME, user, os.geteuid()))
    run.say("  sd        %s" % V.SD)
    run.say("  sdsys     %s" % V.SDSYS)
    run.say("  account   %s" % acct)
    run.say("  probe     %s  ->  %s" % (PROBE_SRC, os.path.join(bp, PROBE)))
    run.say("")

    run.heading("0. preconditions")
    if V.require_not_root(run, "Every check is about the caller's own account."):
        return run.verdict()
    if V.require_paths(run, V.SD, V.SDSYS, acct, PROBE_SRC):
        return run.verdict()
    if a.allow_stale:
        run.say("  *** --allow-stale: assert-current is NOT being enforced.")
        V.require_current(run)
        run.blocked = None
    elif V.require_current(run):
        return run.verdict()
    if V.require_running(run, acct):
        return run.verdict()

    def sd(title, cmds, timeout=None):
        s = V.show_sd(run, title, cmds, cwd=acct, timeout=timeout or a.timeout)
        V.session_ok(run, title, s)
        return s

    def probe(mode):
        s = sd("RUN BP %s %s" % (PROBE, mode), ["RUN BP %s %s" % (PROBE, mode)])
        return s.text

    # ---------------------------------------------------- 1. the installed source
    run.heading("1. what was installed (static, the installed tree)")
    gplbp = os.path.join(V.SDSYS, "GPL.BP")
    literal = re.compile(r"""["']\$SAVEDLISTS["']""")
    hits = []
    for fn in sorted(os.listdir(gplbp)):
        p = os.path.join(gplbp, fn)
        if os.path.isfile(p):
            with open(p, errors="replace") as f:
                for i, line in enumerate(f, 1):
                    code = line.split(";*")[0]
                    if not line.lstrip().startswith("*") and literal.search(code):
                        hits.append("%s:%d" % (fn, i))
    run.say("  scanned %d GPL.BP records" % len(os.listdir(gplbp)))
    run.note("S1 no quoted '$SAVEDLISTS' literal left in installed GPL.BP code",
             [], hits)
    for d in ("NEWVOC", "VOC_TEMPLATE"):
        p = os.path.join(V.SDSYS, d, "EDIT.LIST")
        txt = open(p, errors="replace").read() if os.path.exists(p) else ""
        run.note("S2 %s/EDIT.LIST edits $savedlists" % d, True,
                 "ED $savedlists" in txt)

    # voccase's created.ids must equal the lower-case ids CREATEA writes.
    def quoted(path, pattern):
        src = open(path, errors="replace").read()
        out = set()
        for m in re.finditer(pattern, src, re.MULTILINE):
            out.update(re.findall(r"'([^']*)'", m.group(0)))
        return out
    createa = quoted(os.path.join(gplbp, "CREATEA"),
                     r"^\s*fn = '[^']*'|^\s*write 'X' to voc\.f, '[^']*'")
    created_lower = sorted(i for i in createa if i == i.lower())
    voc_ids = sorted(quoted(os.path.join(gplbp, "voccase"),
                            r"^\s*created\.ids = .*$"))
    run.say("  CREATEA writes: %s" % sorted(createa))
    run.note("S3 CREATEA's ids were read (not the null case)", True, len(createa) >= 4)
    run.note("S4 voccase's created.ids == the lower-case ids CREATEA writes",
             created_lower, voc_ids)
    # S4 ALONE PASSES AS [] == [] on an install from before any rename - watched
    # doing exactly that on d79ae15.  From this category on the list cannot be
    # empty, so an empty one is a failure, not agreement.
    run.note("S5 and that list is not empty (S4 compared something)",
             True, len(created_lower) > 0)

    # ---------------------------------------------------------------- 2. ground
    run.heading("2. ground and probe")
    if os.path.exists(os.path.join(bp, PROBE)):
        run.refuse("%s already exists" % os.path.join(bp, PROBE))
        return run.verdict()
    s = V.show_sd(run, "no list of ours exists", ["GET.LIST %s" % LIST],
                  cwd=acct, timeout=a.timeout)
    if not V.session_ok(run, "ground session", s):
        run.refuse("the ground-check session did not run")
        return run.verdict()
    if not V.says(s.text, r"^Saved select list '%s' not found$" % LIST):
        run.refuse("saved list %s already exists" % LIST)
        return run.verdict()
    bpout_before = os.path.exists(bpout)
    os.makedirs(bp, exist_ok=True)
    shutil.copyfile(PROBE_SRC, os.path.join(bp, PROBE))
    s = sd("compile", ["BASIC BP %s" % PROBE])
    run.note("F1 the probe compiled with 0 errors", True, V.says(s.text, r"^0 error\(s\)"))

    # ***THE RESTORE UNDOES ONLY WHAT THIS RUN DID.***  On an install from before
    # the rename the account starts on $SAVEDLISTS, and a restore that "moved it
    # forward" there would change the account instead of measuring it.
    down = False
    baseline = (None, None)
    try:
        # ------------------------------------------------ 3. a new account
        run.heading("3. an account made by this install holds the NEW id")
        t = probe("READ")
        baseline = (tag(t, "EXACT.LOWER"), tag(t, "EXACT.UPPER"))
        run.say("  baseline (lower, upper) = %s" % (baseline,))
        run.note("A1 probe ran", "1", tag(t, "ZZLCN.END"))
        run.note("A2 $savedlists exists, exactly", "Y", tag(t, "EXACT.LOWER"))
        run.note("A3 $SAVEDLISTS does not", "N", tag(t, "EXACT.UPPER"))

        s = sd("the lists work, and CT names the id it matched",
               ["SELECT VOC SAMPLE 2", "SAVE.LIST %s" % LIST,
                "GET.LIST %s" % LIST, "CLEARSELECT", "CT VOC $SAVEDLISTS"])
        run.note("L1 SAVE.LIST saved 2", True, V.says(s.text, SAVED))
        run.note("L2 GET.LIST got 2", True, V.says(s.text, GOT))
        run.note("L3 CT VOC $SAVEDLISTS answers with the id it matched, $savedlists",
                 True, V.says(s.text, r"^VOC \$savedlists$"))
        run.note("L4 no runtime fault", False, V.says(s.text, FAULT))

        # ---------------------------------------- 4. an account from before
        run.heading("4. an account from BEFORE the rename (moved back by the probe)")
        t = probe("DOWN")
        down = tag(t, "DOWN") == "1"
        run.note("B1 the id was moved back to $SAVEDLISTS", "1", tag(t, "DOWN"))
        run.note("B2 exactly $SAVEDLISTS now", ("N", "Y"),
                 (tag(t, "EXACT.LOWER"), tag(t, "EXACT.UPPER")))
        s = sd("the lists still work through the fold",
               ["GET.LIST %s" % LIST, "CLEARSELECT", "CT VOC $savedlists"])
        run.note("B3 GET.LIST still got 2 (the literal $savedlists folds UP)",
                 True, V.says(s.text, GOT))
        run.note("B4 control: CT VOC $savedlists now answers $SAVEDLISTS", True,
                 V.says(s.text, r"^VOC \$SAVEDLISTS$"))

        # ----------------------------------------------- 5. the migration
        run.heading("5. the real update.voc carries it across")
        if not down:
            run.note("U0 section 4 moved the id back (else this measures nothing)",
                     True, False)
        s = sd("UPDATE.ACCOUNTS (own account)", ["UPDATE.ACCOUNTS"], timeout=180)
        run.note("U1 10916 names exactly $savedlists", True, V.says(s.text, M10916))
        run.note("U2 no both-spellings refusal (10917)", False, V.says(s.text, M10917))
        run.note("U3 no runtime fault", False, V.says(s.text, FAULT))
        t = probe("READ")
        run.note("U4 exactly $savedlists again", ("Y", "N"),
                 (tag(t, "EXACT.LOWER"), tag(t, "EXACT.UPPER")))
        s = sd("the saved list survived", ["GET.LIST %s" % LIST, "CLEARSELECT"])
        run.note("U5 GET.LIST still got 2 (the move is the VOC id only)",
                 True, V.says(s.text, GOT))
    finally:
        # ----------------------------------------------------- 6. restore
        run.heading("6. restore and tidy (always runs)")
        if down:
            t = probe("UP")
            run.say("  UP=%s" % tag(t, "UP"))
        else:
            run.say("  this run did not move the id, so it does not move it back")
            t = probe("READ")
        run.note("Z1 the account ends exactly as it started (lower, upper)",
                 baseline, (tag(t, "EXACT.LOWER"), tag(t, "EXACT.UPPER")))
        s = sd("delete the list", ["DELETE.LIST %s" % LIST])
        run.note("Z2 the saved list is gone", True,
                 V.says(s.text, r"^Deleted saved select list '%s'$" % LIST))
        p = os.path.join(bp, PROBE)
        if os.path.exists(p):
            os.remove(p)
        if not bpout_before:
            V.show_sd(run, "BP.OUT was made by this run", ["DELETE VOC BP.OUT"],
                      cwd=acct, timeout=a.timeout)
            shutil.rmtree(bpout, ignore_errors=True)
        elif os.path.exists(os.path.join(bpout, PROBE)):
            os.remove(os.path.join(bpout, PROBE))

    rc = run.verdict()
    if a.allow_stale:
        run.say("  (measured with --allow-stale: the install is NOT current.)")
    return rc


if __name__ == "__main__":
    sys.exit(main())
