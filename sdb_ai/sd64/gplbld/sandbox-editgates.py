#!/usr/bin/env python3
#
# sandbox-editgates.py - the edit gates voc.edit, bp.edit and dict.edit (S.64, the owner's request of 17 Oct 2026).  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-editgates.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or absent);
# without it <dir> must already be built.  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 17 Oct 26 dm  New.  Register fields 10 to 12 (ACC$VOC.EDIT, ACC$BP.EDIT, ACC$DICT.EDIT), K_VOC_EDIT 121 to K_EDIT_OS_OK 126, the user
#               table's gates word; op_dio3.c edit_refusal() before WRITE, WRITEV, DELETE and CLEARFILE; op_seqio.c OPENSEQ read only and
#               DELETESEQ refused for a path in a guarded file; the BASIC verbs ED, SED, IDE, CED, COPY, COPYP, DELETE, CLEAR.FILE, CNAME,
#               DELETE.FILE ask; BASIC, CATALOG, DELETE.CATALOG and DECATALOG need bp.edit; LOGIN and the API server load the gates at sign-on.
# END-HISTORY
#
# It uses sandbox-gates.py's way of making ordinary sessions in fixture accounts, by loading that file.  Every fixture account holds the
# same things, built by the administrator: a VOC; a data file zzd with a dictionary holding the record zzf; a second data file zzd2
# whose dictionary the probe clears; a program file bp holding the record zzold; a second one, zzwork.bp, and the object file bp.out;
# and a program, zzprobe, compiled by the administrator (the account cannot compile it itself when it has not bp.edit).
#
# THE INSTRUMENT.  zzprobe is an ORDINARY program (not $internal), so the kernel's test of a WRITE, a WRITEV, a DELETE and a CLEARFILE is
# what is under test.  For each change it tries, it prints "PR <what> OK|REFUSED P=<0|1>": the word is what the statement reported, P is
# whether the change is there afterwards, read back by the same program (1 = the record was written / is gone).  A verdict is the word
# AND P, so a statement that said OK and changed nothing, or said REFUSED and changed something, fails.  The sequential file routes
# print only the word, because the program cannot see a file name: the disk is read from here.  The controls are the account with all
# three gates on, the administrator in an account with them off, and every ordinary file in the same program, which must always work.

import importlib.util
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ptydrive import PtySession  # noqa: E402
spec = importlib.util.spec_from_file_location("sandbox_gates", os.path.join(HERE, "sandbox-gates.py"))
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
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
    say("sandbox-editgates: CANNOT RUN - " + msg)
    sys.exit(2)


# account -> (voc, bp, dict) as the register is to say it: "yes", "no", or None for a record that has no such field at all
ACCOUNTS = {
    "zzoff": ("no", "no", "no"),
    "zzvoc": ("yes", "no", "no"),
    "zzbp": ("no", "yes", "no"),
    "zzdict": ("no", "no", "yes"),
    "zzall": ("yes", "yes", "yes"),
    "zzblank": (None, None, None),
    "zzadmin": ("no", "no", "no"),      # the administrator works in it; its own gates are off
}
# accounts for the LOGTO section: A signs on with the gates on, B has them off, C on, D off
LOGTO_ACCOUNTS = {"zzlga": ("yes", "yes", "yes"), "zzlgb": ("no", "no", "no"), "zzlgc": ("yes", "yes", "yes"), "zzlgd": ("no", "no", "no")}
# accounts for EDIT, the external-editor verb, which needs a terminal and OS.EXECUTE before it looks at the file: os-on, gates off / bp on
EDIT_ACCOUNTS = {"zzeo": ("no", "no", "no"), "zzeo2": ("no", "yes", "no")}
FIELDS = dict(ACCOUNTS, **LOGTO_ACCOUNTS, **EDIT_ACCOUNTS)
WANT = {a: tuple(v == "yes" for v in f) for a, f in FIELDS.items()}      # may it change a (voc, bp, dict)?

# (name, kind index into (voc, bp, dict), statement, read-back that leaves p = 1 when the change is there)
CHANGES = [
    ("voc-write", 0, "write 'X' to v, 'zzp1' on error ok = @false", "read x from v, 'zzp1' then p = 1 else p = 0"),
    ("voc-writev", 0, "writev 'Y' to v, 'zzvrec2', 2 on error ok = @false", "readv x from v, 'zzvrec2', 2 then p = (x = 'Y') else p = 0"),
    ("voc-delete", 0, "delete v, 'zzvrec' on error ok = @false", "read x from v, 'zzvrec' then p = 0 else p = 1"),
    ("dict-write", 2, "write 'D':@fm:'0' to dd, 'zzp2' on error ok = @false", "read x from dd, 'zzp2' then p = 1 else p = 0"),
    ("dict-delete", 2, "delete dd, 'zzf' on error ok = @false", "read x from dd, 'zzf' then p = 0 else p = 1"),
    ("dict-clear", 2, "clearfile dd2 on error ok = @false", "select dd2 to 9 ; readnext x from 9 then p = 0 else p = 1"),
    ("bp-write", 1, "write 'x' to b, 'zzp3' on error ok = @false", "read x from b, 'zzp3' then p = 1 else p = 0"),
    ("bp-delete", 1, "delete b, 'zzold' on error ok = @false", "read x from b, 'zzold' then p = 0 else p = 1"),
    ("wk-write", 1, "write 'x' to w, 'zzp4' on error ok = @false", "read x from w, 'zzp4' then p = 1 else p = 0"),
    ("obj-write", 1, "write 'x' to bo, 'zzp5' on error ok = @false", "read x from bo, 'zzp5' then p = 1 else p = 0"),
]
# ordinary files in the same program: these must work for everybody
CONTROLS = [
    ("data-write", "write 'X' to d, 'zzp6' on error ok = @false", "read x from d, 'zzp6' then p = 1 else p = 0"),
    ("data-delete", "delete d, 'zzdr' on error ok = @false", "read x from d, 'zzdr' then p = 0 else p = 1"),
]

