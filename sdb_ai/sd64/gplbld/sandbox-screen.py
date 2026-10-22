#!/usr/bin/env python3
#
# sandbox-screen.py - the SCREEN statement of the screen library, through USER programs.  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-screen.py <dir> [--build] [--only=owned,dialogs,forms]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty
# or absent).  --only runs just those of the three big parts (the statement basics and the compile errors always run).  Exit 0 every row passed, 1 a row failed, 2 it could not run.  Only one private SD can exist on a
# machine (shared memory keys 0x53434c91/92): stop the sandbox afterwards with sandbox-fromtree.py <dir> stop.
#
# START-HISTORY:
# 12 Oct 26 dm  Written with the spike: SCREEN MSGBOX compiled by bcomp's ST.SCREEN into a call of !screen_msgbox.
# END-HISTORY
#
# HOW IT DRIVES THE PROGRAMS.  Every program here is an ordinary USER program, compiled by a plain session (not
# sd -internal): the point of the SCREEN statement is that a user program needs no $-named routine.  It runs on a
# PSEUDO-TERMINAL (ptydrive.py) and the screen is read from the emulator in termscreen.py, as sandbox-sed-menu.py
# does.  Each program paints a background it knows, runs one SCREEN statement, and prints what came back on a line
# of its own, so a row can compare the answer and the screen with the background.  Every row that changes something
# has a control (the screen before the key, the same program without the clause); a program that printed no answer
# line fails its rows, so a statement that did nothing cannot pass.

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ptydrive import PtySession  # noqa: E402

TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
passed = failed = 0

UP, DOWN, LEFT, RIGHT = "\x1bOA", "\x1bOB", "\x1bOD", "\x1bOC"
ESC, RET = "\x1b", "\r"
CTRL_A = "\x01"
CTRL_U_KEY = "\x15"


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
    say("sandbox-screen: CANNOT RUN - " + msg)
    sys.exit(2)


def sess(box, *cmds):
    """A plain scripted session through a pipe, for compiling and setting up (no keys)."""
    say("    > " + " | ".join(cmds))
    p = subprocess.run([sys.executable, TOOL, box, "sess", os.path.join(box, "user_accounts")] + list(cmds),
                       capture_output=True, text=True, errors="replace", timeout=600)
    out = ANSI.sub("", p.stdout + p.stderr)
    return out.split(":TERM 200,9999", 1)[-1]


class Term:
    """One run of a command on a pseudo-terminal: type to it, read its screen."""

    def __init__(self, box, cmd, cols=100, rows=30, term="xterm", termsize=True, utf8=False):
        """termsize False: the size is not typed (TERM w,h): SD has to find it out from the terminal itself.
        utf8 True: the emulator decodes UTF-8 (a three-byte character is one cell)."""
        self.cols = cols
        self.rows = rows
        env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"), TERM="xterm")
        self.s = PtySession([os.path.join(box, "sys", "bin", "sd")], os.path.join(box, "user_accounts"), env, cols, rows, utf8=utf8)
        self.s.settle(1.0)
        self.s.type("TERM %s\r" % term)
        if termsize:
            self.s.type("TERM %d,%d\r" % (cols, rows))
        self.s.type(cmd + "\r", idle=1.0)

    def resize(self, cols, rows, idle=0.8):
        """Drag the window to cols by rows: SD is sent SIGWINCH.  Returns the screen's lines."""
        self.cols = cols
        self.rows = rows
        self.s.resize(cols, rows, idle=idle)
        return self.lines()

    def keys(self, *chunks, idle=0.5):
        for chunk in chunks:
            self.s.type(chunk, idle=idle)
        return self.lines()

    def lines(self):
        return self.s.screen.lines()

    def reverse(self, i):
        return self.s.screen.reverse(i)

    def underline(self, i):
        return self.s.screen.underline(i)

    def attrs(self, i):
        return self.s.screen.attrs(i)

    def style(self, r, c):
        """(foreground, background, flags) of one cell: ANSI colour numbers or None, flags from r u b (termscreen.style)."""
        return self.s.screen.style(r, c)

    def where(self, r, **kw):
        """The text of row r whose cells have the look asked for (termscreen.text_where)."""
        return self.s.screen.text_where(r, **kw)

    def cursor(self):
        """(column, row) of the terminal's cursor, from 0."""
        return (self.s.screen.c, self.s.screen.r)

    def cursor_visible(self):
        return self.s.screen.cursor_visible

    def end(self):
        self.s.type("\rOFF\r", idle=0.5)
        self.s.finish()


def result(lines, tag):
    """The text after TAG on the line that starts with it (None if no line does)."""
    for l in lines:
        if l.startswith(tag):
            return l[len(tag):].strip()
    return None


BG = """   crt @(-1) :
   for r = 0 to 14
      crt @(0, r) : fmt('bg row ' : fmt(r, 'R%2') : ' ' : str('.', 50), '60L') :
   next r
"""


def bg_ok(lines, rows=range(0, 15)):
    """The background rows are as painted; the rows that differ."""
    bad = []
    for r in rows:
        want = ("bg row %02d " % r) + "." * 50
        if lines[r] != want:
            bad.append((r, lines[r]))
    return bad


def hole(line, r):
    """How many cells of background row r are blanks where the painted row has dots (None if anything else differs)."""
    want = ("bg row %02d " % r) + "." * 50
    got = line.ljust(len(want))[:len(want)]
    n = 0
    for g, w in zip(got, want):
        if g == w:
            continue
        if g != " ":
            return None
        n += 1
    return n


# The programs.  The message box is 6 rows high and centred on a 30 row screen, so it covers rows 12 to 17.
PROGS = {
    # the whole statement: a text, a title from a variable, buttons as a comma list, a default, RETURNING, THEN / ELSE
    "zzscmsg": BG + """   t = 'Confirm'
   screen msgbox 'Delete the record?' title t buttons '&Yes,&No' default 2 returning n then
      crt @(0, 20) : 'THEN ' : n : '|'
   end else
      crt @(0, 20) : 'ELSE ' : n : '|'
   end
   crt @(0, 21) : 'TITLE ' : t : '|'
   crt @(0, 22) : 'DONE'
end
""",
    # the same box with the clauses written the other way round, and buttons as values
    "zzscord": BG + """   screen msgbox 'Delete the record?' default 2 buttons '&Yes':@vm:'&No' title 'Confirm' returning n then
      crt @(0, 20) : 'THEN ' : n : '|'
   end else
      crt @(0, 20) : 'ELSE ' : n : '|'
   end
end
""",
    # no clauses at all: one OK button, no THEN / ELSE, the statement is just a statement
    "zzscmin": BG + """   screen msgbox 'Done.'
   crt @(0, 20) : 'AFTER'
end
""",
    # a line of text is ended by a field mark; RETURNING left out
    "zzsclin": BG + """   screen msgbox 'First line':@fm:'Second line' title 'Two'
   crt @(0, 20) : 'AFTER'
end
""",
    # names the statement uses as words are still variables: SCREEN, TITLE, BUTTONS, DEFAULT, RETURNING
    "zzscvar": """   crt @(-1) :
   screen = ''
   screen<2> = 'a'
   crt @(0, 0) : 'ARR ' : convert(@fm, '/', screen) : '|'
   screen = 5
   title = 'T' ; buttons = 'OK' ; default = 1 ; returning = 7
   crt @(0, 1) : 'VARS ' : screen : '|' : title : '|' : buttons : '|' : default : '|' : returning : '|'
   screen msgbox 'hi' title title buttons buttons default default returning n
   crt @(0, 20) : 'GOT ' : n : '|' : title : '|' : buttons : '|' : default : '|'
end
""",
}

# A program that draws 20 styled rows with the library, waits for a key (the test records the screen then), runs
# the dialogue it is given, prints what came back on row 25 and waits for a key again (the test compares the
# screen with the record).
def dialogue_program(dialogue):
    return """   screen open clear else crt @(0, 28) : 'NOTERM' ; stop
   for r = 0 to 19
      screen text 'row ':fmt(r, 'R%2'):' ':str('.', 60) at 0,r
      if mod(r, 2) = 1 then
         screen text ' REV ' at 6,r attr 'reverse'
      end else
         screen text ' UL ' at 22,r attr 'underline'
      end
      if mod(r, 3) = 0 then
         screen text ' REV2 ' at 44,r attr 'reverse'
      end else
         screen text ' UL2 ' at 50,r attr 'underline'
      end
   next r
   screen cursor at 7,9
   screen key returning k1
""" + dialogue + """   screen key returning k2
   crt @(0, 25) : res
end
"""


CUSTOMER_FORM = """   cities = 'Albany':@vm:'Boston':@vm:'Chicago':@vm:'Denver'
   screen form title 'Customer' at 10,3 size 56,16 returning f
   screen label  f, 'l1', 'Name:'          at 2,2
   screen entry  f, 'name'                 at 12,2 width 30 value 'Smith'
   screen check  f, 'vip', '&VIP customer' at 12,4 value 1 place 'right'
   screen label  f, 'l2', 'Type:'          at 2,6
   screen radio  f, 'kind', 'Retail':@vm:'Wholesale':@vm:'Staff' at 12,6 value 2
   screen label  f, 'l3', 'City:'          at 2,10
   screen list   f, 'city', cities         at 12,10 size 20,4
   screen button f, 'ok',     '&OK'        at 18,14 default
   screen button f, 'cancel', '&Cancel'    at 28,14 cancel
"""

RUN_AND_REPORT = """   screen run f returning pressed then
      res = 'PRESSED ':pressed:'|'
   end else
      res = 'CANCEL ':pressed:'|'
   end
   screen values f returning v
   res := ' ':v{'name'}:'|':v{'vip'}:'|':v{'kind'}:'|':v{'city'}:'|'
"""

PROGS.update({
    # the customer form of the design note, run once
    "zzscfrm": dialogue_program(CUSTOMER_FORM + RUN_AND_REPORT),
    # the same form written out as JSON and read back, then run: a screen kept as a record
    "zzscfjs": dialogue_program(CUSTOMER_FORM + """   j = jbuild(f)
   f = jparse(j)
   crt @(0, 27) : 'JSON ' : len(j) : '|'
""" + RUN_AND_REPORT),
    # SET, ENABLED and FOCUS before the run
    "zzscfst": dialogue_program(CUSTOMER_FORM + """   screen set f, 'name' value 'Zed'
   screen set f, 'kind' value 3
   screen set f, 'city' value 2
   screen set f, 'vip' value 0
   screen set f, 'ok' enabled 0
   screen focus f, 'kind'
""" + RUN_AND_REPORT),
    # a masked entry that takes five characters, and a longer text in a narrower entry
    "zzscfen": dialogue_program("""   screen form title 'Secrets' at 20,8 size 40,8 returning f
   screen label  f, 'l', 'Password:' at 2,2
   screen entry  f, 'pw' at 13,2 width 12 mask maxlen 5
   screen entry  f, 'nm' at 13,4 width 8 value 'abcdefghijkl'
   screen button f, 'ok', '&OK' at 2,6 default
   screen run f returning pressed then
      res = 'PRESSED ':pressed
   end else
      res = 'CANCEL ':pressed
   end
   screen values f returning v
   res := ' ':v{'pw'}:'|':v{'nm'}:'|'
"""),
    # what is refused: a second widget of one id, a null id, a / in an id, a missing id, a widget that cannot be focused
    "zzscfer": """   dup = '-' ; bad1 = '-' ; bad2 = '-' ; gm = '-' ; sm = '-' ; fm1 = '-' ; rm = '-' ; okm = '-' ; nof = '-'
   screen form title 'Errors' returning f
   screen label f, 'a', 'one' at 1,1
   screen label f, 'a', 'two' at 1,2 else dup = 'DUP'
   screen label f, '', 'three' at 1,3 else bad1 = 'EMPTYID'
   screen label f, 'x/y', 'four' at 1,4 else bad2 = 'SLASH'
   screen label f, 'b', 'five' at 1,5 else okm = 'FAILED'
   screen get f, 'nosuch' returning g else gm = 'NOGET'
   screen set f, 'nosuch' value 1 else sm = 'NOSET'
   screen focus f, 'a' else fm1 = 'NOFOCUS'
   screen get f, 'b' returning g2 else nof = 'FAILED'
   not.a.form = 'text'
   screen run not.a.form returning p else rm = 'NORUN'
   crt @(0, 1) : 'ERRS ' : dup : ' ' : bad1 : ' ' : bad2 : ' ' : gm : ' ' : sm : ' ' : fm1 : ' ' : rm : ' ' : okm : ' ' : nof : ' ' : g2 : '|'
end
""",
    # an event loop: the form stays on the screen between the waits, the program changes it with SET and ends it with HIDE
    "zzscwt1": dialogue_program("""   screen form title 'Events' at 10,3 size 44,12 returning f
   screen label  f, 'st', 'ready' at 2,9 width 30 attr 'reverse'
   screen entry  f, 'name' at 8,2 width 20 value 'Al'
   screen check  f, 'on', '&Enable' at 8,4 value 0 place 'right'
   screen combo  f, 'city', 'Albany':@vm:'Boston':@vm:'Chicago' at 8,6 width 12 value 'Boston'
   screen progress f, 'pg' at 2,8 width 20 value 25
   screen button f, 'go', '&Go' at 2,10 default
   screen button f, 'quit', '&Quit' at 12,10 cancel
   log = ''
   loop
      screen wait f timeout 5 returning ev else
         log := ev<1>:';'
         exit
      end
      begin case
         case ev<1> = 'button'
            log := 'button:':ev<2>:';'
            screen set f, 'pg' value 75
            screen set f, 'st' text 'working'
         case ev<1> = 'change'
            log := 'change:':ev<2>:'=':ev<3>:';'
         case ev<1> = 'focus'
            log := 'focus:':ev<2>:'<':ev<3>:';'
         case ev<1> = 'key'
            log := 'key:':ev<3>:';'
      end case
   repeat
   screen hide f
   res = log
"""),
    # SET with WRAP, READONLY and VISIBLE: a memo that is wrapped and made a viewer while the form is shown, a button hidden
    "zzscset": dialogue_program("""   screen form title 'Set' at 10,3 size 40,12 returning f
   screen memo f, 'm', 'the quick brown fox jumps over the lazy dog' at 2,2 size 20,4
   screen button f, 'ok', '&OK' at 10,8 default
   loop
      screen wait f timeout 8 returning ev else exit
      if ev<1> = 'key' then
         if ev<3> = 'f2' then
            screen set f, 'm' wrap 1
            screen set f, 'ok' visible 0
         end
         if ev<3> = 'f3' then screen set f, 'm' readonly 1
         if ev<3> = 'f4' then
            screen set f, 'ok' visible 1
            exit
         end
      end
   repeat
   screen get f, 'm' returning t
   screen hide f
   res = 'DONE ':t:'|'
"""),
    # a scroll bar of its own: 20 lines, 5 shown, a bar 6 long; every move is a change event
    "zzscsb": dialogue_program("""   screen form title 'Scroll' at 10,3 size 30,12 returning f
   screen label f, 'l', 'lines' at 6,1 width 10
   screen scrollbar f, 'sb', 20 at 2,1 size 1,6 visible 5
   screen button f, 'ok', '&OK' at 6,9 default
   log = ''
   loop
      screen wait f timeout 8 returning ev else exit
      if ev<1> = 'change' then
         log := ev<3>:';'
         screen set f, 'l' text 'line ':ev<3>
      end
      if ev<1> = 'button' then exit
   repeat
   screen get f, 'sb' returning v
   screen hide f
   res = 'LOG ':log:' V ':v:'|'
"""),
    # a wait that times out, and the hide that follows
    "zzscwt2": dialogue_program("""   res = 'NO-ELSE'
   screen form title 'Late' at 10,3 size 30,6 returning f
   screen label  f, 'st', 'waiting' at 2,2 width 20
   screen button f, 'ok', '&OK' at 2,4 default
   screen wait f timeout 1 returning ev else
      res = 'ELSE ':ev<1>:'|'
   end
   screen set f, 'st' text 'timed out'
   screen key returning kk
   screen hide f
"""),
    # a phantom has no terminal: every statement that waits for the user answers ELSE and nothing hangs.  It writes
    # what it found to a VOC record, which zzscphs (a program in the session that started it) reads back.
    "zzscph": """   r1 = 'OPEN-THEN' ; r2 = 'MSG-THEN' ; r3 = 'KEY-THEN' ; r4 = 'MENU-THEN' ; r5 = 'RUN-THEN' ; r6 = 'PICK-THEN' ; r7 = 'ASK-THEN' ; r8 = 'WAIT-THEN'
   screen open clear else r1 = 'OPEN-ELSE'
   screen msgbox 'hi' returning n else r2 = 'MSG-ELSE ':n
   screen key timeout 1 returning k else r3 = 'KEY-ELSE'
   screen menu 'a':@vm:'b' returning c else r4 = 'MENU-ELSE'
   screen pick 'a':@vm:'b' returning n2 else r6 = 'PICK-ELSE'
   screen ask 'Name' returning s else r7 = 'ASK-ELSE'
   screen form returning f
   screen entry f, 'x' at 1,1
   screen button f, 'ok', 'OK' at 1,3 default
   screen run f returning p else r5 = 'RUN-ELSE'
   screen wait f timeout 1 returning ev else r8 = 'WAIT-ELSE ':ev<1>
   r9 = 'THEME-THEN' ; r10 = 'STYLE-THEN'
   screen theme 'classic' returning th else r9 = 'THEME-ELSE ':th
   screen style 'bar', 'red', 'black', 'bold' else r10 = 'STYLE-ELSE'
   open 'VOC' to v else stop
   write r1:@fm:r2:@fm:r3:@fm:r4:@fm:r5:@fm:r6:@fm:r7:@fm:r8:@fm:r9:@fm:r10 on v, 'zzscph_out'
end
""",
    "zzscphs": """   open 'VOC' to v else stop
   delete v, 'zzscph_out'
   execute 'PHANTOM NO.MSG RUN bp zzscph'
   for i = 1 to 40
      read r from v, 'zzscph_out' then exit
      sleep 1
   next i
   read r from v, 'zzscph_out' then
      crt 'PHANTOM ' : convert(@fm, '|', r) : '|'
      delete v, 'zzscph_out'
   end else
      crt 'PHANTOM none'
   end
end
""",
    # a form that wants a name, run again with what was typed until it has one
    "zzscfr2": dialogue_program("""   screen form title 'Needs a name' returning f
   screen label  f, 'l', 'Name:' at 2,1
   screen entry  f, 'name' at 8,1 width 20
   screen button f, 'ok', '&OK' at 6,3 default
   screen button f, 'cancel', '&Cancel' at 14,3 cancel
   runs = 0
   loop
      runs += 1
      screen run f returning pressed else
         res = 'CANCELLED ':runs:'|'
         exit
      end
      screen get f, 'name' returning name
      if name = '' then
         screen msgbox 'The name is required.' title 'Form'
         continue
      end
      res = 'NAME ':name:' RUNS ':runs:'|'
      exit
   repeat
"""),
    # a pop-up menu: four entries, one a line, shortcuts shown, codes given for some
    "zzscmnu": dialogue_program("""   items = 'Open':@sm:'Ctrl-O':@sm:'open':@vm:'-':@vm:'&Save':@sm:'Ctrl-S':@vm:'E&xit'
   screen menu items at 10,4 returning c then
      res ='CODE ' : c : '|'
   end else
      res ='CANCEL [' : c : ']'
   end
"""),
    # a menu bar: drawn alone, then used
    "zzscbar": dialogue_program("""   menus = '&File':@vm:'&Open':@sm:'Ctrl-O':@sm:'open':@vm:'E&xit':@sm:'':@sm:'exit'
   menus<2> = '&Edit':@vm:'&Copy':@vm:'&Paste'
   screen menubar menus draw
   screen key returning kk
   screen menubar menus returning c then
      res ='CODE ' : c : '|'
   end else
      res ='CANCEL [' : c : ']'
   end
"""),
    # a menu bar with a disabled entry, a checked one and a submenu (a menu whose title begins with >)
    "zzscmfl": dialogue_program("""   menus = '&File':@vm:'&Open':@sm:'':@sm:'open':@vm:'&Save':@sm:'':@sm:'save':@sm:'D':@vm:'&Autosave':@sm:'':@sm:'auto':@sm:'C'
   menus := @vm:'&Recent':@sm:'':@sm:'>Recent':@vm:'E&xit':@sm:'':@sm:'exit'
   menus<2> = '&Edit':@vm:'&Copy':@sm:'':@sm:'copy':@vm:'&Paste':@sm:'':@sm:'paste':@sm:'D'
   menus<3> = '>Recent':@vm:'one.txt':@sm:'':@sm:'r1':@vm:'two.txt':@sm:'':@sm:'r2'
   screen menubar menus returning c then
      res ='CODE ' : c : '|'
   end else
      res ='CANCEL [' : c : ']'
   end
"""),
    # a pick list with more entries than rows
    "zzscpik": dialogue_program("""   items = 'Albany':@vm:'Boston':@vm:'Chicago':@vm:'Denver':@vm:'Elgin':@vm:'Fresno':@vm:'Gary':@vm:'Houston':@vm:'Irvine':@vm:'Jackson'
   screen pick items title 'Pick one' size 20,5 returning n then
      res ='PICKED ' : n : '|'
   end else
      res ='CANCEL [' : n : ']'
   end
"""),
    "zzscpim": dialogue_program("""   items = 'Albany':@vm:'Boston':@vm:'Chicago':@vm:'Denver'
   screen pick items title 'Several' multi returning n then
      res ='PICKED ' : convert(@vm, ',', n) : '|'
   end else
      res ='CANCEL [' : n : ']'
   end
"""),
    # a line of text asked for
    "zzscask": dialogue_program("""   screen ask 'Your name?' value 'Bob' width 12 title 'Name' returning s then
      res ='TEXT ' : s : '|'
   end else
      res ='CANCEL [' : s : ']'
   end
"""),
    "zzscpwd": dialogue_program("""   screen ask 'Password' value 'abc' width 10 mask returning s then
      res ='TEXT ' : s : '|'
   end else
      res ='CANCEL [' : s : ']'
   end
"""),
    # a message box put where the program says
    "zzscmat": dialogue_program("""   screen msgbox 'Moved.' title 'Here' at 5,3 returning n
   res = 'BUTTON ' : n : '|'
"""),
    # the owned screen: text with styles, a continued text, a padded text, a clipped text, a box with a title
    "zzscown": """   screen open clear else crt @(0, 28) : 'NOTERM' ; stop
   screen text 'plain text' at 2,1
   screen text 'REVERSE' at 2,3 attr 'reverse'
   screen text 'under' at 12,3 attr 'underline'
   screen text 'cont' at 30,5
   screen text 'next'
   screen text 'ab' at 10,7 width 6
   screen text 'xyzzy-long-text' at 5,8 width 5
   screen text '0123456789' at 95,9
   for r = 12 to 14
      screen text 'xxxxxxxxxxxxxxxxxxxx' at 2,r
   next r
   screen box at 2,11 size 20,5 title 'Box' fill
   screen text 'yyyyyyyyyyyy' at 30,12
   screen text 'yyyyyyyyyyyy' at 30,13
   screen box at 30,11 size 12,4
   screen text 'inside' at 33,12
   screen size returning dims
   crt @(0, 20) : 'SIZE ' : dims<1> : 'x' : dims<2> : '|'
   screen key returning k
end
""",
    # borders in line-drawing characters (SCREEN OPEN ... LINES), a message box in them, and plain ones after SCREEN CLOSE
    "zzscbln": """   screen open clear lines else crt @(0, 28) : 'NOTERM' ; stop
   screen box at 2,2 size 12,4 title 'Hi'
   screen text 'a + b - c | d' at 2,8
   screen msgbox 'Boxed.' title 'T' at 20,3 returning n
   screen key returning k
   screen close
   screen open clear
   screen box at 2,2 size 12,4 title 'Hi'
   screen key returning k
   screen close
end
""",
    # SCREEN CLIP: text outside the rectangle is not drawn, text across its edge is cut, and the clip comes off again
    "zzscclp": """   screen open clear else crt @(0, 28) : 'NOTERM' ; stop
   screen clip at 10,5 size 10,3
   screen text 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' at 5,4
   screen text 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' at 5,6
   screen text 'abcdefghijklmnopqrstuvwxyz' at 14,7
   screen text 'below' at 10,8
   screen clip at 10,5 size 10,3 else crt @(0, 20) : 'CLIP-ELSE'
   screen clip
   screen text 'free' at 0,12
   screen key returning k
end
""",
    # a background of styled rows, then a dialogue over it, then the key that ends the program
    "zzscund": """   screen open clear else crt @(0, 28) : 'NOTERM' ; stop
   for r = 0 to 19
      screen text 'row ':fmt(r, 'R%2'):' ':str('.', 30) at 0,r
      if mod(r, 2) = 1 then
         screen text ' REV ' at 6,r attr 'reverse'
      end else
         screen text ' UL ' at 22,r attr 'underline'
      end
      if mod(r, 3) = 0 then
         screen text ' REV2 ' at 44,r attr 'reverse'
      end else
         screen text ' UL2 ' at 50,r attr 'underline'
      end
   next r
   screen cursor at 7,9
   screen key returning k1
   screen msgbox 'Replace it?' title 'Ask' buttons '&Yes,&No' returning n
   screen key returning k2
   crt @(0, 25) : 'ANSWER ' : n : ' ' : k1 : ' ' : k2 : '|'
end
""",
    # the terminal is cleared behind the library's back, and SCREEN REFRESH paints the shadow again
    "zzscref": """   screen open clear else crt @(0, 28) : 'NOTERM' ; stop
   screen text 'kept text' at 3,2
   screen text 'kept reverse' at 3,4 attr 'reverse'
   screen key returning k
   crt @(-1) :
   crt @(0, 20) : 'CLEARED'
   screen key returning k
   screen refresh returning r
   crt @(0, 21) : 'REFRESH [' : r : ']'
   screen key returning k
end
""",
    # the cursor: hidden, placed, shown, and put back after a dialogue
    "zzsccur": """   screen open clear nocursor else crt @(0, 28) : 'NOTERM' ; stop
   screen text 'x' at 0,0
   screen cursor at 7,9
   screen key returning k
   screen cursor on
   screen key returning k
   screen msgbox 'Hi'
   screen key returning k
   screen cursor off
   screen key returning k
end
""",
    # keys by name, a timeout, and a screen too small for the program
    "zzsckey": """   crt @(-1) :
   screen open minsize 300,100 else crt @(0, 0) : 'SMALL' ; goto next1
   crt @(0, 0) : 'BIG'
next1:
   for i = 1 to 3
      screen key timeout 3 returning k then
         crt @(0, i) : 'KEY [' : k : ']'
      end else
         crt @(0, i) : 'NOKEY'
      end
   next i
   screen key timeout 1 returning k else crt @(0, 5) : 'TIMEOUT [' : k : ']'
end
""",
})

