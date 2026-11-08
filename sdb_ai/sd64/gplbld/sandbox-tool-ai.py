#!/usr/bin/env python3
#
# sandbox-tool-ai.py - the AI choice page, TOOL.AI, driven on a PSEUDO-TERMINAL on a private SD (S.69 step 2, group D; plan .claude/plan-ai-step2.md).  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-tool-ai.py <dir> [--build] [--mutant=NAME]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent).  Exit 0 every row passed, 1 a row failed, 2 it could not
# run.  With --mutant=NAME one change is made to the SANDBOX'S OWN COPY of the page and exit 0 means the rows that had to fail failed and no others (MUTANTS below).
#
# WHAT RUNS.  The administrator's session (SDTEST_ADMIN, the person who runs this suite) opens TOOL.AI on a 140 by 43 terminal.  The AI helper is the real one (gplbld/sd-ai, served
# by ai-runner.py as systemd would serve it, with this person as its administrator), the provider is the fake (gplbld/fakemodel.py) and the shipped provider table is read with
# the fake's address in place of the real ones.  SET.AI finds the helper's client through SD_AI_CTL and the helper through SD_AI_SOCKET.  The account gate is membership of the
# Linux group sdaiusers, which a sandbox cannot change: modify.account runs with the helper stood in by a script that edits a SCRATCH group file and the group lookups read that file
# (sandbox-filesgrp.py's method, as sandbox-aigate.py uses it), and $tk_gates reads the same file.  The register holds three USER accounts (zzai1 for this person, zzai2 and the
# suspended zzai3 for others), a GROUP account that must not be listed, and the fixtures of sandbox-home.py, which are not USER accounts and are not listed.
#
# THE INSTRUMENT.  Every outcome is read from the DISK or the AUDIT TRAIL, not from what the page said: ai.conf, the key file, the scratch group file, the audit file.  A row that
# says "nothing was run" is judged by those, and the key sentinel is looked for in the whole byte stream the terminal received.
#
#   T0-T2   an ordinary account has no tool.ai; the page: four boxes, four named providers (Anthropic, OpenAI, Google, DeepSeek) each with its shipped address and default model, and
#           Custom not filled in, no key, none checked, the summary says the AI is off; a [?] at the end of the Provider and the Accounts boxes (1 Nov 26: Google and the default models)
#   T7a-T7d M on a model in use names it in the prompt; a dash goes back to the default and ai.conf loses the setting; naming the default already in use changes nothing
#   T3-T4   Enter on a provider shows the command and its effect and Cancel runs nothing; Run asks for the provider's NAME, a wrong name runs nothing, the right one checks it
#           (the check box moves, ai.conf holds it, one audit line)
#   T5-T7   M: the model (the sentence, the effect, ai.conf); a model name with a character it may not have runs nothing; capitals and a colon get through $tk_runx
#   T8-T9   K: the terminal goes to the helper's prompt, nothing typed there is shown, the key file is 0600 and holds it, the page shows it set and the summary says the provider
#           can be used; the key is in no screen, no byte of the terminal's output and no audit line; X removes it
#   T10-T14 C: the Custom row (a refused address first, then the whole connection and the name typed), selecting Custom moves the check, deselecting turns the AI off, D is
#           refused by the helper while Custom is in use and works after
#   T15-T16 L: a limit (and a name that is none); A: the file of certificate authorities, with the word ca typed
#   T17-T19 Accounts: only USER accounts, their gates read from the scratch group file; Enter asks for the name before turning a gate ON and runs modify.account; OFF needs none;
#           the Provider keys are refused in this box
#   T30-T38 (S.160, 7 Nov 26; --only=context runs them alone) T, the standing text: the box shows the shipped default, Esc changes nothing, Save shows a Run / Cancel box and Cancel
#           writes nothing, Run keeps the edited text in the helper's file with one audit line, a text naming gpl.bp is refused by set.ai, the ai verb's preview shows nothing of
#           the text and what arrives at the provider carries it, Shipped default removes the administrator's file
#   T20-T22 the helper not running (words, no crash); a window under 140 by 43 gets no page
# NOT HELD: the installer, the real systemd socket, a real provider, the real /etc/group and sudo, the help text itself (test-help-units.py reads it as text), the end of input during a
# dialog.
import importlib.util
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


sh = _load("sandbox_home_for_toolai", "sandbox-home.py")
ag = _load("sandbox_aigate_for_toolai", "sandbox-aigate.py")
fg, q3 = ag.fg, ag.q3
import fakemodel  # noqa: E402

say, row, bail, has, dump, adm, H, g = sh.say, sh.row, sh.bail, sh.has, sh.dump, sh.adm, sh.H, sh.g
sh.KEYS["f1"] = "\x1b[[A"
ME = ag.ME
KEY = ag.KEY
FAILED_IDS = []
MODEL = "claude-test"
STATE = {}


def arow(rid, name, ok, detail=""):
    """A row with an id (T3 ...): the mutant mode compares the ids that failed with the ids that had to."""
    row("%s %s" % (rid, name), ok, detail)
    if not ok:
        FAILED_IDS.append(rid)


MUTANTS = {
    # name: (old text of the sandbox's tool_ai, new text, the row ids that must fail and no others)
    "no-confirm": ("   call $tk_confirm(sent, el, typed, res, cmsg)\n   if res = 'run' then\n      if use.x then", "   res = 'run'\n   if res = 'run' then\n      if use.x then", ["T3", "T4", "T18"]),
    "no-typed-provider": ("      sent = 'set.ai provider ' : p\n      typed = p\n", "      sent = 'set.ai provider ' : p\n      typed = ''\n", ["T4"]),
    "no-typed-gate": ("      typed = an.name\n      lpid = sel", "      typed = ''\n      lpid = sel", ["T18"]),
}
MUTANT_SECTIONS = ("provider", "accounts")


