#!/usr/bin/env python3
#
# sandbox-tk-layout.py - the toolkit's layout service (S.88 L1, `gpl.bp/tk_layout`), the resize a dialogue read (R-a), the cursor lock decided by the window (R-b) and the
# frame cache's epoch (F1), driven on a PSEUDO-TERMINAL through four fixture programs of the sandbox's own.  No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-tk-layout.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT, under /tmp).  Exit 0 no row
# failed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 28 Oct 26 dm  New (S.88 L1).  WRITTEN, NOT RUN (the owner's rule: one complete run when the full-screen phases are done).  Its expected rectangles come from the model in
#               test-tklayout-units.py, which was checked against the real $tk_layout once by hand (353 rectangles, 0 differences, 28 Oct 26).
# END-HISTORY
#
# WHY FIXTURES AND NOT THE PAGES.  In L1 no page uses the service yet (L2 moves them, one at a time, and sandbox-tk-resize.py's rows are L2's acceptance), so the service is driven by
# INTERNAL programs compiled in the sandbox's gpl.bp (a user program cannot call a $-routine: the compiler reads "call $tk_layout(" as a bracket) and given to the administrator's VOC as
# verbs (V CA $zztlN), as sandbox-tk-faults.py does with $zzcf:
#
#   zztl1 [floorw floorh]   a page in the shape of tool.files (its boxes, 138x22 and 138x17), DECLARED to the service and drawn from its rectangles; on the key resize it calls
#                           $tk_layout 'refresh' and draws again; r refreshes without a resize; Ctrl-Q leaves.  It appends a line to bp zztl.log at the start and after every key:
#                           the event, the changed flag, every frame and body slot, the mode, the floor, the epoch and both rectangles.  THE LOG IS THE EVIDENCE of the numbers; the
#                           screen (a fresh emulator fed only the bytes written after a resize, plan 7.4) is the evidence that they were drawn.
#   zztl2 [wait]            SCREEN KEY (or SCREEN WAIT on a one-button form) in a loop with a 3-second timeout; m opens SCREEN MSGBOX (z opens SCREEN ASK from the form), which reads
#                           a resize the program never sees today; it logs every key, event, timeout and box.
#   zztl3                   $tk_open, $tk_frame, a key, $tk_close, then all of it again with the SAME status text: F1.
#   zztl4                   a SCREEN OPEN program that asks for the cursor lock with the old THREE arguments, its cursor at 0,0: the cursor mode, kept.
#
# THE ROWS.  A the service at one size (140x43 against the page's literal boxes; 180x55 against the model; r with no resize says nothing changed); B a resize (grow, shrink above the
# floor: the log, the footer written on the new last rows, the keys still the page's); C the lock (120x43 and 140x41 lock with the floor named, keys dropped; back at 140x43 it lifts
# without a key and the page is told resize; a three-argument program at 120x43 is NOT locked; a declared floor of 150x45 is asked by $tk_open and named by the lock; a floor under
# 100x30 is raised to it and the layout is compact as the model says); D a resize while a dialogue is open reaches SCREEN KEY / SCREEN WAIT at once when the dialogue closes, and only
# once; a resize with no dialogue is delivered once; E F1: the second open of an app draws its status line, border and keys, and an unchanged frame writes nothing.
import importlib.util
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ptydrive import PtySession  # noqa: E402
from termscreen import Screen  # noqa: E402
from tuirows import Rows  # noqa: E402


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sh = _load("sandbox_home_for_tklayout", "sandbox-home.py")          # setup / teardown / adm: the sandbox, its fixture accounts and the administrator's internal session
tl = _load("test_tklayout_model", "test-tklayout-units.py")         # the model of $tk_layout's equations: the expected rectangles
R = Rows("tk-layout")
M = tl.Model()
BOX = SYS = None
E = "\x1b"
CTRL_Q, RET, DOWN = "\x11", "\r", E + "OB"
LOGREC = "zztl.log"
DECL = [tl.P("list", 1, 22, v=True), tl.P("detail", 2, 17)]          # zztl1's declaration (tool.files': DECLS["tool_files"])


def say(s=""):
    print(s, flush=True)


