#!/usr/bin/env python3
#
# sandbox-viewport.py - containers and viewports of the screen library, through USER programs on a pseudo-terminal at 140 by 42.
# No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-viewport.py <dir> [--build] [--only=con,nest,keys,...]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or absent).
# Exit 0 every row passed, 1 a row failed, 2 it could not run.  Only one private SD can exist per keyset; stop the sandbox afterwards
# with sandbox-fromtree.py <dir> stop.
#
# START-HISTORY:
# 18 Oct 26 dm  Written with SCREEN CONTAINER / VIEWPORT / IN / MOVE / DELETE / SCROLL (plan-fullscreen-apps.md, "Container and
#               viewport").
# END-HISTORY
#
# HOW IT DRIVES THE PROGRAMS.  As sandbox-screen.py: every program is an ordinary USER program compiled by a plain session, run on a
# pseudo-terminal (ptydrive.py), the screen read from the emulator (termscreen.py).  A program keeps a LOG of the events it was given
# (focus changes, scrolls) and prints it on row 40 when the user presses Esc, so a row can compare what the library reported with what the
# screen shows.  F2-F7 are keys the form has no use for, which WAIT hands to the program as key events; the program does one thing to the
# form for each (move, hide, ...), so a row can send a key and read the screen.  The four things the plan left to test (popups, the
# cursor of a widget scrolled away, widgets that do not draw through the clip, the mouse drag) have a row each, marked PLAN-1 to PLAN-4.
# Every row that changes something has a control (the screen before the key); a program that printed no log fails its rows.

import importlib.util
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("sbs", os.path.join(HERE, "sandbox-screen.py"))
sbs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sbs)
Term = sbs.Term
click = sbs.click
sess = sbs.sess
TOOL = sbs.TOOL
passed = failed = 0

COLS, ROWS = 140, 42
UP, DOWN, LEFT, RIGHT = "\x1bOA", "\x1bOB", "\x1bOD", "\x1bOC"
TAB, BTAB, ESC, RET = "\t", "\x1b[Z", "\x1b", "\r"
HOME, END, PGUP, PGDN = "\x1b[1~", "\x1b[4~", "\x1b[5~", "\x1b[6~"
F2, F3, F4 = "\x1bOQ", "\x1bOR", "\x1bOS"
F5, F6, F7, F8 = "\x1b[15~", "\x1b[17~", "\x1b[18~", "\x1b[19~"
VM = "\xfd"


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
    say("sandbox-viewport: CANNOT RUN - " + msg)
    sys.exit(2)


class PaddedTerm(Term):
    """A Term whose lines are all COLS wide, so that a row can index a cell of a blank line (a program that did not run leaves the screen blank:
    that must be a failed row, not an exception)."""

    def lines(self):
        return [l.ljust(COLS) for l in Term.lines(self)]


def term(box, prog):
    return PaddedTerm(box, "RUN bp " + prog, cols=COLS, rows=ROWS)


def wheel(t, x, y, up=False, shift=False):
    """The wheel at cell x, y: 64 up, 65 down, +4 with Shift (the xterm SGR report)."""
    b = (64 if up else 65) + (4 if shift else 0)
    return t.keys("\x1b[<%d;%d;%dM" % (b, x + 1, y + 1), idle=0.35)


def drag(t, x, y):
    """The pointer moved to x, y with the left button held (button 0 + 32)."""
    return t.keys("\x1b[<32;%d;%dM" % (x + 1, y + 1), idle=0.3)


def press(t, x, y):
    return t.keys("\x1b[<0;%d;%dM" % (x + 1, y + 1), idle=0.3)


def release(t, x, y):
    return t.keys("\x1b[<0;%d;%dm" % (x + 1, y + 1), idle=0.3)


def at(L, r, c, s):
    return 0 <= r < len(L) and L[r][c:c + len(s)] == s


def blank(L, r, c0, c1):
    return 0 <= r < len(L) and L[r][c0:c1].strip() == ""


def has(L, s):
    return any(s in l for l in L)


def blank_rect(L, r0, r1, c0, c1):
    """Every cell of the rectangle (rows r0..r1, columns c0..c1 inclusive) is a blank."""
    return all(blank(L, r, c0, c1 + 1) for r in range(r0, r1 + 1))


def outside(L, r0, r1, c0, c1):
    """The screen with the rectangle blanked: what is NOT in it."""
    out = []
    for r, l in enumerate(L):
        if r0 <= r <= r1:
            l = l[:c0] + " " * (c1 - c0 + 1) + l[c1 + 1:]
        out.append(l.rstrip())
    return out


def logline(L):
    for l in L:
        if l.startswith("LOG ") or l.rstrip() == "LOG":
            return l[4:].rstrip()
    return None


def finish(t):
    """Esc leaves the loop and the program prints its log: returns the screen."""
    return t.keys(ESC, idle=0.8)


# ------------------------------------------------------------------------------------------------------------------------------
# The programs
# ------------------------------------------------------------------------------------------------------------------------------

OPEN = "   screen open clear else crt @(0, 41) : 'NOTERM' ; stop\n"

# One container with children; F2 moves it, F3 hides it, F4 shows it, F5 disables it, F6 enables it, F7 deletes it.
# Form at 1,1 (so a widget at x,y is on the screen at 1+x,1+y); the box at 4,3 of size 30 by 8: corner (5,4), inside from (6,5) and 28 by 6.
CON = OPEN + """   screen form title 'Container' at 1,1 size 100,30 returning f
   screen label f, 'top', 'TOPLABEL' at 2,1
   screen container f, 'box' at 4,3 size 30,8 title 'Box'
   screen in f, 'box'
   screen label f, 'c1', 'CHILD-ONE' at 0,0
   screen label f, 'c2', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdefghijklmnop' at 0,1
   screen label f, 'c3', 'BELOWINNER' at 0,6
   screen label f, 'c4', 'RIGHTEDGE' at 26,2
   screen label f, 'c5', 'LEFTCUT' at -3,5
   screen label f, 'c6', 'ABOVE' at 5,-2
   screen entry f, 'ce' at 0,3 width 10 value 'abc'
   screen button f, 'cb', '&Go' at 0,4
   screen in f, ''
   screen label f, 'out', 'OUTSIDE' at 40,3
   screen entry f, 'oe' at 40,5 width 10 value 'zz'
   log = ''
   loop
      screen wait f returning ev else exit
      begin case
         case ev<1> = 'focus'
            log := 'F:' : ev<2> : ' '
         case ev<1> = 'key'
            k = ev<3>
            begin case
               case k = 'f2'
                  screen move f, 'box' at 30,12
               case k = 'f3'
                  screen set f, 'box' visible 0
               case k = 'f4'
                  screen set f, 'box' visible 1
               case k = 'f5'
                  screen set f, 'box' enabled 0
               case k = 'f6'
                  screen set f, 'box' enabled 1
               case k = 'f7'
                  screen delete f, 'box' returning n
                  log := 'DEL:' : n : ' '
                  screen get f, 'ce' returning g else log := 'GONE '
            end case
      end case
   repeat
   crt @(0, 40) : 'LOG ' : log
end
"""

# Containers in a container.  Form at 1,1.  Outer: corner (3,3), inside from (4,4), 38 by 12 (columns 4-41, rows 4-15).  Inner: at 20,4 of the
# outer's inside, so corner (24,8), 24 by 7 (columns 24-47: it runs past the outer's right edge), inside from (25,9), 22 by 5.
NST = OPEN + """   screen form title 'Nested' at 1,1 size 100,30 returning f
   screen container f, 'o' at 2,2 size 40,14 title 'Outer'
   screen in f, 'o'
   screen label f, 'ol', 'OUTERLBL' at 0,0
   screen container f, 'i' at 20,4 size 24,7 title 'Inner'
   screen in f, 'i'
   screen label f, 'dl', 'DEEPLABEL' at 0,0
   screen entry f, 'de' at 0,1 width 10 value 'deep'
   screen label f, 'dw', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' at 0,2
   screen in f, ''
   screen entry f, 'oe' at 50,3 width 10 value 'zz'
   log = ''
   loop
      screen wait f returning ev else exit
      begin case
         case ev<1> = 'focus'
            log := 'F:' : ev<2> : ' '
         case ev<1> = 'key'
            k = ev<3>
            begin case
               case k = 'f2'
                  screen move f, 'o' at 20,5
               case k = 'f3'
                  screen set f, 'o' visible 0
               case k = 'f4'
                  screen set f, 'o' visible 1
               case k = 'f5'
                  screen set f, 'o' enabled 0
               case k = 'f6'
                  screen set f, 'o' enabled 1
               case k = 'f7'
                  screen delete f, 'o' returning n
                  log := 'DEL:' : n : ' '
                  screen get f, 'de' returning g else log := 'GONE '
            end case
      end case
   repeat
   crt @(0, 40) : 'LOG ' : log
end
"""

# A borderless container against the same widgets in the form itself: the screens must be the same.  KIND is replaced by the lines of each.
EQ_BODY = """   screen label f, 'a', 'ALPHA' at X1,Y1
   screen entry f, 'b' at X2,Y2 width 12 value 'bravo'
   screen check f, 'c', '&Charlie' at X3,Y3 value 1
   screen list f, 'd', 'one':@vm:'two':@vm:'three' at X4,Y4 size 10,3
   screen button f, 'e', '&Echo' at X5,Y5 default
"""
EQ_POS = [(3, 2), (3, 4), (3, 6), (3, 8), (3, 12)]


