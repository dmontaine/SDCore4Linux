#!/usr/bin/env python3
#
# sandbox-tool-jobs.py - the scheduled jobs page, TOOL.JOBS, and its verb SET.BATCH, on a private SD (S.102 stage 1: the batch gate's list, account jobs only).
# No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-tool-jobs.py <dir> [--build] [--mutant=NAME]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 every row passed, 1 a row
# failed, 2 it could not run.  With --mutant=NAME one change is made to the SANDBOX'S OWN COPY of the page and exit 0 means the rows that had to fail failed and no others (MUTANTS).
#
# THE INSTRUMENT.  What the page and the verb did is read from the disk (the account's record in @SDSYS/batch.jobs), from the audit file, and from a REAL command-line session of
# the fixture account (sd -azjob zjrep, as a cron job would start it, an ordinary session: SDTEST_ADMIN is not set), never from what the page says about itself.
#
#   J0   an ordinary account has neither tool.jobs nor set.batch
#   J1   SET.BATCH's refusals and its list, each with the disk unchanged; the command-line session is refused before anything is allowed (the null case of J3)
#   J2   the page: the audit line, the account with 0, its paragraphs and sentences (a verb is not offered), the box naming the command, Esc runs nothing, Run writes the record
#   J3   the command-line session now runs the paragraph; the sentence that was not allowed is still refused (the control)
#   J4   a listed name whose VOC record has gone is shown so and is taken off; an empty list leaves no record
#   J5   a name $tk_run cannot pass is not sent: the page names the prompt command and opens no box
#   J6   F1 and the [?]; a window under 140 by 43 gets no page; Ctrl-Q leaves
# NOT HELD: a real cron job or timer (a sandbox has no scheduler of its own; the session started here is the same command line), the help text itself (sandbox-docs.py).
import importlib.util
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


sh = _load("sandbox_home_for_tooljobs", "sandbox-home.py")
say, row, bail, has, dump, H, g = sh.say, sh.row, sh.bail, sh.has, sh.dump, sh.H, sh.g
sh.KEYS["f1"] = "\x1b[[A"
FAILED_IDS = []
ACC = "zjob"
ODD = "zj$odd"

MUTANTS = {
    # name: (old text of the sandbox's tool_jobs, new text, the row ids that must fail and no others, the last section run)
    "no-confirm": ("   call $tk_confirm(sent, el, '', res, cmsg)\n", "   res = 'run' ; cmsg = ''\n", ["J2"], "J2"),
    "plain-test-out": ("   if convert(PLAIN, '', acct) # '' or convert(PLAIN, '', cmd) # '' then\n", "   if 0 then\n", ["J5"], "J5"),
}


def arow(rid, name, ok, detail=""):
    row("%s %s" % (rid, name), ok, detail)
    if not ok:
        FAILED_IDS.append(rid)


def norm(t):
    return re.sub(r"[|\s]+", " ", t)


def box_open(T):
    """The confirm box's own buttons, '[ Run ]  [ Cancel ]': the bare word Cancel is also in the page's help box, and matching it once made the suite press Esc on a page with no box."""
    return re.search(r"\[ ?Run ?\] \[ ?Cancel ?\]", T) is not None


def audit_off():
    path = os.path.join(sh.SYS, "audit")
    if not os.path.exists(path):
        open(path, "ab").close()
    return os.path.getsize(path)


def audit_new(off):
    with open(os.path.join(sh.SYS, "audit"), "rb") as f:
        f.seek(off)
        return f.read().decode("utf-8", errors="replace")


def listed():
    """The account's record in batch.jobs as it is on the disk: None when there is no record."""
    p = os.path.join(sh.SYS, "batch.jobs", ACC)
    if not os.path.exists(p):
        return None
    with open(p, errors="replace") as f:
        return [ln.strip() for ln in f.read().splitlines() if ln.strip()]