def bail(msg):
    say("sandbox-tk-layout: CANNOT RUN - " + msg)
    sys.exit(2)


# ------------------------------------------------------------------------------------------------------------------------ the fixture programs
LOGNOTE = """note:
   open 'bp' to lf then
      read lg from lf, 'zztl.log' else lg = ''
      lg<-1> = ln
      write lg on lf, 'zztl.log'
      close lf
   end
   return
"""

ZZTL1 = """$internal
program $zztl1
$catalog $zztl1
$include tk.h

   s = trim(@sentence)
   fw = field(s, ' ', 2)
   fh = field(s, ' ', 3)
   call $tk_open('zztl1', '', ctx, err, fw, fh)
   if err # '' then
      crt 'ZZTL1 REFUSED ' : err
      stop
   end
   d = ''
   d<1> = 'list' : @vm : 1 : @vm : '' : @vm : 22 : @vm : 138 : @vm : '' : @vm : 'stretch' : @vm : '' : @vm : 'stretch'
   d<2> = 'detail' : @vm : 2 : @vm : '' : @vm : 17 : @vm : 138 : @vm : '' : @vm : '' : @vm : '' : @vm : 'stretch'
   call $tk_layout('declare', ctx, d, perr)
   keys = ''
   call $tk_keys('add', keys, 'ctrl-q', 'quit', 'quit', '', 1)
   ev = 'open'
   if perr # '' then ev = 'perr ' : perr
   chg = ctx<TK.C.CHANGED>
   gosub note.ctx
   gen = 0
   nm = ''
   loop
      gosub draw
      call $sl_curat(0, ctx<TK.C.YSTAT>)
      screen key timeout 60 returning nm else nm = ''
      if nm = '' or nm = 'guardquit' or nm = 'ctrl-q' then exit
      chg = ''
      begin case
         case nm = 'resize'
            call $tk_layout('refresh', ctx, '', chg)
            gen += 1
            ctx<TK.C.GEN> = gen
            ev = 'resize'
         case nm = 'r'
            call $tk_layout('refresh', ctx, '', chg)
            ev = 'r'
         case 1
            ev = 'key ' : nm
      end case
      gosub note.ctx
   repeat
   ev = 'end ' : nm
   chg = ''
   gosub note.ctx
   call $tk_close(ctx)
   crt 'ZZTL1 DONE'
   stop

note.ctx:
   ln = ev : '|' : chg : '|' : ctx<TK.C.W> : '|' : ctx<TK.C.H> : '|' : ctx<TK.C.YSTAT> : '|' : ctx<TK.C.YBORD> : '|' : ctx<TK.C.YKEYS>
   ln := '|' : ctx<TK.C.XBODY> : '|' : ctx<TK.C.YBODY> : '|' : ctx<TK.C.BODYW> : '|' : ctx<TK.C.BODYH> : '|' : ctx<TK.C.MODE>
   ln := '|' : ctx<TK.C.FLOORW> : '|' : ctx<TK.C.FLOORH> : '|' : ctx<TK.C.EPOCH>
   call $tk_layout('pane', ctx, 'list', r)
   ln := '|' : convert(@vm, ' ', r)
   call $tk_layout('pane', ctx, 'detail', r)
   ln := '|' : convert(@vm, ' ', r)
   gosub note
   return

draw:
   cw = ctx<TK.C.W>
   cb = ctx<TK.C.BODYH>
   screen clear at 0,1 size cw,cb
   call $tk_layout('pane', ctx, 'list', r)
   bx = r<1,1>
   by = r<1,2>
   bw = r<1,3>
   bh = r<1,4>
   if r<1,5> then
      screen box at bx,by size bw,bh title 'List'
   end
   call $tk_layout('pane', ctx, 'detail', r)
   bx = r<1,1>
   by = r<1,2>
   bw = r<1,3>
   bh = r<1,4>
   if r<1,5> then
      screen box at bx,by size bw,bh title 'Detail'
   end
   msg = 'zztl1 ' : ctx<TK.C.W> : 'x' : ctx<TK.C.H>
   call $tk_frame(ctx, keys, 'List', msg)
   return

""" + LOGNOTE + "end\n"

