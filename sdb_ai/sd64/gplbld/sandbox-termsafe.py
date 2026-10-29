#!/usr/bin/env python3
#
# sandbox-termsafe.py - terminal safety, data safety and the screen library's set / focus / frame behaviour (S.88, Phase 0 of ~/Documents/Audits/TUI/Opus_TUI_Plan.txt, rows
# S1 S2 S3 S4 D3 F1 F2 F3 of the defect register).  No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-termsafe.py <dir> [--build] [--strict] [--slow]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 every row that counts
# passed, 1 a row failed, 2 it could not run.  --strict counts a row of a phase that has not landed as FAILED (that is how the red run on the old tree is made); without it such a
# row is PENDING (tuirows.py).  --slow adds the AUTOLOGOUT rows (about three minutes of idling); without it they are SKIPPED, printed as skipped, and not counted as passed.
#
# START-HISTORY:
# 28 Oct 26 dm  New (S.88 Phase 0).  Written from the probes of the Opus evaluation (Opus_TUI_Evidence/rt2: probe_lib, probe_pages, probe_e2).
# 28 Oct 26 dm  S.88 phase 2 (written, not run): section D4 - the break key after an abort inside a toolkit app and after SED, and HOME after a refused tile command (plan 2.5, 2.6).
# 28 Oct 26 dm  TUI phase 2 review (written, not run): D4d0 - a tile command that aborts waits for Enter before HOME is drawn again, and D4d presses it.
# END-HISTORY
#
# WHAT IT HOLDS, row by row (the id is the plan's; the phase is the plan's phase whose change makes the row pass):
#   W / S1   escape sequences in the DATA of a user program's LABEL, TABLE cell, LIST item and MEMO line must not reach the terminal as ESC ] 0 ; ... BEL or ESC [ 2 J          [2]
#   P / S1   the same bytes as VOC ids (tool.files, tool.voc), the id of a tree entry and a source line (the IDE)                                                              [2]
#   K / S1   an ORDINARY session's READU lock on a record id holding ESC bytes must not reach the ADMINISTRATOR's terminal through tool.sessions                               [2]
#   S2       tool.query with voc-edit ON and bp-edit OFF and a VOC entry &queries& that points at bp must not overwrite (S) or delete (X) a bp record                         [2]
#   S4       tool.voc D on the VOC entry `all` is refused by the page, and the account's VOC is not emptied                                                                  [2]
#   D4       the break key is back (PTERM DISPLAY at the prompt) after an abort inside a toolkit app and after SED, the person's own Off is not turned on, and HOME survives a refused tile command   [2]
#   D3       memo undo keeps a value mark: type, Ctrl-Z, byte for byte (subvalue and text marks are the controls)                                                               [2]
#   F2       SCREEN SET ... VALUE '' / TEXT '' / ITEMS '' clear an entry, a label, a list, a table's rows and a memo                                                           [3]
#   F3       a hidden or disabled entry takes no typed letters, and the focus moves on                                                                                          [3]
#   F1       the frame cache: tool.keys opened twice in one session draws the app name, the status line, the border and the key row both times; tool.files after tool.keys      [3]
#   S3       AUTOLOGOUT ends a session that waits in a screen library app (--slow)                                                                                            [2]
#
# THE INSTRUMENT.  A terminal-safety row is judged on the RAW BYTES the program wrote (PtySession.raw), taken from a mark made just before the command was typed: termscreen.py drops
# an OSC and prints the rest, so the emulated screen cannot show the fault.  Every such row has a CONTROL that passes on today's tree and proves the page was reached: the plain text
# next to the planted bytes (a prefix that is part of the same label, cell, item, line or id) did reach the terminal.  A control that fails makes its row FAIL (no phase): an
# instrument that did not reach the page must never pass.  Outcomes of the data rows (S2, S4, D3, F2, F3) are read from the DISK or from SD (a program the page's own session is
# not, a separate session, the administrator's reader), never from what the page said.  Every pty is printed with the account, window and the keys sent.
#
# THE ACCOUNTS (fixture accounts, ORDINARY sessions, sandbox-gates.py's way): zzhd (sandbox-home's, all three edit gates on) runs the widget programs, the memo, set / focus and
# frame rows; zzta holds the planted records; zzq1 has voc-edit ON, bp-edit OFF and dict-edit ON; zzq2 has all three on; zztv is a throw-away VOC for the tool.voc rows.
# NOT HELD HERE: key decoding (sandbox-realkeys.py), resize (sandbox-tk-resize.py), the IDE at a bare start (sandbox-ide-fresh.py).
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import importlib.util  # noqa: E402
from tuirows import Rows  # noqa: E402


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sh = _load("sandbox_home_for_termsafe", "sandbox-home.py")
g, H, adm = sh.g, sh.H, sh.adm
R = Rows("termsafe")
SLOW = "--slow" in sys.argv
SKIPPED = []

ESC = "\x1b"
F8, F9 = "\x1b[19~", "\x1b[20~"
CTRL_Q, CTRL_Z = "\x11", "\x1a"
TAB, RET, DOWN = "\t", "\r", "\x1b[B"
HD, ZT, Q1, Q2, TV, BK = "zzhd", "zzta", "zzq1", "zzq2", "zztv", "zzbk"
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def say(s=""):
    print(s, flush=True)


def bail(msg):
    say("sandbox-termsafe: CANNOT RUN - " + msg)
    sys.exit(2)


def acct_dir(a):
    return os.path.join(sh.BOX, "user_accounts", a)


def bpfile(a, n):
    return os.path.join(acct_dir(a), "bp", n)


# ---------------------------------------------------------------------------------------------------------------------------------------- the pty helpers

def open_h(account=None, admin=False, cols=140, rows=43):
    h = H(account=account, admin=admin, cols=cols, rows=rows)
    say("  [pty] argv=%s%s cwd=%s TERM=xterm (the account's LOGIN then sets linux) LC_ALL=C window=%dx%d SDTEST_ADMIN=%s SDBOX_KEYSET=%s SD_CONFIG=%s" % (
        os.path.join(sh.SYS, "bin", "sd"), (" -a" + account) if account else "", sh.SYS if admin else acct_dir(account), cols, rows,
        "1" if admin else "unset", os.environ.get("SDBOX_KEYSET", "(unset)"), os.path.join(sh.BOX, "sd.conf")))
    return h


def send(h, data, idle=0.8, label=""):
    say("  [key] %s%r" % ((label + " ") if label else "", data))
    h.s.type(data, idle=idle)


def waitfor(h, secs):
    """PtySession._pump returns at the FIRST byte, so a wait of N seconds is a deadline loop."""
    end = time.time() + secs
    while time.time() < end and not h.s.exited:
        h.s._pump(min(0.2, max(0.0, end - time.time())))


def mark(h):
    return len(h.s.raw)


def tail_ctx(raw, i, n=14):
    return raw[max(0, i - n):i + n]


def until(h, pred, secs=15.0):
    end = time.time() + secs
    while time.time() < end:
        if pred(h.text()):
            return True
        h.s._pump(0.4)
    return pred(h.text())


def compile_progs(account, progs):
    for n, body in progs.items():
        g.put(bpfile(account, n), body)
    out = g.plain(account, ["BASIC bp %s" % n for n in progs])
    n_ok = sum(1 for l in out if re.match(r"^Compiled 1 program\(s\) with no errors", l))
    say("    compiled %d of %d programs in %s with no errors" % (n_ok, len(progs), account))
    if n_ok != len(progs):
        raise RuntimeError("programs did not compile in %s: %s" % (account, " | ".join(out[-12:])))


def read_res(account, name):
    p = bpfile(account, name)
    if not os.path.isfile(p):
        return None
    with open(p, "rb") as fh:
        return fh.read().decode("latin-1").split("\n")


def resdict(lines):
    d = {}
    for l in lines or []:
        if "=" in l:
            k, v = l.split("=", 1)
            d[k] = v
    return d


def codes(s):
    s = (s or "").strip().strip(",")
    return bytes(int(x) for x in s.split(",")) if s else b""


