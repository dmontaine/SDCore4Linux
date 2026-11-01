#!/usr/bin/env python3
"""test-aipage-units.py - the AI line on a PAGE of the toolkit ($tk_aipage, S.97 stage 1), as invariants read off the source.  Free: no install, no sudo, no sd.

    python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-aipage-units.py [--selftest]

WHAT THIS IS, AND WHAT IT IS NOT.  It reads the BASIC of the library programs and of the pages that have the line (the pilot pages tool.voc and tool.files of stage 1; tool.catalog, tool.mygates,
tool.dict, tool.test, tool.query and tool.bulk since stage 2, 1 Nov 26) as text, comments removed.  ***IT RUNS NOTHING, SO IT CANNOT
SAY WHAT A SESSION SEES***: that is `sandbox-ai-pages.py` (an ordinary session on a private SD, the fake provider's log and the screen as the evidence).  What a text check is for: the
properties that make the line SAFE and make a page WITHOUT the AI exactly what it was - the row is taken only when a page asked, the line is drawn only then, an action is offered only
when the page opted it in, a proposal is carried out only by the page's own key, nothing here runs a command or writes - are mostly ORDER and ABSENCE, and an edit that breaks one still
compiles.

--selftest breaks each invariant in the way an edit plausibly would and requires a check to notice; a mutant that nothing catches is a failure of the self-test.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SDSYS = os.path.normpath(os.path.join(HERE, "..", "sdsys"))
GPL = os.path.join(SDSYS, "gpl.bp")
FILES = {
    "tkh": os.path.join(GPL, "tk.h"),
    "layout": os.path.join(GPL, "tk_layout"),
    "frame": os.path.join(GPL, "tk_frame"),
    "ai": os.path.join(GPL, "tk_ai"),
    "keys": os.path.join(GPL, "tk_keys"),
    "page": os.path.join(GPL, "tk_aipage"),
    "voc": os.path.join(GPL, "tool_voc"),
    "files": os.path.join(GPL, "tool_files"),
    "catalog": os.path.join(GPL, "tool_catalog"),
    "mygates": os.path.join(GPL, "tool_mygates"),
    "dict": os.path.join(GPL, "tool_dict"),
    "test": os.path.join(GPL, "tool_test"),
    "query": os.path.join(GPL, "tool_query"),
    "bulk": os.path.join(GPL, "tool_bulk"),
    "accounts": os.path.join(GPL, "tool_accounts"),
    "audit": os.path.join(GPL, "tool_audit"),
    "backups": os.path.join(GPL, "tool_backups"),
    "config": os.path.join(GPL, "tool_config"),
    "gates": os.path.join(GPL, "tool_gates"),
    "masters": os.path.join(GPL, "tool_masters"),
    "remote": os.path.join(GPL, "tool_remote"),
    "sessions": os.path.join(GPL, "tool_sessions"),
    "viewers": os.path.join(GPL, "tool_viewers"),
    "aipg": os.path.join(GPL, "tool_ai"),
    "menus": os.path.join(GPL, "tool_menus"),
    "mymenu": os.path.join(GPL, "mymenu"),
    "m43": os.path.join(SDSYS, "messages", "11943"),
    "m44": os.path.join(SDSYS, "messages", "11944"),
    "fake": os.path.join(HERE, "fakemodel.py"),
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


def checks(raw):
    rows = []

    def ck(i, what, ok, detail=""):
        rows.append((i, what, bool(ok), detail))

    tkh, lay, frm, ai, ks, ap, voc, fil = (strip_bas(raw[k]) for k in ("tkh", "layout", "frame", "ai", "keys", "page", "voc", "files"))
    ck("AP0", "NULL CASE: every program, both pages, the two messages and the fake were found and are not empty (a check on nothing would pass)",
       all(len(x) > 200 for x in (tkh, lay, frm, ai, ks, ap, voc, fil)) and raw["m43"].strip() != "" and raw["m44"].strip() != "" and "act_refresh" in raw["fake"] or False,
       repr([len(x) for x in (tkh, lay, frm, ai, ks, ap, voc, fil)]))
    ck("AP1", "tk.h: slot 28 is TK.C.AIROW (after the menu bar's 27, nothing before it moved) and value 10 of a key row is TK.K.AI",
       re.search(r"\$define TK\.C\.BAR\s+27\b", tkh) is not None and re.search(r"\$define TK\.C\.AIROW\s+28\b", tkh) is not None and re.search(r"\$define TK\.K\.ROW\s+9\b", tkh) is not None
       and re.search(r"\$define TK\.K\.AI\s+10\b", tkh) is not None, "")
    ck("AP2", "THE ROW IS TAKEN ONLY WHEN A PAGE ASKED: the body is one row shorter through ctx<TK.C.AIROW> and nowhere else, and the layout's 'full' test makes the same allowance (a page with no AI line is laid out as it always was)",
       lay.count("ctx<TK.C.BODYH> = ctx<TK.C.YSTAT> - TK.YBODY - (if ctx<TK.C.AIROW> then 1 else 0)") == 1 and lay.count("TK.C.AIROW") == 3
       and "if bw >= rbw and bh >= rbh - (if ctx<TK.C.AIROW> then 1 else 0) then" in lay
       and "if ctx<TK.C.AIROW> and pvs<i> > 0 and v > 1 then v -= 1" in lay, repr(lay.count("TK.C.AIROW")))     # (the third: a pane that stretches may give the row up though its page declared no least height)
    ck("AP3", "$tk_frame draws the line last, only for a page that has a row AND an AI that is on, through $tk_ai 'show'; it draws nothing of its own",
       frm.count("$tk_ai('show'") == 1 and "if ctx<TK.C.AIROW> and ctx<TK.C.AI> then call $tk_ai('show', ctx, '', '')" in frm and ordered(frm, "last.top = a", "$tk_ai('show'", "return"), "")
    ck("AP4", "$tk_ai 'show' writes the line only when something it shows has changed (the window, the frame's generation and epoch, the focus, the text, the cursor, the pan) and 'focused' says whether it has the focus",
       "case op = 'show'" in ai and "if ai.on and ai.line then" in ai and re.search(r"sg = ctx<TK\.C\.W> : '/' : ctx<TK\.C\.YSTAT> : '/' : ctx<TK\.C\.GEN> : '/' : ctx<TK\.C\.EPOCH> : '/' : ai\.focus : '/' : ai\.w\{'value'\} : '/' : ai\.w\{'pos'\} : '/' : ai\.w\{'pan'\}", ai)
       and ordered(ai, "if sg # ai.sig then", "ai.sig = sg", "gosub paint") and "ai.line, ai.sig" in ai and "case op = 'focused'" in ai, "")
    ck("AP5", "the dim hint of a page says F6 (message 11943), the home screen's is the old one (11637): the choice is made on ctx<TK.C.AIROW> in the one place the hint is drawn",
       "sysmsg((if ctx<TK.C.AIROW> then 11943 else 11637))" in ai and ai.count("11637") == 1, "")
    ck("AP6", "$tk_keys 'ai' only sets TK.K.AI on the rows of the action named, and 'aiacts' offers only rows that carry it, once each, that are available now for the pane AND have a key to press",
       re.search(r"case op = 'ai'.*?if keys<i, TK\.K\.ACT> = a then keys<i, TK\.K\.AI> = 1", ks, re.S) is not None and "if keys<i, TK.K.AI> = 1 and fa # '' and index(seen, @fm : fa : @fm, 1) = 0 then" in ks
       and "if ia and ikf # '' then" in ks, "")
    ck("AP7", "THE REGISTRY STILL HOLDS NO CODE, and neither does the page program: no execute, perform, chain, write, delete, open, read, confirm box or $tk_run in $tk_keys or $tk_aipage, and no assignment to the frame's generation",
       not re.search(r"^\s*(?:execute|os\.execute|perform|chain|write[uv]?|delete[uv]?|matwrite|openpath|open|openseq|readu?|readv|gosub on\.key)\b", ks + "\n" + ap, re.M) and "$tk_run" not in ks + ap
       and "$tk_confirm" not in ks + ap and "TK.C.GEN" not in ap, "")
    ck("AP8", "$tk_aipage is an internal subroutine with SIX arguments, catalogued $tk_aipage; 'init' clears the page's row FIRST and gives it, adds the F6 row and the AI menu entry and refreshes the layout ONLY when the AI is usable ('again' adds no row)",
       re.search(r"\$internal\s*\nsubroutine tk_aipage\(op, ctx, keys, pane, a, out\)\s*\n\$catalog \$tk_aipage\b", ap) is not None
       and ordered(ap, "case op = 'init' or op = 'again'", "ctx<TK.C.AIROW> = ''", "if ctx<TK.C.AI> then", "ctx<TK.C.AIROW> = 1", "if op = 'init' then gosub add.rows", "$tk_layout('refresh'",
                  "case op = 'keys'", "if ctx<TK.C.AIROW> then gosub add.rows")
       and ordered(ap, "add.rows:", "$tk_keys('add', keys, 'f6', 'ask ai', 'ai', '', 1)", "$tk_keys('menu', keys, 'ai', '&AI', '&Ask the AI', '', '')", "return"), "")
    ck("AP9", "WHAT IS OFFERED is the page's table (aiacts), the actions only NAVIGATE (<5> 1: Enter alone accepts), a command is ignored ('nocmd'), no file's text is sent (<13> 'none'), ONE ask, and an accepted action is carried out only through the key the table gives for it (keyof)",
       ap.count("$tk_ai('ask'") == 1 and "$tk_keys('aiacts', keys, pane, acts, '', '', '')" in ap and "acts : @fm : 1" in ap and "actx<11> = 'nocmd'" in ap and "actx<13> = 'none'" in ap
       and "$tk_keys('keyof', keys, res<2>, pane, kk, '', '')" in ap and "out = 'replay' : @fm : kk" in ap, "")
    ck("AP10", "the line takes a key only while it has the focus, and never the end of the input, a resize, the mouse or the cursor lock's guard; Esc, Tab, Back-tab, Up and Down give the focus back and clear the message",
       "$tk_ai('focused', ctx, foc, '')" in ap and "if foc and nm # '' and nm # 'resize' and nm # 'mouse' and nm # 'guardquit' then" in ap
       and "case ko = 'leave' or ko = 'tab' or ko = 'btab' or ko = 'up' or ko = 'down'" in ap, "")
    # 1 Nov 26 (S.97 stage 2): every page that has the line, as one table: its id letter, its source, the pane argument it gives the library (a literal in quotes or a variable),
    # what it offers the model, whether it lays itself out BEFORE its key table (then the panes are declared again right after 'init'), and whether it makes its key table anew
    # (tool.bulk: the line's rows are put back by $tk_aipage 'keys' at the end of build.keys).  Only actions that change what is shown are offered.
    # 1 Nov 26 (S.97 stage 2 group B and stage 3): the administrator's pages, tool.menus and my.menu join; the last field is the page's layout routine (declare.layout or
    # lay.declare; my.menu has none: its one box leaves the line's row free).  The administrator's pages offer navigation only (the owner's default: nothing that changes an
    # account, a gate, a session, a door, a setting or a backup); my.menu offers nothing at all.
    PAGES = (("a", voc, "'VOC'", ["type", "state", "filter", "refresh"], "tool.voc", 0, 0, "declare.layout"),
             ("b", fil, "'Files'", ["filter", "refresh"], "tool.files", 0, 0, "declare.layout"),
             ("c", strip_bas(raw["catalog"]), "'Programs'", ["filter", "refresh"], "tool.catalog", 0, 0, "declare.layout"),
             ("d", strip_bas(raw["mygates"]), "'My gates'", ["refresh"], "tool.mygates", 0, 0, "declare.layout"),
             ("e", strip_bas(raw["dict"]), "pnames<pi>", ["indices", "items", "file", "filter", "refresh"], "tool.dict", 0, 0, "declare.layout"),
             ("f", strip_bas(raw["test"]), "pn", ["filter", "refresh", "runspane"], "tool.test", 1, 0, "declare.layout"),
             ("g", strip_bas(raw["query"]), "cur.pane", ["filter", "reread"], "tool.query", 0, 0, "declare.layout"),
             ("h", strip_bas(raw["bulk"]), "panes<pane>", ["switch", "refresh"], "tool.bulk", 1, 1, "declare.layout"),
             ("i", strip_bas(raw["accounts"]), "'Accounts'", ["refresh"], "tool.accounts", 1, 0, "declare.layout"),
             ("j", strip_bas(raw["audit"]), "'Audit'", ["filter", "clear", "goto", "follow", "refresh"], "tool.audit", 1, 0, "declare.layout"),
             ("k", strip_bas(raw["backups"]), "'Backups'", ["refresh"], "tool.backups", 0, 0, "lay.declare"),
             ("l", strip_bas(raw["config"]), "panes<view>", ["parameters", "backups", "report", "differ", "refresh"], "tool.config", 0, 0, "lay.declare"),
             ("m", strip_bas(raw["gates"]), "'Gates'", ["filter", "refresh"], "tool.gates", 1, 0, "declare.layout"),
             ("n", strip_bas(raw["masters"]), "'Masters'", ["journal", "refresh"], "tool.masters", 1, 0, "declare.layout"),
             ("o", strip_bas(raw["remote"]), "panes<view>", ["doors", "routes", "servers", "connected", "tls", "login", "refresh"], "tool.remote", 0, 0, "lay.declare"),
             ("p", strip_bas(raw["sessions"]), "panes<pane>", ["switch", "output", "refresh"], "tool.sessions", 1, 0, "declare.layout"),
             ("q", strip_bas(raw["viewers"]), "pnames<pane>", ["pane", "output", "refresh"], "tool.viewers", 0, 0, "declare.layout"),
             ("r", strip_bas(raw["aipg"]), "pnames<pane>", ["pane", "refresh"], "tool.ai", 0, 0, "lay.declare"),
             ("s", strip_bas(raw["menus"]), "pnames<pane>", ["pane", "refresh"], "tool.menus", 0, 0, "lay.declare"),
             ("t", strip_bas(raw["mymenu"]), "'My programs'", [], "my.menu", 0, 0, None))
    for letter, pg, nm, opts, name, lay_first, rebuilt, lay in PAGES:
        lay_call = "gosub " + (lay or "no.layout.here")
        got = re.findall(r"\$tk_keys\('ai', keys, '([a-z.]+)', '', '', '', ''\)", pg)
        pre = pg.find("$tk_aipage('init'")
        lastmenu = pg.rfind("$tk_keys('menu'")
        o1 = pg.find("call $tk_open(")
        hand = pg.find("call $tk_open(", o1 + 1) if o1 >= 0 else -1                   # the SECOND open of the toolkit: the page took the terminal back from the IDE or a verb
        again = pg.find("$tk_aipage('again'")
        decl2 = pg.find(lay_call, hand) if hand >= 0 else -1
        init_ok = pg.count("$tk_aipage('init'") == 1 and re.search(r"call \$tk_aipage\('init', ctx, keys, '', '', aout\)", pg) is not None
        if rebuilt:
            bk = pg[pg.find("build.keys:"):]
            bk = bk[:bk.find("\n   return")]
            where = (init_ok and "call $tk_aipage('keys', ctx, keys, '', '', aout)" in bk and 0 <= pg.find("gosub build.keys") < pre
                     and all("$tk_keys('ai', keys, '%s'" % o in bk for o in opts))
        else:
            where = init_ok and 0 < lastmenu < pre
        if lay is None:
            where = where and "gosub declare.layout" not in pg and "gosub lay.declare" not in pg          # no layout: nothing to lay out again (the row is free)
        elif lay_first:
            where = where and re.search(r"call \$tk_aipage\('init', ctx, keys, '', '', aout\)[^\n]*\n\s*if aout then " + re.escape(lay_call), pg) is not None
        else:
            where = where and pre < pg.find(lay_call)
        ck("AP11" + letter, "%s offers the AI exactly %s (never edit, delete, run, apply, save, quit, help, new or the menu), and asks for the line after its key table and before its layout, or lays itself out again after"
           % (name, ", ".join(opts)), len(pg) > 200 and sorted(got) == sorted(opts) and where, repr((got, lastmenu, pre)))
        reopen = (hand < 0 and again < 0) or (0 < hand < again < decl2)
        ck("AP12" + letter, "%s: the hook sees every key BEFORE the menu bar and the bar is not given a key the line used; an accepted proposal is replayed as the page's own key; the status line follows the answer; 'taken' is the first case; F6 and a click on the line reach it; a new context after a hand-over is given its row before its layout" % name,
           ordered(pg, "call $tk_aipage('key', ctx, keys, %s, nm, ao)" % nm, "if ao<1> = 'replay' then nm = ao<2>", "if ao<1> # '' then msg = ao<4>", "if nm # '' and ao<1> = '' then call $tk_menubar('key', ctx, keys, %s" % nm,
                    "case ao<1> = 'taken'", "case nm = ''") and re.search(r"(?:case|if) nm = 'f6'(?: then)?\s*\n\s*call \$tk_aipage\('open', ctx, keys, %s, '', ap\)" % re.escape(nm), pg) is not None
           and (ordered(pg, "call $tk_aipage('mouse', ctx, keys, %s, mev, ap)" % nm, "call $tk_help('hit'") if "$tk_help('hit'" in pg
                else "call $tk_aipage('mouse', ctx, keys, %s, mev, ap)" % nm in pg) and reopen, repr((hand, again, decl2)))
    m43 = raw["m43"].rstrip("\n")
    m44 = raw["m44"].rstrip("\n")
    ck("AP13", "messages 11943 (the hint: names F6) and 11944 (the replay refusal: takes the action id) are one line each and under 80 characters",
       "\n" not in m43 and "\n" not in m44 and "F6" in m43 and "%1" in m44 and len(m43) < 80 and len(m44) < 80, repr((len(m43), len(m44))))
    ck("AP14", "the fake provider answers act_refresh, act_type and act_delete with the action of that id, and the suite's own page has delete as a key it did NOT opt in",
       all(re.search(r'"act_%s": \'\{"say": "[^"]+", "action": "%s"' % (w, w), raw["fake"]) for w in ("refresh", "type", "delete")) and "'delete'" in voc and "$tk_keys('ai', keys, 'delete'" not in voc, "")
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
    ("the row is taken by every page", "AP2", sub("layout", "ctx<TK.C.YSTAT> - TK.YBODY - (if ctx<TK.C.AIROW> then 1 else 0)", "ctx<TK.C.YSTAT> - TK.YBODY - 1")),
    ("the 'full' test forgets the row", "AP2", sub("layout", "bh >= rbh - (if ctx<TK.C.AIROW> then 1 else 0) then", "bh >= rbh then")),
    ("the row comes out of the pane that does not stretch", "AP2", sub("layout", "if ctx<TK.C.AIROW> and pvs<i> > 0 and v > 1 then v -= 1", "if 0 then v -= 1")),
    ("the frame draws the line for a page with no row", "AP3", sub("frame", "if ctx<TK.C.AIROW> and ctx<TK.C.AI> then call $tk_ai('show', ctx, '', '')", "if ctx<TK.C.AI> then call $tk_ai('show', ctx, '', '')")),
    ("the line is written on every call", "AP4", sub("ai", "            if sg # ai.sig then", "            if 1 then")),
    ("a page's hint is the home screen's", "AP5", sub("ai", "sysmsg((if ctx<TK.C.AIROW> then 11943 else 11637))", "sysmsg(11637)")),
    ("every action of the table is offered", "AP6", sub("keys", "if keys<i, TK.K.AI> = 1 and fa # '' and index(seen,", "if fa # '' and index(seen,")),
    ("an action with no key is offered", "AP6", sub("keys", "if ia and ikf # '' then", "if ia then")),
    ("the page program writes a record", "AP7", sub("page", "   out = ''\n\n   begin case", "   out = ''\n   write 'x' to nowhere, 'y'\n\n   begin case")),
    ("a page keeps the row of an earlier context", "AP8", sub("page", "         ctx<TK.C.AIROW> = ''\n", "")),
    ("the keys are added for an account without the AI", "AP8", sub("page", "            if op = 'init' then", "            if 1 then")),
    ("a command from the model is run", "AP9", sub("page", "   actx<11> = 'nocmd'", "   actx<11> = ''")),
    ("the actions are not navigation only", "AP9", sub("page", "acts : @fm : 1", "acts : @fm : 0")),
    ("a proposal is replayed without the table's key", "AP9", sub("page", "$tk_keys('keyof', keys, res<2>, pane, kk, '', '')", "kk = res<2>")),
    ("the line takes the resize", "AP10", sub("page", "nm # 'resize' and ", "")),
    ("tool.voc offers delete to the AI", "AP11a", sub("voc", "   call $tk_keys('ai', keys, 'refresh', '', '', '', '')\n", "   call $tk_keys('ai', keys, 'refresh', '', '', '', '')\n   call $tk_keys('ai', keys, 'delete', '', '', '', '')\n")),
    ("tool.files offers delete to the AI", "AP11b", sub("files", "   call $tk_keys('ai', keys, 'refresh', '', '', '', '')\n", "   call $tk_keys('ai', keys, 'refresh', '', '', '', '')\n   call $tk_keys('ai', keys, 'delete', '', '', '', '')\n")),
    ("tool.voc gives the row after the layout", "AP11a", sub("voc", "   call $tk_aipage('init', ctx, keys, '', '', aout)\n\n   VIS = 16 ", "\n   VIS = 16 ")),
    ("tool.voc's bar sees a key the line used", "AP12a", sub("voc", "if nm # '' and ao<1> = '' then call $tk_menubar('key'", "if nm # '' then call $tk_menubar('key'")),
    ("tool.files does not replay a proposal", "AP12b", sub("files", "if ao<1> = 'replay' then nm = ao<2>", "if @false then nm = ao<2>")),
    ("tool.files has no F6", "AP12b", sub("files", "      case nm = 'f6'\n         call $tk_aipage('open', ctx, keys, 'Files', '', ap)", "      case nm = 'zz6'\n         call $tk_aipage('open', ctx, keys, 'Files', '', ap)")),
    ("tool.voc forgets the row after the IDE", "AP12a", sub("voc", "   call $tk_aipage('again', ctx, keys, '', '', aout)", "   aout = 0")),
    ("the hint does not say F6", "AP13", sub("m43", "press F6, ", "press Tab, ")),
    # 1 Nov 26 (S.97 stage 2)
    ("tool.catalog offers compile to the AI", "AP11c", sub("catalog", "   call $tk_keys('ai', keys, 'refresh', '', '', '', '')\n", "   call $tk_keys('ai', keys, 'refresh', '', '', '', '')\n   call $tk_keys('ai', keys, 'compile', '', '', '', '')\n")),
    ("tool.test does not lay out again after the line took a row", "AP11f", sub("test", "   if aout then gosub declare.layout\n", "")),
    ("tool.bulk's new key table loses the line's rows", "AP11h", sub("bulk", "   call $tk_aipage('keys', ctx, keys, '', '', aout)\n", "")),
    ("tool.dict forgets the row after the hand-over", "AP12e", sub("dict", "   call $tk_aipage('again', ctx, keys, '', '', aout)", "   aout = 0")),
    ("tool.query has no F6", "AP12g", sub("query", "   if nm = 'f6' then\n", "   if nm = 'zz6' then\n")),
    ("tool.mygates' bar sees a key the line used", "AP12d", sub("mygates", "if nm # '' and ao<1> = '' then call $tk_menubar('key'", "if nm # '' then call $tk_menubar('key'")),
    # 1 Nov 26 (S.97 stage 2 group B, stage 3): the administrator's pages hold to navigation only
    ("tool.gates offers queue to the AI", "AP11m", sub("gates", "   call $tk_keys('ai', keys, 'refresh', '', '', '', '')\n", "   call $tk_keys('ai', keys, 'refresh', '', '', '', '')\n   call $tk_keys('ai', keys, 'queue', '', '', '', '')\n")),
    ("tool.sessions offers logout to the AI", "AP11p", sub("sessions", "   call $tk_keys('ai', keys, 'switch', '', '', '', '')\n", "   call $tk_keys('ai', keys, 'switch', '', '', '', '')\n   call $tk_keys('ai', keys, 'logout', '', '', '', '')\n")),
    ("tool.accounts does not lay out again after the line took a row", "AP11i", sub("accounts", "   call $tk_aipage('init', ctx, keys, '', '', aout)\n   if aout then gosub declare.layout\n", "   call $tk_aipage('init', ctx, keys, '', '', aout)\n")),
    ("tool.remote forgets the row after the hand-over", "AP12o", sub("remote", "   call $tk_aipage('again', ctx, keys, '', '', aout)", "   aout = 0")),
    ("my.menu offers an action", "AP11t", sub("mymenu", "   call $tk_aipage('init', ctx, keys, '', '', aout)", "   call $tk_keys('ai', keys, 'remove', '', '', '', '')\n   call $tk_aipage('init', ctx, keys, '', '', aout)")),
    ("tool.ai's bar sees a key the line used", "AP12r", sub("aipg", "if nm # '' and ao<1> = '' then call $tk_menubar('key'", "if nm # '' then call $tk_menubar('key'")),
    ("the keys op adds the rows without a line", "AP8", sub("page", "         if ctx<TK.C.AIROW> then gosub add.rows", "         gosub add.rows")),
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
    print("test-aipage-units: tree %s" % os.path.dirname(GPL))
    if not raw["page"]:
        print("test-aipage-units: CANNOT RUN - %s is not there" % FILES["page"])
        return 2
    rows = checks(raw)
    bad = report(rows)
    print("\ntest-aipage-units: %d passed, %d failed" % (len(rows) - bad, bad))
    rc = 1 if bad else 0
    if "--selftest" in argv:
        rc = (selftest(raw) or rc)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