ZZTL2 = """$internal
program $zztl2
$catalog $zztl2

   mode = field(trim(@sentence), ' ', 2)
   screen open clear else
      crt 'ZZTL2 no screen'
      stop
   end
   screen text 'zztl2 ' : mode at 2,2
   if mode = 'wait' then
      screen form title 'Wait' at 5,4 size 30,8 returning f
      screen button f, 'ok', '&OK' at 2,4 default
      for i = 1 to 40
         screen wait f timeout 3 returning ev then
            ln = 'EV ' : ev<1> : ' ' : convert(@vm, 'x', ev<3>)
         end else
            ln = 'ELSE ' : ev<1>
         end
         gosub note
         if ev<1> = 'button' or ev<1> = 'end' then exit
         if ev<1> = 'key' and ev<3> = 'z' then
            screen ask 'Name?' returning a else a = ''
            ln = 'ASK'
            gosub note
         end
      next i
      screen hide f
   end else
      for i = 1 to 40
         screen key timeout 3 returning k else k = ''
         if k = '' then ln = 'TIMEOUT' else ln = 'KEY ' : k
         gosub note
         if k = 'q' then exit
         if k = 'm' then
            screen msgbox 'A box over the program' title 'Box' buttons '&OK' returning b else b = 0
            ln = 'BOX ' : b
            gosub note
         end
      next i
   end
   screen close
   crt 'ZZTL2 DONE'
   stop

""" + LOGNOTE + "end\n"

ZZTL3 = """$internal
program $zztl3
$catalog $zztl3
$include tk.h

   keys = ''
   call $tk_keys('add', keys, 'ctrl-q', 'quit', 'quit', '', 1)
   for pass = 1 to 2
      call $tk_open('zztl3', '', ctx, err)
      if err # '' then
         crt 'ZZTL3 REFUSED ' : err
         stop
      end
      call $tk_frame(ctx, keys, 'P', 'the same status text')
      call $sl_curat(0, ctx<TK.C.YSTAT>)
      screen key timeout 30 returning k else k = ''
      if k = 'n' then
         call $tk_frame(ctx, keys, 'P', 'the same status text')
         call $sl_curat(0, ctx<TK.C.YSTAT>)
         screen key timeout 30 returning k else k = ''
      end
      call $tk_close(ctx)
   next pass
   crt 'ZZTL3 DONE'
end
"""

ZZTL4 = """$internal
program $zztl4
$catalog $zztl4

   screen open clear else
      crt 'ZZTL4 no screen'
      stop
   end
   call $sl_guardmode('zztl4', 140, 43)
   screen text 'zztl4 cursor mode' at 0,0
   for i = 1 to 40
      call $sl_curat(0, 0)
      screen key timeout 3 returning k else k = ''
      ln = 'KEY ' : k
      gosub note
      if k = 'q' then exit
   next i
   screen close
   crt 'ZZTL4 DONE'
   stop

""" + LOGNOTE + "end\n"

ZZVOC = """   open 'VOC' to v else
      crt 'ZZVOC no voc'
      stop
   end
   for i = 1 to 4
      write 'V' : @fm : 'CA' : @fm : '$zztl' : i on v, 'zztl' : i
   next i
   crt 'ZZVOC done'
end
"""


def fixture():
    for name, src in (("zztl1", ZZTL1), ("zztl2", ZZTL2), ("zztl3", ZZTL3), ("zztl4", ZZTL4)):
        with open(os.path.join(SYS, "gpl.bp", name), "w") as f:
            f.write(src)
    out = sh.adm("BASIC gpl.bp zztl1 zztl2 zztl3 zztl4")
    say("\n".join(out[-6:]))
    if not sh.has(out, r"^Compiled 4 program\(s\) with no errors"):
        bail("the fixture programs did not compile:\n" + "\n".join(out[-20:]))
    with open(os.path.join(SYS, "bp", "zzvoc"), "w") as f:
        f.write(ZZVOC)
    out = sh.adm("BASIC bp zzvoc", "RUN bp zzvoc")
    if not sh.has(out, r"^ZZVOC done$"):
        bail("the VOC entries were not made:\n" + "\n".join(out[-8:]))


