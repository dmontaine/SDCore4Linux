#!/usr/bin/env python3
#
# sandbox-qmclient.py - QM4 gaps bundle C-1, the QMClient (SD API) functions added 15 Oct 26: SDRevision (sheet 89), SDGetVar
#                       (195), SDSystem, SDIndices (410), SDTrans and SDRTrans (499).  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-qmclient.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or absent).
# Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 31 Oct 26 dm  The A and S dictionary item types are gone: row H11b (it was H4) now expects the two A items ANAME and ATRIPLE to be refused as items that define no data; it follows H10 because the client keeps the last error text.
# 15 Oct 26 dm  Written for QM4 gaps bundle C-1.
# 15 Oct 26 dm  Part R: six threads in one process (sheet 456).  K1's helper thread selects its own session now: the current
#               session is per thread.
# 15 Oct 26 dm  Parts S and T.  S: a sequential file by pathname for an account that holds os-on (apisrvr's vb.openseq asks K$PATH.OK
#               itself).  T: SDCLIENT=1 and =2 in sd.conf, every request that tests it; it restarts the sandbox, so it runs LAST,
#               after K.  QMC_MUTANT=<name> recompiles the sandbox's apisrvr (or the fixture) with one deliberate fault.
# 18 Oct 26 dm  Part U: SDChecksum (encryption layer 2 / D5, the QMChecksum equivalent) against SD's own CHECKSUM() on the same strings,
#               with the algorithm written out again here, and with no connection at all.
# END-HISTORY
#
# THE INSTRUMENT.  A LOCAL API session: the sandbox's own sdclilib.so is loaded with ctypes, SD_CONFIG names the sandbox, and
# SDConnectLocal starts a real `sd -Q` server process (APISRVR) in a fixture account.  So the C client, the wire protocol and
# apisrvr are all the ones under test; only the TCP login (witness-release-run.sh) is not.  The expected values are computed
# apart from the call: the revision from revstamp.h, the data from the records the probe wrote and read back with SDRead, the
# index details from INDICES() in an ordinary session of the same account, a lowered record by lowering the SDRead answer here.
#
#   A  SDRevision: the client's before a connection, client and server as two values after one, 0.0-0 never for this server;
#      SDSystem(1012) is the same revision
#   B  SDGetVar: @SELECTED after a select, with and without the @ and in either case, the account path, the null string for a
#      name it does not know, a session variable that changed
#   C  SDSystem: keys whose values another route gives (1012, and the count of child phantoms)
#   D  SDIndices: the names of a file's indices and the details of one, against INDICES() in a session; an unknown index
#   E  SDTrans / SDRTrans: a dictionary field, a field number, -1 for the record, a list of ids, the C and X actions, the marks
#      lowered by SDTrans and not by SDRTrans, a file that is not there, a refused action
#   S  a pathname outside the account: refused to an account without os-on (the register flipped and a NEW session made: the
#      switches are loaded at login), opened, written, read back and found on the disk for one with it; what the operating system
#      still refuses
#   U  SDChecksum: ten strings (high bytes, marks, empty, 10,000 characters) against CHECKSUM() in the server's BASIC and against a
#      written-out copy of the algorithm; a control that the value is not constant; the null string is 0; no connection needed
#   T  SDCLIENT in sd.conf (RUNS LAST: it restarts the sandbox).  0 as the control, 1 (no open, no execute), 2 (also a restricted
#      call): SDOpen, SDOpenSeq, SDTrans, SDRTrans, SDExecute, SDCall and the T and U conversions, each with the disk as evidence
#
# MUTANTS.  QMC_MUTANT=<name> makes one deliberate fault in the sandbox's own copy of apisrvr (never the tree) before the run, and
# the rows that notice it must fail: open, openseq, trans, conv, execute, call (the SDCLIENT test of that request disabled),
# path-none (vb.openseq stops asking K$PATH.OK), path-all (it refuses every pathname), fixture-os-off (the os-on account is not).
# Two names are REPAIRS, not faults, for defects this part found (neither is in the tree; the rows T*-6 and T*-5 are red on it until
# they are): fix-call-return (vb.call returns after refusing, where it now goes on to run the subroutine) and fix-execute-lib
# (sdclilib.c's SDExecute copies reply_len bytes, where it strcpy's an on-error reply's text into a 1-byte buffer).
#   F  the program form of NON.DURABLE.TXN, G  SDTxn
#   H  SDEvaluate / SDEvalConv (sheet 247): D, A and I items, an item the dictionary has not, a phrase, an I-type that will not
#      compile, several names, the conversion applied or not, the dictionary left unwritten, @ID put back
#   I  SDIConv / SDOConv / SDIConvs / SDOConvs (sheet 409): dates both ways, the conversion's own status, the plural against the
#      singular, a code that does not exist

import ctypes
import datetime
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("q3", os.path.join(HERE, "sandbox-stmt-q3.py"))
q3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q3)
say, row, has, tag, put = q3.say, q3.row, q3.has, q3.tag, q3.put

FM, VM, SM = b"\xfe", b"\xfd", b"\xfc"

ND_BODY = ("   open 'zzcl' to f else stop 'no file'\n   sc = field(@sentence, ' ', 4)\n"
           "   transaction start\n"      # a WRITE inside a transaction needs the lock first (error 3023 otherwise)
           "   readu x from f, 'p1' else null\n   readu x from f, 'both' else null\n"
           "   write 'parent' on f, 'p1'\n   write 'parent first' on f, 'both'\n"
           "   transaction start\n"
           "   readu x from f, 'c1' else null\n   readu x from f, 'old' else null\n"
           "   write 'child' on f, 'c1'\n   write 'child second' on f, 'both'\n"
           "   if sc = 'delold' then delete f, 'old'\n"
           "   if sc = 'lock' then readu x from f, 'lk' else x = ''\n"
           "   transaction commit\n"
           "   crt 'LOCK1[':recordlocked(f, 'lk'):']'\n"
           "   crt 'CACHE[':change(change(system(1065), @fm, '/'), @vm, '|'):']'\n"
           "   if sc = 'abort' or sc = 'delold' then\n      transaction abort\n   end else\n      transaction commit\n   end\n"
           "   crt 'LOCK2[':recordlocked(f, 'lk'):']'\n"
           "   crt 'DEPTH[':system(1008):']'\n"
           "end\n")

USER_PROGS = {
    # R: a catalogued subroutine that returns its first argument twice in its second (called with SDCallx from six threads)
    "zzcsub": "subroutine zzcsub(a, b)\n   b = a : '/' : a\nreturn\nend\n",
    # T: what SDCLIENT lets through.  zzcmk and zzcok each leave a mark in zzlog when they run (zzcok is flagged $sdcall), zzxmk is a
    # program a command can run, zzmrk reads the marks back in an ordinary session (and clears them with the argument "clear")
    "zzcmk": "subroutine zzcmk(a, b)\n   open 'zzlog' to f else return\n   write 'ran ':a on f, 'callmark'\n   b = 'ret:':a\nreturn\nend\n",
    "zzcok": "$sdcall\nsubroutine zzcok(a, b)\n   open 'zzlog' to f else return\n   write 'ran ':a on f, 'okmark'\n   b = 'ret:':a\nreturn\nend\n",
    "zzxmk": "   open 'zzlog' to f else stop\n   write 'ran' on f, 'execmark'\nend\n",
    "zzmrk": ("   open 'zzlog' to f else stop 'no file'\n   sc = field(@sentence, ' ', 4)\n"
              "   for each id in 'callmark':@fm:'okmark':@fm:'execmark'\n"
              "      read r from f, id then crt 'M[':id:'=':r:']' else crt 'M[':id:'=-]'\n"
              "      if sc = 'clear' then delete f, id\n   next id\n"
              "   open 'zzcl' to g else stop 'no zzcl'\n   crt 'TC[':oconv('r1', 'Tzzcl;X;;1'):']'\nend\n"),
    # the data: three records of zzcl, a dictionary with NAME (field 1), QTY (2) and TAGS (3, multivalued); an index on NAME
    "zzclmk": ("   open 'zzcl' to f else stop 'no file'\n   open 'DICT zzcl' to d else stop 'no dict'\n"
               "   write 'D':@fm:'1':@fm:'':@fm:'Name':@fm:'10L':@fm:'S' on d, 'NAME'\n"
               "   write 'D':@fm:'2':@fm:'':@fm:'Qty':@fm:'5R':@fm:'S' on d, 'QTY'\n"
               "   write 'D':@fm:'3':@fm:'':@fm:'Tags':@fm:'8L':@fm:'M' on d, 'TAGS'\n"
               "   write 'Widget':@fm:'5':@fm:'red':@vm:'blue' on f, 'r1'\n"
               "   write 'Gadget':@fm:'7':@fm:'green' on f, 'r2'\n"
               "   write 'Gizmo':@fm:'9':@fm:'a':@vm:'b':@vm:'c' on f, 'r3'\n"
               # more dictionary items for the Evaluate rows: I-types (one with a conversion, one that is @ID, one that will not
               # compile), A items (since 31 Oct 26 the type is gone: they are refused as items that define no data), D items with a conversion, a phrase that defines no data
               "   write 'I':@fm:'QTY * 2':@fm:'':@fm:'Dbl':@fm:'8R':@fm:'S' on d, 'DOUBLE'\n"
               "   write 'I':@fm:'NAME':@fm:'MCU':@fm:'Up':@fm:'10L':@fm:'S' on d, 'UPNAME'\n"
               "   write 'I':@fm:'@ID':@fm:'':@fm:'Id':@fm:'6L':@fm:'S' on d, 'IDCOPY'\n"
               "   write 'I':@fm:'QTY *':@fm:'':@fm:'Bad':@fm:'8R':@fm:'S' on d, 'BADI'\n"
               "   write 'A':@fm:'1':@fm:'Name':@fm:'':@fm:'':@fm:'S':@fm:'MCU':@fm:'':@fm:'L':@fm:'10' on d, 'ANAME'\n"
               "   write 'A':@fm:'2':@fm:'Qty':@fm:'':@fm:'':@fm:'S':@fm:'':@fm:\"A;2*'3'\":@fm:'R':@fm:'5' on d, 'ATRIPLE'\n"
               "   write 'D':@fm:'4':@fm:'D4/':@fm:'When':@fm:'10L':@fm:'S' on d, 'WHEN'\n"
               "   write 'D':@fm:'3':@fm:'MCU':@fm:'TagsUp':@fm:'8L':@fm:'M' on d, 'TAGU'\n"
               "   write 'PH':@fm:'LIST zzcl' on d, 'PH1'\n"
               "   crt 'MADE'\nend\n"),
    # F: non-durable nested transactions.  zzndt is compiled with $MODE NON.DURABLE.TXN, zzdur is the same text without it (the
    # control).  The scenario is the fourth word of the command; each ends by saying what SYSTEM(1065) lists and what the lock
    # state is, and the NEXT session reads the file to see what reached the disk.
    "zzndt": "$mode non.durable.txn\n" + ND_BODY,
    "zzdur": ND_BODY,
    "zzndr": ("   open 'zzcl' to f else stop 'no file'\n"
              "   for each id in 'p1' : @fm : 'c1' : @fm : 'both' : @fm : 'old' : @fm : 'lk' : @fm : 'top'\n"
              "      read r from f, id then crt 'R[':id:'=':r:']' else crt 'R[':id:'=-]'\n"
              "   next id\nend\n"),
    "zzndw": ("   open 'zzcl' to f else stop 'no file'\n   write 'old data' on f, 'old'\nend\n"),
    # J: a command that waits for input, so that its session is EXECUTING while another one comes and goes
    "zzprmp": "   input x\n   crt 'GOT[':x:']'\nend\n",
    # L: what SD's own DCOUNT() and CHANGE() make of the strings the client's SDDcount and SDChange are given
    "zzstr": ("   crt 'D1[':dcount('a,b,c', ','):']'\n   crt 'D2[':dcount('a::b::c::d', '::'):']'\n   crt 'D3[':dcount('aaaa', 'aa'):']'\n"
              "   crt 'D4[':dcount('a,b', ',,'):']'\n   crt 'D5[':dcount('', ','):']'\n   crt 'D6[':dcount('ab--cd--', '--'):']'\n"
              "   crt 'C1[':change('aaaa', 'aa', 'b'):']'\n   crt 'C2[':change('aaa', 'aa', 'b'):']'\n"
              "   crt 'C3[':change('abababa', 'aba', 'X'):']'\n   crt 'C4[':change('abcabcabcabc', 'abc', 'Z', 2, 2):']'\n"
              "   crt 'C5[':change('hello', 'l', ''):']'\n   crt 'C6[':change('hello', 'xyz', 'Q'):']'\n"
              "   crt 'C7[':change('xx--xx--xx', '--', '<>'):']'\n   crt 'C8[':change('aXbXc', 'X', 'YY', 1, 2):']'\nend\n"),
    # U: what SD's own CHECKSUM() (default mode) makes of the same strings SDChecksum is given; the high-byte strings are built with CHAR()
    "zzsum": ("   crt 'U1[':checksum('ABCDE'):']'\n   crt 'U2[':checksum(''):']'\n   crt 'U3[':checksum('a'):']'\n"
              "   crt 'U4[':checksum('hello world'):']'\n   crt 'U5[':checksum('a':char(200):'z'):']'\n"
              "   crt 'U6[':checksum(char(255)):']'\n   crt 'U7[':checksum(char(128):char(128)):']'\n"
              "   crt 'U8[':checksum(str('0123456789', 1000)):']'\n   crt 'U9[':checksum('ab':@vm:'cd':@fm:'e'):']'\n"
              "   crt 'UA[':checksum('abcdefghijklmnopqrstuvwxyz0123456789'):']'\nend\n"),
    # Q: WRITE / WRITEU ... CREATING.SEQKEY (the counter in the hashed file's header), inside and outside a transaction, and a
    # directory file refused
    "zzsk": ("   open 'zzsq' to f else stop 'no file'\n   write 'first' to f creating.seqkey id1\n   write 'second' to f creating.seqkey id2\n"
             "   writeu 'third' to f creating.seqkey id3\n   crt 'IDS[':id1:'|':id2:'|':id3:']'\n"
             "   crt 'LOCK3[':recordlocked(f, id3):']'\n   crt 'LOCK2[':recordlocked(f, id2):']'\n   release f, id3\n"
             "   read r from f, id2 then crt 'REC2[':r:']' else crt 'REC2[none]'\n   crt 'LAST[':fileinfo(f, 1031):']'\nend\n"),
    "zzskt": ("   open 'zzsq' to f else stop 'no file'\n   transaction start\n   write 'in txn' to f creating.seqkey tid\n"
              "   transaction commit\n   read r from f, tid then crt 'TXN[':tid:'=':r:']' else crt 'TXN[none]'\nend\n"),
    "zzskd": ("   open 'zzdir' to d else stop 'no dir'\n   id = ''\n   write 'x' to d creating.seqkey id on error crt 'REFUSED[':status():']'\n"
              "   crt 'AFTER[':id:']'\nend\n"),
    # N: MASTER.LOGIN and LOGIN both call this; only an API session (@TTY apisrvr) leaves a mark, and it says in what order
    "zzmark": ("   if @tty # 'apisrvr' then stop\n   open 'zzlog' to f else stop\n   read x from f, 'order' else x = ''\n"
               "   x<-1> = field(@sentence, ' ', 4)\n   write x on f, 'order'\nend\n"),
    # O: the BASIC class's connect to a port nothing listens on
    "zzcls": ("   obj = object('!sdclient')\n   ok = obj->connect('127.0.0.1', 1, 'nobody', 'x', 'zzaa')\n   crt 'OK[':ok:']'\n"
              "   crt 'ERR[':obj->error:']'\n   crt 'ST[':obj->ServerStatus:']'\nend\n"),
    # what INDICES() says about the index and the file, in an ordinary session
    "zzclix": ("   open 'zzcl' to f else stop 'no file'\n"
               "   crt 'NAMES[':change(indices(f), @fm, '/'):']'\n"
               "   crt 'DET[':change(change(change(indices(f, 'NAME'), @fm, '/'), @vm, '|'), @sm, '~'):']'\n"
               "end\n"),
}