def batch_session(cmd):
    """A REAL command-line session of the fixture account, as a scheduled job starts one: sd -azjob <cmd>, ordinary (no SDTEST_ADMIN), nothing on its input."""
    acct = os.path.join(g.BOX, "user_accounts", ACC)
    say("    > [command line] sd -a%s %s in %s" % (ACC, cmd, os.path.relpath(acct, g.BOX)))
    p = subprocess.run([g.SD, "-a" + ACC, cmd], input="", cwd=acct, env=g.env(False), capture_output=True, text=True, errors="replace", timeout=60)
    return sh.g.ANSI.sub("", p.stdout + p.stderr)


def voc_prog(name, lines):
    """An administrator's program in SDSYS bp that changes the fixture account's VOC; it must print FIX done."""
    g.put(os.path.join(sh.SYS, "bp", name), "\n".join(["$internal", "   openpath '%s/voc' to v else crt 'FIX no voc' ; stop" % os.path.join(g.BOX, "user_accounts", ACC)] + lines + ["   crt 'FIX done'", "end", ""]))
    out = g.adm(["BASIC bp %s" % name, "RUN bp %s" % name], internal=True)
    if not has(out, r"^FIX done$"):
        bail("%s did not run:\n%s" % (name, "\n".join(out[-6:])))


def setup_page():
    for prog in ("set_batch", "tool_jobs"):
        shutil.copyfile(os.path.join(TREE, "sdsys", "gpl.bp", prog), os.path.join(sh.SYS, "gpl.bp", prog))
        out = g.adm(["BASIC gpl.bp %s" % prog], internal=True)
        if not has(out, r"^Compiled 1 program\(s\) with no errors"):
            bail("%s did not compile in the sandbox:\n%s" % (prog, "\n".join(out[-8:])))
    g.FIXTURES[ACC] = ("no", "no")
    g.build_account(ACC)
    voc_prog("zzjobfix", ["   write 'PA':@fm:'DISPLAY ZJREP RAN' to v, 'zjrep'",
                          "   write 'S':@fm:'DISPLAY ZJSEN RAN' to v, 'zjsen'",
                          "   write 'PA':@fm:'DISPLAY ODD RAN' to v, '%s'" % ODD,
                          "   write 'V':@fm:'CA':@fm:'$zzkf' to v, 'zjverb'"])
    p = os.path.join(sh.SYS, "batch.jobs", ACC)
    if os.path.exists(p):
        os.remove(p)


def mutate(name):
    old, new, _kills, _last = MUTANTS[name]
    path = os.path.join(sh.SYS, "gpl.bp", "tool_jobs")
    src = open(path, encoding="utf-8", errors="replace").read()
    if src.count(old) != 1:
        bail("mutant %s: the text to change is found %d times, not once" % (name, src.count(old)))
    g.put(path, src.replace(old, new))
    out = g.adm(["BASIC gpl.bp tool_jobs"], internal=True)
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("the mutant page did not compile:\n" + "\n".join(out[-8:]))


class Page:
    def __init__(self, cols=140, rows=43):
        self.h = H(admin=True, cols=cols, rows=rows)
        self.h.typed("tool.jobs\r", idle=3.5)

    def text(self):
        return norm(self.h.text())

    def key(self, name, idle=0.6):
        if len(name) == 1:
            self.h.typed(name, idle=idle)
        else:
            self.h.key(name, idle=idle)

    def st(self):
        return self.h.line(40)

    def selected(self):
        m = re.search(r"Selected: (\S+) ", self.text())
        return m.group(1) if m else None

    def walk_to(self, name, n=80):
        """Down until the explanation's Selected line names it, then Up if Down did not reach it."""
        for direction in ("down", "up"):
            for _ in range(n):
                if self.selected() == name:
                    return True
                before = self.selected()
                self.key(direction, 0.3)
                if self.selected() == before:
                    break
        return self.selected() == name

    def quit(self):
        self.key("ctrl-q", idle=1.5)
        self.h.end()


def section_j0():
    say("\n--- J0: an ordinary account has neither")
    out = g.plain("zzhd", ["tool.jobs", "set.batch"])
    T = norm(" ".join(out))
    arow("J0", "an ordinary session is told neither is a command, and no page or list appears", "Accounts" not in T and "may run from the command line" not in T and len(re.findall(r"not in your VOC", T)) == 2, T[:300])


