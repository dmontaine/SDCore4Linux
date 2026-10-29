#!/usr/bin/env python3
"""test-idekinds-units.py - the IDE's record kinds and locks (the editor merge, stage B; ~/Documents/Audits/TUI/Opus_TUI_Plan.txt section 11), read off the source as text.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-idekinds-units.py
  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-idekinds-units.py --selftest

No sudo, no install, no sd.  Exit 0 every check passed, 1 a check failed, 2 it could not run.

START-HISTORY:
28 Oct 26 dm  New with stage B.
END-HISTORY

WHAT IT HOLDS (gpl.bp/ide).  `ide dict file id` and `ide voc id` start on a dictionary item or a VOC record; CREATING.SEQKEY in the place of the id takes the file's
next sequential id ($seqkey, after the account's edit gate), and the same word in quotes is a record of that name.  A file's records are listed by SELECT and READNEXT
stopped at MAXREC, never by an SSELECT of the whole file (the tree, Find in the records, a select list at the start).  The tree has a dictionary node under a file that
has a dictionary, and its items are read only when it is opened.  A record is opened under its lock (lock.take: READU through a file variable the tab keeps in tfv, the
LOCKED clause naming the holder by STATUS()), a collection file's record is refused BEFORE any read of it, a record another session holds opens read-only and cannot
be changed or saved, and a record that is not there opens as a new one only where the caller asked for it and only after the account's edit gate.  A tab that holds
its lock saves with WRITEU through that file variable and never RELEASEs it; closing a tab, every way out of the IDE, Save as and a Cancel give locks back; the screen
taken back from a program takes them again (RECORDLOCKU ... LOCKED).  The token form follows the kind (test-recarr-units.py I11-I14).  Every write asks edit.check on
the open file's own path.  A dictionary item is not compiled.

***IT RUNS NOTHING, SO IT CANNOT SAY THAT A LOCK IS HELD OR A GATE REFUSES***: that is sandbox-ide-kinds.py (a second live session holding a lock, an ordinary account
with dict-off, the disk as the evidence).  --selftest breaks each property the way an edit plausibly would and requires a check to notice.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SDSYS = os.path.normpath(os.path.join(HERE, "..", "sdsys"))
GPL = os.path.join(SDSYS, "gpl.bp")
MSG = os.path.join(SDSYS, "messages")
NEWMSG = list(range(11684, 11699))


def strip(src):
    """the code without comment lines and trailing ;* comments"""
    out = []
    for ln in src.split("\n"):
        if ln.lstrip().startswith("*"):
            continue
        out.append(re.sub(r"\s*;\*.*$", "", ln))
    return "\n".join(out)


def label(text, name):
    """the body of internal subroutine `name:` up to the next label at the start of a line"""
    m = re.search(r"^%s:\n" % re.escape(name), text, re.M)
    if not m:
        return ""
    rest = text[m.end():]
    n = re.search(r"^[a-z][a-z0-9.]*:\s*$", rest, re.M)
    return rest[:n.start()] if n else rest


def ordered(text, *parts):
    pos = -1
    for p in parts:
        i = text.find(p, pos + 1)
        if i < 0:
            return False
        pos = i
    return True


def before(text, a, b):
    i, j = text.find(a), text.find(b)
    return 0 <= i < j


def load():
    src = {}
    try:
        with open(os.path.join(GPL, "ide"), encoding="latin-1") as f:
            src["ide"] = f.read()
    except OSError:
        src["ide"] = ""
    for n in NEWMSG + [11215, 11226]:
        try:
            with open(os.path.join(MSG, str(n)), encoding="latin-1") as f:
                src["m%d" % n] = f.read()
        except OSError:
            src["m%d" % n] = ""
    return src


def checks(src):
    rows = []

    def ck(i, what, ok, detail=""):
        rows.append((i, what, bool(ok), detail))

    raw = src["ide"]
    ide = strip(raw)
    L = {n: label(ide, n) for n in ("load.file", "load.dict", "list.ids", "do.find", "tree.nodes", "do.act", "lock.take", "lock.free", "tab.unlock", "release.all",
                                     "tab.lock", "relock.all", "ro.check", "open.record", "save.one", "close.current", "retake.quiet", "do.saveas", "do.writeas",
                                     "seq.take", "do.new", "open.select", "do.compile", "do.sed", "do.include", "kind.of", "dict.trim", "load.current", "new.form",
                                     "do.replace", "do.fields", "ai.apply", "edit.check", "name.untitled", "add.new.record", "tab.find", "status.line")}
    head = ide[: ide.find("gosub open.screen")]
    main = ide[: ide.find("apply.theme:")]
    ck("K0", "NULL CASE: the IDE was read and every routine this check reads is there (a check on nothing would pass)",
       len(ide) > 60000 and all(len(v) > 20 for v in L.values()), repr(sorted(k for k, v in L.items() if len(v) <= 20)))

    # ---- the start ----------------------------------------------------------------------------------------------------------------------------------------------------
    ck("K1", "the start form: a first word DICT sets the dictionary flag and moves the file and the id one word on; CREATING.SEQKEY (unquoted, any case) is seq0; an id in "
       "quotes loses them (so \"creating.seqkey\" is a record of that name); the file name is lower case",
       ordered(head, "dflag0 = ''", "if upcase(fn0) = 'DICT' then", "dflag0 = 'DICT'", "fn0 = field(@sentence, ' ', 3)", "id0 = field(@sentence, ' ', 4)",
               "fn0 = downcase(fn0)", "seq0 = (upcase(id0) = 'CREATING.SEQKEY')", "id0 = id0[2, len(id0) - 2]"), "")
    st = main[main.find("gosub new.form\n   begin case"):]
    ck("K2", "the start opens: CREATING.SEQKEY through seq.take and then a NEW record of that id; a named record with or.mknew = 1 (a record that is not there is a new one) and the "
       "dictionary flag; an active select list through open.select; the editor is never left without a buffer",
       ordered(st, "case fn0 # '' and seq0", "gosub seq.take", "if sq.id # '' then", "or.dict = dflag0", "or.mknew = 1", "gosub open.record",
               "case fn0 # '' and id0 # ''", "or.dict = dflag0", "or.mknew = 1", "gosub open.record", "case sel0 # ''", "gosub open.select", "if nbuf = 0 then", "gosub add.untitled"), "")
    ck("K3", "an active select list is read from list 0 BEFORE build.files, by READNEXT stopped at MAXREC (not READLIST, which would finish a list still being made), and then cleared",
       ordered(main, "if selectinfo(0, SL$ACTIVE) then", "readnext sel.id from 0 else exit", "if sel0.n >= MAXREC then", "clearselect 0", "gosub build.files")
       and "readlist" not in main[: main.find("gosub build.files")], "")
    ck("K4", "open.select lists every id read in the table (Return opens one, with the dictionary flag) and opens at most MAXSEL of them in tabs",
       ordered(L["open.select"], "for os.i = 1 to os.n", "sid<-1> = sel0<os.i>", "out.dict = dflag0", "gosub err.load", "if os.open > MAXSEL then os.open = MAXSEL",
               "for os.i = 1 to os.open", "or.dict = dflag0", "gosub open.record")
       and "or.dict = out.dict" in label(ide, "act.error"), "")

    # ---- bounded listing ------------------------------------------------------------------------------------------------------------------------------------------------
    li = L["list.ids"]
    ck("K5", "list.ids: SELECT fv TO 9 (made a group at a time) with ON ERROR, READNEXT stopped once MAXREC ids are read (lr.more), the ids put in order, and CLEARSELECT 9 at "
       "the end so a part-read select does not stay on the file",
       ordered(li, "select fv to 9 on error", "clearselect 9", "return", "loop", "readnext lr.id from 9 else exit", "if lr.n >= MAXREC then", "lr.more = @true", "exit",
               "locate lr.id in lr.ids<1> by 'AL' setting lr.p else null", "ins lr.id before lr.ids<1, lr.p>", "repeat", "clearselect 9")
       and "sselect" not in li and "readlist" not in li, li[:200])
    ck("K6", "NO SSELECT AND NO READLIST OF A WHOLE FILE ANYWHERE in the IDE but the VOC walk of build.files: the tree (load.file, load.dict) and Find in the records (do.find) "
       "read through list.ids, and say when the list was cut (11219)",
       len(re.findall(r"^\s*sselect\b", ide, re.M)) == 1 and "sselect vocf to 9" in label(ide, "build.files")
       and all("gosub list.ids" in L[n] for n in ("load.file", "load.dict", "do.find"))
       and all("sselect" not in L[n] and "readlist" not in L[n] for n in ("load.file", "load.dict", "do.find"))
       and all("sysmsg(11219" in L[n] for n in ("load.file", "load.dict", "do.find")), "")
    ck("K7", "Find in the records refuses a collection file (11698) before it reads a record",
       ordered(L["do.find"], "if fileinfo(fv, FL$COLLECTION) then", "msg = sysmsg(11698, ctx.file)", "return", "gosub list.ids", "read r from fv"), "")

    # ---- the tree ---------------------------------------------------------------------------------------------------------------------------------------------------------
    tn = L["tree.nodes"]
    ck("K8", "the tree: a file that has a dictionary (ldict) gets a node of its own (11693, code D:), its items at depth 3 (code Q:) only once that dictionary is listed (dfiles)",
       ordered(tn, "if ldict<lp> then", "nodes<-1> = sysmsg(11693) : @sm : 2 : @sm : 'D:' : nm", "if dp then", "c2 = 'Q:' : nm : ':' : dids<1, j>",
               "nodes<-1> = dids<1, j> : @sm : 3 : @sm : c2", "ids = lrecs<lp>")
       and ordered(L["load.file"], "open 'DICT', lf.name to lf.dv then lf.dict = 1") and "del ldict<lp>" in L["do.act"], "")
    da = L["do.act"]
    ck("K9", "Return on the dictionary node reads its items THEN (load.dict, lazily) or closes it; Return on an item opens it with the dictionary flag",
       ordered(da, "case code[1, 2] = 'D:'", "gosub load.dict", "case code[1, 2] = 'R:' or code[1, 2] = 'Q:'", "if code[1, 2] = 'Q:' then or.dict = 'DICT'", "gosub open.record")
       and "open 'DICT', ld.name to fv" in L["load.dict"], "")

    # ---- the lock -----------------------------------------------------------------------------------------------------------------------------------------------------------
    lt = L["lock.take"]
    ck("K10", "lock.take opens the file WITH the dictionary flag, refuses a collection file (11684) BEFORE any read, and finds a free slot (11690 when there is none)",
       ordered(lt, "open lk.dict, lk.file to fv else", "if fileinfo(fv, FL$COLLECTION) then", "lk.err = sysmsg(11684, lk.name, lk.id)", "return", "gosub kind.of",
               "if tused<lk.s> = '' then exit", "lk.err = sysmsg(11690)", "tfv(lk.s) = fv", "readu ")
       and lt.find("FL$COLLECTION") < lt.find("readu ") and lt.find("FL$COLLECTION") < lt.find("read lk.rec"), "")
    ck("K11", "lock.take reads with READU THROUGH THE TAB'S OWN FILE VARIABLE tfv(slot), ON ERROR; LOCKED takes the holder from STATUS() and reads without a lock (read-only); the "
       "slot is kept only when this session got the lock, otherwise the file variable is let go",
       ordered(lt, "readu lk.rec from tfv(lk.s), lk.id on error", "end locked", "lk.owner = status()", "read lk.rec from tfv(lk.s), lk.id then", "end then", "lk.got = @true",
               "end else", "lk.got = @true", "if lk.got then", "lk.slot = lk.s", "tused<lk.s> = 1", "end else", "tfv(lk.s) = 0"), "")
    orc = L["open.record"]
    ck("K12", "open.record takes or.dict and or.mknew at its first statements and puts them back ('' and 0) before anything else is called, and looks for the record's tab by "
       "file, id AND dictionary flag",
       ordered(orc, "od = or.dict", "omk = or.mknew", "or.dict = ''", "or.mknew = 0", "tf.dict = od", "gosub tab.find") and orc.find("or.mknew = 0") < orc.find("gosub ")
       and "bx{tf.k} = tf.dict" in L["tab.find"], "")
    ck("K13", "open.record: the lock first; a record that is not there and that another session is making is refused (11686); with or.mknew the account's edit gate is asked BEFORE "
       "a tab is made (refused: the lock given back, the reason in a box), else 'not found' (11201) and the lock given back",
       ordered(orc, "gosub lock.take", "if lk.err # '' then", "if not(lk.exists) then", "if lk.owner # '' then", "msg = sysmsg(11686, or.name, or.id, lk.owner)", "return",
               "gosub rc.offer", "case omk", "gosub edit.check", "if not(edit.ok) then", "gosub lock.free", "gosub refuse.box", "return", "case 1", "gosub lock.free",
               "msg = sysmsg(11201, or.id, or.name)", "return", "nbuf += 1"), "")
    ck("K14", "open.record keeps the lock with the tab (tab.state: kind, dictionary flag, slot, owner) and says a read-only open (11689)",
       ordered(orc, "ts.kind = lk.kind", "ts.dict = od", "ts.slot = lk.slot", "ts.owner = lk.owner", "gosub tab.state", "msg = sysmsg(11689, or.name, or.id, lk.owner)")
       and ordered(L["tab.state"] if "tab.state" in L else label(ide, "tab.state"), "k = 'l' : uid", "bx{k} = ts.slot", "k = 'o' : uid", "bx{k} = ts.owner"), "")
    so = L["save.one"]
    ck("K15", "save.one: a read-only tab is refused first (ro.check); a tab holding its lock uses fv = tfv(slot), ITS OWN file variable, and writes with WRITEU, with no RELEASE "
       "on that path; a tab with none opens the file with its dictionary flag, writes and releases",
       ordered(so, "gosub ro.check", "if not(ro.ok) then", "gosub refuse.box", "return", "if bi<sv.i> = '' then", "sv.slot = bx{k} + 0", "if sv.slot then", "fv = tfv(sv.slot)",
               "end else", "open sv.dict, bn<sv.i> to fv else", "gosub edit.check", "readu disk from fv, sv.id locked", "if sv.slot then",
               "writeu sv.text on fv, sv.id on error", "end else", "write sv.text on fv, sv.id on error", "release fv, sv.id")
       and "release" not in so[so.find("writeu sv.text"): so.find("end else", so.find("writeu sv.text") + 1) + 10]
       and "if not(sv.slot) then release fv, sv.id" in so, "")
    ck("K16", "save.one compares a dictionary item with the disk record trimmed the same way (dict.trim: an A, C, I or S item without its compiled code from DICT.SYS.INFO on)",
       ordered(so, "if sv.kind = 'dict' then", "gosub dict.trim", "if disk # sv.saved then")
       and "dt.rec = trim(field(dt.rec, @fm, 1, DICT.SYS.INFO - 1), @fm, 'T')" in L["dict.trim"] and "$include dictdict.h" in raw
       and ordered(orc, "if lk.kind = 'dict' then", "gosub dict.trim"), "")
    ck("K17", "the locks are given back: tab.unlock RELEASEs through the tab's file variable and frees the slot; Close calls it before the tab goes; release.all runs for every tab "
       "before the screen is closed at the end; a Cancel in open.record gives back (lock.free)",
       ordered(L["tab.unlock"], "tu.s = bx{tu.k} + 0", "if tu.s then", "release tfv(tu.s), bi<tu.i>", "tfv(tu.s) = 0", "tused<tu.s> = ''", "bx{tu.k} = 0")
       and ordered(L["close.current"], "gosub tab.unlock", "del bn<cb>")
       and ordered(L["release.all"], "for tu.i = 1 to nbuf", "gosub tab.unlock")
       and ordered(ide, "until done\n   repeat", "gosub release.all", "screen close")
       and ordered(L["lock.free"], "release tfv(lk.slot), lk.id", "tfv(lk.slot) = 0", "tused<lk.slot> = ''"), "")
    ck("K18", "the screen taken back from a program (retake.quiet: Run, Debug, SED, CED) takes the locks again BEFORE the form is made, with RECORDLOCKU ... LOCKED through the tab's "
       "file variable; one another session took makes the tab read-only (11692)",
       ordered(L["retake.quiet"], "gosub open.screen", "gosub relock.all", "gosub new.form")
       and ordered(L["relock.all"], "recordlocku tfv(rl.s), bi<rl.i> locked", "rl.lost = @true", "rl.owner = status()", "if rl.lost then", "tused<rl.s> = ''", "bx{k} = rl.owner",
                   "msg = sysmsg(11692"), "")
    ck("K19", "Save as lets go of the old record's lock, clears read-only and the dictionary flag, and takes the new record's lock; a record open in another tab is refused (11691) "
       "by Save as, Write a copy, New record and the first save of an untitled buffer",
       ordered(L["do.saveas"], "gosub tab.find", "msg = sysmsg(11691, sa.file, sa.id)", "gosub tab.unlock", "k = 'o' : u", "bx{k} = ''", "k = 'd' : u", "bx{k} = ''", "gosub tab.lock",
               "gosub save.one")
       and all("sysmsg(11691" in L[n] and "gosub tab.find" in L[n] for n in ("do.writeas", "do.new", "name.untitled"))
       and ordered(L["name.untitled"], "gosub tab.find", "bn<sv.i> = nm.file", "gosub tab.lock"), "")
    ck("K20", "a read-only tab: the memo is readonly while bx o is set (load.current, new.form); Replace, Edit as fields and an AI edit refuse it (ro.check), the status line "
       "names the holder (11687)",
       "ro = (bx{k} # '')" in L["load.current"] and "ed.ro = (bx{k} # '')" in L["new.form"]
       and all(ordered(L[n], "ro.i = cb", "gosub ro.check", "if not(ro.ok) then return") for n in ("do.replace", "do.fields", "ai.apply"))
       and "sysmsg(11687, bx{k})" in L["status.line"] and "msg = sysmsg(11688, bf.name, bf.id, bx{ro.k})" in L["ro.check"], "")

    # ---- the gates, seqkey, compile, SED, include -----------------------------------------------------------------------------------------------------------------------
    ck("K21", "edit.check asks the kernel on the OPEN file's own path (K$EDIT.OK with fileinfo(fv, FL$PATH)); every way to write asks it: save.one, Write a copy, CREATING.SEQKEY "
       "before the id is taken, and a new record named on the command line before its tab",
       ordered(L["edit.check"], "edit.p = fileinfo(fv, FL$PATH)", "if kernel(K$EDIT.OK, edit.p) then return")
       and ordered(L["do.writeas"], "open wa.file to fv else", "gosub edit.check", "write wa.text on fv")
       and ordered(L["seq.take"], "open sq.dict, sq.file to fv else", "gosub edit.check", "if not(edit.ok) then", "return", "call $seqkey(fv, @true, sq.id, sq.why)")
       and ordered(L["save.one"], "gosub edit.check", "write"), "")
    ck("K22", "New record: CREATING.SEQKEY (any case) takes the next sequential id through seq.take; in quotes it is a record of that name",
       ordered(L["do.new"], "if upcase(nm.id) = 'CREATING.SEQKEY' then", "gosub seq.take", "if sq.id = '' then return", "nm.id = sq.id", "end else",
               "nm.id = nm.id[2, len(nm.id) - 2]", "gosub add.new.record"), "")
    ck("K23", "New record locks the new record for its creation after the recovery copy's question, and refuses one that is now there (11217) or being made (11686)",
       ordered(L["add.new.record"], "gosub rc.offer", "if rc.choice = 'cancel' then return", "gosub lock.take", "if lk.exists then", "gosub lock.free",
               "msg = sysmsg(11217, nm.id, nm.file)", "if lk.owner # '' then", "msg = sysmsg(11686", "nbuf += 1", "ts.slot = lk.slot", "gosub tab.state"), "")
    ck("K24", "a dictionary item is not compiled (11697, after the save, before BASIC is run), and SED is given DICT for one",
       ordered(L["do.compile"], "gosub save.current", "if bx{k} = 'dict' then", "msg = sysmsg(11697, c.file, c.id)", "return", "execute 'basic '")
       and ordered(L["do.sed"], "sd.dict = bx{k}", "if sd.dict # '' then qp.f = 'dict ' : qp.f", "execute 'sed '", "open sd.dict, sd.file to fv then"), "")
    di = L["do.include"]
    ck("K25", "Open the include: the first word is $include (a comment after ; is cut), one word looks in the tab's file and then syscom, two words name the file; a collection file "
       "is passed over before a read; not found says where it looked (11696); found opens it through open.record",
       ordered(di, "in.line = trim(field(in.line, ';', 1))", "if downcase(field(in.line, ' ', 1)) # '$include' then", "msg = sysmsg(11695)", "case in.n = 2", "in.files = bn<cb>",
               "in.files<-1> = 'syscom'", "case in.n = 3", "in.files = field(in.line, ' ', 2)", "if fileinfo(fv, FL$COLLECTION) then continue", "read in.x from fv, in.rec on error",
               "msg = sysmsg(11696", "gosub open.record"), "")
    ko = L["kind.of"]
    ck("K26", "kind.of: dict for the dictionary flag, voc / dict / source from the kernel's own edit kind of the open file's path, source for a directory file, data otherwise",
       ordered(ko, "ko.kind = 'data'", "if ko.dict # '' then", "ko.kind = 'dict'", "ko.ek = kernel(K$EDIT.KIND, fileinfo(fv, FL$PATH))", "case ko.ek = 1", "ko.kind = 'voc'",
               "case ko.ek = 2", "ko.kind = 'dict'", "case ko.ek = 3", "ko.kind = 'source'", "case fileinfo(fv, FL$TYPE) = FL$TYPE.DIR", "ko.kind = 'source'"), "")
    ck("K27", "the file variables of the locks: dim tfv(MAXLOCK) at the start, every slot 0, no slot in use",
       ordered(head, "MAXLOCK = 100", "dim tfv(MAXLOCK)", "mat tfv = 0", "tused = ''"), "")

    # ---- messages -----------------------------------------------------------------------------------------------------------------------------------------------------------
    miss = [n for n in NEWMSG if not src["m%d" % n].strip()]
    want = {11684: "%2", 11685: "%2", 11686: "%3", 11687: "%1", 11688: "%3", 11689: "%3", 11691: "%2", 11692: "%3", 11694: "%2", 11696: "%2", 11697: "%2", 11698: "%1"}
    bad = [n for n, p in want.items() if p not in src["m%d" % n]]
    cited = [n for n in NEWMSG if ("sysmsg(%d" % n) not in ide]
    ck("K28", "messages 11684-11698 are there, each takes the substitutions the IDE passes, and the IDE cites every one of them",
       not miss and not bad and not cited, repr((miss, bad, cited)))
    ck("K29", "the help names the locks and the include; the Go menu has Open the include",
       "Locks" in src["m11215"] and "read-only" in src["m11215"] and "Open the include" in src["m11215"] and "&Open the include~~include" in src["m11226"], "")
    return rows


def sub(key, old, new):
    def f(src):
        r = dict(src)
        if old not in r[key]:
            raise KeyError("%s: %r is not in the file, so the mutant cannot be made" % (key, old[:80]))
        r[key] = r[key].replace(old, new, 1)
        return r
    return f


MUTANTS = [
    ("the DICT word is not read", "K1", sub("ide", "   if upcase(fn0) = 'DICT' then\n      dflag0 = 'DICT'", "   if upcase(fn0) = 'DICTX' then\n      dflag0 = 'DICT'")),
    ("a quoted id keeps its quotes", "K1", sub("ide", "then id0 = id0[2, len(id0) - 2]", "then null")),
    ("a named record that is not there is 'not found' again", "K2", sub("ide", "         or.mknew = 1                          ;* 28 Oct 26 (stage B): a record that is not there", "         null                          ;* 28 Oct 26 (stage B): a record that is not there")),
    ("the select list is read whole", "K3", sub("ide", "            readnext sel.id from 0 else exit\n", "            readlist sel0 from 0 else exit\n")),
    ("the select list is not bounded", "K3", sub("ide", "            if sel0.n >= MAXREC then\n               sel0.more = @true", "            if 0 then\n               sel0.more = @true")),
    ("every listed record opens in a tab", "K4", sub("ide", "   if os.open > MAXSEL then os.open = MAXSEL\n", "")),
    ("the tree sorts the whole file again", "K6", sub("ide", "   gosub list.ids\n   if lr.more then msg = sysmsg(11219, MAXREC, lf.name)", "   sselect fv to 9\n   readlist lr.ids from 9 else lr.ids = ''\n   if lr.more then msg = sysmsg(11219, MAXREC, lf.name)")),
    ("list.ids does not stop", "K5", sub("ide", "      if lr.n >= MAXREC then\n         lr.more = @true\n         exit\n      end\n", "")),
    ("list.ids leaves the select open", "K5", sub("ide", "   repeat\n   clearselect 9                       ;* a select left part read", "   repeat\n   null                       ;* a select left part read")),
    ("Find reads a collection file", "K7", sub("ide", "   if fileinfo(fv, FL$COLLECTION) then\n      msg = sysmsg(11698, ctx.file)", "   if 0 then\n      msg = sysmsg(11698, ctx.file)")),
    ("the dictionary node is never shown", "K8", sub("ide", "         if ldict<lp> then\n            nn += 1", "         if 0 then\n            nn += 1")),
    ("a dictionary item opens as a data record", "K9", sub("ide", "               if code[1, 2] = 'Q:' then or.dict = 'DICT'", "               null")),
    ("a collection record is read", "K10", sub("ide", "   if fileinfo(fv, FL$COLLECTION) then\n      lk.err = sysmsg(11684, lk.name, lk.id)\n      return\n   end\n", "")),
    ("the dictionary flag is not used to open", "K10", sub("ide", "   open lk.dict, lk.file to fv else\n      lk.err", "   open lk.file to fv else\n      lk.err")),
    ("the lock is taken through fv, not the tab's variable", "K11", sub("ide", "   readu lk.rec from tfv(lk.s), lk.id on error", "   readu lk.rec from fv, lk.id on error")),
    ("a record another session holds is taken over", "K11", sub("ide", "      lk.owner = status()\n      read lk.rec from tfv(lk.s), lk.id then", "      read lk.rec from tfv(lk.s), lk.id then")),
    ("or.mknew is not put back", "K12", sub("ide", "   or.dict = ''\n   or.mknew = 0\n   tf.dict = od", "   or.dict = ''\n   tf.dict = od")),
    ("the tab of the data record is taken for the dictionary item", "K12", sub("ide", "and bx{tf.k} = tf.dict then", "then")),
    ("a new record skips the gate", "K13", sub("ide", "         case omk\n            * 28 Oct 26 (stage B): a record named on the command line that is not there is a new one - after the account's edit gate, as the name form asks it\n            gosub edit.check\n            if not(edit.ok) then",
                                                "         case omk\n            * 28 Oct 26 (stage B): a record named on the command line that is not there is a new one - after the account's edit gate, as the name form asks it\n            edit.ok = 1\n            if not(edit.ok) then")),
    ("a record being made elsewhere is opened", "K13", sub("ide", "      if lk.owner # '' then\n         msg = sysmsg(11686, or.name, or.id, lk.owner)     ;* %1 %2 is being made", "      if 0 then\n         msg = sysmsg(11686, or.name, or.id, lk.owner)     ;* %1 %2 is being made")),
    ("the tab forgets its lock", "K14", sub("ide", "   ts.slot = lk.slot\n   ts.owner = lk.owner\n   gosub tab.state\n   tm.u = uid", "   ts.slot = 0\n   ts.owner = lk.owner\n   gosub tab.state\n   tm.u = uid")),
    ("a read-only tab is saved", "K15", sub("ide", "save.one:\n   sv.ok = @false\n   ro.i = sv.i\n   gosub ro.check", "save.one:\n   sv.ok = @false\n   ro.i = sv.i\n   ro.ok = 1")),
    ("the save opens its own file variable (the lock moves to it)", "K15", sub("ide", "   if sv.slot then\n      fv = tfv(sv.slot)\n   end else", "   if sv.slot then\n      open sv.dict, bn<sv.i> to fv else null\n   end else")),
    ("the save gives the tab's lock away", "K15", sub("ide", "      writeu sv.text on fv, sv.id on error", "      write sv.text on fv, sv.id on error")),
    ("a dictionary item always looks changed", "K16", sub("ide", "      if sv.kind = 'dict' then\n         dt.rec = disk\n         gosub dict.trim", "      if 0 then\n         dt.rec = disk\n         gosub dict.trim")),
    ("Close keeps the lock", "K17", sub("ide", "   tu.i = cb\n   gosub tab.unlock                              ;* 28 Oct 26 (stage B): and its record's lock", "   tu.i = cb")),
    ("the end keeps the locks", "K17", sub("ide", "   gosub release.all                           ;* 28 Oct 26 (stage B)", "   null                           ;* 28 Oct 26 (stage B)")),
    ("Cancel keeps the lock", "K17", sub("ide", "lock.free:\n   if lk.slot then\n      release tfv(lk.slot), lk.id", "lock.free:\n   if lk.slot then\n      null")),
    ("the locks are not taken back after a program", "K18", sub("ide", "   gosub relock.all                      ;* 28 Oct 26 (stage B)", "   null                      ;* 28 Oct 26 (stage B)")),
    ("a lost lock leaves the tab writable", "K18", sub("ide", "            bx{k} = rl.owner\n", "            null\n")),
    ("Save as keeps the old record's lock", "K19", sub("ide", "   tu.i = cb\n   gosub tab.unlock\n   u = bu<cb>\n   k = 'o' : u", "   tu.i = cb\n   u = bu<cb>\n   k = 'o' : u")),
    ("Write a copy writes a record open in a tab", "K19", sub("ide", "   if tf.p then\n      msg = sysmsg(11691, wa.file, wa.id)\n      return\n   end\n", "")),
    ("a read-only tab is editable", "K20", sub("ide", "      ro = (bx{k} # '')", "      ro = 0")),
    ("Replace changes a read-only tab", "K20", sub("ide", "do.replace:\n   if nbuf = 0 then\n      msg = sysmsg(11218)\n      return\n   end\n   ro.i = cb\n   gosub ro.check", "do.replace:\n   if nbuf = 0 then\n      msg = sysmsg(11218)\n      return\n   end\n   ro.i = cb\n   ro.ok = 1")),
    ("CREATING.SEQKEY skips the gate", "K21", sub("ide", "      msg = sysmsg(11200, sq.name)\n      return\n   end\n   gosub edit.check", "      msg = sysmsg(11200, sq.name)\n      return\n   end\n   edit.ok = 1")),
    ("New record does not take CREATING.SEQKEY", "K22", sub("ide", "   if upcase(nm.id) = 'CREATING.SEQKEY' then\n      sq.dict = ''", "   if 0 then\n      sq.dict = ''")),
    ("New record takes no lock", "K23", sub("ide", "   lk.dict = ''\n   lk.file = nm.file\n   lk.id = nm.id\n   gosub lock.take\n", "   lk.dict = ''\n   lk.file = nm.file\n   lk.id = nm.id\n   lk.slot = 0 ; lk.err = '' ; lk.exists = 0 ; lk.owner = ''\n")),
    ("a dictionary item is compiled", "K24", sub("ide", "   if bx{k} = 'dict' then\n      msg = sysmsg(11697, c.file, c.id)", "   if 0 then\n      msg = sysmsg(11697, c.file, c.id)")),
    ("SED gets the data record for a dictionary item", "K24", sub("ide", "   if sd.dict # '' then qp.f = 'dict ' : qp.f\n", "")),
    ("the include does not look in syscom", "K25", sub("ide", "         if in.files # 'syscom' then in.files<-1> = 'syscom'\n", "")),
    ("the include reads a collection record", "K25", sub("ide", "      if fileinfo(fv, FL$COLLECTION) then continue\n", "")),
    ("a directory file is data", "K26", sub("ide", "      case fileinfo(fv, FL$TYPE) = FL$TYPE.DIR\n         ko.kind = 'source'", "      case fileinfo(fv, FL$TYPE) = FL$TYPE.DIR\n         ko.kind = 'data'")),
    ("the VOC is data", "K26", sub("ide", "      case ko.ek = 1\n         ko.kind = 'voc'", "      case ko.ek = 1\n         ko.kind = 'data'")),
    ("a message loses its user number", "K28", sub("m11689", "%3", "a user")),
    ("the help forgets the locks", "K29", sub("m11215", "Locks            ", "Records          ")),
]


def report(rows):
    bad = 0
    for i, what, ok, detail in rows:
        print("  [%s] %s %s%s" % ("PASS" if ok else "FAIL", i, what, "" if ok or not detail else "   <- " + str(detail)[:200]))
        bad += 0 if ok else 1
    return bad


def selftest(src):
    base = [r[0] for r in checks(src) if not r[2]]
    if base:
        print("selftest: the unchanged tree fails %s, so a mutant's own failure cannot be told from the tree's; run the plain check first" % base)
        return 1
    holes = 0
    for name, want, mut in MUTANTS:
        try:
            m = mut(src)
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
    src = load()
    print("test-idekinds-units: tree %s" % os.path.dirname(GPL))
    if not src["ide"]:
        print("test-idekinds-units: CANNOT RUN - %s is not there" % os.path.join(GPL, "ide"))
        return 2
    rows = checks(src)
    bad = report(rows)
    print("\ntest-idekinds-units: %d passed, %d failed" % (len(rows) - bad, bad))
    rc = 1 if bad else 0
    if "--selftest" in argv:
        rc = (selftest(src) or rc)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
