#!/usr/bin/env python3
#
# sandbox-ced.py - the data collection editor, CED and !CED().  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-ced.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty
# or absent); without it <dir> must already be built, which is how the same script is run against an OLD tree to
# prove it can fail.  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 12 Oct 26 dm  Written with CED (gpl.bp/ced, ced_edit, ced_sub), from the keys on the openQM pages for CED and !CED().
# 18 Oct 26 dm  The window is 140 by 42 (CED is laid out for it and refuses a smaller one, plan-terminal-140x42.md phase 3): the default
#               size of Ced(), the width at which the scroll bar is cut off, the page of 37 elements, and the piped session that
#               ends its input.  The refusal, the shrink and the cursor lock are sandbox-ide-small.py's.
# 29 Oct 26 dm  S.88 g-P1: the `ced` verb is no longer shipped (gpl.bp/ced is an unshipped test driver), so the run writes the VOC record
#               itself with cedverb.install() after the sandbox starts; a failure to write it is exit 2.  WRITTEN, NOT RUN.
# END-HISTORY
#
# HOW IT DRIVES THE EDITOR.  On a PSEUDO-TERMINAL (ptydrive.py), not a pipe: SD reads a piped stdin a byte at a time
# with no timeout, so a lone Esc cannot be told from the start of a key sequence, and a terminal is also where Ctrl-C
# (SD's break key), Ctrl-S, Ctrl-Q and Ctrl-V can be taken by the tty driver before the program sees them - which is
# how the editor's use of them was found to need the break key switched off.  The terminal type is xterm and the keys
# are the sequences SD's terminfo gives it.  What the editor drew is read from a small screen emulator
# (termscreen.py), not from the byte stream: the rows, the '>' marker, the reverse video of the selected row, the
# path line and the message line.  What it DID to the data is read from the data afterwards (CT, a BASIC probe).
#
# Each scenario has a record of its own so that a record left locked by one cannot disturb the next; a session is
# always ended by quitting the editor, and a hang-up if it will not.

import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ptydrive import PtySession  # noqa: E402
import cedverb  # noqa: E402

TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
RUN = "%05d" % (os.getpid() % 100000)
C, O = "zzec" + RUN, "zzeo" + RUN                 # a collection file and an ordinary file
FIX, BANG = "zzefx" + RUN, "zzebg" + RUN           # the fixture program and the !CED() program
passed = failed = 0

UP, DOWN, LEFT, RIGHT = "\x1bOA", "\x1bOB", "\x1bOD", "\x1bOC"
F1, F3, F4, F5, F6, F7 = "\x1bOP", "\x1bOR", "\x1bOS", "\x1b[15~", "\x1b[17~", "\x1b[18~"
INS, DEL, HOME, END, PGUP, PGDN = "\x1b[2~", "\x1b[3~", "\x1b[1~", "\x1b[4~", "\x1b[5~", "\x1b[6~"
ESC, RET, BS = "\x1b", "\r", "\x7f"
CTRL_C, CTRL_X, CTRL_V, CTRL_S, CTRL_Q, CTRL_I, CTRL_U = "\x03", "\x18", "\x16", "\x13", "\x11", "\t", "\x15"

TEMPLATE = ('{"name":"Acme","n":5,"on":true,"off":false,"none":null,"tags":["a","b","c"],'
            '"sub":{"x":"deep","y":2}}')
NSCEN = 40                                           # records e01 .. e40, each a copy of TEMPLATE


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
    say("sandbox-ced: CANNOT RUN - " + msg)
    sys.exit(2)


def sess(box, *cmds):
    """A plain scripted session through a pipe, for setting up and reading back (no keys)."""
    say("    > " + " | ".join(cmds))
    p = subprocess.run([sys.executable, TOOL, box, "sess", os.path.join(box, "user_accounts")] + list(cmds),
                       capture_output=True, text=True, errors="replace", timeout=600)
    out = ANSI.sub("", p.stdout + p.stderr)
    return out.split(":TERM 200,9999", 1)[-1]


class Ced:
    """One run of a command on a pseudo-terminal: type to it, read its screen."""

    def __init__(self, box, cmd, cols=140, rows=42, pre=()):
        self.box = box
        self.cols = cols
        self.rows = rows
        env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"), TERM="xterm")
        self.s = PtySession([os.path.join(box, "sys", "bin", "sd")], os.path.join(box, "user_accounts"), env, cols, rows)
        self.s.settle(1.0)
        self.s.type("TERM xterm\r")
        self.s.type("TERM %d,%d\r" % (cols, rows))
        for c in pre:
            self.s.type(c + "\r", idle=0.8)
        self.log = [cmd]
        self.s.type(cmd + "\r", idle=0.7)

    def keys(self, *chunks):
        for chunk in chunks:
            self.log.append(chunk)
            self.s.type(chunk, idle=0.45)
        return self.lines()

    def lines(self):
        return self.s.screen.lines()

    def reverse(self, i):
        return self.s.screen.reverse(i)

    def text(self):
        return "\n".join(l for l in self.lines() if l.strip())

    def end(self):
        self.s.type("\rOFF\r", idle=0.5)
        self.s.finish()


