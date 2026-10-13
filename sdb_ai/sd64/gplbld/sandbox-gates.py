#!/usr/bin/env python3
#
# sandbox-gates.py - S.63, the per-account OS-access gates (SH, OS.EXECUTE, and what they govern: OS paths opened
#                    with OPENSEQ / OPENPATH, the embedded Python, nano and micro), through ORDINARY sessions on a
#                    private SD.  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-gates.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or
# absent).  Exit 0 every row passed, 1 a row failed, 2 it could not run.  Only one private SD can exist on a machine
# (shared memory keys 0x53434c91/92): stop it afterwards with sandbox-fromtree.py <dir> stop.
#
# START-HISTORY:
# 13 Oct 26 dm  Written for S.63 (owner, 13 Oct 2026: the tiers were to go and the per-account gates to stay, off by
#               default, switched by SDSYS).
# END-HISTORY
#
# WHY THIS NEEDS PREPARATION.  The sandbox user plays SDSYS (sandbox-fromtree.py patches CPROC so it is elevated), and an
# administrator passes every gate, so a session as it proves nothing.  prepare() therefore (1) recompiles CPROC the way
# the installer's last step does, WITHOUT the IS_INSTALL bootstrap that makes every session an administrator, and
# (2) adds one condition to the elevation test: the session is elevated only if the environment says
# SDTEST_ADMIN=1.  Nothing else in CPROC changes.  A plain session is then `sd -a<account>` run in the account's
# directory, and the suite's first rows prove it IS plain (admin=0) before any other row means anything - if it is
# not, the run stops with exit 2 rather than pass.
#
# THE ACCOUNTS.  The sandbox cannot make Linux users or groups, so each fixture account is a directory with a VOC made
# from NEWVOC, a register record written by hand, and a register GROUP that the sandbox user is really in (its own
# group), so the session's membership test passes.  Fields 7 and 8 of the record are ACC$SH and ACC$OS.EXEC:
#   zzoff  no / no      zzon  yes / yes      zzsh  yes / no      zzos  no / yes
#   zzblank  never told      zzcase  Yes / YES
#
# WHAT IT MEASURES, AND ITS LIMITS.  Gates are tested in the kernel (op_sh.c, op_dio1.c, op_seqio.c, op_sdext.c, op_kernel.c)
# and in CPROC / LOGIN, by what an ordinary session can and cannot DO, with a sentinel file as the evidence of whether a
# command ran.  CREATE.ACCOUNT is NOT driven here: it makes Linux users and groups, which needs root; its defaults are read
# off the source by test-gates-units.py and witnessed by witness-accounts.sh.  Windows' gate and an INSTALL are not touched.

import getpass
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
sys.path.insert(0, HERE)
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
USER = getpass.getuser()
GROUP = subprocess.run(["id", "-gn"], capture_output=True, text=True).stdout.strip()
passed = failed = 0
BOX = SYS = SD = None

FIXTURES = {
    "zzdyn": ("no", "no"),
    "zzoff": ("no", "no"),
    "zzon": ("yes", "yes"),
    "zzsh": ("yes", "no"),
    "zzos": ("no", "yes"),
    "zzblank": ("", ""),
    "zzcase": ("Yes", "YES"),
}


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
    say("sandbox-gates: CANNOT RUN - " + msg)
    sys.exit(2)


def env(admin):
    e = dict(os.environ, SD_CONFIG=os.path.join(BOX, "sd.conf"))
    e.pop("SSH_CONNECTION", None)
    e.pop("SSH_TTY", None)
    if admin:
        e["SDTEST_ADMIN"] = "1"
    else:
        e.pop("SDTEST_ADMIN", None)
    return e


def sd(cwd, cmds, admin=False, internal=False, account=None):
    """Run sd with the commands on stdin and return what it printed after the TERM line, with the echoed commands
    (lines that begin with a colon) removed.  Prints the real inputs: the working directory, the flags and the commands."""
    argv = [SD] + (["-internal"] if internal else []) + (["-a" + account] if account else [])
    say("    > %s%s%s in %s: %s" % ("[admin] " if admin else "", "[internal] " if internal else "",
                                    ("-a" + account + " ") if account else "", os.path.relpath(cwd, BOX), " | ".join(cmds)))
    body = "\nTERM 200,9999\n" + "".join(c + "\n" for c in cmds) + "OFF\n"
    p = subprocess.run(argv, input=body, cwd=cwd, env=env(admin), capture_output=True, text=True, errors="replace",
                       timeout=300)
    out = ANSI.sub("", p.stdout + p.stderr).split(":TERM 200,9999", 1)[-1]
    return [ln.rstrip() for ln in out.splitlines() if ln.strip() and not ln.startswith(":")]


