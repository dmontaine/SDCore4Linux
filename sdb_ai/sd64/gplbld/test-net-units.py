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

17 Oct 26 dm  S.65 slice 2a: set.server's fifth word may be CONNECT.  Section T reads the flow as ORDER - every field, the lock, the
read, the limit and the replace question before the one socket is opened; opened with SKT$TLS and a 5 second timeout; the hash read
and the socket closed before the key question is shown; the key question asked on EVERY connect (no.query is not consulted between
the connect and the question); nothing written on n, on a failed connect, on a failed handshake or on an empty hash; the audit words
pin=typed and pin=confirmed.  Section C3-C6 reads the C side: the hash is of the SubjectPublicKeyInfo (i2d_X509_PUBKEY and SHA-256, not
X509_digest, which is the certificate and changes at every renewal), SOCKET.INFO answers 64 lower case hex digits and a null string
without TLS, and the key number 11 is the same in both headers and unique.  P2, P3, G1-G5 were extended for the new messages
11440-11446 and the audit word.  What it cannot say is whether a handshake works or the hash is the right one: sandbox-net.py, section
"connect", against an independent openssl computation.

17 Oct 26 dm  S.65 slice 2b: the person's login on a server (set.netlogin, delete.netlogin, $netcred, SDEXT SD_FILE_PRIVATE).  Sections F (the
C private-file test: fail closed, lstat and not stat, the EFFECTIVE uid, no bit in 077, a regular file whose parent directory passes the
same test, the number 111 in both headers, SDEXT an internal-only intrinsic in BCOMP), R ($netcred: the path rule, SD_FILE_PRIVATE before
EVERY use, the file never holds the password, READ/WRITE/DELETE/EXISTS as ORDER, a strict shape for every value), U (set.netlogin: the
NET gate, the definition and the account list before anything is dialled, the pin tested before the first SCRAM packet, nothing written
on any failure, the password spent and cleared, no secret in a message or in the audit line), Y (delete.netlogin), V (the VOC entries,
in newvoc so EVERY account has them), H (messages 11450-11479) and E (the root agrees with sd-elevate netcred-dir and the sudoers
line).  B5 was extended: setnetlogin asks (never sets) K$NET.  WHAT THIS CANNOT SAY: that the exchange works against a server, that a
file written is mode 600, that a symlink is refused - sandbox-net.py, sections netcred and netlogin, with a fake server that speaks the
packet text of sdclient (gplbld/netfake.py).

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

C_FILES = ("keys.h", "sysseg.h", "op_kernel.c", "sd_tls.c", "sd_tls.h", "op_skt.c", "op_sdext.c")
MAIN_BP = ("login", "cproc", "apisrvr", "modifya", "createa", "create_account", "acc_os_info", "restorea",
           "netdefs", "setserver", "deleteserver", "listservers", "netcred", "setnetlogin", "deletenetlogin", "bcomp")
VERBS = (("set.server", "setserver", "$setserver"), ("delete.server", "deleteserver", "$deleteserver"),
         ("list.servers", "listservers", "$listservers"))
NL_VERBS = (("set.netlogin", "setnetlogin", "$setnetlogin"), ("delete.netlogin", "deletenetlogin", "$deletenetlogin"))   # slice 2b: in newvoc AND voc_template
MSG_FIRST, MSG_LAST = 11411, 11446      # 11411-11439 slice 1, 11440-11446 slice 2a (CONNECT); 11447-11449 are free
NL_MSG_FIRST, NL_MSG_LAST = 11450, 11479    # slice 2b: the person's login (the whole block is this slice's)
LINUX_BLOCK = (11000, 11999)
SH_FILES = ("installsdcore.sh", "sd-elevate", "sdcore.sudoers")      # shell-style comments (#)


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
    if name in SH_FILES:
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
    get("sd-elevate", os.path.join(HERE, "sd-elevate"))
    get("sdcore.sudoers", os.path.join(HERE, "sdcore.sudoers"))
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
    for word, _prog, _cat in NL_VERBS:
        get("voc:" + word, os.path.join(SDSYS, "voc_template", word))
        get("newvoc:" + word, os.path.join(SDSYS, "newvoc", word))
    srcs["newvoc.list"] = "\n".join(sorted(os.listdir(os.path.join(SDSYS, "newvoc"))))
    for n in list(range(MSG_FIRST, MSG_LAST + 1)) + list(range(NL_MSG_FIRST, NL_MSG_LAST + 1)):
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
    ck("B5 no program but LOGIN (1), CPROC (3), the API server (1) and set.netlogin (1, which only ASKS: K$NET, -1 - see U2) mentions K$NET",
       sites == {"login": 1, "cproc": 3, "apisrvr": 1, "setnetlogin": 1}, repr(sites))
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
       and ss_.count("if yn = '' and status() = ER$EOF then yn = 'N'") == 2, "")   # the replace question and, since slice 2a, the key question
    ck("S3 ...the lock is released straight after the write, whether or not it worked, and before the audit line",
       re.search(r"call !netdefs\('WRITE', defs, err\)\s*\n\s*gosub release\.lock\s*\n\s*if err # '' then", ss_) is not None
       and 0 <= first_write < at(ss_, "kernel(K$AUDIT, 'set.server name='"), "")
    ck("S4 ...the rules: name 1-16 of lower case and digits and a letter first; host 1-253 of letters, digits, dots, hyphens and colons, not "
       "starting with - or .; port 1-65535; account 1-32 of letters, digits and ._-; pin 64 hex; at most 10 servers",
       "len(name) < 1 or len(name) > 16" in ss_ and "index(lc.set, name[1, 1], 1) = 0" in ss_
       and "len(host) < 1 or len(host) > 253" in ss_ and "chk.set = lc.set:digits:'.-:'" in ss_ and "host[1, 1] = '-' or host[1, 1] = '.'" in ss_
       and "port matches '1N0N'" in ss_ and "port + 0 >= 1 and port + 0 <= 65535" in ss_
       and "len(account) < 1 or len(account) > 32" in ss_ and "chk.set = lc.set:upcase(lc.set):digits:'._-'" in ss_
       and "len(pin) # 64" in ss_ and ss_.count("chk.set = digits:'abcdef'") == 2 and re.search(r"\$define NET\.MAX\.SERVERS 10\b", ss_) is not None, "")
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
    def pin_lines(t):       # the lines that use the variable pin (pin.how, the audit word, and the routine's name connect.pin are not it)
        return [ln for ln in strip_strings(t).split("\n") if re.search(r"\bpin\b", re.sub(r"\b(?:pin\.how|connect\.pin)\b", "", ln))]
    leaks = [ln.strip() for ln in pin_lines(ss_) if re.search(r"\b(display|crt|print|stop|sysmsg|kernel)\b", ln)]
    ck("P2 the pin is never shown, printed or put on the audit trail by set.server (the audit line names the server, host, port, mode, "
       "whether it replaced and how the pin was obtained; the one hash that is shown, in CONNECT, is the variable spki - T7)", not leaks, repr(leaks))
    ck("P3 ...it goes into the definition line and nowhere else: its only uses are the lower-casing, the CONNECT word, the form test, the hash "
       "confirmed by SDSYS and the line that builds the definition (8 lines)",
       len(pin_lines(ss_)) == 8
       and re.search(r"one = name:@vm:host:@vm:port:@vm:account:@vm:pin:@vm:mode:@vm:acc\.clean:@vm:created", ss_) is not None
       and "'set.server name=' : name : ' host=' : host : ' port=' : port : ' mode=' : mode : ' replaced=' : rep.word : ' pin=' : pin.how)" in ss_, repr(len(pin_lines(ss_))))

    # ---- T. set.server ... connect (S.65 slice 2a): the order of the flow --------------------------------------------------------
    cp_i = ss_.find("\nconnect.pin:")
    cp_j = ss_.find("\nrelease.lock:", cp_i) if cp_i >= 0 else -1
    cpb = ss_[cp_i:cp_j] if 0 <= cp_i < cp_j else ""         # the routine
    mainb = ss_[:cp_i] if cp_i >= 0 else ss_                  # everything before it
    m_call = re.search(r"if connect\.mode then\s*\n\s*gosub connect\.pin[^\n]*\n\s*pin\.how = 'confirmed'\s*\n\s*end", ss_)
    p_call = m_call.start() if m_call else -1
    sop = strip_strings(ss_)
    ck("T1 the fifth word is CONNECT in any case (the pin is lower-cased first), it empties pin, and the typed-pin form test is skipped for it",
       ordered(ss_, "pin = downcase(field(words, ' ', 6))", "if pin = 'connect' then", "connect.mode = @true", "pin = ''")
       and ordered(ss_, "if not(connect.mode) then", "chk.text = pin", "len(pin) # 64"), "")
    ck("T2 nothing is dialled for a definition that would be refused: every field (11414-11421), the stop on 'bad', the lock, the read, the limit of "
       "10 and the replace question all come BEFORE the one gosub of connect.pin, which is guarded by connect.mode and followed by the write",
       all(0 <= f < gate for f in fld) and p_call >= 0 and ss_.count("gosub connect.pin") == 1
       and 0 <= gate < at(ss_, "readu lock.rec") < at(ss_, "call !netdefs('READ'") < at(ss_, "sysmsg(11422") < at(ss_, "sysmsg(11423") < p_call
       and p_call < at(ss_, "call !netdefs('WRITE'") and at(ss_, "pin.how = 'confirmed'") < at(ss_, "call !netdefs('WRITE'"),
       repr((gate, p_call)))
    ck("T3 the socket is opened in the routine only (the typed pin makes no connection), once, with SKT$BLOCKING + SKT$TLS and the 5 second timeout, "
       "and the status and the operating system error are read at once",
       ss_.count("open.socket(") == 1 and cpb.count("open.socket(") == 1
       and re.search(r"skt = open\.socket\(host, port, SKT\$BLOCKING \+ SKT\$TLS, NET\.CONNECT\.SECS\)\s*\n\s*st = status\(\)\s*\n\s*oserr = os\.error\(\)", cpb) is not None
       and re.search(r"\$define NET\.CONNECT\.SECS 5\b", ss_) is not None and re.search(r"^\$include keys\.h", ss_, re.M) is not None, "")
    ck("T4 a handshake only: the hash is read, the socket is closed (once), and all of that BEFORE anything is shown or asked; nothing is read from "
       "or written to the socket",
       ordered(cpb, "open.socket(", "if st # 0 then", "socket.info(skt, SKT$INFO.TLS.SPKI)", "close.socket skt", "sysmsg(11440", "display spki", "sysmsg(11441", "sysmsg(11442", "input yn")
       and ss_.count("close.socket") == 1 and not re.search(r"\b(?:write|read|select)\.socket\b|set\.socket\.mode|\bsend\b|\brecv\b", sop), "")
    ck("T5 THE KEY QUESTION IS ALWAYS ASKED: no.query is not mentioned in the routine, the only test of it is the replace question (before the connect), "
       "and the question is a loop that ends on y or n, an empty answer and input that ends being n",
       "no.query" not in cpb and len([ln for ln in sop.split("\n") if "no.query" in ln and re.search(r"\bif\b", ln)]) == 1
       and "if found # 0 and not(no.query) then" in ss_ and at(ss_, "if found # 0 and not(no.query) then") < p_call
       and ss_[p_call:at(ss_, "call !netdefs('WRITE'")].count("no.query") == 0
       and re.search(r"display sysmsg\(11442\) :", cpb) is not None
       and ordered(cpb, "loop", "display sysmsg(11442)", "input yn", "if yn = '' and status() = ER$EOF then yn = 'N'", "if yn = '' then yn = 'N'", "until yn = 'Y' or yn = 'N'", "repeat"), "")
    ck("T6 nothing is written on n, on a connection that fails, on a handshake that fails or on an empty hash: each gives the lock back and STOPS "
       "(n with return code 0), and the pin is taken from the hash only after the n has stopped",
       re.search(r"if yn = 'N' then\s*\n\s*gosub release\.lock\s*\n\s*@system\.return\.code = 0\s*\n\s*stop sysmsg\(11443, name\)\s*\n\s*end\s*\n\s*pin = spki\s*\n\s*return", cpb) is not None
       and re.search(r"gosub release\.lock\s*\n\s*@system\.return\.code = -ER\$FAILED\s*\n\s*if st = ER\$CONNECT and oserr = 0 then stop sysmsg\(11445, host, port\)\s*\n\s*stop sysmsg\(11444, host, port, st, oserr\)", cpb) is not None
       and re.search(r"gosub release\.lock\s*\n\s*@system\.return\.code = -ER\$FAILED\s*\n\s*stop sysmsg\(11446, host, port\)", cpb) is not None
       and cpb.count("pin = spki") == 1 and "call !netdefs" not in cpb and ss_.count("call !netdefs('WRITE'") == 1, "")
    ck("T7 the hash is lower case and trimmed, must be 64 hexadecimal digits before it is shown (an empty or damaged one is 11446), and the failure that "
       "is a handshake (status ER$CONNECT with os error 0, 11445) is told from the one that is not (11444)",
       ordered(cpb, "spki = downcase(trim(socket.info(skt, SKT$INFO.TLS.SPKI)))", "close.socket skt", "chk.set = digits:'abcdef'", "len(spki) # 64 or not(chk.ok)", "sysmsg(11446", "sysmsg(11440")
       and ordered(cpb, "sysmsg(11445", "sysmsg(11444") and "display spki" in cpb and ss_.count("display spki") == 1, "")
    ck("T8 the audit line says how the pin was obtained, in lower case: pin.how starts as typed, is confirmed only after connect.pin has returned, "
       "and is in the one audit line, after the write",
       ss_.count("pin.how = '") == 2 and ordered(ss_, "pin.how = 'typed'", "gosub connect.pin", "pin.how = 'confirmed'", "call !netdefs('WRITE'", "kernel(K$AUDIT, 'set.server name='")
       and ss_.count("pin=") == 1 and "' pin=' : pin.how)" in ss_ and ss_.count("kernel(K$AUDIT") == 1, "")

    # ---- C3-C6. the C side of the hash --------------------------------------------------------------------------------------
    tc, th, sk, kh, sy = c["sd_tls.c"], c["sd_tls.h"], c["op_skt.c"], c["keys.h"], c["syscom/keys.h"]
    i = tc.find("int sd_tls_client_peer_spki_sha256(")
    fb = tc[i:tc.find("\n}\n", i)] if i >= 0 else ""
    ck("C3 the hash is of the SubjectPublicKeyInfo - i2d_X509_PUBKEY of X509_get_X509_PUBKEY, then SHA-256 of those bytes, all 32 required - and NOT the "
       "certificate (X509_digest and i2d_X509 would change at every renewal)",
       fb != "" and tc.count("sd_tls_client_peer_spki_sha256(SD_TLS_CLIENT") == 1
       and "i2d_X509_PUBKEY(X509_get_X509_PUBKEY(cert), &der)" in fb and "EVP_Digest(" in fb and "EVP_sha256()" in fb and "n == 32" in fb
       and "X509_digest" not in fb and not re.search(r"i2d_X509\s*\(", fb), "")
    ck("C3b ...it asks for the certificate the server PRESENTED (SSL_get1_peer_certificate), answers false with none, and frees the certificate and the DER bytes",
       "SSL_get1_peer_certificate(c->ssl)" in fb and "if (cert == NULL)" in fb and "X509_free(cert)" in fb and "OPENSSL_free(der)" in fb
       and ordered(fb, "cert == NULL", "i2d_X509_PUBKEY", "EVP_Digest(", "OPENSSL_free(der)", "X509_free(cert)", "return ok"), "")
    ck("C4 sd_tls.h declares it with the same signature (SD_TLS_CLIENT*, 32 bytes out)",
       "int sd_tls_client_peer_spki_sha256(SD_TLS_CLIENT* c, unsigned char* out);" in th, "")
    i = sk.find("case SKT_INFO_TLS_SPKI:")
    cb = sk[i:sk.find("} break;", i)] if i >= 0 else ""
    ck("C5 SOCKET.INFO(.., SKT$INFO.TLS.SPKI) answers 64 lower case hex digits for a TLS socket and the NULL string for any other (the result is set to "
       "empty first and filled only when the socket has TLS and the hash was made)",
       cb != "" and sk.count("case SKT_INFO_TLS_SPKI:") == 1 and "char hex[65];" in cb and "unsigned char spki[32];" in cb
       and ordered(cb, "hex[0] = '\\0';", "sockvar->tls != NULL", "sd_tls_client_peer_spki_sha256((SD_TLS_CLIENT*)sockvar->tls, spki)", "i < 32", '"%02x"', "k_put_c_string(hex, &result_descr)")
       and "%02X" not in cb, "")
    spki_keys = {m.group(1): m.group(2) for m in re.finditer(r"#define\s+(SKT_INFO_[A-Z0-9_]+)\s+(\d+)", kh)}
    spki_bas = {m.group(1): m.group(2) for m in re.finditer(r"\$define\s+(SKT\$INFO\.[A-Z0-9.]+)\s+(\d+)", sy)}
    ck("C6 the key number is 11 in both headers and no other SKT_INFO / SKT$INFO name uses it",
       spki_keys.get("SKT_INFO_TLS_SPKI") == "11" and spki_bas.get("SKT$INFO.TLS.SPKI") == "11"
       and [k for k, v in spki_keys.items() if v == "11"] == ["SKT_INFO_TLS_SPKI"] and [k for k, v in spki_bas.items() if v == "11"] == ["SKT$INFO.TLS.SPKI"],
       repr((spki_keys.get("SKT_INFO_TLS_SPKI"), spki_bas.get("SKT$INFO.TLS.SPKI"))))

    # ---- G. messages ----------------------------------------------------------------------------------------------------------
    texts = {n: srcs["msg:%d" % n] for n in range(MSG_FIRST, MSG_LAST + 1)}
    ck("G1 messages 11411 to 11446 all exist, each one line of text, and inside the Linux block 11000-11999 (not the Windows block)",
       all(t is not None and t.strip() != "" and "\n" not in t.rstrip("\n") for t in texts.values())
       and LINUX_BLOCK[0] <= MSG_FIRST and MSG_LAST <= LINUX_BLOCK[1], repr([n for n, t in texts.items() if not t]))
    verb_code = nd + "\n" + ss_ + "\n" + ds + "\n" + ls
    used = {int(x) for x in re.findall(r"\b(114[1-4]\d)\b", verb_code)}
    ck("G2 every message from 11412 to 11446 is used by the verbs or !netdefs (11447-11449 are free), and 11411 by MODIFY.ACCOUNT and CREATE.ACCOUNT",
       set(range(11412, MSG_LAST + 1)) <= used and not (used & {11447, 11448, 11449}) and "11411" in mo and "11411" in ca2 and 11411 not in used,
       repr(sorted(set(range(11412, MSG_LAST + 1)) - used)))
    literal = {n for n, _a in sysmsg_calls(verb_code + "\n" + mo + "\n" + ca2) if 11411 <= n <= MSG_LAST}
    reused = {n for n, _a in sysmsg_calls(verb_code)} | set(int(x) for x in re.findall(r"\berr = (\d{4,5})", verb_code))
    ck("G3 every number the verbs print exists as a message file (11412-11446 and the reused 2001, 2018, 6000)",
       all(srcs.get("msg:%d" % n) for n in reused if n in (2001, 2018, 6000) or 11411 <= n <= MSG_LAST)
       and all(n in (2001, 2018, 6000) or 11411 <= n <= MSG_LAST for n in reused), repr(sorted(reused)))
    short = []
    for n, args in sysmsg_calls(verb_code + "\n" + mo + "\n" + ca2):
        t = srcs.get("msg:%d" % n)
        if t is None or not (11411 <= n <= MSG_LAST):
            continue
        top = max([int(x) for x in re.findall(r"%(\d)", t)] or [0])
        if len(args) != top:
            short.append((n, len(args), top))
    ck("G4 each call of sysmsg gives as many arguments as its message has %n places", not short and literal, repr(short))
    t = lambda n: texts.get(n) or ""
    ck("G5 the wording the users and the verbs rely on: 11411 'Account %1 has NET %2'; 11423 asks 'Replace it (y/<n>)?'; 11442 asks 'Trust this key (y/<n>)?'; "
       "11413 says no.query never skips the key question; 11439 names net-on; 11412 is the usage line and shows {pin | connect}; "
       "11440 says a handshake only, with the host and port; 11443 and 11444-11446 say nothing was written",
       t(11411).strip() == "Account %1 has NET %2" and t(11423).strip().endswith("Replace it (y/<n>)?") and t(11442).strip().endswith("Trust this key (y/<n>)?")
       and "no.query never skips" in t(11413) and "net-on" in t(11439)
       and t(11412).startswith("Usage: set.server") and "{pin | connect}" in t(11412)
       and "%1:%2" in t(11440) and "handshake only" in t(11440)
       and all("Nothing was written" in t(n) or "nothing was written" in t(n).lower() for n in (11443, 11444, 11445, 11446)), "")
    checks_2b(srcs, c, ck)
    return rows


