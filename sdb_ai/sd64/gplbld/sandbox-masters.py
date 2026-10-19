#!/usr/bin/env python3
#
# sandbox-masters.py - S.67 stage 1, the master files: the file-change hook, the journal, voc_master / dict_master / master_state and the
#                      verbs SYNC.MASTERS, CHECK.MASTERS and LIST.MASTER.PENDING (account to master only), through ORDINARY sessions on a
#                      private SD.  No install, no sudo.
#
#   SDBOX_KEYSET=3 python3 /home/don/Projects/SDCore4Linux-wt-s67/sdb_ai/sd64/gplbld/sandbox-masters.py <dir> [--build] [--sections=a,b]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or absent); without it
# <dir> must already be built.  Exit 0 every row passed, 1 a row failed, 2 it could not run.  Sections: setup, hook, drain, race, txn, fail, check,
# gate, life, keys, perf, upgrade.  Only one private SD can exist per keyset (SDBOX_KEYSET, shared memory keys 0x53434c91/92 + 0x20 per keyset):
# stop it afterwards with sandbox-fromtree.py <dir> stop.
#
# START-HISTORY:
# 19 Oct 26 dm  New (S.67 stage 1).  Written BEFORE the code, from the design in .claude/plan-net-gates-masters-shared-replication.md section 6,
#               and run red on the unchanged tree first (the numbers are in PROJECT_STATUS).
# END-HISTORY
#
# WHAT IT CAN AND CANNOT SHOW.  The sandbox has ONE operating-system user, so it cannot show who OWNS the journal or the master files, or that
# another user cannot read them; it shows their MODES (0620, 0660, 0770), which the code sets.  Ownership and group are the witness's
# (stage 2).  An administrator session is `sd` with SDTEST_ADMIN=1 (sandbox-gates.py's way); every other session is ordinary.  The EVIDENCE of
# a hook event is the journal FILE, read from here; the evidence of a master copy is read by an administrator program (zmtool) that opens the
# masters BY NAME, which is itself the drain trigger - so the rows that look at the journal always look BEFORE anything opens a master.
#
# THE FIXTURE ACCOUNTS (sandbox-gates.py's builder; their register records carry voc.edit, bp.edit and dict.edit = yes so that their own
# sessions may write the VOC and dictionaries):  zmone, zmtwo - ordinary;  zmos - sh and os.execute on, so that its VOC may hold an
# F-pointer at another account's directory;  zmnew - built late, to stand for an account CREATE.ACCOUNT has just made.

import importlib.util
import os
import re
import shutil
import stat
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
spec = importlib.util.spec_from_file_location("sandbox_gates", os.path.join(HERE, "sandbox-gates.py"))
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
passed = failed = 0
SECTIONS = ["setup", "hook", "drain", "race", "txn", "fail", "check", "gate", "life", "keys", "perf", "upgrade"]


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
    say("sandbox-masters: CANNOT RUN - " + msg)
    sys.exit(2)


# ---- the files ----------------------------------------------------------------------------------------------------------------------------

def J():
    return os.path.join(g.SYS, "$master.journal")


def acct_path(name):
    return os.path.join(g.BOX, "user_accounts", name)


def jtext():
    """The whole journal as text, or None when there is no journal file."""
    try:
        with open(J(), "rb") as f:
            return f.read().decode("latin-1")
    except OSError:
        return None


def jsize():
    try:
        return os.path.getsize(J())
    except OSError:
        return None


def jtail(off):
    """What the journal holds after byte OFF (None when there is no journal or OFF is None)."""
    t = jtext()
    if t is None or off is None:
        return None
    return t[off:]


def pdecode(s):
    return re.sub(r"%([0-9A-Fa-f]{2})", lambda m: chr(int(m.group(1), 16)), s)


EV = re.compile(r"^(\d{9,12}) ([vd]) ([wdcnx]) (\S+) (\S+) (\S+)$")


def evs(text):
    """Journal text -> list of (kind, op, account, file, id) with the id decoded; a line that is not a journal line is ('?', line)."""
    out = []
    for ln in (text or "").splitlines():
        m = EV.match(ln)
        if m:
            out.append((m.group(2), m.group(3), m.group(4), m.group(5), pdecode(m.group(6))))
        else:
            out.append(("?", ln))
    return out


def mode_of(path):
    try:
        return stat.S_IMODE(os.stat(path).st_mode)
    except OSError:
        return None


def msg(n, *args):
    p = os.path.join(g.SYS, "messages", str(n))
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8", errors="replace") as f:
        t = f.read().strip("\n")
    for i, a in enumerate(args, 1):
        t = t.replace("%%%d" % i, str(a))
    return t


def msg_rx(n, *fixed):
    """A regular expression for message N.  FIXED gives the text of %1, %2 ... where it is known (None: anything); the other places match anything."""
    t = msg(n)
    if t is None:
        return r"\A\Z-no-such-message-%d" % n
    parts = re.split(r"(%\d)", t)
    rx = ""
    for p in parts:
        m = re.fullmatch(r"%(\d)", p)
        if m:
            i = int(m.group(1)) - 1
            rx += re.escape(str(fixed[i])) if i < len(fixed) and fixed[i] is not None else "(.*)"
        else:
            rx += re.escape(p).replace(r"\ ", " ")
    return rx


def has_msg(out, n, *fixed):
    rx = msg_rx(n, *fixed)
    return any(re.search(rx, ln) for ln in out)


def squash(s):
    return re.sub(r"\s+", "", s)


def has_text(out, text):
    return any(text in ln for ln in out) or (len(squash(text)) > 12 and squash(text) in squash("".join(out)))


# ---- the probes ---------------------------------------------------------------------------------------------------------------------------
# ZMW is an ORDINARY program (the kernel's own tests and the hook are what are under test), compiled in each fixture account's bp.  Lines of
# zm.args:  kind|file|id|value   value: fields separated by ~.   VW write VOC, VV writev VOC, VM matwrite VOC, VD delete VOC, DW write a dictionary
# record, DV writev, DM matwrite, DD delete, DC clearfile the dictionary.  It prints  ZW kind file id OK|REFUSED|NOOPEN.

ZMW = """\
* zmw - ordinary changes to the VOC and to dictionaries (sandbox-masters.py)
   dim m(2)
   openseq 'zm.args' to a else crt 'ZW noargs' ; stop
   loop
      readseq line from a else exit
      kind = field(line, '|', 1) ; nm = field(line, '|', 2) ; id = field(line, '|', 3) ; val = convert('~', @fm, field(line, '|', 4))
      ok = 1
      begin case
         case kind[1,1] = 'V'
            open 'voc' to f else ok = -1
         case kind[1,1] = 'D'
            open 'DICT', nm to f else ok = -1
         case 1
            ok = -1
      end case
      if ok = 1 then
         begin case
            case kind = 'VW' or kind = 'DW'
               write val to f, id on error ok = 0
            case kind = 'VV' or kind = 'DV'
               writev val to f, id, 2 on error ok = 0
            case kind = 'VM' or kind = 'DM'
               mat m = val
               matwrite m to f, id on error ok = 0
            case kind = 'VD' or kind = 'DD'
               delete f, id on error ok = 0
            case kind = 'DC'
               clearfile f on error ok = 0
         end case
         close f
      end
      w = 'OK'
      if ok = 0 then w = 'REFUSED'
      if ok = -1 then w = 'NOOPEN'
      crt 'ZW ':kind:' ':nm:' ':id:' ':w
   repeat
   closeseq a
   crt 'ZW end'
end
"""

# ZMTX: a transaction around a VOC write, saying how big the journal is before it, inside it and after it.  Line: C|id (commit) or R|id (rollback).
ZMTX = """\
* zmtx - a VOC write inside a transaction and the size of the journal around it (sandbox-masters.py)
   openseq 'zm.args' to a else crt 'ZX noargs' ; stop
   readseq line from a else crt 'ZX empty' ; stop
   closeseq a
   mode = field(line, '|', 1) ; id = field(line, '|', 2)
   open 'voc' to f else crt 'ZX noopen' ; stop
   call !zmjsize(n0)
   n1 = 0
   begin transaction
      readu x from f, id else null
      write 'X':@fm:'inside a transaction' to f, id
      call !zmjsize(n1)
      if mode = 'C' then commit else rollback
   end transaction
   call !zmjsize(n2)
   read x from f, id then h = 1 else h = 0
   crt 'ZX ':mode:' before=':n0:' during=':n1:' after=':n2:' present=':h
end
"""

# ZMLOOP: N VOC writes in a loop, timed.  Line: id.prefix|count
ZMLOOP = """\
* zmloop - N record writes to the VOC (or to a data file), timed (sandbox-masters.py).  Line: prefix|n|voc or data
   openseq 'zm.args' to a else crt 'ZL noargs' ; stop
   readseq line from a else crt 'ZL empty' ; stop
   closeseq a
   pre = field(line, '|', 1) ; n = field(line, '|', 2) ; target = field(line, '|', 3)
   if target = 'data' then
      open 'zmdata' to f else crt 'ZL noopen' ; stop
   end else
      open 'voc' to f else crt 'ZL noopen' ; stop
   end
   t0 = system(1081)
   for i = 1 to n
      write 'X':@fm:'loop ':i to f, pre:i
   next i
   t1 = system(1081)
   crt 'ZL wrote ':n:' ms=':(t1 - t0)
end
"""

# ZMCHURN: K x R DISTINCT records written to the dictionary of the file zmrace, so that every journal line is the only one for its key: a line lost to the
# drain's emptying of the journal is a record missing from the master, which nothing later repairs.  Line: prefix|keys|rounds
ZMCHURN = """\
* zmchurn - K x R distinct dictionary records, each written once (sandbox-masters.py)
   openseq 'zm.args' to a else crt 'ZH noargs' ; stop
   readseq line from a else crt 'ZH empty' ; stop
   closeseq a
   pre = field(line, '|', 1) ; keys = field(line, '|', 2) ; rounds = field(line, '|', 3)
   open 'DICT', 'zmrace' to f else crt 'ZH noopen' ; stop
   for r = 1 to rounds
      for k = 1 to keys
         write 'D':@fm:r to f, pre:r:'.':k
      next k
   next r
   crt 'ZH done ':keys * rounds
end
"""

# ZMDRAIN: the administrator drains the journal over and over for N seconds (no session start between drains, so a drain meets the appenders about a
# thousand times a second).  Line: seconds
ZMDRAIN = """\
$internal
program zmdrain
$catalog $zmdrain
$include keys.h
$include int$keys.h
   openseq 'zm.args' to a else crt 'ZR noargs' ; stop
   readseq line from a else crt 'ZR empty' ; stop
   closeseq a
   secs = field(line, '|', 1) + 0
   t0 = system(1081)
   n = 0 ; lines = 0
   loop
      ans = kernel(K$MASTERS, 'drain')
      n += 1
      lines += ans<2>
   until system(1081) - t0 > secs * 1000 do
   repeat
   crt 'ZR drains=':n:' lines=':lines
end
"""

ORDINARY = {"zmw": ZMW, "zmtx": ZMTX, "zmloop": ZMLOOP, "zmchurn": ZMCHURN}

# The internal subroutine that tells an ordinary program how big the journal is.  -1 when there is none.
ZMJSIZE = """\
$internal
subroutine zmjsize(n)
$catalog !zmjsize
   n = -1
   openseq @sdsys:@ds:'$master.journal' to j then
      n = 0
      loop
         readseq line from j else exit
         n += len(line) + 1
      repeat
      closeseq j
   end
return
end
"""

