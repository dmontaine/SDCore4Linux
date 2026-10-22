#!/usr/bin/env python3
#
# sandbox-netindex.py - what a REAL `sd -Q` server answers to the index QUERY requests (S.73 item 3, D1, 21 Oct 2026): 35 and 36 (INDICES), 26 and 39 (SELECTINDEX of a value),
#                       38 (SELECTINDEX, the indexed values), 42 to 45 (SETLEFT, SETRIGHT, SELECTLEFT, SELECTRIGHT).  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-netindex.py <dir> [--build] [--probe]
#
# WHY.  The SDNet client refused these statements on a remote file, although the server serves them to every `sdfiles` login (apifilesok lines 26, 35, 36, 38, 39, 42-45: no new gate, the
# owner's D1).  The client side is built from what the server REALLY answers, and the fake server (netfake.py) imitates exactly these answers: this suite measures them on a real server and
# netfake.py's selftest holds its own answers to the same values (REAL_INDEX there).  The session is files-only with NO group (the test device of sandbox-fileadmin.py, request 27): the
# index queries need sdfiles alone.  --probe prints every reply and judges nothing.
#
# START-HISTORY:
# 21 Oct 26 dm  Written (S.73 item 3, D1).  The first probe found that the requests of the scan were answered wrongly at its end: vb.selectright had no RETURN and ran on into vb.mark.mapping, which
#               switched mark mapping on and left STATUS() 0 where a left scan leaves 1 (the local statement leaves 1 for both).  Fixed in gpl.bp/apisrvr; row S1d holds it.
# END-HISTORY

import getpass
import grp
import importlib.util
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
spec = importlib.util.spec_from_file_location("fa", os.path.join(HERE, "sandbox-fileadmin.py"))
fa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fa)
r29, q3, say, row, tag = fa.r29, fa.q3, fa.say, fa.row, fa.tag
Wire = fa.Wire
ACC = fa.ACC
FM = "\xfe"
FAILED = []

# the fixture: zzx has two dictionary items, CITY (field 1, left aligned text) and AMT (field 2, right aligned numbers), and these records.  r6 has two cities (a value mark between).
USER_PROGS = {
    "zzix": ("   open 'zzx' to f else crt 'IX nofile' ; stop\n"
             "   open 'DICT zzx' to d else crt 'IX nodict' ; stop\n"
             "   write 'D':@fm:'1':@fm:'':@fm:'City':@fm:'12L':@fm:'M' on d, 'CITY'\n"
             "   write 'D':@fm:'2':@fm:'':@fm:'Amt':@fm:'8R':@fm:'S' on d, 'AMT'\n"
             "   write 'Paris':@fm:100 on f, 'r1'\n   write 'Rome':@fm:20 on f, 'r2'\n   write 'Paris':@fm:3 on f, 'r3'\n"
             "   write 'Oslo':@fm:100 on f, 'r4'\n   write 'Rome':@fm:7 on f, 'r5'\n   write 'Paris':@vm:'Oslo':@fm:50 on f, 'r6'\n"
             "   select f to 6\n   readlist ids from 6 else ids = ''\n   crt 'IX[':dcount(ids, @fm):']'\n"),
}

# What INDICES(f, name) answers for the two indices, as the server sent it (a dictionary item's description with the index's flags; byte for byte)
INFO_CITY = "D\xfd\xfd\xfd1\xfd0\xfdL\xfd\xfe1\xfe\xfeCity\xfeL\xfeM"
INFO_AMT = "D\xfd\xfd\xfd1\xfd1\xfdL\xfd\xfe2\xfe\xfeAmt\xfeR\xfeS"


def r(name, ok, detail=""):
    row(name, ok, detail)
    if not ok:
        FAILED.append(name.split()[0])


def S(n):
    return struct.pack("<h", n)


def padname(s):
    """A name as request 26 carries it: its length, the name, a null when the length is odd (the other index requests do NOT pad)."""
    return S(len(s)) + s.encode("latin-1") + (b"\0" if len(s) % 2 else b"")


