#!/usr/bin/env python3
#
# sandbox-dictitem.py - S.90 stage 1 (31 Oct 2026): the dictionary item engine !dict_item, RUN.  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-dictitem.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or absent).  Exit 0 every row passed, 1 a row failed,
# 2 it could not run.
#
# START-HISTORY:
# 31 Oct 26 dm  New.  The engine has no screen, so one $internal probe (zzdi, in the sandbox's gpl.bp) calls it for every case and prints DI[label][result]; this file holds what
#               each result must be, written from the rules (docs User/33, tool_dict's test.answer), not from a run.  The probe is compiled and run as the administrator
#               through sandbox-stmt-q3.py's helpers, as sandbox-ipc.py's are.
# END-HISTORY
#
# WHAT IT HOLDS.  The types and the rows of each type's layout (and that the association row depends on S/M = M); parse of stock-looking records (comment after the type,
# decimals, field 0, a compiled I-type with its stamp and object code, an E path, an L with and without a file expression, a phrase, a text of two lines); the round trip
# parse -> build gives the SAME record for every one of them; edits (a number in its normal form, the type changed, the association dropped when the item turns single valued,
# the stamp and object code kept when the expression changes, new items of every type); every refusal with the key it names, each against a base that is accepted; the
# single-value check.  The null case: the probe must have printed every label it was given and its end line, or no row passes.
import importlib.util
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
_spec = importlib.util.spec_from_file_location("q3", os.path.join(HERE, "sandbox-stmt-q3.py"))
q3 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(q3)
say, has, tag, put = q3.say, q3.has, q3.tag, q3.put

passed = failed = 0

