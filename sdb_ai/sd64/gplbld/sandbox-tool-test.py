#!/usr/bin/env python3
#
# sandbox-tool-test.py - TOOL.TEST, the test runner of the account ($tool_test, S.75 DV7), driven on a PSEUDO-TERMINAL as ORDINARY sessions on a private SD.  No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-tool-test.py <dir> [--build] [--mutants | --mutant=NAME]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Without --build the page is copied
# from the tree into the built sandbox and compiled there first.  Exit 0 every row passed, 1 a row failed, 2 it could not run.  With --mutant=NAME (or --mutants for all of them) one
# change is made to the SANDBOX'S OWN COPY of the page, and exit 0 means the rows that had to fail failed and no others.
#
# START-HISTORY:
# 25 Oct 26 dm  New (S.75 DV7).
# END-HISTORY
#
# WHAT RUNS.  Two fixture accounts with their register records written by hand: zztl1 with the edit gates (voc, bp, dict) ON and zztl2 with them OFF.  In zztl1 a program file bp and a
# program file src.bp (each with a .out beside it once compiled) hold the fixture tests, whose sources are written to the disk by this suite: each logs a line in the data file zzlog
# FIRST (a record per test, a count of its runs), then prints what its name says it does (passes, fails, prints no verdict, aborts, asks for input, prints 20,000 lines, sleeps, never
# ends).  Controls that must NOT be listed: a record in bp that does not start with test. (testing, mytest.x), and a directory file called lib that holds test.lib.  An ORDINARY session
# (sd -a<account>, as the sandbox user, not an administrator) types TOOL.TEST.
#
# THE INSTRUMENT.  Every outcome is read from the DISK or from SD, not from what the page said: the count of runs of each test is read from zzlog by a SEPARATE ordinary session before and
# after the page's action (so "run once", "the failed ones only" and "the second test never ran" are counts), the object code is looked for on the disk, and the page's verdict of a test
# is compared with an INDEPENDENT run of the same program in a separate session, judged by a copy of the rule written here in Python (the page and this file do not share the rule).
# A test that asks for input is not run independently (a piped session would answer it with the next command line); the answer it was given is written by the test itself to zzlog.
#
#   T1      the page draws for an ordinary account; the list holds the test.* records of bp and src.bp and nothing else (the controls are absent), with the object column, the result
#           column and the summary under the list; the gate line for an account with bp-edit on and one with it off
#   T2      R on a passing test: run once (the count), pass, 3 passed 0 failed, the box under the list says so, an independent run agrees
#   T3      the verdicts: a name before the numbers, a failure, no verdict (hello; nothing at all; 0 passed 0 failed), an abort (told by the system's message, the output being thrown
#           away), a test that asks for input (given an empty answer, the leftovers discarded), 20,001 lines (cut to 400, judged on all of them)
#   T6      Enter shows the output in the lower box and scrolls; the marker line of a cut output; Esc comes back; the function-key row of each pane
#   T4      A runs every test shown, once each, in order, with the running one marked; the summary in the status line
#   T5      F runs again only the ones that failed (the count of runs), and says so when none has
#   T7      B compiles a test with no object code after a box (Cancel is the default); an account with bp-edit off meets the compiler's refusal and no object is made
#   T8      a name the page does not give to a command (TEST.UP): listed, not run, not compiled, and A leaves it out
#   T9      the filter keeps the results; F5 reads the program files again (a new test appears) and keeps the results
#   T10     Esc stops A after the test that is running (the later tests are never run)
#   T11     a test that does not end is stopped with Ctrl-C and Q, the page comes back, Ctrl-C is a key of the page again
#   T12     F1 and the [?] reach the help box; a window under 140 by 43 gets no page
import importlib.util
import os
import re
import shutil
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


sh = _load("sandbox_home_for_test", "sandbox-home.py")
say, row, bail, has, dump, adm, H, g = sh.say, sh.row, sh.bail, sh.has, sh.dump, sh.adm, sh.H, sh.g
sh.KEYS["f1"] = "\x1b[[A"
sh.KEYS.setdefault("esc", "\x1b")
FAILED_IDS = []
A1, A2 = "zztl1", "zztl2"
ME = os.environ.get("USER") or os.getlogin()
SCREEN = [None]      # the pty session of the section running: a failed row prints what it was looking at


def arow(rid, name, ok, detail=""):
    row("%s %s" % (rid, name), ok, detail)
    if not ok:
        FAILED_IDS.append(rid)
        if SCREEN[0] is not None:
            say("    --- the screen at the failure of %s ---" % rid)
            dump(SCREEN[0])


PAGE = "tool_test"


def page_path():
    return os.path.join(sh.SYS, "gpl.bp", PAGE)


# name: (old text of the sandbox's tool_test, new text, the row ids that must fail and no others, the sections to run)
MUTANTS = {
    "fail-judged-pass": ("               case nf > 0\n                  zstate = 'fail'\n", "               case nf > 9999999\n                  zstate = 'fail'\n", ["T3b", "T3b2"], ["verdicts"]),
    "abort-not-told": ("      if @abort.message # sentinel then\n         zstate = 'fail'", "      if @abort.message # @abort.message then\n         zstate = 'fail'", ["T3f", "T3g", "T3g2"], ["verdicts"]),
    "failed-runs-all": ("                  if rz(rp)<1> = 'fail' then queue<-1> = zk", "                  if rz(rp)<1> # 'zzz' then queue<-1> = zk", ["T5a", "T5b", "T5c"], ["all"]),
    "name-guard-off": ("      case tok<ri> = 0\n         msg = 'this name has a character the page does not give to a command: type run '",
                       "      case tok<ri> = 99\n         msg = 'this name has a character the page does not give to a command: type run '", ["T8a"], ["names"]),
    "break-not-enabled": ("   void pterm(PT$BREAK, @true)\n   break on\n   t0 = time()", "   t0 = time()", ["T11b", "T11c", "T11d", "T11e"], ["break"]),
}