# R: the client library used by several threads of one process (sheet 456).  It runs in a CHILD process so that a library that
# crashes or hangs is a failed row and not the end of this suite.  argv: the library, the thread count, the revision text.
THREAD_CHILD = r'''
import ctypes, json, sys, threading

lib = ctypes.CDLL(sys.argv[1])
NT = int(sys.argv[2])
REV = sys.argv[3]
for fn in ("SDGetVar", "SDRead", "SDSystem", "SDError", "SDGetArg"):
    getattr(lib, fn).restype = ctypes.c_void_p
for fn in ("SDOpen", "SDConnectLocal", "SDConnect", "SDGetSession", "SDSetSession", "SDConnected"):
    getattr(lib, fn).restype = ctypes.c_int


def text(p):
    if not p:
        return None
    b = ctypes.string_at(p)
    lib.SDFree(ctypes.c_void_p(p))
    return b


def err():
    p = lib.SDError()
    return ctypes.string_at(p) if p else b""


out = {"nt": NT}
errors = []
bar = threading.Barrier(NT, timeout=90)
sess = [None] * NT


def phases(i):
    s = {"ok": None, "idx": None, "who": None, "bad": None, "wrong": None}
    sess[i] = s
    bar.wait()                                    # everyone connects at the same moment
    s["ok"] = lib.SDConnectLocal(b"zzaa")
    s["idx"] = lib.SDGetSession()
    who = text(lib.SDGetVar(b"@USERNO"))
    s["who"] = None if who is None else who.decode("latin-1")
    bar.wait()                                    # then everyone asks which session is its own, over and over
    bad = 0
    for _ in range(100):
        if lib.SDGetSession() != s["idx"]:
            bad += 1
        w = text(lib.SDGetVar(b"@USERNO"))
        if w is None or w.decode("latin-1") != s["who"]:
            bad += 1
    s["bad"] = bad
    fno = lib.SDOpen(b"zzlog")                    # then everyone writes and reads back a record of its own size
    rid = ("thr%d" % i).encode()
    data = bytes([65 + i]) * (3000 + 7000 * i)
    lib.SDWrite(fno, rid, data)
    bar.wait()
    wrong = 0
    for _ in range(40):
        got = text(lib.SDRead(fno, rid, ctypes.byref(ctypes.c_int())))
        if got != data:
            wrong += 1
    s["wrong"] = wrong
    cw = 0                                        # and calls a catalogued subroutine, its returned argument read with SDGetArg
    for n in range(40):
        tok = ("t%d-%d" % (i, n)).encode()
        lib.SDCallx(b"zzcsub", ctypes.c_int16(2), tok, b"")
        got = text(lib.SDGetArg(2))
        if got != tok + b"/" + tok:
            cw += 1
    s["callx_wrong"] = cw
    bar.wait()
    lib.SDDelete(fno, rid)
    lib.SDDisconnect()


def guard(fn, *a):
    try:
        fn(*a)
    except Exception as e:                        # a broken barrier included
        errors.append(repr(e))


ts = [threading.Thread(target=guard, args=(phases, i)) for i in range(NT)]
for t in ts:
    t.start()
for t in ts:
    t.join(150)
out["sessions"] = sess

# a connection that fails keeps its error for its own thread while another thread connects and disconnects
bar4 = threading.Barrier(2, timeout=60)
box = {}


def failer():
    box["r"] = lib.SDConnect(b"127.0.0.1", 1, b"nobody", b"x", b"zzaa")
    box["e1"] = err().decode("latin-1")
    bar4.wait()                                   # the other thread connects and disconnects ten times now
    bar4.wait()
    box["e2"] = err().decode("latin-1")           # before SDConnected(), which clears the error text
    box["connected"] = lib.SDConnected()


def churner():
    bar4.wait()
    n = 0
    for _ in range(10):
        if lib.SDConnectLocal(b"zzaa") == 1:
            n += 1
            lib.SDDisconnect()
    box["churn"] = n
    bar4.wait()


t1 = threading.Thread(target=guard, args=(failer,))
t2 = threading.Thread(target=guard, args=(churner,))
t1.start(); t2.start(); t1.join(120); t2.join(120)
out["failed"] = box

# the library still works for one thread after all of that
ok = lib.SDConnectLocal(b"zzaa")
rv = text(lib.SDSystem(1012))
lib.SDDisconnect()
out["control"] = [ok, None if rv is None else rv.decode("latin-1")]
out["errors"] = errors
print("RESULT " + json.dumps(out))
'''


SDC = 'config("SDCLIENT") # 0'
MUTANTS = {
    # the SDCLIENT test of one request made never true (99 is no mode)
    "open": ('vb.open:\nif kernel(K$SDNET, -1)  or ' + SDC, 'vb.open:\nif kernel(K$SDNET, -1)  or config("SDCLIENT") = 99'),
    "openseq": ('vb.openseq:\nif kernel(K$SDNET, -1) or ' + SDC, 'vb.openseq:\nif kernel(K$SDNET, -1) or config("SDCLIENT") = 99'),
    "trans": ('trans.common:\nif kernel(K$SDNET, -1) or ' + SDC, 'trans.common:\nif kernel(K$SDNET, -1) or config("SDCLIENT") = 99'),
    "conv": ('conv.common:\n', None),       # built below: the line after the label differs from the others
    "execute": ('               if config("SDCLIENT") # 0  or kernel', '               if config("SDCLIENT") = 99  or kernel'),
    "call": ('config("SDCLIENT") = 2 or', 'config("SDCLIENT") = 99 or'),
    # NOT a fault: the repair of the defect row T6 finds (vb.call announces the refusal of an unflagged subroutine under SDCLIENT=2 and
    # then calls it all the same); with it the row passes.  Proposed for apisrvr, not applied to the tree.
    "fix-call-return": ("                     server.error = SV$ON.ERROR\n                  end\n               end\n\n               if arg.count then",
                        "                     server.error = SV$ON.ERROR\n                     return\n                  end\n               end\n\n               if arg.count then"),
    # vb.openseq stops asking the path question, or answers no to every pathname
    "path-none": ("   if not(kernel(K$PATH.OK, os.name)) then", "   if @false then"),
    "path-all": ("   if not(kernel(K$PATH.OK, os.name)) then", "   if @true then"),
}


def apply_mutant(name):
    """One deliberate fault in the SANDBOX's copy of apisrvr (recompiled there as the administrator), or in the fixture."""
    if name == "fixture-os-off":
        os.environ["QMC_FIXTURE_OS"] = "no"
        say("sandbox-qmclient: MUTANT fixture-os-off: the os-on account is registered os-off")
        return
    if name == "call-fixed":
        # the SDCLIENT=2 test of vb.call disabled ON TOP OF the repair: on the unrepaired code row T2-6 is red already, so only here
        # can it show that the test, and not the missing return, is what the row sees
        apply_mutant("fix-call-return")
        apply_mutant("call")
        return
    if name == "fix-execute-lib":
        # NOT a fault: the repair of the defect row T1-5 / T2-5 finds in sdclilib.c's SDExecute, built in the sandbox's tree copy
        src_c = os.path.join(q3.BOX, "tree", "gplsrc", "sdclilib.c")
        old = "  reply = malloc(reply_len + 1);\n  strcpy(reply, buff->data.execute.reply);\n"
        new = "  reply = malloc(reply_len + 1);\n  memcpy(reply, buff->data.execute.reply, reply_len);\n  reply[reply_len] = '\\0';\n"
        with open(src_c, encoding="utf-8", errors="replace") as f:
            csrc = f.read()
        if csrc.count(old) != 1:
            q3.bail("fix-execute-lib: SDExecute's copy is found %d times, not once" % csrc.count(old))
        with open(src_c, "w", encoding="utf-8") as f:
            f.write(csrc.replace(old, new))
        mk = subprocess.run(["make"], cwd=os.path.join(q3.BOX, "tree"), capture_output=True, text=True, errors="replace",
                            timeout=600)
        if mk.returncode != 0:
            q3.bail("fix-execute-lib: make failed:\n" + (mk.stdout + mk.stderr)[-600:])
        shutil.copy2(os.path.join(q3.BOX, "tree", "bin", "sdclilib.so"), os.path.join(q3.SYS, "bin", "sdclilib.so"))
        say("sandbox-qmclient: FIX fix-execute-lib: SDExecute copies reply_len bytes; sdclilib.so rebuilt and copied into the sandbox")
        return
    if name not in MUTANTS:
        q3.bail("no mutant named %s" % name)
    old, new = MUTANTS[name]
    path = os.path.join(q3.SYS, "gpl.bp", "apisrvr")
    with open(path, encoding="utf-8", errors="replace") as f:
        src = f.read()
    if name == "conv":
        old = "conv.common:\n"
        mk = "if kernel(K$SDNET, -1) or config(\"SDCLIENT\") # 0 then\n   cv.count"
        if src.count(mk) != 1:
            q3.bail("mutant conv: the conversion test is not found once (%d)" % src.count(mk))
        old, new = mk, mk.replace(SDC, 'config("SDCLIENT") = 99')
    if src.count(old) != 1:
        q3.bail("mutant %s: the text to change is found %d times, not once" % (name, src.count(old)))
    with open(path, "w", encoding="utf-8") as f:
        f.write(src.replace(old, new))
    out = q3.adm(["BASIC gpl.bp apisrvr"], internal=True)
    if not has(out, r"^Compiled 1 program\(s\) with no errors"):
        q3.bail("the mutant apisrvr did not compile:\n" + "\n".join(out[-8:]))
    say("sandbox-qmclient: MUTANT %s: %r -> %r" % (name, old.strip()[:70], new.strip()[:70]))


# T: SDExecute several times in a child process.  argv: the library, the count, the command.
EXEC_CHILD = r'''
import ctypes, sys
lib = ctypes.CDLL(sys.argv[1])
lib.SDExecute.restype = ctypes.c_void_p
lib.SDConnectLocal.restype = ctypes.c_int
if lib.SDConnectLocal(b"zzaa") != 1:
    print("NOCONNECT")
    sys.exit(2)
n = int(sys.argv[2])
for i in range(n):
    e = ctypes.c_int()
    p = lib.SDExecute(sys.argv[3].encode(), ctypes.byref(e))
    if i == 0:
        print("FIRST err", e.value, flush=True)         # before the free: the free is where the heap damage is found
    if p:
        lib.SDFree(ctypes.c_void_p(p))
print("LOOPS", n, flush=True)
lib.SDDisconnect()
'''


def cap_stderr(fn):
    """Run fn with the C library's stderr (fd 2) sent to a file: (its result, what was written to stderr).  The client prints an
    aborted request's message there (sdclilib.c Abort())."""
    with tempfile.TemporaryFile() as tf:
        saved = os.dup(2)
        os.dup2(tf.fileno(), 2)
        try:
            r = fn()
        finally:
            os.dup2(saved, 2)
            os.close(saved)
        tf.seek(0)
        return r, tf.read().decode("latin-1")


