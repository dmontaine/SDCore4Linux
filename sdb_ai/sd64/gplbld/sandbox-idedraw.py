#!/usr/bin/env python3
#
# sandbox-idedraw.py - what the IDE draws and where it shows the focus: a click on the menu bar, how little a choice writes to the terminal,
#                      the pane named on the status line, and the highlighted cursor cell.  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-idedraw.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or absent); without it
# <dir> must already be built, which is how the same script is run against an OLD tree to prove it can fail.  Exit 0 every row passed,
# 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 19 Oct 26 dm  New, for the owner's four reports of 19 Oct 26 on the IDE (the sitting after the 140x42 merge):
#               (1) "the whole screen flashing in the ide still happens every time a new record or file is chosen" - the screen library
#                   wrote every widget again, the tree three times: $sl_put now leaves out text the terminal already shows (SL.S.DIFF);
#               (2) "the menu is unavailable on a mouse click until after esc has been pressed" - the bar is not a widget, and a click on it
#                   was dropped: SCREEN MENUBAR ... CLICK, and the form's f{'bgclick'};
#               (3) "if you are not using a mouse and press tab, there is no visible indication of which box is active" - the status line
#                   names the pane (messages 11237-11240);
#               (4) "when you select a record to edit, the cursor does not appear in the edit box" - the editor highlights the character at
#                   its cursor while it has the focus (the memo's softcur), whatever the terminal does with its own cursor.
# END-HISTORY
#
# THE INSTRUMENT.  The IDE is driven on a pseudo-terminal at 140 by 42 (sandbox-ide.py's Ide class, which this imports), the screen read from
# the emulator.  "Writes" are the CELLS of text the IDE sent to the terminal for one action, counted from the bytes themselves (a cursor
# position, then the printable text after it), never from what the IDE said.  The numbers under "red" are what the tree before this change
# wrote for the same actions, measured 19 Oct 26 with the same harness: a file chosen 3078 cells, a record chosen 6635 (a screen is 5880),
# F3 4326, DOWN in the tree 1026, a second record 5616, F6 3564.

import importlib.util
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
_spec = importlib.util.spec_from_file_location("sandbox_ide", os.path.join(HERE, "sandbox-ide.py"))
sb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sb)

TOOL = os.path.join(HERE, "sandbox-fromtree.py")
RUN = "%05d" % (os.getpid() % 100000)
passed = failed = 0
CSI = re.compile(r"\x1b\[([0-9;?]*)([A-Za-z])")


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
    say("sandbox-idedraw: CANNOT RUN - " + msg)
    sys.exit(2)


def written(raw):
    """[(row, column, cells)] - every run of text the bytes write, with the place of its first cell (0-based)."""
    s = raw.decode("latin-1")
    out = []
    r = c = 0
    pos = 0
    for m in CSI.finditer(s):
        txt = re.sub(r"[\x00-\x1f]", "", s[pos:m.start()])
        if txt:
            out.append((r, c, len(txt)))
            c += len(txt)
        pos = m.end()
        if m.group(2) == "H":
            p = m.group(1).split(";")
            r = int(p[0] or 1) - 1
            c = int(p[1] or 1) - 1 if len(p) > 1 else 0
    txt = re.sub(r"[\x00-\x1f]", "", s[pos:])
    if txt:
        out.append((r, c, len(txt)))
    return out


def cells(runs):
    return sum(n for _r, _c, n in runs)


def tree_cells(runs):
    """Cells written in the tree's columns (the tree is the left 28), below the menu bar and the title, above the status line."""
    return sum(n for r, c, n in runs if c < 28 and 2 <= r <= 39)


