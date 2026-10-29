#!/usr/bin/env python3
#
# sandbox-recarr.py - the one-editor plan, stage 1: a record as a nested array and back ($recarr), a PROPERTY test.  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-recarr.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or absent).  Exit 0 every row passed,
# 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 26 Oct 26 dm  Written for gpl.bp/recarr (the data mode of CED and the IDE's hand-over to it).
# 28 Oct 26 dm  The editor merge, stage B: the IDE's token form follows the record's KIND, so the token rows (E, F) open records of the DATA file zzrfd (read back by
#               a second probe), and a new row E0 holds that the same record in bp, a program, is never shown in the token form.  Written, NOT run.
# END-HISTORY
#
# WHAT IT PROVES.  CED edits a record as a tree, and the record comes back with its value and subvalue marks put in from the SHAPE of the tree alone.  That is only safe if
# the conversion loses nothing, so the property is the round trip, over 3,000 records from a seeded generator (randomize 20261026) that makes every shape the marks allow:
# empty fields, empty values, a trailing mark, a field of subvalues with no value mark, runs of marks, the text mark inside a text.  Four properties, each counted:
#   RT      to, then from, gives the record back, exactly
#   SHAPE   each field, value and subvalue is a string or an array exactly where the CANONICAL rule says (an array only where a mark is) - computed in the test, not by recarr
#   EDIT    one leaf set to a new text through the ARRAY gives the same record as `r<f,v,s> = text` on the record (the position means the same in both)
#   STRUCT  a value or a subvalue added at the end, or taken out, gives the same record as `r<f,-1> = x` / `del r<f,v>` (the documented forms) on the record
# AND IT SHOWS THAT IT CAN FAIL.  CTRL strips the trailing marks from what `from` gave - the commonest way a conversion could be lossy - and counts how many of the same
# records the RT comparison would then call different: it must be more than a few, or RT could not have caught that defect.  The CASE rows are hand-written records with the
# array they must make; the REFUSE rows are shapes a record cannot have (a number, a boolean, a null, a collection, a fourth level), which must be refused and make no text.
# A failing record is printed with ^ for a field mark, | for a value mark, ~ for a subvalue mark and # for the text mark.

import importlib.util
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
_spec = importlib.util.spec_from_file_location("sandbox_ide", os.path.join(HERE, "sandbox-ide.py"))
sb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sb)                      # the IDE's pseudo-terminal driver (Ide) and its key names

TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
RUN = "%05d" % (os.getpid() % 100000)
F12, INS, CTRL_U = "\x1b[24~", "\x1b[2~", "\x15"
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
    say("sandbox-recarr: CANNOT RUN - " + msg)
    sys.exit(2)


def session(box, *cmds):
    say("    > " + " | ".join(cmds))
    env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"))
    body = "\nTERM 200,9999\n" + "".join(c + "\n" for c in cmds) + "OFF\n"
    p = subprocess.run([os.path.join(box, "sys", "bin", "sd"), "-internal"], input=body, cwd=os.path.join(box, "sys"), env=env,
                       capture_output=True, text=True, errors="replace", timeout=600)
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