def show_res(account, name):
    r = read_res(account, name)
    say("    disk %s/bp/%s: %s" % (account, name, "ABSENT" if r is None else ""))
    for l in r or []:
        if l.strip():
            say("      " + l)
    return r


def reg_record(name, voc, bp, dic):
    return [acct_dir(name), "", g.GROUP, "", "", "", "no", "no", "no", voc, bp, dic, "", "", "no", "", "", ""]


def make_account(name, voc="yes", bp="yes", dic="yes"):
    g.FIXTURES[name] = ("no", "no")
    g.build_account(name)
    g.reg_write(name, reg_record(name, voc, bp, dic))


def esc_rows(rid, label, raw, prefix, marker, kind):
    """One data row and its control.  raw: bytes; prefix: the plain text next to the planted bytes (bytes); marker: PWNxxx (an OSC title) or CLRxxx (a clear screen).
    The row is held to the plan's phase 2 only when its control passed."""
    pre = raw.find(prefix) >= 0
    bad = (b"\x1b]0;" if kind == "osc" else b"\x1b[2J") + marker
    i = raw.find(bad)
    seen = raw.find(marker)
    R.row("%s-ctl %s: the plain text next to the planted bytes (%r) reached the terminal" % (rid, label, prefix.decode()), pre, "the page did not show %r in %d bytes" % (prefix, len(raw)))
    R.row("%s %s: %s is not written raw to the terminal" % (rid, label, repr(bad)), pre and i < 0,
          ("RAW at byte %d: %r" % (i, tail_ctx(raw, i))) if i >= 0 else ("(%s %s)" % ("the marker text is shown neutralised" if seen >= 0 else "the marker text is not shown at all", "")),
          phase=2 if pre else None)


# ---------------------------------------------------------------------------------------------------------------------------------------- the programs

# S1: a form whose label, table cell, list item and memo line each hold ESC ] 0 ; PWNxxx BEL | ESC [ 2 J CLRxxx, after a plain prefix of their own
ZZPD = """   pl = 'lbl-ok:' : char(27) : ']0;PWNLBL' : char(7) : '|' : char(27) : '[2JCLRLBL'
   pt = 'tbl-ok:' : char(27) : ']0;PWNTBL' : char(7) : '|' : char(27) : '[2JCLRTBL'
   pi = 'lst-ok:' : char(27) : ']0;PWNLST' : char(7) : '|' : char(27) : '[2JCLRLST'
   pm = 'mem-ok:' : char(27) : ']0;PWNMEM' : char(7) : '|' : char(27) : '[2JCLRMEM'
   screen open clear else stop
   screen form title 'Esc' at 2,2 size 80,22 returning f
   screen label f, 'l', pl at 2,1 width 60
   screen table f, 't', 'A':@sm:'6L':@vm:'B':@sm:'40L', 'r1':@vm:pt:@fm:'r2':@vm:'y' at 2,3 size 60,4
   screen list f, 'li', 'aa':@vm:pi:@vm:'cc' at 2,9 size 40,4
   screen memo f, 'm', 'line one':@fm:pm at 2,14 size 60,3
   screen button f, 'ok', '&OK' at 2,19 default
   loop
      screen wait f timeout 20 returning ev else exit
      if ev<1> = 'key' and ev<3> = 'f9' then exit
   repeat
   screen hide f
   crt @(0,30) : 'ZZPD-DONE'
end
"""

# S1: plants VOC entries whose ids hold ESC bytes (a file pointer to bp, a verb-like entry, a plain entry) and a bp record whose source line holds them
ZZPDW = """   open 'VOC' to voc else stop 'NOVOC'
   read bpv from voc, 'bp' else stop 'NOBPVOC'
   write bpv on voc, '!!f' : char(27) : ']0;PWNFIL' : char(7)
   write 'X' : char(27) : ']0;PWNVOC' : char(7) : '|' : char(27) : '[2JCLRVOC desc' on voc, '!!v'
   write 'X plain' on voc, '!!w' : char(27) : ']0;PWNVID' : char(7)
   open 'bp' to bpf else stop 'NOBP'
   s = 'program zzescsrc' : @fm : '* ' : char(27) : ']0;PWNIDE' : char(7) : ' and ' : char(27) : '[2JCLRIDE' : @fm : 'crt "hi"' : @fm : 'end'
   write s on bpf, 'zzescsrc'
   crt 'WROTE-FIXTURES ' : bpv<1>
end
"""

# S1 / tool.sessions: an ORDINARY session takes a record lock on an id that holds ESC bytes and keeps it until the record zzlkstop appears in bp
ZZLK = """   open 'zzlf' to f else
      crt 'ZZLK nofile'
      stop
   end
   open 'bp' to bpf else
      crt 'ZZLK nobp'
      stop
   end
   id = char(27) : ']0;PWNLCK' : char(7) : '|' : char(27) : '[2JCLRLCK'
   readu r from f, id else null
   crt 'ZZLK holding'
   loop
      sleep 1
      read s from bpf, 'zzlkstop' then exit else null
   repeat
   crt 'ZZLK done'
end
"""

# S2: an ordinary program that tries to change bp (the control: the bp-edit gate is really off for the account), and a reader of &queries& through the VOC pointer
ZZQBW = """   open 'bp' to bpf else
      crt 'ZQB nobp'
      stop
   end
   write 'GATE-CONTROL' on bpf, 'zzgatectl' on error crt 'ZQB refused'
   crt 'ZQB done'
end
"""

ZZQRD = """   open '&queries&' to qf else
      crt 'ZQR[nofile]'
      stop
   end
   select qf to 9
   n = 0
   ids = ''
   loop
      readnext id from 9 else exit
      n += 1
      ids<-1> = id
   repeat
   crt 'ZQR[' : n : '|' : change(ids, @fm, ',') : ']'
   read r from qf, 'qa-one' then crt 'ZQR1[' : r<1> : '|' : r<2> : ']' else crt 'ZQR1[none]'
end
"""

# S4: the throw-away VOC entries (an ordinary sentence to delete as the control)
ZZVW = """   open 'VOC' to v else crt 'VW no voc' ; stop
   write 'S':@fm:'list voc' on v, 'zzsent'
   crt 'VW done'
end
"""

# D3 / F2 / F3: from the Opus probes (rt2/probe_lib.py) - the program records what the library holds and what the widgets read back
CODES_SUB = """
codes.of:
   cs = ''
   for ci = 1 to len(cx)
      cs := seq(cx[ci, 1]) : ','
   next ci
   return
"""

ZZPA = """   open 'bp' to bpf else stop 'no bp'
   res = ''
   screen open clear else crt 'NOTERM' ; stop
   screen form title 'Clear' at 2,2 size 70,20 returning f
   screen label f, 'l', 'LabelOne' at 2,1 width 20
   screen label f, 'l2', 'LabelTwo' at 2,2 width 20
   screen entry f, 'e' at 2,4 width 20 value 'abc'
   screen entry f, 'e2' at 2,6 width 20 value 'abc'
   screen list f, 'li', 'aa':@vm:'bb':@vm:'cc' at 30,1 size 12,4
   screen list f, 'li2', 'aa':@vm:'bb':@vm:'cc' at 46,1 size 12,4
   screen memo f, 'm', 'mm1':@fm:'mm2' at 30,7 size 20,3
   screen table f, 't', 'A':@sm:'6L':@vm:'B':@sm:'6L', 'r1':@vm:'x':@fm:'r2':@vm:'y' at 2,9 size 30,4
   screen button f, 'ok', '&OK' at 2,16 default
   ph = 'before' ; gosub record
   loop
      screen wait f timeout 30 returning ev else exit
      if ev<1> = 'key' and ev<3> = 'f8' then
         screen set f, 'e' value ''
         screen set f, 'e2' value 'x'
         screen set f, 'l' text ''
         screen set f, 'l2' text 'NewLbl'
         screen set f, 'li' items ''
         screen set f, 'li2' items 'zz'
         screen set f, 'm' readonly 1
         screen set f, 'm' value ''
         screen set f, 'm' readonly ''
         screen set f, 'e2' visible 1
         screen set f, 'l2' enabled ''
         screen set f, 't' items ''
         ph = 'after' ; gosub record
         write res on bpf, 'zzr_a'
      end
      if ev<1> = 'key' and ev<3> = 'f9' then exit
   repeat
   screen hide f
   write res on bpf, 'zzr_a'
   crt @(0, 30) : 'ZZPA-DONE'
   stop

record:
   nw = inmat(f{'widgets'})
   for wi = 1 to nw
      w = f{'widgets', wi}
      wid = w{'id'}
      cx = w{'value'} ; gosub codes.of ; res<-1> = ph : '.' : wid : '.value=' : cs
      cx = w{'text'} ; gosub codes.of ; res<-1> = ph : '.' : wid : '.text=' : cs
      cx = w{'items'} ; gosub codes.of ; res<-1> = ph : '.' : wid : '.items=' : cs
      cx = w{'rows'} ; gosub codes.of ; res<-1> = ph : '.' : wid : '.rows=' : cs
      cx = w{'readonly'} ; gosub codes.of ; res<-1> = ph : '.' : wid : '.readonly=' : cs
      cx = w{'disabled'} ; gosub codes.of ; res<-1> = ph : '.' : wid : '.disabled=' : cs
   next wi
   return
""" + CODES_SUB + "end\n"