def elements(lines):
    """[(marker, name, type, value)] from the element rows of the editor's screen (rows 2 up to the path line)."""
    out = []
    for l in lines[2:]:
        if l.startswith("Path:"):
            break
        if len(l) >= 140:
            l = l[:139]                   # the table's scroll bar is the last column (^ | # v), not part of a value
        m = re.match(r"^([> ]) ?(\S+)\s+(string|number|boolean|null|collection|array|\?)\s*(.*?)\s*$", l)
        if m:
            out.append(m.groups())
    return out


def names(lines):
    return [e[1] for e in elements(lines)]


def selected(lines):
    for e in elements(lines):
        if e[0] == ">":
            return e[1]
    return None


class Absent(dict):
    """by_name()'s result: asking for an element that is not on the screen gives ('<absent>', '<absent>') rather
    than stopping the whole run, so a row fails by itself when the editor is not there."""

    def __missing__(self, key):
        return ("<absent>", "<absent>")


def by_name(lines):
    return Absent((e[1], (e[2], e[3])) for e in elements(lines))


def nth(seq, i):
    """seq[i], or None when there is no such element."""
    try:
        return seq[i]
    except IndexError:
        return None


def path_of(lines):
    for l in lines:
        if l.startswith("Path:"):
            return l[5:].strip()
    return None


def dialog(lines):
    """The lines inside a box the library drew over the editor (+-----+ and | at its left), stripped, or [] if there is none."""
    for r, l in enumerate(lines):
        m = re.search(r"\+-[^|]*\+", l)
        if not m:
            continue
        a, b = m.start(), m.end()
        out = []
        for l2 in lines[r + 1:]:
            if len(l2) > a and l2[a] == "|":
                out.append(l2[a + 1:b - 1].strip())
            else:
                break
        if out:
            return out
    return []


def menu_choices(lines):
    """The entries of a pop-up menu on the screen as ['1=string', '2=number'], or []: rows that are a digit and a data type,
    set well in from the left (the editor's own rows start in column 0 or 1)."""
    out = []
    for l in lines:
        for m in re.finditer(r"(?<![\w.])([1-6]) (string|number|boolean|null|collection|array)(?![\w])", l):
            if m.start() >= 10:           # (the menu is drawn over the list, in the middle of the screen)
                out.append("%s=%s" % m.groups())
    return out


def message_of(lines):
    """What the editor is saying or asking.  A question in a dialogue: its prompt and the text typed, as 'Value: Acme'
    (a box with buttons: its first line).  Else the bottom line of the screen (the message line)."""
    d = dialog(lines)
    if d:
        if any(x.startswith("[") for x in d):
            return d[0]
        if len(d) >= 2:
            return (d[0] + ": " + d[1]).rstrip()
        return d[0]
    last = [l for l in lines if l.strip()]
    return last[-1].strip() if last else ""


def title_of(lines):
    return lines[0].strip() if lines else ""


