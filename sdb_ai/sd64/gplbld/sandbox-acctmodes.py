#!/usr/bin/env python3
#
# sandbox-acctmodes.py - S.96 M6: the modes the kernel gives a NEW VOC or dictionary in a registered account (dh_creat.c acct_group_modes).  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-acctmodes.py <dir> [--build] [--only=SECTIONS] [--mutant=NAME]
#
# <dir> is a sandbox made by sandbox-fromtree.py (a SHORT path under /tmp).  With --build it is built first from THIS tree (it must be empty or absent).  Exit 0 every row
# that was asked passed, 1 a row failed, 2 it could not run - and 2 when NO row was asked (every one SKIPPED): a run that measured nothing is not a pass.  The script stops
# the sandbox at the end; remove the directory afterwards.  SDBOX_KEYSET chooses the pair of shared memory keys, as for every suite.
#
# SECTIONS (--only=a,b; the build, the kernel step and the fixtures of a section always run):
#   group    C1 the UMASK verb takes effect (control); G1 a dictionary under UMASK 022 is 2775 / 664 / 664; G2 the data file beside it is not touched; G3 under UMASK 027
#            only the group bits are added (2770 / 660 / 660)
#   nowrite  W1 an account whose directory the group cannot write (2755): nothing is added
#   nogroup  N1 an account whose directory's group does not hold the sdsys user: nothing is added
#   voc      V1 a new VOC in a registered account is 2775 / 664 / 664; V1c the same in a directory whose group does not hold the sdsys user is 755 / 644 (control)
#   nested   P1 / P1c an inner account 2775 inside an outer 2755: the inner's dictionary is judged by the INNER directory (group write), the outer's by the outer (none);
#            P2 / P2c the reverse (inner 2755 inside outer 2775)
#
# START-HISTORY:
# 2 Nov 26 dm   Written for S.96 M6.  The master-file copies were retired that day with sandbox-masters.py, whose rows M30b, M30c, M31, M31a, M32 and M33 were the only
#               RUNTIME test of the rule that a new VOC or dictionary is made group-writable in an account; the rule moved into dh_creat.c as acct_group_modes()
#               (acct_root_for_path() reads the account register, acct_sdsys_in_group() the sdsys user's groups) and had not been run since.  The free check holding
#               it as text is test-sdsysaccess-units.py (S17g, S18, S18a-d).  New here: the VOC row and the nested accounts (the NEAREST registered account decides).
# END-HISTORY
#
# THE INSTRUMENT.  Every verdict is a mode read from the disk with os.lstat - never SD's words.  The UMASK verb is the first line of each session, because cproc gives
# every session umask 002 at sign-on, which would make 775 / 664 whatever the kernel did; C1 shows the verb takes effect.  Each row prints the modes it read, and the
# fixture prints the account directory's mode and group BEFORE the session.  The dictionaries are made by ORDINARY sessions (`sd -a<account>`, sandbox-gates.py's
# helpers; the sandbox user plays SDSYS only with SDTEST_ADMIN=1).  The accounts are REGISTERED (<sys>/accounts/<name>, line 1 the path), so the kernel's
# acct_root_for_path finds them.  A new VOC is made by an administrator's internal program running CREATE.FILE <path>/voc (the statement CREATE.ACCOUNT's helper uses;
# CREATE.ACCOUNT itself makes Linux users and cannot run in a sandbox).
#
# THE SDSYS USER.  The kernel adds group write only where the sdsys user is in the group of the account's directory (F6, C2), and always on a machine with no sdsys
# user.  So the suite needs a group the sdsys user is in AND the sandbox user is in (chgrp needs nothing more) for the group rows, and a group the sandbox user is in
# that does NOT hold the sdsys user for the nogroup rows.  Where it has neither it says SKIPPED with the reason; a SKIPPED row is not counted as passed.
#
# --mutant=NAME  changes the SANDBOX's own copy of dh_creat.c (<dir>/tree/gplsrc), runs make there and puts the new bin/sd in <dir>/sys/bin; a run without a mutant
# puts the pristine source back (kept as <dir>/dh_creat.c.pristine at the first run) and rebuilds when the copy differs, so one sandbox serves every run:
#   no-call     the call of acct_group_modes() after a file is made is taken out          (red: G1 G3 V1 P1 P2c)
#   outer-wins  the nearest-account test is inverted, the OUTERMOST registered account wins  (red: P1 P2)