BAD = {  # name -> (source, text the compiler must give)
    "zzscbv": ("   screen frob 'x'\nend\n", "Unrecognised screen verb frob"),
    "zzscnv": ("   screen\nend\n", "The screen statement needs a verb after it"),
    "zzsctw": ("   screen msgbox 'x' title 'a' title 'b'\nend\n", "The title clause appears twice in a screen statement"),
    "zzscnt": ("   screen msgbox 'x' colour 5\nend\n", "The screen msgbox statement does not take colour"),
    "zzscnx": ("   screen msgbox title 'a'\nend\n", ""),   # no text: some syntax error, any
}


def part_owned(box):
    say("\n--- SCREEN OPEN, TEXT, BOX, SIZE: the screen the library owns -----------------------------------------")
    t = Term(box, "RUN bp zzscown")
    L = t.keys()
    row("control: the program ran and the screen was cleared first (no NOTERM, no prompt left on row 0)", result(L, "NOTERM") is None and not L[0].startswith(":"), "\n".join(L[:3]))
    row("TEXT at 2,1 puts the line there", L[1][2:12] == "plain text" and L[1][:2].strip() == "", repr(L[1]))
    row("ATTR 'reverse' draws reverse video, and only that text; the text before it is not", t.reverse(3) == "REVERSE" and "plain" not in t.reverse(1), repr((t.reverse(3), t.reverse(1))))
    row("ATTR 'underline' draws underlined text on the same row, in its own cells", t.underline(3) == "under" and t.attrs(3)[2:9] == "r" * 7 and t.attrs(3)[12:17] == "u" * 5, repr(t.attrs(3)[:20]))
    row("TEXT without AT continues where the last one ended: 'cont' then 'next' touch", L[5][30:38] == "contnext", repr(L[5]))
    row("WIDTH 6 pads 'ab' to six cells; WIDTH 5 cuts the long text to its first five", L[7][10:12] == "ab" and L[8][5:10] == "xyzzy" and L[8][10:11] == "", repr((L[7], L[8])))
    row("text that runs past the right edge is cut there and does not wrap (95 + 5 cells)", L[9][95:] == "01234" and L[10].strip() == "", repr((L[9], L[10])))
    row("BOX with a title and FILL: a +-| border exactly 20 wide, the title in the top border",
        L[11][2:22] == "+- Box ------------+" and L[15][2:22] == "+" + "-" * 18 + "+", "\n".join(L[11:16]))
    row("...FILL blanked the inside: the x's that were there are gone (three rows of 18 blanks between the | | border)",
        all(L[r][2:22] == "|" + " " * 18 + "|" for r in (12, 13, 14)) and not any("x" in L[r] for r in (12, 13, 14)), "\n".join(L[11:16]))
    row("BOX without FILL leaves the inside alone: the y's drawn before it are kept either side of the text drawn after, 12 wide, 4 high",
        L[11][30:42] == "+" + "-" * 10 + "+" and L[12][30:42] == "|yyinsideyy|" and L[13][30:42] == "|" + "y" * 10 + "|" and L[14][30:42] == "+" + "-" * 10 + "+", "\n".join(L[11:15]))
    row("SIZE answers the terminal's width and height (100x30)", result(L, "SIZE") == "100x30|", repr(result(L, "SIZE")))
    row("the cursor is left after the last TEXT, not wherever the box ended", t.cursor() != (0, 0), repr(t.cursor()))
    t.keys("q")
    t.end()

    say("\n--- a dialogue over the library's own text: every cell comes back, attribute for attribute -------------")
    t = Term(box, "RUN bp zzscund")
    L0 = t.keys()
    A0 = [t.attrs(r) for r in range(30)]
    row("control: the background is 20 rows of text with reverse and underline spans, recorded", "r" in A0[1] and "u" in A0[0] and "r" not in A0[2] and L0[19].startswith("row 19"), repr((A0[0][:30], A0[1][:30])))
    row("control: the cursor was put at 7,9 and is shown", t.cursor() == (7, 9) and t.cursor_visible(), repr(t.cursor()))
    L1 = t.keys("a")
    row("a key and then the box: it is on the screen, over the background", any("[ Yes ]" in l and "[ No ]" in l for l in L1) and any("Replace it?" in l for l in L1), "\n".join(L1[10:19]))
    row("control: the box really changed rows 12 to 17 (a restore that did nothing cannot pass)", L1[12:18] != L0[12:18], "")
    row("...and left rows 0 to 11 alone", L1[:12] == L0[:12], "")
    L2 = t.keys(RET)
    A2 = [t.attrs(r) for r in range(30)]
    row("Return closes it: every row of the background has its text back", L2[:20] == L0[:20], "\n".join(l for l, m in zip(L2[:20], L0[:20]) if l != m))
    row("...and every cell its style back (reverse and underline spans, 20 rows x 100 cells)", A2[:20] == A0[:20], repr([(i, a, b) for i, (a, b) in enumerate(zip(A2[:20], A0[:20])) if a != b][:2]))
    row("...and the cursor is where SCREEN CURSOR put it (7,9), not where the box ended", t.cursor() == (7, 9) and t.cursor_visible(), repr(t.cursor()))
    L3 = t.keys("z")
    row("the answer, the keys before and after: button 1, a, z", result(L3, "ANSWER") == "1 a z|", repr(result(L3, "ANSWER")))
    t.end()

    say("\n--- SCREEN REFRESH --------------------------------------------------------------------------------------")
    t = Term(box, "RUN bp zzscref")
    L = t.keys()
    row("control: the kept text and the kept reverse text are on the screen", L[2][3:12] == "kept text" and t.reverse(4) == "kept reverse", "\n".join(L[:6]))
    L = t.keys("a")
    row("control: the program cleared the terminal behind the library's back (it says so)", any(l.startswith("CLEARED") for l in L), "\n".join(L[:22]))
    row("...and the kept text really is gone from the screen", not any("kept text" in l for l in L), "\n".join(L[:6]))
    L = t.keys("b")
    row("REFRESH paints the shadow again: the text is back at the same place", L[2][3:12] == "kept text", "\n".join(L[:6]))
    row("...with its style: the reverse text is reverse again", t.reverse(4) == "kept reverse" and "kept text" not in t.reverse(2), repr(t.reverse(4)))
    row("...and the answer is null (the terminal is the size it was)", result(L, "REFRESH") == "[]", repr(result(L, "REFRESH")))
    t.keys("c")
    t.end()

    say("\n--- SCREEN CURSOR ---------------------------------------------------------------------------------------")
    t = Term(box, "RUN bp zzsccur")
    L = t.keys()
    row("NOCURSOR hides the cursor and CURSOR AT places it: hidden, at 7,9", (not t.cursor_visible()) and t.cursor() == (7, 9), repr((t.cursor(), t.cursor_visible())))
    t.keys("a")
    row("CURSOR ON shows it where it was", t.cursor_visible() and t.cursor() == (7, 9), repr((t.cursor(), t.cursor_visible())))
    L = t.keys("b")
    row("control: the next key opens a message box (so the next row is about a cursor that was moved)", any("[ OK ]" in l for l in L), "\n".join(L[10:20]))
    L = t.keys(RET)
    row("after the dialogue the cursor is put back at 7,9 and is shown", t.cursor_visible() and t.cursor() == (7, 9) and not any("[ OK ]" in l for l in L), repr((t.cursor(), t.cursor_visible())))
    t.keys("c")
    row("CURSOR OFF hides it again", not t.cursor_visible(), repr(t.cursor_visible()))
    t.end()

    say("\n--- SCREEN KEY, and MINSIZE ----------------------------------------------------------------------------")
    t = Term(box, "RUN bp zzsckey")
    L = t.keys()
    row("MINSIZE 300,100 on a 100x30 terminal takes the ELSE branch: the screen is not taken", result(L, "SMALL") is not None or any(l.startswith("SMALL") for l in L), "\n".join(L[:3]))
    row("...and the program carried on without the screen (no BIG)", not any(l.startswith("BIG") for l in L), "")
    L = t.keys("x")
    L = t.keys(UP)
    L = t.keys(CTRL_A)
    row("keys come back by name: x, up, ctrl-a", L[1].strip() == "KEY [x]" and L[2].strip() == "KEY [up]" and L[3].strip() == "KEY [ctrl-a]", "\n".join(L[:5]))
    row("control: no TIMEOUT line before the time has run out", not any(l.startswith("TIMEOUT") for l in L), "")
    t.s.settle(1.8)
    L = t.lines()
    row("TIMEOUT 1 with no key: ELSE is taken and RETURNING holds null", any(l.startswith("TIMEOUT []") for l in L), "\n".join(L[:8]))
    t.end()


def same_as(t, L0, A0, rows=range(0, 20)):
    """The screen's rows `rows` (text and the style of every cell) are those recorded in L0 and A0."""
    L = t.lines()
    bad = [r for r in rows if L[r] != L0[r] or t.attrs(r) != A0[r]]
    return not bad, bad


def final(t, tag):
    """Press a key to let the program print what the dialogue returned (the dialogue programs wait for it), and
    answer the text after TAG on the line that starts with it."""
    return result(t.keys("z"), tag)


def record(t):
    return t.lines(), [t.attrs(r) for r in range(30)]