SECRETS = r"\b(pw|client\.key|srvr\.key|salted|proof|stored\.key|expect\.v|auth\.msg|client\.sig|rec)\b"      # the names set.netlogin holds a secret in


def case_body(t, label):
    """The text of one action of $netcred: from  case act = 'LABEL'  to the next case or the end of the block."""
    i = t.find("case act = '%s'" % label)
    if i < 0:
        return ""
    ends = [x for x in (t.find("\n      case act =", i + 5), t.find("\n   end case", i)) if x > 0]
    return t[i:min(ends)] if ends else t[i:]


def routine_body(t, label):
    """A BASIC internal subroutine: from  label:  to the next line that starts a label or the final end."""
    m = re.search(r"^%s:\s*$" % re.escape(label), t, re.M)
    if not m:
        return ""
    n = re.search(r"^[a-z][\w.$]*:\s*$|^end\s*$", t[m.end():], re.M)
    return t[m.start():m.end() + n.start()] if n else t[m.start():]


def fail_places(t):
    """(message number, how many fail.aK it sets) for every  fail.num = N ; fail.a1 = .. ; fail.a2 = ..  line."""
    out = []
    for m in re.finditer(r"fail\.num = (\d+)([^\n]*)", t):
        out.append((int(m.group(1)), len(re.findall(r"fail\.a\d = ", m.group(2)))))
    return out


def err_places(t):
    """(message number, how many arguments it gives) for every  err = N:@vm:arg:@vm:arg  statement of $netcred."""
    out = []
    for m in re.finditer(r"\berr = (\d{4,5})([^\n]*)", t):
        out.append((int(m.group(1)), m.group(2).count(":@vm:")))
    return out


