#!/usr/bin/env python3
"""test-shared-units.py - the shared account (S.66), as invariants read off the source.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-shared-units.py
  python3 .../test-shared-units.py --selftest

No sudo, no install, no sd.  Exit 0 every check passed, 1 a check failed, 2 it could not run.  Written 18 Oct 26.

***WHAT THIS IS, AND WHAT IT IS NOT.***  It reads the C, BASIC and shell sources as text, with comments removed, so a rule that survives only
in a comment does not count.  ***IT DOES NOT RUN ANYTHING, SO IT CANNOT SAY THAT A GATE REFUSES ANYBODY, THAT A FILE OPENS BY NAME, OR THAT THE
INSTALLER MAKES THE ACCOUNT***: those are sandbox-shared.py (ordinary sessions on a private SD, the disk as evidence), test-install-shared.sh
(the installer's two blocks run on scratch files with sudo stubbed) and witness-accounts.sh (a real install, written, needs sudo).  What a text
check is for: the feature is spread over ten kernel files, fifteen BASIC programs, two shell scripts and four headers, and what makes it safe is
mostly ORDER (the structure test before the first change, the administrator test before the gate test, the gate read before the file is looked
at, the reserved-name test before a Linux user is made, the marker consumed at once) and the BLANK-MEANS-ON rule, which lives in five places
that must agree and is the one place where a careless "= 'YES'" turns a delivered default into a wall that is not one.

The blocks of checks:  N numbers, bits, fields and messages  K the kernel (root, tests, keys, the record rule, the structure sites)
L the BASIC lookup (_voc_ref, !shared_ref, !edit_msg, list.shared)  G the gates (loaders, words, reports, manifest, reserved name)
I the installer and the remover  R the suite is wired into regress.sh and regress-map.txt.

***AND THE CHECKS ARE THEMSELVES CHECKED.***  --selftest breaks each invariant in the way an edit plausibly would and requires some check to
notice.  A mutant that nothing catches, or that does not change the file it names, is reported as a FAILURE of the self-test.
"""

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

# the exact texts of the spec (.claude/s66-design.md 1.6)
MSG = {
    11513: "A file in the shared account can only be changed by an account that has shared.write (SDSYS can give it: modify.account <account> shared-write-on)",
    11514: "The structure of a file in the shared account (making, clearing, configuring, indexing, triggers, renaming or deleting it) can only be changed by SDSYS, signed on at a terminal",
    11515: "Account %1 has shared.read %2, shared.write %3",
    11516: "The account name shared is reserved for the shared account, which the installer makes: it cannot be created, restored or attached by hand",
    11517: "The shared account cannot be deleted",
    11518: "There is no shared account in service",
    11519: "Files of the shared account that can be opened by name: %1",
    11520: "Account %1 has shared.read off, so it cannot open the files of the shared account by name (SDSYS can give it back: modify.account %1 shared-read-on)",
}
# who may cite which of the eight messages
MSG_USERS = {11513: {"edit_msg"}, 11514: {"edit_msg"}, 11515: {"create_account", "modifya"}, 11516: {"create_account"}, 11517: {"delacc"},
             11518: {"listshared"}, 11519: {"listshared"}, 11520: {"listshared"}}

BP_PROGRAMS = ("login", "cproc", "apisrvr", "createa", "create_account", "modifya", "delacc", "acc_os_info", "restorea", "_voc_ref", "shared_ref",
               "listshared", "edit_msg", "edit_guard", "ide", "ced_edit", "spview", "sed", "cname", "createf", "deletef", "basic")
C_NAMED = ("keys.h", "sysseg.h", "sd.h", "op_sh.c", "op_kernel.c", "op_dio1.c", "op_dio2.c", "op_dio3.c", "dh_ak.c", "dh_misc.c", "op_seqio.c",
           "op_jumps.c", "kernel.c")
EDIT_MSG_SITES = (("edit_guard", "display edit_msg(kind)"), ("ide", "msg = edit_msg(edit.kind)"), ("ced_edit", "message.text = edit_msg(edit.kind)"),
                  ("spview", "prompt.text = edit_msg(edit.kind)"), ("sed", "message = edit_msg(edit.kind)"), ("cname", "stop edit_msg(ek.kind)"),
                  ("createf", "stop edit_msg(ek.kind)"), ("deletef", "stop edit_msg(ef.kind)"), ("apisrvr", "error.msg = edit_msg(ed.kind)"))


def strip_c(src):
    def blank(m):
        return "\n" * m.group(0).count("\n")
    src = re.sub(r"/\*.*?\*/", blank, src, flags=re.S)
    return re.sub(r"//[^\n]*", "", src)


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


def strip_sh(src):
    return "\n".join("" if l.lstrip().startswith("#") else l for l in src.split("\n"))


def code(name, text):
    if name.startswith("c:"):
        return strip_c(text)
    if name.startswith(("sh:", "txt:")):
        return strip_sh(text)
    if name.startswith(("bp:", "sys:")):
        return strip_bas(text)
    return text


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


def func_body(text, signature):
    """The text of the C function that begins at SIGNATURE, up to the matching close brace (comments already removed)."""
    m = re.search(re.escape(signature) + r"\s*\{", text)
    i = m.start() if m else text.find(signature)
    if i < 0:
        return ""
    j = text.find("{", i)
    depth = 0
    for k in range(j, len(text)):
        if text[k] == "{":
            depth += 1
        elif text[k] == "}":
            depth -= 1
            if depth == 0:
                return text[i:k + 1]
    return text[i:]


def between(text, a, b):
    """The text from A up to the next B after it ('' if either is missing)."""
    i = text.find(a)
    if i < 0:
        return ""
    j = text.find(b, i + len(a))
    return text[i:j] if j >= 0 else ""


def sh_func(text, name):
    """A shell function that starts at column 0 as 'name() {' and ends at the first '}' at column 0."""
    m = re.search(r"^%s\(\) \{.*?^\}" % re.escape(name), text, re.S | re.M)
    return m.group(0) if m else ""


def load():
    srcs = {}

    def get(name, path):
        if not os.path.exists(path):
            print("test-shared-units: CANNOT RUN - %s is missing" % path)
            sys.exit(2)
        with open(path, encoding="utf-8", errors="replace") as f:
            srcs[name] = f.read()
    for fn in sorted(os.listdir(GPLSRC)):
        if fn.endswith((".c", ".h")):
            get("c:" + fn, os.path.join(GPLSRC, fn))
    for n in C_NAMED:
        if "c:" + n not in srcs:
            print("test-shared-units: CANNOT RUN - %s is missing" % os.path.join(GPLSRC, n))
            sys.exit(2)
    for fn in sorted(os.listdir(GPL)):
        p = os.path.join(GPL, fn)
        if os.path.isfile(p):
            get("bp:" + fn, p)
    for n in BP_PROGRAMS:
        if "bp:" + n not in srcs:
            print("test-shared-units: CANNOT RUN - %s is missing" % os.path.join(GPL, n))
            sys.exit(2)
    get("sys:keys.h", os.path.join(SDSYS, "syscom", "keys.h"))
    get("sys:createacc.h", os.path.join(SDSYS, "syscom", "createacc.h"))
    get("sh:installsdcore.sh", os.path.join(ROOT, "installsdcore.sh"))
    get("sh:deletesdcore.sh", os.path.join(ROOT, "deletesdcore.sh"))
    get("txt:regress.sh", os.path.join(HERE, "regress.sh"))
    get("txt:regress-map.txt", os.path.join(HERE, "regress-map.txt"))
    get("voc:list.shared", os.path.join(SDSYS, "voc_template", "list.shared"))
    srcs["newvoc.list"] = "\n".join(sorted(os.listdir(os.path.join(SDSYS, "newvoc"))))
    srcs["voc_template.list"] = "\n".join(sorted(os.listdir(os.path.join(SDSYS, "voc_template"))))
    for n in MSG:
        p = os.path.join(MSGDIR, str(n))
        srcs["msg:%d" % n] = open(p, encoding="utf-8", errors="replace").read() if os.path.exists(p) else None
    for t in ("sandbox-shared.py", "test-shared-units.py", "test-install-shared.sh"):
        srcs["file:" + t] = open(os.path.join(HERE, t), encoding="utf-8", errors="replace").read() if os.path.exists(os.path.join(HERE, t)) else None
    return srcs


def defs(text, pattern, base=10):
    return {m.group(1): int(m.group(2), base) for m in re.finditer(pattern, text)}