# ZMTOOL: the administrator's instrument (it is also run by ordinary sessions, to show that it cannot do what it does for the administrator).
# Lines of zm.args:
#   CMP|acct|kind|file|id        the account's record against the master copy:  SAME DIFF NOMASTER NOACCOUNT ABSENT
#   MGET|kind|key                the master copy of a key (kind v or d), fields shown with |, or ABSENT
#   MPUT|kind|key|value          write a master record directly (a planted difference)
#   MDEL|kind|key                delete one
#   SGET|key                     a master_state record
#   VOCHAS|acct|id               is that record in the account's VOC (read by path)
#   CNT|acct|kind|file           how many records the account's file holds and how many master keys name it
#   OPENV|key                    open voc_master BY NAME and read a key (the drain trigger)
#   OPENP|key                    the same by OPENPATH
#   OPENS|key                    master_state, by name
#   FI                           FILEINFO of the three masters: type, nocase
#   REN|old|new                  OSREN of two paths (an administrator-only way to move a dictionary)
#   MKD|path                     make an account's empty directory (for the OSPATH delete row)
#   KEYS|kind|acct               the master keys that begin  acct*  (the count and the first few)
ZMTOOL = """\
$internal
program zmtool
$catalog $zmtool
$include keys.h
$include int$keys.h
   mf = '' ; ar = '' ; mr = ''
   openseq 'zm.args' to a else crt 'ZT noargs' ; stop
   loop
      readseq line from a else exit
      cmd = field(line, '|', 1)
      begin case
         case cmd = 'CMP' ; gosub cmp
         case cmd = 'MGET' ; gosub mget
         case cmd = 'MPUT' ; gosub mput
         case cmd = 'MDEL' ; gosub mdel
         case cmd = 'SGET' ; gosub sget
         case cmd = 'VOCHAS' ; gosub vochas
         case cmd = 'CNT' ; gosub cnt
         case cmd = 'OPENV' ; gosub openv
         case cmd = 'OPENP' ; gosub openp
         case cmd = 'OPENS' ; gosub opens
         case cmd = 'FI' ; gosub fi
         case cmd = 'REN' ; gosub ren
         case cmd = 'MKD' ; gosub mkd
         case cmd = 'KEYS' ; gosub keys
         case 1 ; crt 'ZT unknown ':cmd
      end case
   repeat
   closeseq a
   crt 'ZT end'
   stop

acct.root:
   root = ''
   openpath @sdsys:@ds:'accounts' to accf then
      read arec from accf, acct then root = arec<1>
      close accf
   end
   return

cmp:
   acct = field(line, '|', 2) ; kind = field(line, '|', 3) ; file = field(line, '|', 4) ; id = field(line, '|', 5)
   gosub acct.root
   ahave = 0 ; mhave = 0 ; ar = '' ; mr = ''
   if kind = 'v' then
      apath = root:@ds:'voc' ; mname = 'voc_master' ; key = acct:'*':id
   end else
      apath = root:@ds:file:'.dic' ; mname = 'dict_master' ; key = acct:'*':file:'*':id
   end
   openpath apath to af then
      read ar from af, id then ahave = 1 else ar = ''
      close af
   end
   open mname to mf then
      read mr from mf, key then mhave = 1 else mr = ''
      close mf
   end else
      crt 'ZT CMP master-not-open ':mname
   end
   begin case
      case ahave and mhave ; res = (if ar = mr then 'SAME' else 'DIFF')
      case ahave ; res = 'NOMASTER'
      case mhave ; res = 'NOACCOUNT'
      case 1 ; res = 'ABSENT'
   end case
   crt 'ZT CMP ':acct:' ':kind:' ':file:' ':id:' ':res
   return

mget:
   kind = field(line, '|', 2) ; key = field(line, '|', 3)
   mname = (if kind = 'v' then 'voc_master' else 'dict_master')
   open mname to mf then
      read mr from mf, key then crt 'ZT MGET ':kind:' ':key:' = ':convert(@fm, '|', mr) else crt 'ZT MGET ':kind:' ':key:' ABSENT'
      close mf
   end else crt 'ZT MGET ':kind:' ':key:' NOOPEN'
   return

mput:
   kind = field(line, '|', 2) ; key = field(line, '|', 3) ; val = convert('~', @fm, field(line, '|', 4))
   mname = (if kind = 'v' then 'voc_master' else 'dict_master')
   open mname to mf then
      write val to mf, key
      close mf
      crt 'ZT MPUT ':kind:' ':key:' done'
   end else crt 'ZT MPUT ':kind:' ':key:' NOOPEN'
   return

mdel:
   kind = field(line, '|', 2) ; key = field(line, '|', 3)
   mname = (if kind = 'v' then 'voc_master' else 'dict_master')
   open mname to mf then
      delete mf, key
      close mf
      crt 'ZT MDEL ':kind:' ':key:' done'
   end else crt 'ZT MDEL ':kind:' ':key:' NOOPEN'
   return

sget:
   key = field(line, '|', 2)
   open 'master_state' to sf then
      read mr from sf, key then crt 'ZT SGET ':key:' = ':convert(@fm, '|', mr) else crt 'ZT SGET ':key:' ABSENT'
      close sf
   end else crt 'ZT SGET ':key:' NOOPEN'
   return

vochas:
   acct = field(line, '|', 2) ; id = field(line, '|', 3)
   gosub acct.root
   openpath root:@ds:'voc' to af then
      read ar from af, id then crt 'ZT VOCHAS ':acct:' ':id:' PRESENT' else crt 'ZT VOCHAS ':acct:' ':id:' ABSENT'
      close af
   end else crt 'ZT VOCHAS ':acct:' ':id:' NOVOC'
   return

cnt:
   acct = field(line, '|', 2) ; kind = field(line, '|', 3) ; file = field(line, '|', 4)
   gosub acct.root
   an = 0 ; mn = 0
   if kind = 'v' then
      apath = root:@ds:'voc' ; mname = 'voc_master' ; pre = acct:'*'
   end else
      apath = root:@ds:file:'.dic' ; mname = 'dict_master' ; pre = acct:'*':file:'*'
   end
   openpath apath to af then
      select af to 9
      loop
         readnext id from 9 else exit
         an += 1
      repeat
      close af
   end
   open mname to mf then
      select mf to 9
      loop
         readnext id from 9 else exit
         if id[1, len(pre)] = pre then mn += 1
      repeat
      close mf
   end
   crt 'ZT CNT ':acct:' ':kind:' ':file:' account=':an:' master=':mn
   return

openv:
   key = field(line, '|', 2)
   open 'voc_master' to mf then
      read mr from mf, key then crt 'ZT OPENV found ':convert(@fm, '|', mr) else crt 'ZT OPENV absent'
      close mf
   end else crt 'ZT OPENV noopen'
   return

openp:
   key = field(line, '|', 2)
   openpath @sdsys:@ds:'voc_master' to mf then
      read mr from mf, key then crt 'ZT OPENP found ':convert(@fm, '|', mr) else crt 'ZT OPENP absent'
      close mf
   end else crt 'ZT OPENP noopen status=':status()
   return

opens:
   key = field(line, '|', 2)
   open 'master_state' to mf then
      read mr from mf, key then crt 'ZT OPENS found ':convert(@fm, '|', mr) else crt 'ZT OPENS absent'
      close mf
   end else crt 'ZT OPENS noopen'
   return

fi:
   for each nm in 'voc_master':@fm:'dict_master':@fm:'master_state'
      open nm to mf then
         crt 'ZT FI ':nm:' type=':fileinfo(mf, FL$TYPE):' nocase=':fileinfo(mf, FL$NOCASE)
         close mf
      end else crt 'ZT FI ':nm:' noopen'
   next nm
   return

ren:
   if osrename(field(line, '|', 2), field(line, '|', 3)) then crt 'ZT REN done' else crt 'ZT REN failed ':status()
   return

mkd:
   if ospath(field(line, '|', 2), 13) then crt 'ZT MKD done' else crt 'ZT MKD failed ':status()
   return

keys:
   kind = field(line, '|', 2) ; acct = field(line, '|', 3)
   mname = (if kind = 'v' then 'voc_master' else 'dict_master')
   n = 0 ; first = ''
   open mname to mf then
      select mf to 9
      loop
         readnext id from 9 else exit
         if id[1, len(acct) + 1] = acct:'*' then
            n += 1
            if n <= 3 then first<-1> = id
         end
      repeat
      close mf
   end
   crt 'ZT KEYS ':kind:' ':acct:' n=':n:' first=':convert(@fm, ',', first)
   return
end
"""

# ZMKOP: kernel(K$MASTERS) from the session it is run in.  Lines: op|arg.  Prints the answer's fields with |.
ZMKOP = """\
$internal
program zmkop
$catalog $zmkop
$include keys.h
$include int$keys.h
   openseq 'zm.args' to a else crt 'ZK noargs' ; stop
   loop
      readseq line from a else exit
      op = field(line, '|', 1) ; arg = field(line, '|', 2)
      req = op
      if arg # '' then req = op:@fm:arg
      ans = kernel(K$MASTERS, req)
      crt 'ZK ':op:' ':arg:' -> ':convert(@vm, '~', convert(@fm, '|', ans))
   repeat
   closeseq a
   crt 'ZK end'
end
"""

INTERNALS = {"zmtool": ZMTOOL, "zmkop": ZMKOP, "zmdrain": ZMDRAIN}


# ---- running things -----------------------------------------------------------------------------------------------------------------------

def args(path_dir, lines):
    g.put(os.path.join(path_dir, "zm.args"), "\n".join(lines) + "\n")


def zw(acct, lines):
    """An ordinary session in ACCT changes the VOC / dictionaries as LINES say.  Returns {(kind, file, id): word}."""
    args(acct_path(acct), lines)
    out = g.plain(acct, ["RUN bp zmw"])
    d = {}
    for ln in out:
        m = re.match(r"^ZW (\S+) (\S+) (\S+) (OK|REFUSED|NOOPEN)$", ln)
        if m:
            d[(m.group(1), m.group(2), m.group(3))] = m.group(4)
    return d, out


def tool(lines, admin=True, acct=None):
    """ZMTOOL, run as the administrator in the SDSYS account (or as an ordinary session in ACCT).  Returns the output lines."""
    if acct is None:
        args(g.SYS, lines)
        return g.sd(g.SYS, ["ZMTOOL"], admin=admin)
    args(acct_path(acct), lines)
    return g.sd(acct_path(acct), ["ZMTOOL"], admin=admin, account=acct)


def kop(lines, acct=None, admin=True):
    if acct is None:
        args(g.SYS, lines)
        return g.sd(g.SYS, ["ZMKOP"], admin=admin)
    args(acct_path(acct), lines)
    return g.sd(acct_path(acct), ["ZMKOP"], admin=admin, account=acct)


def adm(cmds):
    return g.adm(cmds)


def zt(out, what):
    """The ZT lines of one kind: ZT CMP ..., ZT MGET ..."""
    return [ln for ln in out if ln.startswith("ZT " + what + " ")]


def cmp_res(out, acct, kind, file, ident):
    """What zmtool's CMP said about one record.  None when it said nothing or could not open the master (so that ABSENT on a system with no master
    files cannot pass for 'the master does not have it')."""
    if any(ln.startswith("ZT CMP master-not-open") for ln in out):
        return None
    for ln in out:
        m = re.match(r"^ZT CMP (\S+) (\S+) (\S+) (.*) (SAME|DIFF|NOMASTER|NOACCOUNT|ABSENT)$", ln)
        if m and m.group(1) == acct and m.group(2) == kind and m.group(3) == file and m.group(4) == ident:
            return m.group(5)
    return None