# ------------------------------------------------------------------------------------------------------------------------ a session on a pty
class Win:
    def __init__(self, label, s, cols, rows):
        self.label, self.s, self.cols, self.rows = label, s, cols, rows

    def pump(self, secs):
        end = time.time() + secs
        while time.time() < end and not self.s.exited:
            self.s._pump(min(0.2, max(0.01, end - time.time())))
        self.s.settle(0.4)

    def send(self, data, idle=0.6):
        say("   [%s] keys %r" % (self.label, data))
        self.s.type(data, idle=idle)

    def mark(self):
        return len(self.s.raw)

    def resize(self, cols, rows, secs=1.5):
        off = self.mark()
        say("   [%s] resize pty %dx%d -> %dx%d (wait %.1f s)" % (self.label, self.cols, self.rows, cols, rows, secs))
        self.s.resize(cols, rows, idle=0.05)
        self.cols, self.rows = cols, rows
        self.pump(secs)
        return off

    def post(self, off):
        return self.s.raw[off:].decode("latin-1")

    def fresh(self, off):
        f = Screen(self.cols, self.rows)
        f.feed(self.post(off))
        return f

    def lines(self):
        return [l.rstrip() for l in self.s.screen.lines()]

    def text(self):
        return "\n".join(self.lines())

    def end(self):
        if not self.s.exited:
            self.s.type(CTRL_Q, idle=0.8)
        self.s.finish(limit=2.0)
        say("   [%s] finished: exited=%s" % (self.label, self.s.exited))


def launch(label, cmd, cols=140, rows=43):
    """the administrator's session in the sandbox's SDSYS (SDTEST_ADMIN=1, cwd sys), TERM xterm, LC_ALL=C (ASCII borders); the command typed after TERM w,h"""
    clear_log()
    env = dict(os.environ, SD_CONFIG=os.path.join(BOX, "sd.conf"), TERM="xterm", LC_ALL="C", LANG="C", SDTEST_ADMIN="1")
    for k in ("SSH_CONNECTION", "SSH_TTY", "LINES", "COLUMNS"):
        env.pop(k, None)
    argv = [os.path.join(SYS, "bin", "sd")]
    say("== %s: argv=%r cwd=%s TERM=xterm LC_ALL=C SD_CONFIG=%s SDBOX_KEYSET=%s pty=%dx%d command=%r" % (label, argv, SYS, env["SD_CONFIG"], env.get("SDBOX_KEYSET"), cols, rows, cmd))
    w = Win(label, PtySession(argv, SYS, env, cols, rows), cols, rows)
    w.s.settle(1.0)
    w.send("TERM xterm\r", 0.4)
    w.send("TERM %d,%d\r" % (cols, rows), 0.4)
    w.send(cmd + "\r", 1.5)
    w.pump(2.0)
    return w


# ------------------------------------------------------------------------------------------------------------------------ the log
def log_path():
    return os.path.join(SYS, "bp", LOGREC)


def clear_log():
    if SYS and os.path.exists(log_path()):
        os.remove(log_path())


def log():
    try:
        with open(log_path(), encoding="latin-1") as f:
            return [l for l in f.read().replace("\xfe", "\n").split("\n") if l.strip()]
    except OSError:
        return []


NAMES = ["ev", "chg", "W", "H", "YSTAT", "YBORD", "YKEYS", "XBODY", "YBODY", "BODYW", "BODYH", "MODE", "FLOORW", "FLOORH", "EPOCH", "list", "detail"]


def entries():
    """zztl1's log as dicts; a rectangle as a tuple of five numbers"""
    out = []
    for l in log():
        p = l.split("|")
        if len(p) != len(NAMES):
            continue
        d = dict(zip(NAMES, p))
        for k in ("list", "detail"):
            try:
                d[k] = tuple(int(x) for x in d[k].split())
            except ValueError:
                d[k] = None
        out.append(d)
    return out


