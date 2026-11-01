#!/usr/bin/env python3
#
# sandbox-aidocs.py - the AI line's documentation passages (S.100): $tk_aidocs chooses a few sections of SD's own pages, tk_ai shows them in the preview and sends them with the request.
# Driven on the home screen (an ordinary session, and the administrator's) on a private SD.  No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-aidocs.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 every row passed, 1 a row failed,
# 2 it could not run.
#
# WHAT RUNS.  The real helper, the fake provider (which LOGS every request) and the fixture account, all as sandbox-ai-line.py has them, with FIXTURE pages made in the sandbox's system
# directory: docs/user/zzuser.md (a page with three sections, one about "zzfrobnicate"), docs/admin/zzadmin.md (a section about "zzgrommet"), and names and sizes the reader must leave
# alone.  The words are made up, so a passage can only come from the fixture.
#
# THE INSTRUMENT.  "Sent" is the FAKE's request log, "shown" is the emulated screen, "chosen" is both.  Every row that needs a request counts one arriving first.
#
#   D1a-D1d  an ordinary account asks about a word in a user page: the preview says how many passages and from where, shows the section's first lines, and Cancel (the default) sends
#            nothing; Send puts the passage in the request (its id in brackets and the section text) and adds the documentation sentence (11922) to the instruction
#   D2a-D2b  the same account asks about the administrator's word: no passage in the preview, none in the request, whether or not the file is readable by the sandbox user
#   D3a-D3b  the administrator asks about it: the passage is chosen, from docs/admin, and is sent
#   D4a-D4c  nothing is chosen for a request of common words only, for a word that no page holds, and the files the reader must leave alone (a name with a capital, a name with a space, a file
#            over 120,000 bytes, a file with a byte of 248 or more) are never read: their words are in no request
#   D5a      a user page that holds a # inside a fenced block: the block's comment is not a section of its own (the passage that is chosen holds the whole block)
import importlib.util
import os
import re
import shutil
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


al = _load("sandbox_ailine_for_aidocs", "sandbox-ai-line.py")
sh, g, q3 = al.sh, al.g, al.q3
say, bail, has, dump, adm, H = al.say, al.bail, al.has, al.dump, al.adm, al.H
KEY, MODEL = al.KEY, al.MODEL
ACCT = al.ACCT
FAILED_IDS = []
SCREEN = [None]
PROGS = ("tk_aidocs", "tk_ai")
FILES = tuple("gpl.bp/" + n for n in PROGS) + ("messages/11920", "messages/11921", "messages/11922")

USER_PAGE = """# The zz page

An introduction that mentions nothing of the fixture.

## Working with zzfrobnicate

To zzfrobnicate a record, open the file and run the verb zzfrobnicate with the record id.
The zzfrobnicate verb never changes the file.
A second line of the same section.
A third line of the same section.
A fourth line of the same section.
A fifth line of the same section.

## Something else

Nothing about the word here.

## A shell example

Run it like this:

```
# zzcomment inside a block
zzblockcmd one
# second comment
zzblockcmd two
```

and the block is over.
"""

ADMIN_PAGE = """# The zz administrator page

## Tuning the zzgrommet

The administrator sets the zzgrommet with the verb zzgrommet.set and reads it back with zzgrommet.show.
"""


def arow(rid, name, ok, detail=""):
    sh.row("%s %s" % (rid, name), ok, detail)
    if not ok:
        FAILED_IDS.append(rid)
        if SCREEN[0] is not None:
            say("    --- the screen at the failure of %s ---" % rid)
            dump(SCREEN[0])


def make_fixture():
    base = os.path.join(sh.SYS, "docs")
    shutil.rmtree(base, ignore_errors=True)
    os.makedirs(os.path.join(base, "user"))
    os.makedirs(os.path.join(base, "admin"))
    g.put(os.path.join(base, "user", "zzuser.md"), USER_PAGE)
    g.put(os.path.join(base, "admin", "zzadmin.md"), ADMIN_PAGE)
    # names and files the reader must leave alone
    g.put(os.path.join(base, "user", "Zzcapital.md"), "# Capital\n\nThe zzcapitalword page, which has a capital in its name and must never be read.\n")
    g.put(os.path.join(base, "user", "zz space.md"), "# Space\n\nThe zzspaceword page, which has a space in its name and must never be read.\n")
    g.put(os.path.join(base, "user", "zzbig.md"), "# Big\n\nThe zzbigword page, which is over the limit.\n" + ("padding line of the big page\n" * 5000))
    with open(os.path.join(base, "user", "zzhigh.md"), "wb") as f:
        f.write(b"# High\n\nThe zzhighword page has a byte \xf9 in it and must never be read.\n")
    g.put(os.path.join(base, "user", "zznotmd.txt"), "# Text\n\nThe zztextword file does not end in .md.\n")


def sync_and_compile():
    for rel in FILES:
        shutil.copyfile(os.path.join(TREE, "sdsys", rel), os.path.join(sh.SYS, rel))
    for n in PROGS:
        out = q3.adm(["BASIC gpl.bp " + n], internal=True)
        if not has(out, r"^Compiled 1 program\(s\) with no errors"):
            bail("%s did not compile in the sandbox:\n%s" % (n, "\n".join(out[-8:])))