def plain(acct, cmds):
    return sd(os.path.join(BOX, "user_accounts", acct), cmds, account=acct)


def adm(cmds, internal=False):
    return sd(SYS, cmds, admin=True, internal=internal)


def put(path, text):
    with open(path, "w", encoding="ascii") as f:
        f.write(text)


def reg_write(name, fields):
    put(os.path.join(SYS, "accounts", name), "\n".join(fields) + "\n")


def reg_read(name):
    with open(os.path.join(SYS, "accounts", name)) as f:
        return f.read().split("\n")


def flags(lines):
    for ln in lines:
        m = re.match(r"^KFLAGS admin=(\d+) sh=(\d+) osx=(\d+) user=(\S+)$", ln)
        if m:
            return tuple(m.groups())
    return None


def has(lines, pattern):
    return any(re.search(pattern, ln) for ln in lines)


# ---------------------------------------------------------------------------------------------------------------------
# preparation

def prepare():
    path = os.path.join(SYS, "gpl.bp", "cproc")
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    old = "if downcase(kernel(K$USERNAME, 0)) = '%s' and env('SSH_CONNECTION') = ''" % USER
    new = ("if downcase(kernel(K$USERNAME, 0)) = '%s' and env('SDTEST_ADMIN') = '1' and env('SSH_CONNECTION') = ''" % USER)
    if "SDTEST_ADMIN" not in text:
        if text.count(old) != 1:
            bail("the sandbox CPROC does not have the one elevation test this suite patches (%d matches)" % text.count(old))
        with open(path, "w", encoding="utf-8") as f:
            f.write(text.replace(old, new))
    put(os.path.join(SYS, "gpl.bp", "define_install.h"), "*comment out * $define IS_INSTALL\n")
    out = adm(["BASIC gpl.bp cproc"], internal=True)
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("CPROC did not recompile in the sandbox:\n" + "\n".join(out[-8:]))

    # the probes, catalogued in gpl.bp so that they are internal programs a VOC verb can name
    put(os.path.join(SYS, "gpl.bp", "zzkf"), "\n".join([
        "$internal", "program zzkf", "$catalog $zzkf", "$include keys.h", "$include int$keys.h",
        "   crt 'KFLAGS admin=':kernel(K$ADMINISTRATOR,-1):' sh=':kernel(K$SH,-1):' osx=':kernel(K$OS.EXEC,-1):"
        "' user=':kernel(K$USERNAME,0)", "end", ""]))
    put(os.path.join(SYS, "gpl.bp", "zzkp"), "\n".join([
        "$internal", "program zzkp", "$catalog $zzkp", "$include keys.h", "$include int$keys.h",
        "   crt 'KP outside=':kernel(K$PATH.OK,'/etc/hostname'):' inside=':kernel(K$PATH.OK,'inside.txt'):"
        "' sibling=':kernel(K$PATH.OK,'../zzon/voc'):' dotdot=':kernel(K$PATH.OK,'sub/../../zzon/voc'):"
        "' empty=':kernel(K$PATH.OK,'')",
        "   openseq '/etc/hostname' to f then crt 'KP internal-openseq-outside OK' else "
        "crt 'KP internal-openseq-outside REFUSED'", "end", ""]))
    put(os.path.join(SYS, "gpl.bp", "zzinfo"), "\n".join([
        "$internal", "program zzinfo", "$catalog $zzinfo", "$include keys.h", "$include int$keys.h",
        "   openpath @sdsys:@ds:'accounts' to acc.f else",
        "      crt 'INFO no register'",
        "      stop",
        "   end",
        "   for each a in 'zzoff':@fm:'zzon':@fm:'zzsh':@fm:'zzos':@fm:'zzblank'",
        "      read rec from acc.f, a then",
        "         call !acc_os_info(a, rec, info, err)",
        "         crt 'INFO ':a:' ':convert(@fm, '|', info):' err=':err",
        "      end else",
        "         crt 'INFO no record ':a",
        "      end",
        "   next a", "end", ""]))
    out = adm(["BASIC gpl.bp zzkf zzkp zzinfo"], internal=True)
    if not has(out, r"^Compiled 3 program\(s\) with no errors"):
        bail("the probes did not compile:\n" + "\n".join(out[-10:]))