def tree_rows(runs):
    return len(set(r for r, c, n in runs if c < 28 and 2 <= r <= 39))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-idedraw.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-idedraw: sandbox %s" % box)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-idedraw: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    A, B, C = ("zzd%s%s" % (RUN, c) for c in "abc")
    fix = "zzdfx" + RUN
    fixture = """   open 'bp' to f else stop 'no bp'
   write 'crt "one"':@fm:'x = = 1':@fm:'crt "three"':@fm:'end' on f, '%(a)s'
   write 'crt "IDE-RAN-OK"':@fm:'end' on f, '%(b)s'
   write 'alpha':@fm:'the needle is here':@fm:'beta':@fm:'gamma' on f, '%(c)s'
   crt 'FIXTURE DONE'
end
""" % {"a": A, "b": B, "c": C}
    with open(os.path.join(sysd, "bp", fix), "w") as fh:
        fh.write(fixture)
    try:
        say("\n--- fixture ----------------------------------------------------------------------------------------")
        out = sb.sess(box, "BASIC bp %s" % fix, "RUN bp %s" % fix)
        row("setup: the fixture program compiled and made the records", "FIXTURE DONE" in out, out[-300:])
        if "FIXTURE DONE" not in out:
            bail("the fixture was not made:\n" + out[-600:])

        # ---- (2) a click on the menu bar --------------------------------------------------------------------------------
        say("\n--- (2) a click on the menu bar --------------------------------------------------------------------------")
        # Each title is its label with a blank on each side, from column 0 (File 0-5, Go 6-9, Search 10-17).  Before this change a click on the
        # bar came to the IDE as a key it had no use for, and the menu opened only for F10 or Esc.
        e = sb.Ide(box, "IDE bp %s" % A)
        L = e.keys(sb.click(2, 0))
        row("a click on File opens the File menu (New record, Close record, Quit)", sb.has(L, "New record", "Close record", "Quit"), e.text()[:300])
        row("...and not the Go menu", "Go to line" not in "\n".join(L), e.text()[:300])
        L = e.keys(sb.ESC)
        row("Esc closes it", "New record" not in "\n".join(L), e.text()[:300])
        L = e.keys(sb.click(7, 0))
        row("a click on Go opens the Go menu (Go to line, Next error, Next tab) - the menu under the click, not the first",
            sb.has(L, "Go to line", "Next error", "Next tab"), e.text()[:300])
        row("...and not the File menu", "Close record" not in "\n".join(L), e.text()[:300])
        L = e.keys(sb.ESC)
        L = e.keys(sb.click(120, 0))
        row("a click on the bar to the right of the titles opens nothing", not sb.has(L, "New record") and not sb.has(L, "Go to line"), e.text()[:300])
        L = e.keys(sb.click(40, 20))                      # in the editor: the click goes to the editor as before
        L = e.keys(sb.click(2, 0))
        row("a click on File after a click in the editor opens the File menu", sb.has(L, "New record", "Close record"), e.text()[:300])
        L = e.keys(sb.ESC)
        L = e.keys(sb.F10)
        row("F10 after those clicks opens the first menu, not the one last clicked", sb.has(L, "New record", "Close record") and "Go to line" not in "\n".join(L), e.text()[:300])
        L = e.keys(sb.ESC)
        row("the editor is still there after the menus", ("bp %s" % A) in e.status(), e.status())
        L = e.keys(sb.click(2, 0), sb.DOWN, sb.RET)       # File, down to Save, Return: a record with no change is saved as it is
        row("a menu opened by a click is used with the keys as any other (Down, Return chose Save; the menu is gone)", "New record" not in "\n".join(L), e.text()[:300])
        e.end()

        # ---- (1) what choosing writes ---------------------------------------------------------------------------------------
        say("\n--- (1) what a choice writes to the terminal ---------------------------------------------------------------")
        e = sb.Ide(box)
        scr = e.s.screen
        m = len(e.s.raw)
        L = e.keys("b", sb.RET)                           # a FILE chosen: its records are listed under it
        runs = written(bytes(e.s.raw[m:]))
        row("choosing a file writes %d cells (red 3078): the tree rows that changed, under 1500" % cells(runs), cells(runs) < 1500, repr(cells(runs)))
        right = sum(n for r, c, n in runs if c >= 28 and 2 <= r <= 39)
        row("...and none of the editor, the tab strip or the messages (%d cells there)" % right, right < 20, repr(right))
        m = len(e.s.raw)
        L = e.keys("z", sb.RET)                           # the first of the fixture's records (the first name starting with z)
        runs = written(bytes(e.s.raw[m:]))
        row("choosing a record writes %d cells (red 6635, a screen is 5880): under 2000" % cells(runs), cells(runs) < 2000, repr(cells(runs)))
        row("...the tree gets %d cells in %d rows (the highlight moves: red 3 times the whole tree)" % (tree_cells(runs), tree_rows(runs)),
            tree_cells(runs) < 200 and tree_rows(runs) <= 4, repr((tree_cells(runs), tree_rows(runs))))
        row("the record is open and its text shows", sb.has(L[2:8], "crt", "one"), "\n".join(l[:70] for l in L[2:8]))
        m = len(e.s.raw)
        L = e.keys(sb.F3)
        runs = written(bytes(e.s.raw[m:]))
        # (the tree's row, the editor's row that held the highlighted cursor, and the status line, whose first word is the pane: about 275)
        row("F3, the focus back to the tree, writes %d cells (red 4326): under 400" % cells(runs), cells(runs) < 400, repr(cells(runs)))
        m = len(e.s.raw)
        L = e.keys(sb.DOWN)
        runs = written(bytes(e.s.raw[m:]))
        row("Down in the tree writes %d cells in %d rows (red 1026 in 38): under 200 in at most 3" % (cells(runs), len(set(r for r, c, n in runs))),
            cells(runs) < 200 and len(set(r for r, c, n in runs)) <= 3, repr((cells(runs), sorted(set(r for r, c, n in runs)))))
        m = len(e.s.raw)
        L = e.keys(sb.RET)                                # the next record in a tab of its own
        runs = written(bytes(e.s.raw[m:]))
        row("a second record writes %d cells (red 5616): under 2000" % cells(runs), cells(runs) < 2000, repr(cells(runs)))
        m = len(e.s.raw)
        L = e.keys(sb.F6)
        runs = written(bytes(e.s.raw[m:]))
        row("F6, to the other tab, writes %d cells (red 3564): under 2000, none in the tree (%d)" % (cells(runs), tree_cells(runs)),
            cells(runs) < 2000 and tree_cells(runs) < 60, repr((cells(runs), tree_cells(runs))))
        m = len(e.s.raw)
        e.quiet()
        row("an idle IDE writes next to nothing (%d bytes in 2 seconds)" % (len(e.s.raw) - m), len(e.s.raw) - m < 400, repr(len(e.s.raw) - m))
        e.end()

        # ---- (3) the pane that has the focus is named -------------------------------------------------------------------------
        say("\n--- (3) Tab, and the pane named on the status line -----------------------------------------------------------")
        e = sb.Ide(box)
        st = e.status()
        row("the status line names the pane that has the focus at the start: [Files]", st.startswith("[Files]"), st)
        seen = []
        for _ in range(4):
            e.keys(sb.TAB)
            e.quiet()
            seen.append(e.status().split("]")[0] + "]")
        row("Tab goes round four panes and the status line names each: %s" % seen,
            sorted(set(seen)) == sorted(["[Files]", "[Tabs]", "[Editor]", "[Messages]"]), repr(seen))
        e.end()
        e = sb.Ide(box, "IDE bp %s" % A)
        row("a record opened from the command line starts in the editor: the status line says [Editor] and the record", e.status().startswith("[Editor]") and A in e.status(), e.status())
        e.keys(sb.F3)
        e.quiet()
        row("F3 moves the focus to the tree and the line says [Files]", e.status().startswith("[Files]") and A in e.status(), e.status())
        e.end()

        # ---- (4) the cursor in the editor ------------------------------------------------------------------------------------
        say("\n--- (4) the cursor shows in the editor, whatever the terminal does with its own ---------------------------------")
        e = sb.Ide(box, "IDE bp %s" % C)
        scr = e.s.screen

        def cursor_cell():
            return scr.style(scr.r, scr.c)

        r0, c0 = scr.r, scr.c
        here = cursor_cell()
        beside = scr.style(scr.r, scr.c + 1)
        row("the editor has the focus: the character at the cursor is in a style of its own (%r), the next one is not (%r)" % (here, beside),
            here != beside and here[1] is not None, repr((here, beside, (scr.r, scr.c))))
        L = e.keys(sb.RIGHT)
        row("Right moves it: the highlight is on the new place and the old place is plain again",
            scr.c == c0 + 1 and cursor_cell() == here and scr.style(r0, c0) == beside, repr((scr.r, scr.c, cursor_cell(), scr.style(r0, c0))))
        L = e.keys(sb.DOWN)
        row("Down moves it a row", scr.r == r0 + 1 and cursor_cell() == here, repr((scr.r, scr.c, cursor_cell())))
        L = e.keys("Z")
        row("a typed character is drawn and the highlight is on the place after it", "Z" in L[scr.r] and cursor_cell() == here, L[scr.r][:60])
        L = e.keys(sb.F3)
        e.quiet()
        nh = sum(1 for cc in range(28, 138) for rr in range(3, 30) if scr.style(rr, cc) == here)        # (row 2 is the tab strip, which has its own look)
        row("with the focus on the tree the editor has no highlighted cursor (%d cells in the style)" % nh, nh == 0, repr(nh))
        L = e.keys(sb.TAB)
        e.quiet()
        L = e.keys(sb.TAB)
        e.quiet()
        row("Tab back to the editor: it is highlighted again, with the hardware cursor there too and shown",
            cursor_cell() == here and scr.cursor_visible, repr((scr.r, scr.c, cursor_cell(), scr.cursor_visible)))
        e.end()

        e = sb.Ide(box, "IDE bp %s" % A)
        L = e.keys(sb.F3)                                 # a keyboard-only user chooses another record in the tree
        L = e.keys(sb.DOWN)
        L = e.keys(sb.RET)
        scr = e.s.screen
        row("choosing a record by the keyboard puts the cursor in the editor, highlighted, and the hardware cursor there and shown",
            scr.c >= 29 and scr.cursor_visible and scr.style(scr.r, scr.c)[1] is not None and scr.style(scr.r, scr.c) != scr.style(scr.r, scr.c + 1),
            repr((scr.r, scr.c, scr.cursor_visible, scr.style(scr.r, scr.c), scr.style(scr.r, scr.c + 1))))
        e.end()

        # ---- (5) the safeguard: a screen the library cannot know the terminal of is written as it always was -----------------------
        say("\n--- (5) a screen opened without CLEAR: the form overwrites what the program printed ------------------------------")
        # The skip needs the library to KNOW that the terminal shows its shadow, which SCREEN OPEN CLEAR and a repaint make so.  Without CLEAR the
        # library believes the screen blank while the terminal shows the program's PRINTed text, and a form's blank cells must still cover it.
        pg = "zzdpg" + RUN
        prog = ("   for r = 5 to 12\n      crt @(0, r) : str('X', 60) :\n   next r\n"
                "   screen open else crt 'NOTERM' ; stop\n"
                "   screen form title 'Covers' at 10,6 size 30,4 returning f\n"
                "   screen button f, 'ok', '&OK' at 2,1 default\n"
                "   screen wait f timeout 30 returning ev else null\n"
                "   screen hide f\n   screen close\n   crt @(0, 20) : 'PROG-DONE'\nend\n")
        with open(os.path.join(sysd, "bp", pg), "w") as fh:
            fh.write(prog)
        out = sb.sess(box, "BASIC bp %s" % pg)
        row("setup: the program compiled", "Compiled 1 program(s) with no errors" in out, out[-300:])
        e = sb.Ide(box, "RUN bp %s" % pg)
        L = e.lines()
        inside = "".join(L[r][10:40] for r in range(6, 10))
        row("the form is on the screen (its title is there)", "Covers" in "\n".join(L), "\n".join(l[:70] for l in L[4:12]))
        row("...it covers the printed X's under it (%d left in its 30 by 4 cells)" % inside.count("X"), "X" not in inside, repr(inside[:80]))
        row("...and the X's outside it are as they were (rows 5 and 12, and the sides of the rows between)",
            L[5][:60] == "X" * 60 and L[12][:60] == "X" * 60 and L[7][:10] == "X" * 10 and L[7][40:60] == "X" * 20,
            "\n".join(l[:70] for l in (L[5], L[7], L[12])))
        e.keys(sb.RET)
        row("the program ran on to its end", "PROG-DONE" in "\n".join(e.lines()), "\n".join(l[:60] for l in e.lines()[18:22]))
        e.end()
    finally:
        for d in ("bp", "bp.out"):
            pth = os.path.join(sysd, d, "zzdpg" + RUN)
            if os.path.exists(pth):
                os.remove(pth)
        for d in ("bp", "bp.out"):
            pth = os.path.join(sysd, d, fix)
            if os.path.exists(pth):
                os.remove(pth)
        sb.sess(box, "DELETE bp %s" % A, "DELETE bp %s" % B, "DELETE bp %s" % C, "DELETE bp %s" % fix)

    say("")
    say("sandbox-idedraw: %d passed, %d failed" % (passed, failed))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
