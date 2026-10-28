#!/usr/bin/env python3
#
# sandbox-shared.py - S.66, the shared account: a group account named shared whose files an account with the shared.read gate opens by
#                     NAME (no LOGTO, no Q-pointer), through ORDINARY sessions on a private SD.  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-shared.py <dir> [--build] [--sections=a,b]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or absent); without it
# <dir> must already be built.  Exit 0 every row passed, 1 a row failed, 2 it could not run.  Sections: gates, lookup, rights, structure,
# compile, logto.  Only one private SD can exist on a machine (shared memory keys 0x53434c91/92); stop it afterwards with
# sandbox-fromtree.py <dir> stop.
#
# START-HISTORY:
# 18 Oct 26 dm  New (S.66).  ***WRITTEN FROM THE CODE, NEVER RUN: the agent that wrote it could not run SD.  Every row below is a claim about
#               what an ordinary session sees, made from reading op_sh.c, op_dio3.c, _voc_ref, !shared_ref and the loaders; the first real run
#               will fail rows for reasons of syntax or wording that no reading could find.  A row that fails is a finding, not a verdict, until
#               its probe has been looked at.***
# END-HISTORY
#
# THE SHARED ACCOUNT HERE.  The sandbox cannot make Linux groups, so shared is a hand-made register record  <path>\n\nsdg_shared  (a
# group the sandbox user is NOT in, which is the real delivered state: only SDSYS enters it), the directory <sandbox>/group_accounts/shared
# with a VOC made from NEWVOC, and the files listed in SHARED_FILES.  Its fixture is built with the register group temporarily set to the
# sandbox user's own group so that the administrator can sign on to it (CREATE.INDEX needs that); the group is put back before any row.
#
# THE ACCOUNTS (ordinary sessions: `sd -a<account>` run in the account directory, sandbox-gates.py's way; they are administrators only
# when SDTEST_ADMIN=1).  Register fields 13 and 14 are shared.read and shared.write; field 12 is dict.edit; the record of zsblank stops at
# field 12, so BOTH shared fields are absent there - the case that must mean "read ON, write OFF".
#   zsblank  absent / absent    zsempty  empty / empty    zsyes  yes / no    zsno  no / no    zscase  No / Yes    zsjunk  maybe / true
#   zswr  yes / yes with dict.edit NO    zswrd  yes / yes with dict.edit yes    zsstock  as zsblank but its VOC has no syscom
#   zsall  every gate on (sh, os.execute, dict.edit, shared.read, shared.write)    zsnoreg  a directory with a VOC and NO register record
#
# THE INSTRUMENTS.  zsopen opens names, zswrite writes, deletes and reads back, zsone makes ONE change without ON ERROR so that the message
# shows, zsidx writes to an indexed file and asks the index, zshold / zslk hold and meet a record lock - all ORDINARY programs, so the
# kernel's own tests are what is under test; zsk, zsflip and zsint are $internal verbs (the kernel's key answers, the gate withdrawn
# under an open file, and the changes that an internal program is NOT exempt from).  The EVIDENCE of a change is the disk: zsdump, run by
# the administrator, lists every record of every shared file, and the directory is read from here.  A verdict is the word the statement
# gave AND what the disk holds afterwards.
#
# WHAT IT CANNOT SHOW.  (1) The API server's load of the gates (api.shared.read.grant): a sandbox cannot host an API session - that is a
# witness-release-run.sh row.  (2) That `modify.account shared-read-off` and `create.account ... shared-write-on` write the register as
# their reports say: they make or touch Linux users and groups (witness-accounts.sh); here the register is edited by hand and the loaders
# read it.  (3) The installer's creation of the account, its modes and the group sdg_shared (test-install-shared.sh, witness-accounts.sh).
# (4) That the Linux group sdg_shared keeps ordinary users out of LOGTO shared on a real install - here it is shown with a group the user is
# not in.  (5) A rename of a path in shared (OSRENAME): no BASIC statement here reaches it.

import importlib.util
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
spec = importlib.util.spec_from_file_location("sandbox_gates", os.path.join(HERE, "sandbox-gates.py"))
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
g.EDIT_DEFAULT = None           # every record below says all its fields
RUN = "%05d" % (os.getpid() % 100000)
passed = failed = 0
lives = []


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
    say("sandbox-shared: CANNOT RUN - " + msg)
    sys.exit(2)


# name -> shared.read, shared.write (None: the field is absent altogether), dict.edit, sh, os.execute
ACCOUNTS = {
    "zsblank": dict(read=None, write=None, dic="yes", sh="no", osx="no"),
    "zsempty": dict(read="", write="", dic="yes", sh="no", osx="no"),
    "zsyes": dict(read="yes", write="no", dic="yes", sh="no", osx="no"),
    "zsno": dict(read="no", write="no", dic="yes", sh="no", osx="no"),
    "zscase": dict(read="No", write="Yes", dic="yes", sh="no", osx="no"),
    "zsjunk": dict(read="maybe", write="true", dic="yes", sh="no", osx="no"),
    "zswr": dict(read="yes", write="yes", dic="no", sh="no", osx="no"),
    "zswrd": dict(read="yes", write="yes", dic="yes", sh="no", osx="no"),
    "zsstock": dict(read=None, write=None, dic="yes", sh="no", osx="no"),
    "zsall": dict(read="yes", write="yes", dic="yes", sh="yes", osx="yes"),
}
NOREG = ["zsnoreg"]
WANT = {"zsblank": (1, 0), "zsempty": (1, 0), "zsyes": (1, 0), "zsno": (0, 0), "zscase": (0, 1), "zsjunk": (1, 0), "zswr": (1, 1),
        "zswrd": (1, 1), "zsstock": (1, 0), "zsall": (1, 1)}
WHY = {"zsblank": "both fields absent: BLANK MEANS ON for read, OFF for write", "zsempty": "both fields empty", "zsyes": "yes / no",
       "zsno": "no / no: read withdrawn", "zscase": "No / Yes: the tests ignore case", "zsjunk": "maybe / true: only the word no withdraws read, only yes grants write",
       "zswr": "yes / yes", "zswrd": "yes / yes", "zsstock": "absent / absent", "zsall": "yes / yes"}

# the files of the shared account.  data+dictionary files first, then the directory file and the directories
DYN = ["szd", "szown", "szmix", "szw", "szc", "szc2", "szcw", "szidx"]
SHARED_FILES = DYN + ["szdir", "utils", "utils.out"]


def S():
    return os.path.join(g.BOX, "group_accounts", "shared")


def acct_path(name):
    return os.path.join(g.BOX, "user_accounts", name)


def msg(n, *args):
    """The text of message N as the sandbox was built with it, the %n places filled."""
    p = os.path.join(g.SYS, "messages", str(n))
    if not os.path.exists(p):
        bail("the sandbox holds no message %d (%s)" % (n, p))
    with open(p, encoding="utf-8", errors="replace") as f:
        t = f.read().strip("\n")
    for i, a in enumerate(args, 1):
        t = t.replace("%%%d" % i, str(a))
    return t


def msg_rx(n):
    """A regular expression for message N with every %n place matching anything."""
    return re.sub(r"%\d", ".*", re.escape(msg(n)))


def squash(s):
    return re.sub(r"\s+", "", s)


def has_text(out, text):
    """TEXT is on a line of OUT, or - when the terminal wrapped a long message - in the lines joined with their white space taken out."""
    return any(text in ln for ln in out) or (len(squash(text)) > 12 and squash(text) in squash("".join(out)))


def has_rx(out, rx):
    return any(re.search(rx, ln) for ln in out)


def reg_record(name):
    a = ACCOUNTS[name]
    rec = [acct_path(name), "", g.GROUP, "", "", "", a["sh"], a["osx"], "", "yes", "yes", a["dic"]]
    if a["read"] is not None:
        rec += [a["read"], a["write"] or ""]
    return rec


def shared_reg(group="sdg_shared", suspended=False):
    lines = [S(), "The shared account", group, "", "SUSPENDED" if suspended else ""]
    g.put(os.path.join(g.SYS, "accounts", "shared"), "\n".join(lines) + "\n")


# ---- the probes ------------------------------------------------------------------------------------------------------------------------
# Ordinary programs, compiled in every fixture account by the administrator.  Each reads zs.args (written from here) in the account directory.