# The test program.  (Names that are SD BASIC functions - exp, ln, alpha - are not used as variables.)
PROG = r"""$internal
   randomize 20261026
   chars = 'abcdXYZ 0123_-.' : @tm : char(1)
   nchars = len(chars)
   marks = @fm : @vm : @sm : @tm
   shown = '^|~#'
   ntot = 3000
   bad.rt = 0 ; bad.shape = 0 ; bad.edit = 0 ; bad.struct = 0 ; n.edit = 0 ; n.struct = 0 ; lossy.caught = 0 ; n.bad.call = 0
   first.rt = '' ; first.shape = '' ; first.edit = '' ; first.struct = ''
   for t = 1 to ntot
      gosub gen.record
      call $recarr('to', r, arr, ok1)
      call $recarr('from', arr, back, ok2)
      if not(ok1) or not(ok2) then n.bad.call += 1
      if back # r then
         bad.rt += 1
         if first.rt = '' then first.rt = r
      end
      lossy = back
      loop
      while len(lossy) and index(@fm : @vm : @sm, lossy[len(lossy), 1], 1) do
         lossy = lossy[1, len(lossy) - 1]
      repeat
      if lossy # r then lossy.caught += 1
      gosub check.shape
      call $recarr('to', r, arr, ok1)
      gosub edit.one
      call $recarr('to', r, arr, ok1)
      gosub struct.one
   next t
   crt 'RT[N=':ntot:' BAD=':bad.rt:' CALLS=':n.bad.call:' FIRST=':convert(marks, shown, first.rt):']'
   crt 'SHAPE[N=':ntot:' BAD=':bad.shape:' FIRST=':convert(marks, shown, first.shape):']'
   crt 'EDIT[N=':n.edit:' BAD=':bad.edit:' FIRST=':convert(marks, shown, first.edit):']'
   crt 'STRUCT[N=':n.struct:' BAD=':bad.struct:' FIRST=':convert(marks, shown, first.struct):']'
   crt 'CTRL[N=':ntot:' CAUGHT=':lossy.caught:']'
   gosub cases
   gosub token.tests
   gosub refusals
   crt 'END'
   stop

gen.text:
   tx = ''
   tl = rnd(4)
   for ci = 1 to tl
      tx := chars[rnd(nchars) + 1, 1]
   next ci
   return

gen.record:
   r = ''
   nf = rnd(6)
   for fi = 1 to nf
      if fi > 1 then r := @fm
      k = rnd(5)
      begin case
         case k = 0
            null
         case k = 1
            gosub gen.text ; r := tx
         case k = 2
            nv = rnd(4) + 1
            for vi = 1 to nv
               if vi > 1 then r := @vm
               gosub gen.text ; r := tx
            next vi
         case k = 3
            nv = rnd(3) + 1
            for vi = 1 to nv
               if vi > 1 then r := @vm
               ns = rnd(4)
               if ns = 0 then
                  gosub gen.text ; r := tx
               end else
                  for si = 1 to ns + 1
                     if si > 1 then r := @sm
                     gosub gen.text ; r := tx
                  next si
               end
            next vi
         case 1
            ns = rnd(3) + 1
            for si = 1 to ns + 1
               if si > 1 then r := @sm
               gosub gen.text ; r := tx
            next si
      end case
   next fi
   return

* The shape the canonical rule asks for, worked out here from the record's marks, not by recarr
check.shape:
   bad = @false
   nf = dcount(r, @fm)
   if inmat(arr) # nf then bad = @true
   for fi = 1 to nf
      ft = r<fi>
      want = if index(ft, @vm, 1) or index(ft, @sm, 1) then 'array' else 'string'
      if fi <= inmat(arr) then
         if jtype(arr{fi}) # want then bad = @true
         if want = 'array' and jtype(arr{fi}) = 'array' then
            fa = arr{fi}
            nv = dcount(ft, @vm)
            if inmat(fa) # nv then bad = @true
            for vi = 1 to nv
               vt = ft<1, vi>
               wantv = if index(vt, @sm, 1) then 'array' else 'string'
               if vi <= inmat(fa) then
                  if jtype(fa{vi}) # wantv then bad = @true
                  if wantv = 'array' and jtype(fa{vi}) = 'array' then
                     va = fa{vi}
                     if inmat(va) # dcount(vt, @sm) then bad = @true
                  end
               end
            next vi
         end
      end
   next fi
   if bad then
      bad.shape += 1
      if first.shape = '' then first.shape = r
   end
   return

* One leaf set to a new text through the array; the same on the record by position
edit.one:
   nf = dcount(r, @fm)
   if nf = 0 then return
   fi = rnd(nf) + 1
   gosub gen.text ; tx2 = tx
   expect = r
   if jtype(arr{fi}) = 'string' then
      arr{fi} = tx2
      expect<fi> = tx2
   end else
      fa = arr{fi}
      nv = inmat(fa)
      vi = rnd(nv) + 1
      if jtype(fa{vi}) = 'string' then
         fa{vi} = tx2
         expect<fi, vi> = tx2
      end else
         va = fa{vi}
         ns = inmat(va)
         si = rnd(ns) + 1
         va{si} = tx2
         expect<fi, vi, si> = tx2
      end
   end
   call $recarr('from', arr, got, ok3)
   n.edit += 1
   if not(ok3) or got # expect then
      bad.edit += 1
      if first.edit = '' then first.edit = r : '  WANT ' : expect : '  GOT ' : got
   end
   return

* A value or a subvalue added at the end or taken out: the documented dynamic array forms on the record
struct.one:
   nf = dcount(r, @fm)
   if nf = 0 then return
   fi = rnd(nf) + 1
   if jtype(arr{fi}) # 'array' then return
   fa = arr{fi}
   nv = inmat(fa)
   op = rnd(4)
   expect = r
   done = @true
   begin case
      case op = 0
         fa{nv + 1} = 'NEW'
         expect<fi, -1> = 'NEW'
      case op = 1 and nv >= 2
         vi = rnd(nv) + 1
         del fa{vi}
         del expect<fi, vi>
      case op >= 2
         vi = rnd(nv) + 1
         if jtype(fa{vi}) = 'array' then
            va = fa{vi}
            ns = inmat(va)
            if op = 2 then
               va{ns + 1} = 'NEW'
               expect<fi, vi, -1> = 'NEW'
            end else
               if ns >= 2 then
                  si = rnd(ns) + 1
                  del va{si}
                  del expect<fi, vi, si>
               end else done = @false
            end
         end else done = @false
      case 1
         done = @false
   end case
   if done then
      call $recarr('from', arr, got, ok3)
      n.struct += 1
      if not(ok3) or got # expect then
         bad.struct += 1
         if first.struct = '' then first.struct = r : '  WANT ' : expect : '  GOT ' : got
      end
   end
   return

* The token form (26 Oct 26): a PROPERTY test over records made of the fragments that can be mistaken for a token, and hand-written cases.
gen.trecord:
   r = ''
   nf = rnd(4)
   for fi = 1 to nf
      if fi > 1 then r := @fm
      ni = rnd(6)
      for ii = 1 to ni
         tc = rnd(10)
         begin case
            case tc < 5
               fx = rnd(nfrag) + 1
               r := frag<fx>
               if rnd(2) then
                  fx = rnd(nfrag) + 1
                  r := frag<fx>
               end
            case tc < 7
               r := @vm
            case tc = 7
               r := @sm
            case 1
               r := @tm
         end case
      next ii
   next fi
   return

token.tests:
   frag = 'a' : @fm : 'b' : @fm : ':' : @fm : '@' : @fm : '@vm' : @fm : '@sm' : @fm : '@VM' : @fm : 'vm' : @fm : ' ' : @fm : 'x@' : @fm : ':@vm:' : @fm : '10:30' : @fm : '@tm' : @fm : '@v'
   nfrag = dcount(frag, @fm)
   t.ok = 0 ; t.ref = 0 ; t.bad = 0 ; t.unsound = 0 ; t.false.ref = 0 ; n.et = 0 ; bad.et = 0 ; t.first = ''
   for t = 1 to ntot
      gosub gen.trecord
      call $recarr('totext', r, tx, tk)
      if tk then
         t.ok += 1
         call $recarr('fromtext', tx, back, k9)
         if back # r then
            t.bad += 1
            if t.first = '' then t.first = r
         end
         * typing a token: a value mark and the text Z added to the end of the first line is the same record as adding that value to the first field
         if dcount(r, @fm) >= 1 then
            line1 = tx<1>
            if line1 = '' then ad = '@vm:Z' else ad = ':@vm:Z'
            nd = tx
            nd<1> = line1 : ad
            ex = r
            ex<1> = r<1> : @vm : 'Z'
            call $recarr('fromtext', nd, back2, k9)
            n.et += 1
            if back2 # ex then
               bad.et += 1
               if t.first = '' then t.first = r : '  WANT ' : ex : '  GOT ' : back2
            end
         end
      end else
         t.ref += 1
         fno = tx + 0
         if fno < 1 or fno > dcount(r, @fm) then
            t.unsound += 1
         end else
            if index(r<fno>, '@', 1) = 0 then t.unsound += 1
         end
      end
      if index(r, '@', 1) = 0 and not(tk) then t.false.ref += 1
   next t
   crt 'TOKRT[N=':ntot:' OK=':t.ok:' REF=':t.ref:' BAD=':t.bad:' FIRST=':convert(marks, shown, t.first):']'
   crt 'TOKSOUND[UNSOUND=':t.unsound:' FALSEREF=':t.false.ref:']'
   crt 'TOKEDIT[N=':n.et:' BAD=':bad.et:']'
   call $recarr('totext', 'Don' : @vm : 'Henry' : @vm : 'June', tx, tk)
   crt 'CASE12[':tx:' ':tk:']'
   call $recarr('totext', @vm, tx, tk)
   crt 'CASE13[':tx:' ':tk:']'
   call $recarr('totext', @vm : 'Henry', tx, tk)
   call $recarr('totext', 'Don' : @vm, tx2, tk)
   crt 'CASE14[':tx:' ':tx2:']'
   call $recarr('totext', 'a' : @vm : @vm : 'b', tx, tk)
   crt 'CASE15[':tx:' ':tk:']'
   call $recarr('totext', 'a' : @sm : 'b' : @tm : 'c', tx, tk)
   crt 'CASE16[':tx:' ':tk:']'
   call $recarr('totext', '10:30' : @vm : 'x', tx, tk)
   crt 'CASE17[':tx:' ':tk:']'
   call $recarr('totext', 'a' : @fm : 'b' : @vm : 'c', tx, tk)
   crt 'CASE18[':convert(@fm, '^', tx):' ':tk:']'
   call $recarr('fromtext', 'Don:@VM:Henry:@SM:x', rr, tk)
   crt 'CASE19[':convert(@vm : @sm, '|~', rr):']'
   rr0 = 'x@vm' : @vm : 'y'
   call $recarr('totext', rr0, tx, tk)
   call $recarr('fromtext', tx, rr, k9)
   crt 'CASE20[':tx:' ':tk:' ':(rr = rr0):']'
   call $recarr('totext', '@vm', tx, tk1)
   x1 = tx
   call $recarr('totext', 'a' : @fm : '@sm', tx, tk2)
   x2 = tx
   call $recarr('totext', '@vm:x', tx, tk3)
   crt 'CASE21[':tk1:' ':x1:' ':tk2:' ':x2:' ':tk3:' ':tx:']'
   rr0 = 'a:' : @vm : 'b'
   call $recarr('totext', rr0, tx, tk)
   call $recarr('fromtext', tx, rr, k9)
   crt 'CASE22[':tx:' ':tk:' ':(rr = rr0):']'
   call $recarr('fromtext', 'a:@vmx:b', rr, k9)
   call $recarr('fromtext', '@vm:', rr2, k9)
   crt 'CASE23[':rr:' ':convert(@vm, '|', rr2):']'
   return

* Hand-written records and the array each must make
cases:
   call $recarr('to', '', a, k1)
   crt 'CASE1[EMPTY ':inmat(a):' ':k1:']'
   call $recarr('to', 'x', a, k1)
   crt 'CASE2[ONE ':inmat(a):' ':jtype(a{1}):' ':a{1}:']'
   call $recarr('to', 'a' : @fm : 'b', a, k1)
   crt 'CASE3[TWO ':inmat(a):' ':jtype(a{1}):' ':jtype(a{2}):']'
   call $recarr('to', 'a' : @vm : 'b', a, k1)
   fa = a{1}
   crt 'CASE4[VALUES ':inmat(a):' ':jtype(a{1}):' ':inmat(fa):' ':fa{1}:' ':fa{2}:']'
   call $recarr('to', 'a' : @sm : 'b', a, k1)
   fa = a{1} ; va = fa{1}
   crt 'CASE5[SUBONLY ':jtype(a{1}):' ':inmat(fa):' ':jtype(fa{1}):' ':inmat(va):' ':va{1}:' ':va{2}:']'
   call $recarr('to', 'a' : @vm : 'b' : @sm : 'c' : @sm : 'd', a, k1)
   fa = a{1} ; va = fa{2}
   crt 'CASE6[MIXED ':inmat(fa):' ':jtype(fa{1}):' ':jtype(fa{2}):' ':inmat(va):' ':va{1}:' ':va{3}:']'
   call $recarr('to', @vm, a, k1)
   fa = a{1}
   crt 'CASE7[LONEVM ':inmat(fa):' [':fa{1}:'] [':fa{2}:']]'
   call $recarr('to', 'a' : @fm, a, k1)
   crt 'CASE8[TRAILFM ':inmat(a):' [':a{2}:']]'
   call $recarr('from', jparse('[]'), b, k1)
   crt 'CASE9[FROMEMPTY [':b:'] ':k1:']'
   call $recarr('to', '12' : @fm : '1.50' : @fm : '-3', a, k1)
   crt 'CASE10[NUMTEXT ':jtype(a{1}):' ':jtype(a{2}):' ':jtype(a{3}):']'
   call $recarr('from', a, b, k1)
   crt 'CASE11[NUMBACK ':convert(@fm, '^', b):' ':k1:']'
   return

* Shapes that are not a record's: refused, nothing made
refusals:
   n.ref = 0 ; n.ref.ok = 0
   bad.list = ''
   bad.list<-1> = '[1]'
   bad.list<-1> = '[true]'
   bad.list<-1> = '[null]'
   bad.list<-1> = '[{"a":1}]'
   bad.list<-1> = '[["x", 2]]'
   bad.list<-1> = '[[["x", ["too deep"]]]]'
   bad.list<-1> = '{"a":"b"}'
   for q = 1 to dcount(bad.list, @fm)
      c = jparse(bad.list<q>)
      call $recarr('from', c, b, k1)
      n.ref += 1
      if k1 = 0 and b = '' then n.ref.ok += 1
   next q
   crt 'REFUSE[N=':n.ref:' OK=':n.ref.ok:']'
   return
end
"""