ZZPC = """   open 'bp' to bpf else stop
   mode = field(trim(@sentence), ' ', 4)
   begin case
      case mode = 'vm' ; mk = @vm
      case mode = 'sm' ; mk = @sm
      case mode = 'tm' ; mk = @tm
      case 1 ; mk = '-'
   end case
   orig = 'ab' : mk : 'cd' : @fm : 'ef'
   res = 'mode=' : mode
   cx = orig ; gosub codes.of ; res<-1> = 'orig=' : cs
   screen open clear else stop
   screen form title 'Memo' at 2,2 size 50,12 returning f
   screen memo f, 'm', orig at 2,2 size 30,5
   screen button f, 'ok', '&OK' at 2,9
   screen get f, 'm' returning g0
   cx = g0 ; gosub codes.of ; res<-1> = 'loaded=' : cs
   loop
      screen wait f timeout 30 returning ev else exit
      if ev<1> = 'key' and ev<3> = 'f8' then
         screen get f, 'm' returning g1
         cx = g1 ; gosub codes.of ; res<-1> = 'typed=' : cs
      end
      if ev<1> = 'key' and ev<3> = 'f9' then exit
   repeat
   screen get f, 'm' returning g2
   cx = g2 ; gosub codes.of ; res<-1> = 'undone=' : cs
   res<-1> = 'identical=' : (if compare(g2, orig) = 0 then 1 else 0)
   screen hide f
   write res on bpf, 'zzr_c_' : mode
   crt @(0,30) : 'ZZPC-DONE ' : mode
   stop
""" + CODES_SUB + "end\n"

ZZPE = """   open 'bp' to bpf else stop
   mode = field(trim(@sentence), ' ', 4)
   res = 'mode=' : mode
   screen open clear else stop
   screen form title 'Focus' at 2,2 size 50,12 returning f
   screen label f, 'l1', 'One:' at 2,2
   screen entry f, 'e1' at 8,2 width 20
   screen label f, 'l2', 'Two:' at 2,4
   screen entry f, 'e2' at 8,4 width 20
   screen button f, 'ok', '&OK' at 2,8 default
   res<-1> = 'focus.start=' : f{'focus'}
   loop
      screen wait f timeout 30 returning ev else exit
      res<-1> = 'ev=' : ev<1> : '/' : ev<2> : '/' : ev<3>
      if ev<1> = 'key' and ev<3> = 'f8' then
         if mode = 'hidden' then screen set f, 'e1' visible 0
         if mode = 'disabled' then screen set f, 'e1' enabled 0
         res<-1> = 'focus.after.set=' : f{'focus'}
      end
      if ev<1> = 'key' and ev<3> = 'f9' then exit
   repeat
   screen get f, 'e1' returning v1
   screen get f, 'e2' returning v2
   res<-1> = 'e1=' : v1
   res<-1> = 'e2=' : v2
   res<-1> = 'focus.end=' : f{'focus'}
   screen hide f
   write res on bpf, 'zzr_e_' : mode
   crt @(0,30) : 'ZZPE-DONE ' : mode
end
"""


# ---------------------------------------------------------------------------------------------------------------------------------------- S1: the data of widgets

def section_widgets():
    say("\n--- S1 W: ESC bytes in the data of a label, a table cell, a list item and a memo line (a user program, raw bytes)")
    compile_progs(HD, {"zzpd": ZZPD})
    h = open_h(account=HD)
    m = mark(h)
    send(h, "RUN bp zzpd\r", idle=1.5, label="run the form")
    waitfor(h, 2.5)
    raw = h.s.raw[m:]
    say("  bytes written after the command: %d; the form is on the screen: %s" % (len(raw), "Esc" in h.text()))
    for rid, label, prefix, tag in (("S1-LBL", "label", b"lbl-ok:", b"LBL"), ("S1-TBL", "table cell", b"tbl-ok:", b"TBL"), ("S1-LST", "list item", b"lst-ok:", b"LST"),
                                    ("S1-MEM", "memo line", b"mem-ok:", b"MEM")):
        esc_rows(rid + "a", label + " (OSC title)", raw, prefix, b"PWN" + tag, "osc")
        esc_rows(rid + "b", label + " (clear screen)", raw, prefix, b"CLR" + tag, "csi")
    send(h, F9, idle=1.0, label="F9 ends the program")
    h.end()


# ---------------------------------------------------------------------------------------------------------------------------------------- S1: record ids and source lines in the pages

def section_pages():
    say("\n--- S1 P: ESC bytes in VOC ids and a source line, in tool.files, tool.voc and the IDE (raw bytes)")
    compile_progs(ZT, {"zzpdw": ZZPDW})
    out = g.plain(ZT, ["RUN bp zzpdw"])
    wrote = any("WROTE-FIXTURES" in l for l in out)
    R.row("S1-P0 the planted VOC records and the bp record were written by an ordinary session", wrote and os.path.isfile(bpfile(ZT, "zzescsrc")), "\n".join(out[-6:]))
    if not wrote:
        return
    with open(bpfile(ZT, "zzescsrc"), "rb") as fh:
        say("    disk bp/zzescsrc: %r" % fh.read())
    pages = (
        ("tool.files", "tool.files\r", [("S1-FIL", "id of a file pointer in tool.files", b"!!f", b"PWNFIL", "osc")]),
        ("tool.voc", "tool.voc\r", [("S1-VOCa", "id of a file pointer in tool.voc", b"!!f", b"PWNFIL", "osc"), ("S1-VOCb", "id of an entry in tool.voc", b"!!w", b"PWNVID", "osc")]),
        ("IDE bp zzescsrc", "IDE bp zzescsrc\r", [("S1-IDEa", "id of a file pointer in the IDE tree", b"!!f", b"PWNFIL", "osc"), ("S1-IDEb", "source line in the IDE editor (OSC title)", b"zzescsrc", b"PWNIDE", "osc"),
                                                  ("S1-IDEc", "source line in the IDE editor (clear screen)", b"zzescsrc", b"CLRIDE", "csi")]),
    )
    for cmd, typed, checks in pages:
        say("  -- %s" % cmd)
        h = open_h(account=ZT)
        m = mark(h)
        send(h, typed, idle=1.5, label=cmd)
        waitfor(h, 3.5)
        raw = h.s.raw[m:]
        say("  bytes written after the command: %d; screen row 0: %r" % (len(raw), h.line(0)[:100]))
        for rid, label, prefix, marker, kind in checks:
            esc_rows(rid, label, raw, prefix, marker, kind)
        send(h, CTRL_Q, idle=1.2, label="Ctrl-Q")
        h.end()


# ---------------------------------------------------------------------------------------------------------------------------------------- S1: tool.sessions and an ordinary user's lock id

