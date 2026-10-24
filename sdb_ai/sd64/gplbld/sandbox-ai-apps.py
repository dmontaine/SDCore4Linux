#!/usr/bin/env python3
#
# sandbox-ai-apps.py - the AI in SED, CED and the debugger (AI line stage 3), driven on a PSEUDO-TERMINAL on a private SD.  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-ai-apps.py <dir> [--build] [--mutant=NAME]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent).  Exit 0 every row passed, 1 a row failed, 2 it could not
# run.  With --mutant=NAME one change is made to the SANDBOX'S OWN COPY of a program and exit 0 means the rows that had to fail failed and no others (MUTANTS below).
#
# WHAT RUNS.  Everything sandbox-ai-ide.py runs (the real helper, the fake provider, an ordinary fixture account, the program under test on a 140 by 42 pty) - this file loads that
# one and uses its helpers.  What each app DID is read from the DISK afterwards (CT through a pipe session), never from what the screen said; "nothing was sent" from the fake's log.
#
#   S0-S1   SED, AI off: the Tools menu has no AI item and the command AI is not SED's;  AI on: Tools lists Ask the AI... and Explain the selection
#   S2-S6   Ask: the request is typed on the message row, Enter shows EVERYTHING that will be sent (nothing yet), Cancel is the default, Send makes ONE request and the kernel's one
#           audit line; the answer's edit is a diff; Accept puts it in the buffer (the screen shows it, the disk does not), ONE Ctrl-Z takes it back; Reject leaves the buffer
#   S7-S9   Explain the selection: no mark says so and sends nothing; with a mark the preview shows the selected text; the command typed with its request (Esc X, ai ...)
#   S10     an edit set that does not fit is ignored whole and said so
#   C0-C7   CED: F2 does nothing with the AI off; on, a menu of three; the preview shows the record as indented JSON; an edit is a diff; Accept changes the record (not the disk);
#           Ctrl-S saves; an edit that would leave invalid JSON is ignored; the AI's last change is undone from the menu; explain the selected element sends the element
#   D0-D3   the debugger: ai is not a command with the AI off; on, ai shows the program, the stack and the source round the stop in the preview; Send answers in words; the
#           debugger's screen is whole again (source, command line) and goes on working
# NOT HELD: the end of the input during the wait, a record over 24000 bytes, SED's split window, a real provider.
import importlib.util
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


ai = _load("sandbox_ai_ide_for_apps", "sandbox-ai-ide.py")
ids, gt = ai.ids, ai.gt
say = ids.say
TREE = ai.TREE
RET, ESC, TAB = ids.RET, ids.ESC, ids.TAB
F10 = ids.F10
DOWN, RIGHT = ai.DOWN, ai.RIGHT
CTRL_Z = ai.CTRL_Z
F2 = "\x1bOQ"
RUN = ai.RUN
CED_REC = "zzaic" + RUN                  # {"name":"widget","size":3,"tags":["a","b"]}
DBG_PROG = "zzaid" + RUN                 # x = 5 / y = 'abc' / debug / crt 'AFTER-DEBUG' / end
PROGS = ("tk_ai", "sed", "ced_edit", "debug")
TOOLS = RIGHT * 5                        # F10 opens File; Tools is the sixth title of SED's bar


def arow(rid, name, ok, detail=""):
    ai.arow(rid, name, ok, detail)


MUTANTS = {
    # name: (program of the sandbox, old text, new text, the row ids that must fail and no others)
    "sed-saves": ("sed", "   message = sysmsg(11661, ai.sp<3>)\n   gosub ai.say\n", "   gosub save.record\n   message = sysmsg(11661, ai.sp<3>)\n   gosub ai.say\n", ["S5", "S8"]),   # (S8: the saved record no longer holds what S8's preview looks for)
    "sed-no-selection": ("sed", "      if mark.line > 0 then\n         call $tk_ai('select'", "      if mark.line > 9999 then\n         call $tk_ai('select'", ["S8"]),
    "ced-saves": ("ced_edit", "   message.text = sysmsg(11676, ai.sp<3>)\n", "   gosub save.record\n   message.text = sysmsg(11676, ai.sp<3>)\n", ["C4"]),
    "ced-invalid-accepted": ("ced_edit", "   if ai.bad then\n      message.text = sysmsg(11677)\n      return\n   end\n", "   if ai.bad then\n      ai.y = jparse('{}')\n   end\n", ["C6", "C7"]),   # (C7: the record was replaced by {}, so there is no element to explain)
    "dbg-no-source": ("debug", "   for ai.q = ai.first to ai.last\n", "   for ai.q = ai.first to ai.first - 1\n", ["D2"]),   # (D2 reads the request at the fake; D1's preview shows only the first eight lines of the page)
}
MUTANT_SECTIONS = {"sed-saves": "sed", "sed-no-selection": "sed", "ced-saves": "ced", "ced-invalid-accepted": "ced", "dbg-no-source": "dbg"}


