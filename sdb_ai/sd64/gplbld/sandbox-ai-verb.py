#!/usr/bin/env python3
#
# sandbox-ai-verb.py - the `ai` verb and the kernel's transport (K$AI.*) RUN on a private SD, against the real helper and the fake provider (S.69 step 2, group C;
# plan .claude/plan-ai-step2.md).  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-ai-verb.py <dir> [--build] [--mutant=NAME]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent).  Exit 0 every row passed, 1 a row failed, 2 it could
# not run.  With --mutant=NAME one change is made to the SANDBOX'S OWN COPY of the `ai` verb and exit 0 means the rows that had to fail failed and no others (MUTANTS below).
#
# WHAT RUNS.  The helper (gplbld/sd-ai) is served by ai-runner.py on a Unix socket as systemd would serve it, with the person who runs this suite as the administrator and a
# member of the AI group (the runner's two arguments replace the names the installed helper has fixed; nothing else of the helper is changed).  The provider is gplbld/fakemodel.py,
# TLS with a throw-away CA, which LOGS every request, so a row can say what was sent and what was not.  The sessions are an ORDINARY fixture account's (`sd -a<account>`) and
# the administrator's, piped, so the answer to "Send it?" is the next line of the input; the sandbox's kernel finds the helper through SD_AI_SOCKET (op_ai.c; the product never sets it).
#
# THE INSTRUMENT.  Every session prints its input lines and its output; every row that says "nothing was sent" is judged by the FAKE's request log and the audit file, not by what
# the verb printed; the control row V4 sees one request arrive and a null run (the provider never reached) fails its rows, it does not pass them.
#
#   V0-V3   no text; no provider; no model; no key -> the verb's words (11623, 11624, 11626), and the fake saw nothing
#   V4      the control: the preview, the answer, the token line; ONE request at the fake with the right key, model, system text, text and limit; ONE audit line with the sizes
#           and neither the text nor the key
#   V5-V8   an answer that is not y/yes sends nothing (n, empty, anything else, the input ending); Y does send
#   V9-V11  quotes around the text are taken off; characters a shell or JSON would mind arrive exactly; bytes above 127 arrive as ?; text ending in ? must be quoted (V10b, V10c)
#   V12     the account is not in the AI group -> 11625 before the preview, nothing sent
#   V13     the helper is not running -> 11607
#   V14-V16 the provider fails / answers with escape sequences / stops at the token limit -> words, no escape character on the screen, the cut and the replaced count said
#   P1-P3   an INTERNAL probe calling K$AI.START itself: the audit line names the real program; the helper (not the verb) refuses a caller outside the group; no helper -> ERR nohelper
#   V17     the helper's hourly limit is reached -> words; the audit line is written all the same
#   P4      a program that is not $internal cannot compile a KERNEL call at all (the wall that comes first)
# NOT HELD: the real systemd socket, the helper as the user sdai, a real provider (the owner's live check), and the AI choice page and the panel (later groups).
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TREE = os.path.dirname(HERE)
sys.path.insert(0, HERE)


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


ag = _load("sandbox_aigate_for_verb", "sandbox-aigate.py")
fg, q3 = ag.fg, ag.q3
import fakemodel  # noqa: E402

say, has, put = q3.say, q3.has, q3.put
ME = fg.ME
KEY = ag.KEY
ACCT = "zzaiv"
FAILED_IDS = []
MODEL = "claude-test"


def row(name, ok, detail=""):
    q3.row(name, ok, detail)
    if not ok:
        FAILED_IDS.append(name.split()[0])


def msg(n, *args):
    return fg.msg(n, *args)


def verb_source():
    return open(os.path.join(TREE, "sdsys", "gpl.bp", "ai"), encoding="utf-8").read()


def system_text():
    m = re.search(r"^\s*system\.text = '([^']+)'", verb_source(), re.M)
    if not m:
        q3.bail("the verb's fixed system sentence was not found in the source")
    return m.group(1)


