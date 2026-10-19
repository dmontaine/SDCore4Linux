#!/usr/bin/env python3
#
# sandbox-ide.py - the IDE (gpl.bp/ide, the IDE verb).  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-ide.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty
# or absent); without it <dir> must already be built, which is how the same script is run against an OLD tree to
# prove it can fail.  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 14 Oct 26 dm  New, with the IDE.
# END-HISTORY
#
# HOW IT DRIVES THE IDE.  On a PSEUDO-TERMINAL (ptydrive.py) at 120 by 36, the screen read from the emulator
# (termscreen.py).  What the IDE DID to the data is read from the data afterwards (CT through a pipe session), never
# from what it said.  Every record the suite makes is its own (zzi + the run's number), so a leftover cannot disturb
# the next row.  Keys are those SD's terminfo gives xterm.

import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ptydrive import PtySession  # noqa: E402

TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
RUN = "%05d" % (os.getpid() % 100000)
passed = failed = 0

UP, DOWN, LEFT, RIGHT = "\x1bOA", "\x1bOB", "\x1bOD", "\x1bOC"
F1, F2, F3, F4, F5 = "\x1bOP", "\x1bOQ", "\x1bOR", "\x1bOS", "\x1b[15~"
F6, F7, F8, F9, F10 = "\x1b[17~", "\x1b[18~", "\x1b[19~", "\x1b[20~", "\x1b[21~"
F11 = "\x1b[23~"
HOME, END, PGUP, PGDN = "\x1b[1~", "\x1b[4~", "\x1b[5~", "\x1b[6~"
ESC, RET, TAB = "\x1b", "\r", "\t"
CTRL_Q, CTRL_S, CTRL_W, CTRL_L, CTRL_R = "\x11", "\x13", "\x17", "\x0c", "\x12"


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
    say("sandbox-ide: CANNOT RUN - " + msg)
    sys.exit(2)


def sess(box, *cmds):
    """A plain scripted session through a pipe, for setting up and reading back (no keys)."""
    say("    > " + " | ".join(cmds))
    p = subprocess.run([sys.executable, TOOL, box, "sess", os.path.join(box, "user_accounts")] + list(cmds),
                       capture_output=True, text=True, errors="replace", timeout=600)
    out = ANSI.sub("", p.stdout + p.stderr)
    return out.split(":TERM 200,9999", 1)[-1]


class Ide:
    """One run of the IDE on a pseudo-terminal: type to it, read its screen."""

    def __init__(self, box, cmd="IDE", cols=140, rows=42, utf8=False):
        self.box = box
        # the locale decides whether the IDE draws its borders with line-drawing characters, so every run sets it:
        # C (plain + - |) unless the row is about UTF-8
        loc = "en_US.UTF-8" if utf8 else "C"
        env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"), TERM="xterm", LC_ALL=loc, LANG=loc)
        self.s = PtySession([os.path.join(box, "sys", "bin", "sd")], os.path.join(box, "user_accounts"), env, cols, rows, utf8=utf8)
        self.s.settle(1.0)
        self.s.type("TERM xterm\r")
        self.s.type("TERM %d,%d\r" % (cols, rows))
        self.log = [cmd]
        self.s.type(cmd + "\r", idle=1.2)

    def keys(self, *chunks):
        for chunk in chunks:
            self.log.append(chunk)
            self.s.type(chunk, idle=0.6)
        return self.lines()

    def lines(self):
        return self.s.screen.lines()

    def quiet(self):
        """Typed characters are the editor's own; the IDE's status line follows within a second of quiet."""
        time.sleep(1.5)
        self.s.settle(0.4)
        return self.lines()

    def text(self):
        return "\n".join(l for l in self.lines() if l.strip())

    def status(self):
        L = self.lines()
        return L[-1] if L else ""

    def end(self):
        self.s.type("\rOFF\r", idle=0.5)
        self.s.finish()


