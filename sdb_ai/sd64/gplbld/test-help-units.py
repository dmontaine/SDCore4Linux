#!/usr/bin/env python3
"""test-help-units.py - the context help and the [?] button (S.75, plan .claude/plan-fullscreen-toolkit.md section 14.5), as invariants read off the source.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-help-units.py
  python3 .../test-help-units.py --selftest

No sudo, no install, no sd.  Exit 0 every check passed, 1 a check failed, 2 it could not run.

WHAT IT HOLDS.  $tk_help looks a key up only after testing its characters, only in the file context.help of the shared account (found with !shared_ref asked QUIETLY, opened by
path and only read), and runs nothing but pdf <name> through $tk_run; the [?] button answers a left press on its three cells and nothing else; LOAD.HELP asks for the
administrator before it reads anything, writes only records of that one file, makes only that file and goes back to the account it began in; the shipped text under helptext has
a title, a document that exists in the documentation checkout, and is used by a program; every key a page asks for has a record; the wrapping loop lives in $tk_wrap.

***IT READS THE SOURCE AS TEXT AND DOES NOT RUN BASIC.***  That the box shows the text, F1 and a click open it, and LOAD.HELP fills the file is sandbox-help.py.

--selftest mutates the source in the ways this could plausibly be broken and requires each mutation to be CAUGHT and to match its text exactly once.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SDSYS = os.path.abspath(os.path.join(HERE, os.pardir, "sdsys"))
GPL = os.path.join(SDSYS, "gpl.bp")
HELP = os.path.join(SDSYS, "helptext")
DOCS = "/home/don/Projects/SDCore4LinuxDocs"                    # the documentation checkout: an absolute path, as test-pack-units.py has it
PROGS = ("tk_help", "loadhelp", "tool_menus", "tool_viewers", "tk_wrap", "tk_confirm")
MSGS = tuple(str(n) for n in list(range(11830, 11833)) + list(range(11835, 11842)))       # 11833, 11834 and 11842 are free


def strip(src):
    """The code: full-line comments and ;* tails removed."""
    out = []
    for ln in src.split("\n"):
        if ln.lstrip().startswith("*"):
            continue
        out.append(re.sub(r"\s*;\*.*$", "", ln))
    return "\n".join(out)


def read(path):
    with open(path, encoding="latin-1") as f:
        return f.read()


def load():
    src = {n: read(os.path.join(GPL, n)) for n in PROGS}
    src["tool_ai"] = read(os.path.join(GPL, "tool_ai"))     # 23 Oct 26, S.69 step 2: the AI page asks for tool.ai.providers and tool.ai.accounts
    src["tool_gates"] = read(os.path.join(GPL, "tool_gates"))     # 24 Oct 26, S.75 A2: the gate matrix asks for tool.gates.matrix
    src["msgs"] = {n: (read(os.path.join(SDSYS, "messages", n)) if os.path.exists(os.path.join(SDSYS, "messages", n)) else None) for n in MSGS}
    for name in sorted(os.listdir(HELP)):
        src["ht." + name] = read(os.path.join(HELP, name))
    return src


def arg_counts(text, name):
    """The number of arguments of each `call <name>(...)` in TEXT: top-level commas + 1, quotes and brackets respected.  A call with the wrong number stops with
    'Argument count mismatch' at run time and no other free check sees it (found 23 Oct 26: three calls of $tk_help had three arguments, not five)."""
    out = []
    for m in re.finditer(r"call\s+" + re.escape(name) + r"\(", text):
        i, depth, n, q = m.end(), 1, 1, ""
        while i < len(text) and depth:
            c = text[i]
            if q:
                q = "" if c == q else q
            elif c in "'\"":
                q = c
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
            elif c == "," and depth == 1:
                n += 1
            i += 1
        out.append(n)
    return out


def docs_pages():
    pages = set()
    for d in ("User", "Administrator", "GettingStarted"):
        p = os.path.join(DOCS, d, "markdown")
        if os.path.isdir(p):
            pages |= {f[:-3] for f in os.listdir(p) if f.endswith(".md")}
    return pages


def checks(s):
    rows = []

    def ck(name, ok, detail=""):
        rows.append((name, bool(ok), detail))

    th, lh, tm, tv, tw, tc = (strip(s[n]) for n in PROGS)
    hts = {k[3:]: v for k, v in s.items() if k.startswith("ht.")}

    ck("P0 the sources were found (the null case: nothing to compare passes every row)", len(th) > 1500 and len(lh) > 2000 and len(tm) > 8000 and len(tv) > 6000 and len(tw) > 300 and len(hts) >= 12, repr((len(th), len(lh), len(tm), len(tv), len(tw), len(hts))))

    i_chars = th.find("if index('abcdefghijklmnopqrstuvwxyz0123456789._-', k[ci, 1], 1) = 0 then ok = 0")
    i_ref = th.find("ans = shared_ref('context.help', 2, @true)")
    i_open = th.find("openpath ans<1> to hf then")
    ck("P1 $tk_help tests the characters of a key (a-z 0-9 . _ -, 1 to 80) BEFORE it asks where the file is, and asks QUIETLY (so SDSYS and an account whose shared.read was withdrawn are answered)",
       0 < i_chars < i_ref < i_open and "len(k) >= 1 and len(k) <= 80" in th, repr((i_chars, i_ref, i_open)))
    ck("P2 ...it only reads: one OPENPATH, no OPENSEQ, WRITE, DELETE or EXECUTE; the caller supplies a key and never a path",
       th.count("openpath") == 1 and not re.search(r"\b(openseq|writeseq|write|delete|clearfile|execute|os\.execute)\b", th) and "pdf " in th, "")
    ck("P3 ...the document it offers is a lower case name from field 2 of the record, and the ONE command it runs is pdf <name> through $tk_run, only when a document is named and the button was chosen",
       "doc = downcase(trim(rec<2>))" in th and th.count("call $tk_run(") == 1 and "call $tk_run('pdf', 'pdf ' : doc, out, st, err)" in th and "if doc # '' and bn = 1 then" in th)
    ck("P4 ...the box has a Close button the Enter key chooses (the Documentation button is the other, never the default), and a session with no terminal gets nothing",
       "btn = '&Documentation,&Close'\n      dflt = 2" in th and "btn = '&Close'\n      dflt = 1" in th and "if system(25) then return" in th)
    ck("P5 ...the [?] button answers a LEFT PRESS on its three cells and nothing else",
       "if a<1> = 'press' and a<2> = 1 and a<4> = c and a<3> >= b and a<3> <= b + 2 then d = 1" in th and "screen text '[?]' at a,b attr 'bold'" in th)
    ck("P6 ...a missing file and a missing record are answered in words (11832, 11831 and the title 11830), not with an error",
       "sysmsg(11830)" in th and "sysmsg(11831, k[1, 60])" in th and "sysmsg(11832)" in th and "have.file" in th)

    i_adm = lh.find("kernel(K$ADMINISTRATOR, -1)")
    i_dir = lh.find("entries = dir(src)")
    i_lt = lh.find("execute 'logto shared' capturing lt")
    ck("P7 LOAD.HELP asks for the administrator before it reads the directory, and enters the shared account only after that",
       0 < i_adm < i_dir < i_lt and "stop sysmsg(2001)" in lh[i_adm:i_adm + 120], repr((i_adm, i_dir, i_lt)))
    execs = re.findall(r"execute\s+('[^']*'(?:\s*:\s*\w+)?)", lh)
    ck("P8 ...the only commands it runs are LOGTO shared, LOGTO back to the account it began in (on every way out), and CREATE.FILE context.help DYNAMIC",
       sorted(set(execs)) == sorted(["'logto shared'", "'logto ' : origin", "'create.file context.help dynamic'"]) and lh.count("execute 'logto ' : origin") >= 3, repr(execs))
    ck("P9 ...a file is a record only if its name is a key (the same characters as $tk_help, the first a letter or digit) and it has a title; the record id is the file name; the only write is that record",
       "keychars = 'abcdefghijklmnopqrstuvwxyz0123456789._-'" in lh and "index('abcdefghijklmnopqrstuvwxyz0123456789', name[1, 1], 1) > 0" in lh and "if rec<1> = '' then" in lh
       and lh.count("write ") == 1 and "write rec to hf, name on error wok = @false" in lh and "if old = rec then" in lh
       and "   if not(ok) then\n      display sysmsg(11840, name, 'not a key')" in lh)
    ck("P10 ...records the administrator added under other ids are kept (the count is made, nothing is deleted)", not re.search(r"\b(delete|clearfile|del)\b", lh.replace("delete.", "")) and "n.kept" in lh)

    # the shipped text
    pages = docs_pages()
    bad_title = [k for k, v in hts.items() if not v.split("\n")[0].strip() or len(v.split("\n")[0]) > 60]
    bad_doc = [k for k, v in hts.items() if v.split("\n")[1:2] and v.split("\n")[1].strip() and not re.fullmatch(r"[a-z0-9._-]+", v.split("\n")[1].strip())]
    bad_name = [k for k in hts if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,79}", k)]
    bad_body = [k for k, v in hts.items() if len([ln for ln in v.split("\n")[2:] if ln.strip()]) < 1 or len(v.split("\n")) > 14 or "\t" in v or any(len(ln) > 1200 for ln in v.split("\n"))]
    ck("P11 every shipped help file has a key for a name, a title of 1 to 60 characters, a document that is blank or a plain name, and one to twelve paragraphs",
       not bad_title and not bad_doc and not bad_name and not bad_body, repr((bad_title, bad_doc, bad_name, bad_body)))
    missing_docs = [k for k, v in hts.items() if len(v.split("\n")) > 1 and v.split("\n")[1].strip() and v.split("\n")[1].strip() not in pages]
    ck("P12 ...and the document each names is a page of the documentation checkout (%s, %d pages; a missing checkout fails this row, it is not skipped)" % (DOCS, len(pages)),
       len(pages) > 50 and not missing_docs, repr(missing_docs))

    # keys asked for by the pages
    tids = re.search(r"tids = ('[a-z]+'(?: : @fm : '[a-z]+')*)", tm)
    tile_ids = re.findall(r"'([a-z]+)'", tids.group(1)) if tids else []
    asked = set(re.findall(r"'(tool\.(?:menus|viewers|ai|gates)\.[a-z-]+)'", tm + "\n" + tv + "\n" + strip(s["tool_ai"]) + "\n" + strip(s["tool_gates"])))
    if "'tool.menus.tile.' : tids<si - 2>" in tm:
        asked |= {"tool.menus.tile." + t for t in tile_ids}
    ck("P13 every key a page asks for has a shipped record (%d keys)" % len(asked), len(asked) >= 13 and not (asked - set(hts)), repr(sorted(asked - set(hts))))
    ck("P14 ...and every shipped record is asked for by a page (so text does not rot)", not (set(hts) - asked), repr(sorted(set(hts) - asked)))

    # the pages
    ck("P15 tool.menus: a [?] on each of the nine rows of the Menu box (inside the row loop), one at the system default and one at the Accounts list",
       "call $tk_help('mark', 134, 1 + r, 0, 0)" in tm and "call $tk_help('mark', 66, 32, 0, 0)" in tm and "call $tk_help('mark', 66, 2, 0, 0)" in tm and "width 59\n      call $tk_help('mark'" in tm)
    ck("P16 ...F1 and ? show the help of the selected row (the key by pane and row), and a left press on a [?] selects its row, then shows it; the loop variable of the click is not the drawing routines'",
       "case nm = 'f1' or nm = '?'" in tm and "call $tk_help('box', hk, hm, 0, 0)" in tm and "call $tk_help('hit', mev, 134, 1 + hr, hit.now)" in tm and "for hr = 1 to 9" in tm
       and "call $tk_help('hit', mev, 66, 32, hit.default)" in tm and "call $tk_help('hit', mev, 66, 2, hit.accounts)" in tm and "hk = 'tool.menus.tile.' : tids<si - 2>" in tm)
    ck("P17 tool.viewers: a [?] on each box, F1 and ? and a click show their help, and the page runs only set.viewer",
       "call $tk_help('mark', 66, 2, 0, 0)" in tv and "call $tk_help('mark', 134, 2, 0, 0)" in tv and "case nm = 'f1' or nm = '?'" in tv and "call $tk_help('hit', mev, 66, 2, hit.allowed)" in tv
       and "call $tk_help('hit', mev, 134, 2, hit.found)" in tv and "allow = 'set.viewer'" in tv and "tool.viewers.allowed" in tv and "tool.viewers.found" in tv)

    tg = strip(s["tool_gates"])
    ck("P17b tool.gates: a [?] at the end of the matrix box, F1 and ? and a click show its help, and the page runs only modify.account",
       "call $tk_help('mark', 134, 2, 0, 0)" in tg and "case nm = 'f1' or nm = '?'\n         call $tk_help('box', 'tool.gates.matrix', hm, 0, 0)" in tg and "call $tk_help('hit', mev, 134, 2, hit.m)" in tg
       and "allow = 'modify.account'" in tg and tg.count("allow = ") == 1 and "tool.gates.matrix" in hts and "call $tk_wrap(lines<wi>, 134, pieces)" in tg and "rest[cut" not in tg)

    # one wrapping loop
    ck("P18 the wrapping loop is $tk_wrap and nowhere else: $tk_confirm, tool.menus and tool.viewers call it and none has the loop (a SCREEN TEXT longer than its width is cut, not wrapped)",
       "rest[cut, 1] # ' '" in tw and "call $tk_wrap(sentence, wrapw, pieces)" in tc and "call $tk_wrap(lines<wi>, 63, pieces)" in tm and "call $tk_wrap(lines<wi>, 134, pieces)" in tv
       and "rest[cut" not in tc and "rest[cut" not in tm and "rest[cut" not in tv and "wl[wp" not in tm)

    every = th + "\n" + lh + "\n" + tm + "\n" + tv + "\n" + tw + "\n" + tc + "\n" + tg
    want = {"$tk_help": 5, "$tk_wrap": 3, "!viewlist": 4, "$tk_run": 5, "$tk_confirm": 5}
    wrong = {k: [n for n in arg_counts(every, k) if n != v] for k, v in want.items()}
    seen = {k: len(arg_counts(every, k)) for k in want}
    ck("P20 every call of $tk_help (5 arguments), $tk_wrap (3), !viewlist (4), $tk_run (5) and $tk_confirm (5) has the number of arguments the subroutine takes (the null case: each is called at least once)",
       not any(wrong.values()) and seen["$tk_help"] >= 12 and seen["$tk_wrap"] >= 3 and seen["!viewlist"] >= 3 and seen["$tk_run"] >= 2 and seen["$tk_confirm"] >= 2, repr((wrong, seen)))

    m = s["msgs"]
    ck("P19 messages 11830 to 11832 and 11835 to 11841 exist, each one line, none with a capital command word",
       all(m[n] and m[n].count("\n") == 1 for n in MSGS) and "load.help" in (m["11832"] or "") and "context.help" in (m["11831"] or ""), repr([n for n in MSGS if not m[n] or m[n].count("\n") != 1]))
    return rows


MUTANTS = [
    ("tk_help looks up a key before testing its characters", "tk_help", "      for ci = 1 to len(k)\n         if index('abcdefghijklmnopqrstuvwxyz0123456789._-', k[ci, 1], 1) = 0 then ok = 0\n      next ci\n", ""),
    ("tk_help allows a longer key", "tk_help", "len(k) >= 1 and len(k) <= 80", "len(k) >= 1"),
    ("tk_help asks the gates (not quiet)", "tk_help", "shared_ref('context.help', 2, @true)", "shared_ref('context.help', 2, @false)"),
    ("tk_help opens another file than the one found", "tk_help", "openpath ans<1> to hf then", "openpath 'context.help' to hf then"),
    ("tk_help writes", "tk_help", "            read rec from hf, k else rec = ''\n", "            read rec from hf, k else rec = ''\n            write rec to hf, k\n"),
    ("tk_help takes the document name as it is", "tk_help", "doc = downcase(trim(rec<2>))", "doc = rec<2>"),
    ("the Documentation button is the default", "tk_help", "      btn = '&Documentation,&Close'\n      dflt = 2", "      btn = '&Documentation,&Close'\n      dflt = 1"),
    ("the box runs a command of the record", "tk_help", "call $tk_run('pdf', 'pdf ' : doc, out, st, err)", "call $tk_run('pdf', doc, out, st, err)"),
    ("the box runs pdf with no button", "tk_help", "if doc # '' and bn = 1 then", "if doc # '' then"),
    ("a click anywhere on the row counts", "tk_help", "a<4> = c and a<3> >= b and a<3> <= b + 2", "a<4> = c"),
    ("a release counts as a press", "tk_help", "if a<1> = 'press' and a<2> = 1 and", "if a<2> = 1 and"),
    ("a session with no terminal is shown a box", "tk_help", "   if system(25) then return\n   gosub lookup", "   gosub lookup"),
    ("a missing record is an error", "tk_help", "      lines = (if have.file or not(ok) then sysmsg(11831, k[1, 60]) else sysmsg(11832))", "      lines = ''"),
    ("LOAD.HELP does not ask for the administrator", "loadhelp", "   if not(kernel(K$ADMINISTRATOR, -1)) then\n      stop sysmsg(2001) ;* Command requires administrator privileges\n   end\n", ""),
    ("LOAD.HELP enters another account", "loadhelp", "execute 'logto shared' capturing lt", "execute 'logto sdsys' capturing lt"),
    ("LOAD.HELP stays in the shared account", "loadhelp", "   execute 'logto ' : origin capturing lt\n   void kernel(K$AUDIT,", "   void kernel(K$AUDIT,"),
    ("LOAD.HELP runs another command", "loadhelp", "execute 'create.file context.help dynamic' capturing mk", "execute 'create.file context.help dynamic' capturing mk\n      execute 'sh' capturing mk"),
    ("LOAD.HELP loads a file whose name is not a key", "loadhelp", "   if not(ok) then\n      display sysmsg(11840, name, 'not a key')", "   if @false then\n      display sysmsg(11840, name, 'not a key')"),
    ("LOAD.HELP loads a record with no title", "loadhelp", "   if rec<1> = '' then\n", "   if @false then\n"),
    ("LOAD.HELP writes every time", "loadhelp", "      if old = rec then\n         n.same += 1\n         return\n      end\n", ""),
    ("LOAD.HELP writes another record", "loadhelp", "write rec to hf, name on error wok = @false", "write rec to hf, 'x' on error wok = @false"),
    ("LOAD.HELP deletes the administrator's records", "loadhelp", "      locate rid in shipped<1> setting p else n.kept += 1", "      locate rid in shipped<1> setting p else delete hf, rid"),
    ("tool.menus loses a [?] on the Menu rows", "tool_menus", "      call $tk_help('mark', 134, 1 + r, 0, 0)", "      null"),
    ("tool.menus calls $tk_help with too few arguments (a runtime stop in SD BASIC)", "tool_menus", "call $tk_help('mark', 66, 32, 0, 0)", "call $tk_help('mark', 66, 32)"),
    ("tool.viewers calls $tk_help with too few arguments", "tool_viewers", "hm, 0, 0)", "hm)"),
    ("tool.viewers calls $tk_wrap with too many arguments", "tool_viewers", "call $tk_wrap(lines<wi>, 134, pieces)", "call $tk_wrap(lines<wi>, 134, pieces, 0)"),
    ("tool.menus loses F1", "tool_menus", "      case nm = 'f1' or nm = '?'\n         gosub help.here\n", ""),
    ("tool.menus loses the click", "tool_menus", "call $tk_help('hit', mev, 134, 1 + hr, hit.now)", "hit.now = 0"),
    ("tool.menus uses the drawing loop variable for the click", "tool_menus", "for hr = 1 to 9", "for r = 1 to 9"),
    ("tool.menus asks for a tile's help with the wrong index", "tool_menus", "hk = 'tool.menus.tile.' : tids<si - 2>", "hk = 'tool.menus.tile.' : tids<si>"),
    ("tool.menus has its own wrapping loop again", "tool_menus", "call $tk_wrap(lines<wi>, 63, pieces)", "rest[cut"),
    ("$tk_confirm has its own wrapping loop again", "tk_confirm", "call $tk_wrap(sentence, wrapw, pieces)", "rest[cut"),
    ("$tk_wrap cuts a word at the wrong place", "tk_wrap", "rest[cut, 1] # ' '", "rest[cut, 1] # 'x'"),
    ("tool.viewers can run another command", "tool_viewers", "allow = 'set.viewer'", "allow = 'set.viewer sh'"),
    ("tool.viewers loses a [?]", "tool_viewers", "   call $tk_help('mark', 134, 2, 0, 0)\n", ""),
    ("tool.gates loses its [?]", "tool_gates", "   call $tk_help('mark', 134, 2, 0, 0)\n", ""),
    ("tool.gates calls $tk_help with too few arguments", "tool_gates", "      case nm = 'f1' or nm = '?'\n         call $tk_help('box', 'tool.gates.matrix', hm, 0, 0)", "      case nm = 'f1' or nm = '?'\n         call $tk_help('box', 'tool.gates.matrix', hm)"),
    ("tool.gates loses the click", "tool_gates", "call $tk_help('hit', mev, 134, 2, hit.m)", "hit.m = 0"),
    ("tool.gates can run another command", "tool_gates", "allow = 'modify.account'", "allow = 'modify.account sh'"),
    ("tool.gates has its own wrapping loop again", "tool_gates", "call $tk_wrap(lines<wi>, 134, pieces)", "rest[cut"),
    ("a help record names a page that is not there", "ht.tool.menus.pins", "01-accounts-and-security", "no-such-page"),
    ("a help record has no title", "ht.tool.menus.pins", "Programs of the account's own\n", "\n"),
    ("a help record has a tab in it", "ht.tool.menus.default", "Applies to every account", "\tApplies to every account"),
    ("a help record's document name has a slash", "ht.tool.menus.pins", "01-accounts-and-security", "../accounts"),
]


def selftest():
    s = load()
    base = [n for n, ok, _ in checks(s) if not ok]
    if base:
        print("REFUSING - the unmutated source already fails: %s" % ", ".join(base), file=sys.stderr)
        return 2
    holes = 0
    print("--- self-test: the unmutated source passes; each mutation must be CAUGHT and match its text once ---")
    for name, which, old, new in MUTANTS:
        if s[which].count(old) != 1:
            print("  [FAIL] %s: the text to mutate matches %d times in %s, not once" % (name, s[which].count(old), which))
            holes += 1
            continue
        s2 = dict(s)
        s2[which] = s[which].replace(old, new)
        caught = [n for n, ok, _ in checks(s2) if not ok]
        if caught:
            print("  [pass] %s: caught by %s" % (name, ", ".join(caught[:3])))
        else:
            print("  [FAIL] %s: NOT CAUGHT by any check" % name)
            holes += 1
    print("self-test: %d mutants, %d not caught" % (len(MUTANTS), holes))
    return 1 if holes else 0


def main():
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    if not os.path.isdir(HELP):
        print("test-help-units: no helptext directory at %s" % HELP, file=sys.stderr)
        sys.exit(2)
    s = load()
    rows = checks(s)
    bad = 0
    for name, ok, detail in rows:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, ("   <- " + detail) if (detail and not ok) else ""))
        bad += 0 if ok else 1
    print("test-help-units: %d checks, %d failed" % (len(rows), bad))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