class Holder:
    """An ORDINARY session on a pipe, kept open, that runs zzlk (a lock on an id holding ESC bytes) and stops when bp/zzlkstop appears."""

    def __init__(self, account):
        env = dict(os.environ, SD_CONFIG=os.path.join(sh.BOX, "sd.conf"))
        env.pop("SDTEST_ADMIN", None)
        env.pop("SSH_CONNECTION", None)
        env.pop("SSH_TTY", None)
        self.out = os.path.join(sh.BOX, "holder-%s.out" % account)
        self.fh = open(self.out, "w")
        argv = [os.path.join(sh.SYS, "bin", "sd"), "-a" + account]
        self.p = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=self.fh, stderr=subprocess.STDOUT, cwd=acct_dir(account), env=env, text=True)
        self.p.stdin.write("\nTERM 200,9999\nRUN bp zzlk\nOFF\n")
        self.p.stdin.flush()
        say("  [holder] argv=%s cwd=%s SDTEST_ADMIN=unset pid=%d stdin: TERM 200,9999 | RUN bp zzlk | OFF" % (argv, acct_dir(account), self.p.pid))

    def text(self):
        self.fh.flush()
        with open(self.out, errors="replace") as f:
            return ANSI.sub("", f.read())

    def stop(self):
        try:
            self.p.wait(timeout=20)
            return True
        except subprocess.TimeoutExpired:
            self.p.stdin.close()
            try:
                self.p.wait(timeout=10)
                return True
            except subprocess.TimeoutExpired:
                self.p.kill()
                self.p.wait()
                return False
        finally:
            try:
                self.fh.close()
            except OSError:
                pass


def section_sessions():
    say("\n--- S1 K: an ordinary user's lock id reaches the administrator's terminal through tool.sessions (raw bytes)")
    compile_progs(ZT, {"zzlk": ZZLK})
    out = g.plain(ZT, ["CREATE.FILE zzlf"])
    hold = Holder(ZT)
    ok = False
    for _ in range(40):
        if "ZZLK" in hold.text():
            ok = True
            break
        time.sleep(0.5)
    t = hold.text()
    say("  holder output: %r" % t[-300:])
    if not ok or "ZZLK holding" not in t:
        # the observation is the refusal itself: READU of such an id was refused, so no such lock can exist
        R.row("S1-K SKIP: READU refused a record id holding ESC bytes, so an ordinary user cannot make such a lock (the refusal is the observation: %r)" % t[-120:].strip(), ok, "the holder program printed nothing at all: %r" % t)
        hold.stop()
        return
    h = open_h(admin=True)
    m = mark(h)
    send(h, "tool.sessions\r", idle=1.5, label="administrator opens tool.sessions")
    waitfor(h, 5.0)
    raw = h.s.raw[m:]
    rl = raw.lower()
    say("  bytes written after the command: %d; the ordinary holder's account (%s) is on the page: %s" % (len(raw), ZT, ZT.encode() in raw))
    pre = ZT.encode() in raw
    R.row("S1-Kctl tool.sessions drew the ordinary holder's session (its account name %s reached the terminal)" % ZT, pre, "the page showed no row for the holder: bytes=%d" % len(raw))
    for rid, bad, name in (("S1-Ka", b"\x1b]0;pwnlck", "ESC ] 0 ; PWNLCK (a title)"), ("S1-Kb", b"\x1b[2jclrlck", "ESC [ 2 J (a clear screen)")):
        i = rl.find(bad)
        seen = rl.find(bad[-6:])
        R.row("%s the ordinary user's READU lock id does not reach the administrator's terminal as %s" % (rid, name), pre and i < 0,
              ("RAW at byte %d: %r" % (i, tail_ctx(raw, i))) if i >= 0 else ("id %s" % ("shown neutralised" if seen >= 0 else "not shown on the page")), phase=2 if pre else None)
    send(h, CTRL_Q, idle=1.2, label="Ctrl-Q")
    h.end()
    g.put(bpfile(ZT, "zzlkstop"), "stop\n")
    R.row("S1-Kend the holder ended by itself once told to (its locks were given back)", hold.stop(), "the holder had to be killed")


# ---------------------------------------------------------------------------------------------------------------------------------------- S2: tool.query and &queries&

def disk_text(path):
    try:
        with open(path, "rb") as fh:
            return fh.read().decode("latin-1")
    except OSError:
        return None


def qreader(account):
    out = g.plain(account, ["RUN bp zzqrd"])
    for l in out:
        m = re.match(r"^ZQR\[(.*)\]$", l.strip())
        if m:
            return m.group(1)
    return "ERROR:" + " | ".join(out[-3:])


def section_query():
    say("\n--- S2: tool.query with voc-edit on and bp-edit off and &queries& pointing at bp (the disk is the evidence)")
    sentinel = "SENTINEL-ORIGINAL\n"
    for a in (Q1, Q2):
        compile_progs(a, {"zzqbw": ZZQBW, "zzqrd": ZZQRD})
        g.plain(a, ["CREATE.FILE zzqf"])
    g.put(bpfile(Q1, "zzqptr"), "   open 'VOC' to v else crt 'QP novoc' ; stop\n   write 'F':@fm:'bp' on v, '&queries&'\n   crt 'QP done'\nend\n")
    out = g.plain(Q1, ["BASIC bp zzqptr", "RUN bp zzqptr"])
    if not any(l.strip() == "QP done" for l in out):
        bail("the &queries& pointer was not written in %s:\n%s" % (Q1, "\n".join(out[-6:])))
    g.put(bpfile(Q1, "aa-sent"), sentinel)
    # the bp-edit gate goes OFF now (the programs above needed it to compile): voc yes, bp NO, dict yes
    g.reg_write(Q1, reg_record(Q1, "yes", "no", "yes"))
    out = g.plain(Q1, ["RUN bp zzqbw"])
    gate_off = (not os.path.isfile(bpfile(Q1, "zzgatectl"))) and any(("ZQB" in l) or ("edit" in l.lower()) or ("refus" in l.lower()) for l in out)
    R.row("S2-ctl1 in %s an ordinary program cannot write bp (the bp-edit gate is really off; disk: no record zzgatectl) and the VOC pointer &queries& -> bp is there" % Q1,
          gate_off, "output %r; zzgatectl on disk: %s" % (out[-3:], os.path.isfile(bpfile(Q1, "zzgatectl"))))
    rd = qreader(Q1)
    R.row("S2-ctl2 a reader of &queries& through the pointer sees the bp record aa-sent (the pointer leads into bp)", "aa-sent" in rd, "reader said %r" % rd)

    h = open_h(account=Q1)
    send(h, "tool.query zzqf\r", idle=2.5, label="tool.query on the file zzqf")
    T = h.text()
    R.row("S2-ctl3 the page is up for %s (the Columns and Options boxes are on the screen)" % Q1, "Columns" in T and "Options" in T, T[:300])
    send(h, "s", idle=1.2, label="S (save)")
    T = h.text()
    R.row("S2-ctl4 S asks for a name for the query", "Save the query" in T, T[-300:])
    send(h, "aa-sent\r", idle=1.5, label="the name aa-sent, which is an existing bp record")
    if until(h, lambda t: "Replaces the saved query" in t, 3.0):
        send(h, "r", idle=1.2, label="Run")
        send(h, "aa-sent\r", idle=2.0, label="the name typed again")
    else:
        say("    no box 'Replaces the saved query' on the screen: the page did not offer the write (screen tail %r)" % [l.strip()[:80] for l in h.lines() if l.strip()][-3:])
    waitfor(h, 1.5)
    say("    status line: %r" % h.line(40)[:130])
    now = disk_text(bpfile(Q1, "aa-sent"))
    R.row("S2a S: the bp record aa-sent is not overwritten by a saved query (disk: %r)" % (now[:40] if now else now), now == sentinel, "bp/aa-sent now begins %r" % (now[:60] if now else now), phase=2)
    R.row("S2a-ctl the page's own record count is read from disk: the file is there", now is not None, "the bp record is gone")
    send(h, "l", idle=1.5, label="L (list the saved queries)")
    T = h.text()
    say("    the list view shows aa-sent: %s" % ("aa-sent" in T))
    deleted_before = os.path.isfile(bpfile(Q1, "aa-sent"))
    if "aa-sent" in T and deleted_before:
        send(h, "x", idle=1.2, label="X (delete the record under the cursor)")
        if until(h, lambda t: "Deletes the saved query" in t, 3.0):
            send(h, "r", idle=1.2, label="Run")
            send(h, "aa-sent\r", idle=2.0, label="the name typed")
        else:
            say("    no box 'Deletes the saved query' on the screen: the page did not offer the delete")
        waitfor(h, 1.5)
        say("    status line: %r" % h.line(40)[:130])
        R.row("S2b X: the bp record aa-sent is not deleted through &queries& (disk)", os.path.isfile(bpfile(Q1, "aa-sent")), "bp/aa-sent is gone from the disk", phase=2)
    else:
        R.row("S2b X: the bp record aa-sent is not deleted through &queries& (disk)", not deleted_before, "the list did not show aa-sent (%s) and the record %s" % ("aa-sent" in T, "is on disk" if deleted_before else "is gone"),
              phase=2 if deleted_before else None)
        if "aa-sent" not in T and deleted_before:
            R.row("S2b-ctl the list view showed the record the X row had to select", False, "the screen: %r" % T[-300:])
    send(h, ESC, idle=1.0, label="Esc")
    send(h, CTRL_Q, idle=1.2, label="Ctrl-Q")
    h.end()

    say("  -- the control: a normal &queries& in %s (all three edit gates on) saves and loads" % Q2)
    h = open_h(account=Q2)
    send(h, "tool.query zzqf\r", idle=2.5, label="tool.query on the file zzqf")
    send(h, "s", idle=1.2, label="S")
    send(h, "qa-one\r", idle=1.5, label="the name qa-one")
    if until(h, lambda t: "Makes the file" in t, 3.0):
        send(h, "r", idle=1.5, label="Run (makes the file &queries& after its box)")
    if until(h, lambda t: "Saves the query on the screen" in t, 3.0):
        send(h, "r", idle=1.5, label="Run (writes the record)")
    waitfor(h, 1.5)
    rd = qreader(Q2)
    say("    reader of &queries&: %r" % rd)
    R.row("S2-ctl5 a normal &queries& (the page made the file) holds the saved query qa-one on the disk, a query1 record of the file zzqf", "qa-one" in rd, "reader said %r" % rd)
    send(h, "l", idle=1.5, label="L")
    listed = "qa-one" in h.text()
    send(h, RET, idle=1.5, label="Enter (load)")
    waitfor(h, 1.0)
    T = h.text()
    R.row("S2-ctl6 L lists qa-one and Enter loads it (status line says loaded qa-one)", listed and "loaded qa-one" in T, "listed=%s status=%r" % (listed, h.line(40)[:100]))
    send(h, CTRL_Q, idle=1.2, label="Ctrl-Q")
    h.end()