PROBE = "\n".join(
    ["* zzprobe - tries each kind of change and says what happened (sandbox-editgates.py)",
     "   open 'voc' to v else crt 'PR setup voc' ; stop",
     "   open 'zzd' to d else crt 'PR setup data' ; stop",
     "   open 'DICT', 'zzd' to dd else crt 'PR setup dict' ; stop",
     "   open 'DICT', 'zzd2' to dd2 else crt 'PR setup dict2' ; stop",
     "   open 'bp' to b else crt 'PR setup bp' ; stop",
     "   open 'zzwork.bp' to w else crt 'PR setup work' ; stop",
     "   open 'bp.out' to bo else crt 'PR setup bp.out' ; stop"]
    + sum([["   ok = @true", "   " + stmt, "   " + chk, "   crt 'PR %s ':(if ok then 'OK' else 'REFUSED'):' P=':p" % name]
           for name, _k, stmt, chk in CHANGES] +
          [["   ok = @true", "   " + stmt, "   " + chk, "   crt 'PR %s ':(if ok then 'OK' else 'REFUSED'):' P=':p" % name]
           for name, stmt, chk in CONTROLS], []) +
    # sequential files: the record form and the pathname form into the program file, then a delete of a file in it
    ["   ok = @true",
     "   openseq 'bp', 'zzseq1' to f then null else null",
     "   writeseq 'seq record form' to f else ok = @false",
     "   closeseq f",
     "   crt 'PR seq-record ':(if ok then 'OK' else 'REFUSED')",
     "   ok = @true",
     "   openseq 'bp/zzseq2' to f then null else null",
     "   writeseq 'seq path form' to f else ok = @false",
     "   closeseq f",
     "   crt 'PR seq-path ':(if ok then 'OK' else 'REFUSED')",
     "   ok = @true",
     "   openseq 'zzseq3' to f then null else null",
     "   writeseq 'seq outside the guarded files' to f else ok = @false",
     "   closeseq f",
     "   crt 'PR seq-control ':(if ok then 'OK' else 'REFUSED')",
     "   ok = @true",
     "   deleteseq 'bp', 'zzseqold' else ok = @false",
     "   crt 'PR seq-delete ':(if ok then 'OK' else 'REFUSED')",
     "   call !oscopy('inside.txt', 'bp/zzcopy', 1, st)",
     "   crt 'PR oscopy ':(if st = 0 then 'OK' else 'REFUSED')",
     "   call !ioscopy('inside.txt', 'bp/zzicopy', st)",
     "   crt 'PR ioscopy ':(if st = 0 then 'OK' else 'REFUSED')",
     "   call !oscopy('inside.txt', 'zzcopy2', 1, st)",
     "   crt 'PR oscopy-control ':(if st = 0 then 'OK' else 'REFUSED')",
     "end", ""])


# The kernel's own answers, asked by an INTERNAL program (a user program cannot call KERNEL): the three gates as the session holds
# them, K$EDIT.OK and K$EDIT.KIND for names of each kind, K$EDIT.OS.OK for OS paths.  Catalogued as a VOC verb in every account.
EGK = "\n".join([
    "$internal", "program zzegk", "$catalog $zzegk", "$include keys.h", "$include int$keys.h",
    "   crt 'EG gates voc=':kernel(K$VOC.EDIT, -1):' bp=':kernel(K$BP.EDIT, -1):' dict=':kernel(K$DICT.EDIT, -1)",
    "   crt 'EG ok voc=':kernel(K$EDIT.OK, 'x/voc'):' dict=':kernel(K$EDIT.OK, 'x/y.dic'):' bp=':kernel(K$EDIT.OK, 'x/bp')"
    ":' bpout=':kernel(K$EDIT.OK, 'x/bp.out'):' sfx=':kernel(K$EDIT.OK, 'x/z.bp'):' sfxout=':kernel(K$EDIT.OK, 'x/z.bp.out')"
    ":' vocdic=':kernel(K$EDIT.OK, 'x/voc.dic'):' slash=':kernel(K$EDIT.OK, 'x/bp/'):' upper=':kernel(K$EDIT.OK, 'x/BP')"
    ":' other=':kernel(K$EDIT.OK, 'x/data'):' lookalike=':kernel(K$EDIT.OK, 'x/vocabulary'):' empty=':kernel(K$EDIT.OK, '')",
    "   crt 'EG kind voc=':kernel(K$EDIT.KIND, 'x/voc'):' dict=':kernel(K$EDIT.KIND, 'x/y.dic'):' bp=':kernel(K$EDIT.KIND, 'x/bp')"
    ":' bpout=':kernel(K$EDIT.KIND, 'x/bp.out'):' sfx=':kernel(K$EDIT.KIND, 'x/z.bp'):' vocdic=':kernel(K$EDIT.KIND, 'x/voc.dic')"
    ":' other=':kernel(K$EDIT.KIND, 'x/data'):' empty=':kernel(K$EDIT.KIND, '')",
    "   crt 'EG os bp=':kernel(K$EDIT.OS.OK, 'bp/x'):' bpout=':kernel(K$EDIT.OS.OK, 'bp.out/x'):' deep=':kernel(K$EDIT.OS.OK, 'sub/bp/y')"
    ":' dic=':kernel(K$EDIT.OS.OK, 'zzd.dic/%0'):' voc=':kernel(K$EDIT.OS.OK, 'voc/%0'):' plain=':kernel(K$EDIT.OS.OK, 'inside.txt')"
    ":' sub=':kernel(K$EDIT.OS.OK, 'sub/y'):' dotdot=':kernel(K$EDIT.OS.OK, 'sub/../bp/y'):' empty=':kernel(K$EDIT.OS.OK, '')",
    "end", ""])


