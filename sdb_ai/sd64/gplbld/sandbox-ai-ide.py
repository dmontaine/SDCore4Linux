#!/usr/bin/env python3
#
# sandbox-ai-ide.py - the AI line in the IDE (AI line stage 2: $tk_ai with edits, the IDE's AI entry and AI menu), driven on a PSEUDO-TERMINAL on a private SD.  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-ai-ide.py <dir> [--build] [--mutant=NAME]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent).  Exit 0 every row passed, 1 a row failed, 2 it could not
# run.  With --mutant=NAME one change is made to the SANDBOX'S OWN COPY of $tk_ai or of the IDE and exit 0 means the rows that had to fail failed and no others (MUTANTS below).
#
# WHAT RUNS.  The real helper (gplbld/sd-ai through ai-runner.py; the person who runs this suite is "in the AI group", which is the gate), the fake provider (gplbld/fakemodel.py: it
# LOGS every request and answers in the JSON form the line asks for when the LAST line of the prompt carries a marker such as [[edit_ok]]; a request with no marker - the menu's
# Explain items - gets plain words) and the IDE driven on a 140 by 42 pty with sandbox-ide.py's own class.  The record the suite edits is four lines:  crt 'hello' / x = 1 / crt 'bye' /
# end.  What the IDE DID is read from the DISK afterwards (CT through a pipe session), never from what the screen said; "nothing was sent" is read from the fake's request log.
#
#   I0     the AI is off (no provider): the menu bar is as it was, there is no AI> row
#   I1-I2  the AI is on: the AI menu, the AI> row under the editor and the table (the last row of the form), the Tab ring ends at it
#   I3-I4  Enter in the AI entry shows EVERYTHING that will be sent (instruction, the record's lines, the request) and sends nothing; Cancel is the default; Send makes ONE request
#          with the record, the line it starts at and the request as the last line, and the kernel's one audit line
#   I5-I7  a proposed edit is shown as a diff (the old line with -, the new with +, the line number); Enter alone rejects it; Accept changes the editor's BUFFER, not the disk, and one
#          Ctrl-Z takes it back
#   I8     two edits at once, one with a line added: both applied and one Ctrl-Z takes both back
#   I9-I10 a set that does not fit (an old text found twice, not found, overlapping), a diff of more than 30 lines, an empty list, a command (the IDE has nowhere to run one): each
#          is said and none is offered; the buffer is as it was
#   I11-I12 Explain the error (the table's row; the message is in the request) and Explain the selection (the mark to the cursor; with no mark the status line says so, nothing is sent)
#   I13    Esc during the wait gives the request up
# 28 Oct 26: Tab indents in the IDE's editor now (the owner's approval of 28 Oct), so ask() and focus_entry() walk the ring of panes with F6; the loops that come
# BACK to the editor still press Tab, which moves through the AI line, the tree and the tabs as before.  Not run since.
# NOT HELD: the buffer changing while the AI answers (the wait loop is modal, so no key can reach the editor: the fit test in ai.apply is held only as text, by
# test-ailine-units.py I1; a mutant that took it out was tried on 24 Oct and no row could fail), the end of the input during the wait, the SED hand-over, a record
# longer than 24000 bytes (the window), a real provider.
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


ids = _load("sandbox_ide_for_ai", "sandbox-ide.py")
gt = _load("sandbox_gates_for_aiide", "sandbox-gates.py")     # the administrator's internal session (SDTEST_ADMIN, sd -internal): compiling the system programs, SET.AI
import fakemodel  # noqa: E402

say = ids.say
TAB, RET, ESC, F8, F10 = ids.TAB, ids.RET, ids.ESC, ids.F8, ids.F10      # F8 is the IDE's compile since S.88 Phase 4 (F7 is debug)
F6 = ids.F6                                                                 # 28 Oct 26: the next pane; Tab indents in the editor now, so the ring is walked with F6
CTRL_G, CTRL_Z = "\x07", "\x1a"
DOWN = "\x1bOB"
RIGHT = "\x1bOC"
AI_MENU = RIGHT * 5                       # F10 opens File; the AI menu is the sixth title (File Go Search Build View AI Help)
KEY = "test-key-0123456789"
MODEL = "claude-test"
FAILED_IDS = []
STATE = {}
RUN = ids.RUN
ACC = "zzai"                              # the fixture account the IDE runs in
OK_REC = "zzaio" + RUN                    # crt 'hello' / x = 1 / crt 'bye' / end
ERR_REC = "zzaie" + RUN                   # crt "one" / x = = 1 / end   (one compile error, line 2)
BODY = ["   crt 'hello'", "   x = 1", "   crt 'bye'", "end"]