def zk_status(out, op):
    """The first field of the answer to an op in ZMKOP's output (None when there is no such line)."""
    for ln in out:
        m = re.match(r"^ZK %s (.*?) -> (.*)$" % re.escape(op), ln)
        if m:
            return m.group(2).split("|")[0]
    return None


def snapshot(path):
    """Every file below PATH with its size, mtime and a hash of its content, for 'nothing was changed' rows."""
    import hashlib
    d = {}
    for dp, dn, fn in os.walk(path):
        for n in fn:
            p = os.path.join(dp, n)
            try:
                with open(p, "rb") as f:
                    h = hashlib.sha1(f.read()).hexdigest()
                d[os.path.relpath(p, path)] = (os.path.getsize(p), h)
            except OSError:
                d[os.path.relpath(p, path)] = None
    return d


MASTERS = ["voc_master", "dict_master", "master_state"]


def masters_snapshot():
    snap = {}
    for m in MASTERS:
        p = os.path.join(g.SYS, m)
        if os.path.isdir(p):
            snap[m] = snapshot(p)
    return snap


def ed_lines():
    return ["I", "hello", "", "FI", "Q", "Y"]


# ---- preparation --------------------------------------------------------------------------------------------------------------------------

ACCOUNTS = ["zmone", "zmtwo", "zmos"]


def reset_masters():
    """Put the sandbox back to a system with no master files (a run on a sandbox that an earlier run used): the journal, the three master files and
    their dictionaries are removed from the disk.  Their F entries in the SDSYS VOC are taken out by zmfix, below.  On a freshly built sandbox this
    removes nothing."""
    removed = []
    for n in ["$master.journal", "$master.journal.saved", "$master.journal.away", "accounts/zmnew"] + MASTERS + [m + ".dic" for m in MASTERS]:
        p = os.path.join(g.SYS, n)
        if os.path.isdir(p):
            shutil.rmtree(p)
            removed.append(n)
        elif os.path.lexists(p):
            os.remove(p)
            removed.append(n)
    say("  [reset] %s" % (", ".join(removed) if removed else "nothing to remove: a fresh sandbox"))


def prepare_all():
    reset_masters()
    g.FIXTURES["zmone"] = ("no", "no")
    g.FIXTURES["zmtwo"] = ("no", "no")
    g.FIXTURES["zmos"] = ("yes", "yes")
    g.FIXTURES["zmnew"] = ("no", "no")
    g.prepare()
    for nm, src in INTERNALS.items():
        g.put(os.path.join(g.SYS, "gpl.bp", nm), src)
    g.put(os.path.join(g.SYS, "gpl.bp", "zmjsize"), ZMJSIZE)
    out = g.adm(["BASIC gpl.bp zmjsize zmtool"], internal=True)
    ok = g.has(out, r"^Compiled 2 program\(s\) with no errors")
    row("the probes !zmjsize and zmtool compile", ok, repr(out[-6:]))
    out2 = g.adm(["BASIC gpl.bp zmdrain"], internal=True)       # needs K$MASTERS, so on a tree without the key it compiles with a warning, like zmkop
    row("the probe zmdrain (kernel(K$MASTERS)) compiles with no warning", g.has(out2, r"^Compiled 1 program\(s\) with no errors") and not any("is not assigned a value" in ln for ln in out2), repr(out2[-4:]))
    if not ok:
        bail("the probes did not compile:\n" + "\n".join(out[-8:]))
    out = g.adm(["BASIC gpl.bp zmkop"], internal=True)
    row("the probe zmkop (kernel(K$MASTERS)) compiles with no warning - on a tree without the key the compiler says 'is not assigned a value' at 0 errors, which is the red state",
        g.has(out, r"^Compiled 1 program\(s\) with no errors") and not any("is not assigned a value" in ln for ln in out), repr(out[-4:]))
    for n in ACCOUNTS:
        g.build_account(n)
    # VOC verbs for the probes, in the SDSYS VOC and in each fixture VOC; the ordinary program in each account's bp
    lines = ["$internal", "   for each vp in '%s':@fm:%s" % (g.SYS, ":@fm:".join("'%s'" % acct_path(n) for n in ACCOUNTS + ["zmnew"])),
             "      if vp = '%s' then vv = vp:@ds:'voc' else vv = vp:@ds:'voc'" % g.SYS,
             "      openpath vv to v else continue",
             "      delete v, 'voc_master' ; delete v, 'dict_master' ; delete v, 'master_state'",    # from an earlier run; a no-op on a fresh sandbox
             "      write 'V':@fm:'CA':@fm:'$zmtool' to v, 'zmtool'",
             "      write 'V':@fm:'CA':@fm:'$zmkop' to v, 'zmkop'",
             "      write 'V':@fm:'CA':@fm:'$zmdrain' to v, 'zmdrain'",
             "      close v", "   next vp", "   crt 'ZMFIX done'", "end", ""]
    g.put(os.path.join(g.SYS, "bp", "zmfix"), "\n".join(lines))
    # zmnew does not exist yet: the loop skips it
    out = g.adm(["BASIC bp zmfix", "RUN bp zmfix"], internal=True)
    if not g.has(out, r"^ZMFIX done$"):
        bail("the VOC verbs were not written:\n" + "\n".join(out[-8:]))
    for n in ACCOUNTS:
        for pn, src in ORDINARY.items():
            g.put(os.path.join(acct_path(n), "bp", pn), src)
        out = g.sd(acct_path(n), ["BASIC bp " + " ".join(ORDINARY)], admin=True, account=n)
        if not g.has(out, r"^Compiled %d program\(s\) with no errors" % len(ORDINARY)):
            bail("the ordinary probes did not compile in %s:\n%s" % (n, "\n".join(out[-8:])))
    say("  [done] fixture accounts %s; probes zmw zmtx zmloop (ordinary) and zmtool zmkop !zmjsize (internal)" % " ".join(ACCOUNTS))


def controls():
    say("\n--- 0. controls: the sessions are ordinary, the instruments work ---------------------------------------------------------------")
    out = g.plain("zmone", ["ZZKF"])
    f = g.flags(out)
    row("0a: a plain session in zmone is not an administrator (admin=0)", f is not None and f[0] == "0", repr(f))
    if f is None or f[0] != "0":
        bail("the plain session is an administrator (or printed nothing): every row below would be meaningless")
    f = g.flags(g.sd(acct_path("zmone"), ["ZZKF"], admin=True, account="zmone"))
    row("0b: the same session with SDTEST_ADMIN=1 is an administrator (admin=1)", f is not None and f[0] == "1", repr(f))
    d, out = zw("zmone", ["VW|-|zm0|X~control"])
    row("0c: the ordinary probe zmw writes a VOC record and says OK (the instrument reaches the VOC)", d.get(("VW", "-", "zm0")) == "OK", repr(out[-4:]))
    out = tool(["VOCHAS|zmone|zm0"])
    row("0d: the administrator's tool sees that record by path (the instrument reads what is on the disk)",
        any(ln == "ZT VOCHAS zmone zm0 PRESENT" for ln in out), repr(out[-4:]))
    t = jtext()
    row("0e: before the master files are set up there is NO journal file, and a user's VOC write did not make one (the hook never creates it: "
        "a file made by a session would be owned by that user)", t is None, "journal exists, %r bytes" % (jsize(),))


# ---- A. setup ---------------------------------------------------------------------------------------------------------------------------

def setup_section():
    say("\n--- A. SYNC.MASTERS sets the master files up and mirrors every account -------------------------------------------------------------")
    out = adm(["SYNC.MASTERS"])
    row("A1: SYNC.MASTERS (no account) says the master files are set up (11565)", has_msg(out, 11565), repr(out[-8:]))
    for a in ["sdsys"] + ACCOUNTS:
        row("A2: it reports the account %s (11566)" % a, has_msg(out, 11566, a), repr(out[-12:]))
    t = jtext()
    row("A3: the journal file exists now", t is not None, "no journal")
    row("A3a: it is a regular file, mode exactly 0620 (owner read and write, group write only)",
        os.path.isfile(J()) and mode_of(J()) == 0o620, "mode %s" % (oct(mode_of(J())) if mode_of(J()) is not None else None))
    row("A3b: the SYNC left nothing waiting in the journal (everything it wrote was mirrored by the full sync, not by entries)",
        t is not None and not [e for e in evs(t) if e[0] == "?"], repr((t or "")[:200]))
    for m in MASTERS:
        p = os.path.join(g.SYS, m)
        row("A4: %s is a directory file with its subfiles %%0 and %%1" % m,
            os.path.isdir(p) and os.path.exists(os.path.join(p, "%0")) and os.path.exists(os.path.join(p, "%1")), "")
        row("A4a: %s has its directory at mode 0770 and its subfiles at 0660 (SDSYS and its group; no other SD user)" % m,
            mode_of(p) == 0o770 and mode_of(os.path.join(p, "%0")) == 0o660 and mode_of(os.path.join(p, "%1")) == 0o660,
            "%s %s %s" % (oct(mode_of(p) or 0), oct(mode_of(os.path.join(p, "%0")) or 0), oct(mode_of(os.path.join(p, "%1")) or 0)))
        row("A4b: %s.dic exists and is closed to other users in the same way" % m,
            os.path.isdir(p + ".dic") and mode_of(p + ".dic") == 0o770 and mode_of(os.path.join(p + ".dic", "%0")) == 0o660,
            "%s" % (oct(mode_of(p + ".dic") or 0),))
    out = tool(["FI"])
    for m in MASTERS:
        row("A5: %s is a hashed file (type 3) with case-insensitive ids" % m, any(ln == "ZT FI %s type=3 nocase=1" % m for ln in out), repr(zt(out, "FI")))
    # no VOC entry in another account names them
    for a in ACCOUNTS:
        o = tool(["VOCHAS|%s|voc_master" % a, "VOCHAS|%s|dict_master" % a, "VOCHAS|%s|master_state" % a])
        row("A6: the VOC of %s has no entry for any master file (and the master files exist, so the absence is not just that there is nothing)" % a,
            os.path.isdir(os.path.join(g.SYS, "voc_master")) and len(zt(o, "VOCHAS")) == 3 and all(ln.endswith("ABSENT") for ln in zt(o, "VOCHAS")), repr(zt(o, "VOCHAS")))
    o = tool(["VOCHAS|sdsys|voc_master", "VOCHAS|sdsys|dict_master", "VOCHAS|sdsys|master_state"])
    row("A6a: the SDSYS VOC has all three (it is how SDSYS opens them)", len(zt(o, "VOCHAS")) == 3 and all(ln.endswith("PRESENT") for ln in zt(o, "VOCHAS")), repr(zt(o, "VOCHAS")))
    # key forms and contents
    o = tool(["CMP|zmone|v|-|bp", "CMP|zmone|v|-|$command.stack", "CMP|zmtwo|v|-|bp", "CMP|sdsys|v|-|voc_master", "CMP|zmone|v|-|zm0"])
    row("A7: voc_master holds zmone*bp, zmone*$command.stack, zmtwo*bp, sdsys*voc_master, zmone*zm0 - each equal to the account's record",
        all(cmp_res(o, a, "v", "-", i) == "SAME" for a, i in (("zmone", "bp"), ("zmone", "$command.stack"), ("zmtwo", "bp"), ("sdsys", "voc_master"), ("zmone", "zm0"))),
        repr(zt(o, "CMP")))
    for a in ["sdsys"] + ACCOUNTS:
        o = tool(["CNT|%s|v|-" % a])
        m = re.search(r"account=(\d+) master=(\d+)", " ".join(zt(o, "CNT")))
        row("A8: voc_master holds exactly as many keys for %s as the account's VOC holds records (%s)" % (a, m.groups() if m else None),
            bool(m) and int(m.group(1)) > 100 and m.group(1) == m.group(2), repr(zt(o, "CNT")))
    o = tool(["CNT|sdsys|d|voc", "CNT|sdsys|d|accounts", "CMP|sdsys|d|voc|@id"])
    row("A9: dict_master holds the SDSYS dictionaries as dictionary-file-by-file keys sdsys*voc*<id> and sdsys*accounts*<id>, equal in number",
        all(re.search(r"account=(\d+) master=(\d+)", ln) and re.search(r"account=(\d+) master=(\d+)", ln).group(1) == re.search(r"account=(\d+) master=(\d+)", ln).group(2)
            and int(re.search(r"account=(\d+)", ln).group(1)) > 0 for ln in zt(o, "CNT")) and len(zt(o, "CNT")) == 2, repr(zt(o, "CNT")))
    o = tool(["SGET|v*zmone*bp", "SGET|$journal"])
    sg = zt(o, "SGET")
    row("A10: master_state holds v*zmone*bp (a 16-digit checksum, a time) and the journal's own position record $journal",
        len(sg) == 2 and re.search(r"= [0-9a-f]{16}\|\d+", sg[0]) is not None and "ABSENT" not in sg[1], repr(sg))


