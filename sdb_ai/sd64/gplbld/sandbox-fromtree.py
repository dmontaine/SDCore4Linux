#!/usr/bin/env python3
#
# sandbox-fromtree.py - a private SD built from THIS TREE, no install needed.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-fromtree.py <dir> all [--s50]
#   python3 .../sandbox-fromtree.py <dir> start | stop
#   python3 .../sandbox-fromtree.py <dir> sess <cwd> "<command>" ["<command>" ...]
#
# NO SUDO, AND NEVER THE LIVE SYSTEM.  Exit 0 done (for "all": every bootstrap
# pass reached its own success wording), 1 a pass did not, 2 could not run.
#
# START-HISTORY:
# 01 Oct 26 dm  Written for S.50, when there was no install on this machine to
#               copy: sandbox-txnfail.py's sandbox copies /usr/local/sdsys, this
#               one replays installsdai.sh's assembly and its bootstrap passes
#               (sd -i, SECOND.COMPILE, write_install_dicts, THIRD.COMPILE) on a
#               copy of the tree.  Its first real use found the bootstrap break
#               S.50's LOGIN change caused - and that sd exited 0 through it.
# END-HISTORY
#
# WHAT IT CHANGES, IN THE COPY ONLY (each must match exactly once, or it refuses):
#   sandbox-txnfail.py's SANDBOX_PATCHES - IPC keys 0x53434C91/92 (live is
#     0x53434C01/02; SD Core for Linux Solo's are 0x53434C11/12, and an older
#     Solo still on 0x716d0301/02: never touched) and check_admin() stubbed;
#   pcode_bld.py's hard-coded /usr/local/sdsys -> the sandbox's sys;
#   the root tests in cproc (install arm), bbproc and write_install_dicts take
#     the invoking user's uid; that user plays sdsys in cproc; LOGIN's sdusers
#     gate is off (there is no sdusers group here).
#   --s50: every "sudo /usr/local/sbin/sd-elevate" in gpl.bp, and accos.h's two
#     commands, point at <dir>/elevate-shim and the tree's own sd-accarchive.
#     The shim runs the tree's REAL sd-elevate with --dry-run first, so every
#     argument check is the real one, then acts without root where it can
#     (tree-count, backup-pack, restore-place without the chown, akpath-set)
#     and only PRETENDS user and group management, which needs root.
#
# THE INSTRUMENT.  Each bootstrap pass is judged on the wording it prints only
# when it worked: pass 1 no "Errors in compile"; SECOND.COMPILE "Compiled N
# program(s) with no errors"; write_install_dicts "COMPLETE"; and none of them
# "Unable to load".  sd's exit status is printed but never trusted: it is 0
# through a pass that failed (measured 1 Oct 2026, and S.48 before it).

import argparse
import getpass
import importlib.util
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.dirname(HERE)
_spec = importlib.util.spec_from_file_location("sbx", os.path.join(HERE, "sandbox-txnfail.py"))
sbx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sbx)

UID = os.getuid()
USER = getpass.getuser()
ELEVATE = "sudo /usr/local/sbin/sd-elevate"

SHIM = r'''#!/bin/bash
# sandbox stand-in for "sudo /usr/local/sbin/sd-elevate" (sandbox-fromtree.py --s50)
REAL=%(tree)s/gplbld/sd-elevate
ARCH=%(tree)s/gplbld/sd-accarchive
SDIDX=%(sys)s/bin/sdidx
export SD_ACCT_ROOT=%(root)s
verb=${1:-}
if [[ $verb == backup-pack ]]; then
  bash "$REAL" --dry-run "$@" || exit $?
  shift
  exec python3 "$ARCH" pack "$@"
fi
if ! out=$(bash "$REAL" --dry-run "$@" 2>&1); then
  printf '%%s\n' "$out"
  exit 2
fi
case $verb in
  tree-count) exec python3 "$ARCH" count "$2" ;;
  restore-place)
    stage=$(dirname "$(dirname "$4")")
    old=$stage/old.$(basename "$5")
    mv -T -- "$5" "$old" || exit 3
    mv -T -- "$4" "$5" || { mv -T -- "$old" "$5"; exit 3; }
    rm -rf -- "$old"
    echo "sd-elevate: restored $5 ($2:$3) [sandbox: no chown]" ;;
  akpath-set)
    "$SDIDX" -p "$2" "$3" >/dev/null 2>&1
    q=$("$SDIDX" -q "$2" 2>&1)
    if [[ $q == *"Index directory is $3"* ]]; then echo "sd-elevate: index path of $2 is now $3"
    else printf '%%s\n' "$q"; exit 2; fi ;;
  *) echo "sd-elevate (sandbox): checked, pretended: $*" ;;
esac
'''


