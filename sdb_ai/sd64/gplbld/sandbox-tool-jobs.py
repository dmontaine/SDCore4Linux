#!/usr/bin/env python3
#
# sandbox-tool-jobs.py - the scheduled jobs page, TOOL.JOBS, and its verb SET.BATCH, on a private SD (S.102 stage 1: the batch gate's list, account jobs only).
# No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-tool-jobs.py <dir> [--build] [--only=account|admin|account,admin] [--mutant=NAME]
#
# SECTIONS (--only=): account (J0-J6, stage 1: the batch gate's list, about 1 minute) and admin (K0-K12, stage 4: the administrator's scheduled jobs, SET.JOB and the Jobs view).
# Without --only both run; a mutant runs its own section only.
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
#
# SECTION admin (2 Nov 26, S.102 stage 4).  A sandbox is not root and has no sudo, so the SANDBOX'S OWN COPY of set_job is patched in two places and nothing else: the helper
# `sudo -n /usr/local/sbin/sd-elevate` becomes this suite's shim, which runs the REAL sd-elevate with --dry-run first (so the real helper accepts every argument it is given, or its own
# refusal is what set.job sees) and then plays the root half on scratch files - definitions in <dir>/jobs/state, starts in runs.log - printing the helper's own success lines; and
# /usr/bin/systemctl becomes a fake that answers `show -p PROP --value` from the same files.  THE EVIDENCE is what the helper was ASKED (the shim's calls.log, every argument as
# passed), the scratch state, the audit file, and what the page shows after it read the list again.  The success lines the shim prints are the real helper's (test-tooljobs-units.py V6
# ties set.job's anchors to sd-elevate's printf lines); the shim cannot say root writes a timer: that is the VM's.
#   K0   an ordinary account has no set.job
#   K1   set.job's refusals at the prompt (a bad name, a job that is not one of the four, a schedule of none of the five shapes, a wrong form): each says its message and the
#        helper is NOT asked at all
#   K2   set.job alone with no job: the helper is asked job-list, and it says no job is defined
#   K3   the page: J shows the Jobs view, with no job
#   K4   N: the form; a bad schedule and a bad name are refused in the form with nothing asked of the helper
#   K5   N: the box names 'set.job add nightly backup-all daily 02.30', the command and the schedule in words; Esc asks nothing of the helper
#   K6   N, Run: the helper was asked job-set nightly backup-all daily 02:30 (the colon back), the audit line, the row with the next run systemd gave
#   K7   N with the name of a job that exists is refused in the form
#   K8   C: the box names 'set.job change nightly backup-all weekly sun 03.00' and what it replaces; Run asks job-set with the new schedule
#   K9   R: the box names 'set.job run nightly'; Run asks job-run nightly; the row's last run is what systemd says
#   K10  D: the box asks for the name; a wrong name asks nothing; the right one asks job-delete nightly and the job is gone
#   K11  a damaged definition is shown so and R refuses it without asking the helper; (K11b, 2 Nov 26 review) C on a damaged file whose name is not a job name opens no form
#   K12  set.job at the prompt: add of an existing job and change of a missing one are refused before job-set; a helper that fails gives 11332 and an audit line result=failed;
#        F1 in the Jobs view reaches the help box; (2 Nov 26 review) the helper's description lines are not shown (K12g) and run of a damaged job says 11333 before job-run (K12f).
#        The fake systemctl answers ONE `show -p ... TIMER SERVICE` call in systemctl's own block form, the timer's ActiveState being active (K6c, K12c read it).
# NOT HELD: a real cron job or timer (a sandbox has no scheduler of its own; the session started here is the same command line), the help text itself (sandbox-docs.py), root
# writing the units (the VM: witness-s102.py).
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
    "no-confirm": ("   el<-1> = 'It takes effect at the next such session.'\n   call $tk_confirm(sent, el, '', res, cmsg)\n",
                   "   el<-1> = 'It takes effect at the next such session.'\n   res = 'run' ; cmsg = ''\n", ["J2"], "J2"),
    "plain-test-out": ("   if convert(PLAIN, '', acct) # '' or convert(PLAIN, '', cmd) # '' then\n", "   if 0 then\n", ["J5"], "J5"),
    # 2 Nov 26, S.102 stage 4 (section admin)
    "run-no-confirm": ("   el<-1> = 'The page does not wait for it: F5 shows when it has finished, under Last run.'\n   call $tk_confirm(sent, el, '', res, cmsg)\n",
                       "   el<-1> = 'The page does not wait for it: F5 shows when it has finished, under Last run.'\n   res = 'run' ; cmsg = ''\n", ["K9"], "admin"),
    "delete-no-name": ("call $tk_confirm(sent, el, fname, res, cmsg)", "call $tk_confirm(sent, el, '', res, cmsg)", ["K10"], "admin"),
}
JOBS = None        # <dir>/jobs: the shim's scratch state

