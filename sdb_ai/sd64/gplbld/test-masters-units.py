#!/usr/bin/env python3
"""test-masters-units.py - the master files (S.67 stage 1), as invariants read off the source.

  python3 /home/don/Projects/SDCore4Linux-wt-s67/sdb_ai/sd64/gplbld/test-masters-units.py
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

MSG_FIRST, MSG_LAST = 11560, 11578
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
    get("txt:regress.sh", os.path.join(HERE, "regress.sh"))
    get("txt:regress-map.txt", os.path.join(HERE, "regress-map.txt"))
    get("txt:gpl.src", os.path.join(SD64, "gpl.src"))
    for v in ("sync.masters", "check.masters", "list.master.pending"):
        get("voc:" + v, os.path.join(SDSYS, "voc_template", v))
    srcs["newvoc.list"] = "\n".join(sorted(os.listdir(os.path.join(SDSYS, "newvoc"))))
    srcs["voc_template.list"] = "\n".join(sorted(os.listdir(os.path.join(SDSYS, "voc_template"))))
    for n in range(MSG_FIRST, MSG_LAST + 1):
        p = os.path.join(MSGDIR, str(n))
        srcs["msg:%d" % n] = open(p, encoding="utf-8", errors="replace").read() if os.path.exists(p) else None
    for t in ("sandbox-masters.py", "test-masters-units.py"):
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
    ck("N9 every message the verb program cites exists and lies in 11560 to 11578, and its substitution never takes more than 4 arguments (the compiler's SYSMSG limit)",
       all(MSG_FIRST <= n <= MSG_LAST or n == 2001 for n in cited) and all(texts.get(n) is not None for n in cited if n != 2001)
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
    ck("H8 the record opcodes and the transaction code do NOT call the hook: it is in the DH layer, which a COMMIT passes through (a call in op_dio3.c or txn.c would deliver "
       "an uncommitted write and a rolled-back one)", "masters_" not in C("op_dio3.c") and "masters_" not in C("txn.c"), "")
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
       "master files' directories 0770 and their subfiles 0660",
       "O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0620" in ini and "fchmod(fd, 0620)" in ini and "getpwnam(\"sdsys\")" in ini and "getgrnam(\"sdusers\")" in ini
       and "chmod(dirpath, 0770)" in ini and "chmod(q, 0660)" in ini and len(re.findall(r"O_CREAT", m)) == 1, "")

    # ---- D. the drain -----------------------------------------------------------------------------------------------------------------
    oh = func_body(m, "void masters_open_hook(const char *canon)")
    ck("D1 masters_open_hook does nothing unless the session is the administrator and the path is one of the three master files, and it cannot recurse (busy)",
       ordered(oh, "busy ||", "USR_ADMIN", "mst_is_master_path(canon)", "busy = TRUE;", "mst_drain(&cx, -1, &dr)", "busy = FALSE;"), "")
    ck("D2 the three master paths are voc_master, dict_master and master_state under the SYSTEM directory as the OS resolves it (not a name that a VOC entry could give another file)",
       "mst_sysdir_real()" in func_body(m, "Private bool mst_is_master_path(const char *canon)") and "MST_VOC_MASTER" in func_body(m, "Private bool mst_is_master_path(const char *canon)")
       and "MST_DICT_MASTER" in func_body(m, "Private bool mst_is_master_path(const char *canon)") and "MST_STATE" in func_body(m, "Private bool mst_is_master_path(const char *canon)"), "")
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
       ordered(dr, "known = FALSE;", "res->skipped++;", "qsort(ev, (size_t)nev, sizeof(MST_EVT), mst_evt_cmp);", "mst_sync_file(cx, kind, a->name, a->root, e->file, &slice, strlen(sub));",
               "for (j = i + 1;", "mst_sync_key(cx, kind, a->name, a->root, e->file, e->id, e->id_len);"), "")
    ck("D7 ...the account of a line is found in the register by NAME and its directory comes from the register, never from the line (a line cannot name a path)",
       "mst_acc_by_name(e->acct)" in dr and "a->root" in dr and "e->file, &slice" in dr and "root = " not in dr, "")
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
       ordered(sk, "mst_keys(kind, acct, file, id, id_len, mkey, skey) < 0", "return MS_LONG;", "dh_read(adh,", "dh_read(mdh, mkey", "!mst_str_equal(rec, mrec)", "dh_write(mdh, mkey")
       and ordered(sk, "if (!found) {", "dh_delete(mdh, mkey", "dh_delete(cx->st, skey") and ordered(sk, "mst_checksum(rec, cks);", "strcmp(cks, scks) != 0", "mst_put(cx->st, skey"), "")
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
       "no master key backs", ordered(cs, "mst_sync_file(cx, MST_VOC", "mst_sync_file(cx, MST_DICT", "mst_delete_keys(cx, MST_DICT, &gone)", "(void)mst_scan_prefixed(cx->st, sub, &skeys)", "dh_delete(cx->st"), "")
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
    ck("K3 ...the ops are exactly: ready note init pending peek drain sync syncbegin syncend drop check accounts",
       sorted(re.findall(r'strcmp\(op, "(\w+)"\) == 0', rq)) == sorted(["ready", "note", "init", "pending", "peek", "drain", "sync", "syncbegin", "syncend", "drop", "check", "accounts"]),
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
       rq.count("MSA_NOACC") == 2 and "mst_acc_by_name(arg)" in rq, "")

    od = func_body(m, "Private long mst_drop_orphans(MST_CTX *cx)")
    oc = func_body(m, "Private void mst_check_orphans(MST_CTX *cx, MST_CHECK *ck)")
    ir = func_body(m, "Private bool mst_in_register(const char *name)")
    ck("K9 an account's copies are an orphan's only when the account is not in the register: an empty table (a register that could not be read) makes no orphan, and a name whose register "
       "RECORD exists is an account even if a transient failure kept it out of the table",
       ordered(od, "mst_acc_load();", "if (acc_n == 0)", "return 0;", "mst_in_register(name)") and ordered(oc, "mst_acc_load();", "if (acc_n == 0)", "return;", "mst_in_register(name)")
       and "strcasecmp(acc_tab[i].name, name) == 0" in ir and '"%s%caccounts%c%s"' in ir and "stat(p, &sb) == 0" in ir and "mst_valid_account_name(name)" in ir, "")

    # ---- B. the BASIC -------------------------------------------------------------------------------------------------------------------
    mp = B("masters")
    ck("B1 the verb program tests for the administrator BEFORE it calls the kernel, and says 2001; it dispatches on the first word of the sentence in lower case, for exactly three verbs",
       ordered(mp, "if not(kernel(K$ADMINISTRATOR, -1)) then", "stop sysmsg(2001)", "verb = downcase(field(words, ' ', 1))", "kernel(K$MASTERS")
       and mp.find("kernel(K$MASTERS") > mp.find("stop sysmsg(2001)") > mp.find("kernel(K$ADMINISTRATOR") >= 0 and sorted(re.findall(r"case verb = '([\w.]+)'", mp)) == ["check.masters", "list.master.pending", "sync.masters"], "")
    ck("B2 SYNC.MASTERS: sets up first (!masters_setup), applies the journal before a one-account sync, and for no account notes the position (syncbegin), syncs every account and finishes with "
       "syncend with that position; it audits in lower case",
       ordered(mp, "call !masters_setup(rep)", "gosub drain.journal", "'sync.masters account='", "gosub sync.one") and ordered(mp, "'syncbegin'", "gosub sync.one", "'syncend' : @fm : s0")
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
    ck("B7 upgrade_masters sets up first, notes the position, copies every registered account, ends with syncend, counts failures, and prints COMPLETE only when none failed",
       ordered(um, "call !masters_setup(rep)", "'syncbegin'", "'accounts'", "'sync' : @fm : account", "'syncend' : @fm : s0", "if failed = 0 then crt 'COMPLETE'")
       and um.count("COMPLETE") == 1, "")
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
    ck("R3 the two test files exist (this one and the sandbox suite)", all(srcs.get("file:" + t) for t in ("sandbox-masters.py", "test-masters-units.py")), "")
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
    ("a failed append is silent", "c:masters.c", "  } else if (write(fd, line, (size_t)len) != len) {\n    mst_flag(MST_F_STALE);\n  }", "  } else if (write(fd, line, (size_t)len) != len) {\n    ;\n  }"),
    ("the size limit is not tested", "c:masters.c", "  if ((fstat(fd, &st) == 0) && (st.st_size >= MST_JOURNAL_CAP)) {\n    mst_flag(MST_F_RESYNC);\n  } else if (", "  if (0) {\n    mst_flag(MST_F_RESYNC);\n  } else if ("),
    ("the size limit sets the wrong flag", "c:masters.c", "    mst_flag(MST_F_RESYNC);\n  } else if (write", "    mst_flag(MST_F_STALE);\n  } else if (write"),
    ("the append is not under the semaphore", "c:masters.c", "  StartExclusive(ERRLOG_SEM, 72);\n", ""),
    ("the line is written in two pieces", "c:masters.c", "  } else if (write(fd, line, (size_t)len) != len) {", "  } else if ((write(fd, line, 1) != 1) || (write(fd, line + 1, (size_t)len - 1) != len - 1)) {"),
    ("the line carries the record's data", "c:masters.c", "Private void mst_journal_line(int fd, int kind, char op, const char *acct, const char *file, const char *id, int id_len) {",
     "Private void mst_journal_line(int fd, int kind, char op, const char *acct, const char *file, const char *id, int id_len, STRING_CHUNK *data) {"),
    ("setup makes the journal only after the files", "bp:masters_setup", "   ans = kernel(K$MASTERS, 'init')\n   if ans<1> # 0 then\n      close sv\n", "   ans = ''\n   if ans<1> # 0 then\n      close sv\n"),
    ("an id with a space is not encoded", "c:masters.c", "if ((c <= 0x20) || (c == '%')", "if ((c < 0x20) || (c == '%')"),
    ("a percent sign is not encoded", "c:masters.c", " || (c == '%') || (c >= 0x7F)", " || (c >= 0x7F)"),
    ("the entry buffer is a page", "c:masters.c", "char line[1600];", "char line[8192];"),
    ("the flag is set with a plain or", "c:masters.c", "  __sync_fetch_and_or(&sysseg->masters_flags, bit);", "  sysseg->masters_flags |= bit;"),
    ("the journal is made with the wrong mode", "c:masters.c", "O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0620)", "O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0666)"),
    ("the master files are left open to the group", "c:masters.c", "if (chmod(dirpath, 0770) == 0)", "if (chmod(dirpath, 0775) == 0)"),
    # ---- the drain ----
    ("any session drains on opening a master", "c:masters.c", "if (busy || (my_uptr == NULL) || !(my_uptr->flags & USR_ADMIN) || (canon == NULL) || !mst_is_master_path(canon))", "if (busy || (canon == NULL) || !mst_is_master_path(canon))"),
    ("the drain can recurse", "c:masters.c", "  if (busy || (my_uptr", "  if ((my_uptr"),
    ("the drain does not lock the journal", "c:masters.c", "  if (flock(fd, LOCK_EX) != 0) {\n    close(fd);\n    return MSA_ERR;\n  }\n  if (fstat(fd, &st) != 0) {", "  if (fstat(fd, &st) != 0) {"),
    ("the journal is truncated without the semaphore", "c:masters.c", "    StartExclusive(ERRLOG_SEM, 74);\n", ""),
    ("the journal is truncated without looking at the size again", "c:masters.c", "(fstat(fd, &st) == 0) && ((long)st.st_size == consumed) && (ftruncate(fd, 0) == 0)", "(ftruncate(fd, 0) == 0)"),
    ("the journal is truncated when only part was taken", "c:masters.c", "(consumed > 0) && (consumed == (long)st.st_size)", "(consumed > 0)"),
    ("the state is written when nothing moved", "c:masters.c", "  if ((res->offset_after != saved_off) || ((long)st.st_ino != saved_ino) || (res->keys + res->files > 0))\n    mst_jstate_put(", "  mst_jstate_put("),
    ("lines of accounts that are not registered are applied", "c:masters.c", "      if (known)\n        ev[keep++] = ev[i];\n      else\n        res->skipped++;", "      ev[keep++] = ev[i];"),
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
    ("a record the account lacks stays in the master", "c:masters.c", "      if (!dh_delete(mdh, mkey, (int16_t)mk)) {", "      if (0) {"),
    ("the state is written every time", "c:masters.c", "  if (strcmp(cks, scks) != 0) {", "  if (1) {"),
    ("a file that cannot be read through has its master copies deleted", "c:masters.c", "  } else if ((adh != NULL) || !absent) {\n    cx->errs++; /* could not be opened, or could not be read through: leave the master copies alone */\n    mst_ids_free(&ids);\n    return;\n  } else {", "  } else if (adh != NULL) {\n    cx->errs++;\n  } else {"),
    ("a file that cannot be opened is taken for one that is not there", "c:masters.c", "(stat(sub, &sb) != 0) && (errno == ENOENT);", "TRUE;"),
    ("sync_key deletes the master copy of a file it cannot open", "c:masters.c", "  } else if (!cx->last_absent) {\n    cx->errs++; /* the file is there and cannot be opened: say nothing about its records, and delete no copy of them */\n    return MS_ERR;\n  }", "  }"),
    ("check calls an unopenable file clean", "c:masters.c", "  if ((adh == NULL) && !cx->last_absent) { /* there, and cannot be opened: nothing can be said about its records */\n    mst_row(ck, \"unreadable\", acct, what, file, NULL, 0);\n    return;\n  }\n", ""),
    ("the nearest account does not win", "c:masters.c", "return (a->rlen > b->rlen) ? -1 : 1;", "return (a->rlen < b->rlen) ? -1 : 1;"),
    ("a VOC may be any file called voc below the root", "c:masters.c", '  if ((strcmp(rel, "voc") == 0) || (strncmp(rel, "voc/", 4) == 0))', '  if (strstr(rel, "voc") != NULL)'),
    ("the sync forgets the dictionaries the account no longer has", "c:masters.c", "    mst_delete_keys(cx, MST_DICT, &gone);\n    mst_ids_free(&gone);\n  }\n\n  /* state records", "    mst_ids_free(&gone);\n  }\n\n  /* state records"),
    # ---- the ops ----
    ("an ordinary session may init", "c:masters.c", "  if (!admin) {\n    mst_status(&out, MSA_REFUSED);\n    mst_answer(result, &out);\n    return;\n  }\n\n  if (strcmp(op, \"init\") == 0) {", "  if (strcmp(op, \"init\") == 0) {"),
    ("the administrator test comes after the first op", "c:masters.c", "  if (strcmp(op, \"ready\") == 0) {", "  if (strcmp(op, \"drain\") == 0) {\n    mst_status(&out, MSA_OK);\n    mst_answer(result, &out);\n    return;\n  }\n  if (strcmp(op, \"ready\") == 0) {"),
    ("admin is anyone", "c:masters.c", "bool admin = (my_uptr != NULL) && ((my_uptr->flags & USR_ADMIN) != 0);", "bool admin = (my_uptr != NULL);"),
    ("note does more than note", "c:masters.c", "    masters_note_name(arg, 'n');\n    mst_status(&out, MSA_OK);", "    masters_note_name(arg, 'n');\n    (void)mst_init(&out);\n    mst_status(&out, MSA_OK);"),
    ("a new op", "c:masters.c", '  } else if (strcmp(op, "accounts") == 0) {', '  } else if (strcmp(op, "wipe") == 0) {\n    mst_status(&out, MSA_OK);\n  } else if (strcmp(op, "accounts") == 0) {'),
    ("check repairs", "c:masters.c", '      mst_row(ck, "differs", acct, what, file, id, id_len);', '      { dh_write(mdh, mkey, (int16_t)mk, rec); mst_row(ck, "differs", acct, what, file, id, id_len); }'),
    ("check forgets the unwritable files", "c:masters.c", "    if (!mst_group_writable(path))\n      mst_row(ck, \"nonwritable\", acct, what, file, NULL, 0);", ""),
    ("the group write test looks at the owner bit", "c:masters.c", "if (!(sb.st_mode & S_IWGRP))", "if (!(sb.st_mode & S_IWUSR))"),
    ("syncbegin leaves the flags up", "c:masters.c", "    __sync_fetch_and_and(&sysseg->masters_flags, (u_int16_t)~(MST_F_STALE | MST_F_RESYNC));\n", ""),
    ("syncend forgets the orphans", "c:masters.c", "    long dropped = mst_drop_orphans(&cx);\n    int rc", "    long dropped = 0;\n    int rc"),
    ("an unregistered account is not refused by sync", "c:masters.c", "    if (a == NULL) {\n      mst_status(&out, MSA_NOACC);\n    } else {", "    if (a == NULL) {\n      mst_status(&out, MSA_OK);\n    } else {"),
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
    ("setup runs a shell command", "bp:masters_setup", "   close sv\n\n   ans = kernel", "   close sv\n   os.execute 'chmod 777 x'\n\n   ans = kernel"),
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