ZSOPEN = """\
* zsopen - opens names by NAME and says what happened (sandbox-shared.py)
   openseq 'zs.args' to a else crt 'SO noargs' ; stop
   loop
      readseq line from a else exit
      kind = field(line, '|', 1) ; nm = field(line, '|', 2) ; id = field(line, '|', 3)
      v = '<none>' ; ok = 1
      begin case
         case kind = 'O'
            open nm to f then
               read v from f, id else v = '<none>'
               crt 'SO O ':nm:' OK ':convert(@fm, '|', v)
               close f
            end else crt 'SO O ':nm:' NO'
         case kind = 'D'
            open 'DICT', nm to f then
               read v from f, id else v = '<none>'
               crt 'SO D ':nm:'.':id:' OK ':convert(@fm, '|', v)
               close f
            end else crt 'SO D ':nm:'.':id:' NO'
         case kind = 'S'
            openseq nm, id to f then
               crt 'SO S ':nm:' OK'
               close f
            end else crt 'SO S ':nm:' NO'
         case kind = 'X'
            deleteseq nm, id else ok = 0
            crt 'SO X ':nm:' ':(if ok then 'OK' else 'NO')
      end case
   repeat
   close a
   crt 'SO end'
end
"""

# kind|file|id|value.  P=1: the change is there afterwards (a write: the value is stored; a delete: the record is gone)
ZSWRITE = """\
* zswrite - tries a change and reads back what is there (sandbox-shared.py)
   dim m(2)
   openseq 'zs.args' to a else crt 'SW noargs' ; stop
   loop
      readseq line from a else exit
      kind = field(line, '|', 1) ; nm = field(line, '|', 2) ; id = field(line, '|', 3) ; val = field(line, '|', 4)
      ok = 1 ; p = 0 ; x = ''
      if kind = 'WD' then
         open 'DICT', nm to f else ok = -1
      end else
         open nm to f else ok = -1
      end
      if ok = 1 then
         begin case
            case kind = 'W' or kind = 'WD'
               write val to f, id on error ok = 0
               read x from f, id then p = (x = val) else p = 0
            case kind = 'WV'
               writev val to f, id, 2 on error ok = 0
               readv x from f, id, 2 then p = (x = val) else p = 0
            case kind = 'MW'
               mat m = val
               matwrite m to f, id on error ok = 0
               read x from f, id then p = 1 else p = 0
            case kind = 'DEL'
               delete f, id on error ok = 0
               read x from f, id then p = 0 else p = 1
            case kind = 'RD'
               read x from f, id then p = 1 else p = 0
         end case
      end
      w = 'OK'
      if ok = 0 then w = 'REFUSED'
      if ok = -1 then w = 'NOOPEN'
      crt 'SW ':kind:' ':nm:' ':id:' ':w:' P=':p
   repeat
   close a
   crt 'SW end'
end
"""

# ONE statement, no ON ERROR: a refusal is an error whose message shows, and the program stops there ("ONE done" is then NOT printed)
ZSONE = """\
* zsone - one change without ON ERROR (sandbox-shared.py)
   openseq 'zs.args' to a else crt 'ONE noargs' ; stop
   readseq line from a else crt 'ONE empty' ; stop
   close a
   kind = field(line, '|', 1) ; nm = field(line, '|', 2) ; id = field(line, '|', 3)
   crt 'ONE start ':kind
   begin case
      case kind = 'W'
         open nm to f else crt 'ONE noopen' ; stop
         write 'x' to f, id
      case kind = 'WD'
         open 'DICT', nm to f else crt 'ONE noopen' ; stop
         write 'D':@fm:'0' to f, id
      case kind = 'CLR'
         open nm to f else crt 'ONE noopen' ; stop
         clearfile f
      case kind = 'FC'
         open nm to f else crt 'ONE noopen' ; stop
         x = fcontrol(f, 7, 5)
   end case
   crt 'ONE done ':kind
end
"""

ZSIDX = """\
* zsidx - writes to an indexed shared file and asks the index (sandbox-shared.py)
   field.id = field(@sentence, ' ', 4)
   open 'szidx' to f else crt 'IX noopen' ; stop
   ok = 1
   write 'Paris' to f, 'ix-':field.id on error ok = 0
   selectindex 'CITY', 'Paris' from f to 5
   readlist l from 5 else l = ''
   crt 'IX write ':(if ok then 'OK' else 'REFUSED'):' list=':convert(@fm, ',', l)
end
"""

ZSHOLD = """\
* zshold - takes a record lock on a shared record by name and keeps it (sandbox-shared.py)
   open 'szd' to f else crt 'HD noopen' ; stop
   readu x from f, 'lk1' else x = ''
   crt 'HD got'
   sleep 12
   release f, 'lk1'
   crt 'HD done'
end
"""

ZSLK = """\
* zslk - meets that lock (sandbox-shared.py)
   open 'szd' to f else crt 'LK noopen' ; stop
   readu x from f, 'lk1' locked
      crt 'LK locked'
   end then
      crt 'LK got'
      release f, 'lk1'
   end else
      crt 'LK none'
      release f, 'lk1'
   end
   crt 'LK end'
end
"""

PROGS = {"zsopen": ZSOPEN, "zswrite": ZSWRITE, "zsone": ZSONE, "zsidx": ZSIDX, "zshold": ZSHOLD, "zslk": ZSLK}

ZSK = """\
$internal
program zsk
$catalog $zsk
$include keys.h
$include int$keys.h
   crt 'ZK admin=':kernel(K$ADMINISTRATOR, -1):' read=':kernel(K$SHARED.READ, -1):' write=':kernel(K$SHARED.WRITE, -1):' path=':@path
end
"""
# the gate withdrawn under an open file: the open file goes on being usable, a new open is refused
ZSFLIP = """\
$internal
program zsflip
$catalog $zsflip
$include keys.h
$include int$keys.h
   open 'szd' to f else crt 'FL first-open NO' ; stop
   crt 'FL first-open OK'
   void kernel(K$SHARED.READ, 0)
   v = ''
   read v from f, 'r1' then crt 'FL read-after-withdraw OK ':v else crt 'FL read-after-withdraw NO'
   open 'szd' to f2 then crt 'FL second-open OK' else crt 'FL second-open NO'
   crt 'FL gate ':kernel(K$SHARED.READ, -1)
end
"""
# what an INTERNAL program is exempt from (a record write) and what it is not (structure, in the kernel): kind|target
ZSINT = """\
$internal
program zsint
$catalog $zsint
$include keys.h
$include int$keys.h
   openseq 'zs.args' to a else crt 'IN noargs' ; stop
   loop
      readseq line from a else exit
      kind = field(line, '|', 1) ; tgt = field(line, '|', 2)
      ok = 1
      begin case
         case kind = 'IW'
            open tgt to f else ok = 0
            if ok then write 'internal' to f, 'zsintrec' on error ok = 0
         case kind = 'CF'
            create.file tgt dynamic on error ok = 0
         case kind = 'OSD'
            x = ospath(tgt, 5) ; if not(x) then ok = 0
         case kind = 'OSM'
            x = ospath(tgt, 13) ; if not(x) then ok = 0
         case kind = 'OSP'
            x = ospath(tgt, 14) ; if not(x) then ok = 0
      end case
      crt 'IN ':kind:' ':tgt:' ':(if ok then 'OK' else 'REFUSED')
   repeat
   close a
   crt 'IN end'
end
"""