# ---- B. the hook, writer by writer --------------------------------------------------------------------------------------------------------

def one(label, off, expect, extra=None):
    """The journal since OFF holds exactly the events EXPECT (a set: the order of the pieces of one command is not a promise)."""
    t = jtail(off)
    got = evs(t)
    ok = t is not None and sorted(got) == sorted(expect)
    row(label, ok, "got %r, wanted %r" % (got, expect))
    return got


def hook_section():
    say("\n--- B. the file-change hook: one journal line (keys only) for each way a VOC or a dictionary is changed ---------------------------------")
    off = jsize()
    out = g.plain("zmone", ["WHO"])
    one("B0: a session that changes nothing adds nothing to the journal (sign-on and sign-off write no VOC record)", off, [])
    secret = "SECRET-DATA-9f3a1c"
    off = jsize()
    d, out = zw("zmone", ["VW|-|zmw1|X~" + secret])
    got = one("B1: WRITE to a VOC record: one line  v w zmone - zmw1", off, [("v", "w", "zmone", "-", "zmw1")])
    row("B1a: the line holds keys and NO data: the record's text is not in the journal (which does hold the line for the record)",
        jtext() is not None and "zmw1" in jtext() and secret not in jtext(), "")
    off = jsize()
    zw("zmone", ["VV|-|zmw2|X~a~" + secret + "2"])
    one("B2: WRITEV to a VOC record: one line", off, [("v", "w", "zmone", "-", "zmw2")])
    off = jsize()
    zw("zmone", ["VM|-|zmw3|X~m1~m2"])
    one("B3: MATWRITE to a VOC record: one line", off, [("v", "w", "zmone", "-", "zmw3")])
    off = jsize()
    zw("zmone", ["VD|-|zmw1|"])
    one("B4: DELETE of a VOC record: one line with op d", off, [("v", "d", "zmone", "-", "zmw1")])
    off = jsize()
    zw("zmone", ["VD|-|zmnosuch|"])
    one("B4a: DELETE of a record that is not there changes nothing and is not journalled", off, [])
    off = jsize()
    g.plain("zmone", ["ED VOC zmed1"] + ed_lines())
    got = evs(jtail(off))
    row("B5: ED saving a VOC record: a write line for zmed1 (and nothing for any other record)",
        ("v", "w", "zmone", "-", "zmed1") in got and all(e[:4] == ("v", "w", "zmone", "-") for e in got if e[0] != "?") and not any(e[0] == "?" for e in got), repr(got))
    off = jsize()
    g.plain("zmone", ["CREATE.FILE zmf1 DYNAMIC"])
    got = evs(jtail(off))
    row("B6: CREATE.FILE: the pointer in the VOC, the new dictionary, its @id record",
        set(got) >= {("v", "w", "zmone", "-", "zmf1"), ("d", "n", "zmone", "zmf1", "-"), ("d", "w", "zmone", "zmf1", "@id")} and not any(e[0] == "?" for e in got), repr(got))
    off = jsize()
    zw("zmone", ["DW|zmf1|F1|D~1~~Field one~10L~S", "DW|zmf1|IT1|I~1+1~~IT1~10R~S"])
    one("B7: WRITE to a dictionary record: one line per record, keyed by the file that holds the dictionary", off,
        [("d", "w", "zmone", "zmf1", "F1"), ("d", "w", "zmone", "zmf1", "IT1")])
    off = jsize()
    g.plain("zmone", ["CD zmf1 IT1"])
    got = evs(jtail(off))
    row("B8: CD compiling an I-type writes the object into the dictionary: a write line for IT1", ("d", "w", "zmone", "zmf1", "IT1") in got and not any(e[0] == "?" for e in got), repr(got))
    # a drain in the middle of the section: the dictionary is still there, so its records are in the master (B14 deletes the file)
    o = tool(["OPENV|zmone*bp", "CMP|zmone|d|zmf1|F1", "CMP|zmone|d|zmf1|IT1", "CMP|zmone|d|zmf1|@id"])
    row("B8a: (a drain, to look) the dictionary records the sections above wrote - F1, the compiled I-type IT1 and the default @id - are in the master and equal to the account's",
        all(cmp_res(o, "zmone", "d", "zmf1", i) == "SAME" for i in ("F1", "IT1", "@id")), repr(zt(o, "CMP")))
    off = jsize()
    g.plain("zmone", ["COPY FROM VOC TO VOC zmw3,zmcopy1"])
    one("B9: COPY into the VOC: one write line for the new record", off, [("v", "w", "zmone", "-", "zmcopy1")])
    off = jsize()
    zw("zmone", ["DV|zmf1|F1|D~2"])
    one("B10: WRITEV to a dictionary record: one line", off, [("d", "w", "zmone", "zmf1", "F1")])
    off = jsize()
    zw("zmone", ["DM|zmf1|F2|D~3~~m"])
    one("B10a: MATWRITE to a dictionary record: one line", off, [("d", "w", "zmone", "zmf1", "F2")])
    off = jsize()
    zw("zmone", ["DD|zmf1|F2|"])
    one("B11: DELETE of a dictionary record: one line with op d", off, [("d", "d", "zmone", "zmf1", "F2")])
    off = jsize()
    g.plain("zmone", ["CLEAR.FILE DICT zmf1"])
    got = evs(jtail(off))
    row("B12: CLEAR.FILE DICT: a clear line for the file (op c), then the @ID record it puts back",
        ("d", "c", "zmone", "zmf1", "-") in got and not any(e[0] == "?" for e in got), repr(got))
    off = jsize()
    g.plain("zmone", ["CNAME zmf1 TO zmf2"])
    got = evs(jtail(off))
    row("B13: CNAME of a data file: the pointer moves (a write for zmf2, a delete for zmf1); the dictionary keeps its name, so no dictionary event",
        ("v", "w", "zmone", "-", "zmf2") in got and ("v", "d", "zmone", "-", "zmf1") in got and not [e for e in got if e[0] == "d"], repr(got))
    off = jsize()
    g.plain("zmone", ["DELETE.FILE zmf2 NO.QUERY", "Y"])
    got = evs(jtail(off))
    row("B14: DELETE.FILE: the dictionary is removed (op x, file zmf1: it is the dictionary's own name) and the pointer deleted",
        ("d", "x", "zmone", "zmf1", "-") in got and ("v", "d", "zmone", "-", "zmf2") in got and not any(e[0] == "?" for e in got), repr(got))
    # the administrator and the account derived from the PATH
    off = jsize()
    g.put(os.path.join(g.SYS, "bp", "zmint"), "\n".join([
        "$internal", "   openpath '%s/voc' to v else crt 'ZI novoc' ; stop" % acct_path("zmtwo"),
        "   write 'X':@fm:'by the administrator' to v, 'zmint1'", "   close v", "   crt 'ZI done'", "end", ""]))
    o = g.adm(["BASIC bp zmint", "RUN bp zmint"], internal=True)
    one("B15: an INTERNAL program in the SDSYS account writing zmtwo's VOC by path: the line names zmtwo (the account is derived from the file's path, not from the session)",
        off, [("v", "w", "zmtwo", "-", "zmint1")])
    off = jsize()
    g.adm(["BASIC bp zmint"], internal=True)
    g.put(os.path.join(g.SYS, "bp", "zmsys"), "\n".join([
        "$internal", "   open 'voc' to v else crt 'ZI novoc' ; stop",
        "   write 'X':@fm:'sdsys own' to v, 'zmsys1'", "   close v", "   crt 'ZI done'", "end", ""]))
    g.adm(["BASIC bp zmsys", "RUN bp zmsys"], internal=True)
    one("B16: the SDSYS account's own VOC: a line for sdsys", off, [("v", "w", "sdsys", "-", "zmsys1")])
    # a dictionary physically in another account, reached through an F-pointer
    g.plain("zmone", ["CREATE.FILE zmf3 DYNAMIC"])
    g.put(os.path.join(g.SYS, "bp", "zmptr"), "\n".join([
        "$internal", "   openpath '%s/voc' to v else crt 'ZP novoc' ; stop" % acct_path("zmos"),
        "   write 'F':@fm:'%s/zmf3':@fm:'%s/zmf3.dic' to v, 'zmx'" % (acct_path("zmone"), acct_path("zmone")),
        "   close v", "   crt 'ZP done'", "end", ""]))
    g.adm(["BASIC bp zmptr", "RUN bp zmptr"], internal=True)
    off = jsize()
    d, out = zw("zmos", ["DW|zmx|P1|D~1"])
    one("B17: a dictionary held by zmone, written through an F-pointer from zmos: the line names zmone, the account whose directory holds the dictionary (D8) - and file zmf3",
        off, [("d", "w", "zmone", "zmf3", "P1")])
    # controls: files that are not VOCs or dictionaries
    g.plain("zmone", ["CREATE.FILE zmdata DYNAMIC", "CREATE.FILE zmdir DIRECTORY"])
    off = jsize()
    g.put(os.path.join(acct_path("zmone"), "zm.args"), "")
    g.put(os.path.join(g.SYS, "bp", "zmctl"), "\n".join([
        "$internal", "   for each nm in 'zmdata':@fm:'zmdir':@fm:'bp'",
        "      openpath '%s/':nm to f else crt 'ZC no ':nm ; continue" % acct_path("zmone"),
        "      write 'a data record' to f, 'zmr1'",
        "      delete f, 'zmr1'", "      close f", "   next nm", "   crt 'ZC done'", "end", ""]))
    g.adm(["BASIC bp zmctl", "RUN bp zmctl"], internal=True)
    one("B18: records written and deleted in a hashed data file, a directory file and a program file add nothing to the journal", off, [])
    # ids
    off = jsize()
    zw("zmone", ["VW|-|zm sp%1|X~spaced", "VW|-|zm*star|X~starred", "VW|-|ZMUPPER|X~u"])
    got = evs(jtail(off))
    raw = jtail(off) or ""
    row("B19: a record id with a space and a percent sign is written to the journal encoded (%20 and %25) and reads back whole; an id with * is kept as it is",
        ("v", "w", "zmone", "-", "zm sp%1") in got and ("v", "w", "zmone", "-", "zm*star") in got and "zm%20sp%251" in raw, repr((got, raw[-200:])))
    row("B19a: every line is one line of the form  time kind op account file id  (no control character, no second line forged by an id)",
        all(EV.match(ln) for ln in raw.splitlines()) and raw.endswith("\n"), repr(raw[-200:]))
    off = jsize()
    zw("zmone", ["DW|zmf3|a*b|D~1"])
    one("B19b: a dictionary record id with a * is journalled whole", off, [("d", "w", "zmone", "zmf3", "a*b")])
    # the OS routes: rename and an OSPATH delete from an ordinary program
    g.plain("zmone", ["CREATE.FILE zmren DYNAMIC"])
    off = jsize()
    o = tool(["REN|%s/zmren.dic|%s/zmren2.dic" % (acct_path("zmone"), acct_path("zmone"))])
    got = evs(jtail(off))
    row("B20: OSRENAME of a dictionary directory: a removal line for the old name and a creation line for the new", ("d", "x", "zmone", "zmren", "-") in got and ("d", "n", "zmone", "zmren2", "-") in got
        and any(ln.startswith("ZT REN done") for ln in o), repr((got, o[-3:])))
    tool(["MKD|%s/zmempty.dic" % acct_path("zmone")])
    g.put(os.path.join(acct_path("zmone"), "bp", "zmrmd"), "\n".join([
        "   ok = ospath('zmempty.dic', 5)", "   crt 'ZD deleted ':ok", "end", ""]))
    g.plain("zmone", ["BASIC bp zmrmd"])
    off = jsize()
    o = g.plain("zmone", ["RUN bp zmrmd"])
    got = evs(jtail(off))
    row("B21: OSPATH delete of an (empty) dictionary directory from an ORDINARY program: a removal line (the second implementation of OSPATH)",
        ("d", "x", "zmone", "zmempty", "-") in got and any("ZD deleted 1" in ln for ln in o), repr((got, o[-3:])))
    # !OSCOPY into a dictionary directory: a copy at the operating system level, which the hook cannot see, so the routine tells the journal
    g.plain("zmone", ["CREATE.FILE zmcp DYNAMIC"])
    g.put(os.path.join(acct_path("zmone"), "zmsrc.txt"), "a file to copy\n")
    g.put(os.path.join(acct_path("zmone"), "bp", "zmcpy"), "\n".join([
        "   call !oscopy('zmsrc.txt', 'zmcp.dic/zmstray', 1, st)", "   crt 'ZC st=':st", "end", ""]))
    g.plain("zmone", ["BASIC bp zmcpy"])
    off = jsize()
    o = g.plain("zmone", ["RUN bp zmcpy"])
    got = evs(jtail(off))
    row("B22: !OSCOPY of a file into a dictionary directory tells the journal (a file-level line for the dictionary: n), and the copy happened",
        ("d", "n", "zmone", "zmcp", "-") in got and any("ZC st=0" in ln for ln in o) and os.path.exists(os.path.join(acct_path("zmone"), "zmcp.dic", "zmstray")), repr((got, o[-3:])))
    try:
        os.remove(os.path.join(acct_path("zmone"), "zmcp.dic", "zmstray"))
    except OSError:
        pass