# ---------------------------------------------------------------------------------------------------------------------------------------- S4: tool.voc D on `all`

VOCC = """$internal
   openpath '%s/voc' to v else crt 'VC[novoc]' ; stop
   read r from v, 'all' then ex = 1 else ex = 0
   select v to 9
   n = 0
   loop
      readnext id from 9 else exit
      n += 1
   repeat
   crt 'VC[' : n : '|' : ex : ']'
end
"""


def voc_state(account):
    """(record count, 'all' exists) of the account's VOC, read by a separate ADMINISTRATOR program from the account's voc directory - it works when the VOC has been emptied."""
    g.put(os.path.join(sh.SYS, "bp", "zzvc"), VOCC % acct_dir(account))
    out = adm("BASIC bp zzvc", "RUN bp zzvc")
    for l in out:
        m = re.match(r"^VC\[(\d+)\|(\d)\]$", l.strip())
        if m:
            return int(m.group(1)), int(m.group(2))
    return None, None


def vtable(h):
    order = []
    for n in range(3, 19):
        name = h.line(n)[3:31].strip()
        if name:
            order.append(name)
    return order


def vfilter(h, text):
    send(h, "/", idle=0.8, label="/ (filter)")
    send(h, text + "\r", idle=1.2, label="the filter " + text)


def section_vocall():
    say("\n--- S4: tool.voc D on the VOC entry `all` (a throw-away VOC in %s; the disk is the evidence)" % TV)
    compile_progs(TV, {"zzvw": ZZVW})
    out = g.plain(TV, ["RUN bp zzvw"])
    n0, ex0 = voc_state(TV)
    say("    VOC of %s: %s records, `all` present: %s" % (TV, n0, ex0))
    R.row("S4-ctl0 the fixture VOC holds the entry `all` and the ordinary sentence zzsent (read from the disk by the administrator)", n0 is not None and ex0 == 1 and any("VW done" in l for l in out), "count=%s all=%s out=%r" % (n0, ex0, out[-3:]))
    if n0 is None or ex0 != 1:
        return
    # control: D on an ordinary entry asks, and deletes after Run with the id typed
    h = open_h(account=TV)
    send(h, "tool.voc\r", idle=3.5, label="tool.voc")
    vfilter(h, "zzsent")
    send(h, "d", idle=1.5, label="D")
    T = re.sub(r"[|\s]+", " ", h.text())
    R.row("S4-ctl1 D on an ordinary entry shows the box 'delete voc zzsent' with Run and Cancel", "delete voc zzsent" in T and "Run" in T and "Cancel" in T, T[-300:])
    send(h, "r", idle=1.2, label="Run")
    send(h, "zzsent\r", idle=2.0, label="the id typed")
    until(h, lambda t: "zzsent" not in "\n".join(vtable(h)))
    n1, _ = voc_state(TV)
    R.row("S4-ctl2 Run with the id typed deletes the ordinary entry: the count falls by exactly one (disk)", n1 == n0 - 1, "before %s after %s" % (n0, n1))
    send(h, CTRL_Q, idle=1.2, label="Ctrl-Q")
    h.end()
    n0, _ = voc_state(TV)
    # the fault: D on `all`
    h = open_h(account=TV)
    send(h, "tool.voc\r", idle=3.5, label="tool.voc")
    vfilter(h, "all")
    order = vtable(h)
    say("    entries shown for the filter 'all': %r" % order)
    if "all" not in order:
        R.row("S4-ctl3 the entry `all` is in the filtered list", False, "list: %r" % order)
        send(h, CTRL_Q, idle=1.2)
        h.end()
        return
    for _ in range(order.index("all")):
        send(h, DOWN, idle=0.5, label="Down")
    before_status = h.line(40)
    send(h, "d", idle=1.5, label="D on `all`")
    T = re.sub(r"[|\s]+", " ", h.text())
    box = re.search(r"delete voc (\S+)", T)
    say("    the screen after D: box=%r status=%r" % (box.group(0) if box else None, h.line(40)[:120]))
    if box and box.group(1) != "all":
        R.row("S4-ctl3 the cursor was on `all` when D was pressed", False, "the box names %r" % box.group(0))
        send(h, ESC, idle=1.0)
        send(h, CTRL_Q, idle=1.2)
        h.end()
        return
    offered = box is not None
    R.row("S4a D on `all` is refused by the page: no box offering the command 'delete voc all' (status line: %r)" % h.line(40)[:90], not offered and h.line(40) != before_status,
          "the page offers 'delete voc all' with Run and Cancel" if offered else "no box, but the status line did not change: %r" % h.line(40), phase=2)
    if offered:
        send(h, "r", idle=1.5, label="Run (the page's confirm sequence; a fixture VOC)")
        send(h, "all\r", idle=3.0, label="the id typed (no y is ever sent)")
        waitfor(h, 3.0)
        say("    the screen after Run: %r" % [l.strip()[:100] for l in h.lines() if l.strip()][-4:])
    n2, ex2 = voc_state(TV)
    R.row("S4b the account's VOC is not emptied: the record count is unchanged (disk) %s -> %s, `all` present: %s" % (n0, n2, ex2), n2 == n0 and ex2 == 1, "before %s after %s, all=%s" % (n0, n2, ex2), phase=2)
    h.end()


# ---------------------------------------------------------------------------------------------------------------------------------------- D3 / F2 / F3: the library