def box():
    return sh.BOX


def conf():
    return ag.conf_lines(box())


def keyfile(p):
    return os.path.join(box(), "ai", "state", "keys", p)


def page(cols=140, rows=43):
    h = H(admin=True, cols=cols, rows=rows)
    h.typed("tool.ai\r", idle=3.0)
    return h


def st(h):
    return h.line(40)


def cell(h, r):
    """The text of a row inside the boxes: from column 3, without the border at column 139 and without the padding."""
    return h.line(r)[3:138].rstrip()


def setup_ai():
    """The helper, the fake provider, the scratch group file and the patched programs; the accounts."""
    b = box()
    q3.BOX, q3.SYS, q3.SD = b, sh.SYS, os.path.join(sh.SYS, "bin", "sd")
    shutil.rmtree(os.path.join(b, "ai"), ignore_errors=True)
    for sub in ("state/keys", "state/state", "pki"):
        os.makedirs(os.path.join(b, "ai", sub))
    pki = fakemodel.make_pki(os.path.join(b, "ai", "pki"))
    fm = fakemodel.FakeModel(pki).start()
    providers = os.path.join(b, "ai", "ai-providers")
    text = open(os.path.join(HERE, "ai-providers")).read()
    for old, new in (("https://api.anthropic.com/v1/messages", "https://127.0.0.1:%d/v1/messages" % fm.port), ("https://api.openai.com/v1/chat/completions", "https://127.0.0.1:%d/v1/chat/completions" % fm.port),
                     ("https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", "https://127.0.0.1:%d/v1beta/openai/chat/completions" % fm.port),
                     ("https://api.deepseek.com/chat/completions", "https://127.0.0.1:%d/chat/completions" % fm.port)):
        text = text.replace(old, new)
    g.put(providers, text)
    STATE.update(fm=fm, pki=pki, providers=providers, ca=os.path.join(pki, "ca.crt"), port=fm.port)
    STATE["runner"] = ag.start_runner(b, providers, STATE["ca"])
    os.environ["SD_AI_SOCKET"] = os.path.join(b, "ai", "sock")
    os.environ["SD_AI_CTL"] = os.path.join(HERE, "sd-ai-ctl")
    # the group lookups and the helper of modify.account, pointed at the scratch directory (sandbox-filesgrp.py's method)
    os.makedirs(os.path.join(b, "grp", "fakebin"), exist_ok=True)
    shim = os.path.join(b, "grp", "elevate-shim")
    g.put(shim, fg.SHIM % {"box": b, "elevate": os.path.join(HERE, "sd-elevate")})
    os.chmod(shim, 0o755)
    getent = os.path.join(b, "grp", "fakebin", "getent")
    g.put(getent, fg.GETENT % {"box": b})
    os.chmod(getent, 0o755)
    g.put(os.path.join(b, "grp", "calls.log"), "")
    ag.write_ai_group(False)
    fg.patch_modifya(None)
    src = open(os.path.join(TREE, "sdsys", "gpl.bp", "tk_gates"), encoding="utf-8", errors="replace").read()
    old = "deffun is_grp_member(user,group) calling '!is_grp_member'"
    if src.count(old) != 1:
        bail("the tree's tk_gates has its group lookup %d times, not once" % src.count(old))
    g.put(os.path.join(sh.SYS, "gpl.bp", "tk_gates"), src.replace(old, "deffun is_grp_member(user,group) calling '!zzgm'"))
    out = q3.adm(["BASIC gpl.bp tk_gates"], internal=True)
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("the patched tk_gates did not compile:\n" + "\n".join(out[-6:]))
    # the page of the tree (a mutant of an earlier run is not carried over)
    shutil.copyfile(os.path.join(TREE, "sdsys", "gpl.bp", "tool_ai"), os.path.join(sh.SYS, "gpl.bp", "tool_ai"))
    compile_page()
    # the accounts: three USER accounts and a GROUP account in the register
    for name, grp, susp in (("zzai1", "sdu_" + ME, ""), ("zzai2", "sdu_zzother2", ""), ("zzai3", "sdu_zzother3", "SUSPENDED"), ("zzaig", "sdg_zzaig", "")):
        path = os.path.join(b, "user_accounts", name)
        os.makedirs(path, exist_ok=True)
        g.put(os.path.join(sh.SYS, "accounts", name), "\n".join([path, "", grp, "", susp, "", "no", "no"]) + "\n")


def mutate(name):
    old, new, _kills = MUTANTS[name]
    path = os.path.join(sh.SYS, "gpl.bp", "tool_ai")
    src = open(path, encoding="utf-8", errors="replace").read()
    if src.count(old) != 1:
        bail("mutant %s: the text to change is found %d times, not once" % (name, src.count(old)))
    g.put(path, src.replace(old, new))


def compile_page():
    out = q3.adm(["BASIC gpl.bp tool_ai"], internal=True)
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("tool_ai did not compile in the sandbox:\n" + "\n".join(out[-8:]))