def is_(rr, status, data):
    """The reply is OK (error 0) with this STATUS() and exactly this data."""
    return rr is not None and rr[0] == 0 and rr[1] == status and rr[2].decode("latin-1") == data


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        q3.bail("usage: sandbox-netindex.py <dir> [--build] [--probe]")
    probe = "--probe" in sys.argv
    q3.BOX = os.path.abspath(args[0])
    q3.SYS = os.path.join(q3.BOX, "sys")
    q3.SD = os.path.join(q3.SYS, "bin", "sd")
    q3.USER_PROGS = USER_PROGS
    BOX = q3.BOX
    say("sandbox-netindex: sandbox  %s" % BOX)
    if "--build" in sys.argv:
        if os.path.exists(BOX) and os.listdir(BOX):
            q3.bail("%s is not empty" % BOX)
        rr = subprocess.run([sys.executable, q3.TOOL, BOX, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in rr.stdout or rr.returncode != 0 or "[PASS] THIRD.COMPILE" not in rr.stdout:
            q3.bail("the sandbox build did not pass:\n" + rr.stdout[-800:])
        say("sandbox-netindex: built, bootstrap passed")
    elif not os.path.isfile(q3.SD):
        q3.bail("%s holds no built sandbox (use --build, or point it at one)" % BOX)
    subprocess.run([sys.executable, q3.TOOL, BOX, "start"], capture_output=True, text=True, errors="replace", timeout=120)
    me = getpass.getuser()
    try:
        in_sdusers = me in grp.getgrnam("sdusers").gr_mem
    except KeyError:
        in_sdusers = False
    if not in_sdusers:
        q3.bail("the user running this (%s) is not in the Linux group sdusers, which the local API login needs" % me)

    say("\n--- preparation: the account %s with a hashed file zzx, two dictionary items and six records, then the indices CITY and AMT made and built by an ordinary session ---" % ACC)
    q3.prepare()
    q3.build_account(ACC)
    out = q3.plain(ACC, ["CREATE.FILE zzx DYNAMIC", "RUN bp zzix"])
    if tag(out, "IX") != ["6"]:
        q3.bail("the fixture file zzx does not hold its six records: %r" % (out[-6:],))
    fa.register(q3.GROUP)
    out = q3.plain(ACC, ["CREATE.INDEX zzx CITY", "CREATE.INDEX zzx AMT", "BUILD.INDEX zzx CITY", "BUILD.INDEX zzx AMT"])
    if not any("6 records processed" in x for x in out):
        q3.bail("the indices were not built: %r" % (out[-6:],))

    try:
        r29.set_prog("apisrvr", [(fa.GATE_OLD, fa.DEVICE + fa.GATE_OLD)])
        if not q3.restart():
            q3.bail("SD does not start with the sandbox's own sd.conf")
        N = Wire("IN")
        e_, t_ = N.login(ACC)
        if e_ != 0:
            q3.bail("the login did not work")
        fN = N.open4("zzx")[0]
        rr = N.req(27, shown="TEST DEVICE: mark this session files-only, no group")
        if not fa.refused_with(rr, 11480, 27):
            q3.bail("the test device did not take: request 27 was not refused by the files-only gate with 11480 (%r)" % (rr,))
        say("  [device] a files-only session with NO group, zzx open as file %r; the marker was refused by the production gate with 11480, the proof that the device took" % fN)

        def req(ptype, data, shown):
            return N.req(ptype, data, shown=shown)

        def scan(ptype, name, lst, shown):
            """One SELECTLEFT / SELECTRIGHT and the READLIST of its list: (the key reply, the ids reply)."""
            k = req(ptype, S(fN) + S(lst) + name.encode("latin-1"), shown)
            ids = req(14, S(lst), "readlist of list %d" % lst)
            return k, ids

        if probe:
            say("--probe: every reply is printed above; nothing is judged")
        say("\n--- I. INDICES: requests 35 and 36 ---")
        a = req(35, S(fN), "indices1 (the names)")
        r("I1 request 35 answers the names of the indices, field marks between, STATUS() 0", is_(a, 0, "CITY" + FM + "AMT"), repr(a))
        a, b, c, d = (req(36, S(fN) + n.encode(), "indices2 " + n) for n in ("CITY", "AMT", "NOSUCH", "city"))
        r("I2 request 36 answers the description of CITY and of AMT (byte for byte, kept in INFO_CITY / INFO_AMT)", is_(a, 0, INFO_CITY) and is_(b, 0, INFO_AMT), repr((a, b)))
        r("I3 ...a name that is not an index is the null string with STATUS() 0 (not 1), and the case of the name matters (city is not CITY)", is_(c, 0, "") and is_(d, 0, ""), repr((c, d)))

        say("\n--- V. the indexed values: request 38 ---")
        a, b, c = (req(38, S(fN) + n.encode(), "selectindexv " + n) for n in ("CITY", "AMT", "NOSUCH"))
        r("V1 request 38 answers the indexed values in index order, field marks between: CITY Oslo Paris Rome, AMT 3 7 20 50 100 (numerically, the index is right aligned), STATUS() 0",
          is_(a, 0, FM.join(["Oslo", "Paris", "Rome"])) and is_(b, 0, FM.join(["3", "7", "20", "50", "100"])), repr((a, b)))
        r("V2 ...an index that is not there is the null string with STATUS() 1", is_(c, 1, ""), repr(c))

        say("\n--- K. the ids for a value: requests 39 and 26 ---")
        a = req(39, S(fN) + S(4) + b"CITY" + b"Paris", "selectindexk CITY Paris")
        b = req(39, S(fN) + S(4) + b"CITY" + b"Rome", "selectindexk CITY Rome")
        c = req(39, S(fN) + S(4) + b"CITY" + b"Nowhere", "selectindexk CITY Nowhere")
        d = req(39, S(fN) + S(4) + b"CITY", "selectindexk CITY '' (a null value)")
        e = req(39, S(fN) + S(6) + b"NOSUCH" + b"Paris", "selectindexk NOSUCH Paris")
        f = req(39, S(fN) + S(3) + b"AMT" + b"100", "selectindexk AMT 100 (the name is NOT padded)")
        g = req(39, S(fN) + S(3) + b"AMT" + b"7", "selectindexk AMT 7")
        r("K1 request 39 answers the ids that hold the value, in id order, field marks between, STATUS() 0: Paris r1 r3 r6 (r6 holds two cities), Rome r2 r5",
          is_(a, 0, FM.join(["r1", "r3", "r6"])) and is_(b, 0, FM.join(["r2", "r5"])), repr((a, b)))
        r("K2 ...a value nobody holds, and a null value, are the null string with STATUS() 0; an index that is not there is the null string with STATUS() 1",
          is_(c, 0, "") and is_(d, 0, "") and is_(e, 1, ""), repr((c, d, e)))
        r("K3 ...the right aligned index finds 100 (r1 r4) and 7 (r5) by the number as typed", is_(f, 0, FM.join(["r1", "r4"])) and is_(g, 0, "r5"), repr((f, g)))
        a = req(26, S(fN) + S(3) + padname("CITY") + padname("Paris"), "selectindex CITY Paris into list 3 (request 26: the names are padded)")
        n1 = req(12, S(3), "readnext of list 3")
        n2 = req(14, S(3), "readlist of list 3")
        b = req(26, S(fN) + S(3) + padname("NOSUCH") + padname("Paris"), "selectindex NOSUCH Paris into list 3")
        n3 = req(14, S(3), "readlist of list 3 after an unknown index")
        r("K4 request 26 leaves the ids in the server's list: STATUS() 0, readnext gives r1 and readlist the rest (r3 r6)", is_(a, 0, "") and is_(n1, 0, "r1") and is_(n2, 0, FM.join(["r3", "r6"])), repr((a, n1, n2)))
        r("K5 ...an index that is not there is STATUS() 1 and an empty list", is_(b, 1, "") and is_(n3, 0, ""), repr((b, n3)))

        say("\n--- S. the scan: requests 42 to 45 ---")
        s0 = req(42, S(fN) + b"CITY", "setleft CITY")
        ks = [scan(45, "CITY", 4, "selectright CITY (call %d, after setleft)" % (i + 1)) for i in range(5)]
        r("S1a request 42 (setleft) is STATUS() 0; each selectright then answers the NEXT key with STATUS() 0 and leaves its ids in the list: Oslo r4 r6, Paris r1 r3 r6, Rome r2 r5",
          is_(s0, 0, "") and is_(ks[0][0], 0, "Oslo") and is_(ks[0][1], 0, FM.join(["r4", "r6"])) and is_(ks[1][0], 0, "Paris") and is_(ks[1][1], 0, FM.join(["r1", "r3", "r6"]))
          and is_(ks[2][0], 0, "Rome") and is_(ks[2][1], 0, FM.join(["r2", "r5"])), repr(ks[:3]))
        r("S1d ...past the last key it answers the null key with STATUS() 1 (as a left scan and as the local statement do; before 21 Oct 26 the server answered 0 here: vb.selectright fell into "
          "vb.mark.mapping), an empty list, and stays at the end", is_(ks[3][0], 1, "") and is_(ks[3][1], 0, "") and is_(ks[4][0], 1, ""), repr(ks[3:]))
        s0 = req(43, S(fN) + b"CITY", "setright CITY")
        ks = [scan(44, "CITY", 4, "selectleft CITY (call %d, after setright)" % (i + 1)) for i in range(4)]
        r("S2 setright, then selectleft answers Rome, Paris, Oslo and then the null key with STATUS() 1; the ids are the same lists",
          is_(s0, 0, "") and is_(ks[0][0], 0, "Rome") and is_(ks[0][1], 0, FM.join(["r2", "r5"])) and is_(ks[1][0], 0, "Paris") and is_(ks[1][1], 0, FM.join(["r1", "r3", "r6"]))
          and is_(ks[2][0], 0, "Oslo") and is_(ks[2][1], 0, FM.join(["r4", "r6"])) and is_(ks[3][0], 1, ""), repr(ks))
        s0 = req(42, S(fN) + b"AMT", "setleft AMT")
        ks = [scan(45, "AMT", 4, "selectright AMT (call %d, after setleft)" % (i + 1)) for i in range(6)]
        r("S3 the right aligned index scans in numeric order: 3 r3, 7 r5, 20 r2, 50 r6, 100 r1 r4, then the end (STATUS() 1)",
          [(k[0][1], k[0][2].decode("latin-1"), k[1][2].decode("latin-1")) for k in ks] == [(0, "3", "r3"), (0, "7", "r5"), (0, "20", "r2"), (0, "50", "r6"), (0, "100", FM.join(["r1", "r4"])), (1, "", "")],
          repr([(k[0][1], k[0][2], k[1][2]) for k in ks]))
        req(39, S(fN) + S(4) + b"CITY" + b"Paris", "selectindexk CITY Paris (sets the position)")
        k1 = scan(45, "CITY", 4, "selectright CITY (after selectindexk Paris)")
        k2 = scan(45, "CITY", 4, "selectright CITY again")
        r("S4 SELECTINDEX of a value sets the position: the next selectright answers Rome r2 r5, and then the end (STATUS() 1)", is_(k1[0], 0, "Rome") and is_(k1[1], 0, FM.join(["r2", "r5"])) and is_(k2[0], 1, ""),
          repr((k1, k2)))
        req(26, S(fN) + S(3) + padname("CITY") + padname("Paris"), "selectindex CITY Paris into list 3 (request 26 sets the position too)")
        k3 = scan(44, "CITY", 4, "selectleft CITY after request 26")
        r("S5 ...request 26 too: the next selectleft answers Oslo r4 r6", is_(k3[0], 0, "Oslo") and is_(k3[1], 0, FM.join(["r4", "r6"])), repr(k3))
        a = req(44, S(fN) + S(4) + b"NOSUCH", "selectleft NOSUCH")
        b = req(45, S(fN) + S(4) + b"NOSUCH", "selectright NOSUCH")
        c = req(42, S(fN) + b"NOSUCH", "setleft NOSUCH")
        d = req(43, S(fN) + b"NOSUCH", "setright NOSUCH")
        r("S6 an index that is not there is STATUS() 1 and the null string for all four", is_(a, 1, "") and is_(b, 1, "") and is_(c, 1, "") and is_(d, 1, ""), repr((a, b, c, d)))
        # a list number the client sends is not trusted: outside 0 to 10 is the server's "Invalid select list number" (message 5269), as request 26 gives it, and the session goes on
        bad_l = []
        for lst, ptype, nm in ((99, 44, "selectleft"), (-1, 45, "selectright"), (11, 44, "selectleft")):
            x = req(ptype, S(fN) + S(lst) + b"CITY", "%s CITY into list %d" % (nm, lst))
            bad_l.append((x, N.errtext()))
        alive = req(35, S(fN), "indices1 (the session is still alive)")
        r("S7 a list number outside 0 to 10 (99, -1, 11) is refused by both scans with an ERROR reply and message 5269 'Invalid select list number', and the session goes on (request 35 is answered after them)",
          all(x is not None and x[0] == 3 and t == fa.msg(5269) for x, t in bad_l) and is_(alive, 0, "CITY" + FM + "AMT"), repr((bad_l, alive)))

        say("\n--- G. no new gate ---")
        rd = req(6, S(fN) + b"r1", "read r1 (control: this session is files-only with no group and reads)")
        r("G1 CONTROL: the session that asked all of the above is files-only with NO group (a read is served, a change would be refused): none of the index queries needed more than sdfiles",
          is_(rd, 0, "Paris" + FM + "100") and fa.refused_with(req(16, S(fN) + S(2) + b"zzx", "write (control: refused)"), 11521, 16), repr(rd))
        N.close()
    finally:
        r29.set_prog("apisrvr", [])
        q3.restart()
        subprocess.run([sys.executable, q3.TOOL, BOX, "stop"], capture_output=True, text=True, errors="replace", timeout=120)

    say("\nsandbox-netindex: %d passed, %d failed" % (q3.passed, q3.failed))
    return 1 if q3.failed else 0


if __name__ == "__main__":
    sys.exit(main())
