#!/usr/bin/env python3
"""test-aidocs-units.py - the AI line's documentation passages ($tk_aidocs and its place in $tk_ai; S.100), as invariants read off the source.  Free: no install, no sudo, no sd.

    python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-aidocs-units.py [--selftest]

WHAT THIS IS, AND WHAT IT IS NOT.  It reads the BASIC as text, comments removed.  ***IT RUNS NOTHING, SO IT CANNOT SAY WHICH PASSAGE IS CHOSEN OR THAT A SESSION SEES ONE***: that is
`sandbox-aidocs.py`.  What a text check is for here: the properties that keep the feature inside its limits are ORDER and ABSENCE - the reader looks at docs/admin only after it has asked the
kernel for the administrator, reads no directory but the two, takes no file name that is not plain, reads nothing and writes nothing outside them, and tk_ai asks for the passages only AFTER
the wall has screened the request, puts them in the preview as well as in the request, and says what they are in the instruction - and an edit that breaks one still compiles.

--selftest breaks each invariant in the way an edit plausibly would and requires a check to notice; a mutant that nothing catches is a failure of the self-test.

HISTORY: 3 Nov 26 dm  AD13 and its mutant anchor on `call $tk_wrap(sysmsg(11920, ...), wrapw, pieces)` and `body<-1> = pieces<p>`: 1d587a48 wraps the 11920 line (it ran over the box at 140
columns), so the old anchor `body<-1> = sysmsg(11920, ...)` was gone and AD13 failed on a correct tk_ai.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SDSYS = os.path.normpath(os.path.join(HERE, "..", "sdsys"))
GPL = os.path.join(SDSYS, "gpl.bp")
FILES = {
    "docs": os.path.join(GPL, "tk_aidocs"),
    "ai": os.path.join(GPL, "tk_ai"),
    "m20": os.path.join(SDSYS, "messages", "11920"),
    "m21": os.path.join(SDSYS, "messages", "11921"),
    "m22": os.path.join(SDSYS, "messages", "11922"),
    "inst": os.path.normpath(os.path.join(HERE, "..", "..", "..", "installsdcore.sh")),
}


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


def ordered(text, *needles):
    pos = -1
    for n in needles:
        i = text.find(n, pos + 1)
        if i < 0:
            return False
        pos = i
    return True


def label(text, name):
    """the lines of the internal subroutine `name:` up to the next label at column 0"""
    m = re.search(r"^%s:\n(.*?)(?=^[a-z][a-z.0-9]*:\n|\Z)" % re.escape(name), text, re.S | re.M)
    return m.group(1) if m else ""


def checks(raw):
    rows = []

    def ck(i, what, ok, detail=""):
        rows.append((i, what, bool(ok), detail))

    d, ai = strip_bas(raw["docs"]), strip_bas(raw["ai"])
    ld = label(d, "list.dir")
    rp = label(d, "read.page")
    fp = label(d, "find.passages")
    ck("AD0", "NULL CASE: the reader, tk_ai and the three messages were found and are not empty (a check on nothing would pass)",
       len(d) > 500 and len(ai) > 2000 and len(ld) > 100 and len(rp) > 100 and len(fp) > 200 and all(raw[k].strip() for k in ("m20", "m21", "m22")), repr((len(d), len(ai), len(ld), len(rp), len(fp))))
    ck("AD1", "$tk_aidocs is an internal subroutine with three arguments, catalogued $tk_aidocs (the kernel trusts an internal program with an OPENSEQ by pathname: that is why it is one)",
       re.search(r"\$internal\s*\nsubroutine tk_aidocs\(op, a, res\)\s*\n\$catalog \$tk_aidocs\b", d) is not None, "")
    ck("AD2", "THE ADMINISTRATOR'S PAGES ARE ASKED FOR AFTER THE KERNEL HAS BEEN ASKED: in list.dir the administrator test comes before the one dir() call, which is the only dir() of the program",
       len(re.findall(r"\bdir\(", d)) == 1 and ordered(ld, "if dkind = 'admin' then", "kernel(K$ADMINISTRATOR, -1)", "then return", "ent = dir(@sdsys : @ds : 'docs' : @ds : dkind)"), repr(len(re.findall(r"\bdir\(", d))))
    ck("AD3", "only the two directories are ever listed: list.dir returns at once for any kind but user and admin",
       ordered(ld, "if dkind # 'user' and dkind # 'admin' then return", "ent = dir(") and d.count("'docs'") == 2, repr(d.count("'docs'")))
    ck("AD4", "a file name is lower case letters, digits and . _ - , ends in .md, does not start with a dot, holds no .., and is at most 80 characters",
       "okn = 'abcdefghijklmnopqrstuvwxyz0123456789._-'" in ld and "nm[len(nm) - 2, 3] = '.md'" in ld and "nm[1, 1] # '.'" in ld and "index(nm, '..', 1) = 0" in ld and "len(nm) <= 80" in ld
       and "convert('x', '', convert(okn, str('x', len(okn)), nm)) = ''" in ld, "")
    ck("AD5", "the one OPENSEQ is READONLY, on the path built from the system directory, the kind and the checked name; a page over TD.MAXFILE or with a byte of 248 or more, or short of its size, is left out",
       d.count("openseq") == 1 and "openseq path readonly to f then" in rp and "path = @sdsys : @ds : 'docs' : @ds : dkind : @ds : nm" in rp and "fsize <= TD.MAXFILE" in rp and "len(buf) = fsize" in rp
       and "char(248) : char(249) : char(250) : char(251) : char(252) : char(253) : char(254) : char(255)" in rp and "char(0)" in rp, repr(d.count("openseq")))
    ck("AD6", "NOTHING IS WRITTEN OR RUN: no write, delete, execute, os.execute, perform, chain, writeseq, writeblk, weofseq, openpath, open, kernel call but the administrator test, and no $ call",
       not re.search(r"^\s*(?:execute|os\.execute|perform|chain|write[uvs]?|writeseq|writeblk|weofseq|delete[uv]?|deleteseq|matwrite|openpath|open|call\s+\$)\b", d, re.M)
       and re.findall(r"kernel\(([A-Z$.]+)", d) == ["K$ADMINISTRATOR"] * len(re.findall(r"kernel\(", d)), repr(re.findall(r"kernel\(([A-Z$.]+)", d)))
    ck("AD7", "the limits: 4 passages, 2,400 bytes each and 6,000 in all, 8 words, 160 pages, a page up to 120,000 bytes",
       all(re.search(x + r"(?![0-9])", d) for x in (r"TD\.MAXFILE = 120000", r"TD\.MAXFILES = 160", r"TD\.MAXTOK = 8", r"TD\.PASSAGES = 4", r"TD\.EACH = 2400", r"TD\.TOTAL = 6000")), "")
    ck("AD8", "a passage is chosen only when at least half of the request's words are in it (so one common word never picks a page) and scores a third of the best; a request with no usable word chooses nothing",
       "need = int((ntok + 1) / 2)" in fp and "if got < need then sc = 0" in fp and "bs * 3 < best" in fp and re.search(r"gosub tokenize\s*\n\s*ntok = dcount\(toks, @fm\)\s*\n\s*if ntok = 0 then return", fp) is not None, "")
    ck("AD9", "what is returned has no byte but plain ASCII and the line feed (a byte of the page that is not, and any control byte, is a ?, one for one)",
       "for q = 1 to 255" in d and "if q # 10 and (q < 32 or q > 126) then odd.bytes := char(q)" in d and "convert(odd.bytes, str('?', len(odd.bytes)), txt)" in fp
       and "convert(odd.bytes, str('?', len(odd.bytes)), s.title(bi))" in fp, "")
    ck("AD10", "a # inside a fenced block does not start a section: the fence state is toggled by the count of ``` in each piece and a heading is taken only when it is not inside one",
       ordered(label(d, "split.sections"), "if not(inside) then", "is.head = 1", "if mod(count(seg, '```'), 2) = 1 then inside = 1 - inside"), "")
    ck("AD11", "TK_AI ASKS FOR THE PASSAGES AFTER THE WALL: the request screen and the origin check come first (and, 3 Nov 26, the screen of a follow-up's earlier questions), then $tk_aidocs 'find' with the typed request",
       ai.count("$tk_aidocs(") == 1 and ai.count("$tk_aiwall('request'") == 3 and ordered(ai, "call $tk_aiwall('request', req, why)", "call $tk_aiwall('origin', origin, why)",
                                                                                      "call $tk_aiwall('request', h.q<hi>, why)", "call $tk_aiwall('request', cx.text, why)",      # S.160: the standing text
                                                                                      "call $tk_aidocs('find', req, dres)", "sysx = sysmsg(11635, app)"), "")
    ck("AD12", "the passages are in the REQUEST (each with its id in brackets, before the typed request, which stays last) and the instruction says what they are, only when there are some",
       "if n.doc > 0 then sysx := ' ' : sysmsg(11922)" in ai and ai.count("'Request: '") == 1 and ordered(ai, "for i = 1 to n.doc\n      prompt := nl : nl : 'Documentation passage [' : dres<2, i> : '] ' : dres<3, i> : ':' : nl : dres<4, i>", "prompt := nl : nl : 'Request: ' : req"), "")
    ck("AD13", "the passages are in the PREVIEW, before the person's own request: their number and size, each one's id and size, its first lines, and a count of the rest; Send and Cancel are asked after",
       ordered(ai, "call $tk_wrap(sysmsg(11920, n.doc, doc.bytes), wrapw, pieces)", "body<-1> = pieces<p>", "body<-1> = sysmsg(11921, dres<2, i>", "body<-1> = sysmsg(11643, len(req))", "screen msgbox body title sysmsg(11639) buttons '&Send,&Cancel' default 2"), "")
    ck("AD14", "the passage text sent is the passage the preview counts: the byte count the preview shows is the sum of the lengths of dres<4, i>",
       "doc.bytes += len(dres<4, i>)" in ai and "for i = 1 to n.doc" in ai, "")
    m20, m21, m22 = (raw[k].rstrip("\n") for k in ("m20", "m21", "m22"))
    ck("AD15", "messages 11920, 11921 and 11922 are one line each, 11920 takes two substitutions and 11921 two, 11922 is the sentence that tells the model what the passages are and to name the id",
       "\n" not in m20 and "\n" not in m21 and "\n" not in m22 and "%1" in m20 and "%2" in m20 and "%1" in m21 and "%2" in m21 and "%3" not in m20 + m21 and "id in brackets" in m22 and "say which id" in m22 and "documentation" in m22.lower(), repr((m20[:40], m21, m22[:40])))
    ck("AD16", "the installer fetches the documentation from its own repository at the branch it installs and the administrator's pages land 700 / 600 (test-install-aidocs.sh runs both blocks)",
       'DOCS_URL="https://github.com/dmontaine/SDCore4LinuxDocs"' in raw["inst"] and "# DOCS-CORPUS-BEGIN" in raw["inst"] and '--branch "$REPO_BRANCH" --depth 1 "$DOCS_URL"' in raw["inst"]
       and 'chmod 700 "$sdsysdir/docs/admin"' in raw["inst"] and "-exec chmod 600 {} +" in raw["inst"], "")
    return rows


def sub(key, old, new):
    def f(raw):
        r = dict(raw)
        if r[key].count(old) != 1:
            raise KeyError("%s: the text to change is found %d times, not once: %r" % (key, r[key].count(old), old[:60]))
        r[key] = r[key].replace(old, new)
        return r
    return f


MUTANTS = [
    ("the administrator is not asked before docs/admin", "AD2", sub("docs", "      if not(kernel(K$ADMINISTRATOR, -1)) then return", "      if 0 then return")),
    ("a second directory listing", "AD2", sub("docs", "   ent = dir(@sdsys : @ds : 'docs' : @ds : dkind)", "   ent = dir(@sdsys : @ds : 'docs' : @ds : dkind)\n   ent2 = dir(@sdsys)")),
    ("any kind of directory", "AD3", sub("docs", "   if dkind # 'user' and dkind # 'admin' then return", "   if 0 then return")),
    ("a capital in a file name", "AD4", sub("docs", "okn = 'abcdefghijklmnopqrstuvwxyz0123456789._-'\n   for i = 1 to dcount(ent", "okn = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-'\n   for i = 1 to dcount(ent")),
    ("any suffix", "AD4", sub("docs", "nm[len(nm) - 2, 3] = '.md'", "1")),
    ("a name with two dots", "AD4", sub("docs", " and index(nm, '..', 1) = 0", "")),
    ("the page is opened for writing", "AD5", sub("docs", "openseq path readonly to f then", "openseq path to f then")),
    ("a page of any size", "AD5", sub("docs", "fsize > 0 and fsize <= TD.MAXFILE", "fsize > 0")),
    ("a page with a byte of 248 or more", "AD5", sub("docs", "char(248) : char(249) : char(250) : char(251) : char(252) : char(253) : char(254) : char(255)", "char(250)")),
    ("a record is written", "AD6", sub("docs", "   res = ''\n\n   begin case", "   res = ''\n   write 'x' to nowhere, 'y'\n\n   begin case")),
    ("the program asks the kernel for something else", "AD6", sub("docs", "adm = kernel(K$ADMINISTRATOR, -1) + 0", "adm = kernel(K$ADMINISTRATOR, -1) + 0 + kernel(K$USERNAME, 0)")),
    ("passages without a limit", "AD7", sub("docs", "TD.TOTAL = 6000", "TD.TOTAL = 600000")),
    ("one word of the request is enough", "AD8", sub("docs", "need = int((ntok + 1) / 2)", "need = 1")),
    ("a weak section is a passage", "AD8", sub("docs", "bs * 3 < best", "bs * 300 < best")),
    ("a byte of 128 and up is sent as it is", "AD9", sub("docs", "if q # 10 and (q < 32 or q > 126) then odd.bytes", "if q # 10 and (q < 32 or q > 255) then odd.bytes")),
    ("a # in a block starts a section", "AD10", sub("docs", "      if not(inside) then\n         if seg[1, 2]", "      if 1 then\n         if seg[1, 2]")),
    ("the passages are asked for before the wall", "AD11", sub("ai", "   call $tk_aiwall('request', req, why)\n   if why # '' then", "   call $tk_aidocs('find', req, dres)\n   call $tk_aiwall('request', req, why)\n   if why # '' then")),
    ("the instruction does not say what the passages are", "AD12", sub("ai", "   if n.doc > 0 then sysx := ' ' : sysmsg(11922)", "   if 0 then sysx := ' ' : sysmsg(11922)")),
    ("the passages come after the typed request", "AD12", sub("ai", "   for i = 1 to n.doc\n      prompt := nl", "   prompt := nl : nl : 'Request: ' : req\n   for i = 1 to n.doc\n      prompt := nl")),
    ("the preview does not show the passages", "AD13", sub("ai", "      call $tk_wrap(sysmsg(11920, n.doc, doc.bytes), wrapw, pieces)", "      pieces = ''")),
    ("the preview counts something else", "AD14", sub("ai", "doc.bytes += len(dres<4, i>)", "doc.bytes += 1")),
    ("the installer takes the source repository's docs", "AD16", sub("inst", 'DOCS_URL="https://github.com/dmontaine/SDCore4LinuxDocs"', 'DOCS_URL="https://github.com/dmontaine/SDCore4Linux"')),
    ("the administrator's pages are readable by everyone", "AD16", sub("inst", 'chmod 700 "$sdsysdir/docs/admin"', 'chmod 755 "$sdsysdir/docs/admin"')),
    ("message 11922 names no id", "AD15", sub("m22", "its id in brackets", "a mark in brackets")),
]


def load():
    raw = {}
    for k, p in FILES.items():
        try:
            with open(p, encoding="latin-1") as f:
                raw[k] = f.read()
        except OSError:
            raw[k] = ""
    return raw


def report(rows):
    bad = 0
    for i, what, ok, detail in rows:
        print("  [%s] %s %s%s" % ("PASS" if ok else "FAIL", i, what, "" if ok or not detail else "   <- " + str(detail)[:200]))
        bad += 0 if ok else 1
    return bad


def selftest(raw):
    base = [r[0] for r in checks(raw) if not r[2]]
    if base:
        print("selftest: the unchanged tree fails %s, so a mutant's own failure cannot be told from the tree's; run the plain check first" % base)
        return 1
    holes = 0
    for name, want, mut in MUTANTS:
        try:
            m = mut(raw)
        except KeyError as exc:
            print("  [FAIL] selftest: %s  <- %s" % (name, exc))
            holes += 1
            continue
        failed = sorted({r[0] for r in checks(m) if not r[2]})
        hit = want in failed
        print("  [%s] selftest: %s is caught by %s (failed: %s)" % ("PASS" if hit else "FAIL", name, want, " ".join(failed) or "none"))
        holes += 0 if hit else 1
    print("selftest: %d mutants, %d not caught" % (len(MUTANTS), holes))
    return 1 if holes else 0


def main(argv):
    raw = load()
    empty = [k for k, v in raw.items() if not v.strip()]
    if empty:
        print("test-aidocs-units: CANNOT RUN - nothing found for %s" % ", ".join(empty))
        return 2
    if "--selftest" in argv:
        return selftest(raw)
    rows = checks(raw)
    bad = report(rows)
    print("test-aidocs-units: %d checks, %d failed" % (len(rows), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
