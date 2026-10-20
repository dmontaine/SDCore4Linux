#!/usr/bin/env python3
#
# mutate-masters.py - RUNTIME MUTANTS of the master files' kernel code (S.67), run against sandbox-masters.py.
#
#   SDBOX_KEYSET=3 python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/mutate-masters.py <dir> [--build] [name,name,...]
#
# No install, no sudo.  <dir> is a sandbox made by sandbox-fromtree.py (--build makes it, from THIS tree; it must be empty or absent).  Each mutant breaks ONE guard in the
# sandbox's own COPY of a kernel source (<dir>/tree/gplsrc), rebuilds that copy, puts the rebuilt sd into the sandbox and runs the sections of sandbox-masters.py that are
# meant to stand behind the guard: a mutant the suite does not turn red is a GAP in the suite.  The tree under test is never touched.  Exit 0 every mutant caught, 1 one
# survived, 2 it could not run (the control must be green first: a red control means no mutant says anything).
#
# NOT HERE: the cutting back of a journal after a SHORT write (a sandbox cannot make a write come up short); test-masters-units.py (T7) holds that one as text, with mutants.
#
# THE INSTRUMENT PRINTS WHAT IT DID.  For every mutant: the file, the text it changed (and how many places matched: it must be exactly one, or the mutant is SKIPPED and
# counted as a failure of this run), the sections it ran, the rows that failed, the verdict.  A build that fails is reported, not counted as caught.
#
# START-HISTORY:
# 19 Oct 26 dm  New.  The independent verifier of S.67 ran 16 of these by hand (/tmp/v67run/mutrun.py) and 8 SURVIVED the 223 rows of the time: the file-name guards of a save
#               and of a journal line, the unopenable-file guard of the drain, O_NOFOLLOW on the journal, the drain's flock, the directory search bit, and the hook after a failed
#               write.  The rows N20 to N27 were written for them; this is the proof that they stand behind them, and the guards of the other findings with them.
# END-HISTORY

import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
SUITE = os.path.join(HERE, "sandbox-masters.py")