def acct_dir(a):
    return os.path.join(sh.BOX, "user_accounts", a)


def reg_record(name, edit):
    e = "yes" if edit else "no"
    return [acct_dir(name), "", g.GROUP, "", "", "", "no", "no", "no", e, e, e, "", "", "no", "", "", ""]


def sync_page():
    shutil.copy(os.path.join(TREE, "sdsys", "gpl.bp", PAGE), page_path())


def compile_page():
    out = adm("BASIC gpl.bp " + PAGE)
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("%s did not compile in the sandbox:\n%s" % (PAGE, "\n".join(out[-8:])))
    if has(out, r"is not assigned a value"):
        bail("%s compiled with a warning that a constant is not assigned a value:\n%s" % (PAGE, "\n".join(out[-8:])))


def mutate(name):
    old, new, _kills, _secs = MUTANTS[name]
    src = open(page_path(), encoding="utf-8", errors="replace").read()
    if src.count(old) != 1:
        bail("mutant %s: the text to change is found %d times, not once" % (name, src.count(old)))
    g.put(page_path(), src.replace(old, new))
    compile_page()


# ---------------------------------------------------------------------------------------------------------------------------------- the fixture tests

LOG = ["   open 'zzlog' to lf else crt 'NO-ZZLOG' ; stop",
       "   read n from lf, '%(id)s' else n = 0",
       "   n += 1",
       "   write n on lf, '%(id)s'"]


def source(tid, lines):
    return "\n".join([l % {"id": tid} for l in LOG] + lines + ["end", ""])


def verdict(n_pass, n_fail):
    return ["   crt '%s passed, %s failed'" % (n_pass, n_fail)]


# id: (the lines after the log, whether the suite compiles it)
TESTS = {
    "test.a.pass": (["   crt 'checking one'", "   crt 'checking two'"] + verdict(3, 0), True),
    "test.b.prefix": (["   crt 'running the cases'", "   crt 'sandbox-x: 12 passed, 0 failed'"], True),
    "test.c.fail": (["   crt 'row a FAIL'"] + verdict(2, 1), True),
    "test.d.nov": (["   crt 'hello'"], True),
    "test.e.empty": (["   x = 1"], True),
    "test.f.zero": (verdict(0, 0), True),
    "test.g.abort": (["   crt 'before the abort'", "   z = undefinedvar + 1"] + verdict(1, 0), True),
    "test.h.input": (["   crt 'asking'", "   input x", "   write 'got:':x on lf, 'test.h.input.got'", "   crt 'got [':x:']'",
                      "   if x = '' then crt '1 passed, 0 failed' else crt '0 passed, 1 failed'"], True),
    "test.i.long": (["   for i = 1 to 20000", "      crt 'line ':i", "   next i"] + verdict(1, 0), True),
    "test.j.noobj": (verdict(1, 0), False),
    "test.l.loop": (["   n = 0", "   loop", "      n += 1", "   repeat"], True),
    "test.y.1": (verdict(1, 0), True),
    "test.y.2": (verdict(1, 1), True),
    "test.y.3": (["   z = undefinedvar + 1"] + verdict(1, 0), True),
    "test.y.4": (verdict(4, 0), True),
    "test.y.5": (["   crt 'no verdict here'"], True),
    "test.y.noobj": (verdict(1, 0), False),
    "test.y.slow": (["   sleep 3"] + verdict(1, 0), True),
    "test.s.1": (["   sleep 3"] + verdict(1, 0), True),
    "test.s.2": (["   sleep 3"] + verdict(1, 0), True),
    "test.s.3": (["   sleep 3"] + verdict(1, 0), True),
}
CONTROLS_BP = {"testing": verdict(1, 0), "mytest.x": verdict(1, 0)}      # in bp, but they do not start with test.
EXPECTED = sorted(set(TESTS) | {"test.other", "TEST.UP"})                # what the page must list for zztl1 (test.other is in src.bp, TEST.UP is a record with capitals written to the disk)
CAP = "TEST.UP"


def runs(account):
    """{record id: value} of the data file zzlog, read by a SEPARATE ordinary session: the count of runs of each test (and what test.h.input was answered)"""
    g.put(os.path.join(acct_dir(account), "bp", "zztcnt"), "\n".join([
        "   open 'zzlog' to lf else crt 'RUNLOG[nofile]' ; stop",
        "   select lf to 9",
        "   loop",
        "      readnext id from 9 else exit",
        "      read v from lf, id then crt 'RUNLOG[':id:'=':v:']'",
        "   repeat", "end", ""]))
    out = g.plain(account, ["BASIC bp zztcnt", "RUN bp zztcnt"])
    res = {}
    for ln in out:
        m = re.match(r"^RUNLOG\[(.*?)=(.*)\]$", ln.strip())
        if m:
            res[m.group(1).lower()] = int(m.group(2)) if m.group(2).isdigit() else m.group(2)
    if has(out, r"RUNLOG\[nofile\]"):
        bail("zzlog is not there in %s" % account)
    return res


def delta(before, after, tid):
    return after.get(tid, 0) - before.get(tid, 0)


def indep(account, tid, fil="bp"):
    """the program run by a SEPARATE ordinary session (RUN FILE ID), what it printed: the lines that are the program's"""
    out = g.plain(account, ["RUN %s %s NO.PAGE" % (fil, tid)])         # NO.PAGE: 20,001 lines would otherwise stop at a page prompt and eat the next command line
    return [l for l in out if not l.startswith("sd: SANDBOX")]


