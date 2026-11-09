#!/usr/bin/env python3
#
# sandbox-memokeys.py - the IDE editor's own keys (S.88 D2: the memo's edkeys and overwrite mode), on a pseudo-terminal on a private SD.  No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-memokeys.py <dir> [--build] --only=keys
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 every row passed,
# 1 a row failed, 2 it could not run.  One section, keys (about 40 s); --only is taken so that the testing hook's rule holds for it as for the other suites.
#
# START-HISTORY:
# 2 Nov 26 dm  New (S.88 d2a: the suite test-memokeys-units.py named and nobody had written).
# 9 Nov 26 dm  Section sed (S.184 stage 2): SED's editing commands in the area, S0-S13 (Alt-C, U, L, T, Backspace, Space, E, A, D, M; undo; the disk unchanged).
#              Not held: the nudge (Ctrl-Up / Ctrl-Down: the record is too short to scroll) and a terminal other than xterm.
# END-HISTORY
#
# The record is three lines: "alpha beta gamma", "   indented", "three".  The keys are sent as xterm sends them (sandbox-realkeys.py's table) and every row reads the
# status line's "Line N, column M" or the editor's text from the emulated screen; nothing is saved (the record on the disk is read at the end and must be unchanged).
#   K1  Ctrl-End: the end of the text (line 3, column 6)        K2  Ctrl-Home: line 1, column 1
#   K3  Ctrl-Right: the end of the word (column 6), K4 again: over the blank and the next word (column 11)
#   K5  Ctrl-Left: back to the start of that word (column 7)
#   K6  Ctrl-Del at column 7 deletes the word "beta" (line 1 is "alpha  gamma")       K7  Ctrl-Z puts it back (one undo step)
#   K8  Ins: the status line says overwrite, and X typed replaces the b of beta ("alpha Xeta gamma")
#   K9  Ins again: insert mode, Y typed is put in ("alpha XYeta gamma")
#   K10 control: the record on the disk is as the fixture wrote it (nothing was saved)
# NOT HERE: the 20,000-line measure (sandbox-ide-big.py, not written), auto-indent and the tab width (menu entries), a terminal other than xterm.
import importlib.util
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
_spec = importlib.util.spec_from_file_location("sandbox_ide_for_memokeys", os.path.join(HERE, "sandbox-ide.py"))
sb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sb)

TOOL = os.path.join(HERE, "sandbox-fromtree.py")
RUN = "%05d" % (os.getpid() % 100000)
E = "\x1b"
CTRL_HOME, CTRL_END, CTRL_LEFT, CTRL_RIGHT, CTRL_DEL, INS = E + "[1;5H", E + "[1;5F", E + "[1;5D", E + "[1;5C", E + "[3;5~", E + "[2~"
CTRL_Z = "\x1a"
passed = failed = 0


def say(s=""):
    print(s, flush=True)


def bail(msg):
    say("sandbox-memokeys: CANNOT RUN - " + msg)
    sys.exit(2)


