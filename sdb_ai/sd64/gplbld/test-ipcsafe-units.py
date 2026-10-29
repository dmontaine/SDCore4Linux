#!/usr/bin/env python3
"""test-ipcsafe-units.py - the readers and the writers of the $IPC records S<n>, F<n> and H<n> show another session's text by ONE rule
(S.88 phase 2, the approved item "escape in the reader and the writers"; 28 Oct 26).

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-ipcsafe-units.py
  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-ipcsafe-units.py --selftest

No sudo, no install, no sd.  Exit 0 all checks passed, 1 a check failed, 2 it could not run.

THE DEFECT.  $IPC is sdsys:sdusers 775, so every SD user can write a record into it.  PSTAT prints the record S<n> (the process-status dump),
PROFILER DISPLAY the record F<n> (the profile table) and HSM USER n the record H<n> (the Hot Spot Monitor's data), each RAW: a record planted
there (S<n> and H<n> while the command polls for the answer, F<n> at any time) put its bytes - ESC ] 0 ; ... BEL, ESC [ 2 J, CSI as byte 155 -
on the terminal of whoever ran the command, the administrator included.  The kernel's own writers were not all safe either: prof_dump()
wrote the program names raw and prof_event() kept DEL and the C1 controls 128-159 in the qualifiers; hsm_dump() wrote the program names raw.

THE CHANGE.  The rule stays op_lock.c's show_unsafe_byte() (0-31, 127, 128-159 and 248-255 as '?'; test-lockids-units.py L1 evaluates it for
all 256 bytes).  The writers use it: prof_event() for the qualifier, prof_dump() and hsm_dump() through show_ts_safe() for every text.  BASIC
reaches it through kernel(K$SHOW.SAFE, text) (K_SHOW_SAFE 151, op_kernel.c), which walks the string chunk by chunk through show_ts_safe(), so
there is no second copy of the rule.  pstat, profiler and hsm print every text of the record they read through it; their comparisons keep the
text as read.  $IPC's mode is NOT changed (the owner declined that).  A reader that believes S<n> only when it is owned by user n's uid was
NOT built: $IPC is a hashed file and its records have no owner.

***WHAT THIS IS AND IS NOT.***  Text only: it reads keys.h, int$keys.h, op_kernel.c, profiler.c, object.c and the three programs.  It cannot
say what a terminal receives: that is sandbox-lockids.py rows PL-ctl0 to PL8 (records planted in $IPC, PSTAT USER n, HSM USER n and PROFILER
DISPLAY USER 9999 captured as bytes), WRITTEN AND NOT RUN.  --selftest mutates the sources (every kernel(K$SHOW.SAFE, ...) of the three programs unwrapped
one at a time, and the C writers put back the old way) and requires every mutant to be caught.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.abspath(os.path.join(HERE, os.pardir))
PATHS = {
    "keys_h": os.path.join(SD64, "gplsrc", "keys.h"),
    "intkeys": os.path.join(SD64, "sdsys", "gpl.bp", "int$keys.h"),
    "op_kernel": os.path.join(SD64, "gplsrc", "op_kernel.c"),
    "profiler_c": os.path.join(SD64, "gplsrc", "profiler.c"),
    "object_c": os.path.join(SD64, "gplsrc", "object.c"),
    "pstat": os.path.join(SD64, "sdsys", "gpl.bp", "pstat"),
    "profiler": os.path.join(SD64, "sdsys", "gpl.bp", "profiler"),
    "hsm": os.path.join(SD64, "sdsys", "gpl.bp", "hsm"),
}
WRAP = "kernel(K$SHOW.SAFE, "
# The texts each program reads from $IPC and prints.  An occurrence AFTER the print / display keyword of a line must sit directly inside
# kernel(K$SHOW.SAFE, ...); "len(" before it (a width) and " / 1000" or " + 0" after it (a number) are not printing the text.
TAINT = {
    "pstat": [r"\brec<[^>]*>", r"\bprog\.list<prg,\s*1>", r"\bln\b"],
    "profiler": [r"\bsel\.(?:type|qual|prog)\b", r"\bkeys<i>", r"\bs<1,\s*4>", r"\be<[^>]*>"],
    "hsm": [r"\bss<[^>]*>", r"\bs<i>"],
}
# At least this many wrapped texts, and printed texts seen, in each program (the null case: a reader that finds nothing must not pass).
MIN_WRAPS = {"pstat": 12, "profiler": 8, "hsm": 2}
MIN_SEEN = {"pstat": 12, "profiler": 7, "hsm": 7}
RULE_LITERALS = re.compile(r"(<\s*32\b|\b127\b|\b159\b|\b248\b|>=\s*248|0x7[fF]|0x9[fF]|0xf8|0xF8)")


def strip_c(text):
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


def squash(s):
    return re.sub(r"\s+", " ", s)


def func_body(code, header_re):
    m = re.search(header_re + r"[^{]*\{\n(.*?)^\}\n", code, re.S | re.M)
    return m.group(1) if m else None


def case_body(code, label):
    """The text of one case of op_kernel()'s switch: from 'case LABEL: {' to the matching '} break;'."""
    m = re.search(r"case " + label + r": \{\n(.*?)\n    \} break;", code, re.S)
    return m.group(1) if m else None