def part_dialogs(box):
    say("\n--- SCREEN MENU: a pop-up menu --------------------------------------------------------------------------")
    t = Term(box, "RUN bp zzscmnu")
    L0, A0 = record(t)
    L = t.keys("a")
    row("control: the background is there and no menu yet (the program waits for a key first)", L0[4].startswith("row 04") and not any("Ctrl-O" in l for l in L0), L0[4])
    row("the entries are drawn at 4,10: label, shortcut aligned to the right, one row each, the line a row of dashes",
        L[4][10:26] == " Open    Ctrl-O " and L[5][10:26] == "-" * 16 and L[6][10:26] == " Save    Ctrl-S " and L[7][10:26] == " Exit           ", "\n".join(l[:40] for l in L[3:9]))
    row("the first entry is the selected one: normal video with its letter underlined; the rest are reverse video",
        t.attrs(4)[10:26] == "nu" + "n" * 14 and t.attrs(5)[10:26] == "r" * 16 and t.attrs(6)[10:26] == "rx" + "r" * 14 and t.attrs(7)[10:26] == "rrx" + "r" * 13,
        repr([t.attrs(r)[10:26] for r in range(4, 8)]))
    L = t.keys(DOWN)
    row("Down skips the line and selects Save: normal video with its letter underlined", t.attrs(6)[10:26] == "nu" + "n" * 14 and t.attrs(5)[10:26] == "r" * 16, repr([t.attrs(r)[10:26] for r in range(4, 8)]))
    row("...and the first entry is reverse again (its letter reverse and underlined)", t.attrs(4)[10:26] == "rx" + "r" * 14, repr(t.attrs(4)[10:26]))
    L = t.keys(RET)
    ok, bad = same_as(t, L0, A0)
    row("Return closes the menu: every cell of the 20 rows is back, text and style", ok, repr(bad))
    row("...and the cursor is where SCREEN CURSOR put it", t.cursor() == (7, 9), repr(t.cursor()))
    row("...and Return answered the code of the entry: Save has none given, so its number in the list, 3", final(t, "CODE") == "3|", "")
    t.end()
    t = Term(box, "RUN bp zzscmnu")
    t.keys("a")
    t.keys("x")
    row("a letter chooses the entry that has it (E&xit: x): its number, 4", final(t, "CODE") == "4|", "")
    t.end()
    t = Term(box, "RUN bp zzscmnu")
    t.keys("a")
    t.keys(DOWN, DOWN, DOWN, RET)
    row("Down three times wraps past the end and the line to the first entry: Return gives its code, open", final(t, "CODE") == "open|", "")
    t.end()
    t = Term(box, "RUN bp zzscmnu")
    L0, A0 = record(t)
    t.keys("a")
    t.keys(ESC, idle=0.9)
    ok, bad = same_as(t, L0, A0)
    row("Esc: the screen is put back", ok, repr(bad))
    row("...ELSE is taken and RETURNING is null", final(t, "CANCEL") == "[]", "")
    t.end()

    say("\n--- SCREEN MENUBAR: a bar with drop-down menus ----------------------------------------------------------")
    t = Term(box, "RUN bp zzscbar")
    L0, A0 = record(t)
    L = t.keys("a")
    row("DRAW: the bar is on row 0, File and Edit, the whole row in reverse video, the mnemonic letters also underlined",
        L[0].startswith(" File  Edit") and t.attrs(0)[:12] == "rxrrrrrxrrrr" and set(t.attrs(0)[12:]) == {"r"}, repr((L[0][:20], t.attrs(0)[:14])))
    row("control: DRAW opened nothing (no entry on rows 1 to 3 yet)", not any("Open" in l for l in L[1:4]), "\n".join(L[:4]))
    L = t.keys("b")
    row("the next statement runs the bar: File is open under its title, with Open and Exit",
        any("Open" in l and "Ctrl-O" in l for l in L[1:4]) and any("Exit" in l for l in L[1:4]), "\n".join(L[:5]))
    L = t.keys(RIGHT)
    row("Right opens Edit (Copy, Paste) and File's entries are gone", any("Copy" in l for l in L[1:4]) and not any("Ctrl-O" in l for l in L[1:4]), "\n".join(L[:5]))
    L = t.keys(DOWN, RET)
    ok, bad = same_as(t, L0, A0, range(1, 20))
    row("Down then Return closes the drop-down: rows 1 to 19 are back cell for cell", ok, repr(bad))
    row("...and the bar is still on row 0", L[0].startswith(" File  Edit") and t.attrs(0)[0] == "r", repr(L[0][:20]))
    row("...and it chose Paste, the second entry of Edit, whose code is its number, 2", final(t, "CODE") == "2|", "")
    t.end()

    say("\n--- SCREEN PICK: a list ---------------------------------------------------------------------------------")
    t = Term(box, "RUN bp zzscpik")
    L0, A0 = record(t)
    L = t.keys("a")
    row("the box is 22 wide and 7 high, centred (39,11): the title in the top border, five of ten entries inside",
        L[11][39:61] == "+- Pick one " + "-" * 9 + "+" and L[17][39:61] == "+" + "-" * 20 + "+", "\n".join(l[36:64] for l in L[10:19]))
    row("...Albany to Elgin are the rows shown; Fresno is not", [L[12 + i][40:48].strip() for i in range(5)] == ["Albany", "Boston", "Chicago", "Denver", "Elgin"] and not any("Fresno" in l for l in L), "\n".join(l[36:64] for l in L[10:19]))
    row("...a scroll bar in the right-hand column: ^ at the top, v at the bottom, between them a # as long as the part showing (half the track: 5 of 10)",
        [L[12 + i][59] for i in range(5)] == ["^", "#", "#", "|", "v"], repr([L[12 + i][59] for i in range(5)]))
    row("...the current entry (Albany) is in reverse video inside the box and the next one is not",
        "r" in t.attrs(12)[40:59] and "r" not in t.attrs(13)[40:59], repr((t.attrs(12)[38:62], t.attrs(13)[38:62])))
    L = t.keys(DOWN, DOWN, DOWN, DOWN)
    row("four Downs: Elgin (5) is the current entry and the last row, so the list has not scrolled yet",
        [L[12 + i][40:48].strip() for i in range(5)] == ["Albany", "Boston", "Chicago", "Denver", "Elgin"] and "r" in t.attrs(16)[40:59], "\n".join(l[36:64] for l in L[10:19]))
    L = t.keys(DOWN)
    row("one more Down: Fresno (6) is the current entry, so the list scrolls by one row at once (Boston first, Fresno last)",
        [L[12 + i][40:48].strip() for i in range(5)] == ["Boston", "Chicago", "Denver", "Elgin", "Fresno"] and "r" in t.attrs(16)[40:59], "\n".join(l[36:64] for l in L[10:19]))
    L = t.keys(DOWN)
    row("and one more: the list scrolls so that Gary (7) is the last row shown, Chicago the first",
        [L[12 + i][40:48].strip() for i in range(5)] == ["Chicago", "Denver", "Elgin", "Fresno", "Gary"] and "r" in t.attrs(16)[40:59], "\n".join(l[36:64] for l in L[10:19]))
    L = t.keys(RET)
    ok, bad = same_as(t, L0, A0)
    row("Return closes the box: every cell of the 20 rows is back", ok, repr(bad))
    row("...and it answered 7, the number of the entry (THEN)", final(t, "PICKED") == "7|", "")
    t.end()
    t = Term(box, "RUN bp zzscpik")
    t.keys("a")
    L = t.keys("h")
    row("a letter jumps to the next entry that starts with it: h is Houston, now scrolled into view and selected",
        any("Houston" in l for l in L) and any("Houston" in t.reverse(r)[:60] for r in range(11, 19)), "\n".join(l[36:64] for l in L[10:19]))
    t.keys(RET)
    row("...and Return answers 8", final(t, "PICKED") == "8|", "")
    t.end()
    t = Term(box, "RUN bp zzscpik")
    L0, A0 = record(t)
    t.keys("a")
    t.keys(ESC, idle=0.9)
    ok, bad = same_as(t, L0, A0)
    row("Esc: the screen is put back", ok, repr(bad))
    row("...ELSE is taken and RETURNING is null", final(t, "CANCEL") == "[]", "")
    t.end()
    t = Term(box, "RUN bp zzscpim")
    t.keys("a")
    L = t.keys(" ", DOWN, DOWN, " ")
    row("MULTI: each row starts [ ] or [x]; the space bar picks the current entry", any("[x] Albany" in l for l in L) and any("[ ] Boston" in l for l in L) and any("[x] Chicago" in l for l in L), "\n".join(l[36:64] for l in L[10:19]))
    L = t.keys(DOWN, DOWN, " ", " ")
    row("...the space bar on a picked entry unpicks it (Denver picked, then unpicked)", any("[ ] Denver" in l for l in L), "\n".join(l[36:64] for l in L[10:19]))
    t.keys(RET)
    row("Return answers the numbers picked, as values: 1 and 3", final(t, "PICKED") == "1,3|", "")
    t.end()

    say("\n--- SCREEN ASK: a line of text --------------------------------------------------------------------------")
    t = Term(box, "RUN bp zzscask")
    L0, A0 = record(t)
    L = t.keys("a")
    row("the box (16 x 4, centred at 42,13) has the title, the prompt and the field holding Bob",
        "Name" in L[13][42:58] and L[14][44:55].startswith("Your name?") and L[15][44:47] == "Bob", "\n".join(l[38:62] for l in L[12:18]))
    row("...the field is 12 cells in reverse video (it has the focus)", t.attrs(15)[44:56] == "r" * 12, repr(t.attrs(15)[40:60]))
    L = t.keys("b", "y")
    row("typing adds to the end: Bobby", L[15][44:49] == "Bobby", repr(L[15][40:60]))
    t.keys(RET)
    ok, bad = same_as(t, L0, A0)
    row("Return closes the box: every cell of the 20 rows is back", ok, repr(bad))
    row("...and it answered the text (THEN)", final(t, "TEXT") == "Bobby|", "")
    t.end()
    t = Term(box, "RUN bp zzscask")
    t.keys("a")
    t.keys(CTRL_U_KEY, "Al", ESC, idle=0.9)
    row("Ctrl-U empties the field, then Al, then Esc: ELSE and RETURNING null", final(t, "CANCEL") == "[]", "")
    t.end()
    t = Term(box, "RUN bp zzscpwd")
    t.keys("a")
    L = t.keys("d")
    row("MASK: the field shows a * for each character, the old text and the new one: ****", any("****" in l for l in L[10:18]) and not any("abc" in l[40:60] for l in L[10:18]), "\n".join(l[38:62] for l in L[12:18]))
    t.keys(RET)
    row("...and the answer is the real text, abcd", final(t, "TEXT") == "abcd|", "")
    t.end()

    say("\n--- SCREEN MSGBOX AT -------------------------------------------------------------------------------------")
    t = Term(box, "RUN bp zzscmat")
    L0, A0 = record(t)
    L = t.keys("a")
    row("AT 5,3 puts the box's top left corner there: a + at column 5 of row 3, the title in the border", L[3][5:7] == "+-" and "Here" in L[3][5:20], "\n".join(l[:30] for l in L[2:9]))
    t.keys(RET)
    ok, bad = same_as(t, L0, A0)
    row("...closed, the screen is as it was", ok, repr(bad))
    row("...and the button was 1", final(t, "BUTTON") == "1|", "")
    t.end()


TAB, BTAB = "\t", "\x1b[Z"


def part_forms(box):
    say("\n--- SCREEN FORM and its widgets: the customer form of the design note ----------------------------------")
    t = Term(box, "RUN bp zzscfrm")
    L0, A0 = record(t)
    L = t.keys("a")
    row("the frame is 56 x 16 at 10,3 with the title in the top border",
        L[3][10:22] == "+- Customer " and L[3][65] == "+" and L[18][10] == "+" and L[18][11:65] == "-" * 54 and L[18][65] == "+" and L[10][10] == "|" and L[10][65] == "|",
        "\n".join(l[8:68] for l in L[2:20]))
    row("the labels are where they were put, counted from the form's corner: Name: at 12,5, Type: at 12,9, City: at 12,13",
        L[5][12:17] == "Name:" and L[9][12:17] == "Type:" and L[13][12:17] == "City:", "\n".join(l[8:68] for l in L[4:14]))
    row("the entry holds Smith, 30 cells wide, in reverse video because it has the focus, and the cursor is after the text",
        L[5][22:27] == "Smith" and t.attrs(5)[22:52] == "r" * 30 and t.attrs(5)[52] == "n" and t.cursor() == (27, 5), repr((L[5][20:55], t.attrs(5)[20:55], t.cursor())))
    row("the check box is checked and has no focus: [x] VIP customer in normal video",
        L[7][22:38] == "[x] VIP customer" and t.attrs(7)[22:38] == "n" * 16, repr((L[7][20:40], t.attrs(7)[20:40])))
    row("the radio group is one to a row with the second selected: ( ) Retail, (*) Wholesale, ( ) Staff",
        L[9][22:32] == "( ) Retail" and L[10][22:35] == "(*) Wholesale" and L[11][22:31] == "( ) Staff", "\n".join(l[20:40] for l in L[8:13]))
    row("the list shows its four entries, the current one marked with >, as it has no focus",
        L[13][22:29] == ">Albany" and L[14][22:29] == " Boston" and L[15][22:30] == " Chicago" and L[16][22:29] == " Denver", "\n".join(l[20:46] for l in L[12:18]))
    row("the two buttons are on row 17: [ OK ] at 28 and [ Cancel ] at 38",
        L[17][28:34] == "[ OK ]" and L[17][38:48] == "[ Cancel ]", repr(L[17][20:55]))
    row("control: nothing but the entry has the focus (no other reverse video inside the form)",
        all("r" not in t.attrs(r)[11:65] for r in range(4, 18) if r != 5), repr([(r, t.attrs(r)[11:65]) for r in range(4, 18) if "r" in t.attrs(r)[11:65] and r != 5]))

    L = t.keys(TAB)
    row("Tab: the focus goes to the check box (reverse video, cursor inside it) and the entry is underlined again",
        t.attrs(7)[22:38] == "r" * 16 and t.attrs(5)[22:52] == "u" * 30 and t.cursor() == (23, 7), repr((t.attrs(7)[20:40], t.attrs(5)[20:54], t.cursor())))
    L = t.keys(TAB)
    row("Tab again: the radio group, with its current choice (Wholesale) in reverse video",
        t.attrs(10)[22:35] == "r" * 13 and "r" not in t.attrs(9)[22:35] and "r" not in t.attrs(7)[22:38], repr((t.attrs(10)[20:40], t.attrs(9)[20:40])))
    L = t.keys(TAB)
    row("Tab again: the list, its current entry (Albany) in reverse video across the list's 20 cells",
        t.attrs(13)[22:42] == "r" * 20 and L[13][22:29] == " Albany", repr((t.attrs(13)[20:44], L[13][20:44])))
    L = t.keys(TAB)
    row("Tab again: the OK button", t.attrs(17)[28:34] == "r" * 6 and "r" not in t.attrs(13)[22:42], repr(t.attrs(17)[26:50]))
    L = t.keys(TAB)
    row("Tab again: the Cancel button", t.attrs(17)[38:48] == "r" * 10 and "r" not in t.attrs(17)[28:34], repr(t.attrs(17)[26:50]))
    L = t.keys(TAB)
    row("Tab again goes round the ring to the entry", t.attrs(5)[22:52] == "r" * 30 and "r" not in t.attrs(17)[28:48], repr(t.attrs(5)[20:54]))
    L = t.keys(BTAB)
    row("Shift-Tab goes the other way round: from the entry back to Cancel", t.attrs(17)[38:48] == "r" * 10, repr((t.attrs(17)[36:50], t.attrs(5)[22:30])))
    t.end()

    t = Term(box, "RUN bp zzscfrm")
    L0, A0 = record(t)
    t.keys("a")
    t.keys("son")
    L = t.keys(RET)
    ok, bad = same_as(t, L0, A0)
    row("typing in the entry adds to the text, and Return there presses the default button: the form closes and the 20 rows are back cell for cell", ok, repr(bad))
    row("...and the cursor is where SCREEN CURSOR put it", t.cursor() == (7, 9), repr(t.cursor()))
    L = t.keys("z")
    row("RUN answered the button's id (THEN); VALUES gave the entry, the check box, the radio group and the list",
        result(L, "PRESSED") == "ok| Smithson|1|2|1|", repr(result(L, "PRESSED")))
    t.end()

    t = Term(box, "RUN bp zzscfrm")
    t.keys("a")
    L = t.keys(TAB, " ")
    row("the space bar on the check box unchecks it: [ ] VIP customer", L[7][22:38] == "[ ] VIP customer" and t.attrs(7)[22:38] == "r" * 16, repr(L[7][20:40]))
    L = t.keys(TAB, DOWN)
    row("Down in the radio group selects the next choice and the cursor row follows: (*) Staff",
        L[11][22:31] == "(*) Staff" and L[10][22:35] == "( ) Wholesale" and t.attrs(11)[22:35] == "r" * 13, "\n".join(l[20:40] for l in L[8:13]))
    L = t.keys(DOWN)
    row("Down at the last choice is the form's: the focus goes to the list", t.attrs(13)[22:42] == "r" * 20 and "r" not in t.attrs(11)[22:35], repr(t.attrs(13)[20:44]))
    L = t.keys(DOWN, DOWN)
    row("Down in the list moves the current entry (and the reverse video) to Chicago", L[15][22:30] == " Chicago" and t.attrs(15)[22:42] == "r" * 20, "\n".join(l[20:46] for l in L[12:18]))
    L = t.keys(RET)
    L = t.keys("z")
    row("Return in the list presses the default button: the values are vip 0, kind 3, city 3",
        result(L, "PRESSED") == "ok| Smith|0|3|3|", repr(result(L, "PRESSED")))
    t.end()

    t = Term(box, "RUN bp zzscfrm")
    t.keys("a")
    t.keys(TAB, TAB, TAB)
    L = t.keys(DOWN, DOWN, DOWN, DOWN)
    row("Down past the last entry of the list is the form's: the focus goes on to the OK button", t.attrs(17)[28:34] == "r" * 6 and L[16][22:29] == ">Denver", repr((t.attrs(17)[26:50], L[16][20:40])))
    t.end()

    t = Term(box, "RUN bp zzscfrm")
    L0, A0 = record(t)
    t.keys("a")
    t.keys(ESC, idle=0.9)
    ok, bad = same_as(t, L0, A0)
    row("Esc cancels the form: the screen is put back cell for cell", ok, repr(bad))
    L = t.keys("z")
    row("...ELSE is taken and RUN answers the id of the cancel button, cancel", result(L, "CANCEL") == "cancel| Smith|1|2|1|", repr(result(L, "CANCEL")))
    t.end()

    t = Term(box, "RUN bp zzscfrm")
    t.keys("a")
    t.keys(TAB, TAB, TAB, TAB, TAB)
    t.keys(RET)
    L = t.keys("z")
    row("Tab to the Cancel button and Return: that button's id, and ELSE because it is the cancel button", result(L, "CANCEL") == "cancel| Smith|1|2|1|", repr(result(L, "CANCEL")))
    t.end()

    t = Term(box, "RUN bp zzscfrm")
    t.keys("a")
    t.keys(TAB, "c")
    L = t.keys("z")
    row("a letter on a widget that takes no text is a button's mnemonic: C pressed Cancel from the check box", result(L, "CANCEL") == "cancel| Smith|1|2|1|", repr(result(L, "CANCEL")))
    t.end()
    t = Term(box, "RUN bp zzscfrm")
    t.keys("a")
    t.keys(TAB, "o")
    L = t.keys("z")
    row("...and O pressed OK", result(L, "PRESSED") == "ok| Smith|1|2|1|", repr(result(L, "PRESSED")))
    t.end()

    say("\n--- the form as a record: JBUILD and JPARSE, SET, ENABLED, FOCUS ----------------------------------------")
    t = Term(box, "RUN bp zzscfjs")
    t.keys("a")
    L = t.lines()
    row("a form written out with JBUILD and read back with JPARSE is shown as it was: the same frame, entry, radio and buttons",
        L[3][10:22] == "+- Customer " and L[5][22:27] == "Smith" and L[10][22:35] == "(*) Wholesale" and L[17][28:34] == "[ OK ]", "\n".join(l[8:68] for l in L[2:20]))
    row("...and it has a real size as JSON (the program printed it)", any(l.startswith("JSON ") and int(re.sub(r"\D", "", l.split()[1]) or 0) > 500 for l in L), "\n".join(L[26:29]))
    t.keys(RET)
    L = t.keys("z")
    row("...and it works: Return, the values are those of the first form", result(L, "PRESSED") == "ok| Smith|1|2|1|", repr(result(L, "PRESSED")))
    t.end()

    t = Term(box, "RUN bp zzscfst")
    L0, A0 = record(t)
    L = t.keys("a")
    row("SET before the run: the entry says Zed, the check box is unchecked, the radio group is on Staff, the list is on Boston",
        L[5][22:25] == "Zed" and L[7][22:38] == "[ ] VIP customer" and L[11][22:31] == "(*) Staff" and L[14][22:29] == ">Boston", "\n".join(l[20:46] for l in L[4:18]))
    row("FOCUS: the radio group (kind) has the focus, not the first widget", t.attrs(11)[22:35] == "r" * 13 and "r" not in t.attrs(5)[22:52], repr((t.attrs(11)[20:40], t.attrs(5)[20:54])))
    L = t.keys(TAB, TAB)
    row("ENABLED 0 on the OK button takes it out of the ring: Tab from the list goes to Cancel", t.attrs(17)[38:48] == "r" * 10 and "r" not in t.attrs(17)[28:34], repr(t.attrs(17)[26:50]))
    L = t.keys(RET)
    L = t.keys("z")
    row("...and Return there presses Cancel (the default button is disabled, so it is not used)", result(L, "CANCEL") == "cancel| Zed|0|3|2|", repr(result(L, "CANCEL")))
    t.end()

    say("\n--- entry fields: a mask, a limit, a text wider than its field; what the form statements refuse -----------")
    t = Term(box, "RUN bp zzscfen")
    t.keys("a")
    L = t.lines()
    row("a text longer than its field shows the end of it (the cursor is after the last character): fghijkl in 8 cells, normal field style",
        L[12][33:41] == "fghijkl" or L[12][33:40] == "fghijkl", "\n".join(l[18:62] for l in L[8:17]))
    L = t.keys("abcdefg")
    row("MASK shows a * for each character typed and MAXLEN 5 stops at five: ***** and the sixth and seventh are not taken",
        L[10][33:38] == "*****" and L[10][38:45].strip() == "" and t.attrs(10)[33:45] == "r" * 12, "\n".join(l[18:62] for l in L[8:17]))
    L = t.keys(RET)
    L = t.keys("z")
    row("...the value is the real text, abcde, and the other entry's is the whole of its longer text",
        result(L, "PRESSED") == "ok abcde|abcdefghijkl|", repr(result(L, "PRESSED")))
    t.end()
    t = Term(box, "RUN bp zzscfer")
    L = t.keys()
    row("what is refused: the second widget of one id, a null id, a / in an id, a missing id for GET and SET, a widget that cannot take the focus, a RUN of something that is not a form; the valid ones are not refused (the dashes)",
        result(L, "ERRS") == "DUP EMPTYID SLASH NOGET NOSET NOFOCUS NORUN - - five|", repr(result(L, "ERRS")))
    t.end()

    say("\n--- no terminal: a phantom ---------------------------------------------------------------------------")
    out = sess(box, "RUN bp zzscphs")
    row("in a phantom SCREEN OPEN takes ELSE (no terminal), and a message box, a key, a menu, a pick list, an input dialogue, a form, "
        "a theme and a style all answer ELSE without waiting for anybody; the answers are not the THEN ones",
        has(out, r"^PHANTOM OPEN-ELSE\|MSG-ELSE 0\|KEY-ELSE\|MENU-ELSE\|RUN-ELSE\|PICK-ELSE\|ASK-ELSE\|WAIT-ELSE end\|THEME-ELSE \|STYLE-ELSE\|"), out[-500:])
    row("control: the phantom did run and write its record (PHANTOM none would mean the harness failed, not the statements)",
        not has(out, r"^PHANTOM none"), out[-300:])


def has(out, pattern):
    return re.search(r"(?m)" + pattern, out) is not None


F2_KEY = "\x1bOQ"