def eq_program(boxed):
    out = OPEN + "   screen form title 'Same' at 1,1 size 60,20 returning f\n"
    ox, oy = (10, 3) if boxed else (0, 0)
    if boxed:
        out += "   screen container f, 'bx' at 10,3 size 40,14 noborder\n   screen in f, 'bx'\n"
        # a borderless container's inside starts at its corner: a widget at x,y is at 10+x,3+y of the form
        pos = EQ_POS
        pos = [(x, y) for (x, y) in pos]
    else:
        pos = [(x + 10, y + 3) for (x, y) in EQ_POS]
    body = EQ_BODY
    for i, (x, y) in enumerate(pos, 1):
        body = body.replace("X%d,Y%d" % (i, i), "%d,%d" % (x, y))
    out += body
    out += """   screen run f returning p then
      res = 'PRESSED ':p
   end else
      res = 'CANCEL ':p
   end
   screen values f returning v
   crt @(0, 40) : 'LOG ' : res : ' ' : v{'b'} : '|' : v{'c'} : '|' : v{'d'} : '|'
end
"""
    return out


# A viewport.  Form at 1,1 size 100 by 34.  The viewport is at 2,2 of the form: corner (3,3), inside from (4,4), 38 by 12 - with both bars
# the window is 37 columns by 11 rows: columns 4-40 and rows 4-14, the vertical bar in column 41 (rows 4-14), the horizontal bar in row 15
# (columns 4-40), the border in column 42 and row 16.  The sheet is 80 by 40.  Labels R<r>C<c> on a grid, every 10 columns and every 4 rows
# (r 0-9, c 0-7), so the label at sheet x,y shows at screen 4+x-sx, 4+y-sy; the entries and the list sit between the label rows.
# 'under' is in the form BEFORE the viewport at the place where the viewport's child 'bot' would be if it were not cut.
VPS_CHILDREN = """   for r = 0 to 9
      for c = 0 to 7
         screen label f, 'g':r:'_':c, 'R':fmt(r, 'R%2'):'C':c at c*10, r*4
      next c
   next r
   screen entry f, 'e1' at 2,1 width 10 value 'hello'
   screen entry f, 'ee' at 35,2 width 10 value 'EDGE'
   screen entry f, 'e2' at 22,10 width 10 value 'two'
   screen list f, 'lst', 'alpha':@vm:'beta':@vm:'gamma' at 56,9 size 12,3
   screen combo f, 'cb', 'Albany':@vm:'Boston':@vm:'Chicago' at 12,14 width 10 value 'Boston'
   screen entry f, 'bot' at 2,18 width 10 value 'BOT'
   screen entry f, 'far' at 61,33 width 10 value 'FAR'
"""

VPS_LOOP = """   log = ''
   loop
      screen wait f returning ev else exit
      begin case
         case ev<1> = 'focus'
            log := 'F:' : ev<2> : ' '
         case ev<1> = 'change'
            log := 'C:' : ev<2> : '=' : convert(@vm, ',', ev<3>) : ' '
         case ev<1> = 'key'
            k = ev<3>
            begin case
               case k = 'f2'
                  screen scroll f, 'vp' to 5,7 returning s
                  log := 'S:' : convert(@vm, ',', s) : ' '
               case k = 'f3'
                  screen scroll f, 'vp' by 2,2 returning s
                  log := 'S:' : convert(@vm, ',', s) : ' '
               case k = 'f4'
                  screen scroll f, 'vp' to 999,999 returning s
                  log := 'S:' : convert(@vm, ',', s) : ' '
               case k = 'f5'
                  screen move f, 'vp' at 30,12
               case k = 'f6'
                  screen set f, 'vp' visible 0
               case k = 'f7'
                  screen delete f, 'vp' returning n
                  log := 'DEL:' : n : ' '
               case k = 'f8'
                  screen set f, 'vp' enabled 0
               case k = 'f9'
                  screen get f, 'vp' returning s
                  crt @(0, 38) : 'POS ' : convert(@vm, ',', s) : space(10) :
               case k = 'a'
                  screen scroll f, 'vp' to 3,0
               case k = 'b'
                  screen scroll f, 'vp' to 0,2
               case k = 'c'
                  screen scroll f, 'vp' to 6,0
               case k = 'd'
                  screen scroll f, 'vp' to 30,0
               case k = 'e'
                  screen scroll f, 'vp' to 30,10
               case k = 'f'
                  screen scroll f, 'vp' to 0,0
            end case
      end case
   repeat
   screen get f, 'vp' returning s else s = 'GONE'
   crt @(0, 39) : 'VP ' : convert(@vm, ',', s)
   crt @(0, 40) : 'LOG ' : log
end
"""

VPS = (OPEN + """   screen form title 'Viewport' at 1,1 size 100,34 returning f
   screen entry f, 'under' at 5,21 width 10 value 'UNDER'
   screen viewport f, 'vp' at 2,2 size 40,14 content 80,40 title 'Sheet'
   screen in f, 'vp'
""" + VPS_CHILDREN + """   screen in f, ''
   screen label f, 'tail', 'TAILLABEL' at 2,18
   screen entry f, 'oe' at 50,3 width 10 value 'out'
   screen button f, 'ok', '&OK' at 2,30
""" + VPS_LOOP)

# The same form with the focus asked for on a child that is out of view before the form is shown
VPS_START = VPS.replace("   screen in f, ''\n   screen label f, 'tail'", "   screen in f, ''\n   screen focus f, 'far'\n   screen label f, 'tail'")

# A viewport of no scrolling to do (the sheet is as small as the window): no bars, nothing moves
VPS_FLAT = (OPEN + """   screen form title 'Flat' at 1,1 size 60,20 returning f
   screen viewport f, 'vp' at 2,2 size 30,8 title 'Same size'
   screen in f, 'vp'
   screen label f, 'a', 'ONE' at 0,0
   screen label f, 'b', 'TWO' at 0,5
   screen in f, ''
""" + VPS_LOOP.replace("screen get f, 'vp'", "screen get f, 'vp'"))

# Widgets that draw a lot - a memo and a table - and one that opens a list, in a viewport smaller than they are
WID = OPEN + """   screen form title 'Wide' at 1,1 size 100,34 returning f
   screen label f, 'lab', 'OUTSIDE-LABEL' at 50,2
   screen viewport f, 'vp' at 2,2 size 30,10 content 60,40 title 'Sheet'
   screen in f, 'vp'
   screen memo f, 'm', 'line1':@fm:'line2':@fm:'line3':@fm:'line4':@fm:'line5':@fm:'line6':@fm:'line7':@fm:'line8':@fm:'line9':@fm:'line10':@fm:'line11':@fm:'line12' at 0,0 size 20,14
   screen table f, 't', 'Name':@vm:'Qty', 'ant':@vm:'1':@fm:'bee':@vm:'2':@fm:'cat':@vm:'3':@fm:'dog':@vm:'4':@fm:'eel':@vm:'5':@fm:'fox':@vm:'6':@fm:'gnu':@vm:'7' at 22,0 size 24,10
   screen in f, ''
   screen button f, 'ok', '&OK' at 2,20
   log = ''
   loop
      screen wait f returning ev else exit
      if ev<1> = 'focus' then log := 'F:' : ev<2> : ' '
   repeat
   screen get f, 'm' returning mt
   crt @(0, 40) : 'LOG ' : log : ' MEMO ' : len(mt)
end
"""

# Viewports in a viewport.  Form at 1,1.  Outer: at 2,2 of the form, corner (3,3), 50 by 20, inside from (4,4), window 47 by 17 (bars), sheet 120 by 80.
# Inner: at 10,10 of the outer's sheet, 30 by 10 (inside 28 by 8, window 27 by 7 with bars), sheet 60 by 40.
NVP = OPEN + """   screen form title 'Nested viewports' at 1,1 size 100,34 returning f
   screen viewport f, 'ov' at 2,2 size 50,20 content 120,80 title 'Outer'
   screen in f, 'ov'
   screen label f, 'o0', 'OUTER-TOP' at 0,0
   screen label f, 'o1', 'OUTER-FAR' at 60,0
   screen viewport f, 'iv' at 10,10 size 30,10 content 60,40 title 'Inner'
   screen in f, 'iv'
   screen label f, 'i0', 'INNER-TOP' at 0,0
   screen label f, 'i1', 'INNER-ROW20' at 0,20
   screen entry f, 'ie' at 40,30 width 10 value 'deepin'
   screen in f, 'ov'
   screen entry f, 'oe' at 70,50 width 10 value 'outerin'
   screen in f, ''
   screen button f, 'ok', '&OK' at 2,30
   log = ''
   loop
      screen wait f returning ev else exit
      begin case
         case ev<1> = 'focus'
            log := 'F:' : ev<2> : ' '
         case ev<1> = 'change'
            log := 'C:' : ev<2> : '=' : convert(@vm, ',', ev<3>) : ' '
         case ev<1> = 'key' and ev<3> = 'f9'
            screen get f, 'ov' returning a
            screen get f, 'iv' returning b
            crt @(0, 38) : 'POS ' : convert(@vm, ',', a) : ' ' : convert(@vm, ',', b) : space(10) :
      end case
   repeat
   screen get f, 'ov' returning a
   screen get f, 'iv' returning b
   crt @(0, 39) : 'OV ' : convert(@vm, ',', a) : ' IV ' : convert(@vm, ',', b)
   crt @(0, 40) : 'LOG ' : log
end
"""