def last_prompt(n0):
    rq = al.requests()
    if len(rq) <= n0:
        return None, None
    body = rq[-1][2] or {}
    prompt = body["messages"][-1]["content"] if body.get("messages") else ""
    system = body.get("system", "")
    if isinstance(system, list):                           # the provider's form: a list of blocks, each with its text
        system = "\n".join(b.get("text", "") for b in system if isinstance(b, dict))
    return prompt, system


def go(admin, text, send):
    """the home screen, the request typed, Enter: the preview.  Returns the screen text of the preview, then (send) sends and returns the request that arrived."""
    fm = al.STATE["fm"]
    h = al.home(admin=admin)
    SCREEN[0] = h
    n0 = len(fm.log)
    al.ask(h, text)
    prev = h.text()
    prompt = system = None
    if send:
        h.typed("s", idle=4.0)
        prompt, system = last_prompt(n0)
        h.key("enter", idle=1.5)
    else:
        h.key("enter", idle=1.5)
    sent = len(fm.log) - n0
    h.key("ctrl-q", idle=1.5)
    h.end()
    return prev, prompt, system, sent


def sec_user():
    say("\n--- D1: an ordinary account, a word in a user page")
    prev, _p, _s, sent = go(False, "how do I zzfrobnicate a record", False)
    arow("D1a", "the preview says how many passages and shows the id of the page and section", re.search(r"The documentation: 1 passages", prev) is not None and "[user/zzuser.md#working-with-zzfrobnicate]" in prev, prev[-900:])
    arow("D1b", "...shows the section's first lines and counts the rest (the preview shows four, the request carries all)", "To zzfrobnicate a record" in prev and "A third line" not in prev and re.search(r"more lines", prev) is not None, prev[-900:])
    arow("D1c", "Cancel is the default: nothing was sent", sent == 0, repr(sent))
    prev, prompt, system, sent = go(False, "how do I zzfrobnicate a record", True)
    arow("D1d", "Send: ONE request holds the passage with its id and ALL its lines, and the instruction holds the documentation sentence",
         sent == 1 and prompt is not None and "Documentation passage [user/zzuser.md#working-with-zzfrobnicate]" in prompt and "A fifth line of the same section." in prompt
         and "Something else" not in prompt and prompt.rstrip().endswith("how do I zzfrobnicate a record") and al.msg(11922)[:40] in (system or ""), repr((sent, (prompt or "")[-500:], (system or "")[-300:])))


def sec_admin_words():
    say("\n--- D2 and D3: the administrator's page of the documentation")
    prev, prompt, system, sent = go(False, "how do I set the zzgrommet", True)
    arow("D2a", "an ordinary account asking about the administrator's word: no passage in the preview", "The documentation:" not in prev and "zzadmin.md" not in prev, prev[-700:])
    arow("D2b", "...and none in the request", sent == 1 and "zzadmin.md" not in (prompt or "") and "Documentation passage" not in (prompt or ""), repr((sent, (prompt or "")[-300:])))
    prev, prompt, system, sent = go(True, "how do I set the zzgrommet", True)
    arow("D3a", "the administrator: the passage from docs/admin is in the preview", "The documentation: 1 passages" in prev and "[admin/zzadmin.md#tuning-the-zzgrommet]" in prev, prev[-900:])
    arow("D3b", "...and in the request, with the text of the section", sent == 1 and "Documentation passage [admin/zzadmin.md#tuning-the-zzgrommet]" in (prompt or "") and "zzgrommet.show" in (prompt or ""), repr((sent, (prompt or "")[-400:])))


def sec_none():
    say("\n--- D4: nothing chosen, and files that are left alone")
    prev, prompt, system, sent = go(False, "how can you do this with the", True)
    arow("D4a", "a request of common words only: no passage", sent == 1 and "Documentation passage" not in (prompt or "") and "The documentation:" not in prev, repr((sent, (prompt or "")[-200:])))
    prev, prompt, system, sent = go(False, "tell me about zzneverheardofit", True)
    arow("D4b", "a word that no page holds: no passage", sent == 1 and "Documentation passage" not in (prompt or ""), repr((sent, (prompt or "")[-200:])))
    leaks = []
    for w in ("zzcapitalword", "zzspaceword", "zzbigword", "zzhighword", "zztextword"):
        prev, prompt, system, sent = go(False, "what is %s" % w, True)
        if "Documentation passage" in (prompt or "") or "The documentation:" in prev:
            leaks.append(w)
    arow("D4c", "a name with a capital or a space, a file over 120,000 bytes, a file with a byte of 248 or more and a file that does not end in .md are never read", not leaks, repr(leaks))


def sec_fence():
    say("\n--- D5: a # inside a fenced block")
    prev, prompt, system, sent = go(False, "show me zzblockcmd", True)
    arow("D5a", "the passage holds the whole block - both comments and both commands - and the comment line did not start a section of its own",
         sent == 1 and "# zzcomment inside a block" in (prompt or "") and "zzblockcmd two" in (prompt or "") and (prompt or "").count("Documentation passage [") == 1, repr((sent, (prompt or "")[-500:])))


def main():
    try:
        sh.setup("sandbox-aidocs.py")
        al.setup_ai(None)
        sync_and_compile()
        make_fixture()
        al.configure()
        al.start_runner()
        sec_user()
        sec_admin_words()
        sec_none()
        sec_fence()
    finally:
        al.stop_runner()
        sh.teardown()
    say("\nsandbox-aidocs: %d passed, %d failed" % (sh.tkb.passed, sh.tkb.failed))
    return 0 if sh.tkb.failed == 0 and sh.tkb.passed > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