def make_json_record():
    prog = "zzaij" + RUN
    body = "\n".join(["   open 'bp' to f else stop 'no bp'",
                      "   write '{\"name\":\"widget\",\"size\":3,\"tags\":[\"a\",\"b\"]}' on f, '%s'" % CED_REC,
                      "   crt 'RECORDS DONE'", "end", ""])
    ai.put(os.path.join(ai.box(), "user_accounts", ai.ACC, "bp", prog), body)
    out = "\n".join(gt.plain(ai.ACC, ["BASIC bp %s" % prog, "RUN bp %s" % prog]))
    if "RECORDS DONE" not in out:
        ids.bail("the JSON record was not made:\n" + out[-500:])


def make_debug_program():
    src = "\n".join(["   x = 5", "   y = 'abc'", "   debug", "   crt 'AFTER-DEBUG'", "   debug", "   crt 'AFTER-TWO'", "end", ""])      # two stops: ai.ok lives in debug.h's common, set at the FIRST
    ai.put(os.path.join(ai.box(), "user_accounts", ai.ACC, "bp", DBG_PROG), src)
    out = "\n".join(gt.plain(ai.ACC, ["BASIC bp %s DEBUGGING" % DBG_PROG]))
    if "with no errors" not in out:
        ids.bail("the debugger's program did not compile:\n" + out[-500:])


ASK_KEY, EXPLAIN_KEY = "a", "p"           # the hotkeys in the Tools menu:  Ask the &AI...  and  Ex&plain the selection  (no earlier item of the menu has either letter)


def sed_open(rid):
    return ai.AccIde(ai.box(), cmd="SED bp %s" % rid)


def tools_has(e, text):
    e.keys(F10, TOOLS)
    T = e.text()
    e.keys(ESC)
    return text in T


def sed_ask(e, request):
    """Tools > Ask the AI..., the request on the message row, Enter: the preview."""
    e.keys(F10, TOOLS)
    e.keys(ASK_KEY)
    e.keys(request)
    e.keys(RET)
    return e.text()


def sec_sed_off():
    say("\n--- SED, the AI off")
    ai.configure(provider=False)
    ai.start_runner()
    e = sed_open(ai.OK_REC)
    arow("S0", "no provider: the Tools menu has no Ask the AI and no Explain the selection", tools_has(e, "Compile") and not tools_has(e, "Ask the AI") and not tools_has(e, "Explain the selecti"), "")
    e.end()
    ai.configure()
    ai.start_runner()


