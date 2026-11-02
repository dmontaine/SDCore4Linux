#!/usr/bin/env python3
"""test-toolentries-units.py - TOOL.ENTRIES, the master files page (S.96 M1a), as invariants read off the source.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-toolentries-units.py
  python3 .../test-toolentries-units.py --selftest

No sudo, no install, no sd.  Exit 0 all checks passed, 1 a check failed, 2 it could not run.  Written 3 Nov 26.

***WHAT THIS IS AND WHAT IT IS NOT.*** It reads sdsys/gpl.bp/tool_entries, the VOC record and the two help records as TEXT.  IT CANNOT SAY THE PAGE SHOWS THE RIGHT GATES OR THE RIGHT
ENTRIES: that is sandbox-tool-entries.py.  What it holds is the shape the design depends on and a hand edit could break unnoticed: the page is the administrator's and asks for that
first; it is READ ONLY (no write, delete, execute, command, confirm box or master-file operation anywhere in it); the only files it opens are the register and, by the pathname the
register gives, an account's VOC; an account's VOC is read when the cursor comes to it and every VOC is read only by the find the person asks for; the gates are the three register
fields in the order v d b; SDSYS is not in the list; the long lists are cut at MAXV.

***AND THE CHECKS ARE THEMSELVES CHECKED.*** --selftest makes the changes that would plausibly break the page and requires each to be CAUGHT.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.abspath(os.path.join(HERE, os.pardir))
PAGE = os.path.join(SD64, "sdsys", "gpl.bp", "tool_entries")
VOCREC = os.path.join(SD64, "sdsys", "voc_template", "tool.entries")
HELP = os.path.join(SD64, "sdsys", "helptext")
REGRESS = os.path.join(HERE, "regress.sh")
RMAP = os.path.join(HERE, "regress-map.txt")


def code(src):
    out = []
    for i, line in enumerate(src.splitlines(), 1):
        s = line.strip()
        if s and not s.startswith("*"):
            cut = s.find(";*")
            out.append((i, (s[:cut] if cut >= 0 else s).rstrip()))
    return out


def unquote(s):
    """The line with the inside of its string literals taken out: the prose a page shows says 'write' and 'modify.account' and must not be read as code."""
    out, q = [], ""
    for ch in s:
        if q:
            if ch == q:
                q = ""
                out.append(ch)
        elif ch in "'\"":
            q = ch
            out.append(ch)
        else:
            out.append(ch)
    return "".join(out)


def section(lines, start, end):
    a = next((n for n, s in lines if s.startswith(start)), None)
    if a is None:
        return []
    b = next((n for n, s in lines if n > a and s.startswith(end)), None)
    return [(n, s) for n, s in lines if n >= a and (b is None or n < b)]


def checks(src, voc, helps):
    out = []

    def ck(name, ok, detail=""):
        out.append((name, bool(ok), detail))

    lines = code(src)
    txt = "\n".join(s for n, s in lines)
    ck("T1 NULL CASE: the page, its VOC record and both help records are there and not empty", len(lines) > 300 and voc and all(helps.values()), "%d lines" % len(lines))
    ck("T2 the VOC record is V / CA / $tool_entries (SDSYS's template only) and the page is internal and catalogued as $tool_entries",
       voc == "V\nCA\n$tool_entries\n" and "program $tool_entries" in txt and "$catalog $tool_entries" in txt and txt.count("$internal") == 1)
    first_open = next((n for n, s in lines if re.search(r"\bopenpath\b", s)), 10 ** 9)
    adm = next((n for n, s in lines if "call $tk_open('tool.entries', 'admin', ctx, err)" in s), None)
    refused = next((n for n, s in lines if n > (adm or 0) and s == "stop"), None)
    ck("T3 it opens the toolkit for the ADMINISTRATOR first and stops on a refusal, before any file is opened",
       adm is not None and refused is not None and adm < refused < first_open, "admin %s stop %s first openpath %s" % (adm, refused, first_open))
    forbidden = [(n, s) for n, s in lines if re.search(r"(^|[\s;(])(write|writev|writeu|delete|deletes|execute|chain|perform|osexecute|os\.execute)\s", unquote(s) + " ")
                 or re.search(r"\$tk_run|\$tk_confirm|K\$MASTERS|!acc_|sd-elevate|modify\.account|set\.batch|run\.in", unquote(s))]
    ck("T4 READ ONLY: no write, delete, execute, command runner, confirm box, master-file operation or account verb anywhere in the page", not forbidden, "%s" % forbidden[:3])
    opens = [s for n, s in lines if re.search(r"\bopenpath\b", s)]
    kinds = sorted(set("register" if "@sdsys:@ds:'accounts'" in s else ("voc" if re.search(r"apath<[a-z0-9]+>:@ds:'voc'", s) else s) for s in opens))
    ck("T5 the only files it opens are the register and an account's VOC by the pathname the register gives (four opens: the list, the entries, the find, the entry under the cursor)",
       kinds == ["register", "voc"] and len(opens) == 4 and txt.count("close ") >= 4, "%s %d" % (kinds, len(opens)))
    ra = section(lines, "read.all:", "read.entries:")
    find_opens = [n for n, s in lines if "for a = 1 to an" in s]
    rf = section(lines, "run.find:", "classify:")
    ck("T6 LAZY: read.all reads the VOC of the selected account only (one gosub read.entries) and runs the find only when a find is set; the loop over every account is in run.find alone",
       "\n".join(s for n, s in ra).count("gosub read.entries") == 1 and any(s == "if fnd # '' then gosub run.find" for n, s in ra)
       and len(find_opens) == 1 and rf and rf[0][0] < find_opens[0] and txt.count("gosub run.find") == 2 and "gosub run.find" in "\n".join(s for n, s in section(lines, "do.find:", "on.mouse:")),
       "calls of run.find: %d" % txt.count("gosub run.find"))
    ck("T7 SDSYS is not in the list; the gates are the register's voc-edit, dict-edit, bp-edit in the order v d b (each 'YES' after trim and upcase); the sdsys column asks is_grp_member only for a group",
       "if id # 'sdsys' then" in txt
       and re.search(r"gset = \(if upcase\(trim\(arec<ACC\$VOC\.EDIT>\)\) = 'YES' then 'v' else '-'\)\s+gset := \(if upcase\(trim\(arec<ACC\$DICT\.EDIT>\)\) = 'YES' then 'd' else '-'\)\s+gset := \(if upcase\(trim\(arec<ACC\$BP\.EDIT>\)\) = 'YES' then 'b' else '-'\)", txt)
       and "if trim(arec<ACC$GROUP>) # '' then" in txt and "is_grp_member('sdsys', trim(arec<ACC$GROUP>))" in txt)
    ck("T8 both long reads are cut at MAXV (the entries and the hits) and the page says so", txt.count(">= MAXV") == 2 and txt.count("only the first ' : MAXV : ' are listed") == 3)       # the entries' foot, the hits' foot and the status line of a find
    ck("T9 the filter and the find ask with screen ask, take the AI's argument as the default, and each clears the other",
       txt.count("screen ask '") == 2 and txt.count("value ai.arg") == 2 and "filt = trim(ft)\nfnd = ''" in txt and "fnd = trim(ft)\nfilt = ''" in txt)
    keyrows = re.findall(r"call \$tk_keys\('add', keys, '([^']+)'", txt)
    ck("T10 eight key rows: f1 enter tab / f f5 ctrl-q esc, and the AI is offered only what changes what is shown (pane filter find refresh)",
       keyrows == ["f1", "enter", "tab", "/", "f", "f5", "ctrl-q", "esc"] and re.findall(r"call \$tk_keys\('ai', keys, '([^']+)'", txt) == ["pane", "filter", "find", "refresh"], "%s" % keyrows)
    ck("T11 four panes declared once (accounts, entries, means, help), the two lists named as the boxes that take the focus, and each list has its [?]",
       txt.count("call $tk_layout('declare'") == 1 and all(("d<%d> = '%s'" % (i + 1, nm)) in txt for i, nm in enumerate(("accounts", "entries", "means", "help")))
       and "ctx<TK.C.FOCI> = 'accounts' : @sm : 'Accounts' : @vm : 'entries' : @sm : 'Entries'" in txt and txt.count("call $tk_help('mark'") == 2)
    asked = sorted(set(re.findall(r"'(tool\.entries\.[a-z]+)'", txt)))
    ck("T12 the help keys the page asks for (tool.entries.accounts and .entries) are the two shipped records, each with a title, a document that exists in the administrator guide and a body",
       asked == ["tool.entries.accounts", "tool.entries.entries"] and all(len(helps[k].split("\n")) >= 3 and helps[k].split("\n")[1] == "19-the-master-files" for k in asked), "%s" % asked)
    with open(REGRESS) as f:
        suites = re.search(r'^ALL_SUITES="([^"]*)"', f.read(), re.M)
    with open(RMAP) as f:
        rmap = f.read()
    ck("T13 the suite is registered (ALL_SUITES) and the map selects it for the page, the VOC record, the help records and the suite itself",
       bool(suites) and "tool-entries" in suites.group(1).split() and re.search(r"^sdsys/gpl\.bp/tool_entries\s*:\s*tool-entries", rmap, re.M) is not None
       and re.search(r"^sdsys/voc_template/tool\.entries\s*:\s*tool-entries", rmap, re.M) is not None and re.search(r"^sdsys/helptext/tool\.entries\.\*\s*:.*tool-entries", rmap, re.M) is not None
       and re.search(r"^gplbld/sandbox-tool-entries\.py\s*:\s*@self", rmap, re.M) is not None)
    return out


def load():
    with open(PAGE, encoding="utf-8", errors="replace") as f:
        src = f.read()
    with open(VOCREC, encoding="utf-8") as f:
        voc = f.read()
    helps = {}
    for k in ("tool.entries.accounts", "tool.entries.entries"):
        p = os.path.join(HELP, k)
        helps[k] = open(p, encoding="utf-8").read() if os.path.isfile(p) else ""
    return src, voc, helps


MUTANTS = [
    ("the page writes", "src", "            eall += 1\n", "            eall += 1\n            delete vf, id\n"),
    ("the page runs a command", "src", "   void kernel(K$AUDIT, 'tool start app=tool.entries')\n", "   void kernel(K$AUDIT, 'tool start app=tool.entries')\n   execute 'x'\n"),
    ("the page is not the administrator's", "src", "call $tk_open('tool.entries', 'admin', ctx, err)", "call $tk_open('tool.entries', '', ctx, err)"),
    ("the find runs at the start", "src", "   if fnd # '' then gosub run.find\n", "   gosub run.find\n"),
    ("the dict gate reads the programs field", "src", "gset := (if upcase(trim(arec<ACC$DICT.EDIT>)) = 'YES' then 'd' else '-')", "gset := (if upcase(trim(arec<ACC$BP.EDIT>)) = 'YES' then 'd' else '-')"),
    ("SDSYS is listed", "src", "         if id # 'sdsys' then", "         if id # '' then"),
    ("the find is not cut", "src", "               if hn >= MAXV then", "               if 0 then"),
    ("another key row", "src", "   call $tk_keys('add', keys, 'f5', 'refresh', 'refresh', '', 1)\n", "   call $tk_keys('add', keys, 'f5', 'refresh', 'refresh', '', 1)\n   call $tk_keys('add', keys, 'e', 'edit', 'edit', '', 1)\n"),
    ("a third file is opened", "src", "   openpath @sdsys:@ds:'accounts' to acc.f then\n", "   openpath @sdsys:@ds:'batch.jobs' to bj.f then\n      close bj.f\n   end\n   openpath @sdsys:@ds:'accounts' to acc.f then\n"),
    ("the voc record is in newvoc form", "voc", "V\nCA\n$tool_entries\n", "V\nCA\n$tool_jobs\n"),
    ("a help record loses its document", "help", "19-the-master-files", "00-nothing"),
]


def selftest():
    src, voc, helps = load()
    if any(not ok for _, ok, _ in checks(src, voc, helps)):
        print("selftest: the unmutated source already fails; fix that first")
        return 1
    missed = 0
    for name, kind, old, new in MUTANTS:
        s, v, h = src, voc, dict(helps)
        if kind == "src":
            if s.count(old) != 1:
                print("  [CANNOT] %-48s the text occurs %d times" % (name, s.count(old)))
                missed += 1
                continue
            s = s.replace(old, new)
        elif kind == "voc":
            v = v.replace(old, new)
        else:
            h["tool.entries.accounts"] = h["tool.entries.accounts"].replace(old, new)
        caught = [n for n, ok, _ in checks(s, v, h) if not ok]
        if caught:
            print("  [caught] %-48s by %s" % (name, ", ".join(c.split()[0] for c in caught[:4])))
        else:
            print("  [MISSED] %-48s" % name)
            missed += 1
    print("selftest: %d mutants, %d missed or not applied" % (len(MUTANTS), missed))
    return 0 if missed == 0 else 1


def main():
    if "--selftest" in sys.argv:
        return selftest()
    try:
        src, voc, helps = load()
    except OSError as e:
        print("cannot read the source: %s" % e)
        return 2
    res = checks(src, voc, helps)
    failed = 0
    for name, ok, detail in res:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, "" if ok else "   <- " + detail))
        failed += 0 if ok else 1
    print("test-toolentries-units: %d checks, %d failed" % (len(res), failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