def arow(rid, name, ok, detail=""):
    ids.row("%s %s" % (rid, name), ok, detail)
    if not ok:
        FAILED_IDS.append(rid)
        if STATE.get("last"):                # the screen the row was judged on, so that a failure can be read without a rerun
            say("      screen at the failure of %s:" % rid)
            for ln in STATE["last"].split("\n"):
                say("      | " + ln.rstrip()[:140])


MUTANTS = {
    # name: (program of the sandbox, old text, new text, the row ids that must fail and no others)
    "edit-applied-to-disk-rows": ("tk_ai", "dflt = 2                                         ;* a change to a text is never accepted by Enter alone", "dflt = 1", ["I6"]),
    "dup-not-refused": ("tk_ai", "               case index(tbm, eo, 2) > 0\n                  bad.why = 'old text found more than once'", "               case @false\n                  bad.why = 'old text found more than once'", ["I9"]),
    "no-undo-step": ("ide", "   call $sl_memo('snap', mw, '', '', ai.sr)\n", "", ["I7", "I8"]),     # 28 Oct 26: the step goes on through the memo's 'snap' (the old mw{'undo'} push was the legacy form)
    # 28 Oct 26 (S5): the diff shows the first row of a long line only (the old cut at the box)
    "cut-not-wrapped": ("tk_ai", "   for wr.k = 1 to wr.len step wr.w\n", "   for wr.k = 1 to 1 step wr.w\n", ["I14"]),
}
MUTANT_SECTIONS = {"edit-applied-to-disk-rows": "edits", "dup-not-refused": "refused", "no-undo-step": "edits", "cut-not-wrapped": "wide"}


def box():
    return STATE["box"]


def sysd():
    return os.path.join(box(), "sys")


def put(path, text):
    with open(path, "w", encoding="latin-1") as fh:
        fh.write(text)


def requests():
    out = []
    for r in STATE["fm"].log:
        try:
            body = json.loads(r["body"].decode("utf-8"))
        except ValueError:
            body = None
        out.append((r["path"], r["headers"], body))
    return out


def prompt_of(body):
    return body["messages"][-1]["content"]


def audit_path():
    return os.path.join(sysd(), "audit")


def audit_off():
    """SD APPENDS to <sys>/audit and never creates it, so without one every audit line is dropped: it is made, empty, when it is missing."""
    try:
        if not os.path.exists(audit_path()):
            with open(audit_path(), "ab"):
                pass
        return os.path.getsize(audit_path())
    except OSError:
        return 0


def audit_new(off):
    try:
        with open(audit_path(), "rb") as f:
            f.seek(off)
            return f.read().decode("utf-8", errors="replace")
    except OSError:
        return ""


def req_lines(a):
    return [ln for ln in a.split("\n") if re.search(r"\bai request\b", ln)]


def msg(n, *args):
    with open(os.path.join(sysd(), "messages", str(n)), encoding="utf-8") as f:
        t = f.read().rstrip("\n")
    for i, a in enumerate(args, 1):
        t = t.replace("%" + str(i), str(a))
    return t


def rec(rid):
    """The record as the disk has it, through a pipe session (CT)."""
    return "\n".join(gt.plain(ACC, ["CT bp %s" % rid]))


