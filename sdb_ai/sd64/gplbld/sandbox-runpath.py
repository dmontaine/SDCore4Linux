#!/usr/bin/env python3
#
# sandbox-runpath.py - S.48: RUN of a runfile path over 128 characters, RUN
#                      rather than compiled, in a private sandbox SD.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-runpath.py --dir <empty scratch dir>
#   python3 .../sandbox-runpath.py --dir <dir> --keep      leave the sandbox built
#
# NO SUDO, AND NEVER THE LIVE SYSTEM.  Exit 0 every row passed on the new
# build AND the control refused as the old code must; 1 a row failed; 2 it
# could not run (or refused to).
#
# WHAT IT MEASURES
#   op_run() now takes a runfile path up to MAX_PATHNAME_LEN (255), and
#   load_object() keeps the tail of a name longer than the object header's
#   128 (SD Core Solo's SOLO 12).  A probe program is compiled, its object
#   copied into directories reached through VOC F-pointers, and RUN from:
#     R1  a 165-character path: the NEW build runs it (the probe's marker),
#         twice in one session - the second call goes through load_object's
#         cache with a truncated header name, which must reload, not misfire
#     R2  the same path on the CONTROL (the installed pre-change source):
#         refused with 10918 naming 128 - which is what shows R1 reached the
#         length check at all
#     R3  a path over 255: the NEW build refuses it cleanly and the session
#         carries on.  Measured: CPROC's readv of the record refuses first
#         ("Overflowed path/filename length in op_readv()!"), so 10918 is a
#         backstop RUN never reaches from CPROC; either wording passes.
# WHAT IT DOES NOT MEASURE
#   k_error's snprintf bound (the other half of S.48): an overrun needs a
#   message plus program name over 240 bytes and shows only as memory
#   corruption, which nothing here can observe.  It is read in the source.
#
# The sandbox machinery is sandbox-txnfail.py's, imported (keys
# 0x716d0901/0902, check_admin stubbed IN THE COPY ONLY, SD_CONFIG).

import argparse
import getpass
import importlib.util
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("sbx", os.path.join(HERE, "sandbox-txnfail.py"))
sbx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sbx)
say, die, ck = sbx.say, sbx.die, sbx.ck

PROBE = """* ZZRP - S.48 runfile-path probe
crt 'ZZRP RAN'
end
"""


def show(out):
    """Every line the session printed after the banner - the evidence each
    row below was judged on."""
    lines = [l.rstrip() for l in out.splitlines() if l.strip()]
    start = next((i for i, l in enumerate(lines) if l.startswith(":")), 0)
    for l in lines[start:]:
        say("      | " + l)


