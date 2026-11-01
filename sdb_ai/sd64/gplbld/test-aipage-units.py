#!/usr/bin/env python3
"""test-aipage-units.py - the AI line on a PAGE of the toolkit ($tk_aipage, S.97 stage 1), as invariants read off the source.  Free: no install, no sudo, no sd.

    python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-aipage-units.py [--selftest]

WHAT THIS IS, AND WHAT IT IS NOT.  It reads the BASIC of the library programs and of the two pilot pages (tool.voc, tool.files) as text, comments removed.  ***IT RUNS NOTHING, SO IT CANNOT
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
       and ordered(ap, "case op = 'init' or op = 'again'", "ctx<TK.C.AIROW> = ''", "if ctx<TK.C.AI> then", "ctx<TK.C.AIROW> = 1", "if op = 'init' then", "$tk_keys('add', keys, 'f6', 'ask ai', 'ai', '', 1)",
                  "$tk_keys('menu', keys, 'ai', '&AI', '&Ask the AI', '', '')", "end", "$tk_layout('refresh'"), "")
    ck("AP9", "WHAT IS OFFERED is the page's table (aiacts), the actions only NAVIGATE (<5> 1: Enter alone accepts), a command is ignored ('nocmd'), no file's text is sent (<13> 'none'), ONE ask, and an accepted action is carried out only through the key the table gives for it (keyof)",
       ap.count("$tk_ai('ask'") == 1 and "$tk_keys('aiacts', keys, pane, acts, '', '', '')" in ap and "acts : @fm : 1" in ap and "actx<11> = 'nocmd'" in ap and "actx<13> = 'none'" in ap
       and "$tk_keys('keyof', keys, res<2>, pane, kk, '', '')" in ap and "out = 'replay' : @fm : kk" in ap, "")
    ck("AP10", "the line takes a key only while it has the focus, and never the end of the input, a resize, the mouse or the cursor lock's guard; Esc, Tab, Back-tab, Up and Down give the focus back and clear the message",
       "$tk_ai('focused', ctx, foc, '')" in ap and "if foc and nm # '' and nm # 'resize' and nm # 'mouse' and nm # 'guardquit' then" in ap
       and "case ko = 'leave' or ko = 'tab' or ko = 'btab' or ko = 'up' or ko = 'down'" in ap, "")
    for pg, nm, opts, name in ((voc, "VOC", ["type", "state", "filter", "refresh"], "tool.voc"), (fil, "Files", ["filter", "refresh"], "tool.files")):
        got = re.findall(r"\$tk_keys\('ai', keys, '([a-z.]+)', '', '', '', ''\)", pg)
        pre = pg.find("$tk_aipage('init'")
        lastmenu = pg.rfind("$tk_keys('menu'")
        o1 = pg.find("call $tk_open(")
        hand = pg.find("call $tk_open(", o1 + 1) if o1 >= 0 else -1                   # the SECOND open of the toolkit: the page took the terminal back from the IDE or a verb
        again = pg.find("$tk_aipage('again'")
        decl2 = pg.find("gosub declare.layout", hand) if hand >= 0 else -1
        ck("AP11" + ("a" if nm == "VOC" else "b"), "%s offers the AI exactly %s (never edit, delete, quit, help, new, clear, analyse, indices, triggers or the menu), and asks for the line after its key table and before its first layout" % (name, ", ".join(opts)),
           sorted(got) == sorted(opts) and 0 < lastmenu < pre < pg.find("gosub declare.layout") and re.search(r"call \$tk_aipage\('init', ctx, keys, '', '', aout\)", pg) is not None, repr((got, lastmenu, pre)))
        ck("AP12" + ("a" if nm == "VOC" else "b"), "%s: the hook sees every key BEFORE the menu bar and the bar is not given a key the line used; an accepted proposal is replayed as the page's own key; the status line follows the answer; 'taken' is the first case; F6 and a click on the line reach it; the new context after a hand-over is given its row before its layout" % name,
           ordered(pg, "call $tk_aipage('key', ctx, keys, '%s', nm, ao)" % nm, "if ao<1> = 'replay' then nm = ao<2>", "if ao<1> # '' then msg = ao<4>", "if nm # '' and ao<1> = '' then call $tk_menubar('key', ctx, keys, '%s'" % nm,
                    "case ao<1> = 'taken'", "case nm = ''") and re.search(r"case nm = 'f6'\s*\n\s*call \$tk_aipage\('open', ctx, keys, '%s', '', ap\)" % nm, pg) is not None
           and ordered(pg, "call $tk_aipage('mouse', ctx, keys, '%s', mev, ap)" % nm, "call $tk_help('hit'") and hand > 0 and hand < again < decl2, repr((hand, again, decl2)))
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