def section_j1():
    say("\n--- J1: SET.BATCH's refusals; the command line before anything is allowed")
    out = batch_session("zjrep")
    arow("J1a", "the command-line session sd -azjob zjrep is refused with message 11000 and does not run the paragraph (the null case of J3)",
         "zjrep is not a command that account zjob may run from the command line" in out and "ZJREP RAN" not in out, repr(out[-300:]))
    a0 = audit_off()
    cases = [("set.batch", r"No account may run a command from the command line"),
             ("set.batch add zjob", r"^set\.batch \{add \| remove\} account command"),
             ("set.batch add sdsys zjrep", r"^sdsys is the administrator's account"),
             ("set.batch add nosuchacct zjrep", r"^nosuchacct is not a registered account$"),
             ("set.batch add zjob zjverb", r"^zjverb is not a paragraph or a sentence in account zjob$"),
             ("set.batch add zjob nosuchcmd", r"^nosuchcmd is not a paragraph or a sentence in account zjob$"),
             ("set.batch remove zjob zjrep", r"^zjrep was not allowed in account zjob; nothing changed$")]
    for i, (cmd, rx) in enumerate(cases):
        out = g.adm([cmd])
        arow("J1b%d" % i, "%s answers %s and the account has no record on the disk" % (cmd, rx), has(out, rx) and listed() is None, repr(out[-3:]))
    new = audit_new(a0)
    arow("J1c", "no refusal wrote a set.batch audit line", "set.batch " not in new, repr(new[-300:]))


def section_j2():
    say("\n--- J2: the page")
    a0 = audit_off()
    p = Page()
    T = p.text()
    if "Accounts" not in T or "What this means" not in T:
        dump(p.h)
        bail("tool.jobs never drew its page, so no row below can be believed")
    new = audit_new(a0)
    arow("J2a", "opening the page writes 'tool start app=tool.jobs' once", len(re.findall(r"tool start app=tool\.jobs$", new, re.M)) == 1, repr(new[-200:]))
    found = p.walk_to(ACC)
    arow("J2b", "the fixture account is listed with 0 commands allowed", found and re.search(r"\b%s 0\b" % ACC, p.text()) is not None, repr(p.text()[:400]))
    p.key("enter", 1.0)
    T = p.text()
    arow("J2c", "Enter goes to its Commands: zjrep (PA) and zjsen (S) are listed as not allowed, the verb zjverb is not offered",
         "Commands in %s" % ACC in T and re.search(r"zjrep PA no\b", T) is not None and re.search(r"zjsen S no\b", T) is not None and "zjverb" not in T, repr(T[:700]))
    p.walk_to("zjrep")
    p.key("enter", 1.3)
    T = p.text()
    arow("J2d", "Enter on zjrep shows the command 'set.batch add zjob zjrep' in a box with Run and Cancel", "set.batch add zjob zjrep" in T and box_open(T), T[-600:])
    p.key("esc", 1.2)
    arow("J2e", "Esc runs nothing: no record on the disk, no set.batch audit line", listed() is None and "set.batch add" not in audit_new(a0), repr((listed(), p.st())))
    p.key("enter", 1.3)
    p.key("r", 3.0)
    new = audit_new(a0)
    T = p.text()
    arow("J2f", "Run: the record on the disk is zjrep, the audit trail has 'set.batch add account=zjob command=zjrep', and the row now says yes",
         listed() == ["zjrep"] and re.search(r"set\.batch add account=zjob command=zjrep$", new, re.M) is not None and re.search(r"zjrep PA yes\b", T) is not None,
         repr((listed(), new[-200:], T[:500])))
    arow("J2g", "the account's count is 1", re.search(r"\b%s 1\b" % ACC, T) is not None, repr(T[:400]))
    return p


def section_j3():
    say("\n--- J3: the command line after the change")
    out = batch_session("zjrep")
    arow("J3a", "sd -azjob zjrep now runs the paragraph", "ZJREP RAN" in out and "may run from the command line" not in out, repr(out[-300:]))
    out = batch_session("zjsen")
    arow("J3b", "sd -azjob zjsen, not allowed, is still refused (the control)", "zjsen is not a command that account zjob may run" in out and "ZJSEN RAN" not in out, repr(out[-300:]))


