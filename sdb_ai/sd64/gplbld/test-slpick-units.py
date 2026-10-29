#!/usr/bin/env python3
"""test-slpick-units.py - the action palette, the record picker and $sl_pickwin's optional arguments (S.88 3.10A), read off the source as text.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-slpick-units.py
  python3 .../test-slpick-units.py --selftest

No sudo, no install, no sd.  Exit 0 every check passed, 1 a check failed, 2 it could not run.  Written 29 Oct 2026.

WHAT IT HOLDS: $sl_pickwin takes two OPTIONAL trailing arguments (hot, filtout; var.args as $sl_guard does) and the four 8-argument callers in tool_tktest are
still valid; a hot key ends the window with status 2 and the key's name and is tested before the other keys; the filter text is handed back whatever ended the
window.  $sl_palette flattens the menus array (separators out, & stripped, submenus to a depth of three, the flag D and the reason in subvalue 5), calls only
$sl_pickwin, and is ADVISORY (owner's answer 25, 29 Oct): it runs nothing, it opens and writes nothing, and the code reaches ret ONLY in the branch where the
entry is not disabled.  $sl_picker lists the files with the IDE's own filter, opens the chosen file for reading only, goes back to the files on Esc, and answers
'new' on Ctrl-N with the typed text; it never writes.  The messages 11171-11175 exist and the programs cite no other new number.

***IT READS SOURCE AS TEXT AND RUNS NOTHING***: that the windows draw and the keys do what is said is a sandbox suite's job (tk-widgets), not run yet.

--selftest runs every check on the real files and then on a copy with one deliberate fault at a time: each must make a check fail.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.normpath(os.path.join(HERE, ".."))
SDSYS = os.path.join(SD64, "sdsys")
BP = os.path.join(SDSYS, "gpl.bp")
MSG = os.path.join(SDSYS, "messages")
NEEDED = ["sl_pickwin", "sl_palette", "sl_picker", "ide"]
OPTIONAL = ["tool_tktest"]
MSGS = [11171, 11172, 11173, 11174, 11175]
REGRESS = os.path.join(HERE, "regress.sh")
MAP = os.path.join(HERE, "regress-map.txt")


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


def squeeze(t):
    return re.sub(r"\s+", " ", t).strip()


def ordered(text, *needles):
    pos = -1
    for n in needles:
        p = text.find(n, pos + 1)
        if p < 0:
            return False
        pos = p
    return True


def call_args(text, head):
    """the number of top-level arguments of every call that begins with head, quotes and brackets respected"""
    counts = []
    pos = 0
    while True:
        p = text.find(head, pos)
        if p < 0:
            return counts
        i = p + len(head)
        depth, q, n = 1, "", 1
        while i < len(text) and depth:
            c = text[i]
            if q:
                if c == q:
                    q = ""
            elif c in "'\"":
                q = c
            elif c in "([":
                depth += 1
            elif c in ")]":
                depth -= 1
            elif c == "," and depth == 1:
                n += 1
            i += 1
        counts.append(n)
        pos = i


def line_no(text, needle):
    p = text.find(needle)
    return text.count("\n", 0, p) + 1 if p >= 0 else -1


def checks(raw):
    code = {n: strip_bas(raw[n]) for n in NEEDED + OPTIONAL if n in raw}
    sq = {n: squeeze(c) for n, c in code.items()}
    out = []

    def add(i, what, ok, detail=""):
        out.append((i, what, bool(ok), detail))

    add("Q0", "NULL CASE: every program was found and none is trivially short (a check on nothing would pass)", all(len(raw[n]) > 300 for n in NEEDED),
        ", ".join("%s %d" % (n, len(raw[n])) for n in NEEDED))
    pw, pa, pk, ide = sq["sl_pickwin"], sq["sl_palette"], sq["sl_picker"], sq["ide"]

    # ---- $sl_pickwin ----
    add("Q1", "$sl_pickwin: the two trailing arguments are optional (var.args); hot is read only when it was given; filtout is cleared before the phantom return and "
        "set from the filter after the window is put back; an 8-argument call is still valid",
        "subroutine sl_pickwin(items, title, multi, default, ret, status, src, opts, hot, filtout) var.args" in pw
        and "if not(unassigned(hot)) then hotl = hot" in pw and pw.count("unassigned(") == 1
        and ordered(pw, "filtout = ''", "if system(25) then return")
        and ordered(pw, "call $sl_region('restore'", "call $sl_scr('put', scr)", "if st = 'hot' then status = 2", "filtout = filt")
        and pw.count("filtout =") == 2, "")
    add("Q2", "$sl_pickwin: a hot key is tested after the mouse and the resize and before every other key, answers the key's name, ends the window as 'hot' and gives status 2; "
        "the loop ends on it",
        ordered(pw, "case k = 'mouse'", "case k = 'resize'", "case hotl # '' and index(@vm : hotl : @vm, @vm : k : @vm, 1) > 0 ret = k st = 'hot' case k = 'esc'")
        and "until st = 'done' or st = 'cancel' or st = 'hot'" in pw and pw.count("st = 'hot'") == 3 + 0 and "status = 2" in pw, "")
    if "tool_tktest" in raw:
        cnt = call_args(code["tool_tktest"], "call $sl_pickwin(")
        add("Q3", "the %d calls of $sl_pickwin in tool_tktest still give 8 arguments" % len(cnt), len(cnt) >= 4 and all(c == 8 for c in cnt), repr(cnt))
    pal_calls = call_args(code["sl_palette"], "call $sl_pickwin(")
    pick_calls = call_args(code["sl_picker"], "call $sl_pickwin(")
    add("Q4", "the palette gives $sl_pickwin 8 arguments and the picker 8 (stage 1) and 10 (stage 2, with the hot key and the filter text)", pal_calls == [8] and pick_calls == [8, 10], "%r %r" % (pal_calls, pick_calls))

    # ---- $sl_palette ----
    add("Q5", "$sl_palette: internal, catalogued under its own name, a session with no terminal returns at once with status 1 and nothing chosen, and the first thing it does "
        "is give its answers a value",
        ordered(pa, "$internal subroutine sl_palette(menus, title, ret, status, reason) $catalog $sl_palette", "ret = '' status = 1 reason = '' if system(25) then return"), "")
    add("Q6", "$sl_palette is ADVISORY: it calls only $sl_pickwin, runs, writes, locks and opens nothing, and reads nothing from disk",
        re.findall(r"call (\$\w+)\(", code["sl_palette"]) == ["$sl_pickwin"]
        and not re.search(r"\b(execute|perform|write|writev|readu|readv|read|delete|openpath|open|openseq|kernel|os\.execute|crt|display|screen|chain|oscopy)\b",
                          re.sub(r"'[^']*'", "''", code["sl_palette"])), "")
    add("Q7", "$sl_palette: the code reaches ret in ONE place, the branch where the entry is not disabled; a disabled entry gets status 2, no code, and its reason (else message 11175)",
        pa.count("ret = codes<pr>") == 1 and pa.count("ret =") == 2
        and ordered(pa, "if dis<pr> then status = 2", "reason = why<pr>", "if reason = '' then reason = sysmsg(11175)", "end else ret = codes<pr> status = 0 end")
        and "if ps # 0 then return" in pa and ordered(pa, "if ps # 0 then return", "if dis<pr> then"), "")
    add("Q8", "$sl_palette flattens the menus as the bar reads them: separators and empty labels are left out, & is stripped, the reason is subvalue 5, the flag D (any case) makes "
        "an entry disabled and marks it (11174), a submenu is the menu whose title is the item's code and is followed to a depth of three, and nothing is listed twice by a cycle",
        "if label = '-' or label = '' then continue" in pa and "change(label, '&', '')" in pa and "change(menus<m, 1>, '&', '')" in pa and "why<n> = menus<m, v, 5>" in pa
        and "index(upcase(menus<m, v, 4>), 'D', 1) > 0" in pa and "sysmsg(11174)" in pa
        and "equate PAL.DEPTH to 3" in pa and "if code[1, 1] = '>' then if depth < PAL.DEPTH then" in pa and "if menus<s, 1> = code then" in pa and "depth + 1" in pa
        and "if menus<m, 1>[1, 1] # '>' then" in pa and "dis<n> = (if isdis then 1 else 0)" in pa, "")
    add("Q9", "$sl_palette: the pick window gets the entry's NAME 'Menu > Label', its shortcut, and the reason or the label as help; the answer is the number in the list (pr), "
        "mapped back to the code by the list's own array",
        "items<n, 1> = prefix : plain" in pa and "items<n, 2> = shortcut" in pa and "items<n, 3> = (if menus<m, v, 5> # '' then menus<m, v, 5> else plain)" in pa
        and "codes<n> = code" in pa and "' > '" in pa and "if n = 0 then return" in pa, "")

    # ---- $sl_picker ----
    add("Q10", "$sl_picker: internal, catalogued, a session with no terminal returns 'cancel' with nothing chosen",
        ordered(pk, "$internal subroutine sl_picker(mode, file, id, res, newtext) $catalog $sl_picker", "res = 'cancel' id = '' newtext = '' if system(25) then return"), "")
    ide_line = "if (t1 = 'F' or t1[1, 5] = 'FILE ') and ids<i>[1, 1] # '$' then fl<-1> = ids<i>"
    add("Q11", "$sl_picker lists the files with the IDE's own filter (type F or 'FILE ', no '$'), from the VOC, and asks nothing else of the disk",
        ide_line in ide and ide_line in pk and "open 'VOC' to vocf then" in pk and "sselect vocf to 9" in pk, "")
    add("Q12", "$sl_picker is READ ONLY: it never writes, deletes, locks or runs, the record file is opened once and closed, and the record list is the paged source "
        "(the open file, never an empty string tested as a file variable)",
        not re.search(r"\b(execute|perform|write|writev|writeu|readu|delete|openpath|openseq|kernel|os\.execute|crt|display|screen|oscopy|clearfile|chain)\b",
                      re.sub(r"'[^']*'", "''", code["sl_picker"]))
        and pk.count("open file to fv else return") == 1 and pk.count("close fv") == 1 and "src #" not in pk and "src#" not in pk
        and "call $sl_pickwin('', sysmsg(11172, file), 0, 0, pr, ps, fv, '0' : @fm : 200 : @fm : 100000 : @fm : 20000, 'ctrl-n', typed)" in pk, "")
    add("Q13", "$sl_picker: Ctrl-N answers 'new' with what was typed and no id; Enter answers 'ok' with the record id as stored; Esc in the records goes back to the files "
        "(and ends the picker in mode 'record'); Esc in the files cancels; mode 'file' stops after the file",
        ordered(pk, "case ps = 0 id = pr res = 'ok' return", "case ps = 2 newtext = typed res = 'new' return", "case mode = 'record' return", "case 1 stage = 1")
        and "if ps # 0 then return file = fl<pr, 1>" in pk and "if mode = 'file' then res = 'ok' return end stage = 2" in pk and "if mode = 'record' then stage = 2" in pk
        and pk.count("res = 'ok'") == 2 and pk.count("res = 'new'") == 1 and "if fl = '' then return" in pk, "")

    # ---- messages ----
    miss = [m for m in MSGS if ("msg%d" % m) not in raw]
    add("Q14", "messages 11171-11175 exist, one plain line each, 11172 takes the file name, and no program of this step cites another new number in the block",
        not miss and "%1" in raw["msg11172"] and all(raw["msg%d" % m].strip() and raw["msg%d" % m].count("\n") == 1 for m in MSGS)
        and all(int(x) in MSGS or int(x) not in range(11171, 11179)
                for n in ("sl_palette", "sl_picker", "sl_pickwin") for x in re.findall(r"sysmsg\((\d+)", code[n])), ", ".join(map(str, miss)))
    cited = set(int(x) for n in ("sl_palette", "sl_picker") for x in re.findall(r"sysmsg\((\d+)", code[n]))
    add("Q15", "every message 11171-11175 is cited by the palette or the picker (none left over)", set(MSGS) == cited, "cited %s" % sorted(cited))

    # ---- wiring ----
    rs, mp = raw["regress.sh"], raw["regress-map.txt"]
    suites = re.search(r'^ALL_SUITES="([^"]*)"', rs, re.M)
    add("Q16", "wiring: the tk-widgets suite is in ALL_SUITES; the map has rules for sl_palette and sl_picker before the coarse sl_* line and the message rule before the 117* line",
        suites is not None and "tk-widgets" in suites.group(1).split()
        and 0 < line_no(mp, "sdsys/gpl.bp/sl_palette") < line_no(mp, "sdsys/gpl.bp/sl_*            :")
        and 0 < line_no(mp, "sdsys/gpl.bp/sl_picker") < line_no(mp, "sdsys/gpl.bp/sl_*            :")
        and 0 < line_no(mp, "sdsys/messages/1117[1-5]") < line_no(mp, "sdsys/messages/117*"), "")
    return out


def load():
    raw = {}
    for n in NEEDED + OPTIONAL:
        p = os.path.join(BP, n)
        if not os.path.isfile(p):
            if n in OPTIONAL:
                continue
            raise FileNotFoundError(p)
        with open(p, encoding="latin-1") as f:
            raw[n] = f.read()
    for m in MSGS:
        p = os.path.join(MSG, str(m))
        if not os.path.isfile(p):
            continue
        with open(p, encoding="latin-1") as f:
            raw["msg%d" % m] = f.read()
    for key, p in (("regress.sh", REGRESS), ("regress-map.txt", MAP)):
        with open(p, encoding="latin-1") as f:
            raw[key] = f.read()
    return raw


def run(raw, quiet=False):
    rows = checks(raw)
    bad = [r for r in rows if not r[2]]
    if not quiet:
        for i, what, ok, detail in rows:
            print("  [%s] %s %s%s" % ("PASS" if ok else "FAIL", i, what, ("   <- " + str(detail)) if (detail and not ok) else ""))
    return rows, bad


MUT = [
    ("sl_pickwin", "the hot argument is no longer optional", "if not(unassigned(hot)) then hotl = hot", "hotl = hot"),
    ("sl_pickwin", "the filter text is not handed back", "   filtout = filt\n", "   null\n"),
    ("sl_pickwin", "a hot key is not looked for", "         case hotl # '' and index(@vm : hotl : @vm, @vm : k : @vm, 1) > 0\n", ""),
    ("sl_pickwin", "a hot key does not end the loop", "until st = 'done' or st = 'cancel' or st = 'hot'", "until st = 'done' or st = 'cancel'"),
    ("sl_pickwin", "a hot key gives status 0", "   if st = 'hot' then status = 2\n", "   if st = 'hot' then status = 0\n"),
    ("sl_pickwin", "a hot key answers nothing", "ret = k  ", "ret = ''  "),
    ("sl_palette", "the palette runs the code", "if ps # 0 then return", "if ps # 0 then return\n   execute codes<pr>"),
    ("sl_palette", "the palette answers the code of a disabled entry", "status = 2", "status = 2\n      ret = codes<pr>"),
    ("sl_palette", "a disabled entry is chosen like any other", "   if dis<pr> then", "   if 0 then"),
    ("sl_palette", "the code is answered before the test", "if ps # 0 then return", "if ps # 0 then return\n   ret = codes<pr>"),
    ("sl_palette", "a separator is listed", "if label = '-' or label = '' then continue", "if label = '' then continue"),
    ("sl_palette", "the mnemonic mark stays in the name", "         plain = change(label, '&', '')", "         plain = label"),
    ("sl_palette", "the reason is read from another subvalue", "why<n> = menus<m, v, 5>", "why<n> = menus<m, v, 4>"),
    ("sl_palette", "the submenu depth has no bound", "            if depth < PAL.DEPTH then", "            if 1 then"),
    ("sl_palette", "a disabled entry is not marked", "if isdis then shortcut = trim(shortcut : '  ' : sysmsg(11174))", "null"),
    ("sl_palette", "the flag is case sensitive", "index(upcase(menus<m, v, 4>), 'D', 1) > 0", "index(menus<m, v, 4>, 'D', 1) > 0"),
    ("sl_palette", "the phantom is asked to choose", "if system(25) then return", "if 0 then return"),
    ("sl_palette", "the palette opens a file", "   items = ''\n   codes = ''", "   open 'VOC' to vf else null\n   items = ''\n   codes = ''"),
    ("sl_palette", "the empty list is shown", "if n = 0 then return", "null"),
    ("sl_picker", "the picker writes a record", "         close fv\n", "         close fv\n         write id to vocf, 'x'\n"),
    ("sl_picker", "the file filter drops the dollar test", "and ids<i>[1, 1] # '$' then fl<-1> = ids<i>", "then fl<-1> = ids<i>"),
    ("sl_picker", "Ctrl-N is not asked for", ", 'ctrl-n', typed)", ", '', typed)"),
    ("sl_picker", "Ctrl-N answers ok", "               res = 'new'", "               res = 'ok'"),
    ("sl_picker", "Esc in the records ends the picker", "            case 1\n               stage = 1", "            case 1\n               return"),
    ("sl_picker", "the records are not a paged source", "pr, ps, fv, '0' : @fm", "pr, ps, '', '0' : @fm"),
    ("sl_picker", "the file is never closed", "         close fv\n", "         null\n"),
    ("sl_picker", "the phantom is asked to pick", "if system(25) then return", "if 0 then return"),
    ("sl_picker", "mode file goes on to the records", "         if mode = 'file' then", "         if 0 then"),
    ("sl_picker", "the typed text is not handed on", "               newtext = typed", "               newtext = ''"),
    ("msg11175", "the reason message is empty", "That action is not available now.", ""),
]


def selftest():
    try:
        raw = load()
    except FileNotFoundError as e:
        print("CANNOT RUN: %s is not there" % e)
        return 2
    rows, bad = run(raw)
    if bad:
        print("selftest: the real files already fail %d check(s)" % len(bad))
        return 1
    killed, missed = 0, []
    for fname, what, old, new in MUT:
        if raw[fname].count(old) != 1:
            print("  [CANNOT] %s: the text to change is found %d times in %s, not once" % (what, raw[fname].count(old), fname))
            return 2
        m = dict(raw)
        m[fname] = raw[fname].replace(old, new)
        rows_m, bad_m = run(m, quiet=True)
        if bad_m:
            killed += 1
            print("  [killed] %s  <- %s" % (what, ", ".join(r[0] for r in bad_m)))
        else:
            missed.append(what)
            print("  [MISSED] %s" % what)
    print("selftest: %d mutants, %d killed, %d missed" % (len(MUT), killed, len(missed)))
    return 0 if not missed else 1


def main():
    if "--selftest" in sys.argv:
        return selftest()
    try:
        raw = load()
    except FileNotFoundError as e:
        print("CANNOT RUN: %s is not there" % e)
        return 2
    rows, bad = run(raw)
    print("test-slpick-units: %d passed, %d failed" % (len(rows) - len(bad), len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