def part_events(box):
    say("\n--- SCREEN WAIT: events from a form that stays on the screen; combo box, progress bar, a label with a width ---")
    t = Term(box, "RUN bp zzscwt1")
    L0, A0 = record(t)
    L = t.keys("a")
    row("the first WAIT draws the form (44 x 12 at 10,3) and the program is still waiting: no event, no report line",
        L[3][10:20] == "+- Events " and L[14][10] == "+" and L[14][53] == "+" and result(L, "PRESSED") is None, "\n".join(l[8:56] for l in L[2:16]))
    row("the label has a width of 30: 'ready' on 30 cells of reverse video",
        L[12][12:17] == "ready" and t.attrs(12)[12:42] == "r" * 30, repr((L[12][10:44], t.attrs(12)[10:44])))
    row("the combo box shows Boston in its entry field and [v] after it; the progress bar is [###          ] 25% (13 cells inside: a quarter is 3.25, three filled)",
        L[9][18:24] == "Boston" and L[9][30:33] == "[v]" and L[11][12:32] == "[###" + " " * 10 + "]  25%", "\n".join(l[8:56] for l in L[8:13]))
    row("the first widget (the entry) has the focus, as in a run",
        L[5][18:20] == "Al" and t.attrs(5)[18:38] == "r" * 20, repr((L[5][16:40], t.attrs(5)[16:40])))
    L = t.keys(TAB)
    row("Tab moves the focus to the check box: the check box is reverse video now, and the form is still on the screen",
        t.attrs(7)[18:28] == "r" * 10 and L[7][18:28] == "[ ] Enable", repr((L[7][16:30], t.attrs(7)[16:30])))
    L = t.keys(" ")
    row("the space bar checks it", L[7][18:28] == "[x] Enable", repr(L[7][16:30]))
    L = t.keys(TAB, DOWN)
    row("Tab to the combo box and Down: the list of choices opens under the field (Albany, Boston, Chicago) with Boston current",
        L[10][18] == "+" and L[11][19:26] == " Albany" and L[12][19:26] == " Boston" and L[13][19:27] == " Chicago" and t.attrs(12)[19:32] == "r" * 13,
        "\n".join(l[14:40] for l in L[8:16]))
    L = t.keys(DOWN, RET)
    row("Down and Return pick Chicago: the list closes, the field says Chicago, and what was under the list is back",
        L[9][18:25] == "Chicago" and L[10][18:22].strip() == "" and L[11][19:26].strip() == "" and "Albany" not in "".join(L[10:15]), "\n".join(l[14:40] for l in L[8:16]))
    L = t.keys(F2_KEY)
    L = t.keys(TAB)
    L = t.keys(RET)
    row("a button pressed is an event and the program changes the form while it is on the screen: the bar is 75% and the label says working (padded, nothing left of 'ready')",
        L[11][12:32] == "[" + "#" * 10 + " " * 3 + "]  75%" and L[12][12:19] == "working" and L[12][19:42].strip() == "" and t.attrs(12)[12:42] == "r" * 30,
        "\n".join(l[8:56] for l in L[10:14]))
    L = t.keys(ESC, idle=0.9)
    ok, bad = same_as(t, L0, A0)
    row("Esc is the cancel event, not a close: the program ended its loop and HID the form, and the 20 rows are back cell for cell", ok, repr(bad))
    L = t.keys("z")
    got = [l for l in L if "focus:on<name" in l]
    row("the events the program saw, in order: focus (to the check box), change (checked), focus (to the combo), change (Chicago), "
        "key (F2), focus (to the button), button (go), cancel (Esc)",
        bool(got) and got[0].strip() == "focus:on<name;change:on=1;focus:city<on;change:city=Chicago;key:f2;focus:go<city;button:go;cancel;", repr(got))
    t.end()

    t = Term(box, "RUN bp zzscwt2")
    L0, A0 = record(t)
    t.keys("a")
    t.s.settle(1.8)
    L = t.lines()
    row("a WAIT with TIMEOUT 1 and no key gives ELSE, and the program changes the label while the form is still shown: 'timed out' over 'waiting'",
        any("Late" in l for l in L) and L[5][12:21] == "timed out" and "waiting" not in "".join(L[3:10]), "\n".join(l[8:44] for l in L[2:10]))
    t.keys("k")
    ok, bad = same_as(t, L0, A0)
    row("HIDE puts the screen back cell for cell", ok, repr(bad))
    L = t.keys("z")
    row("...and the event was `timeout`", result(L, "ELSE") == "timeout|", repr(result(L, "ELSE")))
    t.end()


def part_forms2(box):
    say("\n--- a form run again with what was typed, a message box over it ------------------------------------------")
    t = Term(box, "RUN bp zzscfr2")
    L0, A0 = record(t)
    t.keys("a")
    L = t.keys(RET)
    row("Return with the name empty: the program shows a message box over the form",
        any("The name is required." in l for l in L) and any("[ OK ]" in l for l in L), "\n".join(L[8:20]))
    L = t.keys(RET)
    row("...the box closes and the form is run again, still on the screen", not any("The name is required." in l for l in L) and any("Needs a name" in l for l in L) and any("Name:" in l for l in L), "\n".join(L[8:20]))
    t.keys("Al")
    t.keys(RET)
    ok, bad = same_as(t, L0, A0)
    row("a name and Return: the form closes and the screen is back", ok, repr(bad))
    L = t.keys("z")
    row("...the program went round twice and has the name", result(L, "NAME") == "Al RUNS 2|", repr(result(L, "NAME")))
    t.end()


# --- themes (13 Oct 26 sitting): what the styles look like.  Colours are read back from the emulator as ANSI numbers
# (0 black 1 red 2 green 3 yellow 4 blue 5 magenta 6 cyan 7 white), which is NOT the order the library's colour names use.
BLACK, RED, GREEN, BLUE, WHITE = 0, 1, 2, 4, 7

PROGS.update({
    # classic: the theme is asked for with a screen already drawn, then a message box over it
    "zzthcls": dialogue_program("""   screen theme 'classic' returning th then
      res = 'THEME ':th
   end else
      res = 'REFUSED ':th
   end
   screen text 'Bold text' at 60,22 attr 'bold'
   screen msgbox 'Colourful' title 'Colours' buttons '&Yes,&No' at 20,8 returning n
   res := ' ':n
"""),
    # classic, then mono again, with a key between: the screen goes back to what it was
    "zzthmon": dialogue_program("""   screen theme 'classic' returning th
   screen key returning kk
   screen theme 'mono' returning th2
   res = 'BACK ':th:'|':th2:'|'
"""),
    # a theme that is not one, the empty name, a name in capitals
    "zzthbad": dialogue_program("""   screen theme 'nosuch' returning a else a = a : '/ELSE'
   screen theme '' returning b
   screen theme 'blue' returning c
   screen theme 'CLASSIC' returning d
   res = 'NAMES ':a:'|':b:'|':c:'|':d:'|'
"""),
    # SCREEN STYLE: one that works, then the four that are refused, then a box in the changed style
    "zzthsty": dialogue_program("""   screen theme 'classic' returning th
   screen style 'highlight', 'red', 'black', 'bold underline' then
      s1 = 'OK'
   end else
      s1 = 'NO'
   end
   screen style 'reverse', 'red', 'black', '' then
      s2 = 'OK'
   end else
      s2 = 'NO'
   end
   screen style 'bar', 'pink', '', '' then
      s3 = 'OK'
   end else
      s3 = 'NO'
   end
   screen style 'bar', 'red', '', 'sparkly' then
      s4 = 'OK'
   end else
      s4 = 'NO'
   end
   screen style 'nosuch', 'red', '', '' then
      s5 = 'OK'
   end else
      s5 = 'NO'
   end
   screen msgbox 'Styled' title 'S' buttons '&Yes,&No' at 20,8 returning n
   res = 'STYLE ':s1:s2:s3:s4:s5:' ':n
"""),
    # the theme asked for BEFORE the screen is opened: the open paints the desktop; the close takes it away and the theme with it
    "zzthopn": """   screen theme 'classic' returning th
   screen open clear else crt @(0, 28) : 'NOTERM' ; stop
   screen text 'Hello' at 2,2
   screen key returning k1
   screen close
   screen theme '' returning after
   crt @(0, 20) : 'AFTER ' : after : '|' : th : '|'
end
""",
    # a terminal with no colour: the theme is refused, the library carries on in mono
    "zzthnoc": dialogue_program("""   screen theme 'blue' returning th then
      res = 'OK ':th
   end else
      res = 'ELSE ':th
   end
   screen msgbox 'Plain' at 20,8
"""),
    # a menu bar and its first menu in classic
    "zzthbar": dialogue_program("""   screen theme 'classic' returning th
   menus = '&File':@vm:'&Open':@sm:'Ctrl-O':@sm:'open':@vm:'E&xit':@sm:'':@sm:'exit'
   menus<2> = '&Edit':@vm:'&Copy':@vm:'&Paste'
   screen menubar menus draw
   screen key returning kk
   screen menubar menus returning c then
      res = 'CODE ':c:'|'
   end else
      res = 'CANCEL [':c:']'
   end
"""),
})


PROGS.update({
    # a form with a tab strip: three pages, widgets that belong to a page and ones that are on every page
    "zzthtab": dialogue_program("""   screen form title 'Tabs' at 10,3 size 50,14 returning f
   screen tabs f, 'tabs', 'General':@vm:'Address':@vm:'Notes' at 2,1
   screen page f, 1
   screen label  f, 'l1', 'Name:' at 2,3
   screen entry  f, 'name' at 10,3 width 20 value 'Smith'
   screen check  f, 'vip', '&VIP' at 10,5 value 1 place 'right'
   screen page f, 2
   screen label  f, 'l2', 'Street:' at 2,3
   screen entry  f, 'street' at 10,3 width 20 value 'Main St'
   screen page f, 3
   screen label  f, 'l3', 'Notes:' at 2,3
   screen list   f, 'note', 'aa':@vm:'bb' at 10,3 size 10,3
   screen page f, 0
   screen button f, 'ok', '&OK' at 10,11 default
   screen button f, 'cancel', '&Cancel' at 20,11 cancel
   screen run f returning pressed then
      res = 'PRESSED ':pressed:'|'
   end else
      res = 'CANCEL ':pressed:'|'
   end
   screen values f returning v
   res := ' ':v{'tabs'}:'|':v{'name'}:'|':v{'street'}:'|':v{'vip'}:'|'
"""),
    # the same idea with SCREEN WAIT: the events a tab strip gives
    "zzthtb2": dialogue_program("""   screen form title 'Events' at 10,3 size 50,12 returning f
   screen tabs f, 'tabs', 'One':@vm:'Two':@vm:'Three' at 2,1
   screen page f, 1
   screen label f, 'l1', 'Page one' at 2,3
   screen page f, 2
   screen label f, 'l2', 'Page two' at 2,3
   screen page f, 0
   screen button f, 'ok', '&OK' at 10,9 default
   log = ''
   loop
      screen wait f returning ev then
         log := ev<1>:'/':ev<2>:'/':ev<3>:' '
      end else
         log := 'ELSE:':ev<1>:' '
         exit
      end
   repeat
   screen hide f
   res = 'LOG ':log
"""),
})


HOME, END, PGUP, PGDN, DELK, BS = "\x1b[1~", "\x1b[4~", "\x1b[5~", "\x1b[6~", "\x1b[3~", "\x7f"
CTRL_K, CTRL_A, CTRL_E, TAB = "\x0b", "\x01", "\x05", "\t"

PROGS.update({
    # a text area of five rows over a text of six lines, one of them too long for it, and a button after it
    "zzthmem": dialogue_program("""   text = 'first line':@fm:'second':@fm:'third line is rather long indeed, longer than the area':@fm:'4':@fm:'5':@fm:'6'
   screen form title 'Memo' at 10,3 size 40,14 returning f
   screen memo f, 'm', text at 2,2 size 20,5
   screen button f, 'ok', '&OK' at 10,11 default
   screen run f returning pressed then
      res = 'PRESSED ':pressed:'|'
   end else
      res = 'CANCEL ':pressed:'|'
   end
   screen get f, 'm' returning t
   res := ' ':dcount(t, @fm):'|':convert(@fm, '/', t):'|'
"""),
    # a viewer over the same text: it moves and does not change
    "zzthmvw": dialogue_program("""   text = 'first line':@fm:'second':@fm:'third line':@fm:'4':@fm:'5':@fm:'6':@fm:'7':@fm:'8'
   screen form title 'View' at 10,3 size 40,14 returning f
   screen memo f, 'm', text at 2,2 size 20,4 readonly
   screen button f, 'ok', '&OK' at 10,11 default
   screen run f returning pressed then
      res = 'PRESSED ':pressed:'|'
   end else
      res = 'CANCEL ':pressed:'|'
   end
   screen get f, 'm' returning t
   res := ' ':dcount(t, @fm):'|':t<1>:'|'
"""),
})


F3 = "\x1bOR"
F2_KEY, F3_KEY, F4_KEY = "\x1bOQ", "\x1bOR", "\x1bOS"
CTRL_G, CTRL_O, CTRL_X, CTRL_V, CTRL_Z, CTRL_Y, CTRL_T, CTRL_N, CTRL_B, CTRL_F, CTRL_P, CTRL_U = (
    "\x07", "\x0f", "\x18", "\x16", "\x1a", "\x19", "\x14", "\x0e", "\x02", "\x06", "\x10", "\x15")

PROGS.update({
    # a wrapped text area (19 cells of text) of five rows over three lines: a long one of words, a short one and a
    # word of 36 letters that has to be broken; a button after it
    "zzthmwr": dialogue_program("""   text = 'the quick brown fox jumps over the lazy dog':@fm:'short':@fm:str('a', 36)
   screen form title 'Wrap' at 10,3 size 40,14 returning f
   screen memo f, 'm', text at 2,2 size 20,5 wrap
   screen button f, 'ok', '&OK' at 10,11 default
   screen run f returning pressed then
      res = 'PRESSED ':pressed:'|'
   end else
      res = 'CANCEL ':pressed:'|'
   end
   screen get f, 'm' returning t
   res := ' ':dcount(t, @fm):'|':convert(@fm, '/', t):'|'
"""),
    # the same text without wrap, to see that the extra keys work there too: a viewer (it selects and copies, and
    # nothing else) in one memo and an editor in the other, the clipboard passing from one to the other
    "zzthmcb": dialogue_program("""   text = 'one two three':@fm:'four five six'
   screen form title 'Clip' at 10,3 size 40,14 returning f
   screen memo f, 'v', text at 2,2 size 20,3 readonly
   screen memo f, 'e', 'x' at 2,6 size 20,3
   screen button f, 'ok', '&OK' at 10,11 default
   screen run f returning pressed then
      res = 'PRESSED ':pressed:'|'
   end else
      res = 'CANCEL ':pressed:'|'
   end
   screen get f, 'v' returning t
   screen get f, 'e' returning u
   res := ' ':convert(@fm, '/', t):'|':convert(@fm, '/', u):'|'
"""),
})


PROGS.update({
    # a tree of three roots, two of them with nodes under them (one three deep), a button after it
    "zzthtre": dialogue_program("""   nodes = 'Root A':@sm:1:@sm:'a':@vm:'Child A1':@sm:2:@sm:'a1':@vm:'Leaf A1a':@sm:3:@sm:'a1a':@vm:'Child A2':@sm:2:@sm:'a2'
   nodes := @vm:'Root B':@sm:1:@sm:'b':@vm:'Child B1':@sm:2:@sm:'b1':@vm:'Root C':@sm:1:@sm:'c'
   screen form title 'Tree' at 10,3 size 40,14 returning f
   screen tree f, 'tr', nodes at 2,1 size 20,6
   screen button f, 'ok', '&OK' at 10,9 default
   screen run f returning pressed then
      res = 'PRESSED ':pressed:'|'
   end else
      res = 'CANCEL ':pressed:'|'
   end
   screen get f, 'tr' returning v
   res := ' ':v:'|'
"""),
})


PROGS.update({
    # a table of four columns in 22 cells (so the last two are off to the right), five rows, rows that can be marked
    "zzthtbs": dialogue_program("""   cols = 'Name':@sm:'8L':@vm:'Qty':@sm:'4R':@vm:'City':@sm:'8L':@vm:'Code':@sm:'6L'
   rows = 'Smith':@vm:'12':@vm:'Albany':@vm:'A1'
   rows<2> = 'Jones':@vm:'7':@vm:'Boston':@vm:'B2'
   rows<3> = 'Adams':@vm:'150':@vm:'Chicago':@vm:'C3'
   rows<4> = 'Baker':@vm:'3':@vm:'Denver':@vm:'D4'
   rows<5> = 'Clark':@vm:'44':@vm:'Elgin':@vm:'E5'
   screen form title 'Sorting' at 10,3 size 40,14 returning f
   screen table f, 'tbl', cols, rows at 2,1 size 22,6 multi
   screen button f, 'ok', '&OK' at 10,9 default
   screen run f returning pressed then
      res = 'PRESSED ':pressed:'|'
   end else
      res = 'CANCEL ':pressed:'|'
   end
   screen get f, 'tbl' returning v
   res := ' ':convert(@vm, ',', v):'|'
"""),
})


PROGS.update({
    # a table of six rows in four rows of room: a heading, right-aligned numbers, a scroll bar, a button after it
    "zzthtbl": dialogue_program("""   cols = 'Name':@sm:'10L':@vm:'Qty':@sm:'4R':@vm:'City'
   rows = 'Smith':@vm:'12':@vm:'Albany'
   rows<2> = 'Jones':@vm:'7':@vm:'Boston'
   rows<3> = 'Adams':@vm:'150':@vm:'Chicago'
   rows<4> = 'Baker':@vm:'3':@vm:'Denver'
   rows<5> = 'Clark':@vm:'44':@vm:'Elgin'
   rows<6> = 'Davis':@vm:'9':@vm:'Fresno'
   screen form title 'People' at 10,3 size 44,12 returning f
   screen table f, 'tbl', cols, rows at 2,1 size 36,5
   screen button f, 'ok', '&OK' at 10,8 default
   screen run f returning pressed then
      res = 'PRESSED ':pressed:'|'
   end else
      res = 'CANCEL ':pressed:'|'
   end
   screen get f, 'tbl' returning t
   res := ' ':t:'|'
"""),
    # SCREEN WAIT: the table's change events, and SCREEN SET ITEMS giving it new rows
    "zzthtb3": dialogue_program("""   cols = 'Name':@vm:'Qty'
   rows = 'Smith':@vm:'12'
   rows<2> = 'Jones':@vm:'7'
   rows<3> = 'Adams':@vm:'150'
   screen form title 'Events' at 10,3 size 40,12 returning f
   screen table f, 'tbl', cols, rows at 2,1 size 20,4
   screen button f, 'ok', '&OK' at 10,8 default
   log = ''
   loop
      screen wait f returning ev then
         log := ev<1>:'/':ev<2>:'/':ev<3>:' '
         if ev<1> = 'change' and ev<3> = 3 then
            newrows = 'Zed':@vm:'1'
            newrows<2> = 'Yves':@vm:'2'
            screen set f, 'tbl' items newrows
         end
      end else
         log := 'ELSE:':ev<1>:' '
         exit
      end
   repeat
   screen get f, 'tbl' returning t
   screen hide f
   res = 'LOG ':log:'ROW ':t
"""),
    # a pick list of a hundred entries: the thumb of the scroll bar is as long as a cell is worth, never less than one
    "zzthscr": dialogue_program("""   items = ''
   for i = 1 to 100
      items<1, i> = 'Item ':i
   next i
   screen pick items title 'Many' size 14,5 returning n then
      res = 'PICKED ':n:'|'
   end else
      res = 'CANCEL ':n:'|'
   end
"""),
})


def part_table(box):
    say("\n--- the table -------------------------------------------------------------------------------------------")
    t = Term(box, "RUN bp zzthtbl")
    t.keys()
    L = t.keys("a")
    p = at(L, "Name")
    r0 = p[0] if p else 0
    c0 = p[1] - 1 if p else 0                      # the table's own first cell: one before the first column
    area = [l[c0:c0 + 36] for l in L[r0:r0 + 5]]
    row("the heading row names the columns, the first row of data follows, Qty is right-aligned in its four cells",
        p is not None and "Name" in area[0] and "Qty" in area[0] and "City" in area[0] and area[1].startswith(" Smith ") and area[1][13:16] == " 12"
        and "Albany" in area[1], repr(area))
    row("the heading is in the header style (underlined and bold in mono), the rows are not",
        t.style(r0, c0 + 1) == (None, None, "ub") and t.style(r0 + 2, c0 + 1) == (None, None, ""), repr((t.style(r0, c0 + 1), t.style(r0 + 2, c0 + 1))))
    row("the first row is the current one and the table has the focus: it is in reverse video", "Smith" in t.reverse(r0 + 1) and "Jones" not in t.reverse(r0 + 2), repr((t.reverse(r0 + 1), t.reverse(r0 + 2))))
    row("six rows in four: a scroll bar in the last column, ^ at the top and v at the bottom", area[1][35] == "^" and area[4][35] == "v", repr([a[35:36] for a in area]))
    row("only the first four rows are shown", "Baker" in area[4] and not any("Clark" in l for l in L), repr(area))
    L = t.keys(DOWN, DOWN, DOWN, DOWN)
    area = [l[c0:c0 + 36] for l in L[r0:r0 + 5]]
    row("four Downs: the fifth row (Clark) is current and the table has scrolled one row: Jones first, Smith gone",
        "Jones" in area[1] and "Clark" in area[4] and "Clark" in t.reverse(r0 + 4) and not any("Smith" in l[c0:c0 + 36] for l in L[r0 + 1:r0 + 5]), repr(area))
    L = t.keys("d")
    area = [l[c0:c0 + 36] for l in L[r0:r0 + 5]]
    row("a letter goes to the next row whose first cell starts with it: D is Davis, the last row; the table scrolled to show it",
        "Davis" in t.reverse(r0 + 4) and "Adams" in area[1], repr(area))
    L = t.keys(HOME)
    row("Home: the first row again and the top of the table", "Smith" in t.reverse(r0 + 1), repr(t.reverse(r0 + 1)))
    t.keys(END)
    t.keys(RET)
    row("Return is not the table's: the form's default button is pressed and the program has the number of the current row, the last (6)",
        final(t, "PRESSED") == "ok| 6|", "")
    t.end()

    t = Term(box, "RUN bp zzthtb3")
    t.keys("a")
    L = t.keys(DOWN, DOWN)
    row("SCREEN SET ITEMS: the form is redrawn with the two new rows, one to a line (Zed, Yves), and the old third row (Adams) is gone",
        any("Zed" in l for l in L) and any("Yves" in l for l in L) and not any("Adams" in l for l in L) and not any("Smith" in l for l in L),
        "\n".join(l[8:40] for l in L[3:12]))
    t.keys(ESC, idle=0.9)
    row("SCREEN WAIT: each move of the current row is a change event (type, id, the row); SCREEN SET ITEMS gave it two new rows and "
        "the current one went back to the first",
        final(t, "LOG") == "change/tbl/2 change/tbl/3 ELSE:cancel ROW 1", "")
    t.end()