def row(rid, name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        say("  [PASS] %s %s" % (rid, name))
    else:
        failed += 1
        say("  [FAIL] %s %s%s" % (rid, name, ("   <- " + detail[:400]) if detail else ""))


def ed_line(L, i):
    """line i (1-based) of the editor: rows 3 on, columns 29 to before the scroll bar and the border, the mark cell and the line number taken off"""
    if 2 + i >= len(L):
        return ""
    return re.sub(r"^[ *]?\s*\d+ ", "", L[2 + i][29:-2]).rstrip()


def at(e):
    m = re.search(r"Line (\d+), column (\d+)", e.status())
    return (int(m.group(1)), int(m.group(2))) if m else None


def section_keys(box):
    say("\n--- keys: the editor's keys ------------------------------------------------------------------------------")
    rid = "zzmk" + RUN
    fx = "zzmkfx" + RUN
    with open(os.path.join(box, "sys", "bp", fx), "w") as fh:
        fh.write("   open 'bp' to f else stop 'no bp'\n   write 'alpha beta gamma':@fm:'   indented':@fm:'three' on f, '%s'\n   crt 'FIX':'TURE DONE'\nend\n" % rid)
    out = sb.sess(box, "BASIC bp %s" % fx, "RUN bp %s" % fx)
    if "FIXTURE DONE" not in out:
        bail("the fixture record was not made:\n" + out[-500:])
    before = sb.rec_text(box, rid)
    e = sb.Ide(box, "IDE bp %s" % rid)
    try:
        e.quiet()
        row("K0", "setup: the record is open with the cursor at line 1, column 1", at(e) == (1, 1) and ed_line(e.lines(), 1) == "alpha beta gamma", repr((at(e), e.status())))
        for k_id, key, want, what in (("K1", CTRL_END, (3, 6), "Ctrl-End goes to the end of the text"),
                                      ("K2", CTRL_HOME, (1, 1), "Ctrl-Home goes to the start of the text"),
                                      ("K3", CTRL_RIGHT, (1, 6), "Ctrl-Right goes to the end of the word"),
                                      ("K4", CTRL_RIGHT, (1, 11), "Ctrl-Right again: over the blank and the next word"),
                                      ("K5", CTRL_LEFT, (1, 7), "Ctrl-Left goes back to the start of that word")):
            e.keys(key)
            e.quiet()
            row(k_id, "%s (line %d, column %d)" % ((what,) + want), at(e) == want, repr(e.status()))
        L = e.keys(CTRL_DEL)
        row("K6", "Ctrl-Del at column 7 deletes the word beta", ed_line(L, 1) == "alpha  gamma", repr(ed_line(L, 1)))
        L = e.keys(CTRL_Z)
        row("K7", "Ctrl-Z puts the word back (one undo step)", ed_line(L, 1) == "alpha beta gamma", repr(ed_line(L, 1)))
        e.keys(INS)
        e.quiet()
        st = e.status()
        L = e.keys("X")
        row("K8", "Ins turns overwrite on (said on the status line) and X replaces the b of beta", "overwrite" in st.lower() and ed_line(L, 1) == "alpha Xeta gamma", repr((st, ed_line(L, 1))))
        e.keys(INS)
        L = e.keys("Y")
        row("K9", "Ins again: insert mode, Y is put in", ed_line(L, 1) == "alpha XYeta gamma", repr(ed_line(L, 1)))
    finally:
        e.s.finish()
    after = sb.rec_text(box, rid)
    row("K10", "control: the record on the disk is as the fixture wrote it (nothing was saved)", "alpha beta gamma" in after and after == before, repr(after[-200:]))
    for d in ("bp", "bp.out"):
        for nm in (rid, fx):
            pth = os.path.join(box, "sys", d, nm)
            if os.path.exists(pth):
                os.remove(pth)


ALT = lambda ch: E + ch          # noqa: E731  (a terminal sends Alt+x as Esc and x)
HOME, DOWN = E + "[1~", E + "[B"


def section_sed(box):
    """9 Nov 26 (S.184 stage 2): SED's editing commands in the area.  The record is the same three lines; every row reads line 1 or 2 and the cursor."""
    say("\n--- sed: SED's editing commands in the editor (S.184 stage 2) ------------------------------------------------")
    rid = "zzms" + RUN
    fx = "zzmsfx" + RUN
    with open(os.path.join(box, "sys", "bp", fx), "w") as fh:
        fh.write("   open 'bp' to f else stop 'no bp'\n   write 'alpha beta gamma':@fm:'   indented':@fm:'three' on f, '%s'\n   crt 'FIX':'TURE DONE'\nend\n" % rid)
    out = sb.sess(box, "BASIC bp %s" % fx, "RUN bp %s" % fx)
    if "FIXTURE DONE" not in out:
        bail("the fixture record was not made:\n" + out[-500:])
    before = sb.rec_text(box, rid)
    e = sb.Ide(box, "IDE bp %s" % rid)
    try:
        e.quiet()
        row("S0", "setup: the record is open with the cursor at line 1, column 1", at(e) == (1, 1) and ed_line(e.lines(), 1) == "alpha beta gamma", repr((at(e), e.status())))
        L = e.keys(ALT("c"))
        e.quiet()
        row("S1", "Alt-C gives the word a capital initial and goes to its end", ed_line(L, 1) == "Alpha beta gamma" and at(e) == (1, 6), repr((ed_line(L, 1), at(e))))
        L = e.keys(ALT("u"))
        e.quiet()
        row("S2", "Alt-U puts the next word in capitals (from the blank before it)", ed_line(L, 1) == "Alpha BETA gamma" and at(e) == (1, 11), repr((ed_line(L, 1), at(e))))
        e.keys(CTRL_LEFT)
        L = e.keys(ALT("l"))
        e.quiet()
        row("S3", "Alt-L puts it in small letters again", ed_line(L, 1) == "Alpha beta gamma" and at(e) == (1, 11), repr((ed_line(L, 1), at(e))))
        L = e.keys(ALT("t"))
        e.quiet()
        row("S4", "Alt-T at column 11 swaps the a before the cursor and the blank at it, and moves on", ed_line(L, 1) == "Alpha bet agamma" and at(e) == (1, 12), repr((ed_line(L, 1), at(e))))
        L = e.keys(CTRL_Z)
        e.quiet()
        row("S5", "Ctrl-Z undoes the swap in one step", ed_line(L, 1) == "Alpha beta gamma", repr(ed_line(L, 1)))
        e.keys(HOME, CTRL_RIGHT, CTRL_RIGHT)
        e.quiet()
        L = e.keys(ALT("\x7f"))
        e.quiet()
        row("S6", "Alt-Backspace after beta deletes the word before the cursor", ed_line(L, 1) == "Alpha  gamma" and at(e) == (1, 7), repr((ed_line(L, 1), at(e))))
        L = e.keys(ALT(" "))
        e.quiet()
        row("S7", "Alt-Space closes the two blanks into one", ed_line(L, 1) == "Alpha gamma" and at(e) == (1, 7), repr((ed_line(L, 1), at(e))))
        L = e.keys(ALT("e"))
        e.quiet()
        row("S8", "Alt-E cuts from the cursor to the end of the line", ed_line(L, 1) == "Alpha" and at(e) == (1, 7), repr((ed_line(L, 1), at(e))))
        L = e.keys("\x16")
        e.quiet()
        row("S9", "...and Ctrl-V pastes what it cut back", ed_line(L, 1) == "Alpha gamma", repr(ed_line(L, 1)))
        e.keys(DOWN)
        L = e.keys(ALT("a"))
        e.quiet()
        row("S10", "Alt-A on line 2 indents it as line 1 is (not at all): the three blanks go", ed_line(L, 2) == "indented", repr(ed_line(L, 2)))
        e.keys(HOME)
        L = e.keys(ALT("d"))
        e.quiet()
        row("S11", "Alt-D deletes the word at the cursor, as Ctrl-Del does", ed_line(L, 2) == "", repr(ed_line(L, 2)))
        e.keys(CTRL_Z, CTRL_Z)
        e.keys(HOME, "\x07", sb.END)                  # Ctrl-G sets the mark at column 1, End takes the cursor to the end: the selection is the line
        e.quiet()
        c_end = at(e)
        e.keys(ALT("m"))
        e.quiet()
        c_swap = at(e)
        row("S12", "Alt-M with a selection (Ctrl-G, then End) swaps the cursor and the mark (end of line to column 1)",
            c_end is not None and c_end[1] > 1 and c_swap == (c_end[0], 1), repr((c_end, c_swap)))
    finally:
        e.s.finish()
    after = sb.rec_text(box, rid)
    row("S13", "control: the record on the disk is as the fixture wrote it (nothing was saved)", "alpha beta gamma" in after and after == before, repr(after[-200:]))
    for d in ("bp", "bp.out"):
        for nm in (rid, fx):
            pth = os.path.join(box, "sys", d, nm)
            if os.path.exists(pth):
                os.remove(pth)


SECTIONS = {"keys": section_keys, "sed": section_sed}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    only = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--only=")), "keys,sed").split(",")
    if len(args) != 1 or not only or any(s not in SECTIONS for s in only):
        bail("usage: sandbox-memokeys.py <dir> [--build] [--only=keys,sed]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-memokeys: sandbox %s, keyset %s" % (box, os.environ.get("SDBOX_KEYSET", "0")))
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-memokeys: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)
    try:
        for s in only:
            SECTIONS[s](box)
    finally:
        subprocess.run([sys.executable, TOOL, box, "stop"], capture_output=True, text=True, errors="replace", timeout=120)
    say("\nsandbox-memokeys: %d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        bail("no row ran - a broken test, not a pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
