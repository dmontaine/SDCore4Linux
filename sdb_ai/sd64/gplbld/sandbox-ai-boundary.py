#!/usr/bin/env python3
#
# sandbox-ai-boundary.py - S.97 stage 0 (1 Nov 2026): THE AI BOUNDARY, on a private SD, the same rows for EVERY provider.  No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-ai-boundary.py <dir> --build
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Use --build: the programs under test
# are the ones the build compiled.  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# THE RULE (the owner, 1 Nov 2026; CLAUDE.md "THE AI BOUNDARY"): the AI field never reaches the C and GPL.BP code or any other system information, and no question about SD's own code or
# build is taken to the AI from inside SD, the administrator included - whichever provider is set up.  Two things are enforced in $tk_ai 'ask' before any preview is built and before any
# provider is addressed: the ORIGIN of the text an app puts in a request ($tk_aiwall 'origin': a text of SD's own files is never sent, nor one whose origin cannot be told) and a SCREEN on
# the TYPED request ($tk_aiwall 'request': the names of the system's code).  The screen is a screen, not a wall: a question that names none passes.
#
# WHAT RUNS.  The real AI helper (ai-runner.py, as systemd would run it) and the FAKE provider (fakemodel.py), the shipped provider table read with every provider's address pointed at the fake.
# For EACH of anthropic, openai, google, deepseek and custom the helper is set up for that provider (provider, model, key) and the same rows run:
#   P1  CONTROL: `ai hello` in an ordinary account reaches the fake ONCE, at that provider's own path and with that provider's own way of sending the key (so "for every provider" is not a label)
#   P2  `ai how does gpl.bp compile programs` is refused with message 11941; the fake saw NOTHING; no preview; one audit line `ai refused why=request ...` and no word of the request in it
#   P3  the IDE on a record of `syscom` (the file the account's VOC points at inside the system directory), a request in the AI line: refused with 11940, no preview, the fake saw nothing
#   P4  SED on the same record, Tools > Ask the AI: the same
# Once: the IDE on the account's own record DOES show the preview (the wall does not block a person's own work); a typed request naming gplsrc in the IDE's AI line is refused with 11941; and a
# probe program (an $internal subroutine in the sandbox) puts a table of origins and of typed requests to $tk_aiwall itself, with the real kernel's path test: SD's own files by record, by path, by
# `..`, by a link out of an account and by a directory called gplsrc are 'system'; an account's own record and a user's C file are not; an origin of no known kind, a missing file and a relative path
# are 'unknown'; every request that names the system's code is refused and a list of questions that merely contain a word of it (a kernel panic, a variable k$) are not.
# NOT HELD: the debugger's AI line (its source origin is a path: the probe holds the path rule; the debugger itself is sandbox-ai-apps.py's), /etc/sd.conf (the sandbox has none), a real provider,
# the administrator's own IDE session (the probe runs as the administrator; the ordinary account's `syscom` is the end-to-end row).
import importlib.util
import json
import os
import re
import shutil
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


aa = _load("sandbox_ai_apps_for_boundary", "sandbox-ai-apps.py")        # the SED and IDE drivers; it loads sandbox-ai-ide.py as aa.ai
ai = aa.ai
ids, gt = ai.ids, ai.gt
import fakemodel  # noqa: E402

say = ids.say
RET, ESC = ids.RET, ids.ESC
PROVIDERS = ("anthropic", "openai", "google", "deepseek", "custom")
PATHS = {"anthropic": "/v1/messages", "openai": "/v1/chat/completions", "google": "/v1beta/openai/chat/completions", "deepseek": "/chat/completions", "custom": "/v1/chat/completions"}
FAILED = []


def row(rid, name, ok, detail=""):
    ai.arow(rid, name, ok, detail)
    if not ok:
        FAILED.append(rid)


def nreq():
    return len(ai.STATE["fm"].log)


def setup_boundary():
    """The helper and the fake, with EVERY shipped provider's address pointed at the fake (sandbox-ai-ide.py's set-up maps only three of the four)."""
    b = ai.box()
    shutil.rmtree(os.path.join(b, "ai"), ignore_errors=True)
    for sub in ("state/keys", "state/state", "pki"):
        os.makedirs(os.path.join(b, "ai", sub))
    pki = fakemodel.make_pki(os.path.join(b, "ai", "pki"))
    fm = fakemodel.FakeModel(pki).start()
    providers = os.path.join(b, "ai", "ai-providers")
    text = open(os.path.join(HERE, "ai-providers")).read()
    for old, new in (("https://api.anthropic.com/v1/messages", "https://127.0.0.1:%d/v1/messages" % fm.port),
                     ("https://api.openai.com/v1/chat/completions", "https://127.0.0.1:%d/v1/chat/completions" % fm.port),
                     ("https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", "https://127.0.0.1:%d/v1beta/openai/chat/completions" % fm.port),
                     ("https://api.deepseek.com/chat/completions", "https://127.0.0.1:%d/chat/completions" % fm.port)):
        if old not in text:
            ids.bail("the provider table has no %s: the suite and the table disagree" % old)
        text = text.replace(old, new)
    ai.put(providers, text)
    ai.STATE.update(fm=fm, pki=pki, providers=providers, ca=os.path.join(pki, "ca.crt"))
    ai.start_runner()
    os.environ["SD_AI_SOCKET"] = os.path.join(b, "ai", "sock")
    os.environ["SD_AI_CTL"] = os.path.join(HERE, "sd-ai-ctl")