def bas_lines(text):
    out = []
    for ln in text.split("\n"):
        s = re.sub(r";\*.*$", "", ln).rstrip()
        if s.strip() and not s.lstrip().startswith("*"):
            out.append(s)
    return out


def raw_prints(name, text):
    """Each occurrence of a tainted text that a print / display / crt of NAME shows without the rule: (line, the text)."""
    bad = []
    seen = 0
    for ln in bas_lines(text):
        m = re.search(r"\b(print|display|crt)\b", ln)
        if not m:
            continue
        tail = ln[m.start():]
        for pat in TAINT[name]:
            for t in re.finditer(pat, tail):
                seen += 1
                before = tail[:t.start()]
                after = tail[t.end():]
                if before.endswith(WRAP) or before.endswith("len("):
                    continue
                if re.match(r"\s*(/\s*1000|\+\s*0)\b", after):
                    continue
                bad.append((ln.strip(), t.group(0)))
    return bad, seen


def checks(files):
    out = []

    def ck(name, ok, detail=""):
        out.append((name, bool(ok), detail))

    # --- K: the key -------------------------------------------------------------------------------------------------------------
    kh = strip_c(files["keys_h"])
    kdef = re.findall(r"^#define K_SHOW_SAFE\s+(\d+)\s*$", kh, re.M)
    idef = re.findall(r"^\s*\$define K\$SHOW\.SAFE\s+(\d+)\b", files["intkeys"], re.M)
    ck("K1 keys.h defines K_SHOW_SAFE once and int$keys.h K$SHOW.SAFE once, with the same number",
       len(kdef) == 1 and len(idef) == 1 and kdef[0] == idef[0], "keys.h %r int$keys.h %r" % (kdef, idef))
    num = kdef[0] if kdef else "?"
    others = [l for l in re.findall(r"^#define (K_[A-Z_0-9]+)\s+(\d+)\s*$", kh, re.M) if l[1] == num and l[0] != "K_SHOW_SAFE"]
    iothers = [l for l in re.findall(r"^\s*\$define (K\$[A-Z.0-9]+)\s+(\d+)\b", files["intkeys"], re.M) if l[1] == num and l[0] != "K$SHOW.SAFE"]
    ck("K2 no other kernel key has its number (%s) in either header" % num, not others and not iothers, repr(others + iothers))
    ok_code = strip_c(files["op_kernel"])
    cb = case_body(ok_code, "K_SHOW_SAFE")
    cbs = squash(cb or "")
    ck("K3 op_kernel() answers K_SHOW_SAFE: the argument as a string, a new string, every chunk through show_ts_safe(), ts_terminate()",
       cb is not None and ordered(cbs, "k_get_string(descr);", "InitDescr(&result, STRING);", "ts_init(&(result.data.str.saddr),",
                                  "for (safe_chunk = descr->data.str.saddr; safe_chunk != NULL; safe_chunk = safe_chunk->next)",
                                  "show_ts_safe(safe_chunk->data, (int)(safe_chunk->bytes));", "ts_terminate();"), cbs[:300])
    ck("K4 ... and has no rule of its own: no ts_copy / ts_copy_byte / memcpy, no comparison with the rule's bounds (32, 127, 159, 248)",
       cb is not None and not re.search(r"\bts_copy(_byte)?\(|\bmemcpy\(", cbs) and not RULE_LITERALS.search(cbs), cbs[:300])

    # --- P: profiler.c --------------------------------------------------------------------------------------------------------
    pc = strip_c(files["profiler_c"])
    pe = func_body(pc, r"^void prof_event\(int16_t bit, const char\* qual, int qlen\) ")
    peb = squash(pe or "")
    ck("P1 prof_event() keeps a qualifier byte or '?' by show_unsafe_byte() (it took 0-31 and 248-255 only)",
       pe is not None and "q[i] = show_unsafe_byte((u_char)(qual[i])) ? '?' : qual[i];" in peb and not RULE_LITERALS.search(peb), peb[:200])
    pd = func_body(pc, r"^void prof_dump\(DESCRIPTOR\* result\) ")
    pdb = squash(pd or "")
    ck("P2 prof_dump() writes the qualifier and the program name through show_ts_safe(), between value marks, after the event name",
       pd is not None and ordered(pdb, "ts_copy_byte(FIELD_MARK);", 'ts_printf("%s%c", prof_names[t], VALUE_MARK);', "show_ts_safe(e->qual, -1);",
                                  "ts_copy_byte(VALUE_MARK);", "show_ts_safe(e->prog, -1);", 'ts_printf("%c%d%c%d", VALUE_MARK, (int)e->line, VALUE_MARK, (int)e->count);'),
       pdb[:300])
    printfs = re.findall(r"ts_printf\((.*?)\);", pdb)
    ck("P3 no ts_printf() of prof_dump() formats e->qual or e->prog, and its only %s is the event's name",
       pd is not None and not any("e->qual" in p or "e->prog" in p for p in printfs)
       and sum(p.count("%s") for p in printfs) == 1 and any("prof_names[t]" in p for p in printfs), repr(printfs))

    # --- H: object.c hsm_dump() -----------------------------------------------------------------------------------------------
    oc = strip_c(files["object_c"])
    hd = func_body(oc, r"^STRING_CHUNK\* hsm_dump\(\) ")
    hdb = squash(hd or "")
    hp = re.findall(r"ts_printf\((.*?)\);", hdb)
    ck("H1 hsm_dump() writes each program name through show_ts_safe() before its numbers, and formats no text (no %s, no p->name)",
       hd is not None and ordered(hdb, "for (p = hsm_head; p != NULL; p = p->next)", "show_ts_safe(p->name, -1);", 'ts_printf("\\xfd%d')
       and len(hp) == 1 and "%s" not in hp[0] and "p->name" not in hp[0], repr(hp))

    # --- R: one rule ----------------------------------------------------------------------------------------------------------
    copies = [n for n in ("profiler_c", "object_c", "op_kernel") if re.search(r"^(bool|char\s*\*|void|Private \w+)\s*\w*(unsafe|safe_text|ts_safe)\w*\s*\(", strip_c(files[n]), re.M)]
    ck("R1 none of profiler.c, object.c and op_kernel.c defines a function of its own for the rule (op_lock.c's is the one)", not copies, repr(copies))
    hand = [n for n in ("pstat", "profiler", "hsm") if re.search(r"char\(\s*27\s*\)|\bseq\(|\bconvert\b|\bchange\(", "\n".join(bas_lines(files[n])), re.I)]
    ck("R2 none of the three programs makes text safe by hand (char(27), seq(), convert, change()): they ask the kernel", not hand, repr(hand))

    # --- B: the three readers -------------------------------------------------------------------------------------------------
    for i, name in enumerate(("pstat", "profiler", "hsm")):
        code = "\n".join(bas_lines(files[name]))
        nw = code.count(WRAP)
        bad, seen = raw_prints(name, files[name])
        ck("B%da %s: at least %d texts go through kernel(K$SHOW.SAFE, ...) (%d) and the reader saw at least %d printed texts (%d; the null case)"
           % (i + 1, name, MIN_WRAPS[name], nw, MIN_SEEN[name], seen), nw >= MIN_WRAPS[name] and seen >= MIN_SEEN[name], "")
        ck("B%db %s: every text of the $IPC record that a print / display shows sits directly inside kernel(K$SHOW.SAFE, ...)" % (i + 1, name), not bad, repr(bad[:4]))
        ck("B%dc %s: includes int$keys.h (where K$SHOW.SAFE is defined)" % (i + 1, name), re.search(r"^\$include int\$keys\.h", files[name], re.M), "")
    pl = "\n".join(bas_lines(files["pstat"]))
    ck("B4 pstat: the lock holder's name is built through the rule before it is printed",
       re.search(r"holder = if holder # '' then \(' \(' : kernel\(K\$SHOW\.SAFE, holder\) : '\)'\) else ''", pl), "")
    ck("B5 pstat: the record is still DELETEd after it is read and the comparisons ($cproc, $vbsrvr) use the name as read",
       "delete ipc.f, 'S':user" in pl and "case prog.name= '$cproc'" in pl and "prog.name = prog.list<prg,1>" in pl, "")
    fl = "\n".join(bas_lines(files["profiler"]))
    ck("B6 profiler: a key is shown as (none) when empty, else through the rule, and the choice keeps the key as read (sel.qual = keys<answer>)",
       "if shown = '' then shown = '(none)' else shown = kernel(K$SHOW.SAFE, shown)" in fl and "if level = 2 then sel.qual = keys<answer>" in fl, "")
    return out