def s(b):
    """Text for a message: the marks as visible characters."""
    if b is None:
        return "None"
    return b.decode("latin-1").replace("\xfe", "<FM>").replace("\xfd", "<VM>").replace("\xfc", "<SM>")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        q3.bail("usage: sandbox-qmclient.py <dir> [--build]")
    q3.BOX = os.path.abspath(args[0])
    q3.SYS = os.path.join(q3.BOX, "sys")
    q3.SD = os.path.join(q3.SYS, "bin", "sd")
    q3.USER_PROGS = USER_PROGS
    BOX, SYS = q3.BOX, q3.SYS
    say("sandbox-qmclient: sandbox  %s" % BOX)
    if "--build" in sys.argv:
        if os.path.exists(BOX) and os.listdir(BOX):
            q3.bail("%s is not empty" % BOX)
        r = subprocess.run([sys.executable, q3.TOOL, BOX, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            q3.bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-qmclient: built, bootstrap passed")
    elif not os.path.isfile(q3.SD):
        q3.bail("%s holds no built sandbox (use --build, or point it at one)" % BOX)
    subprocess.run([sys.executable, q3.TOOL, BOX, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    say("\n--- preparation ------------------------------------------------------------------------------------------------")
    q3.prepare()
    acct = q3.build_account("zzaa")
    q3.build_account("zzab")                      # a second account, for SDLogto
    q3.plain("zzaa", ["CREATE.FILE zzcl DYNAMIC", "RUN bp zzclmk", "CREATE.INDEX zzcl NAME", "BUILD.INDEX zzcl NAME", "CREATE.FILE zzlog DYNAMIC",
                         "CREATE.FILE zzdir DIRECTORY", "CREATE.FILE zzsq DYNAMIC"])
    csub = q3.plain("zzaa", ["BASIC bp zzcsub", "CATALOG bp zzcsub LOCAL"])      # part R's subroutine
    csub += q3.plain("zzaa", ["BASIC bp zzcmk zzcok", "CATALOG bp zzcmk LOCAL", "CATALOG bp zzcok LOCAL"])      # part T's two
    if not has(csub, r"^Compiled 2 program\(s\) with no errors"):
        q3.bail("part T's subroutines did not compile: " + repr(csub[-6:]))
    mutant = os.environ.get("QMC_MUTANT", "")
    if mutant:
        apply_mutant(mutant)
    ix = q3.plain("zzaa", ["RUN bp zzclix"])
    if not tag(ix, "NAMES"):
        q3.bail("the fixture file was not made: " + repr(ix))

    # the oracle for the revision
    with open(os.path.join(HERE, "..", "gplsrc", "revstamp.h")) as f:
        m = re.search(r'#define\s+SD_REV_STAMP\s+"([^"]+)"', f.read())
    rev = m.group(1).encode() if m else None
    if rev is None:
        q3.bail("no SD_REV_STAMP in revstamp.h")

    os.environ["SD_CONFIG"] = os.path.join(BOX, "sd.conf")
    lib = ctypes.CDLL(os.path.join(SYS, "bin", "sdclilib.so"))
    for fn in ("SDRevision", "SDGetVar", "SDSystem", "SDIndices", "SDTrans", "SDRTrans", "SDRead", "SDReadu", "SDExecute", "SDError",
               "SDEvaluate", "SDEvalConv", "SDIConv", "SDOConv", "SDIConvs", "SDOConvs", "SDChange", "SDRespond",
               "SDReadSeq", "SDReadBlk"):
        getattr(lib, fn).restype = ctypes.c_void_p
    lib.SDOpen.restype = ctypes.c_int
    lib.SDStatus.restype = ctypes.c_int
    lib.SDConnectLocal.restype = ctypes.c_int

    def text(ptr):
        if not ptr:
            return None
        b = ctypes.string_at(ptr)
        lib.SDFree(ctypes.c_void_p(ptr))
        return b

    def call(name, *a):
        argt = []
        for x in a:
            argt.append(x)
        return text(getattr(lib, name)(*argt))

    try:
        say("\n--- A. SDRevision ---------------------------------------------------------------------------------------------")
        r0 = call("SDRevision")
        row("A1: before a connection SDRevision is the client's revision alone (SD_REV_STAMP of revstamp.h)", r0 == rev, s(r0) + " vs " + s(rev))
        ok = lib.SDConnectLocal(b"zzaa")
        row("A0: a local API session connects to the fixture account", ok == 1, "connect %r, error %s" % (ok, s(ctypes.string_at(lib.SDError()))))   # SDError's text is the library's own, not freed
        if ok != 1:
            q3.bail("no API session; nothing below can run")
        r1 = call("SDRevision")
        row("A2: connected it is client, a value mark, server: both this build's revision", r1 == rev + VM + rev, s(r1))
        sy = call("SDSystem", 1012)
        row("A3: SDSystem(1012) is the server revision, the same text", sy == rev, s(sy))

        say("\n--- B. SDGetVar -----------------------------------------------------------------------------------------------")
        out = text(lib.SDExecute(b"SELECT zzcl", ctypes.byref(ctypes.c_int())))
        sel = call("SDGetVar", b"@SELECTED")
        row("B1: @SELECTED after a select of the three records is 3, as a string", sel == b"3", s(sel))
        row("B1: ... with no @ and in lower case the same", call("SDGetVar", b"selected") == b"3" and call("SDGetVar", b"SELECTED") == b"3", "")
        pth = call("SDGetVar", b"@PATH")
        row("B2: @PATH is the account's directory", pth is not None and os.path.realpath(pth.decode()) == os.path.realpath(acct), s(pth))
        row("B2: @WHO is the account's name", call("SDGetVar", b"@WHO") == b"zzaa", s(call("SDGetVar", b"@WHO")))
        row("B3: a name it does not know gives the null string, not an error", call("SDGetVar", b"@NOSUCHTHING") == b"", s(call("SDGetVar", b"@NOSUCHTHING")))
        lib.SDExecute(b'SELECT zzcl WITH NAME = "Widget"', ctypes.byref(ctypes.c_int()))
        row("B4: CONTROL: after a select of one record @SELECTED is 1 (the value follows the session, it is not a constant)",
            call("SDGetVar", b"@SELECTED") == b"1", s(call("SDGetVar", b"@SELECTED")))
        row("B5: @USERNO is a user number, a plain integer", re.fullmatch(rb"\d+", call("SDGetVar", b"@USERNO") or b"") is not None,
            s(call("SDGetVar", b"@USERNO")))

        say("\n--- C. SDSystem -----------------------------------------------------------------------------------------------")
        row("C1: SDSystem(1052), the count of child phantoms, is 0 in a session that started none", call("SDSystem", 1052) == b"0", s(call("SDSystem", 1052)))
        row("C2: a key the server has no meaning for answers 0 and the session goes on", call("SDSystem", 99999) in (b"0", b""), s(call("SDSystem", 99999)))
        row("C3: CONTROL: the session still works afterwards (SDSystem(1012) again)", call("SDSystem", 1012) == rev, "")

        say("\n--- D. SDIndices ----------------------------------------------------------------------------------------------")
        fno = lib.SDOpen(b"zzcl")
        row("D0: the file opens through the API", fno >= 1, str(fno))
        names = call("SDIndices", fno, b"")
        want_names = (tag(ix, "NAMES") or [""])[0].replace("/", "\xfe").encode("latin-1")
        row("D1: with no index name SDIndices gives the file's index names (INDICES(f) in a session)", names == want_names, s(names) + " vs " + s(want_names))
        det = call("SDIndices", fno, b"NAME")
        want = (tag(ix, "DET") or [""])[0].replace("/", "\xfe").replace("|", "\xfd").replace("~", "\xfc").encode("latin-1")
        row("D2: with a name it gives the details of the index (INDICES(f, name) in a session)", det == want and det != b"", s(det) + " vs " + s(want))
        row("D3: an index the file has not gives the null string", call("SDIndices", fno, b"NOPE") == b"", s(call("SDIndices", fno, b"NOPE")))
        row("D4: CONTROL: a file number that was never opened is refused (nothing returned, no crash)",
            call("SDIndices", 99, b"") in (b"", None), s(call("SDIndices", 99, b"")))

        say("\n--- E. SDTrans and SDRTrans -----------------------------------------------------------------------------------")
        rec1 = text(lib.SDRead(fno, b"r1", ctypes.byref(ctypes.c_int())))
        rec3 = text(lib.SDRead(fno, b"r3", ctypes.byref(ctypes.c_int())))
        row("E0: the records read back as written (the oracle)", rec1 == b"Widget" + FM + b"5" + FM + b"red" + VM + b"blue", s(rec1))
        row("E1: SDTrans of a dictionary field (NAME) of r1 is Widget", call("SDTrans", b"zzcl", b"r1", b"NAME", b"X") == b"Widget", s(call("SDTrans", b"zzcl", b"r1", b"NAME", b"X")))
        row("E1: ... a field number (2) the same way: 5", call("SDTrans", b"zzcl", b"r1", b"2", b"X") == b"5", "")
        low = rec1.replace(VM, SM).replace(FM, VM)
        whole = call("SDTrans", b"zzcl", b"r1", b"-1", b"X")
        row("E2: field -1 is the whole record with the marks lowered one level (field marks become value marks)", whole == low, s(whole) + " vs " + s(low))
        raw = call("SDRTrans", b"zzcl", b"r1", b"-1", b"X")
        row("E2: SDRTrans leaves the marks as they are: the record exactly as SDRead has it", raw == rec1, s(raw))
        multi = call("SDTrans", b"zzcl", b"r1" + VM + b"r2", b"NAME", b"X")
        row("E3: a list of ids gives the answers as a value mark list: Widget, Gadget", multi == b"Widget" + VM + b"Gadget", s(multi))
        mv = call("SDTrans", b"zzcl", b"r3", b"TAGS", b"X")
        rmv = call("SDRTrans", b"zzcl", b"r3", b"TAGS", b"X")
        row("E4: a multivalued field: SDRTrans gives its value marks, SDTrans lowers them to subvalue marks",
            rmv == b"a" + VM + b"b" + VM + b"c" and mv == b"a" + SM + b"b" + SM + b"c", s(mv) + " / " + s(rmv))
        row("E5: a record that is not there: X gives the null string, C gives the id", call("SDTrans", b"zzcl", b"nope", b"NAME", b"X") == b""
            and call("SDTrans", b"zzcl", b"nope", b"NAME", b"C") == b"nope", s(call("SDTrans", b"zzcl", b"nope", b"NAME", b"C")))
        row("E5: no action means X", call("SDTrans", b"zzcl", b"nope", b"NAME", b"") == b"", "")
        row("E6: a file that is not there gives the null string", call("SDTrans", b"nosuchfile", b"r1", b"NAME", b"X") == b"", "")
        row("E6: so does a field the dictionary has not",
            call("SDTrans", b"zzcl", b"r1", b"NOSUCH", b"X") in (b"", b"r1"), s(call("SDTrans", b"zzcl", b"r1", b"NOSUCH", b"X")))
        bad = call("SDTrans", b"zzcl", b"r1", b"NAME", b"B")
        row("E7: the B (binary) action is refused: nothing returned", bad == b"" or bad is None, s(bad))
        row("E7: CONTROL: the session still works afterwards", call("SDTrans", b"zzcl", b"r2", b"QTY", b"X") == b"7", "")
        say("\n--- F. NON.DURABLE.TXN (the program form) ---------------------------------------------------------------------")

        def disk():
            """What is on disk for the records of the scenarios, read by a new session."""
            out = q3.plain("zzaa", ["RUN bp zzndr"])
            return {m.group(1): m.group(2) for m in (re.match(r"^R\[([a-z0-9]+)=(.*)\]$", t) for t in out) if m}

        def reset():
            q3.plain("zzaa", ["DELETE zzcl p1", "DELETE zzcl c1", "DELETE zzcl both", "DELETE zzcl lk", "RUN bp zzndw"])

        def run(prog, sc):
            reset()
            out = q3.plain("zzaa", ["RUN bp %s %s" % (prog, sc)])
            return out, disk()

        out, d = run("zzndt", "commit")
        cache = (tag(out, "CACHE") or [""])[0]
        row("F1: non-durable, the child's COMMIT writes nothing: the cache lists the child's records under the PARENT's transaction "
            "(p1, both, c1 - all W, one transaction number)",
            len(cache.split("/")) == 3 and len({e.split("|")[0] for e in cache.split("/")}) == 1
            and {e.split("|")[2] for e in cache.split("/")} == {"p1", "c1", "both"}, cache)
        row("F1: ... and the parent's COMMIT then writes them all, the later write of 'both' (the child's) winning",
            d.get("p1") == "parent" and d.get("c1") == "child" and d.get("both") == "child second", repr(d))
        out, d = run("zzndt", "abort")
        row("F2: non-durable, the parent ABORTS after the child committed: neither the parent's nor the child's record reached the disk",
            d.get("p1") == "-" and d.get("c1") == "-" and d.get("both") == "-", repr(d))
        out, d = run("zzdur", "abort")
        row("F3: CONTROL, the same program without the mode: the child's COMMIT is durable and survives the parent's abort "
            "(c1 and the child's 'both' on disk, p1 not)", d.get("c1") == "child" and d.get("both") == "child second" and d.get("p1") == "-",
            repr(d))
        out, d = run("zzdur", "commit")
        row("F3: CONTROL, durable, parent commits: everything on disk too", d.get("p1") == "parent" and d.get("c1") == "child", repr(d))
        out, d = run("zzndt", "delold")
        row("F4: non-durable: a record the child deleted comes back when the parent aborts ('old' still on disk)", d.get("old") == "old data", repr(d))
        out, d = run("zzdur", "delold")
        row("F4: CONTROL, durable: the same delete stays deleted", d.get("old") == "-", repr(d))
        out, d = run("zzndt", "lock")
        row("F5: the child's lock is held after its non-durable COMMIT (RECORDLOCKED non-zero) and released when the parent commits (0)",
            tag(out, "LOCK1") not in ([], ["0"]) and tag(out, "LOCK2") == ["0"], repr((tag(out, "LOCK1"), tag(out, "LOCK2"))))
        out, d = run("zzdur", "lock")
        row("F5: CONTROL, durable: the child's COMMIT releases its lock at once (0)", tag(out, "LOCK1") == ["0"], repr(tag(out, "LOCK1")))
        row("F6: the transaction level is back to 0 after both end", tag(out, "DEPTH") == ["0"], repr(tag(out, "DEPTH")))

        say("\n--- G. SDTxn --------------------------------------------------------------------------------------------------")
        reset()
        fno2 = lib.SDOpen(b"zzcl")
        row("G0: the file is open", fno2 >= 1, str(fno2))

        def api_write(i, v):
            text(lib.SDReadu(fno2, i, 0, ctypes.byref(ctypes.c_int())))       # the lock a transaction's write needs
            lib.SDWrite(fno2, i, v)

        lib.SDTxn(1)
        api_write(b"p1", b"parent")
        lib.SDTxn(1)
        api_write(b"c1", b"child")
        lib.SDTxn(4)
        row("G1: SDTxn(4), a non-durable commit of the nested transaction, leaves STATUS 0 and the session usable", lib.SDStatus() == 0,
            str(lib.SDStatus()))
        lib.SDTxn(3)
        d = disk()
        row("G2: SDTxn(3), the parent aborted: neither record reached the disk", d.get("p1") == "-" and d.get("c1") == "-", repr(d))
        lib.SDTxn(1)
        api_write(b"p1", b"parent")
        lib.SDTxn(1)
        api_write(b"c1", b"child")
        lib.SDTxn(2)
        lib.SDTxn(3)
        d = disk()
        row("G3: CONTROL, SDTxn(2) a durable commit of the child: c1 survives the parent's abort, p1 does not",
            d.get("c1") == "child" and d.get("p1") == "-", repr(d))
        lib.SDTxn(1)
        api_write(b"p1", b"parent")
        lib.SDTxn(2)
        d = disk()
        row("G4: a top-level SDTxn(2) writes: p1 on disk", d.get("p1") == "parent", repr(d))
        lib.SDTxn(2)
        err = ctypes.string_at(lib.SDError()) if lib.SDError() else b""
        row("G5: a commit with no transaction is refused, with a message, and the session goes on",
            lib.SDStatus() != 0 or b"Transaction mode" in err, repr((lib.SDStatus(), err)))
        lib.SDTxn(7)
        err = ctypes.string_at(lib.SDError()) if lib.SDError() else b""
        row("G5: mode 7 is refused the same way", b"Transaction mode" in err, repr(err))
        row("G5: CONTROL: after the refusals the session still answers", call("SDSystem", 1012) == rev, "")

        say("\n--- H. SDEvaluate and SDEvalConv ------------------------------------------------------------------------------")

        def err():
            p = lib.SDError()
            return ctypes.string_at(p) if p else b""

        IM = b"\xff"
        flds = rec1.split(FM)                       # the oracle: the record the probe wrote, taken apart here
        day = (datetime.date(2026, 10, 15) - datetime.date(1967, 12, 31)).days
        dfno = lib.SDOpen(b"DICT zzcl")
        row("H0: the dictionary opens through the API (SDOpen of DICT zzcl)", dfno >= 1, str(dfno))
        # 18 Oct 26, S.65: the word dict in ANY case.  The SDNet handler (gpl.bp/netfile) sends "dict <name>" in lower case; apisrvr's vb.open used the single-argument OPEN, which
        # _voc_ref understands only with an upper case DICT, so a REMOTE dictionary was never opened (ELSE 3007) and the fake server, which had always accepted it, hid the defect.
        # The oracle is the same dictionary item read through the upper case open.
        d_item = lib.SDRead(dfno, b"DOUBLE", ctypes.byref(ctypes.c_int()))
        want_item = text(d_item)
        for spelling in (b"dict zzcl", b"Dict zzcl", b"dIcT zzcl", b"dict  zzcl"):
            lo = lib.SDOpen(spelling)
            got_item = text(lib.SDRead(lo, b"DOUBLE", ctypes.byref(ctypes.c_int()))) if lo >= 1 else None
            row("H0a: SDOpen of %r opens the dictionary of zzcl (a file number, and the item DOUBLE reads back as through DICT zzcl)" % s(spelling),
                lo >= 1 and want_item is not None and got_item == want_item and len(want_item.split(FM)) == 6, "fno=%s item=%r want=%r err=%s" % (lo, got_item, want_item, s(err())))
        no_such = lib.SDOpen(b"dict nosuchfile")
        row("H0b: SDOpen of dict and a file that is not there gives 0, no file number", no_such == 0, "fno=%s err=%s" % (no_such, s(err())))
        plain = lib.SDOpen(b"zzcl")
        plain_item = text(lib.SDRead(plain, b"DOUBLE", ctypes.byref(ctypes.c_int()))) if plain >= 1 else None
        row("H0c: CONTROL: the DATA file zzcl opened by its plain name does not hold the dictionary item DOUBLE (so the opens above reached the dictionary, not the data)",
            plain >= 1 and plain_item in (None, b""), "fno=%s item=%r" % (plain, plain_item))
        no_dict = lib.SDOpen(b"dictzzcl")
        row("H0d: CONTROL: 'dictzzcl' (no space) is a plain file name, not a dictionary open: gives 0", no_dict == 0, "fno=%s" % no_dict)

        def ev(name, data=rec1, id=b"r1", fn="SDEvaluate", f=None):
            return call(fn, dfno if f is None else f, name, data, id)

        row("H1: SDEvaluate of a D item (NAME) is the record's field 1", ev(b"NAME") == flds[0], s(ev(b"NAME")))
        row("H1: ... the data given is what is evaluated, not the stored record: other data, other answer",
            ev(b"NAME", b"Other" + FM + b"1") == b"Other", s(ev(b"NAME", b"Other" + FM + b"1")))
        row("H2: an I-type (QTY * 2) is evaluated, though the dictionary record holds no object code", ev(b"DOUBLE") == str(int(flds[1]) * 2).encode(),
            s(ev(b"DOUBLE")))
        drec = text(lib.SDRead(dfno, b"DOUBLE", ctypes.byref(ctypes.c_int())))
        row("H2: ... and the dictionary was NOT written to by the evaluation (still its six fields, no object code in field 16)",
            drec is not None and len(drec.split(FM)) == 6, s(drec))
        row("H3: an I-type that is @ID answers the id given", ev(b"IDCOPY") == b"r1" and ev(b"IDCOPY", id=b"zz9") == b"zz9", s(ev(b"IDCOPY")))
        row("H3: ... and the null id gives the null string", ev(b"IDCOPY", id=b"") == b"", s(ev(b"IDCOPY", id=b"")))
        row("H5: several names (value marks) give the answers joined by item marks (character 255)",
            ev(b"NAME" + VM + b"QTY") == flds[0] + IM + flds[1], s(ev(b"NAME" + VM + b"QTY")))
        row("H6: SDEvaluate applies NO conversion: the I-type UPNAME (conversion MCU) is Widget", ev(b"UPNAME") == b"Widget", s(ev(b"UPNAME")))
        row("H6: SDEvalConv applies it: WIDGET", ev(b"UPNAME", fn="SDEvalConv") == b"WIDGET", s(ev(b"UPNAME", fn="SDEvalConv")))
        row("H6: SDEvalConv of an item with no conversion is the plain value (NAME)", ev(b"NAME", fn="SDEvalConv") == flds[0], "")
        dated = rec1 + FM + str(day).encode()
        row("H7: a date item: SDEvaluate gives the day number, SDEvalConv the date its D4/ conversion makes",
            ev(b"WHEN", dated) == str(day).encode() and ev(b"WHEN", dated, fn="SDEvalConv") == b"10/15/2026",
            s(ev(b"WHEN", dated)) + " / " + s(ev(b"WHEN", dated, fn="SDEvalConv")))
        row("H8: a multivalued item: SDEvaluate keeps the values, SDEvalConv converts each (MCU: RED and BLUE)",
            ev(b"TAGU") == b"red" + VM + b"blue" and ev(b"TAGU", fn="SDEvalConv") == b"RED" + VM + b"BLUE",
            s(ev(b"TAGU")) + " / " + s(ev(b"TAGU", fn="SDEvalConv")))
        row("H8: several names with a conversion: NAME is left, UPNAME converted",
            ev(b"NAME" + VM + b"UPNAME", fn="SDEvalConv") == flds[0] + IM + b"WIDGET", s(ev(b"NAME" + VM + b"UPNAME", fn="SDEvalConv")))
        row("H9: a name in lower case finds the item (a dictionary folds case)", ev(b"double") == ev(b"DOUBLE") and ev(b"double") != b"", s(ev(b"double")))
        row("H10: an item that is not in the dictionary gives nothing, and no error text about types or compiling",
            ev(b"NOSUCH") == b"" and b"defines data" not in err() and b"compiled" not in err(), s(err()))
        row("H11: a phrase (type PH) defines no data: nothing, and the error says so", ev(b"PH1") == b"" and b"defines data" in err(), s(err()))
        # 31 Oct 26: after H10 and H11 because the client keeps the last error text: an error left by an earlier row is read by H10's "no error" test
        row("H11b: an A item is not evaluated any more (31 Oct 26: the A and S types are gone): nothing, and the error says it defines no data",
            ev(b"ANAME") == b"" and b"ANAME" in err() and b"defines data" in err() and ev(b"ATRIPLE") == b"" and b"ATRIPLE" in err() and b"defines data" in err(), s(err()))
        row("H12: an I-type that will not compile gives nothing, and the error says it cannot be compiled",
            ev(b"BADI") == b"" and b"cannot be compiled" in err(), s(err()))
        row("H13: a file number that was never opened is refused with the file number message", ev(b"NAME", f=99) == b"" and b"file number" in err().lower(), s(err()))
        idb = call("SDGetVar", b"@ID")
        ev(b"IDCOPY", id=b"r3")
        row("H14: CONTROL: @ID on the server is what it was before an evaluation that set it (the environment is put back)",
            call("SDGetVar", b"@ID") == idb, s(idb) + " -> " + s(call("SDGetVar", b"@ID")))
        row("H15: CONTROL: after the refusals the session still answers", ev(b"NAME") == flds[0], "")

        say("\n--- I. SDIConv, SDOConv, SDIConvs and SDOConvs ----------------------------------------------------------------")
        d1 = str(day).encode()
        d2 = str(day + 1).encode()
        row("I1: SDOConv of the day number with D4/ is the date, and the status is 0",
            call("SDOConv", d1, b"D4/") == b"10/15/2026" and lib.SDStatus() == 0, s(call("SDOConv", d1, b"D4/")))
        row("I2: SDIConv of that date with D4/ is the day number, and the status is 0",
            call("SDIConv", b"10/15/2026", b"D4/") == d1 and lib.SDStatus() == 0, s(call("SDIConv", b"10/15/2026", b"D4/")))
        r = call("SDIConv", b"13/45/2026", b"D4/")
        bad_status = lib.SDStatus()
        row("I3: an impossible date gives the null string and a NON-ZERO status, the conversion's own", r == b"" and bad_status != 0,
            "result %s status %d" % (s(r), bad_status))
        call("SDIConv", b"10/15/2026", b"D4/")
        row("I3: CONTROL: the next successful conversion leaves the status 0 again (it is per call, not left over)", lib.SDStatus() == 0, str(lib.SDStatus()))
        two = d1 + VM + d2
        row("I4: SDOConvs converts each value of a dynamic array in turn",
            call("SDOConvs", two, b"D4/") == b"10/15/2026" + VM + b"10/16/2026", s(call("SDOConvs", two, b"D4/")))
        row("I4: ... each field the same way", call("SDOConvs", d1 + FM + d2, b"D4/") == b"10/15/2026" + FM + b"10/16/2026", "")
        row("I4: CONTROL: SDOConv of the same array does not (it treats it as one string), so the plural is not the singular",
            call("SDOConv", two, b"D4/") != b"10/15/2026" + VM + b"10/16/2026", s(call("SDOConv", two, b"D4/")))
        row("I5: SDIConvs converts each value of a dynamic array of dates", call("SDIConvs", b"10/15/2026" + VM + b"10/16/2026", b"D4/") == two,
            s(call("SDIConvs", b"10/15/2026" + VM + b"10/16/2026", b"D4/")))
        row("I6: other codes: MCU upper-cases, MD2 turns 12.34 into 1234",
            call("SDOConv", b"widget", b"MCU") == b"WIDGET" and call("SDIConv", b"12.34", b"MD2") == b"1234",
            s(call("SDOConv", b"widget", b"MCU")) + " / " + s(call("SDIConv", b"12.34", b"MD2")))
        call("SDIConv", b"x", b"ZZ")
        row("I7: a code that does not exist leaves a non-zero status", lib.SDStatus() != 0, str(lib.SDStatus()))
        row("I8: null data is converted to the null string", call("SDOConv", b"", b"D4/") == b"", s(call("SDOConv", b"", b"D4/")))
        row("I9: CONTROL: the session still answers", call("SDSystem", 1012) == rev, "")

        # ------------------------------------------------------------------------------------------------------ J
        say("\n--- J. sessions: more than four, one waiting for input while another comes and goes, a failed connect, SDRecordlocked ---")
        main_idx = lib.SDGetSession()
        idxs = [main_idx]
        okc = []
        for _ in range(5):
            r = lib.SDConnectLocal(b"zzaa")
            okc.append(r)
            if r == 1:
                idxs.append(lib.SDGetSession())
        row("J1: six local sessions open at once, each with an index of its own (sheet 134: the client held four)",
            okc == [1] * 5 and len(set(idxs)) == 6, "connects %r, indexes %r" % (okc, idxs))
        answers = 0
        for i in idxs:
            if lib.SDSetSession(i) and call("SDSystem", 1012) == rev:
                answers += 1
        row("J1: ... and each answers when it is selected", answers == len(idxs), "%d of %d" % (answers, len(idxs)))
        for i in idxs[1:]:
            lib.SDSetSession(i)
            lib.SDDisconnect()
        row("J1: CONTROL: the first session is still there and answers after the five others were disconnected",
            lib.SDSetSession(main_idx) == 1 and call("SDSystem", 1012) == rev, "")

        perr = ctypes.c_int(-1)
        lib.SDExecute(b"RUN bp zzprmp", ctypes.byref(perr))
        prompted = perr.value
        r = lib.SDConnectLocal(b"zzaa")
        other = lib.SDGetSession()
        lib.SDDisconnect()
        lib.SDSetSession(main_idx)
        rerr = ctypes.c_int(-1)
        out2 = text(lib.SDRespond(b"hello", ctypes.byref(rerr)))
        row("J2: a session waiting for input (EXECUTING) is not harmed when another one connects and disconnects (sheet 281): the answer "
            "reaches the command and its output comes back", prompted == 5 and r == 1 and out2 is not None and b"GOT[hello]" in out2
            and rerr.value == 0, "prompt status %d, second connect %d, reply %s, status %d" % (prompted, r, s(out2), rerr.value))
        row("J2: CONTROL: the session is an ordinary one again afterwards", call("SDSystem", 1012) == rev, "")

        r = lib.SDConnect(b"127.0.0.1", 1, b"nobody", b"x", b"zzaa")
        failed_error = err()
        row("J3: a connect to a port nothing listens on fails, says why, and the session it started from can be selected and used again",
            r == 0 and failed_error != b"" and lib.SDSetSession(main_idx) == 1 and call("SDSystem", 1012) == rev,
            "result %d, error %s" % (r, s(failed_error)))

        rl = getattr(lib, "SDRecordlocked", None)
        if rl is None:
            row("J4: SDRecordlocked is in the library (sheet 262)", False, "not there")
        else:
            rl.restype = ctypes.c_int
            lf = lib.SDOpen(b"zzcl")
            e0 = ctypes.byref(ctypes.c_int())
            s_none = rl(lf, b"r1")
            text(lib.SDReadu(lf, b"r1", 0, e0))
            s_mine_u = rl(lf, b"r1")
            lib.SDRelease(lf, b"r1")
            s_rel = rl(lf, b"r1")
            text(lib.SDReadl(lf, b"r1", 0, e0))
            s_mine_l = rl(lf, b"r1")
            lib.SDRelease(lf, b"r1")
            row("J4: SDRecordlocked: 0 when nothing is held, 2 for this session's update lock, 0 after SDRelease, 1 for its read lock",
                (s_none, s_mine_u, s_rel, s_mine_l) == (0, 2, 0, 1), repr((s_none, s_mine_u, s_rel, s_mine_l)))
            lib.SDConnectLocal(b"zzaa")
            idx_b = lib.SDGetSession()
            fb = lib.SDOpen(b"zzcl")
            text(lib.SDReadu(fb, b"r1", 0, e0))
            lib.SDSetSession(main_idx)
            s_other = rl(lf, b"r1")
            lib.SDSetSession(idx_b)
            lib.SDRelease(fb, b"r1")
            lib.SDDisconnect()
            lib.SDSetSession(main_idx)
            s_after = rl(lf, b"r1")
            row("J4: a lock held by ANOTHER session shows as -2 (update) to this one, and 0 once it is released", (s_other, s_after) == (-2, 0),
                repr((s_other, s_after)))
            bad_fno = rl(99, b"r1")
            row("J4: a file number that was never opened gives 0 and says so (no abort, no crash)", bad_fno == 0 and b"file number" in err().lower(),
                "%d, %s" % (bad_fno, s(err())))

        # Python ignores SIGPIPE, so a missing guard in the library can never show in this process.  A child process with the signal
        # at its default action starts a local session, kills the server (as the system or an administrator might) and sends a
        # request to it: the request must fail, and the child must live to say so.
        child = (
            "import ctypes, os, signal, sys, time\n"
            "signal.signal(signal.SIGPIPE, signal.SIG_DFL)\n"
            "lib = ctypes.CDLL(sys.argv[1])\nlib.SDSystem.restype = ctypes.c_void_p\n"
            "if lib.SDConnectLocal(b'zzaa') != 1:\n    print('NOCONNECT'); sys.exit(2)\n"
            "me = str(os.getpid())\n"
            "def ppid(p):\n"
            "    try: return open('/proc/%s/stat' % p).read().rsplit(')', 1)[1].split()[1]\n"
            "    except (OSError, IndexError): return None   # a process that ended between listdir and open: not ours\n"
            "kids = [int(p) for p in os.listdir('/proc') if p.isdigit() and ppid(p) == me]\n"
            "for k in kids: os.kill(k, signal.SIGKILL)\n"
            "time.sleep(1)\nprint('KILLED', len(kids))\nr = lib.SDSystem(1012)\n"
            "print('ANSWER', 'EMPTY' if (not r or ctypes.string_at(r) == b'') else 'GOT')\nprint('SURVIVED')\nlib.SDDisconnect()\nprint('DISCONNECTED')\n")
        try:
            cp = subprocess.run([sys.executable, "-I", "-c", child, os.path.join(SYS, "bin", "sdclilib.so")], capture_output=True, text=True,
                                timeout=40, env=dict(os.environ))
            cout, crc = cp.stdout.split(), cp.returncode
            if crc != 0:
                cout = cout + ["STDERR:", cp.stderr.strip()[-300:]]
        except subprocess.TimeoutExpired:
            cout, crc = ["TIMEOUT"], None
        row("J5: with SIGPIPE at its default action, a request to a server that was killed fails (nothing back) and the program lives "
            "to disconnect: the write is a failed write, not a signal", "SURVIVED" in cout and "DISCONNECTED" in cout and "EMPTY" in cout and crc == 0,
            "output %r, exit %r" % (cout, crc))

        # ------------------------------------------------------------------------------------------------------ L
        say("\n--- L. SDDcount and SDChange against SD's own DCOUNT() and CHANGE() ------------------------------------------")
        sout = q3.plain("zzaa", ["RUN bp zzstr"])
        for t, src_, dl_ in (("D1", b"a,b,c", b","), ("D2", b"a::b::c::d", b"::"), ("D3", b"aaaa", b"aa"), ("D4", b"a,b", b",,"),
                             ("D5", b"", b","), ("D6", b"ab--cd--", b"--")):
            want = (tag(sout, t) or [None])[0]
            got = lib.SDDcount(src_, dl_)
            row("L1: SDDcount(%s, %s) is what DCOUNT() gives (%s)%s" % (s(src_), s(dl_), want, "  <- a multi-character delimiter (sheet 260)" if len(dl_) > 1 else ""),
                want is not None and str(got) == want, "got %d" % got)
        row("L1: no delimiter gives 0, as it always did", lib.SDDcount(b"abc", b"") == 0, "")
        for t, args in (("C1", (b"aaaa", b"aa", b"b", 0, 0)), ("C2", (b"aaa", b"aa", b"b", 0, 0)), ("C3", (b"abababa", b"aba", b"X", 0, 0)),
                        ("C4", (b"abcabcabcabc", b"abc", b"Z", 2, 2)), ("C5", (b"hello", b"l", b"", 0, 0)), ("C6", (b"hello", b"xyz", b"Q", 0, 0)),
                        ("C7", (b"xx--xx--xx", b"--", b"<>", 0, 0)), ("C8", (b"aXbXc", b"X", b"YY", 1, 2))):
            want = (tag(sout, t) or [None])[0]
            got = text(lib.SDChange(*args))
            row("L2: SDChange%s is what CHANGE() gives (%s)%s" % (repr(args[:3] + args[3:]).replace("b'", "'"), want,
                                                                   "  <- overlapping strings (sheet 261)" if t in ("C1", "C2", "C3") else ""),
                want is not None and got is not None and got.decode("latin-1") == want, "got %s" % s(got))

        # ------------------------------------------------------------------------------------------------------ U
        say("\n--- U. SDChecksum against SD's own CHECKSUM() and against the algorithm written out here -----------------------")

        def ref_checksum(b):
            """The default CHECKSUM(): rotate left one bit, exclusive-or the next byte as a SIGNED char (sign-extended)."""
            acc = 0
            for ch in b:
                v = ch - 256 if ch > 127 else ch
                acc = ((acc << 1) | (acc >> 31)) & 0xFFFFFFFF
                acc ^= v & 0xFFFFFFFF
            return acc - (1 << 32) if acc >= (1 << 31) else acc

        fn = getattr(lib, "SDChecksum", None)
        row("U0: the library exports SDChecksum", fn is not None, "no such symbol in sdclilib.so")
        if fn is not None:
            fn.argtypes = [ctypes.c_char_p]
            fn.restype = ctypes.c_int
        uout = q3.plain("zzaa", ["RUN bp zzsum"])
        ucases = (("U1", b"ABCDE"), ("U2", b""), ("U3", b"a"), ("U4", b"hello world"), ("U5", b"a\xc8z"), ("U6", b"\xff"),
                  ("U7", b"\x80\x80"), ("U8", b"0123456789" * 1000), ("U9", b"ab" + VM + b"cd" + FM + b"e"),
                  ("UA", b"abcdefghijklmnopqrstuvwxyz0123456789"))
        seen = set()
        for t, data in ucases:
            want = (tag(uout, t) or [None])[0]
            got = fn(data) if fn is not None else None
            refv = ref_checksum(data)
            seen.add(got)
            row("%s: SDChecksum(%s) is %s, what CHECKSUM() gives%s" % (t, s(data)[:30], want,
                                                                       "  <- a byte of 128 or more is sign-extended, as the server reads it" if any(c > 127 for c in data) and len(data) < 8 and b"\xfd" not in data else ""),
                want is not None and got is not None and str(got) == want and got == refv,
                "client %s, server %s, written out here %s" % (got, want, refv))
        row("U11: CONTROL: ten different strings give more than five different values (it is not a constant)", len(seen) > 5, "values %s" % sorted(map(str, seen)))
        row("U12: the null string is 0", fn is not None and fn(b"") == 0, "")
        # a child process that loads the library and never connects: SDConnected() is false, and the answer is the same
        cp = subprocess.run([sys.executable, "-I", "-c",
                             "import ctypes, sys\nlib = ctypes.CDLL(sys.argv[1])\nlib.SDChecksum.argtypes = [ctypes.c_char_p]\n"
                             "print('CONNECTED', lib.SDConnected())\nprint('SUM', lib.SDChecksum(b'ABCDE'))\n",
                             os.path.join(SYS, "bin", "sdclilib.so")], capture_output=True, text=True, timeout=30)
        row("U13: needs no connection: a process that never connected (SDConnected() is 0) gets the same value",
            ("CONNECTED 0" in cp.stdout) and ("SUM %d" % ref_checksum(b"ABCDE")) in cp.stdout, "output %r %r" % (cp.stdout, cp.stderr[-200:]))

        # ------------------------------------------------------------------------------------------------------ M
        say("\n--- M. SDLogto -------------------------------------------------------------------------------------------------")
        row("M1: SDLogto to another account returns true (sheet 272: it always returned false) and the session is in it (@WHO)",
            lib.SDLogto(b"zzab") == 1 and call("SDGetVar", b"@WHO") == b"zzab", s(call("SDGetVar", b"@WHO")))
        r = lib.SDLogto(b"nosuchaccountzz")
        row("M2: SDLogto to an account that is not there returns false, says why, and the session stays where it was",
            r == 0 and err() != b"" and call("SDGetVar", b"@WHO") == b"zzab", "result %d, error %s, @WHO %s" % (r, s(err()), s(call("SDGetVar", b"@WHO"))))
        row("M3: CONTROL: back to the first account it returns true again", lib.SDLogto(b"zzaa") == 1 and call("SDGetVar", b"@WHO") == b"zzaa", "")

        # ------------------------------------------------------------------------------------------------------ N
        say("\n--- N. the MASTER.LOGIN paragraph (sheet 170) ------------------------------------------------------------------")
        q3.put(os.path.join(SYS, "bp", "zzmv"),
               "$internal\n   openpath @sdsys:@ds:'voc' to v else crt 'NOVOC' ; stop\n"
               "   write 'PA':@fm:'RUN bp zzmark MASTER' on v, 'MASTER.LOGIN'\n   crt 'MVDONE'\nend\n")
        q3.put(os.path.join(BOX, "user_accounts", "zzaa", "bp", "zzlv"),
               "   open 'voc' to v else stop\n   write 'PA':@fm:'RUN bp zzmark LOGIN' on v, 'LOGIN'\n   crt 'LVDONE'\nend\n")
        mv = q3.adm(["BASIC bp zzmv", "RUN bp zzmv"], internal=True)
        lv = q3.plain("zzaa", ["BASIC bp zzlv", "RUN bp zzlv"])
        row("N0: the two paragraphs are installed (MASTER.LOGIN in the SDSYS VOC, LOGIN in the account's)",
            any(l == "MVDONE" for l in mv) and any(l == "LVDONE" for l in lv), repr((mv[-2:], lv[-2:])))

        def order_after_connect():
            q3.plain("zzaa", ["DELETE zzlog order"])
            ok = lib.SDConnectLocal(b"zzaa")
            n_idx = lib.SDGetSession()
            nf = lib.SDOpen(b"zzlog")
            rec = text(lib.SDRead(nf, b"order", ctypes.byref(ctypes.c_int())))
            return ok, n_idx, nf, rec

        ok, n_idx, nf, rec = order_after_connect()
        row("N1: a new API session runs MASTER.LOGIN first and then the account's LOGIN", ok == 1 and rec == b"MASTER" + FM + b"LOGIN", s(rec))
        lib.SDLogto(b"zzaa")
        rec2 = text(lib.SDRead(nf, b"order", ctypes.byref(ctypes.c_int())))
        row("N2: LOGTO runs the new account's LOGIN again and NOT MASTER.LOGIN (as in a terminal session)",
            rec2 == b"MASTER" + FM + b"LOGIN" + FM + b"LOGIN", s(rec2))
        lib.SDDisconnect()
        lib.SDSetSession(main_idx)
        q3.put(os.path.join(SYS, "bp", "zzmv2"),
               "$internal\n   openpath @sdsys:@ds:'voc' to v else crt 'NOVOC' ; stop\n   delete v, 'MASTER.LOGIN'\n   crt 'MV2DONE'\nend\n")
        rm = q3.adm(["BASIC bp zzmv2", "RUN bp zzmv2"], internal=True)
        ok, n_idx, nf, rec = order_after_connect()
        row("N3: CONTROL: with no MASTER.LOGIN paragraph the session runs the account's LOGIN alone", ok == 1 and rec == b"LOGIN",
            "%s (%s)" % (s(rec), rm[-1:]))
        lib.SDDisconnect()
        lib.SDSetSession(main_idx)

        # ------------------------------------------------------------------------------------------------------ O
        say("\n--- O. the BASIC class's connect to a port nothing listens on (sheet 571) -------------------------------------")
        cout = q3.plain("zzaa", ["RUN bp zzcls"])
        cst = (tag(cout, "ST") or [""])[0]
        row("O1: connect() returns false, and ServerStatus is the failed open's status (a number, not zero) and error names the host and port",
            tag(cout, "OK") == ["0"] and cst.lstrip("-").isdigit() and cst != "0" and "127.0.0.1:1" in (tag(cout, "ERR") or [""])[0],
            repr(cout[-4:]))

        # ------------------------------------------------------------------------------------------------------ P
        say("\n--- P. sequential files (sheet 441): SDOpenSeq, SDReadSeq, SDReadBlk, SDWriteSeq, SDWriteBlk, SDSeek, SDWeofSeq ---")
        disk_dir = os.path.join(acct, "zzdir")

        def ondisk(name):
            try:
                with open(os.path.join(disk_dir, name), "rb") as fh:
                    return fh.read()
            except OSError:
                return None

        rs_err = ctypes.c_int()
        rb_n = ctypes.c_int()

        def rseq(f):
            t = text(lib.SDReadSeq(f, ctypes.byref(rs_err)))
            return t, rs_err.value

        def rblk(f, n):
            ptr = lib.SDReadBlk(f, n, ctypes.byref(rb_n))
            data = ctypes.string_at(ptr, rb_n.value) if ptr else b""
            if ptr:
                lib.SDFree(ctypes.c_void_p(ptr))
            return data, rb_n.value

        sf = lib.SDOpenSeq(b"zzdir", b"lines", 512)
        row("P1: SDOpenSeq of an item of a directory file (the VOC name and the item) in overwrite mode gives a file number of its own, "
            "above SDOpen's", sf > 10000, str(sf))
        for ln in (b"alpha", b"beta", b"gamma"):
            lib.SDWriteSeq(sf, ln)
        lib.SDClose(sf)
        row("P1: three SDWriteSeq lines are on the disk, each with its terminator, once the file is closed (read from the disk, not "
            "through the API)", ondisk("lines") == b"alpha\nbeta\ngamma\n", repr(ondisk("lines")))
        sf = lib.SDOpenSeq(b"zzdir", b"lines", 0)
        got = [rseq(sf) for _ in range(4)]
        row("P2: SDReadSeq gives the three lines without their terminators and then the empty string with the ELSE answer (2) at the "
            "end of the file", got == [(b"alpha", 0), (b"beta", 0), (b"gamma", 0), (b"", 2)], repr(got))
        lib.SDSeek(sf, 6, 0)
        b1 = rblk(sf, 4)
        lib.SDSeek(sf, -6, 2)
        b2 = rblk(sf, 10)
        lib.SDSeek(sf, 0, 0)
        lib.SDSeek(sf, 6, 1)
        b3 = rblk(sf, 4)
        b4 = rblk(sf, 100)
        row("P3: SDSeek from the start then SDReadBlk(4) gives beta; from the end by -6 then SDReadBlk(10) gives the 6 bytes there "
            "(fewer than asked, and the count says so); from here by 6 gives beta again, the next 100 give the 7 bytes that are left; "
            "and a read at the end gives nothing with a count of 0", (b1, b2, b3) == ((b"beta", 4), (b"gamma\n", 6), (b"beta", 4)) and b4 == (b"\ngamma\n", 7) and rblk(sf, 5) == (b"", 0),
            repr((b1, b2, b3, b4)))
        lib.SDClose(sf)

        sf = lib.SDOpenSeq(b"zzdir", b"bin", 512)
        binary = b"\x00\x01\xfe\xff\n\x00z"
        lib.SDWriteBlk(sf, binary, len(binary))
        lib.SDClose(sf)
        sf = lib.SDOpenSeq(b"zzdir", b"bin", 16)
        back = rblk(sf, 100)
        lib.SDClose(sf)
        row("P4: SDWriteBlk writes bytes exactly as given, zeros and high bytes included, and SDReadBlk returns them by its count",
            ondisk("bin") == binary and back == (binary, len(binary)), "disk %r, back %r" % (ondisk("bin"), back))

        sf = lib.SDOpenSeq(b"zzdir", b"lines", 256)
        lib.SDWriteSeq(sf, b"delta")
        lib.SDClose(sf)
        row("P5: append mode (256) adds to what is there", ondisk("lines") == b"alpha\nbeta\ngamma\ndelta\n", repr(ondisk("lines")))
        sf = lib.SDOpenSeq(b"zzdir", b"lines", 16)
        lib.SDWriteSeq(sf, b"not allowed")
        lib.SDClose(sf)
        row("P5: read only (16) cannot be written: the file is as it was", ondisk("lines") == b"alpha\nbeta\ngamma\ndelta\n", repr(ondisk("lines")))
        sf = lib.SDOpenSeq(b"zzdir", b"lines", 0)
        lib.SDSeek(sf, 6, 0)
        lib.SDWeofSeq(sf)
        lib.SDClose(sf)
        row("P5: SDWeofSeq cuts the file off at the position (6: after alpha)", ondisk("lines") == b"alpha\n", repr(ondisk("lines")))
        sf = lib.SDOpenSeq(b"zzdir", b"lines", 512)
        lib.SDClose(sf)
        row("P5: overwrite mode (512) empties the file on opening it", ondisk("lines") == b"", repr(ondisk("lines")))

        sf = lib.SDOpenSeq(b"zzdir", b"flush", 512 + 1024)
        lib.SDWriteSeq(sf, b"at once")
        flushed = ondisk("flush")
        lib.SDClose(sf)
        sf = lib.SDOpenSeq(b"zzdir", b"flush2", 512)
        lib.SDWriteSeq(sf, b"later")
        held_back = ondisk("flush2")
        lib.SDClose(sf)
        row("P6: with 1024 (unbuffered) a line is on the disk before the file is closed; the CONTROL, the same without it, has "
            "nothing there until the close", flushed == b"at once\n" and held_back in (b"", None) and ondisk("flush2") == b"later\n",
            repr((flushed, held_back, ondisk("flush2"))))

        row("P7: a file number that was never given is refused with the file number message, for each of the functions",
            rseq(10999) == (b"", 3) and b"file number" in err().lower() and rblk(10999, 5) == (b"", 0)
            and (lib.SDWriteSeq(10999, b"x"), b"file number" in err().lower())[1] and (lib.SDSeek(10999, 0, 0), b"file number" in err().lower())[1],
            s(err()))
        sf = lib.SDOpenSeq(b"zzdir", b"lines", 0)
        lib.SDClose(sf)
        row("P7: after SDClose the number is no longer good", rseq(sf)[1] == 3, repr(rseq(sf)))
        row("P7: an item in a file that is not there gives 0 and a message, and so does a null file name",
            lib.SDOpenSeq(b"nosuchdirfile", b"x", 0) == 0 and lib.SDOpenSeq(b"", b"", 0) == 0 and b"name" in err().lower(), s(err()))

        pf = lib.SDOpenSeq(b"inside.txt", b"", 512)
        lib.SDWriteSeq(pf, b"in the account")
        lib.SDClose(pf)
        try:
            with open(os.path.join(acct, "inside.txt"), "rb") as fh:
                inside = fh.read()
        except OSError:
            inside = None
        row("P8: THE GATE, by pathname: a file inside the account's own directory can be opened and written, with no switch on "
            "(a null id makes the first argument a pathname)", pf > 10000 and inside == b"in the account\n", "%d, %r" % (pf, inside))
        before = open("/etc/hostname", "rb").read()
        refused = [lib.SDOpenSeq(p, b"", 16) for p in (b"/etc/hostname", b"../zzab/inside.txt", b"sub/../../zzab/x", b"/tmp/zzqm-seq-out")]
        e_out = err()
        w = lib.SDOpenSeq(b"/tmp/zzqm-seq-out", b"", 512)
        row("P8: ... and a pathname OUTSIDE it is refused, an account without os-on reaching only its own directory: /etc/hostname, a "
            "sibling account's file, a path that climbs out, a new file in /tmp - none gets a number, the message says it may not be "
            "opened, and nothing was made",
            refused == [0, 0, 0, 0] and w == 0 and b"may open" in e_out and not os.path.exists("/tmp/zzqm-seq-out")
            and open("/etc/hostname", "rb").read() == before, "%r %d %s" % (refused, w, s(e_out)))

        # a second session finding a file held by the first
        sa = lib.SDGetSession()
        first = lib.SDOpenSeq(b"zzdir", b"held", 512)
        lib.SDConnectLocal(b"zzaa")
        sb = lib.SDGetSession()
        second = lib.SDOpenSeq(b"zzdir", b"held", 2)
        sec_status = lib.SDStatus()
        lib.SDSetSession(sa)
        lib.SDClose(first)
        lib.SDSetSession(sb)
        third = lib.SDOpenSeq(b"zzdir", b"held", 2)
        lib.SDDisconnect()
        lib.SDSetSession(sa)
        row("P9: a file another session has open is refused to a second open with 2 (give up) - 0, and the status says locked - and "
            "can be opened once the first has closed it", first > 10000 and second == 0 and third > 10000,
            "first %d, second %d (status %d), third %d" % (first, second, sec_status, third))

        # 26 Oct 26 (S.83): an open of an item that is NOT THERE.  The suspicion was that apisrvr's failed OPENSEQ keeps the name locked; two runs showed that A is GIVEN a file number
        #   (default and read-only mode alike), and op_seqio.c explains it: the ELSE clause is taken with STATUS() = 0, the file variable is allocated and the record locked, and vb.openseq
        #   (os.st = 0) treats that as an open file, which the client's close releases.  Not a defect.  This row holds the semantics: A gets a number, B's open with 2 (give up) is
        #   refused while A holds the name (status 3011), and once A has closed it B makes the item.
        sa = lib.SDGetSession()
        held_a = lib.SDOpenSeq(b"zzdir", b"absent16", 16)
        lib.SDConnectLocal(b"zzaa")
        sb = lib.SDGetSession()
        while_open = lib.SDOpenSeq(b"zzdir", b"absent16", 512 + 2)
        while_status = lib.SDStatus()
        lib.SDSetSession(sa)
        lib.SDClose(held_a)
        lib.SDSetSession(sb)
        after_close = lib.SDOpenSeq(b"zzdir", b"absent16", 512 + 2)
        if after_close > 10000:
            lib.SDClose(after_close)
        lib.SDDisconnect()
        lib.SDSetSession(sa)
        row("P9b: an item that is not there: the open is given a file number (read-only), the name is held by that open - another session's open with 2 (give up) is refused, "
            "status locked - and once it is closed the other session can make the item", held_a > 10000 and while_open == 0 and after_close > 10000,
            "A: %d; B while A holds it: %d (status %d); B after A closed it: %d" % (held_a, while_open, while_status, after_close))

        # ------------------------------------------------------------------------------------------------------ Q
        say("\n--- Q. WRITE ... CREATING.SEQKEY, FILEINFO(1031), CONFIGURE.FILE NEXT, SDWriteSeqKey and SDWriteuSeqKey ------------------")
        r1 = q3.plain("zzaa", ["RUN bp zzsk"])
        row("Q1: three writes with CREATING.SEQKEY (two WRITE, one WRITEU) on a new hashed file are given 1, 2 and 3", tag(r1, "IDS") == ["1|2|3"],
            repr(r1[-6:]))
        row("Q1: ... the WRITEU keeps its update lock (RECORDLOCKED 2), the WRITE released its own (0), and the record is read back by its id",
            tag(r1, "LOCK3") == ["2"] and tag(r1, "LOCK2") == ["0"] and tag(r1, "REC2") == ["second"], repr((tag(r1, "LOCK3"), tag(r1, "LOCK2"), tag(r1, "REC2"))))
        row("Q1: FILEINFO(file, 1031) is the id of the last record written with it: 3", tag(r1, "LAST") == ["3"], repr(tag(r1, "LAST")))
        q3.plain("zzaa", ["CONFIGURE.FILE zzsq NEXT 100"])
        r2 = q3.plain("zzaa", ["RUN bp zzsk"])
        row("Q2: CONFIGURE.FILE NEXT 100 sets the counter: the next three are 100, 101 and 102 (and 1031 says 102)",
            tag(r2, "IDS") == ["100|101|102"] and tag(r2, "LAST") == ["102"], repr((tag(r2, "IDS"), tag(r2, "LAST"))))
        qq = q3.plain("zzaa", ["CONFIGURE.FILE zzsq NEXT QUERY"])
        row("Q2: NEXT QUERY says what the next id will be (103)", any("next sequential record id is 103" in ln for ln in qq), repr(qq[-3:]))
        rt = q3.plain("zzaa", ["RUN bp zzskt"])
        row("Q3: in a transaction the id is taken at the WRITE and the record is there after the commit (103)", tag(rt, "TXN") == ["103=in txn"],
            repr(tag(rt, "TXN")))
        rd = q3.plain("zzaa", ["RUN bp zzskd"])
        row("Q4: a DIRECTORY file is refused (status 3005, not a dynamic file) and the id variable is left null",
            any(re.fullmatch(r"REFUSED\[-?3005\]", ln) for ln in rd) and tag(rd, "AFTER") == [""], repr(rd[-4:]))
        qf = lib.SDOpen(b"zzsq")
        k1 = text(lib.SDWriteSeqKey(qf, b"api one"))
        l1 = lib.SDRecordlocked(qf, k1) if k1 else None
        k2 = text(lib.SDWriteuSeqKey(qf, b"api two"))
        l2 = lib.SDRecordlocked(qf, k2) if k2 else None
        if k2:
            lib.SDRelease(qf, k2)
        back = text(lib.SDRead(qf, k1 or b"x", ctypes.byref(ctypes.c_int()))) if k1 else None
        row("Q5: SDWriteSeqKey and SDWriteuSeqKey over the API give the file's next ids (104, 105), the first releasing its lock (0) and "
            "the second keeping it (2), and the record is there", (k1, k2, l1, l2, back) == (b"104", b"105", 0, 2, b"api one"),
            repr((k1, k2, l1, l2, back)))
        qdf = lib.SDOpen(b"zzdir")
        row("Q5: on a directory file they give nothing and say a hashed file is needed",
            text(lib.SDWriteSeqKey(qdf, b"x")) == b"" and b"hashed" in err(), s(err()))
        qq = q3.plain("zzaa", ["CONFIGURE.FILE zzsq NEXT QUERY"])
        row("Q5: the API and the program use the one counter: NEXT QUERY now says 106", any("next sequential record id is 106" in ln for ln in qq),
            repr(qq[-3:]))

        # ------------------------------------------------------------------------------------------------------ R
        say("\n--- R. threads (sheet 456): sessions, buffers and a failed connect's error, six threads in one process --------------")
        NTH = 6
        try:
            cp = subprocess.run([sys.executable, "-I", "-c", THREAD_CHILD, os.path.join(SYS, "bin", "sdclilib.so"), str(NTH), rev.decode()],
                                capture_output=True, text=True, timeout=240, env=dict(os.environ))
            res_line = [ln for ln in cp.stdout.splitlines() if ln.startswith("RESULT ")]
            tres = json.loads(res_line[-1][7:]) if res_line else None
            tcrc, terr = cp.returncode, cp.stderr.strip()[-300:]
        except subprocess.TimeoutExpired:
            tres, tcrc, terr = None, None, "TIMEOUT"
        say("sandbox-qmclient: thread child exit %r, result %s" % (tcrc, json.dumps(tres)[:900] if tres else None))
        if tres is None:
            for t in ("R1", "R2", "R3", "R4", "R5"):
                row("%s: the thread child gave no result (exit %r) - %s" % (t, tcrc, terr), False, "")
        else:
            ss = [x for x in tres["sessions"] if x]
            row("R1: six threads connect at the same moment: every connect succeeds and each thread is given a session index of its "
                "own and a user number of its own", len(ss) == NTH and all(x["ok"] == 1 for x in ss)
                and len({x["idx"] for x in ss}) == NTH and len({x["who"] for x in ss}) == NTH,
                repr([(x["ok"], x["idx"], x["who"]) for x in ss]))
            row("R2: each thread's current session stays its own through 100 rounds of asking while the others do the same "
                "(SDGetSession and @USERNO never name another thread's)", len(ss) == NTH and all(x["bad"] == 0 for x in ss),
                repr([x["bad"] for x in ss]))
            row("R3: each thread writes a record of its own size (3 KB to 38 KB) and reads it back 40 times at the same moment as "
                "the others: every read is exactly what it wrote", len(ss) == NTH and all(x["wrong"] == 0 for x in ss),
                repr([x["wrong"] for x in ss]))
            row("R3: ... and each thread's SDCallx of a catalogued subroutine gives it, through SDGetArg, the argument that call "
                "returned, 40 times, as the others call it (the Callx buffers are per thread)",
                len(ss) == NTH and all(x.get("callx_wrong") == 0 for x in ss),
                repr([x.get("callx_wrong") for x in ss]) + (" catalogue: " + repr(csub[-3:]) if any(x.get("callx_wrong") for x in ss) else ""))
            fl = tres["failed"]
            row("R4: a connect that fails keeps its error text for its own thread while another thread connects and disconnects ten "
                "times (the slot is held, not handed to the next connect)", fl.get("r") == 0 and fl.get("e1", "") != ""
                and fl.get("e2") == fl.get("e1") and fl.get("churn") == 10 and fl.get("connected") == 0, repr(fl))
            row("R5: CONTROL: afterwards one thread connects, asks the server's revision and disconnects as before",
                tres["control"] == [1, rev.decode()], repr(tres["control"]))
        row("R6: the thread child ended normally (exit 0, no exception in any thread, no barrier broken)",
            tres is not None and tcrc == 0 and tres.get("errors") == [], "exit %r, errors %r %s" % (tcrc, (tres or {}).get("errors"), terr))
        for rid in ["thr%d" % i for i in range(NTH)]:
            q3.plain("zzaa", ["DELETE zzlog %s" % rid])

        # ------------------------------------------------------------------------------------------------------ S
        say("\n--- S. a pathname outside the account, for an account that holds os-on (apisrvr's vb.openseq asks K$PATH.OK itself) ---")
        out_path = "/tmp/zzqm-os-out"
        nodir = "/tmp/zzqm-nodir-xyz"
        for p_ in (out_path, nodir):
            if os.path.exists(p_):
                q3.bail("%s exists before the run; remove it (it is this suite's own scratch name)" % p_)
        acct_c = q3.build_account("zzac")
        fixture_osx = os.environ.get("QMC_FIXTURE_OS", "yes")

        def register(osx_value):
            """The register entry of zzac: path, null, group, 3 nulls, SH, OS.EXECUTE.  A session reads it at login."""
            q3.put(os.path.join(SYS, "accounts", "zzac"), "\n".join([acct_c, "", q3.GROUP, "", "", "", "no", osx_value]) + "\n")
            say("sandbox-qmclient: register zzac -> %r" % open(os.path.join(SYS, "accounts", "zzac")).read().split("\n")[6:8])

        def seq_open_out(mode):
            # + 2: give up if another process has the file.  A wrong gate would leave session A holding it, and without 2 the next
            # open would wait for ever (the first mutant run of this part hung there)
            f_ = lib.SDOpenSeq(out_path.encode(), b"", mode + 2)
            return f_, err()

        try:
            register("no")
            ok_a = lib.SDConnectLocal(b"zzac")
            sess_a = lib.SDGetSession()
            fa, ea = seq_open_out(512)
            row("S1: CONTROL, os-off: zzac (the same account, its register entry OS.EXECUTE no) is refused a pathname in /tmp - no file number, "
                "the message says it may not be opened, nothing was made", ok_a == 1 and fa == 0 and b"may open" in ea and not os.path.exists(out_path),
                "connect %r, %r, %s" % (ok_a, fa, s(ea)))
            register(fixture_osx)
            ok_b = lib.SDConnectLocal(b"zzac")
            sess_b = lib.SDGetSession()
            row("S2: the register flipped and a NEW session made in zzac: it connects and is in zzac", ok_b == 1 and sess_b != sess_a
                and call("SDGetVar", b"@WHO") == b"zzac", "%r %r %s" % (ok_b, sess_b, s(call("SDGetVar", b"@WHO"))))
            fb, eb = seq_open_out(512)
            row("S3: os-on: the pathname in /tmp is OPENED (a file number of the sequential range)", fb > 10000, "%r, %s" % (fb, s(eb)))
            if fb > 10000:
                lib.SDWriteSeq(fb, b"written by an os-on account")
                lib.SDWriteSeq(fb, b"second line")
                lib.SDClose(fb)
            try:
                with open(out_path, "rb") as fh:
                    on_disk = fh.read()
            except OSError:
                on_disk = None
            row("S3: ... the two lines are on the disk in /tmp with their terminators, read back by this program, not by SD",
                on_disk == b"written by an os-on account\nsecond line\n", repr(on_disk))
            rf = lib.SDOpenSeq(out_path.encode(), b"", 16 + 2)      # + 2: give up, do not wait, if a wrong gate left it held
            l1, st1 = rseq(rf) if rf else (None, None)
            l2, st2 = rseq(rf) if rf else (None, None)
            if rf:
                lib.SDClose(rf)
            row("S4: ... and read back through the API (read only): both lines, without their terminators",
                rf > 10000 and (l1, l2) == (b"written by an os-on account", b"second line"), "%r %r %r" % (rf, l1, l2))
            host_line = open("/etc/hostname", "rb").read().split(b"\n")[0]
            hf = lib.SDOpenSeq(b"/etc/hostname", b"", 16)
            h1, _ = rseq(hf) if hf else (None, None)
            if hf:
                lib.SDClose(hf)
            row("S4: a file the account does not own, /etc/hostname, is opened read only and its first line is read (the P8 refusal, lifted)",
                hf > 10000 and h1 == host_line, "%r %r vs %r" % (hf, h1, host_line))

            # what os-on does not lift: the operating system's own rules and the request's own checks
            before_h = open("/etc/hostname", "rb").read()
            if os.geteuid() != 0:
                # OPENSEQ in overwrite mode refuses a file the operating system will not let the SD process truncate (an abort in
                # the request, which the client prints on stderr); in append mode the open is answered and the first WRITE fails
                (ovf, _) = cap_stderr(lambda: lib.SDOpenSeq(b"/etc/hostname", b"", 512))
                row("S5: STILL REFUSED by the operating system, not the gate: /etc/hostname (root's, mode 644) in overwrite mode gets no file "
                    "number and the file is as it was", ovf == 0 and open("/etc/hostname", "rb").read() == before_h, "%r, %s" % (ovf, s(err())))
                af = lib.SDOpenSeq(b"/etc/hostname", b"", 256)
                (wr, _) = cap_stderr(lambda: lib.SDWriteSeq(af, b"zz") if af else -1)
                wst = lib.SDStatus()
                if af:
                    lib.SDClose(af)
                row("S5: ... in append mode the open is answered but the WRITE fails (nothing written, a non-zero status), and the file is as "
                    "it was", wst != 0 and open("/etc/hostname", "rb").read() == before_h, "open %r, status %r, file as it was %r (26 Oct 26: SDWriteSeq is a VOID function, so the old test of its 'return value' %r read whatever was left in a register and went red on an unrelated build; the status and the disk are the evidence)" % (af, wst, open("/etc/hostname", "rb").read() == before_h, wr))
            # no refusal for a missing directory: OPENSEQ makes it, as it does for any program that holds the gate
            ndf = lib.SDOpenSeq((nodir + "/x").encode(), b"", 512)
            if ndf > 10000:
                lib.SDWriteSeq(ndf, b"made")
                lib.SDClose(ndf)
            nd_data = open(nodir + "/x", "rb").read() if os.path.exists(nodir + "/x") else None
            row("S5: os-on is not limited to directories that exist: a file in a new directory under /tmp is made, written and found "
                "on the disk (OPENSEQ makes the directory)", ndf > 10000 and nd_data == b"made\n", "%r, %r" % (ndf, nd_data))
            ef = lib.SDOpenSeq(b"", b"", 512)
            row("S5: STILL REFUSED: a null name - the message says a sequential file needs a name", ef == 0 and b"needs a name" in err(),
                "%r, %s" % (ef, s(err())))

            # the first session, made while zzac was os-off, keeps its switches: they were loaded at login
            if os.path.exists(out_path):
                os.remove(out_path)
            lib.SDSetSession(sess_a)
            fa2, ea2 = seq_open_out(512)
            row("S6: the os-off session made BEFORE the flip is still refused after it (the switches are loaded at login), nothing made",
                fa2 == 0 and b"may open" in ea2 and not os.path.exists(out_path), "%r, %s" % (fa2, s(ea2)))
            lib.SDDisconnect()
            lib.SDSetSession(sess_b)
            lib.SDDisconnect()
            register("no")
            ok_c = lib.SDConnectLocal(b"zzac")
            fc, ec = seq_open_out(512)
            row("S7: CONTROL: with the register os-off again a NEW session is refused again", ok_c == 1 and fc == 0 and b"may open" in ec
                and not os.path.exists(out_path), "%r %r, %s" % (ok_c, fc, s(ec)))
            lib.SDDisconnect()
        finally:
            for p_ in (out_path, nodir + "/x"):       # this suite's own scratch names, and the one directory it caused
                if os.path.exists(p_):
                    os.remove(p_)
            if os.path.isdir(nodir):
                os.rmdir(nodir)
        lib.SDSetSession(main_idx)

        # ------------------------------------------------------------------------------------------------------ K (the long one)
        say("\n--- K. AUTOLOGOUT in an API session (sheet 474): two sessions, one given AUTOLOGOUT 1, both idle for 70 seconds ------")
        lib.SDConnectLocal(b"zzaa")
        ia = lib.SDGetSession()
        eK = ctypes.c_int()
        text(lib.SDExecute(b"AUTOLOGOUT 1", ctypes.byref(eK)))
        shown = text(lib.SDExecute(b"AUTOLOGOUT", ctypes.byref(eK)))
        lib.SDConnectLocal(b"zzaa")
        ib = lib.SDGetSession()
        shown_b = text(lib.SDExecute(b"AUTOLOGOUT", ctypes.byref(eK)))
        row("K0: AUTOLOGOUT is set by the command in one session (1 minute) and is off in the other", shown is not None and b"1 minute" in shown
            and shown_b is not None and b"disabled" in shown_b, "%s / %s" % (s(shown), s(shown_b)))
        time.sleep(70)
        lib.SDSetSession(ia)
        box = {}

        def idle_call():
            lib.SDSetSession(ia)       # the current session is per thread (sheet 456): this thread must select the one to ask
            t0 = time.time()
            box["answer"] = call("SDSystem", 1012)
            box["secs"] = time.time() - t0

        th = threading.Thread(target=idle_call, daemon=True)
        th.start()
        th.join(30)
        row("K1: after the minute the session whose AUTOLOGOUT has run out is gone: its next request comes back at once with nothing and "
            "an error, where it used to wait for ever on a pipe nobody would write to",
            not th.is_alive() and box.get("answer") in (b"", None) and err() != b"", "answer %r after %s s, error %s" % (box.get("answer"), box.get("secs"), s(err())))
        lib.SDSetSession(ib)
        row("K2: CONTROL: the other session, idle for the same time without AUTOLOGOUT, still answers", call("SDSystem", 1012) == rev, "")
        lib.SDDisconnect()
        lib.SDSetSession(ia)
        t0 = time.time()
        lib.SDDisconnect()
        row("K3: disconnecting the session whose server has gone returns (no SIGPIPE ended this program, no wait)", time.time() - t0 < 20,
            "%.1f s" % (time.time() - t0))
        lib.SDSetSession(main_idx)
        row("K3: CONTROL: the first session is still there", call("SDSystem", 1012) == rev, "")
        lib.SDDisconnect()

        # ------------------------------------------------------------------------------------------------------ T (LAST: it restarts SD)
        say("\n--- T. SDCLIENT in sd.conf (sheet 571 family): every request that tests it; 0 is the control, then 1, then 2 -----------")
        say("sandbox-qmclient: part T restarts the sandbox for each mode, which ends every session, so it runs after K and last")
        lib.SDGetArg.restype = ctypes.c_void_p
        lib.SDOpenSeq.restype = ctypes.c_int

        cap = cap_stderr

        def marks(clear=False):
            """The marks the probes leave in zzlog, and the oracle for the T conversion, read in an ordinary session."""
            o = q3.plain("zzaa", ["RUN bp zzmrk" + (" clear" if clear else "")])
            d = {m.group(1): m.group(2) for m in (re.match(r"^M\[([a-z]+)=(.*)\]$", t) for t in o) if m}
            return d, (tag(o, "TC") or [None])[0]

        def phase(mode, up):
            """One SDCLIENT mode: a new session, every request that tests it, the disk as evidence."""
            marks(clear=True)
            for nm in ("sdcl%d" % mode, "sdclpath%d.txt" % mode):
                for base in (os.path.join(acct, "zzdir"), acct):
                    if os.path.exists(os.path.join(base, nm)):
                        os.remove(os.path.join(base, nm))
            P = "T%d-" % mode          # T0- the control, T1- SDCLIENT=1, T2- SDCLIENT=2
            allow_file = mode == 0
            okc = lib.SDConnectLocal(b"zzaa")
            row("%s0: with SDCLIENT=%d SD is up and a NEW session connects" % (P, mode), up and okc == 1, "SD up %s, connect %r, %s" % (up, okc, s(err())))
            if not (up and okc == 1):
                return
            row("%s1: ... and still answers SDSystem(1012) with the revision" % P, call("SDSystem", 1012) == rev, "")
            row("%s1: ... and SDGetVar(@WHO) names the account" % P, call("SDGetVar", b"@WHO") == b"zzaa", "")
            # SDOpen
            fno, e = cap(lambda: lib.SDOpen(b"zzcl"))
            row("%s2: SDOpen of a hashed file %s" % (P, "gives a file number" if allow_file else "gives 0, no file number (message 5262)"),
                (fno >= 1) if allow_file else (fno == 0), "%r, stderr %r, error %s" % (fno, e, s(err())))
            # (SDOpen, SDTrans and SDRTrans print no text of a refusal: sdclilib.c's SDOpen ignores the on-error reply's message)
            # SDTrans and SDRTrans
            tw, et = cap(lambda: call("SDTrans", b"zzcl", b"r1", b"NAME", b"X"))
            rw, er = cap(lambda: call("SDRTrans", b"zzcl", b"r1", b"NAME", b"X"))
            row("%s3: SDTrans and SDRTrans of a dictionary field %s" % (P, "give Widget" if allow_file else "give nothing (message 5262)"),
                (tw == b"Widget" and rw == b"Widget") if allow_file else (tw in (b"", None) and rw in (b"", None)),
                "%s %s, stderr %r %r" % (s(tw), s(rw), et, er))
            # SDOpenSeq, by VOC name and by pathname in the account
            qf, eq = cap(lambda: lib.SDOpenSeq(b"zzdir", ("sdcl%d" % mode).encode(), 512))
            if qf > 10000:
                lib.SDWriteSeq(qf, b"seq")
                lib.SDClose(qf)
            pf_, ep = cap(lambda: lib.SDOpenSeq(os.path.join(acct, "sdclpath%d.txt" % mode).encode(), b"", 512))
            if pf_ > 10000:
                lib.SDWriteSeq(pf_, b"path")
                lib.SDClose(pf_)
            f1 = os.path.join(acct, "zzdir", "sdcl%d" % mode)
            f2 = os.path.join(acct, "sdclpath%d.txt" % mode)
            d1 = open(f1, "rb").read() if os.path.exists(f1) else None
            d2 = open(f2, "rb").read() if os.path.exists(f2) else None
            if allow_file:
                row("%s4: SDOpenSeq by VOC name and by a pathname in the account both open, write, and the bytes are on the disk" % P,
                    qf > 10000 and pf_ > 10000 and d1 == b"seq\n" and d2 == b"path\n", "%r %r %r %r" % (qf, pf_, d1, d2))
            else:
                row("%s4: SDOpenSeq by VOC name and by a pathname in the account both give 0 (message 5262) and NOTHING was made on the disk" % P,
                    qf == 0 and pf_ == 0 and d1 is None and d2 is None and not os.path.exists(f1) and not os.path.exists(f2),
                    "%r %r %r %r, error %s" % (qf, pf_, d1, d2, s(err())))
                row("%s4: ... the text reaches the client (File access is disabled)" % P,
                    b"File access is disabled" in err() or "File access is disabled" in ep or "File access is disabled" in eq, "%s / %r" % (s(err()), ep))
            # SDExecute
            # In a CHILD process, because sdclilib.c's SDExecute copies the refusal's text into a 1-byte buffer (reply_len stays 0 on
            # an on-error reply, then strcpy): a heap overflow that corrupts the allocator, and a crash would end this suite.
            rounds = 1 if allow_file else 300
            try:
                xp = subprocess.run([sys.executable, "-I", "-c", EXEC_CHILD, os.path.join(SYS, "bin", "sdclilib.so"), str(rounds),
                                     "RUN bp zzxmk"], capture_output=True, text=True, errors="replace", timeout=120,
                                    # no tcache: a free() then checks the next chunk's size, which the overflow has overwritten
                                    env=dict(os.environ, GLIBC_TUNABLES="glibc.malloc.tcache_count=0"))
                xrc, xout, ex = xp.returncode, xp.stdout, xp.stderr
            except subprocess.TimeoutExpired:
                xrc, xout, ex = None, "", "TIMEOUT"
            m1, tc = marks()
            if allow_file:
                row("%s5: SDExecute runs the command: its mark is in the file" % P, m1.get("execmark") == "ran" and "FIRST err 0" in xout,
                    "%r, %r, child exit %r" % (m1, xout, xrc))
            else:
                row("%s5: SDExecute is refused - 'Command execution is disabled' on stderr, an on-error answer - and the command did NOT run "
                    "(no mark)" % P, "Command execution is disabled" in ex and "FIRST err 1" in xout and m1.get("execmark") == "-",
                    "stderr %r, stdout %r, marks %r" % (ex[:120], xout, m1))
                row("%s5: ... and 300 refused SDExecutes in a row leave the client library's heap sound: the child ends normally (exit 0, all "
                    "300 done), where the refusal's text written past a 1-byte buffer corrupts it" % P,
                    xrc == 0 and "LOOPS 300" in xout, "exit %r, stdout %r, stderr tail %r" % (xrc, xout, ex[-160:]))
            # SDCall of a subroutine that is not flagged $sdcall, and of one that is
            lib.SDCallx(b"zzcmk", ctypes.c_int16(2), b"X", b"")
            ra = text(lib.SDGetArg(2))
            _, ec = cap(lambda: lib.SDCallx(b"zzcmk", ctypes.c_int16(2), b"Y", b""))
            ra2 = text(lib.SDGetArg(2))
            lib.SDCallx(b"zzcok", ctypes.c_int16(2), b"Z", b"")
            rb = text(lib.SDGetArg(2))
            m2, _ = marks()
            if mode < 2:
                row("%s6: SDCall of an unflagged subroutine runs (only SDCLIENT=2 restricts calls): it returned its argument and left its mark" % P,
                    ra2 == b"ret:Y" and m2.get("callmark") == "ran Y", "%r %r" % (ra2, m2))
            else:
                row("%s6: SDCall of a subroutine NOT flagged $sdcall is refused (message 5264, zzcmk cannot be called from a SDClient session): "
                    "it returned nothing and did NOT run (no mark)" % P,
                    "cannot be called from a SDClient session" in ec and ra2 in (b"", None) and m2.get("callmark") == "-",
                    "stderr %r, returned %r, marks %r" % (ec, ra2, m2))
            row("%s7: SDCall of a subroutine flagged $sdcall runs in every mode: it returned its argument and left its mark" % P,
                rb == b"ret:Z" and m2.get("okmark") == "ran Z", "%r %r" % (rb, m2))
            # the conversions that read a file (T with a ;) or call a program (U)
            tconv, etc_ = cap(lambda: call("SDOConv", b"r1", b"Tzzcl;X;;1"))
            err_t = err()
            uconv = call("SDOConv", b"x", b"U50BB")
            err_u = err()
            sconv = call("SDOConv", b"widget", b"MCU")
            if mode == 0:
                row("%s8: SDOConv with a T conversion that reads a file is done (the answer is what OCONV gives in a session: %s)" % (P, tc),
                    tc not in (None, "") and tconv == tc.encode("latin-1"), "%s vs %r" % (s(tconv), tc))
                row("%s8: ... and a U conversion is not refused for being a conversion that calls a program" % P,
                    b"not allowed in this session" not in err_u, s(err_u))
            else:
                row("%s8: SDOConv with a T conversion that reads a file gives nothing and says it is not allowed in this session (11343)" % P,
                    tconv in (b"", None) and b"not allowed in this session" in err_t, "%s, %s" % (s(tconv), s(err_t)))
                row("%s8: ... so does a U conversion (one that calls a program)" % P,
                    uconv in (b"", None) and b"not allowed in this session" in err_u, "%s, %s" % (s(uconv), s(err_u)))
            row("%s8: CONTROL: a conversion that does neither (MCU) is done in every mode" % P, sconv == b"WIDGET", s(sconv))
            row("%s9: CONTROL: the session still answers afterwards" % P, call("SDSystem", 1012) == rev, "")
            lib.SDDisconnect()

        try:
            phase(0, True)
            for mode in (1, 2):
                up = q3.restart("SDCLIENT=%d" % mode)
                phase(mode, up)
        finally:
            up = q3.restart()
        okz = lib.SDConnectLocal(b"zzaa")
        zf = lib.SDOpen(b"zzcl")
        row("Tz: sd.conf restored: SD is up and a new session opens a file again", up and okz == 1 and zf >= 1, "%s %r %r" % (up, okz, zf))
        lib.SDDisconnect()
    finally:
        try:
            lib.SDDisconnectAll()
        except Exception:
            pass
        for nm in USER_PROGS:
            for d in ("bp", "bp.out"):
                p = os.path.join(SYS, d, nm)
                if os.path.exists(p):
                    os.remove(p)

    say("\nsandbox-qmclient: %d passed, %d failed" % (q3.passed, q3.failed))
    if q3.passed + q3.failed == 0:
        q3.bail("no row ran - a broken test, not a pass")
    return 1 if q3.failed else 0


if __name__ == "__main__":
    sys.exit(main())
