#!/usr/bin/env python3
#
# sandbox-tk-widgets.py - S.88: the toolkit's three facades over the library widgets, measured through INTERNAL probe programs: $tk_out (the output pane's state and history), $tk_pickrec
# (the record picker) and $tk_form (the labelled form).  No install, no sudo.  WRITTEN BLIND (the owner's rule of 28 Oct 2026: no sandbox run until the one complete run); the first run is
# the main session's, and a row that fails on it is as likely to be a wrong assumption of the row as a fault of the widget - read the probe's lines before believing either.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-tk-widgets.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (SHORT path under /tmp).  With --build it is built first from THIS tree (it must be empty or absent).  Exit 0 every row passed,
# 1 a row failed, 2 it could not run.  Remove the directory afterwards.
#
# START-HISTORY:
# 29 Oct 26 dm  New (S.88; the suite regress.sh and regress-map.txt have listed since the library widgets were written).
# END-HISTORY
#
# WHAT IT MEASURES.
#   O  $tk_out on a pipe (no terminal): the state is 0 before anything, 'add' keeps the history without opening the pane, 'toggle' opens and closes it and answers the state, 'close' keeps the
#      history, and a ctx with another TK.C.EPOCH starts closed (the history belongs to one open of the app)
#   K  $tk_pickrec on a pipe: no terminal is 'cancel' in all three modes (the whole pick, a file, a record of a file), and a record of a file that does not exist is 'cancel'
#   F  $tk_form on a pipe: 'open' answers 'no' (nothing drawn) and 'run' answers 'cancel'
#   T  $tk_form on a pseudo-terminal of 140 by 60 (xterm): the form opens (c null), the entries start with their texts and the cursor stands AFTER them (so a typed letter is appended),
#      Tab moves to the next entry, Return in an entry presses the default button ('ok' and both texts as typed, the focus entry named), Esc is 'cancel', 'say' puts the refusal's words on the
#      screen and the form stays so that a second 'run' still answers.  These are the assumptions the edited sandbox rows of the question-chain pages (remote R5, ai T10, audit set_filters,
#      bulk add_op, menus mymenu add) make about the form: a failure here explains a failure there.
# THE INSTRUMENT.  Every probe line starts with a tag no echo carries (OUT, PRK, FRM, FRT); a row that finds no such line FAILS.

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ptydrive import PtySession  # noqa: E402

TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
RUN = "%05d" % (os.getpid() % 100000)
POUT = "zzwo" + RUN
PPIK = "zzwp" + RUN
PFRM = "zzwf" + RUN
PFRT = "zzwt" + RUN
passed = failed = 0

SRC_OUT = """$internal
$include gpl.bp tk.h
   ctx = ''
   ctx<TK.C.EPOCH> = 7
   call $tk_out('state', ctx, '', '', c)
   crt 'OUT state before=' : c
   call $tk_out('add', ctx, 'ok', 'first line', '')
   call $tk_out('add', ctx, 'refuse', 'second line', '')
   call $tk_out('state', ctx, '', '', c)
   crt 'OUT state after add=' : c
   call $tk_out('toggle', ctx, '', '', c)
   crt 'OUT toggle 1=' : c
   call $tk_out('state', ctx, '', '', c)
   crt 'OUT state open=' : c
   call $tk_out('toggle', ctx, '', '', c)
   crt 'OUT toggle 2=' : c
   call $tk_out('open', ctx, '', '', c)
   call $tk_out('close', ctx, '', '', c)
   call $tk_out('state', ctx, '', '', c)
   crt 'OUT state closed=' : c
   call $tk_out('open', ctx, '', '', c)
   ctx<TK.C.EPOCH> = 8
   call $tk_out('state', ctx, '', '', c)
   crt 'OUT state other epoch=' : c
end
"""

SRC_PIK = """$internal
$include gpl.bp tk.h
   ctx = ''
   ctx<TK.C.EPOCH> = 7
   for m = 1 to 3
      mode = field(',file,record', ',', m)
      f = ''
      if mode = 'record' then f = 'voc'
      id = 'unset'
      res = 'unset'
      nt = ''
      call $tk_pickrec(ctx, mode, f, id, res, nt)
      crt 'PRK mode=<' : mode : '> res=' : res : ' id=<' : id : '>'
   next m
   f = 'zznosuchfile'
   id = ''
   call $tk_pickrec(ctx, 'record', f, id, res, nt)
   crt 'PRK nosuchfile res=' : res
end
"""

SRC_FRM = """$internal
$include gpl.bp tk.h
   ctx = ''
   ctx<TK.C.EPOCH> = 7
   spec = 'Probe form' : @fm : '&Go' : @fm : ''
   spec<-1> = 'a' : @vm : 'Alpha' : @vm : 20 : @vm : 20
   spec<-1> = 'b' : @vm : 'Beta' : @vm : 20 : @vm : 20
   fv = 'x' : @fm : 'y'
   call $tk_form('open', ctx, spec, fv, fo)
   crt 'FRM open=<' : fo : '>'
   call $tk_form('run', ctx, ans, vals, fid)
   crt 'FRM run=' : ans
   call $tk_form('close', ctx, '', '', '')
end
"""

