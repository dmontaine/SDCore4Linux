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
# 29 Oct 26 dm  The review's rows (R1, R2): G3 and G4 (Go to a line alone and 1.5,2.5; the IDE is up) and C2/C3 (a command that aborts leaves the IDE up).  G1 already held R1's second form.
#               WRITTEN, NOT RUN.
# 9 Nov 26 dm  Section T (S.184 stage 3): Stamp, Expand tabs, the character code (Alt-=), the Syntax colour and Line numbers switches, a tab width over 8; the record zze<run>tab
#               holds a tab.  Not held: Run with arguments (it needs a program and the screen given over).
# 9 Nov 26 dm  Section O (S.184 stage 3b): &ide.options& (an unknown word named, INDENT, TABS 7, NO.MOUSE, NO.CASE.EXPLORE), View > Mouse read from the bytes sent to the
#               terminal, the tree's order on a directory file whose ids differ by '_' and 'a', and View > Scroll the view up / down a line on a 60-line record; a
#               control with no options record.  O1 and O4 hold FOUR ids in order and O15 an Edit menu SED entry: the first run found the IDE's LOCATE in <1>
#               walking fields, so the tree's records were never in order and every SED entry of the Edit menu sent Alt-Backspace (O12 caught it).
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
CTRL_Q, CTRL_S, CTRL_R = sb.CTRL_Q, sb.CTRL_S, sb.CTRL_R
GOTO = sb.ALT_G                                                  # go to a line: Alt-G since S.179 (8 Nov 26; Ctrl-L is redraw)
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
   write '      x = 1':@fm:'if x = 1 then':@fm:'y = 2':@fm:'end' on p, '%(rec)sfmt'
   write 'a':char(9):'b':@fm:'no tab' on p, '%(rec)stab'
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
ABORTP = """   crt 'EABORT start'
   abort 'EABORT now'
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
    """F10, RIGHT n_right times (File is the first menu), DOWN n_down times, Return.  n_right counts the menus as they were before S.180 (File Go
    Search Build View); the Edit menu (8 Nov 26) is after File, so every menu but File is one Right further."""
    e.keys(F10, RIGHT * (n_right + 1 if n_right else 0), DOWN * n_down, RET)
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
    menu(e, 2, 4)                                                       # Find options (the fifth entry of Search: Find, Replace, List, Query replace, Find options)
    e.keys("W", RET)
    e.quiet()
    menu(e, 2, 2)
    e.keys("alpha", RET)
    e.quiet()
    tt = table_text(e)
    row("L3 with whole words on, 'alpha' lists line 1 only ('alphabet' is another word)", "alpha beta" in tt and "alphabet end" not in tt, repr(tt[:300]))
    menu(e, 2, 4)
    e.keys(RET)                                                       # blank: match case off, whole words off
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
    menu(e, 2, 5)                                                       # Upcase the selection (index 5)
    t = editor_text(e)
    row("U1 only the selection changes case: 'ALPHA beta' (the rest of the line and the other lines are as they were)", "ALPHA beta" in t and "Beta gamma" in t and "alphabet end" in t, repr(t[:200]))
    e.keys(CTRL_G)
    e.keys(RIGHT * 5)
    menu(e, 2, 6)                                                       # Downcase the selection (index 6)
    t = editor_text(e)
    row("U2 Downcase gives it back", "alpha beta" in t, repr(t[:200]))
    done(e)
    e = open_rec()                                                      # a fresh editor, no mark set: a case change keeps the mark, so the one U1 and U2 set would still select
    menu(e, 2, 5)
    row("U3 with nothing selected it says so", "Nothing is selected" in e.status(), e.status()[:120])
    done(e)


def section_xp():
    say("\n--- X: Export the selection and Import a record -----------------------------------------------------------------------------")
    e = open_rec()
    e.keys(CTRL_G)
    e.keys(RIGHT * 5)
    menu(e, 2, 8)                                                       # Export the selection: the form for the file and the record
    e.keys(EXP, RET)
    e.quiet()
    d = disk()
    row("X1 Export writes the selected text to the new record (the file is bp, the form's own default)", d.get(EXP) == "[alpha]", repr((d.get(EXP), e.status()[:100])))
    e.keys(DOWN, DOWN)                                                  # (the cursor to line 3 for the import)
    menu(e, 2, 7)                                                       # Import a record here
    e.keys(REC + "imp", RET)
    e.quiet()
    t = editor_text(e)
    row("X2 Import puts the lines of the record in at the cursor: INS1 and INS2 are in the text, and nothing was written", "INS1" in t and "INS2" in t and disk().get(REC) == "[%s]" % "^".join(LINES), repr(t[:300]))
    done(e)


def section_goto():
    say("\n--- G: Go to ---------------------------------------------------------------------------------------------------------------")
    e = open_rec()
    e.keys(GOTO)
    e.keys("3,4", RET)
    e.quiet()
    row("G1 'Go to 3,4' puts the cursor on line 3, column 4 (the status line gives both)", re.search(r"\b3\b\D+\b4\b", e.status()) is not None, e.status()[:120])
    e.keys(GOTO)
    e.keys("0", RET)
    e.quiet()
    row("G2 a zero is not a line: the cursor stays", re.search(r"\b3\b\D+\b4\b", e.status()) is not None, e.status()[:120])
    e.keys(GOTO)
    e.keys("2", RET)
    e.quiet()
    row("G3 'Go to 2' (a line alone) leaves the IDE up and puts the cursor on line 2 (review R1, 29 Oct 26: gl.p was used before it had a value, so any answer stopped the IDE)",
        "IDE: " in "\n".join(e.lines()[:3]) and re.search(r"\b2\b", e.status()) is not None, e.status()[:120])
    e.keys(GOTO)
    e.keys("1.5,2.5", RET)
    e.quiet()
    row("G4 'Go to 1.5,2.5' is line 1, column 2 (a line and a column are whole numbers), and the IDE is still up", "IDE: " in "\n".join(e.lines()[:3]) and re.search(r"\b1\b\D+\b2\b", e.status()) is not None, e.status()[:120])
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
    # review R2, 29 Oct 26: a command that ABORTS must not take the IDE with it (EXECUTE ... TRAPPING ABORTS).  The aborting program is compiled here and not in the setup, so that a compile
    # fault is one failed row and not the end of the run.  WRITTEN, NOT RUN.
    put("zzeabort" + RUN, ABORTP)
    o = sb.sess(BOX, "BASIC bp zzeabort" + RUN)
    ok = re.search(r"(?m)^Compiled 1 program\(s\) with no errors", o) is not None
    row("C2 setup: the program that aborts compiled", ok, o[-300:])
    if ok:
        e = open_rec()
        menu(e, 3, 4)
        e.keys("RUN bp zzeabort" + RUN, RET)
        e.quiet()
        row("C3 a command that aborts leaves the IDE up with the record on the screen (without TRAPPING ABORTS the abort cast the IDE off)", "IDE: " in "\n".join(e.lines()[:3]) and "alpha beta" in editor_text(e),
            "%r | %r" % ("\n".join(e.lines()[:3]), editor_text(e)[:100]))
        done(e)


CTRL_HOME, CTRL_END, CTRL_RIGHT, CTRL_DEL, INS = "\x1b[1;5H", "\x1b[1;5F", "\x1b[1;5C", "\x1b[3;5~", "\x1b[2~"


def section_modes():
    say("\n--- M: the editor's keys and modes (S.88 D2, 29 Oct 26; WRITTEN, NOT RUN) -------------------------------------------------------")
    e = open_rec()
    e.keys(CTRL_END, "Z")
    e.quiet()
    t = editor_text(e)
    row("M1 Ctrl-End goes to the end of the text: a typed Z is appended to the last line", "line fourZ" in t, repr(t[-120:]))
    done(e)
    e = open_rec()
    e.keys(CTRL_END, CTRL_HOME, "Y")
    e.quiet()
    row("M2 Ctrl-Home goes back to line 1 column 1: a typed Y begins the first line", "Yalpha beta" in editor_text(e), repr(editor_text(e)[:120]))
    e.keys(CTRL_RIGHT, "|")
    e.quiet()
    row("M3 Ctrl-Right moves over the rest of a word: the | stands after 'Yalpha'", "Yalpha| beta" in editor_text(e), repr(editor_text(e)[:120]))
    done(e)
    e = open_rec()
    e.keys(CTRL_DEL)
    e.quiet()
    row("M4 Ctrl-Del at the start of line 1 deletes the word 'alpha', not the line", " beta" in editor_text(e) and "alpha beta" not in editor_text(e) and "Beta gamma" in editor_text(e), repr(editor_text(e)[:120]))
    e.keys(CTRL_Z)
    e.quiet()
    row("M5 ONE Ctrl-Z gives the word back", "alpha beta" in editor_text(e), repr(editor_text(e)[:120]))
    done(e)
    e = open_rec()
    e.keys(INS, "XY")
    e.quiet()
    row("M6 Ins turns overwrite on: XY replaces 'al' (the first line is 'XYpha beta') and the status line says [overwrite]", "XYpha beta" in editor_text(e) and "[overwrite]" in e.status(), "%r | %r" % (editor_text(e)[:100], e.status()[:120]))
    e.keys(INS, "Q")
    e.quiet()
    row("M7 Ins again turns it off: Q is put in before the next character, and the marker is gone", "XYQpha beta" in editor_text(e) and "[overwrite]" not in e.status(), "%r | %r" % (editor_text(e)[:100], e.status()[:120]))
    done(e)
    e = open_rec()
    e.keys("   x", RET, "Q")
    e.quiet()
    row("M8 control (auto-indent off): Return after '   x' starts the next line at column 1, so the line holding Q is 'Qalpha beta'", "Qalpha beta" in editor_text(e) and "   Qalpha" not in editor_text(e), repr(editor_text(e)[:120]))
    done(e)
    e = open_rec()
    menu(e, 4, 3)                                                       # View menu, Auto-indent (the fourth entry after Theme, Refresh, Overwrite mode)
    row("M9 View > Auto-indent says it is on", "Auto-indent is on" in e.status(), e.status()[:120])
    e.keys("   x", RET, "Q")
    e.quiet()
    row("M10 with auto-indent on, Return after '   x' begins the next line with the same 3 blanks: '   Qalpha beta'", "   Qalpha beta" in editor_text(e), repr(editor_text(e)[:120]))
    done(e)
    e = open_rec()
    menu(e, 4, 4)                                                       # View menu, Tab width
    e.keys("\x7f5", RET)
    e.quiet()
    row("M11 View > Tab width 5 says so", "Tab width is 5" in e.status(), e.status()[:120])
    e.keys(CTRL_HOME, "\t")
    e.quiet()
    row("M12 Tab now indents by 5: the first line begins with 5 blanks", "1      alpha beta" in editor_text(e) and "1       alpha beta" not in editor_text(e), repr(editor_text(e)[:120]))
    done(e)
    e = sb.Ide(BOX, "IDE bp %sfmt" % REC)
    e.quiet()
    before = editor_text(e)
    menu(e, 3, 5)                                                       # Build menu, Format the program (its sixth entry)
    after = editor_text(e)
    row("M13 Build > Format changes the program's layout (the text is not what it was) and the status line says it is laid out again", after != before and "laid out again" in e.status(), "%r | %r | %r" % (before[:80], after[:80], e.status()[:100]))
    e.keys(CTRL_Z)
    e.quiet()
    row("M14 ONE Ctrl-Z gives the program back as it was", editor_text(e).split("\n")[0].rstrip() == before.split("\n")[0].rstrip(), repr(editor_text(e)[:100]))
    done(e)
    e = open_rec()
    menu(e, 3, 5)
    row("M15 Format on a record that is not BASIC (the fixture's lines) changes nothing or says so: the text is still there", "alpha beta" in editor_text(e), "%r | %r" % (editor_text(e)[:100], e.status()[:100]))
    done(e)


def section_s184():
    """9 Nov 26 (S.184 stage 3): SED's small commands in the IDE.  Search: Stamp (10th entry), Expand tabs (11th); View: Tab width (5th), Syntax colour (6th),
    Line numbers (7th), Character code (8th, Alt-=).  Nothing is saved: the disk is read at the end."""
    say("\n--- T: SED's small commands (S.184 stage 3) -------------------------------------------------------------------------------")
    e = open_rec()
    menu(e, 2, 9)                                                       # Search > Stamp a history line
    t = editor_text(e)
    row("T1 Stamp puts '* Updated by <who> (<login>) ...' above line 1 and says so; line 1 is now the old line 1's second", "* Updated by" in t.split("\n")[0] and "alpha beta" in t.split("\n")[1]
        and "history line" in e.status(), repr((t[:160], e.status()[:120])))
    e.keys(CTRL_Z)
    e.quiet()
    row("T2 one Ctrl-Z takes the stamp away", "* Updated by" not in editor_text(e) and "alpha beta" in editor_text(e).split("\n")[0], repr(editor_text(e)[:120]))
    menu(e, 2, 10)                                                      # Search > Expand tabs
    row("T3 control: Expand tabs on a text with no tab says so", "no tab" in e.status(), e.status()[:120])
    e.keys("\x1b=")                                                     # Alt-= : the character code (line 1, column 1 is the a of alpha)
    e.quiet()
    row("T4 Alt-= shows the code of the character at the cursor: char(97) 'a', field 1 value 1 subvalue 1", "char(97) 'a'" in e.status() and "field 1, value 1, subvalue 1" in e.status(), e.status()[:160])
    menu(e, 4, 5)                                                       # View > Syntax colour
    row("T5 View > Syntax colour switches it off and says so", "Syntax color is off" in e.status(), e.status()[:120])
    menu(e, 4, 5)
    row("T6 ...and on again", "Syntax color is on" in e.status(), e.status()[:120])
    with_n = e.lines()[3][28:40]
    menu(e, 4, 6)                                                       # View > Line numbers
    without_n = e.lines()[3][28:40]
    row("T7 View > Line numbers takes the numbers away (line 1's row no longer begins with its number) and says so",
        "Line numbers are off" in e.status() and re.search(r"\b1\b", with_n) is not None and "alpha" in without_n and re.search(r"^\s*\*?\s*1\s", without_n) is None, repr((with_n, without_n, e.status()[:80])))
    menu(e, 4, 6)
    row("T8 ...and puts them back", "Line numbers are on" in e.status(), e.status()[:120])
    menu(e, 4, 4)                                                       # View > Tab width
    e.keys("\x15", "50", RET)                                           # Ctrl-U empties the answer, then 50
    e.quiet()
    row("T9 Tab width takes 50 (it took 1 to 8 only)", "Tab width is 50" in e.status(), e.status()[:120])
    done(e)
    e = sb.Ide(BOX, "IDE bp %stab" % REC)
    e.quiet()
    menu(e, 4, 4)
    e.keys("\x15", "3", RET)
    menu(e, 2, 10)                                                      # Search > Expand tabs, tab width 3
    t = editor_text(e)
    row("T10 Expand tabs: the tab after 'a' becomes blanks to the next stop of 3 ('a  b'), and one line is counted", "a  b" in t and "1 line(s) had tabs" in e.status(), repr((t[:80], e.status()[:120])))
    done(e)
    d = disk()
    row("T11 control: nothing was saved (the record on the disk is as the fixture wrote it)", d.get(REC) == "[%s]" % "^".join(LINES), repr(d.get(REC)))


OFILE = "zzo" + RUN                     # a directory file whose two ids sort differently by case-blind order: '_' is between 'Z' and 'a'
OFIX = """   open 'bp' to p else stop 'OFIX no bp'
   t = ''
   for i = 1 to 60
      t<i> = 'L':i
   next i
   write t on p, '%(rec)slong'
   execute 'create.file %(ofile)s directory' capturing out
   open '%(ofile)s' to f else stop 'OFIX no file'
   write 'x' on f, '%(ofile)sc1'
   write 'x' on f, '%(ofile)s_1'
   write 'x' on f, '%(ofile)sb1'
   write 'x' on f, '%(ofile)sa1'
   crt 'OFIX done'