PROBE = r"""$internal
program zzdi
$include dictdict.h

   gosub t.types
   gosub t.layouts
   gosub t.parse
   gosub t.roundtrip
   gosub t.edits
   gosub t.refusals
   gosub t.check
   crt 'DIDONE'
   stop

* A base set of values that is accepted: a data item.  Every key of every type is set (a missing key is not what is under test)
base:
   v = collection()
   v{'type'} = 'D'
   v{'loc'} = '5'
   v{'path'} = 'a/b'
   v{'expr'} = 'AMT * 2'
   v{'idexpr'} = 'FIELD(@ID, "-", 1)'
   v{'file'} = 'TITLES'
   v{'fexpr'} = ''
   v{'text'} = 'abc'
   v{'conv'} = ''
   v{'head'} = 'Name'
   v{'width'} = '30'
   v{'just'} = 'L'
   v{'dec'} = ''
   v{'sm'} = 'S'
   v{'assoc'} = ''
   v{'user'} = ''
   return

* The probe's output: DI[label][text], the marks made visible
say:
   crt 'DI[' : lab : '][' : convert(@fm : @vm : @sm : char(10), '|^~/', txt) : ']'
   return

* The key of the row a build named, or 'ok' (no error), or the whole message when it is unexpected
build.run:
   call !dict_item('build', v, old, newrec, err)
   return

t.types:
   call !dict_item('types', '', ty.b, '', ty.d)
   lab = 'types' ; txt = ty.b ; gosub say
   return

t.layouts:
   for ltn = 1 to 7
      lty = field('D,E,I,L,PH,X,Q', ',', ltn)
      call !dict_item('layout', lty, rws, '', ly.d)
      keys = ''
      for rp = 1 to dcount(rws, @fm)
         keys := (if rp > 1 then ',' else '') : rws<rp, 1>
      next rp
      lab = 'layout ' : lty ; txt = keys : ' d=' : ly.d ; gosub say
      if lty = 'D' then
         lab = 'layout D assoc depends' ; txt = rws<9, 7> : '=' : rws<9, 8> ; gosub say
         lab = 'layout D loc kind' ; txt = rws<2, 3> : ' ' : rws<2, 4> : '..' : rws<2, 5> : ' optional=' : rws<2, 6> ; gosub say
      end
   next ltn
   return

t.parse:
   gosub recs
   for pr = 1 to dcount(plist, @vm)
      nm = plist<1, pr>
      rec = recset{nm}
      call !dict_item('parse', rec, pv, '', pd)
      lab = 'parse ' : nm
      txt = pv{'type'} : '/' : pv{'loc'} : '/' : pv{'path'} : '/' : pv{'expr'} : '/' : pv{'head'} : '/' : pv{'width'} : '/' : pv{'just'} : '/' : pv{'dec'} : '/' : pv{'sm'} : '/' : pv{'assoc'} : '/' : pv{'user'} : ' d=' : pd
      gosub say
   next pr
   return

* The records the cases use: D1 stock, D2 decimals / association / user, D3 field 0, D4 a comment after the type, I1 with a stamp and object code, E1, L1, L2, PH1, X1
recs:
   recset = collection()
   recset{'D1'} = 'D' : @fm : '2' : @fm : '' : @fm : 'F2' : @fm : '5L' : @fm : 'S'
   recset{'D2'} = 'D' : @fm : '3' : @fm : 'MD2' : @fm : 'Amt' : @fm : '10R2' : @fm : 'M' : @fm : 'LINE' : @fm : 'keep me'
   recset{'D3'} = 'D' : @fm : '0' : @fm : '' : @fm : '@ID' : @fm : '10L' : @fm : 'S'
   recset{'D4'} = 'D Data for stock qty' : @fm : '4' : @fm : '' : @fm : 'Qty' : @fm : '6R' : @fm : 'S'
   recset{'I1'} = 'I' : @fm : 'AMT * 2' : @fm : '' : @fm : 'Double' : @fm : '8R2' : @fm : 'S' : @fm : '' : @fm : '' : @fm : '' : @fm : '' : @fm : '' : @fm : '' : @fm : '' : @fm : '' : @fm : '99887' : @fm : 'OBJ1'
   recset{'E1'} = 'E' : @fm : 'order/lines/*' : @fm : '' : @fm : 'Line' : @fm : '12L' : @fm : 'M' : @fm : 'LN'
   recset{'L1'} = 'L' : @fm : 'FIELD(@ID, "-", 1)' : @fm : 'TITLES'
   recset{'L2'} = 'L' : @fm : 'FIELD(@ID, "-", 1)' : @fm : 'TITLES' : @fm : 'REGION : "SALES"'
   recset{'PH1'} = 'PH' : @fm : "GRAND.TOTAL 'L'"
   recset{'X1'} = 'X' : @fm : 'line one' : @fm : 'line two'
   plist = 'D1' : @vm : 'D2' : @vm : 'D3' : @vm : 'D4' : @vm : 'I1' : @vm : 'E1' : @vm : 'L1' : @vm : 'L2' : @vm : 'PH1' : @vm : 'X1'
   * records that the form cannot show
   badset = collection()
   badset{'A'} = 'A' : @fm : 'x'
   badset{'S'} = 'S' : @fm : '1'
   badset{'empty'} = ''
   badset{'fmtabc'} = 'D' : @fm : '2' : @fm : '' : @fm : 'F' : @fm : 'abc'
   badset{'fmtnojust'} = 'D' : @fm : '2' : @fm : '' : @fm : 'F' : @fm : '10'
   badset{'fmtdec12'} = 'D' : @fm : '2' : @fm : '' : @fm : 'F' : @fm : '10L12'
   badset{'phtab'} = 'PH' : @fm : 'a' : char(9) : 'b'
   blist = 'A' : @vm : 'S' : @vm : 'empty' : @vm : 'fmtabc' : @vm : 'fmtnojust' : @vm : 'fmtdec12' : @vm : 'phtab'
   return

t.roundtrip:
   gosub recs
   for pr = 1 to dcount(plist, @vm)
      nm = plist<1, pr>
      old = recset{nm}
      call !dict_item('parse', old, v, '', pd)
      call !dict_item('build', v, old, newrec, err)
      lab = 'roundtrip ' : nm
      if newrec = old and err = '' and pd = '' then txt = 'same' else txt = 'DIFFERENT ' : newrec : ' err=' : err : ' pd=' : pd
      gosub say
   next pr
   for pr = 1 to dcount(blist, @vm)
      nm = blist<1, pr>
      call !dict_item('parse', badset{nm}, v, '', pd)
      lab = 'cannot show ' : nm ; txt = pd ; gosub say
   next pr
   return

t.edits:
   gosub recs
   * a number in its normal form, a lower case justification, the width changed
   old = recset{'D1'}
   call !dict_item('parse', old, v, '', pd)
   v{'loc'} = '007' ; v{'width'} = '40' ; v{'just'} = 'r'
   gosub build.run
   lab = 'edit D1 number and justification' ; txt = newrec : ' err=' : err ; gosub say
   * the type changed D to I: nothing of the old type's own fields is left
   v{'loc'} = '2' ; v{'width'} = '5' ; v{'just'} = 'L' ; v{'type'} = 'i' ; v{'expr'} = 'F2 * 2'
   gosub build.run
   lab = 'edit D1 to I' ; txt = newrec : ' err=' : err ; gosub say
   * the compile stamp and object code of an I item are kept when the expression changes
   old = recset{'I1'}
   call !dict_item('parse', old, v, '', pd)
   v{'expr'} = 'AMT * 3'
   gosub build.run
   lab = 'edit I1 expression keeps the stamp' ; txt = newrec<2> : '/' : newrec<15> : '/' : newrec<16> : ' err=' : err ; gosub say
   * an I item made into a D item loses the stamp and the object code
   v{'type'} = 'D' ; v{'loc'} = '9'
   gosub build.run
   lab = 'edit I1 to D drops the object code' ; txt = newrec : ' n=' : dcount(newrec, @fm) : ' err=' : err ; gosub say
   * a multivalued item turned single valued loses its association
   old = recset{'D2'}
   call !dict_item('parse', old, v, '', pd)
   v{'sm'} = 'S'
   gosub build.run
   lab = 'edit D2 to single valued' ; txt = newrec : ' err=' : err ; gosub say
   * new items
   old = ''
   gosub base
   gosub build.run
   lab = 'new D' ; txt = newrec : ' err=' : err ; gosub say
   v{'dec'} = '0' ; v{'loc'} = '0'
   gosub build.run
   lab = 'new D, field 0 and decimals 0' ; txt = newrec : ' err=' : err ; gosub say
   gosub base
   v{'sm'} = 'S' ; v{'assoc'} = 'a b'
   gosub build.run
   lab = 'new D, single valued: a bad association is not looked at' ; txt = newrec : ' err=' : err ; gosub say
   gosub base
   v{'type'} = 'L'
   gosub build.run
   lab = 'new L' ; txt = newrec : ' err=' : err ; gosub say
   v{'fexpr'} = 'REGION : "SALES"'
   gosub build.run
   lab = 'new L with a file expression' ; txt = newrec : ' err=' : err ; gosub say
   gosub base
   v{'type'} = 'X' ; v{'text'} = ''
   gosub build.run
   lab = 'new X, empty' ; txt = newrec : ' err=' : err ; gosub say
   v{'text'} = 'a' : char(10) : 'b'
   gosub build.run
   lab = 'new X, two lines' ; txt = newrec : ' err=' : err ; gosub say
   gosub base
   v{'type'} = 'PH' ; v{'text'} = 'abc'
   gosub build.run
   lab = 'new PH' ; txt = newrec : ' err=' : err ; gosub say
   gosub base
   v{'type'} = 'E' ; v{'path'} = 'order/lines/*'
   gosub build.run
   lab = 'new E' ; txt = newrec : ' err=' : err ; gosub say
   return

* Each row: a label, the key that is changed, its new value (and the type when it is not D); the build must refuse and name the key
t.refusals:
   old = ''
   rf = ''
   rf<-1> = 'loc letters' : @vm : 'loc' : @vm : 'abc' : @vm : 'D'
   rf<-1> = 'loc negative' : @vm : 'loc' : @vm : '-1' : @vm : 'D'
   rf<-1> = 'loc too big' : @vm : 'loc' : @vm : '10000' : @vm : 'D'
   rf<-1> = 'loc with a decimal point' : @vm : 'loc' : @vm : '1.5' : @vm : 'D'
   rf<-1> = 'loc empty' : @vm : 'loc' : @vm : '' : @vm : 'D'
   rf<-1> = 'width zero' : @vm : 'width' : @vm : '0' : @vm : 'D'
   rf<-1> = 'width 201' : @vm : 'width' : @vm : '201' : @vm : 'D'
   rf<-1> = 'justification X' : @vm : 'just' : @vm : 'X' : @vm : 'D'
   rf<-1> = 'single/multi Q' : @vm : 'sm' : @vm : 'Q' : @vm : 'D'
   rf<-1> = 'unknown conversion' : @vm : 'conv' : @vm : 'XYZ' : @vm : 'D'
   rf<-1> = 'conversion with a space' : @vm : 'conv' : @vm : 'D2 x' : @vm : 'D'
   rf<-1> = 'heading 41 characters' : @vm : 'head' : @vm : str('x', 41) : @vm : 'D'
   rf<-1> = 'heading with a control character' : @vm : 'head' : @vm : 'a' : char(7) : 'b' : @vm : 'D'
   rf<-1> = 'user 301 characters' : @vm : 'user' : @vm : str('x', 301) : @vm : 'D'
   rf<-1> = 'decimals 10' : @vm : 'dec' : @vm : '10' : @vm : 'D'
   rf<-1> = 'type Z' : @vm : 'type' : @vm : 'Z' : @vm : 'D'
   rf<-1> = 'I expression empty' : @vm : 'expr' : @vm : '' : @vm : 'I'
   rf<-1> = 'L id expression with a semicolon' : @vm : 'idexpr' : @vm : 'A;B' : @vm : 'L'
   rf<-1> = 'L file empty' : @vm : 'file' : @vm : '' : @vm : 'L'
   rf<-1> = 'L file with a space' : @vm : 'file' : @vm : 'a b' : @vm : 'L'
   rf<-1> = 'E path empty' : @vm : 'path' : @vm : '' : @vm : 'E'
   rf<-1> = 'PH phrase empty' : @vm : 'text' : @vm : '' : @vm : 'PH'
   rf<-1> = 'X text with a control character' : @vm : 'text' : @vm : 'a' : char(7) : @vm : 'X'
   for rr = 1 to dcount(rf, @fm)
      gosub base
      v{'type'} = rf<rr, 4>
      v{rf<rr, 2>} = rf<rr, 3>
      gosub build.run
      lab = 'refuse ' : rf<rr, 1> ; txt = 'key=' : err<1> : ' made=' : (if newrec = '' then 'nothing' else newrec) ; gosub say
   next rr
   * width given with no justification, and the reverse
   gosub base
   v{'just'} = ''
   gosub build.run
   lab = 'refuse width without justification' ; txt = 'key=' : err<1> ; gosub say
   gosub base
   v{'width'} = ''
   gosub build.run
   lab = 'refuse justification without width' ; txt = 'key=' : err<1> ; gosub say
   gosub base
   v{'width'} = '' ; v{'just'} = ''
   gosub build.run
   lab = 'no format at all is allowed' ; txt = newrec : ' err=' : err ; gosub say
   return

t.check:
   ck = ''
   ck<-1> = 'D' : @vm : 'loc' : @vm : '007'
   ck<-1> = 'D' : @vm : 'just' : @vm : 'l'
   ck<-1> = 'D' : @vm : 'type' : @vm : 'ph'
   ck<-1> = 'D' : @vm : 'conv' : @vm : ''
   ck<-1> = 'D' : @vm : 'loc' : @vm : ''
   ck<-1> = 'D' : @vm : 'nosuchrow' : @vm : 'x'
   ck<-1> = 'D' : @vm : 'width' : @vm : '300'
   ck<-1> = 'I' : @vm : 'expr' : @vm : '  AMT  *  2  '
   ck<-1> = 'L' : @vm : 'idexpr' : @vm : 'A;B'
   for cr = 1 to dcount(ck, @fm)
      cv = ck<cr, 3>
      call !dict_item('check', ck<cr, 1>, ck<cr, 2>, cv, cd)
      lab = 'check ' : ck<cr, 1> : ' ' : ck<cr, 2> : ' [' : ck<cr, 3> : ']'
      txt = '[' : cv : '] ' : (if cd = '' then 'ok' else (if cd[1, 12] = 'there is no ' then 'no such row' else 'refused'))
      gosub say
   next cr
   return
end
"""