BASE = "setup,deliver,vfix"                    # enough state for the rows of the findings, and about a minute
# (name, file under gplsrc, text, replacement, sections)
M = [
    # ---- the guards the verifier found nothing standing behind (its K numbers) ----
    ("K2-file-ok-removed-in-deliver", "masters.c", "    if (!mst_file_ok(file))\n      return mst_refuse(MSG_BADKEY, keytxt, NULL, NULL);\n    rid = p2 + 1;",
     "    if (0)\n      return mst_refuse(MSG_BADKEY, keytxt, NULL, NULL);\n    rid = p2 + 1;", BASE),
    ("K3-account-name-check-removed", "masters.c", "if ((rid_len < 1) || (rid_len > 255) || !mst_valid_account_name(acct))", "if ((rid_len < 1) || (rid_len > 255))", BASE),
    ("K4-file-ok-removed-in-journal-parse", "masters.c", "  if ((ev->kind == 'd') && !mst_file_ok(ev->file))\n    return 0;", "  if (0)\n    return 0;", BASE),
    ("K5-journal-parse-accepts-extra-fields", "masters.c", "  if ((n != 6) || (p != NULL))\n    return 0;", "  if (n < 6)\n    return 0;", BASE),
    ("K9-unopenable-file-treated-as-absent", "masters.c",
     "  } else if (!cx->last_absent) {\n    cx->errs++; /* the file is there and cannot be opened: say nothing about its records, and delete no copy of them */\n    return MS_ERR;\n  }",
     "  } else if (0) {\n    cx->errs++;\n    return MS_ERR;\n  }", BASE),
    ("K48-hook-after-failed-write", "dh_write.c", "  if (dh_err == 0) {\n    dh_forced_write(dh_file); /* a file in forced write mode (Fixes item 102) */\n\n    /* 19 Oct 26 S.67: a VOC or dictionary record has been written.",
     "  if (1) {\n    dh_forced_write(dh_file); /* a file in forced write mode (Fixes item 102) */\n\n    /* 19 Oct 26 S.67: a VOC or dictionary record has been written.", "setup,window"),
    ("K49-journal-append-follows-symlink", "masters.c", "  fd = open(path, O_WRONLY | O_APPEND | O_NOFOLLOW | O_CLOEXEC);\n  if (fd < 0) {\n    if ((errno != ENOENT) || mst_masters_present())",
     "  fd = open(path, O_WRONLY | O_APPEND | O_CLOEXEC);\n  if (fd < 0) {\n    if ((errno != ENOENT) || mst_masters_present())", BASE),
    ("K50-drain-opens-journal-through-symlink", "masters.c", "  fd = open(jpath, O_RDWR | O_NOFOLLOW | O_CLOEXEC);\n  if (fd < 0) {\n    if (errno == ENOENT)\n      return MSA_NOTSET;",
     "  fd = open(jpath, O_RDWR | O_CLOEXEC);\n  if (fd < 0) {\n    if (errno == ENOENT)\n      return MSA_NOTSET;", BASE),
    ("K51-no-flock-in-drain", "masters.c", "  if (flock(fd, LOCK_EX) != 0) {\n    close(fd);\n    return MSA_ERR;\n  }", "  if (0) {\n    close(fd);\n    return MSA_ERR;\n  }", BASE),
    ("K57-dir-search-bit-not-needed", "masters.c", "(sb.st_mode & (S_IWGRP | S_IXGRP)) != (S_IWGRP | S_IXGRP))", "(sb.st_mode & (S_IWGRP)) != (S_IWGRP))", BASE),
    # ---- the guards the first two stages already had (the verifier's caught ones, kept as controls that the suite still catches them) ----
    ("K1-admin-check-removed", "masters.c", "  if ((my_uptr == NULL) || !(my_uptr->flags & USR_ADMIN))\n    return mst_refuse(MSG_NOTADMIN, keytxt, NULL, NULL);",
     "  if (0)\n    return mst_refuse(MSG_NOTADMIN, keytxt, NULL, NULL);", BASE),
    ("K41-write-check-removed", "masters.c", "  /* 3 can this process write the file?  Before a lock is taken or a byte is written */\n  why = mst_write_check(path, gname, sizeof(gname));\n  if (why != MST_W_OK) {\n    mst_ctx_close(&cx);\n    goto refuse_rights;\n  }",
     "  /* 3 mutant: not asked */\n  why = MST_W_OK;", BASE),
    ("K43-no-dh_write-of-account", "masters.c", "  wok = dh_write(adh, (char *)rid, (int16_t)rid_len, data);", "  wok = TRUE;", BASE),
    # ---- F1 the modes ----
    ("F1-master-files-open-to-the-group", "masters.c", "      if (chmod(dirpath, 0700) == 0)", "      if (chmod(dirpath, 0770) == 0)", "setup"),
    ("F1-master-subfiles-open-to-the-group", "masters.c", "        if (chmod(q, 0600) == 0)", "        if (chmod(q, 0660) == 0)", "setup"),
    # the files are made under umask 077 now, so the kernel's chmod matters only when the files are THERE already with the old modes: row A4d is what stands behind it
    ("F1-repair-dir-chmod-skipped", "masters.c", "      if (chmod(dirpath, 0700) == 0)\n        modes++;", "      if (0)\n        modes++;", "setup"),
    ("F1-repair-subfile-chmod-skipped", "masters.c", "        if (chmod(q, 0600) == 0)\n          modes++;", "        if (0)\n          modes++;", "setup"),
    # ---- F2 the freed table ----
    ("F2-pointer-into-the-account-table", "masters.c", "  if (!mst_acc_by_name(acct, &acc))\n    return mst_refuse(MSG_NOACCOUNT, keytxt, acct, NULL);\n",
     "  if (!mst_acc_by_name(acct, &acc))\n    return mst_refuse(MSG_NOACCOUNT, keytxt, acct, NULL);\n  a = &acc_tab[mst_acc_find(acct)]; /* the bug */\n", "setup,uaf"),
    # ---- F3 what the session read ----
    ("F3-judged-against-master-state", "masters.c", "  rd = mst_read_find(which, (const char *)id, id_len);", "  rd = NULL;", BASE),
    ("F3-blind-save-accepted", "masters.c", "    if (cks[0] != '\\0') /* not read, and the account has the record */\n      return mst_deliver_stop(&cx, &fv, took, rid, rid_len, MSG_NOTREAD, keytxt, NULL, NULL);\n", "", BASE),
    ("F3-read-not-noted", "op_dio3.c", "      if (!(dh_file->flags & DHF_MST_NOMASTER))\n        masters_note_read(dh_file, id, id_len, str, dh_err);\n", "", BASE),
    # ---- F4 the window ----
    ("F4-no-comparison-when-found", "dh_write.c", "        if (masters_cas_on) {\n          STRING_CHUNK* cas_cur", "        if (0) {\n          STRING_CHUNK* cas_cur", "setup,window"),
    ("F4-comparison-never-armed", "masters.c", "  masters_cas_on = 1;\n  wok = dh_write(", "  wok = dh_write(", "setup,window"),
    # ---- F5 / F6 ----
    ("F5-unlistable-directory-complete", "masters.c", "    closedir(d);\n  } else {\n    complete = FALSE;\n  }", "    closedir(d);\n  }", BASE),
    ("F5-prune-from-incomplete-list", "masters.c", "  if (dcomplete) {\n    MST_IDS gone", "  {\n    MST_IDS gone", BASE),
    ("F6-link-out-of-the-account-opened", "masters.c", "  if (!mst_inside_root(path, root, real, sizeof(real))) {\n    absent = TRUE;", "  if (0) {\n    absent = TRUE;", BASE),
    ("F6-linked-dictionary-scanned", "masters.c", "      if (!mst_inside_root(dpath, a->root, lreal, sizeof(lreal)))\n        continue; /* a link out of the account: another account's dictionary, or nobody's (verifier F6) */\n", "", BASE),
    # ---- F7 the scans ----
    ("F7-no-index-for-syncall", "masters.c", "      mst_ctx_index(&cx, TRUE);\n", "", "setup,scale"),
    ("F7-no-index-for-check", "masters.c", "        mst_ctx_index(&cx, FALSE); /* each master read once, not once per account (verifier F7) */\n", "", "setup,scale"),
    # ---- what the hook costs (the K2 row): 30 microseconds in the journal's append, and 40 in the hook before it knows whose file it is ----
    ("K2-journal-append-slowed", "masters.c", "  EndExclusive(ERRLOG_SEM);\n  close(fd);\n}", "  usleep(30);\n  EndExclusive(ERRLOG_SEM);\n  close(fd);\n}", "setup,perf"),
    ("K2-hook-slowed", "masters.c", "  kind = (dh->flags & DHF_MST_VOC) ? MST_VOC : MST_DICT;\n  if ((fd = mst_journal_open()) < 0) /* no journal: nothing more to do, and nothing worked out */\n    return;\n",
     "  kind = (dh->flags & DHF_MST_VOC) ? MST_VOC : MST_DICT;\n  usleep(40);\n  if ((fd = mst_journal_open()) < 0) /* no journal: nothing more to do, and nothing worked out */\n    return;\n", "setup,perf"),
    # ---- the small ones ----
    ("L-uppercase-key-not-retried", "masters.c", "  if ((adh == NULL) && cx.last_absent && (which == MST_DICT)) {", "  if (0) {", BASE),
    ("L-unterminated-line-not-ended", "masters.c", "        (void)pwrite(fd, \"\\n\", 1, st.st_size);", "        ;", BASE),
    ("C-control-no-op", "masters.c", "      consumed += (long)(nl - lstart) + 1;", "      consumed += (long)(nl - lstart) + 1; if (0) {}", BASE),   # a no-op: it MUST stay green
]