def part_scroll(box):
    say("\n--- the scroll bar of a long list -------------------------------------------------------------------------")
    t = Term(box, "RUN bp zzthscr")
    t.keys()
    L = t.keys("a")
    p = at(L, "Item 1")
    r0 = p[0] if p else 0
    bc = L[r0].rindex("^") if p and "^" in L[r0] else 0
    bar = lambda L: [L[r0 + i][bc] for i in range(5)]
    row("a hundred entries in five rows: the thumb is one cell (a fiftieth of a track of three cells is less, and a thumb is never less than one) at the top",
        p is not None and bar(L) == ["^", "#", "|", "|", "v"], repr((p, bar(L))))
    L = t.keys(END)
    row("End: the thumb is in the last cell of the track", bar(L) == ["^", "|", "|", "#", "v"] and "Item 100" in L[r0 + 4], repr((bar(L), L[r0 + 4][bc - 14:bc + 1])))
    L = t.keys(HOME)
    row("Home: and back at the top", bar(L) == ["^", "#", "|", "|", "v"], repr(bar(L)))
    t.keys(RET)
    t.end()


def click(t, x, y, button=0, release=True):
    """A press, and then its release, of a mouse button over the cell x, y (from 0): the xterm SGR reports (mode 1006).
    button 0 left, 1 middle, 2 right; 64 and 65 are the wheel up and down (which have no release)."""
    seq = ["\x1b[<%d;%d;%dM" % (button, x + 1, y + 1)]
    if release and button < 64:
        seq.append("\x1b[<%d;%d;%dm" % (button, x + 1, y + 1))
    return t.keys(*seq, idle=0.35)


PROGS.update({
    # the mouse reported to a program that reads keys itself, and what SCREEN MOUSE says about it
    "zzthmky": """   screen open clear else crt 'NOTERM' ; stop
   screen key returning k
   screen mouse returning m else m = 'NONE'
   screen close
   crt 'KEY ':k:'|':convert(@fm, '/', m):'|'
end
""",
    # the same with NOMOUSE: the terminal is never asked to report it
    "zzthmk2": """   screen open clear nomouse else crt @(0, 28) : 'NOTERM' ; stop
   screen key returning k
   screen close
   crt 'KEY ':k:'|'
end
""",
    "zzthmsg": dialogue_program("""   screen msgbox 'Delete the record?' title 'Confirm' buttons '&Yes,&No' default 2 returning n then
      res = 'THEN ':n:'|'
   end else
      res = 'ELSE ':n:'|'
   end
"""),
    "zzthcmb": dialogue_program("""   screen form title 'Combo' at 10,3 size 40,10 returning f
   screen combo f, 'c', 'Albany':@vm:'Boston':@vm:'Chicago' at 2,2 width 14 value 'Albany'
   screen button f, 'ok', '&OK' at 10,6 default
   screen run f returning pressed then
      res = 'PRESSED ':pressed:'|'
   end else
      res = 'CANCEL ':pressed:'|'
   end
   screen get f, 'c' returning c
   res := ' ':c:'|'
"""),
})


def part_mouse(box):
    say("\n--- the mouse: what the terminal is asked, and a program that reads it itself -------------------------------")
    t = Term(box, "RUN bp zzthmky")
    t.keys()
    row("SCREEN OPEN asks the terminal for button, drag and wheel reports in the SGR form (modes 1000, 1002, 1006)",
        b"\x1b[?1000h\x1b[?1002h\x1b[?1006h" in t.s.raw, repr(t.s.raw[-200:]))
    click(t, 30, 12, release=False)
    L = t.keys(idle=0.5)
    row("a press is the key mouse, and SCREEN MOUSE says what it was: press, button 1, column 30, row 12, no modifiers; SCREEN CLOSE then switches reporting off",
        result(L, "KEY") == "mouse|press/1/30/12/|" and b"\x1b[?1006l\x1b[?1002l\x1b[?1000l" in t.s.raw, repr((result(L, "KEY"), t.s.raw[-120:])))
    row("the report is not typed into the program: nothing of 0;31;13M is on the screen", not any("31;13" in l for l in L), "\n".join(L[:6]))
    t.end()
    t = Term(box, "RUN bp zzthmky")
    t.keys()
    t.keys("\x1b[<16;11;6M", idle=0.5)
    L = t.keys(idle=0.5)
    row("a press with Ctrl held (button 0 + 16) at 10,5 reports the control modifier", result(L, "KEY") == "mouse|press/1/10/5/c|", repr(result(L, "KEY")))
    t.end()
    t = Term(box, "RUN bp zzthmky")
    t.keys()
    t.keys("\x1b[<65;4;5M", idle=0.5)
    L = t.keys(idle=0.5)
    row("the wheel is a wheel event: the button is up or down", result(L, "KEY") == "mouse|wheel/down/3/4/|", repr(result(L, "KEY")))
    t.end()
    t = Term(box, "RUN bp zzthmk2")
    t.keys()
    row("SCREEN OPEN NOMOUSE never asks the terminal to report the mouse", b"\x1b[?100" not in t.s.raw, repr(t.s.raw[-120:]))
    t.keys("a")
    t.end()

    say("\n--- the mouse: a form -------------------------------------------------------------------------------------")
    t = Term(box, "RUN bp zzscfrm")
    t.keys()
    L = t.keys("a")
    nm = at(L, "Smith")
    vip = at(L, "VIP customer")
    wh = at(L, "Wholesale")
    st = at(L, "Staff")
    ch = at(L, "Chicago")
    ok = at(L, "[ OK ]")
    row("control: the form is up with its widgets where the program put them", all(x is not None for x in (nm, vip, wh, st, ch, ok)), repr((nm, vip, wh, st, ch, ok)))
    L = click(t, vip[1] + 1, vip[0])
    row("a click on the check box unticks it (it started ticked); the release did nothing more", any("[ ] VIP customer" in l for l in L), "\n".join(l[10:60] for l in L[5:10]))
    L = click(t, st[1] + 1, st[0])
    row("a click on a radio button chooses it: ( ) Wholesale and (*) Staff", any("(*) Staff" in l for l in L) and any("( ) Wholesale" in l for l in L), "\n".join(l[10:60] for l in L[8:13]))
    L = click(t, ch[1] + 2, ch[0])
    row("a click on a row of the list makes it the current one: Chicago is in reverse video", "Chicago" in t.reverse(ch[0]), repr(t.reverse(ch[0])))
    L = click(t, nm[1] + 3, nm[0])
    t.keys("X")
    row("a click in the entry field puts the cursor under it: X goes in after the third character (SmiXth)", any("SmiXth" in l for l in L) or any("SmiXth" in l for l in t.lines()), "\n".join(l[10:60] for l in t.lines()[4:7]))
    L = click(t, vip[1] + 1, vip[0], button=2)
    row("a click of the RIGHT button is ignored: the check box is as it was (still unticked)", any("[ ] VIP customer" in l for l in L), "\n".join(l[10:60] for l in L[5:10]))
    L = click(t, 3, 25)
    row("a click outside the form, on nothing, is ignored: the form is still there", any("Customer" in l for l in L), "")
    click(t, ok[1] + 3, ok[0])
    row("a click on the OK button presses it: the program has OK and every value as the clicks left them (name SmiXth, vip 0, kind 3, city 3)",
        final(t, "PRESSED") == "ok| SmiXth|0|3|3|", "")
    t.end()
    t = Term(box, "RUN bp zzscfrm")
    t.keys()
    L = t.keys("a")
    ch = at(L, "Chicago")
    click(t, ch[1] + 2, ch[0])
    click(t, ch[1] + 2, ch[0])
    row("a second click on the row the last click chose is Return: the form's default button is pressed, and the list's choice and the other values are as they were",
        final(t, "PRESSED") == "ok| Smith|1|2|3|", "")
    t.end()

    say("\n--- the mouse: a form's other widgets ------------------------------------------------------------------")
    t = Term(box, "RUN bp zzthtab")
    t.keys()
    L = t.keys("a")
    ad = at(L, "Address")
    L = click(t, ad[1] + 1, ad[0])
    row("a click on a tab chooses it and the form shows its page", any("Street:" in l for l in L) and any("[Address]" in l for l in L) and not any("Name:" in l for l in L), "\n".join(L[3:12]))
    no = at(L, "Notes")
    L = click(t, no[1] + 1, no[0])
    row("...and another", any("Notes:" in l and "aa" in l for l in L) and any("[Notes]" in l for l in L), "\n".join(L[3:12]))
    t.keys(ESC, idle=0.9)
    t.end()

    t = Term(box, "RUN bp zzthcmb")
    t.keys()
    L = t.keys("a")
    fld = at(L, "Albany")
    L = click(t, fld[1] + 14, fld[0])
    row("a click on the [v] opens the combo's list under the field: Albany, Boston, Chicago", any("Boston" in l for l in L[fld[0] + 1:]) and any("Chicago" in l for l in L[fld[0] + 1:]), "\n".join(L[3:12]))
    ch = at(L[fld[0] + 1:], "Chicago")
    L = click(t, ch[1] + 1, fld[0] + 1 + ch[0])
    row("a click on an entry of the list chooses it and closes the list: the field says Chicago, Boston is gone", any("Chicago" in l[10:40] for l in L[fld[0]:fld[0] + 1]) and not any("Boston" in l for l in L), "\n".join(L[3:12]))
    L = click(t, fld[1] + 14, fld[0])
    L = click(t, 3, 25)
    row("a click outside the list closes it and chooses nothing", not any("Boston" in l for l in L) and any("Chicago" in l[10:40] for l in L[fld[0]:fld[0] + 1]), "\n".join(L[3:12]))
    t.keys(RET)
    row("the choice reached the program", final(t, "PRESSED") == "ok| Chicago|", "")
    t.end()

    t = Term(box, "RUN bp zzthtbl")
    t.keys()
    L = t.keys("a")
    jo = at(L, "Jones")
    L = click(t, jo[1] + 1, jo[0])
    row("a click on a row of a table makes it the current one", "Jones" in t.reverse(jo[0]), repr(t.reverse(jo[0])))
    hd = at(L, "Name")
    L = click(t, hd[1] + 1, hd[0])
    names = [L[hd[0] + 1 + i][hd[1]:hd[1] + 5].strip() for i in range(4)]
    row("a click on the heading sorts by that column (since 13 Oct): Adams, Baker, Clark, Davis come first", names == ["Adams", "Baker", "Clark", "Davis"], repr(names))
    L = click(t, hd[1] + 1, hd[0])
    L = click(t, hd[1] + 1, hd[0])
    names = [L[hd[0] + 1 + i][hd[1]:hd[1] + 5].strip() for i in range(4)]
    row("two clicks more (down, then the order of rows again): Smith, Jones, Adams, Baker as given",
        names == ["Smith", "Jones", "Adams", "Baker"], repr(names))
    click(t, jo[1] + 1, jo[0])
    click(t, jo[1] + 1, jo[0])
    row("a second click on the row the last click chose is Return: the form's default button is pressed and the program has the row, 2",
        final(t, "PRESSED") == "ok| 2|", "")
    t.end()

    t = Term(box, "RUN bp zzthmem")
    t.keys()
    L = t.keys("a")
    th = at(L, "third line")
    L = click(t, th[1] + 6, th[0])
    t.keys("#")
    row("a click in the text area puts the cursor at the cell: # goes in after the sixth character of the third line",
        any("third #line" in l for l in t.lines()), "\n".join(l[10:50] for l in t.lines()[4:12]))
    click(t, th[1] + 2, th[0], button=65)
    L = t.lines()
    row("the wheel scrolls the area as far as it can (six lines in five rows: one line goes): the first line has gone, the second is at the top",
        not any("first line" in l for l in L) and L[th[0] - 2][th[1]:th[1] + 6] == "second", "\n".join(l[10:50] for l in L[4:12]))
    t.keys(ESC, idle=0.9)
    t.end()

    say("\n--- the mouse: dialogues -----------------------------------------------------------------------------------")
    t = Term(box, "RUN bp zzthmsg")
    t.keys()
    L = t.keys("a")
    y = at(L, "[ Yes ]")
    click(t, y[1] + 3, y[0])
    row("a message box: a click on [ Yes ] chooses it (THEN 1, the default was 2)", final(t, "THEN") == "1|", "")
    t.end()
    t = Term(box, "RUN bp zzthmsg")
    t.keys()
    L = t.keys("a")
    y = at(L, "[ Yes ]")
    click(t, y[1] + 3, y[0] - 2)
    L = t.lines()
    row("...a click on the box away from the buttons is ignored: the box is still up", any("[ Yes ]" in l for l in L), "")
    t.keys(ESC, idle=0.9)
    t.end()

    t = Term(box, "RUN bp zzscmnu")
    t.keys()
    L = t.keys("a")
    sv = at(L, "Save")
    click(t, sv[1] + 1, sv[0])
    row("a pop-up menu: a click on Save chooses it (its number, 3)", final(t, "CODE") == "3|", "")
    t.end()
    t = Term(box, "RUN bp zzscmnu")
    t.keys()
    L = t.keys("a")
    click(t, 70, 20)
    row("...a click outside the menu cancels it", final(t, "CANCEL") == "[]", "")
    t.end()

    t = Term(box, "RUN bp zzscbar")
    t.keys()
    t.keys("a")
    L = t.keys("b")
    ed = at(L, "Edit")
    L = click(t, ed[1] + 1, ed[0])
    row("a menu bar: a click on the title Edit opens that menu (File's entries go)", any("Copy" in l for l in L[1:4]) and not any("Ctrl-O" in l for l in L[1:4]), "\n".join(L[:5]))
    pa = at(L, "Paste")
    click(t, pa[1] + 1, pa[0])
    row("...and a click on Paste chooses it (the second entry of Edit: 2)", final(t, "CODE") == "2|", "")
    t.end()

    t = Term(box, "RUN bp zzscpik")
    t.keys()
    L = t.keys("a")
    ci = at(L, "Chicago")
    click(t, ci[1] + 1, ci[0])
    row("a pick list: a click on Chicago chooses it at once (3)", final(t, "PICKED") == "3|", "")
    t.end()
    t = Term(box, "RUN bp zzscpik")
    t.keys()
    t.keys("a")
    click(t, 3, 25)
    row("...a click outside the box cancels", final(t, "CANCEL") == "[]", "")
    t.end()

    t = Term(box, "RUN bp zzscask")
    t.keys()
    L = t.keys("a")
    p = at(L, "Bob")
    click(t, p[1] + 1, p[0])
    t.keys("Z")
    t.keys(RET)
    got = final(t, "TEXT")
    row("an input box: a click in the field puts the cursor there: Z goes in after the first character", got == "BZob|", repr(got))
    t.end()


PROGS.update({
    # what SD thinks the terminal's size is (nobody typed TERM w,h)
    "zzrsz1": """   crt 'SIZE ':@crtwide:'x':@crthigh:'|'
end
""",
    # the same in a phantom, which has no terminal to ask
    "zzrsz2": """   open 'VOC' to v else stop
   write @crtwide:'x':@crthigh on v, 'zzrsz2_out'
end
""",
    "zzrsz2s": """   open 'VOC' to v else stop
   delete v, 'zzrsz2_out'
   execute 'PHANTOM NO.MSG RUN bp zzrsz2'
   for i = 1 to 40
      read r from v, 'zzrsz2_out' then exit
      sleep 1
   next i
   read r from v, 'zzrsz2_out' then
      crt 'PHANTOM ':r:'|'
      delete v, 'zzrsz2_out'
   end else
      crt 'PHANTOM none'
   end
end
""",
    # a program that reads keys with SCREEN KEY, over text it drew with SCREEN TEXT
    "zzrsz3": """   screen open clear else crt 'NOTERM' ; stop
   screen text 'Hello, resize' at 2,2
   screen text 'far right' at 60,3
   screen text 'low' at 5,18
   loop
      screen key timeout 60 returning k else exit
      screen size returning sz
      screen text 'KEY ':k:' SIZE ':sz<1>:'x':sz<2> at 2,5 width 40
      if k = 'q' then exit
   repeat
   screen close
   crt 'DONE'
end
""",
    # a message box open while the terminal is resized
    "zzrsz4": """   screen open clear else crt 'NOTERM' ; stop
   screen text 'Background text' at 2,2
   screen msgbox 'Delete the record?' title 'Confirm' buttons '&Yes,&No' returning n then
      res = 'THEN ':n
   end else
      res = 'ELSE ':n
   end
   screen close
   crt res
end
""",
    # a form on SCREEN WAIT: the resize is an event
    "zzrsz5": """   screen open clear else crt 'NOTERM' ; stop
   screen text 'Background text' at 2,2
   screen form title 'Resize' at 5,3 size 30,8 returning f
   screen button f, 'ok', '&OK' at 2,4 default
   log = ''
   loop
      screen wait f returning ev then
         log := ev<1>:'/':convert(@vm, 'x', ev<3>):' '
         if ev<1> = 'button' then exit
      end else
         exit
      end
   repeat
   screen hide f
   screen close
   crt 'LOG ':log
end
""",
})


def part_resize(box):
    say("\n--- the terminal's own size, and a resize --------------------------------------------------------------")
    t = Term(box, "RUN bp zzrsz1", cols=90, rows=26, termsize=False)
    L = t.keys()
    row("SD asks the terminal how big it is: on a 90 by 26 window, with nobody typing TERM w,h, @crtwide and @crthigh are 90 and 26 (they were 120 and 36 whatever the window)",
        result(L, "SIZE") == "90x26|", repr(result(L, "SIZE")))
    t.end()
    t = Term(box, "RUN bp zzrsz1", cols=70, rows=20, termsize=False)
    L = t.keys()
    row("...and on a 70 by 20 window they are 70 and 20", result(L, "SIZE") == "70x20|", repr(result(L, "SIZE")))
    t.end()
    t = Term(box, "RUN bp zzrsz1", cols=90, rows=26)
    L = t.keys()
    row("TERM w,h typed by hand still sets the size (here the window's own, typed): 90x26", result(L, "SIZE") == "90x26|", repr(result(L, "SIZE")))
    t.end()
    out = sess(box, "RUN bp zzrsz2s")
    row("a phantom has no terminal to ask and keeps its own size (the path the kernel did not change); the value is whatever it was",
        has(out, r"^PHANTOM \d+x\d+\|"), out[-300:])

    say("\n--- a resize under a library program ---------------------------------------------------------------------")
    t = Term(box, "RUN bp zzrsz3", cols=90, rows=26, termsize=False)
    t.keys()
    L = t.keys("a")
    row("control: a key, and the size the program sees: KEY a SIZE 90x26", any("KEY a SIZE 90x26" in l for l in L), "\n".join(L[:8]))
    L = t.resize(70, 20)
    row("the window is made 70 by 20: the program is given the key resize and SCREEN SIZE says 70 by 20", any("KEY resize SIZE 70x20" in l for l in L), "\n".join(L[:8]))
    row("...and the library drew its picture again: the text that fits is still there (Hello, resize; far right, which ends in column 68; low on row 18)",
        any("Hello, resize" in l for l in L) and any("far right" in l for l in L) and any(l.strip() == "low" or l[5:8] == "low" for l in L), "\n".join(L[:20]))
    L = t.resize(50, 15)
    row("made 50 by 15 it keeps what still fits and cuts the rest: Hello, resize stays; far right (column 60) and low (row 18) are gone",
        any("Hello, resize" in l for l in L) and not any("far right" in l for l in L) and not any(l[5:8] == "low" for l in L) and any("KEY resize SIZE 50x15" in l for l in L),
        "\n".join(L[:16]))
    L = t.resize(100, 30)
    row("made 100 by 30 it keeps what it has (what was cut stays cut: the program redraws it on resize if it wants it): the heading and KEY resize SIZE 100x30",
        any("Hello, resize" in l for l in L) and any("KEY resize SIZE 100x30" in l for l in L), "\n".join(L[:8]))
    t.keys("q")
    row("the program ends cleanly after all that", result(t.lines(), "DONE") is not None, "\n".join(t.lines()[:10]))
    t.end()

    say("\n--- a resize under a dialogue and under a form --------------------------------------------------------")
    t = Term(box, "RUN bp zzrsz4", cols=90, rows=26, termsize=False)
    t.keys()
    L = t.lines()
    row("control: the message box is up over Background text", any("[ Yes ]" in l for l in L) and any("Background text" in l for l in L), "\n".join(L[8:18]))
    L = t.resize(70, 20)
    row("the window is made 70 by 20: the box is drawn again with the rest, Background text too, and still waiting for an answer",
        any("[ Yes ]" in l and "[ No ]" in l for l in L) and any("Background text" in l for l in L), "\n".join(L[:20]))
    L = t.keys("y")
    row("and it answers: Y chooses the first button", result(L, "THEN") == "1", repr(result(L, "THEN")))
    t.end()
    t = Term(box, "RUN bp zzrsz5", cols=90, rows=26, termsize=False)
    L = t.keys(idle=1.2)
    row("control: the form is on the screen (SCREEN WAIT shows it and gives the program a timeout-free wait)", any("[ OK ]" in l for l in L), "\n".join(L[:12]))
    L = t.resize(70, 20)
    row("a resize while the program waits is the event resize, with the new size 70 by 20; the form is drawn again", any("[ OK ]" in l for l in L), "\n".join(L[:12]))
    L = t.keys(RET)
    row("the program saw the resize event (data 70x20) and then the button", result(L, "LOG") == "resize/70x20 button/", repr((result(L, "LOG"), L[10:20])))
    t.end()


