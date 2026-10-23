#!/usr/bin/env python3
#
# sandbox-aigate.py - the `ai` gate and the AI settings RUN on a private SD (S.69 step 2, groups B; plan .claude/plan-ai-step2.md).  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-aigate.py <dir> [--build] [--mutant=NAME]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent).  Exit 0 every row passed, 1 a row failed, 2 it
# could not run.  With --mutant=NAME only PART 1 runs, and exit 0 means the mutant was killed by exactly the rows listed for it (MUTANTS below).
#
# PART 1 - MODIFY.ACCOUNT <account> AI-ON | AI-OFF, the program itself, against a SCRATCH group file and a stand-in for the privileged helper, exactly as sandbox-filesgrp.py does
#          it (that suite's shim runs the REAL sd-elevate --dry-run first, so sdaiusers has to be on its whitelist, and edits the scratch file; the two group lookups read it).
#          Cases I0 to I11: the add, "already", the removal, the helper failing, the helper saying yes and changing nothing (the read back catches it), the group missing on the
#          machine (10024), a person who is not in sdusers, a group account (10087), two words in one command, a conflict (11791) and the usage.
# PART 2 - SET.AI, the administrator's verb, against a REAL helper (ai-runner.py serves gplbld/sd-ai on a Unix socket as systemd would, the caller being the person who runs
#          this suite, who is made the "administrator" and a member of the AI group for the helper by the runner's two arguments) and the fake provider (gplbld/fakemodel.py,
#          TLS with a throw-away CA): the VOC (only SDSYS has the verb), the reading form, provider / model / custom / ca / limit and their messages and audit lines, a refusal
#          by the helper, the characters a word may not have (nothing is run: a sentinel file shows it), the helper not running, and on a PSEUDO-TERMINAL the key: the prompt
#          comes from the helper's client and not from SD, nothing typed is shown, the key is in the helper's key file and in no message and no audit line.
# NOT HELD: a real systemd socket, the helper as the user sdai, sudo, create.account's AI-ON (it makes Linux users: test-ai-units.py reads it as text and the VM witness runs it),
# the AI choice page and `ai text` (later groups).
import getpass
import importlib.util
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
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


fg = _load("sandbox_filesgrp_for_ai", "sandbox-filesgrp.py")
q3 = fg.q3
import fakemodel  # noqa: E402
from ptydrive import PtySession  # noqa: E402

say, has, put = q3.say, q3.has, q3.put
ME = fg.ME
ACCT = fg.ACCT
GROUP_ACCT = "zzaig"                   # a group account (sdg_), for the refusal
KEY = "test-key-0123456789"
FAILED_IDS = []


def row(name, ok, detail=""):
    q3.row(name, ok, detail)
    if not ok:
        FAILED_IDS.append(name.split()[0])


MUTANTS = {
    # name: (old text of the sandbox's modifya, new text, the case ids whose rows must fail and no others)
    "no-read-back": ("      if files.stat = 0 and cg.now # cg.want then files.stat = 2\n", "", ["I5"]),          # the group changer's read back (shared with set.files; only the I rows run here)
    "no-sdusers-check": ("ai.want then\n      in.sdusers = is_grp_member(files.user, 'sdusers')", "@false then\n      in.sdusers = is_grp_member(files.user, 'sdusers')", ["I7"]),
    "no-group-check": ("      if not(ai.found) then", "      if @false then", ["I6"]),
}


def msg(n, *args):
    return fg.msg(n, *args)


def gfile():
    return os.path.join(q3.BOX, "grp", "group")


def write_ai_group(ai, sdusers=True, with_ai_group=True):
    """The scratch group file: ME in sdusers, and in sdaiusers when AI; the other route groups empty (the file the shim and the two lookups read)."""
    lines = ["root:x:0:", fg.grp_line("sdusers", 2000, [ME] if sdusers else []), fg.grp_line("sdfiles", 2001, []), fg.grp_line("sdfileswrite", 2002, []),
             fg.grp_line("sdfilesadmin", 2003, [])]
    if with_ai_group:
        lines.append(fg.grp_line("sdaiusers", 2004, [ME] if ai else []))
    lines.append(fg.grp_line("wheel", 10, []))
    put(gfile(), "\n".join(lines))