def build_account(name):
    path = os.path.join(BOX, "user_accounts", name)
    if os.path.isdir(path):
        shutil.rmtree(path)
    os.makedirs(os.path.join(path, "sub"))
    os.symlink("/etc/hostname", os.path.join(path, "link.txt"))     # a link INSIDE the account that points OUT of it
    put(os.path.join(path, "inside.txt"), "an ordinary file in the account\n")
    put(os.path.join(SYS, "bp", "zzfix"), "\n".join([
        "$internal",
        "   acct = '%s'" % path,
        "   create.file acct:'/voc' dynamic on error crt 'FIX create voc failed' ; stop",
        "   openpath acct:'/voc' to v else crt 'FIX open voc failed' ; stop",
        "   openpath '%s/newvoc' to nv else crt 'FIX no newvoc' ; stop" % SYS,
        "   select nv to 11",
        "   loop",
        "      readnext id from 11 else exit",
        "      read rec from nv, id then write rec to v, id",
        "   repeat",
        "   write 'X' to v, '$command.stack'",
        "   write 'V':@fm:'CA':@fm:'$zzkf' to v, 'zzkf'",
        "   write 'V':@fm:'CA':@fm:'$zzkp' to v, 'zzkp'",
        "   create.file acct:'/bp' directory on error crt 'FIX bp failed' ; stop",
        "   write 'F':@fm:'bp' to v, 'bp'",
        "   create.file acct:'/cat' directory on error crt 'FIX cat failed' ; stop",
        "   crt 'FIX done ':'%s'" % name,
        "end", ""]))
    out = adm(["BASIC bp zzfix", "RUN bp zzfix"], internal=True)
    if not has(out, r"^FIX done " + name + "$"):
        bail("the fixture account %s was not built:\n%s" % (name, "\n".join(out[-6:])))
    sh, osx = FIXTURES[name]
    reg_write(name, [path, "", GROUP, "", "", "", sh, osx])
    return path


# ---------------------------------------------------------------------------------------------------------------------