def configure_provider(p):
    port = ai.STATE["fm"].port
    cmds = ["set.ai ca " + ai.STATE["ca"], "set.ai limit requests-hour 1000"]
    if p == "custom":
        cmds.append("set.ai custom MyLLM https://127.0.0.1:%d/v1/chat/completions openai bearer - max_tokens" % port)
    cmds += ["set.ai provider " + p, "set.ai model %s %s" % (p, ai.MODEL)]
    out = ai.admin(*cmds)
    kp = os.path.join(ai.box(), "ai", "state", "keys", p)
    ai.put(kp, ai.KEY + "\n")
    os.chmod(kp, 0o600)
    return out


def verb(*cmds):
    """an ordinary session of the fixture account: the lines it printed"""
    return gt.plain(ai.ACC, list(cmds))


def refusal_on_screen(e, n, *args):
    """the message n is on the screen (cut at the first 60 characters: a status row cuts a long one) and the preview's buttons are not"""
    T = e.text()
    return ai.msg(n, *args)[:60] in T and "[ Send ]" not in T and "This will be sent to" not in T


def sec_provider(p):
    say("\n--- the boundary with the provider set to %s" % p)
    out = configure_provider(p)
    fm = ai.STATE["fm"]
    # P1 the control: the verb reaches THIS provider, once, at its path
    n0 = nreq()
    lines = verb("ai hello", "y")
    n1 = nreq()
    log = fm.log[n0:] if n1 > n0 else []
    path = log[0]["path"] if log else ""
    hdr = log[0]["headers"] if log else {}
    key_ok = ((hdr.get("x-api-key") == ai.KEY) if p == "anthropic" else (hdr.get("authorization") == "Bearer " + ai.KEY))
    row("P1." + p, "%s: CONTROL, `ai hello` reaches the fake once, at the provider's own path %s and with its own way of sending the key" % (p, PATHS[p]),
        n1 - n0 == 1 and path.startswith(PATHS[p]) and key_ok, repr((n1 - n0, path, sorted(hdr)[:6], lines[-4:])))
    # P2 the screen on the typed request
    a0 = ai.audit_off()
    n0 = nreq()
    lines = verb("ai how does gpl.bp compile programs")
    new = ai.audit_new(a0) or ""
    txt = "\n".join(lines)
    row("P2." + p, "%s: `ai how does gpl.bp compile programs` is refused (11941, naming gpl.bp), nothing is previewed, the fake saw nothing, one audit line that holds no word of the request" % p,
        ai.msg(11941, "gpl.bp")[:50] in txt and "This will be sent to" not in txt and nreq() == n0 and len(re.findall(r"ai refused why=request app=ai name=gpl\.bp$", new, re.M)) == 1
        and "compile programs" not in new, repr((lines[-3:], new[-200:], nreq() - n0)))
    # P3 the IDE on a record of SD's own files
    n0 = nreq()
    e = ai.AccIde(ai.box(), cmd="IDE syscom keys.h")
    row("P3a." + p, "%s: setup, the IDE has the record of `syscom` (keys.h) on its screen" % p, "keys" in e.text().lower() and "AI>" in e.text(), e.text()[:300])
    ai.ask(e, "what does this file define")
    e.s.settle(1.5)
    row("P3." + p, "%s: IDE, a record of syscom (inside the system directory): the request is refused with 11940, no preview, the fake saw nothing" % p,
        refusal_on_screen(e, 11940) and nreq() == n0, repr((e.text()[-500:], nreq() - n0)))
    e.end()
    # P4 SED on the same record
    n0 = nreq()
    e = ai.AccIde(ai.box(), cmd="SED syscom keys.h")
    T = aa.sed_ask(e, "what does this file define")
    e.s.settle(1.5)
    row("P4." + p, "%s: SED, the same record: refused with 11940, no preview, the fake saw nothing" % p, refusal_on_screen(e, 11940) and nreq() == n0, repr((e.text()[-500:], nreq() - n0)))
    e.end()


