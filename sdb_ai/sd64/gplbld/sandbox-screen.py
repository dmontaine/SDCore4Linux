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

    def __init__(self, box, cmd, cols=100, rows=30):
        self.cols = cols
        self.rows = rows
        env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"), TERM="xterm")
        self.s = PtySession([os.path.join(box, "sys", "bin", "sd")], os.path.join(box, "user_accounts"), env, cols, rows)
        self.s.settle(1.0)
        self.s.type("TERM xterm\r")
        self.s.type("TERM %d,%d\r" % (cols, rows))
        self.s.type(cmd + "\r", idle=1.0)

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
   screen check  f, 'vip', '&VIP customer' at 12,4 value 1
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
   screen check  f, 'on', '&Enable' at 8,4 value 0
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
   open 'VOC' to v else stop
   write r1:@fm:r2:@fm:r3:@fm:r4:@fm:r5:@fm:r6:@fm:r7:@fm:r8 on v, 'zzscph_out'
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
    row("...a scroll bar in the right-hand column: ^ at the top, v at the bottom, a # between",
        [L[12 + i][59] for i in range(5)] == ["^", "#", "|", "|", "v"], repr([L[12 + i][59] for i in range(5)]))
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
    row("in a phantom SCREEN OPEN takes ELSE (no terminal), and a message box, a key, a menu, a pick list, an input dialogue and a form "
        "all answer ELSE without waiting for anybody; the answers are not the THEN ones",
        has(out, r"^PHANTOM OPEN-ELSE\|MSG-ELSE 0\|KEY-ELSE\|MENU-ELSE\|RUN-ELSE\|PICK-ELSE\|ASK-ELSE\|WAIT-ELSE end\|"), out[-500:])
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
        parts = only[0].split(",") if only else ["owned", "dialogs", "forms", "events"]
        if "owned" in parts:
            part_owned(box)
        if "dialogs" in parts:
            part_dialogs(box)
        if "forms" in parts:
            part_forms(box)
            part_forms2(box)
        if "events" in parts:
            part_events(box)

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
