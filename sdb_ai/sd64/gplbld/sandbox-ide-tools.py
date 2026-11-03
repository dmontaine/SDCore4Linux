#!/usr/bin/env python3
#
# sandbox-ide-tools.py - the IDE's Tools menu (S.75 DV10, Opus decision 12c): the development pages opened from the IDE through its terminal hand-over, on a pseudo-terminal on a
# private SD.  No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-ide-tools.py <dir> [--build] [--mutant=NAME]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 every row passed,
# 1 a row failed, 2 it could not run.  With --mutant=NAME one change is made to the SANDBOX'S OWN COPY of `ide`, compiled, the rows are run, and exit 0 means exactly the rows
# the mutant names failed; the copy is put back and compiled again afterwards.  One section (about a minute), so no --only.
#
# START-HISTORY:
# 3 Nov 26 dm  New (S.75 DV10).
# END-HISTORY
#
# WHAT IT HOLDS.  The IDE is started with no record (an Untitled buffer) and ZZQkeep is typed into it, unsaved.  Then:
#   D0  the menu bar of the IDE names Tools (between View and Help; the AI menu is not there: the sandbox has no AI)
#   D1  F10 and T open the Tools menu: Files, Dictionary, Vocabulary, Queries, Bulk update, Programs, Tests
#   D2  F: the IDE gives the terminal to tool.files - the PAGE is on the screen (its name at the right end of row 0, its box The file under the cursor), drawn by the page itself
#   D3  Ctrl-Q leaves the page, the hand-over's "Press Return to go back to the IDE" is shown, and Return gives the IDE back: its bar, and the status line says Back from tool.files
#   D4  the unsaved text is still in the editor (ZZQkeep): the hand-over kept the buffer
#   D5  Tools > Tests opens tool.test the same way (The test under the cursor), and D5b Ctrl-Q, Return bring the IDE back
# Mutant (each row is read from the screen, not from what the IDE says it did):  no-tests - do.tool's own list of verbs leaves out tool.test, so the entry opens nothing: D5 and D5b
# must fail and nothing else.
import importlib.util
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
_spec = importlib.util.spec_from_file_location("sandbox_ide_for_tools", os.path.join(HERE, "sandbox-ide.py"))
sb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sb)

TOOL = os.path.join(HERE, "sandbox-fromtree.py")
CTRL_Q = "\x11"
passed = failed = 0
FAILED = []

MUTANTS = {
    # name: (old text of the sandbox's ide, new text, the rows that must fail and no others)
    "no-tests": ("tool.bulk tool.catalog tool.test ', ' ' : tl.verb", "tool.bulk tool.catalog ', ' ' : tl.verb", ["D5", "D5b"]),
}


def say(s=""):
    print(s, flush=True)


def bail(msg):
    say("sandbox-ide-tools: CANNOT RUN - " + msg)
    sys.exit(2)


