#!/usr/bin/env python3
"""test-net-units.py - the NET gate and the SDNet server definitions (S.65 slice 1), as invariants read off the source.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-net-units.py
  python3 .../test-net-units.py --selftest

No sudo, no install, no sd.  Exit 0 every check passed, 1 a check failed, 2 it could not run.  Written 17 Oct 26.

***WHAT THIS IS, AND WHAT IT IS NOT.***  It reads the C and BASIC sources as text, with comments removed, so a gate that survives only
in a comment does not count.  ***IT DOES NOT RUN ANYTHING, SO IT CANNOT SAY THAT THE GATE ANSWERS OR THAT A VERB WRITES OR REFUSES***:
that is sandbox-net.py (ordinary and administrator sessions on a private SD; the disk and the kernel's own answer are the evidence).
What a text check is for: the numbers must agree across seven files, the gate is loaded in four programs (LOGIN, CPROC at LOGTO and
on the way back, the API server), and the invariants that make the verbs safe are ORDER - every field looked at before the first
write, the administrator test before anything else, the umask around the creation of the file, the rename last, the lock released
after the write.  An edit that moves one still compiles.

NOTHING OPENS A REMOTE FILE YET.  This slice is the gate (nothing reads it) and the definitions (nothing uses them); the checks say
so by what they do not look for.

***AND THE CHECKS ARE THEMSELVES CHECKED.***  --selftest breaks each invariant in the way an edit plausibly would and requires some
check to notice.  A mutant that nothing catches is reported as a FAILURE of the self-test.
"""

import functools
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.abspath(os.path.join(HERE, os.pardir))
SDSYS = os.path.join(SD64, "sdsys")
GPL = os.path.join(SDSYS, "gpl.bp")
GPLSRC = os.path.join(SD64, "gplsrc")
ROOT = os.path.dirname(os.path.dirname(SD64))
MSGDIR = os.path.join(SDSYS, "messages")

C_FILES = ("keys.h", "sysseg.h", "op_kernel.c")
MAIN_BP = ("login", "cproc", "apisrvr", "modifya", "createa", "create_account", "acc_os_info", "restorea",
           "netdefs", "setserver", "deleteserver", "listservers")
VERBS = (("set.server", "setserver", "$setserver"), ("delete.server", "deleteserver", "$deleteserver"),
         ("list.servers", "listservers", "$listservers"))
MSG_FIRST, MSG_LAST = 11411, 11439
LINUX_BLOCK = (11000, 11999)


@functools.lru_cache(maxsize=None)
def strip_c(src):
    def blank(m):
        return "\n" * m.group(0).count("\n")
    src = re.sub(r"/\*.*?\*/", blank, src, flags=re.S)
    return re.sub(r"//[^\n]*", "", src)


@functools.lru_cache(maxsize=None)
def strip_bas(src):
    out = []
    for line in src.split("\n"):
        s = line.lstrip()
        if s.startswith("*") or s.startswith("!"):
            out.append("")
            continue
        cut = line.find(";*")
        out.append(line if cut < 0 else line[:cut])
    return "\n".join(out)


@functools.lru_cache(maxsize=None)
def strip_sh(src):
    return "\n".join("" if l.lstrip().startswith("#") else l for l in src.split("\n"))


def strip_strings(src):
    """Quoted text emptied, so that a word inside a string ('WRITE', 'netservers') is not taken for a statement."""
    return re.sub(r"'[^'\n]*'|\"[^\"\n]*\"", "''", src)


def code(name, text):
    if name in C_FILES:
        return strip_c(text)
    if name == "installsdcore.sh":
        return strip_sh(text)
    return strip_bas(text)


def at(text, needle, start=0):
    return text.find(needle, start)


def ordered(text, *needles):
    """Every needle found, each after the one before it."""
    pos = -1
    for n in needles:
        p = text.find(n, pos + 1)
        if p < 0:
            return False
        pos = p
    return True


def sysmsg_calls(text):
    """(number, [argument texts]) of every sysmsg(NNNNN, ...) call with a literal number."""
    out = []
    for m in re.finditer(r"sysmsg\(\s*(\d+)", text):
        k = m.end()
        while k < len(text) and text[k] in " \t":
            k += 1
        if k < len(text) and text[k] == ",":
            k += 1
        args, cur, depth, q = [], "", 0, None
        while k < len(text):
            ch = text[k]
            if q:
                cur += ch
                if ch == q:
                    q = None
            elif ch in "'\"":
                q = ch
                cur += ch
            elif ch in "(<":
                depth += 1
                cur += ch
            elif ch in ")>":
                if ch == ")" and depth == 0:
                    if cur.strip():
                        args.append(cur.strip())
                    break
                depth -= 1
                cur += ch
            elif ch == "," and depth == 0:
                args.append(cur.strip())
                cur = ""
            else:
                cur += ch
            k += 1
        out.append((int(m.group(1)), args))
    return out


def load():
    srcs = {}

    def get(name, path):
        if not os.path.exists(path):
            print("test-net-units: CANNOT RUN - %s is missing" % path)
            sys.exit(2)
        with open(path, encoding="utf-8", errors="replace") as f:
            srcs[name] = f.read()
    for n in C_FILES:
        get(n, os.path.join(GPLSRC, n))
    get("int$keys.h", os.path.join(GPL, "int$keys.h"))
    get("syscom/keys.h", os.path.join(SDSYS, "syscom", "keys.h"))
    get("createacc.h", os.path.join(SDSYS, "syscom", "createacc.h"))
    get("installsdcore.sh", os.path.join(ROOT, "installsdcore.sh"))
    for fname in sorted(os.listdir(GPL)):
        p = os.path.join(GPL, fname)
        if os.path.isfile(p):
            get("bp:" + fname, p)
    for n in MAIN_BP:
        if "bp:" + n not in srcs:
            print("test-net-units: CANNOT RUN - %s is missing" % os.path.join(GPL, n))
            sys.exit(2)
        srcs[n] = srcs["bp:" + n]
    for word, _prog, _cat in VERBS:
        get("voc:" + word, os.path.join(SDSYS, "voc_template", word))
    srcs["newvoc.list"] = "\n".join(sorted(os.listdir(os.path.join(SDSYS, "newvoc"))))
    for n in range(MSG_FIRST, MSG_LAST + 1):
        p = os.path.join(MSGDIR, str(n))
        srcs["msg:%d" % n] = open(p, encoding="utf-8", errors="replace").read() if os.path.exists(p) else None
    for n in (2001, 2018, 6000):
        p = os.path.join(MSGDIR, str(n))
        srcs["msg:%d" % n] = open(p, encoding="utf-8", errors="replace").read() if os.path.exists(p) else None
    return srcs


