#!/usr/bin/env python3
"""test-toolquery-units.py - the query and report builder, TOOL.QUERY (`gpl.bp/tool_query`), as invariants read off the source (S.75, development app DV4).  Free: no install, no sudo, no sd.

    python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-toolquery-units.py [--selftest]

WHAT THIS IS, AND WHAT IT IS NOT.  It reads the page's BASIC as text, with comments removed.  ***IT RUNS NOTHING, SO IT CANNOT SAY THAT A SENTENCE IS REFUSED OR THAT A QUERY IS SAVED***: that is
`sandbox-tool-query.py` (a private SD, ordinary sessions on a pseudo-terminal, the disk and a separate session as the evidence, and injection attempts whose side effects are looked for on the disk).
What a text check is for: the properties that make the page safe to give to an account holder - it is a USER app that asks no gate; the ONLY commands it runs are the query itself and the one
`create.file`; the query runs ONLY after `check.sentence` has accepted the exact text it runs; every value in a sentence goes through ONE quoting routine; every word is on a fixed list or is an
item of the chosen file's dictionary; the output of the query goes into one array and is cleaned before it is shown; the only file the page writes is `&queries&`, only after a box, and only with
the one `write` and the one `delete` statement.  Those are ORDER and ABSENCE, which an edit can move and still compile.

--selftest breaks each invariant in the way an edit plausibly would and requires a check to notice; a mutant that nothing catches is a failure of the self-test.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SDSYS = os.path.normpath(os.path.join(HERE, "..", "sdsys"))
GPL = os.path.join(SDSYS, "gpl.bp")
FILES = {
    "page": os.path.join(GPL, "tool_query"),
    "voc": os.path.join(SDSYS, "voc_template", "tool.query"),
    "newvoc": os.path.join(SDSYS, "newvoc", "tool.query"),
    "help": os.path.join(SDSYS, "helptext", "tool.query.page"),
}
SAFE = "abcdefghijklmnopqrstuvwxyz0123456789._-"


def load():
    raw = {}
    for k, p in FILES.items():
        try:
            with open(p, encoding="latin-1") as f:
                raw[k] = f.read()
        except OSError:
            raw[k] = ""
    return raw


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


def nostr(text):
    """the code with the quoted text taken out, so that a word in a message is not read as a statement"""
    return re.sub(r"'[^'\n]*'|\"[^\"\n]*\"", "''", text)


def block(text, label):
    """The text of an internal subroutine: from its label to the next label at the start of a line (or to END)."""
    m = re.search(r"^" + re.escape(label) + r":\s*$", text, re.M)
    if not m:
        return ""
    n = re.search(r"^[a-z][a-z.0-9]*:\s*$|^end\s*$", text[m.end():], re.M)
    return text[m.start(): m.end() + (n.start() if n else len(text))]


def ordered(text, *needles):
    """every needle is in the text and they come in this order"""
    at = -1
    for n in needles:
        i = text.find(n, at + 1)
        if i < 0:
            return False
        at = i
    return True


def words(pg, name):
    m = re.search(r"^\s*" + re.escape(name) + r" = '([^']*)'", pg, re.M)
    return m.group(1).split() if m else None


def checks(raw):
    rows = []

    def ck(i, what, ok, detail=""):
        rows.append((i, what, bool(ok), detail))

    pg = strip_bas(raw["page"])
    code = nostr(pg)
    main = pg[: pg.find("\nreset.query:")] if "\nreset.query:" in pg else pg
    ck("TQ0", "NULL CASE: the page, both VOC entries and the help record were found and are not empty (a check on nothing would pass)",
       len(pg) > 25000 and raw["voc"].strip() != "" and raw["newvoc"].strip() != "" and len(raw["help"].split("\n")) >= 4, "%d" % len(pg))
    ck("TQ1", "the page is an internal program catalogued as $tool_query, and EVERY account has it as a verb: newvoc and SDSYS's VOC both run that program",
       re.search(r"^\$internal\s*\nprogram \$tool_query\s*\n\$catalog \$tool_query\b", pg, re.M) is not None and raw["voc"].split("\n")[:3] == ["V", "CA", "$tool_query"]
       and raw["newvoc"].split("\n")[1:3] == ["CA", "$tool_query"], repr((raw["voc"][:30], raw["newvoc"][:60])))
    op = main.find("call $tk_open('tool.query', '', ctx, err)")
    ck("TQ2", "it is a USER app that asks no gate: the base is opened with no audience BEFORE the files are read (the first read is gosub read.files), and nothing in the program asks the kernel for a gate or the administrator",
       0 <= op < main.find("gosub read.files") and "kernel(" not in pg and "'admin'" not in pg and "K$" not in code.replace("SL$ACTIVE", "") and "if err # '' then\n      display err\n      stop" in main
       and not re.search(r"^\s*(open|read|readv|select|sselect)\b", main[: max(op, 0)], re.M), op)
    verbs, redirect, keepwords, opwords = (words(pg, n) for n in ("verbs", "redirect", "keepwords", "opwords"))
    need = "to saving on.to lptr file as csv delimiter xml json json.lines style".split()
    ck("TQ3", "the word lists are declared once at the top: the first words are exactly list, sort, count and sum; every word that sends the output elsewhere or writes (to saving on.to lptr file as csv delimiter xml json style ...) is in the redirect list; "
       "no word of the redirect list is also a word the page allows; the operators the page offers are the eight of the table",
       verbs == ["list", "sort", "count", "sum"] and redirect is not None and set(need) <= set(redirect) and keepwords is not None and opwords is not None
       and not (set(redirect) & (set(keepwords) | set(opwords) | set(verbs))) and "qwords = verbs : ' ' : redirect : ' ' : keepwords : ' ' : opwords" in pg
       and "ops = '=' : @fm : 'ne' : @fm : '<' : @fm : '>' : @fm : '<=' : @fm : '>=' : @fm : 'like' : @fm : 'unlike'" in pg, repr((verbs, redirect)))
    ex = [e.strip() for e in re.findall(r"^\s*execute\b[^\n]*", code, re.M)]
    run, sav = block(pg, "do.run"), block(pg, "do.save")
    ck("TQ4", "the page runs exactly two commands, each by one execute statement: the query (in do.run, the sentence check.sentence returned) and `create.file &queries& dynamic` (in do.save, a literal declared once, after its box); "
       "it uses neither $tk_run nor $tk_runx (they refuse a quote), and no statement can reach the operating system or another program",
       ex == ["execute run.s trapping aborts capturing out", "execute qsent trapping aborts capturing mk"] and any(e in nostr(run) for e in ex[:1]) and ex[1] in nostr(sav)
       and pg.count("qsent = 'create.file &queries& dynamic'") == 1 and pg.count("create.file") == 1 and "$tk_run" not in pg
       and not re.search(r"^\s*(openseq|openpath|osopen|oswrite|osdelete|osread|logto|chain|perform|clearfile|deleteseq|writeseq|setptr|call\s+!?sh\b)", code, re.M), ex)
    ck("TQ5", "R: the sentence is checked once more, and what is RUN is the text check.sentence returned (run.s = chk.out, never sent), a refusal returns before the execute; a waiting select list is noticed before the run; "
       "the output is cut into lines, cleaned and kept in one array, and NOTHING else shows or keeps it",
       ordered(run, "if sent = '' then", "chk.s = sent", "gosub check.sentence", "if chk.err # '' then\n      msg = 'not run: ' : chk.err\n      return\n   end", "run.s = chk.out",
               "sel.was = selectinfo(0, SL$ACTIVE)", "execute run.s trapping aborts capturing out", "out = change(change(change(out, char(13) : char(10), @fm), char(10), @fm), char(13), '')",
               "gosub strip.esc", "view = 'results'") and run.count("run.s") == 3 and not re.search(r"^\s*(crt|display|print|screen text)\b[^\n]*\bout\b", code, re.M)
       and "execute run.s" not in pg.replace(run, ""), "")
    qv = block(pg, "q.value")
    ck("TQ6", "ONE routine quotes a value: it refuses every control character and every character that is not plain ASCII, the double and the single quote, the backslash, the backquote and the semicolon, and puts the value in double quotes; "
       "the five characters are made with char() once; gen.sentence never quotes by hand, and every use of qv.out follows a call of q.value whose refusal is looked at",
       "QDQ = char(34) ; QSQ = char(39) ; QBS = char(92) ; QBQ = char(96) ; QSEMI = char(59)" in pg and "case qn < 32 or qn > 126" in qv
       and "case qc = QDQ or qc = QSQ or qc = QBS or qc = QBQ or qc = QSEMI" in qv and "if qv.err = '' then qv.out = QDQ : qv.in : QDQ" in qv and "qn = seq(qc)" in qv
       and "QDQ" not in block(pg, "gen.sentence") and "qv.out =" not in pg.replace(qv, "") and pg.count("QDQ : qv.in : QDQ") == 1
       and block(pg, "gen.sentence").count("gosub q.value") == 3 and block(pg, "gen.sentence").count("qv.out") == 3
       and len(re.findall(r"gosub q\.value\n\s+if qv\.err # '' then", block(pg, "gen.sentence"))) == 3, "")
    cs = block(pg, "check.sentence")
    ck("TQ7", "check.sentence refuses what the quoting would: a control or non-ASCII character, a single quote, a backslash, a backquote, a semicolon; it reads the words (a quote glued to a word, an open quote, text glued after a closing quote are refused); "
       "the first word must be one of the four, the file must be the chosen one, every other word is a quoted value, a redirect word REFUSED FIRST, a word of the lists, a number, or a usable item of the dictionary; anything else is refused",
       ordered(cs, "if len(cs) > MAXSENT then", "case cn < 32 or cn > 126", "case cn = 39 or cn = 92 or cn = 96 or cn = 59", "chk.err = 'a quote must come after a space, not inside a word'", "chk.err = 'a quote is not closed'",
               "if index(' ' : verbs : ' ', ' ' : toks<1> : ' ', 1) = 0 then", "if fname = '' or toks<2> # fname then", "for ck = 3 to nt")
       and ordered(cs, "case tk[1, 1] = QDQ", "case index(' ' : redirect : ' ', ' ' : tk : ' ', 1) > 0", "case index(' ' : keepwords : ' ' : opwords : ' ', ' ' : tk : ' ', 1) > 0", "case tk matches \"1N0N\"",
                   "gosub find.item", "if vdp = 0 then", "if dok<vdp> # 1 then chk.err =", "chk.out = change(toks, @fm, ' ')")
       and "a closing quote must be followed by a space" in cs and "toks<-1> = downcase(cur)" in cs, "")
    gs = block(pg, "gen.sentence")
    ck("TQ8", "the sentence the boxes make is checked by check.sentence before it is kept: sent is assigned from chk.out only after the check passed, and nowhere else in the routine; a value is quoted only through q.value and its refusal ends the build",
       ordered(gs, "chk.s = verb : ' ' : fname : body", "gosub check.sentence", "if chk.err # '' then\n      senterr = 'The boxes made a sentence the page will not run: ' : chk.err\n      return\n   end\n   sent = chk.out")
       and len(re.findall(r"^\s*sent = ", gs, re.M)) == 2 and "senterr = 'condition ' : gi : ': ' : qv.err\n            exit" in gs, "")
    rd = block(pg, "read.dict")
    ic = block(pg, "item.check")
    ck("TQ9", "the items offered are the fields of the dictionary: types D E I C A S only (a phrase, a link, a text record and a record whose id starts with a dollar are not listed), @id first; an item is put in a sentence only when its name is made of a-z 0-9 dot dash underscore "
       "(@ as the first character), is not a word of the lists the page knows, and is not a keyword of the VOC",
       "index('DEICAS', tc, 1) = 0" in rd and "if t2[1, 2] = 'PH' then tc = ''" in rd and "if did[1, 1] = '$' then tc = ''" in rd and "ditem<1> = '@id'" in rd
       and "if upcase(dkr<1>)[1, 1] = 'K' then ck.ok = 0" in rd and "okc = '%s'" % SAFE in ic and "not(ck.q = 1 and ck.c = '@')" in ic and "index(' ' : qwords : ' ', ' ' : ck.id : ' ', 1) > 0" in ic
       and ordered(rd, "gosub item.check", "read dkr from dvoc, ck.id then", "dok<rd> = (if ck.ok then 1 else 0)"), "")
    rf, pf, cf, cn = block(pg, "read.files"), block(pg, "probe.file"), block(pg, "choose.file"), block(pg, "check.name")
    ck("TQ10", "the files offered are the VOC entries of type F that open, are a dynamic or a directory file and have a dictionary; a name is chosen only when it is made of the characters $tk_run lets through (the same list, at most 63), checked before fname is set",
       "if t1 = 'F' or t1[1, 5] = 'FILE ' then" in rf and "if pft = FL$TYPE.DH then pf.t = 'dyn'" in pf and "if pft = FL$TYPE.DIR then pf.t = 'dir'" in pf and "open 'DICT', pfn to pdv then" in pf
       and "good = '%s'" % SAFE in cn and "okname = (len(fn) > 0 and len(fn) <= 63)" in cn and "okname = @false" in cn and ordered(cf, "fn = fshown<fc>", "gosub check.name", "if not(okname) then", "fname = fn", "gosub read.dict") and cf.count("fname = fn") == 1, "")
    de = block(pg, "do.edit")
    ck("TQ11", "E: the text typed is read by check.sentence before it becomes the sentence, a refusal leaves the sentence as it was, and edited is set only after the check passed",
       ordered(de, "chk.s = trimf(trimb(es))", "gosub check.sentence", "if chk.err # '' then\n      msg = 'not accepted: ' : chk.err\n      return\n   end", "sent = chk.out", "edited = 1")
       and len(re.findall(r"^\s*sent = ", de, re.M)) == 1 and de.count("edited = 1") == 1, "")
    chg = block(pg, "changed")
    handlers = {"mark.column": 1, "flag.column": 1, "edit.cond": 1, "edit.sort": 1, "edit.option": 7, "keys.conds": 2, "keys.sorts": 2, "keys.columns": 1}
    ck("TQ12", "a change in a box writes the sentence again and gives up a hand edit: `changed` clears edited before it builds, and every routine that changes a box calls it (as many times as it has places that change one)",
       ordered(chg, "if edited then\n      edited = 0", "gosub gen.sentence") and all(block(pg, h).count("gosub changed") >= n for h, n in handlers.items()), "")
    wr = [w.strip() for w in re.findall(r"^\s*write\s[^\n]*", code, re.M)]
    dl = [d.strip() for d in re.findall(r"^\s*delete\s[^\n]*", code, re.M)]
    opens = [o.strip() for o in re.findall(r"^\s*open\s+(.*?)\s+to\s+\w+", pg, re.M)]
    allowed = {"'VOC'", "pfn", "'DICT', pfn", "'DICT', fname", "'&queries&'"}
    ck("TQ13", "the page writes one file, &queries&: one `write` statement and one `delete` statement in the whole program, both on a file opened as '&queries&' (no other file is opened but the VOC, the files it lists and their dictionaries); the save checks the name "
       "(a-z 0-9 dot dash underscore, at most 40), the cap of 100, shows a box (the file's creation; the write, with the name typed to replace one) and writes only when the box answered Run",
       wr == ["write wrec to qf, qname on error writeok = @false"] and dl == ["delete qf, lname on error delok = @false"] and set(opens) <= allowed and "'&queries&'" in opens
       and all(re.search(r"^\s*open\s+'&queries&'\s+to\s+qf\b", l) for l in pg.split("\n") if re.search(r"\bto qf\b", l) and l.strip().startswith("open"))
       and ordered(sav, "gosub check.name", "if not(okname) or len(fn) > 40 then", "qname = fn", "call $tk_confirm(qsent, lines, '', res, cmsg)", "if res # 'run' then", "execute qsent trapping aborts capturing mk",
                   "if naq >= MAXSAVED then", "call $tk_confirm(wsent, lines, qname, res, cmsg, sysmsg(11952))", "call $tk_confirm(wsent, lines, '', res, cmsg, sysmsg(11952))",
                   "if res # 'run' then\n      msg = cmsg\n      close qf\n      return\n   end\n   gosub pack.record", "write wrec to qf, qname") and "fn = downcase(trim(nn))" in sav, repr((wr, dl, sorted(set(opens)))))
    dsel = block(pg, "delete.selected")
    ck("TQ14", "X: a saved query is deleted only after a box that asks its name typed, and the only record deleted is the one named in the list",
       ordered(dsel, "lname = sv.ids<svc>", "call $tk_confirm(dsent, lines, lname, res, cmsg, sysmsg(11953))", "if res # 'run' then\n      msg = cmsg\n      return\n   end", "open '&queries&' to qf then", "delete qf, lname on error delok = @false"), "")
    ls = block(pg, "load.selected")
    ck("TQ15", "a loaded record is DATA: it must say it is a query, name a file the page lists (checked again as a name), its kind is one of three words, it goes into the boxes only through validate.panes BEFORE the sentence is built, "
       "and a sentence it holds is kept only when check.sentence accepts it",
       ordered(ls, "if lrec<1> # 'query1' then", "if not(known) then", "gosub check.name", "if not(okname) then", "fname = lfile", "gosub read.dict", "opt.kind = (if lk = 'count' or lk = 'sum' then lk else 'list')",
               "gosub validate.panes", "gosub gen.sentence", "chk.s = lrec<19>", "gosub check.sentence", "if chk.err = '' then\n         sent = chk.out\n         edited = 1"), "")
    vp = block(pg, "validate.panes")
    ck("TQ16", "validate.panes keeps only what passes: a column that is an item the page uses (once, at most 20), a condition whose item is one, whose operator is in the table and whose value q.value accepts, a sort item that is one, a heading and a footing that q.value accepts, a sample of 1 to 99999 digits",
       "if dok<vdp> = 1 then\n            vn += 1" in vp and "locate vop in ops<1> setting vpo else vpo = 0" in vp and "if vdp > 0 and vpo > 0 and qv.err = '' then" in vp and "vn < MAXC" in vp and "not(dupe)" in vp
       and vp.count("gosub q.value") == 3 and "smp.in = opt.sample\n      gosub check.sample" in vp and ordered(block(pg, "check.sample"), "if smp.in matches \"1N0N\" then", "if len(smp.in) <= 5 then", "smp.out = smp.in + 0", "if smp.out >= 1 then smp.ok = 1")
       and "gosub check.sample" in block(pg, "edit.option") and ordered(vp, "if vdp > 0 then\n            if dok<vdp> = 1 then\n               ns2<vi> = vid"), "")
    ck("TQ17", "what the query printed is cut into lines, every escape sequence is taken out and every other control and non-ASCII character is made a dot BEFORE a line is kept; at most 2000 lines are kept and the page says how many there were",
       ordered(run, "rl.n = dcount(out, @fm)", "if rl.cnt > MAXLINES then rl.cnt = MAXLINES", "gosub strip.esc", "rl<ri> = convert(ctl, dots, ln)[1, 400]", "out = ''")
       and "for k0 = 1 to 31" in pg and "for k0 = 127 to 255" in pg and "info := ', the first ' : rl.cnt : ' are kept'" in block(pg, "draw.results") and not re.search(r"screen text[^\n]*\bout\b", code), "")
    need_keys = ["f1", "tab", "enter", "space", "b", "t", "x", "j", "d", "/", "r", "e", "s", "l", "f5", "up", "esc", "ctrl-q"]
    acts = ["nm = 'f1'", "nm = 'tab'", "nm = 'enter'", "nm = 'space'", "nm = 'b'", "nm = 't'", "nm = 'x'", "nm = 'j'", "nm = 'd'", "nm = '/'", "nm = 'r'", "nm = 'e'", "nm = 's'", "nm = 'l'", "nm = 'f5'", "nm = 'up'", "nm = 'esc'", "nm = 'ctrl-q'"]
    ck("TQ18", "a letter is the same key in either case, a space is the key `space`, and every key the page acts on has a place in the key table (the function-key row shows exactly the keys it uses)",
       "if len(nm) = 1 then nm = downcase(nm)" in pg and "if nm = ' ' then nm = 'space'" in pg and all(("call $tk_keys('add', keys, '%s'," % k) in pg for k in need_keys) and all(a in pg for a in acts), "")
    ck("TQ19", "the layout fits the 140 by 43 frame: five boxes and the sentence (rows 1-19, 20-30, 31-39), 16 rows of files at y 2-17 and of columns at y 3-18, six condition rows at y 3-8, four sort rows at y 22-25, seven option rows at y 21-27, five sentence rows at y 32-36; [?] at 134,2",
       all(s in pg for s in ("screen box at 1,1 size 28,19", "screen box at 29,1 size 44,19", "screen box at 73,1 size 66,19", "screen box at 1,20 size 46,11", "screen box at 47,20 size 92,11", "screen box at 1,31 size 138,9",
                             "VISF = 16 ; VISC = 16 ; RVIS = 33 ; SVIS = 32", "hx = 134 ; hy = 2", "at 2,1 + dr attr ra width 26", "at 30,2 + dr attr ra width 42", "at 74,2 + dr attr ra width 62", "at 2,21 + dr attr ra width 44",
                             "at 48,20 + dr attr ra width 90", "for dr = 1 to 5", "at 3,31 + dr attr"))
       and "chh = ctx<TK.C.H> - 4" in pg, "")
    ck("TQ20", "the page waits on the keyboard only through the base: the key read is screen key, the end of the input and the cursor lock end it, and the base is closed on the way out",
       "screen key returning nm" in pg and "if status() = ER$EOF then exit" in pg and "case nm = 'guardquit'\n            exit" in pg and pg.find("call $tk_close(ctx)") > pg.find("repeat") and "input " not in code.replace("input.", ""), "")
    ck("TQ21", "the help record names a page of the documentation, and the page asks for it by that name from the key and from the mouse (the key is the record's name)",
       pg.count("call $tk_help('box', 'tool.query.page', hm, 0, 0)") == 2 and re.match(r"^[^\n]{1,60}\n[0-9a-z-]+\n", raw["help"]) is not None and "tool.query.page" in raw["page"], repr(raw["help"][:60]))
    ck("TQ22", "the limits are the ones the documentation states: a sentence of 600 characters, a value of 200, six conditions, four sort levels, 20 columns, 2000 lines of output, 100 saved queries, 500 dictionary items",
       all(re.search(s + r"\b", pg) for s in ("MAXCOND = 6", "MAXSORT = 4", "MAXC = 20", "MAXSENT = 600", "MAXVAL = 200", "MAXLINES = 2000", "MAXSAVED = 100", "MAXITEMS = 500")), "")
    sg = block(pg, "gen.sentence")
    ck("TQ23", "the sentence is made in one order the query processor takes (conditions with their own and / or, the sorts, the columns with break.on or total, then the options), the verb is sort only when a sort level is set, and count and sum take no sort",
       ordered(sg, "piece = 'with ' :", "(if srt.dir<gi> = 'd' then 'by.dsnd' else 'by')", "if nso > 0 then verb = 'sort'", "body := ' break.on ' : cols<gi>", "body := ' total ' : cols<gi>", "body := ' id.sup'", "body := ' det.sup'", "body := ' heading '",
               "body := ' footing '", "if verb = 'sum' then", "body := ' no.page'", "body := ' sample ' : opt.sample") and "if verb = 'list' then\n      nso = 0" in sg and "senterr = 'A sum needs at least one column" in sg, "")
    ck("TQ24", "a VOC file name and a dictionary item id are shown through the control-character filter, as every other text the page shows is (a name another user wrote into a shared dictionary or a pointed-at file can hold an escape sequence)",
       "fmt(convert(ctl, dots, dn)[1, 20], '20L')" in block(pg, "draw.files") and "fmt(convert(ctl, dots, ditem<kk>)[1, 21], '22L')" in block(pg, "draw.columns"), "")
    return rows


def sub(key, old, new):
    def f(raw):
        r = dict(raw)
        n = r[key].count(old)
        if n != 1:
            raise KeyError("%s: %r is found %d times, not once, so the mutant cannot be made" % (key, old[:70], n))
        r[key] = r[key].replace(old, new, 1)
        return r
    return f


def setkey(key, val):
    def f(raw):
        r = dict(raw)
        r[key] = val
        return r
    return f


Q = "call $tk_open('tool.query', '', ctx, err)"
MUTANTS = [
    ("a file name is shown raw", "TQ24", sub("page", "fmt(convert(ctl, dots, dn)[1, 20], '20L')", "fmt(dn[1, 20], '20L')")),
    ("an item id is shown raw", "TQ24", sub("page", "fmt(convert(ctl, dots, ditem<kk>)[1, 21], '22L')", "fmt(ditem<kk>[1, 21], '22L')")),
    ("a value may hold a semicolon", "TQ6", sub("page", "qc = QBQ or qc = QSEMI", "qc = QBQ")),
    ("a value may hold a single quote", "TQ6", sub("page", "qc = QDQ or qc = QSQ or qc = QBS", "qc = QDQ or qc = QBS")),
    ("a value may hold a double quote", "TQ6", sub("page", "case qc = QDQ or qc = QSQ", "case qc = QSQ")),
    ("a value may hold a backslash", "TQ6", sub("page", "qc = QSQ or qc = QBS or qc = QBQ", "qc = QSQ or qc = QBQ")),
    ("a value may hold a control character", "TQ6", sub("page", "case qn < 32 or qn > 126", "case qn > 126")),
    ("a value may hold a character that is not ASCII", "TQ6", sub("page", "case qn < 32 or qn > 126", "case qn < 32")),
    ("a value is not put in quotes", "TQ6", sub("page", "if qv.err = '' then qv.out = QDQ : qv.in : QDQ", "if qv.err = '' then qv.out = qv.in")),
    ("the semicolon constant is the wrong character", "TQ6", sub("page", "QSEMI = char(59)", "QSEMI = char(58)")),
    ("gen.sentence quotes a value by hand", "TQ6", sub("page", "         qv.in = cnd.val<gi>\n         gosub q.value\n         if qv.err # '' then\n            senterr = 'condition ' : gi : ': ' : qv.err\n            exit\n         end\n",
                                                       "         qv.out = QDQ : cnd.val<gi> : QDQ\n")),
    ("a sentence may hold a semicolon", "TQ7", sub("page", "cn = 96 or cn = 59", "cn = 96")),
    ("a sentence may hold a backquote", "TQ7", sub("page", "cn = 92 or cn = 96 or cn = 59", "cn = 92 or cn = 59")),
    ("a sentence may hold a single quote", "TQ7", sub("page", "case cn = 39 or cn = 92", "case cn = 92")),
    ("a sentence may start with any word", "TQ7", sub("page", "index(' ' : verbs : ' ', ' ' : toks<1> : ' ', 1) = 0 then", "index(' ' : verbs : ' ', ' ' : toks<1> : ' ', 1) = -1 then")),
    ("a sentence may name any file", "TQ7", sub("page", "if fname = '' or toks<2> # fname then", "if fname = '' then")),
    ("a redirect word is not looked for", "TQ7", sub("page", "case index(' ' : redirect : ' ', ' ' : tk : ' ', 1) > 0", "case index(' ' : redirect : ' ', ' ' : tk : ' ', 1) > 99999")),
    ("an unknown word is accepted", "TQ7", sub("page", "            if vdp = 0 then\n               chk.err = tk :", "            if vdp = -1 then\n               chk.err = tk :")),
    ("an item the page does not use is accepted", "TQ7", sub("page", "if dok<vdp> # 1 then chk.err =", "if dok<vdp> = 7 then chk.err =")),
    ("a long sentence is accepted", "TQ7", sub("page", "if len(cs) > MAXSENT then", "if len(cs) > 99999 then")),
    ("an open quote is accepted", "TQ7", sub("page", "   if inq then\n      chk.err = 'a quote is not closed'\n      return\n   end\n", "")),
    ("lptr leaves the redirect list", "TQ3", sub("page", "redirect = 'to saving on.to lptr file", "redirect = 'to saving on.to file")),
    ("to leaves the redirect list", "TQ3", sub("page", "redirect = 'to saving", "redirect = 'saving")),
    ("select is a first word", "TQ3", sub("page", "verbs = 'list sort count sum'", "verbs = 'list sort count sum select'")),
    ("lptr is an allowed word", "TQ3", sub("page", "keepwords = 'with and or by", "keepwords = 'lptr with and or by")),
    ("the query runs the text as it was, not as it was checked", "TQ5", sub("page", "run.s = chk.out", "run.s = sent")),
    ("the query runs without the check", "TQ5", sub("page", "   chk.s = sent\n   gosub check.sentence\n   if chk.err # '' then\n      msg = 'not run: ' : chk.err\n      return\n   end\n   run.s = chk.out", "   run.s = sent")),
    ("the output is shown as it came", "TQ5", sub("page", "      gosub strip.esc\n      rl<ri> = convert(ctl, dots, ln)[1, 400]", "      crt out<ri>\n      rl<ri> = ln")),
    ("a waiting select list is not noticed", "TQ5", sub("page", "   sel.was = selectinfo(0, SL$ACTIVE)\n", "   sel.was = 0\n")),
    ("a third command is run", "TQ4", sub("page", "draw.all:\n   cw2 = ctx<TK.C.W>", "draw.all:\n   execute 'sh'\n   cw2 = ctx<TK.C.W>")),
    ("the file the page makes is another", "TQ4", sub("page", "qsent = 'create.file &queries& dynamic'", "qsent = 'create.file &queries& dynamic sh'")),
    ("a command goes through $tk_run", "TQ4", sub("page", "      execute qsent trapping aborts capturing mk\n", "      call $tk_run('create.file', qsent, mk, mst, mer)\n")),
    ("the boxes' sentence is kept without a check", "TQ8", sub("page", "   gosub check.sentence\n   if chk.err # '' then\n      senterr = 'The boxes made a sentence the page will not run: ' : chk.err\n      return\n   end\n   sent = chk.out", "   sent = chk.s")),
    ("a refused value does not end the build", "TQ8", sub("page", "senterr = 'condition ' : gi : ': ' : qv.err\n            exit", "senterr = 'condition ' : gi : ': ' : qv.err")),
    ("an edited sentence is taken unchecked", "TQ11", sub("page", "   chk.s = trimf(trimb(es))\n   gosub check.sentence\n   if chk.err # '' then\n      msg = 'not accepted: ' : chk.err\n      return\n   end\n   sent = chk.out", "   sent = trimf(trimb(es))")),
    ("an edit is marked before it is checked", "TQ11", sub("page", "   chk.s = trimf(trimb(es))\n   gosub check.sentence", "   edited = 1\n   chk.s = trimf(trimb(es))\n   gosub check.sentence")),
    ("a change does not give up a hand edit", "TQ12", sub("page", "   if edited then\n      edited = 0\n      msg = 'the sentence was written again from the boxes'\n   end\n   gosub gen.sentence", "   gosub gen.sentence")),
    ("marking a column does not write the sentence again", "TQ12", sub("page", "      cols<-1> = mcol\n   end\n   gosub changed\n   return", "      cols<-1> = mcol\n   end\n   return")),
    ("a second record is written", "TQ13", sub("page", "   wrec<19> = sent\n   return", "   wrec<19> = sent\n   write wrec to qf, 'zz'\n   return")),
    ("the save writes without waiting for the box", "TQ13", sub("page", "   if res # 'run' then\n      msg = cmsg\n      close qf\n      return\n   end\n   gosub pack.record", "   gosub pack.record")),
    ("a record is replaced without its name typed", "TQ13", sub("page", "call $tk_confirm(wsent, lines, qname, res, cmsg, sysmsg(11952))", "call $tk_confirm(wsent, lines, '', res, cmsg, sysmsg(11952))")),
    ("the cap of saved queries is not looked at", "TQ13", sub("page", "      if naq >= MAXSAVED then", "      if naq >= 999999 then")),
    ("a name is not checked", "TQ13", sub("page", "   if not(okname) or len(fn) > 40 then", "   if len(fn) > 40 then")),
    ("another file is opened", "TQ13", sub("page", "set.pane:\n   begin case", "set.pane:\n   open 'bp' to xbp then close xbp\n   begin case")),
    ("the file the page creates is made without its box", "TQ13", sub("page", "      call $tk_confirm(qsent, lines, '', res, cmsg)\n      if res # 'run' then\n         msg = cmsg\n         return\n      end\n", "")),
    ("a saved query is deleted without its name typed", "TQ14", sub("page", "call $tk_confirm(dsent, lines, lname, res, cmsg, sysmsg(11953))", "call $tk_confirm(dsent, lines, '', res, cmsg, sysmsg(11953))")),
    ("a saved query is deleted without the box", "TQ14", sub("page", "   call $tk_confirm(dsent, lines, lname, res, cmsg, sysmsg(11953))\n   if res # 'run' then\n      msg = cmsg\n      return\n   end\n   delok", "   delok")),
    ("a loaded record skips the checks", "TQ15", sub("page", "   gosub validate.panes\n   gosub gen.sentence\n   * a sentence that was edited", "   gosub gen.sentence\n   * a sentence that was edited")),
    ("a loaded record may name any file", "TQ15", sub("page", "   if not(known) then", "   if known = 7 then")),
    ("a loaded sentence is taken unchecked", "TQ15", sub("page", "      chk.s = lrec<19>\n      gosub check.sentence\n      if chk.err = '' then\n         sent = chk.out", "      chk.s = lrec<19>\n      chk.err = ''\n      if chk.err = '' then\n         sent = chk.s")),
    ("a loaded record may be any kind of thing", "TQ15", sub("page", "   if lrec<1> # 'query1' then", "   if lrec<1> = 'zzz' then")),
    ("an item the page does not use is kept on loading", "TQ16", sub("page", "         if dok<vdp> = 1 then\n            vn += 1", "         if 1 then\n            vn += 1")),
    ("an operator is not looked up on loading", "TQ16", sub("page", "if vdp > 0 and vpo > 0 and qv.err = '' then", "if vdp > 0 and qv.err = '' then")),
    ("a condition value is not quoted-checked on loading", "TQ16", sub("page", "         qv.in = cnd.val<vi>\n         gosub q.value\n         if vdp > 0 and vpo > 0", "         qv.err = ''\n         if vdp > 0 and vpo > 0")),
    ("the sample is added to before it is known to be digits (BASIC does not short-circuit: a non-number aborts the page)", "TQ16",
     sub("page", "   if smp.in matches \"1N0N\" then\n      if len(smp.in) <= 5 then\n         smp.out = smp.in + 0\n         if smp.out >= 1 then smp.ok = 1\n      end\n   end",
         "   smp.out = smp.in + 0\n   if smp.in matches \"1N0N\" and len(smp.in) <= 5 and smp.out >= 1 then smp.ok = 1")),
    ("the sample box takes any text", "TQ16", sub("page", "               smp.in = vv\n               gosub check.sample\n               if smp.ok then\n                  opt.sample = smp.out", "               if 1 then\n                  opt.sample = vv")),
    ("escape sequences are not taken out of the output", "TQ17", sub("page", "      gosub strip.esc\n", "")),
    ("the output is not cut at 2000 lines", "TQ17", sub("page", "   if rl.cnt > MAXLINES then rl.cnt = MAXLINES\n", "")),
    ("the page does not say how many lines were cut", "TQ17", sub("page", "if rl.n > rl.cnt then info := ', the first ' : rl.cnt : ' are kept'", "info := ''")),
    ("a phrase is listed as a column", "TQ9", sub("page", "            if t2[1, 2] = 'PH' then tc = ''\n", "")),
    ("a dollar record is listed as a column", "TQ9", sub("page", "            if did[1, 1] = '$' then tc = ''\n", "")),
    ("a VOC keyword may be an item in a sentence", "TQ9", sub("page", "if upcase(dkr<1>)[1, 1] = 'K' then ck.ok = 0", "if upcase(dkr<1>)[1, 1] = 'Z' then ck.ok = 0")),
    ("@id is not the first item", "TQ9", sub("page", "   ditem<1> = '@id'\n", "")),
    ("an item name may hold a semicolon", "TQ9", sub("page", "okc = 'abcdefghijklmnopqrstuvwxyz0123456789._-'", "okc = 'abcdefghijklmnopqrstuvwxyz0123456789._-;'")),
    ("a link item is listed as a column", "TQ9", sub("page", "index('DEICAS', tc, 1) = 0", "index('DEICASL', tc, 1) = 0")),
    ("a file name may hold a dollar", "TQ10", sub("page", "good = 'abcdefghijklmnopqrstuvwxyz0123456789._-'\n   for q = 1", "good = 'abcdefghijklmnopqrstuvwxyz0123456789._-$'\n   for q = 1")),
    ("a file is chosen before its name is checked", "TQ10", sub("page", "   fn = fshown<fc>\n   gosub check.name\n   if not(okname) then\n      msg = 'this file name has", "   fn = fshown<fc>\n   fname = fn\n   gosub check.name\n   if not(okname) then\n      msg = 'this file name has")),
    ("a sequential file is offered", "TQ10", sub("page", "      if pft = FL$TYPE.DIR then pf.t = 'dir'", "      if pft = FL$TYPE.SEQ then pf.t = 'seq'")),
    ("the page asks the administrator question", "TQ2", sub("page", Q, "call $tk_open('tool.query', 'admin', ctx, err)")),
    ("the page reads the VOC before it opens the base", "TQ2", sub("page", "   " + Q + "\n", "   open 'VOC' to vocx then close vocx\n   " + Q + "\n")),
    ("the page asks for a gate", "TQ2", sub("page", "   prompt ''\n", "   prompt ''\n   if kernel(K$SH, -1) then null\n")),
    ("a key is missing from the key table", "TQ18", sub("page", "   call $tk_keys('add', keys, 'f5', 'read', 'reread', panes, 1)\n", "")),
    ("a capital R is not a key", "TQ18", sub("page", "   if len(nm) = 1 then nm = downcase(nm)", "   if len(nm) = 0 then nm = downcase(nm)")),
    ("the options box overruns its border", "TQ19", sub("page", "screen box at 47,20 size 92,11", "screen box at 47,20 size 92,12")),
    ("the page waits with no key reader of the library", "TQ20", sub("page", "screen key returning nm", "input nm, 1")),
    ("the end of the input is not seen", "TQ20", sub("page", "            if status() = ER$EOF then exit\n", "")),
    ("the help key names a record that does not exist", "TQ21", sub("help", "29c-sd-tcl-the-development-tools", "")),
    ("the help button asks for another record", "TQ21", sub("page", "      call $tk_help('box', 'tool.query.page', hm, 0, 0)\n      if hm # '' then msg = hm\n      return\n   end\n   if mev<1>", "      call $tk_help('box', 'tool.query.nopage', hm, 0, 0)\n      if hm # '' then msg = hm\n      return\n   end\n   if mev<1>")),
    ("the sentence may be longer", "TQ22", sub("page", "MAXSENT = 600", "MAXSENT = 6000")),
    ("the sort comes after the columns", "TQ23", sub("page", "      if nso > 0 then verb = 'sort'\n", "")),
    ("an ordinary account has no verb", "TQ1", setkey("newvoc", "")),
    ("SDSYS's verb runs another program", "TQ1", sub("voc", "$tool_query", "$tool_keys")),
]


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
    print("test-toolquery-units: tree %s" % os.path.dirname(GPL))
    if not raw["page"]:
        print("test-toolquery-units: CANNOT RUN - %s is not there" % FILES["page"])
        return 2
    rows = checks(raw)
    bad = report(rows)
    print("\ntest-toolquery-units: %d passed, %d failed" % (len(rows) - bad, bad))
    rc = 1 if bad else 0
    if "--selftest" in argv:
        rc = (selftest(raw) or rc)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