VERD = re.compile(r"^(?:.*: )?(\d+) passed, (\d+) failed(?:[,.;) ].*)?$")


def expect_state(lines):
    """THE RULE, written here again and not shared with the page: what the page must say about a program, from what an independent run printed"""
    ne = [l.strip() for l in lines if l.strip()]
    if any("Unassigned variable" in l or "Divide by zero" in l for l in ne):
        return "fail: abort"
    if not ne:
        return "no verdict"
    m = VERD.match(ne[-1])
    if not m:
        return "no verdict"
    p, f = int(m.group(1)), int(m.group(2))
    if f > 0:
        return "fail"
    return "pass" if p > 0 else "no verdict"


def setup_tests():
    q = sh.g
    for a, edit in ((A1, True), (A2, False)):
        q.FIXTURES[a] = ("no", "no")
        q.build_account(a)
        q.reg_write(a, reg_record(a, edit))
    sync_page()
    compile_page()
    out = q.plain(A1, ["CREATE.FILE zzlog", "CREATE.FILE src.bp directory", "CREATE.FILE lib directory"])
    out += q.plain(A2, ["CREATE.FILE zzlog"])
    bp1 = os.path.join(acct_dir(A1), "bp")
    for tid, (lines, _c) in TESTS.items():
        q.put(os.path.join(bp1, tid), source(tid, lines))
    for tid, lines in CONTROLS_BP.items():
        q.put(os.path.join(bp1, tid), "\n".join(lines + ["end", ""]))
    q.put(os.path.join(acct_dir(A1), "src.bp", "test.other"), source("test.other", verdict(5, 0)))
    q.put(os.path.join(acct_dir(A1), "lib", "test.lib"), "\n".join(verdict(1, 0) + ["end", ""]))
    q.put(os.path.join(bp1, CAP), "\n".join(verdict(1, 0) + ["end", ""]))      # a record with capitals in its name: written to the disk, SD never makes one
    q.put(os.path.join(acct_dir(A2), "bp", "test.q.noobj"), source("test.q.noobj", verdict(1, 0)))
    names = [t for t, (_l, c) in TESTS.items() if c]
    for i in range(0, len(names), 7):
        o = q.plain(A1, ["BASIC bp " + " ".join(names[i:i + 7])])
        if not has(o, r"^Compiled \d+ program\(s\) with no errors"):
            bail("the fixture tests did not compile:\n" + "\n".join(o[-8:]))
    o = q.plain(A1, ["BASIC src.bp test.other"])
    if not has(o, r"^Compiled 1 program\(s\) with no errors"):
        bail("src.bp/test.other did not compile:\n" + "\n".join(o[-8:]))
    for tid, (_l, c) in TESTS.items():
        if c != os.path.exists(os.path.join(acct_dir(A1), "bp.out", tid)):
            bail("the object code of %s is %s on the disk, but should %sbe there" % (tid, "absent" if c else "present", "" if c else "not "))
    if not os.path.exists(os.path.join(acct_dir(A1), "src.bp.out", "test.other")):
        bail("src.bp.out/test.other is not on the disk after BASIC src.bp: %s" % sorted(os.listdir(acct_dir(A1))))
    r = runs(A1)
    if any(isinstance(v, int) and v for v in r.values()):
        bail("the fixture was run while it was made: %r" % r)


# ---------------------------------------------------------------------------------------------------------------------------------- the screen

def page(account, cols=140, rows=43):
    h = H(account=account, cols=cols, rows=rows)
    SCREEN[0] = h
    h.typed("tool.test\r", idle=3.5)
    return h


COL = {"file": (33, 47), "obj": (47, 55), "res": (55, 68), "pas": (68, 75), "fai": (75, 82), "sec": (82, 88), "ran": (90, 99), "lin": (99, 106)}


def table(h):
    """{name: (file, object, result, passed, failed, seconds, ran, lines)} from the rows of the first box, and the names in order"""
    out = {}
    order = []
    for n in range(3, 19):
        l = h.line(n)
        name = l[3:33].strip()
        if name:
            order.append(name)
            out[name] = tuple(l[a:b].strip() for a, b in (COL["file"], COL["obj"], COL["res"], COL["pas"], COL["fai"], COL["sec"], COL["ran"], COL["lin"]))
    return out, order


def lower(h):
    return [h.line(n)[3:138].rstrip() for n in range(24, 39)]


def st(h):
    return h.line(40)


def foot(h):
    return h.line(19)[3:138].rstrip()


def filt(h, text):
    h.typed("/", idle=0.8)
    h.typed(text + "\r", idle=1.0)


def until(h, pred, secs=20.0):
    """a test that the page runs prints nothing while it runs, so a wait for idle output is not a wait for the page: pump the pty until the screen satisfies pred"""
    end = time.time() + secs                     # a clock, not a count: a burst of output makes a pump return at once, and a count of pumps ran out in a second (T10, first run)
    while time.time() < end:
        if pred(h.text()):
            return True
        if h.s.exited:
            break
        h.s._pump(0.25)
    return pred(h.text())


def result_of(h, tid):
    return table(h)[0].get(tid, ("",) * 8)[2]


def run_one(h, tid, secs=60.0):
    """filter to one test and press R: wait until its row has a result; return (the row, the lower box, the status line)"""
    filt(h, tid)
    h.typed("r", idle=0.6)
    until(h, lambda t: result_of(h, tid) not in ("", "not run", "running"), secs)
    return table(h)[0].get(tid), lower(h), st(h)


# ---------------------------------------------------------------------------------------------------------------------------------- sections