def run_prog(account, cmd, wait=2.0):
    h = open_h(account=account)
    send(h, cmd + "\r", idle=1.5, label=cmd)
    waitfor(h, wait)
    return h


def section_memo():
    say("\n--- D3: memo undo with a value mark in the line (the saved record is the evidence)")
    compile_progs(HD, {"zzpc": ZZPC})
    for mode in ("plain", "sm", "tm", "vm"):
        h = run_prog(HD, "RUN bp zzpc %s" % mode)
        up = "Memo" in h.text()
        send(h, "Z", idle=0.6, label="type Z")
        send(h, F8, idle=0.8, label="F8 (the program records the value)")
        send(h, CTRL_Z, idle=0.8, label="Ctrl-Z undo")
        send(h, F9, idle=1.0, label="F9 (end)")
        h.end()
        r = show_res(HD, "zzr_c_" + mode)
        d = resdict(r)
        orig, typed, undone = codes(d.get("orig")), codes(d.get("typed")), codes(d.get("undone"))
        say("  MATRIX D3 %-5s orig=%r typed=%r undone=%r identical=%s" % (mode, orig, typed, undone, d.get("identical")))
        reached = up and r is not None and typed[:1] == b"Z" and len(orig) > 0
        if mode == "vm":
            R.row("D3-ctl vm: the memo form was up, the typed Z reached the memo (typed value %r)" % typed, reached, "form up=%s record=%s typed=%r" % (up, r is not None, typed))
            R.row("D3 vm: type Z then Ctrl-Z leaves a line holding a value mark byte for byte as it was (%r)" % orig, reached and undone == orig, "after undo %r, expected %r" % (undone, orig), phase=2 if reached else None)
        else:
            R.row("D3-ctl %s: type Z then Ctrl-Z leaves the line byte for byte as it was (the control for a mark that already survives)" % mode, reached and undone == orig, "form up=%s typed=%r orig=%r undone=%r" % (up, typed, orig, undone))


def section_set():
    say("\n--- F2: SCREEN SET ... VALUE '' / TEXT '' / ITEMS '' (what the library holds afterwards is the evidence)")
    compile_progs(HD, {"zzpa": ZZPA})
    h = run_prog(HD, "RUN bp zzpa")
    up = "Clear" in h.text() and "LabelOne" in h.text()
    send(h, F8, idle=1.0, label="F8 (the program runs the SET statements)")
    shown_after = h.text()
    send(h, F9, idle=1.0, label="F9 (end)")
    h.end()
    d = resdict(show_res(HD, "zzr_a"))

    def dd(k):
        return codes(d.get(k)) if k in d else None
    for wid, fld in (("e", "value"), ("e2", "value"), ("l", "text"), ("l2", "text"), ("li", "items"), ("li2", "items"), ("m", "value"), ("t", "rows")):
        say("  MATRIX F2 %-3s %-5s before=%r after=%r" % (wid, fld, dd("before.%s.%s" % (wid, fld)), dd("after.%s.%s" % (wid, fld))))
    got = dd("after.e2.value") is not None
    R.row("F2-ctl0 the form was up and the program ran its SET statements (the record holds the values read after F8)", up and got, "form up=%s after-record=%s" % (up, got))
    for rid, wid, fld, want, what in (("F2-ctl1", "e2", "value", b"x", "VALUE 'x' sets an entry"), ("F2-ctl2", "l2", "text", b"NewLbl", "TEXT 'NewLbl' sets a label"), ("F2-ctl3", "li2", "items", b"zz", "ITEMS 'zz' sets a list")):
        R.row("%s %s" % (rid, what), got and dd("after.%s.%s" % (wid, fld)) == want, "after %r" % dd("after.%s.%s" % (wid, fld)))
    for rid, wid, fld, what in (("F2-VAL", "e", "value", "VALUE '' clears an entry"), ("F2-TXT", "l", "text", "TEXT '' clears a label"), ("F2-ITM", "li", "items", "ITEMS '' clears a list"),
                                ("F2-ROW", "t", "rows", "ITEMS '' clears a table's rows"), ("F2-MEM", "m", "value", "VALUE '' clears a memo")):
        a = dd("after.%s.%s" % (wid, fld))
        R.row("%s %s (the widget reads back empty)" % (rid, what), got and a == b"", "after %r (before %r)" % (a, dd("before.%s.%s" % (wid, fld))))
    # owner decision 5(b), 29 Oct 26: a written '' on a flag changes nothing, and a clause left out changes nothing
    ro = dd("after.m.readonly")
    R.row("F2-RO READONLY 1 then READONLY '' leaves the memo a viewer (readonly reads back 1, not 0)", got and ro == b"1", "after %r" % ro)
    R.row("F2-ENA ENABLED '' leaves a label enabled (disabled reads back 0 or empty, not 1)", got and dd("after.l2.disabled") in (b"", b"0"), "after %r" % dd("after.l2.disabled"))
    R.row("F2-OMIT a SET that writes only VISIBLE leaves an entry's value alone (e2 still reads x)", got and dd("after.e2.value") == b"x", "after %r" % dd("after.e2.value"))


def section_focus():
    say("\n--- F3: a hidden or disabled entry and the focus (what the entries hold afterwards is the evidence)")
    compile_progs(HD, {"zzpe": ZZPE})
    res = {}
    for mode in ("control", "hidden", "disabled"):
        h = run_prog(HD, "RUN bp zzpe %s" % mode)
        up = "Focus" in h.text()
        send(h, F8, idle=0.8, label="F8 (the program sets e1 %s)" % mode)
        send(h, "xyz", idle=0.8, label="type xyz")
        say("    cursor (col,row)=(%d,%d)" % (h.s.screen.c, h.s.screen.r))
        send(h, F9, idle=1.0, label="F9 (end)")
        h.end()
        d = resdict(show_res(HD, "zzr_e_" + mode))
        res[mode] = (up, d)
        say("  MATRIX F3 %-8s e1=%r e2=%r focus.start=%s after.set=%s end=%s" % (mode, d.get("e1"), d.get("e2"), d.get("focus.start"), d.get("focus.after.set"), d.get("focus.end")))
    up, d = res["control"]
    R.row("F3-ctl the form was up and with no change typing xyz fills the first entry (e1=%r)" % d.get("e1"), up and d.get("e1") == "xyz" and d.get("e2") == "", "form up=%s e1=%r e2=%r" % (up, d.get("e1"), d.get("e2")))
    for mode, rid in (("hidden", "F3h"), ("disabled", "F3d")):
        up, d = res[mode]
        reached = up and "e1" in d
        R.row("%s-a an entry set %s takes no typed letters (e1 is empty, was %r)" % (rid, mode, d.get("e1")), reached and d.get("e1") == "", "e1=%r" % d.get("e1"), phase=3 if reached else None)
        R.row("%s-b the focus moves on: the letters go to the next entry (e2=%r)" % (rid, d.get("e2")), reached and d.get("e2") == "xyz", "e2=%r e1=%r" % (d.get("e2"), d.get("e1")), phase=3 if reached else None)


# ---------------------------------------------------------------------------------------------------------------------------------------- F1: the frame cache

SEQ = re.compile(rb"\x1b\[[0-9;?<>]*[ -/]*[@-~]|\x1b\][^\x07]*\x07|\x1b[()][0-9A-Za-z]|\x1b.")
CUP = re.compile(rb"\x1b\[(\d*)(?:;(\d*))?H")


def nonblank_by_row(raw):
    """{row (0-based): non-blank printable cells written}, following the cursor positions (ESC [ r ; c H) in the bytes."""
    rows = {}
    r = 0
    pos = 0

    def add(chunk):
        n = len(re.sub(rb"[\x00-\x1f\x7f ]", b"", chunk))
        if n:
            rows[r] = rows.get(r, 0) + n
    for m in SEQ.finditer(raw):
        add(raw[pos:m.start()])
        pos = m.end()
        c = CUP.fullmatch(m.group(0))
        if c:
            r = int(c.group(1) or 1) - 1
    add(raw[pos:])
    return rows