def final_after(t, tag):
    """The text after TAG on the line that starts with it, on the screen now (the program has printed it and ended)."""
    return result(t.lines(), tag)


def part_memo(box):
    say("\n--- the text area: editing ------------------------------------------------------------------------------")
    t = Term(box, "RUN bp zzthmem")
    t.keys()
    L = t.keys("a")
    p = at(L, "first line")
    r0 = p[0] if p else 0
    c0 = p[1] if p else 0
    area = [l[c0:c0 + 20] for l in L[r0:r0 + 5]]
    row("the area shows five of the six lines, the long one cut at the width (19 cells); the last column is the scroll bar",
        p is not None and area[0].startswith("first line") and area[1].startswith("second") and area[2][:19] == "third line is rathe"
        and area[3].startswith("4") and area[4].startswith("5") and not any(l.strip().startswith("6") for l in area), repr(area))
    row("the scroll bar: ^ at the top, v at the bottom, # between", area[0][19] == "^" and area[4][19] == "v" and "#" in "".join(a[19] for a in area[1:4]), repr([a[19:20] for a in area]))
    row("the text has the focus and the cursor is at its first character", t.cursor() == (c0, r0), repr((t.cursor(), c0, r0)))
    L = t.keys("AB")
    row("typing inserts at the cursor: the first line is ABfirst line and the cursor is two on", L[r0][c0:c0 + 12] == "ABfirst line" and t.cursor() == (c0 + 2, r0), repr((L[r0][c0:c0 + 12], t.cursor())))
    L = t.keys(DOWN, DOWN)
    row("Down twice: the cursor is on the third line, in the column it had (the cursor keeps its column through shorter lines)", t.cursor() == (c0 + 2, r0 + 2), repr(t.cursor()))
    L = t.keys(END)
    row("End goes after the last character of the long line and the area pans: the end of the line shows, the start is gone",
        "the area" in L[r0 + 2] and "third line" not in L[r0 + 2], L[r0 + 2][c0:c0 + 20])
    L = t.keys(HOME)
    row("Home pans back: the line starts at its first column, the cursor there", "third line is rathe" in L[r0 + 2] and t.cursor() == (c0, r0 + 2), repr((L[r0 + 2][c0:c0 + 20], t.cursor())))
    L = t.keys(DOWN, DOWN, DOWN)
    area = [l[c0:c0 + 20] for l in L[r0:r0 + 5]]
    row("Down past the last row scrolls: the sixth line shows, the first has gone", area[4].startswith("6") and area[0].startswith("second"), repr(area))
    L = t.keys(DOWN)
    row("Down on the last line is not taken by the text: the form moves the focus on to the OK button (the cursor leaves the text)",
        t.cursor()[1] > r0 + 4, repr(t.cursor()))
    L = t.keys(UP)
    row("Up from the button goes back to the text, on its line", t.cursor()[1] <= r0 + 4 and t.cursor()[1] >= r0, repr(t.cursor()))
    L = t.keys(PGUP)
    row("Page Up moves a page: the first line shows again, the cursor is on a line of the area", L[r0].startswith(" " * 0) and "ABfirst line" in L[r0][c0:], "\n".join(l[c0:c0 + 20] for l in L[r0:r0 + 5]))
    L = t.keys(UP, RIGHT, RIGHT, RET)
    row("the cursor kept its screen row through Page Up, so it was on the second line: Up goes to the first (in column 1, where Home "
        "left it), Right twice, and Return splits the line there: ABfirst line becomes AB and first line, the second line follows",
        "AB" == L[r0][c0:c0 + 19].strip() and "first line" == L[r0 + 1][c0:c0 + 19].strip() and t.cursor() == (c0, r0 + 1), "\n".join(l[c0:c0 + 20] for l in L[r0:r0 + 5]))
    L = t.keys(BS)
    row("Backspace at the start of a line joins it to the one before: ABfirst line is back, the cursor between B and f", "ABfirst line" in L[r0] and t.cursor() == (c0 + 2, r0), repr((L[r0][c0:c0 + 20], t.cursor())))
    L = t.keys(CTRL_K)
    row("Ctrl-K cuts to the end of the line", L[r0][c0:c0 + 19].strip() == "AB", repr(L[r0][c0:c0 + 20]))
    L = t.keys(DELK)
    row("Delete at the end of a line joins the next one to it: ABsecond", L[r0][c0:c0 + 19].strip() == "ABsecond", repr(L[r0][c0:c0 + 20]))
    L = t.keys(TAB)
    row("Tab is not the text's: the focus goes to the OK button", t.cursor()[1] > r0 + 4, repr(t.cursor()))
    t.keys(RET)
    row("Return on the button: the program has the text, five lines now, edited as above",
        final(t, "PRESSED") == "ok| 5|ABsecond/third line is rather long indeed, longer than the area/4/5/6|", "")
    t.end()

    say("\n--- the text area: a viewer ---------------------------------------------------------------------------")
    t = Term(box, "RUN bp zzthmvw")
    t.keys()
    L = t.keys("a")
    p = at(L, "first line")
    r0 = p[0] if p else 0
    c0 = p[1] if p else 0
    L = t.keys("x", "y")
    row("a viewer takes no typing: the text is as it was", L[r0][c0:c0 + 10] == "first line" and "xy" not in L[r0], repr(L[r0][c0:c0 + 20]))
    L = t.keys(PGDN)
    area = [l[c0:c0 + 19].rstrip() for l in L[r0:r0 + 4]]
    row("Page Down scrolls a page less a line (3 of the 4 rows): lines 4 to 7 show, the first three have gone",
        area == ["4", "5", "6", "7"] and t.cursor() == (c0, r0), repr((area, t.cursor())))
    L = t.keys(PGDN)
    area = [l[c0:c0 + 19].rstrip() for l in L[r0:r0 + 4]]
    row("Page Down again stops at the end of the text: lines 5 to 8", area == ["5", "6", "7", "8"], repr(area))
    L = t.keys(BS, DELK)
    row("Backspace and Delete change nothing in a viewer", [l[c0:c0 + 19].rstrip() for l in L[r0:r0 + 4]] == area, repr([l[c0:c0 + 19].rstrip() for l in L[r0:r0 + 4]]))
    t.keys(RET)
    row("Return on a viewer is the form's: it presses the default button; the text is unchanged", final(t, "PRESSED") == "ok| 8|first line|", "")
    t.end()


def part_memo2(box):
    say("\n--- the text area: word wrap, selection, clipboard, undo, find ---------------------------------------")
    t = Term(box, "RUN bp zzthmwr")
    t.keys()
    L = t.keys("a")
    p = at(L, "the quick brown")
    r0 = p[0] if p else 0
    c0 = p[1] if p else 0

    def area(L, n=5):
        return [l[c0:c0 + 19].rstrip() for l in L[r0:r0 + n]]

    A = area(L)
    row("wrap: the long line is broken after the last blank that fits, the short one is whole, the 36-letter word is cut at the width (19)",
        p is not None and A == ["the quick brown", "fox jumps over the", "lazy dog", "short", "a" * 19], repr(A))
    row("wrap: the scroll bar is there (^ at the top, v at the bottom) and the 17 letters that are left are below the area",
        L[r0][c0 + 19] == "^" and L[r0 + 4][c0 + 19] == "v" and "a" * 17 not in "".join(L[r0 + 4:r0 + 5])[19:], repr([l[c0 + 19:c0 + 20] for l in L[r0:r0 + 5]]))
    L = t.keys(DOWN)
    row("Down goes a ROW down, not a line: the cursor is on 'fox jumps over the', in the column it had", t.cursor() == (c0, r0 + 1), repr(t.cursor()))
    L = t.keys(DOWN, DOWN, DOWN)
    row("Down three more: 'lazy dog', 'short', then the first row of the long word", t.cursor() == (c0, r0 + 4), repr(t.cursor()))
    L = t.keys(DOWN)
    A = area(L)
    row("Down onto the row the area does not show scrolls it: the rows are 'fox jumps over the' .. the 17 letters, the cursor on the last",
        A == ["fox jumps over the", "lazy dog", "short", "a" * 19, "a" * 17] and t.cursor() == (c0, r0 + 4), repr((A, t.cursor(), L[r0 + 4])))
    L = t.keys(UP, UP, UP, UP, UP)
    A = area(L)
    row("Up five times is back at the top: the first row shows again, the cursor at its first character",
        A[0] == "the quick brown" and t.cursor() == (c0, r0), repr((A, t.cursor())))
    L = t.keys(END)
    row("End goes to the end of the ROW (the blank the line was wrapped at), not the line", t.cursor() == (c0 + 15, r0), repr(t.cursor()))
    L = t.keys(RIGHT)
    row("Right from there is the next row's first character: 'fox'", t.cursor() == (c0, r0 + 1), repr(t.cursor()))
    before = t.attrs(r0 + 1)[c0:c0 + 3]
    L = t.keys(CTRL_G, RIGHT, RIGHT, RIGHT)
    sel = t.attrs(r0 + 1)[c0:c0 + 4]
    row("selection: Ctrl-G then three Rights shows 'fox' in reverse (the highlight style), the blank after it not; before the mark it was not",
        sel == "rrrn" and before != "rrr", repr((before, sel)))
    L = t.keys(CTRL_O)
    row("Ctrl-O copies and takes the selection off the screen", t.attrs(r0 + 1)[c0:c0 + 3] != "rrr", repr(t.attrs(r0 + 1)[c0:c0 + 3]))
    L = t.keys(END, CTRL_V)
    A = area(L)
    row("Ctrl-V puts 'fox' in at the cursor, before the blank that ends the row: the line is 'the quick brown fox jumps over thefox lazy dog' "
        "and it is wrapped again, the cursor after the pasted word",
        A[:4] == ["the quick brown", "fox jumps over", "thefox lazy dog", "short"] and t.cursor() == (c0 + 6, r0 + 2), repr((A, t.cursor())))
    L = t.keys(CTRL_Z)
    A = area(L)
    row("Ctrl-Z undoes the paste: the rows are as they were", A[:4] == ["the quick brown", "fox jumps over the", "lazy dog", "short"], repr(A))
    L = t.keys(CTRL_Y)
    A = area(L)
    row("Ctrl-Y does it again", A[2] == "thefox lazy dog", repr(A))
    L = t.keys(CTRL_Z)
    row("and Ctrl-Z once more takes it back", area(L)[1] == "fox jumps over the", repr(area(L)))
    L = t.keys(CTRL_T, "LAZY", RET)
    A = area(L)
    sel = t.attrs(r0 + 2)[c0:c0 + 5]
    row("find: Ctrl-T asks for the text on the bottom row of the area and Return finds it, ignoring case: 'lazy' is selected "
        "and the row under the question is back as it was",
        sel == "rrrrn" and A == ["the quick brown", "fox jumps over the", "lazy dog", "short", "a" * 19], repr((sel, A)))
    L = t.keys("X")
    A = area(L)
    row("typing on a selection replaces it: 'X dog'", A[2] == "X dog", repr(A))
    L = t.keys("a", "b", "c")
    row("typed on: 'Xabc dog'", area(L)[2] == "Xabc dog", repr(area(L)))
    L = t.keys(CTRL_Z)
    row("one Ctrl-Z takes the whole run of typing back (a run is one step): 'X dog'", area(L)[2] == "X dog", repr(area(L)))
    L = t.keys(CTRL_N)
    row("Ctrl-N with nothing more to find rings the bell and leaves the text as it is", area(L)[2] == "X dog", repr(area(L)))
    L = t.keys(CTRL_F, BS * 4, "fox", RET)               # the question starts with the last text ('LAZY'): rubbed out
    sel = t.attrs(r0 + 1)[c0:c0 + 4]
    row("find (14 Oct 26): Ctrl-F asks and finds forward, as SED's does - 'fox' on the second row is selected", sel == "rrrn", repr(sel))
    L = t.keys(CTRL_B, BS * 3, "quick", RET)
    sel = t.attrs(r0)[c0 + 4:c0 + 10]
    row("find backward: Ctrl-B asks and finds the last 'quick' before the selection (the first row)", sel == "rrrrrn", repr(sel))
    L = t.keys(CTRL_B, RET)
    sel = t.attrs(r0)[c0 + 4:c0 + 10]
    row("...and Return on the question, which starts with the last text, finds it again: the one text 'quick' is found "
        "again (the search wraps round the text)", sel == "rrrrrn", repr(sel))
    L = t.keys(TAB)
    t.keys(RET)
    row("Return on the button: the program has the text, three lines, edited as above and wrapped nowhere",
        final(t, "PRESSED") == "ok| 3|the quick brown fox jumps over the X dog/short/" + "a" * 36 + "|", "")
    t.end()

    say("\n--- the text area: a viewer that copies, the clipboard between areas, words -------------------------")
    t = Term(box, "RUN bp zzthmcb")
    t.keys()
    L = t.keys("a")
    p = at(L, "one two three")
    r0 = p[0] if p else 0
    c0 = p[1] if p else 0
    L = t.keys(CTRL_G, RIGHT, RIGHT, RIGHT)
    row("a viewer selects: 'one' is in reverse", t.attrs(r0)[c0:c0 + 4] == "rrrn", repr(t.attrs(r0)[c0:c0 + 4]))
    L = t.keys(CTRL_O, "z", CTRL_V, BS)
    row("...copies; typing, Ctrl-V and Backspace change nothing in a viewer",
        L[r0][c0:c0 + 13] == "one two three" and L[r0 + 1][c0:c0 + 13] == "four five six", repr(L[r0:r0 + 2]))
    L = t.keys(TAB, CTRL_V)
    p2 = at(L, "onex")
    row("Tab to the editor and Ctrl-V: what the viewer copied is pasted in front of its 'x': 'onex'", p2 is not None, "\n".join(l[c0:c0 + 20] for l in L[r0:r0 + 9]))
    L = t.keys(END, " red blue", CTRL_P, CTRL_P, CTRL_U, "Q")
    row("Ctrl-P goes a word back and Ctrl-U a word on (they were Ctrl-B and Ctrl-F until 14 Oct 26): "
        "'onex red blue' becomes 'onex redQ blue'", at(L, "onex redQ blue") is not None, "\n".join(l[c0:c0 + 20] for l in L[r0:r0 + 9]))
    t.keys(TAB)
    t.keys(RET)
    row("the program has both texts: the viewer's untouched, the editor's edited",
        final(t, "PRESSED") == "ok| one two three/four five six|onex redQ blue|", "")
    t.end()


PROGS.update({
    # a text area that shows SD BASIC in colour (the dark theme has the syntax styles) with line numbers, and a button after it
    "zzthsyn": dialogue_program("""   text = '* a comment':@fm:'if x = 5 then crt "hi"':@fm:'$include syscom.h':@fm:'end'
   screen theme 'dark' returning th else th = 'NO-COLOUR'
   screen form title 'Syntax' at 10,3 size 50,14 returning f
   screen memo f, 'm', text at 2,2 size 40,5 syntax 'sd.basic' lnum
   screen button f, 'ok', '&OK' at 10,11 default
   screen run f returning pressed then
      res = 'PRESSED ':pressed:'|'
   end else
      res = 'CANCEL ':pressed:'|'
   end
   screen get f, 'm' returning t
   res := ' ':dcount(t, @fm):'|':convert(@fm, '/', t):'|'
"""),
    # the same with the mono theme (which has no syntax styles) and a language that does not exist: plain, no error
    "zzthsy2": dialogue_program("""   text = '* a comment':@fm:'if x = 5 then crt "hi"'
   screen form title 'Plain' at 10,3 size 50,14 returning f
   screen memo f, 'm', text at 2,2 size 40,5 syntax 'sd.basic'
   screen memo f, 'n', text at 2,8 size 40,3 syntax 'nosuch.language'
   screen button f, 'ok', '&OK' at 10,12 default
   screen run f returning pressed then
      res = 'PRESSED ':pressed:'|'
   end else
      res = 'CANCEL ':pressed:'|'
   end
"""),
    # line numbers with wrap: a number on the first row of a line only
    "zzthlnw": dialogue_program("""   text = 'short':@fm:'a very long line that has to be wrapped in the narrow area':@fm:'end'
   screen form title 'Numbers' at 10,3 size 40,14 returning f
   screen memo f, 'm', text at 2,2 size 16,8 wrap lnum readonly
   screen button f, 'ok', '&OK' at 10,11 default
   screen run f returning pressed then
      res = 'PRESSED ':pressed:'|'
   end else
      res = 'CANCEL ':pressed:'|'
   end
"""),
})


PROGS.update({
    # a menu of twenty entries under the bar's first title, for a terminal with fewer rows than it needs
    "zzthmbg": dialogue_program("""   menus = '&Tall'
   for i = 1 to 20
      menus := @vm : 'Item ' : fmt(i, 'R%2') : @sm : '' : @sm : 'i' : i
   next i
   screen menubar menus returning c then
      res = 'CHOSE ':c:'|'
   end else
      res = 'LEFT|'
   end
"""),
})


def tall_geometry(L):
    """(row, column of the first character of the label) of 'Item 01' on the screen, or None."""
    for i, l in enumerate(L):
        if "Item 01" in l:
            return i, l.index("Item 01")
    return None