def provider_section():
    b = box()
    port = STATE["port"]
    say("\n--- the page, its first screen")
    out = g.plain("zzhd", ["tool.ai"])
    arow("T0", "an ordinary account cannot reach it: tool.ai is in SDSYS's VOC only", has(out, r"not in your VOC"), repr(out[:3]))
    a_open = fg.audit_off()
    h = page()
    T = h.text()
    if "What this means" not in T:
        dump(h)
        bail("tool.ai never drew its page, so no row below can be believed")
    arow("T0b", "opening the page writes one audit line, 'tool start app=tool.ai', and nothing else changes: ai.conf holds nothing yet", len(re.findall(r"tool start app=tool\.ai$", fg.audit_new(a_open) or "", re.M)) == 1
         and not any(l.startswith(("provider=", "model.", "custom.", "limit.", "ca-file=")) and not l == "provider=" for l in conf()), repr((fg.audit_new(a_open), conf())))
    arow("T1a", "the four boxes", all(w in T for w in ("AI provider - one for every account", "The row under the cursor", "Accounts that may use the AI", "What this means")), T[:400])
    urls = ("https://127.0.0.1:%d/v1/messages" % port, "https://127.0.0.1:%d/v1/chat/completions" % port, "https://127.0.0.1:%d/v1beta/openai/chat/completions" % port, "https://127.0.0.1:%d/chat/completions" % port)
    names = ("Anthropic", "OpenAI", "Google", "DeepSeek")
    DEFAULTS = re.findall(r"^model=(.*)$", open(os.path.join(HERE, "ai-providers")).read(), re.M)      # the shipped table's default models, in the order of the names
    STATE["defaults"] = DEFAULTS
    ok = len(DEFAULTS) == 4 and all(re.match(r"^\[ \] %s\s+%s\s+%s \(default\)\s+not set$" % (re.escape(nm), re.escape(u), re.escape(dm)), cell(h, 3 + i))
                                    for i, (nm, u, dm) in enumerate(zip(names, urls, DEFAULTS)))
    arow("T1b", "the four named providers (Anthropic, OpenAI, Google, DeepSeek) are filled in with their shipped address and their default model (marked default), no key, none checked", ok, repr([cell(h, r) for r in range(3, 8)]))
    arow("T1c", "the fifth row is Custom, not filled in, nothing checked", re.match(r"^\[ \] Custom\s+\(not filled in\)\s+\(not set\)\s+not set$", cell(h, 7)) is not None, repr(cell(h, 7)))
    arow("T1d", "the summary says the AI is off (no provider is selected)", h.line(9)[3:].startswith("The AI is OFF: no provider is selected."), repr(h.line(9)[3:80]))
    arow("T2", "a [?] at the end of the Provider box and of the Accounts box", h.line(2)[134:137] == "[?]" and h.line(25)[134:137] == "[?]", repr((h.line(2)[130:139], h.line(25)[130:139])))
    arow("T1e", "the row under the cursor is described: the Anthropic request layout, the x-api-key header and the version header", all(w in h.text() for w in ("anthropic  (the Messages API)", "x-api-key: <key>", "2023-06-01", "max_tokens")), h.text()[1500:2600])
    # ------------------------------------------------------------------------------------------ the mouse on the provider rows (8 Nov 26, Kimi's review: the hit box stopped one row short of Custom)
    hl = lambda r_: "r" in h.style(r_, 5)[2]             # the row under the cursor is drawn highlighted (reverse)
    h.click(10, 6)
    arow("T1f", "CONTROL: a click on the DeepSeek row (the fourth) puts the cursor there", hl(6) and not hl(3), repr([hl(r_) for r_ in range(3, 8)]))
    h.click(10, 7)
    arow("T1g", "a click on the Custom row (the fifth, the last) puts the cursor there", hl(7) and not hl(6), repr([hl(r_) for r_ in range(3, 8)]))
    h.click(10, 3)
    arow("T1h", "a click on the Anthropic row puts the cursor back on the first row", hl(3) and not hl(7), repr([hl(r_) for r_ in range(3, 8)]))
    # ------------------------------------------------------------------------------------------ select a provider
    say("\n--- Enter on a provider")
    a0 = fg.audit_off()
    h.key("enter", idle=1.4)
    T = h.text()
    arow("T3a", "Enter shows the command and its effect, says which default model it will ask, and warns that no key is set", "set.ai provider anthropic" in T and "will use Anthropic" in T
         and ("It will ask its default model, " + STATE["defaults"][0]) in re.sub(r"\s+", " ", T) and "No model is set for it yet" not in T and "No key is set for it yet" in T, T[-900:])
    h.key("esc", idle=1.0)
    arow("T3b", "Esc is Cancel: nothing was run (the status line says so), ai.conf holds no provider, no audit line", "nothing was run" in st(h) and not any(l.startswith("provider=") and l != "provider=" for l in conf())
         and "set.ai" not in (fg.audit_new(a0) or ""), repr((st(h), conf())))
    h.key("enter", idle=1.2)
    h.typed("r", idle=1.2)
    T = h.text()
    arow("T4a", "Run asks for the provider's NAME to be typed", "anthropic" in T and re.search(r"[Tt]ype", T) is not None, T[-400:])
    h.typed("nope\r", idle=1.5)
    arow("T4b", "a name that is not the provider's runs nothing", not any(l.startswith("provider=") and l != "provider=" for l in conf()) and h.line(3)[3:6] == "[ ]", repr((conf(), h.line(3)[3:20])))
    h.key("enter", idle=1.2)
    h.typed("r", idle=1.2)
    h.typed("anthropic\r", idle=2.0)
    new = fg.audit_new(a0) or ""
    arow("T4c", "the right name runs it: Anthropic is checked, ai.conf holds provider=anthropic, the audit trail has one 'set.ai provider=anthropic', and the page says what the verb said",
         h.line(3)[3:6] == "[x]" and "provider=anthropic" in conf() and len(re.findall(r"set\.ai provider=anthropic$", new, re.M)) == 1 and "The AI provider for every account is now anthropic" in st(h),
         repr((h.line(3)[3:20], conf(), new[-200:], st(h))))
    arow("T4d", "the summary says what is missing: only the key (the model is the default)", ("In use: Anthropic, model " + STATE["defaults"][0] + " (default), key not set.  It cannot be used until the key is set") in h.line(9), repr(h.line(9)[3:140]))
    if MUTANT_ONLY_PROVIDER_SELECT:
        h.key("ctrl-q", idle=1.0)
        h.end()
        return
    # ------------------------------------------------------------------------------------------ the model
    say("\n--- M: the model")
    h.typed("m", idle=1.2)
    T = h.text()
    arow("T5a", "M asks for the model name of the row under the cursor, naming the default in use", "Model for Anthropic (now " + STATE["defaults"][0] in re.sub(r"\s+", " ", T), T[-500:])
    h.typed(MODEL + "\r", idle=1.5)
    T = h.text()
    arow("T5b", "the sentence and its effect are shown before anything runs", "set.ai model anthropic " + MODEL in T and "will ask model " + MODEL in T, T[-700:])
    h.typed("r", idle=2.0)
    arow("T5c", "Run: ai.conf holds the model, the row shows it, the verb's own words are on the status line", ("model.anthropic=" + MODEL) in conf() and MODEL in h.line(3) and ("The model for anthropic is now " + MODEL) in st(h), repr((conf(), h.line(3)[3:100], st(h))))
    a1 = fg.audit_off()
    before = list(conf())
    h.typed("m", idle=1.0)
    h.typed("a;b\r", idle=1.5)
    arow("T6", "a model name with a semicolon is refused by the page (words), nothing is run, nothing is audited", "A model name has 1 to 80 letters" in st(h) and conf() == before and "set.ai" not in (fg.audit_new(a1) or ""),
         repr((st(h), fg.audit_new(a1))))
    h.key("down", idle=0.6)
    h.typed("m", idle=1.0)
    h.typed("GPT-Test:1\r", idle=1.5)
    h.typed("r", idle=2.0)
    arow("T7", "capitals and a colon in a model name go through $tk_runx (the OpenAI row)", "model.openai=GPT-Test:1" in conf() and "GPT-Test:1" in h.line(4), repr((conf(), h.line(4)[3:100], st(h))))
    h.typed("m", idle=1.0)
    arow("T7a", "M names the model in use in its prompt, and says a dash is the default", "Model for OpenAI (now GPT-Test:1; - = default)" in re.sub(r"\s+", " ", h.text()), h.text()[-500:])
    h.typed("-\r", idle=1.5)
    T = h.text()
    arow("T7b", "a dash says the model goes back to its default (the table's, named) and shows the sentence", "set.ai model openai -" in T and ("goes back to its default, " + STATE["defaults"][1]) in re.sub(r"\s+", " ", T), T[-700:])
    h.typed("r", idle=2.0)
    arow("T7c", "Run: the row shows the default again, marked default, and ai.conf no longer holds the administrator's model",
         (STATE["defaults"][1] + " (default)") in h.line(4) and "model.openai=GPT-Test:1" not in conf(), repr((h.line(4)[3:100], conf(), st(h))))
    h.key("down", idle=0.6)
    a4 = fg.audit_off()
    before = list(conf())
    h.typed("m", idle=1.0)
    h.typed(STATE["defaults"][2] + "\r", idle=1.5)
    arow("T7d", "M on the Google row, naming the default it already uses: the page says so and runs nothing",
         ("already uses its default model, " + STATE["defaults"][2]) in st(h) and conf() == before and "set.ai" not in (fg.audit_new(a4) or ""), repr((st(h), fg.audit_new(a4))))
    h.key("up", idle=0.6)
    h.key("up", idle=0.6)
    # ------------------------------------------------------------------------------------------ the key
    # S.170 (8 Nov 26; the owner: one dialog for the model and the key, the key shown as *): K is ONE form; the key goes to the helper through the hand-over file
    say("\n--- K: the key and the model in one form (S.170)")
    # the list of models is a real request to the fake provider, whose certificate only the test CA vouches for: set it first with the page's own A (T16 does it again later)
    h.typed("a", idle=1.0)
    h.typed(STATE["ca"] + "\r", idle=1.5)
    h.typed("r", idle=1.2)
    h.typed("ca\r", idle=2.0)
    if ("ca-file=" + STATE["ca"]) not in conf():
        bail("the test CA could not be set with A, so the list of models cannot be fetched: %r" % (conf(),))
    a2 = fg.audit_off()
    hdir = os.path.join(sh.SYS, "$aikey")
    h.typed("k", idle=1.4)
    T = h.text()
    arow("T8a", "K opens ONE form 'Key and model for Anthropic' with the model in use (claude-test) in its Model entry, a Key entry, and a hint naming the host the key goes to",
         "Key and model for Anthropic" in T and "claude-test" in T and "Key" in T and "127.0.0.1" in T, T[-900:])
    h.key("tab", idle=0.6)
    h.typed(KEY, idle=0.8)
    T = h.text()
    arow("T8b", "the key typed into the Key entry is shown as * and not as itself", KEY not in T and ("*" * 10) in T, T[-500:])
    h.typed("\r", idle=4.0)
    new = fg.audit_new(a2) or ""
    kp = keyfile("anthropic")
    arow("T8c", "Save: the form is gone, the page says the key is set and the model stays claude-test (the provider lists it, so the name was accepted)",
         "Key and model for" not in h.text() and "The key for Anthropic is set" in st(h) and "stays claude-test" in st(h), repr(st(h)))
    arow("T8d", "the hand-over file is gone and its directory is sdsys's alone (mode 0700)", not os.path.exists(os.path.join(hdir, "key")) and os.path.isdir(hdir) and (os.stat(hdir).st_mode & 0o777) == 0o700,
         repr((os.path.exists(os.path.join(hdir, "key")), oct(os.stat(hdir).st_mode) if os.path.isdir(hdir) else None)))
    arow("T9a", "back on the page: the row shows the key set, the summary no longer says it cannot be used", re.search(r"claude-test\s+set$", cell(h, 3)) is not None
         and "In use: Anthropic, model claude-test, key set" in h.line(9) and "cannot be used" not in h.line(9), repr((cell(h, 3), cell(h, 9))))
    arow("T9b", "the key file is the helper's: mode 0600, holds the key; the audit trail has 'set.ai key set provider=anthropic from=page' and no key", os.path.exists(kp) and open(kp).read().strip() == KEY
         and (os.stat(kp).st_mode & 0o777) == 0o600 and re.search(r"set\.ai key set provider=anthropic from=page$", new, re.M) is not None and KEY not in new, repr((os.path.exists(kp), new[-200:])))
    arow("T9c", "the key sentinel is in NO byte the terminal received, and on no screen line", KEY.encode() not in h.s.raw and KEY not in h.text(), "")
    a5 = fg.audit_off()
    before = list(conf())
    h.typed("k", idle=1.4)
    h.typed("\x15Claude-Test\r", idle=4.0)               # Ctrl-U empties the entry; the key left empty keeps the key now set
    TL = h.text().split("\n")
    T = re.sub(r"\s+", " ", h.text())
    seen = [l for l in TL if "list" in l or "Claude-Test" in l or "case-sensitive" in l]
    # the form wraps its message into the rows under the entries, beside the page's own boxes: the pieces are looked for, not one run of words
    arow("T8e", "a model the provider does not list (Claude-Test, the case wrong) is refused IN the form, which names the listed one; the key left empty is kept; nothing changed",
         any("does not list" in l for l in TL) and "Claude-Test" in T and "claude-test" in T and any("case-sensitive" in l for l in TL)
         and conf() == before and "set.ai model" not in (fg.audit_new(a5) or ""), repr(seen))
    h.key("esc", idle=1.2)
    arow("T8f", "Esc leaves the form: nothing was changed, the key is still there", "nothing was changed" in st(h) and os.path.exists(kp), repr(st(h)))
    # M with a key set: the provider's own list in a pick window (typing narrows it)
    h.typed("m", idle=3.0)
    T = h.text()
    arow("T8g", "M with the key set opens the list the provider gives ('Models Anthropic offers'), its names and the entry to type another",
         "Models Anthropic offers" in T and "fake-small" in T and "type a name" in T, repr([l for l in T.split("\n") if "Models" in l or "fake" in l or "type a" in l]))
    h.typed("small", idle=1.0)
    h.typed("\r", idle=1.5)
    T = h.text()
    arow("T8h", "typing 'small' and Enter picks fake-small: the sentence set.ai model anthropic fake-small is shown before it runs", "set.ai model anthropic fake-small" in T, T[-700:])
    h.typed("r", idle=2.5)
    arow("T8i", "Run: ai.conf holds model.anthropic=fake-small", "model.anthropic=fake-small" in conf(), repr(conf()))
    h.typed("m", idle=3.0)
    h.key("esc", idle=1.0)
    arow("T8j", "Esc in the list changes nothing (the page says so)", "nothing was changed" in st(h), repr(st(h)))
    # put the model the later rows expect back, through the typed entry of the list
    h.typed("m", idle=3.0)
    h.typed("type a name", idle=0.8)
    h.typed("\r", idle=1.2)
    h.typed(MODEL + "\r", idle=1.5)
    h.typed("r", idle=2.5)
    arow("T8k", "the list's last entry asks for a typed name: claude-test typed there is set again", ("model.anthropic=" + MODEL) in conf(), repr(conf()))
    h.typed("x", idle=1.2)
    T = h.text()
    arow("T9d", "X shows set.ai key anthropic clear", "set.ai key anthropic clear" in T and "will be removed from the AI helper" in T, T[-600:])
    h.typed("r", idle=2.0)
    arow("T9e", "Run removes it: the key file is gone, the row says not set", not os.path.exists(kp) and cell(h, 3).endswith("not set") and "The key for anthropic is cleared" in st(h), repr((os.path.exists(kp), cell(h, 3), st(h))))
    # ------------------------------------------------------------------------------------------ Custom
    say("\n--- C: Custom")
    for _ in range(4):
        h.key("down", idle=0.5)
    h.typed("x", idle=0.9)
    arow("T10a", "X on a row with no key says so and runs nothing", "No key is set for Custom" in st(h), repr(st(h)))
    h.typed("c", idle=1.0)
    # S.88: one form (six entries, Tab between them, Return presses Continue); a refusal is said in the form, which stays until Esc
    h.typed("\t".join(("Bad", "http://127.0.0.1/v1", "openai", "bearer", "", "max_tokens")) + "\r", idle=1.2)
    refused = "Not accepted: the address" in h.text()
    h.key("esc", idle=1.0)
    arow("T10b", "an http address is refused by the form: 'Not accepted: the address', nothing changed", refused and not any(l.startswith("custom.") for l in conf()), repr((st(h), conf())))
    h.typed("c", idle=1.0)
    url = "https://127.0.0.1:%d/v1/chat/completions" % STATE["port"]
    h.typed("\t".join(("MyLLM", url, "openai", "bearer", "", "max_tokens")) + "\r", idle=1.5)
    T = h.text()
    arow("T11a", "the whole sentence is shown before it runs: set.ai custom MyLLM <url> openai bearer - max_tokens, and the effect names the host",
         ("set.ai custom MyLLM " + url + " openai bearer - max_tokens") in re.sub(r"\s+", " ", T) or ("set.ai custom MyLLM" in T and "openai bearer - max_tokens" in T), T[-900:])
    a3 = fg.audit_off()
    h.typed("r", idle=1.2)
    h.typed("custom\r", idle=2.0)
    new = fg.audit_new(a3) or ""
    arow("T11b", "with the word custom typed it runs: the row shows MyLLM and the address, ai.conf holds the connection, the audit line has the host and not the address",
         "MyLLM" in h.line(7) and ("custom.url=" + url) in conf() and re.search(r"set\.ai custom name=MyLLM host=127\.0\.0\.1:%d$" % STATE["port"], new, re.M) is not None and "/v1/chat/completions" not in new,
         repr((h.line(7)[3:110], new[-200:])))
    h.key("enter", idle=1.2)
    h.typed("r", idle=1.2)
    h.typed("custom\r", idle=2.0)
    marks = [h.line(r)[3:6] for r in range(3, 8)]
    arow("T12", "selecting Custom moves the check box: exactly one [x], on the Custom row, and ai.conf says provider=custom", marks == ["[ ]", "[ ]", "[ ]", "[ ]", "[x]"] and "provider=custom" in conf(), repr((marks, conf())))
    h.typed("d", idle=1.0)
    h.typed("r", idle=2.0)
    arow("T13a", "D while Custom is in use: the helper refuses and the page shows its words; the connection stays", "The AI helper refused" in st(h) and any(l.startswith("custom.url=") for l in conf()), repr((st(h), conf())))
    h.key("enter", idle=1.2)
    h.typed("r", idle=2.0)
    marks = [h.line(r)[3:6] for r in range(3, 8)]
    arow("T13b", "Enter on the provider in use unchecks it: no [x] anywhere, the summary says the AI is off, ai.conf has an empty provider", marks == ["[ ]"] * 5 and h.line(9)[3:].startswith("The AI is OFF") and "provider=" in conf(),
         repr((marks, h.line(9)[3:60], conf())))
    h.typed("d", idle=1.0)
    h.typed("r", idle=2.0)
    arow("T14", "D now works: no custom.* line is left and the row is not filled in again", not any(l.startswith("custom.") for l in conf()) and "(not filled in)" in h.line(7) and "The custom connection is cleared" in st(h), repr((conf(), h.line(7)[3:80], st(h))))
    # ------------------------------------------------------------------------------------------ limits and the CA file
    say("\n--- L and A")
    h.typed("l", idle=1.0)
    h.typed("speed\r", idle=1.3)
    arow("T15a", "L with a name that is none of the six runs nothing", "speed is not one of the six limits" in st(h), repr(st(h)))
    h.typed("l", idle=1.0)
    h.typed("requests-hour\r", idle=1.0)
    h.typed("77\r", idle=1.4)
    T = h.text()
    arow("T15b", "the sentence is shown: set.ai limit requests-hour 77", "set.ai limit requests-hour 77" in T, T[-600:])
    h.typed("r", idle=2.0)
    arow("T15c", "Run: ai.conf holds limit.requests-hour=77 and the Limits line shows it", "limit.requests-hour=77" in conf() and "requests-hour 77" in h.text(), repr((conf(), st(h))))
    h.typed("a", idle=1.0)
    h.typed(STATE["ca"] + "\r", idle=1.5)
    h.typed("r", idle=1.2)
    h.typed("ca\r", idle=2.0)
    arow("T16", "A: a certificate file needs the word ca typed; then ai.conf holds ca-file and the page shows it", ("ca-file=" + STATE["ca"]) in conf() and ("Certificate authorities: " + STATE["ca"]) in h.text(), repr((conf(), st(h))))
    h.key("ctrl-q", idle=1.5)
    h.end()