def run_ai(cid, label, command, ai_before=False, sdusers=True, with_ai_group=True, inject=None, want_ai=None, want_calls=(), want_lines=(), deny_lines=(), want_fail=False,
           want_audit=(), deny_audit=()):
    """One case of part 1.  want_ai: the person is afterwards in sdaiusers (True / False), None when the group does not exist; want_calls: [(verb, group)] in order."""
    write_ai_group(ai_before, sdusers, with_ai_group)
    put(os.path.join(q3.BOX, "grp", "calls.log"), "")
    put(os.path.join(q3.BOX, "grp", "inject.json"), json.dumps(inject or {}))
    say("\n  %s %s" % (cid, label))
    say("    [inputs] scratch group file before: sdaiusers=%r sdusers=%r (group exists: %s); command %r; injected into the helper: %r" % (
        fg.read_group().get("sdaiusers"), fg.read_group().get("sdusers"), with_ai_group, command, inject or {}))
    off = fg.audit_off()
    out = q3.adm([command])
    new = fg.audit_new(off)
    after = fg.read_group()
    calls = fg.read_calls()
    say("    [outputs] helper calls: %r; sdaiusers after: %r; output tail: %r; audit gained: %r" % (calls, after.get("sdaiusers"), out[-4:], new))
    row("%so %s: the output has %s%s" % (cid, label, "; ".join(repr(x) for x in want_lines) if want_lines else "no line that is asked for",
                                          ("" if not deny_lines else " and none of " + "; ".join(repr(x) for x in deny_lines))),
        all(any(ln == x for ln in out) for x in want_lines) and not any(any(ln == x for ln in out) for x in deny_lines), repr(out[-6:]))
    if want_fail:
        pat = re.escape(msg(10081, ACCT, "\x00")).replace("\x00", r"\d+")
        row("%sf %s: the failure is reported as 10081 with a status (never as a success)" % (cid, label), any(re.fullmatch(pat, ln) for ln in out), repr(out[-4:]))
    if want_audit or deny_audit:
        row("%sa %s: the audit trail %s%s" % (cid, label, ("has " + "; ".join(want_audit)) if want_audit else "has no line that is asked for",
                                               ("" if not deny_audit else " and has none of " + "; ".join(deny_audit))),
            new is not None and all(re.search(x, new, re.M) for x in want_audit) and not any(re.search(x, new, re.M) for x in deny_audit), repr(new))
    if want_ai is not None:
        row("%sg %s: the person is afterwards %s sdaiusers" % (cid, label, "in" if want_ai else "not in"), (ME in after.get("sdaiusers", [])) == want_ai, repr(after.get("sdaiusers")))
    exp = ["%s %s %s" % (v, ME, g) for v, g in want_calls]
    row("%sc %s: the helper was called %s" % (cid, label, ("in this order: " + ", ".join("%s %s" % x for x in want_calls)) if want_calls else "NEVER"), calls == exp, repr(calls))
    return out