# zzchk: where things stand after the verbs ran.  An ORDINARY program: reading is never gated.  "CK <label> <n>": n is 1 / 0 for a record
# or a file that is / is not there, a count for a count, -1 when the file it would read has gone (renamed or deleted).
CHECKS = [
    ("voc-copy", "v", "read x from v, 'zzdrcopy' then p = 1 else p = 0"),
    ("voc-zzvrec", "v", "read x from v, 'zzvrec' then p = 1 else p = 0"),
    ("voc-zzmoved", "v", "read x from v, 'zzmoved' then p = 1 else p = 0"),
    ("voc-zzwork3", "v", "read x from v, 'zzwork3.bp' then p = 1 else p = 0"),
    ("voc-zzbas", "v", "read x from v, 'zzbas' then p = 1 else p = 0"),
    ("voc-zzprobe", "v", "read x from v, 'zzprobe' then p = 1 else p = 0"),
    ("voc-zzdbp", "v", "read x from v, 'zzd4.bp' then p = 1 else p = 0"),
    ("voc-zzed", "v", "read x from v, 'zzed' then p = 1 else p = 0"),
    ("voc-zzedv1", "v", "read x from v, 'zzedv1' then p = 1 else p = 0"),
    ("voc-zzedv2", "v", "read x from v, 'zzedv2' then p = 1 else p = 0"),
    ("voc-zzcat", "v", "read x from v, 'zzcat' then p = 1 else p = 0"),
    ("dict-copy", "dd", "read x from dd, 'zzdcopy' then p = 1 else p = 0"),
    ("dict-zzf", "dd", "read x from dd, 'zzf' then p = 1 else p = 0"),
    ("dict-zzq", "dd", "read x from dd, 'zzq' then p = 1 else p = 0"),
    ("dict-zzqb", "dd", "read x from dd, 'zzqb' then p = 1 else p = 0"),
    ("dict-zzed2", "dd", "read x from dd, 'zzed2' then p = 1 else p = 0"),
    ("dict2-count", "dd2", "COUNT dd2"),
    ("bp-copy", "b", "read x from b, 'zzbpcopy' then p = 1 else p = 0"),
    ("bp-zzold", "b", "read x from b, 'zzold' then p = 1 else p = 0"),
    ("bp-zzed3", "b", "read x from b, 'zzed3' then p = 1 else p = 0"),
    ("bp-zzmv", "b", "read x from b, 'zzmv' then p = 1 else p = 0"),
    ("work-count", "w", "COUNT w"),
    ("data-ok", "d", "read x from d, 'zzdr' then p = 1 else p = 0"),
    ("d3-dict-exists", "dd3", "p = 1"),
    ("work2-exists", "w2", "p = 1"),
]
# zzrec: the text of the records the full-screen editors are given.  "REC <what> <text, fields joined by |>"
REC = "\n".join(
    ["* zzrec - the text of the records the editors are given (sandbox-editgates.py)",
     "   open 'voc' to v else stop", "   open 'bp' to b else stop", "   open 'DICT', 'zzd' to dd else stop"]
    + sum([["   read x from %s, '%s' then crt 'REC %s ':convert(@fm, '|', x) else crt 'REC %s <absent>'" % (fv, rid, label, label)]
           for label, fv, rid in (("voc-zzvrec2", "v", "zzvrec2"), ("voc-zzvrec3", "v", "zzvrec3"), ("bp-zzold", "b", "zzold"),
                                  ("bp-zzold2", "b", "zzold2"), ("dict-zzf", "dd", "zzf"), ("dict-zzf2", "dd", "zzf2"))], []) + ["end", ""])


def chk_lines(label, fv, stmt):
    if stmt.startswith("COUNT "):
        body = ["      p = 0", "      select %s to 9" % fv, "      loop", "         readnext x from 9 else exit", "         p += 1", "      repeat"]
    else:
        body = ["      p = 0", "      " + stmt]
    return ["   if have.%s then" % fv] + body + ["   end else p = -1", "   crt 'CK %s ':p" % label]


CHK = "\n".join(
    ["* zzchk - where things stand (sandbox-editgates.py)",
     "   open 'voc' to v then have.v = 1 else crt 'CK setup voc' ; stop",
     "   open 'zzd' to d then have.d = 1 else have.d = 0",
     "   open 'DICT', 'zzd' to dd then have.dd = 1 else have.dd = 0",
     "   open 'DICT', 'zzd2' to dd2 then have.dd2 = 1 else have.dd2 = 0",
     "   open 'DICT', 'zzd3' to dd3 then have.dd3 = 1 else have.dd3 = 0",
     "   open 'bp' to b then have.b = 1 else have.b = 0",
     "   open 'zzwork.bp' to w then have.w = 1 else have.w = 0",
     "   open 'zzwork2.bp' to w2 then have.w2 = 1 else have.w2 = 0"]
    + sum([chk_lines(label, fv, stmt) for label, fv, stmt in CHECKS], []) + ["end", ""])


def acct_path(name):
    return os.path.join(g.BOX, "user_accounts", name)