def accounts_section():
    say("\n--- the Accounts box")
    h = page()
    h.key("tab", idle=0.8)
    T = h.text()
    arow("T17a", "Tab moves to the Accounts box (the status line names it)", st(h).startswith("[Accounts]"), repr(st(h)))
    rows = [cell(h, r) for r in range(26, 31)]
    arow("T17b", "only the USER accounts are listed, by name, each with its gate read from the scratch group file: zzai1 off, zzai2 off, zzai3 off and suspended; no group account, no fixture",
         re.match(r"^zzai1\s+%s\s+off$" % re.escape(ME), rows[0]) is not None and re.match(r"^zzai2\s+zzother2\s+off$", rows[1]) is not None
         and re.match(r"^zzai3\s+zzother3\s+off\s+\(suspended\)$", rows[2]) is not None and rows[3] == "" and "zzaig" not in T, repr(rows))
    arow("T17c", "the summary counts them: 3 accounts of persons; 0 may use the AI", h.line(31)[3:].startswith("3 accounts of persons; 0 may use the AI."), repr(h.line(31)[3:100]))
    a0 = fg.audit_off()
    h.key("enter", idle=1.4)
    T = h.text()
    arow("T18a", "Enter on zzai1 shows modify.account zzai1 ai-on and the effect", "modify.account zzai1 ai-on" in T and "will be able to" in T, T[-800:])
    h.typed("r", idle=1.2)
    h.typed("nope\r", idle=1.6)
    arow("T18b", "a wrong name runs nothing: the scratch group file is unchanged and the row is off", ME not in fg.read_group().get("sdaiusers", []) and "off" in h.line(26)[3:], repr((fg.read_group().get("sdaiusers"), h.line(26)[3:80])))
    h.key("enter", idle=1.2)
    h.typed("r", idle=1.2)
    h.typed("zzai1\r", idle=2.5)
    new = fg.audit_new(a0) or ""
    arow("T18", "the name typed: the gate is ON in the scratch group file, the row says ON, the summary counts one, the audit trail has 'modify.account ai-on account=zzai1'",
         ME in fg.read_group().get("sdaiusers", []) and re.search(r"zzai1\s+%s\s+ON$" % re.escape(ME), cell(h, 26)) is not None and cell(h, 31).startswith("3 accounts of persons; 1 may use the AI.")
         and re.search(r"modify\.account ai-on account=zzai1$", new, re.M) is not None, repr((fg.read_group().get("sdaiusers"), cell(h, 26), new[-200:])))
    if MUTANT_ONLY_ACCOUNTS:
        h.key("ctrl-q", idle=1.0)
        h.end()
        return
    h.key("enter", idle=1.2)
    T = h.text()
    arow("T19a", "Enter again shows ai-off, and no name is asked for turning a gate OFF", "modify.account zzai1 ai-off" in T and "no longer be able" in T, T[-600:])
    h.typed("r", idle=2.5)
    arow("T19b", "Run: the gate is off in the scratch group file and the row says off", ME not in fg.read_group().get("sdaiusers", []) and "off" in h.line(26)[3:], repr((fg.read_group().get("sdaiusers"), h.line(26)[3:80])))
    h.typed("m", idle=0.9)
    arow("T19c", "a Provider key in the Accounts box is refused in words", "Move to the Provider box" in st(h), repr(st(h)))
    h.key("ctrl-q", idle=1.5)
    h.end()


