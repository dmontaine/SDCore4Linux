#!/usr/bin/env python3
#
# sandbox-tk-public.py - the PUBLIC full-screen toolkit (S.130): the `!tk` routines called by an ORDINARY user program in an ordinary account, driven on a pseudo-terminal.
# No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-tk-public.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 every row passed, 1 a row
# failed, 2 it could not run.  The account is sandbox-home.py's zzhd (an ORDINARY session: the first row of its setup proves it); the program is `bp/zzpub`, a plain BASIC program with
# `$include tkpub.h` and no `$internal`, so it has no more right than any user program.
#
# WHAT IS HELD.
#   P1  the program compiles in an ordinary account with the public header (the header is found, every !tk name resolves at run time)
#   P2  it runs: the menu bar on row 0 with the program's name and "don@zzhd" at its right end (the USER audience), the pane in brackets and a message on the status line, the function-key row
#       made from the table
#   P3  F2 is the finder: every entry of the bar's menus in one list ("File > Quit"); Esc closes it
#   P4  the confirm box shows the sentence and the explanation; Enter alone is Cancel; r is Run; and THE LIBRARY RUNS NOTHING either way (the sentence is `touch <a file>`: no file appears)
#   P5  the form shows its title and labels; Enter is ok with the texts the entries held; Esc is cancel
#   P6  the pick list answers the entry chosen
#   P7  THE AI LINE IS NOT THE PROGRAM'S: with the AI line's two context slots set by hand, the body is still 39 rows (the row the line would take is not taken) and aiacts answers nothing
#   P8  THE PICKER OPENS WHAT THE ACCOUNT MAY, AND WRITES NOTHING: a VOC pointer at a directory outside the account, which this account's own OPEN is refused (the control row, from a plain
#       program), is refused by the picker too and no record of it is listed; the record picked in the account's own file is left byte for byte as it was
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sh = _load("sandbox_home_for_tkpublic", "sandbox-home.py")
g = sh.g
say, row, bail, has, dump, adm, H = sh.say, sh.row, sh.bail, sh.has, sh.dump, sh.adm, sh.H
ACCT = "zzhd"
CTRL = {"ctrl-k": "\x0b", "ctrl-n": "\x0e", "ctrl-p": "\x10", "ctrl-r": "\x12", "ctrl-b": "\x02", "ctrl-q": "\x11"}

PROGRAM = """$include tkpub.h
$include err.h
   prompt ''
   call !tkopen('pubdemo', ctx, err, '', '')
   if err # '' then
      crt err
      stop
   end
   keys = ''
   call !tkkeys('add', keys, 'f1', 'help', 'help', '', 1)
   call !tkkeys('add', keys, 'ctrl-q', 'quit', 'quit', '', 1)
   call !tkkeys('add', keys, 'ctrl-k', 'sure', 'sure', '', 1)
   call !tkkeys('add', keys, 'ctrl-n', 'form', 'form', '', 1)
   call !tkkeys('add', keys, 'ctrl-p', 'pick', 'pick', '', 1)
   call !tkkeys('add', keys, 'ctrl-r', 'recs', 'recs', '', 1)
   call !tkkeys('add', keys, 'ctrl-b', 'body', 'body', '', 1)
   call !tkkeys('add', keys, 'esc', 'menu', 'menu', '', 1)
   call !tkkeys('menu', keys, 'quit', '&File', '&Quit', '', '')
   call !tkkeys('menu', keys, 'sure', '&File', '&Confirm', '', '')
   call !tkkeys('menu', keys, 'pick', '&View', '&Pick', '', '')
   d = ''
   d<1> = 'main' : @vm : 1 : @vm : 1 : @vm : 39 : @vm : 138 : @vm : '' : @vm : 'stretch' : @vm : 1 : @vm : 'stretch' : @vm : 1
   perr = ''
   call !tklayout('declare', ctx, d, perr)
   call !tklayout('pane', ctx, 'main', rc)
   msg = 'ready'
   gosub draw.all
   loop
      call !tkmenubar('draw', ctx, keys, 'Main', '', '', mr)
      call !tkframe(ctx, keys, 'Main', msg)
      nm = ''
      screen key returning nm
      mr = ''
      if nm # '' then call !tkmenubar('key', ctx, keys, 'Main', nm, 0, mr)
      if mr<1> # '' then nm = mr<4>
      begin case
         case nm = ''
            if status() = ER$EOF then exit
         case nm = 'guardquit' or nm = 'ctrl-q'
            exit
         case nm = 'ctrl-k'
            sent = 'touch ' : '@PUBFILE@'
            res = '' ; m = ''
            call !tkconfirm(sent, 'This explanation line comes from the program.', '', res, m, '', '')
            msg = 'confirm:' : res
         case nm = 'ctrl-n'
            spec = 'Make one' : @fm : '&Create' : @fm : ''
            spec<4> = 'name' : @vm : 'Name' : @vm : 20
            spec<5> = 'code' : @vm : 'Code' : @vm : 20
            vals = 'abc' : @fm : 'xyz'
            fa = '' ; fb = '' ; fc = ''
            call !tkform('open', ctx, spec, vals, fc)
            call !tkform('run', ctx, fa, fb, fc)
            call !tkform('close', ctx, '', '', '')
            msg = 'form:' : fa : ':' : change(fb, @fm, '|')
         case nm = 'ctrl-p'
            items = 'alpha' : @vm : 'first one' : @fm : 'beta' : @vm : 'second one' : @fm : 'gamma' : @vm : 'third one'
            pid = 'Pick one' ; pres = '' ; pstart = 1
            call !tkpickrec(ctx, 'list', items, pid, pres, pstart)
            msg = 'pick:' : pres : ':' : pid
         case nm = 'ctrl-r'
            pfile = '@PICKFILE@' ; pid = '' ; pres = '' ; pnew = ''
            call !tkpickrec(ctx, 'record', pfile, pid, pres, pnew)
            msg = 'rec:' : pres : ':' : pid
         case nm = 'ctrl-b'
            ctx<11> = 1
            ctx<28> = 1
            call !tklayout('refresh', ctx, '', chg)
            ab = '' ; ac = ''
            call !tkkeys('aiacts', keys, 'Main', ab, ac, '', '')
            msg = 'bodyh=' : ctx<TK.C.BODYH> : ' aiacts=[' : ab : ']'
      end case
   repeat
   call !tkclose(ctx)
   stop

draw.all:
   screen clear at 0,ctx<TK.C.YBODY> size ctx<TK.C.W>,ctx<TK.C.BODYH>
   screen box at rc<1,1>,rc<1,2> size rc<1,3>,rc<1,4> title 'Public toolkit'
   return
end
"""