def sec_once():
    say("\n--- the wall does not block a person's own work, and the screen on the IDE's own AI line")
    configure_provider("anthropic")
    n0 = nreq()
    e = ai.ide(ai.OK_REC)
    ai.ask(e, "explain this program")
    e.s.settle(1.5)
    T = e.text()
    row("O1", "the IDE on the account's own record: the same request DOES show the preview (Send and Cancel) and nothing has gone yet", "This will be sent to" in T and "Send" in T and "Cancel" in T and nreq() == n0, repr((T[-300:], nreq() - n0)))
    e.keys(ESC)
    e.s.settle(1.0)
    row("O2", "Cancel sends nothing", nreq() == n0, repr(nreq() - n0))
    e.end()
    n0 = nreq()
    e = ai.ide(ai.OK_REC)
    ai.ask(e, "explain how op_sort.c reads gplsrc")
    e.s.settle(1.5)
    row("O3", "the IDE's AI line with a request that names the system's code: refused with 11941 before any preview, the fake saw nothing", refusal_on_screen(e, 11941, "gplsrc") and nreq() == n0,
        repr((e.text()[-400:], nreq() - n0)))
    e.end()
    n0 = nreq()
    e = aa.sed_open(ai.OK_REC)
    T = aa.sed_ask(e, "explain this program")
    e.s.settle(1.5)
    row("O4", "SED on the account's own record: the preview is shown (the wall does not block it)", "This will be sent to" in e.text() and nreq() == n0, repr((e.text()[-300:], nreq() - n0)))
    e.keys(ESC)
    e.end()


def bas(s):
    """a BASIC string literal that is safe for a quote in it"""
    return '"' + s.replace('"', '""') + '"'


