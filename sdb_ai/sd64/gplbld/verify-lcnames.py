#!/usr/bin/env python3
#
# verify-lcnames.py - the lower-case renames, category by category (plan
#                     section M3).  Intent from the port's verify-lcnames.ps1.
#                     No migration half: there are no existing installs to
#                     carry across a rename (owner, 12 Sep 2026), so the case
#                     migration and the sections that ran it were removed.
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
#                as the one exercised in a session.
#   pointers     the ten F/Q file-pointer ids (the port's 0394af4); static
#                rows S10-S14, and syscom exercised in a session.  Fields 2/3
#                (the paths on disk) are a later category.
#
# ***"NOT FOUND" CANNOT TEST A RENAME*** - the port's lesson (its 65c681f):
# CT folds the record id, so CT VOC $SAVEDLISTS finds $savedlists either way.
# Two instruments instead: CT's heading echoes the id it MATCHED, and the
# probe's exact READ says which spelling is on disk.  The run does not change
# any VOC id; it saves one list and prints one hold record, both tidied.
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

FAULT = r"^[0-9A-F]{8}: "
SAVED = r"^2 records saved to select list 'zzlcl'$"
GOT = r"^2 record\(s\) selected to select list 0$"


def readtxt(path):
    """A file's text, or '' if it is absent - so a rename that moved a file
    fails the row that reads it instead of killing the run before a verdict."""
    try:
        with open(path, errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def tag(text, name):
    m = re.search(r"^%s=(.*)$" % re.escape(name), text, re.MULTILINE)
    return m.group(1).strip() if m else None


def main():
    ap = argparse.ArgumentParser(description="plan M3 lower-case renames")
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

    def probe(lid):
        return sd("RUN BP %s %s" % (PROBE, lid),
                  ["RUN BP %s %s" % (PROBE, lid)]).text

    # ---------------------------------------------------- 1. the installed source
    run.heading("1. what was installed (static, the installed tree)")
    gplbp = os.path.join(V.SDSYS, "gpl.bp")
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
    for d in ("newvoc", "voc_template"):
        # edit.list since the command rename; a missing file fails S2, so
        # reading the old spelling would report the rename as a regression.
        p = os.path.join(V.SDSYS, d, "edit.list")
        txt = open(p, errors="replace").read() if os.path.exists(p) else ""
        run.note("S2 %s/EDIT.LIST edits $savedlists" % d, True,
                 "ED $savedlists" in txt)
    tdir = os.listdir(os.path.join(V.SDSYS, "voc_template"))
    run.note("S2b voc_template ships $hold and not $HOLD", (True, False),
             ("$hold" in tdir, "$HOLD" in tdir))

    # THE COMMAND IDS (the port's 1a88360).  Which ids keep upper case, and why:
    # F/Q file pointers (file names, a later category), T tier lists (data),
    # X, and $ % @ records.  Everything else in NEWVOC / VOC_TEMPLATE /
    # SD.VOCLIB must be lower case.
    def vtype(p):
        l1 = open(p, errors="replace").readline()
        t = l1[:1].upper()
        return l1[:2].upper() if t == "P" else t
    upper_cmds, counted = [], 0
    for d in ("newvoc", "voc_template", "sd.voclib"):
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
    for lst, src in (("TIER.OMIT.STANDARD", "newvoc"),
                     ("TIER.ADD.ADMINISTRATOR", "voc_template")):
        body = readtxt(os.path.join(V.SDSYS, "newvoc", lst))
        if not body:
            unresolved.append("%s: absent or empty" % lst)
        for n in [l.strip() for l in body.splitlines()[1:] if l.strip()]:
            if n != n.lower() or not os.path.exists(os.path.join(V.SDSYS, src, n)):
                unresolved.append("%s:%s" % (lst, n))
    run.note("S8 every tier-list entry is lower case and names a shipped record",
             [], unresolved)
    bad_r = []
    for d in ("newvoc", "voc_template"):
        dp = os.path.join(V.SDSYS, d)
        for n in sorted(os.listdir(dp)):
            p = os.path.join(dp, n)
            if os.path.isfile(p) and vtype(p) == "R":
                f = open(p, errors="replace").read().split("\n")
                tgt = f[2] if len(f) > 2 else ""
                if not os.path.exists(os.path.join(V.SDSYS, f[1] if len(f) > 1 else "", tgt)):
                    bad_r.append("%s/%s -> %s" % (d, n, tgt))
    run.note("S9 every R record's field 3 names a record that exists", [], bad_r)

    # THE F/Q FILE-POINTER IDS (the port's 0394af4).  Ids only: fields 2 and 3
    # are paths on disk and are NOT renamed by this category.
    PTRS = {"newvoc": ["voc", "newvoc", "syscom", "dict.dict", "md",
                       "sd.accounts", "sd.voclib"],
            "voc_template": ["voc", "newvoc", "syscom", "dict.dict", "md",
                             "sd.accounts", "sd.voclib", "accounts",
                             "messages", "qfile"]}
    wrong = []
    for d, ids in PTRS.items():
        have = os.listdir(os.path.join(V.SDSYS, d))
        for i in ids:
            if i not in have or i.upper() in have:
                wrong.append("%s/%s" % (d, i))
    run.note("S10 the F/Q pointer ids are shipped lower case, and not upper", [], wrong)
    qt = []
    for d in PTRS:
        for i, tgt in (("md", "voc"), ("sd.accounts", "accounts")):
            # A MISSING RECORD IS A FAILED ROW, NOT A TRACEBACK - watched
            # crashing here on the pre-rename install, where md is MD.
            p = os.path.join(V.SDSYS, d, i)
            if not os.path.exists(p):
                qt.append("%s/%s absent" % (d, i))
                continue
            f = open(p, errors="replace").read().split("\n")
            if len(f) < 3 or f[2] != tgt:
                qt.append("%s/%s field 3 = %r" % (d, i, f[2] if len(f) > 2 else None))
    run.note("S11 the Q pointers name their targets lower case", [], qt)
    tc = readtxt(os.path.join(V.SDSYS, "voc_template", "third.compile"))
    run.note("S12 third.compile's CD targets are lower case", True,
             all(("CD %s" % t) in tc for t in ("accounts", "dict.dict", "voc")))
    # ***THE TWO THAT MUST STAY UPPER.*** A future sweep lowering either is a
    # defect: DELETEF's guard upcases only its left side, and SETFILE's default
    # covers accounts from before the rename through exact-then-downcase.
    deletef = readtxt(os.path.join(gplbp, "DELETEF"))
    setfile = readtxt(os.path.join(gplbp, "SETFILE"))
    run.note("S13 DELETEF's banned list is still 'VOC' (the guard upcases one side)",
             True, "banned.files = 'VOC':@VM:'$ACC'" in deletef)
    run.note("S14 SETFILE's default pointer is still 'QFILE'", True,
             "pointer = 'QFILE'" in setfile)

    # THE sdsys DATA DIRECTORIES ON DISK (plan M3 D1, the port's e1095ab).  On
    # ext4 both spellings could exist side by side, so "lower present" alone is
    # not the rename: the upper spelling must be ABSENT too.  $HOLD, $HOLD.DIC
    # and VOC are the SDSYS account's own (D3); GPL.BP and friends are D2.
    D1 = ["newvoc", "voc_template", "messages", "syscom", "sd.voclib",
          "accounts", "$ipc", "$map", "$map.dic", "voc.dic", "accounts.dic",
          "dict.dic", "dir_dict"]
    top = set(os.listdir(V.SDSYS))
    run.say("  sdsys top level: %s" % sorted(top))
    d1_wrong = ["%s (lower %s, upper %s)" % (n, n in top, n.upper() in top)
                for n in D1
                if not os.path.isdir(os.path.join(V.SDSYS, n)) or n.upper() in top]
    run.note("S15 the %d D1 sdsys directories exist lower case and not upper"
             % len(D1), [], d1_wrong)

    # THE sdsys PROGRAM DIRECTORIES (plan M3 D2) - the same both-halves rule -
    # and the SDSYS account's F records that name them, which must be lower
    # case in id AND path, or BASIC's "<file>.OUT" would reach a mixed name.
    D2 = ["gpl.bp", "gpl.bp.out", "bp", "bp.out", "pcode.out"]
    d2_wrong = ["%s (lower %s, upper %s)" % (n, n in top, n.upper() in top)
                for n in D2
                if not os.path.isdir(os.path.join(V.SDSYS, n)) or n.upper() in top]
    run.note("S16 the %d D2 sdsys directories exist lower case and not upper"
             % len(D2), [], d2_wrong)
    vt = os.path.join(V.SDSYS, "voc_template")
    vt_names = set(os.listdir(vt))
    rec_wrong = []
    for n in D2[:4]:
        f = readtxt(os.path.join(vt, n)).split("\n")
        if n.upper() in vt_names or len(f) < 2 or f[1] != n:
            rec_wrong.append("%s (upper id %s, field 2 %r)"
                             % (n, n.upper() in vt_names, f[1] if len(f) > 1 else None))
    run.note("S17 voc_template's gpl.bp/gpl.bp.out/bp/bp.out: id and path lower,"
             " no upper id", [], rec_wrong)

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

    def pointer_works(prefix, first):
        s = sd("the pointer opened by both spellings",
               ["COUNT SYSCOM", "COUNT syscom"])
        run.note(prefix + "a it counted SYSCOM's records, typed both ways", 2,
                 V.say_count(s.text, r"^[1-9][0-9]* record\(s\) counted$"))
        run.note(prefix + "b neither said 'File not found'", False,
                 V.says(s.text, r"^File not found$"))
        run.note(prefix + "c no runtime fault", False, V.says(s.text, FAULT))

    CATS = [
        ("$savedlists", "L", savedlists_works),
        ("$hold", "H", hold_works),
        ("count", "C", command_works),
        ("syscom", "P", pointer_works),
    ]

    try:
        for lid, k, works in CATS:
            uid = lid.upper()
            run.heading("3%s. %s - the account holds the NEW id" % (k, lid))
            t = probe(lid)
            run.say("  (lower, upper) = %s"
                    % ((tag(t, "EXACT.LOWER"), tag(t, "EXACT.UPPER")),))
            run.note(k + "1 probe ran for " + lid, "1", tag(t, "ZZLCN.END"))
            run.note(k + "2 %s exists, exactly" % lid, "Y", tag(t, "EXACT.LOWER"))
            run.note(k + "3 %s does not" % uid, "N", tag(t, "EXACT.UPPER"))
            s = sd("CT names the id it matched", ["CT VOC %s" % uid])
            run.note(k + "4 CT VOC %s answers with the id it matched, %s"
                     % (uid, lid), True,
                     V.says(s.text, r"^VOC %s$" % re.escape(lid)))
            works(k + "5", True)
    finally:
        run.heading("4. tidy (always runs)")
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