def main():
    global BOX, SYS, SD
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-gates.py <dir> [--build]")
    BOX = os.path.abspath(args[0])
    SYS = os.path.join(BOX, "sys")
    SD = os.path.join(SYS, "bin", "sd")
    say("sandbox-gates: sandbox  %s" % BOX)
    say("sandbox-gates: tree     %s" % os.path.dirname(HERE))
    say("sandbox-gates: user %s, group %s (the register group of every fixture account)" % (USER, GROUP))
    if "--build" in sys.argv:
        if os.path.exists(BOX) and os.listdir(BOX):
            bail("%s is not empty" % BOX)
        r = subprocess.run([sys.executable, TOOL, BOX, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-gates: built, bootstrap passed")
    elif not os.path.isfile(SD):
        bail("%s holds no built sandbox (use --build, or point it at one)" % BOX)
    subprocess.run([sys.executable, TOOL, BOX, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    say("\n--- preparation: a CPROC that is not the install build, the probes, the fixture accounts ----------------------")
    prepare()
    for name in FIXTURES:
        build_account(name)
    say("  [done] %d accounts: %s" % (len(FIXTURES), " ".join(FIXTURES)))

    # --- controls: the session is ordinary --------------------------------------------------------------------
    say("\n--- 0. controls: a plain session is NOT an administrator, and the switch that makes one works ---------------")
    f = flags(plain("zzoff", ["ZZKF"]))
    row("0a: a plain session in zzoff is not an administrator (admin=0)", f is not None and f[0] == "0",
        "KFLAGS line: %r" % (f,))
    if f is None or f[0] != "0":
        bail("the plain session is an administrator (or printed nothing): every row below would be meaningless")
    f = flags(sd(os.path.join(BOX, "user_accounts", "zzoff"), ["ZZKF"], admin=True, account="zzoff"))
    row("0b: the same session with SDTEST_ADMIN=1 is an administrator (admin=1) - the control that the switch works",
        f is not None and f[0] == "1", "KFLAGS line: %r" % (f,))

    # --- A. the grants are loaded at account entry -----------------------------------------------------------
    say("\n--- A. LOGIN loads the grants from ACC$SH / ACC$OS.EXEC: yes is on, anything else is off -----------------------")
    want = {"zzoff": ("0", "0"), "zzon": ("1", "1"), "zzsh": ("1", "0"), "zzos": ("0", "1"), "zzblank": ("0", "0"),
            "zzcase": ("1", "1")}
    why = {"zzoff": "no / no", "zzon": "yes / yes", "zzsh": "yes / no (independent)", "zzos": "no / yes (independent)",
           "zzblank": "blank fields: never told is denied", "zzcase": "Yes / YES: the test ignores case"}
    for name, (s, o) in want.items():
        f = flags(plain(name, ["ZZKF"]))
        row("A: %s (%s) -> sh=%s osx=%s, not an administrator" % (name, why[name], s, o),
            f is not None and f[0] == "0" and f[1] == s and f[2] == o and f[3] == USER, "KFLAGS line: %r" % (f,))

    # --- B. the SH verb -----------------------------------------------------------------------------------------
    say("\n--- B. the SH verb: refused without the grant (and the command does not run), runs with it ------------------------")
    refusal = "%s is not permitted to use the operating system shell" % USER
    for name, ok_expected in (("zzoff", False), ("zzblank", False), ("zzos", False), ("zzon", True), ("zzsh", True)):
        sent = os.path.join(BOX, "user_accounts", name, "b.sentinel")
        if os.path.exists(sent):
            os.remove(sent)
        out = plain(name, ["SH touch " + sent])
        ran = os.path.exists(sent)
        refused = has(out, "^" + re.escape(refusal) + "$")
        if ok_expected:
            row("B: %s runs SH: the sentinel exists and there is no refusal" % name, ran and not refused,
                "sentinel exists=%s refused=%s output=%r" % (ran, refused, out[-3:]))
        else:
            row("B: %s is refused SH with the Windows port's 10053 wording and the command did not run" % name,
                (not ran) and refused, "sentinel exists=%s refused=%s output=%r" % (ran, refused, out[-3:]))
    sent = os.path.join(BOX, "user_accounts", "zzoff", "b.admin.sentinel")
    if os.path.exists(sent):
        os.remove(sent)
    out = sd(os.path.join(BOX, "user_accounts", "zzoff"), ["SH touch " + sent], admin=True, account="zzoff")
    row("B: control - an administrator in zzoff is not refused (the gate does not bind SDSYS)", os.path.exists(sent),
        "output=%r" % (out[-3:],))

    # --- C. OS.EXECUTE from a user program ------------------------------------------------------------------
    say("\n--- C. OS.EXECUTE in a user's BASIC program: refused without the grant, independent of SH ----------------------")
    for name in ("zzoff", "zzon", "zzsh", "zzos", "zzblank"):
        d = os.path.join(BOX, "user_accounts", name)
        sent = os.path.join(d, "c.sentinel")
        if os.path.exists(sent):
            os.remove(sent)
        put(os.path.join(d, "bp", "zzosx"), "   crt 'C before'\n   os.execute 'touch %s'\n   crt 'C after'\nend\n" % sent)
        out = plain(name, ["BASIC bp zzosx", "RUN bp zzosx"])
        if not has(out, r"^Compiled 1 program\(s\) with no errors"):
            row("C: %s's probe program compiled" % name, False, "output=%r" % (out[-4:],))
            continue
        ran = os.path.exists(sent)
        refused = has(out, re.escape("%s is not permitted to use OS.EXECUTE" % USER))
        after = has(out, "^C after$")
        osx = FIXTURES[name][1].lower() == "yes"
        if osx:
            row("C: %s (os %s) runs OS.EXECUTE: the sentinel exists, the program ran on" % (name, FIXTURES[name][1]),
                ran and after and not refused, "ran=%s after=%s refused=%s" % (ran, after, refused))
        else:
            row("C: %s (os %s) is refused OS.EXECUTE (10054): no sentinel, and the program stopped" % (name, FIXTURES[name][1] or "blank"),
                (not ran) and refused and not after, "ran=%s after=%s refused=%s output=%r" % (ran, after, refused, out[-3:]))

    # --- D. OPENSEQ / OPENPATH ----------------------------------------------------------------------------------
    say("\n--- D. OPENSEQ and OPENPATH by pathname: without OS.EXECUTE only the account's own directory ---------------------")
    seq = "\n".join([
        "   crt 'P begin'",
        "   openseq '/etc/hostname' to f1 then crt 'P outside OK' else crt 'P outside REFUSED ':status()",
        "   openseq 'inside.txt' to f2 then crt 'P inside OK' else crt 'P inside REFUSED ':status()",
        "   openseq './newfile.txt' to f3 then crt 'P new-in-account OK' else",
        "      st = status()",
        "      if st = 3035 then",
        "         crt 'P new-in-account REFUSED ':st",
        "      end else",
        "         create f3 then crt 'P new-in-account CREATED' else crt 'P new-in-account FAILED ':status()",
        "      end",
        "   end",
        "   openseq 'sub/../inside.txt' to f4 then crt 'P dotdot-inside OK' else crt 'P dotdot-inside REFUSED ':status()",
        "   openseq '../zzon/inside.txt' to f5 then crt 'P sibling OK' else crt 'P sibling REFUSED ':status()",
        "   openseq 'sub/../../zzon/inside.txt' to f6 then crt 'P dotdot-out OK' else crt 'P dotdot-out REFUSED ':status()",
        "   openseq 'link.txt' to f7 then crt 'P symlink-out OK' else crt 'P symlink-out REFUSED ':status()",
        "   openseq '/tmp/zzgates.nonexistent' to f8 then crt 'P tmp-new OK' else",
        "      st = status()",
        "      if st = 3035 then",
        "         crt 'P tmp-new REFUSED ':st",
        "      end else",
        "         create f8 then crt 'P tmp-new CREATED' else crt 'P tmp-new FAILED ':status()",
        "      end",
        "   end",
        "   openpath '/etc' to g1 then crt 'P openpath-outside OK' else crt 'P openpath-outside REFUSED ':status()",
        "   openpath 'bp' to g2 then crt 'P openpath-inside OK' else crt 'P openpath-inside REFUSED ':status()",
        "   openpath '/tmp' to g3 then crt 'P openpath-tmp OK' else crt 'P openpath-tmp REFUSED ':status()",
        "   open 'bp' to v1 then crt 'P voc-open OK' else crt 'P voc-open REFUSED ':status()",
        "   openseq 'bp', 'zzseq' to v2 then crt 'P voc-openseq OK' else crt 'P voc-openseq REFUSED ':status()",
        "   crt 'P end'", "end", ""])

    def rows_d(name):
        d = os.path.join(BOX, "user_accounts", name)
        for junk in (os.path.join(d, "newfile.txt"), "/tmp/zzgates.nonexistent"):
            if os.path.exists(junk):
                os.remove(junk)
        put(os.path.join(d, "bp", "zzseq"), seq)
        out = plain(name, ["BASIC bp zzseq", "RUN bp zzseq"])
        got = {}
        for ln in out:
            m = re.match(r"^P (\S+) (OK|CREATED|REFUSED(?: \d+)?)$", ln)
            if m:
                got[m.group(1)] = m.group(2)
        return got, out

    got, out = rows_d("zzoff")
    if "end" not in got and not has(out, "^P end$"):
        bail("zzoff's OPENSEQ probe did not run to its end:\n" + "\n".join(out[-6:]))
    refused = "REFUSED 3035"
    for key, label in (("outside", "/etc/hostname"), ("sibling", "../zzon/inside.txt"), ("dotdot-out", "sub/../../zzon/inside.txt"),
                       ("symlink-out", "a link inside the account that points out of it"), ("tmp-new", "/tmp (to create a file)"),
                       ("openpath-outside", "OPENPATH /etc"), ("openpath-tmp", "OPENPATH /tmp")):
        row("D: zzoff (no OS.EXECUTE) is refused %s with status 3035 (ER_PERM)" % label, got.get(key) == refused,
            "%s -> %r" % (key, got.get(key)))
    for key, label in (("inside", "its own existing file"), ("new-in-account", "a new file in the account"),
                       ("dotdot-inside", "sub/../inside.txt, which lands inside"), ("openpath-inside", "OPENPATH of its own bp"),
                       ("voc-open", "OPEN of a file named by its VOC (an SD file)"),
                       ("voc-openseq", "OPENSEQ of a record of a VOC-named file")):
        row("D: zzoff may still open %s" % label, got.get(key) in ("OK", "CREATED"), "%s -> %r" % (key, got.get(key)))
    for name in ("zzon", "zzos"):
        got, out = rows_d(name)
        row("D: %s (OS.EXECUTE yes) opens /etc/hostname, a sibling account's file, a link out, /tmp and OPENPATH /etc"
            % name,
            all(got.get(k) in ("OK", "CREATED") for k in ("outside", "sibling", "symlink-out", "tmp-new", "openpath-outside",
                                                          "openpath-tmp")), "%r" % (got,))
    got, out = rows_d("zzsh")
    row("D: zzsh (SH yes, OS.EXECUTE no) is contained like zzoff: SH does not open paths",
        got.get("outside") == refused and got.get("inside") == "OK", "%r" % (got,))
    for junk in ("/tmp/zzgates.nonexistent",):
        if os.path.exists(junk):
            os.remove(junk)

    # --- E. K$PATH.OK, the question an internal program asks for the user ---------------------------------------
    say("\n--- E. K$PATH.OK: the account's own answer, which an internal program (SED) must ask because it is exempt -------")
    out = plain("zzoff", ["ZZKP"])
    row("E: zzoff - outside=0 inside=1 sibling=0 dotdot=0 empty=0",
        has(out, r"^KP outside=0 inside=1 sibling=0 dotdot=0 empty=0$"), "output=%r" % (out[-3:],))
    row("E: zzoff - and yet an internal program's own OPENSEQ outside the account is NOT refused (that exemption is why "
        "SED has to ask)", has(out, r"^KP internal-openseq-outside OK$"), "output=%r" % (out[-3:],))
    out = plain("zzon", ["ZZKP"])
    row("E: zzon - outside=1 inside=1 sibling=1 dotdot=1 empty=0 (an empty name is never allowed)",
        has(out, r"^KP outside=1 inside=1 sibling=1 dotdot=1 empty=0$"), "output=%r" % (out[-3:],))

    # --- F. the embedded Python -----------------------------------------------------------------------------
    say("\n--- F. the embedded Python runs arbitrary code, so it is behind OS.EXECUTE too ----------------------------------")
    for name, allowed in (("zzoff", False), ("zzsh", False), ("zzon", True), ("zzos", True)):
        d = os.path.join(BOX, "user_accounts", name)
        sent = os.path.join(d, "py.sentinel")
        if os.path.exists(sent):
            os.remove(sent)
        put(os.path.join(d, "bp", "zzpy"), "\n".join([
            "$include syscom sdpyfunc.h", "   x = py_initialize()", "   crt 'PY init=[':x:']'",
            "   y = py_runstring(\"open('%s','w').write('ran')\")" % sent, "   crt 'PY run=[':y:']'", "   crt 'PY end'", "end", ""]))
        out = plain(name, ["BASIC bp zzpy", "RUN bp zzpy"])
        ran = os.path.exists(sent)
        if allowed:
            row("F: %s may run Python: init=[0], the code ran (sentinel exists)" % name,
                has(out, r"^PY init=\[0\]$") and ran, "ran=%s output=%r" % (ran, out[-3:]))
        else:
            row("F: %s is refused Python: init returns null, the code did not run (no sentinel)" % name,
                has(out, r"^PY init=\[\]$") and (not ran) and has(out, "^PY end$"), "ran=%s output=%r" % (ran, out[-3:]))

    # --- G. MODIFY.ACCOUNT --------------------------------------------------------------------------------------
    say("\n--- G. MODIFY.ACCOUNT sh-on / sh-off / os-on / os-off: two independent switches, written to the register ---------")
    reg_write("zzmod", ["/x", "", "sdu_zzmod"])
    reg_write("zzgrp", ["/x", "", "sdg_zzgrp"])

    def fields(name):
        r = reg_read(name)
        return tuple((r[i] if len(r) > i else "") for i in (6, 7))

    def mod(*words):
        return adm(["MODIFY.ACCOUNT " + " ".join(words)])

    row("G: before - zzmod has never been told (fields 7 and 8 blank)", fields("zzmod") == ("", ""), "%r" % (fields("zzmod"),))
    out = mod("zzmod", "SH-ON")
    row("G: sh-on - SH yes, OS.EXECUTE untouched: the report (10102) and the register agree",
        has(out, "^Account zzmod has SH yes, OS.EXECUTE no$") and fields("zzmod") == ("yes", ""),
        "out=%r reg=%r" % (out[-2:], fields("zzmod")))
    out = mod("zzmod", "SH-ON")
    row("G: sh-on again says it had that access already (10080) and writes nothing",
        has(out, "^zzmod already had that access; nothing changed$") and fields("zzmod") == ("yes", ""),
        "out=%r reg=%r" % (out[-2:], fields("zzmod")))
    out = mod("zzmod", "OS-ON")
    row("G: os-on - both yes", has(out, "^Account zzmod has SH yes, OS.EXECUTE yes$") and fields("zzmod") == ("yes", "yes"),
        "out=%r reg=%r" % (out[-2:], fields("zzmod")))
    out = mod("zzmod", "SH-OFF")
    row("G: sh-off - SH no and OS.EXECUTE still yes (SH-OFF says nothing about OS.EXECUTE)",
        has(out, "^Account zzmod has SH no, OS.EXECUTE yes$") and fields("zzmod") == ("no", "yes"),
        "out=%r reg=%r" % (out[-2:], fields("zzmod")))
    out = mod("zzmod", "OS-OFF")
    row("G: os-off - both no, written as the word no (an explicit decision, not a blank)",
        has(out, "^Account zzmod has SH no, OS.EXECUTE no$") and fields("zzmod") == ("no", "no"),
        "out=%r reg=%r" % (out[-2:], fields("zzmod")))
    before = reg_read("zzgrp")
    out = mod("zzgrp", "SH-ON")
    row("G: a GROUP account is refused (10105) and its record is not touched",
        has(out, "^zzgrp is a group account and has no Linux user, so it has no shell to permit$") and reg_read("zzgrp") == before,
        "out=%r" % (out[-2:],))
    out = adm(["MODIFY.ACCOUNT"])
    row("G: the usage lists the four words", has(out, r"modify\.account <account> sh-on \| sh-off") and
        has(out, r"modify\.account <account> os-on \| os-off"), "out=%r" % (out[:6],))

    # the end-to-end row: the switch an administrator sets is what the next session in the account gets.  MODIFY.ACCOUNT
    # needs an sdu_ group in the record; the session needs a group the sandbox user is really in.  So: the record gets
    # the sdu_ name while MODIFY.ACCOUNT runs, and the real group back afterwards - the two fields it wrote are untouched.
    dyn = os.path.join(BOX, "user_accounts", "zzdyn")
    reg_write("zzdyn", [dyn, "", "sdu_zzdyn", "", "", "", "no", "no"])
    mod("zzdyn", "SH-ON")
    mod("zzdyn", "OS-ON")
    r = reg_read("zzdyn")
    r[2] = GROUP            # the sandbox cannot make the Linux group sdu_zzdyn; the two fields MODIFY.ACCOUNT wrote stay
    reg_write("zzdyn", r[:8])
    f = flags(plain("zzdyn", ["ZZKF"]))
    row("G: end to end - after MODIFY.ACCOUNT zzdyn sh-on and os-on, the next plain session in it holds both grants",
        f is not None and f[0] == "0" and f[1] == "1" and f[2] == "1", "KFLAGS line: %r register=%r" % (f, r[6:8]))
    r[6] = "no"
    r[7] = "no"
    reg_write("zzdyn", r[:8])
    f = flags(plain("zzdyn", ["ZZKF"]))
    row("G: and with both switched off again the next session holds neither", f is not None and f[1] == "0" and f[2] == "0",
        "KFLAGS line: %r" % (f,))

    # --- H. the manifest and the report -------------------------------------------------------------------------
    say("\n--- H. the account archive manifest carries the gates (acc_os_info), so a restore keeps them --------------------")
    reg_write("zzoff", [os.path.join(BOX, "user_accounts", "zzoff"), "", "sdu_zzoff", "", "", "", "no", "no"])
    reg_write("zzon", [os.path.join(BOX, "user_accounts", "zzon"), "", "sdu_zzon", "", "", "", "yes", "yes"])
    reg_write("zzsh", [os.path.join(BOX, "user_accounts", "zzsh"), "", "sdu_zzsh", "", "", "", "yes", "no"])
    reg_write("zzos", [os.path.join(BOX, "user_accounts", "zzos"), "", "sdu_zzos", "", "", "", "no", "yes"])
    reg_write("zzblank", [os.path.join(BOX, "user_accounts", "zzblank"), "", "sdu_zzblank"])
    out = adm(["RUN gpl.bp zzinfo"], internal=True)
    for name, (s, o) in (("zzoff", ("0", "0")), ("zzon", ("1", "1")), ("zzsh", ("1", "0")), ("zzos", ("0", "1")),
                         ("zzblank", ("0", "0"))):
        row("H: %s -> os.sh: %s and os.execute: %s in the manifest" % (name, s, o),
            has(out, r"^INFO %s .*\|os\.sh: %s\|os\.execute: %s(\||\s)" % (name, s, o)), "out=%r" % ([l for l in out if name in l][:2],))

    # --- I. the upgrade ---------------------------------------------------------------------------------------
    say("\n--- I. upgrade_gates: the accounts that exist keep their shell and OS.EXECUTE, once ----------------------------")
    marker = os.path.join(SYS, "$gates.done")
    if os.path.exists(marker):
        os.remove(marker)
    reg_write("zzu_blank", ["/x", "", "sdu_zzu_blank"])
    reg_write("zzu_no", ["/x", "", "sdu_zzu_no", "", "", "", "no", "no"])
    reg_write("zzu_half", ["/x", "", "sdu_zzu_half", "", "", "", "yes", ""])
    reg_write("zzu_both", ["/x", "", "sdu_zzu_both", "", "", "", "yes", "yes"])
    reg_write("zzu_grp", ["/x", "", "sdg_zzu_grp"])
    # expected from the register as it stands now: every sdu_ record that lacks either 'yes' is changed
    need = both = 0
    for n in sorted(os.listdir(os.path.join(SYS, "accounts"))):
        r = reg_read(n)
        if len(r) > 2 and r[2].startswith("sdu_"):
            if (r[6] if len(r) > 6 else "").strip().upper() == "YES" and (r[7] if len(r) > 7 else "").strip().upper() == "YES":
                both += 1
            else:
                need += 1
    sdsys_before = reg_read("sdsys")
    grp_before = reg_read("zzu_grp")
    out = adm(["RUN gpl.bp upgrade_gates"], internal=True)
    row("I: the first run reports the count it should (%d switched on, %d already had both) and COMPLETE" % (need, both),
        has(out, r"^OS-access gates: switched on for %d existing account\(s\); %d already had both; 0 failed$" % (need, both))
        and has(out, "^COMPLETE$"), "out=%r" % (out[-4:],))
    row("I: a blank record, a record of explicit no/no, and a half-set one all end yes / yes",
        all(tuple(reg_read(n)[6:8]) == ("yes", "yes") for n in ("zzu_blank", "zzu_no", "zzu_half")),
        "%r" % ({n: reg_read(n)[6:8] for n in ("zzu_blank", "zzu_no", "zzu_half")},))
    row("I: a GROUP account and SDSYS are not touched", reg_read("zzu_grp") == grp_before and reg_read("sdsys") == sdsys_before,
        "grp=%r sdsys=%r" % (reg_read("zzu_grp"), reg_read("sdsys")))
    row("I: the marker sdsys/$gates.done exists", os.path.exists(marker))
    mod("zzu_no", "SH-OFF")
    out = adm(["RUN gpl.bp upgrade_gates"], internal=True)
    row("I: a second run changes nothing and says so, and still ends COMPLETE",
        has(out, "set for the existing accounts by an earlier install; nothing changed") and has(out, "^COMPLETE$"),
        "out=%r" % (out[-3:],))
    row("I: an administrator's later sh-off is NOT undone by the second run", tuple(reg_read("zzu_no")[6:8]) == ("no", "yes"),
        "%r" % (reg_read("zzu_no")[6:8],))

    say("\n--- summary " + "-" * 100)
    say("sandbox-gates: %d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
