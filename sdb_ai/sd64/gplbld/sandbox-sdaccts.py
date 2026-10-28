#!/usr/bin/env python3
#
# sandbox-sdaccts.py - the SD.ACCOUNTS gate (QM4 gap 22, the owner's third gate).  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-sdaccts.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty
# or absent); without it <dir> must already be built.  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 16 Oct 26 dm  New.  Register field 9 (ACC$SD.ACCOUNTS), K_SD_ACCOUNTS 118, USR_SD_ACCOUNTS; LOGIN, CPROC's logto and the API
#               server load it; op_sh.c os_path_ok_for_account() asks path_in_enterable_account(); MODIFY.ACCOUNT SD-ON / SD-OFF.
# END-HISTORY
#
# It uses sandbox-gates.py's way of making ordinary sessions in fixture accounts, by loading that file.  Accounts: zzoff (the gate
# off), zzgate (on), the targets zzon (the user's group, so enterable), zznolog (a group the user is not in) and zzsusp (suspended).
# Each target holds data.json; a program in the caller opens each one by a relative pathname and prints what it read.  THE
# INSTRUMENT.  A verdict is the word the program printed for that pathname, and the controls are the same program in the caller
# without the gate, a path in no account at all, the caller's own files, and the administrator.  The VOC rows open the target's
# voc and the caller's own.