SHIM = r'''#!/usr/bin/env python3
# sandbox-tool-jobs.py's stand-in for `sudo -n /usr/local/sbin/sd-elevate` in the sandbox's copy of set_job: the REAL sd-elevate with --dry-run first, then the root half played on
# scratch files, printing the helper's own lines.  Every call is logged with its arguments as passed.
import json, os, re, subprocess, sys
J = %(jobs)r
args = sys.argv[1:]
with open(os.path.join(J, "calls.log"), "a") as f:
    f.write(" ".join(args) + "\n")
p = subprocess.run(["bash", %(elevate)r, "--dry-run"] + args, capture_output=True, text=True)
if p.returncode != 0:
    sys.stdout.write(p.stdout + p.stderr)
    sys.exit(p.returncode)
inj = os.path.join(J, "inject")
if os.path.exists(inj) and args and open(inj).read().strip() == args[0]:
    os.remove(inj)
    sys.stdout.write("shim: injected failure\n")
    sys.exit(1)
st = os.path.join(J, "state")
os.makedirs(st, exist_ok=True)
verb = args[0]
if verb == "job-list":
    sys.stdout.write(p.stdout)
    n = 0
    for name in sorted(os.listdir(st)):
        base, ext = os.path.splitext(name)
        if ext == ".damaged":
            if re.match(r"^[a-z]([a-z0-9-]{0,30}[a-z0-9])?$", base):
                print("damaged %%s: the definition does not agree with the helper" %% base)
            else:
                print("damaged %%s: not a job name" %% base)        # the real helper's line for a file whose name is not a job name
            n += 1
        elif ext == ".json":
            d = json.load(open(os.path.join(st, name)))
            print("job %%s: %%s: %%s (%%s)" %% (base, d["sched"], d["cmd"], d["id"]))
            n += 1
    if n == 0:
        print("sd-elevate: no job is defined")
elif verb == "job-set":
    sys.stdout.write(p.stdout)
    m = re.search(r'job-set (\S+): runs "([^"]+)" \((\S+)\) (.+), OnCalendar=', p.stdout)
    name, cmd, jid, sched = m.groups()
    path = os.path.join(st, name + ".json")
    how = "replaced" if os.path.exists(path) else "created"
    json.dump({"id": jid, "cmd": cmd, "sched": sched}, open(path, "w"))
    print("sd-elevate: job %%s %%s" %% (name, how))
    print("sd-elevate: job %%s is scheduled: %%s" %% (name, sched))
elif verb == "job-delete":
    sys.stdout.write(p.stdout)
    name = args[1]
    hit = [x for x in (name + ".json", name + ".damaged") if os.path.exists(os.path.join(st, x))]
    for x in hit:
        os.remove(os.path.join(st, x))
    print("sd-elevate: job %%s deleted" %% name if hit else "sd-elevate: no job named %%s; nothing was changed" %% name)
elif verb == "job-run":
    sys.stdout.write(p.stdout)
    name = args[1]
    if os.path.exists(os.path.join(st, name + ".damaged")):                # the real helper's job_run_state refusal
        sys.stderr.write("sd-elevate: REFUSED - job %%s is damaged; nothing was started (job-set writes it again, job-delete removes it)\n" %% name)
        sys.exit(2)
    if os.path.exists(os.path.join(st, name + ".json")):
        with open(os.path.join(J, "runs.log"), "a") as f:
            f.write(name + "\n")
        print("sd-elevate: job %%s started" %% name)
    else:
        print("sd-elevate: no job named %%s; nothing was started" %% name)
else:
    sys.exit(9)
'''