def build(name):
    """Make the fixture account, give it the register fields, compile the probe as the administrator."""
    g.EXTRA_FIXTURES[name] = ("no", "no")
    path = g.build_account(name)
    fixer = "\n".join([
        "$internal",
        "   acct = '%s'" % path,
        "   openpath acct:'/voc' to v else crt 'EGFIX no voc' ; stop",
        "   for each nm in 'zzd':@fm:'zzd2':@fm:'zzd3':@fm:'zzd4'",
        "      create.file acct:'/':nm dynamic on error crt 'EGFIX create ':nm ; stop",
        "      create.file acct:'/':nm:'.dic' dynamic on error crt 'EGFIX create dict ':nm ; stop",
        "      write 'F':@fm:nm:@fm:nm:'.dic' to v, nm",
        "      openpath acct:'/':nm:'.dic' to dd else crt 'EGFIX open dict ':nm ; stop",
        "      write 'D':@fm:'0' to dd, 'zzf'",
        "      write 'D':@fm:'0' to dd, 'zzq'",
        "      close dd",
        "   next nm",
        "   openpath acct:'/zzd' to d else crt 'EGFIX open zzd' ; stop",
        "   write 'data record' to d, 'zzdr'",
        "   close d",
        "   create.file acct:'/zzwork.bp' directory on error crt 'EGFIX create zzwork.bp' ; stop",
        "   write 'F':@fm:'zzwork.bp' to v, 'zzwork.bp'",
        "   openpath acct:'/zzwork.bp' to w1 else crt 'EGFIX open zzwork.bp' ; stop",
        "   write 'a record in the work program file' to w1, 'zzwk1'",
        "   close w1",
        "   for each wn in 'zzwork2.bp':@fm:'zzwork3.bp'",
        "      create.file acct:'/':wn directory on error crt 'EGFIX create ':wn ; stop",
        "      write 'F':@fm:wn to v, wn",
        "   next wn",
        "   write 'F':@fm:'bp.out' to v, 'bp.out'",
        "   write 'V':@fm:'CA':@fm:'$zzegk' to v, 'zzegk'",
        "   write 'X' to v, 'zzvrec'",
        "   write 'V':@fm:'a':@fm:'b' to v, 'zzvrec2'",
        "   openpath acct:'/bp' to b else crt 'EGFIX open bp' ; stop",
        "   write 'old program text' to b, 'zzold'",
        "   write 'old program text two' to b, 'zzold2'",
        "   write 'a record to be moved out' to b, 'zzmv'",
        "   close b",
        "   write 'X' to v, 'zzedv1'",
        "   write 'X' to v, 'zzedv2'",
        "   write 'V':@fm:'c':@fm:'d' to v, 'zzvrec3'",
        "   openpath acct:'/zzd.dic' to dd9 else crt 'EGFIX open dict for zzf2' ; stop",
        "   write 'D':@fm:'0' to dd9, 'zzf2'",
        "   close dd9",
        "   crt 'EGFIX done'",
        "end", ""])
    g.put(os.path.join(path, "bp", "zzprobe"), PROBE)
    g.put(os.path.join(path, "bp", "zzchk"), CHK)
    g.put(os.path.join(path, "bp", "zzrec"), REC)
    g.put(os.path.join(path, "bp", "zzbas"), "   crt 'zzbas ran'\nend\n")
    g.put(os.path.join(path, "bp", "zzcat"), "   crt 'zzcat ran'\nend\n")          # compiled by the administrator, catalogued by the account
    g.put(os.path.join(path, "bp", "zzseqold"), "an old file in the program file\n")
    out = g.sd(path, ["BASIC bp zzprobe zzchk zzrec zzcat"], admin=True, account=name)
    if not g.has(out, r"^Compiled 4 program\(s\) with no errors"):
        bail("zzprobe, zzchk, zzrec and zzcat did not compile in %s:\n%s" % (name, "\n".join(out[-8:])))
    g.put(os.path.join(g.SYS, "bp", "zzegfix"), fixer)
    out = g.adm(["BASIC bp zzegfix", "RUN bp zzegfix"], internal=True)
    if not g.has(out, r"^EGFIX done$"):
        bail("the fixture %s was not completed:\n%s" % (name, "\n".join(out[-6:])))
    out = g.sd(path, ["CATALOG bp zzprobe LOCAL"], admin=True, account=name)     # a catalogue entry for the verbs to remove
    if not g.has(out, r"zzprobe added to local catalogue"):
        bail("zzprobe was not catalogued in %s:\n%s" % (name, "\n".join(out[-6:])))
    f = FIELDS[name]
    rec = [path, "", g.GROUP, "", "", "", "no", "yes" if name in EDIT_ACCOUNTS else "no", "", f[0] or "", f[1] or "", f[2] or ""]
    if f[0] is None:
        rec = rec[:8]
    g.reg_write(name, rec)
    return path


def run_probe(name, admin=False):
    out = g.sd(acct_path(name), ["RUN bp zzprobe"], admin=admin, account=name) if admin else g.plain(name, ["RUN bp zzprobe"])
    d = {}
    for ln in out:
        m = re.match(r"^PR (\S+) (OK|REFUSED)(?: P=(\d))?$", ln)
        if m:
            d[m.group(1)] = (m.group(2), m.group(3))
    return d, out


def on_disk(name, rel):
    return os.path.exists(os.path.join(acct_path(name), rel))


# What the verbs are given, in one session per account.  The ED lines end with Q and Y: a refused FI leaves the editor waiting, and
# a successful one has already left it (what follows is then a command that is not in the VOC, which is harmless).
ED_LINES = ["I", "hello", "", "FI", "Q", "Y"]


def ed_record_delete(cmd, allowed):
    """DELETE or FD, then what answers it.  Allowed: the 'sure?' question wants Y.  Refused: there is no question, and a Y would be an
    unrecognised command that ED answers with an insert prompt, which loops at the end of the input; so only Q follows, twice: the first
    ends the editor, the second is then a harmless unknown word at the command prompt.  A delete that was made is followed by one Q, the
    same.  KNOWN LIMIT: if the refusal were missing, the first Q would be the answer to ED's 'sure?' question, which is asked again for
    ever at the end of the input - the suite then hangs and times out instead of failing a row (the runtime mutants of ED's DELETE and FD
    were detected that way, not by a row)."""
    return [cmd, "Y", "Q"] if allowed else [cmd, "Q", "Q"]


def verbs(voc):
    """What the verbs are given in one session, for an account whose voc.edit is on (voc) or off."""
    return (["COPY FROM zzd TO VOC zzdr,zzdrcopy",
          "COPY FROM zzd TO DICT zzd zzdr,zzdcopy",
          "COPY FROM zzd TO bp zzdr,zzbpcopy",
          "DELETE VOC zzvrec NO.QUERY",
          "DELETE DICT zzd zzf NO.QUERY",
          "DELETE bp zzold NO.QUERY",
          "CLEAR.FILE DICT zzd2",
          "CLEAR.FILE zzwork.bp",
          "CNAME DICT zzd zzq TO zzqb",
          "CNAME zzwork3.bp TO zzmoved",
          "DELETE.FILE DICT zzd3 NO.QUERY",
          "DELETE.FILE zzwork2.bp NO.QUERY",
          "BASIC bp zzbas",
          "CATALOG bp zzbas LOCAL",
          "CATALOG bp zzcat LOCAL",                     # compiled by the administrator: only the gate can stop this one
          "DELETE.CATALOG zzprobe LOCAL",
          "DECATALOG zzprobe",
          "COPY FROM bp TO zzd zzmv DELETING",          # a record moved OUT of a program file
          "ED VOC zzed"] + ED_LINES +
         ["ED DICT zzd zzed2"] + ED_LINES +
         ["ED bp zzed3"] + ED_LINES +
         ["ED VOC zzedv1"] + ed_record_delete("DELETE", voc) +
         ["ED VOC zzedv2"] + ed_record_delete("FD", voc) +
         ["CNAME zzd4 TO zzd4.bp"])



MESSAGES = {"voc": "The VOC can only be changed by an account that has voc.edit",
            "dict": "A dictionary can only be changed by an account that has dict.edit",
            "bp": "A program file can only be changed by an account that has bp.edit",
            "compile": "Programs can only be compiled or catalogued by an account that has bp.edit"}


def checks(name):
    out = g.plain(name, ["RUN bp zzchk"])
    d = {}
    for ln in out:
        m = re.match(r"^CK (\S+) (-?\d+)$", ln)
        if m:
            d[m.group(1)] = int(m.group(2))
    return d, out


def reg_fields(name):
    return (g.reg_read(name) + [""] * 12)[:12]