import grp
import importlib.util
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("sandbox_gates", os.path.join(HERE, "sandbox-gates.py"))
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
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
    say("sandbox-sdaccts: CANNOT RUN - " + msg)
    sys.exit(2)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-sdaccts.py <dir> [--build]")
    g.BOX = os.path.abspath(args[0])
    g.SYS = os.path.join(g.BOX, "sys")
    g.SD = os.path.join(g.SYS, "bin", "sd")
    say("sandbox-sdaccts: sandbox %s" % g.BOX)
    if "--build" in sys.argv:
        if os.path.exists(g.BOX) and os.listdir(g.BOX):
            bail("%s is not empty" % g.BOX)
        r = subprocess.run([sys.executable, g.TOOL, g.BOX, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-sdaccts: built, bootstrap passed")
    elif not os.path.isfile(g.SD):
        bail("%s holds no built sandbox (use --build, or point it at one)" % g.BOX)
    subprocess.run([sys.executable, g.TOOL, g.BOX, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    my_gids = set(os.getgroups()) | {os.getgid()}
    foreign = next((x.gr_name for x in grp.getgrall() if x.gr_gid not in my_gids and g.USER not in x.gr_mem), None)
    if foreign is None:
        bail("no group exists that the sandbox user is not in, so an account it could not LOGTO cannot be staged")

    say("\n--- preparation: a CPROC that is not the install build, the probes, the fixture accounts ----------------------")
    g.prepare()
    g.EXTRA_FIXTURES.update({"zzgate": ("no", "no"), "zznolog": ("no", "no"), "zzsusp": ("no", "no")})
    for n in ("zzoff", "zzon", "zzgate", "zznolog", "zzsusp"):
        g.build_account(n)

    def register(name, **fields):
        rec = (g.reg_read(name) + [""] * 10)[:9]
        for k, v in fields.items():
            rec[{"group": 2, "susp": 4, "sd": 8}[k]] = v
        g.reg_write(name, rec)
    register("zzgate", sd="yes")
    register("zznolog", group=foreign)
    register("zzsusp", susp="SUSPENDED")
    for t in ("zzon", "zznolog", "zzsusp"):
        g.put(os.path.join(g.BOX, "user_accounts", t, "data.json"), '{"from":"%s"}\n' % t)
    for caller in ("zzoff", "zzgate"):
        g.put(os.path.join(g.BOX, "user_accounts", caller, "data.own"), "own-file\n")
        g.put(os.path.join(g.BOX, "user_accounts", caller, "bp", "zzrd"), "\n".join([
            "   names = '../zzon/data.json':@fm:'../zznolog/data.json':@fm:'../zzsusp/data.json':@fm:'/etc/hostname':@fm:'data.own'",
            "   for i = 1 to dcount(names, @fm)",
            "      nm = names<i>",
            "      openseq nm to f then",
            "         readseq l from f then crt 'R ':nm:' OK ':l else crt 'R ':nm:' OK empty'",
            "         close f",
            "      end else crt 'R ':nm:' DENIED'",
            "   next i",
            "end", ""]))
        g.put(os.path.join(g.BOX, "user_accounts", caller, "bp", "zzvc"), "\n".join([
            "   openpath '../zzon/voc' to f1 then crt 'V target-voc OPENED' ; close f1 else crt 'V target-voc DENIED'",
            "   openpath '../zzon/sub' to f2 then crt 'V target-sub OPENED' ; close f2 else crt 'V target-sub DENIED'",
            "   openpath 'voc' to f3 then crt 'V own-voc OPENED' ; close f3 else crt 'V own-voc DENIED'",
            "end", ""]))

    def run(caller, prog, admin=False):
        cmds = ["BASIC bp %s" % prog, "RUN bp %s" % prog]
        if admin:
            return g.sd(os.path.join(g.BOX, "user_accounts", caller), cmds, admin=True, account=caller)
        return g.plain(caller, cmds)

    def verdicts(out):
        d = {}
        for ln in out:
            m = re.match(r"^R (\S+) (OK(?: empty| .*)?|DENIED)$", ln)
            if m:
                d[m.group(1)] = m.group(2)
        return d

    say("\n--- the gate off ------------------------------------------------------------------------------------------")
    v = verdicts(run("zzoff", "zzrd"))
    row("CONTROL: without the gate a file in another account is refused", v.get("../zzon/data.json") == "DENIED", repr(v))
    row("CONTROL: the account's own file is read", v.get("data.own", "").startswith("OK own-file"), repr(v))

    say("\n--- the gate on -------------------------------------------------------------------------------------------")
    v = verdicts(run("zzgate", "zzrd"))
    row("an account the user could LOGTO: its file is read", v.get("../zzon/data.json", "").startswith("OK") and "zzon" in v.get("../zzon/data.json", ""), repr(v))
    row("an account in a group the user is not in: refused", v.get("../zznolog/data.json") == "DENIED", repr(v))
    row("a suspended account: refused", v.get("../zzsusp/data.json") == "DENIED", repr(v))
    row("a path in no account at all (/etc/hostname): refused", v.get("/etc/hostname") == "DENIED", repr(v))
    row("the account's own file is still read", v.get("data.own", "").startswith("OK own-file"), repr(v))

    say("\n--- the VOC of another account is left out -------------------------------------------------------------")
    out = run("zzgate", "zzvc")
    row("the other account's directory inside it is opened", g.has(out, r"^V target-sub OPENED$"), repr(out[-4:]))
    row("THE ROW: the other account's VOC is not", g.has(out, r"^V target-voc DENIED$"), repr(out[-4:]))
    row("CONTROL: the account's own VOC is (the exception is for other accounts)", g.has(out, r"^V own-voc OPENED$"), repr(out[-4:]))
    out = run("zzoff", "zzvc")
    row("CONTROL: without the gate neither the target's directory nor its VOC", g.has(out, r"^V target-sub DENIED$") and g.has(out, r"^V target-voc DENIED$"), repr(out[-4:]))

    say("\n--- SDSYS is not held to it -----------------------------------------------------------------------------")
    v = verdicts(run("zzoff", "zzrd", admin=True))
    row("an administrator in the account without the gate reads every one of them, VOC and the rest included",
        all(v.get(k, "").startswith("OK") for k in ("../zzon/data.json", "../zznolog/data.json", "../zzsusp/data.json", "/etc/hostname")), repr(v))

    say("\n--- MODIFY.ACCOUNT SD-ON / SD-OFF ------------------------------------------------------------------------")
    out = g.adm(["MODIFY.ACCOUNT zzoff SD-ON"])
    row("SD-ON says where the gate now stands", g.has(out, r"^Account zzoff has SD.ACCOUNTS yes$"), repr(out))
    row("...and writes field 9 of the register record", (g.reg_read("zzoff") + [""] * 9)[8] == "yes", repr(g.reg_read("zzoff")))
    out = g.adm(["MODIFY.ACCOUNT zzoff SH-ON"])
    row("...it is allowed on an account whose group is not an sdu_ one (a group account), where SH-ON is refused (10105)",
        g.has(out, r"is a group account") and (g.reg_read("zzoff") + [""] * 9)[8] == "yes", repr(out))
    v = verdicts(run("zzoff", "zzrd"))
    row("the gate takes effect at the next entry: zzoff now reads the file", v.get("../zzon/data.json", "").startswith("OK"), repr(v))
    out = g.adm(["MODIFY.ACCOUNT zzoff SD-OFF"])
    row("SD-OFF switches it off again", g.has(out, r"^Account zzoff has SD.ACCOUNTS no$") and (g.reg_read("zzoff") + [""] * 9)[8] == "no", repr(out))
    v = verdicts(run("zzoff", "zzrd"))
    row("...and the file is refused again", v.get("../zzon/data.json") == "DENIED", repr(v))

    say("")
    say("sandbox-sdaccts: %d passed, %d failed" % (passed, failed))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