def shared_fixer():
    s = S()
    lines = [
        "$internal",
        "   s = '%s'" % s,
        "   create.file s:'/voc' dynamic on error crt 'SHFIX create voc failed' ; stop",
        "   openpath s:'/voc' to v else crt 'SHFIX open voc failed' ; stop",
        "   openpath '%s/newvoc' to nv else crt 'SHFIX no newvoc' ; stop" % g.SYS,
        "   select nv to 11",
        "   loop",
        "      readnext id from 11 else exit",
        "      read rec from nv, id then write rec to v, id",
        "   repeat",
        "   close nv",
        "   write 'X' to v, '$command.stack'",
        "   for each nm in " + ":@fm:".join("'" + n + "'" for n in DYN),
        "      create.file s:'/':nm dynamic on error crt 'SHFIX create ':nm ; stop",
        "      create.file s:'/':nm:'.dic' dynamic on error crt 'SHFIX create dict ':nm ; stop",
        "      write 'F':@fm:nm:@fm:nm:'.dic' to v, nm",
        "   next nm",
        "   create.file s:'/szdir' directory on error crt 'SHFIX create szdir' ; stop",
        "   create.file s:'/szdir.dic' dynamic on error crt 'SHFIX create szdir.dic' ; stop",
        "   write 'F':@fm:'szdir':@fm:'szdir.dic' to v, 'szdir'",
        "   for each dn in 'utils':@fm:'utils.out':@fm:'bp':@fm:'bp.out':@fm:'szwork.bp':@fm:'cat':@fm:'privcat'",
        "      create.file s:'/':dn directory on error crt 'SHFIX create ':dn ; stop",
        "   next dn",
        "   write 'F':@fm:'utils':@fm:'szdir.dic' to v, 'utils'",
        "   write 'F':@fm:'utils.out':@fm:'szdir.dic' to v, 'utils.out'",
        # the entries that must be REFUSED
        "   write 'Q':@fm:'zsblank':@fm:'szown' to v, 'szq'",
        "   write 'F':@fm:'%s/zsblank/szown':@fm:'%s/zsblank/szown.dic' to v, 'szabs'" % (os.path.join(g.BOX, "user_accounts"), os.path.join(g.BOX, "user_accounts")),
        "   write 'N':@fm:'nosuchserver':@fm:'szd' to v, 'szn'",
        "   write 'V':@fm:'CA':@fm:'$listshared' to v, 'szv'",
        "   write 'F':@fm:'szd':@fm:'szd.dic':@fm:'compone' to v, 'szmulti'",
        "   write 'F':@fm:'voc':@fm:'voc.dic' to v, 'szvoc'",
        "   write 'F':@fm:'voc.dic':@fm:'szd.dic' to v, 'szvocdic'",
        "   write 'F':@fm:'szd.dic':@fm:'szd.dic' to v, 'szdictdata'",
        "   write 'F':@fm:'bp':@fm:'szdir.dic' to v, 'szbp'",
        "   write 'F':@fm:'bp.out':@fm:'szdir.dic' to v, 'szbpout'",
        "   write 'F':@fm:'szwork.bp':@fm:'szdir.dic' to v, 'szwork'",
        "   write 'F':@fm:'cat':@fm:'szdir.dic' to v, 'szcat'",
        "   write 'X':@fm:'privcat' to v, '$private.catalogue'",
        "   write 'F':@fm:'privcat':@fm:'szdir.dic' to v, 'szpriv'",
        "   write 'F':@fm:'szd':@fm:'szd.dic' to v, 'syscom'",
        "   write 'F':@fm:'szd':@fm:'szd.dic' to v, '$savedlists'",
        "   write 'F':@fm:'szd':@fm:'szd.dic' to v, '$hold'",
        "   write 'F':@fm:'szd':@fm:'szd.dic' to v, '_under'",
        "   write 'F':@fm:'szmix':@fm:'szmix.dic' to v, 'SZUP'",
        # the data
        "   openpath s:'/szd' to d else crt 'SHFIX open szd' ; stop",
        "   write 'alpha' to d, 'r1'",
        "   write 'beta' to d, 'r2'",
        "   write 'gamma' to d, 'r3'",
        "   write 'lock me' to d, 'lk1'",
        "   close d",
        "   openpath s:'/szd.dic' to dd else crt 'SHFIX open szd.dic' ; stop",
        "   write 'D':@fm:'1':@fm:'':@fm:'Field one':@fm:'10L':@fm:'S' to dd, 'szf'",
        "   write 'I':@fm:'@ID':@fm:'':@fm:'Ident':@fm:'10L':@fm:'S' to dd, 'szi'",
        "   close dd",
        "   openpath s:'/szown' to d else crt 'SHFIX open szown' ; stop",
        "   write 'shared-copy' to d, 'own1'",
        "   close d",
        "   openpath s:'/szmix' to d else crt 'SHFIX open szmix' ; stop",
        "   write 'mixed' to d, 'm1'",
        "   close d",
        "   openpath s:'/szdir' to d else crt 'SHFIX open szdir' ; stop",
        "   write 'a record of a directory file' to d, 'd1'",
        "   close d",
        "   openpath s:'/szw' to d else crt 'SHFIX open szw' ; stop",
        "   write 'orig' to d, 'w0'",
        "   for each acct in %s" % ":@fm:".join("'" + a + "'" for a in list(ACCOUNTS) + ["admin"]),
        "      write 'seed' to d, 'del-':acct",
        "      write 'seed' to d, 'wv-':acct",
        "   next acct",
        "   close d",
        "   openpath s:'/szw.dic' to dd else crt 'SHFIX open szw.dic' ; stop",
        "   write 'D':@fm:'1':@fm:'':@fm:'W':@fm:'10L':@fm:'S' to dd, 'szwd'",
        "   close dd",
        "   for each cn in 'szc':@fm:'szc2':@fm:'szcw'",
        "      openpath s:'/':cn to d else crt 'SHFIX open ':cn ; stop",
        "      write 'x' to d, 'c1'",
        "      write 'x' to d, 'c2'",
        "      write 'x' to d, 'c3'",
        "      close d",
        "   next cn",
        "   openpath s:'/szidx.dic' to dd else crt 'SHFIX open szidx.dic' ; stop",
        "   write 'D':@fm:'1':@fm:'':@fm:'City':@fm:'12L':@fm:'S' to dd, 'CITY'",
        "   close dd",
        "   openpath s:'/szidx' to d else crt 'SHFIX open szidx' ; stop",
        "   write 'Paris' to d, 'i1'",
        "   write 'Rome' to d, 'i2'",
        "   close d",
        "   openpath s:'/utils' to d else crt 'SHFIX open utils' ; stop",
        "   write \"   crt 'compiled from the shared account'\":@fm:'end' to d, 'prog1'",
        "   close d",
        "   close v",
        "   crt 'SHFIX done'",
        "end", ""]
    return "\n".join(lines)


def acct_fixer():
    ua = os.path.join(g.BOX, "user_accounts")
    names = ":@fm:".join("'" + n + "'" for n in list(ACCOUNTS) + NOREG)
    return "\n".join([
        "$internal",
        "   for each a in %s" % names,
        "      ap = '%s':@ds:a" % ua,
        "      openpath ap:@ds:'voc' to v else crt 'SHFIX no voc ':a ; stop",
        "      write 'V':@fm:'CA':@fm:'$zsk' to v, 'zsk'",
        "      write 'V':@fm:'CA':@fm:'$zsflip' to v, 'zsflip'",
        "      write 'V':@fm:'CA':@fm:'$zsint' to v, 'zsint'",
        "      write 'V':@fm:'CA':@fm:'$listshared' to v, 'list.shared'",
        "      for each nm in 'zsmine':@fm:'szown'",
        "         create.file ap:@ds:nm dynamic on error crt 'SHFIX create ':nm ; stop",
        "         create.file ap:@ds:nm:'.dic' dynamic on error crt 'SHFIX create dict ':nm ; stop",
        "         write 'F':@fm:nm:@fm:nm:'.dic' to v, nm",
        "         openpath ap:@ds:nm to d else crt 'SHFIX open ':nm ; stop",
        "         if nm = 'zsmine' then write 'mine1' to d, 'm1' else write 'account-copy' to d, 'own1'",
        "         close d",
        "      next nm",
        "      if a = 'zsstock' then delete v, 'syscom'",
        "      close v",
        "   next a",
        "   crt 'SHFIX done'",
        "end", ""])


def dump_src():
    files = ["szd", "szown", "szmix", "szw", "szc", "szc2", "szcw", "szidx", "szdir", "utils", "utils.out"]
    return "\n".join([
        "$internal", "$include keys.h",
        "   s = '%s'" % S(),
        "   fl = " + ":@fm:".join("'" + n + "'" for n in files),
        "   for fi = 1 to dcount(fl, @fm)",
        "      nm = fl<fi>",
        "      for part = 1 to 2",
        "         pn = nm ; lab = nm",
        "         if part = 2 then pn = nm:'.dic' ; lab = 'dic:':nm",
        "         openpath s:'/':pn to f then",
        "            select f to 9",
        "            n = 0",
        "            loop",
        "               readnext id from 9 else exit",
        "               n += 1",
        "               read r from f, id then crt 'SR ':lab:' ':id:' ':convert(@fm, '|', r) else crt 'SR ':lab:' ':id:' <unreadable>'",
        "            repeat",
        "            crt 'SF ':lab:' n=':n",
        "            close f",
        "         end else crt 'SF ':lab:' <nofile>'",
        "      next part",
        "   next fi",
        "   openpath s:'/szc' to f then",
        "      crt 'ST szc trigger=':fileinfo(f, FL$TRIGGER)",
        "      close f",
        "   end",
        "   openpath s:'/szidx' to f then",
        "      selectindex 'CITY', 'Paris' from f to 5",
        "      readlist l from 5 else l = ''",
        "      crt 'IX Paris=':convert(@fm, ',', l)",
        "      close f",
        "   end",
        "   crt 'DUMP end'",
        "end", ""])


# ---- helpers ------------------------------------------------------------------------------------------------------------------------

def dump():
    """The administrator's view of every shared file: (records, counts, extras), or None when the dump did not finish."""
    out = g.adm(["RUN bp zsdump"], internal=True)
    if not has_text(out, "DUMP end"):
        return None
    recs, counts, extra = {}, {}, {}
    for ln in out:
        m = re.match(r"^SR (\S+) (\S+) (.*)$", ln)
        if m:
            recs[(m.group(1), m.group(2))] = m.group(3)
        m = re.match(r"^SF (\S+) n=(\d+)$", ln)
        if m:
            counts[m.group(1)] = int(m.group(2))
        m = re.match(r"^(ST|IX) (.*)$", ln)
        if m:
            extra[m.group(1)] = m.group(2)
    return recs, counts, extra