SRC_FRT = """$internal
$include gpl.bp tk.h
   ctx = ''
   ctx<TK.C.EPOCH> = 7
   spec = 'Probe form' : @fm : '&Go' : @fm : ''
   spec<-1> = 'a' : @vm : 'Alpha' : @vm : 20 : @vm : 20
   spec<-1> = 'b' : @vm : 'Beta' : @vm : 20 : @vm : 20
   fv = 'x' : @fm : 'y'
   call $tk_form('open', ctx, spec, fv, fo)
   o1 = 'FRT open=<' : fo : '>'
   call $tk_form('run', ctx, ans, vals, fid)
   r1 = 'FRT first=' : ans : ' a=<' : vals<1> : '> b=<' : vals<2> : '> focus=' : fid
   call $tk_form('say', ctx, 'the refusal words', 'b', '')
   call $tk_form('run', ctx, ans, vals, fid)
   r2 = 'FRT second=' : ans : ' a=<' : vals<1> : '> b=<' : vals<2> : '> focus=' : fid
   call $tk_form('close', ctx, '', '', '')
   * the lines are printed AFTER the close: a line written while the form is open lies on its window, and the close puts back what was under it (29 Oct 26, seen on the screen)
   crt o1
   crt r1
   crt r2
   crt 'FRT done'
end
"""


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
    say("sandbox-tk-widgets: CANNOT RUN - " + msg)
    sys.exit(2)


def sdenv(box, term=None):
    e = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"), SDTEST_ADMIN="1", LC_ALL="C")
    e.pop("LINES", None)
    e.pop("COLUMNS", None)
    if term:
        e["TERM"] = term
    return e


def isess(box, *cmds):
    """INTERNAL mode on a pipe: no terminal"""
    body = "\nTERM 200,9999\n" + "".join(c + "\n" for c in cmds) + "OFF\n"
    p = subprocess.run([os.path.join(box, "sys", "bin", "sd"), "-internal"], input=body, cwd=os.path.join(box, "sys"), env=sdenv(box),
                       capture_output=True, text=True, errors="replace", timeout=300)
    return ANSI.sub("", p.stdout + p.stderr)


def psess(box, *cmds):
    """A NORMAL session as the administrator on a pipe whose input ENDS right after the last command (the screen library takes that as Esc).  Not `sd -internal`: that mode
    spins at 100% CPU when its input has ended (measured by hand 29 Oct 26, the pick probe: 20 s of CPU in 21 s), a normal session ends in 0.03 s.  The probes were compiled INTERNAL
    (isess, above) and an administrator may run them.  `no terminal` in the toolkit is a PHANTOM (SYSTEM(25)); a pipe is not one, so these rows are about an input that has ended."""
    body = "TERM xterm\nTERM 140,43\n" + "".join(c + "\n" for c in cmds)
    p = subprocess.run([os.path.join(box, "sys", "bin", "sd")], input=body, cwd=os.path.join(box, "sys"), env=sdenv(box),
                       capture_output=True, text=True, errors="replace", timeout=60)
    text = ANSI.sub("", p.stdout + p.stderr)
    return re.sub(r"\b(OUT|PRK|FRM) (?=[a-z])", r"\n\1 ", text)        # a probe's line follows the picture a page drew on the same line (no line feed): start it on a line of its own


def pty_run(box, prog, keys):
    """INTERNAL mode on a pseudo-terminal of 140 by 60: RUN the probe, then send each of keys (text, idle seconds); returns the screen's lines"""
    s = PtySession([os.path.join(box, "sys", "bin", "sd"), "-internal"], os.path.join(box, "sys"), sdenv(box, "xterm"), 140, 60)
    s.settle(1.0)
    s.type("TERM xterm\r")
    s.type("RUN bp " + prog + "\r", idle=1.5)
    for text, idle in keys:
        s.type(text, idle=idle)
    lines = s.screen.lines()
    s.type("\rOFF\r", idle=0.5)
    s.finish()
    return lines


def tagged(text, tag):
    """the probe lines that carry the tag: a probe's crt line is written wherever the cursor stood, so it may come after blanks or after what a page drew on the same screen row (29 Oct 26: on the
    pseudo-terminal 'FRT first=' was printed after the form closed and was not at the start of its row); the tag must stand at the start of the row or after a blank"""
    out = []
    for ln in (text if isinstance(text, list) else text.split("\n")):
        i = ln.find(tag + " ")
        while i > 0 and ln[i - 1] != " ":
            i = ln.find(tag + " ", i + 1)
        if i >= 0:
            out.append(ln[i:].rstrip())
    return out


