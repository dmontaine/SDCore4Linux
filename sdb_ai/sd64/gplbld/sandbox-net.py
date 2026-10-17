#!/usr/bin/env python3
#
# sandbox-net.py - the NET gate and the SDNet server definitions (S.65 slice 1, the owner's request of 17 Oct 2026).  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-net.py <dir> [--build] [--sections=a,b]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or absent);
# without it <dir> must already be built.  Exit 0 every row passed, 1 a row failed, 2 it could not run.  --sections= runs only the named
# parts (gate, logto, modify, manifest, defs, ordinary); no flag runs all of them.
#
# START-HISTORY:
# 17 Oct 26 dm  New.  S.65 slice 1: register field 15 (ACC$NET), K_NET 127, the user table's UG_NET bit, MODIFY.ACCOUNT NET-ON / NET-OFF,
#               the manifest key net, LOGIN / CPROC's logto (and the way back under OPTION STACKED.ACCOUNT); and the SDSYS-only verbs
#               set.server, delete.server and list.servers with the file netservers they keep (!netdefs).  NOTHING OPENS A REMOTE FILE
#               YET: the gate has no effect and the definitions are used by nothing, and these rows say only that they are right.
#               ***NOT YET RUN*** - written on 17 Oct without a sandbox to run it on.  The first run is the first evidence; read a red
#               row as a possible wrong expectation in this file as well as a fault in the tree.
# END-HISTORY
#
# It uses sandbox-gates.py's way of making ordinary sessions in fixture accounts, by loading that file.  The sandbox user plays SDSYS (the
# session is an administrator only when SDTEST_ADMIN=1, which g.adm() and g.sd(admin=True) set); every other session is ordinary.
#
# WHAT IT CANNOT SHOW.  (1) The API server's load of the gate (api.net.grant): a sandbox cannot host an API session, so that is a
# witness row.  (2) The file's owner and its mode against ANOTHER operating system user: the sandbox user is SDSYS and every
# fixture account's user, so the mode (0644) is read from the disk but whether an unprivileged user can write the file is not tried; an
# ordinary account's refusal here is the S.63 OS-access gate (status 3035), which an os-on account does not meet.  (3) The audit lines
# (they are in a file only root reads).  (4) CREATE.ACCOUNT, which makes Linux users.
#
# THE INSTRUMENTS.  zznk (a $internal verb in every fixture account) prints "NK net=<0|1> admin=<0|1>": the kernel's own answer to
# K$NET and whether the session is an administrator; zznkset sets it from internal code and reads it back.  For the verbs the evidence is
# the DISK: the bytes of <sandbox>/sys/netservers before and after each command, line by line, and the message the verb printed,
# matched against the text of the message file the sandbox was built with.  A refusal row demands the failure wording AND no success
# wording AND the file unchanged AND no netservers.new left behind.  Every session is ended: the input always ends with OFF, the only
# question the verbs ask (replace?) is answered by a line in the same input, and an unanswered one is read as a no at the end of input.

import datetime
import importlib.util
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
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


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-net.py <dir> [--build] [--sections=a,b]")
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
                          ("defs", defs_section), ("ordinary", ordinary_section)):
        if run(name):
            section()

    say("")
    say("sandbox-net: %d passed, %d failed" % (passed, failed))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