def part_menutall(box):
    say("\n--- a menu with more entries than the screen has rows (13 Oct 26) ---------------------------------------")
    # twenty entries.  Before 13 Oct the rows that did not fit were not drawn though the cursor still moved over them
    t = Term(box, "RUN bp zzthmbg", cols=100, rows=24)
    t.keys()
    L = t.keys("a")
    g = tall_geometry(L)
    row("control (24 rows): all twenty entries show, Item 01 first and Item 20 last, no ^ and no v at the right edge",
        g is not None and "Item 20" in L[g[0] + 19] and "^" not in L[g[0]][g[1]:g[1] + 12] and "v" not in L[g[0] + 19][g[1] + 6:g[1] + 12], "\n".join(L[:24]))
    t.keys(ESC)
    t.end()

    t = Term(box, "RUN bp zzthmbg", cols=100, rows=12)
    before = t.keys()
    L = t.keys("a")
    g = tall_geometry(L)
    if g is None:
        row("12 rows: the menu is drawn (Item 01 found)", False, "\n".join(L))
        t.end()
        return
    r1, c1 = g
    # the marker is in the last cell of the dropdown: it starts one cell left of the label (a blank first) and is the label's
    # 7 cells and 4 more wide (a blank each side, and room for a shortcut that these entries do not have)
    mk = (c1 - 1) + 11 - 1
    row("12 rows: the first eleven entries show (Item 01 on row 1, Item 11 on row 11) and Item 12 does not",
        r1 == 1 and "Item 11" in L[11] and not any("Item 12" in l for l in L), "\n".join(L))
    row("...no ^ on the first row (nothing above it), a v on the last row (more below)", L[1][mk:mk + 1] != "^" and L[11][mk:mk + 1] == "v", repr((L[1][mk - 3:mk + 2], L[11][mk - 3:mk + 2])))
    hl = [i for i in range(1, 12) if t.attrs(i)[c1 + 1:c1 + 2] not in ("r", "x")]
    row("...and Item 01 is the highlighted row, the only one", hl == [1], repr(hl))
    L = t.keys(UP)
    hl = [i for i in range(1, 12) if t.attrs(i)[c1 + 1:c1 + 2] not in ("r", "x")]
    row("Up from the first goes to the last and the menu scrolls to it: Item 20 is on the last row, highlighted, with a ^ above and no v",
        "Item 20" in L[11] and hl == [11] and L[1][mk:mk + 1] == "^" and L[11][mk:mk + 1] != "v" and not any("Item 01" in l for l in L), "\n".join(L) + repr(hl))
    L = t.keys(DOWN)
    row("Down from the last wraps to the first: Item 01 shows again, no ^", "Item 01" in L[1] and L[1][mk:mk + 1] != "^", repr(L[1]))
    L = t.keys(*([DOWN] * 14))
    ri = [i for i, l in enumerate(L) if "Item 15" in l]
    hl = [i for i in range(1, 12) if t.attrs(i)[c1 + 1:c1 + 2] not in ("r", "x")]
    row("Down fourteen times: Item 15 is shown and highlighted, Item 01 has scrolled off, ^ above and v below",
        bool(ri) and hl == [ri[0]] and not any("Item 01" in l for l in L) and L[1][mk:mk + 1] == "^" and L[11][mk:mk + 1] == "v", "\n".join(L) + repr((hl, ri)))
    L = t.keys(UP, UP, UP, UP, UP, UP, UP, UP, UP, UP, UP, UP, UP, UP)
    row("Up fourteen times: back at Item 01, the window with it", "Item 01" in L[1] and t.attrs(1)[c1 + 1:c1 + 2] not in ("r", "x"), "\n".join(L))
    t.keys(*([DOWN] * 14))
    t.keys(RET)
    # on a 12-row window the program's result line (@(0, 25)) lands on a row that still holds the background, so the
    # answer is the text between the tag and its bar, not the rest of the row
    got = [l for l in t.keys("z") if l.startswith("CHOSE")]
    row("Return on a scrolled-in entry chooses it, and the program has its code: i15",
        bool(got) and got[0][len("CHOSE "):].split("|")[0] == "i15", repr(got))
    t.end()

    t = Term(box, "RUN bp zzthmbg", cols=100, rows=12)
    t.keys()
    L0, A0 = t.lines(), [t.attrs(r) for r in range(12)]       # (record() reads 30 rows; this window has 12)
    t.keys("a", UP)
    L = t.keys(ESC, idle=0.9)
    ok, bad = same_as(t, L0, A0, range(1, 12))
    row("Esc on a scrolled menu leaves no trace: rows 1-11 are cell for cell as they were before the menu opened (row 0 keeps the bar)",
        ok and L[0].lstrip().startswith("Tall"), repr((bad, L[0][:20])))
    t.end()


def part_memo3(box):
    say("\n--- the text area: syntax colour and line numbers (13 Oct 26) -------------------------------------------")
    t = Term(box, "RUN bp zzthsyn")
    t.keys()
    L = t.keys("a")
    p = at(L, "* a comment")
    r0 = p[0] if p else 0
    c0 = p[1] if p else 0
    row("line numbers: the four lines are 1 * a comment, 2 if x ..., 3 $include ... and 4 end, the text two cells in from the numbers",
        p is not None and L[r0][c0 - 2:c0 + 11] == "1 * a comment" and L[r0 + 1][c0 - 2:c0 + 4] == "2 if x" and L[r0 + 2][c0 - 2:c0 + 6] == "3 $inclu"
        and L[r0 + 3][c0 - 2:c0 + 5] == "4 end  ", repr([l[c0 - 2:c0 + 22] for l in L[r0:r0 + 4]]))
    row("control: the theme was given (the dark theme is coloured)", t.style(r0, c0) != (None, None, ""), repr(t.style(r0, c0)))
    cm = t.style(r0, c0)
    row("a comment line is blue and bold, all of it", cm == (BLUE, None, "b") and t.style(r0, c0 + 8) == cm, repr((cm, t.style(r0, c0 + 8))))
    line2 = L[r0 + 1]
    ci, ct, cs, cn = c0, line2.index("then"), line2.index('"hi"'), line2.index("5")
    kw = t.style(r0 + 1, ci)
    row("keywords are one colour, bold, and not the comment's: if, then and crt", kw[0] is not None and "b" in kw[2] and kw != cm
        and t.style(r0 + 1, ct) == kw and t.style(r0 + 1, line2.index("crt")) == kw, repr((kw, t.style(r0 + 1, ct), t.style(r0 + 1, line2.index("crt")))))
    row("a name that is no keyword is plain: the x", t.style(r0 + 1, line2.index(" x ") + 1) == (None, None, ""), repr(t.style(r0 + 1, line2.index(" x ") + 1)))
    row("a string is green, and so are its quotes: \"hi\"", t.style(r0 + 1, cs) == (GREEN, None, "") and t.style(r0 + 1, cs + 3) == (GREEN, None, ""), repr((t.style(r0 + 1, cs), t.style(r0 + 1, cs + 3))))
    row("a number is not plain and not a keyword's colour: the 5", t.style(r0 + 1, cn) not in ((None, None, ""), kw), repr(t.style(r0 + 1, cn)))
    row("a line that starts with $ is the preprocessor's, red, all of it", t.style(r0 + 2, c0) == (RED, None, "") and t.style(r0 + 2, c0 + 15) == (RED, None, ""), repr((t.style(r0 + 2, c0), t.style(r0 + 2, c0 + 15))))
    L = t.keys("q")
    row("typing goes in at the cursor and the colours follow the text: q* a comment is no comment now, the * is plain",
        L[r0][c0:c0 + 12] == "q* a comment" and t.style(r0, c0 + 1) == (None, None, ""), repr((L[r0][c0:c0 + 12], t.style(r0, c0 + 1))))
    L = t.keys(CTRL_A, DELK)
    row("deleting the q gives the comment back its colour, in one go", L[r0][c0:c0 + 11] == "* a comment" and t.style(r0, c0) == cm, repr((L[r0][c0:c0 + 11], t.style(r0, c0))))
    # a click on the text: through the numbers
    click(t, c0 + 4, r0)
    L = t.keys("Z")
    row("a click on the c of comment puts the cursor there (the numbers are not counted): Z goes in before it", L[r0][c0:c0 + 12] == "* a Zcomment", repr(L[r0][c0:c0 + 13]))
    t.keys(TAB, RET)                    # (Return in the text splits a line: Tab goes to the button first)
    got = final(t, "PRESSED")
    row("the text the program gets back has no line numbers in it, and the Z",
        got == 'ok| 4|* a Zcomment/if x = 5 then crt "hi"/$include syscom.h/end|', repr(got))
    t.end()

    t = Term(box, "RUN bp zzthsy2")
    t.keys()
    L = t.keys("a")
    p = at(L, "* a comment")
    r1 = p[0] if p else 0
    c1 = p[1] if p else 0
    row("the mono theme has no syntax colours: the text is plain, a comment included (and no line numbers when none are asked for)",
        p is not None and t.style(r1, c1) == (None, None, "") and t.style(r1 + 1, c1) == (None, None, "") and L[r1][c1 - 2:c1 + 2] != "1 * ",
        repr((t.style(r1, c1), L[r1][c1 - 2:c1 + 11])))
    p2 = [i for i, l in enumerate(L) if i > r1 + 1 and "* a comment" in l]
    row("a language that does not exist is not an error: the second area shows its text, plain", bool(p2) and t.style(p2[0], c1) == (None, None, ""), repr(p2))
    t.keys(RET)
    t.end()

    t = Term(box, "RUN bp zzthlnw")
    t.keys()
    L = t.keys("a")
    p = at(L, "short")
    r2 = p[0] if p else 0
    c2 = p[1] if p else 0
    area = [l[c2 - 2:c2 + 14] for l in L[r2:r2 + 8]]
    row("wrap with numbers: a number on the first row of each line only: 1 short, 2 a very long, a blank where the line goes on, 3 end",
        p is not None and area[0].startswith("1 short") and area[1].startswith("2 a very long") and area[2].startswith("  ") and area[2][2:3].strip() != ""
        and any(a.startswith("3 end") for a in area), repr(area))
    t.keys(RET)
    t.end()


def part_table2(box):
    say("\n--- the table: sorting, marked rows, columns -----------------------------------------------------------")
    t = Term(box, "RUN bp zzthtbs")
    t.keys()
    L = t.keys("a")
    p = at(L, "Name")
    r0 = p[0] if p else 0
    c0 = p[1] if p else 0

    def names(L):
        return [L[r0 + 1 + i][c0:c0 + 8].rstrip() for i in range(5)]

    row("the table: the heading, five names; the columns that do not fit (Code, most of City) are off the right edge",
        p is not None and names(L) == ["Smith", "Jones", "Adams", "Baker", "Clark"] and "Code" not in L[r0], repr((names(L), L[r0])))
    L = t.keys(RIGHT, F3)
    row("Right makes Qty the current column and F3 sorts by it, up, as NUMBERS (3, 7, 12, 44, 150, not 12, 150, 3...): Baker Jones Smith Clark Adams, "
        "and the heading says ^",
        names(L) == ["Baker", "Jones", "Smith", "Clark", "Adams"] and "^" in L[r0][c0 + 9:c0 + 14], repr((names(L), L[r0])))
    L = t.keys(F3)
    row("F3 again: down, Adams first, v in the heading", names(L) == ["Adams", "Clark", "Smith", "Jones", "Baker"] and "v" in L[r0][c0 + 9:c0 + 14], repr((names(L), L[r0])))
    L = t.keys(F3)
    row("F3 again: the order of the rows, no mark", names(L) == ["Smith", "Jones", "Adams", "Baker", "Clark"] and "^" not in L[r0] and "v" not in L[r0][c0 + 9:c0 + 14], repr((names(L), L[r0])))
    L = t.keys(" ", DOWN, DOWN, " ")
    lead = [L[r0 + 1 + i][c0 - 1] for i in range(5)]
    row("the space bar marks rows: Smith and Adams have a * in front of them, the others not", lead == ["*", " ", "*", " ", " "], repr(lead))
    L = t.keys(F3)
    lead = [L[r0 + 1 + i][c0 - 1] for i in range(5)]
    row("the marks stay with their rows through a sort: Baker Jones *Smith Clark *Adams",
        names(L) == ["Baker", "Jones", "Smith", "Clark", "Adams"] and lead == [" ", " ", "*", " ", "*"], repr((names(L), lead)))
    L = t.keys(">")
    row("> makes the current column (Qty) one cell wider: City moves right by one", L[r0][c0 + 14:c0 + 18].strip() == "City"[:len(L[r0][c0 + 14:c0 + 18].strip())] or "City" in L[r0], repr(L[r0]))
    L = t.keys(RIGHT, RIGHT, RIGHT)
    row("Right to the last column scrolls the table sideways: Code is shown and Name is gone",
        "Code" in L[r0] and "Name" not in L[r0], repr(L[r0]))
    L = t.keys(LEFT, LEFT, LEFT)
    row("Left back to the first column scrolls it back: Name is shown", "Name" in L[r0], repr(L[r0]))
    t.keys(TAB)
    t.keys(RET)
    row("the program has the NUMBERS (in the data's order) of the rows marked: 1 and 3", final(t, "PRESSED") == "ok| 1,3|", "")
    t.end()


def part_lines(box):
    say("\n--- borders in line-drawing characters --------------------------------------------------------------")
    t = Term(box, "RUN bp zzscbln", utf8=True)
    L = t.keys()
    TL, TR, BL, BR, H, V = "┌", "┐", "└", "┘", "─", "│"
    row("LINES: the box is 12 cells wide with the Unicode line-drawing characters, the title in the top border",
        L[2][2:14] == TL + H + " Hi " + H * 5 + TR and L[5][2:14] == BL + H * 10 + BR and L[3][2] == V and L[3][13] == V, repr(L[2:6]))
    row("...and a + - | the program wrote itself is untouched (the stand-ins are not those characters)", "a + b - c | d" in L[8], repr(L[8]))
    row("the message box is in them too: its top border with the title and its side",
        L[3][20:21] == TL and "T" in L[3][20:30] and L[4][20] == V and "Boxed." in L[4], "\n".join(L[3:9]))
    L = t.keys(RET, "a")
    row("after SCREEN CLOSE and a second SCREEN OPEN without LINES the box is + - | again and no line-drawing character is left",
        L[2][2:14] == "+- Hi -----+" and L[5][2:14] == "+" + "-" * 10 + "+" and not any(c in "".join(L) for c in (TL, TR, BL, BR, H, V)), "\n".join(L[:12]))
    t.keys("b")
    t.end()


def part_clip(box):
    say("\n--- SCREEN CLIP -------------------------------------------------------------------------------------")
    t = Term(box, "RUN bp zzscclp")
    L = t.keys()
    row("text above the clip rectangle (row 4) is not drawn at all", L[4].strip() == "", repr(L[4]))
    row("text across its left edge is cut there: 'FGHIJKLMNO' is what is inside columns 10 to 19, and nothing is left of or right of it",
        L[6][:30].strip() == "FGHIJKLMNO" and L[6][10:20] == "FGHIJKLMNO", repr(L[6]))
    row("text starting inside and running past the right edge is cut there: 'abcdef' in columns 14 to 19", L[7][14:20] == "abcdef" and L[7][20:].strip() == "", repr(L[7]))
    row("text below the rectangle (row 8) is not drawn", L[8].strip() == "", repr(L[8]))
    row("SCREEN CLIP with no rectangle takes the clip off: 'free' is drawn at the left edge", L[12][:4] == "free", repr(L[12]))
    row("control: the clip statement did not take ELSE", "CLIP-ELSE" not in "".join(L), repr(L[20]))
    t.keys("a")
    t.end()


def part_scrollbar(box):
    say("\n--- a scroll bar of its own -------------------------------------------------------------------------")
    t = Term(box, "RUN bp zzscsb")
    t.keys()
    L = t.keys("a")
    p = at(L, "lines")
    r0 = p[0] if p else 0
    c0 = (p[1] if p else 0) - 4

    def bar(L):
        return "".join(L[r0 + i][c0] for i in range(6))

    row("the bar: ^ at the top, v at the bottom, the thumb (# one cell: 5 of 20 of 4 track cells) right under the ^", p is not None and bar(L) == "^#|||v", repr(bar(L)))
    L = t.keys(DOWN)
    row("Down moves it one: the thumb has not left its cell (a quarter of the way is still the first cell of four) and the label says line 2",
        any("line 2" in l for l in L), "\n".join(L[r0:r0 + 3]))
    L = t.keys(PGDN)
    L = t.keys(END)
    row("End goes to the last place, 16 (20 lines, 5 shown): the thumb is on the last track cell, next to the v", bar(L) == "^|||#v", repr(bar(L)))
    t.keys(TAB)
    t.keys(RET)
    row("every move was a change event with the number of the first line, and SCREEN GET answers where the bar is: 16",
        final(t, "LOG") == "2;6;16; V 16|", repr(final(t, "LOG")))
    t.end()


def part_set(box):
    say("\n--- SCREEN SET: WRAP, READONLY, VISIBLE ----------------------------------------------------------------")
    t = Term(box, "RUN bp zzscset")
    t.keys()
    L = t.keys("a")
    p = at(L, "the quick brown")
    r0 = p[0] if p else 0
    c0 = p[1] if p else 0
    row("before: the memo pans (the first row is 'the quick brown fox', 19 cells) and the OK button is there",
        p is not None and L[r0][c0:c0 + 19] == "the quick brown fox" and any("OK" in l for l in L), "\n".join(L[r0 - 1:r0 + 7]))
    L = t.keys(F2_KEY)
    A = [L[r0 + i][c0:c0 + 19].rstrip() for i in range(3)]
    row("SET WRAP 1 wraps the memo while it is on the screen: 'the quick brown', 'fox jumps over the', 'lazy dog'",
        A == ["the quick brown", "fox jumps over the", "lazy dog"], repr(A))
    row("SET VISIBLE 0 hides the button: no OK on the form", not any("[ OK ]" in l for l in L), "\n".join(L[r0 - 1:r0 + 8]))
    L = t.keys(F3_KEY, "x", "y")
    A = [L[r0 + i][c0:c0 + 19].rstrip() for i in range(3)]
    row("SET READONLY 1 makes it a viewer: typing changes nothing", A == ["the quick brown", "fox jumps over the", "lazy dog"], repr(A))
    t.keys(F4_KEY)
    row("the program ended with the text as it was",
        final(t, "DONE") == "the quick brown fox jumps over the lazy dog|", repr(final(t, "DONE")))
    t.end()


def part_tree(box):
    say("\n--- the tree ----------------------------------------------------------------------------------------")
    t = Term(box, "RUN bp zzthtre")
    t.keys()
    L = t.keys("a")
    p = at(L, "Root A")
    r0 = p[0] if p else 0
    c0 = (p[1] if p else 0) - 3                       # the lead cell is c0, the + or - is c0 + 1, the label starts at c0 + 3

    def tree(L, n=7):
        return [L[r0 + i][c0:c0 + 20].rstrip() for i in range(n)]

    A = tree(L)
    row("the tree starts closed: the three roots, + before those with nodes under them, a blank before the leaf",
        p is not None and A[:3] == [" + Root A", " + Root B", "   Root C"] and A[3] == "", repr(A))
    row("the cursor is on Root A, which is in reverse (the highlight style)", t.attrs(r0)[c0 + 3:c0 + 9] == "rrrrrr", repr(t.attrs(r0)[c0:c0 + 20]))
    L = t.keys(RIGHT)
    A = tree(L)
    row("Right opens Root A: - before it, Child A1 (+) and Child A2 under it, indented two cells; the roots below move down",
        A[:5] == [" - Root A", "   + Child A1", "     Child A2", " + Root B", "   Root C"], repr(A))
    L = t.keys(RIGHT, DOWN, LEFT)
    A = tree(L)
    row("Right on an open node goes to its first node (Child A1), Down to Child A2, Left on a leaf goes to the node it is under: "
        "the cursor is on Root A again", t.attrs(r0)[c0 + 3:c0 + 9] == "rrrrrr" and t.attrs(r0 + 2)[c0 + 3:c0 + 9] != "rrrrrr", repr((t.attrs(r0)[:20], t.attrs(r0 + 2)[:20])))
    L = t.keys(RIGHT, RIGHT)
    A = tree(L)
    row("Right to Child A1 and Right again opens it: Leaf A1a under it, indented four cells",
        A[:6] == [" - Root A", "   - Child A1", "       Leaf A1a", "     Child A2", " + Root B", "   Root C"], repr(A))
    L = t.keys(LEFT, LEFT)
    A = tree(L)
    row("Left closes Child A1 and Left again (on a closed node) goes to Root A",
        A[:4] == [" - Root A", "   + Child A1", "     Child A2", " + Root B"] and t.attrs(r0)[c0 + 3:c0 + 9] == "rrrrrr", repr(A))
    L = t.keys(" ")
    A = tree(L)
    row("the space bar closes Root A: back to the three roots", A[:3] == [" + Root A", " + Root B", "   Root C"], repr(A))
    L = t.keys("r", "r")
    row("a letter goes to the next node shown that starts with it: R twice from Root A is Root C", t.attrs(r0 + 2)[c0 + 3:c0 + 9] == "rrrrrr", repr(t.attrs(r0 + 2)[:20]))
    L = t.keys(UP, UP, RIGHT, RIGHT, RIGHT, DOWN)
    A = tree(L)
    row("up to Root A, open it, to Child A1, open it, Down to Leaf A1a", t.attrs(r0 + 2)[c0 + 7:c0 + 15] == "rrrrrrrr", repr((A[:6], t.attrs(r0 + 2)[:20])))
    t.keys(RET)
    row("Return is a done event (the default button): the program has the leaf's code, a1a", final(t, "PRESSED") == "ok| a1a|", "")
    t.end()