def checks(srcs):
    rows = []

    def ck(i, ok, detail=""):
        rows.append((i, bool(ok), detail))

    c = {name: code(name, text) for name, text in srcs.items() if isinstance(text, str)}

    def C(n):
        return c["c:" + n]

    def B(n):
        return c["bp:" + n]

    # ---- N. numbers, bits, fields, messages ------------------------------------------------------------------------------------
    kk = defs(C("keys.h"), r"#define\s+(K_[A-Z0-9_]+)\s+(\d+)")
    want = {"K_SHARED_READ": 128, "K_SHARED_WRITE": 129, "K_SHARED_REF": 130, "K_SHARED_ONCE": 131}
    ck("N1 keys.h: K_SHARED_READ 128, K_SHARED_WRITE 129, K_SHARED_REF 130, K_SHARED_ONCE 131, and no kernel key number is used twice",
       all(kk.get(k) == v for k, v in want.items()) and len(set(kk.values())) == len(kk.values()), repr({k: kk.get(k) for k in want}))
    bk = defs(B("int$keys.h"), r"\$define\s+(K\$[A-Z0-9.]+)\s+(\d+)")
    mirror = {"K$SHARED.READ": 128, "K$SHARED.WRITE": 129, "K$SHARED.REF": 130, "K$SHARED.ONCE": 131}
    ck("N2 int$keys.h carries the same four numbers and none is used twice",
       all(bk.get(k) == v for k, v in mirror.items()) and len(set(v for v in bk.values() if v >= 100)) == len([v for v in bk.values() if v >= 100]), repr({k: bk.get(k) for k in mirror}))
    acc = defs(c["sys:keys.h"], r"\$define\s+(ACC\$[A-Z0-9.]+)\s+(\d+)")
    ck("N3 syscom/keys.h: ACC$SHARED.READ is register field 13, ACC$SHARED.WRITE 14, ACC$NET still 15, and no field is used twice",
       acc.get("ACC$SHARED.READ") == 13 and acc.get("ACC$SHARED.WRITE") == 14 and acc.get("ACC$NET") == 15 and len(set(acc.values())) == len(acc.values()), repr(acc))
    ug = defs(C("sysseg.h"), r"#define\s+(UG_[A-Z_]+)\s+(0x[0-9A-Fa-f]+)", 16)
    ck("N4 sysseg.h: UG_SHARED_READ is 0x0010 and UG_SHARED_WRITE 0x0020, each one bit, no bit used twice, the gates word still 16 bits",
       ug.get("UG_SHARED_READ") == 0x10 and ug.get("UG_SHARED_WRITE") == 0x20 and len(set(ug.values())) == len(ug)
       and all(v & (v - 1) == 0 for v in ug.values()) and re.search(r"u_int16_t\s+gates\s*;", C("sysseg.h")) is not None, repr(ug))
    ca = defs(c["sys:createacc.h"], r"\$define\s+(CA\$[A-Z0-9.]+)\s+(\d+)")
    ck("N5 createacc.h: CA$SHARED.READ.OFF is 37 and CA$SHARED.WRITE 38, inside the Linux-only block (31 to 40), and no setting is used twice",
       ca.get("CA$SHARED.READ.OFF") == 37 and ca.get("CA$SHARED.WRITE") == 38 and len(set(ca.values())) == len(ca.values())
       and all(31 <= ca[k] <= 40 for k in ("CA$SHARED.READ.OFF", "CA$SHARED.WRITE") if k in ca), repr({k: v for k, v in ca.items() if v >= 31}))
    ed = defs(C("sd.h"), r"#define\s+(EDIT_[A-Z_]+)\s+(\d+)")
    ck("N6 sd.h: EDIT_SHARED_WRITE is 4 and EDIT_SHARED_STRUCT 5, after EDIT_PROG 3, each kind a number of its own",
       ed.get("EDIT_SHARED_WRITE") == 4 and ed.get("EDIT_SHARED_STRUCT") == 5 and ed.get("EDIT_PROG") == 3 and len(set(ed.values())) == len(ed), repr(ed))
    protos = ("bool shared_root_get(char *out)", "bool path_in_shared(const char *canon)", "bool path_resolved_in_shared(const char *name)",
              "bool shared_write_ok(void)", "int edit_refusal_for_canon(const char *canon)", "int edit_refusal_for_name(const char *name)",
              "bool shared_ref_ok(const char *path, int fno, const char *catname)", "bool shared_once(const char *name)",
              "int edit_refused_message(int kind)", "int shared_structure_refusal(FILE_VAR *fvar)")
    flat = re.sub(r"\s+", "", C("sd.h"))
    ck("N7 sd.h declares the ten functions of the shared account's kernel half, and get_voc_file_reference_ex with its fifth argument",
       all(p.replace(" ", "") + ";" in flat for p in protos) and re.search(r"get_voc_file_reference_ex\([^)]*boolallow_shared\)", flat) is not None,
       repr([p for p in protos if p.replace(" ", "") + ";" not in flat]))
    texts = {n: srcs.get("msg:%d" % n) for n in MSG}
    ck("N8 messages 11513 to 11520 exist with EXACTLY the texts of the spec (one line each; the 231 byte bound once expanded is test-msglen-units.py's)",
       all(texts[n] is not None and texts[n].rstrip("\n") == t and "\n" not in texts[n].rstrip("\n") for n, t in MSG.items()),
       repr([n for n, t in MSG.items() if texts[n] is None or texts[n].rstrip("\n") != t]))
    users = {n: set() for n in MSG}
    for name, text in c.items():
        if name.startswith("bp:"):
            for m in re.finditer(r"\b(1151[3-9]|11520)\b", text):
                users[int(m.group(1))].add(name[3:])
    cusers = sorted(name for name, text in c.items() if name.startswith("c:") and re.search(r"\b(1151[3-9]|11520)\b", text))
    ck("N9 the eight messages are cited only by the programs that own them (11513 and 11514 by !edit_msg, 11515 by create_account and modifya, 11516 by "
       "create_account, 11517 by delacc, 11518 to 11520 by list.shared) and, in C, only by op_sh.c's edit_refused_message: every kernel refusal says EDIT_SHARED_STRUCT, not a number",
       all(users[n] == MSG_USERS[n] for n in MSG) and cusers == ["c:op_sh.c"], repr({n: sorted(u) for n, u in users.items() if u != MSG_USERS[n]}) + repr(cusers))

    # ---- K. the kernel --------------------------------------------------------------------------------------------------------
    sh = C("op_sh.c")
    rg = func_body(sh, "bool shared_root_get(char *out)")
    ck("K1 shared_root_get: the root is line 1 of <sysdir>/accounts/shared, absolute, resolved with realpath(), trailing slashes stripped, a root of length 1 or less refused, "
       "and the cache is set (have = TRUE) only AFTER all of that",
       "accounts%cshared" in rg and "sd_sysdir()" in rg and "body[0] != '/'" in rg and ordered(rg, "realpath(line1, resolved)", "resolved[n - 1] == '/'", "if (n <= 1)", "have = TRUE;")
       and rg.count("have = TRUE;") == 1, "")
    ck("K1b ...a HIT is kept for the life of the process and a MISS is retried no more than once a minute (a session started before the installer made the account must "
       "begin enforcing when it appears); the time of the try is taken BEFORE the file is opened; and the SUSPENDED word is never looked at (suspension must not unprotect the files)",
       re.search(r"#define SHARED_RETRY_SECONDS 60\b", sh) is not None
       and re.search(r"if \(have\) \{\s*strcpy\(out, root\);\s*return TRUE;\s*\}", rg) is not None
       and re.search(r"if \(\(last_try != 0\) && \(now >= last_try\) && \(\(now - last_try\) < SHARED_RETRY_SECONDS\)\)\s*return FALSE;\s*last_try = now;", rg) is not None
       and ordered(rg, "last_try = now;", "fopen(path") and "SUSPEND" not in rg.upper(), "")
    ps = func_body(sh, "bool path_in_shared(const char *canon)")
    ck("K2 path_in_shared: no root is no shared (FALSE); a pathname is inside when it begins with the root and the next byte is the end or a slash (so /x/shared2 is not inside /x/shared)",
       "!shared_root_get(root)" in ps and "strncmp(canon, root, len) == 0" in ps and "canon[len] == '\\0'" in ps and "canon[len] == '/'" in ps
       and re.search(r"return \(strncmp\(canon, root, len\) == 0\) && \(\(canon\[len\] == '\\0'\) \|\| \(canon\[len\] == '/'\)\);", ps) is not None, "")
    pr = func_body(sh, "bool path_resolved_in_shared(const char *name)")
    ck("K2b path_resolved_in_shared: no root is FALSE, an empty name is FALSE, a name that cannot be resolved is TRUE once the root is known (a gate that fails open on a path it cannot read is "
       "decoration), otherwise path_in_shared of the resolved name",
       ordered(pr, "!shared_root_get(root)", "return FALSE;", "name[0] == '\\0'", "return FALSE;", "!resolve_name(cwd, name, resolved)", "return TRUE;", "return path_in_shared(resolved);"), "")
    sw = func_body(sh, "bool shared_write_ok(void)")
    ck("K3 shared_write_ok is the administrator or the UG_SHARED_WRITE bit and nothing else",
       "MY_ADMIN()" in sw and "UG_SHARED_WRITE" in sw and "UG_SHARED_READ" not in sw and "UG_NET" not in sw, "")
    fc = func_body(sh, "int edit_refusal_for_canon(const char *canon)")
    fnm = func_body(sh, "int edit_refusal_for_name(const char *name)")
    ck("K4 edit_refusal_for_canon: the administrator passes FIRST, then a file inside shared without shared.write is EDIT_SHARED_WRITE, THEN the S.64 kind (so a shared dictionary needs "
       "shared.write AND dict.edit, and the refusal names the first that is missing)",
       ordered(fc, "MY_ADMIN()", "return EDIT_NONE;", "path_in_shared(canon)", "!shared_write_ok()", "return EDIT_SHARED_WRITE;", "edit_kind_of_path(canon)", "!edit_permitted(kind)", "return kind;", "return EDIT_NONE;"), "")
    ck("K4b ...edit_refusal_for_name is the same in the same order for a string from BASIC (resolved first), and edit_ok_for_path is edit_refusal_for_name(path) == EDIT_NONE",
       ordered(fnm, "MY_ADMIN()", "return EDIT_NONE;", "path_resolved_in_shared(name)", "!shared_write_ok()", "return EDIT_SHARED_WRITE;", "edit_kind_of_path(name)", "!edit_permitted(kind)", "return kind;", "return EDIT_NONE;")
       and re.search(r"bool edit_ok_for_path\(const char \*path\) \{\s*return edit_refusal_for_name\(path\) == EDIT_NONE;\s*\}", sh) is not None, "")
    em = func_body(sh, "int edit_refused_message(int kind)")
    ck("K4c edit_refused_message: kinds 1 to 3 are 11404 + kind, EDIT_SHARED_WRITE is 11513, EDIT_SHARED_STRUCT is 11514, anything else 11405",
       re.search(r"case EDIT_VOC:\s*case EDIT_DICT:\s*case EDIT_PROG:\s*return 11404 \+ kind;", em) is not None
       and re.search(r"case EDIT_SHARED_WRITE:\s*return 11513;", em) is not None and re.search(r"case EDIT_SHARED_STRUCT:\s*return 11514;", em) is not None
       and re.search(r"return 11405;\s*\}$", em) is not None, "")
    sr = func_body(sh, "bool shared_ref_ok(const char *path, int fno, const char *catname)")
    ck("K5 shared_ref_ok: fno must be 2 or 3; the path absolute, short enough, with a known root; realpath() must succeed (the file exists); and it must be STRICTLY under the root "
       "(root + '/' + at least one more byte: the root itself is the $acc entry and is refused)",
       ordered(sr, "(fno != 2) && (fno != 3)", "return FALSE;", "path[0] != '/'", "!shared_root_get(root)", "realpath(path, resolved)", "strncmp(resolved, root, root_len) != 0",
               "resolved[root_len] != '/'", "resolved[root_len + 1] == '\\0'", "return FALSE;"), "")
    ck("K5b ...every component below the root is classified (edit_kind_of_name): EDIT_NONE, except that for field 3 the LAST must be a dictionary; a component called cat, or the last component "
       "of the shared account's own private catalogue (catname), is refused; and it answers TRUE only at the end",
       ordered(sr, "edit_kind_of_name(comp)", "(fno == 3) && is_last", "kind != EDIT_DICT", "return FALSE;", "kind != EDIT_NONE", "return FALSE;", 'strcasecmp(comp, "cat") == 0',
               "return FALSE;", "strncasecmp(comp, cat_last, n) == 0", "return FALSE;", "return TRUE;"), "")
    so = func_body(sh, "bool shared_once(const char *name)")
    ck("K6 shared_once: an empty name is TRUE, a name seen is FALSE (compared with strcasecmp), 64 names are remembered and a full table answers TRUE (more audit, never less)",
       "static char seen[64][64]" in so and ordered(so, "name[0] == '\\0'", "return TRUE;", "strcasecmp(seen[i], key) == 0", "return FALSE;", "count >= 64", "return TRUE;", "strcpy(seen[count++], key);", "return TRUE;"), "")
    kn = C("op_kernel.c")
    sk = kn[at(kn, "case K_SHARED_READ:"):at(kn, "case K_SHARED_REF:")]
    ck("K7 K_SHARED_READ and K_SHARED_WRITE set only from a $internal program (n >= 0, then HDR_INTERNAL, then the bit), -1 only asks; each touches its OWN bit, answers it as 1 or 0, and "
       "closes no connection (net_close_all is not called: the shared gates have nothing to do with NET)",
       kn.count("case K_SHARED_READ:") == 1 and kn.count("case K_SHARED_WRITE:") == 1 and "GetInt(descr)" in sk
       and ordered(sk, "n >= 0", "HDR_INTERNAL", "SET_MY_GATE(shared_bit, n > 0)", "MY_GATE(shared_bit)")
       and "shared_bit = (action == K_SHARED_READ) ? UG_SHARED_READ : UG_SHARED_WRITE" in sk
       and "UG_NET" not in sk and "UG_VOC_EDIT" not in sk and "UG_BP_EDIT" not in sk and "UG_DICT_EDIT" not in sk and "net_close_all" not in sk, "")
    ck("K7b ...they sit AFTER the K_EDIT_OS_OK block and BEFORE K_PATH_OK, so the text between K_NET and K_EDIT_OK that test-net-units cuts out does not change",
       ordered(kn, "case K_NET:", "case K_EDIT_OK:", "case K_EDIT_OS_OK:", "case K_SHARED_READ:", "case K_SHARED_WRITE:", "case K_SHARED_REF:", "case K_SHARED_ONCE:", "case K_PATH_OK:")
       and "K_SHARED" not in between(kn, "case K_NET:", "case K_EDIT_OK:"), "")
    kr = kn[at(kn, "case K_SHARED_REF:"):at(kn, "case K_SHARED_ONCE:")]
    ck("K7c K_SHARED_REF answers 0 by default, splits the argument at two field marks, and asks shared_ref_ok(path, atoi(fno), catname); an argument that does not split into three parts stays 0",
       "result.data.value = 0;" in kr and kr.count("strchr(") == 2 and kr.count("FIELD_MARK") == 2 and "shared_ref_ok(shared_buf, atoi(shared_fno), shared_cat) ? 1 : 0" in kr, "")
    ko = kn[at(kn, "case K_SHARED_ONCE:"):at(kn, "case K_PATH_OK:")]
    ck("K7d K_SHARED_ONCE answers shared_once of the name", "shared_once(shared_name) ? 1 : 0" in ko, "")
    ke = kn[at(kn, "case K_EDIT_OK:"):at(kn, "case K_EDIT_OS_OK:")]
    ck("K7e K_EDIT_OK keeps its administrator shortcut and asks edit_ok_for_path; K_EDIT_KIND of a string answers the REFUSING kind (edit_refusal_for_name) and, when nothing refuses, the raw kind "
       "(edit_kind_of_path) as before",
       ordered(ke, "MY_ADMIN()", "edit_ok_for_path(edit_name)") and ordered(ke, "result.data.value = edit_refusal_for_name(edit_name);", "== EDIT_NONE", "result.data.value = edit_kind_of_path(edit_name);"), "")
    d3 = C("op_dio3.c")
    er = func_body(d3, "Private int edit_refusal(FILE_VAR *fvar)")
    ck("K8 edit_refusal (the record rule): a file with no pathname, a $internal program and the administrator return EDIT_NONE BEFORE edit_refusal_for_canon is asked of the file table's pathname; "
       "EDIT_REFUSED_MSG is edit_refused_message",
       ordered(er, "DYNAMIC_FILE", "return EDIT_NONE;", "HDR_INTERNAL", "return EDIT_NONE;", "MY_ADMIN()", "return EDIT_NONE;", "edit_refusal_for_canon(path)")
       and "#define EDIT_REFUSED_MSG(kind) edit_refused_message(kind)" in d3 and "FPtr(fvar->file_id)->pathname" in er, "")
    ss = func_body(d3, "int shared_structure_refusal(FILE_VAR *fvar)")
    ck("K9 shared_structure_refusal: NONE for no file variable, a file of another type and the administrator; EDIT_SHARED_STRUCT for a pathname inside shared; and HDR_INTERNAL is NOT an exemption "
       "(no sanctioned internal path changes the structure of a shared file for a non-administrator)",
       ordered(ss, "fvar == NULL", "DYNAMIC_FILE", "DIRECTORY_FILE", "return EDIT_NONE;", "MY_ADMIN()", "return EDIT_NONE;", "path_in_shared(", "return EDIT_SHARED_STRUCT;", "return EDIT_NONE;")
       and "HDR_INTERNAL" not in ss and "process.program" not in ss, "")
    cl = func_body(d3, "void op_clrfile()")
    ck("K10 op_clrfile asks shared_structure_refusal right after the NET_FILE block and BEFORE the transaction test, the read-only test, the S.64 block and the file lock; message 11514 via "
       "EDIT_SHARED_STRUCT, an error unless ON ERROR, the status -ER_PERM with the file variable dropped and the status pushed",
       ordered(cl, "refuse_net_file(fvar", "fvar->type == NET_FILE", "shared_structure_refusal(fvar) != EDIT_NONE", "EDIT_REFUSED_MSG(EDIT_SHARED_STRUCT)", "process.status = -ER_PERM;", "k_dismiss();",
               "k_txn_error()", "FV_RDONLY", "edit_refusal(fvar)", "StartExclusive(")
       and re.search(r"if \(shared_structure_refusal\(fvar\) != EDIT_NONE\) \{\s*if \(!\(op_flags & P_ON_ERROR\)\)\s*k_error\(sysmsg\(EDIT_REFUSED_MSG\(EDIT_SHARED_STRUCT\)\)\);\s*process\.status = -ER_PERM;\s*k_dismiss\(\);", cl) is not None, "")
    d1, d2, dk, dm = C("op_dio1.c"), C("op_dio2.c"), C("dh_ak.c"), C("dh_misc.c")
    SREF = "shared_structure_refusal(fvar) != EDIT_NONE"
    cfl = func_body(d1, "void op_configfl()")
    ck("K11 op_configfl asks the structure test after the NET_FILE test and BEFORE the read-only test and dh_configure", ordered(cfl, "net_refuse(fvar", SREF, "FV_RDONLY", "dh_configure("), "")
    akc, ake = func_body(dk, "void op_akclear()"), func_body(dk, "void op_akenable()")
    ck("K11b op_akclear asks it before the type test and ak_clear; op_akenable before its first change",
       ordered(akc, "net_refuse(fvar", SREF, "fvar->type != DYNAMIC_FILE", "ak_clear(") and ordered(ake, "net_refuse(fvar", SREF, "fvar->type == DYNAMIC_FILE && akno < MAX_INDICES"), "")
    cra, dka = func_body(dk, "void op_createak()"), func_body(dk, "void op_deleteak()")
    ck("K11c op_createak and op_deleteak are given PATHNAMES, so they ask path_resolved_in_shared (the data path and the index path; the file's path) before create_ak / delete_ak; the administrator passes",
       ordered(cra, "MY_ADMIN()", "path_resolved_in_shared(data_path)", "path_resolved_in_shared(ak_path)", "edit_refused_message(EDIT_SHARED_STRUCT)", "create_ak(")
       and ordered(dka, "MY_ADMIN()", "path_resolved_in_shared(pathname)", "edit_refused_message(EDIT_SHARED_STRUCT)", "delete_ak(")
       and "shared_structure_refusal" not in cra and "shared_structure_refusal" not in dka, "")
    ck("K11d op_akwrite, op_akdelete, op_akmap, op_akread and op_akrelease are NOT asked: _ak runs them on every write to an indexed file, so refusing them would break index maintenance for a "
       "legitimate shared.write user",
       all("shared_structure_refusal" not in func_body(dk, "void %s()" % n) and "path_resolved_in_shared" not in func_body(dk, "void %s()" % n) and "path_in_shared" not in func_body(dk, "void %s()" % n)
           and func_body(dk, "void %s()" % n) != "" for n in ("op_akwrite", "op_akdelete", "op_akmap", "op_akread", "op_akrelease")), "")
    fcn, pfc, stg = func_body(dm, "void op_fcontrol()"), func_body(dm, "void pub_fcontrol()"), func_body(dm, "void op_settrig()")
    first_sw = between(fcn, "switch (action) {", "switch (action) {")
    ck("K12 op_fcontrol: the seven actions that CHANGE a setting (FC_SET_JNL_FNO, FC_KILL_JNL, FC_SET_AKPATH, FC_NON_TXN, FC_SPLIT_MERGE, FC_NO_RESIZE, FC_SET_MODE) are refused in a switch of their own "
       "BEFORE the switch that does them; FC_SET_SEQ_KEY and FC_GET_SEQ_KEY (record level) are not",
       all(k in first_sw for k in ("FC_SET_JNL_FNO", "FC_KILL_JNL", "FC_SET_AKPATH", "FC_NON_TXN", "FC_SPLIT_MERGE", "FC_NO_RESIZE", "FC_SET_MODE")) and SREF in first_sw
       and "FC_SET_SEQ_KEY" not in first_sw and "FC_GET_SEQ_KEY" not in first_sw and fcn.count("switch (action) {") == 2, "")
    ck("K12b pub_fcontrol: FC$SYNC (1), FC$CRLF (4) and FC$MINMOD (7) are refused when the qualifier SETS (not -1), before the switch; 2, 3, 5 and 6 are left alone",
       re.search(r"\(action == 1\) \|\| \(action == 4\) \|\| \(action == 7\)\) && \(shared_structure_refusal\(fvar\) != EDIT_NONE\)\)", pfc) is not None
       and ordered(pfc, "shared_structure_refusal(fvar)", "descr->data.value != -1", "edit_refused_message(EDIT_SHARED_STRUCT)", "switch (action) {"), "")
    ck("K12c op_settrig asks it after the file variable is read and BEFORE a trigger is set on either kind of file", ordered(stg, "k_get_file(descr)", SREF, "dir_set_trigger(", "DYNAMIC_FILE"), "")
    osp = func_body(d2, "void op_ospath()")
    osn = func_body(d2, "void op_osrename()")
    ck("K13 OSPATH: OS_DELETE, OS_MKDIR and OS_MKPATH (not OS_CHOWN) are answered 0 with ER_PERM for a non-administrator naming a path inside shared, BEFORE the switch that does them; "
       "OSRENAME refuses a rename with either name inside shared before it looks at the old path",
       re.search(r"\(\(key == OS_DELETE\) \|\| \(key == OS_MKDIR\) \|\| \(key == OS_MKPATH\)\) && !MY_ADMIN\(\) && path_resolved_in_shared\(path\)", osp) is not None
       and ordered(osp, "path_resolved_in_shared(path)", "process.status = ER_PERM;", "status = 0;", "switch (key) {") and "OS_CHOWN" not in between(osp, "path_resolved_in_shared(path)", "switch (key) {")
       and ordered(osn, "MY_ADMIN()", "path_resolved_in_shared(old_path)", "path_resolved_in_shared(new_path)", "ER_PERM", "access(old_path, 0)", "rename(old_path, new_path)"), "")
    cer = func_body(d1, "Private int create_edit_refusal(const char* path)")
    ck("K14 create_edit_refusal: making anything inside shared is EDIT_SHARED_STRUCT for a non-administrator, tested BEFORE the $internal exemption (createf is $internal); op_create_dh and "
       "op_create_t1 print edit_refused_message(kind), not 11404 + kind",
       ordered(cer, "MY_ADMIN()", "path_resolved_in_shared(path)", "return EDIT_SHARED_STRUCT;", "HDR_INTERNAL", "return EDIT_NONE;", "edit_os_path_refusal(path, FALSE)")
       and d1.count("k_error(sysmsg(edit_refused_message(edit_kind)))") == 2 and "11404 + edit_kind" not in d1, "")
    ck("K15 get_voc_file_reference is a wrapper that passes FALSE, get_voc_file_reference_ex pushes the fifth INTEGER and calls k_recurse(pcode_voc_ref, 5), and ONLY open_file's map_name call "
       "passes TRUE (OPENSEQ and DELETESEQ never follow shared; CALL \"file prog\" no longer exists, so op_jumps.c does not look a file up at all)",
       "return get_voc_file_reference_ex(voc_name, get_dict_name, path, vflags, FALSE);" in d1 and "k_recurse(pcode_voc_ref, 5)" in d1 and "(e_stack++)->data.value = allow_shared;" in d1
       and sum(t.count("get_voc_file_reference_ex(") for n, t in c.items() if n.startswith("c:") and n not in ("c:sd.h", "c:op_dio1.c")) == 0
       and d1.count("get_voc_file_reference_ex(") == 3 and d1.count("vflags, TRUE)") == 1 and d1.count("vflags, FALSE)") == 1
       and ordered(func_body(d1, "Private void open_file(bool map_name)"), "if (map_name) {", "get_voc_file_reference_ex(voc_name, open_dict, mapped_name, vflags, TRUE)")
       and "get_voc_file_reference(" in C("op_seqio.c") and "get_voc_file_reference(" not in C("op_jumps.c"), "")

    # ---- L. the BASIC lookup ------------------------------------------------------------------------------------------------------
    vr = B("_voc_ref")
    fb = "if allow.shared and component = '' and not(vr.admin) then"
    fbb = between(vr, fb, "parse.as.q.pointer:")
    ck("L1 _voc_ref has a fifth argument, deffun shared_ref calling !shared_ref, and the fallback is in the else of the account's own first VOC read: AFTER the three folds and the PATH: / "
       "Account:File forms (the account's own entry always wins), guarded by allow.shared, no component, not the administrator and the session's K$SHARED.READ, BEFORE the final ER$NVR; "
       "on an answer it sets pathname and vflags and returns status 0",
       "subroutine voc_ref(filename, is.dict, pathname, vflags, allow.shared)" in vr and "deffun shared_ref(name, fno, quiet) calling '!shared_ref'" in vr
       and ordered(vr, "read voc.rec from voc,voc.id else", "read voc.rec from voc,downcase(voc.id) then", "read voc.rec from voc,upcase(voc.id) then", "upcase(x1) = 'PATH'", fb)
       and ordered(vr[at(vr, fb):], "if kernel(K$SHARED.READ, -1) then", "shared.ans = shared_ref(voc.id, fno, @false)", "pathname = shared.ans<1>", "vflags = shared.ans<2>", "set.status 0", "return",
                   "set.status ER$NVR", "parse.as.q.pointer:")
       and "set.status ER$NVR" in fbb and vr.count("shared_ref(") == 2 and "check.f.path" not in fbb and "qroot" not in fbb, "")
    sr_ = B("shared_ref")
    ck("L2 !shared_ref, step 1 and 2: unless quiet the administrator is refused FIRST (SDSYS reaches the files with LOGTO shared) and then a session without K$SHARED.READ; quiet (list.shared) is "
       "the only way past them",
       re.search(r"if not\(quiet\) then\s*if kernel\(K\$ADMINISTRATOR, -1\) then return ''\s*if not\(kernel\(K\$SHARED\.READ, -1\)\) then return ''\s*end", sr_) is not None
       and "$internal" in sr_ and "$catalog !shared_ref" in sr_ and len(re.findall(r"\bquiet\b", sr_)) == 3, "")
    ck("L2b ...step 3 to 5: fno must be 2 or 3; the name 1 to 63 characters, folded to lower case, its FIRST character a letter or digit (so no name that begins with $ & ! * _ or %), the rest letters, "
       "digits and . _ - $; a name in the stock VOC (newvoc) is never looked up, and an unreadable stock file refuses",
       ordered(sr_, "if fno # 2 and fno # 3 then return ''", "len(name) < 1 or len(name) > 63", "lname = downcase(name)", "index(letters : digits, lname[1,1], 1) = 0", "return ''",
               "index(letters : digits : '._-$', lname[ch,1], 1) = 0", "if not(shape.ok) then return ''", "openpath @sdsys:@ds:'newvoc' to stock.f else return ''",
               "read stock.rec from stock.f, lname then", "return ''")
       and re.search(r"read stock\.rec from stock\.f, lname then\s*close stock\.f\s*return ''\s*end", sr_) is not None
       and "letters = 'abcdefghijklmnopqrstuvwxyz'" in sr_ and "digits = '0123456789'" in sr_, "")
    ck("L2c ...step 6 to 8: the register record of the account called shared must exist, must not be SUSPENDED, and its path must be absolute (no token expansion); then its VOC is opened, read with the "
       "same three folds as _voc_ref, and the entry must be an F (upcase of the first character) that is not a multifile",
       ordered(sr_, "openpath @sdsys:@ds:'accounts' to acc.f else return ''", "read acc.rec from acc.f, 'shared' else", "upcase(trim(acc.rec<ACC$SUSPENDED>)) = 'SUSPENDED' then return ''",
               "spath[1,1] # @ds then return ''", "openpath spath:@ds:'voc' to svoc else return ''", "read rec from svoc, name then", "read rec from svoc, lname then",
               "read rec from svoc, upcase(name) then", "if not(found) then return ''", "if upcase(rec[1,1]) # 'F' then return ''", "if rec<4> # '' then return ''"), "")
    ck("L2d ...step 9 to 11: the pathname is field fno of the entry, an empty one refuses, one that begins with @ refuses (no token expansion), a relative one is taken from the shared directory; "
       "THEN the kernel's acceptance (K$SHARED.REF with the catalogue's name); only THEN the audit, once for each name, for a lookup and not for list.shared; the answer is the path and "
       "the VOC flags in capitals",
       ordered(sr_, "p = rec<fno>", "if p = '' then return ''", "if p[1,1] = '@' then return ''", "if p[1,1] # @ds then p = spath : @ds : p",
               "if not(kernel(K$SHARED.REF, p : @fm : fno : @fm : catname)) then return ''", "if not(quiet) then", "if kernel(K$SHARED.ONCE, lname) then",
               "void kernel(K$AUDIT, 'shared open file=' : lname)", "return p : @fm : upcase(rec<6>)")
       and sr_.count("K$AUDIT") == 1 and sr_.count("shared open file=") == 1 and at(sr_, "K$AUDIT") > at(sr_, "kernel(K$SHARED.REF,")
       and "$private.catalogue" in sr_ and "catname = crec<2>" in sr_, "")
    ck("L2e !shared_ref opens nothing by NAME (only openpath), so it cannot call _voc_ref again, and closes what it opened (the stock file, the register, the VOC)",
       re.search(r"^\s*open\s", sr_, re.M) is None and sr_.count("openpath ") == 3 and sr_.count("close stock.f") >= 2 and "close acc.f" in sr_ and "close svoc" in sr_, "")
    em_ = B("edit_msg")
    ck("L3 !edit_msg gives the text of 11405, 11406 and 11407 for kinds 1 to 3, 11513 for kind 4, 11514 for kind 5 and 11405 for anything else",
       re.search(r"case kind = 1\s*return sysmsg\(11405\)\s*case kind = 2\s*return sysmsg\(11406\)\s*case kind = 3\s*return sysmsg\(11407\)\s*case kind = 4\s*return sysmsg\(11513\)\s*"
                 r"case kind = 5\s*return sysmsg\(11514\)\s*end case\s*return sysmsg\(11405\)", em_) is not None and "$catalog !edit_msg" in em_, "")
    miss = [p for p, needle in EDIT_MSG_SITES if needle not in B(p)]
    clamp = [p for p, _ in EDIT_MSG_SITES if re.search(r"kind\s*>\s*3|11404\s*\+", B(p))]
    ck("L4 every program that prints an edit refusal calls edit_msg() (edit_guard, ide, ced_edit, spview, sed, cname, createf, deletef, the API server) and none keeps the clamp 'kind > 3' or the "
       "sum 11404 + kind: kinds 4 and 5 would print the VOC's message",
       not miss and not clamp, repr(miss) + repr(clamp))
    bs = B("basic")
    ck("L5 basic (the compiler verb) asks edit_guard(out.f) after the object file is open and before anything is compiled, for every session but the administrator (the bootstrap runs basic before "
       "!edit_guard is catalogued)",
       re.search(r"if not\(kernel\(K\$ADMINISTRATOR, -1\)\) then\s*if not\(edit_guard\(out\.f\)\) then\s*@system\.return\.code = -ER\$PERM\s*stop\s*end\s*end", bs) is not None
       and "deffun edit_guard(f) calling '!edit_guard'" in bs, "")
    ls = B("listshared")
    ck("L6 list.shared: an extra token is 2018; the order is the gate (11520, for a session that is not the administrator and has K$SHARED.READ off), then the register record (11518 when missing or "
       "SUSPENDED), then the VOC; each id goes through shared_ref with quiet = 1 (no administrator test, no gate test, no audit); the count line 11519 comes after the list; the return code is 0",
       ordered(ls, "sysmsg(2018", "not(kernel(K$ADMINISTRATOR, -1)) and not(kernel(K$SHARED.READ, -1))", "sysmsg(11520, @who)", "read acc.rec from acc.f, 'shared' else", "sysmsg(11518)",
               "SUSPENDED", "openpath spath:@ds:'voc' to svoc", "sselect svoc", "shared_ref(ids<i>, 2, 1)", "crt ids<i>", "crt sysmsg(11519, shown)", "@system.return.code = 0")
       and "$listshared" in ls and "$internal" in ls, "")
    vt = srcs["voc:list.shared"].split("\n")
    ck("L7 voc_template/list.shared is the three lines V / CA / $listshared, and the verb is NOT in newvoc (as list.servers is not): only SDSYS has it until it is given to an account",
       [x.strip() for x in vt if x.strip()] == ["V", "CA", "$listshared"] and "list.shared" not in srcs["newvoc.list"].split("\n") and "list.shared" in srcs["voc_template.list"].split("\n"), repr(vt))
    cats = {}
    for name, text in srcs.items():
        if name.startswith("bp:"):
            for m in re.finditer(r"^\$catalog\s+(\S+)", strip_bas(text), re.M):
                cats.setdefault(m.group(1).lower(), []).append(name[3:])
    ck("L8 the three new catalogue names are held by exactly one program each: !shared_ref, !edit_msg and $listshared",
       cats.get("!shared_ref") == ["shared_ref"] and cats.get("!edit_msg") == ["edit_msg"] and cats.get("$listshared") == ["listshared"], repr({k: cats.get(k) for k in ("!shared_ref", "!edit_msg", "$listshared")}))

    # ---- G. the gates ------------------------------------------------------------------------------------------------------------
    lg, cp, ap = B("login"), B("cproc"), B("apisrvr")
    rd = r"upcase\(trim\(%s<ACC\$SHARED\.READ>\)\) # 'NO'"
    ck("G1 BLANK MEANS ON, in LOGIN: shared.read is loaded as 'not no' (# 'NO') and shared.write as 'yes' (= 'YES'), after K$NET and before the S.64 edit gates, each once",
       re.search(r"void kernel\(K\$SHARED\.READ,\s*" + rd % r"acc\.rec" + r"\)", lg) is not None and re.search(r"void kernel\(K\$SHARED\.WRITE,\s*upcase\(trim\(acc\.rec<ACC\$SHARED\.WRITE>\)\) = 'YES'\)", lg) is not None
       and ordered(lg, "void kernel(K$NET,", "void kernel(K$SHARED.READ,", "void kernel(K$SHARED.WRITE,", "void kernel(K$VOC.EDIT,") and lg.count("kernel(K$SHARED.READ,") == 1 and lg.count("kernel(K$SHARED.WRITE,") == 1, "")
    ck("G1b ...in the API server: both grants start false (fail closed), are read from the register INSIDE the block that read it ('not no' for read, 'yes' for write), and are loaded at EVERY entry "
       "(outside master.login.done) immediately BEFORE K$NET",
       re.search(r"api\.shared\.read\.grant = @false\s*\napi\.shared\.write\.grant = @false", ap) is not None
       and re.search(r"api\.shared\.read\.grant = \(" + rd % r"acc\.rec" + r"\)", ap) is not None
       and re.search(r"api\.shared\.write\.grant = \(upcase\(trim\(acc\.rec<ACC\$SHARED\.WRITE>\)\) = 'YES'\)", ap) is not None
       and ordered(ap, "api.shared.read.grant = @false", "read acc.rec from acc.f, downcase(new.account) then", "api.shared.read.grant = (", "api.shared.write.grant = (",
                   "void kernel(K$SHARED.READ,  api.shared.read.grant)", "void kernel(K$SHARED.WRITE, api.shared.write.grant)", "void kernel(K$NET, api.net.grant)")
       and 0 <= at(ap, "void kernel(K$SHARED.READ,  api.shared.read.grant)") < at(ap, "if not(master.login.done) then\n   void kernel(K$VOC.EDIT"), "")
    ck("G1c ...the OS user sdsys entering the sdsys account holds both ON (an API session of sdsys follows shared and can write its records but has no administrator flag, so no structure change), "
       "set BEFORE the api.net.grant = @true line that test-net-units B4c needs last",
       re.search(r"if downcase\(@logname\) = 'sdsys' and downcase\(new\.account\) = 'sdsys' then(?:\s*\n\s*api\.[\w.]+\.grant = @true)*\s*\n\s*api\.net\.grant = @true\s*\n\s*end", ap) is not None
       and ordered(ap, "downcase(@logname) = 'sdsys'", "api.shared.read.grant = @true", "api.shared.write.grant = @true", "api.net.grant = @true"), "")
    ck("G1d ...in CPROC's logto: the loads need the register record to have a PATH (a LOGTO by path has no record: both gates OFF, fail closed), read is 'not no', write is 'yes', and they come after "
       "K$NET and before the logto audit line",
       re.search(r"void kernel\(K\$SHARED\.READ,\s*\(acc\.record<ACC\$PATH> # ''\) and \(" + rd % r"acc\.record" + r"\)\)", cp) is not None
       and re.search(r"void kernel\(K\$SHARED\.WRITE,\s*\(acc\.record<ACC\$PATH> # ''\) and \(upcase\(trim\(acc\.record<ACC\$SHARED\.WRITE>\)\) = 'YES'\)\)", cp) is not None
       and ordered(cp, "void kernel(K$NET, upcase(trim(acc.record<ACC$NET>)) = 'YES')", "void kernel(K$SHARED.READ,  (acc.record<ACC$PATH>", "void kernel(K$SHARED.WRITE, (acc.record<ACC$PATH>", "'logto account='"), "")
    ck("G1e ...CPROC clears acc.record BEFORE it reads the register (a failed openpath would otherwise leave the previous LOGTO's record in the variable and the gates would be read from it), holds the "
       "gates beside stk.net, and revert.account gives them back BEFORE the SD.ACCOUNTS line (so stk.net stays next to the revert audit line)",
       ordered(cp, "acc.record = ''", "openpath @sdsys:@ds:'accounts' to acc.f then", "read acc.record from acc.f, downcase(new.account) then")
       and re.search(r"stk\.net = kernel\(K\$NET, -1\)\s*\n\s*stk\.shared\.read = kernel\(K\$SHARED\.READ, -1\)\s*\n\s*stk\.shared\.write = kernel\(K\$SHARED\.WRITE, -1\)", cp) is not None
       and ordered(cp, "revert.account:", "void kernel(K$SHARED.READ,  stk.shared.read)", "void kernel(K$SHARED.WRITE, stk.shared.write)", "void kernel(K$SD.ACCOUNTS, stk.sd.accounts)", "void kernel(K$NET, stk.net)",
                   "'logto revert account='"), "")
    setters = sorted(n[3:] for n, t in c.items() if n.startswith("bp:") and re.search(r"kernel\(K\$SHARED\.(READ|WRITE),\s*(?!-1\))\S", t))
    lits = sorted(n[3:] for n, t in c.items() if n.startswith("bp:") and re.search(r"kernel\(K\$SHARED\.(READ|WRITE),\s*(1\b|@true)", t))
    askers = sorted(n[3:] for n, t in c.items() if n.startswith("bp:") and re.search(r"kernel\(K\$SHARED\.(READ|WRITE),\s*-1\)", t))
    ck("G2 only LOGIN, CPROC and the API server SET the shared gates; _voc_ref, !shared_ref and list.shared (and CPROC, which holds them) only ASK; and nothing turns a gate on by a literal",
       setters == ["apisrvr", "cproc", "login"] and not lits and set(askers) >= {"_voc_ref", "shared_ref", "listshared", "cproc", "tool_mygates"} and set(askers) <= {"_voc_ref", "shared_ref", "listshared", "cproc", "tool_mygates"},      # tool_mygates (24 Oct 26): the account holder's gate page only asks
       repr(setters) + repr(lits) + repr(askers))
    ai = B("acc_os_info")
    mo = B("modifya")
    ck("G3 the manifest carries shared.read ('not no': 1 unless the field says no) and shared.write (1 only for yes) for a USER account, after net: and before the GROUP branch",
       ordered(ai, "'net: '", "'shared.read: '", "'shared.write: '", "case grp[1,4] = 'sdg_'")
       and re.search(r"info<-1> = 'shared\.read: ':\(if " + rd % r"acc\.rec" + r" then 1 else 0\)", ai) is not None
       and re.search(r"info<-1> = 'shared\.write: ':\(if upcase\(trim\(acc\.rec<ACC\$SHARED\.WRITE>\)\) = 'YES' then 1 else 0\)", ai) is not None, "")
    rs = B("restorea")
    ck("G4 restorea: m.shared.read and m.shared.write start empty, are read from the manifest keys, and only an explicit 0 withdraws read and only an explicit 1 grants write (a manifest without the keys, "
       "an older one or Solo's: read on, write off)",
       "m.shared.read = '' ; m.shared.write = ''" in rs and "case sec.keys<s.idx,kp> = 'shared.read'  ; m.shared.read = kv" in rs and "case sec.keys<s.idx,kp> = 'shared.write' ; m.shared.write = kv" in rs
       and "settings<CA$SHARED.READ.OFF> = (if m.shared.read = '0' then 1 else '')" in rs and "settings<CA$SHARED.WRITE> = (if m.shared.write = '1' then 1 else '')" in rs, "")
    ca2, cr = B("create_account"), B("createa")
    ck("G5 create_account: a setting is a request only when it is exactly 1; a USER account is written explicitly ('no' for read only on request, else 'yes'; write 'yes' only on request, else 'no'); any other type is "
       "written only when asked (blank stays the default); the USER report line 11515 follows 11411 and comes before 11482",
       "shared.read.off = (settings<CA$SHARED.READ.OFF> = 1)" in ca2 and "shared.write.want = (settings<CA$SHARED.WRITE> = 1)" in ca2
       and "acc.rec<ACC$SHARED.READ> = if shared.read.off then 'no' else 'yes'" in ca2 and "acc.rec<ACC$SHARED.WRITE> = if shared.write.want then 'yes' else 'no'" in ca2
       and "if shared.read.off then acc.rec<ACC$SHARED.READ> = 'no'" in ca2 and "if shared.write.want then acc.rec<ACC$SHARED.WRITE> = 'yes'" in ca2
       and ordered(ca2, "crt sysmsg(11411,", "crt sysmsg(11515, acc.name, acc.rec<ACC$SHARED.READ>, acc.rec<ACC$SHARED.WRITE>)", "crt sysmsg(11482,"), "")
    rb = between(ca2, "acc.shared = (downcase(trim(acc.name)) = 'shared')", "acc.uname = ''")
    ck("G6 create_account: THE NAME shared IS RESERVED, refused for every type before ANY Linux user or group is made (right after the type is folded, before create_user); the one way through is a GROUP from "
       "an -internal session with the installer's one-shot marker, which is DELETED at once; otherwise -ER$ARGS and message 11516",
       ordered(ca2, "acc.type = upcase(trim(acc.type))", "acc.shared = (downcase(trim(acc.name)) = 'shared')", "shared.marker = @sdsys:@ds:'$shared.make'",
               "acc.type = 'GROUP' and kernel(K$INTERNAL, -1) and ospath(shared.marker, OS$EXISTS)", "void ospath(shared.marker, OS$DELETE)", "err = 11516", "return", "acc.uname = ''", "create_user(acc.uname)")
       and "-ER$ARGS" in rb, "")
    ck("G6b ...set.owner gives the shared directory the group sdusers (every SD user's own process must read the DH files through the kernel) while the register keeps sdg_shared as the account's group "
       "(only SDSYS, root and members of sdg_shared may sign on to shared)",
       re.search(r"gid\s*=\s*group_name\s*\n\s*if acc\.name = 'shared' then gid = 'sdusers'", ca2) is not None and "acc.rec<ACC$GROUP> = group_name" in ca2, "")
    ck("G7 createa: the syntax line puts {shared-read-off} {shared-write-on} between {dict-on} and {net-on} (so the {net-on} {files-on} {no.query} tail still matches), and ONLY those two words are "
       "taken (SHARED-READ-OFF sets CA$SHARED.READ.OFF, SHARED-WRITE-ON sets CA$SHARED.WRITE): the other two restate the default",
       "{dict-on} {shared-read-off} {shared-write-on} {net-on} {files-on} {files-write-on} {files-admin-on} {ai-on} {start-menu | start-terminal} {pins-on} {no.query}" in cr
       and re.search(r"case upcase\(token\) = 'SHARED-READ-OFF'\s*\n\s*settings<CA\$SHARED\.READ\.OFF> = 1\s*\n\s*case upcase\(token\) = 'SHARED-WRITE-ON'\s*\n\s*settings<CA\$SHARED\.WRITE> = 1", cr) is not None
       and "SHARED-READ-ON" not in cr and "SHARED-WRITE-OFF" not in cr, "")
    cases_ok = all(re.search(r"case action = '%s'\s*\n\s*os\.field = %s ; os\.want = @%s\s*\n\s*gosub os\.set\s*\n\s*return" % (w, f, b), mo)
                   for w, f, b in (("SHARED-READ-ON", "ACC\\$SHARED\\.READ", "true"), ("SHARED-READ-OFF", "ACC\\$SHARED\\.READ", "false"),
                                   ("SHARED-WRITE-ON", "ACC\\$SHARED\\.WRITE", "true"), ("SHARED-WRITE-OFF", "ACC\\$SHARED\\.WRITE", "false")))
    ck("G8 modifya has the four words, each through os.set with its own field; the syntax line and the 'Action Must Be' list name them on lines of their own (net-on, net-off stays intact); and nothing "
       "is refused for the account named shared (the words on THAT account decide what the members of its group can do inside it)",
       cases_ok and "modify.account <account> shared-read-on | shared-read-off | shared-write-on | shared-write-off" in mo and "shared-read-on, shared-read-off, shared-write-on, shared-write-off," in mo
       and "net-on, net-off," in mo and "'shared'" not in mo, "")
    osw = mo[at(mo, "os.set:"):]
    ck("G8b modifya os.set: both fields are let through on a group account; and os.was is 'not no' for read (a BLANK field is ON, so shared-read-off on a blank record must WRITE 'no' instead of saying "
       "'already') and 'yes' for every other field; the values written are yes / no",
       "os.field # ACC$SHARED.READ and os.field # ACC$SHARED.WRITE" in osw[:osw.find("return")]
       and re.search(r"if os\.field = ACC\$SHARED\.READ then\s*\n\s*os\.was = \(upcase\(trim\(acc\.rec<os\.field>\)\) # 'NO'\)\s*\n\s*end else\s*\n\s*os\.was = \(upcase\(trim\(acc\.rec<os\.field>\)\) = 'YES'\)\s*\n\s*end", mo) is not None
       and "if os.want then acc.new<os.field> = 'yes' else acc.new<os.field> = 'no'" in mo, "")
    ck("G8c ...the report for the two fields prints both states with 11515, read now 'no' only when the field says NO and write now 'yes' only when it says YES, after the audit line",
       ordered(mo, "void kernel(K$AUDIT, 'modify.account ' : downcase(action)", "if os.field = ACC$SHARED.READ or os.field = ACC$SHARED.WRITE then", "sh.read.now = 'yes'",
               "if upcase(trim(acc.new<ACC$SHARED.READ>)) = 'NO' then sh.read.now = 'no'", "sh.write.now = 'no'", "if upcase(trim(acc.new<ACC$SHARED.WRITE>)) = 'YES' then sh.write.now = 'yes'",
               "crt sysmsg(11515, acc.name, sh.read.now, sh.write.now)"), "")
    da = B("delacc")
    ck("G9 delacc refuses the account named shared (11517) after the sdsys refusal and BEFORE the own-account test, the register read, any prompt and any removal",
       ordered(da, "stop sysmsg(6025)", "if acc.name = 'shared' then", "stop sysmsg(11517)", "if acc.name = @who then", "stop sysmsg(6026)")
       and ordered(da, "acc.name = downcase(acc.name)", "stop sysmsg(11517)", "openpath @sdsys:@ds:'accounts' to acc.f else", "readu acc.rec from acc.f, acc.name locked", "input yn", "delete acc.f, acc.name"), "")

    # ---- I. the installer and the remover ----------------------------------------------------------------------------------------
    ins = c["sh:installsdcore.sh"]
    pre = sh_func(ins, "shared_preflight")
    ck("I1 installsdcore.sh defines shared_preflight (closing brace at column 0): for each of /home/sd/accounts/shared and ${sdsysdir}/accounts/shared that exists it reads line 1 and line 3 and the account "
       "is 'ours' only when line 1 is /home/sd/group_accounts/shared AND line 3 is sdg_shared; anything else prints, names the register file, says nothing was changed and returns 1",
       pre != "" and '"/home/sd/accounts/shared" "${sdsysdir}/accounts/shared"' in pre and "sudo test -f" in pre and "sed -n '1p'" in pre and "sed -n '3p'" in pre
       and '[ "$line1" = "/home/sd/group_accounts/shared" ] && [ "$line3" = "sdg_shared" ]' in pre and "Nothing has been changed." in pre and "Its register record is:  $reg" in pre
       and ordered(pre, "continue", "return 1", "return 0"), "")
    i_sudo = ins.find("if ! sudo -v; then")
    i_fi = ins.find("\nfi\n", i_sudo)
    i_call = ins.find("if ! shared_preflight; then")
    i_apt = ins.find("sudo apt-get")
    i_dnf = ins.find("sudo dnf")
    ck("I2 the preflight is CALLED right after the sudo -v check's closing fi, before the first package install (apt-get or dnf) or any other change to the machine, and the caller exits (it needs "
       "sudo, which is warm by then)",
       0 <= i_sudo < i_fi < i_call < min(p for p in (i_apt, i_dnf) if p >= 0) and re.search(r"if ! shared_preflight; then\s*exit 1\s*fi", ins) is not None and ins.find("shared_preflight() {") < i_call, "")
    rawblk = strip_sh(between(srcs["sh:installsdcore.sh"], "# SHARED-CREATE-BEGIN", "# SHARED-CREATE-END"))
    ck("I3 the creation block sits AFTER the installing user's account block and BEFORE the accounts_kept test (so UPDATE.ACCOUNTS ALL brings shared's VOC forward in an upgrade); a registered account "
       "is kept and bin/sd is not run, a directory without a register is a warning that touches nothing, otherwise the one-shot marker is made, bin/sd -internal create-account GROUP shared is run "
       "with a failure tolerated (|| shared_rc=$?), and the marker is removed WHATEVER happened (not under an if, not behind &&)",
       ordered(srcs["sh:installsdcore.sh"], '${tuser_lc}', "# SHARED-CREATE-BEGIN", "# SHARED-CREATE-END", 'if [ "$accounts_kept" = yes ]; then')
       and ordered(rawblk, 'if sudo test -f "$shared_reg"; then', "is already registered and is kept", "elif sudo test -d", "WARNING:", 'sudo touch "$shared_marker"',
                   "sudo bin/sd -internal create-account GROUP shared || shared_rc=$?", 'sudo rm -f "$shared_marker"')
       and re.search(r'^    sudo rm -f "\$shared_marker"$', rawblk, re.M) is not None and "shared_marker=\"${sdsysdir}/\\$shared.make\"" in rawblk, "")
    ck("I3b ...afterwards it says what the system ACTUALLY holds (register lines 1 and 3, the directory's group and mode, the members of sdg_shared), prints a WARNING for a group other than sdg_shared, "
       "a directory that is not 'sdusers 2775', members besides root and sdsys and a missing register, each of which sets shared_ok=no, and the success line "
       "'Registered shared as a group account (group: sdg_shared)' appears ONLY behind shared_ok = yes",
       ordered(rawblk, "sed -n '1p'", "sed -n '3p'", "stat -c '%G %a'", "getent group sdg_shared", "WARNING: the shared account was not registered", "WARNING: shared was registered with group",
               "WARNING: the shared directory is", "WARNING: sdg_shared has members besides root and sdsys", 'if [ "$shared_ok" = yes ]; then', "Registered shared as a group account (group: sdg_shared).")
       and rawblk.count("Registered shared as a group account") == 1 and rawblk.count("shared_ok=no") >= 5 and '[ "$shared_stat" != "sdusers 2775" ]' in rawblk and '[ "$shared_line3" != "sdg_shared" ]' in rawblk
       and re.search(r'elif \[ -n "\$shared_extra" \]; then\s*shared_ok=no\s*printf[^\n]*\n\s*echo "WARNING: sdg_shared has members besides root and sdsys', rawblk) is not None
       and re.search(r'if \[ -z "\$shared_members" \]; then\s*shared_ok=no\s*printf[^\n]*\n\s*echo "WARNING: the group sdg_shared does not exist or has no members', rawblk) is not None, "")
    dl = c["sh:deletesdcore.sh"]
    gi = dl.find("groupdel sdg_shared")
    ck("I4 deletesdcore.sh removes the group sdg_shared once, in the DELETE path (after the orphan sdsys group, before the accounts-saved else) and not in the keep-accounts path",
       dl.count("groupdel sdg_shared") == 1 and 0 <= dl.find("Removed orphan sdsys group.") < gi < dl.find("sd ACCOUNTS were saved", gi)
       and dl.rfind('if [ "$keep_accts" = "DELETE" ]; then', 0, gi) > dl.find("# remove sdsys user and sdusers group only if deleting ACCOUNTS") and "getent group sdg_shared" in dl, "")
    ck("I5 the marker's name is the same in the installer and in create_account: $shared.make in the sdsys directory",
       "${sdsysdir}/\\$shared.make" in rawblk and "@sdsys:@ds:'$shared.make'" in ca2, "")

    # ---- R. the suite is wired in ---------------------------------------------------------------------------------------------------
    rg_ = c["txt:regress.sh"]
    am = re.search(r'^ALL_SUITES="([^"]*)"', rg_, re.M)
    mp = c["txt:regress-map.txt"]
    ck("R1 regress.sh lists the suite 'shared' in ALL_SUITES and regress-map.txt has a rule for each new file of this feature (the new programs, the verb, the three test files)",
       am is not None and "shared" in am.group(1).split()
       and all(re.search(r"^%s\s*:" % re.escape(p), mp, re.M) for p in ("sdsys/gpl.bp/shared_ref", "sdsys/gpl.bp/edit_msg", "sdsys/gpl.bp/listshared", "sdsys/voc_template/list.shared")), "")
    ck("R2 the three test files exist (this one, the installer test and the sandbox suite)", all(srcs.get("file:" + t) for t in ("sandbox-shared.py", "test-shared-units.py", "test-install-shared.sh")), "")
    return rows


