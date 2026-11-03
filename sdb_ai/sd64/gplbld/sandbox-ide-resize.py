#!/usr/bin/env python3
#
# sandbox-ide-resize.py - the IDE across a window resize (S.88 p3.3a) and the IDE's theme (S.88 p3.7b), on a pseudo-terminal on a private SD.  No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-ide-resize.py <dir> [--build] --only=resize,theme [--mutant=NAME]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 every row passed,
# 1 a row failed, 2 it could not run.  --only names the sections (resize, theme; both by default).  With --mutant=NAME one change is made to the SANDBOX'S OWN COPY of `ide`,
# compiled, the section it belongs to is run, and exit 0 means exactly its rows failed; the copy is put back and compiled again afterwards.
#
# START-HISTORY:
# 2 Nov 26 dm  New (S.88 p3.3a and p3.7b).
# END-HISTORY
#
#   resize (about 40 s)  a record is opened, ZZQ typed on line 1, Ctrl-F finds "needle" (line 2, selected); the window goes to 160 by 50 and back to 140 by 43; then
#     Z1  control: the layout followed (160 wide, the status line on row 47) and the record is still open
#     Z2  the separator lost the rows the form lost: after the shrink the form's bottom border (row 39) is whole at the separator's column (28) and rows 40-42 hold no |
#     Z3  control: the typed text is still in the editor (both the old and the new IDE keep the TEXT: stash.current)
#     Z4  THE MARK: Ctrl-X cuts the selection the find made before the resize - "needle" goes from line 2
#     Z5  THE UNDO STEPS: Ctrl-Z twice puts back the cut and takes away the typing (line 1 is alpha again)
#     Z6  THE FIND TEXT: from line 3, F3 finds the next "needle" (line 4) without asking for it again
#   theme (about 25 s)  the colour of the menu bar's background, read from the emulated screen's cells: blue's bar is black on cyan (6), classic's black on white (7)
#     T0  control: the sandbox's sd.conf names no SCREENTHEME: the IDE is blue, as it always was
#     T1  SCREENTHEME=classic: the IDE opens in classic (red on the IDE that started blue whatever the site said)
#     T2  SCREENTHEME=nosuch (no theme of that name): the IDE falls back to blue, not to mono
# Mutants (each is run against its own section): rebuild (relayout makes the form again: Z4 Z5 Z6), blue-first (the IDE ignores SCREENTHEME: T1).
import importlib.util
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
_spec = importlib.util.spec_from_file_location("sandbox_ide_for_resize", os.path.join(HERE, "sandbox-ide.py"))
sb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sb)

TOOL = os.path.join(HERE, "sandbox-fromtree.py")
RUN = "%05d" % (os.getpid() % 100000)
SECTIONS = ("resize", "theme")
CTRL_X, CTRL_Z = "\x18", "\x1a"
passed = failed = 0
FAILED = []

MUTANTS = {
    # name: (section, old text of the sandbox's ide, new text, the rows that must fail and no others)
    "rebuild": ("resize", "   if have.form then\n      gosub move.form\n", "   if have.form then\n      gosub new.form\n", ["Z4", "Z5", "Z6"]),
    "blue-first": ("theme", "   th.want = downcase(trim(config('SCREENTHEME')))\n", "   th.want = ''\n", ["T1"]),
}


def say(s=""):
    print(s, flush=True)


def bail(msg):
    say("sandbox-ide-resize: CANNOT RUN - " + msg)
    sys.exit(2)