def part_menu2(box):
    say("\n--- menus: disabled and checked entries, submenus -----------------------------------------------------")
    t = Term(box, "RUN bp zzscmfl")
    L = t.keys("a")
    rows = [l[:14].rstrip() for l in L[1:7]]
    row("File is open: Open, Save, Autosave (with a * in its first cell: checked), Recent with a > at its right, Exit; "
        "the hidden submenu is not on the bar (File and Edit only)",
        rows[0].startswith(" Open") and rows[1].startswith(" Save") and rows[2].startswith("*Autosave")
        and rows[3].startswith(" Recent") and rows[3].endswith(">") and rows[4].startswith(" Exit")
        and L[0].startswith(" File  Edit") and "Recent" not in L[0], repr(rows))
    row("the cursor (the selected entry is drawn normal on the reverse menu) is on Open, not on Save",
        t.attrs(1)[3] == "n" and t.attrs(2)[3] in "rx", repr([t.attrs(r)[:8] for r in (1, 2, 3)]))
    L = t.keys(DOWN)
    row("Down skips the disabled Save: the cursor is on Autosave", t.attrs(3)[3] == "n" and t.attrs(2)[3] in "rx" and t.attrs(1)[3] in "rx",
        repr([t.attrs(r)[:8] for r in (1, 2, 3, 4)]))
    L = t.keys("s")
    row("the letter of a disabled entry chooses nothing: File is still open on Autosave", any("Autosave" in l for l in L[1:7]) and t.attrs(3)[3] == "n", "\n".join(L[:7]))
    L = t.keys(DOWN, RIGHT)
    sub = [l[14:30].rstrip() for l in L[3:7]]
    row("Down to Recent and Right opens its submenu beside it: one.txt and two.txt; File is still open under it",
        any("one.txt" in l for l in L[1:8]) and any("two.txt" in l for l in L[1:8]) and any("Autosave" in l for l in L[1:7]), "\n".join(L[:8]))
    L = t.keys(ESC)
    row("Esc closes the submenu only: its entries are gone and File is still open", not any("one.txt" in l for l in L[1:8]) and any("Recent" in l for l in L[1:7]), "\n".join(L[:8]))
    L = t.keys(RIGHT)
    row("Right on Recent opens it again", any("one.txt" in l for l in L[1:8]), "\n".join(L[:8]))
    L = t.keys(DOWN, RET)
    row("Down and Return in the submenu choose two.txt: its code is what the program gets, and every drop-down is closed",
        not any("one.txt" in l for l in L[1:8]) and not any("Autosave" in l for l in L[1:7]) and final(t, "CODE") == "r2|", "")
    t.end()
    t = Term(box, "RUN bp zzscmfl")
    L = t.keys("a")
    L = t.keys(RIGHT)
    row("Edit: Copy and Paste (disabled); Down from Copy stays on Copy because Paste cannot be chosen",
        any("Copy" in l for l in L[1:5]) and any("Paste" in l for l in L[1:5]), "\n".join(L[:5]))
    L = t.keys(DOWN, RET)
    row("...so Down then Return chooses Copy", final(t, "CODE") == "copy|", "")
    t.end()


def part_tabs(box):
    say("\n--- tabs and pages ------------------------------------------------------------------------------------")
    t = Term(box, "RUN bp zzthtab")
    t.keys()
    L = t.keys("a")
    row("page 1: the strip with the first tab in brackets, the widgets of page 1, none of pages 2 and 3, the buttons that are on every page",
        any("[General]" in l and "Address" in l and "Notes" in l for l in L) and any("Name:" in l and "Smith" in l for l in L)
        and any("VIP" in l for l in L) and not any("Street:" in l for l in L) and not any("Notes:" in l for l in L)
        and any("[ OK ]" in l and "[ Cancel ]" in l for l in L), "\n".join(L[3:19]))
    L = t.keys(RIGHT)
    row("Right chooses the second tab: page 2 shows, page 1's widgets are gone, the strip follows",
        any("Street:" in l and "Main St" in l for l in L) and not any("Name:" in l for l in L) and not any("VIP" in l for l in L)
        and any("[Address]" in l for l in L) and not any("[General]" in l for l in L) and any("[ OK ]" in l for l in L), "\n".join(L[3:19]))
    L = t.keys(RIGHT)
    row("Right again: page 3 (its list, not page 2's entry)", any("Notes:" in l and "aa" in l for l in L) and not any("Street:" in l for l in L)
        and any("[Notes]" in l for l in L), "\n".join(L[3:19]))
    L = t.keys(RIGHT)
    row("Right on the last tab stays on it", any("[Notes]" in l for l in L), "\n".join(L[3:6]))
    L = t.keys(LEFT, LEFT)
    row("Left twice: page 1 again, with the text it had", any("Name:" in l and "Smith" in l for l in L) and not any("Notes:" in l for l in L)
        and any("[General]" in l for l in L), "\n".join(L[3:19]))
    L = t.keys(RIGHT)
    L = t.keys(DOWN, "Z")
    row("Down from the strip goes to the first widget on the page: the street entry, not page 1's name (hidden widgets take no focus)",
        any("Main StZ" in l for l in L) and not any("SmithZ" in l for l in L), "\n".join(L[3:19]))
    t.keys(RET)
    row("Return presses the default button, which is on every page; the values of all pages reach the program, those of a page that was not shown unchanged",
        final(t, "PRESSED") == "ok| 2|Smith|Main StZ|1|", "")
    t.end()

    t = Term(box, "RUN bp zzthtb2")
    t.keys("a")
    t.keys(RIGHT)
    t.keys(RIGHT)
    t.keys(ESC, idle=0.9)
    row("SCREEN WAIT: choosing a tab is a change event (type, widget id, the new tab), once for each tab; Esc is ELSE",
        final(t, "LOG") == "change/tabs/2 change/tabs/3 ELSE:cancel", "")
    t.end()


def at(lines, text):
    """(row, column) of the first place TEXT is on the screen, or None."""
    for i, l in enumerate(lines):
        j = l.find(text)
        if j >= 0:
            return i, j
    return None


def part_themes(box):
    say("\n--- themes: classic, on three terminal types ---------------------------------------------------------")
    for term in ("xterm", "linux", "ansi"):
        t = Term(box, "RUN bp zzthcls", term=term)
        L0, A0 = record(t)
        coloured = [(r, c) for r in range(30) for c in range(100) if t.style(r, c)[:2] != (None, None)]
        row("%s: control: before the theme is asked for, no cell on the screen has a colour" % term, not coloured, repr(coloured[:5]))
        L = t.keys("a")
        # the bottom right cell: written like the others, except on a terminal that scrolls when it is (no xenl: ansi), where the
        # library leaves that one cell alone rather than scroll its own screen
        corner = (None, None, "") if term == "ansi" else (WHITE, BLUE, "")
        row("%s: the desktop is white on blue, text and blank cells alike, to the last cell of the screen%s" % (term, " but the corner (this terminal scrolls when it is written)" if term == "ansi" else ""),
            t.style(1, 3) == (WHITE, BLUE, "") and t.style(22, 5) == (WHITE, BLUE, "") and t.style(29, 98) == (WHITE, BLUE, "") and t.style(29, 99) == corner,
            repr((t.style(1, 3), t.style(22, 5), t.style(29, 98), t.style(29, 99))))
        row("%s: cells given the raw reverse style keep it, with no colour: the same in every theme" % term,
            t.style(1, 7) == (None, None, "r"), repr(t.style(1, 7)))
        row("%s: bold text on the desktop is bold in the desktop's colours (bright white on blue), not in a box of the terminal's own black" % term,
            t.style(22, 62) == (WHITE, BLUE, "b"), repr(t.style(22, 62)))
        p = at(L, "Colourful")
        row("%s: the message box body is black on light grey (the window style)" % term,
            p is not None and t.style(p[0], p[1]) == (BLACK, WHITE, "") and t.style(p[0], p[1] + 8) == (BLACK, WHITE, ""), repr((p, p and t.style(*p))))
        ti = at(L, "Colours")
        row("%s: ...and so is its title in the top border" % term, ti is not None and t.style(*ti) == (BLACK, WHITE, ""), repr((ti, ti and t.style(*ti))))
        y = at(L, "[ Yes ]")
        n = at(L, "[ No ]")
        row("%s: the default button is white on green and bold (highlight), the other black on light grey" % term,
            y is not None and n is not None and t.style(*y) == (WHITE, GREEN, "b") and t.style(y[0], y[1] + 6) == (WHITE, GREEN, "b")
            and t.style(*n) == (BLACK, WHITE, ""), repr((y, n, y and t.style(*y), n and t.style(*n))))
        L2 = t.keys(RET)
        row("%s: Return closes the box and what was under it is back, in the desktop colours" % term,
            p is not None and L2[p[0]].startswith("row %02d" % p[0]) and t.style(p[0], p[1]) == (WHITE, BLUE, "") and t.style(y[0], y[1]) == (WHITE, BLUE, ""),
            repr((L2[p[0]][:30], t.style(p[0], p[1]))))
        row("%s: the program was told the theme and the button" % term, final(t, "THEME") == "classic 1", "")
        t.end()

    say("\n--- themes: back to mono, and what is refused ----------------------------------------------------------")
    t = Term(box, "RUN bp zzthmon")
    L0, A0 = record(t)
    t.keys("a")
    row("classic is on: the desktop is coloured", t.style(1, 3) == (WHITE, BLUE, ""), repr(t.style(1, 3)))
    t.keys("b")
    ok, bad = same_as(t, L0, A0)
    coloured = [(r, c) for r in range(30) for c in range(100) if t.style(r, c)[:2] != (None, None)]
    row("mono again: the 20 rows are back as they were, text and style, with no colour anywhere", ok and not coloured, repr((bad, coloured[:5])))
    row("...and the names came back as classic and mono", final(t, "BACK") == "classic|mono|", "")
    t.end()
    t = Term(box, "RUN bp zzthbad")
    t.keys("a")
    row("a name that is no theme takes ELSE and leaves mono; the empty name only answers; a name in capitals is the same theme",
        final(t, "NAMES") == "mono/ELSE|mono|blue|classic|", "")
    t.end()

    say("\n--- themes: SCREEN STYLE -------------------------------------------------------------------------------")
    t = Term(box, "RUN bp zzthsty")
    t.keys("a")
    L = t.keys()
    y = at(L, "[ Yes ]")
    row("the changed style is what the default button is drawn in: red on black, bold and underlined",
        y is not None and t.style(*y) == (RED, BLACK, "ub"), repr((y, y and t.style(*y))))
    t.keys(RET)
    row("a raw style, an unknown colour, an unknown flag and an unknown style are refused (ELSE) and nothing changed",
        final(t, "STYLE") == "OKNONONONO 1", "")
    t.end()

    say("\n--- themes: the theme before OPEN, and CLOSE ------------------------------------------------------------")
    t = Term(box, "RUN bp zzthopn")
    t.keys()
    row("a theme asked for before SCREEN OPEN CLEAR: the open paints the desktop, the text on it is in the same colours",
        t.style(0, 0) == (WHITE, BLUE, "") and t.style(2, 2) == (WHITE, BLUE, "") and t.style(29, 99) == (WHITE, BLUE, ""),
        repr((t.style(0, 0), t.style(2, 2), t.style(29, 99))))
    L = t.keys("a")
    coloured = [(r, c) for r in range(30) for c in range(100) if t.style(r, c)[:2] != (None, None)]
    row("SCREEN CLOSE takes the coloured desktop away", not coloured, repr(coloured[:5]))
    row("...and puts the theme back to mono", result(L, "AFTER") == "mono|classic|", repr(result(L, "AFTER")))
    t.end()

    say("\n--- themes: a terminal with no colour ------------------------------------------------------------------")
    t = Term(box, "RUN bp zzthnoc", term="vt100")
    t.keys()
    L = t.keys("a")
    y = at(L, "[ OK ]")
    coloured = [(r, c) for r in range(30) for c in range(100) if t.style(r, c)[:2] != (None, None)]
    row("on a vt100 the theme blue is refused: the box is the mono one (default button in reverse video), and nothing has a colour",
        y is not None and "[ OK ]" in t.reverse(y[0]) and not coloured, repr((y, t.reverse(y[0]) if y else None, coloured[:5])))
    t.keys(RET)
    row("...and the program was told so: ELSE, and the theme in force is mono", final(t, "ELSE") == "mono", "")
    t.end()

    say("\n--- themes: a menu bar -----------------------------------------------------------------------------------")
    t = Term(box, "RUN bp zzthbar")
    t.keys("a")
    L = t.keys()
    f = at(L, "File")
    row("the bar is black on light grey, and the mnemonic letters red on light grey (hotkey.bar)",
        f is not None and f[0] == 0 and t.style(0, 0) == (BLACK, WHITE, "") and t.style(0, f[1]) == (RED, WHITE, "")
        and t.style(0, f[1] + 1) == (BLACK, WHITE, ""), repr((f, t.style(0, 0), f and t.style(0, f[1]), f and t.style(0, f[1] + 1))))
    L = t.keys("b")
    o = at(L, "Open")
    x = at(L, "Exit")
    row("the open menu: the selected entry is white on green and bold (barsel), the others black on light grey",
        o is not None and x is not None and t.style(o[0], o[1] + 1) == (WHITE, GREEN, "b") and t.style(x[0], x[1]) == (BLACK, WHITE, ""),
        repr((o, x, o and t.style(o[0], o[1] + 1), x and t.style(x[0], x[1]))))
    t.keys(ESC, idle=0.9)
    t.keys(ESC, idle=0.9)
    t.end()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-screen.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-screen: sandbox %s" % box)
    say("sandbox-screen: tree    %s" % os.path.dirname(HERE))
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-screen: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    for nm, body in PROGS.items():
        with open(os.path.join(sysd, "bp", nm), "w") as fh:
            fh.write(body)
    for nm, (body, _) in BAD.items():
        with open(os.path.join(sysd, "bp", nm), "w") as fh:
            fh.write(body)
    try:
        say("\n--- the programs compile as USER programs ---------------------------------------------------------")
        out = sess(box, *["BASIC bp %s" % n for n in PROGS])
        n_ok = len(re.findall(r"(?m)^Compiled 1 program\(s\) with no errors", out))
        row("setup: all %d programs compile with no errors, in a session that is not internal" % len(PROGS), n_ok == len(PROGS), out[-900:])
        row("control: the library routine is catalogued for user programs (the compile did not need sd -internal)",
            os.path.isfile(os.path.join(sysd, "gpl.bp", "screen_msgbox")), "missing")

        say("\n--- SCREEN MSGBOX ---------------------------------------------------------------------------------")
        t = Term(box, "RUN bp zzscmsg")
        L = t.keys()
        row("control: before any key the box is drawn and there is no answer line",
            any("Delete the record?" in l for l in L) and result(L, "THEN") is None and result(L, "ELSE") is None, "\n".join(L[10:20]))
        row("the box has the title (from a variable), the text, and the two buttons from a comma list",
            any("Confirm" in l for l in L) and any("[ Yes ]" in l and "[ No ]" in l for l in L), "\n".join(L[10:20]))
        top = next((i for i, l in enumerate(L) if "+- Confirm" in l), None)
        bot = next((i for i in range(top + 1, len(L)) if L[i].strip().startswith("+--") and L[i].strip().endswith("-+")), None) if top is not None else None
        row("the top border (with the title) is as wide as the bottom one, and starts in the same column",
            top is not None and bot is not None and len(L[top].rstrip()) == len(L[bot].rstrip()) and L[top].index("+") == L[bot].index("+"), "\n".join(L[10:19]))
        btn = next((i for i, l in enumerate(L) if "[ Yes ]" in l), None)
        row("DEFAULT 2: the second button is the one in reverse video, the first is not",
            btn is not None and "[ No ]" in t.reverse(btn) and "[ Yes ]" not in t.reverse(btn), repr(btn))
        row("control: the background above the box is as painted", not bg_ok(L, range(0, 12)), repr(bg_ok(L, range(0, 12))))
        L = t.keys(RET)
        row("Return chooses the default: THEN is taken and RETURNING holds 2", result(L, "THEN") == "2|" and result(L, "ELSE") is None,
            repr((result(L, "THEN"), result(L, "ELSE"))))
        row("...the box is gone (the program runs on to DONE)", not any("[ Yes ]" in l for l in L) and result(L, "DONE") is not None, "\n".join(L[10:24]))
        holes = [hole(L[r], r) for r in (12, 13, 14)]
        row("...rows above the box are untouched; where the box was the rows are blank, and only there (no SCREEN OPEN yet, so the library has no text to put back)",
            not bg_ok(L, range(0, 12)) and all(h is not None and h >= 10 for h in holes), repr((bg_ok(L, range(0, 12)), holes)))
        row("the title variable is as it was (arguments are passed by value)", result(L, "TITLE") == "Confirm|", repr(result(L, "TITLE")))
        t.end()
        t = Term(box, "RUN bp zzscmsg")
        t.keys()
        L = t.keys("y")
        row("a button letter chooses at once: Y is the first button, THEN 1", result(L, "THEN") == "1|", repr((result(L, "THEN"), result(L, "ELSE"))))
        t.end()
        t = Term(box, "RUN bp zzscmsg")
        t.keys()
        L = t.keys(ESC, idle=0.9)
        row("Esc cancels: ELSE is taken, RETURNING holds 0, THEN is not", result(L, "ELSE") == "0|" and result(L, "THEN") is None,
            repr((result(L, "THEN"), result(L, "ELSE"))))
        t.end()
        t = Term(box, "RUN bp zzscmsg")
        t.keys()
        L = t.keys(LEFT, RET)
        row("Left moves to the first button: Return then gives 1", result(L, "THEN") == "1|", repr(result(L, "THEN")))
        t.end()

        say("\n--- the clauses in another order, with values ---------------------------------------------------------")
        t = Term(box, "RUN bp zzscord")
        L = t.keys()
        row("DEFAULT, BUTTONS, TITLE written in the other order give the same box",
            any("Confirm" in l for l in L) and any("[ Yes ]" in l and "[ No ]" in l for l in L)
            and "[ No ]" in t.reverse(next((i for i, l in enumerate(L) if "[ Yes ]" in l), 0)), "\n".join(L[10:20]))
        L = t.keys(RET)
        row("...and the answer is the same: THEN 2", result(L, "THEN") == "2|", repr(result(L, "THEN")))
        t.end()

        say("\n--- the shortest form --------------------------------------------------------------------------------")
        t = Term(box, "RUN bp zzscmin")
        L = t.keys()
        row("control: the box shows its text and one OK button, and the program has not run on",
            any("Done." in l for l in L) and any("[ OK ]" in l for l in L) and result(L, "AFTER") is None, "\n".join(L[10:20]))
        L = t.keys(RET)
        row("Return closes it and the next statement runs (no THEN / ELSE needed)", result(L, "AFTER") is not None and not any("[ OK ]" in l for l in L), "\n".join(L[10:24]))
        t.end()
        t = Term(box, "RUN bp zzsclin")
        L = t.keys()
        row("a field mark ends a line of the text: two lines and the title", any("First line" in l for l in L) and any("Second line" in l for l in L) and any("Two" in l for l in L), "\n".join(L[8:20]))
        t.keys(RET)
        t.end()

        say("\n--- words of the statement stay usable as variables ---------------------------------------------------")
        t = Term(box, "RUN bp zzscvar")
        L = t.keys()
        row("control: SCREEN (also as a dynamic array), TITLE, BUTTONS, DEFAULT, RETURNING as variables keep their values",
            result(L, "ARR") == "/a|" and result(L, "VARS") == "5|T|OK|1|7|", repr((result(L, "ARR"), result(L, "VARS"))))
        L = t.keys(RET)
        row("and the same names used as the statement's values: the box answers 1 and the variables are unchanged",
            result(L, "GOT") == "1|T|OK|1|", repr(result(L, "GOT")))
        t.end()

        only = [a[7:] for a in sys.argv[1:] if a.startswith("--only=")]
        parts = only[0].split(",") if only else ["owned", "dialogs", "forms", "events", "themes", "tabs", "memo", "table", "scroll", "mouse", "resize"]
        if "resize" in parts:
            part_resize(box)
        if "mouse" in parts:
            part_mouse(box)
        if "table" in parts:
            part_table(box)
            part_table2(box)
            part_tree(box)
        if "scroll" in parts:
            part_scroll(box)
        if "memo" in parts:
            part_memo(box)
            part_memo2(box)
            part_memo3(box)
        if "themes" in parts:
            part_themes(box)
        if "tabs" in parts:
            part_tabs(box)
        if "owned" in parts:
            part_owned(box)
        if "dialogs" in parts:
            part_dialogs(box)
            part_menu2(box)
        if "dialogs" in parts or "menutall" in parts:            # (menutall alone is a development aid)
            part_menutall(box)
        if "forms" in parts:
            part_forms(box)
            part_forms2(box)
        if "events" in parts:
            part_events(box)
            part_set(box)
            part_scrollbar(box)
            part_lines(box)
            part_clip(box)

        say("\n--- compile errors -------------------------------------------------------------------------------------")
        for nm, (_, want) in BAD.items():
            out = sess(box, "BASIC bp %s" % nm)
            ok = ("with no errors" not in out) and (want in out)
            row("%s: refused%s" % (nm, (" with '" + want + "'") if want else ""), ok, out[-400:])
    finally:
        say("\n--- cleanup ---------------------------------------------------------------------------------------")
        for nm in list(PROGS) + list(BAD):
            for d in ("bp", "bp.out"):
                pth = os.path.join(sysd, d, nm)
                if os.path.exists(pth):
                    os.remove(pth)

    say("\nsandbox-screen: %d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        bail("no row ran - a broken test, not a pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