def expect(ww, hh, floor=(None, None)):
    """the model's frame, body, mode and rectangles for zztl1 at a window of ww by hh"""
    fr = M.frame(ww, hh, *floor)
    rects, mode = M.layout(DECL, fr)
    fw = floor[0] or M.minw
    fh = floor[1] or M.minh
    return {"W": str(fr["W"]), "H": str(fr["H"]), "YSTAT": str(fr["YSTAT"]), "YBORD": str(fr["YBORD"]), "YKEYS": str(fr["YKEYS"]), "XBODY": str(fr["XBODY"]),
            "YBODY": str(fr["YBODY"]), "BODYW": str(fr["BODYW"]), "BODYH": str(fr["BODYH"]), "MODE": mode, "FLOORW": str(max(fw, 100)), "FLOORH": str(max(fh, 30)),
            "list": rects[0], "detail": rects[1]}


def matches(e, want):
    if e is None:
        return False
    return all(e.get(k) == v for k, v in want.items())


def diff(e, want):
    if e is None:
        return "no log line"
    return ", ".join("%s %r want %r" % (k, e.get(k), v) for k, v in want.items() if e.get(k) != v) or "same"


def foot(lines, cols, rows):
    L = [l.rstrip() for l in lines] + [""] * rows
    st, bd, ky = L[rows - 3], L[rows - 2], L[rows - 1]
    bd_w = len(bd) if bd and not re.search(r"[A-Za-z0-9]", bd) else 0
    d = dict(st_ok=st.startswith("[List]") or st.startswith("[P]"), key_ok="^Q" in ky, bd_w=bd_w, st=st[:40], ky=ky[:30])
    d["ok"] = d["st_ok"] and d["key_ok"] and bd_w > 0
    return d


LOCK = re.compile(r"is laid out for (\d+) by (\d+) or larger")


def lock_named(lines):
    m = LOCK.search(" ".join(l.strip() for l in lines))
    return (int(m.group(1)), int(m.group(2))) if m else None


# ------------------------------------------------------------------------------------------------------------------------ A, B: the service and a resize
def sec_service():
    say("\n--- A: the service at one size")
    w = launch("A-140", "zztl1", 140, 43)
    E0 = entries()
    first = E0[0] if E0 else None
    f0 = foot(w.lines(), 140, 43)
    ctrl = R.row("A0 zztl1 at 140x43 is up: it logged its open line and its footer is on rows 41-43 (status [List], border, ^Q)", first is not None and first["ev"] == "open" and f0["ok"],
                 "%r %r" % (first, f0))
    want = expect(140, 43)
    R.row("A1 at 140x43 the context is what $tk_open has always made and the body is 138 by 39 at 1,1: W 140 H 43 YSTAT 40 YBORD 41 YKEYS 42, mode full, floor 140 by 43",
          ctrl and matches(first, {k: want[k] for k in ("W", "H", "YSTAT", "YBORD", "YKEYS", "XBODY", "YBODY", "BODYW", "BODYH", "MODE", "FLOORW", "FLOORH")}), diff(first, want))
    R.row("A2 at 140x43 the declared panes are EXACTLY tool.files' literal boxes: list 1,1 138x22, detail 1,23 138x17 (both shown)",
          ctrl and first["list"] == (1, 1, 138, 22, 1) and first["detail"] == (1, 23, 138, 17, 1), "%r %r" % (first and first["list"], first and first["detail"]))
    L = w.lines()
    R.row("A3 ...and drawn there: box corners at row 1 and row 23, column 1 (the list's bottom border on row 22, the detail's on row 39)",
          ctrl and L[1][1:2] == "+" and L[22][1:2] == "+" and L[23][1:2] == "+" and L[39][1:2] == "+" and L[1][138:139] == "+", "\n".join(l[:20] for l in L[0:3] + L[21:25] + L[38:41]))
    w.send("r", 0.8)
    E1 = entries()
    last = E1[-1] if E1 else None
    R.row("A4 r ($tk_layout 'refresh' with no resize) says nothing changed (0) and leaves every slot and rectangle as it was",
          ctrl and last is not None and last["ev"] == "r" and last["chg"] == "0" and matches(last, want), diff(last, dict(want, chg="0")))
    w.end()

    w = launch("A-180", "zztl1", 180, 55)
    E0 = entries()
    first = E0[0] if E0 else None
    want = expect(180, 55)
    R.row("A5 started at 180x55: W 180 H 55, YSTAT 52 YBORD 53 YKEYS 54, body 178 by 51, mode full; the list (stretching) gets the 12 rows: list 1,1 178x34, detail 1,35 178x17 (the model)",
          matches(first, want) and want["list"] == (1, 1, 178, 34, 1) and want["detail"] == (1, 35, 178, 17, 1), diff(first, want))
    f0 = foot(w.lines(), 180, 55)
    R.row("A6 ...the footer is on rows 53-55 and the border 180 wide", f0["ok"] and f0["bd_w"] == 180, repr(f0))
    w.end()


