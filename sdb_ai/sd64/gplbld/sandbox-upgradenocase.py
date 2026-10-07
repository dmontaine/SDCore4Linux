#!/usr/bin/env python3
#
# sandbox-upgradenocase.py - the upgrade walk: an installed account's case-sensitive files are made
# case insensitive, a file holding a fold-pair is left whole and named, and the private catalogue's
# names are made lower case.  RELEASE_1.1 5 D2 and PAL-1 stage 3a (the Linux form of the Windows port's
# verify-nocaseupgrade.ps1).
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-upgradenocase.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (a private SD built from a tree, no sudo, its own IPC keys:
# never the live system).  With --build the sandbox is built first from THIS tree; <dir> must then be empty
# or absent.  Fixture names are unique to the run, and the register records are removed at the end.
#
# Exit 0 every row passed, 1 a row failed, 2 it could not run (the fixture is not what the rows assume).
#
# THE FIXTURE, built before the walk and read back before it runs (a fixture that was never made would let
# every "unchanged" row pass over nothing):
#   account zzacct  a USER account owned by the user running this script (sdu_<user>), with
#     voc          a case-sensitive VOC holding the F-records ZZD1 and ZZD2 (upper-case ids)
#     zzd1(.dic)   case-sensitive, ids Alpha, beta, GAMMA - no pair: must convert, keeping every record
#     zzd2(.dic)   case-sensitive, ids jack AND JACK - a fold-pair: must be left whole and named
#     cat/         ZZSUB1 and Mixed (to be made lower case), zzsub2 (already), ZZPAIR beside zzpair (both kept)
#   account zzgrp   a GROUP account whose Linux group does not exist  -> skipped, 11028
#   account zzusr   a USER account whose Linux user does not exist     -> skipped, 11029
#   account zzoth   neither a user nor a group account                  -> skipped, 11028
#
# THE LEGS.  CHECK first (a null case: it must change NOTHING and still name the twin and the cat renames),
# then the real run, then a second real run (it must have nothing left to convert).  The walk acts as each
# account's owner (!euid_set); a sandbox cannot be root, so the owner here is the invoking user, which an
# ordinary process may switch to.  What a root install adds - files made as ANOTHER user - is the one thing
# this cannot measure; witness-upgradenocase.sh is the owner-run row for it.

import getpass
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
RUN = "%05d" % (os.getpid() % 100000)
USER = getpass.getuser()
# --solo: run SD Core for Linux Solo's version of the walk (its own gpl.bp/upgrade_nocase and messages
# 11060-11063, no owner switching: one user) inside this full-product sandbox.  The kernel is the full
# product's, which is the same C for everything the walk does; a Solo kernel sandbox does not exist (LSOLO 40).
SOLO = "--solo" in sys.argv
SOLO_SDSYS = "/home/don/Projects/SDCore4LinuxSolo/sdb_ai/sd64/sdsys"
A, G, U, O = "zzacct" + RUN, "zzgrp" + RUN, "zzusr" + RUN, "zzoth" + RUN
FIX, RD = "zzfix" + RUN, "zzrd" + RUN
passed = failed = 0


def say(s=""):
    print(s)


def row(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        say("  [PASS] " + name)
    else:
        failed += 1
        say("  [FAIL] " + name + ("   <- " + detail if detail else ""))


def bail(msg):
    say("sandbox-upgradenocase: CANNOT RUN - " + msg)
    sys.exit(2)


def isess(box, *cmds):
    say("    > [sd -internal] " + " | ".join(cmds))
    env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"))
    body = "\nTERM 200,9999\n" + "".join(c + "\n" for c in cmds) + "OFF\n"
    p = subprocess.run([os.path.join(box, "sys", "bin", "sd"), "-internal"], input=body, cwd=os.path.join(box, "sys"),
                       env=env, capture_output=True, text=True, errors="replace", timeout=600)
    out = ANSI.sub("", p.stdout + p.stderr)
    out = re.sub(r"\[[0-9;]*[A-Za-z]", "", out.split(":TERM 200,9999", 1)[-1])
    for line in out.splitlines():
        if line.strip() and not line.startswith(":") and not line.startswith("exit ") and not line.startswith("sd: SANDBOX"):
            say("      | " + line.rstrip()[:140])
    return out


def write_text(path, lines):
    with open(path, "wb") as f:
        f.write(("\n".join(lines) + "\n").encode("ascii"))


def reg(box, name, path, group):
    write_text(os.path.join(box, "sys", "accounts", name), [path, "", group])


def stat_of(path):
    st = os.stat(path)
    return (st.st_uid, st.st_gid, st.st_mode & 0o777)


def readback(box, acct):
    """{file: {'nocase': flag, 'ids': sorted stored ids} | 'missing'} and the fold probe line, from RD."""
    out = isess(box, "RUN bp " + RD)
    d = {}
    for m in re.finditer(r"(?m)^RD (\S+) nocase=(\S+) n=(\d+) ids=(.*)$", out):
        d[m.group(1)] = {"nocase": m.group(2), "n": int(m.group(3)),
                         "ids": sorted(x for x in m.group(4).strip().split(",") if x)}
    for m in re.finditer(r"(?m)^RD (\S+) missing", out):
        d[m.group(1)] = "missing"
    f = re.search(r"(?m)^RD fold alpha=(.*)$", out)
    return d, (f.group(1).strip() if f else None), out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-upgradenocase.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    acct = os.path.join(box, "user_accounts", A)
    say("sandbox-upgradenocase: sandbox  %s" % box)
    say("sandbox-upgradenocase: tree     %s" % os.path.dirname(HERE))
    say("sandbox-upgradenocase: user     %s (the account's owner; also the walk's owner switch)" % USER)
    say("sandbox-upgradenocase: accounts %s (converted) %s (group, no group) %s (user, no such user) %s (other)" % (A, G, U, O))
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-upgradenocase: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    if not os.path.isfile(os.path.join(sysd, "gpl.bp", "upgrade_nocase")):
        bail("this tree has no gpl.bp/upgrade_nocase")
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)
    if SOLO:
        say("sandbox-upgradenocase: SOLO MODE - Solo's upgrade_nocase and messages 11060-11063 replace the full product's in this sandbox")
        for rel in ("gpl.bp/upgrade_nocase",) + tuple("messages/%d" % n for n in range(11060, 11064)):
            src = os.path.join(SOLO_SDSYS, rel)
            if not os.path.isfile(src):
                bail("Solo has no %s" % src)
            shutil.copyfile(src, os.path.join(sysd, rel))
        out = isess(box, "BASIC gpl.bp upgrade_nocase")
        if not re.search(r"(?m)^Compiled 1 program\(s\) with no errors", out):
            bail("Solo's upgrade_nocase did not compile in the sandbox")

    created = []

    def cleanup():
        for n in (A, G, U, O):
            p = os.path.join(sysd, "accounts", n)
            if os.path.exists(p):
                os.remove(p)
        for p in (acct,):
            if os.path.isdir(p):
                shutil.rmtree(p)
        for rec in (FIX, RD):
            for d in ("bp", "bp.out"):
                p = os.path.join(sysd, d, rec)
                if os.path.exists(p):
                    os.remove(p)

    try:
        say("\n--- the fixture ------------------------------------------------------------------")
        cleanup()
        os.makedirs(os.path.join(acct, "cat"))
        created.append(acct)
        # register: path, description, group (ACC$PATH, ACC$DESCR, ACC$GROUP)
        reg(box, A, acct, "sdu_" + USER)
        reg(box, G, os.path.join(box, "group_accounts", G), "sdg_" + G)
        reg(box, U, os.path.join(box, "user_accounts", U), "sdu_zznouser" + RUN)
        reg(box, O, os.path.join(box, "user_accounts", O), "zzother" + RUN)
        for name, body in (("ZZSUB1", b"obj1"), ("Mixed", b"obj2"), ("zzsub2", b"obj3"), ("ZZPAIR", b"upper"), ("zzpair", b"lower")):
            with open(os.path.join(acct, "cat", name), "wb") as f:
                f.write(body)
        # the fixture builder: case-sensitive files can only be made in internal mode (KEEPCASE, flags 4)
        write_text(os.path.join(sysd, "bp", FIX), [
            "   acct = '%s'" % acct,
            "   nm = 'voc':@fm:'zzd1':@fm:'zzd1.dic':@fm:'zzd2':@fm:'zzd2.dic'",
            "   for i = 1 to 5",
            "      create.file acct:'/':nm<i> dynamic flags 4 on error crt 'FIX create failed ':nm<i> ; stop",
            "   next i",
            "   openpath acct:'/zzd1' to f1 else crt 'FIX no zzd1' ; stop",
            "   write 'one' to f1, 'Alpha' ; write 'two' to f1, 'beta' ; write 'three' to f1, 'GAMMA'",
            "   openpath acct:'/zzd2' to f2 else crt 'FIX no zzd2' ; stop",
            "   write 'x' to f2, 'jack' ; write 'y' to f2, 'JACK' ; write 'z' to f2, 'solo'",
            "   openpath acct:'/voc' to v else crt 'FIX no voc' ; stop",
            "   write 'F':@fm:'zzd1':@fm:'zzd1.dic' to v, 'ZZD1'",
            "   write 'F':@fm:'zzd2':@fm:'zzd2.dic' to v, 'ZZD2'",
            "   crt 'FIX done'", "end"])
        write_text(os.path.join(sysd, "bp", RD), [
            "$internal",             # select list 11 is for an $internal program only
            "$include keys.h",
            "   acct = '%s'" % acct,
            "   nm = 'voc':@fm:'zzd1':@fm:'zzd1.dic':@fm:'zzd2':@fm:'zzd2.dic'",
            "   for i = 1 to 5",
            "      openpath acct:'/':nm<i> to f then",
            "         ids = ''",
            "         select f to 11",
            "         loop",
            "            readnext id from 11 else exit",
            "            ids<-1> = id",
            "         repeat",
            "         crt 'RD ':nm<i>:' nocase=':fileinfo(f, FL$NOCASE):' n=':dcount(ids, @fm):' ids=':convert(@fm, ',', ids)",
            "         close f",
            "      end else",
            "         crt 'RD ':nm<i>:' missing'",
            "      end",
            "   next i",
            "   openpath acct:'/zzd1' to f then",
            "      read r from f, 'ALPHA' then crt 'RD fold alpha=':r else crt 'RD fold alpha=none'",
            "   end",
            "end"])
        out = isess(box, "BASIC bp " + FIX, "BASIC bp " + RD, "RUN bp " + FIX)
        clean = len(re.findall(r"(?m)^Compiled 1 program\(s\) with no errors", out))
        row("setup: both probe programs compiled with no errors", clean == 2, "clean compiles: %d of 2" % clean)
        row("setup: the fixture builder finished", re.search(r"(?m)^FIX done\s*$", out) is not None, "no 'FIX done'")
        if clean != 2 or "FIX done" not in out:
            bail("the fixture was not built")
        before, fold0, _ = readback(box, acct)
        say("    fixture read back: %s" % before)
        ok = all(isinstance(before.get(k), dict) for k in ("voc", "zzd1", "zzd1.dic", "zzd2", "zzd2.dic"))
        row("setup: all five files exist and are readable", ok, repr(before))
        row("setup: every one of them is case SENSITIVE (flag 0) - KEEPCASE worked", ok and all(v["nocase"] == "0" for v in before.values()),
            repr(before))
        row("setup: zzd1 holds Alpha, beta, GAMMA; zzd2 holds jack, JACK, solo",
            ok and before["zzd1"]["ids"] == ["Alpha", "GAMMA", "beta"] and before["zzd2"]["ids"] == ["JACK", "jack", "solo"],
            repr(before.get("zzd1")) + repr(before.get("zzd2")))
        row("setup: the fold probe finds nothing (ALPHA is not the stored spelling)", fold0 == "none", repr(fold0))
        if failed:
            bail("the fixture is not what the rows assume")
        cat0 = sorted(os.listdir(os.path.join(acct, "cat")))
        mark = {p: stat_of(p) for p in (os.path.join(acct, "zzd1", "%0"), os.path.join(acct, "zzd1", "%1"))}
        sysmark = os.stat(os.path.join(sysd, "voc", "%0")).st_mtime_ns

        say("\n--- leg 1: CHECK - reads, converts nothing, still names the twin and the cat renames ---")
        out = isess(box, "RUN gpl.bp upgrade_nocase CHECK")
        row("1: it ran to the end (COMPLETE)", re.search(r"(?m)^COMPLETE\s*$", out) is not None, "no COMPLETE")
        row("1: it walked the fixture account (Account %s)" % A, ("Account " + A) in out, "no 'Account' line")
        row("1: it named the twinned file, zzd2, and the pair jack and JACK",
            "zzd2" in out and re.search(r"jack / JACK|JACK / jack", out) is not None, "no twin report for zzd2")
        row("1: it did NOT name zzd1 as a twin", not re.search(r"File: \S*/zzd1\b", out), "zzd1 reported")
        row("1: it said 2 catalogue names would be made lower case", "2 private catalogue name(s) in" in out and "would be made lower case" in out,
            "no 11031 line with 2")
        row("1: it named both pairs of cat that cannot be renamed (ZZPAIR / zzpair)", "'ZZPAIR' and 'zzpair' both exist" in out, "no 11032 line")
        if SOLO:
            row("1 (Solo): every registered account is walked and none is skipped (there is no owner to switch to)",
                all(("Account " + x) in out for x in (G, U, O)) and "skipped" not in out and "not converted" not in out,
                "a skip line, or an account not walked")
        else:
            row("1: the group account with no Linux group was skipped with the helper's words (11035, 11021)",
                ("Account %s was skipped: its operating-system details could not be read. Cannot read the Linux group sdg_%s" % (G, G)) in out,
                "no 11035 line for %s" % G)
            row("1: the account that is neither user nor group was skipped (11028)",
                out.count("Account %s was skipped: it is neither a user nor a group account" % O) == 1, "no 11028 line for %s" % O)
            row("1: CHECK switches no owner, so the missing-user account is NOT skipped in CHECK (no 11029)",
                "this session cannot act as its owner" not in out, "an owner switch was attempted in CHECK")
            row("1: the two skips were counted", "2 account(s) were not converted" in out, "no 11033 line with 2")
        after, fold1, _ = readback(box, acct)
        row("1: CHECK changed nothing: every file is still case sensitive", after == before, repr(after))
        row("1: CHECK renamed nothing in cat/", sorted(os.listdir(os.path.join(acct, "cat"))) == cat0, repr(sorted(os.listdir(os.path.join(acct, "cat")))))

        say("\n--- leg 2: the real run ---------------------------------------------------------")
        out = isess(box, "RUN gpl.bp upgrade_nocase")
        row("2: it ran to the end (COMPLETE)", re.search(r"(?m)^COMPLETE\s*$", out) is not None, "no COMPLETE")
        after, fold2, _ = readback(box, acct)
        say("    read back after: %s" % after)
        row("2: zzd1 is now case insensitive (flag 1)", after.get("zzd1", {}).get("nocase") == "1", repr(after.get("zzd1")))
        row("2: and it kept all three records, stored as they were (Alpha, beta, GAMMA)",
            after.get("zzd1", {}).get("ids") == ["Alpha", "GAMMA", "beta"], repr(after.get("zzd1")))
        row("2: a record is now found under another case (ALPHA reads 'one')", fold2 == "one", repr(fold2))
        row("2: the dictionary part zzd1.dic converted too", after.get("zzd1.dic", {}).get("nocase") == "1", repr(after.get("zzd1.dic")))
        row("2: the VOC converted, last, and kept ZZD1 and ZZD2",
            after.get("voc", {}).get("nocase") == "1" and after["voc"]["ids"] == ["ZZD1", "ZZD2"], repr(after.get("voc")))
        row("2: THE TWIN FILE WAS LEFT WHOLE: zzd2 is still case sensitive with jack, JACK and solo",
            after.get("zzd2", {}).get("nocase") == "0" and after["zzd2"]["ids"] == ["JACK", "jack", "solo"], repr(after.get("zzd2")))
        row("2: the report names the twin (WARNING line, then the file and the pair)",
            "WARNING: 1 file(s) hold 1 record id(s) that differ only by case" in out and re.search(r"jack / JACK|JACK / jack", out) is not None,
            "no WARNING for zzd2")
        row("2: the summary says 4 of 5 files converted (voc, zzd1, zzd1.dic, zzd2.dic)", "Converted 4 of 5 file(s)" in out, "summary differs")
        row("2: cat/ is ZZSUB1 and Mixed renamed lower, the pair and zzsub2 untouched",
            sorted(os.listdir(os.path.join(acct, "cat"))) == sorted(["zzsub1", "mixed", "zzsub2", "ZZPAIR", "zzpair"]),
            repr(sorted(os.listdir(os.path.join(acct, "cat")))))
        row("2: the renamed catalogue files kept their bytes",
            open(os.path.join(acct, "cat", "zzsub1"), "rb").read() == b"obj1" if os.path.exists(os.path.join(acct, "cat", "zzsub1")) else False)
        row("2: both of a catalogue pair survive, each with its own bytes",
            open(os.path.join(acct, "cat", "ZZPAIR"), "rb").read() == b"upper" and open(os.path.join(acct, "cat", "zzpair"), "rb").read() == b"lower")
        if SOLO:
            row("2 (Solo): every registered account is walked and none is skipped",
                all(("Account " + x) in out for x in (A, G, U, O)) and "skipped" not in out and "not converted" not in out,
                "a skip line, or an account not walked")
        else:
            row("2: the owner switch was refused for the missing user (11029), once",
                out.count("Account %s was skipped: this session cannot act as its owner, zznouser%s" % (U, RUN)) == 1, "no 11029 line for %s" % U)
            row("2: and the other two skips are as in CHECK (11028 once, 11035 once)",
                out.count("neither a user nor a group account") == 1 and out.count("operating-system details could not be read") == 1,
                "wrong skip lines")
        row("2: a catalogue pair is a warning, not a failure (no 'could not be read or rebuilt' line)",
            "could not be read or rebuilt" not in out, "the pair was counted as an error")
        if not SOLO:
            row("2: and the skips were counted (3 account(s) were not converted)", "3 account(s) were not converted" in out, "no 11033 line")
        owner_ok = all(stat_of(p) [:2] == mark[p][:2] for p in mark if os.path.exists(p))
        row("2: the rebuilt file belongs to the same owner and group as the one it replaced", owner_ok,
            "before %r after %r" % (mark, {p: stat_of(p) for p in mark if os.path.exists(p)}))
        modes = [stat_of(os.path.join(acct, "zzd1", n))[2] for n in ("%0", "%1") if os.path.exists(os.path.join(acct, "zzd1", n))]
        if SOLO:
            row("2 (Solo): the rebuilt file has the mode of the one it replaced (the user's own umask; Solo sets none)",
                bool(modes) and all(stat_of(p)[2] == mark[p][2] for p in mark if os.path.exists(p)),
                "before %r after %r" % ({p: oct(m[2]) for p, m in mark.items()}, {p: oct(stat_of(p)[2]) for p in mark if os.path.exists(p)}))
        else:
            row("2: the rebuilt file is group writable (mode 664 under the walk's umask 002)", bool(modes) and all(m == 0o664 for m in modes), repr([oct(m) for m in modes]))
        row("2: SDSYS was not touched (its voc is unchanged)", os.stat(os.path.join(sysd, "voc", "%0")).st_mtime_ns == sysmark,
            "sys/voc/%0 was rewritten")

        say("\n--- leg 3: a second real run has nothing left to convert -------------------------")
        out = isess(box, "RUN gpl.bp upgrade_nocase")
        row("3: it ran to the end (COMPLETE)", re.search(r"(?m)^COMPLETE\s*$", out) is not None, "no COMPLETE")
        row("3: nothing more was converted (Converted 0 of 5)", "Converted 0 of 5 file(s)" in out, "summary differs")
        row("3: the twin is still reported, and still left whole", "WARNING: 1 file(s) hold 1 record id(s)" in out, "no WARNING")
        again, _, _ = readback(box, acct)
        row("3: the files read back as after leg 2", again == after, repr(again))
    finally:
        say("\n--- cleanup ------------------------------------------------------------------")
        cleanup()
        left = [n for n in (A, G, U, O) if os.path.exists(os.path.join(sysd, "accounts", n))]
        row("cleanup: no register record and no fixture account is left", not left and not os.path.exists(acct), " ".join(left))

    say("\nsandbox-upgradenocase: %d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        bail("no row ran - a broken test, not a pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