def args_file(acct, lines):
    g.put(os.path.join(acct_path(acct), "zs.args"), "\n".join(lines) + "\n")


def run_prog(acct, prog, lines, admin=False):
    args_file(acct, lines)
    if admin:
        return g.sd(acct_path(acct), ["RUN bp " + prog], admin=True, account=acct)
    return g.plain(acct, ["RUN bp " + prog])


def so(out):
    """SO lines -> {(kind, name): ('OK', value) or ('NO', None)}"""
    d = {}
    for ln in out:
        m = re.match(r"^SO (\S) (\S+) (OK|NO)(?: (.*))?$", ln)
        if m:
            d[(m.group(1), m.group(2))] = (m.group(3), m.group(4))
    return d


def sw(out):
    """SW lines -> {(kind, file, id): (word, p)}"""
    d = {}
    for ln in out:
        m = re.match(r"^SW (\S+) (\S+) (\S+) (OK|REFUSED|NOOPEN) P=(\d+)$", ln)
        if m:
            d[(m.group(1), m.group(2), m.group(3))] = (m.group(4), m.group(5))
    return d


def zk(out):
    for ln in out:
        m = re.match(r"^ZK admin=(\d+) read=(\d+) write=(\d+) path=(.*)$", ln)
        if m:
            return int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4)
    return None


def zk_all(out):
    return [(int(m.group(2)), int(m.group(3)), m.group(4)) for m in (re.match(r"^ZK admin=(\d+) read=(\d+) write=(\d+) path=(.*)$", ln) for ln in out) if m]


def tree(path):
    """Every name below PATH (relative), for 'nothing was made / nothing was removed' rows."""
    names = []
    for dp, dn, fn in os.walk(path):
        for n in dn + fn:
            names.append(os.path.relpath(os.path.join(dp, n), path))
    return sorted(names)


def audit_off():
    path = os.path.join(g.SYS, "audit")
    try:
        if not os.path.exists(path):
            with open(path, "ab"):
                pass
        return os.path.getsize(path)
    except OSError:
        return None


def audit_new(off):
    try:
        with open(os.path.join(g.SYS, "audit"), "rb") as f:
            f.seek(off or 0)
            return f.read().decode("utf-8", errors="replace")
    except OSError:
        return None


def build(name):
    a = ACCOUNTS.get(name, dict(sh="no", osx="no"))
    g.EXTRA_FIXTURES[name] = (a["sh"], a["osx"])
    path = g.build_account(name)
    if name in ACCOUNTS:
        g.reg_write(name, reg_record(name))
    else:
        os.remove(os.path.join(g.SYS, "accounts", name))        # a directory with a VOC and NO register record
    return path


# ---- preparation -----------------------------------------------------------------------------------------------------------------------

def prepare_all():
    g.prepare()
    for nm, src in (("zsk", ZSK), ("zsflip", ZSFLIP), ("zsint", ZSINT)):
        g.put(os.path.join(g.SYS, "gpl.bp", nm), src)
    out = g.adm(["BASIC gpl.bp zsk zsflip zsint"], internal=True)
    row("the kernel probes zsk, zsflip and zsint compile", g.has(out, r"^Compiled 3 program\(s\) with no errors"), repr(out[-6:]))
    if not g.has(out, r"^Compiled 3 program\(s\) with no errors"):
        bail("the internal probes did not compile:\n" + "\n".join(out[-8:]))
    for n in list(ACCOUNTS) + NOREG:
        build(n)
    # the shared account: made with the register group the sandbox user is in, so that the administrator can sign on to it
    os.makedirs(S(), exist_ok=True)
    shared_reg(g.GROUP)
    g.put(os.path.join(g.SYS, "bp", "zsfixs"), shared_fixer())
    out = g.adm(["BASIC bp zsfixs", "RUN bp zsfixs"], internal=True)
    if not g.has(out, r"^SHFIX done$"):
        bail("the shared account was not built:\n" + "\n".join(out[-8:]))
    out = g.sd(S(), ["CREATE.INDEX szidx CITY", "BUILD.INDEX szidx CITY", "LIST.INDEX szidx"], admin=True, account="shared")
    say("    index set-up output: %r" % (out[-4:],))
    shared_reg("sdg_shared")                      # the delivered group: nobody the sandbox user is in
    g.put(os.path.join(g.SYS, "bp", "zsfixa"), acct_fixer())
    out = g.adm(["BASIC bp zsfixa", "RUN bp zsfixa"], internal=True)
    if not g.has(out, r"^SHFIX done$"):
        bail("the fixture accounts were not completed:\n" + "\n".join(out[-8:]))
    for n in ACCOUNTS:
        for pn, src in PROGS.items():
            g.put(os.path.join(acct_path(n), "bp", pn), src)
        out = g.sd(acct_path(n), ["BASIC bp " + " ".join(PROGS)], admin=True, account=n)
        if not g.has(out, r"^Compiled %d program\(s\) with no errors" % len(PROGS)):
            bail("the probes did not compile in %s:\n%s" % (n, "\n".join(out[-8:])))
    g.put(os.path.join(g.SYS, "bp", "zsdump"), dump_src())
    out = g.adm(["BASIC bp zsdump"], internal=True)
    if not g.has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("zsdump did not compile:\n" + "\n".join(out[-8:]))
    say("  [done] %d accounts, the shared account with %d files: %s" % (len(ACCOUNTS) + len(NOREG), len(SHARED_FILES), " ".join(SHARED_FILES)))


def controls():
    say("\n--- 0. controls: the sessions are ordinary, the shared fixture is what the rows assume --------------------------------------")
    r = zk(g.plain("zsblank", ["ZSK"]))
    row("0a: a plain session in zsblank is not an administrator (admin=0)", r is not None and r[0] == 0, repr(r))
    if r is None or r[0] != 0:
        bail("the plain session is an administrator (or printed nothing): every row below would be meaningless")
    r = zk(g.sd(acct_path("zsblank"), ["ZSK"], admin=True, account="zsblank"))
    row("0b: the same session with SDTEST_ADMIN=1 is an administrator (admin=1): the control that the switch works", r is not None and r[0] == 1, repr(r))
    d = dump()
    row("0c: the administrator sees the shared files as built: szd holds r1 = alpha, r2 = beta, r3 = gamma, lk1; szown holds own1 = shared-copy",
        d is not None and d[0].get(("szd", "r1")) == "alpha" and d[0].get(("szd", "r2")) == "beta" and d[0].get(("szd", "r3")) == "gamma"
        and d[1].get("szd") == 4 and d[0].get(("szown", "own1")) == "shared-copy", repr(d and (d[1], {k: v for k, v in d[0].items() if k[0] == "szd"})))
    if d is None:
        bail("zsdump printed no end line: the shared files cannot be inspected")
    row("0e: the administrator's CREATE.INDEX / BUILD.INDEX on szidx worked (the index CITY answers Paris = i1): without it the index refusals below could not be told from 'no such index'",
        "i1" in d[2].get("IX", ""), repr(d[2]))
    out = g.plain("zsblank", ["LOGTO shared", "ZSK"])
    r = zk(out)
    row("0d: LOGTO shared by an ordinary session is refused (the register group is sdg_shared and the user is not in it): the session is still in zsblank",
        r is not None and r[3].endswith("/zsblank") and not r[3].endswith("/shared"), repr((r, out[-4:])))


# ---- E. the gates as the loaders read the register ---------------------------------------------------------------------------------------

def gates_section():
    say("\n--- E. the loaders: shared.read is ON unless the field says no (a blank field is ON); shared.write is OFF unless it says yes ---")
    for name in ACCOUNTS:
        r = zk(g.plain(name, ["ZSK"]))
        want = WANT[name]
        row("E: %s (%s) -> read=%d write=%d, not an administrator" % (name, WHY[name], want[0], want[1]),
            r is not None and r[0] == 0 and (r[1], r[2]) == want, repr(r))
    r = zk(g.plain("zsblank", ["ZSK"]))
    row("E: THE BLANK-MEANS-ON ROW - a record that stops at field 12 (zsblank) gives read=1: a gate whose blank meant off would be a wall that is not one",
        r is not None and r[1] == 1 and r[2] == 0, repr(r))
    for name in ("zsno", "zsblank"):
        r = zk(g.sd(acct_path(name), ["ZSK"], admin=True, account=name))
        row("E: %s, the administrator: admin=1 (an administrator passes the kernel's write test whatever the gates say)" % name, r is not None and r[0] == 1, repr(r))


