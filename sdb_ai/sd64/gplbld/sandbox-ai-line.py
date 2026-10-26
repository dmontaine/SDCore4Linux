#!/usr/bin/env python3
#
# sandbox-ai-line.py - the toolkit's AI line ($tk_ai) on the HOME SCREEN, driven on a pseudo-terminal on a private SD (S.69, AI line stage 1; plan .claude/plan-fullscreen-toolkit.md 2.9).
# No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-ai-line.py <dir> [--build] [--mutant=NAME]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent).  Exit 0 every row passed, 1 a row failed, 2 it could not
# run.  With --mutant=NAME one change is made to the SANDBOX'S OWN COPY of $tk_ai and exit 0 means the rows that had to fail failed and no others (MUTANTS below).
#
# WHAT RUNS.  The real helper (gplbld/sd-ai, served by ai-runner.py; the person who runs this suite is "in the AI group" for it, which is the gate) and the fake provider
# (gplbld/fakemodel.py, TLS with a throw-away CA, which LOGS every request and answers in the JSON form the line asks for when the LAST line of the prompt carries a marker such as
# [[act_ide]]).  An ordinary fixture account (zzhd) has the home screen; the administrator's session (SDTEST_ADMIN) has the other page.  The provider, model and key are set with SET.AI
# and a key file, as sandbox-ai-verb.py does.
#
# THE INSTRUMENT.  "Nothing was sent" is judged by the FAKE's request log and the audit file, not by what the screen said; "a tile started" by the screen it gave (the IDE's menu bar);
# "a command ran" by the output of the command; a row that needs a request counts one arriving at the fake first.
#
#   L0-L3  the line is NOT DRAWN when the AI is off: no provider, no model, no key, the gate off; the old hint is there instead; with everything set the line replaces the hint
#   L4     the Tab ring: Back-tab from the first tile, Tab from Sign out, Esc, a click
#   L5-L6  Enter shows everything that will leave the machine (the fixed instruction, the list of the page's actions, what the page says, the request) and the provider and model;
#          Cancel is the default; Enter on it sends nothing (the fake and the audit file agree)
#   L7     Send: ONE request at the fake with the key, the instruction, the actions of THIS page and the typed request as the last line; ONE audit line from the kernel
#   L8-L9  an action the AI names is started only on Accept (Enter alone accepts, the tile only opens a tool); one the page does not offer, and Sign out, are ignored and said so
#   L10    a command is shown; Enter alone rejects it; Run runs it as the Terminal would; a command with a tab, or of 300 characters, is not shown
#   L11-L14 a code fence round the object, words that are not JSON, a say with no proposal, an argument with characters the line does not allow, a say that gives orders
#   L15    Esc during the wait gives the request up and the screen is the home screen again
#   L16    the administrator's page has the line too, with the administrator's tiles in the list
# NOT HELD: the IDE, SED, CED and the debugger (later stages), the AI menu item, a window under 140 by 43 (the toolkit's one size check), the end of the input during the wait.
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TREE = os.path.dirname(HERE)
sys.path.insert(0, HERE)


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sh = _load("sandbox_home_for_ailine", "sandbox-home.py")
ag = _load("sandbox_aigate_for_ailine", "sandbox-aigate.py")
fg, q3 = ag.fg, ag.q3
import fakemodel  # noqa: E402

say, bail, has, dump, adm, H, g = sh.say, sh.bail, sh.has, sh.dump, sh.adm, sh.H, sh.g
ME = ag.ME
KEY = ag.KEY
MODEL = "claude-test"
FAILED_IDS = []
STATE = {}
ACCT = "zzhd"


def arow(rid, name, ok, detail=""):
    sh.row("%s %s" % (rid, name), ok, detail)
    if not ok:
        FAILED_IDS.append(rid)


