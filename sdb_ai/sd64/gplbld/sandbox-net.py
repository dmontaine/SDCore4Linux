#!/usr/bin/env python3
#
# sandbox-net.py - the NET gate and the SDNet server definitions (S.65 slice 1, the owner's request of 17 Oct 2026).  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-net.py <dir> [--build] [--sections=a,b]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or absent);
# without it <dir> must already be built.  Exit 0 every row passed, 1 a row failed, 2 it could not run.  --sections= runs only the named
# parts (gate, logto, modify, manifest, defs, connect, netcred, netlogin, ordinary); no flag runs all of them.
#
# START-HISTORY:
# 17 Oct 26 dm  New.  S.65 slice 1: register field 15 (ACC$NET), K_NET 127, the user table's UG_NET bit, MODIFY.ACCOUNT NET-ON / NET-OFF,
#               the manifest key net, LOGIN / CPROC's logto (and the way back under OPTION STACKED.ACCOUNT); and the SDSYS-only verbs
#               set.server, delete.server and list.servers with the file netservers they keep (!netdefs).  NOTHING OPENS A REMOTE FILE
#               YET: the gate has no effect and the definitions are used by nothing, and these rows say only that they are right.
#               ***NOT YET RUN*** - written on 17 Oct without a sandbox to run it on.  The first run is the first evidence; read a red
#               row as a possible wrong expectation in this file as well as a fault in the tree.
# 17 Oct 26 dm  S.65 slice 2a: the section "connect" - set.server name host port account CONNECT.  A TLS 1.3 server of this process (the
#               ssl module, 127.0.0.1, a random port, no client certificate, one thread each, a lifetime limit and a 10 second limit on
#               every connection) stands in for the other SD server; its certificates and keys are made with the openssl command line
#               and the pin the rows expect is computed by the openssl command line too (x509 -pubkey | pkey -pubin -outform DER |
#               dgst -sha256), never by SD.  The servers count the connections they accept, the handshakes they complete and the
#               application bytes they receive (none: a handshake only).  ***NOT YET RUN*** - written without a sandbox to run it on;
#               read a red row as a possible wrong expectation here as well as a fault in the tree.
# 17 Oct 26 dm  S.65 slice 2b: the sections "netcred" and "netlogin" - the person's login on a server.  netcred drives $netcred (READ, WRITE,
#               DELETE, EXISTS) through an internal probe on a scratch credential root, with the DISK as the evidence: the line written, the
#               modes, the refusal of a file or a directory that is not private (group and world bits, a link, a directory in the file's
#               place), a damaged file, a pin that differs, every shape of value.  netlogin runs set.netlogin and delete.netlogin as ordinary
#               accounts against a FAKE SD API SERVER (gplbld/netfake.py: TLS 1.3, the Ack byte, the packet framing of gpl.bp/sdclient and the
#               server side of SCRAM-SHA-256, computed with hashlib) that records every packet it receives; every expected value (salt,
#               iterations, ClientKey, ServerKey, the proof) is computed here with hashlib/hmac, never by SD.
#               HOW THE SANDBOX REACHES WHAT IS ROOT'S ON AN INSTALL.  $netcred's root is /var/lib/sd-net, made by root through
#               `sudo -n sd-elevate netcred-dir`; a sandbox has neither.  So this suite edits the SANDBOX'S OWN COPIES of gpl.bp/netcred
#               (the NETCRED.ROOT define -> a scratch directory) and gpl.bp/setnetlogin (the elevate command -> a shell script that makes the
#               scratch directory the way the helper would: root 755, <user> 700, and prints `netcred-dir: <path>`), as sandbox-gates.py
#               patches CPROC, and recompiles them.  THE PATCHES ARE THE ONLY DIFFERENCE from the shipped programs; what they cannot show -
#               that the helper and the sudoers line work - is test-accelevate-units.py and an install (witness-release-run.sh).
#               NOT WRITTEN HERE, and why: (1) the administrator's refusal 11462 (sdsys has no Linux login): in a sandbox the administrator IS
#               the sandbox user, so a row would show the administrator being let through instead (it does so below, as evidence that the NET
#               gate and the account list are not asked of it); (2) a file or directory owned by ANOTHER user (a sandbox user cannot chown);
#               (3) the channel binding, which Python's ssl cannot compute (netfake.py says so): witness-release-run.sh on an install;
#               (4) a server that goes silent (a 15 second read timeout per row); (5) the real sudoers line and the real helper.
#               ***NOT YET RUN*** - written without a sandbox to run it on; read a red row as a possible wrong expectation as well as a fault.
# END-HISTORY
#
# It uses sandbox-gates.py's way of making ordinary sessions in fixture accounts, by loading that file.  The sandbox user plays SDSYS (the
# session is an administrator only when SDTEST_ADMIN=1, which g.adm() and g.sd(admin=True) set); every other session is ordinary.
#
# WHAT IT CANNOT SHOW.  (1) The API server's load of the gate (api.net.grant): a sandbox cannot host an API session, so that is a
# witness row.  (2) The file's owner and its mode against ANOTHER operating system user: the sandbox user is SDSYS and every
# fixture account's user, so the mode (0644) is read from the disk but whether an unprivileged user can write the file is not tried; an
# ordinary account's refusal here is the S.63 OS-access gate (status 3035), which an os-on account does not meet.  (3) The audit lines of
# an INSTALL (they are in a file only root reads); the section "connect" reads the SANDBOX's own audit file, <sandbox>/sys/audit, and a row
# that needs it fails when it cannot be read.  (4) CREATE.ACCOUNT, which makes Linux users.  (5) A connection that is never answered: the
# 5 second connect timeout needs an address that drops packets, which a sandbox cannot count on, so only refused, reset, non-TLS and
# unresolvable targets are tried.
#
# THE INSTRUMENTS.  zznk (a $internal verb in every fixture account) prints "NK net=<0|1> admin=<0|1>": the kernel's own answer to
# K$NET and whether the session is an administrator; zznkset sets it from internal code and reads it back.  For the verbs the evidence is
# the DISK: the bytes of <sandbox>/sys/netservers before and after each command, line by line, and the message the verb printed,
# matched against the text of the message file the sandbox was built with.  A refusal row demands the failure wording AND no success
# wording AND the file unchanged AND no netservers.new left behind.  Every session is ended: the input always ends with OFF, the only
# question the verbs ask (replace?) is answered by a line in the same input, and an unanswered one is read as a no at the end of input.

import datetime
import errno
import hashlib
import importlib.util
import os
import pwd
import re
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
from stat import S_IMODE, S_ISREG

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import netfake                      # the fake API server and the SCRAM arithmetic of section netlogin (slice 2b); self-tested: netfake.py --selftest
spec = importlib.util.spec_from_file_location("sandbox_gates", os.path.join(HERE, "sandbox-gates.py"))
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
RUN = "%05d" % (os.getpid() % 100000)
passed = failed = 0

PIN_A = "0123456789abcdef" * 4
PIN_B = "fedcba9876543210" * 4

# name -> (register field 8 ACC$OS.EXEC, register field 15 ACC$NET); None for field 15 means a record that has no such field at all
ACCOUNTS = {
    "zznoff": ("no", "no"),
    "zznon": ("no", "yes"),
    "zznblank": ("no", None),
    "zzncase": ("no", "Yes"),
    "zzntrue": ("no", "true"),
    "zzntrim": ("no", " yes "),
    "zznmod": ("no", "no"),          # MODIFY.ACCOUNT works on this one
    "zznverb": ("no", "no"),         # an ordinary account whose VOC holds the three verbs
    "zznosx": ("yes", "no"),         # OS.EXECUTE yes: the control that an outside file can be reached when the S.63 gate lets it
}
WANT_NET = {"zznoff": 0, "zznon": 1, "zznblank": 0, "zzncase": 1, "zzntrue": 0, "zzntrim": 1, "zznmod": 0, "zznverb": 0, "zznosx": 0}
WHY = {"zznoff": "no", "zznon": "yes", "zznblank": "a record with no field 15", "zzncase": "Yes (the test ignores case)",
       "zzntrue": "true (only yes is yes)", "zzntrim": "' yes ' (spaces are trimmed)", "zznmod": "no", "zznverb": "no", "zznosx": "no"}


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
    say("sandbox-net: CANNOT RUN - " + msg)
    sys.exit(2)


def acct_path(name):
    return os.path.join(g.BOX, "user_accounts", name)


def netfile():
    return os.path.join(g.SYS, "netservers")


def msg(n, *args):
    """The text of message N as the sandbox was built with it, the %n places filled."""
    p = os.path.join(g.SYS, "messages", str(n))
    if not os.path.exists(p):
        bail("the sandbox holds no message %d (%s)" % (n, p))
    with open(p, encoding="utf-8", errors="replace") as f:
        t = f.read().strip("\n")
    for i, a in enumerate(args, 1):
        t = t.replace("%%%d" % i, str(a))
    return t


def has_line(out, text):
    return any(ln == text for ln in out)


def has_text(out, text):
    return any(text in ln for ln in out)


def snap():
    """The bytes of the definitions file, or None when there is none."""
    try:
        with open(netfile(), "rb") as f:
            return f.read()
    except OSError:
        return None


def file_lines():
    b = snap()
    if b is None:
        return None
    return b.decode("ascii", errors="replace").split("\n")[:-1] if b.endswith(b"\n") else b.decode("ascii", errors="replace").split("\n")


def adm1(*cmds):
    return g.adm(list(cmds))


# ---- fixtures -------------------------------------------------------------------------------------------------------------

def reg_record(name, path):
    osx, net = ACCOUNTS[name]
    rec = [path, "", g.GROUP, "", "", "", "no", osx, "", "yes", "yes", "yes", "", ""]       # fields 1-14: the edit gates on, so the account can compile
    if net is not None:
        rec.append(net)                                                                          # field 15
    return rec


def build(name):
    g.EXTRA_FIXTURES[name] = ("no", "no")
    path = g.build_account(name)
    g.reg_write(name, reg_record(name, path))
    return path


ZZNK = "\n".join([
    "$internal", "program zznk", "$catalog $zznk", "$include keys.h", "$include int$keys.h",
    "   crt 'NK net=':kernel(K$NET, -1):' admin=':kernel(K$ADMINISTRATOR, -1)", "end", ""])
ZZNKSET = "\n".join([
    "$internal", "program zznkset", "$catalog $zznkset", "$include keys.h", "$include int$keys.h",
    "   a = kernel(K$NET, -1)", "   b = kernel(K$NET, 1)", "   c = kernel(K$NET, -1)", "   d = kernel(K$NET, 0)", "   e = kernel(K$NET, -1)",
    "   crt 'NS before=':a:' set1=':b:' ask1=':c:' set0=':d:' ask0=':e", "end", ""])


def fixer_text():
    names = "'" + "':@fm:'".join(ACCOUNTS) + "'"
    return "\n".join([
        "$internal",
        "   for each a in %s" % names,
        "      openpath '%s':@ds:a:@ds:'voc' to v else crt 'NETFIX no voc ':a ; stop" % os.path.join(g.BOX, "user_accounts"),
        "      write 'V':@fm:'CA':@fm:'$zznk' to v, 'zznk'",
        "      write 'V':@fm:'CA':@fm:'$zznkset' to v, 'zznkset'",
        "      if a = 'zznverb' then",
        "         write 'V':@fm:'CA':@fm:'$setserver' to v, 'set.server'",
        "         write 'V':@fm:'CA':@fm:'$deleteserver' to v, 'delete.server'",
        "         write 'V':@fm:'CA':@fm:'$listservers' to v, 'list.servers'",
        "      end",
        "      close v",
        "   next a",
        "   crt 'NETFIX done'",
        "end", ""])


def nk(out):
    for ln in out:
        m = re.match(r"^NK net=(\d+) admin=(\d+)$", ln)
        if m:
            return m.group(1), m.group(2)
    return None


def nk_all(out):
    return [m.group(1) for m in (re.match(r"^NK net=(\d+) admin=\d+$", ln) for ln in out) if m]


# ---- the gate ---------------------------------------------------------------------------------------------------------------

def gate_section():
    say("\n--- the gate: K$NET as the session holds it, loaded at sign-on from register field 15 (yes is on, anything else is off) ---")
    for name in ACCOUNTS:
        out = g.plain(name, ["ZZNK"])
        r = nk(out)
        want = WANT_NET[name]
        row("%s (field 15: %s) -> net=%d, not an administrator" % (name, WHY[name], want),
            r is not None and r[0] == str(want) and r[1] == "0", "NK line: %r  output: %r" % (r, out[-3:]))
    for name in ("zznoff", "zznon"):
        r = nk(g.sd(acct_path(name), ["ZZNK"], admin=True, account=name))
        row("%s, the administrator (SDTEST_ADMIN=1): admin=1, which is how the later remote-open check lets SDSYS through" % name,
            r is not None and r[1] == "1", repr(r))
    out = g.plain("zznoff", ["ZZNKSET", "ZZNK"])
    row("zznoff: an internal program sets K$NET and reads it back (before 0, set 1 -> 1, set 0 -> 0)",
        has_line(out, "NS before=0 set1=1 ask1=1 set0=0 ask0=0"), repr(out[:4]))
    out = g.plain("zznon", ["ZZNKSET"])
    row("zznon: an internal program turns it off and on again, and starts from the register's 1",
        has_line(out, "NS before=1 set1=1 ask1=1 set0=0 ask0=0"), repr(out[:4]))
    out = g.plain("zznon", ["ZZNKSET", "ZZNK"])
    row("zznon: a session that turned it off still reports what its program left (0): the key is the session's, not the register's",
        nk(out) is not None and nk(out)[0] == "0", repr(out[:4]))
    out = g.plain("zznon", ["ZZNK"])
    row("CONTROL: a NEW session in zznon starts at the register's 1 again (the setter changed nothing on disk)",
        nk(out) is not None and nk(out)[0] == "1", repr(out[:3]))


# ---- LOGTO ---------------------------------------------------------------------------------------------------------------------

def logto_section():
    say("\n--- LOGTO: the gate is the account the session is IN (account-scoped), reloaded at LOGTO and given back on the way out ---")
    out = g.plain("zznoff", ["LOGTO zznon", "ZZNK"])
    row("signed on to zznoff (net 0), LOGTO zznon: the session reports net=1", nk_all(out) == ["1"], repr(out[:6]))
    out = g.plain("zznon", ["LOGTO zznoff", "ZZNK"])
    row("signed on to zznon (net 1), LOGTO zznoff: net=0 (zznon's grant does not follow the person)", nk_all(out) == ["0"], repr(out[:6]))
    out = g.plain("zznon", ["ZZNK", "LOGTO zznoff", "ZZNK", "LOGTO zznon", "ZZNK"])
    row("zznon, then zznoff, then zznon again at the prompt: 1, 0, 1", nk_all(out) == ["1", "0", "1"], repr(out[:9]))
    out = g.plain("zznoff", ["ZZNK", "LOGTO zzncase", "ZZNK", "LOGTO zzntrue", "ZZNK"])
    row("zznoff, then zzncase (Yes), then zzntrue (true): 0, 1, 0", nk_all(out) == ["0", "1", "0"], repr(out[:9]))

    # the way back: OPTION STACKED.ACCOUNT puts the account (and, since S.65, the gate) back when an EXECUTEd command ends
    progs = {}
    for acct, other in (("zznoff", "zznon"), ("zznon", "zznoff")):
        prog = "zznst%s%s" % (acct[3:], RUN)
        progs[acct] = prog
        g.put(os.path.join(acct_path(acct), "bp", prog), "\n".join([
            "   execute 'LOGTO %s'" % other, "   crt 'PATH ':@path", "   execute 'ZZNK' capturing nk",
            "   crt 'NKOUT ':trim(nk)", "end", ""]))
        out = g.plain(acct, ["BASIC bp " + prog])
        row("setup: %s's program compiled with no errors" % acct, g.has(out, r"^Compiled 1 program\(s\) with no errors"), repr(out[-3:]))

    def result(out):
        path = next((ln[5:].strip() for ln in out if ln.startswith("PATH ")), None)
        m = next((re.search(r"net=(\d+)", ln) for ln in out if ln.startswith("NKOUT ")), None)
        return path, (m.group(1) if m else None)
    for acct, other, want_net_back in (("zznoff", "zznon", "0"), ("zznon", "zznoff", "1")):
        out = g.plain(acct, ["RUN bp " + progs[acct]])
        path, n = result(out)
        row("CONTROL, no option: after EXECUTE 'LOGTO %s' the session STAYS in %s with %s's gate (%s)" % (other, other, other, ACCOUNTS[other][1]),
            path is not None and path.endswith("/" + other) and n == str(WANT_NET[other]), repr((path, n)))
        out = g.plain(acct, ["OPTION STACKED.ACCOUNT", "RUN bp " + progs[acct]])
        path, n = result(out)
        row("OPTION STACKED.ACCOUNT: after EXECUTE 'LOGTO %s' the session is back in %s with its OWN gate (net=%s)" % (other, acct, want_net_back),
            path is not None and path.endswith("/" + acct) and n == want_net_back, repr((path, n)))
    for acct in progs:
        for d in ("bp", "bp.out"):
            p = os.path.join(acct_path(acct), d, progs[acct])
            if os.path.exists(p):
                os.remove(p)