def section_list():
    say("\n--- T1: the list, the summary, the gate")
    h = page(A1)
    T = h.text()
    if "The test under the cursor" not in T:
        dump(h)
        bail("tool.test never drew its page in an ordinary account, so no row below can be believed")
    tb, order = table(h)
    arow("T1", "the page draws for an ordinary account, for the audience %s@%s (the right end of row 0), and says whose tests these are" % (ME, A1),
         re.search(r"tool\.test\s+%s@%s" % (re.escape(ME), A1), h.line(0)) is not None and "Tests in %s" % A1 in T, repr(h.line(0)[100:]))
    h.key("end", idle=1.0)
    tb2, order2 = table(h)
    allt = dict(tb)
    allt.update(tb2)
    names = set(allt)
    arow("T1b", "the list holds exactly the test.* records of bp and src.bp (%d, TEST.UP with its capitals included) and none of the controls: testing and mytest.x (not test.), test.lib (a directory file called lib)" % len(EXPECTED),
         names == set(EXPECTED), repr((sorted(names - set(EXPECTED)), sorted(set(EXPECTED) - names))))
    arow("T1c", "...the program file column says bp for the bp tests and src.bp for test.other, which is the last row (the files are in the VOC's order)",
         allt.get("test.other", ("",))[0] == "src.bp" and order2[-1] == "test.other" and allt.get("test.a.pass", ("",))[0] == "bp", repr((allt.get("test.other"), order2[-3:])))
    ok_obj = all(allt[t][1] == ("yes" if TESTS[t][1] else "no") for t in TESTS if t in allt) and allt["test.other"][1] == "yes" and allt[CAP][1] == "no"
    arow("T1d", "the Object column is read from the .out file: yes for what the suite compiled (bp.out and src.bp.out), no for test.j.noobj, test.y.noobj and TEST.UP", ok_obj, repr({t: allt[t][1] for t in allt}))
    res_ok = allt["test.a.pass"][2] == "not run" and allt["test.j.noobj"][2] == "no object" and allt[CAP][2] == "by hand" and allt["test.y.noobj"][2] == "no object"
    arow("T1e", "...and the Result column of a test not run is 'not run', of one without object code 'no object', of one the page will not name in a command 'by hand'", res_ok, repr((allt["test.a.pass"][2], allt["test.j.noobj"][2], allt[CAP][2])))
    n = len(EXPECTED)
    F = foot(h)
    arow("T1f", "the summary under the list counts the tests and the files, nothing has been run, and the gate line says bp-edit on, asked of the system",
         F.startswith("%d tests in 2 program files:  0 pass, 0 fail, 0 no verdict, %d not run" % (n, n)) and "bp-edit on (B compiles)" in F, repr(F))
    h.key("home", idle=1.0)
    B = lower(h)
    first = table(h)[1][0]
    arow("T1g", "the box under the list describes the test under the cursor (the first): its program file, where its object code is, and that R runs it", B[0].startswith(first + "  -  in the program file") and any("Not run in this session" in x or "cannot be run yet" in x or "does not give this name" in x for x in B), repr(B[:3]))
    Fk = h.line(42)
    arow("T1h", "the function-key row of the Tests pane is made from the key table", Fk.startswith("F1 help  R run  A run all  F run failed  B compile  Enter output  F11 filter  F5 refresh  ^Q quit"), repr(Fk))
    h.key("ctrl-q", idle=1.2)
    h.end()
    h = page(A2)
    arow("T1i", "...and for an account with the edit gates OFF the gate line says bp-edit off", "bp-edit off (B compiles)" in foot(h), repr(foot(h)))
    h.key("ctrl-q", idle=1.2)
    h.end()


def check_one(rid, h, tid, want, np, nf, lines, extra_ok=True, note=""):
    """a run through R, judged from the page, the disk and an independent run.  want: the Result column"""
    before = runs(A1)
    row_, B, S = run_one(h, tid)
    after = runs(A1)
    d = delta(before, after, tid)
    ok = row_ is not None and row_[2] == want and row_[3] == str(np) and row_[4] == str(nf) and row_[7] == str(lines) and d == 1 and extra_ok
    arow(rid, "%s: R runs it ONCE (the count in zzlog went up by %d), the row says %s, passed %s, failed %s, %s lines%s" % (tid, d, want, np, nf, lines, note), ok, repr((row_, d, S[-100:])))
    return row_, B, S