def checks(srcs):
    rows = []

    def ck(i, ok, detail=""):
        rows.append((i, bool(ok), detail))

    c = {name: code(name, text) for name, text in srcs.items() if isinstance(text, str) and not name.startswith(("msg:", "voc:", "newvoc"))}

    # ---- K. numbers, bits, fields -------------------------------------------------------------------------------------------
    got = {m.group(1): int(m.group(2)) for m in re.finditer(r"#define\s+(K_[A-Z0-9_]+)\s+(\d+)", c["keys.h"])}
    ck("K1 keys.h: K_NET is 127", got.get("K_NET") == 127, repr(got.get("K_NET")))
    by_num = {}
    for k, v in got.items():
        by_num.setdefault(v, []).append(k)
    ck("K2 no kernel key number is used twice (127 is K_NET's alone)", all(len(v) == 1 for v in by_num.values()),
       repr({n: v for n, v in by_num.items() if len(v) > 1}))
    bas = {m.group(1): int(m.group(2)) for m in re.finditer(r"\$define\s+(K\$[A-Z0-9.]+)\s+(\d+)", c["int$keys.h"])}
    ck("K3 int$keys.h: K$NET is 127 and nothing else there is", bas.get("K$NET") == 127 and sum(1 for v in bas.values() if v == 127) == 1,
       repr(bas.get("K$NET")))
    acc = {m.group(1): int(m.group(2)) for m in re.finditer(r"\$define\s+(ACC\$[A-Z0-9.]+)\s+(\d+)", c["syscom/keys.h"])}
    ck("K4 syscom/keys.h: ACC$NET is register field 15; 13 and 14 stay free (reserved for the shared-account gates) and no field is used twice",
       acc.get("ACC$NET") == 15 and 13 not in acc.values() and 14 not in acc.values()
       and len(set(acc.values())) == len(acc.values()), repr(acc))
    ss = c["sysseg.h"]
    ug = {m.group(1): int(m.group(2), 16) for m in re.finditer(r"#define\s+(UG_[A-Z_]+)\s+(0x[0-9A-Fa-f]+)", ss)}
    ck("K5 sysseg.h: UG_NET is 0x0008 in the gates word, on its own bit, and 0x0010 and 0x0020 stay free for the shared gates",
       ug.get("UG_NET") == 8 and len(set(ug.values())) == len(ug) and all(v & (v - 1) == 0 for v in ug.values())
       and 0x10 not in ug.values() and 0x20 not in ug.values() and re.search(r"u_int16_t\s+gates\s*;", ss) is not None, repr(ug))
    ca = {m.group(1): int(m.group(2)) for m in re.finditer(r"\$define\s+(CA\$[A-Z0-9.]+)\s+(\d+)", c["createacc.h"])}
    ck("K6 createacc.h: CA$NET is 35, after CA$DICT.EDIT 34, and no setting is used twice",
       ca.get("CA$NET") == 35 and ca.get("CA$DICT.EDIT") == 34 and len(set(ca.values())) == len(ca.values()), repr(ca.get("CA$NET")))

    # ---- C. the kernel ---------------------------------------------------------------------------------------------------
    kn = c["op_kernel.c"]
    i = kn.find("case K_NET:")
    body = kn[i:kn.find("break;", i)] if i >= 0 else ""
    ck("C1 K_NET sets the gate only from a $internal program (n >= 0, then HDR_INTERNAL, then the bit), -1 only asks",
       kn.count("case K_NET:") == 1 and "GetInt(descr)" in body and ordered(body, "n >= 0", "HDR_INTERNAL", "n > 0", "gates |= UG_NET"), "")
    ck("C2 ...clears with UG_NET, answers the UG_NET bit as 1 or 0, and touches no other gate",
       "gates &= (u_int16_t)~UG_NET" in body and "result.data.value = (my_uptr->gates & UG_NET) != 0" in body
       and "UG_VOC_EDIT" not in body and "UG_BP_EDIT" not in body and "UG_DICT_EDIT" not in body, "")

    # ---- B. the BASIC side: where the gate is loaded --------------------------------------------------------------------------
    lg, cp, ap = c["login"], c["cproc"], c["apisrvr"]
    ck("B1 LOGIN loads K$NET from ACC$NET at sign-on, off unless 'yes', beside the SD.ACCOUNTS load and before the edit gates",
       len(re.findall(r"kernel\(K\$NET,", lg)) == 1
       and re.search(r"void kernel\(K\$NET,\s*upcase\(trim\(acc\.rec<ACC\$NET>\)\) = 'YES'\)", lg) is not None
       and ordered(lg, "void kernel(K$SD.ACCOUNTS,", "void kernel(K$NET,", "void kernel(K$VOC.EDIT,"), "")
    m = re.search(r"void kernel\(K\$NET,\s*upcase\(trim\(acc\.record<ACC\$NET>\)\) = 'YES'\)", cp)
    ck("B2 CPROC's logto loads K$NET from the NEW account's record (acc.record), off unless 'yes', after the SD.ACCOUNTS load and before the audit line",
       m is not None and 0 <= at(cp, "void kernel(K$SD.ACCOUNTS, upcase(trim(acc.record<") < m.start() < at(cp, "'logto account='"), "")
    ck("B3 CPROC holds it in stk.net with the other account-scoped gates and gives it back in revert.account, before the revert audit line",
       re.search(r"stk\.sd\.accounts = kernel\(K\$SD\.ACCOUNTS, -1\)\s*\n\s*stk\.net = kernel\(K\$NET, -1\)", cp) is not None
       and ordered(cp, "revert.account:", "void kernel(K$SD.ACCOUNTS, stk.sd.accounts)", "void kernel(K$NET, stk.net)", "'logto revert account='")
       and len(re.findall(r"kernel\(K\$NET,", cp)) == 3, "")
    ck("B4 the API server starts api.net.grant false at every entry, reads it from ACC$NET with the other grants, and loads K$NET with SD.ACCOUNTS",
       re.search(r"api\.net\.grant = @false", ap) is not None
       and re.search(r"api\.net\.grant = \(upcase\(trim\(acc\.rec<ACC\$NET>\)\) = 'YES'\)", ap) is not None
       and ordered(ap, "api.net.grant = @false", "api.net.grant = (upcase(trim(acc.rec<ACC$NET>)) = 'YES')", "void kernel(K$NET, api.net.grant)")
       and ordered(ap, "void kernel(K$SD.ACCOUNTS, api.sd.grant)", "void kernel(K$NET, api.net.grant)"), "")
    ck("B4b ...the load is at EVERY entry (account-scoped), so it is not inside the master.login.done test the edit gates sit in",
       0 <= at(ap, "void kernel(K$NET, api.net.grant)") < at(ap, "if not(master.login.done) then\n   void kernel(K$VOC.EDIT"), "")
    ck("B4c ...and the OS user sdsys entering the sdsys account holds it ON (the administrator passes), before the refusals and the load",
       re.search(r"if downcase\(@logname\) = 'sdsys' and downcase\(new\.account\) = 'sdsys' then(?:\s*\n\s*api\.\w+\.grant = @true)*\s*\n\s*api\.net\.grant = @true\s*\n\s*end", ap) is not None
       and 0 <= at(ap, "downcase(@logname) = 'sdsys'") < at(ap, "void kernel(K$NET, api.net.grant)"), "")
    sites = {}
    for name, text in c.items():
        if name.startswith("bp:"):
            n = len(re.findall(r"kernel\(K\$NET,", text))
            if n:
                sites[name[3:]] = n
    ck("B5 no program but LOGIN (1), CPROC (3) and the API server (1) mentions K$NET", sites == {"login": 1, "cproc": 3, "apisrvr": 1}, repr(sites))
    bad = [n[3:] for n, t in c.items() if n.startswith("bp:") and re.search(r"kernel\(K\$NET,\s*(?!-1\))(\d+|@true|1\b)", t)]
    ck("B6 nothing turns the gate on by a literal (K$NET with a number other than -1, or @true)", not bad, repr(bad))
    ups = {n[3:]: t for n, t in c.items() if n.startswith("bp:upgrade_")}
    ck("B7 there is NO upgrade walk for the gate: no upgrade_net program, no upgrade program touches ACC$NET, the installer names none "
       "(owner, 17 Oct: nothing existing used it, every existing account stays off)",
       not any("net" in n for n in ups) and not any("ACC$NET" in t for t in ups.values())
       and "upgrade_net" not in c["installsdcore.sh"] and "ACC$NET" not in c["installsdcore.sh"], "")

    # ---- M. the verbs that set it, the manifest ------------------------------------------------------------------------------
    mo = c["modifya"]
    ck("M1 MODIFY.ACCOUNT has NET-ON and NET-OFF, each through os.set with ACC$NET",
       all(re.search(r"case action = '%s'\s*\n\s*os\.field = ACC\$NET ; os\.want = @%s\s*\n\s*gosub os\.set\s*\n\s*stop" % (w, b), mo)
           for w, b in (("NET-ON", "true"), ("NET-OFF", "false"))), "")
    ck("M2 ...os.set lets the words through on a group account (as SD-ON), and says only the NET state with 11411 (the other lines unchanged)",
       re.search(r"if group\.name\[1,4\] # 'sdu_' and .*os\.field # ACC\$NET then", mo) is not None
       and re.search(r"if os\.field = ACC\$NET then\s*\n\s*crt sysmsg\(11411, acc\.name, if upcase\(trim\(acc\.new<ACC\$NET>\)\) = 'YES' then 'yes' else 'no'\)"
                     r"\s*\n\s*end else\s*\n\s*crt sysmsg\(10102,", mo) is not None, "")
    ck("M3 ...the syntax lines and the list of words name net-on and net-off",
       "modify.account <account> net-on | net-off" in mo and "net-on, net-off," in mo, "")
    cr, ca2 = c["createa"], c["create_account"]
    ck("M4 CREATE.ACCOUNT takes NET-ON (CA$NET = 1) and its syntax line names {net-on}",
       re.search(r"case upcase\(token\) = 'NET-ON'\s*\n\s*settings<CA\$NET> = 1", cr) is not None
       and cr.count("{net-on}") >= 1, "")
    ck("M5 !create_account: a request is exactly 1; a USER account is written 'yes' or 'no' explicitly, any other type 'yes' only when asked",
       "net.want = (settings<CA$NET> = 1)" in ca2
       and "acc.rec<ACC$NET> = if net.want then 'yes' else 'no'" in ca2 and "if net.want then acc.rec<ACC$NET> = 'yes'" in ca2, "")
    ck("M6 ...and a USER account is told its state: 11411 follows 11409",
       re.search(r"crt sysmsg\(11409,[^\n]*\n\s*crt sysmsg\(11411, acc\.name, acc\.rec<ACC\$NET>\)", ca2) is not None, "")
    ai, rs = c["acc_os_info"], c["restorea"]
    ck("M7 the manifest carries net: 1/0 for a USER account (after edit.dict, before the GROUP branch)",
       ordered(ai, "'edit.dict: '", "'net: '", "case grp[1,4] = 'sdg_'")
       and "'net: ':(if upcase(trim(acc.rec<ACC$NET>)) = 'YES' then 1 else 0)" in ai, "")
    ck("M8 RESTORE.ACCOUNT reads the manifest key net, clears it for each section, and hands it on as CA$NET",
       re.search(r"= 'net'\s*; m\.net = kv", rs) is not None and "settings<CA$NET> = m.net" in rs and "m.edit.dict = '' ; m.net = ''" in rs, "")

    # ---- D. the definitions: netdefs, set.server, delete.server, list.servers ------------------------------------------------------
    nd, ss_, ds, ls = c["netdefs"], c["setserver"], c["deleteserver"], c["listservers"]
    ck("D1 all four are $internal, catalogued once each under the right name, and netdefs is a subroutine",
       all("$internal" in t for t in (nd, ss_, ds, ls))
       and "subroutine netdefs(mode, defs, err)" in nd and "$catalog !netdefs" in nd
       and all(("$catalog %s" % cat) in c[prog] and len([n for n, t in c.items() if n.startswith("bp:") and ("$catalog %s\n" % cat) in t + "\n"]) == 1
               for _w, prog, cat in VERBS)
       and len([n for n, t in c.items() if n.startswith("bp:") and "$catalog !netdefs" in t]) == 1, "")
    nv = srcs["newvoc.list"].lower().split("\n")
    ck("D2 the three verbs are in voc_template (V / CA / $name) and NOT in newvoc, so only SDSYS has them",
       all(srcs["voc:" + w].split() == ["V", "CA", cat] and w not in nv for w, _p, cat in VERBS), "")
    ck("D3 each verb asks K$ADMINISTRATOR first, before it reads a word or opens anything (netdefs asks for WRITE before it looks at a line)",
       all(0 <= at(t, "kernel(K$ADMINISTRATOR, -1)") < min(x for x in (at(t, "openpath"), at(t, "@sentence"), at(t, "call !netdefs")) if x >= 0)
           for t in (ss_, ds, ls))
       and ordered(nd, "case mode = 'WRITE'", "kernel(K$ADMINISTRATOR, -1)", "dcount(defs, @fm)", "openseq tmp"), "")

    # set.server: every field before anything is written
    first_write = at(ss_, "call !netdefs('WRITE'")
    fld = [at(ss_, "sysmsg(%d" % n) for n in (11414, 11415, 11416, 11417, 11418, 11419, 11420, 11421)]
    gate = at(ss_, "if bad # 0 then stop")
    ck("S1 set.server looks at every field (11414 to 11421) BEFORE it stops on 'bad', and that stop is before the lock, the read and the write",
       all(0 <= f < gate for f in fld) and 0 <= gate < at(ss_, "openpath @sdsys to sys.f") < at(ss_, "readu lock.rec") < at(ss_, "call !netdefs('READ'") < first_write
       and ss_.count("call !netdefs('WRITE'") == 1 and ss_.count("readu lock.rec") == 1, repr((fld, gate)))
    ck("S2 ...the limit of 10 and the replace question come before the write, a 'no' (or input that ends) stops with nothing written, and NO.QUERY skips only the question",
       0 <= at(ss_, "sysmsg(11422") < first_write and 0 <= at(ss_, "sysmsg(11423") < first_write
       and re.search(r"\$define NET\.MAX\.SERVERS 10\b", ss_) is not None
       and "if found = 0 and n.defs >= NET.MAX.SERVERS then" in ss_ and "if found # 0 and not(no.query) then" in ss_
       and re.search(r"if yn = 'N' then\s*\n\s*gosub release\.lock\s*\n\s*@system\.return\.code = 0\s*\n\s*stop sysmsg\(11426", ss_) is not None
       and "if yn = '' and status() = ER$EOF then yn = 'N'" in ss_, "")
    ck("S3 ...the lock is released straight after the write, whether or not it worked, and before the audit line",
       re.search(r"call !netdefs\('WRITE', defs, err\)\s*\n\s*gosub release\.lock\s*\n\s*if err # '' then", ss_) is not None
       and 0 <= first_write < at(ss_, "kernel(K$AUDIT, 'set.server name='"), "")
    ck("S4 ...the rules: name 1-16 of lower case and digits and a letter first; host 1-253 of letters, digits, dots, hyphens and colons, not "
       "starting with - or .; port 1-65535; account 1-32 of letters, digits and ._-; pin 64 hex; at most 10 servers",
       "len(name) < 1 or len(name) > 16" in ss_ and "index(lc.set, name[1, 1], 1) = 0" in ss_
       and "len(host) < 1 or len(host) > 253" in ss_ and "chk.set = lc.set:digits:'.-:'" in ss_ and "host[1, 1] = '-' or host[1, 1] = '.'" in ss_
       and "port matches '1N0N'" in ss_ and "port + 0 >= 1 and port + 0 <= 65535" in ss_
       and "len(account) < 1 or len(account) > 32" in ss_ and "chk.set = lc.set:upcase(lc.set):digits:'._-'" in ss_
       and "len(pin) # 64" in ss_ and "chk.set = digits:'abcdef'" in ss_ and re.search(r"\$define NET\.MAX\.SERVERS 10\b", ss_) is not None, "")
    ck("S5 ...the accounts list: a name is checked for form and then against the register (11421); a list over 2000 bytes, an empty name or a name over 32 is 11420",
       re.search(r"\$define NET\.MAX\.ACCLIST 2000\b", ss_) is not None and "len(acc.list) <= NET.MAX.ACCLIST" in ss_
       and "if a = '' or len(a) > 32 or not(chk.ok) then list.ok = @false" in ss_
       and ordered(ss_, "sysmsg(11420", "openpath @sdsys:@ds:'accounts'", "read reg.rec from acc.f, a then", "sysmsg(11421"), "")
    ck("S6 ...the mode is read unless write is given, and only read or write is a mode (11419 for another word at the mode's place)",
       "mode = 'read'" in ss_ and "(lw = 'read' or lw = 'write') and not(mode.given)" in ss_ and "sysmsg(11419, w)" in ss_, "")

    # delete.server
    dwrite = at(ds, "call !netdefs('WRITE'")
    ck("X1 delete.server finds the name (11430 and a stop when there is none) and cuts it out BEFORE the one write, under the lock, released after",
       ds.count("call !netdefs('WRITE'") == 1 and ordered(ds, "readu lock.rec", "call !netdefs('READ'", "sysmsg(11430", "del defs<found>", "call !netdefs('WRITE'")
       and re.search(r"call !netdefs\('WRITE', defs, err\)\s*\n\s*gosub release\.lock", ds) is not None
       and re.search(r"if found = 0 then\s*\n\s*gosub release\.lock\s*\n\s*@system\.return\.code = -ER\$FNF\s*\n\s*stop sysmsg\(11430", ds) is not None
       and dwrite < at(ds, "kernel(K$AUDIT, 'delete.server name='"), "")
    ck("X2 delete.server wants exactly one word (11429 otherwise) and converts the name to lower case",
       "if dcount(words, ' ') # 2 then" in ds and "stop sysmsg(11429)" in ds and "name = downcase(field(words, ' ', 2))" in ds, "")

    # list.servers
    ck("L1 list.servers takes no lock and writes nothing (no readu, no WRITE, no release), and has the administrator test",
       not re.search(r"\b(readu|readvu|readlist|release|lock)\b", ls) and "!netdefs('WRITE'" not in ls and "!netdefs('READ'" in ls, "")
    ck("L2 list.servers shows the pin SHORTENED (16 digits and three dots) in the list and the FULL pin only for a named server (and the date then)",
       re.search(r"if name = '' then\s*\n\s*pin\.text = defs<i,5>\[1, 16\] : '\.\.\.'\s*\n\s*end else\s*\n\s*pin\.text = defs<i,5>\s*\n\s*end", ls) is not None
       and "if name # '' then crt sysmsg(11435, defs<i,8>)" in ls, "")
    ck("L3 list.servers: no definitions is 11433, an unknown name is 11430, a damaged line is 11436, and the account field 'none' is message 11438",
       "sysmsg(11433)" in ls and "sysmsg(11430, name)" in ls and "sysmsg(11436, i)" in ls and "sysmsg(11438)" in ls, "")

    # netdefs: the one writer
    ck("N1 !netdefs checks every definition (8 fields, no bar, no byte outside 32-126 apart from the value mark) BEFORE the first byte is written (11436)",
       ordered(nd, "case mode = 'WRITE'", "ok = (dcount(one, @vm) = NETDEFS.FIELDS)", "c # 253 and (c < 32 or c > 126 or c = 124)", "err = 11436",
               "tmp = path : '.new'", "openseq tmp to tmp.f", "writeseq line to tmp.f", "osrename(tmp, path)")
       and nd.count("openseq tmp to tmp.f") == 1 and "$define NETDEFS.FIELDS 8" in nd, "")
    ck("N2 ...the file is netservers in @sdsys, written whole as netservers.new and renamed over the old one LAST, and a failed write deletes the copy",
       "$define NETDEFS.FILE   'netservers'" in nd and "path = @sdsys:@ds:NETDEFS.FILE" in nd
       and nd.count("osrename(") == 1 and nd.count("writeseq") == 1
       and re.search(r"if err # '' then\s*\n\s*void ospath\(tmp, OS\$DELETE\)\s*\n\s*return\s*\n\s*end\s*\n\s*if not\(osrename\(tmp, path\)\) then", nd) is not None, "")
    ck("N3 ...mode 644: the umask is set to 022 (18) before the copy is made, put back straight after, and before any line is written",
       ordered(nd, "old.umask = umask(-1)", "void umask(18)", "openseq tmp to tmp.f", "void umask(old.umask)", "writeseq line to tmp.f"), "")
    ck("N4 ...READ takes no administrator test and no lock, turns the bar into a value mark, and replaces mark bytes 251 to 255 so a line cannot make a new attribute",
       ordered(nd, "case mode = 'READ'", "convert char(251)", "convert '|' to @vm in line", "case mode = 'WRITE'")
       and "kernel(K$ADMINISTRATOR" not in nd[nd.find("case mode = 'READ'"):nd.find("case mode = 'WRITE'")], "")
    names = {n[3:]: t for n, t in c.items() if n.startswith("bp:") and "netservers" in strip_strings(t).replace("'", "") + t and "netservers" in t}
    ck("N5 the file's name is in the code of netdefs, and of set.server and delete.server only as the lock id netservers.lock",
       set(names) == {"netdefs", "setserver", "deleteserver"}
       and all(re.fullmatch(r"netservers\.lock", s) for s in re.findall(r"netservers[\w.]*", ss_ + ds)), repr(sorted(names)))
    ck("N6 netdefs holds the warning: the file must never hold a secret (read raw, since it is a comment)",
       "MUST NEVER HOLD A SECRET" in srcs["netdefs"], "")

    # the pin
    wsrc = r"\b(writeseq|writeblk|weofseq|oswrite|osdelete|osrename|osopen|openseq|write|writev|writeu|writet|delete|deleteu|os\.execute|execute|create|createfile|create\.file)\b"
    def bare(t):        # no quoted text, and the PROGRAM line (the verb delete.server is not the statement DELETE)
        return strip_strings(re.sub(r"^\s*program\s+\S+", "", t, flags=re.M))
    ck("P1 set.server, delete.server and list.servers have no statement that writes, deletes, creates or runs anything outside the register and the lock "
       "(only !netdefs writes the pin to disk)",
       not any(re.search(wsrc, bare(t)) for t in (ss_, ds, ls)), repr([re.search(wsrc, bare(t)).group(0) for t in (ss_, ds, ls) if re.search(wsrc, bare(t))]))
    leaks = [ln.strip() for ln in strip_strings(ss_).split("\n") if re.search(r"\bpin\b", ln) and re.search(r"\b(display|crt|print|stop|sysmsg|kernel)\b", ln)]
    ck("P2 the pin is never shown, printed or put on the audit trail by set.server (the audit line names the server, host, port and mode)", not leaks, repr(leaks))
    ck("P3 ...it goes into the definition line and nowhere else: its only uses are the lower-casing, the form test and the line that builds the definition",
       len([ln for ln in strip_strings(ss_).split("\n") if re.search(r"\bpin\b", ln)]) == 5
       and re.search(r"one = name:@vm:host:@vm:port:@vm:account:@vm:pin:@vm:mode:@vm:acc\.clean:@vm:created", ss_) is not None
       and "'set.server name=' : name : ' host=' : host : ' port=' : port : ' mode=' : mode : ' replaced=' : rep.word" in ss_, "")

    # ---- G. messages ----------------------------------------------------------------------------------------------------------
    texts = {n: srcs["msg:%d" % n] for n in range(MSG_FIRST, MSG_LAST + 1)}
    ck("G1 messages 11411 to 11439 all exist, each one line of text, and inside the Linux block 11000-11999 (not the Windows block)",
       all(t is not None and t.strip() != "" and "\n" not in t.rstrip("\n") for t in texts.values())
       and LINUX_BLOCK[0] <= MSG_FIRST and MSG_LAST <= LINUX_BLOCK[1], repr([n for n, t in texts.items() if not t]))
    verb_code = nd + "\n" + ss_ + "\n" + ds + "\n" + ls
    used = {int(x) for x in re.findall(r"\b(114[1-3]\d)\b", verb_code)}
    ck("G2 every message from 11412 to 11439 is used by the verbs or !netdefs, and 11411 by MODIFY.ACCOUNT and CREATE.ACCOUNT",
       set(range(11412, 11440)) <= used and "11411" in mo and "11411" in ca2 and 11411 not in used, repr(sorted(set(range(11412, 11440)) - used)))
    literal = {n for n, _a in sysmsg_calls(verb_code + "\n" + mo + "\n" + ca2) if 11411 <= n <= 11439}
    reused = {n for n, _a in sysmsg_calls(verb_code)} | set(int(x) for x in re.findall(r"\berr = (\d{4,5})", verb_code))
    ck("G3 every number the verbs print exists as a message file (11412-11439 and the reused 2001, 2018, 6000)",
       all(srcs.get("msg:%d" % n) for n in reused if n in (2001, 2018, 6000) or 11411 <= n <= 11439)
       and all(n in (2001, 2018, 6000) or 11411 <= n <= 11439 for n in reused), repr(sorted(reused)))
    short = []
    for n, args in sysmsg_calls(verb_code + "\n" + mo + "\n" + ca2):
        t = srcs.get("msg:%d" % n)
        if t is None or not (11411 <= n <= 11439):
            continue
        top = max([int(x) for x in re.findall(r"%(\d)", t)] or [0])
        if len(args) != top:
            short.append((n, len(args), top))
    ck("G4 each call of sysmsg gives as many arguments as its message has %n places", not short and literal, repr(short))
    t = lambda n: texts.get(n) or ""
    ck("G5 the wording the users and the verbs rely on: 11411 'Account %1 has NET %2'; 11423 asks 'Replace it (y/<n>)?'; 11413 says nothing connects yet; "
       "11439 names net-on; 11412 is the usage line",
       t(11411).strip() == "Account %1 has NET %2" and t(11423).strip().endswith("Replace it (y/<n>)?") and "Nothing connects to the server yet" in t(11413)
       and "net-on" in t(11439) and t(11412).startswith("Usage: set.server"), "")
    return rows