# label -> what the probe must print (the marks are shown as | ^ ~ and a line feed as /)
EXPECT = [
    ("types", "D|E|I|L|PH|X"),
    ("layout D", "type,loc,conv,head,width,just,dec,sm,assoc,user d="),
    ("layout D assoc depends", "sm=M"),
    ("layout D loc kind", "num 0..9999 optional=0"),
    ("layout E", "type,path,conv,head,width,just,dec,sm,assoc,user d="),
    ("layout I", "type,expr,conv,head,width,just,dec,sm,assoc,user d="),
    ("layout L", "type,idexpr,file,fexpr d="),
    ("layout PH", "type,text d="),
    ("layout X", "type,text d="),
    ("layout Q", " d=type"),
    ("parse D1", "D/2///F2/5/L//S// d="),
    ("parse D2", "D/3///Amt/10/R/2/M/LINE/keep me d="),
    ("parse D3", "D/0///@ID/10/L//S// d="),
    ("parse D4", "D/4///Qty/6/R//S// d="),
    ("parse I1", "I///AMT * 2/Double/8/R/2/S// d="),
    ("parse E1", "E//order/lines/*//Line/12/L//M/LN/ d="),
    ("parse L1", "L///////////" + " d="),
    ("parse L2", "L///////////" + " d="),
    ("parse PH1", "PH///////////" + " d="),
    ("parse X1", "X///////////" + " d="),
    ("roundtrip D1", "same"), ("roundtrip D2", "same"), ("roundtrip D3", "same"), ("roundtrip D4", "same"), ("roundtrip I1", "same"),
    ("roundtrip E1", "same"), ("roundtrip L1", "same"), ("roundtrip L2", "same"), ("roundtrip PH1", "same"), ("roundtrip X1", "same"),
    ("cannot show A", "type"), ("cannot show S", "type"), ("cannot show empty", "type"), ("cannot show fmtabc", "format"),
    ("cannot show fmtnojust", "format"), ("cannot show fmtdec12", "format"), ("cannot show phtab", "text"),
    ("edit D1 number and justification", "D|7||F2|40R|S err="),
    ("edit D1 to I", "I|F2 * 2||F2|5L|S err="),
    ("edit I1 expression keeps the stamp", "AMT * 3/99887/OBJ1 err="),
    ("edit I1 to D drops the object code", "D|9||Double|8R2|S n=6 err="),
    ("edit D2 to single valued", "D|3|MD2|Amt|10R2|S||keep me err="),
    ("new D", "D|5||Name|30L|S err="),
    ("new D, field 0 and decimals 0", "D|0||Name|30L0|S err="),
    ("new D, single valued: a bad association is not looked at", "D|5||Name|30L|S err="),
    ("new L", "L|FIELD(@ID, \"-\", 1)|TITLES err="),
    ("new L with a file expression", "L|FIELD(@ID, \"-\", 1)|TITLES|REGION : \"SALES\" err="),
    ("new X, empty", "X err="),
    ("new X, two lines", "X|a|b err="),
    ("new PH", "PH|abc err="),
    ("new E", "E|order/lines/*||Name|30L|S err="),
    ("refuse loc letters", "key=loc made=nothing"), ("refuse loc negative", "key=loc made=nothing"), ("refuse loc too big", "key=loc made=nothing"),
    ("refuse loc with a decimal point", "key=loc made=nothing"), ("refuse loc empty", "key=loc made=nothing"),
    ("refuse width zero", "key=width made=nothing"), ("refuse width 201", "key=width made=nothing"),
    ("refuse justification X", "key=just made=nothing"), ("refuse single/multi Q", "key=sm made=nothing"),
    ("refuse unknown conversion", "key=conv made=nothing"), ("refuse conversion with a space", "key=conv made=nothing"),
    ("refuse heading 41 characters", "key=head made=nothing"), ("refuse heading with a control character", "key=head made=nothing"),
    ("refuse user 301 characters", "key=user made=nothing"), ("refuse decimals 10", "key=dec made=nothing"), ("refuse type Z", "key=type made=nothing"),
    ("refuse I expression empty", "key=expr made=nothing"), ("refuse L id expression with a semicolon", "key=idexpr made=nothing"),
    ("refuse L file empty", "key=file made=nothing"), ("refuse L file with a space", "key=file made=nothing"),
    ("refuse E path empty", "key=path made=nothing"), ("refuse PH phrase empty", "key=text made=nothing"),
    ("refuse X text with a control character", "key=text made=nothing"),
    ("refuse width without justification", "key=just"), ("refuse justification without width", "key=width"),
    ("no format at all is allowed", "D|5||Name||S err="),
    ("check D loc [007]", "[7] ok"), ("check D just [l]", "[L] ok"), ("check D type [ph]", "[PH] ok"), ("check D conv []", "[] ok"),
    ("check D loc []", "[] refused"), ("check D nosuchrow [x]", "[x] no such row"), ("check D width [300]", "[300] refused"),
    ("check I expr [  AMT  *  2  ]", "[AMT  *  2] ok"), ("check L idexpr [A;B]", "[A;B] refused"),
]


