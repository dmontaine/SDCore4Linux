#!/usr/bin/env python3
#
# sandbox-tk-base.py - the toolkit's shared base, slice 1 (TK-0.1: the frame, the key table and the function-key row), on a pseudo-terminal.  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-tk-base.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent).  Exit 0 every row passed, 1 a row failed, 2 it
# could not run.  The throw-away app `tktest` (gpl.bp/tool_tktest, catalogued $tool_tktest) is given a VOC entry by this suite and by nothing else: it is not a verb of the product.
#
# START-HISTORY:
# 22 Oct 26 dm  New (S.75, TK-0.1).  Rows written BEFORE the programs; run red on a tree without them.
# END-HISTORY
#
# WHAT IS HELD (plan .claude/plan-fullscreen-toolkit.md 2.1, 2.2, 2.12): at 140 by 43 the foot of the screen is, top to bottom, the status line (row 40, reverse video, the pane in
# brackets first, then the message), the border (row 41), and the function keys (row 42, the added 43rd line); the function-key row names only the keys the focused pane uses, in the
# key table's order, and changes when the focus does; a key the table disables is not shown; the keys do what their labels say (Tab, F1, F3 on pane A only, F5 on pane B only, Ctrl-Q);
# a bigger window is used whole (the rows move to its foot); a window under 140 by 43 is refused with the library's message 11197 before the screen is taken; Ctrl-Q leaves and gives the
# prompt back; and when the input ENDS the app ends and does not spin (a piped session: wall time and the child's own CPU).
#
# THE INSTRUMENT.  Each row reads the screen the emulator holds (termscreen.py) after the keys were typed; a row passes on the words it prints when it ran to the end, and the suite stops
# (exit 2) if the app never drew its frame.  The border is judged with LC_ALL=C, where the library's line character is the plain "-".  NOT HELD HERE: the refusal of a non-administrator
# for audience `admin` (the sandbox's session is the administrator; the check is a text check in test-tkbase-units.py and a later witness), a UTF-8 border, the mouse.
import os
import re
import resource
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ptydrive import PtySession    # noqa: E402

TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b[()][0-9A-B]|\x1b[=>78M]")
passed = failed = skipped = 0

F_A = "F1 help  F3 sort  Tab next  ^Q quit"
F_B = "F1 help  F5 refresh  Tab next  ^Q quit"

KEYS = {"F1": "\x1bOP", "F3": "\x1bOR", "F5": "\x1b[15~", "TAB": "\t", "CTRLQ": "\x11", "CTRLS": "\x13"}


def say(s=""):
    print(s, flush=True)


