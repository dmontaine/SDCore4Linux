#!/usr/bin/env python3
"""test-csvjsonxml-units.py - S.74: the C code of the CSV / JSON / XML task (gplsrc/op_csv.c, op_json.c, op_xml.c), read off the source as text.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-csvjsonxml-units.py
  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-csvjsonxml-units.py --selftest

No sudo, no install, no sd.  Exit 0 every check passed, 1 a check failed, 2 it could not run.

START-HISTORY:
03 Nov 26 dm  New (S.74's left-over: until today only the sandbox suites csvb, jsonx and xmlx named these three files, and nothing held their
              limits as text, so a hand edit that took a depth guard out was seen only if a suite happened to nest that deep).
END-HISTORY

WHAT IT HOLDS.  The invariants a hand edit can break without a suite row noticing:
  CSV   the output buffer grows BEFORE it copies; mode 1 encloses a field that holds the quote, the delimiter, CR, LF or the escape character;
        inside an enclosed field the quote is doubled (or escaped) and the escape character doubled; a dialect string with one character in
        two places or a line break is refused, and FORMCSV / CSV.MODE drop an escape character that is the quote or the delimiter.
  JSON  every recursive walker stops at a depth (merge and descendants at J_MAX_DEPTH 200, a JSONPath filter at 20, a schema at 64) and the
        schema walker gives its depth back on EVERY return after it took it; the faults of JVALIDATE stop at J_MAX_ERRORS 100; every regcomp
        is freed; a $ref reaches into the same schema only ("#" or "#/...").
  XML   no DTD is read: an entity is one of the five or a character reference (not 0, not over 0x10FFFF, its name scan bounded); every
        recursive walker stops at X_MAX_DEPTH 500; the writer escapes & < > always, " LF TAB in an attribute, CR always and any other control
        byte as a space; an XPath expression nests at most 100 deep and gives the depth back on every return.
  ALL   none of the three files opens, runs or removes anything on the system (no fopen, open, popen, system, exec, unlink).

IT READS THE SOURCE AS TEXT.  What the functions DO with real input is the sandbox suites' (sandbox-csvb.py, sandbox-jsonx.py, sandbox-xmlx.py,
sandbox-csvq.py).  --selftest requires each mutation to match its text exactly once and to be caught.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, os.pardir, "gplsrc")
FILES = {"csv": os.path.join(SRC, "op_csv.c"), "json": os.path.join(SRC, "op_json.c"), "xml": os.path.join(SRC, "op_xml.c")}


def strip_c(s):
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    return re.sub(r"//[^\n]*", "", s)


def squash(s):
    return re.sub(r"\s+", " ", s)


def ordered(text, *parts):
    pos = -1
    for p in parts:
        i = text.find(p, pos + 1)
        if i < 0:
            return False
        pos = i
    return True


def body(text, head):
    """The body of the function whose definition starts with HEAD (a prototype, which ends in ';', is skipped); '' when absent."""
    i = 0
    while True:
        i = text.find(head, i)
        if i < 0:
            return ""
        j = text.find("{", i)
        k = text.find(";", i)
        if j >= 0 and (k < 0 or j < k):
            break
        i += len(head)
    depth, n = 0, j
    while n < len(text):
        if text[n] == "{":
            depth += 1
        elif text[n] == "}":
            depth -= 1
            if depth == 0:
                return text[j:n + 1]
        n += 1
    return ""


def gives_back(fbody, take, give):
    """True when FBODY has TAKE once and every 'return' after it has GIVE as the statement just before it.  (count of returns, unbalanced ones)"""
    i = fbody.find(take)
    if i < 0 or fbody.count(take) != 1:
        return False, -1, ["no single '%s'" % take]
    rest = fbody[i + len(take):]
    bad, n = [], 0
    for m in re.finditer(r"\breturn\b[^;]*;", rest):
        n += 1
        before = rest[:m.start()].rstrip()
        if not before.endswith(give):
            bad.append(m.group(0))
    return n > 0 and not bad, n, bad


def checks(src):
    rows = []

    def ck(name, ok, detail=""):
        rows.append((name, bool(ok), detail))

    c, j, x = strip_c(src["csv"]), strip_c(src["json"]), strip_c(src["xml"])
    ck("N0 NULL CASE: the reader sees the three files' code (CSV over 15 KB, JSON over 40 KB, XML over 40 KB)", len(c) > 15000 and len(j) > 40000 and len(x) > 40000,
       repr((len(c), len(j), len(x))))

    # CSV
    fa = body(c, "Private void fb_add(")
    ck("C1 the CSV buffer grows BEFORE it copies: the test is len + n + 1 > cap, the new size doubles until it holds len + n + 1, then the copy",
       ordered(fa, "if (f->len + n + 1 > f->cap)", "while (nc < f->len + n + 1)", "nb = (char*)k_alloc(CSV_TAG, nc);", "memcpy(nb, f->b, f->len);", "memcpy(f->b + f->len, s, n);"), fa[:200])
    pf = squash(body(c, "Private void csv_put_field("))
    ck("C2 mode 1 encloses a field that holds the quote, the delimiter, a line feed, a carriage return or the escape character",
       "enclose = (memchr(s, d->quote, len) != NULL || memchr(s, d->delim, len) != NULL || memchr(s, '\\n', len) != NULL || memchr(s, '\\r', len) != NULL || (d->esc != 0 && memchr(s, d->esc, len) != NULL));" in pf, "")
    ck("C3 inside an enclosed field the quote is written twice (or once after the escape character) and the escape character itself is doubled",
       ordered(pf, "fb_addc(out, d->quote); for (i = 0; i < len; i++) {", "if (s[i] == d->quote) { if (d->esc != 0) fb_addc(out, d->esc); else fb_addc(out, d->quote); }",
               "else if (d->esc != 0 && s[i] == d->esc) { fb_addc(out, d->esc); }", "fb_addc(out, s[i]);", "fb_addc(out, d->quote);"), "")
    df = squash(body(c, "Private bool csvd_from_string("))
    ck("C4 a dialect string with one character in two places, or a line break as the delimiter, quote or escape character, is refused",
       "if (d->delim == d->quote || d->delim == '\\n' || d->delim == '\\r' || d->quote == '\\n' || d->quote == '\\r') return FALSE;" in df
       and "if (d->esc != 0 && (d->esc == d->delim || d->esc == d->quote || d->esc == '\\n' || d->esc == '\\r')) return FALSE;" in df, "")
    fx, qe = squash(body(c, "void x_formcsvx(")), squash(body(c, "void x_csvqesc("))
    ck("C5 FORMCSV(item, delim, quote, esc) and CSV.MODE's operands drop an escape character that is the quote or the delimiter (a quote that is the delimiter is the double quote)",
       "if (cd.esc == cd.quote || cd.esc == cd.delim || cd.quote == cd.delim) cd.esc = 0;" in fx
       and "if (q == process.program.csv_delim || q == '\\n' || q == '\\r') q = '\"';" in qe and "if (e == q || e == process.program.csv_delim || e == '\\n' || e == '\\r') e = 0;" in qe, "")

    # JSON
    mi, de = body(j, "Private void merge_into("), body(j, "Private void descend(")
    ck("J1 J_MAX_DEPTH is 200, and JMERGE's merge and JPATH's descendants both stop at it before they go one level deeper",
       re.search(r"#define J_MAX_DEPTH 200\b", j) is not None and ordered(mi, "depth > J_MAX_DEPTH", "merge_into(te, pe, depth + 1);")
       and ordered(de, "if (depth > J_MAX_DEPTH)", "return;", "descend(&h->e[i], out, depth + 1);"), "")
    ck("J2 a JSONPath filter nests at most 20 deep and gives the level back after it",
       "if (++p->depth > 20 || !qp_or(p, &s.filter)) return qp_fail(p); p->depth--;" in squash(j), "")
    vc = body(j, "Private bool v_check(")
    ok, n, bad = gives_back(vc, "cx->depth++;", "cx->depth--;")
    ck("J3 the schema walker stops at depth 64 BEFORE it takes a level, and every one of its returns after that gives the level back (%d returns)" % n,
       ordered(vc, "if (cx->depth > 64)", "return TRUE;", "cx->depth++;") and ok, "unbalanced: %r" % bad[:3])
    ve = squash(body(j, "Private void v_err("))
    ck("J4 JVALIDATE's faults stop at J_MAX_ERRORS (100): the hundred-and-first is not added and the list is marked cut",
       re.search(r"#define J_MAX_ERRORS 100\b", j) is not None and ordered(ve, "if (cx->count >= J_MAX_ERRORS) { cx->cut = TRUE; return; }", "cx->count++;"), "")
    ck("J5 every regcomp() is freed: as many regfree() as regcomp(), each regfree after its regexec",
       j.count("regcomp(") >= 3 and j.count("regcomp(") == j.count("regfree(") and all(ordered(j[m.start():m.start() + 600], "regexec(", "regfree(") for m in re.finditer(r"regcomp\(", j)),
       repr((j.count("regcomp("), j.count("regfree("))))
    vr = squash(body(j, "Private bool v_ref("))
    ck("J6 a $ref reaches into the same schema only: '#' is the root schema and '#/...' a pointer into it; nothing else is followed",
       ordered(vr, "*target = NULL;", "if (len >= 1 && s[0] == '#') {", "*target = cx->rootschema;", "s[1] == '/' && ptr_parse(", "*target = ptr_get(cx->rootschema,") and "ok = TRUE;" in vr
       and vr.count("*target =") == 3, "")

    # XML
    xe = squash(body(x, "Private bool xp_entity("))
    ck("X1 no DTD: an entity is lt gt amp quot or apos, anything else fails; a character reference is 1 to 0x10FFFF; the name is looked for in 12 bytes at most",
       "while (i < p->n && p->s[i] != ';' && i - start < 12) i++;" in xe and xe.count("if (cp > 0x10FFFF) return xp_fail(p);") == 2 and "if (cp == 0) return xp_fail(p);" in xe
       and ordered(xe, 'memcmp(p->s + start, "lt", 2)', 'memcmp(p->s + start, "gt", 2)', 'memcmp(p->s + start, "amp", 3)', 'memcmp(p->s + start, "quot", 4)', 'memcmp(p->s + start, "apos", 4)',
                   "else return xp_fail(p);") and "<!ENTITY" not in x, "")
    walkers = [("xp_element", "Private bool xp_element(", "if (depth > X_MAX_DEPTH)", "xp_element(p, slot, depth + 1)"),
               ("xw_element", "Private bool xw_element(", "if (depth > X_MAX_DEPTH ||", "xw_element(w, &k->e[i], depth + 1)"),
               ("xd_build", "Private bool xd_build(", "if (depth > X_MAX_DEPTH ||", "xd_build(d, &m->d.data.coll->e[i], self, depth + 1)"),
               ("xn_string", "Private void xn_string(", "if (depth > X_MAX_DEPTH)", "xn_string(d, nd->kids[i], out, depth + 1)"),
               ("x_descend", "Private void x_descend(", "if (depth > X_MAX_DEPTH)", "x_descend(d, nd->kids[i], out, depth + 1)")]
    miss = [w for w, head, guard, rec in walkers if not ordered(body(x, head), guard, rec)]
    ck("X2 X_MAX_DEPTH is 500, and the parser, the writer, the XPath document builder, string() and the descendant axis each test it before they go one level deeper",
       re.search(r"#define X_MAX_DEPTH 500\b", x) is not None and not miss, "unguarded: %r" % miss)
    xw = squash(body(x, "Private void xw_escape("))
    ck("X3 the writer escapes & < > always, \" LF and TAB inside an attribute, CR always, and writes any other control byte as a space",
       ordered(xw, "case '&': xb_add(out, \"&amp;\", 5);", "case '<': xb_add(out, \"&lt;\", 4);", "case '>': xb_add(out, \"&gt;\", 4);", "case '\"': if (attr) xb_add(out, \"&quot;\", 6);",
               "case '\\n': if (attr) xb_add(out, \"&#10;\", 5);", "case '\\r': xb_add(out, \"&#13;\", 5);", "case '\\t': if (attr) xb_add(out, \"&#9;\", 4);",
               "if ((unsigned char)s[i] < 0x20 && s[i] != '\\n' && s[i] != '\\t') {", "xb_addc(out, ' ');"), "")
    xq = body(x, "Private bool xq_expr(")
    ok, n, bad = gives_back(xq, "if (++x->depth > 100)\n    return xq_fail(x);", "x->depth--;")
    ck("X4 an XPath expression nests at most 100 deep, and every return after the level is taken gives it back (%d returns)" % n, ok, "unbalanced: %r" % bad[:3])

    # ALL
    sysc = [(k, m.group(0)) for k, t in (("csv", c), ("json", j), ("xml", x)) for m in re.finditer(r"\b(fopen|popen|open|openat|system|exec[lv]p?e?|unlink|remove|rename)\s*\(", t)]
    ck("A1 none of the three files opens, runs, removes or renames anything on the system", not sysc, repr(sysc[:5]))
    return rows


MUTANTS = [
    ("csv", "the CSV buffer is grown by too little", "    while (nc < f->len + n + 1)\n", "    while (nc < f->len)\n"),
    ("csv", "the CSV buffer copies before it grows", "  if (f->len + n + 1 > f->cap) {", "  if (f->len + n > f->cap + 1) {"),
    ("csv", "mode 1 does not enclose a field holding a line feed", "memchr(s, '\\n', len) != NULL ||\n", ""),
    ("csv", "a quote inside an enclosed field is written once", "      else\n        fb_addc(out, d->quote);\n", "      else\n        ;\n"),
    ("csv", "the escape character is not doubled", "    } else if (d->esc != 0 && s[i] == d->esc) {\n      fb_addc(out, d->esc);\n    }", "    }"),
    ("csv", "a dialect with the delimiter as the quote is taken", "  if (d->delim == d->quote || d->delim == '\\n'", "  if (d->delim == '\\n'"),
    ("csv", "FORMCSV keeps an escape character that is the quote", "  if (cd.esc == cd.quote || cd.esc == cd.delim || cd.quote == cd.delim)\n    cd.esc = 0;", "  if (cd.quote == cd.delim)\n    cd.esc = 0;"),
    ("json", "J_MAX_DEPTH is raised", "#define J_MAX_DEPTH 200", "#define J_MAX_DEPTH 20000"),
    ("json", "JPATH's descendants are walked with no depth limit", "  nl_add(out, e);\n  if (depth > J_MAX_DEPTH)\n    return;\n", "  nl_add(out, e);\n"),
    ("json", "a JSONPath filter nests without a limit", "if (++p->depth > 20 || !qp_or(p, &s.filter))", "if (!qp_or(p, &s.filter))"),
    ("json", "the schema walker keeps a level on its boolean-schema return", "      v_err(cx, path, \"false\", \"no value is allowed here\");\n    cx->depth--;\n", "      v_err(cx, path, \"false\", \"no value is allowed here\");\n"),
    ("json", "the schema walker has no depth limit", "  if (cx->depth > 64)\n    return TRUE;\n", ""),
    ("json", "JVALIDATE's faults are not capped", "  if (cx->count >= J_MAX_ERRORS) {", "  if (0) {"),
    ("json", "a regcomp is never freed", "            rc = regexec(&re, a.s, 0, NULL, 0);\n            regfree(&re);\n", "            rc = regexec(&re, a.s, 0, NULL, 0);\n"),
    ("json", "a $ref may name another document", "  if (len >= 1 && s[0] == '#') {", "  if (len >= 1) {"),
    ("xml", "an unknown entity is taken as text", "    else if (l == 4 && memcmp(p->s + start, \"apos\", 4) == 0)\n      xb_addc(out, '\\'');\n    else\n      return xp_fail(p);",
     "    else if (l == 4 && memcmp(p->s + start, \"apos\", 4) == 0)\n      xb_addc(out, '\\'');\n    else\n      xb_addc(out, '&');"),
    ("xml", "the character reference &#0; is taken", "    if (cp == 0)\n      return xp_fail(p);\n", ""),
    ("xml", "the entity name is scanned without a bound", "p->s[i] != ';' && i - start < 12)", "p->s[i] != ';')"),
    ("xml", "X_MAX_DEPTH is raised", "#define X_MAX_DEPTH 500", "#define X_MAX_DEPTH 500000"),
    ("xml", "the parser has no depth limit", "  if (depth > X_MAX_DEPTH)\n    return xp_fail(p);", "  if (0)\n    return xp_fail(p);"),
    ("xml", "the writer does not escape <", "        xb_add(out, \"&lt;\", 4);", "        xb_addc(out, '<');"),
    ("xml", "a control byte is written as it is", "          xb_addc(out, ' ');\n        } else {", "          xb_addc(out, s[i]);\n        } else {"),
    ("xml", "an XPath 'or' keeps its level on failure", "    if (!xq_and(x, set, ctx, pos, size, &r)) {\n      x->depth--;\n      return FALSE;", "    if (!xq_and(x, set, ctx, pos, size, &r)) {\n      return FALSE;"),
    ("xml", "XPARSE reads a file", "#define X_MAX_DEPTH 500\n", "#define X_MAX_DEPTH 500\nPrivate void *x_peek(const char* f) { return fopen(f, \"r\"); }\n"),
]


def load():
    src = {}
    for k, p in FILES.items():
        with open(p, encoding="latin-1") as f:
            src[k] = f.read()
    return src


def report(rows):
    bad = 0
    for name, ok, detail in rows:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, ("   <- " + detail) if detail and not ok else ""))
        bad += 0 if ok else 1
    return bad


def selftest():
    src = load()
    if any(not ok for _, ok, _ in checks(src)):
        print("REFUSING - the unmutated source already fails", file=sys.stderr)
        return 2
    holes = 0
    print("--- self-test: each mutation must be CAUGHT and match its text once ---")
    for fk, name, old, new in MUTANTS:
        n = src[fk].count(old)
        if n != 1:
            print("  [FAIL] %s: the text matches %d times in %s, not once" % (name, n, fk))
            holes += 1
            continue
        mut = dict(src)
        mut[fk] = src[fk].replace(old, new)
        caught = [r.split(" ")[0] for r, ok, _ in checks(mut) if not ok]
        print("  [%s] %s%s" % ("pass" if caught else "FAIL", name, ": caught by " + ", ".join(caught[:3]) if caught else ": NOT CAUGHT"))
        holes += 0 if caught else 1
    print("\n%d of %d mutants caught, %d missed" % (len(MUTANTS) - holes, len(MUTANTS), holes))
    return 1 if holes else 0


def main():
    missing = [p for p in FILES.values() if not os.path.isfile(p)]
    if missing:
        print("test-csvjsonxml-units: CANNOT RUN - not readable: %s" % missing, file=sys.stderr)
        return 2
    print("test-csvjsonxml-units: reading %s" % ", ".join(os.path.abspath(p) for p in FILES.values()))
    if "--selftest" in sys.argv[1:]:
        return selftest()
    rows = checks(load())
    bad = report(rows)
    print("\nNOT MEASURED HERE: what the functions do with real input (sandbox-csvb.py, sandbox-jsonx.py, sandbox-xmlx.py, sandbox-csvq.py).")
    print("test-csvjsonxml-units: %d checks, %d failed" % (len(rows), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