# ---- C. drain --------------------------------------------------------------------------------------------------------------------------

def drain_section():
    say("\n--- C. the drain: opening a master file as SDSYS applies the journal to the master files and to master_state -------------------------------")
    before = jsize()
    row("C0: the journal is not empty before any master is opened (the earlier sections left entries)", before is not None and before > 0, repr(before))
    off = jsize()
    out = adm(["LIST.MASTER.PENDING"])
    row("C1: LIST.MASTER.PENDING shows the waiting entries and does not drain them", has_msg(out, 11571) and jsize() == off and off > 0, repr((out[:6], jsize(), off)))
    out = adm(["LIST VOC SAMPLE 3"])
    row("C2: an administrator session that opens no master does not drain (the journal, which holds entries, is as it was)", off is not None and off > 0 and jsize() == off, repr((jsize(), off)))
    # the file as the master copy sees it BEFORE: planted entries from section B have no master copy yet
    o = tool(["OPENV|zmone*zmw3", "CMP|zmone|v|-|zmw3", "CMP|zmone|v|-|zmcopy1", "CMP|zmone|v|-|zmw1"])
    row("C3: the OPEN of voc_master by name drained: the same program finds the records written in section B (zmw3, zmcopy1)", any(ln.startswith("ZT OPENV found") for ln in o)
        and cmp_res(o, "zmone", "v", "-", "zmw3") == "SAME" and cmp_res(o, "zmone", "v", "-", "zmcopy1") == "SAME", repr(zt(o, "OPENV") + zt(o, "CMP")))
    row("C3a: the record deleted in section B (zmw1) is not in the master either: account and master are both ABSENT", cmp_res(o, "zmone", "v", "-", "zmw1") == "ABSENT", repr(zt(o, "CMP")))
    row("C4: the drain compacted the journal: it is empty again", jsize() == 0, repr(jsize()))
    o = tool(["CMP|zmone|d|zmf1|F1", "CMP|zmone|d|zmf1|IT1", "CMP|zmone|d|zmf1|F2", "CMP|zmone|d|zmf3|P1", "CMP|zmone|d|zmf3|a*b", "CMP|zmone|d|zmren2|@id"])
    row("C5: dictionary records were mirrored: P1 (written through the F-pointer), a*b, and zmren2's @id from the rename",
        all(cmp_res(o, "zmone", "d", f, i) == "SAME" for f, i in (("zmf3", "P1"), ("zmf3", "a*b"), ("zmren2", "@id"))), repr(zt(o, "CMP")))
    row("C5a: the dictionary DELETE.FILE removed in B14 (zmf1.dic) took its master copies with it: F1, IT1 (seen in B8a) and F2 are ABSENT in the account AND in the master "
        "(an event of op x resynced the whole file)", all(cmp_res(o, "zmone", "d", "zmf1", i) == "ABSENT" for i in ("F1", "IT1", "F2")), repr(zt(o, "CMP")))
    o = tool(["CNT|zmone|d|zmf1", "CNT|zmone|d|zmf2", "CNT|zmone|d|zmren", "CNT|zmone|d|zmempty", "CNT|zmone|d|zmf3"])
    cn = " ".join(zt(o, "CNT"))
    m3 = re.search(r"zmf3 account=(\d+) master=(\d+)", cn)
    row("C6: the dictionaries removed in section B (zmren and zmempty removed or renamed) have no master keys left, and dictionary zmf2 never existed; "
        "the control zmf3, which is there, is in the master in full",
        "ZT CNT zmone d zmren account=0 master=0" in cn and "ZT CNT zmone d zmempty account=0 master=0" in cn and "zmf2 account=0 master=0" in cn
        and bool(m3) and int(m3.group(1)) > 0 and m3.group(1) == m3.group(2), repr(cn))
    # state
    o = tool(["SGET|v*zmone*zmw3", "SGET|d*zmone*zmf3*P1", "SGET|v*zmone*zmw1"])
    sg = zt(o, "SGET")
    row("C7: master_state follows: a checksum record for zmw3 and for the dictionary record P1; none for the deleted zmw1",
        len(sg) == 3 and re.search(r"= [0-9a-f]{16}\|\d+", sg[0]) and re.search(r"= [0-9a-f]{16}\|\d+", sg[1]) and sg[2].endswith("ABSENT"), repr(sg))
    # OPENPATH drains too
    zw("zmone", ["VW|-|zmw4|X~after"])
    o = tool(["OPENP|zmone*zmw4"])
    row("C8: opening voc_master by OPENPATH drains as well", any(ln.startswith("ZT OPENP found") for ln in o) and jsize() == 0, repr((zt(o, "OPENP"), jsize())))
    # master_state by name drains
    zw("zmone", ["VW|-|zmw5|X~after2"])
    o = tool(["OPENS|v*zmone*zmw5"])
    row("C9: opening master_state by name drains too", any(ln.startswith("ZT OPENS found") for ln in o), repr(zt(o, "OPENS")))
    # an ordinary session cannot reach the masters
    g.put(os.path.join(acct_path("zmone"), "bp", "zmpeek"), "\n".join([
        "   open 'voc_master' to f then crt 'ZY byname OPEN' else crt 'ZY byname NO'",
        "   openpath '%s/voc_master' to f2 then crt 'ZY bypath OPEN' else crt 'ZY bypath NO status=':status()" % g.SYS,
        "   openseq '%s/$master.journal' to j then crt 'ZY journal OPEN' else crt 'ZY journal NO status=':status()" % g.SYS,
        "end", ""]))
    g.plain("zmone", ["BASIC bp zmpeek"])
    o = g.plain("zmone", ["RUN bp zmpeek"])
    row("C10: an ordinary session cannot open voc_master by name (no VOC entry), by path (the OS gate, status 3035) or read the journal by path - and both exist",
        os.path.isdir(os.path.join(g.SYS, "voc_master")) and os.path.isfile(J()) and "ZY byname NO" in o and any(ln.startswith("ZY bypath NO status=3035") for ln in o) and any(ln.startswith("ZY journal NO") for ln in o), repr(o[-5:]))
    # replay is harmless
    t = jtext()
    zw("zmone", ["VW|-|zmw6|X~replay"])
    dup = jtext()
    with open(J(), "ab") as f:
        f.write(dup.encode("latin-1") * 3)
    tool(["OPENV|zmone*zmw6"])
    o = tool(["CMP|zmone|v|-|zmw6"])
    row("C11: the same entries three more times change nothing (the drain applies the CURRENT state of each key, so it is idempotent)", cmp_res(o, "zmone", "v", "-", "zmw6") == "SAME", repr(zt(o, "CMP")))
    # malformed lines and hostile ones
    zw("zmone", ["VW|-|zmw7|X~after bad lines"])
    with open(J(), "ab") as f:
        f.write(b"garbage\n\n1 x y\n1760000000 v w zmone\n1760000000 v w zmghost - zmghostrec\n"
                b"1760000000 d w zmone ../zmtwo zmesc\n1760000000 d w zmone /etc zmesc2\n")
    o = tool(["OPENV|zmone*zmw7", "CMP|zmone|v|-|zmw7", "MGET|v|zmghost*zmghostrec", "MGET|d|zmone*../zmtwo*zmesc"])
    row("C12: lines that are not entries, an entry for an account that is not registered, and entries naming a dictionary with .. or / are skipped; "
        "the good entry after them is still applied", cmp_res(o, "zmone", "v", "-", "zmw7") == "SAME" and any(ln.endswith("ABSENT") for ln in zt(o, "MGET")) and
        len([ln for ln in zt(o, "MGET") if ln.endswith("ABSENT")]) == 2, repr(zt(o, "CMP") + zt(o, "MGET")))
    row("C12a: the journal was compacted all the same (bad lines are consumed, not kept for ever)", jsize() == 0, repr(jsize()))
    # a master edit by SDSYS is not pushed: the account is the truth in stage 1
    tool(["MPUT|v|zmone*zmw7|X~edited in the master"])
    o = tool(["CMP|zmone|v|-|zmw7"])
    row("C13: (stage 1) an edit of a master record is NOT pushed to the account, and CHECK sees the difference: CMP says DIFF", cmp_res(o, "zmone", "v", "-", "zmw7") == "DIFF", repr(zt(o, "CMP")))
    zw("zmone", ["VW|-|zmw7|X~account changed again"])
    o = tool(["OPENV|zmone*zmw7", "CMP|zmone|v|-|zmw7"])
    row("C14: the next change of that key in the account overwrites the master copy: the account is the truth", cmp_res(o, "zmone", "v", "-", "zmw7") == "SAME", repr(zt(o, "CMP")))


# ---- D. transactions ---------------------------------------------------------------------------------------------------------------------