def sec_sed():
    say("\n--- SED, the AI on")
    fm = ai.STATE["fm"]
    e = sed_open(ai.OK_REC)
    arow("S1", "the Tools menu lists Ask the AI... and Explain the selection", tools_has(e, "Ask the AI...") and tools_has(e, "Explain the selecti"), e.text()[:300])
    n0, a0 = len(fm.log), ai.audit_off()
    T = sed_ask(e, "make the greeting longer [[edit_ok]]")
    arow("S2", "Enter on the request shows EVERYTHING that will be sent (the provider, the instruction naming SED, the record's lines, the request), Send and Cancel, and sends nothing",
         "This will be sent to anthropic" in T and "who is using SED" in T and "crt 'hello'" in T and "x = 1" in T and "make the greeting longer [[edit_ok]]" in T
         and "Send" in T and "Cancel" in T and len(fm.log) == n0, T[-1500:])
    e.keys(RET)
    arow("S3", "Enter on the default button is Cancel: nothing was sent (the fake's log and the audit file agree)", len(fm.log) == n0 and not ai.req_lines(ai.audit_new(a0)), repr((len(fm.log) - n0)))
    T = sed_ask(e, "make the greeting longer [[edit_ok]]")
    e.keys("s")
    T = ai.wait_popup(e)
    rq = ai.requests()
    pr = ai.prompt_of(rq[-1][2]) if len(rq) > n0 else ""
    rl = ai.req_lines(ai.audit_new(a0))
    arow("S4a", "Send: ONE request at the fake, the request as its last line, with the record's lines; ONE audit line, the kernel's, program tk_ai, none holds the record's text",
         len(fm.log) == n0 + 1 and pr.endswith("Request: make the greeting longer [[edit_ok]]") and "crt 'hello'" in pr and len(rl) == 1 and "program=tk_ai" in rl[0]
         and "crt 'hello'" not in ai.audit_new(a0), repr((len(fm.log) - n0, pr[-100:], rl)))
    arow("S4b", "the answer is a popup: what the AI said and the diff (the old line with -, the new with +) with Accept and Reject", "I made the greeting longer." in T and "- crt 'hello'" in T
         and "+ crt 'hello world'" in T and "[ Accept ]" in T and "[ Reject ]" in T, T[-900:])
    e.keys(RET)
    arow("S4c", "Enter alone is Reject: the buffer is as it was and so is the disk", "hello world" not in e.text() and "hello world" not in ai.rec(ai.OK_REC), "")
    sed_ask(e, "make the greeting longer [[edit_ok]]")
    e.keys("s")
    ai.wait_popup(e)
    e.keys("a")
    time.sleep(1.0)
    e.s.settle(0.6)
    T = e.text()
    arow("S5", "Accept: the buffer shows the new line, the disk does not have it, the message says it is in the editor", "crt 'hello world'" in T and "hello world" not in ai.rec(ai.OK_REC), T[-600:])
    e.keys(RIGHT)
    e.keys(CTRL_Z)
    time.sleep(0.8)
    T = e.text()
    arow("S6", "ONE Ctrl-Z takes the change back: the old line is in the buffer", "crt 'hello world'" not in T and "crt 'hello'" in T, T[-500:])
    # an edit set that does not fit
    sed_ask(e, "x [[edit_dup]]")
    e.keys("s")
    T = ai.wait_popup(e)
    arow("S10", "edit_dup: a set that does not fit is ignored whole and said so (found more than once), no Accept button", ai.msg(11660, "old text found more than once") in T and "[ Accept ]" not in T and "[ Close ]" in T, T[-700:])
    e.keys(RET)
    e.end()
    # the selection
    e = sed_open(ai.OK_REC)
    n0 = len(fm.log)
    e.keys(F10, TOOLS)
    e.keys(EXPLAIN_KEY)
    arow("S7", "Explain the selection with no mark: the message row says to set one (11671) and nothing is sent", ai.msg(11671)[:30] in e.text() and len(fm.log) == n0, e.text()[-300:])
    e.keys(RET)                                     # (the key that dismisses the message)
    e.keys("\x1b.")                                 # Esc . sets the mark (one chunk: a lone Esc is the menu)
    e.keys("\x1bOB")                                # a line down
    e.keys(F10, TOOLS)
    e.keys(EXPLAIN_KEY)
    T = e.text()
    arow("S8", "with a mark and the cursor a line down: the preview shows the selected text and its size and sends nothing", ai.msg(11669, 1).split("1")[0][:20] in T and "crt 'hello'" in T and len(fm.log) == n0, T[-900:])
    e.keys("s")
    T = ai.wait_popup(e)
    rq = ai.requests()
    pr = ai.prompt_of(rq[-1][2]) if len(rq) > n0 else ""
    arow("S8b", "Send: the prompt has the selected-text block with the first line and the standard request", "The selected text:" in pr and "crt 'hello'" in pr.split("The selected text:")[-1] and "Explain the selected text" in pr, repr(pr[-300:]))
    e.keys(RET)
    e.end()
    # the command typed, with its request
    e = sed_open(ai.OK_REC)
    n0 = len(fm.log)
    e.keys("\x1bx")                                 # Esc X: the command prompt
    e.keys("ai make it longer [[edit_ok]]", RET)
    T = e.text()
    arow("S9", "Esc X, then  ai make it longer [[edit_ok]]  goes straight to the preview with that request (the AI verb is not run), nothing sent yet", "This will be sent to anthropic" in T
         and "make it longer [[edit_ok]]" in T and len(fm.log) == n0, T[-700:])
    e.keys(RET)
    e.end()


def sec_ced_off():
    say("\n--- CED, the AI off")
    ai.configure(provider=False)
    ai.start_runner()
    e = ai.AccIde(ai.box(), cmd="CED bp %s" % CED_REC)
    e.keys(F2)
    T = e.text()
    arow("C0", "no provider: F2 does nothing (no AI menu), and the record is on screen", "Explain the selected element" not in T and "widget" in T, T[-400:])
    e.end()
    ai.configure()
    ai.start_runner()


def ced_ask(e, request):
    e.keys(F2)
    e.keys("a")                                      # &Ask the AI about this record
    e.keys(request, RET)
    return e.text()


