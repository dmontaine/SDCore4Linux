#!/usr/bin/env python3
#
# sandbox-memoundo.py - the memo's undo and redo (S.88 phase 2, D3): a PROPERTY test of $sl_memo.  No install, no sudo.  WRITTEN 28 Oct 2026, NOT RUN (the owner's testing rule of that day:
# one complete run after the last phase).
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-memoundo.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or absent).  Exit 0 every row passed, 1 a row failed, 2 it could not
# run.
#
# START-HISTORY:
# 28 Oct 26 dm  Written for the structured undo steps of gpl.bp/sl_memo (plan 2.7, defect D3).
# END-HISTORY
#
# THE DEFECT.  The memo kept its undo steps as ONE string: a step's lines had their field marks turned into value marks, the stack was cut at field marks and a step at text marks.  A record whose
# lines held a value, subvalue or text mark (the IDE shows a record in the memo, and a record may hold them) came back from an undo changed: a value mark became a line end, a text mark cut
# the text short.  Now every step is a string of its own in the widget, the lines kept as they are.
#
# WHAT RUNS.  A BASIC program (bp zzmemoundo, compiled and run by an internal session) calls $sl_memo directly on a widget collection - 'init', then 'key' with names a person's keys have -
# and reads the widget's value back.  Nothing is drawn on a terminal that matters: the memo paints into a blank screen context and the output is discarded; every result is a TAG[...] line that
# starts a line of its own.  The properties, over 250 records from a seeded generator (randomize 20261028) made of a few lines of letters, a blank, the VALUE, SUBVALUE and TEXT marks and a
# CHAR(1), and a random run of 5 to 30 keys (typing a letter or a mark, Return, Backspace, Delete, the arrows, Home, End, select all, cut, paste, duplicate the line, cut the line):
#   UR     pressing Ctrl-Z until there is nothing left to undo gives the record the memo was started with, exactly
#   CUR    ... and the cursor is where it was when the FIRST step was taken (the first key that made one)
#   RY     pressing Ctrl-Y until there is nothing left to redo gives the text the keys ended with, exactly, and as many steps as were undone
#   MID    every text an undo or a redo gives is one the memo really had (it is in the list of the texts seen after each key); and k undos then k redos give the final text again
# CONTROLS (the instrument can fail): INSTR counts the keys that changed the text (it must be plenty, or UR ran against nothing), the records that held a mark in some text, and the
# records for which THE OLD ENCODING (field marks to value marks and back, which is what the old snap.make and snap.restore did to a step) gives a different text: it must be many, or
# this property could not have caught the defect.  The fixed rows: CAP (150 Returns keep the newest 100 steps, 250 undos then go back 100 and no further, and there are 100 redos), BIG (steps
# of about 30,000 characters keep at most a million characters, so about 33), CASE1-CASE6 (a record with marks and a few hand-made key runs: the record comes back exactly), LEGACY (a step put
# on the old key 'undo', as the IDE does for the change an AI edit makes, is read), SNAP (the 'snap' op), ZERO (Ctrl-Z and Ctrl-Y with nothing to undo change nothing), REDOCLEAR (a new edit
# ends the redo list).  A failing record is printed with ^ for a field mark, | for a value mark, ~ for a subvalue mark and # for the text mark.
# RED BEFORE: on the memo before this change UR fails on every record that holds a value mark or a text mark and CASE1-CASE6 fail; the rows that call the 'snap' op fail (no such op) and LEGACY
# fails (the old key was the stack).  Not measured: no run has been made.

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
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
    say("sandbox-memoundo: CANNOT RUN - " + msg)
    sys.exit(2)


def session(box, *cmds):
    say("    > " + " | ".join(cmds))
    env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"))
    body = "\nTERM 140,42\n" + "".join(c + "\n" for c in cmds) + "OFF\n"
    p = subprocess.run([os.path.join(box, "sys", "bin", "sd"), "-internal"], input=body, cwd=os.path.join(box, "sys"), env=env,
                       capture_output=True, text=True, errors="replace", timeout=1800)
    return ANSI.sub("", p.stdout + p.stderr)


