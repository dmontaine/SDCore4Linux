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
# CATEGORIES COVERED (add one per M3 rename):
#   $savedlists  saved-list VOC id; on disk still $SVLISTS
#   $hold        hold-file VOC id; on disk still $HOLD.  The "$hold recname"
#                marker SETPTR writes is matched by C (to_file.c), so this
#                category also proves the C and the BASIC agree: a mismatch
#                prints to a file literally named "$hold zzlch" in the account
#                directory instead of $HOLD/zzlch, and row H5b looks for it.
#   commands     every K/PA/PH/R/S/V id in NEWVOC, VOC_TEMPLATE, SD.VOCLIB
#                (the port's 1a88360, 777 here); static rows S6-S9, and count
#                as the one run through the account migration.
#
# ***"NOT FOUND" CANNOT TEST A RENAME*** - the port's lesson (its 65c681f):
# CT folds the record id, so CT VOC $SAVEDLISTS finds $savedlists either way.
# Two instruments instead: CT's heading echoes the id it MATCHED, and the
# probe's exact READ says which spelling is on disk.
#
# THE MIGRATION IS RUN FOR REAL, ON THE CALLER'S OWN VOC, ONE CATEGORY AT A
# TIME.  The probe moves the id back to upper case - an account from before the
# rename - the category's function must still work through the fold, and the
# real UPDATE.ACCOUNTS (mode 2, own account, no sudo) must move it forward and
# name exactly that id (10916).  THE RESTORE UNDOES ONLY WHAT THE RUN DID, and
# each category's last row is "the account ends as it started".
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
HOLDREC = "zzlch"

