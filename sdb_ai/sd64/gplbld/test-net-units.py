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

17 Oct 26 dm  S.65 slice 2c: the SERVER side of a files-only login - a second, narrower API route.  Section W reads: !apifilesok (the one place that
decides, an ALLOW table of request numbers; the table parsed out of the source and run in Python for every number 0 to 80 with the account
entered and not, against a list written again in this file from the task, so a number wrong in either direction fails; 3 allowed once; an empty
or non-numeric action refused; the function pure), apisrvr (sdusers first, sdapi tried first and winning, sdfiles second, neither refused
exactly as before with 10073, both groups read with the three-valued status, sdsys exempt by name, the mark in the common block set once and
never cleared, the gate after the not-logged-in test and BEFORE the dispatch, audited, answering 11480), MODIFY.ACCOUNT / CREATE.ACCOUNT /
CREATEA / the manifest (route.files - NOT `files`, which is the backup's file count) / RESTORE.ACCOUNT, the installer and deletesdcore (the group
is made and removed), sd-elevate (the group is whitelisted, never deletable), and messages 11480 / 11482.  WHAT THIS CANNOT SAY: that a
files-only user logs in, that a request is refused on the wire or that the group changes - sandbox-net.py, section "files" (the table run by the
real compiled function; the words' syntax and their refusals), and an install for the rest (witness-release-run.sh).

17 Oct 26 dm  S.65 slice 3a: the BASIC client class gpl.bp/sdclient logs in from stored derived keys.  Section Z reads sdclient as text: connect.keys
(its parameters by value; every argument checked before open.socket; the socket opened with SKT$TLS and the 5 second connect timeout; THE PIN TESTED
BEFORE A BYTE IS SENT - nothing between the open and the comparison writes, reads or exchanges, and the comparison is of text ('p' : prefix) and not of
numbers; the Ack read bounded by io.ms; the exchange; the account entered and its refusal failing the call; the keys cleared after the exchange and on
every failure path, the socket closed), scram.exchange (the stored salt and count compared with the server's AFTER client-first and BEFORE the
client-final message, PBKDF2 only in the password branch, the spent keys dropped before the final message), scram.login as a one line wrapper, connect()
unchanged in kind (its Ack wait still unbounded, its open still without a timeout), the bounded reads of read.packet, settimeout, the three defines, no
secret in any error text, and the suite's wiring (regress.sh, regress-map.txt, the verdict line of sandbox-netfile.py, and every error text the suite
asserts being in the class).  WHAT THIS CANNOT SAY: that the class compiles, that obj->connect.keys parses, or that anything it checks happens at run
time - sandbox-netfile.py, against the fake in gplbld/netfake.py.

17 Oct 26 dm  S.65 slice 3b: the remote file handler gpl.bp/netfile ($netfile, operations in netfile.h).  Section N reads it as ORDER and as what it cannot
do: the 13 operation codes and the limits (NF1), the header (NF2), the checks of NF$OPEN in order with the gate asked by the handler itself and nothing dialled
before the audit line (NF3), the one way to the network (NF4), READ ONLY - no write, delete, create, lock or command, $netcred and !netdefs called with READ only, the
refused operations touching no connection (NF5), the gate in check.gate and again for every request (NF6), every request preceded by the no-reply mark, no retry
and no loop, the 30 second bound (NF7), the connections in the one named common block with no secret in it (NF8), exactly two audit lines and no secret in any message
argument (NF9), messages 11490-11506 (NF10), and the suite and the map (NF11, NF12).  B5 now counts the handler as one asker of K$NET.  WHAT THIS CANNOT SAY: that the
handler compiles, that an object stays in common, or that any of it happens - sandbox-netfile.py, sections handler, readonly, refuse, lost and timeout.

17 Oct 26 dm  S.65 slice 3c: the KERNEL half of remote files - the NET_FILE file variable type (descr.h 4), netfiles.c, the VOC pointer type N, open_file(), and the
refusal of every other statement.  Section NK reads the C and BASIC as ORDER: the type, the union member and the limits agreeing across C, BASIC and the messages (NK1); the nine
functions defined once, with one prototype everywhere (NK2); net_open_work in the order shape - GATE - audit - handler, the gate asking the session and NEVER exempting an $internal program,
the handler found and called BY NAME (NK3); net_refuse running no BASIC, net_close sending only for a CLOSE statement and queueing every other release, net_stale and the epoch, the NET_FILE made last
and only on success (NK4); _voc_ref's N case and check.n.pointer, with the C parse of the encoded form (NK5); open_file recognising the encoded path inside the OPEN-by-name block before fullpath and
the file table, and dio_close / op_close (NK6); THE CENSUS - each of the 31 sites the 17 Oct census says REFUSE (27 since slice 3d took SELECT, SELECTV and both INDICES out) calls net_refuse (or refuse_net_file) behind a NET_FILE test and before the first
read or write of the file table, a lock, a select list or an edit-gate decision; the guards on the file table's readers; READV and FILEINFO answered before the file table (NK7); and a scan that
FAILS when a new kernel function is given a file variable and nobody has decided what it does with a remote one (NK8); messages 11507 / 11508, the Makefile list, the suite and the map, the history
lines (NK9-NK12).  WHAT THIS CANNOT SAY: that anything compiles (make is the compiler), that a statement is refused, that ON ERROR runs, or what reaches the wire - the section kernel of
sandbox-netfile.py, whose refusal matrix runs about 40 statements against the fake server and requires its packet log to hold nothing but login, account, open, read, close and quit.

17 Oct 26 dm  S.65 slice 3d: SELECT and SELECTV of a remote file, the dictionary of one, and three FILEINFO keys.  SELECT, SELECTV and both INDICES leave the refusal census (NK7 now counts 27 sites; INDICES of a remote file is the null string, NK18): NK13
reads net_select (through net_op with NF_SELECT, net_raise only from the statement's own ON ERROR, *ids and *count set only on success, the field marks counted), NK14 op_select (the ids asked
of the server BEFORE end_select and clear_select, so an error leaves the target list alone, then store_select_list), NK15 op_selectv (the target found again from the e-stack after the call,
because the handler runs BASIC; @SELECTED set; list 11 never used), NK16 op_fileinfo (FL_TYPE FL_TYPE_NET, FL_COLLECTION 0 and FL_FLAGS the NOCASE bit for an $internal program only, all before
any FPtr; the value 7 in both keys.h files) and NK17 the DICT form (_voc_ref adds 'dict ' only for fno 3 and only after the shape check; the file name buffer and the length test hold the 5 more
characters).  NK5 and NK5b were rewritten for it.  WHAT THIS CANNOT SAY: that a remote SELECT returns the server's ids or that a dictionary opens - sandbox-netfile.py.