def checks_2b(srcs, c, ck):
    """S.65 slice 2b: the person's login on a server."""
    kh, sy, ex_ = c["keys.h"], c["syscom/keys.h"], c["op_sdext.c"]
    nc, sn, dn, bc = c["bp:netcred"], c["bp:setnetlogin"], c["bp:deletenetlogin"], c["bp:bcomp"]

    # ---- F. SD_FILE_PRIVATE: the C test -------------------------------------------------------------------------------------------
    sd_c = {m.group(1): int(m.group(2)) for m in re.finditer(r"#define\s+(SD_[A-Za-z0-9_]+)\s+(\d+)\b", kh)}
    sd_b = {m.group(1): int(m.group(2)) for m in re.finditer(r"\$define\s+(SD_[A-Za-z0-9_]+)\s+(\d+)\b", sy)}
    both = {k for k in sd_c if k in sd_b and 100 <= sd_c[k] <= 127}
    ck("F1 SD_FILE_PRIVATE is 111 in gplsrc/keys.h and in syscom/keys.h, no other SD_ name uses 111 in either, and every SDEXT function number the two headers "
       "share (100-127) is the same in both",
       sd_c.get("SD_FILE_PRIVATE") == 111 and sd_b.get("SD_FILE_PRIVATE") == 111
       and [k for k, v in sd_c.items() if v == 111] == ["SD_FILE_PRIVATE"] and [k for k, v in sd_b.items() if v == 111] == ["SD_FILE_PRIVATE"]
       and all(sd_c[k] == sd_b[k] for k in both) and "SD_FILE_PRIVATE" in both, repr((sd_c.get("SD_FILE_PRIVATE"), sd_b.get("SD_FILE_PRIVATE"))))
    i = ex_.find("case SD_FILE_PRIVATE:")
    cb = ex_[i:ex_.find("break;", i)] if i >= 0 else ""
    ck("F2 the SDEXT case answers the text 0 unless the C test says 1: the answer is set to '0' first, '1' is put in only inside "
       "`if (file_private_check(...))` for the word FILE (want_dir 0) and for the word DIR (want_dir 1), a wrong argument count is not 1, and "
       "exactly the text '0' or '1' is returned",
       ex_.count("case SD_FILE_PRIVATE:") == 1 and cb != "" and ordered(cb, "answer[0] = '0';", "argCnt != 2", "SD_EXT_ARG_CNT", "k_put_c_string(answer, e_stack)")
       and cb.count("answer[0] = '1'") == 2
       and re.search(r'strcmp\(SDMEArgArray\[1\], "FILE"\) == 0\)\s*\{\s*if \(file_private_check\(SDMEArgArray\[0\], 0\)\)\s*answer\[0\] = \'1\';', cb) is not None
       and re.search(r'strcmp\(SDMEArgArray\[1\], "DIR"\) == 0\)\s*\{\s*if \(file_private_check\(SDMEArgArray\[0\], 1\)\)\s*answer\[0\] = \'1\';', cb) is not None
       and re.search(r"if \(argCnt != 2\) \{\s*process\.status = SD_EXT_ARG_CNT;\s*\} else if", cb) is not None, "")
    j = ex_.find("Private int file_private_check(const char* path, int want_dir) {")
    fb2 = ex_[j:ex_.find("\n}\n", j) + 3] if j >= 0 else ""          # the function, to its closing brace
    ck("F3 file_private_check is fail-closed: a path that is not absolute or is PATH_MAX or longer is 0, lstat (NOT stat, which follows a link) failing is 0, "
       "an owner that is not geteuid() (NOT getuid) is 0, any bit in 077 is 0, and no `return 1;` stands anywhere in it",
       fb2 != "" and ordered(fb2, "path == NULL || path[0] != '/'", "return 0;", "len >= sizeof(parent)", "return 0;", "lstat(path, &st) != 0", "return 0;",
                             "st.st_uid != geteuid()", "return 0;", "(st.st_mode & 077) != 0", "return 0;")
       and not re.search(r"(?<![l\w])stat\s*\(", fb2) and "getuid" not in fb2 and not re.search(r"return\s+1\s*;", fb2) and "access(" not in fb2
       and re.search(r"if \(lstat\(path, &st\) != 0\)\s*return 0;", fb2) is not None and re.search(r"if \(st\.st_uid != geteuid\(\)\)\s*return 0;", fb2) is not None
       and re.search(r"if \(\(st\.st_mode & 077\) != 0\)\s*return 0;", fb2) is not None
       and re.search(r"if \(path == NULL \|\| path\[0\] != '/'\)\s*return 0;", fb2) is not None and re.search(r"if \(len >= sizeof\(parent\)\)\s*return 0;", fb2) is not None, "")
    ck("F4 ...a directory test is S_ISDIR of the lstat result (a link to a directory is not one); a file test is S_ISREG of it, and then the PARENT directory "
       "(everything before the last slash, '/' for a file in the root) must pass the directory test, which is the last thing and the answer",
       ordered(fb2, "if (want_dir)", "return S_ISDIR(st.st_mode) ? 1 : 0;", "!S_ISREG(st.st_mode)", "return 0;", "memcpy(parent, path, len + 1)", "strrchr(parent, '/')",
               "return file_private_check(parent, 1);")
       and re.search(r"return file_private_check\(parent, 1\);\s*\}\s*$", fb2) is not None, "")
    sdext_calls = {n[3:]: re.findall(r"SDEXT\([^\n]*SD_FILE_PRIVATE\)[^\n]*", t) for n, t in c.items() if n.startswith("bp:") and "SD_FILE_PRIVATE" in t}
    ck("F5 only $netcred (5 calls: the directory, and the file for EXISTS, READ, the new file and DELETE) and set.netlogin (1: the directory) call it, each with "
       "@TRUE and a FILE or DIR word, each compared with the text '1'",
       set(sdext_calls) == {"netcred", "setnetlogin"} and len(sdext_calls.get("netcred", [])) == 5 and len(sdext_calls.get("setnetlogin", [])) == 1
       and all(re.search(r"SDEXT\(\w[\w.]* : @FM : '(?:FILE|DIR)', @TRUE, SD_FILE_PRIVATE\) (?:#|=) '1'", x) for v in sdext_calls.values() for x in v), repr(sdext_calls))
    ck("F6 SDEXT is an INTERNAL intrinsic in BCOMP (int.intrinsics), so a user program cannot call SD_FILE_PRIVATE, or SD_PBKDF2, or any of its neighbours",
       'int.intrinsics<-1> = "SDEXT"' in bc and re.search(r'(?<!int\.)intrinsics<-1> = "SDEXT"', bc) is None, "")

    # ---- R. $netcred -------------------------------------------------------------------------------------------------------------
    ck("R1 $netcred is $internal, `subroutine netcred(action, server, record, pin, err)`, catalogued once as $netcred, and nothing else in gpl.bp takes the name",
       nc.lstrip().startswith("$internal") or "\n$internal\n" in nc, "")
    ck("R1b ...(the signature, the catalogue name, and uniqueness)",
       "subroutine netcred(action, server, record, pin, err)" in nc and "$catalog $netcred" in nc
       and len([n for n, t in c.items() if n.startswith("bp:") and "$catalog $netcred\n" in t + "\n"]) == 1 and "$internal" in nc, "")
    ck("R2 THE PATH RULE: /var/lib/sd-net is defined once (NETCRED.ROOT), the directory is that root, a slash and the Linux user, the file is the directory, a slash and "
       "the server name, the copy is the file and '.new'; the Linux user is kernel(K$USERNAME, 0) and nothing else (no @logname, no @who, no env()); no other string "
       "in the program names the directory",
       re.search(r"\$define NETCRED\.ROOT\s+'/var/lib/sd-net'", nc) is not None and nc.count("sd-net") == 1
       and len(re.findall(r"^   cred\.dir = NETCRED\.ROOT : '/' : lu\s*$", nc, re.M)) == 1 and len(re.findall(r"^   path = cred\.dir : '/' : server\s*$", nc, re.M)) == 1
       and len(re.findall(r"^   tmp = path : '\.new'\s*$", nc, re.M)) == 1
       and nc.count("kernel(K$USERNAME, 0)") == 1 and not re.search(r"@logname|@who|@user|\benv\(", nc), "")
    ck("R2b ...the server name is validated (a lower case letter first, 1-16 of lower case letters and digits: 11452) and the Linux user is refused when it is empty, "
       "root, sdsys, too long or holds a character outside letters, digits and ._- (11458), BOTH before the first look at the disk",
       ordered(nc, "len(server) < 1 or len(server) > 16", "index(lc.set, server[1, 1], 1) = 0", "err = 11452", "lu = kernel(K$USERNAME, 0)",
               "lu = '' or lu = 'root' or lu = 'sdsys'", "len(lu) > MAX.USERNAME.LEN", "err = 11458", "cred.dir = NETCRED.ROOT", "ospath(cred.dir, OS$EXISTS)")
       and "chk.text = server ; chk.set = lc.set:digits ; gosub check.chars" in nc and "chk.text = lu ; chk.set = os.chars ; gosub check.chars" in nc
       and "if not(dir.there) or SDEXT(cred.dir : @FM : 'DIR', @TRUE, SD_FILE_PRIVATE) # '1' then" in nc, "")
    rd, wr, dl, xs = case_body(nc, "READ"), case_body(nc, "WRITE"), case_body(nc, "DELETE"), case_body(nc, "EXISTS")
    ck("R3 THE PRIVATE-FILE TEST COMES FIRST, EVERY TIME: the directory is tested (and a directory that is missing or fails is 11454) before the action is looked at; "
       "READ tests the file before it opens it; DELETE tests it before it removes it; EXISTS tests it before it says 1; WRITE tests the new copy after it is written and "
       "BEFORE it is renamed over the login",
       ordered(nc, "dir.there = ospath(cred.dir, OS$EXISTS)", "SDEXT(cred.dir : @FM : 'DIR', @TRUE, SD_FILE_PRIVATE) # '1'", "err = 11454", "begin case")
       and ordered(rd, "SDEXT(path : @FM : 'FILE', @TRUE, SD_FILE_PRIVATE) # '1'", "err = 11454", "openseq path to f")
       and ordered(dl, "SDEXT(path : @FM : 'FILE', @TRUE, SD_FILE_PRIVATE) # '1'", "err = 11454", "ospath(path, OS$DELETE)")
       and ordered(xs, "SDEXT(path : @FM : 'FILE', @TRUE, SD_FILE_PRIVATE) = '1'", "record = 1")
       and ordered(wr, "openseq tmp to tmp.f", "writeseq line to tmp.f", "SDEXT(tmp : @FM : 'FILE', @TRUE, SD_FILE_PRIVATE) # '1'", "err = 11454", "osrename(tmp, path)"),
       repr([bool(rd), bool(wr), bool(dl), bool(xs)]))
    ck("R3b ...the file is opened in exactly two places (READ, and the new copy in WRITE), renamed in one, written in one, and deleted in three (the old copy before "
       "a write, the copy after a failure, the login by DELETE after its test)",
       nc.count("openseq ") == 2 and nc.count("osrename(") == 1 and nc.count("writeseq ") == 1 and nc.count("OS$DELETE") == 3
       and rd.count("openseq path to f") == 1, repr((nc.count("openseq "), nc.count("osrename("), nc.count("writeseq "), nc.count("OS$DELETE"))))
    ck("R4 THE FILE NEVER HOLDS THE PASSWORD: there is no password parameter and no word password, passwd or pw in the code; the only thing written is `line`, built "
       "from the literal v1 and the seven values one<1> to one<7>; WRITE has no other way to put text in the file",
       not re.search(r"\b(password|passwd|pw)\b", nc, re.I) and "line = 'v1'" in nc and "line := '|' : one<i>" in nc and nc.count("writeseq line to tmp.f") == 1
       and re.search(r"for i = 1 to 7\s*\n\s*line := '\|' : one<i>\s*\n\s*next i", wr) is not None
       and "subroutine netcred(action, server, record, pin, err)" in nc, "")
    ck("R5 READ in order: the pin argument must be 64 lower case hex digits (11459) before the disk is touched; no file is 11453; an untrusted one 11454; the line is read "
       "and the file closed; a mark byte or the wrong layout (v1 and 8 fields) is 11456; every value has its shape (check.record) BEFORE the stored pin is compared with "
       "the definition's (11455, and record stays null); the record is handed back last",
       ordered(rd, "record = ''", "gosub check.pin", "err = 11459", "ospath(path, OS$EXISTS)", "err = 11453", "SD_FILE_PRIVATE", "openseq path to f", "readseq line from f", "closeseq f",
               "convert(marks, '', line)", "err = 11456", "dcount(line, @fm) # 8 or line<1> # 'v1'", "err = 11456", "gosub check.record", "err = 11456",
               "if one<6> # pin then", "err = 11455", "record = one") and rd.count("record = one") == 1 and rd.count("gosub check.record") == 1, "")
    ck("R6 WRITE in order: the pin argument first (11459), the pin ARGUMENT is what is stored (attribute 6 of the record is overwritten), every value checked (11456) before "
       "the first byte is written; umask 077 (63) while the copy is made and put back straight after, before anything is written; the copy is tested; the rename is last, "
       "only when there is no error; a failed write deletes the copy",
       ordered(wr, "gosub check.pin", "err = 11459", "one = record", "one<6> = pin", "gosub check.record", "err = 11456", "line = 'v1'", "void umask(NETCRED.UMASK)",
               "openseq tmp to tmp.f", "void umask(old.umask)", "writeseq line to tmp.f", "closeseq tmp.f", "SD_FILE_PRIVATE", "if err = '' then\n            if not(osrename(tmp, path))")
       and re.search(r"if err # '' then void ospath\(tmp, OS\$DELETE\)", wr) is not None and re.search(r"\$define NETCRED\.UMASK\s+63\b", nc) is not None
       and "old.umask = umask(-1)" in wr, "")
    ck("R6b ...an old copy left behind is removed first (and a failure to remove it is 11457), and a failure to create the copy is 11457",
       ordered(wr, "if ospath(tmp, OS$EXISTS) then", "ospath(tmp, OS$DELETE)", "err = 11457", "old.umask = umask(-1)", "if not(made) then", "err = 11457"), "")
    ck("R7 check.record gives every value its shape: remote user of letters, digits and ._- up to MAX.USERNAME.LEN; iterations a whole number inside SCRAM$MIN.ITER and "
       "SCRAM$MAX.ITER; salt and both keys base64 of 4 to 128 characters; the pin 64 lower case hex digits; created yyyy-mm-dd",
       ordered(nc, "check.record:", "chk.set = os.chars", "MAX.USERNAME.LEN", "what matches '1N0N'", "SCRAM$MIN.ITER", "SCRAM$MAX.ITER", "chk.set = b64", "len(what) < 4 or len(what) > 128 or not(chk.ok)",
               "chk.set = hex.set", "len(what) # 64", "'4N\"-\"2N\"-\"2N'") and "b64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':lc.set:digits:'+/='" in nc
       and "hex.set = digits:'abcdef'" in nc and "os.chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':lc.set:digits:'._-'" in nc, "")
    ck("R8 DELETE: no login is 11453; EXISTS: a missing directory or a missing file answers 0 with no error, a file that is there and not trusted is 11454 with 0; an unknown "
       "action is 2018 before anything else",
       ordered(dl, "err = 11453", "SD_FILE_PRIVATE", "err = 11454", "ospath(path, OS$DELETE)", "err = 11457")
       and ordered(nc, "if act # 'READ' and act # 'WRITE' and act # 'DELETE' and act # 'EXISTS' then", "err = 2018", "chk.text = server")
       and "if act = 'EXISTS' then return" in nc and "if act = 'EXISTS' then record = 0" in nc, "")

    # ---- U. set.netlogin ---------------------------------------------------------------------------------------------------------
    ck("U1 set.netlogin is $internal, `program set.netlogin`, catalogued once as $setnetlogin",
       "\n$internal\nprogram set.netlogin" in "\n" + sn and "$catalog $setnetlogin" in sn
       and len([n for n, t in c.items() if n.startswith("bp:") and "$catalog $setnetlogin\n" in t + "\n"]) == 1, "")
    ck("U2 EVERY LOCAL CHECK COMES BEFORE ANY PROMPT OR CONNECTION, in this order: the usage (11450), the server name (11452), the NET gate or the administrator (11460), the "
       "definition (11430, 11436), the account list (11461), the Linux user (11462), sd-elevate netcred-dir (11463), the directory test; and then the two prompts, then the one socket",
       ordered(sn, "stop sysmsg(11450", "stop sysmsg(11452", "is.admin = kernel(K$ADMINISTRATOR, -1)", "stop sysmsg(11460", "call !netdefs('READ'", "stop sysmsg(11430",
               "stop sysmsg(11436", "stop sysmsg(11461", "stop sysmsg(11462", "os.execute elev", "stop sysmsg(11463", "SD_FILE_PRIVATE", "stop sysmsg(11463", "input ru",
               "stop sysmsg(11467", "input pw HIDDEN", "stop sysmsg(11468", "open.socket(")
       and "len(name) < 1 or len(name) > 16 or not(chk.ok) or index(lc.set, name[1, 1], 1) = 0" in sn and sn.count("input ru") == 1 and sn.count("input pw HIDDEN") == 1
       and "if dcount(words, ' ') # 2 then" in sn and "acc = downcase(@who)" in sn and "if len(pin) # 64 or not(chk.ok) then" in sn
       and "if ru = '' or len(ru) > MAX.USERNAME.LEN or not(chk.ok) then" in sn
       and re.search(r"if pw = '' then\s*\n\s*@system\.return\.code = -ER\$ARGS\s*\n\s*stop sysmsg\(11468\)", sn) is not None
       and re.search(r"if not\(is\.admin\) and not\(kernel\(K\$NET, -1\)\) then", sn) is not None and "kernel(K$NET, -1)" in sn and sn.count("kernel(K$NET") == 1
       and "index(',':downcase(defs<found,7>):',', ',':acc:',', 1) = 0" in sn and re.search(r"if not\(is\.admin\) then\s*\n\s*if index\(", sn) is not None, "")
    ck("U3 the Linux user is kernel(K$USERNAME, 0) and nothing else, sdsys, root and an empty one are refused before sd-elevate is run, the helper is run as `sudo -n` "
       "(no password prompt in an SD session), its success line must be `netcred-dir: <path>` and the path must end in /<the Linux user> and pass SD_FILE_PRIVATE as a directory",
       ordered(sn, "lu = kernel(K$USERNAME, 0)", "lu = '' or lu = 'sdsys' or lu = 'root'", "elev = ACCOS$ELEVATE", "'sudo -n '", "os.execute elev : ' netcred-dir 2>&1' capturing out",
               "out<i>[1, 13] = 'netcred-dir: '", "tail = '/' : lu", "cred.path[len(cred.path) - len(tail) + 1, len(tail)] # tail", "SDEXT(cred.path : @FM : 'DIR', @TRUE, SD_FILE_PRIVATE) # '1'")
       and sn.count("os.execute") == 1 and sn.count("kernel(K$USERNAME") == 1 and not re.search(r"@logname", sn), "")
    ck("U4 ONE connection, TLS, to the host and port of the DEFINITION, and the key it presents is tested BEFORE a byte is sent or read: open.socket (once) -> the hash "
       "(socket.info .. SKT$INFO.TLS.SPKI, once, lower case) must be 64 hex digits (11479) -> `spki # pin` gives 11471 through give.up -> only then the Ack read and the first packet",
       sn.count("open.socket(") == 1 and sn.count("socket.info(skt, SKT$INFO.TLS.SPKI)") == 1 and "open.socket(host, port, SKT$BLOCKING + SKT$TLS, NET.CONNECT.SECS)" in sn
       and ordered(sn, "open.socket(", "spki = downcase(trim(socket.info(skt, SKT$INFO.TLS.SPKI)))", "fail.num = 11479", "if spki # pin then", "fail.num = 11471", "gosub give.up",
                   "read.socket(skt, 1, SKT$BLOCKING, NET.READ.MS)", "ptype = SrvrScramFirst")
       and re.search(r"if spki # pin then\s*\n\s*fail\.num = 11471[^\n]*\n\s*gosub give\.up\s*\n\s*end", sn) is not None
       and "if len(spki) # 64 or not(chk.ok) then" in sn
       and "pin = downcase(defs<found,5>)" in sn and "host = defs<found,2>" in sn and "port = defs<found,3>" in sn, "")
    reads = re.findall(r"(?:read|write)\.socket\([^\n]*\)", sn)
    ck("U4b ...every read and every write of the socket has a timeout (NET.READ.MS), write.socket stands once and only in send.packet, which every packet goes through "
       "and which comes after the pin test in the flow",
       len(reads) == 4 and all("NET.READ.MS)" in x for x in reads) and sn.count("write.socket(") == 1 and sn.count("gosub send.packet") == 2
       and ordered(sn, "if spki # pin then", "gosub send.packet", "gosub send.packet") and "write.socket(" in routine_body(sn, "send.packet"), repr(reads))
    ck("U5 THE SCRAM EXCHANGE as sdclient makes it: client-first is `p=tls-exporter,,` + n= + r=, with the binding read from the socket and required; the server's first "
       "message must keep our nonce and extend it, the iteration count must be a whole number inside SCRAM$MIN.ITER..SCRAM$MAX.ITER, the salt base64 of 4 to 128; the "
       "proof is built from ClientKey over AuthMessage; the server's v= is compared in constant time (SD_CTEQUAL) and a missing or wrong one stops",
       ordered(sn, "cbind = socket.info(skt, SKT$INFO.TLS.CBIND)", "cfirst.bare = 'n=' : ru : ',r=' : cnonce", "pdata = 'p=tls-exporter,,' : cfirst.bare",
               "nonce[1, len(cnonce)] # cnonce or len(nonce) = len(cnonce)", "iter matches '1N0N'","iter < SCRAM$MIN.ITER or iter > SCRAM$MAX.ITER",
               "len(salt) < 4 or len(salt) > 128", "SD_PBKDF2", "pw = ''", "SD_HMACSHA256", "SD_SHA256", "SD_XORBYTES", "pdata = cfinal.bare : ',p=' : proof",
               "in.pkt[1, 2] # 'v='", "SD_CTEQUAL) # '1'", "fail.num = 11475")
       and "if cbind = '' then" in sn and "cfinal.bare = 'c=' : cbind : ',r=' : nonce" in sn and "auth.msg = cfirst.bare : ',' : sfirst : ',' : cfinal.bare" in sn, "")
    pwl = [ln.strip() for ln in sn.split("\n") if re.search(r"\bpw\b", ln)]
    allowed_pw = (r"pw = ''", r"input pw HIDDEN", r"if pw = '' then", r"salted = SDEXT\(pw : @FM : salt : @FM : iter : @FM : SCRAM\$KEY\.LEN, @TRUE, SD_PBKDF2\)")
    ck("U6 THE PASSWORD IS HELD IN ONE VARIABLE AND NOWHERE ELSE: every line that names pw is `pw = ''`, the hidden input, the empty test, or the SD_PBKDF2 call; it is cleared "
       "right after the derivation and in give.up (the only exit of a failure); and the keys the program derived are cleared there too",
       pwl and all(any(re.fullmatch(a, x) for a in allowed_pw) for x in pwl) and ordered(sn, "salted = SDEXT(pw :", "pw = ''", "client.key = SDEXT(salted")
       and "pw = ''" in routine_body(sn, "give.up") and all(v in routine_body(sn, "give.up") for v in ("salted = ''", "client.key = ''", "srvr.key = ''", "expect.v = ''", "proof = ''")),
       repr(pwl))
    leaks = []
    for n, args in sysmsg_calls(sn):
        for a in args:
            if re.search(SECRETS, a):
                leaks.append((n, a))
    for ln in sn.split("\n"):
        if re.search(r"\b(display|crt|print|stop)\b", ln) and re.search(SECRETS, strip_strings(ln)) and "pw = ''" not in ln:
            leaks.append(ln.strip())
        if re.search(r"fail\.a\d = ", ln) and re.search(SECRETS, strip_strings(ln.split("=", 1)[1])):
            leaks.append(ln.strip())
    ck("U7 NO SECRET IS EVER PRINTED: no message, display, crt or fail.a argument names the password, the salted password, a key, the proof, the signature or the AuthMessage",
       not leaks, repr(leaks))
    gu = routine_body(sn, "give.up")
    wr_re = r"\b(writeseq|writeblk|weofseq|oswrite|osdelete|osrename|osopen|openseq|openpath|write|writev|writeu|writet|delete|deleteu|execute|create|createfile|create\.file)\b"
    bare2 = strip_strings(re.sub(r"\b(?:write|open|close|read)\.socket\b|\bos\.execute\b|\b(?:ospath|osrename)\(", "", re.sub(r"^\s*program\s+\S+", "", sn, flags=re.M)))
    ck("U8 NOTHING IS WRITTEN ON ANY FAILURE: the only call of $netcred is WRITE, once, after the server's signature has been verified and the socket closed, and a refusal "
       "from it is the last word; give.up (the exit of every failure) calls nothing that writes and closes the socket; set.netlogin has no statement that writes or deletes a "
       "file at all (only $netcred does) and runs one command (the helper)",
       sn.count("$netcred(") == 1 and sn.count("call $netcred('WRITE', name, rec, pin, err)") == 1
       and ordered(sn, "SD_CTEQUAL) # '1'", "expect.v = ''", "close.socket skt", "call $netcred('WRITE', name, rec, pin, err)", "if err # '' then", "stop sysmsg(err<1,1>", "kernel(K$AUDIT")
       and "netcred" not in gu and "close.socket skt" in gu and "stop sysmsg(fail.num" in gu and not re.search(wr_re, bare2), repr(re.findall(wr_re, bare2)))
    ck("U8b ...every failure goes through give.up (message and stop): no `stop sysmsg(11469..11479` stands anywhere else, and the record handed to $netcred is only the remote "
       "user, the salt, the iteration count and the two keys (attributes 1-5; the pin goes as the argument)",
       not re.search(r"stop sysmsg\(114(?:69|7\d)", sn.replace(gu, "")) and ordered(sn, "rec = ''", "rec<1> = ru", "rec<2> = salt", "rec<3> = iter", "rec<4> = client.key", "rec<5> = srvr.key", "call $netcred('WRITE'")
       and re.search(r"rec = ''\s*\n\s*rec<1> = ru", sn) is not None and not re.search(r"rec<[67]>", sn)
       and re.search(r"fail\.num = 11474 ; fail\.a1 = reason\s*\n\s*gosub give\.up", routine_body(sn, "refused")) is not None, "")
    audits = re.findall(r"kernel\(K\$AUDIT[^\n]*", sn)
    ck("U9 THE AUDIT LINE is one, lower case, after the login is stored: `set.netlogin server=<name> remote=<remote user>` and nothing else - no password, key, hash, salt or pin",
       audits == ["kernel(K$AUDIT, 'set.netlogin server=' : name : ' remote=' : ru)"] and ordered(sn, "call $netcred('WRITE'", "kernel(K$AUDIT"), repr(audits))
    ck("U10 the exit code and the success message: 0 and message 11477 are set together after the audit line, and every refusal sets a failure code before its message",
       ordered(sn, "kernel(K$AUDIT", "@system.return.code = 0", "crt sysmsg(11477, name, ru)", "stop")
       and sn.count("@system.return.code = 0") == 1, "")

    # ---- Y. delete.netlogin ------------------------------------------------------------------------------------------------------
    ck("Y1 delete.netlogin is $internal, `program delete.netlogin`, catalogued once as $deletenetlogin; it validates the name (11452) before $netcred is called, asks EXISTS and "
       "then DELETE (11453 when there is none), audits after the delete and then says 11478",
       "\n$internal\nprogram delete.netlogin" in "\n" + dn and "$catalog $deletenetlogin" in dn
       and len([n for n, t in c.items() if n.startswith("bp:") and "$catalog $deletenetlogin\n" in t + "\n"]) == 1
       and "len(name) < 1 or len(name) > 16 or not(chk.ok) or index(lc.set, name[1, 1], 1) = 0" in dn and "if dcount(words, ' ') # 2 then" in dn
       and ordered(dn, "stop sysmsg(11451", "stop sysmsg(11452", "call $netcred('EXISTS'", "stop sysmsg(11453", "call $netcred('DELETE'", "kernel(K$AUDIT", "crt sysmsg(11478"), "")
    ck("Y2 ...it asks no gate (K$NET, K$ADMINISTRATOR: removing a login adds nothing to what an account may do), prompts for nothing, opens no socket, runs no command, and "
       "has exactly one audit line, `delete.netlogin server=<name>`",
       not re.search(r"K\$NET|K\$ADMINISTRATOR|\binput\b|open\.socket|os\.execute|\$netcred\('(?:READ|WRITE)'", dn)
       and re.findall(r"kernel\(K\$AUDIT[^\n]*", dn) == ["kernel(K$AUDIT, 'delete.netlogin server=' : name)"], "")

    # ---- V. the VOC entries ---------------------------------------------------------------------------------------------------------
    nv = srcs["newvoc.list"].lower().split("\n")
    ck("V1 both verbs are in voc_template as V / CA / $name AND in newvoc (so EVERY account has them: a person needs no administrator to set up a login, the gate and the "
       "list are what limit it) as a description line, CA, $name",
       all(srcs["voc:" + w].split() == ["V", "CA", cat] and w in nv
           and [x for x in srcs["newvoc:" + w].split("\n") if x != ""][1:] == ["CA", cat] and len([x for x in srcs["newvoc:" + w].split("\n") if x != ""]) == 3
           for w, _p, cat in NL_VERBS), "")

    # ---- H. messages 11450-11479 -------------------------------------------------------------------------------------------------------
    nlt = {n: srcs["msg:%d" % n] for n in range(NL_MSG_FIRST, NL_MSG_LAST + 1)}
    ck("H1 messages 11450 to 11479 all exist, each one line, inside the Linux block 11000-11999, and the whole block is this slice's",
       all(t is not None and t.strip() != "" and "\n" not in t.rstrip("\n") for t in nlt.values()) and LINUX_BLOCK[0] <= NL_MSG_FIRST and NL_MSG_LAST <= LINUX_BLOCK[1],
       repr([n for n, t in nlt.items() if not t]))
    prog = nc + "\n" + sn + "\n" + dn
    used2 = {int(x) for x in re.findall(r"\b(114[5-7]\d)\b", prog)}
    ck("H2 every message from 11450 to 11479 is used by $netcred, set.netlogin or delete.netlogin (and none outside the block is invented)",
       set(range(NL_MSG_FIRST, NL_MSG_LAST + 1)) <= used2 and not (used2 - set(range(NL_MSG_FIRST, NL_MSG_LAST + 1))), repr(sorted(set(range(NL_MSG_FIRST, NL_MSG_LAST + 1)) - used2)))
    short2 = []
    for n, args in sysmsg_calls(sn + "\n" + dn):
        t = srcs.get("msg:%d" % n)
        if t is None or not (NL_MSG_FIRST <= n <= NL_MSG_LAST):
            continue
        top = max([int(x) for x in re.findall(r"%(\d)", t)] or [0])
        if len(args) != top:
            short2.append((n, len(args), top))
    for n, a in fail_places(sn):
        top = max([int(x) for x in re.findall(r"%(\d)", srcs.get("msg:%d" % n) or "")] or [0])
        if a != top:
            short2.append(("fail.num", n, a, top))
    for n, a in err_places(nc):
        t = srcs.get("msg:%d" % n)
        if t is None or not (NL_MSG_FIRST <= n <= NL_MSG_LAST):
            continue
        top = max([int(x) for x in re.findall(r"%(\d)", t)] or [0])
        if a != top:
            short2.append(("err", n, a, top))
    ck("H3 each message a program gives has as many arguments as the message has %n places: the sysmsg calls, the fail.aK of every failure, and the err of $netcred",
       not short2 and len(fail_places(sn)) >= 10 and len(err_places(nc)) >= 12, repr(short2))
    g_ = lambda n: nlt.get(n) or ""
    ck("H4 the wording the users rely on: the password is said not to be stored (11464, 11477); every failure after the pin says nothing was stored, and the ones before any "
       "byte was sent say nothing was sent (11469, 11470, 11471, 11479); 11460 names net-on in lower case; 11455 tells the person to run set.netlogin again; 11454 says nothing was used",
       "not stored" in g_(11464) and "not stored" in g_(11477) and all("Nothing was sent or stored" in g_(n) or "nothing was stored" in g_(n) for n in (11469, 11470, 11471, 11479))
       and "Nothing was sent to it" in g_(11471) and all("Nothing was stored" in g_(n) for n in (11472, 11473, 11474, 11475, 11476))
       and "net-on" in g_(11460) and "Run set.netlogin %1 again" in g_(11455) and "Nothing was used" in g_(11454)
       and g_(11450).strip() == "Usage: set.netlogin server" and g_(11451).strip() == "Usage: delete.netlogin server", "")

    # ---- E. the root agrees with sd-elevate, and the sudoers line is exactly one command -----------------------------------------
    se, sdo = c["sd-elevate"], c["sdcore.sudoers"]
    ck("E1 /var/lib/sd-net is the root in $netcred and in sd-elevate netcred-dir (SD_NET_ROOT_REAL), and the verb is `netcred-dir` in the usage, the case and the helper's success line",
       "SD_NET_ROOT_REAL=/var/lib/sd-net" in se and "/var/lib/sd-net" in nc and re.search(r"netcred-dir\)", se) is not None and "netcred-dir: " in se, "")
    sline = next((ln for ln in sdo.split("\n") if ln.startswith("%sdusers") and "NOPASSWD:" in ln), "")
    cmds = [x.strip() for x in sline.split("NOPASSWD:", 1)[1].split(",")] if sline else []
    ck("E2 the sudoers line gives %sdusers exactly `/usr/local/sbin/sd-elevate netcred-dir` for it - no wildcard, no argument after it - and nothing else for netcred-dir",
       [x for x in cmds if "netcred-dir" in x] == ["/usr/local/sbin/sd-elevate netcred-dir"] and sdo.count("netcred-dir") >= 1
       and not re.search(r"netcred-dir\s*\*", sdo), repr(cmds))


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
mut("set.server puts the pin on the audit trail", "setserver", "' pin=' : pin.how)", "' pin=' : pin.how : ' hash=' : pin)")
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
mut("11413 says no.query skips the key question", "msg:11413", lambda t: t.replace("no.query never skips that question", "no.query skips that question", 1))
mut("11439 stops naming the word", "msg:11439", lambda t: t.replace("net-on", "net-add"))
mut("11412 stops being the usage line", "msg:11412", lambda t: "Use the server verb\n")


