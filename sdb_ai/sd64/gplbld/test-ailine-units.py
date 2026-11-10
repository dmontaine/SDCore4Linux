#!/usr/bin/env python3
"""test-ailine-units.py - the toolkit's AI line ($tk_ai) and its use by the home screen, as invariants read off the source (AI line stage 1, 23 Oct 2026).

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-ailine-units.py
  python3 .../test-ailine-units.py --selftest [--from=N]

No sudo, no install, no sd.  Exit 0 every check passed, 1 a check failed, 2 it could not run.  It reads the BASIC as text, comments removed, so a rule that survives only in a comment
does not count.  IT RUNS NOTHING OF SD: that the line really asks first, sends nothing on Cancel and starts a tile only on Accept is sandbox-ai-line.py.  What a text check is for:
the invariants are mostly ORDERING (the preview before the request, the offered ids before an action is used) and an edit that moves one still compiles.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.abspath(os.path.join(HERE, os.pardir))
GPL = os.path.join(SD64, "sdsys", "gpl.bp")
MSG = os.path.join(SD64, "sdsys", "messages")
FILES = {"tk_ai": os.path.join(GPL, "tk_ai"), "tool_home": os.path.join(GPL, "tool_home"), "tk.h": os.path.join(GPL, "tk.h"),
         "ide": os.path.join(GPL, "ide"), "sl_form": os.path.join(GPL, "sl_form"),
         "ced_edit": os.path.join(GPL, "ced_edit"), "ced_core": os.path.join(GPL, "ced_core"), "debug": os.path.join(GPL, "debug")}
MSGS = list(range(11635, 11653))
MSGS2 = list(range(11653, 11682))              # AI line stage 2 (the IDE: edits as diffs, 11653-11669) and stage 3 (SED, CED, the debugger: 11670-11681)


def read(p):
    with open(p, encoding="latin-1") as f:
        return f.read()


def strip_bas(t):
    out = []
    for ln in t.split("\n"):
        s = ln.lstrip()
        if s.startswith("*") or s.startswith("!"):
            continue
        out.append(re.sub(r";\*.*$", "", ln))
    return "\n".join(out)


def ordered(t, *needles):
    pos = -1
    for n in needles:
        i = t.find(n, pos + 1)
        if i < 0:
            return False
        pos = i
    return True


def load():
    s = {k: read(p) for k, p in FILES.items()}
    s["msgs"] = {n: (read(os.path.join(MSG, str(n))) if os.path.exists(os.path.join(MSG, str(n))) else None) for n in MSGS + MSGS2}
    return s


def checks(s):
    rows = []

    def ck(name, ok, detail=""):
        rows.append((name, bool(ok), detail))

    ai = strip_bas(s["tk_ai"])
    home = strip_bas(s["tool_home"])
    ask = ai[ai.find("run.ask:"):ai.find("read.proposal:")]
    prop = ai[ai.find("read.proposal:"):ai.find("clean:\n")]

    ck("A1 the preview comes first: the msgbox with Send and Cancel (Cancel the default), then the request is made, then the wait, then the answer is read",
       ordered(ask, "buttons '&Send,&Cancel' default 2", "if bn # 1 then", "kernel(K$AI.START", "kernel(K$AI.POLL", "jparse(rp<2>)", "gosub read.proposal"), "")
    ck("A2 nothing is sent on Cancel: the branch on bn # 1 returns before K$AI.START (there is no other call of it)", ai.count("K$AI.START") == 1 and ordered(ask, "if bn # 1 then", "return", "kernel(K$AI.START"), "")
    ck("A3 the preview shows EVERYTHING that leaves: the fixed instruction, every action line, what the page tells about itself and the request, with sizes (messages 11640 to 11644)",
       all(("sysmsg(%d" % n) in ask for n in (11640, 11641, 11642, 11643)) and "sysx" in ask and "prompt = " in ask, "")
    ck("A4 an action is used only if it is exactly one of the ids the app offered (a loop over the offered values, a match on the whole id), and the note 11649 is shown otherwise",
       ordered(prop, "for i = 1 to n.acts", "field(acts<1, i>, ':', 1) = act", "if found then", "pk = 'action'") and "sysmsg(11649" in prop and prop.count("found = ") == 2, "")
    ck("A5 the proposal's argument is cleaned twice: ASCII only, then only letters, digits and . _ : / - and space, 100 characters", "gosub clean" in prop and "[1, 100]" in prop
       and "'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._:/- '" in prop, "")
    ck("A6 a command is shown and never run here: no execute, no os.execute, no kernel call but the five K$AI.* of this file; it must be printable, at most 200 characters and unchanged by the cleaning",
       not re.search(r"\b(execute|os\.execute|perform)\b", ai) and "if len(c) > 200 or c # raw then" in prop and "sysmsg(11650)" in prop, "")
    ck("A7 a command's default button is the one that does NOT run it, and its letters are distinct (Run, Cancel): Enter alone never runs a command", "btn = '&Run,&Cancel'" in ask and re.search(r"btn = '&Run,&Cancel'[^\n]*\n\s*dflt = 2", ask) is not None, "")
    ck("A8 Enter alone accepts an action only when the app said the actions just navigate (actx<5>) AND the one proposed is not among the ids the app named as doing more (actx<12>: its own "
       "programs, the prompt), else it rejects - per proposal, not per page (handoff step 2, 28 Oct 26)",
       "dflt = (if nav and index(@vm : nav.not : @vm, @vm : pid : @vm, 1) = 0 then 1 else 2)" in ask and "nav = a<5>" in ask and "nav.not = a<12>" in ask, "")
    ck("A9 the model's text is read as ONE JSON object from the first { to the last } (a fence round it does no harm) and anything else is shown as words with the note 11651 and nothing proposed",
       ordered(prop, "index(atext, '{', 1)", "jparse(atext[f1, l1 - f1 + 1])", "sysmsg(11651)") and "obj.ok" in prop, "")
    ck("A10 a parsed JSON object is never compared with a string (that raises 'Value not found' and the error is swallowed: the answer popup never came, 23 Oct): a flag says whether obj holds one",
       not re.search(r"\bobj\s*(=|#)\s*''", ai) and not re.search(r"\bhj\s*(=|#)\s*''", ai), "")
    au = [l for l in ai.split("\n") if not l.lstrip().startswith("*") and "audit" in l.lower()]
    ck("A11 the audit line of a request that goes is the kernel's (K$AI.START): this file writes only the four audit lines of a REFUSAL (S.97 stage 0, a follow-up's earlier question, "
       "pinned by test-aiwall-units A3 and A5, and (S.160) a standing text that names SD's own code) and no other",
       len(au) == 4 and all("kernel(K$AUDIT, 'ai refused why=" in l for l in au), "")
    ck("CX1 (S.160) THE STANDING TEXT: read from the helper's status at each request, put to the wall's screen with the other screens and BEFORE the documentation is looked up, a refusal "
       "audited (never the text) and nothing sent; it goes FIRST in the system text; and it is INVISIBLE in the preview (the owner, 7 Nov 26): no line of the preview reads it",
       ordered(ask, "next hi", "cx.text = cxj{'context'}", "gosub clean.nl", "call $tk_aiwall('request', cx.text, why)",
               "void kernel(K$AUDIT, 'ai refused why=context app=' : downcase(app) : ' name=' : why)", "sysmsg(14013, why)", "return", "call $tk_aidocs('find', req, dres)",
               "if cx.text # '' then cx.send = 'Standing information from the administrator of this SD system:' : char(10) : cx.text", "ks = cx.send : sysx : @fm : 600")
       and not re.search(r"body<-1>[^\n]*\bcx\.(text|send)\b", ai) and not re.search(r"wr\.text = [^\n]*\bcx\.", ai), "")
    ck("A12 the app's words are cleaned like the person's: every offered action line goes through clean before the preview or the prompt", ordered(ask, "for i = 1 to dcount(a<4>, @vm)", "gosub clean", "acts<1, i> = ", "sysx = sysmsg(11635, app)"), "")
    ck("A13 the line is not drawn at all when the AI is not usable (the gate, a provider, a model and a key): read.status sets ai.on only after all four tests, and the other ops do nothing when it is 0",
       ordered(ai, "read.status:", "if not(hj{'gate'}) then return", "hj{'provider'} = ''", "if not(hj{'key'}) then return", "ai.on = 1") and ai.count("if ai.on then") >= 6, "")
    ck("A14 the wait gives up on Esc, on the cursor lock's way out and on an input that has ended, and cancels the request", ordered(ask, "screen key timeout 1 returning nm", "nm = 'esc' or nm = 'guardquit'", "ER$EOF", "kernel(K$AI.CANCEL, 0)"), "")
    mv = re.search(r"case op = 'move'\n(.*?)\n      case op = 'draw'", ai, re.S)
    mvb = mv.group(1) if mv else ""
    ck("A15 the 'move' op only puts the entry where the new window says (place.widget): it does not read the status, make the entry again, empty the text or touch the focus, and make.widget places the entry the same way before $sl_entry('init')",
       mv is not None and "gosub place.widget" in mvb and not any(w in mvb for w in ("read.status", "sl_entry", "ai.w =", "ai.focus", "ctx<TK.C.AI>", "'value'", "'pos'", "'pan'"))
       and ordered(ai, "make.widget:", "gosub place.widget", "call $sl_entry('init', ai.w, '', '', r)", "place.widget:", "ai.w{'ax'} = ", "ai.w{'ay'} = ", "ai.w{'w'} = ")
       and "place.widget:\n   lw = ctx<TK.C.W>" in ai, "")
    ck("H1 the home screen offers only tiles that start a tool: 'cmd:' tiles and the terminal; never Sign out or Switch account", "if ta[1, 4] = 'cmd:' or ta = 'terminal' then" in home
       and "acts<1, -1> = " in home, "")
    ck("H2 the page's text goes in as VALUES of one field (a field mark would move the fields after it: the action list was empty on 23 Oct), the navigation flag (actx<5>) is 1 and the ids of the "
       "offered actions that do more than open a tool - a pin, the Terminal tile - go in actx<12> (ai.more), so the library makes Reject the default for those proposals only (S.88 phase 2, S6; per proposal since step 2)",
       "ctxt := @vm : " in home and "@vm : 'Each action starts the tool" in home and re.search(r"actx = 'home' : @fm : 'home' : @fm : ctxt : @fm : acts : @fm : ai\.nav", home) is not None
       and "ai.nav = 1" in home and "ai.more = ''" in home and "if tl<i, HT.ID>[1, 3] = 'pin' or ta = 'terminal' then ai.more<1, -1> = tl<i, HT.ID>" in home
       and "actx<12> = ai.more" in home and "then ai.nav = 0" not in home, "")
    ck("H3 an accepted action is looked up by id among the page's own tiles and started through start.tile, as a click would; a command goes through run.command, as the Terminal's prompt would",
       ordered(home, "case res<1> = 'action'", "tl<i, HT.ID> = res<2>", "gosub start.tile", "case res<1> = 'command'", "gosub run.command"), "")
    # 8 Nov 26 (S.176, the owner: one box key on every page, "F6 for boxes is fine"): the tiles and the line are the two stops of the F6 ring; Tab goes round the tiles only
    ck("H4 F6 and Shift-F6 move between the tiles and the AI line both ways (ai.key gives the line up on them before $tk_ai sees the key), and Tab / Back-tab go round the tiles only, never onto the line",
       "case nm = 'f6' or nm = 'shift-f6'\n         if ctx<TK.C.AI> then\n            gosub ai.focus.on" in home
       and ordered(home, "ai.key:", "if nm = 'f6' or nm = 'shift-f6' then", "gosub ai.leave", "return", "call $tk_ai('key', ctx, nm, out)")
       and "if ctx<TK.C.AI> and fi = nt then" not in home and "if ctx<TK.C.AI> and fi = 1 then" not in home, "")
    ck("H5 the hint row is drawn only when there is no AI line, the AI line is made again in a new session and on F5 (three init calls), and a resize only MOVES it (p3.3a: the request typed in it and its focus aif are kept, and the resize no longer sets aif = 0)",
       home.count("call $tk_ai('init', ctx, '', '')") == 3 and home.count("call $tk_ai('move', ctx, '', '')") == 1 and "if ctx<TK.C.AI> then\n      call $tk_ai('draw', ctx, aif, '')" in home
       and re.search(r"gen \+= 1\n   ctx<TK\.C\.GEN> = gen\n   lastmin = ''\n   call \$tk_ai\('move', ctx, '', ''\)", home) is not None, "")
    ck("H6 while the line has the focus no tile does (draw.tile), and the cursor is in the line (the loop draws it and does not park the cursor on the status line)",
       "if aif then focused = 0" in home and ordered(home, "if aif then", "call $tk_ai('draw', ctx, 1, '')", "call $sl_curat(0, ctx<TK.C.YSTAT>)"), "")
    ck("M1 messages 11635 to 11652 exist, each one line", all(s["msgs"][n] is not None and len(s["msgs"][n].rstrip("\n").split("\n")) == 1 for n in MSGS), repr([n for n in MSGS if s["msgs"][n] is None]))
    ck("M2 the fixed instruction (11635) asks for ONE JSON object with say, action, arg and command, plain ASCII, and offers an action only for a request the list covers",
       all(w in (s["msgs"][11635] or "") for w in ('"say"', '"action"', '"arg"', '"command"', "ONE JSON object", "Plain ASCII only")), "")
    ck("T1 tk.h defines TK.C.AI (11)", re.search(r"\$define TK\.C\.AI\s+11\b", s["tk.h"]) is not None, "")

    # AI line stage 2 (24 Oct 2026): proposals as edits, and the IDE
    edits = ai[ai.find("read.edits:"):ai.find("map1:")]
    ide = strip_bas(s["ide"])
    apply_ = ide[ide.find("ai.apply:"):ide.find("get.context:")]
    ck("E1 edits are all or none: a set with one edit that does not fit gives the note 11660 and returns BEFORE the diff is built and before pk is set to 'edit'",
       ordered(edits, "if bad.why # '' then", "note.p = sysmsg(11660, bad.why)", "return", "diff.lines = ''", "pk = 'edit'"), "")
    ck("E2 an old text must be in the text shown exactly once and be what the model was shown there (not found, found twice, differs from the original)",
       ordered(edits, "ep = index(tbm, eo, 1)", "bad.why = 'old text not found'", "index(tbm, eo, 2) > 0", "bad.why = 'old text found more than once'", "tb.raw[ep, len(eo)] # eo"), "")
    ck("E3 at most 8 edits, no empty old text, no new text over 4000 bytes, no two edits that overlap, and a diff of more than 30 lines is not offered (11659)",
       all(w in edits for w in ("for ei = 1 to 8", "'more than 8 edits'", "bad.why = 'an empty old text'", "len(en) > 4000", "epos<i> + elen<i> > epos<i + 1>", "bad.why = 'two edits overlap'", "if dl > 30 then", "sysmsg(11659, dl)")), "")
    ck("E4 a change to a text is never accepted by Enter alone: the popup of an edit has Accept and Reject and Reject is the default", re.search(r"case pk = 'edit'.*?btn = '&Accept,&Reject'\s*\n\s*dflt = 2", ask, re.S) is not None, "")
    ck("E5 the diff shows EVERY edit in full: each old line with -, each new line with +, the change number and the line it is at (11658)",
       ordered(edits, "sysmsg(11658, k, ed.n, line.no)", "wr.p1 = '- ' ; wr.p2 = '  '", "wr.text = field(eo, nl, j)", "gosub wrap.exact", "wr.p1 = '+ ' ; wr.p2 = '  '", "wr.text = field(en, nl, j)", "gosub wrap.exact"), "")      # 28 Oct 26 (S5): a long line goes on in rows (test-aiwrap-units.py)
    ck("E6 an app that has nowhere to run a command says so ('nocmd') and a command is then ignored; an action is looked for first, edits second, a command last",
       "no.cmd" in ai and ordered(prop, "if found then", "if pk = '' and tbm # '' then gosub read.edits", "if pk = '' and not(no.cmd) then"), "")
    ck("E7 the accepted edits are returned only for an edit proposal, with the model's own words: pk, the edit list, the argument, the words", "(if pk = 'action' then pid else (if pk = 'edit' then ed.list else pcmd))" in ask, "")
    splice = ai[ai.find("splice.edits:"):ai.find("* ----", ai.find("splice.edits:"))]
    ck("I1 the edits are applied only if the buffer still holds, at every place, exactly what the model was shown ($tk_ai 'splice'): it answers null otherwise, and the IDE then says 11666, changes nothing and returns",
       ordered(splice, "s.now[s.off + s.p, s.l] # s.win[s.p, s.l]", "if not(s.fits) then return", "s.new = s.now")
       and ordered(apply_, "call $tk_ai('splice'", "if ai.sp = '' then", "msg = sysmsg(11666)", "return", "mw{'value'} = "), "")
    # 28 Oct 26 (TUI phase 2 review): through the memo's own 'snap' op, which keeps the step in the memo's form (the old mw{'undo'} push was the legacy form, whose value marks came back as line ends)
    ck("I2 the change is ONE undo step: the memo's own 'snap' puts the old text and cursor on its undo steps (and forgets redo) before the new value is set; the IDE writes no undo key itself",
       ordered(apply_, "call $sl_memo('snap', mw,", "mw{'value'} = ") and not re.search(r"\{'(undo|redo)'\}", apply_), "")
    ck("I3 the IDE writes nothing to the disk for the AI: no write, no save in the routine that applies the edits", not re.search(r"\b(write|writev|save|do\.save|delete)\b", apply_), "")
    ck("I4 the AI is asked through $tk_ai only, only when a record is open, and the IDE gives the text, the line it starts at, the selection and 'nocmd'",
       ide.count("call $tk_ai('ask'") == 1 and ordered(ide, "ai.go:", "if nbuf = 0 then", "msg = sysmsg(11662)", "call $tk_ai('ask'") and "ai.sel : @fm : 'nocmd'" in ide, "")
    ck("I5 the AI entry, the AI menu and the shorter table exist only when the AI is usable (ai.on, from $tk_ai usable)", "call $tk_ai('usable', '', ai.on, ai.pm)" in ide and "ai.rows = (if ai.on then 1 else 0)" in ide
       and "if j = 11230 and ai.on then" in ide and ordered(ide, "if ai.on then", "screen label f, 'ailab'", "screen entry f, 'ai'"), "")
    ck("I6 a request typed in the AI entry goes through the same route as the menu (ai.go), and only on Enter (the entry activates)", "case focus.id = 'ai'" in ide and "gosub ai.go" in ide and "aw{'activate'} = 1" in ide, "")
    ck("I7 sl_form lets an entry activate on Enter only when the app asked for it (the flag), so no other form's entry changes", "(aw{'type'} = 'entry' and aw{'activate'} + 0)" in strip_bas(s["sl_form"]), "")
    ck("M3 messages 11653 to 11681 exist, each one line", all(s["msgs"][n] is not None and len(s["msgs"][n].rstrip("\n").split("\n")) == 1 for n in MSGS2), repr([n for n in MSGS2 if s["msgs"][n] is None]))

    # AI line stage 3 (24 Oct 2026): SED, CED and the debugger
    ced = strip_bas(s["ced_core"])               # 30 Oct 26: CED's AI code is the engine's (ced_core); the host (ced_edit) asks whether the AI is usable and hands the answer over
    ced_host = strip_bas(s["ced_edit"])
    ced_ai = ced[ced.find("ai.menu:"):ced.find("revert:")]
    dbg = strip_bas(s["debug"])
    dbg_ai = dbg[dbg.find("ai.run:"):dbg.find("help:")]
    ck("X1 the shared routines are the library's: 'select', 'window' and 'splice' are in $tk_ai and the IDE and SED use them (SED the first, the IDE and CED the window), no editor has its own copy",
       all(("case op = '%s'" % o) in ai for o in ("select", "window", "splice")) and "call $tk_ai('window'" in ide and "call $tk_ai('splice'" in ide and "call $tk_ai('select'" in ide
       and "call $tk_ai('window'" in ced and "call $tk_ai('splice'" in ced
       and "ai.total = dcount" in ide and "> 24000" not in ide, "")
    ck("X5 CED offers F2 only when the AI is usable; an accepted set must leave a JSON collection or array (else 11677 and c is not touched); the old record is kept for one undo BEFORE c is replaced; the routines save nothing",
       "case c.key = 'f2' and ai.ok" in ced and "call $tk_ai('usable', '', ai.ok, ai.pm)" in ced_host and "st{'ai.ok'} = ai.ok" in ced_host
       and ordered(ced_ai, "ai.apply:", "call $tk_ai('splice'", "ai.y = jparse(ai.sp<1>)", "if ai.bad then", "sysmsg(11677)", "return", "ai.undo = jbuild(c)", "c = ai.y", "dirty = @true")
       and "'nocmd'" in ced_ai and not re.search(r"\b(save\.record|writeu|writev)\b", ced_ai), "")
    ck("X6 the debugger offers the command AI only in the full-screen display and when the AI is usable (ai.ok is set only under full.screen), sends no text to edit (so no edit is asked for), ignores a command, and draws the screen again after",
       ordered(dbg, "ai.ok = 0", "if full.screen then call $tk_ai('usable', '', ai.ok, ai.pm)") and "case action = 'AI' and ai.ok" in dbg and ": @fm : '' : @fm : 1 : @fm : '' : @fm : 'nocmd'" in dbg_ai
       and ordered(dbg_ai, "call $tk_ai('ask'", "gosub relayout") and "'edit'" not in dbg_ai, "")

    # 3 Nov 26 (S.97): a form's fields, and the follow-up
    fields = ai[ai.find("read.fields:"):ai.find("read.edits:")]
    keep = ai[ai.find("follow.keep:"):ai.find("follow.drop:")]
    ck("FD1 a form's fields (actx<14>) are cleaned as the actions are and are in the instruction, the prompt and the preview (with their count and size) only when the app gave some",
       ordered(ask, "for i = 1 to dcount(a<14>, @vm)", "gosub clean", "flds<1, i> = trim(clean.out)[1, 120]", "n.flds = dcount(flds, @vm)", "if n.flds > 0 then", "This page is a form.",
               "if n.flds > 0 then prompt := 'Fields of this form", "if n.flds > 0 then", "The form's fields (", "wr.text = flds<1, i>", "screen msgbox body"), "")
    ck("FD2 \"fields\" is read only when the app offered fields and nothing else was proposed; a name is used only when it is EXACTLY one of the keys offered (the cleaning changed nothing) and once; "
       "a value that is not text or a number is left out; each is cleaned to ASCII with its line feeds and cut at 2000; what is left out is said",
       "if pk = '' and n.flds > 0 then gosub read.fields" in prop and ordered(fields, "if jtype(obj{'fields'}) # 'collection' then return", "fnames = enumerate(fo)",
               "trim(field(flds<1, j>, ':', 1)) = fk", "if offered and fk = fnm then", "index(@vm : fl.keys : @vm, @vm : fk : @vm, 1)", "if offered then ft = jtype(fo{fnm})",
               "if ft = 'string' or ft = 'number' then", "gosub clean.nl", "fl.vals<1, fl.n> = clean.out[1, 2000]", "fl.skip<1, -1>", "note.p = ", "if fl.n > 0 then pk = 'fields'")
       and fields.count("offered = 1") == 1 and ordered(fields, "offered = 0", "for j = 1 to n.flds", "offered = 1", "next j"), "")
    ck("FD3 proposed values are shown in full (every line of every value, in rows of exactly its characters) with Accept and Reject, and Reject is the default; only Accept returns them, as "
       "'fields', the keys and the values; the library fills nothing",
       re.search(r"case pk = 'fields'.*?for j = 1 to dcount\(fv, nl\).*?gosub wrap\.exact.*?btn = '&Accept,&Reject'\s*\n\s*dflt = 2", ask, re.S) is not None
       and "case pk = 'fields' and bn = 1" in ask and "b = 'fields' : @fm : fl.keys : @fm : fl.vals : @fm : say : @fm : ''" in ask, "")
    ck("FU1 FOLLOW UP is the LAST button of every answer's box and never its default (the person's choice, each time); choosing it applies nothing and returns 'follow'",
       ordered(ask, "fu.bn = dcount(btn, ',') + 1", "btn := ',&Follow up'", "buttons btn default dflt", "case bn = fu.bn", "gosub follow.keep", "b = 'follow' : @fm : '' : @fm : '' : @fm : say")
       and ask.find("case bn = fu.bn") < ask.find("case pk = 'fields' and bn = 1") and "default fu.bn" not in ask and "dflt = fu.bn" not in ask, "")
    ck("FU2 a follow-up is taken only for the SAME app, the same account and within 10 minutes, and is dropped at once (used once) whatever happens to the request; 'init' drops it too",
       ordered(ask, "h.q = '' ; h.a = '' ; h.n = 0", "if ai.fq # '' then", "if ai.fapp = app and ai.fwho = @who and (date() * 86400 + time()) - ai.ft <= 600 then", "h.q = ai.fq", "gosub follow.drop",
               "call $tk_aiwall('request', req, why)")
       and ordered(ai, "case op = 'init'", "gosub read.status", "gosub follow.drop", "ai.line = ai.on"), "")
    ck("FU3 the preview shows every earlier question and answer IN FULL (wrap.exact, no line limit) before the request, and its size counts them; the earlier exchanges go to K$AI.START as "
       "maxtokens VM n then the questions and answers, the prompt last, and there is still ONE call of it",
       ordered(ask, "size = len(cx.send) + len(sysx) + len(prompt) + h.bytes", "if h.n > 0 then", "A follow-up: ", "wr.text = h.q<i>", "gosub wrap.exact", "wr.text = h.a<i>", "gosub wrap.exact", "sysmsg(11643, len(req))",
               "ks = cx.send : sysx : @fm : 600", "ks := @vm : h.n", "ks := @fm : h.q<i> : @fm : h.a<i>", "ks := @fm : prompt", "rq = kernel(K$AI.START, ks)") and ai.count("K$AI.START") == 1, "")
    ck("FU4 what is kept: this request and the AI's answer after the exchanges this one carried, the last 3 at most, with the app, the account and the time",
       ordered(keep, "nq = h.q ; na = h.a", "nq<h.n + 1> = req", "na<h.n + 1> = atext[1, 2000]", "while dcount(nq, @fm) > 3", "nq = field(nq, @fm, 2, 999)", "ai.fq = nq", "ai.fapp = app",
               "ai.ft = date() * 86400 + time()", "ai.fwho = @who"), "")
    ck("FU5 the library's line says so while a follow-up is kept (its label, and the 'show' signature has the flag so that it is drawn again)", "ai.label = (if ai.fq # '' then 'AI follow-up>' else sysmsg(11636)) : ' '" in ai
       and "ai.w{'pan'} : '/' : (ai.fq # '')" in ai and ordered(ai, "paint:", "gosub place.widget"), "")
    return rows


MUTANTS = [
    ("the preview is skipped", "tk_ai", "   if bn # 1 then\n      b = 'none'", "   if @false then\n      b = 'none'", "A1"),
    ("Send is the default button", "tk_ai", "buttons '&Send,&Cancel' default 2", "buttons '&Send,&Cancel' default 1", "A1"),
    ("any action id is accepted", "tk_ai", "      if found then\n         pk = 'action'", "      found = 1\n      if found then\n         pk = 'action'", "A4"),
    ("a command is run", "tk_ai", "            pk = 'command'\n            pcmd = c", "            pk = 'command'\n            pcmd = c\n            execute c", "A6"),
    ("a command's default is Run", "tk_ai", "         dflt = 2\n      case 1\n         btn = '&Close'", "         dflt = 1\n      case 1\n         btn = '&Close'", "A7"),
    ("Run and Reject share a letter", "tk_ai", "btn = '&Run,&Cancel'", "btn = '&Run,&Reject'", "A7"),
    ("an object is compared with a string", "tk_ai", "   if not(obj.ok) then", "   if obj = '' then", "A10"),
    ("Sign out is offered", "tool_home", "if ta[1, 4] = 'cmd:' or ta = 'terminal' then", "if ta[1, 4] = 'cmd:' or ta = 'terminal' or ta = 'signout' then", "H1"),
    ("the page's lines are fields", "tool_home", "ctxt := @vm : 'The person is '", "ctxt := @fm : 'The person is '", "H2"),
    ("the line is drawn without the AI", "tk_ai", "   if not(hj{'key'}) then return", "   null", "A13"),
    # AI line stage 2 (24 Oct 2026): the first of these is marker 10 for --from=10
    ("an old text found twice is accepted", "tk_ai", "               case index(tbm, eo, 2) > 0\n", "               case @false\n", "E2"),
    ("a bad edit is only skipped, not the whole set", "tk_ai", "      note.p = sysmsg(11660, bad.why)\n      return\n", "      note.p = sysmsg(11660, bad.why)\n", "E1"),
    ("Enter accepts an edit", "tk_ai", "         dflt = 2                                         ;* a change to a text is never accepted by Enter alone", "         dflt = 1", "E4"),
    ("splice applies without the fit test", "tk_ai", "      if s.now[s.off + s.p, s.l] # s.win[s.p, s.l] then s.fits = 0", "      null", "I1"),
    ("the IDE's change is not an undo step", "ide", "   call $sl_memo('snap', mw, '', '', ai.sr)\n", "", "I2"),
    ("the IDE saves after applying", "ide", "   msg = sysmsg(11661, ai.n)\n", "   msg = sysmsg(11661, ai.n)\n   write ai.new on fv, bi<cb>\n", "I3"),
    ("the IDE does not say nocmd", "ide", "ai.sel : @fm : 'nocmd'", "ai.sel", "I4"),
    ("every entry activates", "sl_form", "(aw{'type'} = 'entry' and aw{'activate'} + 0)", "aw{'type'} = 'entry'", "I7"),
    # AI line stage 3 (24 Oct 2026): the first of these is marker 18 for --from=18
    ("CED accepts invalid JSON", "ced_core", "   if ai.bad then\n      message.text = sysmsg(11677)\n      return\n   end\n", "   if ai.bad then\n      ai.y = jparse('{}')\n   end\n", "X5"),
    ("CED replaces c before keeping the old record", "ced_core", "   ai.undo = jbuild(c)\n   c = ai.y\n", "   c = ai.y\n   ai.undo = jbuild(c)\n", "X5"),
    ("CED saves after applying", "ced_core", "   message.text = sysmsg(11676, ai.sp<3>)\n", "   gosub save.record\n   message.text = sysmsg(11676, ai.sp<3>)\n", "X5"),
    ("the debugger offers AI outside the full-screen display", "debug", "   if full.screen then call $tk_ai('usable', '', ai.ok, ai.pm)", "   call $tk_ai('usable', '', ai.ok, ai.pm)", "X6"),
    ("the debugger sends text to edit", "debug", ": @fm : '' : @fm : 1 : @fm : '' : @fm : 'nocmd'", ": @fm : ai.page : @fm : 1 : @fm : '' : @fm : 'nocmd'", "X6"),
    # 28 Oct 26 (TUI phase 2 review): the IDE's AI step in the memo's old form (value marks for line ends), which the memo reads as legacy - marker 27 for --from=27
    ("the IDE pushes the old-form step again", "ide", "   call $sl_memo('snap', mw, '', '', ai.sr)\n", "   mw{'undo'} = mw{'cy'} : @tm : mw{'cx'} : @tm : convert(@fm, @vm, mw{'value'}) : @fm : mw{'undo'}\n", "I2"),
    # 28 Oct 26 (handoff step 2): the AI's default is per proposal - the first of these is marker 28 for --from=28
    ("the proposed action is not asked about (a pin is accepted by Enter)", "tk_ai", "if nav and index(@vm : nav.not : @vm, @vm : pid : @vm, 1) = 0 then 1 else 2", "if nav then 1 else 2", "A8"),
    ("every action is a rejection by default again", "tk_ai", "if nav and index(@vm : nav.not : @vm, @vm : pid : @vm, 1) = 0 then 1 else 2", "if 0 then 1 else 2", "A8"),
    ("the library never learns which actions do more", "tool_home", "   actx<12> = ai.more ", "   null ", "H2"),
    ("a pin is not named as doing more", "tool_home", "if tl<i, HT.ID>[1, 3] = 'pin' or ta = 'terminal' then ai.more<1, -1> = tl<i, HT.ID>", "if ta = 'terminal' then ai.more<1, -1> = tl<i, HT.ID>", "H2"),
    # 29 Oct 26 (S.88 p3.3a): a resize moves the home screen's AI line - the first of these is marker 32 for --from=32
    ("a resize makes the AI line again (the typed request is lost)", "tool_home", "   call $tk_ai('move', ctx, '', '')", "   aif = 0\n   call $tk_ai('init', ctx, '', '')", "H5"),
    ("a resize clears the line's focus", "tool_home", "   call $tk_ai('move', ctx, '', '')", "   aif = 0\n   call $tk_ai('move', ctx, '', '')", "H5"),
    ("the move reads the status again", "tk_ai", "      case op = 'move'\n         if ai.on then gosub place.widget", "      case op = 'move'\n         gosub read.status\n         if ai.on then gosub place.widget", "A15"),
    ("the move makes the entry again", "tk_ai", "      case op = 'move'\n         if ai.on then gosub place.widget", "      case op = 'move'\n         if ai.on then gosub make.widget", "A15"),
    ("the move empties the text", "tk_ai", "      case op = 'move'\n         if ai.on then gosub place.widget", "      case op = 'move'\n         if ai.on then ai.w{'value'} = ''\n         if ai.on then gosub place.widget", "A15"),
]
M_STAGE2 = 10
M_STAGE3 = 18
M_S97 = len(MUTANTS)            # 3 Nov 26 (S.97, the form's fields and the follow-up): the first mutant of the sitting, for --selftest --from=M_S97
MUTANTS += [
    ("a field name that was not offered is used", "tk_ai", "      if offered and fk = fnm then", "      offered = 1\n      if offered and fk = fnm then", "FD2"),
    ("a value that is not text is used", "tk_ai", "      if ft = 'string' or ft = 'number' then", "      if ft # '' then", "FD2"),
    ("Enter accepts proposed values", "tk_ai", "         dflt = 2                                         ;* a form is never filled by Enter alone", "         dflt = 1", "FD3"),
    ("the values are returned whatever was chosen", "tk_ai", "      case pk = 'fields' and bn = 1", "      case pk = 'fields'", "FD3"),
    ("Follow up is the default button", "tk_ai", "   screen msgbox body title sysmsg(11639) buttons btn default dflt returning bn else bn = 0\n   begin case",
     "   dflt = fu.bn\n   screen msgbox body title sysmsg(11639) buttons btn default dflt returning bn else bn = 0\n   begin case", "FU1"),
    ("a follow-up is used again and again", "tk_ai", "         h.n = dcount(h.q, @fm)\n      end\n      gosub follow.drop", "         h.n = dcount(h.q, @fm)\n      end", "FU2"),
    ("a follow-up never times out", "tk_ai", " and (date() * 86400 + time()) - ai.ft <= 600 then", " then", "FU2"),
    ("the preview does not show the earlier answers", "tk_ai", "         wr.text = h.a<i>\n", "         wr.text = ''\n", "FU3"),
    ("more than 3 exchanges are kept", "tk_ai", "   while dcount(nq, @fm) > 3\n", "   while dcount(nq, @fm) > 9\n", "FU4"),
]
M_S160 = len(MUTANTS)           # 7 Nov 26 (S.160, the standing text): --selftest --from=M_S160
MUTANTS += [
    ("the standing text is shown in the preview", "tk_ai", "   body<-1> = sysmsg(11640, len(sysx))", "   body<-1> = cx.text\n   body<-1> = sysmsg(11640, len(sysx))", "CX1"),
    ("the standing text is not screened", "tk_ai", "      call $tk_aiwall('request', cx.text, why)\n", "      why = ''\n", "CX1"),
    ("the standing text is not sent", "tk_ai", "   ks = cx.send : sysx : @fm : 600", "   ks = sysx : @fm : 600", "CX1"),
]
M_S176 = len(MUTANTS)           # 8 Nov 26 (S.176, F6 the box key of every page): --selftest --from=M_S176
MUTANTS += [
    ("F6 typed in the AI line goes into the line", "tool_home", "   if nm = 'f6' or nm = 'shift-f6' then\n      gosub ai.leave", "   if 0 then\n      gosub ai.leave", "H4"),
    ("Tab steps onto the AI line again", "tool_home", "      case nm = 'tab'\n         dir = 1\n         gosub next.tile",
     "      case nm = 'tab'\n         dir = 1\n         if ctx<TK.C.AI> and fi = nt then gosub ai.focus.on else gosub next.tile", "H4"),
]


def run(over=None):
    s = load()
    if over:
        s.update(over)
    return checks(s)


def selftest(first=0):
    base = run()
    base_fail = {n.split()[0] for n, ok, _ in base if not ok}
    print("selftest: the unchanged tree fails %d check(s): %s" % (len(base_fail), ", ".join(sorted(base_fail)) or "none"))
    if base_fail:
        return 1
    s0 = load()
    bad = 0
    for name, key, old, new, want in MUTANTS[first:]:
        if s0[key].count(old) != 1:
            print("  [FAIL] selftest: %s: the old text occurs %d times in %s, not once" % (name, s0[key].count(old), key))
            bad += 1
            continue
        failed = [n.split()[0] for n, ok, _ in run({key: s0[key].replace(old, new)}) if not ok]
        hit = want in failed
        print("  [%s] selftest: %s is caught by %s (failed: %s)" % ("PASS" if hit else "FAIL", name, want, " ".join(failed) or "none"))
        bad += 0 if hit else 1
    print("selftest: %s" % ("every mutant was caught" if bad == 0 else "%d problem(s)" % bad))
    return 0 if bad == 0 else 1


def main(argv):
    for k, p in FILES.items():
        if not os.path.exists(p):
            print("test-ailine-units: CANNOT RUN - %s is missing" % k)
            return 2
    if "--selftest" in argv:
        first = 0
        for a in argv:
            if a.startswith("--from="):
                first = int(a[len("--from="):])
        return selftest(first)
    rows = run()
    bad = 0
    for n, ok, d in rows:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", n, "" if ok else "   <- " + str(d)[:300]))
        bad += 0 if ok else 1
    print("test-ailine-units: %d checks, %d failed" % (len(rows), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