# ---- MODIFY.ACCOUNT --------------------------------------------------------------------------------------------------------------

def fields15(name):
    return (g.reg_read(name) + [""] * 16)[:15]


def modify_section():
    say("\n--- MODIFY.ACCOUNT NET-ON / NET-OFF: register field 15, message 11411, the other fields untouched ---------------------")
    n = "zznmod"
    before = fields15(n)
    row("setup: zznmod starts with field 15 = no", before[14] == "no", repr(before))
    steps = [("modify.account zznmod net-on", "yes"), ("MODIFY.ACCOUNT zznmod NET-OFF", "no"), ("modify.account zznmod NET-ON", "yes"),
             ("MODIFY.ACCOUNT zznmod net-off", "no")]
    for cmd, state in steps:
        out = g.adm([cmd])
        row("%s says the state with 11411: 'Account zznmod has NET %s'" % (cmd, state), has_line(out, msg(11411, "zznmod", state)), repr(out[-3:]))
        f = fields15(n)
        row("...and writes field 15 (%s) and no other field" % state, f[14] == state and f[:14] == before[:14], repr(f))
    out = g.adm(["modify.account zznmod net-off"])
    row("a switch already in that state says so (10080) and changes nothing", has_line(out, msg(10080, "zznmod")) and fields15(n) == before, repr(out[-3:]))
    g.adm(["modify.account zznmod net-on"])
    out = g.plain(n, ["ZZNK"])
    row("the switch takes effect at the next entry: a NEW session in zznmod holds net=1", nk(out) is not None and nk(out)[0] == "1", repr(out[:3]))
    g.adm(["modify.account zznmod net-off"])
    out = g.plain(n, ["ZZNK"])
    row("...and NET-OFF takes it away at the entry after that (net=0)", nk(out) is not None and nk(out)[0] == "0", repr(out[:3]))
    out = g.adm(["MODIFY.ACCOUNT"])
    row("MODIFY.ACCOUNT's syntax lines name net-on | net-off", g.has(out, r"net-on \| net-off"), repr(out[-8:]))
    out = g.adm(["MODIFY.ACCOUNT zznmod NETON"])
    row("a word that is not one of them is refused, and the list of words names net-on and net-off",
        g.has(out, r"modify\.account Action Must Be") and g.has(out, r"net-on, net-off"), repr(out[-4:]))
    sdsys_before = g.reg_read("sdsys")
    out = g.adm(["modify.account sdsys net-on"])
    row("sdsys is refused (2202) and its register record is the same", has_line(out, msg(2202)) and g.reg_read("sdsys") == sdsys_before, repr(out[-3:]))
    out = g.adm(["modify.account zznnosuch net-on"])
    row("an account that is not in the register is refused (6003)", has_line(out, msg(6003)) and not os.path.exists(os.path.join(g.SYS, "accounts", "zznnosuch")), repr(out[-3:]))

    # a GROUP account takes the word as SD-ON does; SH-ON, which a group may not have, is the control that the group test is on
    g.reg_write("zznmodg", ["/tmp/zznmodg", "", "sdg_zznmodg", "", "", "", "", "", "", "", "", "", "", "", ""])
    out = g.adm(["modify.account zznmodg net-on"])
    row("a GROUP account (sdg_) is accepted: 'Account zznmodg has NET yes', field 15 = yes", has_line(out, msg(11411, "zznmodg", "yes")) and fields15("zznmodg")[14] == "yes", repr(out[-3:]))
    out = g.adm(["modify.account zznmodg net-off"])
    row("...and NET-OFF takes it off again", has_line(out, msg(11411, "zznmodg", "no")) and fields15("zznmodg")[14] == "no", repr(out[-3:]))
    out = g.adm(["modify.account zznmodg sh-on"])
    row("CONTROL: SH-ON on the same group account is refused (10105) and field 7 stays blank", has_line(out, msg(10105, "zznmodg")) and fields15("zznmodg")[6] == "", repr(out[-3:]))

    # an ordinary account has no such verb
    before = fields15("zznoff")
    out = g.plain("zznoff", ["MODIFY.ACCOUNT zznoff NET-ON"])
    row("an ordinary account cannot run MODIFY.ACCOUNT (not in its VOC) and its field 15 is unchanged", g.has(out, r"(?i)is not in your VOC|not found in VOC") and fields15("zznoff") == before, repr(out[-3:]))


# ---- the manifest ---------------------------------------------------------------------------------------------------------------

def manifest_section():
    say("\n--- the account manifest (BACKUP.ACCOUNT / RESTORE.ACCOUNT) carries the gate --------------------------------------------")
    g.put(os.path.join(g.SYS, "gpl.bp", "zznetinfo"), "\n".join([
        "$internal", "program zznetinfo", "$catalog $zznetinfo", "$include keys.h", "$include int$keys.h",
        "   openpath @sdsys:@ds:'accounts' to acc.f else crt 'NI no register' ; stop",
        "   for each a in 'zznmana':@fm:'zznmanb':@fm:'zznmand':@fm:'zznmang'",
        "      read rec from acc.f, a then",
        "         call !acc_os_info(a, rec, info, err)",
        "         crt 'NI ':a:' ':convert(@fm, '|', info):' err=':err",
        "      end else crt 'NI no record ':a",
        "   next a", "end", ""]))
    out = g.adm(["BASIC gpl.bp zznetinfo"], internal=True)
    if not g.has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("zznetinfo did not compile:\n" + "\n".join(out[-8:]))
    g.reg_write("zznmana", ["/tmp/zznmana", "", "sdu_zznmana", "", "", "", "no", "no", "", "no", "no", "no", "", "", "yes"])
    g.reg_write("zznmanb", ["/tmp/zznmanb", "", "sdu_zznmanb", "", "", "", "yes", "yes"])                      # no gate fields at all
    g.reg_write("zznmand", ["/tmp/zznmand", "", "sdu_zznmand", "", "", "", "no", "no", "", "yes", "yes", "yes", "", "", "no"])
    g.reg_write("zznmang", ["/tmp/zznmang", "", "sdg_zznmang", "", "", "", "", "", "", "", "", "", "", "", "yes"])
    out = g.adm(["RUN gpl.bp zznetinfo"], internal=True)
    pick = lambda a: [x for x in out if x.startswith("NI %s " % a)]
    row("zznmana (net yes, the edit gates no): net: 1 after edit.dict: 0 in its manifest",
        g.has(pick("zznmana"), r"\|edit\.dict: 0\|net: 1(\||\s|$)"), repr(pick("zznmana")[:2]))
    row("zznmanb (a record with no gate fields): net: 0, as a blank is off", g.has(pick("zznmanb"), r"\|net: 0(\||\s|$)"), repr(pick("zznmanb")[:2]))
    row("zznmand (net no, the edit gates yes): net: 0 and edit.voc: 1 edit.bp: 1 edit.dict: 1 - the fields are independent",
        g.has(pick("zznmand"), r"\|edit\.voc: 1\|edit\.bp: 1\|edit\.dict: 1\|net: 0(\||\s|$)"), repr(pick("zznmand")[:2]))
    row("zznmang (a GROUP account with field 15 = yes): type GROUP and no net key (only a user account has one)",
        g.has(pick("zznmang"), r"type: GROUP") and not g.has(pick("zznmang"), r"net:"), repr(pick("zznmang")[:2]))


# ---- the definitions ---------------------------------------------------------------------------------------------------------------

DATE_RE = r"\d{4}-\d{2}-\d{2}"


def dates():
    d = datetime.date.today()
    return {d.isoformat(), (d - datetime.timedelta(days=1)).isoformat(), (d + datetime.timedelta(days=1)).isoformat()}


def line_is(line, fields):
    """A stored line is these eight fields, the last a date from today (give or take midnight)."""
    if line is None:
        return False
    parts = line.split("|")
    return len(parts) == 8 and parts[:7] == list(fields) and parts[7] in dates()


SUCCESS = r"\) (is defined|was replaced)$"


def refused(label, cmd, expect, answers=()):
    """A definition that must be refused: every expected message is printed as a line of its own, no success wording is, the file is the
    same bytes as before, and there is no netservers.new."""
    before = snap()
    out = adm1(cmd, *answers)
    after = snap()
    miss = [t for t in expect if not has_line(out, t)]
    row("%s -> refused, nothing written" % label,
        not miss and not g.has(out, SUCCESS) and before == after and not os.path.exists(netfile() + ".new"),
        "missing %r; file unchanged=%s; output %r" % (miss, before == after, out[-4:]))
    return out