# ---- A. the lookup -----------------------------------------------------------------------------------------------------------------

def lookup_section():
    say("\n--- A. the lookup: an account with the gate opens a shared file by NAME; the account's own VOC always wins ----------------")
    base = [("O", "szd", "r1"), ("O", "szd", "r3")]
    for name in ACCOUNTS:
        if name == "zsstock":
            continue
        out = run_prog(name, "zsopen", ["%s|%s|%s" % t for t in base])
        d = so(out)
        read_on = WANT[name][0]
        got1 = d.get(("O", "szd"))
        if read_on:
            row("A: %s (%s): OPEN 'szd' succeeds and r1 reads alpha (not an administrator)" % (name, WHY[name]),
                got1 is not None and got1[0] == "OK" and has_text(out, "SO O szd OK alpha"), repr(out[-4:]))
        else:
            row("A: %s (%s): OPEN 'szd' takes its ELSE branch and reads nothing" % (name, WHY[name]),
                got1 is not None and got1[0] == "NO" and not has_text(out, "alpha"), repr(out[-4:]))

    say("  -- the name rules (zsblank, read ON)")
    # (kind, name, id, wanted, why): wanted is "NO" (the ELSE branch) or "OK <value>" (the open worked and the record read is <value>)
    cases = [
        ("O", "szd", "r1", "OK alpha", "the data file by its name"),
        ("O", "SZMIX", "m1", "OK mixed", "the name typed in upper case (the three folds are _voc_ref's)"),
        ("O", "szup", "m1", "OK mixed", "an entry written as SZUP (a NOCASE VOC folds it) found by a lower-case request"),
        ("O", "szown", "own1", "OK account-copy", "the account's OWN file of the same name wins over the shared one"),
        ("O", "szdir", "d1", "OK a record of a directory file", "a DIRECTORY file"),
        ("O", "utils", "prog1", "OK ", "a directory file that holds source (utils): not a guarded name"),
        ("O", "szq", "own1", "NO", "a Q-pointer entry in shared's VOC"),
        ("O", "szabs", "own1", "NO", "an F entry whose path is in ANOTHER account"),
        ("O", "szn", "r1", "NO", "an N entry"),
        ("O", "szv", "r1", "NO", "a V entry"),
        ("O", "szmulti", "r1", "NO", "a multifile entry"),
        ("O", "szd,compone", "r1", "NO", "name,component"),
        ("O", "szvoc", "r1", "NO", "an entry that names shared's own VOC"),
        ("O", "szvocdic", "r1", "NO", "an entry whose data part is shared's voc.dic"),
        ("O", "szdictdata", "r1", "NO", "an entry whose data part is a dictionary (szd.dic)"),
        ("O", "szbp", "r1", "NO", "an entry that names shared's bp directory"),
        ("O", "szbpout", "r1", "NO", "an entry that names bp.out"),
        ("O", "szwork", "r1", "NO", "an entry that names a .bp directory"),
        ("O", "szcat", "r1", "NO", "an entry that names shared's cat directory"),
        ("O", "szpriv", "r1", "NO", "an entry that names the directory $PRIVATE.CATALOGUE says is shared's catalogue"),
        ("O", "$savedlists", "r1", "NO", "a name that begins with $ (the account's own list file, never shared)"),
        ("O", "$hold", "r1", "NO", "$hold"),
        ("O", "_under", "r1", "NO", "a name that begins with an underscore"),
        ("O", "nosuchname", "r1", "NO", "a name nobody has (the control: the ELSE branch)"),
        ("D", "szd", "szf", "OK D", "OPEN DICT follows (the dictionary part of the entry)"),
        ("D", "szd", "szi", "OK I", "...and holds the I-type"),
        ("S", "szd", "r1", "NO", "OPENSEQ szd, r1 does NOT follow"),
        ("X", "szd", "r1", "NO", "DELETESEQ szd, r1 does NOT follow"),
    ]
    args = ["%s|%s|%s" % (k, n, i) for k, n, i, _w, _d in cases]
    out = run_prog("zsblank", "zsopen", args)
    d = so(out)
    row("A: the probe ran to its end line (a probe that stopped early cannot pass the rows below)", has_text(out, "SO end"), repr(out[-3:]))
    for kind, nm, rid, want, why in cases:
        got = d.get((kind, nm + "." + rid if kind == "D" else nm))     # a D line carries the record id (two dictionary records of one file)
        if want == "NO":
            ok = got is not None and got[0] == "NO"
        else:
            ok = got is not None and got[0] == "OK" and (got[1] or "").startswith(want[3:])
        row("A: zsblank, %s %s (%s) -> %s" % (kind, nm, why, want), ok, "got %r; output %r" % (got, out[:2]))
    say("  -- the stock names (zsstock: its VOC has no syscom; shared's VOC has a syscom entry)")
    out = run_prog("zsstock", "zsopen", ["O|syscom|r1", "O|szd|r1"])
    d = so(out)
    row("A: zsstock, OPEN 'syscom' (a name in the stock VOC) is NOT looked up in shared, though shared's VOC has an entry syscom", d.get(("O", "syscom")) == ("NO", None), repr(out[-3:]))
    row("A: ...the control: the same entry reached under a name that is not stock (szd) opens", d.get(("O", "szd")) is not None and d[("O", "szd")][0] == "OK", repr(out[-3:]))

    say("  -- the administrator does not follow shared; a suspended or missing shared account gives nothing")
    out = run_prog("zsblank", "zsopen", ["O|szd|r1"], admin=True)
    row("A: the administrator in zsblank: OPEN 'szd' is NOT answered from shared (SDSYS reaches the files with LOGTO shared; its own OPEN does not follow)",
        so(out).get(("O", "szd")) == ("NO", None), repr(out[-3:]))
    shared_reg("sdg_shared", suspended=True)
    out = run_prog("zsblank", "zsopen", ["O|szd|r1"])
    row("A: shared SUSPENDED in the register: zsblank's OPEN 'szd' is refused (suspension withdraws the by-name lookup)", so(out).get(("O", "szd")) == ("NO", None), repr(out[-3:]))
    reg = os.path.join(g.SYS, "accounts", "shared")
    hold = reg + ".hold"
    os.rename(reg, hold)
    try:
        out = run_prog("zsblank", "zsopen", ["O|szd|r1"])
        row("A: NO register record named shared: zsblank's OPEN 'szd' is refused", so(out).get(("O", "szd")) == ("NO", None), repr(out[-3:]))
        out = g.plain("zsblank", ["LIST.SHARED"])
        row("A: ...and LIST.SHARED says there is no shared account in service (11518)", has_text(out, msg(11518)), repr(out[-3:]))
    finally:
        os.rename(hold, reg)
    shared_reg("sdg_shared")
    out = run_prog("zsblank", "zsopen", ["O|szd|r1"])
    row("A: CONTROL: the register put back, zsblank opens szd again", so(out).get(("O", "szd")) is not None and so(out)[("O", "szd")][0] == "OK", repr(out[-3:]))

    say("  -- LIST.SHARED")
    out = g.plain("zsblank", ["LIST.SHARED"])
    shown = [ln for ln in out if re.match(r"^[a-z0-9._$-]+$", ln)]
    expect = {"szd", "szown", "szmix", "szdir", "utils", "utils.out", "szw", "szc", "szc2", "szcw", "szidx"}
    row("A: LIST.SHARED (zsblank) shows the names that can be opened, one to a line, and the count line (11519) at the end",
        expect <= set(shown) and has_rx(out, "^" + msg_rx(11519).replace(r".*", r"\d+") + "$"), repr(out[-14:]))
    refused = {"szq", "szabs", "szn", "szv", "szmulti", "szvoc", "szvocdic", "szdictdata", "szbp", "szbpout", "szwork", "szcat", "szpriv", "syscom", "$savedlists", "$hold", "_under"}
    row("A: ...and none of the refused entries is listed", not (refused & set(shown)), repr(sorted(refused & set(shown))))
    out = g.plain("zsno", ["LIST.SHARED"])
    row("A: LIST.SHARED in zsno says shared.read is off for it (11520) and lists nothing", has_text(out, msg(11520, "zsno")) and not has_text(out, "szd"), repr(out[-4:]))
    out = g.sd(acct_path("zsblank"), ["LIST.SHARED"], admin=True, account="zsblank")
    row("A: LIST.SHARED for the administrator shows what the accounts with the gate can reach", "szd" in out and has_rx(out, "^" + msg_rx(11519).replace(r".*", r"\d+") + "$"), repr(out[-6:]))
    out = g.plain("zsblank", ["LIST.SHARED surplus"])
    row("A: LIST.SHARED with an extra token is refused (2018) and lists nothing", has_text(out, "surplus") and "szd" not in out, repr(out[-3:]))

    say("  -- the audit line: one for each name in a session, none for a refusal")
    off = audit_off()
    run_prog("zsblank", "zsopen", ["O|szd|r1", "O|szd|r2", "O|szown|own1", "O|SZMIX|m1", "O|szq|own1", "O|szabs|own1"])
    new = audit_new(off)
    row("A: audit: szd opened twice in one session -> exactly ONE 'shared open file=szd' line", new is not None and new.count("shared open file=szd") == 1, repr(new and new[-300:]))
    row("A: ...a name the account owns (szown) is NOT audited as a shared open", new is not None and "shared open file=szown" not in new, "")
    row("A: ...the upper-case request is audited once under its lower-case name", new is not None and new.count("shared open file=szmix") == 1, "")
    row("A: ...a refused entry (szq, szabs) writes no line", new is not None and "file=szq" not in new and "file=szabs" not in new, "")
    off2 = audit_off()
    run_prog("zsblank", "zsopen", ["O|szd|r1"])
    new2 = audit_new(off2)
    row("A: ...a NEW session opens szd again: one more line", new2 is not None and new2.count("shared open file=szd") == 1, repr(new2 and new2[-200:]))
    off3 = audit_off()
    run_prog("zsno", "zsopen", ["O|szd|r1"])
    new3 = audit_new(off3)
    row("A: ...zsno (read off) writes none", new3 is not None and "shared open file=" not in new3, repr(new3 and new3[-200:]))

    say("  -- a record lock is shared between the sessions (the file is one file)")
    holder = Live(acct_path("zsblank"), "zsblank", ["RUN bp zshold"])
    time.sleep(4)
    out = g.plain("zsyes", ["RUN bp zslk"])
    holder.wait(25)
    txt = holder.text()
    row("A: the holder (zsblank) took the lock on szd/lk1 by name", "HD got" in txt, repr(txt[-300:]))
    row("A: a second account (zsyes) opening the same shared file by name is told the record is LOCKED", has_text(out, "LK locked") and has_text(out, "LK end"), repr(out[-4:]))
    holder.kill()
    out = g.plain("zsyes", ["RUN bp zslk"])
    row("A: CONTROL: once the holder has gone the same read takes the lock (LK got)", has_text(out, "LK got"), repr(out[-4:]))

    say("  -- the gate withdrawn under an open file")
    out = g.plain("zsblank", ["ZSFLIP"])
    row("A: an open shared file stays usable when shared.read is withdrawn (documented: it takes effect at the NEXT entry)",
        has_text(out, "FL first-open OK") and has_text(out, "FL read-after-withdraw OK alpha"), repr(out[-5:]))
    row("A: ...and a NEW open after the withdrawal is refused", has_text(out, "FL second-open NO") and has_text(out, "FL gate 0"), repr(out[-5:]))