# the control: what the account's OWN OPEN does with the pointer at a directory outside the account
CONTROL = """   crt 'CTL begin'
   open 'zzout' to f then
      crt 'CTL opened'
      select f to 11
      readnext id from 11 else id = 'NONE'
      crt 'CTL first ':id
   end else
      crt 'CTL refused ':status()
   end
   crt 'CTL end'
end
"""


def box():
    return sh.BOX


def compile_prog(name, src):
    g.put(os.path.join(box(), "user_accounts", ACCT, "bp", name), src)
    return g.plain(ACCT, ["BASIC bp " + name])


def key(h, name, idle=0.8):
    h.s.type(CTRL[name] if name in CTRL else sh.KEYS[name], idle=idle)


def main():
    try:
        sh.setup("sandbox-tk-public.py")
        acct = os.path.join(box(), "user_accounts", ACCT)
        pubfile = os.path.join(box(), "pubdemo.ran")
        outside = os.path.join(box(), "zz-outside")
        os.makedirs(outside, exist_ok=True)
        g.put(os.path.join(outside, "secret.rec"), "SECRET-OUTSIDE-12345\n")
        g.put(os.path.join(acct, "bp", "zzmine"), "own record\n")
        g.put(os.path.join(g.SYS, "bp", "zzptr"), "\n".join([
            "$internal",
            "   openpath '%s/voc' to v else crt 'PTR no voc' ; stop" % acct,
            "   write 'F':@fm:'%s' to v, 'zzout'" % outside,
            "   crt 'PTR done'", "end", ""]))
        o = adm("BASIC bp zzptr", "RUN bp zzptr")
        if not has(o, r"^PTR done$"):
            bail("the outside pointer was not written:\n" + "\n".join(o[-5:]))

        say("\n--- P1. the program compiles in an ordinary account")
        src = PROGRAM.replace("@PUBFILE@", pubfile).replace("@PICKFILE@", "bp")
        out = compile_prog("zzpub", src)
        row("P1 zzpub ($include tkpub.h, the !tk routines, no $internal) compiles in %s" % ACCT, has(out, r"^Compiled 1 program\(s\) with no errors"), repr(out[-6:]))
        if not has(out, r"^Compiled 1 program\(s\) with no errors"):
            bail("zzpub did not compile, so no row below can run:\n" + "\n".join(out[-8:]))
        before_bp = open(os.path.join(acct, "bp", "zzmine"), "rb").read()

        say("\n--- P2-P7. the page on a terminal")
        h = H(ACCT)
        h.typed("RUN bp zzpub\r", idle=3.5)
        T = h.text()
        if "Public toolkit" not in T:
            dump(h)
        row("P2a the page is drawn: the box and the menu bar's title on row 0", "Public toolkit" in T and "File" in h.line(0) and "View" in h.line(0), repr(h.line(0)[:60]))
        row("P2b the right end of row 0 names the program and the USER audience (don@%s), never the administrator" % ACCT,
            "pubdemo" in h.line(0) and "@%s" % ACCT in h.line(0) and "administrator" not in h.line(0), repr(h.line(0)[-40:]))
        row("P2c the status line (row 40) has the pane in brackets and the message; the function-key row (42) is made from the table", "[Main]" in h.line(40) and "ready" in h.line(40)
            and "F1 help" in h.line(42) and "^Q quit" in h.line(42), repr((h.line(40)[:30], h.line(42)[:50])))

        key(h, "f2")
        T = h.text()
        row("P3a F2 is the finder: every entry of the bar's menus, 'File > Quit' and 'View > Pick'", "File > Quit" in T and "View > Pick" in T, "")
        key(h, "esc")
        row("P3b Esc closes the finder", "File > Quit" not in h.text(), "")

        key(h, "ctrl-k")
        T = h.text()
        row("P4a the confirm box shows the sentence unaltered and the explanation, with Run and Cancel", "pubdemo.ran" in T
            and "This explanation line comes from the program." in T and "Run" in T and "Cancel" in T, "")
        key(h, "enter")
        row("P4b Enter alone is Cancel: the status line says confirm:cancel", "confirm:cancel" in h.line(40), repr(h.line(40)[:40]))
        key(h, "ctrl-k")
        h.s.type("r", idle=1.0)
        row("P4c r is Run: confirm:run", "confirm:run" in h.line(40), repr(h.line(40)[:40]))
        row("P4d THE LIBRARY RAN NOTHING: the sentence was 'touch <file>' and no file appeared", not os.path.exists(pubfile), pubfile)

        key(h, "ctrl-n")
        T = h.text()
        row("P5a the form shows its title and the labels of its entries", "Make one" in T and "Name" in T and "Code" in T, "")
        key(h, "enter")
        row("P5b Enter presses the default button: ok, with the texts the entries held", "form:ok:abc|xyz" in h.line(40), repr(h.line(40)[:50]))
        key(h, "ctrl-n")
        key(h, "esc")
        row("P5c Esc is cancel", "form:cancel" in h.line(40), repr(h.line(40)[:50]))

        key(h, "ctrl-p")
        T = h.text()
        row("P6a the pick list shows the program's entries", "alpha" in T and "beta" in T and "gamma" in T, "")
        key(h, "down")
        key(h, "enter")
        row("P6b the entry chosen is answered (the second)", "pick:ok:2" in h.line(40), repr(h.line(40)[:40]))

        key(h, "ctrl-b")
        row("P7 the AI line is not the program's: with its two slots set by hand the body is still 39 rows and aiacts answers nothing", "bodyh=39 aiacts=[]" in h.line(40), repr(h.line(40)[:50]))

        key(h, "ctrl-r")
        T = h.text()
        row("P8a the picker lists the account's own file (bp): zzmine and zzpub", "zzmine" in T and "zzpub" in T, "")
        key(h, "enter")
        row("P8b a record is answered", "rec:ok:" in h.line(40), repr(h.line(40)[:40]))
        row("P8c THE PICKER WROTE NOTHING: the record is byte for byte as it was", open(os.path.join(acct, "bp", "zzmine"), "rb").read() == before_bp, "")
        key(h, "ctrl-q")
        h.end()

        say("\n--- P8d-f. the picker opens what the account may and no more")
        ctl = compile_prog("zzctl", CONTROL)
        ran = g.plain(ACCT, ["RUN bp zzctl"]) if has(ctl, r"^Compiled 1 program\(s\) with no errors") else []
        state = "opened" if has(ran, r"^CTL opened$") else ("refused" if has(ran, r"^CTL refused") else "unknown")
        seen = has(ran, r"^CTL first secret\.rec$")
        row("P8d (control) the account's OWN program %s a VOC pointer at a directory outside the account%s" % (state, " and sees its record" if seen else ""), state != "unknown", repr(ran[-4:]))
        src2 = PROGRAM.replace("@PUBFILE@", pubfile).replace("@PICKFILE@", "zzout")
        out = compile_prog("zzpub2", src2)
        h = H(ACCT)
        h.typed("RUN bp zzpub2\r", idle=3.5)
        up = "Public toolkit" in h.text()
        key(h, "ctrl-r")
        T = h.text()
        shown = "secret.rec" in T
        answered_cancel = "rec:cancel:" in h.line(40)
        if not shown and not answered_cancel:
            key(h, "esc")
            answered_cancel = "rec:cancel:" in h.line(40)
        # the page must be up, and the picker must have either listed the record or answered cancel at once: an empty window or a dead page proves nothing
        row("P8e the picker shows the outside record exactly when the account's own OPEN does, and when it does not the picker answers cancel (own OPEN: %s, picker: %s)"
            % ("sees it" if seen else "does not", "shows it" if shown else ("answered cancel" if answered_cancel else "NOTHING")),
            up and ((seen and shown) or (not seen and not shown and answered_cancel)), repr((up, T[-200:])))
        key(h, "esc")
        key(h, "ctrl-q")
        h.end()
        row("P8f the outside file is as it was", open(os.path.join(outside, "secret.rec"), "rb").read() == b"SECRET-OUTSIDE-12345\n", "")
    finally:
        sh.teardown()
    sh.summary("sandbox-tk-public")


if __name__ == "__main__":
    main()