def mutate(srcs, name, old, new=None):
    s = dict(srcs)
    if callable(old):                       # a mutant made by a function of the source text (raises KeyError when it does not apply)
        s[name] = old(s[name])
        return s
    if old not in s[name]:
        raise KeyError("mutant text not in %s: %r" % (name, old[:70]))
    s[name] = s[name].replace(old, new, 1)
    return s


def rx(pattern, repl, flags=0):
    def f(text):
        out, n = re.subn(pattern, repl, text, count=1, flags=flags)
        if n == 0:
            raise KeyError("pattern not in the source: %r" % pattern[:70])
        return out
    return f


def drop_line(pattern):
    """The first line that matches PATTERN is taken out."""
    return rx(r"^[^\n]*" + pattern + r"[^\n]*\n", "", re.M)


M = []   # (label, source name, old text | function, new text | None)


def mut(label, name, old, new=None):
    M.append((label, name, old, new))


# ---- K
mut("K_NET is 128", "keys.h", rx(r"(#define\s+K_NET\s+)127", r"\g<1>128"))
mut("K_NET shares 126 with K_EDIT_OS_OK", "keys.h", rx(r"(#define\s+K_NET\s+)127", r"\g<1>126"))
mut("K$NET is 128 in int$keys.h", "int$keys.h", rx(r"(\$define\s+K\$NET\s+)127", r"\g<1>128"))
mut("ACC$NET is 14", "syscom/keys.h", rx(r"(\$define\s+ACC\$NET\s+)15", r"\g<1>14"))
mut("ACC$NET is 12 (the dict edit field)", "syscom/keys.h", rx(r"(\$define\s+ACC\$NET\s+)15", r"\g<1>12"))
mut("UG_NET is 0x0010 (a shared-gate bit)", "sysseg.h", rx(r"(#define\s+UG_NET\s+)0x0008", r"\g<1>0x0010"))
mut("UG_NET shares 0x0004 with the dict gate", "sysseg.h", rx(r"(#define\s+UG_NET\s+)0x0008", r"\g<1>0x0004"))
mut("CA$NET is 34", "createacc.h", rx(r"(\$define\s+CA\$NET\s+)35", r"\g<1>34"))
mut("CA$NET is 36", "createacc.h", rx(r"(\$define\s+CA\$NET\s+)35", r"\g<1>36"))
# ---- C
mut("K_NET can be set by a user program", "op_kernel.c", rx(r"if \(process\.program\.flags & HDR_INTERNAL\) \{(\s*)if \(n > 0\)(\s*)my_uptr->gates \|= UG_NET;", r"if (1) {\1if (n > 0)\2my_uptr->gates |= UG_NET;"))
mut("K_NET switches on the wrong bit", "op_kernel.c", "my_uptr->gates |= UG_NET;", "my_uptr->gates |= UG_BP_EDIT;")
mut("K_NET switches off the wrong bit", "op_kernel.c", "my_uptr->gates &= (u_int16_t)~UG_NET;", "my_uptr->gates &= (u_int16_t)~UG_DICT_EDIT;")
mut("K_NET always answers 1", "op_kernel.c", "result.data.value = (my_uptr->gates & UG_NET) != 0;", "result.data.value = 1;")
# ---- B
mut("LOGIN forgets the NET gate", "login", drop_line(r"void kernel\(K\$NET,"))
mut("LOGIN turns the gate on for a blank field", "login", "upcase(trim(acc.rec<ACC$NET>)) = 'YES')", "upcase(trim(acc.rec<ACC$NET>)) # 'NO')")
mut("LOGIN loads the gate from the wrong field", "login", "upcase(trim(acc.rec<ACC$NET>)) = 'YES')", "upcase(trim(acc.rec<ACC$SH>)) = 'YES')")
mut("CPROC's logto forgets the NET gate", "cproc", drop_line(r"void kernel\(K\$NET, upcase\(trim\(acc\.record"))
mut("CPROC's logto loads it from the old account's record", "cproc", "void kernel(K$NET, upcase(trim(acc.record<ACC$NET>)) = 'YES')", "void kernel(K$NET, upcase(trim(acc.rec<ACC$NET>)) = 'YES')")
mut("CPROC's logto loads the gate after the audit line", "cproc", rx(r"(   void kernel\(K\$NET, upcase\(trim\(acc\.record<ACC\$NET>\)\) = 'YES'\)\n)(\n   void kernel\(K\$AUDIT, 'logto account=' : new\.account\)[^\n]*\n)", r"\2\1"))
mut("CPROC never holds the gate", "cproc", drop_line(r"stk\.net = kernel"))
mut("CPROC does not give the gate back", "cproc", drop_line(r"void kernel\(K\$NET, stk\.net\)"))
mut("CPROC gives the gate back after the revert audit line", "cproc", rx(r"(   void kernel\(K\$NET, stk\.net\)[^\n]*\n)(   void kernel\(K\$AUDIT, 'logto revert account=' : who\)\n)", r"\2\1"))
mut("the API server forgets api.net.grant at every entry", "apisrvr", drop_line(r"^api\.net\.grant = @false"))
mut("the API server starts with the gate on", "apisrvr", rx(r"api\.net\.grant = @false", "api.net.grant = @true"))
mut("the API server does not read the register field", "apisrvr", drop_line(r"api\.net\.grant = \(upcase"))
mut("the API server does not load the gate", "apisrvr", drop_line(r"^void kernel\(K\$NET, api\.net\.grant\)"))
mut("the API server loads the gate only at the first entry", "apisrvr",
    rx(r"^void kernel\(K\$NET, api\.net\.grant\)[^\n]*\n", "", re.M))