def row(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        say("  [PASS] " + name)
    else:
        failed += 1
        say("  [FAIL] %s%s" % (name, ("   <- " + detail) if detail else ""))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        q3.bail("usage: sandbox-dictitem.py <dir> [--build]")
    q3.BOX = os.path.abspath(args[0])
    q3.SYS = os.path.join(q3.BOX, "sys")
    q3.SD = os.path.join(q3.SYS, "bin", "sd")
    SYS = q3.SYS
    say("sandbox-dictitem: sandbox  %s" % q3.BOX)
    if "--build" in sys.argv:
        if os.path.exists(q3.BOX) and os.listdir(q3.BOX):
            q3.bail("%s is not empty" % q3.BOX)
        r = subprocess.run([sys.executable, TOOL, q3.BOX, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            q3.bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-dictitem: built, bootstrap passed")
    elif not os.path.isfile(q3.SD):
        q3.bail("%s holds no built sandbox (use --build, or point it at one)" % q3.BOX)
    subprocess.run([sys.executable, TOOL, q3.BOX, "start"], capture_output=True, text=True, errors="replace", timeout=120)
    q3.prepare()
    probe = os.path.join(SYS, "gpl.bp", "zzdi")
    try:
        put(probe, PROBE)
        out = q3.adm(["BASIC gpl.bp zzdi"], internal=True)
        if not has(out, r"^Compiled 1 program\(s\) with no errors"):
            q3.bail("the probe did not compile:\n" + "\n".join(out[-12:]))
        out = q3.adm(["RUN gpl.bp zzdi"], internal=True)
    finally:
        for d in ("gpl.bp", "gpl.bp.out"):
            p = os.path.join(SYS, d, "zzdi")
            if os.path.exists(p):
                os.remove(p)
    got = {}
    for t in tag(out, "DI"):
        m = re.match(r"^(.*?)\]\[(.*)$", t)
        if m:
            got[m.group(1)] = m.group(2)
    say("\n--- the probe printed %d of %d lines, and its end line %s ---" % (len(got), len(EXPECT), "yes" if has(out, r"^DIDONE$") else "NO"))
    if not has(out, r"^DIDONE$") or not got:
        say("  [FAIL] NULL CASE: the probe did not run to its end   <- " + " | ".join(out[-8:]))
        say("\nsandbox-dictitem: %d passed, %d failed" % (passed, 1))
        return 1
    # the parse rows for records with no D/E/I fields: the engine gives the text in the 'text' key, which the probe does not print; only the type matters there
    loose = {"parse L1": r"^L/", "parse L2": r"^L/", "parse PH1": r"^PH/", "parse X1": r"^X/"}
    for label, want in EXPECT:
        g = got.get(label)
        if g is None:
            row(label, False, "the probe printed no such line")
        elif label in loose:
            row(label, re.match(loose[label], g) is not None and g.endswith(" d="), "got %r" % g)
        else:
            row(label, g == want, "got %r, wanted %r" % (g, want))
    extra = sorted(set(got) - set(l for l, _ in EXPECT))
    row("no line the suite does not know", not extra, repr(extra))
    say("\nsandbox-dictitem: %d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        q3.bail("no row ran - a broken test, not a pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