import grp
import hashlib
import importlib.util
import os
import pwd
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
sys.path.insert(0, HERE)

_spec = importlib.util.spec_from_file_location("sandbox_gates_for_acctmodes", os.path.join(HERE, "sandbox-gates.py"))
g = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(g)

SECTIONS = ["group", "nowrite", "nogroup", "voc", "nested"]

MUTANTS = {
    "no-call": ("  acct_group_modes(path);\n\nexit_dh_create_file:",
                "  if (0) acct_group_modes(path);  /* MUTANT no-call */\n\nexit_dh_create_file:",
                ["G1", "G3", "V1", "P1", "P2c"]),
    "outer-wins": ("(n >= rootsz) || (n <= best))",
                   "(n >= rootsz) || ((best != 0) && (n >= best)))  /* MUTANT outer-wins */",
                   ["P1", "P2"]),
}

passed = failed = skipped = 0
FAILED_IDS = []
ASKED = []


def say(s=""):
    print(s, flush=True)


def row(rid, name, ok, detail=""):
    global passed, failed
    ASKED.append(rid)
    if ok:
        passed += 1
        say("  [PASS] %s: %s   (%s)" % (rid, name, detail))
    else:
        failed += 1
        FAILED_IDS.append(rid)
        say("  [FAIL] %s: %s   <- %s" % (rid, name, detail))


def skip(rid, why):
    global skipped
    skipped += 1
    say("  SKIPPED %s: %s" % (rid, why))


def bail(msg):
    say("sandbox-acctmodes: CANNOT RUN - " + msg)
    sys.exit(2)


def mode_of(p):
    try:
        return os.lstat(p).st_mode & 0o7777
    except OSError:
        return None


def modes(base, subs=("", "/%0", "/%1")):
    """the modes of a file directory and its subfiles, for the row's detail: '2775 664 664', 'absent' where there is nothing"""
    return [mode_of(base + s) for s in subs]


def show(ms):
    return " ".join("absent" if m is None else "%04o" % m for m in ms)


def want(ms, d, f, mask=0o7777):
    """the directory mode D (under MASK) and every subfile F - a file that is absent fails"""
    return None not in ms and (ms[0] & mask) == d and all(m == f for m in ms[1:])


# ---------------------------------------------------------------------------------------------------------------------
# the kernel: the sandbox's own copy of dh_creat.c, pristine or with one mutant

def kernel_step(box, mutant):
    tree = os.path.join(box, "tree")
    src = os.path.join(tree, "gplsrc", "dh_creat.c")
    keep = os.path.join(box, "dh_creat.c.pristine")
    if not os.path.isfile(src):
        bail("%s is not there: the sandbox has no tree to rebuild" % src)
    if not os.path.isfile(keep):
        shutil.copy2(src, keep)
    with open(keep, encoding="utf-8") as f:
        text = f.read()
    if mutant:
        old, new, _ = MUTANTS[mutant]
        if text.count(old) != 1:
            bail("the mutant %s does not match the pristine dh_creat.c exactly once (%d)" % (mutant, text.count(old)))
        text = text.replace(old, new)
    with open(src, encoding="utf-8") as f:
        now = f.read()
    if now == text:
        say("kernel: <dir>/tree/gplsrc/dh_creat.c is already %s; no rebuild" % (("mutant " + mutant) if mutant else "pristine"))
    else:
        with open(src, "w", encoding="utf-8") as f:
            f.write(text)
        say("kernel: <dir>/tree/gplsrc/dh_creat.c made %s; make in %s" % (("mutant " + mutant) if mutant else "pristine", tree))
        p = subprocess.run(["make"], cwd=tree, capture_output=True, text=True, errors="replace", timeout=900)
        if p.returncode != 0:
            bail("make failed in %s:\n%s" % (tree, (p.stdout + p.stderr)[-1500:]))
        tmp = os.path.join(box, "sys", "bin", "sd.new")
        shutil.copy2(os.path.join(tree, "bin", "sd"), tmp)
        os.replace(tmp, os.path.join(box, "sys", "bin", "sd"))
    a = hashlib.sha256(open(os.path.join(tree, "bin", "sd"), "rb").read()).hexdigest()[:16]
    b = hashlib.sha256(open(os.path.join(box, "sys", "bin", "sd"), "rb").read()).hexdigest()[:16]
    say("kernel: tree bin/sd %s, sandbox sys/bin/sd %s%s" % (a, b, "" if a == b else "   <- DIFFERENT"))
    if a != b:
        bail("the sandbox's sd is not the one just built")
    with open(src, encoding="utf-8") as f:
        live = f.read()
    marker = "/* MUTANT "
    if (marker in live) != bool(mutant):
        bail("the kernel source does not say what this run asked for (mutant %s)" % mutant)


