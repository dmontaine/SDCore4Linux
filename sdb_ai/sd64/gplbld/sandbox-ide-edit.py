#!/usr/bin/env python3
#
# sandbox-ide-edit.py - the IDE's editing commands (the editor merge's stage D, first slice, 29 Oct 26).  No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-ide-edit.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 every row passed, 1 a row failed, 2 it
# could not run.
#
# START-HISTORY:
# 29 Oct 26 dm  New with stage D.  WRITTEN, NOT RUN (the owner's rule for the full-screen phases: one complete run at the end).  The free check that holds the same properties as text is
#               test-ideedit-units.py.  EXPECT FIRST-RUN FAULTS IN THE SUITE: the number of Down presses to an entry of a menu, the words of a box and how the form of Export and Import takes its
#               answers are guesses from the other IDE suites.
# END-HISTORY
#
# WHAT RUNS.  The IDE on a PSEUDO-TERMINAL at 140 by 43 in the sandbox user's own account (sandbox-ide.py's Ide), on a record of the file bp that this script writes.  EVERY VERDICT ON A RECORD IS READ
# FROM THE DISK by a probe program, and what the editor shows is read off the emulated screen.
#
#   S0  setup and controls: the fixture and the probe compile; the probe reads the record as written
#   R   Replace is ONE undo step (a single Ctrl-Z gives the whole text back); it matches case as delivered and changes nothing on a read-only tab is held by the free check
#   L   List matching lines: the lines that hold a text are in the table with their numbers, Return on one goes to it; the find options (case, whole words) change what is listed
#   Q   Query replace: Yes for the first match and No for the second changes only the first, as one undo step
#   U   Upcase and Downcase the selection change only the characters between the mark and the cursor
#   X   Export the selection writes the selected text to a new record; Import a record here puts a record's lines in at the cursor
#   G   Go to: a line, a line and column
#   C   Run a command: what it prints is in the table
#   V   Refresh draws the screen again

import importlib.util
import os
import re
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


sb = _load("sandbox_ide_for_edit", "sandbox-ide.py")
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
RUN = "%05d" % (os.getpid() % 100000)
F10, RIGHT, LEFT, DOWN, RET, ESC = sb.F10, sb.RIGHT, sb.LEFT, sb.DOWN, sb.RET, sb.ESC
CTRL_Q, CTRL_S, CTRL_L, CTRL_R = sb.CTRL_Q, sb.CTRL_S, sb.CTRL_L, sb.CTRL_R
CTRL_Z, CTRL_G = "\x1a", "\x07"
passed = failed = 0
BOX = SYSD = None
REC = "zze" + RUN                       # the record of bp the rows work on
EXP = "zzx" + RUN                       # the record Export makes
LINES = ["alpha beta", "Beta gamma", "alphabet end", "line four"]


def say(s=""):
    print(s)
    sys.stdout.flush()