def ordered(text, *parts):
    pos = 0
    for p in parts:
        i = text.find(p, pos)
        if i < 0:
            return False
        pos = i + len(p)
    return True


def unwrap_all(text):
    """Every kernel(K$SHOW.SAFE, X) of TEXT unwrapped to X, one at a time: [(label, new text)]."""
    out = []
    start = 0
    while True:
        i = text.find(WRAP, start)
        if i < 0:
            return out
        j = i + len(WRAP)
        depth = 1
        k = j
        while k < len(text) and depth:
            if text[k] == "(":
                depth += 1
            elif text[k] == ")":
                depth -= 1
            k += 1
        arg = text[j:k - 1]
        line = text.count("\n", 0, i) + 1
        ls = text.rfind("\n", 0, i) + 1
        prefix = text[ls:i]
        if not prefix.lstrip().startswith("*") and ";*" not in prefix:     # a comment that names the key is not code
            out.append(("line %d: %s printed raw" % (line, arg), text[:i] + arg + text[k:]))
        start = k


def mutants(files):
    M = []
    for name in ("pstat", "profiler", "hsm"):
        for label, new in unwrap_all(files[name]):
            M.append(("%s %s" % (name, label), dict(files, **{name: new})))

    def cx(key, name, old, new):
        M.append((name, dict(files, **{key: files[key].replace(old, new, 1)})))

    cx("profiler_c", "prof_event back to the old rule (0-31 and 248-255 only)", "    q[i] = show_unsafe_byte((u_char)(qual[i])) ? '?' : qual[i];",
       "    q[i] = (((u_char)qual[i] < 32) || ((u_char)qual[i] >= 248)) ? '?' : qual[i];")
    cx("profiler_c", "prof_dump writes the qualifier raw", "    show_ts_safe(e->qual, -1);\n", "    ts_printf(\"%s\", e->qual);\n")
    cx("profiler_c", "prof_dump writes the program name raw", "    show_ts_safe(e->prog, -1);\n", "    ts_copy(e->prog, (int)strlen(e->prog));\n")
    cx("profiler_c", "prof_dump back to one ts_printf of every text",
       "    ts_printf(\"%s%c\", prof_names[t], VALUE_MARK);\n    show_ts_safe(e->qual, -1);\n    ts_copy_byte(VALUE_MARK);\n    show_ts_safe(e->prog, -1);\n    ts_printf(\"%c%d%c%d\", VALUE_MARK, (int)e->line, VALUE_MARK, (int)e->count);",
       "    ts_printf(\"%s%c%s%c%s%c%d%c%d\", prof_names[t], VALUE_MARK, e->qual, VALUE_MARK, e->prog, VALUE_MARK, (int)e->line, VALUE_MARK, (int)e->count);")
    cx("object_c", "hsm_dump writes the program name raw (the old way)",
       "    show_ts_safe(p->name, -1); /* 28 Oct 26 S.88 phase 2: the kernel's one rule; the name went out raw */\n    ts_printf(\"\\xfd%d",
       "    ts_printf(\"%s\\xfd%d")
    cx("object_c", "hsm_dump: the name formatted after the escaped copy too", "    ts_printf(\"\\xfd%d\\xfd%lld", "    ts_printf(\"%s\\xfd%d\\xfd%lld")
    cx("op_kernel", "K_SHOW_SAFE copies the text raw", "        show_ts_safe(safe_chunk->data, (int)(safe_chunk->bytes));", "        ts_copy(safe_chunk->data, (int)(safe_chunk->bytes));")
    cx("op_kernel", "K_SHOW_SAFE has a rule of its own", "        show_ts_safe(safe_chunk->data, (int)(safe_chunk->bytes));",
       "        { int k; for (k = 0; k < safe_chunk->bytes; k++) ts_copy_byte(((u_char)safe_chunk->data[k] < 32) ? '?' : safe_chunk->data[k]); }")
    cx("op_kernel", "the K_SHOW_SAFE case is gone", "    case K_SHOW_SAFE: {", "    case K_SHOW_SAFE_GONE: {")
    cx("intkeys", "int$keys.h gives K$SHOW.SAFE another number", "$define K$SHOW.SAFE       151", "$define K$SHOW.SAFE       152")
    cx("keys_h", "keys.h gives K_SHOW_SAFE the number of K_MASTERS", "#define K_SHOW_SAFE          151", "#define K_SHOW_SAFE          150")
    cx("pstat", "pstat prints @PSTAT raw through another variable", "kernel(K$SHOW.SAFE, rec<6>)", "rec<6>")
    cx("pstat", "pstat filters by hand instead of asking the kernel", "kernel(K$SHOW.SAFE, rec<5>)", "convert(char(27), '?', rec<5>)")
    cx("hsm", "hsm shows the name without the rule", "display kernel(K$SHOW.SAFE, ss<1, 1>)", "display ss<1, 1>")
    cx("profiler", "profiler shows the key raw again", ": '  ' : shown", ": '  ' : keys<i>")
    return M