def part1():
    say("\n=== PART 1: MODIFY.ACCOUNT %s AI-ON / AI-OFF ===" % ACCT)
    yes, no = msg(11606, ACCT, "yes"), msg(11606, ACCT, "no")
    already = msg(10080, ACCT)

    def aud(word):
        return r"modify\.account %s account=%s$" % (re.escape(word), re.escape(ACCT))
    run_ai("I0", "CONTROL, ai-on (typed in lower case) for a person who is in sdusers and not in sdaiusers", "modify.account %s ai-on" % ACCT, want_ai=True, want_calls=[("addgroup", "sdaiusers")],
           want_lines=[yes], deny_lines=[already], want_audit=[aud("ai-on")])
    run_ai("I1", "ai-on again: 'already had that access', nothing called, nothing audited", "MODIFY.ACCOUNT %s AI-ON" % ACCT, ai_before=True, want_ai=True, want_lines=[already], deny_lines=[yes],
           deny_audit=[aud("ai-on")])
    run_ai("I2", "ai-off", "MODIFY.ACCOUNT %s AI-OFF" % ACCT, ai_before=True, want_ai=False, want_calls=[("delgroup", "sdaiusers")], want_lines=[no], want_audit=[aud("ai-off")])
    run_ai("I3", "ai-off for a person who is not in the group: 'already', nothing called", "MODIFY.ACCOUNT %s AI-OFF" % ACCT, want_ai=False, want_lines=[already], deny_lines=[no],
           deny_audit=[aud("ai-off")])
    run_ai("I4", "ai-on, the helper FAILS", "MODIFY.ACCOUNT %s AI-ON" % ACCT, inject={"addgroup sdaiusers": ["fail"]}, want_ai=False, want_calls=[("addgroup", "sdaiusers")], deny_lines=[yes],
           want_fail=True, deny_audit=[aud("ai-on")])
    run_ai("I5", "ai-on, the helper says yes and changes nothing: the read back catches it", "MODIFY.ACCOUNT %s AI-ON" % ACCT, inject={"addgroup sdaiusers": ["noop"]}, want_ai=False,
           want_calls=[("addgroup", "sdaiusers")], deny_lines=[yes], want_fail=True, deny_audit=[aud("ai-on")])
    run_ai("I6", "ai-on on a machine without the Linux group sdaiusers: 10024 names it and nothing is called", "MODIFY.ACCOUNT %s AI-ON" % ACCT, with_ai_group=False,
           want_lines=[msg(10024, "sdaiusers")], deny_lines=[yes])
    run_ai("I7", "ai-on for a person who is not in sdusers: refused (10081, status 2), nothing called", "MODIFY.ACCOUNT %s AI-ON" % ACCT, sdusers=False,
           want_lines=[msg(10081, ACCT, 2)], deny_lines=[yes], want_ai=False)
    # a group account
    put(os.path.join(q3.SYS, "accounts", GROUP_ACCT), "\n".join([os.path.join(q3.BOX, "user_accounts", GROUP_ACCT), "", "sdg_" + GROUP_ACCT, "", "", "", "no", "no"]) + "\n")
    run_ai("I8", "ai-on for a GROUP account: 10087 (a group account has no Linux user and no remote access)", "MODIFY.ACCOUNT %s AI-ON" % GROUP_ACCT, want_lines=[msg(10087, GROUP_ACCT)], deny_lines=[yes])
    run_ai("I8b", "ai-off for a GROUP account: the same", "MODIFY.ACCOUNT %s AI-OFF" % GROUP_ACCT, ai_before=True, want_lines=[msg(10087, GROUP_ACCT)], deny_lines=[no])
    run_ai("I9", "two words in one command: files-on and ai-on are carried out in the list's order (files first), and the summary says both", "MODIFY.ACCOUNT %s AI-ON FILES-ON" % ACCT,
           want_ai=True, want_calls=[("addgroup", "sdfiles"), ("addgroup", "sdaiusers")], want_lines=[msg(11793, ACCT, 2, "files-on, ai-on"), yes],
           want_audit=[aud("files-on"), aud("ai-on")])
    run_ai("I10", "ai-on with ai-off: refused before anything changes (11791)", "MODIFY.ACCOUNT %s AI-ON AI-OFF" % ACCT, want_lines=[msg(11791, "ai-on", "ai-off")], deny_lines=[yes, no], want_ai=False)
    write_ai_group(False)
    out = q3.adm(["MODIFY.ACCOUNT %s" % ACCT])
    row("I11 no action: the usage names the AI words ('modify.account <account> ai-on | ai-off')", any(ln.strip() == "modify.account <account> ai-on | ai-off" for ln in out), repr(out[:16]))
    out = q3.adm(["MODIFY.ACCOUNT %s AI-SIDEWAYS" % ACCT])
    row("I12 a word that is not an action is still refused as typed (11790), the AI words did not widen it", any("AI-SIDEWAYS is not a modify.account action" in ln for ln in out), repr(out[-3:]))


