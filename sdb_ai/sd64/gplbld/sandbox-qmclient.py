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
# 15 Oct 26 dm  Written for QM4 gaps bundle C-1.
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

import ctypes
import importlib.util
import os
import re
import subprocess
import sys

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
    # the data: three records of zzcl, a dictionary with NAME (field 1), QTY (2) and TAGS (3, multivalued); an index on NAME
    "zzclmk": ("   open 'zzcl' to f else stop 'no file'\n   open 'DICT zzcl' to d else stop 'no dict'\n"
               "   write 'D':@fm:'1':@fm:'':@fm:'Name':@fm:'10L':@fm:'S' on d, 'NAME'\n"
               "   write 'D':@fm:'2':@fm:'':@fm:'Qty':@fm:'5R':@fm:'S' on d, 'QTY'\n"
               "   write 'D':@fm:'3':@fm:'':@fm:'Tags':@fm:'8L':@fm:'M' on d, 'TAGS'\n"
               "   write 'Widget':@fm:'5':@fm:'red':@vm:'blue' on f, 'r1'\n"
               "   write 'Gadget':@fm:'7':@fm:'green' on f, 'r2'\n"
               "   write 'Gizmo':@fm:'9':@fm:'a':@vm:'b':@vm:'c' on f, 'r3'\n"
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
    # what INDICES() says about the index and the file, in an ordinary session
    "zzclix": ("   open 'zzcl' to f else stop 'no file'\n"
               "   crt 'NAMES[':change(indices(f), @fm, '/'):']'\n"
               "   crt 'DET[':change(change(change(indices(f, 'NAME'), @fm, '/'), @vm, '|'), @sm, '~'):']'\n"
               "end\n"),
}


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
    q3.plain("zzaa", ["CREATE.FILE zzcl DYNAMIC", "RUN bp zzclmk", "CREATE.INDEX zzcl NAME", "BUILD.INDEX zzcl NAME"])
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
    for fn in ("SDRevision", "SDGetVar", "SDSystem", "SDIndices", "SDTrans", "SDRTrans", "SDRead", "SDReadu", "SDExecute", "SDError"):
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