end
"""
OSET = """   open 'VOC' to v else stop 'OSET no voc'
   write 'X':@fm:'INDENT TABS 7 NO.MOUSE NO.CASE.EXPLORE BOGUS' on v, '&ide.options&'
   crt 'OSET done'
end
"""
ODEL = """   open 'VOC' to v else stop 'ODEL no voc'
   delete v, '&ide.options&'
   crt 'ODEL done'
end
"""


def tree_order(e):
    """The file's four ids in the order the tree (the first 28 columns) shows them, as their suffixes ('_1', 'a1', 'b1', 'c1'); an absent one is left out.
    Four ids, so that an order that is not sorted cannot pass by luck (the tree's insert walked the fields until 9 Nov 26: 'd b e a c' gave a c b e d)."""
    t = [l[:28] for l in e.lines()[3:39]]
    seen = []
    for l in t:
        for s in ("_1", "a1", "b1", "c1"):
            if (OFILE + s) in l and s not in seen:
                seen.append(s)
    return seen


def mouse_last(raw):
    """'on' or 'off': which of the terminal's mouse switches the IDE sent last (?1000h asks for reports, ?1000l stops them); '' when neither was sent."""
    s = raw.decode("latin-1")
    on, off = s.rfind("\x1b[?1000h"), s.rfind("\x1b[?1000l")
    return "" if on < 0 and off < 0 else ("on" if on > off else "off")


def section_options():
    """9 Nov 26 (S.184 stage 3b): the account's &ide.options& (an X record, SED's &sed.options& words), View > Mouse, NO.CASE.EXPLORE, and View > Scroll the view
    up / down a line (SED's nudge).  View: Mouse is the 9th entry, Scroll up the 10th, Scroll down the 11th.  The options record is deleted at the end."""
    say("\n--- O: the options record, the mouse, case-blind order, the nudge (S.184 stage 3b) ------------------------------------------")
    SUBS["ofile"] = OFILE
    put("zzofix" + RUN, OFIX)
    put("zzoset" + RUN, OSET)
    put("zzodel" + RUN, ODEL)
    o = sb.sess(BOX, "BASIC bp zzofix%s zzoset%s zzodel%s" % (RUN, RUN, RUN), "RUN bp zzofix" + RUN, "RUN bp zzodel" + RUN)
    if not row("O0 setup: the three programs compile, the file and the long record are made", re.search(r"(?m)^Compiled 3 program\(s\) with no errors", o) is not None
               and "OFIX done" in o and "ODEL done" in o, o[-500:]):
        return
    e = sb.Ide(BOX, "IDE " + OFILE)
    e.quiet()
    tr = tree_order(e)
    row("O1 control (no options record): the tree lists the ids in order, _1 a1 b1 c1 ('_' sorts before 'a'), and the mouse was switched on",
        tr == ["_1", "a1", "b1", "c1"] and mouse_last(e.s.raw) == "on", repr((tr, mouse_last(e.s.raw))))
    done(e)
    o = sb.sess(BOX, "RUN bp zzoset" + RUN)
    row("O2 setup: &ide.options& written", "OSET done" in o, o[-300:])
    try:
        e = sb.Ide(BOX, "IDE " + OFILE)
        e.quiet()
        tr = tree_order(e)
        row("O3 the status line names the word the IDE does not use (BOGUS)", "does not use: BOGUS" in e.status(), e.status()[:140])
        row("O4 NO.CASE.EXPLORE: the ids in case-blind order, a1 b1 c1 _1 ('A' before '_')", tr == ["a1", "b1", "c1", "_1"], repr(tr))
        row("O5 NO.MOUSE: the last mouse switch the IDE sent stops the reports", mouse_last(e.s.raw) == "off", repr(mouse_last(e.s.raw)))
        menu(e, 4, 8)                                                   # View > Mouse
        row("O6 View > Mouse turns it on and says so (it began off), and the terminal is told", "The mouse is on" in e.status() and mouse_last(e.s.raw) == "on",
            repr((e.status()[:120], mouse_last(e.s.raw))))
        menu(e, 4, 8)
        row("O7 ...and off again", "The mouse is off" in e.status() and mouse_last(e.s.raw) == "off", repr((e.status()[:120], mouse_last(e.s.raw))))
        done(e)
        e = open_rec()
        e.keys("   x", RET, "Q")
        e.quiet()
        row("O8 INDENT: auto-indent is on from the start - Return after '   x' begins the next line with 3 blanks", "   Qalpha beta" in editor_text(e), repr(editor_text(e)[:120]))
        done(e)
        e = open_rec()
        e.keys(CTRL_HOME, "\t")
        e.quiet()
        row("O9 TABS 7: Tab indents by 7 from the start", "1" + " " * 8 + "alpha beta" in editor_text(e) and "1" + " " * 9 + "alpha beta" not in editor_text(e), repr(editor_text(e)[:120]))
        done(e)
    finally:
        o = sb.sess(BOX, "RUN bp zzodel" + RUN)
        row("O10 setup: &ide.options& deleted", "ODEL done" in o, o[-300:])
    e = sb.Ide(BOX, "IDE bp %slong" % REC)
    e.quiet()
    first = lambda: (editor_text(e).split("\n") or [""])[0]
    row("O11 control: the long record opens with L1 on the editor's first row", re.search(r"\bL1\b", first()) is not None, repr(first()[:80]))
    menu(e, 4, 10)                                                      # View > Scroll the view down a line
    row("O12 View > Scroll the view down a line: L2 is on the first row", re.search(r"\bL2\b", first()) is not None and re.search(r"\bL1\b", first()) is None, repr(first()[:80]))
    menu(e, 4, 9)                                                       # View > Scroll the view up a line
    row("O13 View > Scroll the view up a line: L1 is back on the first row", re.search(r"\bL1\b", first()) is not None, repr(first()[:80]))
    done(e)
    e = sb.Ide(BOX, "IDE " + OFILE)
    e.quiet()
    row("O14 control: with the record gone the IDE names no word on the status line", "does not use" not in e.status(), e.status()[:140])
    done(e)
    e = open_rec()
    e.keys(F10, RIGHT, DOWN * 13, RET)                                  # Edit > Word in capitals (the 14th entry; Edit is the second menu)
    e.quiet()
    row("O15 Edit > Word in capitals sends the editor Alt-U: 'alpha' becomes 'ALPHA' (every SED entry of the Edit menu sent Alt-Backspace until 9 Nov 26)",
        "ALPHA beta" in editor_text(e), repr(editor_text(e)[:120]))
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
        section_modes()
        section_s184()
        section_options()
    finally:
        teardown()
    say("\nsandbox-ide-edit: %d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        say("sandbox-ide-edit: CANNOT RUN - no row ran (a broken test, not a pass)")
        return 2
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