def val(lines, tag, key):
    for ln in tagged(lines, tag):
        m = re.match(r"%s %s=(.*)$" % (tag, re.escape(key)), ln)
        if m:
            return m.group(1)
    return None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-tk-widgets.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-tk-widgets: sandbox %s" % box)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-tk-widgets: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    progs = ((POUT, SRC_OUT), (PPIK, SRC_PIK), (PFRM, SRC_FRM), (PFRT, SRC_FRT))
    for nm, body in progs:
        with open(os.path.join(sysd, "bp", nm), "w") as fh:
            fh.write(body)
    try:
        say("\n--- setup ---------------------------------------------------------------------------------------")
        iout = isess(box, *["BASIC bp " + nm for nm, _ in progs])
        n = len(re.findall(r"(?m)^Compiled 1 program\(s\) with no errors", iout))
        row("setup: the four probes (internal: a user program cannot call a $ subroutine) compiled with no errors", n == 4, iout[-600:])
        if n != 4:
            bail("the probes did not compile:\n" + iout[-800:])

        say("\n--- O: $tk_out on a pipe whose input has ended ------------------------------------------------------")
        out = psess(box, "RUN bp " + POUT)
        g = {k: val(out, "OUT", k) for k in ("state before", "state after add", "toggle 1", "state open", "toggle 2", "state closed", "state other epoch")}
        row("the probe answered for every step (the null case: the instrument measured)", all(v is not None for v in g.values()), repr(g))
        row("the pane starts closed (state 0), and 'add' keeps the history without opening it", g["state before"] == "0" and g["state after add"] == "0", repr(g))
        row("'toggle' opens it (answers 1, state 1) and the next 'toggle' closes it (answers 0); 'close' after 'open' leaves it closed",
            g["toggle 1"] == "1" and g["state open"] == "1" and g["toggle 2"] == "0" and g["state closed"] == "0", repr(g))
        row("another open of the app (TK.C.EPOCH 8) starts closed although epoch 7 had opened it", g["state other epoch"] == "0", repr(g))

        say("\n--- K: $tk_pickrec on a pipe whose input has ended --------------------------------------------------")
        out = psess(box, "RUN bp " + PPIK)
        pk = tagged(out, "PRK")
        row("the probe answered four times (the null case)", len(pk) == 4, repr(pk))
        row("a session whose input has ended gets 'cancel' in the whole pick, in 'file' mode and in 'record' mode, and the id stays empty",
            len(pk) >= 3 and all("res=cancel" in x for x in pk[:3]) and all("id=<>" in x for x in pk[:3]), repr(pk[:3]))
        row("a record of a file that does not exist is 'cancel'", any(x == "PRK nosuchfile res=cancel" for x in pk), repr(pk))

        say("\n--- F: $tk_form on a pipe whose input has ended -----------------------------------------------------")
        out = psess(box, "RUN bp " + PFRM)
        fo, fr = val(out, "FRM", "open"), val(out, "FRM", "run")
        row("the probe answered (the null case)", fo is not None and fr is not None, repr((fo, fr)))
        row("'open' answers null (the form was drawn: only a phantom gets 'no') and 'run' answers 'cancel' because the input has ended", fo == "<>" and fr == "cancel", repr((fo, fr)))

        say("\n--- T: $tk_form on a terminal -----------------------------------------------------------------------")
        # the probe prints its lines after the form is CLOSED (a line written while it is open is wiped by the close), and it runs the form twice: each row ends the second run with an Esc
        lines = pty_run(box, PFRT, [("Q\tZ\r", 1.5), ("\x1b", 1.5)])
        t = tagged(lines, "FRT")
        row("the form opened (c null) and the first 'run' answered", any(x == "FRT open=<>" for x in t) and any(x.startswith("FRT first=") for x in t), repr(t))
        first = [x for x in t if x.startswith("FRT first=")]
        row("Q, Tab, Z, Return: both entries started with their texts and the cursor stood after them (xQ, yZ), Return in the second entry pressed the default button ('ok'), and the focus entry is b",
            bool(first) and first[0] == "FRT first=ok a=<xQ> b=<yZ> focus=b", repr(first))
        lines = pty_run(box, PFRT, [("\x1b", 1.5), ("\x1b", 1.5)])
        first = [x for x in tagged(lines, "FRT") if x.startswith("FRT first=")]
        row("Esc is 'cancel' (and the texts come back as they were: x and y)", bool(first) and first[0].startswith("FRT first=cancel a=<x> b=<y>"), repr(first))
        lines = pty_run(box, PFRT, [("\x1b", 1.5), ("\x1b", 1.5)])
        t = tagged(lines, "FRT")
        row("after 'say' the form stays: a second 'run' answers (here Esc again: cancel) and the probe goes on to close it (the refusal's words themselves are not read: they are gone with the form)",
            any(x.startswith("FRT second=cancel") for x in t) and any(x == "FRT done" for x in t), repr(t))
    finally:
        subprocess.run([sys.executable, TOOL, box, "stop"], capture_output=True, text=True, errors="replace", timeout=120)

    say("")
    say("sandbox-tk-widgets: %d passed, %d failed" % (passed, failed))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