SYSTEMCTL = r'''#!/usr/bin/env python3
# sandbox-tool-jobs.py's stand-in for /usr/bin/systemctl in the sandbox's copy of set_job: `show -p PROP ... sdcore-job-NAME.timer sdcore-job-NAME.service` answered from the
# shim's files as systemctl prints it: each unit's NAME=VALUE lines, a blank line between the units.  The TIMER has an ActiveState (active) and a Result of its own, as the real
# one has, so a reader that took them from the wrong block would say "running now".
import os, sys
J = %(jobs)r
a = sys.argv[1:]
with open(os.path.join(J, "systemctl.log"), "a") as f:
    f.write(" ".join(a) + "\n")
props, units, i = [], [], 1
if not a or a[0] != "show":
    sys.exit(9)
while i < len(a):
    if a[i] == "-p" and i + 1 < len(a):
        props.append(a[i + 1])
        i += 2
    elif a[i].startswith("sdcore-job-"):
        units.append(a[i])
        i += 1
    else:
        sys.exit(9)
if not props or not units:
    sys.exit(9)
runs = open(os.path.join(J, "runs.log")).read().split() if os.path.exists(os.path.join(J, "runs.log")) else []
blocks = []
for u in units:
    name, kind = u[len("sdcore-job-"):].rsplit(".", 1)
    known = os.path.exists(os.path.join(J, "state", name + ".json"))
    if kind == "timer":
        vals = {"NextElapseUSecRealtime": "Tue 2026-11-03 02:30:00 UTC" if known else "", "ActiveState": "active" if known else "inactive", "Result": "success"}
    else:
        vals = {"ActiveState": "inactive", "ExecMainExitTimestamp": "Mon 2026-11-02 12:00:00 UTC" if name in runs else "", "Result": "success"}
    blocks.append("\n".join("%%s=%%s" %% (p, vals[p]) for p in props if p in vals))
print("\n\n".join(blocks))
'''


def arow(rid, name, ok, detail=""):
    row("%s %s" % (rid, name), ok, detail)
    if not ok:
        FAILED_IDS.append(rid)


def norm(t):
    return re.sub(r"[|\s─-╿]+", " ", t)          # 2 Nov 26: box-drawing characters too, so a line the box wraps reads as one


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


def setup_jobs():
    """The shim, the fake systemctl and their scratch directory; the sandbox's set_job pointed at them (the two lines that differ from the shipped program, each found once)."""
    global JOBS
    JOBS = os.path.join(sh.BOX, "jobs")
    if os.path.exists(JOBS):
        shutil.rmtree(JOBS)
    os.makedirs(os.path.join(JOBS, "state"))
    for name, text in (("elevate-shim", SHIM % {"jobs": JOBS, "elevate": os.path.join(HERE, "sd-elevate")}), ("systemctl", SYSTEMCTL % {"jobs": JOBS})):
        g.put(os.path.join(JOBS, name), text)
        os.chmod(os.path.join(JOBS, name), 0o755)
    g.put(os.path.join(JOBS, "calls.log"), "")
    with open(os.path.join(TREE, "sdsys", "gpl.bp", "set_job"), encoding="utf-8", errors="replace") as f:
        src = f.read()
    for old, new in (("'sudo -n /usr/local/sbin/sd-elevate'", "'%s'" % os.path.join(JOBS, "elevate-shim")), ("/usr/bin/systemctl", os.path.join(JOBS, "systemctl"))):
        if src.count(old) != 1:
            bail("the tree's set_job has %r %d times, not once" % (old, src.count(old)))
        src = src.replace(old, new)
    g.put(os.path.join(sh.SYS, "gpl.bp", "set_job"), src)
    say("  [setup] the sandbox's set_job: the helper is %s (the real sd-elevate's dry run, then scratch files), systemctl is %s" % (os.path.join(JOBS, "elevate-shim"), os.path.join(JOBS, "systemctl")))


def calls():
    with open(os.path.join(JOBS, "calls.log")) as f:
        return [ln.strip() for ln in f.read().splitlines() if ln.strip()]


