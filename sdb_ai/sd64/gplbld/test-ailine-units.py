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
FILES = {"tk_ai": os.path.join(GPL, "tk_ai"), "tool_home": os.path.join(GPL, "tool_home"), "tk.h": os.path.join(GPL, "tk.h")}
MSGS = list(range(11635, 11653))


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
    s["msgs"] = {n: (read(os.path.join(MSG, str(n))) if os.path.exists(os.path.join(MSG, str(n))) else None) for n in MSGS}
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
    ck("A8 Enter alone accepts an action only when the app said every action just navigates (actx<5>), else it rejects", "dflt = (if nav then 1 else 2)" in ask and "nav = a<5>" in ask, "")
    ck("A9 the model's text is read as ONE JSON object from the first { to the last } (a fence round it does no harm) and anything else is shown as words with the note 11651 and nothing proposed",
       ordered(prop, "index(atext, '{', 1)", "jparse(atext[f1, l1 - f1 + 1])", "sysmsg(11651)") and "obj.ok" in prop, "")
    ck("A10 a parsed JSON object is never compared with a string (that raises 'Value not found' and the error is swallowed: the answer popup never came, 23 Oct): a flag says whether obj holds one",
       not re.search(r"\bobj\s*(=|#)\s*''", ai) and not re.search(r"\bhj\s*(=|#)\s*''", ai), "")
    ck("A11 the audit line is the kernel's: this file writes none and calls no audit of its own", "K$AUDIT" not in ai and "audit" not in ai.lower().replace("the audit", ""), "")
    ck("A12 the app's words are cleaned like the person's: every offered action line goes through clean before the preview or the prompt", ordered(ask, "for i = 1 to dcount(a<4>, @vm)", "gosub clean", "acts<1, i> = ", "sysx = sysmsg(11635, app)"), "")
    ck("A13 the line is not drawn at all when the AI is not usable (the gate, a provider, a model and a key): read.status sets ai.on only after all four tests, and the other ops do nothing when it is 0",
       ordered(ai, "read.status:", "if not(hj{'gate'}) then return", "hj{'provider'} = ''", "if not(hj{'key'}) then return", "ai.on = 1") and ai.count("if ai.on then") >= 6, "")
    ck("A14 the wait gives up on Esc, on the cursor lock's way out and on an input that has ended, and cancels the request", ordered(ask, "screen key timeout 1 returning nm", "nm = 'esc' or nm = 'guardquit'", "ER$EOF", "kernel(K$AI.CANCEL, 0)"), "")
    ck("H1 the home screen offers only tiles that start a tool: 'cmd:' tiles and the terminal; never Sign out or Switch account", "if ta[1, 4] = 'cmd:' or ta = 'terminal' then" in home
       and "acts<1, -1> = " in home, "")
    ck("H2 the page's text goes in as VALUES of one field (a field mark would move the fields after it: the action list was empty on 23 Oct), and every action is a navigation (actx<5> = 1)",
       "ctxt := @vm : " in home and "@vm : 'Each action starts the tool" in home and re.search(r"actx = 'home' : @fm : 'home' : @fm : ctxt : @fm : acts : @fm : 1", home) is not None, "")
    ck("H3 an accepted action is looked up by id among the page's own tiles and started through start.tile, as a click would; a command goes through run.command, as the Terminal's prompt would",
       ordered(home, "case res<1> = 'action'", "tl<i, HT.ID> = res<2>", "gosub start.tile", "case res<1> = 'command'", "gosub run.command"), "")
    ck("H4 the AI line is the last stop of the Tab ring and the first of Back-tab, and without the AI the old keys are unchanged (the tests ask ctx<TK.C.AI>)", "if ctx<TK.C.AI> and fi = nt then" in home and "if ctx<TK.C.AI> and fi = 1 then" in home, "")
    ck("H5 the hint row is drawn only when there is no AI line, and the AI line is made again on a resize, a new session and F5", home.count("call $tk_ai('init', ctx, '', '')") >= 4 and "if ctx<TK.C.AI> then\n      call $tk_ai('draw', ctx, aif, '')" in home, "")
    ck("H6 while the line has the focus no tile does (draw.tile), and the cursor is in the line (the loop draws it and does not park the cursor on the status line)",
       "if aif then focused = 0" in home and ordered(home, "if aif then", "call $tk_ai('draw', ctx, 1, '')", "call $sl_curat(0, ctx<TK.C.YSTAT>)"), "")
    ck("M1 messages 11635 to 11652 exist, each one line", all(s["msgs"][n] is not None and len(s["msgs"][n].rstrip("\n").split("\n")) == 1 for n in MSGS), repr([n for n in MSGS if s["msgs"][n] is None]))
    ck("M2 the fixed instruction (11635) asks for ONE JSON object with say, action, arg and command, plain ASCII, and offers an action only for a request the list covers",
       all(w in (s["msgs"][11635] or "") for w in ('"say"', '"action"', '"arg"', '"command"', "ONE JSON object", "Plain ASCII only")), "")
    ck("T1 tk.h defines TK.C.AI (11)", re.search(r"\$define TK\.C\.AI\s+11\b", s["tk.h"]) is not None, "")
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