# ---------------------------------------------------------------------------------------------------------------------
# fixtures

def mkacct(name, path, dmode, gid):
    """a registered account at PATH: its VOC copied from newvoc by an administrator's internal program, registered, then its directory given GID and DMODE"""
    if os.path.isdir(path):
        shutil.rmtree(path)
    os.makedirs(path)
    g.put(os.path.join(g.SYS, "bp", "zzamk"), "\n".join([
        "$internal",
        "   acct = '%s'" % path,
        "   create.file acct:'/voc' dynamic on error crt 'AMK create voc failed' ; stop",
        "   openpath acct:'/voc' to v else crt 'AMK open voc failed' ; stop",
        "   openpath '%s/newvoc' to nv else crt 'AMK no newvoc' ; stop" % g.SYS,
        "   select nv to 11",
        "   loop",
        "      readnext id from 11 else exit",
        "      read rec from nv, id then write rec to v, id",
        "   repeat",
        "   write 'X' to v, '$command.stack'",
        "   crt 'AMK done %s'" % name,
        "end", ""]))
    out = g.adm(["BASIC bp zzamk", "RUN bp zzamk"], internal=True)
    if not g.has(out, r"^AMK done " + name + "$"):
        bail("the fixture account %s was not built:\n%s" % (name, "\n".join(out[-6:])))
    g.reg_write(name, [path, "", g.GROUP, "", "", "", "no", "no"])
    os.chown(path, -1, gid)
    os.chmod(path, dmode)
    st = os.stat(path)
    say("    fixture %s: %s, mode %04o, group %d (%s), registered" % (name, os.path.relpath(path, g.BOX), st.st_mode & 0o7777, st.st_gid, grname(st.st_gid)))
    if (st.st_mode & 0o7777) != dmode or st.st_gid != gid:
        bail("the fixture %s did not take mode %04o and group %d" % (name, dmode, gid))


def grname(gid):
    try:
        return grp.getgrgid(gid).gr_name
    except KeyError:
        return "?"


def plain(name, path, cmds):
    out = g.sd(path, cmds, account=name)
    return out


def ua(*parts):
    return os.path.join(g.BOX, "user_accounts", *parts)


# ---------------------------------------------------------------------------------------------------------------------
# the sections

def sec_group(G_YES, why_yes):
    say("\n--- group: a dictionary in an account whose directory the group may write and whose group holds the sdsys user --------------------------")
    p = ua("amg")
    mkacct("amg", p, 0o2775, G_YES if G_YES is not None else os.getgid())
    out = plain("amg", p, ["UMASK 022", "CREATE.FILE amf1 DYNAMIC", "UMASK 027", "CREATE.FILE amf3 DYNAMIC"])
    d1, d3 = modes(os.path.join(p, "amf1")), modes(os.path.join(p, "amf3"))
    row("C1", "(control) the UMASK verb takes effect: the data file made under UMASK 022 is 755 / 644, under 027 750 / 640 (directory permission bits; it may carry the setgid bit it inherits)",
        want(d1, 0o755, 0o644, 0o777) and want(d3, 0o750, 0o640, 0o777), "amf1 %s, amf3 %s; session %r" % (show(d1), show(d3), out[-3:]))
    if G_YES is None:
        for r in ("G1", "G2", "G3"):
            skip(r, why_yes)
        return
    k1, k3 = modes(os.path.join(p, "amf1.dic")), modes(os.path.join(p, "amf3.dic"))
    row("G1", "a dictionary made by an ordinary session under UMASK 022 is group-writable: directory 2775 (setgid), %0 and %1 664", want(k1, 0o2775, 0o664), "amf1.dic %s" % show(k1))
    row("G2", "the DATA file beside it is not touched: 755 / 644 / 644 as the umask made it", want(d1, 0o755, 0o644, 0o777) and not any(m & 0o020 for m in d1 if m is not None),
        "amf1 %s" % show(d1))
    row("G3", "under UMASK 027 only the GROUP bits are added, the other bits stay clear: directory 2770, %0 and %1 660", want(k3, 0o2770, 0o660), "amf3.dic %s" % show(k3))