def defs_section():
    say("\n--- set.server / list.servers / delete.server, run as the administrator in the sandbox ----------------------------------")
    for p in (netfile(), netfile() + ".new", netfile() + ".lock"):
        if os.path.exists(p):
            os.remove(p)
            say("  [note] a leftover %s was removed" % os.path.basename(p))
    ok_cmd = lambda name, host="valid.example.org", port="4247", account="acct", pin=PIN_A, extra="": \
        "set.server %s %s %s %s %s%s" % (name, host, port, account, pin, (" " + extra) if extra else "")

    # -- the first listing: no file at all
    out = adm1("list.servers")
    row("list.servers with no file: 'No servers are defined', and listing makes no file", has_line(out, msg(11433)) and snap() is None, repr(out[-3:]))
    out = adm1("delete.server nosuch")
    row("delete.server with no file: 'No server is defined with the name nosuch', and no file made", has_line(out, msg(11430, "nosuch")) and snap() is None, repr(out[-3:]))

    # -- usage
    for cmd, label in (("set.server", "no words"), ("set.server alpha1 host", "two words"), ("set.server a b c d", "four words")):       # five words are the five required fields: a field message, not usage
        out = refused("set.server with %s" % label, cmd, [msg(11412)])
        row("...and it says where the pin comes from (11413)", g.has(out, "^" + re.escape(msg(11413)[:60])), repr(out[-3:]))

    # -- the first definition: well formed, mode 644, one line
    old = os.umask(0o077)
    try:
        out = adm1(ok_cmd("alpha1", "host1.example.org", "4247", "reader", PIN_A, "write accounts zznon,zznoff"))
    finally:
        os.umask(old)
    row("a valid set.server says 'Server alpha1 (host1.example.org:4247) is defined'", has_line(out, msg(11424, "alpha1", "host1.example.org", "4247")), repr(out[-3:]))
    row("...and lists no 'no account is listed' warning (accounts were given)", not has_text(out, msg(11439, "alpha1")[:30]), repr(out[-3:]))
    lines = file_lines()
    row("...the file netservers holds exactly one line", lines is not None and len(lines) == 1, repr(lines))
    row("...of eight fields: name|host|port|account|pin|mode|accounts|created",
        lines is not None and line_is(lines[0], ["alpha1", "host1.example.org", "4247", "reader", PIN_A, "write", "zznon,zznoff"]), repr(lines))
    try:
        st = os.stat(netfile())
        row("...mode 0644 although this process ran with umask 077 (the program sets 022 around the creation), owned by the session's user, a plain file",
            (st.st_mode & 0o7777) == 0o644 and st.st_uid == os.getuid() and os.path.isfile(netfile()), oct(st.st_mode))
    except OSError as e:
        row("...mode 0644 (the file could not be examined)", False, repr(e))
    row("...no copy netservers.new and no lock record netservers.lock are left behind",
        not os.path.exists(netfile() + ".new") and not os.path.exists(netfile() + ".lock"), "")
    first = snap()

    # -- a second one with the defaults, and one typed in upper case
    out = adm1(ok_cmd("beta", "h2.example.net", "4249", "admin", PIN_B))
    row("a second server with no mode and no accounts: defined, and told that no account may use it yet (11439)",
        has_line(out, msg(11424, "beta", "h2.example.net", "4249")) and has_line(out, msg(11439, "beta")), repr(out[-3:]))
    lines = file_lines()
    row("...two lines now, the first byte for byte as it was", lines is not None and len(lines) == 2 and snap().startswith(first), repr(lines))
    row("...the new line has mode read and an EMPTY accounts field (two bars), nothing else",
        lines is not None and len(lines) == 2 and line_is(lines[1], ["beta", "h2.example.net", "4249", "admin", PIN_B, "read", ""]), repr(lines))
    out = adm1("set.server UPPEROK Host3.Example.ORG 04250 Remote.Acct %s WRITE ACCOUNTS ZZNON" % PIN_A.upper())
    lines = file_lines() or []
    row("upper case is converted: name, host, pin, mode and accounts are stored in lower case, the port without its zero, the remote account as typed",
        len(lines) == 3 and line_is(lines[2], ["upperok", "host3.example.org", "4250", "Remote.Acct", PIN_A, "write", "zznon"]), repr(lines))
    out = adm1("set.server dupacc h4.example.net 4247 acct %s read accounts zznon,zznon,zznoff,zznon" % PIN_A)
    lines = file_lines() or []
    row("a name listed twice in the accounts list is kept once (zznon,zznoff)",
        len(lines) == 4 and line_is(lines[3], ["dupacc", "h4.example.net", "4247", "acct", PIN_A, "read", "zznon,zznoff"]), repr(lines))
    adm1("delete.server dupacc")

    # -- list.servers
    out = adm1("list.servers")
    want = [msg(11434, "alpha1", "host1.example.org:4247", "reader/write", PIN_A[:16] + "...  zznon,zznoff"),
            msg(11434, "beta", "h2.example.net:4249", "admin/read", PIN_B[:16] + "...  " + msg(11438)),
            msg(11434, "upperok", "host3.example.org:4250", "Remote.Acct/write", PIN_A[:16] + "...  zznon")]
    in_order = all(w in out for w in want) and out.index(want[0]) < out.index(want[1]) < out.index(want[2])
    row("list.servers: one line for each, in the order they were defined: name, host:port, account/mode, the pin shortened to 16 digits and '...', the accounts or 'none'",
        in_order, repr(out[-5:]))
    row("...and NO full pin appears anywhere in the list", not has_text(out, PIN_A) and not has_text(out, PIN_B), repr([x for x in out if PIN_A in x or PIN_B in x]))
    out = adm1("list.servers alpha1")
    row("list.servers alpha1: that server only, with the FULL pin and the date it was defined",
        has_line(out, msg(11434, "alpha1", "host1.example.org:4247", "reader/write", PIN_A + "  zznon,zznoff"))
        and any(re.fullmatch(re.escape(msg(11435, "@@")).replace("@@", DATE_RE), ln) for ln in out) and not has_text(out, "beta"), repr(out[-4:]))
    out = adm1("LIST.SERVERS ALPHA1")
    row("...the name is converted to lower case", has_line(out, msg(11434, "alpha1", "host1.example.org:4247", "reader/write", PIN_A + "  zznon,zznoff")), repr(out[-3:]))
    out = adm1("list.servers nosuch")
    row("list.servers of an unknown name: 'No server is defined with the name nosuch'", has_line(out, msg(11430, "nosuch")), repr(out[-3:]))
    out = adm1("list.servers a b")
    row("list.servers with two words: its usage line (11432)", has_line(out, msg(11432)), repr(out[-3:]))
    row("CONTROL: none of the listings changed the file", snap().startswith(first), "")

    # -- replacing a name asks
    before = snap()
    new_cmd = ok_cmd("alpha1", "other.example.org", "4300", "reader", PIN_B, "write")
    prompt = msg(11423, "alpha1", "host1.example.org:4247")
    for answer, label in (("n", "n"), ("", "an empty line"), ("N", "N")):
        out = adm1(new_cmd, answer)
        row("replacing alpha1 with the answer '%s': the question is put, 'Server alpha1 was not changed', and the file is the same bytes" % label,
            has_text(out, prompt) and has_text(out, msg(11426, "alpha1")) and not g.has(out, SUCCESS) and snap() == before, repr(out[-3:]))
    out = adm1(new_cmd, "maybe", "n")
    row("an answer that is neither y nor n puts the question again, and the n after it ends it: unchanged",
        sum(ln.count(prompt) for ln in out) >= 2 and has_text(out, msg(11426, "alpha1")) and snap() == before, repr(out[-4:]))
    out = adm1(new_cmd)
    row("the question with NO answer in the input (end of input) is a no: unchanged, and the session ends", has_text(out, msg(11426, "alpha1")) and snap() == before, repr(out[-3:]))
    out = adm1(new_cmd, "y")
    lines = file_lines() or []
    row("the answer y replaces it: 'Server alpha1 (other.example.org:4300) was replaced', in the same place, still three lines",
        has_text(out, msg(11425, "alpha1", "other.example.org", "4300")) and len(lines) == 3
        and line_is(lines[0], ["alpha1", "other.example.org", "4300", "reader", PIN_B, "write", ""]), repr(lines))
    row("...the other two lines are as they were", len(lines) == 3 and lines[1:] == before.decode("ascii").split("\n")[1:3], repr(lines))
    row("...and it warns that no account is listed any more (11439) - replacing does not keep the old accounts",
        has_line(out, msg(11439, "alpha1")), repr(out[-3:]))
    out = adm1(ok_cmd("alpha1", "host1.example.org", "4247", "reader", PIN_A, "write accounts zznon,zznoff no.query"))
    lines = file_lines() or []
    row("NO.QUERY replaces with no question at all", has_text(out, msg(11425, "alpha1", "host1.example.org", "4247")) and not has_text(out, "is already defined")
        and len(lines) == 3 and line_is(lines[0], ["alpha1", "host1.example.org", "4247", "reader", PIN_A, "write", "zznon,zznoff"]), repr(out[-3:]))
    out = adm1(ok_cmd("beta", "h2.example.net", "4249", "admin", PIN_B, "no.query"), ok_cmd("ALPHA1", "host1.example.org", "4247", "reader", PIN_A, "write accounts zznon,zznoff"), "Y")
    lines = file_lines() or []
    row("the name is converted before the test (ALPHA1 is alpha1) and the answer Y is accepted", has_text(out, msg(11425, "alpha1", "host1.example.org", "4247")) and len(lines) == 3, repr(out[-3:]))

    # -- boundary controls: the values just inside every limit are accepted, then the values just outside are refused
    ctl = [
        ("a name of 16 characters", ok_cmd("abcdefghijklmnop"), ["abcdefghijklmnop", "valid.example.org", "4247", "acct", PIN_A, "read", ""]),
        ("port 1", ok_cmd("ctl", port="1", extra="no.query"), ["ctl", "valid.example.org", "1", "acct", PIN_A, "read", ""]),
        ("port 65535", ok_cmd("ctl", port="65535", extra="no.query"), ["ctl", "valid.example.org", "65535", "acct", PIN_A, "read", ""]),
        ("a host of 253 characters", ok_cmd("ctl", host="a" * 253, extra="no.query"), ["ctl", "a" * 253, "4247", "acct", PIN_A, "read", ""]),
        ("an IPv6 literal host", ok_cmd("ctl", host="fe80::1", extra="no.query"), ["ctl", "fe80::1", "4247", "acct", PIN_A, "read", ""]),
        ("a host that starts with a digit and holds hyphens", ok_cmd("ctl", host="10-0-0-1.example", extra="no.query"), ["ctl", "10-0-0-1.example", "4247", "acct", PIN_A, "read", ""]),
        ("a remote account of 32 characters", ok_cmd("ctl", account="B" * 32, extra="no.query"), ["ctl", "valid.example.org", "4247", "B" * 32, PIN_A, "read", ""]),
        ("a remote account with dots, underscores and hyphens", ok_cmd("ctl", account="a.b_c-d", extra="no.query"), ["ctl", "valid.example.org", "4247", "a.b_c-d", PIN_A, "read", ""]),
    ]
    for label, cmd, fields in ctl:
        out = adm1(cmd)
        lines = file_lines() or []
        got = [x for x in lines if x.startswith(fields[0] + "|")]
        row("CONTROL, inside the limit: %s is accepted and stored" % label, len(got) == 1 and line_is(got[0], fields) and not g.has(out, r"is not valid"), repr((out[-2:], got)))

    # -- every invalid field, one at a time, each refused with its own message and each writing NOTHING
    say("  (every invalid field, one at a time: the message of its own, the file the same bytes)")
    for name in ("1abc", "ab_cd", "a.b", "a" * 17, "-abc"):
        refused("name %r" % name, ok_cmd(name), [msg(11414, name)])
    for host in ("-bad.org", ".bad.org", "ba|d.org", "ba/d.org", "bad_host", "a" * 254, "ba@d.org"):
        refused("host %r" % (host if len(host) < 40 else host[:10] + "..."), ok_cmd("hostx", host=host), [msg(11415, host)])
    for port in ("0", "65536", "abc", "-1", "12ab", "1.5", "123456", "99999", "00000"):
        refused("port %s" % port, ok_cmd("portx", port=port), [msg(11416, port)])
    for account in ("bad@acct", "a" * 33, "bad/acct", "bad:acct"):
        refused("remote account %r" % (account if len(account) < 40 else account[:10] + "..."), ok_cmd("accx", account=account), [msg(11417, account)])
    for label, pin in (("63 digits", PIN_A[:63]), ("65 digits", PIN_A + "a"), ("64 with a non-hex character", PIN_A[:63] + "g"), ("xyz", "xyz"), ("64 with a hyphen", PIN_A[:63] + "-")):
        refused("pin of %s" % label, ok_cmd("pinx", pin=pin), [msg(11418)])
    refused("mode 'append'", ok_cmd("modex", extra="append"), [msg(11419, "append")])
    refused("two mode words (read write)", ok_cmd("modex", extra="read write"), [msg(2018, "write")])
    refused("an unknown extra word", ok_cmd("modex", extra="read frobnicate"), [msg(2018, "frobnicate")])
    refused("accounts: an unregistered account", ok_cmd("accl", extra="accounts zznnosuch"), [msg(11421, "zznnosuch")])
    refused("accounts: a registered account first and an unregistered one after it (nothing is written for the good one)",
            ok_cmd("accl", extra="accounts zznon,zznnosuch"), [msg(11421, "zznnosuch")])
    refused("accounts: an empty name between commas", ok_cmd("accl", extra="accounts zznon,,zznoff"), [msg(11420)])
    refused("accounts: a name with a bar", ok_cmd("accl", extra="accounts zznon,a|b"), [msg(11420)])
    refused("accounts: a name of 33 characters", ok_cmd("accl", extra="accounts " + "a" * 33), [msg(11420)])
    long_list = ",".join(("a" * 31 + str(i % 10)) for i in range(64))
    refused("accounts: a list of %d characters (over 2000)" % len(long_list), ok_cmd("accl", extra="accounts " + long_list), [msg(11420)])
    refused("a space inside the remote account shifts the words: the pin position holds 'acct' and a stray word is left",
            "set.server spacex valid.example.org 4247 bad acct %s" % PIN_A, [msg(11418)])
    out = refused("name, port and pin all wrong at once: every message is shown, still nothing is written",
                  ok_cmd("1x", port="0", pin="zz"), [msg(11414, "1x"), msg(11416, "0"), msg(11418)])

    # -- the limit of ten
    lines = file_lines() or []
    fill = [("s%02d" % i) for i in range(1, 30)]
    todo = [n for n in fill if not any(x.startswith(n + "|") for x in lines)][:max(0, 10 - len(lines))]
    out = adm1(*[ok_cmd(n) for n in todo])
    lines = file_lines() or []
    row("filled to ten definitions (%d more were defined)" % len(todo), len(lines) == 10 and all(has_line(out, msg(11424, n, "valid.example.org", "4247")) for n in todo), repr((len(lines), out[-2:])))
    before = snap()
    refused("an 11th definition (a new name)", ok_cmd("eleven"), [msg(11422, 10)])
    out = adm1(ok_cmd("s05", host="changed.example.org", extra="no.query"))
    lines = file_lines() or []
    pos = [i for i, x in enumerate(file_lines() or []) if x.startswith("s05|")]
    row("CONTROL: with ten defined, REPLACING one is still allowed (no new name), and it stays ten",
        has_text(out, msg(11425, "s05", "changed.example.org", "4247")) and len(lines) == 10 and len(pos) == 1, repr(out[-3:]))

    # -- delete.server
    before = snap()
    out = adm1("delete.server nosuch")
    row("delete.server of an unknown name: 'No server is defined with the name nosuch', the file the same bytes", has_line(out, msg(11430, "nosuch")) and snap() == before, repr(out[-3:]))
    for cmd in ("delete.server", "delete.server a b"):
        out = adm1(cmd)
        row("%r: its usage line (11429), the file the same bytes" % cmd, has_line(out, msg(11429)) and snap() == before, repr(out[-3:]))
    keep = [x for x in (file_lines() or []) if not x.startswith("beta|")]
    out = adm1("delete.server beta")
    lines = file_lines() or []
    row("delete.server beta: 'Server beta was deleted', that line gone and the nine others as they were, in order",
        has_line(out, msg(11431, "beta")) and lines == keep and len(lines) == 9, repr((out[-2:], len(lines))))
    out = adm1("delete.server BETA")
    row("...a second time it is not there (11430), and nothing changes", has_line(out, msg(11430, "beta")) and (file_lines() or []) == keep, repr(out[-3:]))
    out = adm1("DELETE.SERVER UPPEROK")
    row("the name is converted to lower case: DELETE.SERVER UPPEROK removes upperok", has_line(out, msg(11431, "upperok")) and not any(x.startswith("upperok|") for x in (file_lines() or [])), repr(out[-3:]))
    out = adm1("list.servers upperok")
    row("...and list.servers no longer finds it", has_line(out, msg(11430, "upperok")), repr(out[-3:]))
    rest = [x.split("|")[0] for x in (file_lines() or [])]
    out = adm1(*["delete.server " + n for n in rest])
    row("every remaining definition deleted (%d)" % len(rest), all(has_line(out, msg(11431, n)) for n in rest), repr(out[-3:]))
    row("...the file is still there and EMPTY (a list of no servers is a file of no lines), with no copy left", snap() == b"" and not os.path.exists(netfile() + ".new"), repr(snap()))
    out = adm1("list.servers")
    row("...and list.servers says 'No servers are defined' again", has_line(out, msg(11433)), repr(out[-3:]))
    adm1(ok_cmd("alpha1", "host1.example.org", "4247", "reader", PIN_A, "write accounts zznon,zznoff"))
    row("CONTROL: a definition made after the file was emptied is the only line", len(file_lines() or []) == 1, repr(file_lines()))


# ---- an ordinary account --------------------------------------------------------------------------------------------------------

def ordinary_section():
    say("\n--- an ordinary account cannot run the verbs and cannot write the file -----------------------------------------------------")
    if snap() is None:
        adm1("set.server alpha1 host1.example.org 4247 reader %s write accounts zznon" % PIN_A)
    before = snap()
    row("setup: the definitions file exists and has a definition to protect", before is not None and before.count(b"\n") >= 1, repr(before))
    cmds = ["SET.SERVER hackx evil.example.org 4247 acct %s read" % PIN_A, "DELETE.SERVER alpha1", "LIST.SERVERS"]
    out = g.plain("zznoff", cmds)
    n_nf = sum(1 for ln in out if re.search(r"(?i)is not in your VOC|not found in VOC", ln))
    row("zznoff (the verbs are in SDSYS's VOC only): all three are 'not found in VOC', and the file is the same bytes", n_nf == 3 and snap() == before, repr(out[-4:]))
    out = g.plain("zznon", cmds)
    row("zznon (the NET gate ON does not give the verbs): the same", sum(1 for ln in out if re.search(r"(?i)is not in your VOC|not found in VOC", ln)) == 3 and snap() == before, repr(out[-4:]))
    out = g.plain("zznverb", cmds)
    n_ad = sum(1 for ln in out if ln == msg(2001))
    row("zznverb (an ordinary account whose VOC HOLDS the three verbs): each answers 'Command requires administrator privileges', the file unchanged",
        n_ad == 3 and snap() == before and not g.has(out, SUCCESS) and not has_text(out, msg(11433)), repr(out[-4:]))
    nf = netfile()
    prog_w = "\n".join([
        "   crt 'NW begin'",
        "   openseq '%s' to f1 then crt 'NW read-open OK' else crt 'NW read-open REFUSED ':status()" % nf,
        "   openseq '%s.new' to f2 then crt 'NW new-open OK' else" % nf,
        "      st = status()",
        "      if st = 3035 then",
        "         crt 'NW new-open REFUSED ':st",
        "      end else",
        "         create f2 then crt 'NW new-open CREATED' else crt 'NW new-open FAILED ':st",
        "      end",
        "   end",
        "   dok = @true",
        "   deleteseq '%s', 'netservers' else dok = @false" % g.SYS,
        "   crt 'NW delete ':(if dok then 'OK' else 'REFUSED')",
        "   crt 'NW end'", "end", ""])
    for acct in ("zznoff", "zznverb"):
        g.put(os.path.join(acct_path(acct), "bp", "zznetw" + RUN), prog_w)
        out = g.plain(acct, ["BASIC bp zznetw" + RUN, "RUN bp zznetw" + RUN])
        got = {m.group(1): m.group(2) for m in (re.match(r"^NW (\S+) (OK|CREATED|REFUSED(?: \d+)?|FAILED(?: \d+)?)$", ln) for ln in out) if m}
        row("%s: a program that opens the file, makes netservers.new and deletes the file by its operating system path is refused each time (3035 for the opens)"
            % acct, g.has(out, r"^NW end$") and got.get("read-open") == "REFUSED 3035"
            and got.get("new-open") == "REFUSED 3035" and got.get("delete") == "REFUSED", repr((got, out[-3:])))
        row("...and the disk agrees: the file is the same bytes and there is no netservers.new", snap() == before and not os.path.exists(nf + ".new"), repr(snap()))
    prog_r = "\n".join([
        "   openseq '%s' to f1 then crt 'NR read-open OK' else crt 'NR read-open REFUSED ':status()" % nf,
        "   crt 'NR end'", "end", ""])
    g.put(os.path.join(acct_path("zznosx"), "bp", "zznetr" + RUN), prog_r)
    out = g.plain("zznosx", ["BASIC bp zznetr" + RUN, "RUN bp zznetr" + RUN])
    row("CONTROL: the same open from zznosx (OS.EXECUTE yes) WORKS, so the refusals above are the S.63 gate and not a file that cannot be opened (in the sandbox the user is SDSYS)",
        g.has(out, r"^NR read-open OK$") and snap() == before, repr(out[-3:]))
    for acct in ("zznoff", "zznverb", "zznosx"):
        for d in ("bp", "bp.out"):
            for nm in ("zznetw", "zznetr"):
                p = os.path.join(acct_path(acct), d, nm + RUN)
                if os.path.exists(p):
                    os.remove(p)


# ---- set.server ... connect --------------------------------------------------------------------------------------------------------

