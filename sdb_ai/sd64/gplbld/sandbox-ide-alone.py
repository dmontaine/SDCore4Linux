#!/usr/bin/env python3
#
# sandbox-ide-alone.py - the verb SED: the IDE started as the editor by itself (S.184 stage 7, 9 Nov 26).  Driven on a pseudo-terminal on a private SD.  No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-ide-alone.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree).  Exit 0 every row passed, 1 a row failed, 2 it could not run.
# What it holds: no files pane and no Tools menu; a record on the command line opens in the editor; Ctrl-E is the end of the line; a save reaches the disk; a compile's errors come up under
# the editor and Go, Hide the results takes them away; a bare SED asks File name? and Record name?, an empty answer ends it, ? lists the records and picks one; a quoted id with a blank;
# a dictionary item opens as text and not as the form; closing the last record ends it.  The disk is the oracle for what a save did.  The IDE's own suites hold what it shares with the IDE.
#
import importlib.util
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
spec = importlib.util.spec_from_file_location("sandbox_ide_for_alone", os.path.join(HERE, "sandbox-ide.py"))
sb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sb)
RUN = "%05d" % (os.getpid() % 100000)
F10, DOWN, RET, UP = sb.F10, sb.DOWN, sb.RET, sb.UP
CTRL_S, CTRL_Q = sb.CTRL_S, sb.CTRL_Q
CTRL_W = "\x17"
F8 = sb.F8
passed = failed = 0
BOX = SYSD = None


def say(s=""):
    print(s, flush=True)


def bail(msg):
    say("sandbox-ide-alone: CANNOT RUN - " + msg)
    sys.exit(2)


def row(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        say("  [PASS] " + name)
    else:
        failed += 1
        say("  [FAIL] " + name + ("   <- " + str(detail) if detail else ""))


def put(name, text):
    with open(os.path.join(SYSD, "bp", name), "w", encoding="latin-1") as fh:
        fh.write(text)


def disk(name):
    with open(os.path.join(SYSD, "bp", name), encoding="latin-1") as fh:
        return fh.read()


def alive(e):
    return not e.s.exited and "File" in (e.lines()[0] if e.lines() else "")


def at_prompt(e):
    """the session is back at the prompt: the editor has ended"""
    return "File  " not in (e.lines()[0] if e.lines() else "") and any(l.rstrip().endswith(":") for l in e.lines())


def section():
    rec = "zza" + RUN
    put(rec, "alpha one\nbeta two\n")
    e = sb.Ide(BOX, "SED bp %s" % rec)
    e.quiet()
    top = e.lines()[0]
    row("A0 setup: SED on a record brings up the IDE's menu bar with the record in the editor", alive(e) and "alpha one" in e.text(), e.text()[:300])
    row("A1 there is no Tools menu", "Tools" not in top, top)
    row("A2 there is no files pane: the tree's list of the account's files is not on the screen", not any(l[:30].strip("| ").startswith("bp.out") for l in e.lines()), "\n".join(l[:30] for l in e.lines()[:8]))
    e.keys("\x05", "Z")
    e.quiet()
    row("A3 Ctrl-E is the end of the line, not the zoom", "alpha oneZ" in e.text(), e.text()[:200])
    e.keys(CTRL_S)
    e.quiet()
    row("A4 Ctrl-S writes the record", disk(rec).startswith("alpha oneZ"), repr(disk(rec)[:40]))
    bad = "zzb" + RUN
    put(bad, "print 'unterminated\nend\n")
    e.end()
    e = sb.Ide(BOX, "SED bp %s" % bad)
    e.quiet()
    e.keys(F8)
    e.quiet()
    row("A5 a compile with errors shows them under the editor, and the editor is still on the screen", "print 'unterminated" in e.text() and "Line" in e.text(), e.text()[-500:])
    e.keys(F10, sb.RIGHT * 2)
    e.quiet()
    row("A6 the Go menu offers Hide the results and no longer Files and records", "Hide the results" in e.text() and "Files and records" not in e.text(), e.text()[:400])
    e.keys("r")
    e.quiet()
    row("A7 Hide the results takes the table away and the editor stays", "print 'unterminated" in e.text(), e.text()[-300:])
    e.end()
    e = sb.Ide(BOX, "SED")
    e.quiet()
    row("A8 a bare SED asks File name?", "File name?" in e.text(), e.text()[-300:])
    e.keys("bp", RET)
    e.quiet()
    row("A9 and then Record name?", "Record name" in e.text(), e.text()[-300:])
    e.keys("?", RET)
    e.quiet()
    row("A10 ? lists the records of the file", "The records of bp" in e.text(), e.text()[:400])
    e.keys(rec, RET)
    e.quiet()
    row("A11 picking one opens it", "alpha oneZ" in e.text(), e.text()[:300])
    e.end()
    e = sb.Ide(BOX, "SED")
    e.quiet()
    e.keys(RET)
    e.quiet()
    row("A12 an empty answer to File name? ends the editor", at_prompt(e), "\n".join(e.lines()[:4]))
    e.end()
    blank = "zz c" + RUN
    put(blank, "with a blank\n")
    e = sb.Ide(BOX, "SED bp \"%s\"" % blank)
    e.quiet()
    row("A13 a record id in quotes may hold a blank", "with a blank" in e.text(), e.text()[:300])
    e.end()
    e = sb.Ide(BOX, "SED bp %s" % rec)
    e.quiet()
    e.keys(CTRL_W)
    e.quiet()
    row("A14 closing the last record ends the editor", at_prompt(e), "\n".join(e.lines()[:4]))
    e.end()
    o = sb.sess(BOX, "CREATE.FILE zzdf" + RUN)
    e = sb.Ide(BOX, "SED DICT zzdf%s @ID" % RUN)
    e.quiet()
    row("A15 a dictionary item opens as text, and not as the IDE's form", "Dictionary item" not in e.lines()[1] and "D" in e.text(), e.text()[:300] + o[-100:])
    e.end()


def main():
    global BOX, SYSD
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-ide-alone.py <dir> [--build]")
    BOX = os.path.abspath(args[0])
    SYSD = os.path.join(BOX, "sys")
    say("sandbox-ide-alone: sandbox %s, keyset %s" % (BOX, os.environ.get("SDBOX_KEYSET", "0")))
    if "--build" in sys.argv:
        if os.path.exists(BOX) and os.listdir(BOX):
            bail("%s is not empty" % BOX)
        r = subprocess.run([sys.executable, TOOL, BOX, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-ide-alone: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(SYSD, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % BOX)
    subprocess.run([sys.executable, TOOL, BOX, "start"], capture_output=True, text=True, errors="replace", timeout=120)
    try:
        section()
    finally:
        subprocess.run([sys.executable, TOOL, BOX, "stop"], capture_output=True, text=True, errors="replace", timeout=120)
    say("\nsandbox-ide-alone: %d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        bail("no row ran - a broken test, not a pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