F2, CTRL_Q, CTRL_S, DOWN, HOME, RET = "\x1bOQ", "\x11", "\x13", "\x1bOB", "\x1b[1~", "\r"


def pty_edit(account, cmd, keys, leave):
    """One run of a full-screen editor on a pseudo-terminal in the account (as an ordinary user): type to it, read the screen, and leave
    through the keys given (what a refused save leaves behind is a changed record, which the editor asks about).  Returns the screen."""
    env = dict(os.environ, SD_CONFIG=os.path.join(g.BOX, "sd.conf"), TERM="xterm", LC_ALL="C", LANG="C")
    env.pop("SDTEST_ADMIN", None)
    env.pop("SSH_CONNECTION", None)
    say("    > pty %s: %s | keys %r" % (account, cmd, keys))
    s = PtySession([g.SD, "-a" + account], acct_path(account), env, 120, 36)
    s.settle(1.0)
    s.type("TERM xterm\r")
    s.type("TERM 120,36\r")
    s.type(cmd + "\r", idle=1.2)
    for k in keys:
        s.type(k, idle=0.7)
    text = "\n".join(l for l in s.screen.lines() if l.strip())
    for k in leave:
        s.type(k, idle=0.6)
    s.type("\rOFF\r", idle=0.5)
    s.finish()
    return text


def records(name):
    out = g.plain(name, ["RUN bp zzrec"])
    d = {}
    for ln in out:
        m = re.match(r"^REC (\S+) (.*)$", ln)
        if m:
            d[m.group(1)] = m.group(2)
    return d


def editors_section():
    say("\n--- the full-screen editors, on a pseudo-terminal: IDE and SED save, and say why they do not --------------------------")
    for n in ("zzoff", "zzall"):
        build(n)
        voc, bp, dic = WANT[n]
        # IDE: a program record and a VOC record (F2 saves)
        t1 = pty_edit(n, "IDE bp zzold", [HOME, "ZZ", F2], [CTRL_Q, DOWN, RET])
        t2 = pty_edit(n, "IDE voc zzvrec2", [HOME, "ZZ", F2], [CTRL_Q, DOWN, RET])
        # SED: a program record, a VOC record and a dictionary record (Ctrl-S saves)
        t3 = pty_edit(n, "SED bp zzold2", ["ZZ", CTRL_S], [CTRL_Q, "y"])
        t4 = pty_edit(n, "SED voc zzvrec3", ["ZZ", CTRL_S], [CTRL_Q, "y"])
        t5 = pty_edit(n, "SED DICT zzd zzf2", ["ZZ", CTRL_S], [CTRL_Q, "y"])
        r = records(n)
        for label, rec_key, allowed, text, msg in (
                ("IDE saves a program record", "bp-zzold", bp, t1, MESSAGES["bp"]),
                ("IDE saves a VOC record", "voc-zzvrec2", voc, t2, MESSAGES["voc"]),
                ("SED saves a program record", "bp-zzold2", bp, t3, MESSAGES["bp"]),
                ("SED saves a VOC record", "voc-zzvrec3", voc, t4, MESSAGES["voc"]),
                ("SED saves a dictionary record", "dict-zzf2", dic, t5, MESSAGES["dict"])):
            got = r.get(rec_key, "<missing>")
            changed = got.startswith("ZZ")
            row("%s: %s %s (the record %s)" % (n, label, "and it is saved" if allowed else "and it is refused", "has ZZ" if allowed else "is as it was"),
                changed == allowed and ((msg in text) == (not allowed)), "record %r; refusal %s on screen" % (got, "seen" if msg in text else "not seen"))
        # the editors that were not given a save leave the other records alone
        row("%s: the dictionary record SED was NOT asked about (zzf) and the other VOC record (zzvrec3 before SED) are untouched" % n,
            r.get("dict-zzf") == "D|0", repr(r.get("dict-zzf")))
    # NANO (and MICRO), the verbs that hand a record to an editor outside SD (the program $edit; the EDIT verb is the line editor ED): they
    # need a terminal and OS.EXECUTE first, so the accounts here hold os-on; the guard is asked before the editor is started, so what is
    # looked for is the refusal (11407) on the screen, and its absence in the account that holds bp.edit (whatever the editor then does
    # there is not the question)
    for n in EDIT_ACCOUNTS:
        build(n)
        allowed = WANT[n][1]
        t = pty_edit(n, "NANO bp zzold", [], [])
        row("%s (OS.EXECUTE on): NANO bp zzold %s" % (n, "is not refused (bp.edit on)" if allowed else "is refused before an editor starts (11407)"),
            (MESSAGES["bp"] in t) == (not allowed), "screen: %r" % t[-400:])


def modify_section():
    say("\n--- MODIFY.ACCOUNT VOC-ON / VOC-OFF / BP-ON / BP-OFF / DICT-ON / DICT-OFF -------------------------------------------")
    n = "zzoff"
    steps = [
        ("modify.account zzoff voc-on", (1, 0, 0)), ("MODIFY.ACCOUNT zzoff BP-ON", (1, 1, 0)), ("modify.account zzoff dict-on", (1, 1, 1)),
        ("MODIFY.ACCOUNT zzoff VOC-OFF", (0, 1, 1)), ("modify.account zzoff bp-off", (0, 0, 1)), ("MODIFY.ACCOUNT zzoff DICT-OFF", (0, 0, 0)),
    ]
    for cmd, state in steps:
        out = g.adm([cmd])
        word = lambda b: "yes" if b else "no"
        row("%s says where all three now stand (a switch names only one)" % cmd,
            g.has(out, r"^Account zzoff has VOC\.EDIT %s, BP\.EDIT %s, DICT\.EDIT %s$" % tuple(word(b) for b in state)), repr(out[-3:]))
        f = reg_fields(n)
        row("...and writes fields 10, 11 and 12 of the register record (%s)" % "/".join(word(b) for b in state),
            tuple(x == "yes" for x in f[9:12]) == state, repr(f))
    out = g.adm(["MODIFY.ACCOUNT zzoff VOC-OFF"])
    row("a switch already in that state says so (10080) and changes nothing", g.has(out, r"already had that access; nothing changed"), repr(out[-3:]))
    out = g.adm(["MODIFY.ACCOUNT zzoff DICT-ON"])
    out = g.plain(n, ["ZZEGK"])
    row("the switch takes effect at the next sign-on: a new session in zzoff now holds dict only", g.has(out, r"^EG gates voc=0 bp=0 dict=1$"), repr(out[:4]))
    g.adm(["MODIFY.ACCOUNT zzoff DICT-OFF"])
    out = g.plain(n, ["ZZEGK"])
    row("...and DICT-OFF takes it away at the sign-on after that", g.has(out, r"^EG gates voc=0 bp=0 dict=0$"), repr(out[:4]))
    out = g.adm(["MODIFY.ACCOUNT"])
    row("MODIFY.ACCOUNT's syntax lines name the six words", g.has(out, r"voc-on \| voc-off \| bp-on \| bp-off \| dict-on \| dict-off"), repr(out[-8:]))
    out = g.adm(["MODIFY.ACCOUNT zzoff VOCON"])
    row("a word that is not one of them is refused, and the list of words names the six",
        g.has(out, r"modify\.account Action Must Be") and g.has(out, r"voc-on, voc-off, bp-on, bp-off, dict-on, dict-off"), repr(out[-4:]))


