#!/usr/bin/env python3
#
# sandbox-fileadmin.py - API requests 70 (fileadmin: a verb run on the server for the login), 71 (fcontrol), 68 and 69 (write ... creating.seqkey) against a REAL `sd -Q`,
#                        S.73 item 3 (QMNet tiers C and D), 21 Oct 26.  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-fileadmin.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or absent).  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 21 Oct 26 dm  Written with the build of S.73 item 3.  The method is sandbox-req29.py's: the sandbox's own `sd -Q` on pipes, the wire protocol spoken from here, every request and reply printed, and
#               the evidence is the DISK as an ordinary session of the account reads it (ANALYSE.FILE, LIST.INDEX, COUNT), never what the server said about itself.  THE GATE IS THE PRODUCTION GATE:
#               the sandbox's apisrvr gets a TEST DEVICE in front of it (three request numbers that set the common variables vb.scram.final sets from the Linux groups: 27 files-only, 28 files-only
#               and in sdfileswrite, 72 files-only, in sdfileswrite AND in sdfilesadmin), so !apifilesok, message 11480 / 11521 / 11524 and the audit lines are what answer.  What the device cannot do is
#               read a group: that is the SCRAM final, covered by the VM witness only.  The rows were written from the design (.claude/s73-sdnet-admin-design.md, section 4), not from the output.
# END-HISTORY
#
#   G  the gate: a files-only login with neither group, with the write group only, and with both, asked for requests 70, 71, 68 (the messages and the audit lines)
#   V  the verbs of request 70 on a hashed file, each read back from the disk by an ordinary session: analyse, configure, create.index, build.index, disable.index, delete.index, create.file, delete.file
#   Q  request 71 (the FC$ keys) and requests 68 and 69 (the id the server's counter gives)
#   R  what is refused before anything runs: a word the grammar does not take, an operation that is not one, a file number that is not open - and the disk is as it was
#   E  the edit gate by the file's PATH: a dictionary of an account without dict.edit
#   U  the audit trail gained exactly the lines the design lists

import getpass
import grp
import importlib.util
import os
import re
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
spec = importlib.util.spec_from_file_location("r29", os.path.join(HERE, "sandbox-req29.py"))
r29 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r29)
q3, say, row, has, tag, put = r29.q3, r29.say, r29.row, r29.has, r29.tag, r29.put
Wire, msg, audit_off, audit_new, audit_has = r29.Wire, r29.msg, r29.audit_off, r29.audit_new, r29.audit_has

ACC = "zzfa"
GATE_OLD = r29.GATE_OLD
DEVICE = ("   if action = 27 then files.only = @true      ;* TEST DEVICE (sandbox-fileadmin.py): request 27 marks this session files-only, no group\n"
          "   if action = 28 then                         ;* TEST DEVICE: request 28 marks it files-only AND in sdfileswrite\n"
          "      files.only = @true\n"
          "      files.write = @true\n"
          "   end\n"
          "   if action = 72 then                         ;* TEST DEVICE: request 72 marks it files-only, in sdfileswrite AND in sdfilesadmin\n"
          "      files.only = @true\n"
          "      files.write = @true\n"
          "      files.admin = @true\n"
          "   end\n")
USER_PROGS = {
    # the fixture: a hashed file zzh with one dictionary item CITY (field 1) and three records, read back by the program itself
    "zzfx": ("   open 'zzh' to f else crt 'FX nofile' ; stop\n"
             "   open 'DICT zzh' to d else crt 'FX nodict' ; stop\n"
             "   write 'D':@fm:'1':@fm:'':@fm:'City':@fm:'12L':@fm:'S' on d, 'CITY'\n"
             "   write 'Paris' on f, 'r1'\n   write 'Rome' on f, 'r2'\n   write 'Paris' on f, 'r3'\n"
             "   select f to 6\n   readlist ids from 6 else ids = ''\n   crt 'FX[':dcount(ids, @fm):']'\n"),
    # the next id a hashed file's counter gives, WITHOUT taking it, read from the disk by an ordinary session: it writes a probe record under CREATING.SEQKEY and says the id
    "zzfs": ("   open 'zzh' to f else crt 'FS nofile' ; stop\n"
             "   id = ''\n   write 'probe' to f creating.seqkey id\n   crt 'FS[':id:']'\n   delete f, id\n"),
}
FAILED = []