# The statements' refusals
BADS = OPEN + """   r1 = '-' ; r2 = '-' ; r3 = '-' ; r4 = '-' ; r5 = '-' ; r6 = '-' ; r7 = '-' ; r8 = '-' ; r9 = '-'
   screen form title 'Bad' returning f
   screen label f, 'lab', 'text' at 1,1
   screen container f, 'c' at 1,3 size 10,5
   screen viewport f, 'v' at 1,9 size 10,5 content 30,30
   screen in f, 'nosuch' else r1 = 'NOIN'
   screen in f, 'lab' else r2 = 'LABELIN'
   screen move f, 'lab' size 5,5 else r3 = 'NOSIZE'
   screen move f, 'c' content 5,5 else r4 = 'NOCONTENT'
   screen move f, 'nosuch' at 1,1 else r5 = 'NOMOVE'
   screen scroll f, 'c' to 1,1 else r6 = 'NOSCROLL'
   screen scroll f, 'nosuch' to 1,1 else r7 = 'NOSCROLL2'
   screen delete f, 'nosuch' else r8 = 'NODEL'
   screen in f, 'c'
   screen in f, '' else r9 = 'FAILED'
   screen scroll f, 'v' to 7,9 returning s
   screen get f, 'v' returning g
   screen delete f, 'c' returning n
   not.a.form = 'text'
   screen in not.a.form, 'c' else r9 = 'NOFORM'
   crt @(0, 1) : 'BAD ' : r1 : ' ' : r2 : ' ' : r3 : ' ' : r4 : ' ' : r5 : ' ' : r6 : ' ' : r7 : ' ' : r8 : ' ' : r9 : '|'
   crt @(0, 2) : 'GOOD ' : convert(@vm, ',', s) : '|' : convert(@vm, ',', g) : '|' : n : '|'
end
"""

# 200 by 60 of sheet in a window on the whole 140 by 42 screen: 600 labels and 30 entries
BIG = OPEN + """   screen form title 'Big' at 0,0 size 140,42 returning f
   screen viewport f, 'vp' at 1,1 size 138,40 content 200,60 title 'Sheet 200 by 60'
   screen in f, 'vp'
   for r = 0 to 29
      for c = 0 to 19
         screen label f, 'g':r:'_':c, 'R':fmt(r, 'R%2'):'C':fmt(c, 'R%2') at c*10, r*2
      next c
   next r
   for r = 0 to 29 step 1
      screen entry f, 'e':r at 6, r*2+1 width 8 value 'e':r
   next r
   screen in f, ''
   log = ''
   nch = 0
   last = ''
   loop
      screen wait f returning ev else exit
      if ev<1> = 'change' then
         nch += 1
         if nch <= 6 then log := ev<2> : '=' : convert(@vm, ',', ev<3>) : ' '
         last = convert(@vm, ',', ev<3>)
      end
   repeat
   screen get f, 'vp' returning s
   crt @(0, 40) : 'LOG ' : log : 'N=' : nch : ' LAST=' : last : ' VP ' : convert(@vm, ',', s)
end
"""

# A modal form (SCREEN RUN) with a viewport and an entry in it, for the place of the cursor.  Form at 2,1; the viewport at 2,3 of it: corner
# (4,4), inside from (5,5) 18 by 6, window 17 by 5 (columns 5-21, rows 5-9, bar column 22 and row 10); sheet 40 by 20; e1 at 2,3 of the sheet.
CUR = OPEN + """   screen form title 'Cursor' at 2,1 size 60,24 returning f
   screen entry f, 'under' at 40,10 width 10 value 'under'
   screen viewport f, 'vp' at 2,3 size 20,8 content 40,20 title 'Sheet'
   screen in f, 'vp'
   screen label f, 'l0', 'zero' at 0,0
   screen entry f, 'e1' at 2,3 width 10 value 'hello'
   screen entry f, 'far' at 25,15 width 10 value 'FAR'
   screen in f, ''
   screen button f, 'ok', '&OK' at 2,20 default
   screen run f returning p then
      res = 'PRESSED ':p
   end else
      res = 'CANCEL ':p
   end
   screen get f, 'vp' returning s
   crt @(0, 40) : 'LOG ' : convert(@vm, ',', s) : ' ' : res
end
"""

# A viewport that needs one bar only: VERT is taller than its window and not wider, HORZ the other way round.  Form at 1,1; viewport at 2,2 of it:
# corner (3,3), 30 by 8, inside from (4,4), 28 by 6 (columns 4-31, rows 4-9).  A label at the sheet's last row but one.
def one_bar(cw, ch):
    return OPEN + """   screen form title 'One bar' at 1,1 size 60,20 returning f
   screen viewport f, 'vp' at 2,2 size 30,8 content %d,%d title 'Sheet'
   screen in f, 'vp'
   screen label f, 'a', 'FIRSTROW' at 0,0
   screen label f, 'b', 'ROW5' at 0,5
   screen in f, ''
   screen run f returning p else p = 0
end
""" % (cw, ch)


PROGS = {
    "zzvpver": one_bar(20, 20),
    "zzvphor": one_bar(60, 4),
    "zzvpcur": CUR,
    "zzvpcon": CON,
    "zzvpnst": NST,
    "zzvpeq1": eq_program(False),
    "zzvpeq2": eq_program(True),
    "zzvpscr": VPS,
    "zzvpstr": VPS_START,
    "zzvpflt": VPS_FLAT,
    "zzvpwid": WID,
    "zzvpnvp": NVP,
    "zzvpbad": BADS,
    "zzvpbig": BIG,
}


# ------------------------------------------------------------------------------------------------------------------------------
# The parts
# ------------------------------------------------------------------------------------------------------------------------------

def part_stmt(box):
    say("\n--- the statements: what is refused, and the viewport of a form that is not on the screen ---------------------")
    t = term(box, "zzvpbad")
    L = t.keys()
    b = sbs.result(L, "BAD ")
    row("a SCREEN IN naming nothing, a label, a SCREEN MOVE with a size for a label or a sheet for a container, a MOVE and a SCROLL of "
        "nothing, a SCROLL of a container, a DELETE of nothing, and a form that is not one: each takes its ELSE",
        b == "NOIN LABELIN NOSIZE NOCONTENT NOMOVE NOSCROLL NOSCROLL2 NODEL NOFORM|", repr(b))
    g = sbs.result(L, "GOOD ")
    row("control: a viewport of a form that was never shown scrolls (to 7,9, kept inside its sheet), SCREEN GET answers where it is, and "
        "DELETE of an empty container says it took out one",
        g == "7,9|7,9|1|", repr(g))
    t.end()