def sec_resize():
    say("\n--- B: a resize")
    w = launch("B", "zztl1", 140, 43)
    c = R.row("B0 zztl1 at 140x43 is up (an open line in the log)", any(e["ev"] == "open" for e in entries()), repr(log()[:2]))
    off = w.resize(180, 55, 2.0)
    last = entries()[-1] if entries() else None
    want = expect(180, 55)
    R.row("B1 140x43 -> 180x55: the page is told resize, $tk_layout 'refresh' says changed (1) and the context is the 180x55 one (the model's)", c and last is not None and last["ev"] == "resize"
          and last["chg"] == "1" and matches(last, want), diff(last, dict(want, ev="resize", chg="1")))
    fr = w.fresh(off)
    f = foot(fr.lines(), 180, 55)
    R.row("B2 ...and the program writes its footer on rows 53-55 with a border 180 wide, and the detail box from row 35 (plan 7.4: the bytes written after the resize only)",
          c and f["ok"] and f["bd_w"] == 180 and fr.lines()[35][1:2] == "+", "%r; bytes %d" % (f, len(w.post(off))))
    off = w.resize(150, 45, 2.0)
    last = entries()[-1] if entries() else None
    want = expect(150, 45)
    locked = lock_named(w.lines())
    R.row("B3 180x55 -> 150x45 (above the floor): no lock, the context is the 150x45 one (list 1,1 148x24, detail 1,25 148x17)",
          c and locked is None and last is not None and last["ev"] == "resize" and matches(last, want), "lock %r; %s" % (locked, diff(last, want)))
    f = foot(w.fresh(off).lines(), 150, 45)
    R.row("B4 ...the footer is written on rows 43-45 with a border 150 wide", c and f["ok"] and f["bd_w"] == 150, repr(f))
    w.send("x", 0.8)
    last = entries()[-1] if entries() else None
    R.row("B5 ...and the keys are the page's: x is logged", c and last is not None and last["ev"] == "key x", repr(last and last["ev"]))
    w.send("r", 0.8)
    last = entries()[-1] if entries() else None
    R.row("B6 r at 150x45 says nothing changed (0)", c and last is not None and last["ev"] == "r" and last["chg"] == "0", repr(last and (last["ev"], last["chg"])))
    w.end()