# ---- slice 2a: CONNECT
def after(marker, old, new):
    """OLD replaced by NEW at its first place AFTER MARKER (the same text earlier in the file is not touched)."""
    def f(text):
        i = text.find(marker)
        j = text.find(old, i) if i >= 0 else -1
        if j < 0:
            raise KeyError("text not after the marker: %r / %r" % (marker[:40], old[:40]))
        return text[:j] + new + text[j + len(old):]
    return f


def last(old, new):
    """The LAST place OLD stands in the text is replaced."""
    def f(text):
        j = text.rfind(old)
        if j < 0:
            raise KeyError("text not in the source: %r" % old[:60])
        return text[:j] + new + text[j + len(old):]
    return f


CONN_BLOCK = r"   if connect\.mode then\n      gosub connect\.pin[^\n]*\n      pin\.how = 'confirmed'\n   end\n"
SPKI_FN = "int sd_tls_client_peer_spki_sha256("
# T1-T2: the order of the flow
mut("CONNECT is case sensitive", "setserver", "pin = downcase(field(words, ' ', 6))", "pin = field(words, ' ', 6)")
mut("CONNECT does not set connect mode", "setserver", "      connect.mode = @true", "      connect.mode = @false")
mut("a typed-pin check still runs for CONNECT", "setserver", "if not(connect.mode) then", "if @true then")
mut("set.server dials before the fields are checked", "setserver", "   if bad # 0 then stop", "   if connect.mode then gosub connect.pin\n   if bad # 0 then stop")
mut("set.server dials before the replace question", "setserver",
    lambda t: re.sub(r"(   if found # 0 and not\(no\.query\) then\n)", lambda m: "   if connect.mode then\n      gosub connect.pin\n      pin.how = 'confirmed'\n   end\n" + m.group(1),
                     rx(CONN_BLOCK, "", re.M)(t), count=1))