***AND THE CHECKS ARE THEMSELVES CHECKED.***  --selftest breaks each invariant in the way an edit plausibly would and requires some
check to notice.  A mutant that nothing catches is reported as a FAILURE of the self-test.
"""

import fnmatch
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

NK_C = ("netfiles.c", "descr.h", "sd.h", "op_dio1.c", "op_dio2.c", "op_dio3.c", "op_dio4.c", "op_lock.c", "dh_ak.c", "dh_misc.c", "analyse.c", "k_error.c", "pdump.c")   # slice 3c
C_FILES = ("keys.h", "sysseg.h", "op_kernel.c", "sd_tls.c", "sd_tls.h", "op_skt.c", "op_sdext.c") + NK_C
MAIN_BP = ("login", "cproc", "apisrvr", "modifya", "createa", "create_account", "acc_os_info", "restorea",
           "netdefs", "setserver", "deleteserver", "listservers", "netcred", "setnetlogin", "deletenetlogin", "bcomp", "apifilesok", "netfile")
VERBS = (("set.server", "setserver", "$setserver"), ("delete.server", "deleteserver", "$deleteserver"),
         ("list.servers", "listservers", "$listservers"))
NL_VERBS = (("set.netlogin", "setnetlogin", "$setnetlogin"), ("delete.netlogin", "deletenetlogin", "$deletenetlogin"))   # slice 2b: in newvoc AND voc_template
MSG_FIRST, MSG_LAST = 11411, 11446      # 11411-11439 slice 1, 11440-11446 slice 2a (CONNECT); 11447-11449 are free
NL_MSG_FIRST, NL_MSG_LAST = 11450, 11479    # slice 2b: the person's login (the whole block is this slice's)
NF_MSG_FIRST, NF_MSG_LAST, NF_MSG_USED = 11490, 11519, 11506    # slice 3b: the remote file handler's block; 11490-11506 are written and used by the handler
NF_MSG_KERNEL = (11507, 11508)                                  # slice 3c: the kernel's own two (netfiles.c); 11509-11519 are kept free
LINUX_BLOCK = (11000, 11999)
SH_FILES = ("installsdcore.sh", "deletesdcore.sh", "sd-elevate", "sdcore.sudoers", "regress.sh", "regress-map.txt")      # shell-style comments (#)


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
    if name in C_FILES or name.startswith("c:"):
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
    get("gpl.src", os.path.join(SD64, "gpl.src"))                            # slice 3c: the list the Makefile builds from
    for fname in sorted(os.listdir(GPLSRC)):                                  # slice 3c: every other kernel source that is given a file variable (the census scan)
        if fname.endswith(".c") and fname not in srcs:
            with open(os.path.join(GPLSRC, fname), encoding="utf-8", errors="replace") as f:
                text = f.read()
            if "k_get_file(" in text or "data.fvar" in text:
                srcs["c:" + fname] = text
    get("int$keys.h", os.path.join(GPL, "int$keys.h"))
    get("syscom/keys.h", os.path.join(SDSYS, "syscom", "keys.h"))
    get("createacc.h", os.path.join(SDSYS, "syscom", "createacc.h"))
    get("installsdcore.sh", os.path.join(ROOT, "installsdcore.sh"))
    get("deletesdcore.sh", os.path.join(ROOT, "deletesdcore.sh"))
    get("sd-elevate", os.path.join(HERE, "sd-elevate"))
    get("sdcore.sudoers", os.path.join(HERE, "sdcore.sudoers"))
    get("regress.sh", os.path.join(HERE, "regress.sh"))                    # slice 3a: the netfile suite is wired in
    get("regress-map.txt", os.path.join(HERE, "regress-map.txt"))
    get("sandbox-netfile.py", os.path.join(HERE, "sandbox-netfile.py"))
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
    for n in (2001, 2018, 6000, 10024, 10080, 10081, 10087, 11480, 11481, 11482):      # 11480-11482: slice 2c (11481 is not used; read only to be sure)
        p = os.path.join(MSGDIR, str(n))
        srcs["msg:%d" % n] = open(p, encoding="utf-8", errors="replace").read() if os.path.exists(p) else None
    for n in range(NF_MSG_FIRST, NF_MSG_LAST + 1):                                      # slice 3b: the handler's block
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
    ck("B5 no program but LOGIN (1), CPROC (3), the API server (1), set.netlogin (1) and the remote file handler netfile (1) mentions K$NET - the last two only ASK: K$NET, -1 (see U2, NF6)",
       sites == {"login": 1, "cproc": 3, "apisrvr": 1, "setnetlogin": 1, "netfile": 1}, repr(sites))
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
    i = tc.find("void sd_tls_client_end(SD_TLS_CLIENT* c) {")
    eb = tc[i:tc.find("\n}\n", i)] if i >= 0 else ""
    ck("C3c sd_tls_client_end holds SIGPIPE off around SSL_shutdown (the close_notify write ended the whole process when the peer had already closed the "
       "connection): the signal is blocked, and consumed only if it was not already pending, BEFORE the mask is put back",
       eb != "" and ordered(eb, "pthread_sigmask(SIG_BLOCK", "SSL_shutdown(c->ssl)", "sigtimedwait(", "pthread_sigmask(SIG_SETMASK")
       and "was_pending" in eb and "SSL_free(c->ssl)" in eb, "")
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
    checks_2c(srcs, c, ck)
    checks_3a(srcs, c, ck)
    checks_3b(srcs, c, ck)
    checks_3c(srcs, c, ck)
    checks_3d(srcs, c, ck)
    checks_3e(srcs, c, ck)
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


# ---- W. S.65 slice 2c: the files-only route -----------------------------------------------------------------------------------------------
# The request numbers a files-only session may make, WRITTEN OUT HERE from the owner's list and not read from the program: 1 quit, 2 get error text,
# 4 open, 5 close, 6-10 the reads, 11 select, 12 readnext, 13 clearselect, 14 readlist, 15 release, 16-19 write / writeu / delete / deleteu, 26
# selectindex (a select, so allowed), 30-34 the locks, 35-36 indices, 37-39 the select lists, 40 fileinfo, 41 readv, 42-45 the left / right pair,
# 46 mark mapping, 49 revision.  3 (set account) is allowed ONCE and is not in this tuple.  Everything else - 0, 20-25, 27-29, 47, 48, 50 and
# up - is refused.
FILES_ALLOWED = (1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 26,
                 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 49)


def files_ok_table(text):
    """What apifilesok builds: the string it starts from (files.ok = '..') and the pieces appended to it (files.ok := '..')."""
    m = re.search(r"^files\.ok = '([^']*)'[ \t]*$", text, re.M)
    return (m.group(1) if m else None), re.findall(r"^files\.ok := '([^']*)'[ \t]*$", text, re.M)


def files_ok_model(allow, action, entered):
    """What !apifilesok answers, run in Python on the table read from its source: empty is 0, not a number is 0, 3 is 0 once entered and 1
    before, anything else is 1 only if ',N,' is in the table.  (The source is held to exactly these tests, in this order, by W2.)"""
    if action == "":
        return 0
    if not re.fullmatch(r"[+-]?(?:\d+\.?\d*|\.\d+)", action):
        return 0
    if float(action) == 3:
        return 0 if entered else 1
    return 1 if ("," + action + ",") in allow else 0


def want_files_ok(n, entered):
    if n == 3:
        return 0 if entered else 1
    return 1 if n in FILES_ALLOWED else 0


def checks_2c(srcs, c, ck):
    """S.65 slice 2c: the files-only route, the group sdfiles."""
    fo, ap = c["apifilesok"], c["apisrvr"]
    mo, cr, ca2, ai, rs = c["modifya"], c["createa"], c["create_account"], c["acc_os_info"], c["restorea"]
    inst, dele, se = c["installsdcore.sh"], c["deletesdcore.sh"], c["sd-elevate"]
    bps = {n[3:]: t for n, t in c.items() if n.startswith("bp:")}

    # ---- W1-W3. !apifilesok -----------------------------------------------------------------------------------------------------------
    init, parts = files_ok_table(fo)
    allow = (init or "") + "".join(parts)
    nums = [int(x) for p in parts for x in p.split(",") if x != ""]
    wrong = [(e, n, files_ok_model(allow, str(n), e), want_files_ok(n, e)) for e in (0, 1) for n in range(0, 81)
             if files_ok_model(allow, str(n), e) != want_files_ok(n, e)]
    ck("W1 !apifilesok, the table read from its source and run for EVERY request number 0 to 80, the account entered and not, agrees with the list "
       "written out in this file (a number wrong in either direction fails); the table holds exactly those 37 numbers once each, 3 is NOT in it "
       "(it is allowed once, by its own test) and the table starts from ','",
       init == "," and not wrong and sorted(nums) == sorted(FILES_ALLOWED) and 3 not in nums and len(FILES_ALLOWED) == 37, repr((init, wrong[:6], sorted(set(nums) ^ set(FILES_ALLOWED)))))
    odd = [a for a in ("", "abc", "-1", "1000", "81", "70", "4x", "x4", "3x") if files_ok_model(allow, a, 0) or files_ok_model(allow, a, 1)]
    ck("W2 ...and the tests after the table are exactly these, in this order: an empty action is 0, a non-number is 0, 3 is 0 when entered and 1 before, "
       "a number is 1 only if ',N,' (commas on both sides, so 4 cannot match 49 or 14) is in the table, and the default is 0 (fail closed)",
       not odd and re.search(r"if action = '' then return 0\s*\n\s*if not\(num\(action\)\) then return 0\s*\n\s*if action = 3 then\s*\n\s*if entered then return 0\s*\n"
                             r"\s*return 1\s*\n\s*end\s*\n\s*if index\(files\.ok, ',' : action : ',', 1\) then return 1\s*\n\s*return 0\s*\n\s*end\s*$", fo) is not None
       and ordered(fo, "files.ok := ", "if action = '' then return 0"), repr(odd))
    ck("W3 ...it is a $internal function catalogued once as !apifilesok, and it is PURE: no read, no write, no open, no kernel call, no execute, no prompt - "
       "a sandbox asks it about every number and the server asks it about every request",
       "$internal" in fo and re.search(r"^function apifilesok\(action, entered\)\s*$", fo, re.M) is not None and re.search(r"^\$catalog !apifilesok\s*$", fo, re.M) is not None
       and len([n for n, t in bps.items() if "$catalog !apifilesok" in t]) == 1
       and not re.search(r"\b(?:kernel|read|readv|readu|readt|open|openseq|openpath|write|writeu|writev|writeseq|delete|execute|os\.execute|select|readnext|input|crt|display|print|call|gosub|goto|void)\b", strip_strings(fo)), "")

    # ---- W4-W12. apisrvr -------------------------------------------------------------------------------------------------------------
    cm_i = ap.find("common /$APISRVR/")
    cm = ap[cm_i:ap.find("seq.unbuf(SEQ.MAX)", cm_i)] if cm_i >= 0 else ""
    fi = ap.find("\nvb.scram.final:")
    fin = ap[fi:] if fi >= 0 else ""
    ck("W4 apisrvr declares !apifilesok, keeps the files-only mark in the COMMON block /$APISRVR/ (a plain variable is set afresh by a runtime abort "
       "while logged.in survives it, which would hand a files-only login the whole API) and starts it false ONCE, in the first-time block beside master.login.done",
       re.search(r"^deffun apifilesok\(action, entered\) calling '!apifilesok'\s*$", ap, re.M) is not None and re.search(r"^files\.only,", cm, re.M) is not None
       and ap.count("files.only = @false") == 1
       and ordered(ap, "if not(kernel(K$CPROC.LEVEL,0)) then", "master.login.done = @false", "files.only = @false", 'openpath "voc" to voc else'), "")
    others = [n for n, t in bps.items() if n != "apisrvr" and re.search(r"\bfiles\.only\b", t)]
    ck("W5 the mark is SET ONCE and NEVER CLEARED: exactly two assignments to files.only in the whole tree (the initialisation and the one `= @true`), the true one "
       "inside `if api.files.login then`, in vb.scram.final after K$ASSUME.USER and before logged.in, and no other program mentions it",
       len(re.findall(r"\bfiles\.only\s*=(?!=)", ap)) == 2 and ap.count("files.only = @true") == 1 and not others
       and re.search(r"if api\.files\.login then\s*\n\s*files\.only = @true\s*\n", fin) is not None
       and ordered(fin, "kernel(K$ASSUME.USER, scram.user)", "if api.files.login then", "files.only = @true", "logged.in = @true"), repr(others))
    ck("W6 THE ORDER OF THE ROUTE: sdusers first, then sdapi, then sdfiles, then the identity is assumed, then the mark - each group read ONCE, by scram.user (the name "
       "just proven)",
       ordered(fin, "is_grp_member(scram.user, 'sdusers')", "is_grp_member(scram.user, 'sdapi')", "is_grp_member(scram.user, 'sdfiles')", "kernel(K$ASSUME.USER, scram.user)",
               "files.only = @true", "logged.in = @true")
       and all(fin.count("is_grp_member(scram.user, '%s')" % g_) == 1 for g_ in ("sdusers", "sdapi", "sdfiles"))
       and ap.count("is_grp_member(scram.user, 'sdfiles')") == 1, "")
    ck("W7 sdapi is tried first and WINS: the sdfiles read is inside `if not(api.in.sdapi) then`, api.files.login starts false before it and is set true only after the "
       "sdfiles test passed (once in the tree)",
       ordered(fin, "api.files.login = @false", "api.in.sdapi = is_grp_member(scram.user, 'sdapi')", "if not(api.in.sdapi) then", "api.in.sdfiles = is_grp_member(scram.user, 'sdfiles')",
               "if not(api.in.sdfiles) then", "api.files.login = @true")
       and ap.count("api.files.login = @true") == 1 and ap.count("api.files.login = @false") == 1, "")
    ck("W8 SDSYS IS EXEMPT BY NAME from both groups (one test, downcased, round the reading of both, before the first of them)",
       re.search(r"if not\(downcase\(scram\.user\) = 'sdsys'\) then\s*\n\s*api\.in\.sdapi = is_grp_member", fin) is not None
       and ordered(fin, "if not(downcase(scram.user) = 'sdsys') then", "api.in.sdapi = is_grp_member", "api.in.sdfiles = is_grp_member", "api.files.login = @true", "logged.in = @true"), "")
    ck("W9 BOTH groups are read with the three-valued status and neither is collapsed: a lookup that could not answer refuses (10073) with its own reason, for sdapi and for sdfiles",
       re.search(r"api\.in\.sdapi = is_grp_member\(scram\.user, 'sdapi'\)\s*\n\s*api\.route\.stat = status\(\)\s*\n\s*if api\.route\.stat # 0 then\s*\n"
                 r"\s*scram\.refuse\.reason = 'the sdapi route could not be read, status ' : api\.route\.stat\s*\n\s*abort\.message = sysmsg\(10073, scram\.user\)\s*\n"
                 r"\s*server\.error = SV\$ON\.ERROR\s*\n\s*goto exit\.vb\.scram\.fail", fin) is not None
       and re.search(r"api\.in\.sdfiles = is_grp_member\(scram\.user, 'sdfiles'\)\s*\n\s*api\.files\.stat = status\(\)\s*\n\s*if api\.files\.stat # 0 then\s*\n"
                     r"\s*scram\.refuse\.reason = 'the sdfiles route could not be read, status ' : api\.files\.stat\s*\n\s*abort\.message = sysmsg\(10073, scram\.user\)\s*\n"
                     r"\s*server\.error = SV\$ON\.ERROR\s*\n\s*goto exit\.vb\.scram\.fail", fin) is not None, "")
    ck("W10 a user in NEITHER group is refused EXACTLY as before: the same reason ('not a member of sdapi'), the same message 10073, the same exit; and a user not in sdusers "
       "is still refused first with 5009",
       re.search(r"if not\(api\.in\.sdfiles\) then\s*\n\s*scram\.refuse\.reason = 'not a member of sdapi'\s*\n\s*abort\.message = sysmsg\(10073, scram\.user\)\s*\n"
                 r"\s*server\.error = SV\$ON\.ERROR\s*\n\s*goto exit\.vb\.scram\.fail", fin) is not None
       and re.search(r"if not\(is_grp_member\(scram\.user, 'sdusers'\)\) then\s*\n\s*scram\.refuse\.reason = 'not a member of sdusers'\s*\n\s*abort\.message = sysmsg\(5009\)", fin) is not None, "")
    gi = ap.find("if files.only then")
    gb = ap[gi:ap.find("cproc.date = date()", gi)] if gi >= 0 else ""
    nl_ = ap.find("abort.message = sysmsg(5270)")
    dsp = ap.find("on action + 1 gosub")
    ck("W11 THE GATE: one `if files.only then`, after the not-logged-in test (5270) and BEFORE cproc.date and the dispatch table, so no request goes round it; "
       "it asks !apifilesok with master.login.done as `entered`; a refusal is audited, is an error answer (SV$ON.ERROR), says 11480 with the request number, and "
       "goes to return.status.set - the reply is written and the dispatch is skipped",
       ap.count("if files.only then") == 1 and 0 <= nl_ < gi < ap.find("cproc.date = date()") < dsp
       and "if not(apifilesok(action, master.login.done)) then" in gb
       and re.search(r"void kernel\(K\$AUDIT, 'api refused request=' : action : ' route=sdfiles user=' : @logname\)", gb) is not None
       and ordered(gb, "kernel(K$AUDIT", "server.error = SV$ON.ERROR", "abort.message = sysmsg(11480, action)", "st = status()", "goto return.status.set")
       and ap.count("apifilesok(") == 2 and "\nreturn.status.set:" in ap and ap.find("\nreturn.status.set:") > dsp, "")
    ck("W12 'entered' is real: master.login.done is set true exactly once, at the first successful entry (vb.account), after the first-time `if not(master.login.done)` "
       "tests; a request 3 is therefore allowed until then and refused after; and the audit words are lower case: api login route=sdfiles user=, api refused request=",
       ap.count("master.login.done = @true") == 1 and ordered(ap, "if not(master.login.done) then\n   void kernel(K$VOC.EDIT", "master.login.done = @true")
       and "void kernel(K$AUDIT, 'api login route=sdfiles user=' : scram.user)" in fin and "'api refused request='" in ap, "")

    # ---- W13-W15. the messages ---------------------------------------------------------------------------------------------------------
    m80, m82 = srcs.get("msg:11480"), srcs.get("msg:11482")
    cited = {}
    for n_, t_ in bps.items():
        for num_, args_ in sysmsg_calls(t_):
            if 11480 <= num_ <= 11489:
                cited.setdefault(num_, []).append((n_, len(args_)))
    stray = sorted({int(x) for t_ in bps.values() for x in re.findall(r"\b(1148\d)\b", t_)} - {11480, 11482})
    ck("W13 message 11480 and 11482 exist, one line each, inside the Linux block, with the wording the logins and the verbs rely on: 11480 'This login is for files only: request %1 "
       "is not allowed', 11482 'Account %1 has FILES %2'",
       m80 is not None and m82 is not None and m80.strip() == "This login is for files only: request %1 is not allowed" and m82.strip() == "Account %1 has FILES %2"
       and "\n" not in m80.rstrip("\n") and "\n" not in m82.rstrip("\n") and LINUX_BLOCK[0] <= 11480 <= 11489 <= LINUX_BLOCK[1], repr((m80, m82)))
    ck("W14 11480 is cited only by apisrvr with ONE argument (the request number); 11482 only by MODIFY.ACCOUNT and CREATE.ACCOUNT with TWO (the account, yes or no); "
       "no program cites 11481 or 11483 to 11489, or writes such a number any other way (the block 11480-11489 is this slice's and only 11480 and 11482 are used)",
       sorted(cited.get(11480, [])) == [("apisrvr", 1)] and sorted(cited.get(11482, [])) == [("create_account", 2), ("modifya", 2)] and set(cited) <= {11480, 11482} and not stray, repr((cited, stray)))
    ck("W15 nothing is said on a successful files-only login: the login path prints nothing in vb.scram.final (no crt, display or print between the mark and logged.in)",
       not re.search(r"\b(?:crt|display|print)\b", fin[fin.find("if api.files.login then"):fin.find("logged.in = @true", fin.find("if api.files.login then"))]), "")

    # ---- W16-W22. the words: MODIFY.ACCOUNT, CREATE.ACCOUNT, CREATEA ----------------------------------------------------------------------
    sf = routine_body(mo, "set.files")
    ck("W16 MODIFY.ACCOUNT: FILES-ON and FILES-OFF are words (files.want true / false, set.files, stop), in the syntax lines and in the list of words; sdapi and sdssh are not "
       "touched by set.files",
       all(re.search(r"case action = '%s'\s*\n\s*files\.want = @%s\s*\n\s*gosub set\.files\s*\n\s*stop" % (w, b), mo) for w, b in (("FILES-ON", "true"), ("FILES-OFF", "false")))
       and "modify.account <account> files-on | files-off" in mo and "files-on, files-off, suspended or unsuspended" in mo
       and sf != "" and "sdapi" not in sf and "sdssh" not in sf, "")
    ck("W17 set.files refuses what has no Linux user BEFORE it runs anything: a group account (10087) and any other account that is not sdu_ (10081, status 2), then the "
       "name is checked with valid_os_name; the Linux user is the one the account's group names (the manifest reads the same)",
       ordered(sf, "if group.name[1,4] # 'sdu_' then", "sysmsg(10087, acc.name)", "sysmsg(10081, acc.name, 2)", "files.user = group.name[5,999]", "valid_os_name(files.user)", "os.execute")
       and sf.count("os.execute") == 2, "")
    ck("W18 ...membership is read three-valued (status read at once, a lookup that cannot answer changes NOTHING and says 10081 with the status); FILES-ON also needs sdusers "
       "(else status 2 - the login would refuse them first); FILES-OFF is never gated on sdusers",
       re.search(r"has\.files = is_grp_member\(files\.user, 'sdfiles'\)\s*\n\s*files\.stat = status\(\)\s*\n\s*if files\.stat = 0 and files\.want then\s*\n"
                 r"\s*in\.sdusers = is_grp_member\(files\.user, 'sdusers'\)\s*\n\s*files\.stat = status\(\)\s*\n\s*if files\.stat = 0 and not\(in\.sdusers\) then files\.stat = 2\s*\n"
                 r"\s*end\s*\n\s*if files\.stat # 0 then\s*\n\s*@system\.return\.code = -ER\$FAILED\s*\n\s*crt sysmsg\(10081, acc\.name, files\.stat\)\s*\n\s*return", sf) is not None
       and ordered(sf, "if files.stat # 0 then", "if has.files = files.want then", "sysmsg(10080, acc.name)", "os.execute"), "")
    ck("W19 ...already in the wanted state is 10080 and nothing is run; FILES-ON when the group sdfiles does not exist is 10024 and nothing is run; the change is the SAME "
       "helper and verbs the api word uses (sd-elevate addgroup / delgroup <user> sdfiles)",
       ordered(sf, "if has.files = files.want then", "sysmsg(10080, acc.name)", "return", "files.found = is_group('sdfiles')", "sysmsg(10024, 'sdfiles')", "os.execute")
       and re.search(r'os\.execute "sudo /usr/local/sbin/sd-elevate addgroup " : files\.user : " sdfiles"', sf) is not None
       and re.search(r'os\.execute "sudo /usr/local/sbin/sd-elevate delgroup " : files\.user : " sdfiles"', sf) is not None
       and ordered(sf, "files.found = is_group('sdfiles')", 'addgroup " : files.user', 'delgroup " : files.user'), "")
    ck("W20 ...after the change the membership is READ BACK from /etc/group, a read back that does not show the wanted state is a failure (10081, status 2), the audit line "
       "(lower case) comes only after it, and the line printed (11482) is the read-back value and not the request",
       re.search(r"files\.stat = OS\.ERROR\(\)\s*\n\s*if files\.stat = 0 then\s*\n\s*now\.files = is_grp_member\(files\.user, 'sdfiles'\)\s*\n\s*files\.stat = status\(\)\s*\n"
                 r"\s*if files\.stat = 0 and now\.files # files\.want then files\.stat = 2\s*\n\s*end\s*\n\s*if files\.stat # 0 then\s*\n\s*@system\.return\.code = -ER\$FAILED\s*\n"
                 r"\s*crt sysmsg\(10081, acc\.name, files\.stat\)\s*\n\s*return\s*\n\s*end\s*\n\s*@system\.return\.code = 0\s*\n"
                 r"\s*void kernel\(K\$AUDIT, 'modify\.account ' : downcase\(action\) : ' account=' : acc\.name\)\s*\n"
                 r"\s*crt sysmsg\(11482, acc\.name, if now\.files then 'yes' else 'no'\)", sf) is not None, "")
    ck("W21 CREATEA: the word FILES-ON sets CA$FILES = 1 (and nothing sets it to anything else), the syntax line names {files-on} and the text says what it is",
       re.search(r"case upcase\(token\) = 'FILES-ON'\s*\n\s*settings<CA\$FILES> = 1\s*\n", cr) is not None and len(re.findall(r"settings<CA\$FILES>\s*=", cr)) == 1
       and "{net-on} {files-on} {no.query}" in cr and "(files-on)" in cr, "")
    ck("W21b createacc.h defines CA$FILES as 36 right after CA$NET 35 (the compiler warns 'not assigned a value' and reads 0 errors without it: test-includes-units.py), "
       "and no register field is added - the membership of the group IS the state",
       re.search(r"\$define\s+CA\$FILES\s+36\b", c["createacc.h"]) is not None and re.search(r"\$define\s+CA\$NET\s+35\b", c["createacc.h"]) is not None
       and "ACC$FILES" not in c["syscom/keys.h"],
       "createacc.h has no  $define CA$FILES 36")
    ck("W22 CREATE.ACCOUNT: a request is exactly CA$FILES = 1; the group is looked for BEFORE the Linux user is made (a missing group is 10024 and creates nothing, an unreadable "
       "/etc/group is 10081); a GROUP account (10087) and an OTHER account (10081, status 2) are refused before anything is created",
       "files.want = (settings<CA$FILES> = 1)" in ca2
       and ordered(ca2, "files.found = is_group('sdfiles')", "err = 10081:@vm:acc.uname:@vm:files.stat", "err = 10024:@vm:'sdfiles'", "if not(create_user(acc.uname)) then")
       and re.search(r"if files\.want then\s*\n\s*files\.found = is_group\('sdfiles'\)\s*\n\s*files\.stat = status\(\)\s*\n\s*if files\.stat # 0 then\s*\n"
                     r"\s*@system\.return\.code = -ER\$FAILED\s*\n\s*err = 10081:@vm:acc\.uname:@vm:files\.stat\s*\n\s*goto exit\.create\s*\n\s*end\s*\n"
                     r"\s*if not\(files\.found\) then\s*\n\s*@system\.return\.code = -ER\$FAILED\s*\n\s*err = 10024:@vm:'sdfiles'\s*\n\s*goto exit\.create", ca2) is not None
       and re.search(r"case acc\.type = 'GROUP'.*?if files\.want then\s*\n\s*@system\.return\.code = -ER\$ARGS\s*\n\s*err = 10087:@vm:acc\.name\s*\n\s*goto exit\.create.*?case acc\.type = 'OTHER'.*?"
                     r"if files\.want then\s*\n\s*@system\.return\.code = -ER\$ARGS\s*\n\s*err = 10081:@vm:acc\.name:@vm:2\s*\n\s*goto exit\.create", ca2.replace('"', "'"), re.S) is not None, "")
    ck("W23 ...the join is sd-elevate addgroup <user> sdfiles, only when asked, AFTER the sdssh and sdapi joins; a failed join is 10081 with its status and the account stops; "
       "and a user account is told its state (11482), read off /etc/group, right after the NET line",
       re.search(r'if files\.want then\s*\n\s*os\.execute "sudo /usr/local/sbin/sd-elevate addgroup ":acc\.uname:" sdfiles"\s*\n\s*route\.stat = OS\.ERROR\(\)\s*\n\s*if route\.stat # 0 then\s*\n'
                 r'\s*@system\.return\.code = -ER\$FAILED\s*\n\s*err = 10081:@vm:acc\.uname:@vm:route\.stat\s*\n\s*goto exit\.create', ca2) is not None
       and ordered(ca2, 'addgroup ":acc.uname:" sdssh"', 'addgroup ":acc.uname:" sdapi"', 'addgroup ":acc.uname:" sdfiles"')
       and re.search(r"crt sysmsg\(11411, acc\.name, acc\.rec<ACC\$NET>\)\s*\n\s*crt sysmsg\(11482, acc\.name, if is_grp_member\(acc\.uname, 'sdfiles'\) then 'yes' else 'no'\)", ca2) is not None, "")

    # ---- W24-W26. the manifest and the restore -------------------------------------------------------------------------------------------
    ck("W24 the account manifest carries `route.files: 1|0` for a USER account, read from membership of sdfiles, after route.api and before os.sh, and before the GROUP branch; "
       "the key is NOT `files` - the backup writes `files: N` (the file count) into the same section and RESTORE.ACCOUNT reads it as that count",
       ordered(ai, "'route.api: '", "'route.files: ':(if is_grp_member(user, 'sdfiles') then 1 else 0)", "'os.sh: '", "case grp[1,4] = 'sdg_'")
       and "'files: '" not in ai and ai.count("route.files") == 1 and "'files: ':files" in c["bp:backupa"] and re.search(r"= 'files'\s*; m\.files = kv", rs) is not None, "")
    ck("W25 RESTORE.ACCOUNT reads route.files, clears it for each section, hands it on as CA$FILES (a manifest without the key restores as NOT in the group), and still reads "
       "`files` as the count",
       re.search(r"= 'route\.files'\s*; m\.route\.files = kv", rs) is not None and "settings<CA$FILES> = m.route.files" in rs and "m.net = '' ; m.route.files = ''" in rs
       and re.search(r"= 'files'\s*; m\.files = kv", rs) is not None, "")

    # ---- W26-W28. the group: installer, deletesdcore, sd-elevate ----------------------------------------------------------------------------
    ck("W26 the installer makes sdfiles beside sdssh and sdapi: one loop `for sd_route_group in sdssh sdapi sdfiles`, groupadd --system, only when the group is missing",
       inst.count("for sd_route_group in") == 1
       and re.search(r'for sd_route_group in sdssh sdapi sdfiles; do\s*\n\s*if ! getent group "\$sd_route_group" &>/dev/null; then\s*\n(?:[^\n]*\n){0,2}?\s*sudo groupadd --system "\$sd_route_group"', inst) is not None, "")
    li = dele.find("for sd_route_group in sdssh sdapi sdfiles; do")
    br = dele.rfind('if [ "$keep_accts" = "DELETE" ]; then', 0, li) if li >= 0 else -1
    el = dele.find("\nelse\n", li) if li >= 0 else -1
    fi_ = dele.find("\nfi", el) if el >= 0 else -1
    ck("W27 deletesdcore removes it with the others ONLY on a full DELETE (the loop and its groupdel inside the DELETE branch, no end of branch between them) and says it kept it "
       "when the accounts are kept (in the else branch)",
       dele.count("for sd_route_group in") == 1 and 0 <= br < li < el and "\nfi" not in dele[br:li] and 'sudo groupdel "$sd_route_group"' in dele[li:el]
       and "route groups sdssh, sdapi and sdfiles were kept" in dele[el:el + 200] and fi_ > el and "groupdel" not in dele[el:fi_], "")
    ck("W28 sd-elevate whitelists sdfiles by its exact name for addgroup, delgroup and groupadd (require_sd_group), says so in its refusal text, and never deletes it with groupdel "
       "(it is one of the system groups)",
       re.search(r"case \$group in\s*\n\s*sdusers\|sdssh\|sdapi\|sdfiles\) : ;;\s*\n\s*sdu_\?\*\|sdg_\?\*\) : ;;", se) is not None
       and "(want sdusers, sdssh, sdapi, sdfiles, sdu_*, or sdg_*)" in se
       and re.search(r"case \$1 in\s*\n\s*sdusers\|sdssh\|sdapi\|sdfiles\)\s*\n\s*die \"'\$1' is one of SD's system groups and is never deleted here\"", se) is not None
       and "sdfiles*" not in se, "")


# ---- Z. S.65 slice 3a: gpl.bp/sdclient logs in from the stored derived keys -------------------------------------------------------------------

# Every error text sandbox-netfile.py asserts of the class, written out here once: each must be in sdclient AND in the suite, so that a text changed in
# one and not the other is found by a free check and not by a red row in a suite that takes minutes.
CLIENT_TEXTS = ("A connection has already been established", "Invalid host name", "Invalid user name", "Invalid public key pin",
                "The stored login is incomplete", "The stored iteration count is not a whole number", "The stored iteration count is unacceptable",
                "PIN MISMATCH: the public key of", "is not the key pinned in its definition; nothing was sent",
                "No acknowledgement from", "at the start of the session", "during the login (the connection failed or timed out)",
                "Server signature did not verify", "Server did not return a signature",
                "Server nonce does not extend the client nonce", "Malformed server-first message", "Server sent a non-numeric iteration count",
                "Server asked for an unacceptable iteration count", "The TLS handshake with ", " did not complete (status ", "Cannot connect to ",
                "The server's salt is not the stored one: the stored login is out of date or this is not the server it was made with",
                "The server's iteration count is not the stored one: the stored login is out of date or this is not the server it was made with")


def between(text, start, end):
    i = text.find(start)
    j = text.find(end, i + 1) if i >= 0 else -1
    return text[i:j] if i >= 0 and j >= 0 else ""


def checks_3a(srcs, c, ck):
    """S.65 slice 3a: connect.keys, scram.exchange, settimeout and the wiring of the netfile suite."""
    sc = c["bp:sdclient"]
    raw = srcs["bp:sdclient"]
    kb = between(sc, "public function connect.keys(", "public subroutine settimeout(")
    cb = between(sc, "public function connect(host", "public function connect.keys(")
    ex = between(sc, "local function scram.exchange(", "local function evaluate.packet(")
    rp = between(sc, "local function read.packet()", "local subroutine disconnect.session")
    pre_pin = kb[:kb.find("('p' : spki)")] if "('p' : spki)" in kb else kb
    keys_branch = between(ex, "if keys.mode then", "end else")

    # ---- Z1. the shape
    ck("Z1 connect.keys is a public function, once, whose secret parameters are BY VALUE (port, salt, iterations, client.key, server.key, pin: the copies are cleared here and the "
       "caller's variables are the caller's); settimeout is a public subroutine; the class lists both in its description",
       sc.count("public function connect.keys(host, (port), username, (salt), (iterations), (client.key), (server.key), account, (pin))") == 1
       and sc.count("public subroutine settimeout(ms)") == 1 and "bool = obj->connect.keys(host, port, username, salt, iterations, client.key, server.key, account, pin)" in raw
       and "obj->settimeout(ms)" in raw, "")

    # ---- Z2. the order
    ck("Z2 connect.keys, in this ORDER: a connected object refused, the host, the user name, the pin's shape, an incomplete login, the count a whole number and within the bounds, the "
       "one open.socket, the key hash, the pin compared, the Ack read, the exchange, the account entered, the context set last",
       ordered(kb, "context # CX.DISCONNECTED", "len(host) = 0", "valid_os_name(username)", "pin = downcase(trim(pin))", "'The stored login is incomplete'",
               "iterations matches '1N0N'", "iterations < SCRAM$MIN.ITER or iterations > SCRAM$MAX.ITER", "open.socket(", "socket.info(skt, SKT$INFO.TLS.SPKI)",
               "('p' : spki) # ('p' : pin)", "read.socket(skt, 1, SKT$BLOCKING, io.ms)", "scram.exchange(username, '', salt, iterations, client.key, server.key)",
               "message.pair(SrvrAccount, account)", "server.error # SV$OK", "context = CX.CONNECTED"), "")
    ck("Z2a ...each shape check refuses with ITS OWN text and returns false (a connected object, an empty host, a user name !valid_os_name refuses, a pin that is not 64 hex digits, "
       "a login with ANY of salt, ClientKey and ServerKey null, a count that is not 1 to 8 digits, a count outside the bounds)",
       all(re.search(p, kb) is not None for p in (
           r"if context # CX\.DISCONNECTED then\s*\n\s*error = 'A connection has already been established'\s*\n\s*return @false",
           r"if len\(host\) = 0 then\s*\n\s*error = 'Invalid host name'\s*\n\s*return @false",
           r"if not\(valid_os_name\(username\)\) then\s*\n\s*error = 'Invalid user name'\s*\n\s*return @false",
           r"if len\(pin\) # 64 or len\(convert\('0123456789abcdef', '', pin\)\) # 0 then\s*\n\s*error = 'Invalid public key pin'\s*\n\s*return @false",
           r"if salt = '' or client\.key = '' or server\.key = '' then\s*\n\s*error = 'The stored login is incomplete'\s*\n\s*return @false",
           r"if len\(iterations\) < 1 or len\(iterations\) > 8 or not\(iterations matches '1N0N'\) then\s*\n\s*error = 'The stored iteration count is not a whole number'\s*\n\s*return @false",
           r"if iterations < SCRAM\$MIN\.ITER or iterations > SCRAM\$MAX\.ITER then\s*\n\s*error = 'The stored iteration count is unacceptable'\s*\n\s*return @false")), "")
    ck("Z3 ...the shape checks are all BEFORE the socket is opened (no network is touched for a bad argument), the socket is opened once, with SKT$TLS and the 5 second connect timeout",
       kb.count("open.socket(") == 1 and re.search(r"skt = open\.socket\(host, port, SKT\$BLOCKING \+ SKT\$TLS, NET\.CONNECT\.SECS\)", kb) is not None
       and not re.search(r"socket|SDEXT|message\.pair", kb[:kb.find("open.socket(")]), "")
    ck("Z4 ...NOTHING IS SENT BEFORE THE PIN IS CHECKED: between the open and the comparison of the key hash there is no write, no read, no packet, no exchange and no disconnect "
       "(the only thing done is SOCKET.INFO); the comparison is of TEXT - each side has a letter in front, because two all-digit strings would be compared as numbers - and a mismatch "
       "and a missing hash both leave through keys.fail, naming a PIN MISMATCH and saying nothing was sent",
       "('p' : spki)" in kb and not re.search(r"write\.packet|write\.socket|message\.pair|read\.socket|read\.packet|scram\.|disconnect|SrvrQuit|SDEXT", pre_pin)
       and re.search(r"if \('p' : spki\) # \('p' : pin\) then\s*\n\s*error = 'PIN MISMATCH: the public key of ' : host : ':' : port : ' is not the key pinned in its definition; nothing was sent'\s*\n\s*goto keys\.fail\s*\n\s*end", kb) is not None
       and re.search(r"if spki = '' then\s*\n\s*error = '[^']*nothing was sent'\s*\n\s*goto keys\.fail", kb) is not None
       and not re.search(r"if spki # pin|if pin # spki", kb), "")
    ck("Z5 ...the Ack is awaited with the BOUNDED read (io.ms, a byte at a time, a limited number of tries), and the exchange is entered only after it; connect.keys sets the bound to "
       "NET.READ.MS only when it is still 0, so that settimeout() called first wins",
       re.search(r"if io\.ms = 0 then io\.ms = NET\.READ\.MS", kb) is not None and ordered(kb, "if io.ms = 0 then io.ms = NET.READ.MS", "tries += 1", "read.socket(skt, 1, SKT$BLOCKING, io.ms)",
                                                                                         "until acked or tries >= NET.ACK.TRIES", "scram.exchange(") and kb.count("read.socket(") == 1, "")
    ck("Z6 ...the keys are dropped the moment the exchange has returned (client.key and server.key set to null before the result is tested), and on EVERY failure path through keys.fail, which "
       "also closes the socket and returns false; every failure after the open goes through it; a refusal of the account fails the call",
       ordered(kb, "ok = scram.exchange(", "client.key = ''", "server.key = ''", "if not(ok) then")
       and re.search(r"\nkeys\.fail:\s*\n\s*client\.key = ''\s*\n\s*server\.key = ''\s*\n\s*close\.socket skt\s*\n\s*return @false\s*\nend", kb) is not None
       and len(re.findall(r"goto keys\.fail", kb)) == 7 and kb[kb.find("spki = downcase"):].count("return @false") == 1
       and re.search(r"if server\.error # SV\$OK then\s*\n\s*error = 'The server did not enter the account'\s*\n\s*goto keys\.fail", kb) is not None, "")

    # ---- Z7-Z9. the exchange, shared by both logins
    ck("Z7 scram.exchange in the stored-key mode (keys.mode: a stored ClientKey was given): AFTER client-first and BEFORE client-final, the server's salt is compared with the stored one "
       "as TEXT and its count as a NUMBER with the stored count, each mismatch ending the exchange with its own text and the stored keys dropped; the nonce and the iteration bounds are "
       "tested before either; the stored keys become the working keys only after both compares",
       ordered(ex, "keys.mode = (stored.ck # '')", "message.pair(SrvrScramFirst", "nonce[1,len(cnonce)] # cnonce", "iter < SCRAM$MIN.ITER or iter > SCRAM$MAX.ITER", "if keys.mode then",
               "if ('s' : salt) # ('s' : stored.salt) then", "if iter + 0 # stored.iter + 0 then", "client.key = stored.ck", "srvr.key = stored.sk", "end else", "message.pair(SrvrScramFinal")
       and "stored." not in re.sub(r"keys\.mode = \(stored\.ck # ''\)", "", ex[ex.find("keys.mode = (stored.ck"):ex.find("message.pair(SrvrScramFirst")]) and "keys.mode" not in ex[:ex.find("keys.mode = (")]
       and re.search(r"if \('s' : salt\) # \('s' : stored\.salt\) then\s*\n\s*error = \"The server's salt is not the stored one[^\"]*\"\s*\n\s*stored\.ck = '' ; stored\.sk = ''\s*\n\s*return @false\s*\n\s*end", ex) is not None
       and re.search(r"if iter \+ 0 # stored\.iter \+ 0 then\s*\n\s*error = \"The server's iteration count is not the stored one[^\"]*\"\s*\n\s*stored\.ck = '' ; stored\.sk = ''\s*\n\s*return @false\s*\n\s*end", ex) is not None, "")
    ck("Z8 ...PBKDF2 (the password) is used only in the password branch: once in the whole exchange, after the stored-key branch, and the stored-key branch uses no SDEXT of it; the proof "
       "and the server's signature are computed from client.key and srvr.key either way, and the working keys, the stored key and the client signature are dropped before the final message "
       "is sent; the server's v= is compared in constant time",
       ex.count("SD_PBKDF2") == 1 and "SD_PBKDF2" not in keys_branch and ex.find("SD_PBKDF2") > ex.find("end else")
       and ordered(ex, "stored.key = SDEXT(client.key", "client.sig = SDEXT(", "proof = SDEXT(", "expect.v = SDEXT(srvr.key", "client.key = ''", "srvr.key = ''", "stored.key = ''", "client.sig = ''",
                   "message.pair(SrvrScramFinal", "in.pkt[1,2] # 'v='", "SD_CTEQUAL") and "stored.ck" not in ex[ex.find("end else"):], "")
    ck("Z9 scram.login is the ONE LINE `return scram.exchange(username, password, '', '', '', '')` and nothing else (a null stored ClientKey is the password mode), declared once; connect() "
       "calls it and calls neither connect.keys nor scram.exchange",
       re.search(r"local function scram\.login\(username, password\)\s*\n\s*return scram\.exchange\(username, password, '', '', '', ''\)\s*\nend", sc) is not None
       and sc.count("local function scram.login(") == 1 and sc.count("deffun scram.login(username, password) local") == 1
       and sc.count("deffun scram.exchange(username, password, stored.salt, stored.iter, stored.ck, stored.sk) local") == 1
       and cb.count("scram.login(username, password)") == 1 and "scram.exchange" not in cb and "connect.keys" not in cb, "")

    # ---- Z10. connect() is the same kind of function it was
    ck("Z10 connect() is UNCHANGED IN KIND: its Ack wait still reads with the timeout 0 (it waits for ever, as before), its socket is still opened with no timeout argument, it enters the "
       "account as before (no check of the reply), and it asks no pin",
       "read.socket(skt, 1, SKT$BLOCKING, 0) = char(6)" in cb and re.search(r"skt = open\.socket\(host, port, SKT\$BLOCKING \+ SKT\$TLS\)\s*\n", cb) is not None
       and "io.ms" not in cb and "SPKI" not in cb and re.search(r"\bpin\b", cb) is None and ordered(cb, "scram.login(username, password)", "message.pair(SrvrAccount, account)", "context = CX.CONNECTED"), "")
    ck("Z11 the bounded read: read.packet reads the header and the data with io.ms (both of its read.socket calls, and no literal 0 timeout is left in it); create.object starts io.ms at 0 so "
       "that connect() still waits for ever; settimeout accepts only a number of 0 or more (it aborts 'Illegal timeout') and sets io.ms; io.ms is a private variable",
       len(re.findall(r"read\.socket\(skt, n, SKT\$BLOCKING, io\.ms\)", rp)) == 2 and not re.search(r"read\.socket\([^)]*, 0\)", rp)
       and re.search(r"public subroutine create\.object\s*\n(?:[^\n]*\n){0,6}?\s*io\.ms = 0\s*\nend", sc) is not None
       and re.search(r"public subroutine settimeout\(ms\)\s*\n\s*if not\(num\(ms\)\) or ms < 0 then abort 'Illegal timeout'\s*\n\s*io\.ms = ms \+ 0\s*\nend", sc) is not None
       and re.search(r"private context,[^\n]*\n(?:[^\n]*\n){0,4}?\s*io\.ms\b", sc) is not None, "")
    dv = {m.group(1): int(m.group(2)) for m in re.finditer(r"\$define (NET\.[A-Z.]+)\s+(\d+)", sc)}
    ck("Z12 the three defines: NET.CONNECT.SECS 5 (the plan's connect timeout), NET.READ.MS 30000 (a read), NET.ACK.TRIES 16", dv == {"NET.CONNECT.SECS": 5, "NET.READ.MS": 30000, "NET.ACK.TRIES": 16}, repr(dv))

    # ---- Z13. nothing secret in a message
    leak = [ln.strip() for ln in strip_strings(sc).split("\n") if re.search(r"\berror\s*=", ln) and re.search(
        r"\b(client\.key|server\.key|stored\.ck|stored\.sk|srvr\.key|salted|proof|stored\.key|expect\.v|auth\.msg|client\.sig|cbind|cnonce)\b", ln)]
    shown = [ln.strip() for ln in (kb + "\n" + ex).split("\n") if re.search(r"\b(display|crt|print)\b", ln)]
    ck("Z13 no error text carries a key, a proof, a signature or the binding (no `error =` line names one), and neither connect.keys nor scram.exchange displays anything",
       not leak and not shown, repr((leak[:3], shown[:3])))

    # ---- Z14. every text the suite asserts is the class's, and the suite is wired in
    suite = srcs["sandbox-netfile.py"]
    miss = [t for t in CLIENT_TEXTS if t not in raw or t not in suite]
    ck("Z14 every error text sandbox-netfile.py asserts of the class (%d of them) is in sdclient and in the suite, word for word" % len(CLIENT_TEXTS), not miss, repr(miss[:4]))
    al = re.search(r'^ALL_SUITES="([^"]*)"', c["regress.sh"], re.M)
    names = al.group(1).split() if al else []
    rm = c["regress-map.txt"]
    ck("Z15 the suite is wired in: `netfile` is in regress.sh's ALL_SUITES once, gplbld/sandbox-netfile.py is its own suite in the map, and the map selects it for sdclient, netdefs, netcred, "
       "setnetlogin and netfake.py; the suite file prints the verdict line regress.sh reads and builds with --build",
       names.count("netfile") == 1 and re.search(r"^gplbld/sandbox-netfile\.py\s*:\s*@self\s*$", rm, re.M) is not None
       and all(re.search(r"^%s\s*:[^\n]*\bnetfile\b" % re.escape(p), rm, re.M) is not None
               for p in ("sdsys/gpl.bp/sdclient", "sdsys/gpl.bp/netdefs", "sdsys/gpl.bp/netcred", "sdsys/gpl.bp/setnetlogin", "gplbld/netfake.py"))
       and 'say("sandbox-netfile: %d passed, %d failed" % (passed, failed))' in suite and '"--build" in sys.argv' in suite, repr(names[-3:]))
    ck("Z16 the dated history lines are there: sdclient (`17 Oct 26 dm S.65 slice 3a`), and the suite's own",
       "17 Oct 26 dm S.65 slice 3a" in raw and "17 Oct 26 dm  New.  S.65 slice 3a" in suite, "")


# ---- N. S.65 slice 3b: gpl.bp/netfile, the handler for every operation on a remote file ---------------------------------------------------------

NF_OPS = {"NF$OPEN": 1, "NF$CLOSE": 2, "NF$READ": 3, "NF$READV": 4, "NF$RECORDLOCKED": 5, "NF$SELECT": 6, "NF$FILEINFO": 7, "NF$CLOSEALL": 8,
          "NF$WRITE": 9, "NF$DELETE": 10, "NF$CLEARFILE": 11, "NF$LOCK": 12, "NF$STATE": 13}
NF_DEFS = dict(NF_OPS, **{"NF$RC.OK": 0, "NF$RC.ELSE": 2, "NF$RC.ERROR": 3, "NF$MAX.SERVERS": 10, "NF$MAX.HANDLES": 100})
NF_REASONS = ("gate", "server", "list", "credential", "limit", "file")
NF_METHODS = {"connect.keys", "settimeout", "open", "close", "read", "select", "readlist", "recordlocked", "disconnect", "error", "ServerStatus"}
NF_SECRET_LOCALS = r"\b(cred|ruser|rsalt|riter|rck|rsk|pin|pw|password)\b"
NF_SUITE_SECTIONS = ("handler", "readonly", "refuse", "lost", "timeout", "gaps")
NF_FORBIDDEN = (r"(?<![\w.$])(write|writeu|writev|writevu|writeseq|writeblk|weofseq|delete|deleteu|deleteseq|create|openseq|openpath|osrename|osdelete|"
                r"execute|perform|sh|logto|clearfile|recordlock|release|mkdir|chdir)(?![\w.$])")


def checks_3b(srcs, c, ck):
    """S.65 slice 3b: the handler $netfile, as ORDER and as what it cannot do.  Nothing here runs it: the sections handler, readonly, refuse, lost and
    timeout of sandbox-netfile.py do, against the fake server."""
    nf, nfh, raw, rawh = c["bp:netfile"], c["bp:netfile.h"], srcs["bp:netfile"], srcs["bp:netfile.h"]
    suite, rm = srcs["sandbox-netfile.py"], c["regress-map.txt"]
    ns = strip_strings(nf)
    main = nf[:nf.find("\nact.open:")] if "\nact.open:" in nf else nf
    body = {lab: routine_body(nf, lab) for lab in ("act.open", "act.close", "act.read", "act.recordlocked", "act.select", "act.fileinfo", "act.closeall", "act.refuse",
                                                   "act.state", "get.handle", "check.gate", "check.id", "connect.new", "shape.names", "after.rq", "lost.fail", "drop.conn",
                                                   "refuse", "fail", "idle.release")}
    ao, gh = body["act.open"], body["get.handle"]

    # ---- N1. the numbers the kernel slice will mirror
    got = {m.group(1): int(m.group(2)) for m in re.finditer(r"\$define\s+(NF\$[A-Z.]+)\s+(-?\d+)", nfh)}
    ck("NF1 netfile.h: the 13 operation codes are 1 to 13 in this order (OPEN CLOSE READ READV RECORDLOCKED SELECT FILEINFO CLOSEALL WRITE DELETE CLEARFILE LOCK STATE), the results are "
       "NF$RC.OK 0, ELSE 2, ERROR 3, the limits are 10 servers and 100 files, and no name or number is defined twice (the kernel slice mirrors these in C)",
       got == NF_DEFS and len(re.findall(r"\$define\s+NF\$", nfh)) == len(NF_DEFS) and len(set(got[k] for k in NF_OPS)) == 13, repr({k: v for k, v in got.items() if NF_DEFS.get(k) != v}))
    ck("NF2 netfile is an internal subroutine `netfile(op, a, b, c, out, rc)` catalogued as $netfile (only an internal program can call a dollar name), and includes netfile.h",
       re.match(r"\s*\$internal\s*\nsubroutine netfile\(op, a, b, c, out, rc\)\s*\n\$catalog \$netfile\s*\n", nf) is not None and "$include netfile.h" in nf
       and nf.count("$catalog") == 1 and nf.count("subroutine ") == 1, "")

    # ---- N3. the order of the checks on NF$OPEN, every one before anything is dialled
    ai = ao.find("void kernel(K$AUDIT, 'netfile open server='")
    pre = ao[:ai] if ai >= 0 else ao
    ck("NF3 NF$OPEN, in this ORDER: the name shapes (no side effect), THE GATE (administrator or K$NET), the definition read (!netdefs READ) and its fields, the accounts list (the administrator "
       "exempt), the stored login ($netcred READ), the limits (10 servers, 100 files), the file name - then the audit line, and only then the connection and the open",
       ordered(ao, "gosub shape.names", "gosub check.gate", "call !netdefs('READ'", "gosub check.def", "if not(is.admin) then", "index(',':downcase(accts):','", "call $netcred('READ'",
               "gosub find.slot", "ns >= NF$MAX.SERVERS", "nh >= NF$MAX.HANDLES", "if not(fname.ok) then", "void kernel(K$AUDIT, 'netfile open server='", "gosub connect.new", "obj->open(fname)"), "")
    ck("NF3a ...NOTHING IS DIALLED BEFORE THE AUDIT LINE: before it there is no connect.new, no object(), no connect.keys and no `->` call of the class",
       ai >= 0 and not re.search(r"connect\.new|object\(|connect\.keys|->", pre), repr(re.findall(r"connect\.new|object\(|connect\.keys|->[\w.]+", pre)))
    ck("NF3b ...every refusal of NF$OPEN is `gosub refuse` followed by a return (six reasons: gate, server, list, credential, limit, file - each used), the reason a literal word, and the audit "
       "names the server only as the lower cased name that passed its shape test or the word invalid, never the bytes typed",
       len(re.findall(r"gosub refuse\s*\n\s*return", ao)) == ao.count("gosub refuse") >= 8
       and sorted(set(re.findall(r"refused\.why = '(\w+)'", ao))) == sorted(NF_REASONS)
       and re.search(r"safe = 'invalid'\s*\n\s*if name\.ok then safe = srv", ao) is not None
       and ordered(body["refuse"], "gosub fail", "void kernel(K$AUDIT, 'netfile refused server=' : safe : ' reason=' : refused.why)"), "")
    ck("NF3c ...the administrator is exempt from the accounts list but from nothing else the gate asks (the list test is inside `if not(is.admin)`), and the account compared is the lower cased @who",
       re.search(r"if not\(is\.admin\) then\s*\n\s*if index\(',':downcase\(accts\):',', ',':acc:',', 1\) = 0 then", ao) is not None and "acc = downcase(@who)" in main, "")

    # ---- N4. the one way to the network
    cn = body["connect.new"]
    ck("NF4 the network is reached in ONE place: object('!sdclient') once and obj->connect.keys once, both in connect.new, which has NO password login (no ->connect, no open.socket or any socket "
       "verb of its own, no SDEXT), and connect.new is called from act.open only",
       nf.count("object('!sdclient')") == 1 and nf.count("connect.keys(") == 1 and "object('!sdclient')" in cn and "obj->connect.keys(" in cn
       and not re.search(r"->connect\(|open\.socket|read\.socket|write\.socket|SDEXT", nf) and nf.count("gosub connect.new") == 1 and "gosub connect.new" in ao, "")
    ck("NF4a connect.new copies the five values out of the credential, CLEARS the credential before the object is made, calls connect.keys with them and the definition's host, port, remote "
       "account and pin, clears each copy at once, sets the 30 second read bound, and only then puts the object in common (and refuses if it did not stay an object)",
       ordered(cn, "ruser = cred<1>", "rsalt = cred<2>", "riter = cred<3>", "rck = cred<4>", "rsk = cred<5>", "cred = ''", "obj = object('!sdclient')",
               "obj->connect.keys(host, port, ruser, rsalt, riter, rck, rsk, racct, pin)", "ruser = ''", "rsalt = ''", "riter = ''", "rck = ''", "rsk = ''",
               "obj->settimeout(NF$REQUEST.MS)", "nf.s.obj(slot) = obj", "vartype(nf.s.obj(slot)) # V$OBJ"), "")
    meth = set(re.findall(r"->([A-Za-z.]+)", nf))
    ck("NF4b the handler calls only these methods and properties of the class: connect.keys, settimeout, open, close, read, select, readlist, recordlocked, disconnect, error, ServerStatus "
       "(no write, delete, lock, execute, call, logto, sequential-file or password login method)", meth <= NF_METHODS, repr(sorted(meth - NF_METHODS)))

    # ---- N5. nothing is written to the remote server, nothing is stored
    ck("NF5 READ ONLY: no statement of netfile writes, deletes, creates, opens a file, runs a command or releases a lock; $netcred is called with 'READ' only and !netdefs with 'READ' only; "
       "kernel() is called for K$AUDIT, and for K$ADMINISTRATOR and K$NET with -1 only; nothing is shown (no crt, print or display)",
       not re.search(NF_FORBIDDEN, re.sub(r"->[\w.]+", "", ns), re.I) and re.findall(r"call \$netcred\('(\w+)'", nf) == ["READ"] and re.findall(r"call !netdefs\('(\w+)'", nf) == ["READ"]
       and all(m.group(1) == "K$AUDIT" or (m.group(1) in ("K$ADMINISTRATOR", "K$NET") and m.group(2).strip() == "-1") for m in re.finditer(r"kernel\((K\$[A-Z.]+)\s*,\s*([^)\n]*)", nf))
       and not re.search(r"(?<![\w.$])(crt|print|display)(?![\w.$])", ns), repr(re.findall(NF_FORBIDDEN, re.sub(r"->[\w.]+", "", ns), re.I)[:4]))
    ar = body["act.refuse"]
    ck("NF5a write, delete, clear.file and lock are ONE case that gosubs act.refuse, which asks for a handle of this account and answers 11501 naming the server and the operation - and "
       "touches no object, no connection and no request (the word obj is not in it)",
       re.search(r"case op = NF\$WRITE or op = NF\$DELETE or op = NF\$CLEARFILE or op = NF\$LOCK\s*\n\s*gosub act\.refuse", main) is not None
       and ordered(ar, "gosub get.handle", "'write'", "'delete'", "'clear.file'", "'lock'", "fail.num = 11501", "fail.a1 = srvname", "fail.a2 = opname", "gosub fail")
       and not re.search(r"\bobj\b|nf\.s\.obj|nf\.s\.state|connect|requests", ar), "")

    # ---- N6. the gate is asked by the handler itself, and only asked
    cg = body["check.gate"]
    ck("NF6 the handler asks the gate ITSELF (an internal program is exempt from the kernel's): check.gate is `is.admin = kernel(K$ADMINISTRATOR, -1)` and `kernel(K$NET, -1)` and nothing else, "
       "it is the only place either is mentioned, and it is gosubbed from NF$OPEN first of all and from get.handle",
       "is.admin = kernel(K$ADMINISTRATOR, -1)" in cg and re.search(r"if not\(is\.admin\) and not\(kernel\(K\$NET, -1\)\) then gate\.ok = @false", cg) is not None
       and nf.count("kernel(K$NET") == 1 and nf.count("kernel(K$ADMINISTRATOR") == 1 and nf.count("gosub check.gate") == 2, "")
    ck("NF6a ...every operation that sends a request asks it again through get.handle (need.gate = @true in read, readv, recordlocked, select and fileinfo), the gate test comes BEFORE the test that "
       "the handle belongs to this account, and a handle belongs to the account that opened it (stored lower case, compared with the lower cased @who)",
       all(re.match(r"act\.[a-z]+:\s*\n\s*need\.gate = @true", body[l]) for l in ("act.read", "act.recordlocked", "act.select", "act.fileinfo"))
       and ordered(gh, "if need.gate then", "gosub check.gate", "fail.num = 11460", "if not(any.acct) then", "nf.h.acct(hx) # acc", "fail.num = 11494")
       and "nf.h.acct(hx) = acc" in ao, "")

    # ---- N7. a request, a lost connection and no retry
    lines = [ln for ln in nf.split("\n") if ln.strip()]
    reqs = [i for i, ln in enumerate(lines) if re.search(r"obj->(open|close|read|select|readlist|recordlocked)\(", ln)]
    unmarked = [lines[i].strip() for i in reqs if not any("obj->ServerStatus = NF$NOREPLY" in p for p in lines[max(0, i - 3):i])]
    ck("NF7 EVERY request is preceded by the 'no reply' mark (obj->ServerStatus = NF$NOREPLY, three lines before at most): %d request sites, none unmarked; a reply of any kind overwrites it, "
       "so after.rq reads a mark still in place as a lost connection (rq.lost = ServerStatus < 0), and NF$NOREPLY is -1" % len(reqs),
       len(reqs) == 7 and not unmarked and "st = obj->ServerStatus" in body["after.rq"] and "rq.lost = (st < 0)" in body["after.rq"]
       and re.search(r"\$define NF\$NOREPLY\s+-1\b", nf) is not None, repr(unmarked))
    ck("NF7a a lost connection is dropped and reported, NEVER retried or reconnected inside an operation: lost.fail drops the connection then answers 11497; the only connect.new is in NF$OPEN; the "
       "handler holds no loop construct at all (no loop, no repeat, no while); drop.conn frees the slot and marks every handle on it lost (state 2)",
       ordered(body["lost.fail"], "gosub drop.conn", "fail.num = 11497") and "connect.new" not in body["lost.fail"] + body["drop.conn"]
       and not re.search(r"(?<![\w.$])(loop|repeat|while|goto)(?![\w.$])", ns) and "nf.h.state(hy) = 2" in body["drop.conn"]
       and ordered(body["drop.conn"], "nf.s.obj(slot) = 0", "nf.s.state(slot) = 0", "nf.h.state(hy) = 2"), "")
    ck("NF7b the 30 second request bound: NF$REQUEST.MS is 30000 and is given to the object once, in connect.new; a handle of a lost connection answers 11495 (not a new connection) and CLOSE of it frees "
       "it without a word (allow.lost)",
       re.search(r"\$define NF\$REQUEST\.MS\s+30000\b", nf) is not None and nf.count("settimeout(") == 1
       and ordered(gh, "if nf.h.state(hx) = 2 then", "if allow.lost then return", "fail.num = 11495")
       and re.search(r"act\.close:\s*\n\s*need\.gate = @false ; need\.conn = @false ; any\.acct = @true ; allow\.lost = @true", body["act.close"]) is not None, "")
    ck("NF7c CLOSEALL ends every connection and forgets every handle, is never refused (no gate, no list) and sends nothing but the quit that disconnect sends; STATE asks nothing and sends nothing",
       "obj->disconnect" in body["act.closeall"] and "gosub clear.handle" in body["act.closeall"] and not re.search(r"gate|kernel|obj->(open|read|select|close)", body["act.closeall"] + body["act.state"]), "")

    # ---- N8. the connection table: in named common, no secret in it
    cm = re.search(r"common\s+/\$netfile/[^\n]*(?:\n[ \t]+[^\n]*)*", nf)
    ck("NF8 the connections live in the named common block /$netfile/ (the only COMMON statement of the program), and the block holds no key, hash, pin, password, salt or credential by name",
       re.findall(r"common\s+/([^/]+)/", nf) == ["$netfile"] and cm is not None and not re.search(r"key|pin|pass|cred|hash|salt|secret", cm.group(0), re.I) and "nf.s.obj(NF$MAX.SERVERS)" in cm.group(0), "")

    # ---- N9. the audit trail and the messages carry nothing secret
    audits = re.findall(r"kernel\(K\$AUDIT,[^\n]*", nf)
    fails = re.findall(r"fail\.a\d = [^\n;]*", nf)
    ck("NF9 exactly two audit lines, both lower case with fixed words and values: `netfile open server=<name> file=<remote file>` and `netfile refused server=<name> reason=<word>`; no secret local "
       "(login, keys, salt, pin, password) is in an audit line or becomes an argument of a message",
       audits == ["kernel(K$AUDIT, 'netfile open server=' : srv : ' file=' : fname)", "kernel(K$AUDIT, 'netfile refused server=' : safe : ' reason=' : refused.why)"]
       and not any(re.search(NF_SECRET_LOCALS, a, re.I) for a in audits) and not any(re.search(NF_SECRET_LOCALS, f) for f in fails), repr((audits, [f for f in fails if re.search(NF_SECRET_LOCALS, f)])))
    ck("NF9a the shapes that guard the names: a server name is a lower case letter then up to 15 lower case letters or digits; a remote file name is letters, digits and . _ - $ up to MAX.ID.LEN with "
       "'dict ' in front for a dictionary - and no slash, so no pathname can be asked for",
       ordered(body["shape.names"], "chk.set = lc.set:digits", "len(srv) <= 16", "index(lc.set, srv[1, 1], 1)", "fname[1, 5] = 'dict '", "chk.set = lc.set:digits:'._-$'", "len(body) <= MAX.ID.LEN")
       and "'/'" not in body["shape.names"] and "/" not in re.sub(r"'[^']*'", "", body["shape.names"]), "")

    # ---- N10. the messages
    lits = {}
    for m in re.finditer(r"fail\.num = (\d+)([^\n]*)", nf):
        lits.setdefault(int(m.group(1)), []).append(len(re.findall(r"fail\.a\d = ", m.group(2))))
    block_used = {n for n in lits if NF_MSG_FIRST <= n <= NF_MSG_LAST}
    texts = {n: srcs.get("msg:%d" % n) for n in range(NF_MSG_FIRST, NF_MSG_LAST + 1)}
    places = {n: max([int(x) for x in re.findall(r"%(\d)", t)] or [0]) for n, t in texts.items() if t}
    ck("NF10 messages 11490 to 11506 all exist (one line each, inside the Linux block 11000-11999), all are used by netfile, 11507 and 11508 are the KERNEL's (slice 3c: netfiles.c, one line each, "
       "never used by netfile), 11509 to 11519 are kept free (no file, no use), and no other program of gpl.bp cites a number of the block",
       all(texts[n] is not None and texts[n].strip() != "" and "\n" not in texts[n].rstrip("\n") for n in range(NF_MSG_FIRST, NF_MSG_USED + 1))
       and all(texts[n] is not None and texts[n].strip() != "" and "\n" not in texts[n].rstrip("\n") for n in NF_MSG_KERNEL)
       and block_used == set(range(NF_MSG_FIRST, NF_MSG_USED + 1)) and all(texts[n] is None for n in range(NF_MSG_KERNEL[1] + 1, NF_MSG_LAST + 1))
       and LINUX_BLOCK[0] <= NF_MSG_FIRST and NF_MSG_LAST <= LINUX_BLOCK[1]
       and not [k for k, t in c.items() if k.startswith("bp:") and k not in ("bp:netfile", "bp:netfile.h") and re.search(r"\b115[01]\d\b|\b1149\d\b", t)],
       repr(sorted(set(range(NF_MSG_FIRST, NF_MSG_USED + 1)) ^ block_used)))
    short = [(n, k, places.get(n, 0)) for n, ks in lits.items() if n in places for k in ks if k < places.get(n, 0)]
    ck("NF10a each message has at most three %n places (rc carries three arguments), and every place a message has is given an argument at the line that raises it (11460, reused, gets two - its "
       "server is rc<4>, which the text does not print)",
       all(v <= 3 for v in places.values()) and not short and places.get(11497) == 2 and places.get(11500) == 3 and places.get(11494) == 1, repr(short))
    ck("NF10b the wording the suite relies on: 11494 names the handle, 11495 and 11497 and 11499 and 11500 name the server, 11497 says the connection was LOST during an operation and that nothing "
       "more is sent, 11501 says the file is read only and that nothing was sent, 11493 says 10 servers is the limit by its argument",
       all("%1" in (texts.get(n) or "") for n in (11493, 11494, 11495, 11496, 11497, 11498, 11499, 11500, 11501)) and "lost during" in (texts.get(11497) or "")
       and "Nothing more is sent" in (texts.get(11497) or "") and "read only" in (texts.get(11501) or "") and "Nothing was sent" in (texts.get(11501) or "")
       and "%1 servers" in (texts.get(11493) or ""), "")

    # ---- N11. the suite and the map
    drv = suite[suite.find("NFH_DRIVER = r"):suite.find("NFH_SUB = r")]
    k_errs = {int(x) for x in re.findall(r"k_err\((\d+)", suite)}
    ck("NF11 the suite sandbox-netfile.py drives EVERY operation by its NF$ name (13 names in the driver), compiles netcred, netfile and its two test programs, has the sections handler, readonly, "
       "refuse, lost, timeout and gaps, runs gaps only when it is named (it is red by design), and every message number it expects is a message of the tree",
       all(re.search(r"op = %s\b" % re.escape(k).replace(r"\$", "[$]"), drv) for k in NF_OPS)
       and "BASIC gpl.bp netcred netfile zznfh zznfhx" in suite and r"Compiled 4 program\(s\) with no errors" in suite
       and all('("%s", %s_section)' % (s, s) in suite for s in NF_SUITE_SECTIONS) and 'OPT_IN = ("gaps",)' in suite
       and "(sections is None and name not in OPT_IN)" in suite and k_errs and all(os.path.exists(os.path.join(MSGDIR, str(k))) for k in k_errs), repr(sorted(k_errs)))
    rules_ok = all(re.search(r"^%s\s*:[^\n]*\bnetfile\b" % re.escape(p), rm, re.M) is not None
                   for p in ("sdsys/gpl.bp/netfile", "sdsys/gpl.bp/netfile.h", "sdsys/messages/1149*", "sdsys/messages/1150*", "sdsys/messages/1151*"))
    def first(pat):
        m = re.search(r"^%s\s*:" % re.escape(pat), rm, re.M)
        return m.start() if m else 10 ** 9
    ck("NF12 regress-map.txt: the handler, its header and its messages select the netfile suite, and each rule comes BEFORE the coarse rule that would otherwise take the file (gpl.bp/*.h, gpl.bp/*, "
       "messages/* - the first rule that matches is the only one used)",
       rules_ok and first("sdsys/gpl.bp/netfile") < first("sdsys/gpl.bp/*.h") and first("sdsys/gpl.bp/netfile.h") < first("sdsys/gpl.bp/*.h") and first("sdsys/gpl.bp/netfile.h") < first("sdsys/gpl.bp/*")
       and first("sdsys/messages/1151*") < first("sdsys/messages/*"), "")
    ck("NF13 the dated history lines are there: netfile, netfile.h and the suite (`17 Oct 26 dm  S.65 slice 3b`), and this check's own file says so",
       "17 Oct 26 dm  S.65 slice 3b" in raw and "17 Oct 26 dm  S.65 slice 3b" in rawh and "17 Oct 26 dm  S.65 slice 3b" in suite and "S.65 slice 3b" in (__doc__ or ""), "")


# ---- NK. S.65 slice 3c: the kernel half - the NET_FILE type, netfiles.c, the VOC pointer, and the refusal of every other statement ----------------------

NK_FUNCS = ("net_path_is_net", "net_open", "net_close", "net_read", "net_readv", "net_fileinfo", "net_select", "net_refuse", "net_close_all", "net_message")   # net_select: slice 3d
NK_TYPES = {"DIRECTORY_FILE": 1, "DYNAMIC_FILE": 2, "SEQ_FILE": 3, "NET_FILE": 4}
# what a refusal must come before: the first of these in the function (a NET_FILE has no file table entry, so each of them reads or WRITES memory in front of the table)
NK_DANGER = ("FPtr(", "access.dh", "lock_record(", "unlock_record(", "check_lock(", "end_select(", "clear_select(", "log_permissions_error(", "edit_refusal(", "txn_read(", "k_recurse(")
# THE CENSUS OF 17 OCT 26 (49 opcode functions take a file variable): the sites it says REFUSE.  How: R = net_refuse() called directly after a NET_FILE test,
# H = refuse_net_file() (op_dio3.c: tests the type, refuses, sets the status).  The tuple is what, besides NK_DANGER, the refusal must come before.
NK_REFUSE = {
    ("op_dio1.c", "op_configfl"): ("R", ("FV_RDONLY",)),
    ("op_dio3.c", "read_record"): ("H", ()),
    ("op_dio3.c", "op_readv"): ("H", ()),
    ("op_dio3.c", "op_clrfile"): ("H", ("file_lock",)),
    ("op_dio3.c", "op_delete"): ("H", ()),
    ("op_dio3.c", "op_write"): ("H", ()),
    ("op_dio3.c", "op_writev"): ("H", ()),
    ("op_lock.c", "op_filelock"): ("R", ()),
    ("op_lock.c", "op_flunlock"): ("R", ()),
    ("op_lock.c", "op_getlocks"): ("R", ("descr->data.fvar->file_id",)),
    ("op_lock.c", "op_lockrec"): ("R", ()),
    ("op_lock.c", "op_reclckd"): ("R", ()),
    ("op_lock.c", "op_release"): ("R", ()),
    ("op_lock.c", "op_rlsfile"): ("R", ()),
    ("dh_ak.c", "op_akdelete"): ("R", ()),
    ("dh_ak.c", "op_akread"): ("R", ()),
    ("dh_ak.c", "op_akwrite"): ("R", ()),
    ("dh_ak.c", "op_akclear"): ("R", ()),
    ("dh_ak.c", "op_akenable"): ("R", ()),
    ("dh_ak.c", "op_akmap"): ("R", ()),
    ("dh_ak.c", "op_selindx"): ("R", ()),
    ("dh_ak.c", "op_selindxv"): ("R", ()),
    ("dh_ak.c", "akscan"): ("R", ()),
    ("dh_ak.c", "setakpos"): ("R", ()),
    ("dh_misc.c", "op_fcontrol"): ("R", ()),
    ("dh_misc.c", "pub_fcontrol"): ("R", ()),
    ("analyse.c", "op_analyse"): ("R", ()),
}
# SELECT and SELECTV were REFUSE sites in slice 3c; since slice 3d they ask the server (NK14, NK15), and are decided here
NK_SELECT = {("op_dio4.c", "op_select"), ("op_dio4.c", "op_selectv")}
# INDICES (both forms) were REFUSE sites in slice 3c; since slice 3d a NET_FILE gets the null string through the default arm (NK18), because the query processor asks it of every file
NK_INDICES = {("dh_ak.c", "op_indices1"), ("dh_ak.c", "op_indices2")}
# the census says REFUSE, but by a guard on the read of the file table and not by a statement refusal: the NET_FILE test must come before the first FPtr(
NK_GUARD = (("op_dio2.c", "get_file_status"), ("k_error.c", "log_permissions_error"), ("pdump.c", "dump_variable"), ("op_dio2.c", "op_fileinfo"))
# the census says IGNORE because the function already answers any other kind of file: the sequential-file family (ER_NSEQ), GETPORT / SETPORT, GROUPSTAT, SET.TRIGGER, MARK.MAPPING
NK_SAFE = {("op_seqio.c", n): "SEQ_FILE" for n in ("op_createsq", "op_flush", "op_nobuf", "openseq", "op_readblk", "op_readseq", "op_seek", "op_timeout", "op_weofseq", "op_writeblk",
                                                    "writeseq", "op_get_device")}
NK_SAFE.update({("lnxport.c", "op_getport"): "SEQ_FILE", ("lnxport.c", "op_setport"): "SEQ_FILE", ("dh_misc.c", "op_grpstat"): "DYNAMIC_FILE", ("dh_misc.c", "op_settrig"): "ER_NDYN",
                ("op_dio3.c", "op_mapmarks"): "DIRECTORY_FILE"})
# the rest of the census: SUPPORT (OPEN, CLOSE and the release of a variable) and IGNORE with a reason (generic descriptor code; the IPC file is opened with OPENPATH; the debugger prints a type; triggers
# are reached from the DYNAMIC and DIRECTORY arms only)
NK_OTHER = {("op_dio1.c", "op_close"), ("op_dio1.c", "open_file"), ("op_dio3.c", "call_trigger"), ("k_funcs.c", "k_dereference"), ("k_funcs.c", "k_get_file"), ("k_funcs.c", "k_incr_refct"),
            ("k_funcs.c", "k_release"), ("kernel.c", "process_events"), ("kernel.c", "dump_status"), ("op_debug.c", "get_var_info"), ("op_loads.c", "op_dup")}
NK_SITES_WITH_H = {"read_record", "op_readv", "op_clrfile", "op_delete", "op_write", "op_writev"}
NK_SUITE_MATRIX = ("write", "writeu", "writev", "matwrite", "delete", "clearfile", "readu", "readl", "readvu", "readvl", "matreadu", "matreadl", "recordlocku", "release", "filelock",
                   "fileunlock", "recordlocked", "selectindex", "selectright", "setleft", "setright", "fcontrol6", "fiexcl", "txnwrite")
NK_MAP_FILES = ("gplsrc/netfiles.c", "gplsrc/op_dio1.c", "gplsrc/op_dio2.c", "gplsrc/op_dio3.c", "gplsrc/op_dio4.c", "gplsrc/op_lock.c", "gplsrc/dh_ak.c", "gplsrc/dh_misc.c",
                "gplsrc/analyse.c", "gplsrc/k_error.c", "gplsrc/pdump.c", "gplsrc/descr.h", "gplsrc/sd.h", "gpl.src", "sdsys/gpl.bp/_voc_ref")


@functools.lru_cache(maxsize=None)
def c_functions(tx):
    """{name: text} of the top-level C functions of one comment-free source: a header at column 0, then the body in braces (strings and character
    constants skipped when the braces are counted)."""
    return {name: tx[a:b] for name, (a, b) in c_spans(tx).items()}


def blank_c(src):
    """The source with every comment turned to white space of the same length, so that offsets found in it are offsets in the source."""
    def blank(m):
        return re.sub(r"[^\n]", " ", m.group(0))
    src = re.sub(r"/\*.*?\*/", blank, src, flags=re.S)
    return re.sub(r"//[^\n]*", blank, src)


@functools.lru_cache(maxsize=None)
def c_spans(tx):
    """{name: (start, end)} of the top-level C functions of a source in which comments are gone or blanked."""
    out = {}
    for m in re.finditer(r"^[A-Za-z_][^\n;{}=]*?\b([A-Za-z_]\w*)\s*\([^;{}]*\)\s*\{", tx, re.M):
        name = m.group(1)
        if name in ("if", "for", "while", "switch", "return", "sizeof"):
            continue
        depth, k = 0, m.end() - 1
        while k < len(tx):
            ch = tx[k]
            if ch in "\"'":
                q = ch
                k += 1
                while k < len(tx) and tx[k] != q:
                    if tx[k] == "\\":
                        k += 1
                    k += 1
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        out[name] = (m.start(), k + 1)
    return out


def edit_func(name, pattern, repl, count=1):
    """A mutant (a function of the source text) that changes PATTERN to REPL (a regular expression) inside the function NAME only; KeyError if it is not there."""
    def f(text):
        span = c_spans(blank_c(text)).get(name)
        if span is None:
            raise KeyError("function not in the source: " + name)
        a, b = span
        body, n = re.subn(pattern, repl, text[a:b], count=count, flags=re.S)
        if n == 0:
            raise KeyError("pattern not in %s: %r" % (name, pattern[:60]))
        return text[:a] + body + text[b:]
    return f


def nospace(s):
    return re.sub(r"\s+", "", s)


def c_types(params):
    """The parameter list with the parameter NAMES and the white space gone: "FILE_VAR * fvar, int key" is "FILE_VAR*,int" (a name is not part of what a prototype promises)."""
    if params.strip() in ("", "void"):
        return ""
    return ",".join(nospace(re.sub(r"\s*\b[A-Za-z_]\w*\s*$", "", p)) for p in params.split(","))


def c_proto(text, name):
    """The prototype of NAME in a comment-free source: the return type, the name and the parameter types, white space gone ("intnet_open(FILE_VAR*,constchar*)"), or None."""
    m = re.search(r"^[ \t]*([A-Za-z_][\w \t\*]*?)\b%s\s*\(([^;{)]*)\)\s*;" % re.escape(name), text, re.M)
    if not m:
        return None
    return nospace(m.group(1)) + name + "(" + c_types(m.group(2)) + ")"


def c_header(text, name):
    """The same for the definition of NAME (the header up to its opening brace)."""
    m = re.search(r"^([A-Za-z_][\w \t\*]*?)\b%s\s*\(([^;{)]*)\)\s*\{" % re.escape(name), text, re.M)
    if not m:
        return None
    return nospace(m.group(1)) + name + "(" + c_types(m.group(2)) + ")"


def inside(body, opener, needle):
    """NEEDLE is found, and the nearest OPENER before it is a block that is still open there."""
    j = body.find(needle)
    i = body.rfind(opener, 0, j) if j >= 0 else -1
    if i < 0 or j < 0:
        return False
    depth = 1
    for ch in body[i + len(opener):j]:
        depth += (ch == "{") - (ch == "}")
        if depth <= 0:
            return False
    return True


def map_rules(text):
    out = []
    for ln in text.split("\n"):
        ln = ln.strip()
        if not ln or ln.startswith("@") or ":" not in ln or " ~ " in ln:
            continue
        pat, suites = ln.split(":", 1)
        out.append((pat.strip(), suites.split()))
    return out


def checks_3c(srcs, c, ck):
    """S.65 slice 3c: the kernel half of remote files, as ORDER and as what no statement may reach.  Nothing here compiles or runs C: the section kernel of
    sandbox-netfile.py runs real statements against a NET file (and the refusal matrix), and `make` is the compiler."""
    nf, dsc, sdh = c["netfiles.c"], c["descr.h"], c["sd.h"]
    nfraw = srcs["netfiles.c"]
    vr = c["bp:_voc_ref"]
    suite, rm = srcs["sandbox-netfile.py"], c["regress-map.txt"]

    def ct(fname):
        return c.get(fname) or c.get("c:" + fname, "")

    def fn(fname, name):
        return c_functions(ct(fname)).get(name, "")

    nw, nraw = fn("netfiles.c", "net_open_work"), fn("netfiles.c", "net_call_raw")

    # ---- NK1. the type, the union member, the limits
    allf = {m.group(1): int(m.group(2)) for m in re.finditer(r"#define\s+([A-Z_]+_FILE)\s+(\d+)\b", dsc)}
    ck("NK1 descr.h: the file variable types are DIRECTORY_FILE 1, DYNAMIC_FILE 2, SEQ_FILE 3 and NET_FILE 4 (4 is NET_FILE's alone, and 5 stays unused), and the union member `net` holds, in this "
       "order, the two pointer-sized words that read as a NULL access.dir.trg (void *zero[2]), the handler's handle (int16_t), the epoch (u_int16_t) and the server name (NET_SERVER_LEN + 1 bytes)",
       all(allf.get(k) == v for k, v in NK_TYPES.items()) and [k for k, v in allf.items() if v == 4] == ["NET_FILE"] and 5 not in allf.values()
       and re.search(r"struct\s*\{\s*void\s*\*\s*zero\[2\];\s*int16_t\s+handle;\s*u_int16_t\s+epoch;\s*char\s+server\[NET_SERVER_LEN\s*\+\s*1\];\s*\}\s*net;", dsc) is not None, repr(allf))
    nfh = c["bp:netfile.h"]
    handles = re.search(r"\$define\s+NF\$MAX\.HANDLES\s+(\d+)", nfh)
    ck("NK1a the limits agree across C and BASIC: NET_MAX_HANDLES is netfile.h's NF$MAX.HANDLES (100); NET_SERVER_LEN is 16, the length _voc_ref and the handler allow for a server name; NET_FILE_MAX is 63, "
       "the length _voc_ref allows for a file name and the number message 11491 gives",
       re.search(r"#define\s+NET_MAX_HANDLES\s+(\d+)", dsc) is not None and handles is not None and re.search(r"#define\s+NET_MAX_HANDLES\s+(\d+)", dsc).group(1) == handles.group(1) == "100"
       and re.search(r"#define\s+NET_SERVER_LEN\s+16\b", dsc) is not None and "len(srv) <= 16" in c["bp:netfile"] and "len(n.srv) > 16" in vr
       and re.search(r"#define\s+NET_FILE_MAX\s+63\b", nf) is not None and "len(n.file) > 63" in vr and "up to 63 characters" in (srcs.get("msg:11491") or ""), "")
    codes = {"NF_OPEN": "NF$OPEN", "NF_CLOSE": "NF$CLOSE", "NF_READ": "NF$READ", "NF_READV": "NF$READV", "NF_FILEINFO": "NF$FILEINFO", "NF_CLOSEALL": "NF$CLOSEALL",
             "NF_RC_OK": "NF$RC.OK", "NF_RC_ELSE": "NF$RC.ELSE", "NF_RC_ERROR": "NF$RC.ERROR"}
    cdef = {m.group(1): int(m.group(2)) for m in re.finditer(r"#define\s+(NF_[A-Z_]+)\s+(\d+)\b", nf)}
    bdef = {m.group(1): int(m.group(2)) for m in re.finditer(r"\$define\s+(NF\$[A-Z.]+)\s+(-?\d+)", nfh)}
    ck("NK1b the operation and result codes netfiles.c mirrors are netfile.h's, name for name (OPEN, CLOSE, READ, READV, FILEINFO, CLOSEALL; the results OK 0, ELSE 2, ERROR 3)",
       all(k in cdef and bdef.get(v) == cdef[k] for k, v in codes.items()), repr({k: (cdef.get(k), bdef.get(v)) for k, v in codes.items() if bdef.get(v) != cdef.get(k)}))

    # ---- NK2. the nine functions, once each, and every declaration of them says the same
    defs = {n: c_header(nf, n) for n in NK_FUNCS}
    protos = {n: c_proto(sdh, n) for n in NK_FUNCS}
    others = {}
    for fname in ("op_dio2.c", "op_dio3.c", "op_dio1.c"):
        for n in NK_FUNCS:
            p = c_proto(c[fname], n)
            if p is not None:
                others[(fname, n)] = p
    twice = [n for n in NK_FUNCS if sum(len(re.findall(r"^[A-Za-z_][\w \t\*]*?\b%s\s*\([^;{)]*\)\s*\{" % n, t, re.M)) for k, t in c.items()
                                          if k.endswith((".c",)) or k.startswith("c:")) != 1]
    ck("NK2 the ten netfiles.c functions (net_path_is_net, net_open, net_close, net_read, net_readv, net_fileinfo, net_select, net_refuse, net_close_all, net_message) are each DEFINED ONCE in the kernel, "
       "have a prototype in sd.h that says exactly what the definition says, and every other prototype of them (op_dio2.c, op_dio3.c) agrees too",
       all(defs.values()) and defs == protos and not twice and all(p == protos[n] for (f, n), p in others.items()) and len(others) >= 5, repr((defs, protos, twice, others)))

    # ---- NK3. the order: the shapes, THE GATE, the audit, then the handler
    ck("NK3 net_open_work, in this ORDER: the encoded pointer's shape (char(1) N char(1) server char(1) file), THE GATE (net_gate_ok), its refusal audited and RETURNED, and only then the queued closes and the "
       "handler (NF_OPEN) - before the gate there is no handler call, no load_object and no queue flush",
       ordered(nw, "encoded_path[1] != 'N'", "(u_char)encoded_path[2] != 1", "strchr(p, 1)", "if (!net_gate_ok())", "audit_message(", "return -ER_PERM;", "net_flush_pending();", "net_call_raw(NF_OPEN")
       and not re.search(r"net_call_raw\(|net_flush_pending\(|load_object\(|k_call\(", nw[:nw.find("if (!net_gate_ok())")]) if "if (!net_gate_ok())" in nw else False, "")
    gate = fn("netfiles.c", "net_gate_ok")
    ck("NK3a THE GATE: the administrator (USR_ADMIN in the session's flags) or an account holding the NET gate (UG_NET in its gates), asked of the session and of nothing else; an $internal program is NOT "
       "exempt (HDR_INTERNAL is not in netfiles.c at all); the refusal is message 11460 with the account, audited as 'netfile refused server=<name> reason=gate' with the server name made safe",
       re.search(r"return\s*\(\(my_uptr->flags & USR_ADMIN\) != 0\)\s*\|\|\s*\(\(my_uptr->gates & UG_NET\) != 0\);", gate) is not None and "HDR_INTERNAL" not in nf
       and ordered(nw, "net_set_message(MSG_NO_GATE, account(), safe", "\"netfile refused server=%s reason=gate\"") and "#define MSG_NO_GATE 11460" in nf
       and re.search(r"safe\[i\]\s*=\s*\(\(\(server\[i\] >= 'a'\) && \(server\[i\] <= 'z'\)\) \|\| \(\(server\[i\] >= '0'\) && \(server\[i\] <= '9'\)\)\) \? server\[i\] : '\?';", nw) is not None, "")
    ck("NK3b net_call_raw: the program is looked for FIRST (load_object of $netfile, so a tree without it says message 11507 and does not stop the process), the six arguments are pushed, the handler is "
       "called BY NAME (k_call of \"$netfile\", so the $internal flag it carries is the global catalogue's) with PF_IS_TRIGGER, run to its RETURN, and the reference k_call counted is given back; the name "
       "$netfile appears in the kernel's code exactly twice (the lookup and the call) and in no other kernel file",
       ordered(nraw, "load_object(\"$netfile\", FALSE) == NULL", "net_set_message(MSG_HANDLER", "(e_stack++)->data.value = op;", "net_push_string(a, alen);", "(e_stack++)->data.d_addr = out;",
               "(e_stack++)->data.d_addr = &rc_descr;", "k_call(\"$netfile\", 6, NULL, 0);", "process.program.flags |= PF_IS_TRIGGER;", "k_run_program();", "k_exit_cause == K_EXIT_RECURSIVE",
               "--(hdr->ext_hdr.prog.refs)", "unload_object(")
       and nf.count("\"$netfile\"") == 2 and not [k for k, t in c.items() if k != "netfiles.c" and (k.endswith(".c") or k.startswith("c:")) and "\"$netfile\"" in t], "")

    # ---- NK4. what each public function may and may not do
    refuse, close_, closeall, stale, op_ = (fn("netfiles.c", n) for n in ("net_refuse", "net_close", "net_close_all", "net_stale", "net_op"))
    ck("NK4 net_refuse RUNS NO BASIC and touches nothing: no handler call, no queue flush, no k_call, no k_run_program; it takes the server from the variable only when it is a NET_FILE, writes the statement "
       "in lower case, builds message 11501 (server, statement) and returns net_raise(-ER_NETWORK) - which does not return without ON ERROR",
       refuse != "" and not re.search(r"net_call_raw\(|net_flush_pending\(|net_op\(|k_call\(|k_run_program\(|load_object\(", refuse)
       and ordered(refuse, "fvar->type == NET_FILE", "server = fvar->access.net.server;", "'A') && (what[i] <= 'Z')", "net_set_message(MSG_READ_ONLY, server, op", "return net_raise(-ER_NETWORK, entry);")
       and "#define MSG_READ_ONLY 11501" in nf, "")
    ck("NK4a net_close: the handler is run only under explicit_close (the CLOSE statement), the handle is cleared BEFORE anything is sent, a stale variable is not sent at all, and any other release (an unwind, a "
       "scope exit, kill_process) is only QUEUED - BASIC must not run where the e-stack may be gone",
       ordered(close_, "fvar->type != NET_FILE", "if (net_stale(fvar))", "fvar->access.net.handle = 0;", "if (explicit_close) {", "net_flush_pending();", "net_call_raw(NF_CLOSE", "} else if (net_pending_ct < NET_MAX_HANDLES) {",
               "net_pending[net_pending_ct++] = handle;")
       and not re.search(r"net_call_raw\(", close_[close_.find("} else if"):]), "")
    ck("NK4b net_stale is closed, not a NET_FILE, or from an earlier epoch; net_op asks it BEFORE the queue is flushed or the handler called (message 11494 for a stale handle); net_close_all moves the epoch on and "
       "empties the queue BEFORE it calls the handler (NF_CLOSEALL), and only if this process ever opened a remote file",
       ordered(stale, "fvar->type != NET_FILE", "access.net.handle <= 0", "access.net.epoch != net_epoch") and ordered(op_, "if (net_stale(fvar))", "MSG_BAD_HANDLE", "net_flush_pending();", "net_call_raw(op")
       and ordered(closeall, "net_epoch++;", "net_pending_ct = 0;", "if (!net_used)", "net_call_raw(NF_CLOSEALL"), "")
    opn = nw
    ck("NK4c a NET_FILE is made LAST and only on success: the union is zeroed, the handle (1 to NET_MAX_HANDLES, digits only) is checked, then the epoch, the server name, file_id -1, FV_RDONLY | FV_NON_TXN and the "
       "type - and `type = NET_FILE` occurs once, so no failed open leaves a variable the other statements would treat as remote",
       ordered(opn, "(handle < 1) || (handle > NET_MAX_HANDLES)", "memset(&fvar->access, 0, sizeof(fvar->access));", "fvar->access.net.handle = (int16_t)handle;", "fvar->access.net.epoch = net_epoch;",
               "strcpy(fvar->access.net.server, server);", "fvar->file_id = -1;", "fvar->flags |= FV_RDONLY | FV_NON_TXN;", "fvar->type = NET_FILE;")
       and len(re.findall(r"type\s*=\s*NET_FILE", nf)) == 1 and "hs[i] < '0') || (hs[i] > '9'" in opn, "")
    rd = fn("netfiles.c", "net_read")
    ck("NK4d net_read and net_readv answer an empty id with ER_IID WITHOUT calling the handler; an error is raised by net_raise with the message the handler gave unless the statement has ON ERROR, the ELSE branch is "
       "the remote STATUS() when the server sent one and ER_RNF otherwise; the handler's message numbers 11460, 11461 and 11496 are the permission class (ER_PERM), every other error ER_NETWORK",
       ordered(rd, "if (id_len < 1)", "return ER_IID;", "net_op(fvar, NF_READ") and ordered(fn("netfiles.c", "net_readv"), "if (id_len < 1)", "return ER_IID;", "net_op(fvar, NF_READV")
       and re.search(r"return \(rc->status > 0\) \? rc->status : else_status;", nf) is not None
       and re.search(r"case MSG_NO_GATE:\s*case MSG_NOT_LISTED:\s*case MSG_NO_CREDENTIAL:\s*return -ER_PERM;", nf) is not None and "return -ER_NETWORK;" in fn("netfiles.c", "net_error_status"), "")

    # ---- NK5. the VOC pointer
    i = vr.find('case type = "N"')
    case_n = vr[i:vr.find("\n         case 1", i)] if i >= 0 else ""
    chk = routine_body(vr, "check.n.pointer")
    ck("NK5 _voc_ref: an N pointer is its own case of the pointer loop (after F and Q, before the default); both names are trimmed and lower cased; the shape "
       "test is a gosub and a failure is ER$NAM; a dictionary (fno 3) is NOT refused any more (no ER$VNF in the case) - 'dict ' goes in front of the file name AFTER the shape test; the pathname returned is "
       "char(1) 'N' char(1) server char(1) file with status 0; NO kernel call and NO gate in the case (the gate is the session's, asked in C)",
       i > 0 and vr.find('case type = "Q"') < i < vr.find("\n         case 1", i)
       and ordered(case_n, "n.srv = downcase(trim(voc.rec<2>))", "n.file = downcase(trim(voc.rec<3>))", "gosub check.n.pointer", "if not(n.ok) then", "set.status ER$NAM", "return", "end",
                   "if fno = 3 then n.file = 'dict ':n.file", "pathname = char(1):'N':char(1):n.srv:char(1):n.file", "set.status 0", "return")
       and "ER$VNF" not in case_n
       and "kernel(" not in case_n and "K$NET" not in vr, repr(case_n[:120]))
    ck("NK5a check.n.pointer: a server name is 1 to 16 characters, a lower case LETTER first, then letters and digits; a file name is 1 to 63 lower case letters, digits and . _ - $ (no space: the 'dict ' of the "
       "DICT form is added by the case AFTER this test, NK17; no slash, so no pathname); n.ok starts true and only ever goes false",
       ordered(chk, "n.ok = @true", "'abcdefghijklmnopqrstuvwxyz'", "'0123456789'", "len(n.srv) < 1 or len(n.srv) > 16", "len(n.file) < 1 or len(n.file) > 63", "index(n.letters, n.srv[1,1], 1) = 0",
               "index(n.letters:n.digits, n.srv[n.k,1], 1) = 0", "index(n.letters:n.digits:'._-$', n.file[n.k,1], 1) = 0") and "n.ok = @true" not in chk[chk.find("n.ok = @true") + 12:]
       and chk.count("n.ok = @false") >= 5 and "/" not in re.sub(r"'[^']*'", "", chk), "")
    ck("NK5b the C side reads the encoded form the BASIC side writes: byte 0 is char(1), byte 1 is 'N', byte 2 is char(1), the server name runs to the next char(1) (1 to NET_SERVER_LEN), the file name is the rest "
       "(1 to NET_FILE_NAME_MAX, which is NET_FILE_MAX and the 5 characters of 'dict ' - the buffer holds that many - no second separator) - and a path that is not that is message 11508 and ER_NAM, never a call of the handler",
       ordered(nw, "(u_char)encoded_path[0] != 1", "encoded_path[1] != 'N'", "MSG_BAD_POINTER, \"it does not begin N\"", "return -ER_NAM;", "q = strchr(p, 1);", "if (q == NULL) {", "(n > NET_SERVER_LEN)",
               "(n > NET_FILE_NAME_MAX)", "strchr(p, 1) != NULL") and "u_char)path[0]==1" in fn("netfiles.c", "net_path_is_net").replace(" ", "")
       and re.search(r"#define\s+NET_FILE_NAME_MAX\s+\(NET_FILE_MAX\s*\+\s*5\)", nf) is not None and re.search(r"char\s+file\[NET_FILE_NAME_MAX\s*\+\s*1\];", nw) is not None
       and "(n > NET_FILE_MAX)" not in nw and "file[NET_FILE_MAX" not in nw, "")

    # ---- NK6. open_file, close, dio_close
    of = fn("op_dio1.c", "open_file")
    ck("NK6 open_file: the encoded path is recognised right after the VOC lookup, INSIDE the `if (map_name)` block (so OPEN by name only), BEFORE fullpath(), the OS path test, the transaction cache and the "
       "file table; OPENPATH and OPENTEMP call open_file(FALSE) and the kernel never calls net_open or net_path_is_net anywhere else",
       ordered(of, "get_voc_file_reference(voc_name, open_dict, mapped_name, vflags)", "if (net_path_is_net(mapped_name)) {", "net_open(fvar, mapped_name)", "goto net_file_opened;", "fullpath(pathname, mapped_name);",
               "os_path_open_ok(", "txn_open(", "dh_open(", "get_file_entry(")
       and inside(of, "if (map_name) {", "if (net_path_is_net(mapped_name))") and "open_file(FALSE)" in fn("op_dio1.c", "op_openpath") and "open_file(FALSE)" in fn("op_dio1.c", "op_opentemp")
       and not re.search(r"net_", fn("op_dio1.c", "op_openpath")) and not re.search(r"net_", fn("op_dio1.c", "op_opentemp"))
       and sum(t.count("net_open(") for k, t in c.items() if (k.endswith(".c") or k.startswith("c:")) and k != "netfiles.c") == 1
       and sum(t.count("net_path_is_net(") for k, t in c.items() if (k.endswith(".c") or k.startswith("c:")) and k != "netfiles.c") == 1, "")
    ck("NK6a a failed net_open keeps the file variable out of the file table (net_open sets the type only on success) and shows ITS message: the status is the net_open status, the error is raised from "
       "net_message() BEFORE the generic 'Error opening file' (message 1402), and only without ON ERROR",
       ordered(of, "net_status = net_open(fvar, mapped_name);", "process.status = net_status;", "net_failed = (net_status < 0);", "goto exit_op_open;", "net_file_opened:", "exit_op_open:",
               "if (net_failed)", "k_error(\"%s\", net_message());", "k_error(sysmsg(1402)") and "!(op_flags & P_ON_ERROR)" in of[of.find("exit_op_open:"):of.find("if (net_failed)")], "")
    dc, oc = fn("op_dio1.c", "dio_close"), fn("op_dio1.c", "op_close")
    arm = dc[dc.find("case NET_FILE:"):dc.find("break;", dc.find("case NET_FILE:")) + 6] if "case NET_FILE:" in dc else ""
    ck("NK6b dio_close has a NET_FILE arm that does one thing, net_close(fvar) - the file table block above it runs only for file_id > 0 - and the CLOSE statement sets explicit_close around the release (and clears "
       "it after), which is the only moment net_close talks to the server",
       arm.replace("\n", " ").count("net_close(fvar);") == 1 and arm.count(";") == 2 and "if (fno > 0)" in dc[:dc.find("case NET_FILE:")] and ordered(oc, "explicit_close = TRUE;", "k_release(descr);", "explicit_close = FALSE;")
       and ordered(close_, "if (explicit_close) {", "explicit_close = FALSE;", "net_call_raw(NF_CLOSE"), repr(arm))

    # ---- NK7. every census REFUSE site refuses first
    bad, seen = [], 0
    for (fname, name), (how, extra) in sorted(NK_REFUSE.items()):
        body = fn(fname, name)
        seen += 1
        if not body:
            bad.append("%s/%s: function not found" % (fname, name))
            continue
        call = "net_refuse(" if how == "R" else "refuse_net_file("
        i = body.find(call)
        if i < 0:
            bad.append("%s/%s: no %s" % (fname, name, call))
            continue
        if how == "R" and not (0 <= body.find("NET_FILE") < i):
            bad.append("%s/%s: net_refuse is not behind a NET_FILE test" % (fname, name))
        j = [body.find(x) for x in NK_DANGER + tuple(extra) if body.find(x) >= 0]
        if j and min(j) < i:
            bad.append("%s/%s: %r comes before the refusal" % (fname, name, body[min(j):min(j) + 24]))
    ck("NK7 THE CENSUS: each of the %d statements the census of 17 Oct 26 says REFUSE (CONFIGURE.FILE, the locking reads, READVU, CLEARFILE, DELETE, WRITE, WRITEV, FILELOCK, FILEUNLOCK, "
       "GETLOCKS, RECORDLOCKU/L, RECORDLOCKED, RELEASE, the ten index operations other than INDICES, both FCONTROLs, ANALYSE.FILE) calls net_refuse (or refuse_net_file) behind a NET_FILE test and BEFORE the first read or "
       "write of the file table, a lock, a select list or an edit-gate decision in the function (SELECT and SELECTV are not in it since slice 3d: NK14, NK15; nor is INDICES: NK18)" % seen, not bad, repr(bad))
    badg = []
    for fname, name in NK_GUARD:
        body = fn(fname, name)
        i, j = body.find("NET_FILE"), body.find("FPtr(")
        if not body or i < 0 or (j >= 0 and j < i):
            badg.append("%s/%s" % (fname, name))
    ck("NK7a the census sites that read the file table to PRINT or to LOG (FILEINFO, the file status, the permissions log, the process dump) test for NET_FILE BEFORE the first FPtr(: " + ", ".join(n for _f, n in NK_GUARD),
       not badg, repr(badg))
    hdr = fn("op_dio3.c", "refuse_net_file")
    rc_ = fn("op_dio3.c", "read_record")
    ck("NK7b the helper refuse_net_file: not a NET_FILE is FALSE and nothing else happens; for one it hands net_refuse ONLY the ON ERROR bit, takes the negative status (never a non-negative one), and "
       "without ON ERROR still raises message 11501 itself if net_refuse returned; READU / READL / MATREADU / MATREADL are refused in read_record behind (type NET_FILE and P_REC_LOCKS) and a NET_FILE's "
       "transaction id is forced to 0 (txn_read would read the file table); READ and MATREAD have their own `case NET_FILE:` that calls net_read",
       ordered(hdr, "fvar->type != NET_FILE", "return FALSE;", "process.op_flags = op_flags & P_ON_ERROR;", "net_refuse(fvar, what)", "process.op_flags = 0;", "(st < 0) ? st : -ER_PERM", "k_error(sysmsg(11501)")
       and "(fvar->type == NET_FILE) && (op_flags & P_REC_LOCKS)" in rc_ and "(fvar->type == NET_FILE)) ? 0 : process.txn_id" in rc_ and ordered(rc_, "case NET_FILE: {", "net_read(fvar, id, id_len, &net_rec)"), "")
    ro = fn("op_dio3.c", "op_readv")
    ck("NK7c READV of a NET_FILE never runs the recursive _readv (which would READ, and cut the field in BASIC): the NET branch is the first branch, reads through net_readv, refuses READVU / READVL, and "
       "dismisses the same four operands the local branch does", ordered(ro, "if (fvar->type == NET_FILE) {", "refuse_net_file(", "net_readv(fvar, id, id_len, field_no, &net_str)", "} else if (field_no != 0) {", "k_recurse(pcode_readv")
       and ro[ro.find("if (fvar->type == NET_FILE) {"):ro.find("} else if (field_no != 0) {")].count("k_dismiss()") == 3, "")
    fi = fn("op_dio2.c", "op_fileinfo")
    branch = fi[fi.find("if (ftype == NET_FILE) {"):fi.find("fptr = FPtr(fvar->file_id);")] if "if (ftype == NET_FILE) {" in fi else ""
    ck("NK7d FILEINFO of a NET_FILE is answered BEFORE fptr = FPtr(file_id): the keys about the variable (VOCNAME, READONLY, NON.TXN, NETFILE, FILENO, TXN.UPDATE, INDEX.SCAN, ID) are answered from it, the three "
       "that write the file table (FL_EXCLUSIVE, FL_STATS_ON, FL_STATS_OFF) are refused, and every other key goes to net_fileinfo; the branch reads no FPtr",
       branch != "" and "FPtr(" not in branch and all(k in branch for k in ("case FL_VOCNAME:", "case FL_READONLY:", "case FL_NON_TXN:", "case FL_NETFILE:", "case FL_FILENO:", "case FL_TXN_UPDATE:", "case FL_INDEX_SCAN:",
                                                                         "case FL_ID:", "case FL_EXCLUSIVE:", "case FL_STATS_ON:", "case FL_STATS_OFF:", "net_refuse(fvar, \"FILEINFO\")", "default:", "net_fileinfo(fvar, key)")), "")

    # ---- NK8. nothing that takes a file variable has been left undecided
    found = set()
    for k, t in c.items():
        if k.endswith(".c") or k.startswith("c:"):
            for name, body in c_functions(t).items():
                if "k_get_file(" in body or "data.fvar" in body:
                    found.add((k[2:] if k.startswith("c:") else k, name))
    decided = set(NK_REFUSE) | set(NK_GUARD) | set(NK_SAFE) | NK_OTHER | NK_SELECT | NK_INDICES
    safe_bad = [(f, n) for (f, n), tok in sorted(NK_SAFE.items()) if tok not in fn(f, n)]
    ck("NK8 NOTHING IS LEFT UNDECIDED: every kernel function that is given a file variable (k_get_file or ->data.fvar) is in the census table of this check - refused, guarded, answering any other kind of file by "
       "its own type test (the sequential family, GETPORT, SETPORT, GROUPSTAT, SET.TRIGGER, MARK.MAPPING - the token is still in each), or listed as supported / ignored - so a NEW function that reads a file "
       "variable fails here until someone decides what it does with a remote file (%d found, %d decided)" % (len(found), len(decided)),
       not (found - decided) and not safe_bad, repr((sorted(found - decided), safe_bad)))

    # ---- NK9. messages and the build
    m7, m8 = srcs.get("msg:11507"), srcs.get("msg:11508")
    used = {int(x) for x in re.findall(r"#define\s+MSG_\w+\s+(\d+)", nf)}
    ck("NK9 the kernel's own messages: 11507 (the handler could not be used: %1) and 11508 (the VOC entry is not valid: %1) are one line each with ONE place; every message number netfiles.c names exists as a "
       "one-line message (11460, 11461, 11494, 11496, 11501, 11507, 11508); the kernel cites no number the handler's block does not hold apart from those two",
       m7 is not None and m8 is not None and m7.count("\n") <= 1 and m8.count("\n") <= 1 and "%1" in m7 and "%1" in m8 and not re.search(r"%[2-9]", m7 + m8)
       and used == {11460, 11461, 11494, 11496, 11501, 11507, 11508} and all(os.path.exists(os.path.join(MSGDIR, str(n))) for n in used), repr(sorted(used)))
    src_list = srcs["gpl.src"].split()
    ck("NK10 the Makefile builds from gpl.src: `netfiles` is in it exactly once, after `messages`, and gplsrc/netfiles.c exists; sd.h no longer says NETFILES.C was removed",
       src_list.count("netfiles") == 1 and src_list.index("netfiles") == src_list.index("messages") + 1 and os.path.exists(os.path.join(GPLSRC, "netfiles.c"))
       and "NETFILES.C removed" not in srcs["sd.h"], "")

    # ---- NK11. the suite and the map
    tags = set(re.findall(r'km\("([a-z0-9]+)"', suite))
    nums = {int(x) for x in re.findall(r"\bmsg\((\d+)", suite)}
    rules = map_rules(rm)
    unmapped = []
    for path in NK_MAP_FILES:
        first = next((s for pat, s in rules if fnmatch.fnmatchcase(path, pat)), None)
        if first is None or "netfile" not in first:
            unmapped.append(path)
    ck("NK11 the suite sandbox-netfile.py has the section kernel (before gaps), its refusal matrix names every statement of the census (%d tags, %s missing), the fake's allowed request types are exactly "
       "login, account, open, close, read and quit, every message number the section expects is a message of the tree, and the map sends every kernel file of this slice to the netfile suite "
       "(%s unmapped)" % (len(tags), sorted(set(NK_SUITE_MATRIX) - tags), unmapped),
       '("kernel", kernel_section), ("gaps", gaps_section)' in suite and not (set(NK_SUITE_MATRIX) - tags) and "KALLOWED = {47, 48, 3, 4, 5, 6, 1}" in suite and "except subprocess.TimeoutExpired:" in suite
       and nums and all(os.path.exists(os.path.join(MSGDIR, str(n))) for n in nums) and not unmapped, repr((sorted(set(NK_SUITE_MATRIX) - tags), unmapped, sorted(nums))))
    texts_ = {n: (srcs.get(n) or "") for n in ("netfiles.c", "descr.h", "sd.h", "op_dio1.c", "op_dio2.c", "op_dio3.c", "op_dio4.c", "op_lock.c", "dh_ak.c", "dh_misc.c", "analyse.c", "k_error.c", "pdump.c",
                                                 "bp:_voc_ref", "sandbox-netfile.py")}
    lack = [n for n, t in texts_.items() if not re.search(r"17 Oct 26 dm\s+S\.65 slice 3c", t)]
    ck("NK12 the dated history lines are there: every file slice 3c changed says `S.65 slice 3c` (%d files), and this check's own file says so" % len(texts_), not lack and "slice 3c" in (__doc__ or ""), repr(lack))


def checks_3d(srcs, c, ck):
    """S.65 slice 3d: SELECT and SELECTV of a remote file, the dictionary of one, and the FILEINFO keys a query asks.  Text only: the section kernel of
    sandbox-netfile.py runs the statements, and `make` is the compiler."""
    nf, dsc, kh, skh = c["netfiles.c"], c["descr.h"], c["keys.h"], c["syscom/keys.h"]
    vr, nfh = c["bp:_voc_ref"], c["bp:netfile.h"]

    def ct(fname):
        return c.get(fname) or c.get("c:" + fname, "")

    def fn(fname, name):
        return c_functions(ct(fname)).get(name, "")

    # ---- NK13. net_select
    ns = fn("netfiles.c", "net_select")
    cdef = {m.group(1): int(m.group(2)) for m in re.finditer(r"#define\s+(NF_[A-Z_]+)\s+(\d+)\b", nf)}
    bdef = {m.group(1): int(m.group(2)) for m in re.finditer(r"\$define\s+(NF\$[A-Z.]+)\s+(-?\d+)", nfh)}
    ok_at = ns.find("return status;")                      # the end of the two failure returns: nothing may be set before it
    ck("NK13 net_select: NF_SELECT is netfile.h's NF$SELECT (6); the statement's flags are taken FIRST (u_int16_t entry = process.op_flags), the request goes through net_op (never the handler directly), "
       "process.op_flags is given back, a negative status is raised by net_raise with THAT entry (so only a statement without ON ERROR stops, exactly as net_read) and a positive one is the ELSE branch; "
       "*ids and *count are each set once, after both returns, so a failure leaves the caller's values alone; the ids are counted by their field marks (an empty answer is 0, not 1)",
       cdef.get("NF_SELECT") == bdef.get("NF$SELECT") == 6 and ns != ""
       and ordered(ns, "u_int16_t entry = process.op_flags;", "net_op(fvar, NF_SELECT", "process.op_flags = entry;", "if (status < 0)", "return net_raise(status, entry);", "if (status > 0)",
                   "return status;", "net_take_string(&out)", "k_release(&out);", "== FIELD_MARK", "n++;", "*ids = s;", "*count = n;", "return 0;")
       and ns.count("net_raise(") == 1 and ns.count("*ids =") == 1 and ns.count("*count =") == 1 and 0 < ok_at < ns.find("*ids =") and ok_at < ns.find("*count =")
       and not re.search(r"net_call_raw\(|net_flush_pending\(|k_call\(|load_object\(|net_refuse\(", ns)
       and re.search(r"int32_t\s+n\s*=\s*0;", ns) is not None and re.search(r"if \(s != NULL\) \{\s*n = 1;", ns) is not None, repr(ns[:80]))
    # ---- NK14. SELECT
    sel = fn("op_dio4.c", "op_select")
    d4 = ct("op_dio4.c")
    first_net = sel.find("if (fvar->type == NET_FILE)")
    danger = [sel.find(x) for x in NK_DANGER if sel.find(x) >= 0]
    helper = fn("op_dio4.c", "net_select_with_flags")
    sl = fn("op_dio4.c", "store_select_list")
    ck("NK14 SELECT of a NET_FILE: the ids are asked of the server (net_select_with_flags) BEFORE end_select, clear_select or anything that reads the file table, so an error or an ELSE leaves the target list alone "
       "(the status is kept, the stack is cleaned and the function leaves by select_status); only then does `case NET_FILE:` of the select switch call store_select_list (the same function dir_select ends with) "
       "UNCONDITIONALLY - no `if (net_ids != NULL)` in front of it - and store_select_list sets SELECT.COUNT first and returns early for a NULL list only AFTER that, so an empty remote file gives @SELECTED 0; "
       "the helper hands net_select ONLY the statement's ON ERROR bit and clears process.op_flags again; net_select is called from the helper and from nowhere else in the kernel; SELECT no longer calls net_refuse",
       sel != "" and 0 <= first_net < sel.find("net_select_with_flags(fvar, op_flags, &net_ids, &net_count)") and (not danger or first_net < min(danger))
       and ordered(sel, "if (fvar->type == NET_FILE)", "net_select_with_flags(fvar, op_flags, &net_ids, &net_count)", "if (net_st != 0) {", "process.status = net_st;", "k_pop(1);", "k_dismiss();",
                   "goto select_status;", "end_select(list_no);", "clear_select(list_no);", "switch (fvar->type) {", "case NET_FILE:", "store_select_list(list_no, net_ids, net_count);")
       and re.search(r"case NET_FILE:\s*store_select_list\(list_no, net_ids, net_count\);\s*break;", sel) is not None      # no `if (net_ids != NULL)` guard: an empty file must still set the count
       and ordered(sl, "SYSCOM_SELECT_COUNT", "descr->data.value = record_count;", "if (head == NULL)", "return;", "SYSCOM_SELECT_LIST", "descr->data.str.saddr = head;")
       and sl.count("if (head == NULL)") == 1 and sl.count("return;") == 1
       and "net_refuse(" not in sel and helper != "" and ordered(helper, "process.op_flags = op_flags & P_ON_ERROR;", "net_select(fvar, ids, count)", "process.op_flags = 0;", "return st;")
       and sum(t.count("net_select(") for k, t in c.items() if (k.endswith(".c") or k.startswith("c:")) and k != "netfiles.c") == 1
       and "store_select_list(list_no, head, record_count)" in fn("op_dio4.c", "dir_select")
       and c_proto(d4, "net_select_with_flags") is not None and c_proto(d4, "net_select_with_flags") == c_header(d4, "net_select_with_flags")
       and c_proto(d4, "store_select_list") is not None and c_proto(d4, "store_select_list") == c_header(d4, "store_select_list"), repr(sel[:80]))
    # ---- NK15. SELECTV
    sv = fn("op_dio4.c", "op_selectv")
    i0 = sv.find("if (fvar->type == NET_FILE)")
    i1 = sv.find("net_select_with_flags(fvar, op_flags, &net_ids, &net_count)")
    i2 = sv.find("goto selectv_status;", i1) if i1 >= 0 else -1
    netb = sv[i0:i2] if 0 <= i0 < i1 < i2 else ""
    danger = [sv.find(x, i0) for x in NK_DANGER if i0 >= 0 and sv.find(x, i0) >= 0]
    ck("NK15 SELECTV of a NET_FILE: the NET branch asks the server and leaves by selectv_status BEFORE the file type switch (list 11 and the local selects are never reached); nothing touches tgt_descr between the "
       "branch's opening and the call, and AFTER the call the target is found again from the e-stack (the handler runs BASIC and can move it, as op_read does) and made an empty SELLIST; on success the ids are "
       "the list and their count is its offset (both only when there are ids: a NULL list is not touched), and @SELECTED is the count on EVERY success, an empty file included; an error or an ELSE leaves the empty list and the status; SELECTV no longer calls net_refuse",
       sv != "" and netb != "" and "tgt_descr" not in netb[:netb.find("net_select_with_flags(")]
       and ordered(netb, "net_select_with_flags(fvar, op_flags, &net_ids, &net_count);", "tgt_descr = e_stack - 1;", "while (tgt_descr->type == ADDR)", "tgt_descr = tgt_descr->data.d_addr;",
                   "InitDescr(tgt_descr, SELLIST);", "tgt_descr->data.str.saddr = NULL;", "if (net_st != 0) {", "process.status = net_st;", "} else {", "if (net_ids != NULL) {", "tgt_descr->data.str.saddr = net_ids;",
                   "net_ids->offset = net_count;", "Element(process.syscom, SYSCOM_SELECTED)", "descr->data.value = net_count;")
       and re.search(r"\} else \{\s*if \(net_ids != NULL\) \{\s*tgt_descr->data\.str\.saddr = net_ids;\s*net_ids->offset = net_count;\s*\}\s*"
                     r"descr = Element\(process\.syscom, SYSCOM_SELECTED\);\s*descr->data\.value = net_count;\s*\}\s*$", netb) is not None      # @SELECTED on EVERY success, outside the NULL test
       and i2 < sv.find("switch (fvar->type) {", i2) and "net_refuse(" not in sv and not [d for d in danger if d < i2], repr(netb[:80]))
    # ---- NK16. FILEINFO answers three more keys of a remote file
    fi = fn("op_dio2.c", "op_fileinfo")
    branch = fi[fi.find("if (ftype == NET_FILE) {"):fi.find("fptr = FPtr(fvar->file_id);")] if "if (ftype == NET_FILE) {" in fi else ""

    def seg(label):
        j = branch.find(label)
        return branch[j:branch.find("goto set_integer;", j)] if j >= 0 else ""
    tdef = {m.group(1): int(m.group(2)) for m in re.finditer(r"#define\s+(FL_TYPE_[A-Z]+)\s+(\d+)\b", kh)}
    bt = {m.group(1): int(m.group(2)) for m in re.finditer(r"\$define\s+(FL\$TYPE\.[A-Z]+)\s+(\d+)", skh)}
    ck("NK16 FILEINFO of a NET_FILE: FL_TYPE answers FL_TYPE_NET (7, its own number: FL_TYPE_NET is defined in gplsrc/keys.h and FL$TYPE.NET in sdsys/syscom/keys.h with the same value and no other type uses 7), "
       "FL_COLLECTION answers 0, FL_FLAGS answers DHF_NOCASE for an $internal program and 0 for any other - each in the NET branch, which has no FPtr( and comes before fptr = FPtr(file_id), and each ahead of "
       "`default:` (the server is not asked for them)",
       branch != "" and "FPtr(" not in branch and tdef.get("FL_TYPE_NET") == bt.get("FL$TYPE.NET") == 7 and sorted(tdef.values()).count(7) == 1 and sorted(bt.values()).count(7) == 1
       and ordered(branch, "case FL_TYPE:", "n = FL_TYPE_NET;", "goto set_integer;", "case FL_COLLECTION:", "n = 0;", "goto set_integer;", "case FL_FLAGS:",
                   "n = (process.program.flags & HDR_INTERNAL) ? DHF_NOCASE : 0;", "goto set_integer;", "default:", "net_fileinfo(fvar, key)")
       and re.fullmatch(r"case FL_TYPE:\s*n = FL_TYPE_NET;\s*", seg("case FL_TYPE:")) is not None and re.fullmatch(r"case FL_COLLECTION:\s*n = 0;\s*", seg("case FL_COLLECTION:")) is not None
       and re.fullmatch(r"case FL_FLAGS:\s*n = \(process\.program\.flags & HDR_INTERNAL\) \? DHF_NOCASE : 0;\s*", seg("case FL_FLAGS:")) is not None
       and branch.count("case FL_TYPE:") == 1 and branch.count("case FL_COLLECTION:") == 1 and branch.count("case FL_FLAGS:") == 1, repr((tdef, bt)))
    # ---- NK18. INDICES of a remote file is the null string
    ix1, ix2 = fn("dh_ak.c", "op_indices1"), fn("dh_ak.c", "op_indices2")
    ck("NK18 INDICES(f) and INDICES(f, name) of a NET_FILE do NOT refuse: op_indices1 and op_indices2 hold no net_refuse, no refuse_net_file and no NET_FILE arm, and keep their `default:` arm that answers the null string "
       "(a query asks it of every file; a refusal stopped every query on a remote file); the DYNAMIC_FILE arm is still the only other one",
       ix1 != "" and ix2 != "" and not re.search(r"net_refuse\(|refuse_net_file\(|NET_FILE", ix1 + ix2)
       and ordered(ix1, "switch (fvar->type) {", "case DYNAMIC_FILE:", "default:", "InitDescr(e_stack, STRING);", "(e_stack++)->data.str.saddr = NULL;")
       and ordered(ix2, "if (fvar->type == DYNAMIC_FILE) {", "} else {", "switch (fvar->type) {", "default:", "InitDescr(e_stack, STRING);", "(e_stack++)->data.str.saddr = NULL;")
       and ix1.count("case ") == 1 and ix2.count("case ") == 0, "")
    # ---- NK17. the DICT form (NK18 above: INDICES; the record cache and the gate's close are checks_3e, NK19 to NK25)
    i = vr.find('case type = "N"')
    case_n = vr[i:vr.find("\n         case 1", i)] if i >= 0 else ""
    chk = routine_body(vr, "check.n.pointer")
    ck("NK17 the DICT form of a remote file: the case adds 'dict ' (4 letters and one space, the 5 characters NET_FILE_NAME_MAX allows beyond NET_FILE_MAX) to the file name only for fno = 3 (once, on a line of its "
       "own, after the failure return of the shape test and before the pathname is built); check.n.pointer still allows no space, so a VOC entry cannot hold the prefix itself; the dictionary is not refused",
       case_n != "" and case_n.count("fno") == 1 and case_n.count("'dict '") == 1 and re.search(r"^\s*if fno = 3 then n\.file = 'dict ':n\.file\s*$", case_n, re.M) is not None
       and len("dict ") == 5 and "ER$VNF" not in case_n and chk != "" and "' '" not in chk and "dict" not in chk
       and ordered(case_n, "gosub check.n.pointer", "set.status ER$NAM", "return", "if fno = 3 then n.file = 'dict ':n.file", "pathname = ")
       and re.search(r"#define\s+NET_FILE_NAME_MAX\s+\(NET_FILE_MAX\s*\+\s*5\)", nf) is not None and re.search(r"#define\s+NET_FILE_MAX\s+63\b", nf) is not None, repr(case_n[:120]))


def checks_3e(srcs, c, ck):
    """S.65, 18 Oct 26: the record cache of netfiles.c (NK19-NK24) and K_NET closing the remote files when the account scope changes (NK25).  Text only: the
    cache's behaviour (a hit, an expiry, a copy) is sandbox-netfile.py's, and `make` is the compiler."""
    nf, kn = c["netfiles.c"], c["op_kernel.c"]

    def fn(name):
        return c_functions(nf).get(name, "")

    # ---- NK19. the constants, the include and the entry
    ent = re.search(r"typedef struct \{(.*?)\} NET_CACHE_ENTRY;", nf, re.S)
    ent = ent.group(1) if ent else ""
    ck("NK19 THE RECORD CACHE's constants: NET_CACHE_SLOTS 64, NET_CACHE_TTL 2 (seconds), NET_CACHE_REC_MAX 32768; <time.h> is included BEFORE sd.h; an entry holds used, absent, the handle AND the epoch AND the id "
       "length AND the id (MAX_ID_LEN + 1 bytes), the record chain and the time; the table is NET_CACHE_SLOTS entries and the ring cursor starts at 0",
       re.search(r"#define\s+NET_CACHE_SLOTS\s+64\b", nf) is not None and re.search(r"#define\s+NET_CACHE_TTL\s+2\b", nf) is not None and re.search(r"#define\s+NET_CACHE_REC_MAX\s+32768\b", nf) is not None
       and ordered(nf, "#include <time.h>", '#include "sd.h"') and ent != ""
       and ordered(ent, "bool used;", "bool absent;", "int16_t handle;", "u_int16_t epoch;", "int16_t id_len;", "char id[MAX_ID_LEN + 1];", "STRING_CHUNK* rec;", "time_t when;")
       and re.search(r"NET_CACHE_ENTRY\s+net_cache\[NET_CACHE_SLOTS\];", nf) is not None and re.search(r"int\s+net_cache_next\s*=\s*0;", nf) is not None, "")
    # ---- NK20. net_cache_find
    fd = fn("net_cache_find")
    ck("NK20 net_cache_find: an entry is a hit only when handle AND epoch AND id length AND the id bytes (memcmp over id_len) all agree - so one file variable's record is never given to another, nor "
       "an epoch's to the next; every used entry it passes is aged first, and one older than NET_CACHE_TTL or from the FUTURE (the clock went back) is freed and skipped, before the comparison",
       fd != "" and ordered(fd, "time(NULL)", "if (!e->used)", "continue;", "(now < e->when) || ((now - e->when) > NET_CACHE_TTL)", "net_cache_free(e);", "continue;", "(e->handle == fvar->access.net.handle)",
                            "(e->epoch == fvar->access.net.epoch)", "(e->id_len == id_len)", "(memcmp(e->id, id, id_len) == 0)", "return e;", "return NULL;")
       and re.search(r"\(e->handle == fvar->access\.net\.handle\) && \(e->epoch == fvar->access\.net\.epoch\) && \(e->id_len == id_len\) && \(memcmp\(e->id, id, id_len\) == 0\)", fd) is not None
       and fd.count("net_cache_free(") == 1, "")
    # ---- NK21. net_cache_put
    pt = fn("net_cache_put")
    ck("NK21 net_cache_put: an id of length under 1 or over MAX_ID_LEN, and a record over NET_CACHE_REC_MAX, are not kept (returned before any slot is touched); a free slot is taken first, and when there is none the "
       "OLDEST by ring (net_cache_next, advanced modulo NET_CACHE_SLOTS) after its old record is freed; the entry gets its handle, epoch, id bytes, absent flag and a COPY of the record (k_copy_string - never the "
       "caller's chain) and the time it was stored",
       pt != "" and ordered(pt, "(id_len < 1) || (id_len > MAX_ID_LEN)", "(rec != NULL) && (rec->string_len > NET_CACHE_REC_MAX)", "return;", "if (!net_cache[i].used)", "if (e == NULL) {",
                            "e = &net_cache[net_cache_next];", "net_cache_next = (net_cache_next + 1) % NET_CACHE_SLOTS;", "net_cache_free(e);", "e->used = TRUE;", "e->absent = absent;",
                            "e->handle = fvar->access.net.handle;", "e->epoch = fvar->access.net.epoch;", "e->id_len = id_len;", "memcpy(e->id, id, id_len);",
                            "e->rec = (rec != NULL) ? k_copy_string(rec) : NULL;", "e->when = time(NULL);")
       and not re.search(r"e->rec\s*=\s*rec\b", pt) and pt.count("k_copy_string(") == 1 and pt.count("net_cache_free(") == 1, "")
    # ---- NK22. free and drop
    fr, dr = fn("net_cache_free"), fn("net_cache_drop")
    ck("NK22 net_cache_free releases the record (s_free) when there is one, clears the pointer and then the used flag; net_cache_drop(0) frees every used entry and net_cache_drop(h) only the used entries of "
       "handle h - the test is `used && (handle == 0 || entry handle == h)` and nothing else",
       fr != "" and ordered(fr, "if (e->rec != NULL)", "s_free(e->rec);", "e->rec = NULL;", "e->used = FALSE;")
       and re.search(r"if \(net_cache\[i\]\.used && \(\(handle == 0\) \|\| \(net_cache\[i\]\.handle == handle\)\)\)\s*net_cache_free\(&net_cache\[i\]\);", dr) is not None
       and re.search(r"for \(i = 0; i < NET_CACHE_SLOTS; i\+\+\)", dr) is not None, "")
    # ---- NK23. net_read and net_readv
    rd, rv = fn("net_read"), fn("net_readv")
    gap = rd[rd.find("if (status < 0)"):rd.find("if (status > 0)")] if "if (status < 0)" in rd else "x"
    ck("NK23 net_read: the cache is consulted only when the file variable is not stale (a closed one is not answered from it - net_op says why), after the empty-id test and before net_op; a hit on an ABSENT "
       "entry is ER_RNF, any other hit is a COPY of the cached chain (never the chain itself, which the caller may change or free); after net_op a record is put (what was read, FALSE), an ABSENT entry only "
       "when the status is exactly ER_RNF (not for any other positive status), and nothing at all on an error; net_cache_find is called here only, net_cache_put twice; net_readv does not use the cache",
       rd != "" and ordered(rd, "if (id_len < 1)", "return ER_IID;", "if (!net_stale(fvar)) {", "net_cache_find(fvar, id, id_len)", "if (hit->absent)", "return ER_RNF;",
                            "*rec = (hit->rec != NULL) ? k_copy_string(hit->rec) : NULL;", "return 0;", "net_op(fvar, NF_READ", "if (status < 0)", "return net_raise(status, entry);",
                            "if (status > 0) {", "if (status == ER_RNF)", "net_cache_put(fvar, id, id_len, NULL, TRUE);", "return status;", "*rec = net_take_string(&out);", "k_release(&out);",
                            "net_cache_put(fvar, id, id_len, *rec, FALSE);", "return 0;")
       and inside(rd, "if (!net_stale(fvar)) {", "net_cache_find(") and not re.search(r"\*rec\s*=\s*hit->rec", rd) and "net_cache_put(" not in gap
       and rd.count("net_cache_put(") == 2 and nf.count("net_cache_find(") == 2 and nf.count("net_cache_put(") == 3      # a definition and the uses
       and rv != "" and "net_cache" not in rv, "")
    # ---- NK24. where the entries go
    ns, cl, ca = fn("net_select"), fn("net_close"), fn("net_close_all")
    ck("NK24 the entries of a file variable go when it is SELECTed again (net_select drops that handle BEFORE net_op), when it is closed (net_close drops that handle - only a real handle, `handle > 0`, since "
       "drop(0) would drop everything - BEFORE the net_stale test and before the handle is zeroed, so a stale or already queued variable loses them too) and when the connections are dropped (net_close_all: "
       "net_cache_drop(0), right after the epoch moves and BEFORE the `net_used` return, so it happens even when nothing was opened); net_cache_drop is called from nowhere else",
       ns != "" and ordered(ns, "net_cache_drop(fvar->access.net.handle);", "net_op(fvar, NF_SELECT")
       and ordered(cl, "fvar->type != NET_FILE", "handle = fvar->access.net.handle;", "if (handle > 0)", "net_cache_drop(handle);", "if (net_stale(fvar))", "fvar->access.net.handle = 0;")
       and ordered(ca, "net_epoch++;", "net_pending_ct = 0;", "net_cache_drop(0);", "if (!net_used)", "net_call_raw(NF_CLOSEALL")
       and nf.count("net_cache_drop(") == 4, "")
    # ---- NK25. K_NET closes the remote files when the gate is set
    i = kn.find("case K_NET:")
    blk = kn[i:kn.find("case K_EDIT_OK:", i)] if i >= 0 else ""
    after = blk[blk.find("net_close_all();"):] if "net_close_all();" in blk else "descr"
    ck("NK25 K_NET: a $internal caller that SETS the gate (n >= 0) changes the bit, computes the answer, saves process.status in n, calls net_close_all() (the remote files and connections belong to the account "
       "scope that ended), restores process.status and leaves - in that order, the call AFTER the bit is changed and inside the HDR_INTERNAL block; the -1 ask form and a caller that is not $internal never call "
       "it (net_close_all appears once in the case); nothing uses `descr` after the call, because the handler is BASIC and moves the e-stack",
       blk != "" and blk.count("net_close_all()") == 1
       and ordered(blk, "if (n >= 0) {", "if (process.program.flags & HDR_INTERNAL) {", "my_uptr->gates |= UG_NET;", "my_uptr->gates &= (u_int16_t)~UG_NET;",
                   "result.data.value = (my_uptr->gates & UG_NET) != 0;", "n = process.status;", "net_close_all();", "process.status = n;", "break;", "result.data.value = (my_uptr->gates & UG_NET) != 0;", "break;")
       and inside(blk, "if (process.program.flags & HDR_INTERNAL) {", "net_close_all()") and "descr" not in after, "")


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
mut("K_NET always answers 1", "op_kernel.c", "      }\n      result.data.value = (my_uptr->gates & UG_NET) != 0;", "      }\n      result.data.value = 1;")
mut("K_NET always answers 1 when it sets the gate", "op_kernel.c", "          result.data.value = (my_uptr->gates & UG_NET) != 0;\n          n = process.status;", "          result.data.value = 1;\n          n = process.status;")
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
mut("sd_tls_client_end no longer blocks SIGPIPE for the close_notify", "sd_tls.c", after("void sd_tls_client_end(SD_TLS_CLIENT* c) {", "pthread_sigmask(SIG_BLOCK, &pipe_only, &old_mask);", ""))
mut("sd_tls_client_end shuts down before the signal is blocked", "sd_tls.c", after("void sd_tls_client_end(SD_TLS_CLIENT* c) {", "(void)SSL_shutdown(c->ssl);", "/* gone */"))
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


# ---- slice 2c: the files-only route ---------------------------------------------------------------------------------------------------
AFO, AP2, MOD, CRA, CAC = "apifilesok", "apisrvr", "modifya", "createa", "create_account"
# !apifilesok: every number of the list, taken out of the table, one at a time (a request the server then refuses a files-only client)
for _n in FILES_ALLOWED:
    mut("apifilesok: %d is taken out of the table" % _n, AFO, "files.ok := '%d,'" % _n, "files.ok := ''")
# ...and every kind of number that must stay refused, put into it, one at a time (the first four and the last are the ones the owner named: execute, call, logins, SDNet)
for _n in (0, 3, 20, 21, 22, 23, 24, 25, 27, 28, 29, 47, 48, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 80):
    mut("apifilesok: %d is put into the table" % _n, AFO, "files.ok := '49,'", "files.ok := '49,'\nfiles.ok := '%d,'" % _n)
mut("apifilesok: one line holds two numbers (49,21)", AFO, "files.ok := '49,'", "files.ok := '49,21,'")
mut("apifilesok: the table starts from nothing (the first number cannot match)", AFO, "files.ok = ','", "files.ok = ''")
mut("apifilesok: 3 is allowed always", AFO, "if entered then return 0", "if 0 then return 0")
mut("apifilesok: 3 is refused always", AFO, "if entered then return 0", "return 0")
mut("apifilesok: 3 is not special (it falls to the table)", AFO, "if action = 3 then", "if action = 3 and 0 then")
mut("apifilesok: an empty action is tested no more", AFO, "if action = '' then return 0\n", "")
mut("apifilesok: a non-number is tested no more", AFO, "if not(num(action)) then return 0\n", "")
mut("apifilesok: the table is searched without its commas (4 matches 49)", AFO, "',' : action : ','", "action")
mut("apifilesok: the default is yes", AFO, rx(r"(if index\(files\.ok[^\n]*\n\s*)return 0", r"\g<1>return 1"))
mut("apifilesok: an unknown number is yes", AFO, "if index(files.ok, ',' : action : ',', 1) then return 1", "if index(files.ok, ',' : action : ',', 1) or action > 69 then return 1")
mut("apifilesok: it is not $internal", AFO, "$internal\nfunction", "function")
mut("apifilesok: it is catalogued under another name", AFO, "$catalog !apifilesok", "$catalog !apifilesk")
mut("apifilesok: it asks the kernel something", AFO, "$catalog !apifilesok\n", "$catalog !apifilesok\nx = kernel(K$USERNAME, 0)\n")
mut("apifilesok: it writes something", AFO, "$catalog !apifilesok\n", "$catalog !apifilesok\nwriteseq 'x' to zz else null\n")
# apisrvr: the declaration, the mark, the order of the route
mut("apisrvr: the mark is a plain variable (not in the common block)", AP2, "files.only,         ;*", "files.zz,           ;*")
mut("apisrvr: the mark is not started false", AP2, "   files.only = @false\n", "")
mut("apisrvr: the mark is started false twice", AP2, "   files.only = @false\n", "   files.only = @false\n   files.only = @false\n")
mut("apisrvr: the mark is started at EVERY entry (an abort would clear it), not in the first-time block",
    AP2, lambda t: t.replace("   files.only = @false\n", "", 1).replace("if not(kernel(K$CPROC.LEVEL,0)) then", "files.only = @false\nif not(kernel(K$CPROC.LEVEL,0)) then", 1))
mut("apisrvr: the mark is cleared after the login", AP2, "               response = 'v=' : scram.ssig\n               logged.in = @true\n",
    "               response = 'v=' : scram.ssig\n               logged.in = @true\n               files.only = @false\n")
mut("apisrvr: the mark is cleared at an SDLogto", AP2, "if not(master.login.done) then\n   master.login.done = @true", "files.only = @false\nif not(master.login.done) then\n   master.login.done = @true")
mut("apisrvr: the mark is set for everybody", AP2, "if api.files.login then\n                  files.only = @true", "if @true then\n                  files.only = @true")
mut("apisrvr: the mark is never set", AP2, "files.only = @true", "files.zz = @true")
mut("apisrvr: the mark is set before the identity is assumed",
    AP2, lambda t: t.replace("                  files.only = @true\n", "", 1).replace("               if not(kernel(K$ASSUME.USER, scram.user)) then", "               files.only = api.files.login\n               if not(kernel(K$ASSUME.USER, scram.user)) then", 1))
mut("apisrvr: the sdusers test is gone", AP2, "if not(is_grp_member(scram.user, 'sdusers')) then", "if 0 then")
mut("apisrvr: sdfiles is read before sdapi",
    AP2, lambda t: t.replace("is_grp_member(scram.user, 'sdapi')", "is_grp_member(scram.user, 'sdfiles') ;* swapped", 1).replace("api.in.sdfiles = is_grp_member(scram.user, 'sdfiles')", "api.in.sdfiles = is_grp_member(scram.user, 'sdapi')", 1))
mut("apisrvr: sdapi does not win (the sdfiles route is read for everybody)", AP2, "                  if not(api.in.sdapi) then\n", "                  if @true then\n")
mut("apisrvr: a member of sdapi is marked files-only too", AP2, "                     api.files.login = @true\n", "                     api.files.login = @true\n                  end\n                  if api.in.sdapi then\n                     api.files.login = @true\n")
mut("apisrvr: neither group is not refused", AP2, "if not(api.in.sdfiles) then", "if 0 then")
mut("apisrvr: neither group gives another reason", AP2, "scram.refuse.reason = 'not a member of sdapi'", "scram.refuse.reason = 'not a member of sdfiles'")
mut("apisrvr: neither group gives another message", AP2, "                        scram.refuse.reason = 'not a member of sdapi'\n                        abort.message = sysmsg(10073, scram.user)",
    "                        scram.refuse.reason = 'not a member of sdapi'\n                        abort.message = sysmsg(5009)")
mut("apisrvr: the sdfiles lookup that cannot answer is not looked at", AP2, "if api.files.stat # 0 then", "if 0 then")
mut("apisrvr: the sdfiles status is not read", AP2, "api.files.stat = status()", "api.files.stat = 0")
mut("apisrvr: the sdapi lookup that cannot answer is not looked at", AP2, "if api.route.stat # 0 then", "if 0 then")
mut("apisrvr: an unreadable sdfiles route is let in", AP2, "scram.refuse.reason = 'the sdfiles route could not be read, status ' : api.files.stat\n",
    "scram.refuse.reason = 'the sdfiles route could not be read, status ' : api.files.stat\n                        api.files.login = @true\n")
mut("apisrvr: sdsys is not exempt by name", AP2, "if not(downcase(scram.user) = 'sdsys') then", "if @true then")
mut("apisrvr: sdsys's name is compared in the case it was typed", AP2, "if not(downcase(scram.user) = 'sdsys') then", "if not(scram.user = 'sdsys') then")
mut("apisrvr: the login by this route is not audited", AP2, drop_line(r"'api login route=sdfiles user='"))
mut("apisrvr: the login audit line is upper case", AP2, "'api login route=sdfiles user='", "'API LOGIN route=sdfiles user='")
mut("apisrvr: the login audit line names the wrong route", AP2, "'api login route=sdfiles user='", "'api login route=sdapi user='")
# apisrvr: the gate
mut("apisrvr: the gate is not taken", AP2, "   if files.only then\n", "   if 0 then\n")
mut("apisrvr: the gate is taken for every session", AP2, "   if files.only then\n", "   if @true then\n")
mut("apisrvr: the gate asks no function", AP2, "if not(apifilesok(action, master.login.done)) then", "if 0 then")
mut("apisrvr: the account is always 'not yet entered' (3 allowed for ever)", AP2, "apifilesok(action, master.login.done)", "apifilesok(action, @false)")
mut("apisrvr: the account is always 'entered' (the first 3 is refused)", AP2, "apifilesok(action, master.login.done)", "apifilesok(action, @true)")
mut("apisrvr: the refusal does not skip the dispatch", AP2, "         goto return.status.set\n", "         null\n")
mut("apisrvr: the refusal is not an error answer", AP2, "         server.error = SV$ON.ERROR\n         abort.message = sysmsg(11480, action)", "         abort.message = sysmsg(11480, action)")
mut("apisrvr: the refusal says another message", AP2, "sysmsg(11480, action)", "sysmsg(5270)")
mut("apisrvr: the refusal does not name the request", AP2, "sysmsg(11480, action)", "sysmsg(11480)")
mut("apisrvr: the refusal is not audited", AP2, drop_line(r"'api refused request='"))
mut("apisrvr: the refusal audit line is upper case", AP2, "'api refused request='", "'API REFUSED request='")
mut("apisrvr: the refusal audit line has no route", AP2, " route=sdfiles user=' : @logname)", " user=' : @logname)")
mut("apisrvr: the refusal audit line uses a plain variable that an abort loses", AP2, "' route=sdfiles user=' : @logname)", "' route=sdfiles user=' : logname)")
mut("apisrvr: the gate comes after the dispatch",
    AP2, lambda t: t.replace(t[t.index("   if files.only then\n"):t.index("   cproc.date = date()")], "", 1).replace("   st = status()\nreturn.status.set:", t[t.index("   if files.only then\n"):t.index("   cproc.date = date()")] + "   st = status()\nreturn.status.set:", 1))
mut("apisrvr: the gate comes before the not-logged-in test",
    AP2, lambda t: t.replace(t[t.index("   if files.only then\n"):t.index("   cproc.date = date()")], "", 1).replace("   if not(logged.in) then\n      * 14 Sep 26 dm - 47 and 48", t[t.index("   if files.only then\n"):t.index("   cproc.date = date()")] + "   if not(logged.in) then\n      * 14 Sep 26 dm - 47 and 48", 1))
mut("apisrvr: a second use of the function (a second gate that lets 20 through)", AP2, "   cproc.date = date()\n", "   if files.only and action = 20 then null\n   if apifilesok(action, 1) then null\n   cproc.date = date()\n")
mut("apisrvr: master.login.done is set at another place too", AP2, "   tty = 'apisrvr'\n", "   tty = 'apisrvr'\n   master.login.done = @true\n")
# MODIFY.ACCOUNT
mut("modifya: the word FILES-ON is not a word", MOD, "case action = 'FILES-ON'", "case action = 'FILES-ONX'")
mut("modifya: the word FILES-OFF is not a word", MOD, "case action = 'FILES-OFF'", "case action = 'FILES-OFX'")
mut("modifya: FILES-ON asks for off", MOD, "files.want = @true\n         gosub set.files", "files.want = @false\n         gosub set.files")
mut("modifya: FILES-OFF asks for on", MOD, "files.want = @false\n         gosub set.files", "files.want = @true\n         gosub set.files")
mut("modifya: the syntax lines do not name the words", MOD, drop_line(r"modify\.account <account> files-on \| files-off"))
mut("modifya: the list of words does not name them", MOD, "files-on, files-off, suspended or unsuspended", "suspended or unsuspended")
mut("modifya: set.files lets a group account through", MOD, "   if group.name[1,4] # 'sdu_' then\n      @system.return.code = -ER$FAILED\n      if group.name[1,4] = 'sdg_' then",
    "   if 0 then\n      @system.return.code = -ER$FAILED\n      if group.name[1,4] = 'sdg_' then")
mut("modifya: a group account is told 10081 and not 10087", MOD, "crt sysmsg(10087, acc.name)  ;* %1 is a group account and has no remote access; reach it with logto\n      end else\n         crt sysmsg(10081, acc.name, 2)",
    "crt sysmsg(10081, acc.name, 2)\n      end else\n         crt sysmsg(10081, acc.name, 2)")
mut("modifya: the Linux user is not checked for its name", MOD, "if not(valid_os_name(files.user)) then", "if 0 then")
mut("modifya: the Linux user comes from the account name", MOD, "files.user = group.name[5,999]", "files.user = acc.name")
mut("modifya: membership is not read three-valued", MOD, "has.files = is_grp_member(files.user, 'sdfiles')\n   files.stat = status()", "has.files = is_grp_member(files.user, 'sdfiles')\n   files.stat = 0")
mut("modifya: FILES-ON does not need sdusers", MOD, "in.sdusers = is_grp_member(files.user, 'sdusers')", "in.sdusers = @true")
mut("modifya: FILES-OFF needs sdusers too", MOD, "if files.stat = 0 and files.want then\n      in.sdusers", "if files.stat = 0 then\n      in.sdusers")
mut("modifya: already in the state is not noticed", MOD, "if has.files = files.want then", "if 0 then")
mut("modifya: the group's existence is not checked", MOD, "files.found = is_group('sdfiles')", "files.found = @true")
mut("modifya: FILES-ON adds to sdapi", MOD, "addgroup \" : files.user : \" sdfiles\"", "addgroup \" : files.user : \" sdapi\"")
mut("modifya: FILES-OFF takes the person out of sdapi", MOD, "delgroup \" : files.user : \" sdfiles\"", "delgroup \" : files.user : \" sdapi\"")
mut("modifya: the helper is not sd-elevate", MOD, "sudo /usr/local/sbin/sd-elevate addgroup \" : files.user", "sudo /usr/sbin/usermod -aG sdfiles \" : files.user")
mut("modifya: the change is not read back", MOD, "now.files = is_grp_member(files.user, 'sdfiles')", "now.files = files.want")
mut("modifya: a read back that differs is a success", MOD, "if files.stat = 0 and now.files # files.want then files.stat = 2", "null")
mut("modifya: the line shows the request and not the read back", MOD, "crt sysmsg(11482, acc.name, if now.files then 'yes' else 'no')", "crt sysmsg(11482, acc.name, if files.want then 'yes' else 'no')")
mut("modifya: the audit line is upper case",
    MOD, "void kernel(K$AUDIT, 'modify.account ' : downcase(action) : ' account=' : acc.name)\n   crt sysmsg(11482", "void kernel(K$AUDIT, 'MODIFY.ACCOUNT ' : action : ' account=' : acc.name)\n   crt sysmsg(11482")
mut("modifya: the audit line is written before the change",
    MOD, lambda t: t.replace("   void kernel(K$AUDIT, 'modify.account ' : downcase(action) : ' account=' : acc.name)\n   crt sysmsg(11482", "   crt sysmsg(11482", 1).replace("   if files.want then\n      files.found = is_group('sdfiles')", "   void kernel(K$AUDIT, 'modify.account ' : downcase(action) : ' account=' : acc.name)\n   if files.want then\n      files.found = is_group('sdfiles')", 1))
mut("modifya: a failed change is reported as done", MOD, "   if files.stat # 0 then\n      @system.return.code = -ER$FAILED\n      crt sysmsg(10081, acc.name, files.stat)\n      return\n   end\n\n   @system.return.code = 0\n   void kernel",
    "   @system.return.code = 0\n   void kernel")
# CREATEA and CREATE.ACCOUNT
mut("createa: FILES-ON is not a word", CRA, "case upcase(token) = 'FILES-ON'", "case upcase(token) = 'FILES-ONX'")
mut("createa: FILES-ON sets the NET gate", CRA, "settings<CA$FILES> = 1", "settings<CA$NET> = 1")
mut("createa: FILES-ON sets the setting to 2", CRA, "settings<CA$FILES> = 1", "settings<CA$FILES> = 2")
mut("createa: the syntax line does not name it", CRA, " {files-on}", "")
mut("createacc.h: CA$FILES is 35 (the NET setting's number)", "createacc.h", rx(r"(\$define\s+CA\$FILES\s+)36", r"\g<1>35"))
mut("createacc.h: CA$FILES is not defined", "createacc.h", drop_line(r"\$define\s+CA\$FILES"))
mut("create_account: any non-zero setting is a request", CAC, "files.want = (settings<CA$FILES> = 1)", "files.want = (settings<CA$FILES> # 0)")
mut("create_account: the group is not looked for", CAC, "files.found = is_group('sdfiles')", "files.found = @true")
mut("create_account: a missing group is not told", CAC, "if not(files.found) then\n         @system.return.code = -ER$FAILED\n         err = 10024:@vm:'sdfiles'", "if 0 then\n         @system.return.code = -ER$FAILED\n         err = 10024:@vm:'sdfiles'")
mut("create_account: an unreadable /etc/group is not looked at", CAC, "if files.stat # 0 then\n         @system.return.code = -ER$FAILED\n         err = 10081:@vm:acc.uname:@vm:files.stat", "if 0 then\n         @system.return.code = -ER$FAILED\n         err = 10081:@vm:acc.uname:@vm:files.stat")
mut("create_account: the group is looked for AFTER the Linux user is made",
    CAC, lambda t: (lambda m: t.replace(m.group(1), "", 1).replace("      if not(is_grp_member(acc.uname,'sdusers')) then", m.group(1) + "      if not(is_grp_member(acc.uname,'sdusers')) then", 1))(
        re.search(r"(\* 17 Oct 26 dm - S\.65 slice 2c: the group sdfiles is looked for.*?\n     end\n)", t, re.S)))
mut("create_account: a GROUP account is not refused", CAC, "if files.want then\n       @system.return.code = -ER$ARGS\n       err = 10087:@vm:acc.name ;* %1 is a group account and has no remote access\n       goto exit.create",
    "if 0 then\n       @system.return.code = -ER$ARGS\n       err = 10087:@vm:acc.name ;* %1 is a group account and has no remote access\n       goto exit.create")
mut("create_account: an OTHER account is not refused", CAC, "if files.want then\n       @system.return.code = -ER$ARGS\n       err = 10081:@vm:acc.name:@vm:2", "if 0 then\n       @system.return.code = -ER$ARGS\n       err = 10081:@vm:acc.name:@vm:2")
mut("create_account: the join goes to sdapi", CAC, "sd-elevate addgroup \":acc.uname:\" sdfiles\"", "sd-elevate addgroup \":acc.uname:\" sdapi\"")
mut("create_account: the join is not asked for", CAC, "      if files.want then\n         os.execute \"sudo /usr/local/sbin/sd-elevate addgroup \":acc.uname:\" sdfiles\"", "      if @true then\n         os.execute \"sudo /usr/local/sbin/sd-elevate addgroup \":acc.uname:\" sdfiles\"")
mut("create_account: a failed join is not reported", CAC, "         route.stat = OS.ERROR()\n         if route.stat # 0 then", "         route.stat = OS.ERROR()\n         if 0 then")
mut("create_account: the state line shows the request", CAC, "if is_grp_member(acc.uname, 'sdfiles') then 'yes' else 'no'", "if files.want then 'yes' else 'no'")
mut("create_account: the state line is not printed", CAC, drop_line(r"crt sysmsg\(11482,"))
mut("a register field ACC$FILES is added", "syscom/keys.h", lambda t: t + "\n$define ACC$FILES            16\n")
# the manifest and the restore
mut("acc_os_info: the manifest key is `files`", "acc_os_info", "'route.files: '", "'files: '")
mut("acc_os_info: the manifest asks sdapi", "acc_os_info", "is_grp_member(user, 'sdfiles')", "is_grp_member(user, 'sdapi')")
mut("acc_os_info: the manifest has no route.files", "acc_os_info", drop_line(r"'route\.files: '"))
mut("acc_os_info: route.files is written for a group account too", "acc_os_info", "      case grp[1,4] = 'sdg_'\n", "      case grp[1,4] = 'sdg_'\n         info<-1> = 'route.files: 0'\n")
mut("restorea: the key route.files is not read", "restorea", "= 'route.files' ; m.route.files = kv", "= 'route.filez' ; m.route.files = kv")
mut("restorea: the key route.files is read into the file count", "restorea", "= 'route.files' ; m.route.files = kv", "= 'route.files' ; m.files = kv")
mut("restorea: it is not handed on", "restorea", "settings<CA$FILES> = m.route.files", "settings<CA$FILES> = m.files")
mut("restorea: it is not cleared for each section", "restorea", " ; m.route.files = ''", "")
mut("restorea: the file count is lost", "restorea", "case sec.keys<s.idx,kp> = 'files'       ; m.files = kv", "case sec.keys<s.idx,kp> = 'filez'       ; m.files = kv")
mut("backupa: the file count is renamed route.files", "bp:backupa", "m<-1> = 'files: ':files", "m<-1> = 'route.files: ':files")
# the group
mut("the installer does not make sdfiles", "installsdcore.sh", "for sd_route_group in sdssh sdapi sdfiles; do", "for sd_route_group in sdssh sdapi; do")
mut("the installer makes sdfiles a login group", "installsdcore.sh", "sudo groupadd --system \"$sd_route_group\"", "sudo groupadd \"$sd_route_group\"")
mut("deletesdcore does not remove sdfiles", "deletesdcore.sh", "for sd_route_group in sdssh sdapi sdfiles; do", "for sd_route_group in sdssh sdapi; do")
mut("deletesdcore says it kept two groups", "deletesdcore.sh", "route groups sdssh, sdapi and sdfiles were kept", "route groups sdssh and sdapi were kept")
mut("deletesdcore removes sdfiles when the accounts are kept", "deletesdcore.sh", "else\n    echo \"sd ACCOUNTS were saved", "else\n    sudo groupdel sdfiles\n    echo \"sd ACCOUNTS were saved")
mut("sd-elevate does not whitelist sdfiles", "sd-elevate", "sdusers|sdssh|sdapi|sdfiles) : ;;", "sdusers|sdssh|sdapi) : ;;")
mut("sd-elevate whitelists sdfiles* (a prefix)", "sd-elevate", "sdusers|sdssh|sdapi|sdfiles) : ;;", "sdusers|sdssh|sdapi|sdfiles*) : ;;")
mut("sd-elevate lets groupdel delete sdfiles", "sd-elevate", "      sdusers|sdssh|sdapi|sdfiles)\n        die", "      sdusers|sdssh|sdapi)\n        die")
mut("sd-elevate's refusal does not name sdfiles", "sd-elevate", "(want sdusers, sdssh, sdapi, sdfiles, sdu_*, or sdg_*)", "(want sdusers, sdssh, sdapi, sdu_*, or sdg_*)")
# the messages
mut("message 11480 is missing", "msg:11480", lambda t: None)
mut("message 11480 says another thing", "msg:11480", lambda t: t.replace("files only", "files and more", 1))
mut("message 11480 loses its place for the request", "msg:11480", lambda t: t.replace("%1", "", 1))
mut("message 11482 is two lines", "msg:11482", lambda t: t.rstrip("\n") + "\nsecond line\n")
mut("message 11482 says NET", "msg:11482", lambda t: t.replace("FILES", "NET", 1))
mut("message 11481 is cited by a program", "bp:cd", lambda t: t + "\n   crt sysmsg(11481)\n")
mut("a program cites 11483", "bp:cd", lambda t: t + "\n   crt sysmsg(11483)\n")
mut("a second program cites 11480", "bp:cd", lambda t: t + "\n   crt sysmsg(11480, 1)\n")
mut("another program reads the mark", "bp:cd", lambda t: t + "\n   if files.only then null\n")
mut("the login prints something on success", AP2, "                  files.only = @true\n", "                  files.only = @true\n                  crt 'files only'\n")


# ---- slice 3a: the class logs in from the stored keys ---------------------------------------------------------------------------------------
SCL = "bp:sdclient"
mut("connect.keys: the parameters are by reference", SCL, "public function connect.keys(host, (port), username, (salt), (iterations), (client.key), (server.key), account, (pin))",
    "public function connect.keys(host, (port), username, salt, iterations, client.key, server.key, account, pin)")
mut("connect.keys: the pin comparison is gone", SCL, "if ('p' : spki) # ('p' : pin) then", "if 0 then")
mut("connect.keys: the pin is compared as numbers", SCL, "if ('p' : spki) # ('p' : pin) then", "if spki # pin then")
mut("connect.keys: the hash is not required", SCL, "   if spki = '' then\n      error = 'The server gave no public key hash", "   if 0 then\n      error = 'The server gave no public key hash")
mut("connect.keys: something is sent before the pin is checked", SCL, "   spki = downcase(trim(socket.info(skt, SKT$INFO.TLS.SPKI)))",
    "   void message.pair(SrvrRevision, '')\n   spki = downcase(trim(socket.info(skt, SKT$INFO.TLS.SPKI)))")
mut("connect.keys: the Ack is read before the pin is checked", SCL, "   spki = downcase(trim(socket.info(skt, SKT$INFO.TLS.SPKI)))",
    "   void read.socket(skt, 1, SKT$BLOCKING, 5000)\n   spki = downcase(trim(socket.info(skt, SKT$INFO.TLS.SPKI)))")
mut("connect.keys: the pin is not lowered", SCL, "   pin = downcase(trim(pin))", "   pin = trim(pin)")
mut("connect.keys: the pin's shape is not checked", SCL, "if len(pin) # 64 or len(convert('0123456789abcdef', '', pin)) # 0 then", "if 0 then")
mut("connect.keys: no connect timeout", SCL, "SKT$BLOCKING + SKT$TLS, NET.CONNECT.SECS)", "SKT$BLOCKING + SKT$TLS)")
mut("connect.keys: the socket is opened without TLS", SCL, "SKT$BLOCKING + SKT$TLS, NET.CONNECT.SECS)", "SKT$BLOCKING, NET.CONNECT.SECS)")
mut("connect.keys: the Ack wait is for ever", SCL, "      b = read.socket(skt, 1, SKT$BLOCKING, io.ms)", "      b = read.socket(skt, 1, SKT$BLOCKING, 0)")
mut("connect.keys: the Ack loop has no limit", SCL, "   until acked or tries >= NET.ACK.TRIES", "   until acked")
mut("connect.keys: the read bound is always 30 s (settimeout() before it is lost)", SCL, "   if io.ms = 0 then io.ms = NET.READ.MS", "   io.ms = NET.READ.MS")
mut("connect.keys: the iteration bounds are not checked", SCL, "   if iterations < SCRAM$MIN.ITER or iterations > SCRAM$MAX.ITER then\n      error = 'The stored iteration count is unacceptable'",
    "   if 0 then\n      error = 'The stored iteration count is unacceptable'")
mut("connect.keys: an incomplete login is let through", SCL, "if salt = '' or client.key = '' or server.key = '' then", "if salt = '' then")
mut("connect.keys: a connected object is let through", SCL, "   if context # CX.DISCONNECTED then\n      error = 'A connection has already been established'", "   if 0 then\n      error = 'A connection has already been established'")
mut("connect.keys: the keys are not dropped after the exchange", SCL, "   client.key = ''\n   server.key = ''\n   if not(ok) then", "   if not(ok) then")
mut("connect.keys: keys.fail leaves the socket open", SCL, "keys.fail:\n   client.key = ''\n   server.key = ''\n   close.socket skt", "keys.fail:\n   client.key = ''\n   server.key = ''")
mut("connect.keys: keys.fail does not drop the keys", SCL, "keys.fail:\n   client.key = ''\n   server.key = ''\n   close.socket skt", "keys.fail:\n   close.socket skt")
mut("connect.keys: a refused account is let through", SCL, "   if server.error # SV$OK then\n      error = 'The server did not enter the account'", "   if 0 then\n      error = 'The server did not enter the account'")
mut("connect.keys: a failed account is not a failure", SCL, "   if not(message.pair(SrvrAccount, account)) then\n      if error = '' then error = 'No reply from ' : host : ':' : port : ' when entering the account'\n      goto keys.fail\n   end",
    "   void message.pair(SrvrAccount, account)")
mut("connect.keys: a failure returns without keys.fail", SCL, "         error = 'No acknowledgement from ' : host : ':' : port : ' at the start of the session'\n         goto keys.fail\n      end\n      if b = char(6)",
    "         error = 'No acknowledgement from ' : host : ':' : port : ' at the start of the session'\n         return @false\n      end\n      if b = char(6)")
mut("connect.keys: a text names the ClientKey", SCL, "error = 'Server signature did not verify'", "error = 'Server signature did not verify ' : expect.v")
mut("connect.keys: it displays the pin", SCL, "   pin = downcase(trim(pin))", "   pin = downcase(trim(pin))\n   display pin")
mut("scram.exchange: the salt is not compared", SCL, "if ('s' : salt) # ('s' : stored.salt) then", "if 0 then")
mut("scram.exchange: the salt is compared as numbers", SCL, "if ('s' : salt) # ('s' : stored.salt) then", "if salt # stored.salt then")
mut("scram.exchange: the count is not compared", SCL, "if iter + 0 # stored.iter + 0 then", "if 0 then")
mut("scram.exchange: the stored mode is never taken", SCL, "   if keys.mode then", "   if 0 then")
mut("scram.exchange: the stored mode is taken for a password", SCL, "   keys.mode = (stored.ck # '')", "   keys.mode = @true")
mut("scram.exchange: a refused salt keeps the stored keys", SCL, "error = \"The server's salt is not the stored one: the stored login is out of date or this is not the server it was made with\"\n         stored.ck = '' ; stored.sk = ''",
    "error = \"The server's salt is not the stored one: the stored login is out of date or this is not the server it was made with\"")
mut("scram.exchange: the compare comes after the nonce check no more (before client-first)", SCL, "   if not(message.pair(SrvrScramFirst, 'p=tls-exporter,,' : cfirst.bare)) then return @false",
    "   if keys.mode and ('s' : stored.salt) # ('s' : '') then return @false\n   if not(message.pair(SrvrScramFirst, 'p=tls-exporter,,' : cfirst.bare)) then return @false")
mut("scram.exchange: the working keys are not dropped", SCL, "   client.key = ''\n   srvr.key = ''\n   stored.key = ''\n   client.sig = ''", "   client.key = ''\n   srvr.key = ''\n   client.sig = ''")
mut("scram.exchange: the server signature is compared with =", SCL, "SDEXT(in.pkt[3,999999] : @FM : expect.v, @TRUE, SD_CTEQUAL) # '1'", "in.pkt[3,999999] # expect.v")
mut("scram.exchange: the server's signature is not required", SCL, "   if in.pkt[1,2] # 'v=' then", "   if 0 then")
mut("scram.login is not a wrapper", SCL, "   return scram.exchange(username, password, '', '', '', '')\nend", "   return scram.exchange(username, password, '', '', '', '') and @true\nend")
mut("connect() calls connect.keys", SCL, "   if not(scram.login(username, password)) then", "   if not(obj->connect.keys(host, port, username, '', 4096, '', '', account, '')) then")
mut("connect() waits with a bound", SCL, "      until read.socket(skt, 1, SKT$BLOCKING, 0) = char(6)", "      until read.socket(skt, 1, SKT$BLOCKING, io.ms) = char(6)")
mut("connect() opens with a timeout", SCL, "   skt = open.socket(host, port, SKT$BLOCKING + SKT$TLS)\n   if status() then", "   skt = open.socket(host, port, SKT$BLOCKING + SKT$TLS, 5)\n   if status() then")
mut("connect() asks a pin", SCL, "   if not(scram.login(username, password)) then", "   if socket.info(skt, SKT$INFO.TLS.SPKI) = '' then return @false\n   if not(scram.login(username, password)) then")
mut("read.packet's header read waits for ever", SCL, "      s = read.socket(skt, n, SKT$BLOCKING, io.ms)\n      if status() then return @false\n      pkt.header := s",
    "      s = read.socket(skt, n, SKT$BLOCKING, 0)\n      if status() then return @false\n      pkt.header := s")
mut("read.packet's data read waits for ever", SCL, "      s = read.socket(skt, n, SKT$BLOCKING, io.ms)\n      if status() then return @false\n      if debugging then",
    "      s = read.socket(skt, n, SKT$BLOCKING, 0)\n      if status() then return @false\n      if debugging then")
mut("create.object does not start io.ms", SCL, "   debugging = @false\n   io.ms = 0\nend", "   debugging = @false\nend")
mut("settimeout takes a negative", SCL, "if not(num(ms)) or ms < 0 then abort 'Illegal timeout'", "if not(num(ms)) then abort 'Illegal timeout'")
mut("settimeout does not set the bound", SCL, "   io.ms = ms + 0\nend", "   null\nend")
mut("NET.CONNECT.SECS is 50", SCL, "$define NET.CONNECT.SECS  5 ", "$define NET.CONNECT.SECS  50")
mut("NET.READ.MS is 0", SCL, "$define NET.READ.MS   30000", "$define NET.READ.MS       0")
mut("NET.ACK.TRIES is 1", SCL, "$define NET.ACK.TRIES    16", "$define NET.ACK.TRIES     1")
mut("the class text for a pin mismatch changes", SCL, "'PIN MISMATCH: the public key of '", "'PIN MISSMATCH: the public key of '")
mut("the class text for a stale salt changes", SCL, "The server's salt is not the stored one: the stored login", "The server salt is not the stored one: the stored login")
mut("sdclient's history line is gone", SCL, "* 17 Oct 26 dm S.65 slice 3a: connect.keys()", "* 17 Oct 26 dm slice 3a: connect.keys()")
mut("sdclient's description does not list connect.keys", SCL, "* bool = obj->connect.keys(host, port, username, salt, iterations, client.key, server.key, account, pin)\n", "")
mut("regress.sh does not list netfile", "regress.sh", ' editgates net netfile"', ' editgates net"')
mut("regress.sh lists netfile twice", "regress.sh", ' editgates net netfile"', ' editgates net netfile netfile"')
mut("the map does not select netfile for sdclient", "regress-map.txt", "sdsys/gpl.bp/sdclient        : qmclient netfile net", "sdsys/gpl.bp/sdclient        : qmclient net")
mut("the map does not select netfile for netcred", "regress-map.txt", "sdsys/gpl.bp/netcred         : net netfile", "sdsys/gpl.bp/netcred         : net")
mut("the map does not select netfile for setnetlogin", "regress-map.txt", "sdsys/gpl.bp/setnetlogin     : net netfile", "sdsys/gpl.bp/setnetlogin     : net")
mut("the map does not select netfile for netdefs", "regress-map.txt", "sdsys/gpl.bp/netdefs         : net netfile", "sdsys/gpl.bp/netdefs         : net")
mut("the map does not select netfile for netfake.py", "regress-map.txt", "gplbld/netfake.py            : net netfile", "gplbld/netfake.py            : net")
mut("the map has no rule for the suite file", "regress-map.txt", "gplbld/sandbox-netfile.py    : @self\n", "")
mut("the suite's verdict line changes", "sandbox-netfile.py", 'say("sandbox-netfile: %d passed, %d failed" % (passed, failed))', 'say("sandbox-netfile: %d ok, %d failed" % (passed, failed))')
mut("the suite has no --build", "sandbox-netfile.py", '"--build" in sys.argv', '"--make" in sys.argv')
mut("the suite expects another text for the stale count", "sandbox-netfile.py", 'iter_err = "The server\'s iteration count is not the stored one: the stored login is out of date or this is not the server it was made with"',
    'iter_err = "The server\'s count is not the stored one"')
mut("the suite's history line is gone", "sandbox-netfile.py", "# 17 Oct 26 dm  New.  S.65 slice 3a.", "# 17 Oct 26 dm  New.")


# ---- slice 3b: the remote file handler ------------------------------------------------------------------------------------------------------
NFP, NFHD, NFSUITE, NFMAP = "bp:netfile", "bp:netfile.h", "sandbox-netfile.py", "regress-map.txt"
mut("netfile.h: NF$LOCK is 11 (the same as CLEARFILE)", NFHD, rx(r"(\$define\s+NF\$LOCK\s+)12", r"\g<1>11"))
mut("netfile.h: NF$WRITE is 14", NFHD, rx(r"(\$define\s+NF\$WRITE\s+)9", r"\g<1>14"))
mut("netfile.h: NF$MAX.SERVERS is 11", NFHD, rx(r"(\$define\s+NF\$MAX\.SERVERS\s+)10", r"\g<1>11"))
mut("netfile.h: NF$MAX.HANDLES is 101", NFHD, rx(r"(\$define\s+NF\$MAX\.HANDLES\s+)100", r"\g<1>101"))
mut("netfile.h: NF$RC.ERROR is 4", NFHD, rx(r"(\$define\s+NF\$RC\.ERROR\s+)3", r"\g<1>4"))
mut("netfile.h: NF$STATE is gone", NFHD, drop_line(r"\$define NF\$STATE\b"))
mut("netfile is not internal", NFP, "$internal\nsubroutine netfile(", "subroutine netfile(")
mut("netfile is catalogued under another name", NFP, "$catalog $netfile\n", "$catalog $netfiles\n")
mut("NF$OPEN does not ask the gate", NFP, "*  (1) THE GATE\n   gosub check.gate\n   if not(gate.ok) then", "*  (1) THE GATE\n   gate.ok = @true\n   if not(gate.ok) then")
mut("NF$OPEN asks the gate after the definition is read", NFP,
    lambda t: t.replace("   gosub check.gate\n   if not(gate.ok) then", "   gate.ok = @true\n   if not(gate.ok) then", 1).replace("   call !netdefs('READ', defs, err)\n", "   call !netdefs('READ', defs, err)\n   gosub check.gate\n", 1))
mut("the accounts list is not asked", NFP, "if index(',':downcase(accts):',', ',':acc:',', 1) = 0 then", "if 0 then")
mut("the administrator is not exempt from the list", NFP, "   if not(is.admin) then\n      if index(", "   if 1 then\n      if index(")
mut("the accounts list is compared case sensitively", NFP, "index(',':downcase(accts):',', ',':acc:',', 1)", "index(',':accts:',', ',':acc:',', 1)")
mut("the stored login is not read", NFP, "call $netcred('READ', srv, cred, pin, err)", "cred = ''")
mut("the stored login is written", NFP, "call $netcred('READ', srv, cred, pin, err)", "call $netcred('WRITE', srv, cred, pin, err)")
mut("the definitions are rewritten", NFP, "call !netdefs('READ', defs, err)", "call !netdefs('WRITE', defs, err)")
mut("the file name is not checked", NFP, "   if not(fname.ok) then\n      cred = ''", "   if 0 then\n      cred = ''")
mut("the limit on servers is not asked", NFP, "if slot = 0 and ns >= NF$MAX.SERVERS then", "if 0 then")
mut("the limit on files is not asked", NFP, "   if nh >= NF$MAX.HANDLES then\n      cred = ''", "   if 0 then\n      cred = ''")
mut("the connection is made before the file name is checked", NFP, "*  (7) THE REMOTE FILE NAME\n", "   gosub connect.new\n*  (7) THE REMOTE FILE NAME\n")
mut("the open is audited after the connection is made", NFP,
    lambda t: t.replace("   void kernel(K$AUDIT, 'netfile open server=' : srv : ' file=' : fname)\n\n   created = @false", "   created = @false", 1)
    .replace("   fno = obj->open(fname)\n", "   void kernel(K$AUDIT, 'netfile open server=' : srv : ' file=' : fname)\n   fno = obj->open(fname)\n", 1))
mut("a refusal is not audited", NFP, "   void kernel(K$AUDIT, 'netfile refused server=' : safe : ' reason=' : refused.why)\n", "")
mut("the open audit line names the pin", NFP, "' file=' : fname)\n\n   created", "' file=' : fname : ' pin=' : pin)\n\n   created")
mut("the open audit line is in capitals", NFP, "'netfile open server='", "'NETFILE OPEN server='")
mut("a refusal reason outside the six", NFP, "refused.why = 'credential' ; gosub refuse", "refused.why = 'secret' ; gosub refuse")
mut("a refusal falls through without a return", NFP, "refused.why = 'list' ; gosub refuse\n         return\n", "refused.why = 'list' ; gosub refuse\n")
mut("the audit names the server as typed", NFP, "   if name.ok then safe = srv\n", "   safe = srv\n")
mut("the password login is used", NFP, "obj->connect.keys(host, port, ruser, rsalt, riter, rck, rsk, racct, pin)", "obj->connect(host, port, ruser, rck, racct)")
mut("the copies of the keys are not cleared", NFP, "   ruser = ''\n   rsalt = ''\n   riter = ''\n   rck = ''\n   rsk = ''\n   if not(ok) then", "   if not(ok) then")
mut("the credential is not cleared before the object is made", NFP, "   cred = ''\n   obj = object('!sdclient')", "   obj = object('!sdclient')")
mut("a second place makes an object", NFP, lambda t: t + "\n   obj2 = object('!sdclient')\n")
mut("the request bound is not given to the object", NFP, "   obj->settimeout(NF$REQUEST.MS)\n", "")
mut("the request bound is 0", NFP, "$define NF$REQUEST.MS 30000", "$define NF$REQUEST.MS 0")
mut("a refused operation calls a write method", NFP, "   fail.num = 11501 ; fail.a1 = srvname ; fail.a2 = opname\n",
    "   obj = nf.s.obj(nf.h.slot(hx))\n   obj->write(nf.h.fno(hx), b, c)\n   fail.num = 11501 ; fail.a1 = srvname ; fail.a2 = opname\n")
mut("LOCK is no longer refused", NFP, "case op = NF$WRITE or op = NF$DELETE or op = NF$CLEARFILE or op = NF$LOCK", "case op = NF$WRITE or op = NF$DELETE or op = NF$CLEARFILE")
mut("a read takes a lock", NFP, "rec = obj->read(nf.h.fno(hx), id, e)", "rec = obj->readu(nf.h.fno(hx), id, 0, e)")
mut("the handler executes a command on the server", NFP, lambda t: t + "\n   obj->execute('x', e)\n")
mut("the handler writes a file", NFP, lambda t: t + "\n   writeseq 'x' to f else null\n")
mut("the handler shows the credential", NFP, lambda t: t + "\n   crt cred\n")
mut("the refusal message is another number", NFP, "fail.num = 11501", "fail.num = 11500")
mut("the gate is asked with a set", NFP, "kernel(K$NET, -1)", "kernel(K$NET, 1)")
mut("a second place asks the gate", NFP, lambda t: t + "\n   if kernel(K$NET, -1) then null\n")
mut("get.handle does not ask the gate", NFP, "   if need.gate then\n      gosub check.gate", "   if 0 then\n      gosub check.gate")
mut("read does not ask the gate again", NFP, "act.read:\n   need.gate = @true", "act.read:\n   need.gate = @false")
mut("select does not ask the gate again", NFP, "act.select:\n   need.gate = @true", "act.select:\n   need.gate = @false")
mut("a handle is not tied to its account", NFP, "      if nf.h.acct(hx) # acc then", "      if 0 then")
mut("the account is not stored with the handle", NFP, "   nf.h.acct(hx) = acc\n", "   nf.h.acct(hx) = ''\n")
mut("the account is the log name", NFP, "   acc = downcase(@who)", "   acc = downcase(@logname)")
mut("a request is sent without the no-reply mark", NFP, "   obj->ServerStatus = NF$NOREPLY\n   e = ''\n   rec = obj->read(", "   e = ''\n   rec = obj->read(")
mut("a lost connection is not noticed", NFP, "   rq.lost = (st < 0)", "   rq.lost = (st = 0)")
mut("the no-reply mark is 0", NFP, "$define NF$NOREPLY    -1", "$define NF$NOREPLY    0")
mut("a lost connection is reconnected", NFP, "   gosub drop.conn\n   fail.num = 11497", "   gosub drop.conn\n   gosub connect.new\n   fail.num = 11497")
mut("a lost connection is retried in a loop", NFP, "   gosub drop.conn\n   fail.num = 11497", "   gosub drop.conn\n   loop\n   until 1 do\n   repeat\n   fail.num = 11497")
mut("a lost handle is let through", NFP, "      if allow.lost then return\n", "")
mut("CLOSE of a lost handle is refused", NFP, "need.gate = @false ; need.conn = @false ; any.acct = @true ; allow.lost = @true", "need.gate = @false ; need.conn = @false ; any.acct = @true ; allow.lost = @false")
mut("CLOSEALL asks the gate", NFP, "act.closeall:\n   for sx = 1", "act.closeall:\n   gosub check.gate\n   for sx = 1")
mut("a dropped connection does not mark its handles lost", NFP, "                  nf.h.state(hy) = 2\n", "                  nf.h.state(hy) = 0\n")
mut("the common block holds a key", NFP, "common /$netfile/ nf.opens,", "common /$netfile/ nf.s.key(NF$MAX.SERVERS), nf.opens,")
mut("a second common block", NFP, "   out = ''\n   rc = ''\n   rc<1> = NF$RC.OK", "   common /$other/ zz.x\n   out = ''\n   rc = ''\n   rc<1> = NF$RC.OK")
mut("a message carries the pin", NFP, "fail.num = 11492 ; fail.a1 = srv ; fail.a2 = bad.field", "fail.num = 11492 ; fail.a1 = srv ; fail.a2 = pin")
mut("a slash is a character of a remote file name", NFP, "chk.set = lc.set:digits:'._-$'", "chk.set = lc.set:digits:'._-$/'")
mut("a server name may be 17 characters", NFP, "len(srv) <= 16", "len(srv) <= 17")
mut("message 11497 is missing", "msg:11497", lambda t: None)
mut("message 11501 has two lines", "msg:11501", lambda t: t.rstrip("\n") + "\nsecond line\n")
mut("message 11500 has a fourth place", "msg:11500", lambda t: t.rstrip("\n") + " %4\n")
mut("message 11509 exists", "msg:11509", lambda t: "x\n")
mut("message 11507 (the kernel's) is gone", "msg:11507", lambda t: None)
mut("message 11508 (the kernel's) has two lines", "msg:11508", lambda t: t.rstrip("\n") + "\nsecond line\n")
mut("a message of the block is not used", NFP, "fail.num = 11506 ;", "fail.num = 11507 ;")
mut("another program cites 11502", "bp:cd", lambda t: t + "\n   crt sysmsg(11502)\n")
mut("the map loses the handler rule", NFMAP, "sdsys/gpl.bp/netfile         : netfile\n", "")
mut("the map loses the header rule", NFMAP, "sdsys/gpl.bp/netfile.h       : netfile\n", "")
mut("the map loses a message rule", NFMAP, "sdsys/messages/1150*         : netfile\n", "")
mut("the map's last message rule comes after the none rule", NFMAP, "sdsys/messages/1151*         : netfile\nsdsys/messages/*             : none", "sdsys/messages/*             : none\nsdsys/messages/1151*         : netfile")
mut("the map's header rule comes after the *.h rule", NFMAP,
    lambda t: t.replace("sdsys/gpl.bp/netfile.h       : netfile\n", "", 1).replace("sdsys/gpl.bp/*.h             : @compiler @core\n", "sdsys/gpl.bp/*.h             : @compiler @core\nsdsys/gpl.bp/netfile.h       : netfile\n", 1))
mut("the suite loses a section", NFSUITE, '("lost", lost_section), ', "")
mut("the suite runs gaps by default", NFSUITE, 'OPT_IN = ("gaps",)', "OPT_IN = ()")
mut("the suite's driver loses CLEARFILE", NFSUITE, "            op = NF$CLEARFILE\n", "            op = 11\n")
mut("the suite expects a message that is not there", NFSUITE, "k_err(11501, ", "k_err(11599, ")
mut("the suite does not compile netfile", NFSUITE, "BASIC gpl.bp netcred netfile zznfh zznfhx", "BASIC gpl.bp netcred zznfh zznfhx")
mut("netfile's history line is gone", NFP, "* 17 Oct 26 dm  S.65 slice 3b: written.", "* 17 Oct 26 dm  written.")
mut("netfile.h's history line is gone", NFHD, "* 17 Oct 26 dm  S.65 slice 3b: written.", "* 17 Oct 26 dm  written.")
mut("the suite's history line is gone", NFSUITE, "# 17 Oct 26 dm  S.65 slice 3b:", "# 17 Oct 26 dm  slice 3b:")


# ---- slice 3c: the kernel half ----------------------------------------------------------------------------------------------------------------
M3C = len(M)        # the mutants from here on are slice 3c's
NFC = "netfiles.c"
mut("NET_FILE is 5", "descr.h", rx(r"(#define\s+NET_FILE\s+)4", r"\g<1>5"))
mut("NET_FILE shares 3 with SEQ_FILE", "descr.h", rx(r"(#define\s+NET_FILE\s+)4", r"\g<1>3"))
mut("a second type is 4", "descr.h", rx(r"(#define\s+SEQ_FILE\s+)3", r"\g<1>4"))
mut("the union member loses a zero word", "descr.h", "void* zero[2];", "void* zero[1];")
mut("the union member loses the epoch", "descr.h", "      u_int16_t epoch;\n", "")
mut("the server name is not NET_SERVER_LEN long", "descr.h", "char server[NET_SERVER_LEN + 1];", "char server[16];")
mut("NET_MAX_HANDLES is 101", "descr.h", rx(r"(#define\s+NET_MAX_HANDLES\s+)100", r"\g<1>101"))
mut("NET_SERVER_LEN is 17", "descr.h", rx(r"(#define\s+NET_SERVER_LEN\s+)16", r"\g<1>17"))
mut("NET_FILE_MAX is 64", NFC, rx(r"(#define\s+NET_FILE_MAX\s+)63", r"\g<1>64"))
mut("NF_READ is not netfile.h's", NFC, rx(r"(#define\s+NF_READ\s+)3", r"\g<1>4"))
mut("NF_CLOSEALL is not netfile.h's", NFC, rx(r"(#define\s+NF_CLOSEALL\s+)8", r"\g<1>9"))
mut("NF_RC_ELSE is 1", NFC, rx(r"(#define\s+NF_RC_ELSE\s+)2", r"\g<1>1"))
mut("a prototype in sd.h changes a type", "sd.h", "int net_read(FILE_VAR * fvar, char * id, int16_t id_len, STRING_CHUNK ** rec);", "int net_read(FILE_VAR * fvar, char * id, int32_t id_len, STRING_CHUNK ** rec);")
mut("a prototype in sd.h loses a function", "sd.h", "const char * net_message(void);\n", "")
mut("op_dio3.c declares net_refuse with another type", "op_dio3.c", "int net_refuse(FILE_VAR *fvar, const char *what);", "void net_refuse(FILE_VAR *fvar, const char *what);")
mut("op_dio2.c declares net_fileinfo with another type", "op_dio2.c", "STRING_CHUNK* net_fileinfo(FILE_VAR* fvar, int key);", "STRING_CHUNK* net_fileinfo(FILE_VAR* fvar, long key);")
mut("a netfiles function is defined twice", NFC, lambda t: t + "\nconst char* net_message() {\n  return \"\";\n}\n")
mut("the gate is not asked", NFC, "  if (!net_gate_ok()) {", "  if (0) {")
mut("the queue is flushed before the gate", NFC, "  /* THE GATE, before anything is loaded or called.  An $internal program is not exempt. */\n  if (!net_gate_ok()) {",
    "  net_flush_pending();\n  if (!net_gate_ok()) {")
mut("the gate exempts an $internal program", NFC, "return ((my_uptr->flags & USR_ADMIN) != 0) ||", "return (process.program.flags & HDR_INTERNAL) || ((my_uptr->flags & USR_ADMIN) != 0) ||")
mut("the gate is the administrator's alone", NFC, " || ((my_uptr->gates & UG_NET) != 0);", ";")
mut("the gate refusal is not audited", NFC, "    audit_message(audit);\n    return -ER_PERM;", "    return -ER_PERM;")
mut("the gate refusal falls through", NFC, "    audit_message(audit);\n    return -ER_PERM;", "    audit_message(audit);")
mut("the gate audit line is in capitals", NFC, "\"netfile refused server=%s reason=gate\"", "\"NETFILE REFUSED server=%s reason=gate\"")
mut("the server name is audited as typed", NFC, "(((server[i] >= 'a') && (server[i] <= 'z')) || ((server[i] >= '0') && (server[i] <= '9'))) ? server[i] : '?'", "server[i]")
mut("the gate message is 11461", NFC, "#define MSG_NO_GATE 11460", "#define MSG_NO_GATE 11461")
mut("the pointer's first byte is not tested", NFC, "((u_char)encoded_path[0] != 1) || ", "")
mut("a pointer with no file name is not refused", NFC, "  q = strchr(p, 1);\n  if (q == NULL) {", "  q = strchr(p, 1);\n  if (0) {")
mut("a file name may be 64 characters too long", NFC, "(n > NET_FILE_NAME_MAX) || (strchr(p, 1) != NULL)", "(n > NET_FILE_NAME_MAX + 1) || (strchr(p, 1) != NULL)")
mut("the file name test is NET_FILE_MAX again (a dictionary name is refused)", NFC, "(n > NET_FILE_NAME_MAX) || (strchr(p, 1) != NULL)", "(n > NET_FILE_MAX) || (strchr(p, 1) != NULL)")
mut("the file name buffer is too small for 'dict '", NFC, "char file[NET_FILE_NAME_MAX + 1];", "char file[NET_FILE_MAX + 1];")
mut("NET_FILE_NAME_MAX is NET_FILE_MAX + 4", NFC, "#define NET_FILE_NAME_MAX (NET_FILE_MAX + 5)", "#define NET_FILE_NAME_MAX (NET_FILE_MAX + 4)")
mut("the handler is called by another name", NFC, "k_call(\"$netfile\", 6, NULL, 0);", "k_call(\"netfile\", 6, NULL, 0);")
mut("the handler is not looked for first", NFC, "if (load_object(\"$netfile\", FALSE) == NULL) {", "if (0) {")
mut("the handler is not marked as a trigger", NFC, "  process.program.flags |= PF_IS_TRIGGER;\n", "")
mut("the handler's reference count is not given back", NFC, "if (returned && (--(hdr->ext_hdr.prog.refs) == 0) && (hdr->id < 0))", "if (returned && ((hdr->ext_hdr.prog.refs) == 0) && (hdr->id < 0))")
mut("the handler is called with five arguments", NFC, "k_call(\"$netfile\", 6, NULL, 0);", "k_call(\"$netfile\", 5, NULL, 0);")
mut("net_refuse flushes the queue (runs BASIC)", NFC, "  net_set_message(MSG_READ_ONLY, server, op, \"\");", "  net_flush_pending();\n  net_set_message(MSG_READ_ONLY, server, op, \"\");")
mut("net_refuse does not lower case the statement", NFC, "op[i] = ((what[i] >= 'A') && (what[i] <= 'Z')) ? (char)(what[i] - 'A' + 'a') : what[i];", "op[i] = what[i];")
mut("net_refuse returns 0", NFC, "  return net_raise(-ER_NETWORK, entry);\n}\n\n/* END-CODE */", "  return 0;\n}\n\n/* END-CODE */")
mut("net_refuse reads the server of any variable", NFC, "  if ((fvar != NULL) && (fvar->type == NET_FILE))\n    server = fvar->access.net.server;", "  server = fvar->access.net.server;")
mut("the refusal message is another number", NFC, "#define MSG_READ_ONLY 11501", "#define MSG_READ_ONLY 11500")
mut("net_close talks to the server for every release", NFC, "  if (explicit_close) {\n    explicit_close = FALSE;", "  if (1) {\n    explicit_close = FALSE;")
mut("net_close does not clear the handle first", NFC, "  fvar->access.net.handle = 0;\n\n", "\n")
mut("net_close sends a stale variable", NFC, "  if (net_stale(fvar))\n    return;\n  fvar->access.net.handle = 0;", "  fvar->access.net.handle = 0;")
mut("net_close queues nothing", NFC, "    net_pending[net_pending_ct++] = handle;", "    ;")
mut("a stale variable ignores the epoch", NFC, " || (fvar->access.net.epoch != net_epoch);", ";")
mut("a stale variable ignores its type", NFC, "return (fvar->type != NET_FILE) || (fvar->access.net.handle <= 0)", "return (fvar->access.net.handle <= 0)")
mut("net_close_all does not move the epoch", NFC, "  net_epoch++;\n", "")
mut("net_close_all calls the handler even when nothing was opened", NFC, "  if (!net_used)\n    return;\n", "")
mut("net_close_all keeps the queue", NFC, "  net_pending_ct = 0;\n  net_cache_drop(0);", "  net_cache_drop(0);")
mut("net_op flushes before it asks whether the handle is stale", NFC,
    lambda t: t.replace("  net_flush_pending();\n  ran = net_call_raw(op, hs,", "  ran = net_call_raw(op, hs,", 1)
    .replace("  if (net_stale(fvar)) {\n    snprintf(hs, sizeof(hs), \"%d\", (int)fvar->access.net.handle);\n    net_set_message(MSG_BAD_HANDLE", "  net_flush_pending();\n  if (net_stale(fvar)) {\n    snprintf(hs, sizeof(hs), \"%d\", (int)fvar->access.net.handle);\n    net_set_message(MSG_BAD_HANDLE", 1))
mut("the type is set before the handler has answered", NFC, lambda t: t.replace("  fvar->type = NET_FILE;\n  net_used = TRUE;", "  net_used = TRUE;", 1).replace("  net_flush_pending();\n  ran = net_call_raw(NF_OPEN", "  fvar->type = NET_FILE;\n  net_flush_pending();\n  ran = net_call_raw(NF_OPEN", 1))
mut("a NET_FILE may be written", NFC, "  fvar->flags |= FV_RDONLY | FV_NON_TXN;", "  fvar->flags |= FV_NON_TXN;")
mut("a NET_FILE may be in a transaction", NFC, "  fvar->flags |= FV_RDONLY | FV_NON_TXN;", "  fvar->flags |= FV_RDONLY;")
mut("a NET_FILE has a file table entry", NFC, "  fvar->file_id = -1;\n  fvar->flags", "  fvar->file_id = 0;\n  fvar->flags")
mut("the union is not zeroed", NFC, "  memset(&fvar->access, 0, sizeof(fvar->access));\n", "")
mut("a handle may be \"3x\"", NFC, "if ((hs[i] < '0') || (hs[i] > '9'))", "if (0)")
mut("a handle may be 101", NFC, "(handle < 1) || (handle > NET_MAX_HANDLES)", "(handle < 1) || (handle > NET_MAX_HANDLES + 1)")
mut("net_read asks the handler for an empty id", NFC, "  if (id_len < 1)\n    return ER_IID; /* an empty or over-long id", "  if (0)\n    return ER_IID; /* an empty or over-long id")
mut("the accounts list is not the permission class", NFC, "    case MSG_NOT_LISTED:\n", "")
mut("the ELSE branch ignores the server's status", NFC, "return (rc->status > 0) ? rc->status : else_status;", "return else_status;")
mut("every error is ER_PERM", NFC, "  return -ER_NETWORK;\n}\n\n/* ======================================================================\n   net_answer()", "  return -ER_PERM;\n}\n\n/* ======================================================================\n   net_answer()")
# _voc_ref
VR = "bp:_voc_ref"
mut("_voc_ref: a dictionary of a NET file is refused again", VR, "            n.srv = downcase(trim(voc.rec<2>))", "            if fno = 3 then\n               set.status ER$VNF\n               return\n            end\n            n.srv = downcase(trim(voc.rec<2>))")
mut("_voc_ref: a dictionary of a NET file is not given 'dict '", VR, "            if fno = 3 then n.file = 'dict ':n.file", "            if fno = 3 then n.file = n.file")
mut("_voc_ref: every NET file is given 'dict '", VR, "            if fno = 3 then n.file = 'dict ':n.file", "            n.file = 'dict ':n.file")
mut("_voc_ref: the data part is given 'dict ' (fno 2)", VR, "            if fno = 3 then n.file = 'dict ':n.file", "            if fno = 2 then n.file = 'dict ':n.file")
mut("_voc_ref: the prefix has no space", VR, "            if fno = 3 then n.file = 'dict ':n.file", "            if fno = 3 then n.file = 'dict':n.file")
mut("_voc_ref: 'dict ' is added BEFORE the shape test", VR, "            n.file = downcase(trim(voc.rec<3>))\n            gosub check.n.pointer", "            n.file = downcase(trim(voc.rec<3>))\n            if fno = 3 then n.file = 'dict ':n.file\n            gosub check.n.pointer")
mut("_voc_ref: the shape test allows a space (a VOC entry may hold the prefix)", VR, "'._-$'", "'._-$ '")
mut("_voc_ref: the server name is not lower cased", VR, "n.srv = downcase(trim(voc.rec<2>))", "n.srv = trim(voc.rec<2>)")
mut("_voc_ref: the file name is not trimmed", VR, "n.file = downcase(trim(voc.rec<3>))", "n.file = downcase(voc.rec<3>)")
mut("_voc_ref: the pathname has no separator", VR, "pathname = char(1):'N':char(1):n.srv:char(1):n.file", "pathname = char(1):'N':char(1):n.srv:'/':n.file")
mut("_voc_ref: the pointer is not shape tested", VR, "            gosub check.n.pointer\n            if not(n.ok) then", "            n.ok = @true\n            if not(n.ok) then")
mut("_voc_ref: a bad pointer is ER$VNF", VR, "            if not(n.ok) then\n               set.status ER$NAM", "            if not(n.ok) then\n               set.status ER$VNF")
mut("_voc_ref: the N case asks the gate", VR, "            n.srv = downcase(trim(voc.rec<2>))", "            n.gate = kernel(K$NET, -1)\n            n.srv = downcase(trim(voc.rec<2>))")
mut("_voc_ref: a server name may be 17 characters", VR, "len(n.srv) > 16", "len(n.srv) > 17")
mut("_voc_ref: a file name may be 64 characters", VR, "len(n.file) > 63", "len(n.file) > 64")
mut("_voc_ref: a server name may start with a digit", VR, "if index(n.letters, n.srv[1,1], 1) = 0 then n.ok = @false", "if 0 then n.ok = @false")
mut("_voc_ref: a file name may hold a slash", VR, "'._-$'", "'._-$/'")
mut("_voc_ref: the pointer checks are not all", VR, "   n.ok = @true\n   n.letters", "   n.ok = @true\n   n.ok = @true\n   n.letters")
mut("_voc_ref: the N case comes after the default", VR, lambda t: t.replace('         case type = "N"', '         case type = "NN"', 1))
# open_file, OPENPATH, dio_close
mut("open_file does not look for the encoded path", "op_dio1.c", "if (net_path_is_net(mapped_name)) {", "if (0 && net_path_is_net(mapped_name)) {")
mut("OPENPATH looks for the encoded path", "op_dio1.c", "  open_file(FALSE);", "  open_file(TRUE);")
mut("a second place opens a NET file", "op_dio2.c", lambda t: t + "\nvoid zz_open(FILE_VAR* v) {\n  net_open(v, \"\");\n}\n")
mut("a failed net_open shows the generic message", "op_dio1.c", "    if (net_failed)\n      k_error(\"%s\", net_message());", "    if (0)\n      k_error(\"%s\", net_message());")
mut("a failed net_open is not an error", "op_dio1.c", "      net_failed = (net_status < 0);", "      net_failed = FALSE;")
mut("dio_close does more for a NET_FILE", "op_dio1.c", "      net_close(fvar);\n      break;", "      net_close(fvar);\n      fvar->file_id = -1;\n      break;")
mut("dio_close has no NET_FILE arm", "op_dio1.c", "    case NET_FILE:\n      /* 17 Oct 26 S.65 slice 3c: file_id is -1, so nothing above ran.", "    case 77:\n      /* 17 Oct 26 S.65 slice 3c: file_id is -1, so nothing above ran.")
mut("CLOSE does not set explicit_close", "op_dio1.c", "  explicit_close = TRUE; /* OPTION", "  /* OPTION")
# every census REFUSE site: the call is taken out
for (_f, _n), _v in sorted(NK_REFUSE.items()):
    mut("%s no longer refuses a NET_FILE" % _n, _f, edit_func(_n, r"\b(?:net_refuse|refuse_net_file)\((?=\w)", "nobody_refuses("))
mut("op_filelock refuses AFTER it reads the file table", "op_lock.c",
    lambda t: edit_func("op_filelock", r"fptr = FPtr\(file_id\);", "fptr = FPtr(file_id);\n    net_refuse(fvar, \"FILELOCK\");")(
        edit_func("op_filelock", r"if \(fvar->type == NET_FILE\)\s*net_refuse\(fvar, \"FILELOCK\"\);[^\n]*\n", "")(t)))
mut("op_getlocks reads file_id before it refuses", "op_lock.c", lambda t: edit_func("op_getlocks", r"if \(descr->data\.fvar->type == NET_FILE\)\s*net_refuse\(descr->data\.fvar, \"GETLOCKS\"\);",
                                                                                    "file_id = descr->data.fvar->file_id;\n    net_refuse(descr->data.fvar, \"GETLOCKS\");")(t))
mut("op_write refuses after the edit gate", "op_dio3.c", lambda t: edit_func("op_write", r"if \(refuse_net_file\(fvar, op_flags, keep_lock \? \"WRITEU\" : \"WRITE\"\)\)\s*goto exit_op_write;", "")(t)
    .replace("    int edit_kind = edit_refusal(fvar);\n    if (edit_kind != EDIT_NONE) {\n      if (!(op_flags & P_ON_ERROR))\n        k_error(sysmsg(EDIT_REFUSED_MSG(edit_kind)));", "    int edit_kind = edit_refusal(fvar);\n    if (refuse_net_file(fvar, op_flags, \"WRITE\"))\n      goto exit_op_write;\n    if (edit_kind != EDIT_NONE) {\n      if (!(op_flags & P_ON_ERROR))\n        k_error(sysmsg(EDIT_REFUSED_MSG(edit_kind)));", 1))
# guards and supported statements
mut("the file status of a NET_FILE reads the file table", "op_dio2.c", edit_func("get_file_status", r"if \(ftype == NET_FILE\)\s*return NULL;", ""))
mut("the permissions log reads the file table of a NET_FILE", "k_error.c", edit_func("log_permissions_error", r"fvar->type == NET_FILE", "0"))
mut("the process dump reads the file table of a NET_FILE", "pdump.c", edit_func("dump_variable", r"fvar->type == NET_FILE", "0"))
mut("FILEINFO of a NET_FILE reads the file table", "op_dio2.c", edit_func("op_fileinfo", r"ftype == NET_FILE", "0"))
mut("FILEINFO FL_STATS_OFF is no longer refused for a NET_FILE", "op_dio2.c", "        case FL_STATS_OFF: /* 10003 */", "        case 99999: /* 10003 */")
mut("FILEINFO FL_NETFILE is no longer answered", "op_dio2.c", "        case FL_NETFILE:  /* 1022  A file on another server */\n", "")
mut("FILEINFO does not ask the server for the other keys", "op_dio2.c", "str = net_fileinfo(fvar, key);", "str = NULL;")
mut("READV of a NET_FILE goes through the recursive _readv", "op_dio3.c", edit_func("op_readv", r"if \(fvar->type == NET_FILE\) \{", "if (0) {"))
mut("READV of a NET_FILE does not ask the server", "op_dio3.c", "net_st = net_readv(fvar, id, id_len, field_no, &net_str);", "net_st = 0;")
mut("a NET_FILE has a transaction id", "op_dio3.c", "txn_id = ((fvar->flags & FV_NON_TXN) || (fvar->type == NET_FILE)) ? 0 : process.txn_id;", "txn_id = (fvar->flags & FV_NON_TXN) ? 0 : process.txn_id;")
mut("a locking read of a NET_FILE is not refused", "op_dio3.c", "if ((fvar->type == NET_FILE) && (op_flags & P_REC_LOCKS)) {", "if (0) {")
mut("READ of a NET_FILE has no case", "op_dio3.c", edit_func("read_record", r"case NET_FILE: \{", "case 77: {"))
mut("the helper refuses every file", "op_dio3.c", "  if ((fvar == NULL) || (fvar->type != NET_FILE))\n    return FALSE;\n\n  process.op_flags", "  if (fvar == NULL)\n    return FALSE;\n\n  process.op_flags")
mut("the helper takes a non-negative status", "op_dio3.c", "process.status = (st < 0) ? st : -ER_PERM;", "process.status = st;")
mut("the helper gives net_refuse the whole op_flags", "op_dio3.c", "process.op_flags = op_flags & P_ON_ERROR; /* net_refuse() reads it", "process.op_flags = op_flags; /* net_refuse() reads it")
# the census scan
mut("a new function reads a file variable", "op_dio4.c", lambda t: t + "\nvoid op_zzz() {\n  DESCRIPTOR* d = e_stack - 1;\n  k_get_file(d);\n}\n")
mut("a new function in another kernel file reads a file variable", "c:op_seqio.c", lambda t: t + "\nvoid op_zzz() {\n  DESCRIPTOR* d = e_stack - 1;\n  k_get_file(d);\n}\n")
mut("a sequential function loses its type test", "c:op_seqio.c", edit_func("op_seek", r"SEQ_FILE", "XX_FILE", count=0))
mut("SET.TRIGGER loses its type test", "dh_misc.c", edit_func("op_settrig", r"ER_NDYN", "ER_XXX", count=0))
# messages, the Makefile list, the suite, the map, the history
mut("message 11507 has a second place", "msg:11507", lambda t: t.rstrip("\n") + " %2\n")
mut("message 11508 has no place", "msg:11508", lambda t: t.replace("%1", ""))
mut("netfiles.c names a message that is not there", NFC, "#define MSG_HANDLER 11507", "#define MSG_HANDLER 11509")
mut("gpl.src loses netfiles", "gpl.src", "netfiles\n", "")
mut("gpl.src lists netfiles before messages", "gpl.src", "messages\nnetfiles\n", "netfiles\nmessages\n")
mut("sd.h says netfiles was removed", "sd.h", "/* NETFILES.C - files on another SD server", "/* NETFILES.C removed - files on another SD server")
mut("the suite loses the kernel section", NFSUITE, '("kernel", kernel_section), ("gaps", gaps_section)', '("gaps", gaps_section)')
mut("the suite allows a write request", NFSUITE, "KALLOWED = {47, 48, 3, 4, 5, 6, 1}", "KALLOWED = {47, 48, 3, 4, 5, 6, 1, 16}")
mut("the suite loses a matrix statement", NFSUITE, 'km("delete", "delete f', 'km("deletx", "delete f')
mut("the suite expects a message that is not there", NFSUITE, 'msg(11501, "nfa", "getlocks")', 'msg(11599, "nfa", "getlocks")')
mut("the suite loses its hang guard", NFSUITE, "    except subprocess.TimeoutExpired:\n        out, hung = [], True", "    except ValueError:\n        out, hung = [], True")
mut("the map loses the op_dio3 rule's suite", NFMAP, "gplsrc/op_dio3.c             : @files @seq prof lockown editgates netfile", "gplsrc/op_dio3.c             : @files @seq prof lockown editgates")
mut("the map loses the netfiles.c rule", NFMAP, "gplsrc/netfiles.c            : netfile\n", "")
mut("the map loses the _voc_ref rule", NFMAP, "sdsys/gpl.bp/_voc_ref        : @core netfile\n", "")
mut("the map's dh_ak rule is gone", NFMAP, "gplsrc/dh_ak.c               : @files netfile\n", "")
mut("descr.h's history line is gone", "descr.h", "S.65 slice 3c: NET_FILE (4) is back", "S.65: NET_FILE (4) is back")
mut("netfiles.c's history line is gone", NFC, "17 Oct 26 dm  S.65 slice 3c: written.", "17 Oct 26 dm  written.")
mut("_voc_ref's history line is gone", VR, "S.65 slice 3c: a new VOC pointer type N", "S.65: a new VOC pointer type N")
mut("the suite's slice 3c history line is gone", NFSUITE, "# 17 Oct 26 dm  S.65 slice 3c: the section kernel", "# 17 Oct 26 dm  the section kernel")

# ---- slice 3d: SELECT, SELECTV, the DICT form and three FILEINFO keys ----------------------------------------------------------------------------
M3D = len(M)        # the mutants from here on are slice 3d's (the rewritten 3c ones above stay where they were)
OD4, OD2 = "op_dio4.c", "op_dio2.c"
# net_select
mut("net_select asks for another operation", NFC, "status = net_op(fvar, NF_SELECT,", "status = net_op(fvar, NF_READ,")
mut("NF_SELECT is 5 in netfiles.c", NFC, rx(r"(#define\s+NF_SELECT\s+)6", r"\g<1>5"))
mut("NF$SELECT is 5 in netfile.h", NFHD, rx(r"(\$define\s+NF\$SELECT\s+)6", r"\g<1>5"))
mut("net_select calls the handler directly", NFC, edit_func("net_select", r"net_op\(fvar, NF_SELECT, \"\", 0, \"\", 0, ER_FNF, &out\)", "net_call_raw(NF_SELECT, \"\", \"\", \"\", &out, NULL)"))
mut("net_select raises even with ON ERROR", NFC, edit_func("net_select", r"net_raise\(status, entry\)", "net_raise(status, 0)"))
mut("net_select takes no flags at entry", NFC, edit_func("net_select", r"u_int16_t entry = process\.op_flags;", "u_int16_t entry = 0;"))
mut("net_select does not give the flags back", NFC, edit_func("net_select", r"process\.op_flags = entry;\n", ""))
mut("net_select does not stop on an ELSE", NFC, edit_func("net_select", r"if \(status > 0\)\s*return status;", ""))
mut("net_select does not stop on an error", NFC, edit_func("net_select", r"if \(status < 0\)\s*return net_raise\(status, entry\);", ""))
mut("net_select sets *ids before it knows", NFC, edit_func("net_select", r"  status = net_op", "  *ids = NULL;\n  status = net_op"))
mut("net_select sets *count before it knows", NFC, edit_func("net_select", r"  status = net_op", "  *count = 0;\n  status = net_op"))
mut("net_select counts an empty answer as one id", NFC, edit_func("net_select", r"int32_t n = 0;", "int32_t n = 1;"))
mut("net_select does not count the field marks", NFC, edit_func("net_select", r"== FIELD_MARK", "== 0"))
mut("sd.h declares net_select with another type", "sd.h", "int net_select(FILE_VAR * fvar, STRING_CHUNK ** ids, int32_t * count);", "int net_select(FILE_VAR * fvar, STRING_CHUNK ** ids, int32_t count);")
mut("sd.h loses net_select", "sd.h", "int net_select(FILE_VAR * fvar, STRING_CHUNK ** ids, int32_t * count);\n", "")
# op_select and the helper
mut("SELECT empties the target list before it asks the server", OD4, edit_func("op_select", r"fvar = descr->data\.fvar;", "fvar = descr->data.fvar;\n    clear_select(list_no);"))
mut("SELECT of a NET_FILE goes on after an error", OD4, "        k_dismiss();\n        goto select_status;\n      }\n    }\n\n    end_select(list_no);", "        k_dismiss();\n      }\n    }\n\n    end_select(list_no);")
mut("SELECT's switch has no NET_FILE case", OD4, "      case NET_FILE:\n        store_select_list(list_no, net_ids, net_count);", "      case 77:\n        store_select_list(list_no, net_ids, net_count);")
mut("SELECT does not store the ids", OD4, "        store_select_list(list_no, net_ids, net_count);", "        ;")
mut("SELECT's NULL guard is back (an empty file leaves the old count)", OD4, "      case NET_FILE:\n        store_select_list(list_no, net_ids, net_count);", "      case NET_FILE:\n        if (net_ids != NULL)\n          store_select_list(list_no, net_ids, net_count);")
mut("store_select_list returns before it sets the count", OD4, edit_func("store_select_list", r"  descr = Element\(process\.syscom, SYSCOM_SELECT_COUNT\);", "  if (head == NULL)\n    return;\n  descr = Element(process.syscom, SYSCOM_SELECT_COUNT);"))
mut("store_select_list has no early return for a NULL list", OD4, edit_func("store_select_list", r"  if \(head == NULL\)\s*return;", ""))
mut("SELECT calls net_select without the helper", OD4, edit_func("op_select", r"net_select_with_flags\(fvar, op_flags, &net_ids, &net_count\)", "net_select(fvar, &net_ids, &net_count)"))
mut("SELECT refuses a NET_FILE again", OD4, edit_func("op_select", r"net_st = net_select_with_flags", "net_refuse(fvar, \"SELECT\");\n      net_st = net_select_with_flags"))
mut("the helper gives net_select the whole op_flags", OD4, "process.op_flags = op_flags & P_ON_ERROR;\n  st = net_select(fvar, ids, count);", "process.op_flags = op_flags;\n  st = net_select(fvar, ids, count);")
mut("the helper leaves process.op_flags set", OD4, "  st = net_select(fvar, ids, count);\n  process.op_flags = 0;", "  st = net_select(fvar, ids, count);")
mut("dir_select no longer ends with store_select_list", OD4, edit_func("dir_select", r"store_select_list\(list_no, head, record_count\);", ";"))
mut("store_select_list is declared with another type", OD4, "Private void store_select_list(int16_t list_no, STRING_CHUNK* head, int32_t record_count);", "Private void store_select_list(int16_t list_no, STRING_CHUNK* head, int16_t record_count);")
mut("net_select_with_flags is declared with another type", OD4, "Private int net_select_with_flags(FILE_VAR* fvar, u_int16_t op_flags, STRING_CHUNK** ids, int32_t* count);", "Private int net_select_with_flags(FILE_VAR* fvar, u_int16_t op_flags, STRING_CHUNK** ids, int32_t count);")
mut("a second place calls net_select", OD4, lambda t: t + "\nvoid zz_sel(FILE_VAR* v) {\n  net_select(v, NULL, NULL);\n}\n")
# op_selectv
mut("SELECTV does not find its target again after the call", OD4, "\n\n      /* The handler ran BASIC: the target is found again from the stack, as op_read does */\n      tgt_descr = e_stack - 1;\n      while (tgt_descr->type == ADDR)\n        tgt_descr = tgt_descr->data.d_addr;\n", "\n")
mut("SELECTV uses its target before the call", OD4, edit_func("op_selectv", r"net_ids = NULL;\n      net_count = 0;\n      net_st", "net_ids = NULL;\n      net_count = 0;\n      InitDescr(tgt_descr, SELLIST);\n      net_st"))
mut("SELECTV's target is not an empty list after an error", OD4, "      tgt_descr->data.str.saddr = NULL; /* an empty list unless the ids came */\n", "")
mut("SELECTV's list has no count", OD4, "        net_ids->offset = net_count;\n", "")
mut("SELECTV does not set @SELECTED", OD4, "        descr = Element(process.syscom, SYSCOM_SELECTED);\n        descr->data.value = net_count;\n      }\n      goto selectv_status;", "      }\n      goto selectv_status;")
mut("SELECTV sets @SELECTED only for a non-empty list", OD4, "          net_ids->offset = net_count;\n        }\n        descr = Element(process.syscom, SYSCOM_SELECTED);\n        descr->data.value = net_count;",
    "          net_ids->offset = net_count;\n          descr = Element(process.syscom, SYSCOM_SELECTED);\n          descr->data.value = net_count;\n        }")
mut("SELECTV gives the list its ids without the NULL test", OD4, "        if (net_ids != NULL) {\n          tgt_descr->data.str.saddr = net_ids;\n          net_ids->offset = net_count;\n        }", "        tgt_descr->data.str.saddr = net_ids;\n        net_ids->offset = net_count;")
mut("SELECTV of a NET_FILE goes on into the local switch", OD4, "      }\n      goto selectv_status;\n    }\n\n    /* Do the select */", "      }\n    }\n\n    /* Do the select */")
mut("SELECTV refuses a NET_FILE again", OD4, edit_func("op_selectv", r"net_st = net_select_with_flags", "net_refuse(fvar, \"SELECTV\");\n      net_st = net_select_with_flags"))
mut("SELECTV ignores the status", OD4, "      if (net_st != 0) {\n        process.status = net_st;\n      } else {", "      if (0) {\n        process.status = net_st;\n      } else {")
# INDICES of a remote file: the refusal comes back
mut("INDICES(f) refuses a NET_FILE again", "dh_ak.c", edit_func("op_indices1", r"fvar = descr->data\.fvar;", "fvar = descr->data.fvar;\n  if (fvar->type == NET_FILE)\n    net_refuse(fvar, \"INDICES\");"))
mut("INDICES(f, name) refuses a NET_FILE again", "dh_ak.c", edit_func("op_indices2", r"fvar = descr->data\.fvar;", "fvar = descr->data.fvar;\n  if (fvar->type == NET_FILE)\n    net_refuse(fvar, \"INDICES\");"))
mut("INDICES(f) refuses through the helper", "dh_ak.c", edit_func("op_indices1", r"k_dismiss\(\);", "refuse_net_file(fvar, 0, \"INDICES\");\n  k_dismiss();"))
mut("INDICES(f) has no default arm", "dh_ak.c", edit_func("op_indices1", r"    default:", "    case 99:"))
mut("INDICES(f, name) has no default arm", "dh_ak.c", edit_func("op_indices2", r"      default:", "      case 99:"))
mut("INDICES(f) has a NET_FILE arm", "dh_ak.c", edit_func("op_indices1", r"    default:", "    case NET_FILE:\n      break;\n\n    default:"))
mut("SELECTV has no NET branch", OD4, edit_func("op_selectv", r"if \(fvar->type == NET_FILE\)", "if (0)"))
# FILEINFO
mut("FL_TYPE_NET is 6 in keys.h", "keys.h", rx(r"(#define\s+FL_TYPE_NET\s+)7", r"\g<1>6"))
mut("FL_TYPE_NET is 5 (the sequential file's)", "keys.h", rx(r"(#define\s+FL_TYPE_NET\s+)7", r"\g<1>5"))
mut("FL$TYPE.NET is 8 in syscom/keys.h", "syscom/keys.h", rx(r"(\$define\s+FL\$TYPE\.NET\s+)7", r"\g<1>8"))
mut("FL$TYPE.NET is gone from syscom/keys.h", "syscom/keys.h", drop_line(r"FL\$TYPE\.NET"))
mut("FL_TYPE_NET is gone from keys.h", "keys.h", drop_line(r"FL_TYPE_NET"))
mut("FILEINFO FL_TYPE answers a directory file", OD2, "n = FL_TYPE_NET;", "n = FL_TYPE_DIR;")
mut("FILEINFO FL_TYPE of a NET_FILE goes to the server", OD2, "        case FL_TYPE: /* 3  A file on another server", "        case 99998: /* 3  A file on another server")
mut("FILEINFO FL_COLLECTION answers 1", OD2, "(slice 3d) */\n          n = 0;", "(slice 3d) */\n          n = 1;")
mut("FILEINFO FL_COLLECTION of a NET_FILE goes to the server", OD2, "        case FL_COLLECTION: /* 1035  The query processor asks", "        case 99997: /* 1035  The query processor asks")
mut("FILEINFO FL_FLAGS is not restricted to $internal programs", OD2, "n = (process.program.flags & HDR_INTERNAL) ? DHF_NOCASE : 0;", "n = DHF_NOCASE;")
mut("FILEINFO FL_FLAGS answers 0 to an $internal program", OD2, "n = (process.program.flags & HDR_INTERNAL) ? DHF_NOCASE : 0;", "n = 0;")
mut("FILEINFO FL_FLAGS of a NET_FILE goes to the server", OD2, "        case FL_FLAGS: /* 10001  The query processor asks for the NOCASE bit", "        case 99996: /* 10001  The query processor asks for the NOCASE bit")
mut("FILEINFO FL_FLAGS of a NET_FILE reads the file table", OD2, "(process.program.flags & HDR_INTERNAL) ? DHF_NOCASE : 0;", "(process.program.flags & HDR_INTERNAL) ? FPtr(fvar->file_id)->flags : 0;")

# ---- 18 Oct 26: the record cache (NK19-NK24) and K_NET closing the remote files (NK25)
mut("the cache has 65 slots", NFC, "#define NET_CACHE_SLOTS 64", "#define NET_CACHE_SLOTS 65")
mut("the cache keeps a record for 3 seconds", NFC, "#define NET_CACHE_TTL 2 ", "#define NET_CACHE_TTL 3 ")
mut("the cache keeps records of 64 KB", NFC, "#define NET_CACHE_REC_MAX 32768", "#define NET_CACHE_REC_MAX 65536")
mut("netfiles.c does not include time.h", NFC, "#include <time.h>\n", "")
mut("a cache entry has no epoch", NFC, "  u_int16_t epoch;\n  int16_t id_len;", "  int16_t id_len;")
mut("a cache hit ignores the handle", NFC, "(e->handle == fvar->access.net.handle) && ", "")
mut("a cache hit ignores the epoch", NFC, " && (e->epoch == fvar->access.net.epoch)", "")
mut("a cache hit ignores the id length", NFC, " && (e->id_len == id_len)", "")
mut("a cache hit ignores the id bytes", NFC, "(memcmp(e->id, id, id_len) == 0)", "1")
mut("the cache never expires an entry", NFC, "(now < e->when) || ((now - e->when) > NET_CACHE_TTL)", "(now < e->when)")
mut("the cache trusts an entry from the future", NFC, "(now < e->when) || ((now - e->when) > NET_CACHE_TTL)", "((now - e->when) > NET_CACHE_TTL)")
mut("an expired entry is skipped but not freed", NFC, edit_func("net_cache_find", r"net_cache_free\(e\);\s*continue;", "continue;"))
mut("the cache keeps an id of length 0", NFC, "(id_len < 1) || (id_len > MAX_ID_LEN)", "(id_len > MAX_ID_LEN)")
mut("the cache keeps an id over MAX_ID_LEN", NFC, "(id_len < 1) || (id_len > MAX_ID_LEN)", "(id_len < 1)")
mut("the cache keeps a record over NET_CACHE_REC_MAX", NFC, " || ((rec != NULL) && (rec->string_len > NET_CACHE_REC_MAX))", "")
mut("the cache keeps the caller's chain, not a copy", NFC, "e->rec = (rec != NULL) ? k_copy_string(rec) : NULL;", "e->rec = rec;")
mut("a full cache does not free the old record of the slot it takes", NFC, edit_func("net_cache_put", r"net_cache_free\(e\);", ""))
mut("a full cache always takes slot 0", NFC, "e = &net_cache[net_cache_next];", "e = &net_cache[0];")
mut("the cache's ring does not advance", NFC, "net_cache_next = (net_cache_next + 1) % NET_CACHE_SLOTS;", "net_cache_next = net_cache_next;")
mut("a cache entry has no time", NFC, "  e->when = time(NULL);", "  e->when = 0;")
mut("a cache entry is stored without its epoch", NFC, "  e->epoch = fvar->access.net.epoch;\n", "")
mut("net_cache_free leaks the record", NFC, "    s_free(e->rec);", "    ;")
mut("net_cache_free leaves the entry in use", NFC, "  e->used = FALSE;\n}", "}")
mut("net_cache_drop(0) drops only handle 0", NFC, "((handle == 0) || (net_cache[i].handle == handle))", "(net_cache[i].handle == handle)")
mut("net_cache_drop(h) drops nothing", NFC, "((handle == 0) || (net_cache[i].handle == handle))", "(handle == 0)")
mut("net_cache_drop(h) drops every handle", NFC, "((handle == 0) || (net_cache[i].handle == handle))", "1")
mut("net_read consults the cache for a stale file variable", NFC, "  if (!net_stale(fvar)) {\n    NET_CACHE_ENTRY* hit", "  {\n    NET_CACHE_ENTRY* hit")
mut("net_read serves an absent entry as another status", NFC, "      if (hit->absent)\n        return ER_RNF;", "      if (hit->absent)\n        return ER_FNF;")
mut("net_read gives the cached chain itself", NFC, "*rec = (hit->rec != NULL) ? k_copy_string(hit->rec) : NULL;", "*rec = hit->rec;")
mut("net_read caches an absent entry for any positive status", NFC, "    if (status == ER_RNF)\n      net_cache_put(fvar, id, id_len, NULL, TRUE);", "    net_cache_put(fvar, id, id_len, NULL, TRUE);")
mut("net_read caches nothing it read", NFC, "  net_cache_put(fvar, id, id_len, *rec, FALSE);\n", "")
mut("net_read caches on an error", NFC, edit_func("net_read", r"  if \(status < 0\)\s*return net_raise\(status, entry\);", "  if (status < 0) {\n    net_cache_put(fvar, id, id_len, NULL, TRUE);\n    return net_raise(status, entry);\n  }"))
mut("net_read never consults the cache", NFC, "NET_CACHE_ENTRY* hit = net_cache_find(fvar, id, id_len);", "NET_CACHE_ENTRY* hit = NULL;")
mut("net_readv uses the cache", NFC, edit_func("net_readv", r"  status = net_op\(fvar, NF_READV", "  (void)net_cache_find(fvar, id, id_len);\n  status = net_op(fvar, NF_READV"))
mut("net_select does not drop the handle's entries", NFC, "  net_cache_drop(fvar->access.net.handle); /* a new query is a new look at the file */\n", "")
mut("net_select drops them after the request", NFC, lambda t: t.replace("  net_cache_drop(fvar->access.net.handle); /* a new query is a new look at the file */\n", "", 1).replace("  process.op_flags = entry;\n  if (status < 0)\n    return net_raise(status, entry);\n  if (status > 0)\n    return status;\n\n  s = net_take_string", "  net_cache_drop(fvar->access.net.handle);\n  process.op_flags = entry;\n  if (status < 0)\n    return net_raise(status, entry);\n  if (status > 0)\n    return status;\n\n  s = net_take_string", 1))
mut("net_close does not drop the handle's entries", NFC, "  if (handle > 0)\n    net_cache_drop(handle);\n", "")
mut("net_close drops them after the stale test", NFC, "  if (handle > 0)\n    net_cache_drop(handle);\n  if (net_stale(fvar))\n    return;", "  if (net_stale(fvar))\n    return;\n  if (handle > 0)\n    net_cache_drop(handle);")
mut("net_close drops handle 0, which is everything", NFC, "  if (handle > 0)\n    net_cache_drop(handle);", "  net_cache_drop(handle);")
mut("net_close_all keeps the cache", NFC, "  net_cache_drop(0);\n", "")
mut("net_close_all drops the cache only when something was opened", NFC, "  net_cache_drop(0);\n\n  if (!net_used)\n    return;\n", "\n  if (!net_used)\n    return;\n  net_cache_drop(0);\n")
mut("a second place drops the cache", NFC, lambda t: t + "\nvoid zz_drop(void) {\n  net_cache_drop(0);\n}\n")
# K_NET
mut("K_NET never closes the remote files", "op_kernel.c", "          net_close_all();\n", "")
mut("K_NET's ask form closes the remote files", "op_kernel.c", "      result.data.value = (my_uptr->gates & UG_NET) != 0;\n      break;\n\n    /* K_EDIT_OK / K_EDIT_KIND", "      net_close_all();\n      result.data.value = (my_uptr->gates & UG_NET) != 0;\n      break;\n\n    /* K_EDIT_OK / K_EDIT_KIND")
mut("K_NET closes the remote files for a caller that is not $internal", "op_kernel.c", "          net_close_all();\n          process.status = n;\n          break;\n        }\n      }\n", "          process.status = n;\n          break;\n        }\n        net_close_all();\n      }\n")
mut("K_NET closes the remote files before it changes the gate", "op_kernel.c", lambda t: t.replace("          net_close_all();\n", "", 1).replace("          if (n > 0)\n            my_uptr->gates |= UG_NET;", "          net_close_all();\n          if (n > 0)\n            my_uptr->gates |= UG_NET;", 1))
mut("K_NET does not save the caller's STATUS()", "op_kernel.c", "          n = process.status; /* the handler is BASIC and leaves its own STATUS() behind; the caller's is given back */\n", "")
mut("K_NET does not give the caller's STATUS() back", "op_kernel.c", "          process.status = n;\n          break;", "          break;")
mut("K_NET uses descr after the handler ran", "op_kernel.c", "          process.status = n;\n          break;", "          process.status = n;\n          result.data.value = descr->data.value;\n          break;")
mut("K_NET computes the answer after the handler ran", "op_kernel.c", lambda t: t.replace("          result.data.value = (my_uptr->gates & UG_NET) != 0;\n          n = process.status;", "          n = process.status;", 1).replace("          net_close_all();\n          process.status = n;\n", "          net_close_all();\n          process.status = n;\n          result.data.value = (my_uptr->gates & UG_NET) != 0;\n", 1))
mut("K_NET falls through after the close", "op_kernel.c", "          process.status = n;\n          break;\n        }\n      }\n      result.data.value", "          process.status = n;\n        }\n      }\n      result.data.value")


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