def r(name, ok, detail=""):
    """row(), and the id of a failed row is kept."""
    row(name, ok, detail)
    if not ok:
        FAILED.append(name.split()[0])


def fileadmin(w, op, fno, text="", secs=90):
    """Request 70: operation (two bytes), the file number (two bytes, 0 for the operation that names none), the verb's words."""
    data = struct.pack("<hh", op, fno) + text.encode("latin-1")
    return w.req(70, data, shown="fileadmin op %d fno %r words %r" % (op, fno, text[:60]), secs=secs)


def fcontrol(w, fno, key, value=""):
    """Request 71: the file number, the key (two bytes each), the value as text."""
    return w.req(71, struct.pack("<hh", fno, key) + value.encode("latin-1"), shown="fcontrol fno %r key %d value %r" % (fno, key, value[:40]))


def seqkey(w, fno, rec, keep=False):
    """Request 68 (69 keeps the update lock): the file number then the record; the reply is the id the file's counter gave."""
    return w.req(69 if keep else 68, struct.pack("<h", fno) + rec.encode("latin-1"), shown="writeseqkey fno %r record %r keep %s" % (fno, rec[:30], keep))


def text(rr):
    return rr[2].decode("latin-1") if rr is not None else None


def refused_with(rr, number, request):
    """The reply is an ON ERROR one with message NUMBER for request REQUEST (the text has %1 for the request number)."""
    want = msg(number).replace("%1", str(request))
    return rr is not None and rr[0] == 1 and text(rr) == want


def register(group, dict_edit="yes"):
    """The register record of ACC: a member's account with the NET gate on and the edit gates as asked (field 12 is dict.edit)."""
    path = os.path.join(q3.BOX, "user_accounts", ACC)
    fields = [path, "", group, "", "", "", "no", "no", "no", "yes", "yes", dict_edit, "", "", "yes"]
    put(os.path.join(q3.SYS, "accounts", ACC), "\n".join(fields) + "\n")


def ordinary(*cmds):
    return q3.plain(ACC, list(cmds))


def analyse_field(lines, label):
    for ln in lines:
        m = re.match(r"^\s*(?:\d\d)?\s*" + re.escape(label) + r"\s*:\s*(.*)$", ln)
        if m:
            return m.group(1).strip()
    return None


def count_records(f="zzh"):
    """The number COUNT gives ("N record(s) counted"), or None when the file is not there ("File not found")."""
    out = ordinary("COUNT " + f)
    for ln in out:
        m = re.search(r"(\d+) record\(s\) counted", ln)
        if m:
            return int(m.group(1))
    return None