def run(env, cmd, cwd=None, timeout=900):
    sbx.say("> %s (cwd %s)" % (" ".join(cmd), cwd))
    p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    out = sbx.ANSI.sub("", p.stdout + p.stderr)
    sbx.say(out[-2500:])
    sbx.say("exit %d" % p.returncode)
    return p.returncode, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("step", choices=["all", "build", "assemble", "boot", "start", "stop", "sess"])
    ap.add_argument("rest", nargs="*")
    ap.add_argument("--s50", action="store_true", help="point sd-elevate and the archiver at stand-ins")
    a = ap.parse_args()
    root = os.path.abspath(a.dir)
    tree, sysd, conf = os.path.join(root, "tree"), os.path.join(root, "sys"), os.path.join(root, "sd.conf")
    env = dict(os.environ, SD_CONFIG=conf)
    if UID == 0:
        sbx.die("sandbox-fromtree: REFUSED - run it as an ordinary user")
    box = sbx.Box(root, USER)
    box.sys, box.conf = sysd, conf

    if a.step in ("all", "build"):
        if os.path.exists(root) and os.listdir(root):
            sbx.die("sandbox-fromtree: REFUSED - %s is not empty" % root)
        if any(k in sbx.ipcs_keys() for k in sbx.BOX_KEYS):
            sbx.die("sandbox-fromtree: REFUSED - sandbox keys %s exist; stop the old sandbox first" % " ".join(sbx.BOX_KEYS))
        os.makedirs(root, exist_ok=True)
        sbx.build(tree, sbx.SANDBOX_PATCHES + [
            ("gplbld/pcode_bld.py", "SDSYS = '/usr/local/sdsys'", "SDSYS = %r" % sysd, "pcode_bld sdsys")])

    if a.step in ("all", "assemble"):
        patches = [
            ("sdsys/gpl.bp/cproc", "      if system(27) = 0 then           ;* entered as root?\n",
             "$ifdef IS_INSTALL\n      if system(27) = %d then\n$else\n      if system(27) = 0 then           ;* entered as root?\n$endif\n" % UID,
             "install arm grants the sandbox uid"),
            ("sdsys/gpl.bp/cproc", "if downcase(kernel(K$USERNAME, 0)) = 'sdsys' and",
             "if downcase(kernel(K$USERNAME, 0)) = '%s' and" % USER, "the sandbox user plays sdsys"),
            ("sdsys/gpl.bp/cproc", "if kernel(K$LOGIN.UID, 'sdsys') = 1 then", "if 1 then", "no sdsys login uid"),
            ("sdsys/gpl.bp/bbproc", "if system(27) # 0 then", "if system(27) # %d then" % UID, "bootstrap uid"),
            ("sdsys/gpl.bp/login", "if  not(is_grp_member(lgn.id,'sdusers')) then", "if @false then", "no sdusers group"),
            ("sdsys/gpl.bp/write_install_dicts", "IF SYSTEM(27) # 0 THEN", "IF SYSTEM(27) # %d THEN" % UID, "pass 3 uid"),
        ]
        for rel, old, new, label in patches:
            sbx.replace_once(os.path.join(tree, rel), old, new, "sandbox: " + label)
        if a.s50:
            shim = os.path.join(root, "elevate-shim")
            with open(shim, "w") as f:
                f.write(SHIM % {"tree": tree, "sys": sysd, "root": root})
            os.chmod(shim, 0o755)
            n = 0
            gpl = os.path.join(tree, "sdsys", "gpl.bp")
            for name in sorted(os.listdir(gpl)):
                p = os.path.join(gpl, name)
                txt = open(p, encoding="latin-1").read()
                if ELEVATE in txt:
                    open(p, "w", encoding="latin-1").write(txt.replace(ELEVATE, "bash " + shim))
                    n += txt.count(ELEVATE)
            sbx.replace_once(os.path.join(tree, "sdsys", "syscom", "accos.h"),
                             "'%s'" % ELEVATE, "'bash %s'" % shim, "s50: accos.h elevate -> shim")
            sbx.replace_once(os.path.join(tree, "sdsys", "syscom", "accos.h"),
                             "'python3 /usr/local/sbin/sd-accarchive'",
                             "'python3 %s'" % os.path.join(tree, "gplbld", "sd-accarchive"), "s50: accos.h archiver")
            sbx.say("    --s50: %d sd-elevate call sites in gpl.bp now run %s" % (n, shim))
        shutil.copytree(os.path.join(tree, "sdsys"), sysd)
        open(os.path.join(sysd, "gcat", "$CPROC"), "w").close()
        open(os.path.join(sysd, "errlog"), "w").close()
        for d in ("bin", "gplsrc", "gplobj", "terminfo"):
            if os.path.isdir(os.path.join(tree, d)):
                shutil.copytree(os.path.join(tree, d), os.path.join(sysd, d), dirs_exist_ok=True)
        os.makedirs(os.path.join(sysd, "gplbld"), exist_ok=True)
        shutil.copytree(os.path.join(tree, "gplbld", "FILES_DICTS"), os.path.join(sysd, "gplbld", "FILES_DICTS"))
        for src in ("bbproc", "bcomp", "pathtkn"):
            rc, out = run(env, ["python3", "gplbld/bbcmp.py", sysd, "gpl.bp/" + src, "gpl.bp.out/" + src], cwd=tree)
            if rc != 0:
                sbx.die("sandbox-fromtree: CANNOT RUN - bbcmp of %s failed" % src)
        run(env, ["python3", "gplbld/pcode_bld.py"], cwd=tree)
        for f in ("Makefile", "gpl.src", "terminfo.src"):
            shutil.copy2(os.path.join(tree, f), sysd)
        shutil.copytree(os.path.join(tree, "gplbld", "microcfg"), os.path.join(sysd, "microcfg"))
        for d in ("dumps", "$cred", "batch.jobs"):
            os.makedirs(os.path.join(sysd, d), exist_ok=True)
        with open(os.path.join(sysd, "accounts", "sdsys"), "w") as f:
            f.write("%s\n\nsdsys\n" % sysd)
        for d in ("user_accounts", "group_accounts"):
            os.makedirs(os.path.join(root, d), exist_ok=True)
        with open(conf, "w") as f:
            f.write("[sd]\nSDSYS=%s\nGRPSIZE=2\nNUMUSERS=20\nSORTMEM=4096\nERRLOG=50\nUSRDIR=%s\nGRPDIR=%s\nDUMPDIR=%s\n"
                    % (sysd, os.path.join(root, "user_accounts"), os.path.join(root, "group_accounts"),
                       os.path.join(sysd, "dumps")))

    if a.step in ("all", "boot"):
        sd = os.path.join(sysd, "bin", "sd")
        box.start()
        verdicts = []
        try:
            rc, out = run(env, [sd, "-i"], cwd=sysd)
            verdicts.append(("pass 1 (sd -i)", "Errors in compile" not in out and "Unable to load" not in out
                             and "0 error(s)" in out))
            rc, out = run(env, [sd, "-internal", "SECOND.COMPILE"], cwd=sysd)
            m = re.search(r"Compiled (\d+) program\(s\) with no errors", out)
            verdicts.append(("pass 2 (SECOND.COMPILE) %s" % (m.group(0) if m else "- no success line"),
                             m is not None and "Unable to load" not in out))
            rc, out = run(env, [sd, "RUN", "gpl.bp", "write_install_dicts", "NO.PAGE"], cwd=sysd)
            verdicts.append(("pass 3 (write_install_dicts)", re.search(r"^COMPLETE$", out, re.M) is not None
                             and "Unable to load" not in out))
            rc, out = run(env, [sd, "THIRD.COMPILE"], cwd=sysd)
            verdicts.append(("THIRD.COMPILE", "Unable to load" not in out and "rror" not in out))
        finally:
            box.stop()
        sbx.say("\nbootstrap verdicts:")
        for label, ok in verdicts:
            sbx.say("  [%s] %s" % ("PASS" if ok else "FAIL", label))
        if not all(ok for _, ok in verdicts):
            return 1

    if a.step == "start":
        box.start()
    if a.step == "stop":
        box.stop()
    if a.step == "sess":
        if len(a.rest) < 2:
            sbx.die("sandbox-fromtree: sess needs <cwd> and at least one command")
        body = "\nTERM 200,9999\n" + "".join(l + "\n" for l in a.rest[1:]) + "OFF\n"
        p = subprocess.run([os.path.join(sysd, "bin", "sd")], input=body, cwd=a.rest[0], env=env,
                           capture_output=True, text=True, timeout=600)
        sbx.say(sbx.ANSI.sub("", p.stdout + p.stderr))
        sbx.say("exit %d" % p.returncode)
    return 0


if __name__ == "__main__":
    sys.exit(main())