def load():
    files = {}
    for k, p in PATHS.items():
        if not os.path.isfile(p):
            return None, p
        with open(p, encoding="latin-1") as f:
            files[k] = f.read()
    return files, None


def main():
    files, missing = load()
    if files is None:
        print("test-ipcsafe-units: CANNOT RUN - no file %s" % missing)
        return 2
    for k, p in PATHS.items():
        print("%-11s: %s" % (k, p))
    if "--selftest" in sys.argv:
        base = checks(files)
        if not all(ok for _, ok, _ in base):
            print("selftest: CANNOT RUN - the unmutated sources already fail:")
            for n, ok, d in base:
                if not ok:
                    print("  FAIL %s (%s)" % (n, d))
            return 2
        bad = 0
        ms = mutants(files)
        for name, mf in ms:
            if mf == files:
                print("  [NOT APPLIED] %s" % name)
                bad += 1
                continue
            caught = [n.split(" ", 1)[0] for n, ok, _ in checks(mf) if not ok]
            if caught:
                print("  [caught] %s  (by %s)" % (name, ", ".join(caught)))
            else:
                print("  [MISSED] %s" % name)
                bad += 1
        if len(ms) < 30:
            print("test-ipcsafe-units --selftest: only %d mutants - refusing to pass" % len(ms))
            return 1
        print("test-ipcsafe-units --selftest: %d mutant(s), %d not caught" % (len(ms), bad))
        return 1 if bad else 0
    res = checks(files)
    fails = 0
    for name, ok, detail in res:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, "" if ok or not detail else "  (" + str(detail) + ")"))
        fails += 0 if ok else 1
    if len(res) < 20:
        print("test-ipcsafe-units: only %d checks ran - refusing to pass" % len(res))
        return 1
    print("test-ipcsafe-units: %d checks, %d failed" % (len(res), fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