def frame(h, app, status):
    L = [h.line(0), h.line(40), h.line(41), h.line(42)]
    return {"name": app in L[0], "status": status in L[1], "border": L[2].strip() != "", "keys": "quit" in L[3].lower()}


def frame_row(rid, what, h, m, app, status, gate):
    """Two rows: what the screen shows, and what was WRITTEN after the command.  gate: (screen control passed, bytes control passed) or None for the controls themselves.
    Returns (screen ok, bytes ok)."""
    st = frame(h, app, status)
    nb = nonblank_by_row(h.s.raw[m:])
    cells = [nb.get(r, 0) for r in (0, 40, 41, 42)]
    s_ok = all(st.values())
    # 29 Oct 26: the pages' first status message no longer carries a key hint, so the status row can hold only its pane name ("[Files]", 7 cells): its floor is the pane's name
    b_ok = nb.get(40, 0) >= (len(status) if status else 10) and all(nb.get(r, 0) >= 10 for r in (41, 42)) and nb.get(0, 0) >= len(app)
    say("    %s: screen %r; non-blank cells written on rows 0/40/41/42 after the command: %r; rows 40-42 now: %r" % (what, st, cells, [h.line(r)[:60] for r in (40, 41, 42)]))
    R.row("%s %s: the app name, the status line, the border and the key row are on the screen" % (rid, what), s_ok, "screen %r" % (st,),
          phase=None if gate is None else (3 if gate[0] else None))
    R.row("%s-bytes %s: the bytes written after the command put non-blank cells on the status, border and key rows" % (rid, what), b_ok, "non-blank cells rows 0/40/41/42: %r" % (cells,),
          phase=None if gate is None else (3 if gate[1] else None))
    return s_ok, b_ok


def section_frame():
    say("\n--- F1: the frame cache (the same page twice in one session; another page after it)")
    h = open_h(account=HD)
    m = mark(h)
    send(h, "tool.keys\r", idle=1.5, label="tool.keys (first open)")
    waitfor(h, 2.0)
    first = frame_row("F1-ctl", "tool.keys, first open in the session", h, m, "tool.keys", "[Keys]", None)
    if not all(first):
        say("  the first open does not draw the whole frame by this instrument: the F1 rows whose control failed are held to the pass, not to phase 3")
    send(h, CTRL_Q, idle=1.5, label="Ctrl-Q")
    back = any(l.startswith(":") for l in h.lines())
    R.row("F1-ctl2 Ctrl-Q ended the page: the TCL prompt is back", back, "screen: %r" % [l[:60] for l in h.lines() if l.strip()][-3:])
    m = mark(h)
    send(h, "tool.keys\r", idle=1.5, label="tool.keys (second open)")
    waitfor(h, 2.0)
    frame_row("F1a", "tool.keys, second open in the same session", h, m, "tool.keys", "[Keys]", first)
    send(h, CTRL_Q, idle=1.5, label="Ctrl-Q")
    m = mark(h)
    send(h, "tool.files\r", idle=1.5, label="tool.files (after tool.keys)")
    waitfor(h, 2.5)
    frame_row("F1b", "tool.files after tool.keys in the same session", h, m, "tool.files", "[Files]", first)
    send(h, CTRL_Q, idle=1.5, label="Ctrl-Q")
    m = mark(h)
    send(h, "tool.keys\r", idle=1.5, label="tool.keys (after tool.files)")
    waitfor(h, 2.0)
    frame_row("F1c", "tool.keys after tool.files in the same session", h, m, "tool.keys", "[Keys]", first)
    send(h, CTRL_Q, idle=1.5, label="Ctrl-Q")
    h.end()
    h = open_h(account=HD)
    m = mark(h)
    send(h, "tool.files\r", idle=1.5, label="tool.files (first open in a fresh session)")
    waitfor(h, 2.5)
    frame_row("F1-ctl3", "tool.files, first open in a fresh session", h, m, "tool.files", "[Files]", None)
    send(h, CTRL_Q, idle=1.5, label="Ctrl-Q")
    h.end()


# ---------------------------------------------------------------------------------------------------------------------------------------- S3: AUTOLOGOUT (slow)

def listu_pids():
    out = g.adm(["LISTU"])
    pids = set()
    for ln in out:
        m = re.match(r"^\*?\s*(\d+)\s+(\d+)\s", ln)
        if m:
            pids.add(int(m.group(2)))
    return pids


def section_autologout():
    say("\n--- S3: AUTOLOGOUT 1 (minute) while a screen library app waits for a key (three sessions idle together, about 80 seconds)")
    a = open_h(account=HD)       # control: at the TCL prompt with AUTOLOGOUT 1 - must end
    b = open_h(account=HD)       # the fault: in tool.keys with AUTOLOGOUT 1
    c = open_h(account=HD)       # control: in tool.keys with no AUTOLOGOUT - must still be alive
    send(a, "AUTOLOGOUT 1\r", idle=1.0, label="a: AUTOLOGOUT 1")
    send(b, "AUTOLOGOUT 1\r", idle=1.0, label="b: AUTOLOGOUT 1")
    send(b, "tool.keys\r", idle=1.5, label="b: tool.keys")
    send(c, "tool.keys\r", idle=1.5, label="c: tool.keys (no AUTOLOGOUT)")
    t0 = time.time()
    before = listu_pids()
    pids = {"a": a.s.pid, "b": b.s.pid, "c": c.s.pid}
    seen = all(p in before for p in pids.values())
    say("  sessions: pids %r; the user table (LISTU) before: %r; all three listed: %s" % (pids, sorted(before), seen))
    R.row("S3-ctl0 the user table lists all three sessions before the idle wait (the instrument sees them)", seen, "pids %r in the table %r" % (pids, sorted(before)))
    end = t0 + 80.0
    while time.time() < end:
        for hh in (a, b, c):
            hh.s._pump(0.2)
    after = listu_pids()
    say("  after %.0f s: exited a=%s b=%s c=%s; the user table now: %r" % (time.time() - t0, a.s.exited, b.s.exited, c.s.exited, sorted(after)))
    R.row("S3-ctl1 AUTOLOGOUT 1 ended the session idle at the TCL prompt within 80 seconds (process ended: %s, in the user table: %s)" % (a.s.exited, pids["a"] in after), a.s.exited and (not seen or pids["a"] not in after), "exited=%s" % a.s.exited)
    R.row("S3-ctl2 with no AUTOLOGOUT the session in tool.keys is still alive and still in the user table", (not c.s.exited) and (not seen or pids["c"] in after), "exited=%s in table=%s" % (c.s.exited, pids["c"] in after))
    R.row("S3 AUTOLOGOUT 1 ended the session idle in tool.keys within 80 seconds (process ended: %s, in the user table: %s)" % (b.s.exited, pids["b"] in after), b.s.exited and (not seen or pids["b"] not in after),
          "the session is still alive after %.0f s of idling (exited=%s, in the user table=%s)" % (time.time() - t0, b.s.exited, pids["b"] in after), phase=2 if a.s.exited else None)
    for hh in (b, c):
        if not hh.s.exited:
            hh.s.type(CTRL_Q, idle=1.0)
    for hh in (a, b, c):
        hh.end()


# ---------------------------------------------------------------------------------------------------------------------------------------- D4 and plan 2.5: the break key after an abort, and HOME after a refused command
# (28 Oct 26, S.88 phase 2, WRITTEN AND NOT RUN: the owner ruled that no suite runs until all the phases are in.)
#
# THE INSTRUMENT.  A tiny INTERNAL program of the sandbox's own, $zzab, opens the toolkit's base like a page ($tk_open turns the break key off and takes the screen) and then reads an unassigned
# variable, which aborts the program with the screen open and the break key off - the state an abort inside a page, the IDE or CED leaves.  An ordinary account gets it as a verb through a VOC entry
# (V, CA, $zzab), as every tool.* page is given.  The break setting is READ AS THE PERSON WOULD, with PTERM DISPLAY at the prompt ("Break trapping: On|Off (char ^C)", message 6830/6831), after the abort:
# On is the person's own setting, restored; Off with the person having typed PTERM BREAK OFF first is the control that the fix puts back what the person had and does not turn the key on.
# THE NULL CASES.  Before any abort the setting is read (the control reaches the prompt and PTERM DISPLAY answers); the abort row shows the library was reached (the page's own sign that the program ran is
# the unassigned-variable message at the prompt, and the screen's top rows are the page's, not a shell's); SED is shown to have started (its menu bar) before it is left.