def section_verdicts():
    say("\n--- T2 and T3: R, and the verdicts")
    h = page(A1)
    row_, B, S = check_one("T2", h, "test.a.pass", "pass", 3, 0, 3)
    arow("T2b", "...the box under the list says PASS - 3 passed, 0 failed, the command that ran, and the end of what it printed; the status line gives the same verdict",
         any(x.startswith("PASS - 3 passed, 0 failed.") for x in B) and any("Command: run bp test.a.pass" in x for x in B) and any("checking two" in x for x in B) and "test.a.pass: PASS - 3 passed, 0 failed." in S, repr((B[:8], S)))
    ind = indep(A1, "test.a.pass")
    arow("T2c", "...and an independent run in a separate session printed the same last line and is judged 'pass' by the suite's own copy of the rule", ind and ind[-1].strip() == "3 passed, 0 failed" and expect_state(ind) == "pass", repr(ind[-3:]))
    cases = [
        ("T3a", "test.b.prefix", "pass", 12, 0, 2, "a name and a colon before the numbers is allowed"),
        ("T3b", "test.c.fail", "fail", 2, 1, 2, "a failure"),
        ("T3c", "test.d.nov", "no verdict", "", "", 1, "no verdict line"),
        ("T3d", "test.e.empty", "no verdict", "", "", 0, "nothing printed at all"),
        ("T3e", "test.f.zero", "no verdict", 0, 0, 1, "0 passed, 0 failed is not a pass"),
    ]
    for rid, tid, want, np, nf, nl, what in cases:
        row_, B, S = check_one(rid, h, tid, want, np, nf, nl, note=" (%s)" % what)
        ind = indep(A1, tid)
        arow(rid + "2", "...an independent run is judged '%s' by the suite's own rule, as the page judged it" % want, expect_state(ind) == want and row_ is not None and row_[2] == want, repr((expect_state(ind), ind[-2:])))
    # the abort: the system throws the output away; the page tells it by the message
    before = runs(A1)
    row_, B, S = run_one(h, "test.g.abort")
    after = runs(A1)
    arow("T3f", "test.g.abort: the run aborted (an unassigned variable) - Result 'fail: abort', 0 lines (the system discards an aborted run's output), run once, and the box names the abort and where it happened",
         row_ is not None and row_[2] == "fail: abort" and row_[7] == "0" and delta(before, after, "test.g.abort") == 1 and any("FAIL - the run aborted: Unassigned variable UNDEFINEDVAR at line" in x for x in B) and "test.g.abort" in " ".join(B), repr((row_, B[:3])))
    ind = indep(A1, "test.g.abort")
    arow("T3g", "...an independent run printed the same abort message, and the suite's rule calls it 'fail: abort', as the page did", expect_state(ind) == "fail: abort" and row_ is not None and row_[2] == "fail: abort", repr(ind[-3:]))
    # the same abort with the page's Result read again after another run: a second abort is told again (the page sets its own message each time)
    filt(h, "test.g.abort")
    before = runs(A1)
    h.typed("r", idle=1.5)
    until(h, lambda t: delta(before, runs(A1), "test.g.abort") == 1 and result_of(h, "test.g.abort") == "fail: abort", 20)
    arow("T3g2", "...a SECOND run of the same test aborts the same way and is told as an abort again (the message is the same text as the first time)", result_of(h, "test.g.abort") == "fail: abort" and delta(before, runs(A1), "test.g.abort") == 1, repr(result_of(h, "test.g.abort")))
    # the test that asks for input
    before = runs(A1)
    row_, B, S = run_one(h, "test.h.input")
    after = runs(A1)
    arow("T3h", "test.h.input asks for input: the page does not hang, the test was given an EMPTY answer (the test wrote got: with nothing after it to zzlog), the verdict is pass, and the box says it asked once",
         row_ is not None and row_[2] == "pass" and after.get("test.h.input.got") == "got:" and delta(before, after, "test.h.input") == 1 and any("It asked for input 1 time and was given an empty answer each time." in x for x in B), repr((row_, after.get("test.h.input.got"), B[:5])))
    # the long output
    before = runs(A1)
    row_, B, S = run_one(h, "test.i.long", secs=90)
    after = runs(A1)
    ind = indep(A1, "test.i.long")
    arow("T3i", "test.i.long prints 20,001 lines: the page says pass (judged on the last line of ALL of them), 20001 lines, run once, and the box says the output is cut to the first 360 and the last 39",
         row_ is not None and row_[2] == "pass" and row_[7] == "20001" and delta(before, after, "test.i.long") == 1 and any("The output is cut: the first 360 and the last 39 of its 20001 lines are kept" in x for x in B), repr((row_, B[:6])))
    arow("T3i2", "...an independent run printed 20001 lines too and its last line is the verdict", len(ind) == 20001 and expect_state(ind) == "pass", repr((len(ind), ind[-1:])))
    section_output(h)
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_output(h):
    say("\n--- T6: Enter shows the output, scrolling")
    # the page is filtered to test.i.long and its result is in
    h.key("enter", idle=1.0)
    until(h, lambda t: "Output of test.i.long" in h.line(23), 10)
    T0 = h.line(23)
    arow("T6a", "Enter: the lower box becomes the output - title 'Output of test.i.long (lines 1 to 15 of 400 kept', the first row is line 1 of what it printed, the function-key row is the Output pane's",
         "Output of test.i.long  (lines 1 to 15 of 400 kept" in T0 and h.line(24)[3:20].strip() == "1  line 1" and h.line(42).startswith("F1 help  Esc tests  F5 refresh  ^Q quit"), repr((T0[:80], h.line(24)[:30], h.line(42))))
    h.key("down", idle=0.5)
    arow("T6b", "Down scrolls one line: lines 2 to 16", "(lines 2 to 16 of 400 kept" in h.line(23) and h.line(24)[3:20].strip() == "2  line 2", repr((h.line(23)[:80], h.line(24)[:30])))
    h.key("pgdn", idle=0.5)
    arow("T6c", "PgDn scrolls a page: lines 17 to 31", "(lines 17 to 31 of 400 kept" in h.line(23), repr(h.line(23)[:80]))
    h.key("home", idle=0.5)
    for _ in range(24):
        h.key("pgdn", idle=0.2)
    L = h.line(24)
    arow("T6d", "after 24 more pages the first row is line 361: the marker that says how many lines were left out (19602 of 20001 = 20001 - 360 - 39)", L[3:8].strip() == "361" and "... 19602 lines left out ..." in L, repr(L[:60]))
    h.key("end", idle=0.6)
    arow("T6e", "End shows the last page: lines 386 to 400, the last row is the verdict line, and the row before it is the last 'line' the test printed",
         "(lines 386 to 400 of 400 kept" in h.line(23) and h.line(38)[3:40].strip() == "400  1 passed, 0 failed" and h.line(37)[3:40].strip() == "399  line 20000", repr((h.line(23)[:80], h.line(37)[:40], h.line(38)[:40])))
    h.key("esc", idle=0.8)
    arow("T6f", "Esc comes back to the tests: the box is the test under the cursor again, the function-key row is the Tests pane's, the result of the test is still there",
         "The test under the cursor" in h.line(23) and h.line(42).startswith("F1 help  R run  A run all") and result_of(h, "test.i.long") == "pass", repr((h.line(23)[:50], h.line(42)[:40])))