mut("the API server loads the gate with the edit gates (first entry only)", "apisrvr",
    lambda t: rx(r"^void kernel\(K\$NET, api\.net\.grant\)[^\n]*\n", "", re.M)(t).replace("if not(master.login.done) then\n   void kernel(K$VOC.EDIT,", "if not(master.login.done) then\n   void kernel(K$NET, api.net.grant)\n   void kernel(K$VOC.EDIT,", 1))
mut("SDSYS over the API does not pass the NET gate", "apisrvr", drop_line(r"api\.net\.grant = @true"))
mut("a program sets K$NET to 1", "bp:basic",lambda t: t + "\n   void kernel(K$NET, 1)\n")
mut("a program turns the gate on with @true", "bp:catalog", lambda t: t + "\n   void kernel(K$NET, @true)\n")
mut("LOGIN loads the gate twice", "login", lambda t: t + "\n   void kernel(K$NET, 0)\n")
mut("an upgrade walk for the gate appears", "bp:upgrade_gates", lambda t: t + "\n   if trim(rec<ACC$NET>) = '' then rec<ACC$NET> = 'yes'\n")
mut("the installer runs an upgrade_net walk", "installsdcore.sh", lambda t: t + "\nsudo sd -internal RUN gpl.bp upgrade_net\n")
# ---- M
mut("MODIFY.ACCOUNT loses NET-OFF", "modifya", "case action = 'NET-OFF'", "case action = 'NET-OFFX'")
mut("MODIFY.ACCOUNT loses NET-ON", "modifya", "case action = 'NET-ON'", "case action = 'NET-ONX'")
mut("NET-ON switches off", "modifya", rx(r"(case action = 'NET-ON'\s*\n\s*os\.field = ACC\$NET ; os\.want = )@true", r"\1@false"))
mut("NET-ON works on the wrong field", "modifya", rx(r"(case action = 'NET-ON'\s*\n\s*os\.field = )ACC\$NET", r"\1ACC$SD.ACCOUNTS"))
mut("a group account is refused NET-ON", "modifya", " and os.field # ACC$NET then", " then")
mut("NET-ON prints the SH line", "modifya", "if os.field = ACC$NET then", "if os.field = ACC$SD.ACCOUNTS then")
mut("the NET line names the wrong state", "modifya", "if upcase(trim(acc.new<ACC$NET>)) = 'YES' then 'yes' else 'no')   ;* Account %1 has NET %2", "if upcase(trim(acc.rec<ACC$NET>)) = 'YES' then 'yes' else 'no')   ;* Account %1 has NET %2")
mut("MODIFY.ACCOUNT's syntax lines forget the words", "modifya", "modify.account <account> net-on | net-off", "modify.account <account> net")
mut("MODIFY.ACCOUNT's word list forgets them", "modifya", "dict-on, dict-off, net-on, net-off,", "dict-on, dict-off,")
mut("CREATE.ACCOUNT loses NET-ON", "createa", "case upcase(token) = 'NET-ON'", "case upcase(token) = 'NET-ONX'")
mut("NET-ON asks for CA$NET = 0", "createa", rx(r"(case upcase\(token\) = 'NET-ON'\s*\n\s*settings<CA\$NET> = )1", r"\g<1>0"))
mut("CREATE.ACCOUNT's syntax line forgets {net-on}", "createa", lambda t: t.replace("{net-on}", "", 1))
mut("a request for the gate is any non-zero", "create_account", "net.want = (settings<CA$NET> = 1)", "net.want = (settings<CA$NET> # 0)")
mut("a new user account is written with the NET field blank", "create_account", drop_line(r"acc\.rec<ACC\$NET> = if net\.want then 'yes' else 'no'"))
mut("a new user account is written 'yes'", "create_account", "acc.rec<ACC$NET> = if net.want then 'yes' else 'no'", "acc.rec<ACC$NET> = 'yes'")
mut("a group account loses the requested gate", "create_account", drop_line(r"if net\.want then acc\.rec<ACC\$NET> = 'yes'"))
mut("CREATE.ACCOUNT does not report the state", "create_account", drop_line(r"crt sysmsg\(11411,"))
mut("the manifest drops net", "acc_os_info", drop_line(r"'net: '"))
mut("the manifest says net for the group account branch only", "acc_os_info", lambda t: t.replace("         info<-1> = 'net: ':(if upcase(trim(acc.rec<ACC$NET>)) = 'YES' then 1 else 0)", "", 1).replace("      case grp[1,4] = 'sdg_'\n", "      case grp[1,4] = 'sdg_'\n         info<-1> = 'net: ':(if upcase(trim(acc.rec<ACC$NET>)) = 'YES' then 1 else 0)\n", 1))
mut("RESTORE.ACCOUNT does not read net", "restorea", drop_line(r"= 'net'\s*; m\.net = kv"))
mut("RESTORE.ACCOUNT does not hand net on", "restorea", drop_line(r"settings<CA\$NET> = m\.net"))
mut("RESTORE.ACCOUNT keeps net from the section before", "restorea", " ; m.net = ''", "")
# ---- D / S / X / L / N / P
mut("a verb's VOC entry is missing", "voc:set.server", "$setserver", "$setserve")
mut("a verb is in newvoc, for every account", "newvoc.list", lambda t: t + "\nlist.servers")
mut("delete.server points at the wrong program", "voc:delete.server", "$deleteserver", "$setserver")
mut("a second program takes the name $setserver", "bp:cd", lambda t: t + "\n$catalog $setserver\n")
mut("set.server is not internal", "setserver", "$internal\nprogram set.server", "program set.server")
mut("set.server forgets the administrator test", "setserver", rx(r"   if not\(kernel\(K\$ADMINISTRATOR, -1\)\) then\n      stop sysmsg\(2001\)[^\n]*\n   end\n", ""))
mut("set.server tests the administrator after reading the sentence", "setserver", rx(r"(   if not\(kernel\(K\$ADMINISTRATOR, -1\)\) then\n      stop sysmsg\(2001\)[^\n]*\n   end\n)(.*)(   words = trim\(@sentence\)\n)", r"\2\3\1", re.S))
mut("delete.server forgets the administrator test", "deleteserver", rx(r"   if not\(kernel\(K\$ADMINISTRATOR, -1\)\) then\n      stop sysmsg\(2001\)[^\n]*\n   end\n", ""))
mut("list.servers forgets the administrator test", "listservers", rx(r"   if not\(kernel\(K\$ADMINISTRATOR, -1\)\) then\n      stop sysmsg\(2001\)[^\n]*\n   end\n", ""))
mut("!netdefs WRITE forgets the administrator test", "netdefs", rx(r"         if not\(kernel\(K\$ADMINISTRATOR, -1\)\) then\n            err = 2001[^\n]*\n            return\n         end\n", ""))
mut("set.server does not stop on a bad field", "setserver", "if bad # 0 then stop", "if bad > 99 then stop")
mut("set.server stops on bad before the accounts are checked", "setserver",
    lambda t: rx(r"^   if bad # 0 then stop[^\n]*\n", "", re.M)(t).replace("   acc.clean = ''\n", "   if bad # 0 then stop\n   acc.clean = ''\n", 1))