def part_con(box):
    say("\n--- a container: its children, the clip at its edges, and move / hide / disable / delete ---------------------")
    t = term(box, "zzvpcon")
    L = t.keys()
    # corner (5,4), inside from (6,5), 28 by 6: columns 6-33, rows 5-10; the border is column 5 and 34, rows 4 and 11
    row("control: the form is up with its own labels (one before the container, one after it)", at(L, 2, 3, "TOPLABEL") and at(L, 4, 41, "OUTSIDE"),
        "\n".join(L[1:12]))
    row("the container draws its border with the title in the top border", at(L, 4, 5, "+- Box -") and L[4][34] == "+" and L[11][5] == "+", "\n".join(L[3:13]))
    row("a child's x,y count from the first cell inside the border: CHILD-ONE is at the inside's top left, (6,5)", at(L, 5, 6, "CHILD-ONE"), repr(L[5][:40]))
    row("a child wider than the inside is cut at the inside's right edge (28 cells), and the border to its right is whole",
        at(L, 6, 6, "ABCDEFGHIJKLMNOPQRSTUVWXYZ01") and L[6][34] == "|" and "2345" not in L[6], repr(L[6][:50]))
    row("a child below the inside is not drawn, and the bottom border is whole",
        not has(L, "BELOWINNER") and L[11][5:35] == "+" + "-" * 28 + "+", repr(L[11][:40]))
    row("a child that starts inside and runs past the right edge is cut there: RI shows, the border is whole, nothing of GHTEDGE anywhere",
        at(L, 7, 32, "RI") and L[7][34] == "|" and not has(L, "GHTEDGE"), repr(L[7][:40]))
    row("a child that starts left of the inside is cut at its left edge: TCUT shows from column 6, columns 3-4 are blank, the border is whole",
        at(L, 10, 6, "TCUT") and blank(L, 10, 3, 5) and L[10][5] == "|" and not has(L, "LEFT"), repr(L[10][:40]))
    row("a child above the inside is not drawn, and the row over the border has nothing on it", not has(L, "ABOVE") and blank(L, 3, 3, 60), repr(L[3][:60]))
    row("an entry and a button inside it are drawn where they were put", at(L, 8, 6, "abc") and at(L, 9, 6, "[ Go ]"), "\n".join(L[7:11]))

    L = t.keys(F2)
    # moved to 30,12 of the form: corner (31,13), inside from (32,14)
    row("SCREEN MOVE: the container and its children are at the new place (title at its corner, CHILD-ONE at the inside's top left)",
        at(L, 13, 31, "+- Box -") and at(L, 14, 32, "CHILD-ONE") and at(L, 17, 32, "abc") and at(L, 18, 32, "[ Go ]"), "\n".join(L[12:21]))
    row("...they are cut at the new edges just as before (c2 to 28 cells and a whole border, no BELOWINNER)",
        at(L, 15, 32, "ABCDEFGHIJKLMNOPQRSTUVWXYZ01") and L[15][60] == "|" and not has(L, "BELOWINNER") and not has(L, "ABOVE"), "\n".join(L[13:22]))
    row("...and the old place is blank: nothing of the box is left in columns 3-36, rows 4-11 (the form was drawn again)", blank_rect(L, 4, 11, 3, 36),
        "\n".join(L[3:13]))
    row("...the widgets that are not in it did not move", at(L, 2, 3, "TOPLABEL") and at(L, 4, 41, "OUTSIDE"), "\n".join(L[1:6]))

    L = t.keys(F3)
    row("SCREEN SET VISIBLE 0 on the container hides it and everything in it: no border, no CHILD-ONE, no entry, no button; the place is blank",
        at(L, 1, 1, "+- Container") and at(L, 2, 3, "TOPLABEL") and not has(L, "CHILD-ONE") and not has(L, "[ Go ]") and not has(L, "abc") and blank_rect(L, 13, 22, 31, 61),
        "\n".join(L[12:23]))
    t.keys(TAB)
    L = t.keys(F4)
    row("VISIBLE 1 brings it all back", at(L, 13, 31, "+- Box -") and at(L, 14, 32, "CHILD-ONE") and at(L, 18, 32, "[ Go ]"), "\n".join(L[12:21]))
    t.keys(BTAB)
    t.keys(TAB)
    L = t.keys(F5)
    row("SET ENABLED 0 on the container: its children are still drawn", at(L, 14, 32, "CHILD-ONE") and at(L, 17, 32, "abc"), "\n".join(L[12:21]))
    t.keys(TAB)
    t.keys(BTAB)
    click(t, 33, 17)
    t.keys(F6)
    click(t, 33, 17)
    L = t.keys(F7)
    row("SCREEN DELETE takes the container and all eight children out (it says 9) and the form shows nothing of them",
        blank_rect(L, 13, 22, 31, 61) and has(L, "TOPLABEL") and has(L, "OUTSIDE"), "\n".join(L[12:23]))
    L = finish(t)
    lg = logline(L)
    row("the focus: hidden children are skipped by Tab (oe), come back when shown (cb, oe), a disabled container's are skipped by Tab and Shift-Tab and "
        "cannot be clicked, enabled again one can (ce); the delete said 9 and the child was gone (SCREEN GET: ELSE)",
        lg == "F:oe F:cb F:oe F:ce DEL:9 GONE", repr(lg))
    t.end()


def part_nst(box):
    say("\n--- containers in a container -----------------------------------------------------------------------------")
    t = term(box, "zzvpnst")
    L = t.keys()
    # outer: corner (3,3), inside from (4,4), columns 4-41 and rows 4-15 (border column 42, row 16).  Inner: corner (24,8), inside from (25,9).
    row("control: the outer container is drawn with a title and the label in it", at(L, 3, 3, "+- Outer -") and at(L, 4, 4, "OUTERLBL"), "\n".join(L[2:6]))
    row("a container in a container is placed from the outer one's inside: its border starts at (24,8)", at(L, 8, 24, "+- Inner -"), repr(L[8][20:60]))
    row("...and is cut at the OUTER container's edge: its top border stops at column 41 and the outer's border (|) is column 42",
        L[8][41] == "-" and L[8][42] == "|" and "+" not in L[8][43:60], repr(L[8][20:60]))
    row("a child of the inner one is placed from the inner one's inside, (25,9), (25,10)", at(L, 9, 25, "DEEPLABEL") and at(L, 10, 25, "deep"), "\n".join(L[8:13]))
    row("...and cut at the outer's edge, not only the inner's (which is 6 columns further): 17 cells of the long label, then the outer border",
        at(L, 11, 25, "ABCDEFGHIJKLMNOPQ") and L[11][42] == "|" and "RSTU" not in L[11], repr(L[11][20:60]))
    row("the outer container's border is whole all the way down its right side and along the bottom (nothing drawn over it)",
        all(L[r][42] == "|" for r in range(4, 16)) and L[16][3:43] == "+" + "-" * 38 + "+", "\n".join(L[14:18]))

    L = t.keys(F2)
    # outer to 20,5: corner (21,6), inside from (22,7); inner corner (42,11), inside (43,12)
    row("SCREEN MOVE of the outer one moves the inner one and what is in it with it: OUTERLBL at (22,7), the inner border at (42,11), DEEPLABEL at (43,12)",
        at(L, 7, 22, "OUTERLBL") and at(L, 11, 42, "+- Inner -") and at(L, 12, 43, "DEEPLABEL") and at(L, 13, 43, "deep"), "\n".join(L[5:20]))
    row("...and the old place is blank (columns 3-20, rows 3-16)", blank_rect(L, 3, 16, 3, 20), "\n".join(L[2:18]))
    L = t.keys(F3)
    row("hiding the outer one hides the inner one and all in it (nothing of DEEPLABEL, deep, OUTERLBL, either border)",
        not has(L, "DEEPLABEL") and not has(L, "deep") and not has(L, "OUTERLBL") and not has(L, "Inner") and not has(L, "Outer") and at(L, 1, 1, "+- Nested") and at(L, 4, 51, "zz"), "\n".join(L[3:20]))
    t.keys(TAB)
    t.keys(F4)
    t.keys(BTAB)
    t.keys(TAB)
    t.keys(F5)
    t.keys(TAB)
    t.keys(BTAB)
    click(t, 44, 13)
    t.keys(F6)
    click(t, 44, 13)
    L = t.keys(F7)
    row("SCREEN DELETE of the outer one takes both containers and everything in them (six) and leaves the form's own widget",
        not has(L, "DEEPLABEL") and not has(L, "OUTERLBL") and has(L, "zz") and blank_rect(L, 6, 19, 21, 60), "\n".join(L[3:20]))
    L = finish(t)
    lg = logline(L)
    row("the focus: the deep entry is skipped while the outer container is hidden or disabled (no click, no Tab), reached again when it is enabled; the "
        "delete said 6", lg == "F:oe F:de F:oe F:de DEL:6 GONE", repr(lg))
    t.end()


def part_eq(box):
    say("\n--- control: widgets in a borderless container are the widgets in the form --------------------------------------")
    out = []
    for prog in ("zzvpeq1", "zzvpeq2"):
        t = term(box, prog)
        L0 = t.keys()
        a0 = [t.attrs(r) for r in range(ROWS)]
        L1 = t.keys(TAB, DOWN, "x", " ", idle=0.4)
        a1 = [t.attrs(r) for r in range(ROWS)]
        L2 = finish(t)
        out.append((L0, a0, L1, a1, L2))
        t.end()
    row("setup: both draw a label, an entry, a check box, a list and a button, and a log line comes back",
        has(out[0][0], "ALPHA") and has(out[0][0], "bravo") and has(out[0][0], "[ Echo ]") and logline(out[0][4]) is not None, "\n".join(out[0][0][2:14]))
    row("the screen is the same, cell for cell and in the same attributes, before any key", out[0][0] == out[1][0] and out[0][1] == out[1][1],
        repr([i for i in range(ROWS) if out[0][0][i] != out[1][0][i]]))
    row("...after Tab, Down, a letter typed and a space", out[0][2] == out[1][2] and out[0][3] == out[1][3],
        repr([i for i in range(ROWS) if out[0][2][i] != out[1][2][i]]))
    row("...and the values the program got back are the same", logline(out[0][4]) == logline(out[1][4]), repr((logline(out[0][4]), logline(out[1][4]))))


# The viewport VPS: window columns 4-40, rows 4-14; vertical bar column 41 (rows 4-14); horizontal bar row 15 (columns 4-40); border column 42, row 16.
WX0, WX1, WY0, WY1 = 4, 40, 4, 14
BARC, BARR = 41, 15
RECT = (3, 16, 3, 42)                       # rows 3-16, columns 3-42: the viewport with its border and bars


def vbar(L):
    return "".join(L[r][BARC] for r in range(WY0, WY1 + 1))


def hbar(L):
    return L[BARR][WX0:WX1 + 1]


def thumb(bar):
    """(first cell, length) of the # run in a bar string, None if there is none or more than one run."""
    runs = re.findall(r"#+", bar)
    if len(runs) != 1:
        return None
    return bar.index("#"), len(runs[0])


def pos(t):
    """The scroll place the program prints for F9: (sx, sy), and the screen."""
    L = t.keys("\x1b[20~")
    p = sbs.result(L, "POS ")
    try:
        sx, sy = [int(v) for v in p.split(",")]
    except (AttributeError, ValueError):
        return None, L
    return (sx, sy), L


