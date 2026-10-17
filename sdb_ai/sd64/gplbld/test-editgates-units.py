#!/usr/bin/env python3
"""test-editgates-units.py - the edit gates voc.edit, bp.edit and dict.edit (S.64), as invariants read off the source.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-editgates-units.py
  python3 .../test-editgates-units.py --selftest

No sudo, no install, no sd.  Exit 0 every check passed, 1 a check failed, 2 it could not run.  Written 17 Oct 26.

***WHAT THIS IS, AND WHAT IT IS NOT.***  It reads the C and BASIC sources as text, with comments removed, so a gate that survives only
in a comment does not count.  ***IT DOES NOT RUN ANYTHING, SO IT CANNOT SAY THAT A GATE REFUSES ANYBODY***: that is sandbox-editgates.py
(ordinary sessions on a private SD; the program's own read-back and the disk are the evidence).  What a text check is for: the gate is
reached from many places - op_dio3.c, op_seqio.c, to_file.c, op_kernel.c, op_sh.c, login, the API server, and the twelve BASIC programs
the kernel's own test lets through because they are $internal - and the invariants that make it a gate are mostly ORDERING (the refusal
before an id is taken or a lock is held, the load at SIGN-ON and nowhere else, the install walk's marker after the walk).  An edit that
moves one still compiles.

***AND THE CHECKS ARE THEMSELVES CHECKED.***  --selftest breaks each invariant in the way an edit plausibly would and requires some
check to notice.  A mutant that nothing catches is reported as a FAILURE of the self-test.
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

C_FILES = ("op_sh.c", "op_dio3.c", "op_seqio.c", "op_kernel.c", "to_file.c", "kernel.c", "keys.h", "sysseg.h", "sd.h")
BP_PROGRAMS = ("login", "cproc", "apisrvr", "modifya", "createa", "create_account", "acc_os_info", "restorea", "upgrade_editgates", "edit_guard",
               "clearfl", "delete", "copy", "copyp", "cname", "ed", "edit", "deletef", "sed", "ide", "ced_edit", "basic", "catalog", "delcat",
               "decat", "_oscopy", "_ioscopy")
FILES = {n: os.path.join(GPLSRC, n) for n in C_FILES}
FILES.update({n: os.path.join(GPL, n) for n in BP_PROGRAMS})
FILES.update({"int$keys.h": os.path.join(GPL, "int$keys.h"), "syscom/keys.h": os.path.join(SDSYS, "syscom", "keys.h"),
              "createacc.h": os.path.join(SDSYS, "syscom", "createacc.h"), "installsdcore.sh": os.path.join(ROOT, "installsdcore.sh"),
              "check-storewriters.py": os.path.join(HERE, "check-storewriters.py")})
SH_FILES = ("installsdcore.sh",)
PY_FILES = ("check-storewriters.py",)


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


def code(name, src):
    if name in C_FILES:
        return strip_c(src)
    if name in SH_FILES or name in PY_FILES:
        return strip_sh(src)
    return strip_bas(src)


def at(text, needle, start=0):
    return text.find(needle, start)


def func_body(text, signature):
    """The text of the C function that begins at SIGNATURE, up to the matching close brace (comments already removed)."""
    i = text.find(signature)
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


def checks(srcs, messages_dir):
    rows = []

    def ck(i, ok, detail=""):
        rows.append((i, bool(ok), detail))

    c = {name: code(name, text) for name, text in srcs.items()}

    # ---- K. numbers, bits, fields -----------------------------------------------------------------------------------------
    want = {"K_VOC_EDIT": 121, "K_BP_EDIT": 122, "K_DICT_EDIT": 123, "K_EDIT_OK": 124, "K_EDIT_KIND": 125, "K_EDIT_OS_OK": 126}
    got = {m.group(1): int(m.group(2)) for m in re.finditer(r"#define\s+(K_[A-Z0-9_]+)\s+(\d+)", c["keys.h"])}
    ck("K1 the six kernel keys have their numbers in keys.h", all(got.get(k) == v for k, v in want.items()), repr({k: got.get(k) for k in want}))
    by_num = {}
    for k, v in got.items():
        by_num.setdefault(v, []).append(k)
    ck("K2 no kernel key number is used twice", all(len(v) == 1 for v in by_num.values()), repr({n: v for n, v in by_num.items() if len(v) > 1}))
    bas = {m.group(1): int(m.group(2)) for m in re.finditer(r"\$define\s+(K\$[A-Z0-9.]+)\s+(\d+)", c["int$keys.h"])}
    mirror = {"K$VOC.EDIT": 121, "K$BP.EDIT": 122, "K$DICT.EDIT": 123, "K$EDIT.OK": 124, "K$EDIT.KIND": 125, "K$EDIT.OS.OK": 126}
    ck("K3 int$keys.h carries the same numbers", all(bas.get(k) == v for k, v in mirror.items()), repr({k: bas.get(k) for k in mirror}))
    acc = {m.group(1): int(m.group(2)) for m in re.finditer(r"\$define\s+(ACC\$[A-Z0-9.]+)\s+(\d+)", c["syscom/keys.h"])}
    ck("K4 register fields 10, 11, 12 are ACC$VOC.EDIT, ACC$BP.EDIT, ACC$DICT.EDIT and nothing else uses them",
       (acc.get("ACC$VOC.EDIT"), acc.get("ACC$BP.EDIT"), acc.get("ACC$DICT.EDIT")) == (10, 11, 12)
       and sorted(v for v in acc.values() if v >= 10) == [10, 11, 12], repr(acc))
    ss = c["sysseg.h"]
    ck("K5 the user table has its own gates word and the three bits (the flags word is full)",
       re.search(r"u_int16_t\s+gates\s*;", ss) is not None and re.search(r"#define\s+UG_VOC_EDIT\s+0x0001", ss) is not None
       and re.search(r"#define\s+UG_BP_EDIT\s+0x0002", ss) is not None and re.search(r"#define\s+UG_DICT_EDIT\s+0x0004", ss) is not None, "")
    kc = c["kernel.c"]
    f_off = at(kc, "my_uptr->flags = 0;")
    g_off = at(kc, "my_uptr->gates = 0;")
    ck("K6 a process taking its user entry starts with the gates off (gates zeroed beside flags)", 0 <= f_off < g_off < f_off + 400, "%d %d" % (f_off, g_off))
    ca = c["createacc.h"]
    ck("K7 createacc.h has CA$VOC.EDIT 32, CA$BP.EDIT 33, CA$DICT.EDIT 34 in the Linux-only block",
       all(re.search(r"\$define\s+%s\s+%d" % (re.escape(n), v), ca) for n, v in (("CA$VOC.EDIT", 32), ("CA$BP.EDIT", 33), ("CA$DICT.EDIT", 34))), "")

    # ---- C. the kernel ---------------------------------------------------------------------------------------------------
    sh = c["op_sh.c"]
    kind = func_body(sh, "int edit_kind_of_path(const char *path)")
    ck("C1 edit_kind_of_path knows voc, *.dic, bp, bp.out, *.bp and *.bp.out, and ignores case",
       all(s in kind for s in ('"voc"', '".dic"', '"bp"', '"bp.out"', '".bp"', '".bp.out"')) and kind.count("strncasecmp") >= 6, "")
    perm = func_body(sh, "bool edit_permitted(int kind)")
    ck("C2 edit_permitted lets the administrator through BEFORE it looks at any gate",
       0 <= at(perm, "USR_ADMIN") < at(perm, "UG_VOC_EDIT"), "")
    ck("C3 edit_permitted reads each kind's own bit", "UG_VOC_EDIT" in perm and "UG_BP_EDIT" in perm and "UG_DICT_EDIT" in perm, "")
    osr = func_body(sh, "int edit_os_path_refusal(const char *name)")
    ck("C4 edit_os_path_refusal passes the administrator, refuses a path it cannot resolve, and leaves an OS.EXECUTE account alone outside its own directory",
       "USR_ADMIN" in osr and "return EDIT_VOC" in osr and "USR_OS_EXEC" in osr, "")
    d3 = c["op_dio3.c"]
    ref = func_body(d3, "Private int edit_refusal(FILE_VAR *fvar)")
    ck("C5 edit_refusal: a $internal program and the administrator pass BEFORE the path is read",
       0 <= at(ref, "HDR_INTERNAL") < at(ref, "->pathname") and 0 <= at(ref, "USR_ADMIN") < at(ref, "->pathname"), "")
    wr = func_body(d3, "void op_write()")
    ck("C6 op_write asks edit_refusal BEFORE a CREATING.SEQKEY id is taken from the file",
       0 <= at(wr, "edit_refusal(fvar)") < at(wr, "P_SEQKEY"), "")
    wv = func_body(d3, "void op_writev()")
    ck("C7 op_writev asks BEFORE the recursive pcode, whose flags are internal", 0 <= at(wv, "edit_refusal(") < at(wv, "k_recurse(pcode_writev"), "")
    dl = func_body(d3, "void op_delete()")
    ck("C8 op_delete asks after the read-only test and before a record lock is taken or the record is read",
       0 <= at(dl, "FV_RDONLY") < at(dl, "edit_refusal(fvar)") < at(dl, "check_lock("), "")
    cl = func_body(d3, "void op_clrfile()")
    ck("C9 op_clrfile asks before it takes the file lock (StartExclusive)", 0 <= at(cl, "edit_refusal(fvar)") < at(cl, "StartExclusive("), "")
    ck("C10 a refusal without ON ERROR is an error that gives the reason (k_error with message 11404 + kind)",
       d3.count("k_error(sysmsg(EDIT_REFUSED_MSG(edit_kind)))") >= 4 and "#define EDIT_REFUSED_MSG(kind) (11404 + (kind))" in d3, "")
    kn = c["op_kernel.c"]
    setter = kn[at(kn, "case K_VOC_EDIT:"):at(kn, "case K_EDIT_OK:")]
    ck("C11 the three gate keys are set only from a $internal program", "HDR_INTERNAL" in setter and "my_uptr->gates |= edit_bit" in setter, "")
    okh = kn[at(kn, "case K_EDIT_OK:"):at(kn, "case K_EDIT_OS_OK:")]
    ck("C12 K_EDIT_OK passes the administrator, refuses an empty pathname (it starts with no name and the answer starts at 0) and asks edit_ok_for_path",
       "USR_ADMIN" in okh and re.search(r"edit_name\[0\] = '\\0';\s*result\.data\.value = 0;", okh) is not None and "edit_ok_for_path(edit_name)" in okh, "")
    osk = kn[at(kn, "case K_EDIT_OS_OK:"):at(kn, "case K_PATH_OK:")]
    ck("C13 K_EDIT_OS_OK passes the administrator and otherwise asks edit_os_path_refusal on the argument", "USR_ADMIN" in osk and "edit_os_path_refusal(edit_os_name)" in osk, "")
    sq = c["op_seqio.c"]
    ops = func_body(sq, "void op_delseq()")
    ck("C14 DELETESEQ asks edit_os_path_refusal after the path is built and before the file is looked at (stat)",
       0 <= at(ops, "edit_os_path_refusal(file_name)") < at(ops, "stat(file_name"), "")
    opn = sq[at(sq, "edit_blocked = FALSE"):]
    ck("C15 OPENSEQ works out edit_blocked once the full path is known and before the file is opened (dio_open)",
       0 <= at(opn, "edit_blocked = (edit_os_path_refusal(fullpathname)") < at(opn, "dio_open("), "")
    ck("C16 ...makes an existing file read only, refuses CREATING there (ER_PERM) and marks the file variable read only",
       "|| edit_blocked) {" in opn and "(op_flags & 0x400) && edit_blocked" in opn and "read_only || edit_blocked" in opn, "")
    ck("C17 a $internal program is not asked (as os_path_open_ok does)", "!(process.program.flags & HDR_INTERNAL)" in opn and '#include "header.h"' in sq, "")
    tf = c["to_file.c"]
    ck("C18 a print file is refused in a guarded file, after the OS gate and before the file is made",
       0 <= at(tf, "os_path_ok_for_account(fn)") < at(tf, "if (edit_os_path_refusal(fn) != EDIT_NONE) {") < at(tf, "open_file:"), "")

    # ---- B. the BASIC side -------------------------------------------------------------------------------------------------
    lg, cp, ap = c["login"], c["cproc"], c["apisrvr"]
    ck("B1 LOGIN loads the three keys from the register, off unless 'yes'",
       all(re.search(r"kernel\(K\$%s,\s*upcase\(trim\(acc\.rec<ACC\$%s>\)\) = 'YES'\)" % (k, k), lg) for k in ("VOC.EDIT", "BP.EDIT", "DICT.EDIT")), "")
    ck("B2 CPROC (LOGTO) never loads, restores or stacks them: the sign-on account decides (owner, 17 Oct)",
       all(s not in cp for s in ("K$VOC.EDIT", "K$BP.EDIT", "K$DICT.EDIT", "ACC$VOC.EDIT", "ACC$BP.EDIT", "ACC$DICT.EDIT")), "")
    m = re.search(r"if not\(master\.login\.done\) then\s*\n\s*void kernel\(K\$VOC\.EDIT,\s*api\.voc\.grant\)\s*\n\s*void kernel\(K\$BP\.EDIT,\s*api\.bp\.grant\)\s*"
                  r"\n\s*void kernel\(K\$DICT\.EDIT,\s*api\.dict\.grant\)\s*\n\s*end", ap)
    ck("B3 the API server loads them at the FIRST entry only (inside the master.login.done test), not at an SDLogto", m is not None, "")
    ck("B3b ...and that test comes before master.login.done is set", m is not None and at(ap, "master.login.done = @true", m.start()) > m.start(), "")
    ck("B4 each of the three fields starts off for every call of the API server's account routine",
       all(re.search(r"api\.%s\.grant = @false" % k, ap) for k in ("voc", "bp", "dict")), "")
    mo = c["modifya"]
    ck("B5 MODIFY.ACCOUNT has the six words, each through os.set with its own field, and os.set allows them on any account",
       all(re.search(r"case action = '%s'\s*\n\s*os\.field = ACC\$%s ; os\.want = @%s" % (w, f, b), mo)
           for w, f, b in (("VOC-ON", "VOC.EDIT", "true"), ("VOC-OFF", "VOC.EDIT", "false"), ("BP-ON", "BP.EDIT", "true"),
                           ("BP-OFF", "BP.EDIT", "false"), ("DICT-ON", "DICT.EDIT", "true"), ("DICT-OFF", "DICT.EDIT", "false")))
       and "os.field # ACC$VOC.EDIT" in mo and "sysmsg(11409" in mo, "")
    cr, ca2 = c["createa"], c["create_account"]
    ck("B6 CREATE.ACCOUNT takes VOC-ON, BP-ON and DICT-ON, and !create_account writes 'no' explicitly for a user account unless named",
       all(("case upcase(token) = '%s'" % w) in cr for w in ("VOC-ON", "BP-ON", "DICT-ON"))
       and all(re.search(r"acc\.rec<ACC\$%s> = if edit\.%s\.want then 'yes' else 'no'" % (f, k), ca2)
               for f, k in (("VOC.EDIT", "voc"), ("BP.EDIT", "bp"), ("DICT.EDIT", "dict"))), "")
    ai, rs = c["acc_os_info"], c["restorea"]
    ck("B7 the manifest carries edit.voc, edit.bp and edit.dict, and RESTORE.ACCOUNT reads them back into the settings",
       all(("'edit.%s: '" % k) in ai for k in ("voc", "bp", "dict"))
       and all(("'edit.%s'" % k) in rs for k in ("voc", "bp", "dict")) and "settings<CA$VOC.EDIT>" in rs, "")
    ue = c["upgrade_editgates"]
    walk = at(ue, "select acc.f to 12")
    ck("B8 upgrade_editgates tests its marker BEFORE the walk and writes it AFTER the walk, and only when nothing failed",
       0 <= at(ue, "ospath(marker, OS$EXISTS)") < walk < at(ue, "if failed # 0 then") < at(ue, "openseq marker to marker.f"), "")
    ck("B9 ...touches only a USER account (sdu_), and only a field that is BLANK (an explicit no is somebody's decision)",
       "rec<ACC$GROUP>[1, 4] = 'sdu_'" in ue and all(("if trim(rec<ACC$%s>) = '' then" % f) in ue for f in ("VOC.EDIT", "BP.EDIT", "DICT.EDIT")), "")
    ins = c["installsdcore.sh"]
    og = at(ins, "-internal RUN gpl.bp upgrade_gates")
    oe = at(ins, "-internal RUN gpl.bp upgrade_editgates")
    chown = at(ins, 'sudo chown -R sdsys:sdusers "$sdsysdir/accounts"')
    ck("B10 the installer runs upgrade_editgates as root after upgrade_gates and BEFORE the register is chowned to sdsys",
       0 <= og < oe < chown, "%d %d %d" % (og, oe, chown))
    ck("B11 ...and says COMPLETE is what it waits for, as for the other walks", "oe_plain" in ins and "grep -qx '[[:space:]]*COMPLETE[[:space:]]*'" in ins, "")
    ck("B12 check-storewriters lists upgrade_editgates as an install-run writer", '"upgrade_editgates"' in c["check-storewriters.py"], "")
    ck("B13 the installer tells the installing user's account the three words", all(("modify.account ${tuser_lc} %s" % w) in srcs["installsdcore.sh"]
                                                                                for w in ("voc-on", "bp-on", "dict-on")), "")

    # ---- G. the programs that must ask ---------------------------------------------------------------------------------------
    eg = c["edit_guard"]
    ck("G1 !edit_guard is an internal function that asks the kernel by the pathname of the open file and is the administrator's pass",
       "$internal" in eg and "$catalog !edit_guard" in eg and "fileinfo(f, FL$PATH)" in eg and "kernel(K$EDIT.OK, p)" in eg
       and "kernel(K$EDIT.KIND, p)" in eg and "K$ADMINISTRATOR" in eg, "")
    asks = {"clearfl": 1, "delete": 1, "copy": 2, "copyp": 2, "cname": 1, "ed": 4, "edit": 1}
    for prog, n in asks.items():
        have = len(re.findall(r"\bedit_guard\(", c[prog])) - len(re.findall(r"deffun\s+edit_guard", c[prog]))
        ck("G2 %s asks edit_guard at least %d time(s) and declares it" % (prog, n), have >= n and "deffun edit_guard" in c[prog], "asks=%d" % have)
    ck("G2b COPY asks about the source when it moves records out (DELETING), COPYP when it moves them (the D flag)",
       re.search(r"if deleting then\s*\n\s*if not\(edit_guard\(src\.file\)\)", c["copy"]) is not None
       and re.search(r"if dflag then\s*\n\s*if not\(edit_guard\(f\.file\)\)", c["copyp"]) is not None, "")
    ck("G3 CNAME of a FILE asks the kernel for the old path and the new name (a rename cannot take a program file out of its name)",
       "kernel(K$EDIT.OK, ek.path)" in c["cname"] and "ek.path = rec<2>" in c["cname"] and "ek.path = new.file.name" in c["cname"], "")
    ck("G4 DELETE.FILE asks for the data part, and for a dictionary deleted on its own, and the ask is a subroutine at the END of the program",
       c["deletef"].count("gosub edit.check.path") == 2 and at(c["deletef"], "edit.check.path:") > at(c["deletef"], "delete.dict:"), "")
    sd = c["sed"]
    ck("G5 SED asks before it saves, exports and deletes a record, and puts the reason in the message line (not a DISPLAY)",
       sd.count("gosub check.edit.file") >= 3 and "message = sysmsg(11404 + edit.kind)" in sd and "check.edit.file:" in sd, "")
    ck("G6 SED leaves its -EXT extension record out of a file the session may not change",
       sd.count("kernel(K$EDIT.OK, fileinfo(file(current.buffer), FL$PATH))") >= 2, "")
    ide = c["ide"]
    ck("G7 IDE asks before it saves, saves as and makes a new record (msg, not DISPLAY)",
       ide.count("gosub edit.check") >= 3 and "msg = sysmsg(11404 + edit.kind)" in ide and "$include syscom keys.h" in ide, "")
    ce = c["ced_edit"]
    ck("G8 CED asks before it writes a record, and includes the header that defines FL$PATH",
       "kernel(K$EDIT.OK, edit.p)" in ce and "$include syscom keys.h" in ce, "")
    ck("G8b CED asks only for a record of a FILE: !CED() on a variable has no id and no file path, and the kernel refuses a null path by design",
       re.search(r"if id # '' then\s*\n\s+edit\.p = fileinfo\(fv, FL\$PATH\)\s*\n\s+if not\(kernel\(K\$EDIT\.OK, edit\.p\)\) then", ce) is not None, "")
    for prog in ("basic", "catalog", "delcat", "decat"):
        cc = c[prog]
        first_parse = at(cc, '"!PARSER"') if prog != "basic" else at(cc, "num.programs = 0")
        gate = at(cc, "kernel(K$BP.EDIT, -1)")
        ck("G9 %s refuses a session without bp.edit (the administrator passes) before it does anything" % prog,
           0 <= gate and "kernel(K$ADMINISTRATOR, -1)" in cc and "sysmsg(11408)" in cc and (first_parse < 0 or gate < first_parse), "")
    ck("G10 !OSCOPY and !IOSCOPY refuse a copy INTO a guarded path (the target only)",
       "kernel(K$EDIT.OS.OK, target)" in c["_oscopy"] and "kernel(K$EDIT.OS.OK, target)" in c["_ioscopy"], "")

    # ---- M. the messages ------------------------------------------------------------------------------------------------------
    texts = {}
    for n in range(11405, 11411):
        p = os.path.join(messages_dir, str(n))
        texts[n] = open(p).read().strip() if os.path.exists(p) else None
    ck("M1 messages 11405 to 11410 exist", all(texts.values()), repr([n for n, t in texts.items() if not t]))
    ck("M2 each refusal names its gate and the word that gives it (voc-on, dict-on, bp-on)",
       "voc.edit" in (texts[11405] or "") and "modify.account" in (texts[11405] or "") and "voc-on" in (texts[11405] or "")
       and "dict.edit" in (texts[11406] or "") and "dict-on" in (texts[11406] or "")
       and "bp.edit" in (texts[11407] or "") and "bp-on" in (texts[11407] or "") and "bp.edit" in (texts[11408] or ""), "")
    ck("M3 11409 takes the account and the three states", "%1" in (texts[11409] or "") and "%4" in (texts[11409] or ""), "")
    return rows


def load():
    srcs = {}
    for name, path in FILES.items():
        if not os.path.exists(path):
            print("test-editgates-units: CANNOT RUN - %s is missing" % path)
            sys.exit(2)
        with open(path, encoding="utf-8", errors="replace") as f:
            srcs[name] = f.read()
    return srcs


def mutate(srcs, name, old, new, count=1):
    s = dict(srcs)
    if old not in s[name]:
        raise KeyError("mutant text not in %s: %r" % (name, old[:70]))
    s[name] = s[name].replace(old, new, count)
    return s


MUTANTS = [
    ("edit_refusal forgets that a $internal program passes", "op_dio3.c", "  if (process.program.flags & HDR_INTERNAL)\n    return EDIT_NONE;\n  if (my_uptr->flags & USR_ADMIN)\n    return EDIT_NONE;\n\n  /* The file table is shared memory", "  if (my_uptr->flags & USR_ADMIN)\n    return EDIT_NONE;\n\n  /* The file table is shared memory"),
    ("op_write does not ask before the SEQKEY id is taken", "op_dio3.c", "a CREATING.SEQKEY id included. */\n    int edit_kind = edit_refusal(fvar);", "a CREATING.SEQKEY id included. */\n    int edit_kind = EDIT_NONE;"),
    ("op_writev asks nothing before the recursive pcode", "op_dio3.c", "    edit_kind = edit_refusal(wv_fvar->data.fvar);", "    edit_kind = EDIT_NONE;"),
    ("op_clrfile asks after the lock", "op_dio3.c", "    int edit_kind = edit_refusal(fvar); /* 17 Oct 26 S.64: the edit gates */\n\n    if (edit_kind != EDIT_NONE) {\n      if (!(op_flags & P_ON_ERROR))\n        k_error(sysmsg(EDIT_REFUSED_MSG(edit_kind)));\n      /* ON ERROR", "    int edit_kind = EDIT_NONE; /* 17 Oct 26 S.64: the edit gates */\n\n    if (edit_kind != EDIT_NONE) {\n      if (!(op_flags & P_ON_ERROR))\n        k_error(sysmsg(EDIT_REFUSED_MSG(edit_kind)));\n      /* ON ERROR"),
    ("edit_permitted looks at the gate before the administrator", "op_sh.c", "bool edit_permitted(int kind) {\n  if (my_uptr->flags & USR_ADMIN)\n    return TRUE;\n  switch (kind) {\n    case EDIT_VOC:\n      return (my_uptr->gates & UG_VOC_EDIT) != 0;", "bool edit_permitted(int kind) {\n  switch (kind) {\n    case EDIT_VOC:\n      return (my_uptr->gates & UG_VOC_EDIT) != 0;"),
    ("a bp.out file is no longer a program file", "op_sh.c", '  if ((n == 6) && (strncasecmp(last, "bp.out", 6) == 0))\n    return EDIT_PROG;\n', ""),
    ("K_EDIT_OK answers 1 for an empty pathname", "op_kernel.c", "  edit_name[0] = '\\0';\n      result.data.value = 0;\n      if (action == K_EDIT_OK) {", "  edit_name[0] = '\\0';\n      result.data.value = 1;\n      if (action == K_EDIT_OK) {"),
    ("the gate keys can be set from a user program", "op_kernel.c", "      if (n >= 0) {\n        if (process.program.flags & HDR_INTERNAL) {\n          if (n > 0)\n            my_uptr->gates |= edit_bit;", "      if (n >= 0) {\n        if (1) {\n          if (n > 0)\n            my_uptr->gates |= edit_bit;"),
    ("OPENSEQ no longer makes a blocked file read only", "op_seqio.c", "      if ((op_flags & P_READONLY) || access(fullpathname, 2) || edit_blocked) {", "      if ((op_flags & P_READONLY) || access(fullpathname, 2)) {"),
    ("DELETESEQ asks after the file is looked at", "op_seqio.c", "  if (!(process.program.flags & HDR_INTERNAL) && (edit_os_path_refusal(file_name) != EDIT_NONE)) {\n    process.status = ER_PERM;\n    goto exit_op_delseq;\n  }\n\n  /* Check file exists */\n\n  if (stat(file_name, &stat_buf) != 0) {\n    process.status = ER_FNF;\n    goto exit_op_delseq;\n  }", "  /* Check file exists */\n\n  if (stat(file_name, &stat_buf) != 0) {\n    process.status = ER_FNF;\n    goto exit_op_delseq;\n  }\n\n  if (!(process.program.flags & HDR_INTERNAL) && (edit_os_path_refusal(file_name) != EDIT_NONE)) {\n    process.status = ER_PERM;\n    goto exit_op_delseq;\n  }"),
    ("a print file is not looked at", "to_file.c", "    if (edit_os_path_refusal(fn) != EDIT_NONE) {", "    if (0) {"),
    ("LOGTO reloads the VOC gate", "cproc", "   void kernel(K$SD.ACCOUNTS, upcase(trim(acc.record<ACC$SD.ACCOUNTS>)) = 'YES')", "   void kernel(K$VOC.EDIT, upcase(trim(acc.record<ACC$VOC.EDIT>)) = 'YES')\n   void kernel(K$SD.ACCOUNTS, upcase(trim(acc.record<ACC$SD.ACCOUNTS>)) = 'YES')"),
    ("LOGIN forgets the bp gate", "login", "   void kernel(K$BP.EDIT,   upcase(trim(acc.rec<ACC$BP.EDIT>)) = 'YES')\n", ""),
    ("the API server reloads at every SDLogto", "apisrvr", "if not(master.login.done) then\n   void kernel(K$VOC.EDIT,  api.voc.grant)", "if 1 then\n   void kernel(K$VOC.EDIT,  api.voc.grant)"),
    ("MODIFY.ACCOUNT loses DICT-OFF", "modifya", "      case action = 'DICT-OFF'\n         os.field = ACC$DICT.EDIT ; os.want = @false", "      case action = 'DICT-OFFX'\n         os.field = ACC$DICT.EDIT ; os.want = @false"),
    ("a new user account is written with the voc field blank", "create_account", "     acc.rec<ACC$VOC.EDIT> = if edit.voc.want then 'yes' else 'no'\n", ""),
    ("the manifest drops edit.bp", "acc_os_info", "         info<-1> = 'edit.bp: ':(if upcase(trim(acc.rec<ACC$BP.EDIT>)) = 'YES' then 1 else 0)\n", ""),
    ("upgrade_editgates writes its marker before the walk", "upgrade_editgates", "   changed = 0\n   kept = 0", "   openseq marker to marker.f then\n      weofseq marker.f\n   end else\n      create marker.f else null\n   end\n   changed = 0\n   kept = 0"),
    ("upgrade_editgates overwrites an explicit no", "upgrade_editgates", "if trim(rec<ACC$VOC.EDIT>) = '' then rec<ACC$VOC.EDIT> = 'yes'", "rec<ACC$VOC.EDIT> = 'yes'"),
    ("the installer stops running upgrade_editgates", "installsdcore.sh", "-internal RUN gpl.bp upgrade_editgates", "-internal RUN gpl.bp upgrade_nothing"),
    ("ED forgets to ask when it saves", "ed", "   if not(edit_guard(n.file)) then return\n\n   readvu s from n.file, new.record, 0 locked", "   readvu s from n.file, new.record, 0 locked"),
    ("COPY forgets the source of a move", "copy", "   if deleting then\n      if not(edit_guard(src.file)) then", "   if 0 then\n      if not(edit_guard(src.file)) then"),
    ("CNAME forgets the new name", "cname", "      if ek = 1 then ek.path = rec<2> else ek.path = new.file.name", "      if ek = 1 then ek.path = rec<2> else ek.path = ''"),
    ("SED saves without asking", "sed", "   edit.f = file(current.buffer)\n   gosub check.edit.file\n   if not(edit.ok) then return\n\n   * Process source control actions if required", "   * Process source control actions if required"),
    ("IDE's save-as forgets to ask", "ide", "   gosub edit.check                  ;* 17 Oct 26 dm - S.64\n   if not(edit.ok) then return\n   exists = @false\n   read x from fv, wa.id then exists = @true", "   exists = @false\n   read x from fv, wa.id then exists = @true"),
    ("CED saves without asking", "ced_edit", "   if not(kernel(K$EDIT.OK, edit.p)) then", "   if 0 then"),
    ("CED asks about a variable too (no id, no file)", "ced_edit", "   if id # '' then\n      edit.p = fileinfo(fv, FL$PATH)", "   if 1 then\n      edit.p = fileinfo(fv, FL$PATH)"),
    ("BASIC compiles for anybody", "basic", "   if not(kernel(K$ADMINISTRATOR, -1)) and not(kernel(K$BP.EDIT, -1)) then", "   if 0 then"),
    ("CATALOG forgets the gate", "catalog", "   if not(kernel(K$ADMINISTRATOR, -1)) and not(kernel(K$BP.EDIT, -1)) then", "   if 0 then"),
    ("DELETE.FILE forgets a dictionary on its own", "deletef", "         if not(delete.data) then\n            ef.path = dict.path\n            gosub edit.check.path\n         end", ""),
    ("!OSCOPY forgets the target", "_oscopy", "end else if not(kernel(K$EDIT.OS.OK, target)) then", "end else if 0 then"),
    ("message 11405 stops naming the word", "MESSAGE:11405", "voc-on", "voc-add"),
]


def run(srcs, messages_dir):
    rows = checks(srcs, messages_dir)
    return rows


def main():
    srcs = load()
    messages_dir = os.path.join(SDSYS, "messages")
    if "--selftest" in sys.argv:
        base = run(srcs, messages_dir)
        bad = [i for i, ok, d in base if not ok]
        if bad:
            print("test-editgates-units: the unmutated source already fails: %s" % bad)
            return 2
        missed = 0
        for label, name, old, new in MUTANTS:
            if name.startswith("MESSAGE:"):
                mdir = os.path.join(os.environ.get("TMPDIR", "/tmp"), "editgates-msgs-%d" % os.getpid())
                os.makedirs(mdir, exist_ok=True)
                for n in range(11405, 11411):
                    with open(os.path.join(messages_dir, str(n))) as f:
                        t = f.read()
                    if str(n) == name.split(":")[1]:
                        t = t.replace(old, new)
                    with open(os.path.join(mdir, str(n)), "w") as f:
                        f.write(t)
                rows = checks(srcs, mdir)
                for n in range(11405, 11411):
                    os.remove(os.path.join(mdir, str(n)))
                os.rmdir(mdir)
            else:
                try:
                    rows = checks(mutate(srcs, name, old, new), messages_dir)
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
        print("\ntest-editgates-units --selftest: %d mutants, %d missed" % (len(MUTANTS), missed))
        return 1 if missed else 0
    rows = run(srcs, messages_dir)
    failed = 0
    for i, ok, d in rows:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", i, "" if ok or not d else "   <- " + d))
        failed += 0 if ok else 1
    print("\ntest-editgates-units: %d checks, %d failed" % (len(rows), failed))
    print("NOT MEASURED HERE: whether a gate refuses anybody.  That is sandbox-editgates.py (ordinary sessions on a private SD).")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