def elements(L):
    """[(marker, name, type, value)] from the element rows of CED's screen (rows 2 up to the path line)."""
    out = []
    for l in L[2:]:
        if l.startswith("Path:"):
            break
        if len(l) >= 140:
            l = l[:139]                   # the table's scroll bar is the last column
        m = re.match(r"^([> ]) ?(\S+)\s+(string|array|\?)\s*(.*?)\s*$", l)
        if m:
            out.append(m.groups())
    return out


def path_of(L):
    for l in L:
        if l.startswith("Path:"):
            return l[5:].strip()
    return None


def bottom(L):
    last = [l for l in L if l.strip()]
    return last[-1].strip() if last else ""


def menu_choices(L):
    """The entries of the type menu drawn over the list: ['1=string', '2=array'] (set well in from the left)."""
    out = []
    for l in L:
        for m in re.finditer(r"(?<![\w.])([1-6]) (string|number|boolean|null|collection|array)(?![\w])", l):
            if m.start() >= 10:
                out.append("%s=%s" % m.groups())
    return out


FIELDS_FIX = """   open 'bp' to f else stop 'no bp'
   write 'Acme':@fm:'red':@vm:'dark':@sm:'green':@vm:'blue':@fm:'x' on f, 'zzrf%(r)sa'
   write 'one':@fm:'two':@vm:'three' on f, 'zzrf%(r)sb'
   write 'p':@fm:'q':@vm:'r':@sm:'s':@fm:'t' on f, 'zzrf%(r)sc'
   write 'x':@fm:'y':@vm:'z' on f, 'zzrf%(r)sd'
   write 'Don':@vm:'Henry':@vm:'June':@fm:'x':@sm:'y':@tm:'z' on f, 'zzrf%(r)se'
   write '@vm':@fm:'b':@vm:'c' on f, 'zzrf%(r)sf'
   crt 'FIXTURE DONE'
end
"""
FIELDS_PROBE = """   open 'bp' to f else stop 'no bp'
   ids = 'a':@fm:'b':@fm:'c':@fm:'d':@fm:'e':@fm:'f'
   for i = 1 to 6
      read r from f, 'zzrf%(r)s' : ids<i> else r = '<absent>'
      crt 'REC':i:'[':convert(@fm:@vm:@sm:@tm, '^|~#', r):']'
   next i
   crt 'END'
end
"""
# a data file that is not bp (so that the file name decides nothing), made in an ORDINARY session so that the IDE's account has it: two scripts, one with a first line #!/bin/sh and one without
FIELDS_FIX2 = """   execute 'DELETE.FILE zzrfd%(r)s' capturing j0
   execute 'CREATE.FILE zzrfd%(r)s' capturing j1
   open 'zzrfd%(r)s' to d else stop 'no data file'
   write '#!/bin/sh':@fm:'# a comment':@fm:'hello world' on d, 'script'
   write 'first line':@fm:'# a comment':@fm:'hello world' on d, 'plain'
   write 'Don':@vm:'Henry':@vm:'June':@fm:'x':@sm:'y':@tm:'z' on d, 'tokrec'
   write '@vm':@fm:'b':@vm:'c' on d, 'tokfix'
   crt 'FIXTURE2 DONE'
end
"""
# 28 Oct 26 (the editor merge, stage B): the token form follows the KIND of the record - a data record shows it, a program (bp) never does - so the token rows read
# records of the data file, through this probe, run as the fixture above is
FIELDS_PROBE2 = """   open 'zzrfd%(r)s' to d else stop 'no data file'
   ids = 'tokrec':@fm:'tokfix'
   for i = 1 to 2
      read r from d, ids<i> else r = '<absent>'
      crt 'DREC':i:'[':convert(@fm:@vm:@sm:@tm, '^|~#', r):']'
   next i
   crt 'END'
end
"""