def sec_probe():
    say("\n--- $tk_aiwall itself, with the real kernel's path test (a probe program run as the administrator)")
    b = ai.box()
    sysdir = ai.sysd()
    accdir = os.path.join(b, "user_accounts", ai.ACC)
    link = os.path.join(accdir, "zzlinksys")
    if os.path.lexists(link):
        os.remove(link)
    os.symlink(sysdir, link)
    own = os.path.join(accdir, "bp", ai.OK_REC)
    origins = [
        ("record-gplbp", "SD's own program file gpl.bp, by record", ["record", "gpl.bp", "tk_ai", "0"], "system"),
        ("record-syscom", "a record of syscom, by record", ["record", "syscom", "keys.h", "0"], "system"),
        ("record-dict", "an item of the dictionary of a system file, by record", ["record", "voc", "@id", "1"], "system"),
        ("path-sys", "a path inside the system directory", ["path", "", os.path.join(sysdir, "gpl.bp", "tool_ai"), ""], "system"),
        ("path-dots", "a path that reaches the system directory through ..", ["path", "", os.path.join(accdir, "bp", "..", "..", "..", "sys", "gpl.bp", "tool_ai"), ""], "system"),
        ("path-link", "a path through a link out of the account into the system directory", ["path", "", os.path.join(link, "gpl.bp", "tool_ai"), ""], "system"),
        ("path-gplsrc", "a path with a directory called gplsrc on the way, wherever it is", ["path", "", "/tmp/zzx/gplsrc/op_x.c", ""], "system"),
        ("path-own", "the account's own record, by path: allowed", ["path", "", own, ""], ""),
        ("path-userc", "a user's own C file outside the system directory: allowed (the rule is where a file is, not what it is called)", ["path", "", "/tmp/zzx.c", ""], ""),
        ("kind-none", "an app that sends no text of a file says none: allowed", ["none"], ""),
        ("kind-untitled", "a buffer that is not yet a record: allowed", ["untitled"], ""),
        ("kind-odd", "a kind that is none of the known: unknown", ["weird", "a", "b", "0"], "unknown"),
        ("rec-nofile", "a record of a file that cannot be opened: unknown", ["record", "zznosuchfile", "x", "0"], "unknown"),
        ("path-rel", "a relative path: unknown", ["path", "", "bp/x", ""], "unknown"),
        ("rec-noid", "a record with no id: unknown", ["record", "bp", "", "0"], "unknown"),
    ]
    reqs = [
        ("r-gplbp", "GPL.BP in capitals", "Tell me about GPL.BP", "gpl.bp"),
        ("r-gplsrc", "gplsrc", "explain the gplsrc directory", "gplsrc"),
        ("r-gplbld", "gplbld", "what is in gplbld", "gplbld"),
        ("r-opc", "a kernel file op_name.c", "how does op_sort.c work", "op_*.c"),
        ("r-kkey", "a key of the kernel's private interface", "what is K$AUDIT for", "k$"),
        ("r-internal", "$internal", "what does $internal do", "$internal"),
        ("r-bcomp", "the compiler's own program", "show me bcomp", "bcomp"),
        ("r-make", "the build", "edit the Makefile", "makefile"),
        ("r-devbuild", "the developer build flag", "turn on SD_DEV_BUILD", "sd_dev_build"),
        ("r-source", "a phrase about SD's source", "where is SD's source", "sd's source"),
        ("r-kcode", "a phrase about the kernel", "change the kernel code", "kernel code"),
        ("r-okpanic", "CONTROL: a kernel panic is not SD's kernel", "my machine had a kernel panic, what do I do", ""),
        ("r-oksort", "CONTROL: an ordinary question", "how do I sort a file by customer name", ""),
        ("r-okop", "CONTROL: op.c has no underscore", "my program op.c prints a total", ""),
        ("r-okk", "CONTROL: k$ followed by a space is not a kernel key", "I called a variable k$ in my program", ""),
        ("r-okprog", "CONTROL: gpl on its own is a word", "create a file called gpl", ""),
    ]
    prog = ["$internal", "program zzaw"]
    for rid, label, parts, want in origins:
        arr = " : @vm : ".join(bas(x) for x in parts)
        prog.append("   org = %s" % arr)
        prog.append("   call $tk_aiwall('origin', org, why)")
        prog.append("   crt 'W[%s][' : why : ']'" % rid)
    for rid, label, text, want in reqs:
        prog.append("   call $tk_aiwall('request', %s, why)" % bas(text))
        prog.append("   crt 'W[%s][' : why : ']'" % rid)
    prog.append("end")
    ai.put(os.path.join(ai.sysd(), "gpl.bp", "zzaw"), "\n".join(prog) + "\n")
    out = ai.admin("BASIC gpl.bp zzaw")
    if not re.search(r"^Compiled 1 program\(s\) with no errors", out, re.M):
        ids.bail("the probe did not compile:\n" + out[-600:])
    out = ai.admin("RUN gpl.bp zzaw")
    got = dict(re.findall(r"^W\[([\w-]+)\]\[(.*)\]\s*$", out, re.M))
    row("W0", "NULL CASE: the probe answered every row (%d origins, %d requests)" % (len(origins), len(reqs)), len(got) == len(origins) + len(reqs), "%d answers: %r" % (len(got), out[-400:]))
    for rid, label, parts, want in origins:
        row("W." + rid, "origin: " + label, got.get(rid) == want, "got %r want %r" % (got.get(rid), want))
    for rid, label, text, want in reqs:
        row("W." + rid, "request: " + label, got.get(rid) == want, "got %r want %r" % (got.get(rid), want))
    os.remove(link)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        ids.bail("usage: sandbox-ai-boundary.py <dir> --build")
    ai.STATE["box"] = os.path.abspath(args[0])
    b = ai.box()
    say("sandbox-ai-boundary: sandbox %s" % b)
    if "--build" in sys.argv:
        if os.path.exists(b) and os.listdir(b):
            ids.bail("%s is not empty" % b)
        r = subprocess.run([sys.executable, ids.TOOL, b, "all"], capture_output=True, text=True, errors="replace", timeout=1800)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            ids.bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-ai-boundary: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(ai.sysd(), "bin", "sd")):
        ids.bail("%s holds no built sandbox (use --build)" % b)
    subprocess.run([sys.executable, ids.TOOL, b, "start"], capture_output=True, text=True, errors="replace", timeout=120)
    gt.BOX, gt.SYS, gt.SD = b, ai.sysd(), os.path.join(ai.sysd(), "bin", "sd")
    try:
        gt.prepare()
        gt.FIXTURES[ai.ACC] = ("no", "no")
        gt.build_account(ai.ACC)
        flags = gt.flags(gt.plain(ai.ACC, ["zzkf"]))
        if flags is None or flags[0] != "0":
            ids.bail("the first ordinary session is not shown to be one (admin=%r), so no row below can be believed" % (flags,))
        setup_boundary()
        ai.make_records()
        for p in PROVIDERS:
            sec_provider(p)
        sec_once()
        sec_probe()
    finally:
        ai.stop_runner()
        if "fm" in ai.STATE:
            ai.STATE["fm"].stop()
        os.environ.pop("SD_AI_SOCKET", None)
        os.environ.pop("SD_AI_CTL", None)
        subprocess.run([sys.executable, ids.TOOL, b, "stop"], capture_output=True, text=True, errors="replace", timeout=120)
    say("\nsandbox-ai-boundary: %d passed, %d failed" % (ids.passed, ids.failed))
    return 0 if ids.failed == 0 and ids.passed > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