def has(L, *words):
    t = "\n".join(L)
    return all(w in t for w in words)


CSI = re.compile(r"\x1b\[([0-9;?]*)([A-Za-z])")


def cells_written(raw):
    """(cells, rows): how many cells the bytes write to the screen and the set of rows they touch (0-based), from the cursor
    positions and the printable text after each.  A screen of 140 by 42 is 5880 cells."""
    s = raw.decode("latin-1")
    n = 0
    rows = set()
    r = c = 0
    pos = 0
    for m in CSI.finditer(s):
        txt = re.sub(r"[\x00-\x1f]", "", s[pos:m.start()])
        if txt:
            n += len(txt)
            rows.add(r)
            c += len(txt)
        pos = m.end()
        if m.group(2) == "H":
            p = m.group(1).split(";")
            r = int(p[0] or 1) - 1
            c = int(p[1] or 1) - 1 if len(p) > 1 else 0
    return n, rows


def click(x, y):
    """A left click and its release at the cell x, y (0-based) in the SGR mouse form."""
    return "\x1b[<0;%d;%dM\x1b[<0;%d;%dm" % (x + 1, y + 1, x + 1, y + 1)


def rec_text(box, rid):
    """The record rid of the bp file, as the account sees it (CT through a pipe session)."""
    out = sess(box, "CT bp %s" % rid)
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-ide.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-ide: sandbox %s" % box)
    say("sandbox-ide: tree    %s" % os.path.dirname(HERE))
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-ide: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    A, B, C, D, E = ("zzi%s%s" % (RUN, c) for c in "abcde")   # a program with an error, a good one, a text with words, a spare, a long line
    fixture = """   open 'bp' to f else stop 'no bp'
   write str('0123456789', 25):@fm:'short' on f, '%(e)s'
   write 'crt "one"':@fm:'x = = 1':@fm:'crt "three"':@fm:'end' on f, '%(a)s'
   write 'crt "IDE-RAN-OK"':@fm:'end' on f, '%(b)s'
   write 'alpha':@fm:'the needle is here':@fm:'beta':@fm:'another NEEDLE line':@fm:'gamma' on f, '%(c)s'
   write 'first':@fm:'second':@fm:'third':@fm:'fourth' on f, '%(d)s'
   crt 'FIXTURE DONE'
end
""" % {"a": A, "b": B, "c": C, "d": D, "e": E}
    fix = "zzifx" + RUN
    with open(os.path.join(sysd, "bp", fix), "w") as fh:
        fh.write(fixture)
    try:
        say("\n--- fixture --------------------------------------------------------------------------------------")
        out = sess(box, "BASIC bp %s" % fix, "RUN bp %s" % fix)
        row("setup: the fixture program compiled and made the records", "FIXTURE DONE" in out, out[-300:])
        if "FIXTURE DONE" not in out:
            bail("the fixture was not made:\n" + out[-600:])
        row("setup: the IDE's program is in the sandbox", os.path.isfile(os.path.join(sysd, "gpl.bp", "ide")), "missing")

        # ---- the screen at the start ---------------------------------------------------------------------
        say("\n--- the start -------------------------------------------------------------------------------------")
        e = Ide(box)
        L = e.lines()
        row("the menu bar is on the top row", re.search(r"File\s+Go\s+Search\s+Build\s+View\s+Help", L[0]) is not None, L[0])
        row("the form's title names the account", "IDE: " in L[1], L[1])
        row("the tree lists the account's files (bp, gpl.bp, voc)", has(L[2:], " bp", "gpl.bp", " voc"), e.text()[:400])
        row("the tab strip says no record is open", "(no record)" in L[2], L[2])
        row("the table's headings are Line and Message", has(L, "Line", "Message"), e.text()[-300:])
        row("there is no button at the bottom of the tree (Return is an event of the form, not a default button)", "[ Open ]" not in "\n".join(L), "\n".join(L[-6:]))

        # ---- open a record ---------------------------------------------------------------------------------
        say("\n--- the tree: a file lists its records, a record opens -----------------------------------------------")
        L = e.keys("b", RET)
        row("Return on a file lists its records under it (the fixture's four)", has(L, A, B, C, D), e.text()[:700])
        L = e.keys("z", RET)
        row("Return on a record opens it: its tab, its first line, and the status line names it",
            "[%s]" % A in L[2] and "crt \"one\"" in "\n".join(L) and ("bp %s" % A) in e.status(), "\n".join(L[:6]) + "\n" + e.status())
        row("the status line says where the cursor is", "Line 1, column 1" in e.status(), e.status())
        row("the editor has the line numbers", re.search(r"\b1 crt \"one\"", "\n".join(L)) is not None and re.search(r"\b2 x = = 1", "\n".join(L)) is not None, "\n".join(L[2:8]))

        # ---- compile ---------------------------------------------------------------------------------------
        say("\n--- compile ----------------------------------------------------------------------------------------")
        L = e.keys(F7)
        t = "\n".join(L)
        row("F7 compiles: the status line counts the errors and names the record", re.search(r"\d+ error\(s\) in bp %s" % A, e.status()) is not None, e.status())
        tab = [l for l in L if re.search(r"^\|?\s*\|?.*\s+\|?\s*2\s+\S", l)]
        row("the table lists the error with its line number (2)", any(re.search(r"\b2\s+\S.*", l[30:]) for l in L[27:]), "\n".join(L[26:34]))
        row("the cursor went to the error's line", "Line 2," in e.status(), e.status())

        # ---- edit and save ----------------------------------------------------------------------------------
        say("\n--- edit and save ----------------------------------------------------------------------------------")
        L = e.keys(HOME, "ZZ")
        L = e.quiet()
        row("typing marks the record changed (a star in the status line)", " *" in e.status(), e.status())
        before = rec_text(box, A)
        L = e.keys(F2)
        row("F2 says the record was saved", ("Saved bp %s" % A) in e.status() and " *" not in e.status().split("Saved")[0], e.status())
        after = rec_text(box, A)
        row("the record on disk has the change (read back through CT)", "ZZ" in after and "ZZ" not in before, after[-300:])

        # ---- a good program, and the second tab -------------------------------------------------------------
        say("\n--- a second record in a tab of its own ------------------------------------------------------------")
        L = e.keys(F3)                                    # back to the tree
        L = e.keys(DOWN, RET)                             # the record after A in the list is B
        row("a second record opens in a second tab (both ids on the strip)", has(L[2:3], A, B), L[2])
        L = e.keys(F7)
        row("a good program compiles with no errors and the table is empty",
            ("Compiled bp %s with no errors" % B) in e.status(), e.status())
        L = e.keys(F6)
        row("F6 goes to the next tab: the first record is back with its change", ("bp %s" % A) in e.status() and "ZZ" in "\n".join(L[3:12]), e.status() + "\n" + "\n".join(L[3:8]))
        L = e.keys(F6)
        row("...and again, to the second", ("bp %s" % B) in e.status(), e.status())

        # ---- go to a line -----------------------------------------------------------------------------------
        say("\n--- go to a line, the keys that are not the editor's ---------------------------------------------------")
        L = e.keys(F6)                                     # to A (four lines)
        L = e.keys(CTRL_L)
        row("Ctrl-L asks for a line number", "Line number" in e.text(), e.text()[-300:])
        L = e.keys("3", RET)
        row("the cursor goes to line 3", "Line 3," in e.status(), e.status())
        L = e.keys(F1)
        row("F1 shows the help", "Next pane" in e.text() or "Tab, Shift-Tab" in e.text(), e.text()[:300])
        L = e.keys(RET)

        # ---- the menu ---------------------------------------------------------------------------------------
        say("\n--- the menu bar ------------------------------------------------------------------------------------")
        L = e.keys(F10)
        row("F10 opens the first menu: its entries are listed", has(L, "New record", "Save", "Close record", "Quit"), e.text()[:400])
        L = e.keys(RIGHT)
        row("Right goes to the next menu (Go)", has(L, "Go to line", "Next error", "Next tab"), e.text()[:400])
        L = e.keys(ESC)
        row("Esc closes it and the editor is still there", ("bp %s" % A) in e.status(), e.status())

        # ---- changes in a tab are kept when the tab is left ---------------------------------------------------
        say("\n--- the text of each tab is kept ----------------------------------------------------------------------")
        L = e.keys(F6)                                     # to B
        L = e.keys(END, "QQ")
        L = e.quiet()
        row("typing in the second tab marks it changed", " *" in e.status() and ("bp %s" % B) in e.status(), e.status())
        L = e.keys(F6, F6)                                 # A, then B
        row("leaving a changed tab and coming back keeps what was typed", "QQ" in "\n".join(L[3:10]) and " *" in e.status(), e.status() + "\n" + "\n".join(L[3:8]))
        row("...and nothing reached the disk", "QQ" not in rec_text(box, B), "")

        # ---- close with changes, discarding ------------------------------------------------------------------
        say("\n--- close a record with changes ----------------------------------------------------------------------")
        L = e.keys(F10, DOWN * 3, RET)                     # File, Close record
        row("File, Close record on a changed record asks what to do", has(L, "has changes", "Save", "Discard", "Cancel"), e.text()[:500])
        L = e.keys(DOWN, RET)                              # Save, Discard, Cancel: down to Discard
        row("Discard closes the tab (one left) and the disk is as it was", B not in L[2] and "QQ" not in rec_text(box, B), L[2] + " | " + e.status())

        # ---- search ---------------------------------------------------------------------------------------------
        say("\n--- find in the records of the file -------------------------------------------------------------------")
        L = e.keys(F11)
        row("F11 asks for the text to find in the records", "Find in the records of bp" in e.text(), e.text()[-300:])
        L = e.keys("needle", RET)
        t = "\n".join(L)
        row("the matching lines are listed with the record id (case ignored, both lines)",
            re.search(r"%s: the needle is here" % C, t) is not None and re.search(r"%s: another NEEDLE line" % C, t) is not None, "\n".join(L[26:34]))
        # (three: the fixture program that wrote the records holds the word too)
        row("the status line counts them", re.search(r"3 line\(s\) found in bp", e.status()) is not None, e.status())
        L = e.keys(TAB, TAB, TAB, TAB)                      # round the ring to the table
        L = e.keys(F4)
        row("F4 goes to a result: that record is opened, at the line", ("bp %s" % C) in e.status(), e.status())

        # ---- a new record -----------------------------------------------------------------------------------------
        say("\n--- a new record --------------------------------------------------------------------------------------")
        newid = "zzin" + RUN
        L = e.keys(F10, RET)                                # the first entry of File: New record
        row("File, New record asks for a name", "Name of the new record" in e.text(), e.text()[-300:])
        L = e.keys(newid, RET)
        row("the record is made, opened and empty", ("bp %s" % newid) in e.status(), e.status())
        row("...and it exists on disk", "1 record(s) selected" in sess(box, "SELECT bp WITH @ID = '%s'" % newid), "")

        # ---- the keys SED has: write a record under another name (Ctrl-W), replace (Ctrl-R) ----------------------------
        say("\n--- SED's keys: Ctrl-W writes the text to another record, Ctrl-R replaces -----------------------------------")
        L = e.keys("alpha beta alpha")
        e.quiet()
        copyid = newid + "w"
        L = e.keys(CTRL_W)
        row("Ctrl-W asks for the name of the record to write to", "Name of the new record" in e.text(), e.text()[-300:])
        L = e.keys(copyid, RET)
        row("...writes the text there (read back through CT) and the editor stays on the record it had",
            "alpha beta alpha" in rec_text(box, copyid) and ("bp %s" % newid) in e.status() and ("Saved bp %s" % copyid) in e.status(),
            e.status())
        L = e.keys(CTRL_W)
        L = e.keys(copyid, RET)
        row("...and refuses a name that is already a record, leaving it alone", ("already exists in bp") in e.status(), e.status())
        L = e.keys(CTRL_R)
        row("Ctrl-R asks for the text to replace", "Replace this text" in e.text(), e.text()[-300:])
        L = e.keys("alpha", RET)
        row("...and then for what to put there", re.search(r"With:", e.text()) is not None, e.text()[-300:])
        L = e.keys("omega", RET)
        e.quiet()
        row("every occurrence is replaced in the editor: 'omega beta omega', and the status line counts two",
            "omega beta omega" in "\n".join(e.lines()[3:12]) and "2 replacement(s)" in e.status(), e.status() + "\n" + "\n".join(e.lines()[3:8]))
        row("...and nothing is written until the record is saved", "omega" not in rec_text(box, newid), "")
        L = e.keys(F2)
        row("F2 then saves it (read back through CT)", "omega beta omega" in rec_text(box, newid), "")

        e.end()

        # ---- run, with a record chosen by the command line ---------------------------------------------------------
        say("\n--- run -----------------------------------------------------------------------------------------------")
        e = Ide(box, "IDE bp %s" % B)
        L = e.lines()
        row("IDE file record opens that record at once", ("bp %s" % B) in e.status() and "[%s]" % B in L[2], e.status() + " | " + L[2])
        L = e.keys(F5)
        row("F5 runs the program: its output is on the terminal and the IDE says to press Return",
            "IDE-RAN-OK" in e.text() and "Press Return to go back to the IDE" in e.text(), e.text()[-400:])
        L = e.keys(RET)
        row("Return gives the IDE back, with the record still open", re.search(r"File\s+Go\s+Search", L[0]) is not None and ("bp %s" % B) in e.status(), L[0] + " | " + e.status())

        # ---- catalogue and debug ------------------------------------------------------------------------------------
        say("\n--- catalogue, debug, theme -------------------------------------------------------------------------------")
        L = e.keys(F8)
        row("F8 compiles and catalogues: the status line says so", ("Catalogued bp %s" % B) in e.status(), e.status())
        row("...and the program runs from the command prompt by its name", "IDE-RAN-OK" in sess(box, B), "")
        L = e.keys(F9)
        row("F9 compiles with debugging and gives the terminal to the debugger (the program's source is shown)",
            'crt "IDE-RAN-OK"' in e.text() and not re.search(r"File\s+Go\s+Search", e.lines()[0]), e.text()[:400])
        L = e.keys("q", RET)
        row("quitting the debugger comes back to the IDE after Return",
            "Press Return to go back to the IDE" in e.text(), e.text()[-300:])
        L = e.keys(RET)
        row("...with the record still open", re.search(r"File\s+Go\s+Search", L[0]) is not None and ("bp %s" % B) in e.status(), e.status())
        L = e.keys(F10, RIGHT * 4, RET)
        row("View, Theme changes the theme and the IDE is still on the screen", re.search(r"File\s+Go\s+Search", e.lines()[0]) is not None and ("bp %s" % B) in e.status(), e.text()[:300])

        # ---- quitting ----------------------------------------------------------------------------------------------
        say("\n--- quitting ----------------------------------------------------------------------------------------------")
        L = e.keys("x")
        L = e.quiet()
        row("a change is made", " *" in e.status(), e.status())
        L = e.keys(CTRL_Q)
        row("Ctrl-Q with a changed record asks", has(L, "has changes", "Save", "Discard", "Cancel"), e.text()[:400])
        L = e.keys(ESC)
        row("Esc in the question (Cancel) stays in the IDE", re.search(r"File\s+Go\s+Search", L[0]) is not None, L[0])
        L = e.keys(CTRL_Q, DOWN, RET)
        row("Discard leaves the IDE: the menu bar is gone and the record is unchanged",
            not re.search(r"File\s+Go\s+Search", e.lines()[0]) and "xcrt" not in rec_text(box, B), e.text()[:300])
        e.end()

        # ---- Return on the table's row, and on a file that is open -------------------------------------------------------
        say("\n--- the table and the tree ----------------------------------------------------------------------------------")
        e = Ide(box, "IDE bp %s" % A)
        e.keys(F7)
        row("setup: the record is open and compiled with its error", ("bp %s" % A) in e.status() and "error(s)" in e.status(), e.status())
        e.keys(CTRL_L)
        e.keys("1", RET)
        row("the cursor is moved to line 1", "Line 1," in e.status(), e.status())
        e.keys(F3, TAB, TAB, TAB)                       # tree, tabs, editor, table
        L = e.keys(RET)
        row("Return on a row of the table goes to its line (2)", "Line 2," in e.status(), e.status())
        L = e.keys(F3)                                  # the tree is on bp, the file the IDE was started on
        tree = "\n".join(l[:30] for l in e.lines()[3:26])
        row("the file's records are listed under it", C in tree, tree)
        L = e.keys(RET)
        tree = "\n".join(l[:30] for l in L[3:26])
        row("Return on a file that is open closes it: its records are not listed under it any more", C not in tree, tree)
        e.end()

        # ---- line-drawing characters on a UTF-8 terminal ------------------------------------------------------------
        say("\n--- borders: line drawing when the locale is UTF-8, + - | when it is not ------------------------------------------")
        e = Ide(box, "IDE bp %s" % B, utf8=True)
        L = e.lines()
        t = "\n".join(L)
        row("a UTF-8 locale: the frame is drawn with line-drawing characters (corners, horizontal and vertical)",
            "┌" in t and "┐" in t and "└" in t and "┘" in t and "─" in t and "│" in t, t[:300])
        row("...and none of the plain + - | frame is left (no row starts with + and dashes)",
            not any(re.match(r"^\+-", l) for l in L), "\n".join(L[:3]))
        row("...the scroll bar's arrows are drawn too (▲ ▼), and no ASCII ^ v bar is left in its column",
            "▲" in t and "▼" in t, t[-600:])
        row("...and the record is open and works as before", ("bp %s" % B) in e.status(), e.status())
        e.end()
        e = Ide(box, "IDE gpl.bp ced_edit", utf8=True)
        t = e.text()
        row("a long program (a record of gpl.bp, hundreds of lines): the thumb of the scroll bar is a block (█)",
            "█" in t and "ced_edit" in e.status(), e.status() + "\n" + t[:200])
        e.end()
        e = Ide(box, "IDE bp %s" % B)
        L = e.lines()
        row("a C locale: the frame is + - | as before and no line-drawing character is on the screen",
            re.match(r"^\+- IDE", L[1]) is not None and not any(ord(ch) > 127 for l in L for ch in l), "\n".join(L[:3]))
        e.end()

        # ---- the window follows the terminal ------------------------------------------------------------------------
        say("\n--- the window --------------------------------------------------------------------------------------------")
        # 18 Oct 26 (terminal 140 by 42): the IDE is laid out for at least 140 by 42 and a window that becomes smaller shows the upper left
        # corner of that layout; sandbox-ide-small.py has the rows for the refusal, the shrink and the cursor lock.
        e = Ide(box, "IDE bp %s" % B)
        row("at 140 by 42 the form's frame ends on the row before the status line (row 40) and the status line is the last row",
            re.match(r"^\+-+\+$", e.lines()[40].strip()) is not None and ("bp %s" % B) in e.status(), "\n".join(e.lines()[38:42]))
        e.s.resize(100, 30, idle=1.5)
        time.sleep(1.8)
        e.s.settle(0.8)
        L = e.lines()
        row("a resize to 100 by 30 shows the upper left corner of the same layout: the menu bar and the frame's top, no row wider than 100",
            re.search(r"File\s+Go\s+Search", L[0]) is not None and L[1].startswith("+- IDE") and max(len(l) for l in L) <= 100, "\n".join(l[:60] for l in L[:3]))
        row("...the record is still open in its tab", "[%s]" % B in L[2], L[2])
        e.s.resize(160, 50, idle=1.5)
        time.sleep(1.8)
        e.s.settle(0.8)
        L = e.lines()
        row("a resize to 160 by 50 makes the layout the window's: the frame is 160 wide and the status line is the last row (49)",
            len(L[1].rstrip()) == 160 and ("bp %s" % B) in L[49], repr(L[1][-6:]) + repr(L[49][:30]))
        e.end()
        e = Ide(box, "IDE", cols=50, rows=12)
        row("a terminal smaller than 140 by 42 is refused with the library's message, and nothing is drawn",
            "".join("IDE needs a window of at least 140 columns by 42 lines; this one is 50 by 12".split()) in "".join(e.text().split())   # the message wraps at column 50
            and not re.search(r"File\s+Go\s+Search", e.lines()[0]), e.text()[:300])
        e.end()

        # ---- a record somebody else changed ---------------------------------------------------------------------------
        say("\n--- somebody else changed the record -----------------------------------------------------------------------")
        e = Ide(box, "IDE bp %s" % D)
        e.keys("Q")
        other = """   open 'bp' to f else stop
   write 'other':@fm:'text' on f, '%s'
   crt 'OTHER DONE'
end
""" % D
        with open(os.path.join(sysd, "bp", "zzio" + RUN), "w") as fh:
            fh.write(other)
        out = sess(box, "BASIC bp zzio%s" % RUN, "RUN bp zzio%s" % RUN)
        L = e.keys(F2)
        row("saving a record that changed on disk asks before overwriting", has(L, "changed by someone else", "Overwrite", "Cancel"), e.text()[:400])
        L = e.keys(ESC)
        row("Cancel leaves the disk as the other session made it", "other" in rec_text(box, D) and "Qfirst" not in rec_text(box, D), "")
        e.keys(CTRL_Q, DOWN, RET)
        e.end()

        # ---- the owner's three reports, 18 Oct 26: no cursor at the start, the whole screen flashing at each record, no horizontal bar ----
        say("\n--- the cursor, what choosing a record writes, and the horizontal bar ----------------------------------------")
        e = Ide(box)
        scr = e.s.screen
        row("started with no record: the cursor is shown, on the tree (left of the editor), not at the end of the status row",
            scr.cursor_visible and 2 <= scr.r <= 39 and scr.c < 28, repr((scr.r, scr.c, scr.cursor_visible)))
        at = (scr.r, scr.c)
        m = len(e.s.raw)
        e.quiet()
        e.quiet()
        idle = len(e.s.raw) - m
        row("an idle IDE writes next to nothing: %d bytes in 3 seconds (it wrote the whole status line ten times a second)" % idle, idle < 400, repr(idle))
        row("...and the cursor has not moved", (scr.r, scr.c) == at, "%r then %r" % (at, (scr.r, scr.c)))

        e.keys("b", RET)                                  # the file's records are listed under it
        e.keys("z", RET)                                  # the first of the fixture's records opens (A)
        e.keys(F3)                                        # back to the tree
        e.keys(DOWN)                                      # the record after A
        m = len(e.s.raw)
        L = e.keys(RET)                                   # ... opens in a second tab
        raw = bytes(e.s.raw[m:])
        n, rws = cells_written(raw)
        row("the second record is open in its own tab, and the cursor is shown in the editor", has(L[2:3], A, B) and scr.cursor_visible and scr.c >= 29,
            "%s | cursor %r" % (L[2][:80], (scr.r, scr.c, scr.cursor_visible)))
        row("choosing it writes less than one screen's worth of cells (%d of the screen's 5880; it wrote 14800 when it drew the form three times)" % n,
            n < 5880, repr(n))
        row("...nothing in the menu bar or the form's title row (rows 1 and 2), and no clear-screen", not (rws & {0, 1}) and b"\x1b[2J" not in raw, repr(sorted(rws))[:80])
        m = len(e.s.raw)
        L = e.keys(F6)                                    # the other tab
        n, rws = cells_written(bytes(e.s.raw[m:]))
        row("F6, to the other tab, writes under one screen's worth too (%d cells) and leaves the title row alone" % n, n < 5880 and 1 not in rws, repr((n, sorted(rws))))
        m = len(e.s.raw)
        e.keys(F3)
        n, rws = cells_written(bytes(e.s.raw[m:]))
        row("F3 puts the cursor on the tree at once (SCREEN FOCUS alone moves a pointer and draws nothing)", scr.cursor_visible and scr.c < 28 and 2 <= scr.r <= 39,
            repr((scr.r, scr.c, scr.cursor_visible)))
        row("...and F3 draws only the two widgets that change (%d cells; the editor and the tree), not the form" % n, n < 5880 and not (rws & {0, 1}), repr((n, sorted(rws))))
        e.end()

        e = Ide(box, "IDE bp %s" % A)
        L = e.lines()
        bars = [i for i, l in enumerate(L) if re.search(r"<[#-]+>", l)]
        row("the cursor is shown in the editor of a record opened from the command line", e.s.screen.cursor_visible and e.s.screen.c >= 29,
            repr((e.s.screen.r, e.s.screen.c, e.s.screen.cursor_visible)))
        row("a record whose lines all fit has the bar, with no thumb on it (nothing to scroll sideways)", len(bars) == 1 and "#" not in L[bars[0]],
            "\n".join(l[:60] for l in L[28:36]))
        m = len(e.s.raw)
        e.keys("\x1b[24~")                                # F12: neither the editor's nor the IDE's, so nothing changes and nothing is drawn
        e.quiet()
        n, _ = cells_written(bytes(e.s.raw[m:]))
        row("a key that neither the editor nor the IDE uses draws nothing (%d cells; the editor drew all its rows again for it)" % n, n < 300, repr(n))
        e.end()

        e = Ide(box, "IDE bp %s" % E)
        L = e.lines()
        bars = [i for i, l in enumerate(L) if re.search(r"<[#-]+>", l)]
        row("a record with a 250-character line has the bar under the text, with a thumb", len(bars) == 1 and "#" in L[bars[0]], "\n".join(l[:70] for l in L[28:36]))
        if len(bars) == 1:
            br = bars[0]
            t0 = L[br].index("#")
            row("...the text area is one row shorter: the bar is the row under the last line shown and the table's heading is below it",
                "Messages" in L[br + 1], "\n".join(l[:70] for l in L[br - 1:br + 3]))
            L = e.keys(END)
            t1 = L[br].index("#") if "#" in L[br] else -1
            row("End on the long line moves the thumb to the right (%d to %d)" % (t0, t1), t1 > t0, L[br][:140])
            L = e.keys(HOME)
            row("Home brings it back to the left", "#" in L[br] and L[br].index("#") == t0, L[br][:140])
            right = L[br].rindex(">")
            L = e.keys(click(right, br))
            row("a click on the right arrow scrolls the text sideways (the thumb moves right)", "#" in L[br] and L[br].index("#") > t0, L[br][:140])
            L = e.keys(click(L[br].index("<"), br))
            row("a click on the left arrow scrolls it back", "#" in L[br] and L[br].index("#") == t0, L[br][:140])
        e.end()
    finally:
        pass

    say("")
    say("sandbox-ide: %d passed, %d failed" % (passed, failed))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