class Live:
    def __init__(self, cwd, account, cmds):
        self.out = os.path.join(g.BOX, "live-%s-%s.out" % (account, RUN))
        env = g.env(False)
        self.fh = open(self.out, "w")
        self.p = subprocess.Popen([g.SD, "-a" + account], stdin=subprocess.PIPE, stdout=self.fh, stderr=subprocess.STDOUT, cwd=cwd, env=env, text=True)
        self.p.stdin.write("\nTERM 200,9999\n" + "".join(c + "\n" for c in cmds) + "OFF\n")
        self.p.stdin.flush()
        say("    > live %s: %s" % (account, " | ".join(cmds)))
        lives.append(self)

    def text(self):
        self.fh.flush()
        return g.ANSI.sub("", open(self.out, errors="replace").read())

    def wait(self, seconds):
        try:
            self.p.wait(timeout=seconds)
            return True
        except subprocess.TimeoutExpired:
            return False

    def kill(self):
        if self.p.poll() is None:
            self.p.kill()
            self.p.wait()
        try:
            self.fh.close()
        except OSError:
            pass


# ---- B. record rights ---------------------------------------------------------------------------------------------------------------

def rights_section():
    say("\n--- B. record rights: a write, a writev, a matwrite and a delete in a shared file need shared.write; a shared dictionary needs dict.edit too ---")
    before = dump()
    if before is None:
        bail("zsdump failed before section B")
    for name in ("zsblank", "zsempty", "zsyes", "zsjunk", "zswr", "zswrd", "zsall", "zscase"):
        read_on, write_on = WANT[name]
        lines = ["W|szw|w-%s|new" % name, "WV|szw|wv-%s|v2" % name, "MW|szw|m-%s|mm" % name, "DEL|szw|del-%s|" % name,
                 "W|zsmine|own-%s|mine" % name, "RD|szw|w0|", "RD|szd|r1|"]
        out = run_prog(name, "zswrite", lines)
        d = sw(out)
        word = "OK" if write_on else "REFUSED"
        pw = "1" if write_on else "0"
        if not read_on:
            row("B: %s (read off): the files cannot be opened at all, so nothing is written (NOOPEN)" % name,
                all(d.get(k, ("", ""))[0] == "NOOPEN" for k in (("W", "szw", "w-" + name), ("DEL", "szw", "del-" + name))), repr(out[:4]))
            continue
        row("B: %s (%s): the probe ran to its end line" % (name, WHY[name]), has_text(out, "SW end"), repr(out[-3:]))
        for k, label in (("W", "WRITE"), ("WV", "WRITEV"), ("MW", "MATWRITE"), ("DEL", "DELETE")):
            key = (k, "szw", {"W": "w-", "WV": "wv-", "MW": "m-", "DEL": "del-"}[k] + name)
            row("B: %s %s of a shared record -> %s, and the record %s afterwards" % (name, label, word, "has changed" if write_on else "is unchanged"),
                d.get(key) == (word, pw), "got %r" % (d.get(key),))
        row("B: %s: a record of its OWN file (zsmine) is written whatever the gates say (the control)" % name, d.get(("W", "zsmine", "own-" + name)) == ("OK", "1"), repr(d.get(("W", "zsmine", "own-" + name))))
        row("B: %s: READS are never refused (szw/w0 and szd/r1 are read)" % name, d.get(("RD", "szw", "w0")) == ("OK", "1") and d.get(("RD", "szd", "r1")) == ("OK", "1"), repr(out[-4:]))
    after = dump()
    recs = after[0] if after else {}
    row("B: the DISK, read by the administrator: only the writers' records are in szw (zswr, zswrd, zsall wrote; zsblank, zsempty, zsyes, zsjunk could not, and "
        "zscase has shared.write but no read, so it could not even open the file)",
        after is not None and all(("szw", "w-" + n) in recs for n in ("zswr", "zswrd", "zsall"))
        and not any(("szw", "w-" + n) in recs for n in ("zsblank", "zsempty", "zsyes", "zsjunk", "zscase")), repr(sorted(k[1] for k in recs if k[0] == "szw")))
    row("B: ...and the seeded records of the refused accounts are still there (del-zsblank, wv-zsyes = seed), those of the writers are gone / changed",
        ("szw", "del-zsblank") in recs and recs.get(("szw", "wv-zsyes")) == "seed" and ("szw", "del-zswr") not in recs and recs.get(("szw", "wv-zswr")) == "seed|v2",
        repr({k: v for k, v in recs.items() if k[0] == "szw" and ("zsblank" in k[1] or "zswr" in k[1])}))

    say("  -- the message: 11513 for a record, without ON ERROR; the dictionary needs shared.write FIRST and dict.edit second")
    for name, kind, nm, rid, want_msg, why in (
            ("zsblank", "W", "szw", "msg-1", 11513, "a record of a shared file without shared.write"),
            ("zsyes", "WD", "szw", "zsnew-yes", 11513, "a shared DICTIONARY with dict.edit but WITHOUT shared.write: shared.write is missing first"),
            ("zswr", "WD", "szw", "zsnew-wr", 11406, "a shared dictionary with shared.write but WITHOUT dict.edit"),
    ):
        out = run_prog(name, "zsone", ["%s|%s|%s" % (kind, nm, rid)])
        row("B: %s, %s: message %d and the program stops there" % (name, why, want_msg), has_text(out, msg(want_msg)) and not has_text(out, "ONE done"), repr(out[-4:]))
    out = run_prog("zswrd", "zsone", ["WD|szw|zsnew-wrd"])
    row("B: zswrd (shared.write AND dict.edit): the dictionary record is written (ONE done)", has_text(out, "ONE done WD"), repr(out[-3:]))
    out = run_prog("zswr", "zsone", ["W|szw|msg-wr"])
    row("B: zswr: the same write as zsblank's is not refused (ONE done)", has_text(out, "ONE done W"), repr(out[-3:]))
    d2 = dump()
    row("B: the DISK: the dictionary record exists for zswrd only (zsnew-wrd), not for zsyes or zswr",
        d2 is not None and ("dic:szw", "zsnew-wrd") in d2[0] and ("dic:szw", "zsnew-yes") not in d2[0] and ("dic:szw", "zsnew-wr") not in d2[0],
        repr(d2 and sorted(k for k in d2[0] if k[0] == "dic:szw")))

    say("  -- the verbs that write a file the user names ask the same question")
    for name, ok_expected in (("zsblank", False), ("zswr", True)):
        out = g.plain(name, ["COPY FROM zsmine TO szw m1,vcopy-%s" % name, "DELETE szw wv-%s NO.QUERY" % name])
        dd = dump()
        recs = dd[0] if dd else {}
        row("B: %s: COPY into a shared file %s" % (name, "writes the record" if ok_expected else "is refused and writes nothing"),
            dd is not None and ((("szw", "vcopy-" + name) in recs) == ok_expected), repr(out[-3:]))
        if not ok_expected:
            row("B: %s: the refusal says why (11513)" % name, has_text(out, msg(11513)), repr(out[-4:]))
        row("B: %s: DELETE of a shared record %s" % (name, "removes it" if ok_expected else "is refused and removes nothing"),
            dd is not None and ((("szw", "wv-" + name) in recs) == (not ok_expected)), repr(out[-3:]))

    say("  -- what a $internal program is exempt from: a RECORD write (S5), because the verbs that write a file the user named ask for themselves")
    args_file("zsblank", ["IW|szw"])
    out = g.plain("zsblank", ["ZSINT"])
    dd = dump()
    row("B: zsblank, an INTERNAL program writes a record of a shared file (exempt, as for the S.64 gates): IN IW OK and the record is on the disk",
        has_text(out, "IN IW szw OK") and dd is not None and ("szw", "zsintrec") in dd[0], repr(out[-3:]))

    say("  -- a plain LIST writes the compiled I-type back into a shared dictionary, whoever the user is (the S.64 exemption, an explicit row)")
    pre = dump()
    out = g.plain("zsyes", ["LIST szd szi NO.PAGE"])
    post = dump()
    n0 = len((pre[0].get(("dic:szd", "szi")) or "").split("|")) if pre else 0
    n1 = len((post[0].get(("dic:szd", "szi")) or "").split("|")) if post else 0
    row("B: zsyes (no shared.write) LISTs szd with the I-type szi: the listing shows the ids", has_rx(out, r"\br1\b") and has_rx(out, r"\br3\b"), repr(out[-6:]))
    row("B: ...and the compiled I-type was written back into shared's dictionary (the record grew from %d to %d fields) although zsyes may not write there" % (n0, n1),
        n1 > n0, repr((pre and pre[0].get(("dic:szd", "szi")), post and post[0].get(("dic:szd", "szi")))))