# ------------------------------------------------------------------------------------------------------------------------ C: the lock
def sec_lock():
    say("\n--- C: the cursor lock, decided by the window against the floor")
    w = launch("C", "zztl1", 140, 43)
    c = R.row("C0 zztl1 at 140x43 is up", any(e["ev"] == "open" for e in entries()), repr(log()[:2]))
    off = w.resize(120, 43, 2.0)
    named = lock_named(w.fresh(off).lines())
    R.row("C1 120x43 (too narrow; the cursor at the start of the status line still shows): the program writes the lock naming 140 by 43", c and named == (140, 43),
          "named %r; rows %r" % (named, [l.strip()[:70] for l in w.fresh(off).lines() if l.strip()][:3]))
    n0 = len(log())
    w.send("x", 0.8)
    R.row("C2 ...and the key x does not reach the page (no new log line)", c and len(log()) == n0, repr(log()[n0:]))
    off = w.resize(140, 43, 2.5)
    last = entries()[-1] if entries() else None
    f = foot(w.fresh(off).lines(), 140, 43)
    R.row("C3 back at 140x43 the lock lifts WITHOUT a key: the page is told resize and draws its footer on rows 41-43", c and last is not None and last["ev"] == "resize" and f["ok"],
          "%r %r" % (last and last["ev"], f))
    w.send("y", 0.8)
    last = entries()[-1] if entries() else None
    R.row("C4 ...and y reaches the page", c and last is not None and last["ev"] == "key y", repr(last and last["ev"]))
    off = w.resize(140, 41, 2.0)
    named = lock_named(w.fresh(off).lines())
    R.row("C5 140x41 (two rows short; the status line on row 41 still shows): locked, naming 140 by 43", c and named == (140, 43), repr(named))
    w.send(CTRL_Q, 0.8)
    w.send("y", 1.5)
    w.pump(1.0)
    last = entries()[-1] if entries() else None
    R.row("C6 in the lock Ctrl-Q, y leaves: the page is given guardquit and ends (ZZTL1 DONE)", c and last is not None and last["ev"] == "end guardquit" and "ZZTL1 DONE" in w.text(),
          "%r; %s" % (last and last["ev"], w.text()[-200:]))
    w.end()

    w = launch("C-cursor", "zztl4", 140, 43)
    c = R.row("C7c zztl4 (three-argument $sl_guardmode, the cursor at 0,0) is up", "zztl4 cursor mode" in w.text(), w.text()[:200])
    w.resize(120, 43, 2.0)
    n0 = len(log())
    w.send("x", 1.0)
    R.row("C7 the old cursor mode is kept for a three-argument call: at 120x43 with the cursor at 0,0 there is no lock and x reaches the program",
          c and lock_named(w.lines()) is None and "KEY x" in log()[n0:], repr(log()[n0:]))
    w.send("q", 1.0)
    w.end()

    w = launch("C-floor", "zztl1 150 45", 140, 43)
    R.row("C8 a declared floor of 150 by 45 is asked by $tk_open: at 140x43 it is refused with 11197 naming 150 columns by 45 lines, and nothing was laid out",
          "zztl1 needs a window of at least 150 columns by 45 lines" in " ".join(w.lines()) and not entries(), w.text()[-300:])
    w.end()
    w = launch("C-floor2", "zztl1 150 45", 160, 50)
    E0 = entries()
    first = E0[0] if E0 else None
    want = expect(160, 50, (150, 45))
    c = R.row("C9 at 160x50 it opens with the floor 150 by 45 in the context, and the layout is the window's (the model's)", matches(first, want), diff(first, want))
    off = w.resize(145, 50, 2.0)
    R.row("C10 ...145x50 is under ITS floor: locked, naming 150 by 45", c and lock_named(w.fresh(off).lines()) == (150, 45), repr(lock_named(w.fresh(off).lines())))
    w.end()
    w = launch("C-least", "zztl1 90 20", 100, 30)
    E0 = entries()
    first = E0[0] if E0 else None
    want = expect(100, 30, (100, 30))
    R.row("C11 a floor under 100 by 30 (90 by 20) is raised to 100 by 30: at 100x30 the page opens, the layout is compact (body 98 by 26) and the panes are the model's "
          "(list 1,1 98x22, detail cut to 1,23 98x4)", matches(first, want) and want["MODE"] == "compact" and want["list"] == (1, 1, 98, 22, 1) and want["detail"] == (1, 23, 98, 4, 1),
          diff(first, want))
    w.end()


# ------------------------------------------------------------------------------------------------------------------------ D: a resize read by a dialogue
def lines_from(n0):
    return [l.split(" t=")[0] for l in log()[n0:]]


