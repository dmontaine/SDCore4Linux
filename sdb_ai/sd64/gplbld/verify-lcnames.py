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
#   $savedlists  saved-list VOC id; on disk $svlists since D3
#   $hold        hold-file VOC id; on disk $hold since D3.  The "$hold recname"
#                marker SETPTR writes is matched by C (to_file.c), so this
#                category also proves the C and the BASIC agree: a mismatch
#                prints to a file literally named "$hold zzlch" in the account
#                directory instead of $hold/zzlch, and row H5b looks for it.
#   directories  S15 (D1), S16-S17 (D2), S18 (D3), and F0-F5: the object file
#                BASIC names is bp.out, reachable by BASIC BP afterwards.
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
    bp = os.path.join(acct, "bp")           # plan M3 D3
    bpout = os.path.join(acct, "bp.out")    # plan M3 D4: CREATE.FILE makes it lower
    bpout_upper = os.path.join(acct, "BP.OUT")
    holddir = os.path.join(acct, "$hold")
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
    # A MISSING RECORD READS AS '' AND FAILS S13/S14 - so lowering the names
    # here is required, not cosmetic (gpl.bp record names lower since 13 Sep).
    deletef = readtxt(os.path.join(gplbp, "deletef"))
    setfile = readtxt(os.path.join(gplbp, "setfile"))
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

    # THE ACCOUNT DIRECTORIES (plan M3 D3), in the account CREATE.ACCOUNT made
    # for the installing user and in SDSYS - same both-halves rule.  BP.OUT is
    # not here: CREATE.FILE still upper-cases the directory it makes (D4).
    d3_wrong = []
    for root, names in ((acct, ["voc", "$hold", "$hold.dic", "$svlists", "bp"]),
                        (V.SDSYS, ["voc", "$hold", "$hold.dic"])):
        have = set(os.listdir(root))
        run.say("  %s: %s" % (root, sorted(n for n in have if n.lower() in names)))
        d3_wrong += ["%s/%s (lower %s, upper %s)" % (root, n, n in have, n.upper() in have)
                     for n in names
                     if not os.path.isdir(os.path.join(root, n)) or n.upper() in have]
    run.note("S18 the D3 account directories exist lower case and not upper",
             [], d3_wrong)

    # THE $ RECORDS (plan M3), statically: shipped lower and not upper, and the
    # three programs that read or write them by EXACT id name the lower one.
    dollar_wrong = []
    for d in ("newvoc", "voc_template"):
        have = set(os.listdir(os.path.join(V.SDSYS, d)))
        for n in ("$acc", "$map", "$release"):
            if n not in have or n.upper() in have:
                dollar_wrong.append("%s/%s (lower %s, upper %s)"
                                    % (d, n, n in have, n.upper() in have))
    run.note("S19 newvoc and voc_template ship $acc $map $release lower, not upper",
             [], dollar_wrong)
    lits = {"LOGIN": ['"$release"', '"$command.stack"'],
            "CPROC": ['"$command.stack"', "'$command.stack'"],
            "CREATEA": ["'$command.stack'"]}
    missing = ["%s %s" % (p, l) for p, ls in sorted(lits.items())
               for l in ls if l not in readtxt(os.path.join(gplbp, p.lower()))]
    stale = [p for p in lits
             if re.search(r"""["']\$(RELEASE|COMMAND\.STACK)["']""",
                          "\n".join(ln.split(";*")[0] for ln in
                                    readtxt(os.path.join(gplbp, p.lower())).splitlines()
                                    if not ln.lstrip().startswith("*")))]
    run.note("S20 LOGIN/CPROC/CREATEA name $release and $command.stack lower", [],
             missing)
    run.note("S21 and no upper-case literal of either is left in their code", [], stale)

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
    bpout_before = os.path.exists(bpout) or os.path.exists(bpout_upper)
    os.makedirs(bp, exist_ok=True)
    shutil.copyfile(PROBE_SRC, os.path.join(bp, PROBE))
    # ***THE OBJECT-FILE NAME (plan M3 D3, the port's 1943704).***  BASIC builds
    # the name only when the object file does not exist yet, so with one already
    # there this measures nothing - F0 is decisive for that reason, not context.
    # The old failure was never in the compile that made the file: it was the
    # NEXT one, typed the other way.  So: lower first, then upper.
    run.note("F0 no bp.out or BP.OUT before this run, so BASIC's create branch"
             " is reached", False, bpout_before)
    s = sd("compile, file typed lower", ["BASIC bp %s" % PROBE])
    run.note("F1 the probe compiled with 0 errors", True, V.says(s.text, r"^0 error\(s\)"))
    t = sd("exact VOC reads of the object file id",
           ["RUN BP %s bp.out" % PROBE]).text
    run.note("F2 VOC holds bp.out exactly, and not BP.OUT", ("Y", "N"),
             (tag(t, "EXACT.LOWER"), tag(t, "EXACT.UPPER")))
    run.note("F3 and not the mixed bp.OUT the old BASIC made", "N",
             tag(t, "EXACT.MIXED"))
    s = sd("compile again, file typed upper", ["BASIC BP %s" % PROBE])
    run.note("F4 the second compile, typed the other way, compiled with 0 errors",
             True, V.says(s.text, r"^0 error\(s\)"))
    run.note("F5 and did not hit 'already exists'", False,
             V.says(s.text, r"already exists"))
    # D4: the directory CREATE.FILE made behind that id is lower case too.
    top_acct = set(os.listdir(acct))
    run.note("F6 the object directory on disk is bp.out, and there is no BP.OUT",
             (True, False), ("bp.out" in top_acct, "BP.OUT" in top_acct))

    # ***CREATE.FILE ITSELF (plan M3 D4).***  Typed in UPPER case, a new file must
    # get a lower-case VOC id, directory and .dic; the same name typed lower must
    # then find it rather than make a second casing; and DELETE.FILE typed upper
    # must remove it.  The name is this run's own and is refused if present.
    cf = "zzlccf"
    cfu = cf.upper()
    for n in (cf, cfu, cf + ".dic", cfu + ".DIC"):
        if n in top_acct:
            run.refuse("%s already exists in %s" % (n, acct))
            return run.verdict()
    s = sd("CREATE.FILE typed upper", ["CREATE.FILE %s" % cfu])
    # N, not C: section 3C's command rows are already C1-C5.
    run.note("N1 it created the data part as %s" % cf, True,
             V.says(s.text, r"^Created DATA part as %s$" % re.escape(cf)))
    run.note("N2 and the dictionary part as %s.dic" % cf, True,
             V.says(s.text, r"^Created DICT part as %s\.dic$" % re.escape(cf)))
    have = set(os.listdir(acct))
    run.note("N3 on disk: %s and %s.dic, no upper spelling of either" % (cf, cf),
             (True, True, False, False),
             (cf in have, cf + ".dic" in have, cfu in have, cfu + ".DIC" in have))
    t = sd("exact VOC reads of the new file's id", ["RUN BP %s %s" % (PROBE, cf)]).text
    run.note("N4 VOC holds %s exactly, and not %s" % (cf, cfu), ("Y", "N"),
             (tag(t, "EXACT.LOWER"), tag(t, "EXACT.UPPER")))
    s = sd("CREATE.FILE typed lower, the same name", ["CREATE.FILE %s" % cf])
    run.note("N5 the second CREATE.FILE found the file instead of making another",
             False, V.says(s.text, r"^Created (DATA|DICT) part"))
    s = sd("DELETE.FILE typed upper", ["DELETE.FILE %s FORCE NO.QUERY" % cfu])
    after = set(os.listdir(acct))
    run.note("N6 DELETE.FILE %s removed %s and %s.dic without asking" % (cfu, cf, cf),
             (False, False, False),
             (cf in after, cf + ".dic" in after, V.says(s.text, r"\(y/<n>\)")))

    # ***ACCOUNT NAMES (13 Sep 2026, owner: lower case, SDSYS included).***  The
    # register key is the name lower-cased, and every lookup downcases its
    # input.  The instrument is WHO, which prints @WHO: typed in UPPER case,
    # LOGTO must reach the account and WHO must say it in lower case - and in
    # no other spelling.  The caller's own account, so no grant is involved.
    reg = os.path.join(V.SDSYS, "accounts")
    reg_ids = sorted(os.listdir(reg)) if os.path.isdir(reg) else []
    run.say("  register ids: %s" % reg_ids)
    run.note("U1 the register holds %s and sdsys, and no upper-case id" % user.lower(),
             (True, True, []),
             (user.lower() in reg_ids, "sdsys" in reg_ids,
              [i for i in reg_ids if i != i.lower()]))
    s = sd("LOGTO own account typed upper, then WHO",
           ["LOGTO %s" % user.upper(), "WHO"])
    run.note("U2 LOGTO %s was not refused as unregistered" % user.upper(), False,
             V.says(s.text, r"not in register"))
    run.note("U3 WHO reports %s in lower case" % user.lower(), True,
             V.says(s.text, r"^\s*\d+\s+%s\s*$" % re.escape(user.lower())))
    run.note("U4 and not in upper case", False,
             V.says(s.text, r"^\s*\d+\s+%s\s*$" % re.escape(user.upper())))

    # ***CASE INVERSION IS OFF WITHOUT THE LOGIN PARAGRAPH (13 Sep 2026).***  C
    # started every session inverted and LOGIN set it again; only the VOC login
    # paragraph's PTERM CASE NOINVERT turned it off - measured on 80bd15c: with
    # the paragraph set aside, "Case inversion: On".  THE RESTORE IS THE RISK:
    # measured the same day, a restore session with inversion on had its
    # record ids flipped and copied nothing.  So every session here STARTS with
    # PTERM CASE NOINVERT, which arrives intact either way (verbs and keywords
    # fold), and the restore is checked against the paragraph's own text.
    save = "zzlcnlogin"
    pre = sd("the login paragraph before", ["PTERM CASE NOINVERT", "CT VOC login %s" % save])
    body_before = re.findall(r"^\s*\d+: .*$", pre.text.split("VOC login", 1)[-1].split("Record", 1)[0],
                             re.MULTILINE)
    run.note("I0 the account has a login paragraph and no %s" % save, (True, True),
             (len(body_before) > 0, V.says(pre.text, r"^Record '%s' not found$" % save)))
    if len(body_before) > 0 and V.says(pre.text, r"^Record '%s' not found$" % save):
        try:
            s = sd("set the login paragraph aside",
                   ["PTERM CASE NOINVERT", "COPY FROM VOC login,%s" % save, "DELETE VOC login"])
            run.note("I1 the paragraph was set aside (copied, then deleted)", True,
                     V.says(s.text, r"^1 record\(s\) copied\.") and
                     V.says(s.text, r"^1 record\(s\) deleted"))
            s = sd("a session with no login paragraph", ["PTERM DISPLAY"])
            run.note("I2 THE ROW: with no login paragraph, case inversion is Off", True,
                     V.says(s.text, r"^\s*Case inversion: Off\s*$"))
        finally:
            s = sd("restore the login paragraph",
                   ["PTERM CASE NOINVERT", "COPY FROM VOC %s,login" % save,
                    "DELETE VOC %s" % save])
            post = sd("the login paragraph after", ["PTERM CASE NOINVERT", "CT VOC login %s" % save])
            body_after = re.findall(r"^\s*\d+: .*$",
                                    post.text.split("VOC login", 1)[-1].split("Record", 1)[0],
                                    re.MULTILINE)
            run.say("  login paragraph before: %s" % body_before)
            run.say("  login paragraph after : %s" % body_after)
            run.note("I3 the login paragraph is back exactly, and %s is gone" % save,
                     (body_before, True),
                     (body_after, V.says(post.text, r"^Record '%s' not found$" % save)))

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
        run.note(prefix + "a the print landed in $hold/%s on disk" % HOLDREC, True,
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

    # THE $ RECORDS (plan M3, 13 Sep 2026; $command.stack is the port's 69015c3).
    # LOGIN and CPROC read $release and $command.stack by EXACT record id, so
    # these rows are about what those reads reach, not about the fold.
    def release_works(prefix, first):
        s = sd("a session reaches the prompt through LOGIN's $release read", ["WHO"])
        run.note(prefix + "a LOGIN did not refuse for a missing $release (5028)",
                 False, V.says(s.text, r"release VOC record not found"))
        run.note(prefix + "b the session ran a command", True,
                 V.says(s.text, r"^[0-9]+ \S+"))

    # $acc is a DIRECTORY file on the account directory, whose records are the
    # plain files in it - and a fresh account holds only subdirectories, so
    # COUNT $ACC says 0 (measured 13 Sep on 80b4e83; the first version of this
    # row expected >= 1 and failed on a correct SD).  "0 counted" cannot tell a
    # file reached from one that is empty, so the row plants its own record,
    # counts exactly 1 more than the baseline, and removes it.
    acc_rec = os.path.join(acct, "zzlcnacc")

    def acc_works(prefix, first):
        if os.path.exists(acc_rec):
            run.note(prefix + "0 the fixture record %s was absent" % acc_rec, False, True)
            return
        s = sd("baseline", ["COUNT $acc"])
        m = re.search(r"^([0-9]+) record\(s\) counted$", s.text, re.MULTILINE)
        base = int(m.group(1)) if m else None
        run.say("  baseline COUNT $acc = %s" % base)
        with open(acc_rec, "w") as f:
            f.write("zzlcn\n")
        try:
            s = sd("the account-directory pointer, typed both ways",
                   ["COUNT $ACC", "COUNT $acc"])
        finally:
            os.remove(acc_rec)
        want = "%d record(s) counted" % ((base or 0) + 1)
        run.note(prefix + "a the baseline count was read", True, base is not None)
        run.note(prefix + "b typed both ways, it counted the planted record (%s)" % want,
                 2, V.say_count(s.text, r"^%s$" % re.escape(want)))
        run.note(prefix + "c neither said 'File not found'", False,
                 V.says(s.text, r"^File not found$"))
        run.note(prefix + "d no runtime fault", False, V.says(s.text, FAULT))

    def map_works(prefix, first):
        s = sd("the map file, typed both ways", ["COUNT $MAP", "COUNT $map"])
        run.note(prefix + "a it counted the map file, typed both ways", 2,
                 V.say_count(s.text, r"^[0-9]+ record\(s\) counted$"))
        run.note(prefix + "b neither said 'File not found'", False,
                 V.says(s.text, r"^File not found$"))

    # THE INSTRUMENT FOR $command.stack IS THE stacks FILE, NOT THE VOC (the
    # port's lesson): CPROC writes it at session end only when its exact read of
    # the record succeeded, so a marker command turning up in it IS the read.
    stackfile = os.path.join(acct, "stacks", user)
    marker = "COUNT VOC WITH F1 = ZZLCNSTACK%d" % os.getpid()

    def stack_works(prefix, first):
        before = readtxt(stackfile)
        run.say("  stack file %s: marker present before = %s"
                % (stackfile, marker in before))
        run.note(prefix + "a the marker is not in the saved stack before", False,
                 marker in before)
        sd("a session that ends with the marker on its stack", [marker])
        after = readtxt(stackfile)
        run.note(prefix + "b the session's stack was saved through $command.stack",
                 True, marker in after)

    CATS = [
        ("$savedlists", "L", savedlists_works),
        ("$hold", "H", hold_works),
        ("count", "C", command_works),
        ("syscom", "P", pointer_works),
        ("$release", "R", release_works),
        ("$acc", "A", acc_works),
        ("$map", "M", map_works),
        ("$command.stack", "K", stack_works),
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
            V.show_sd(run, "BP.OUT was made by this run", ["DELETE VOC bp.out"],
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