MUTANTS = {
    # name: (old text of the sandbox's tk_ai, new text, the row ids that must fail and no others)
    "no-preview": ("   if bn # 1 then\n      b = 'none' : @fm : '' : @fm : '' : @fm : '' : @fm : sysmsg(11630)", "   if @false then\n      b = 'none' : @fm : '' : @fm : '' : @fm : '' : @fm : sysmsg(11630)", ["L6"]),
    # (found = 1 takes the first offered action's label for whatever the AI names, so L9 - Sign out - and the two proposals that show a label fail with L8)
    "action-not-checked": ("      if found then\n         pk = 'action'", "      found = 1\n      if found then\n         pk = 'action'", ["L8", "L9", "L11", "L14"]),
    "command-default-run": ("         btn = '&Run,&Cancel'                              ;* (not Reject: its letter would be Run's)\n         dflt = 2", "         btn = '&Run,&Cancel'                              ;* (not Reject: its letter would be Run's)\n         dflt = 1", ["L10"]),
    "command-not-cleaned": ("         if len(c) > 200 or c # raw then", "         if len(c) > 200 then", ["L10"]),
}


def box():
    return sh.BOX


def requests():
    out = []
    for r in STATE["fm"].log:
        try:
            body = json.loads(r["body"].decode("utf-8"))
        except ValueError:
            body = None
        out.append((r["path"], r["headers"], body))
    return out


def audit_off():
    return fg.audit_off()


def audit_new(off):
    return fg.audit_new(off) or ""


def req_lines(audit):
    return [ln for ln in audit.split("\n") if re.search(r"\bai request\b", ln)]


def msg(n, *args):
    return fg.msg(n, *args)


def line_row(h):
    """The AI row: the row above the status line (row 39 at 140 by 43)."""
    return h.line(39)