def race_section():
    import threading
    say("\n--- D2. sessions appending while SDSYS drains and empties the journal: no line falls between the drain's last look and its truncation ---------")
    tool(["OPENV|zmone*bp"])
    KEYS, ROUNDS = 100, 300       # 3 x 30,000 distinct records: 3 x 30,000 journal lines is 5.4 MB, over the journal's 4 MB limit if no drain kept up
    writers = [("zmone", "zmra"), ("zmtwo", "zmrb"), ("zmos", "zmrc")]
    for acct, prefix in writers:
        g.plain(acct, ["CREATE.FILE zmrace DYNAMIC"])
        args(acct_path(acct), ["%s|%d|%d" % (prefix, KEYS, ROUNDS)])
    tool(["OPENV|zmone*bp"])
    args(g.SYS, ["4"])                  # the administrator drains for 4 seconds, flat out, without a session start between drains
    done = {}
    drain_out = []

    def write(acct):
        done[acct] = g.plain(acct, ["RUN bp zmchurn"])

    def drainer():
        drain_out.extend(g.sd(g.SYS, ["ZMDRAIN"], admin=True))

    ths = [threading.Thread(target=write, args=(a,)) for a, _ in writers]
    dt = threading.Thread(target=drainer)
    t0 = time.time()
    dt.start()
    time.sleep(0.3)                     # the drainer is running before the first line is written
    for t in ths:
        t.start()
    for t in ths:
        t.join()
    elapsed = time.time() - t0
    dt.join()
    m = re.search(r"ZR drains=(\d+) lines=(\d+)", "\n".join(drain_out))
    nd, nl = (int(m.group(1)), int(m.group(2))) if m else (None, None)
    say("      %d writers x %d writes took %.1f s while SDSYS drained %s times and applied %s lines" % (len(writers), KEYS * ROUNDS, elapsed, nd, nl))
    row("D2a: every writer finished all of its %d writes (the null case: a writer that did nothing fails here)" % (KEYS * ROUNDS),
        all(any(ln == "ZH done %d" % (KEYS * ROUNDS) for ln in done.get(a, [])) for a, _ in writers), repr({a: done.get(a, [])[-1:] for a, _ in writers}))
    row("D2b: SDSYS drained hundreds of times while they wrote, and applied lines in more of those drains than one (so the emptying of the journal met live appenders)",
        nd is not None and nd >= 100 and nl is not None and nl > 0, repr((nd, nl, drain_out[-3:])))
    tool(["OPENV|zmone*bp"])
    out = adm(["LIST.MASTER.PENDING"])
    row("D2c: neither flag was raised during the run (a journal that reaches its limit drops lines, and this test would then be measuring that)",
        not has_msg(out, 11572) and not has_msg(out, 11573), repr(out[-4:]))
    cnt = tool(["CNT|%s|d|zmrace" % a for a, _ in writers])
    rows_ = [re.search(r"account=(\d+) master=(\d+)", ln) for ln in zt(cnt, "CNT")]
    row("D2d: after a last drain each master holds EVERY one of the %d distinct records of its account (plus the @id): no journal line was lost to the emptying of the journal" % (KEYS * ROUNDS),
        len(rows_) == 3 and all(r and int(r.group(1)) == KEYS * ROUNDS + 1 and r.group(1) == r.group(2) for r in rows_), repr(zt(cnt, "CNT")))
    chk = adm(["CHECK.MASTERS"])
    row("D2e: CHECK.MASTERS finds no difference in any account afterwards", has_msg(chk, 11568), repr(chk[-6:]))
    for a, _ in writers:
        g.plain(a, ["DELETE.FILE zmrace NO.QUERY", "Y"])      # one event for the whole dictionary
    tool(["OPENV|zmone*bp"])
    cnt = tool(["CNT|%s|d|zmrace" % a for a, _ in writers])
    row("D2f: DELETE.FILE of the file took every one of its master copies with it (one event of op x for 90,000 keys)",
        len(zt(cnt, "CNT")) == 3 and all(ln.endswith("account=0 master=0") for ln in zt(cnt, "CNT")), repr(zt(cnt, "CNT")))
    adm(["SYNC.MASTERS"])           # whatever the run raised or left is put right for the next section


def txn_section():
    say("\n--- D. transactions: the hook delivers at COMMIT and drops at ROLLBACK -------------------------------------------------------------------")
    tool(["OPENV|zmone*bp"])           # drain first so that sizes start from 0
    args(acct_path("zmone"), ["C|zmtxc"])
    o = g.plain("zmone", ["RUN bp zmtx"])
    m = re.search(r"ZX C before=(-?\d+) during=(-?\d+) after=(-?\d+) present=(\d)", "\n".join(o))
    row("D1: COMMIT - the journal is the same size inside the transaction as before it, and has the line after COMMIT",
        bool(m) and m.group(1) == m.group(2) and int(m.group(3)) > int(m.group(1)) and m.group(4) == "1", repr(o[-3:]))
    got = evs(jtext())
    row("D1a: that line is  v w zmone - zmtxc", got == [("v", "w", "zmone", "-", "zmtxc")], repr(got))
    tool(["OPENV|zmone*bp"])
    args(acct_path("zmone"), ["R|zmtxr"])
    o = g.plain("zmone", ["RUN bp zmtx"])
    m = re.search(r"ZX R before=(-?\d+) during=(-?\d+) after=(-?\d+) present=(\d)", "\n".join(o))
    row("D2: ROLLBACK - the journal exists and has no line at all, and the record is not there", bool(m) and int(m.group(1)) == 0 and m.group(1) == m.group(2) == m.group(3) and m.group(4) == "0"
        and jtext() == "", repr(o[-3:]))


# ---- E. failure and the size cap ----------------------------------------------------------------------------------------------------------

def fail_section():
    say("\n--- E. a journal that cannot be written never stops the user's write; it sets a flag CHECK.MASTERS and LIST.MASTER.PENDING report -------")
    tool(["OPENV|zmone*bp"])
    out = adm(["LIST.MASTER.PENDING"])
    row("E0: to begin with no flag is set (a missing journal earlier did not count as a failure)", not has_msg(out, 11572) and not has_msg(out, 11573), repr(out[-6:]))
    os.chmod(J(), 0o000)
    d, o = zw("zmone", ["VW|-|zmfail1|X~written with the journal closed"])
    os.chmod(J(), 0o620)
    row("E1: the user's WRITE succeeded although the journal could not be appended to", d.get(("VW", "-", "zmfail1")) == "OK", repr(o[-3:]))
    o = tool(["VOCHAS|zmone|zmfail1"])
    row("E1a: and the record is there", any(ln.endswith("PRESENT") for ln in zt(o, "VOCHAS")), repr(zt(o, "VOCHAS")))
    out = adm(["LIST.MASTER.PENDING"])
    row("E2: LIST.MASTER.PENDING reports the stale flag (11572)", has_msg(out, 11572), repr(out[-6:]))
    out = adm(["CHECK.MASTERS zmone"])
    row("E3: CHECK.MASTERS reports it too, and finds the record the master lacks (a missing row for zmfail1)",
        has_msg(out, 11572) and any("zmfail1" in ln and "zmone" in ln for ln in out), repr(out[-8:]))
    out = adm(["SYNC.MASTERS zmone"])
    out2 = adm(["CHECK.MASTERS zmone"])
    row("E4: SYNC.MASTERS zmone repairs zmone (CHECK.MASTERS zmone finds no difference) but does not clear the system-wide flag, which only a sync of every account can",
        has_msg(out2, 11568) and has_msg(out2, 11572), repr((out[-4:], out2[-6:])))
    out = adm(["SYNC.MASTERS"])
    out2 = adm(["LIST.MASTER.PENDING"])
    row("E5: SYNC.MASTERS with no account (it ran: it reports zmone) clears the flag, and LIST.MASTER.PENDING says nothing is waiting",
        has_msg(out, 11566, "zmone") and not has_msg(out2, 11572) and not has_msg(out2, 11573) and has_msg(out2, 11574), repr((out[-3:], out2[-6:])))
    # a journal that is a directory: open() fails, the write is not blocked
    jp = J()
    saved = jp + ".saved"
    os.rename(jp, saved)
    os.mkdir(jp)
    d, o = zw("zmone", ["VW|-|zmfail2|X~journal is a directory"])
    os.rmdir(jp)
    os.rename(saved, jp)
    row("E6: a journal that is a directory (or anything that cannot be appended to) does not stop the WRITE", d.get(("VW", "-", "zmfail2")) == "OK", repr(o[-3:]))
    out = adm(["LIST.MASTER.PENDING"])
    row("E7: and sets the stale flag", has_msg(out, 11572), repr(out[-6:]))
    adm(["SYNC.MASTERS"])
    # a journal that is MISSING where master files exist is a lost journal (somebody moved it): every line meant for it is gone
    out = adm(["LIST.MASTER.PENDING"])
    row("E7a: (control) the flag is down again after the full sync", not has_msg(out, 11572), repr(out[-4:]))
    lost = J() + ".lost"
    os.rename(J(), lost)
    d, o = zw("zmone", ["VW|-|zmlost1|X~written while the journal is gone"])
    os.rename(lost, J())
    row("E7b: a journal that is not there, on a system that has master files, does not stop the user's WRITE", d.get(("VW", "-", "zmlost1")) == "OK", repr(o[-3:]))
    out = adm(["LIST.MASTER.PENDING"])
    row("E7c: ...and is a lost journal: the stale flag is up (11572) - unlike a missing journal before there were master files (E0)", has_msg(out, 11572), repr(out[-6:]))
    adm(["SYNC.MASTERS"])
    # the size cap
    with open(J(), "ab") as f:
        f.write(b"x" * (4 * 1024 * 1024 + 4096))
    size = jsize()
    d, o = zw("zmone", ["VW|-|zmcap1|X~journal over its limit"])
    row("E8: with the journal at its limit the user's WRITE succeeds, the journal does not grow", d.get(("VW", "-", "zmcap1")) == "OK" and jsize() == size, repr((jsize(), size)))
    out = adm(["LIST.MASTER.PENDING"])
    row("E9: the resync flag is set (11573)", has_msg(out, 11573), repr(out[-6:]))
    out = adm(["SYNC.MASTERS"])
    row("E10: SYNC.MASTERS with no account brings everything up to date, empties the journal and clears the flag",
        jsize() == 0 and not has_msg(adm(["LIST.MASTER.PENDING"]), 11573), repr(jsize()))
    o = tool(["CMP|zmone|v|-|zmcap1", "CMP|zmone|v|-|zmfail2"])
    row("E11: the records written while the journal could not take them are in the masters now", cmp_res(o, "zmone", "v", "-", "zmcap1") == "SAME" and cmp_res(o, "zmone", "v", "-", "zmfail2") == "SAME", repr(zt(o, "CMP")))


# ---- F. check ----------------------------------------------------------------------------------------------------------------------------