def fields_part(box, sysd, made):
    """The IDE hands a record to CED's data mode (F12) as fields, values and subvalues, and takes it back; the IDE saves."""
    say("\n--- the IDE hands a record to CED as fields (F12), CED edits it as a tree, the IDE takes it back and saves it ------------")
    ra, rb, rc, rd, re_, rf_ = ("zzrf%s%s" % (RUN, c) for c in "abcdef")
    dfile = "zzrfd" + RUN
    fix, probe = "zzrffix" + RUN, "zzrfprobe" + RUN
    for nm, body in ((fix, FIELDS_FIX), (probe, FIELDS_PROBE), (fix + "b", FIELDS_FIX2), (probe + "b", FIELDS_PROBE2)):
        with open(os.path.join(sysd, "bp", nm), "w") as fh:
            fh.write(body % {"r": RUN})
        made.append(nm)
    made.extend([ra, rb, rc, rd, re_, rf_])
    out = session(box, "BASIC bp %s" % fix, "BASIC bp %s" % probe, "RUN bp %s" % fix)
    row("setup: the fixture and the probe compile and the four multivalue records were written",
        len(re.findall(r"(?m)^Compiled 1 program\(s\) with no errors", out)) == 2 and "FIXTURE DONE" in out, out[-400:])
    if "FIXTURE DONE" not in out:
        bail("the IDE fixture was not made:\n" + out[-600:])

    def disk():
        o = session(box, "RUN bp %s" % probe)
        return [tag(o, "REC%d" % i) for i in (1, 2, 3, 4, 5, 6)]

    d0 = disk()
    row("control: the probe reads the six records as written (marks shown as ^ | ~ #)",
        d0 == ["Acme^red|dark~green|blue^x", "one^two|three", "p^q|r~s^t", "x^y|z", "Don|Henry|June^x~y#z", "@vm^b|c"], repr(d0))
    o2 = sb.sess(box, "BASIC bp %s" % (fix + "b"), "RUN bp %s" % (fix + "b"), "BASIC bp %s" % (probe + "b"))
    row("setup: the second fixture (an ordinary session) made the data file %s with its two scripts and its two token records, and its probe compiled" % dfile,
        "FIXTURE2 DONE" in o2 and len(re.findall(r"(?m)^Compiled 1 program\(s\) with no errors", o2)) == 2, o2[-300:])

    def ddisk():
        o = sb.sess(box, "RUN bp %s" % (probe + "b"))
        return [tag(o, "DREC%d" % i) for i in (1, 2)]

    dd0 = ddisk()
    row("control: the second probe reads the data file's token records as written", dd0 == ["Don|Henry|June^x~y#z", "@vm^b|c"], repr(dd0))

    e = sb.Ide(box)
    e.keys(F12)
    row("F12 on the bare IDE's Untitled buffer asks for a file and a record first (the name form), and CED is not started (S.88 Phase 4: there is always a buffer now; it said 'No record is open')",
        "Name of the new record" in e.text() and not bottom(e.lines()).startswith("Collection editor"), e.status())
    e.keys("\x1b")
    e.end()

    # ---- A: look, dive, the type menu by level, edit a subvalue, Ctrl-S, back to the IDE, the IDE saves ---------------------------------
    e = sb.Ide(box, "IDE bp %s" % ra)
    e.quiet()
    L = e.keys(F12)
    el = elements(L)
    row("F12: CED shows the record as fields - the title names the record, the rows are the field numbers with string / array and the value",
        L[0].strip() == "Collection editor: bp %s" % ra and [(x[1], x[2], x[3]) for x in el] == [("1", "string", "Acme"), ("2", "array", "[3]"), ("3", "string", "x")],
        "%r %r" % (L[0].strip(), el))
    L = e.keys(sb.DOWN, sb.RET)
    el = elements(L)
    row("a field of values dives into its values: /2 holds string red, an array of two subvalues, string blue",
        path_of(L) == "/2" and [(x[1], x[2], x[3]) for x in el] == [("1", "string", "red"), ("2", "array", "[2]"), ("3", "string", "blue")], "%r %r" % (path_of(L), el))
    L = e.keys(sb.DOWN, sb.RET)
    el = elements(L)
    row("a value of subvalues dives into them: /2/2 holds the strings dark and green",
        path_of(L) == "/2/2" and [(x[1], x[2], x[3]) for x in el] == [("1", "string", "dark"), ("2", "string", "green")], "%r %r" % (path_of(L), el))
    e.keys(INS)
    L = e.keys(sb.RET)
    row("Ins at the subvalue level offers one type, string (a subvalue is never a list)", menu_choices(L) == ["1=string"], repr(menu_choices(L)))
    e.keys(sb.ESC)
    L = e.keys(sb.ESC)
    row("Esc leaves the menu and then the level: back at /2", path_of(L) == "/2", repr(path_of(L)))
    e.keys(INS)
    L = e.keys(sb.RET)
    row("Ins at the value level offers string and array", menu_choices(L) == ["1=string", "2=array"], repr(menu_choices(L)))
    e.keys(sb.ESC)
    L = e.keys(sb.ESC)
    row("... and Esc returns to the top, /", path_of(L) == "/", repr(path_of(L)))
    L = e.keys(sb.RET, sb.DOWN, sb.RET, sb.DOWN, sb.RET)
    row("the subvalue green is asked for in a dialogue", any("green" in l for l in L), "\n".join(l for l in L if l.strip())[-300:])
    L = e.keys(CTRL_U, "lime", sb.RET)
    by = {x[1]: (x[2], x[3]) for x in elements(L)}
    row("the new text is shown: subvalue 2 is the string lime, and the title says the record is changed (a star)",
        by.get("2") == ("string", "lime") and L[0].rstrip().endswith("*"), "%r %r" % (by, L[0].strip()))
    L = e.keys(sb.CTRL_S)
    row("Ctrl-S keeps it: the star goes and the message line says Saved", not L[0].rstrip().endswith("*") and bottom(L) == "Saved", "%r %r" % (L[0].strip(), bottom(L)))
    d = disk()
    row("CED wrote nothing: the record on disk is as it was (the IDE has the save)", d[0] == d0[0], repr(d[0]))
    e.keys(sb.CTRL_Q)
    e.quiet()
    st = e.status()
    row("back in the IDE: the status line says the fields came back changed, and the tab is marked changed",
        "Back from the fields: bp %s is changed, save it to keep it" % ra in st and re.search(r"bp %s \*" % ra, st) is not None, st)
    d = disk()
    row("... and still nothing is on disk until the IDE saves", d[0] == d0[0], repr(d[0]))
    e.keys(sb.CTRL_S)                                  # the IDE's save key is Ctrl-S only (F2 went, S.88 Phase 4)
    st = e.status()
    d = disk()
    row("Ctrl-S in the IDE saves it: the status line says so and the record is Acme^red|dark~lime|blue^x - the subvalue mark in place, nobody typed it",
        ("Saved bp %s" % ra) in st and d[0] == "Acme^red|dark~lime|blue^x", "%r %r" % (st, d[0]))
    e.end()

    # ---- B: leave without changing anything ---------------------------------------------------------------------------------------------
    e = sb.Ide(box, "IDE bp %s" % rb)
    e.quiet()
    e.keys(F12)
    e.keys(sb.CTRL_Q)
    e.quiet()
    st = e.status()
    row("F12 and leave without a change: the IDE says the record is as it was, the tab is not marked changed, the disk is as it was",
        "Back from the fields: bp %s is as it was" % rb in st and re.search(r"bp %s \*" % rb, st) is None and disk()[1] == d0[1], "%r %r" % (st, disk()[1]))
    e.end()

    # ---- C: a paste that is not a record is refused; the leave-without-saving question throws the changes away ---------------------------
    e = sb.Ide(box, "IDE bp %s" % rc)
    e.quiet()
    e.keys(F12)
    e.keys(sb.DOWN, sb.F5)                             # copy field 2, an array holding an array
    e.keys(sb.RET)                                     # into /2, the level of values
    L = e.keys(sb.F7)
    row("pasting a field into the level of values is refused (message 11988: it would be a list below a subvalue) and the list is as it was",
        bottom(L).startswith("A record holds only text") and [x[1] for x in elements(L)] == ["1", "2"], "%r %r" % (bottom(L), [x[1] for x in elements(L)]))
    L = e.keys(sb.ESC, sb.F7)
    L = e.keys(sb.RET)
    el = elements(L)
    row("pasting it at the top is allowed: four fields, string array array string, and the title shows the star",
        [(x[1], x[2]) for x in el] == [("1", "string"), ("2", "array"), ("3", "array"), ("4", "string")] and L[0].rstrip().endswith("*"), "%r %r" % (el, L[0].strip()))
    e.keys(sb.CTRL_Q, "N")
    e.quiet()
    st = e.status()
    row("Ctrl-Q and No to the question throws the paste away: the IDE says as it was and the disk is as it was",
        "Back from the fields: bp %s is as it was" % rc in st and disk()[2] == d0[2], "%r %r" % (st, disk()[2]))
    e.end()

    # ---- D: Ctrl-S, then another change, then leave without saving: what comes back is what Ctrl-S kept -----------------------------------
    e = sb.Ide(box, "IDE bp %s" % rd)
    e.quiet()
    e.keys(F12)
    e.keys(sb.DOWN, sb.RET, sb.RET)
    e.keys(CTRL_U, "Y1", sb.RET)
    e.keys(sb.CTRL_S)
    e.keys(sb.DOWN, sb.RET)
    L = e.keys(CTRL_U, "Z2", sb.RET)
    by = {x[1]: x[3] for x in elements(L)}
    row("a second change after Ctrl-S is shown (z is now Z2) and the record is marked changed again", by.get("2") == "Z2" and L[0].rstrip().endswith("*"), "%r %r" % (by, L[0].strip()))
    e.keys(sb.CTRL_Q, "N")
    e.quiet()
    st = e.status()
    e.keys(sb.CTRL_S)                                  # the IDE's Ctrl-S (the one CED's Ctrl-S above is not)
    d = disk()
    row("leaving with No keeps what Ctrl-S kept: the IDE saves x^Y1|z, not x^Y1|Z2",
        "is changed, save it to keep it" in st and d[3] == "x^Y1|z", "%r %r" % (st, d[3]))
    e.end()

    # ---- E: a record that holds marks is shown in the token form, and typing a token writes a mark --------------------------------------------------------------------
    say("\n--- the token form in the IDE: marks shown as :@vm: :@sm: :@tm:, read back when the record is saved ---------------------------------------------------")
    # 28 Oct 26 (the editor merge, stage B): the token form follows the KIND of the record.  The same record in bp is a program, and a program is never shown so
    #   (E0, the control the owner's rule asks for); in a data file it is (E1 onward).  These rows used the bp record until stage B.
    e = sb.Ide(box, "IDE bp %s" % re_)
    e.quiet()
    t = "\n".join(e.lines())
    st = e.status()
    row("E0 a PROGRAM (bp) that holds marks is never shown in the token form: the editor does not show Don:@vm:Henry, the status line does not say so, and the tab is "
        "not marked changed", "Don:@vm:Henry" not in t and "Marks are shown as @vm" not in st and re.search(r"bp %s \*" % re_, st) is None, st + "\n" + t[:600])
    e.end()
    row("... and the program on disk is untouched", disk()[4] == d0[4], repr(disk()[4]))
    e = sb.Ide(box, "IDE %s tokrec" % dfile)
    e.quiet()
    t = "\n".join(e.lines())
    st = e.status()
    row("a DATA record that holds marks opens in the token form: the editor shows Don:@vm:Henry:@vm:June and x:@sm:y:@tm:z",
        "Don:@vm:Henry:@vm:June" in t and "x:@sm:y:@tm:z" in t, t[:900])
    row("... and no mark character (251, 252 or 253) is drawn (a weak companion: the token text above is the evidence)", not any(ch in t for ch in "\xfb\xfc\xfd"),
        repr([ch for ch in t if ch in "\xfb\xfc\xfd"]))
    row("... the status line says that marks are shown as @vm, @sm and @tm", "Marks are shown as @vm, @sm and @tm" in st, st)
    row("... and the tab is not marked changed: what was read converts back to the record exactly", re.search(r"%s tokrec \*" % dfile, st) is None, st)
    e.keys(sb.END, ":@vm:Jules")
    e.quiet()
    st = e.status()
    dd = ddisk()
    row("typing :@vm:Jules at the end of line 1 marks the tab changed, and the disk is as it was", re.search(r"%s tokrec \*" % dfile, st) is not None and dd[0] == dd0[0],
        "%r %r" % (st, dd[0]))
    e.keys(sb.CTRL_S)
    st = e.status()
    dd = ddisk()
    row("Ctrl-S in the IDE saves it as marks: Don|Henry|June|Jules^x~y#z - the value mark written from the typed token, the rest of the record exactly as it was",
        ("Saved %s tokrec" % dfile) in st and dd[0] == "Don|Henry|June|Jules^x~y#z", "%r %r" % (st, dd[0]))
    e.end()

    # ---- F: a field that holds the TEXT of a token is not converted ---------------------------------------------------------------------------------------------------
    e = sb.Ide(box, "IDE %s tokfix" % dfile)
    e.quiet()
    st = e.status()
    row("a data record whose field 1 is the text @vm is shown as it is: the status line says field 1 holds the text of a mark token, and the tab is not marked changed",
        "Marks are shown as characters: field 1 holds the text of a mark token" in st and re.search(r"%s tokfix \*" % dfile, st) is None, st)
    row("... and the record on disk is untouched", ddisk()[1] == dd0[1], repr(ddisk()[1]))
    e.end()

    # ---- G: the language of a record is $sl_syntax's, as SED's: the first line decides when the name does not -------------------------------------------------------------
    say("\n--- the language of a record: the first line of a script with no suffix, in a file that is not bp -------------------------------------------------------------")

    def comment_and_text(ident):
        ide = sb.Ide(box, "IDE %s %s" % (dfile, ident))
        ide.quiet()
        L = ide.lines()
        rc = next((i for i, l in enumerate(L) if "# a comment" in l), None)
        rh = next((i for i, l in enumerate(L) if "hello world" in l), None)
        if rc is None or rh is None:
            ide.end()
            return None, "the lines are not on the screen:\n" + "\n".join(l[:60] for l in L[:12])
        sc = ide.s.screen.style(rc, L[rc].index("# a comment") + 4)
        sh = ide.s.screen.style(rh, L[rh].index("hello world") + 2)
        ide.end()
        return (sc, sh), ""

    got, why = comment_and_text("script")
    row("a script with the first line #!/bin/sh and no suffix, in a file that is not bp, is coloured as shell: its comment is drawn in another style than its plain text",
        got is not None and got[0] != got[1], why or repr(got))
    got, why = comment_and_text("plain")
    row("CONTROL: the same lines without the #! line are not coloured: the comment and the plain text have the same style", got is not None and got[0] == got[1], why or repr(got))
    sb.sess(box, "DELETE.FILE %s" % dfile)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-recarr.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-recarr: sandbox %s" % box)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-recarr: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    made = []
    try:
        with open(os.path.join(sysd, "bp", "zzrecarr"), "w") as fh:
            fh.write(PROG)
        made.append("zzrecarr")
        out = session(box, "BASIC bp zzrecarr")
        row("setup: the test program compiles with no errors", "Compiled 1 program(s) with no errors" in out, out[-700:])
        if "Compiled 1 program(s) with no errors" not in out:
            bail("the test program did not compile:\n" + out[-900:])
        out = session(box, "RUN bp zzrecarr")
        row("setup: control - the program ran to its end (it printed END)", re.search(r"(?m)^END\s*$", out) is not None, out[-400:])

        rt, sh, ed, st, ct = (counts(tag(out, n)) for n in ("RT", "SHAPE", "EDIT", "STRUCT", "CTRL"))
        row("RT: 3,000 random records go to an array and back as the same record, every one (no refusal on the way)",
            rt.get("N") == "3000" and rt.get("BAD") == "0" and rt.get("CALLS") == "0", repr(tag(out, "RT")))
        row("SHAPE: every field, value and subvalue is a string or an array exactly where the canonical rule says", sh.get("N") == "3000" and sh.get("BAD") == "0",
            repr(tag(out, "SHAPE")))
        row("EDIT: one leaf set to a new text through the array is the same record as `r<f,v,s> = text`, and at least 2,000 such edits ran",
            ed.get("BAD") == "0" and int(ed.get("N", "0")) >= 2000, repr(tag(out, "EDIT")))
        row("STRUCT: a value or a subvalue added at the end, or taken out, is the same record as the dynamic array forms, and at least 800 ran",
            st.get("BAD") == "0" and int(st.get("N", "0")) >= 800, repr(tag(out, "STRUCT")))
        row("CTRL (the instrument can fail): a conversion that dropped trailing marks would have been called different on %s of 3,000 records" % ct.get("CAUGHT", "?"),
            int(ct.get("CAUGHT", "0")) > 50, repr(tag(out, "CTRL")))

        want = {"CASE1": "EMPTY 0 1", "CASE2": "ONE 1 string x", "CASE3": "TWO 2 string string", "CASE4": "VALUES 1 array 2 a b",
                "CASE5": "SUBONLY array 1 array 2 a b", "CASE6": "MIXED 2 string array 3 b d", "CASE7": "LONEVM 2 [] []", "CASE8": "TRAILFM 2 []",
                "CASE9": "FROMEMPTY [] 1", "CASE10": "NUMTEXT string string string", "CASE11": "NUMBACK 12^1.50^-3 1",
                "CASE12": "Don:@vm:Henry:@vm:June 1", "CASE13": "@vm 1", "CASE14": "@vm:Henry Don:@vm", "CASE15": "a:@vm:@vm:b 1", "CASE16": "a:@sm:b:@tm:c 1",
                "CASE17": "10:30:@vm:x 1", "CASE18": "a^b:@vm:c 1", "CASE19": "Don|Henry~x", "CASE20": "x@vm:@vm:y 1 1", "CASE21": "0 1 0 2 0 1",
                "CASE22": "a::@vm:b 1 1", "CASE23": "a:@vmx:b |"}
        for k, w in want.items():
            got = tag(out, k)
            row("%s: %s" % (k, w), got == w, "got %r" % (got,))
        rf = counts(tag(out, "REFUSE"))
        row("REFUSE: a number, a boolean, a null, a collection, a mixed list, a fourth level and a top-level collection are each refused and make no text",
            rf.get("N") == "7" and rf.get("OK") == "7", repr(tag(out, "REFUSE")))
        tr, ts, te = (counts(tag(out, n)) for n in ("TOKRT", "TOKSOUND", "TOKEDIT"))
        row("TOKRT: 3,000 random records made of the fragments that can be mistaken for a token: every one 'totext' accepts is read back as the same record (%s accepted, %s refused)"
            % (tr.get("OK"), tr.get("REF")), tr.get("N") == "3000" and tr.get("BAD") == "0", repr(tag(out, "TOKRT")))
        row("TOKRT (the instrument sees both kinds): at least 200 records were accepted and at least 200 refused, so neither the round trip nor the refusal ran against nothing",
            int(tr.get("OK", "0")) >= 200 and int(tr.get("REF", "0")) >= 200, repr(tag(out, "TOKRT")))
        row("TOKSOUND: every refusal names a field that exists and that holds an '@' (UNSOUND=%s), and no record without an '@' is ever refused (FALSEREF=%s)"
            % (ts.get("UNSOUND"), ts.get("FALSEREF")), ts.get("UNSOUND") == "0" and ts.get("FALSEREF") == "0", repr(tag(out, "TOKSOUND")))
        row("TOKEDIT: typing a token - a value mark and a text added to the end of the first line - is the same record as adding that value to the first field, over at least 200 records",
            te.get("BAD") == "0" and int(te.get("N", "0")) >= 200, repr(tag(out, "TOKEDIT")))
        fields_part(box, sysd, made)
    finally:
        for nm in made:
            for d in ("bp", "bp.out"):
                p = os.path.join(sysd, d, nm)
                if os.path.exists(p):
                    os.remove(p)

    say("\nsandbox-recarr: %d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        bail("no row ran - a broken test, not a pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