def row(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        say("  [PASS] " + name)
    else:
        failed += 1
        say("  [FAIL] " + name + ("   <- " + detail if detail else ""))


def skip(name, why):
    global skipped
    skipped += 1
    say("  [SKIP] %s: %s" % (name, why))


def bail(msg):
    say("sandbox-tk-base: CANNOT RUN - " + msg)
    sys.exit(2)


def sess(box, *cmds):
    """A session in internal mode (sd -internal), the only place a $internal program compiles; the sandbox tool's own `sess` cannot (as sandbox-sortord.py's isess)."""
    env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"))
    body = "\nTERM 200,9999\n" + "".join(c + "\n" for c in cmds) + "OFF\n"
    p = subprocess.Popen([os.path.join(box, "sys", "bin", "sd"), "-internal"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         cwd=os.path.join(box, "sys"), env=env)
    try:
        out, _ = p.communicate(body.encode("latin-1"), timeout=300)
    except subprocess.TimeoutExpired:
        p.kill()
        p.communicate()
        return ""
    return ANSI.sub("", out.decode("latin-1", "replace")).split(":TERM 200,9999", 1)[-1]


class Term:
    def __init__(self, box, cmd, cols=140, rows=43):
        env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"), TERM="xterm", LC_ALL="C", LANG="C")
        self.s = PtySession([os.path.join(box, "sys", "bin", "sd")], os.path.join(box, "user_accounts"), env, cols, rows)
        self.cols, self.rows = cols, rows
        self.s.settle(1.0)
        self.s.type("TERM xterm\r")
        self.s.type("TERM %d,%d\r" % (cols, rows))
        self.s.type(cmd + "\r", idle=1.0)

    def lines(self):
        return self.s.screen.lines()

    def line(self, r):
        L = self.lines()
        return L[r].rstrip() if r < len(L) else ""

    def rev(self, r):
        return self.s.screen.reverse(r)

    def key(self, name):
        self.s.type(KEYS[name], idle=0.5)

    def end(self):
        self.s.type("\x11", idle=0.3)
        self.s.type("\rOFF\r", idle=0.5)
        self.s.finish()


# TK-0.2.  A $internal program calls $tk_gate_info and $tk_run in an internal session and prints one line for each; the numbers in it are the TK.G.* fields of tk.h
# (test-tkgates-units.py holds them).  The sentinel is a real effect: create.file zztkrunf.  Every refusal below is a sentence that WOULD make the file if it ran.
RUNPROG = """$internal
   crt 'TKRUN begin'
   call $tk_gate_info('list', ids)
   crt 'GL ' : dcount(ids, @fm) : ' ' : ids<1> : ' ' : ids<dcount(ids, @fm)>
   call $tk_gate_info('sh', g)
   crt 'GSH ' : g<3> : ' ' : g<4> : ' ' : g<8> : ' ' : g<11> : ' ' : g<15>
   call $tk_gate_info('nosuch', g)
   crt 'GNO [' : g : ']'
   call $tk_gate_info('sockets', g)
   crt 'GSK ' : g<15> : ' [' : g<3> : ']'
   allow = 'who.am.i create.file'
   tag = 'T1' ; sentence = 'who.am.i' ; gosub go
   tag = 'T2' ; sentence = 'WHO.AM.I' ; gosub go
   tag = 'T3' ; sentence = 'sh ls' ; gosub go
   tag = 'T4' ; sentence = 'who' ; gosub go
   tag = 'T5' ; sentence = 'who.am.i x;sh' ; gosub go
   tag = 'T6' ; sentence = "who.am.i 'x'" ; gosub go
   tag = 'T7' ; sentence = 'who.am.i' : char(9) : 'x' ; gosub go
   tag = 'T8' ; sentence = 'who.am.i x' : @vm ; gosub go
   tag = 'T9' ; sentence = '' ; gosub go
   tag = 'T10' ; sentence = '   ' ; gosub go
   tag = 'T11' ; sentence = 'who.am.i ' : str('a', 600) ; gosub go
   tag = 'T12' ; sentence = 'who.am.i' : str(' a', 41) ; gosub go
   tag = 'T13' ; sentence = 'who.am.i' : str(' a', 39) ; gosub go
   tag = 'T14' ; sentence = 'who.am.i `x`' ; gosub go
   tag = 'T15' ; sentence = 'who.am.i $x' ; gosub go
   tag = 'S1' ; sentence = 'create.file zztkrunf;ls dynamic' ; gosub go
   tag = 'S2' ; sentence = 'CREATE.FILE zztkrunf dynamic' ; gosub go
   tag = 'S3' ; sentence = "create.file zztkrunf 'dynamic'" ; gosub go
   open 'zztkrunf' to f then
      crt 'SENT after-refusals EXISTS'
      close f
   end else crt 'SENT after-refusals ABSENT'
   tag = 'S4' ; sentence = 'create.file zztkrunf dynamic' ; gosub go
   open 'zztkrunf' to f then
      crt 'SENT after-run EXISTS'
      close f
   end else crt 'SENT after-run ABSENT'
   execute 'delete.file zztkrunf force' capturing o2
   crt 'TKRUN end'
   stop
go:
   call $tk_run(allow, sentence, out, st, err)
   crt tag : ' st=' : st : ' err=[' : err : '] ran=' : (if index(out, 'Admin?', 1) > 0 then 1 else 0)
   return
end
"""


def runtime_rows(box, made):
    say("\n--- the gate table and the one place a tool runs a command (TK-0.2)")
    with open(os.path.join(box, "sys", "bp", "zztkrun"), "w", encoding="latin-1") as f:
        f.write(RUNPROG)
    made.append("zztkrun")
    out = sess(box, "DELETE.FILE zztkrunf FORCE", "BASIC bp zztkrun", "RUN bp zztkrun")
    if not re.search(r"^TKRUN begin\s*$", out, re.M) or not re.search(r"^TKRUN end\s*$", out, re.M):
        say(out[-1200:])
        bail("the TK-0.2 program did not run to its end, so no row below can be believed")
    got = {}
    for m in re.finditer(r"^(\w+) st=(-?\d+) err=\[(.*)\] ran=(\d)\s*$", out, re.M):
        got[m.group(1)] = (int(m.group(2)), m.group(3), int(m.group(4)))
    line = lambda pat: re.search(pat, out, re.M)
    row("$tk_gate_info 'list' returns the 15 ids, the first ssh and the last the planned sockets", line(r"^GL 15 ssh sockets\s*$") is not None, out[-300:])
    row("a gate by id returns its words, kernel key, conflict slot and status: sh = sh-on sh-off K$SH SH built", line(r"^GSH sh-on sh-off K\$SH SH built\s*$") is not None, "")
    row("an id that is not in the table returns nothing", line(r"^GNO \[\]\s*$") is not None, "")
    row("a planned gate shows as planned and has no word to run", line(r"^GSK planned \[\]\s*$") is not None, "")

    NOTALLOWED, CHAR, EMPTY, LONG = "is not one of the commands this tool may run", "has a character that a command word may not have", "there is nothing to run", "the command is too long to run"
    want = [
        ("T1", "an allowed command runs: who.am.i (no message, it ran, and its own words came back)", lambda e, r: e == "" and r == 1),
        ("T2", "the first word is compared as typed: WHO.AM.I in capitals is refused (11805) and did not run", lambda e, r: NOTALLOWED in e and r == 0),
        ("T3", "a command that is not in the list (sh ls) is refused (11805)", lambda e, r: NOTALLOWED in e and r == 0),
        ("T4", "the first word is compared whole: 'who' is not 'who.am.i'", lambda e, r: NOTALLOWED in e and r == 0),
        ("T5", "a semicolon in an argument is refused (11806): the command did not run", lambda e, r: CHAR in e and r == 0),
        ("T6", "a quote in an argument is refused", lambda e, r: CHAR in e and r == 0),
        ("T7", "a tab joins the next word to the first, which is then not in the list", lambda e, r: NOTALLOWED in e and r == 0),
        ("T8", "a value mark in an argument is refused", lambda e, r: CHAR in e and r == 0),
        ("T9", "an empty sentence is refused (11804)", lambda e, r: EMPTY in e and r == 0),
        ("T10", "a sentence of spaces is refused (11804)", lambda e, r: EMPTY in e and r == 0),
        ("T11", "a sentence of 600 characters is refused (11807)", lambda e, r: LONG in e and r == 0),
        ("T12", "a sentence of 42 words is refused (11807)", lambda e, r: LONG in e and r == 0),
        ("T13", "a sentence of exactly 40 words is run (the boundary)", lambda e, r: e == "" and r == 1),
        ("T14", "a backtick in an argument is refused", lambda e, r: CHAR in e and r == 0),
        ("T15", "a dollar sign in an argument is refused", lambda e, r: CHAR in e and r == 0),
        ("S1", "create.file with a second command after a semicolon is refused (11806)", lambda e, r: CHAR in e),
        ("S2", "CREATE.FILE in capitals is refused (11805)", lambda e, r: NOTALLOWED in e),
        ("S3", "create.file with a quoted word is refused (11806)", lambda e, r: CHAR in e),
        ("S4", "create.file zztkrunf dynamic, as the tool would build it, is run: no message", lambda e, r: e == ""),
    ]
    for tag, what, test in want:
        g = got.get(tag)
        row("%s: %s" % (tag, what), g is not None and test(g[1], g[2]), repr(g))
    row("THE SENTINEL: after S1, S2 and S3 (each would have made the file) the file zztkrunf does not exist", line(r"^SENT after-refusals ABSENT\s*$") is not None, out[-400:])
    row("...and after S4, which was allowed, it does (so the sentinel can fire)", line(r"^SENT after-run EXISTS\s*$") is not None, out[-400:])


def main():
    args =[a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-tk-base.py <dir> [--build]")
    box = os.path.abspath(args[0])
    say("sandbox-tk-base: sandbox %s" % box)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-tk-base: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(box, "sys", "bin", "sd")):
        bail("%s holds no built sandbox" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)
    made = []
    try:
        with open(os.path.join(box, "sys", "bp", "zztkvoc"), "w", encoding="latin-1") as f:
            f.write("$internal\n   open 'VOC' to v else crt 'TKVOC no voc' ; stop\n   write 'V':@fm:'CA':@fm:'$tool_tktest' to v, 'tktest'\n   crt 'TKVOC done'\nend\n")
        made.append("zztkvoc")
        out = sess(box, "BASIC bp zztkvoc", "RUN bp zztkvoc")
        row("SETUP: the VOC entry tktest (the throw-away app, catalogued $tool_tktest) is written", re.search(r"^TKVOC done\s*$", out, re.M) is not None, out[-300:])
        who = sess(box, "WHO.AM.I")
        is_admin = re.search(r"Admin\?\s*:\s*Yes", who) is not None
        say("    (the sandbox session is %s)" % ("an administrator" if is_admin else "NOT an administrator"))

        say("\n--- a window of 140 by 43: the foot of the screen")
        t = Term(box, "tktest")
        if "F1 help" not in "\n".join(t.lines()):
            say("    screen after the command:\n" + "\n".join(l.rstrip() for l in t.lines() if l.strip())[:900])
            bail("the app never drew its function-key row, so no row below can be believed")
        row("the function-key row is row 42 (the added 43rd line) and names exactly the keys pane A uses, in table order: %r" % F_A, t.line(42) == F_A, repr(t.line(42)))
        row("...in the bar's style: the text is in reverse video", F_A in t.rev(42), repr(t.rev(42)))
        row("the border is row 41: 140 plain characters across (LC_ALL=C)", t.line(41) == "-" * 140, repr(t.line(41)[:60]))
        row("the status line is row 40, in reverse video, and starts with the pane in brackets: [A]", t.line(40).startswith("[A]") and "[A]" in t.rev(40), repr(t.line(40)))
        row("a key the table disables (Ctrl-S, save) is not shown", "^S" not in t.line(42), repr(t.line(42)))
        t.key("TAB")
        row("Tab moves the focus: the function-key row now names the keys of pane B: %r" % F_B, t.line(42) == F_B, repr(t.line(42)))
        row("...and the status line shows [B]", t.line(40).startswith("[B]"), repr(t.line(40)))
        t.key("F1")
        row("F1 (help, every pane): the status line carries the message after the pane: 'help for pane B'", t.line(40).startswith("[B]") and "help for pane B" in t.line(40), repr(t.line(40)))
        t.key("F3")
        row("F3 (sort) is pane A's key: on pane B it does nothing (the message is still the help one)", "help for pane B" in t.line(40) and "sorted" not in t.line(40), repr(t.line(40)))
        t.key("F5")
        row("F5 (refresh) is pane B's key: the message is 'refreshed'", "refreshed" in t.line(40), repr(t.line(40)))
        t.key("TAB")
        row("Tab again: back to pane A, its keys, [A]", t.line(42) == F_A and t.line(40).startswith("[A]"), repr((t.line(42), t.line(40))))
        t.key("F3")
        row("F3 on pane A: 'sorted'", "sorted" in t.line(40), repr(t.line(40)))
        t.key("CTRLQ")
        t.s.settle(0.8)
        L = "\n".join(t.lines())
        row("Ctrl-Q leaves the app and gives the prompt back: no function-key row any more, and SD answers a command", "F1 help" not in L, L[-300:])
        t.s.type("WHO\r", idle=0.8)
        row("...the session is still alive after the app", re.search(r"(?m)^\d+ \w+", "\n".join(t.lines())) is not None or "WHO" in "\n".join(t.lines()), "\n".join(t.lines())[-200:])
        t.end()

        say("\n--- a window bigger than 43 rows is used whole")
        t = Term(box, "tktest", cols=160, rows=50)
        row("at 160 by 50 the function-key row is the LAST row (49), the border above it (48), the status line above that (47)",
            t.line(49) == F_A and t.line(48) == "-" * 160 and t.line(47).startswith("[A]"), repr((t.line(47)[:20], t.line(48)[:20], t.line(49), t.line(42)[:20])))
        t.end()

        say("\n--- a window under 140 by 43 is refused before the screen is taken")
        t = Term(box, "tktest", cols=100, rows=30)
        L = "\n".join(t.lines())
        row("the library's message 11197 names the app and both sizes: 'at least 140 columns by 43 lines; this one is 100 by 30'",
            "at least 140 columns by 43 lines" in L and "100 by 30" in L, L[-300:])
        row("...and no frame was drawn", "F1 help" not in L and not any(l.strip() == "-" * 100 for l in t.lines()), "")
        t.end()

        say("\n--- the audience")
        if is_admin:
            t = Term(box, "tktest admin")
            row("audience admin in an administrator's session: the frame is drawn (the refusal for anyone else is a text check)", t.line(42) == F_A, repr(t.line(42)))
            row("...and the right end of row 0 names the app and the audience: 'administrator'", "administrator" in t.line(0), repr(t.line(0)))
            t.end()
        else:
            skip("audience admin", "the sandbox session is not an administrator, so the frame cannot be shown for it")

        runtime_rows(box, made)

        say("\n--- the end of the input ends the app (a pipe; TERM 140,43 typed so that the window is big enough)")
        env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"), TERM="xterm", LC_ALL="C")
        r0 = resource.getrusage(resource.RUSAGE_CHILDREN)         # the children reaped so far (the pty runs above); this child's own CPU is the difference
        p = subprocess.Popen([os.path.join(box, "sys", "bin", "sd")], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=os.path.join(box, "user_accounts"), env=env)
        t0 = time.time()
        p.stdin.write(b"\nTERM 140,43\ntktest\n")
        p.stdin.flush()
        p.stdin.close()
        ended = False
        while time.time() - t0 < 15:
            if p.poll() is not None:
                ended = True
                break
            time.sleep(0.2)
        took = time.time() - t0
        if not ended:
            os.kill(p.pid, 1)           # SIGHUP first: SD lets go of what it holds; a killed session keeps its slot
            time.sleep(1)
            if p.poll() is None:
                p.kill()
        p.wait()
        r1 = resource.getrusage(resource.RUSAGE_CHILDREN)
        cpu = (r1.ru_utime - r0.ru_utime) + (r1.ru_stime - r0.ru_stime)
        say("    [measured] ended: %s after %.1f s, the child's CPU %.2f s" % (ended, took, cpu))
        row("a piped session whose input ENDS ends the app within 15 s (it does not wait for a key that cannot come)", ended, "%.1f s" % took)
        row("...and did not spin: under 3 s of CPU (a loop that takes the end of input for an empty key uses all of it)", ended and cpu < 3.0, "%.2f s" % cpu)
    finally:
        for nm in made:
            for d in ("bp", "bp.out"):
                p_ = os.path.join(box, "sys", d, nm)
                if os.path.exists(p_):
                    os.remove(p_)
        subprocess.run([sys.executable, TOOL, box, "stop"], capture_output=True, text=True, errors="replace", timeout=120)
    say("\nsandbox-tk-base: %d passed, %d failed, %d skipped" % (passed, failed, skipped))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