def job_state():
    st = os.path.join(JOBS, "state")
    return sorted(os.listdir(st))


def setup_page():
    setup_jobs()
    for prog in ("set_batch", "set_job", "tool_jobs"):
        if prog != "set_job":
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


# ------------------------------------------------------------------------------------------------- section admin (S.102 stage 4)

def jtext(p):
    """The Jobs box's rows and the status line, as one normalised string"""
    return p.text()


def set_job_out(cmds):
    out = g.adm(cmds)
    return [sh.g.ANSI.sub("", ln) for ln in out]


def section_k0_k2():
    say("\n--- K0-K2: set.job at the prompt")
    out = g.plain("zzhd", ["set.job"])
    T = norm(" ".join(out))
    arow("K0", "an ordinary session is told set.job is not a command, and no list appears", "not in your VOC" in T and "scheduled job" not in T, T[:300])
    a0 = audit_off()
    c0 = len(calls())
    cases = [("set.job add b_d update-accounts hourly", r"^b_d is not a job name"),
             ("set.job add -x update-accounts hourly", r"^-x is not a job name"),
             ("set.job add a- update-accounts hourly", r"^a- is not a job name"),
             ("set.job add %s update-accounts hourly" % ("a" * 33), r"is not a job name"),
             ("set.job add nightly rm hourly", r"^rm is not a job: a job is backup-all"),
             ("set.job add nightly update-accounts every 7 minutes", r"^The schedule is none of"),
             ("set.job add nightly update-accounts daily 24:00", r"^The schedule is none of"),
             ("set.job add nightly update-accounts monthly 31 01:00", r"^The schedule is none of"),
             ("set.job add nightly update-accounts weekly sunday 03:00", r"^The schedule is none of"),
             ("set.job delete", r"^set\.job \{add \| change\} name job schedule"),
             ("set.job run a b", r"^set\.job \{add \| change\} name job schedule"),
             ("set.job stop nightly", r"^set\.job \{add \| change\} name job schedule")]
    bad = []
    for cmd, rx in cases:
        out = set_job_out([cmd])
        if not has(out, rx):
            bad.append((cmd, out[-3:]))
    arow("K1a", "set.job refuses a bad name, a job that is not one of the four, a schedule of none of the five shapes and a wrong form, each with its own message (%d cases)" % len(cases),
         not bad, repr(bad[:3]))
    c1 = len(calls())
    arow("K1b", "none of the refused forms asked the helper anything, and none wrote a set.job audit line", calls()[c0:] == [] and "set.job " not in audit_new(a0), repr((calls()[c0:], audit_new(a0)[-200:])))
    out = set_job_out(["set.job"])
    arow("K2", "set.job alone with no job asks the helper job-list and says no scheduled job is defined", has(out, r"^No scheduled job is defined$") and calls()[c1:] == ["job-list"], repr((out[-3:], calls()[c1:])))


def fill(p, vals, defaults):
    """The form: each entry's default taken off with Backspace and the value typed, Tab between them, Return presses the default button"""
    s = "\t".join("\x7f" * len(d) + v for v, d in zip(vals, defaults)) + "\r"
    p.h.typed(s, idle=1.5)


