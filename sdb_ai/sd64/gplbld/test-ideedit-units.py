#!/usr/bin/env python3
"""test-ideedit-units.py - the IDE's editing commands (the editor merge's stage D, 29 Oct 2026), read off the source as text.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-ideedit-units.py
  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-ideedit-units.py --selftest

No sudo, no install, no sd.  Exit 0 every check passed, 1 a check failed, 2 it could not run.

START-HISTORY:
29 Oct 26 dm  New with stage D, first slice.
END-HISTORY

WHAT IT HOLDS (gpl.bp/ide, the end of the program).  Every command works on the TEXT AREA'S LIVE TEXT (mw{'value'}) and sets it ONCE through ed.set, which puts the old text and cursor on the
undo steps ($sl_memo 'snap') BEFORE it assigns: Replace was set through load.current, which forgot the undo steps.  ed.get refuses a tab that cannot be changed (ro.check); the commands that only
look (List matching lines, Export the selection) use ed.read.  The find options (match case on as delivered, how Replace has always compared; whole words off) are find.in.line's.  Query
replace asks about each match and sets the text once at the end.  Upcase / Downcase change only the characters between the mark and the cursor, by the same range as the AI's selection.  Export
writes through write.copy (Write a copy's own write: the gate asked again, the record locked and looked at again).  Import refuses what the editor cannot keep.  Run a command goes through
EXECUTE, so the prompt's command processor and its gates, keeps the changed texts' copies first (rc.tick) and takes the tabs' locks again after (relock.all).  The menus' new entries are at the END
of their menus, so that no existing entry moves.

***IT RUNS NOTHING, SO IT CANNOT SAY THAT A COMMAND DOES WHAT IT SAYS ON A SCREEN***: that is sandbox-ide-edit.py (written, not run).  --selftest breaks each property the way an edit
plausibly would and requires a check to notice.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SDSYS = os.path.normpath(os.path.join(HERE, "..", "sdsys"))
GPL = os.path.join(SDSYS, "gpl.bp")
MSG = os.path.join(SDSYS, "messages")
NEWMSG = [11543, 11544, 11545, 11546, 11547, 11548, 11549, 11550, 11551, 11553, 11554, 11555, 11556, 11558, 11559]
CMDS = ["view", "qreplace", "findopts", "upcase", "downcase", "import", "export", "xeq", "refresh"]


def strip(src):
    out = []
    for ln in src.split("\n"):
        if ln.lstrip().startswith("*"):
            continue
        out.append(re.sub(r"\s*;\*.*$", "", ln))
    return "\n".join(out)


def label(text, name):
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


def read(path):
    try:
        with open(path, encoding="latin-1") as f:
            return f.read()
    except OSError:
        return ""


def load():
    src = {"ide": read(os.path.join(GPL, "ide"))}
    for n in NEWMSG + [11209, 11216, 11227, 11228, 11229]:
        src["m%d" % n] = read(os.path.join(MSG, str(n)))
    return src


def checks(src):
    rows = []

    def ck(i, what, ok, detail=""):
        rows.append((i, what, bool(ok), detail))

    ide = strip(src["ide"])
    names = ("ed.read", "ed.get", "ed.set", "find.in.line", "replace.line", "do.replace", "do.qreplace", "do.view", "do.findopts", "sel.range", "do.case", "do.export", "do.import", "do.xeq",
             "do.refresh", "do.goto", "do.writeas", "write.copy", "run.cmd")
    L = {n: label(ide, n) for n in names}
    main = ide[: ide.find("apply.theme:")]
    ck("E0", "NULL CASE: the IDE was read and every routine this check reads is there (a check on nothing would pass)", len(ide) > 80000 and all(len(v) > 20 for v in L.values()),
       repr(sorted(k for k, v in L.items() if len(v) <= 20)))

    # ---- the menus ----------------------------------------------------------------------------------------------------------------------------------------------------
    m27, m28, m29 = (src["m%d" % n].strip() for n in (11227, 11228, 11229))
    def cmds_of(m):
        return [e.split("~")[2] for e in m.split("|")[1:]]
    def mnem_ok(m, old=0):
        """the mnemonics of the entries after the first OLD ones are different from each other and from the old ones' (Build has two old entries that share a C: not this stage's)"""
        ms = [re.search(r"&(.)", e.split("~")[0]).group(1).lower() for e in m.split("|")[1:] if "&" in e.split("~")[0]]
        new = ms[old:]
        return len(new) == len(set(new)) and not (set(new) & set(ms[:old]))
    ck("E1", "the new entries are at the END of their menus, so no existing entry moves (Search keeps Find and Replace first, Build its four, View its Theme), each runs a command run.cmd knows, and the "
       "mnemonics of a menu are all different",
       m27.startswith("&Search|&Find in the records~~find|&Replace in the record~^R~replace|") and m28.startswith("&Build|&Compile~F8~compile|Compile and &catalogue~F9~catalog|&Run~F5~run|&Debug~F7~debug|")
       and m29.startswith("&View|&Theme~~theme|") and all(c in cmds_of(m27) + cmds_of(m28) + cmds_of(m29) for c in CMDS)
       and all(("case cmd = '%s'" % c) in L["run.cmd"] for c in CMDS) and mnem_ok(m27) and mnem_ok(m28, 4) and mnem_ok(m29), repr((cmds_of(m27), cmds_of(m28), cmds_of(m29))))

    # ---- the one place a text is set ----------------------------------------------------------------------------------------------------------------------------------
    ck("E2", "ed.get asks ro.check before it reads (a tab that cannot be changed gets no command that changes it) and ed.read does not; ed.set puts the old text on the undo steps BEFORE it "
       "assigns the new one, takes the mark away and draws the editor",
       ordered(L["ed.get"], "if nbuf = 0 then", "gosub ro.check", "if not(ro.ok) then", "gosub ro.box", "gosub ed.read") and "ro.check" not in L["ed.read"]
       and ordered(L["ed.set"], "call $sl_memo('snap', ed.mw", "ed.mw{'value'} = ed.new", "ed.mw{'mx'} = 0", "ed.mw{'my'} = 0", "gosub redraw.editor"), "")
    ck("E3", "find.in.line: case is folded on BOTH sides unless fo.case; a whole-word match must have no word character before it and none after it, the set built from digits, letters and ._$%; "
       "the search goes on after a match that fails the test",
       ordered(L["find.in.line"], "if not(fo.case) then", "fp.hay = upcase(fp.hay)", "fp.nee = upcase(fp.nee)", "index(fp.hay[fp.p, 99999], fp.nee, 1)", "if fo.word then",
               "convert(WORDCH, '', fp.hay[fp.s - 1, 1]) = ''", "convert(WORDCH, '', fp.c) = ''", "if fp.good then", "fp.p = fp.s + 1")
       and ordered(main, "WORDCH = '._$%'", "for wc.i = 48 to 57", "for wc.i = 65 to 90", "char(wc.i) : char(wc.i + 32)")
       and ordered(main, "fo.case = @true", "fo.word = @false"), "")
    rp = L["do.replace"]
    ck("E4", "Replace (Ctrl-R) is ONE undo step: it reads the live text through ed.get, sets it once through ed.set and does NOT go through bx / load.current (which forgot the undo steps); the whole text "
       "is changed at once only with the delivered options, else line by line",
       ordered(rp, "gosub ed.get", "if fo.case and not(fo.word) then", "rp.n = count(ed.t, rp.old)", "ed.new = change(ed.t, rp.old, rp.new)", "end else", "gosub replace.line", "gosub ed.set")
       and "load.current" not in rp and "bx{k}" not in rp and rp.count("gosub ed.set") == 1, "")
    qr = L["do.qreplace"]
    ck("E5", "Query replace asks about each match with Yes, No, All and Quit (Quit is the default answer if the box is left), takes the line with it, builds the text in ed.new and sets it ONCE at the "
       "end; nothing is changed when nothing was answered Yes",
       ordered(qr, "gosub ed.get", "gosub find.in.line", "buttons 'Yes,No,All,Quit' default 1 returning qr.b else qr.b = 4", "qr.quit = @true", "if qr.yes = 0 then", "return", "gosub ed.set")
       and qr.count("gosub ed.set") == 1 and "sysmsg(11546, qr.old, qr.new, qr.j)" in qr and "qr.line" in qr.split("sysmsg(11546")[1].split("\n")[0], "")
    vw = L["do.view"]
    ck("E6", "List matching lines reads the text without the read-only test (a locked record can be looked at), puts the line number and the trimmed line in the table (err.rows, err.lines), stops at "
       "MAXHIT, and marks the table 'view' so that Return goes to the line",
       ordered(vw, "gosub ed.read", "gosub find.in.line", "err.rows<-1> = vw.j", "err.lines<-1> = vw.j", "until vw.n >= MAXHIT", "out.kind = 'view'", "gosub err.load") and "ed.get" not in vw
       and "gl.n = err.lines<k2> + 0" in strip(src["ide"]), "")
    ck("E7", "Find options sets both options from the answer (C and W, any case; blank is neither) and says what they are",
       ordered(L["do.findopts"], "screen ask sysmsg(11548)", "upcase(fo.text)", "fo.case = (index(fo.text, 'C', 1) > 0)", "fo.word = (index(fo.text, 'W', 1) > 0)", "sysmsg(11549"), "")
    ck("E8", "sel.range orders the mark and the cursor and leaves out the character under the later end (as the AI's selection does) and answers no range for no mark or nothing between; Upcase and "
       "Downcase change only that range of each line (the first line from x1, the last up to x2 - 1) and set the text once",
       ordered(L["sel.range"], "if sr.my < 1 or sr.mx < 1 then return", "if sr.my < sr.cy or (sr.my = sr.cy and sr.mx <= sr.cx) then", "if sr.y1 = sr.y2 and sr.x1 = sr.x2 then return", "sr.ok = @true")
       and ordered(L["do.case"], "gosub ed.get", "gosub sel.range", "if not(sr.ok) then", "sysmsg(11551)", "if dc.j = sr.y1 then dc.a = sr.x1", "if dc.j = sr.y2 then dc.z = sr.x2 - 1",
                   "dc.part = dc.ln[dc.a, dc.z - dc.a + 1]", "upcase(dc.part)", "downcase(dc.part)", "dc.ln[1, dc.a - 1] : dc.part : dc.ln[dc.z + 1, 99999]", "gosub ed.set")
       and L["do.case"].count("gosub ed.set") == 1, "")
    ex = L["do.export"]
    ck("E9", "Export the selection reads without the read-only test, takes the AI's selection text, asks the name form in the 'copy' mode, refuses a record a tab holds, and writes through write.copy - "
       "itself it holds no write; Write a copy writes through the same label",
       ordered(ex, "gosub ed.read", "gosub sel.range", "call $tk_ai('select', ed.t", "call $ide_name('copy', wa.file, wa.id, wa.res)", "gosub tab.find", "if tf.p then", "gosub write.copy")
       and not re.search(r"^\s*(write|writeu|readu)\s", ex, re.M) and ordered(L["do.writeas"], "call $ide_name('copy', wa.file, wa.id, wa.res)", "gosub tab.find", "gosub write.copy")
       and ordered(L["write.copy"], "open wa.file to fv else", "gosub edit.check", "readu x from fv, wa.id locked", "write wa.text on fv, wa.id on error", "release fv, wa.id", "gosub refresh.tree.for"), "")
    im = L["do.import"]
    ck("E10", "Import a record here needs a tab that can be changed, asks the name form in the 'open' mode (the record must exist), refuses an operating system file, a collection file, a record holding "
       "value, subvalue or text marks or bytes 128 to 247, and puts the lines in at the cursor through ed.set; it writes no record",
       ordered(im, "gosub ed.get", "call $ide_name('open', im.file, im.id, im.res)", "if im.file = 'path:' then", "FL$COLLECTION", "read im.x from fv, im.id else", "index(im.x, @vm, 1)", "index(im.x, @sm, 1)",
               "index(im.x, @tm, 1)", "convert(NA.CHARS, '', im.x) # im.x", "im.block = im.ln[1, im.cx - 1] : im.x", "im.block := im.ln[im.cx, 99999]", "ed.new<im.cy> = im.block", "gosub ed.set")
       and not re.search(r"\b(write|writeu|readu|delete)\b", im), "")
    xq = L["do.xeq"]
    ck("E11", "Run a command keeps the changed texts' copies BEFORE it runs (the command may end the session), runs it with EXECUTE ... CAPTURING (the prompt's command processor: its gates), takes the tabs' "
       "locks again AFTER it, and shows what it printed in the table (rows that jump nowhere: err.lines 0)",
       ordered(xq, "screen ask sysmsg(11554)", "gosub rc.tick", "execute xq.cmd capturing xq.out", "gosub relock.all", "err.rows<-1> = xq.n", "err.lines<-1> = 0", "out.kind = 'xeq'", "gosub err.load"), "")
    gt = L["do.goto"]
    ck("E12", "Go to takes a line, a line and column, or field, value and subvalue (the value after the (v - 1)-th ':@vm:', the subvalue after the (s - 1)-th ':@sm:' inside it); each number must be a number "
       "of at least 1; the cursor is put inside the line",
       ordered(gt, "screen ask sysmsg(11209)", "gl.k > 3", "num(gl.p<gl.i>)", "gl.p<gl.i> + 0 < 1", "gosub goto.line", "index(gl.ln, ':@vm:', gl.p<2> + 0 - 1)", "gl.from = gl.q + 5", "index(gl.seg, ':@sm:', gl.p<3> + 0 - 1)",
               "gl.col = gl.from + gl.q + 4", "if gl.col > len(gl.ln) + 1 then gl.col = len(gl.ln) + 1", "mw{'cx'} = gl.col")
       and "gosub do.goto" in L["run.cmd"] and ordered(L["do.refresh"], "screen refresh", "last.status = char(1)", "last.foot = ''"), "")
    ck("E13", "messages 11543-11559 (the ones used) are there, one line each, and the IDE cites each; the Go to prompt names the forms and the help names the new menu entries",
       all(src["m%d" % n].strip() and src["m%d" % n].count("\n") == 1 for n in NEWMSG) and all(("sysmsg(%d" % n) in ide for n in NEWMSG if n not in (11209,))
       and "line,column" not in "" and "field,value,subvalue" in src["m11209"] and "line,column" in src["m11209"]
       and all(w in src["m11216"] for w in ("List matching lines", "Query replace", "Find options", "Upcase", "Import", "Export", "Run a command", "Refresh")), repr([n for n in NEWMSG if ("sysmsg(%d" % n) not in ide]))
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
    ("a menu entry moved: Search starts with List", "E1", sub("m11227", "&Search|&Find in the records~~find|", "&Search|&List matching lines~~view|&Find in the records~~find|")),
    ("a menu entry has no command", "E1", sub("ide", "      case cmd = 'xeq'\n         gosub do.xeq", "      case cmd = 'xeqq'\n         gosub do.xeq")),
    ("two entries share a mnemonic", "E1", sub("m11227", "Find &options", "&Find options")),
    ("ed.get skips the read-only test", "E2", sub("ide", "   ro.i = cb\n   gosub ro.check\n   if not(ro.ok) then\n      gosub ro.box\n      return\n   end\n   gosub ed.read", "   gosub ed.read")),
    ("ed.set assigns before it snaps", "E2", sub("ide", "   call $sl_memo('snap', ed.mw, '', '', ed.sr)\n   ed.mw{'value'} = ed.new", "   ed.mw{'value'} = ed.new\n   call $sl_memo('snap', ed.mw, '', '', ed.sr)")),
    ("ed.set leaves the mark", "E2", sub("ide", "   ed.mw{'mx'} = 0\n   ed.mw{'my'} = 0\n   ed.nl", "   ed.nl")),
    ("whole words ignore the character before", "E3", sub("ide", "            if convert(WORDCH, '', fp.hay[fp.s - 1, 1]) = '' then fp.good = @false", "            null")),
    ("whole words ignore the character after", "E3", sub("ide", "            if convert(WORDCH, '', fp.c) = '' then fp.good = @false", "            null")),
    ("a failed whole-word match ends the search", "E3", sub("ide", "      fp.p = fp.s + 1\n   repeat", "      exit\n   repeat")),
    ("case is folded on the pattern only", "E3", sub("ide", "      fp.hay = upcase(fp.hay)\n      fp.nee = upcase(fp.nee)", "      fp.nee = upcase(fp.nee)")),
    ("the options are on as delivered", "E3", sub("ide", "   fo.case = @true\n   fo.word = @false", "   fo.case = @false\n   fo.word = @false")),
    ("Replace goes through load.current again", "E4", sub("ide", "   ed.cy = 0\n   gosub ed.set\n   msg = sysmsg(11234, rp.n)", "   ed.cy = 0\n   gosub ed.set\n   gosub load.current\n   msg = sysmsg(11234, rp.n)")),
    ("Replace takes the quick way with options on", "E4", sub("ide", "   if fo.case and not(fo.word) then\n      rp.n = count(ed.t, rp.old)", "   if 1 then\n      rp.n = count(ed.t, rp.old)")),
    ("Query replace sets the text for each match", "E5", sub("ide", "            if qr.take then\n               qr.out := qr.new", "            if qr.take then\n               gosub ed.set\n               qr.out := qr.new")),
    ("Query replace has no Quit", "E5", sub("ide", "buttons 'Yes,No,All,Quit' default 1 returning qr.b else qr.b = 4", "buttons 'Yes,No,All' default 1 returning qr.b else qr.b = 2")),
    ("Query replace writes when nothing was answered Yes", "E5", sub("ide", "   if qr.yes = 0 then\n      msg = sysmsg(11547, 0, qr.no)\n      return\n   end", "   if 0 then\n      msg = sysmsg(11547, 0, qr.no)\n      return\n   end")),
    ("List matching lines asks the read-only test", "E6", sub("ide", "do.view:\n   gosub ed.read", "do.view:\n   gosub ed.get")),
    ("List matching lines has no limit", "E6", sub("ide", "   until vw.n >= MAXHIT\n   next vw.j", "   next vw.j")),
    ("List matching lines marks the table 'search'", "E6", sub("ide", "   out.kind = 'view'\n   out.file = ''\n   out.dict = ''\n   gosub err.load\n   msg = sysmsg(11544", "   out.kind = 'search'\n   out.file = ''\n   out.dict = ''\n   gosub err.load\n   msg = sysmsg(11544")),
    ("Find options reads W as C", "E7", sub("ide", "   fo.word = (index(fo.text, 'W', 1) > 0)", "   fo.word = (index(fo.text, 'C', 1) > 0)")),
    ("the selection includes the character under the later end", "E8", sub("ide", "      if dc.j = sr.y2 then dc.z = sr.x2 - 1", "      if dc.j = sr.y2 then dc.z = sr.x2")),
    ("the selection ignores where it starts", "E8", sub("ide", "      if dc.j = sr.y1 then dc.a = sr.x1", "      dc.a = 1")),
    ("nothing selected is the whole text", "E8", sub("ide", "   if sr.y1 = sr.y2 and sr.x1 = sr.x2 then return\n   sr.ok = @true", "   sr.ok = @true")),
    ("Export asks the read-only test", "E9", sub("ide", "do.export:\n   gosub ed.read", "do.export:\n   gosub ed.get")),
    ("Export writes itself", "E9", sub("ide", "      msg = sysmsg(11691, wa.file, wa.id)\n      return\n   end\n   gosub write.copy\n   return\n\n* Search / Import", "      msg = sysmsg(11691, wa.file, wa.id)\n      return\n   end\n   write wa.text on fv, wa.id\n   return\n\n* Search / Import")),
    ("Write a copy loses the gate", "E9", sub("ide", "write.copy:\n   open wa.file to fv else\n      msg = sysmsg(11200, wa.file)\n      return\n   end\n   gosub edit.check", "write.copy:\n   open wa.file to fv else\n      msg = sysmsg(11200, wa.file)\n      return\n   end\n   edit.ok = 1")),
    ("Import takes a record with value marks", "E10", sub("ide", "   if index(im.x, @vm, 1) or index(im.x, @sm, 1) or index(im.x, @tm, 1) or convert(NA.CHARS, '', im.x) # im.x then", "   if convert(NA.CHARS, '', im.x) # im.x then")),
    ("Import takes a collection file's record", "E10", sub("ide", "   if fileinfo(fv, FL$COLLECTION) then\n      msg = sysmsg(11698, im.file)", "   if 0 then\n      msg = sysmsg(11698, im.file)")),
    ("Import takes an operating system file", "E10", sub("ide", "   if im.file = 'path:' then\n      msg = sysmsg(11558)", "   if 0 then\n      msg = sysmsg(11558)")),
    ("Import works in a read-only tab", "E10", sub("ide", "do.import:\n   gosub ed.get", "do.import:\n   gosub ed.read")),
    ("Run a command does not keep the copies first", "E11", sub("ide", "   gosub rc.tick\n   xq.out = ''", "   xq.out = ''")),
    ("Run a command does not take the locks again", "E11", sub("ide", "   execute xq.cmd capturing xq.out\n   gosub relock.all", "   execute xq.cmd capturing xq.out")),
    ("Run a command shows the output on the terminal", "E11", sub("ide", "   execute xq.cmd capturing xq.out", "   execute xq.cmd")),
    ("Go to takes a zero", "E12", sub("ide", "      if gl.p<gl.i> + 0 < 1 then return", "      null")),
    ("Go to counts the value from the wrong mark", "E12", sub("ide", "index(gl.ln, ':@vm:', gl.p<2> + 0 - 1)", "index(gl.ln, ':@vm:', gl.p<2> + 0)")),
    ("a message is empty", "E13", sub("m11546", "\n", "")),
    ("the help forgets the new entries", "E13", sub("m11216", "Query replace", "Query")),
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
    print("test-ideedit-units: tree %s" % os.path.dirname(GPL))
    if not src["ide"]:
        print("test-ideedit-units: CANNOT RUN - %s is not there" % os.path.join(GPL, "ide"))
        return 2
    rows = checks(src)
    bad = report(rows)
    print("\ntest-ideedit-units: %d passed, %d failed" % (len(rows) - bad, bad))
    rc = 1 if bad else 0
    if "--selftest" in argv:
        rc = (selftest(src) or rc)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