def sec_ced():
    say("\n--- CED, the AI on")
    fm = ai.STATE["fm"]
    e = ai.AccIde(ai.box(), cmd="CED bp %s" % CED_REC)
    e.keys(F2)
    T = e.text()
    arow("C1", "F2 opens a menu of three: Explain the selected element, Ask the AI about this record, Undo the AI's last change", "Explain the selected element" in T and "Ask the AI about this record" in T
         and "Undo the AI's last change" in T, T[-600:])
    e.keys(ESC)
    n0 = len(fm.log)
    T = ced_ask(e, "raise the size [[ced_ok]]")
    arow("C2", "Ask: the preview shows the record as indented JSON, one element to a line, and the request; Send and Cancel; nothing sent", "This will be sent to anthropic" in T and "who is using CED" in T
         and '"size": 3' in T and '"name": "widget"' in T and "raise the size [[ced_ok]]" in T and len(fm.log) == n0, T[-1400:])
    e.keys("s")
    T = ai.wait_popup(e)
    arow("C3", "the answer is a diff of the text (the old line with -, the new with +) with Accept and Reject; the table still shows 3", '- "size": 3' in T and '+ "size": 4' in T and "[ Accept ]" in T, T[-900:])
    e.keys("a")
    time.sleep(1.0)
    e.s.settle(0.6)
    T = e.text()
    arow("C4", "Accept: the table shows size 4 and the record is marked changed; the disk still has 3", re.search(r"size\s+number\s+4", T) is not None and T.split("\n")[0].rstrip().endswith("*"), T[:300])
    arow("C4b", "...and the disk is untouched: the record still says 3", '"size":3' in ai.rec(CED_REC), ai.rec(CED_REC)[-200:])
    e.keys(F2)
    e.keys("u")                                      # &Undo
    time.sleep(0.8)
    T = e.text()
    arow("C5", "Undo the AI's last change: the table shows size 3 again", re.search(r"size\s+number\s+3", T) is not None, T[:300])
    # an edit that would leave invalid JSON
    ced_ask(e, "break it [[ced_bad]]")
    e.keys("s")
    T = ai.wait_popup(e)
    arow("C6a", "ced_bad is shown as a diff (the AI cannot know)", "[ Accept ]" in T, T[-500:])
    e.keys("a")
    time.sleep(1.0)
    e.s.settle(0.6)
    T = e.text()
    arow("C6", "...and Accept is refused because the result is not valid JSON: the table still shows size 3 and the message says so", re.search(r"size\s+number\s+3", T) is not None
         and ai.msg(11677)[:30] in T, T[:300] + T[-300:])
    # explain the selected element
    e.keys(ai.DOWN)                                  # a line down: the selected element
    n1 = len(fm.log)
    e.keys(F2)
    e.keys("e")                                      # &Explain
    T = e.text()
    arow("C7", "Explain the selected element: the preview has the element and its path in the request", "This will be sent to anthropic" in T and "Explain this part of the record" in T and len(fm.log) == n1, T[-900:])
    e.keys(RET)
    e.end()
    # Ctrl-S saves what the AI changed
    make_json_record()
    e = ai.AccIde(ai.box(), cmd="CED bp %s" % CED_REC)
    ced_ask(e, "raise the size [[ced_ok]]")
    e.keys("s")
    ai.wait_popup(e)
    e.keys("a")
    time.sleep(1.0)
    e.keys("\x13")                                   # Ctrl-S
    time.sleep(1.0)
    arow("C4c", "Ctrl-S saves the AI's change, as ever: the disk now says 4", '"size":4' in ai.rec(CED_REC), ai.rec(CED_REC)[-200:])
    e.end()