def sec_nowrite(G_YES, why_yes):
    say("\n--- nowrite: the account's directory is 2755 (the group may not write) ------------------------------------------------------------------")
    if G_YES is None:
        skip("W1", why_yes + " (and with the sdsys user in no usable group nothing would be added for that reason instead)")
        return
    p = ua("amw")
    mkacct("amw", p, 0o2755, G_YES)
    out = plain("amw", p, ["UMASK 022", "CREATE.FILE amf2 DYNAMIC"])
    k = modes(os.path.join(p, "amf2.dic"))
    row("W1", "where the account's directory is not group-writable nothing is added: the dictionary is 755 / 644 / 644 (permission bits) as the umask made it",
        want(k, 0o755, 0o644, 0o777), "amf2.dic %s; session %r" % (show(k), out[-2:]))


def sec_nogroup(G_NO, why_no):
    say("\n--- nogroup: the account directory's group does not hold the sdsys user --------------------------------------------------------------")
    if G_NO is None:
        skip("N1", why_no)
        return
    p = ua("amn")
    mkacct("amn", p, 0o2775, G_NO)
    out = plain("amn", p, ["UMASK 022", "CREATE.FILE amf4 DYNAMIC"])
    k = modes(os.path.join(p, "amf4.dic"))
    row("N1", "the sdsys user exists and is not in the group of the account's directory (gid %d): nothing is added, 755 / 644 / 644 (permission bits)" % G_NO,
        want(k, 0o755, 0o644, 0o777), "amf4.dic %s; session %r" % (show(k), out[-2:]))


def sec_voc(G_YES, why_yes, G_NO, why_no):
    say("\n--- voc: a NEW VOC made in a registered account (CREATE.FILE <path>/voc by an administrator's internal program, under UMASK 022) --------")
    cases = []
    if G_YES is None:
        skip("V1", why_yes)
    else:
        cases.append(("V1", "amv", G_YES))
    if G_NO is None:
        skip("V1c", why_no)
    else:
        cases.append(("V1c", "amvn", G_NO))
    for rid, name, gid in cases:
        p = ua(name)
        if os.path.isdir(p):
            shutil.rmtree(p)
        os.makedirs(p)
        g.reg_write(name, [p, "", g.GROUP, "", "", "", "no", "no"])      # registered BEFORE the VOC is made, as CREATE.ACCOUNT registers an account
        os.chown(p, -1, gid)
        os.chmod(p, 0o2775)
        st = os.stat(p)
        say("    fixture %s: %s, mode %04o, group %d (%s), registered, no VOC yet: %s" % (name, os.path.relpath(p, g.BOX), st.st_mode & 0o7777, st.st_gid, grname(st.st_gid),
                                                                             not os.path.exists(os.path.join(p, "voc"))))
        g.put(os.path.join(g.SYS, "bp", "zzamv"), "\n".join([
            "$internal",
            "   create.file '%s/voc' dynamic on error crt 'AMV failed status=':status() ; stop" % p,
            "   crt 'AMV made %s'" % name,
            "end", ""]))
        out = g.adm(["UMASK 022", "BASIC bp zzamv", "RUN bp zzamv"], internal=True)
        k = modes(os.path.join(p, "voc"))
        if rid == "V1":
            row("V1", "a new VOC in a registered account whose directory (2775) has a group holding the sdsys user: directory 2775, %0 and %1 664", want(k, 0o2775, 0o664),
                "voc %s; program %r" % (show(k), out[-2:]))
        else:
            row("V1c", "(control) the same in a directory whose group (gid %d) does not hold the sdsys user: 755 / 644 / 644 (permission bits) - the umask 022 really applied" % gid,
                want(k, 0o755, 0o644, 0o777), "voc %s; program %r" % (show(k), out[-2:]))