mut("the dial is not guarded by connect mode", "setserver", "   if connect.mode then\n      gosub connect.pin", "   if @true then\n      gosub connect.pin")
mut("confirmed is set before the dial", "setserver",
    lambda t: t.replace("      pin.how = 'confirmed'\n", "", 1).replace("      gosub connect.pin", "      pin.how = 'confirmed'\n      gosub connect.pin", 1))
mut("a typed pin opens a socket too", "setserver", lambda t: t.replace("   d = date()\n", "   skt = open.socket(host, port, SKT$BLOCKING + SKT$TLS, NET.CONNECT.SECS)\n   d = date()\n", 1))
mut("the sockets keys are not included", "setserver", rx(r"^\$include keys\.h\n", "", re.M))
# T3-T4: the socket
mut("the socket is opened without TLS", "setserver", "SKT$BLOCKING + SKT$TLS", "SKT$BLOCKING")
mut("the socket is opened with no timeout", "setserver", ", NET.CONNECT.SECS)", ")")
mut("the timeout is 50 seconds", "setserver", "$define NET.CONNECT.SECS 5", "$define NET.CONNECT.SECS 50")
mut("the socket is not closed", "setserver", drop_line(r"^   close\.socket skt"))
mut("the socket is closed after the question", "setserver",
    lambda t: t.replace("   close.socket skt\n", "", 1).replace("   pin = spki\n", "   close.socket skt\n   pin = spki\n", 1))