M10917 = r"under BOTH an upper-case and a lower-case name"
FAULT = r"^[0-9A-F]{8}: "
SAVED = r"^2 records saved to select list 'zzlcl'$"
GOT = r"^2 record\(s\) selected to select list 0$"


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
    holddir = os.path.join(acct, "$HOLD")
    stray = os.path.join(acct, "$hold " + HOLDREC)

    run.say("%s: as %s (uid %d), NOT elevated" % (NAME, user, os.geteuid()))
    run.say("  sd        %s" % V.SD)
    run.say("  sdsys     %s" % V.SDSYS)
    run.say("  account   %s" % acct)
    run.say("  probe     %s  ->  %s" % (PROBE_SRC, os.path.join(bp, PROBE)))
    run.say("")

    run.heading("0. preconditions")
    if V.require_not_root(run, "Every check is about the caller's own account."):
        return run.verdict()
    if V.require_paths(run, V.SD, V.SDSYS, acct, PROBE_SRC, holddir):
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

    def probe(mode, lid):
        return sd("RUN BP %s %s %s" % (PROBE, mode, lid),
                  ["RUN BP %s %s %s" % (PROBE, mode, lid)]).text

    # ---------------------------------------------------- 1. the installed source
    run.heading("1. what was installed (static, the installed tree)")
    gplbp = os.path.join(V.SDSYS, "GPL.BP")
    literal = re.compile(r"""["']\$(SAVEDLISTS|HOLD)[ "']""")
    # A DIRECTORY NAME ON DISK is not a VOC id and is expected to stay upper case
    # until the on-disk half moves: CREATEA's os.name, and BBPROC's FILES_LIST
    # (the bootstrap creating SDSYS's own directories by path).  Those lines are
    # listed, not counted.
    disk = re.compile(r"os\.name\s*=|FILES_LIST")
    hits, exempt = [], []
    records = [fn for fn in sorted(os.listdir(gplbp))
               if os.path.isfile(os.path.join(gplbp, fn))]
    for fn in records:
        with open(os.path.join(gplbp, fn), errors="replace") as f:
            for i, line in enumerate(f, 1):
                code = line.split(";*")[0]
                if not line.lstrip().startswith("*") and literal.search(code):
                    (exempt if disk.search(code) else hits).append("%s:%d" % (fn, i))
    run.say("  scanned %d GPL.BP records; disk-name lines exempted: %s"
            % (len(records), exempt))
    run.note("S1 no quoted $SAVEDLISTS / $HOLD VOC-id literal left in installed"
             " GPL.BP code", [], hits)
    for d in ("NEWVOC", "VOC_TEMPLATE"):
        # edit.list since the command rename; a missing file fails S2, so
        # reading the old spelling would report the rename as a regression.
        p = os.path.join(V.SDSYS, d, "edit.list")
        txt = open(p, errors="replace").read() if os.path.exists(p) else ""
        run.note("S2 %s/EDIT.LIST edits $savedlists" % d, True,
                 "ED $savedlists" in txt)
    tdir = os.listdir(os.path.join(V.SDSYS, "VOC_TEMPLATE"))
    run.note("S2b VOC_TEMPLATE ships $hold and not $HOLD", (True, False),
             ("$hold" in tdir, "$HOLD" in tdir))

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
    run.note("S5 and that list is not empty (S4 compared something)",
             True, len(created_lower) > 0)

    # THE COMMAND IDS (the port's 1a88360).  Which ids keep upper case, and why:
    # F/Q file pointers (file names, a later category), T tier lists (data),
    # X, and $ % @ records.  Everything else in NEWVOC / VOC_TEMPLATE /
    # SD.VOCLIB must be lower case.
    def vtype(p):
        l1 = open(p, errors="replace").readline()
        t = l1[:1].upper()
        return l1[:2].upper() if t == "P" else t
    upper_cmds, counted = [], 0
    for d in ("NEWVOC", "VOC_TEMPLATE", "SD.VOCLIB"):
        dp = os.path.join(V.SDSYS, d)
        for n in sorted(os.listdir(dp)):
            p = os.path.join(dp, n)
            if not os.path.isfile(p) or n[0] in "$%@":
                continue
            if vtype(p) in ("K", "PA", "PH", "R", "S", "V"):
                counted += 1
                if n != n.lower():
                    upper_cmds.append("%s/%s" % (d, n))
    run.say("  command-type records examined: %d" % counted)
    run.note("S6 command records were found (not the null case)", True, counted > 700)
    run.note("S7 no command id in NEWVOC/VOC_TEMPLATE/SD.VOCLIB has an upper-case"
             " letter", [], upper_cmds[:10])
    unresolved = []
    for lst, src in (("TIER.OMIT.STANDARD", "NEWVOC"),
                     ("TIER.ADD.ADMINISTRATOR", "VOC_TEMPLATE")):
        body = open(os.path.join(V.SDSYS, "NEWVOC", lst), errors="replace").read()
        for n in [l.strip() for l in body.splitlines()[1:] if l.strip()]:
            if n != n.lower() or not os.path.exists(os.path.join(V.SDSYS, src, n)):
                unresolved.append("%s:%s" % (lst, n))
    run.note("S8 every tier-list entry is lower case and names a shipped record",
             [], unresolved)
    bad_r = []
    for d in ("NEWVOC", "VOC_TEMPLATE"):
        dp = os.path.join(V.SDSYS, d)
        for n in sorted(os.listdir(dp)):
            p = os.path.join(dp, n)
            if os.path.isfile(p) and vtype(p) == "R":
                f = open(p, errors="replace").read().split("\n")
                tgt = f[2] if len(f) > 2 else ""
                if not os.path.exists(os.path.join(V.SDSYS, f[1] if len(f) > 1 else "", tgt)):
                    bad_r.append("%s/%s -> %s" % (d, n, tgt))
    run.note("S9 every R record's field 3 names a record that exists", [], bad_r)

    # ---------------------------------------------------------------- 2. ground
    run.heading("2. ground and probe")
    for p in (os.path.join(bp, PROBE), os.path.join(holddir, HOLDREC), stray):
        if os.path.exists(p):
            run.refuse("%s already exists" % p)
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

    # ------------------------------------------------ per-category function
    def savedlists_works(prefix, first):
        if first:
            s = sd("save a list", ["SELECT VOC SAMPLE 2", "SAVE.LIST %s" % LIST])
            run.note(prefix + "a SAVE.LIST saved 2", True, V.says(s.text, SAVED))
        s = sd("get the list", ["GET.LIST %s" % LIST, "CLEARSELECT"])
        run.note(prefix + "b GET.LIST got 2", True, V.says(s.text, GOT))
        run.note(prefix + "c no runtime fault", False, V.says(s.text, FAULT))

    def hold_works(prefix, first):
        for p in (os.path.join(holddir, HOLDREC), stray):
            if os.path.exists(p):
                os.remove(p)
        s = sd("print to a named hold record, then show the unit",
               ["SETPTR 5,80,66,0,0,3,AS %s,BRIEF" % HOLDREC,
                "LIST VOC SAMPLE 1 LPTR 5", "SETPTR 5"])
        run.note(prefix + "a the print landed in $HOLD/%s on disk" % HOLDREC, True,
                 os.path.exists(os.path.join(holddir, HOLDREC)))
        run.note(prefix + "b and NOT in a stray file named '$hold %s' (C and BASIC"
                 " agree on the marker)" % HOLDREC, False, os.path.exists(stray))
        run.note(prefix + "c SETPTR names the hold file in the new spelling", True,
                 V.says(s.text, r"^\s*Mode\s+: 3 \(Hold file: \$hold %s\)$" % HOLDREC))
        run.note(prefix + "d no runtime fault", False, V.says(s.text, FAULT))

    def command_works(prefix, first):
        s = sd("the command typed in both cases", ["COUNT VOC", "count voc"])
        run.note(prefix + "a it counted, typed both ways", 2,
                 V.say_count(s.text, r"^[0-9]+ record\(s\) counted$"))
        run.note(prefix + "b neither said 'is not in your VOC'", False,
                 V.says(s.text, r"is not in your VOC"))
        run.note(prefix + "c no runtime fault", False, V.says(s.text, FAULT))

    CATS = [
        ("$savedlists", "L", savedlists_works),
        ("$hold", "H", hold_works),
        ("count", "C", command_works),
    ]

    try:
        for lid, k, works in CATS:
            uid = lid.upper()
            down = False
            baseline = (None, None)
            try:
                run.heading("3%s. %s - a new account holds the NEW id" % (k, lid))
                t = probe("READ", lid)
                baseline = (tag(t, "EXACT.LOWER"), tag(t, "EXACT.UPPER"))
                run.say("  baseline (lower, upper) = %s" % (baseline,))
                run.note(k + "1 probe ran for " + lid, "1", tag(t, "ZZLCN.END"))
                run.note(k + "2 %s exists, exactly" % lid, "Y", tag(t, "EXACT.LOWER"))
                run.note(k + "3 %s does not" % uid, "N", tag(t, "EXACT.UPPER"))
                s = sd("CT names the id it matched", ["CT VOC %s" % uid])
                run.note(k + "4 CT VOC %s answers with the id it matched, %s"
                         % (uid, lid), True,
                         V.says(s.text, r"^VOC %s$" % re.escape(lid)))
                works(k + "5", True)

                run.heading("4%s. %s - an account from BEFORE the rename" % (k, lid))
                t = probe("DOWN", lid)
                down = tag(t, "DOWN") == "1"
                run.note(k + "6 the id was moved back to " + uid, "1", tag(t, "DOWN"))
                run.note(k + "7 exactly %s now" % uid, ("N", "Y"),
                         (tag(t, "EXACT.LOWER"), tag(t, "EXACT.UPPER")))
                works(k + "8", False)

                run.heading("5%s. %s - the real update.voc carries it across" % (k, lid))
                if not down:
                    run.note(k + "9 section 4 moved the id back (else this measures"
                             " nothing)", True, False)
                s = sd("UPDATE.ACCOUNTS (own account)", ["UPDATE.ACCOUNTS"], timeout=180)
                run.note(k + "10 10916 names exactly " + lid, True, V.says(
                    s.text, r"^1 VOC record\(s\) were renamed to the lower-case name"
                            r" SD now uses: %s$" % re.escape(lid)))
                run.note(k + "11 no both-spellings refusal (10917)", False,
                         V.says(s.text, M10917))
                run.note(k + "12 no runtime fault", False, V.says(s.text, FAULT))
                t = probe("READ", lid)
                run.note(k + "13 exactly %s again" % lid, ("Y", "N"),
                         (tag(t, "EXACT.LOWER"), tag(t, "EXACT.UPPER")))
                works(k + "14", False)
            finally:
                run.heading("6%s. %s - restore (always runs)" % (k, lid))
                if down:
                    t = probe("UP", lid)
                    run.say("  UP=%s" % tag(t, "UP"))
                else:
                    run.say("  this run did not move the id, so it does not move it back")
                    t = probe("READ", lid)
                run.note(k + "Z the account ends exactly as it started (lower, upper)",
                         baseline, (tag(t, "EXACT.LOWER"), tag(t, "EXACT.UPPER")))
    finally:
        run.heading("7. tidy (always runs)")
        s = sd("delete the list", ["DELETE.LIST %s" % LIST])
        run.note("Z1 the saved list is gone", True,
                 V.says(s.text, r"^Deleted saved select list '%s'$" % LIST))
        for p in (os.path.join(holddir, HOLDREC), stray, os.path.join(bp, PROBE)):
            if os.path.exists(p):
                os.remove(p)
        run.note("Z2 no hold record of ours is left", False,
                 os.path.exists(os.path.join(holddir, HOLDREC)) or os.path.exists(stray))
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