def logto_section():
    say("\n--- LOGTO: the account the person SIGNED ON to decides (owner, 17 Oct: sign-on only) ------------------------------")
    for n in LOGTO_ACCOUNTS:
        build(n)
    for start, target, allowed in (("zzlga", "zzlgb", True), ("zzlgd", "zzlgc", False)):
        want = "gates on" if LOGTO_ACCOUNTS[start][0] == "yes" else "gates off"
        out = g.plain(start, ["LOGTO " + target, "WHO", "RUN bp zzprobe"])
        d = {}
        for ln in out:
            m = re.match(r"^PR (\S+) (OK|REFUSED)(?: P=(\d))?$", ln)
            if m:
                d[m.group(1)] = (m.group(2), m.group(3))
        row("signed on to %s (%s), LOGTO %s: WHO shows the session is in %s, from %s" % (start, want, target, target, start),
            g.has(out, r"^\d+ %s from %s$" % (target, start)), repr(out[:6]))
        got_ok = all(d.get(name, (None, None)) == ("OK", "1") for name, _k, _s, _c in CHANGES)
        got_no = all(d.get(name, (None, None)) == ("REFUSED", "0") for name, _k, _s, _c in CHANGES)
        row("...every change in %s is %s: the gates of %s, where the person signed on, and not %s's" % (
            target, "made" if allowed else "refused", start, target), got_ok if allowed else got_no, repr(d))


def upgrade_section():
    say("\n--- upgrade_editgates: the accounts that exist keep what they had, once ----------------------------------------------")
    marker = os.path.join(g.SYS, "$editgates.done")
    if os.path.exists(marker):
        os.remove(marker)
    base = [os.path.join(g.BOX, "user_accounts", "zzup")]
    g.reg_write("zzupa", [base[0], "", "sdu_zzupa", "", "", "", "no", "no"])                     # a user account that never heard of the gates
    g.reg_write("zzupb", [base[0], "", "sdu_zzupb", "", "", "", "no", "no", "", "no", "no", "no"])       # one that was told no
    g.reg_write("zzupc", [base[0], "", "sdu_zzupc", "", "", "", "no", "no", "", "no", "", ""])           # told no on one, never told on the rest
    g.reg_write("zzupg", [base[0], "", "sdg_zzupg", "", "", "", "", "", "", "", "", ""])                  # a GROUP account
    out = g.adm(["RUN gpl.bp upgrade_editgates"], internal=True)
    row("the walk says it finished (COMPLETE on a line of its own, which is what the installer looks for)", g.has(out, r"^COMPLETE$"), repr(out[-4:]))
    a, b, c, gr = (reg_fields(x) for x in ("zzupa", "zzupb", "zzupc", "zzupg"))
    row("a user account with no such fields: all three switched on", a[9:12] == ["yes", "yes", "yes"], repr(a))
    row("one that says no on all three is left alone (somebody decided)", b[9:12] == ["no", "no", "no"], repr(b))
    row("one that says no on voc and nothing on the rest: voc stays no, the others are switched on", c[9:12] == ["no", "yes", "yes"], repr(c))
    row("a GROUP account is left blank", gr[9:12] == ["", "", ""], repr(gr))
    row("the marker sdsys/$editgates.done was written, after the walk", os.path.exists(marker), "")
    g.reg_write("zzupa", [base[0], "", "sdu_zzupa", "", "", "", "no", "no", "", "no", "yes", "yes"])      # the administrator then switches voc off
    out = g.adm(["RUN gpl.bp upgrade_editgates"], internal=True)
    row("a second run says an earlier install did it, changes nothing, and still says COMPLETE",
        g.has(out, r"earlier install; nothing changed") and g.has(out, r"^COMPLETE$"), repr(out[-3:]))
    row("...so the administrator's VOC-OFF is not undone", reg_fields("zzupa")[9] == "no", repr(reg_fields("zzupa")))


def manifest_section():
    say("\n--- the account manifest (BACKUP.ACCOUNT / RESTORE.ACCOUNT) carries the gates -----------------------------------------")
    g.put(os.path.join(g.SYS, "gpl.bp", "zzegi"), "\n".join([
        "$internal", "program zzegi", "$catalog $zzegi", "$include keys.h", "$include int$keys.h",
        "   openpath @sdsys:@ds:'accounts' to acc.f else crt 'EGI no register' ; stop",
        "   for each a in 'zzmana':@fm:'zzmanb'",
        "      read rec from acc.f, a then",
        "         call !acc_os_info(a, rec, info, err)",
        "         crt 'EGI ':a:' ':convert(@fm, '|', info):' err=':err",
        "      end else crt 'EGI no record ':a",
        "   next a", "end", ""]))
    out = g.adm(["BASIC gpl.bp zzegi"], internal=True)
    if not g.has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("zzegi did not compile:\n" + "\n".join(out[-8:]))
    g.reg_write("zzmana", ["/tmp/zzmana", "", "sdu_zzmana", "", "", "", "no", "no", "", "yes", "no", "yes"])
    g.reg_write("zzmanb", ["/tmp/zzmanb", "", "sdu_zzmanb", "", "", "", "yes", "yes"])               # no edit fields at all
    out = g.adm(["RUN gpl.bp zzegi"], internal=True)
    row("zzmana (voc yes, bp no, dict yes): edit.voc: 1, edit.bp: 0, edit.dict: 1 in its manifest",
        g.has(out, r"^EGI zzmana .*\|edit\.voc: 1\|edit\.bp: 0\|edit\.dict: 1(\||\s)"), repr([x for x in out if "zzmana" in x][:2]))
    row("zzmanb (no edit fields): all three 0, as a blank is off", g.has(out, r"^EGI zzmanb .*\|edit\.voc: 0\|edit\.bp: 0\|edit\.dict: 0(\||\s)"),
        repr([x for x in out if "zzmanb" in x][:2]))