def part_scroll(box):
    say("\n--- a viewport: the window, the bars, the keys, and the clip at all four edges ----------------------------------")
    t = term(box, "zzvpscr")
    L = t.keys()
    row("control: the form is up (the entry before the viewport, the label after it)", at(L, 22, 6, "UNDER") and at(L, 19, 3, "TAILLABEL"), "\n".join(L[19:24]))
    row("the sheet's top left is in the window's top left: R00C0 at (4,4); the label at x=30 is whole (R00C3 at 34-38), the one at x=40 is not there",
        at(L, 4, 4, "R00C0") and at(L, 4, 34, "R00C3") and not has(L, "R00C4"), repr(L[4][:50]))
    row("the window is 37 by 11: the label at y=8 shows (row 12), the one at y=12 does not (it would be row 16, the border)",
        at(L, 12, 4, "R02C0") and not has(L, "R03C0"), "\n".join(L[3:18]))
    row("the border is whole: top and bottom rows and the right column (column 42), the left column (3)",
        L[3][3:43] == "+- Sheet " + "-" * 30 + "+" and L[16][3:43] == "+" + "-" * 38 + "+" and all(L[r][42] == "|" and L[r][3] == "|" for r in range(4, 16)),
        "\n".join(L[3:17]))
    vb, hb = vbar(L), hbar(L)
    row("both bars are there, each from its arrow to its arrow with the thumb right under the first: ^#||...|v and <#---...->, and the corner is blank",
        vb[0] == "^" and vb[-1] == "v" and thumb(vb) and thumb(vb)[0] == 1 and hb[0] == "<" and hb[-1] == ">" and thumb(hb) and thumb(hb)[0] == 1 and L[BARR][BARC] == " ",
        repr((vb, hb, L[BARR][BARC])))
    o0 = outside(L, *RECT)

    t.keys(TAB)
    L = t.keys(DOWN, DOWN, DOWN)
    row("Down x3 with the viewport focused: the sheet moves 3 rows (R01C0, y=4, is now at row 5; R00C0 is gone) and the thumb has moved down",
        at(L, 5, 4, "R01C0") and not has(L, "R00C0") and thumb(vbar(L)) and thumb(vbar(L))[0] > 1, "\n".join(L[3:10]))
    L = t.keys(RIGHT, RIGHT, RIGHT, RIGHT)
    row("Right x4: the sheet moves 4 columns - the label at x=0 is cut at the window's left edge (only its last cell, the 0, shows) and the border is whole; "
        "R01C1 (x=10) is at column 10", at(L, 5, 3, "|0") and L[5][5:10] == "     " and at(L, 5, 10, "R01C1"), repr(L[5][:50]))
    row("...the label at x=40 is cut at the RIGHT edge: one cell (R) shows at column 40, the bar is whole at column 41",
        L[5][40] == "R" and L[5][41] in "|#" and "C4" not in L[5], repr(L[5][30:50]))
    t.keys(PGDN)
    t.keys(PGUP)
    t.keys(HOME)
    L = t.keys(END)
    row("End goes to the bottom of the sheet (the first row shown is y=29): R08C1 (y=32, x=10, the sheet is 4 columns along) is at row 7 and R07C1 (y=28) is gone",
        at(L, 7, 10, "R08C1") and not has(L, "R07C1"), "\n".join(L[3:16]))
    t.keys(F2)
    t.keys(F3)
    L = t.keys(F4)
    row("SCREEN SCROLL TO 999,999 stops at the sheet's far corner (43,29) and shows it: R09C7 (x=70, y=36) is at column 31, row 11; the thumbs are at the ends",
        at(L, 11, 31, "R09C7") and thumb(vbar(L)) and thumb(vbar(L))[0] + thumb(vbar(L))[1] == len(vbar(L)) - 1 and thumb(hbar(L)) and thumb(hbar(L))[0] + thumb(hbar(L))[1] == len(hbar(L)) - 1,
        "\n".join(L[3:17]))
    t.keys("f")
    L = t.keys("a")
    row("TO 3,0: the label at the left edge is cut to its last two cells: C0 at column 4, the border whole", at(L, 4, 4, "C0 ") and L[4][3] == "|", repr(L[4][:20]))
    row("...and nothing outside the viewport moved", outside(L, *RECT) == o0, repr([i for i, (x, y) in enumerate(zip(outside(L, *RECT), o0)) if x != y]))
    L = t.keys("c")
    row("TO 6,0: the label at x=40 shows three cells, R00 at columns 38-40, and the vertical bar (its up arrow, in row 4) is whole at column 41",
        at(L, 4, 38, "R00") and L[4][41] == "^", repr(L[4][30:50]))
    L = t.keys("d")
    row("TO 30,0: the list (x=56, three rows at y=9-11) is cut by the BOTTOM edge: alpha and beta show, gamma does not, row 15 is the horizontal bar",
        at(L, 13, 30, ">alpha") and at(L, 14, 31, "beta") and not has(L, "gamma") and set(L[15][4:41]) <= set("<>#-"), "\n".join(L[11:17]))
    L = t.keys("e")
    row("TO 30,10: ...and by the TOP edge: alpha (y=9) is above the window, beta and gamma are the first two rows", at(L, 4, 31, "beta") and at(L, 5, 31, "gamma") and not has(L, "alpha"),
        "\n".join(L[3:8]))
    L = t.keys("b")
    row("TO 0,2: the rows above y=2 are gone, R01C0 (y=4) is at row 6", at(L, 6, 4, "R01C0") and not has(L, "R00C0"), "\n".join(L[3:8]))
    row("...and through all of it nothing outside the viewport's rectangle changed (the labels, the entry before it, the entry after it)",
        outside(L, *RECT) == o0, repr([i for i, (x, y) in enumerate(zip(outside(L, *RECT), o0)) if x != y]))
    L = finish(t)
    lg = logline(L)
    row("the events: a change with the viewport's id and where it is, for every key that moved it; a SCREEN SCROLL from the program is not an event, "
        "it answers where it went (and TO 999,999 was kept inside the sheet)",
        lg == "F:vp C:vp=0,1 C:vp=0,2 C:vp=0,3 C:vp=1,3 C:vp=2,3 C:vp=3,3 C:vp=4,3 C:vp=4,13 C:vp=4,3 C:vp=4,0 C:vp=4,29 S:5,7 S:7,9 S:43,29",
        repr(lg))
    row("the end: SCREEN GET answered the place the sheet was left at (0,2)", (L[39].strip() == "VP 0,2") if len(L) > 39 else False, repr(L[39:41]))
    t.end()


def part_wheel(box):
    say("\n--- the wheel, and Shift-wheel --------------------------------------------------------------------------------")
    t = term(box, "zzvpscr")
    t.keys()
    t.keys(TAB)
    L = wheel(t, 10, 8)
    row("the wheel over the sheet (on a label, which takes no focus) scrolls it 3 rows: R01C0 (y=4) is at row 5, and R00C0 is gone",
        at(L, 5, 4, "R01C0") and not has(L, "R00C0"), "\n".join(L[3:9]))
    L = wheel(t, 10, 8, shift=True)
    row("Shift-wheel scrolls 3 columns: R01C1 (x=10) is at column 11 (and the label at x=0 is cut to C0)", at(L, 5, 11, "R01C1") and at(L, 5, 4, "C0"), repr(L[5][:30]))
    wheel(t, 10, 8, up=True)
    L = wheel(t, 10, 8, up=True, shift=True)
    row("wheel up and Shift-wheel up undo them: the sheet is at the corner again", at(L, 4, 4, "R00C0"), repr(L[4][:30]))
    L = wheel(t, 10, 8, up=True)
    row("control: another wheel up at the top changes nothing (the sheet does not go past its edge)", at(L, 4, 4, "R00C0"), repr(L[4][:30]))
    L = wheel(t, 8, 5)
    row("the wheel over an entry that is in the viewport scrolls the viewport, not the entry", at(L, 5, 4, "R01C0") and not has(L, "R00C0"), "\n".join(L[3:9]))
    L = t.keys(DOWN)
    row("...and the focus did not move to the entry: Down still scrolls the viewport (one more row: R01C0 is at row 4), it does not go to the next widget",
        at(L, 4, 4, "R01C0"), "\n".join(L[3:9]))
    t.keys("d")
    wheel(t, 32, 13)
    wheel(t, 51, 4)
    L = finish(t)
    lg = logline(L)
    row("the log: the wheel over the sheet and over the entry are changes of the viewport and no focus change; the wheel over the list (which scrolls "
        "itself) goes to the list and the focus with it; the wheel outside the viewport is not the viewport's",
        lg == "F:vp C:vp=0,3 C:vp=3,3 C:vp=3,0 C:vp=0,0 C:vp=0,3 C:vp=0,4 F:lst F:oe", repr(lg))
    t.end()