def section_k3_k10():
    say("\n--- K3-K10: the Jobs view")
    p = Page()
    p.key("j", 3.0)
    T = p.text()
    if "Scheduled jobs of the administrator" not in T:
        dump(p.h)
        bail("J did not show the Jobs view, so no row below can be believed")
    arow("K3", "J shows the Jobs view; it read the list (the helper was asked job-list) and says no job is scheduled", "No job is scheduled" in T and calls()[-1:] == ["job-list"], repr((T[:400], calls()[-2:])))

    say("\n--- K4: the form refuses before anything is asked")
    c0 = len(calls())
    p.key("n", 1.5)
    fill(p, ["nightly", "backup-all", "every 7 minutes"], ["", "update-accounts", "daily 02:30"])
    T = p.text()
    ok1 = "the schedule is every 5 10 15 20 30 minutes" in T and not box_open(T)        # norm() reads the bars of 5|10|15 as the box's own
    p.key("esc", 1.0)
    p.key("n", 1.5)
    fill(p, ["Bad-", "backup-all", "daily 02:30"], ["", "update-accounts", "daily 02:30"])
    T = p.text()
    ok2 = "a job name is 1 to 32 characters" in T and not box_open(T)
    p.key("esc", 1.0)
    arow("K4", "the form refuses a schedule of none of the five shapes and a bad name, says so in the form and asks the helper nothing", ok1 and ok2 and calls()[c0:] == [], repr((ok1, ok2, calls()[c0:])))

    say("\n--- K5-K6: N, then Run")
    a0 = audit_off()
    p.key("n", 1.5)
    fill(p, ["nightly", "backup-all", "daily 02:30"], ["", "update-accounts", "daily 02:30"])
    T = p.text()
    arow("K5a", "the box names the whole sentence 'set.job add nightly backup-all daily 02.30', the command backup.account all and the schedule in words",
         box_open(T) and "set.job add nightly backup-all daily 02.30" in T and "backup.account all" in T and "every day at 02:30" in T, T[-900:])
    p.key("esc", 1.2)
    arow("K5b", "Esc asks nothing of the helper and writes no audit line", calls()[c0:] == [] and "set.job " not in audit_new(a0), repr(calls()[c0:]))
    p.key("n", 1.5)
    fill(p, ["nightly", "backup-all", "daily 02:30"], ["", "update-accounts", "daily 02:30"])
    p.key("r", 5.0)
    new = audit_new(a0)
    T = p.text()
    arow("K6a", "Run: set.job asked job-list, then job-set nightly backup-all daily 02:30 (the time with its colon), then the page read the list again",
         calls()[c0:] == ["job-list", "job-set nightly backup-all daily 02:30", "job-list"], repr(calls()[c0:]))
    arow("K6b", "the audit trail has 'set.job add name=nightly job=backup-all result=done schedule=daily 02:30'",
         re.search(r"set\.job add name=nightly job=backup-all result=done schedule=daily 02:30$", new, re.M) is not None, repr(new[-300:]))
    arow("K6c", "the row shows nightly, its schedule, its command, the next run systemd gave and no last run",
         re.search(r"nightly daily 02:30 backup\.account all Tue 2026-11-03 02:30:00 UTC never", T) is not None, repr(T[:600]))

    say("\n--- K7: N with a name that exists")
    c1 = len(calls())
    p.key("n", 1.5)
    fill(p, ["nightly", "update-accounts", "hourly"], ["", "update-accounts", "daily 02:30"])
    T = p.text()
    arow("K7", "the form refuses the name of a job that exists (C changes it) and asks the helper nothing", "a job named nightly exists" in T and not box_open(T) and calls()[c1:] == [], repr((T[-400:], calls()[c1:])))
    p.key("esc", 1.0)

    say("\n--- K8: C")
    a1 = audit_off()
    p.key("c", 1.5)
    fill(p, ["backup-all", "weekly sun 03:00"], ["backup-all", "daily 02:30"])
    T = p.text()
    ok_box = box_open(T) and "set.job change nightly backup-all weekly sun 03.00" in T and "every Sunday at 03:00" in T and "It replaces what nightly does now" in T
    p.key("r", 5.0)
    arow("K8", "C: the box names 'set.job change nightly backup-all weekly sun 03.00', the schedule in words and what it replaces; Run asks job-set with the new schedule, audited",
         ok_box and calls()[c1:] == ["job-list", "job-set nightly backup-all weekly sun 03:00", "job-list"]
         and re.search(r"set\.job change name=nightly job=backup-all result=done schedule=weekly sun 03:00$", audit_new(a1), re.M) is not None, repr((ok_box, calls()[c1:], T[-600:])))

    say("\n--- K9: R")
    c2 = len(calls())
    a2 = audit_off()
    p.key("r", 1.5)
    T = p.text()
    ok_box = box_open(T) and "set.job run nightly" in T and "exactly as its timer would" in T
    if ok_box:
        p.key("r", 5.0)
    T = p.text()
    arow("K9", "R: the box names 'set.job run nightly'; Run asks job-list (set.job refuses a damaged job first) then job-run nightly once, the audit has the run line, "
         "and the row's last run is what systemd now says",
         ok_box and calls()[c2:] == ["job-list", "job-run nightly", "job-list"] and re.search(r"set\.job run name=nightly result=done$", audit_new(a2), re.M) is not None
         and "Mon 2026-11-02 12:00:00 UTC (success)" in T, repr((ok_box, calls()[c2:], T[:600])))

    say("\n--- K10: D")
    c3 = len(calls())
    p.key("d", 1.5)
    T = p.text()
    ok_box = box_open(T) and "set.job delete nightly" in T
    p.key("r", 1.5)
    p.h.typed("nope\r", idle=1.5)
    wrong_none = calls()[c3:] == [] and job_state() == ["nightly.json"]
    p.key("d", 1.5)
    p.key("r", 1.5)
    p.h.typed("nightly\r", idle=5.0)
    T = p.text()
    arow("K10", "D: the box names 'set.job delete nightly' and asks for the name; a wrong name asks the helper nothing; the right one asks job-delete nightly and the job is gone",
         ok_box and wrong_none and calls()[c3:] == ["job-delete nightly", "job-list"] and job_state() == [] and "No job is scheduled" in T, repr((ok_box, wrong_none, calls()[c3:], job_state())))
    return p