def tag(out, name):
    m = re.search(r"(?m)^%s\[(.*)\]\s*$" % name, out)
    return None if m is None else m.group(1)


def counts(s):
    """'N=3000 BAD=0 FIRST=...' -> {'N': '3000', 'BAD': '0', 'FIRST': '...'}"""
    d = {}
    if s is None:
        return d
    for m in re.finditer(r"(\w+)=(\S*)", s):
        d[m.group(1)] = m.group(2)
    return d


def num(d, k):
    try:
        return int(d.get(k, "x"))
    except ValueError:
        return -1


# The test program.  (Names that are SD BASIC functions - exp, ln, alpha, count - are not used as variables; BASIC does not short-circuit AND and OR, and a comparison of two
# strings that look like numbers is numeric, so every comparison of texts is COMPARE().)
PROG = r"""$internal
   randomize 20261028
   chars = 'abXY 0_' : @vm : @sm : @tm : char(1)
   nchars = len(chars)
   marks = @fm : @vm : @sm : @tm
   shown = '^|~#'
   kl = 'enter' : @fm : 'bs' : @fm : 'del' : @fm : 'left' : @fm : 'right' : @fm : 'up' : @fm : 'down' : @fm : 'home' : @fm : 'end'
   kl := @fm : 'ctrl-a' : @fm : 'ctrl-x' : @fm : 'ctrl-v' : @fm : 'ctrl-d' : @fm : 'ctrl-k'
   nkl = dcount(kl, @fm)
   ntot = 250
   dim seen(80)
   call $sl_scr('get', scr)
   bad.ur = 0 ; bad.cur = 0 ; bad.ry = 0 ; bad.cnt = 0 ; bad.mid = 0 ; bad.mid2 = 0 ; first.bad = ''
   n.changes = 0 ; n.marked = 0 ; n.old.fail = 0 ; n.undone = 0 ; n.pushed = 0
   for t = 1 to ntot
      gosub gen.record
      gosub new.memo
      nseen = 1 ; seen(1) = r0
      old.fail = @false ; marked = @false
      sv = r0 ; gosub note.state
      nk = 5 + rnd(26)
      pushed.cy = 0 ; pushed.cx = 0 ; pushed.done = @false
      for kn = 1 to nk
         gosub random.key
         pre = w{'value'}
         pre.cy = w{'cy'} + 0 ; pre.cx = w{'cx'} + 0
         pre.id = (w{'ukb'} + 0) + (w{'ukn'} + 0)
         gosub do.key
         post = w{'value'}
         post.id = (w{'ukb'} + 0) + (w{'ukn'} + 0)
         if post.id > pre.id and not(pushed.done) then
            pushed.done = @true
            pushed.cy = pre.cy ; pushed.cx = pre.cx
         end
         if compare(post, pre) # 0 then
            n.changes += 1
            nseen += 1 ; seen(nseen) = post
            sv = post ; gosub note.state
         end
      next kn
      fin.v = w{'value'}
      * all the way back
      nundo = 0
      loop
      while (w{'ukn'} + 0) > 0 and nundo < 150
         key.n = 'ctrl-z' ; gosub do.key
         nundo += 1
         st = w{'value'} ; gosub in.seen
         if not(found) then bad.mid += 1
      repeat
      n.undone += nundo
      if marked then n.marked += 1
      if old.fail then n.old.fail += 1
      if compare(w{'value'}, r0) # 0 then
         bad.ur += 1
         if first.bad = '' then first.bad = r0 : '  GOT ' : w{'value'}
      end
      if pushed.done then
         n.pushed += 1
         if (w{'cy'} + 0) # pushed.cy or (w{'cx'} + 0) # pushed.cx then bad.cur += 1
      end
      * all the way on
      nredo = 0
      loop
      while (w{'rkn'} + 0) > 0 and nredo < 150
         key.n = 'ctrl-y' ; gosub do.key
         nredo += 1
         st = w{'value'} ; gosub in.seen
         if not(found) then bad.mid += 1
      repeat
      if compare(w{'value'}, fin.v) # 0 then bad.ry += 1
      if nredo # nundo then bad.cnt += 1
      * k undos then k redos
      kk = rnd(6) + 1
      did = 0
      for jj = 1 to kk
         if (w{'ukn'} + 0) > 0 then
            key.n = 'ctrl-z' ; gosub do.key
            did += 1
         end
      next jj
      for jj = 1 to did
         key.n = 'ctrl-y' ; gosub do.key
      next jj
      if compare(w{'value'}, fin.v) # 0 then bad.mid2 += 1
   next t
   crt char(10) : 'UR[N=':ntot:' BAD=':bad.ur:' FIRST=':convert(marks, shown, first.bad):']'
   crt char(10) : 'CUR[N=':n.pushed:' BAD=':bad.cur:']'
   crt char(10) : 'RY[N=':ntot:' BAD=':bad.ry:' COUNTS=':bad.cnt:']'
   crt char(10) : 'MID[N=':ntot:' BAD=':bad.mid:' BACKON=':bad.mid2:']'
   crt char(10) : 'INSTR[CHANGES=':n.changes:' UNDONE=':n.undone:' MARKED=':n.marked:' OLDFAIL=':n.old.fail:']'
   gosub cap.test
   gosub big.test
   gosub cases
   gosub legacy.test
   gosub snap.test
   gosub zero.test
   gosub redoclear.test
   crt char(10) : 'END'
   stop

* a record of 1 to 5 lines, each of 0 to 8 characters from chars (marks among them)
gen.record:
   r0 = ''
   nln = 1 + rnd(5)
   for li = 1 to nln
      if li > 1 then r0 := @fm
      ll = rnd(9)
      for ci = 1 to ll
         r0 := chars[rnd(nchars) + 1, 1]
      next ci
   next li
   return

new.memo:
   w = collection()
   w{'value'} = r0
   w{'w'} = 40 ; w{'h'} = 8 ; w{'ax'} = 2 ; w{'ay'} = 2
   call $sl_memo('init', w, scr, '', ret)
   return

do.key:
   call $sl_memo('key', w, scr, key.n, ret)
   return

* four in ten keys are a typed character (a mark among them now and then), the rest a name from kl
random.key:
   if rnd(10) < 4 then
      key.n = chars[rnd(nchars) + 1, 1]
   end else
      key.n = kl<rnd(nkl) + 1>
   end
   return

* st is a text the memo gave back: found if it is one of the texts seen
in.seen:
   found = @false
   for si = 1 to nseen
      if compare(seen(si), st) = 0 then
         found = @true
         exit
      end
   next si
   return

* sv is a text the memo had: does it hold a mark, and would THE OLD ENCODING have damaged it (field marks to value marks and back; a text mark cut the step)
note.state:
   if index(sv, @vm, 1) or index(sv, @sm, 1) or index(sv, @tm, 1) then marked = @true
   if compare(convert(@vm, @fm, convert(@fm, @vm, sv)), sv) # 0 or index(sv, @tm, 1) then old.fail = @true
   return

* 150 Returns: the newest 100 steps are kept
cap.test:
   r0 = 'x'
   gosub new.memo
   for kn = 1 to 150
      key.n = 'enter' ; gosub do.key
   next kn
   crt char(10) : 'CAP1[STEPS=':(w{'ukn'} + 0):' LINES=':(count(w{'value'}, @fm) + 1):']'
   nun = 0
   loop
   while nun < 250
      key.n = 'ctrl-z' ; gosub do.key
      nun += 1
   repeat
   crt char(10) : 'CAP2[LINES=':(count(w{'value'}, @fm) + 1):' LEFT=':(w{'ukn'} + 0):' REDO=':(w{'rkn'} + 0):']'
   return

* a text of 30,000 characters and 60 Returns: the steps are over a million characters in all, so the oldest go
big.test:
   r0 = str('a', 30000)
   gosub new.memo
   for kn = 1 to 60
      key.n = 'enter' ; gosub do.key
   next kn
   crt char(10) : 'BIG[STEPS=':(w{'ukn'} + 0):' CHARS=':(w{'ukt'} + 0):' LINES=':(count(w{'value'}, @fm) + 1):']'
   return

* a record with marks and a few key runs: back to the record exactly.  ck = the keys, one to a field; the result is CASEn[SAME=1 CHANGED=1]
run.case:
   gosub new.memo
   for kn = 1 to dcount(ck, @fm)
      key.n = ck<kn> ; gosub do.key
   next kn
   mid = w{'value'}
   nun = 0
   loop
   while (w{'ukn'} + 0) > 0 and nun < 150
      key.n = 'ctrl-z' ; gosub do.key
      nun += 1
   repeat
   same = (if compare(w{'value'}, r0) = 0 then 1 else 0)
   changed = (if compare(mid, r0) # 0 then 1 else 0)
   crt char(10) : cname:'[SAME=':same:' CHANGED=':changed:']'
   return

cases:
   cname = 'CASE1' ; r0 = 'a' : @vm : 'b' : @fm : 'c' ; ck = 'x'
   gosub run.case
   cname = 'CASE2' ; r0 = 'a' : @tm : 'b' ; ck = 'x' : @fm : 'enter' : @fm : 'bs'
   gosub run.case
   cname = 'CASE3' ; r0 = 'p' : @sm : 'q' : @fm : char(1) : ' ' : @fm : '' ; ck = 'end' : @fm : 'y' : @fm : 'down' : @fm : 'z'
   gosub run.case
   cname = 'CASE4' ; r0 = @vm ; ck = 'end' : @fm : 'enter' : @fm : 'q'
   gosub run.case
   cname = 'CASE5' ; r0 = 'one' : @vm : 'two' : @fm : 'three' : @tm : 'four' : @fm : 'five' ; ck = 'ctrl-a' : @fm : 'ctrl-x' : @fm : 'ctrl-v' : @fm : 'x'
   gosub run.case
   cname = 'CASE6' ; r0 = 'k' : @vm : @vm : 'l' : @sm : @sm : @fm : @tm ; ck = 'ctrl-d' : @fm : 'ctrl-k' : @fm : 'del'
   gosub run.case
   return

* a step put on the old key (what the IDE did for an AI edit): the old form, fields cut at field marks, cursor line, text mark, place, text mark, the lines with value marks for line ends
legacy.test:
   r0 = 'one' : @fm : 'two'
   gosub new.memo
   w{'value'} = 'changed'
   w{'cy'} = 1 ; w{'cx'} = 3
   w{'undo'} = '2' : @tm : '4' : @tm : convert(@fm, @vm, r0) : @fm : ''
   w{'redo'} = ''
   key.n = 'ctrl-z' ; gosub do.key
   l1 = (if compare(w{'value'}, r0) = 0 then 1 else 0)
   l2 = w{'cy'} + 0 ; l3 = w{'cx'} + 0
   l4 = (if w{'undo'} = '' then 1 else 0)
   key.n = 'ctrl-y' ; gosub do.key
   l5 = (if compare(w{'value'}, 'changed') = 0 then 1 else 0)
   crt char(10) : 'LEGACY[SAME=':l1:' CY=':l2:' CX=':l3:' CLEARED=':l4:' REDO=':l5:']'
   return

* the 'snap' op: the text as it is goes on the steps, marks and all, and redo is forgotten
snap.test:
   r0 = 'p' : @vm : 'q' : @fm : 'r' : @tm : 's'
   gosub new.memo
   w{'cy'} = 2 ; w{'cx'} = 2
   call $sl_memo('snap', w, scr, '', ret)
   s1 = w{'ukn'} + 0
   w{'value'} = 'changed' ; w{'cy'} = 1 ; w{'cx'} = 4
   key.n = 'ctrl-z' ; gosub do.key
   s2 = (if compare(w{'value'}, r0) = 0 then 1 else 0)
   s3 = w{'cy'} + 0 ; s4 = w{'cx'} + 0
   key.n = 'ctrl-y' ; gosub do.key
   s5 = (if compare(w{'value'}, 'changed') = 0 then 1 else 0)
   crt char(10) : 'SNAP[STEPS=':s1:' SAME=':s2:' CY=':s3:' CX=':s4:' REDO=':s5:']'
   return

zero.test:
   r0 = 'a' : @vm : 'b' : @fm : 'c'
   gosub new.memo
   key.n = 'ctrl-z' ; gosub do.key
   z1 = (if compare(w{'value'}, r0) = 0 then 1 else 0)
   key.n = 'ctrl-y' ; gosub do.key
   z2 = (if compare(w{'value'}, r0) = 0 then 1 else 0)
   crt char(10) : 'ZERO[UNDO=':z1:' REDO=':z2:' STEPS=':(w{'ukn'} + 0):' REDOS=':(w{'rkn'} + 0):']'
   return

* undo, then a new edit: the redo list is gone, and Ctrl-Y changes nothing
redoclear.test:
   r0 = 'abc' : @vm : 'd'
   gosub new.memo
   key.n = 'x' ; gosub do.key
   key.n = 'ctrl-z' ; gosub do.key
   rc1 = w{'rkn'} + 0
   key.n = 'y' ; gosub do.key
   rc2 = w{'rkn'} + 0
   after = w{'value'}
   key.n = 'ctrl-y' ; gosub do.key
   rc3 = (if compare(w{'value'}, after) = 0 then 1 else 0)
   crt char(10) : 'REDOCLEAR[BEFORE=':rc1:' AFTER=':rc2:' UNCHANGED=':rc3:']'
   return
end
"""


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-memoundo.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-memoundo: sandbox %s" % box)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-memoundo: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    made = []
    try:
        with open(os.path.join(sysd, "bp", "zzmemoundo"), "w") as fh:
            fh.write(PROG)
        made.append("zzmemoundo")
        out = session(box, "BASIC bp zzmemoundo")
        row("setup: the test program compiles with no errors", "Compiled 1 program(s) with no errors" in out, out[-700:])
        if "Compiled 1 program(s) with no errors" not in out:
            bail("the test program did not compile:\n" + out[-900:])
        out = session(box, "RUN bp zzmemoundo")
        row("setup: control - the program ran to its end (it printed END)", re.search(r"(?m)^END\s*$", out) is not None, out[-400:])

        ur, cur, ry, mid, ins = (counts(tag(out, n)) for n in ("UR", "CUR", "RY", "MID", "INSTR"))
        row("INSTR (the instrument sees what it claims): at least 2,000 keys changed the text, at least 1,500 undos were pressed, at least 100 of the 250 records held a mark in some text, "
            "and the OLD encoding would have damaged the text of at least 60 of them (so UR could have caught the defect)",
            num(ins, "CHANGES") >= 2000 and num(ins, "UNDONE") >= 1500 and num(ins, "MARKED") >= 100 and num(ins, "OLDFAIL") >= 60, repr(tag(out, "INSTR")))
        row("UR: Ctrl-Z until nothing is left gives the record the memo started with, exactly, for all 250 records", ur.get("N") == "250" and ur.get("BAD") == "0", repr(tag(out, "UR")))
        row("CUR: ... with the cursor where it was when the first step was taken, and at least 200 records took a step", cur.get("BAD") == "0" and num(cur, "N") >= 200, repr(tag(out, "CUR")))
        row("RY: Ctrl-Y until nothing is left gives the text the keys ended with, exactly, and as many redos as there were undos", ry.get("N") == "250" and ry.get("BAD") == "0" and ry.get("COUNTS") == "0",
            repr(tag(out, "RY")))
        row("MID: every text an undo or a redo gave was one the memo had had, and k undos then k redos give the final text again", mid.get("N") == "250" and mid.get("BAD") == "0" and mid.get("BACKON") == "0",
            repr(tag(out, "MID")))

        c1, c2 = counts(tag(out, "CAP1")), counts(tag(out, "CAP2"))
        row("CAP1: 150 Returns keep the newest 100 steps (STEPS 100) and the text has 151 lines", c1.get("STEPS") == "100" and c1.get("LINES") == "151", repr(tag(out, "CAP1")))
        row("CAP2: 250 undos go back exactly 100 steps and no further: 51 lines, nothing left to undo, 100 to redo", c2.get("LINES") == "51" and c2.get("LEFT") == "0" and c2.get("REDO") == "100", repr(tag(out, "CAP2")))
        bg = counts(tag(out, "BIG"))
        row("BIG: steps of about 30,000 characters are kept to a million characters at most - between 30 and 34 steps, not 60, and the characters held do not pass 1,000,000",
            30 <= num(bg, "STEPS") <= 34 and 0 < num(bg, "CHARS") <= 1000000, repr(tag(out, "BIG")))
        for k in range(1, 7):
            cs = counts(tag(out, "CASE%d" % k))
            row("CASE%d: a record with marks and a few key runs comes back from Ctrl-Z exactly (and the keys did change it)" % k, cs.get("SAME") == "1" and cs.get("CHANGED") == "1", repr(tag(out, "CASE%d" % k)))
        lg = counts(tag(out, "LEGACY"))
        row("LEGACY: a step put on the old key 'undo' (what the IDE writes for an AI edit) is read: Ctrl-Z gives the old text, the cursor goes to line 2 place 4, the old key is emptied, and Ctrl-Y gives the change back",
            lg.get("SAME") == "1" and lg.get("CY") == "2" and lg.get("CX") == "4" and lg.get("CLEARED") == "1" and lg.get("REDO") == "1", repr(tag(out, "LEGACY")))
        sn = counts(tag(out, "SNAP"))
        row("SNAP: the 'snap' op makes one step with the marks kept; after the value is changed Ctrl-Z gives it back with the cursor at line 2 place 2, and Ctrl-Y gives the change",
            sn.get("STEPS") == "1" and sn.get("SAME") == "1" and sn.get("CY") == "2" and sn.get("CX") == "2" and sn.get("REDO") == "1", repr(tag(out, "SNAP")))
        zr = counts(tag(out, "ZERO"))
        row("ZERO: Ctrl-Z and Ctrl-Y with nothing to undo or redo leave the text alone", zr.get("UNDO") == "1" and zr.get("REDO") == "1" and zr.get("STEPS") == "0" and zr.get("REDOS") == "0", repr(tag(out, "ZERO")))
        rc = counts(tag(out, "REDOCLEAR"))
        row("REDOCLEAR: an undo leaves one step to redo (BEFORE 1), a new edit ends the list (AFTER 0), and Ctrl-Y then changes nothing", rc.get("BEFORE") == "1" and rc.get("AFTER") == "0" and rc.get("UNCHANGED") == "1",
            repr(tag(out, "REDOCLEAR")))
    finally:
        for nm in made:
            for d in ("bp", "bp.out"):
                p = os.path.join(sysd, d, nm)
                if os.path.exists(p):
                    os.remove(p)

    say("\nsandbox-memoundo: %d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        bail("no row ran - a broken test, not a pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