def mutate(srcs, name, a, b, count=1):
    """A copy of SRCS with a change made to one file.  A is an exact string (or a compiled regex), B the replacement (or a replacement for the regex).
    A change that finds nothing, or changes nothing, is an error: a mutant that does not apply tests nothing."""
    s = dict(srcs)
    if name not in s or s[name] is None:
        raise KeyError("no such source: %s" % name)
    old = s[name]
    if isinstance(a, re.Pattern):
        new = a.sub(b, old, count=count)
    elif callable(a):
        new = a(old)
    else:
        if a not in old:
            raise KeyError("mutant text not in %s: %r" % (name, a[:80]))
        new = old.replace(a, b, count)
    if new == old:
        raise KeyError("the mutation changed nothing in %s" % name)
    s[name] = new
    return s


def X(pattern, flags=0):
    return re.compile(pattern, flags)


# (label, source, old, new)   -   old is an exact string or X(regex); new its replacement
MUTANTS = [
    # ---- numbers ----
    ("K_SHARED_ONCE shares a number with another key", "c:keys.h", "#define K_SHARED_ONCE        131", "#define K_SHARED_ONCE        127"),
    ("K$SHARED.REF disagrees with the C number", "bp:int$keys.h", "$define K$SHARED.REF      130", "$define K$SHARED.REF      140"),
    ("ACC$SHARED.WRITE takes the field of ACC$NET", "sys:keys.h", "$define ACC$SHARED.WRITE 14", "$define ACC$SHARED.WRITE 15"),
    ("UG_SHARED_WRITE is two bits", "c:sysseg.h", "#define UG_SHARED_WRITE 0x0020", "#define UG_SHARED_WRITE 0x0030"),
    ("CA$SHARED.READ.OFF leaves the Linux block", "sys:createacc.h", "$define CA$SHARED.READ.OFF 37", "$define CA$SHARED.READ.OFF 44"),
    ("EDIT_SHARED_STRUCT is the program kind", "c:sd.h", "#define EDIT_SHARED_STRUCT 5", "#define EDIT_SHARED_STRUCT 3"),
    ("message 11514 loses its words", "msg:11514", "can only be changed by SDSYS", "can be changed by anyone"),
    ("message 11520 is deleted", "msg:11520", X(r"(?s).*"), ""),
    ("a program cites 11513 that is not !edit_msg", "bp:edit_guard", "   kind = kernel(K$EDIT.KIND, p)\n   display edit_msg(kind)", "   kind = kernel(K$EDIT.KIND, p)\n   display sysmsg(11513)"),
    ("a kernel refusal says 11514 as a number", "c:dh_ak.c", "k_error(sysmsg(edit_refused_message(EDIT_SHARED_STRUCT)));\n  if (fvar->type != DYNAMIC_FILE)", "k_error(sysmsg(11514));\n  if (fvar->type != DYNAMIC_FILE)"),
    # ---- the root ----
    ("a miss is final (never retried)", "c:op_sh.c", "((now - last_try) < SHARED_RETRY_SECONDS)", "1"),
    ("a miss is retried at every call", "c:op_sh.c", "  last_try = now;\n", ""),
    ("the hit is never kept", "c:op_sh.c", "  strcpy(root, resolved);\n  have = TRUE;", "  strcpy(root, resolved);"),
    ("the hit is kept before the path is resolved", "c:op_sh.c", "  if (realpath(line1, resolved) == NULL)\n    return FALSE;", "  have = TRUE;\n  if (realpath(line1, resolved) == NULL)\n    return FALSE;"),
    ("a suspended shared account is not protected", "c:op_sh.c", "  body[got] = '\\0';\n  if ((p = strchr(body, '\\n')) != NULL)", "  body[got] = '\\0';\n  if (strstr(body, \"SUSPENDED\") != NULL)\n    return FALSE;\n  if ((p = strchr(body, '\\n')) != NULL)"),
    ("a root of length one is accepted", "c:op_sh.c", "  if (n <= 1)\n    return FALSE;\n\n  strcpy(root, resolved);", "  if (n <= 0)\n    return FALSE;\n\n  strcpy(root, resolved);"),
    ("a relative line 1 is accepted", "c:op_sh.c", "if ((body[0] != '/') || (n > PATH_MAX))", "if (n > PATH_MAX)"),
    ("the boundary after the root is not tested", "c:op_sh.c", "((canon[len] == '\\0') || (canon[len] == '/'))", "1"),
    ("an unresolvable name is taken as outside shared", "c:op_sh.c", "!resolve_name(cwd, name, resolved))\n    return TRUE;", "!resolve_name(cwd, name, resolved))\n    return FALSE;"),
    ("shared.write is the read bit", "c:op_sh.c", "MY_GATE(UG_SHARED_WRITE)", "MY_GATE(UG_SHARED_READ)"),
    ("the S.64 kind is asked before shared.write (canon)", "c:op_sh.c",
     "  if (path_in_shared(canon) && !shared_write_ok())\n    return EDIT_SHARED_WRITE;\n  kind = edit_kind_of_path(canon);\n  if ((kind != EDIT_NONE) && !edit_permitted(kind))\n    return kind;\n  return EDIT_NONE;",
     "  kind = edit_kind_of_path(canon);\n  if ((kind != EDIT_NONE) && !edit_permitted(kind))\n    return kind;\n  if (path_in_shared(canon) && !shared_write_ok())\n    return EDIT_SHARED_WRITE;\n  return EDIT_NONE;"),
    ("the S.64 kind is asked before shared.write (name)", "c:op_sh.c",
     "  if (path_resolved_in_shared(name) && !shared_write_ok())\n    return EDIT_SHARED_WRITE;\n  kind = edit_kind_of_path(name);\n  if ((kind != EDIT_NONE) && !edit_permitted(kind))\n    return kind;\n  return EDIT_NONE;",
     "  kind = edit_kind_of_path(name);\n  if ((kind != EDIT_NONE) && !edit_permitted(kind))\n    return kind;\n  if (path_resolved_in_shared(name) && !shared_write_ok())\n    return EDIT_SHARED_WRITE;\n  return EDIT_NONE;"),
    ("the administrator is asked after the shared test (canon)", "c:op_sh.c", "  if (MY_ADMIN())\n    return EDIT_NONE;\n  if (path_in_shared(canon)", "  if (path_in_shared(canon)"),
    ("edit_ok_for_path forgets shared", "c:op_sh.c", "return edit_refusal_for_name(path) == EDIT_NONE;", "return edit_kind_of_path(path) == EDIT_NONE || edit_permitted(edit_kind_of_path(path));"),
    ("11513 says the program message", "c:op_sh.c", "    case EDIT_SHARED_WRITE:\n      return 11513;", "    case EDIT_SHARED_WRITE:\n      return 11405;"),
    ("shared_ref_ok accepts the root itself", "c:op_sh.c", " || (resolved[root_len + 1] == '\\0'))", ")"),
    ("shared_ref_ok accepts a dictionary as a data file", "c:op_sh.c", "if ((fno == 3) && is_last) {", "if (is_last) {"),
    ("shared_ref_ok forgets the private catalogue", "c:op_sh.c", "    if ((cat_last != NULL) && (cat_n == n) && (strncasecmp(comp, cat_last, n) == 0))\n      return FALSE;\n", ""),
    ("shared_ref_ok accepts any fno", "c:op_sh.c", "  if ((fno != 2) && (fno != 3))\n    return FALSE;\n", ""),
    ("shared_ref_ok does not resolve links", "c:op_sh.c", "  if (realpath(path, resolved) == NULL)\n    return FALSE;\n  root_len", "  strcpy(resolved, path);\n  root_len"),
    ("shared_ref_ok lets a VOC component through", "c:op_sh.c", "    } else if (kind != EDIT_NONE) {\n      return FALSE;\n    }", "    }"),
    ("shared_once is case blind no longer", "c:op_sh.c", "strcasecmp(seen[i], key) == 0", "strcmp(seen[i], key) == 0"),
    ("shared_once answers FALSE when full", "c:op_sh.c", "  if (count >= 64)\n    return TRUE;", "  if (count >= 64)\n    return FALSE;"),
    # ---- the kernel keys ----
    ("K_SHARED sets from a user program", "c:op_kernel.c", "        if (process.program.flags & HDR_INTERNAL)\n          SET_MY_GATE(shared_bit, n > 0);", "        if (1)\n          SET_MY_GATE(shared_bit, n > 0);"),
    ("K_SHARED_READ also sets the NET bit", "c:op_kernel.c", "SET_MY_GATE(shared_bit, n > 0);", "SET_MY_GATE(shared_bit | UG_NET, n > 0);"),
    ("K_SHARED closes the NET connections", "c:op_kernel.c", "      result.data.value = MY_GATE(shared_bit);", "      net_close_all();\n      result.data.value = MY_GATE(shared_bit);"),
    ("a K_SHARED case between K_NET and K_EDIT_OK", "c:op_kernel.c", "    case K_EDIT_OK:\n    case K_EDIT_KIND: {", "    case K_SHARED_ONCE: break;\n    case K_EDIT_OK:\n    case K_EDIT_KIND: {"),
    ("K_EDIT_KIND answers the raw kind after a refusal", "c:op_kernel.c", "        result.data.value = edit_refusal_for_name(edit_name);\n        if (result.data.value == EDIT_NONE)\n          result.data.value = edit_kind_of_path(edit_name);", "        result.data.value = edit_kind_of_path(edit_name);"),
    ("K_SHARED_REF always accepts", "c:op_kernel.c", "shared_ref_ok(shared_buf, atoi(shared_fno), shared_cat) ? 1 : 0", "1"),
    ("K_SHARED_ONCE always answers 1", "c:op_kernel.c", "result.data.value = shared_once(shared_name) ? 1 : 0;", "result.data.value = 1;"),
    # ---- the record rule and the structure sites ----
    ("edit_refusal forgets that a $internal program passes", "c:op_dio3.c", "  if (process.program.flags & HDR_INTERNAL)\n    return EDIT_NONE;\n  if (MY_ADMIN())\n    return EDIT_NONE;\n\n  /* The file table is shared memory", "  if (MY_ADMIN())\n    return EDIT_NONE;\n\n  /* The file table is shared memory"),
    ("edit_refusal forgets shared (asks only the S.64 kind)", "c:op_dio3.c", "kind = edit_refusal_for_canon(path);", "kind = edit_kind_of_path(path);"),
    ("shared_structure_refusal exempts a $internal program", "c:op_dio3.c", "  if (MY_ADMIN())\n    return EDIT_NONE;\n  if (path_in_shared((const char *)FPtr(fvar->file_id)->pathname))", "  if (MY_ADMIN() || (process.program.flags & HDR_INTERNAL))\n    return EDIT_NONE;\n  if (path_in_shared((const char *)FPtr(fvar->file_id)->pathname))"),
    ("shared_structure_refusal never refuses", "c:op_dio3.c", "    return EDIT_SHARED_STRUCT;\n  return EDIT_NONE;\n}\n\n/* ======================================================================\n   refuse_net_file()", "    return EDIT_NONE;\n  return EDIT_NONE;\n}\n\n/* ======================================================================\n   refuse_net_file()"),
    ("CLEARFILE of a shared file is not asked", "c:op_dio3.c", "  if (shared_structure_refusal(fvar) != EDIT_NONE) {\n    if (!(op_flags & P_ON_ERROR))\n      k_error(sysmsg(EDIT_REFUSED_MSG(EDIT_SHARED_STRUCT)));", "  if (0) {\n    if (!(op_flags & P_ON_ERROR))\n      k_error(sysmsg(EDIT_REFUSED_MSG(EDIT_SHARED_STRUCT)));"),
    ("CLEARFILE of a shared file says the program message", "c:op_dio3.c", "k_error(sysmsg(EDIT_REFUSED_MSG(EDIT_SHARED_STRUCT)));\n    process.status = -ER_PERM;", "k_error(sysmsg(EDIT_REFUSED_MSG(EDIT_PROG)));\n    process.status = -ER_PERM;"),
    ("CONFIGURE.FILE is not asked", "c:op_dio1.c", "  if (shared_structure_refusal(fvar) != EDIT_NONE)\n    k_error(sysmsg(edit_refused_message(EDIT_SHARED_STRUCT)));\n\n  if (fvar->flags & FV_RDONLY)\n    k_error(sysmsg(1400));", "  if (fvar->flags & FV_RDONLY)\n    k_error(sysmsg(1400));"),
    ("CLEAR.AK is not asked", "c:dh_ak.c", "  if (shared_structure_refusal(fvar) != EDIT_NONE)\n    k_error(sysmsg(edit_refused_message(EDIT_SHARED_STRUCT)));\n  if (fvar->type != DYNAMIC_FILE)", "  if (fvar->type != DYNAMIC_FILE)"),
    ("AKENABLE is not asked", "c:dh_ak.c", "  if (shared_structure_refusal(fvar) != EDIT_NONE)\n    k_error(sysmsg(edit_refused_message(EDIT_SHARED_STRUCT)));\n\n  if (fvar->type == DYNAMIC_FILE && akno < MAX_INDICES) {", "  if (fvar->type == DYNAMIC_FILE && akno < MAX_INDICES) {"),
    ("CREATE.AK forgets the index path", "c:dh_ak.c", "(path_resolved_in_shared(data_path) || path_resolved_in_shared(ak_path))", "(path_resolved_in_shared(data_path))"),
    ("CREATE.AK asks after it has made the index", "c:dh_ak.c", "  if (!MY_ADMIN() && (path_resolved_in_shared(data_path) || path_resolved_in_shared(ak_path)))\n    k_error(sysmsg(edit_refused_message(EDIT_SHARED_STRUCT)));\n\n  if (create_ak(data_path, ak_path, ak_name, fno, flags, dict_rec, collation_map_name, collation_map) == 0) {", "  if (create_ak(data_path, ak_path, ak_name, fno, flags, dict_rec, collation_map_name, collation_map) == 0) {"),
    ("DELETE.AK is not asked", "c:dh_ak.c", "  if (!MY_ADMIN() && path_resolved_in_shared(pathname))\n    k_error(sysmsg(edit_refused_message(EDIT_SHARED_STRUCT)));\n\n  if (!delete_ak(pathname, akno)) {", "  if (!delete_ak(pathname, akno)) {"),
    ("AKWRITE is refused too (index maintenance would break)", "c:dh_ak.c", "void op_akwrite() {", "void op_akwrite() {\n  if (!MY_ADMIN() && path_resolved_in_shared(\"x\"))\n    return;"),
    ("AKDELETE is refused too", "c:dh_ak.c", "void op_akdelete() {", "void op_akdelete() {\n  if (shared_structure_refusal(NULL) != EDIT_NONE)\n    return;"),
    ("FCONTROL FC_SET_MODE is not asked", "c:dh_misc.c", "    case FC_NO_RESIZE:\n    case FC_SET_MODE:\n      if (shared_structure_refusal(fvar)", "    case FC_NO_RESIZE:\n      if (shared_structure_refusal(fvar)"),
    ("FCONTROL asks the sequential key too", "c:dh_misc.c", "    case FC_SET_JNL_FNO:\n    case FC_KILL_JNL:\n    case FC_SET_AKPATH:", "    case FC_SET_SEQ_KEY:\n    case FC_SET_JNL_FNO:\n    case FC_KILL_JNL:\n    case FC_SET_AKPATH:"),
    ("FCONTROL() FC$MINMOD is not asked", "c:dh_misc.c", "(action == 1) || (action == 4) || (action == 7)", "(action == 1) || (action == 4)"),
    ("FCONTROL() refuses a query too", "c:dh_misc.c", "    if (descr->data.value != -1)\n      k_error(sysmsg(edit_refused_message(EDIT_SHARED_STRUCT)));", "    k_error(sysmsg(edit_refused_message(EDIT_SHARED_STRUCT)));"),
    ("SET.TRIGGER is not asked", "c:dh_misc.c", "  if (shared_structure_refusal(fvar) != EDIT_NONE)\n    k_error(sysmsg(edit_refused_message(EDIT_SHARED_STRUCT)));\n\n  /* A directory file has no header", "  /* A directory file has no header"),
    ("OSPATH makes a path in shared", "c:op_dio2.c", "((key == OS_DELETE) || (key == OS_MKDIR) || (key == OS_MKPATH))", "((key == OS_DELETE) || (key == OS_MKDIR))"),
    ("OSPATH refuses OS_CHOWN too", "c:op_dio2.c", "((key == OS_DELETE) || (key == OS_MKDIR) || (key == OS_MKPATH))", "((key == OS_DELETE) || (key == OS_MKDIR) || (key == OS_MKPATH) || (key == OS_CHOWN))"),
    ("OSRENAME forgets the new name", "c:op_dio2.c", "(path_resolved_in_shared(old_path) || path_resolved_in_shared(new_path))", "(path_resolved_in_shared(old_path))"),
    ("create_edit_refusal exempts a $internal program first", "c:op_dio1.c", "  if (!MY_ADMIN() && path_resolved_in_shared(path))\n    return EDIT_SHARED_STRUCT;\n  if (process.program.flags & HDR_INTERNAL)\n    return EDIT_NONE;", "  if (process.program.flags & HDR_INTERNAL)\n    return EDIT_NONE;\n  if (!MY_ADMIN() && path_resolved_in_shared(path))\n    return EDIT_SHARED_STRUCT;"),
    ("CREATE.FILE prints the old sum", "c:op_dio1.c", "k_error(sysmsg(edit_refused_message(edit_kind))); /* 11405", "k_error(sysmsg(11404 + edit_kind)); /* 11405"),
    ("the wrapper follows shared", "c:op_dio1.c", "return get_voc_file_reference_ex(voc_name, get_dict_name, path, vflags, FALSE);", "return get_voc_file_reference_ex(voc_name, get_dict_name, path, vflags, TRUE);"),
    ("open_file never follows shared", "c:op_dio1.c", "get_voc_file_reference_ex(voc_name, open_dict, mapped_name, vflags, TRUE)", "get_voc_file_reference_ex(voc_name, open_dict, mapped_name, vflags, FALSE)"),
    ("_voc_ref is given four arguments", "c:op_dio1.c", "k_recurse(pcode_voc_ref, 5); /*", "k_recurse(pcode_voc_ref, 4); /*"),
    ("the fifth argument is not pushed", "c:op_dio1.c", "  (e_stack++)->data.value = allow_shared;", "  (e_stack++)->data.value = 0;"),
    ("OPENSEQ follows shared", "c:op_seqio.c", "get_voc_file_reference(file_name, FALSE, file_name, vflags)", "get_voc_file_reference_ex(file_name, FALSE, file_name, vflags, TRUE)"),
    # ---- the BASIC lookup ----
    ("_voc_ref follows shared for every caller", "bp:_voc_ref", "if allow.shared and component = '' and not(vr.admin) then", "if component = '' and not(vr.admin) then"),
    ("_voc_ref follows shared for the administrator", "bp:_voc_ref", "if allow.shared and component = '' and not(vr.admin) then", "if allow.shared and component = '' then"),
    ("_voc_ref follows shared for name,component", "bp:_voc_ref", "if allow.shared and component = '' and not(vr.admin) then", "if allow.shared and not(vr.admin) then"),
    ("_voc_ref does not ask the session's gate", "bp:_voc_ref", "         if kernel(K$SHARED.READ, -1) then\n            shared.ans", "         if @true then\n            shared.ans"),
    ("_voc_ref takes the vflags nowhere", "bp:_voc_ref", "               vflags = shared.ans<2>\n", ""),
    ("_voc_ref has no fifth argument", "bp:_voc_ref", "subroutine voc_ref(filename, is.dict, pathname, vflags, allow.shared)", "subroutine voc_ref(filename, is.dict, pathname, vflags)"),
    ("shared_ref forgets the administrator", "bp:shared_ref", "      if kernel(K$ADMINISTRATOR, -1) then return ''\n", ""),
    ("shared_ref forgets the session's gate", "bp:shared_ref", "      if not(kernel(K$SHARED.READ, -1)) then return ''\n", ""),
    ("shared_ref: quiet skips nothing (a lookup is always tested, list.shared would be refused)", "bp:shared_ref", "   if not(quiet) then\n      if kernel(K$ADMINISTRATOR, -1) then return ''", "   if 1 then\n      if kernel(K$ADMINISTRATOR, -1) then return ''"),
    ("shared_ref: quiet skips the kernel's acceptance too", "bp:shared_ref", "   if not(kernel(K$SHARED.REF, p : @fm : fno : @fm : catname)) then return ''", "   if not(quiet) and not(kernel(K$SHARED.REF, p : @fm : fno : @fm : catname)) then return ''"),
    ("shared_ref accepts fno 1", "bp:shared_ref", "   if fno # 2 and fno # 3 then return ''\n", ""),
    ("shared_ref lets a name begin with an underscore", "bp:shared_ref", "index(letters : digits, lname[1,1], 1) = 0", "index(letters : digits : '_$&', lname[1,1], 1) = 0"),
    ("shared_ref lets a name hold a colon", "bp:shared_ref", "index(letters : digits : '._-$', lname[ch,1], 1) = 0", "index(letters : digits : '._-$:,', lname[ch,1], 1) = 0"),
    ("shared_ref looks up a stock name", "bp:shared_ref", "   read stock.rec from stock.f, lname then\n      close stock.f\n      return ''\n   end", "   read stock.rec from stock.f, lname then\n      close stock.f\n   end"),
    ("shared_ref ignores a suspended account", "bp:shared_ref", "   if upcase(trim(acc.rec<ACC$SUSPENDED>)) = 'SUSPENDED' then return ''\n", ""),
    ("shared_ref accepts a relative path for the account", "bp:shared_ref", "   if spath[1,1] # @ds then return ''\n", ""),
    ("shared_ref accepts any VOC type", "bp:shared_ref", "   if upcase(rec[1,1]) # 'F' then return ''\n", ""),
    ("shared_ref accepts a multifile", "bp:shared_ref", "   if rec<4> # '' then return ''           ;* a multifile\n", ""),
    ("shared_ref expands tokens", "bp:shared_ref", "   if p[1,1] = '@' then return ''          ;* no token expansion\n", ""),
    ("shared_ref forgets the kernel's acceptance", "bp:shared_ref", "   if not(kernel(K$SHARED.REF, p : @fm : fno : @fm : catname)) then return ''\n", ""),
    ("shared_ref audits every open", "bp:shared_ref", "      if kernel(K$SHARED.ONCE, lname) then", "      if @true then"),
    ("shared_ref audits before the acceptance", "bp:shared_ref", "   if not(kernel(K$SHARED.REF, p : @fm : fno : @fm : catname)) then return ''\n", "   void kernel(K$AUDIT, 'shared open file=' : lname)\n   if not(kernel(K$SHARED.REF, p : @fm : fno : @fm : catname)) then return ''\n"),
    ("shared_ref audits in upper case", "bp:shared_ref", "'shared open file=' : lname", "'SHARED OPEN file=' : lname"),
    ("shared_ref opens the file by name", "bp:shared_ref", "   openpath spath:@ds:'voc' to svoc else return ''", "   open 'voc' to svoc else return ''"),
    ("shared_ref leaves the VOC open", "bp:shared_ref", "   close svoc\n", ""),
    ("edit_msg: kind 4 says the structure message", "bp:edit_msg", "      case kind = 4\n         return sysmsg(11513)", "      case kind = 4\n         return sysmsg(11514)"),
    ("edit_msg: no case for 5", "bp:edit_msg", "      case kind = 5\n         return sysmsg(11514)\n", ""),
    ("cname keeps the old sum", "bp:cname", "stop edit_msg(ek.kind)", "stop sysmsg(11404 + ek.kind)"),
    ("IDE keeps the clamp", "bp:ide", "msg = edit_msg(edit.kind)", "if edit.kind > 3 then edit.kind = 1\n   msg = sysmsg(11404 + edit.kind)"),
    ("the API server keeps the clamp", "bp:apisrvr", "error.msg = edit_msg(ed.kind)", "error.msg = sysmsg(11404 + ed.kind)"),
    ("deletef keeps the old sum", "bp:deletef", "stop edit_msg(ef.kind)", "stop sysmsg(11404 + ef.kind)"),
    ("basic does not ask edit_guard", "bp:basic", "      if not(edit_guard(out.f)) then", "      if 0 then"),
    ("list.shared forgets the gate message", "bp:listshared", "      stop sysmsg(11520, @who) ;* Account %1 has shared.read off", "      stop"),
    ("list.shared applies the administrator test", "bp:listshared", "shared_ref(ids<i>, 2, 1)", "shared_ref(ids<i>, 2, 0)"),
    ("list.shared forgets the suspended account", "bp:listshared", "upcase(trim(acc.rec<ACC$SUSPENDED>)) = 'SUSPENDED' or ", ""),
    ("the list.shared verb points at another program", "voc:list.shared", "$listshared", "$listserver"),
    # ---- the gates: BLANK MEANS ON ----
    ("LOGIN loads read as 'yes' (a blank record is a wall)", "bp:login", "void kernel(K$SHARED.READ,  upcase(trim(acc.rec<ACC$SHARED.READ>)) # 'NO')", "void kernel(K$SHARED.READ,  upcase(trim(acc.rec<ACC$SHARED.READ>)) = 'YES')"),
    ("LOGIN loads write as 'not no' (a blank record may write)", "bp:login", "upcase(trim(acc.rec<ACC$SHARED.WRITE>)) = 'YES')", "upcase(trim(acc.rec<ACC$SHARED.WRITE>)) # 'NO')"),
    ("LOGIN loads the shared gates before K$NET", "bp:login", "   void kernel(K$SHARED.READ,  upcase(trim(acc.rec<ACC$SHARED.READ>)) # 'NO')      ;* blank = ON\n   void kernel(K$SHARED.WRITE, upcase(trim(acc.rec<ACC$SHARED.WRITE>)) = 'YES')\n", ""),
    ("the API server reads read as 'yes'", "bp:apisrvr", "api.shared.read.grant = (upcase(trim(acc.rec<ACC$SHARED.READ>)) # 'NO')", "api.shared.read.grant = (upcase(trim(acc.rec<ACC$SHARED.READ>)) = 'YES')"),
    ("the API server starts read ON", "bp:apisrvr", "api.shared.read.grant = @false    ;*", "api.shared.read.grant = @true    ;*"),
    ("the API server loads the gates at the first entry only", "bp:apisrvr", "void kernel(K$SHARED.READ,  api.shared.read.grant)    ;* 18 Oct 26, S.66: account-scoped like NET, so every entry and every SDLogto loads them\nvoid kernel(K$SHARED.WRITE, api.shared.write.grant)\n", ""),
    ("sdsys over the API does not follow shared", "bp:apisrvr", "   api.shared.read.grant = @true    ;*", "   api.shared.read.grant = @false    ;*"),
    ("sdsys's block sets the gates after the NET line", "bp:apisrvr", "   api.shared.read.grant = @true    ;* 18 Oct 26, S.66: an API session of sdsys follows shared and can write its records (it has no administrator flag, so no structure change)\n   api.shared.write.grant = @true\n   api.net.grant = @true", "   api.net.grant = @true\n   api.shared.read.grant = @true\n   api.shared.write.grant = @true\n"),
    ("LOGTO loads read without the PATH guard (a path-attached account reads)", "bp:cproc", "void kernel(K$SHARED.READ,  (acc.record<ACC$PATH> # '') and (", "void kernel(K$SHARED.READ,  (@true) and ("),
    ("LOGTO does not clear the record first", "bp:cproc", "   acc.record = ''\n   openpath @sdsys:@ds:'accounts' to acc.f then", "   openpath @sdsys:@ds:'accounts' to acc.f then"),
    ("LOGTO does not hold the gates", "bp:cproc", "         stk.shared.read = kernel(K$SHARED.READ, -1)    ;* 18 Oct 26, S.66: the shared-account gates are account-scoped too\n         stk.shared.write = kernel(K$SHARED.WRITE, -1)\n", ""),
    ("revert.account restores the gates after the NET line", "bp:cproc", "   void kernel(K$SHARED.READ,  stk.shared.read)    ;* 18 Oct 26, S.66: before the SD.ACCOUNTS line, so stk.net stays next to the revert audit line\n   void kernel(K$SHARED.WRITE, stk.shared.write)\n   void kernel(K$SD.ACCOUNTS, stk.sd.accounts)\n   void kernel(K$NET, stk.net)", "   void kernel(K$SD.ACCOUNTS, stk.sd.accounts)\n   void kernel(K$NET, stk.net)\n   void kernel(K$SHARED.READ,  stk.shared.read)\n   void kernel(K$SHARED.WRITE, stk.shared.write)"),
    ("the manifest says read is 1 only for yes", "bp:acc_os_info", "upcase(trim(acc.rec<ACC$SHARED.READ>)) # 'NO' then 1 else 0", "upcase(trim(acc.rec<ACC$SHARED.READ>)) = 'YES' then 1 else 0"),
    ("the manifest drops shared.write", "bp:acc_os_info", "         info<-1> = 'shared.write: ':(if upcase(trim(acc.rec<ACC$SHARED.WRITE>)) = 'YES' then 1 else 0)\n", ""),
    ("restorea withdraws read from a manifest that has no key", "bp:restorea", "(if m.shared.read = '0' then 1 else '')", "(if m.shared.read = '1' then '' else 1)"),
    ("restorea grants write to a manifest that has no key", "bp:restorea", "(if m.shared.write = '1' then 1 else '')", "(if m.shared.write = '0' then '' else 1)"),
    ("modifya: shared-read-off finds a blank record already off", "bp:modifya", "      os.was = (upcase(trim(acc.rec<os.field>)) # 'NO')", "      os.was = (upcase(trim(acc.rec<os.field>)) = 'YES')"),
    ("modifya: a group account cannot carry the shared words", "bp:modifya", " and os.field # ACC$SHARED.READ and os.field # ACC$SHARED.WRITE", ""),
    ("modifya has no SHARED-READ-OFF", "bp:modifya", "      case action = 'SHARED-READ-OFF'", "      case action = 'SHARED-READ-OFFX'"),
    ("modifya refuses the account named shared", "bp:modifya", "os.set:\n", "os.set:\n   if acc.name = 'shared' then return\n"),
    ("modifya reports read as yes unless the field says yes", "bp:modifya", "if upcase(trim(acc.new<ACC$SHARED.READ>)) = 'NO' then sh.read.now = 'no'", "if upcase(trim(acc.new<ACC$SHARED.READ>)) # 'YES' then sh.read.now = 'no'"),
    ("create.account takes shared-read-on too", "bp:createa", "         case upcase(token) = 'SHARED-READ-OFF'", "         case upcase(token) = 'SHARED-READ-ON'\n            null\n         case upcase(token) = 'SHARED-READ-OFF'"),
    ("create.account's syntax puts the words after net-on", "bp:createa", "{dict-on} {shared-read-off} {shared-write-on} {net-on}", "{dict-on} {net-on} {shared-read-off} {shared-write-on}"),
    ("create_account writes a USER's read as blank", "bp:create_account", "     acc.rec<ACC$SHARED.READ> = if shared.read.off then 'no' else 'yes'\n", ""),
    ("create_account asks the setting loosely", "bp:create_account", "shared.write.want = (settings<CA$SHARED.WRITE> = 1)", "shared.write.want = (settings<CA$SHARED.WRITE> # '')"),
    ("create_account's report comes before 11411", "bp:create_account", "     crt sysmsg(11515, acc.name, acc.rec<ACC$SHARED.READ>, acc.rec<ACC$SHARED.WRITE>)  ;* Account %1 has shared.read %2, shared.write %3\n", ""),
    ("the marker is not consumed", "bp:create_account", "         void ospath(shared.marker, OS$DELETE)\n", "         null\n"),
    ("the reserved name is open to a USER", "bp:create_account", "      if acc.type = 'GROUP' and kernel(K$INTERNAL, -1) and ospath(shared.marker, OS$EXISTS) then", "      if kernel(K$INTERNAL, -1) and ospath(shared.marker, OS$EXISTS) then"),
    ("the reserved name is open to a typed session", "bp:create_account", "acc.type = 'GROUP' and kernel(K$INTERNAL, -1) and ospath(shared.marker, OS$EXISTS)", "acc.type = 'GROUP' and ospath(shared.marker, OS$EXISTS)"),
    ("the reserved name needs no marker", "bp:create_account", "acc.type = 'GROUP' and kernel(K$INTERNAL, -1) and ospath(shared.marker, OS$EXISTS)", "acc.type = 'GROUP' and kernel(K$INTERNAL, -1)"),
    ("the reserved name is tested after the Linux user is made", "bp:create_account", "   acc.shared = (downcase(trim(acc.name)) = 'shared')\n   if acc.shared then", "   acc.shared = @false\n   if acc.shared then"),
    ("the shared directory gets its own group", "bp:create_account", "        if acc.name = 'shared' then gid = 'sdusers'", "        null"),
    ("delacc deletes shared", "bp:delacc", "   if acc.name = 'shared' then\n      stop sysmsg(11517) ;* The shared account cannot be deleted\n   end\n", ""),
    ("delacc refuses shared after the own-account test", "bp:delacc", "   if acc.name = 'shared' then\n      stop sysmsg(11517) ;* The shared account cannot be deleted\n   end\n\n   if acc.name = @who then\n      stop sysmsg(6026) ;* Cannot delete own account\n   end", "   if acc.name = @who then\n      stop sysmsg(6026) ;* Cannot delete own account\n   end\n   if acc.name = 'shared' then\n      stop sysmsg(11517) ;* The shared account cannot be deleted\n   end"),
    # ---- the installer and the remover ----
    ("the installer skips the preflight", "sh:installsdcore.sh", "if ! shared_preflight; then\n    exit 1\nfi", "true"),
    ("the preflight is called after the packages", "sh:installsdcore.sh",
     lambda t: t.replace("if ! shared_preflight; then\n    exit 1\nfi\n", "", 1).replace("    if ! sudo apt-get -y install git", "    if ! shared_preflight; then exit 1; fi\n    if ! sudo apt-get -y install git", 1), None),
    ("the preflight lets a foreign account through", "sh:installsdcore.sh", "    printf \"%b\\n\" \"$NC\"\n    return 1\n  done", "    printf \"%b\\n\" \"$NC\"\n    return 0\n  done"),
    ("the preflight forgets line 3", "sh:installsdcore.sh", ' && [ "$line3" = "sdg_shared" ]', ""),
    ("the preflight forgets the live register", "sh:installsdcore.sh", 'for reg in "/home/sd/accounts/shared" "${sdsysdir}/accounts/shared"; do', 'for reg in "/home/sd/accounts/shared"; do'),
    ("the marker is not removed", "sh:installsdcore.sh", '    sudo rm -f "$shared_marker"\n', "    true\n"),
    ("a failed create ends the install", "sh:installsdcore.sh", "sudo bin/sd -internal create-account GROUP shared || shared_rc=$?", "sudo bin/sd -internal create-account GROUP shared"),
    ("the success line is unguarded", "sh:installsdcore.sh", '    if [ "$shared_ok" = yes ]; then', "    if true; then"),
    ("a directory with the wrong mode is not reported", "sh:installsdcore.sh", 'if [ "$shared_stat" != "sdusers 2775" ]; then', "if false; then"),
    ("members besides root and sdsys are not reported", "sh:installsdcore.sh", '        elif [ -n "$shared_extra" ]; then', "        elif false; then"),
    ("the group is not checked", "sh:installsdcore.sh", 'if [ "$shared_line3" != "sdg_shared" ]; then', "if false; then"),
    ("the creation block runs after the accounts_kept test", "sh:installsdcore.sh",
     lambda t: (lambda i, j: t[:i] + t[j:])(t.index("# SHARED-CREATE-BEGIN"), t.index("# SHARED-CREATE-END") + len("# SHARED-CREATE-END\n")).replace(
         'if [ "$accounts_kept" = yes ]; then\n', 'if [ "$accounts_kept" = yes ]; then\n' + t[t.index("# SHARED-CREATE-BEGIN"):t.index("# SHARED-CREATE-END") + len("# SHARED-CREATE-END\n")], 1), None),
    ("the remover keeps sdg_shared", "sh:deletesdcore.sh", "        sudo groupdel sdg_shared || true\n", "        true\n"),
    ("the remover removes the group only in the keep path", "sh:deletesdcore.sh", "    if getent group sdg_shared &>/dev/null; then\n        sudo groupdel sdg_shared || true\n        echo \"Removed group sdg_shared.\"\n    fi\n    echo \"Note: for complete clean up", "    echo \"Note: for complete clean up"),
    # ---- the suite ----
    ("regress.sh forgets the suite", "txt:regress.sh", " qm4def shared viewport", " qm4def viewport"),   # 19 Oct 26: it ended the list (' shared"') until suites were added after it
]


