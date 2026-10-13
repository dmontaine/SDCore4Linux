#!/usr/bin/env python3
"""test-gates-units.py - the per-account OS-access gates (S.63), as invariants read off the source.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-gates-units.py
  python3 .../test-gates-units.py --selftest

No sudo, no install, no sd.  Exit 0 every check passed, 1 a check failed, 2 it could not run.  Written 13 Oct 26.

***WHAT THIS IS, AND WHAT IT IS NOT.***  It reads the C and BASIC sources as text, with comments removed, so a gate that
survives only in a comment does not count.  ***IT DOES NOT RUN ANYTHING, SO IT CANNOT SAY THAT THE GATE REFUSES ANYBODY***:
that is sandbox-gates.py (ordinary sessions on a private SD, which refuse, run, and leave a sentinel as evidence) and
witness-accounts.sh (the owner's, with sudo, for CREATE.ACCOUNT and the Linux users and groups the sandbox cannot make).
What a text check is for: this code is reached from eleven places - op_sh.c, op_seqio.c, op_dio1.c, op_kernel.c, op_sdext.c,
cproc, login, createa, create_account, modifya, edit - and the invariants that make it a gate are mostly ORDERING (the
refusal before the stack is touched, the path test after fullpath() and before the transaction cache, the load at account
entry before the audit line, the upgrade before the register is chowned).  An edit that moves one still compiles.

***AND THE CHECKS ARE THEMSELVES CHECKED.***  --selftest breaks each invariant in the way an edit plausibly would and
requires some check to notice.  A mutant that nothing catches is reported as a FAILURE of the self-test.
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
WINMSG = "/home/don/Projects/SDCore4Windows/sdb_ai/sd64/sdsys/messages"

FILES = {
    "op_sh.c": os.path.join(GPLSRC, "op_sh.c"),
    "op_seqio.c": os.path.join(GPLSRC, "op_seqio.c"),
    "op_dio1.c": os.path.join(GPLSRC, "op_dio1.c"),
    "op_kernel.c": os.path.join(GPLSRC, "op_kernel.c"),
    "op_sdext.c": os.path.join(GPLSRC, "op_sdext.c"),
    "keys.h": os.path.join(GPLSRC, "keys.h"),
    "sysseg.h": os.path.join(GPLSRC, "sysseg.h"),
    "int$keys.h": os.path.join(GPL, "int$keys.h"),
    "syscom/keys.h": os.path.join(SDSYS, "syscom", "keys.h"),
    "cproc": os.path.join(GPL, "cproc"),
    "login": os.path.join(GPL, "login"),
    "createa": os.path.join(GPL, "createa"),
    "create_account": os.path.join(GPL, "create_account"),
    "modifya": os.path.join(GPL, "modifya"),
    "edit": os.path.join(GPL, "edit"),
    "acc_os_info": os.path.join(GPL, "acc_os_info"),
    "upgrade_gates": os.path.join(GPL, "upgrade_gates"),
    "installsdcore.sh": os.path.join(ROOT, "installsdcore.sh"),
}
C_FILES = ("op_sh.c", "op_seqio.c", "op_dio1.c", "op_kernel.c", "op_sdext.c", "keys.h", "sysseg.h")
SH_FILES = ("installsdcore.sh",)


def strip_c(src):
    """C with comments removed and every removed newline kept, so offsets still map to lines."""
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
    if name in SH_FILES:
        return strip_sh(src)
    return strip_bas(src)


def at(text, needle, start=0):
    """Offset of the first occurrence at or after start, or -1."""
    return text.find(needle, start)


def line_of(text, off):
    return text.count("\n", 0, off) + 1 if off >= 0 else None


def checks(srcs, messages_dir):
    """[(id, ok, detail)] - every invariant the gates rest on."""
    rows = []

    def ck(i, ok, detail=""):
        rows.append((i, bool(ok), detail))

    c = {name: code(name, text) for name, text in srcs.items()}

    # ---- K. the key numbers and the flag bits -------------------------------------------------------------------
    nums = {}
    for m in re.finditer(r"#define\s+(K_[A-Z0-9_]+)\s+(\d+)", c["keys.h"]):
        nums.setdefault(int(m.group(2)), []).append(m.group(1))
    for key, want in (("K_SH", 93), ("K_OS_EXEC", 94), ("K_PATH_OK", 95)):
        m = re.search(r"#define\s+%s\s+(\d+)" % key, c["keys.h"])
        ck("K1 %s is %d in gplsrc/keys.h" % (key, want), m and int(m.group(1)) == want, m.group(0) if m else "absent")
        bkey = key.replace("K_", "K$").replace("_", ".")
        m2 = re.search(r"\$define\s+%s\s+(\d+)" % re.escape(bkey), srcs["int$keys.h"])
        ck("K2 %s is %d in gpl.bp/int$keys.h, the same number" % (bkey, want), m2 and int(m2.group(1)) == want,
           m2.group(0) if m2 else "absent")
    dups = {n: k for n, k in nums.items() if len(k) > 1}
    ck("K3 no kernel key number in gplsrc/keys.h is used twice", not dups, repr(dups))
    ck("K4 USR_SH and USR_OS_EXEC are defined in sysseg.h and do not share a bit",
       re.search(r"#define\s+USR_SH\s+0x0100", c["sysseg.h"]) and re.search(r"#define\s+USR_OS_EXEC\s+0x0200", c["sysseg.h"]))
    ck("K5 ACC$SH is field 7 and ACC$OS.EXEC field 8 of the register",
       re.search(r"\$define ACC\$SH\s+7\b", srcs["syscom/keys.h"]) and re.search(r"\$define ACC\$OS\.EXEC\s+8\b", srcs["syscom/keys.h"]))

    # ---- C. the kernel -----------------------------------------------------------------------------------------
    sh = c["op_sh.c"]
    fn = at(sh, "Private void sh(bool capture) {")
    refuse = at(sh, "if (!os_permitted())", fn)
    getstr = at(sh, "k_get_string(descr)", fn)
    ck("C1 sh() refuses BEFORE it touches the stack (the refusal precedes k_get_string)",
       fn >= 0 and refuse > fn and getstr > refuse, "refusal at line %s, k_get_string at line %s" % (line_of(sh, refuse), line_of(sh, getstr)))
    ck("C2 the refusal is the Windows port's 10054", re.search(r"if \(!os_permitted\(\)\)\s*k_error\(sysmsg\(10054\)", sh))
    perm = sh[at(sh, "Private bool os_permitted(void) {"):][:200]
    ck("C3 os_permitted(): an $internal program first, then the account's own gate (never an unconditional TRUE)",
       "HDR_INTERNAL" in perm and "return os_gate_open();" in perm)
    gate = sh[at(sh, "bool os_gate_open(void) {"):]
    gate = gate[:gate.find("\n}") + 2]
    ck("C4 os_gate_open() is the administrator or USR_OS_EXEC, and does NOT look at HDR_INTERNAL",
       "USR_ADMIN" in gate and "USR_OS_EXEC" in gate and "HDR_INTERNAL" not in gate, gate.strip()[:120])
    pia = sh[at(sh, "Private bool path_inside_account"):]
    pia = pia[:at(pia, "bool os_path_ok_for_account")]
    ck("C5 containment resolves with realpath() on both sides and tests a path-component boundary",
       pia.count("realpath(") >= 2 and "strncmp(resolved, root, root_len)" in pia
       and "(resolved[root_len] == '\\0') || (resolved[root_len] == '/')" in pia)
    ck("C6 a '..' tail that cannot be resolved is refused, and so is an account rooted at /",
       'strcmp(p + 1, "..") == 0' in pia and "root_len == 1" in pia)
    ck("C7 os_path_ok_for_account: the gate opens everything, otherwise containment",
       re.search(r"if \(os_gate_open\(\)\)\s*return TRUE;\s*return path_inside_account\(name\);", sh))
    ck("C8 os_path_open_ok: an $internal program is trusted, anyone else is asked",
       re.search(r"bool os_path_open_ok\(const char \*name\) \{\s*if \(process\.program\.flags & HDR_INTERNAL\)\s*return TRUE;\s*"
                 r"return os_path_ok_for_account\(name\);", sh))

    sq = c["op_seqio.c"]
    fnq = at(sq, "Private void openseq(bool map_name) {")
    nam = at(sq, "process.status = ER_NAM;", at(sq, "filename_descr = e_stack - 2;", fnq))      # the OPENSEQP branch
    hook = at(sq, "if (!os_path_open_ok(file_name)) {", fnq)
    port = at(sq, "if (is_port(file_name))", fnq)
    ck("C9 OPENSEQ by pathname is asked AFTER the name is validated and BEFORE the port test and the open",
       nam > 0 and hook > nam and port > hook, "ER_NAM %s, hook %s, is_port %s" % (line_of(sq, nam), line_of(sq, hook), line_of(sq, port)))
    ck("C10 and the refusal is ER_PERM", re.search(r"if \(!os_path_open_ok\(file_name\)\) \{\s*process\.status = ER_PERM;", sq))

    d1 = c["op_dio1.c"]
    fnd = at(d1, "Private void open_file(bool map_name)")
    fp = at(d1, "fullpath(pathname, mapped_name);", fnd)
    hk = at(d1, "if (!map_name && !os_path_open_ok(pathname)) {", fnd)
    txn = at(d1, "txn_open(pathname)", fnd)
    ck("C11 OPENPATH is asked AFTER fullpath() and BEFORE the transaction cache, and only when no VOC mapped the name",
       fp > 0 and hk > fp and txn > hk, "fullpath %s, hook %s, txn_open %s" % (line_of(d1, fp), line_of(d1, hk), line_of(d1, txn)))
    ck("C12 and the refusal is ER_PERM", re.search(r"if \(!map_name && !os_path_open_ok\(pathname\)\) \{\s*process\.status = ER_PERM;", d1))

    kn = c["op_kernel.c"]
    for case, flag in (("K_SH", "USR_SH"), ("K_OS_EXEC", "USR_OS_EXEC")):
        s0 = at(kn, "case %s:" % case)
        blk = kn[s0:at(kn, "case K_", s0 + 8)]               # this case's own block, not the next one's
        ck("C13 kernel(%s) changes the flag only for an $internal caller, and reports it" % case,
           "HDR_INTERNAL" in blk and ("|= %s" % flag) in blk and ("&= ~%s" % flag) in blk and "result.data.value" in blk)
    kp = kn[at(kn, "case K_PATH_OK:"):][:420]
    ck("C14 kernel(K_PATH_OK) answers os_path_ok_for_account (the account's question, not the caller's)",
       "os_path_ok_for_account(path_ok_name)" in kp and "os_path_open_ok" not in kp)

    sx = c["op_sdext.c"]
    py = sx[at(sx, "case SD_PyInit:"):][:900]
    g = at(py, "os_gate_open()")
    run = at(py, "sdext_py(key")
    ck("C15 the Python gate asks the ACCOUNT (os_gate_open) and comes before sdext_py()", 0 < g < run, "gate %s, run %s" % (g, run))
    cond = py[:g]
    ck("C16 it gates starting the interpreter and running code, and not 'is Python running?'",
       "SD_PyInit" in cond[cond.find("if ("):] and "SD_PyRunStr" in cond and "SD_PyRunFile" in cond and "SD_IsPyInit" not in cond[cond.find("if ("):])

    # ---- B. BASIC ---------------------------------------------------------------------------------------------
    cp = c["cproc"]
    ld = at(cp, "void kernel(K$SH,")
    aud = at(cp, "void kernel(K$AUDIT, 'logto account='")
    ck("B1 CPROC's LOGTO loads K$SH and K$OS.EXEC from the register record BEFORE the audit line",
       0 < ld < aud and "upcase(trim(acc.record<ACC$SH>)) = 'YES'" in cp and "upcase(trim(acc.record<ACC$OS.EXEC>)) = 'YES'" in cp,
       "load %s, audit %s" % (line_of(cp, ld), line_of(cp, aud)))
    oc = at(cp, "os.command.text = trimf(voc.rec<3>")
    gate_ = at(cp, "if not(kernel(K$ADMINISTRATOR, -1)) and not(kernel(K$SH, -1)) then", oc)
    meta = at(cp, "if not(valid_shell_cmd(os.command.text)) then", oc)
    osx = at(cp, "os.execute os.command.text", oc)
    ck("B2 the SH verb refuses (10053) BEFORE the metacharacter test and BEFORE it runs the command",
       0 < oc < gate_ < meta < osx and "sysmsg(10053, @logname)" in cp[gate_:meta],
       "gate %s, filter %s, run %s" % (line_of(cp, gate_), line_of(cp, meta), line_of(cp, osx)))

    lg = c["login"]
    ll = at(lg, "void kernel(K$SH,")
    pth = at(lg, "account.path = ospath(\"\", OS$CWD)")
    ck("B3 LOGIN loads both grants at sign-on, from the 'YES' in fields 7 and 8, before @PATH is set",
       0 < ll < pth and "upcase(trim(acc.rec<ACC$SH>)) = 'YES'" in lg and "upcase(trim(acc.rec<ACC$OS.EXEC>)) = 'YES'" in lg)

    ca = c["create_account"]
    ck("B4 a new account starts with NO ssh and NO API: a route is on only if the setting is exactly 1",
       "access.ssh = (settings<CA$ROUTE.SSH> = 1)" in ca and "access.api = (settings<CA$ROUTE.API> = 1)" in ca
       and "# '0'" not in ca[ca.find("access.given"):ca.find("access.given") + 900])
    ck("B5 SH and OS.EXECUTE start off too: a switch is on only if its setting is exactly 1",
       "os.sh.want = (settings<CA$OS.SH> = 1)" in ca and "os.exec.want = (settings<CA$OS.EXECUTE> = 1)" in ca)
    att = at(ca, "if attach then")
    ck("B6 ATTACH (the installing user) turns all four on, inside the install-only branch",
       att > 0 and all(x in ca[att:att + 260] for x in ("access.ssh = @true", "access.api = @true", "os.sh.want = @true", "os.exec.want = @true"))
       and at(ca, "err = 2018:@vm:'ATTACH'") < att)
    ck("B7 a GROUP and an OTHER account given SH or OS are refused with 10105",
       ca.count("os.sh.want or os.exec.want") >= 2 and ca.count("err = 10105") >= 2)
    wr = at(ca, "write acc.rec to acc.f, acc.name")
    ck("B8 the register record gets ACC$SH and ACC$OS.EXEC as yes/no for a USER account, before it is written",
       0 < at(ca, "acc.rec<ACC$SH> = if os.sh.want then 'yes' else 'no'") < wr
       and 0 < at(ca, "acc.rec<ACC$OS.EXEC> = if os.exec.want then 'yes' else 'no'") < wr)

    cr = c["createa"]
    ck("B9 CREATE.ACCOUNT accepts SH-ON and OS-ON, each setting only its own field",
       re.search(r"upcase\(token\) = 'SH-ON'\s*settings<CA\$OS\.SH> = 1", cr) and re.search(r"upcase\(token\) = 'OS-ON'\s*settings<CA\$OS\.EXECUTE> = 1", cr))
    ck("B10 its usage says what the default is and names the words",
       "sh-on" in srcs["createa"] and "no ssh, no API, no shell" in srcs["createa"])

    md = c["modifya"]
    for word, field, want in (("SH-ON", "ACC$SH", "@true"), ("SH-OFF", "ACC$SH", "@false"), ("OS-ON", "ACC$OS.EXEC", "@true"),
                              ("OS-OFF", "ACC$OS.EXEC", "@false")):
        ck("B11 MODIFY.ACCOUNT %s sets os.field = %s, os.want = %s and calls os.set" % (word, field, want),
           re.search(r"case action = '%s'\s*os\.field = %s ; os\.want = %s\s*gosub os\.set" % (re.escape(word), re.escape(field), want), md))
    osset = md[at(md, "\nos.set:"):]
    rd = at(osset, "readu acc.new from acc.f, acc.name")
    wt = at(osset, "write acc.new to acc.f, acc.name")
    ck("B12 os.set writes the register under a lock (readu before write) and reports a failed write",
       0 < rd < wt and "sysmsg(10114, acc.name)" in osset)
    ck("B13 os.set reports both fields afterwards (10102), refuses a non-sdu_ account (10105) and says 'no change' (10080)",
       "sysmsg(10102, acc.name, os.sh.now, os.ex.now)" in osset and "sysmsg(10105, acc.name)" in osset and "sysmsg(10080, acc.name)" in osset)

    ed = c["edit"]
    cpm = ed[at(ed, "check.permitted:"):][:1400]
    tty = at(cpm, "kernel(K$TTY, 0) = ''")
    ox = at(cpm, "kernel(K$OS.EXEC, -1)")
    ck("B14 nano and micro (EDIT) need OS.EXECUTE: the grant is tested after the terminal test, and a plain 'permitted = @true' "
       "no longer ends check.permitted", 0 < tty < ox and not re.search(r"@system|\n\s*permitted = @true\s*\nreturn", cpm.split("kernel(K$OS.EXEC, -1)")[0][-60:]),
       "tty %s, grant %s" % (tty, ox))

    ai = c["acc_os_info"]
    ck("B15 the account manifest writes os.sh and os.execute (what RESTORE.ACCOUNT reads back)",
       "'os.sh: '" in ai and "'os.execute: '" in ai and "ACC$SH" in ai and "ACC$OS.EXEC" in ai)

    ug = c["upgrade_gates"]
    mk = at(ug, "if ospath(marker, OS$EXISTS) then")
    wk = at(ug, "select acc.f to 12")
    wm = at(ug, "openseq marker to marker.f")
    fl = at(ug, "if failed # 0 then")
    ck("B16 upgrade_gates: the marker is tested BEFORE the walk and written AFTER it, and only when nothing failed",
       0 < mk < wk < fl < wm, "marker test %s, walk %s, failed test %s, marker write %s" % (mk, wk, fl, wm))
    ck("B17 it touches USER accounts only (an sdu_ group) and sets both fields to yes",
       "rec<ACC$GROUP>[1, 4] = 'sdu_'" in ug and "rec<ACC$SH> = 'yes'" in ug and "rec<ACC$OS.EXEC> = 'yes'" in ug)

    # ---- I. the installer ---------------------------------------------------------------------------------------
    ins = c["installsdcore.sh"]
    blk0 = at(ins, 'if [ "$accounts_kept" = yes ]; then')
    run_ = at(ins, "-internal RUN gpl.bp upgrade_gates", blk0)
    nc = at(ins, "-internal RUN gpl.bp upgrade_nocase", blk0)
    chown = at(ins, 'sudo chown -R sdsys:sdusers "$sdsysdir/accounts"')
    recompile = at(ins, "Compiling CPROC without IS_INSTALL defined.")
    ck("I1 the installer runs upgrade_gates as root, inside the kept-accounts block, after the VOC/case walks and BEFORE the register "
       "is chowned to sdsys and CPROC is recompiled without IS_INSTALL",
       0 < blk0 < nc < run_ < chown < recompile and "sudo" in ins[ins.rfind("\n", 0, run_):run_],
       "block %s, nocase %s, gates %s, chown %s, cproc %s" % (blk0, nc, run_, chown, recompile))
    tail = ins[run_:run_ + 900]
    ck("I2 a run that did not print COMPLETE is reported and the install goes on", "grep -qx" in tail and "COMPLETE" in tail
       and "WARNING" in tail and "exit 1" not in tail.split("fi")[0])

    # ---- M. the messages ----------------------------------------------------------------------------------------
    want = {"10053": ("%1 is not permitted to use the operating system shell", True),
            "10054": ("%s is not permitted to use OS.EXECUTE", True),
            "10080": ("%1 already had that access; nothing changed", True),
            "10102": ("Account %1 has SH %2, OS.EXECUTE %3", False),
            "10105": ("%1 is a group account and has no Linux user, so it has no shell to permit", False),
            "11167": ("%1 has no OS access", False)}
    for num, (text, same_as_windows) in want.items():
        path = os.path.join(messages_dir, num)
        try:
            with open(path) as f:
                body = f.read().rstrip("\n")
        except OSError as exc:
            ck("M1 message %s exists" % num, False, str(exc))
            continue
        ck("M1 message %s exists and starts as the code expects" % num, body.startswith(text), repr(body[:80]))
        if same_as_windows and os.path.isdir(WINMSG) and os.path.isfile(os.path.join(WINMSG, num)):
            with open(os.path.join(WINMSG, num)) as f:
                ck("M2 message %s is word for word the Windows port's" % num, f.read().rstrip("\n") == body, repr(body[:60]))
    return rows


# --------------------------------------------------------------- self-test
def sub(name, old, new):
    def f(srcs):
        s = dict(srcs)
        if old not in s[name]:
            return s
        s[name] = s[name].replace(old, new, 1)
        return s
    return f


def swap(name, a, b):
    """Swap two exclusive substrings of the file (order mutants)."""
    def f(srcs):
        s = dict(srcs)
        t = s[name]
        if a not in t or b not in t:
            return s
        t = t.replace(a, "\0A\0", 1).replace(b, a, 1).replace("\0A\0", b, 1)
        s[name] = t
        return s
    return f


def _move_seq_hook(srcs):
    """Take the OPENSEQ pathname test out from before the port test and put it after fullpath() in the other branch,
    so it is still there, still compiles, and sits where the port test has already run."""
    s = dict(srcs)
    t = s["op_seqio.c"]
    hook = ("    if (!os_path_open_ok(file_name)) {\n      process.status = ER_PERM;\n      goto exit_op_openseq;\n    }\n")
    anchor = "      fullpath(fullpathname, file_name);\n"
    if hook not in t or anchor not in t:
        return s
    t = t.replace(hook, "", 1)
    t = t.replace(anchor, anchor + hook.replace("    if", "      if", 1), 1)
    s["op_seqio.c"] = t
    return s


MUTANTS = [
    ("sh(): the refusal is removed", sub("op_sh.c", "if (!os_permitted())\n    k_error(sysmsg(10054), process.username);", "if (0)\n    k_error(sysmsg(10054), process.username);")),
    ("os_permitted() always true", sub("op_sh.c", "  return os_gate_open();\n}\n\nPrivate bool path_inside", "  return TRUE;\n}\n\nPrivate bool path_inside")),
    ("os_gate_open() asks the program instead of the account", sub("op_sh.c", "return (my_uptr->flags & (USR_ADMIN | USR_OS_EXEC)) != 0;", "return (process.program.flags & HDR_INTERNAL) != 0;")),
    ("containment compares prefixes without a component boundary", sub("op_sh.c", "(resolved[root_len] == '\\0') || (resolved[root_len] == '/')", "1")),
    ("containment no longer resolves symbolic links", sub("op_sh.c", "if (realpath(work, resolved) != NULL)", "if (strcpy(resolved, work))")),
    ("an unresolvable .. tail is allowed", sub("op_sh.c", "if ((strcmp(p + 1, \"..\") == 0) || (strcmp(p + 1, \".\") == 0))\n      return FALSE;", "")),
    ("an account rooted at / is allowed", sub("op_sh.c", "if (root_len == 1)", "if (root_len == 99999)")),
    ("OPENSEQ hook moved below the port test", lambda srcs: _move_seq_hook(srcs)),
    ("OPENPATH hook removed", sub("op_dio1.c", "if (!map_name && !os_path_open_ok(pathname)) {", "if (0) {")),
    ("OPENPATH hook asks before the name is resolved", swap("op_dio1.c", "  fullpath(pathname, mapped_name);\n", "  if (!map_name && !os_path_open_ok(pathname)) {\n    process.status = ER_PERM;\n    goto exit_op_open;\n  }\n")),
    ("kernel(K_SH) lets any caller set the flag", sub("op_kernel.c", "case K_SH:\n      GetInt(descr);\n      n = descr->data.value;\n      if (n >= 0) {\n        if (process.program.flags & HDR_INTERNAL) {", "case K_SH:\n      GetInt(descr);\n      n = descr->data.value;\n      if (n >= 0) {\n        if (1) {")),
    ("kernel(K_PATH_OK) answers the caller's question", sub("op_kernel.c", "os_path_ok_for_account(path_ok_name)", "os_path_open_ok(path_ok_name)")),
    ("the Python gate asks the program", sub("op_sdext.c", "!os_gate_open()) {", "!(process.program.flags & HDR_INTERNAL)) {")),
    ("the Python gate is gone", sub("op_sdext.c", "!os_gate_open()) {", "0) {")),
    ("the Python gate also blocks 'is Python running?'", sub("op_sdext.c", "((key == SD_PyInit) || (key == SD_PyRunStr) || (key == SD_PyRunFile))", "((key == SD_PyInit) || (key == SD_PyRunStr) || (key == SD_PyRunFile) || (key == SD_IsPyInit))")),
    ("key K_SH renumbered in the kernel only", sub("keys.h", "#define K_SH                 93", "#define K_SH                 92")),
    ("key K_OS_EXEC clashes with K_SH", sub("keys.h", "#define K_OS_EXEC            94", "#define K_OS_EXEC            93")),
    ("USR_SH and USR_OS_EXEC share a bit", sub("sysseg.h", "USR_OS_EXEC     0x0200", "USR_OS_EXEC     0x0100")),
    ("LOGTO no longer loads the grants", sub("cproc", "   void kernel(K$SH,      upcase(trim(acc.record<ACC$SH>)) = 'YES')\n", "")),
    ("LOGTO loads them after the audit line", swap("cproc", "   void kernel(K$SH,      upcase(trim(acc.record<ACC$SH>)) = 'YES')\n   void kernel(K$OS.EXEC, upcase(trim(acc.record<ACC$OS.EXEC>)) = 'YES')\n\n", "   void kernel(K$AUDIT, 'logto account=' : new.account)")),
    ("the SH verb gate is removed", sub("cproc", "   if not(kernel(K$ADMINISTRATOR, -1)) and not(kernel(K$SH, -1)) then\n      display sysmsg(10053, @logname)", "   if @false then\n      display sysmsg(10053, @logname)")),
    ("the SH verb gate comes after the command has run", swap("cproc", "   if not(kernel(K$ADMINISTRATOR, -1)) and not(kernel(K$SH, -1)) then\n      display sysmsg(10053, @logname) ;* %1 is not permitted to use the operating system shell\n      return\n   end\n", "   os.execute os.command.text\n")),
    ("LOGIN grants everyone both", sub("login", "void kernel(K$SH,      upcase(trim(acc.rec<ACC$SH>)) = 'YES')", "void kernel(K$SH,      1)")),
    ("a new account is on both routes by default again", sub("create_account", "access.ssh = (settings<CA$ROUTE.SSH> = 1)", "access.ssh = settings<CA$ROUTE.SSH> # '0'")),
    ("a new account gets the shell by default", sub("create_account", "os.sh.want = (settings<CA$OS.SH> = 1)", "os.sh.want = (settings<CA$OS.SH> # '0')")),
    ("ATTACH no longer turns the four on", sub("create_account", "         os.exec.want = @true\n      end\n   end", "      end\n   end")),
    ("a GROUP account may be given a shell", sub("create_account", "     if os.sh.want or os.exec.want then\n       @system.return.code = -ER$ARGS\n       err = 10105:@vm:acc.name ;* %1 is a group account", "     if @false then\n       @system.return.code = -ER$ARGS\n       err = 10105:@vm:acc.name ;* %1 is a group account")),
    ("the register is written without the gate fields", sub("create_account", "     acc.rec<ACC$SH> = if os.sh.want then 'yes' else 'no'\n", "")),
    ("CREATE.ACCOUNT OS-ON sets the wrong field", sub("createa", "settings<CA$OS.EXECUTE> = 1", "settings<CA$OS.SH> = 1")),
    ("MODIFY.ACCOUNT SH-OFF turns the shell on", sub("modifya", "os.field = ACC$SH ; os.want = @false", "os.field = ACC$SH ; os.want = @true")),
    ("MODIFY.ACCOUNT OS-ON changes the shell field", sub("modifya", "os.field = ACC$OS.EXEC ; os.want = @true", "os.field = ACC$SH ; os.want = @true")),
    ("os.set writes without the lock", sub("modifya", "   readu acc.new from acc.f, acc.name else acc.new = acc.rec\n   if os.want", "   acc.new = acc.rec\n   if os.want")),
    ("nano and micro need no grant", sub("edit", "   if kernel(K$OS.EXEC, -1) then\n      permitted = @true\n      return\n   end\n", "   permitted = @true\n   return\n")),
    ("the manifest leaves out os.sh", sub("acc_os_info", "info<-1> = 'os.sh: '", "info<-1> = 'zz.sh: '")),
    ("upgrade_gates tests its marker after the walk", swap("upgrade_gates", "   if ospath(marker, OS$EXISTS) then", "   select acc.f to 12")),
    ("upgrade_gates writes the marker even when a record failed", sub("upgrade_gates", "   if failed # 0 then", "   if @false then")),
    ("upgrade_gates touches group accounts", sub("upgrade_gates", "if rec<ACC$GROUP>[1, 4] = 'sdu_' then", "if @true then")),
    ("the installer stops running upgrade_gates", sub("installsdcore.sh", "-internal RUN gpl.bp upgrade_gates", "-internal RUN gpl.bp upgrade_nothing")),
    ("the installer runs upgrade_gates after the register is chowned", swap("installsdcore.sh", "    og_out=$(sudo \"$sdsysdir/bin/sd\" -internal RUN gpl.bp upgrade_gates 2>&1) || og_rc=$?\n", "sudo chown -R sdsys:sdusers \"$sdsysdir/accounts\"\n")),
]


def selftest(srcs, messages_dir):
    print("--- self-test: each mutation must be CAUGHT by at least one check ---")
    base_bad = [n for n, ok, _ in checks(srcs, messages_dir) if not ok]
    if base_bad:
        print("REFUSING - the unmutated source already fails: %s" % ", ".join(base_bad), file=sys.stderr)
        return 2
    holes = 0
    for name, fn in MUTANTS:
        mutated = fn(srcs)
        if mutated == srcs:
            print("  [FAIL] %s: the mutation did not change the file (this test no longer understands the source)" % name)
            holes += 1
            continue
        caught = [n for n, ok, _ in checks(mutated, messages_dir) if not ok]
        if caught:
            print("  [pass] %s: caught by %s" % (name, ", ".join(caught[:4])))
        else:
            print("  [FAIL] %s: NOT CAUGHT by any check" % name)
            holes += 1
    print("\n%d of %d mutants caught" % (len(MUTANTS) - holes, len(MUTANTS)))
    return 1 if holes else 0


def main(argv):
    srcs = {}
    for name, path in FILES.items():
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                srcs[name] = f.read()
        except OSError as exc:
            print("CANNOT RUN - %s: %s" % (path, exc), file=sys.stderr)
            return 2
    messages_dir = os.path.join(SDSYS, "messages")
    print("reading %d sources under %s" % (len(srcs), SD64))
    if "--selftest" in argv:
        return selftest(srcs, messages_dir)
    rows = checks(srcs, messages_dir)
    if not rows:
        print("REFUSING - no checks ran", file=sys.stderr)
        return 2
    failed = 0
    for name, ok, detail in rows:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, ("   <- " + detail) if (detail and not ok) else ""))
        failed += 0 if ok else 1
    print("\n%d passed, %d failed" % (len(rows) - failed, failed))
    print("NOT MEASURED HERE: whether any gate refuses anybody.  That is sandbox-gates.py (ordinary sessions on a private SD) and "
          "witness-accounts.sh (CREATE.ACCOUNT, which makes Linux users).")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