mut("something is sent over the connection", "setserver", "   spki = downcase(trim(", "   write.socket 'x' to skt else null\n   spki = downcase(trim(")
mut("the status is not read at once", "setserver", drop_line(r"^   oserr = os\.error\(\)"))
mut("the hash is not shown", "setserver", "   display spki\n", "   display ''\n")
# T5: the key question
mut("no.query skips the key question", "setserver", "   display sysmsg(11440, host, port)", "   if no.query then\n      pin = spki\n      return\n   end\n   display sysmsg(11440, host, port)")
mut("an empty answer to the key question is a yes", "setserver", last("if yn = '' then yn = 'N'", "if yn = '' then yn = 'Y'"))
mut("input that ends is a yes to the key question", "setserver", last("if yn = '' and status() = ER$EOF then yn = 'N'", "if yn = '' and status() = ER$EOF then yn = 'Y'"))
mut("the key question is asked once", "setserver", rx(r"(   loop\n      display sysmsg\(11442\) : [^\n]*\n.*?\n)   until yn = 'Y' or yn = 'N'\n   repeat\n", r"\1   until 1\n   repeat\n", re.S))
# T6: nothing is written
mut("an n to the key question goes on to write", "setserver", "stop sysmsg(11443, name)", "display sysmsg(11443, name)")
mut("a failed connection goes on to write", "setserver", "stop sysmsg(11444, host, port, st, oserr)", "display sysmsg(11444, host, port, st, oserr)")
mut("a failed handshake is not told from a failed connection", "setserver", drop_line(r"if st = ER\$CONNECT and oserr = 0 then stop sysmsg\(11445"))
mut("every ER$CONNECT is a handshake failure", "setserver", "if st = ER$CONNECT and oserr = 0 then stop sysmsg(11445", "if st = ER$CONNECT then stop sysmsg(11445")
mut("an empty hash is accepted", "setserver", "if len(spki) # 64 or not(chk.ok) then", "if len(spki) > 64 then")
mut("the hash is not checked for hexadecimal digits", "setserver", drop_line(r"^   chk\.text = spki ; chk\.set"))
mut("the hash is not lower cased", "setserver", "spki = downcase(trim(socket.info(skt, SKT$INFO.TLS.SPKI)))", "spki = trim(socket.info(skt, SKT$INFO.TLS.SPKI))")
mut("the lock is left held after a failed connection", "setserver", rx(r"      gosub release\.lock\n(      @system\.return\.code = -ER\$FAILED\n      if st = ER\$CONNECT)", r"\1"))
mut("the lock is left held after an empty hash", "setserver", rx(r"      gosub release\.lock\n(      @system\.return\.code = -ER\$FAILED\n      stop sysmsg\(11446)", r"\1"))
mut("the routine writes the definitions", "setserver", "   pin = spki\n   return", "   call !netdefs('WRITE', defs, err)\n   pin = spki\n   return")
# T8: the audit words
mut("the audit line loses how the pin was obtained", "setserver", "' replaced=' : rep.word : ' pin=' : pin.how)", "' replaced=' : rep.word)")
mut("a confirmed pin is audited as typed", "setserver", "pin.how = 'confirmed'", "pin.how = 'typed'")
mut("the audit word confirmed is upper case", "setserver", "pin.how = 'confirmed'", "pin.how = 'CONFIRMED'")
mut("a typed pin is audited as confirmed", "setserver", "pin.how = 'typed'", "pin.how = 'confirmed'")
# C: the hash is of the key
mut("the hash is of the certificate", "sd_tls.c", "der_len = i2d_X509_PUBKEY(X509_get_X509_PUBKEY(cert), &der);", "der_len = 1; X509_digest(cert, EVP_sha256(), out, &n);")
mut("the hash is SHA-1", "sd_tls.c", after(SPKI_FN, "EVP_sha256()", "EVP_sha1()"))
mut("the hash may be short", "sd_tls.c", after(SPKI_FN, "n == 32", "n == 20"))
mut("the certificate is not freed", "sd_tls.c", after(SPKI_FN, "  X509_free(cert);\n", ""))
mut("the DER bytes are not freed", "sd_tls.c", after(SPKI_FN, "  OPENSSL_free(der);\n", ""))
mut("no certificate is not answered false", "sd_tls.c", after(SPKI_FN, "if (cert == NULL)", "if (0)"))
mut("the hash function has another signature", "sd_tls.h", "int sd_tls_client_peer_spki_sha256(SD_TLS_CLIENT* c, unsigned char* out);", "int sd_tls_client_peer_spki_sha256(SD_TLS_CLIENT* c, unsigned char* out, int n);")
mut("the hash digits are upper case", "op_skt.c", after("case SKT_INFO_TLS_SPKI:", '"%02x"', '"%02X"'))
mut("the answer is not emptied first", "op_skt.c", after("case SKT_INFO_TLS_SPKI:", "hex[0] = '\\0';", ""))
mut("only half the hash is written", "op_skt.c", after("case SKT_INFO_TLS_SPKI:", "i < 32", "i < 16"))
mut("a socket without TLS is not tested", "op_skt.c", after("case SKT_INFO_TLS_SPKI:", "(sockvar->tls != NULL) && ", ""))
mut("the answer is not returned", "op_skt.c", after("case SKT_INFO_TLS_SPKI:", "k_put_c_string(hex, &result_descr)", "k_put_c_string(\"\", &result_descr)"))
mut("the SOCKET.INFO key is gone", "op_skt.c", "case SKT_INFO_TLS_SPKI:", "case SKT_INFO_TLS_SPKJ:")
mut("SKT_INFO_TLS_SPKI shares 10 with the trace key", "keys.h", rx(r"(#define\s+SKT_INFO_TLS_SPKI\s+)11", r"\g<1>10"))
mut("SKT_INFO_TLS_SPKI is 12", "keys.h", rx(r"(#define\s+SKT_INFO_TLS_SPKI\s+)11", r"\g<1>12"))
mut("SKT$INFO.TLS.SPKI is 9 in the BASIC header", "syscom/keys.h", rx(r"(\$define\s+SKT\$INFO\.TLS\.SPKI\s+)11", r"\g<1>9"))
# G: the new messages
mut("11442 stops asking", "msg:11442", lambda t: "Trusted\n")
mut("11440 says something was sent", "msg:11440", lambda t: t.replace("a TLS handshake only: nothing was sent", "a TLS session", 1))
mut("11444 loses its fourth place", "msg:11444", lambda t: t.replace("(status %3, os error %4)", "(status %3)", 1))
mut("message 11446 is missing", "msg:11446", lambda t: None)
mut("11443 stops saying nothing was written", "msg:11443", lambda t: t.replace("Nothing was written: ", "", 1))
mut("11412 loses the word connect", "msg:11412", lambda t: t.replace("{pin | connect}", "pin", 1))
mut("message 11446 takes two lines", "msg:11446", lambda t: t.rstrip("\n") + "\nsecond line\n")

# ---- slice 2b: the person's login ---------------------------------------------------------------------------------------------------
FP_FN = "Private int file_private_check(const char* path, int want_dir) {"
NCR = "bp:netcred"
SNL = "bp:setnetlogin"
DNL = "bp:deletenetlogin"
NC_TRUST_READ = "         if SDEXT(path : @FM : 'FILE', @TRUE, SD_FILE_PRIVATE) # '1' then\n            err = 11454:@vm:server:@vm:path\n            return\n         end\n"
# F: the number and the case
mut("SD_FILE_PRIVATE is 112 in keys.h", "keys.h", rx(r"(#define\s+SD_FILE_PRIVATE\s+)111", r"\g<1>112"))
mut("SD_FILE_PRIVATE is 112 in the BASIC header", "syscom/keys.h", rx(r"(\$define\s+SD_FILE_PRIVATE\s+)111", r"\g<1>112"))
mut("SD_FILE_PRIVATE shares 110 with SD_TLS_CBIND", "keys.h", rx(r"(#define\s+SD_FILE_PRIVATE\s+)111", r"\g<1>110"))
mut("the BASIC header gives the neighbour another number", "syscom/keys.h", rx(r"(\$define\s+SD_TLS_CBIND\s+)110", r"\g<1>109"))
mut("the answer starts as 1", "op_sdext.c", after("case SD_FILE_PRIVATE:", "answer[0] = '0';", "answer[0] = '1';"))
mut("a wrong argument count is not looked at", "op_sdext.c", after("case SD_FILE_PRIVATE:", "argCnt != 2", "argCnt != 3"))
mut("the word FILE asks for a directory", "op_sdext.c", after("case SD_FILE_PRIVATE:", "file_private_check(SDMEArgArray[0], 0)", "file_private_check(SDMEArgArray[0], 1)"))
mut("the word DIR asks for a file", "op_sdext.c", after("case SD_FILE_PRIVATE:", "file_private_check(SDMEArgArray[0], 1)", "file_private_check(SDMEArgArray[0], 0)"))
mut("any other word is a yes", "op_sdext.c", after("case SD_FILE_PRIVATE:", "      }\n      k_put_c_string(answer, e_stack);", "      } else {\n        answer[0] = '1';\n      }\n      k_put_c_string(answer, e_stack);"))
mut("the answer is not the computed one", "op_sdext.c", after("case SD_FILE_PRIVATE:", "k_put_c_string(answer, e_stack)", "k_put_c_string(\"1\", e_stack)"))
mut("lstat is stat (a link is followed)", "op_sdext.c", after(FP_FN, "lstat(path, &st)", "stat(path, &st)"))
mut("the owner is the real uid", "op_sdext.c", after(FP_FN, "geteuid()", "getuid()"))
mut("the owner is not tested", "op_sdext.c", after(FP_FN, "if (st.st_uid != geteuid())", "if (0)"))
mut("group bits are allowed", "op_sdext.c", after(FP_FN, "(st.st_mode & 077)", "(st.st_mode & 007)"))
mut("world bits are allowed", "op_sdext.c", after(FP_FN, "(st.st_mode & 077)", "(st.st_mode & 070)"))
mut("a relative path is allowed", "op_sdext.c", after(FP_FN, "path[0] != '/'", "path[0] != 'x'"))
mut("a long path is allowed", "op_sdext.c", after(FP_FN, "len >= sizeof(parent)", "0"))
mut("a failed lstat is allowed", "op_sdext.c", after(FP_FN, "lstat(path, &st) != 0", "lstat(path, &st) != 0 && 0"))
mut("any directory passes", "op_sdext.c", after(FP_FN, "return S_ISDIR(st.st_mode) ? 1 : 0;", "return 1;"))
mut("a link to a directory passes (not S_ISDIR)", "op_sdext.c", after(FP_FN, "S_ISDIR(st.st_mode)", "(st.st_mode & S_IFMT) != 0"))
mut("a file need not be a regular file", "op_sdext.c", after(FP_FN, "!S_ISREG(st.st_mode)", "0"))
mut("the parent directory is not tested", "op_sdext.c", after(FP_FN, "return file_private_check(parent, 1);", "return 1;"))
mut("the parent is tested as a file", "op_sdext.c", after(FP_FN, "return file_private_check(parent, 1);", "return file_private_check(parent, 0);"))
mut("the parent is the file itself", "op_sdext.c", after(FP_FN, "slash = strrchr(parent, '/');", "slash = parent + len;"))
# F: who calls it
mut("a program outside $netcred and set.netlogin calls it", "bp:cd", lambda t: t + "\n   x = SDEXT(path : @FM : 'FILE', @TRUE, SD_FILE_PRIVATE) # '1'\n")
mut("set.netlogin's call is not compared with 1", SNL, "SDEXT(cred.path : @FM : 'DIR', @TRUE, SD_FILE_PRIVATE) # '1'", "SDEXT(cred.path : @FM : 'DIR', @TRUE, SD_FILE_PRIVATE)")
mut("SDEXT is a plain intrinsic in BCOMP", "bp:bcomp", lambda t: t + '\n   intrinsics<-1> = "SDEXT"\n')
mut("SDEXT is not an internal intrinsic", "bp:bcomp", 'int.intrinsics<-1> = "SDEXT"', 'int.intrinsics<-1> = "SDEXX"')
# R: $netcred, the path
mut("the credential root is /tmp/sd-net", NCR, "'/var/lib/sd-net'", "'/tmp/sd-net'")
mut("the credential root is built twice", NCR, lambda t: t.replace("   tmp = path : '.new'\n", "   tmp = path : '.new'\n   zz = '/var/lib/sd-net/x'\n", 1))
mut("the Linux user comes from @logname", NCR, "lu = kernel(K$USERNAME, 0)", "lu = @logname")
mut("root may keep a login", NCR, "lu = '' or lu = 'root' or lu = 'sdsys'", "lu = '' or lu = 'sdsys'")
mut("sdsys may keep a login", NCR, "lu = '' or lu = 'root' or lu = 'sdsys'", "lu = '' or lu = 'root'")
mut("the user name is not length checked", NCR, "len(lu) > MAX.USERNAME.LEN", "len(lu) > 9999")
mut("the path is built before the user is validated", NCR,
    lambda t: t.replace("   cred.dir = NETCRED.ROOT : '/' : lu\n", "", 1).replace("   lu = kernel(K$USERNAME, 0)\n", "   cred.dir = NETCRED.ROOT : '/' : lu\n   lu = kernel(K$USERNAME, 0)\n", 1))