def check_section():
    say("\n--- F. CHECK.MASTERS: read only; finds what differs, what is missing, what is extra, what cannot be written -----------------------------")
    out = adm(["CHECK.MASTERS"])
    row("F1: on a system whose masters are right, CHECK.MASTERS says so (11568) and counts no differences", has_msg(out, 11568) and any("0" in ln for ln in out if re.search(msg_rx(11569), ln)), repr(out[-6:]))
    tool(["MPUT|v|zmone*bp|X~changed in the master", "MDEL|v|zmone*zmw3", "MPUT|v|zmone*ghostrec|X~extra",
          "MPUT|d|zmone*nosuchfile*x|D~1", "MPUT|v|zmghost*oldrec|X~account long gone"])
    snap = masters_snapshot()
    out = adm(["CHECK.MASTERS"])
    snap2 = masters_snapshot()
    txt = "\n".join(out)
    row("F2: a changed master record is reported as differing (account zmone, VOC record bp)", re.search(r"differs\S*\s+zmone\s+.*\bbp\b", txt) is not None, repr(out[-14:]))
    row("F3: a master record whose account record exists is reported missing when the master lacks it (zmw3)", re.search(r"missing\S*\s+zmone\s+.*zmw3", txt) is not None, repr(out[-14:]))
    row("F4: a master record the account does not have is reported extra (ghostrec)", re.search(r"extra\S*\s+zmone\s+.*ghostrec", txt) is not None, repr(out[-14:]))
    row("F5: so is a dictionary record of a file the account has no dictionary for (nosuchfile), and a record of an account that is not registered (zmghost)",
        re.search(r"extra\S*\s+zmone\s+.*nosuchfile", txt) is not None and re.search(r"extra\S*\s+zmghost\s+.*oldrec", txt) is not None, repr(out[-14:]))
    row("F6: CHECK.MASTERS (it ran: it counted the differences) changed nothing: every byte of the three master files is as it was before the check (it is read only)",
        has_msg(out, 11569) and len(snap) == 3 and snap == snap2, "differences: %r" % [m for m in snap if snap[m] != snap2.get(m)])
    out = adm(["CHECK.MASTERS zmtwo"])
    row("F7: CHECK.MASTERS zmtwo (it ran) looks at zmtwo only: none of zmone's differences is listed",
        has_msg(out, 11569) and not re.search(r"zmone", "\n".join(ln for ln in out if "zmtwo" not in ln and re.search(msg_rx(11570), ln))), repr(out[-6:]))
    out = adm(["CHECK.MASTERS zmnosuch"])
    row("F8: an account that is not registered is refused (11563)", has_msg(out, 11563), repr(out[-4:]))
    out = adm(["SYNC.MASTERS"])
    out2 = adm(["CHECK.MASTERS"])
    row("F9: SYNC.MASTERS with no account repairs all of it - the changed, the missing, the extra, the dictionary record of no file and the unregistered account's record "
        "(CHECK.MASTERS is clean again)", has_msg(out2, 11568), repr(out2[-8:]))
    # not writable
    p0 = os.path.join(acct_path("zmone"), "voc", "%0")
    pd = os.path.join(acct_path("zmone"), "zmf3.dic", "%0")
    os.chmod(p0, 0o444)
    os.chmod(pd, 0o444)
    out = adm(["CHECK.MASTERS zmone"])
    os.chmod(p0, 0o664)
    os.chmod(pd, 0o664)
    txt = "\n".join(out)
    row("F10: a VOC subfile that lacks group write is reported (nonwritable, zmone, voc)", re.search(r"nonwritable\S*\s+zmone\s+.*voc", txt) is not None, repr(out[-8:]))
    row("F11: so is a dictionary's (zmf3)", re.search(r"nonwritable\S*\s+zmone\s+.*zmf3", txt) is not None, repr(out[-8:]))
    out = adm(["CHECK.MASTERS zmone"])
    row("F12: with the modes put back CHECK.MASTERS zmone is clean", has_msg(out, 11568), repr(out[-6:]))
    # a key that is too long for MAXIDLEN
    longid = "zmlong" + "x" * 54
    zw("zmone", ["VW|-|%s|X~long" % longid])
    out = adm(["CHECK.MASTERS zmone"])
    row("F13: a VOC id whose master key (account*id) is longer than MAXIDLEN cannot be mirrored and is REPORTED, not dropped silently (toolong)", "toolong" in "\n".join(out) and longid[:20] in "\n".join(out), repr(out[-6:]))
    out = adm(["SYNC.MASTERS zmone"])
    left_out = [int(m.group(3)) for m in (re.search(msg_rx(11578), ln) for ln in out) if m]
    row("F14: SYNC.MASTERS zmone counts it among the records left out (the third number of 11578 is 1)", left_out == [1], repr((left_out, out[-4:])))
    zw("zmone", ["VD|-|%s|" % longid])
    adm(["SYNC.MASTERS zmone"])
    # the boundary: a master key exactly as long as MAXIDLEN (63) would fit voc_master, but the state key is two characters longer, and a master file that
    # holds an id longer than MAXIDLEN cannot be opened again - so such a record is left out as well
    edge = "zmedge" + "y" * 51          # 'zmone*' (6) and 57 = 63
    zw("zmone", ["VW|-|%s|X~edge" % edge])
    out = adm(["CHECK.MASTERS zmone"])
    row("F14a: a VOC id that makes the master key exactly MAXIDLEN long is reported toolong too (the state key would be 65)", "toolong" in "\n".join(out) and edge[:20] in "\n".join(out), repr(out[-6:]))
    out = adm(["SYNC.MASTERS zmone"])
    o = tool(["OPENS|$journal", "OPENV|zmone*bp"])
    row("F14b: ...and master_state and voc_master can still be opened afterwards (nothing longer than MAXIDLEN was written to either)",
        any(ln.startswith("ZT OPENS found") for ln in o) and any(ln.startswith("ZT OPENV found") for ln in o), repr(zt(o, "OPENS") + zt(o, "OPENV")))
    zw("zmone", ["VD|-|%s|" % edge])
    adm(["SYNC.MASTERS zmone"])
    # a copy is never deleted for want of being able to read the original
    before = tool(["CNT|zmone|d|zmf3"])
    mb = re.search(r"account=(\d+) master=(\d+)", " ".join(zt(before, "CNT")))
    dd = os.path.join(acct_path("zmone"), "zmf3.dic")
    for n in ("%0", "%1"):
        os.chmod(os.path.join(dd, n), 0o000)
    out = adm(["SYNC.MASTERS zmone"])
    chk = adm(["CHECK.MASTERS zmone"])
    for n in ("%0", "%1"):
        os.chmod(os.path.join(dd, n), 0o664)
    after = tool(["CNT|zmone|d|zmf3"])
    ma = re.search(r"account=(\d+) master=(\d+)", " ".join(zt(after, "CNT")))
    row("F15: a dictionary that EXISTS and cannot be opened (its subfiles at mode 0) leaves its master copies alone when SYNC.MASTERS runs: the master still holds every key it did",
        bool(mb) and bool(ma) and int(mb.group(2)) > 0 and mb.group(2) == ma.group(2), repr((mb and mb.groups(), ma and ma.groups())))
    row("F16: ...and CHECK.MASTERS says so (unreadable, zmone, zmf3) and does not call its master records extra",
        re.search(r"unreadable\S*\s+zmone\s+.*zmf3", "\n".join(chk)) is not None and not re.search(r"extra\S*\s+zmone\s+.*zmf3", "\n".join(chk)), repr(chk[-6:]))
    out = adm(["CHECK.MASTERS zmone"])
    row("F17: with the modes put back the account is clean again (nothing was lost)", has_msg(out, 11568), repr(out[-4:]))


# ---- G. who may do what ----------------------------------------------------------------------------------------------------------------

def gate_section():
    say("\n--- G. SDSYS only -----------------------------------------------------------------------------------------------------------------------")
    newvoc = os.path.join(os.path.dirname(HERE), "sdsys", "newvoc")
    tmpl = os.path.join(os.path.dirname(HERE), "sdsys", "voc_template")
    verbs = ["sync.masters", "check.masters", "list.master.pending"]
    row("G1: the verbs are records of voc_template and of NO other VOC source (newvoc, which every account is made from)",
        all(os.path.exists(os.path.join(tmpl, v)) for v in verbs) and not any(os.path.exists(os.path.join(newvoc, v)) for v in verbs), "")
    for a in ACCOUNTS:
        o = g.plain(a, ["SYNC.MASTERS", "CHECK.MASTERS", "LIST.MASTER.PENDING"])
        row("G2: in %s (an ordinary account) none of the three verbs exists" % a, not has_msg(o, 11565) and not has_msg(o, 11566) and not has_msg(o, 11568) and not has_msg(o, 11571), repr(o[-6:]))
    # plant the verbs in a fixture VOC and run them as an ordinary session
    g.put(os.path.join(g.SYS, "bp", "zmplant"), "\n".join([
        "$internal", "   openpath '%s/voc' to v else crt 'ZP no voc' ; stop" % acct_path("zmtwo"),
        "   write 'V':@fm:'CA':@fm:'$masters' to v, 'sync.masters'", "   write 'V':@fm:'CA':@fm:'$masters' to v, 'check.masters'",
        "   write 'V':@fm:'CA':@fm:'$masters' to v, 'list.master.pending'", "   close v", "   crt 'ZP done'", "end", ""]))
    g.adm(["BASIC bp zmplant", "RUN bp zmplant"], internal=True)
    tool(["OPENV|zmone*bp"])
    mark = masters_snapshot()
    off = jsize()
    for v in ("SYNC.MASTERS zmone", "CHECK.MASTERS zmone", "LIST.MASTER.PENDING"):
        o = g.plain("zmtwo", [v])
        row("G3: an ordinary session that has the verb in its VOC is refused it (administrator required, 2001): %s" % v, any("administrator" in ln.lower() for ln in o) and not has_msg(o, 11566) and not has_msg(o, 11571), repr(o[-4:]))
    row("G3a: and the refused verbs changed no master file (there are three to compare)", len(mark) == 3 and masters_snapshot() == mark, "")
    # kernel ops from an ordinary session
    ops = ["pending", "peek|5", "drain", "sync|zmone", "check|zmone", "drop|zmtwo", "init"]
    o = kop(ops, acct="zmtwo", admin=False)
    row("G4: kernel(K$MASTERS) from an ordinary session refuses every administrator op (status 2) - %s" % ", ".join(x.split("|")[0] for x in ops),
        all(zk_status(o, op.split("|")[0]) == "2" for op in ops), repr(zt(o, "") or [ln for ln in o if ln.startswith("ZK")]))
    row("G4a: and nothing was changed (the three masters are as they were)", len(mark) == 3 and masters_snapshot() == mark, "")
    o = kop(["pending", "ready"], admin=True)
    row("G5: the same ops from the administrator answer status 0", zk_status(o, "pending") == "0" and zk_status(o, "ready") == "0", repr([ln for ln in o if ln.startswith("ZK")]))
    o = kop(["ready"], acct="zmtwo", admin=False)
    row("G6: 'ready' (is it set up here?) is the one op an ordinary $internal program may ask", zk_status(o, "ready") == "0", repr([ln for ln in o if ln.startswith("ZK")]))


# ---- H. lifecycle ----------------------------------------------------------------------------------------------------------------------

