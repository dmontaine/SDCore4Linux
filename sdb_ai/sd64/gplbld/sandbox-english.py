#!/usr/bin/env python3
#
# sandbox-english.py - S.46: the English-only removal's C half, RUN rather
#                      than compiled, in a private sandbox SD.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-english.py --dir <empty scratch dir>
#   python3 .../sandbox-english.py --dir <dir> --keep      leave the sandbox built
#
# NO SUDO, AND NEVER THE LIVE SYSTEM.  Exit 0 every row passed on the new
# build AND on the control; 1 a row failed; 2 it could not run (or refused to).
#
# WHAT IT MEASURES
#   load_language("") became init_messages() (messages.c, sd.c), and sysmsg()
#   lost its language-prefix lookup.  Both run at every start-up, so a slip
#   there stops SD starting or garbles every message and date.  Each row runs
#   on the NEW build and on the CONTROL - the installed /usr/local/sdsys/bin/sd,
#   which predates the change - in the same sandbox, and must read the same:
#     E1  a session starts and runs a cataloged program (the probe's marker)
#     E2  sysmsg(1500) is the English month list, not "[1500] Message not found"
#     E3  sysmsg(1501) is the English day list
#     E4  OCONV(0,'DMA') is DECEMBER and OCONV(0,'DWA') SUNDAY (day 0 is
#         Sunday 31 Dec 1967): the tables init_messages builds
#     E5  a message the C side raises reads as text: an unknown verb
# WHAT IT DOES NOT MEASURE
#   - that K$SET.LANGUAGE (38) is refused: KERNEL() compiles only in internal
#     mode, and the retirement is visible in op_kernel.c's switch.
#   - that SETLANG/LOADLANG/NLS are gone from the catalog: the sandbox copies
#     the INSTALLED sdsys, which still has them.  That needs an install
#     (witness-absence.sh), not this.
#
# The sandbox machinery (keys 0x716d0901/0902, check_admin stubbed IN THE COPY
# ONLY, SD_CONFIG, the sdlnxd kill) is sandbox-txnfail.py's, imported.

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

MONTHS = "January,February,March,April,May,June,July,August,September,October,November,December"
DAYS = "Monday,Tuesday,Wednesday,Thursday,Friday,Saturday,Sunday"

PROBE = """* ZZENG - S.46 English-only probe
crt 'ZZENG START'
crt 'ZZENG M=':sysmsg(1500)
crt 'ZZENG D=':sysmsg(1501)
crt 'ZZENG DMA=':oconv(0, 'DMA')
crt 'ZZENG DWA=':oconv(0, 'DWA')
crt 'ZZENG END'
end
"""


