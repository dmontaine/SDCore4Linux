#!/usr/bin/env python3
"""test-toolentries-units.py - TOOL.ENTRIES, the master files page (S.96 M1a-M2), as invariants read off the source.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-toolentries-units.py
  python3 .../test-toolentries-units.py --selftest

No sudo, no install, no sd.  Exit 0 all checks passed, 1 a check failed, 2 it could not run.  Written 3 Nov 26.

***WHAT THIS IS AND WHAT IT IS NOT.*** It reads sdsys/gpl.bp/tool_entries, the VOC record and the two help records as TEXT.  IT CANNOT SAY THE PAGE SHOWS THE RIGHT GATES OR THE RIGHT
ENTRIES: that is sandbox-tool-entries.py.  What it holds is the shape the design depends on and a hand edit could break unnoticed: the page is the administrator's and asks for that
first; it changes no record itself (since M2 the ONLY write is the temporary Q-pointer in SDSYS's VOC that lets the IDE reach an account's file, the ONLY delete takes that pointer away
and the ONLY execute gives the terminal to the IDE; no command, confirm box or master-file operation anywhere in it); THE OWNER'S POINTER RULE for E and N (3 Nov 26): the file to be edited
is judged by the kernel's geometry, from a register and an account VOC read afresh, BEFORE the pointer is written, and what the pointer opens is judged again before the IDE is given it;
the only files it opens are the register and, by the pathname the register gives, an account's VOC; an account's VOC is read when the cursor comes to it and every VOC is read only by
the find the person asks for; the gates are the three register fields in the order v d b; SDSYS is not in the list; the long lists are cut at MAXV.

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
IDE = os.path.join(SD64, "sdsys", "gpl.bp", "ide")
OPSH = os.path.join(SD64, "gplsrc", "op_sh.c")
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
    forbidden = [(n, s) for n, s in lines if re.search(r"(^|[\s;(])(writev|writeu|deletes|chain|perform|osexecute|os\.execute)\s", unquote(s) + " ")
                 or re.search(r"\$tk_run|\$tk_confirm|K\$MASTERS|!acc_|sd-elevate|modify\.account|set\.batch|run\.in", unquote(s))]
    forbidden = [(n, s) for n, s in forbidden if s != "call $tk_confirm(dsent, dlines, eid, res, cmsg, sysmsg(11953))"]   # M3: D's one confirm box, held by T18
    writes = [s for n, s in lines if re.search(r"(^|[\s;(])write\s", unquote(s) + " ")]
    deletes = [s for n, s in lines if re.search(r"(^|[\s;(])delete\s", unquote(s) + " ")]
    execs = [s for n, s in lines if re.search(r"(^|[\s;(])execute\s", unquote(s) + " ")]
    ck("T4 WHAT IT MAY CHANGE (M2, M3, M4): no record is written but the temporary pointer in SDSYS's VOC (ONE write, `write qrec on svf, qn on error`), the deletes take that pointer away "
       "(`delete svf, qn`), sweep the user number's own leftovers at the start (`delete svf, sw.id`) and delete D's one record through the file edit.record judged (`delete tf, eid`), the two "
       "executes give the terminal to the IDE (`execute sent`) and compile through run.in (`execute csent capturing cout`); no chain, perform, OS command, command runner, master-file operation or account verb anywhere in the page, "
       "and no confirm box but D's",
       not forbidden and writes == ["write qrec on svf, qn on error"] and deletes == ["delete svf, sw.id", "delete svf, qn", "delete tf, eid on error delok = @false"] and execs == ["execute csent capturing cout", "execute sent"],
       "%s %s %s %s" % (forbidden[:3], writes, deletes, execs))
    opens = [s for n, s in lines if re.search(r"\bopenpath\b", s)]
    kinds = sorted(set("register" if "@sdsys:@ds:'accounts'" in s else ("voc" if re.search(r"(apath<[a-z0-9]+>|ap\.f) ?:@ds ?: ?'voc'", s.replace(" : ", ":")) else ("dict" if re.match(r"openpath dp to df2? then", s)
                       else ("prog" if re.match(r"openpath (op2 to ofv|pp to pfv|pp2 to pf2) then", s) else s))) for s in opens))
    ck("T5 the only files it opens by pathname are the register, an account's VOC by the pathname the register gives and, by a path of one of that VOC's file pointers, a dictionary, a program "
       "file or the .out file beside it (twelve opens: the list; the VOC, the dictionaries, the .out file and the program files in collect.account; the entry under the cursor in the VOC, in "
       "a dictionary and in a program file; and the register and the account's VOC again in edit.record, for E and N); the other opens are SDSYS's own VOC (the pointer) and the file "
       "that pointer leads to, which is judged before the IDE is given it",
       kinds == ["dict", "prog", "register", "voc"] and len(opens) == 12 and txt.count("close ") >= 12
       and len(re.findall(r"^open 'voc' to svf else$", txt, re.M)) == 1 and len(re.findall(r"^open 'voc' to svf then$", txt, re.M)) == 2
       and len(re.findall(r"^open dfl, qn to tf else$", txt, re.M)) == 1, "%s %d" % (kinds, len(opens)))
    cap = "\n".join(s for n, s in section(lines, "collect.account:", "dclassify:"))
    ck("T5b a dictionary path that is not absolute is made from the ACCOUNT's directory, never the current one; the dictionaries are those the VOC's file pointers name (field 3); an item matches in its id OR its heading",
       "dp = parse.pathname.tokens(dpaths<fi>)" in cap and "if dp[1, 1] # '/' then dp = apath<ca> : @ds : dp" in cap and "upcase(trim(r<1>))[1, 1] = 'F' and trim(r<3>) # ''" in cap
       and "index(upcase(did), upcase(pat), 1) > 0 or index(upcase(dhead), upcase(pat), 1) > 0" in cap and "kind = 1 then" in cap)
    kd = "\n".join(s for n, s in section(lines, "do.kind:", "on.mouse:"))
    ck("T5c K cycles the kind (1, 2, 3 and round to 1) and takes the filter and the find off", "kind += 1\nif kind > 3 then kind = 1" in kd and "fnd = '' ; filt = ''" in kd and re.search(r"^kind = 1$", txt, re.M) is not None)
    ck("T5e the programs (M1c): a program file is found as tool.catalog finds it - a directory file named bp, or ending .bp, or with an F entry of the same name and .out beside it, and never a "
       "file whose name ends .out itself; its path has its tokens expanded and is the account's when relative; it must be a DIRECTORY file; a program is built when its lower-case id is among the "
       "ids of the .out file; the file's own path is asked for the > mark",
       "if not(len(tl) > 4 and tl[len(tl) - 3, 4] = '.out') then" in cap and "if tl = 'bp' then isp = 1" in cap and "if len(tl) > 3 and tl[len(tl) - 2, 3] = '.bp' then isp = 1" in cap
       and "read orr from vf, id : '.out' else orr = ''" in cap and "pp = parse.pathname.tokens(ppaths<fi>)" in cap and "if pp[1, 1] # '/' then pp = apath<ca> : @ds : pp" in cap
       and "if fileinfo(pfv, FL$TYPE) = FL$TYPE.DIR then" in cap and "onames = downcase(onames)" in cap and "locate downcase(pid) in onames<1> setting op3 then built = 'yes'" in cap
       and "op2 = pp : '.out'" in cap and "if popaths<fi> # '' then" in cap
       and "poutf = is.out" in cap and "ins poutf before cout<lp>" in cap)
    ck("T5d THE OWNER'S RULE (3 Nov 26): no pointer may lead the master to edit something in one account from another.  A target OUTSIDE the account being listed (asked of the kernel's own "
       "geometry, K$PATH.IN, which resolves .. and links; tokens expanded and the path made absolute from the account) is marked > - for a dictionary item that the ITEM lives elsewhere, "
       "for a VOC file pointer, a Q-pointer to another account or a remote item that the POINTER leads elsewhere - in a column of its own in every list; the pointer record itself stays an "
       "ordinary entry of the account; and the page follows no pointer to change anything (T4)",
       "is.out = (if kernel(K$PATH.IN, apath<ca> : @fm : tp) then 0 else 1)" in txt and "doutf = is.out" in cap and "ins doutf before cout<lp>" in cap and "ins coutf before cout<lp>" in cap
       and "coutf = (if downcase(trim(r<2>)) = downcase(anm<ca>) then 0 else 1)" in txt and re.search(r"case cty = 'R'\ncoutf = 1", txt) is not None and txt.count("fmt('>', '2L')") == 4
       and txt.count("(if hout<k> then '>' else '')") == 2 and txt.count("(if eout<k> then '>' else '')") == 2 and "sdsys" not in "\n".join(s for n, s in section(lines, "out.test:", "dclassify:")))
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
    ck("T8 both long reads are cut at MAXV (the entries and the hits) and the page says so", txt.count(">= MAXV") == 4 and txt.count("only the first ' : MAXV : ' are listed") == 3)       # collect.account's three reads and the find; the entries' foot, the hits' foot and the status line of a find
    ck("T9 the filter and the find ask with screen ask, take the AI's argument as the default, and each clears the other",
       txt.count("screen ask ptxt width 40 value ai.arg") == 2 and txt.count("value ai.arg") == 2 and "filt = trim(ft)\nfnd = ''" in txt and "fnd = trim(ft)\nfilt = ''" in txt)
    keyrows = re.findall(r"call \$tk_keys\('add', keys, '([^']+)'", txt)
    ck("T10 thirteen key rows: f1 enter tab / f k e n d c f5 ctrl-q esc, and the AI is offered only what changes what is shown (pane filter find kind refresh), never an edit, a delete or a compile",
       keyrows == ["f1", "enter", "tab", "/", "f", "k", "e", "n", "d", "c", "f5", "ctrl-q", "esc"] and re.findall(r"call \$tk_keys\('ai', keys, '([^']+)'", txt) == ["pane", "filter", "find", "kind", "refresh"], "%s" % keyrows)
    er = "\n".join(s for n, s in section(lines, "edit.record:", "sweep.pointers:"))
    ho = "\n".join(s for n, s in section(lines, "hand.over:", "do.filter:"))
    de = "\n".join(s for n, s in section(lines, "do.edit:", "do.delete:"))
    dd = "\n".join(s for n, s in section(lines, "do.delete:", "do.build:"))
    db = "\n".join(s for n, s in section(lines, "do.build:", "do.new:"))
    dr = "\n".join(s for n, s in section(lines, "delete.reached:", "compile.reached:"))
    cr = "\n".join(s for n, s in section(lines, "compile.reached:", "hand.over:"))
    dn = "\n".join(s for n, s in section(lines, "do.new:", "edit.record:"))

    def at(t, s=er):
        return s.find(t)
    i_ck, i_guard, i_w = at("if not(kernel(K$PATH.IN, ap.f : @fm : tp)) then"), at("if qold # qrec then"), at("write qrec on svf, qn on error")
    i_open, i_ck2, i_aud, i_hand = at("open dfl, qn to tf else"), at("in.ok = kernel(K$PATH.IN, ap.f : @fm : rp)"), at("void kernel(K$AUDIT, 'master edit account="), at("gosub hand.over")
    ck("T14 THE POINTER RULE for E and N (owner, 3 Nov 26): the register and the account's VOC are read AGAIN in edit.record; the file to be edited is judged by the kernel's geometry "
       "(the VOC file of the account, or the DICTIONARY path of the file pointer with its tokens expanded and made the account's when relative) BEFORE any pointer is written; an entry "
       "SDSYS's VOC already holds under that name that the page did not make is never overwritten; what the pointer opens is judged again (FL$PATH) before the IDE is given it; both refusals "
       "take the pointer away again; the audit line comes after both tests and before the hand-over",
       0 <= i_ck < i_guard < i_w < i_open < i_ck2 < i_aud < i_hand and "read arec from acc.f, ea else arec = ''" in er and "openpath ap.f : @ds : 'voc' to rvf else" in er
       and "tp = ap.f : @ds : 'voc'" in er and "tp = parse.pathname.tokens(trim(fr<3>))" in er and "if tp[1, 1] # '/' then tp = ap.f : @ds : tp" in er
       and "rp = fileinfo(tf, FL$PATH)" in er and er.count("gosub drop.pointer") == 4 and "if upcase(trim(fr<1>))[1, 1] # 'F' or trim(fr<3>) = '' then" in er
       and "in.ok = kernel(K$PATH.IN, ap.f : @fm : rp)" in er and "if in.ok then in.ok = kernel(K$PATH.IN, ap.f : @fm : rp : @ds : '%0')" in er
       and "if in.ok then in.ok = kernel(K$PATH.IN, ap.f : @fm : rp : @ds : '%1')" in er and "rt = fileinfo(tf, FL$TYPE)" in er and "if rt # rtw then" in er
       and "rtw = (if isprog then FL$TYPE.DIR else FL$TYPE.DH)" in er and at("if rt # rtw then", er) < i_aud and at("if not(in.ok) then", er) < i_aud
       and at("read arec from acc.f", er) < i_ck and "ap.f = parse.pathname.tokens(arec<1>)" in er and i_ck < at("gosub check.word") < i_w,
       "ck %d guard %d write %d open %d ck2 %d audit %d hand %d" % (i_ck, i_guard, i_w, i_open, i_ck2, i_aud, i_hand))
    ck("T15 the pointer and the sentence: the pointer is an F pointer holding THE PATH THAT WAS CHECKED (never a Q-pointer into the account's VOC, which is followed again at every open, "
       "after the check: the review of 3 Nov 26), both parts the dictionary for an item and no dictionary part for the VOC, named zm<user number>.<account>.<file> from words that passed "
       "check.word (a-z 0-9 . _ -, 1 to 63; and not creating.seqkey, which the IDE reads as a keyword); the sentence is 'ide' (with dict for an item) and the pointer's name and the id; "
       "hand.over refuses any other first word, takes the pointer away straight after the IDE ends and takes it away only if it is the one the page made",
       "qrec = 'F' : @fm : tp : @fm : (if efl = '' then '' else tp)" in er and "qn = 'zm' : @userno : '.' : ea : '.' : qf" in er and "ok2 = (okname and eid # 'creating.seqkey')" in er
       and "'Q'" not in er and "good = 'abcdefghijklmnopqrstuvwxyz0123456789._-'" in txt
       and "okname = (len(cw) > 0 and len(cw) <= 63)" in txt and er.count("gosub check.word") == 3 and "if not(ok1 and ok2 and okname) then" in er
       and "sent = 'ide ' : (if efl = '' then '' else 'dict ') : qn : ' ' : eid" in er
       and "if field(sent, ' ', 1) # 'ide' then" in ho and ho.find("execute sent\ngosub drop.pointer") > ho.find("if field(sent, ' ', 1) # 'ide' then")
       and "if qold = qrec then\ndelete svf, qn\nend" in txt)
    ck("T16 E and N keys: E edits the row under the cursor (a hit in the account it was found in), only from Entries; N refuses while a find is on and asks the id first; "
       "a new item or program needs a row to take the file from; the id is lower-cased and trimmed",
       "if pane # 2 then" in de and "if kind = 3 then" not in de and "ea = hacc<ec> ; eid = hid<ec> ; efl = hfile<ec>" in de and "ea = anm<ac> ; eid = enm<ec> ; efl = efile<ec>" in de and "enw = 0" in de
       and "if kind = 3 then" in dn and "if fnd # '' then" in dn and "efl = efile<ec>" in dn and "eid = downcase(trim(nt))" in dn and "enw = 1" in dn
       and "case nm = 'e'\ngosub do.edit" in txt and "case nm = 'n'\ngosub do.new" in txt)
    def at2(t):
        return dr.find(t)
    i_lk, i_cf, i_cancel, i_del, i_bad, i_daud = (at2("readu dold from tf, eid locked"), at2("call $tk_confirm(dsent, dlines, eid, res, cmsg, sysmsg(11953))"), at2("if res # 'run' then"),
                                                   at2("delete tf, eid on error delok = @false"), at2("if not(delok) then"), at2("void kernel(K$AUDIT, 'master delete account="))
    i_branch = at("if emode = 'delete' then\ngosub delete.reached\nreturn\nend")
    ck("T18 D (M3) goes E's whole way and only then deletes: do.delete takes the row as E does (Entries only, the programs refused, a hit in its own account) and calls edit.record with "
       "emode 'delete'; edit.record branches to delete.reached AFTER both refusals of the opened file and BEFORE E's audit line, and keeps tf open only for D; delete.reached takes the "
       "record's update lock (a held lock refuses), asks the confirm box with the id to be TYPED and the title 'Delete this record?' (11953), does nothing unless the answer is run, deletes "
       "through tf, gives the pointer back on each of its four ways out, and writes 'master delete' only after a delete that worked",
       "if pane # 2 then" in dd and "if kind = 3 then" in dd and "ea = hacc<ec> ; eid = hid<ec> ; efl = hfile<ec>" in dd and "ea = anm<ac> ; eid = enm<ec> ; efl = efile<ec>" in dd
       and "emode = 'delete'\ngosub edit.record" in dd and "emode = 'edit'\ngosub edit.record" in de and "emode = 'edit'\ngosub edit.record" in dn
       and at("if not(in.ok) then") < i_branch < i_aud and at("if rt # rtw then") < i_branch and "if emode # 'delete' then close tf" in er and "\nclose tf\n" not in er
       and 0 <= i_lk < i_cf < i_cancel < i_del < i_bad < i_daud and dr.count("gosub drop.pointer") == 4 and dr.count("close tf") == 4
       and 0 <= at2("dmsg = 'deleted ' : eid : ' from ' : dwhere") < at2("gosub read.all") and "msg = dmsg" in dr
       and "case nm = 'd'\ngosub do.delete" in txt and "call $tk_keys('menu', keys, 'delete', '&Entry', '&Delete the record', '', '')" in txt,
       "branch %d audit %d lock %d confirm %d cancel %d delete %d bad %d daudit %d" % (i_branch, i_aud, i_lk, i_cf, i_cancel, i_del, i_bad, i_daud))
    ide = code(helps.get("__ide__", ""))
    itxt = "\n".join(s for n, s in ide)
    imb = "\n".join(s for n, s in section(ide, "master.build:", "catalog.verified:"))
    idc = "\n".join(s for n, s in section(ide, "do.compile:", "master.build:"))
    irc = "\n".join(s for n, s in section(ide, "run.cmd:", "case cmd = 'menu'"))
    ck("T19 THE PROGRAMS (M4; the owner's mechanism C of 2 Nov 26: what must run inside an account goes through run.in).  The page: E and N take a program (no refusal of kind 3), "
       "edit.record judges the program file's DATA path (field 2) by the pointer rule, makes a data-only pointer, wants a DIRECTORY file, judges the program's own file and refuses a "
       "name that is a link leading nowhere, all before the compile branch and the audit; the IDE's sentence ends /in=account,file; C (do.build, programs only) goes through edit.record "
       "with emode 'compile', which gives the pointer back and calls compile.reached; that builds `run.in <account> basic <file> <id>` from checked words only, judges the compiler's "
       "success line, then audits 'master compile'.  The IDE: /in= is taken off the sentence and names the pointer file; do.compile of a tab of it runs run.in in the account and "
       "judges the success line, any other tab still runs basic; run.cmd sends Catalog, Run and Debug of such a tab to master.build BEFORE its case, which catalogues through run.in "
       "and refuses Run and Debug",
       "isprog = (kind = 3)" in er and "tp = parse.pathname.tokens(trim(fr<2>))" in er and "if isprog then qrec = 'F' : @fm : tp" in er and "if isprog then dfl = ''" in er
       and "if isprog and in.ok then in.ok = kernel(K$PATH.IN, ap.f : @fm : rp : @ds : eid)" in er
       and 0 <= at("if not(in.ok) then") < at("if emode = 'compile' then") < i_aud
       and re.search(r"if \(realpath\(work, resolved\) != NULL\)\s*break;\s*(/\*.*?\*/\s*)?if \(\(lstat\(work, &lst\) == 0\) && S_ISLNK\(lst\.st_mode\)\)\s*return FALSE;",
                     helps.get("__opsh__", ""), re.S) is not None
       and "if emode = 'compile' then\ngosub drop.pointer\ngosub compile.reached\nreturn\nend" in er
       and "if isprog then sent = 'ide ' : qn : ' ' : eid : ' /in=' : ea : ',' : efl" in er
       and "if kind # 3 then" in db and "emode = 'compile'\ngosub edit.record" in db and "ea = hacc<ec> ; eid = hid<ec> ; efl = hfile<ec>" in db and "case nm = 'c'\ngosub do.build" in txt
       and "csent = 'run.in ' : ea : ' basic ' : efl : ' ' : eid" in cr and "cok = (index(cout, 'Compiled 1 program(s) with no errors', 1) > 0)" in cr
       and 0 <= cr.find("execute csent capturing cout") < cr.find("void kernel(K$AUDIT, 'master compile account=")
       and "if downcase(in.last[1, 4]) = '/in=' then" in itxt and "in.ptr = downcase(field(sent.in, ' ', 2))" in itxt
       and "if in.good and convert('abcdefghijklmnopqrstuvwxyz0123456789._-', '', in.acct : in.file) # '' then in.good = @false" in itxt
       and "if in.ptr # '' and c.file = in.ptr then" in idc and "execute 'run.in ' : in.acct : ' basic ' : in.file : ' ' : c.id : c.opt capturing c.out" in idc
       and "c.ok = (index(c.out, 'Compiled 1 program(s) with no errors', 1) > 0)" in idc and "execute 'basic ' : qp.f : ' ' : qp.i : c.opt capturing c.out" in idc
       and "if bn<cb> = in.ptr and (cmd = 'catalog' or cmd = 'run' or cmd = 'debug' or cmd = 'debug1') then\ngosub master.build\nreturn" in irc
       and "execute 'run.in ' : in.acct : ' catalog ' : in.file : ' ' : c.id capturing co" in imb and "if cmd = 'run' then" in imb and "execute 'catalog" not in imb,
       "ide %d chars, mb %d, dc %d, rc %d" % (len(itxt), len(imb), len(idc), len(irc)))
    sw = "\n".join(s for n, s in section(lines, "sweep.pointers:", "drop.pointer:"))
    ck("T17 a pointer left by a session killed inside the IDE is swept when the page starts: right after the start's audit line, before anything is read, only names that begin "
       "zm<this user number>. and only an F or a Q record",
       "void kernel(K$AUDIT, 'tool start app=tool.entries')\ngosub sweep.pointers\n" in txt and txt.find("gosub sweep.pointers") < txt.find("gosub read.all")
       and "sw.pre = 'zm' : @userno : '.'" in sw and "if sw.id[1, len(sw.pre)] = sw.pre then" in sw and "if sw.r<1> = 'F' or sw.r<1> = 'Q' then" in sw)
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
    with open(IDE, encoding="utf-8", errors="replace") as f:
        helps["__ide__"] = f.read()          # M4: the IDE's half of the hand-over (T19); a mutant of kind "ide" changes it
    with open(OPSH, encoding="utf-8", errors="replace") as f:
        helps["__opsh__"] = f.read()         # M4: the kernel's resolve_name refuses a link that leads nowhere (T19); kind "opsh"
    return src, voc, helps


MUTANTS = [
    ("the page writes", "src", "                  gosub classify\n                  locate id in ckey<1> by 'AL' setting lp else\n", "                  gosub classify\n                  delete vf, id\n                  locate id in ckey<1> by 'AL' setting lp else\n"),
    ("the page runs a command", "src", "   void kernel(K$AUDIT, 'tool start app=tool.entries')\n", "   void kernel(K$AUDIT, 'tool start app=tool.entries')\n   execute 'x'\n"),
    ("the page is not the administrator's", "src", "call $tk_open('tool.entries', 'admin', ctx, err)", "call $tk_open('tool.entries', '', ctx, err)"),
    ("the find runs at the start", "src", "   if fnd # '' then gosub run.find\n", "   gosub run.find\n"),
    ("the dict gate reads the programs field", "src", "gset := (if upcase(trim(arec<ACC$DICT.EDIT>)) = 'YES' then 'd' else '-')", "gset := (if upcase(trim(arec<ACC$BP.EDIT>)) = 'YES' then 'd' else '-')"),
    ("SDSYS is listed", "src", "         if id # 'sdsys' then", "         if id # '' then"),
    ("the find is not cut", "src", "            if hn >= MAXV then", "            if 0 then"),
    ("another key row", "src", "   call $tk_keys('add', keys, 'f5', 'refresh', 'refresh', '', 1)\n", "   call $tk_keys('add', keys, 'f5', 'refresh', 'refresh', '', 1)\n   call $tk_keys('add', keys, 'd', 'delete', 'delete', '', 1)\n"),
    ("a third file is opened", "src", "   openpath @sdsys:@ds:'accounts' to acc.f then\n", "   openpath @sdsys:@ds:'batch.jobs' to bj.f then\n      close bj.f\n   end\n   openpath @sdsys:@ds:'accounts' to acc.f then\n"),
    ("a dictionary item is matched by its id only", "src", " or index(upcase(dhead), upcase(pat), 1) > 0)", ")"),
    ("a relative dictionary path is not made from the account", "src", "      if dp[1, 1] # '/' then dp = apath<ca> : @ds : dp\n", ""),
    ("the tokens of a dictionary path are not expanded", "src", "      dp = parse.pathname.tokens(dpaths<fi>)", "      dp = dpaths<fi>"),
    ("the outside test is lost", "src", "is.out = (if kernel(K$PATH.IN, apath<ca> : @fm : tp) then 0 else 1)", "is.out = 0"),
    ("the outside test is a text prefix", "src", "is.out = (if kernel(K$PATH.IN, apath<ca> : @fm : tp) then 0 else 1)", "is.out = (if tp[1, len(apath<ca>)] = apath<ca> then 0 else 1)"),
    ("dictionary items are not marked", "src", "                        ins doutf before cout<lp>\n", ""),
    ("a Q-pointer to another account is not marked", "src", "         coutf = (if downcase(trim(r<2>)) = downcase(anm<ca>) then 0 else 1)\n", "         coutf = 0\n"),
    ("a remote item is not marked", "src", "      case cty = 'R'\n         coutf = 1\n", ""),
    ("K keeps the filter", "src", "   if kind > 3 then kind = 1\n   fnd = '' ; filt = ''\n", "   if kind > 3 then kind = 1\n"),
    ("K stops at the dictionaries", "src", "   if kind > 3 then kind = 1\n", "   if kind > 2 then kind = 1\n"),
    ("a .out file is a program file", "src", "               if not(len(tl) > 4 and tl[len(tl) - 3, 4] = '.out') then\n", "               if 1 then\n"),
    ("the .out file beside a program file is not looked for", "src", "            op2 = pp : '.out'", "            op2 = ''"),
    ("a program is built only if its case matches", "src", "         onames = downcase(onames)\n", ""),
    ("a program file that is not a directory is read", "src", "            if fileinfo(pfv, FL$TYPE) = FL$TYPE.DIR then\n", "            if 1 then\n"),
    ("a program file outside the account is not marked", "src", "                           ins poutf before cout<lp>\n", "                           ins 0 before cout<lp>\n"),
    ("a dictionary is written", "src", "                  read dr from df2, eid then\n", "                  read dr from df2, eid then\n                     write dr to df2, eid\n"),
    ("the outside test of E is lost", "src", "   if not(kernel(K$PATH.IN, ap.f : @fm : tp)) then\n", "   if 0 then\n"),
    ("the outside test of E is a text prefix", "src", "   if not(kernel(K$PATH.IN, ap.f : @fm : tp)) then\n", "   if tp[1, len(ap.f)] # ap.f then\n"),
    ("the pointer's target is not judged again", "src", "   in.ok = kernel(K$PATH.IN, ap.f : @fm : rp)\n", "   in.ok = 1\n"),
    ("the subfiles are not judged", "src", "   if in.ok then in.ok = kernel(K$PATH.IN, ap.f : @fm : rp : @ds : '%0')\n", ""),
    ("a file that is not hashed is handed over", "src", "   if rt # rtw then\n", "   if 0 then\n"),
    ("a program file need not be a directory file", "src", "   rtw = (if isprog then FL$TYPE.DIR else FL$TYPE.DH)", "   rtw = (if isprog then rt else FL$TYPE.DH)"),
    ("the pointer is a Q-pointer into the account's VOC again", "src", "qrec = 'F' : @fm : tp : @fm : (if efl = '' then '' else tp)", "qrec = 'Q' : @fm : ea : @fm : qf"),
    ("creating.seqkey is handed to the IDE", "src", "   ok2 = (okname and eid # 'creating.seqkey')", "   ok2 = okname"),
    ("no sweep at the start", "src", "   gosub sweep.pointers\n", ""),
    ("the sweep takes every user's pointers", "src", "   sw.pre = 'zm' : @userno : '.'\n", "   sw.pre = 'zm'\n"),
    ("a foreign entry of SDSYS's VOC is overwritten", "src", "      if qold # qrec then\n", "      if 0 then\n"),
    ("the pointer is left after the IDE", "src", "   execute sent\n   gosub drop.pointer\n", "   execute sent\n"),
    ("the page runs anything", "src", "   if field(sent, ' ', 1) # 'ide' then\n", "   if 0 then\n"),
    ("the data path is judged for an item", "src", "      tp = parse.pathname.tokens(trim(fr<3>))\n", "      tp = parse.pathname.tokens(trim(fr<2>))\n"),
    ("E refuses the programs again", "src", "   if pane # 2 then\n      msg = 'Tab to the entries first, then E'\n      return\n   end\n",
     "   if pane # 2 then\n      msg = 'Tab to the entries first, then E'\n      return\n   end\n   if kind = 3 then\n      return\n   end\n"),
    ("a program's own file is not judged", "src", "   if isprog and in.ok then in.ok = kernel(K$PATH.IN, ap.f : @fm : rp : @ds : eid)", "   in.ok = in.ok"),
    ("a link that leads nowhere is judged a new name (kernel)", "opsh", "    if ((lstat(work, &lst) == 0) && S_ISLNK(lst.st_mode))\n      return FALSE;\n", ""),
    ("the program pointer reaches a dictionary", "src", "   if isprog then qrec = 'F' : @fm : tp ", "   if isprog then qrec = qrec "),
    ("C compiles without the checks", "src", "   emode = 'compile'\n   gosub edit.record\n", "   gosub compile.reached\n"),
    ("C is judged on nothing", "src", "   cok = (index(cout, 'Compiled 1 program(s) with no errors', 1) > 0)", "   cok = 1"),
    ("the IDE compiles a master tab here in SDSYS", "ide", "   if in.ptr # '' and c.file = in.ptr then\n", "   if 0 then\n"),
    ("the IDE runs a master tab", "ide", "(cmd = 'catalog' or cmd = 'run' or cmd = 'debug' or cmd = 'debug1')", "(cmd = 'catalog')"),
    ("the IDE catalogues a master tab here in SDSYS", "ide", "execute 'run.in ' : in.acct : ' catalog ' : in.file : ' ' : c.id capturing co", "execute 'catalog ' : in.file : ' ' : c.id capturing co"),
    ("the IDE takes an account name with any character", "ide", "      if in.good and convert('abcdefghijklmnopqrstuvwxyz0123456789._-', '', in.acct : in.file) # '' then in.good = @false\n", ""),
    ("N works during a find", "src", "   if fnd # '' then\n      msg = 'Esc takes the find off first: a new record is made in the account selected in Accounts'\n      return\n   end\n", ""),
    ("the register is not read again", "src", "   read arec from acc.f, ea else arec = ''\n", "   arec = 'x'\n"),
    ("the pointer holds an unchecked path", "src", "qrec = 'F' : @fm : tp : @fm : (if efl = '' then '' else tp)", "qrec = 'F' : @fm : ap.f : @fm : (if efl = '' then '' else tp)"),
    ("the audit line is lost", "src", "   void kernel(K$AUDIT, 'master edit account=' : ea : ' kind=' : akind : ' file=' : qf : ' id=' : eid : ' new=' : enw)\n", ""),
    ("a slash is a word character", "src", "   good = 'abcdefghijklmnopqrstuvwxyz0123456789._-'\n   for cwq", "   good = 'abcdefghijklmnopqrstuvwxyz0123456789._-/'\n   for cwq"),
    ("E works in Accounts", "src", "   if pane # 2 then\n      msg = 'Tab to the entries first, then E'\n      return\n   end\n", ""),
    ("the pointer is left when SD cannot follow it", "src", "   open dfl, qn to tf else\n      gosub drop.pointer\n", "   open dfl, qn to tf else\n"),
    ("D deletes without the id typed", "src", "call $tk_confirm(dsent, dlines, eid, res, cmsg, sysmsg(11953))", "call $tk_confirm(dsent, dlines, '', res, cmsg, sysmsg(11953))"),
    ("D deletes on Cancel", "src", "   if res # 'run' then\n      close tf", "   if 0 then\n      close tf"),
    ("D ignores another session's lock", "src", "   readu dold from tf, eid locked\n", "   read dold from tf, eid locked\n"),
    ("D has no branch (it would audit an edit and open the IDE)", "src", "   if emode = 'delete' then\n      gosub delete.reached\n      return\n   end\n", ""),
    ("D deletes through a second open", "src", "   if emode # 'delete' then close tf", "   close tf"),
    ("the pointer is left after a delete", "src", "   delete tf, eid on error delok = @false\n   close tf\n   gosub drop.pointer\n", "   delete tf, eid on error delok = @false\n   close tf\n"),
    ("the delete's message is made after the redraw", "src", "   dmsg = 'deleted ' : eid : ' from ' : dwhere\n", ""),
    ("a program is deleted", "src", "   if kind = 3 then\n      msg = 'the programs are not deleted from this page yet'\n      return\n   end\n", ""),
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
        elif kind in ("ide", "opsh"):
            key = "__%s__" % kind
            if h[key].count(old) != 1:
                print("  [CANNOT] %-48s the text occurs %d times in %s" % (name, h[key].count(old), kind))
                missed += 1
                continue
            h[key] = h[key].replace(old, new)
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