def sec_dbg():
    say("\n--- the debugger")
    ai.configure(provider=False)
    ai.start_runner()
    e = ai.AccIde(ai.box(), cmd="RUN bp %s" % DBG_PROG)
    e.keys("ai", RET)
    T = e.text()
    arow("D0", "no provider: ai is not the debugger's (a format error), nothing is previewed", "This will be sent" not in T and "debug" in T, T[-300:])
    e.end()
    ai.configure()
    ai.start_runner()
    fm = ai.STATE["fm"]
    e = ai.AccIde(ai.box(), cmd="RUN bp %s" % DBG_PROG)
    n0, a0 = len(fm.log), ai.audit_off()
    e.keys("ai what is y [[sayonly]]", RET)
    T = e.text()
    arow("D1", "ai: the preview names the program and line, the source round the stop and the request; nothing sent yet", "This will be sent to anthropic" in T and "who is using debugger" in T
         and DBG_PROG in T and "debug" in T and "what is y [[sayonly]]" in T and len(fm.log) == n0, T[-1400:])
    e.keys("s")
    T = ai.wait_popup(e)
    rq = ai.requests()
    pr = ai.prompt_of(rq[-1][2]) if len(rq) > n0 else ""
    rl = ai.req_lines(ai.audit_new(a0))
    arow("D2", "Send: ONE request whose prompt has the stop and the source lines (x = 5, debug), ONE audit line, and the answer is words with Close", len(fm.log) == n0 + 1 and "x = 5" in pr and "debug" in pr
         and len(rl) == 1 and "[ Close ]" in T, repr((len(fm.log) - n0, pr[-300:], rl)))
    e.keys(RET)
    time.sleep(0.6)
    e.s.settle(0.6)
    L = e.lines()
    arow("D3", "the popup is gone and the debugger's screen is whole: the source with its line numbers, the command line on the last row", any(re.match(r"^\s*3:\s+debug", l) for l in L) and L[41].startswith(">"), "\n".join(L[:6] + L[38:42]))
    L = e.keys("/x", RET)
    arow("D3b", "...and it goes on working: /x shows the variable", any("5" in l for l in L[34:41]), "\n".join(L[34:42]))
    e.keys("r", RET)
    time.sleep(1.5)
    e.s.settle(0.6)
    n1 = len(fm.log)
    e.keys("ai again [[sayonly]]", RET)
    T = e.text()
    arow("D4", "the SECOND stop of the program: ai works there too (the setting lives in the debugger's common, not in a variable of the first call), the preview is shown and nothing is sent", "This will be sent to anthropic" in T
         and "again [[sayonly]]" in T and len(fm.log) == n1, T[-700:])
    e.keys(RET)
    e.end()


def main():
    mutant = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mutant=")), None)
    if mutant is not None and mutant not in MUTANTS:
        ids.bail("usage: sandbox-ai-apps.py <dir> [--build] [--mutant=%s]" % "|".join(MUTANTS))
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        ids.bail("usage: sandbox-ai-apps.py <dir> [--build] [--mutant=NAME]")
    ai.STATE["box"] = os.path.abspath(args[0])
    b = ai.box()
    say("sandbox-ai-apps: sandbox %s" % b)
    if "--build" in sys.argv:
        if os.path.exists(b) and os.listdir(b):
            ids.bail("%s is not empty" % b)
        r = subprocess.run([sys.executable, ids.TOOL, b, "all"], capture_output=True, text=True, errors="replace", timeout=1800)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            ids.bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-ai-apps: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(ai.sysd(), "bin", "sd")):
        ids.bail("%s holds no built sandbox (use --build, or point it at one)" % b)
    subprocess.run([sys.executable, ids.TOOL, b, "start"], capture_output=True, text=True, errors="replace", timeout=120)
    gt.BOX, gt.SYS, gt.SD = b, ai.sysd(), os.path.join(ai.sysd(), "bin", "sd")
    try:
        gt.prepare()
        gt.FIXTURES[ai.ACC] = ("no", "no")
        gt.build_account(ai.ACC)
        flags = gt.flags(gt.plain(ai.ACC, ["zzkf"]))
        if flags is None or flags[0] != "0":
            ids.bail("the first ordinary session is not shown to be one (admin=%r), so no row below can be believed" % (flags,))
        ai.setup_ai(mutant, progs=PROGS, mutants=MUTANTS)
        ai.configure()
        ai.make_records()
        make_json_record()
        make_debug_program()
        if mutant is None:
            sec_sed_off()
            sec_sed()
            sec_ced_off()
            sec_ced()
            sec_dbg()
        else:
            {"sed": sec_sed, "ced": sec_ced, "dbg": sec_dbg}[MUTANT_SECTIONS[mutant]]()
    finally:
        ai.stop_runner()
        if "fm" in ai.STATE:
            ai.STATE["fm"].stop()
        os.environ.pop("SD_AI_SOCKET", None)
        os.environ.pop("SD_AI_CTL", None)
        subprocess.run([sys.executable, ids.TOOL, b, "stop"], capture_output=True, text=True, errors="replace", timeout=120)
    say("\nsandbox-ai-apps: %d passed, %d failed" % (ids.passed, ids.failed))
    if mutant is not None:
        want = sorted(set(MUTANTS[mutant][3]))
        got = sorted({re.match(r"[SCD]\d+", i).group(0) for i in ai.FAILED_IDS if re.match(r"[SCD]\d+", i)})
        ok = want == got
        say("sandbox-ai-apps: MUTANT %s: the rows that failed are %s; they had to be exactly %s -> %s" % (mutant, got, want, "KILLED BY ITS OWN ROWS" if ok else "NOT AS EXPECTED"))
        return 0 if ok else 1
    return 0 if ids.failed == 0 and ids.passed > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