# ---- C. structure ----------------------------------------------------------------------------------------------------------------------

def structure_section():
    say("\n--- C. structure: clear, configure, index, trigger, delete, make, remove - SDSYS at a terminal only, whatever the account holds -----")
    for name in ("zsblank", "zswrd", "zsall"):
        out = run_prog(name, "zsone", ["CLR|szc|"])
        row("C: %s, CLEARFILE of a shared file from a program: message 11514 and the program stops there" % name, has_text(out, msg(11514)) and not has_text(out, "ONE done"), repr(out[-4:]))
        out = run_prog(name, "zsone", ["FC|szc|"])
        row("C: %s, FCONTROL(f, 7, 5) (a setting changed): message 11514" % name, has_text(out, msg(11514)) and not has_text(out, "ONE done"), repr(out[-4:]))
    post = dump()
    row("C: the DISK: szc still holds its three records and szc2, szcw are untouched", post is not None and post[1].get("szc") == 3 and post[1].get("szc2") == 3 and post[1].get("szcw") == 3,
        repr(post and post[1]))

    verbs = [
        ("zswrd", "CLEAR.FILE szc2", "CLEAR.FILE of a shared file"),
        ("zswrd", "CONFIGURE.FILE szc MINIMUM.MODULUS 7", "CONFIGURE.FILE"),
        ("zswrd", "CREATE.INDEX szw szwd", "CREATE.INDEX on the dictionary item szwd"),
        ("zswrd", "DELETE.INDEX szidx CITY", "DELETE.INDEX"),
        ("zswrd", "BUILD.INDEX szidx CITY", "BUILD.INDEX"),
        ("zswrd", "SET.TRIGGER szc zstrig ALL", "SET.TRIGGER"),
        ("zsall", "CLEAR.FILE szcw", "CLEAR.FILE by an account with every gate on"),
    ]
    for name, cmd, label in verbs:
        before_t = tree(S())
        before_d = dump()
        out = g.plain(name, [cmd])
        after_d = dump()
        after_t = tree(S())
        row("C: %s: %s (%s): nothing in the shared directory was made or removed" % (name, cmd, label), before_t == after_t, repr(set(before_t) ^ set(after_t)))
        row("C: %s: ...and no record count changed, no trigger was set, the index answers as before" % cmd,
            before_d is not None and after_d is not None and before_d[1] == after_d[1] and before_d[2] == after_d[2], repr((before_d and before_d[2], after_d and after_d[2])))
        row("C: %s: ...and the verb did run to a refusal (it did not stop at 'file not found'; the output is the refusal, not nothing)" % cmd,
            not has_text(out, msg(2019)) and len(out) > 0, repr(out[-3:]))
    before_t = tree(S())
    before_d = dump()
    out = g.plain("zsall", ["DELETE.FILE szc NO.QUERY"])
    row("C: zsall, DELETE.FILE szc: the verb reads the account's OWN VOC, which does not hold shared's names, so nothing is found and nothing happens (the DISK is as before)",
        before_t == tree(S()) and before_d is not None and before_d[1] == (dump() or (None, None))[1], repr(out[-3:]))

    say("  -- an INTERNAL program is not exempt from a structure change; the administrator is (the control)")
    S_ = S()
    g.put(os.path.join(S_, "szdel.txt"), "delete me\n")
    os.makedirs(os.path.join(S_, "szdeldir"), exist_ok=True)
    lines = ["OSD|%s/szdel.txt" % S_, "OSM|%s/szmkdir" % S_, "OSP|%s/szmkpath/a/b" % S_, "CF|%s/zsnewfile" % S_, "OSD|%s/szdeldir" % S_]
    for name in ("zsall", "zsblank"):
        args_file(name, lines)
        out = g.plain(name, ["ZSINT"])
        row("C: %s, an INTERNAL program: OSPATH delete / mkdir / mkpath and CREATE.FILE inside shared all answer REFUSED" % name,
            has_text(out, "IN OSD %s/szdel.txt REFUSED" % S_) and has_text(out, "IN OSM %s/szmkdir REFUSED" % S_) and has_text(out, "IN OSP %s/szmkpath/a/b REFUSED" % S_)
            and has_text(out, "IN CF %s/zsnewfile REFUSED" % S_) and has_text(out, "IN OSD %s/szdeldir REFUSED" % S_), repr(out[-7:]))
        row("C: %s: ...the DISK agrees: the file is still there, the directory is not made, nothing new was created" % name,
            os.path.exists(os.path.join(S_, "szdel.txt")) and os.path.isdir(os.path.join(S_, "szdeldir")) and not os.path.exists(os.path.join(S_, "szmkdir"))
            and not os.path.exists(os.path.join(S_, "szmkpath")) and not os.path.exists(os.path.join(S_, "zsnewfile")), "")
    args_file("zsall", lines)
    out = g.sd(acct_path("zsall"), ["ZSINT"], admin=True, account="zsall")
    row("C: CONTROL - the administrator, the same program: every one of them is OK", all(has_text(out, "IN %s %s OK" % (k, t)) for k, t in (
        ("OSD", "%s/szdel.txt" % S_), ("OSM", "%s/szmkdir" % S_), ("OSP", "%s/szmkpath/a/b" % S_), ("CF", "%s/zsnewfile" % S_), ("OSD", "%s/szdeldir" % S_))), repr(out[-7:]))
    row("C: ...and the DISK shows it: szdel.txt is gone, szmkdir and szmkpath/a/b exist, zsnewfile was made",
        not os.path.exists(os.path.join(S_, "szdel.txt")) and os.path.isdir(os.path.join(S_, "szmkdir")) and os.path.isdir(os.path.join(S_, "szmkpath", "a", "b"))
        and (os.path.exists(os.path.join(S_, "zsnewfile")) or os.path.exists(os.path.join(S_, "zsnewfile.dic"))), "")
    for p in ("szmkdir", "szmkpath", "zsnewfile", "szdeldir"):
        full = os.path.join(S_, p)
        if os.path.isdir(full):
            shutil.rmtree(full, ignore_errors=True)
        elif os.path.exists(full):
            os.remove(full)

    say("  -- the administrator at a terminal MAY change the structure (the control for every refusal above)")
    # 18 Oct 26: the first run was refused "User not allowed in requested account": the sandbox user plays the administrator but is not in sdg_shared
    # (on a real install sdsys is).  The register group is the sandbox user's own group for this one sign-on, as the fixture build does.
    shared_reg(g.GROUP)
    out = g.sd(S(), ["CLEAR.FILE szc2", "Y"], admin=True, account="shared")
    shared_reg("sdg_shared")
    dd = dump()
    row("C: CONTROL - the administrator signed on to shared: CLEAR.FILE szc2 empties it (count 0)", dd is not None and dd[1].get("szc2") == 0, repr((out[-3:], dd and dd[1].get("szc2"))))

    say("  -- the INDEX is maintained by a shared.write user's WRITE (the refusals above do not reach _ak)")
    out = g.plain("zswr", ["RUN bp zsidx zswr"])
    dd = dump()
    row("C: zswr writes ix-zswr = Paris to the indexed shared file szidx and the index (asked in the same program) lists it", has_rx(out, r"^IX write OK list=.*ix-zswr"), repr(out[-3:]))
    row("C: ...the DISK: the administrator's own SELECTINDEX shows i1 and ix-zswr under Paris", dd is not None and "ix-zswr" in dd[2].get("IX", "") and "i1" in dd[2].get("IX", ""), repr(dd and dd[2]))
    out = g.plain("zsyes", ["RUN bp zsidx zsyes"])
    row("C: zsyes (no shared.write): the same write is refused and the index does not list ix-zsyes", has_rx(out, r"^IX write REFUSED") and not has_text(out, "ix-zsyes"), repr(out[-3:]))