def section_j4(p):
    say("\n--- J4: a listed name whose VOC record has gone")
    voc_prog("zzjobdel", ["   delete v, 'zjrep'"])
    p.key("f5", 2.5)
    p.walk_to("zjrep")
    T = p.text()
    arow("J4a", "after F5 zjrep is shown as listed but no longer a paragraph or a sentence", re.search(r"zjrep - listed; not PA or S now", T) is not None, repr(T[:600]))
    a0 = audit_off()
    p.key("enter", 1.3)
    p.key("r", 3.0)
    new = audit_new(a0)
    arow("J4b", "Enter and Run take it off: the empty list leaves no record on the disk, the audit has the remove line, the row is gone",
         listed() is None and re.search(r"set\.batch remove account=zjob command=zjrep$", new, re.M) is not None
         and re.search(r"zjrep (-|PA|S) ", p.text()) is None, repr((listed(), new[-200:], p.text()[:500])))      # a ROW: the status line rightly still names zjrep


def section_j5(p):
    say("\n--- J5: a name $tk_run cannot pass")
    p.walk_to(ODD)
    a0 = audit_off()
    p.key("enter", 1.3)
    T = p.text()
    arow("J5", "Enter on %s opens no box and names the command to type at the prompt; nothing is written" % ODD,
         ("at the prompt, set.batch add %s %s" % (ACC, ODD)) in norm(p.st()) and not box_open(T) and listed() is None and "set.batch" not in audit_new(a0), repr((p.st(), T[-300:])))
    if box_open(T):
        p.key("esc", 1.0)


def section_j6(p):
    say("\n--- J6: help, a small window, Ctrl-Q")
    p.key("f1", 1.2)
    arow("J6a", "F1 reaches the help box (a sandbox has no shared account: help is not installed here)", "Help is not installed here" in p.text(), p.text()[-300:])
    p.key("esc", 1.0)
    p.quit()
    h = H(admin=True, cols=100, rows=30)
    h.typed("tool.jobs\r", idle=3.0)
    T = norm(h.text())
    arow("J6b", "a window under 140 by 43 gets no page", "What this means" not in T, T[-300:])
    h.end()


def main():
    mutant = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mutant=")), None)
    if mutant is not None and mutant not in MUTANTS:
        bail("usage: sandbox-tool-jobs.py <dir> [--build] [--mutant=%s]" % "|".join(MUTANTS))
    last = MUTANTS[mutant][3] if mutant else "J6"
    order = ["J2", "J3", "J4", "J5", "J6"]
    try:
        sh.setup("sandbox-tool-jobs.py")
        setup_page()
        if mutant is not None:
            mutate(mutant)
            say("sandbox-tool-jobs: MUTANT %s: the rows that must fail, and nothing else: %s" % (mutant, ", ".join(MUTANTS[mutant][2])))
        if mutant is None:
            section_j0()
            section_j1()
        p = section_j2()
        if mutant is None:
            section_j3()
        if mutant is None or order.index("J4") <= order.index(last):
            if mutant is None:
                section_j4(p)
        if mutant is None or last == "J5":
            section_j5(p)
        if mutant is None:
            section_j6(p)
        else:
            p.quit()
    finally:
        sh.teardown()
    say("\nsandbox-tool-jobs: %d passed, %d failed" % (sh.tkb.passed, sh.tkb.failed))
    if mutant is not None:
        want = sorted(set(MUTANTS[mutant][2]))
        got = sorted({re.match(r"J\d", i).group(0) for i in FAILED_IDS})
        ok = want == got
        say("sandbox-tool-jobs: MUTANT %s: the rows that failed are %s; they had to be exactly %s -> %s" % (mutant, got, want, "KILLED BY ITS OWN ROWS" if ok else "NOT AS EXPECTED"))
        return 0 if ok else 1
    return 0 if sh.tkb.failed == 0 and sh.tkb.passed > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