def rec_json(box, fname, rid):
    """The record as JSON, read back by CT in an ordinary session (null if it is not there)."""
    out = sess(box, "CT %s %s" % (fname, rid))
    m = re.search(r"(?m)^%s %s\s*$(.*)" % (re.escape(fname), re.escape(rid)), out, re.S)
    if not m:
        return None
    body = m.group(1)
    body = re.sub(r"(?m)^:?OFF.*$|^exit .*$|^:.*$", "", body).strip()
    body = re.sub(r"(?m)^1: ", "", body)         # an ordinary file shows the text as line 1
    try:
        return json.loads(body)
    except ValueError:
        return body


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-ced.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-ced: sandbox %s" % box)
    say("sandbox-ced: tree    %s" % os.path.dirname(HERE))
    say("sandbox-ced: files   %s (collection) %s (ordinary)" % (C, O))
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-ced: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)
    if not cedverb.install(box):
        bail("the VOC record ced could not be written; every row that types CED would be red for that reason")

    fixture = """   execute 'DELETE.FILE %(c)s' capturing j0
   execute 'DELETE.FILE %(o)s' capturing j1
   execute 'CREATE.FILE %(c)s COLLECTION' capturing j2
   execute 'CREATE.FILE %(o)s' capturing j3
   open '%(c)s' to f else stop 'no collection file'
   open '%(o)s' to o else stop 'no ordinary file'
   t = '%(t)s'
   for i = 1 to %(n)d
      write jparse(t) on f, 'e':fmt(i, 'R%%2')
   next i
   s = '{'
   for i = 1 to 60
      s := '"k':fmt(i, 'R%%2'):'":':i:(if i < 60 then ',' else '')
   next i
   s := '}'
   write jparse(s) on f, 'big'
   write jparse('{"a/b":1,"ok":2}') on f, 'slash'
   write jparse('{}') on f, 'emptyobj'
   write jparse('[]') on f, 'emptyarr'
   write jparse('[10,20,30]') on f, 'arr'
   write '{"title": "from a text file", "count": 3}' on o, 'j1'
   write '{"title": "second text", "count": 4}' on o, 'j2'
   write 'this is not json' on o, 'bad'
   crt 'FIXTURE DONE'
end
""" % {"c": C, "o": O, "t": TEMPLATE, "n": NSCEN}
    bang = """   c = jparse('{"a":1,"b":"two"}')
   call !ced(c)
   crt 'AFTER ':jbuild(c)
end
"""
    for nm, body in ((FIX, fixture), (BANG, bang)):
        with open(os.path.join(sysd, "bp", nm), "w") as fh:
            fh.write(body)
    try:
        say("\n--- fixture --------------------------------------------------------------------------------------")
        out = sess(box, "BASIC bp %s" % FIX, "BASIC bp %s" % BANG, "RUN bp %s" % FIX)
        row("setup: both programs compiled and the fixture was made",
            len(re.findall(r"(?m)^Compiled 1 program\(s\) with no errors", out)) == 2 and "FIXTURE DONE" in out, out[-400:])
        if "FIXTURE DONE" not in out:
            bail("the fixture was not made:\n" + out[-600:])
        row("setup: the three programs of the editor are in the sandbox",
            all(os.path.isfile(os.path.join(sysd, "gpl.bp", p)) for p in ("ced", "ced_edit", "ced_sub")), "missing")

        n = [0]

        def scen():
            n[0] += 1
            return "e%02d" % n[0]

        # ---- display and movement ------------------------------------------------------------------------
        say("\n--- display and movement --------------------------------------------------------------------------")
        rid = scen()
        e = Ced(box, "CED %s %s" % (C, rid))
        L = e.lines()
        row("the title names the file and the record: 'Collection editor: <file> <id>'", title_of(L) == "Collection editor: %s %s" % (C, rid), title_of(L))
        row("the headings are Name, Type and Value", re.match(r"^\s*Name\s+Type\s+Value\s*$", L[1]) is not None, L[1])
        row("the top level is shown: names in order, each with its data type", names(L) == ["n", "name", "none", "off", "on", "sub", "tags"], repr(names(L)))
        bn = by_name(L)
        row("the values are shown: a string, a number, a boolean, a null",
            bn.get("name") == ("string", "Acme") and bn.get("n") == ("number", "5") and bn.get("on") == ("boolean", "true")
            and bn.get("off") == ("boolean", "false") and bn.get("none") == ("null", "null"), repr(bn))
        row("a collection shows how many elements it has, an array likewise",
            bn.get("sub") == ("collection", "{2}") and bn.get("tags") == ("array", "[3]"), repr(bn))
        row("the first element is marked with '>' in the left column", selected(L) == "n" and [x[0] for x in elements(L)].count(">") == 1, repr(elements(L)[:2]))
        row("...and its row is drawn in reverse video", e.reverse(2).startswith(">") and "n" in e.reverse(2), repr(e.reverse(2)))
        row("the path line says '/' at the top level", path_of(L) == "/", repr(path_of(L)))
        L = e.keys(DOWN)
        row("Cursor down selects the next element", selected(L) == "name", repr(selected(L)))
        L = e.keys(UP)
        row("Cursor up goes back", selected(L) == "n", repr(selected(L)))
        L = e.keys(UP)
        row("Cursor up on the first element stays on it", selected(L) == "n", repr(selected(L)))
        L = e.keys(END)
        row("End selects the last element", selected(L) == "tags", repr(selected(L)))
        L = e.keys(HOME)
        row("Home selects the first", selected(L) == "n", repr(selected(L)))
        L = e.keys(DOWN * 5, RET)
        row("Return on a collection dives into it: its elements, and the path says /sub",
            path_of(L) == "/sub" and names(L) == ["x", "y"] and selected(L) == "x", "%r %r" % (path_of(L), names(L)))
        L = e.keys(ESC)
        row("Esc returns to the parent, with the element dived into selected again", path_of(L) == "/" and selected(L) == "sub", "%r %r" % (path_of(L), selected(L)))
        L = e.keys(DOWN, RET)
        row("Return on an array dives in: the positions are the names",
            path_of(L) == "/tags" and names(L) == ["1", "2", "3"] and by_name(L)["2"] == ("string", "b"), "%r %r" % (path_of(L), by_name(L)))
        L = e.keys(ESC, ESC)
        row("Esc at the top level does nothing (it does not leave the editor)", path_of(L) == "/" and title_of(L).startswith("Collection editor"), repr(path_of(L)))
        L = e.keys(DOWN, RET, "q")
        row("Q below the top level is not a quit", path_of(L) == "/sub" or path_of(L) == "/tags", repr(path_of(L)))
        L = e.keys(F1)
        row("F1 shows the help in a box over the list, which names the keys and has an OK button",
            "Ctrl-Q" in e.text() and "Ins or Ctrl-I" in e.text() and "F5 or Ctrl-C" in e.text() and "[ OK ]" in e.text(), e.text()[:300])
        L = e.keys(RET)
        row("Return (OK) closes it: the list and its path are back", "[ OK ]" not in e.text() and "Path:" in e.text(), e.text()[-200:])
        e.keys(CTRL_Q)
        e.end()

        # ---- paging ---------------------------------------------------------------------------------------
        say("\n--- paging ---------------------------------------------------------------------------------------")
        e = Ced(box, "CED %s big" % C)
        L = e.lines()
        per = len(names(L))
        row("a window of 42 lines shows 37 elements at a time", per == 37 and nth(names(L), 0) == "k01", repr(names(L)))
        L = e.keys(PGDN)
        row("Page down moves to the next page", nth(names(L), 0) == "k38" and selected(L) == "k38", "%r %r" % (names(L)[:2], selected(L)))
        L = e.keys(PGUP)
        row("Page up moves back", nth(names(L), 0) == "k01" and selected(L) == "k01", "%r %r" % (names(L)[:2], selected(L)))
        L = e.keys(END)
        row("End goes to the last element and shows the last page", selected(L) == "k60" and nth(names(L), -1) == "k60", "%r %r" % (names(L)[-2:], selected(L)))
        L = e.keys(DOWN)
        row("Cursor down at the last element stays on it", selected(L) == "k60", repr(selected(L)))
        e.keys(CTRL_Q)
        e.end()

        # ---- changing a value -------------------------------------------------------------------------------
        say("\n--- changing a value ------------------------------------------------------------------------------")
        rid = scen()
        e = Ced(box, "CED %s %s" % (C, rid))
        e.keys(DOWN, RET)
        L = e.lines()
        row("Return on a string asks for the value, starting from the old one", message_of(L) == "Value: Acme", message_of(L))
        L = e.keys(BS * 4, "Zed", RET)
        row("a new value replaces it and the title says the record has changed (*)", by_name(L)["name"] == ("string", "Zed") and title_of(L).endswith("*"), "%r %r" % (by_name(L).get("name"), title_of(L)))
        L = e.keys(UP, RET, BS, "x7", RET)
        row("a number must be a number: 'x7' is refused, with the message, and the prompt stays",
            "That is not a number" in e.text() and message_of(e.lines()) == "Value: x7", e.text()[-200:])
        L = e.keys(CTRL_U, "7.5", RET)
        row("Ctrl-U clears the line; a valid number is stored as a number", by_name(L)["n"] == ("number", "7.5"), repr(by_name(L).get("n")))
        L = e.keys(DOWN * 3, RET)
        row("a boolean is edited as true or false", message_of(L) == "Value: false", message_of(L))
        L = e.keys(CTRL_U, "maybe", RET)
        row("'maybe' is refused for a boolean", "That is not true or false" in e.text(), e.text()[-200:])
        L = e.keys(CTRL_U, "TRUE", RET)
        row("'TRUE' is accepted, in any case", by_name(L)["off"] == ("boolean", "true"), repr(by_name(L).get("off")))
        L = e.keys(UP, RET)
        row("a null cannot be edited, and the message says how to change its type", "A null cannot be edited" in e.text() and "none" == selected(L), e.text()[-200:])
        L = e.keys(UP, RET, ESC)
        row("Esc in the value prompt leaves the value as it was", by_name(L)["name"] == ("string", "Zed") and "Value:" not in e.text(), repr(by_name(L).get("name")))
        L = e.keys(RET, LEFT, LEFT, "X", END, "Y", HOME, "W", RET)
        row("the line editor: Left, End and Home move the cursor, and typing inserts there (Zed -> WZXedY)",
            by_name(L)["name"] == ("string", "WZXedY"), repr(by_name(L).get("name")))
        e.keys(CTRL_Q, "N")
        e.end()
        row("quitting with N throws the changes away: the record in the file is as it was",
            rec_json(box, C, rid) == json.loads(TEMPLATE), repr(rec_json(box, C, rid)))

        # ---- rename ------------------------------------------------------------------------------------------
        say("\n--- rename ----------------------------------------------------------------------------------------")
        rid = scen()
        e = Ced(box, "CED %s %s" % (C, rid))
        L = e.keys(F3)
        row("F3 asks for the new name, starting from the old", message_of(L) == "New name: n", message_of(L))
        L = e.keys(BS, "zz", RET)
        row("the element has the new name, which puts it in its new place, and it stays selected",
            names(L) == ["name", "none", "off", "on", "sub", "tags", "zz"] and selected(L) == "zz", "%r %r" % (names(L), selected(L)))
        L = e.keys(F3, CTRL_U, "name", RET)
        row("a name that is already there is refused", "That name is already in use" in e.text(), e.text()[-200:])
        L = e.keys(F3, CTRL_U, "a/b", RET)
        row("a name with a slash is refused", "must not be empty or contain a slash" in e.text(), e.text()[-200:])
        L = e.keys(F3, CTRL_U, RET)
        row("an empty name is refused", "must not be empty or contain a slash" in e.text(), e.text()[-200:])
        L = e.keys(F3, ESC)
        row("Esc cancels the rename", selected(L) == "zz", repr(selected(L)))
        L = e.keys(UP, RET, DOWN, F3)
        row("the elements of an array have no names to change", path_of(e.lines()) == "/tags" and "no names to change" in e.text(), e.text()[-200:])
        e.keys(ESC, CTRL_Q, "N")
        e.end()

        # ---- change type -------------------------------------------------------------------------------------
        say("\n--- change type -----------------------------------------------------------------------------------")
        rid = scen()
        e = Ced(box, "CED %s %s" % (C, rid))
        L = e.keys(F4)
        row("F4 on a number offers only string (5 is not a boolean)", menu_choices(L) == ["1=string"], repr(menu_choices(L)))
        L = e.keys("1")
        row("choosing 1 makes the number a string", by_name(L)["n"] == ("string", "5"), repr(by_name(L).get("n")))
        L = e.keys(F4)
        row("a string that is a number offers number (and not boolean or null)", menu_choices(L) == ["1=number"], repr(menu_choices(L)))
        L = e.keys("1")
        row("...and the number comes back", by_name(L)["n"] == ("number", "5"), repr(by_name(L).get("n")))
        L = e.keys(DOWN, F4)
        row("a string that is not a number or JSON offers nothing, and the editor says so",
            "The type of this element cannot be changed" in e.text(), e.text()[-200:])
        L = e.keys(DOWN * 2, F4)
        row("a boolean offers string and number", menu_choices(L) == ["1=string", "2=number"], repr(menu_choices(L)))
        L = e.keys("2")
        row("a boolean made a number is 1 or 0", by_name(L)["off"] == ("number", "0"), repr(by_name(L).get("off")))
        L = e.keys(UP, F4, "1")
        row("a null offers string: it becomes an empty string", by_name(L)["none"] == ("string", ""), repr(by_name(L).get("none")))
        L = e.keys(F4)
        row("an empty string offers null", "1=null" in menu_choices(L), repr(menu_choices(L)))
        L = e.keys("1")
        row("...and is a null again", by_name(L)["none"] == ("null", "null"), repr(by_name(L).get("none")))
        L = e.keys(DOWN * 4, F4)
        row("an array offers collection and string", menu_choices(L) == ["1=string", "2=collection"], repr(menu_choices(L)))
        L = e.keys("2")
        row("an array made a collection has its positions for names", by_name(L)["tags"] == ("collection", "{3}"), repr(by_name(L).get("tags")))
        L = e.keys(F4)
        row("...and a collection of that kind offers an array again", "2=array" in menu_choices(L), repr(menu_choices(L)))
        L = e.keys("2")
        row("...which it becomes", by_name(L)["tags"] == ("array", "[3]"), repr(by_name(L).get("tags")))
        L = e.keys(F4, "9")
        row("a choice that is not offered is not taken (the menu stays)", len(menu_choices(e.lines())) > 0, repr(menu_choices(e.lines())))
        menu_was_open = len(menu_choices(e.lines())) > 0
        L = e.keys(ESC)
        row("Esc cancels the menu", menu_was_open and not menu_choices(e.lines()) and "Collection editor" in e.text(), e.text()[-150:])
        e.keys(CTRL_Q, "N")
        e.end()

        # ---- insert, delete, copy, cut, paste -------------------------------------------------------------------
        say("\n--- insert, delete, copy, cut, paste ---------------------------------------------------------------")
        rid = scen()
        e = Ced(box, "CED %s %s" % (C, rid))
        L = e.keys(INS)
        row("Ins asks for a name", message_of(L) == "New name:", message_of(L))
        L = e.keys("aa", RET)
        row("...then a type, from all six", menu_choices(L) == ["1=string", "2=number", "3=boolean", "4=null", "5=collection", "6=array"], repr(menu_choices(L)))
        L = e.keys("1")
        row("...then a value", message_of(L) == "Value:", message_of(L))
        L = e.keys("hello", RET)
        row("the new string element is there, and selected", by_name(L).get("aa") == ("string", "hello") and selected(L) == "aa", "%r %r" % (by_name(L).get("aa"), selected(L)))
        L = e.keys(CTRL_I, "bb", RET, "2", "42", RET)
        row("Ctrl-I inserts too; a number element", by_name(L).get("bb") == ("number", "42"), repr(by_name(L).get("bb")))
        L = e.keys(INS, "cc", RET, "3")
        row("a boolean element starts from false in the value prompt", message_of(L) == "Value: false", message_of(L))
        L = e.keys(CTRL_U, "true", RET)
        row("...and 'true' makes it true", by_name(L).get("cc") == ("boolean", "true"), repr(by_name(L).get("cc")))
        L = e.keys(INS, "dd", RET, "4")
        row("a null element has no value to ask for", by_name(L).get("dd") == ("null", "null"), repr(by_name(L).get("dd")))
        L = e.keys(INS, "ee", RET, "5")
        row("a collection is inserted empty", by_name(L).get("ee") == ("collection", "{0}"), repr(by_name(L).get("ee")))
        L = e.keys(INS, "ff", RET, "6")
        row("an array is inserted empty", by_name(L).get("ff") == ("array", "[0]"), repr(by_name(L).get("ff")))
        L = e.keys(INS, "aa", RET)
        row("inserting a name that is there is refused", "That name is already in use" in e.text(), e.text()[-200:])
        L = e.keys(DOWN)
        e.keys(ESC)
        sel0 = selected(e.lines())
        L = e.keys(DEL)
        row("Del deletes the selected element at once, without asking", sel0 is not None and sel0 not in names(L) and len(names(L)) > 0, "%r %r" % (sel0, names(L)))
        L = e.keys(END, F5)
        row("F5 copies (the element stays)", "tags" in names(L) or len(names(L)) > 0, repr(names(L)))
        copied = selected(L) or "?"
        L = e.keys(F7)
        row("F7 asks for a name for the pasted element, starting from the copied one's", message_of(L) == "New name: %s" % copied, message_of(L))
        L = e.keys(RET)
        row("pasting under a name that is there is refused", "already in use" in e.text(), e.text()[-200:])
        L = e.keys(F7, "2", RET)
        row("pasting under a new name makes the copy", (copied + "2") in names(L) and copied in names(L), repr(names(L)))
        L = e.keys(F6)
        row("F6 cuts: the selected element is gone", copied != "?" and (copied + "2") not in names(L) and copied in names(L), repr(names(L)))
        L = e.keys(F7, "3", RET)
        row("...and F7 puts it back under another name (the cut one's name with the 3 typed after it)", (copied + "23") in names(L), repr(names(L)))
        e.keys(CTRL_Q, "N")
        e.end()
        rid = scen()
        e = Ced(box, "CED %s %s" % (C, rid))
        L = e.keys(F7)
        row("F7 with nothing copied says so", "Nothing has been copied or cut" in e.text(), e.text()[-200:])
        e.keys(CTRL_Q)
        e.end()

        # ---- arrays ------------------------------------------------------------------------------------------
        say("\n--- arrays ----------------------------------------------------------------------------------------")
        rid = scen()
        e = Ced(box, "CED %s %s" % (C, rid))
        e.keys(END, RET)
        L = e.keys(INS)
        row("Ins in an array asks for a position, 1 to one more than there are", message_of(L) == "Position (1 to 4): 4", message_of(L))
        L = e.keys(RET, "1", "d", RET)
        row("the default position is the end: the new element is number 4", by_name(L).get("4") == ("string", "d"), repr(by_name(L)))
        L = e.keys(INS, CTRL_U, "1", RET, "1", "first", RET)
        row("a position inside the array pushes the later ones along", [by_name(L)[k][1] for k in ("1", "2", "3", "4", "5")] == ["first", "a", "b", "c", "d"], repr(by_name(L)))
        L = e.keys(INS, CTRL_U, "9", RET)
        row("a position beyond the end is refused", "Position (1 to 6)" in e.text() and "9" not in names(L), e.text()[-200:])
        L = e.keys(UP, UP, UP, UP, UP, DEL)
        row("Del in an array closes it up: the later elements move down",
            [by_name(L)[k][1] for k in names(L)] == ["a", "b", "c", "d"], repr(by_name(L)))
        L = e.keys(F6)
        row("F6 on the first element of an array cuts it and closes the array up", [by_name(L)[k][1] for k in names(L)] == ["b", "c", "d"], repr(by_name(L)))
        L = e.keys(END, F7)
        row("pasting into an array asks for a position, starting from the selected one", message_of(L) == "Position (1 to 4): 3", message_of(L))
        L = e.keys(CTRL_U, "1", RET)
        row("...and puts the element there", [by_name(L)[k][1] for k in names(L)] == ["a", "b", "c", "d"], repr(by_name(L)))
        e.keys(ESC, CTRL_Q, "N")
        e.end()

        # ---- the Ctrl keys and the function keys ---------------------------------------------------------------
        say("\n--- the Ctrl keys (the terminal's break key and flow control are not in the way) ---------------------")
        rid = scen()
        e = Ced(box, "CED %s %s" % (C, rid))
        L = e.keys(CTRL_C, CTRL_V)
        row("Ctrl-C copies and Ctrl-V pastes (Ctrl-C did not break out of the program)", message_of(L) == "New name: n", message_of(L))
        L = e.keys("2", RET)
        row("...the copy is there", "n2" in names(L), repr(names(L)))
        L = e.keys(DOWN, CTRL_X)
        row("Ctrl-X cuts", "name" not in names(L) and "none" in names(L), repr(names(L)))
        L = e.keys(CTRL_S)
        row("Ctrl-S saves and carries on: the message says Saved and the title loses its mark",
            "Saved" in message_of(L) and not title_of(L).endswith("*"), "%r %r" % (message_of(L), title_of(L)))
        was_open = "Collection editor" in e.text()
        e.keys(CTRL_Q)
        L = e.lines()
        row("Ctrl-Q with nothing unsaved leaves the editor at once", was_open and "Collection editor" not in e.text(), e.text()[-200:])
        e.end()
        got = rec_json(box, C, rid)
        exp = json.loads(TEMPLATE)
        exp["n2"] = exp["n"]
        del exp["name"]
        row("what Ctrl-S saved is in the file: n2 added, name cut", got == exp, repr(got))

        # ---- saving and leaving -----------------------------------------------------------------------------
        say("\n--- saving and leaving ----------------------------------------------------------------------------")
        rid = scen()
        e = Ced(box, "CED %s %s" % (C, rid))
        e.keys(F3, BS, "zz", RET, "q")
        L = e.lines()
        row("Q at the top level with changes asks 'Save changes (Y/N)?'", message_of(L) == "Save changes (Y/N)?", message_of(L))
        L = e.keys(ESC)
        row("Esc there cancels the quit: the editor is still open", "Collection editor" in e.text(), e.text()[-150:])
        L = e.keys("q", "x")
        row("any other key is refused (the question stays)", message_of(e.lines()) == "Save changes (Y/N)?", message_of(e.lines()))
        question_was_open = message_of(e.lines()) == "Save changes (Y/N)?"
        e.keys("y")
        row("Y saves and leaves", question_was_open and "Collection editor" not in e.text(), e.text()[-150:])
        e.end()
        got = rec_json(box, C, rid)
        row("...the file has the change", isinstance(got, dict) and "zz" in got and "n" not in got, repr(got))
        rid = scen()
        e = Ced(box, "CED %s %s" % (C, rid))
        e.keys(DOWN * 5, RET, F3, BS, "yy", RET, CTRL_Q)
        row("Ctrl-Q from below the top level asks too", message_of(e.lines()) == "Save changes (Y/N)?", message_of(e.lines()))
        e.keys("N")
        e.end()
        row("...N leaves the file as it was", rec_json(box, C, rid) == json.loads(TEMPLATE), repr(rec_json(box, C, rid)))
        rid1, rid2 = scen(), scen()
        e = Ced(box, "CED %s %s %s" % (C, rid1, rid2))
        row("two ids: the first is opened first", rid1 in title_of(e.lines()), title_of(e.lines()))
        e.keys("q")
        row("Q at the top level goes on to the next id", rid2 in title_of(e.lines()), title_of(e.lines()))
        e.keys(CTRL_Q)
        e.end()
        e = Ced(box, "CED %s %s %s" % (C, rid1, rid2))
        was_open = rid1 in title_of(e.lines())
        e.keys(CTRL_Q)
        row("Ctrl-Q leaves the whole series: the second id is not opened", was_open and "Collection editor" not in e.text(), e.text()[-200:])
        e.end()

        # ---- the records it can edit -------------------------------------------------------------------------
        say("\n--- the records it can edit -----------------------------------------------------------------------")
        e = Ced(box, "CED %s j1" % O)
        L = e.lines()
        row("a JSON string in a record of an ordinary file is edited like a collection", title_of(L) == "Collection editor: %s j1" % O and names(L) == ["count", "title"], repr(names(L)))
        e.keys(F3, BS * 5, "total", RET, CTRL_S, CTRL_Q)
        e.end()
        got = rec_json(box, O, "j1")
        row("...and saved back as JSON text (compact)", got == {"total": 3, "title": "from a text file"}, repr(got))
        out = sess(box, "CT %s j1" % O)
        row("...in the ordinary file it is a line of text, not a collection", re.search(r'(?m)^1: \{"title":"from a text file","total":3\}', out) is not None, out[-300:])
        e = Ced(box, "CED %s bad" % O)
        row("a record that is not JSON is refused with a message and no editor",
            "is not a JSON object or array" in e.text() and "Collection editor" not in e.text(), e.text()[-200:])
        e.end()
        e = Ced(box, "CED %s freshobj" % C)
        row("a new record asks whether it is a collection or an array", "C = collection, A = array" in e.text(), e.text()[-200:])
        L = e.keys("C")
        row("C opens an empty collection", "Collection editor" in e.text() and names(L) == [], e.text()[-150:])
        e.keys(INS, "k", RET, "1", "v", RET, CTRL_S, CTRL_Q)
        e.end()
        row("...which Ctrl-S creates", rec_json(box, C, "freshobj") == {"k": "v"}, repr(rec_json(box, C, "freshobj")))
        e = Ced(box, "CED %s freshobj2" % C)
        e.keys("A", INS, RET, "2", "42", RET, CTRL_S, CTRL_Q)
        e.end()
        row("A makes a new array record", rec_json(box, C, "freshobj2") == [42], repr(rec_json(box, C, "freshobj2")))
        e = Ced(box, "CED %s nevermade" % C)
        asked = "C = collection, A = array" in e.text()
        e.keys(ESC)
        row("Esc at the question makes nothing", asked and "Collection editor" not in e.text(), e.text()[-150:])
        e.end()
        row("...and no record 'nevermade' exists", rec_json(box, C, "nevermade") is None, repr(rec_json(box, C, "nevermade")))
        e = Ced(box, "CED nosuchfile%s r1" % RUN)
        row("a file that is not there is reported", "File not found" in e.text(), e.text()[-150:])
        e.end()
        e = Ced(box, "CED %s" % C)
        row("with no ids and no select list it asks for them", "Record id:" in e.text(), e.text()[-150:])
        e.keys("arr", RET)
        row("...takes one and edits it", "Collection editor: %s arr" % C in e.text() and names(e.lines()) == ["1", "2", "3"], e.text()[:300])
        e.keys("q")
        row("...and asks again afterwards", "Record id:" in e.text(), e.text()[-150:])
        asked_again = "Record id:" in message_of(e.lines())
        e.keys(RET)
        row("a null id ends the command", asked_again and "Record id" not in message_of(e.lines()), message_of(e.lines()))
        e.end()
        e = Ced(box, "CED %s" % C, pre=("SELECT %s" % C,))
        row("with a select list active it takes the ids from that (the first record of the file opens)",
            title_of(e.lines()).startswith("Collection editor: %s " % C), title_of(e.lines()))
        e.keys(CTRL_Q)
        e.end()
        e = Ced(box, "CED %s e39" % C)
        e2 = Ced(box, "CED %s e39" % C)
        row("a record being edited by someone else is reported as locked and not opened",
            "is locked by user" in e2.text() and "Collection editor" not in e2.text(), e2.text()[-200:])
        e2.end()
        e.keys(CTRL_Q)
        e.end()
        e = Ced(box, "CED %s slash" % C)
        L = e.lines()
        row("an element whose name holds a slash is shown, and marked '?'", by_name(L).get("a/b", ("",))[0] == "?", repr(by_name(L)))
        L = e.keys(RET)
        row("...it cannot be edited here, and the message says why (no run time error)", "contains a slash" in e.text() and "Collection editor" in e.text(), e.text()[-200:])
        e.keys(F3, F4, F5, F6, DEL)
        row("...nor renamed, retyped, copied, cut or deleted", "Collection editor" in e.text() and "a/b" in names(e.lines()), e.text()[-200:])
        e.keys(CTRL_Q)
        e.end()
        e = Ced(box, "CED %s emptyobj" % C)
        row("an empty collection shows no elements and survives every key", names(e.lines()) == [] and (e.keys(RET, DEL, F3, F4, F5, F6, DOWN, UP) is not None) and "Collection editor" in e.text(), e.text()[-200:])
        e.keys(CTRL_Q)
        e.end()
        e = Ced(box, "CED %s emptyarr" % C)
        e.keys(INS)
        row("an empty array offers position 1", message_of(e.lines()) == "Position (1 to 1): 1", message_of(e.lines()))
        e.keys(ESC, CTRL_Q)
        e.end()

        # ---- !CED() ------------------------------------------------------------------------------------------
        say("\n--- CALL !CED(collection) --------------------------------------------------------------------------")
        e = Ced(box, "RUN bp %s" % BANG)
        row("the subroutine shows the collection it is given", title_of(e.lines()).startswith("Collection editor") and names(e.lines()) == ["a", "b"], repr(names(e.lines())))
        e.keys(RET, BS, "9", RET, CTRL_S, CTRL_Q)
        row("changes kept with Ctrl-S are in the variable on return", 'AFTER {"a":9,"b":"two"}' in e.text(), e.text()[-200:])
        e.end()
        e = Ced(box, "RUN bp %s" % BANG)
        e.keys(DOWN, RET, BS * 3, "X", RET, "q", "N")
        row("changes thrown away on leaving are not in the variable", 'AFTER {"a":1,"b":"two"}' in e.text(), e.text()[-200:])
        e.end()
        e = Ced(box, "RUN bp %s" % BANG)
        e.keys(DOWN, RET, BS * 3, "ONE", RET, CTRL_S, RET, BS * 5, "TWO", RET, "q", "N")
        row("...N after a Ctrl-S throws away only what came after it", 'AFTER {"a":1,"b":"ONE"}' in e.text(), e.text()[-200:])
        e.end()

        # ---- the terminal is given back, and a dead input does not hang it ------------------------------------
        say("\n--- the terminal, and an input that has ended -------------------------------------------------------")
        e = Ced(box, "CED %s e40" % C)
        ran = "Collection editor" in e.text()
        e.keys(CTRL_Q)
        e.s.type("PTERM DISPLAY\r", idle=0.8)
        row("after the editor the break key is trapped again (PTERM shows Break trapping: On)", ran and "Break trapping: On" in e.text(), e.text()[-300:])
        e.end()
        p = subprocess.run([os.path.join(sysd, "bin", "sd")], input=("\nTERM 140,42\nCED %s e38\n" % C).encode(), cwd=os.path.join(box, "user_accounts"),
                           env=dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf")), capture_output=True, timeout=90)
        row("when its input ends (a pipe, a dropped line) the editor gives up and the session ends: it does not loop",
            p.returncode == 0 and b"Collection editor" in p.stdout, "exit %s, editor drawn: %s" % (p.returncode, b"Collection editor" in p.stdout))
        row("...and it left the record alone", rec_json(box, C, "e38") == json.loads(TEMPLATE), repr(rec_json(box, C, "e38")))
    finally:
        say("\n--- cleanup ---------------------------------------------------------------------------------------")
        sess(box, "DELETE.FILE %s" % C, "DELETE.FILE %s" % O)
        for nm in (FIX, BANG):
            for d in ("bp", "bp.out"):
                pth = os.path.join(sysd, d, nm)
                if os.path.exists(pth):
                    os.remove(pth)
        left = [x for x in (C, O) if any(os.path.exists(os.path.join(box, d, x)) for d in ("sys", "user_accounts"))]
        row("cleanup: no fixture file is left", not left, " ".join(left))

    say("\nsandbox-ced: %d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        bail("no row ran - a broken test, not a pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