# ---- D. compile -----------------------------------------------------------------------------------------------------------------------

def compile_section():
    say("\n--- D. BASIC writes its object by name: a user with bp.edit and shared.read must not compile INTO the shared account ---------------")
    obj = os.path.join(S(), "utils.out", "prog1")
    if os.path.exists(obj):
        os.remove(obj)
    out = g.plain("zsyes", ["BASIC utils prog1"])
    row("D: zsyes (bp.edit yes, shared.write no): BASIC utils prog1 is refused with 11513", has_text(out, msg(11513)), repr(out[-4:]))
    row("D: ...and no object was written (the DISK: utils.out/prog1 does not exist)", not os.path.exists(obj), repr(os.listdir(os.path.join(S(), "utils.out"))))
    out = g.plain("zswr", ["BASIC utils prog1"])
    row("D: CONTROL - zswr (shared.write yes): the same compile runs", g.has(out, r"^Compiled 1 program\(s\) with no errors"), repr(out[-4:]))
    row("D: ...and the object is on the disk (utils.out/prog1)", os.path.exists(obj), repr(os.listdir(os.path.join(S(), "utils.out"))))


# ---- L. LOGTO -------------------------------------------------------------------------------------------------------------------------

def logto_section():
    say("\n--- L. LOGTO: the gates are the account the session is IN; a LOGTO by path has no register record, so read is OFF ----------------")
    out = g.plain("zsno", ["LOGTO zsblank", "ZSK"])
    r = zk(out)
    row("L: signed on to zsno (read off), LOGTO zsblank: the session reports read=1 (a blank field is ON)", r is not None and (r[1], r[2]) == (1, 0), repr(out[-4:]))
    out = run_prog("zsno", "zsopen", ["O|szd|r1"])
    row("L: ...(control) zsno itself still cannot open szd", so(out).get(("O", "szd")) == ("NO", None), repr(out[-3:]))
    args_file("zsblank", ["O|szd|r1"])
    out = g.plain("zsblank", ["LOGTO zsno", "ZSK"])
    r = zk(out)
    row("L: signed on to zsblank (read on), LOGTO zsno: read=0 (zsblank's grant does not follow the person)", r is not None and (r[1], r[2]) == (0, 0), repr(out[-4:]))
    out = g.plain("zsblank", ["ZSK", "LOGTO zswr", "ZSK", "LOGTO zsno", "ZSK"])
    row("L: zsblank, then zswr, then zsno: (read, write) = (1,0) (1,1) (0,0)", [(a, b) for a, b, _ in zk_all(out)] == [(1, 0), (1, 1), (0, 0)], repr(zk_all(out)))
    out = g.sd(acct_path("zsall"), ["LOGTO %s" % acct_path("zsnoreg"), "ZSK"], account="zsall")
    r = zk(out)
    # 18 Oct 26: the first run showed LOGTO to a path with no register record is REFUSED ("User not allowed in requested account", the group test
    # that long predates S.66), not entered with the gates off.  The row now says what happens: the refusal, and the session still in zsall with zsall's own gates.
    row("L: zsall (os.execute yes) LOGTO the PATH of zsnoreg, a directory with a VOC and NO register record: refused, and the session stays in zsall with its own gates (1,1)",
        r is not None and has_text(out, "User not allowed in requested account") and (r[1], r[2]) == (1, 1) and r[3].endswith("/zsall"), repr(out[-4:]))
    # 28 Oct 26, S.87: OPTION STACKED.ACCOUNT is gone; the control that remains says an EXECUTEd LOGTO stays where it went
    progs = {}
    for acct, other in (("zsno", "zsblank"), ("zsblank", "zsno")):
        prog = "zsst%s%s" % (acct[2:], RUN)
        progs[acct] = prog
        g.put(os.path.join(acct_path(acct), "bp", prog), "\n".join([
            "   execute 'LOGTO %s'" % other, "   crt 'PATH ':@path", "   execute 'ZSK' capturing zk", "   crt 'ZKOUT ':trim(zk)", "end", ""]))
        out = g.plain(acct, ["BASIC bp " + prog])
        row("L: setup - %s's stacked-account program compiled" % acct, g.has(out, r"^Compiled 1 program\(s\) with no errors"), repr(out[-3:]))

    def result(o):
        path = next((ln[5:].strip() for ln in o if ln.startswith("PATH ")), None)
        m = next((re.search(r"read=(\d+) write=(\d+)", ln) for ln in o if ln.startswith("ZKOUT ")), None)
        return path, ((int(m.group(1)), int(m.group(2))) if m else None)
    for acct, other in (("zsno", "zsblank"), ("zsblank", "zsno")):
        out = g.plain(acct, ["RUN bp " + progs[acct]])
        path, rw = result(out)
        row("L: CONTROL, no option: after EXECUTE 'LOGTO %s' the session STAYS in %s with %s's gates %s" % (other, other, other, WANT[other]),
            path is not None and path.endswith("/" + other) and rw == WANT[other], repr((path, rw)))
    for acct in progs:
        for d in ("bp", "bp.out"):
            p = os.path.join(acct_path(acct), d, progs[acct])
            if os.path.exists(p):
                os.remove(p)


# ---------------------------------------------------------------------------------------------------------------------------------------

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-shared.py <dir> [--build] [--sections=gates,lookup,rights,structure,compile,logto]")
    g.BOX = os.path.abspath(args[0])
    g.SYS = os.path.join(g.BOX, "sys")
    g.SD = os.path.join(g.SYS, "bin", "sd")
    sections = next((set(a.split("=", 1)[1].split(",")) for a in sys.argv[1:] if a.startswith("--sections=")), None)

    def run(part):
        return sections is None or part in sections
    say("sandbox-shared: sandbox %s%s" % (g.BOX, "" if sections is None else "  (parts: %s)" % ",".join(sorted(sections))))
    say("sandbox-shared: tree    %s" % os.path.dirname(HERE))
    say("sandbox-shared: user %s, group %s (the register group of every fixture account; shared's is sdg_shared)" % (g.USER, g.GROUP))
    if "--build" in sys.argv:
        if os.path.exists(g.BOX) and os.listdir(g.BOX):
            bail("%s is not empty" % g.BOX)
        r = subprocess.run([sys.executable, g.TOOL, g.BOX, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-shared: built, bootstrap passed")
    elif not os.path.isfile(g.SD):
        bail("%s holds no built sandbox (use --build, or point it at one)" % g.BOX)
    subprocess.run([sys.executable, g.TOOL, g.BOX, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    say("\n--- preparation: a CPROC that is not the install build, the probes, the shared account, the fixture accounts ---------------------")
    audit_off()
    prepare_all()
    controls()
    try:
        for name, section in (("gates", gates_section), ("lookup", lookup_section), ("rights", rights_section), ("structure", structure_section),
                              ("compile", compile_section), ("logto", logto_section)):
            if run(name):
                section()
    finally:
        for lv in lives:
            lv.kill()

    say("")
    say("sandbox-shared: %d passed, %d failed" % (passed, failed))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