ZZAB = """$internal
program $zzab
$catalog $zzab

   call $tk_open('zzab', '', ctx, err)
   if err # '' then
      crt err
      stop
   end
   crt zzunset
   call $tk_close(ctx)
end
"""

ZZVE = """   open 'VOC' to v else crt 'ZVE novoc' ; stop
   write 'V':@fm:'CA':@fm:'$zzab' on v, 'zzab'
   write 'V':@fm:'CA':@fm:'$zzab' on v, 'tool.keys'
   crt 'ZVE done'
end
"""


def break_state(h):
    """what the person would read at the prompt: 'On', 'Off' or None (PTERM DISPLAY's own line)"""
    send(h, "pterm display\r", idle=1.3, label="PTERM DISPLAY")
    m = re.findall(r"Break trapping: (On|Off)", h.text())
    return m[-1] if m else None


def section_break():
    say("\n--- D4: the break key after an abort inside a toolkit app, after SED, and HOME after a refused command (account %s)" % BK)
    g.put(os.path.join(sh.SYS, "gpl.bp", "zzab"), ZZAB)
    out = adm("BASIC gpl.bp zzab")
    R.row("D4-ctl0 the throw-away internal program $zzab compiled in the sandbox", any(re.match(r"^Compiled 1 program\(s\) with no errors", l) for l in out), "\n".join(out[-6:]))
    compile_progs(BK, {"zzve": ZZVE})
    out = g.plain(BK, ["RUN bp zzve"])
    R.row("D4-ctl0b the verbs zzab and tool.keys (the latter pointing at $zzab) are in %s's VOC" % BK, any("ZVE done" in l for l in out), "\n".join(out[-4:]))

    h = open_h(account=BK)
    b0 = break_state(h)
    R.row("D4-ctl1 before anything runs the person's break setting is On (PTERM DISPLAY answered: %r)" % b0, b0 == "On", "PTERM DISPLAY said %r; screen %r" % (b0, h.text()[-200:]))
    send(h, "zzab\r", idle=3.5, label="zzab (opens the base, then aborts)")
    T = h.text()
    aborted = ("nassigned" in T or "Unassigned" in T)
    R.row("D4-ctl2 $zzab ran and aborted (the unassigned-variable message is on the screen) and the TCL prompt is back", aborted and any(l.startswith(":") for l in h.lines()), "screen tail %r" % [l[:80] for l in h.lines() if l.strip()][-4:])
    b1 = break_state(h)
    R.row("D4a after an abort inside a toolkit app (screen open, break key off) the break setting is On again at the prompt (PTERM DISPLAY: %r)" % b1, b1 == "On", "PTERM DISPLAY said %r" % b1, phase=2 if aborted else None)

    send(h, "pterm break off\r", idle=1.0, label="PTERM BREAK OFF (the person's own choice)")
    b2 = break_state(h)
    R.row("D4-ctl3 PTERM BREAK OFF took: the setting reads Off", b2 == "Off", "PTERM DISPLAY said %r" % b2)
    send(h, "zzab\r", idle=3.5, label="zzab again")
    b3 = break_state(h)
    R.row("D4b ...and after the same abort the person's own Off is what is given back (the fix restores what the person had; it does not force the key on)", b3 == "Off", "PTERM DISPLAY said %r" % b3, phase=2 if aborted else None)
    send(h, "pterm break on\r", idle=1.0, label="PTERM BREAK ON")

    # SED: it turns the break key off with PTERM BREAK OFF and gave nothing back (reset.term.state)
    send(h, "sed voc zzab\r", idle=3.0, label="SED on the VOC record zzab")
    started = "File" in h.line(0) or "Edit" in h.line(0)
    R.row("D4-ctl4 SED started on the record (its menu bar is on row 0)", started, "row 0 %r" % h.line(0)[:100])
    send(h, CTRL_Q, idle=1.5, label="Ctrl-Q")
    if until(h, lambda t: "uit without saving" in t, 1.0):
        send(h, "y", idle=1.2, label="y")
    waitfor(h, 1.0)
    b4 = break_state(h)
    R.row("D4c after SED the break setting is On again at the prompt (PTERM DISPLAY: %r)" % b4, b4 == "On", "PTERM DISPLAY said %r" % b4, phase=2 if started else None)
    h.end()

    # HOME: a tile whose command is refused no longer ends HOME (plan 2.5).  The tile Keys runs tool.keys, which is $zzab in this account: it aborts.
    h = open_h(account=BK)
    send(h, "home\r", idle=3.0, label="home")
    up = h.home()
    R.row("D4-ctl5 HOME is on the screen (Everyone, Terminal and Sign out)", up, "screen %r" % [l[:80] for l in h.lines() if l.strip()][:4])
    if up:
        send(h, "k", idle=0.8, label="k (jumps to Keys)")
        send(h, RET, idle=3.5, label="Enter (starts the tile: tool.keys -> $zzab, which aborts)")
        waitfor(h, 1.5)
        # 28 Oct 26, TUI phase 2 review (a): an aborted command waits for a key before the page is drawn again, so that the abort message is read (written, not run)
        held = (not h.home()) and any("Press Enter to return" in l for l in h.lines())
        R.row("D4d0 the abort message is not drawn over: the screen waits for Enter (\"Press Enter to return\") and is not the home screen yet", held, "screen %r" % [l[:80] for l in h.lines() if l.strip()][-4:], phase=2)
        if held:
            send(h, RET, idle=3.0, label="Enter (the page is drawn again)")
            waitfor(h, 1.5)
        back = h.home()
        R.row("D4d the aborted tile command did not end HOME: the home screen is on the screen again, not the TCL prompt", back, "screen %r" % [l[:80] for l in h.lines() if l.strip()][-4:], phase=2)
        if back:
            send(h, "\x1b[B", idle=0.5, label="Down (the page answers keys: HOME is alive)")
    h.end()
    h = open_h(account=BK)
    b5 = break_state(h)
    R.row("D4-ctl6 a new session of the account reads On (the setting is per session: the rows above do not carry into it)", b5 == "On", "PTERM DISPLAY said %r" % b5)
    h.end()


# ---------------------------------------------------------------------------------------------------------------------------------------- main

def main():
    say("sandbox-termsafe: S.88 Phase 0 - terminal safety, data safety, set / focus / frame.  strict=%s slow=%s SDBOX_KEYSET=%s" % (
        "--strict" in sys.argv, SLOW, os.environ.get("SDBOX_KEYSET", "(unset)")))
    try:
        sh.setup("sandbox-termsafe.py")
        if sh.tkb.failed:
            bail("the sandbox setup did not pass its own row")
        for a, spec in ((ZT, ("yes", "yes", "yes")), (Q1, ("yes", "yes", "yes")), (Q2, ("yes", "yes", "yes")), (TV, ("yes", "yes", "yes")), (BK, ("yes", "yes", "yes"))):
            make_account(a, *spec)
        for fn in (section_widgets, section_pages, section_sessions, section_query, section_vocall, section_break, section_memo, section_set, section_focus, section_frame):
            try:
                fn()
            except SystemExit:
                raise
            except Exception as e:                                   # a harness fault must show up as a failed row, not hide the rows after it
                import traceback
                traceback.print_exc()
                R.row("%s ran to the end" % fn.__name__, False, "exception %r" % (e,))
        if SLOW:
            try:
                section_autologout()
            except SystemExit:
                raise
            except Exception as e:
                import traceback
                traceback.print_exc()
                R.row("section_autologout ran to the end", False, "exception %r" % (e,))
        else:
            SKIPPED.append("S3 AUTOLOGOUT (run with --slow, about 3 minutes)")
    finally:
        sh.teardown()
    for s in SKIPPED:
        say("  [SKIP] %s - not counted as a pass" % s)
    sys.exit(R.finish())


if __name__ == "__main__":
    main()