class TestServer(threading.Thread):
    """A local server standing in for the other SD server.  MODE 'tls': a TLS 1.3 handshake (no client certificate), then it waits up to 2
    seconds for application data (a handshake-only client sends none and closes), then closes.  MODE 'plain': a TCP server that is not TLS -
    it reads what the client sent and answers with an HTTP error, which a TLS client cannot parse.  Counts what it was given:
      count      connections accepted
      handshakes TLS handshakes it completed
      app_bytes  application bytes received after the handshake (0 for a client that only shakes hands)
    It is a daemon thread with a lifetime limit, and every connection has a 10 second limit, so nothing here can hold the suite for ever."""

    def __init__(self, mode, cert=None, key=None, life=1500):
        threading.Thread.__init__(self, daemon=True)
        self.mode = mode
        self.count = 0
        self.handshakes = 0
        self.app_bytes = 0
        self.busy = False
        self.ended = threading.Event()
        self.deadline = time.time() + life
        self.ctx = None
        if mode == "tls":
            self.ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            self.ctx.minimum_version = ssl.TLSVersion.TLSv1_3
            self.ctx.maximum_version = ssl.TLSVersion.TLSv1_3
            self.ctx.load_cert_chain(cert, key)
        self.lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.lsock.bind(("127.0.0.1", 0))
        self.lsock.listen(8)
        self.lsock.settimeout(0.1)
        self.port = self.lsock.getsockname()[1]
        self.start()

    def run(self):
        while not self.ended.is_set() and time.time() < self.deadline:
            try:
                conn, _addr = self.lsock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            self.busy = True
            self.count += 1
            try:
                conn.settimeout(10)
                self.handle(conn)
            except Exception:           # a client that goes away in the middle of a handshake is not the suite's concern
                pass
            finally:
                try:
                    conn.close()
                except OSError:
                    pass
                self.busy = False
        try:
            self.lsock.close()
        except OSError:
            pass

    def handle(self, conn):
        if self.mode == "plain":
            try:
                conn.recv(4096)          # the ClientHello; read first so that closing does not reset the connection
            except OSError:
                pass
            conn.sendall(b"HTTP/1.1 400 Bad Request\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
            return
        tls = self.ctx.wrap_socket(conn, server_side=True)
        self.handshakes += 1
        tls.settimeout(2)
        try:
            self.app_bytes += len(tls.recv(4096))
        except (OSError, ssl.SSLError):
            pass
        try:
            tls.close()
        except OSError:
            pass

    def settle(self, quiet=0.7, limit=8.0):
        """Wait until a connection the client has just made has been accepted and dealt with (a 'no connection' row waits the same time)."""
        time.sleep(quiet)
        t0 = time.time()
        while self.busy and time.time() - t0 < limit:
            time.sleep(0.05)

    def shutdown(self):
        self.ended.set()
        self.join(timeout=5)


def run_ssl(args, data=None):
    """The openssl command line; raises with its error text when it fails."""
    p = subprocess.run(["openssl"] + args, input=data, capture_output=True, timeout=60)
    if p.returncode != 0:
        raise RuntimeError("openssl %s failed: %s" % (" ".join(args[:3]), p.stderr.decode(errors="replace")[-300:]))
    return p.stdout


def make_key(path):
    run_ssl(["genpkey", "-algorithm", "EC", "-pkeyopt", "ec_paramgen_curve:P-256", "-out", path])


def make_cert(key, cert, cn, serial):
    run_ssl(["req", "-x509", "-new", "-key", key, "-out", cert, "-days", "2", "-subj", "/CN=" + cn, "-set_serial", str(serial)])


def expected_pin(cert):
    """The pin a server definition must hold for this certificate, computed WITHOUT sd: the SHA-256 of the SubjectPublicKeyInfo, as
    openssl x509 -pubkey | openssl pkey -pubin -outform DER | openssl dgst -sha256, in lower case hex; Python's hashlib must agree."""
    pub = run_ssl(["x509", "-in", cert, "-pubkey", "-noout"])
    der = run_ssl(["pkey", "-pubin", "-outform", "DER"], pub)
    dg = run_ssl(["dgst", "-sha256", "-binary"], der)
    if dg != hashlib.sha256(der).digest():
        raise RuntimeError("openssl dgst and hashlib disagree about the SubjectPublicKeyInfo of " + cert)
    return dg.hex()


def cert_fingerprint(cert):
    """The SHA-256 of the whole certificate (what a pin must NOT be)."""
    der = run_ssl(["x509", "-in", cert, "-outform", "DER"])
    return run_ssl(["dgst", "-sha256", "-binary"], der).hex()


def closed_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def msg_re(n, *args):
    """Message N as a regular expression; each ARG is a regular expression for its %n place."""
    t = re.escape(msg(n, *["QQ%dQQ" % i for i in range(1, len(args) + 1)]))
    for i, a in enumerate(args, 1):
        t = t.replace("QQ%dQQ" % i, a)
    return t


def first_idx(out, text):
    for i, ln in enumerate(out):
        if text in ln:
            return i
    return -1


def entry(name):
    for ln in file_lines() or []:
        if ln.startswith(name + "|"):
            return ln
    return None


def audit_off():
    """Size of the sandbox's audit file.  SD APPENDS to <sys>/audit and never creates it (audit_message() opens it without O_CREAT: the
    install makes it), so without one every audit line is dropped silently; the file is made here, empty, when it is missing."""
    path = os.path.join(g.SYS, "audit")
    try:
        if not os.path.exists(path):
            with open(path, "ab"):
                pass
        return os.path.getsize(path)
    except OSError:
        return None


def audit_new(off):
    """What the sandbox's audit trail gained since OFF; None when the file cannot be read (a row that needs it then FAILS)."""
    try:
        with open(os.path.join(g.SYS, "audit"), "rb") as f:
            f.seek(off or 0)
            return f.read().decode("utf-8", errors="replace")
    except OSError:
        return None


def audit_rx(name, host, port, mode, replaced, how):
    return r"set\.server name=%s host=%s port=%s mode=%s replaced=%s pin=%s(?:\s|$)" % tuple(re.escape(str(x)) for x in (name, host, port, mode, replaced, how))


def conn_cmd(name, port, extra="", host="127.0.0.1", account="reader", word="connect"):
    return "set.server %s %s %s %s %s%s" % (name, host, port, account, word, (" " + extra) if extra else "")


def conn_run(cmd, answers, srv=None):
    """Run CMD with the ANSWERS in an administrator session.  Returns the output, the definitions file before and after, what the audit
    trail gained, and how many connections SRV accepted meanwhile (None without SRV).  Every session ends: the input ends with OFF."""
    c0 = srv.count if srv is not None else 0
    before = snap()
    a0 = audit_off()
    out = adm1(cmd, *answers)
    after = snap()
    if srv is not None:
        srv.settle()
    return out, before, after, audit_new(a0), (srv.count - c0 if srv is not None else None)


def sock_probe(port):
    return "\n".join([
        "$include keys.h",
        "   skt = open.socket('127.0.0.1', %d, SKT$BLOCKING, 5)" % port,
        "   if status() # 0 then crt 'SK plain-open FAILED ':status() ; stop",
        "   h = socket.info(skt, SKT$INFO.TLS.SPKI)",
        "   crt 'SK plain len=':len(h):' [':h:']'",
        "   close.socket skt",
        "   skt = open.socket('127.0.0.1', %d, SKT$BLOCKING + SKT$TLS, 5)" % port,
        "   if status() # 0 then crt 'SK tls-open FAILED ':status() ; stop",
        "   h = socket.info(skt, SKT$INFO.TLS.SPKI)",
        "   crt 'SK tls len=':len(h):' [':h:']'",
        "   close.socket skt",
        "   crt 'SK end'", "end", ""])


def connect_section():
    say("\n--- set.server ... connect: ONE TLS handshake, the hash of the key shown, SDSYS asked; a local TLS 1.3 server stands in for the other SD ---")
    for p in (netfile(), netfile() + ".new", netfile() + ".lock"):
        if os.path.exists(p):
            os.remove(p)
            say("  [note] a leftover %s was removed" % os.path.basename(p))
    if shutil.which("openssl") is None:
        row("SETUP: the openssl command line is needed to make the test certificates and the expected pins, and it is NOT installed: "
            "NONE of the connect rows can run", False, "install openssl and run again")
        return
    work = tempfile.mkdtemp(prefix="sdnet-conn-")
    servers = []
    probes = []
    try:
        try:
            k1, k2 = os.path.join(work, "k1.pem"), os.path.join(work, "k2.pem")
            c1, c1b, c2 = (os.path.join(work, n) for n in ("c1.pem", "c1b.pem", "c2.pem"))
            make_key(k1)
            make_key(k2)
            make_cert(k1, c1, "sdnet-test-one", 1)
            make_cert(k1, c1b, "sdnet-test-one-renewed", 2)       # a NEW certificate over the SAME key
            make_cert(k2, c2, "sdnet-test-two", 3)                # a certificate over a NEW key
            pin_a, pin_a2, pin_b = expected_pin(c1), expected_pin(c1b), expected_pin(c2)
            fp_a, fp_a2 = cert_fingerprint(c1), cert_fingerprint(c1b)
        except (RuntimeError, OSError, subprocess.SubprocessError) as e:
            row("SETUP: the test certificates and the expected pins were made with the openssl command line", False, repr(e))
            return
        row("SETUP: the independent computation (openssl): a renewed certificate over the same key has the SAME pin and a DIFFERENT certificate hash; "
            "a certificate over a new key has a different pin; each pin is 64 lower case hex digits",
            pin_a == pin_a2 and fp_a != fp_a2 and pin_b != pin_a and all(re.fullmatch(r"[0-9a-f]{64}", x) for x in (pin_a, pin_b)),
            repr((pin_a, pin_a2, pin_b, fp_a == fp_a2)))
        srv_a = TestServer("tls", c1, k1)
        srv_a2 = TestServer("tls", c1b, k1)
        srv_b = TestServer("tls", c2, k2)
        srv_p = TestServer("plain")
        servers += [srv_a, srv_a2, srv_b, srv_p]
        dead = closed_port()
        say("  [note] test servers on 127.0.0.1: tls %d, tls (renewed certificate, same key) %d, tls (new key) %d, not-TLS %d; a closed port %d"
            % (srv_a.port, srv_a2.port, srv_b.port, srv_p.port, dead))
        H = "127.0.0.1"
        succ_ok = lambda out: g.has(out, SUCCESS)
        q_key = lambda out: has_text(out, msg(11442))

        # -- the control: a new name, the hash shown, y
        pa = srv_a.port
        out, b, a, au, dials = conn_run(conn_cmd("conna", pa), ["y"], srv_a)
        order = [first_idx(out, msg(11440, H, pa)), next((i for i, ln in enumerate(out) if ln == pin_a), -1),
                 first_idx(out, msg(11441)[:60]), first_idx(out, msg(11442)), first_idx(out, msg(11424, "conna", H, pa))]
        row("CONTROL, a new name and the answer y: 'Connected to host:port (a TLS handshake only...)', the hash ALONE on a line, the advice to compare it, "
            "the question 'Trust this key (y/<n>)?', then 'Server conna is defined' - in that order",
            all(i >= 0 for i in order) and order[0] < order[1] < order[2] <= order[3] <= order[4], repr((order, out[-6:])))
        row("...the stored pin is EXACTLY the one computed with openssl (SHA-256 of the SubjectPublicKeyInfo, lower case), and the other fields are as typed (read, no accounts)",
            line_is(entry("conna"), ["conna", H, str(pa), "reader", pin_a, "read", ""]), "file now: %r  expected pin %s" % (file_lines(), pin_a))
        row("...it is the hash of the KEY and not of the certificate: the stored pin differs from the certificate's own SHA-256 (%s...)" % fp_a[:12],
            entry("conna") is not None and entry("conna").split("|")[4] != fp_a, repr(entry("conna")))
        row("...the audit trail says how the pin was obtained: 'set.server name=conna host=%s port=%d mode=read replaced=no pin=confirmed'" % (H, pa),
            au is not None and re.search(audit_rx("conna", H, pa, "read", "no", "confirmed"), au) is not None, repr((au or "NO AUDIT FILE")[-300:]))
        row("...and the audit trail does not carry the hash", au is not None and pin_a not in au and pin_a.upper() not in au, "")
        row("...the server saw ONE connection, ONE completed handshake and NO application data at all (a handshake only), and no copy netservers.new is left",
            dials == 1 and srv_a.handshakes == 1 and srv_a.app_bytes == 0 and not os.path.exists(netfile() + ".new"),
            repr((dials, srv_a.handshakes, srv_a.app_bytes)))

        # -- n, an empty answer and the end of input are all a no; the file is the same bytes
        for label, answers in (("n", ["n"]), ("an empty line", [""]), ("N", ["N"]), ("x and then n (the question is put again)", ["x", "n"]),
                               ("no answer at all (end of input)", [])):
            out, b, a, au, dials = conn_run(conn_cmd("connb", pa), answers, srv_a)
            asked = sum(ln.count(msg(11442)) for ln in out)        # the prompt has no newline, so two of them can stand on one line
            row("the key question answered with %s: the hash was shown, 'The key was not trusted', no success wording, the file the SAME BYTES, no audit line, no copy left" % label,
                has_line(out, pin_a) and has_text(out, msg(11443, "connb")) and not succ_ok(out) and b == a and entry("connb") is None
                and au is not None and "name=connb" not in au and not os.path.exists(netfile() + ".new") and asked >= (2 if label.startswith("x") else 1)
                and dials == 1, "asked=%d dials=%s before==after %s  out %r" % (asked, dials, b == a, out[-4:]))

        # -- no.query never skips the key question
        out, b, a, au, dials = conn_run(conn_cmd("connc", pa, "no.query"), ["n"], srv_a)
        row("NO.QUERY does not skip the key question: the question is on the screen, the answer n writes NOTHING (file the same bytes), and the server was dialled",
            q_key(out) and has_text(out, msg(11443, "connc")) and b == a and entry("connc") is None and dials == 1, repr((b == a, dials, out[-3:])))
        out, b, a, au, dials = conn_run(conn_cmd("connc", pa, "no.query"), ["y"], srv_a)
        row("...and with the answer y the same command defines it (the question was still put)",
            q_key(out) and has_text(out, msg(11424, "connc", H, pa)) and line_is(entry("connc"), ["connc", H, str(pa), "reader", pin_a, "read", ""]), repr(out[-3:]))
        out, b, a, au, dials = conn_run(conn_cmd("conna", srv_b.port, "no.query"), ["y"], srv_b)
        row("NO.QUERY skips only the question about replacing: conna is replaced with no 'already defined' question, the KEY question is put, and the pin is now the other key's",
            not has_text(out, "is already defined") and q_key(out) and has_text(out, msg(11425, "conna", H, srv_b.port))
            and line_is(entry("conna"), ["conna", H, str(srv_b.port), "reader", pin_b, "read", ""]), repr((out[-3:], entry("conna"))))
        row("...the audit trail says replaced=yes pin=confirmed",
            au is not None and re.search(audit_rx("conna", H, srv_b.port, "read", "yes", "confirmed"), au) is not None, repr((au or "NO AUDIT FILE")[-300:]))

        # -- replacing an existing name: the replace question comes first and a no to it never dials
        out, b, a, au, dials = conn_run(conn_cmd("conna", pa), ["n"], srv_a)
        row("replacing conna: the answer n to 'Replace it' ends it - 'Server conna was not changed', the file the same bytes and NO connection at all (the server counted %s)" % dials,
            has_text(out, msg(11426, "conna")) and b == a and dials == 0 and not q_key(out), repr((b == a, dials, out[-3:])))
        out, b, a, au, dials = conn_run(conn_cmd("conna", pa), ["y", "n"], srv_a)
        row("...y to 'Replace it' and then n to the key question: the connection was made (1), the hash shown, the file the same bytes (the old pin stays)",
            has_text(out, "is already defined") and has_line(out, pin_a) and has_text(out, msg(11443, "conna")) and b == a and dials == 1, repr((b == a, dials, out[-3:])))
        out, b, a, au, dials = conn_run(conn_cmd("conna", pa), ["y", "y"], srv_a)
        row("...y and y: both questions, in that order, and the definition is replaced with the first server's pin again",
            0 <= first_idx(out, "is already defined") <= first_idx(out, msg(11440, H, pa)) < first_idx(out, msg(11442)) <= first_idx(out, msg(11425, "conna", H, pa))
            and line_is(entry("conna"), ["conna", H, str(pa), "reader", pin_a, "read", ""]) and dials == 1, repr((out[-4:], entry("conna"))))

        # -- a renewed certificate over the same key, and a new key
        out, b, a, au, dials = conn_run(conn_cmd("connr", srv_a2.port), ["y"], srv_a2)
        row("a RENEWED certificate over the SAME key (another serial, another subject) gives the SAME pin as the first server: %s..." % pin_a[:16],
            line_is(entry("connr"), ["connr", H, str(srv_a2.port), "reader", pin_a2, "read", ""]) and pin_a2 == pin_a and has_line(out, pin_a2) and dials == 1,
            repr((entry("connr"), pin_a2)))
        out, b, a, au, dials = conn_run(conn_cmd("connk", srv_b.port), ["y"], srv_b)
        row("a certificate over a NEW key gives a DIFFERENT pin, the one openssl computes for it: %s..." % pin_b[:16],
            line_is(entry("connk"), ["connk", H, str(srv_b.port), "reader", pin_b, "read", ""]) and pin_b != pin_a and has_line(out, pin_b) and dials == 1,
            repr((entry("connk"), pin_b)))

        # -- a server that is not TLS
        out, b, a, au, dials = conn_run(conn_cmd("connp", srv_p.port), [], srv_p)
        row("a plain TCP server that is not TLS is refused with the HANDSHAKE message (11445), no hash, no question, no 'Cannot connect', the file the same bytes",
            g.has(out, msg_re(11445, re.escape(H), str(srv_p.port))) and not g.has(out, msg_re(11444, ".*", ".*", ".*", ".*")) and not q_key(out)
            and not g.has(out, r"^[0-9a-f]{64}$") and not succ_ok(out) and b == a and entry("connp") is None and dials == 1, repr((b == a, dials, out[-3:])))
        row("...and no audit line for it", au is not None and "name=connp" not in au, repr(au))

        # -- a closed port, a name that does not resolve
        out, b, a, au, dials = conn_run(conn_cmd("connd", dead), [])
        er = None
        try:
            with open(os.path.join(os.path.dirname(HERE), "gplsrc", "err.h"), encoding="utf-8", errors="replace") as f:
                m = re.search(r"#define\s+ER_CONNECT\s+(\d+)", f.read())
            er = m.group(1) if m else None
        except OSError:
            pass
        row("a CLOSED port is refused with the CANNOT CONNECT message (11444: status %s, os error %d), not the handshake one, nothing written" % (er or "?", errno.ECONNREFUSED),
            g.has(out, msg_re(11444, re.escape(H), str(dead), er or r"\d+", str(errno.ECONNREFUSED))) and not g.has(out, msg_re(11445, ".*", ".*"))
            and not q_key(out) and not succ_ok(out) and b == a and entry("connd") is None, repr((b == a, out[-3:])))
        out, b, a, au, dials = conn_run(conn_cmd("conne", pa, host="nosuchhost.invalid"), [], srv_a)
        row("a host name that does not resolve is a clear failure (11444 with its status and os error), no question, nothing written, and the real server was NOT dialled (%s)" % dials,
            g.has(out, msg_re(11444, "nosuchhost\\.invalid", str(pa), r"\d+", r"\d+")) and not q_key(out) and not succ_ok(out) and b == a
            and entry("conne") is None and dials == 0, repr((b == a, dials, out[-3:])))

        # -- a definition that fails field validation never dials
        say("  (a definition that would be refused is never dialled: no 'Connected', no 'Cannot connect', no handshake message, no question, the server counts 0)")
        bad = [("a bad name", conn_cmd("1bad", pa), [msg(11414, "1bad")]),
               ("a bad host", conn_cmd("badh", pa, host="-bad.org"), [msg(11415, "-bad.org")]),
               ("a bad port", conn_cmd("badp", 0), [msg(11416, "0")]),
               ("a bad remote account", conn_cmd("bada", pa, account="bad@acct"), [msg(11417, "bad@acct")]),
               ("a bad mode", conn_cmd("badm", pa, "append"), [msg(11419, "append")]),
               ("an unregistered account in the list", conn_cmd("badl", pa, "accounts zznnosuch"), [msg(11421, "zznnosuch")]),
               ("a bad list", conn_cmd("badl", pa, "accounts zznon,,zznoff"), [msg(11420)]),
               ("name, port and account all wrong", conn_cmd("1x", 0, account="b@d"), [msg(11414, "1x"), msg(11416, "0"), msg(11417, "b@d")])]
        for label, cmd, expect in bad:
            out, b, a, au, dials = conn_run(cmd, [], srv_a)
            miss = [t for t in expect if not has_line(out, t)]
            dialled = g.has(out, r"Connected to |Cannot connect to |The TLS handshake with |completed the handshake") or q_key(out)
            row("%s with connect -> refused with its own message, nothing dialled (the server counted %s), the file the same bytes" % (label, dials),
                not miss and not dialled and dials == 0 and b == a and not succ_ok(out), "missing %r; dialled=%s dials=%s out %r" % (miss, dialled, dials, out[-4:]))

        # -- the typed pin makes no connection
        out, b, a, au, dials = conn_run("set.server connt %s %d reader %s read" % (H, pa, pin_b), [], srv_a)
        row("a TYPED pin makes NO connection (the server counted %s) and no key question, even for a port with a TLS server on it; the typed pin is stored as typed" % dials,
            dials == 0 and not q_key(out) and not g.has(out, r"Connected to ") and has_text(out, msg(11424, "connt", H, pa))
            and line_is(entry("connt"), ["connt", H, str(pa), "reader", pin_b, "read", ""]), repr((dials, out[-3:])))
        row("...and its audit line says pin=typed (and not pin=confirmed)",
            au is not None and re.search(audit_rx("connt", H, pa, "read", "no", "typed"), au) is not None and "pin=confirmed" not in au, repr((au or "NO AUDIT FILE")[-300:]))
        out, b, a, au, dials = conn_run("set.server connt2 %s %d reader %s read" % (H, dead, pin_a), [])
        row("...a typed pin for a port with nothing listening is accepted too (nothing is dialled)", has_text(out, msg(11424, "connt2", H, dead)) and entry("connt2") is not None, repr(out[-3:]))

        # -- the word is CONNECT in any case, and the other words still work with it
        out, b, a, au, dials = conn_run(conn_cmd("connu", pa, "write accounts zznon,zznoff", word="CONNECT"), ["y"], srv_a)
        row("the word is accepted in upper case, with write and an accounts list after it: defined with pin %s... and mode write" % pin_a[:12],
            line_is(entry("connu"), ["connu", H, str(pa), "reader", pin_a, "write", "zznon,zznoff"]) and dials == 1, repr((entry("connu"), out[-3:])))
        out, b, a, au, dials = conn_run(conn_cmd("connv", pa, "no.query", word="Connect"), ["y"], srv_a)
        row("...and as Connect, before no.query", line_is(entry("connv"), ["connv", H, str(pa), "reader", pin_a, "read", ""]) and dials == 1, repr((entry("connv"), out[-3:])))

        # -- the limit of ten comes before the dial
        have = [x.split("|")[0] for x in (file_lines() or [])]
        fill = ["tt%02d" % i for i in range(1, 30) if ("tt%02d" % i) not in have][:max(0, 10 - len(have))]
        adm1(*["set.server %s %s %d reader %s read" % (n, H, dead, pin_a) for n in fill])
        row("setup: ten definitions are held (%d filled)" % len(fill), len(file_lines() or []) == 10, repr(file_lines()))
        out, b, a, au, dials = conn_run(conn_cmd("eleven", pa), [], srv_a)
        row("an 11th NEW name with connect is refused with 11422 BEFORE any connection (the server counted %s), the file the same bytes" % dials,
            has_line(out, msg(11422, 10)) and dials == 0 and b == a and not q_key(out), repr((dials, b == a, out[-3:])))
        out, b, a, au, dials = conn_run(conn_cmd("conna", pa, "no.query"), ["y"], srv_a)
        row("CONTROL: with ten held, REPLACING one with connect still works (it is no new name), and stays ten",
            has_text(out, msg(11425, "conna", H, pa)) and len(file_lines() or []) == 10 and dials == 1, repr((len(file_lines() or []), dials, out[-3:])))

        # -- a program reads the hash of a socket: the null string without TLS
        say("  (SOCKET.INFO(.., SKT$INFO.TLS.SPKI): a program that opens the test server WITHOUT SKT$TLS gets the null string, and WITH it the 64 digits)")
        prog = "zznetsk" + RUN
        g.put(os.path.join(g.SYS, "bp", prog), sock_probe(srv_a.port))
        probes.append(os.path.join(g.SYS, "bp", prog))
        out = adm1("BASIC bp " + prog, "RUN bp " + prog)
        row("the administrator's probe compiled with no errors", g.has(out, r"^Compiled 1 program\(s\) with no errors"), repr(out[-4:]))
        row("...a socket opened WITHOUT SKT$TLS: SOCKET.INFO answers the NULL string (length 0)", has_line(out, "SK plain len=0 []"), repr(out[-4:]))
        row("...CONTROL, the same probe with SKT$TLS: 64 digits, the pin openssl computed for that server (so the null above is not a broken SOCKET.INFO)",
            has_line(out, "SK tls len=64 [%s]" % pin_a) and has_line(out, "SK end"), repr(out[-4:]))
        g.put(os.path.join(acct_path("zznoff"), "bp", prog), sock_probe(srv_a.port))
        probes.append(os.path.join(acct_path("zznoff"), "bp", prog))
        out = g.plain("zznoff", ["BASIC bp " + prog, "RUN bp " + prog])
        row("an ORDINARY account (zznoff): the same probe - null string for the plain socket, the 64 digits for the TLS one (the hash is a public key's, no gate hides it)",
            g.has(out, r"^Compiled 1 program\(s\) with no errors") and has_line(out, "SK plain len=0 []") and has_line(out, "SK tls len=64 [%s]" % pin_a), repr(out[-5:]))
    finally:
        for s in servers:
            s.shutdown()
        for p in probes:
            for q in (p, p.replace(os.sep + "bp" + os.sep, os.sep + "bp.out" + os.sep)):
                if os.path.exists(q):
                    os.remove(q)
        shutil.rmtree(work, ignore_errors=True)
        if os.path.exists(netfile()):
            os.remove(netfile())            # the next section makes its own


# ---- slice 2b: the person's login on a server (sections netcred and netlogin) ---------------------------------------------------------------

NL_PW = "Zq7-remote-Passw0rd-x"       # the remote passwords the rows type: strings that appear nowhere else, so their presence anywhere is a leak
NL_PW2 = "Another-Passw0rd-y9"
NL_BADPW = "Wrong-Passw0rd-q3"
NL_REMOTE = "alice"
SUCC = r"is stored\.  The password is not stored$"                 # the success wording of 11477 and of nothing else
SALT0 = "AAECAwQFBgcICQoLDA0ODw=="                                  # base64 of 16 bytes, for the rows that write a login by hand
NL = {}

# The probes.  zznc drives $netcred: one line of input per call, "ACTION|server|pin|attr1|..|attr7", ended by END.  zznc2 and zznc3 are the
# same READ as an INTERNAL program (the control) and as an ordinary account's program.
ZZNC = "\n".join([
    "$internal", "program zznc", "$catalog $zznc", "$include err.h",
    "   done = @false", "   rec = ''", "   err = ''",
    "   loop",
    "      input ln",
    "      done = (ln = 'END') or (ln = '' and status() = ER$EOF)",
    "   until done do",
    "      act = field(ln, '|', 1)", "      srv = field(ln, '|', 2)", "      pn = field(ln, '|', 3)", "      rec = ''",
    "      for i = 1 to 7", "         rec<i> = field(ln, '|', 3 + i)", "      next i",
    "      err = ''",
    "      call $netcred(act, srv, rec, pn, err)",
    "      crt 'NC ':act:' ':srv:' err=':convert(@vm, '~', err):' rec=':convert(@fm, '|', rec)",
    "   repeat",
    "   crt 'NC end'", "end", ""])
READ_BODY = ["   rec = ''", "   err = ''", "   call $netcred('READ', 'nlgate', rec, '%s', err)" % PIN_A]
ZZNC2 = "\n".join(["$internal", "program zznc2", "$catalog $zznc2"] + READ_BODY + ["   crt 'NC2 remote=':rec<1>:' err=':convert(@vm, '~', err)", "end", ""])
ZZNC3 = "\n".join(READ_BODY + ["   crt 'NC3 remote=':rec<1>:' err=':convert(@vm, '~', err)", "end", ""])


def standin_text(work, root):
    """What stands in for `sudo -n /usr/local/sbin/sd-elevate netcred-dir`.  It logs every call (so a row can show it was or was not run), makes
    the root 755 and the person's directory 700 the way the helper does, and prints the helper's success line.  Flag files in WORK change its
    behaviour for one row: elev-fail (refuse), elev-mode (the mode to give the person's directory), elev-wrongpath (name another directory)."""
    return "\n".join([
        "#!/bin/sh",
        "# a stand-in for: sudo -n /usr/local/sbin/sd-elevate netcred-dir   (sandbox-net.py: the sandbox has no sudoers line and no /var/lib/sd-net)",
        'W="%s"' % work, 'R="%s"' % root,
        'echo "standin: $*" >> "$W/elev.log"',
        'if [ "$1" != "netcred-dir" ] || [ $# -ne 1 ]; then echo "standin: usage"; exit 2; fi',
        'if [ -e "$W/elev-fail" ]; then echo "standin: refused for test"; exit 1; fi',
        'if [ -e "$W/elev-wrongpath" ]; then echo "netcred-dir: $R/someone-else"; exit 0; fi',     # before anything is made: it names the wrong place and changes nothing
        'u=$(id -un)',
        'mkdir -p "$R" || exit 1', 'chmod 755 "$R"',
        'mkdir -p "$R/$u" || exit 1',
        'mode=700', 'if [ -e "$W/elev-mode" ]; then mode=$(cat "$W/elev-mode"); fi', 'chmod "$mode" "$R/$u"',
        'echo "netcred-dir: $R/$u"', ""])


def nl_patch(path, pattern, repl, what):
    """Edit the SANDBOX'S copy of a program: PATTERN (a regular expression) must match exactly once."""
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    new, n = re.subn(pattern, lambda m: m.group(1) + repl + (m.group(2) if m.re.groups >= 2 else ""), text, flags=re.M)
    if n != 1:
        bail("the sandbox's %s does not hold exactly one %s to patch (%d matches)" % (os.path.basename(path), what, n))
    with open(path, "w", encoding="utf-8") as f:
        f.write(new)


def nl_prepare():
    """What both sections need, done once: a scratch credential root, the stand-in for the helper, and the sandbox's copies of $netcred and
    set.netlogin pointed at them and recompiled, with the probes.  Returns True when ready (a failed step is a failed row and the sections skip)."""
    if "ready" in NL:
        return NL["ready"]
    NL["ready"] = False
    user = pwd.getpwuid(os.getuid()).pw_name
    if user in ("root", "sdsys") or not re.fullmatch(r"[A-Za-z0-9._-]{1,32}", user) or user[0] in ".-":
        row("SETUP: the user running this suite (%r) is one $netcred can keep a login for (not root, not sdsys, letters digits ._-)" % user, False,
            "run it as an ordinary user")
        return False
    work = tempfile.mkdtemp(prefix="sdnet-cred-")
    root = os.path.join(work, "sd-net")
    script = os.path.join(work, "standin.sh")
    NL.update(work=work, made=work, root=root, user=user, dir=os.path.join(root, user), log=os.path.join(work, "elev.log"), script=script)
    with open(script, "w", encoding="ascii") as f:
        f.write(standin_text(work, root))
    nl_patch(os.path.join(g.SYS, "gpl.bp", "netcred"), r"(\$define NETCRED\.ROOT\s+')[^']*(')", root, "NETCRED.ROOT define")
    nl_patch(os.path.join(g.SYS, "gpl.bp", "setnetlogin"), r"(^   elev = )(?:ACCOS\$ELEVATE|'/bin/sh [^']*')$", "'/bin/sh %s'" % script, "elev line")
    g.put(os.path.join(g.SYS, "gpl.bp", "zznc"), ZZNC)
    g.put(os.path.join(g.SYS, "gpl.bp", "zznc2"), ZZNC2)
    out = g.adm(["BASIC gpl.bp netcred setnetlogin zznc zznc2"], internal=True)
    ok = g.has(out, r"^Compiled 4 program\(s\) with no errors")
    row("SETUP: the sandbox's $netcred (root -> %s) and set.netlogin (helper -> a stand-in script) and the probes zznc, zznc2 compile with no errors" % root,
        ok, repr(out[-8:]))
    NL["ready"] = ok
    return ok


def nl_cleanup():
    """Remove the scratch area: only the one directory this run made with mkdtemp (kept in NL as it was made), never a path worked out afterwards."""
    work = NL.get("made")
    if work and os.path.isdir(work) and os.path.basename(work).startswith("sdnet-cred-"):
        shutil.rmtree(work, ignore_errors=True)


def cred_path(server):
    return os.path.join(NL["dir"], server)


def reset_root():
    """The credential root as the stand-in finds it before it has ever run: not there."""
    if os.path.isdir(NL["root"]) and NL["root"].startswith(NL["work"] + os.sep):
        shutil.rmtree(NL["root"], ignore_errors=True)


def cred_state():
    """The whole credential directory as the disk holds it: None when it is not there, else {name: (mode, inode, mtime_ns, bytes or None)}."""
    d = NL["dir"]
    try:
        names = sorted(os.listdir(d))
    except OSError:
        return None
    out = {}
    for n in names:
        p = os.path.join(d, n)
        try:
            lst = os.lstat(p)
            data = None
            if S_ISREG(lst.st_mode):
                with open(p, "rb") as f:
                    data = f.read()
            out[n] = (lst.st_mode, lst.st_ino, lst.st_mtime_ns, data)
        except OSError as e:
            out[n] = ("error", repr(e))
    return out


def read_cred(server):
    try:
        with open(cred_path(server), "rb") as f:
            return f.read()
    except OSError:
        return None


def cred_line(remote, salt_b64, iters, ck_b64, sk_b64, pin, date=None):
    return "|".join(["v1", remote, salt_b64, str(iters), ck_b64, sk_b64, pin, date or datetime.date.today().isoformat()])


def cred_matches(server, remote, salt_b64, iters, ck_b64, sk_b64, pin):
    """Is the file ONE line of eight bars-separated fields, the first seven exactly these (computed by the caller, not by SD) and the last a date?"""
    raw = read_cred(server)
    if raw is None:
        return False
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError:
        return False
    if text.endswith("\n"):
        text = text[:-1]
    parts = text.split("|")
    return "\n" not in text and len(parts) == 8 and parts[:7] == ["v1", remote, salt_b64, str(iters), ck_b64, sk_b64, pin] and parts[7] in dates()


def plant(server, line=None, mode=0o600, raw=None):
    """A login put on the disk by hand, as the person's own user: for the rows that need a file to be there, or to be wrong."""
    os.makedirs(NL["root"], exist_ok=True)
    os.chmod(NL["root"], 0o755)
    if not os.path.isdir(NL["dir"]):
        os.mkdir(NL["dir"])
    os.chmod(NL["dir"], 0o700)
    p = cred_path(server)
    with open(p, "wb") as f:
        f.write(raw if raw is not None else (line + "\n").encode("ascii"))
    os.chmod(p, mode)


def valid_line(remote=NL_REMOTE, pin=PIN_A, iters=4096, pw=NL_PW, salt=SALT0):
    k = netfake.derive(pw, salt, iters)
    return cred_line(remote, salt, iters, k["client_key_b64"], k["server_key_b64"], pin)


def elev_calls():
    try:
        with open(NL["log"], "r", encoding="ascii", errors="replace") as f:
            return len(f.read().splitlines())
    except OSError:
        return 0


def flag(name, on, text="1"):
    p = os.path.join(NL["work"], name)
    if on:
        with open(p, "w") as f:
            f.write(text)
    elif os.path.exists(p):
        os.remove(p)


def has_msg(out, text):
    """The message is on the screen: a line of its own, or - for one longer than the 200 columns the sessions are given - its first 120
    characters at the start of a line (the arguments are all in them)."""
    if has_line(out, text):
        return True
    return len(text) > 190 and any(ln.startswith(text[:120]) for ln in out)


def nl_run(acct, cmd, answers=(), srv=None, admin=False):
    """One session: CMD, then the ANSWERS as the lines the prompts read.  Returns the output, the credential directory before and after, what
    the audit trail gained, how often the stand-in for the helper was run, and what the fake server saw meanwhile."""
    a0 = audit_off()
    st0 = cred_state()
    m = srv.mark() if srv is not None else None
    e0 = elev_calls()
    cmds = [cmd] + list(answers)
    out = g.adm(cmds) if admin else g.plain(acct, cmds)
    if srv is not None:
        srv.settle(quiet=0.3)
    return {"out": out, "before": st0, "after": cred_state(), "audit": audit_new(a0), "elev": elev_calls() - e0, "d": srv.delta(m) if srv is not None else None}


def scan_for(needles, roots, skip_over=256 * 1024 * 1024):
    """Every regular file under ROOTS is read, a megabyte at a time (with the overlap a needle could straddle), for each of the byte strings
    in NEEDLES.  Returns (files read, {needle: [paths]})."""
    found = {n: [] for n in needles}
    nfiles = 0
    keep = max(len(n) for n in needles) - 1
    skip_tree = os.path.join(g.BOX, "tree")      # the sandbox's own COPY of the source tree, this suite's text included: it holds the passwords the rows type
    for root in roots:
        for dp, _dn, fns in os.walk(root, followlinks=False):
            if dp == skip_tree or dp.startswith(skip_tree + os.sep):
                continue
            for fn in fns:
                p = os.path.join(dp, fn)
                try:
                    if os.path.islink(p) or not os.path.isfile(p) or os.path.getsize(p) > skip_over:
                        continue
                    nfiles += 1
                    tail = b""
                    with open(p, "rb") as f:
                        while True:
                            chunk = f.read(1 << 20)
                            if not chunk:
                                break
                            buf = tail + chunk
                            for n in needles:
                                if n in buf and p not in found[n]:
                                    found[n].append(p)
                            tail = buf[-keep:] if keep else b""
                except OSError:
                    continue
    return nfiles, found


# ---- $netcred --------------------------------------------------------------------------------------------------------------------------

def nc_session(lines):
    """Run the probe zznc (an internal program, as the administrator of the sandbox) with these input lines.  Returns [(action, server, [err
    values], [record attributes])] and whether it reached its end line."""
    out = g.adm(["RUN gpl.bp zznc"] + list(lines) + ["END"], internal=True)
    res = []
    for ln in out:
        m = re.match(r"^NC (\S+) (\S*) err=(.*?) rec=(.*)$", ln)
        if m:
            res.append((m.group(1), m.group(2), m.group(3).split("~") if m.group(3) != "" else [], m.group(4).split("|") if m.group(4) != "" else []))
    return res, has_line(out, "NC end"), out


def L(act, server, pin="", *attrs):
    return "|".join([act, server, pin] + list(attrs))


def netcred_section():
    say("\n--- $netcred: READ / WRITE / DELETE / EXISTS on a scratch credential root, driven by an internal probe; the DISK is the evidence ---")
    if not nl_prepare():
        return
    U, D = NL["user"], NL["dir"]
    keys = netfake.derive(NL_PW, SALT0, 4096)
    CK, SK = keys["client_key_b64"], keys["server_key_b64"]
    pin_b = PIN_B
    reset_root()

    def expect(res, i, err=None, rec=None):
        """Row i of the probe's answers: err and rec are the lists it must hold (None = not looked at)."""
        if i >= len(res):
            return False
        # an empty record is the probe printing seven empty attributes as well as nothing at all
        return (err is None or res[i][2] == err) and (rec is None or res[i][3] == rec or (rec == [] and all(x == "" for x in res[i][3])))

    # -- no directory yet
    res, ended, out = nc_session([L("READ", "nlx", PIN_A), L("EXISTS", "nlx"), L("DELETE", "nlx"), L("WRITE", "nlx", PIN_A, NL_REMOTE, SALT0, "4096", CK, SK)])
    row("the probe ran to its end line with one answer for each of the four calls", ended and len(res) == 4, repr(out[-5:]))
    row("no directory: READ says there is no login (11453) and EXISTS answers 0 with NO error", expect(res, 0, ["11453", "nlx"], []) and expect(res, 1, [], ["0"]), repr(res[:2]))
    row("...DELETE says there is none (11453), and WRITE refuses (11454, with the directory) - it does NOT make the directory, which is root's to make",
        expect(res, 2, ["11453", "nlx"]) and expect(res, 3, ["11454", "nlx", D]) and not os.path.exists(D), repr((res[2:], os.path.exists(D))))

    # -- the directory is there, private, empty: WRITE, then READ it back
    os.makedirs(NL["root"], exist_ok=True)
    os.chmod(NL["root"], 0o755)
    os.mkdir(D)
    os.chmod(D, 0o700)
    long_name = "a" * 17
    lines = [L("WRITE", "nlx", PIN_A, NL_REMOTE, SALT0, "4096", CK, SK), L("READ", "nlx", PIN_A), L("EXISTS", "nlx"), L("READ", "nlx", PIN_B),
             L("READ", "nlx", ""), L("READ", "nlx", PIN_A[:63]), L("READ", "nlx", PIN_A.upper()),
             L("READ", "Nlx"), L("READ", "1nlx"), L("READ", "n_x"), L("READ", long_name), L("READ", ""), L("FOO", "nlx")]
    res, ended, out = nc_session(lines)
    row("WRITE then READ: the probe answered all %d calls" % len(lines), ended and len(res) == len(lines), repr(out[-4:]))
    row("WRITE of a good record says nothing (err null)", expect(res, 0, []), repr(res[:1]))
    row("...the file holds EXACTLY v1|remote user|salt|iterations|ClientKey|ServerKey|pin|date, with the values computed here with hashlib and the pin the caller gave",
        cred_matches("nlx", NL_REMOTE, SALT0, 4096, CK, SK, PIN_A), repr(read_cred("nlx")))
    try:
        st = os.lstat(cred_path("nlx"))
        row("...mode 600, a plain file, owned by the user running the suite, and the directory is still 700 with nothing else in it (no nlx.new)",
            S_IMODE(st.st_mode) == 0o600 and S_ISREG(st.st_mode) and st.st_uid == os.getuid() and S_IMODE(os.lstat(D).st_mode) == 0o700 and os.listdir(D) == ["nlx"],
            "%s %s" % (oct(st.st_mode), os.listdir(D)))
    except OSError as e:
        row("...mode 600 (the file could not be examined)", False, repr(e))
    row("READ with the pin of the definition gives the seven values back in order, the date today",
        len(res) > 1 and res[1][2] == [] and len(res[1][3]) == 7 and res[1][3][:6] == [NL_REMOTE, SALT0, "4096", CK, SK, PIN_A] and res[1][3][6] in dates(), repr(res[1:2]))
    row("EXISTS answers 1 for a login that is there and private", expect(res, 2, [], ["1"]), repr(res[2:3]))
    row("READ with a pin that differs is refused (11455) and the record comes back null", expect(res, 3, ["11455", "nlx"], []), repr(res[3:4]))
    row("READ with no pin, a pin of 63 digits or a pin in upper case is refused BEFORE the disk is looked at (11459), the record null",
        expect(res, 4, ["11459"], []) and expect(res, 5, ["11459"], []) and expect(res, 6, ["11459"], []), repr(res[4:7]))
    row("a server name with a capital, a digit first, an underscore, 17 characters or none is refused (11452)",
        expect(res, 7, ["11452", "Nlx"]) and expect(res, 8, ["11452", "1nlx"]) and expect(res, 9, ["11452", "n_x"]) and expect(res, 10, ["11452", long_name])
        and expect(res, 11, ["11452", ""]), repr(res[7:12]))
    row("an action that is not READ, WRITE, DELETE or EXISTS is 2018", expect(res, 12, ["2018", "FOO"]), repr(res[12:13]))
    good = cred_state()

    # -- WRITE refuses every shape of value, one at a time; the login is untouched and no copy is left
    base = [NL_REMOTE, SALT0, "4096", CK, SK, "", ""]

    def w(i, value, pin=PIN_A):
        a = list(base)
        a[i] = value
        return L("WRITE", "nlx", pin, *a)
    bad = [("remote user with a space", w(0, "bad user"), "remote user"), ("an empty remote user", w(0, ""), "remote user"),
           ("a remote user of 33 characters", w(0, "u" * 33), "remote user"),
           ("iterations 4095 (below the floor)", w(2, "4095"), "iterations"), ("iterations 10000001 (above the ceiling)", w(2, "10000001"), "iterations"),
           ("iterations 'abc'", w(2, "abc"), "iterations"), ("iterations empty", w(2, ""), "iterations"), ("iterations 100", w(2, "100"), "iterations"),
           ("iterations -5", w(2, "-5"), "iterations"), ("iterations 4096.5", w(2, "4096.5"), "iterations"), ("iterations of 9 digits", w(2, "123456789"), "iterations"),
           ("a salt of 3 characters", w(1, "abc"), "salt"), ("an empty salt", w(1, ""), "salt"), ("a salt with an exclamation mark", w(1, "ab!d"), "salt"),
           ("a salt of 129 characters", w(1, "A" * 129), "salt"),
           ("an empty ClientKey", w(3, ""), "ClientKey"), ("a ClientKey of 129 characters", w(3, "A" * 129), "ClientKey"),
           ("an empty ServerKey", w(4, ""), "ServerKey"), ("a ServerKey with an exclamation mark", w(4, "!!!!"), "ServerKey"),
           ("a date 2026-1-2", w(6, "2026-1-2"), "created"), ("a date 20260102", w(6, "20260102"), "created"), ("a date abcd-ef-gh", w(6, "abcd-ef-gh"), "created")]
    res, ended, out = nc_session([b[1] for b in bad] + [w(0, NL_REMOTE, pin=""), w(0, NL_REMOTE, pin=PIN_A[:63]), w(0, NL_REMOTE, pin=PIN_A.upper())])
    row("the bad writes: the probe answered every call", ended and len(res) == len(bad) + 3, repr(out[-3:]))
    for i, (label, _line, field) in enumerate(bad):
        row("WRITE of %s is refused: 11456 naming '%s'" % (label, field), expect(res, i, ["11456", "nlx", field]), repr(res[i:i + 1]))
    row("WRITE with no pin, 63 digits or upper case digits is 11459", all(expect(res, len(bad) + k, ["11459"]) for k in range(3)), repr(res[len(bad):]))
    row("...and after ALL of them the credential directory is the SAME BYTES, inode and time as before (nothing written, no nlx.new)", cred_state() == good, "")

    # -- a leftover copy is replaced; the pin ARGUMENT is stored, not attribute 6; a date given is kept; the limits themselves are allowed
    junk = cred_path("nlx.new")
    with open(junk, "wb") as f:
        f.write(b"junk left by a crash\n")
    os.chmod(junk, 0o644)
    res, ended, out = nc_session([L("WRITE", "nlx", PIN_A, NL_REMOTE, SALT0, "4096", CK, SK, pin_b, "2026-01-02")])
    row("a leftover nlx.new (mode 644) does not stop a WRITE: it succeeds and the copy is gone", expect(res, 0, []) and not os.path.exists(junk) and os.listdir(D) == ["nlx"], repr((res, os.listdir(D))))
    row("...the pin stored is the ARGUMENT (attribute 6 of the record, a different pin, was ignored) and the date given is kept",
        cred_matches("nlx", NL_REMOTE, SALT0, 4096, CK, SK, PIN_A) is False and read_cred("nlx") == ("|".join(["v1", NL_REMOTE, SALT0, "4096", CK, SK, PIN_A, "2026-01-02"]) + "\n").encode(),
        repr(read_cred("nlx")))
    big = "A" * 128
    res, ended, out = nc_session([L("WRITE", "nlx", PIN_A, "u" * 32, SALT0, "10000000", big, big), L("READ", "nlx", PIN_A), L("WRITE", "nlx", PIN_A, NL_REMOTE, SALT0, "4096", CK, SK)])
    row("CONTROL, the values just inside every limit are accepted and read back: a remote user of 32, 10000000 iterations, keys of 128 characters",
        expect(res, 0, []) and expect(res, 1, []) and len(res[1][3]) == 7 and res[1][3][:6] == ["u" * 32, SALT0, "10000000", big, big, PIN_A] and expect(res, 2, []), repr(res[:3]))

    # -- the file or directory is not private: nothing in it is used
    os.chmod(cred_path("nlx"), 0o600)
    state = cred_state()
    for mode in (0o640, 0o604, 0o620, 0o602, 0o666):
        os.chmod(cred_path("nlx"), mode)
        res, ended, out = nc_session([L("READ", "nlx", PIN_A), L("EXISTS", "nlx"), L("DELETE", "nlx")])
        want = ["11454", "nlx", cred_path("nlx")]
        row("the file has mode %s: READ, EXISTS and DELETE all refuse it (11454, with its path), the record is null, and the file is still there"
            % oct(mode), expect(res, 0, want, []) and expect(res, 1, want, ["0"]) and expect(res, 2, want) and os.path.exists(cred_path("nlx")), repr(res))
    os.chmod(cred_path("nlx"), 0o600)
    res, ended, out = nc_session([L("READ", "nlx", PIN_A)])
    row("CONTROL: mode 600 again and the same READ works (so the refusals above are the mode)", expect(res, 0, []) and len(res[0][3]) == 7, repr(res))
    for mode in (0o750, 0o770, 0o701, 0o755):
        os.chmod(D, mode)
        before = cred_state()
        res, ended, out = nc_session([L("READ", "nlx", PIN_A), L("EXISTS", "nlx"), L("DELETE", "nlx"), L("WRITE", "nlx", PIN_A, NL_REMOTE, SALT0, "4096", CK, SK)])
        want = ["11454", "nlx", D]
        os.chmod(D, 0o700)
        row("the DIRECTORY has mode %s: READ, EXISTS, DELETE and WRITE all refuse (11454, with the directory) and the files are the same bytes"
            % oct(mode), all(expect(res, k, want) for k in range(4)) and cred_state() == before, repr(res))
    state = cred_state()

    # -- a link, a directory, a damaged file in the place of the login
    decoy = os.path.join(NL["work"], "decoy")
    with open(decoy, "wb") as f:
        f.write(b"decoy that must survive\n")
    os.chmod(decoy, 0o600)
    os.remove(cred_path("nlx"))
    os.symlink(decoy, cred_path("nlx"))
    res, ended, out = nc_session([L("READ", "nlx", PIN_A), L("EXISTS", "nlx"), L("DELETE", "nlx")])
    want = ["11454", "nlx", cred_path("nlx")]
    row("a SYMBOLIC LINK in the login's place (to a private file of the same user) is refused by READ, EXISTS and DELETE (11454): the test is lstat, not stat",
        expect(res, 0, want, []) and expect(res, 1, want, ["0"]) and expect(res, 2, want), repr(res))
    row("...and DELETE did not follow or remove it: the link is still there and so is its target", os.path.islink(cred_path("nlx")) and open(decoy, "rb").read() == b"decoy that must survive\n", "")
    res, ended, out = nc_session([L("WRITE", "nlx", PIN_A, NL_REMOTE, SALT0, "4096", CK, SK)])
    row("WRITE where a link stands never writes THROUGH it: the target is the same bytes (what the path then holds is %s)"
        % ("a regular file" if os.path.isfile(cred_path("nlx")) and not os.path.islink(cred_path("nlx")) else "still a link"),
        open(decoy, "rb").read() == b"decoy that must survive\n", repr((res, os.path.islink(cred_path("nlx")))))
    if os.path.lexists(cred_path("nlx")):
        os.remove(cred_path("nlx"))
    os.mkdir(cred_path("nlx"), 0o700)
    with open(os.path.join(cred_path("nlx"), "keep"), "wb") as f:
        f.write(b"inside\n")
    res, ended, out = nc_session([L("READ", "nlx", PIN_A), L("EXISTS", "nlx"), L("DELETE", "nlx")])
    row("a DIRECTORY named like the login is refused (11454) by READ, EXISTS and DELETE, and DELETE did not remove it or what is in it (no recursive delete)",
        expect(res, 0, want, []) and expect(res, 1, want, ["0"]) and expect(res, 2, want) and os.path.isfile(os.path.join(cred_path("nlx"), "keep")), repr(res))
    os.remove(os.path.join(cred_path("nlx"), "keep"))
    os.rmdir(cred_path("nlx"))

    good_fields = ["v1", NL_REMOTE, SALT0, "4096", CK, SK, PIN_A, "2026-01-02"]

    def variant(i, value):
        f = list(good_fields)
        f[i] = value
        return "|".join(f)
    damaged = [("nldlay", "a first field that is not v1", variant(0, "v2").encode(), "layout"),
               ("nldfew", "seven fields", "|".join(good_fields[:7]).encode(), "layout"), ("nldmany", "nine fields", ("|".join(good_fields) + "|x").encode(), "layout"),
               ("nldempty", "an empty file", b"", "layout"),
               ("nldmark", "a mark byte (0xFB) in the remote user", variant(1, "ali\xfbce").encode("latin-1"), "marks"),
               ("nlditer", "iterations 'abc'", variant(3, "abc").encode(), "iterations"), ("nlditer2", "iterations 100", variant(3, "100").encode(), "iterations"),
               ("nldsalt", "a salt of two characters", variant(2, "ab").encode(), "salt"), ("nldpin", "a pin that is not hexadecimal", variant(6, "XYZ" * 21 + "X").encode(), "pin"),
               ("nlddate", "a date 2026/01/02", variant(7, "2026/01/02").encode(), "created"), ("nlduser", "a remote user with a space", variant(1, "bad user").encode(), "remote user")]
    for name, _label, raw, _field in damaged:
        plant(name, raw=raw + b"\n")
    plant("nldgood", "|".join(good_fields))
    state = cred_state()
    res, ended, out = nc_session([L("READ", name, PIN_A) for name, _l, _r, _f in damaged] + [L("READ", "nldgood", PIN_A), L("READ", "nldgood", PIN_B)])
    for i, (name, label, _raw, field) in enumerate(damaged):
        row("a stored login with %s is DAMAGED: READ says 11456 naming '%s', the record is null" % (label, field), expect(res, i, ["11456", name, field], []), repr(res[i:i + 1]))
    n = len(damaged)
    row("CONTROL: a well formed file written by hand is read (the damaged ones are refused for their damage), and with the other pin it is 11455",
        expect(res, n, [], good_fields[1:]) and expect(res, n + 1, ["11455", "nldgood"], []), repr(res[n:]))
    row("...and the READs wrote nothing: the directory is the same bytes as before", cred_state() == state, "")
    for name in [d[0] for d in damaged] + ["nldgood"]:
        os.remove(cred_path(name))

    # -- DELETE, EXISTS after it
    plant("nlx", valid_line())
    res, ended, out = nc_session([L("EXISTS", "nlx"), L("DELETE", "nlx"), L("EXISTS", "nlx"), L("DELETE", "nlx")])
    row("DELETE of a private login removes it: EXISTS 1, DELETE (no error), EXISTS 0 with no error, DELETE again 11453, and the file is gone from the disk",
        expect(res, 0, [], ["1"]) and expect(res, 1, []) and expect(res, 2, [], ["0"]) and expect(res, 3, ["11453", "nlx"]) and not os.path.lexists(cred_path("nlx")), repr(res))
    if os.path.exists(decoy):
        os.remove(decoy)


# ---- set.netlogin and delete.netlogin ------------------------------------------------------------------------------------------------

def netlogin_section():
    say("\n--- set.netlogin / delete.netlogin as ordinary accounts, against a FAKE SD API SERVER (gplbld/netfake.py) that records every packet ---")
    if shutil.which("openssl") is None:
        row("SETUP: the openssl command line is needed to make the fake server's certificates and the expected pins, and it is NOT installed: "
            "NONE of the netlogin rows can run", False, "install openssl and run again")
        return
    if not nl_prepare():
        return
    U, work = NL["user"], NL["work"]
    reset_root()
    for p in (netfile(), netfile() + ".new", netfile() + ".lock"):
        if os.path.exists(p):
            os.remove(p)
    for f in ("elev-fail", "elev-mode", "elev-wrongpath", "elev.log"):
        flag(f, False)
    srvs = []
    try:
        k1, k2, c1, c2 = (os.path.join(work, n) for n in ("k1.pem", "k2.pem", "c1.pem", "c2.pem"))
        try:
            make_key(k1)
            make_key(k2)
            make_cert(k1, c1, "sdnet-login-one", 11)
            make_cert(k2, c2, "sdnet-login-two", 12)
            pin_a, pin_b = expected_pin(c1), expected_pin(c2)
        except (RuntimeError, OSError, subprocess.SubprocessError) as e:
            row("SETUP: the fake servers' certificates and expected pins were made with the openssl command line", False, repr(e))
            return
        srvA, srvB = netfake.FakeServer(c1, k1), netfake.FakeServer(c2, k2)
        srvs += [srvA, srvB]
        salt_a = srvA.add_user(NL_REMOTE, NL_PW, iterations=4096)
        salt_b = srvB.add_user(NL_REMOTE, NL_PW, iterations=4096)
        pa, pb = srvA.port, srvB.port
        H = "127.0.0.1"
        say("  [note] fake API servers on 127.0.0.1: A (key one) %d, B (key two) %d; the user %s knows the password the rows type" % (pa, pb, NL_REMOTE))

        # -- the definitions, made by the administrator with typed pins
        defs = [("nlok", pa, pin_a, "zznon,zznoff"), ("nlf", pa, pin_a, "zznon"), ("nlpin", pb, pin_a, "zznon"), ("nlb", pb, pin_b, "zznon"), ("nlnolist", pa, pin_a, "zznoff")]
        adm1(*["set.server %s %s %d reader %s read accounts %s" % (n, H, p, pin, accs) for n, p, pin, accs in defs])
        row("SETUP: five server definitions are on the disk (nlok and nlf and nlpin and nlb for zznon; nlnolist for zznoff only); nlpin sends zznon to server B with server A's pin",
            all(line_is(entry(n), [n, H, str(p), "reader", pin, "read", accs]) for n, p, pin, accs in defs), repr(file_lines()))
        if not all(entry(n) for n, *_ in defs):
            return

        def refuse(label, acct, cmd, want, answers=(), prompts=False, elev=False, no_pw_prompt=False):
            """A command that must be refused BEFORE anything is dialled: the message on the screen, no success wording, the credential directory the
            same bytes, the fake server never connected to, the helper's stand-in run or not run as the row says, the prompts shown or not, no
            audit line (and the password prompt not shown when the remote user was refused)."""
            r = nl_run(acct, cmd, answers, srvA)
            out, d = r["out"], r["d"]
            row("%s -> refused, nothing stored: %s" % (label, want[:70] + ("..." if len(want) > 70 else "")),
                has_msg(out, want) and not g.has(out, SUCC) and r["before"] == r["after"] and d["conns"] == 0 and (r["elev"] > 0) == elev
                and has_text(out, msg(11465)) == prompts and (not no_pw_prompt or not has_text(out, msg(11466)))
                and r["audit"] is not None and "set.netlogin server=" not in r["audit"],
                "message on screen=%s elev runs=%d prompts shown=%s password prompt shown=%s connections=%d before==after %s  out %r" %
                (has_msg(out, want), r["elev"], has_text(out, msg(11465)), has_text(out, msg(11466)), d["conns"], r["before"] == r["after"], out[-4:]))
            return r

        # -- the verbs are in an ordinary account's VOC from newvoc (nothing was added to the fixture accounts by this suite)
        out = g.plain("zznoff", ["set.netlogin", "delete.netlogin"])
        row("both verbs are in a fresh account's VOC, from newvoc, with the NET gate off: each answers its usage line (11450, 11451)",
            has_line(out, msg(11450)) and has_line(out, msg(11451)), repr(out[-4:]))

        say("  (every local check comes before the stand-in for the helper is run, before any prompt and before any connection)")
        refuse("set.netlogin with no server", "zznon", "set.netlogin", msg(11450))
        refuse("set.netlogin with two words", "zznon", "set.netlogin nlok nlf", msg(11450))
        for nm in ("1abc", "a_b", "a" * 17, "Upper_x"):
            refuse("set.netlogin with the server name %r" % nm, "zznon", "set.netlogin " + nm, msg(11452, nm.lower()))
        refuse("zznoff (NET gate off) on a server it is LISTED for", "zznoff", "set.netlogin nlok", msg(11460, "zznoff"))
        refuse("zznblank (a register record with no NET field)", "zznblank", "set.netlogin nlok", msg(11460, "zznblank"))
        refuse("zzntrue (field 15 'true': only yes is yes)", "zzntrue", "set.netlogin nlok", msg(11460, "zzntrue"))
        refuse("the gate is asked BEFORE the definition: zznoff on a server that does not exist", "zznoff", "set.netlogin nosuch", msg(11460, "zznoff"))
        refuse("zznon (gate on) on a server that is not defined", "zznon", "set.netlogin nosuch", msg(11430, "nosuch"))
        refuse("zznon (gate on) on a server whose list does not name it", "zznon", "set.netlogin nlnolist", msg(11461, "zznon", "nlnolist"))
        say("  (the helper: a refusal, a path that is not the person's, a directory that is not private; each ends the command before the prompts)")
        flag("elev-fail", True)
        refuse("sd-elevate netcred-dir refuses", "zznon", "set.netlogin nlok", msg(11463, "standin: refused for test"), elev=True)
        flag("elev-fail", False)
        flag("elev-wrongpath", True)
        refuse("the helper names a directory that is not <root>/<the person>", "zznon", "set.netlogin nlok", msg(11463, os.path.join(NL["root"], "someone-else")), elev=True)
        flag("elev-wrongpath", False)
        os.makedirs(NL["dir"], exist_ok=True)      # the stand-in makes the person's directory (then sets the mode); it must already be there for 'nothing changed' to be a fair test
        flag("elev-mode", True, "755")
        refuse("the helper's directory is mode 755 (not private)", "zznon", "set.netlogin nlok", msg(11463, NL["dir"]), elev=True)
        flag("elev-mode", False)
        if os.path.isdir(NL["dir"]):
            os.chmod(NL["dir"], 0o700)
        say("  (the prompts: a remote user or password that is not acceptable ends the command with nothing sent; a refused user never meets the password prompt)")
        refuse("an empty remote user", "zznon", "set.netlogin nlok", msg(11467), [""], prompts=True, elev=True, no_pw_prompt=True)
        refuse("a remote user with a space", "zznon", "set.netlogin nlok", msg(11467), ["bad user"], prompts=True, elev=True, no_pw_prompt=True)
        refuse("a remote user with an exclamation mark", "zznon", "set.netlogin nlok", msg(11467), ["bad!"], prompts=True, elev=True, no_pw_prompt=True)
        refuse("a remote user of 64 characters", "zznon", "set.netlogin nlok", msg(11467), ["u" * 64], prompts=True, elev=True, no_pw_prompt=True)
        refuse("an empty remote password", "zznon", "set.netlogin nlok", msg(11468), [NL_REMOTE, ""], prompts=True, elev=True)

        def fail_row(tag, server, srv, port, cfg, label, user, pw, want, types):
            srv.configure(**cfg)
            r = nl_run("zznon", "set.netlogin " + server, [user, pw], srv)
            srv.configure()
            out, d = r["out"], r["d"]
            row("[%s] %s -> refused: %s ... nothing stored, the credential directory the same bytes" % (tag, label, want[:60]),
                has_msg(out, want) and not g.has(out, SUCC) and r["before"] == r["after"] and d["conns"] == 1 and d["types"] == types and not d["errors"]
                and r["audit"] is not None and "set.netlogin server=" not in r["audit"] and pw not in "\n".join(out),
                "message on screen=%s before==after %s server saw %s  out %r" % (has_msg(out, want), r["before"] == r["after"], {k: d[k] for k in ("conns", "types", "errors")}, out[-4:]))

        def matrix(tag, server):
            say("  (%s: a server that goes wrong at each step, and a wrong password; the exchange is cut short at the step named)" % tag)
            ref = msg(11474, " (Authentication failed)")
            cases = [
                ("a wrong password", {}, NL_REMOTE, NL_BADPW, ref, [47, 48]),
                ("a remote user the server does not know", {}, "mallory", NL_PW, ref, [47]),
                ("a refusal with no text (error field 3)", dict(first_error=(netfake.SV_ERROR, "")), NL_REMOTE, NL_PW, msg(11474, ""), [47]),
                ("a refusal of the final message whose text holds a bell and a control byte (shown cleaned)", dict(final_error=(netfake.SV_ON_ERROR, "Oops\x07\x01 text")), NL_REMOTE, NL_PW,
                 msg(11474, " (Oops text)"), [47, 48]),
                ("an iteration count of 1", dict(offer_iter=1), NL_REMOTE, NL_PW, msg(11473, "first", "unacceptable iteration count"), [47]),
                ("an iteration count of 4095 (one below the floor)", dict(offer_iter=4095), NL_REMOTE, NL_PW, msg(11473, "first", "unacceptable iteration count"), [47]),
                ("an iteration count of 99999999 (above the ceiling)", dict(offer_iter=99999999), NL_REMOTE, NL_PW, msg(11473, "first", "unacceptable iteration count"), [47]),
                ("an iteration count that is not a number", dict(iter_text="abc"), NL_REMOTE, NL_PW, msg(11473, "first", "the iteration count is not a whole number"), [47]),
                ("a salt that is not base64", dict(salt_text="!!!!"), NL_REMOTE, NL_PW, msg(11473, "first", "the salt is not valid"), [47]),
                ("a nonce that does not extend ours", dict(nonce="wrong"), NL_REMOTE, NL_PW, msg(11473, "first", "the nonce does not extend ours"), [47]),
                ("a nonce that is ours and nothing more", dict(nonce="same"), NL_REMOTE, NL_PW, msg(11473, "first", "the nonce does not extend ours"), [47]),
                ("a server-first message with no attributes", dict(first_raw="garbage"), NL_REMOTE, NL_PW, msg(11473, "first", "malformed"), [47]),
                ("a WRONG v= signature (the server does not know the password)", dict(bad_v=True), NL_REMOTE, NL_PW, msg(11475), [47, 48]),
                ("an answer that is not v=", dict(no_v=True), NL_REMOTE, NL_PW, msg(11473, "final", "no server signature"), [47, 48]),
                ("a connection closed after the first message", dict(close_after="first"), NL_REMOTE, NL_PW, msg(11472, H, pa, "the server's first reply"), [47]),
                ("a connection closed after the final message", dict(close_after="final"), NL_REMOTE, NL_PW, msg(11472, H, pa, "the final reply"), [47, 48]),
                ("a connection closed before the Ack byte", dict(close_after="handshake"), NL_REMOTE, NL_PW, msg(11472, H, pa, "the start of the session"), []),
            ]
            for label, cfg, user, pw, want, types in cases:
                fail_row(tag, server, srvA, pa, cfg, label, user, pw, want, types)

        # -- the failures first, on a server with NO login yet
        matrix("nlf: no login yet", "nlf")
        row("...and after all of them there is no credential directory entry for nlf at all", (cred_state() or {}).get("nlf") is None, repr(cred_state()))

        # -- the success
        say("  (the success: zznon, listed, NET gate on, the right password)")
        r = nl_run("zznon", "set.netlogin nlok", [NL_REMOTE, NL_PW], srvA)
        out, d = r["out"], r["d"]
        ex = d["exchanges"][0] if d["exchanges"] else None
        keys = netfake.derive(NL_PW, salt_a, 4096)
        row("set.netlogin nlok as zznon: the header (11464), both prompts, and 'Your login on server nlok as %s is stored.  The password is not stored' (11477)" % NL_REMOTE,
            has_msg(out, msg(11464, "nlok", H, pa)) and has_text(out, msg(11465)) and has_text(out, msg(11466)) and has_msg(out, msg(11477, "nlok", NL_REMOTE)), repr(out[-6:]))
        row("...the helper's stand-in was run once, as the person, with the one word netcred-dir", r["elev"] == 1 and open(NL["log"]).read().strip().splitlines()[-1] == "standin: netcred-dir", repr(r["elev"]))
        row("...the fake server saw ONE connection, ONE TLS handshake, exactly two packets of types 47 then 48 and nothing after, one proof verified, nothing it found wrong",
            d["conns"] == 1 and d["handshakes"] == 1 and d["types"] == [47, 48] and d["ok"] == 1 and d["bad"] == 0 and not d["errors"], repr({k: d[k] for k in ("conns", "handshakes", "types", "ok", "bad", "errors")}))
        row("...client-first is p=tls-exporter,, with n=%s and a client nonce of 24 base64 characters; client-final is c=<binding>,r=<our nonce and the server's>,p=<44 characters>; the binding "
            "decodes to the GS2 header and more (its VALUE is not checkable here)" % NL_REMOTE,
            ex is not None and re.fullmatch(r"n=%s,r=[A-Za-z0-9+/]{24}" % NL_REMOTE, ex["cfirst_bare"]) is not None
            and re.fullmatch(r"c=[A-Za-z0-9+/=]+,r=[^,]+,p=[A-Za-z0-9+/]{43}=", ex["final_text"]) is not None and ex["nonce"] == ex["cnonce"] + ex["snonce"]
            and ex["cbind"].startswith(netfake.GS2) and len(ex["cbind"]) > len(netfake.GS2), repr(ex and (ex["cfirst_bare"], ex["final_text"][:60])))
        row("...the ClientProof the client sent EQUALS the one computed here (PBKDF2 of the typed password with the salt and count the server gave, over the AuthMessage the server recorded)",
            ex is not None and ex["proof"] == netfake.client_proof(keys["client_key"], keys["stored_key"], ex["authmsg"]), repr(ex and ex["proof"].hex()))
        row("...the login is on the disk: ONE line v1|%s|salt|4096|ClientKey|ServerKey|pin|date with the salt the server gave, the ClientKey and ServerKey computed here, and the pin of the "
            "DEFINITION (%s...)" % (NL_REMOTE, pin_a[:12]),
            cred_matches("nlok", NL_REMOTE, salt_a, 4096, keys["client_key_b64"], keys["server_key_b64"], pin_a), repr(read_cred("nlok")))
        try:
            st = os.lstat(cred_path("nlok"))
            row("...file mode 600, a plain file, owned by the person; the directory mode 700 and holding only nlok (no nlok.new); the root 755",
                S_IMODE(st.st_mode) == 0o600 and S_ISREG(st.st_mode) and st.st_uid == os.getuid() and S_IMODE(os.lstat(NL["dir"]).st_mode) == 0o700
                and S_IMODE(os.lstat(NL["root"]).st_mode) == 0o755 and "nlok" in os.listdir(NL["dir"]) and "nlok.new" not in os.listdir(NL["dir"]), "%s %s" % (oct(st.st_mode), os.listdir(NL["dir"])))
        except OSError as e:
            row("...file mode 600 (the file could not be examined)", False, repr(e))
        au = r["audit"]
        row("...the audit trail gained exactly one set.netlogin line: 'set.netlogin server=nlok remote=%s', and nothing in it is the password, a key or a hash" % NL_REMOTE,
            au is not None and len(re.findall(r"set\.netlogin server=", au)) == 1 and re.search(r"set\.netlogin server=nlok remote=%s(?:\s|$)" % NL_REMOTE, au) is not None
            and all(x not in au for x in (NL_PW, keys["client_key_b64"], keys["server_key_b64"], pin_a, salt_a)), repr((au or "NO AUDIT FILE")[-300:]))
        row("...the typed password is not on the screen (SD echoes asterisks) and is not in the output at all", NL_PW not in "\n".join(out), repr(out[-6:]))
        keep = cred_state()

        # -- the same failures with a login already there: it must be untouched
        matrix("nlok: a login already stored", "nlok")
        row("...and after all of them the stored login is still the one written (same bytes, same inode, same time)", cred_state() == keep, "")

        # -- replacing a login on success, silently
        salt_a2 = srvA.add_user(NL_REMOTE, NL_PW2, iterations=5000)
        r = nl_run("zznon", "set.netlogin nlok", [NL_REMOTE, NL_PW2], srvA)
        k2 = netfake.derive(NL_PW2, salt_a2, 5000)
        row("set.netlogin on a server that has a login REPLACES it with no question, on success: the file now holds the new salt, 5000 iterations and the new keys, and the old bytes are gone",
            has_msg(r["out"], msg(11477, "nlok", NL_REMOTE)) and cred_matches("nlok", NL_REMOTE, salt_a2, 5000, k2["client_key_b64"], k2["server_key_b64"], pin_a)
            and r["after"]["nlok"][3] != keep["nlok"][3] and sorted(r["after"]) == sorted(set(keep) | {"nlok"}), repr(read_cred("nlok")))
        row("...replaced through a copy that is gone again (no nlok.new), mode 600, and the new password is not on the screen", "nlok.new" not in r["after"]
            and S_IMODE(r["after"]["nlok"][0]) == 0o600 and NL_PW2 not in "\n".join(r["out"]), repr(sorted(r["after"])))
        salt_a = srvA.add_user(NL_REMOTE, NL_PW, iterations=4096)

        # -- the key the server presents is not the key in the definition
        say("  (the pin: server B presents key two, the definition nlpin holds key one's hash)")
        srvB.configure()
        r = nl_run("zznon", "set.netlogin nlpin", [NL_REMOTE, NL_PW], srvB)
        out, d = r["out"], r["d"]
        row("a pin that differs: 'The key presented by 127.0.0.1:%d is not the key in the definition of server nlpin.  Nothing was sent to it and nothing was stored'" % pb,
            has_msg(out, msg(11471, H, pb, "nlpin")) and not g.has(out, SUCC), repr(out[-3:]))
        row("...THE SERVER RECEIVED NOTHING: one connection, one completed TLS handshake, ZERO packets and zero application bytes (the password was not even used)",
            d["conns"] == 1 and d["handshakes"] == 1 and d["types"] == [] and d["app_bytes"] == 0 and d["ok"] == 0 and d["bad"] == 0, repr({k: d[k] for k in ("conns", "handshakes", "types", "app_bytes")}))
        row("...nothing stored (no nlpin file), no audit line, and the password not on the screen",
            r["before"] == r["after"] and (r["after"] or {}).get("nlpin") is None and r["audit"] is not None and "set.netlogin server=" not in r["audit"] and NL_PW not in "\n".join(out), repr(r["after"]))
        plant("nlpin", valid_line(pin=pin_a))
        before = cred_state()
        r = nl_run("zznon", "set.netlogin nlpin", [NL_REMOTE, NL_PW], srvB)
        row("a pin that differs with a login ALREADY stored for that server: refused the same way, zero packets, and the stored login is the same bytes, inode and time",
            has_msg(r["out"], msg(11471, H, pb, "nlpin")) and r["d"]["types"] == [] and r["d"]["app_bytes"] == 0 and r["after"] == before, repr(r["out"][-3:]))
        r = nl_run("zznon", "set.netlogin nlb", [NL_REMOTE, NL_PW], srvB)
        kb = netfake.derive(NL_PW, salt_b, 4096)
        row("CONTROL: the same server B with a definition that holds ITS key's hash succeeds (so the refusal above is the pin and not a broken server): login stored with pin %s..." % pin_b[:12],
            has_msg(r["out"], msg(11477, "nlb", NL_REMOTE)) and r["d"]["types"] == [47, 48] and r["d"]["ok"] == 1
            and cred_matches("nlb", NL_REMOTE, salt_b, 4096, kb["client_key_b64"], kb["server_key_b64"], pin_b), repr(r["out"][-3:]))

        # -- the administrator is exempt from the gate and the list
        r = nl_run(None, "set.netlogin nlnolist", [NL_REMOTE, NL_PW], srvA, admin=True)
        ka = netfake.derive(NL_PW, salt_a, 4096)
        row("the ADMINISTRATOR (zznon is not listed for nlnolist and holds no gate here; the administrator needs neither) goes through to the prompts and stores a login "
            "(in a sandbox the administrator is the sandbox user; on an install SDSYS gets 11462 instead - witness only)",
            has_msg(r["out"], msg(11477, "nlnolist", NL_REMOTE)) and cred_matches("nlnolist", NL_REMOTE, salt_a, 4096, ka["client_key_b64"], ka["server_key_b64"], pin_a), repr(r["out"][-4:]))

        # -- delete.netlogin
        say("  (delete.netlogin: only a private plain file, and no gate)")
        for label, cmd, want in (("no server", "delete.netlogin", msg(11451)), ("two words", "delete.netlogin a b", msg(11451)), ("a bad name", "delete.netlogin 1x", msg(11452, "1x"))):
            r = nl_run("zznon", cmd)
            row("delete.netlogin with %s -> %s, nothing removed" % (label, want), has_msg(r["out"], want) and r["before"] == r["after"], repr(r["out"][-3:]))
        before = cred_state()
        r = nl_run("zznon", "delete.netlogin nlok")
        row("delete.netlogin nlok as zznon: 'Your login on server nlok was deleted' (11478), nlok is GONE from the disk and every other file is the same bytes",
            has_msg(r["out"], msg(11478, "nlok")) and "nlok" not in (r["after"] or {}) and {k: v for k, v in before.items() if k != "nlok"} == r["after"], repr(r["out"][-3:]))
        row("...the audit trail gained 'delete.netlogin server=nlok' and nothing else of the verb's",
            r["audit"] is not None and re.search(r"delete\.netlogin server=nlok(?:\s|$)", r["audit"]) is not None and len(re.findall(r"delete\.netlogin", r["audit"])) == 1, repr((r["audit"] or "NO AUDIT FILE")[-200:]))
        r = nl_run("zznon", "delete.netlogin nlok")
        row("a second delete.netlogin nlok: 'There is no login stored for server nlok' (11453), nothing changes, no audit line",
            has_msg(r["out"], msg(11453, "nlok")) and r["before"] == r["after"] and "delete.netlogin server=" not in (r["audit"] or "x"), repr(r["out"][-3:]))
        plant("nlbad", valid_line(), mode=0o644)
        r = nl_run("zznon", "delete.netlogin nlbad")
        row("a login file that is mode 644 is NOT removed: 'The stored login for server nlbad is not trusted' (11454, with its path); the file is still there, the same bytes",
            has_msg(r["out"], msg(11454, "nlbad", cred_path("nlbad"))) and r["before"] == r["after"] and (r["after"] or {}).get("nlbad") is not None, repr(r["out"][-3:]))
        decoy = os.path.join(work, "decoy2")
        with open(decoy, "wb") as f:
            f.write(b"decoy2\n")
        os.chmod(decoy, 0o600)
        os.symlink(decoy, cred_path("nllink"))
        r = nl_run("zznon", "delete.netlogin nllink")
        row("a SYMBOLIC LINK named for a server is refused (11454) and left, with its target", has_msg(r["out"], msg(11454, "nllink", cred_path("nllink"))) and os.path.islink(cred_path("nllink"))
            and open(decoy, "rb").read() == b"decoy2\n", repr(r["out"][-3:]))
        os.mkdir(cred_path("nldir"), 0o700)
        with open(os.path.join(cred_path("nldir"), "keep"), "wb") as f:
            f.write(b"keep\n")
        r = nl_run("zznon", "delete.netlogin nldir")
        row("a DIRECTORY named for a server is refused (11454) and neither it nor what is in it is removed", has_msg(r["out"], msg(11454, "nldir", cred_path("nldir")))
            and os.path.isfile(os.path.join(cred_path("nldir"), "keep")), repr(r["out"][-3:]))
        os.remove(os.path.join(cred_path("nldir"), "keep"))
        os.rmdir(cred_path("nldir"))
        os.remove(cred_path("nllink"))
        os.remove(decoy)
        plant("nlnog", valid_line())
        r = nl_run("zznoff", "delete.netlogin nlnog")
        row("NO GATE IS ASKED: zznoff (NET gate off, not listed anywhere) deletes its own login", has_msg(r["out"], msg(11478, "nlnog")) and "nlnog" not in (r["after"] or {}), repr(r["out"][-3:]))

        # -- an ordinary account cannot reach the file any way but through the verbs
        say("  (an ordinary account with the OS-access gate off cannot read, remove or call its way to the login)")
        plant("nlgate", valid_line())
        gate_before = cred_state()
        path = cred_path("nlgate")
        prog_w = "\n".join(["   crt 'CW begin'",
                            "   openseq '%s' to f1 then crt 'CW read-open OK' else crt 'CW read-open REFUSED ':status()" % path,
                            "   dok = @true", "   deleteseq '%s', 'nlgate' else dok = @false" % NL["dir"],
                            "   crt 'CW delete ':(if dok then 'OK' else 'REFUSED')", "   crt 'CW end'", "end", ""])
        prog_r = "\n".join(["   openseq '%s' to f1 then crt 'CR read-open OK' else crt 'CR read-open REFUSED ':status()" % path,
                            "   readseq line from f1 then crt 'CR first=':line[1, 3] else crt 'CR no line'", "   crt 'CR end'", "end", ""])
        names = {"w": "zznlw" + RUN, "r": "zznlr" + RUN, "c": "zznc3" + RUN}
        g.put(os.path.join(acct_path("zznon"), "bp", names["w"]), prog_w)
        g.put(os.path.join(acct_path("zznosx"), "bp", names["r"]), prog_r)
        g.put(os.path.join(acct_path("zznon"), "bp", names["c"]), ZZNC3)
        out = g.plain("zznon", ["BASIC bp " + names["w"], "RUN bp " + names["w"]])
        got = {m.group(1): m.group(2) for m in (re.match(r"^CW (\S+) (OK|REFUSED(?: \d+)?)$", ln) for ln in out) if m}
        row("zznon (OS.EXECUTE no, SH no; it HAS the NET gate): a program that OPENSEQs the login by its path is refused (status 3035) and one that DELETESEQs it is refused",
            g.has(out, r"^CW end$") and got.get("read-open") == "REFUSED 3035" and got.get("delete") == "REFUSED", repr((got, out[-3:])))
        row("...and the disk agrees: the login is the same bytes", cred_state() == gate_before, "")
        out = g.plain("zznosx", ["BASIC bp " + names["r"], "RUN bp " + names["r"]])
        row("CONTROL: the same open from zznosx (OS.EXECUTE yes) WORKS and reads the first three characters, v1| - the HONEST LIMIT: an account that holds the gate reads what its Linux user reads, "
            "as it reads ~/.ssh - and the refusal above is the gate and not a file that cannot be opened",
            g.has(out, r"^CR read-open OK$") and has_line(out, "CR first=v1|"), repr(out[-4:]))
        g.put(os.path.join(g.SYS, "gpl.bp", "zznc2"), ZZNC2)
        out2 = g.adm(["RUN gpl.bp zznc2"], internal=True)
        row("CONTROL: the same READ as an INTERNAL program gets the record (NC2 remote=%s)" % NL_REMOTE, has_line(out2, "NC2 remote=%s err=" % NL_REMOTE), repr(out2[-3:]))
        out3 = g.plain("zznon", ["BASIC bp " + names["c"], "RUN bp " + names["c"]])
        row("an ordinary account's program that CALLs $netcred gets NO record (it does not compile, or it is stopped; either way the remote user is not printed): %s" %
            ("compiled" if g.has(out3, r"^Compiled 1 program\(s\) with no errors") else "did not compile"),
            not has_line(out3, "NC3 remote=%s err=" % NL_REMOTE) and not has_text(out3, "NC3 remote=%s" % NL_REMOTE), repr(out3[-4:]))
        for acct in ("zznon", "zznosx"):
            for d in ("bp", "bp.out"):
                for nm in names.values():
                    p = os.path.join(acct_path(acct), d, nm)
                    if os.path.exists(p):
                        os.remove(p)

        # -- the password is nowhere: not in the sandbox, not in the scratch area
        say("  (the three remote passwords, searched for in every file of the sandbox and of the scratch area)")
        canary = b"zq7-canary-%s" % RUN.encode()
        with open(os.path.join(work, "canary.txt"), "wb") as f:
            f.write(b"x" * 1000 + canary + b"y" * 10)
        needles = [NL_PW.encode(), NL_PW2.encode(), NL_BADPW.encode(), canary]
        nfiles, found = scan_for(needles, [g.BOX, work])
        row("the scan itself works: it read %d files and found the planted canary in exactly the one file that holds it (and not in the others)" % nfiles,
            nfiles > 500 and found[canary] == [os.path.join(work, "canary.txt")], repr((nfiles, found[canary])))
        for nm, pw in (("the successful password", NL_PW), ("the replacement password", NL_PW2), ("the WRONG password", NL_BADPW)):
            row("%s is in NO file of the sandbox (%s) and none of the scratch area: not the credential files, not the audit trail, not a command stack" % (nm, g.BOX), not found[pw.encode()], repr(found[pw.encode()][:5]))
        row("the fake server was never given a protocol it found wrong (no malformed message from SD over the whole run)", not srvA.errors and not srvB.errors, repr((srvA.errors, srvB.errors)))
    finally:
        for s in srvs:
            s.shutdown()
        for p in (netfile(), netfile() + ".new", netfile() + ".lock"):
            if os.path.exists(p):
                os.remove(p)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-net.py <dir> [--build] [--sections=a,b]   (parts: gate, logto, modify, manifest, defs, connect, netcred, netlogin, ordinary)")
    g.BOX = os.path.abspath(args[0])
    g.SYS = os.path.join(g.BOX, "sys")
    g.SD = os.path.join(g.SYS, "bin", "sd")
    sections = next((set(a.split("=", 1)[1].split(",")) for a in sys.argv[1:] if a.startswith("--sections=")), None)

    def run(part):
        return sections is None or part in sections
    say("sandbox-net: sandbox %s%s" % (g.BOX, "" if sections is None else "  (parts: %s)" % ",".join(sorted(sections))))
    say("sandbox-net: tree    %s" % os.path.dirname(HERE))
    if "--build" in sys.argv:
        if os.path.exists(g.BOX) and os.listdir(g.BOX):
            bail("%s is not empty" % g.BOX)
        r = subprocess.run([sys.executable, g.TOOL, g.BOX, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-net: built, bootstrap passed")
    elif not os.path.isfile(g.SD):
        bail("%s holds no built sandbox (use --build, or point it at one)" % g.BOX)
    subprocess.run([sys.executable, g.TOOL, g.BOX, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    say("\n--- preparation: a CPROC that is not the install build, the probes, the fixture accounts ---------------------------------")
    g.prepare()
    g.put(os.path.join(g.SYS, "gpl.bp", "zznk"), ZZNK)
    g.put(os.path.join(g.SYS, "gpl.bp", "zznkset"), ZZNKSET)
    out = g.adm(["BASIC gpl.bp zznk zznkset"], internal=True)
    row("the kernel probes zznk and zznkset (K$NET) compile", g.has(out, r"^Compiled 2 program\(s\) with no errors"), repr(out[-6:]))
    for n in ACCOUNTS:
        build(n)
    g.put(os.path.join(g.SYS, "bp", "zznetfix"), fixer_text())
    out = g.adm(["BASIC bp zznetfix", "RUN bp zznetfix"], internal=True)
    if not g.has(out, r"^NETFIX done$"):
        bail("the fixture accounts were not completed:\n" + "\n".join(out[-6:]))
    say("  [done] %d accounts: %s" % (len(ACCOUNTS), " ".join(ACCOUNTS)))
    f = g.flags(g.plain("zznoff", ["ZZKF"]))
    row("CONTROL: a plain session in zznoff is not an administrator (admin=0), so no ordinary-session row below passes merely because the session may do anything",
        f is not None and f[0] == "0", repr(f))
    if f is None or f[0] != "0":
        bail("the plain session is an administrator (or printed nothing): every row below would be meaningless")

    for name, section in (("gate", gate_section), ("logto", logto_section), ("modify", modify_section), ("manifest", manifest_section),
                          ("defs", defs_section), ("connect", connect_section), ("netcred", netcred_section), ("netlogin", netlogin_section),
                          ("ordinary", ordinary_section)):
        if run(name):
            section()
    nl_cleanup()

    say("")
    say("sandbox-net: %d passed, %d failed" % (passed, failed))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