def section_all():
    say("\n--- T4 and T5: A runs every test shown, F the failed ones")
    h = page(A1)
    filt(h, "test.y.")
    tb, order = table(h)
    base = runs(A1)
    h.typed("a", idle=1.0)
    Tbox = re.sub(r"[|\s]+", " ", h.text())
    arow("T4g", "A first shows a box (Run this command, the number of tests and the first commands) with Run and Cancel, before any test runs", "Run this command" in Tbox and "6 tests" in Tbox and "run bp test.y.1" in Tbox and "Cancel" in Tbox, Tbox[-500:])
    h.key("enter", idle=1.5)
    arow("T4h", "Enter is Cancel: nothing ran (the counts in zzlog did not move) and no test is running", all(delta(base, runs(A1), t) == 0 for t in TESTS) and "running run" not in st(h), repr(st(h)))
    h.typed("a", idle=1.0)
    h.typed("r", idle=0.5)
    saw = until(h, lambda t: "test 6 of 6: running run bp test.y.slow" in st(h), 60)
    mid = table(h)[0]
    arow("T4a", "A: while the sixth test (which sleeps 3 seconds) runs, the status line says 'test 6 of 6: running run bp test.y.slow' and its row says running", saw and mid.get("test.y.slow", ("",) * 8)[2] == "running", repr((st(h)[:90], mid.get("test.y.slow"))))
    until(h, lambda t: "ran 6 of 6" in st(h), 60)
    S = st(h)
    after = runs(A1)
    tb, order = table(h)
    arow("T4b", "...every runnable test was run EXACTLY ONCE (the counts in zzlog: y.1 to y.5 and y.slow went up by 1) and test.y.noobj, which has no object code, was not",
         all(delta(base, after, t) == 1 for t in ("test.y.1", "test.y.2", "test.y.3", "test.y.4", "test.y.5", "test.y.slow")) and delta(base, after, "test.y.noobj") == 0, repr({t: delta(base, after, t) for t in TESTS if t.startswith("test.y.")}))
    want = {"test.y.1": "pass", "test.y.2": "fail", "test.y.3": "fail: abort", "test.y.4": "pass", "test.y.5": "no verdict", "test.y.slow": "pass", "test.y.noobj": "no object"}
    arow("T4c", "...the Result column: pass, fail, fail: abort, pass, no verdict, pass, and no object for the one that was not run", {t: tb.get(t, ("",) * 8)[2] for t in want} == want, repr({t: tb.get(t, ("",) * 8)[2] for t in want}))
    arow("T4d", "...the status line sums up: ran 6 of 6: 3 pass, 2 fail, 1 no verdict; 1 without object code left out", "ran 6 of 6: 3 pass, 2 fail, 1 no verdict; 1 without object code left out" in S, repr(S))
    F = foot(h)
    arow("T4e", "...and the summary under the list counts the results of the session: 3 pass, 2 fail, 1 no verdict", "3 pass, 2 fail, 1 no verdict" in F, repr(F))
    bad = []
    for t, w in want.items():
        if t == "test.y.noobj":
            continue
        ind = indep(A1, t)
        if expect_state(ind) != w:
            bad.append((t, w, expect_state(ind)))
    arow("T4f", "...an independent run of each test in a separate session is judged by the suite's own rule exactly as the page judged it", not bad, repr(bad))
    # F: only the failed ones
    base = runs(A1)
    h.typed("f", idle=1.0)
    h.typed("r", idle=0.5)
    until(h, lambda t: "ran 2 of 2" in st(h), 40)
    after = runs(A1)
    S = st(h)
    arow("T5a", "F runs again only the tests that failed (y.2, and y.3 which aborted): their counts went up by 1 and y.1, y.4, y.5 and y.slow did not move",
         delta(base, after, "test.y.2") == 1 and delta(base, after, "test.y.3") == 1 and all(delta(base, after, t) == 0 for t in ("test.y.1", "test.y.4", "test.y.5", "test.y.slow")), repr({t: delta(base, after, t) for t in TESTS if t.startswith("test.y.")}))
    arow("T5b", "...and the status line says ran 2 of 2: 0 pass, 2 fail, 0 no verdict", "ran 2 of 2: 0 pass, 2 fail, 0 no verdict" in S, repr(S))
    filt(h, "test.y.1")
    base = runs(A1)
    h.typed("f", idle=1.5)
    arow("T5c", "F with a test shown that has not failed runs nothing and says so: 'no test shown has failed' (the count did not move)", "no test shown has failed" in st(h) and delta(base, runs(A1), "test.y.1") == 0, repr(st(h)))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_compile():
    say("\n--- T7: B compiles a test with no object code")
    h = page(A1)
    tid = "test.j.noobj"
    obj = os.path.join(acct_dir(A1), "bp.out", tid)
    filt(h, tid)
    base = runs(A1)
    h.typed("r", idle=1.2)
    arow("T7a", "R on a test with no object code does not run it: the status line says there is no object code and that B compiles it first, and the count did not move",
         "no object code for test.j.noobj: B compiles it first (basic bp test.j.noobj)" in st(h) and delta(base, runs(A1), tid) == 0, repr(st(h)))
    h.typed("b", idle=1.5)
    T = re.sub(r"[|\s]+", " ", h.text())
    arow("T7b", "B shows the command in a box with Run and Cancel before anything is compiled: basic bp test.j.noobj", "basic bp test.j.noobj" in T and "Run" in T and "Cancel" in T and not os.path.exists(obj), T[-400:])
    h.key("enter", idle=1.5)
    arow("T7c", "Enter is Cancel: nothing was compiled (no object code on the disk) and the row still says no object", not os.path.exists(obj) and result_of(h, tid) == "no object", repr((os.path.exists(obj), result_of(h, tid))))
    h.typed("b", idle=1.2)
    h.typed("r", idle=3.0)
    until(h, lambda t: os.path.exists(obj), 20)
    until(h, lambda t: table(h)[0].get(tid, ("",) * 8)[1] == "yes", 10)
    arow("T7d", "B, Run: the compiler ran - the object code is on the disk, the Object column says yes, and the status line gives the compiler's last line",
         os.path.exists(obj) and table(h)[0].get(tid, ("",) * 8)[1] == "yes" and "basic bp test.j.noobj: Compiled 1 program(s) with no errors" in st(h), repr((os.path.exists(obj), table(h)[0].get(tid), st(h))))
    before = runs(A1)
    h.typed("r", idle=1.0)
    until(h, lambda t: result_of(h, tid) == "pass", 20)
    arow("T7e", "R now runs it: pass, once", result_of(h, tid) == "pass" and delta(before, runs(A1), tid) == 1, repr((result_of(h, tid), delta(before, runs(A1), tid))))
    h.typed("b", idle=1.0)
    arow("T7f", "B on a test that has its object code says so and compiles nothing", "the object code is there already" in st(h) and "Run this command" not in h.text(), repr(st(h)))
    h.key("ctrl-q", idle=1.2)
    h.end()
    # the account whose bp-edit gate is off
    h = page(A2)
    tid2 = "test.q.noobj"
    obj2 = os.path.join(acct_dir(A2), "bp.out", tid2)
    filt(h, tid2)
    h.typed("b", idle=1.5)
    h.typed("r", idle=3.0)
    until(h, lambda t: st(h).strip() != "" and "Run this command" not in t, 20)
    S = st(h)
    arow("T7g", "an account with bp-edit OFF: B, Run - the compiler's own refusal comes back (the status line names the command and does not say Compiled), and no object code was made",
         not os.path.exists(obj2) and "basic bp test.q.noobj:" in S and "Compiled 1 program" not in S, repr((os.path.exists(obj2), S)))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_names():
    say("\n--- T8: a name the page does not give to a command")
    h = page(A1)
    filt(h, "test.up")
    tb, order = table(h)
    base = runs(A1)
    h.typed("r", idle=1.5)
    S1 = st(h)
    arow("T8a", "TEST.UP (capitals) is listed as 'by hand'; R says the name has a character the page does not give to a command and shows what to type, and no box or run happens",
         order == [CAP] and tb[CAP][2] == "by hand" and "does not give to a command" in S1 and "run bp TEST.UP" in S1 and "Run this command" not in h.text(), repr((order, tb.get(CAP), S1)))
    h.typed("b", idle=1.5)
    S2 = st(h)
    arow("T8b", "B on it says the same with basic, and shows no box", "does not give to a command" in S2 and "basic bp TEST.UP" in S2 and "Run this command" not in h.text(), repr(S2))
    h.typed("a", idle=1.5)
    arow("T8c", "A with only that test shown has nothing to run and says so", "nothing to run" in st(h), repr(st(h)))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_refresh():
    say("\n--- T9: the filter and F5 keep the results")
    h = page(A1)
    row_, B, S = run_one(h, "test.a.pass")
    name = "test.n.new"
    g.put(os.path.join(acct_dir(A1), "bp", name), source(name, verdict(1, 0)))
    o = g.plain(A1, ["BASIC bp " + name])
    h.key("f5", idle=1.5)
    arow("T9a", "F5 reads the program files again and says the results are kept: test.a.pass still says pass", "read the program files again; the results are kept" in st(h) and result_of(h, "test.a.pass") == "pass", repr((st(h), result_of(h, "test.a.pass"))))
    filt(h, "test.n.")
    tb, order = table(h)
    arow("T9b", "...a test written and compiled after the page started is in the list now, with its object code and not run", order == [name] and tb[name][1] == "yes" and tb[name][2] == "not run", repr((order, tb.get(name), o[-2:])))
    h.key("esc", idle=1.0)
    tb, order = table(h)
    arow("T9c", "Esc clears the filter: all the tests are listed again", len(order) >= 16, repr(order))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_stop():
    say("\n--- T10: Esc stops A after the test that is running")
    h = page(A1)
    filt(h, "test.s.")
    base = runs(A1)
    h.typed("a", idle=1.0)
    h.typed("r", idle=0.5)
    until(h, lambda t: "test 1 of 3: running run bp test.s.1" in st(h), 30)
    t_esc = time.time()
    h.s.type("\x1b", idle=0.2)
    stopped = until(h, lambda t: "stopped with Esc" in st(h), 40)
    S = st(h)
    say("    (T10: Esc typed, the page stopped after %.1f s: %s; the session has %s)" % (time.time() - t_esc, "seen" if stopped else "NOT seen", "ended" if h.s.exited else "not ended"))
    time.sleep(4)
    after = runs(A1)
    arow("T10", "A on three tests that sleep 3 seconds each, Esc pressed during the first: the first finished and the later two were never run (counts 1, 0, 0, four seconds later), and the status line says it stopped after test 1",
         delta(base, after, "test.s.1") == 1 and delta(base, after, "test.s.2") == 0 and delta(base, after, "test.s.3") == 0 and "ran 1 of 3" in S and "stopped with Esc after test 1" in S, repr((S, {t: delta(base, after, t) for t in ("test.s.1", "test.s.2", "test.s.3")})))
    h.key("ctrl-q", idle=1.2)
    h.end()