def run(srcs):
    return checks(srcs)


def main():
    srcs = load()
    if "--selftest" in sys.argv:
        base = run(srcs)
        bad = [i for i, ok, d in base if not ok]
        if bad:
            print("test-shared-units: the unmutated source already fails: %s" % bad)
            return 2
        missed = 0
        for label, name, old, new in MUTANTS:
            try:
                rows = checks(mutate(srcs, name, old, new))
            except KeyError as e:
                print("  [FAIL] mutant is not applicable: %s (%s)" % (label, e))
                missed += 1
                continue
            caught = [i for i, ok, d in rows if not ok]
            if caught:
                print("  [PASS] mutant caught: %s  <- %s" % (label, ", ".join(c_.split(" ")[0] for c_ in caught[:3])))
            else:
                print("  [FAIL] MUTANT NOT CAUGHT: %s" % label)
                missed += 1
        print("\ntest-shared-units --selftest: %d mutants, %d missed" % (len(MUTANTS), missed))
        return 1 if missed else 0
    rows = run(srcs)
    failed = 0
    for i, ok, d in rows:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", i, "" if ok or not d else "   <- " + d))
        failed += 0 if ok else 1
    print("\ntest-shared-units: %d checks, %d failed" % (len(rows), failed))
    print("NOT MEASURED HERE: whether a gate refuses anybody, a name opens, or the installer makes the account.  That is sandbox-shared.py (ordinary sessions on a private SD),\n"
          "test-install-shared.sh (the installer's blocks on scratch files) and witness-accounts.sh (a real install, needs sudo).")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