mut("the server name is not validated", NCR, "len(server) < 1 or len(server) > 16 or not(chk.ok) or index(lc.set, server[1, 1], 1) = 0", "len(server) < 1")
mut("a server name may start with a digit", NCR, " or index(lc.set, server[1, 1], 1) = 0", "")
mut("a server name of 17 is allowed", NCR, "len(server) > 16", "len(server) > 17")
mut("a server name may hold a slash", NCR, "chk.text = server ; chk.set = lc.set:digits", "chk.text = server ; chk.set = lc.set:digits:'/'")
mut("the copy has the login's own name", NCR, "tmp = path : '.new'", "tmp = path")
mut("the file is somewhere else", NCR, "path = cred.dir : '/' : server", "path = cred.dir : '/' : server : '.cred'")
# R: the test comes first
mut("the directory is not tested", NCR, "if not(dir.there) or SDEXT(cred.dir : @FM : 'DIR', @TRUE, SD_FILE_PRIVATE) # '1' then", "if not(dir.there) then")
mut("a missing directory is allowed", NCR, "if not(dir.there) or SDEXT(cred.dir : @FM : 'DIR', @TRUE, SD_FILE_PRIVATE) # '1' then", "if dir.there and SDEXT(cred.dir : @FM : 'DIR', @TRUE, SD_FILE_PRIVATE) # '1' then")
mut("READ opens a file it has not tested", NCR, after("case act = 'READ'", NC_TRUST_READ, ""))
mut("READ tests the file after it opens it", NCR,
    lambda t: after("case act = 'READ'", NC_TRUST_READ, "")(t).replace("         closeseq f\n", "         closeseq f\n" + NC_TRUST_READ, 1))
mut("DELETE removes a file it has not tested", NCR, after("case act = 'DELETE'", NC_TRUST_READ, ""))
mut("EXISTS says 1 without the test", NCR, after("case act = 'EXISTS'", "SDEXT(path : @FM : 'FILE', @TRUE, SD_FILE_PRIVATE) = '1'", "1"))
mut("WRITE renames a copy it has not tested", NCR, "if SDEXT(tmp : @FM : 'FILE', @TRUE, SD_FILE_PRIVATE) # '1' then", "if 0 then")
mut("WRITE tests the copy before it is written", NCR,
    lambda t: t.replace("if SDEXT(tmp : @FM : 'FILE', @TRUE, SD_FILE_PRIVATE) # '1' then", "if 0 then", 1).replace("         writeseq line to tmp.f else\n", "         if SDEXT(tmp : @FM : 'FILE', @TRUE, SD_FILE_PRIVATE) # '1' then err = 11454\n         writeseq line to tmp.f else\n", 1))
mut("a file that fails the test is reported as damaged", NCR, after("case act = 'READ'", "err = 11454:@vm:server:@vm:path", "err = 11456:@vm:server:@vm:path"))
mut("a file is opened a third time", NCR, lambda t: t.replace("         closeseq f\n", "         closeseq f\n         openseq path to f else null\n", 1))
mut("the copy is renamed twice", NCR, lambda t: t.replace("         if err # '' then void ospath(tmp, OS$DELETE)\n", "         void osrename(tmp, path)\n         if err # '' then void ospath(tmp, OS$DELETE)\n", 1))
# R: the file never holds the password
mut("the line holds a password", NCR, "line = 'v1'", "line = 'v1' : pw")
mut("WRITE writes the record raw", NCR, "line := '|' : one<i>", "line := '|' : record<i>")
mut("a password parameter appears", NCR, "subroutine netcred(action, server, record, pin, err)", "subroutine netcred(action, server, record, pin, err, password)")
mut("a second line is written", NCR, "         writeseq line to tmp.f else\n", "         writeseq 'x' to tmp.f else null\n         writeseq line to tmp.f else\n")
# R: READ and WRITE in order
mut("READ does not need the pin argument", NCR, after("case act = 'READ'", "gosub check.pin", "pin.ok = @true"))
mut("READ accepts another pin", NCR, "if one<6> # pin then", "if one<6> # one<6> then")
mut("READ does not look at the shape of the record", NCR, after("case act = 'READ'", "         gosub check.record\n", ""))
mut("READ hands the record back before the pin test", NCR, after("case act = 'READ'", "         if one<6> # pin then", "         record = one\n         if one<6> # pin then"))
mut("READ does not look for marks", NCR, "len(convert(marks, '', line)) # len(line)", "0")
mut("READ takes any layout", NCR, "dcount(line, @fm) # 8 or line<1> # 'v1'", "0")
mut("READ opens before it looks for the file", NCR, after("case act = 'READ'", "         if not(ospath(path, OS$EXISTS)) then\n            err = 11453:@vm:server\n            return\n         end\n", ""))
mut("WRITE keeps attribute 6 of the record", NCR, "         one<6> = pin\n", "")
mut("WRITE does not need the pin argument", NCR, after("case act = 'WRITE'", "gosub check.pin", "pin.ok = @true"))
mut("WRITE does not look at the shape of the record", NCR, after("case act = 'WRITE'", "         gosub check.record\n", ""))
mut("WRITE sets no umask", NCR, "         void umask(NETCRED.UMASK)\n", "")
mut("the umask is 022", NCR, "$define NETCRED.UMASK 63", "$define NETCRED.UMASK 18")
mut("the umask is not put back", NCR, "         void umask(old.umask)\n", "")
mut("the umask is put back after the write", NCR,
    lambda t: t.replace("         void umask(old.umask)\n", "", 1).replace("         closeseq tmp.f\n", "         closeseq tmp.f\n         void umask(old.umask)\n", 1))
mut("WRITE renames whatever the error", NCR, "         if err = '' then\n            if not(osrename(tmp, path)) then", "         if @true then\n            if not(osrename(tmp, path)) then")
mut("a failed write leaves the copy", NCR, "if err # '' then void ospath(tmp, OS$DELETE)", "if err # '' then null")
mut("an old copy is not removed first", NCR, "if ospath(tmp, OS$EXISTS) then", "if 0 then")
mut("a copy that could not be made is not noticed", NCR, "         if not(made) then\n            err = 11457", "         if 0 then\n            err = 11457")
mut("check.record: iterations have no ceiling", NCR, " or what + 0 > SCRAM$MAX.ITER", "")
mut("check.record: iterations have no floor", NCR, "what + 0 < SCRAM$MIN.ITER", "what + 0 < 1")
mut("check.record: iterations need not be a number", NCR, "or not(what matches '1N0N')", "")
mut("check.record: base64 allows a bar", NCR, "digits:'+/='", "digits:'+/=|'")
mut("check.record: a key may be long", NCR, "len(what) < 4 or len(what) > 128", "len(what) < 4 or len(what) > 1280")
mut("check.record: a pin may be upper case", NCR, "hex.set = digits:'abcdef'", "hex.set = digits:'abcdefABCDEF'")
mut("check.record: a pin may be short", NCR, "len(what) # 64", "len(what) < 8")
mut("check.record: created is anything", NCR, "'4N\"-\"2N\"-\"2N'", "'0X'")
mut("check.record: a remote user may hold a space", NCR, "os.chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':lc.set:digits:'._-'", "os.chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':lc.set:digits:'._- '")
mut("an unknown action is allowed through", NCR, "err = 2018:@vm:action", "err = 11452:@vm:action")
mut("EXISTS reports an error for no directory", NCR, "if act = 'EXISTS' then return", "null")
mut("EXISTS does not start at 0", NCR, "if act = 'EXISTS' then record = 0", "null")
mut("DELETE of nothing is not told", NCR, after("case act = 'DELETE'", "err = 11453:@vm:server", "err = 11457:@vm:server"))
# U: set.netlogin, the order of the checks
mut("set.netlogin is not internal", SNL, "$internal\nprogram set.netlogin", "program set.netlogin")
mut("set.netlogin is catalogued under another name", SNL, "$catalog $setnetlogin", "$catalog $setnetlogon")
mut("the NET gate is not asked", SNL, "if not(is.admin) and not(kernel(K$NET, -1)) then", "if not(is.admin) and 0 then")
mut("the NET gate is asked with 1 (set)", SNL, "kernel(K$NET, -1)", "kernel(K$NET, 1)")
mut("the administrator test is not made", SNL, "is.admin = kernel(K$ADMINISTRATOR, -1)", "is.admin = @false")
mut("the NET gate is asked after the definition", SNL,
    lambda t: t.replace("   if not(is.admin) and not(kernel(K$NET, -1)) then\n      @system.return.code = -ER$PERM\n      stop sysmsg(11460, acc) ;* This account does not have the NET gate\n   end\n", "", 1)
    .replace("   host = defs<found,2>\n", "   if not(is.admin) and not(kernel(K$NET, -1)) then\n      @system.return.code = -ER$PERM\n      stop sysmsg(11460, acc)\n   end\n   host = defs<found,2>\n", 1))
mut("the account list is not tested", SNL, "index(',':downcase(defs<found,7>):',', ',':acc:',', 1) = 0", "0")
mut("the account list is a substring test", SNL, "index(',':downcase(defs<found,7>):',', ',':acc:',', 1) = 0", "index(downcase(defs<found,7>), acc, 1) = 0")
mut("the account list binds the administrator too", SNL, "if not(is.admin) then\n      if index(", "if @true then\n      if index(")
mut("the account name is not lower cased", SNL, "acc = downcase(@who)", "acc = @who")
mut("the server name is not validated", SNL, "len(name) < 1 or len(name) > 16 or not(chk.ok) or index(lc.set, name[1, 1], 1) = 0", "len(name) < 1")
mut("two words after the verb are allowed", SNL, "if dcount(words, ' ') # 2 then", "if dcount(words, ' ') < 2 then")
mut("the definition's pin is not tested for form", SNL, "if len(pin) # 64 or not(chk.ok) then", "if 0 then")
mut("sdsys may run it", SNL, "lu = '' or lu = 'sdsys' or lu = 'root'", "lu = ''")
mut("the Linux user comes from @logname", SNL, "lu = kernel(K$USERNAME, 0)", "lu = @logname")
mut("sudo may ask for a password", SNL, "   if elev[1, 5] = 'sudo ' then elev = 'sudo -n ' : elev[6, 9999]\n", "")
mut("the helper is run with another word", SNL, "elev : ' netcred-dir 2>&1'", "elev : ' netcred-dir all 2>&1'")
mut("a second command is run", SNL, "   stat = os.error()\n", "   stat = os.error()\n   os.execute 'id' capturing zz\n")
mut("the helper's path need not end in the user", SNL, "cred.path[len(cred.path) - len(tail) + 1, len(tail)] # tail or SDEXT", "SDEXT")
mut("the directory is not tested", SNL, " or SDEXT(cred.path : @FM : 'DIR', @TRUE, SD_FILE_PRIVATE) # '1'", "")
mut("the helper's success line is any line", SNL, "out<i>[1, 13] = 'netcred-dir: ' and ", "")
# U: prompts and the connection
mut("the password is asked before the user", SNL, lambda t: t.replace("   input ru\n", "   input pw HIDDEN\n   input ru\n", 1))
mut("the user is asked twice", SNL, lambda t: t.replace("   input ru\n", "   input ru\n   input ru\n", 1))
mut("an empty user goes on", SNL, "if ru = '' or len(ru) > MAX.USERNAME.LEN or not(chk.ok) then", "if 0 then")
mut("an empty password goes on", SNL, "   if pw = '' then\n      @system.return.code = -ER$ARGS\n      stop sysmsg(11468)", "   if 0 then\n      @system.return.code = -ER$ARGS\n      stop sysmsg(11468)")
mut("the socket is opened without TLS", SNL, "SKT$BLOCKING + SKT$TLS", "SKT$BLOCKING")
mut("the socket is opened with no timeout", SNL, ", NET.CONNECT.SECS)", ")")
mut("a second socket is opened", SNL, lambda t: t.replace("   spki = downcase(", "   skt2 = open.socket(host, port, SKT$BLOCKING + SKT$TLS, NET.CONNECT.SECS)\n   spki = downcase(", 1))
mut("the host is not the definition's", SNL, "host = defs<found,2>", "host = 'localhost'")
mut("the pin is not the definition's", SNL, "pin = downcase(defs<found,5>)", "pin = ''")
mut("the pin is not compared", SNL, "if spki # pin then", "if spki # spki then")
mut("the pin is compared after the Ack", SNL,
    lambda t: t.replace("if spki # pin then", "if 0 then", 1).replace("   if not(acked) then", "   if spki # pin then\n      fail.num = 11471 ; fail.a1 = host ; fail.a2 = port ; fail.a3 = name\n      gosub give.up\n   end\n   if not(acked) then", 1))