def rows(label, out):
    lines = [l for l in out.splitlines() if l.startswith("ZZENG") or "zznoverb" in l.lower()]
    for l in lines:
        say("      | " + l)
    ck("E1 %s: the probe ran start to end" % label, "ZZENG START" in out and "ZZENG END" in out)
    ck("E2 %s: sysmsg(1500) is the English month list" % label,
       ("ZZENG M=" + MONTHS) in out and "[1500]" not in out)
    ck("E3 %s: sysmsg(1501) is the English day list" % label,
       ("ZZENG D=" + DAYS) in out and "[1501]" not in out)
    ck("E4 %s: OCONV DMA/DWA give DECEMBER/SUNDAY" % label,
       "ZZENG DMA=DECEMBER" in out.upper() and "ZZENG DWA=SUNDAY" in out.upper())
    # Anchored on the message's own wording: ":ZZNOVERB" is the echoed command
    # and appears on the failure path too.
    verb = [l for l in out.splitlines() if "ZZNOVERB is not in your VOC" in l]
    ck("E5 %s: an unknown verb's message is text, not a missing-message stub" % label,
       bool(verb) and not any("message not found" in l.lower() or "message file not found" in l.lower()
                              for l in out.splitlines()),
       verb[0].strip() if verb else "no 'ZZNOVERB is not in your VOC' line")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="an EMPTY or absent scratch directory")
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args()
    root = os.path.abspath(a.dir)
    user = getpass.getuser()
    live_acct = os.path.join("/home/sd/user_accounts", user)
    control = os.path.join(sbx.LIVE_SYS, "bin", "sd")

    say("sandbox-english")
    say("  tree        : %s" % sbx.SD64)
    say("  sandbox     : %s" % root)
    say("  user        : %s (uid %d)" % (user, os.getuid()))
    say("  account copy: %s" % live_acct)
    say("  control     : %s (the installed, pre-change binary)" % control)
    before = sbx.ipcs_keys()
    say("  IPC keys before: %s" % " ".join(before))
    if os.getuid() == 0:
        die("sandbox-english: REFUSED - run it as an ordinary user; root would reach the live system's files.")
    if any(k in before for k in sbx.BOX_KEYS):
        die("sandbox-english: REFUSED - sandbox keys %s already exist; tear the old sandbox down first."
            % " ".join(sbx.BOX_KEYS))
    if os.path.exists(root) and os.listdir(root):
        die("sandbox-english: REFUSED - %s is not empty." % root)
    if not os.path.isdir(live_acct) or not os.path.isfile(control):
        die("sandbox-english: CANNOT RUN - %s or %s is missing." % (live_acct, control))
    with open(os.path.join(sbx.SD64, "gplsrc", "messages.c")) as f:
        if "bool init_messages(void)" not in f.read():
            die("sandbox-english: CANNOT RUN - this tree's messages.c has no init_messages(); nothing to test.")
    os.makedirs(root, exist_ok=True)

    box = sbx.Box(root, user)
    try:
        say("\n=== 1. build: the new tree, sandbox keys")
        sbx.build(os.path.join(root, "new"), sbx.SANDBOX_PATCHES)
        say("\n=== 1b. build: the control, the installed gplsrc with sandbox keys")
        ctl = os.path.join(root, "control")
        shutil.copytree(sbx.SD64, ctl, ignore=shutil.ignore_patterns("bin", "gplobj", "terminfo", "__pycache__", "gplsrc"))
        shutil.copytree(os.path.join(sbx.LIVE_SYS, "gplsrc"), os.path.join(ctl, "gplsrc"))
        with open(os.path.join(ctl, "gplsrc", "messages.c")) as f:
            if "load_language" not in f.read():
                die("sandbox-english: CANNOT RUN - the installed gplsrc already lacks load_language; no control.")
        os.makedirs(os.path.join(ctl, "bin"))
        os.makedirs(os.path.join(ctl, "gplobj"))
        for rel, old, new, label in sbx.SANDBOX_PATCHES:
            sbx.replace_once(os.path.join(ctl, rel), old, new, label)
        p = sbx.sh(["make"], cwd=ctl)
        if p.returncode != 0 or not os.path.exists(os.path.join(ctl, "bin", "sd")):
            say(p.stdout[-2000:] + p.stderr[-2000:])
            die("sandbox-english: CANNOT RUN - make failed for the control")
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

        new = os.path.join(box.sys, "bin", "sd")
        with open(os.path.join(box.acct, "bp", "zzeng"), "w") as f:
            f.write(PROBE)
        out = box.session(new, ["BASIC BP ZZENG", "CATALOG BP zzeng LOCAL"])
        ck("S1 the probe compiled", "Compiled 1 program(s) with no errors" in out)

        for label, binary in (("new", new), ("control", os.path.join(ctl, "bin", "sd"))):
            say("\n=== 3. %s: %s" % (label, os.path.relpath(binary, root)))
            box.stop(); box.start()
            out = box.session(binary, ["ZZENG", "ZZNOVERB"])
            rows(label, out)
    finally:
        box.stop()
        sbx.sh(["ipcrm", "-M", sbx.BOX_KEYS[0], "-S", sbx.BOX_KEYS[1]])
        say("\n  IPC keys after teardown: %s" % " ".join(sbx.ipcs_keys()))
        if not a.keep:
            shutil.rmtree(root, ignore_errors=True)

    say("\nsandbox-english: %d passed, %d failed" % (sbx.PASS, sbx.FAIL))
    if sbx.PASS == 0:
        say("sandbox-english: NOTHING WAS MEASURED - refusing to call that a pass")
        sys.exit(2)
    sys.exit(1 if sbx.FAIL else 0)


if __name__ == "__main__":
    main()
