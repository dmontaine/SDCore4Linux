#!/usr/bin/env python3
#
# sandbox-ide-sed.py - Part B of the 140x42 plan: Ctrl-E in the IDE hands the record to SED, and SED's save (or leaving it) brings the IDE
#                      back.  No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-ide-sed.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or absent); without it
# <dir> must already be built, which is how the same script is run against an OLD tree to prove it can fail.  Exit 0 every row passed,
# 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 18 Oct 26 dm  New (plan-terminal-140x42.md, Part B).
# 28 Oct 26 dm  F3 is the editor's find next, not the tree: the tree is reached with ID.GOTO_TREE (Shift-F6 twice); the Go menu has Previous pane,
#               so Edit in SED is its eighth entry.
# END-HISTORY
#
# HOW IT DRIVES THEM.  The IDE and SED run on ONE pseudo-terminal at 140 by 42 (ptydrive.py, the screen read from termscreen.py), the keys
# typed as a person types them: Ctrl-E in the IDE, then SED's own keys (Ctrl-S saves, Ctrl-Q leaves, y answers "quit without saving").
# What the hand-over DID to the data is read from the data afterwards (CT through a pipe session), never from what either program said.
# Every record the suite makes is its own (zzie + the run's number).
#
# THE CONTROLS.  Each outcome row follows a row that shows the state before it (the IDE's menu bar on the top row before Ctrl-E, SED's
# status line after it), so a key that did nothing cannot pass for one that worked; the compile errors are made and seen BEFORE the
# hand-over, so "the table is empty afterwards" means something.
#
# THE MUTANTS (the suite is run against copies of the sandbox's programs with one change each; the rows that must fail are named):
#   the SED that does not end its edit on a save    row "SED's save returns to the IDE"
#   the IDE that does not read the record again     row "the editor shows what SED saved"
#   the IDE that hands over without saving         rows of the changed-buffer section
# They are not built into this file: see the status entry of 18 Oct 26 for what was run.

import importlib.util
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
spec = importlib.util.spec_from_file_location("ideM", os.path.join(HERE, "sandbox-ide.py"))
ID = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ID)

TOOL = os.path.join(HERE, "sandbox-fromtree.py")
RUN = ID.RUN
F8, F10, DOWN, RIGHT, RET, ESC, END = ID.F8, ID.F10, ID.DOWN, ID.RIGHT, ID.RET, ID.ESC, ID.END   # F8 is compile since S.88 Phase 4 (F7 is debug)
CTRL = lambda ch: chr(ord(ch.upper()) - 64)         # noqa: E731
CTRL_E, CTRL_Q, CTRL_S = CTRL("e"), CTRL("q"), CTRL("s")

passed = failed = 0


def say(s=""):
    print(s)