def index_line(lines, name="CITY"):
    """The LIST.INDEX row of the index NAME: (enabled column, type column), or None when there is no such row."""
    for ln in lines:
        m = re.match(r"^%s\s+([YN])\s+(\S+)" % re.escape(name), ln)
        if m:
            return m.group(1), m.group(2)
    return None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        q3.bail("usage: sandbox-fileadmin.py <dir> [--build]")
    q3.BOX = os.path.abspath(args[0])
    q3.SYS = os.path.join(q3.BOX, "sys")
    q3.SD = os.path.join(q3.SYS, "bin", "sd")
    q3.USER_PROGS = USER_PROGS
    BOX = q3.BOX
    say("sandbox-fileadmin: sandbox  %s" % BOX)
    say("sandbox-fileadmin: tree     %s" % os.path.dirname(HERE))
    if "--build" in sys.argv:
        if os.path.exists(BOX) and os.listdir(BOX):
            q3.bail("%s is not empty" % BOX)
        rr = subprocess.run([sys.executable, q3.TOOL, BOX, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in rr.stdout or rr.returncode != 0 or "[PASS] THIRD.COMPILE" not in rr.stdout:
            q3.bail("the sandbox build did not pass:\n" + rr.stdout[-800:])
        say("sandbox-fileadmin: built, bootstrap passed")
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

    say("\n--- preparation: the account %s with a hashed file zzh (dictionary item CITY, three records), read back by ordinary sessions ---" % ACC)
    q3.prepare()
    q3.build_account(ACC)
    out = q3.plain(ACC, ["CREATE.FILE zzh DYNAMIC", "RUN bp zzfx"])
    got = tag(out, "FX")
    if got != ["3"]:
        q3.bail("the fixture file zzh does not hold its three records: %r" % (out[-6:],))
    register(q3.GROUP)
    base = ordinary("ANALYSE.FILE zzh")
    minmod0 = analyse_field(base, "Minimum modulus")
    if minmod0 is None:
        q3.bail("an ordinary session's ANALYSE.FILE zzh does not show a minimum modulus, so no row below could be read from the disk:\n" + "\n".join(base[-12:]))
    say("  [done] the fixture holds zzh; an ordinary session reads its minimum modulus as %r" % minmod0)

    try:
        r29.set_prog("apisrvr", [(GATE_OLD, DEVICE + GATE_OLD)])
        if not q3.restart():
            q3.bail("SD does not start with the sandbox's own sd.conf")
        off0 = audit_off()
        say("  [device] the sandbox's apisrvr has requests 27 (files-only), 28 (files-only + write) and 72 (files-only + write + admin) in front of its gate")
        H, N, W, A = Wire("FH"), Wire("FN"), Wire("FW"), Wire("FA")
        logins = [w.login(ACC) for w in (H, N, W, A)]
        r("FA0 four sessions sign on to %s (OK all): H stays an ordinary session, N will be files-only with no group, W with the write group, A with the write and the administration groups" % ACC,
          all(e == 0 for e, t in logins), repr(logins))
        if not all(e == 0 for e, t in logins):
            q3.bail("the control logins did not work, so no row below can be believed")
        fH, fN, fW, fA = [w.open4("zzh")[0] for w in (H, N, W, A)]
        if None in (fH, fN, fW, fA):
            q3.bail("zzh did not open in a session, so no row below can be believed")
        say("  [files] zzh is file number %r (H), %r (N), %r (W), %r (A)" % (fH, fN, fW, fA))

        # ---- the markers ------------------------------------------------------------------------------------------------------------------------------------------------------------------
        for w, n in ((N, 27), (W, 28), (A, 72)):
            rr = w.req(n, shown="TEST DEVICE: mark this session")
            if not refused_with(rr, 11480, n):
                q3.bail("the test device did not take: request %d was not refused by the files-only gate with 11480, so no row below measures the gate (%r)" % (n, rr))
        say("  [device] N, W and A are marked; every marker was refused by the production gate with 11480, which is the proof that the device took")

        # ---- G. the gate ------------------------------------------------------------------------------------------------------------------------------------------------------------------
        say("\n--- G. the gate: a files-only login with neither group, with the write group only, and with both -----------------------------------------")
        n70, n71, n68 = fileadmin(N, 1, fN), fcontrol(N, fN, 6, "abc"), seqkey(N, fN, "x")
        r("G1 N (files-only, no group) asks request 70: refused - ON ERROR with message 11524 for request 70 (%r): the larger ask is named, and nothing ran" % msg(11524).replace("%1", "70"),
          refused_with(n70, 11524, 70), repr(n70))
        r("G2 ...request 71 the same (11524 for request 71) ...", refused_with(n71, 11524, 71), repr(n71))
        r("G3 ...and request 68 (write ... creating.seqkey) the same (11524 for request 68)", refused_with(n68, 11524, 68), repr(n68))
        w70, w71, w68 = fileadmin(W, 1, fW), fcontrol(W, fW, 6, "abc"), seqkey(W, fW, "x")
        r("G4 W (files-only, the WRITE group only) asks request 70: refused with 11524 too - the write group lifts the change set, not the administration set", refused_with(w70, 11524, 70), repr(w70))
        r("G5 ...71 and 68 the same", refused_with(w71, 11524, 71) and refused_with(w68, 11524, 68), repr((w71, w68)))
        wl = W.lockrec(fW, 3, b"g1")
        r("G6 CONTROL: W's own request 30 (lock record, a change of the write group) is served - the refusals above are the administration set and not a dead session", wl is not None and wl[0] == 0, repr(wl))
        W.release(fW, b"g1")
        hr = H.req(6, struct.pack("<h", fH) + b"r1", shown="read (request 6) fno %r id r1" % fH)
        r("G7 CONTROL: H (an ordinary session) and N still read (request 6) - the reads need sdfiles alone: H gets Paris", hr is not None and hr[0] == 0 and text(hr) == "Paris", repr(hr))
        nr = N.req(6, struct.pack("<h", fN) + b"r2", shown="read (request 6) fno %r id r2" % fN)
        r("G8 ...N gets Rome", nr is not None and nr[0] == 0 and text(nr) == "Rome", repr(nr))
        a1 = fileadmin(A, 1, fA)
        r("G9 A (files-only, BOTH groups) asks request 70 operation 1 (analyse.file): served - OK, and what the verb printed comes back (it names the file)", a1 is not None and a1[0] == 0 and b"zzh" in a1[2], repr(a1))
        say("      [what analyse.file printed on the server, for the record]\n        " + "\n        ".join((text(a1) or "").replace("\xfe", "\n").split("\n")[:14]))

        # ---- V. the verbs ---------------------------------------------------------------------------------------------------------------------------------------------------------------
        say("\n--- V. the verbs of request 70 on a hashed file, each read back from the disk by an ordinary session ----------------------------------------")
        before = analyse_field(ordinary("ANALYSE.FILE zzh"), "Minimum modulus")
        v2 = fileadmin(A, 2, fA, "MINIMUM.MODULUS 7")
        after = analyse_field(ordinary("ANALYSE.FILE zzh"), "Minimum modulus")
        r("V1 configure.file MINIMUM.MODULUS 7 (operation 2) on zzh: OK, and an ordinary session reads the minimum modulus as 7 from the disk (it was %r)" % before,
          v2 is not None and v2[0] == 0 and after == "7" and before != "7", repr((v2, before, after)))
        rb = A.req(6, struct.pack("<h", fA) + b"r1", shown="read (request 6) fno %r id r1" % fA)
        r("V1a the file number still works afterwards: the server opened zzh again under the same number (READ r1 gives Paris)", rb is not None and rb[0] == 0 and text(rb) == "Paris", repr(rb))
        v3 = fileadmin(A, 3, fA, "CITY")
        li = ordinary("LIST.INDEX zzh CITY")
        r("V2 create.index CITY (operation 3): OK, and LIST.INDEX in an ordinary session lists the index - not yet enabled (it is made, not built)",
          v3 is not None and v3[0] == 0 and v3[1] == 0 and index_line(li) == ("N", "D"), repr((v3, index_line(li), li[-4:])))
        # the verbs that work on the index's data need the file to ITSELF: H, N and W hold zzh open, so build.index is refused BY THE VERB, on the server, with its own words - the reply is OK
        # (the request ran) and STATUS() is the verb's return code, not 0.  Nothing changed.
        v3a = fileadmin(A, 4, fA, "CITY")
        li_a = ordinary("LIST.INDEX zzh CITY")
        r("V2a build.index CITY while H, N and W hold zzh open: the verb refuses - reply OK, STATUS() the verb's non-zero code, and the words 'exclusive access' come back; the index is still not enabled",
          v3a is not None and v3a[0] == 0 and v3a[1] != 0 and b"exclusive access" in v3a[2] and index_line(li_a) == ("N", "D"), repr((v3a[:2] if v3a else v3a, index_line(li_a))))
        for w_, f_ in ((H, fH), (N, fN), (W, fW)):
            w_.close_fno(f_)
        v4 = fileadmin(A, 4, fA, "CITY")
        li2 = ordinary("LIST.INDEX zzh CITY")
        say("      [LIST.INDEX after the build]\n        " + "\n        ".join(li2[-6:]))
        r("V3 the same request once the others have closed it (operation 4, build.index): OK with STATUS() 0, and the index is ENABLED on the disk", v4 is not None and v4[0] == 0 and v4[1] == 0 and index_line(li2) == ("Y", "D"), repr((v4[:2] if v4 else v4, index_line(li2))))
        v6 = fileadmin(A, 6, fA, "CITY")
        li3 = ordinary("LIST.INDEX zzh CITY")
        r("V4 disable.index CITY (operation 6): OK, and LIST.INDEX shows the index switched off again", v6 is not None and v6[0] == 0 and v6[1] == 0 and index_line(li3) == ("N", "D"), repr((v6[:2] if v6 else v6, index_line(li3))))
        v5 = fileadmin(A, 5, fA, "CITY")
        li4 = ordinary("LIST.INDEX zzh CITY")
        r("V5 delete.index CITY (operation 5): OK, and LIST.INDEX has no CITY row any more", v5 is not None and v5[0] == 0 and v5[1] == 0 and index_line(li4) is None, repr((v5[:2] if v5 else v5, li4[-4:])))
        say("\n      [create.file and delete.file: a NEW file named by the words, then removed through the number it was opened under]")
        v8 = fileadmin(A, 8, 0, "zznew MINIMUM.MODULUS 3")
        cnt = count_records("zznew")
        op4 = A.open4("zznew")
        r("V6 create.file zznew MINIMUM.MODULUS 3 (operation 8, no file number): OK, an ordinary session counts it (0 records), and the session can OPEN it by name",
          v8 is not None and v8[0] == 0 and cnt == 0 and op4[0] is not None, repr((v8, cnt, op4)))
        if op4[0] is not None:
            v9 = fileadmin(A, 9, op4[0])
            op5 = A.open4("zznew")
            r("V7 delete.file (operation 9) on zznew, through the number it was opened under: OK, and the file is gone - the name no longer opens (ELSE), an ordinary session cannot count it",
              v9 is not None and v9[0] == 0 and op5[0] is None and op5[1] is not None and op5[1][0] == 2 and count_records("zznew") is None, repr((v9, op5)))
        else:
            r("V7 delete.file (operation 9)", False, "zznew did not open, so there was nothing to delete")
        r("V8 zzh itself is untouched by all of it: its three records are there", count_records("zzh") == 3, repr(count_records("zzh")))

        # ---- Q. request 71, 68 and 69 -----------------------------------------------------------------------------------------------------------------------------------------------
        say("\n--- Q. request 71 (fcontrol) and requests 68 / 69 (the id the file's counter gives) ------------------------------------------------------")
        q1 = fcontrol(A, fA, 6, "abc")
        r("Q1 fcontrol key 6 (FC$VALID.ID) 'abc': OK with the answer 1 (the id could be written)", q1 is not None and q1[0] == 0 and text(q1) == "1", repr(q1))
        q2 = fcontrol(A, fA, 2, "100")
        r("Q2 fcontrol key 2 (FC$SET.SEQ.KEY) 100: OK with the answer 1 (it was set)", q2 is not None and q2[0] == 0 and text(q2) == "1", repr(q2))
        q3_ = seqkey(A, fA, "first")
        r("Q3 request 68 (write ... creating.seqkey) 'first': OK and the id is the one the counter was set to, 100", q3_ is not None and q3_[0] == 0 and text(q3_) == "100", repr(q3_))
        rd = A.req(6, struct.pack("<h", fA) + b"100", shown="read (request 6) fno %r id 100" % fA)
        r("Q3a ...and the record is in the file under that id (READ 100 gives 'first')", rd is not None and rd[0] == 0 and text(rd) == "first", repr(rd))
        q4 = seqkey(A, fA, "second", keep=True)
        r("Q4 request 69 (the same, keeping the update lock): the next id, 101", q4 is not None and q4[0] == 0 and text(q4) == "101", repr(q4))
        rl = A.reclocked(fA, b"101")
        r("Q4a ...and the session holds the update lock on it (RECORDLOCKED 2 - request 68 released its lock: 100 is code 0)", rl[0] == 2 and A.reclocked(fA, b"100")[0] == 0, repr((rl[:2], A.reclocked(fA, b"100")[:2])))
        q5 = fcontrol(A, fA, 3)
        r("Q5 fcontrol key 3 (FC$GET.SEQ.KEY): takes the next id and moves the counter on - the answer is 102", q5 is not None and q5[0] == 0 and text(q5) == "102", repr(q5))
        ps = ordinary("RUN bp zzfs")
        r("Q6 an ORDINARY session, writing a probe under creating.seqkey, is given 103: the counter on the disk moved with the server's, nothing was lost or given twice", tag(ps, "FS") == ["103"], repr(ps[-3:]))
        ck = fcontrol(A, fA, 99, "x")
        alive = A.req(2)
        r("Q7 an unknown key (99) is the function's own error and the session lives: the reply is an error (ON ERROR or ERROR), and the next request is answered",
          ck is not None and ck[0] in (1, 3) and alive is not None and alive[0] == 0, repr((ck, alive)))

        # ---- R. refused before anything runs ----------------------------------------------------------------------------------------------------------------------------------------------
        say("\n--- R. what is refused before anything runs: the disk and the audit trail are as they were ----------------------------------------------------")
        off_r = audit_off()
        before = analyse_field(ordinary("ANALYSE.FILE zzh"), "Minimum modulus")
        bad = [("PATHNAME x", "PATHNAME"), ("MINIMUM.MODULUS 9 PATHNAME", "PATHNAME"), ("LPTR", "LPTR"), ("FORCE", "FORCE"), ("NO.QUERY", "NO.QUERY"), ("a;b", "a;b"), ("a'b", "a'b"),
               ("a/b", "a/b"), ("a  b", "(two blanks)"), ("x" * 201, "x" * 20 + "..."), ("DIRECTORY x", "DIRECTORY")]
        results = [(w, shown, fileadmin(A, 2, fA, w)) for w, shown in bad]
        r("R1 operation 2 with a word the grammar does not take - %s - each is refused with message 11530 naming the word, and none ran" % ", ".join(repr(w[:12]) for w, s in bad),
          all(rr is not None and rr[0] == 1 and text(rr) == msg(11530).replace("%1", s) for w, s, rr in results), repr([(w[:12], text(rr)) for w, s, rr in results if text(rr) != msg(11530).replace("%1", s)]))
        r("R2 ...and the disk is as it was (the minimum modulus is still %r) ..." % before, analyse_field(ordinary("ANALYSE.FILE zzh"), "Minimum modulus") == before, repr(before))
        ops = [fileadmin(A, n, fA, "") for n in (0, 7, 10, 99)]
        r("R3 an operation that is not one (0, 7, 10, 99) is refused with message 11531 naming it", all(refused_with(rr, 11531, n) for rr, n in zip(ops, (0, 7, 10, 99))), repr(ops))
        nf_ = fileadmin(A, 2, 99, "MINIMUM.MODULUS 5")
        r("R4 a file number that is not open (99) is an error (ERROR, the 5268 text) and changes nothing", nf_ is not None and nf_[0] == 3 and A.errtext() == msg(5268), repr(nf_))
        dr = fileadmin(A, 8, 0, "zzdirx DIRECTORY")
        isdir = analyse_field(ordinary("ANALYSE.FILE zzdirx"), "Type")
        r("R5 DIRECTORY as the LAST word makes a directory file (it is the one place the word is taken): OK, and an ordinary session's ANALYSE.FILE reads its type as Directory", dr is not None and dr[0] == 0 and isdir == "Directory", repr((dr, isdir)))
        d_del = A.open4("zzdirx")
        if d_del[0] is not None:
            fileadmin(A, 9, d_del[0])
        new = audit_new(off_r)
        r("R6 the audit trail has NO 'api admin' line for the refused requests of R1 to R4 (the audit is written after the words are checked, before the command runs): the lines are the two of R5 only",
          new is not None and re.findall(r"api admin request=70 op=(\S+) file=(\S+) user=", new) == [("create.file", "zzdirx"), ("delete.file", "zzdirx")], repr(re.findall(r"api admin request=70[^\n]*", new or "")))

        # ---- E. the edit gate by the file's path ------------------------------------------------------------------------------------------------------------------------------------
        say("\n--- E. the edit gate: a DICTIONARY of an account without dict.edit is not changed by request 70 (the gate asks the file's path) ---------------")
        register(q3.GROUP, dict_edit="no")
        E = Wire("FE")
        e_, t_ = E.login(ACC)
        E.req(72, shown="TEST DEVICE: mark this session")
        fd = E.open4("dict zzh")[0]
        c_an = fileadmin(E, 1, fd) if fd is not None else None
        c_cf = fileadmin(E, 2, fd, "MINIMUM.MODULUS 5") if fd is not None else None
        r("E1 a session of an account whose dict.edit is NO opens dict zzh and runs analyse.file on it (a read: OK) ...", c_an is not None and c_an[0] == 0, repr((fd, c_an)))
        r("E2 ...but configure.file on it is refused by the edit gate - ERROR with the text of message 11406 (a dictionary) - and the dictionary is as it was",
          c_cf is not None and c_cf[0] == 3 and E.errtext() == msg(11406), repr(c_cf))
        E.close()
        register(q3.GROUP)

        # ---- U. the audit trail ----------------------------------------------------------------------------------------------------------------------------------------------------------
        say("\n--- U. the audit trail gained exactly the lines of the design, in order ----------------------------------------------------------------------")
        new = audit_new(off0)
        got = re.findall(r"api (refused request=\d+ route=sdfiles write=(?:on|off) admin=(?:on|off)|admin request=\d+ op=\S+ file=.+?) user=%s$" % re.escape(me), new or "", re.M)
        want = ["refused request=27 route=sdfiles write=off admin=off", "refused request=28 route=sdfiles write=on admin=off", "refused request=72 route=sdfiles write=on admin=on",
                "refused request=70 route=sdfiles write=off admin=off", "refused request=71 route=sdfiles write=off admin=off", "refused request=68 route=sdfiles write=off admin=off",
                "refused request=70 route=sdfiles write=on admin=off", "refused request=71 route=sdfiles write=on admin=off", "refused request=68 route=sdfiles write=on admin=off",
                "admin request=70 op=analyse.file file=zzh", "admin request=70 op=configure.file file=zzh", "admin request=70 op=create.index file=zzh", "admin request=70 op=build.index file=zzh",
                "admin request=70 op=build.index file=zzh",                     # V2a (the verb refused) and V3 (it ran): the audit line is written before the command, whatever the verb says
                "admin request=70 op=disable.index file=zzh", "admin request=70 op=delete.index file=zzh", "admin request=70 op=create.file file=zznew", "admin request=70 op=delete.file file=zznew",
                "admin request=70 op=create.file file=zzdirx", "admin request=70 op=delete.file file=zzdirx", "refused request=72 route=sdfiles write=on admin=on",
                "admin request=70 op=analyse.file file=dict zzh"]      # E1: the name the file was opened under, a dictionary as 'dict zzh'
        r("U1 the 'api refused ... admin=' and 'api admin ...' lines of the whole run are exactly these %d, in this order, all user=%s (refusals first, then every verb that ran; nothing for the "
          "words the grammar refused or the edit gate; the last two lines are E's marker and the analyse of E1)" % (len(want), me), got == want, repr(got))
        for w in (H, N, W, A):
            w.close()
    finally:
        r29.set_prog("apisrvr", [])
        q3.restart()
        subprocess.run([sys.executable, q3.TOOL, BOX, "stop"], capture_output=True, text=True, errors="replace", timeout=120)

    say("\nsandbox-fileadmin: %d passed, %d failed" % (q3.passed, q3.failed))
    return 1 if q3.failed else 0


if __name__ == "__main__":
    sys.exit(main())