def sh(cmd, cwd=None, timeout=3000):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, errors="replace", timeout=timeout)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print("usage: mutate-masters.py <dir> [--build] [name,name,...]")
        return 2
    box = os.path.abspath(args[0])
    only = args[1].split(",") if len(args) > 1 else None
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            print("mutate-masters: CANNOT RUN - %s is not empty" % box)
            return 2
        r = sh([sys.executable, TOOL, box, "all"], timeout=1500)
        if r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            print("mutate-masters: CANNOT RUN - the sandbox build did not pass\n" + r.stdout[-600:])
            return 2
    if not os.path.isdir(os.path.join(box, "tree", "gplsrc")):
        print("mutate-masters: CANNOT RUN - %s holds no built sandbox with its own copy of the tree" % box)
        return 2
    print("mutate-masters: sandbox %s, keyset %s, tree under test %s" % (box, os.environ.get("SDBOX_KEYSET"), os.path.dirname(HERE)))

    def install():
        r = sh(["make"], cwd=os.path.join(box, "tree"))
        if r.returncode != 0:
            return False, (r.stdout + r.stderr)[-500:]
        sh([sys.executable, TOOL, box, "stop"], timeout=120)
        shutil.copy2(os.path.join(box, "tree", "bin", "sd"), os.path.join(box, "sys", "bin", "sd"))
        return True, ""

    def run_suite(sections):
        sh([sys.executable, TOOL, box, "stop"], timeout=120)
        r = sh([sys.executable, SUITE, box, "--sections=" + sections], timeout=3000)
        sh([sys.executable, TOOL, box, "stop"], timeout=120)
        out = r.stdout
        fails = [ln.strip() for ln in out.splitlines() if "[FAIL]" in ln]
        m = re.search(r"sandbox-masters: (\d+) passed, (\d+) failed", out)
        return (m.groups() if m else None), fails, out

    selected = [x for x in M if not only or x[0] in only or x[0].split("-")[0] in only]
    if not selected:
        print("mutate-masters: CANNOT RUN - no mutant is called %s" % args[1])
        return 2
    failures = 0
    controls = {}
    for sec in sorted({s for _, _, _, _, s in selected}, key=lambda s: -len(s)):       # one control for each set of sections the selected mutants use
        print("---- control (unmutated), sections %s" % sec)
        t0 = time.time()
        ok, why = install()
        if not ok:
            print("CANNOT RUN: the unmutated tree does not build\n" + why)
            return 2
        res, fails, out = run_suite(sec)
        print("CONTROL %s -> %s (%d s) failing rows: %s" % (sec, res, time.time() - t0, [f[:90] for f in fails[:3]]))
        controls[sec] = (res, fails)
        if res is None or res[1] != "0":
            print("CANNOT RUN: the control for sections %s is not green; no mutant that uses them means anything" % sec)
            return 2
    caught = survived = skipped = built_bad = 0
    for name, fname, old, new, sec in M:
        if only and name not in only and name.split("-")[0] not in only:
            continue
        path = os.path.join(box, "tree", "gplsrc", fname)
        text = open(path, encoding="latin-1").read()
        n = text.count(old)
        print("---- MUTANT %s  (%s, %d place(s) match, sections %s)" % (name, fname, n, sec))
        if n != 1:
            print("   SKIPPED - the text to change must match exactly once")
            skipped += 1
            continue
        open(path, "w", encoding="latin-1").write(text.replace(old, new))
        try:
            t0 = time.time()
            ok, why = install()
            if not ok:
                print("   BUILD FAILED: %s" % why)
                built_bad += 1
                continue
            res, fails, out = run_suite(sec)
        finally:
            open(path, "w", encoding="latin-1").write(text)
        noop = name.startswith("C-")
        # A run with no verdict line ("N passed, M failed") proved NOTHING: the suite stopped before it could judge anything (the first version of this file counted that as a
        # catch, and an F3 mutant that broke every read looked caught).  It is its own result, it fails the run, and it is not a catch.
        no_verdict = res is None
        is_caught = (not no_verdict) and res[1] != "0"
        if no_verdict:
            verdict = "NO VERDICT - THE SUITE DID NOT RUN TO THE END, NOTHING WAS PROVED"
            failures += 1
        elif noop:
            verdict = "GREEN (as it must)" if not is_caught else "RED - A NO-OP MUTANT FAILED THE SUITE, THE INSTRUMENT IS WRONG"
            if is_caught:
                failures += 1
        elif is_caught:
            verdict = "CAUGHT"
            caught += 1
        else:
            verdict = "SURVIVED"
            survived += 1
        print("   %s %s (%d s) failing rows: %s" % (verdict, res, time.time() - t0, [f[:100] for f in fails[:4]]))
        if res is None:
            print("   tail: " + " | ".join(out.splitlines()[-4:]))
    install()
    sh([sys.executable, TOOL, box, "stop"], timeout=120)
    print("\nmutate-masters: %d caught, %d SURVIVED, %d skipped, %d did not build, %d with no verdict or a no-op that failed" % (caught, survived, skipped, built_bad, failures))
    return 0 if (survived == 0 and skipped == 0 and built_bad == 0 and failures == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
