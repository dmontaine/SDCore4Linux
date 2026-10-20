#!/usr/bin/env python3
"""test-masters-units.py - the master files (S.67 stage 1), as invariants read off the source.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-masters-units.py
  python3 .../test-masters-units.py --selftest

No sudo, no install, no sd.  Exit 0 every check passed, 1 a check failed, 2 it could not run.  Written 19 Oct 26.

***WHAT THIS IS, AND WHAT IT IS NOT.***  It reads the C, BASIC and shell sources as text, with comments removed, so a rule that survives only in a
comment does not count.  ***IT DOES NOT RUN ANYTHING, SO IT CANNOT SAY THAT A JOURNAL LINE IS WRITTEN, THAT A MASTER COPY EQUALS ITS ACCOUNT'S
RECORD, THAT CHECK.MASTERS FINDS A PLANTED DIFFERENCE OR THAT A MODE IS WHAT THE CODE SAYS***: that is sandbox-masters.py (ordinary sessions on a
private SD, the journal and the master files read as evidence).  What a text check is for: the feature hangs on ORDER, in places where a wrong order
loses an update without a sign - the hook after the write has succeeded and nowhere before; the size test and the append under the semaphore the drain
truncates under; the administrator test before every op that changes or reveals anything; the register write before the sync that needs it; the
register delete before the drop; the journal read before the state is written - and on THE ABSENCES: the hook never creates the journal, never
carries a record's data, never blocks a write, and the check op never writes.

The blocks of checks:  N numbers, bits, files and messages  H the hook (the DH layer and the OS routes)  J the journal line  D the drain
K the ops of K_MASTERS  B the BASIC (verbs, set-up, lifecycle)  I the installer  R wiring (regress.sh, regress-map.txt).

***AND THE CHECKS ARE THEMSELVES CHECKED.***  --selftest breaks each invariant in the way an edit plausibly would and requires some check to notice.
A mutant that nothing catches, or that does not change the file it names, is reported as a FAILURE of the self-test.
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

MSG_FIRST, MSG_LAST = 11560, 11578           # stage 1
MSG2_FIRST, MSG2_LAST = 11579, 11596         # stage 2 (master to account); 11595 and 11596 are the verifier fixes' (no lock could be taken; not read first)
BP_NAMED = ("masters", "masters_setup", "upgrade_masters", "create_account", "delacc", "restorea", "_oscopy", "_ioscopy")
C_NAMED = ("masters.c", "dh_write.c", "dh_del.c", "dh_clear.c", "dh_creat.c", "op_dio1.c", "op_dio2.c", "op_dio3.c", "op_xfun.c", "op_kernel.c",
           "txn.c", "keys.h", "sysseg.h", "sd.h", "dh.h")


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
    i = text.find(a)
    if i < 0:
        return ""
    j = text.find(b, i + len(a))
    return text[i:j] if j >= 0 else ""


def squash(s):
    return re.sub(r"\s+", "", s)


def sysmsg_arg_counts(text):
    """The number of substitution arguments of each sysmsg( call in BASIC TEXT: the commas at the top level of the call, not those inside < > or ( )."""
    counts = []
    for m in re.finditer(r"sysmsg\(", text):
        depth, angle, n, i = 1, 0, 0, m.end()
        while i < len(text) and depth:
            ch = text[i]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif ch == "<":
                angle += 1
            elif ch == ">" and angle:
                angle -= 1
            elif ch == "," and depth == 1 and angle == 0:
                n += 1
            elif ch == "'" or ch == '"':
                j = text.find(ch, i + 1)
                i = j if j > i else i
            i += 1
        counts.append(n)
    return counts


def load():
    srcs = {}

    def get(name, path):
        if not os.path.exists(path):
            print("test-masters-units: CANNOT RUN - %s is missing" % path)
            sys.exit(2)
        with open(path, encoding="utf-8", errors="replace") as f:
            srcs[name] = f.read()
    for fn in sorted(os.listdir(GPLSRC)):
        if fn.endswith((".c", ".h")):
            get("c:" + fn, os.path.join(GPLSRC, fn))
    for n in C_NAMED:
        if "c:" + n not in srcs:
            print("test-masters-units: CANNOT RUN - %s is missing" % os.path.join(GPLSRC, n))
            sys.exit(2)
    for fn in sorted(os.listdir(GPL)):
        p = os.path.join(GPL, fn)
        if os.path.isfile(p):
            get("bp:" + fn, p)
    for n in BP_NAMED:
        if "bp:" + n not in srcs:
            print("test-masters-units: CANNOT RUN - %s is missing" % os.path.join(GPL, n))
            sys.exit(2)
    get("sh:installsdcore.sh", os.path.join(ROOT, "installsdcore.sh"))
    get("sh:sd-elevate", os.path.join(HERE, "sd-elevate"))
    get("txt:regress.sh", os.path.join(HERE, "regress.sh"))
    get("txt:regress-map.txt", os.path.join(HERE, "regress-map.txt"))
    get("txt:gpl.src", os.path.join(SD64, "gpl.src"))
    for v in ("sync.masters", "check.masters", "list.master.pending"):
        get("voc:" + v, os.path.join(SDSYS, "voc_template", v))
    srcs["newvoc.list"] = "\n".join(sorted(os.listdir(os.path.join(SDSYS, "newvoc"))))
    srcs["voc_template.list"] = "\n".join(sorted(os.listdir(os.path.join(SDSYS, "voc_template"))))
    for n in range(MSG_FIRST, MSG2_LAST + 1):
        p = os.path.join(MSGDIR, str(n))
        srcs["msg:%d" % n] = open(p, encoding="utf-8", errors="replace").read() if os.path.exists(p) else None
    for t in ("sandbox-masters.py", "test-masters-units.py", "witness-masters.sh", "test-install-sdsysgroups.sh"):
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

    m = C("masters.c")

    # ---- N. numbers, bits, files, messages ---------------------------------------------------------------------------------------------
    kk = defs(C("keys.h"), r"#define\s+(K_[A-Z0-9_]+)\s+(\d+)")
    ck("N1 keys.h: K_MASTERS is 150, and no kernel key number is used twice", kk.get("K_MASTERS") == 150 and len(set(kk.values())) == len(kk.values()), repr(kk.get("K_MASTERS")))
    bk = defs(B("int$keys.h"), r"\$define\s+(K\$[A-Z0-9.]+)\s+(\d+)")
    ck("N2 int$keys.h carries the same number, and none is used twice (outside the old low block)",
       bk.get("K$MASTERS") == 150 and len(set(v for v in bk.values() if v >= 100)) == len([v for v in bk.values() if v >= 100]), repr(bk.get("K$MASTERS")))
    dh = defs(C("dh.h"), r"#define\s+(DHF_[A-Z_]+|FILE_UPDATED)\s+(0x[0-9A-Fa-f]+)", 16)
    bits = [dh.get(k) for k in ("DHF_MST_NONE", "DHF_MST_VOC", "DHF_MST_DICT")]
    ck("N3 dh.h: DHF_MST_NONE 0x04000000, DHF_MST_VOC 0x08000000, DHF_MST_DICT 0x10000000 - each one bit in the INTERNAL half of the word (above 0xFFFF, so none is ever in a "
       "file header), no bit used by another flag",
       bits == [0x04000000, 0x08000000, 0x10000000] and all(b & (b - 1) == 0 for b in bits) and len(set(dh.values())) == len(dh.values()), repr(bits))
    ss = C("sysseg.h")
    ck("N4 sysseg.h: the three fields (u_int16_t masters_flags, u_int32_t masters_failed, u_int32_t masters_dropped) come after lock_trace, the last field before them, so that no "
       "offset moves; MST_F_STALE is 0x0001 and MST_F_RESYNC 0x0002",
       ordered(ss, "int16_t lock_trace;", "u_int16_t masters_flags;", "u_int32_t masters_failed;", "u_int32_t masters_dropped;", "};")
       and ss.count("masters_flags;") == 1 and ss.count("masters_failed;") == 1 and ss.count("masters_dropped;") == 1 and re.search(r"#define\s+MST_F_STALE\s+0x0001\b", ss) is not None and re.search(r"#define\s+MST_F_RESYNC\s+0x0002\b", ss) is not None, "")
    flat = squash(C("sd.h"))
    protos = ("void masters_note_record(DH_FILE*dh,charop,constchar*id,intid_len);", "void masters_note_dh(DH_FILE*dh,charop);", "void masters_note_name(constchar*name,charop);",
              "void masters_open_hook(constchar*canon);", "void masters_request(constchar*req,DESCRIPTOR*result);")
    ck("N5 sd.h declares the five public functions of masters.c", all(squash(p).replace("constchar*id,", "constchar*id,") in flat or p in flat for p in protos),
       repr([p for p in protos if p not in flat]))
    ck("N6 gpl.src lists masters, so that the Makefile builds it", re.search(r"^masters$", c["txt:gpl.src"], re.M) is not None, "")
    texts = {n: srcs.get("msg:%d" % n) for n in range(MSG_FIRST, MSG_LAST + 1)}
    used = [n for n in texts if texts[n] is not None]
    ck("N7 all nineteen messages 11560 to 11578 exist, each one non-empty line",
       len(used) == MSG_LAST - MSG_FIRST + 1 and all(texts[n].strip() and "\n" not in texts[n].rstrip("\n") for n in used), repr([n for n in texts if not texts[n] or not texts[n].strip()]))
    ck("N8 the usage messages name the verbs in lower case, as the command words of messages are written: 11560 sync.masters, 11561 check.masters, 11562 list.master.pending",
       (texts.get(11560) or "").startswith("Usage: sync.masters") and (texts.get(11561) or "").startswith("Usage: check.masters")
       and (texts.get(11562) or "").startswith("Usage: list.master.pending"), "")
    cited = set()
    for name in ("masters", "masters_setup", "upgrade_masters"):
        cited |= set(int(x) for x in re.findall(r"sysmsg\((\d+)", B(name)))
    ck("N9 every message the verb program cites exists and lies in 11560 to 11594 (stage 2 added 11593, the CHECK.MASTERS hint, and 11594, the last refusal), and its substitution never takes more than 4 arguments (the compiler's SYSMSG limit)",
       all(MSG_FIRST <= n <= MSG2_LAST or n == 2001 for n in cited) and all(srcs.get("msg:%d" % n) is not None for n in cited if n != 2001)
       and max(sysmsg_arg_counts(B("masters")) + [0]) <= 4 and len(sysmsg_arg_counts(B("masters"))) >= 15, repr((sorted(cited), sysmsg_arg_counts(B("masters")))))
    big = [n for n, t in texts.items() if t is not None and max([int(x) for x in re.findall(r"%(\d)", t)] + [0]) > 4]
    ck("N10 no message of the block has a %5 or higher", not big, repr(big))

    # ---- H. the hook ----------------------------------------------------------------------------------------------------------------
    dw = C("dh_write.c")
    ck("H1 dh_write.c: masters_note_record(dh_file, 'w', id, id_len) is called once, inside the final 'if (dh_err == 0)' block, AFTER dh_forced_write and BEFORE the return",
       dw.count("masters_note_record(") == 1 and ordered(dw, "if (dh_err == 0) {", "dh_forced_write(dh_file);", "masters_note_record(dh_file, 'w', id, id_len);", "return (dh_err == 0);")
       and re.search(r"if \(dh_err == 0\) \{\s*dh_forced_write\(dh_file\);[^}]*masters_note_record\(dh_file, 'w', id, id_len\);\s*\}\s*return \(dh_err == 0\);", dw) is not None, "")
    dd = C("dh_del.c")
    ck("H2 dh_del.c: masters_note_record(dh_file, 'd', id, id_len) is called once, only 'if (found)' (this function succeeds for a record that was not there), under dh_err == 0, after dh_forced_write",
       dd.count("masters_note_record(") == 1 and re.search(r"if \(dh_err == 0\) \{\s*dh_forced_write\(dh_file\);[\s\S]*?if \(found\)\s*masters_note_record\(dh_file, 'd', id, id_len\);\s*\}\s*return \(dh_err == 0\);", dd) is not None, "")
    dc = C("dh_clear.c")
    ck("H3 dh_clear.c: masters_note_dh(dh_file, 'c') once, after status = TRUE and before the exit label (a clear that failed is not journalled)",
       dc.count("masters_note_dh(") == 1 and ordered(dc, "status = TRUE;", "masters_note_dh(dh_file, 'c');", "exit_dh_clear:"), "")
    dcr = C("dh_creat.c")
    ck("H4 dh_creat.c: masters_note_name(path, 'n') once, after status = TRUE and before the exit label (a file that was not made is not journalled)",
       dcr.count("masters_note_name(") == 1 and ordered(dcr, "status = TRUE;", "masters_note_name(path, 'n');", "exit_dh_create_file:"), "")
    d2 = C("op_dio2.c")
    ck("H5 op_dio2.c: OSPATH's OS_DELETE journals the path AFTER delete_path (the path need not exist); OSRENAME journals the old name (x) and the new (n) AFTER rename() succeeded "
       "and not before the failure exits",
       ordered(d2, "case OS_DELETE:", "status = (int32_t)delete_path(path);", "masters_note_name(path, 'x');", "break;")
       and ordered(d2, "if (rename(old_path, new_path)) {", "goto exit_osrename;", "masters_note_name(old_path, 'x');", "masters_note_name(new_path, 'n');", "exit_osrename:")
       and d2.count("masters_note_name(old_path, 'x')") == 1 and d2.count("masters_note_name(new_path, 'n')") == 1 and d2.count("masters_note_name(path, 'x')") == 1, "")
    xf = C("op_xfun.c")
    ck("H6 op_xfun.c: the second OSPATH (the function for programs that are not internal) journals key 5's path after it removed it",
       ordered(xf, "value = (rmdir(path) == 0);", "value = (unlink(path) == 0);", "masters_note_name(path, 'x');", "break;") and xf.count("masters_note_name(") == 1, "")
    d1 = C("op_dio1.c")
    ck("H7 op_dio1.c: open_file() calls masters_open_hook(pathname) after fullpath() and before the OS-access test of OPENPATH and before the transaction and cache lookups",
       d1.count("masters_open_hook(pathname)") == 1 and ordered(d1, "fullpath(pathname, mapped_name);", "masters_open_hook(pathname);", "if (!map_name && !os_path_open_ok(pathname))", "txn_open(pathname)"), "")
    ck("H8 the record opcodes and the transaction code do NOT call the JOURNAL hook: it is in the DH layer, which a COMMIT passes through (a call in op_dio3.c or txn.c would deliver "
       "an uncommitted write and a rolled-back one).  Stage 2: op_dio3.c asks only masters_txn_refusal and masters_refusal_text (S7), and (verifier F3) tells masters_note_read of a read; txn.c nothing",
       set(re.findall(r"\bmasters_\w+", C("op_dio3.c"))) <= {"masters_txn_refusal", "masters_refusal_text", "masters_note_read"} and "masters_" not in C("txn.c"), repr(set(re.findall(r"\bmasters_\w+", C("op_dio3.c")))))
    callers = sorted(n for n, t in c.items() if n.startswith("c:") and re.search(r"\bmasters_(note_record|note_dh|note_name|open_hook|request)\(", t) and n != "c:masters.c" and n != "c:sd.h")
    ck("H9 exactly these files call into masters.c: dh_write, dh_del, dh_clear, dh_creat, op_dio1, op_dio2, op_kernel, op_xfun",
       callers == ["c:dh_clear.c", "c:dh_creat.c", "c:dh_del.c", "c:dh_write.c", "c:op_dio1.c", "c:op_dio2.c", "c:op_kernel.c", "c:op_xfun.c"], repr(callers))
    nr = func_body(m, "void masters_note_record(DH_FILE *dh, char op, const char *id, int id_len)")
    ck("H10 masters_note_record: the cheap refusal (DHF_MST_NONE) is the FIRST test, the name is classified once per open file and remembered in the DH_FILE's flags, the account comes from "
       "the file's pathname, and a file whose class does not agree with its name is ignored",
       ordered(nr, "DHF_MST_NONE", "mst_name_kind(", "dh->flags |= DHF_MST_NONE", "dh->flags |= (kind == MST_VOC)", "mst_journal_open()", "mst_classify(", "mst_journal_line(fd, kind, op, acct, file, id, id_len);")
       and re.search(r"mst_classify\([^;]*sizeof\(file\)\) != kind\) \{\s*close\(fd\);\s*return;", nr) is not None, "")
    nn = func_body(m, "void masters_note_name(const char *name, char op)")
    ck("H10a ...and the JOURNAL IS OPENED BEFORE ANYTHING IS WORKED OUT (a system with no master files costs one failed open): the first mst_classify comes after the open, and in "
       "masters_note_name the path is not resolved before it either",
       0 <= nr.find("mst_journal_open()") < nr.find("mst_classify(") and nr.count("mst_classify(") == 1
       and ordered(nn, "mst_journal_open()", "fullpath(full", "mst_classify(", "mst_journal_line(fd, kind, op, acct, file") and 0 <= nn.find("mst_journal_open()") < nn.find("fullpath(") and nn.count("fullpath(") == 1, "")
    ck("H11 the hook functions return void and none of them can stop the caller: no k_error, exit, abort, longjmp or return of a status in masters_note_* / mst_journal_open / mst_journal_line",
       all(re.search(r"\b(k_error|exit|abort|longjmp)\s*\(", b) is None for b in (nr, func_body(m, "void masters_note_name(const char *name, char op)"),
                                                                                    func_body(m, "void masters_note_dh(DH_FILE *dh, char op)"),
                                                                                    func_body(m, "Private int mst_journal_open(void)"),
                                                                                    func_body(m, "Private void mst_journal_line(int fd, int kind, char op, const char *acct, const char *file, const char *id, int id_len)")))
       and "void masters_note_record(" in m and "void masters_note_dh(" in m and "void masters_note_name(" in m, "")
    ck("H12 the K_MASTERS case of op_kernel.c reads the request as a C string and hands it to masters_request, nothing else",
       ordered(C("op_kernel.c"), "case K_MASTERS: {", "k_get_c_string(descr, masters_req", "masters_request(masters_req, &result);", "} break;"), "")

    # ---- J. the journal line ---------------------------------------------------------------------------------------------------------
    jl = func_body(m, "Private void mst_journal_line(int fd, int kind, char op, const char *acct, const char *file, const char *id, int id_len)")
    jo = func_body(m, "Private int mst_journal_open(void)")
    ck("J1 mst_journal_open opens the journal O_WRONLY | O_APPEND | O_NOFOLLOW and never O_CREAT (a session that made it would own it); a missing journal is NOT a failure on a system with no "
       "master files, and IS one (stale) where they exist - a lost journal loses every line; any other failure to open is stale",
       "O_WRONLY | O_APPEND | O_NOFOLLOW" in jo and "O_CREAT" not in jl + jo and re.search(r"if \(\(errno != ENOENT\) \|\| mst_masters_present\(\)\)\s*mst_flag\(MST_F_STALE\);\s*return -1;", jo) is not None
       and "%s%c%s%c%%0" in func_body(m, "Private bool mst_masters_present(void)") and "MST_VOC_MASTER" in func_body(m, "Private bool mst_masters_present(void)"), "")
    ck("J2 ...there is exactly ONE write() in it (one line, one write), made under ERRLOG_SEM together with the size test, and the semaphore is given back on every path that took it",
       len(re.findall(r"\bwrite\s*\(", jl)) == 1 and jl.count("StartExclusive(ERRLOG_SEM") == 1 and jl.count("EndExclusive(ERRLOG_SEM)") == 1
       and ordered(jl, "StartExclusive(ERRLOG_SEM", "fstat(fd, &st)", "MST_JOURNAL_CAP", "write(fd, line", "EndExclusive(ERRLOG_SEM)", "close(fd)"), "")
    ck("J3 ...the size test comes BEFORE the write and sets the resync flag; a short or failed write sets the stale flag; an id that cannot be encoded sets the stale flag; "
       "the line is built from the keys and the time only",
       ordered(jl, "st.st_size >= MST_JOURNAL_CAP", "mst_flag(MST_F_RESYNC);", "write(fd, line", "!= len", "mst_flag(MST_F_STALE);")
       and re.search(r'snprintf\(line, sizeof\(line\), "%lld %c %c %s %s %s\\n", \(long long\)time\(NULL\), \(kind == MST_VOC\) \? \'v\' : \'d\', op, acct, fenc, ienc\);', jl) is not None, "")
    ck("J4 the function takes the keys (kind, op, account, file, id and its length) and nothing that could carry a record's data: no STRING_CHUNK, DESCRIPTOR or buffer of data in its signature",
       "STRING_CHUNK" not in jl and "DESCRIPTOR" not in jl and "data" not in re.sub(r"\s+", " ", jl.split("{", 1)[0]), "")
    enc = func_body(m, "Private int mst_enc(char *out, size_t outsz, const char *s, int len)")
    ck("J5 mst_enc encodes every byte that could split or forge a line: a control character and the space (<= 0x20), the percent sign, DEL and everything above (>= 0x7F), and a lone '-'; "
       "an empty string is '-'", "c <= 0x20" in enc and "c == '%'" in enc and "c >= 0x7F" in enc and "c == '-'" in enc and "out[0] = '-'" in enc, "")
    ck("J6 the journal's size limit is 4 MB and the entry buffer is smaller than PIPE_BUF (4096), so that one write is atomic",
       re.search(r"#define MST_JOURNAL_CAP \(4L \* 1024L \* 1024L\)", m) is not None and re.search(r"char line\[(\d+)\]", jl) is not None and int(re.search(r"char line\[(\d+)\]", jl).group(1)) < 4096, "")
    ck("J7 the flags are set with atomic operations on the shared segment (two sessions failing at once lose neither bit)",
       "__sync_fetch_and_or(&sysseg->masters_flags, bit)" in func_body(m, "Private void mst_flag(u_int16_t bit)"), "")
    ini = func_body(m, "Private void mst_init(MST_BUF *out)")
    ck("J8 mst_init is the only place the journal is created: O_CREAT | O_EXCL with mode 0620, fchmod(fd, 0620) against the umask, owner sdsys and group sdusers when they exist; the "
       "master files' directories 0700 and their subfiles 0600 (verifier F1: the sdsys user alone - no group bit, no other bit; there is no group called sdsys, and the group of an SDSYS "
       "session is sdusers, which every SD user is in), their owner the sdsys user and their group the sdsys user's own (pw_gid), never a group looked up by the name sdsys",
       "O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0620" in ini and "fchmod(fd, 0620)" in ini and "getpwnam(\"sdsys\")" in ini and "getgrnam(\"sdusers\")" in ini
       and "chmod(dirpath, 0700)" in ini and "chmod(q, 0600)" in ini and len(re.findall(r"O_CREAT", m)) == 1
       and 'getgrnam("sdsys")' not in ini and "sys_gid = pw->pw_gid;" in ini and "chown(dirpath, want_uid, sys_gid)" in ini and "chown(q, want_uid, sys_gid)" in ini
       and re.search(r"chmod\((dirpath|q), 0[67][0-7][0-7]\)", ini.replace("chmod(dirpath, 0700)", "").replace("chmod(q, 0600)", "")) is None, "")

    # ---- D. the drain -----------------------------------------------------------------------------------------------------------------
    oh = func_body(m, "void masters_open_hook(const char *canon)")
    ck("D1 masters_open_hook does nothing unless the session is the administrator and the path is one of the three master files, and it cannot recurse (busy)",
       ordered(oh, "busy ||", "USR_ADMIN", "mst_is_master_path(canon)", "busy = TRUE;", "mst_drain(&cx, -1, &dr)", "busy = FALSE;"), "")
    mw = func_body(m, "Private int mst_master_which(const char *canon)")
    ck("D2 the three master paths are voc_master, dict_master and master_state under the SYSTEM directory as the OS resolves it (not a name that a VOC entry could give another file); "
       "mst_is_master_path is 'which is not 0'",
       "mst_sysdir_real()" in mw and "MST_VOC_MASTER" in mw and "MST_DICT_MASTER" in mw and "MST_STATE" in mw
       and re.search(r"mst_is_master_path\(const char \*canon\) \{\s*return mst_master_which\(canon\) != 0;", m) is not None, "")
    dr = func_body(m, "Private int mst_drain(MST_CTX *cx, long start, MST_DRAIN *res)")
    ck("D3 mst_drain: the journal is locked with flock(LOCK_EX) before anything is read, the saved position is read before the lines, the lines are read only up to the last newline "
       "(a half line stays), the state is written AFTER the compaction decision, and unlocked last",
       ordered(dr, "flock(fd, LOCK_EX)", "mst_jstate_get(cx, &offset, &sino, &total);", "pread(fd, buf", "memchr(lstart, '\\n'", "ftruncate(fd, 0)", "mst_jstate_put(", "flock(fd, LOCK_UN)"), "")
    ck("D4 ...the truncation is made only when everything up to the end was taken (consumed == st_size), under ERRLOG_SEM, and only if the size is STILL what was taken when the semaphore is held "
       "(an entry appended in between stays)",
       ordered(dr, "consumed == (long)st.st_size", "StartExclusive(ERRLOG_SEM", "fstat(fd, &st) == 0", "(long)st.st_size == consumed", "ftruncate(fd, 0) == 0", "EndExclusive(ERRLOG_SEM)"), "")
    ck("D5 ...the position record is written only when something moved (a drain that found nothing changes no byte of master_state: CHECK.MASTERS, which drains first, is read only because of it)",
       re.search(r"if \(\(res->offset_after != saved_off\) \|\| \(\(long\)st\.st_ino != saved_ino\) \|\| \(res->keys \+ res->files > 0\)\)\s*mst_jstate_put\(", dr) is not None, "")
    ck("D6 ...only lines of REGISTERED accounts are applied (the rest are counted skipped), the lines are sorted so that a file-level line comes before the key lines of its file, and a file synced "
       "whole makes its other lines redundant (they are skipped, not applied again)",
       ordered(dr, "if (mst_acc_find(ev[i].acct) >= 0)", "res->skipped++;", "qsort(ev, (size_t)nev, sizeof(MST_EVT), mst_evt_cmp);", "mst_sync_file(cx, kind, a->name, a->root, e->file, &slice, strlen(sub));",
               "for (j = i + 1;", "mst_sync_key(cx, kind, a->name, a->root, e->file, e->id, e->id_len);"), "")
    ck("D7 ...the account of a line is found in the register by NAME - as a COPY of its table entry (verifier F2) - and its directory comes from the register, never from the line (a line cannot name a path)",
       "mst_acc_by_name(e->acct, &acc)" in dr and "MST_ACC acc;" in dr and "a->root" in dr and "e->file, &slice" in dr and "root = " not in dr, "")
    pl = func_body(m, "Private int mst_parse_line(char *line, MST_EVT *ev)")
    ck("D8 mst_parse_line refuses a line that is not exactly six fields, a time that is not digits, a kind other than v or d, an op other than w d c n x, an account name that is not a valid "
       "account name, a dictionary file name that mst_file_ok refuses (.., a leading /, an asterisk), a VOC line that names a file, and a write or delete without an id",
       'if ((n != 6) || (p != NULL))' in pl and 'strspn(f[0], "0123456789")' in pl and "strchr(\"wdcnx\", f[2][0])" in pl and "mst_valid_account_name(f[3])" in pl
       and "mst_file_ok(ev->file)" in pl and "(ev->kind == 'v') && (ev->file[0] != '\\0')" in pl and "ev->id_len == 0" in pl, "")
    fo = func_body(m, "Private bool mst_file_ok(const char *f)")
    ck("D9 mst_file_ok refuses an empty name, one over MST_FILE_MAX, an absolute one, a control or space or non-ASCII character, an asterisk, and a component that is empty or . or ..",
       "(f[0] == '/')" in fo and "(f[i] == '*')" in fo and "< 33" in fo and "> 126" in fo and "cl == 0" in fo and "((cl == 1) && (p[0] == '.'))" in fo
       and "((cl == 2) && (p[0] == '.') && (p[1] == '.'))" in fo and "MST_FILE_MAX" in fo, "")
    sk = func_body(m, "Private int mst_sync_key(MST_CTX *cx, int kind, const char *acct, const char *root, const char *file, const char *id, int id_len)")
    ck("D10 mst_sync_key: a key too long to mirror is refused BEFORE any file is touched (MS_LONG), the account's record is read before the master's, the master is written only when it "
       "differs, a record the account lacks is removed from the master and from the state, and the state record is written only when its checksum differs",
       ordered(sk, "mst_keys(kind, acct, file, id, id_len, mkey, skey) < 0", "return MS_LONG;", "dh_read(adh,", "dh_read(mdh, mkey", "!mst_str_equal(rec, mrec)", "mst_mwrite(mdh, mkey")
       and ordered(sk, "if (!found) {", "mst_mdelete(mdh, mkey", "dh_delete(cx->st, skey") and ordered(sk, "mst_checksum(rec, cks);", "strcmp(cks, scks) != 0", "mst_put(cx->st, skey"), "")
    mk = func_body(m, "Private int mst_keys(int kind, const char *acct, const char *file, const char *id, int id_len, char *mkey, char *skey)")
    ck("D11 mst_keys: a master key must fit MAXIDLEN less the two characters of the state key (a master file holding a longer id cannot be opened again), and never exceed 255; the state key is the "
       "kind letter, an asterisk and the master key", "sysseg->maxidlen - 2" in mk and "MAX_KEY_LEN - 2" in mk and "skey[0] = (kind == MST_VOC) ? 'v' : 'd';" in mk and "skey[1] = '*';" in mk, "")
    cl = func_body(m, "Private int mst_classify(const char *canon, char *acct, size_t acctsz, char *file, size_t filesz)")
    ck("D12 the account of a path is the one whose directory is the nearest prefix of it (the table is sorted longest root first), the VOC is exactly <root>/voc, a dictionary is the path below "
       "the root without .dic, and a name with an asterisk is not mirrored",
       "if (a->rlen != b->rlen)" in func_body(m, "Private int mst_acc_cmp(const void *pa, const void *pb)") and "return (a->rlen > b->rlen) ? -1 : 1;" in func_body(m, "Private int mst_acc_cmp(const void *pa, const void *pb)")
       and 'strcmp(rel, "voc") == 0' in cl and "strchr(file, '*') != NULL" in cl and "strncasecmp(p + n - 4, \".dic\", 4)" in cl, "")
    cs = func_body(m, "Private bool mst_sync_account(MST_CTX *cx, const MST_ACC *a, MST_SYNCRES *res)")
    ck("D13 mst_sync_account: the VOC, then each dictionary the account holds with its own slice of the master keys, then the master keys of dictionaries it no longer has, then the state records "
       "no master key backs", ordered(cs, "mst_sync_file(cx, MST_VOC", "mst_sync_file(cx, MST_DICT", "mst_delete_keys(cx, MST_DICT, &gone)", "(void)mst_keys_of(cx, MST_IX_STATE, sub, &skeys)", "dh_delete(cx->st"), "")
    sf = func_body(m, "Private void mst_sync_file(MST_CTX *cx, int kind, const char *acct, const char *root, const char *file, const MST_IDS *mkeys, size_t prefixlen)")
    ck("D14 mst_sync_file: a file that cannot be opened or cannot be read through (as against one that is not there) leaves the master copies ALONE and counts an error - a copy is never "
       "deleted for want of being able to read the original; only a file that is ABSENT (the flag cx->last_absent, read at once) has its copies taken out",
       ordered(sf, "bool absent = cx->last_absent;", "mst_scan_ids(adh, &ids)", "else if ((adh != NULL) || !absent) {", "cx->errs++;", "return;")
       and re.search(r"return;\s*\} else \{\s*have_set = mst_set_build\(&set, &ids\);\s*\}", sf) is not None, "")
    af = func_body(m, "Private DH_FILE *mst_acct_file(MST_CTX *cx, int kind, const char *root, const char *file)")
    ck("D15 mst_acct_file tells 'no such file' from 'could not be opened': the file is ABSENT only when the open failed and stat of its %0 subfile says ENOENT; mst_sync_key, the check and the "
       "sync all look at it before they say anything about the records",
       "stat(sub, &sb) != 0) && (errno == ENOENT)" in af and "cx->last_absent = absent;" in af and "cx->h[i].absent = absent;" in af
       and ordered(sk, "} else if (!cx->last_absent) {", "cx->errs++;", "return MS_ERR;")
       and ordered(func_body(m, "Private void mst_check_file(MST_CTX *cx, MST_CHECK *ck, int kind, const char *acct, const char *root, const char *file, const MST_IDS *mkeys, size_t prefixlen)"),
                   "if ((adh == NULL) && !cx->last_absent) {", '"unreadable"', "return;"), "")

    # ---- K. the ops ---------------------------------------------------------------------------------------------------------------------
    rq = func_body(m, "void masters_request(const char *req, DESCRIPTOR *result)")
    ck("K1 masters_request: 'ready' and 'note' are answered BEFORE the administrator test; every other op comes after 'if (!admin)' returns MSA_REFUSED, and 'init' (which makes files) is after it too",
       ordered(rq, 'strcmp(op, "ready") == 0', 'strcmp(op, "note") == 0', "if (!admin) {", "mst_status(&out, MSA_REFUSED);", 'strcmp(op, "init") == 0', "mst_is_set_up()")
       and ordered(rq, "if (!admin) {", 'strcmp(op, "pending") == 0', 'strcmp(op, "drain") == 0', 'strcmp(op, "sync") == 0', 'strcmp(op, "drop") == 0', 'strcmp(op, "check") == 0'), "")
    ck("K2 ...admin is the user table's administrator flag", "bool admin = (my_uptr != NULL) && ((my_uptr->flags & USR_ADMIN) != 0);" in rq, "")
    ck("K3 ...the ops are exactly: ready note refusal init pending peek drain sync syncall syncbegin syncend drop check accounts (refusal is stage 2's, syncall the verifier's F7)",
       sorted(re.findall(r'strcmp\(op, "(\w+)"\) == 0', rq)) == sorted(["ready", "note", "refusal", "init", "pending", "peek", "drain", "sync", "syncall", "syncbegin", "syncend", "drop", "check", "accounts"]),
       repr(sorted(re.findall(r'strcmp\(op, "(\w+)"\) == 0', rq))))
    ck("K4 'note' adds a journal line for a path and nothing else (the op that an ordinary session may reach through !OSCOPY)",
       re.search(r'strcmp\(op, "note"\) == 0\) \{\s*masters_note_name\(arg, \'n\'\);\s*mst_status\(&out, MSA_OK\);\s*mst_answer\(result, &out\);\s*return;\s*\}', rq) is not None, "")
    chk = "".join(func_body(m, s) for s in ("Private void mst_check_file(MST_CTX *cx, MST_CHECK *ck, int kind, const char *acct, const char *root, const char *file, const MST_IDS *mkeys, size_t prefixlen)",
                                            "Private void mst_check_account(MST_CTX *cx, MST_CHECK *ck, const MST_ACC *a)", "Private void mst_check_orphans(MST_CTX *cx, MST_CHECK *ck)",
                                            "Private void mst_row(MST_CHECK *ck, const char *type, const char *acct, const char *what, const char *file, const char *id, int id_len)"))
    ck("K5 the check functions never change anything: no dh_write, dh_delete, dh_clear, mst_put, mst_sync_*, mst_delete_keys, ftruncate, chmod, unlink, rename or write in them",
       len(chk) > 800 and re.search(r"\b(dh_write|dh_delete|dh_clear|mst_put|mst_sync_key|mst_sync_file|mst_delete_keys|ftruncate|chmod|unlink|rename|write)\s*\(", chk) is None, "")
    ck("K6 the check reports the five kinds of finding: differs, missing, extra, nonwritable (a subfile without group write), toolong, and unreadable",
       all(('"%s"' % w) in chk for w in ("differs", "missing", "extra", "nonwritable", "toolong", "unreadable")) and "S_IWGRP" in func_body(m, "Private bool mst_group_writable(const char *dirpath)"), "")
    ck("K7 'syncbegin' notes the journal's size and puts BOTH flags down before the sync (a failure during the sync raises them again); 'syncend' drops the master keys of accounts that are not "
       "registered and drains from the noted position - so lines that arrived during the sync are applied and lines older than it (covered by the full sync) are not",
       ordered(rq, 'strcmp(op, "syncbegin") == 0', "__sync_fetch_and_and(&sysseg->masters_flags", 'strcmp(op, "syncend") == 0', "mst_drop_orphans(&cx)", "mst_drain(&cx, atol(arg), &dr)"), "")
    ck("K8 an account that is not in the register is answered MSA_NOACC by sync and check (the register is read again on every such question)",
       rq.count("MSA_NOACC") == 2 and rq.count("mst_acc_by_name(arg, &acc)") == 2, "")

    od = func_body(m, "Private long mst_drop_orphans(MST_CTX *cx)")
    oc = func_body(m, "Private void mst_check_orphans(MST_CTX *cx, MST_CHECK *ck)")
    ir = func_body(m, "Private bool mst_in_register(const char *name)")
    ck("K9 an account's copies are an orphan's only when the account is not in the register: an empty table (a register that could not be read) makes no orphan, and a name whose register "
       "RECORD exists is an account even if a transient failure kept it out of the table",
       ordered(od, "mst_acc_load();", "if (acc_n == 0)", "return 0;", "mst_in_register(name)") and ordered(oc, "mst_acc_load();", "if (acc_n == 0)", "return;", "mst_in_register(name)")
       and "mst_acc_find(name) >= 0" in ir and '"%s%caccounts%c%s"' in ir and "stat(p, &sb) == 0" in ir and "mst_valid_account_name(name)" in ir, "")

    # ---- B. the BASIC -------------------------------------------------------------------------------------------------------------------
    mp = B("masters")
    ck("B1 the verb program tests for the administrator BEFORE it calls the kernel, and says 2001; it dispatches on the first word of the sentence in lower case, for exactly three verbs",
       ordered(mp, "if not(kernel(K$ADMINISTRATOR, -1)) then", "stop sysmsg(2001)", "verb = downcase(field(words, ' ', 1))", "kernel(K$MASTERS")
       and mp.find("kernel(K$MASTERS") > mp.find("stop sysmsg(2001)") > mp.find("kernel(K$ADMINISTRATOR") >= 0 and sorted(re.findall(r"case verb = '([\w.]+)'", mp)) == ["check.masters", "list.master.pending", "sync.masters"], "")
    ck("B2 SYNC.MASTERS: sets up first (!masters_setup), applies the journal before a one-account sync, and for no account notes the position (syncbegin), syncs every account in ONE call (syncall, "
       "verifier F7) and finishes with syncend with that position; it audits in lower case",
       ordered(mp, "call !masters_setup(rep)", "gosub drain.journal", "'sync.masters account='", "gosub sync.one") and ordered(mp, "'syncbegin'", "kernel(K$MASTERS, 'syncall')", "sysmsg(11566", "'syncend' : @fm : s0")
       and mp.count("'syncall'") == 1 and "'accounts'" not in mp
       and "kernel(K$AUDIT, 'sync.masters account=' : account)" in mp and "kernel(K$AUDIT, 'sync.masters account=*')" in mp, "")
    ck("B3 CHECK.MASTERS asks whether the master files are set up before it drains or checks (11564 if not), drains first, and prints a difference row per finding, the flags, and the summary",
       ordered(mp, "do.check:", "kernel(K$MASTERS, 'ready')", "sysmsg(11564)", "gosub drain.journal", "'check'", "sysmsg(11570", "sysmsg(11572", "sysmsg(11573", "sysmsg(11568", "sysmsg(11569"), "")
    ck("B4 LIST.MASTER.PENDING does not drain (it asks 'pending' and 'peek', never 'drain')", "'pending'" in between(mp, "do.pending:", "end\n") and "'drain'" not in between(mp, "do.pending:", "end\n"), "")
    vt = {v: srcs.get("voc:" + v) for v in ("sync.masters", "check.masters", "list.master.pending")}
    ck("B5 the three verbs are records of voc_template (V, CA, $masters) and of NO other VOC source: not in newvoc",
       all(t is not None and t.split("\n")[:3] == ["V", "CA", "$masters"] for t in vt.values())
       and not any(v in srcs["newvoc.list"].split("\n") for v in vt) and all(v in srcs["voc_template.list"].split("\n") for v in vt), "")
    ms = B("masters_setup")
    ck("B6 !masters_setup makes the three files BY PATH under @sdsys (so the account the administrator is in does not matter), a dictionary for each with the @id record, an F entry in the SDSYS VOC "
       "only when there is none (it never overwrites one), and only then asks the kernel to set modes and make the journal",
       ordered(ms, "openpath @sdsys:@ds:'voc' to sv", "kernel(K$MASTERS, 'init')", "dp = @sdsys : @ds : nm", "create.file dp dynamic", "create.file dp : '.dic' dynamic", "write 'D' : @fm : '0'",
               "read x from sv, nm else", "write 'F' : @fm : nm", "kernel(K$MASTERS, 'init')") and ms.count("kernel(K$MASTERS, 'init')") == 2
       and "KEEPCASE" not in ms.upper() and ms.count("write 'F'") == 1, "")
    um = B("upgrade_masters")
    ck("B7 upgrade_masters sets up first, notes the position, copies every registered account in ONE call (syncall, verifier F7), ends with syncend, counts failures, and prints COMPLETE only when none "
       "failed",
       ordered(um, "call !masters_setup(rep)", "'syncbegin'", "kernel(K$MASTERS, 'syncall')", "failed += 1", "'syncend' : @fm : s0", "if failed = 0 then crt 'COMPLETE'")
       and um.count("COMPLETE") == 1 and um.count("'syncall'") == 1 and "'accounts'" not in um, "")
    ca = B("create_account")
    ck("B8 create_account: the sync of the new account comes AFTER the register record is written (the hook cannot tell whose the VOC is until then) and its answer is not looked at",
       ordered(ca, "write acc.rec to acc.f, acc.name", "void kernel(K$MASTERS, 'sync' : @fm : downcase(acc.name))") and ca.count("kernel(K$MASTERS") == 1, "")
    da = B("delacc")
    ck("B9 delacc: the drop comes AFTER the register delete and after the audit line (only a deletion that completed is followed)",
       ordered(da, "delete acc.f, acc.name", "kernel(K$AUDIT, 'delete.account account='", "void kernel(K$MASTERS, 'drop' : @fm : downcase(acc.name))") and da.count("kernel(K$MASTERS") == 1, "")
    ra = B("restorea")
    ck("B10 restorea: the sync of a restored account comes after its audit line, inside the loop's success branch", ordered(ra, "kernel(K$AUDIT, 'restore.account account='", "void kernel(K$MASTERS, 'sync' : @fm : downcase(acc.name))", "failed += 1"), "")
    ck("B11 !oscopy and !ioscopy tell the journal the target's path after the copy ('note'), which any $internal program may do",
       ordered(B("_oscopy"), "os.execute cmd", "void kernel(K$MASTERS, 'note' : @fm : target)", "return") and ordered(B("_ioscopy"), "os.execute", "void kernel(K$MASTERS, 'note' : @fm : target)", "return")
       and B("_oscopy").count("kernel(K$MASTERS") == 1 and B("_ioscopy").count("kernel(K$MASTERS") == 1, "")
    ck("B12 none of the new BASIC runs a shell command or opens an operating system file by a name it was handed (the files are made by path under @sdsys and the kernel does the rest)",
       all(re.search(r"\b(os\.execute|sh\b|execute)\b", B(n), re.I) is None for n in ("masters", "masters_setup", "upgrade_masters")), "")

    # ---- I. the installer ---------------------------------------------------------------------------------------------------------------
    ins = c["sh:installsdcore.sh"]
    ck("I1 the installer runs upgrade_masters as root, on every install (outside the accounts_kept test), after upgrade_editgates and BEFORE the register is chowned to sdsys, and reports a run that "
       "did not print COMPLETE",
       ordered(ins, "-internal RUN gpl.bp upgrade_editgates", "-internal RUN gpl.bp upgrade_masters", 'sudo chown -R sdsys:sdusers "$sdsysdir/accounts"')
       and re.search(r"^om_out=\$\(sudo \"\$sdsysdir/bin/sd\" -internal RUN gpl\.bp upgrade_masters 2>&1\) \|\| om_rc=\$\?$", ins, re.M) is not None
       and 'grep -qx \'[[:space:]]*COMPLETE[[:space:]]*\'' in between(ins, "om_out=", "fi\n") and "WARNING: the master files were not all set up or filled." in ins
       and 'if [ "$om_rc" -ne 0 ] || ! printf' in ins, "")

    # ---- R. wiring ----------------------------------------------------------------------------------------------------------------------
    rg_ = c["txt:regress.sh"]
    am = re.search(r'^ALL_SUITES="([^"]*)"', rg_, re.M)
    mp_ = c["txt:regress-map.txt"]
    ck("R1 regress.sh lists the suite 'masters' in ALL_SUITES, and regress-map.txt has a rule for each new file of this feature",
       am is not None and "masters" in am.group(1).split()
       and all(re.search(r"^%s\s*:" % re.escape(p), mp_, re.M) for p in ("gplsrc/masters.c", "sdsys/gpl.bp/masters", "sdsys/gpl.bp/masters_setup", "sdsys/gpl.bp/upgrade_masters",
                                                                        "sdsys/voc_template/sync.masters", "sdsys/voc_template/check.masters", "sdsys/voc_template/list.master.pending",
                                                                        "sdsys/gpl.bp/create_account")), "")
    ck("R2 the kernel files the feature touches select the suite: dh_*.c, dh.h, op_dio1.c, op_dio2.c, op_xfun.c, op_kernel.c, keys.h, sd.h, sysseg, gpl.src and int$keys.h",
       all(re.search(r"^%s\s*:.*\bmasters\b" % re.escape(p), mp_, re.M) for p in ("gplsrc/dh_*.c", "gplsrc/dh.h", "gplsrc/op_dio1.c", "gplsrc/op_dio2.c", "gplsrc/op_xfun.c", "gplsrc/op_kernel.c",
                                                                                  "gplsrc/keys.h", "gplsrc/sd.h", "gplsrc/sysseg.[ch]", "gpl.src", "sdsys/gpl.bp/int$keys.h")), "")
    ck("R3 the test files exist (this one, the sandbox suite, the installer block test and the witness)", all(srcs.get("file:" + t) for t in ("sandbox-masters.py", "test-masters-units.py", "witness-masters.sh", "test-install-sdsysgroups.sh")), "")

    # ===== S. STAGE 2, MASTER TO ACCOUNT (D7) ========================================================================================================
    # ---- S1-S4 numbers and messages -------------------------------------------------------------------------------------------------------------
    sdh = C("sd.h")
    ck("S1 DHE_MASTER_REFUSED is 8910, defined in sd.h and NOT in err.h (err.h is generated into SYSCOM/ERR.H and ERRTEXT.H); no #define of err.h has that value",
       re.search(r"#define DHE_MASTER_REFUSED 8910\b", sdh) is not None and "DHE_MASTER_REFUSED" not in C("err.h") and not re.findall(r"#define\s+\w+\s+8910\b", C("err.h")), "")
    bits2 = [dh.get(k) for k in ("DHF_MST_NOMASTER", "DHF_MST_VM", "DHF_MST_DM")]
    ck("S2 dh.h: DHF_MST_NOMASTER 0x20000000, DHF_MST_VM 0x40000000, DHF_MST_DM 0x80000000 - one bit each in the INTERNAL half of the word, none shared with another flag",
       bits2 == [0x20000000, 0x40000000, 0x80000000] and len(set(dh.values())) == len(dh.values()), repr(bits2))
    t2 = {n: srcs.get("msg:%d" % n) for n in range(MSG2_FIRST, MSG2_LAST + 1)}
    cexp = {11580: 1, 11581: 2, 11582: 2, 11583: 2, 11584: 2, 11585: 2, 11586: 2, 11587: 3, 11588: 1, 11589: 1, 11590: 1, 11591: 2, 11592: 2, 11595: 1, 11596: 1}   # the %s places each C message has
    c_ok = all(t2.get(n) is not None and t2[n].count("\n") == 1 and t2[n].count("%s") == k and not re.findall(r"%[^s]", t2[n]) for n, k in cexp.items())
    # THE ROOM A MESSAGE HAS (verifier, low): k_error puts it after a 10-character prefix in a buffer of MAX_ERROR_LINES * MAX_EMSG_LEN + 1, so 231 characters, ARGUMENTS INCLUDED.
    # The part a reader needs most is "Nothing was changed", and a sentence cut short loses it.  The worst argument each %s can be given: the key as shown (MST_SHOWN_MAX, 60), an
    # account (MAX_ACCOUNT_NAME_LEN, 32), a group (sdu_ or sdg_ and an account: 36), what the account lacks or cannot be written (60), a user number or a status (6), a reason (24).
    sd_ = C("sddefs.h")
    try:
        room = int(re.search(r"#define\s+MAX_ERROR_LINES\s+(\d+)", sd_).group(1)) * int(re.search(r"#define\s+MAX_EMSG_LEN\s+(\d+)", sd_).group(1)) + 1 - 10
        shown = int(re.search(r"#define MST_SHOWN_MAX (\d+)", m).group(1))
        acct_ = int(re.search(r"#define\s+MAX_ACCOUNT_NAME_LEN\s+(\d+)", sd_).group(1))
    except (AttributeError, ValueError):
        room, shown, acct_ = 0, 0, 0
    worst_args = {11580: (shown,), 11581: (shown, acct_), 11582: (shown, 24), 11583: (shown, acct_), 11584: (shown, 6), 11585: (shown, 60), 11586: (shown, acct_ + 4), 11587: (shown, acct_ + 4, acct_ + 4),
                  11588: (shown,), 11589: (shown,), 11590: (shown,), 11591: (shown, 24), 11592: (shown, 24), 11595: (shown,), 11596: (shown,)}
    worst = {n: len(t2[n].rstrip("\n").replace("%s", "")) + sum(worst_args[n]) for n in cexp if t2.get(n)}
    short = room == 231 and shown == 60 and all(worst[n] <= room for n in worst)
    ck("S3 messages 11579 to 11596 exist, each one line.  11580 to 11592, 11595 and 11596 are written for C (printf's %s, exactly the places masters.c passes, no other conversion, none with %1) and "
       "FIT k_error's room (231 characters) with the longest argument each place can be given (the key is cut at 60); 11579 (%1 %2), 11593 (none) and 11594 (%1) are BASIC and have no %s; "
       "and every refusal that leaves the account as it was says so (\"Nothing was changed\") - the saves not delivered, in the sentence",
       all(t2.get(n) is not None for n in range(MSG2_FIRST, MSG2_LAST + 1)) and c_ok and short and "%s" not in (t2.get(11579) or "") and "%2" in (t2.get(11579) or "") and "%s" not in (t2.get(11593) or "")
       and "%" not in (t2.get(11593) or "") and "%1" in (t2.get(11594) or "") and "%s" not in (t2.get(11594) or "")
       and all("Nothing was changed" in (t2.get(n) or "") for n in (11580, 11581, 11582, 11583, 11584, 11585, 11586, 11587, 11589, 11592, 11595, 11596)),
       repr(([n for n in cexp if t2.get(n) is None or t2[n].count("%s") != cexp[n]], {n: w for n, w in worst.items() if w > room}, room, shown)))
    ck("S3a ...in lower case wherever a command word is written: sync.masters, check.masters, sd-elevate, sdsys-join, voc_master; no verb in capitals",
       all(re.search(r"\b[A-Z]{3,}\.[A-Z]{3,}\b", t) is None for t in t2.values() if t) and "sd-elevate sdsys-join" in " ".join(t for t in t2.values() if t)
       and "sync.masters" in (t2.get(11583) or "") + (t2.get(11588) or ""), "")
    msgnum = {mm.group(1): int(mm.group(2)) for mm in re.finditer(r"#define (MSG_\w+) (\d+)", m)}
    calls = re.findall(r"mst_refuse\((MSG_\w+),\s*([^,]+),\s*([^,]+),\s*([^)]+)\)", m) + re.findall(r"mst_deliver_stop\(&cx, &fv, took, rid, rid_len, (MSG_\w+),\s*([^,]+),\s*([^,]+),\s*([^)]+)\)", m)
    ck("S4 every mst_refuse call passes at least as many real arguments (not NULL) as its message has %s places, never more than three, and every message of 11580-11592, 11595 and 11596 is used by one",
       len(calls) >= 18 and all(msgnum.get(n) in cexp and sum(1 for a in (x, y, z) if a.strip() != "NULL") >= cexp[msgnum[n]] for n, x, y, z in calls)
       and {msgnum[n] for n, _, _, _ in calls if n in msgnum} == set(cexp), repr(sorted({n for n, x, y, z in calls if msgnum.get(n) not in cexp or sum(1 for a in (x, y, z) if a.strip() != "NULL") < cexp.get(msgnum.get(n), 0)})))

    # ---- S5-S8 where the DH layer and the opcodes ask ----------------------------------------------------------------------------------------
    ck("S5 dh_write.c asks masters_before_write ONCE, first of all - behind the one-bit test, before dh_err is cleared and before any buffer is taken - and a refusal returns FALSE with dh_err the refusal",
       dw.count("masters_before_write(") == 1 and ordered(dw, "if (!(dh_file->flags & DHF_MST_NOMASTER)) {", "masters_before_write(dh_file, id, id_len, new_data)", "dh_err = master_refusal;", "return FALSE;",
                                                        "dh_err = 0;", "k_alloc(16, group_bytes)"), "")
    ck("S6 dh_del.c asks masters_before_delete ONCE, first of all, the same way",
       dd.count("masters_before_delete(") == 1 and ordered(dd, "if (!(dh_file->flags & DHF_MST_NOMASTER)) {", "masters_before_delete(dh_file, id, id_len)", "dh_err = master_refusal;", "return FALSE;",
                                                        "dh_err = 0;", "k_alloc(5, group_bytes)"), "")
    d3 = C("op_dio3.c")
    ck("S7 op_dio3.c: a WRITE or a DELETE of a master record inside a transaction is refused BEFORE it reaches the transaction's cache (masters_txn_refusal, once in each, ahead of txn_write / txn_delete), "
       "with status -DHE_MASTER_REFUSED; both tails print masters_refusal_text() through \"%s\" (not as a format) in place of the generic error",
       d3.count("masters_txn_refusal(") == 2
       and re.search(r"if \(txn_id != 0\) \{[^{}]*if \(masters_txn_refusal\(dh_file, id, id_len\) != 0\) \{\s*process\.status = -DHE_MASTER_REFUSED;\s*goto exit_op_write;\s*\}\s*if \(!txn_write\(fvar, id, id_len, str\)\)", d3) is not None
       and re.search(r"if \(masters_txn_refusal\(dh_file, id, id_len\) != 0\)\s*process\.status = -DHE_MASTER_REFUSED;\s*else\s*txn_delete\(fvar, id, id_len\);", d3) is not None
       and d3.count('k_error("%s", masters_refusal_text())') == 2 and d3.count("process.status == -DHE_MASTER_REFUSED") == 2, "")
    ck("S8 dh_creat.c calls masters_fix_modes(path) ONCE, after the file is made and journalled, and never as an error: after masters_note_name, before the exit label",
       dcr.count("masters_fix_modes(") == 1 and ordered(dcr, "masters_note_name(path, 'n');", "masters_fix_modes(path);", "exit_dh_create_file:"), "")

    # ---- S9-S11 the classification and the two refusals --------------------------------------------------------------------------------------
    bw = func_body(m, "int masters_before_write(DH_FILE *dh, char *id, int id_len, STRING_CHUNK *data)")
    mkd = func_body(m, "Private int mst_master_kind(DH_FILE *dh)")
    ck("S9 masters_before_write does nothing for a file that is not a delivering master, and nothing while the stage 1 code is writing (mst_inside): the bit test, the classification, the inside test, only then mst_deliver",
       ordered(bw, "DHF_MST_NOMASTER", "mst_master_kind(dh)", "mst_inside > 0", "return mst_deliver(kind, id, id_len, data);"), "")
    ck("S10 mst_master_kind: the file is voc_master or dict_master by its exact path (mst_master_which 1 or 2) and remembered in the flags; master_state (3) and everything else is NOMASTER - "
       "a write to master_state is never taken for a save",
       ordered(mkd, "mst_master_which((const char *)FPtr(dh->file_id)->pathname)", "w == 1", "DHF_MST_VM", "w == 2", "DHF_MST_DM", "dh->flags |= DHF_MST_NOMASTER;") and "w == 3" not in mkd and "w >= 1" not in mkd, "")
    bd = func_body(m, "int masters_before_delete(DH_FILE *dh, char *id, int id_len)")
    bt = func_body(m, "int masters_txn_refusal(DH_FILE *dh, char *id, int id_len)")
    ck("S11 masters_before_delete refuses EVERY delete of a master record (message 11588), whoever asks, except while the stage 1 code is deleting; masters_txn_refusal refuses a write or delete inside a "
       "transaction (11589) the same way; neither takes a lock or writes",
       ordered(bd, "DHF_MST_NOMASTER", "mst_master_kind(dh) == 0", "mst_inside > 0", "return mst_refuse(MSG_DELETE") and ordered(bt, "DHF_MST_NOMASTER", "mst_master_kind(dh) == 0", "mst_inside > 0", "return mst_refuse(MSG_TXN")
       and re.search(r"\b(dh_write|dh_delete|lock_record|audit_message|mst_put)\s*\(", bd + bt) is None and "USR_ADMIN" not in bd + bt, "")

    # ---- S12-S15 the delivery -----------------------------------------------------------------------------------------------------------------
    dv = func_body(m, "Private int mst_deliver(int which, char *id, int id_len, STRING_CHUNK *data)")
    ck("S12 mst_deliver does its steps in the order D7 gives: the administrator, the key, the registered account (a COPY of its table entry), the account's file, the permission test, the keys, the "
       "try-lock, the account's record against the record the session READ (verifier F3; master_state only for a key it did not read), the write with the comparison armed (F4), master_state, the "
       "unlock, the audit line",
       ordered(dv, "USR_ADMIN", "memchr(id, '*'", "mst_valid_account_name(acct)", "mst_acc_by_name(acct, &acc)", "mst_acct_file(&cx, which", "mst_write_check(path, gname", "mst_keys(which, a->name",
               "check_lock(&fv", "lock_record(&fv", "dh_read(adh", "mst_read_find(which", "mst_state_get(&cx, skey", "masters_cas_on = 1;", "dh_write(adh", "masters_cas_on = 0;",
               "mst_checksum(data, ncks)", "mst_put(cx.st, skey", "mst_read_put(which", "unlock_record(&fv", "audit_message(line)"), "")
    ck("S12a ...the administrator test is the first thing it does and the answer is a refusal (MSG_NOTADMIN) for anyone else",
       re.search(r"mst_shown\(keytxt, sizeof\(keytxt\), id, id_len\);\s*/\*[^*]*\*/\s*if \(\(my_uptr == NULL\) \|\| !\(my_uptr->flags & USR_ADMIN\)\)\s*return mst_refuse\(MSG_NOTADMIN", dv) is not None
       or re.search(r"if \(\(my_uptr == NULL\) \|\| !\(my_uptr->flags & USR_ADMIN\)\)\s*return mst_refuse\(MSG_NOTADMIN", dv) is not None, "")
    ck("S12c ...the permission test is made TWICE and the second is the preflight: after the account's file is opened and before the keys and the lock, a refusal goes to the reasons (goto refuse_rights)",
       dv.count("mst_write_check(") == 2 and ordered(dv, "mst_acct_file(&cx, which", "goto refuse_rights;", "why = mst_write_check(path, gname, sizeof(gname));", "if (why != MST_W_OK) {", "goto refuse_rights;", "mst_keys(which, a->name"), "")
    ck("S12b ...the key is cut at the FIRST asterisk (account), and for a dictionary at the next one (file) - the rest is the record id, which may hold asterisks - and the file name must pass the rule "
       "the journal uses (no .., no slash at the front, no control character)",
       ordered(dv, "p1 = memchr(id, '*', (size_t)id_len);", "p2 = memchr(p1 + 1, '*'", "mst_file_ok(file)") and "strchr(" not in dv and "strrchr(" not in dv and "strtok" not in dv, "")
    ck("S13 THE TRY-LOCK: lock_record is called ONCE with update TRUE, transaction 0 and no_wait TRUE (it returns at once; the account's process may hold the record and be waiting on the master); a lock this "
       "process holds already (check_lock) is not taken again and, below, not let go (took); a lock that cannot be had is a refusal (MSG_LOCKED) before anything is read or written",
       len(re.findall(r"(?<![\w])lock_record\(", dv)) == 1 and "lock_record(&fv, (char *)rid, (int16_t)rid_len, TRUE, 0, TRUE)" in dv
       and re.search(r"if \(!check_lock\(&fv, \(char \*\)rid, \(int16_t\)rid_len\)\) \{\s*lk = lock_record\([^;]*;\s*if \(lk != 0\) \{[^{}]*if \(lk > 0\)\s*return mst_refuse\(MSG_LOCKED[^;]*;\s*"
                     r"return mst_refuse\(MSG_NOLOCK[^;]*;[^{}]*\}\s*took = TRUE;", dv) is not None
       and "Sleep(" not in dv and "pc--" not in dv, "")
    ck("S13a ...the file variable the lock is taken on belongs to no program: type DYNAMIC_FILE, the account file's file_id, index -2",
       "fv.type = DYNAMIC_FILE;" in dv and "fv.file_id = adh->file_id;" in dv and "fv.index = -2;" in dv, "")
    after_lock = dv[dv.find("lock_record("):dv.find("audit_message(line);")]
    stop_ = func_body(m, "Private int mst_deliver_stop(MST_CTX *cx, FILE_VAR *fv, bool took, const char *rid, int rid_len, int msg, const char *a, const char *b, const char *c)")
    stops = list(re.finditer(r"return mst_deliver_stop\(&cx, &fv, took, rid, rid_len, (\w+)", after_lock))
    ck("S13b ...and every refusal after the lock goes out through mst_deliver_stop, which lets the lock go only when this call took it (`if (took)`), closes what was opened and then refuses "
       "(msg 0: with the words already in the buffer), so that no refusal can leave the lock held or the files open; the success path lets it go behind the same `if (took)`; unlock_record is "
       "called in those two places and nowhere else",
       ordered(stop_, "if (took)", "unlock_record(fv", "mst_ctx_close(cx);", "if (msg == 0)", "return DHE_MASTER_REFUSED;", "return mst_refuse(msg, a, b, c);")
       and dv.count("unlock_record(") == 1 and len(re.findall(r"if \(took\)\s*unlock_record\(&fv", dv)) == 1 and m.count("unlock_record(") == 2
       and {x.group(1) for x in stops} >= {"MSG_NOSTATE", "MSG_CHANGED", "MSG_NOTREAD", "MSG_WRITEFAIL", "0"} and len(stops) >= 6
       and re.search(r"return mst_refuse\(", after_lock.replace("return mst_refuse(MSG_LOCKED", "").replace("return mst_refuse(MSG_NOLOCK", "")) is None, "")
    ck("S14 THE COMPARISON (verifier F3): the account's record is read after the lock and its checksum compared with the checksum of the record THIS SESSION READ (mst_read_find; masters_note_read put it "
       "there) - not with master_state, which is the version of the last DRAIN; a difference is a refusal (MSG_CHANGED) before anything is written; a key the session did not read may CREATE a "
       "record (the account has none and master_state has none) and may not overwrite one (MSG_NOTREAD) or put back one the account deleted (MSG_CHANGED); the state record is written ONCE, only "
       "after dh_write succeeded, and so is the read table",
       ordered(dv, "lock_record(", "rec = dh_read(adh", "mst_checksum(rec, cks);", "cks[0] = '\\0';", "mst_read_find(which", "strcmp(cks, rd->cks) != 0", "MSG_CHANGED",
               "mst_state_get(&cx, skey, mk + 2, scks);", "MSG_NOTREAD", "scks[0] != '\\0'", "MSG_CHANGED", "masters_cas_on = 1;", "wok = dh_write(adh")
       and dv.count("mst_put(") == 1 and dv.count("dh_write(") == 1 and dv.count("mst_read_put(") == 1 and ordered(dv, "wok = dh_write(adh", "MSG_WRITEFAIL", "mst_put(cx.st", "mst_read_put(which"), "")
    ck("S14c THE COMPARISON IS MADE AGAIN INSIDE THE WRITE (verifier F4): mst_deliver arms it just before the one dh_write of the account's file (the file, the key, the checksum it accepted, and "
       "masters_cas_on) and disarms it just after, whatever came back; masters_cas_check answers only for the file and key armed, spends the arming when it answers, takes a missing record to "
       "have the checksum \"\", and refuses with MSG_CHANGED; dh_write asks it when it has FOUND the record (group locked, nothing changed yet, the record read from the group buffer by "
       "dh_read_record) and when it has found there is NONE (before add_record), and gives back a big record's new chain when it refuses",
       ordered(dv, "snprintf(mst_cas.expect", "mst_cas.dh = adh;", "masters_cas_on = 1;", "wok = dh_write(adh", "masters_cas_on = 0;")
       and 'snprintf(mst_cas.expect, sizeof(mst_cas.expect), "%s", cks);' in dv and "memcpy(mst_cas.id, rid, (size_t)rid_len);" in dv
       and ordered(func_body(m, "int masters_cas_check(DH_FILE *dh, const char *id, int id_len, STRING_CHUNK *current, bool found)"), "if (!masters_cas_on || (dh != mst_cas.dh)", "(id_len != mst_cas.idlen)",
                   "memcmp(id, mst_cas.id, (size_t)id_len) != 0", "return 0;", "masters_cas_on = 0;", "if (found)", "mst_checksum(current, cks);", "cks[0] = '\\0';", "strcmp(cks, mst_cas.expect) == 0",
                   "return mst_refuse(MSG_CHANGED")
       and ordered(C("dh_write.c"), "if (found) {", "ak_mode = AK_MOD;", "if (masters_cas_on) {", "dh_read_record(dh_file, rec_ptr)", "masters_cas_check(dh_file, id, id_len, cas_cur, TRUE)",
                   "dh_free_big_rec(dh_file, new_big_rec_head, NULL)", "goto exit_dh_write;", "memcpy(stored_id, rec_ptr->id, id_len);")
       and ordered(C("dh_write.c"), "} while (1);", "masters_cas_check(dh_file, id, id_len, NULL, FALSE)", "dh_free_big_rec(dh_file, new_big_rec_head, NULL)", "goto exit_dh_write;", "add_record:")
       and C("dh_write.c").count("masters_cas_check(") == 2 and "masters_cas_on" in C("sd.h") and "masters_cas_check" in C("sd.h"), "")
    nr_ = func_body(m, "void masters_note_read(DH_FILE *dh, const char *id, int id_len, STRING_CHUNK *rec, int err)")
    d3_ = C("op_dio3.c")
    ck("S14d WHAT THE SESSION READ (verifier F3): op_dio3.c tells masters_note_read of every read of a DYNAMIC file, once, right after the dh_read and before the status is looked at, behind the one-bit test; "
       "masters_note_read does nothing for a file that is not voc_master or dict_master, takes the checksum of the record that came back (or \"\" for a record that was not there, and nothing for any "
       "other failure), and keeps it per key and kind in a ring of 128, in this process's memory only; a key read again replaces its entry",
       d3_.count("masters_note_read(") == 1 and ordered(d3_, "str = dh_read(dh_file, id, id_len, actual_id);", "if (!(dh_file->flags & DHF_MST_NOMASTER))", "masters_note_read(dh_file, id, id_len, str, dh_err);", "switch (dh_err) {")
       and ordered(nr_, "DHF_MST_NOMASTER", "mst_master_kind(dh)", "mst_checksum(rec, cks);", "DHE_RECORD_NOT_FOUND", "cks[0] = '\\0';", "return;", "mst_read_put(kind, id, id_len, cks);")
       and "#define MST_READ_N 128" in m and ordered(func_body(m, "Private void mst_read_put(int kind, const char *id, int id_len, const char *cks)"), "mst_read_find(kind, id, id_len)",
                                                                                              "mst_read_next = (mst_read_next + 1) % MST_READ_N;", "memcpy(r->id, id,"), "")
    ck("S14a ...the account's file is written by dh_write like any other writer (so it is journalled, and its indices are kept) and by nothing else: no open(), fopen(), write(), rename(), chmod(), unlink() "
       "and no mst_inside in mst_deliver",
       re.search(r"(?<![\w_])(open|fopen|openat|creat|rename|chmod|fchmod|unlink|truncate|ftruncate|system|execl|execv|popen)\s*\(", dv) is None and re.search(r"(?<![\w_])write\s*\(", dv) is None
       and "mst_inside" not in dv, "")
    ck("S15 THE AUDIT LINE: written once, after the write and after the lock is given back, in lower case, 'master edit account=%s file=%s id=%s', through audit_message (which adds the user and the "
       "process); a refused save writes none (the one call is after every refusal)",
       dv.count("audit_message(") == 1 and 'snprintf(line, sizeof(line), "master edit account=%s file=%s id=%s", a->name, filetxt, idtxt);' in dv
       and ordered(dv, "wok = dh_write(adh", "mst_put(cx.st", "unlock_record(&fv", 'snprintf(line, sizeof(line), "master edit account=', "audit_message(line);", "return 0;")
       and "return mst_refuse(" not in dv[dv.find("audit_message(line);"):dv.find("refuse_rights:")], "")

    # ---- S16 the stage 1 writes are marked ------------------------------------------------------------------------------------------------------
    mww = func_body(m, "Private bool mst_mwrite(DH_FILE *dh, char *key, int16_t klen, STRING_CHUNK *rec)")
    mdd = func_body(m, "Private bool mst_mdelete(DH_FILE *dh, char *key, int16_t klen)")
    ck("S16 the stage 1 code's own writes to the masters go through mst_mwrite / mst_mdelete, which raise mst_inside for the ONE call (up before, down after, no code in between); nothing else in masters.c "
       "raises it, and no dh_write or dh_delete outside those two (and mst_put, the state file's, and the delivery's own) names a master",
       ordered(mww, "mst_inside++;", "dh_write(dh, key, klen, rec)", "mst_inside--;") and ordered(mdd, "mst_inside++;", "dh_delete(dh, key, klen)", "mst_inside--;")
       and len(re.findall(r"mst_inside\+\+", m)) == 2 and len(re.findall(r"mst_inside--", m)) == 2 and re.search(r"dh_(write|delete)\((mdh|cx->vm|cx->dm|cx->h)", m) is None
       and m.count("mst_mwrite(") >= 2 and m.count("mst_mdelete(") >= 4, "")

    # ---- S17 can this session write the file ---------------------------------------------------------------------------------------------------
    wc = func_body(m, "Private int mst_write_check(const char *dirpath, char *gname, size_t gsz)")
    wy = func_body(m, "Private int mst_write_why(const struct stat *sb)")
    gw = func_body(m, "Private bool mst_group_writable(const char *dirpath)")
    ck("S17 mst_write_check asks the operating system (access): search on the account file's directory, write on %0 and on %1, BEFORE any lock or write; the reason is read off the mode and the group "
       "lists - the owner's class first, then the group bit, then the groups this process was STARTED with (getgroups), then /etc/group's list for the user (stale session) - and the four words are "
       "mode, stale-session, not-a-member, no-write",
       ordered(wc, 'snprintf(p, sizeof(p), "%s", dirpath)', 'snprintf(p, sizeof(p), "%s/%%%d", dirpath, i - 1)', "access(p, (i == 0) ? X_OK : W_OK)", "mst_write_why(&sb)")
       and ordered(wy, "sb->st_uid == geteuid()", "S_IWUSR", "MST_W_MODE", "sb->st_mode & S_IWGRP", "mst_gid_in_groups(sb->st_gid)", "mst_user_listed(sb->st_gid)", "MST_W_STALE", "MST_W_NOTMEMBER")
       and all(w in m for w in ('"mode"', '"stale-session"', '"not-a-member"', '"no-write"')) and "NGROUPS_MAX" not in m.replace("limits.h", "") and "getgroups(0, NULL)" in m, "")
    ck("S17a ...a refusal for each reason says it in the words of its message: stale (11586), not a member (11587), anything else the mode (11585); the permission test comes BEFORE the lock",
       ordered(dv, "mst_write_check(path, gname", "check_lock(&fv") and re.search(r"case MST_W_STALE:\s*return mst_refuse\(MSG_STALE", dv) is not None
       and re.search(r"case MST_W_NOTMEMBER:\s*return mst_refuse\(MSG_NOTMEMBER, keytxt, gname, gname\)", dv) is not None and re.search(r"default:\s*return mst_refuse\(MSG_MODE", dv) is not None, "")
    ck("S17b ...CHECK.MASTERS: a VOC or dictionary whose DIRECTORY lacks group write and search, or whose %0 or %1 lacks group write, is nonwritable; one whose modes are right and which this session cannot write is "
       "norights, with the reason as the last word - and the two are never both said of one file",
       re.search(r"\(sb\.st_mode & \(S_IWGRP \| S_IXGRP\)\) != \(S_IWGRP \| S_IXGRP\)", gw) is not None and re.search(r"if \(!\(sb\.st_mode & S_IWGRP\)\)", gw) is not None
       and re.search(r'if \(strcasecmp\(acct, MST_SYSTEM_ACCOUNT\) != 0 && !mst_group_writable\(path\)\) \{\s*mst_row\(ck, "nonwritable", acct, what, file, NULL, 0\);\s*\} else \{[^}]*mst_write_check\(path, gname, sizeof\(gname\)\)[^}]*"norights"', m) is not None
       and '#define MST_SYSTEM_ACCOUNT "sdsys"' in m, "")
    ck("S17c ...and the BASIC prints the hint (11593) when a nonwritable or norights row is among the rows, once, and the verb program still stops nothing: the hint is a display",
       ordered(B("masters"), "if ans<i, 1> = 'nonwritable' or ans<i, 1> = 'norights' then hint = 1", "if hint then display sysmsg(11593)") and B("masters").count("sysmsg(11593)") == 1, "")

    # ---- S18 the modes of what SD makes --------------------------------------------------------------------------------------------------------
    fm = func_body(m, "void masters_fix_modes(const char *path)")
    ck("S18 masters_fix_modes adds GROUP bits only (g+rwx and setgid on the directory, g+rw on %0 and %1) and takes nothing away: the bits OR-ed in are S_IRWXG | S_ISGID and S_IRGRP | S_IWGRP, there is no mask, no "
       "other bit (S_IRWXO, S_IROTH, S_IWOTH, S_IXOTH, S_ISUID), no chmod() by name - only fchmod on descriptors opened O_NOFOLLOW",
       "(ds.st_mode & 07777) | S_IRWXG | S_ISGID" in fm and "(fs.st_mode & 07777) | S_IRGRP | S_IWGRP" in fm and re.search(r"S_IRWXO|S_IROTH|S_IWOTH|S_IXOTH|S_ISUID|~", fm) is None
       and re.search(r"(?<![\w_])chmod\s*\(", fm) is None and fm.count("fchmod(") == 2 and fm.count("O_NOFOLLOW") == 2, "")
    ck("S18a ...only where the account's own directory lets its group write, and only what THIS process made and what has that directory's group: S_IWGRP of the account directory, owner = the effective user, "
       "group = the account directory's; and only the VOC itself (rel is voc) or a directory whose last component ends .dic, in a registered account",
       ordered(fm, "mst_acc_for_path(full, &rel)", 'strcmp(rel, "voc") == 0', "stat(a->root, &ra)", "ra.st_mode & S_IWGRP", "O_DIRECTORY | O_NOFOLLOW", "ds.st_uid != geteuid()", "ds.st_gid != ra.st_gid", "fchmod(dfd")
       and "fs.st_uid == geteuid()" in fm and "fs.st_gid == ra.st_gid" in fm and "S_ISREG(fs.st_mode)" in fm and "S_ISDIR(ds.st_mode)" in fm, "")

    # ---- S19 the BASIC and the installer -------------------------------------------------------------------------------------------------------
    ca2 = B("create_account")
    ck("S19 create_account puts the sdsys user in a user account's group through sd-elevate's sdsys-join, only when it is not a member already (is_grp_member), only in the USER branch after create.group and before "
       "the account is made, and a failure is said (11012, 11579) without stopping the account (no goto exit.create in join.sdsys)",
       ordered(ca2, 'group_name = "sdu_":downcase(acc.uname)', "gosub create.group", "gosub join.sdsys", 'case acc.type = "GROUP"', "gosub make.account")
       and ca2.count("gosub join.sdsys") == 1 and ca2.count("sd-elevate sdsys-join") == 1 and 'os.execute "sudo /usr/local/sbin/sd-elevate sdsys-join ":group_name' in ca2
       and ordered(between(ca2, "join.sdsys:", "end\n   return\n"), "is_grp_member('sdsys', group_name)", "os.execute", "sysmsg(11011", "sysmsg(11012", "sysmsg(11579")
       and "goto exit.create" not in between(ca2, "join.sdsys:", "end\n   return\n"), "")
    ins2 = c["sh:installsdcore.sh"]
    jf = re.search(r"^join_sdsys_groups\(\) \{.*?^\}", c["sh:installsdcore.sh"], re.M | re.S)
    jf = jf.group(0) if jf else ""
    ck("S20 the installer's join_sdsys_groups: sdsys-join only for a group named sdu_<something> (the case arm), and only when /etc/group does not already list sdsys; group-write only for a path directly under "
       "/home/sd/user_accounts or /home/sd/group_accounts, a group sdu_ or sdg_, and only when the directory's group IS the register's group; judged on sd-elevate's own success line; never exits; "
       "called once, with the register, before upgrade_masters",
       len(jf) > 1500 and "sd-elevate sdsys-join \"$group\"" in jf and jf.count("sdsys-join") == 2 and ordered(jf, "sdu_?*)", "getent group", "sdsys-join \"$group\"")
       and ordered(jf, "sdu_?*|sdg_?*)", "/home/sd/user_accounts/*|/home/sd/group_accounts/*)", 'dir_group=$(sudo stat -c', '[ "$dir_group" = "$group" ]', "sd-elevate group-write \"$path\"")
       and "group-write: 0 directories and 0 file(s) changed" in jf and re.search(r"\b(exit|return 1)\b", jf) is None and ins2.count("join_sdsys_groups \"$sdsysdir/accounts\"") == 1
       and ordered(ins2, "-internal RUN gpl.bp upgrade_editgates", 'join_sdsys_groups "$sdsysdir/accounts"', "-internal RUN gpl.bp upgrade_masters"), "")
    se = c["sh:sd-elevate"]
    ck("S21 sd-elevate has the two verbs: sdsys-join builds usermod -aG GROUP -- sdsys (the user written in the helper, never an argument; -aG appends) after require_account_group; group-write runs the worker "
       "on one validated account directory and exits with its status; their rules are measured by test-sd-elevate.py and test-accelevate-units.py",
       ordered(between(se, "sdsys-join)", ";;"), "[[ $# -eq 1 ]] || usage", 'require_account_group "$1"', 'cmd=(usermod -aG "$1" -- sdsys)') and "SUDO_USER" not in between(se, "sdsys-join)", ";;")
       and ordered(between(se, "group-write)", ";;"), "[[ $# -eq 1 ]] || usage", 'require_group_write_target "$1"', "need_root", 'python3 -c "$GW_PY"', "exit $?"), "")
    ck("S22 wiring: the map has rules for messages 11579-11599, sd-elevate and the two new tests (or the coarse rules take them), and the new installer test is a free check that names the function",
       re.search(r"^sdsys/messages/1157\[0-9\]\s*:.*\bmasters\b", mp_, re.M) is not None and re.search(r"^sdsys/messages/1158\[0-9\]\s*:.*\bmasters\b", mp_, re.M) is not None
       and re.search(r"^sdsys/messages/1159\[0-6\]\s*:.*\bmasters\b", mp_, re.M) is not None and re.search(r"^gplbld/sd-elevate\s*:\s*none\b", mp_, re.M) is not None
       and "join_sdsys_groups" in (srcs.get("file:test-install-sdsysgroups.sh") or ""), "")
    ck("S23 the op 'refusal' is the administrator's (it comes after the 'if (!admin)' refusal) and answers the stage 2 buffer and nothing else; ED asks it at both its write-error sites, only for status 8910, and "
       "displays the second field; CHECK.MASTERS and LIST.MASTER.PENDING each end with it (message 11594)",
       ordered(rq, "if (!admin) {", 'strcmp(op, "refusal") == 0', "masters_refusal_text()", 'strcmp(op, "init") == 0')
       and ordered(B("ed"), "write.status = status()", "gosub master.refusal") and B("ed").count("gosub master.refusal") == 2
       and ordered(B("ed"), "master.refusal:", "if write.status = 8910 then", "kernel(K$MASTERS, 'refusal')", "display refusal.reply<2>")
       and B("masters").count("gosub last.refusal") == 2 and ordered(B("masters"), "last.refusal:", "kernel(K$MASTERS, 'refusal')", "sysmsg(11594"), "")

    # ===== T. THE INDEPENDENT VERIFIER'S FINDINGS, 19 OCT 26 (the numbers F1 to F7 are the verifier's) ============================================
    # ---- T1 F1: the master files are the sdsys user's alone, from the moment they exist -------------------------------------------------------
    ms2 = B("masters_setup")
    ck("T1 (F1) masters_setup makes the three files and their dictionaries under umask 077 (written 63: BASIC has no octal) and puts the umask back on every way out - the two `create.file ... on error` "
       "returns and the end; the kernel's mst_init sets 0700 and 0600 as well (J8)",
       ordered(ms2, "um = umask(63)", "create.file dp dynamic", "create.file dp : '.dic' dynamic", "if umask(um) then null", "kernel(K$MASTERS, 'init')")
       and ms2.count("if umask(um) then null") == 3 and ms2.count("umask(") == 4
       and re.search(r"create\.file dp dynamic on error\s+close sv\s+if umask\(um\) then null\s+report = 2", ms2) is not None
       and re.search(r"create\.file dp : '\.dic' dynamic on error\s+close sv\s+if umask\(um\) then null\s+report = 2", ms2) is not None, "")
    # ---- T2 F2: no pointer into the table of accounts is kept across a call that can read the table again ---------------------------------------
    ma_ = func_body(m, "Private bool mst_acc_by_name(const char *name, MST_ACC *out)")
    ck("T2 (F2) mst_acc_by_name gives a COPY of the account's table entry (`*out = acc_tab[i]`), and its every caller passes the copy it keeps; mst_deliver works on `MST_ACC acc` and `a = &acc` - "
       "never on a pointer into acc_tab, which the inner write replaces (the hook classifies the path); the loops over every account walk a snapshot (mst_acc_snapshot), not acc_tab; the only "
       "address of a table entry that leaves the table's own functions is mst_acc_scan_path's, used at once by mst_classify and masters_fix_modes",
       "*out = acc_tab[i];" in ma_ and "MST_ACC acc;" in dv and "const MST_ACC *a = &acc;" in dv
       and all(re.search(r"mst_acc_by_name\([^;]*&acc\)", ln) for ln in re.findall(r".*mst_acc_by_name\(.*", m) if "Private bool mst_acc_by_name" not in ln) and m.count("mst_acc_by_name(") == 5
       and len(re.findall(r"&acc_tab\[", m)) == 1 and "&acc_tab[" in func_body(m, "Private const MST_ACC *mst_acc_scan_path(const char *canon, const char **rel)")
       and "mst_check_account(&cx, &ck, &all[i])" in rq and "mst_sync_account(&cx, &all[i], &r)" in rq and "memcpy(c, acc_tab" in func_body(m, "Private MST_ACC *mst_acc_snapshot(int *n)")
       and "mst_acc_find(" in func_body(m, "Private bool mst_in_register(const char *name)"), "")
    ck("T2a ...the table is sorted by NAME as well (acc_sorted, a binary search), so that finding an account is not a walk over all of them for each key of a journal or a master",
       "int *acc_sorted" in m and "strcasecmp(mst_acc_ctx[*(const int *)pa].name, mst_acc_ctx[*(const int *)pb].name)" in m and "strcasecmp(acc_tab[acc_sorted[mid]].name, name)" in m
       and "free(acc_sorted);" in func_body(m, "Private void mst_acc_load(void)"), "")
    # ---- T3 F3 is S14 and S14d.  F4 is S14c.  ------------------------------------------------------------------------------------------------
    # ---- T4 F5: an account whose directory or VOC cannot be read keeps its dictionary copies ---------------------------------------------------
    adx = func_body(m, "Private bool mst_account_dicts(MST_CTX *cx, const MST_ACC *a, char ***names, int *n)")
    csy = func_body(m, "Private bool mst_sync_account(MST_CTX *cx, const MST_ACC *a, MST_SYNCRES *res)")
    cck = func_body(m, "Private void mst_check_account(MST_CTX *cx, MST_CHECK *ck, const MST_ACC *a)")
    ck("T4 (F5) mst_account_dicts says whether its list is COMPLETE: not when the account's directory could not be listed (opendir) or its VOC is there and could not be opened or read through; "
       "mst_sync_account takes the master keys of dictionaries the account 'no longer has' out ONLY when it is (and counts an error when it is not); mst_check_account says 'unreadable dict' when "
       "it is not and calls no copy extra",
       ordered(adx, "bool complete = TRUE;", "opendir(a->root)", "} else {", "complete = FALSE;", "mst_acct_file(cx, MST_VOC", "if (!cx->last_absent)", "complete = FALSE;", "mst_scan_ids(vdh, &vids)", "complete = FALSE;", "return complete;")
       and ordered(csy, "dcomplete = mst_account_dicts(cx, a, &dn, &dnn);", "if (!dcomplete)", "cx->errs++;", "if (dcomplete) {", "mst_delete_keys(cx, MST_DICT, &gone)")
       and ordered(cck, "dcomplete = mst_account_dicts(cx, a, &dn, &dnn);", "if (!dcomplete)", '"unreadable", a->name, "dict"', "dcomplete && (p < dkeys.len)", '"extra", a->name, "dict"'), "")
    # ---- T5 F6: a link out of the account is not the account's file --------------------------------------------------------------------------
    ctf = func_body(m, "Private DH_FILE *mst_acct_file(MST_CTX *cx, int kind, const char *root, const char *file)")
    ck("T5 (F6) mst_acct_file counts a VOC or dictionary that resolves (realpath) to a place outside the account's directory as NOT THERE (absent: its copies go, a save is refused as 'no dictionary of "
       "that name') and opens nothing through it; after the open the file's device and inode are compared with the resolved path's and a mismatch closes it; the directory scan skips a *.dic that "
       "links out, by the same test",
       ordered(ctf, "mst_inside_root(path, root, real, sizeof(real))", "absent = TRUE;", "mst_open_path(path)", "stat(real, &rs)", "fe->device", "(u_int32_t)rs.st_dev", "dh_close(dh);", "dh = NULL;")
       and "if (((fe->device != 0) || (fe->inode != 0)) && ((fe->device != (u_int32_t)rs.st_dev) || (fe->inode != (u_int32_t)rs.st_ino))) {" in ctf
       and ordered(adx, "mst_inside_root(dpath, a->root", "continue;", "mst_file_ok(f)")
       and "(strncmp(r, root, rl) == 0) && (r[rl] == '/')" in func_body(m, "Private bool mst_inside_root(const char *path, const char *root, char *real, size_t realsz)"), "")
    # ---- T6 F7: each master is read once for an operation over every account ---------------------------------------------------------------------
    ck("T6 (F7) mst_sync_account and mst_check_account take an account's keys from mst_keys_of (an index sorted by key, found by a binary search on the prefix) and never scan a master themselves; "
       "'syncall' builds the indexes (with master_state), the all-accounts check builds them (without), the drain's whole-file lines use an index too, and mst_ctx_close frees them; the "
       "index is sorted in the order mst_id_cmp gives and searched with a prefix comparison that folds the same way",
       "mst_scan_prefixed" not in csy and "mst_scan_prefixed" not in cck and csy.count("mst_keys_of(") == 4 and cck.count("mst_keys_of(") == 2
       and ordered(rq, 'strcmp(op, "syncall") == 0', "mst_acc_snapshot(&n)", "mst_ctx_index(&cx, TRUE);", "mst_sync_account(&cx, &all[i], &r)", 'strcmp(op, "syncbegin") == 0')
       and ordered(rq, 'strcmp(op, "check") == 0', "mst_acc_snapshot(&n)", "mst_ctx_index(&cx, FALSE);", "mst_check_account(&cx, &ck, &all[i])", "mst_check_orphans(&cx, &ck);")
       and "mst_index_build(cx->vm, &vall)" in dr and "mst_index_slice(" in dr and "mst_scan_ids(cx->vm" not in dr
       and ordered(func_body(m, "Private void mst_ctx_close(MST_CTX *cx)"), "mst_index_free(cx->ix[i]);", "free(cx->ix[i]);")
       and "mst_set_cmp" in func_body(m, "Private bool mst_set_build(MST_SET *s, const MST_IDS *l)")
       and func_body(m, "Private int mst_prefix_cmp(const char *key, int klen, const char *prefix, size_t plen)").count("mst_fold(") == 2, "")
    # ---- T7 the journal: a short write is cut back, an unterminated last line is ended by the drain -----------------------------------------------
    ck("T7 mst_journal_line cuts the journal back to the size it read when a write came up short (a front of a line left at the end would swallow the next line), under the same semaphore; the drain "
       "ENDS an unterminated last line with a newline (pwrite at the end, under ERRLOG_SEM, only when the file's last byte is not a newline and something is left unconsumed), so the next line "
       "is a line of its own",
       ordered(jl, "have_size = (fstat(fd, &st) == 0);", "write(fd, line", "if ((w > 0) && have_size)", "ftruncate(fd, st.st_size);", "mst_flag(MST_F_STALE);")
       and ordered(dr, "} else if (can_write && (consumed < (long)st.st_size)) {", "StartExclusive(ERRLOG_SEM", "pread(fd, &last, 1, st.st_size - 1)", "last != '\\n'", 'pwrite(fd, "\\n", 1, st.st_size)', "EndExclusive(ERRLOG_SEM)"), "")
    # ---- T8 the file part of a dictionary key is case blind -------------------------------------------------------------------------------------
    ck("T8 a dictionary key typed in capitals finds the dictionary: only when the first try says the file is NOT THERE, and only for a dictionary, the file part is put in lower case (every file SD makes "
       "is) and tried once more; the keys of master_state and the audit line then name it as the account has it",
       ordered(dv, "adh = mst_acct_file(&cx, which, a->root, file);", "(adh == NULL) && cx.last_absent && (which == MST_DICT)", "tolower((unsigned char)file[k])", "adh = mst_acct_file(&cx, which, a->root, file);",
               'snprintf(filetxt, sizeof(filetxt), "%s.dic", file);', "mst_keys(which, a->name, file, rid, rid_len, mkey, skey)"), "")
    # ---- T9 the witness and the headers --------------------------------------------------------------------------------------------------------
    wit = strip_sh(srcs.get("file:witness-masters.sh") or "")
    ck("T9 witness-masters.sh: states the owner, group and mode of the three master files, their dictionaries, their subfiles and the journal (the sandbox has one user and cannot), requiring 700 / 600 and "
       "no group or other bit on the master files, and the journal 620 in the group sdusers; and its cleanup deletes a register record ONLY when this run made it (MADE_A1 / MADE_A2), never one that "
       "was there before",
       "master files: owner, group and mode" in wit and 'stat -c' in wit and "no group or other bit" in wit and "6e $A1 is in sdusers" in wit and '"DENIED DENIED DENIED"' in wit
       and re.search(r'for a in "\$A1" "\$A2"; do\s+MADE=\$\(\[ "\$a" = "\$A1" \] && echo "\$MADE_A1" \|\| echo "\$MADE_A2"\)\s+if \[ "\$MADE" -eq 1 \] && \[ -e "\$REGISTER/\$a" \]; then', wit) is not None, "")
    ck("T10 no header of the tests names a worktree path: every run instruction is the absolute path in the repository that stays (/home/don/Projects/SDCore4Linux/...)",
       not any(("SDCore4Linux" + "-wt") in (srcs.get("file:" + t) or "") for t in ("sandbox-masters.py", "test-masters-units.py", "witness-masters.sh", "test-install-sdsysgroups.sh")), "")
    ck("T11 regress-map.txt: the kernel files whose behaviour the masters suite alone tests select it - op_dio3.c (the transaction refusal, the 8910 text, the read note), sdsys/gpl.bp/ed (the refusal "
       "line), op_lock.c (lock_record, taken by the save), txn.c and k_error.c (audit_message) - and so do messages 11590-11596",
       all(re.search(r"^%s\s*:.*\bmasters\b" % re.escape(p), mp_, re.M) for p in ("gplsrc/op_dio3.c", "sdsys/gpl.bp/ed", "gplsrc/op_lock.c", "gplsrc/txn.c", "gplsrc/k_error.c"))
       and re.search(r"^sdsys/messages/1159\[0-6\]\s*:.*\bmasters\b", mp_, re.M) is not None, "")
    return rows


def mutate(srcs, name, a, b, count=1):
    """A copy of SRCS with a change made to one file.  A is an exact string (or a compiled regex), B the replacement.  A change that finds nothing, or
    changes nothing, is an error: a mutant that does not apply tests nothing."""
    s = dict(srcs)
    if name not in s or s[name] is None:
        raise KeyError("no such source: %s" % name)
    old = s[name]
    if isinstance(a, re.Pattern):
        new = a.sub(b, old, count=count)
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
    ("K_MASTERS shares a number with another key", "c:keys.h", "#define K_MASTERS            150", "#define K_MASTERS            131"),
    ("K$MASTERS disagrees with the C number", "bp:int$keys.h", "$define K$MASTERS         150", "$define K$MASTERS         151"),
    ("DHF_MST_VOC takes a bit of another flag", "c:dh.h", "#define DHF_MST_VOC  0x08000000", "#define DHF_MST_VOC  0x02000000"),
    ("DHF_MST_NONE is a header bit", "c:dh.h", "#define DHF_MST_NONE 0x04000000", "#define DHF_MST_NONE 0x00000400"),
    ("masters_flags moves before lock_trace", "c:sysseg.h", "   int16_t lock_trace;          /* LOCK.TRACER", "   u_int16_t masters_flags;\n   int16_t lock_trace;          /* LOCK.TRACER"),
    ("MST_F_RESYNC is the stale bit", "c:sysseg.h", "#define MST_F_RESYNC  0x0002", "#define MST_F_RESYNC  0x0001"),
    ("masters is not built", "txt:gpl.src", "masters\n", ""),
    ("a message is deleted", "msg:11568", X(r"(?s).*"), ""),
    ("a message takes a fifth argument", "msg:11578", "%3 left out", "%5 left out"),
    ("the usage message loses its lower case", "msg:11560", "Usage: sync.masters", "Usage: SYNC.MASTERS"),
    # ---- the hook ----
    ("dh_write journals before the write is done", "c:dh_write.c", "  if (dh_err == 0) {\n    dh_forced_write(dh_file);", "  masters_note_record(dh_file, 'w', id, id_len);\n  if (dh_err == 0) {\n    dh_forced_write(dh_file);"),
    ("dh_write journals a failed write", "c:dh_write.c", "    masters_note_record(dh_file, 'w', id, id_len);\n  }\n\n  return (dh_err == 0);", "  }\n  masters_note_record(dh_file, 'w', id, id_len);\n\n  return (dh_err == 0);"),
    ("dh_write never journals", "c:dh_write.c", "    masters_note_record(dh_file, 'w', id, id_len);\n", ""),
    ("dh_delete journals a record that was not there", "c:dh_del.c", "    if (found)\n      masters_note_record(dh_file, 'd', id, id_len);", "    masters_note_record(dh_file, 'd', id, id_len);"),
    ("dh_delete never journals", "c:dh_del.c", "      masters_note_record(dh_file, 'd', id, id_len);", ""),
    ("dh_clear never journals", "c:dh_clear.c", "  masters_note_dh(dh_file, 'c');\n", ""),
    ("dh_clear journals a clear that failed", "c:dh_clear.c", "  status = TRUE;\n\n  /* 19 Oct 26 S.67", "  masters_note_dh(dh_file, 'c');\n  status = TRUE;\n\n  /* 19 Oct 26 S.67"),
    ("dh_create_file never journals", "c:dh_creat.c", "  masters_note_name(path, 'n');\n", ""),
    ("dh_create_file journals before the file exists", "c:dh_creat.c", "  CloseFile(fu);\n  fu = INVALID_FILE_HANDLE;\n\n  status = TRUE;", "  masters_note_name(path, 'n');\n  CloseFile(fu);\n  fu = INVALID_FILE_HANDLE;\n\n  status = TRUE;"),
    ("OSPATH delete does not journal", "c:op_dio2.c", "      masters_note_name(path, 'x'); /* 19 Oct 26 S.67: a dictionary (or what is in one) removed; the path need not exist any more */\n", ""),
    ("OSRENAME journals only the new name", "c:op_dio2.c", "  masters_note_name(old_path, 'x');\n", ""),
    ("OSRENAME journals before the failure exits", "c:op_dio2.c", "  if (rename(old_path, new_path)) {", "  masters_note_name(old_path, 'x');\n  if (rename(old_path, new_path)) {"),
    ("the second OSPATH does not journal", "c:op_xfun.c", "      masters_note_name(path, 'x'); /* 19 Oct 26 S.67: an (empty) dictionary directory removed; the path need not exist any more */\n", ""),
    ("open_file does not drain", "c:op_dio1.c", "  masters_open_hook(pathname);\n", ""),
    ("open_file drains after the OS gate", "c:op_dio1.c", "  masters_open_hook(pathname);\n\n  /* 13 Oct 26 S.63: OPENPATH names", "  /* 13 Oct 26 S.63: OPENPATH names"),
    ("a record opcode calls the hook (a write inside a transaction is journalled before COMMIT)", "c:op_dio3.c", "static const char hookprobe[] = \"x\";", "static const char hookprobe[] = \"x\";"),
    ("the transaction code calls the hook", "c:txn.c", "#include \"sd.h\"", "#include \"sd.h\"\nvoid masters_note_record(DH_FILE *dh, char op, const char *id, int id_len);\nstatic void masters_probe(void) { masters_note_record(0, 'w', \"\", 0); }"),
    ("the cheap refusal is not the first test", "c:masters.c", "  if ((dh == NULL) || (dh->flags & DHF_MST_NONE))\n    return;\n  if (!(dh->flags & (DHF_MST_VOC | DHF_MST_DICT))) {",
     "  if (dh == NULL)\n    return;\n  if (!(dh->flags & (DHF_MST_VOC | DHF_MST_DICT))) {"),
    ("the hook can raise an error", "c:masters.c", "  mst_journal_line(fd, kind, op, acct, file, id, id_len);\n}\n\nvoid masters_note_dh", "  if (kind == MST_DICT)\n    k_error(\"cannot journal\");\n  mst_journal_line(fd, kind, op, acct, file, id, id_len);\n}\n\nvoid masters_note_dh"),
    ("a class that disagrees with the name is journalled all the same", "c:masters.c", "sizeof(file)) != kind) {\n    close(fd);\n    return;", "sizeof(file)) == 0) {\n    close(fd);\n    return;"),
    ("the journal is opened after the file is classified", "c:masters.c", "  if ((fd = mst_journal_open()) < 0) /* no journal: nothing more to do, and nothing worked out */\n    return;\n  if (mst_classify(",
     "  if (mst_classify((const char *)FPtr(dh->file_id)->pathname, acct, sizeof(acct), file, sizeof(file)) != kind)\n    return;\n  if ((fd = mst_journal_open()) < 0)\n    return;\n  if (mst_classify("),
    ("the journal is opened after the path is resolved", "c:masters.c", "  if ((fd = mst_journal_open()) < 0)\n    return;\n  if (!fullpath(full,", "  if (!fullpath(full, (char *)name))\n    return;\n  if ((fd = mst_journal_open()) < 0)\n    return;\n  if (!fullpath(full,"),
    # ---- the journal ----
    ("the journal is created by a session", "c:masters.c", "fd = open(path, O_WRONLY | O_APPEND | O_NOFOLLOW | O_CLOEXEC);\n  if (fd < 0) {\n    if ((errno != ENOENT)", "fd = open(path, O_WRONLY | O_APPEND | O_CREAT | O_NOFOLLOW | O_CLOEXEC, 0620);\n  if (fd < 0) {\n    if ((errno != ENOENT)"),
    ("a lost journal is silent", "c:masters.c", "    if ((errno != ENOENT) || mst_masters_present())\n      mst_flag(MST_F_STALE);", "    if (errno != ENOENT)\n      mst_flag(MST_F_STALE);"),
    ("a journal that is not there is always a failure", "c:masters.c", "    if ((errno != ENOENT) || mst_masters_present())\n      mst_flag(MST_F_STALE);", "    mst_flag(MST_F_STALE);"),
    ("the master files are looked for in the wrong place", "c:masters.c", 'snprintf(p, sizeof(p), "%s%c%s%c%%0", (const char *)sysseg->sysdir, DS, MST_VOC_MASTER, DS)', 'snprintf(p, sizeof(p), "%s%c%s%c%%0", (const char *)sysseg->sysdir, DS, MST_STATE, DS)'),
    ("a failed append is silent", "c:masters.c", "        (void)ftruncate(fd, st.st_size);\n      mst_flag(MST_F_STALE);\n    }", "        (void)ftruncate(fd, st.st_size);\n    }"),
    ("the size limit is not tested", "c:masters.c", "  if (have_size && (st.st_size >= MST_JOURNAL_CAP)) {\n    mst_flag(MST_F_RESYNC);\n  } else {", "  if (0) {\n    mst_flag(MST_F_RESYNC);\n  } else {"),
    ("the size limit sets the wrong flag", "c:masters.c", "    mst_flag(MST_F_RESYNC);\n  } else {\n    ssize_t w", "    mst_flag(MST_F_STALE);\n  } else {\n    ssize_t w"),
    ("the append is not under the semaphore", "c:masters.c", "  StartExclusive(ERRLOG_SEM, 72);\n", ""),
    ("the line is written in two pieces", "c:masters.c", "    ssize_t w = write(fd, line, (size_t)len);", "    ssize_t w = (write(fd, line, 1) == 1) ? 1 + write(fd, line + 1, (size_t)len - 1) : -1;"),
    ("the line carries the record's data", "c:masters.c", "Private void mst_journal_line(int fd, int kind, char op, const char *acct, const char *file, const char *id, int id_len) {",
     "Private void mst_journal_line(int fd, int kind, char op, const char *acct, const char *file, const char *id, int id_len, STRING_CHUNK *data) {"),
    ("setup makes the journal only after the files", "bp:masters_setup", "   ans = kernel(K$MASTERS, 'init')\n   if ans<1> # 0 then\n      close sv\n", "   ans = ''\n   if ans<1> # 0 then\n      close sv\n"),
    ("an id with a space is not encoded", "c:masters.c", "if ((c <= 0x20) || (c == '%')", "if ((c < 0x20) || (c == '%')"),
    ("a percent sign is not encoded", "c:masters.c", " || (c == '%') || (c >= 0x7F)", " || (c >= 0x7F)"),
    ("the entry buffer is a page", "c:masters.c", "char line[1600];", "char line[8192];"),
    ("the flag is set with a plain or", "c:masters.c", "  __sync_fetch_and_or(&sysseg->masters_flags, bit);", "  sysseg->masters_flags |= bit;"),
    ("the journal is made with the wrong mode", "c:masters.c", "O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0620)", "O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0666)"),
    ("the master files are left open to the group", "c:masters.c", "if (chmod(dirpath, 0700) == 0)", "if (chmod(dirpath, 0770) == 0)"),
    ("the master files' subfiles are left open to the group", "c:masters.c", "if (chmod(q, 0600) == 0)", "if (chmod(q, 0660) == 0)"),
    ("the master files' group is looked up under the name sdsys, which no system has", "c:masters.c", "  if ((gr = getgrnam(\"sdusers\")) != NULL)\n    sdusers_gid = gr->gr_gid;\n",
     "  if ((gr = getgrnam(\"sdusers\")) != NULL)\n    sdusers_gid = gr->gr_gid;\n  if ((gr = getgrnam(\"sdsys\")) != NULL)\n    sys_gid = gr->gr_gid;\n"),
    ("setup makes the files under the session's umask", "bp:masters_setup", "   um = umask(63)\n", "   um = 0\n"),
    ("setup leaves the umask changed after a failed create", "bp:masters_setup", "            close sv\n            if umask(um) then null\n            report = 2 : @fm : 'cannot make ' : nm : @fm : made", "            close sv\n            report = 2 : @fm : 'cannot make ' : nm : @fm : made"),
    # ---- the drain ----
    ("any session drains on opening a master", "c:masters.c", "if (busy || (my_uptr == NULL) || !(my_uptr->flags & USR_ADMIN) || (canon == NULL) || !mst_is_master_path(canon))", "if (busy || (canon == NULL) || !mst_is_master_path(canon))"),
    ("the drain can recurse", "c:masters.c", "  if (busy || (my_uptr", "  if ((my_uptr"),
    ("the drain does not lock the journal", "c:masters.c", "  if (flock(fd, LOCK_EX) != 0) {\n    close(fd);\n    return MSA_ERR;\n  }\n  if (fstat(fd, &st) != 0) {", "  if (fstat(fd, &st) != 0) {"),
    ("the journal is truncated without the semaphore", "c:masters.c", "    StartExclusive(ERRLOG_SEM, 74);\n", ""),
    ("the journal is truncated without looking at the size again", "c:masters.c", "(fstat(fd, &st) == 0) && ((long)st.st_size == consumed) && (ftruncate(fd, 0) == 0)", "(ftruncate(fd, 0) == 0)"),
    ("the journal is truncated when only part was taken", "c:masters.c", "(consumed > 0) && (consumed == (long)st.st_size)", "(consumed > 0)"),
    ("the state is written when nothing moved", "c:masters.c", "  if ((res->offset_after != saved_off) || ((long)st.st_ino != saved_ino) || (res->keys + res->files > 0))\n    mst_jstate_put(", "  mst_jstate_put("),
    ("lines of accounts that are not registered are applied", "c:masters.c", "      if (mst_acc_find(ev[i].acct) >= 0)\n        ev[keep++] = ev[i];\n      else\n        res->skipped++;", "      ev[keep++] = ev[i];"),
    ("the events are not sorted", "c:masters.c", "  if (nev > 1)\n    qsort(ev, (size_t)nev, sizeof(MST_EVT), mst_evt_cmp);", ""),
    ("a file synced whole is synced again for each line", "c:masters.c", "        for (j = i + 1; (j < nev) && (ev[j].kind == e->kind) && (strcasecmp(ev[j].acct, e->acct) == 0) && (strcasecmp(ev[j].file, e->file) == 0); j++) {\n        }\n        i = j;", "        i++;"),
    ("a line can name a path", "c:masters.c", "  if ((ev->kind == 'd') && !mst_file_ok(ev->file))\n    return 0;", ""),
    ("a line may carry any account name", "c:masters.c", "  if (!mst_valid_account_name(f[3]))\n    return 0;", ""),
    ("a line with seven fields is accepted", "c:masters.c", "  if ((n != 6) || (p != NULL))", "  if (n < 6)"),
    ("a VOC line may name a file", "c:masters.c", "  if ((ev->kind == 'v') && (ev->file[0] != '\\0'))\n    return 0;", ""),
    ("a delete line without an id is accepted", "c:masters.c", "  if (((ev->op == 'w') || (ev->op == 'd')) && (ev->id_len == 0))\n    return 0;", ""),
    ("a dictionary name may have an asterisk", "c:masters.c", " || (f[i] == '*'))", ")"),
    ("a dictionary name may start with a slash", "c:masters.c", "(f[0] == '/'))", "0)"),
    ("a dictionary name may hold ..", "c:masters.c", "((cl == 2) && (p[0] == '.') && (p[1] == '.'))", "0"),
    ("a key too long is written", "c:masters.c", "  if (mst_keys(kind, acct, file, id, id_len, mkey, skey) < 0) {\n    cx->toolong++;\n    return MS_LONG;\n  }", "  mst_keys(kind, acct, file, id, id_len, mkey, skey);"),
    ("the key limit ignores the state key", "c:masters.c", "int limit = sysseg->maxidlen - 2;", "int limit = sysseg->maxidlen;"),
    ("the master is written even when it is the same", "c:masters.c", "  if (!mfound || !mst_str_equal(rec, mrec)) {", "  if (1) {"),
    ("a record the account lacks stays in the master", "c:masters.c", "      if (!mst_mdelete(mdh, mkey, (int16_t)mk)) {", "      if (0) {"),
    ("the state is written every time", "c:masters.c", "  if (strcmp(cks, scks) != 0) {", "  if (1) {"),
    ("a file that cannot be read through has its master copies deleted", "c:masters.c", "  } else if ((adh != NULL) || !absent) {\n    cx->errs++; /* could not be opened, or could not be read through: leave the master copies alone */\n    mst_ids_free(&ids);\n    return;\n  } else {", "  } else if (adh != NULL) {\n    cx->errs++;\n  } else {"),
    ("a file that cannot be opened is taken for one that is not there", "c:masters.c", "(stat(sub, &sb) != 0) && (errno == ENOENT);", "TRUE;"),
    ("sync_key deletes the master copy of a file it cannot open", "c:masters.c", "  } else if (!cx->last_absent) {\n    cx->errs++; /* the file is there and cannot be opened: say nothing about its records, and delete no copy of them */\n    return MS_ERR;\n  }", "  }"),
    ("check calls an unopenable file clean", "c:masters.c", "  if ((adh == NULL) && !cx->last_absent) { /* there, and cannot be opened: nothing can be said about its records */\n    mst_row(ck, \"unreadable\", acct, what, file, NULL, 0);\n    return;\n  }\n", ""),
    ("the nearest account does not win", "c:masters.c", "return (a->rlen > b->rlen) ? -1 : 1;", "return (a->rlen < b->rlen) ? -1 : 1;"),
    ("a VOC may be any file called voc below the root", "c:masters.c", '  if ((strcmp(rel, "voc") == 0) || (strncmp(rel, "voc/", 4) == 0))', '  if (strstr(rel, "voc") != NULL)'),
    ("the sync forgets the dictionaries the account no longer has", "c:masters.c", "    mst_delete_keys(cx, MST_DICT, &gone);\n    mst_ids_free(&gone);\n  }\n\n  /* state records", "    mst_ids_free(&gone);\n  }\n\n  /* state records"),
    # ---- the ops ----
    ("an ordinary session may init", "c:masters.c", "  if (!admin) {\n    mst_status(&out, MSA_REFUSED);\n    mst_answer(result, &out);\n    return;\n  }\n", ""),
    ("the administrator test comes after the first op", "c:masters.c", "  if (strcmp(op, \"ready\") == 0) {", "  if (strcmp(op, \"drain\") == 0) {\n    mst_status(&out, MSA_OK);\n    mst_answer(result, &out);\n    return;\n  }\n  if (strcmp(op, \"ready\") == 0) {"),
    ("admin is anyone", "c:masters.c", "bool admin = (my_uptr != NULL) && ((my_uptr->flags & USR_ADMIN) != 0);", "bool admin = (my_uptr != NULL);"),
    ("note does more than note", "c:masters.c", "    masters_note_name(arg, 'n');\n    mst_status(&out, MSA_OK);", "    masters_note_name(arg, 'n');\n    (void)mst_init(&out);\n    mst_status(&out, MSA_OK);"),
    ("a new op", "c:masters.c", '  } else if (strcmp(op, "accounts") == 0) {', '  } else if (strcmp(op, "wipe") == 0) {\n    mst_status(&out, MSA_OK);\n  } else if (strcmp(op, "accounts") == 0) {'),
    ("check repairs", "c:masters.c", '      mst_row(ck, "differs", acct, what, file, id, id_len);', '      { dh_write(mdh, mkey, (int16_t)mk, rec); mst_row(ck, "differs", acct, what, file, id, id_len); }'),
    ("check forgets the unwritable files", "c:masters.c", "    if (strcasecmp(acct, MST_SYSTEM_ACCOUNT) != 0 && !mst_group_writable(path)) {\n      mst_row(ck, \"nonwritable\", acct, what, file, NULL, 0);\n    } else {", "    if (0) {\n      mst_row(ck, \"nonwritable\", acct, what, file, NULL, 0);\n    } else {"),
    ("check asks the group bits of the SDSYS account's own files too", "c:masters.c", "if (strcasecmp(acct, MST_SYSTEM_ACCOUNT) != 0 && !mst_group_writable(path)) {", "if (!mst_group_writable(path)) {"),
    ("the group write test looks at the owner bit", "c:masters.c", "if (!(sb.st_mode & S_IWGRP))", "if (!(sb.st_mode & S_IWUSR))"),
    ("syncbegin leaves the flags up", "c:masters.c", "    __sync_fetch_and_and(&sysseg->masters_flags, (u_int16_t)~(MST_F_STALE | MST_F_RESYNC));\n", ""),
    ("syncend forgets the orphans", "c:masters.c", "    long dropped = mst_drop_orphans(&cx);\n    int rc", "    long dropped = 0;\n    int rc"),
    ("an unregistered account is not refused by sync", "c:masters.c", "    if (!mst_acc_by_name(arg, &acc)) {\n      mst_status(&out, MSA_NOACC);\n    } else {", "    if (0) {\n      mst_status(&out, MSA_NOACC);\n    } else {"),
    ("an unreadable register makes every copy an orphan (drop)", "c:masters.c", "  if (acc_n == 0)\n    return 0; /* a register that could not be read is not a register with no accounts in it: every copy would be called an orphan */\n", ""),
    ("an unreadable register makes every copy an orphan (check)", "c:masters.c", "  if (acc_n == 0)\n    return; /* as in mst_drop_orphans: an unreadable register is not an empty one */\n", ""),
    ("an account the table lacks is an orphan", "c:masters.c", '  return (snprintf(p, sizeof(p), "%s%caccounts%c%s", (const char *)sysseg->sysdir, DS, DS, name) < (int)sizeof(p)) && (stat(p, &sb) == 0);', "  return FALSE;"),
    # ---- the BASIC ----
    ("the verb program does not test for the administrator", "bp:masters", "   if not(kernel(K$ADMINISTRATOR, -1)) then\n      stop sysmsg(2001) ;* Command requires administrator privileges\n   end\n", ""),
    ("the verb program tests after the kernel", "bp:masters", "   if not(kernel(K$ADMINISTRATOR, -1)) then\n      stop sysmsg(2001) ;* Command requires administrator privileges\n   end\n\n   words = trim(@sentence)",
     "   words = trim(@sentence)\n   void kernel(K$MASTERS, 'ready')\n   if not(kernel(K$ADMINISTRATOR, -1)) then\n      stop sysmsg(2001) ;* Command requires administrator privileges\n   end\n"),
    ("a fourth verb", "bp:masters", "      case verb = 'list.master.pending'", "      case verb = 'wipe.masters'\n         stop\n      case verb = 'list.master.pending'"),
    ("SYNC does not set up first", "bp:masters", "   call !masters_setup(rep)\n   if rep<1> # 0 then\n      @system.return.code = -ER$FAILED", "   if rep<1> # 0 then\n      @system.return.code = -ER$FAILED"),
    ("SYNC with no account never ends the sync", "bp:masters", "      ans = kernel(K$MASTERS, 'syncend' : @fm : s0)\n", "      ans = ''\n"),
    ("SYNC with no account does not note the position", "bp:masters", "      ans = kernel(K$MASTERS, 'syncbegin')\n", "      ans = ''\n"),
    ("SYNC is not audited", "bp:masters", "      void kernel(K$AUDIT, 'sync.masters account=*')\n", ""),
    ("the audit word is upper case", "bp:masters", "'sync.masters account=*'", "'SYNC.MASTERS account=*'"),
    ("CHECK does not drain", "bp:masters", "   gosub drain.journal\n   if account # '' then ans = kernel(K$MASTERS, 'check'", "   if account # '' then ans = kernel(K$MASTERS, 'check'"),
    ("CHECK does not ask whether the files are set up", "bp:masters", "   ans = kernel(K$MASTERS, 'ready')\n   if ans<2> # 1 then\n      @system.return.code = -ER$FNF\n      stop sysmsg(11564)\n   end\n   gosub drain.journal", "   gosub drain.journal"),
    ("LIST.MASTER.PENDING drains", "bp:masters", "   ans = kernel(K$MASTERS, 'pending')\n   st = ans<1>\n   if st = 1 then", "   ans = kernel(K$MASTERS, 'drain')\n   ans = kernel(K$MASTERS, 'pending')\n   st = ans<1>\n   if st = 1 then"),
    ("the verbs are in newvoc", "newvoc.list", "zzz", "zzz"),
    ("a verb record points elsewhere", "voc:check.masters", "$masters", "$listshared"),
    ("setup overwrites an existing VOC entry", "bp:masters_setup", "      read x from sv, nm else\n         write 'F' : @fm : nm : @fm : nm : '.dic' to sv, nm\n         made = 1\n      end", "      write 'F' : @fm : nm : @fm : nm : '.dic' to sv, nm\n      made = 1"),
    ("setup makes a file by a relative name", "bp:masters_setup", "      dp = @sdsys : @ds : nm", "      dp = nm"),
    ("setup asks the kernel before the files exist", "bp:masters_setup", "   ans = kernel(K$MASTERS, 'init')\n   if ans<1> # 0 then", "   if 0 then"),
    ("setup runs a shell command", "bp:masters_setup", "   close sv\n   if umask(um) then null\n\n   ans = kernel", "   close sv\n   os.execute 'chmod 777 x'\n   if umask(um) then null\n\n   ans = kernel"),
    ("the upgrade prints COMPLETE whatever happened", "bp:upgrade_masters", "   if failed = 0 then crt 'COMPLETE'", "   crt 'COMPLETE'"),
    ("the upgrade does not finish the sync", "bp:upgrade_masters", "   rep = kernel(K$MASTERS, 'syncend' : @fm : s0)\n", ""),
    ("create_account syncs before the register is written", "bp:create_account", "   write acc.rec to acc.f, acc.name\n   locked = @false\n", "   void kernel(K$MASTERS, 'sync' : @fm : downcase(acc.name))\n   write acc.rec to acc.f, acc.name\n   locked = @false\n"),
    ("create_account never syncs", "bp:create_account", "   void kernel(K$MASTERS, 'sync' : @fm : downcase(acc.name))\n", ""),
    ("delacc drops before the register delete", "bp:delacc", "   delete acc.f, acc.name\n", "   void kernel(K$MASTERS, 'drop' : @fm : downcase(acc.name))\n   delete acc.f, acc.name\n"),
    ("delacc never drops", "bp:delacc", "   void kernel(K$MASTERS, 'drop' : @fm : downcase(acc.name))\n", ""),
    ("restorea never syncs", "bp:restorea", "         void kernel(K$MASTERS, 'sync' : @fm : downcase(acc.name))\n", ""),
    ("!oscopy never notes", "bp:_oscopy", "   void kernel(K$MASTERS, 'note' : @fm : target)\n", ""),
    ("!ioscopy notes before it copies", "bp:_ioscopy", "   os.execute \"cp -R -f", "   void kernel(K$MASTERS, 'note' : @fm : target)\n   os.execute \"cp -R -f"),
    # ---- the installer ----
    ("the installer stops running upgrade_masters", "sh:installsdcore.sh", "-internal RUN gpl.bp upgrade_masters", "-internal RUN gpl.bp upgrade_nothing"),
    ("the installer runs it after the register is handed over", "sh:installsdcore.sh",
     lambda t: t, None),
    ("the installer does not report a run that failed", "sh:installsdcore.sh", 'if [ "$om_rc" -ne 0 ] || ! printf', 'if false || ! printf'),
    # ---- wiring ----
    ("regress.sh forgets the suite", "txt:regress.sh", " pack-examples masters\"", " pack-examples\""),
    ("the map forgets the new program", "txt:regress-map.txt", "sdsys/gpl.bp/masters_setup   : masters\n", ""),
    ("the map forgets the DH files", "txt:regress-map.txt", "gplsrc/dh_*.c                : @files masters", "gplsrc/dh_*.c                : @files"),

    # ================== STAGE 2: MASTER TO ACCOUNT ==================
    # ---- numbers and messages ----
    ("DHE_MASTER_REFUSED is a record-not-found value", "c:sd.h", "#define DHE_MASTER_REFUSED 8910", "#define DHE_MASTER_REFUSED 8301"),
    ("DHE_MASTER_REFUSED is added to err.h (which is generated)", "c:err.h", "#define DHE_ECB_TYPE             8900 /* ECB has incorrect type */", "#define DHE_ECB_TYPE             8900 /* ECB has incorrect type */\n#define DHE_MASTER_REFUSED 8910"),
    ("DHF_MST_NOMASTER shares a bit with DHF_MST_DICT", "c:dh.h", "#define DHF_MST_NOMASTER 0x20000000", "#define DHF_MST_NOMASTER 0x10000000"),
    ("DHF_MST_DM is a header bit", "c:dh.h", "#define DHF_MST_DM       0x80000000", "#define DHF_MST_DM       0x00000004"),
    ("a message loses a %s", "msg:11583", "the record in %s has changed", "the record in the account has changed"),
    ("a message takes the BASIC form", "msg:11587", "sd-elevate sdsys-join %s)", "sd-elevate sdsys-join %3)"),
    ("a message is too long for k_error", "msg:11585", "(see check.masters). Nothing was changed", "(see check.masters). Nothing was changed, and what follows is a very long extension of this message so that it can no longer fit in the buffer k_error has, which is 231 characters less the 10 of the offset and the name of the program, so the last words, the ones that say what to do, are cut"),
    ("a message names a verb in capitals", "msg:11588", "then run sync.masters", "then run SYNC.MASTERS"),
    ("the BASIC message takes a %s", "msg:11579", "account %1 until", "account %s until"),
    ("a refusal passes too few arguments", "c:masters.c", "MSG_CHANGED, keytxt, a->name, NULL);", "MSG_CHANGED, keytxt, NULL, NULL);"),
    ("the lock refusal does not say who", "c:masters.c", "return mst_refuse(MSG_LOCKED, keytxt, num, NULL);", "return mst_refuse(MSG_LOCKED, keytxt, NULL, NULL);"),
    ("a lock table that is full is called a lock held by a user", "c:masters.c", "      return mst_refuse(MSG_NOLOCK, keytxt, NULL, NULL);", "      return mst_refuse(MSG_LOCKED, keytxt, num, NULL);"),
    ("a refusal is never used", "c:masters.c", "return mst_refuse(MSG_NOACCOUNT, keytxt, acct, NULL);", "return mst_refuse(MSG_BADKEY, keytxt, NULL, NULL);"),
    # ---- where the DH layer and the opcodes ask ----
    ("dh_write never asks", "c:dh_write.c", "    int master_refusal = masters_before_write(dh_file, id, id_len, new_data);", "    int master_refusal = 0;"),
    ("dh_write asks without the bit test", "c:dh_write.c", "  if (!(dh_file->flags & DHF_MST_NOMASTER)) {\n    int master_refusal = masters_before_write", "  {\n    int master_refusal = masters_before_write"),
    ("dh_write goes on after a refusal", "c:dh_write.c", "      dh_err = master_refusal;\n      process.os_error = 0;\n      return FALSE;", "      dh_err = master_refusal;\n      process.os_error = 0;"),
    ("dh_write asks after it has cleared dh_err", "c:dh_write.c", "  if (!(dh_file->flags & DHF_MST_NOMASTER)) {\n    int master_refusal = masters_before_write(dh_file, id, id_len, new_data);\n\n    if (master_refusal != 0) {\n      dh_err = master_refusal;\n      process.os_error = 0;\n      return FALSE;\n    }\n  }\n\n  dh_err = 0;\n  process.os_error = 0;",
     "  dh_err = 0;\n  process.os_error = 0;\n  if (!(dh_file->flags & DHF_MST_NOMASTER)) {\n    int master_refusal = masters_before_write(dh_file, id, id_len, new_data);\n\n    if (master_refusal != 0) {\n      dh_err = master_refusal;\n      process.os_error = 0;\n      return FALSE;\n    }\n  }"),
    ("dh_delete never asks", "c:dh_del.c", "    int master_refusal = masters_before_delete(dh_file, id, id_len);", "    int master_refusal = 0;"),
    ("dh_delete goes on after a refusal", "c:dh_del.c", "      dh_err = master_refusal;\n      process.os_error = 0;\n      return FALSE;", "      dh_err = master_refusal;\n      process.os_error = 0;"),
    ("a write inside a transaction is not refused", "c:op_dio3.c", "        if (masters_txn_refusal(dh_file, id, id_len) != 0) {\n          process.status = -DHE_MASTER_REFUSED;\n          goto exit_op_write;\n        }\n", ""),
    ("a delete inside a transaction is not refused", "c:op_dio3.c", "        if (masters_txn_refusal(dh_file, id, id_len) != 0)\n          process.status = -DHE_MASTER_REFUSED;\n        else\n          txn_delete(fvar, id, id_len);", "        txn_delete(fvar, id, id_len);"),
    ("the refusal is printed as a format", "c:op_dio3.c", 'k_error("%s", masters_refusal_text()); /* 19 Oct 26 S.67 stage 2: SDSYS\'s save', 'k_error(masters_refusal_text()); /* 19 Oct 26 S.67 stage 2: SDSYS\'s save'),
    ("the write tail prints the generic error", "c:op_dio3.c", "    else if (process.status == -DHE_MASTER_REFUSED)\n      k_error(\"%s\", masters_refusal_text()); /* 19 Oct 26 S.67 stage 2: SDSYS's save of a master record was refused; the reason is in plain words */\n", ""),
    ("dh_create_file never fixes modes", "c:dh_creat.c", "  masters_fix_modes(path);\n", ""),
    ("dh_create_file fixes modes before it journals", "c:dh_creat.c", "  masters_note_name(path, 'n');\n\n  /* 19 Oct 26 S.67 stage 2: and the group of the account may write it, where the account's own directory lets that group write (whatever the UMASK\n     of this session): SDSYS, a member of the group, writes master edits into the VOC and the dictionaries.  Never an error. */\n  masters_fix_modes(path);",
     "  masters_fix_modes(path);\n  masters_note_name(path, 'n');"),
    # ---- the classification and the two refusals ----
    ("master_state is taken for a master that delivers", "c:masters.c", "  if (w == 2) {\n    dh->flags |= DHF_MST_DM;\n    return MST_DICT;\n  }", "  if ((w == 2) || (w == 3)) {\n    dh->flags |= DHF_MST_DM;\n    return MST_DICT;\n  }"),
    ("dict_master does not deliver", "c:masters.c", "  if (w == 2) {\n    dh->flags |= DHF_MST_DM;", "  if (0) {\n    dh->flags |= DHF_MST_DM;"),
    ("the classification is not remembered", "c:masters.c", "  dh->flags |= DHF_MST_NOMASTER;\n  return 0;", "  return 0;"),
    ("the stage 1 writes are taken for saves", "c:masters.c", "  if (((kind = mst_master_kind(dh)) == 0) || (mst_inside > 0))\n    return 0;\n  return mst_deliver", "  if ((kind = mst_master_kind(dh)) == 0)\n    return 0;\n  return mst_deliver"),
    ("a delete is let through", "c:masters.c", "  return mst_refuse(MSG_DELETE, keytxt, NULL, NULL);\n}", "  return 0;\n}"),
    ("the administrator's delete is let through", "c:masters.c", "  mst_shown(keytxt, sizeof(keytxt), id, id_len, MST_SHOWN_MAX);\n  return mst_refuse(MSG_DELETE", "  if ((my_uptr != NULL) && (my_uptr->flags & USR_ADMIN))\n    return 0;\n  mst_shown(keytxt, sizeof(keytxt), id, id_len, MST_SHOWN_MAX);\n  return mst_refuse(MSG_DELETE"),
    ("a transaction is let through", "c:masters.c", "  return mst_refuse(MSG_TXN, keytxt, NULL, NULL);", "  return 0;"),
    # ---- the delivery ----
    ("anyone's save is delivered", "c:masters.c", "  if ((my_uptr == NULL) || !(my_uptr->flags & USR_ADMIN))\n    return mst_refuse(MSG_NOTADMIN, keytxt, NULL, NULL);\n", ""),
    ("an unregistered account is accepted", "c:masters.c", "  if (!mst_acc_by_name(acct, &acc))\n    return mst_refuse(MSG_NOACCOUNT, keytxt, acct, NULL);", "  (void)mst_acc_by_name(acct, &acc);"),
    ("the second asterisk is looked for from the first", "c:masters.c", "p2 = memchr(p1 + 1, '*'", "p2 = memchr(p1, '*'"),
    ("a dictionary name is not checked", "c:masters.c", "    if (!mst_file_ok(file))\n      return mst_refuse(MSG_BADKEY, keytxt, NULL, NULL);\n", ""),
    ("an account name is not checked", "c:masters.c", " || !mst_valid_account_name(acct))\n    return mst_refuse(MSG_BADKEY", ")\n    return mst_refuse(MSG_BADKEY"),
    ("the permission preflight is gone", "c:masters.c", "  /* 3 can this process write the file?  Before a lock is taken or a byte is written */\n  why = mst_write_check(path, gname, sizeof(gname));\n  if (why != MST_W_OK) {\n    mst_ctx_close(&cx);\n    goto refuse_rights;\n  }\n", ""),
    ("the lock WAITS", "c:masters.c", "(int16_t)rid_len, TRUE, 0, TRUE);\n    if (lk != 0) {", "(int16_t)rid_len, TRUE, 0, FALSE);\n    if (lk != 0) {"),
    ("the lock is a read lock", "c:masters.c", "(int16_t)rid_len, TRUE, 0, TRUE);\n    if (lk != 0) {", "(int16_t)rid_len, FALSE, 0, TRUE);\n    if (lk != 0) {"),
    ("a lock this process holds is taken again", "c:masters.c", "  if (!check_lock(&fv, (char *)rid, (int16_t)rid_len)) {\n    lk = lock_record", "  {\n    lk = lock_record"),
    ("a lock this process held is let go", "c:masters.c", "  if (took)\n    unlock_record(fv, (char *)rid, (int16_t)rid_len);\n  mst_ctx_close(cx);", "  unlock_record(fv, (char *)rid, (int16_t)rid_len);\n  mst_ctx_close(cx);"),
    ("the lock is kept after a refusal", "c:masters.c", "  if (took)\n    unlock_record(fv, (char *)rid, (int16_t)rid_len);\n  mst_ctx_close(cx);", "  mst_ctx_close(cx);"),
    ("the lock is kept after a write that failed", "c:masters.c", "    return mst_deliver_stop(&cx, &fv, took, rid, rid_len, MSG_WRITEFAIL, keytxt, num, NULL);", "    mst_ctx_close(&cx);\n    return mst_refuse(MSG_WRITEFAIL, keytxt, num, NULL);"),
    ("the lock is kept after a good save", "c:masters.c", "  if (took)\n    unlock_record(&fv, (char *)rid, (int16_t)rid_len);\n  mst_ctx_close(&cx);\n\n  /* 9 the audit line", "  mst_ctx_close(&cx);\n\n  /* 9 the audit line"),
    ("the checksum test is gone", "c:masters.c", "    if (strcmp(cks, rd->cks) != 0) /*", "    if (0) /*"),
    ("master_state is written before the account", "c:masters.c", "  wok = dh_write(adh, (char *)rid, (int16_t)rid_len, data);", "  mst_checksum(data, ncks);\n  svl = snprintf(sv, sizeof(sv), \"%s%c%lld%c\", ncks, MST_FM, (long long)time(NULL), MST_FM);\n  (void)mst_put(cx.st, skey, mk + 2, sv, svl);\n  wok = dh_write(adh, (char *)rid, (int16_t)rid_len, data);"),
    ("master_state is never brought up to date", "c:masters.c", "  (void)mst_put(cx.st, skey, mk + 2, sv, svl);\n", ""),
    ("the audit line is never written", "c:masters.c", "  audit_message(line);\n  return 0;", "  return 0;"),
    ("the audit words are in capitals", "c:masters.c", '"master edit account=%s file=%s id=%s"', '"MASTER EDIT account=%s file=%s id=%s"'),
    ("the account's file is opened and written by the OS", "c:masters.c", "  wok = dh_write(adh, (char *)rid, (int16_t)rid_len, data);", "  (void)open(path, O_WRONLY);\n  wok = dh_write(adh, (char *)rid, (int16_t)rid_len, data);"),
    ("the delivery raises the stage 1 mark", "c:masters.c", "  wok = dh_write(adh, (char *)rid, (int16_t)rid_len, data);", "  mst_inside++;\n  wok = dh_write(adh, (char *)rid, (int16_t)rid_len, data);"),
    ("the keys are built from the account name as typed", "c:masters.c", "mst_keys(which, a->name, file, rid, rid_len, mkey, skey)", "mst_keys(which, acct, file, rid, rid_len, mkey, skey)"),
    ("a stale session is called a mode problem", "c:masters.c", "    case MST_W_STALE:\n      return mst_refuse(MSG_STALE, keytxt, gname, NULL);", "    case MST_W_STALE:\n      return mst_refuse(MSG_MODE, keytxt, whattxt, NULL);"),
    ("a non-member is not told the group twice", "c:masters.c", "return mst_refuse(MSG_NOTMEMBER, keytxt, gname, gname);", "return mst_refuse(MSG_NOTMEMBER, keytxt, gname, NULL);"),
    ("the stage 1 write marks are gone", "c:masters.c", "  mst_inside++;\n  ok = dh_write(dh, key, klen, rec);\n  mst_inside--;", "  ok = dh_write(dh, key, klen, rec);"),
    ("a stage 1 delete bypasses the mark", "c:masters.c", "      (void)mst_mdelete(dh, (char *)gone.d + p + 1, gone.d[p]);", "      (void)dh_delete(dh, (char *)gone.d + p + 1, gone.d[p]);"),
    ("the mark is raised across a stretch of code", "c:masters.c", "  mst_inside++;\n  ok = dh_delete(dh, key, klen);\n  mst_inside--;\n  return ok;", "  mst_inside++;\n  ok = dh_delete(dh, key, klen);\n  return ok;"),
    # ---- can this session write the file ----
    ("the preflight only asks for existence", "c:masters.c", "access(p, (i == 0) ? X_OK : W_OK)", "access(p, F_OK)"),
    ("the owner's class is read after the group bit", "c:masters.c", "  if (sb->st_uid == geteuid())\n    return (sb->st_mode & S_IWUSR) ? MST_W_NOWRITE : MST_W_MODE; /* the owner's class applies to the owner, whatever the group bits say */\n  if (!(sb->st_mode & S_IWGRP))\n    return MST_W_MODE;",
     "  if (!(sb->st_mode & S_IWGRP))\n    return MST_W_MODE;\n  if (sb->st_uid == geteuid())\n    return (sb->st_mode & S_IWUSR) ? MST_W_NOWRITE : MST_W_MODE;"),
    ("stale and not-a-member are swapped", "c:masters.c", "return mst_user_listed(sb->st_gid) ? MST_W_STALE : MST_W_NOTMEMBER;", "return mst_user_listed(sb->st_gid) ? MST_W_NOTMEMBER : MST_W_STALE;"),
    ("the process's groups are not read", "c:masters.c", "  if (mst_gid_in_groups(sb->st_gid))\n    return MST_W_NOWRITE;", "  if (1)\n    return MST_W_NOWRITE;"),
    ("the group list is a big array on the stack", "c:masters.c", "getgroups(0, NULL)", "getgroups(NGROUPS_MAX, NULL)"),
    ("check never says norights", "c:masters.c", '        mst_row(ck, "norights", acct, what, file, w, (int)strlen(w));\n', ""),
    ("check says both", "c:masters.c", "    if (strcasecmp(acct, MST_SYSTEM_ACCOUNT) != 0 && !mst_group_writable(path)) {\n      mst_row(ck, \"nonwritable\", acct, what, file, NULL, 0);\n    } else {", "    if (strcasecmp(acct, MST_SYSTEM_ACCOUNT) != 0 && !mst_group_writable(path)) {\n      mst_row(ck, \"nonwritable\", acct, what, file, NULL, 0);\n    }\n    {"),
    ("the directory's modes are not looked at", "c:masters.c", "  if ((stat(dirpath, &sb) != 0) || ((sb.st_mode & (S_IWGRP | S_IXGRP)) != (S_IWGRP | S_IXGRP)))\n    return FALSE;\n", ""),
    ("the hint is never shown", "bp:masters", "   if hint then display sysmsg(11593)", "   if 0 then display sysmsg(11593)"),
    # ---- the modes of what SD makes ----
    ("the other bits are added too", "c:masters.c", "(ds.st_mode & 07777) | S_IRWXG | S_ISGID", "(ds.st_mode & 07777) | S_IRWXG | S_ISGID | S_IRWXO"),
    ("the mode is set by name", "c:masters.c", "  (void)fchmod(dfd, (mode_t)((ds.st_mode & 07777) | S_IRWXG | S_ISGID));", "  chmod(full, 0775);\n  (void)fchmod(dfd, (mode_t)((ds.st_mode & 07777) | S_IRWXG | S_ISGID));"),
    ("a link can take the place of the directory", "c:masters.c", "open(full, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)", "open(full, O_RDONLY | O_DIRECTORY | O_CLOEXEC)"),
    ("the account directory's group write is not asked", "c:masters.c", "  if ((stat(a->root, &ra) != 0) || !(ra.st_mode & S_IWGRP))\n    return;", "  if (stat(a->root, &ra) != 0)\n    return;"),
    ("what another user made is changed", "c:masters.c", "(ds.st_uid != geteuid()) || ", ""),
    ("what another group has is changed", "c:masters.c", " || (ds.st_gid != ra.st_gid)", ""),
    ("a file of another group is changed", "c:masters.c", " && (fs.st_gid == ra.st_gid)", ""),
    ("any path with voc in it is the VOC", "c:masters.c", 'if (!((strcmp(rel, "voc") == 0) ||', 'if (!((strstr(rel, "voc") != NULL) ||'),
    # ---- the BASIC, the installer and the helper ----
    ("create_account never joins sdsys", "bp:create_account", "      gosub join.sdsys\n\n   case acc.type = \"GROUP\"", "\n   case acc.type = \"GROUP\""),
    ("create_account joins even a member", "bp:create_account", "   if is_grp_member('sdsys', group_name) then return\n", ""),
    ("create_account stops the account when the join fails", "bp:create_account", "      crt sysmsg(11579, acc.name, group_name) ;* master edits cannot be written into account %1 until the sdsys user is in group %2\n", "      crt sysmsg(11579, acc.name, group_name) ;* master edits cannot be written into account %1 until the sdsys user is in group %2\n      goto exit.create\n"),
    ("create_account joins a group account too", "bp:create_account", "      group_name = downcase(\"sdg_\" : acc.name)\n      gosub create.group\n      if err # '' then goto exit.create\n", "      group_name = downcase(\"sdg_\" : acc.name)\n      gosub create.group\n      if err # '' then goto exit.create\n      gosub join.sdsys\n"),
    ("the installer's walk joins any group", "sh:installsdcore.sh", "            sdu_?*)\n                members=", "            *)\n                members="),
    ("the installer's walk changes modes of any group", "sh:installsdcore.sh", "            sdu_?*|sdg_?*)\n                case \"$path\" in", "            *)\n                case \"$path\" in"),
    ("the installer's walk skips the directory-group test", "sh:installsdcore.sh", '                        if [ "$dir_group" = "$group" ]; then', "                        if true; then"),
    ("the installer's walk does not judge the success line", "sh:installsdcore.sh", "                                    *'group-write: 0 directories and 0 file(s) changed'*) n_ok=$((n_ok+1)) ;;\n", ""),
    ("the installer's walk can stop the install", "sh:installsdcore.sh", '    echo "  The sdsys user is put in the group of every account, and the VOC', '    exit 1; echo "  The sdsys user is put in the group of every account, and the VOC'),
    ("the installer's walk is called twice", "sh:installsdcore.sh", 'join_sdsys_groups "$sdsysdir/accounts"\n\n# 19 Oct 26 dm - S.67 stage 1', 'join_sdsys_groups "$sdsysdir/accounts"\njoin_sdsys_groups "$sdsysdir/accounts"\n\n# 19 Oct 26 dm - S.67 stage 1'),
    ("sdsys-join replaces the groups", "sh:sd-elevate", 'cmd=(usermod -aG "$1" -- sdsys)', 'cmd=(usermod -G "$1" -- sdsys)'),
    ("sdsys-join takes the user from sudo", "sh:sd-elevate", 'cmd=(usermod -aG "$1" -- sdsys)', 'cmd=(usermod -aG "$1" -- "${SUDO_USER:-sdsys}")'),
    ("sdsys-join skips the group rule", "sh:sd-elevate", '    require_account_group "$1"\n    [[ $DRY -eq 1 ]] || id -u sdsys', '    [[ $DRY -eq 1 ]] || id -u sdsys'),
    ("group-write needs no root", "sh:sd-elevate", '    need_root\n    python3 -c "$GW_PY"', '    python3 -c "$GW_PY"'),
    ("group-write forgets the worker's status", "sh:sd-elevate", '"$GW_OWNERS" "$DRY"\n    exit $?', '"$GW_OWNERS" "$DRY"\n    exit 0'),
    ("group-write skips the account rule", "sh:sd-elevate", '    require_group_write_target "$1"\n    printf', '    printf'),
    ("an ordinary session may ask why a save was refused", "c:masters.c", "  if (!admin) {\n    mst_status(&out, MSA_REFUSED);\n    mst_answer(result, &out);\n    return;\n  }\n",
     "  if (strcmp(op, \"refusal\") == 0) {\n    mst_status(&out, MSA_OK);\n    mst_fld_s(&out, masters_refusal_text());\n    mst_answer(result, &out);\n    return;\n  }\n  if (!admin) {\n    mst_status(&out, MSA_REFUSED);\n    mst_answer(result, &out);\n    return;\n  }\n"),
    ("the refusal op answers something else", "c:masters.c", "    mst_fld_s(&out, masters_refusal_text());", "    mst_fld_s(&out, \"\");"),
    ("ED does not ask why at the unload", "bp:ed", "            gosub error\n            gosub master.refusal\n            goto abort.unload", "            gosub error\n            goto abort.unload"),
    ("ED asks why for every write error", "bp:ed", "   if write.status = 8910 then\n      refusal.reply", "   if 1 then\n      refusal.reply"),
    ("ED asks and says nothing", "bp:ed", "      if refusal.reply<2> # '' then display refusal.reply<2>", "      if refusal.reply<2> # '' then null"),
    ("CHECK.MASTERS does not say why a save was refused", "bp:masters", "   display sysmsg(11569, ans<2>, ans<3>)\n   gosub last.refusal\n", "   display sysmsg(11569, ans<2>, ans<3>)\n"),
    ("LIST.MASTER.PENDING does not say why", "bp:masters", "   gosub last.refusal\n   @system.return.code = 0\n   return\n\n* ======================================================================\n* last.refusal", "   @system.return.code = 0\n   return\n\n* ======================================================================\n* last.refusal"),
    # ---- wiring ----
    ("the map forgets messages 11580 to 11589", "txt:regress-map.txt", "sdsys/messages/1158[0-9]     : masters\n", ""),
    ("the map forgets sd-elevate", "txt:regress-map.txt", "gplbld/sd-elevate            : none\n", ""),
    ("the witness is missing", "file:witness-masters.sh", X(r"(?s).*"), ""),

    # ================== THE INDEPENDENT VERIFIER'S FINDINGS, 19 OCT 26 ==================
    # ---- F1 the modes ----
    ("the master files' dictionaries are left to the umask", "c:masters.c", "      if (chmod(dirpath, 0700) == 0)\n        modes++;\n      if (getuid() == 0)\n        (void)chown(dirpath, want_uid, sys_gid);",
     "      if (getuid() == 0)\n        (void)chown(dirpath, want_uid, sys_gid);"),
    ("the owner of a master file is given a group that does not exist", "c:masters.c", "chown(q, want_uid, sys_gid)", "chown(q, want_uid, sdusers_gid)"),
    ("setup does not put the umask back at the end", "bp:masters_setup", "   close sv\n   if umask(um) then null\n\n   ans = kernel", "   close sv\n\n   ans = kernel"),
    ("setup leaves the umask changed after a failed dictionary", "bp:masters_setup", "            close sv\n            if umask(um) then null\n            report = 2 : @fm : 'cannot make ' : nm : '.dic' : @fm : made",
     "            close sv\n            report = 2 : @fm : 'cannot make ' : nm : '.dic' : @fm : made"),
    # ---- F2 the table of accounts ----
    ("mst_deliver keeps a pointer into the table of accounts", "c:masters.c", "  const MST_ACC *a = &acc;\n  MST_CTX cx;", "  const MST_ACC *a = &acc_tab[0];\n  MST_CTX cx;"),
    ("mst_acc_by_name hands back something other than the entry found", "c:masters.c", "      *out = acc_tab[i];", "      *out = acc_tab[0];"),
    ("the check walks the live table", "c:masters.c", "mst_check_account(&cx, &ck, &all[i]);", "mst_check_account(&cx, &ck, &acc_tab[i]);"),
    ("the sync walks the live table", "c:masters.c", "(void)mst_sync_account(&cx, &all[i], &r);", "(void)mst_sync_account(&cx, &acc_tab[i], &r);"),
    ("the sorted index of accounts is leaked and kept", "c:masters.c", "  free(acc_tab);\n  free(acc_sorted);\n", "  free(acc_tab);\n"),
    ("the drain keeps a pointer into the table", "c:masters.c", "      MST_ACC acc; /* a copy: see the note on acc_tab */\n      const MST_ACC *a = mst_acc_by_name(e->acct, &acc) ? &acc : NULL;",
     "      MST_ACC acc;\n      const MST_ACC *a = (mst_acc_by_name(e->acct, &acc), &acc_tab[0]);"),
    # ---- F3 what the session read ----
    ("a save is judged against master_state again", "c:masters.c", "  rd = mst_read_find(which, (const char *)id, id_len);", "  rd = NULL;"),
    ("a read is not noted", "c:op_dio3.c", "        masters_note_read(dh_file, id, id_len, str, dh_err);\n", ""),
    ("a read is noted before the record is read", "c:op_dio3.c", "      str = dh_read(dh_file, id, id_len, actual_id);\n      /* 19 Oct 26 S.67 (verifier F3): a read of voc_master or dict_master is remembered, so that a later save is judged against the record that was READ (masters.c) */\n      if (!(dh_file->flags & DHF_MST_NOMASTER))\n        masters_note_read(dh_file, id, id_len, str, dh_err);",
     "      if (!(dh_file->flags & DHF_MST_NOMASTER))\n        masters_note_read(dh_file, id, id_len, str, dh_err);\n      str = dh_read(dh_file, id, id_len, actual_id);"),
    ("a blind save of a record the account has is accepted", "c:masters.c", "    if (cks[0] != '\\0') /* not read, and the account has the record */\n      return mst_deliver_stop(&cx, &fv, took, rid, rid_len, MSG_NOTREAD, keytxt, NULL, NULL);\n", ""),
    ("a blind save puts back a record the account deleted", "c:masters.c", "    if (scks[0] != '\\0') /* not read, the account has none now, and master_state remembers that it had one: the account deleted it */\n      return mst_deliver_stop(&cx, &fv, took, rid, rid_len, MSG_CHANGED, keytxt, a->name, NULL);\n", ""),
    ("a save does not remember what it wrote", "c:masters.c", "  mst_read_put(which, (const char *)id, id_len, ncks);\n", ""),
    ("the read table holds one key", "c:masters.c", "#define MST_READ_N 128", "#define MST_READ_N 1"),
    ("a read that found no record is not noted", "c:masters.c", "  else if (err == DHE_RECORD_NOT_FOUND)\n    cks[0] = '\\0';\n  else\n    return;", "  else\n    return;"),
    ("a read is noted whatever went wrong", "c:masters.c", "  else if (err == DHE_RECORD_NOT_FOUND)\n    cks[0] = '\\0';\n  else\n    return;", "  else\n    cks[0] = '\\0';"),
    ("a read of every file is noted", "c:masters.c", "  if ((kind = mst_master_kind(dh)) == 0)\n    return;\n  if (err == 0)\n    mst_checksum(rec, cks);", "  kind = MST_VOC;\n  if (err == 0)\n    mst_checksum(rec, cks);"),
    # ---- F4 the comparison inside the write ----
    ("dh_write does not compare when it has found the record", "c:dh_write.c", "        if (masters_cas_on) {\n          STRING_CHUNK* cas_cur", "        if (0) {\n          STRING_CHUNK* cas_cur"),
    ("dh_write does not compare when it has found none", "c:dh_write.c", "  if (masters_cas_on && (masters_cas_check(dh_file, id, id_len, NULL, FALSE) != 0)) {", "  if (0) {"),
    ("the comparison is never armed", "c:masters.c", "  masters_cas_on = 1;\n  wok = dh_write(", "  wok = dh_write("),
    ("the comparison stays armed after the write", "c:masters.c", "  masters_cas_on = 0;\n  if (!wok) {", "  if (!wok) {"),
    ("the comparison is not spent when it answers", "c:masters.c", "    return 0; /* not the write that was armed */\n  masters_cas_on = 0;\n", "    return 0; /* not the write that was armed */\n"),
    ("the comparison answers for any file", "c:masters.c", "if (!masters_cas_on || (dh != mst_cas.dh) || (id_len != mst_cas.idlen)", "if (!masters_cas_on || (id_len != mst_cas.idlen)"),
    ("the comparison answers for any key", "c:masters.c", " || (memcmp(id, mst_cas.id, (size_t)id_len) != 0))\n    return 0; /* not the write that was armed */", ")\n    return 0; /* not the write that was armed */"),
    ("a refused write keeps the new big record's chain", "c:dh_write.c", "            if (big_rec) /* Give away big record space just written */\n              (void)dh_free_big_rec(dh_file, new_big_rec_head, NULL);\n            goto exit_dh_write;\n          }\n        }",
     "            goto exit_dh_write;\n          }\n        }"),
    ("the comparison forgets that a missing record has no checksum", "c:masters.c", "  if (found)\n    mst_checksum(current, cks);\n  else\n    cks[0] = '\\0';\n  if (strcmp(cks, mst_cas.expect) == 0)", "  mst_checksum(current, cks);\n  if (strcmp(cks, mst_cas.expect) == 0)"),
    ("the comparison is made with the version of the last drain", "c:masters.c", "  snprintf(mst_cas.expect, sizeof(mst_cas.expect), \"%s\", cks);", "  snprintf(mst_cas.expect, sizeof(mst_cas.expect), \"%s\", scks);"),
    # ---- F5 an unreadable account keeps its dictionary copies ----
    ("an unlistable directory is a complete list", "c:masters.c", "    closedir(d);\n  } else {\n    complete = FALSE;\n  }", "    closedir(d);\n  }"),
    ("an unreadable VOC is a complete list", "c:masters.c", "    if (!cx->last_absent)\n      complete = FALSE; /* the VOC is there and cannot be opened: the dictionaries it names are not known */", "    ;"),
    ("a VOC that cannot be read through is a complete list", "c:masters.c", "  } else if (!mst_scan_ids(vdh, &vids)) {\n    complete = FALSE;\n  } else {", "  } else if (!mst_scan_ids(vdh, &vids)) {\n    ;\n  } else {"),
    ("the sync prunes dictionary copies from an incomplete list", "c:masters.c", "  if (dcomplete) {\n    MST_IDS gone", "  {\n    MST_IDS gone"),
    ("the sync does not count the incomplete list", "c:masters.c", "  if (!dcomplete)\n    cx->errs++; /* the list of the account's dictionaries is not complete: the pruning below is skipped, and the sync says so */\n", ""),
    ("the check calls copies extra from an incomplete list", "c:masters.c", "for (p = 0; dcomplete && (p < dkeys.len);", "for (p = 0; p < dkeys.len;"),
    ("the check does not say the list is incomplete", "c:masters.c", '    mst_row(ck, "unreadable", a->name, "dict", NULL, NULL, 0); /* the list of its dictionaries is not complete: no copy is called extra below */\n', ""),
    # ---- F6 a link out of the account ----
    ("a link out of the account is opened", "c:masters.c", "  if (!mst_inside_root(path, root, real, sizeof(real))) {\n    absent = TRUE;", "  if (0) {\n    absent = TRUE;"),
    ("a link out of the account is taken for a file that cannot be opened", "c:masters.c", "    absent = TRUE; /* a link out of the account: not the account's file */", "    absent = FALSE;"),
    ("the file opened is not compared with the file resolved", "c:masters.c", "if (((fe->device != 0) || (fe->inode != 0)) && ((fe->device != (u_int32_t)rs.st_dev)", "if (0 && ((fe->device != (u_int32_t)rs.st_dev)"),
    ("the directory scan takes a dictionary that links out", "c:masters.c", "      if (!mst_inside_root(dpath, a->root, lreal, sizeof(lreal)))\n        continue; /* a link out of the account: another account's dictionary, or nobody's (verifier F6) */\n", ""),
    ("the root test is a prefix without its slash", "c:masters.c", "(strncmp(r, root, rl) == 0) && (r[rl] == '/')", "(strncmp(r, root, rl) == 0)"),
    # ---- F7 each master read once ----
    ("syncall builds no index", "c:masters.c", "      mst_ctx_index(&cx, TRUE);\n", ""),
    ("the check builds no index", "c:masters.c", "        mst_ctx_index(&cx, FALSE); /* each master read once, not once per account (verifier F7) */\n", ""),
    ("the sync scans the master for each account", "c:masters.c", "  if (!mst_keys_of(cx, MST_IX_VOC, prefix, &vkeys) || !mst_keys_of(cx, MST_IX_DICT, prefix, &dkeys)) {\n    cx->errs++;", "  if (!mst_scan_prefixed(cx->vm, prefix, &vkeys) || !mst_scan_prefixed(cx->dm, prefix, &dkeys)) {\n    cx->errs++;"),
    ("the check scans the master for each account", "c:masters.c", "  if (!mst_keys_of(cx, MST_IX_VOC, prefix, &vkeys) || !mst_keys_of(cx, MST_IX_DICT, prefix, &dkeys)) {\n    mst_row(ck,", "  if (!mst_scan_prefixed(cx->vm, prefix, &vkeys) || !mst_scan_prefixed(cx->dm, prefix, &dkeys)) {\n    mst_row(ck,"),
    ("the indexes are not freed", "c:masters.c", "      mst_index_free(cx->ix[i]);\n      free(cx->ix[i]);\n", ""),
    ("the prefix comparison does not fold", "c:masters.c", "    int x = mst_fold((unsigned char)key[i]);\n    int y = mst_fold((unsigned char)prefix[i]);", "    int x = (unsigned char)key[i];\n    int y = mst_fold((unsigned char)prefix[i]);"),
    ("the drain scans the whole master for each whole-file line", "c:masters.c", "(have_v = mst_index_build(cx->vm, &vall))", "(have_v = mst_scan_ids(cx->vm, &vall.ids))"),
    ("the account search is a walk again", "c:masters.c", "    int c = strcasecmp(acc_tab[acc_sorted[mid]].name, name);", "    int c = strcasecmp(acc_tab[mid].name, name);"),
    # ---- the journal ----
    ("a short write leaves the front of a line", "c:masters.c", "      if ((w > 0) && have_size)\n        (void)ftruncate(fd, st.st_size);\n", ""),
    ("a short write cuts the journal back without knowing its size", "c:masters.c", "      if ((w > 0) && have_size)\n        (void)ftruncate(fd, st.st_size);", "      if (w > 0)\n        (void)ftruncate(fd, st.st_size);"),
    ("the drain does not end an unterminated line", "c:masters.c", "        (void)pwrite(fd, \"\\n\", 1, st.st_size);", "        ;"),
    ("the drain ends every last line", "c:masters.c", "      if ((pread(fd, &last, 1, st.st_size - 1) == 1) && (last != '\\n'))", "      if (pread(fd, &last, 1, st.st_size - 1) == 1)"),
    ("the drain ends an unterminated line without the semaphore", "c:masters.c", "  } else if (can_write && (consumed < (long)st.st_size)) {", "  } else if (can_write && (consumed < (long)st.st_size) && (st.st_size > 0)) {\n    ;\n  } else if (0) {"),
    # ---- the file part of a key ----
    ("a dictionary key in capitals is not tried in lower case", "c:masters.c", "  if ((adh == NULL) && cx.last_absent && (which == MST_DICT)) {", "  if (0) {"),
    ("the lower case retry is made for a file that cannot be opened too", "c:masters.c", "  if ((adh == NULL) && cx.last_absent && (which == MST_DICT)) {", "  if ((adh == NULL) && (which == MST_DICT)) {"),
    # ---- the messages ----
    ("a message is longer than the room for its worst arguments", "msg:11586", "Sign on again and repeat the edit. Nothing was changed", "Sign on again and repeat the edit, which is the only thing to do once the session has been started before the account was made. Nothing was changed"),
    ("a refusal no longer says that nothing was changed", "msg:11596", " Nothing was changed", ""),
    ("the key is shown in 120 characters again", "c:masters.c", "#define MST_SHOWN_MAX 60", "#define MST_SHOWN_MAX 120"),
    ("the new messages are in the BASIC form", "msg:11595", "Master record %s not saved", "Master record %1 not saved"),
    # ---- the witness, the headers, the map ----
    ("the witness deletes a register record it did not make", "file:witness-masters.sh", 'if [ "$MADE" -eq 1 ] && [ -e "$REGISTER/$a" ]; then', 'if [ -e "$REGISTER/$a" ]; then'),
    ("the witness stops stating the modes of the master files", "file:witness-masters.sh", "6a master files: owner, group and mode - every one", "6a the files - every one"),
    ("the witness lets a member of sdusers be", "file:witness-masters.sh", '"DENIED DENIED DENIED" "$R1 $R2 $R3"', '"DENIED" "$R1"'),
    ("a header names a worktree", "file:sandbox-masters.py", "#   SDBOX_KEYSET=3 python3 /home/don/Projects/SDCore4Linux/sdb_ai", "#   SDBOX_KEYSET=3 python3 /home/don/Projects/SDCore4Linux" + "-wt-s67/sdb_ai"),
    ("the map forgets op_dio3 for the master files", "txt:regress-map.txt", "gplsrc/op_dio3.c             : @files @seq prof lockown editgates netfile shared masters", "gplsrc/op_dio3.c             : @files @seq prof lockown editgates netfile shared"),
    ("the map forgets the editor for the master files", "txt:regress-map.txt", "sdsys/gpl.bp/ed              : @editors edext editgates eofkeys masters", "sdsys/gpl.bp/ed              : @editors edext editgates eofkeys"),
    ("the map forgets the lock for the master files", "txt:regress-map.txt", "gplsrc/op_lock.c             : lock-b6 listu-a5 conf-b1 cll @files netfile masters", "gplsrc/op_lock.c             : lock-b6 listu-a5 conf-b1 cll @files netfile"),
    ("the map forgets the new messages", "txt:regress-map.txt", "sdsys/messages/1159[0-6]     : masters\n", "sdsys/messages/1159[0-4]     : masters\n"),
]
def _installer_after_chown(srcs):
    """The installer's upgrade_masters block moved to just after the line that hands the register to sdsys."""
    t = srcs["sh:installsdcore.sh"]
    i = t.index("om_out=$(sudo")
    j = t.index("fi\n", t.index("WARNING: the master files were not all set up or filled.")) + 3
    block = t[i:j]
    rest = t[:i] + t[j:]
    chown = 'sudo chown -R sdsys:sdusers "$sdsysdir/accounts"'
    return dict(srcs, **{"sh:installsdcore.sh": rest.replace(chown, chown + "\n" + block, 1)})


# mutants that are not plain text replacements (they build the mutated source themselves)
LAMBDA_MUTANTS = {
    "the verbs are in newvoc": lambda srcs: dict(srcs, **{"newvoc.list": srcs["newvoc.list"] + "\nsync.masters"}),
    "a record opcode calls the hook (a write inside a transaction is journalled before COMMIT)": lambda srcs: dict(srcs, **{"c:op_dio3.c": srcs["c:op_dio3.c"] + "\nstatic void probe(void) { masters_note_record(0, 'w', \"\", 0); }\n"}),
    "the installer runs it after the register is handed over": lambda srcs: _installer_after_chown(srcs),
}


def run(srcs):
    return checks(srcs)


def main():
    srcs = load()
    if "--selftest" in sys.argv:
        base = run(srcs)
        bad = [i for i, ok, d in base if not ok]
        if bad:
            print("test-masters-units: the unmutated source already fails: %s" % bad)
            return 2
        missed = 0
        n = 0
        for label, name, old, new in MUTANTS:
            n += 1
            try:
                if label in LAMBDA_MUTANTS:
                    ms = LAMBDA_MUTANTS[label](srcs)
                    if ms == srcs:
                        raise KeyError("the mutation changed nothing")
                else:
                    ms = mutate(srcs, name, old, new)
                rows = checks(ms)
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
        print("\ntest-masters-units --selftest: %d mutants, %d missed" % (n, missed))
        return 1 if missed else 0
    rows = run(srcs)
    failed = 0
    for i, ok, d in rows:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", i, "" if ok or not d else "   <- " + d))
        failed += 0 if ok else 1
    print("\ntest-masters-units: %d checks, %d failed" % (len(rows), failed))
    print("NOT MEASURED HERE: whether a line is written, a copy equals its account's record, CHECK.MASTERS finds a planted difference or a mode is right.  That is sandbox-masters.py\n"
          "(ordinary sessions on a private SD, the journal and the master files read as evidence).")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