def part_bars(box):
    say("\n--- the scroll bars: arrows, track, thumb, and dragging the thumb (PLAN-4) ------------------------------------")
    t = term(box, "zzvpscr")
    t.keys()
    t.keys(TAB)
    click(t, BARC, WY1)
    click(t, BARC, WY1)
    click(t, BARC, WY0)
    L = click(t, WX0, BARR)
    row("the vertical bar's arrows: down, down, up is 1 row (R01C0, y=4, at row 7; R00C0 gone); the horizontal bar's left arrow at the left edge changes nothing",
        at(L, 7, 4, "R01C0") and not has(L, "R00C0"), "\n".join(L[3:9]))
    click(t, WX1, BARR)
    L = t.lines()
    vb = vbar(L)
    s, n = thumb(vb)
    click(t, BARC, WY0 + s + n)
    L = t.lines()
    vb = vbar(L)
    s, n = thumb(vb)
    click(t, BARC, WY0 + s - 1)
    L = t.lines()
    hb = hbar(L)
    s, n = thumb(hb)
    click(t, WX0 + s + n, BARR)
    L = t.lines()
    hb = hbar(L)
    s, n = thumb(hb)
    click(t, WX0 + s - 1, BARR)
    L = finish(t)
    lg = logline(L)
    row("the bars: the arrows move 1, a click on the track beyond the thumb a page (window less one: 10 rows, 36 columns), either way, on either bar",
        lg == "F:vp C:vp=0,1 C:vp=0,2 C:vp=0,1 C:vp=1,1 C:vp=1,11 C:vp=1,1 C:vp=37,1 C:vp=1,1", repr(lg))
    t.end()

    t = term(box, "zzvpscr")
    t.keys()
    t.keys(TAB)
    L = t.lines()
    vb = vbar(L)
    s, n = thumb(vb)
    press(t, BARC, WY0 + s)
    drag(t, BARC, WY0 + s + 2)
    drag(t, BARC, WY0 + s + 4)
    L = t.lines()
    rows_to = thumb(vbar(L))
    drag(t, 20, WY1 + 3)
    L = t.lines()
    bottom = thumb(vbar(L))
    drag(t, 90, 0)
    L = t.lines()
    release(t, 90, 0)
    t.keys("\x1b[<35;60;10M", idle=0.3)                # the pointer moves with no button: nothing
    L = finish(t)
    lg = logline(L)
    ev = re.findall(r"C:vp=0,(\d+)", lg or "")
    vals = [int(v) for v in ev]
    row("PLAN-4: a press on the thumb and the pointer moved down with the button held: the sheet follows - twice, further each time (the values %s)" % vals[:2],
        len(vals) >= 4 and 0 < vals[0] < vals[1] < 29, repr(lg))
    row("...the thumb moved with it (it is no longer at the top), the pointer past the bottom of the track - and off the bar sideways - takes the sheet "
        "to its end (29), above the top of the screen to its start (0)",
        rows_to is not None and rows_to[0] > 1 and bottom is not None and bottom[0] + bottom[1] == 10 and vals[2:4] == [29, 0], repr((vals, rows_to, bottom)))
    row("...the release ends it: a move with no button held after it changes nothing (no more events), and the focus is the viewport's from the press",
        lg is not None and lg.startswith("F:vp ") and len(vals) == 4, repr(lg))
    t.end()

    t = term(box, "zzvpscr")
    t.keys()
    t.keys(TAB)
    L = t.lines()
    s, n = thumb(hbar(L))
    press(t, WX0 + s, BARR)
    drag(t, WX0 + s + 5, BARR)
    drag(t, WX1 + 4, 40)
    release(t, WX1 + 4, 40)
    L = finish(t)
    lg = logline(L)
    ev = re.findall(r"C:vp=(\d+),0", lg or "")
    vals = [int(v) for v in ev]
    row("a drag of the horizontal bar's thumb: it follows, then to the end of the sheet (43) when the pointer is far past the right end",
        len(vals) == 2 and 0 < vals[0] < 43 and vals[1] == 43, repr(lg))
    t.end()


def part_focus(box):
    say("\n--- the focus: a child scrolls into view, a click outside the visible part hits nothing, the cursor, the combo's list ---")
    t = term(box, "zzvpscr")
    t.keys()
    seq = [("e1", "hello", 2, 1), ("ee", "EDGE", 35, 2), ("e2", "two", 22, 10), ("lst", "alpha", 57, 9), ("cb", "Boston", 12, 14),
           ("bot", "BOT", 2, 18), ("far", "FAR", 61, 33)]
    t.keys(TAB)
    got = {}
    for nm, txt, x, y in seq:
        t.keys(TAB)
        p, L = pos(t)
        got[nm] = p
        ok = p is not None and at(L, WY0 + y - p[1], WX0 + x - p[0], txt) and WX0 <= WX0 + x - p[0] and WX0 + x - p[0] + len(txt) - 1 <= WX1 and WY0 <= WY0 + y - p[1] <= WY1
        row("Tab to %s: it is inside the window (its text %r is at row %s, column %s), the sheet is at %s" % (
            nm, txt, WY0 + y - p[1] if p else "?", WX0 + x - p[0] if p else "?", p), ok, "\n".join(L[3:17]))
    row("...and the sheet moved no further than it had to: e1, ee and e2 are in the first window (rows 0), the list needed 1 row more (it is three high), "
        "cb needed 4, bot 8 and far 23; going left, bot and cb put the entry at the window's left edge",
        [got[k][1] for k in ("e1", "ee", "e2", "lst", "cb", "bot", "far")] == [0, 0, 0, 1, 4, 8, 23] and got["cb"][0] == 12 and got["bot"][0] == 2, repr(got))
    t.keys(BTAB)
    p, L = pos(t)
    row("Shift-Tab back to bot: the window comes back up to it, and the entry is at the top left (sheet place 2,18)", p == (2, 18) and at(L, WY0, WX0, "BOT"), repr(p))
    t.end()

    t = term(box, "zzvpstr")
    t.keys()
    p, L = pos(t)
    row("SCREEN FOCUS on a child that is out of view before the form is shown: the first draw has the sheet scrolled to it (FAR in the window)",
        p is not None and p[1] == 23 and at(L, WY0 + 33 - p[1], WX0 + 61 - p[0], "FAR"), repr((p, L[3:17])))
    t.end()

    t = term(box, "zzvpscr")
    t.keys()
    t.keys(TAB)
    click(t, 7, 22)                                        # where bot would be if it were not cut: the entry before the viewport is there
    click(t, BARC, 6)                                      # the bar, on the row where the entry 'ee' would run on
    click(t, 42, 6)                                        # the border, ditto
    click(t, 65, 37)                                       # where 'far' would be, cut away altogether: nothing
    L = finish(t)
    lg = logline(L)
    row("a click outside the visible part of a child hits nothing of that child: on the cell where 'bot' (cut away by the bottom edge) would be, the entry "
        "before the viewport takes it (not bot); on the bar (the thumb: a drag starts) or the border, where the entry 'ee' would run on, the viewport "
        "does (not ee); on the place of 'far' (cut away altogether) nothing", lg == "F:vp F:under F:vp", repr(lg))
    t.end()

    t = term(box, "zzvpscr")
    t.keys()
    t.keys(TAB)
    L = click(t, 39, 6)
    p, L = pos(t)
    row("a click on the part of 'ee' that shows (2 of its cells) gives it the focus, and the sheet is scrolled so that it is whole",
        p is not None and p[0] > 0 and at(L, WY0 + 2 - p[1], WX0 + 35 - p[0], "EDGE"), repr((p, L[5:8])))
    L = finish(t)
    row("...as the focus change F:ee", logline(L) == "F:vp F:ee", repr(logline(L)))
    t.end()

    # PLAN-2: the hardware cursor of a widget that is scrolled away.  A modal SCREEN RUN, because a SCREEN WAIT that has returned an event gives
    # the cursor back to the program (the library's own place, (0,0)) and the entry's place is only meaningful while the form has the keys.
    # The viewport is at 2,3 of a form at 2,1: corner (4,4), inside from (5,5), 18 by 6, window 17 by 5 (bars); e1 at 2,3 of the sheet, so at (7,8).
    t = term(box, "zzvpcur")
    t.keys()
    t.keys(TAB)
    t.keys(TAB)
    row("PLAN-2: the entry in view has the cursor where its text ends: visible, at row 8, column 12", t.cursor_visible() and t.cursor() == (12, 8), repr((t.cursor(), t.cursor_visible())))
    wheel(t, 10, 7)
    row("...the wheel moves the sheet 3 rows and the entry with it (focus unchanged): the cursor is still on its text, row 5", t.cursor_visible() and t.cursor() == (12, 5),
        repr((t.cursor(), t.cursor_visible())))
    wheel(t, 10, 7)
    row("...scrolled out of the window altogether the cursor is hidden - it is not left on whatever is at the place", not t.cursor_visible(), repr((t.cursor(), t.cursor_visible())))
    wheel(t, 10, 7, up=True)
    row("...and back in view it is shown again, on the text", t.cursor_visible() and t.cursor() == (12, 5), repr((t.cursor(), t.cursor_visible())))
    wheel(t, 10, 7, shift=True)
    row("...scrolled 3 columns the entry is cut by the left edge (its first cells are gone): the cursor is hidden",
        not t.cursor_visible(), repr((t.cursor(), t.cursor_visible())))
    wheel(t, 10, 7, up=True, shift=True)
    row("...and shown again when the entry is whole", t.cursor_visible() and t.cursor() == (12, 5), repr((t.cursor(), t.cursor_visible())))
    t.keys(TAB)
    p, L = None, t.lines()
    row("Tab to the entry that is cut away (far): the sheet scrolls to it and the cursor is shown, after its text", t.cursor_visible() and at(L, t.cursor()[1], t.cursor()[0] - 3, "FAR"),
        repr((t.cursor(), t.cursor_visible())))
    t.keys(BTAB)
    t.keys(BTAB)
    row("the viewport itself has the focus: no cursor (it takes no text)", not t.cursor_visible(), repr((t.cursor(), t.cursor_visible())))
    t.keys(ESC)
    t.end()

    # PLAN-1: a pop-up list of a combo box is not cut by the viewport it is in
    t = term(box, "zzvpscr")
    t.keys()
    for _ in range(6):
        t.keys(TAB)
    p, L0 = pos(t)
    row("setup: the combo box is in view (row 14, column 4, sheet at 12,4)", p == (12, 4) and at(L0, 14, 4, "Boston"), repr((p, L0[13:15])))
    L1 = t.keys(DOWN)
    row("PLAN-1: Down opens its list under the field, and the list is NOT cut at the viewport's edge: its frame covers the horizontal bar's row (15) and the "
        "border's row (16), and the three choices are in rows 16-18",
        at(L1, 15, 4, "+") and at(L1, 16, 6, "Albany") and at(L1, 17, 6, "Boston") and at(L1, 18, 6, "Chicago") and at(L1, 19, 4, "+"), "\n".join(L1[13:21]))
    L2 = t.keys(ESC)
    row("Esc closes the list and the screen is put back exactly as it was (the bar and the border under the list included)", L2[:38] == L0[:38],
        repr([i for i in range(38) if L2[i] != L0[i]]))
    t.keys(DOWN)
    t.keys(DOWN)
    L3 = t.keys(RET)
    row("a choice made in the list is the combo's value, shown in its field (the list's text is where the field is cut by the viewport, not its own)",
        at(L3, 14, 4, "Chicago") and not has(L3, "Albany"), "\n".join(L3[13:20]))
    L = finish(t)
    row("...and a change event with the new value", "C:cb=Chicago" in (logline(L) or ""), repr(logline(L)))
    t.end()