def sec_nested(G_YES, why_yes):
    say("\n--- nested: two registered accounts, one directory inside the other - the NEAREST account decides ----------------------------------")
    if G_YES is None:
        for r in ("P1", "P1c", "P2", "P2c"):
            skip(r, why_yes)
        return
    # P1: outer 2755, inner 2775
    po, pi = ua("amo"), ua("amo", "ami")
    mkacct("amo", po, 0o2775, G_YES)        # writable while the inner one is made inside it, then closed below
    mkacct("ami", pi, 0o2775, G_YES)
    os.chmod(po, 0o2755)
    say("    fixture amo now %04o" % mode_of(po))
    o1 = plain("ami", pi, ["UMASK 022", "CREATE.FILE amfi DYNAMIC"])
    o2 = plain("amo", po, ["UMASK 022", "CREATE.FILE amfo DYNAMIC"])
    ki, ko = modes(os.path.join(pi, "amfi.dic")), modes(os.path.join(po, "amfo.dic"))
    row("P1", "inner account 2775 inside an outer 2755: the inner's new dictionary is judged by the INNER directory - 2775 / 664 / 664", want(ki, 0o2775, 0o664),
        "ami/amfi.dic %s; session %r" % (show(ki), o1[-2:]))
    row("P1c", "(control) the outer account's own new dictionary gets nothing: 755 / 644 / 644 (permission bits)", want(ko, 0o755, 0o644, 0o777),
        "amo/amfo.dic %s; session %r" % (show(ko), o2[-2:]))
    # P2: outer 2775, inner 2755
    po, pi = ua("amp"), ua("amp", "amq")
    mkacct("amp", po, 0o2775, G_YES)
    mkacct("amq", pi, 0o2755, G_YES)
    o1 = plain("amq", pi, ["UMASK 022", "CREATE.FILE amfq DYNAMIC"])
    o2 = plain("amp", po, ["UMASK 022", "CREATE.FILE amfp DYNAMIC"])
    ki, ko = modes(os.path.join(pi, "amfq.dic")), modes(os.path.join(po, "amfp.dic"))
    row("P2", "inner account 2755 inside an outer 2775: the inner's new dictionary is judged by the INNER directory - nothing added, 755 / 644 / 644 (permission bits)",
        want(ki, 0o755, 0o644, 0o777), "amp/amq/amfq.dic %s; session %r" % (show(ki), o1[-2:]))
    row("P2c", "(control) the outer account's own new dictionary is group-writable: 2775 / 664 / 664", want(ko, 0o2775, 0o664),
        "amp/amfp.dic %s; session %r" % (show(ko), o2[-2:]))


# ---------------------------------------------------------------------------------------------------------------------