mut("set.server forgets the port message", "setserver", drop_line(r"display sysmsg\(11416"))
mut("set.server forgets the pin message", "setserver", drop_line(r"display sysmsg\(11418"))
mut("set.server does not check the register for an account", "setserver", drop_line(r"display sysmsg\(11421"))
mut("set.server takes the lock before it has opened the directory", "setserver",
    rx(r"(   openpath @sdsys to sys\.f else.*?\n   end\n)(\n   readu lock\.rec.*?\n   end else\n      null\n   end\n)", r"\2\1", re.S))
mut("set.server takes the lock only after the read", "setserver",
    lambda t: t.replace("   readu lock.rec", "   null ; zz.lock.rec", 1).replace("   d = date()\n", "   readu lock.rec from sys.f, NET.LOCK.ID locked\n   end then null\n   end else null\n   d = date()\n", 1))
mut("set.server allows an 11th server", "setserver", "n.defs >= NET.MAX.SERVERS", "n.defs >= 99")
mut("the limit is 11", "setserver", "$define NET.MAX.SERVERS 10", "$define NET.MAX.SERVERS 11")
mut("set.server replaces without asking", "setserver", "if found # 0 and not(no.query) then", "if found # 0 and no.query then")
mut("a 'no' to the question goes on to write", "setserver", rx(r"(      if yn = 'N' then\n)(         gosub release\.lock\n)", r"\1         null\n"))
mut("input that ends is a yes", "setserver", "if yn = '' and status() = ER$EOF then yn = 'N'", "if yn = '' and status() = ER$EOF then yn = 'Y'")
mut("the lock is not released after the write", "setserver", rx(r"(call !netdefs\('WRITE', defs, err\)\n)   gosub release\.lock\n", r"\1"))
mut("set.server accepts a name of 17", "setserver", "len(name) > 16", "len(name) > 17")
mut("set.server accepts a name starting with a digit", "setserver", " or index(lc.set, name[1, 1], 1) = 0", "")
mut("set.server accepts a host of 254", "setserver", "len(host) > 253", "len(host) > 254")
mut("set.server accepts a host starting with a hyphen", "setserver", " or host[1, 1] = '-' or host[1, 1] = '.'", "")
mut("set.server allows a bar in a host", "setserver", "chk.set = lc.set:digits:'.-:'", "chk.set = lc.set:digits:'.-:|'")
mut("set.server accepts port 0", "setserver", "port + 0 >= 1 and", "port + 0 >= 0 and")
mut("set.server accepts port 65536", "setserver", "port + 0 <= 65535", "port + 0 <= 65536")
mut("set.server accepts a non-numeric port", "setserver", "port matches '1N0N'", "port matches '0X'")
mut("set.server accepts an account of 33", "setserver", "len(account) > 32", "len(account) > 33")
mut("set.server accepts a pin of 63", "setserver", "len(pin) # 64", "len(pin) < 63")
mut("set.server accepts a non-hex pin", "setserver", "chk.set = digits:'abcdef'", "chk.set = digits:'abcdefg'")
mut("the accounts list may be long", "setserver", "$define NET.MAX.ACCLIST 2000", "$define NET.MAX.ACCLIST 20000")
mut("an empty account name is allowed", "setserver", "if a = '' or len(a) > 32 or not(chk.ok) then list.ok = @false", "if len(a) > 32 or not(chk.ok) then list.ok = @false")
mut("mode may be anything", "setserver", "(lw = 'read' or lw = 'write') and not(mode.given)", "not(mode.given)")
mut("the default mode is write", "setserver", "   mode = 'read'\n", "   mode = 'write'\n")
mut("set.server prints the pin", "setserver", lambda t: t.replace("display sysmsg(11424, name, host, port)", "display sysmsg(11424, name, host, port) : pin", 1))
mut("set.server puts the pin on the audit trail", "setserver", "' replaced=' : rep.word)", "' replaced=' : rep.word : ' pin=' : pin)")
mut("set.server writes a file itself", "setserver", lambda t: t.replace("   @system.return.code = 0\n   if replaced then", "   openseq 'netpin' to pf then null\n   writeseq pin to pf else null\n   @system.return.code = 0\n   if replaced then", 1))
mut("set.server stores the pin twice", "setserver", "pin:@vm:mode", "pin:@vm:pin:@vm:mode")
mut("delete.server writes before it looks for the name", "deleteserver", rx(r"(   if found = 0 then\n.*?\n   end\n)(\n   host = defs<found,2>.*?   del defs<found>\n)", r"\2\1", re.S))
mut("delete.server does not stop on an unknown name", "deleteserver", rx(r"(   if found = 0 then\n      gosub release\.lock\n      @system\.return\.code = -ER\$FNF\n)      stop sysmsg\(11430, name\)", r"\1      null"))
mut("delete.server lets two words through", "deleteserver", "if dcount(words, ' ') # 2 then", "if dcount(words, ' ') < 2 then")
mut("delete.server keeps the name's case", "deleteserver", "name = downcase(field(words, ' ', 2))", "name = field(words, ' ', 2)")
mut("delete.server leaves the lock held", "deleteserver", rx(r"(call !netdefs\('WRITE', defs, err\)\n)   gosub release\.lock\n", r"\1"))
mut("delete.server deletes without cutting the line", "deleteserver", "   del defs<found>\n", "   null\n")
mut("list.servers takes a lock", "listservers", lambda t: t.replace("   call !netdefs('READ', defs, err)", "   readu lk from sys.f, 'netservers.lock' else null\n   call !netdefs('READ', defs, err)", 1))
mut("list.servers writes", "listservers", lambda t: t.replace("   call !netdefs('READ', defs, err)", "   call !netdefs('WRITE', defs, err)\n   call !netdefs('READ', defs, err)", 1))
mut("list.servers shows the full pin in the list", "listservers", "pin.text = defs<i,5>[1, 16] : '...'", "pin.text = defs<i,5>")
mut("list.servers shows the short pin for a named server", "listservers", "   end else\n            pin.text = defs<i,5>\n", "   end else\n            pin.text = defs<i,5>[1, 16] : '...'\n")
mut("list.servers forgets the date", "listservers", "if name # '' then crt sysmsg(11435, defs<i,8>)", "if name # '' then null")
mut("list.servers has no empty message", "listservers", "sysmsg(11433)", "sysmsg(11438)")
mut("list.servers forgets 'none'", "listservers", "sysmsg(11438)   ;* none", "''")
mut("!netdefs writes lines before checking them", "netdefs", rx(r"(         tmp = path : '\.new'\n)", r"         openseq tmp to tmp.f then null else null\n\1"))
mut("!netdefs accepts a bar inside a field", "netdefs", " or c = 124)", ")")
mut("!netdefs accepts a control character", "netdefs", "c < 32 or c > 126", "c > 126")
mut("!netdefs accepts a definition of 7 fields", "netdefs", "ok = (dcount(one, @vm) = NETDEFS.FIELDS)", "ok = (dcount(one, @vm) >= 7)")
mut("!netdefs writes the file in place", "netdefs", "tmp = path : '.new'", "tmp = path")
mut("!netdefs renames before it has written", "netdefs", rx(r"(         if not\(osrename\(tmp, path\)\) then)", r"         void osrename(tmp, path)\n\1"))
mut("!netdefs writes two ways", "netdefs", lambda t: t.replace("         closeseq tmp.f\n", "         writeseq 'x' to tmp.f else null\n         closeseq tmp.f\n", 1))
mut("!netdefs leaves the copy after a failed write", "netdefs", rx(r"if err # '' then\n\s*void ospath\(tmp, OS\$DELETE\)\n", "if err # '' then\n"))
mut("!netdefs never sets the umask", "netdefs", "         void umask(18)\n", "")
mut("!netdefs sets the umask after the copy is made", "netdefs", rx(r"(         void umask\(18\)\n)(         openseq tmp to tmp\.f then\n.*?\n         end\n)", r"\2\1", re.S))
mut("!netdefs does not put the umask back", "netdefs", "         void umask(old.umask)\n", "")
mut("!netdefs writes with umask 0", "netdefs", "void umask(18)", "void umask(0)")
mut("!netdefs READ asks for the administrator", "netdefs", lambda t: t.replace("      case mode = 'READ'\n", "      case mode = 'READ'\n         if not(kernel(K$ADMINISTRATOR, -1)) then err = 2001 ; return\n", 1))
mut("!netdefs READ keeps a mark byte", "netdefs", drop_line(r"convert char\(251\)"))
mut("!netdefs READ keeps the bar", "netdefs", drop_line(r"convert '\|' to @vm in line"))
mut("the definitions file is somewhere else", "netdefs", "$define NETDEFS.FILE   'netservers'", "$define NETDEFS.FILE   'netserver'")
mut("another program names the definitions file", "bp:cd", lambda t: t + "\n   openseq '/usr/local/sdsys/netservers' to nf else null\n")
mut("the warning about secrets is gone", "netdefs", "MUST NEVER HOLD A SECRET", "may hold what it likes")
# ---- G
mut("message 11411 is missing", "msg:11411", lambda t: None)
mut("message 11430 is empty", "msg:11430", lambda t: "")
mut("message 11425 takes two lines", "msg:11425", lambda t: t.rstrip("\n") + "\nsecond line\n")
mut("11420 is never used", "setserver", drop_line(r"display sysmsg\(11420"))
mut("11436 is never used", "netdefs", "err = 11436:@vm:i", "err = 11428:@vm:i")
mut("11411 is never printed by CREATE.ACCOUNT", "create_account", "crt sysmsg(11411,", "crt sysmsg(11409,")
mut("a verb prints a number that has no file", "listservers", "sysmsg(11433)", "sysmsg(11449)")
mut("message 11424 has a place the call does not fill", "msg:11424", lambda t: t.rstrip("\n") + " %4\n")
mut("11434 is called with three arguments", "listservers", "defs<i,4>:'/':defs<i,6>, pin.text:'  ':allowed)", "defs<i,4>:'/':defs<i,6>)")
mut("11411 loses its words", "msg:11411", lambda t: "Account %1 has gate %2\n")
mut("11423 stops asking", "msg:11423", lambda t: "Server %1 is already defined (%2)\n")
mut("11413 hints that it connects", "msg:11413", lambda t: t.replace("Nothing connects to the server yet", "It connects to the server", 1))
mut("11439 stops naming the word", "msg:11439", lambda t: t.replace("net-on", "net-add"))
mut("11412 stops being the usage line", "msg:11412", lambda t: "Use the server verb\n")


