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
import grp
import os
import re
import shutil
import socket
import subprocess
import sys
import threading

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


# Built by section D3 only (accounts a Q-pointer leads into), so that the loops over FIXTURES above are not changed.
EXTRA_FIXTURES = {
    "zznolog": ("no", "no"),     # register group is one the sandbox user is NOT in: LOGTO would refuse it
    "zzsusp": ("no", "no"),      # SUSPENDED: LOGTO would refuse it
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


# 17 Oct 26 dm (S.64).  THE FIXTURE ACCOUNTS KEEP THE RIGHT TO EDIT.  The edit gates (register fields 10 to 12) are off for an account that
# says nothing, as a blank is off; but the accounts these suites make stand for accounts that existed before the gates, which the
# upgrade switches on, and their ordinary sessions compile, catalogue and write the VOC all the time.  So a register record written with
# fewer than 10 fields is given 'yes' in all three.  sandbox-editgates.py is the suite OF the gates and sets this to None.
EDIT_DEFAULT = ["yes", "yes", "yes"]


def reg_write(name, fields):
    fields = list(fields)
    if EDIT_DEFAULT is not None and len(fields) < 10:
        fields += [""] * (9 - len(fields)) + list(EDIT_DEFAULT)
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
    sh, osx = FIXTURES.get(name) or EXTRA_FIXTURES[name]
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

    # --- D4. OSREAD, OSWRITE and OSDELETE (QM4 gaps Q-4, 15 Oct 26) ------------------------------------------------
    # They are ordinary programs made of OPENSEQ and DELETESEQ, so the gate is the account's own.  The evidence is the disk: a file
    # that appears in /tmp, a file in /tmp that is gone or still there, and what an account reads of /etc/hostname.
    say("\n--- D4. OSREAD, OSWRITE and OSDELETE: the same gate as OPENSEQ -------------------------------------------------")
    osq = "\n".join([
        "   crt 'Q begin'",
        "   osread d1 from '/etc/hostname' then crt 'Q read-outside OK ':(len(d1) > 0) else crt 'Q read-outside REFUSED'",
        "   oswrite 'abc' to 'zzqw.txt'",
        "   osread d2 from 'zzqw.txt' then crt 'Q read-inside OK ':d2 else crt 'Q read-inside FAILED'",
        "   oswrite 'xyz' to '/tmp/zzgates.osw'",
        "   crt 'Q write-outside-status ':status()",
        "   osdelete '/tmp/zzgates.osdel'",
        "   osdelete 'zzqw.txt'",
        "   osread d3 from 'zzqw.txt' then crt 'Q inside-gone NO' else crt 'Q inside-gone YES'",
        "   crt 'Q own-account-path ':(account.path(@who) # '')",
        "   crt 'Q other-account-path ':(account.path('zzon') # '')",
        "   crt 'Q vocpath-bp ':(vocpath('bp') # '')",
        "   crt 'Q end'", "end", ""])

    def rows_q(name):
        d = os.path.join(BOX, "user_accounts", name)
        for junk in ("/tmp/zzgates.osw", "/tmp/zzgates.osdel", os.path.join(d, "zzqw.txt")):
            if os.path.exists(junk):
                os.remove(junk)
        with open("/tmp/zzgates.osdel", "w") as f:
            f.write("keep")
        put(os.path.join(d, "bp", "zzosq"), osq)
        out = plain(name, ["BASIC bp zzosq", "RUN bp zzosq"])
        got = {}
        for ln in out:
            m = re.match(r"^Q (\S+) (.*)$", ln)
            if m:
                got[m.group(1)] = m.group(2)
        disk = {"osw": open("/tmp/zzgates.osw").read() if os.path.exists("/tmp/zzgates.osw") else None,
                "osdel": os.path.exists("/tmp/zzgates.osdel")}
        for junk in ("/tmp/zzgates.osw", "/tmp/zzgates.osdel"):
            if os.path.exists(junk):
                os.remove(junk)
        return got, disk, out

    got, disk, out = rows_q("zzoff")
    if "end" not in got and not has(out, "^Q end$"):
        bail("zzoff's OSREAD probe did not run to its end:\n" + "\n".join(out[-6:]))
    row("D4: zzoff (no OS.EXECUTE): OSREAD of /etc/hostname is refused", got.get("read-outside") == "REFUSED", "%r" % (got,))
    row("D4: zzoff: OSWRITE then OSREAD inside its own directory works, and gives what was written",
        got.get("read-inside") == "OK abc", "%r" % (got,))
    row("D4: zzoff: OSWRITE to /tmp writes nothing (no file on the disk) and says so in STATUS(): 3035",
        disk["osw"] is None and got.get("write-outside-status") == "3035", "disk=%r status=%r" % (disk, got.get("write-outside-status")))
    row("D4: zzoff: OSDELETE of a file in /tmp deletes nothing: the file is still there", disk["osdel"] is True, "%r" % (disk,))
    row("D4: zzoff: OSDELETE of its own file works", got.get("inside-gone") == "YES", "%r" % (got,))
    row("D4: zzoff: ACCOUNT.PATH of its own account and VOCPATH of its own bp are told, but ACCOUNT.PATH of the sibling zzon is a null string",
        got.get("own-account-path") == "1" and got.get("vocpath-bp") == "1" and got.get("other-account-path") == "0", "%r" % (got,))
    for name in ("zzon", "zzos"):
        got, disk, out = rows_q(name)
        row("D4: %s (OS.EXECUTE yes): OSREAD of /etc/hostname gives its contents" % name, got.get("read-outside") == "OK 1", "%r" % (got,))
        row("D4: %s: ACCOUNT.PATH of zzon is told (its own account, or another one to an account that has the OS gate), and its own is" % name,
            got.get("other-account-path") == "1" and got.get("own-account-path") == "1" and got.get("vocpath-bp") == "1", "%r" % (got,))
        row("D4: %s: OSWRITE to /tmp writes the file, and OSDELETE of another in /tmp removes it" % name,
            disk["osw"] == "xyz" and disk["osdel"] is False and got.get("write-outside-status") == "0", "disk=%r got=%r" % (disk, got))
    got, disk, out = rows_q("zzsh")
    row("D4: zzsh (SH yes, OS.EXECUTE no) is contained like zzoff: SH does not open paths",
        got.get("read-outside") == "REFUSED" and disk["osw"] is None and disk["osdel"] is True, "%r %r" % (got, disk))
    for junk in (os.path.join(BOX, "user_accounts", "zzoff", "zzqw.txt"),):
        if os.path.exists(junk):
            os.remove(junk)

    # --- D2. the other routes to an OS path -----------------------------------------------------------------------
    # 13 Oct 26 (second sitting).  THE FIRST VERSION OF THIS SUITE ASKED ABOUT OPENSEQ AND OPENPATH ONLY, AND AN
    # ACCOUNT WITH BOTH GATES OFF STILL READ /etc, LISTED IT, COPIED FILES OUT OF AND INTO OTHER DIRECTORIES, DELETED
    # A FILE OUTSIDE ITS OWN AND PRINTED INTO ONE: DIR() and SELECT.DIR, !OSCOPY / !IOSCOPY / the OSCOPY verb,
    # DELETESEQ of a bare pathname, and SETPTR ... AS PATHNAME / the SETPU statement.  Each was measured on a build of
    # the first S.63 commit (disk evidence, below), then closed; the rows are the evidence it stays closed.
    # EVIDENCE IS THE DISK, read by this suite: a file that appears, a file that is gone, a file that is still there.
    say("\n--- D2. the other routes to an OS path: DIR, SELECT.DIR, OSCOPY, DELETESEQ, SETPTR / SETPU print files -----------")
    outside = os.path.join(BOX, "zzoutside")          # made here, outside every account; the suite removes it again
    shutil.rmtree(outside, ignore_errors=True)
    os.makedirs(os.path.join(outside, "subdir"))
    put(os.path.join(outside, "secret.txt"), "SECRET-OUTSIDE-12345\n")
    put(os.path.join(outside, "subdir", "x.txt"), "x\n")
    # The fixtures are in their original state here (section I, which switches every account on, comes last).
    for name in ("zzoff", "zzsh", "zzon", "zzos"):
        d = os.path.join(BOX, "user_accounts", name)
        osx = FIXTURES[name][1].lower() == "yes"
        victim = os.path.join(outside, "victim-%s.txt" % name)
        dropped = os.path.join(outside, "dropped-%s.txt" % name)
        printed = os.path.join(outside, "printed-%s.txt" % name)
        printed_tcl = os.path.join(outside, "printedtcl-%s.txt" % name)
        for junk in (victim, dropped, printed, printed_tcl, os.path.join(d, "got1.txt"), os.path.join(d, "gotdir"),
                     os.path.join(d, "copy-in-account.txt"), os.path.join(d, "mine-to-delete.txt"),
                     os.path.join(d, "tcl-got.txt"), os.path.join(d, "tcl-own.txt")):
            if os.path.isdir(junk):
                shutil.rmtree(junk)
            elif os.path.exists(junk):
                os.remove(junk)
        put(victim, "to be deleted\n")
        put(os.path.join(d, "mine-to-delete.txt"), "an ordinary file of the account\n")
        put(os.path.join(d, "bp", "zzroute"), "\n".join([
            "   crt 'T begin'",
            "   s1 = 99",
            "   call !oscopy('%s/secret.txt', 'got1.txt', 1, s1)" % outside,
            "   crt 'T oscopy-read ':s1",
            "   s2 = 99",
            "   call !oscopy('inside.txt', '%s', 1, s2)" % dropped,
            "   crt 'T oscopy-write ':s2",
            "   s3 = 99",
            "   call !ioscopy('%s/subdir', 'gotdir', s3)" % outside,
            "   crt 'T ioscopy ':s3",
            "   s4 = 99",
            "   call !oscopy('inside.txt', 'copy-in-account.txt', 1, s4)",
            "   crt 'T oscopy-inside ':s4",
            "   x = dir('%s')" % outside,
            "   crt 'T dir-outside ':dcount(x, @fm)",
            "   y = dir('.')",
            "   crt 'T dir-own ':(dcount(y, @fm) > 0)",
            "   deleteseq '%s' then" % victim,
            "      crt 'T deleteseq-outside DONE'",
            "   end else",
            "      crt 'T deleteseq-outside ELSE ':status()",
            "   end",
            "   deleteseq 'mine-to-delete.txt' then",
            "      crt 'T deleteseq-own DONE'",
            "   end else",
            "      crt 'T deleteseq-own ELSE ':status()",
            "   end",
            "   crt 'T end'", "end", ""]))
        put(os.path.join(d, "bp", "zzprint"), "\n".join([
            "   crt 'T print-begin'",
            "   setpu 1, 1, 3",
            "   setpu 11, 1, '%s'" % printed,
            "   print on 1 'T printed-line-from-setpu'",
            "   printer close on 1",
            "   crt 'T print-end'", "end", ""]))
        # The "$hold name" marker is the ordinary way to name a hold file, and a SETPU program can write it itself.
        # The kernel turns it into $hold/name with no check that name stays below $hold, so "..", three times from
        # the account's own $hold directory, lands in the outside directory.  $hold must exist for the unguarded build
        # to be able to make the file at all, so this fixture makes it (a real account has one from CREATE.ACCOUNT).
        os.makedirs(os.path.join(d, "$hold"), exist_ok=True)
        holdfile = os.path.join(outside, "hold-%s.txt" % name)
        if os.path.exists(holdfile):
            os.remove(holdfile)
        put(os.path.join(d, "bp", "zzhold"), "\n".join([
            "   crt 'T hold-begin'",
            "   setpu 1, 1, 3",
            "   setpu 11, 1, '$hold ../../../zzoutside/hold-%s.txt'" % name,
            "   print on 1 'T printed-via-hold-marker'",
            "   printer close on 1",
            "   crt 'T hold-end'", "end", ""]))
        out = plain(name, ["BASIC bp zzroute zzprint zzhold", "RUN bp zzroute"])
        if not has(out, r"^Compiled 3 program\(s\) with no errors"):
            row("D2: %s's probe programs compiled" % name, False, "output=%r" % (out[-4:],))
            continue
        if not has(out, r"^T end$"):
            row("D2: %s's route probe ran to its end" % name, False, "output=%r" % (out[-5:],))
            continue
        secret_in = os.path.join(d, "got1.txt")
        if osx:
            row("D2: %s (OS.EXECUTE yes) !OSCOPY reads a file outside the account: status 0, and the content is here" % name,
                has(out, r"^T oscopy-read 0$") and os.path.exists(secret_in)
                and "SECRET-OUTSIDE-12345" in open(secret_in).read(), "output=%r" % (out[:6],))
            row("D2: %s !OSCOPY writes a file outside the account, and !IOSCOPY copies a directory in" % name,
                has(out, r"^T oscopy-write 0$") and os.path.exists(dropped) and has(out, r"^T ioscopy 0$")
                and os.path.isdir(os.path.join(d, "gotdir")), "output=%r" % (out[:6],))
            row("D2: %s DIR() lists the directory outside the account (secret.txt and subdir at least)" % name,
                any(re.match(r"^T dir-outside (\d+)$", ln) and int(ln.split()[-1]) >= 2 for ln in out), "output=%r" % (out,))
            row("D2: %s DELETESEQ removes a file outside the account: ... DONE, and it is gone" % name,
                has(out, r"^T deleteseq-outside DONE$") and not os.path.exists(victim), "exists=%s" % os.path.exists(victim))
        else:
            row("D2: %s (OS.EXECUTE no) !OSCOPY of a file outside is refused, status -4: nothing was copied in" % name,
                has(out, r"^T oscopy-read -4$") and not os.path.exists(secret_in), "output=%r" % (out[:6],))
            row("D2: %s !OSCOPY into a place outside is refused (-4): no file was made there" % name,
                has(out, r"^T oscopy-write -4$") and not os.path.exists(dropped), "exists=%s" % os.path.exists(dropped))
            row("D2: %s !IOSCOPY of a directory outside is refused (-4): nothing was copied in" % name,
                has(out, r"^T ioscopy -4$") and not os.path.exists(os.path.join(d, "gotdir")), "output=%r" % (out[:6],))
            row("D2: %s DIR() of a directory outside gives nothing (0 entries)" % name,
                has(out, r"^T dir-outside 0$"), "output=%r" % (out,))
            row("D2: %s DELETESEQ of a file outside is refused (ELSE 3035) and the file is still there" % name,
                has(out, r"^T deleteseq-outside ELSE 3035$") and os.path.exists(victim),
                "output=%r exists=%s" % (out[-4:], os.path.exists(victim)))
        row("D2: %s may still copy inside its own directory, list it and delete its own file (controls)" % name,
            has(out, r"^T oscopy-inside 0$") and os.path.exists(os.path.join(d, "copy-in-account.txt"))
            and has(out, r"^T dir-own 1$") and has(out, r"^T deleteseq-own DONE$")
            and not os.path.exists(os.path.join(d, "mine-to-delete.txt")), "output=%r" % (out,))

        # the verbs, and the print unit
        out = plain(name, ["OSCOPY %s/secret.txt tcl-got.txt" % outside, "SELECT.DIR %s" % outside,
                           "OSCOPY inside.txt tcl-own.txt", "SELECT.DIR sub",
                           "SETPTR 1,80,60,0,0,3,AS PATHNAME %s,BRIEF" % printed_tcl])
        gotf = os.path.join(d, "tcl-got.txt")
        if osx:
            row("D2: %s the OSCOPY verb copies a file in from outside, and SELECT.DIR lists outside" % name,
                has(out, r"copied to tcl-got\.txt$") and os.path.exists(gotf) and has(out, r"^\d+ record\(s\) selected")
                and not has(out, "has no OS access"), "output=%r" % (out,))
            row("D2: %s SETPTR ... AS PATHNAME outside the account is accepted" % name,
                not has(out, "has no OS access") and not has(out, "Unexpected token"), "output=%r" % (out[-3:],))
        else:
            row("D2: %s the OSCOPY verb is refused in 11180's words, and nothing came in" % name,
                has(out, re.escape("%s has no OS access, so a file or directory outside its own account cannot be reached" % name))
                and not os.path.exists(gotf) and not has(out, r"copied to tcl-got"), "output=%r" % (out,))
            refusals = sum(1 for ln in out if "has no OS access" in ln)
            selected = [ln for ln in out if re.match(r"^\d+ record\(s\) selected", ln)]
            row("D2: %s SELECT.DIR of a directory outside is refused: three refusals in all (OSCOPY, SELECT.DIR, SETPTR), "
                "and the one SELECT.DIR that answered is its own empty sub (0 records)" % name,
                refusals == 3 and selected == ["0 record(s) selected to select list 0"], "output=%r" % (out,))
            row("D2: %s SETPTR ... AS PATHNAME outside the account is refused (11180) and no file was made" % name,
                refusals == 3 and not os.path.exists(printed_tcl), "output=%r" % (out[-3:],))
        row("D2: %s the OSCOPY verb still copies inside the account, and SELECT.DIR of its own sub works" % name,
            has(out, r"inside\.txt copied to tcl-own\.txt$") and os.path.exists(os.path.join(d, "tcl-own.txt")),
            "output=%r" % (out,))

        out = plain(name, ["RUN bp zzprint"])
        if osx:
            row("D2: %s the SETPU statement prints into a file outside the account (the file is there, with the line)" % name,
                os.path.exists(printed) and "T printed-line-from-setpu" in open(printed).read() and has(out, r"^T print-end$"),
                "output=%r exists=%s" % (out, os.path.exists(printed)))
        else:
            row("D2: %s the SETPU statement cannot print into a file outside the account: refused at print time, no file, "
                "the program stopped" % name,
                has(out, "has no OS access") and not os.path.exists(printed) and not has(out, r"^T print-end$"),
                "output=%r exists=%s" % (out, os.path.exists(printed)))
        out = plain(name, ["RUN bp zzhold"])
        if osx:
            row("D2: %s a '$hold ../../..' print name reaches outside the account (it may: it holds OS.EXECUTE)" % name,
                os.path.exists(holdfile) and has(out, r"^T hold-end$"), "output=%r exists=%s" % (out, os.path.exists(holdfile)))
        else:
            row("D2: %s a '$hold ../../..' print name does NOT climb out of the account: refused, no file, the program stopped"
                % name, has(out, "has no OS access") and not os.path.exists(holdfile) and not has(out, r"^T hold-end$"),
                "output=%r exists=%s" % (out, os.path.exists(holdfile)))
    shutil.rmtree(outside, ignore_errors=True)

    # --- D4. OPENTEMP (14 Oct 26, openQM 431 and 440; owner: "security first") -----------------------------------------
    # OPENTEMP makes a dynamic file and deletes it when the file variable is closed.  A pathname it is given, and the file it
    # makes itself in the temp directory (SYSTEM(38), outside every account), are both OS paths and both ask the account's
    # OS-access question: an account with OS.EXECUTE no may use OPENTEMP only on a name inside its own directory.  Evidence is
    # the disk: no file made outside (or in the temp directory) for an account without the gate, none left behind for one
    # with it, and an existing file or directory is never taken (it would be deleted at close).
    say("\n--- D4. OPENTEMP: the temp directory and a named path ask the OS-access gate; the file goes at close ---------")
    outside4 = os.path.join(BOX, "zzoutside4")
    shutil.rmtree(outside4, ignore_errors=True)
    os.makedirs(outside4)
    for name in ("zzoff", "zzsh", "zzon", "zzos"):
        d = os.path.join(BOX, "user_accounts", name)
        osx = FIXTURES[name][1].lower() == "yes"
        put(os.path.join(d, "bp", "zztmp"), "\n".join([
            "   crt 'T begin'",
            "   td = system(38)",
            "   crt 'T tempdir ':td",
            "   opentemp to f1 then",
            "      crt 'T null OPENED'",
            "      write 'hello' on f1, 'k1'",
            "      read r1 from f1, 'k1' then crt 'T null-read ':r1 else crt 'T null-read NONE'",
            "      close f1",
            "      crt 'T null-closed'",
            "   end else",
            "      crt 'T null REFUSED ':status()",
            "   end",
            "   opentemp 'zztmpin' to f2 then",
            "      crt 'T inside OPENED'",
            "      close f2",
            "   end else",
            "      crt 'T inside REFUSED ':status()",
            "   end",
            "   opentemp '%s/zztmpout' to f3 then" % outside4,
            "      crt 'T outside OPENED'",
            "      close f3",
            "   end else",
            "      crt 'T outside REFUSED ':status()",
            "   end",
            "   opentemp 'bp' to f4 then",
            "      crt 'T existing OPENED'",
            "      close f4",
            "   end else",
            "      crt 'T existing REFUSED ':status()",
            "   end",
            "   opentemp 'zztmpnt' ecs non.transactional to f5 then",
            "      crt 'T options OPENED'",
            "      close f5",
            "   end else",
            "      crt 'T options REFUSED ':status()",
            "   end",
            "   crt 'T end'", "end", ""]))
        out = plain(name, ["BASIC bp zztmp", "RUN bp zztmp"])
        if not has(out, r"^Compiled 1 program\(s\) with no errors"):
            row("D4: %s's OPENTEMP probe compiled" % name, False, "output=%r" % (out[-4:],))
            continue
        tdir = None
        for ln in out:
            m = re.match(r"^T tempdir (.+)$", ln)
            if m:
                tdir = m.group(1)
        before = set(os.listdir(tdir)) if tdir and os.path.isdir(tdir) else None
        out = plain(name, ["RUN bp zztmp"])
        after = set(os.listdir(tdir)) if tdir and os.path.isdir(tdir) else None
        if not has(out, r"^T end$") or before is None or after is None:
            row("D4: %s's OPENTEMP probe ran to its end and the temp directory %r could be listed" % (name, tdir), False,
                "output=%r" % (out[-6:],))
            continue
        leftover = sorted(n for n in after - before if n.startswith("sdtmp"))
        row("D4: %s OPENTEMP leaves nothing behind: no sdtmp file in %s, none of zztmpin / zztmpout / zztmpnt on disk, and the "
            "directory 'bp' it was pointed at is still there" % (name, tdir),
            not leftover and not os.path.exists(os.path.join(d, "zztmpin")) and not os.path.exists(os.path.join(outside4, "zztmpout"))
            and not os.path.exists(os.path.join(d, "zztmpnt")) and os.path.isdir(os.path.join(d, "bp")),
            "leftover=%r" % leftover)
        row("D4: %s OPENTEMP of an existing name is refused, in every account (it would be deleted at close)" % name,
            has(out, r"^T existing REFUSED ") and not has(out, r"^T existing OPENED$"), "output=%r" % (out,))
        row("D4: %s OPENTEMP of a name inside its own directory works, and takes ECS and NON.TRANSACTIONAL" % name,
            has(out, r"^T inside OPENED$") and has(out, r"^T options OPENED$"), "output=%r" % (out,))
        if osx:
            row("D4: %s (OS.EXECUTE yes) OPENTEMP in the temp directory works: a record written and read back, then closed" % name,
                has(out, r"^T null OPENED$") and has(out, r"^T null-read hello$") and has(out, r"^T null-closed$"), "output=%r" % (out,))
            row("D4: %s (OS.EXECUTE yes) OPENTEMP of a path outside the account works" % name, has(out, r"^T outside OPENED$"),
                "output=%r" % (out,))
        else:
            row("D4: %s (OS.EXECUTE no) OPENTEMP in the temp directory is REFUSED (ELSE 3035), nothing made there" % name,
                has(out, r"^T null REFUSED 3035$") and not leftover, "output=%r leftover=%r" % (out, leftover))
            row("D4: %s (OS.EXECUTE no) OPENTEMP of a path outside the account is REFUSED (ELSE 3035)" % name,
                has(out, r"^T outside REFUSED 3035$"), "output=%r" % (out,))
    shutil.rmtree(outside4, ignore_errors=True)

    # --- D5. SKT$INFO.TRACE (15 Oct 26, openQM 162) -------------------------------------------------------------------------
    # SET.SOCKET.MODE(skt, SKT$INFO.TRACE, path) makes a log of the data sent and received, in a file the program names, so it is an
    # OS path like OPENSEQ's: an account with OS.EXECUTE no may trace only into its own directory.  Evidence is the disk: the log
    # outside the account exists, with the data in it, only for an account with the gate; the log inside exists for all of them;
    # a null path ends the trace (what is sent after it is not in the log); a link at the path is not followed.  The server is a
    # thread of this process that echoes what it receives.
    say("\n--- D5. SKT$INFO.TRACE: a log of a socket's traffic is an OS path, and the gate decides where it may go --------")
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(8)
    srv_port = srv.getsockname()[1]
    srv_stop = threading.Event()

    def echo_one(conn):
        conn.settimeout(10)
        try:
            while True:
                data = conn.recv(4096)
                if not data:
                    break
                conn.sendall(data)
        except OSError:
            pass
        finally:
            conn.close()

    def echo_server():
        srv.settimeout(0.5)
        while not srv_stop.is_set():
            try:
                conn, _ = srv.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(target=echo_one, args=(conn,), daemon=True).start()

    srv_thread = threading.Thread(target=echo_server, daemon=True)
    srv_thread.start()
    outside5 = os.path.join(BOX, "zzoutside5")
    shutil.rmtree(outside5, ignore_errors=True)
    os.makedirs(outside5)
    for name in ("zzoff", "zzsh", "zzon", "zzos"):
        d = os.path.join(BOX, "user_accounts", name)
        osx = FIXTURES[name][1].lower() == "yes"
        out_log = os.path.join(outside5, "skt-%s.log" % name)
        own_log = os.path.join(d, "skt-own.log")
        link_log = os.path.join(d, "skt-link.log")
        link_target = os.path.join(outside5, "link-target-%s.txt" % name)
        for junk in (out_log, own_log, link_log, link_target):
            if os.path.lexists(junk):
                os.remove(junk)
        put(link_target, "NOT A LOG\n")
        os.symlink(link_target, link_log)
        put(os.path.join(d, "bp", "zzskt"), "\n".join([
            "$include keys.h",
            "   sk1 = open.socket('127.0.0.1', %d, 0, 5)" % srv_port,
            "   if status() # 0 then crt 'T open-failed ':status() ; stop",
            "   ok1 = set.socket.mode(sk1, SKT$INFO.TRACE, '%s')" % out_log,
            "   crt 'T trace-outside ':ok1",
            "   n = write.socket(sk1, 'hello':char(1), 0, 0)",
            "   r = read.socket(sk1, 100, SKT$BLOCKING, 5)",
            "   close.socket sk1",
            "   sk2 = open.socket('127.0.0.1', %d, 0, 5)" % srv_port,
            "   ok2 = set.socket.mode(sk2, SKT$INFO.TRACE, 'skt-own.log')",
            "   crt 'T trace-inside ':ok2",
            "   n = write.socket(sk2, 'A':char(1):'B', 0, 0)",
            "   r = read.socket(sk2, 100, SKT$BLOCKING, 5)",
            "   ok3 = set.socket.mode(sk2, SKT$INFO.TRACE, '')",
            "   crt 'T trace-off ':ok3",
            "   n = write.socket(sk2, 'afteroff', 0, 0)",
            "   r = read.socket(sk2, 100, SKT$BLOCKING, 5)",
            "   close.socket sk2",
            "   sk3 = open.socket('127.0.0.1', %d, 0, 5)" % srv_port,
            "   ok4 = set.socket.mode(sk3, SKT$INFO.TRACE, 'skt-link.log')",
            "   crt 'T trace-link ':ok4",
            "   n = write.socket(sk3, 'viaLink', 0, 0)",
            "   r = read.socket(sk3, 100, SKT$BLOCKING, 5)",
            "   close.socket sk3",
            "   crt 'T end'", "end", ""]))
        out = plain(name, ["BASIC bp zzskt", "RUN bp zzskt"])
        if not has(out, r"^Compiled 1 program\(s\) with no errors"):
            row("D5: %s's trace probe compiled" % name, False, "output=%r" % (out[-4:],))
            continue
        if not has(out, r"^T end$"):
            row("D5: %s's trace probe ran to its end" % name, False, "output=%r" % (out[-6:],))
            continue
        own_text = open(own_log, errors="replace").read() if os.path.exists(own_log) else None
        row("D5: %s a trace into its own directory works for every account: the log has SEND 3 bytes and RECV 3 bytes, "
            "and the bytes 41 01 42 in hexadecimal and A.B as characters" % name,
            has(out, r"^T trace-inside 1$") and own_text is not None and "SEND 3 bytes" in own_text and "RECV 3 bytes" in own_text
            and "41 01 42" in own_text and "A.B" in own_text, "output=%r log=%r" % (out, own_text))
        row("D5: %s a null path ends the trace: what was sent after it ('afteroff') is not in the log" % name,
            has(out, r"^T trace-off 1$") and own_text is not None and "afteroff" not in own_text and "SEND 8 bytes" not in own_text,
            "log=%r" % own_text)
        row("D5: %s the log is made owner-only (mode 0600)" % name,
            os.path.exists(own_log) and (os.stat(own_log).st_mode & 0o777) == 0o600,
            "mode=%s" % (oct(os.stat(own_log).st_mode & 0o777) if os.path.exists(own_log) else None))
        row("D5: %s a link at the log path is not followed: SET.SOCKET.MODE gives 0 and the file it pointed at is untouched" % name,
            has(out, r"^T trace-link 0$") and open(link_target).read() == "NOT A LOG\n", "target=%r output=%r" % (open(link_target).read(), out))
        if osx:
            out_text = open(out_log, errors="replace").read() if os.path.exists(out_log) else None
            row("D5: %s (OS.EXECUTE yes) a trace into a place outside the account works: the log is there, with SEND 6 bytes, "
                "RECV 6 bytes and the bytes 68 65 6c 6c 6f 01" % name,
                has(out, r"^T trace-outside 1$") and out_text is not None and "SEND 6 bytes" in out_text
                and "RECV 6 bytes" in out_text and "68 65 6c 6c 6f 01" in out_text, "output=%r log=%r" % (out, out_text))
        else:
            row("D5: %s (OS.EXECUTE no) a trace into a place outside the account is REFUSED: SET.SOCKET.MODE gives 0 and no log "
                "was made there" % name,
                has(out, r"^T trace-outside 0$") and not os.path.exists(out_log), "output=%r exists=%s" % (out, os.path.exists(out_log)))
    srv_stop.set()
    srv.close()
    shutil.rmtree(outside5, ignore_errors=True)

    # --- D3. a VOC pointer is a way to name a file ------------------------------------------------------------------
    # 13 Oct 26 (second sitting; owner: "try to make tighter ... q pointers should only be allowed into an account the
    # user can logto in any case").  The first S.63 asked about a path a program NAMED, and a file named THROUGH THE VOC was
    # an SD file and not asked, so an account could write an F-pointer into its own VOC - or make one with CREATE.FILE ...
    # PATHNAME - at any directory its Linux user could read.  _VOC_REF now asks, for everybody but SDSYS: an F-pointer must
    # end inside the account, or inside the account a Q-pointer was followed into, or be the stock pointer of the same id in
    # NEWVOC, or the account holds os-on; a Q-pointer into a registered account is followed only if the user could LOGTO it
    # (a member of its group, not suspended), WHETHER OR NOT the account holds os-on; a path is the OS gate's question.
    say("\n--- D3. VOC pointers: an F-pointer outside the account, and a Q-pointer into an account the user could not LOGTO ---")
    my_gids = set(os.getgroups()) | {os.getgid()}
    foreign = None
    for g in grp.getgrall():
        if g.gr_gid not in my_gids and USER not in g.gr_mem:
            foreign = g.gr_name
            break
    if foreign is None:
        bail("no group exists that the sandbox user is not in, so a Q-pointer into an account it could not LOGTO cannot be staged")
    out3 = os.path.join(BOX, "zzoutside3")
    shutil.rmtree(out3, ignore_errors=True)
    os.makedirs(out3)
    put(os.path.join(out3, "secret.txt"), "SECRET-OUTSIDE-12345\n")
    for name in ("zznolog", "zzsusp"):
        build_account(name)
    rec = (reg_read("zznolog") + [""] * 8)[:8]
    rec[2] = foreign
    reg_write("zznolog", rec)
    rec = (reg_read("zzsusp") + [""] * 8)[:8]
    rec[4] = "SUSPENDED"
    reg_write("zzsusp", rec)
    for name in ("zzon", "zznolog", "zzsusp"):
        put(os.path.join(BOX, "user_accounts", name, "bp", "qprobe"), "hello-from-%s\n" % name)
    put(os.path.join(SYS, "bp", "zzvoc3"), "\n".join([
        "$internal",
        "   accts = 'zzoff':@fm:'zzsh':@fm:'zzon':@fm:'zzos'",
        "   for i = 1 to dcount(accts, @fm)",
        "      a = accts<i>",
        "      openpath '%s/user_accounts/':a:'/voc' to v else" % BOX,
        "         crt 'VOC3 cannot open the VOC of ':a",
        "         stop",
        "      end",
        "      write 'F':@fm:'%s' to v, 'outptr'" % out3,
        "      write 'Q':@fm:'zzon':@fm:'bp' to v, 'qok'",
        "      write 'Q':@fm:'zznolog':@fm:'bp' to v, 'qnolog'",
        "      write 'Q':@fm:'zzsusp':@fm:'bp' to v, 'qsusp'",
        "      write 'Q':@fm:'/etc':@fm:'voc' to v, 'qraw'",
        "      close v",
        "   next i",
        "   crt 'VOC3 done'",
        "end", ""]))
    out = adm(["BASIC bp zzvoc3", "RUN bp zzvoc3"], internal=True)
    if not has(out, r"^VOC3 done$"):
        bail("the D3 fixture VOC records were not written:\n" + "\n".join(out[-6:]))
    vp_prog = "\n".join([
        "   crt 'V begin'",
        "   names = 'outptr':@fm:'qok':@fm:'qnolog':@fm:'qsusp':@fm:'qraw':@fm:'newptr':@fm:'sd.accounts':@fm:'syscom'"
        ":@fm:'sd.voclib':@fm:'$map':@fm:'bp'",
        "   for i = 1 to dcount(names, @fm)",
        "      nm = names<i>",
        "      open nm to f then",
        "         crt 'V ':nm:' OPENED'",
        "         close f",
        "      end else",
        "         crt 'V ':nm:' REFUSED ':status()",
        "      end",
        "   next i",
        "   open 'outptr' to g1 then",
        "      read r1 from g1, 'secret.txt' then",
        "         crt 'V outptr-read ':r1<1>",
        "      end else",
        "         crt 'V outptr-read NONE'",
        "      end",
        "      close g1",
        "   end",
        "   open 'qok' to g2 then",
        "      read r2 from g2, 'qprobe' then",
        "         crt 'V qok-read ':r2<1>",
        "      end else",
        "         crt 'V qok-read NONE'",
        "      end",
        "      close g2",
        "   end",
        "   crt 'V end'", "end", ""])

    def vp_states(lines):
        got = {}
        for ln in lines:
            m = re.match(r"^V (\S+) (OPENED|REFUSED \d+)$", ln)
            if m:
                got[m.group(1)] = m.group(2)
            m = re.match(r"^V (outptr-read|qok-read) (.*)$", ln)
            if m:
                got[m.group(1)] = m.group(2)
        return got

    stock = ("syscom", "sd.voclib", "$map", "bp")
    refused = "REFUSED 3035"
    states = {}
    for name in ("zzoff", "zzsh", "zzon", "zzos"):
        d = os.path.join(BOX, "user_accounts", name)
        osx = FIXTURES[name][1].lower() == "yes"
        put(os.path.join(d, "bp", "zzvp"), vp_prog)
        # CREATE.FILE makes the dictionary part beside the data directory, so each account gets a directory of its own
        # (a second CREATE.FILE at the same path says the file exists: 3007)
        np_dir = os.path.join(BOX, "zznp-%s" % name)
        os.makedirs(np_dir, exist_ok=True)
        put(os.path.join(np_dir, "secret.txt"), "SECRET-OUTSIDE-12345\n")
        out = plain(name, ["CREATE.FILE newptr DIRECTORY PATHNAME %s" % np_dir, "BASIC bp zzvp", "RUN bp zzvp"])
        if not has(out, r"^V end$"):
            row("D3: %s's pointer probe ran to its end" % name, False, "output=%r" % (out[-6:],))
            continue
        got = vp_states(out)
        states[name] = got
        row("D3: %s (os %s) STOCK pointers still open: syscom, sd.voclib, $map and its own bp" % (name, FIXTURES[name][1]),
            all(got.get(k) == "OPENED" for k in stock), "%r" % ({k: got.get(k) for k in stock},))
        row("D3: %s may follow a Q-pointer into an account it could LOGTO (zzon, same group): opened, and it reads zzon's record"
            % name, got.get("qok") == "OPENED" and got.get("qok-read") == "hello-from-zzon", "qok=%r read=%r" % (got.get("qok"), got.get("qok-read")))
        row("D3: %s is refused a Q-pointer into an account whose group it is not in (3035) - whether or not it holds os-on" % name,
            got.get("qnolog") == refused, "qnolog=%r" % (got.get("qnolog"),))
        row("D3: %s is refused a Q-pointer into a SUSPENDED account (3035), as LOGTO would" % name,
            got.get("qsusp") == refused, "qsusp=%r" % (got.get("qsusp"),))
        if osx:
            row("D3: %s (os-on) opens an F-pointer to a directory outside the account, reads its record, and opens the pointer "
                "CREATE.FILE ... PATHNAME made" % name,
                got.get("outptr") == "OPENED" and got.get("outptr-read") == "SECRET-OUTSIDE-12345" and got.get("newptr") == "OPENED",
                "outptr=%r read=%r newptr=%r" % (got.get("outptr"), got.get("outptr-read"), got.get("newptr")))
            row("D3: %s (os-on) is NOT stopped by the gate on a Q-pointer that names a path (it fails, if at all, for another reason)"
                % name, got.get("qraw") != refused, "qraw=%r" % (got.get("qraw"),))
        else:
            row("D3: %s (os-off) is refused an F-pointer to a directory outside the account (3035), and reads nothing"
                % name, got.get("outptr") == refused and "outptr-read" not in got, "outptr=%r read=%r" % (got.get("outptr"), got.get("outptr-read")))
            row("D3: %s (os-off) is refused the pointer CREATE.FILE ... PATHNAME made at a directory outside (3035)" % name,
                got.get("newptr") == refused, "newptr=%r" % (got.get("newptr"),))
            row("D3: %s (os-off) is refused a Q-pointer that names a path outside the account (3035)" % name,
                got.get("qraw") == refused, "qraw=%r" % (got.get("qraw"),))
    # the stock Q-pointer into SDSYS is judged against the administrator's own result, so a sandbox whose SDSYS has no
    # `accounts` entry does not turn this into a row about something else
    adm_got = vp_states(sd(os.path.join(BOX, "user_accounts", "zzoff"), ["BASIC bp zzvp", "RUN bp zzvp"], admin=True, account="zzoff"))
    row("D3: the administrator opens every pointer: the one into an account nobody could LOGTO, the suspended one, the outside directory",
        adm_got.get("qnolog") == "OPENED" and adm_got.get("qsusp") == "OPENED" and adm_got.get("outptr") == "OPENED",
        "%r" % ({k: adm_got.get(k) for k in ("qnolog", "qsusp", "outptr")},))
    for name, got in states.items():
        row("D3: %s opens sd.accounts (the stock Q-pointer into SDSYS, an account it could not LOGTO) exactly as the administrator does: %s"
            % (name, adm_got.get("sd.accounts")), got.get("sd.accounts") == adm_got.get("sd.accounts") and adm_got.get("sd.accounts") is not None,
            "%r vs %r" % (got.get("sd.accounts"), adm_got.get("sd.accounts")))
    shutil.rmtree(out3, ignore_errors=True)
    for name in ("zzoff", "zzsh", "zzon", "zzos"):
        shutil.rmtree(os.path.join(BOX, "zznp-%s" % name), ignore_errors=True)
        shutil.rmtree(os.path.join(BOX, "zznp-%s.dic" % name), ignore_errors=True)

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
    # 18 Oct 26: a word after the action used to be read by nobody, so the first action was done and the second dropped without a word.
    before = fields("zzmod")
    out = mod("zzmod", "SH-ON", "OS-ON")
    row("G: two actions in one command are refused (11714), naming the second, and the FIRST was not done either",
        has(out, r"^modify\.account does one action at a time, and nothing was changed: OS-ON was not carried out") and
        fields("zzmod") == before == ("no", "no"), "out=%r reg=%r (was %r)" % (out[-2:], fields("zzmod"), before))
    out = mod("zzmod", "SH-ON")
    row("G: CONTROL: the same first action alone is done", has(out, "^Account zzmod has SH yes, OS.EXECUTE no$") and fields("zzmod") == ("yes", "no"),
        "out=%r reg=%r" % (out[-2:], fields("zzmod")))
    mod("zzmod", "SH-OFF")
    # ADD is only read for an account whose Linux group exists, so this account carries the sandbox user's own group; the refusal comes
    # before the membership test and the sudo call, which is why nothing in /etc/group can change here.
    reg_write("zzadd", ["/x", "", GROUP])
    out = mod("zzadd", "ADD", "zzperson", "zzperson2")
    row("G: ADD with two user names is refused (11714) before anything is done: no 'added' and no 'not a member' line",
        has(out, r"^modify\.account does one action at a time, and nothing was changed: zzperson2 was not carried out") and
        not has(out, r"added to group|not a member of|is already a member"), "out=%r" % (out[-3:],))

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