def section_k11_k12(p):
    say("\n--- K11: a damaged definition")
    g.put(os.path.join(JOBS, "state", "zbad.damaged"), "")
    p.key("f5", 3.0)
    c0 = len(calls())
    T = p.text()
    shown = re.search(r"zbad damaged: the definition does not agree with the helper", T) is not None
    p.key("r", 1.5)
    arow("K11", "a damaged definition is shown as damaged and R refuses it on the status line without a box and without asking the helper",
         shown and "a damaged job cannot be run" in norm(p.st()) and not box_open(p.text()) and calls()[c0:] == [], repr((shown, p.st(), calls()[c0:])))
    os.remove(os.path.join(JOBS, "state", "zbad.damaged"))
    # 2 Nov 26 (the review): a damaged FILE whose name is not a job name - C must not open a form that could never be sent
    g.put(os.path.join(JOBS, "state", "Zbad.damaged"), "")
    p.key("f5", 3.0)
    p.walk_to("Zbad")              # the status line below names the job C acted on (jnm<ji>), which is the evidence that the cursor was on Zbad
    c0 = len(calls())
    p.key("c", 1.5)
    T = p.text()
    found = "Zbad" in T
    arow("K11b", "C on a damaged file named Zbad (not a job name) opens no form: the status line names the prompt command set.job delete Zbad, and the helper is asked nothing",
         found and "set.job delete Zbad" in norm(p.st()) and "Change the job Zbad" not in T and not box_open(T) and calls()[c0:] == [], repr((found, p.st(), calls()[c0:])))
    if "Change the job Zbad" in T:
        p.key("esc", 1.0)
    os.remove(os.path.join(JOBS, "state", "Zbad.damaged"))
    p.key("f5", 3.0)
    p.key("f1", 1.2)
    arow("K12a", "F1 in the Jobs view reaches the help box (a sandbox has no shared account: help is not installed here)", "Help is not installed here" in p.text(), p.text()[-300:])
    p.key("esc", 1.0)
    p.quit()

    say("\n--- K12: set.job at the prompt, against jobs that exist and a helper that fails")
    g.put(os.path.join(JOBS, "state", "zone.json"), '{"id": "update-accounts", "cmd": "update.accounts all", "sched": "hourly"}')
    c1 = len(calls())
    out1 = set_job_out(["set.job add zone backup-all hourly"])
    out2 = set_job_out(["set.job change znone backup-all hourly"])
    arow("K12b", "add of a job that exists says 11302 and change of a missing one 11319, each having asked only job-list",
         has(out1, r"^A job named zone already exists; nothing was changed") and has(out2, r"^No job is named znone; nothing was changed") and calls()[c1:] == ["job-list", "job-list"],
         repr((out1[-2:], out2[-2:], calls()[c1:])))
    out = set_job_out(["set.job"])
    arow("K12c", "set.job alone lists the job with its next run and its last run", has(out, r"^job zone: hourly: update\.accounts all \(update-accounts\)$")
         and has(out, r"^\s*next run: Tue 2026-11-03 02:30:00 UTC; last run: never$"), repr(out[-4:]))
    a0 = audit_off()
    g.put(os.path.join(JOBS, "inject"), "job-set")
    out = set_job_out(["set.job change zone backup-all daily 05.15"])
    new = audit_new(a0)
    arow("K12d", "a helper that fails: set.job prints what it said and 11332, the audit line says result=failed, and the job is unchanged",
         has(out, r"^shim: injected failure$") and has(out, r"^The root helper did not do it \(status \d+\)$")
         and re.search(r"set\.job change name=zone job=backup-all result=failed status=\S+ schedule=daily 05:15$", new, re.M) is not None
         and '"update-accounts"' in open(os.path.join(JOBS, "state", "zone.json")).read(), repr((out[-3:], new[-300:])))
    out = set_job_out(["set.job delete zone"])
    arow("K12e", "set.job delete at the prompt is judged on the helper's own line: job zone deleted", has(out, r"^sd-elevate: job zone deleted$") and job_state() == [], repr(out[-3:]))
    # 2 Nov 26 (the review): the helper's description of what it is about to do is not shown; set.job run of a damaged job is refused before job-run
    arow("K12g", "the helper's description lines (job-delete zone: first: ..., then: ...) are not shown, only what it did (the shim printed both: the dry run's own lines)",
         not has(out, r"job-delete zone:") and not has(out, r"^sd-elevate: then:") and has(out, r"^sd-elevate: job zone deleted$"), repr(out[-4:]))
    g.put(os.path.join(JOBS, "state", "zrun.damaged"), "")
    c2 = len(calls())
    out = set_job_out(["set.job run zrun"])
    arow("K12f", "set.job run of a job the list shows as damaged says 11333 and asks the helper only job-list (never job-run)",
         has(out, r"^Job zrun is damaged; nothing was started") and calls()[c2:] == ["job-list"] and "zrun" not in " ".join(open(os.path.join(JOBS, "runs.log")).read().split() if os.path.exists(os.path.join(JOBS, "runs.log")) else []),
         repr((out[-3:], calls()[c2:])))
    os.remove(os.path.join(JOBS, "state", "zrun.damaged"))