def verbs_section():
    say("\n--- the user verbs: the same gates, asked by the programs the kernel's own test lets through -------------------------")
    for n in ACCOUNTS:
        if n == "zzadmin":
            continue
        build(n)                                   # a fresh account: the probe section changed this one
        want = WANT[n]
        voc, bp, dic = want
        out = g.plain(n, verbs(voc))
        text = "\n".join(out)
        ck, ckout = checks(n)
        exp = {
            "voc-copy": 1 if voc else 0, "voc-zzvrec": 0 if voc else 1, "voc-zzed": 1 if voc else 0,
            "voc-zzedv1": 0 if voc else 1, "voc-zzedv2": 0 if voc else 1, "voc-zzcat": 1 if bp else 0, "bp-zzmv": 0 if bp else 1,
            "dict-copy": 1 if dic else 0, "dict-zzf": 0 if dic else 1, "dict-zzq": 0 if dic else 1, "dict-zzqb": 1 if dic else 0,
            "dict-zzed2": 1 if dic else 0, "dict2-count": 0 if dic else None, "d3-dict-exists": -1 if dic else 1,
            "bp-copy": 1 if bp else 0, "bp-zzold": 0 if bp else 1, "bp-zzed3": 1 if bp else 0, "work-count": 0 if bp else 1,
            "work2-exists": -1 if bp else 1, "voc-zzwork3": 0 if bp else 1, "voc-zzmoved": 1 if bp else 0,
            "voc-zzbas": 1 if bp else 0, "voc-zzprobe": 0 if bp else 1, "voc-zzdbp": 1 if bp else 0, "data-ok": 1,
        }
        labels = [
            ("COPY into the VOC / DELETE a VOC record / ED a VOC record / ED DELETE / ED FD",
             ("voc-copy", "voc-zzvrec", "voc-zzed", "voc-zzedv1", "voc-zzedv2")),
            ("COPY into a dictionary / DELETE a dictionary record / CLEAR.FILE DICT / CNAME DICT / DELETE.FILE DICT / ED DICT",
             ("dict-copy", "dict-zzf", "dict2-count", "dict-zzq", "dict-zzqb", "dict-zzed2", "d3-dict-exists")),
            ("COPY into a program file / COPY out of one (DELETING) / DELETE / CLEAR.FILE / DELETE.FILE / ED a program file",
             ("bp-copy", "bp-zzmv", "bp-zzold", "bp-zzed3", "work-count", "work2-exists")),
            ("CNAME a program file away and a data file to a program file's name / BASIC / CATALOG (of one the administrator compiled) / DELETE.CATALOG / DECATALOG",
             ("voc-zzwork3", "voc-zzmoved", "voc-zzbas", "voc-zzcat", "voc-zzprobe", "voc-zzdbp", "data-ok")),
        ]
        for label, keys in labels:
            bad = [k for k in keys if (ck.get(k) is None) or (exp[k] is not None and ck[k] != exp[k]) or (exp[k] is None and ck[k] <= 0)]
            row("%s: %s" % (n, label), not bad, "wrong for %s: have %r" % (bad, {k: ck.get(k) for k in keys}))
        for key, msg_ok in (("voc", voc), ("dict", dic), ("bp", bp)):
            seen = MESSAGES[key] in text
            row("%s: the refusal for a %s says so (11405 / 11406 / 11407) exactly when the gate is off" % (n, key if key != "bp" else "program file"),
                seen == (not msg_ok), "gate %s, message %s" % ("on" if msg_ok else "off", "seen" if seen else "not seen"))
        row("%s: BASIC, CATALOG, DELETE.CATALOG and DECATALOG say 11408 exactly when bp.edit is off" % n,
            (MESSAGES["compile"] in text) == (not bp), "bp.edit %s" % ("on" if bp else "off"))
        row("%s: the compile produced bp.out/zzbas on the disk exactly when bp.edit is on" % n, on_disk(n, "bp.out/zzbas") == bp, "")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-editgates.py <dir> [--build]")
    g.BOX = os.path.abspath(args[0])
    g.SYS = os.path.join(g.BOX, "sys")
    g.SD = os.path.join(g.SYS, "bin", "sd")
    g.EDIT_DEFAULT = None       # this is the suite OF the gates: a register record is written exactly as the rows say
    # --sections=verbs,editors runs only those parts (core = the kernel's answers, the probe and the sequential routes; verbs, editors,
    # modify, logto, upgrade, manifest, admin); no flag runs them all.  The runtime mutants use it to ask one part about one change.
    sections = next((set(a.split("=", 1)[1].split(",")) for a in sys.argv[1:] if a.startswith("--sections=")), None)

    def run(part):
        return sections is None or part in sections
    core_accounts = ACCOUNTS if run("core") else {}
    say("sandbox-editgates: sandbox %s%s" % (g.BOX, "" if sections is None else "  (parts: %s)" % ",".join(sorted(sections))))
    if "--build" in sys.argv:
        if os.path.exists(g.BOX) and os.listdir(g.BOX):
            bail("%s is not empty" % g.BOX)
        r = subprocess.run([sys.executable, g.TOOL, g.BOX, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-editgates: built, bootstrap passed")
    elif not os.path.isfile(g.SD):
        bail("%s holds no built sandbox (use --build, or point it at one)" % g.BOX)
    subprocess.run([sys.executable, g.TOOL, g.BOX, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    say("\n--- preparation: a CPROC that is not the install build, the fixture accounts, the probe compiled by the administrator ---")
    g.prepare()
    g.put(os.path.join(g.SYS, "gpl.bp", "zzegk"), EGK)
    out = g.adm(["BASIC gpl.bp zzegk"], internal=True)
    # On a tree WITHOUT the gates (run against an old sandbox to prove the suite can fail) the keys do not exist and this does not compile:
    # that is a failed row, not a reason to stop, so that every other row still says what the old tree does.
    row("the kernel probe zzegk (K$VOC.EDIT ... K$EDIT.OS.OK) compiles", g.has(out, r"^Compiled 1 program\(s\) with no errors"), repr(out[-6:]))
    for n in core_accounts:
        build(n)

    say("\n--- the kernel's answers, asked by an internal program --------------------------------------------------------------")
    for n in core_accounts:
        if n == "zzadmin":
            continue
        out = g.plain(n, ["ZZEGK"])
        want = WANT[n]
        gates = next((ln for ln in out if ln.startswith("EG gates ")), "")
        row("%s: the session holds voc=%d bp=%d dict=%d, loaded at sign-on from the register (a missing field is off)" % ((n,) + tuple(int(x) for x in want)),
            gates == "EG gates voc=%d bp=%d dict=%d" % tuple(int(x) for x in want), repr(gates))
        ok = next((ln for ln in out if ln.startswith("EG ok ")), "")
        m = dict(re.findall(r"(\w+)=(\d)", ok))
        voc, bp, dic = want[0], want[1], want[2]
        exp = {"voc": voc, "dict": dic, "bp": bp, "bpout": bp, "sfx": bp, "sfxout": bp, "vocdic": dic, "slash": bp, "upper": bp,
               "other": True, "lookalike": True, "empty": False}
        bad = [k for k, v in exp.items() if m.get(k) != ("1" if v else "0")]
        row("%s: K$EDIT.OK by the last component of the pathname (voc, *.dic, bp, bp.out, *.bp, *.bp.out; case and a trailing slash do not matter; "
            "an empty name is refused)" % n, not bad, "wrong for %s: %r" % (bad, ok))
        if n == "zzoff":
            kind = next((ln for ln in out if ln.startswith("EG kind ")), "")
            row("K$EDIT.KIND names the kind (1 VOC, 2 dictionary, 3 program file, 0 neither; voc.dic is a dictionary, not the VOC)",
                kind == "EG kind voc=1 dict=2 bp=3 bpout=3 sfx=3 vocdic=2 other=0 empty=0", repr(kind))
            osl = next((ln for ln in out if ln.startswith("EG os ")), "")
            row("zzoff: K$EDIT.OS.OK looks at every component below the account (bp/x, bp.out/x, sub/bp/y, zzd.dic/%0, voc/%0, sub/../bp/y refused; "
                "inside.txt and sub/y allowed; an empty path refused)",
                osl == "EG os bp=0 bpout=0 deep=0 dic=0 voc=0 plain=1 sub=1 dotdot=0 empty=0", repr(osl))

    say("\n--- the probe in each account: every change is allowed exactly when the gate for its kind is on ----------------------")
    kinds = ("voc", "bp", "dict")
    results = {}
    for n in core_accounts:
        if n == "zzadmin":
            continue
        results[n], out = run_probe(n)
        row("%s: the probe ran to its last line" % n, "oscopy-control" in results[n], repr(out[-6:]))
    for n in core_accounts:
        if n == "zzadmin":
            continue
        r = results[n]
        want = WANT[n]
        for name, k, _s, _c in CHANGES:
            word, p = r.get(name, (None, None))
            expect = "OK" if want[k] else "REFUSED"
            row("%s: %s is %s%s" % (n, name, expect, " and the change is there" if want[k] else " and nothing changed"),
                word == expect and p == ("1" if want[k] else "0"), repr((word, p)))
        for name, _s, _c in CONTROLS:
            word, p = r.get(name, (None, None))
            row("CONTROL %s: %s, an ordinary file, is always changed" % (n, name), word == "OK" and p == "1", repr((word, p)))

    say("\n--- the sequential-file routes to a program file (the disk is the evidence) ----------------------------------------")
    for n in core_accounts:
        if n == "zzadmin":
            continue
        r = results[n]
        bp_on = WANT[n][1]
        row("%s: OPENSEQ bp,id then WRITESEQ %s (disk: bp/zzseq1 %s)" % (n, "writes" if bp_on else "is refused", "exists" if bp_on else "absent"),
            on_disk(n, "bp/zzseq1") == bp_on, repr(r.get("seq-record")))
        row("%s: OPENSEQ 'bp/id' (a pathname inside the account) then WRITESEQ %s" % (n, "writes" if bp_on else "is refused"),
            on_disk(n, "bp/zzseq2") == bp_on, repr(r.get("seq-path")))
        row("%s: DELETESEQ bp,id %s (disk: bp/zzseqold %s)" % (n, "deletes" if bp_on else "is refused", "gone" if bp_on else "still there"),
            on_disk(n, "bp/zzseqold") != bp_on, repr(r.get("seq-delete")))
        row("%s: !OSCOPY INTO bp/ %s" % (n, "copies" if bp_on else "is refused"), on_disk(n, "bp/zzcopy") == bp_on, repr(r.get("oscopy")))
        row("%s: !IOSCOPY INTO bp/ %s" % (n, "copies" if bp_on else "is refused"), on_disk(n, "bp/zzicopy") == bp_on, repr(r.get("ioscopy")))
        row("CONTROL %s: OPENSEQ and !OSCOPY into the account's ordinary files are always allowed" % n,
            on_disk(n, "zzseq3") and on_disk(n, "zzcopy2"), repr((r.get("seq-control"), r.get("oscopy-control"))))

    for name, section in (("verbs", verbs_section), ("editors", editors_section), ("modify", modify_section), ("logto", logto_section),
                          ("upgrade", upgrade_section), ("manifest", manifest_section)):
        if run(name):
            section()

    if run("admin"):
        say("\n--- the administrator is never refused --------------------------------------------------------------------------------")
        r, out = run_probe("zzadmin", admin=True)
        row("zzadmin (gates off in its register), run as the administrator: every change is made",
            all(r.get(name, (None, None)) == ("OK", "1") for name, _k, _s, _c in CHANGES), repr(r))
        row("...and so are the sequential routes", on_disk("zzadmin", "bp/zzseq1") and on_disk("zzadmin", "bp/zzseq2") and on_disk("zzadmin", "bp/zzcopy")
            and on_disk("zzadmin", "bp/zzicopy") and not on_disk("zzadmin", "bp/zzseqold"), "")

    say("")
    say("sandbox-editgates: %d passed, %d failed" % (passed, failed))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