def ctx_file():
    return os.path.join(box(), "ai", "state", "context")


def ctx_text():
    try:
        return open(ctx_file()).read()
    except OSError:
        return None


def context_section():
    """S.160 (7 Nov 26): T, the standing text.  The shipped default is put beside the providers file, as the installer puts it beside the installed one.  Every outcome is the helper's
    file (box/ai/state/context), the audit trail, or what the ai verb's preview printed."""
    say("\n--- T, the standing text sent with every request (S.160)")
    shipped = open(os.path.join(HERE, "ai-context")).read().rstrip("\n")
    first = shipped.split("\n")[0]
    shutil.copyfile(os.path.join(HERE, "ai-context"), os.path.join(os.path.dirname(STATE["providers"]), "ai-context"))
    if os.path.exists(ctx_file()):
        os.remove(ctx_file())
    h = page()
    h.typed("t", idle=1.5)
    T = h.text()
    arow("T30", "T opens a box titled 'Standing text sent with every AI request' that says the text in use is the shipped default and shows its first line",
         "Standing text sent with every AI request" in T and "Now: the shipped default." in T and first[:60] in T, T[:600])
    a0 = fg.audit_off()
    h.key("esc", idle=1.5)
    arow("T31", "Esc closes it: the page is back, the status says unchanged, no file was made and nothing was audited",
         "What this means" in h.text() and "unchanged" in st(h) and ctx_text() is None and not (fg.audit_new(a0) or "").strip(), repr((st(h), fg.audit_new(a0))))
    h.typed("t", idle=1.5)
    h.typed("Site note: ZQX7 is our test account.\r", idle=0.8)
    h.key("tab", idle=0.6)
    h.key("enter", idle=1.5)
    T = h.text()
    arow("T32", "typing a line at the top and Save shows the Run / Cancel box naming set.ai context and the size; Cancel is the default",
         "set.ai context <the text above," in T and "as hexadecimal>" in T, T[:800])
    # the sentence wraps inside the box, and the page's own boxes show beside it on the same screen rows, so the two halves are matched on consecutive rows
    TL = T.split("\n")
    wrapped = any("it is not shown in" in TL[i] and "the preview." in TL[i + 1] for i in range(len(TL) - 1)) or any("it is not shown in the preview." in l for l in TL)
    arow("T32b", "the box says the text is NOT shown in the preview (8 Nov 26, Kimi's review: it said 'shown in each preview', which the preview does not do)",
         wrapped and "shown in each" not in T, repr([l for l in TL if "preview" in l or "begin with" in l]))
    h.key("esc", idle=1.5)
    arow("T33", "Cancel in that box runs nothing: no file, the status says nothing was run", ctx_text() is None, repr((st(h), ctx_text())))
    a1 = fg.audit_off()
    h.typed("t", idle=1.5)
    h.typed("Site note: ZQX7 is our test account.\r", idle=0.8)
    h.key("tab", idle=0.6)
    h.key("enter", idle=1.5)
    h.typed("r", idle=3.0)
    want = "Site note: ZQX7 is our test account.\n" + shipped + "\n"
    got = ctx_text()
    aud = fg.audit_new(a1) or ""
    arow("T34", "Run: the helper's file holds the typed line followed by the default, whole; one audit line 'set.ai context bytes=N' (N the text's length) and no text in it",
         got == want and len(re.findall(r"set\.ai context bytes=%d$" % (len(want) - 1), aud, re.M)) == 1 and "ZQX7" not in aud,
         repr((got[:120] if got else got, len(want) - 1, aud[-300:])))
    arow("T34b", "the status line says the standing text is now the administrator's (14011)", "now the administrator's" in st(h), repr(st(h)))
    h.typed("t", idle=1.5)
    arow("T35", "T again says the text in use is the administrator's own and shows the typed line", "Now: the administrator's own." in h.text() and "ZQX7" in h.text(), h.text()[:500])
    h.key("esc", idle=1.5)
    a2 = fg.audit_off()
    h.typed("t", idle=1.5)
    h.typed("Explain gpl.bp to me.\r", idle=0.8)
    h.key("tab", idle=0.6)
    h.key("enter", idle=1.5)
    h.typed("r", idle=3.0)
    aud = fg.audit_new(a2) or ""
    arow("T36", "a text that names SD's own code (gpl.bp) is refused by set.ai: the kept text is unchanged and the trail says 'set.ai context refused name=gpl.bp'",
         ctx_text() == want and "set.ai context refused name=gpl.bp" in aud and "names SD's own code" in st(h), repr((st(h), aud[-200:])))
    # what an ordinary request now sends: the ai verb's preview, answered n (nothing is sent)
    g.put(os.path.join(box(), "ai", "state", "ai.conf"), "# test\nprovider=openai\nmodel.openai=%s\nca-file=%s\n" % (MODEL, STATE["ca"]))
    g.put(keyfile("openai"), KEY + "\n")
    os.chmod(keyfile("openai"), 0o600)
    n0 = len(STATE["fm"].log)
    out = adm('ai "what is a select list"', "n")
    blob = "\n".join(out)
    arow("T37", "the ai verb's preview shows NOTHING of the standing text, only the fixed sentence and the question; nothing is sent on n",
         "ZQX7" not in blob and "Standing" not in blob and "You are answering" in blob and "what is a select list" in blob and len(STATE["fm"].log) == n0, repr(out[-12:]))
    n0 = len(STATE["fm"].log)
    out = adm('ai "what is a select list [[plain]]"', "y")
    rq = STATE["fm"].log[n0:] if len(STATE["fm"].log) > n0 else []
    bodyb = rq[-1].get("body", b"") if rq else b""
    bodys = bodyb.decode("utf-8", "replace") if isinstance(bodyb, bytes) else str(bodyb)
    arow("T37b", "answered y: what arrives carries the administrator's standing text (ZQX7) before the fixed sentence, and the question as typed",
         len(rq) == 1 and "ZQX7" in bodys and bodys.index("ZQX7") < bodys.index("You are answering") and "what is a select list [[plain]]" in bodys, bodys[:300])
    h.typed("t", idle=1.5)
    h.key("tab", idle=0.6)
    h.key("tab", idle=0.6)
    h.key("enter", idle=1.5)
    a3 = fg.audit_off()
    h.typed("r", idle=3.0)
    aud = fg.audit_new(a3) or ""
    arow("T38", "Shipped default, Run: the administrator's file is gone, one audit line 'set.ai context=default', and the status says the default is back (14012)",
         ctx_text() is None and len(re.findall(r"set\.ai context=default$", aud, re.M)) == 1 and "shipped default again" in st(h), repr((st(h), aud[-200:])))
    h.key("ctrl-q", idle=1.5)
    h.end()


