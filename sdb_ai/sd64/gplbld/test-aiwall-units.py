#!/usr/bin/env python3
"""test-aiwall-units.py - S.97 stage 0, THE AI BOUNDARY (1 Nov 2026): the wall ($tk_aiwall), where $tk_ai asks it, and every app that sends text, read off the source as text.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-aiwall-units.py
  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-aiwall-units.py --selftest

No sudo, no install, no sd.  Exit 0 every check passed, 1 a check failed, 2 it could not run.

START-HISTORY:
1 Nov 26 dm  New with the wall (CLAUDE.md "THE AI BOUNDARY"; .claude/plan-common-look-1nov.md, S.97 stage 0).
END-HISTORY

WHAT IT HOLDS.  The owner's rule: the AI field never reaches the C and GPL.BP code or any other system information, and no question about SD's own code or build is taken to the AI from
inside SD, for EVERY provider.  Two things in one place: `$tk_ai 'ask'` screens the TYPED request and asks WHERE THE TEXT COMES FROM (actx<13>) before it builds anything for the preview and before
it addresses any provider; `$tk_aiwall` decides by where a FILE is (the kernel's path test: realpath), never by what a text says.  Held here: the order inside `ask` (the screen, the origin, THEN the
preview and the send), fail-shut (a text with no origin is refused), the places that are SD's own, no provider's name anywhere in the wall, that every app that calls `ask` says where its text
comes from (and a NEW caller fails this check until it does), the ai verb's screen, the messages and the audit lines.

***IT READS THE SOURCE AS TEXT.***  That a record of SD's own files is refused, that the screen refuses what it should and passes what it should, for each provider, is
sandbox-ai-boundary.py (the real helper and the fake provider on a private SD).  --selftest requires each mutation to match its text exactly once and to be caught.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SDSYS = os.path.join(HERE, os.pardir, "sdsys")
GPL = os.path.join(SDSYS, "gpl.bp")
MSG = os.path.join(SDSYS, "messages")
FILES = {k: os.path.join(GPL, v) for k, v in (("wall", "tk_aiwall"), ("ai", "tk_ai"), ("ide", "ide"), ("sed", "sed"), ("core", "ced_core"), ("cedit", "ced_edit"), ("dbg", "debug"),
                                                ("dbgh", "debug.h"), ("home", "tool_home"), ("verb", "ai"), ("aipage", "tk_aipage"))}
FILES.update({"m40": os.path.join(MSG, "11940"), "m41": os.path.join(MSG, "11941"), "m42": os.path.join(MSG, "11942")})
# the programs that call $tk_ai('ask' and how each says where its text comes from
CALLERS = {"ide": "@fm : '' : @fm : ai.org", "sed": "@fm : '' : @fm : ai.org", "ced_core": "@fm : '' : @fm : st{'origin'}", "debug": "@fm : '' : @fm : ai.org", "tool_home": "actx<13> = 'none'",
           "tk_aipage": "actx<13> = 'none'"}      # 1 Nov 26 (S.97 stage 1): the AI line on a page of the toolkit sends no text of any file, only what the page is and what it offers
PROVIDER_WORDS = ("anthropic", "openai", "google", "gemini", "deepseek", "custom", "sonnet", "gpt")      # ("claude" is not here: CLAUDE.md is a file this program's header names)


def strip(src):
    """the code without comment lines and trailing ;* comments"""
    out = []
    for ln in src.split("\n"):
        if ln.lstrip().startswith("*"):
            continue
        out.append(re.sub(r"\s*;\*.*$", "", ln))
    return "\n".join(out)


def ordered(text, *parts):
    pos = -1
    for p in parts:
        i = text.find(p, pos + 1)
        if i < 0:
            return False
        pos = i
    return True


def between(text, start, end):
    a = text.find(start)
    if a < 0:
        return ""
    b = text.find(end, a + len(start))
    return text[a:] if b < 0 else text[a:b]


def checks(src, tree_calls):
    rows = []

    def ck(name, ok, detail=""):
        rows.append((name, bool(ok), detail))

    wall, ai, ide, sed, core, cedit, dbg, dbgh, home, verb, aipage = (strip(src[k]) for k in ("wall", "ai", "ide", "sed", "core", "cedit", "dbg", "dbgh", "home", "verb", "aipage"))
    ck("N0 NULL CASE: the reader sees the wall (over 2 KB of code), $tk_ai (over 15 KB), the IDE (over 100 KB) and SED (over 100 KB)", len(wall) > 2000 and len(ai) > 15000 and len(ide) > 100000 and len(sed) > 100000,
       repr((len(wall), len(ai), len(ide), len(sed))))
    ck("W1 the wall is $internal, `subroutine tk_aiwall(op, a, why)`, catalogued as $tk_aiwall, and no other program takes the name",
       wall.lstrip().startswith("$internal") and re.search(r"^subroutine tk_aiwall\(op, a, why\)$", wall, re.M) is not None and "$catalog $tk_aiwall" in wall
       and sum(1 for t in tree_calls["catalog"] if t == "$tk_aiwall") == 1, repr(tree_calls["catalog"][:3]))
    bad = re.findall(r"\b(write|writev|writeu|delete|execute|perform|chain|oscopy|openseq|openpath|readseq|writeseq|sh)\b", wall, re.I)
    ck("W2 the wall writes nothing, runs nothing and reads no file's text (it only opens a file to ask where it is, and closes it)", not bad and "readv" not in wall and re.search(r"\bread\b", wall) is None, repr(bad[:5]))
    low = src["wall"].lower()
    ck("W3 NO PROVIDER IS NAMED in the wall, in code or in comment: it is one rule for every provider", not [w for w in PROVIDER_WORDS if w in low], repr([w for w in PROVIDER_WORDS if w in low]))
    ck("W4 an origin whose kind is none, untitled or empty is let through, a kind that is not record or path is 'unknown', and a record needs a file and an id", ordered(wall, "check.origin:", "kind = a<1, 1>",
       "if kind = '' or kind = 'none' or kind = 'untitled' then return", "case kind = 'path'", "case kind = 'record'", "if rf = '' or a<1, 3> = '' then", "why = 'unknown'", "case 1")
       and "why = 'unknown'" in between(wall, "      case 1\n", "   end case"), "")
    ck("W5 a record is found by opening its file (the dictionary for a dictionary item) and asking FILEINFO FL$PATH, and a file that cannot be opened is 'unknown'",
       ordered(wall, "open 'DICT', rf to fv else", "why = 'unknown'", "open rf to fv else", "why = 'unknown'", "pth = fileinfo(fv, FL$PATH)", "close fv"), "")
    ck("W6 a path that is not absolute is 'unknown'", ordered(wall, "if pth[1, 1] # '/' then", "why = 'unknown'", "return"), "")
    ck("W7 THE PLACES THAT ARE SD'S OWN are tested with the kernel's path test (K$PATH.IN: realpath): the system directory, the AI helper's two directories and its socket directory, /run/sd and /etc/sd.conf",
       ordered(wall, "places = @sdsys", "'/var/lib/sd-ai'", "'/usr/local/lib/sd-ai'", "'/run/sd-ai'", "'/run/sd'", "'/etc/sd.conf'", "kernel(K$PATH.IN, places<i> : @fm : pth)", "why = 'system'"), "")
    ck("W8 a directory called gplsrc, gplbld or gplobj on the way is the build tree, wherever a copy is: 'system'", ordered(wall, "c = field(pth, '/', i)", "c = 'gplsrc'", "c = 'gplbld'", "c = 'gplobj'", "why = 'system'"), "")
    toks = between(wall, "check.request:", "op_name")
    ck("R1 THE SCREEN names the system's code: gpl.bp, gplsrc, gplbld, gplobj, $internal, bcomp, bbcmp, bbproc, pcode_bld, sysseg, revstamp, makefile, sd_dev_build, sd -internal, kernel(, .git-private, project_status and the phrases about SD's source",
       all(("'%s'" % t) in toks or ('"%s"' % t) in toks for t in ("gpl.bp", "gplsrc", "gplbld", "gplobj", "$internal", "bcomp", "bbcmp", "bbproc", "pcode_bld", "sysseg", "revstamp", "makefile", "sd_dev_build",
                                                                   "sd -internal", "kernel(", ".git-private", "project_status", "sd source", "source of sd", "kernel source", "kernel code")) and "sd's source" in toks, "")
    ck("R2 the screen does NOT take the names a person's own programs meet: syscom, newvoc and voc_template are not on it (a program includes the headers of syscom and sees newvoc)",
       not any(("'%s'" % t) in toks for t in ("syscom", "newvoc", "voc_template")), "")
    ck("R3 the screen reads the lower-cased TYPED request: it scans op_name.c and a key k$name by hand (a name needs the letters after it)", ordered(wall, "low = downcase(a)", "index(low, toks<i>, 1)", "p = index(low, 'op_', occ)",
       "low[q, 2] = '.c'", "why = 'op_*.c'", "p = index(low, 'k$', occ)", "why = 'k$'"), "")
    m = between(ai, "call $tk_aiwall('request', req, why)", "no.cmd") or ai
    ck("A1 IN $tk_ai 'ask' THE WALL COMES BEFORE ANYTHING IS BUILT FOR THE PREVIEW AND BEFORE ANY PROVIDER IS ADDRESSED: the typed request is screened, then the origin, each refusal returns, and only then the text, the preview and K$AI.START",
       ordered(ai, "run.ask:", "req = trim(clean.out)", "app = a<1>", "call $tk_aiwall('request', req, why)", "if why # '' then", "return", "call $tk_aiwall('origin', origin, why)", "if why # '' then", "return",
               "tb.raw = a<8>", "sysx = sysmsg(11635, app)", "screen msgbox body", "rq = kernel(K$AI.START")
       and 0 <= ai.find("call $tk_aiwall('request'") < ai.find("sysx = sysmsg(11635") and ai.find("call $tk_aiwall('origin'") < ai.find("sysx = sysmsg(11635") and ai.count("sysx = sysmsg(11635") == 1
       and ai.find("call $tk_aiwall('origin'") < ai.find("screen msgbox body") and ai.count("kernel(K$AI.START") == 1 and ai.find("call $tk_aiwall('origin'") < ai.find("kernel(K$AI.START"), "")
    ck("A2 FAIL SHUT: an app that gives a text (<8> or <10>) and no origin is refused as unknown, whatever else it says", ordered(ai, "origin = a<13>", "if origin = '' and (a<8> # '' or a<10> # '') then origin = 'unknown'",
       "call $tk_aiwall('origin', origin, why)"), "")
    ck("A3 each refusal is a message in words and ONE audit line that names why and the app and never the text: request (the name found), origin (the kind and the reason)",
       "void kernel(K$AUDIT, 'ai refused why=request app=' : downcase(app) : ' name=' : why)" in ai and "sysmsg(11941, why)" in ai
       and "void kernel(K$AUDIT, 'ai refused why=origin app=' : downcase(app) : ' kind=' : origin<1, 1> : ' reason=' : why)" in ai and "sysmsg(11940)" in ai and "sysmsg(11942)" in ai
       and ai.count("K$AUDIT") == 2, "")
    ck("A4 the refusal result is a result of 'none' with the message on res<5>, the line the apps show on their status rows", ai.count("b = 'none' : @fm : '' : @fm : '' : @fm : '' : @fm : sysmsg(11941, why)") == 1
       and ai.count("(if why = 'system' then sysmsg(11940) else sysmsg(11942))") == 1, "")
    sites = tree_calls["ask"]
    ck("C1 EVERY PROGRAM THAT CALLS $tk_ai('ask' IS ON THE LIST HERE and says where its text comes from: %s (a new caller is refused by this check until it is added with its origin)" % ", ".join(sorted(CALLERS)),
       sorted(sites) == sorted(CALLERS), repr(sorted(sites)))
    ok = {"ide": ide, "sed": sed, "ced_core": core, "debug": dbg, "tool_home": home, "tk_aipage": aipage}
    ck("C2 each of them has its origin in the request it builds", all(CALLERS[k] in ok[k] for k in CALLERS), repr([k for k in CALLERS if CALLERS[k] not in ok[k]]))
    d = between(ide, "ai.origin:", "* The fields view")
    ck("C3 the IDE's origin: untitled when there is no record yet, path (the operating system pathname) for a path: tab, a record with its file, its id and the dictionary flag otherwise; the fields view gets the same",
       ordered(d, "if bi<cb> = '' then", "ai.org = 'untitled'", "if bn<cb> = 'path:' then", "ai.org = 'path' : @vm : '' : @vm : bi<cb>", "ai.org = 'record' : @vm : bn<cb> : @vm : bi<cb> : @vm : (if bx{k} # '' then 1 else 0)")
       and ordered(ide, "gosub ai.origin", "actx = 'IDE'") and ordered(ide, "fz.st{'title'} = fz.title", "gosub ai.origin", "fz.st{'origin'} = ai.org"), "")
    ck("C4 SED's origin: untitled for a buffer with no record name, else the file, the record and the dictionary flag", ordered(sed, "if record.name = '' then", "ai.org = 'untitled'",
       "ai.org = 'record' : @vm : file.name : @vm : record.name : @vm : (if dict.flag = 'DICT' then 1 else 0)", "ai.actx = 'SED'"), "")
    ck("C5 the collection editor's host says none (a collection a program holds is no record of any file) and the engine passes whatever its host set", "st{'origin'} = 'none'" in cedit and "st{'origin'}" in core, "")
    ck("C6 the debugger's page text holds the program's SOURCE, so its origin is the source record's pathname, kept for each program in debug.h's common block when the program is first seen",
       "program.src(INITIAL.PROGRAMS)" in dbgh and "program.src(idx) = source.path" in dbg and ordered(dbg, "ai.org = 'path' : @vm : '' : @vm : program.src(src.idx)", "ai.actx = 'debugger'"), "")
    ck("C7 the home screen sends no text of a file and says so", "actx<13> = 'none'" in home, "")
    ck("V1 THE ai VERB takes the same screen on the typed question, BEFORE it asks the helper anything: refused with 11941, one audit line, a failure code", ordered(verb, "if question = '' then stop sysmsg(11623)",
       "call $tk_aiwall('request', question, why)", "void kernel(K$AUDIT, 'ai refused why=request app=ai name=' : why)", "stop sysmsg(11941, why)", "reply = kernel(K$AI.STATUS, 0)"), "")
    mm = {k: src[k] for k in ("m40", "m41", "m42")}
    ck("M1 messages 11940, 11941 and 11942 exist, 11941 takes the name found (%1), none says a provider's name, and each is under 200 characters",
       "%1" in mm["m41"] and all(0 < len(t.strip()) < 200 for t in mm.values()) and not [w for t in mm.values() for w in PROVIDER_WORDS if w in t.lower()], "")
    return rows


def calls_of(raw):
    """what the whole of gpl.bp holds: the programs that call $tk_ai('ask' and every $catalog name"""
    ask, catalog = [], []
    for n in sorted(os.listdir(GPL)):
        p = os.path.join(GPL, n)
        if not os.path.isfile(p):
            continue
        with open(p, encoding="latin-1") as f:
            t = strip(f.read())
        if "$tk_ai('ask'" in t and n != "tk_ai":
            ask.append(n)
        for m in re.finditer(r"^\$catalog\s+(\S+)", t, re.M):
            catalog.append(m.group(1))
    return {"ask": ask, "catalog": catalog}


def load():
    src = {}
    for k, p in FILES.items():
        with open(p, encoding="latin-1") as f:
            src[k] = f.read()
    return src


def report(rows):
    bad = 0
    for name, ok, detail in rows:
        bad += 0 if ok else 1
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, "" if ok else "   <- " + detail))
    return bad


# (file key, name, old, new): each must match its file's text once and be caught
MUTANTS = [
    ("ai", "the typed request is not screened", "   call $tk_aiwall('request', req, why)\n   if why # '' then", "   why = ''\n   if why # '' then"),
    ("ai", "the origin is not asked", "   call $tk_aiwall('origin', origin, why)\n   if why # '' then", "   why = ''\n   if why # '' then"),
    ("ai", "a text with no origin is let through", "   if origin = '' and (a<8> # '' or a<10> # '') then origin = 'unknown'", "   if origin = '' and (a<8> # '' or a<10> # '') then origin = 'none'"),
    ("ai", "the wall comes after the preview is built", "   call $tk_aiwall('request', req, why)\n   if why # '' then\n      void kernel(K$AUDIT, 'ai refused why=request",
     "   sysx = sysmsg(11635, app)\n   call $tk_aiwall('request', req, why)\n   if why # '' then\n      void kernel(K$AUDIT, 'ai refused why=request"),
    ("ai", "the refusal does not return", "      b = 'none' : @fm : '' : @fm : '' : @fm : '' : @fm : sysmsg(11941, why)\n      return", "      b = 'none' : @fm : '' : @fm : '' : @fm : '' : @fm : sysmsg(11941, why)"),
    ("ai", "the audit line carries the typed request", "' name=' : why)\n      b = 'none'", "' name=' : why : ' text=' : req)\n      b = 'none'"),
    ("wall", "a provider is named in the wall", "No provider is named anywhere in this program", "This rule is for Anthropic only"),
    ("wall", "the system directory is not a place", "   places = @sdsys : @fm : '/var/lib/sd-ai'", "   places = '/var/lib/sd-ai'"),
    ("wall", "the helper's state is not a place", ": @fm : '/var/lib/sd-ai' : @fm : '/usr/local/lib/sd-ai'", ": @fm : '/usr/local/lib/sd-ai'"),
    ("wall", "the build tree is not looked for", "      if c = 'gplsrc' or c = 'gplbld' or c = 'gplobj' then", "      if c = 'gplsrcx' then"),
    ("wall", "a file that cannot be opened is let through", "         open rf to fv else\n               why = 'unknown'\n               return\n            end", "         open rf to fv else\n               null\n            end"),
    ("wall", "a relative path is let through", "   if pth[1, 1] # '/' then\n      why = 'unknown'\n      return\n   end", "   if pth[1, 1] # '/' then\n      return\n   end"),
    ("wall", "a kind that is not known is let through", "      case 1\n         why = 'unknown'\n         return\n   end case\n\n   if pth[1, 1]", "      case 1\n         return\n   end case\n\n   if pth[1, 1]"),
    ("wall", "the screen drops gplsrc", "'gpl.bp' : @fm : 'gplsrc' : @fm :", "'gpl.bp' : @fm :"),
    ("wall", "the screen takes syscom", "@fm : 'sysseg'\n   toks := @fm : 'revstamp'", "@fm : 'sysseg' : @fm : 'syscom'\n   toks := @fm : 'revstamp'"),
    ("wall", "op_name.c is not scanned", "         if low[q, 2] = '.c' then", "         if low[q, 2] = '.cx' then"),
    ("ide", "the IDE does not say where its text comes from", ": @fm : 'nocmd' : @fm : '' : @fm : ai.org", ": @fm : 'nocmd'"),
    ("ide", "the IDE's fields view does not say where its record comes from", "   fz.st{'origin'} = ai.org ", "   fz.st{'origin2'} = ai.org "),
    ("sed", "SED does not say where its text comes from", ": @fm : 'nocmd' : @fm : '' : @fm : ai.org", ": @fm : 'nocmd'"),
    ("core", "the fields engine drops the origin", ": @fm : '' : @fm : st{'origin'}", ""),
    ("dbg", "the debugger does not keep a program's source path", "   program.src(idx) = source.path ", "   program.src(idx) = '' "),
    ("home", "the home screen no longer says none", "   actx<13> = 'none' ", "   actx<14> = 'none' "),
    ("verb", "the ai verb is not screened", "   call $tk_aiwall('request', question, why)\n   if why # '' then", "   why = ''\n   if why # '' then"),
]


def selftest():
    src = load()
    tc = calls_of(src)
    if any(not ok for _, ok, _ in checks(src, tc)):
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
        caught = [x.split(" ")[0] for x, ok, _ in checks(mut, tc) if not ok]
        print("  [%s] %s%s" % ("pass" if caught else "FAIL", name, ": caught by " + ", ".join(caught[:3]) if caught else ": NOT CAUGHT"))
        holes += 0 if caught else 1
    t2 = dict(tc)
    t2["ask"] = tc["ask"] + ["zz_newapp"]
    caught = [x.split(" ")[0] for x, ok, _ in checks(src, t2) if not ok]
    print("  [%s] a new program that calls $tk_ai('ask' and is not on the list%s" % ("pass" if caught else "FAIL", ": caught by " + ", ".join(caught) if caught else ": NOT CAUGHT"))
    holes += 0 if caught else 1
    t3 = dict(tc)
    t3["catalog"] = tc["catalog"] + ["$tk_aiwall"]
    caught = [x.split(" ")[0] for x, ok, _ in checks(src, t3) if not ok]
    print("  [%s] another program takes the catalogue name%s" % ("pass" if caught else "FAIL", ": caught by " + ", ".join(caught) if caught else ": NOT CAUGHT"))
    holes += 0 if caught else 1
    total = len(MUTANTS) + 2
    print("\n%d of %d mutants caught, %d missed" % (total - holes, total, holes))
    return 1 if holes else 0


def main():
    missing = [p for p in FILES.values() if not os.path.isfile(p)]
    if missing:
        print("test-aiwall-units: CANNOT RUN - not readable: %s" % missing, file=sys.stderr)
        return 2
    if "--selftest" in sys.argv[1:]:
        return selftest()
    src = load()
    rows = checks(src, calls_of(src))
    bad = report(rows)
    print("\nNOT MEASURED HERE: that a record of SD's own files is refused and an account's own is not, for each provider.  That is sandbox-ai-boundary.py.")
    print("test-aiwall-units: %d checks, %d failed" % (len(rows), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