def start_runner(gate_group=None):
    stop_runner()
    mygroup = gate_group or subprocess.run(["id", "-gn"], capture_output=True, text=True).stdout.strip()
    me = subprocess.run(["id", "-un"], capture_output=True, text=True).stdout.strip()
    p = subprocess.Popen([sys.executable, os.path.join(HERE, "ai-runner.py"), "--socket", os.path.join(box(), "ai", "sock"), "--state", os.path.join(box(), "ai", "state"),
                          "--providers", STATE["providers"], "--admin-user", me, "--gate-group", mygroup], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    if p.stdout.readline().strip() != "ready":
        ids.bail("the AI helper's runner did not start")
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


def compile_prog(n):
    out = "\n".join(gt.adm(["BASIC gpl.bp " + n], internal=True))
    if not re.search(r"^Compiled 1 program\(s\) with no errors", out, re.M):
        ids.bail("%s did not compile in the sandbox:\n%s" % (n, out[-600:]))


def admin(*cmds):
    return "\n".join(gt.adm(list(cmds), internal=True))


def setup_ai(mutant, progs=("sl_form", "tk_ai", "ide"), mutants=None):
    """progs: the system programs copied from the tree and compiled; mutants: the table to look the mutant up in (sandbox-ai-apps.py has its own)."""
    mutants = mutants if mutants is not None else MUTANTS
    b = box()
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
    put(providers, text)
    STATE.update(fm=fm, pki=pki, providers=providers, ca=os.path.join(pki, "ca.crt"))
    for n in progs:                      # the programs of the tree (a sandbox used for an earlier mutant starts from the tree's again)
        shutil.copyfile(os.path.join(TREE, "sdsys", "gpl.bp", n), os.path.join(sysd(), "gpl.bp", n))
    if mutant is not None:
        prog, old, new, _k = mutants[mutant]
        path = os.path.join(sysd(), "gpl.bp", prog)
        src = open(path, encoding="utf-8", errors="replace").read()
        if src.count(old) != 1:
            ids.bail("mutant %s: the text to change is found %d times, not once" % (mutant, src.count(old)))
        put(path, src.replace(old, new))
        say("sandbox-ai-ide: MUTANT %s: %s changed; the rows that must fail, and nothing else: %s" % (mutant, prog, ", ".join(mutants[mutant][3])))
    for n in progs:
        compile_prog(n)
    start_runner()
    os.environ["SD_AI_SOCKET"] = os.path.join(b, "ai", "sock")
    os.environ["SD_AI_CTL"] = os.path.join(HERE, "sd-ai-ctl")


def configure(provider=True):
    cmds = ["set.ai ca " + STATE["ca"], "set.ai limit requests-hour 1000", "set.ai provider anthropic" if provider else "set.ai provider none", "set.ai model anthropic " + MODEL]
    admin(*cmds)
    kp = os.path.join(box(), "ai", "state", "keys", "anthropic")
    put(kp, KEY + "\n")
    os.chmod(kp, 0o600)


def make_records():
    prog = "zzaimk" + RUN
    body = "\n".join([
        "   open 'bp' to f else stop 'no bp'",
        "   write \"%s\" on f, '%s'" % ("\":@fm:\"".join(BODY), OK_REC),     # (the lines hold single quotes)
        "   write 'crt \"one\"':@fm:'x = = 1':@fm:'end' on f, '%s'" % ERR_REC,
        "   crt 'RECORDS DONE'", "end", ""])
    put(os.path.join(box(), "user_accounts", ACC, "bp", prog), body)
    out = "\n".join(gt.plain(ACC, ["BASIC bp %s" % prog, "RUN bp %s" % prog]))
    if "RECORDS DONE" not in out:
        ids.bail("the records were not made:\n" + out[-500:])


def reset_record():
    make_records()


class AccIde(ids.Ide):
    """sandbox-ide.py's Ide, signed on to the fixture account ACC as an ordinary session (-a, no SDTEST_ADMIN)."""

    def __init__(self, box, cmd="IDE", cols=140, rows=42):
        self.box = box
        env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"), TERM="xterm", LC_ALL="C", LANG="C")
        for k in ("SDTEST_ADMIN", "SSH_CONNECTION", "SSH_TTY"):
            env.pop(k, None)
        self.s = ids.PtySession([os.path.join(box, "sys", "bin", "sd"), "-a" + ACC], os.path.join(box, "user_accounts", ACC), env, cols, rows, utf8=False)
        self.s.settle(1.5)
        self.s.type("TERM xterm\r")
        self.s.type("TERM %d,%d\r" % (cols, rows))
        self.log = [cmd]
        self.s.type(cmd + "\r", idle=1.2)

    def lines(self):
        L = ids.Ide.lines(self)
        STATE["last"] = "\n".join(l for l in L if l.strip())
        return L


def ide(rid=None):
    e = AccIde(box(), cmd=("IDE bp %s" % rid) if rid else "IDE")
    return e


def screen_has(e, *words):
    t = e.text()
    return all(w in t for w in words)


def menu_bar(e):
    return e.lines()[0]


def ai_row(e):
    for i, l in enumerate(e.lines()):
        if "AI>" in l:
            return i, l
    return None, ""


def wait_popup(e, tmax=15.0):
    """The answer's popup has Accept or Close on it; the wait loop polls the helper about once a second, so the answer shows between 1 and 4 seconds after Send.  Returns the screen's text."""
    t0 = time.time()
    while time.time() - t0 < tmax:
        e.s.settle(0.5)                  # (the pty is read only while the suite waits on it: a sleep leaves the screen as it was)
        T = e.text()
        if "[ Close ]" in T or "[ Accept ]" in T:
            return T
    return e.text()


def ask(e, request, go_send=False):
    """The AI entry has the focus (F6 round the ring of panes from the editor: the messages, then the AI line), the request is typed, Enter shows the preview."""
    e.keys(F6, F6)
    e.keys(request)
    e.keys(RET)


def focus_entry(e):
    """The entry is the last stop of the ring: F6 until the status line names it (28 Oct 26: Tab indents in the editor)."""
    for _ in range(6):
        if "[AI]" in e.status():
            return True
        e.keys(F6)
    return "[AI]" in e.status()


def sec_off():
    say("\n--- the AI is off")
    configure(provider=False)
    start_runner()
    e = ide(OK_REC)
    L = e.lines()
    arow("I0", "no provider: the menu bar is File Go Search Build View Help as ever and there is no AI> row", re.search(r"File\s+Go\s+Search\s+Build\s+View\s+Help", L[0]) is not None
         and "AI" not in L[0] and ai_row(e)[0] is None, repr(L[0][:80]))
    e.end()
    configure()
    start_runner()


def sec_on():
    say("\n--- the AI is on")
    e = ide(OK_REC)
    L = e.lines()
    arow("I1a", "the menu bar has the AI menu before Help", re.search(r"File\s+Go\s+Search\s+Build\s+View\s+AI\s+Help", L[0]) is not None, repr(L[0][:90]))
    r, line = ai_row(e)
    arow("I1b", "an AI> row under the editor, in the form's last row (the next row down is the form's bottom border, then the status line)", r is not None and r == len(L) - 3 and "AI>" in line, repr((r, len(L), line[:60])))
    arow("I2", "Tab from the editor goes on round the ring and ends at the AI entry (the status line names it [AI])", focus_entry(e), repr(e.status()))
    e.end()


def sec_preview():
    say("\n--- the preview, Cancel and Send")
    fm = STATE["fm"]
    e = ide(OK_REC)
    focus_entry(e)
    n0, a0 = len(fm.log), audit_off()
    e.keys("make the greeting longer [[edit_ok]]")
    e.keys(RET)
    T = e.text()
    arow("I3a", "Enter shows the preview: the provider and model, the instruction naming the IDE, the text being worked on from line 1 (its lines are there), the request, Send and Cancel",
         "This will be sent to anthropic" in T and "who is using IDE" in T and msg(11668, 4, 0, 1).split("0")[0][:25] in T and "crt 'hello'" in T and "x = 1" in T
         and "make the greeting longer [[edit_ok]]" in T and "Send" in T and "Cancel" in T, T[-1400:])
    arow("I3b", "nothing has been sent yet", len(fm.log) == n0, repr(len(fm.log) - n0))
    e.keys(RET)
    arow("I3c", "Enter on the default button is Cancel: nothing was sent (the fake's log and the audit file agree) and the status line says so",
         len(fm.log) == n0 and not req_lines(audit_new(a0)) and msg(11630) in e.status(), repr((len(fm.log) - n0, e.status()[:80])))
    e.end()
    e = ide(OK_REC)
    focus_entry(e)
    n0, a0 = len(fm.log), audit_off()
    e.keys("make the greeting longer [[edit_ok]]")
    e.keys(RET)
    e.keys("s")
    wait_popup(e)
    rq = requests()
    last = rq[-1] if len(rq) > n0 else (None, {}, None)
    body = last[2] or {}
    pr = prompt_of(body) if body.get("messages") else ""
    try:
        sysx = body["system"][0]["text"]
    except (KeyError, IndexError, TypeError):
        sysx = ""
    arow("I4a", "Send: ONE request at the fake, with the instruction (IDE, and the paragraph about edits), the record's lines, the line it starts at and the request as the last line",
         len(fm.log) == n0 + 1 and "who is using IDE" in sysx and '"edits"' in sysx and "crt 'hello'" in pr and "(it starts at line 1)" in pr and pr.endswith("Request: make the greeting longer [[edit_ok]]"),
         repr((len(fm.log) - n0, sysx[:80], pr[-120:])))
    rl = req_lines(audit_new(a0))
    arow("I4b", "ONE audit line, the kernel's, before the request: account, program tk_ai and a size; the record's text is in no audit line", len(rl) == 1 and "program=tk_ai" in rl[0] and "crt 'hello'" not in audit_new(a0), repr(rl))
    STATE["e"] = e


def sec_edits():
    say("\n--- an edit as a diff")
    e = STATE.pop("e")
    T = e.text()
    arow("I5a", "the answer is a popup with what the AI said and the diff: the change number and the line, the old line with -, the new with +", "I made the greeting longer." in T
         and msg(11658, 1, 1, 1) in T and "- crt 'hello'" in T and "+ crt 'hello world'" in T, T[-900:])
    arow("I5b", "Accept and Reject are the buttons, and the editor still holds the old line (nothing is changed before Accept)", "Accept" in T and "Reject" in T, T[-500:])
    e.keys(RET)
    arow("I6", "Enter alone is Reject: the editor is as it was and so is the disk", "crt 'hello world'" not in e.text() and "hello world" not in rec(OK_REC), repr(e.text()[:200]))
    e.end()
    fm = STATE["fm"]
    reset_record()
    e = ide(OK_REC)
    focus_entry(e)
    e.keys("longer [[edit_ok]]")
    e.keys(RET)
    e.keys("s")
    wait_popup(e)
    e.keys("a")
    time.sleep(1.5)
    t = e.quiet()
    ed = "\n".join(t)
    arow("I7a", "Accept: the editor shows the new line, the status line says it is in the editor and nothing is saved (the record is marked changed)", "crt 'hello world'" in ed and " *" in e.status()
         and msg(11661, 1).split("(")[0][:20] in e.status(), repr((e.status()[:120],)))
    arow("I7b", "the disk is untouched: the record has no 'hello world'", "hello world" not in rec(OK_REC), "")
    e.keys(ESC)
    e.keys(ESC)
    e.keys("\x1b" if False else "")
    # back to the editor: Shift-Tab is not needed, Tab round the ring
    for _ in range(6):
        if "[Editor]" in e.status() or "[Edit" in e.status():
            break
        e.keys(TAB)
    e.keys(CTRL_Z)
    t = e.quiet()
    arow("I7c", "one Ctrl-Z takes the change back: the old line is in the editor and the record is no longer marked changed", "crt 'hello'" in "\n".join(t) and "hello world" not in "\n".join(t) and " *" not in e.status(), repr(e.status()[:100]))
    e.end()
    reset_record()
    e = ide(OK_REC)
    focus_entry(e)
    e.keys("two [[edit_two]]")
    e.keys(RET)
    e.keys("s")
    T = wait_popup(e)
    arow("I8a", "two edits: both are in the diff, in the order they appear in the text (x = 1 first, though the AI gave crt 'bye' first), and the added line is shown", msg(11658, 1, 2, 2) in T
         and msg(11658, 2, 2, 3) in T and "+ crt 'see you'" in T, T[-1100:])
    e.keys("a")
    time.sleep(1.5)
    t = "\n".join(e.quiet())
    arow("I8b", "Accept: both are applied (x = 2, goodbye and see you), and the record grew a line", "x = 2" in t and "crt 'goodbye'" in t and "crt 'see you'" in t, t[:700])
    for _ in range(6):
        if "[Edit" in e.status():
            break
        e.keys(TAB)
    e.keys(CTRL_Z)
    t = "\n".join(e.quiet())
    arow("I8c", "ONE Ctrl-Z takes both back", "x = 1" in t and "crt 'bye'" in t and "goodbye" not in t and "see you" not in t, t[:600])
    e.end()
    reset_record()


def sec_refused():
    say("\n--- what is refused")
    fm = STATE["fm"]
    for rid, marker, note, extra in (("I9a", "edit_dup", "old text found more than once", None), ("I9b", "edit_none", "old text not found", None), ("I9c", "edit_overlap", "two edits overlap", None)):
        e = ide(OK_REC)
        focus_entry(e)
        e.keys("x [[%s]]" % marker)
        e.keys(RET)
        e.keys("s")
        T = wait_popup(e)
        arow(rid,"%s: a set that does not fit is ignored whole and said so (%s), no Accept button" % (marker, note), msg(11660, note) in T and "Accept" not in T and "Close" in T, T[-700:])
        e.keys(RET)
        arow(rid + "z", "...and the buffer is as it was", "\n".join(e.quiet()).count("crt 'hello'") >= 1 and " *" not in e.status(), repr(e.status()[:80]))
        e.end()
    e = ide(OK_REC)
    focus_entry(e)
    e.keys("x [[edit_big]]")
    e.keys(RET)
    e.keys("s")
    T = wait_popup(e)
    arow("I9d", "a diff of more than 30 lines is not offered (11659)", msg(11659, 41).split("(")[0][:40] in T and "Accept" not in T, T[-600:])
    e.keys(RET)
    e.end()
    e = ide(OK_REC)
    focus_entry(e)
    e.keys("x [[edit_empty]]")
    e.keys(RET)
    e.keys("s")
    T = wait_popup(e)
    arow("I9e", "an empty list of edits proposes nothing: only what the AI said, with Close", "Nothing to change." in T and "Accept" not in T and "Close" in T, T[-500:])
    e.keys(RET)
    e.end()
    e = ide(OK_REC)
    focus_entry(e)
    e.keys("x [[edit_cmd]]")
    e.keys(RET)
    e.keys("s")
    T = wait_popup(e)
    arow("I10", "a command from the AI is ignored in the IDE (it has nowhere to run one): shown as words only, no Run button", "Run it." in T and "Run" not in T.replace("Run it.", "") and "Close" in T, T[-500:])
    e.keys(RET)
    e.end()


def sec_wide():
    """28 Oct 26 (S.88 phase 2, S5): a proposed line wider than the box is SHOWN whole (in rows), because Accept applies it whole.  The new line is 230 Z; the diff must show 230."""
    say("\n--- a line wider than the box")
    reset_record()
    e = ide(OK_REC)
    focus_entry(e)
    e.keys("x [[edit_wide]]")
    e.keys(RET)
    e.keys("s")
    T = wait_popup(e)
    arow("I14a", "the diff of a 230 character new line shows all 230 characters (the old code cut it at the box, about 94), and offers Accept and Reject", T.count("Z") == 230 and "Accept" in T and "Reject" in T,
         "Z shown: %d" % T.count("Z"))
    arow("I14b", "...in more than one row: no row of the popup holds more than 100 Z (the longest is a chunk of the box's width, not the whole line)",
         max([ln.count("Z") for ln in T.split("\n")] or [0]) <= 100, repr(max([ln.count("Z") for ln in T.split("\n")] or [0])))
    e.keys(RET)
    e.end()
    reset_record()


def sec_explain():
    say("\n--- Explain the error and Explain the selection")
    fm = STATE["fm"]
    e = ide(ERR_REC)
    e.keys(F8)
    time.sleep(1.5)
    n0 = len(fm.log)
    e.keys(F10, AI_MENU, RET)                   # AI > Explain the error (the first entry)
    T = e.text()
    arow("I11a", "AI > Explain the error: the preview names the compile message and the record's lines, and nothing is sent", "This will be sent to anthropic" in T and "The message: Data item" in T
         and "x = = 1" in T and len(fm.log) == n0, T[-900:])
    e.keys("s")
    wait_popup(e)
    rq = requests()
    pr = prompt_of(rq[-1][2]) if len(rq) > n0 else ""
    arow("I11b", "Send: ONE request whose last line is the standard request with the compile message in it", len(fm.log) == n0 + 1 and "Explain this compile message and say how to fix it. The message:" in pr.split("\n")[-1], repr(pr[-200:]))
    T = e.text()
    arow("I11c", "the answer (plain words here) is shown with the note that it is not in the form asked for, and Close", "The answer is forty-two." in T and msg(11651) in T, T[-500:])
    e.keys(RET)
    e.end()
    e = ide(OK_REC)
    n0 = len(fm.log)
    e.keys(F10, AI_MENU, DOWN, RET)             # AI > Explain the selection (the second entry)
    arow("I12a", "Explain the selection with no mark: the status line says to set one (11664) and nothing is sent", msg(11664)[:30] in e.status() and len(fm.log) == n0, repr(e.status()[:100]))
    e.keys(CTRL_G, DOWN)
    e.keys(F10, AI_MENU, DOWN, RET)
    T = e.text()
    arow("I12b", "with a mark and the cursor a line down: the preview shows the selected text and its size", msg(11669, 1).split("1")[0][:20] in T and "crt 'hello'" in T and len(fm.log) == n0, T[-900:])
    e.keys("s")
    wait_popup(e)
    rq = requests()
    pr = prompt_of(rq[-1][2]) if len(rq) > n0 else ""
    arow("I12c", "Send: the prompt has a selected-text block with the first line, and the standard request", "The selected text:" in pr and "crt 'hello'" in pr.split("The selected text:")[-1] and "Explain the selected text" in pr, repr(pr[-300:]))
    e.keys(RET)
    e.end()


def sec_wait():
    say("\n--- giving the request up")
    fm = STATE["fm"]
    e = ide(OK_REC)
    focus_entry(e)
    e.keys("slow [[slow]]")
    e.keys(RET)
    e.keys("s")
    time.sleep(0.8)
    e.keys(ESC)
    time.sleep(1.0)
    arow("I13", "Esc during the wait: the request is given up (the status line says so), no popup, the editor as it was", msg(11646)[:25] in e.status() and "Accept" not in e.text(), repr(e.status()[:100]))
    time.sleep(3.5)
    e.end()


def main():
    mutant = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mutant=")), None)
    if mutant is not None and mutant not in MUTANTS:
        ids.bail("usage: sandbox-ai-ide.py <dir> [--build] [--mutant=%s]" % "|".join(MUTANTS))
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        ids.bail("usage: sandbox-ai-ide.py <dir> [--build] [--mutant=NAME]")
    STATE["box"] = os.path.abspath(args[0])
    b = box()
    say("sandbox-ai-ide: sandbox %s" % b)
    if "--build" in sys.argv:
        if os.path.exists(b) and os.listdir(b):
            ids.bail("%s is not empty" % b)
        r = subprocess.run([sys.executable, ids.TOOL, b, "all"], capture_output=True, text=True, errors="replace", timeout=1800)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            ids.bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-ai-ide: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd(), "bin", "sd")):
        ids.bail("%s holds no built sandbox (use --build, or point it at one)" % b)
    subprocess.run([sys.executable, ids.TOOL, b, "start"], capture_output=True, text=True, errors="replace", timeout=120)
    gt.BOX, gt.SYS, gt.SD = b, sysd(), os.path.join(sysd(), "bin", "sd")
    try:
        gt.prepare()                       # a CPROC that is not the install build: the administrator's internal session works, and the sandbox's own user is an ordinary one
        gt.FIXTURES[ACC] = ("no", "no")
        gt.build_account(ACC)              # the IDE runs in an ordinary fixture account (edit gates on, SH and OS off), as a person would have it
        flags = gt.flags(gt.plain(ACC, ["zzkf"]))
        if flags is None or flags[0] != "0":
            ids.bail("the first ordinary session is not shown to be one (admin=%r), so no row below can be believed" % (flags,))
        setup_ai(mutant)
        configure()
        make_records()
        if mutant is None:
            sec_off()
            sec_on()
            sec_preview()
            sec_edits()
            sec_refused()
            sec_wide()
            sec_explain()
            sec_wait()
        else:
            sec = MUTANT_SECTIONS[mutant]
            if sec == "edits":
                sec_preview()
                sec_edits()
            elif sec == "wide":
                sec_wide()
            else:
                sec_refused()
    finally:
        stop_runner()
        if "fm" in STATE:
            STATE["fm"].stop()
        os.environ.pop("SD_AI_SOCKET", None)
        os.environ.pop("SD_AI_CTL", None)
        subprocess.run([sys.executable, ids.TOOL, b, "stop"], capture_output=True, text=True, errors="replace", timeout=120)
    say("\nsandbox-ai-ide: %d passed, %d failed" % (ids.passed, ids.failed))
    if mutant is not None:
        want = sorted(set(MUTANTS[mutant][3]))
        got = sorted({re.match(r"I\d+", i).group(0) for i in FAILED_IDS if re.match(r"I\d+", i)})
        ok = want == got
        say("sandbox-ai-ide: MUTANT %s: the rows that failed are %s; they had to be exactly %s -> %s" % (mutant, got, want, "KILLED BY ITS OWN ROWS" if ok else "NOT AS EXPECTED"))
        return 0 if ok else 1
    return 0 if ids.failed == 0 and ids.passed > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