def row(rid, name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        say("  [PASS] %s %s" % (rid, name))
    else:
        failed += 1
        FAILED.append(rid)
        say("  [FAIL] %s %s%s" % (rid, name, ("   <- " + detail[:600]) if detail else ""))


def ed_line(L, i):
    """line i (1-based) of the editor as shown: rows 3 on, from column 29 (after the tree and the separator) to before the scroll bar and the form's border (the last
    two columns), the mark cell and the line number taken off"""
    if 2 + i >= len(L):
        return ""
    return re.sub(r"^[ *]?\s*\d+ ", "", L[2 + i][29:-2]).rstrip()


def compile_ide(box):
    env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"), SDTEST_ADMIN="1")
    env.pop("SSH_CONNECTION", None)
    env.pop("SSH_TTY", None)
    say("    > [admin] [internal] in sys: BASIC gpl.bp ide")
    p = subprocess.run([os.path.join(box, "sys", "bin", "sd"), "-internal"], input="\nTERM 200,9999\nBASIC gpl.bp ide\nOFF\n", cwd=os.path.join(box, "sys"), env=env,
                       capture_output=True, text=True, errors="replace", timeout=600)
    out = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", p.stdout + p.stderr)
    return "Compiled 1 program(s) with no errors" in out, out


def section_resize(box):
    say("\n--- resize: the editor's state across a window resize ---------------------------------------------------")
    rid = "zzrz" + RUN
    with open(os.path.join(box, "sys", "bp", "zzrzfx" + RUN), "w") as fh:
        fh.write("   open 'bp' to f else stop 'no bp'\n   write 'alpha':@fm:'the needle is here':@fm:'beta':@fm:'another NEEDLE line':@fm:'gamma' on f, '%s'\n"
                 "   crt 'FIX':'TURE DONE'\nend\n" % rid)
    out = sb.sess(box, "BASIC bp zzrzfx%s" % RUN, "RUN bp zzrzfx%s" % RUN)
    if "FIXTURE DONE" not in out:
        bail("the fixture record was not made:\n" + out[-500:])
    e = sb.Ide(box, "IDE bp %s" % rid)
    try:
        e.keys("ZZQ")
        e.keys(sb.CTRL_F)
        e.keys("needle", sb.RET)
        L = e.quiet()
        row("Z0", "setup: ZZQ typed on line 1 and the find stopped on line 2", ed_line(L, 1).startswith("ZZQalpha") and "Line 2," in e.status(),
            repr((ed_line(L, 1), e.status())))
        e.s.resize(160, 50, idle=1.5)
        time.sleep(1.8)
        e.s.settle(0.8)
        L = e.lines()
        row("Z1", "control: at 160 by 50 the frame is 160 wide, the status line is row 47 and the record is still open",
            len(L) > 47 and len(L[1].rstrip()) == 160 and rid in L[47], repr(L[1][-6:]) + repr(L[47][:40] if len(L) > 47 else None))
        e.s.resize(140, 43, idle=1.5)
        time.sleep(1.8)
        e.s.settle(0.8)
        L = e.lines()
        col = [l[28] if len(l) > 28 else " " for l in L[38:43]]
        row("Z2", "after the shrink to 140 by 43 the form's bottom border is whole at the separator's column and nothing of the separator is below it",
            len(L) == 43 and L[39][28] in "-+" and L[38][28] == "|" and "|" not in col[2:], repr(col) + "\n" + "\n".join(l[20:40] for l in L[37:43]))
        row("Z3", "control: the typed text is still in the editor (line 1 ZZQalpha, line 2 holds needle)",
            ed_line(L, 1).startswith("ZZQalpha") and "needle" in ed_line(L, 2), repr((ed_line(L, 1), ed_line(L, 2))))
        L = e.keys(CTRL_X)
        row("Z4", "the selection the find made before the resize is still there: Ctrl-X cuts needle from line 2",
            ed_line(L, 2).startswith("the ") and "needle" not in ed_line(L, 2) and "is here" in ed_line(L, 2), repr(ed_line(L, 2)))
        e.keys(CTRL_Z)
        L = e.keys(CTRL_Z)
        row("Z5", "the undo steps from before the resize are still there: Ctrl-Z twice gives back the cut and takes the typing away",
            ed_line(L, 1) == "alpha" and ed_line(L, 2).startswith("the needle is here"), repr((ed_line(L, 1), ed_line(L, 2))))
        e.keys(sb.CTRL_L)
        e.keys("3", sb.RET)
        e.quiet()
        e.keys(sb.F3)
        L = e.quiet()
        row("Z6", "the find text from before the resize is still there: F3 from line 3 goes to line 4 without asking",
            "Line 4," in e.status(), repr(e.status()) + "\n" + "\n".join(l[29:90] for l in L[36:40]))
    finally:
        e.s.finish()
        for d in ("bp", "bp.out"):
            for nm in (rid, "zzrzfx" + RUN):
                pth = os.path.join(box, "sys", d, nm)
                if os.path.exists(pth):
                    os.remove(pth)


def bar_style(e):
    """the look of a blank cell of the menu bar (row 0) between two menu names: the bar's own style, not a mnemonic's"""
    L = e.lines()
    top = L[0] if L else ""
    m = re.search(r"\S  ", top)
    if not m:
        return None, top
    return e.s.screen.style(0, m.start() + 1), top


def section_theme(box):
    say("\n--- theme: the IDE opens in the site's theme -------------------------------------------------------------")
    conf = os.path.join(box, "sd.conf")
    with open(conf) as fh:
        original = fh.read()
    base = re.sub(r"(?m)^SCREENTHEME=.*\n?", "", original)
    try:
        for rid, line, want, what in (("T0", None, 6, "control: no SCREENTHEME line - blue (black on cyan), as the IDE always was"),
                                      ("T1", "classic", 7, "SCREENTHEME=classic - the IDE opens in classic (black on white)"),
                                      ("T2", "nosuch", 6, "SCREENTHEME=nosuch (no such theme) - the IDE falls back to blue, not mono")):
            with open(conf, "w") as fh:
                fh.write(base.rstrip("\n") + "\n" + ("SCREENTHEME=%s\n" % line if line else ""))
            e = sb.Ide(box, "IDE")
            st, top = bar_style(e)
            row(rid, what, st is not None and st[:2] == (0, want) and "File" in top, repr((st, top[:60])))
            e.s.finish()
    finally:
        with open(conf, "w") as fh:
            fh.write(original)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    only = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--only=")), ",".join(SECTIONS)).split(",")
    mutant = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mutant=")), None)
    if len(args) != 1 or any(s not in SECTIONS for s in only) or (mutant is not None and mutant not in MUTANTS):
        bail("usage: sandbox-ide-resize.py <dir> [--build] [--only=%s] [--mutant=%s]" % (",".join(SECTIONS), "|".join(MUTANTS)))
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-ide-resize: sandbox %s, keyset %s, sections %s%s" % (box, os.environ.get("SDBOX_KEYSET", "0"), ",".join(only), ", mutant " + mutant if mutant else ""))
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-ide-resize: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)
    ide_path = os.path.join(sysd, "gpl.bp", "ide")
    original_ide = None
    try:
        if mutant is not None:
            sec, old, new, _ = MUTANTS[mutant]
            src = open(ide_path, encoding="latin-1").read()
            if src.count(old) != 1:
                bail("mutant %s: the text to change is found %d times, not once" % (mutant, src.count(old)))
            original_ide = src
            with open(ide_path, "w", encoding="latin-1") as fh:
                fh.write(src.replace(old, new))
            ok, out = compile_ide(box)
            if not ok:
                bail("the mutant IDE did not compile:\n" + out[-600:])
            only = [sec]
            say("sandbox-ide-resize: MUTANT %s: the rows that must fail, and nothing else: %s" % (mutant, ", ".join(MUTANTS[mutant][3])))
        if "resize" in only:
            section_resize(box)
        if "theme" in only:
            section_theme(box)
    finally:
        if original_ide is not None:
            with open(ide_path, "w", encoding="latin-1") as fh:
                fh.write(original_ide)
            ok, out = compile_ide(box)
            say("sandbox-ide-resize: the sandbox's ide put back and compiled again: %s" % ("yes" if ok else "NO\n" + out[-400:]))
        subprocess.run([sys.executable, TOOL, box, "stop"], capture_output=True, text=True, errors="replace", timeout=120)
    say("\nsandbox-ide-resize: %d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        bail("no row ran - a broken test, not a pass")
    if mutant is not None:
        want = sorted(MUTANTS[mutant][3])
        got = sorted(set(FAILED))
        ok = want == got
        say("sandbox-ide-resize: MUTANT %s: the rows that failed are %s; they had to be exactly %s -> %s" % (mutant, got, want, "KILLED BY ITS OWN ROWS" if ok else "NOT AS EXPECTED"))
        return 0 if ok else 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