def groups():
    """(G_YES, why, G_NO, why): a group of the sandbox user the sdsys user is in, and one it is not in - as acct_sdsys_in_group() decides"""
    mine = sorted(set(os.getgroups()) | {os.getgid()})
    try:
        sd_pw = pwd.getpwnam("sdsys")
    except KeyError:
        sd_pw = None
    if sd_pw is None:
        say("sdsys user: none on this machine - the kernel adds group write in every group; the nogroup rows cannot be asked")
        return os.getgid(), "", None, "there is no sdsys user on this machine, and then acct_sdsys_in_group() is TRUE for every group"

    def holds(gid):
        if sd_pw.pw_gid == gid:
            return True
        try:
            return "sdsys" in grp.getgrgid(gid).gr_mem
        except KeyError:
            return False
    yes = [x for x in mine if holds(x)]
    no = [x for x in mine if not holds(x)]
    say("sdsys user: uid %d, primary gid %d; the sandbox user's groups %s; holding sdsys %s, not %s" % (sd_pw.pw_uid, sd_pw.pw_gid, mine, yes, no))
    gy = (sd_pw.pw_gid if sd_pw.pw_gid in yes else (yes[0] if yes else None))
    gn = (os.getgid() if os.getgid() in no else (no[0] if no else None))
    return (gy, "no group of the sandbox user holds the sdsys user (its primary gid %d; the sandbox user's groups %s), so no fixture directory can be given one" % (sd_pw.pw_gid, mine),
            gn, "every group of the sandbox user holds the sdsys user, so no fixture directory can be given a group without it")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-acctmodes.py <dir> [--build] [--only=SECTIONS] [--mutant=NAME]")
    only, mutant = list(SECTIONS), None
    for a in sys.argv[1:]:
        if a.startswith("--only="):
            only = [s for s in a.split("=", 1)[1].split(",") if s]
            bad = [s for s in only if s not in SECTIONS]
            if bad or not only:
                bail("unknown section(s) %s (known: %s)" % (bad, ", ".join(SECTIONS)))
        elif a.startswith("--mutant="):
            mutant = a.split("=", 1)[1]
            if mutant not in MUTANTS:
                bail("unknown mutant %r (known: %s)" % (mutant, ", ".join(MUTANTS)))
        elif a.startswith("--") and a != "--build":
            bail("unknown option %s" % a)
    g.BOX = os.path.abspath(args[0])
    g.SYS = os.path.join(g.BOX, "sys")
    g.SD = os.path.join(g.SYS, "bin", "sd")
    say("sandbox-acctmodes: sandbox %s, keyset %s, user %s (group %s), sections %s, mutant %s" % (g.BOX, os.environ.get("SDBOX_KEYSET", "0"), g.USER, g.GROUP,
                                                                                               ",".join(only), mutant or "none"))
    if os.getuid() == 0:
        bail("run it as an ordinary user")
    if "--build" in sys.argv:
        if os.path.exists(g.BOX) and os.listdir(g.BOX):
            bail("%s is not empty" % g.BOX)
        r = subprocess.run([sys.executable, TOOL, g.BOX, "all"], capture_output=True, text=True, errors="replace", timeout=1800)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-acctmodes: built, bootstrap passed")
    elif not os.path.isfile(g.SD):
        bail("%s holds no built sandbox (use --build, or point it at one)" % g.BOX)
    subprocess.run([sys.executable, TOOL, g.BOX, "stop"], capture_output=True, text=True, errors="replace", timeout=120)
    kernel_step(g.BOX, mutant)
    subprocess.run([sys.executable, TOOL, g.BOX, "start"], capture_output=True, text=True, errors="replace", timeout=120)
    try:
        G_YES, why_yes, G_NO, why_no = groups()
        say("group for the group rows: %s; group for the nogroup rows: %s" % (G_YES if G_YES is not None else "NONE", G_NO if G_NO is not None else "NONE"))
        g.prepare()
        if "group" in only:
            sec_group(G_YES, why_yes)
        if "nowrite" in only:
            sec_nowrite(G_YES, why_yes)
        if "nogroup" in only:
            sec_nogroup(G_NO, why_no)
        if "voc" in only:
            sec_voc(G_YES, why_yes, G_NO, why_no)
        if "nested" in only:
            sec_nested(G_YES, why_yes)
    finally:
        subprocess.run([sys.executable, TOOL, g.BOX, "stop"], capture_output=True, text=True, errors="replace", timeout=120)
        say("\nsandbox stopped (%s)" % g.BOX)
    if mutant:
        exp = [r for r in MUTANTS[mutant][2] if r in ASKED]     # the rows of the mutant this run asked (--only, SKIPPED)
        say("mutant %s: failed rows %s, expected %s: %s" % (mutant, FAILED_IDS, exp, "CAUGHT EXACTLY BY ITS ROWS" if sorted(FAILED_IDS) == sorted(exp)
                                                             else ("caught, but not by exactly its rows" if FAILED_IDS else "NOT CAUGHT")))
    say("%d skipped (not counted)" % skipped)
    say("%d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        say("sandbox-acctmodes: NO ROW WAS ASKED - refusing the null case")
        return 2
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