def tail_section():
    say("\n--- the helper not running, a small window")
    h = page()
    STATE["runner"].terminate()
    STATE["runner"].wait(timeout=10)
    h.key("f5", idle=2.0)
    arow("T20a", "the helper is not running: the summary says so in words and the rows are blank", h.line(9)[3:].startswith("The AI helper is not running"), repr(h.line(9)[3:100]))
    h.typed("m", idle=1.0)
    arow("T20b", "M then says the helper could not be reached (11607); the page is still there", "The AI helper could not be reached" in st(h) and "What this means" in h.text(), repr(st(h)))
    h.key("enter", idle=1.0)
    arow("T20c", "Enter on a provider says the same and opens no box", "The AI helper could not be reached" in st(h) and "set.ai provider" not in h.text(), repr(st(h)))
    h.key("ctrl-q", idle=1.5)
    h.end()
    h = page(cols=100, rows=30)
    T = h.text()
    arow("T22", "a window under 140 by 43 gets no page (the toolkit's one size check)", "AI provider - one for every account" not in T and "What this means" not in T, T[-300:])
    h.end()


MUTANT_ONLY_PROVIDER_SELECT = False
MUTANT_ONLY_ACCOUNTS = False


def main():
    global MUTANT_ONLY_PROVIDER_SELECT, MUTANT_ONLY_ACCOUNTS
    mutant = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mutant=")), None)
    only = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--only=")), None)     # 7 Nov 26: provider | accounts | context
    if only not in (None, "provider", "accounts", "context"):
        bail("usage: sandbox-tool-ai.py <dir> [--build] [--only=provider|accounts|context] [--mutant=NAME]")
    if mutant is not None and mutant not in MUTANTS:
        bail("usage: sandbox-tool-ai.py <dir> [--build] [--mutant=%s]" % "|".join(MUTANTS))
    try:
        sh.setup("sandbox-tool-ai.py")
        setup_ai()
        if mutant is not None:
            mutate(mutant)
            compile_page()
            MUTANT_ONLY_PROVIDER_SELECT = True
            MUTANT_ONLY_ACCOUNTS = True
            say("sandbox-tool-ai: MUTANT %s: the rows that must fail, and nothing else: %s" % (mutant, ", ".join(MUTANTS[mutant][2])))
        if only in (None, "provider"):
            provider_section()
        if only in (None, "accounts"):
            accounts_section()
        if mutant is None and only in (None, "context"):
            context_section()
        if mutant is None and only is None:
            tail_section()
    finally:
        try:
            STATE["runner"].terminate()
            STATE["runner"].wait(timeout=10)
        except Exception:
            pass
        if "fm" in STATE:
            STATE["fm"].stop()
        os.environ.pop("SD_AI_SOCKET", None)
        os.environ.pop("SD_AI_CTL", None)
        sh.teardown()
    say("\nsandbox-tool-ai: %d passed, %d failed" % (sh.tkb.passed, sh.tkb.failed))
    if mutant is not None:
        want = sorted(set(MUTANTS[mutant][2]))
        got = sorted({re.match(r"T\d+", i).group(0) for i in FAILED_IDS if re.match(r"T\d+", i)})
        ok = want == got
        say("sandbox-tool-ai: MUTANT %s: the rows that failed are %s; they had to be exactly %s -> %s" % (mutant, got, want, "KILLED BY ITS OWN ROWS" if ok else "NOT AS EXPECTED"))
        return 0 if ok else 1
    return 0 if sh.tkb.failed == 0 and sh.tkb.passed > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