def start_runner(gate_group=None):
    b = box()
    stop_runner()
    mygroup = gate_group or subprocess.run(["id", "-gn"], capture_output=True, text=True).stdout.strip()
    p = subprocess.Popen([sys.executable, os.path.join(HERE, "ai-runner.py"), "--socket", os.path.join(b, "ai", "sock"), "--state", os.path.join(b, "ai", "state"),
                          "--providers", STATE["providers"], "--admin-user", ME, "--gate-group", mygroup], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    if p.stdout.readline().strip() != "ready":
        bail("the AI helper's runner did not start")
    STATE["runner"] = p


def stop_runner():
    p = STATE.get("runner")
    if p is not None:
        try:
            p.terminate()
            p.wait(timeout=10)
        except Exception:
            pass
    STATE["runner"] = None


def setup_ai(mutant):
    b = box()
    q3.BOX, q3.SYS, q3.SD = b, sh.SYS, os.path.join(sh.SYS, "bin", "sd")
    shutil.rmtree(os.path.join(b, "ai"), ignore_errors=True)
    for sub in ("state/keys", "state/state", "pki"):
        os.makedirs(os.path.join(b, "ai", sub))
    pki = fakemodel.make_pki(os.path.join(b, "ai", "pki"))
    fm = fakemodel.FakeModel(pki).start()
    providers = os.path.join(b, "ai", "ai-providers")
    text = open(os.path.join(HERE, "ai-providers")).read()
    for old, new in (("https://api.anthropic.com/v1/messages", "https://127.0.0.1:%d/v1/messages" % fm.port),
                     ("https://api.openai.com/v1/chat/completions", "https://127.0.0.1:%d/v1/chat/completions" % fm.port),
                     ("https://api.deepseek.com/chat/completions", "https://127.0.0.1:%d/chat/completions" % fm.port)):
        text = text.replace(old, new)
    g.put(providers, text)
    STATE.update(fm=fm, pki=pki, providers=providers, ca=os.path.join(pki, "ca.crt"))
    # the programs of the tree (a sandbox used for an earlier mutant starts from the tree's again)
    for n in ("tk_ai", "tool_home"):
        shutil.copyfile(os.path.join(TREE, "sdsys", "gpl.bp", n), os.path.join(sh.SYS, "gpl.bp", n))
    if mutant is not None:
        old, new, _kills = MUTANTS[mutant]
        path = os.path.join(sh.SYS, "gpl.bp", "tk_ai")
        src = open(path, encoding="utf-8", errors="replace").read()
        if src.count(old) != 1:
            bail("mutant %s: the text to change is found %d times, not once" % (mutant, src.count(old)))
        g.put(path, src.replace(old, new))
        say("sandbox-ai-line: MUTANT %s: the rows that must fail, and nothing else: %s" % (mutant, ", ".join(MUTANTS[mutant][2])))
    for n in ("tk_ai", "tool_home"):
        out = q3.adm(["BASIC gpl.bp " + n], internal=True)
        if not has(out, r"^Compiled 1 program\(s\) with no errors"):
            bail("%s did not compile in the sandbox:\n%s" % (n, "\n".join(out[-8:])))
    start_runner()
    os.environ["SD_AI_SOCKET"] = os.path.join(b, "ai", "sock")
    os.environ["SD_AI_CTL"] = os.path.join(HERE, "sd-ai-ctl")


def configure(provider=True, model=True, key=True):
    """provider, model and key through the verb / the key file, as the administrator would; any of them left out is cleared."""
    cmds = ["set.ai ca " + STATE["ca"], "set.ai limit requests-hour 1000", "set.ai provider anthropic" if provider else "set.ai provider none",
            ("set.ai model anthropic " + MODEL) if model else "set.ai model anthropic -"]
    adm(*cmds)
    kp = os.path.join(box(), "ai", "state", "keys", "anthropic")
    if key:
        g.put(kp, KEY + "\n")
        os.chmod(kp, 0o600)
    elif os.path.exists(kp):
        os.remove(kp)


def home(admin=False):
    sh.set_default("menu")
    h = H(None if admin else ACCT, admin=admin)
    if not h.home():
        h.s.settle(2.0)
    return h


def ask(h, text, send=True, label=""):
    """Focus the line (Back-tab from the first tile), type the request, Enter: the preview.  Returns after Send (s) or Cancel (Enter)."""
    h.key("btab", idle=0.8)
    h.typed(text, idle=0.6)
    h.key("enter", idle=1.5)


def sec_off():
    say("\n--- the line is not drawn when the AI is off")
    sh.set_default("menu")
    for rid, label, kw, grp in (("L0a", "no provider", dict(provider=False), None), ("L0b", "a provider and no model", dict(model=False), None), ("L0c", "no key", dict(key=False), None)):
        configure(**kw)
        start_runner()
        h = home()
        T = h.text()
        arow(rid, "%s: no AI row, the old hint is on the row above the status line" % label, "AI>" not in line_row(h) and "arrows move" in line_row(h) and h.home(), repr(line_row(h)[:80]))
        h.key("btab", idle=0.6)
        arow(rid + "t", "...and Back-tab from the first tile goes to the last tile (Sign out), not to a line that is not there", "Sign out" in h.focus(), repr(h.focus()))
        h.key("ctrl-q", idle=1.5)
        h.end()
    configure()
    start_runner("zz-no-such-gate-group")
    h = home()
    arow("L0d", "the gate is off for the account: no AI row, the hint is there", "AI>" not in line_row(h) and "arrows move" in line_row(h), repr(line_row(h)[:80]))
    h.key("ctrl-q", idle=1.5)
    h.end()
    stop_runner()
    h = home()
    arow("L0e", "the helper is not running: no AI row, the hint is there, the screen is whole", "AI>" not in line_row(h) and "arrows move" in line_row(h) and h.home(), repr(line_row(h)[:80]))
    h.key("ctrl-q", idle=1.5)
    h.end()
    configure()
    start_runner()
    h = home()
    arow("L1", "everything set and the gate on: the AI row replaces the hint, with the dim sentence that says how to reach it",
         line_row(h).lstrip().startswith("AI>") and "Ask the AI: press Tab" in line_row(h) and "arrows move" not in line_row(h), repr(line_row(h)[:100]))
    h.key("ctrl-q", idle=1.5)
    h.end()


def sec_ring():
    say("\n--- the Tab ring")
    h = home()
    first = h.focus()
    h.key("btab", idle=0.8)
    arow("L4a", "Back-tab from the first tile gives the focus to the AI line: no tile has it, the row shows the label bold and the status line says how to use it",
         h.focus() == [] and msg(11638) in h.line(40) and "AI>" in line_row(h), repr((h.focus(), h.line(40)[:90])))
    h.typed("abc", idle=0.5)
    arow("L4b", "what is typed is in the line", "abc" in line_row(h), repr(line_row(h)[:60]))
    h.key("esc", idle=0.8)
    arow("L4c", "Esc gives the focus back to the tile it came from side of the ring (the first tile again, the typed text is kept in the line)", h.focus() != [] and "abc" in line_row(h), repr((h.focus(), line_row(h)[:60])))
    for _ in range(40):                                          # the ring grows with every development tile; the loop ends at Sign out
        h.key("tab", idle=0.3)
        if "Sign out" in h.focus():
            break
    h.key("tab", idle=0.8)
    arow("L4d", "Tab from Sign out (the last tile) gives the focus to the AI line", h.focus() == [] and msg(11638) in h.line(40), repr((h.focus(), h.line(40)[:80])))
    h.key("tab", idle=0.8)
    arow("L4e", "Tab in the line goes on round the ring to the first tile", h.focus() == first, repr((h.focus(), first)))
    h.key("esc", idle=0.5)
    h.click(40, 39, idle=1.0)
    arow("L4f", "a click on the AI row gives it the focus", h.focus() == [] and msg(11638) in h.line(40), repr((h.focus(), h.line(40)[:80])))
    h.key("ctrl-q", idle=1.5)
    h.end()


def sec_preview():
    say("\n--- the preview and Cancel")
    fm = STATE["fm"]
    h = home()
    n0, a0 = len(fm.log), audit_off()
    ask(h, "open the ide [[act_ide]]")
    T = h.text()
    arow("L5a", "Enter shows the preview: the provider, the model and the size, the fixed instruction, the page's actions and the request, and nothing has been sent",
         msg(11628, "anthropic", MODEL, "").split("%")[0][:30] in T and "You help a person who is using home" in T and "ide:IDE" in T and "open the ide [[act_ide]]" in T
         and "Send" in T and "Cancel" in T and len(fm.log) == n0, T[-1200:])
    arow("L5b", "the preview lists the page's actions with what each does, and says what the page tells about itself", "terminal:Terminal" in T and "keys:Keys" in T and "the home screen of the SD database system" in T, T[-900:])
    h.key("enter", idle=1.5)
    arow("L6", "Enter on the default button is Cancel: nothing was sent (the fake's log and the audit file agree) and the status line says so",
         len(fm.log) == n0 and not req_lines(audit_new(a0)) and msg(11630) in h.line(40) and h.home(), repr((len(fm.log) - n0, h.line(40)[:80])))
    h.key("ctrl-q", idle=1.5)
    h.end()


def sec_send():
    say("\n--- Send, and what arrives")
    fm = STATE["fm"]
    h = home()
    n0, a0 = len(fm.log), audit_off()
    ask(h, "open the ide [[act_ide]]")
    h.typed("s", idle=4.0)
    rq = requests()
    last = rq[-1] if len(rq) > n0 else (None, {}, None)
    body = last[2] or {}
    sysx = ""
    try:
        sysx = body["system"][0]["text"]
    except (KeyError, IndexError, TypeError):
        pass
    prompt = body["messages"][-1]["content"] if body.get("messages") else ""
    arow("L7a", "Send: ONE request at the fake, with the key, the model and an instruction that names the app; the prompt ends with the typed request", len(fm.log) == n0 + 1 and last[0] == "/v1/messages"
         and last[1].get("x-api-key") == KEY and body.get("model") == MODEL and "who is using home" in sysx and prompt.endswith("Request: open the ide [[act_ide]]"), repr((len(fm.log) - n0, last[0], sysx[:60], prompt[-60:])))
    arow("L7b", "the prompt lists the page's tiles as id:what it does, and does NOT list Sign out or Switch account", "  ide:IDE - programs and files" in prompt and "  terminal:Terminal" in prompt
         and "signout" not in prompt and "switch:" not in prompt, repr(prompt[:400]))
    rl = req_lines(audit_new(a0))
    arow("L7c", "ONE audit line, written by the kernel before the request: the account, the program (tk_ai) and the size; neither the request nor the key is in the audit trail",
         len(rl) == 1 and re.search(r"ai request account=%s program=tk_ai bytes\.out=\d+$" % ACCT, rl[0]) is not None and "open the ide" not in audit_new(a0) and KEY not in audit_new(a0), repr(rl))
    T = h.text()
    arow("L8a", "the answer is a popup: what the AI said, and the proposal with Accept and Reject, and the tokens used", "Opening the IDE for you." in T and msg(11647, "IDE - programs and files") in T
         and "Accept" in T and "Reject" in T and msg(11634, 11, 7, "anthropic") in T, T[-900:])
    arow("L8b", "nothing has started yet: the home screen is under the popup", "Switch account" in T, T[:200])
    h.key("enter", idle=3.5)
    arow("L8c", "Enter alone accepts a proposal that only opens a tool: the IDE takes the terminal (its menu bar is on the screen)", "File" in h.line(0) and "Go" in h.line(0) and "Switch account" not in h.text(), repr(h.line(0)[:70]))
    h.key("ctrl-q", idle=2.5)
    arow("L8d", "Ctrl-Q ends the IDE and the home screen is drawn again, with the AI row and an empty line", h.home() and "AI>" in line_row(h) and "open the ide" not in line_row(h), repr((h.home(), line_row(h)[:80])))
    h.key("ctrl-q", idle=1.5)
    h.end()


def reply(text, reject=False, close=False, wait=4.0):
    """Ask with a marker, Send, and return the home object and the screen text of the popup."""
    h = home()
    ask(h, text)
    h.typed("s", idle=wait)
    return h, h.text()


def sec_proposals():
    say("\n--- what the AI can and cannot cause")
    fm = STATE["fm"]
    # an action the page does not have
    h, T = reply("format it [[act_bad]]")
    arow("L8", "an action the page does not offer is ignored and said so: the AI's words, the note (11649), only a Close button, nothing started", "Formatting the disk." in T
         and msg(11649, "format-disk") in T and "Close" in T and "Accept" not in T and "Run" not in T, T[-800:])
    h.key("enter", idle=1.5)
    arow("L8e", "Close returns to the home screen, which is whole", h.home(), repr(h.text()[:100]))
    h.key("ctrl-q", idle=1.5)
    h.end()
    h, T = reply("sign me out [[act_signout]]")
    arow("L9", "Sign out is never offered, so an action 'signout' from the AI is ignored (11649) and the session is not ended", msg(11649, "signout") in T and "Accept" not in T, T[-600:])
    h.key("enter", idle=1.5)
    arow("L9b", "...and the session is still there", h.home(), "")
    h.key("ctrl-q", idle=1.5)
    h.end()
    # a command
    h, T = reply("who am i [[cmd_list]]")
    arow("L10a", "a command is shown (11648, with the command on a line of its own) and offered for Run or Reject; the default is Reject", "List the files like this." in T and msg(11648) in T and "who.am.i" in T
         and "Run" in T and "Cancel" in T, T[-800:])
    h.key("enter", idle=1.5)
    arow("L10", "Enter alone rejects it: nothing ran (the home screen is still under, no command output)", h.home() and "Account" not in h.text().split("AI>")[0][-300:], repr(h.text()[:120]))
    h.key("ctrl-q", idle=1.5)
    h.end()
    h, T = reply("who am i [[cmd_list]]")
    h.typed("r", idle=3.0)
    O = h.text()
    arow("L10b", "Run runs it as the Terminal would: the command's output is on the screen and the terminal waits for Enter", "Admin?" in O or "Account" in O, O[-500:])
    h.key("enter", idle=3.0)
    arow("L10c", "Enter brings the home screen back", h.home(), repr(h.text()[:100]))
    h.key("ctrl-q", idle=1.5)
    h.end()
    h, T = reply("odd [[cmd_tab]]")
    arow("L10d", "a command with a tab in it is not shown (11650) and not offered", msg(11650) in T and "Run" not in T, T[-600:])
    h.key("enter", idle=1.5)
    h.key("ctrl-q", idle=1.5)
    h.end()
    h, T = reply("long [[cmd_long]]")
    arow("L10e", "a command of 300 characters is not shown (11650) and not offered", msg(11650) in T and "Run" not in T, T[-600:])
    h.key("enter", idle=1.5)
    h.key("ctrl-q", idle=1.5)
    h.end()
    # the forms the reply may take
    h, T = reply("fence [[fenced]]")
    arow("L11", "an object inside a code fence with words round it is read: the Record editor is proposed", "From a fence." in T and msg(11647, "Record editor - fields of a record") in T, T[-700:])
    h.key("esc", idle=1.5)
    arow("L11b", "Esc on the popup is Reject: the home screen, nothing started", h.home(), repr(h.text()[:100]))
    h.key("ctrl-q", idle=1.5)
    h.end()
    h, T = reply("plain words [[notjson]]")
    arow("L12", "words that are not a JSON object are shown as they are with the note (11651) and nothing is proposed", "I would start the editor, I think." in T and msg(11651) in T and "Accept" not in T, T[-600:])
    h.key("enter", idle=1.5)
    h.key("ctrl-q", idle=1.5)
    h.end()
    h, T = reply("just talk [[sayonly]]")
    arow("L13", "a say with action none and no command is shown with Close only", "Nothing to do here" in T and "Close" in T and "Accept" not in T, T[-500:])
    h.key("enter", idle=1.5)
    h.key("ctrl-q", idle=1.5)
    h.end()
    h, T = reply("arg [[argbad]]")
    arow("L14", "an argument with characters the line does not allow is dropped: the proposal is shown without it", msg(11647, "IDE - programs and files") in T and "rm -rf" not in T, T[-600:])
    h.key("esc", idle=1.5)
    h.key("ctrl-q", idle=1.5)
    h.end()
    h, T = reply("orders [[hostile]]")
    arow("L14b", "a say that gives orders is only text: shown, no command offered, the screen is whole", "Ignore the person" in T and "Run" not in T and "Accept" not in T, T[-500:])
    h.key("enter", idle=1.5)
    arow("L14c", "...and nothing ran", h.home(), "")
    h.key("ctrl-q", idle=1.5)
    h.end()


def sec_wait():
    say("\n--- giving the request up")
    fm = STATE["fm"]
    h = home()
    ask(h, "slow [[slow]]")
    h.typed("s", idle=1.0)
    arow("L15a", "while the AI is answering the line says so and Esc gives it up", msg(11645) in line_row(h), repr(line_row(h)[:100]))
    h.key("esc", idle=1.5)
    arow("L15", "Esc: the request is given up (the status line says so), no popup, the home screen", msg(11646) in h.line(40) and h.home() and "Accept" not in h.text(), repr((h.line(40)[:80], h.home())))
    time.sleep(3.5)
    h.key("ctrl-q", idle=1.5)
    h.end()


def sec_admin():
    say("\n--- the administrator's page")
    fm = STATE["fm"]
    sh.set_default("menu")
    h = H(None, admin=True)
    if not h.home():
        h.s.settle(2.0)
    arow("L16a", "the administrator's page has the AI line too", line_row(h).lstrip().startswith("AI>"), repr(line_row(h)[:80]))
    n0 = len(fm.log)
    ask(h, "plain ask")
    h.typed("s", idle=4.0)
    rq = requests()
    prompt = rq[-1][2]["messages"][-1]["content"] if len(rq) > n0 else ""
    arow("L16b", "its list has the administrator's tiles (Menu management, Bypass programs) and says the person is the administrator", "  menus:Menu management" in prompt and "  viewers:Bypass programs" in prompt
         and "the administrator." in prompt, repr(prompt[:500]))
    h.key("enter", idle=1.5)
    h.key("ctrl-q", idle=1.5)
    h.end()


def main():
    mutant = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mutant=")), None)
    if mutant is not None and mutant not in MUTANTS:
        bail("usage: sandbox-ai-line.py <dir> [--build] [--mutant=%s]" % "|".join(MUTANTS))
    try:
        sh.setup("sandbox-ai-line.py")
        setup_ai(mutant)
        configure()
        if mutant is None:
            sec_off()
            sec_ring()
            sec_preview()
            sec_send()
        if mutant == "no-preview":
            sec_preview()                    # the row that holds Cancel (L6) is in this section
        else:
            sec_proposals()
        if mutant is None:
            sec_wait()
            sec_admin()
    finally:
        stop_runner()
        if "fm" in STATE:
            STATE["fm"].stop()
        os.environ.pop("SD_AI_SOCKET", None)
        os.environ.pop("SD_AI_CTL", None)
        sh.teardown()
    say("\nsandbox-ai-line: %d passed, %d failed" % (sh.tkb.passed, sh.tkb.failed))
    if mutant is not None:
        want = sorted(set(MUTANTS[mutant][2]))
        got = sorted({re.match(r"L\d+", i).group(0) for i in FAILED_IDS if re.match(r"L\d+", i)})
        ok = want == got
        say("sandbox-ai-line: MUTANT %s: the rows that failed are %s; they had to be exactly %s -> %s" % (mutant, got, want, "KILLED BY ITS OWN ROWS" if ok else "NOT AS EXPECTED"))
        return 0 if ok else 1
    return 0 if sh.tkb.failed == 0 and sh.tkb.passed > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