def section_break():
    say("\n--- T11: a test that does not end")
    h = page(A1)
    filt(h, "test.l.loop")
    base = runs(A1)
    h.typed("r", idle=0.8)
    ok_a = until(h, lambda t: "running run bp test.l.loop - Ctrl-C then Q stops a test that does not end" in st(h), 15) and delta(base, runs(A1), "test.l.loop") == 1
    arow("T11a", "R on a test that never ends: the page shows it running and says how to stop it (Ctrl-C then Q); the test did start (the count went up)", ok_a, repr(st(h)))
    time.sleep(1.0)
    h.s.type("\x03", idle=1.0)
    prompt = until(h, lambda t: "A to abort, Q to Quit" in t, 8)
    arow("T11b", "Ctrl-C reaches the system's break prompt (A to abort, Q to Quit ...) while the test runs", prompt, repr(h.text()[-300:]))
    h.s.type("q", idle=1.0)
    back = until(h, lambda t: "The test under the cursor" in t and "running run bp test.l.loop" not in st(h) and result_of(h, "test.l.loop") != "running", 10)
    res = result_of(h, "test.l.loop")
    say("    (what Q left behind: the Result column says %r, the status line %r)" % (res, st(h)[:110]))
    arow("T11c", "Q gives the page back: the page is drawn again, the row is not 'running' any more (it says %r) and the test is not left running" % res, back and res in ("no verdict", "fail: abort", "fail"), repr((res, st(h))))
    h.s.type("\x03", idle=1.0)
    h.key("f5", idle=1.5)
    arow("T11d", "afterwards Ctrl-C does nothing on the page (the break key is turned off again): no break prompt, and the page answers a key (F5 reads the program files again)",
         "A to abort, Q to Quit" not in h.text() and "read the program files again; the results are kept" in st(h), repr((st(h), h.text()[-200:])))
    before = runs(A1)
    row_, B, S = run_one(h, "test.a.pass")
    arow("T11e", "the page runs another test after that: test.a.pass passes", row_ is not None and row_[2] == "pass" and delta(before, runs(A1), "test.a.pass") == 1, repr((row_, S[-90:])))
    h.key("ctrl-q", idle=1.5)
    h.end()