def voc_writer(name, target):
    return ('open "voc" to f else stop "ZZW: cannot open voc"\n'
            'r = "F" : @fm : "%s"\n'
            'write r to f, "%s"\n'
            'crt "ZZW wrote %s"\n'
            'end\n' % (target, name, name))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="an EMPTY or absent scratch directory")
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args()
    root = os.path.abspath(a.dir)
    user = getpass.getuser()
    live_acct = os.path.join("/home/sd/user_accounts", user)

    say("sandbox-runpath")
    say("  tree        : %s" % sbx.SD64)
    say("  sandbox     : %s" % root)
    say("  user        : %s (uid %d)" % (user, os.getuid()))
    before = sbx.ipcs_keys()
    say("  IPC keys before: %s" % " ".join(before))
    if os.getuid() == 0:
        die("sandbox-runpath: REFUSED - run it as an ordinary user.")
    if any(k in before for k in sbx.BOX_KEYS):
        die("sandbox-runpath: REFUSED - sandbox keys %s already exist." % " ".join(sbx.BOX_KEYS))
    if os.path.exists(root) and os.listdir(root):
        die("sandbox-runpath: REFUSED - %s is not empty." % root)
    with open(os.path.join(sbx.SD64, "gplsrc", "op_jumps.c")) as f:
        if "char runfile_name[MAX_PATHNAME_LEN + 1];" not in f.read():
            die("sandbox-runpath: CANNOT RUN - this tree's op_run() still has the 128 limit; nothing to test.")
    os.makedirs(root, exist_ok=True)

    box = sbx.Box(root, user)
    try:
        say("\n=== 1. build: the new tree, and the installed gplsrc as control")
        sbx.build(os.path.join(root, "new"), sbx.SANDBOX_PATCHES)
        ctl = os.path.join(root, "control")
        shutil.copytree(sbx.SD64, ctl, ignore=shutil.ignore_patterns("bin", "gplobj", "terminfo", "__pycache__", "gplsrc"))
        shutil.copytree(os.path.join(sbx.LIVE_SYS, "gplsrc"), os.path.join(ctl, "gplsrc"))
        with open(os.path.join(ctl, "gplsrc", "op_jumps.c")) as f:
            if "char runfile_name[MAX_PROGRAM_NAME_LEN + 1];" not in f.read():
                die("sandbox-runpath: CANNOT RUN - the installed gplsrc already lacks the 128 limit; no control.")
        os.makedirs(os.path.join(ctl, "bin"))
        os.makedirs(os.path.join(ctl, "gplobj"))
        for rel, old, new, label in sbx.SANDBOX_PATCHES:
            sbx.replace_once(os.path.join(ctl, rel), old, new, label)
        p = sbx.sh(["make"], cwd=ctl)
        if p.returncode != 0 or not os.path.exists(os.path.join(ctl, "bin", "sd")):
            say(p.stdout[-2000:] + p.stderr[-2000:])
            die("sandbox-runpath: CANNOT RUN - make failed for the control")
        say("    make exit 0, control bin/sd built")

        say("\n=== 2. the sandbox system and account")
        shutil.copytree(sbx.LIVE_SYS, box.sys, ignore=shutil.ignore_patterns("$cred", "audit", "dumps"))
        os.makedirs(os.path.join(box.sys, "$cred"))
        os.makedirs(os.path.join(box.sys, "dumps"))
        open(os.path.join(box.sys, "audit"), "w").close()
        for b in ("sd", "sdlnxd"):
            shutil.copy2(os.path.join(root, "new", "bin", b), os.path.join(box.sys, "bin", b))
        shutil.copytree(live_acct, box.acct, ignore=shutil.ignore_patterns("stacks"))
        reg = os.path.join(box.sys, "accounts")
        for r in os.listdir(reg):
            os.remove(os.path.join(reg, r))
        with open(os.path.join(reg, user), "w") as f:
            f.write("%s\n\nsdu_%s\n" % (box.acct, user))
        with open(os.path.join(reg, "sdsys"), "w") as f:
            f.write("%s\n\nsdsys\n" % box.sys)
        with open(box.conf, "w") as f:
            f.write("[sd]\nSDSYS=%s\nGRPSIZE=2\nNUMUSERS=20\nSORTMEM=4096\nERRLOG=50\nUSRDIR=%s\nGRPDIR=%s\nDUMPDIR=%s\n"
                    % (box.sys, os.path.dirname(box.acct), os.path.join(root, "groups"),
                       os.path.join(box.sys, "dumps")))
        box.start()
        after = sbx.ipcs_keys()
        say("  IPC keys after start: %s" % " ".join(after))
        ck("S0 the sandbox has its own keys and the live keys are untouched",
           all(k in after for k in sbx.BOX_KEYS) and all((k in after) == (k in before) for k in sbx.LIVE_KEYS))

        # Two deep directories.  Components stay under NAME_MAX (255).
        # R3's DIRECTORY must itself stay openable (<= 250: SD refuses a file
        # path over MAX_PATHNAME_LEN with "File ... not found" before RUN is
        # reached - measured, the first run of this script); the RECORD NAME
        # (<= MAXIDLEN 63) is what takes the run path past 255.
        mid = os.path.join(box.acct, "zzrp", "d" * 60, "e" * 60)
        base = os.path.join(box.acct, "zzrp") + os.sep
        long_ = base + "f" * (250 - len(base))
        long_rec = "zzrp" + "q" * 40
        bp = os.path.join(box.acct, "bp")
        with open(os.path.join(bp, "zzrp"), "w") as f:
            f.write(PROBE)
        with open(os.path.join(bp, "zzw1"), "w") as f:
            f.write(voc_writer("zzmid.out", mid))   # RUN ZZMID reads zzmid.out
        with open(os.path.join(bp, "zzw2"), "w") as f:
            f.write(voc_writer("zzlong.out", long_))
        out = box.session(os.path.join(box.sys, "bin", "sd"),
                          ["BASIC BP ZZRP ZZW1 ZZW2", "RUN BP zzw1", "RUN BP zzw2"])
        ck("S1 the three programs compiled", "Compiled 3 program(s) with no errors" in out)
        ck("S2 both VOC pointers were written", "ZZW wrote zzmid.out" in out and "ZZW wrote zzlong.out" in out)
        obj = os.path.join(box.acct, "bp.out", "zzrp")
        os.makedirs(mid)
        shutil.copy2(obj, os.path.join(mid, "zzrp"))
        os.makedirs(long_)
        shutil.copy2(obj, os.path.join(long_, long_rec))
        mid_len = len(os.path.join(mid, "zzrp"))
        long_len = len(os.path.join(long_, long_rec))
        say("  run path R1/R2: %d characters   R3: %d characters (directory %d, record %d)"
            % (mid_len, long_len, len(long_), len(long_rec)))
        if not (128 < mid_len <= 255 and long_len > 255 and len(long_) <= 250):
            die("sandbox-runpath: CANNOT RUN - path lengths %d/%d do not straddle 128 and 255" % (mid_len, long_len))

        say("\n=== 3. R1: the new build, %d characters, twice" % mid_len)
        box.stop(); box.start()
        out = box.session(os.path.join(box.sys, "bin", "sd"), ["RUN ZZMID zzrp", "RUN ZZMID zzrp"])
        show(out)
        ck("R1 the program ran from a %d-character path" % mid_len, out.count("ZZRP RAN") >= 1)
        ck("R1b and ran again from the cache path (two markers)", out.count("ZZRP RAN") == 2,
           "%d marker(s)" % out.count("ZZRP RAN"))
        ck("R1c no 10918", "Runfile pathname is longer than" not in out)

        say("\n=== 4. R2: the control, same path")
        box.stop(); box.start()
        out = box.session(os.path.join(ctl, "bin", "sd"), ["RUN ZZMID zzrp"])
        show(out)
        ck("R2 the old code refuses it with 10918 naming 128",
           "Runfile pathname is longer than 128 characters" in out and "ZZRP RAN" not in out)

        say("\n=== 5. R3: the new build, %d characters" % long_len)
        box.stop(); box.start()
        out = box.session(os.path.join(box.sys, "bin", "sd"), ["RUN ZZLONG " + long_rec, "WHO"])
        show(out)
        # MEASURED 29 Sep 26: CPROC reads the record from the file (readv)
        # BEFORE it calls RUN, and op_readv refuses a path over 255 with
        # "Overflowed path/filename length in op_readv()!" - so through RUN
        # the file layer is the effective limit and 10918 is a backstop.
        # Either clean refusal passes; running the program does not.
        ck("R3 over 255 is refused cleanly (op_readv's overflow, or 10918 naming 255)",
           ("Overflowed path/filename length" in out
            or "Runfile pathname is longer than 255 characters" in out)
           and "ZZRP RAN" not in out)
        ck("R3b not the old 1135", "Invalid runfile pathname" not in out)
        ck("R3c the file itself was found (the refusal is about length)", "not found" not in out)
        ck("R3d the session carried on (WHO answered)", "1 " + user in out)
    finally:
        box.stop()
        sbx.sh(["ipcrm", "-M", sbx.BOX_KEYS[0], "-S", sbx.BOX_KEYS[1]])
        say("\n  IPC keys after teardown: %s" % " ".join(sbx.ipcs_keys()))
        if not a.keep:
            shutil.rmtree(root, ignore_errors=True)

    say("\nsandbox-runpath: %d passed, %d failed" % (sbx.PASS, sbx.FAIL))
    if sbx.PASS == 0:
        say("sandbox-runpath: NOTHING WAS MEASURED - refusing to call that a pass")
        sys.exit(2)
    sys.exit(1 if sbx.FAIL else 0)


if __name__ == "__main__":
    main()