mut("the pin is compared after the first packet", SNL,
    lambda t: t.replace("if spki # pin then", "if 0 then", 1).replace("   gosub read.packet\n", "   if spki # pin then\n      fail.num = 11471 ; fail.a1 = host ; fail.a2 = port ; fail.a3 = name\n      gosub give.up\n   end\n   gosub read.packet\n", 1))
mut("a mismatch only warns", SNL, "      fail.num = 11471 ; fail.a1 = host ; fail.a2 = port ; fail.a3 = name   ;* The key is not the key in the definition\n      gosub give.up\n", "      crt 'warning'\n")
mut("the hash is not lower cased", SNL, "spki = downcase(trim(socket.info(skt, SKT$INFO.TLS.SPKI)))", "spki = trim(socket.info(skt, SKT$INFO.TLS.SPKI))")
mut("an empty hash goes on", SNL, "if len(spki) # 64 or not(chk.ok) then", "if len(spki) > 64 then")
mut("a read has no timeout", SNL, "b = read.socket(skt, 1, SKT$BLOCKING, NET.READ.MS)", "b = read.socket(skt, 1, SKT$BLOCKING, 0)")
mut("a write has no timeout", SNL, "void write.socket(skt, pk, SKT$BLOCKING, NET.READ.MS)", "void write.socket(skt, pk, SKT$BLOCKING, 0)")
mut("a second place writes to the socket", SNL, lambda t: t.replace("   spki = downcase(", "   void write.socket(skt, 'x', SKT$BLOCKING, NET.READ.MS)\n   spki = downcase(", 1))
mut("the first packet is sent before the pin test", SNL, lambda t: t.replace("   skt.open = @true\n", "   skt.open = @true\n   ptype = SrvrScramFirst ; pdata = 'x' ; gosub send.packet\n", 1))
# U: the exchange
mut("client-first has no binding", SNL, "pdata = 'p=tls-exporter,,' : cfirst.bare", "pdata = 'n,,' : cfirst.bare")
mut("a missing binding goes on", SNL, "   if cbind = '' then", "   if 0 then")
mut("the nonce is not checked", SNL, "nonce[1, len(cnonce)] # cnonce or len(nonce) = len(cnonce)", "0")
mut("the iteration count is not bounded", SNL, "iter < SCRAM$MIN.ITER or iter > SCRAM$MAX.ITER", "iter < 1")
mut("the iteration count need not be a number", SNL, "or not(iter matches '1N0N')", "")
mut("the salt is not checked", SNL, "len(salt) < 4 or len(salt) > 128 or not(chk.ok)", "len(salt) < 0")
mut("the signature is not compared", SNL, "SDEXT(in.pkt[3, 999999] : @FM : expect.v, @TRUE, SD_CTEQUAL) # '1'", "0")
mut("the signature is compared in the open", SNL, "SDEXT(in.pkt[3, 999999] : @FM : expect.v, @TRUE, SD_CTEQUAL) # '1'", "in.pkt[3, 999999] # expect.v")
mut("a missing signature goes on", SNL, "if in.pkt[1, 2] # 'v=' then", "if 0 then")
# U: the password and the keys
mut("the password is printed", SNL, "   salted = SDEXT(pw :", "   crt pw\n   salted = SDEXT(pw :")
mut("the password is a message argument", SNL, "crt sysmsg(11477, name, ru)", "crt sysmsg(11477, name, pw)")
mut("the password is audited", SNL, "' remote=' : ru)", "' remote=' : ru : ' pw=' : pw)")
mut("the password is stored", SNL, "   rec<5> = srvr.key\n", "   rec<5> = srvr.key\n   rec<6> = pw\n")
mut("the password is kept after the derivation", SNL, "   pw = ''\n   if salted = '' then", "   if salted = '' then")
mut("give.up keeps the password", SNL, "   pw = ''\n   salted = ''\n   client.key = ''", "   salted = ''\n   client.key = ''")
mut("give.up keeps the server key", SNL, "   srvr.key = ''\n   expect.v = ''\n   proof = ''\n   rec = ''", "   expect.v = ''\n   proof = ''\n   rec = ''")
mut("give.up leaves the socket open", SNL, "   if skt.open then\n      close.socket skt\n      skt.open = @false\n   end\n   @system.return.code = -ER$FAILED", "   @system.return.code = -ER$FAILED")
mut("a key is a message argument", SNL, "fail.num = 11476 ; fail.a1 = 'the proof'", "fail.num = 11476 ; fail.a1 = client.key")
mut("the server key is displayed", SNL, "   srvr.key = SDEXT(salted : @FM : 'Server Key', @TRUE, SD_HMACSHA256)\n", "   srvr.key = SDEXT(salted : @FM : 'Server Key', @TRUE, SD_HMACSHA256)\n   display srvr.key\n")
mut("the login is written before the signature is checked", SNL, "   salted = SDEXT(pw :", "   call $netcred('WRITE', name, rec, pin, err)\n   salted = SDEXT(pw :")
mut("a failure writes", SNL, "   rec = ''\n   if skt.open then", "   call $netcred('WRITE', name, rec, pin, err)\n   rec = ''\n   if skt.open then")
mut("a failure deletes the old login", SNL, "   rec = ''\n   if skt.open then", "   call $netcred('DELETE', name, rec, pin, err)\n   rec = ''\n   if skt.open then")
mut("a refusal stops outside give.up", SNL, "      fail.num = 11475\n      gosub give.up\n", "      stop sysmsg(11475)\n")
mut("the server's text is not a failure", SNL, "   fail.num = 11474 ; fail.a1 = reason\n", "   crt reason\n   fail.num = 11474 ; fail.a1 = reason\n   return\n")
mut("the record carries the pin", SNL, "   rec<5> = srvr.key\n", "   rec<5> = srvr.key\n   rec<6> = pin\n")
mut("the record is not cleared first", SNL, "   rec = ''\n   rec<1> = ru\n", "   rec<1> = ru\n")
mut("the audit line is in upper case", SNL, "'set.netlogin server='", "'SET.NETLOGIN server='")
mut("the audit line carries the pin", SNL, "' remote=' : ru)", "' remote=' : ru : ' pin=' : pin)")
mut("the audit line is written before the login is stored", SNL,
    lambda t: t.replace("   void kernel(K$AUDIT, 'set.netlogin server=' : name : ' remote=' : ru)\n", "", 1).replace("   call $netcred('WRITE'", "   void kernel(K$AUDIT, 'set.netlogin server=' : name : ' remote=' : ru)\n   call $netcred('WRITE'", 1))
mut("a second audit line is written", SNL, "   @system.return.code = 0\n   crt sysmsg(11477", "   void kernel(K$AUDIT, 'set.netlogin done')\n   @system.return.code = 0\n   crt sysmsg(11477")
mut("success is not exit 0", SNL, "   @system.return.code = 0\n   crt sysmsg(11477", "   @system.return.code = -ER$FAILED\n   crt sysmsg(11477")
# Y: delete.netlogin
mut("delete.netlogin is not internal", DNL, "$internal\nprogram delete.netlogin", "program delete.netlogin")
mut("delete.netlogin asks for the NET gate", DNL, lambda t: t.replace("   words = trim(@sentence)\n", "   if not(kernel(K$NET, -1)) then stop\n   words = trim(@sentence)\n", 1))
mut("delete.netlogin asks for the administrator", DNL, lambda t: t.replace("   words = trim(@sentence)\n", "   if not(kernel(K$ADMINISTRATOR, -1)) then stop\n   words = trim(@sentence)\n", 1))
mut("delete.netlogin does not ask if there is one", DNL, "call $netcred('EXISTS', name, rec, '', err)", "rec = 1")
mut("delete.netlogin does not validate the name", DNL, "len(name) < 1 or len(name) > 16 or not(chk.ok) or index(lc.set, name[1, 1], 1) = 0", "len(name) < 1")
mut("delete.netlogin reads the login", DNL, "call $netcred('DELETE', name, rec, '', err)", "call $netcred('READ', name, rec, '', err)")
mut("delete.netlogin audits in upper case", DNL, "'delete.netlogin server='", "'DELETE.NETLOGIN server='")
mut("delete.netlogin audits the password", DNL, "'delete.netlogin server=' : name)", "'delete.netlogin server=' : name : ' pw=' : rec)")
mut("delete.netlogin audits before the delete", DNL,
    lambda t: t.replace("   void kernel(K$AUDIT, 'delete.netlogin server=' : name)\n", "", 1).replace("   call $netcred('DELETE'", "   void kernel(K$AUDIT, 'delete.netlogin server=' : name)\n   call $netcred('DELETE'", 1))
mut("delete.netlogin prompts", DNL, lambda t: t.replace("   words = trim(@sentence)\n", "   input zz\n   words = trim(@sentence)\n", 1))
# V: the VOC entries
mut("set.netlogin is not in newvoc", "newvoc.list", lambda t: t.replace("set.netlogin", "", 1))
mut("delete.netlogin is not in newvoc", "newvoc.list", lambda t: t.replace("delete.netlogin", "", 1))
mut("the template entry names another program", "voc:set.netlogin", "$setnetlogin", "$setnetlogon")
mut("the template entry of delete.netlogin is a paragraph", "voc:delete.netlogin", "V\n", "PA\n")
mut("the newvoc entry names another program", "newvoc:set.netlogin", "$setnetlogin", "$deletenetlogin")
mut("the newvoc entry is not a catalogued verb", "newvoc:delete.netlogin", "CA", "BA")
# H: the messages
mut("message 11450 is missing", "msg:11450", lambda t: None)
mut("message 11460 is empty", "msg:11460", lambda t: "")
mut("message 11464 takes two lines", "msg:11464", lambda t: t.rstrip("\n") + "\nsecond line\n")
mut("11464 stops saying the password is not stored", "msg:11464", lambda t: t.replace("Your password is used once here and is not stored", "Your password is used here", 1))
mut("11477 says the password is stored", "msg:11477", lambda t: t.replace("The password is not stored", "The password is stored", 1))
mut("11471 stops saying nothing was sent", "msg:11471", lambda t: t.replace("Nothing was sent to it and nothing was stored", "Nothing was stored", 1))
mut("11460 names the gate in upper case", "msg:11460", lambda t: t.replace("net-on", "NET-ON", 1))
mut("11455 stops telling the person what to do", "msg:11455", lambda t: t.replace("Run set.netlogin %1 again", "Try later", 1))
mut("11454 stops saying nothing was used", "msg:11454", lambda t: t.replace("Nothing was used", "Used", 1))
mut("message 11475 stops saying nothing was stored", "msg:11475", lambda t: t.replace("Nothing was stored", "", 1))
mut("message 11469 has a place the call does not fill", "msg:11469", lambda t: t.rstrip("\n") + " %5\n")
mut("11466 is never used", SNL, "display sysmsg(11466)", "display sysmsg(11465)")
mut("11479 is never used", SNL, "fail.num = 11479", "fail.num = 11473")
mut("11471 loses its third argument", SNL, "fail.num = 11471 ; fail.a1 = host ; fail.a2 = port ; fail.a3 = name", "fail.num = 11471 ; fail.a1 = host ; fail.a2 = port")
mut("11477 loses its second argument", SNL, "crt sysmsg(11477, name, ru)", "crt sysmsg(11477, name)")
mut("11454 loses its path", NCR, after("case act = 'READ'", "err = 11454:@vm:server:@vm:path", "err = 11454:@vm:server"))
mut("11457 loses its status", NCR, "err = 11457:@vm:server:@vm:path:@vm:status()", "err = 11457:@vm:server:@vm:path")
mut("$netcred gives a message number outside the block", NCR, "err = 11455:@vm:server", "err = 11499:@vm:server")
# E: the helper and the sudoers line
mut("the helper's root is another directory", "sd-elevate", "SD_NET_ROOT_REAL=/var/lib/sd-net", "SD_NET_ROOT_REAL=/var/lib/sdnet")
mut("the sudoers line gives netcred-dir a wildcard", "sdcore.sudoers", "/usr/local/sbin/sd-elevate netcred-dir", "/usr/local/sbin/sd-elevate netcred-dir *")
mut("the sudoers line is lost", "sdcore.sudoers", ", /usr/local/sbin/sd-elevate netcred-dir", "")
mut("the sudoers line gives netcred-dir an argument", "sdcore.sudoers", "/usr/local/sbin/sd-elevate netcred-dir", "/usr/local/sbin/sd-elevate netcred-dir --dry-run")
# B5: nobody else asks the gate
mut("another program asks K$NET", "bp:cd", lambda t: t + "\n   x = kernel(K$NET, -1)\n")


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