def run(srcs):
    return checks(srcs)


def main():
    srcs = load()
    if "--selftest" in sys.argv:
        base = run(srcs)
        bad = [i for i, ok, d in base if not ok]
        if bad:
            print("test-net-units: the unmutated source already fails: %s" % bad)
            return 2
        missed = 0
        for label, name, old, new in M:
            try:
                rows = checks(mutate(srcs, name, old, new))
            except KeyError as e:
                print("  [FAIL] mutant is not applicable: %s (%s)" % (label, e))
                missed += 1
                continue
            caught = [i for i, ok, d in rows if not ok]
            if caught:
                print("  [PASS] mutant caught: %s  <- %s" % (label, ", ".join(caught[:3])))
            else:
                print("  [FAIL] MUTANT NOT CAUGHT: %s" % label)
                missed += 1
        print("\ntest-net-units --selftest: %d mutants, %d missed" % (len(M), missed))
        return 1 if missed else 0
    rows = run(srcs)
    failed = 0
    for i, ok, d in rows:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", i, "" if ok or not d else "   <- " + d))
        failed += 0 if ok else 1
    print("\ntest-net-units: %d checks, %d failed" % (len(rows), failed))
    print("NOT MEASURED HERE: whether the gate answers, or whether a verb writes or refuses.  That is sandbox-net.py (a private SD).")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