def life_section():
    say("\n--- H. lifecycle: a new account, a deleted account ------------------------------------------------------------------------------------")
    # zmnew: an account CREATE.ACCOUNT has just made (directory, VOC and register record), with no master copies yet
    path = g.build_account("zmnew")
    # CREATE.ACCOUNT makes the VOC BEFORE it writes the register record, so the hook cannot yet tell whose the VOC is: take the record away while
    # the VOC is added to, and put it back
    reg = os.path.join(g.SYS, "accounts", "zmnew")
    os.remove(reg)
    g.put(os.path.join(g.SYS, "bp", "zmfixn"), "\n".join([
        "$internal", "   openpath '%s/voc' to v else crt 'ZN no voc' ; stop" % acct_path("zmnew"),
        "   write 'V':@fm:'CA':@fm:'$zmtool' to v, 'zmtool'", "   close v", "   crt 'ZN done'", "end", ""]))
    o = g.adm(["BASIC bp zmfixn", "RUN bp zmfixn"], internal=True)
    row("H0: the unregistered account's VOC was written (the hook found no account for it and journalled nothing for zmnew)",
        g.has(o, r"^ZN done$") and not any(e[2:3] == ("zmnew",) for e in evs(jtext())), repr((o[-2:], evs(jtext())[-3:])))
    g.reg_write("zmnew", [path, "", g.GROUP, "", "", "", "no", "no"])
    o = tool(["CNT|zmnew|v|-"])
    row("H1: a new account has records in its VOC and no master copies (the starting point)",
        any(re.search(r"account=([1-9]\d*) master=0$", ln) for ln in zt(o, "CNT")), repr(zt(o, "CNT")))
    out = adm(["SYNC.MASTERS zmnew"])
    o = tool(["CNT|zmnew|v|-"])
    m = re.search(r"account=(\d+) master=(\d+)", " ".join(zt(o, "CNT")))
    row("H2: SYNC.MASTERS zmnew (what CREATE.ACCOUNT does when the register record is written) populates its copies", bool(m) and int(m.group(1)) > 100 and m.group(1) == m.group(2), repr((zt(o, "CNT"), out[-3:])))
    # DELETE.ACCOUNT's drop
    o = kop(["drop|zmnew"], admin=True)
    o2 = tool(["KEYS|v|zmnew", "KEYS|v|zmtwo", "KEYS|d|zmnew"])
    ks = {re.match(r"ZT KEYS (\S) (\S+) n=(\d+)", ln).group(2): int(re.match(r"ZT KEYS (\S) (\S+) n=(\d+)", ln).group(3)) for ln in zt(o2, "KEYS") if re.match(r"ZT KEYS (\S) (\S+) n=(\d+)", ln)}
    row("H3: the drop op (DELETE.ACCOUNT's) removes every master copy of the account and no other account's", zk_status(o, "drop") == "0" and ks.get("zmnew") == 0 and ks.get("zmtwo", 0) > 100, repr((o[-2:], zt(o2, "KEYS"))))
    st = tool(["SGET|v*zmnew*bp"])
    row("H4: and its master_state records", any(ln.endswith("ABSENT") for ln in zt(st, "SGET")), repr(zt(st, "SGET")))


# ---- J. key forms --------------------------------------------------------------------------------------------------------------------------

def keys_section():
    say("\n--- J. key forms: split at the first one or two asterisks only; case does not make two keys -----------------------------------------------")
    zw("zmone", ["VW|-|zmk*a*b|X~two stars", "VW|-|ZMCASE|X~one", "VW|-|zmcase|X~two"])
    zw("zmone", ["DW|zmf3|k*x*y|D~9"])
    adm(["SYNC.MASTERS zmone"])
    o = tool(["MGET|v|zmone*zmk*a*b", "MGET|d|zmone*zmf3*k*x*y", "MGET|v|zmone*zmcase", "MGET|v|zmone*ZMCASE", "CMP|zmone|v|-|zmk*a*b", "CMP|zmone|d|zmf3|k*x*y"])
    mg = zt(o, "MGET")
    row("J1: a VOC id with two asterisks is the key zmone*zmk*a*b (the first * ends the account)", len(mg) > 0 and "= X|two stars" in mg[0], repr(mg))
    row("J2: a dictionary record id with two asterisks is zmone*zmf3*k*x*y (the first two end the account and the file)", len(mg) > 1 and "= D|9" in mg[1], repr(mg))
    row("J3: the VOC and the master files are case-insensitive: zmcase and ZMCASE are one record, in the account and in voc_master",
        len(mg) > 3 and mg[2].split("= ", 1)[-1] == mg[3].split("= ", 1)[-1] and "= X|two" in mg[2], repr(mg[2:]))
    row("J4: CMP agrees: SAME for both", cmp_res(o, "zmone", "v", "-", "zmk*a*b") == "SAME" and cmp_res(o, "zmone", "d", "zmf3", "k*x*y") == "SAME", repr(zt(o, "CMP")))


# ---- K. what it costs -----------------------------------------------------------------------------------------------------------------------

def perf_section():
    say("\n--- K. what the journal costs on the write path --------------------------------------------------------------------------------------")
    tool(["OPENV|zmone*bp"])
    N = 2000
    ROUNDS = 3

    def loop(prefix, target):
        args(acct_path("zmone"), ["%s|%d|%s" % (prefix, N, target)])
        o = g.plain("zmone", ["RUN bp zmloop"])
        m = re.search(r"wrote (\d+) ms=(\d+)", "\n".join(o))
        return (int(m.group(2)) if m and int(m.group(1)) == N else None)

    def median(xs):
        xs = sorted(x for x in xs if x is not None)
        return xs[len(xs) // 2] if xs else None

    off = jsize()
    with_j = [loop("zmp%d" % r, "voc") for r in range(ROUNDS)]
    lines = len([e for e in evs(jtail(off)) if e[0] != "?"])
    row("K1: %d VOC writes in each of %d loops add exactly %d journal lines (the null case: a loop that wrote nothing would fail here)" % (N, ROUNDS, N * ROUNDS), lines == N * ROUNDS, repr((lines, with_j)))
    # the time the drain takes to apply them (it is the next thing that opens a master)
    t0 = time.time()
    tool(["OPENV|zmone*bp"])
    drain_s = time.time() - t0
    # the same loops with the journal moved away: every append is ENOENT, which costs one failed open
    saved = J() + ".away"
    os.rename(J(), saved)
    no_j = [loop("zmq%d" % r, "voc") for r in range(ROUNDS)]
    data = [loop("zmd%d" % r, "data") for r in range(ROUNDS)]
    os.rename(saved, J())
    ms1, ms2, ms3 = median(with_j), median(no_j), median(data)
    say("    MEASURED (median of %d, %d writes each, in a session's loop on tmpfs; one session start included in none of them):" % (ROUNDS, N))
    say("      VOC writes with the journal      %s ms  =  %s microseconds each" % (ms1, "%.1f" % (ms1 * 1000.0 / N) if ms1 is not None else None))
    say("      VOC writes, no journal file      %s ms  =  %s microseconds each" % (ms2, "%.1f" % (ms2 * 1000.0 / N) if ms2 is not None else None))
    say("      data file writes (not mirrored)  %s ms  =  %s microseconds each" % (ms3, "%.1f" % (ms3 * 1000.0 / N) if ms3 is not None else None))
    say("      the drain of %d lines (opening voc_master, which includes one session start): %.2f s" % (N * ROUNDS, drain_s))
    row("K2: all loops ran and reported a time (the numbers are printed above); the journal did not multiply the cost of a VOC write by more than 3",
        None not in (ms1, ms2, ms3) and ms1 <= max(3 * ms2, ms2 + 400), "with %s ms, without %s ms, data %s ms" % (ms1, ms2, ms3))
    t0 = time.time()
    out = adm(["SYNC.MASTERS"])
    full_s = time.time() - t0
    t0 = time.time()
    adm(["SYNC.MASTERS"])
    again_s = time.time() - t0
    say("      SYNC.MASTERS of every account (%d accounts, one session start included): first %.2f s, again with nothing changed %.2f s" % (4 + 0, full_s, again_s))
    row("K3: SYNC.MASTERS with no account ran and reported every account (the numbers are above)", all(has_msg(out, 11566, a) for a in ["sdsys"] + ACCOUNTS), repr(out[-3:]))


# ---- L. what the installer runs ---------------------------------------------------------------------------------------------------------

def upgrade_section():
    say("\n--- L. upgrade_masters, the program the installer runs as the root session of an install (here as the sandbox user, an administrator) ------")
    out = g.adm(["RUN gpl.bp upgrade_masters"], internal=True)
    row("L1: RUN gpl.bp upgrade_masters on a system that is set up prints COMPLETE on a line of its own (the word the installer looks for)",
        any(ln.strip() == "COMPLETE" for ln in out) and not any("could not" in ln or "error(s) while" in ln for ln in out), repr(out[-6:]))
    chk = adm(["CHECK.MASTERS"])
    row("L2: ...and every master copy matches its account afterwards", has_msg(chk, 11568), repr(chk[-4:]))
    # from nothing: a system that has never had master files, as the first install of this version meets it
    reset_masters()
    g.adm(["RUN bp zmfix"], internal=True)            # takes the three F entries out of the SDSYS VOC, as a system that never had them
    row("L3: (the starting point) the journal and the master files are gone", not os.path.exists(J()) and not os.path.isdir(os.path.join(g.SYS, "voc_master")), "")
    out = g.adm(["RUN gpl.bp upgrade_masters"], internal=True)
    row("L4: on a system with no master files it makes them and copies every account: COMPLETE, and the journal and the files are there with their modes",
        any(ln.strip() == "COMPLETE" for ln in out) and os.path.isfile(J()) and mode_of(J()) == 0o620 and all(os.path.isdir(os.path.join(g.SYS, m)) and mode_of(os.path.join(g.SYS, m)) == 0o770
        for m in MASTERS), repr(out[-6:]))
    chk = adm(["CHECK.MASTERS"])
    row("L5: ...and CHECK.MASTERS finds no difference in any account", has_msg(chk, 11568), repr(chk[-4:]))
    o = tool(["VOCHAS|sdsys|voc_master", "VOCHAS|sdsys|dict_master", "VOCHAS|sdsys|master_state"])
    row("L6: ...and the three F entries are in the SDSYS VOC again", len(zt(o, "VOCHAS")) == 3 and all(ln.endswith("PRESENT") for ln in zt(o, "VOCHAS")), repr(zt(o, "VOCHAS")))
    t0 = time.time()
    out = g.adm(["RUN gpl.bp upgrade_masters"], internal=True)
    say("      upgrade_masters on a system already set up: %.2f s (session start included)" % (time.time() - t0))
    row("L7: run again it prints COMPLETE and leaves the journal empty", any(ln.strip() == "COMPLETE" for ln in out) and jsize() == 0, repr((out[-3:], jsize())))


# ---- main ------------------------------------------------------------------------------------------------------------------------------

def main():
    args_ = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args_) != 1:
        bail("usage: sandbox-masters.py <dir> [--build] [--sections=a,b]")
    g.BOX = os.path.abspath(args_[0])
    g.SYS = os.path.join(g.BOX, "sys")
    g.SD = os.path.join(g.SYS, "bin", "sd")
    sel = [a.split("=", 1)[1].split(",") for a in sys.argv[1:] if a.startswith("--sections=")]
    sections = sel[0] if sel else SECTIONS
    say("sandbox-masters: sandbox %s" % g.BOX)
    say("sandbox-masters: tree    %s" % os.path.dirname(HERE))
    say("sandbox-masters: user %s, group %s" % (g.USER, g.GROUP))
    if "--build" in sys.argv:
        if os.path.exists(g.BOX) and os.listdir(g.BOX):
            bail("%s is not empty" % g.BOX)
        r = subprocess.run([sys.executable, g.TOOL, g.BOX, "all"], capture_output=True, text=True, errors="replace", timeout=1200)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-masters: built, bootstrap passed")
    elif not os.path.isfile(g.SD):
        bail("%s holds no built sandbox (use --build, or point it at one)" % g.BOX)
    subprocess.run([sys.executable, g.TOOL, g.BOX, "start"], capture_output=True, text=True, errors="replace", timeout=120)
    say("\n--- preparation ---------------------------------------------------------------------------------------------------------------------")
    prepare_all()
    controls()
    table = {"setup": setup_section, "hook": hook_section, "drain": drain_section, "race": race_section, "txn": txn_section, "fail": fail_section, "check": check_section,
             "gate": gate_section, "life": life_section, "keys": keys_section, "perf": perf_section, "upgrade": upgrade_section}
    # the sections run in this order whatever --sections says, because each leaves the state the next one needs
    for s in SECTIONS:
        if s in sections:
            try:
                table[s]()
            except Exception as e:      # a section that cannot go on is a failed row, and the next one still runs
                import traceback
                row("section %s ran to its end" % s, False, "%s: %s" % (type(e).__name__, e))
                say("".join(traceback.format_exc().splitlines(True)[-6:]))
    say("\nsandbox-masters: %d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