MUTANTS = {
    # name: (old text of the sandbox's ai, new text, the row ids that must fail and no others)
    "no-preview": ("   if ans # 'y' and ans # 'yes' then", "   if @false then", ["V5", "V6", "V7", "V8"]),
    "no-gate-check": ("   if not(st{'gate'}) then", "   if @false then", ["V12"]),
    "adds-to-prompt": ("system.text : @fm : 1024 : @fm : question)", "system.text : @fm : 1024 : @fm : question : ' (account ' : @who : ')')", ["V4", "V9", "V10", "V11"]),
}


def start_runner(box, providers, gate_group):
    state = os.path.join(box, "ai", "state")
    sock = os.path.join(box, "ai", "sock")
    p = subprocess.Popen([sys.executable, os.path.join(HERE, "ai-runner.py"), "--socket", sock, "--state", state, "--providers", providers, "--admin-user", ME,
                          "--gate-group", gate_group], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    if p.stdout.readline().strip() != "ready":
        q3.bail("the AI helper's runner did not start")
    return p


def stop_runner(p):
    try:
        p.terminate()
        p.wait(timeout=10)
    except Exception:
        pass


def requests(fm):
    """The requests the fake provider has had, each as (path, headers, parsed body)."""
    out = []
    for r in fm.log:
        try:
            body = json.loads(r["body"].decode("utf-8"))
        except ValueError:
            body = None
        out.append((r["path"], r["headers"], body))
    return out


def prompt_of(body):
    return body["messages"][-1]["content"]


def ask(account_cmds, label, fm, who="user"):
    """Run the commands in an ordinary session (or the administrator's) and say what the fake and the audit file saw."""
    off = fg.audit_off()
    n0 = len(fm.log)
    out = q3.plain(ACCT, account_cmds) if who == "user" else q3.adm(account_cmds, internal=(who == "internal"))
    new = fg.audit_new(off)
    say("    [%s] output: %r" % (label, out[-12:]))
    say("    [%s] requests the fake provider had: %d; audit gained: %r" % (label, len(fm.log) - n0, new))
    return out, len(fm.log) - n0, new or ""


def req_lines(audit):
    return [ln for ln in audit.split("\n") if re.search(r"\bai request\b", ln)]


def verb_rows(fm, box, providers):
    sysx = system_text()

    # ---- before anything is set: the verb's words
    out, n, aud = ask(["ai"], "V0", fm)
    row("V0 no text: the usage (11623), nothing sent, no 'ai request' audit line", msg(11623) in out and n == 0 and not req_lines(aud), repr(out[-4:]))
    out, n, aud = ask(["ai hello", "y"], "V1", fm)
    row("V1 no provider is chosen: 11624 (the AI is off), no preview, nothing sent, no audit line", msg(11624) in out and n == 0 and not req_lines(aud)
        and not any(ln.startswith("This will be sent to") for ln in out), repr(out[-4:]))
    out2 = q3.adm(["set.ai provider anthropic"])
    if msg(11611, "anthropic") not in out2:
        q3.bail("set.ai provider anthropic did not work in the setup: %r" % out2[-3:])
    out, n, aud = ask(["ai hello", "y"], "V2", fm)
    row("V2 a provider and no model: 11626 (anthropic, model), no preview, nothing sent", msg(11626, "anthropic", "model") in out and n == 0 and not req_lines(aud), repr(out[-4:]))
    out2 = q3.adm(["set.ai model anthropic " + MODEL])
    if msg(11613, "anthropic", MODEL) not in out2:
        q3.bail("set.ai model did not work in the setup: %r" % out2[-3:])
    out, n, aud = ask(["ai hello", "y"], "V3", fm)
    row("V3 a model and no key: 11626 (anthropic, key), no preview, nothing sent", msg(11626, "anthropic", "key") in out and n == 0 and not req_lines(aud), repr(out[-4:]))
    kp = os.path.join(box, "ai", "state", "keys", "anthropic")
    put(kp, KEY + "\n")
    os.chmod(kp, 0o600)

    # ---- the control
    q = "what is the answer"
    out, n, aud = ask(["ai " + q, "y"], "V4", fm)
    rq = requests(fm)
    last = rq[-1] if rq else (None, {}, None)
    body = last[2] or {}
    size = len(q) + len(sysx)
    row("V4a the preview names the provider, the model and the size, then shows the fixed sentence and the text, then asks", msg(11628, "anthropic", MODEL, size) in out and sysx in out and q in out
        and any(ln.startswith(msg(11629)) for ln in out), repr(out[:8]))
    row("V4b the answer is printed as text, with the token line (11634) and no failure line", fakemodel.PLAIN_TEXT in out and msg(11634, 11, 7, "anthropic") in out
        and not any(ln.startswith("The AI did not answer") for ln in out), repr(out[-6:]))
    row("V4c ONE request reached the provider, with the key in the right header, the model, the fixed system sentence, the limit of 1024 tokens and exactly the text that was typed",
        n == 1 and last[0] == "/v1/messages" and last[1].get("x-api-key") == KEY and body.get("model") == MODEL and body.get("max_tokens") == 1024 and prompt_of(body) == q
        and body.get("system", [{}])[0].get("text") == sysx and sorted(body.keys()) == ["max_tokens", "messages", "model", "system"] and len(body["messages"]) == 1, repr((n, last[0], body)))
    rl = req_lines(aud)
    row("V4d ONE audit line, written by the kernel: account, the program's name and the size; the text and the key are in no audit line",
        len(rl) == 1 and re.search(r"ai request account=%s program=ai bytes\.out=%d$" % (re.escape(ACCT), size), rl[0]) is not None and q not in aud and KEY not in aud, repr(rl))
    row("V4e the key is on no screen line", not any(KEY in ln for ln in out), repr(out[:3]))

    # ---- anything but yes sends nothing
    for rid, label, answer, expect_sent in (("V5", "n", "n", False), ("V6", "an empty answer", "", False), ("V7", "'yep'", "yep", False)):
        out, n, aud = ask(["ai " + q, answer], rid, fm)
        row("%s the answer %s: 11630 ('Nothing was sent'), nothing at the provider, no audit line" % (rid, label), msg(11630) in out and n == 0 and not req_lines(aud), repr(out[-3:]))
    out, n, aud = ask(["ai " + q], "V8", fm)
    row("V8 the input ends at the question (the session's next line is OFF): nothing is sent, as for a pipe that has ended", n == 0 and not req_lines(aud) and msg(11630) in out, repr(out[-3:]))
    out, n, aud = ask(["ai " + q, "Y"], "V8b", fm)
    row("V8b 'Y' is yes (case does not matter): one request, the answer is printed", n == 1 and fakemodel.PLAIN_TEXT in out and len(req_lines(aud)) == 1, repr(out[-4:]))
    out, n, aud = ask(["ai " + q, "yes"], "V8c", fm)
    row("V8c 'yes' is yes", n == 1 and fakemodel.PLAIN_TEXT in out, repr(out[-4:]))

    # ---- what arrives
    out, n, aud = ask(['ai "what is a select list?"', "y"], "V9", fm)
    got = prompt_of(requests(fm)[-1][2]) if n else None
    row("V9 a pair of double quotes round the text is taken off; the preview shows the text without them", got == "what is a select list?" and "what is a select list?" in out, repr((got, out[:5])))
    out, n, aud = ask(["ai 'one two'", "y"], "V9b", fm)
    got = prompt_of(requests(fm)[-1][2]) if n else None
    row("V9b a pair of single quotes likewise", got == "one two", repr(got))
    odd = "a\\b $c \"d\" 'e' ; | & `f` {g} <h> * . ? x"
    out, n, aud = ask(["ai " + odd, "y"], "V10", fm)
    got = prompt_of(requests(fm)[-1][2]) if n else None
    row("V10 a backslash, dollar, both quotes, semicolon, pipe, ampersand, backtick, braces, angle brackets, a star and a question mark inside arrive exactly as typed", got == odd, repr((got, odd)))
    out, n, aud = ask(["ai what is it?", "y"], "V10b", fm)
    row("V10b text that ENDS with ? is not run (TCL adds a command that ends with ? to the stack without running it): no preview, nothing sent, which is why 11623 says to quote it",
        n == 0 and not req_lines(aud) and not any(ln.startswith("This will be sent to") for ln in out) and "quotes" in msg(11623), repr(out[-3:]))
    out, n, aud = ask(['ai "what is it?"', "y"], "V10c", fm)
    got = prompt_of(requests(fm)[-1][2]) if n else None
    row("V10c the same text in quotes is run, and the question mark arrives (the quotes do not)", got == "what is it?", repr(got))
    out, n, aud = ask(["ai café au lait", "y"], "V11", fm)
    got = prompt_of(requests(fm)[-1][2]) if n else None
    row("V11 bytes above 127 become ? on the way out (English only; each byte of the two that make an e-acute)", got == "caf?? au lait", repr(got))

    # ---- failures of the provider
    for rid, marker, check, what in (
            ("V14", "[[err500]]", lambda o: any(ln.startswith("The AI did not answer: ") for ln in o) and not any("Traceback" in ln for ln in o), "words, and no traceback"),
            ("V15", "[[ctrl]]", lambda o: any(ln.startswith("Fine.") for ln in o), "the text, with nothing that moves the cursor"),
            ("V16", "[[trunc]]", lambda o: msg(11632) in o, "the cut said (11632)")):
        out, n, aud = ask(["ai " + marker + " tell me", "y"], rid, fm)
        row("%s the provider answers %s: %s" % (rid, marker, what), check(out) and n >= 1 and not any(("\x1b" in ln or "\x07" in ln) for ln in out), repr(out[-6:]))
    out, n, aud = ask(["ai [[ctrl]] tell me", "y"], "V15b", fm)
    rep = [ln for ln in out if "characters of the answer were replaced" in ln]
    row("V15b the escape sequences, the SD marks and the curly quotes of the reply are gone before SD sees it: a replaced count is said (11633)", len(rep) == 1 and re.match(r"^\d+ characters of the answer were replaced with \?", rep[0]) is not None, repr(out[-8:]))

    # ---- the helper's own limit
    q3.adm(["set.ai limit requests-hour 1"])
    out, n, aud = ask(["ai hello", "y"], "V17", fm)
    q3.adm(["set.ai limit requests-hour 1000"])
    row("V17 the helper's hourly limit is reached: the verb says so in words (11627, 'limit'), nothing reached the provider, and the audit line is there all the same (the kernel writes it before the call)",
        any(ln.startswith("The AI did not answer: limit (") for ln in out) and n == 0 and len(req_lines(aud)) == 1, repr(out[-3:]))
    return sysx


def probes(fm, box, providers, runner_cell):
    say("\n--- the internal probe and the program that is not internal ---")
    put(os.path.join(q3.SYS, "gpl.bp", "zzaip"), "\n".join([
        "$internal", "program zzaip", "$catalog $zzaip", "$include keys.h", "$include int$keys.h",
        "   r = kernel(K$AI.START, 'sys':@fm:'64':@fm:'probe question')",
        "   crt 'AIP start=':convert(@fm, '|', r)",
        "   if r<1> = 'OK' then",
        "      for i = 1 to 150",
        "         r = kernel(K$AI.POLL, 0)",
        "         if r<1> # 'W' then exit",
        "         nap 100",
        "      next i",
        "      crt 'AIP poll=':convert(@fm, '|', r)",
        "   end",
        "end", ""]))
    out = q3.adm(["BASIC gpl.bp zzaip"], internal=True)
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        q3.bail("the probe did not compile:\n" + "\n".join(out[-6:]))
    ni = os.path.join(q3.BOX, "user_accounts", ACCT, "bp", "zzni")
    put(ni, "\n".join(["   crt 'NI status=':convert(@fm, '|', kernel(163, 0))",
                       "   crt 'NI start=':convert(@fm, '|', kernel(160, 'sys':@fm:'64':@fm:'not internal'))", "end", ""]))
    n0 = len(fm.log)
    out = q3.plain(ACCT, ["BASIC bp zzni"])
    row("P4 a program that is not $internal cannot call KERNEL() at all: it does not compile (the kernel's own internal-only test in k_ai is the second wall, read as text by test-ai-units.py); nothing is sent",
        has(out, r"Compiled 1 program\(s\) with errors") and has(out, r"KERNEL") and len(fm.log) == n0, repr(out[-4:]))

    out, n, aud = ask(["RUN gpl.bp zzaip"], "P1", fm, who="internal")
    rl = req_lines(aud)
    poll = [ln for ln in out if ln.startswith("AIP poll=D|")]
    row("P1 an internal program calls K$AI.START: the request goes, the reply is the helper's JSON, and the audit line names THAT program (zzaip), not 'ai'",
        n == 1 and len(poll) == 1 and '"t": "ok"' in poll[0] and len(rl) == 1 and "program=zzaip" in rl[0] and "bytes.out=%d" % (len("sys") + len("probe question")) in rl[0], repr((out[-3:], rl)))

    # the helper refuses a caller outside the group, whatever the verb said: restart the runner with a group the person is not in
    stop_runner(runner_cell[0])
    runner_cell[0] = start_runner(box, providers, "zzaiv-no-such-group")
    out, n, aud = ask(["RUN gpl.bp zzaip"], "P2", fm, who="internal")
    poll = [ln for ln in out if ln.startswith("AIP poll=D|")]
    row("P2 the verb is skipped and the kernel is called directly by a caller outside the group: the HELPER refuses (nogate), nothing reaches the provider",
        n == 0 and len(poll) == 1 and '"code": "nogate"' in poll[0], repr(out[-3:]))
    out, n, aud = ask(["ai hello", "y"], "V12", fm)
    row("V12 the account is not in the AI group: 11625 names the way to allow it (modify.account <name> ai-on), no preview, nothing sent", msg(11625, ACCT) in out and n == 0
        and not any(ln.startswith("This will be sent to") for ln in out), repr(out[-3:]))
    stop_runner(runner_cell[0])
    runner_cell[0] = None
    out, n, aud = ask(["ai hello", "y"], "V13", fm)
    row("V13 the helper is not running: 11607 (could not be reached), nothing sent", msg(11607) in out and n == 0, repr(out[-3:]))
    out, n, aud = ask(["RUN gpl.bp zzaip"], "P3", fm, who="internal")
    row("P3 no helper: K$AI.START answers ERR|nohelper at once (nothing is waiting for an answer that cannot come)", has(out, r"^AIP start=ERR\|nohelper$"), repr(out[-3:]))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    mutant = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mutant=")), None)
    if len(args) != 1 or (mutant is not None and mutant not in MUTANTS):
        q3.bail("usage: sandbox-ai-verb.py <dir> [--build] [--mutant=%s]" % "|".join(MUTANTS))
    q3.BOX = os.path.abspath(args[0])
    q3.SYS = os.path.join(q3.BOX, "sys")
    q3.SD = os.path.join(q3.SYS, "bin", "sd")
    box = q3.BOX
    say("sandbox-ai-verb: sandbox %s" % box)
    say("sandbox-ai-verb: tree    %s" % TREE)
    say("sandbox-ai-verb: person  %s (the administrator for the helper and a member of the AI group; the sandbox's sessions are theirs)" % ME)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            q3.bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, q3.TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            q3.bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-ai-verb: built, bootstrap passed")
    elif not os.path.isfile(q3.SD):
        q3.bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, q3.TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)
    runner_cell = [None]
    fm = None
    try:
        say("\n--- preparation: a CPROC that is not the install build, the fixture account, the helper and the fake provider ---")
        q3.prepare()
        q3.build_account(ACCT)
        if mutant is not None:
            old, new, _kills = MUTANTS[mutant]
            path = os.path.join(q3.SYS, "gpl.bp", "ai")
            shutil.copyfile(os.path.join(TREE, "sdsys", "gpl.bp", "ai"), path)          # a sandbox used for an earlier mutant starts from the tree's verb again
            src = open(path, encoding="utf-8", errors="replace").read()
            if src.count(old) != 1:
                q3.bail("mutant %s: the text to change is found %d times, not once" % (mutant, src.count(old)))
            put(path, src.replace(old, new))
            out = q3.adm(["BASIC gpl.bp ai"], internal=True)
            if not has(out, r"^Compiled 1 program\(s\) with no errors"):
                q3.bail("the mutated ai did not compile:\n" + "\n".join(out[-6:]))
            say("sandbox-ai-verb: MUTANT %s: the rows that must fail, and nothing else: %s" % (mutant, ", ".join(MUTANTS[mutant][2])))
        shutil.rmtree(os.path.join(box, "ai"), ignore_errors=True)
        for sub in ("state/keys", "state/state", "pki"):
            os.makedirs(os.path.join(box, "ai", sub))
        pki = fakemodel.make_pki(os.path.join(box, "ai", "pki"))
        fm = fakemodel.FakeModel(pki).start()
        providers = os.path.join(box, "ai", "ai-providers")
        text = open(os.path.join(HERE, "ai-providers")).read()
        for old, new in (("https://api.anthropic.com/v1/messages", "https://127.0.0.1:%d/v1/messages" % fm.port),
                         ("https://api.openai.com/v1/chat/completions", "https://127.0.0.1:%d/v1/chat/completions" % fm.port),
                         ("https://api.deepseek.com/chat/completions", "https://127.0.0.1:%d/chat/completions" % fm.port)):
            text = text.replace(old, new)
        put(providers, text)
        ca = os.path.join(pki, "ca.crt")
        mygroup = subprocess.run(["id", "-gn"], capture_output=True, text=True).stdout.strip()
        runner_cell[0] = start_runner(box, providers, mygroup)
        os.environ["SD_AI_SOCKET"] = os.path.join(box, "ai", "sock")
        os.environ["SD_AI_CTL"] = os.path.join(HERE, "sd-ai-ctl")
        out = q3.adm(["set.ai ca " + ca, "set.ai limit requests-hour 1000"])
        if msg(11619, ca) not in out or msg(11621, "requests-hour", "1000") not in out:
            q3.bail("set.ai ca and limit did not work in the setup (the default is 20 requests an hour, which this suite exceeds): %r" % out[-3:])
        say("\n=== the ai verb ===")
        verb_rows(fm, box, providers)
        probes(fm, box, providers, runner_cell)
    finally:
        if runner_cell[0] is not None:
            stop_runner(runner_cell[0])
        if fm is not None:
            fm.stop()
        os.environ.pop("SD_AI_SOCKET", None)
        os.environ.pop("SD_AI_CTL", None)
        subprocess.run([sys.executable, q3.TOOL, box, "stop"], capture_output=True, text=True, errors="replace", timeout=120)
    say("\nsandbox-ai-verb: %d passed, %d failed" % (q3.passed, q3.failed))
    if mutant is not None:
        want = sorted(set(MUTANTS[mutant][2]))
        got = sorted(set(i for i in FAILED_IDS if re.match(r"[VP]\d+", i)))
        got = sorted({re.match(r"[VP]\d+", i).group(0) for i in got})
        ok = want == got
        say("sandbox-ai-verb: MUTANT %s: the rows that failed are %s; they had to be exactly %s -> %s" % (mutant, got, want, "KILLED BY ITS OWN ROWS" if ok else "NOT AS EXPECTED"))
        return 0 if ok else 1
    return 1 if q3.failed else 0


if __name__ == "__main__":
    sys.exit(main())