def row(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        say("  [PASS] " + name)
    else:
        failed += 1
        say("  [FAIL] " + name + ("   <- " + detail if detail else ""))


def bail(msg):
    say("sandbox-ide-sed: CANNOT RUN - " + msg)
    sys.exit(2)


class IdeK(ID.Ide):
    """The IDE suite's run of the IDE on a pty, with the wait after a key as an argument."""

    def keys(self, *chunks, idle=0.6):
        for chunk in chunks:
            self.log.append(chunk)
            self.s.type(chunk, idle=idle)
        return self.lines()


def in_sed(L):
    """SED's screen: its status line (… | line.column) is the last row, and the IDE's menu bar is not on the top row."""
    return re.search(r"\|\s*\d+\.\d+", "\n".join(L[-3:])) is not None and "Build" not in L[0]


def in_ide(L):
    return re.search(r"File\s+Go\s+Search\s+Build\s+View\s+Help", L[0]) is not None


def wait(e, secs=2.2):
    """SED takes a moment to start or to end; the IDE's status line follows within a second of quiet."""
    time.sleep(secs)
    e.s.settle(0.5)
    return e.lines()


def leave_sed(e):
    """Ctrl-Q in SED, and y to 'Quit without saving?' ONLY IF SED asks (it does not when nothing changed, and a y then goes to the IDE)."""
    L = e.keys(CTRL_Q, idle=1.0)
    if in_sed(L):
        L = e.keys("y", idle=1.0)
    return wait(e)


def line_of(e):
    m = re.search(r"Line (\d+), column (\d+)", e.status())
    return (int(m.group(1)), int(m.group(2))) if m else None


def table_empty(L):
    """The error table (below the editor) holds no row: only blanks between the frame and the scroll bar."""
    return all(not l[30:136].strip() for l in L[35:39])           # rows 35 to 38: the table's last rows; row 39 is the form's bottom border (the IDE's foot, 28 Oct 26)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-ide-sed.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-ide-sed: sandbox %s" % box)
    say("sandbox-ide-sed: tree    %s" % os.path.dirname(HERE))
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-ide-sed: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    P, Q, L1, L2, R2 = ("zzie%s%s" % (RUN, c) for c in "pqlmr")   # a program with an error, a plain text, two records for the lock row, a second buffer
    SP = "zz1 sp" + RUN                                         # an id with a blank in it; sorts before the others, so the tree's z key finds it
    fixture = """   open 'bp' to f else stop 'no bp'
   write 'crt "one"':@fm:'x = = 1':@fm:'crt "three"':@fm:'end' on f, '%(p)s'
   write 'first':@fm:'second':@fm:'third' on f, '%(q)s'
   write 'locked text':@fm:'second line' on f, '%(l1)s'
   write 'blank one':@fm:'blank two' on f, '%(sp)s'
   write 'rr1':@fm:'rr2' on f, '%(r2)s'
   crt 'FIXTURE DONE'
end
""" % {"p": P, "q": Q, "l1": L1, "sp": SP, "r2": R2}
    holder = """   open 'bp' to f else stop 'no bp'
   readu r from f, '%(l1)s' else stop 'no record'
   crt 'HOLDING'
   sleep 45
   release f, '%(l1)s'
end
""" % {"l1": L1}
    fix, hold = "zziefx" + RUN, "zzieho" + RUN
    for nm, src in ((fix, fixture), (hold, holder)):
        with open(os.path.join(sysd, "bp", nm), "w") as fh:
            fh.write(src)
    try:
        say("\n--- fixture --------------------------------------------------------------------------------------")
        out = ID.sess(box, "BASIC bp %s" % fix, "RUN bp %s" % fix, "BASIC bp %s" % hold)
        row("setup: the fixture program compiled and made the records", "FIXTURE DONE" in out, out[-300:])
        if "FIXTURE DONE" not in out:
            bail("the fixture was not made:\n" + out[-600:])
        row("setup: SED and the IDE are in the sandbox", os.path.isfile(os.path.join(sysd, "gpl.bp", "sed")) and os.path.isfile(os.path.join(sysd, "gpl.bp", "ide")), "missing")

        # ---- the key, SED's save, and what comes back -----------------------------------------------------------------
        say("\n--- Ctrl-E: the record goes to SED; SED's save returns to the IDE with the new text ---------------------------")
        e = IdeK(box, "IDE bp %s" % P)
        scr = e.s.screen
        L = e.keys(F8)
        row("control: the IDE shows the record and its compile errors (the table has the error before the hand-over)",
            in_ide(L) and "1 error(s)" in e.status() and not table_empty(L), e.status() + " | " + " ".join(l[30:80] for l in L[35:38]))
        L = e.keys(CTRL_E)
        L = wait(e)
        row("Ctrl-E opens SED on the record: its status line is up, the IDE's menu bar is gone, the first line is the record's",
            in_sed(L) and 'crt "one"' in "\n".join(L[:4]), "\n".join(l[:60] for l in L[:3]) + " | " + L[-1][:80])
        e.keys("ZZ", idle=0.5)
        L = e.keys(CTRL_S, idle=0.5)
        L = wait(e)
        row("SED's save returns to the IDE (its menu bar is back on the top row)", in_ide(L), "\n".join(l[:60] for l in L[:3]) + " | " + L[-1][:80])
        row("...the editor shows what SED saved (ZZ at the start of line 1) and the status line says it is saved",
            "ZZcrt" in "\n".join(L[2:8]) and "Back from SED" in e.status() and " *" not in e.status().split("Back")[0], e.status() + " | " + L[3][28:80])
        row("...the record on disk has it (read back through CT)", "ZZcrt" in ID.rec_text(box, P), ID.rec_text(box, P)[-200:])
        row("...the compile errors are gone: the table is empty (they named lines of the old text)", table_empty(L), "\n".join(l[30:100] for l in L[34:39]))
        row("...the cursor is shown, in the editor", scr.cursor_visible and 2 <= scr.r <= 33 and scr.c >= 29, repr((scr.r, scr.c, scr.cursor_visible)))
        e.quiet()
        at0 = line_of(e)
        L = e.keys(ID.DOWN, idle=1.2)
        L = e.quiet()
        at1 = line_of(e)
        row("...and the IDE's keys work again: Down moves the editor's cursor one line (%r to %r)" % (at0, at1),
            at0 is not None and at1 is not None and at1[0] == at0[0] + 1, e.status())

        say("\n--- leaving SED without saving returns too, and nothing changes --------------------------------------------------")
        before = ID.rec_text(box, P)
        L = e.keys(CTRL_E)
        L = wait(e)
        row("control: Ctrl-E again opens SED", in_sed(L), L[-1][:80])
        e.keys("YY", idle=0.5)
        L = e.keys(CTRL_Q, idle=1.0)
        row("control: with typing in it SED asks before it lets go (a box 'Record changed.  Quit without saving?')",
            in_sed(L) and "without saving" in "\n".join(L).lower(), "\n".join(l[40:100] for l in L[17:24]))
        L = e.keys("y", idle=1.0)
        L = wait(e)
        row("Ctrl-Q, y leaves SED and returns to the IDE", in_ide(L), "\n".join(l[:60] for l in L[:3]) + " | " + L[-1][:80])
        row("...the editor and the disk are as they were (no YY), and the status line says so",
            "YY" not in "\n".join(L[2:8]) and "YY" not in ID.rec_text(box, P) and ID.rec_text(box, P) == before and "is as it was" in e.status(),
            e.status() + " | " + L[3][28:80])
        e.end()

        say("\n--- a changed buffer is saved first, or the hand-over is cancelled --------------------------------------------------")
        e = IdeK(box, "IDE bp %s" % Q)
        scr = e.s.screen
        L = e.keys("QQ")
        e.quiet()
        row("control: typing marks the record changed (a star in the status line) and the disk does not have it",
            " *" in e.status() and "QQ" not in ID.rec_text(box, Q), e.status())
        L = e.keys(CTRL_E, idle=1.0)
        row("Ctrl-E on a changed record asks 'Save them, then edit in SED?' and SED is not started", "has changes" in "\n".join(L) and "edit in SED" in "\n".join(L) and in_ide(L),
            "\n".join(l[:80] for l in L[14:24]))
        L = e.keys("c", idle=1.0)
        L = e.quiet()
        row("Cancel leaves everything as it was: in the IDE, still changed, the disk without QQ", in_ide(L) and " *" in e.status() and "QQ" not in ID.rec_text(box, Q),
            e.status() + " | " + ID.rec_text(box, Q)[-80:])
        L = e.keys(CTRL_E, idle=1.0)
        L = e.keys(RET, idle=0.5)                           # Save is the default button
        L = wait(e)
        row("Save writes the buffer, then SED opens on it (QQ is in SED's first line)", in_sed(L) and "QQ" in L[1] and "QQ" in ID.rec_text(box, Q),
            L[1][:60] + " | " + ID.rec_text(box, Q)[-80:])
        L = leave_sed(e)
        row("leaving SED returns to the IDE, the buffer is not changed any more (it is on disk)", in_ide(L) and " *" not in e.status(), e.status())
        e.end()

        say("\n--- the menu entry -------------------------------------------------------------------------------------------")
        e = IdeK(box, "IDE bp %s" % P)
        L = e.keys(F10, RIGHT)
        row("the Go menu lists Edit in SED with its key, ^E", any("Edit in SED" in l and "^E" in l for l in L[1:12]), "\n".join(l[:60] for l in L[:10]))
        L = e.keys(DOWN * 7, RET, idle=0.8)                 # the eighth entry of Go: Go to line, Next error, Next tab, Previous tab, Files and records, Next pane, Previous pane, Edit in SED
        L = wait(e)
        row("choosing it opens SED on the record", in_sed(L), L[-1][:80])
        L = leave_sed(e)
        row("...and leaving returns to the IDE", in_ide(L) and " *" not in e.status(), L[0][:60] + " | " + e.status())
        e.end()

        say("\n--- the editor still ends a row with End; Ctrl-E is the IDE's now --------------------------------------------------")
        e = IdeK(box, "IDE bp %s" % P)
        L = e.keys(END)
        L = e.quiet()
        m = re.search(r"column (\d+)", e.status())
        row("End moves the cursor to the end of the row (the status line reads a column past 1)", m is not None and int(m.group(1)) > 1, e.status())
        e.end()

        say("\n--- a record id with a blank in it goes to SED whole (the verifier's F1, 19 Oct 26) ----------------------------------")
        e = IdeK(box)
        e.keys(*ID.GOTO_TREE, "b", RET)                   # Shift-F6 twice to the tree (F3 is find next): the focus starts in the Untitled editor since S.88 Phase 4
        L = e.keys("z", RET)
        row("control: the record %r is open in the IDE, opened from the tree (its tab, its first line)" % SP,
            ("[%s]" % SP) in L[2] and "blank one" in "\n".join(L[3:6]), L[2][:90] + " | " + L[3][28:70])
        e.keys(CTRL_E, idle=1.0)
        L = wait(e)
        row("Ctrl-E opens SED on THAT record: its first line is the record's and SED does not say 'New record'",
            in_sed(L) and "blank one" in L[1] and "new record" not in "\n".join(L[-3:]).lower(), L[1][:60] + " | " + L[-1][:80])
        e.keys("Q", idle=0.5)
        e.keys(CTRL_S, idle=0.8)
        L = wait(e)
        txt = ID.sess(box, 'CT bp "%s"' % SP)
        row("...its save returns to the IDE and the record under its whole id now begins Qblank one", in_ide(L) and "Qblank one" in txt, e.status() + " | " + txt[-120:])
        e.end()

        say("\n--- a save in a second buffer of SED does not end the edit and lose the first (the verifier's F2) --------------------")
        e = IdeK(box, "IDE bp %s" % Q)
        e.keys(CTRL_E, idle=1.0)
        L = wait(e)
        e.keys("AA", idle=0.5)
        L = e.keys(CTRL("o"), idle=1.0)
        say("      screen after Ctrl-O: " + " | ".join(l.strip()[:70] for l in L if l.strip())[:300])
        e.keys("bp %s" % R2, idle=0.3)
        L = e.keys(RET, idle=1.0)
        L = wait(e)
        row("control: SED has the second record open next to the first", in_sed(L) and "rr1" in "\n".join(L[:6]), "\n".join(l[:70] for l in L[:4]) + " | " + L[-1][:80])
        e.keys("BB", idle=0.5)
        e.keys(CTRL_S, idle=0.8)
        L = wait(e)
        row("saving the SECOND buffer does not end SED (the IDE does not come back), the first buffer's typing is still there",
            in_sed(L) and "BBrr1" in ID.rec_text(box, R2), L[-1][:80] + " | " + ID.rec_text(box, R2)[-100:])
        row("...and the first record on disk has no AA: it was not saved and not thrown away silently", "AA" not in ID.rec_text(box, Q), ID.rec_text(box, Q)[-100:])
        L = leave_sed(e)
        row("...leaving SED (and answering its question) returns to the IDE", in_ide(L), L[0][:60] + " | " + e.status())
        e.end()

        say("\n--- a record somebody else holds locked ---------------------------------------------------------------------------")
        p = subprocess.Popen([sys.executable, TOOL, box, "sess", os.path.join(box, "user_accounts"), "RUN bp %s" % hold],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace")
        time.sleep(4.0)
        try:
            e = IdeK(box, "IDE bp %s" % L1)
            before = ID.rec_text(box, L1)
            L = e.keys(CTRL_E, idle=1.0)
            L = wait(e, 3.0)
            say("      screen after Ctrl-E on a locked record: " + " | ".join(l.strip()[:60] for l in L if l.strip())[:300])
            row("SED opens a record someone else holds locked READ ONLY and says so on its screen (it is not edited and not refused)",
                in_sed(L) and "locked by another user" in "\n".join(L), "\n".join(l[:90] for l in L[:6]))
            e.keys("ZZ", idle=0.6)
            L = e.keys(CTRL_S, idle=1.0)
            L = wait(e)
            row("...typing and saving there changes nothing: SED stays up (the save returns to the IDE only when it saved) and the disk is as it was",
                in_sed(L) and ID.rec_text(box, L1) == before, L[-1][:80])
            L = leave_sed(e)
            row("...leaving returns to the IDE, the record is as it was on disk, and the status line says so",
                in_ide(L) and ID.rec_text(box, L1) == before and "is as it was" in e.status(), e.status())
            e.end()
        finally:
            p.kill()
            p.wait()
    finally:
        for nm in (fix, hold):
            for d in ("bp", "bp.out"):
                path = os.path.join(sysd, d, nm)
                if os.path.exists(path):
                    os.remove(path)

    say("")
    say("sandbox-ide-sed: %d passed, %d failed" % (passed, failed))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