def row(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        say("  [PASS] " + name)
    else:
        failed += 1
        say("  [FAIL] " + name + ("   <- " + detail if detail else ""))
    return ok


def bail(msg):
    say("sandbox-ide-edit: CANNOT RUN - " + msg)
    teardown()
    sys.exit(2)


FIX = """   open 'bp' to p else stop 'EFIX no bp'
   write '%(l1)s':@fm:'%(l2)s':@fm:'%(l3)s':@fm:'%(l4)s' on p, '%(rec)s'
   write 'INS1':@fm:'INS2' on p, '%(rec)simp'
   delete p, '%(exp)s'
   crt 'EFIX done'
end
"""
PROBE = """   open 'bp' to p else stop 'EPROBE no bp'
   for i = 1 to 3
      id = field('%(rec)s %(exp)s %(rec)simp', ' ', i)
      read r from p, id then crt 'EREC ':id:' [':convert(@fm, '^', r):']' else crt 'EREC ':id:' <absent>'
   next i
   crt 'EPROBE END'
end
"""
SUBS = {"l1": LINES[0], "l2": LINES[1], "l3": LINES[2], "l4": LINES[3], "rec": REC, "exp": EXP}


def put(name, text):
    with open(os.path.join(SYSD, "bp", name), "w") as fh:
        fh.write(text % SUBS)


def disk():
    o = sb.sess(BOX, "RUN bp zzeprobe" + RUN)
    return dict(re.findall(r"(?m)^EREC (\S+) (.*?)\s*$", o))


def tab_row(e):
    L = e.lines()
    return L[2] if len(L) > 2 else ""


def editor_text(e):
    return "\n".join(l[28:] for l in e.lines()[3:39])


def table_text(e):
    return "\n".join(e.lines()[28:41])


def open_rec():
    e = sb.Ide(BOX, "IDE bp %s" % REC)
    e.quiet()
    return e


def menu(e, n_right, n_down):
    """F10, RIGHT n_right times (File is the first menu), DOWN n_down times, Return"""
    e.keys(F10, RIGHT * n_right, DOWN * n_down, RET)
    e.quiet()


def done(e):
    if not e.s.exited and "IDE: " in "\n".join(e.lines()[:3]):
        e.keys(CTRL_Q)
        n = 0
        while "has changes" in e.text() and n < 6:
            e.keys(DOWN, RET)
            n += 1
        time.sleep(0.5)
    e.end()


def section_setup():
    say("\n--- S0: the fixture, the probe, and the instruments' controls -------------------------------------------------------------")
    put("zzefix" + RUN, FIX)
    put("zzeprobe" + RUN, PROBE)
    o = sb.sess(BOX, "BASIC bp zzefix%s zzeprobe%s" % (RUN, RUN), "RUN bp zzefix" + RUN)
    ok = re.search(r"(?m)^Compiled 2 program\(s\) with no errors", o) is not None and "EFIX done" in o
    row("S0 setup: the fixture and the probe compile and the fixture ran to its end", ok, o[-500:])
    if not ok:
        bail("the fixture was not made")
    d = disk()
    row("S0 control: the probe reads the record as written and the export target is absent", d.get(REC) == "[%s]" % "^".join(LINES) and d.get(EXP) == "<absent>", repr(d))


def section_replace():
    say("\n--- R: Replace is one undo step ---------------------------------------------------------------------------------------")
    e = open_rec()
    e.keys(CTRL_R)
    e.keys("alpha", RET)
    e.keys("ALPHA", RET)
    e.quiet()
    t = editor_text(e)
    row("R1 Ctrl-R replaces every 'alpha' (case as typed: 'Beta' and 'alphabet' keep their other letters), and says how many", "ALPHA beta" in t and "ALPHAbet end" in t and "Beta gamma" in t and "2" in e.status(),
        "%r | %r" % (t[:200], e.status()[:100]))
    e.keys(CTRL_Z)
    e.quiet()
    t = editor_text(e)
    row("R2 ONE Ctrl-Z gives the whole text back (it forgot the undo steps before 29 Oct 26)", "alpha beta" in t and "alphabet end" in t and "ALPHA" not in t, repr(t[:200]))
    done(e)


def section_list():
    say("\n--- L: List matching lines and the find options -----------------------------------------------------------------------------")
    e = open_rec()
    menu(e, 2, 2)                                                       # Search is the third menu; List is its third entry
    e.keys("alpha", RET)
    e.quiet()
    tt = table_text(e)
    row("L1 List matching lines puts the lines that hold 'alpha' in the table at the bottom, with their numbers (1 and 3, not 2)", "alpha beta" in tt and "alphabet end" in tt and "Beta gamma" not in tt, repr(tt[:300]))
    row("L2 the status line says how many", "2 lines" in e.status(), e.status()[:120])
    menu(e, 2, 5)                                                       # Find options
    e.keys("W", RET)
    e.quiet()
    menu(e, 2, 2)
    e.keys("alpha", RET)
    e.quiet()
    tt = table_text(e)
    row("L3 with whole words on, 'alpha' lists line 1 only ('alphabet' is another word)", "alpha beta" in tt and "alphabet end" not in tt, repr(tt[:300]))
    menu(e, 2, 5)
    e.keys(RET)                                                         # blank: match case off, whole words off
    e.quiet()
    menu(e, 2, 2)
    e.keys("BETA", RET)
    e.quiet()
    tt = table_text(e)
    row("L4 with both options off, 'BETA' lists lines 1 and 2 (the case is ignored)", "alpha beta" in tt and "Beta gamma" in tt, repr(tt[:300]))
    done(e)


def section_qreplace():
    say("\n--- Q: Query replace --------------------------------------------------------------------------------------------------------")
    e = open_rec()
    menu(e, 2, 3)                                                       # Query replace
    e.keys("alpha", RET)
    e.keys("A", RET)
    e.keys(RET)                                                         # the box for line 1: Yes (the default)
    e.keys(RIGHT, RET)                                                  # the box for line 3: No
    e.quiet()
    t = editor_text(e)
    row("Q1 Yes to the first match and No to the second changes only the first: 'A beta' and 'alphabet end'", "A beta" in t and "alphabet end" in t, repr(t[:200]))
    e.keys(CTRL_Z)
    e.quiet()
    row("Q2 one Ctrl-Z gives the text back", "alpha beta" in editor_text(e), repr(editor_text(e)[:200]))
    done(e)


def section_case():
    say("\n--- U: Upcase and Downcase the selection ---------------------------------------------------------------------------------")
    e = open_rec()
    e.keys(CTRL_G)
    e.keys(RIGHT * 5)                                                   # the mark at line 1 column 1, the cursor at column 6
    menu(e, 2, 6)                                                       # Upcase the selection
    t = editor_text(e)
    row("U1 only the selection changes case: 'ALPHA beta' (the rest of the line and the other lines are as they were)", "ALPHA beta" in t and "Beta gamma" in t and "alphabet end" in t, repr(t[:200]))
    e.keys(CTRL_G)
    e.keys(RIGHT * 5)
    menu(e, 2, 7)                                                       # Downcase the selection
    t = editor_text(e)
    row("U2 Downcase gives it back", "alpha beta" in t, repr(t[:200]))
    menu(e, 2, 6)
    row("U3 with nothing selected it says so", "Nothing is selected" in e.status(), e.status()[:120])
    done(e)


def section_xp():
    say("\n--- X: Export the selection and Import a record -----------------------------------------------------------------------------")
    e = open_rec()
    e.keys(CTRL_G)
    e.keys(RIGHT * 5)
    menu(e, 2, 9)                                                       # Export the selection: the form for the file and the record
    e.keys(EXP, RET)
    e.quiet()
    d = disk()
    row("X1 Export writes the selected text to the new record (the file is bp, the form's own default)", d.get(EXP) == "[alpha]", repr((d.get(EXP), e.status()[:100])))
    e.keys(DOWN, DOWN)                                                  # (the cursor to line 3 for the import)
    menu(e, 2, 8)                                                       # Import a record here
    e.keys(REC + "imp", RET)
    e.quiet()
    t = editor_text(e)
    row("X2 Import puts the lines of the record in at the cursor: INS1 and INS2 are in the text, and nothing was written", "INS1" in t and "INS2" in t and disk().get(REC) == "[%s]" % "^".join(LINES), repr(t[:300]))
    done(e)


def section_goto():
    say("\n--- G: Go to ---------------------------------------------------------------------------------------------------------------")
    e = open_rec()
    e.keys(CTRL_L)
    e.keys("3,4", RET)
    e.quiet()
    row("G1 'Go to 3,4' puts the cursor on line 3, column 4 (the status line gives both)", re.search(r"\b3\b\D+\b4\b", e.status()) is not None, e.status()[:120])
    e.keys(CTRL_L)
    e.keys("0", RET)
    e.quiet()
    row("G2 a zero is not a line: the cursor stays", re.search(r"\b3\b\D+\b4\b", e.status()) is not None, e.status()[:120])
    done(e)


def section_xeq():
    say("\n--- C: Run a command; V: Refresh ----------------------------------------------------------------------------------------------")
    e = open_rec()
    menu(e, 3, 4)                                                       # Build is the fourth menu; Run a command is its fifth entry
    e.keys("WHO", RET)
    e.quiet()
    row("C1 Run a command shows what the command printed in the table, and says how many lines", "lines printed by" in e.status() and len(table_text(e).strip()) > 0, "%r | %r" % (e.status()[:120], table_text(e)[:200]))
    menu(e, 4, 1)                                                       # View menu, Refresh
    row("V1 Refresh leaves the IDE up and the record on the screen", "alpha beta" in editor_text(e) and "IDE: " in "\n".join(e.lines()[:3]), "%r" % editor_text(e)[:100])
    done(e)


def teardown():
    if BOX:
        subprocess.run([sys.executable, TOOL, BOX, "stop"], capture_output=True, text=True, errors="replace", timeout=120)


def main():
    global BOX, SYSD
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        say("usage: sandbox-ide-edit.py <dir> [--build]")
        sys.exit(2)
    BOX = os.path.abspath(args[0])
    SYSD = os.path.join(BOX, "sys")
    say("sandbox-ide-edit: sandbox %s  tree %s  run %s  SDBOX_KEYSET=%s" % (BOX, os.path.dirname(HERE), RUN, os.environ.get("SDBOX_KEYSET")))
    if "--build" in sys.argv:
        if os.path.exists(BOX) and os.listdir(BOX):
            bail("%s is not empty" % BOX)
        r = subprocess.run([sys.executable, TOOL, BOX, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-ide-edit: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(SYSD, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % BOX)
    subprocess.run([sys.executable, TOOL, BOX, "start"], capture_output=True, text=True, errors="replace", timeout=120)
    try:
        section_setup()
        section_replace()
        section_list()
        section_qreplace()
        section_case()
        section_xp()
        section_goto()
        section_xeq()
    finally:
        teardown()
    say("\nsandbox-ide-edit: %d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        say("sandbox-ide-edit: CANNOT RUN - no row ran (a broken test, not a pass)")
        return 2
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