def main():
    mutant = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mutant=")), None)
    only = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--only=")), "account,admin")
    sections = [s for s in only.split(",") if s]
    if (mutant is not None and mutant not in MUTANTS) or not sections or any(s not in ("account", "admin") for s in sections):
        bail("usage: sandbox-tool-jobs.py <dir> [--build] [--only=account|admin|account,admin] [--mutant=%s]" % "|".join(MUTANTS))
    last = MUTANTS[mutant][3] if mutant else "J6"
    if mutant is not None:
        sections = ["admin"] if last == "admin" else ["account"]
    order = ["J2", "J3", "J4", "J5", "J6"]
    say("sandbox-tool-jobs: sections %s" % ", ".join(sections))
    try:
        sh.setup("sandbox-tool-jobs.py")
        setup_page()
        if mutant is not None:
            mutate(mutant)
            say("sandbox-tool-jobs: MUTANT %s: the rows that must fail, and nothing else: %s" % (mutant, ", ".join(MUTANTS[mutant][2])))
        if "account" in sections:
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
        if "admin" in sections:
            if mutant is None:
                section_k0_k2()
            p = section_k3_k10()
            if mutant is None:
                section_k11_k12(p)
            else:
                p.quit()
    finally:
        sh.teardown()
    say("\nsandbox-tool-jobs: %d passed, %d failed" % (sh.tkb.passed, sh.tkb.failed))
    if mutant is not None:
        want = sorted(set(MUTANTS[mutant][2]))
        got = sorted({re.match(r"[JK]\d+", i).group(0) for i in FAILED_IDS})
        ok = want == got
        say("sandbox-tool-jobs: MUTANT %s: the rows that failed are %s; they had to be exactly %s -> %s" % (mutant, got, want, "KILLED BY ITS OWN ROWS" if ok else "NOT AS EXPECTED"))
        return 0 if ok else 1
    return 0 if sh.tkb.failed == 0 and sh.tkb.passed > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