def row(rid, name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        say("  [PASS] %s %s" % (rid, name))
    else:
        failed += 1
        FAILED.append(rid)
        say("  [FAIL] %s %s%s" % (rid, name, ("   <- " + detail[:700]) if detail else ""))


def compile_ide(box):
    env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"), SDTEST_ADMIN="1")
    env.pop("SSH_CONNECTION", None)
    env.pop("SSH_TTY", None)
    say("    > [admin] [internal] in sys: BASIC gpl.bp ide")
    p = subprocess.run([os.path.join(box, "sys", "bin", "sd"), "-internal"], input="\nTERM 200,9999\nBASIC gpl.bp ide\nOFF\n", cwd=os.path.join(box, "sys"), env=env,
                       capture_output=True, text=True, errors="replace", timeout=600)
    out = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", p.stdout + p.stderr)
    return "Compiled 1 program(s) with no errors" in out, out


def wait_for(e, pred, secs=15.0):
    """pump the pty until the screen satisfies pred (a page that starts prints nothing while it reads the account)"""
    end = time.time() + secs
    while time.time() < end:
        if pred("\n".join(e.lines())):
            return True
        e.s._pump(0.3)
    return pred("\n".join(e.lines()))


def open_tool(e, letter, name, mark):
    """F10, T (the Tools menu), then the entry's letter; True when the page's name is at the right end of row 0 and its own box title is on the screen"""
    e.keys(sb.F10)
    e.keys("t")
    menu = "\n".join(e.lines())
    e.keys(letter)
    ok = wait_for(e, lambda t: name in t.split("\n")[0] and mark in t)
    return menu, ok


def back_to_ide(e):
    """Ctrl-Q leaves the page; the hand-over says Press Return; Return gives the IDE back.  (prompt seen, the IDE's bar and status line after)"""
    e.keys(CTRL_Q)
    seen = wait_for(e, lambda t: "Press Return to go back to the IDE" in t, 10)
    e.keys(sb.RET)
    wait_for(e, lambda t: "Tools" in t.split("\n")[0] and "Back from" in t, 10)
    return seen


def section_tools(box):
    say("\n--- tools: the IDE's Tools menu, each page through the terminal hand-over -----------------------------------")
    e = sb.Ide(box, "IDE")
    try:
        e.quiet()
        e.keys("ZZQkeep")
        L = e.quiet()
        top = L[0] if L else ""
        row("D0", "the IDE's menu bar names Tools, after View and before Help", re.search(r"View\s+Tools\s+Help", top) is not None and "ZZQkeep" in "\n".join(L), repr(top[:100]))
        menu, ok = open_tool(e, "f", "tool.files", "The file under the cursor")
        row("D1", "F10 and T open the Tools menu: Files, Dictionary, Vocabulary, Queries, Bulk update, Programs, Tests",
            all(w in menu for w in ("Files", "Dictionary", "Vocabulary", "Queries", "Bulk update", "Programs", "Tests")), menu[:900])
        L = e.lines()
        row("D2", "F: tool.files is on the screen, drawn by the page itself (its name at the right end of row 0, its box The file under the cursor); the IDE's bar is gone",
            ok and "Tools" not in L[0], repr(L[0][-40:]) + "\n" + "\n".join(L[:6]))
        seen = back_to_ide(e)
        L = e.lines()
        row("D3", "Ctrl-Q leaves the page, the hand-over asks for Return, and Return gives the IDE back: its bar, and the status line says Back from tool.files",
            seen and "Tools" in L[0] and "Back from tool.files" in e.status(), repr((seen, L[0][:80], e.status())))
        row("D4", "the unsaved text typed before the hand-over is still in the editor (ZZQkeep)", "ZZQkeep" in "\n".join(L), "\n".join(l for l in L[:12]))
        menu, ok = open_tool(e, "t", "tool.test", "The test under the cursor")
        L = e.lines()
        row("D5", "Tools > Tests opens tool.test the same way (its name at the right end of row 0, The test under the cursor)", ok, repr(L[0][-40:]) + "\n" + "\n".join(L[:6]))
        seen = back_to_ide(e)
        L = e.lines()
        row("D5b", "...and Ctrl-Q, Return bring the IDE back from it (Back from tool.test)", seen and "Tools" in L[0] and "Back from tool.test" in e.status(), repr((seen, L[0][:80], e.status())))
    finally:
        e.s.finish()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    mutant = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mutant=")), None)
    if len(args) != 1 or (mutant is not None and mutant not in MUTANTS):
        bail("usage: sandbox-ide-tools.py <dir> [--build] [--mutant=%s]" % "|".join(MUTANTS))
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-ide-tools: sandbox %s, keyset %s%s" % (box, os.environ.get("SDBOX_KEYSET", "0"), ", mutant " + mutant if mutant else ""))
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-ide-tools: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)
    ide_path = os.path.join(sysd, "gpl.bp", "ide")
    original_ide = None
    try:
        if mutant is not None:
            old, new, _ = MUTANTS[mutant]
            src = open(ide_path, encoding="latin-1").read()
            if src.count(old) != 1:
                bail("mutant %s: the text to change is found %d times, not once" % (mutant, src.count(old)))
            original_ide = src
            with open(ide_path, "w", encoding="latin-1") as fh:
                fh.write(src.replace(old, new))
            ok, out = compile_ide(box)
            if not ok:
                bail("the mutant IDE did not compile:\n" + out[-600:])
            say("sandbox-ide-tools: MUTANT %s: the rows that must fail, and nothing else: %s" % (mutant, ", ".join(MUTANTS[mutant][2])))
        section_tools(box)
    finally:
        if original_ide is not None:
            with open(ide_path, "w", encoding="latin-1") as fh:
                fh.write(original_ide)
            ok, out = compile_ide(box)
            say("sandbox-ide-tools: the sandbox's ide put back and compiled again: %s" % ("yes" if ok else "NO\n" + out[-400:]))
        subprocess.run([sys.executable, TOOL, box, "stop"], capture_output=True, text=True, errors="replace", timeout=120)
    say("\nsandbox-ide-tools: %d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        bail("no row ran - a broken test, not a pass")
    if mutant is not None:
        want = sorted(MUTANTS[mutant][2])
        got = sorted(set(FAILED))
        ok = want == got
        say("sandbox-ide-tools: MUTANT %s: the rows that failed are %s; they had to be exactly %s -> %s" % (mutant, got, want, "KILLED BY ITS OWN ROWS" if ok else "NOT AS EXPECTED"))
        return 0 if ok else 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