def sec_dialog():
    say("\n--- D: a resize while a dialogue is open reaches the program when it closes, once")
    w = launch("D-key", "zztl2", 140, 43)
    c = R.row("D0 zztl2 is up", "zztl2" in w.text(), w.text()[:120])
    w.send("m", 1.0)
    c2 = R.row("D1c m opens the message box (its text is on the screen)", c and "A box over the program" in w.text(), w.text()[-300:])
    w.send(RET, 1.0)
    w.pump(3.5)
    L = lines_from(0)
    R.row("D2c control: with no resize, after the box (BOX 1) the next SCREEN KEY times out (TIMEOUT), it is not given resize", c2 and "BOX 1" in L and L[L.index("BOX 1") + 1:L.index("BOX 1") + 2] == ["TIMEOUT"],
          repr(L))
    n0 = len(log())
    w.send("m", 1.0)
    w.resize(150, 45, 1.0)
    w.send(RET, 0.4)
    w.pump(0.8)
    L = lines_from(n0)
    R.row("D3 a resize while the box was open: right after BOX 1 (within a second, before the 3-second timeout) SCREEN KEY gives resize", c2 and L[:3] == ["KEY m", "BOX 1", "KEY resize"], repr(L))
    w.pump(3.5)
    L = lines_from(n0)
    R.row("D4 ...once: the SCREEN KEY after it times out (not a second resize)", c2 and L[3:4] == ["TIMEOUT"], repr(L))
    n0 = len(log())
    w.resize(140, 43, 1.0)
    w.pump(3.5)
    L = lines_from(n0)
    R.row("D5 a resize while SCREEN KEY itself waits is given once, then a timeout", c and L[:2] == ["KEY resize", "TIMEOUT"], repr(L))
    w.send("q", 1.0)
    w.end()

    w = launch("D-wait", "zztl2 wait", 140, 43)
    c = R.row("D6c zztl2 wait shows its form", "[ OK ]" in w.text() or "OK" in w.text(), w.text()[:300])
    n0 = len(log())
    w.send("z", 1.0)
    w.resize(150, 45, 1.0)
    w.send(E, 0.4)
    w.pump(0.8)
    L = lines_from(n0)
    R.row("D6 SCREEN WAIT: z (a key the form does not use) opens SCREEN ASK; a resize while it is open is the form's next event, at once: EV key z, ASK, EV resize 150x45",
          c and L[:3] == ["EV key z", "ASK", "EV resize 150x45"], repr(L))
    w.pump(3.5)
    L = lines_from(n0)
    R.row("D7 ...once: the wait after it times out (ELSE timeout)", c and L[3:4] == ["ELSE timeout"], repr(L))
    w.send(RET, 1.0)
    w.end()


# ------------------------------------------------------------------------------------------------------------------------ E: the frame cache's epoch
def sec_epoch():
    say("\n--- E: F1, the second open of an app draws its whole frame")
    w = launch("E", "zztl3", 140, 43)
    f0 = foot(w.lines(), 140, 43)
    c = R.row("E0 control: the first open draws the status line ([P] the same status text), the border and the key row", f0["ok"] and "the same status text" in w.lines()[40], repr(f0))
    off = w.mark()
    w.send("n", 1.0)
    nb = len(w.s.raw) - off
    R.row("E1 the cache still works: $tk_frame called again with nothing changed writes next to nothing (%d bytes for the key and the call)" % nb, c and nb <= 24, "bytes %d: %r" % (nb, w.post(off)[:80]))
    off = w.mark()
    w.send("x", 1.5)
    fr = w.fresh(off)
    f = foot(fr.lines(), 140, 43)
    R.row("E2 F1: after $tk_close and a second $tk_open (SCREEN OPEN clears the screen), the SAME status text, border and keys are written again (the bytes after the key hold them)",
          c and f["ok"] and "the same status text" in fr.lines()[40], "%r; bytes %d" % (f, len(w.post(off))))
    w.send("x", 1.5)
    R.row("E3 ...and the program ends (ZZTL3 DONE)", "ZZTL3 DONE" in w.text(), w.text()[-200:])
    w.end()


# ------------------------------------------------------------------------------------------------------------------------ main
def main():
    global BOX, SYS
    try:
        sh.setup("sandbox-tk-layout.py")
        BOX, SYS = sh.BOX, sh.SYS
        say("sandbox-tk-layout: sandbox %s, keyset %s" % (BOX, os.environ.get("SDBOX_KEYSET")))
        fixture()
        sh.set_default("terminal")
        sec_service()
        sec_resize()
        sec_lock()
        sec_dialog()
        sec_epoch()
    finally:
        sh.teardown()
    sys.exit(R.finish())


if __name__ == "__main__":
    main()