def part_wid(box):
    say("\n--- PLAN-3: widgets that draw a lot (memo, table) in a viewport smaller than they are --------------------------")
    # the viewport at 2,2 of the form at 1,1: corner (3,3), 30 by 10 -> columns 3-32, rows 3-12; inside from (4,4), window 27 by 7 (bars)
    r = (3, 12, 3, 32)
    t = term(box, "zzvpwid")
    L = t.keys()
    o0 = outside(L, *r)
    row("control: the memo (14 rows high) and the table are drawn in the window only: line1 is there, line8 (row 11) would be in the horizontal bar's row and "
        "line12 outside the border - neither is", at(L, 4, 4, "line1") and not has(L, "line8") and not has(L, "line12") and has(L, "OUTSIDE-LABEL"), "\n".join(L[2:20]))
    row("...the border is whole (top, bottom, both sides) and nothing is drawn under the form's window rectangle below it",
        L[3][3:33] == "+- Sheet " + "-" * 20 + "+" and L[12][3:33] == "+" + "-" * 28 + "+" and all(L[q][3] == "|" and L[q][32] == "|" for q in range(4, 12)) and blank_rect(L, 13, 19, 3, 60),
        "\n".join(L[2:24]))
    t.keys(TAB)
    row("the memo has the focus; it is taller than the window, so the cursor is hidden (the plan's rule: a widget not wholly in view has no cursor)", not t.cursor_visible(),
        repr((t.cursor(), t.cursor_visible())))
    L = t.keys("XYZ", RET, RET, RET)
    row("typing in the memo (it redraws all its 14 rows each time) draws nothing outside the viewport", outside(L, *r) == o0,
        repr([(i, outside(L, *r)[i]) for i in range(len(L)) if outside(L, *r)[i] != o0[i]][:3]))
    L = t.keys(*([DOWN] * 12), PGDN)
    row("...nor does moving the cursor down it (the memo scrolls itself), a page at a time", outside(L, *r) == o0,
        repr([(i, outside(L, *r)[i]) for i in range(len(L)) if outside(L, *r)[i] != o0[i]][:3]))
    row("...and the viewport's border is whole after all that", L[3][3:33] == "+- Sheet " + "-" * 20 + "+" and L[12][3:33] == "+" + "-" * 28 + "+" and
        all(L[q][3] == "|" and L[q][32] == "|" for q in range(4, 12)), "\n".join(L[2:14]))
    t.keys(TAB)
    L = t.keys(*([DOWN] * 6), END)
    row("the table (10 rows high, 24 wide, cut by the right edge) scrolls itself with the keys and draws nothing outside either",
        outside(L, *r) == o0, repr([(i, outside(L, *r)[i]) for i in range(len(L)) if outside(L, *r)[i] != o0[i]][:3]))
    L = finish(t)
    lg = logline(L)
    row("the log: the focus went memo, table; the memo took the letters and the 3 returns (80 characters, 6 more than it had)",
        lg is not None and lg.startswith("F:m F:t") and lg.endswith("MEMO 80"), repr(lg))
    t.end()


def part_nvp(box):
    say("\n--- viewports in a viewport -----------------------------------------------------------------------------------")
    # outer: corner (3,3), 50 by 20, inside from (4,4): window columns 4-50 (bar column 51), rows 4-20 (bar row 21); border column 52, row 22.
    # inner: at 10,10 of the outer's sheet: corner (14,14), 30 by 10, inside from (15,15): window columns 15-41 (bar 42), rows 15-21 (bar 22) - but the
    # outer's window stops at row 20, so the inner one is cut there
    t = term(box, "zzvpnvp")
    L = t.keys()
    row("control: the outer's sheet origin has OUTER-TOP; the inner viewport is in it with its title and its own sheet origin (INNER-TOP at (15,15))",
        at(L, 4, 4, "OUTER-TOP") and at(L, 14, 14, "+- Inner -") and at(L, 15, 15, "INNER-TOP"), "\n".join(L[3:24]))
    row("the inner one runs past the bottom of the outer one's window and is cut there: the outer's horizontal bar (row 21) and its border (row 22) are "
        "whole, nothing of the inner one's bar or border is in them",
        set(L[21][4:51]) <= set("<>#-") and L[22][3:53] == "+" + "-" * 48 + "+" and L[21][51] == " " and blank_rect(L, 23, 29, 4, 60), "\n".join(L[19:31]))
    L = wheel(t, 20, 17)
    row("the wheel over the INNER viewport scrolls it (3 rows: INNER-TOP is gone) and not the outer one (OUTER-TOP is still there)",
        not has(L, "INNER-TOP") and at(L, 4, 4, "OUTER-TOP"), "\n".join(L[3:20]))
    L = wheel(t, 8, 8)
    row("the wheel over the outer one outside the inner one scrolls the outer one: OUTER-TOP is gone and the inner viewport has moved up 3 rows (its title at row 11)",
        not has(L, "OUTER-TOP") and at(L, 11, 14, "+- Inner -"), "\n".join(L[3:20]))
    wheel(t, 8, 8, up=True)
    t.keys(TAB)
    t.keys(TAB)
    L = t.keys("\x1b[20~")
    pp = sbs.result(L, "POS ")
    m = re.match(r"(\d+),(\d+) (\d+),(\d+)$", pp or "")
    if m:
        osx, osy, isx, isy = [int(v) for v in m.groups()]
        icol = 4 + 10 - osx + 1 + 40 - isx
        irow = 4 + 10 - osy + 1 + 30 - isy
    row("Tab to the entry deep in the inner sheet scrolls the inner viewport to it (and the outer one if that is what it takes): 'deepin' is in view",
        m is not None and at(L, irow, icol, "deepin") and 15 <= icol <= 41 and 15 <= irow <= 20, repr((pp, L[12:24])))
    t.keys(TAB)
    L = t.keys("\x1b[20~")
    pp = sbs.result(L, "POS ")
    m = re.match(r"(\d+),(\d+) (\d+),(\d+)$", pp or "")
    osx = osy = 0
    if m:
        osx, osy, isx, isy = [int(v) for v in m.groups()]
    row("Tab to the entry at the far corner of the outer sheet: the outer viewport scrolls to it ('outerin' at column %s, row %s)" % (4 + 70 - (osx if m else 0), 4 + 50 - (osy if m else 0)),
        m is not None and at(L, 4 + 50 - osy, 4 + 70 - osx, "outerin"), repr((pp, L[3:24])))
    L = finish(t)
    lg = logline(L)
    row("the log: the two wheels (and the wheel up) are changes of the viewport they were over, the Tabs are focus changes (the scrolls the focus caused are "
        "not events of their own)", lg is not None and lg.startswith("C:iv=0,3 C:ov=0,3 C:ov=0,0 F:iv F:ie F:oe"), repr(lg))
    t.end()