def start_runner(box, providers, ca):
    state = os.path.join(box, "ai", "state")
    sock = os.path.join(box, "ai", "sock")
    mygroup = subprocess.run(["id", "-gn"], capture_output=True, text=True).stdout.strip()
    p = subprocess.Popen([sys.executable, os.path.join(HERE, "ai-runner.py"), "--socket", sock, "--state", state, "--providers", providers, "--admin-user", ME, "--gate-group", mygroup],
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    if p.stdout.readline().strip() != "ready":
        q3.bail("the AI helper's runner did not start")
    return p


def conf_lines(box):
    try:
        return open(os.path.join(box, "ai", "state", "ai.conf")).read().split("\n")
    except OSError:
        return []


def part2():
    say("\n=== PART 2: SET.AI against a real helper and the fake provider ===")
    box = q3.BOX
    shutil.rmtree(os.path.join(box, "ai"), ignore_errors=True)
    for sub in ("state/keys", "state/state", "pki"):
        os.makedirs(os.path.join(box, "ai", sub))
    pki = fakemodel.make_pki(os.path.join(box, "ai", "pki"))
    fm = fakemodel.FakeModel(pki).start()
    ca = os.path.join(pki, "ca.crt")
    providers = os.path.join(box, "ai", "ai-providers")
    text = open(os.path.join(HERE, "ai-providers")).read()
    for old, new in (("https://api.anthropic.com/v1/messages", "https://127.0.0.1:%d/v1/messages" % fm.port), ("https://api.openai.com/v1/chat/completions", "https://127.0.0.1:%d/v1/chat/completions" % fm.port),
                     ("https://api.deepseek.com/chat/completions", "https://127.0.0.1:%d/chat/completions" % fm.port)):
        text = text.replace(old, new)
    put(providers, text)
    runner = start_runner(box, providers, ca)
    sock = os.path.join(box, "ai", "sock")
    ctl = os.path.join(HERE, "sd-ai-ctl")
    os.environ["SD_AI_SOCKET"] = sock
    os.environ["SD_AI_CTL"] = ctl
    try:
        q3.build_account("zzord")
        out = q3.plain("zzord", ["set.ai"])
        row("J0 an ordinary account has no set.ai: it is not in its VOC (the verb is SDSYS's alone)", any("not in your VOC" in ln for ln in out), repr(out[:4]))
        a0 = fg.audit_off()
        out = q3.adm(["set.ai"])
        row("J1 set.ai alone (the administrator): it says the AI is off and lists the four providers with their details, a [ ] each, none selected, no key set",
            any("none (the AI is off)" in ln for ln in out) and sum(1 for ln in out if "[ ]" in ln) == 4 and any("https://127.0.0.1:%d/v1/messages" % fm.port in ln for ln in out)
            and sum(1 for ln in out if "key: (not set)" in ln) == 4, repr(out[:14]))
        out = q3.adm(["set.ai provider openai"])
        new = fg.audit_new(a0)
        row("J2 set.ai provider openai: 11611, ai.conf holds provider=openai, one audit line 'set.ai provider=openai'", msg(11611, "openai") in out and "provider=openai" in conf_lines(box)
            and new is not None and re.search(r"set\.ai provider=openai$", new, re.M) is not None, repr((out[-3:], conf_lines(box), new)))
        before = list(conf_lines(box))
        out = q3.adm(["set.ai provider martian"])
        row("J3 a provider that is none of the four: 11610, ai.conf unchanged", msg(11610, "martian") in out and conf_lines(box) == before, repr(out[-3:]))
        out = q3.adm(["set.ai provider"])
        row("J4 set.ai provider with no name: the usage (11609)", msg(11609) in out, repr(out[-3:]))
        a1 = fg.audit_off()
        out = q3.adm(["set.ai model openai gpt-test"])
        new = fg.audit_new(a1)
        row("J5 set.ai model openai gpt-test: 11613, model.openai in ai.conf, audit 'set.ai model provider=openai model=gpt-test'", msg(11613, "openai", "gpt-test") in out and "model.openai=gpt-test" in conf_lines(box)
            and new is not None and re.search(r"set\.ai model provider=openai model=gpt-test$", new, re.M) is not None, repr((out[-3:], new)))
        a2 = fg.audit_off()
        before = list(conf_lines(box))
        out = q3.adm(["set.ai model openai x;y", "set.ai model openai x$y", "set.ai model openai x=y"])
        new = fg.audit_new(a2) or ""
        row("J6 a word with a character a command line must not carry (; $ =) is refused with 11622 and nothing is changed or audited", sum(1 for ln in out if "has a character that is not allowed here" in ln) == 3
            and conf_lines(box) == before and "set.ai" not in new, repr((out, new)))
        a3 = fg.audit_off()
        url = "https://127.0.0.1:%d/v1/chat/completions" % fm.port
        out = q3.adm(["set.ai custom MyLLM %s openai bearer - max_tokens" % url])
        new = fg.audit_new(a3) or ""
        c = conf_lines(box)
        row("J7 set.ai custom: 11617 names the host, ai.conf holds the whole connection, and the audit line has the host and NOT the URL", msg(11617, "MyLLM", "127.0.0.1:%d" % fm.port) in out
            and ("custom.url=" + url) in c and "custom.auth=bearer" in c and re.search(r"set\.ai custom name=MyLLM host=127\.0\.0\.1:%d$" % fm.port, new, re.M) is not None and "/v1/chat/completions" not in new, repr((out[-3:], new)))
        before = list(conf_lines(box))
        out = q3.adm(["set.ai custom Bad http://127.0.0.1/v1 openai bearer - max_tokens"])
        row("J8 custom with an http URL: the helper refuses (badconf) and SD says so with 11608; ai.conf is unchanged", any(ln.startswith("The AI helper refused: badconf (") for ln in out) and conf_lines(box) == before, repr(out[-3:]))
        out = q3.adm(["set.ai ca " + ca, "set.ai limit tokens-day 5000", "set.ai limit tokens-day lots"])
        c = conf_lines(box)
        row("J9 set.ai ca <file>: 11619 and ca-file in ai.conf; set.ai limit tokens-day 5000: 11621 and limit.tokens-day=5000; a limit that is no number: refused (badreq)",
            msg(11619, ca) in out and ("ca-file=" + ca) in c and msg(11621, "tokens-day", "5000") in out and "limit.tokens-day=5000" in c and any(ln.startswith("The AI helper refused: badreq") for ln in out), repr(out[-5:]))
        out = q3.adm(["set.ai limit tokens-day 100000", "set.ai model openai -"])
        row("J10 a limit set back, and a model cleared with -: 11621 and 11614, the model line is gone from ai.conf", msg(11614, "openai") in out and "model.openai=gpt-test" not in conf_lines(box), repr(out[-3:]))
        out = q3.adm(["set.ai provider custom", "set.ai custom clear"])
        row("J11 custom is selected, then 'set.ai custom clear' is refused (the helper: badreq) because it is the selected provider; its connection stays",
            msg(11611, "custom") in out and any(ln.startswith("The AI helper refused: badreq") for ln in out) and any(l.startswith("custom.url=") for l in conf_lines(box)), repr(out[-4:]))
        out = q3.adm(["set.ai provider anthropic", "set.ai custom clear"])
        row("J12 with another provider selected, set.ai custom clear works (11618) and no custom.* line is left", msg(11618) in out and not any(l.startswith("custom.") for l in conf_lines(box)), repr(out[-3:]))
        out = q3.adm(["set.ai provider none"])
        row("J13 set.ai provider none: 11612 (the AI is off for every account) and provider= is empty", msg(11612) in out and "provider=" in conf_lines(box), repr(out[-3:]))
        os.environ["SD_AI_CTL"] = os.path.join(box, "ai", "no-such-client")
        out = q3.adm(["set.ai"])
        row("J14 the client is not there: 11607 (the helper could not be reached), not a traceback or a silence", msg(11607) in out, repr(out[-3:]))
        os.environ["SD_AI_CTL"] = ctl
        runner.terminate()
        runner.wait(timeout=10)
        out = q3.adm(["set.ai"])
        row("J15 the helper is not running: 11607", msg(11607) in out, repr(out[-3:]))
        runner = start_runner(box, providers, ca)
        out = q3.adm(["set.ai provider openai", "set.ai model openai gpt-test"])
        pty_key_rows(box, fm)
        out = q3.adm(["set.ai key openai clear"])
        row("J20 set.ai key openai clear: 11616 and the key file is gone", msg(11616, "openai") in out and not os.path.exists(os.path.join(box, "ai", "state", "keys", "openai")), repr(out[-3:]))
        out = q3.adm(["set.ai"])
        row("J21 set.ai shows no key set for any provider again, and still never shows the key", not any("key: set" in ln for ln in out) and sum(1 for ln in out if "key: (not set)" in ln) == 4
            and not any(KEY in ln for ln in out), repr(out[:12]))
    finally:
        try:
            runner.terminate()
            runner.wait(timeout=10)
        except Exception:
            pass
        fm.stop()
        os.environ.pop("SD_AI_SOCKET", None)
        os.environ.pop("SD_AI_CTL", None)


def pty_key_rows(box, fm):
    """set.ai key openai on a pseudo-terminal: the client asks, nothing typed is shown, SD never holds the key."""
    say("\n  [pty] set.ai key openai in an administrator's session on a pseudo-terminal")
    kp = os.path.join(box, "ai", "state", "keys", "openai")
    if os.path.exists(kp):
        os.remove(kp)
    a0 = fg.audit_off()
    s = PtySession([q3.SD], q3.SYS, q3.env(True), 140, 43)
    s.settle(2.5)
    s.type("set.ai key openai\r", idle=2.5)
    scr = "\n".join(l.rstrip() for l in s.screen.lines())
    row("J16 the prompt is the client's: 'Key for openai (not shown):' is on the screen, from sd-ai-ctl and not from SD", "Key for openai (not shown):" in scr, scr[-300:])
    s.type(KEY[:6], idle=0.6)
    scr2 = "\n".join(l.rstrip() for l in s.screen.lines())
    row("J17 what is typed at the prompt is not shown (the first six characters of the key are not on the screen)", KEY[:6] not in scr2, scr2[-300:])
    s.type(KEY[6:] + "\r", idle=3.0)
    scr3 = "\n".join(l.rstrip() for l in s.screen.lines())
    s.finish()
    new = fg.audit_new(a0) or ""
    row("J18 after Enter SD says 11615 ('The key for openai is set'), and the key is on no screen line", msg(11615, "openai") in scr3 and KEY not in scr3, scr3[-400:])
    row("J19 the key is in the helper's key file (mode 0600) and in NO audit line; the audit line 'set.ai key set provider=openai' is there", os.path.exists(kp) and open(kp).read().strip() == KEY
        and (os.stat(kp).st_mode & 0o777) == 0o600 and KEY not in new and re.search(r"set\.ai key set provider=openai$", new, re.M) is not None, repr((os.path.exists(kp), new)))
    out = q3.adm(["set.ai"])
    row("J19b set.ai now lists a key set for openai (the listing says so; it never shows the key)", any("key: set" in ln for ln in out) and not any(KEY in ln for ln in out), repr(out[:12]))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    mutant = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mutant=")), None)
    if len(args) != 1 or (mutant is not None and mutant not in MUTANTS):
        q3.bail("usage: sandbox-aigate.py <dir> [--build] [--mutant=%s]" % "|".join(MUTANTS))
    q3.BOX = os.path.abspath(args[0])
    q3.SYS = os.path.join(q3.BOX, "sys")
    q3.SD = os.path.join(q3.SYS, "bin", "sd")
    say("sandbox-aigate: sandbox %s" % q3.BOX)
    say("sandbox-aigate: tree    %s" % TREE)
    say("sandbox-aigate: person  %s (whoever runs this: the helper's runner makes them the administrator, and the real helper's dry run only accepts a user that exists)" % ME)
    if "--build" in sys.argv:
        if os.path.exists(q3.BOX) and os.listdir(q3.BOX):
            q3.bail("%s is not empty" % q3.BOX)
        r = subprocess.run([sys.executable, q3.TOOL, q3.BOX, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            q3.bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-aigate: built, bootstrap passed")
    elif not os.path.isfile(q3.SD):
        q3.bail("%s holds no built sandbox (use --build, or point it at one)" % q3.BOX)
    subprocess.run([sys.executable, q3.TOOL, q3.BOX, "start"], capture_output=True, text=True, errors="replace", timeout=120)
    os.makedirs(os.path.join(q3.BOX, "grp"), exist_ok=True)
    shim = os.path.join(q3.BOX, "grp", "elevate-shim")
    put(shim, fg.SHIM % {"box": q3.BOX, "elevate": os.path.join(HERE, "sd-elevate")})
    os.chmod(shim, 0o755)
    os.makedirs(os.path.join(q3.BOX, "grp", "fakebin"), exist_ok=True)
    getent = os.path.join(q3.BOX, "grp", "fakebin", "getent")
    put(getent, fg.GETENT % {"box": q3.BOX})
    os.chmod(getent, 0o755)
    put(os.path.join(q3.BOX, "grp", "calls.log"), "")
    try:
        say("\n--- preparation: a CPROC that is not the install build, the fixture account, the patched modifya ---")
        q3.prepare()
        put(os.path.join(q3.SYS, "accounts", ACCT), "\n".join([os.path.join(q3.BOX, "user_accounts", ACCT), "", "sdu_" + ME, "", "", "", "no", "no"]) + "\n")
        fg.patch_modifya(None)
        if mutant is not None:
            old, new, _kills = MUTANTS[mutant]
            path = os.path.join(q3.SYS, "gpl.bp", "modifya")
            src = open(path, encoding="utf-8", errors="replace").read()
            if src.count(old) != 1:
                q3.bail("mutant %s: the text to change is found %d times, not once" % (mutant, src.count(old)))
            put(path, src.replace(old, new))
            out = q3.adm(["BASIC gpl.bp modifya"], internal=True)
            if not has(out, r"^Compiled 1 program\(s\) with no errors"):
                q3.bail("the mutated modifya did not compile:\n" + "\n".join(out[-6:]))
            say("sandbox-aigate: MUTANT %s: the rows that must fail, and nothing else: %s" % (mutant, ", ".join(MUTANTS[mutant][2])))
        real = subprocess.run(["id", "-nG", ME], capture_output=True, text=True).stdout.split()
        if "sdaiusers" in real and "sdusers" in real:
            q3.bail("%s is really in sdusers AND sdaiusers, so a case could pass by reading /etc/group instead of the scratch file" % ME)
        part1()
        if mutant is None:
            part2()
    finally:
        subprocess.run([sys.executable, q3.TOOL, q3.BOX, "stop"], capture_output=True, text=True, errors="replace", timeout=120)
    say("\nsandbox-aigate: %d passed, %d failed" % (q3.passed, q3.failed))
    if mutant is not None:
        want = sorted(set(MUTANTS[mutant][2]))
        got = sorted({re.match(r"I\d+", i).group(0) for i in FAILED_IDS if re.match(r"I\d+", i)})
        ok = want == got
        say("sandbox-aigate: MUTANT %s: the cases that failed are %s; they had to be exactly %s -> %s" % (mutant, got, want, "KILLED BY ITS OWN ROWS" if ok else "NOT AS EXPECTED"))
        return 0 if ok else 1
    return 1 if q3.failed else 0


if __name__ == "__main__":
    sys.exit(main())