def section_other():
    say("\n--- T12: help and a small window")
    h = page(A1)
    arow("T12a", "a [?] at the end of the first box", h.line(2)[134:137] == "[?]", repr(h.line(2)[130:139]))
    h.click(135, 2)
    T = re.sub(r"[|\s]+", " ", h.text())
    arow("T12b", "a click on the [?] reaches the help box ($tk_help answers that help is not installed here: a sandbox has no shared account)", "Help is not installed here" in T, T[-400:])
    h.key("esc", idle=1.0)
    h.key("f1", idle=1.2)
    T = re.sub(r"[|\s]+", " ", h.text())
    arow("T12c", "F1 reaches it too", "Help is not installed here" in T, T[-400:])
    h.key("esc", idle=1.0)
    h.key("ctrl-q", idle=1.2)
    h.end()
    h = H(account=A1, cols=100, rows=30)
    h.typed("tool.test\r", idle=3.0)
    T = h.text()
    arow("T12d", "a window under 140 by 43 gets no page", "The test under the cursor" not in T and "Tests in" not in T, T[-300:])
    h.end()


SECTIONS = {
    "list": section_list, "verdicts": section_verdicts, "all": section_all, "failed": lambda: None, "compile": section_compile, "names": section_names,
    "refresh": section_refresh, "stop": section_stop, "break": section_break, "other": section_other,
}
ORDER = ["list", "verdicts", "all", "compile", "names", "refresh", "stop", "break", "other"]


def run_mutant(name):
    old, new, kills, secs = MUTANTS[name]
    FAILED_IDS[:] = []
    sync_page()
    mutate(name)
    say("sandbox-tool-test: MUTANT %s: the rows that must fail, and nothing else: %s" % (name, ", ".join(kills)))
    for s in secs:
        SECTIONS[s]()
    want = sorted(set(kills))
    got = sorted(set(FAILED_IDS))
    ok = want == got
    say("sandbox-tool-test: MUTANT %s: the rows that failed are %s; they had to be exactly %s -> %s" % (name, got, want, "KILLED BY ITS OWN ROWS" if ok else "NOT AS EXPECTED"))
    sync_page()
    compile_page()
    return ok


def main():
    arg_m = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mutant=")), None)
    all_m = "--mutants" in sys.argv[1:]
    if arg_m is not None and arg_m not in MUTANTS:
        bail("usage: sandbox-tool-test.py <dir> [--build] [--mutants | --mutant=%s]" % "|".join(MUTANTS))
    rc = 0
    try:
        sh.setup("sandbox-tool-test.py")
        setup_tests()
        if arg_m is None and not all_m:
            for s in ORDER:
                SECTIONS[s]()
        else:
            results = [run_mutant(m) for m in (list(MUTANTS) if all_m else [arg_m])]
            rc = 0 if all(results) else 1
            say("\nsandbox-tool-test: %d mutants, %d killed by exactly their own rows" % (len(results), sum(1 for r in results if r)))
    finally:
        try:
            sync_page()
        except OSError:
            pass
        sh.teardown()
    if arg_m is None and not all_m:
        say("\nsandbox-tool-test: %d passed, %d failed" % (sh.tkb.passed, sh.tkb.failed))
        return 0 if sh.tkb.failed == 0 and sh.tkb.passed > 0 else 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