def part_vpops(box):
    say("\n--- a viewport: move, hide, disable, delete, one with no sheet to scroll -----------------------------------------")
    t = term(box, "zzvpscr")
    t.keys()
    t.keys(TAB)
    t.keys(F2)
    L = t.keys(F5)
    # moved to 30,12: corner (31,13), inside from (32,14); scrolled to 5,7 before
    row("SCREEN MOVE of a viewport that has been scrolled (5,7): it keeps its place in the sheet and its children go with it - R02C1 (x=10, y=8) is at column 37, row 15",
        at(L, 15, 37, "R02C1") and at(L, 13, 31, "+- Sheet "), "\n".join(L[12:30]))
    row("...the old place is blank (columns 3-30, rows 3-16)", blank_rect(L, 3, 16, 3, 30), "\n".join(L[2:18]))
    L = t.keys(F6)
    row("SET VISIBLE 0: the viewport and all its sheet disappear, bars included", not has(L, "R0") and not has(L, "Sheet") and has(L, "TAILLABEL"), "\n".join(L[2:30]))
    L = t.keys(F7)
    L = finish(t)
    lg = logline(L)
    row("SCREEN DELETE of the viewport takes it and its 87 children (it says 88); SCREEN GET of it is then refused", lg == "F:vp S:5,7 DEL:88" and L[39].strip() == "VP GONE",
        repr((lg, L[39:41])))
    t.end()

    t = term(box, "zzvpscr")
    t.keys()
    t.keys(TAB)
    t.keys(F8)
    wheel(t, 10, 8)
    click(t, 6, 5)
    t.keys(TAB)
    L = finish(t)
    lg = logline(L)
    row("a disabled viewport takes no wheel, and its children take no click: the log has the focus on the viewport from before, then the Tab that "
        "leaves it for the next widget that can have the focus (oe) - not for a child of it", lg == "F:vp F:oe", repr(lg))
    t.end()

    t = term(box, "zzvpver")
    L = t.keys()
    vb = "".join(L[r][31] for r in range(4, 10))
    row("a sheet taller than the window and not wider has the vertical bar only: the window is 28 by 6 (ROW5, the sixth row, is in row 9 with nothing "
        "covering it), the bar is in column 31, the right border column 32", at(L, 9, 4, "ROW5") and vb[0] == "^" and vb[-1] == "v" and L[9][3] == "|" and L[10][3:33] == "+" + "-" * 28 + "+",
        repr(vb) + "\n" + "\n".join(L[3:11]))
    t.keys(ESC)
    t.end()
    t = term(box, "zzvphor")
    L = t.keys()
    hb = L[9][4:32]
    row("...and wider and not higher has the horizontal bar only: it takes the last row of the inside (row 9: <#---...->, ROW5 which would be there is "
        "not), the window is 5 rows", hb[0] == "<" and hb[-1] == ">" and not has(L, "ROW5") and L[4][31] == " ", repr(hb) + "\n" + "\n".join(L[3:11]))
    t.keys(ESC)
    t.end()

    t = term(box, "zzvpflt")
    L = t.keys()
    row("a viewport whose sheet is no larger than its window (the default) has no bars: ONE and TWO are in it (the first and the last row of the "
        "inside), the column before the border is blank and the border row is whole", at(L, 4, 4, "ONE") and at(L, 9, 4, "TWO") and L[4][31] == " " and
        L[4][32] == "|" and L[10][3:33] == "+" + "-" * 28 + "+", "\n".join(L[2:13]))
    wheel(t, 10, 6)
    t.keys(DOWN)
    t.keys(RIGHT)
    L = finish(t)
    row("...and nothing scrolls it: no event for the wheel or the keys, and the view is as it was", logline(L) == "" and at(L, 4, 4, "ONE"), repr(logline(L)))
    t.end()


def timed(t, data, quiet=0.3, limit=30.0):
    """Send DATA and return the seconds until the program stopped writing (the time of its last byte, not the quiet wait after it)."""
    s = t.s
    t0 = time.time()
    s.type(data, settle=False)
    last = t0
    while time.time() < t0 + limit and not s.exited:
        got = s._pump(0.02)
        now = time.time()
        if got:
            last = now
        elif now - last >= quiet:
            break
    return last - t0


def part_big(box):
    say("\n--- 200 by 60 of sheet in a 140 by 42 screen: 630 widgets, and how long a scroll takes to draw -------------------")
    # the form is the whole screen; the viewport at 1,1 of it: corner (1,1), inside from (2,2), 136 by 38 -> window 135 by 37 (columns 2-136, rows 2-38)
    t0 = time.time()
    t = term(box, "zzvpbig")
    L = t.keys()
    say("    (the program started and drew in %.1f s, 630 widgets added with the form drawn once)" % (time.time() - t0 - 1.0))
    row("the first window: R00C00 at (2,2), R00C12 (x=120) whole at column 122, R00C13 (x=130) cut by the right edge (5 of its 6 cells, then the bar), "
        "R00C14 (x=140) past it; R18C00 (y=36) is the last row, row 38, R19C00 (y=38) is not there",
        at(L, 2, 2, "R00C00") and at(L, 2, 122, "R00C12") and at(L, 2, 132, "R00C1^") and not has(L, "R00C14") and at(L, 38, 2, "R18C00") and not has(L, "R19C00"),
        "\n".join(L[0:4] + L[37:41]))
    row("both bars: the vertical one in column 137 (rows 2-38), the horizontal one in row 39 (columns 2-136)",
        L[2][137] == "^" and L[38][137] == "v" and L[39][2] == "<" and L[39][136] == ">", repr((L[2][130:140], L[39][1:10])))
    times = {}
    for nm, key in (("Down", DOWN), ("Page Down", PGDN), ("Home", HOME), ("wheel", "\x1b[<65;60;20M"), ("Shift-wheel", "\x1b[<69;60;20M"), ("End", END)):
        times[nm] = timed(t, key)
    say("    scroll redraw, measured to the last byte: " + ", ".join("%s %d ms" % (k, v * 1000) for k, v in times.items()))
    L = t.lines()
    # at (3,23): the first row shown is y=23 (the sheet is 60 and the window 37), the first column x=3
    end_ok = at(L, 3, 2, "C00") and at(L, 3, 9, "R12C01") and not has(L, "R29C19")
    row("after End (the sheet at 3,23): R12C00 (x=0, y=24) is cut to its last 3 cells at (2,3), R12C01 (x=10) is whole at (9,3); R29C19 (x=190, y=58) is "
        "past the window, so it is not there", end_ok, "\n".join(L[0:6]))
    t.keys("\x1b[<69;60;20M" * 22)
    L = finish(t)
    lg = logline(L)
    row("the changes in order: Down, Page Down (kept in the sheet), Home, the wheel, Shift-wheel, End - and the Shift-wheels after it that take the "
        "sheet to its last column, 65 (the 22nd changes nothing)",
        lg is not None and lg.startswith("vp=0,1 vp=0,23 vp=0,0 vp=0,3 vp=3,3 vp=3,23 N=27 LAST=65,23 VP 65,23"), repr(lg))
    worst = max(times.values())
    row("a scroll at 200 by 60 was drawn in under 3 seconds (the slowest %.0f ms; the plan guessed 'cheap at 140x42, to be measured')" % (worst * 1000), 0.01 < worst < 3.0 and end_ok, repr(times))
    t.end()


# --PARTS-END--

PARTS = [
    ("stmt", [part_stmt]),
    ("con", [part_con]),
    ("nst", [part_nst]),
    ("eq", [part_eq]),
    ("scroll", [part_scroll]),
    ("wheel", [part_wheel]),
    ("bars", [part_bars]),
    ("focus", [part_focus]),
    ("wid", [part_wid]),
    ("nvp", [part_nvp]),
    ("vpops", [part_vpops]),
    ("big", [part_big]),
]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-viewport.py <dir> [--build] [--only=a,b]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-viewport: sandbox %s" % box)
    say("sandbox-viewport: tree    %s" % os.path.dirname(HERE))
    say("sandbox-viewport: keyset  %s" % os.environ.get("SDBOX_KEYSET", "0"))
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-viewport: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    only = [a[7:] for a in sys.argv[1:] if a.startswith("--only=")]
    want = only[0].split(",") if only else [n for n, _ in PARTS]
    for nm, body in PROGS.items():
        with open(os.path.join(sysd, "bp", nm), "w") as fh:
            fh.write(body)
    try:
        say("\n--- the programs compile as USER programs ---------------------------------------------------------")
        out = sess(box, *["BASIC bp %s" % n for n in PROGS])
        n_ok = len(re.findall(r"(?m)^Compiled 1 program\(s\) with no errors", out))
        row("setup: all %d programs compile with no errors, in a session that is not internal" % len(PROGS), n_ok == len(PROGS), out[-1500:])
        for nm, fns in PARTS:
            if nm in want:
                for fn in fns:
                    try:
                        fn(box)
                    except Exception as e:                     # a part that cannot go on is a failed row, and the next part still runs
                        row("%s did not finish: %s: %s" % (fn.__name__, type(e).__name__, e), False, repr(e))
    finally:
        say("\n--- cleanup ---------------------------------------------------------------------------------------")
        for nm in PROGS:
            for d in ("bp", "bp.out"):
                pth = os.path.join(sysd, d, nm)
                if os.path.exists(pth):
                    os.remove(pth)

    say("\nsandbox-viewport: %d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        bail("no row ran - a broken test, not a pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
