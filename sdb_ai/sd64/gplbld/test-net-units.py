#!/usr/bin/env python3
"""test-net-units.py - the NET gate and the SDNet server definitions (S.65 slice 1), as invariants read off the source.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-net-units.py
  python3 .../test-net-units.py --selftest

No sudo, no install, no sd.  Exit 0 every check passed, 1 a check failed, 2 it could not run.  Written 17 Oct 26.
20 Oct 26 dm  S.72b (RECORDLOCKED() of a remote file becomes write-governed: of the five loosenings of S.72 the owner tightened this one alone, the same day).  Written BEFORE the code, from the spec, and shown
red on the unchanged tree.  The wall is the SERVER's (request 34 joins the change set of !apifilesok, so a files-only login without sdfileswrite is refused with message 11521 and the audit line
`api refused request=34 route=sdfiles write=off ...`: S72n here, F1 / F2a / F2d / F17 / F18 of test-fileswrite-units.py) and the clear text is the KERNEL's: a new gate kind NETG_PEEK (sd.h, 5, beside NETG_LOCK) runs
net_gate's FIRST test only - a read-mode file variable is refused with 11501 and -7000, nothing is sent - and not the CREATING.SEQKEY test, the transaction test (11510) or the edit gate, because RECORDLOCKED()
changes nothing; net_recordlocked asks net_gate(fvar, NETG_PEEK, 0, "RECORDLOCKED") FIRST (op_flags the literal 0: the function has no ON ERROR clause, so the refusal is always raised); and the handler's
act.recordlocked refuses a handle whose mode is not write through act.refuse, as act.fileunlock does, so the two layers agree.  MUSTLOCK (net_check_lock, net_pre_change_lock) is NOT gated: it is reached only from
a write path that has passed net_gate.  CHANGED: S2i (the NETG_PEEK arm in net_gate), S2zb (NETG_PEEK 5 and its comment), NF6a (act.recordlocked no longer begins with the gate: it begins as act.fileunlock does),
S72d (net_recordlocked ASKS the gate, and only that gate), S72n (34 IS in the change set), S72q (the read-mode matrix of sandbox-netfile.py has `km("recordlocked"` again: nothing is sent, KALLOWED stays), S2k
(on.error.text has SIX callers: act.recordlocked answers the server's ON ERROR reply now).  NEW: S72r (the handler's mode refusal, in ORDER), S72s (net_gate's NETG_PEEK arm, in ORDER), S72t (NETG_PEEK has one user),
S72u (MUSTLOCK is not gated), S72v (the history lines), S72w (the class's recordlocked() honours quiet: message.pair, not text.request; the abort only when not quiet), S72x (act.recordlocked reads LastError and answers
lost / server error / ON ERROR / unknown like act.fileunlock).  The reason for the last two: a login without sdfileswrite is refused request 34 with an ON ERROR reply, and a class that aborted on it would
stop the handler's own program, and a handler that did not read LastError would answer `not locked` (0) for a refused request.  The mutants of S.72 that tested the old design
(`recordlocked joins the change set`, `the suite's matrix has recordlocked again`, `net_recordlocked asks net_gate`) are replaced by their opposites.  WHAT THIS CANNOT SAY: that
nothing reaches the server from a read-mode handle, that the server answers 11521 or that a MUSTLOCK write ends with 11500 - sandbox-netfile.py (the fake), sandbox-req29.py and sandbox-net.py (the real server) and the VM witness.
20 Oct 26 dm  S.72 (QMNet parity, tiers A and B: RECORDLOCKED() and GETLOCKS() of a remote file, FILELOCK and FILEUNLOCK of one on a write-mode server).  Written BEFORE the code, from the
spec, and shown red on the unchanged tree.  Section S72 (checks_s72, S72a to S72q) reads: op_filelock's NET branch in ORDER - `retry_pc = op_pc` taken first, the NET_FILE test before the first
FPtr(, net_filelock_step, the HELD / WAIT / LOCKED / default switch, the status pushed - and no net_refuse left in the four opcodes (S72a, S72f, S72g, S72h, S72i); net_filelock_step and the
shared tail net_lock_result (S72b); net_fileunlock, which accepts exactly the answers 0, ER_LCK and ER_NLK (S72c); net_recordlocked with no net_gate, errors always raised, the owner's number
only when it is 0 to 32767, and net_lock_code shared with net_check_lock (S72d); rc<8> from the handler to the kernel (S72e, S72l); GETLOCKS of a remote file as the local view
(NO_LOCAL_FILE, no net_ call: S72h); the handler's FILELOCK arm in act.change and the new act.fileunlock (S72j, S72k); the class methods filelock and fileunlock (S72m); the change set of
apifilesok, which does not change (S72n); the numbers across five files (S72o); the history lines (S72p) and the suite's S.72 rows (S72q).  NF1, NF4b, NF5, NF5a, NF7, NF9, NF11, NK1b, NK2,
NK7, NK8, NK11, S2b, S2c, S2g, S2k, S2l, S2q and S2t were changed for it, each to pin the NEW truth (NF7 counts 17 request sites, NK7 23 census sites: the four opcodes left the census table for NK_LOCKSITES).
WHAT THIS CANNOT SAY: that a file lock is taken, that RECORDLOCKED() answers what the server holds or that STATUS() is the owner's number - sandbox-netfile.py, the sections hwrite and kwrite,
against the fake (whose answers sandbox-req29.py holds to the real server).
19 Oct 26 (integration): the mutant "the map's 1151 message rule comes after the none rule" is made by a function, since the masters lane's rules for
11560-11596 now stand between those two rules (the text-anchored version was "not applicable", a FAILURE of the self-test).

***WHAT THIS IS, AND WHAT IT IS NOT.***  It reads the C and BASIC sources as text, with comments removed, so a gate that survives only
in a comment does not count.  ***IT DOES NOT RUN ANYTHING, SO IT CANNOT SAY THAT THE GATE ANSWERS OR THAT A VERB WRITES OR REFUSES***:
that is sandbox-net.py (ordinary and administrator sessions on a private SD; the disk and the kernel's own answer are the evidence).
What a text check is for: the numbers must agree across seven files, the gate is loaded in four programs (LOGIN, CPROC at LOGTO and
on the way back, the API server), and the invariants that make the verbs safe are ORDER - every field looked at before the first
write, the administrator test before anything else, the umask around the creation of the file, the rename last, the lock released
after the write.  An edit that moves one still compiles.

NOTHING OPENS A REMOTE FILE YET.  This slice is the gate (nothing reads it) and the definitions (nothing uses them); the checks say
so by what they do not look for.

17 Oct 26 dm  S.65 slice 2a: set.server's fifth word may be CONNECT.  Section T reads the flow as ORDER - every field, the lock, the
read, the limit and the replace question before the one socket is opened; opened with SKT$TLS and a 5 second timeout; the hash read
and the socket closed before the key question is shown; the key question asked on EVERY connect (no.query is not consulted between
the connect and the question); nothing written on n, on a failed connect, on a failed handshake or on an empty hash; the audit words
pin=typed and pin=confirmed.  Section C3-C6 reads the C side: the hash is of the SubjectPublicKeyInfo (i2d_X509_PUBKEY and SHA-256, not
X509_digest, which is the certificate and changes at every renewal), SOCKET.INFO answers 64 lower case hex digits and a null string
without TLS, and the key number 11 is the same in both headers and unique.  P2, P3, G1-G5 were extended for the new messages
11440-11446 and the audit word.  What it cannot say is whether a handshake works or the hash is the right one: sandbox-net.py, section
"connect", against an independent openssl computation.

17 Oct 26 dm  S.65 slice 2b: the person's login on a server (set.netlogin, delete.netlogin, $netcred, SDEXT SD_FILE_PRIVATE).  Sections F (the
C private-file test: fail closed, lstat and not stat, the EFFECTIVE uid, no bit in 077, a regular file whose parent directory passes the
same test, the number 111 in both headers, SDEXT an internal-only intrinsic in BCOMP), R ($netcred: the path rule, SD_FILE_PRIVATE before
EVERY use, the file never holds the password, READ/WRITE/DELETE/EXISTS as ORDER, a strict shape for every value), U (set.netlogin: the
NET gate, the definition and the account list before anything is dialled, the pin tested before the first SCRAM packet, nothing written
on any failure, the password spent and cleared, no secret in a message or in the audit line), Y (delete.netlogin), V (the VOC entries,
in newvoc so EVERY account has them), H (messages 11450-11479) and E (the root agrees with sd-elevate netcred-dir and the sudoers
line).  B5 was extended: setnetlogin asks (never sets) K$NET.  WHAT THIS CANNOT SAY: that the exchange works against a server, that a
file written is mode 600, that a symlink is refused - sandbox-net.py, sections netcred and netlogin, with a fake server that speaks the
packet text of sdclient (gplbld/netfake.py).

17 Oct 26 dm  S.65 slice 2c: the SERVER side of a files-only login - a second, narrower API route.  Section W reads: !apifilesok (the one place that
decides, an ALLOW table of request numbers; the table parsed out of the source and run in Python for every number 0 to 80 with the account
entered and not, against a list written again in this file from the task, so a number wrong in either direction fails; 3 allowed once; an empty
or non-numeric action refused; the function pure), apisrvr (sdusers first, sdapi tried first and winning, sdfiles second, neither refused
exactly as before with 10073, both groups read with the three-valued status, sdsys exempt by name, the mark in the common block set once and
never cleared, the gate after the not-logged-in test and BEFORE the dispatch, audited, answering 11480), MODIFY.ACCOUNT / CREATE.ACCOUNT /
CREATEA / the manifest (route.files - NOT `files`, which is the backup's file count) / RESTORE.ACCOUNT, the installer and deletesdcore (the group
is made and removed), sd-elevate (the group is whitelisted, never deletable), and messages 11480 / 11482.  WHAT THIS CANNOT SAY: that a
files-only user logs in, that a request is refused on the wire or that the group changes - sandbox-net.py, section "files" (the table run by the
real compiled function; the words' syntax and their refusals), and an install for the rest (witness-release-run.sh).

17 Oct 26 dm  S.65 slice 3a: the BASIC client class gpl.bp/sdclient logs in from stored derived keys.  Section Z reads sdclient as text: connect.keys
(its parameters by value; every argument checked before open.socket; the socket opened with SKT$TLS and the 5 second connect timeout; THE PIN TESTED
BEFORE A BYTE IS SENT - nothing between the open and the comparison writes, reads or exchanges, and the comparison is of text ('p' : prefix) and not of
numbers; the Ack read bounded by io.ms; the exchange; the account entered and its refusal failing the call; the keys cleared after the exchange and on
every failure path, the socket closed), scram.exchange (the stored salt and count compared with the server's AFTER client-first and BEFORE the
client-final message, PBKDF2 only in the password branch, the spent keys dropped before the final message), scram.login as a one line wrapper, connect()
unchanged in kind (its Ack wait still unbounded, its open still without a timeout), the bounded reads of read.packet, settimeout, the three defines, no
secret in any error text, and the suite's wiring (regress.sh, regress-map.txt, the verdict line of sandbox-netfile.py, and every error text the suite
asserts being in the class).  WHAT THIS CANNOT SAY: that the class compiles, that obj->connect.keys parses, or that anything it checks happens at run
time - sandbox-netfile.py, against the fake in gplbld/netfake.py.

17 Oct 26 dm  S.65 slice 3b: the remote file handler gpl.bp/netfile ($netfile, operations in netfile.h).  Section N reads it as ORDER and as what it cannot
do: the 13 operation codes and the limits (NF1), the header (NF2), the checks of NF$OPEN in order with the gate asked by the handler itself and nothing dialled
before the audit line (NF3), the one way to the network (NF4), READ ONLY - no write, delete, create, lock or command, $netcred and !netdefs called with READ only, the
refused operations touching no connection (NF5), the gate in check.gate and again for every request (NF6), every request preceded by the no-reply mark, no retry
and no loop, the 30 second bound (NF7), the connections in the one named common block with no secret in it (NF8), exactly two audit lines and no secret in any message
argument (NF9), messages 11490-11506 (NF10), and the suite and the map (NF11, NF12).  B5 now counts the handler as one asker of K$NET.  WHAT THIS CANNOT SAY: that the
handler compiles, that an object stays in common, or that any of it happens - sandbox-netfile.py, sections handler, readonly, refuse, lost and timeout.

17 Oct 26 dm  S.65 slice 3c: the KERNEL half of remote files - the NET_FILE file variable type (descr.h 4), netfiles.c, the VOC pointer type N, open_file(), and the
refusal of every other statement.  Section NK reads the C and BASIC as ORDER: the type, the union member and the limits agreeing across C, BASIC and the messages (NK1); the nine
functions defined once, with one prototype everywhere (NK2); net_open_work in the order shape - GATE - audit - handler, the gate asking the session and NEVER exempting an $internal program,
the handler found and called BY NAME (NK3); net_refuse running no BASIC, net_close sending only for a CLOSE statement and queueing every other release, net_stale and the epoch, the NET_FILE made last
and only on success (NK4); _voc_ref's N case and check.n.pointer, with the C parse of the encoded form (NK5); open_file recognising the encoded path inside the OPEN-by-name block before fullpath and
the file table, and dio_close / op_close (NK6); THE CENSUS - each of the 31 sites the 17 Oct census says REFUSE (27 since slice 3d took SELECT, SELECTV and both INDICES out) calls net_refuse (or refuse_net_file) behind a NET_FILE test and before the first
read or write of the file table, a lock, a select list or an edit-gate decision; the guards on the file table's readers; READV and FILEINFO answered before the file table (NK7); and a scan that
FAILS when a new kernel function is given a file variable and nobody has decided what it does with a remote one (NK8); messages 11507 / 11508, the Makefile list, the suite and the map, the history
lines (NK9-NK12).  WHAT THIS CANNOT SAY: that anything compiles (make is the compiler), that a statement is refused, that ON ERROR runs, or what reaches the wire - the section kernel of
sandbox-netfile.py, whose refusal matrix runs about 40 statements against the fake server and requires its packet log to hold nothing but login, account, open, read, close and quit.

17 Oct 26 dm  S.65 slice 3d: SELECT and SELECTV of a remote file, the dictionary of one, and three FILEINFO keys.  SELECT, SELECTV and both INDICES leave the refusal census (NK7 now counts 27 sites; INDICES of a remote file is the null string, NK18): NK13
reads net_select (through net_op with NF_SELECT, net_raise only from the statement's own ON ERROR, *ids and *count set only on success, the field marks counted), NK14 op_select (the ids asked
of the server BEFORE end_select and clear_select, so an error leaves the target list alone, then store_select_list), NK15 op_selectv (the target found again from the e-stack after the call,
because the handler runs BASIC; @SELECTED set; list 11 never used), NK16 op_fileinfo (FL_TYPE FL_TYPE_NET, FL_COLLECTION 0 and FL_FLAGS the NOCASE bit for an $internal program only, all before
any FPtr; the value 7 in both keys.h files) and NK17 the DICT form (_voc_ref adds 'dict ' only for fno 3 and only after the shape check; the file name buffer and the length test hold the 5 more
characters).  NK5 and NK5b were rewritten for it.  WHAT THIS CANNOT SAY: that a remote SELECT returns the server's ids or that a dictionary opens - sandbox-netfile.py.

19 Oct 26 dm  Finish 2 (verifier findings).  W20 follows set.files after the failure path learned to say what happened (the audit line modify.account files-write-off and the write group's line,
through the new internal write.removed.line, BEFORE the failure message, and not the audit line of the action asked for); S2g allows the guarded aborts of select and readlist (a quiet
object returns); S2f reads act.select's two ON ERROR branches in order (after the SELECT proper, then after the READLIST); S2k counts four calls of on.error.text.  1327 mutants now (1324 +
three for the failure after the write group went), 0 missed: the first selftest after this change reported 1324 mutants, 1 missed - the mutant "a failed change is reported as done" anchored on the
old failure block and was "not applicable"; it is cut by a pattern now.
19 Oct 26 dm  K1, K2, K3, K4a, K8c, K8d (the S.65 finish).  S2k: on.error.text, the one place an ON ERROR reply becomes text (the handler showed 'status <n>' whatever the server
said); S2l: the ceiling on a reply (sdclient read.packet tests the announced length before it reads, maxpacket, $netfile sets it); W10 names both routes in the refusal reason;
W13 pins message 11482 in lower case; W17 to W20 follow set.files after K4a (change.files.group); T3, U4, Z3, Z5, Z12, NF4a, NF7, NF7b follow the timeouts becoming the parameters
NETWAIT and NETREPLY (request.limits); NF4b allows LastText and maxpacket.  1324 mutants now (1306 before; about a dozen were rewritten for the new source text), 0 missed.
18 Oct 26 dm  S.65 slice 3e (stage 2, writes and locks on a file of a server whose definition says mode=write; the spec is .claude/s65-stage2-design.md).  Section S2 reads: the mode
(S2a), act.change's order and its one request (S2b, S2c), after.rq's signed status and lost.fail's two messages (S2d), act.release (S2e), the quiet object (S2f), the class sdclient -
quiet, LastError, LastText, the guarded aborts, recordlock's flag, clearfile (S2g, S2h), net_gate's order (S2i), net_change_op and its two cache drops (S2j), the server's status passed on for
five entry points (S2k), net_lock_step (S2l), net_release / net_release_all / net_flush_closes (S2m), the chain that is never flattened (S2n), the NET arms of op_write / op_delete / op_clrfile
(S2o), MUSTLOCK and AUTOLOCK (S2p), retry_pc (S2q), the lock block of read_record and op_readv (S2r), op_lockrec / op_release / op_rlsfile / op_rlsall (S2s, S2t), FILEINFO (S2u),
edit_kind_of_net_name and the union (S2v), K_EDIT_OK / K_EDIT_KIND / K_NET -2 (S2w), CPROC and edit_guard (S2x), messages 11509-11512 (S2y) and the history lines (S2z).  NF1, NF4b, NF5, NF5a, NF7, NF7a, NF7b,
NF9, NF10, NF11, NK1, NK1b, NK3a, NK3b, NK4, NK4b, NK4c, NK7b, NK9, NK23, NK24, B3, B5 and Z11 were rewritten for it.  WHAT THIS CANNOT SAY: that a write lands, a lock waits or a gate refuses -
sandbox-netfile.py, the sections hwrite and kwrite.

***AND THE CHECKS ARE THEMSELVES CHECKED.***  --selftest breaks each invariant in the way an edit plausibly would and requires some
check to notice.  A mutant that nothing catches is reported as a FAILURE of the self-test.
"""

import fnmatch
import functools
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.abspath(os.path.join(HERE, os.pardir))
SDSYS = os.path.join(SD64, "sdsys")
GPL = os.path.join(SDSYS, "gpl.bp")
GPLSRC = os.path.join(SD64, "gplsrc")
ROOT = os.path.dirname(os.path.dirname(SD64))
MSGDIR = os.path.join(SDSYS, "messages")

NK_C = ("netfiles.c", "descr.h", "sd.h", "op_dio1.c", "op_dio2.c", "op_dio3.c", "op_dio4.c", "op_lock.c", "dh_ak.c", "dh_misc.c", "analyse.c", "k_error.c", "pdump.c")   # slice 3c
C_FILES = ("keys.h", "sysseg.h", "op_kernel.c", "sd_tls.c", "sd_tls.h", "op_skt.c", "op_sdext.c", "op_sh.c", "err.h") + NK_C       # op_sh.c: slice 3e (edit_kind_of_net_name); err.h: S.72 (ER_LCK, ER_NLK)
MAIN_BP = ("login", "cproc", "apisrvr", "modifya", "createa", "create_account", "acc_os_info", "restorea",
           "netdefs", "setserver", "deleteserver", "listservers", "netcred", "setnetlogin", "deletenetlogin", "bcomp", "apifilesok", "netfile")
VERBS = (("set.server", "setserver", "$setserver"), ("delete.server", "deleteserver", "$deleteserver"),
         ("list.servers", "listservers", "$listservers"))
NL_VERBS = (("set.netlogin", "setnetlogin", "$setnetlogin"), ("delete.netlogin", "deletenetlogin", "$deletenetlogin"))   # slice 2b: in newvoc AND voc_template
MSG_FIRST, MSG_LAST = 11411, 11446      # 11411-11439 slice 1, 11440-11446 slice 2a (CONNECT); 11447-11449 are free
NL_MSG_FIRST, NL_MSG_LAST = 11450, 11479    # slice 2b: the person's login (the whole block is this slice's)
NF_MSG_FIRST, NF_MSG_LAST, NF_MSG_USED = 11490, 11512, 11512    # slice 3b: the remote file handler's block; 11490-11506 written and used by the handler; slice 3e: 11509-11512; 18 Oct 26 S.66: 11513-11520 are the shared account's (test-shared-units.py), no longer kept free here
NF_MSG_KERNEL = (11507, 11508)                                  # slice 3c: the kernel's own two (netfiles.c); slice 3e: 11510 and 11511 are the kernel's as well (NF_MSG_BOTH, NF_MSG_KERNEL_ONLY)
NF_MSG_KERNEL_ONLY = (11507, 11508, 11511)                      # never used by the handler (11511 is net_gate's / net_refuse's); 11510 is cited by both; 11513 onwards are the shared account's since S.66 (test-shared-units.py)
LINUX_BLOCK = (11000, 11999)
SH_FILES = ("installsdcore.sh", "deletesdcore.sh", "sd-elevate", "sdcore.sudoers", "regress.sh", "regress-map.txt")      # shell-style comments (#)


@functools.lru_cache(maxsize=None)
def strip_c(src):
    def blank(m):
        return "\n" * m.group(0).count("\n")
    src = re.sub(r"/\*.*?\*/", blank, src, flags=re.S)
    return re.sub(r"//[^\n]*", "", src)


@functools.lru_cache(maxsize=None)
def strip_bas(src):
    out = []
    for line in src.split("\n"):
        s = line.lstrip()
        if s.startswith("*") or s.startswith("!"):
            out.append("")
            continue
        cut = line.find(";*")
        out.append(line if cut < 0 else line[:cut])
    return "\n".join(out)


@functools.lru_cache(maxsize=None)
def strip_sh(src):
    return "\n".join("" if l.lstrip().startswith("#") else l for l in src.split("\n"))


def strip_strings(src):
    """Quoted text emptied, so that a word inside a string ('WRITE', 'netservers') is not taken for a statement."""
    return re.sub(r"'[^'\n]*'|\"[^\"\n]*\"", "''", src)


def code(name, text):
    if name in C_FILES or name.startswith("c:"):
        return strip_c(text)
    if name in SH_FILES:
        return strip_sh(text)
    return strip_bas(text)


def at(text, needle, start=0):
    return text.find(needle, start)


def ordered(text, *needles):
    """Every needle found, each after the one before it."""
    pos = -1
    for n in needles:
        p = text.find(n, pos + 1)
        if p < 0:
            return False
        pos = p
    return True


def sysmsg_calls(text):
    """(number, [argument texts]) of every sysmsg(NNNNN, ...) call with a literal number."""
    out = []
    for m in re.finditer(r"sysmsg\(\s*(\d+)", text):
        k = m.end()
        while k < len(text) and text[k] in " \t":
            k += 1
        if k < len(text) and text[k] == ",":
            k += 1
        args, cur, depth, q = [], "", 0, None
        while k < len(text):
            ch = text[k]
            if q:
                cur += ch
                if ch == q:
                    q = None
            elif ch in "'\"":
                q = ch
                cur += ch
            elif ch in "(<":
                depth += 1
                cur += ch
            elif ch in ")>":
                if ch == ")" and depth == 0:
                    if cur.strip():
                        args.append(cur.strip())
                    break
                depth -= 1
                cur += ch
            elif ch == "," and depth == 0:
                args.append(cur.strip())
                cur = ""
            else:
                cur += ch
            k += 1
        out.append((int(m.group(1)), args))
    return out


def load():
    srcs = {}

    def get(name, path):
        if not os.path.exists(path):
            print("test-net-units: CANNOT RUN - %s is missing" % path)
            sys.exit(2)
        with open(path, encoding="utf-8", errors="replace") as f:
            srcs[name] = f.read()
    for n in C_FILES:
        get(n, os.path.join(GPLSRC, n))
    get("gpl.src", os.path.join(SD64, "gpl.src"))                            # slice 3c: the list the Makefile builds from
    for fname in sorted(os.listdir(GPLSRC)):                                  # slice 3c: every other kernel source that is given a file variable (the census scan)
        if fname.endswith(".c") and fname not in srcs:
            with open(os.path.join(GPLSRC, fname), encoding="utf-8", errors="replace") as f:
                text = f.read()
            if "k_get_file(" in text or "data.fvar" in text:
                srcs["c:" + fname] = text
    get("int$keys.h", os.path.join(GPL, "int$keys.h"))
    get("syscom/keys.h", os.path.join(SDSYS, "syscom", "keys.h"))
    get("createacc.h", os.path.join(SDSYS, "syscom", "createacc.h"))
    get("installsdcore.sh", os.path.join(ROOT, "installsdcore.sh"))
    get("deletesdcore.sh", os.path.join(ROOT, "deletesdcore.sh"))
    get("sd-elevate", os.path.join(HERE, "sd-elevate"))
    get("sdcore.sudoers", os.path.join(HERE, "sdcore.sudoers"))
    get("regress.sh", os.path.join(HERE, "regress.sh"))                    # slice 3a: the netfile suite is wired in
    get("regress-map.txt", os.path.join(HERE, "regress-map.txt"))
    get("sandbox-netfile.py", os.path.join(HERE, "sandbox-netfile.py"))
    get("netfake.py", os.path.join(HERE, "netfake.py"))                    # slice 3e: its history line is checked (S2z)
    for fname in sorted(os.listdir(GPL)):
        p = os.path.join(GPL, fname)
        if os.path.isfile(p):
            get("bp:" + fname, p)
    for n in MAIN_BP:
        if "bp:" + n not in srcs:
            print("test-net-units: CANNOT RUN - %s is missing" % os.path.join(GPL, n))
            sys.exit(2)
        srcs[n] = srcs["bp:" + n]
    for word, _prog, _cat in VERBS:
        get("voc:" + word, os.path.join(SDSYS, "voc_template", word))
    for word, _prog, _cat in NL_VERBS:
        get("voc:" + word, os.path.join(SDSYS, "voc_template", word))
        get("newvoc:" + word, os.path.join(SDSYS, "newvoc", word))
    srcs["newvoc.list"] = "\n".join(sorted(os.listdir(os.path.join(SDSYS, "newvoc"))))
    for n in list(range(MSG_FIRST, MSG_LAST + 1)) + list(range(NL_MSG_FIRST, NL_MSG_LAST + 1)):
        p = os.path.join(MSGDIR, str(n))
        srcs["msg:%d" % n] = open(p, encoding="utf-8", errors="replace").read() if os.path.exists(p) else None
    for n in (2001, 2018, 6000, 10024, 10080, 10081, 10087, 11480, 11481, 11482):      # 11480-11482: slice 2c (11481 is not used; read only to be sure)
        p = os.path.join(MSGDIR, str(n))
        srcs["msg:%d" % n] = open(p, encoding="utf-8", errors="replace").read() if os.path.exists(p) else None
    for n in range(NF_MSG_FIRST, NF_MSG_LAST + 1):                                      # slice 3b: the handler's block
        p = os.path.join(MSGDIR, str(n))
        srcs["msg:%d" % n] = open(p, encoding="utf-8", errors="replace").read() if os.path.exists(p) else None
    return srcs


def checks(srcs):
    rows = []

    def ck(i, ok, detail=""):
        rows.append((i, bool(ok), detail))

    c = {name: code(name, text) for name, text in srcs.items() if isinstance(text, str) and not name.startswith(("msg:", "voc:", "newvoc"))}

    # ---- K. numbers, bits, fields -------------------------------------------------------------------------------------------
    got = {m.group(1): int(m.group(2)) for m in re.finditer(r"#define\s+(K_[A-Z0-9_]+)\s+(\d+)", c["keys.h"])}
    ck("K1 keys.h: K_NET is 127", got.get("K_NET") == 127, repr(got.get("K_NET")))
    by_num = {}
    for k, v in got.items():
        by_num.setdefault(v, []).append(k)
    ck("K2 no kernel key number is used twice (127 is K_NET's alone)", all(len(v) == 1 for v in by_num.values()),
       repr({n: v for n, v in by_num.items() if len(v) > 1}))
    bas = {m.group(1): int(m.group(2)) for m in re.finditer(r"\$define\s+(K\$[A-Z0-9.]+)\s+(\d+)", c["int$keys.h"])}
    ck("K3 int$keys.h: K$NET is 127 and nothing else there is", bas.get("K$NET") == 127 and sum(1 for v in bas.values() if v == 127) == 1,
       repr(bas.get("K$NET")))
    acc = {m.group(1): int(m.group(2)) for m in re.finditer(r"\$define\s+(ACC\$[A-Z0-9.]+)\s+(\d+)", c["syscom/keys.h"])}
    ck("K4 syscom/keys.h: ACC$NET is register field 15; 13 and 14 are the shared-account gates since S.66 (ACC$SHARED.READ 13, ACC$SHARED.WRITE 14, test-shared-units.py S1) and no field is used twice",
       acc.get("ACC$NET") == 15 and acc.get("ACC$SHARED.READ") == 13 and acc.get("ACC$SHARED.WRITE") == 14
       and len(set(acc.values())) == len(acc.values()), repr(acc))
    ss = c["sysseg.h"]
    ug = {m.group(1): int(m.group(2), 16) for m in re.finditer(r"#define\s+(UG_[A-Z_]+)\s+(0x[0-9A-Fa-f]+)", ss)}
    ck("K5 sysseg.h: UG_NET is 0x0008 in the gates word, on its own bit, and 0x0010 and 0x0020 are the shared gates since S.66 (UG_SHARED_READ, UG_SHARED_WRITE), each on its own bit",
       ug.get("UG_NET") == 8 and ug.get("UG_SHARED_READ") == 0x10 and ug.get("UG_SHARED_WRITE") == 0x20
       and len(set(ug.values())) == len(ug) and all(v & (v - 1) == 0 for v in ug.values())
       and re.search(r"u_int16_t\s+gates\s*;", ss) is not None, repr(ug))
    ca = {m.group(1): int(m.group(2)) for m in re.finditer(r"\$define\s+(CA\$[A-Z0-9.]+)\s+(\d+)", c["createacc.h"])}
    ck("K6 createacc.h: CA$NET is 35, after CA$DICT.EDIT 34, and no setting is used twice",
       ca.get("CA$NET") == 35 and ca.get("CA$DICT.EDIT") == 34 and len(set(ca.values())) == len(ca.values()), repr(ca.get("CA$NET")))

    # ---- C. the kernel ---------------------------------------------------------------------------------------------------
    kn = c["op_kernel.c"]
    i = kn.find("case K_NET:")
    body = kn[i:kn.find("case K_EDIT_OK:", i)] if i >= 0 else ""      # the whole K_NET case (it holds the -2 branch before the set branch since slice 3e)
    ck("C1 K_NET sets the gate only from a $internal program (n >= 0, then HDR_INTERNAL, then the bit), -1 only asks",
       kn.count("case K_NET:") == 1 and "GetInt(descr)" in body and ordered(body, "n >= 0", "HDR_INTERNAL", "SET_MY_GATE(UG_NET, n > 0)"), "")
    ck("C2 ...clears with UG_NET, answers the UG_NET bit as 1 or 0, and touches no other gate",
       "SET_MY_GATE(UG_NET, n > 0)" in body and "result.data.value = MY_GATE(UG_NET)" in body
       and "UG_VOC_EDIT" not in body and "UG_BP_EDIT" not in body and "UG_DICT_EDIT" not in body, "")

    # ---- B. the BASIC side: where the gate is loaded --------------------------------------------------------------------------
    lg, cp, ap = c["login"], c["cproc"], c["apisrvr"]
    ck("B1 LOGIN loads K$NET from ACC$NET at sign-on, off unless 'yes', beside the SD.ACCOUNTS load and before the edit gates",
       len(re.findall(r"kernel\(K\$NET,", lg)) == 1
       and re.search(r"void kernel\(K\$NET,\s*upcase\(trim\(acc\.rec<ACC\$NET>\)\) = 'YES'\)", lg) is not None
       and ordered(lg, "void kernel(K$SD.ACCOUNTS,", "void kernel(K$NET,", "void kernel(K$VOC.EDIT,"), "")
    m = re.search(r"void kernel\(K\$NET,\s*upcase\(trim\(acc\.record<ACC\$NET>\)\) = 'YES'\)", cp)
    ck("B2 CPROC's logto loads K$NET from the NEW account's record (acc.record), off unless 'yes', after the SD.ACCOUNTS load and before the audit line",
       m is not None and 0 <= at(cp, "void kernel(K$SD.ACCOUNTS, upcase(trim(acc.record<") < m.start() < at(cp, "'logto account='"), "")
    ck("B3 CPROC holds it in stk.net with the other account-scoped gates and gives it back in revert.account, before the revert audit line",
       re.search(r"stk\.sd\.accounts = kernel\(K\$SD\.ACCOUNTS, -1\)\s*\n\s*stk\.net = kernel\(K\$NET, -1\)", cp) is not None
       and ordered(cp, "revert.account:", "void kernel(K$SD.ACCOUNTS, stk.sd.accounts)", "void kernel(K$NET, stk.net)", "'logto revert account='")
       and len(re.findall(r"kernel\(K\$NET,", cp)) == 4, "")      # slice 3e: the fourth is kernel(K$NET, -2) in para.reset.environment (S2 checks it)
    ck("B4 the API server starts api.net.grant false at every entry, reads it from ACC$NET with the other grants, and loads K$NET with SD.ACCOUNTS",
       re.search(r"api\.net\.grant = @false", ap) is not None
       and re.search(r"api\.net\.grant = \(upcase\(trim\(acc\.rec<ACC\$NET>\)\) = 'YES'\)", ap) is not None
       and ordered(ap, "api.net.grant = @false", "api.net.grant = (upcase(trim(acc.rec<ACC$NET>)) = 'YES')", "void kernel(K$NET, api.net.grant)")
       and ordered(ap, "void kernel(K$SD.ACCOUNTS, api.sd.grant)", "void kernel(K$NET, api.net.grant)"), "")
    ck("B4b ...the load is at EVERY entry (account-scoped), so it is not inside the master.login.done test the edit gates sit in",
       0 <= at(ap, "void kernel(K$NET, api.net.grant)") < at(ap, "if not(master.login.done) then\n   void kernel(K$VOC.EDIT"), "")
    ck("B4c ...and the OS user sdsys entering the sdsys account holds it ON (the administrator passes), before the refusals and the load",
       re.search(r"if downcase\(@logname\) = 'sdsys' and downcase\(new\.account\) = 'sdsys' then(?:\s*\n\s*api\.[\w.]+\.grant = @true)*\s*\n\s*api\.net\.grant = @true\s*\n\s*end", ap) is not None
       and 0 <= at(ap, "downcase(@logname) = 'sdsys'") < at(ap, "void kernel(K$NET, api.net.grant)"), "")
    sites = {}
    for name, text in c.items():
        if name.startswith("bp:"):
            n = len(re.findall(r"kernel\(K\$NET,", text))
            if n:
                sites[name[3:]] = n
    ck("B5 no program but LOGIN (1), CPROC (4: three of the gate's own, and since slice 3e kernel(K$NET, -2) in para.reset.environment), the API server (1), set.netlogin (1), the remote file handler "
       "netfile (1) and the account holder's gate page tool_mygates (1, 24 Oct 26) mentions K$NET - the last three only ASK: K$NET, -1 (see U2, NF6)",
       sites == {"login": 1, "cproc": 4, "apisrvr": 1, "setnetlogin": 1, "netfile": 1, "tool_mygates": 1}, repr(sites))
    bad = [n[3:] for n, t in c.items() if n.startswith("bp:") and re.search(r"kernel\(K\$NET,\s*(?!-1\))(\d+|@true|1\b)", t)]
    ck("B6 nothing turns the gate on by a literal (K$NET with a number other than -1, or @true)", not bad, repr(bad))
    ups = {n[3:]: t for n, t in c.items() if n.startswith("bp:upgrade_")}
    ck("B7 there is NO upgrade walk for the gate: no upgrade_net program, no upgrade program touches ACC$NET, the installer names none "
       "(owner, 17 Oct: nothing existing used it, every existing account stays off)",
       not any("net" in n for n in ups) and not any("ACC$NET" in t for t in ups.values())
       and "upgrade_net" not in c["installsdcore.sh"] and "ACC$NET" not in c["installsdcore.sh"], "")

    # ---- M. the verbs that set it, the manifest ------------------------------------------------------------------------------
    mo = c["modifya"]
    ck("M1 MODIFY.ACCOUNT has NET-ON and NET-OFF, each through os.set with ACC$NET",
       all(re.search(r"case action = '%s'\s*\n\s*os\.field = ACC\$NET ; os\.want = @%s\s*\n\s*gosub os\.set\s*\n\s*return" % (w, b), mo)
           for w, b in (("NET-ON", "true"), ("NET-OFF", "false"))), "")
    ck("M2 ...os.set lets the words through on a group account (as SD-ON), and says only the NET state with 11411 (the other lines unchanged)",
       re.search(r"if group\.name\[1,4\] # 'sdu_' and .*os\.field # ACC\$NET( and os\.field # ACC\$PINS)? then", mo) is not None
       and re.search(r"if os\.field = ACC\$NET then\s*\n\s*crt sysmsg\(11411, acc\.name, if upcase\(trim\(acc\.new<ACC\$NET>\)\) = 'YES' then 'yes' else 'no'\)"
                     r"\s*\n\s*end else\s*\n\s*crt sysmsg\(10102,", mo) is not None, "")
    ck("M3 ...the syntax lines and the list of words name net-on and net-off",
       "modify.account <account> net-on | net-off" in mo and "net-on, net-off," in mo, "")
    cr, ca2 = c["createa"], c["create_account"]
    ck("M4 CREATE.ACCOUNT takes NET-ON (CA$NET = 1) and its syntax line names {net-on}",
       re.search(r"case upcase\(token\) = 'NET-ON'\s*\n\s*settings<CA\$NET> = 1", cr) is not None
       and cr.count("{net-on}") >= 1, "")
    ck("M5 !create_account: a request is exactly 1; a USER account is written 'yes' or 'no' explicitly, any other type 'yes' only when asked",
       "net.want = (settings<CA$NET> = 1)" in ca2
       and "acc.rec<ACC$NET> = if net.want then 'yes' else 'no'" in ca2 and "if net.want then acc.rec<ACC$NET> = 'yes'" in ca2, "")
    ck("M6 ...and a USER account is told its state: 11411 follows 11409",
       re.search(r"crt sysmsg\(11409,[^\n]*\n\s*crt sysmsg\(11411, acc\.name, acc\.rec<ACC\$NET>\)", ca2) is not None, "")
    ai, rs = c["acc_os_info"], c["restorea"]
    ck("M7 the manifest carries net: 1/0 for a USER account (after edit.dict, before the GROUP branch)",
       ordered(ai, "'edit.dict: '", "'net: '", "case grp[1,4] = 'sdg_'")
       and "'net: ':(if upcase(trim(acc.rec<ACC$NET>)) = 'YES' then 1 else 0)" in ai, "")
    ck("M8 RESTORE.ACCOUNT reads the manifest key net, clears it for each section, and hands it on as CA$NET",
       re.search(r"= 'net'\s*; m\.net = kv", rs) is not None and "settings<CA$NET> = m.net" in rs and "m.edit.dict = '' ; m.net = ''" in rs, "")

    # ---- D. the definitions: netdefs, set.server, delete.server, list.servers ------------------------------------------------------
    nd, ss_, ds, ls = c["netdefs"], c["setserver"], c["deleteserver"], c["listservers"]
    ck("D1 all four are $internal, catalogued once each under the right name, and netdefs is a subroutine",
       all("$internal" in t for t in (nd, ss_, ds, ls))
       and "subroutine netdefs(mode, defs, err)" in nd and "$catalog !netdefs" in nd
       and all(("$catalog %s" % cat) in c[prog] and len([n for n, t in c.items() if n.startswith("bp:") and ("$catalog %s\n" % cat) in t + "\n"]) == 1
               for _w, prog, cat in VERBS)
       and len([n for n, t in c.items() if n.startswith("bp:") and "$catalog !netdefs" in t]) == 1, "")
    nv = srcs["newvoc.list"].lower().split("\n")
    ck("D2 the three verbs are in voc_template (V / CA / $name) and NOT in newvoc, so only SDSYS has them",
       all(srcs["voc:" + w].split() == ["V", "CA", cat] and w not in nv for w, _p, cat in VERBS), "")
    ck("D3 each verb asks K$ADMINISTRATOR first, before it reads a word or opens anything (netdefs asks for WRITE before it looks at a line)",
       all(0 <= at(t, "kernel(K$ADMINISTRATOR, -1)") < min(x for x in (at(t, "openpath"), at(t, "@sentence"), at(t, "call !netdefs")) if x >= 0)
           for t in (ss_, ds, ls))
       and ordered(nd, "case mode = 'WRITE'", "kernel(K$ADMINISTRATOR, -1)", "dcount(defs, @fm)", "openseq tmp"), "")

    # set.server: every field before anything is written
    first_write = at(ss_, "call !netdefs('WRITE'")
    fld = [at(ss_, "sysmsg(%d" % n) for n in (11414, 11415, 11416, 11417, 11418, 11419, 11420, 11421)]
    gate = at(ss_, "if bad # 0 then stop")
    ck("S1 set.server looks at every field (11414 to 11421) BEFORE it stops on 'bad', and that stop is before the lock, the read and the write",
       all(0 <= f < gate for f in fld) and 0 <= gate < at(ss_, "openpath @sdsys to sys.f") < at(ss_, "readu lock.rec") < at(ss_, "call !netdefs('READ'") < first_write
       and ss_.count("call !netdefs('WRITE'") == 1 and ss_.count("readu lock.rec") == 1, repr((fld, gate)))
    ck("S2 ...the limit of 10 and the replace question come before the write, a 'no' (or input that ends) stops with nothing written, and NO.QUERY skips only the question",
       0 <= at(ss_, "sysmsg(11422") < first_write and 0 <= at(ss_, "sysmsg(11423") < first_write
       and re.search(r"\$define NET\.MAX\.SERVERS 10\b", ss_) is not None
       and "if found = 0 and n.defs >= NET.MAX.SERVERS then" in ss_ and "if found # 0 and not(no.query) then" in ss_
       and re.search(r"if yn = 'N' then\s*\n\s*gosub release\.lock\s*\n\s*@system\.return\.code = 0\s*\n\s*stop sysmsg\(11426", ss_) is not None
       and ss_.count("if yn = '' and status() = ER$EOF then yn = 'N'") == 2, "")   # the replace question and, since slice 2a, the key question
    ck("S3 ...the lock is released straight after the write, whether or not it worked, and before the audit line",
       re.search(r"call !netdefs\('WRITE', defs, err\)\s*\n\s*gosub release\.lock\s*\n\s*if err # '' then", ss_) is not None
       and 0 <= first_write < at(ss_, "kernel(K$AUDIT, 'set.server name='"), "")
    ck("S4 ...the rules: name 1-16 of lower case and digits and a letter first; host 1-253 of letters, digits, dots, hyphens and colons, not "
       "starting with - or .; port 1-65535; account 1-32 of letters, digits and ._-; pin 64 hex; at most 10 servers",
       "len(name) < 1 or len(name) > 16" in ss_ and "index(lc.set, name[1, 1], 1) = 0" in ss_
       and "len(host) < 1 or len(host) > 253" in ss_ and "chk.set = lc.set:digits:'.-:'" in ss_ and "host[1, 1] = '-' or host[1, 1] = '.'" in ss_
       and "port matches '1N0N'" in ss_ and "port + 0 >= 1 and port + 0 <= 65535" in ss_
       and "len(account) < 1 or len(account) > 32" in ss_ and "chk.set = lc.set:upcase(lc.set):digits:'._-'" in ss_
       and "len(pin) # 64" in ss_ and ss_.count("chk.set = digits:'abcdef'") == 2 and re.search(r"\$define NET\.MAX\.SERVERS 10\b", ss_) is not None, "")
    ck("S5 ...the accounts list: a name is checked for form and then against the register (11421); a list over 2000 bytes, an empty name or a name over 32 is 11420",
       re.search(r"\$define NET\.MAX\.ACCLIST 2000\b", ss_) is not None and "len(acc.list) <= NET.MAX.ACCLIST" in ss_
       and "if a = '' or len(a) > 32 or not(chk.ok) then list.ok = @false" in ss_
       and ordered(ss_, "sysmsg(11420", "openpath @sdsys:@ds:'accounts'", "read reg.rec from acc.f, a then", "sysmsg(11421"), "")
    ck("S6 ...the mode is read unless write is given, and only read or write is a mode (11419 for another word at the mode's place)",
       "mode = 'read'" in ss_ and "(lw = 'read' or lw = 'write') and not(mode.given)" in ss_ and "sysmsg(11419, w)" in ss_, "")

    # delete.server
    dwrite = at(ds, "call !netdefs('WRITE'")
    ck("X1 delete.server finds the name (11430 and a stop when there is none) and cuts it out BEFORE the one write, under the lock, released after",
       ds.count("call !netdefs('WRITE'") == 1 and ordered(ds, "readu lock.rec", "call !netdefs('READ'", "sysmsg(11430", "del defs<found>", "call !netdefs('WRITE'")
       and re.search(r"call !netdefs\('WRITE', defs, err\)\s*\n\s*gosub release\.lock", ds) is not None
       and re.search(r"if found = 0 then\s*\n\s*gosub release\.lock\s*\n\s*@system\.return\.code = -ER\$FNF\s*\n\s*stop sysmsg\(11430", ds) is not None
       and dwrite < at(ds, "kernel(K$AUDIT, 'delete.server name='"), "")
    ck("X2 delete.server wants exactly one word (11429 otherwise) and converts the name to lower case",
       "if dcount(words, ' ') # 2 then" in ds and "stop sysmsg(11429)" in ds and "name = downcase(field(words, ' ', 2))" in ds, "")

    # list.servers
    ck("L1 list.servers takes no lock and writes nothing (no readu, no WRITE, no release), and has the administrator test",
       not re.search(r"\b(readu|readvu|readlist|release|lock)\b", ls) and "!netdefs('WRITE'" not in ls and "!netdefs('READ'" in ls, "")
    ck("L2 list.servers shows the pin SHORTENED (16 digits and three dots) in the list and the FULL pin only for a named server (and the date then)",
       re.search(r"if name = '' then\s*\n\s*pin\.text = defs<i,5>\[1, 16\] : '\.\.\.'\s*\n\s*end else\s*\n\s*pin\.text = defs<i,5>\s*\n\s*end", ls) is not None
       and "if name # '' then crt sysmsg(11435, defs<i,8>)" in ls, "")
    ck("L3 list.servers: no definitions is 11433, an unknown name is 11430, a damaged line is 11436, and the account field 'none' is message 11438",
       "sysmsg(11433)" in ls and "sysmsg(11430, name)" in ls and "sysmsg(11436, i)" in ls and "sysmsg(11438)" in ls, "")

    # netdefs: the one writer
    ck("N1 !netdefs checks every definition (8 fields, no bar, no byte outside 32-126 apart from the value mark) BEFORE the first byte is written (11436)",
       ordered(nd, "case mode = 'WRITE'", "ok = (dcount(one, @vm) = NETDEFS.FIELDS)", "c # 253 and (c < 32 or c > 126 or c = 124)", "err = 11436",
               "tmp = path : '.new'", "openseq tmp to tmp.f", "writeseq line to tmp.f", "osrename(tmp, path)")
       and nd.count("openseq tmp to tmp.f") == 1 and "$define NETDEFS.FIELDS 8" in nd, "")
    ck("N2 ...the file is netservers in @sdsys, written whole as netservers.new and renamed over the old one LAST, and a failed write deletes the copy",
       "$define NETDEFS.FILE   'netservers'" in nd and "path = @sdsys:@ds:NETDEFS.FILE" in nd
       and nd.count("osrename(") == 1 and nd.count("writeseq") == 1
       and re.search(r"if err # '' then\s*\n\s*void ospath\(tmp, OS\$DELETE\)\s*\n\s*return\s*\n\s*end\s*\n\s*if not\(osrename\(tmp, path\)\) then", nd) is not None, "")
    ck("N3 ...mode 644: the umask is set to 022 (18) before the copy is made, put back straight after, and before any line is written",
       ordered(nd, "old.umask = umask(-1)", "void umask(18)", "openseq tmp to tmp.f", "void umask(old.umask)", "writeseq line to tmp.f"), "")
    ck("N4 ...READ takes no administrator test and no lock, turns the bar into a value mark, and replaces mark bytes 251 to 255 so a line cannot make a new attribute",
       ordered(nd, "case mode = 'READ'", "convert char(251)", "convert '|' to @vm in line", "case mode = 'WRITE'")
       and "kernel(K$ADMINISTRATOR" not in nd[nd.find("case mode = 'READ'"):nd.find("case mode = 'WRITE'")], "")
    names = {n[3:]: t for n, t in c.items() if n.startswith("bp:") and "netservers" in strip_strings(t).replace("'", "") + t and "netservers" in t}
    ck("N5 the file's name is in the code of netdefs, and of set.server and delete.server only as the lock id netservers.lock",
       set(names) == {"netdefs", "setserver", "deleteserver"}
       and all(re.fullmatch(r"netservers\.lock", s) for s in re.findall(r"netservers[\w.]*", ss_ + ds)), repr(sorted(names)))
    ck("N6 netdefs holds the warning: the file must never hold a secret (read raw, since it is a comment)",
       "MUST NEVER HOLD A SECRET" in srcs["netdefs"], "")

    # the pin
    wsrc = r"\b(writeseq|writeblk|weofseq|oswrite|osdelete|osrename|osopen|openseq|write|writev|writeu|writet|delete|deleteu|os\.execute|execute|create|createfile|create\.file)\b"
    def bare(t):        # no quoted text, and the PROGRAM line (the verb delete.server is not the statement DELETE)
        return strip_strings(re.sub(r"^\s*program\s+\S+", "", t, flags=re.M))
    ck("P1 set.server, delete.server and list.servers have no statement that writes, deletes, creates or runs anything outside the register and the lock "
       "(only !netdefs writes the pin to disk)",
       not any(re.search(wsrc, bare(t)) for t in (ss_, ds, ls)), repr([re.search(wsrc, bare(t)).group(0) for t in (ss_, ds, ls) if re.search(wsrc, bare(t))]))
    def pin_lines(t):       # the lines that use the variable pin (pin.how, the audit word, and the routine's name connect.pin are not it)
        return [ln for ln in strip_strings(t).split("\n") if re.search(r"\bpin\b", re.sub(r"\b(?:pin\.how|connect\.pin)\b", "", ln))]
    leaks = [ln.strip() for ln in pin_lines(ss_) if re.search(r"\b(display|crt|print|stop|sysmsg|kernel)\b", ln)]
    ck("P2 the pin is never shown, printed or put on the audit trail by set.server (the audit line names the server, host, port, mode, "
       "whether it replaced and how the pin was obtained; the one hash that is shown, in CONNECT, is the variable spki - T7)", not leaks, repr(leaks))
    ck("P3 ...it goes into the definition line and nowhere else: its only uses are the lower-casing, the CONNECT word, the form test, the hash "
       "confirmed by SDSYS and the line that builds the definition (8 lines)",
       len(pin_lines(ss_)) == 8
       and re.search(r"one = name:@vm:host:@vm:port:@vm:account:@vm:pin:@vm:mode:@vm:acc\.clean:@vm:created", ss_) is not None
       and "'set.server name=' : name : ' host=' : host : ' port=' : port : ' mode=' : mode : ' replaced=' : rep.word : ' pin=' : pin.how)" in ss_, repr(len(pin_lines(ss_))))

    # ---- T. set.server ... connect (S.65 slice 2a): the order of the flow --------------------------------------------------------
    cp_i = ss_.find("\nconnect.pin:")
    cp_j = ss_.find("\nrelease.lock:", cp_i) if cp_i >= 0 else -1
    cpb = ss_[cp_i:cp_j] if 0 <= cp_i < cp_j else ""         # the routine
    mainb = ss_[:cp_i] if cp_i >= 0 else ss_                  # everything before it
    m_call = re.search(r"if connect\.mode then\s*\n\s*gosub connect\.pin[^\n]*\n\s*pin\.how = 'confirmed'\s*\n\s*end", ss_)
    p_call = m_call.start() if m_call else -1
    sop = strip_strings(ss_)
    ck("T1 the fifth word is CONNECT in any case (the pin is lower-cased first), it empties pin, and the typed-pin form test is skipped for it",
       ordered(ss_, "pin = downcase(field(words, ' ', 6))", "if pin = 'connect' then", "connect.mode = @true", "pin = ''")
       and ordered(ss_, "if not(connect.mode) then", "chk.text = pin", "len(pin) # 64"), "")
    ck("T2 nothing is dialled for a definition that would be refused: every field (11414-11421), the stop on 'bad', the lock, the read, the limit of "
       "10 and the replace question all come BEFORE the one gosub of connect.pin, which is guarded by connect.mode and followed by the write",
       all(0 <= f < gate for f in fld) and p_call >= 0 and ss_.count("gosub connect.pin") == 1
       and 0 <= gate < at(ss_, "readu lock.rec") < at(ss_, "call !netdefs('READ'") < at(ss_, "sysmsg(11422") < at(ss_, "sysmsg(11423") < p_call
       and p_call < at(ss_, "call !netdefs('WRITE'") and at(ss_, "pin.how = 'confirmed'") < at(ss_, "call !netdefs('WRITE'"),
       repr((gate, p_call)))
    ck("T3 the socket is opened in the routine only (the typed pin makes no connection), once, with SKT$BLOCKING + SKT$TLS and the NETWAIT timeout (5 seconds by default; the "
       "configuration parameter since 19 Oct 26, K8d), and the status and the operating system error are read at once",
       ss_.count("open.socket(") == 1 and cpb.count("open.socket(") == 1
       and re.search(r"skt = open\.socket\(host, port, SKT\$BLOCKING \+ SKT\$TLS, config\('NETWAIT'\)\)\s*\n\s*st = status\(\)\s*\n\s*oserr = os\.error\(\)", cpb) is not None
       and "NET.CONNECT.SECS" not in ss_ and re.search(r"^\$include keys\.h", ss_, re.M) is not None, "")
    ck("T4 a handshake only: the hash is read, the socket is closed (once), and all of that BEFORE anything is shown or asked; nothing is read from "
       "or written to the socket",
       ordered(cpb, "open.socket(", "if st # 0 then", "socket.info(skt, SKT$INFO.TLS.SPKI)", "close.socket skt", "sysmsg(11440", "display spki", "sysmsg(11441", "sysmsg(11442", "input yn")
       and ss_.count("close.socket") == 1 and not re.search(r"\b(?:write|read|select)\.socket\b|set\.socket\.mode|\bsend\b|\brecv\b", sop), "")
    ck("T5 THE KEY QUESTION IS ALWAYS ASKED: no.query is not mentioned in the routine, the only test of it is the replace question (before the connect), "
       "and the question is a loop that ends on y or n, an empty answer and input that ends being n",
       "no.query" not in cpb and len([ln for ln in sop.split("\n") if "no.query" in ln and re.search(r"\bif\b", ln)]) == 1
       and "if found # 0 and not(no.query) then" in ss_ and at(ss_, "if found # 0 and not(no.query) then") < p_call
       and ss_[p_call:at(ss_, "call !netdefs('WRITE'")].count("no.query") == 0
       and re.search(r"display sysmsg\(11442\) :", cpb) is not None
       and ordered(cpb, "loop", "display sysmsg(11442)", "input yn", "if yn = '' and status() = ER$EOF then yn = 'N'", "if yn = '' then yn = 'N'", "until yn = 'Y' or yn = 'N'", "repeat"), "")
    ck("T6 nothing is written on n, on a connection that fails, on a handshake that fails or on an empty hash: each gives the lock back and STOPS "
       "(n with return code 0), and the pin is taken from the hash only after the n has stopped",
       re.search(r"if yn = 'N' then\s*\n\s*gosub release\.lock\s*\n\s*@system\.return\.code = 0\s*\n\s*stop sysmsg\(11443, name\)\s*\n\s*end\s*\n\s*pin = spki\s*\n\s*return", cpb) is not None
       and re.search(r"gosub release\.lock\s*\n\s*@system\.return\.code = -ER\$FAILED\s*\n\s*if st = ER\$CONNECT and oserr = 0 then stop sysmsg\(11445, host, port\)\s*\n\s*stop sysmsg\(11444, host, port, st, oserr\)", cpb) is not None
       and re.search(r"gosub release\.lock\s*\n\s*@system\.return\.code = -ER\$FAILED\s*\n\s*stop sysmsg\(11446, host, port\)", cpb) is not None
       and cpb.count("pin = spki") == 1 and "call !netdefs" not in cpb and ss_.count("call !netdefs('WRITE'") == 1, "")
    ck("T7 the hash is lower case and trimmed, must be 64 hexadecimal digits before it is shown (an empty or damaged one is 11446), and the failure that "
       "is a handshake (status ER$CONNECT with os error 0, 11445) is told from the one that is not (11444)",
       ordered(cpb, "spki = downcase(trim(socket.info(skt, SKT$INFO.TLS.SPKI)))", "close.socket skt", "chk.set = digits:'abcdef'", "len(spki) # 64 or not(chk.ok)", "sysmsg(11446", "sysmsg(11440")
       and ordered(cpb, "sysmsg(11445", "sysmsg(11444") and "display spki" in cpb and ss_.count("display spki") == 1, "")
    ck("T8 the audit line says how the pin was obtained, in lower case: pin.how starts as typed, is confirmed only after connect.pin has returned, "
       "and is in the one audit line, after the write",
       ss_.count("pin.how = '") == 2 and ordered(ss_, "pin.how = 'typed'", "gosub connect.pin", "pin.how = 'confirmed'", "call !netdefs('WRITE'", "kernel(K$AUDIT, 'set.server name='")
       and ss_.count("pin=") == 1 and "' pin=' : pin.how)" in ss_ and ss_.count("kernel(K$AUDIT") == 1, "")

    # ---- C3-C6. the C side of the hash --------------------------------------------------------------------------------------
    tc, th, sk, kh, sy = c["sd_tls.c"], c["sd_tls.h"], c["op_skt.c"], c["keys.h"], c["syscom/keys.h"]
    i = tc.find("int sd_tls_client_peer_spki_sha256(")
    fb = tc[i:tc.find("\n}\n", i)] if i >= 0 else ""
    ck("C3 the hash is of the SubjectPublicKeyInfo - i2d_X509_PUBKEY of X509_get_X509_PUBKEY, then SHA-256 of those bytes, all 32 required - and NOT the "
       "certificate (X509_digest and i2d_X509 would change at every renewal)",
       fb != "" and tc.count("sd_tls_client_peer_spki_sha256(SD_TLS_CLIENT") == 1
       and "i2d_X509_PUBKEY(X509_get_X509_PUBKEY(cert), &der)" in fb and "EVP_Digest(" in fb and "EVP_sha256()" in fb and "n == 32" in fb
       and "X509_digest" not in fb and not re.search(r"i2d_X509\s*\(", fb), "")
    ck("C3b ...it asks for the certificate the server PRESENTED (SSL_get1_peer_certificate), answers false with none, and frees the certificate and the DER bytes",
       "SSL_get1_peer_certificate(c->ssl)" in fb and "if (cert == NULL)" in fb and "X509_free(cert)" in fb and "OPENSSL_free(der)" in fb
       and ordered(fb, "cert == NULL", "i2d_X509_PUBKEY", "EVP_Digest(", "OPENSSL_free(der)", "X509_free(cert)", "return ok"), "")
    i = tc.find("void sd_tls_client_end(SD_TLS_CLIENT* c) {")
    eb = tc[i:tc.find("\n}\n", i)] if i >= 0 else ""
    ck("C3c sd_tls_client_end holds SIGPIPE off around SSL_shutdown (the close_notify write ended the whole process when the peer had already closed the "
       "connection): the signal is blocked, and consumed only if it was not already pending, BEFORE the mask is put back",
       eb != "" and ordered(eb, "pthread_sigmask(SIG_BLOCK", "SSL_shutdown(c->ssl)", "sigtimedwait(", "pthread_sigmask(SIG_SETMASK")
       and "was_pending" in eb and "SSL_free(c->ssl)" in eb, "")
    ck("C4 sd_tls.h declares it with the same signature (SD_TLS_CLIENT*, 32 bytes out)",
       "int sd_tls_client_peer_spki_sha256(SD_TLS_CLIENT* c, unsigned char* out);" in th, "")
    i = sk.find("case SKT_INFO_TLS_SPKI:")
    cb = sk[i:sk.find("} break;", i)] if i >= 0 else ""
    ck("C5 SOCKET.INFO(.., SKT$INFO.TLS.SPKI) answers 64 lower case hex digits for a TLS socket and the NULL string for any other (the result is set to "
       "empty first and filled only when the socket has TLS and the hash was made)",
       cb != "" and sk.count("case SKT_INFO_TLS_SPKI:") == 1 and "char hex[65];" in cb and "unsigned char spki[32];" in cb
       and ordered(cb, "hex[0] = '\\0';", "sockvar->tls != NULL", "sd_tls_client_peer_spki_sha256((SD_TLS_CLIENT*)sockvar->tls, spki)", "i < 32", '"%02x"', "k_put_c_string(hex, &result_descr)")
       and "%02X" not in cb, "")
    spki_keys = {m.group(1): m.group(2) for m in re.finditer(r"#define\s+(SKT_INFO_[A-Z0-9_]+)\s+(\d+)", kh)}
    spki_bas = {m.group(1): m.group(2) for m in re.finditer(r"\$define\s+(SKT\$INFO\.[A-Z0-9.]+)\s+(\d+)", sy)}
    ck("C6 the key number is 11 in both headers and no other SKT_INFO / SKT$INFO name uses it",
       spki_keys.get("SKT_INFO_TLS_SPKI") == "11" and spki_bas.get("SKT$INFO.TLS.SPKI") == "11"
       and [k for k, v in spki_keys.items() if v == "11"] == ["SKT_INFO_TLS_SPKI"] and [k for k, v in spki_bas.items() if v == "11"] == ["SKT$INFO.TLS.SPKI"],
       repr((spki_keys.get("SKT_INFO_TLS_SPKI"), spki_bas.get("SKT$INFO.TLS.SPKI"))))

    # ---- G. messages ----------------------------------------------------------------------------------------------------------
    texts = {n: srcs["msg:%d" % n] for n in range(MSG_FIRST, MSG_LAST + 1)}
    ck("G1 messages 11411 to 11446 all exist, each one line of text, and inside the Linux block 11000-11999 (not the Windows block)",
       all(t is not None and t.strip() != "" and "\n" not in t.rstrip("\n") for t in texts.values())
       and LINUX_BLOCK[0] <= MSG_FIRST and MSG_LAST <= LINUX_BLOCK[1], repr([n for n, t in texts.items() if not t]))
    verb_code = nd + "\n" + ss_ + "\n" + ds + "\n" + ls
    used = {int(x) for x in re.findall(r"\b(114[1-4]\d)\b", verb_code)}
    ck("G2 every message from 11412 to 11446 is used by the verbs or !netdefs (11447-11449 are free), and 11411 by MODIFY.ACCOUNT and CREATE.ACCOUNT",
       set(range(11412, MSG_LAST + 1)) <= used and not (used & {11447, 11448, 11449}) and "11411" in mo and "11411" in ca2 and 11411 not in used,
       repr(sorted(set(range(11412, MSG_LAST + 1)) - used)))
    literal = {n for n, _a in sysmsg_calls(verb_code + "\n" + mo + "\n" + ca2) if 11411 <= n <= MSG_LAST}
    reused = {n for n, _a in sysmsg_calls(verb_code)} | set(int(x) for x in re.findall(r"\berr = (\d{4,5})", verb_code))
    ck("G3 every number the verbs print exists as a message file (11412-11446 and the reused 2001, 2018, 6000)",
       all(srcs.get("msg:%d" % n) for n in reused if n in (2001, 2018, 6000) or 11411 <= n <= MSG_LAST)
       and all(n in (2001, 2018, 6000) or 11411 <= n <= MSG_LAST for n in reused), repr(sorted(reused)))
    short = []
    for n, args in sysmsg_calls(verb_code + "\n" + mo + "\n" + ca2):
        t = srcs.get("msg:%d" % n)
        if t is None or not (11411 <= n <= MSG_LAST):
            continue
        top = max([int(x) for x in re.findall(r"%(\d)", t)] or [0])
        if len(args) != top:
            short.append((n, len(args), top))
    ck("G4 each call of sysmsg gives as many arguments as its message has %n places", not short and literal, repr(short))
    t = lambda n: texts.get(n) or ""
    ck("G5 the wording the users and the verbs rely on: 11411 'Account %1 has NET %2'; 11423 asks 'Replace it (y/<n>)?'; 11442 asks 'Trust this key (y/<n>)?'; "
       "11413 says no.query never skips the key question; 11439 names net-on; 11412 is the usage line and shows {pin | connect}; "
       "11440 says a handshake only, with the host and port; 11443 and 11444-11446 say nothing was written",
       t(11411).strip() == "Account %1 has NET %2" and t(11423).strip().endswith("Replace it (y/<n>)?") and t(11442).strip().endswith("Trust this key (y/<n>)?")
       and "no.query never skips" in t(11413) and "net-on" in t(11439)
       and t(11412).startswith("Usage: set.server") and "{pin | connect}" in t(11412)
       and "%1:%2" in t(11440) and "handshake only" in t(11440)
       and all("Nothing was written" in t(n) or "nothing was written" in t(n).lower() for n in (11443, 11444, 11445, 11446)), "")
    checks_2b(srcs, c, ck)
    checks_2c(srcs, c, ck)
    checks_3a(srcs, c, ck)
    checks_3b(srcs, c, ck)
    checks_3c(srcs, c, ck)
    checks_3d(srcs, c, ck)
    checks_3e(srcs, c, ck)
    checks_s2(srcs, c, ck)
    checks_s72(srcs, c, ck)
    return rows


SECRETS = r"\b(pw|client\.key|srvr\.key|salted|proof|stored\.key|expect\.v|auth\.msg|client\.sig|rec)\b"      # the names set.netlogin holds a secret in


def case_body(t, label):
    """The text of one action of $netcred: from  case act = 'LABEL'  to the next case or the end of the block."""
    i = t.find("case act = '%s'" % label)
    if i < 0:
        return ""
    ends = [x for x in (t.find("\n      case act =", i + 5), t.find("\n   end case", i)) if x > 0]
    return t[i:min(ends)] if ends else t[i:]


def routine_body(t, label):
    """A BASIC internal subroutine: from  label:  to the next line that starts a label or the final end."""
    m = re.search(r"^%s:\s*$" % re.escape(label), t, re.M)
    if not m:
        return ""
    n = re.search(r"^[a-z][\w.$]*:\s*$|^end\s*$", t[m.end():], re.M)
    return t[m.start():m.end() + n.start()] if n else t[m.start():]


def fail_places(t):
    """(message number, how many fail.aK it sets) for every  fail.num = N ; fail.a1 = .. ; fail.a2 = ..  line."""
    out = []
    for m in re.finditer(r"fail\.num = (\d+)([^\n]*)", t):
        out.append((int(m.group(1)), len(re.findall(r"fail\.a\d = ", m.group(2)))))
    return out


def err_places(t):
    """(message number, how many arguments it gives) for every  err = N:@vm:arg:@vm:arg  statement of $netcred."""
    out = []
    for m in re.finditer(r"\berr = (\d{4,5})([^\n]*)", t):
        out.append((int(m.group(1)), m.group(2).count(":@vm:")))
    return out


def checks_2b(srcs, c, ck):
    """S.65 slice 2b: the person's login on a server."""
    kh, sy, ex_ = c["keys.h"], c["syscom/keys.h"], c["op_sdext.c"]
    nc, sn, dn, bc = c["bp:netcred"], c["bp:setnetlogin"], c["bp:deletenetlogin"], c["bp:bcomp"]

    # ---- F. SD_FILE_PRIVATE: the C test -------------------------------------------------------------------------------------------
    sd_c = {m.group(1): int(m.group(2)) for m in re.finditer(r"#define\s+(SD_[A-Za-z0-9_]+)\s+(\d+)\b", kh)}
    sd_b = {m.group(1): int(m.group(2)) for m in re.finditer(r"\$define\s+(SD_[A-Za-z0-9_]+)\s+(\d+)\b", sy)}
    both = {k for k in sd_c if k in sd_b and 100 <= sd_c[k] <= 127}
    ck("F1 SD_FILE_PRIVATE is 111 in gplsrc/keys.h and in syscom/keys.h, no other SD_ name uses 111 in either, and every SDEXT function number the two headers "
       "share (100-127) is the same in both",
       sd_c.get("SD_FILE_PRIVATE") == 111 and sd_b.get("SD_FILE_PRIVATE") == 111
       and [k for k, v in sd_c.items() if v == 111] == ["SD_FILE_PRIVATE"] and [k for k, v in sd_b.items() if v == 111] == ["SD_FILE_PRIVATE"]
       and all(sd_c[k] == sd_b[k] for k in both) and "SD_FILE_PRIVATE" in both, repr((sd_c.get("SD_FILE_PRIVATE"), sd_b.get("SD_FILE_PRIVATE"))))
    i = ex_.find("case SD_FILE_PRIVATE:")
    cb = ex_[i:ex_.find("break;", i)] if i >= 0 else ""
    ck("F2 the SDEXT case answers the text 0 unless the C test says 1: the answer is set to '0' first, '1' is put in only inside "
       "`if (file_private_check(...))` for the word FILE (want_dir 0) and for the word DIR (want_dir 1), a wrong argument count is not 1, and "
       "exactly the text '0' or '1' is returned",
       ex_.count("case SD_FILE_PRIVATE:") == 1 and cb != "" and ordered(cb, "answer[0] = '0';", "argCnt != 2", "SD_EXT_ARG_CNT", "k_put_c_string(answer, e_stack)")
       and cb.count("answer[0] = '1'") == 2
       and re.search(r'strcmp\(SDMEArgArray\[1\], "FILE"\) == 0\)\s*\{\s*if \(file_private_check\(SDMEArgArray\[0\], 0\)\)\s*answer\[0\] = \'1\';', cb) is not None
       and re.search(r'strcmp\(SDMEArgArray\[1\], "DIR"\) == 0\)\s*\{\s*if \(file_private_check\(SDMEArgArray\[0\], 1\)\)\s*answer\[0\] = \'1\';', cb) is not None
       and re.search(r"if \(argCnt != 2\) \{\s*process\.status = SD_EXT_ARG_CNT;\s*\} else if", cb) is not None, "")
    j = ex_.find("Private int file_private_check(const char* path, int want_dir) {")
    fb2 = ex_[j:ex_.find("\n}\n", j) + 3] if j >= 0 else ""          # the function, to its closing brace
    ck("F3 file_private_check is fail-closed: a path that is not absolute or is PATH_MAX or longer is 0, lstat (NOT stat, which follows a link) failing is 0, "
       "an owner that is not geteuid() (NOT getuid) is 0, any bit in 077 is 0, and no `return 1;` stands anywhere in it",
       fb2 != "" and ordered(fb2, "path == NULL || path[0] != '/'", "return 0;", "len >= sizeof(parent)", "return 0;", "lstat(path, &st) != 0", "return 0;",
                             "st.st_uid != geteuid()", "return 0;", "(st.st_mode & 077) != 0", "return 0;")
       and not re.search(r"(?<![l\w])stat\s*\(", fb2) and "getuid" not in fb2 and not re.search(r"return\s+1\s*;", fb2) and "access(" not in fb2
       and re.search(r"if \(lstat\(path, &st\) != 0\)\s*return 0;", fb2) is not None and re.search(r"if \(st\.st_uid != geteuid\(\)\)\s*return 0;", fb2) is not None
       and re.search(r"if \(\(st\.st_mode & 077\) != 0\)\s*return 0;", fb2) is not None
       and re.search(r"if \(path == NULL \|\| path\[0\] != '/'\)\s*return 0;", fb2) is not None and re.search(r"if \(len >= sizeof\(parent\)\)\s*return 0;", fb2) is not None, "")
    ck("F4 ...a directory test is S_ISDIR of the lstat result (a link to a directory is not one); a file test is S_ISREG of it, and then the PARENT directory "
       "(everything before the last slash, '/' for a file in the root) must pass the directory test, which is the last thing and the answer",
       ordered(fb2, "if (want_dir)", "return S_ISDIR(st.st_mode) ? 1 : 0;", "!S_ISREG(st.st_mode)", "return 0;", "memcpy(parent, path, len + 1)", "strrchr(parent, '/')",
               "return file_private_check(parent, 1);")
       and re.search(r"return file_private_check\(parent, 1\);\s*\}\s*$", fb2) is not None, "")
    sdext_calls = {n[3:]: re.findall(r"SDEXT\([^\n]*SD_FILE_PRIVATE\)[^\n]*", t) for n, t in c.items() if n.startswith("bp:") and "SD_FILE_PRIVATE" in t}
    ck("F5 only $netcred (5 calls: the directory, and the file for EXISTS, READ, the new file and DELETE) and set.netlogin (1: the directory) call it, each with "
       "@TRUE and a FILE or DIR word, each compared with the text '1'",
       set(sdext_calls) == {"netcred", "setnetlogin"} and len(sdext_calls.get("netcred", [])) == 5 and len(sdext_calls.get("setnetlogin", [])) == 1
       and all(re.search(r"SDEXT\(\w[\w.]* : @FM : '(?:FILE|DIR)', @TRUE, SD_FILE_PRIVATE\) (?:#|=) '1'", x) for v in sdext_calls.values() for x in v), repr(sdext_calls))
    ck("F6 SDEXT is an INTERNAL intrinsic in BCOMP (int.intrinsics), so a user program cannot call SD_FILE_PRIVATE, or SD_PBKDF2, or any of its neighbours",
       'int.intrinsics<-1> = "SDEXT"' in bc and re.search(r'(?<!int\.)intrinsics<-1> = "SDEXT"', bc) is None, "")

    # ---- R. $netcred -------------------------------------------------------------------------------------------------------------
    ck("R1 $netcred is $internal, `subroutine netcred(action, server, record, pin, err)`, catalogued once as $netcred, and nothing else in gpl.bp takes the name",
       nc.lstrip().startswith("$internal") or "\n$internal\n" in nc, "")
    ck("R1b ...(the signature, the catalogue name, and uniqueness)",
       "subroutine netcred(action, server, record, pin, err)" in nc and "$catalog $netcred" in nc
       and len([n for n, t in c.items() if n.startswith("bp:") and "$catalog $netcred\n" in t + "\n"]) == 1 and "$internal" in nc, "")
    ck("R2 THE PATH RULE: /var/lib/sd-net is defined once (NETCRED.ROOT), the directory is that root, a slash and the Linux user, the file is the directory, a slash and "
       "the server name, the copy is the file and '.new'; the Linux user is kernel(K$USERNAME, 0) and nothing else (no @logname, no @who, no env()); no other string "
       "in the program names the directory",
       re.search(r"\$define NETCRED\.ROOT\s+'/var/lib/sd-net'", nc) is not None and nc.count("sd-net") == 1
       and len(re.findall(r"^   cred\.dir = NETCRED\.ROOT : '/' : lu\s*$", nc, re.M)) == 1 and len(re.findall(r"^   path = cred\.dir : '/' : server\s*$", nc, re.M)) == 1
       and len(re.findall(r"^   tmp = path : '\.new'\s*$", nc, re.M)) == 1
       and nc.count("kernel(K$USERNAME, 0)") == 1 and not re.search(r"@logname|@who|@user|\benv\(", nc), "")
    ck("R2b ...the server name is validated (a lower case letter first, 1-16 of lower case letters and digits: 11452) and the Linux user is refused when it is empty, "
       "root, sdsys, too long or holds a character outside letters, digits and ._- (11458), BOTH before the first look at the disk",
       ordered(nc, "len(server) < 1 or len(server) > 16", "index(lc.set, server[1, 1], 1) = 0", "err = 11452", "lu = kernel(K$USERNAME, 0)",
               "lu = '' or lu = 'root' or lu = 'sdsys'", "len(lu) > MAX.USERNAME.LEN", "err = 11458", "cred.dir = NETCRED.ROOT", "ospath(cred.dir, OS$EXISTS)")
       and "chk.text = server ; chk.set = lc.set:digits ; gosub check.chars" in nc and "chk.text = lu ; chk.set = os.chars ; gosub check.chars" in nc
       and "if not(dir.there) or SDEXT(cred.dir : @FM : 'DIR', @TRUE, SD_FILE_PRIVATE) # '1' then" in nc, "")
    rd, wr, dl, xs = case_body(nc, "READ"), case_body(nc, "WRITE"), case_body(nc, "DELETE"), case_body(nc, "EXISTS")
    ck("R3 THE PRIVATE-FILE TEST COMES FIRST, EVERY TIME: the directory is tested (and a directory that is missing or fails is 11454) before the action is looked at; "
       "READ tests the file before it opens it; DELETE tests it before it removes it; EXISTS tests it before it says 1; WRITE tests the new copy after it is written and "
       "BEFORE it is renamed over the login",
       ordered(nc, "dir.there = ospath(cred.dir, OS$EXISTS)", "SDEXT(cred.dir : @FM : 'DIR', @TRUE, SD_FILE_PRIVATE) # '1'", "err = 11454", "begin case")
       and ordered(rd, "SDEXT(path : @FM : 'FILE', @TRUE, SD_FILE_PRIVATE) # '1'", "err = 11454", "openseq path to f")
       and ordered(dl, "SDEXT(path : @FM : 'FILE', @TRUE, SD_FILE_PRIVATE) # '1'", "err = 11454", "ospath(path, OS$DELETE)")
       and ordered(xs, "SDEXT(path : @FM : 'FILE', @TRUE, SD_FILE_PRIVATE) = '1'", "record = 1")
       and ordered(wr, "openseq tmp to tmp.f", "writeseq line to tmp.f", "SDEXT(tmp : @FM : 'FILE', @TRUE, SD_FILE_PRIVATE) # '1'", "err = 11454", "osrename(tmp, path)"),
       repr([bool(rd), bool(wr), bool(dl), bool(xs)]))
    ck("R3b ...the file is opened in exactly two places (READ, and the new copy in WRITE), renamed in one, written in one, and deleted in three (the old copy before "
       "a write, the copy after a failure, the login by DELETE after its test)",
       nc.count("openseq ") == 2 and nc.count("osrename(") == 1 and nc.count("writeseq ") == 1 and nc.count("OS$DELETE") == 3
       and rd.count("openseq path to f") == 1, repr((nc.count("openseq "), nc.count("osrename("), nc.count("writeseq "), nc.count("OS$DELETE"))))
    ck("R4 THE FILE NEVER HOLDS THE PASSWORD: there is no password parameter and no word password, passwd or pw in the code; the only thing written is `line`, built "
       "from the literal v1 and the seven values one<1> to one<7>; WRITE has no other way to put text in the file",
       not re.search(r"\b(password|passwd|pw)\b", nc, re.I) and "line = 'v1'" in nc and "line := '|' : one<i>" in nc and nc.count("writeseq line to tmp.f") == 1
       and re.search(r"for i = 1 to 7\s*\n\s*line := '\|' : one<i>\s*\n\s*next i", wr) is not None
       and "subroutine netcred(action, server, record, pin, err)" in nc, "")
    ck("R5 READ in order: the pin argument must be 64 lower case hex digits (11459) before the disk is touched; no file is 11453; an untrusted one 11454; the line is read "
       "and the file closed; a mark byte or the wrong layout (v1 and 8 fields) is 11456; every value has its shape (check.record) BEFORE the stored pin is compared with "
       "the definition's (11455, and record stays null); the record is handed back last",
       ordered(rd, "record = ''", "gosub check.pin", "err = 11459", "ospath(path, OS$EXISTS)", "err = 11453", "SD_FILE_PRIVATE", "openseq path to f", "readseq line from f", "closeseq f",
               "convert(marks, '', line)", "err = 11456", "dcount(line, @fm) # 8 or line<1> # 'v1'", "err = 11456", "gosub check.record", "err = 11456",
               "if one<6> # pin then", "err = 11455", "record = one") and rd.count("record = one") == 1 and rd.count("gosub check.record") == 1, "")
    ck("R6 WRITE in order: the pin argument first (11459), the pin ARGUMENT is what is stored (attribute 6 of the record is overwritten), every value checked (11456) before "
       "the first byte is written; umask 077 (63) while the copy is made and put back straight after, before anything is written; the copy is tested; the rename is last, "
       "only when there is no error; a failed write deletes the copy",
       ordered(wr, "gosub check.pin", "err = 11459", "one = record", "one<6> = pin", "gosub check.record", "err = 11456", "line = 'v1'", "void umask(NETCRED.UMASK)",
               "openseq tmp to tmp.f", "void umask(old.umask)", "writeseq line to tmp.f", "closeseq tmp.f", "SD_FILE_PRIVATE", "if err = '' then\n            if not(osrename(tmp, path))")
       and re.search(r"if err # '' then void ospath\(tmp, OS\$DELETE\)", wr) is not None and re.search(r"\$define NETCRED\.UMASK\s+63\b", nc) is not None
       and "old.umask = umask(-1)" in wr, "")
    ck("R6b ...an old copy left behind is removed first (and a failure to remove it is 11457), and a failure to create the copy is 11457",
       ordered(wr, "if ospath(tmp, OS$EXISTS) then", "ospath(tmp, OS$DELETE)", "err = 11457", "old.umask = umask(-1)", "if not(made) then", "err = 11457"), "")
    ck("R7 check.record gives every value its shape: remote user of letters, digits and ._- up to MAX.USERNAME.LEN; iterations a whole number inside SCRAM$MIN.ITER and "
       "SCRAM$MAX.ITER; salt and both keys base64 of 4 to 128 characters; the pin 64 lower case hex digits; created yyyy-mm-dd",
       ordered(nc, "check.record:", "chk.set = os.chars", "MAX.USERNAME.LEN", "what matches '1N0N'", "SCRAM$MIN.ITER", "SCRAM$MAX.ITER", "chk.set = b64", "len(what) < 4 or len(what) > 128 or not(chk.ok)",
               "chk.set = hex.set", "len(what) # 64", "'4N\"-\"2N\"-\"2N'") and "b64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':lc.set:digits:'+/='" in nc
       and "hex.set = digits:'abcdef'" in nc and "os.chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':lc.set:digits:'._-'" in nc, "")
    ck("R8 DELETE: no login is 11453; EXISTS: a missing directory or a missing file answers 0 with no error, a file that is there and not trusted is 11454 with 0; an unknown "
       "action is 2018 before anything else",
       ordered(dl, "err = 11453", "SD_FILE_PRIVATE", "err = 11454", "ospath(path, OS$DELETE)", "err = 11457")
       and ordered(nc, "if act # 'READ' and act # 'WRITE' and act # 'DELETE' and act # 'EXISTS' then", "err = 2018", "chk.text = server")
       and "if act = 'EXISTS' then return" in nc and "if act = 'EXISTS' then record = 0" in nc, "")

    # ---- U. set.netlogin ---------------------------------------------------------------------------------------------------------
    ck("U1 set.netlogin is $internal, `program set.netlogin`, catalogued once as $setnetlogin",
       "\n$internal\nprogram set.netlogin" in "\n" + sn and "$catalog $setnetlogin" in sn
       and len([n for n, t in c.items() if n.startswith("bp:") and "$catalog $setnetlogin\n" in t + "\n"]) == 1, "")
    ck("U2 EVERY LOCAL CHECK COMES BEFORE ANY PROMPT OR CONNECTION, in this order: the usage (11450), the server name (11452), the NET gate or the administrator (11460), the "
       "definition (11430, 11436), the account list (11461), the Linux user (11462), sd-elevate netcred-dir (11463), the directory test; and then the two prompts, then the one socket",
       ordered(sn, "stop sysmsg(11450", "stop sysmsg(11452", "is.admin = kernel(K$ADMINISTRATOR, -1)", "stop sysmsg(11460", "call !netdefs('READ'", "stop sysmsg(11430",
               "stop sysmsg(11436", "stop sysmsg(11461", "stop sysmsg(11462", "os.execute elev", "stop sysmsg(11463", "SD_FILE_PRIVATE", "stop sysmsg(11463", "input ru",
               "stop sysmsg(11467", "input pw HIDDEN", "stop sysmsg(11468", "open.socket(")
       and "len(name) < 1 or len(name) > 16 or not(chk.ok) or index(lc.set, name[1, 1], 1) = 0" in sn and sn.count("input ru") == 1 and sn.count("input pw HIDDEN") == 1
       and "if dcount(words, ' ') # 2 then" in sn and "acc = downcase(@who)" in sn and "if len(pin) # 64 or not(chk.ok) then" in sn
       and "if ru = '' or len(ru) > MAX.USERNAME.LEN or not(chk.ok) then" in sn
       and re.search(r"if pw = '' then\s*\n\s*@system\.return\.code = -ER\$ARGS\s*\n\s*stop sysmsg\(11468\)", sn) is not None
       and re.search(r"if not\(is\.admin\) and not\(kernel\(K\$NET, -1\)\) then", sn) is not None and "kernel(K$NET, -1)" in sn and sn.count("kernel(K$NET") == 1
       and "index(',':downcase(defs<found,7>):',', ',':acc:',', 1) = 0" in sn and re.search(r"if not\(is\.admin\) then\s*\n\s*if index\(", sn) is not None, "")
    ck("U3 the Linux user is kernel(K$USERNAME, 0) and nothing else, sdsys, root and an empty one are refused before sd-elevate is run, the helper is run as `sudo -n` "
       "(no password prompt in an SD session), its success line must be `netcred-dir: <path>` and the path must end in /<the Linux user> and pass SD_FILE_PRIVATE as a directory",
       ordered(sn, "lu = kernel(K$USERNAME, 0)", "lu = '' or lu = 'sdsys' or lu = 'root'", "elev = ACCOS$ELEVATE", "'sudo -n '", "os.execute elev : ' netcred-dir 2>&1' capturing out",
               "out<i>[1, 13] = 'netcred-dir: '", "tail = '/' : lu", "cred.path[len(cred.path) - len(tail) + 1, len(tail)] # tail", "SDEXT(cred.path : @FM : 'DIR', @TRUE, SD_FILE_PRIVATE) # '1'")
       and sn.count("os.execute") == 1 and sn.count("kernel(K$USERNAME") == 1 and not re.search(r"@logname", sn), "")
    ck("U4 ONE connection, TLS, to the host and port of the DEFINITION, and the key it presents is tested BEFORE a byte is sent or read: open.socket (once) -> the hash "
       "(socket.info .. SKT$INFO.TLS.SPKI, once, lower case) must be 64 hex digits (11479) -> `spki # pin` gives 11471 through give.up -> only then the Ack read and the first packet",
       sn.count("open.socket(") == 1 and sn.count("socket.info(skt, SKT$INFO.TLS.SPKI)") == 1 and "open.socket(host, port, SKT$BLOCKING + SKT$TLS, config('NETWAIT'))" in sn and "NET.CONNECT.SECS" not in sn
       and ordered(sn, "open.socket(", "spki = downcase(trim(socket.info(skt, SKT$INFO.TLS.SPKI)))", "fail.num = 11479", "if spki # pin then", "fail.num = 11471", "gosub give.up",
                   "read.socket(skt, 1, SKT$BLOCKING, NET.READ.MS)", "ptype = SrvrScramFirst")
       and re.search(r"if spki # pin then\s*\n\s*fail\.num = 11471[^\n]*\n\s*gosub give\.up\s*\n\s*end", sn) is not None
       and "if len(spki) # 64 or not(chk.ok) then" in sn
       and "pin = downcase(defs<found,5>)" in sn and "host = defs<found,2>" in sn and "port = defs<found,3>" in sn, "")
    reads = re.findall(r"(?:read|write)\.socket\([^\n]*\)", sn)
    ck("U4b ...every read and every write of the socket has a timeout (NET.READ.MS), write.socket stands once and only in send.packet, which every packet goes through "
       "and which comes after the pin test in the flow",
       len(reads) == 4 and all("NET.READ.MS)" in x for x in reads) and sn.count("write.socket(") == 1 and sn.count("gosub send.packet") == 2
       and ordered(sn, "if spki # pin then", "gosub send.packet", "gosub send.packet") and "write.socket(" in routine_body(sn, "send.packet"), repr(reads))
    ck("U5 THE SCRAM EXCHANGE as sdclient makes it: client-first is `p=tls-exporter,,` + n= + r=, with the binding read from the socket and required; the server's first "
       "message must keep our nonce and extend it, the iteration count must be a whole number inside SCRAM$MIN.ITER..SCRAM$MAX.ITER, the salt base64 of 4 to 128; the "
       "proof is built from ClientKey over AuthMessage; the server's v= is compared in constant time (SD_CTEQUAL) and a missing or wrong one stops",
       ordered(sn, "cbind = socket.info(skt, SKT$INFO.TLS.CBIND)", "cfirst.bare = 'n=' : ru : ',r=' : cnonce", "pdata = 'p=tls-exporter,,' : cfirst.bare",
               "nonce[1, len(cnonce)] # cnonce or len(nonce) = len(cnonce)", "iter matches '1N0N'","iter < SCRAM$MIN.ITER or iter > SCRAM$MAX.ITER",
               "len(salt) < 4 or len(salt) > 128", "SD_PBKDF2", "pw = ''", "SD_HMACSHA256", "SD_SHA256", "SD_XORBYTES", "pdata = cfinal.bare : ',p=' : proof",
               "in.pkt[1, 2] # 'v='", "SD_CTEQUAL) # '1'", "fail.num = 11475")
       and "if cbind = '' then" in sn and "cfinal.bare = 'c=' : cbind : ',r=' : nonce" in sn and "auth.msg = cfirst.bare : ',' : sfirst : ',' : cfinal.bare" in sn, "")
    pwl = [ln.strip() for ln in sn.split("\n") if re.search(r"\bpw\b", ln)]
    allowed_pw = (r"pw = ''", r"input pw HIDDEN", r"if pw = '' then", r"salted = SDEXT\(pw : @FM : salt : @FM : iter : @FM : SCRAM\$KEY\.LEN, @TRUE, SD_PBKDF2\)")
    ck("U6 THE PASSWORD IS HELD IN ONE VARIABLE AND NOWHERE ELSE: every line that names pw is `pw = ''`, the hidden input, the empty test, or the SD_PBKDF2 call; it is cleared "
       "right after the derivation and in give.up (the only exit of a failure); and the keys the program derived are cleared there too",
       pwl and all(any(re.fullmatch(a, x) for a in allowed_pw) for x in pwl) and ordered(sn, "salted = SDEXT(pw :", "pw = ''", "client.key = SDEXT(salted")
       and "pw = ''" in routine_body(sn, "give.up") and all(v in routine_body(sn, "give.up") for v in ("salted = ''", "client.key = ''", "srvr.key = ''", "expect.v = ''", "proof = ''")),
       repr(pwl))
    leaks = []
    for n, args in sysmsg_calls(sn):
        for a in args:
            if re.search(SECRETS, a):
                leaks.append((n, a))
    for ln in sn.split("\n"):
        if re.search(r"\b(display|crt|print|stop)\b", ln) and re.search(SECRETS, strip_strings(ln)) and "pw = ''" not in ln:
            leaks.append(ln.strip())
        if re.search(r"fail\.a\d = ", ln) and re.search(SECRETS, strip_strings(ln.split("=", 1)[1])):
            leaks.append(ln.strip())
    ck("U7 NO SECRET IS EVER PRINTED: no message, display, crt or fail.a argument names the password, the salted password, a key, the proof, the signature or the AuthMessage",
       not leaks, repr(leaks))
    gu = routine_body(sn, "give.up")
    wr_re = r"\b(writeseq|writeblk|weofseq|oswrite|osdelete|osrename|osopen|openseq|openpath|write|writev|writeu|writet|delete|deleteu|execute|create|createfile|create\.file)\b"
    bare2 = strip_strings(re.sub(r"\b(?:write|open|close|read)\.socket\b|\bos\.execute\b|\b(?:ospath|osrename)\(", "", re.sub(r"^\s*program\s+\S+", "", sn, flags=re.M)))
    ck("U8 NOTHING IS WRITTEN ON ANY FAILURE: the only call of $netcred is WRITE, once, after the server's signature has been verified and the socket closed, and a refusal "
       "from it is the last word; give.up (the exit of every failure) calls nothing that writes and closes the socket; set.netlogin has no statement that writes or deletes a "
       "file at all (only $netcred does) and runs one command (the helper)",
       sn.count("$netcred(") == 1 and sn.count("call $netcred('WRITE', name, rec, pin, err)") == 1
       and ordered(sn, "SD_CTEQUAL) # '1'", "expect.v = ''", "close.socket skt", "call $netcred('WRITE', name, rec, pin, err)", "if err # '' then", "stop sysmsg(err<1,1>", "kernel(K$AUDIT")
       and "netcred" not in gu and "close.socket skt" in gu and "stop sysmsg(fail.num" in gu and not re.search(wr_re, bare2), repr(re.findall(wr_re, bare2)))
    ck("U8b ...every failure goes through give.up (message and stop): no `stop sysmsg(11469..11479` stands anywhere else, and the record handed to $netcred is only the remote "
       "user, the salt, the iteration count and the two keys (attributes 1-5; the pin goes as the argument)",
       not re.search(r"stop sysmsg\(114(?:69|7\d)", sn.replace(gu, "")) and ordered(sn, "rec = ''", "rec<1> = ru", "rec<2> = salt", "rec<3> = iter", "rec<4> = client.key", "rec<5> = srvr.key", "call $netcred('WRITE'")
       and re.search(r"rec = ''\s*\n\s*rec<1> = ru", sn) is not None and not re.search(r"rec<[67]>", sn)
       and re.search(r"fail\.num = 11474 ; fail\.a1 = reason\s*\n\s*gosub give\.up", routine_body(sn, "refused")) is not None, "")
    audits = re.findall(r"kernel\(K\$AUDIT[^\n]*", sn)
    ck("U9 THE AUDIT LINE is one, lower case, after the login is stored: `set.netlogin server=<name> remote=<remote user>` and nothing else - no password, key, hash, salt or pin",
       audits == ["kernel(K$AUDIT, 'set.netlogin server=' : name : ' remote=' : ru)"] and ordered(sn, "call $netcred('WRITE'", "kernel(K$AUDIT"), repr(audits))
    ck("U10 the exit code and the success message: 0 and message 11477 are set together after the audit line, and every refusal sets a failure code before its message",
       ordered(sn, "kernel(K$AUDIT", "@system.return.code = 0", "crt sysmsg(11477, name, ru)", "stop")
       and sn.count("@system.return.code = 0") == 1, "")

    # ---- Y. delete.netlogin ------------------------------------------------------------------------------------------------------
    ck("Y1 delete.netlogin is $internal, `program delete.netlogin`, catalogued once as $deletenetlogin; it validates the name (11452) before $netcred is called, asks EXISTS and "
       "then DELETE (11453 when there is none), audits after the delete and then says 11478",
       "\n$internal\nprogram delete.netlogin" in "\n" + dn and "$catalog $deletenetlogin" in dn
       and len([n for n, t in c.items() if n.startswith("bp:") and "$catalog $deletenetlogin\n" in t + "\n"]) == 1
       and "len(name) < 1 or len(name) > 16 or not(chk.ok) or index(lc.set, name[1, 1], 1) = 0" in dn and "if dcount(words, ' ') # 2 then" in dn
       and ordered(dn, "stop sysmsg(11451", "stop sysmsg(11452", "call $netcred('EXISTS'", "stop sysmsg(11453", "call $netcred('DELETE'", "kernel(K$AUDIT", "crt sysmsg(11478"), "")
    ck("Y2 ...it asks no gate (K$NET, K$ADMINISTRATOR: removing a login adds nothing to what an account may do), prompts for nothing, opens no socket, runs no command, and "
       "has exactly one audit line, `delete.netlogin server=<name>`",
       not re.search(r"K\$NET|K\$ADMINISTRATOR|\binput\b|open\.socket|os\.execute|\$netcred\('(?:READ|WRITE)'", dn)
       and re.findall(r"kernel\(K\$AUDIT[^\n]*", dn) == ["kernel(K$AUDIT, 'delete.netlogin server=' : name)"], "")

    # ---- V. the VOC entries ---------------------------------------------------------------------------------------------------------
    nv = srcs["newvoc.list"].lower().split("\n")
    ck("V1 both verbs are in voc_template as V / CA / $name AND in newvoc (so EVERY account has them: a person needs no administrator to set up a login, the gate and the "
       "list are what limit it) as a description line, CA, $name",
       all(srcs["voc:" + w].split() == ["V", "CA", cat] and w in nv
           and [x for x in srcs["newvoc:" + w].split("\n") if x != ""][1:] == ["CA", cat] and len([x for x in srcs["newvoc:" + w].split("\n") if x != ""]) == 3
           for w, _p, cat in NL_VERBS), "")

    # ---- H. messages 11450-11479 -------------------------------------------------------------------------------------------------------
    nlt = {n: srcs["msg:%d" % n] for n in range(NL_MSG_FIRST, NL_MSG_LAST + 1)}
    ck("H1 messages 11450 to 11479 all exist, each one line, inside the Linux block 11000-11999, and the whole block is this slice's",
       all(t is not None and t.strip() != "" and "\n" not in t.rstrip("\n") for t in nlt.values()) and LINUX_BLOCK[0] <= NL_MSG_FIRST and NL_MSG_LAST <= LINUX_BLOCK[1],
       repr([n for n, t in nlt.items() if not t]))
    prog = nc + "\n" + sn + "\n" + dn
    used2 = {int(x) for x in re.findall(r"\b(114[5-7]\d)\b", prog)}
    ck("H2 every message from 11450 to 11479 is used by $netcred, set.netlogin or delete.netlogin (and none outside the block is invented)",
       set(range(NL_MSG_FIRST, NL_MSG_LAST + 1)) <= used2 and not (used2 - set(range(NL_MSG_FIRST, NL_MSG_LAST + 1))), repr(sorted(set(range(NL_MSG_FIRST, NL_MSG_LAST + 1)) - used2)))
    short2 = []
    for n, args in sysmsg_calls(sn + "\n" + dn):
        t = srcs.get("msg:%d" % n)
        if t is None or not (NL_MSG_FIRST <= n <= NL_MSG_LAST):
            continue
        top = max([int(x) for x in re.findall(r"%(\d)", t)] or [0])
        if len(args) != top:
            short2.append((n, len(args), top))
    for n, a in fail_places(sn):
        top = max([int(x) for x in re.findall(r"%(\d)", srcs.get("msg:%d" % n) or "")] or [0])
        if a != top:
            short2.append(("fail.num", n, a, top))
    for n, a in err_places(nc):
        t = srcs.get("msg:%d" % n)
        if t is None or not (NL_MSG_FIRST <= n <= NL_MSG_LAST):
            continue
        top = max([int(x) for x in re.findall(r"%(\d)", t)] or [0])
        if a != top:
            short2.append(("err", n, a, top))
    ck("H3 each message a program gives has as many arguments as the message has %n places: the sysmsg calls, the fail.aK of every failure, and the err of $netcred",
       not short2 and len(fail_places(sn)) >= 10 and len(err_places(nc)) >= 12, repr(short2))
    g_ = lambda n: nlt.get(n) or ""
    ck("H4 the wording the users rely on: the password is said not to be stored (11464, 11477); every failure after the pin says nothing was stored, and the ones before any "
       "byte was sent say nothing was sent (11469, 11470, 11471, 11479); 11460 names net-on in lower case; 11455 tells the person to run set.netlogin again; 11454 says nothing was used",
       "not stored" in g_(11464) and "not stored" in g_(11477) and all("Nothing was sent or stored" in g_(n) or "nothing was stored" in g_(n) for n in (11469, 11470, 11471, 11479))
       and "Nothing was sent to it" in g_(11471) and all("Nothing was stored" in g_(n) for n in (11472, 11473, 11474, 11475, 11476))
       and "net-on" in g_(11460) and "Run set.netlogin %1 again" in g_(11455) and "Nothing was used" in g_(11454)
       and g_(11450).strip() == "Usage: set.netlogin server" and g_(11451).strip() == "Usage: delete.netlogin server", "")

    # ---- E. the root agrees with sd-elevate, and the sudoers line is exactly one command -----------------------------------------
    se, sdo = c["sd-elevate"], c["sdcore.sudoers"]
    ck("E1 /var/lib/sd-net is the root in $netcred and in sd-elevate netcred-dir (SD_NET_ROOT_REAL), and the verb is `netcred-dir` in the usage, the case and the helper's success line",
       "SD_NET_ROOT_REAL=/var/lib/sd-net" in se and "/var/lib/sd-net" in nc and re.search(r"netcred-dir\)", se) is not None and "netcred-dir: " in se, "")
    sline = next((ln for ln in sdo.split("\n") if ln.startswith("%sdusers") and "NOPASSWD:" in ln), "")
    cmds = [x.strip() for x in sline.split("NOPASSWD:", 1)[1].split(",")] if sline else []
    ck("E2 the sudoers line gives %sdusers exactly `/usr/local/sbin/sd-elevate netcred-dir` for it - no wildcard, no argument after it - and nothing else for netcred-dir",
       [x for x in cmds if "netcred-dir" in x] == ["/usr/local/sbin/sd-elevate netcred-dir"] and sdo.count("netcred-dir") >= 1
       and not re.search(r"netcred-dir\s*\*", sdo), repr(cmds))


# ---- W. S.65 slice 2c: the files-only route -----------------------------------------------------------------------------------------------
# The request numbers a files-only session may make, WRITTEN OUT HERE from the owner's list and not read from the program: 1 quit, 2 get error text,
# 4 open, 5 close, 6-10 the reads, 11 select, 12 readnext, 13 clearselect, 14 readlist, 15 release, 16-19 write / writeu / delete / deleteu, 26
# selectindex (a select, so allowed), 30-34 the locks, 35-36 indices, 37-39 the select lists, 40 fileinfo, 41 readv, 42-45 the left / right pair,
# 46 mark mapping, 49 revision.  3 (set account) is allowed ONCE and is not in this tuple.  Everything else - 0, 20-25, 27-29, 47, 48, 50 and
# up - is refused.
FILES_ALLOWED = (1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 26,
                 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 49,
                 68, 69, 70, 71)         # 21 Oct 26, S.73 item 3: the administration set (the table now holds 41 numbers)


def files_ok_table(text):
    """What apifilesok builds: the string it starts from (files.ok = '..') and the pieces appended to it (files.ok := '..')."""
    m = re.search(r"^files\.ok = '([^']*)'[ \t]*$", text, re.M)
    return (m.group(1) if m else None), re.findall(r"^files\.ok := '([^']*)'[ \t]*$", text, re.M)


def files_ok_model(allow, action, entered):
    """What !apifilesok answers, run in Python on the table read from its source: empty is 0, not a number is 0, 3 is 0 once entered and 1
    before, anything else is 1 only if ',N,' is in the table.  (The source is held to exactly these tests, in this order, by W2.)"""
    if action == "":
        return 0
    if not re.fullmatch(r"[+-]?(?:\d+\.?\d*|\.\d+)", action):
        return 0
    if float(action) == 3:
        return 0 if entered else 1
    return 1 if ("," + action + ",") in allow else 0


def want_files_ok(n, entered):
    if n == 3:
        return 0 if entered else 1
    return 1 if n in FILES_ALLOWED else 0


def checks_2c(srcs, c, ck):
    """S.65 slice 2c: the files-only route, the group sdfiles."""
    fo, ap = c["apifilesok"], c["apisrvr"]
    mo, cr, ca2, ai, rs = c["modifya"], c["createa"], c["create_account"], c["acc_os_info"], c["restorea"]
    inst, dele, se = c["installsdcore.sh"], c["deletesdcore.sh"], c["sd-elevate"]
    bps = {n[3:]: t for n, t in c.items() if n.startswith("bp:")}

    # ---- W1-W3. !apifilesok -----------------------------------------------------------------------------------------------------------
    init, parts = files_ok_table(fo)
    allow = (init or "") + "".join(parts)
    nums = [int(x) for p in parts for x in p.split(",") if x != ""]
    wrong = [(e, n, files_ok_model(allow, str(n), e), want_files_ok(n, e)) for e in (0, 1) for n in range(0, 81)
             if files_ok_model(allow, str(n), e) != want_files_ok(n, e)]
    ck("W1 !apifilesok, the table read from its source and run for EVERY request number 0 to 80, the account entered and not, agrees with the list "
       "written out in this file (a number wrong in either direction fails); the table holds exactly those 41 numbers once each (the 37 of S.65 and the four of S.73 item 3), 3 is NOT in it "
       "(it is allowed once, by its own test) and the table starts from ','",
       init == "," and not wrong and sorted(nums) == sorted(FILES_ALLOWED) and 3 not in nums and len(FILES_ALLOWED) == 41, repr((init, wrong[:6], sorted(set(nums) ^ set(FILES_ALLOWED)))))
    odd = [a for a in ("", "abc", "-1", "1000", "81", "72", "4x", "x4", "3x") if files_ok_model(allow, a, 0) or files_ok_model(allow, a, 1)]   # 72, not 70: 70 is a request since S.73 item 3
    ck("W2 ...and the tests after the table are exactly these, in this order: an empty action is 0, a non-number is 0, 3 is 0 when entered and 1 before, "
       "a number is 0 unless ',N,' (commas on both sides, so 4 cannot match 49 or 14) is in the table, then (18 Oct 26, the write group) a login whose writeok is not exactly 1 "
       "is refused the change set and everything else is allowed (the model above is run with the write group, the table's own answer)",
       not odd and re.search(r"if action = '' then return 0\s*\n\s*if not\(num\(action\)\) then return 0\s*\n\s*if action = 3 then\s*\n\s*if entered then return 0\s*\n"
                             r"\s*return 1\s*\n\s*end\s*\n\s*if not\(index\(files\.ok, ',' : action : ',', 1\)\) then return 0\s*\n"
                             r"\s*if writeok # 1 then\s*\n\s*if index\(files\.chg, ',' : action : ',', 1\) then return 0\s*\n\s*end\s*\n"
                             r"\s*if index\(files\.adm, ',' : action : ',', 1\) then\s*\n\s*if writeok # 1 then return 0\s*\n\s*if adminok # 1 then return 0\s*\n\s*end\s*\n\s*return 1\s*\n\s*end\s*$", fo) is not None
       and ordered(fo, "files.ok := ", "if action = '' then return 0"), repr(odd))
    ck("W3 ...it is a $internal function catalogued once as !apifilesok, and it is PURE: no read, no write, no open, no kernel call, no execute, no prompt - "
       "a sandbox asks it about every number and the server asks it about every request",
       "$internal" in fo and re.search(r"^function apifilesok\(action, entered, writeok, adminok\)\s*$", fo, re.M) is not None and re.search(r"^\$catalog !apifilesok\s*$", fo, re.M) is not None
       and len([n for n, t in bps.items() if "$catalog !apifilesok" in t]) == 1
       and not re.search(r"\b(?:kernel|read|readv|readu|readt|open|openseq|openpath|write|writeu|writev|writeseq|delete|execute|os\.execute|select|readnext|input|crt|display|print|call|gosub|goto|void)\b", strip_strings(fo)), "")

    # ---- W4-W12. apisrvr -------------------------------------------------------------------------------------------------------------
    cm_i = ap.find("common /$APISRVR/")
    cm = ap[cm_i:ap.find("seq.unbuf(SEQ.MAX)", cm_i)] if cm_i >= 0 else ""
    fi = ap.find("\nvb.scram.final:")
    fin = ap[fi:] if fi >= 0 else ""
    ck("W4 apisrvr declares !apifilesok, keeps the files-only mark in the COMMON block /$APISRVR/ (a plain variable is set afresh by a runtime abort "
       "while logged.in survives it, which would hand a files-only login the whole API) and starts it false ONCE, in the first-time block beside master.login.done",
       re.search(r"^deffun apifilesok\(action, entered, writeok, adminok\) calling '!apifilesok'\s*$", ap, re.M) is not None and re.search(r"^files\.only,", cm, re.M) is not None
       and ap.count("files.only = @false") == 1
       and ordered(ap, "if not(kernel(K$CPROC.LEVEL,0)) then", "master.login.done = @false", "files.only = @false", 'openpath "voc" to voc else'), "")
    others = [n for n, t in bps.items() if n != "apisrvr" and re.search(r"\bfiles\.only\b", t)]
    ck("W5 the mark is SET ONCE and NEVER CLEARED: exactly two assignments to files.only in the whole tree (the initialisation and the one `= @true`), the true one "
       "inside `if api.files.login then`, in vb.scram.final after K$ASSUME.USER and before logged.in, and no other program mentions it",
       len(re.findall(r"\bfiles\.only\s*=(?!=)", ap)) == 2 and ap.count("files.only = @true") == 1 and not others
       and re.search(r"if api\.files\.login then\s*\n\s*files\.only = @true\s*\n", fin) is not None
       and ordered(fin, "kernel(K$ASSUME.USER, scram.user)", "if api.files.login then", "files.only = @true", "logged.in = @true"), repr(others))
    ck("W6 THE ORDER OF THE ROUTE: sdusers first, then sdapi, then sdfiles, then the identity is assumed, then the mark - each group read ONCE, by scram.user (the name "
       "just proven)",
       ordered(fin, "is_grp_member(scram.user, 'sdusers')", "is_grp_member(scram.user, 'sdapi')", "is_grp_member(scram.user, 'sdfiles')", "kernel(K$ASSUME.USER, scram.user)",
               "files.only = @true", "logged.in = @true")
       and all(fin.count("is_grp_member(scram.user, '%s')" % g_) == 1 for g_ in ("sdusers", "sdapi", "sdfiles"))
       and ap.count("is_grp_member(scram.user, 'sdfiles')") == 1, "")
    ck("W7 sdapi is tried first and WINS: the sdfiles read is inside `if not(api.in.sdapi) then`, api.files.login starts false before it and is set true only after the "
       "sdfiles test passed (once in the tree)",
       ordered(fin, "api.files.login = @false", "api.in.sdapi = is_grp_member(scram.user, 'sdapi')", "if not(api.in.sdapi) then", "api.in.sdfiles = is_grp_member(scram.user, 'sdfiles')",
               "if not(api.in.sdfiles) then", "api.files.login = @true")
       and ap.count("api.files.login = @true") == 1 and ap.count("api.files.login = @false") == 1, "")
    ck("W8 SDSYS IS EXEMPT BY NAME from both groups (one test, downcased, round the reading of both, before the first of them)",
       re.search(r"if not\(downcase\(scram\.user\) = 'sdsys'\) then\s*\n\s*api\.in\.sdapi = is_grp_member", fin) is not None
       and ordered(fin, "if not(downcase(scram.user) = 'sdsys') then", "api.in.sdapi = is_grp_member", "api.in.sdfiles = is_grp_member", "api.files.login = @true", "logged.in = @true"), "")
    ck("W9 BOTH groups are read with the three-valued status and neither is collapsed: a lookup that could not answer refuses (10073) with its own reason, for sdapi and for sdfiles",
       re.search(r"api\.in\.sdapi = is_grp_member\(scram\.user, 'sdapi'\)\s*\n\s*api\.route\.stat = status\(\)\s*\n\s*if api\.route\.stat # 0 then\s*\n"
                 r"\s*scram\.refuse\.reason = 'the sdapi route could not be read, status ' : api\.route\.stat\s*\n\s*abort\.message = sysmsg\(10073, scram\.user\)\s*\n"
                 r"\s*server\.error = SV\$ON\.ERROR\s*\n\s*goto exit\.vb\.scram\.fail", fin) is not None
       and re.search(r"api\.in\.sdfiles = is_grp_member\(scram\.user, 'sdfiles'\)\s*\n\s*api\.files\.stat = status\(\)\s*\n\s*if api\.files\.stat # 0 then\s*\n"
                     r"\s*scram\.refuse\.reason = 'the sdfiles route could not be read, status ' : api\.files\.stat\s*\n\s*abort\.message = sysmsg\(10073, scram\.user\)\s*\n"
                     r"\s*server\.error = SV\$ON\.ERROR\s*\n\s*goto exit\.vb\.scram\.fail", fin) is not None, "")
    ck("W10 a user in NEITHER group is refused with the same message 10073 and the same exit as before, and the audit reason NAMES BOTH ROUTES ('not a member of sdapi or sdfiles': "
       "19 Oct 26, K3 - the route code decides on both groups, so the reason that named only sdapi sent the administrator looking for the wrong one); and a user not in sdusers "
       "is still refused first with 5009",
       re.search(r"if not\(api\.in\.sdfiles\) then\s*\n\s*scram\.refuse\.reason = 'not a member of sdapi or sdfiles'\s*\n\s*abort\.message = sysmsg\(10073, scram\.user\)\s*\n"
                 r"\s*server\.error = SV\$ON\.ERROR\s*\n\s*goto exit\.vb\.scram\.fail", fin) is not None
       and re.search(r"if not\(is_grp_member\(scram\.user, 'sdusers'\)\) then\s*\n\s*scram\.refuse\.reason = 'not a member of sdusers'\s*\n\s*abort\.message = sysmsg\(5009\)", fin) is not None, "")
    gi = ap.find("if files.only then")
    gb = ap[gi:ap.find("cproc.date = date()", gi)] if gi >= 0 else ""
    nl_ = ap.find("abort.message = sysmsg(5270)")
    dsp = ap.find("on action + 1 gosub")
    ck("W11 THE GATE: one `if files.only then`, after the not-logged-in test (5270) and BEFORE cproc.date and the dispatch table, so no request goes round it; "
       "it asks !apifilesok with master.login.done as `entered`; a refusal is audited, is an error answer (SV$ON.ERROR), says 11480 with the request number, and "
       "goes to return.status.set - the reply is written and the dispatch is skipped",
       ap.count("if files.only then") == 1 and 0 <= nl_ < gi < ap.find("cproc.date = date()") < dsp
       and "if not(apifilesok(action, master.login.done, files.write, files.admin)) then" in gb
       and re.search(r"void kernel\(K\$AUDIT, 'api refused request=' : action : ' route=sdfiles write=' : write\.word : ' admin=' : admin\.word : ' user=' : @logname\)", gb) is not None
       and ordered(gb, "kernel(K$AUDIT", "server.error = SV$ON.ERROR", "abort.message = sysmsg(11480, action)", "st = status()", "goto return.status.set")
       and ap.count("apifilesok(") == 5 and "\nreturn.status.set:" in ap and ap.find("\nreturn.status.set:") > dsp, "")
    ck("W12 'entered' is real: master.login.done is set true exactly once, at the first successful entry (vb.account), after the first-time `if not(master.login.done)` "
       "tests; a request 3 is therefore allowed until then and refused after; and the audit words are lower case: api login route=sdfiles user=, api refused request=",
       ap.count("master.login.done = @true") == 1 and ordered(ap, "if not(master.login.done) then\n   void kernel(K$VOC.EDIT", "master.login.done = @true")
       and "void kernel(K$AUDIT, 'api login route=sdfiles write=' : write.word : ' admin=' : admin.word : ' user=' : scram.user)" in fin and "'api refused request='" in ap, "")

    # ---- W13-W15. the messages ---------------------------------------------------------------------------------------------------------
    m80, m82 = srcs.get("msg:11480"), srcs.get("msg:11482")
    cited = {}
    for n_, t_ in bps.items():
        for num_, args_ in sysmsg_calls(t_):
            if 11480 <= num_ <= 11489:
                cited.setdefault(num_, []).append((n_, len(args_)))
    stray = sorted({int(x) for t_ in bps.values() for x in re.findall(r"\b(1148\d)\b", t_)} - {11480, 11482})
    ck("W13 message 11480 and 11482 exist, one line each, inside the Linux block, with the wording the logins and the verbs rely on: 11480 'This login is for files only: request %1 "
       "is not allowed', 11482 'Account %1 has files %2' (lower case since 19 Oct 26, K2: a keyword SD prints is lower case, and its sibling 11522 already was)",
       m80 is not None and m82 is not None and m80.strip() == "This login is for files only: request %1 is not allowed" and m82.strip() == "Account %1 has files %2"
       and "\n" not in m80.rstrip("\n") and "\n" not in m82.rstrip("\n") and LINUX_BLOCK[0] <= 11480 <= 11489 <= LINUX_BLOCK[1], repr((m80, m82)))
    ck("W14 11480 is cited only by apisrvr with ONE argument (the request number); 11482 only by MODIFY.ACCOUNT and CREATE.ACCOUNT with TWO (the account, yes or no); "
       "no program cites 11481 or 11483 to 11489, or writes such a number any other way (the block 11480-11489 is this slice's and only 11480 and 11482 are used)",
       sorted(cited.get(11480, [])) == [("apisrvr", 1)] and sorted(cited.get(11482, [])) == [("create_account", 2), ("modifya", 2)] and set(cited) <= {11480, 11482} and not stray, repr((cited, stray)))
    ck("W15 nothing is said on a successful files-only login: the login path prints nothing in vb.scram.final (no crt, display or print between the mark and logged.in)",
       not re.search(r"\b(?:crt|display|print)\b", fin[fin.find("if api.files.login then"):fin.find("logged.in = @true", fin.find("if api.files.login then"))]), "")

    # ---- W16-W22. the words: MODIFY.ACCOUNT, CREATE.ACCOUNT, CREATEA ----------------------------------------------------------------------
    sf = routine_body(mo, "set.files")
    cgf = routine_body(mo, "change.files.group")        # 19 Oct 26, K4a: the one place set.files changes a group
    ck("W16 MODIFY.ACCOUNT: FILES-ON and FILES-OFF are words (files.want true / false, set.files, stop), in the syntax lines and in the list of words; sdapi and sdssh are not "
       "touched by set.files",
       all(re.search(r"case action = '%s'\s*\n\s*files\.grp = 'sdfiles'\s*\n\s*files\.want = @%s\s*\n\s*gosub set\.files\s*\n\s*return" % (w, b), mo) for w, b in (("FILES-ON", "true"), ("FILES-OFF", "false")))
       and "modify.account <account> files-on | files-off" in mo and "files-on, files-off, files-write-on, files-write-off, files-admin-on, files-admin-off, ai-on, ai-off, suspended or unsuspended" in mo
       and sf != "" and "sdapi" not in sf and "sdssh" not in sf, "")
    ck("W17 set.files refuses what has no Linux user BEFORE it runs anything: a group account (10087) and any other account that is not sdu_ (10081, status 2), then the "
       "name is checked with valid_os_name; the Linux user is the one the account's group names (the manifest reads the same)",
       ordered(sf, "if group.name[1,4] # 'sdu_' then", "sysmsg(10087, acc.name)", "sysmsg(10081, acc.name, 2)", "files.user = group.name[5,999]", "valid_os_name(files.user)", "gosub change.files.group")
       and sf.count("os.execute") == 0 and cgf.count("os.execute") == 2, "")      # 19 Oct 26 (K4a): set.files runs nothing itself; change.files.group does the addgroup and the delgroup
    ck("W18 ...membership is read three-valued (status read at once, a lookup that cannot answer changes NOTHING and says 10081 with the status); FILES-ON also needs sdusers "
       "(else status 2 - the login would refuse them first); FILES-OFF is never gated on sdusers",
       # 21 Oct 26 (S.73 item 3): the membership is read in read.files.groups (the three groups, each three-valued: test-fileswrite-units.py F11 holds that routine); set.files tests its status at once
       re.search(r"gosub read\.files\.groups\s*\n\s*if files\.stat = 0 and files\.want then\s*\n"
                 r"\s*in\.sdusers = is_grp_member\(files\.user, 'sdusers'\)\s*\n\s*files\.stat = status\(\)\s*\n\s*if files\.stat = 0 and not\(in\.sdusers\) then files\.stat = 2\s*\n"
                 r"\s*end\s*\n\s*if files\.stat # 0 then\s*\n\s*@system\.return\.code = -ER\$FAILED\s*\n\s*crt sysmsg\(10081, acc\.name, files\.stat\)\s*\n\s*return", sf) is not None
       and ordered(sf, "if files.stat # 0 then", "nothing.to.do = (has.target = files.want)", "if nothing.to.do then", "sysmsg(10080, acc.name)", "gosub change.files.group")
       and re.search(r"^read\.files\.groups:\s*\n\s*has\.files = is_grp_member\(files\.user, 'sdfiles'\)\s*\n\s*files\.stat = status\(\)", mo, re.M) is not None, "")
    ck("W19 ...already in the wanted state is 10080 and nothing is run; FILES-ON when the group sdfiles does not exist is 10024 and nothing is run; the change is the SAME "
       "helper and verbs the api word uses (sd-elevate addgroup / delgroup <user> sdfiles), in change.files.group",
       ordered(sf, "if nothing.to.do then", "sysmsg(10080, acc.name)", "return", "files.found = is_group(files.grp)", "sysmsg(10024, files.grp)", "gosub change.files.group")
       and re.search(r'os\.execute "sudo /usr/local/sbin/sd-elevate addgroup " : files\.user : " " : cg\.group', cgf) is not None
       and re.search(r'os\.execute "sudo /usr/local/sbin/sd-elevate delgroup " : files\.user : " " : cg\.group', cgf) is not None
       and ordered(cgf, "if cg.want then", 'addgroup " : files.user', "end else", 'delgroup " : files.user'), "")
    ck("W20 ...after EVERY change the membership is READ BACK from /etc/group (change.files.group), a read back that does not show the wanted state is a failure (10081, status 2), "
       "the audit line (lower case) comes only after it, and the line printed (11482) is the read-back value (cg.now copied into now.files) and not the request",
       ordered(cgf, "files.stat = OS.ERROR()", "if files.stat = 0 then", "cg.now = is_grp_member(files.user, cg.group)", "files.stat = status()", "if files.stat = 0 and cg.now # cg.want then files.stat = 2")
       and re.search(r"gosub change\.files\.group\s*\n\s*now\.files = cg\.now\s*\n\s*end\s*\n\s*if files\.stat # 0 then\s*\n\s*@system\.return\.code = -ER\$FAILED\s*\n"
                     # 19 Oct 26 (finish 2): when the write group HAS gone and the step after it failed, the failure path says what happened first - the audit line for THE REMOVAL
                     # (files-write-off, never the action asked for) and the write group's line - and only then the failure (10081)
                     # 21 Oct 26 (S.73 item 3): the failure path's removals are ONE routine, report.removals (audit line and state line of every group above that went: test-fileswrite-units.py F11)
                     r"\s*(?:\*[^\n]*\n\s*)*gosub report\.removals\s*\n"
                     r"\s*crt sysmsg\(10081, acc\.name, files\.stat\)\s*\n\s*return\s*\n\s*end\s*\n\s*@system\.return\.code = 0\s*\n"
                     r"\s*void kernel\(K\$AUDIT, 'modify\.account ' : downcase\(action\) : ' account=' : acc\.name\)\s*\n"
                     r"\s*if admin\.removed then gosub admin\.removed\.line[^\n]*\n"
                     r"\s*begin case\s*\n\s*case files\.grp = 'sdfilesadmin'\s*\n\s*crt sysmsg\(11525, acc\.name, if now\.files then 'yes' else 'no'\)[^\n]*\n"
                     r"\s*case files\.grp = 'sdfileswrite'\s*\n\s*crt sysmsg\(11522, acc\.name, if now\.files then 'yes' else 'no'\)[^\n]*\n"
                     r"\s*case 1\s*\n"
                     r"\s*if write\.removed then gosub write\.removed\.line[^\n]*\n"
                     r"\s*crt sysmsg\(11482, acc\.name, if now\.files then 'yes' else 'no'\)", sf) is not None
       and re.search(r"^write\.removed\.line:\s*\n\s*crt sysmsg\(11522, acc\.name, if now\.write then 'yes' else 'no'\)[^\n]*\n\s*return\s*$", mo, re.M) is not None
       and mo.count("modify.account files-write-off account=") == 1
       # 21 Oct 26 (S.73 item 3): report.removals says the removals that happened, top down - the administration group's audit line and state line, then the write group's
       and re.search(r"^report\.removals:\s*\n\s*if admin\.removed then\s*\n\s*void kernel\(K\$AUDIT, 'modify\.account files-admin-off account=' : acc\.name\)\s*\n\s*gosub admin\.removed\.line\s*\n"
                     r"\s*end\s*\n\s*if write\.removed then\s*\n\s*void kernel\(K\$AUDIT, 'modify\.account files-write-off account=' : acc\.name\)\s*\n\s*gosub write\.removed\.line\s*\n\s*end\s*\n\s*return",
                     mo, re.M) is not None, "")
    ck("W21 CREATEA: the word FILES-ON sets CA$FILES = 1 (and nothing sets it to anything else), the syntax line names {files-on} and the text says what it is",
       re.search(r"case upcase\(token\) = 'FILES-ON'\s*\n\s*settings<CA\$FILES> = 1\s*\n", cr) is not None and len(re.findall(r"(?<!if )settings<CA\$FILES>\s*=", cr)) == 1
       and "{net-on} {files-on} {files-write-on} {files-admin-on} {ai-on} {no.query}" in cr and "files-only login (files-on" in cr, "")
    ck("W21b createacc.h defines CA$FILES as 36 right after CA$NET 35 (the compiler warns 'not assigned a value' and reads 0 errors without it: test-includes-units.py), "
       "and no register field is added - the membership of the group IS the state",
       re.search(r"\$define\s+CA\$FILES\s+36\b", c["createacc.h"]) is not None and re.search(r"\$define\s+CA\$NET\s+35\b", c["createacc.h"]) is not None
       and "ACC$FILES" not in c["syscom/keys.h"],
       "createacc.h has no  $define CA$FILES 36")
    ck("W22 CREATE.ACCOUNT: a request is exactly CA$FILES = 1; the group is looked for BEFORE the Linux user is made (a missing group is 10024 and creates nothing, an unreadable "
       "/etc/group is 10081); a GROUP account (10087) and an OTHER account (10081, status 2) are refused before anything is created",
       "files.want = (settings<CA$FILES> = 1)" in ca2
       # 21 Oct 26 (S.73 item 3): the look-up of a files group is the internal subroutine check.files.group (10081 when the lookup cannot answer, 10024 when the group is not there); the call for sdfiles
       # is made before the Linux user is made (test-fileswrite-units.py F12 holds the routine and the three calls)
       and re.search(r"if files\.want then\s*\n\s*files\.grp\.name = 'sdfiles'\s*\n\s*gosub check\.files\.group\s*\n\s*if files\.bad then goto exit\.create", ca2) is not None
       and ordered(ca2, "files.grp.name = 'sdfiles'", "gosub check.files.group", "if not(create_user(acc.uname)) then")
       and re.search(r"^check\.files\.group:\s*\n\s*files\.bad = @false\s*\n\s*files\.found = is_group\(files\.grp\.name\)\s*\n\s*files\.stat = status\(\)\s*\n\s*if files\.stat # 0 then\s*\n"
                     r"\s*@system\.return\.code = -ER\$FAILED\s*\n\s*err = 10081:@vm:acc\.uname:@vm:files\.stat[^\n]*\n\s*files\.bad = @true\s*\n\s*end else\s*\n"
                     r"\s*if not\(files\.found\) then\s*\n\s*@system\.return\.code = -ER\$FAILED\s*\n\s*err = 10024:@vm:files\.grp\.name", ca2, re.M) is not None
       and re.search(r"case acc\.type = 'GROUP'.*?if files\.want or files\.write\.want or files\.admin\.want or ai\.want then\s*\n\s*@system\.return\.code = -ER\$ARGS\s*\n\s*err = 10087:@vm:acc\.name\s*\n\s*goto exit\.create.*?case acc\.type = 'OTHER'.*?"
                     r"if files\.want or files\.write\.want or files\.admin\.want or ai\.want then\s*\n\s*@system\.return\.code = -ER\$ARGS\s*\n\s*err = 10081:@vm:acc\.name:@vm:2\s*\n\s*goto exit\.create", ca2.replace('"', "'"), re.S) is not None, "")
    ck("W23 ...the join is sd-elevate addgroup <user> sdfiles, only when asked, AFTER the sdssh and sdapi joins; a failed join is 10081 with its status and the account stops; "
       "and a user account is told its state (11482), read off /etc/group, right after the NET line",
       # 21 Oct 26 (S.73 item 3): the join is the internal subroutine join.files.group (sd-elevate addgroup <user> <group>, 10081 with its status), called for sdfiles after the sdssh and sdapi joins
       re.search(r'if files\.want then\s*\n\s*files\.grp\.name = \'sdfiles\'\s*\n\s*gosub join\.files\.group\s*\n\s*if route\.stat # 0 then goto exit\.create', ca2) is not None
       and re.search(r'^join\.files\.group:\s*\n\s*os\.execute "sudo /usr/local/sbin/sd-elevate addgroup ":acc\.uname:" ":files\.grp\.name\s*\n\s*route\.stat = OS\.ERROR\(\)\s*\n\s*if route\.stat # 0 then\s*\n'
                     r'\s*@system\.return\.code = -ER\$FAILED\s*\n\s*err = 10081:@vm:acc\.uname:@vm:route\.stat', ca2, re.M) is not None
       and ordered(ca2, 'addgroup ":acc.uname:" sdssh"', 'addgroup ":acc.uname:" sdapi"', "files.grp.name = 'sdfiles'", "gosub join.files.group")
       and re.search(r"crt sysmsg\(11411, acc\.name, acc\.rec<ACC\$NET>\)[^\n]*\n(?:\s*crt sysmsg\(11515, acc\.name, acc\.rec<ACC\$SHARED\.READ>, acc\.rec<ACC\$SHARED\.WRITE>\)[^\n]*\n)?\s*crt sysmsg\(11482, acc\.name, if is_grp_member\(acc\.uname, 'sdfiles'\) then 'yes' else 'no'\)", ca2) is not None, "")

    # ---- W24-W26. the manifest and the restore -------------------------------------------------------------------------------------------
    ck("W24 the account manifest carries `route.files: 1|0` for a USER account, read from membership of sdfiles, after route.api and before os.sh, and before the GROUP branch; "
       "the key is NOT `files` - the backup writes `files: N` (the file count) into the same section and RESTORE.ACCOUNT reads it as that count",
       ordered(ai, "'route.api: '", "'route.files: ':(if is_grp_member(user, 'sdfiles') then 1 else 0)", "'route.files.write: '", "'os.sh: '", "case grp[1,4] = 'sdg_'")
       and "'files: '" not in ai and ai.count("'route.files: '") == 1 and ai.count("route.files") == 3 and "'files: ':files" in c["bp:backupa"] and re.search(r"= 'files'\s*; m\.files = kv", rs) is not None, "")
    ck("W25 RESTORE.ACCOUNT reads route.files, clears it for each section, hands it on as CA$FILES (a manifest without the key restores as NOT in the group), and still reads "
       "`files` as the count",
       re.search(r"= 'route\.files'\s*; m\.route\.files = kv", rs) is not None and "settings<CA$FILES> = m.route.files" in rs and "m.net = '' ; m.route.files = ''" in rs
       and re.search(r"= 'files'\s*; m\.files = kv", rs) is not None, "")

    # ---- W26-W28. the group: installer, deletesdcore, sd-elevate ----------------------------------------------------------------------------
    ck("W26 the installer makes sdfiles (and, 18 Oct 26, sdfileswrite; 21 Oct 26, sdfilesadmin) beside sdssh and sdapi: one loop `for sd_route_group in sdssh sdapi sdfiles sdfileswrite sdfilesadmin`, groupadd --system, only when the group is missing",
       inst.count("for sd_route_group in") == 1
       and re.search(r'for sd_route_group in sdssh sdapi sdfiles sdfileswrite sdfilesadmin sdaiusers; do\s*\n\s*if ! getent group "\$sd_route_group" &>/dev/null; then\s*\n(?:[^\n]*\n){0,2}?\s*sudo groupadd --system "\$sd_route_group"', inst) is not None, "")
    li = dele.find("for sd_route_group in sdssh sdapi sdfiles sdfileswrite sdfilesadmin sdaiusers; do")
    br = dele.rfind('if [ "$keep_accts" = "DELETE" ]; then', 0, li) if li >= 0 else -1
    el = dele.find("\nelse\n", li) if li >= 0 else -1
    fi_ = dele.find("\nfi", el) if el >= 0 else -1
    ck("W27 deletesdcore removes it with the others ONLY on a full DELETE (the loop and its groupdel inside the DELETE branch, no end of branch between them) and says it kept it "
       "when the accounts are kept (in the else branch)",
       dele.count("for sd_route_group in") == 1 and 0 <= br < li < el and "\nfi" not in dele[br:li] and 'sudo groupdel "$sd_route_group"' in dele[li:el]
       and "route groups sdssh, sdapi, sdfiles, sdfileswrite, sdfilesadmin and sdaiusers were kept" in dele[el:el + 200] and fi_ > el and "groupdel" not in dele[el:fi_], "")
    ck("W28 sd-elevate whitelists sdfiles by its exact name for addgroup, delgroup and groupadd (require_sd_group), says so in its refusal text, and never deletes it with groupdel "
       "(it is one of the system groups)",
       re.search(r"case \$group in\s*\n\s*sdusers\|sdssh\|sdapi\|sdfiles\|sdfileswrite\|sdfilesadmin\|sdaiusers\) : ;;\s*\n\s*sdu_\?\*\|sdg_\?\*\) : ;;", se) is not None
       and "(want sdusers, sdssh, sdapi, sdfiles, sdfileswrite, sdfilesadmin, sdaiusers, sdu_*, or sdg_*)" in se
       and re.search(r"case \$1 in\s*\n\s*sdusers\|sdssh\|sdapi\|sdfiles\|sdfileswrite\|sdfilesadmin\|sdaiusers\)\s*\n\s*die \"'\$1' is one of SD's system groups and is never deleted here\"", se) is not None
       and "sdfiles*" not in se, "")


# ---- Z. S.65 slice 3a: gpl.bp/sdclient logs in from the stored derived keys -------------------------------------------------------------------

# Every error text sandbox-netfile.py asserts of the class, written out here once: each must be in sdclient AND in the suite, so that a text changed in
# one and not the other is found by a free check and not by a red row in a suite that takes minutes.
CLIENT_TEXTS = ("A connection has already been established", "Invalid host name", "Invalid user name", "Invalid public key pin",
                "The stored login is incomplete", "The stored iteration count is not a whole number", "The stored iteration count is unacceptable",
                "PIN MISMATCH: the public key of", "is not the key pinned in its definition; nothing was sent",
                "No acknowledgement from", "at the start of the session", "during the login (the connection failed or timed out)",
                "Server signature did not verify", "Server did not return a signature",
                "Server nonce does not extend the client nonce", "Malformed server-first message", "Server sent a non-numeric iteration count",
                "Server asked for an unacceptable iteration count", "The TLS handshake with ", " did not complete (status ", "Cannot connect to ",
                "The server's salt is not the stored one: the stored login is out of date or this is not the server it was made with",
                "The server's iteration count is not the stored one: the stored login is out of date or this is not the server it was made with")


def between(text, start, end):
    i = text.find(start)
    j = text.find(end, i + 1) if i >= 0 else -1
    return text[i:j] if i >= 0 and j >= 0 else ""


def checks_3a(srcs, c, ck):
    """S.65 slice 3a: connect.keys, scram.exchange, settimeout and the wiring of the netfile suite."""
    sc = c["bp:sdclient"]
    raw = srcs["bp:sdclient"]
    kb = between(sc, "public function connect.keys(", "public subroutine settimeout(")
    cb = between(sc, "public function connect(host", "public function connect.keys(")
    ex = between(sc, "local function scram.exchange(", "local function evaluate.packet(")
    rp = between(sc, "local function read.packet()", "local subroutine disconnect.session")
    pre_pin = kb[:kb.find("('p' : spki)")] if "('p' : spki)" in kb else kb
    keys_branch = between(ex, "if keys.mode then", "end else")

    # ---- Z1. the shape
    ck("Z1 connect.keys is a public function, once, whose secret parameters are BY VALUE (port, salt, iterations, client.key, server.key, pin: the copies are cleared here and the "
       "caller's variables are the caller's); settimeout is a public subroutine; the class lists both in its description",
       sc.count("public function connect.keys(host, (port), username, (salt), (iterations), (client.key), (server.key), account, (pin))") == 1
       and sc.count("public subroutine settimeout(ms)") == 1 and "bool = obj->connect.keys(host, port, username, salt, iterations, client.key, server.key, account, pin)" in raw
       and "obj->settimeout(ms)" in raw, "")

    # ---- Z2. the order
    ck("Z2 connect.keys, in this ORDER: a connected object refused, the host, the user name, the pin's shape, an incomplete login, the count a whole number and within the bounds, the "
       "one open.socket, the key hash, the pin compared, the Ack read, the exchange, the account entered, the context set last",
       ordered(kb, "context # CX.DISCONNECTED", "len(host) = 0", "valid_os_name(username)", "pin = downcase(trim(pin))", "'The stored login is incomplete'",
               "iterations matches '1N0N'", "iterations < SCRAM$MIN.ITER or iterations > SCRAM$MAX.ITER", "open.socket(", "socket.info(skt, SKT$INFO.TLS.SPKI)",
               "('p' : spki) # ('p' : pin)", "read.socket(skt, 1, SKT$BLOCKING, io.ms)", "scram.exchange(username, '', salt, iterations, client.key, server.key)",
               "message.pair(SrvrAccount, account)", "server.error # SV$OK", "context = CX.CONNECTED"), "")
    ck("Z2a ...each shape check refuses with ITS OWN text and returns false (a connected object, an empty host, a user name !valid_os_name refuses, a pin that is not 64 hex digits, "
       "a login with ANY of salt, ClientKey and ServerKey null, a count that is not 1 to 8 digits, a count outside the bounds)",
       all(re.search(p, kb) is not None for p in (
           r"if context # CX\.DISCONNECTED then\s*\n\s*error = 'A connection has already been established'\s*\n\s*return @false",
           r"if len\(host\) = 0 then\s*\n\s*error = 'Invalid host name'\s*\n\s*return @false",
           r"if not\(valid_os_name\(username\)\) then\s*\n\s*error = 'Invalid user name'\s*\n\s*return @false",
           r"if len\(pin\) # 64 or len\(convert\('0123456789abcdef', '', pin\)\) # 0 then\s*\n\s*error = 'Invalid public key pin'\s*\n\s*return @false",
           r"if salt = '' or client\.key = '' or server\.key = '' then\s*\n\s*error = 'The stored login is incomplete'\s*\n\s*return @false",
           r"if len\(iterations\) < 1 or len\(iterations\) > 8 or not\(iterations matches '1N0N'\) then\s*\n\s*error = 'The stored iteration count is not a whole number'\s*\n\s*return @false",
           r"if iterations < SCRAM\$MIN\.ITER or iterations > SCRAM\$MAX\.ITER then\s*\n\s*error = 'The stored iteration count is unacceptable'\s*\n\s*return @false")), "")
    ck("Z3 ...the shape checks are all BEFORE the socket is opened (no network is touched for a bad argument), the socket is opened once, with SKT$TLS and the NETWAIT connect timeout "
       "(5 seconds by default, from the configuration since 19 Oct 26)",
       kb.count("open.socket(") == 1 and re.search(r"skt = open\.socket\(host, port, SKT\$BLOCKING \+ SKT\$TLS, config\('NETWAIT'\)\)", kb) is not None and "NET.CONNECT.SECS" not in kb
       and not re.search(r"socket|SDEXT|message\.pair", kb[:kb.find("open.socket(")]), "")
    ck("Z4 ...NOTHING IS SENT BEFORE THE PIN IS CHECKED: between the open and the comparison of the key hash there is no write, no read, no packet, no exchange and no disconnect "
       "(the only thing done is SOCKET.INFO); the comparison is of TEXT - each side has a letter in front, because two all-digit strings would be compared as numbers - and a mismatch "
       "and a missing hash both leave through keys.fail, naming a PIN MISMATCH and saying nothing was sent",
       "('p' : spki)" in kb and not re.search(r"write\.packet|write\.socket|message\.pair|read\.socket|read\.packet|scram\.|disconnect|SrvrQuit|SDEXT", pre_pin)
       and re.search(r"if \('p' : spki\) # \('p' : pin\) then\s*\n\s*error = 'PIN MISMATCH: the public key of ' : host : ':' : port : ' is not the key pinned in its definition; nothing was sent'\s*\n\s*goto keys\.fail\s*\n\s*end", kb) is not None
       and re.search(r"if spki = '' then\s*\n\s*error = '[^']*nothing was sent'\s*\n\s*goto keys\.fail", kb) is not None
       and not re.search(r"if spki # pin|if pin # spki", kb), "")
    ck("Z5 ...the Ack is awaited with the BOUNDED read (io.ms, a byte at a time, a limited number of tries), and the exchange is entered only after it; connect.keys sets the bound to "
       "NETREPLY seconds (30 by default, from the configuration since 19 Oct 26) only when it is still 0, so that settimeout() called first wins",
       re.search(r"if io\.ms = 0 then io\.ms = config\('NETREPLY'\) \* 1000", kb) is not None and "NET.READ.MS" not in kb
       and ordered(kb, "if io.ms = 0 then io.ms = config('NETREPLY') * 1000", "tries += 1", "read.socket(skt, 1, SKT$BLOCKING, io.ms)",
                                                                                         "until acked or tries >= NET.ACK.TRIES", "scram.exchange(") and kb.count("read.socket(") == 1, "")
    ck("Z6 ...the keys are dropped the moment the exchange has returned (client.key and server.key set to null before the result is tested), and on EVERY failure path through keys.fail, which "
       "also closes the socket and returns false; every failure after the open goes through it; a refusal of the account fails the call",
       ordered(kb, "ok = scram.exchange(", "client.key = ''", "server.key = ''", "if not(ok) then")
       and re.search(r"\nkeys\.fail:\s*\n\s*client\.key = ''\s*\n\s*server\.key = ''\s*\n\s*close\.socket skt\s*\n\s*return @false\s*\nend", kb) is not None
       and len(re.findall(r"goto keys\.fail", kb)) == 7 and kb[kb.find("spki = downcase"):].count("return @false") == 1
       and re.search(r"if server\.error # SV\$OK then\s*\n\s*error = 'The server did not enter the account'\s*\n\s*goto keys\.fail", kb) is not None, "")

    # ---- Z7-Z9. the exchange, shared by both logins
    ck("Z7 scram.exchange in the stored-key mode (keys.mode: a stored ClientKey was given): AFTER client-first and BEFORE client-final, the server's salt is compared with the stored one "
       "as TEXT and its count as a NUMBER with the stored count, each mismatch ending the exchange with its own text and the stored keys dropped; the nonce and the iteration bounds are "
       "tested before either; the stored keys become the working keys only after both compares",
       ordered(ex, "keys.mode = (stored.ck # '')", "message.pair(SrvrScramFirst", "nonce[1,len(cnonce)] # cnonce", "iter < SCRAM$MIN.ITER or iter > SCRAM$MAX.ITER", "if keys.mode then",
               "if ('s' : salt) # ('s' : stored.salt) then", "if iter + 0 # stored.iter + 0 then", "client.key = stored.ck", "srvr.key = stored.sk", "end else", "message.pair(SrvrScramFinal")
       and "stored." not in re.sub(r"keys\.mode = \(stored\.ck # ''\)", "", ex[ex.find("keys.mode = (stored.ck"):ex.find("message.pair(SrvrScramFirst")]) and "keys.mode" not in ex[:ex.find("keys.mode = (")]
       and re.search(r"if \('s' : salt\) # \('s' : stored\.salt\) then\s*\n\s*error = \"The server's salt is not the stored one[^\"]*\"\s*\n\s*stored\.ck = '' ; stored\.sk = ''\s*\n\s*return @false\s*\n\s*end", ex) is not None
       and re.search(r"if iter \+ 0 # stored\.iter \+ 0 then\s*\n\s*error = \"The server's iteration count is not the stored one[^\"]*\"\s*\n\s*stored\.ck = '' ; stored\.sk = ''\s*\n\s*return @false\s*\n\s*end", ex) is not None, "")
    ck("Z8 ...PBKDF2 (the password) is used only in the password branch: once in the whole exchange, after the stored-key branch, and the stored-key branch uses no SDEXT of it; the proof "
       "and the server's signature are computed from client.key and srvr.key either way, and the working keys, the stored key and the client signature are dropped before the final message "
       "is sent; the server's v= is compared in constant time",
       ex.count("SD_PBKDF2") == 1 and "SD_PBKDF2" not in keys_branch and ex.find("SD_PBKDF2") > ex.find("end else")
       and ordered(ex, "stored.key = SDEXT(client.key", "client.sig = SDEXT(", "proof = SDEXT(", "expect.v = SDEXT(srvr.key", "client.key = ''", "srvr.key = ''", "stored.key = ''", "client.sig = ''",
                   "message.pair(SrvrScramFinal", "in.pkt[1,2] # 'v='", "SD_CTEQUAL") and "stored.ck" not in ex[ex.find("end else"):], "")
    ck("Z9 scram.login is the ONE LINE `return scram.exchange(username, password, '', '', '', '')` and nothing else (a null stored ClientKey is the password mode), declared once; connect() "
       "calls it and calls neither connect.keys nor scram.exchange",
       re.search(r"local function scram\.login\(username, password\)\s*\n\s*return scram\.exchange\(username, password, '', '', '', ''\)\s*\nend", sc) is not None
       and sc.count("local function scram.login(") == 1 and sc.count("deffun scram.login(username, password) local") == 1
       and sc.count("deffun scram.exchange(username, password, stored.salt, stored.iter, stored.ck, stored.sk) local") == 1
       and cb.count("scram.login(username, password)") == 1 and "scram.exchange" not in cb and "connect.keys" not in cb, "")

    # ---- Z10. connect() is the same kind of function it was
    ck("Z10 connect() is UNCHANGED IN KIND: its Ack wait still reads with the timeout 0 (it waits for ever, as before), its socket is still opened with no timeout argument, it enters the "
       "account as before (no check of the reply), and it asks no pin",
       "read.socket(skt, 1, SKT$BLOCKING, 0) = char(6)" in cb and re.search(r"skt = open\.socket\(host, port, SKT\$BLOCKING \+ SKT\$TLS\)\s*\n", cb) is not None
       and "io.ms" not in cb and "SPKI" not in cb and re.search(r"\bpin\b", cb) is None and ordered(cb, "scram.login(username, password)", "message.pair(SrvrAccount, account)", "context = CX.CONNECTED"), "")
    ck("Z11 the bounded read: read.packet reads the header and the data with io.ms (both of its read.socket calls, and no literal 0 timeout is left in it); create.object starts io.ms at 0 so "
       "that connect() still waits for ever; settimeout accepts only a number of 0 or more (it aborts 'Illegal timeout') and sets io.ms; io.ms is a private variable",
       len(re.findall(r"read\.socket\(skt, n, SKT\$BLOCKING, io\.ms\)", rp)) == 2 and not re.search(r"read\.socket\([^)]*, 0\)", rp)
       and re.search(r"public subroutine create\.object\s*\n(?:[^\n]*\n){0,6}?\s*io\.ms = 0\s*\n(?:\s*(?:quiet|LastError|LastText|maxpacket) = [^\n]*\n){0,4}end", sc) is not None      # slice 3e: quiet, LastError, LastText after it; 19 Oct 26 (K8c): maxpacket
       and re.search(r"public subroutine settimeout\(ms\)\s*\n\s*if not\(num\(ms\)\) or ms < 0 then abort 'Illegal timeout'\s*\n\s*io\.ms = ms \+ 0\s*\nend", sc) is not None
       and re.search(r"private context,[^\n]*\n(?:[^\n]*\n){0,4}?\s*io\.ms\b", sc) is not None, "")
    dv = {m.group(1): int(m.group(2)) for m in re.finditer(r"\$define (NET\.[A-Z.]+)\s+(\d+)", sc)}
    ck("Z12 the one define left in the class: NET.ACK.TRIES 16 (the connect timeout 5 and the read wait 30 are the configuration parameters NETWAIT and NETREPLY since 19 Oct 26, K8d)",
       dv == {"NET.ACK.TRIES": 16}, repr(dv))

    # ---- Z13. nothing secret in a message
    leak = [ln.strip() for ln in strip_strings(sc).split("\n") if re.search(r"\berror\s*=", ln) and re.search(
        r"\b(client\.key|server\.key|stored\.ck|stored\.sk|srvr\.key|salted|proof|stored\.key|expect\.v|auth\.msg|client\.sig|cbind|cnonce)\b", ln)]
    shown = [ln.strip() for ln in (kb + "\n" + ex).split("\n") if re.search(r"\b(display|crt|print)\b", ln)]
    ck("Z13 no error text carries a key, a proof, a signature or the binding (no `error =` line names one), and neither connect.keys nor scram.exchange displays anything",
       not leak and not shown, repr((leak[:3], shown[:3])))

    # ---- Z14. every text the suite asserts is the class's, and the suite is wired in
    suite = srcs["sandbox-netfile.py"]
    miss = [t for t in CLIENT_TEXTS if t not in raw or t not in suite]
    ck("Z14 every error text sandbox-netfile.py asserts of the class (%d of them) is in sdclient and in the suite, word for word" % len(CLIENT_TEXTS), not miss, repr(miss[:4]))
    al = re.search(r'^ALL_SUITES="([^"]*)"', c["regress.sh"], re.M)
    names = al.group(1).split() if al else []
    rm = c["regress-map.txt"]
    ck("Z15 the suite is wired in: `netfile` is in regress.sh's ALL_SUITES once, gplbld/sandbox-netfile.py is its own suite in the map, and the map selects it for sdclient, netdefs, netcred, "
       "setnetlogin and netfake.py; the suite file prints the verdict line regress.sh reads and builds with --build",
       names.count("netfile") == 1 and re.search(r"^gplbld/sandbox-netfile\.py\s*:\s*@self\s*$", rm, re.M) is not None
       and all(re.search(r"^%s\s*:[^\n]*\bnetfile\b" % re.escape(p), rm, re.M) is not None
               for p in ("sdsys/gpl.bp/sdclient", "sdsys/gpl.bp/netdefs", "sdsys/gpl.bp/netcred", "sdsys/gpl.bp/setnetlogin", "gplbld/netfake.py"))
       and 'say("sandbox-netfile: %d passed, %d failed" % (passed, failed))' in suite and '"--build" in sys.argv' in suite, repr(names[-3:]))
    ck("Z16 the dated history lines are there: sdclient (`17 Oct 26 dm S.65 slice 3a`), and the suite's own",
       "17 Oct 26 dm S.65 slice 3a" in raw and "17 Oct 26 dm  New.  S.65 slice 3a" in suite, "")


# ---- N. S.65 slice 3b: gpl.bp/netfile, the handler for every operation on a remote file ---------------------------------------------------------

NF_OPS = {"NF$OPEN": 1, "NF$CLOSE": 2, "NF$READ": 3, "NF$READV": 4, "NF$RECORDLOCKED": 5, "NF$SELECT": 6, "NF$FILEINFO": 7, "NF$CLOSEALL": 8,
          "NF$WRITE": 9, "NF$DELETE": 10, "NF$CLEARFILE": 11, "NF$LOCK": 12, "NF$STATE": 13,
          "NF$WRITEU": 14, "NF$DELETEU": 15, "NF$RELEASE": 16,                                    # slice 3e: 14 to 16
          "NF$FILELOCK": 18, "NF$FILEUNLOCK": 19,                                                # S.72: 18 and 19; 17 is not used
          "NF$ADMIN": 20, "NF$CREATEFILE": 21, "NF$FCONTROL": 22, "NF$SEQKEY": 23,                # S.73 item 3 (21 Oct 26): 20 to 23
          "NF$INDEXQ": 24}                                                                      # S.73 item 3 D1 (21 Oct 26): the index query statements
NF_DEFS = dict(NF_OPS, **{"NF$RC.OK": 0, "NF$RC.ELSE": 2, "NF$RC.ERROR": 3, "NF$RC.LOCKED": 4, "NF$MAX.SERVERS": 10, "NF$MAX.HANDLES": 100})
NF_OPS_BY_NAME = {k: v for k, v in NF_OPS.items() if k not in ("NF$FILELOCK", "NF$FILEUNLOCK", "NF$ADMIN", "NF$CREATEFILE", "NF$FCONTROL", "NF$SEQKEY", "NF$INDEXQ")}      # the suite's driver names these 16; 18 to 24 it drives by number (the RAW line)
NF_REASONS = ("gate", "server", "list", "credential", "limit", "file")
# the methods and properties of the class the handler uses; slice 3e added the changing and locking ones and the two properties of the quiet object
NF_METHODS = {"connect.keys", "settimeout", "open", "close", "read", "select", "readlist", "recordlocked", "disconnect", "error", "ServerStatus",
              "write", "writeu", "delete", "deleteu", "recordlock", "release", "clearfile", "quiet", "LastError", "LastText", "maxpacket",      # LastText: 19 Oct 26, K1 (on.error.text); maxpacket: K8c
              "filelock", "fileunlock",                                                                                                          # S.72
              "fileadmin", "fcontrol", "writeseqkey", "writeuseqkey",                                                                            # S.73 item 3
              "indices", "selectindexv", "selectindexk", "setleft", "setright", "selectleft", "selectright"}                                      # S.73 item 3 D1
NF_REQUEST_METHODS = ("open", "close", "read", "select", "readlist", "recordlocked", "write", "writeu", "delete", "deleteu", "recordlock", "release", "clearfile",
                      "filelock", "fileunlock", "fileadmin", "fcontrol", "writeseqkey", "writeuseqkey",      # S.72: 15 + 2 = 17 request sites; S.73 item 3: four more (fileadmin twice: act.admin and act.createfile)
                      "indices", "selectindexv", "selectindexk", "setleft", "setright", "selectleft", "selectright")      # S.73 item 3 D1: eight more (the eight arms of act.indexq, and its second readlist)
NF_SECRET_LOCALS = r"\b(cred|ruser|rsalt|riter|rck|rsk|pin|pw|password)\b"
NF_SUITE_SECTIONS = ("handler", "readonly", "refuse", "lost", "timeout", "hwrite", "kwrite", "gaps")      # slice 3e: hwrite and kwrite
NF_FORBIDDEN = (r"(?<![\w.$])(write|writeu|writev|writevu|writeseq|writeblk|weofseq|delete|deleteu|deleteseq|create|openseq|openpath|osrename|osdelete|"
                r"execute|perform|sh|logto|clearfile|recordlock|release|mkdir|chdir)(?![\w.$])")


def checks_3b(srcs, c, ck):
    """S.65 slice 3b: the handler $netfile, as ORDER and as what it cannot do.  Nothing here runs it: the sections handler, readonly, refuse, lost and
    timeout of sandbox-netfile.py do, against the fake server."""
    nf, nfh, raw, rawh = c["bp:netfile"], c["bp:netfile.h"], srcs["bp:netfile"], srcs["bp:netfile.h"]
    suite, rm = srcs["sandbox-netfile.py"], c["regress-map.txt"]
    ns = strip_strings(nf)
    main = nf[:nf.find("\nact.open:")] if "\nact.open:" in nf else nf
    body = {lab: routine_body(nf, lab) for lab in ("act.open", "act.close", "act.read", "act.recordlocked", "act.select", "act.fileinfo", "act.closeall", "act.refuse",
                                                   "act.state", "get.handle", "check.gate", "check.id", "connect.new", "shape.names", "after.rq", "lost.fail", "drop.conn",
                                                   "refuse", "fail", "idle.release", "act.change", "act.release", "release.every", "mode.now", "audit.once", "server.fail",
                                                   "check.id.chg", "check.id.shape", "rc.locked", "request.limits", "act.fileunlock",
                                                   "check.server", "act.createfile", "act.admin", "act.fcontrol", "act.seqkey", "admin.prepare", "admin.outcome",
                                                   "act.indexq")}   # S.73 item 3; act.indexq: its D1
    ao, gh = body["act.open"], body["get.handle"]
    # 21 Oct 26 (S.73 item 3): the checks of NF$OPEN that need no network are the routine check.server, which act.open calls right after the name shapes (NF$CREATEFILE asks it too).  The rows that
    # hold their ORDER read act.open with that routine's body put where the call is.
    cs_body = re.sub(r"\n\s*return\s*$", "", re.sub(r"^check\.server:\s*\n", "", body["check.server"].rstrip()))
    ao = re.sub(r"gosub check\.server\s*\n\s*if failed then return", lambda _m: cs_body, ao, count=1)

    # ---- N1. the numbers the kernel slice will mirror
    got = {m.group(1): int(m.group(2)) for m in re.finditer(r"\$define\s+(NF\$[A-Z.]+)\s+(-?\d+)", nfh)}
    ck("NF1 netfile.h: the 23 operation codes are 1 to 13 in this order (OPEN CLOSE READ READV RECORDLOCKED SELECT FILEINFO CLOSEALL WRITE DELETE CLEARFILE LOCK STATE), since slice 3e WRITEU 14, "
       "DELETEU 15 and RELEASE 16, since S.72 FILELOCK 18 and FILEUNLOCK 19, since S.73 item 3 ADMIN 20, CREATEFILE 21, FCONTROL 22 and SEQKEY 23, and since its D1 INDEXQ 24 (17 is not used), the results are NF$RC.OK 0, ELSE 2, ERROR 3 and LOCKED 4, the limits are 10 servers and 100 files, "
       "and no name or number is defined twice (the kernel mirrors these in C)",
       got == NF_DEFS and len(re.findall(r"\$define\s+NF\$", nfh)) == len(NF_DEFS) and len(set(got[k] for k in NF_OPS)) == 23
       and not any(v in (17,) for v in got.values()) and got.get("NF$FILELOCK") == 18 and got.get("NF$FILEUNLOCK") == 19 and got.get("NF$ADMIN") == 20 and got.get("NF$SEQKEY") == 23
       and got.get("NF$INDEXQ") == 24,
       repr({k: v for k, v in got.items() if NF_DEFS.get(k) != v}))
    ck("NF2 netfile is an internal subroutine `netfile(op, a, b, c, out, rc)` catalogued as $netfile (only an internal program can call a dollar name), and includes netfile.h",
       re.match(r"\s*\$internal\s*\nsubroutine netfile\(op, a, b, c, out, rc\)\s*\n\$catalog \$netfile\s*\n", nf) is not None and "$include netfile.h" in nf
       and nf.count("$catalog") == 1 and nf.count("subroutine ") == 1, "")

    # ---- N3. the order of the checks on NF$OPEN, every one before anything is dialled
    ai = ao.find("void kernel(K$AUDIT, 'netfile open server='")
    pre = ao[:ai] if ai >= 0 else ao
    ck("NF3 NF$OPEN, in this ORDER: the name shapes (no side effect), THE GATE (administrator or K$NET), the definition read (!netdefs READ) and its fields, the accounts list (the administrator "
       "exempt), the stored login ($netcred READ), the limits (10 servers, 100 files), the file name - then the audit line, and only then the connection and the open",
       ordered(ao, "gosub shape.names", "gosub check.gate", "call !netdefs('READ'", "gosub check.def", "if not(is.admin) then", "index(',':downcase(accts):','", "call $netcred('READ'",
               "gosub find.slot", "ns >= NF$MAX.SERVERS", "nh >= NF$MAX.HANDLES", "if not(fname.ok) then", "void kernel(K$AUDIT, 'netfile open server='", "gosub connect.new", "obj->open(fname)"), "")
    ck("NF3a ...NOTHING IS DIALLED BEFORE THE AUDIT LINE: before it there is no connect.new, no object(), no connect.keys and no `->` call of the class",
       ai >= 0 and not re.search(r"connect\.new|object\(|connect\.keys|->", pre), repr(re.findall(r"connect\.new|object\(|connect\.keys|->[\w.]+", pre)))
    ck("NF3b ...every refusal of NF$OPEN is `gosub refuse` followed by a return (six reasons: gate, server, list, credential, limit, file - each used), the reason a literal word, and the audit "
       "names the server only as the lower cased name that passed its shape test or the word invalid, never the bytes typed",
       len(re.findall(r"gosub refuse\s*\n\s*return", ao)) == ao.count("gosub refuse") >= 8
       and sorted(set(re.findall(r"refused\.why = '(\w+)'", ao))) == sorted(NF_REASONS)
       and re.search(r"safe = 'invalid'\s*\n\s*if name\.ok then safe = srv", ao) is not None
       and ordered(body["refuse"], "gosub fail", "void kernel(K$AUDIT, 'netfile refused server=' : safe : ' reason=' : refused.why)"), "")
    ck("NF3c ...the administrator is exempt from the accounts list but from nothing else the gate asks (the list test is inside `if not(is.admin)`), and the account compared is the lower cased @who",
       re.search(r"if not\(is\.admin\) then\s*\n\s*if index\(',':downcase\(accts\):',', ',':acc:',', 1\) = 0 then", ao) is not None and "acc = downcase(@who)" in main, "")

    # ---- N4. the one way to the network
    cn = body["connect.new"]
    ck("NF4 the network is reached in ONE place: object('!sdclient') once and obj->connect.keys once, both in connect.new, which has NO password login (no ->connect, no open.socket or any socket "
       "verb of its own, no SDEXT), and connect.new is called from act.open and (S.73 item 3) act.createfile only",
       nf.count("object('!sdclient')") == 1 and nf.count("connect.keys(") == 1 and "object('!sdclient')" in cn and "obj->connect.keys(" in cn
       and not re.search(r"->connect\(|open\.socket|read\.socket|write\.socket|SDEXT", nf) and nf.count("gosub connect.new") == 2 and "gosub connect.new" in ao
       and "gosub connect.new" in body["act.createfile"], "")
    ck("NF4a connect.new copies the five values out of the credential, CLEARS the credential before the object is made, calls connect.keys with them and the definition's host, port, remote "
       "account and pin, clears each copy at once, sets the 30 second read bound, and only then puts the object in common (and refuses if it did not stay an object)",
       ordered(cn, "ruser = cred<1>", "rsalt = cred<2>", "riter = cred<3>", "rck = cred<4>", "rsk = cred<5>", "cred = ''", "obj = object('!sdclient')",
               "obj->connect.keys(host, port, ruser, rsalt, riter, rck, rsk, racct, pin)", "ruser = ''", "rsalt = ''", "riter = ''", "rck = ''", "rsk = ''",
               "gosub request.limits", "obj->settimeout(req.ms)", "nf.s.obj(slot) = obj", "vartype(nf.s.obj(slot)) # V$OBJ"), "")
    meth = set(re.findall(r"->([A-Za-z.]+)", nf))
    ck("NF4b the handler calls only these methods and properties of the class: connect.keys, settimeout, open, close, read, select, readlist, recordlocked, disconnect, error, ServerStatus and, "
       "since slice 3e, write, writeu, delete, deleteu, recordlock, release, clearfile, quiet and LastError, since 19 Oct 26 LastText and maxpacket, since S.72 filelock and fileunlock, and since S.73 item 3 D1 indices, selectindexv, selectindexk, setleft, setright, selectleft and selectright (no readu or readl, execute, call, logto, sequential-file, readv or password login method; "
       "the changing ones are NOT in the list for any other reason: NF5 holds where they may stand)", meth <= NF_METHODS and {"filelock", "fileunlock", "indices", "selectindexv", "selectindexk", "setleft", "setright", "selectleft", "selectright"} <= meth,
       repr(sorted(meth - NF_METHODS)))

    # ---- N5. nothing is written to the remote server, nothing is stored
    own = re.sub(r"->[\w.]+", "", ns)
    ac, ar, arl = body["act.change"], body["act.refuse"], body["act.release"]
    writers = re.findall(r"obj->(write|writeu|delete|deleteu|recordlock|clearfile)\(", nf)
    ck("NF5 WHAT THE HANDLER MAY CHANGE (slice 3e; it was READ ONLY before): no statement of netfile itself writes, deletes, creates, opens a file or runs a command; the six changing and locking methods of "
       "the class (write, writeu, delete, deleteu, recordlock, clearfile) are called ONCE EACH and only inside act.change, release only inside act.release and release.every, and since S.72 filelock ONCE, only "
       "inside act.change and with the literal @false as its wait flag (the server is never made to block), and fileunlock ONCE, only inside act.fileunlock; $netcred is called with 'READ' "
       "only and !netdefs with 'READ' only (act.open and mode.now); kernel() is called for K$AUDIT, and for K$ADMINISTRATOR and K$NET with -1 only; nothing is shown (no crt, print or display)",
       not re.search(NF_FORBIDDEN, own, re.I) and re.findall(r"call \$netcred\('(\w+)'", nf) == ["READ"] and re.findall(r"call !netdefs\('(\w+)'", nf) == ["READ", "READ"]
       and sorted(writers) == sorted(["write", "writeu", "delete", "deleteu", "recordlock", "clearfile"]) and all(re.search(r"obj->%s\(" % w, ac) for w in set(writers))
       and not re.search(r"obj->(write|writeu|delete|deleteu|recordlock|clearfile)\(", nf.replace(ac, ""))
       and len(re.findall(r"obj->release\(", nf)) == 2 and "obj->release(" in arl and "obj->release(" in body["release.every"] and "obj->release(" not in ac
       and len(re.findall(r"obj->filelock\(", nf)) == 1 and re.search(r"obj->filelock\(nf\.h\.fno\(hx\), @false\)", ac) is not None and "obj->filelock(" not in nf.replace(ac, "")
       and len(re.findall(r"obj->fileunlock\(", nf)) == 1 and "obj->fileunlock(" in body["act.fileunlock"] and "obj->fileunlock(" not in nf.replace(body["act.fileunlock"], "")
       and all(m.group(1) == "K$AUDIT" or (m.group(1) in ("K$ADMINISTRATOR", "K$NET") and m.group(2).strip() == "-1") for m in re.finditer(r"kernel\((K\$[A-Z.]+)\s*,\s*([^)\n]*)", nf))
       and not re.search(r"(?<![\w.$])(crt|print|display)(?![\w.$])", ns), repr((re.findall(NF_FORBIDDEN, own, re.I)[:4], writers)))
    ck("NF5a act.refuse (the refusal of a change or lock on a READ-MODE handle, 11501 naming the server and the operation) touches no object, no connection and no request (the word obj is not in "
       "it); act.change reaches it as its FIRST test after the handle of this account is found (get.handle without the gate or the connection, a lost handle will do), before the gate and the connection "
       "are asked, before the definition is re-read and before any object is named; the dispatch sends the six operations and, since S.72, FILELOCK to act.change, RELEASE to act.release and FILEUNLOCK to act.fileunlock",
       re.search(r"case op = NF\$WRITE or op = NF\$WRITEU or op = NF\$DELETE or op = NF\$DELETEU or op = NF\$CLEARFILE or op = NF\$LOCK or op = NF\$FILELOCK\s*\n\s*gosub act\.change", main) is not None
       and re.search(r"case op = NF\$RELEASE\s*;?\s*gosub act\.release", main) is not None
       and re.search(r"case op = NF\$FILEUNLOCK\s*;?\s*gosub act\.fileunlock", main) is not None
       and ordered(ar, "fail.num = 11501", "fail.a1 = srvname", "fail.a2 = opname", "gosub fail") and not re.search(r"\bobj\b|nf\.s\.obj|nf\.s\.state|connect|requests", ar)
       and ordered(ac, "need.gate = @false ; need.conn = @false ; any.acct = @false ; allow.lost = @true", "gosub get.handle", "if failed then return", "if nf.h.mode(hx) # 'write' then",
                   "gosub act.refuse", "return", "need.gate = @true ; need.conn = @true ; any.acct = @false ; allow.lost = @false", "gosub get.handle", "gosub mode.now")
       and not re.search(r"\bobj\b|nf\.s\.obj", ac[:ac.find("need.gate = @true")]), "")

    # ---- N6. the gate is asked by the handler itself, and only asked
    cg = body["check.gate"]
    ck("NF6 the handler asks the gate ITSELF (an internal program is exempt from the kernel's): check.gate is `is.admin = kernel(K$ADMINISTRATOR, -1)` and `kernel(K$NET, -1)` and nothing else, "
       "it is the only place either is mentioned, and it is gosubbed from NF$OPEN first of all and from get.handle",
       "is.admin = kernel(K$ADMINISTRATOR, -1)" in cg and re.search(r"if not\(is\.admin\) and not\(kernel\(K\$NET, -1\)\) then gate\.ok = @false", cg) is not None
       and nf.count("kernel(K$NET") == 1 and nf.count("kernel(K$ADMINISTRATOR") == 1 and nf.count("gosub check.gate") == 2, "")
    ck("NF6a ...every operation that sends a request asks it again through get.handle (need.gate = @true in read, readv, select and fileinfo as the FIRST thing they do; in recordlocked, since S.72b, in its "
       "SECOND get.handle - its first is the lost-handle-will-do one of the mode refusal, S72r, like act.fileunlock's), the gate test comes BEFORE the test that "
       "the handle belongs to this account, and a handle belongs to the account that opened it (stored lower case, compared with the lower cased @who)",
       all(re.match(r"act\.[a-z]+:\s*\n\s*need\.gate = @true", body[l]) for l in ("act.read", "act.select", "act.fileinfo"))
       and ordered(body["act.recordlocked"], "gosub act.refuse", "need.gate = @true ; need.conn = @true ; any.acct = @false ; allow.lost = @false", "gosub get.handle", "gosub check.id", "obj->recordlocked(")
       and ordered(gh, "if need.gate then", "gosub check.gate", "fail.num = 11460", "if not(any.acct) then", "nf.h.acct(hx) # acc", "fail.num = 11494")
       and "nf.h.acct(hx) = acc" in ao, repr(body["act.recordlocked"][:130]))

    # ---- N7. a request, a lost connection and no retry
    lines = [ln for ln in nf.split("\n") if ln.strip()]
    req_rx = re.compile(r"obj->(%s)\(" % "|".join(NF_REQUEST_METHODS))
    reqs = [(i, m) for i, ln in enumerate(lines) for m in [req_rx.search(ln)] if m]
    # the mark may stand on the request's own line, BEFORE the call (S.73 item 3 D1: the eight arms of act.indexq are `case what = n ; obj->ServerStatus = NF$NOREPLY ; res = obj->...`)
    unmarked = [lines[i].strip() for i, m in reqs if not any("obj->ServerStatus = NF$NOREPLY" in p for p in lines[max(0, i - 3):i] + [lines[i][:m.start()]])]
    ck("NF7 EVERY request is preceded by the 'no reply' mark (obj->ServerStatus = NF$NOREPLY, three lines before at most): %d request sites (open, close, read, select, readlist, recordlocked and, since "
       "slice 3e, write, writeu, delete, deleteu, recordlock, clearfile and release twice, since S.72 filelock and fileunlock, since S.73 item 3 fileadmin twice, fcontrol and writeseqkey / writeuseqkey, and since its D1 the eight arms of act.indexq and its second readlist), none unmarked (the mark of an act.indexq arm is on the arm's own line, before the call) - the CLEARFILE and fileadmin ones have settimeout(clear.ms) BEFORE the mark lines; a reply of any kind "
       "overwrites it, so after.rq reads a mark still in place as a lost connection (rq.lost = ServerStatus = NF$NOREPLY: NOT a sign test, a changing request can be answered with -3023), and NF$NOREPLY is -2000000001, a value no STATUS() takes (18 Oct 26)" % len(reqs),
       len(reqs) == 31 and not unmarked and "st = obj->ServerStatus" in body["after.rq"] and "rq.lost = (st = NF$NOREPLY)" in body["after.rq"]
       and re.search(r"\$define NF\$NOREPLY\s+-2000000001\b", nf) is not None
       and ordered(ac, "gosub request.limits", "obj->settimeout(clear.ms)", "obj->error = ''", "obj->ServerStatus = NF$NOREPLY", "obj->clearfile(nf.h.fno(hx))", "if not(rq.lost) then obj->settimeout(req.ms)"), repr(unmarked))
    ck("NF7a a lost connection is dropped and reported, NEVER retried or reconnected inside an operation: lost.fail drops the connection then answers 11497 - and, for a CHANGING request (changing is set in "
       "act.change: everything but a lock), writes the audit line `netfile lost server=<name> op=<operation>` and answers 11509 instead (the outcome is not known); the only connect.new is in NF$OPEN; the "
       "handler holds no loop construct at all (no loop, no repeat, no while); drop.conn frees the slot and marks every handle on it lost (state 2)",
       ordered(body["lost.fail"], "gosub drop.conn", "if changing then", "kernel(K$AUDIT, 'netfile lost server=' : srvname : ' op=' : opname)", "fail.num = 11509", "end else", "fail.num = 11497")
       and "connect.new" not in body["lost.fail"] + body["drop.conn"]
       and not re.search(r"(?<![\w.$])(loop|repeat|while|goto)(?![\w.$])", ns) and "nf.h.state(hy) = 2" in body["drop.conn"]
       and ordered(body["drop.conn"], "nf.s.obj(slot) = 0", "nf.s.state(slot) = 0", "nf.h.state(hy) = 2"), "")
    rl = body["request.limits"]
    ck("NF7b the request bound (19 Oct 26, K8d: NETREPLY, 30 seconds by default, from the configuration; it was the constant NF$REQUEST.MS 30000): request.limits sets req.ms = NETREPLY * 1000 and "
       "clear.ms = the longer of NF$CLEAR.MIN.MS (300000) and req.ms; req.ms is given to the object in connect.new (the only place it is set for good); the one longer wait is the CLEARFILE's "
       "(clear.ms, set in act.change before the request and put back to req.ms after it); a handle of a lost connection answers 11495 (not a new connection) and CLOSE of it frees "
       "it without a word (allow.lost)",
       re.search(r"\$define NF\$CLEAR\.MIN\.MS\s+300000\b", nf) is not None and "NF$REQUEST.MS" not in nf and "NF$CLEAR.MS" not in nf
       and ordered(rl, "req.ms = config('NETREPLY') * 1000", "clear.ms = NF$CLEAR.MIN.MS", "if req.ms > clear.ms then clear.ms = req.ms", "return")
       # 21 Oct 26 (S.73 item 3): the administration verbs wait as long as a CLEARFILE does (an index on a big file takes minutes): act.admin and act.createfile set it before the request and put it back after
       and nf.count("settimeout(") == 7 and "obj->settimeout(req.ms)" in cn and cn.count("settimeout(") == 1 and "gosub request.limits" in cn
       and nf.count("settimeout(clear.ms)") == 3 and "settimeout(clear.ms)" in ac and ac.count("settimeout(") == 2
       and all(body[lab].count("settimeout(") == 2 and "settimeout(clear.ms)" in body[lab] and "obj->settimeout(req.ms)" in body[lab] for lab in ("act.admin", "act.createfile"))
       and ordered(gh, "if nf.h.state(hx) = 2 then", "if allow.lost then return", "fail.num = 11495")
       and re.search(r"act\.close:\s*\n\s*need\.gate = @false ; need\.conn = @false ; any\.acct = @true ; allow\.lost = @true", body["act.close"]) is not None, "")
    ck("NF7c CLOSEALL ends every connection and forgets every handle, is never refused (no gate, no list) and sends nothing but the quit that disconnect sends; STATE asks nothing and sends nothing",
       "obj->disconnect" in body["act.closeall"] and "gosub clear.handle" in body["act.closeall"] and not re.search(r"gate|kernel|obj->(open|read|select|close)", body["act.closeall"] + body["act.state"]), "")

    # ---- N8. the connection table: in named common, no secret in it
    cm = re.search(r"common\s+/\$netfile/[^\n]*(?:\n[ \t]+[^\n]*)*", nf)
    ck("NF8 the connections live in the named common block /$netfile/ (the only COMMON statement of the program), and the block holds no key, hash, pin, password, salt or credential by name",
       re.findall(r"common\s+/([^/]+)/", nf) == ["$netfile"] and cm is not None and not re.search(r"key|pin|pass|cred|hash|salt|secret", cm.group(0), re.I) and "nf.s.obj(NF$MAX.SERVERS)" in cm.group(0), "")

    # ---- N9. the audit trail and the messages carry nothing secret
    audits = re.findall(r"kernel\(K\$AUDIT,[^\n]*", nf)
    fails = re.findall(r"fail\.a\d = [^\n;]*", nf)
    aud_lines = re.findall(r"aud\.line = 'netfile[^\n]*", nf)
    ck("NF9 the audit lines are fixed words and values, all lower case, and never an id, a record or a secret: `netfile open server=<name> file=<remote file>` (and ` mode=write` after it for a write-mode "
       "handle - the read line is byte for byte the line of slice 3b), `netfile refused server=<name> reason=<word>` (the six open reasons, and mode), and, since slice 3e, `netfile write server=<name> "
       "file=<f>` and `netfile delete server=<name> file=<f>` (the first of each through a handle, by audit.once), `netfile clear server=<name> file=<f>` (every CLEARFILE), since S.72 `netfile filelock "
       "server=<name> file=<f>` (the first FILELOCK through a handle, by audit.once: a wait is many requests and one line) and `netfile lost server=<name> "
       "op=<operation>`; no secret local (login, keys, salt, pin, password) is in an audit line or becomes an argument of a message",
       sorted(audits) == sorted(["kernel(K$AUDIT, 'netfile open server=' : srv : ' file=' : fname)",
                                 "kernel(K$AUDIT, 'netfile open server=' : srv : ' file=' : fname : ' mode=write')",
                                 "kernel(K$AUDIT, 'netfile refused server=' : safe : ' reason=' : refused.why)",
                                 "kernel(K$AUDIT, 'netfile clear server=' : srvname : ' file=' : nf.h.file(hx))",
                                 "kernel(K$AUDIT, 'netfile lost server=' : srvname : ' op=' : opname)",
                                 # 21 Oct 26 (S.73 item 3): the administration operations, one line for each call (not once for the handle); the file is the name the handle was opened under,
                                 # or - for create.file - the first word of the verb's words, cleaned (printable ASCII, at most 100 characters)
                                 "kernel(K$AUDIT, 'netfile admin server=' : srvname : ' file=' : nf.h.file(hx) : ' op=' : opname)",
                                 "kernel(K$AUDIT, 'netfile admin server=' : srv : ' file=' : out.txt : ' op=create.file')",
                                 "kernel(K$AUDIT, 'netfile fcontrol server=' : srvname : ' file=' : nf.h.file(hx) : ' key=' : fkey)",
                                 "kernel(K$AUDIT, aud.line)"])
       and sorted(aud_lines) == sorted(["aud.line = 'netfile refused server=' : srvname : ' reason=mode'", "aud.line = 'netfile write server=' : srvname : ' file=' : nf.h.file(hx)",
                                        "aud.line = 'netfile delete server=' : srvname : ' file=' : nf.h.file(hx)",
                                        "aud.line = 'netfile filelock server=' : srvname : ' file=' : nf.h.file(hx)",
                                        "aud.line = 'netfile refused server=' : srvname : ' reason=mode'", "aud.line = 'netfile write server=' : srvname : ' file=' : nf.h.file(hx)"])   # admin.prepare and act.seqkey: the same two lines again
       and ordered(raw, "' mode=write'") and not re.search(r"[A-Z]", "".join(re.findall(r"'(netfile [^']*)'", nf)))
       and not any(re.search(NF_SECRET_LOCALS, a, re.I) for a in audits + aud_lines) and not any(re.search(NF_SECRET_LOCALS, f) for f in fails), repr((audits, aud_lines, [f for f in fails if re.search(NF_SECRET_LOCALS, f)])))
    ck("NF9a the shapes that guard the names: a server name is a lower case letter then up to 15 lower case letters or digits; a remote file name is letters, digits and . _ - $ up to MAX.ID.LEN with "
       "'dict ' in front for a dictionary - and no slash, so no pathname can be asked for",
       ordered(body["shape.names"], "chk.set = lc.set:digits", "len(srv) <= 16", "index(lc.set, srv[1, 1], 1)", "fname[1, 5] = 'dict '", "chk.set = lc.set:digits:'._-$'", "len(body) <= MAX.ID.LEN")
       and "'/'" not in body["shape.names"] and "/" not in re.sub(r"'[^']*'", "", body["shape.names"]), "")

    # ---- N10. the messages
    lits = {}
    for m in re.finditer(r"fail\.num = (\d+)([^\n]*)", nf):
        lits.setdefault(int(m.group(1)), []).append(len(re.findall(r"fail\.a\d = ", m.group(2))))
    block_used = {n for n in lits if NF_MSG_FIRST <= n <= NF_MSG_LAST}
    texts = {n: srcs.get("msg:%d" % n) for n in range(NF_MSG_FIRST, NF_MSG_LAST + 1)}
    places = {n: max([int(x) for x in re.findall(r"%(\d)", t)] or [0]) for n, t in texts.items() if t}
    handler_msgs = set(range(NF_MSG_FIRST, NF_MSG_USED + 1)) - set(NF_MSG_KERNEL_ONLY)            # 11490-11506, 11509, 11510, 11512
    ck("NF10 messages 11490 to 11512 all exist (one line each, inside the Linux block 11000-11999); the handler uses 11490-11506 and, since slice 3e, 11509 (a changing request got no reply), 11510 (a "
       "transaction is open) and 11512 (a bad lock kind); 11507, 11508 and 11511 are the KERNEL's (netfiles.c, never used by netfile; 11510 is the kernel's as well); 11513 onwards are the shared account's since S.66 "
       "(test-shared-units.py S3), and no other program of gpl.bp cites a number of the block",
       all(texts[n] is not None and texts[n].strip() != "" and "\n" not in texts[n].rstrip("\n") for n in range(NF_MSG_FIRST, NF_MSG_USED + 1))
       and block_used == handler_msgs and all(texts[n] is None for n in range(NF_MSG_USED + 1, NF_MSG_LAST + 1))
       and LINUX_BLOCK[0] <= NF_MSG_FIRST and NF_MSG_LAST <= LINUX_BLOCK[1]
       and not [k for k, t in c.items() if k.startswith("bp:") and k not in ("bp:netfile", "bp:netfile.h") and re.search(r"\b1150\d\b|\b1151[0-2]\b|\b1149\d\b", t)],
       repr(sorted(handler_msgs ^ block_used)))
    short = [(n, k, places.get(n, 0)) for n, ks in lits.items() if n in places for k in ks if k < places.get(n, 0)]
    ck("NF10a each message has at most three %n places (rc carries three arguments), and every place a message has is given an argument at the line that raises it (11460, reused, gets two - its "
       "server is rc<4>, which the text does not print); 11509, 11510, 11511 and 11512 each have exactly two places (the server and the operation, or the bad lock kind)",
       all(v <= 3 for v in places.values()) and not short and places.get(11497) == 2 and places.get(11500) == 3 and places.get(11494) == 1
       and all(places.get(n) == 2 for n in (11509, 11510, 11511, 11512)), repr(short))
    ck("NF10b the wording the suite relies on: 11494 names the handle, 11495 and 11497 and 11499 and 11500 name the server, 11497 says the connection was LOST during an operation and that nothing "
       "more is sent, 11501 says the file is read only and that nothing was sent, 11493 says 10 servers is the limit by its argument; 11509 says the connection was lost during the operation, that it is "
       "NOT KNOWN whether the change was made, that nothing more is sent and how to find out; 11510 says a change or lock is refused inside a transaction and that nothing was sent; 11511 says the "
       "operation is not available for a file on the server and that nothing was sent; 11512 says the lock kind is not valid",
       all("%1" in (texts.get(n) or "") for n in (11493, 11494, 11495, 11496, 11497, 11498, 11499, 11500, 11501, 11509, 11510, 11511, 11512)) and "lost during" in (texts.get(11497) or "")
       and "Nothing more is sent" in (texts.get(11497) or "") and "read only" in (texts.get(11501) or "") and "Nothing was sent" in (texts.get(11501) or "")
       and "%1 servers" in (texts.get(11493) or "")
       and "was lost during" in (texts.get(11509) or "") and "not known whether the change was made" in (texts.get(11509) or "") and "Nothing more is sent" in (texts.get(11509) or "")
       and "read the record to find out" in (texts.get(11509) or "")
       and "inside a transaction" in (texts.get(11510) or "") and "Nothing was sent" in (texts.get(11510) or "")
       and "not available" in (texts.get(11511) or "") and "Nothing was sent" in (texts.get(11511) or "") and "lock kind" in (texts.get(11512) or ""), "")

    # ---- N11. the suite and the map
    drv = suite[suite.find("NFH_DRIVER = r"):suite.find("NFH_SUB = r")]
    k_errs = {int(x) for x in re.findall(r"k_err\((\d+)", suite)}
    m72 = re.search(r"^NF_FILELOCK, NF_FILEUNLOCK = (\d+), (\d+)\s*(?:#.*)?$", suite, re.M)
    ck("NF11 the suite sandbox-netfile.py drives EVERY operation by its NF$ name (16 names in the driver) EXCEPT 18 and 19 (S.72), which it drives by number with the RAW line - so that the driver "
       "compiles on a tree that has no NF$FILELOCK yet - and the suite's constants NF_FILELOCK and NF_FILEUNLOCK are netfile.h's NF$FILELOCK and NF$FILEUNLOCK; it compiles netcred, netfile and its two "
       "test programs, has the sections handler, readonly, refuse, lost, timeout, hwrite (the handler in write mode, slice 3e), kwrite (the statements, slice 3e) and gaps, runs gaps only when it is "
       "named (it is red by design), and every message number it expects is a message of the tree",
       all(re.search(r"op = %s\b" % re.escape(k).replace(r"\$", "[$]"), drv) for k in NF_OPS_BY_NAME) and len(NF_OPS_BY_NAME) == 16
       and not re.search(r"op = NF[$]FILE(?:UN)?LOCK\b", drv) and "case nm = 'RAW'" in drv and "op = a + 0" in drv
       and m72 is not None and (int(m72.group(1)), int(m72.group(2))) == (got.get("NF$FILELOCK"), got.get("NF$FILEUNLOCK")) == (18, 19)
       and "BASIC gpl.bp netcred netfile zznfh zznfhx" in suite and r"Compiled 4 program\(s\) with no errors" in suite
       and all('("%s", %s_section)' % (s, s) in suite for s in NF_SUITE_SECTIONS) and 'OPT_IN = ("gaps",)' in suite
       and "(sections is None and name not in OPT_IN)" in suite and k_errs and all(os.path.exists(os.path.join(MSGDIR, str(k))) for k in k_errs), repr(sorted(k_errs)))
    rules_ok = all(re.search(r"^%s\s*:[^\n]*\bnetfile\b" % re.escape(p), rm, re.M) is not None
                   for p in ("sdsys/gpl.bp/netfile", "sdsys/gpl.bp/netfile.h", "sdsys/messages/1149*", "sdsys/messages/1150*", "sdsys/messages/1151*"))
    def first(pat):
        m = re.search(r"^%s\s*:" % re.escape(pat), rm, re.M)
        return m.start() if m else 10 ** 9
    ck("NF12 regress-map.txt: the handler, its header and its messages select the netfile suite, and each rule comes BEFORE the coarse rule that would otherwise take the file (gpl.bp/*.h, gpl.bp/*, "
       "messages/* - the first rule that matches is the only one used)",
       rules_ok and first("sdsys/gpl.bp/netfile") < first("sdsys/gpl.bp/*.h") and first("sdsys/gpl.bp/netfile.h") < first("sdsys/gpl.bp/*.h") and first("sdsys/gpl.bp/netfile.h") < first("sdsys/gpl.bp/*")
       and first("sdsys/messages/1151*") < first("sdsys/messages/*"), "")
    ck("NF13 the dated history lines are there: netfile, netfile.h and the suite (`17 Oct 26 dm  S.65 slice 3b`), and this check's own file says so",
       "17 Oct 26 dm  S.65 slice 3b" in raw and "17 Oct 26 dm  S.65 slice 3b" in rawh and "17 Oct 26 dm  S.65 slice 3b" in suite and "S.65 slice 3b" in (__doc__ or ""), "")
    # ---- N8. S.73 item 3 D1: NF$INDEXQ, the index query statements
    ai = body["act.indexq"]
    arms = re.findall(r"case what = (\d) ; obj->ServerStatus = NF\$NOREPLY ; (?:res = )?obj->(\w+)\(", ai)
    ck("NF14 act.indexq (NF$INDEXQ, 24; S.73 item 3 D1): dispatched from the main case; the gate and the connection are needed and no account test is skipped (get.handle, need.gate); an unknown `what` (not 1 to 8) "
       "is 11490 naming it before anything is sent; the eight arms each set the 'no reply' mark ON THEIR OWN LINE before the one request they make (1 and 2 indices, 3 selectindexv, 4 selectindexk, 5 and 6 setleft and "
       "setright, 7 and 8 selectleft and selectright with the list number NF$LIST); the answer goes through admin.outcome (the lost connection, the server's error and rc<8> are decided there); a scan "
       "that found a key (what 7 or 8 and rc<8> 0) makes a SECOND marked request, READLIST, handled as act.select handles its own (lost, server error, ON ERROR text, an answer other than 0 or 1 is 11504), and "
       "answers the key, a field mark and the ids with the first request's rc<8> put back; the routine has no mode test, no refusal for a transaction, no audit line and no changing flag - a query changes nothing",
       re.search(r"case op = NF\$INDEXQ\s*;?\s*gosub act\.indexq", main) is not None and ai != ""
       and ordered(ai, "need.gate = @true ; need.conn = @true ; any.acct = @false ; allow.lost = @false", "gosub get.handle", "if failed then return", "opname = 'index'", "what = 0",
                   "if b matches '1N' then what = b + 0", "if what < 1 or what > 8 then", "fail.num = 11490", "gosub fail", "return", "iname = c ; ival = ''", "if what = 4 then",
                   "obj = nf.s.obj(slot)", "obj->error = ''", "begin case", "end case", "gosub admin.outcome", "if failed then return", "out = res", "if what >= 7 and rc<8> = 0 then", "st1 = rc<8>",
                   "obj->error = ''", "obj->ServerStatus = NF$NOREPLY", "lst = obj->readlist(NF$LIST, e)", "gosub after.rq", "nf.requests += 1", "if rq.lost then", "gosub lost.fail", "return",
                   "if rq.err then", "gosub server.fail", "return", "if e = 1 then", "gosub on.error.text", "gosub server.fail", "return", "if e # 0 then", "fail.num = 11504", "gosub fail", "return",
                   "out = key : @fm : lst", "rc<8> = st1")
       and arms == [("1", "indices"), ("2", "indices"), ("3", "selectindexv"), ("4", "selectindexk"), ("5", "setleft"), ("6", "setright"), ("7", "selectleft"), ("8", "selectright")]
       and ai.count("NF$LIST") == 3 and ai.count("obj->") == 20      # 2 `error`, 8 arms of a mark and a method, the second request's mark and readlist
       and not re.search(r"mode\.now|act\.refuse|changing|nf\.h\.mode|NF\$NOREPLY ; obj->(write|delete|clearfile|recordlock|release)|kernel\(K\$AUDIT|audit\.once|txn|transaction", ai), repr((arms, ai.count("obj->"))))


# ---- NK. S.65 slice 3c: the kernel half - the NET_FILE type, netfiles.c, the VOC pointer, and the refusal of every other statement ----------------------

NK_FUNCS = ("net_path_is_net", "net_open", "net_close", "net_read", "net_readv", "net_fileinfo", "net_select", "net_refuse", "net_close_all", "net_message",   # net_select: slice 3d
            "net_gate", "net_write", "net_delete", "net_clear", "net_lock", "net_lock_step", "net_check_lock", "net_release", "net_release_all", "net_flush_closes",   # slice 3e
            "net_filelock_step", "net_fileunlock", "net_recordlocked",   # S.72: exported, defined once, one prototype in sd.h that agrees
            "net_index_query")   # S.73 item 3 D1
NK_TYPES = {"DIRECTORY_FILE": 1, "DYNAMIC_FILE": 2, "SEQ_FILE": 3, "NET_FILE": 4}
# what a refusal must come before: the first of these in the function (a NET_FILE has no file table entry, so each of them reads or WRITES memory in front of the table)
NK_DANGER = ("FPtr(", "access.dh", "lock_record(", "unlock_record(", "check_lock(", "end_select(", "clear_select(", "log_permissions_error(", "edit_refusal(", "txn_read(", "k_recurse(")
# THE CENSUS OF 17 OCT 26 (49 opcode functions take a file variable): the sites it says REFUSE.  How: R = net_refuse() called directly after a NET_FILE test,
# H = refuse_net_file() (op_dio3.c: tests the type, refuses, sets the status).  The tuple is what, besides NK_DANGER, the refusal must come before.
NK_REFUSE = {
    ("op_dio1.c", "op_configfl"): ("R", ("FV_RDONLY",)),
    ("op_dio3.c", "read_record"): ("H", ()),
    ("op_dio3.c", "op_readv"): ("H", ()),
    ("op_dio3.c", "op_clrfile"): ("H", ("file_lock",)),
    ("op_dio3.c", "op_delete"): ("H", ()),
    ("op_dio3.c", "op_write"): ("H", ()),
    ("op_dio3.c", "op_writev"): ("H", ()),
    ("op_lock.c", "op_lockrec"): ("R", ()),
    ("op_lock.c", "op_release"): ("R", ()),
    ("op_lock.c", "op_rlsfile"): ("R", ()),
    ("dh_ak.c", "op_akdelete"): ("R", ()),
    ("dh_ak.c", "op_akread"): ("R", ()),
    ("dh_ak.c", "op_akwrite"): ("R", ()),
    ("dh_ak.c", "op_akclear"): ("R", ()),
    ("dh_ak.c", "op_akenable"): ("R", ()),
    ("dh_ak.c", "op_akmap"): ("R", ()),
    # S.73 item 3 D1 (21 Oct 26): op_selindx, op_selindxv, akscan and setakpos left this table - they ask the server (NK_INDEXQ, NK18)
    ("dh_misc.c", "op_fcontrol"): ("R", ()),       # S.73 item 3: still a refusal for every key but the two internal ones of the administration verbs (FC_NET_ADMIN, FC_NET_CREATE), which it forwards first
    ("analyse.c", "op_analyse"): ("R", ()),
}
# pub_fcontrol (the public FCONTROL()) was a REFUSE site in slice 3c; since S.73 item 3 (21 Oct 26) it forwards the key to the server (net_fcontrol, request 71: gated as a change, FC$VALID.ID as a read) and
# is no refusal at all - NK_FCONTROL_SITES holds what it does (decided in NK8, read by NK7a).
NK_FCONTROL_SITES = {("dh_misc.c", "pub_fcontrol")}
# FILELOCK, FILEUNLOCK, GETLOCKS() and RECORDLOCKED() were REFUSE sites in slices 3c and 3e; since S.72 (20 Oct 26) they are not refusals at all: FILELOCK and FILEUNLOCK ask net_gate (a read-mode handle is
# refused THERE, with 11501) and then the server, RECORDLOCKED() asks net_recordlocked - which, since S.72b (20 Oct 26), asks net_gate(NETG_PEEK) first, so a read-mode handle is refused INSIDE it with 11501 and
# nothing is sent (S72d, S72s) - and GETLOCKS() gives a NET_FILE the local view (the counters, no lock line).  They are decided here, and S72a,
# S72f, S72g, S72h and S72i read what each does.  None of the four may call net_refuse or refuse_net_file in its own body any more.
NK_LOCKSITES = {("op_lock.c", "op_filelock"), ("op_lock.c", "op_flunlock"), ("op_lock.c", "op_getlocks"), ("op_lock.c", "op_reclckd")}
# SELECT and SELECTV were REFUSE sites in slice 3c; since slice 3d they ask the server (NK14, NK15), and are decided here
NK_SELECT ={("op_dio4.c", "op_select"), ("op_dio4.c", "op_selectv")}
# INDICES (both forms) were REFUSE sites in slice 3c; since slice 3d a NET_FILE got the null string through the default arm, because the query processor asks it of every file.  Since S.73 item 3 D1
# (21 Oct 26) the six index QUERY sites ask the server (NK18): INDICES (both), SELECTINDEX (both: op_selindx, op_selindxv), SELECTLEFT / SELECTRIGHT (akscan) and SETLEFT / SETRIGHT (setakpos)
NK_INDEXQ = {("dh_ak.c", "op_indices1"), ("dh_ak.c", "op_indices2"), ("dh_ak.c", "op_selindx"), ("dh_ak.c", "op_selindxv"), ("dh_ak.c", "akscan"), ("dh_ak.c", "setakpos")}
# ...and the two Private helpers that akscan and the two SELECTINDEX opcodes hand over to (they take the file variable off the stack, so NK8 wants them decided; NK18a reads them)
NK_INDEXQ_HELPERS = {("dh_ak.c", "net_selindex"), ("dh_ak.c", "net_akscan")}
# the census says REFUSE, but by a guard on the read of the file table and not by a statement refusal: the NET_FILE test must come before the first FPtr(
NK_GUARD = (("op_dio2.c", "get_file_status"), ("k_error.c", "log_permissions_error"), ("pdump.c", "dump_variable"), ("op_dio2.c", "op_fileinfo"))
# the census says IGNORE because the function already answers any other kind of file: the sequential-file family (ER_NSEQ), GETPORT / SETPORT, GROUPSTAT, SET.TRIGGER, MARK.MAPPING
NK_SAFE = {("op_seqio.c", n): "SEQ_FILE" for n in ("op_createsq", "op_flush", "op_nobuf", "openseq", "op_readblk", "op_readseq", "op_seek", "op_timeout", "op_weofseq", "op_writeblk",
                                                    "writeseq", "op_get_device")}
NK_SAFE.update({("lnxport.c", "op_getport"): "SEQ_FILE", ("lnxport.c", "op_setport"): "SEQ_FILE", ("dh_misc.c", "op_grpstat"): "DYNAMIC_FILE", ("dh_misc.c", "op_settrig"): "ER_NDYN",
                ("op_dio3.c", "op_mapmarks"): "DIRECTORY_FILE"})
# the rest of the census: SUPPORT (OPEN, CLOSE and the release of a variable) and IGNORE with a reason (generic descriptor code; the IPC file is opened with OPENPATH; the debugger prints a type; triggers
# are reached from the DYNAMIC and DIRECTORY arms only)
NK_OTHER = {("op_dio1.c", "op_close"), ("op_dio1.c", "open_file"), ("op_dio3.c", "call_trigger"), ("k_funcs.c", "k_dereference"), ("k_funcs.c", "k_get_file"), ("k_funcs.c", "k_incr_refct"),
            ("k_funcs.c", "k_release"), ("kernel.c", "process_events"), ("kernel.c", "dump_status"), ("op_debug.c", "get_var_info"), ("op_loads.c", "op_dup"),
            ("op_kernel.c", "op_kernel")}      # slice 3e: K_EDIT_OK / K_EDIT_KIND take the FILE VARIABLE of a remote file (k_get_file); decided by the S2 checks (U11), not a refusal
NK_SITES_WITH_H = {"read_record", "op_readv", "op_clrfile", "op_delete", "op_write", "op_writev"}
NK_SUITE_MATRIX = ("write", "writeu", "writev", "matwrite", "delete", "clearfile", "readu", "readl", "readvu", "readvl", "matreadu", "matreadl", "recordlocku", "release", "filelock",
                   "fileunlock", "fcontrol6", "fiexcl", "txnwrite")
NK_MAP_FILES = ("gplsrc/netfiles.c", "gplsrc/op_dio1.c", "gplsrc/op_dio2.c", "gplsrc/op_dio3.c", "gplsrc/op_dio4.c", "gplsrc/op_lock.c", "gplsrc/dh_ak.c", "gplsrc/dh_misc.c",
                "gplsrc/analyse.c", "gplsrc/k_error.c", "gplsrc/pdump.c", "gplsrc/descr.h", "gplsrc/sd.h", "gpl.src", "sdsys/gpl.bp/_voc_ref",
                "gplsrc/op_sh.c", "gplsrc/op_kernel.c", "sdsys/gpl.bp/cproc", "sdsys/gpl.bp/edit_guard")      # slice 3e


@functools.lru_cache(maxsize=None)
def c_functions(tx):
    """{name: text} of the top-level C functions of one comment-free source: a header at column 0, then the body in braces (strings and character
    constants skipped when the braces are counted)."""
    return {name: tx[a:b] for name, (a, b) in c_spans(tx).items()}


def blank_c(src):
    """The source with every comment turned to white space of the same length, so that offsets found in it are offsets in the source."""
    def blank(m):
        return re.sub(r"[^\n]", " ", m.group(0))
    src = re.sub(r"/\*.*?\*/", blank, src, flags=re.S)
    return re.sub(r"//[^\n]*", blank, src)


@functools.lru_cache(maxsize=None)
def c_spans(tx):
    """{name: (start, end)} of the top-level C functions of a source in which comments are gone or blanked."""
    out = {}
    for m in re.finditer(r"^[A-Za-z_][^\n;{}=]*?\b([A-Za-z_]\w*)\s*\([^;{}]*\)\s*\{", tx, re.M):
        name = m.group(1)
        if name in ("if", "for", "while", "switch", "return", "sizeof"):
            continue
        depth, k = 0, m.end() - 1
        while k < len(tx):
            ch = tx[k]
            if ch in "\"'":
                q = ch
                k += 1
                while k < len(tx) and tx[k] != q:
                    if tx[k] == "\\":
                        k += 1
                    k += 1
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        out[name] = (m.start(), k + 1)
    return out


def edit_func(name, pattern, repl, count=1):
    """A mutant (a function of the source text) that changes PATTERN to REPL (a regular expression) inside the function NAME only; KeyError if it is not there."""
    def f(text):
        span = c_spans(blank_c(text)).get(name)
        if span is None:
            raise KeyError("function not in the source: " + name)
        a, b = span
        body, n = re.subn(pattern, repl, text[a:b], count=count, flags=re.S)
        if n == 0:
            raise KeyError("pattern not in %s: %r" % (name, pattern[:60]))
        return text[:a] + body + text[b:]
    return f


def nospace(s):
    return re.sub(r"\s+", "", s)


def c_types(params):
    """The parameter list with the parameter NAMES and the white space gone: "FILE_VAR * fvar, int key" is "FILE_VAR*,int" (a name is not part of what a prototype promises)."""
    if params.strip() in ("", "void"):
        return ""
    return ",".join(nospace(re.sub(r"\s*\b[A-Za-z_]\w*\s*$", "", p)) for p in params.split(","))


def c_proto(text, name):
    """The prototype of NAME in a comment-free source: the return type, the name and the parameter types, white space gone ("intnet_open(FILE_VAR*,constchar*)"), or None."""
    m = re.search(r"^[ \t]*([A-Za-z_][\w \t\*]*?)\b%s\s*\(([^;{)]*)\)\s*;" % re.escape(name), text, re.M)
    if not m:
        return None
    return nospace(m.group(1)) + name + "(" + c_types(m.group(2)) + ")"


def c_header(text, name):
    """The same for the definition of NAME (the header up to its opening brace)."""
    m = re.search(r"^([A-Za-z_][\w \t\*]*?)\b%s\s*\(([^;{)]*)\)\s*\{" % re.escape(name), text, re.M)
    if not m:
        return None
    return nospace(m.group(1)) + name + "(" + c_types(m.group(2)) + ")"


def inside(body, opener, needle):
    """NEEDLE is found, and the nearest OPENER before it is a block that is still open there."""
    j = body.find(needle)
    i = body.rfind(opener, 0, j) if j >= 0 else -1
    if i < 0 or j < 0:
        return False
    depth = 1
    for ch in body[i + len(opener):j]:
        depth += (ch == "{") - (ch == "}")
        if depth <= 0:
            return False
    return True


def map_rules(text):
    out = []
    for ln in text.split("\n"):
        ln = ln.strip()
        if not ln or ln.startswith("@") or ":" not in ln or " ~ " in ln:
            continue
        pat, suites = ln.split(":", 1)
        out.append((pat.strip(), suites.split()))
    return out


def checks_3c(srcs, c, ck):
    """S.65 slice 3c: the kernel half of remote files, as ORDER and as what no statement may reach.  Nothing here compiles or runs C: the section kernel of
    sandbox-netfile.py runs real statements against a NET file (and the refusal matrix), and `make` is the compiler."""
    nf, dsc, sdh = c["netfiles.c"], c["descr.h"], c["sd.h"]
    nfraw = srcs["netfiles.c"]
    vr = c["bp:_voc_ref"]
    suite, rm = srcs["sandbox-netfile.py"], c["regress-map.txt"]

    def ct(fname):
        return c.get(fname) or c.get("c:" + fname, "")

    def fn(fname, name):
        return c_functions(ct(fname)).get(name, "")

    nw, nraw = fn("netfiles.c", "net_open_work"), fn("netfiles.c", "net_call_core")     # slice 3e: net_call_raw is a wrapper over net_call_core

    # ---- NK1. the type, the union member, the limits
    allf = {m.group(1): int(m.group(2)) for m in re.finditer(r"#define\s+([A-Z_]+_FILE)\s+(\d+)\b", dsc)}
    ck("NK1 descr.h: the file variable types are DIRECTORY_FILE 1, DYNAMIC_FILE 2, SEQ_FILE 3 and NET_FILE 4 (4 is NET_FILE's alone, and 5 stays unused), and the union member `net` holds, in this "
       "order, the two pointer-sized words that read as a NULL access.dir.trg (void *zero[2]), the handler's handle (int16_t), the epoch (u_int16_t), the server name (NET_SERVER_LEN + 1 bytes) and, since slice 3e, AFTER the name and in this order the write flag "
       "(u_char write: the server's mode at the open) and the S.64 edit kind of the remote file's name (u_char edit_kind)",
       all(allf.get(k) == v for k, v in NK_TYPES.items()) and [k for k, v in allf.items() if v == 4] == ["NET_FILE"] and 5 not in allf.values()
       and re.search(r"struct\s*\{\s*void\s*\*\s*zero\[2\];\s*int16_t\s+handle;\s*u_int16_t\s+epoch;\s*char\s+server\[NET_SERVER_LEN\s*\+\s*1\];\s*u_char\s+write;\s*u_char\s+edit_kind;\s*\}\s*net;", dsc) is not None, repr(allf))
    nfh = c["bp:netfile.h"]
    handles = re.search(r"\$define\s+NF\$MAX\.HANDLES\s+(\d+)", nfh)
    ck("NK1a the limits agree across C and BASIC: NET_MAX_HANDLES is netfile.h's NF$MAX.HANDLES (100); NET_SERVER_LEN is 16, the length _voc_ref and the handler allow for a server name; NET_FILE_MAX is 63, "
       "the length _voc_ref allows for a file name and the number message 11491 gives",
       re.search(r"#define\s+NET_MAX_HANDLES\s+(\d+)", dsc) is not None and handles is not None and re.search(r"#define\s+NET_MAX_HANDLES\s+(\d+)", dsc).group(1) == handles.group(1) == "100"
       and re.search(r"#define\s+NET_SERVER_LEN\s+16\b", dsc) is not None and "len(srv) <= 16" in c["bp:netfile"] and "len(n.srv) > 16" in vr
       and re.search(r"#define\s+NET_FILE_MAX\s+63\b", nf) is not None and "len(n.file) > 63" in vr and "up to 63 characters" in (srcs.get("msg:11491") or ""), "")
    codes = {"NF_OPEN": "NF$OPEN", "NF_CLOSE": "NF$CLOSE", "NF_READ": "NF$READ", "NF_READV": "NF$READV", "NF_FILEINFO": "NF$FILEINFO", "NF_CLOSEALL": "NF$CLOSEALL",
             "NF_RC_OK": "NF$RC.OK", "NF_RC_ELSE": "NF$RC.ELSE", "NF_RC_ERROR": "NF$RC.ERROR",
             "NF_RECORDLOCKED": "NF$RECORDLOCKED", "NF_SELECT": "NF$SELECT", "NF_WRITE": "NF$WRITE", "NF_DELETE": "NF$DELETE", "NF_CLEARFILE": "NF$CLEARFILE", "NF_LOCK": "NF$LOCK",   # slice 3e
             "NF_WRITEU": "NF$WRITEU", "NF_DELETEU": "NF$DELETEU", "NF_RELEASE": "NF$RELEASE", "NF_RC_LOCKED": "NF$RC.LOCKED",
             "NF_FILELOCK": "NF$FILELOCK", "NF_FILEUNLOCK": "NF$FILEUNLOCK",      # S.72: 18 and 19
             "NF_ADMIN": "NF$ADMIN", "NF_CREATEFILE": "NF$CREATEFILE", "NF_FCONTROL": "NF$FCONTROL", "NF_SEQKEY": "NF$SEQKEY"}      # S.73 item 3: 20 to 23
    cdef ={m.group(1): int(m.group(2)) for m in re.finditer(r"#define\s+(NF_[A-Z_]+)\s+(\d+)\b", nf)}
    bdef = {m.group(1): int(m.group(2)) for m in re.finditer(r"\$define\s+(NF\$[A-Z.]+)\s+(-?\d+)", nfh)}
    ck("NK1b the operation and result codes netfiles.c mirrors are netfile.h's, name for name (OPEN, CLOSE, READ, READV, RECORDLOCKED, SELECT, FILEINFO, CLOSEALL, and since slice 3e WRITE, DELETE, CLEARFILE, LOCK, "
       "WRITEU, DELETEU, RELEASE, since S.72 FILELOCK 18 and FILEUNLOCK 19, and since S.73 item 3 ADMIN 20, CREATEFILE 21, FCONTROL 22 and SEQKEY 23; the results OK 0, ELSE 2, ERROR 3, LOCKED 4), and netfiles.c defines no other NF_ operation (17 stays unused)",
       all(k in cdef and bdef.get(v) == cdef[k] for k, v in codes.items()) and cdef.get("NF_FILELOCK") == 18 and cdef.get("NF_FILEUNLOCK") == 19 and cdef.get("NF_ADMIN") == 20 and cdef.get("NF_SEQKEY") == 23
       and not any(v in (17,) for v in cdef.values()),
       repr({k: (cdef.get(k), bdef.get(v)) for k, v in codes.items() if bdef.get(v) != cdef.get(k)}))

    # ---- NK2. the nine functions, once each, and every declaration of them says the same
    defs = {n: c_header(nf, n) for n in NK_FUNCS}
    protos = {n: c_proto(sdh, n) for n in NK_FUNCS}
    others = {}
    for fname in ("op_dio2.c", "op_dio3.c", "op_dio1.c"):
        for n in NK_FUNCS:
            p = c_proto(c[fname], n)
            if p is not None:
                others[(fname, n)] = p
    twice = [n for n in NK_FUNCS if sum(len(re.findall(r"^[A-Za-z_][\w \t\*]*?\b%s\s*\([^;{)]*\)\s*\{" % n, t, re.M)) for k, t in c.items()
                                          if k.endswith((".c",)) or k.startswith("c:")) != 1]
    ck("NK2 the %d netfiles.c functions (net_path_is_net, net_open, net_close, net_read, net_readv, net_fileinfo, net_select, net_refuse, net_close_all, net_message, the slice 3e entry points and, since S.72, "
       "net_filelock_step, net_fileunlock and net_recordlocked) are each DEFINED ONCE in the kernel, "
       "have a prototype in sd.h that says exactly what the definition says, and every other prototype of them (op_dio2.c, op_dio3.c) agrees too" % len(NK_FUNCS),
       all(defs.values()) and defs == protos and not twice and all(p == protos[n] for (f, n), p in others.items()) and len(others) >= 5, repr((defs, protos, twice, others)))

    # ---- NK3. the order: the shapes, THE GATE, the audit, then the handler
    ck("NK3 net_open_work, in this ORDER: the encoded pointer's shape (char(1) N char(1) server char(1) file), THE GATE (net_gate_ok), its refusal audited and RETURNED, and only then the queued closes and the "
       "handler (NF_OPEN) - before the gate there is no handler call, no load_object and no queue flush",
       ordered(nw, "encoded_path[1] != 'N'", "(u_char)encoded_path[2] != 1", "strchr(p, 1)", "if (!net_gate_ok())", "audit_message(", "return -ER_PERM;", "net_flush_pending();", "net_call_raw(NF_OPEN")
       and not re.search(r"net_call_raw\(|net_flush_pending\(|load_object\(|k_call\(", nw[:nw.find("if (!net_gate_ok())")]) if "if (!net_gate_ok())" in nw else False, "")
    gate = fn("netfiles.c", "net_gate_ok")
    ck("NK3a THE GATE: the administrator (USR_ADMIN in the session's flags) or an account holding the NET gate (UG_NET in its gates), asked of the session and of nothing else; an $internal program is NOT "
       "exempt (HDR_INTERNAL is in netfiles.c once, in net_gate()'s S.64 edit test of slice 3e, and not in the NET gate, the open or the handler call); the refusal is message 11460 with the account, audited as 'netfile refused server=<name> reason=gate' with the server name made safe",
       re.search(r"return\s*MY_ADMIN\(\)\s*\|\|\s*MY_GATE\(UG_NET\);", gate) is not None
       and "HDR_INTERNAL" not in gate + nw + fn("netfiles.c", "net_call_core") and nf.count("HDR_INTERNAL") == 1 and "HDR_INTERNAL" in fn("netfiles.c", "net_gate")     # slice 3e: net_gate's edit test only
       and ordered(nw, "net_set_message(MSG_NO_GATE, account(), safe", "\"netfile refused server=%s reason=gate\"") and "#define MSG_NO_GATE 11460" in nf
       and re.search(r"safe\[i\]\s*=\s*\(\(\(server\[i\] >= 'a'\) && \(server\[i\] <= 'z'\)\) \|\| \(\(server\[i\] >= '0'\) && \(server\[i\] <= '9'\)\)\) \? server\[i\] : '\?';", nw) is not None, "")
    ck("NK3b net_call_raw: the program is looked for FIRST (load_object of $netfile, so a tree without it says message 11507 and does not stop the process), the six arguments are pushed, the handler is "
       "called BY NAME (k_call of \"$netfile\", so the $internal flag it carries is the global catalogue's) with PF_IS_TRIGGER, run to its RETURN, and the reference k_call counted is given back; the name "
       "$netfile appears in the kernel's code exactly twice (the lookup and the call) and in no other kernel file",
       ordered(nraw, "load_object(\"$netfile\", FALSE) == NULL", "net_set_message(MSG_HANDLER", "(e_stack++)->data.value = op;", "net_push_string(a, alen);", "(e_stack++)->data.d_addr = out;",
               "(e_stack++)->data.d_addr = &rc_descr;", "k_call(\"$netfile\", 6, NULL, 0);", "process.program.flags |= PF_IS_TRIGGER;", "k_run_program();", "k_exit_cause == K_EXIT_RECURSIVE",
               "--(hdr->ext_hdr.prog.refs)", "unload_object(")
       and nf.count("\"$netfile\"") == 2 and not [k for k, t in c.items() if k != "netfiles.c" and (k.endswith(".c") or k.startswith("c:")) and "\"$netfile\"" in t], "")

    # ---- NK4. what each public function may and may not do
    refuse, close_, closeall, stale, op_ = (fn("netfiles.c", n) for n in ("net_refuse", "net_close", "net_close_all", "net_stale", "net_op_ex"))
    refwith, lowerw = fn("netfiles.c", "net_refuse_with"), fn("netfiles.c", "net_lower_what")
    ck("NK4 net_refuse RUNS NO BASIC and touches nothing: no handler call, no queue flush, no k_call, no k_run_program; it takes the server from the variable only when it is a NET_FILE, writes the statement "
       "in lower case, builds the message (server, statement) and returns net_raise(status) - which does not return without ON ERROR.  Since slice 3e it is a thin front for net_refuse_with(): message 11501 "
       "(read only) with status -ER_NETWORK for a file variable of a read-mode server, 11511 (not available) with the same status for a write-mode one - and net_gate()'s read-mode refusal is "
       "net_refuse_with(.., MSG_READ_ONLY, -ER_NETWORK), the same text and status",
       refuse != "" and refwith != "" and not re.search(r"net_call_raw\(|net_flush_pending\(|net_op\(|net_op_ex\(|k_call\(|k_run_program\(|load_object\(", refuse + refwith + lowerw)
       and ordered(refuse, "fvar->access.net.write", "net_refuse_with(fvar, what, write ? MSG_UNAVAILABLE : MSG_READ_ONLY, -ER_NETWORK)")
       and ordered(refwith, "fvar->type == NET_FILE", "server = fvar->access.net.server;", "net_lower_what(what, op", "net_set_message(msg_no, server, op", "return net_raise(status, entry);")
       and ordered(lowerw, "(what[i] >= 'A') && (what[i] <= 'Z')", "? (char)(what[i] - 'A' + 'a') : what[i];")
       and "#define MSG_READ_ONLY 11501" in nf and "#define MSG_UNAVAILABLE 11511" in nf and "#define MSG_TXN 11510" in nf
       and "net_refuse_with(fvar, what, MSG_READ_ONLY, -ER_NETWORK)" in fn("netfiles.c", "net_gate"), "")
    ck("NK4a net_close: the handler is run only under explicit_close (the CLOSE statement), the handle is cleared BEFORE anything is sent, a stale variable is not sent at all, and any other release (an unwind, a "
       "scope exit, kill_process) is only QUEUED - BASIC must not run where the e-stack may be gone",
       ordered(close_, "fvar->type != NET_FILE", "if (net_stale(fvar))", "fvar->access.net.handle = 0;", "if (explicit_close) {", "net_flush_pending();", "net_call_raw(NF_CLOSE", "} else if (net_pending_ct < NET_MAX_HANDLES) {",
               "net_pending[net_pending_ct++] = handle;")
       and not re.search(r"net_call_raw\(", close_[close_.find("} else if"):]), "")
    ck("NK4b net_stale is closed, not a NET_FILE, or from an earlier epoch; net_op asks it BEFORE the queue is flushed or the handler called (message 11494 for a stale handle); net_close_all moves the epoch on and "
       "empties the queue BEFORE it calls the handler (NF_CLOSEALL), and only if this process ever opened a remote file",
       ordered(stale, "fvar->type != NET_FILE", "access.net.handle <= 0", "access.net.epoch != net_epoch") and ordered(op_, "if (net_stale(fvar))", "MSG_BAD_HANDLE", "net_flush_pending();", "net_call_core(op")
       and ordered(closeall, "net_epoch++;", "net_pending_ct = 0;", "if (!net_used)", "net_call_raw(NF_CLOSEALL"), "")
    opn = nw
    ck("NK4c a NET_FILE is made LAST and only on success: the union is zeroed, the handle (1 to NET_MAX_HANDLES, digits only) is checked, then the epoch, the server name, the mode the handler reported (rc<7>) "
       "and the S.64 edit kind of the file's name (slice 3e), file_id -1, FV_NON_TXN, FV_RDONLY only when the handle is NOT write-mode, and the type - and `type = NET_FILE` occurs once, so no failed open "
       "leaves a variable the other statements would treat as remote; a read-mode handle is read only exactly as in slice 3c",
       ordered(opn, "(handle < 1) || (handle > NET_MAX_HANDLES)", "memset(&fvar->access, 0, sizeof(fvar->access));", "fvar->access.net.handle = (int16_t)handle;", "fvar->access.net.epoch = net_epoch;",
               "strcpy(fvar->access.net.server, server);", "fvar->access.net.write = rc.mode_write ? 1 : 0;", "fvar->access.net.edit_kind = (u_char)edit_kind_of_net_name(file);",
               "fvar->file_id = -1;", "fvar->flags |= FV_NON_TXN;", "if (!fvar->access.net.write)", "fvar->flags |= FV_RDONLY;", "fvar->type = NET_FILE;")
       and "FV_RDONLY" not in opn.replace("fvar->flags |= FV_RDONLY;", "")
       and len(re.findall(r"type\s*=\s*NET_FILE", nf)) == 1 and "hs[i] < '0') || (hs[i] > '9'" in opn, "")
    rd = fn("netfiles.c", "net_read")
    ck("NK4d net_read and net_readv answer an empty id with ER_IID WITHOUT calling the handler; an error is raised by net_raise with the message the handler gave unless the statement has ON ERROR, the ELSE branch is "
       "the remote STATUS() when the server sent one and ER_RNF otherwise; the handler's message numbers 11460, 11461 and 11496 are the permission class (ER_PERM), every other error ER_NETWORK",
       ordered(rd, "if (id_len < 1)", "return ER_IID;", "net_op(fvar, NF_READ") and ordered(fn("netfiles.c", "net_readv"), "if (id_len < 1)", "return ER_IID;", "net_op(fvar, NF_READV")
       and re.search(r"return \(rc->status > 0\) \? rc->status : else_status;", nf) is not None
       and re.search(r"case MSG_NO_GATE:\s*case MSG_NOT_LISTED:\s*case MSG_NO_CREDENTIAL:\s*return -ER_PERM;", nf) is not None and "return -ER_NETWORK;" in fn("netfiles.c", "net_error_status"), "")

    # ---- NK5. the VOC pointer
    i = vr.find('case type = "N"')
    case_n = vr[i:vr.find("\n         case 1", i)] if i >= 0 else ""
    chk = routine_body(vr, "check.n.pointer")
    ck("NK5 _voc_ref: an N pointer is its own case of the pointer loop (after F and Q, before the default); both names are trimmed and lower cased; the shape "
       "test is a gosub and a failure is ER$NAM; a dictionary (fno 3) is NOT refused any more (no ER$VNF in the case) - 'dict ' goes in front of the file name AFTER the shape test; the pathname returned is "
       "char(1) 'N' char(1) server char(1) file with status 0; NO kernel call and NO gate in the case (the gate is the session's, asked in C)",
       i > 0 and vr.find('case type = "Q"') < i < vr.find("\n         case 1", i)
       and ordered(case_n, "n.srv = downcase(trim(voc.rec<2>))", "n.file = downcase(trim(voc.rec<3>))", "gosub check.n.pointer", "if not(n.ok) then", "set.status ER$NAM", "return", "end",
                   "if fno = 3 then n.file = 'dict ':n.file", "pathname = char(1):'N':char(1):n.srv:char(1):n.file", "set.status 0", "return")
       and "ER$VNF" not in case_n
       and "kernel(" not in case_n and "K$NET" not in vr, repr(case_n[:120]))
    ck("NK5a check.n.pointer: a server name is 1 to 16 characters, a lower case LETTER first, then letters and digits; a file name is 1 to 63 lower case letters, digits and . _ - $ (no space: the 'dict ' of the "
       "DICT form is added by the case AFTER this test, NK17; no slash, so no pathname); n.ok starts true and only ever goes false",
       ordered(chk, "n.ok = @true", "'abcdefghijklmnopqrstuvwxyz'", "'0123456789'", "len(n.srv) < 1 or len(n.srv) > 16", "len(n.file) < 1 or len(n.file) > 63", "index(n.letters, n.srv[1,1], 1) = 0",
               "index(n.letters:n.digits, n.srv[n.k,1], 1) = 0", "index(n.letters:n.digits:'._-$', n.file[n.k,1], 1) = 0") and "n.ok = @true" not in chk[chk.find("n.ok = @true") + 12:]
       and chk.count("n.ok = @false") >= 5 and "/" not in re.sub(r"'[^']*'", "", chk), "")
    ck("NK5b the C side reads the encoded form the BASIC side writes: byte 0 is char(1), byte 1 is 'N', byte 2 is char(1), the server name runs to the next char(1) (1 to NET_SERVER_LEN), the file name is the rest "
       "(1 to NET_FILE_NAME_MAX, which is NET_FILE_MAX and the 5 characters of 'dict ' - the buffer holds that many - no second separator) - and a path that is not that is message 11508 and ER_NAM, never a call of the handler",
       ordered(nw, "(u_char)encoded_path[0] != 1", "encoded_path[1] != 'N'", "MSG_BAD_POINTER, \"it does not begin N\"", "return -ER_NAM;", "q = strchr(p, 1);", "if (q == NULL) {", "(n > NET_SERVER_LEN)",
               "(n > NET_FILE_NAME_MAX)", "strchr(p, 1) != NULL") and "u_char)path[0]==1" in fn("netfiles.c", "net_path_is_net").replace(" ", "")
       and re.search(r"#define\s+NET_FILE_NAME_MAX\s+\(NET_FILE_MAX\s*\+\s*5\)", nf) is not None and re.search(r"char\s+file\[NET_FILE_NAME_MAX\s*\+\s*1\];", nw) is not None
       and "(n > NET_FILE_MAX)" not in nw and "file[NET_FILE_MAX" not in nw, "")

    # ---- NK6. open_file, close, dio_close
    of = fn("op_dio1.c", "open_file")
    ck("NK6 open_file: the encoded path is recognised right after the VOC lookup, INSIDE the `if (map_name)` block (so OPEN by name only), BEFORE fullpath(), the OS path test, the transaction cache and the "
       "file table; OPENPATH and OPENTEMP call open_file(FALSE) and the kernel never calls net_open or net_path_is_net anywhere else",
       ordered(of, "get_voc_file_reference_ex(voc_name, open_dict, mapped_name, vflags, TRUE)", "if (net_path_is_net(mapped_name)) {", "net_open(fvar, mapped_name)", "goto net_file_opened;", "fullpath(pathname, mapped_name);",
               "os_path_open_ok(", "txn_open(", "dh_open(", "get_file_entry(")
       and inside(of, "if (map_name) {", "if (net_path_is_net(mapped_name))") and "open_file(FALSE)" in fn("op_dio1.c", "op_openpath") and "open_file(FALSE)" in fn("op_dio1.c", "op_opentemp")
       and not re.search(r"net_", fn("op_dio1.c", "op_openpath")) and not re.search(r"net_", fn("op_dio1.c", "op_opentemp"))
       and sum(t.count("net_open(") for k, t in c.items() if (k.endswith(".c") or k.startswith("c:")) and k != "netfiles.c") == 1
       and sum(t.count("net_path_is_net(") for k, t in c.items() if (k.endswith(".c") or k.startswith("c:")) and k != "netfiles.c") == 1, "")
    ck("NK6a a failed net_open keeps the file variable out of the file table (net_open sets the type only on success) and shows ITS message: the status is the net_open status, the error is raised from "
       "net_message() BEFORE the generic 'Error opening file' (message 1402), and only without ON ERROR",
       ordered(of, "net_status = net_open(fvar, mapped_name);", "process.status = net_status;", "net_failed = (net_status < 0);", "goto exit_op_open;", "net_file_opened:", "exit_op_open:",
               "if (net_failed)", "k_error(\"%s\", net_message());", "k_error(sysmsg(1402)") and "!(op_flags & P_ON_ERROR)" in of[of.find("exit_op_open:"):of.find("if (net_failed)")], "")
    dc, oc = fn("op_dio1.c", "dio_close"), fn("op_dio1.c", "op_close")
    arm = dc[dc.find("case NET_FILE:"):dc.find("break;", dc.find("case NET_FILE:")) + 6] if "case NET_FILE:" in dc else ""
    ck("NK6b dio_close has a NET_FILE arm that does one thing, net_close(fvar) - the file table block above it runs only for file_id > 0 - and the CLOSE statement sets explicit_close around the release (and clears "
       "it after), which is the only moment net_close talks to the server",
       arm.replace("\n", " ").count("net_close(fvar);") == 1 and arm.count(";") == 2 and "if (fno > 0)" in dc[:dc.find("case NET_FILE:")] and ordered(oc, "explicit_close = TRUE;", "k_release(descr);", "explicit_close = FALSE;")
       and ordered(close_, "if (explicit_close) {", "explicit_close = FALSE;", "net_call_raw(NF_CLOSE"), repr(arm))

    # ---- NK7. every census REFUSE site refuses first
    bad, seen = [], 0
    for (fname, name), (how, extra) in sorted(NK_REFUSE.items()):
        body = fn(fname, name)
        seen += 1
        if not body:
            bad.append("%s/%s: function not found" % (fname, name))
            continue
        call = "net_refuse(" if how == "R" else "refuse_net_file("
        i = body.find(call)
        if i < 0:
            bad.append("%s/%s: no %s" % (fname, name, call))
            continue
        if how == "R" and not (0 <= body.find("NET_FILE") < i):
            bad.append("%s/%s: net_refuse is not behind a NET_FILE test" % (fname, name))
        j = [body.find(x) for x in NK_DANGER + tuple(extra) if body.find(x) >= 0]
        if j and min(j) < i:
            bad.append("%s/%s: %r comes before the refusal" % (fname, name, body[min(j):min(j) + 24]))
    ck("NK7 THE CENSUS: each of the %d statements the census of 17 Oct 26 says REFUSE (CONFIGURE.FILE, the locking reads, READVU, CLEARFILE, DELETE, WRITE, WRITEV, "
       "RECORDLOCKU/L, RELEASE and RLSFILE, the six index operations that change an index or read its tree (AKREAD, AKWRITE, AKDELETE, CLEAR.AK, AKENABLE, AKMAP), the internal FCONTROL.INT (the public FCONTROL() is the server's since S.73 item 3), ANALYSE.FILE) calls net_refuse (or refuse_net_file) behind a NET_FILE test and BEFORE the first read or "
       "write of the file table, a lock, a select list or an edit-gate decision in the function (SELECT and SELECTV are not in it since slice 3d: NK14, NK15; nor are the six index QUERY statements since S.73 item 3 D1: NK18; nor, since S.72, FILELOCK, "
       "FILEUNLOCK, GETLOCKS and RECORDLOCKED(), which call neither in their own body - the gate of net_filelock_step, net_fileunlock and, since S.72b, net_recordlocked decides: NK_LOCKSITES, S72a to S72i)" % seen, not bad and seen == 18, repr(bad))
    pf = fn("dh_misc.c", "pub_fcontrol")
    of_ = fn("dh_misc.c", "op_fcontrol")
    ck("NK7a S.73 item 3: pub_fcontrol answers a NET_FILE through net_fcontrol(fvar, action, value, len, &result) - the qualifier read as text, the result and STATUS() (net_last_reply_status) handed back - and jumps to "
       "its own exit (exit_pub_fcontrol, which pops three operands and pushes the result); it calls NO net_refuse; op_fcontrol answers FC_NET_CREATE (for any local file variable) and FC_NET_ADMIN (for a NET_FILE) "
       "through net_create_file / net_admin BEFORE its net_refuse, and still refuses every other key of a NET_FILE; the two keys are 10 and 11 in keys.h and FCI$NET.ADMIN 10 and FCI$NET.CREATE 11 in int$keys.h",
       "net_refuse(" not in pf and re.search(r"if \(fvar->type == NET_FILE\) \{.*?net_fcontrol\(fvar, action, net_val, net_vlen, &net_out\) == 0.*?goto exit_pub_fcontrol;", pf, re.S) is not None
       and "exit_pub_fcontrol:" in pf and ordered(of_, "FC_NET_ADMIN", "net_create_file(", "net_admin(", "goto exit_op_fcontrol;", "net_refuse(fvar, \"FCONTROL\")")
       and re.search(r"#define\s+FC_NET_ADMIN\s+10\b", c["keys.h"]) is not None and re.search(r"#define\s+FC_NET_CREATE\s+11\b", c["keys.h"]) is not None
       and re.search(r"\$define\s+FCI\$NET\.ADMIN\s+10\b", c["bp:int$keys.h"]) is not None and re.search(r"\$define\s+FCI\$NET\.CREATE\s+11\b", c["bp:int$keys.h"]) is not None, "")
    badg = []
    for fname, name in NK_GUARD:
        body = fn(fname, name)
        i, j = body.find("NET_FILE"), body.find("FPtr(")
        if not body or i < 0 or (j >= 0 and j < i):
            badg.append("%s/%s" % (fname, name))
    ck("NK7a the census sites that read the file table to PRINT or to LOG (FILEINFO, the file status, the permissions log, the process dump) test for NET_FILE BEFORE the first FPtr(: " + ", ".join(n for _f, n in NK_GUARD),
       not badg, repr(badg))
    hdr = fn("op_dio3.c", "refuse_net_file")
    rc_ = fn("op_dio3.c", "read_record")
    ck("NK7b the helper refuse_net_file (slice 3e: it takes the KIND of statement): not a NET_FILE is FALSE and nothing else happens; for one it hands net_gate ONLY the ON ERROR bit (and the statement's own "
       "op_flags, for CREATING.SEQKEY), the kind and the statement's name, returns FALSE when the gate passes it, otherwise takes the negative status (never a non-negative one), and without ON ERROR still "
       "raises net_gate's own message (net_message()) itself if net_gate returned; READU / READL / MATREADU / MATREADL are asked in read_record behind (type NET_FILE and P_REC_LOCKS) with NETG_LOCK and a "
       "NET_FILE's transaction id is forced to 0 (txn_read would read the file table); READ and MATREAD have their own `case NET_FILE:` that calls net_read",
       ordered(hdr, "fvar->type != NET_FILE", "return FALSE;", "process.op_flags = op_flags & P_ON_ERROR;", "st = net_gate(fvar, kind, op_flags, what);", "process.op_flags = 0;", "if (st == 0)", "return FALSE;",
               "(st < 0) ? st : -ER_PERM", "k_error(\"%s\", net_message())")
       and "net_refuse(" not in hdr
       and re.search(r"refuse_net_file\(FILE_VAR\s*\*\s*fvar,\s*u_int16_t\s+op_flags,\s*const\s+char\s*\*\s*what,\s*int\s+kind\)\s*\{", c["op_dio3.c"]) is not None
       and "(fvar->type == NET_FILE) && (op_flags & P_REC_LOCKS)" in rc_ and "(fvar->type == NET_FILE)) ? 0 : process.txn_id" in rc_ and ordered(rc_, "case NET_FILE: {", "net_read(fvar, id, id_len, &net_rec)"), "")
    ro = fn("op_dio3.c", "op_readv")
    ck("NK7c READV of a NET_FILE never runs the recursive _readv (which would READ, and cut the field in BASIC): the NET branch is the first branch, reads through net_readv, refuses READVU / READVL, and "
       "dismisses the same four operands the local branch does", ordered(ro, "if (fvar->type == NET_FILE) {", "refuse_net_file(", "net_readv(fvar, id, id_len, field_no, &net_str)", "} else if (field_no != 0) {", "k_recurse(pcode_readv")
       and ro[ro.find("if (fvar->type == NET_FILE) {"):ro.find("} else if (field_no != 0) {")].count("k_dismiss()") == 3, "")
    fi = fn("op_dio2.c", "op_fileinfo")
    branch = fi[fi.find("if (ftype == NET_FILE) {"):fi.find("fptr = FPtr(fvar->file_id);")] if "if (ftype == NET_FILE) {" in fi else ""
    ck("NK7d FILEINFO of a NET_FILE is answered BEFORE fptr = FPtr(file_id): the keys about the variable (VOCNAME, READONLY, NON.TXN, NETFILE, FILENO, TXN.UPDATE, INDEX.SCAN, ID) are answered from it, the three "
       "that write the file table (FL_EXCLUSIVE, FL_STATS_ON, FL_STATS_OFF) are refused, and every other key goes to net_fileinfo; the branch reads no FPtr",
       branch != "" and "FPtr(" not in branch and all(k in branch for k in ("case FL_VOCNAME:", "case FL_READONLY:", "case FL_NON_TXN:", "case FL_NETFILE:", "case FL_FILENO:", "case FL_TXN_UPDATE:", "case FL_INDEX_SCAN:",
                                                                         "case FL_ID:", "case FL_EXCLUSIVE:", "case FL_STATS_ON:", "case FL_STATS_OFF:", "net_refuse(fvar, \"FILEINFO\")", "default:", "net_fileinfo(fvar, key)")), "")

    # ---- NK8. nothing that takes a file variable has been left undecided
    found = set()
    for k, t in c.items():
        if k.endswith(".c") or k.startswith("c:"):
            for name, body in c_functions(t).items():
                if "k_get_file(" in body or "data.fvar" in body:
                    found.add((k[2:] if k.startswith("c:") else k, name))
    decided = set(NK_REFUSE) | set(NK_GUARD) | set(NK_SAFE) | NK_OTHER | NK_SELECT | NK_INDEXQ | NK_INDEXQ_HELPERS | NK_LOCKSITES | NK_FCONTROL_SITES
    safe_bad = [(f, n) for (f, n), tok in sorted(NK_SAFE.items()) if tok not in fn(f, n)]
    ck("NK8 NOTHING IS LEFT UNDECIDED: every kernel function that is given a file variable (k_get_file or ->data.fvar) is in the census table of this check - refused, guarded, answering any other kind of file by "
       "its own type test (the sequential family, GETPORT, SETPORT, GROUPSTAT, SET.TRIGGER, MARK.MAPPING - the token is still in each), served (the four lock sites of S.72: FILELOCK, FILEUNLOCK, GETLOCKS, "
       "RECORDLOCKED(), in NK_LOCKSITES), or listed as supported / ignored - so a NEW function that reads a file "
       "variable fails here until someone decides what it does with a remote file (%d found, %d decided)" % (len(found), len(decided)),
       not (found - decided) and not safe_bad, repr((sorted(found - decided), safe_bad)))

    # ---- NK9. messages and the build
    m7, m8 = srcs.get("msg:11507"), srcs.get("msg:11508")
    used = {int(x) for x in re.findall(r"#define\s+MSG_\w+\s+(\d+)", nf)}
    ck("NK9 the kernel's own messages: 11507 (the handler could not be used: %1) and 11508 (the VOC entry is not valid: %1) are one line each with ONE place; every message number netfiles.c names exists as a "
       "one-line message (11460, 11461, 11494, 11496, 11500, 11501, 11503, 11507, 11508 and, since slice 3e, 11510 (a transaction is open) and 11511 (not available on a write-mode server)); the "
       "S.64 edit-gate messages net_gate() raises are 11404 + the kind (11405 to 11407) and exist; the kernel cites no number the handler's block does not hold apart from 11507, 11508 and 11511",
       m7 is not None and m8 is not None and m7.count("\n") <= 1 and m8.count("\n") <= 1 and "%1" in m7 and "%1" in m8 and not re.search(r"%[2-9]", m7 + m8)
       and used == {11460, 11461, 11494, 11496, 11500, 11501, 11503, 11507, 11508, 11510, 11511} and all(os.path.exists(os.path.join(MSGDIR, str(n))) for n in used | {11405, 11406, 11407})
       and "net_set_message(11404 + ek" in fn("netfiles.c", "net_gate"), repr(sorted(used)))
    src_list = srcs["gpl.src"].split()
    ck("NK10 the Makefile builds from gpl.src: `netfiles` is in it exactly once, after `messages`, and gplsrc/netfiles.c exists; sd.h no longer says NETFILES.C was removed",
       src_list.count("netfiles") == 1 and src_list.index("netfiles") == src_list.index("messages") + 1 and os.path.exists(os.path.join(GPLSRC, "netfiles.c"))
       and "NETFILES.C removed" not in srcs["sd.h"], "")

    # ---- NK11. the suite and the map
    tags = set(re.findall(r'km\("([a-z0-9]+)"', suite))
    nums = {int(x) for x in re.findall(r"\bmsg\((\d+)", suite)}
    rules = map_rules(rm)
    unmapped = []
    for path in NK_MAP_FILES:
        first = next((s for pat, s in rules if fnmatch.fnmatchcase(path, pat)), None)
        if first is None or "netfile" not in first:
            unmapped.append(path)
    ck("NK11 the suite sandbox-netfile.py has the section kernel (before gaps), its refusal matrix names every statement of the census (%d tags, %s missing), the fake's allowed request types are exactly "
       "login, account, open, close, read and quit, every message number the section expects is a message of the tree, and the map sends every kernel file of this slice to the netfile suite "
       "(%s unmapped)" % (len(tags), sorted(set(NK_SUITE_MATRIX) - tags), unmapped),
       '("kernel", kernel_section), ("mustlock", mustlock_section), ("gaps", gaps_section)' in suite and not (set(NK_SUITE_MATRIX) - tags) and "KALLOWED = {47, 48, 3, 4, 5, 6, 1}" in suite and "except subprocess.TimeoutExpired:" in suite
       and nums and all(os.path.exists(os.path.join(MSGDIR, str(n))) for n in nums) and not unmapped, repr((sorted(set(NK_SUITE_MATRIX) - tags), unmapped, sorted(nums))))
    texts_ = {n: (srcs.get(n) or "") for n in ("netfiles.c", "descr.h", "sd.h", "op_dio1.c", "op_dio2.c", "op_dio3.c", "op_dio4.c", "op_lock.c", "dh_ak.c", "dh_misc.c", "analyse.c", "k_error.c", "pdump.c",
                                                 "bp:_voc_ref", "sandbox-netfile.py")}
    lack = [n for n, t in texts_.items() if not re.search(r"17 Oct 26 dm\s+S\.65 slice 3c", t)]
    ck("NK12 the dated history lines are there: every file slice 3c changed says `S.65 slice 3c` (%d files), and this check's own file says so" % len(texts_), not lack and "slice 3c" in (__doc__ or ""), repr(lack))


def checks_3d(srcs, c, ck):
    """S.65 slice 3d: SELECT and SELECTV of a remote file, the dictionary of one, and the FILEINFO keys a query asks.  Text only: the section kernel of
    sandbox-netfile.py runs the statements, and `make` is the compiler."""
    nf, dsc, kh, skh = c["netfiles.c"], c["descr.h"], c["keys.h"], c["syscom/keys.h"]
    vr, nfh = c["bp:_voc_ref"], c["bp:netfile.h"]

    def ct(fname):
        return c.get(fname) or c.get("c:" + fname, "")

    def fn(fname, name):
        return c_functions(ct(fname)).get(name, "")

    # ---- NK13. net_select
    ns = fn("netfiles.c", "net_select")
    cdef = {m.group(1): int(m.group(2)) for m in re.finditer(r"#define\s+(NF_[A-Z_]+)\s+(\d+)\b", nf)}
    bdef = {m.group(1): int(m.group(2)) for m in re.finditer(r"\$define\s+(NF\$[A-Z.]+)\s+(-?\d+)", nfh)}
    ok_at = ns.find("return status;")                      # the end of the two failure returns: nothing may be set before it
    ck("NK13 net_select: NF_SELECT is netfile.h's NF$SELECT (6); the statement's flags are taken FIRST (u_int16_t entry = process.op_flags), the request goes through net_op (never the handler directly), "
       "process.op_flags is given back, a negative status is raised by net_raise with THAT entry (so only a statement without ON ERROR stops, exactly as net_read) and a positive one is the ELSE branch; "
       "*ids and *count are each set once, after both returns, so a failure leaves the caller's values alone; the ids are counted by their field marks (an empty answer is 0, not 1)",
       cdef.get("NF_SELECT") == bdef.get("NF$SELECT") == 6 and ns != ""
       and ordered(ns, "u_int16_t entry = process.op_flags;", "net_op(fvar, NF_SELECT", "process.op_flags = entry;", "if (status < 0)", "return net_raise(status, entry);", "if (status > 0)",
                   "return status;", "net_take_string(&out)", "k_release(&out);", "== FIELD_MARK", "n++;", "*ids = s;", "*count = n;", "return 0;")
       and ns.count("net_raise(") == 1 and ns.count("*ids =") == 1 and ns.count("*count =") == 1 and 0 < ok_at < ns.find("*ids =") and ok_at < ns.find("*count =")
       and not re.search(r"net_call_raw\(|net_flush_pending\(|k_call\(|load_object\(|net_refuse\(", ns)
       and re.search(r"int32_t\s+n\s*=\s*0;", ns) is not None and re.search(r"if \(s != NULL\) \{\s*n = 1;", ns) is not None, repr(ns[:80]))
    # ---- NK14. SELECT
    sel = fn("op_dio4.c", "op_select")
    d4 = ct("op_dio4.c")
    first_net = sel.find("if (fvar->type == NET_FILE)")
    danger = [sel.find(x) for x in NK_DANGER if sel.find(x) >= 0]
    helper = fn("op_dio4.c", "net_select_with_flags")
    sl = fn("op_dio4.c", "store_select_list")
    ck("NK14 SELECT of a NET_FILE: the ids are asked of the server (net_select_with_flags) BEFORE end_select, clear_select or anything that reads the file table, so an error or an ELSE leaves the target list alone "
       "(the status is kept, the stack is cleaned and the function leaves by select_status); only then does `case NET_FILE:` of the select switch call store_select_list (the same function dir_select ends with) "
       "UNCONDITIONALLY - no `if (net_ids != NULL)` in front of it - and store_select_list sets SELECT.COUNT first and returns early for a NULL list only AFTER that, so an empty remote file gives @SELECTED 0; "
       "the helper hands net_select ONLY the statement's ON ERROR bit and clears process.op_flags again; net_select is called from the helper and from nowhere else in the kernel; SELECT no longer calls net_refuse",
       sel != "" and 0 <= first_net < sel.find("net_select_with_flags(fvar, op_flags, &net_ids, &net_count)") and (not danger or first_net < min(danger))
       and ordered(sel, "if (fvar->type == NET_FILE)", "net_select_with_flags(fvar, op_flags, &net_ids, &net_count)", "if (net_st != 0) {", "process.status = net_st;", "k_pop(1);", "k_dismiss();",
                   "goto select_status;", "end_select(list_no);", "clear_select(list_no);", "switch (fvar->type) {", "case NET_FILE:", "store_select_list(list_no, net_ids, net_count);")
       and re.search(r"case NET_FILE:\s*store_select_list\(list_no, net_ids, net_count\);\s*break;", sel) is not None      # no `if (net_ids != NULL)` guard: an empty file must still set the count
       and ordered(sl, "SYSCOM_SELECT_COUNT", "descr->data.value = record_count;", "if (head == NULL)", "return;", "SYSCOM_SELECT_LIST", "descr->data.str.saddr = head;")
       and sl.count("if (head == NULL)") == 1 and sl.count("return;") == 1
       and "net_refuse(" not in sel and helper != "" and ordered(helper, "process.op_flags = op_flags & P_ON_ERROR;", "net_select(fvar, ids, count)", "process.op_flags = 0;", "return st;")
       and sum(t.count("net_select(") for k, t in c.items() if (k.endswith(".c") or k.startswith("c:")) and k != "netfiles.c") == 1
       and "store_select_list(list_no, head, record_count)" in fn("op_dio4.c", "dir_select")
       and c_proto(d4, "net_select_with_flags") is not None and c_proto(d4, "net_select_with_flags") == c_header(d4, "net_select_with_flags")
       # S.73 item 3 D1 (21 Oct 26): store_select_list is exported (the index scans of dh_ak.c end with it too): no Private prototype in op_dio4.c, ONE in sd.h that says what the definition says
       and c_proto(d4, "store_select_list") is None and c_proto(ct("sd.h"), "store_select_list") is not None
       and c_proto(ct("sd.h"), "store_select_list") == c_header(d4, "store_select_list"), repr(sel[:80]))
    # ---- NK15. SELECTV
    sv = fn("op_dio4.c", "op_selectv")
    i0 = sv.find("if (fvar->type == NET_FILE)")
    i1 = sv.find("net_select_with_flags(fvar, op_flags, &net_ids, &net_count)")
    i2 = sv.find("goto selectv_status;", i1) if i1 >= 0 else -1
    netb = sv[i0:i2] if 0 <= i0 < i1 < i2 else ""
    danger = [sv.find(x, i0) for x in NK_DANGER if i0 >= 0 and sv.find(x, i0) >= 0]
    ck("NK15 SELECTV of a NET_FILE: the NET branch asks the server and leaves by selectv_status BEFORE the file type switch (list 11 and the local selects are never reached); nothing touches tgt_descr between the "
       "branch's opening and the call, and AFTER the call the target is found again from the e-stack (the handler runs BASIC and can move it, as op_read does) and made an empty SELLIST; on success the ids are "
       "the list and their count is its offset (both only when there are ids: a NULL list is not touched), and @SELECTED is the count on EVERY success, an empty file included; an error or an ELSE leaves the empty list and the status; SELECTV no longer calls net_refuse",
       sv != "" and netb != "" and "tgt_descr" not in netb[:netb.find("net_select_with_flags(")]
       and ordered(netb, "net_select_with_flags(fvar, op_flags, &net_ids, &net_count);", "tgt_descr = e_stack - 1;", "while (tgt_descr->type == ADDR)", "tgt_descr = tgt_descr->data.d_addr;",
                   "InitDescr(tgt_descr, SELLIST);", "tgt_descr->data.str.saddr = NULL;", "if (net_st != 0) {", "process.status = net_st;", "} else {", "if (net_ids != NULL) {", "tgt_descr->data.str.saddr = net_ids;",
                   "net_ids->offset = net_count;", "Element(process.syscom, SYSCOM_SELECTED)", "descr->data.value = net_count;")
       and re.search(r"\} else \{\s*if \(net_ids != NULL\) \{\s*tgt_descr->data\.str\.saddr = net_ids;\s*net_ids->offset = net_count;\s*\}\s*"
                     r"descr = Element\(process\.syscom, SYSCOM_SELECTED\);\s*descr->data\.value = net_count;\s*\}\s*$", netb) is not None      # @SELECTED on EVERY success, outside the NULL test
       and i2 < sv.find("switch (fvar->type) {", i2) and "net_refuse(" not in sv and not [d for d in danger if d < i2], repr(netb[:80]))
    # ---- NK16. FILEINFO answers three more keys of a remote file
    fi = fn("op_dio2.c", "op_fileinfo")
    branch = fi[fi.find("if (ftype == NET_FILE) {"):fi.find("fptr = FPtr(fvar->file_id);")] if "if (ftype == NET_FILE) {" in fi else ""

    def seg(label):
        j = branch.find(label)
        return branch[j:branch.find("goto set_integer;", j)] if j >= 0 else ""
    tdef = {m.group(1): int(m.group(2)) for m in re.finditer(r"#define\s+(FL_TYPE_[A-Z]+)\s+(\d+)\b", kh)}
    bt = {m.group(1): int(m.group(2)) for m in re.finditer(r"\$define\s+(FL\$TYPE\.[A-Z]+)\s+(\d+)", skh)}
    ck("NK16 FILEINFO of a NET_FILE: FL_TYPE answers FL_TYPE_NET (7, its own number: FL_TYPE_NET is defined in gplsrc/keys.h and FL$TYPE.NET in sdsys/syscom/keys.h with the same value and no other type uses 7), "
       "FL_COLLECTION answers 0, FL_FLAGS answers DHF_NOCASE for an $internal program and 0 for any other - each in the NET branch, which has no FPtr( and comes before fptr = FPtr(file_id), and each ahead of "
       "`default:` (the server is not asked for them)",
       branch != "" and "FPtr(" not in branch and tdef.get("FL_TYPE_NET") == bt.get("FL$TYPE.NET") == 7 and sorted(tdef.values()).count(7) == 1 and sorted(bt.values()).count(7) == 1
       and ordered(branch, "case FL_TYPE:", "n = FL_TYPE_NET;", "goto set_integer;", "case FL_COLLECTION:", "n = 0;", "goto set_integer;", "case FL_FLAGS:",
                   "n = (process.program.flags & HDR_INTERNAL) ? DHF_NOCASE : 0;", "goto set_integer;", "default:", "net_fileinfo(fvar, key)")
       and re.fullmatch(r"case FL_TYPE:\s*n = FL_TYPE_NET;\s*", seg("case FL_TYPE:")) is not None and re.fullmatch(r"case FL_COLLECTION:\s*n = 0;\s*", seg("case FL_COLLECTION:")) is not None
       and re.fullmatch(r"case FL_FLAGS:\s*n = \(process\.program\.flags & HDR_INTERNAL\) \? DHF_NOCASE : 0;\s*", seg("case FL_FLAGS:")) is not None
       and branch.count("case FL_TYPE:") == 1 and branch.count("case FL_COLLECTION:") == 1 and branch.count("case FL_FLAGS:") == 1, repr((tdef, bt)))
    # ---- NK18. the index QUERY statements of a remote file ask the server (S.73 item 3 D1, 21 Oct 26; before it INDICES was the null string and the rest were refused)
    ix1, ix2 = fn("dh_ak.c", "op_indices1"), fn("dh_ak.c", "op_indices2")
    sx, sxv, aks, sap = (fn("dh_ak.c", n) for n in ("op_selindx", "op_selindxv", "akscan", "setakpos"))
    hsel, hsplit, hscan = (fn("dh_ak.c", n) for n in ("net_selindex", "net_split_scan", "net_akscan"))
    niq = fn("netfiles.c", "net_index_query")
    bad18 = []
    for (fname, name) in sorted(NK_INDEXQ):
        body = fn(fname, name)
        i = body.find("NET_FILE")
        j = [body.find(x) for x in NK_DANGER if body.find(x) >= 0]
        if not body or i < 0 or (j and min(j) < i) or re.search(r"net_refuse\(|refuse_net_file\(", body):
            bad18.append("%s/%s" % (fname, name))
    ck("NK18 THE SIX INDEX QUERY SITES (INDICES both forms, SELECTINDEX both, SELECTLEFT / SELECTRIGHT, SETLEFT / SETRIGHT: NK_INDEXQ) refuse nothing and ask the server: each tests NET_FILE BEFORE the first read "
       "of the file table, a lock or a select list, and none calls net_refuse or refuse_net_file; INDICES(f) and INDICES(f, name) call net_index_query (what 1 and 2) in their NET arm, dismiss their operands AFTER the "
       "call (the handler runs BASIC and can move the stack) and push the answer as a STRING, before the DYNAMIC_FILE code; SELECTINDEX, SELECTLEFT / SELECTRIGHT test the type before end_select and clear_select and "
       "hand over to net_selindex (FALSE for the values, TRUE for the ids) and net_akscan; SETLEFT / SETRIGHT call it with 5 and 6, keep the server's STATUS() in process.status, free the answer and dismiss the file and "
       "the name before the DYNAMIC_FILE test",
       not bad18 and len(NK_INDEXQ) == 6 and ix1 != "" and ix2 != ""
       and ordered(ix1, "if (fvar->type == NET_FILE) {", "net_index_query(fvar, 1, \"\", 0, &tgt, &net_st);", "k_dismiss();", "InitDescr(e_stack, STRING);", "(e_stack++)->data.str.saddr = tgt;", "return;",
                   "k_dismiss();", "switch (fvar->type) {", "case DYNAMIC_FILE:")
       and ordered(ix2, "if (fvar->type == NET_FILE) {", "k_get_c_string(e_stack - 1, index_name, MAX_AK_NAME_LEN)", "net_index_query(fvar, 2, index_name, nlen, &tgt, &net_st);", "k_dismiss();", "k_dismiss();",
                   "(e_stack++)->data.str.saddr = tgt;", "return;", "if (fvar->type == DYNAMIC_FILE) {")
       and ordered(sx, "InvalidSelectListNo(list_no)", "if (descr->data.fvar->type == NET_FILE) {", "net_selindex(FALSE, list_no);", "return;", "end_select(list_no);", "clear_select(list_no);")
       and ordered(sxv, "if (fvar->type == NET_FILE) {", "net_selindex(TRUE, list_no);", "return;", "end_select(list_no);", "clear_select(list_no);")
       and ordered(aks, "if (descr->data.fvar->type == NET_FILE) {", "net_akscan(right, list_no);", "return;", "end_select(list_no);", "clear_select(list_no);")
       and ordered(sap, "if (fvar->type == NET_FILE) {", "net_index_query(fvar, right ? 6 : 5, net_name, net_len, &net_ans, &net_st);", "s_free(net_ans);", "process.status = net_st;",
                   "k_dismiss();", "k_dismiss();", "return;", "if (fvar->type != DYNAMIC_FILE)"), repr(bad18))
    ck("NK18a net_selindex and net_akscan (dh_ak.c; Private): the server is asked FIRST (net_index_query, what 3 or 4 and 7 or 8) and the select list, the key variable and @SELECTED are touched only after it answered - an "
       "error is raised before (net_raise longjmps); the ids of a status other than 0 are freed (an unknown index is an empty list and STATUS() 1); the list is ended, cleared and stored through store_select_list; "
       "STATUS() is the server's; the operands are dismissed AFTER the call and @SELECTED is set last; net_split_scan cuts the answer at its FIRST field mark into the key and the ids, counts the ids, frees the "
       "answer; none of the three reads the file table (no FPtr(, access.dh or lock)",
       hsel != "" and hscan != "" and hsplit != ""
       and ordered(hsel, "net_index_query(fvar, with_value ? 4 : 3, cbuf, clen, &ids, &net_st);", "if ((net_st != 0) && (ids != NULL)) {", "s_free(ids);", "end_select(list_no);", "clear_select(list_no);",
                   "store_select_list(list_no, ids, count);", "process.status = net_st;", "k_pop(1);", "k_dismiss();", "SYSCOM_SELECTED", "descr->data.value = count;")
       and ordered(hscan, "net_index_query(fvar, right ? 8 : 7, name, nlen, &ans, &net_st);", "if (net_st == 0)", "net_split_scan(ans, &key, &ids, &count);", "s_free(ans);", "end_select(list_no);",
                   "clear_select(list_no);", "key_descr = e_stack - 2;", "key_descr->type != UNASSIGNED", "store_select_list(list_no, ids, count);", "process.status = net_st;", "k_pop(1);", "k_dismiss();",
                   "SYSCOM_SELECTED", "descr->data.value = count;")
       and ordered(hsplit, "ts_init(key, 64);", "c->data[i] == FIELD_MARK", "(void)ts_terminate();", "ts_init(ids, MAX_STRING_CHUNK_SIZE);", "(void)ts_terminate();", "(*count)++;", "s_free(ans);")
       and hsel.count("clear_select(list_no)") == 1 and hsel.count("end_select(list_no)") == 1 and hscan.count("clear_select(list_no)") == 1 and hscan.count("end_select(list_no)") == 1
       and not re.search(r"FPtr\(|access\.dh|lock_record\(|net_refuse\(|refuse_net_file\(", hsel + hscan + hsplit), "")
    ck("NK18b net_index_query (netfiles.c): NF_INDEXQ is netfile.h's NF$INDEXQ (24); the statements have no ON ERROR clause, so process.op_flags is cleared first and an error is always raised; ONE request through "
       "net_op_ex (never the handler directly, never net_refuse); an ELSE answer is not one a statement can use and is raised as an error; a negative status is raised by net_raise; the server's STATUS() "
       "(net_reply_status) and the answer (net_take_string) are handed back only AFTER the raise, so a failure leaves the caller's values at 0 and NULL; it is exported, defined once and prototyped in sd.h (NK2)",
       niq != "" and re.search(r"#define\s+NF_INDEXQ\s+24\b", nf) is not None and bdef.get("NF$INDEXQ") == 24 and niq.count("net_op_ex(") == 1 and "net_refuse(" not in niq
       and niq.count("*server_st =") == 2 and niq.count("*answer =") == 2      # each set twice: to its null at the top, and once from the reply after the raise
       and ordered(niq, "*answer = NULL;", "*server_st = 0;", "process.op_flags = 0;", "net_op_ex(fvar, NF_INDEXQ", "if (status > 0) {", "status = -ER_NETWORK;", "if (status < 0)", "return net_raise(status, 0);",
                   "*server_st = net_reply_status;", "*answer = net_take_string(&out);", "k_release(&out);", "return 0;"), "")
    # ---- NK17. the DICT form (NK18 above: INDICES; the record cache and the gate's close are checks_3e, NK19 to NK25)
    i = vr.find('case type = "N"')
    case_n = vr[i:vr.find("\n         case 1", i)] if i >= 0 else ""
    chk = routine_body(vr, "check.n.pointer")
    ck("NK17 the DICT form of a remote file: the case adds 'dict ' (4 letters and one space, the 5 characters NET_FILE_NAME_MAX allows beyond NET_FILE_MAX) to the file name only for fno = 3 (once, on a line of its "
       "own, after the failure return of the shape test and before the pathname is built); check.n.pointer still allows no space, so a VOC entry cannot hold the prefix itself; the dictionary is not refused",
       case_n != "" and case_n.count("fno") == 1 and case_n.count("'dict '") == 1 and re.search(r"^\s*if fno = 3 then n\.file = 'dict ':n\.file\s*$", case_n, re.M) is not None
       and len("dict ") == 5 and "ER$VNF" not in case_n and chk != "" and "' '" not in chk and "dict" not in chk
       and ordered(case_n, "gosub check.n.pointer", "set.status ER$NAM", "return", "if fno = 3 then n.file = 'dict ':n.file", "pathname = ")
       and re.search(r"#define\s+NET_FILE_NAME_MAX\s+\(NET_FILE_MAX\s*\+\s*5\)", nf) is not None and re.search(r"#define\s+NET_FILE_MAX\s+63\b", nf) is not None, repr(case_n[:120]))


def checks_3e(srcs, c, ck):
    """S.65, 18 Oct 26: the record cache of netfiles.c (NK19-NK24) and K_NET closing the remote files when the account scope changes (NK25).  Text only: the
    cache's behaviour (a hit, an expiry, a copy) is sandbox-netfile.py's, and `make` is the compiler."""
    nf, kn = c["netfiles.c"], c["op_kernel.c"]

    def fn(name):
        return c_functions(nf).get(name, "")

    # ---- NK19. the constants, the include and the entry
    ent = re.search(r"typedef struct \{(.*?)\} NET_CACHE_ENTRY;", nf, re.S)
    ent = ent.group(1) if ent else ""
    ck("NK19 THE RECORD CACHE's constants: NET_CACHE_SLOTS 64, NET_CACHE_TTL 2 (seconds), NET_CACHE_REC_MAX 32768; <time.h> is included BEFORE sd.h; an entry holds used, absent, the handle AND the epoch AND the id "
       "length AND the id (MAX_ID_LEN + 1 bytes), the record chain and the time; the table is NET_CACHE_SLOTS entries and the ring cursor starts at 0",
       re.search(r"#define\s+NET_CACHE_SLOTS\s+64\b", nf) is not None and re.search(r"#define\s+NET_CACHE_TTL\s+2\b", nf) is not None and re.search(r"#define\s+NET_CACHE_REC_MAX\s+32768\b", nf) is not None
       and ordered(nf, "#include <time.h>", '#include "sd.h"') and ent != ""
       and ordered(ent, "bool used;", "bool absent;", "int16_t handle;", "u_int16_t epoch;", "int16_t id_len;", "char id[MAX_ID_LEN + 1];", "STRING_CHUNK* rec;", "time_t when;")
       and re.search(r"NET_CACHE_ENTRY\s+net_cache\[NET_CACHE_SLOTS\];", nf) is not None and re.search(r"int\s+net_cache_next\s*=\s*0;", nf) is not None, "")
    # ---- NK20. net_cache_find
    fd = fn("net_cache_find")
    ck("NK20 net_cache_find: an entry is a hit only when handle AND epoch AND id length AND the id bytes (memcmp over id_len) all agree - so one file variable's record is never given to another, nor "
       "an epoch's to the next; every used entry it passes is aged first, and one older than NET_CACHE_TTL or from the FUTURE (the clock went back) is freed and skipped, before the comparison",
       fd != "" and ordered(fd, "time(NULL)", "if (!e->used)", "continue;", "(now < e->when) || ((now - e->when) > NET_CACHE_TTL)", "net_cache_free(e);", "continue;", "(e->handle == fvar->access.net.handle)",
                            "(e->epoch == fvar->access.net.epoch)", "(e->id_len == id_len)", "(memcmp(e->id, id, id_len) == 0)", "return e;", "return NULL;")
       and re.search(r"\(e->handle == fvar->access\.net\.handle\) && \(e->epoch == fvar->access\.net\.epoch\) && \(e->id_len == id_len\) && \(memcmp\(e->id, id, id_len\) == 0\)", fd) is not None
       and fd.count("net_cache_free(") == 1, "")
    # ---- NK21. net_cache_put
    pt = fn("net_cache_put")
    ck("NK21 net_cache_put: an id of length under 1 or over MAX_ID_LEN, and a record over NET_CACHE_REC_MAX, are not kept (returned before any slot is touched); a free slot is taken first, and when there is none the "
       "OLDEST by ring (net_cache_next, advanced modulo NET_CACHE_SLOTS) after its old record is freed; the entry gets its handle, epoch, id bytes, absent flag and a COPY of the record (k_copy_string - never the "
       "caller's chain) and the time it was stored",
       pt != "" and ordered(pt, "(id_len < 1) || (id_len > MAX_ID_LEN)", "(rec != NULL) && (rec->string_len > NET_CACHE_REC_MAX)", "return;", "if (!net_cache[i].used)", "if (e == NULL) {",
                            "e = &net_cache[net_cache_next];", "net_cache_next = (net_cache_next + 1) % NET_CACHE_SLOTS;", "net_cache_free(e);", "e->used = TRUE;", "e->absent = absent;",
                            "e->handle = fvar->access.net.handle;", "e->epoch = fvar->access.net.epoch;", "e->id_len = id_len;", "memcpy(e->id, id, id_len);",
                            "e->rec = (rec != NULL) ? k_copy_string(rec) : NULL;", "e->when = time(NULL);")
       and not re.search(r"e->rec\s*=\s*rec\b", pt) and pt.count("k_copy_string(") == 1 and pt.count("net_cache_free(") == 1, "")
    # ---- NK22. free and drop
    fr, dr = fn("net_cache_free"), fn("net_cache_drop")
    ck("NK22 net_cache_free releases the record (s_free) when there is one, clears the pointer and then the used flag; net_cache_drop(0) frees every used entry and net_cache_drop(h) only the used entries of "
       "handle h - the test is `used && (handle == 0 || entry handle == h)` and nothing else",
       fr != "" and ordered(fr, "if (e->rec != NULL)", "s_free(e->rec);", "e->rec = NULL;", "e->used = FALSE;")
       and re.search(r"if \(net_cache\[i\]\.used && \(\(handle == 0\) \|\| \(net_cache\[i\]\.handle == handle\)\)\)\s*net_cache_free\(&net_cache\[i\]\);", dr) is not None
       and re.search(r"for \(i = 0; i < NET_CACHE_SLOTS; i\+\+\)", dr) is not None, "")
    # ---- NK23. net_read and net_readv
    rd, rv = fn("net_read"), fn("net_readv")
    gap = rd[rd.find("if (status < 0)"):rd.find("if (status > 0)")] if "if (status < 0)" in rd else "x"
    ck("NK23 net_read: the cache is consulted only when the file variable is not stale (a closed one is not answered from it - net_op says why), after the empty-id test and before net_op; a hit on an ABSENT "
       "entry is ER_RNF, any other hit is a COPY of the cached chain (never the chain itself, which the caller may change or free); after net_op a record is put (what was read, FALSE), an ABSENT entry only "
       "when the status is exactly ER_RNF (not for any other positive status), and nothing at all on an error; net_cache_find is called here only, net_cache_put twice; net_readv does not use the cache",
       rd != "" and ordered(rd, "if (id_len < 1)", "return ER_IID;", "if (!net_stale(fvar) && !fvar->access.net.write) {", "net_cache_find(fvar, id, id_len)", "if (hit->absent)", "return ER_RNF;",
                            "*rec = (hit->rec != NULL) ? k_copy_string(hit->rec) : NULL;", "return 0;", "net_op(fvar, NF_READ", "if (status < 0)", "return net_raise(status, entry);",
                            "if (status > 0) {", "if (status == ER_RNF)", "net_cache_put(fvar, id, id_len, NULL, TRUE);", "return status;", "*rec = net_take_string(&out);", "k_release(&out);",
                            "net_cache_put(fvar, id, id_len, *rec, FALSE);", "return 0;")
       and inside(rd, "if (!net_stale(fvar) && !fvar->access.net.write) {", "net_cache_find(") and not re.search(r"\*rec\s*=\s*hit->rec", rd) and "net_cache_put(" not in gap
       and rd.count("net_cache_put(") == 2 and nf.count("net_cache_find(") == 2 and nf.count("net_cache_put(") == 3      # a definition and the uses
       and rv != "" and "net_cache" not in rv, "")
    # ---- NK24. where the entries go
    ns, cl, ca = fn("net_select"), fn("net_close"), fn("net_close_all")
    ck("NK24 the entries of a file variable go when it is SELECTed again (net_select drops that handle BEFORE net_op), when it is closed (net_close drops that handle - only a real handle, `handle > 0`, since "
       "drop(0) would drop everything - BEFORE the net_stale test and before the handle is zeroed, so a stale or already queued variable loses them too) and when the connections are dropped (net_close_all: "
       "net_cache_drop(0), right after the epoch moves and BEFORE the `net_used` return, so it happens even when nothing was opened); net_cache_drop is called from nowhere else but net_change_result() "
       "(slice 3e: twice, by handle, U6; it was net_change_op until S.73 item 3, which is a thin front of it now) - a definition and five uses",
       ns != "" and ordered(ns, "net_cache_drop(fvar->access.net.handle);", "net_op(fvar, NF_SELECT")
       and ordered(cl, "fvar->type != NET_FILE", "handle = fvar->access.net.handle;", "if (handle > 0)", "net_cache_drop(handle);", "if (net_stale(fvar))", "fvar->access.net.handle = 0;")
       and ordered(ca, "net_epoch++;", "net_pending_ct = 0;", "net_cache_drop(0);", "if (!net_used)", "net_call_raw(NF_CLOSEALL")
       and nf.count("net_cache_drop(") == 6 and fn("net_change_result").count("net_cache_drop(") == 2 and fn("net_change_op").count("net_cache_drop(") == 0, "")
    # ---- NK25. K_NET closes the remote files when the gate is set
    i = kn.find("case K_NET:")
    blk = kn[i:kn.find("case K_EDIT_OK:", i)] if i >= 0 else ""
    blk0 = blk[:blk.find("else if")] if "else if" in blk else blk            # slice 3e: the -2 branch (S2w) follows the set branch; the set branch is what NK25 reads
    after = blk0[blk0.find("net_close_all();"):] if "net_close_all();" in blk0 else "descr"
    ck("NK25 K_NET: a $internal caller that SETS the gate (n >= 0) changes the bit, computes the answer, saves process.status in n, calls net_close_all() (the remote files and connections belong to the account "
       "scope that ended), restores process.status and leaves - in that order, the call AFTER the bit is changed and inside the HDR_INTERNAL block; the -1 ask form and a caller that is not $internal never call "
       "it (net_close_all appears once in the case); nothing uses `descr` after the call, because the handler is BASIC and moves the e-stack",
       blk != "" and blk.count("net_close_all()") == 1
       and ordered(blk0, "if (n >= 0) {", "if (process.program.flags & HDR_INTERNAL) {", "SET_MY_GATE(UG_NET, n > 0);",
                   "result.data.value = MY_GATE(UG_NET);", "n = process.status;", "net_close_all();", "process.status = n;", "break;")
       and re.search(r"net_close_all\(\);\s*process\.status = n;\s*break;\s*\}\s*\}\s*result\.data\.value = ", blk) is not None      # the set branch LEAVES the case (a fall-through gives the same answer, so only the text can tell)
       and re.search(r"result\.data\.value = MY_GATE\(UG_NET\);\s*break;\s*$", blk) is not None      # the ask form ends the case (slice 3e put a -2 branch before it)
       and inside(blk, "if (process.program.flags & HDR_INTERNAL) {", "net_close_all()") and "descr" not in after, "")


# ---- S2. S.65 slice 3e (18 Oct 26): writes and locks on a file of a server whose definition says mode=write -----------------------------------------

S2_MSG_TEXTS = {   # the binding texts of the spec (.claude/s65-stage2-design.md, 1.3), one line each
    11509: "The connection to server %1 was lost during %2, so it is not known whether the change was made.  Nothing more is sent on it.  Open the file again and read the record to find out",
    11510: "A file on server %1 cannot be changed or locked inside a transaction: %2 is refused.  Nothing was sent",
    11511: "%2 is not available for a file on server %1.  Nothing was sent",
    11512: "The lock kind for the file on server %1 is not valid (%2)"}
S2_NET_DANGER = ("FPtr(", "access.dh", "lock_record(", "unlock_record(", "check_lock(", "log_permissions_error(", "edit_refusal(", "txn_read(", "k_recurse(", "end_select(", "clear_select(")


def seg(body, start, end, include_end=True):
    """The text from START to the first END after it (END included unless include_end is false), or ''."""
    i = body.find(start)
    j = body.find(end, i + len(start)) if i >= 0 else -1
    return body[i:j + (len(end) if include_end else 0)] if i >= 0 and j >= 0 else ""


def checks_s2(srcs, c, ck):
    """S.65 slice 3e, the spec .claude/s65-stage2-design.md (U1 to U12): writes, deletes, CLEARFILE and record locks on a file of a server whose definition says
    mode write.  Text only.  U1 (the codes) is NF1 and NK1b; U10 (the messages) is NF10 and the exact texts here.  ***WHAT THIS CANNOT SAY: that any statement writes,
    locks, waits or refuses - the sections hwrite and kwrite of sandbox-netfile.py - or that any of it compiles (`make` is the compiler).***  The checks on the class,
    the K_EDIT_OK key, descr.h, CPROC and edit_guard are written from the SPEC; they were held against a hand-made reading of it (see PROJECT_STATUS)."""
    nf, hb, hraw = c["netfiles.c"], c["bp:netfile"], srcs["bp:netfile"]
    d3, lk, d2, sdh, dsc, kn_, shc = c["op_dio3.c"], c["op_lock.c"], c["op_dio2.c"], c["sd.h"], c["descr.h"], c["op_kernel.c"], c["op_sh.c"]
    sc, cp, eg = c["bp:sdclient"], c["bp:cproc"], c["bp:edit_guard"]

    def fn(fname, name):
        return c_functions(c.get(fname) or c.get("c:" + fname, "")).get(name, "")

    def rb(label):
        return routine_body(hb, label)

    ao, ac, arl, rev, mn, arq, lf, rl_ = (rb(x) for x in ("act.open", "act.change", "act.release", "release.every", "mode.now", "after.rq", "lost.fail", "rc.locked"))
    cn, ard, asel = rb("connect.new"), rb("act.read"), rb("act.select")
    afu = rb("act.fileunlock")      # S.72
    # 21 Oct 26 (S.73 item 3): the checks of NF$OPEN that need no network are the routine check.server, called from act.open; the rows below read act.open with its body put where the call is
    ao = re.sub(r"gosub check\.server\s*\n\s*if failed then return",
                lambda _m: re.sub(r"\n\s*return\s*$", "", re.sub(r"^check\.server:\s*\n", "", rb("check.server").rstrip())), ao, count=1)

    # ---- S2a. the mode: where it is read, kept, told to the kernel and read again
    ck("S2a THE MODE (spec 2): act.open takes it from the definition's field 6 AFTER the accounts list and the checks that need no network and BEFORE the stored login - `read` unless the field is exactly "
       "`write` (anything else fails closed) - writes the open audit line (` mode=write` only for write), keeps it in nf.h.mode(hx) beside the account, and answers rc<7> = 1 for write only; the "
       "common block holds nf.h.mode and nf.h.aud and clear.handle empties both; mode.now re-reads the definition with !netdefs READ, starts false, needs eight fields, the same server name and "
       "field 6 `write`, and no other value or failure makes it true",
       ordered(ao, "if not(is.admin) then", "fmode = 'read'", "if defs<found,6> = 'write' then fmode = 'write'", "call $netcred('READ'", "if fmode = 'write' then", "' mode=write')", "end else",
               "nf.h.mode(hx) = fmode", "out = hx", "if fmode = 'write' then rc<7> = 1")
       and "defs<found,6> = 'write'" in ao and ao.count("rc<7>") == 1 and "nf.h.mode(hx) = fmode" in ao and "nf.h.acct(hx) = acc" in ao
       and re.search(r"nf\.h\.mode\(NF\$MAX\.HANDLES\)", hb) is not None and re.search(r"nf\.h\.aud\(NF\$MAX\.HANDLES\)", hb) is not None
       and "nf.h.mode(hy) = ''" in rb("clear.handle") and "nf.h.aud(hy) = ''" in rb("clear.handle")
       and ordered(mn, "mode.ok = @false", "call !netdefs('READ', defs, err)", "if err = '' then", "dcount(defs<dx>, @vm) = 8", "defs<dx,1> = nf.h.srv(hx)", "if defs<dx,6> = 'write' then mode.ok = @true")
       and mn.count("mode.ok = @true") == 1 and "@true" not in mn.replace("mode.ok = @true", ""), "")

    # ---- S2b. act.change: the order of the checks, and one request
    ck("S2b act.change, in this ORDER (spec 3.5): the handle of this account (a lost one will do), a handle that is not write-mode is REFUSED (act.refuse, 11501) before anything else, the handle "
       "again with the gate and the connection, the definition read AGAIN (not write now: the audit line `refused ... reason=mode` once per handle, then 11501), the transaction (11510, from "
       "system(SYS$TRANS_LEVEL)), the record id (not for CLEARFILE, and since S.72 not for FILELOCK, which has none: an empty id is an error 11503 here, not the ELSE branch) and the lock kind (11512), the audit line "
       "(since S.72 `netfile filelock` for NF$FILELOCK, after the clear line), and only then the object and the request; since S.72 only a record lock and a file lock are NOT changes (changing is false for them: a lost reply to one is 11497, not 11509)",
       ordered(ac, "need.gate = @false ; need.conn = @false ; any.acct = @false ; allow.lost = @true", "gosub get.handle", "changing = (op # NF$LOCK and op # NF$FILELOCK)", "if nf.h.mode(hx) # 'write' then", "gosub act.refuse",
               "return", "need.gate = @true ; need.conn = @true ; any.acct = @false ; allow.lost = @false", "gosub get.handle", "gosub mode.now", "if not(mode.ok) then", "aud.k = 'r'",
               "aud.line = 'netfile refused server=' : srvname : ' reason=mode'", "gosub audit.once", "gosub act.refuse", "return", "if system(SYS$TRANS_LEVEL) # 0 then", "fail.num = 11510",
               "if op # NF$CLEARFILE and op # NF$FILELOCK then", "gosub check.id.chg", "if op = NF$LOCK then", "if c # 'l' and c # 'u' then", "fail.num = 11512", "upd = (c = 'u')", "netfile write server=", "netfile delete server=",
               "netfile clear server=", "netfile filelock server=", "obj = nf.s.obj(slot)")
       and "11510" in ac and ac.count("fail.num = 11510") == 1 and ac.count("fail.num = 11512") == 1 and ac.count("changing = ") == 1
       and ordered(rb("check.id.chg"), "id = b", "if id = '' then", "fail.num = 11503", "fail.a2 = 'empty'", "gosub fail", "return", "end", "gosub check.id.shape")      # an empty id is an ERROR for a change
       and rb("check.id.chg").count("rc.else") == 0, "")
    ck("S2c ...and the request and its result (spec 3.5 items 9 and 10): each of the seven methods once (since S.72: filelock too), a lock only ever in the NO-WAIT form (recordlock's last argument is @false, "
       "filelock's is the literal @false, and no other form is written), the kind of the reply read from obj->LastError, a missing reply (LastError -1) counted as LOST, then lost (11509 for a change, through lost.fail), a server error (rq.err), 0 done, 4 busy "
       "for a LOCK or a FILELOCK only (rc.locked, not an error), 1 an ON ERROR reply shown through on.error.text (the reply's text, or the status when it has none: 19 Oct 26, K1), anything else 11504; "
       "NOTHING is retried and the handler holds no sleep",
       ordered(ac, "obj->write(nf.h.fno(hx), id, c)", "obj->writeu(nf.h.fno(hx), id, c)", "obj->delete(nf.h.fno(hx), id)", "obj->deleteu(nf.h.fno(hx), id)", "obj->clearfile(nf.h.fno(hx))",
               "obj->filelock(nf.h.fno(hx), @false)", "obj->recordlock(nf.h.fno(hx), id, upd, @false)", "lerr = obj->LastError", "gosub after.rq", "if lerr = -1 then rq.lost = @true", "if rq.lost then", "gosub lost.fail", "return",
               "if rq.err then", "gosub server.fail", "return", "if lerr = NF$LE.OK then return", "if (op = NF$LOCK or op = NF$FILELOCK) and lerr = NF$LE.LOCKED then", "gosub rc.locked", "return",
               "if lerr = NF$LE.ERROR then", "gosub on.error.text", "gosub server.fail", "return", "fail.num = 11504")
       and re.findall(r"obj->recordlock\(([^\n]*)\)\s*$", hb, re.M) == ["nf.h.fno(hx), id, upd, @false"] and not re.search(r"(?<![\w.$])(sleep|wait)(?![\w.$])", strip_strings(hb))
       and ordered(rl_, "rc = ''", "rc<1> = NF$RC.LOCKED", "rc<6> = rq.st") and "failed" not in rl_
       and re.search(r"\$define NF\$LE\.OK\s+0\b", hb) is not None and re.search(r"\$define NF\$LE\.ERROR\s+1\b", hb) is not None and re.search(r"\$define NF\$LE\.LOCKED\s+4\b", hb) is not None, "")
    ck("S2d after.rq decides `lost` by EQUALITY with the mark (rq.lost = (st = NF$NOREPLY); a changing request can be answered with a negative status, so a sign test is wrong - the class reads the status as a "
       "SIGNED 32 bit value, measured 18 Oct 26) and only then makes a status above 2147483647 negative - and on a success the status is never read into a message; lost.fail writes `netfile lost` for a change and answers 11509, for a lock 11497",
       ordered(arq, "rq.lost = (st = NF$NOREPLY)", "if not(rq.lost) then", "if st > 2147483647 then st -= 4294967296", "rq.st = st", "if rq.lost then rq.st = 0")
       and arq.count("st -= 4294967296") == 1 and arq.count("rq.lost = (st = NF$NOREPLY)") == 1 and arq.find("rq.lost = (st = NF$NOREPLY)") < arq.find("st -= 4294967296")
       and ordered(lf, "gosub drop.conn", "if changing then", "kernel(K$AUDIT, 'netfile lost server=' : srvname : ' op=' : opname)", "fail.num = 11509", "end else", "fail.num = 11497"), "")
    ck("S2e act.release (spec 3.8): it asks no gate, no mode and no transaction (releasing changes no data) and writes no audit line; `0` means every write-mode connection (release.every), a lost handle is "
       "answered OK with nothing sent, an id over MAX.ID.LEN is the only error it gives (11503), a connection that is not an object is dropped, a lost reply drops the connection and RELEASE does not fail; "
       "release.every sends one release per server that has a write-mode handle open (nf.h.mode = 'write') and goes on after a lost reply",
       ordered(arl, "need.gate = @false ; need.conn = @false ; any.acct = @false ; allow.lost = @true", "if a matches '1N0N' then", "release.all = (a + 0 = 0)", "gosub release.every", "return",
               "gosub get.handle", "if failed then return", "if nf.h.state(hx) # 1 then return", "len(id) > MAX.ID.LEN", "fail.num = 11503", "vartype(nf.s.obj(slot)) # V$OBJ", "gosub drop.conn",
               "obj->release(nf.h.fno(hx), id)", "gosub after.rq", "if rq.lost then gosub drop.conn")
       and not re.search(r"mode\.now|SYS\$TRANS_LEVEL|K\$AUDIT|audit\.once", arl) and arl.count("gosub fail") == 1 and arl.count("fail.num =") == 1
       and ordered(rev, "if nf.s.state(sx) = 1 then", "nf.h.slot(hy) = sx and nf.h.mode(hy) = 'write'", "if n > 0 and vartype(nf.s.obj(sx)) = V$OBJ then", "obj->release(0, '')", "gosub after.rq",
               "if rq.lost then", "gosub drop.conn") and "fail" not in rev, "")
    ck("S2f the other handler rules of slice 3e: connect.new makes the object QUIET after connect.keys succeeded and BEFORE the request bound is set (an abort cannot be caught here); act.read and "
       "act.select take an ON ERROR reply (e = 1) as a server error whose text comes from on.error.text (the reply's own text, or the status when it has none); get.handle for a lost handle is unchanged; "
       "the dispatch of NF$RELEASE is act.release",
       ordered(cn, "ok = obj->connect.keys(", "if not(ok) then", "obj->quiet = @true", "obj->settimeout(req.ms)", "nf.s.obj(slot) = obj") and hb.count("obj->quiet = @true") == 1
       and ordered(ard, "case e = 0", "case e = 2", "case e = 1", "gosub on.error.text", "gosub server.fail", "case 1", "fail.num = 11504")
       and ordered(asel, "obj->select(nf.h.fno(hx), NF$LIST)", "if obj->LastError = NF$LE.ERROR then", "gosub on.error.text", "gosub server.fail", "return", "obj->readlist(NF$LIST, e)",
                   "if e = 1 then", "gosub on.error.text", "gosub server.fail", "return", "if e # 0 then"), "")
    ooe = rb("on.error.text")
    ck("S2k on.error.text, the ONE place an ON ERROR reply becomes text (19 Oct 26, K1): it takes the text of THIS reply from obj->LastText (the class empties it before every request), cleans it like any "
       "text that came from another machine (printable ASCII, at most 100 characters), shows it when there is one and falls back to 'status <n>' when there is none; the places that used to say "
       "'status <n>' whatever the reply said (a refused write or lock, a READ, a SELECT) call it - four since 19 Oct 26, finish 2, because the SELECT proper and its READLIST are both looked at (the "
       "class used to abort on either, even when quiet, so neither branch could run), five since S.72, because act.fileunlock answers an ON ERROR reply (the files-only login without the write group) "
       "in the same way, six since S.72b, because act.recordlocked does too (request 34 is refused to that login: message 11521 as an ON ERROR reply, shown by the program as 11500 with the server's text) "
       "- and 'status ' is written nowhere else in the program; the header no longer says the text is never shown",
       ordered(ooe, "txt = obj->LastText", "gosub clean.text", "if out.txt = '' then", "rq.txt = 'status ':rq.st", "end else", "rq.txt = out.txt", "return")
       and hb.count("rq.txt = 'status ':rq.st") == 1 and hb.count("gosub on.error.text") == 8 and "gosub on.error.text" in afu and "gosub on.error.text" in rb("act.recordlocked")
       and "gosub on.error.text" in rb("admin.outcome")      # seven since S.73 item 3: admin.outcome (the answer of the four administration operations) shows the ON ERROR reply's text too
       and "gosub on.error.text" in rb("act.indexq")      # eight since its D1: act.indexq's READLIST of a scan that found a key (the first request goes through admin.outcome)
       and "'status '" not in (ao + ac + ard + asel + arq + lf + afu + rb("act.recordlocked") + rb("act.indexq"))
       and "never shown" not in hraw and "is never shown, it can be stale" not in hraw, repr(ooe[:200]))

    # ---- S2g. the class gpl.bp/sdclient (spec 3.3)
    pub = re.search(r"^public debugging,.*?(?=\n\s*\n)", sc, re.S | re.M)
    pub = pub.group(0) if pub else ""
    co = re.search(r"public subroutine create\.object\s*\n(.*?)\nend", sc, re.S)
    co = co.group(1) if co else ""
    mp = re.search(r"local function message\.pair\(pkt\.type, pkt\)\s*\n(.*?)\nend", sc, re.S)
    mp = mp.group(1) if mp else ""
    gr = re.search(r"local function get\.response\(\)\s*\n(.*?)\nend", sc, re.S)
    gr = gr.group(1) if gr else ""
    sites = re.findall(r"([^\n]*)\n\s*abort '(\w+) generated an abort event'", sc)
    guarded = sorted(v for prev, v in sites if "not(quiet)" in prev)
    ck("S2g THE CLASS, quiet (spec 3.3, items 1 to 3): the public properties quiet, LastError and LastText exist and create.object starts them @false, -1 and ''; message.pair resets LastError and LastText "
       "BEFORE it writes the packet; get.response sets LastError = server.error as soon as read.packet succeeded (and LastText for an ON ERROR reply) BEFORE it tests for SV$ERROR; the abort of each of "
       "write, writeu, delete (twice: delete and deleteu), recordlock, release, read.record, the new clearfile, (19 Oct 26, finish 2) select and readlist, (S.72) the new filelock and fileunlock and (S.73 item 3 D1) setleft and setright is guarded by `and not(quiet)` (recordlocked, selectleft and selectright by a one-line `if not(quiet) then abort`), no other abort is "
       "(CLOSE, ... are unchanged); the pre-send `abort 'Illegal record id'` of write and writeu does `LastError = SV$ON.ERROR` and returns when quiet",
       all(re.search(r"\b%s\b" % w, pub) for w in ("quiet", "LastError", "LastText", "ServerStatus", "error"))
       and re.search(r"quiet = @false", co) is not None and re.search(r"LastError = -1", co) is not None and re.search(r"LastText = ''", co) is not None
       and ordered(mp, "LastError = -1", "LastText = ''", "write.packet(")
       and ordered(gr, "read.packet()", "LastError = server.error", "if server.error = SV$ON.ERROR then LastText = in.pkt", "if server.error = SV$ERROR then")
       # S.73 item 3 D1 (21 Oct 26): SETLEFT and SETRIGHT are guarded too (the handler calls them), and so are the one-line guards `if not(quiet) then abort` of RECORDLOCKED, SELECTLEFT and SELECTRIGHT
       and guarded == sorted(["DELETE", "DELETE", "RECORDLOCK", "RELEASE", "WRITE", "WRITEU", "READ", "CLEARFILE", "SELECT", "READLIST", "FILELOCK", "FILEUNLOCK", "SETLEFT", "SETRIGHT"])
       and sorted(re.findall(r"if not\(quiet\) then abort '(\w+) generated an abort event'", sc)) == ["RECORDLOCKED", "SELECTLEFT", "SELECTRIGHT"]
       and not [v for prev, v in sites if v not in ("DELETE", "RECORDLOCK", "RELEASE", "WRITE", "WRITEU", "READ", "CLEARFILE", "SELECT", "READLIST", "FILELOCK", "FILEUNLOCK", "SETLEFT", "SETRIGHT") and "quiet" in prev]
       and len(re.findall(r"if quiet then\s*\n\s*LastError = SV\$ON\.ERROR\s*\n\s*return\s*\n\s*end\s*\n\s*abort 'Illegal record id'", sc)) == 2, repr((guarded, [v for p, v in sites if "quiet" not in p])))
    rlk = re.search(r"public subroutine recordlock\(fno, id, update, wait\)\s*\n(.*?)\nend", sc, re.S)
    rlk = rlk.group(1) if rlk else ""
    rpk = re.search(r"local function read\.packet\(\)\s*\n(.*?)\nend", sc, re.S)
    rpk = rpk.group(1) if rpk else ""
    ck("S2l THE CEILING ON A REPLY (19 Oct 26, K8c): sdclient's read.packet tests the length the header announces BEFORE it trusts or reads anything else - a count below 10 (the count is read "
       "as a SIGNED 32 bit value, so 2 GB and over arrives negative) fails the call, and so does a count above maxpacket when that is above 0 - and it does so BEFORE server.error and ServerStatus "
       "are set (a caller that marks ServerStatus first sees the mark: no reply) and before the loop that reads the body; maxpacket is a public property that create.object starts at 0 (no "
       "ceiling: other users of the class are unchanged); $netfile sets it to NF$MAX.PACKET, 1073741832 (the largest string SD holds, 1073741822, and the ten byte header), right after quiet "
       "and before the timeout, once",
       ordered(rpk, "pkt.bytes = oconv(pkt.header[1,4], 'ILL')", "if pkt.bytes < 10 then return @false", "if maxpacket > 0 and pkt.bytes > maxpacket then return @false",
               "hdr.error = oconv(pkt.header[5,2], 'ISL')", "hdr.status = oconv(pkt.header[7,4], 'ILL')", "n = pkt.bytes - 10", "in.pkt = ''", "loop",
               "server.error = hdr.error", "ServerStatus = hdr.status")       # 20 Oct 26, S.73 item 2: the header's error and status are kept apart until the BODY is in (test-tlsread-units.py T8)
       and re.search(r"\bmaxpacket\b", pub) is not None and "maxpacket = 0" in co
       and re.search(r"\$define NF\$MAX\.PACKET\s+1073741832\b", hb) is not None
       and ordered(cn, "obj->quiet = @true", "obj->maxpacket = NF$MAX.PACKET", "obj->settimeout(req.ms)") and hb.count("obj->maxpacket") == 1, repr(rpk[:300]))
    clf = re.search(r"public subroutine clearfile\(fno\)\s*\n(.*?)\nend", sc, re.S)
    clf = clf.group(1) if clf else ""
    ck("S2h ...recordlock's wait flag is the right way round (the defect fixed: flag 2 is NO wait, so `if not(wait) then flags += 2`; the old `if wait then flags += 2` is gone), and the new "
       "clearfile(fno) sends request 31 (SrvrClearfile) with the file number and nothing else, takes its abort only when not quiet, and SrvrClearfile is still 31",
       "if not(wait) then flags += 2" in rlk and not re.search(r"if wait then flags \+= 2", sc)
       and ordered(clf, "pkt = iconv(fno, 'ISL')", "message.pair(SrvrClearfile, pkt)", "not(quiet)", "abort 'CLEARFILE generated an abort event'")
       and re.search(r"\$define SrvrClearfile\s+31\b", sc) is not None and re.search(r"\$define SrvrLockRecord\s+30\b", sc) is not None, "")

    # ---- S2i. net_gate (spec 5.2) and the entry points
    ng = fn("netfiles.c", "net_gate")
    ck("S2i net_gate, in this ORDER (spec 5.2; S.72b added step 1a): the caller's ON ERROR bit is the only flag it puts in process.op_flags (given back as found at every one of its returns); 1 a handle that is read-mode or "
       "FV_RDONLY is refused with 11501 and -ER_NETWORK and NOTHING below runs for it; 1a (S.72b) NETG_PEEK, the kind of RECORDLOCKED(), is answered 0 HERE - after step 1, so a read-mode handle is refused, and before "
       "all the rest, so it needs no transaction and no edit gate (it changes nothing); 2 is GONE since S.73 item 3 (WRITE ... CREATING.SEQKEY was refused here with 11511; the counter is the server's now, and the write "
       "has the gate of every other); 3 a transaction, tested on process.txn_id and NOT on the local txn_id "
       "(which is 0 for every NET_FILE), is refused with 11510 and -ER_TXN, for every kind but NETG_PEEK; 4 the S.64 edit gate of the remote file's name for WRITE, DELETE, CLEAR and (S.73 item 3) ADMIN only (never a lock): an $internal caller "
       "(process.program.flags & HDR_INTERNAL, read here before any BASIC runs - net_gate runs none) and the administrator are exempt, otherwise edit_permitted(kind) decides, refusal 11404 + kind "
       "(11405 to 11407) with -ER_PERM raised unless the caller said ON ERROR; 5 else 0 (so process.op_flags is given back at five returns: the three refusals, the PEEK answer and the end)",
       ng != "" and ordered(ng, "process.op_flags = op_flags & P_ON_ERROR;", "!fvar->access.net.write || (fvar->flags & FV_RDONLY)", "net_refuse_with(fvar, what, MSG_READ_ONLY, -ER_NETWORK)",
                            "kind == NETG_PEEK", "return 0;",
                            "process.txn_id != 0", "net_refuse_with(fvar, what, MSG_TXN, -ER_TXN)",
                            "(kind == NETG_WRITE) || (kind == NETG_DELETE) || (kind == NETG_CLEAR) || (kind == NETG_ADMIN)", "fvar->access.net.edit_kind", "!(process.program.flags & HDR_INTERNAL)", "!MY_ADMIN()",
                            "!edit_permitted(ek)", "net_set_message(11404 + ek", "net_raise(-ER_PERM, op_flags & P_ON_ERROR)", "return 0;")
       and "P_SEQKEY" not in ng and "MSG_UNAVAILABLE" not in ng
       and not re.search(r"(?<![\w.])txn_id", ng.replace("process.txn_id", "")) and ng.count("process.op_flags = entry;") == 5
       and not re.search(r"net_call_core\(|net_call_raw\(|net_op_ex\(|net_op\(|net_flush_pending\(|k_call\(|k_run_program\(|load_object\(", ng) and "NETG_LOCK" not in ng, "")
    nk, nl = fn("netfiles.c", "net_change_result"), fn("netfiles.c", "net_lock_step")      # S.73 item 3: the body of net_change_op, which is a thin front of it now (it releases the answer)
    ck("S2j net_change_result (the body of net_write, net_delete, net_clear and net_lock - through net_change_op - and of net_admin, net_fcontrol and net_write_seqkey): the handle's cache entries are dropped BEFORE the request and AGAIN after the answer - success, error or no reply - and "
       "BOTH before net_raise, which longjmps, so a drop placed after it would never run; the drop is by handle (`handle > 0`, never net_cache_drop(0)); the request is made ONCE (net_op_ex with the "
       "server's status passed on), an ELSE answer is not usable, STATUS() is set to 0 on a success and is never the server's (except the holder of a busy lock); a busy answer is understood for a lock only",
       nk != "" and ordered(nk, "int handle = fvar->access.net.handle;", "if (handle > 0)", "net_cache_drop(handle);", "net_was_locked = FALSE;", "net_op_ex(fvar, op, b, blen, c, clen, chain, use_chain, 0, lock_op, TRUE, &out)",
                            "busy = lock_op && net_was_locked;", "if ((status > 0) && !busy)", "MSG_HANDLER", "if (status == 0)", "k_release(&out);", "if (handle > 0)", "net_cache_drop(handle);",
                            "if (status < 0)", "return net_raise(status, entry);", "if (!busy)", "process.status = 0;")
       and nk.count("net_cache_drop(handle)") == 2 and "net_cache_drop(0)" not in nk and nk.count("net_op_ex(") == 1
       and ordered(fn("netfiles.c", "net_answer"), "case NF_RC_LOCKED:", "if (!lock_ok) {", "MSG_HANDLER", "return -ER_NETWORK;", "net_was_locked = TRUE;", "process.status = rc->status;", "return ER_LCK;"), "")
    ck("S2k the server's own status is passed on, negated, for the changing and locking entry points only: net_error_status passes it only for message 11500 and only with pass_status, from the list "
       "ER_IID, ER_RDONLY, ER_TRIGGER, ER_NOLOCK, ER_PERM, ER_MAXRLOCK - everything else (a server's edit-gate refusal, a lost connection, an unknown error) is -ER_NETWORK; net_op_ex is called with "
       "pass_status TRUE from net_change_op and net_lock_code (the request behind net_check_lock and, since S.72, net_recordlocked) only (the read paths keep 7000: net_op is a thin front with FALSE FALSE); "
       "net_parse_rc reads field 7 as write only for an exact 1",
       ordered(fn("netfiles.c", "net_passed_status"), "case ER_IID:", "case ER_RDONLY:", "case ER_TRIGGER:", "case ER_NOLOCK:", "case ER_PERM:", "case ER_MAXRLOCK:", "return -s;", "return -ER_NETWORK;")
       and ordered(fn("netfiles.c", "net_error_status"), "case MSG_SERVER_ERROR:", "if (pass_status)", "return net_passed_status(rc->status);", "return -ER_NETWORK;")
       and nf.count("net_op_ex(") == 6 and "NULL, FALSE, else_status, FALSE, FALSE, out)" in fn("netfiles.c", "net_op")
       and "NULL, FALSE, ER_FNF, FALSE, FALSE, &out)" in fn("netfiles.c", "net_index_query")      # S.73 item 3 D1: the sixth call is the index queries', a read: no status passed on
       and "lock_op, TRUE, &out)" in fn("netfiles.c", "net_change_result") and "FALSE, TRUE, &out)" in fn("netfiles.c", "net_lock_code") and "FALSE, FALSE, &out)" in fn("netfiles.c", "net_release")
       and ordered(fn("netfiles.c", "net_parse_rc"), "(rc->result != NF_RC_LOCKED)", "net_field(buf, 7, num, sizeof(num))", "rc->mode_write = (atoi(num) == 1);"), "")
    nlr = fn("netfiles.c", "net_lock_result")      # S.72: the tail of net_lock_step, shared with net_filelock_step
    ck("S2l net_lock_step: the lock is asked once in the no-wait form with only the ON ERROR bit set (process.op_flags is 0 again straight after the request) and the answer goes to net_lock_result (S.72: the tail "
       "of net_lock_step, moved out so that the record lock and the file lock cannot wait differently); net_lock_result: held answers NET_LOCK_HELD; an error is returned as it is; a busy record with a LOCKED clause answers "
       "NET_LOCK_LOCKED with the holder in process.status; a busy record without one sets the opcode up to run again (pc = retry_pc, process.op_flags = op_flags), processes events, beeps and sleeps 250 ms and "
       "answers NET_LOCK_WAIT; the handler is never asked to wait (net_lock sends NF_LOCK with the kind letter u or l)",
       nl != "" and nlr != "" and ordered(nl, "process.op_flags = op_flags & P_ON_ERROR;", "net_lock(fvar, id, id_len, update)", "process.op_flags = 0;", "return net_lock_result(st, op_flags, retry_pc);")
       and ordered(nlr, "return NET_LOCK_HELD;", "if (st != ER_LCK)", "return st;",
                   "holder = process.status;", "if (op_flags & P_LOCKED)", "return NET_LOCK_LOCKED;", "pc = retry_pc;", "process.op_flags = op_flags;", "process_events();", "lock_beep();", "Sleep(250);",
                   "return NET_LOCK_WAIT;")
       and nf.count("pc = retry_pc;") == 1 and "pc = retry_pc;" in nlr and 'update ? "u" : "l"' in fn("netfiles.c", "net_lock") and "NF_LOCK" in fn("netfiles.c", "net_lock"), "")
    rel, rela, flc = fn("netfiles.c", "net_release"), fn("netfiles.c", "net_release_all"), fn("netfiles.c", "net_flush_closes")
    ck("S2m net_release, net_release_all and net_flush_closes NEVER raise and give process.status, process.op_flags and the last message back as they found them; net_release ignores an id over NET_ID_MAX; "
       "net_release_all does nothing, and runs no BASIC, unless this process ever opened a write-mode file (net_used_write, set in net_open_work, cleared by net_close_all) and asks for handle 0; "
       "net_flush_closes sends only what is queued",
       rel != "" and rela != "" and flc != "" and not re.search(r"net_raise\(|k_error\(", rel + rela + flc)
       and ordered(rel, "int32_t status_keep = process.status;", "id_len > NET_ID_MAX", "return;", "net_op_ex(fvar, NF_RELEASE", "process.op_flags = entry;", "process.status = status_keep;", "memcpy(net_msg, msg_keep")
       and ordered(rela, "if (!net_used_write)", "return;", "net_flush_pending();", "net_call_raw(NF_RELEASE, \"0\", 1", "process.op_flags = entry;", "process.status = status_keep;")
       and ordered(flc, "if (net_pending_ct == 0)", "return;", "net_flush_pending();", "process.op_flags = entry;", "process.status = status_keep;")
       and "net_used_write = TRUE;" in fn("netfiles.c", "net_open_work") and "net_used_write = FALSE;" in fn("netfiles.c", "net_close_all"), "")

    # ---- S2n. the cache (spec 8) and the chain (spec 5.1)
    nwr, ndl, ncl, nlk, ncore = (fn("netfiles.c", x) for x in ("net_write", "net_delete", "net_clear", "net_lock", "net_call_core"))
    ck("S2n U6/U7 the four entry points each go through net_change_op (which drops the handle's cache before and after) and nothing else drops the cache but the three slice 3c places; the id is checked "
       "(1 to NET_ID_MAX) before anything is sent (net_bad_id: 11503 and -ER_IID); the RECORD is passed as the chain the program holds - net_write hands net_change_op `rec` with use_chain TRUE and "
       "the core pushes a STRING descriptor with its reference count up (the caller keeps its own) - and is never flattened: no k_get_c_string of a record anywhere in netfiles.c's write path",
       all("net_change_op(" in b for b in (nwr, ndl, ncl, nlk)) and "net_change_op(fvar, keep_lock ? NF_WRITEU : NF_WRITE, id, id_len, \"\", 0, rec, TRUE, FALSE)" in nwr
       and "net_change_op(fvar, keep_lock ? NF_DELETEU : NF_DELETE, id, id_len, \"\", 0, NULL, FALSE, FALSE)" in ndl and "net_change_op(fvar, NF_CLEARFILE" in ncl
       and "net_change_op(fvar, NF_LOCK, id, id_len, update ? \"u\" : \"l\", 1, NULL, FALSE, TRUE)" in nlk
       and all("(id_len < 1) || (id_len > NET_ID_MAX)" in b and "net_bad_id(fvar, id_len)" in b for b in (nwr, ndl, nlk))
       and ordered(ncore, "if (use_chain) {", "InitDescr(e_stack, STRING);", "(e_stack++)->data.str.saddr = cchain;", "if (cchain != NULL)", "(cchain->ref_ct)++;", "} else {", "net_push_string(c, clen);")
       and "k_get_c_string" not in nwr + nk + ncore and "k_get_string" not in nwr + nk + ncore
       and ordered(fn("netfiles.c", "net_read"), "if (!net_stale(fvar) && !fvar->access.net.write) {", "net_cache_find(", "net_cache_put("), "")

    # ---- S2o. op_dio3.c: the NET arms, the retry point, the lock rules
    ow, od, oc_, rr, orv = (fn("op_dio3.c", x) for x in ("op_write", "op_delete", "op_clrfile", "read_record", "op_readv"))
    ok_ = []
    for name, body, call, stop in (("op_write", ow, "net_write(", "goto exit_op_write;"), ("op_delete", od, "net_delete(", "goto exit_op_delete;"), ("op_clrfile", oc_, "net_clear(", "return;")):
        i = body.find("if (fvar->type == NET_FILE) {")
        j = body.find(stop, body.find(call, i)) if i >= 0 and body.find(call, i) >= 0 else -1
        arm = body[i:j] if i >= 0 and j > i else ""
        ok_.append((name, arm != "" and not any(x in arm for x in S2_NET_DANGER) and body.find("refuse_net_file(") < i
                    and "process.status = net_st;" in body[body.find(call, i):j + 80] and "pc = " not in arm))      # the status of the call is the statement's STATUS(), set AFTER the call (the CREATING.SEQKEY arm of op_write sets its own earlier); pc is net_lock_step's alone
    ck("S2o U8 the NET arms of op_write, op_delete and op_clrfile come AFTER refuse_net_file (the gate) and touch nothing of the file table: no FPtr, no local lock, no check_lock, no edit_refusal, no "
       "transaction cache, no recursion; op_delete tests the empty id FIRST (-ER_IID, as locally) and a record id over NET_ID_MAX before it locks or sends; op_write reads the id and the record "
       "(through k_get_string, so a COLL value is made a string as for any other file), refuses an id that is not valid or over NET_ID_MAX, copies it for the lock, and calls net_write with the CHAIN "
       "and keep_lock; op_clrfile calls net_clear and pushes the status as an integer",
       all(ok for _n, ok in ok_) and ordered(od, "id_len <= 0", "-ER_IID", "refuse_net_file(fvar, op_flags, \"DELETE\", NETG_DELETE)", "id_len > NET_ID_MAX", "net_pre_change_lock(", "net_delete(fvar, id, id_len, keep_lock)")
       and ordered(ow, "refuse_net_file(fvar, op_flags, keep_lock ? \"WRITEU\" : \"WRITE\", NETG_WRITE)", "if (fvar->type == NET_FILE) {", "net_write_seqkey(fvar", "id_len = k_get_c_string(rid_descr, id, sysseg->maxidlen);", "k_get_string(src_descr);", "!valid_id(id, id_len) || (id_len > NET_ID_MAX)",
                    "-ER_IID", "net_pre_change_lock(", "net_write(fvar, id, id_len, src_descr->data.str.saddr, keep_lock)", "goto exit_op_write;")
       and ordered(oc_, "refuse_net_file(fvar, op_flags, \"CLEARFILE\", NETG_CLEAR)", "if (fvar->type == NET_FILE) {", "net_clear(fvar)", "k_dismiss();", "InitDescr(e_stack, INTEGER);", "return;"), repr(ok_))
    npc = fn("op_dio3.c", "net_pre_change_lock")
    ck("S2p MUSTLOCK and $MODE AUTOLOCK are honoured for a remote WRITE and DELETE (spec 5.3, decision 11): net_pre_change_lock takes the update lock with net_lock_step when AUTOLOCK is on (LOCKED taken off: "
       "it waits by re-running the opcode, NETL_WAIT, and the caller returns AT ONCE) and, under MUSTLOCK, asks the server (net_check_lock) whether this session holds it and answers -ER_NOLOCK when it does "
       "not; both op_write and op_delete call it BEFORE the request and return on NETL_WAIT without touching the stack",
       npc != "" and ordered(npc, "if (op_flags & P_AUTOLOCK) {", "net_lock_step(fvar, id, id_len, TRUE, op_flags & ~P_LOCKED, retry_pc)", "case NET_LOCK_HELD:", "return NETL_GO;", "case NET_LOCK_WAIT:",
                             "return NETL_WAIT;", "default:", "return NETL_FAIL;", "if (pcfg.must_lock) {", "net_check_lock(fvar, id, id_len)", "-ER_NOLOCK", "return NETL_FAIL;", "return NETL_GO;")
       and all(ordered(b, "net_pre_change_lock(", "case NETL_WAIT:", "return;", "case NETL_FAIL:", "net_write(" if b is ow else "net_delete(") for b in (ow, od))
       and "check_lock(" not in npc.replace("net_check_lock(", "") and "lock_record(" not in npc, "")
    bad_pc = []
    for fname, name in (("op_dio3.c", "read_record"), ("op_dio3.c", "op_readv"), ("op_lock.c", "op_lockrec"), ("op_dio3.c", "op_write"), ("op_dio3.c", "op_delete"),
                        ("op_lock.c", "op_filelock")):      # S.72: FILELOCK waits for a busy file by the same means
        body = fn(fname, name)
        first = min([m.start() for m in re.finditer(r"\bnet_(?:gate|lock_step|filelock_step|write|delete|read|readv|pre_change_lock|release|refuse)\(|\brefuse_net_file\(", body)] or [10 ** 9])
        decl = re.search(r"u_char\s*\*\s*retry_pc\s*=\s*op_pc;", body)
        others = [m.start() for m in re.finditer(r"\bop_pc\b", body) if not decl or m.start() != decl.end() - len("op_pc;")]      # the LOCAL lock wait uses it after lock_record()
        local_lock = body.find("lock_record(")
        if not decl or decl.start() > first or "pc = retry_pc" in body or any(local_lock < 0 or p < local_lock for p in others):
            bad_pc.append(name)
        for m in re.finditer(r"net_lock_step\(([^;]*)\)", body):
            if not m.group(1).rstrip().rstrip(")").rstrip().endswith("retry_pc"):
                bad_pc.append(name + ": net_lock_step without retry_pc")
        for m in re.finditer(r"net_filelock_step\(([^()]*)\)", body):      # S.72
            if m.group(1).split(",")[-1].strip() != "retry_pc":
                bad_pc.append(name + ": net_filelock_step without retry_pc")
    lrb = fn("op_lock.c", "op_lockrec")
    if lrb and lrb.find("pc--") != -1 and (lrb.find("txn_id = (fvar->flags") < 0 or lrb.find("pc--") < lrb.find("txn_id = (fvar->flags")):
        bad_pc.append("op_lockrec: pc-- on the remote path (before the local lock code begins)")
    ck("S2q U5 the six opcodes that can wait for a remote lock (READU and its kin in read_record, READVU/L in op_readv, RECORDLOCKU/L in op_lockrec, the WRITE and DELETE that AUTOLOCK and, since S.72, FILELOCK in "
       "op_filelock) take "
       "`u_char *retry_pc = op_pc;` BEFORE their first net_ or refuse_net_file call (the handler's own opcodes overwrite op_pc, and k_return restores pc but not op_pc), name op_pc nowhere else but "
       "the LOCAL lock wait that follows lock_record, "
       "never assign pc themselves (net_lock_step does, through net_lock_result: `pc = retry_pc` appears once, in netfiles.c) and pass retry_pc as the last argument of every net_lock_step and net_filelock_step; "
       "the local `pc--` of op_lockrec is nowhere on the remote path (that of op_filelock is S72a's)", not bad_pc, repr(bad_pc))
    lock_blk = seg(rr, "if ((op_flags & P_REC_LOCKS) && (fvar->type == NET_FILE)) {", "} else if (op_flags & P_REC_LOCKS)")
    ck("S2r read_record, in the lock block: a remote file asks net_lock_step (not lock_record) BEFORE the local lock code, finds the operands again from the stack (net_reload_read_operands: the handler ran "
       "BASIC), leaves at once on NET_LOCK_WAIT without popping anything, takes ER_LCK on NET_LOCK_LOCKED, and goes to the exit on an error; refuse_net_file is asked with NETG_LOCK behind (type NET_FILE and "
       "P_REC_LOCKS) before the target is cleared; op_readv asks it only for the locking forms (a plain READV is allowed in every mode), locks BEFORE net_readv, returns before anything is popped on a "
       "wait and does not overwrite the holder in STATUS() when the record is busy",
       lock_blk != "" and ordered(lock_blk, "net_lock_step(fvar, id, id_len, (op_flags & P_ULOCK) != 0, op_flags, retry_pc)", "net_reload_read_operands(", "case NET_LOCK_HELD:", "case NET_LOCK_WAIT:",
                                  "return;", "case NET_LOCK_LOCKED:", "status = ER_LCK;", "goto exit_op_read;", "default:", "goto exit_op_read;") and "lock_record(" not in lock_blk
       and ordered(rr, "refuse_net_file(fvar, op_flags,", "NETG_LOCK", "if (!(op_flags & P_PICKREAD)) {", "net_lock_step(")
       and ordered(orv, "if ((op_flags & P_REC_LOCKS) && refuse_net_file(", "NETG_LOCK", "net_st = 0;", "if (op_flags & P_REC_LOCKS) {", "net_st = net_lock_step(fvar, id, id_len, (op_flags & P_ULOCK) != 0, op_flags, retry_pc)",
                    "case NET_LOCK_WAIT:", "return;", "case NET_LOCK_LOCKED:", "net_st = ER_LCK;", "if (net_st == 0) {", "net_st = net_readv(fvar, id, id_len, field_no, &net_str)", "if (net_st != ER_LCK)",
                    "process.status = net_st;"), "")

    # ---- S2s. op_lock.c
    olr, ore, orf, ora = (fn("op_lock.c", x) for x in ("op_lockrec", "op_release", "op_rlsfile", "op_rlsall"))
    ck("S2s U9 op_lockrec: the empty id is refused first (k_illegal_id); a NET_FILE that is read-mode or FV_RDONLY gets the slice 3c block UNCHANGED (net_refuse unless ON ERROR, STATUS() -ER_PERM, two dismisses, "
       "push); a write-mode one asks net_gate(NETG_LOCK) and then net_lock_step with retry_pc - waiting returns at once with the operands left, a busy record pushes ER_LCK, held pushes 0, an error "
       "pushes process.status, and process.op_flags is cleared before the two dismisses",
       olr != "" and ordered(olr[:olr.find("txn_id = (fvar->flags")], "k_illegal_id(id_descr);", "if (fvar->type == NET_FILE)", "!fvar->access.net.write || (fvar->flags & FV_RDONLY)",
                             "net_refuse(fvar, update ? \"RECORDLOCKU\" : \"RECORDLOCKL\")", "process.status = -ER_PERM;", "k_dismiss();", "k_dismiss();", "net_gate(fvar, NETG_LOCK, op_flags,",
                             "net_lock_step(fvar, id, id_len, update, op_flags, retry_pc)", "case NET_LOCK_HELD:", "case NET_LOCK_WAIT:", "return;", "case NET_LOCK_LOCKED:", "status = ER_LCK;", "default:",
                             "(int16_t)process.status", "process.op_flags = 0;", "k_dismiss();", "k_dismiss();", "return;"), "")
    ck("S2t ...op_release and op_rlsfile: a read-mode handle still ends in net_refuse (slice 3c); a write-mode one sends the release only outside a transaction (process.txn_id == 0 - the local statement does "
       "nothing inside one) and, for the record form, only for an id of 1 to NET_ID_MAX, then dismisses its operands and pushes 0 - NEVER raising; op_rlsall calls net_release_all inside its "
       "process.txn_id == 0 test before unlock_record; the backstops in check_lock, lock_record and unlock_record are kept; since S.72 FILELOCK, FILEUNLOCK, GETLOCKS and RECORDLOCKED() call net_refuse nowhere (S72a to S72i read what they do instead)",
       ordered(ore, "if (fvar->type == NET_FILE) {", "if (!fvar->access.net.write)", "net_refuse(fvar, \"RELEASE\")", "process.txn_id == 0 && id_len > 0 && id_len <= NET_ID_MAX", "net_release(fvar, id, id_len);",
               "k_dismiss();", "k_dismiss();", "(e_stack++)->data.value = 0;", "return;")
       and ordered(orf, "if (fvar->type == NET_FILE) {", "if (!fvar->access.net.write)", "net_refuse(fvar, \"RELEASE\")", "if (process.txn_id == 0)", "net_release(fvar, NULL, 0);", "k_dismiss();",
                   "(e_stack++)->data.value = 0;", "return;")
       and "net_raise" not in ore + orf + ora and ordered(ora, "if (process.txn_id == 0) {", "net_release_all();", "unlock_record(NULL")
       and all("NET_FILE" in fn("op_lock.c", x) for x in ("check_lock", "lock_record", "unlock_record"))
       and not any("net_refuse(" in fn("op_lock.c", x) for x in ("op_filelock", "op_flunlock", "op_getlocks", "op_reclckd")), "")      # S.72: FILELOCK, FILEUNLOCK, GETLOCKS, RECORDLOCKED() refuse nothing now: S72a-S72i

    # ---- S2u. FILEINFO, the mode and the S.64 key (spec 2.5, 5.5)
    fi = fn("op_dio2.c", "op_fileinfo")
    br = seg(fi, "if (ftype == NET_FILE) {", "fptr = FPtr(fvar->file_id);", include_end=False)
    ck("S2u FILEINFO of a NET_FILE (spec 2.5): FL$READONLY answers the variable's OWN flag ((fvar->flags & FV_RDONLY) != 0: 1 for a read-mode server, 0 for write); FL$SETRDONLY sets FV_RDONLY only for an "
       "$internal program and answers 0 (net_gate then refuses every change); FL$NON.TXN and FL$NETFILE stay 1 and FL$TXN.UPDATE 0; the branch still reads no FPtr",
       br != "" and "FPtr(" not in br and ordered(br, "case FL_READONLY:", "n = ((fvar->flags & FV_RDONLY) != 0);", "goto set_integer;", "case FL_NON_TXN:", "case FL_NETFILE:", "n = 1;")
       and ordered(br, "case FL_SETRDONLY:", "if (process.program.flags & HDR_INTERNAL)", "fvar->flags |= FV_RDONLY;", "n = 0;", "goto set_integer;")
       and re.search(r"case FL_TXN_UPDATE:\s*\n\s*case FL_INDEX_SCAN:\s*\n\s*n = 0;", br) is not None, "")
    kio = fn("op_sh.c", "edit_kind_of_net_name")
    ck("S2v THE EDIT KIND OF A REMOTE NAME (spec 5.5, 7): op_sh.c defines edit_kind_of_net_name once - `dict ` in front is a dictionary, otherwise edit_kind_of_name (voc, *.dic, bp, bp.out, *.bp, *.bp.out); "
       "it does NOT use edit_kind_of_path (its private-catalogue test resolves against the working directory, wrong for a remote name); sd.h declares it; net_open_work stores it in the file variable AFTER the "
       "union is zeroed; and the union member holds the two u_char after the server name without growing (the layout is 16 + 2 + 2 + NET_SERVER_LEN + 1 + 2 bytes, 39, in the same 40 byte aligned size as before)",
       kio != "" and ordered(kio, "strncasecmp(name, \"dict \", 5) == 0", "return EDIT_DICT;", "return edit_kind_of_name(name);") and "edit_kind_of_path" not in kio and "getcwd" not in kio
       and c_header(shc, "edit_kind_of_net_name") == "intedit_kind_of_net_name(constchar*)" == c_proto(sdh, "edit_kind_of_net_name")
       and ordered(fn("netfiles.c", "net_open_work"), "memset(&fvar->access, 0, sizeof(fvar->access));", "fvar->access.net.edit_kind = (u_char)edit_kind_of_net_name(file);")
       and (lambda n: n is not None and (16 + 2 + 2 + int(n.group(1)) + 1 + 2 + 7) // 8 * 8 == (16 + 2 + 2 + int(n.group(1)) + 1 + 7) // 8 * 8 == 40)(re.search(r"#define\s+NET_SERVER_LEN\s+(\d+)", dsc)), "")
    ke = seg(kn_, "case K_EDIT_OK:", "case K_EDIT_OS_OK:")
    kj = seg(kn_, "case K_NET:", "case K_EDIT_OK:")
    ck("S2w K_EDIT_OK and K_EDIT_KIND take the FILE VARIABLE of a remote file as well as a pathname (spec 5.5): when the argument is a file reference (FILE_REF, k_get_file) of a NET_FILE the kind is the "
       "file variable's access.net.edit_kind and K_EDIT_OK is the administrator, or kind EDIT_NONE, or edit_permitted(kind); any OTHER file variable is refused (0) - a gate that fails open is decoration; a "
       "string argument behaves as before. K_NET -2 from a $internal program saves process.status, sends the queued closes (net_flush_closes) and gives the status back, and answers the gate as -1 does; "
       "from any other program -2 is -1 (the ask form); net_flush_closes is called nowhere else",
       ke != "" and ordered(ke, "if (descr->type == FILE_REF) {", "descr->data.fvar", "edit_fvar->type == NET_FILE", "access.net.edit_kind", "MY_ADMIN()", "EDIT_NONE", "edit_permitted(",
                            "break;", "edit_ok_for_path(edit_name)", "edit_kind_of_path(edit_name)")
       and re.search(r"else\s+result\.data\.value = [\w>.\-]*kind[\w]*;", ke) is not None            # K_EDIT_KIND answers the kind
       and re.search(r"if \(action == K_EDIT_OK\) \{\s*if \(MY_ADMIN\(\)\)\s*result\.data\.value = 1;\s*else if \(edit_fvar->type == NET_FILE\)\s*"
                     r"result\.data\.value = \(\(edit_fkind == EDIT_NONE\) \|\| edit_permitted\(edit_fkind\)\) \? 1 : 0;\s*\} else\s*result\.data\.value = edit_fkind;\s*break;", ke) is not None   # the whole file-variable arm, as one shape
       and kj != "" and ordered(kj, "(n == -2)", "process.program.flags & HDR_INTERNAL", "n = process.status;", "net_flush_closes();", "process.status = n;", "result.data.value = MY_GATE(UG_NET);", "break;")
       and re.search(r"if \(\(n == -2\) && \(process\.program\.flags & HDR_INTERNAL\)\) \{\s*n = process\.status;\s*net_flush_closes\(\);\s*process\.status = n;\s*"
                     r"result\.data\.value = MY_GATE\(UG_NET\);\s*break;\s*\}", kj) is not None      # the -2 branch as one shape: only a $internal program, and the answer is the gate
       and kn_.count("net_flush_closes()") == 1 and sum(t.count("net_flush_closes(") for k, t in c.items() if (k.endswith(".c") or k.startswith("c:")) and k not in ("netfiles.c", "op_kernel.c")) == 0, "")
    ck("S2x CPROC and edit_guard (spec 3.9): para.reset.environment calls kernel(K$NET, -2) as the very next line after the OS path cache flush (so a lock does not outlive its file variable at the "
       "prompt) and nowhere else; edit_guard, in the branch where the file has no pathname and BEFORE the administrator test, asks for a file on another server (fileinfo FL$NETFILE) and then K$EDIT.OK and "
       "K$EDIT.KIND of the FILE VARIABLE and shows edit_msg(kind) (S.66: the text for 11405 to 11407, 11513, 11514; the clamp is edit_msg's); a local file has FL$NETFILE 0 and takes the old path",
       re.search(r"para\.reset\.environment:\s*\n\s*i = ospath\(\"\", os\$flush\.cache\)\s*\n\s*void kernel\(K\$NET, -2\)", cp) is not None and cp.count("kernel(K$NET, -2)") == 1
       and ordered(eg, "p = fileinfo(f, FL$PATH)", "if p = '' then", "if fileinfo(f, FL$NETFILE) then", "if kernel(K$EDIT.OK, f) then return @true", "kind = kernel(K$EDIT.KIND, f)",
                   "display edit_msg(kind)", "return @false", "end", "if kernel(K$ADMINISTRATOR, -1) then return @true", "display sysmsg(11410)")
       and re.search(r"if fileinfo\(f, FL\$NETFILE\) then\s*if kernel\(K\$EDIT\.OK, f\) then return @true\s*kind = kernel\(K\$EDIT\.KIND, f\)\s*"
                     r"display edit_msg\(kind\)\s*return @false\s*end\s*if kernel\(K\$ADMINISTRATOR, -1\) then return @true", eg) is not None, "")      # the remote branch as one shape

    # ---- S2y. messages, history, the suite
    ck("S2y U10 messages 11509 to 11512 exist with EXACTLY the texts of the spec (one line each; the 231 byte bound once expanded is test-msglen-units.py's); 11513 onwards are the shared account's since S.66",
       all((srcs.get("msg:%d" % n) or "").rstrip("\n") == t for n, t in S2_MSG_TEXTS.items()), repr([n for n, t in S2_MSG_TEXTS.items() if (srcs.get("msg:%d" % n) or "").rstrip("\n") != t]))
    consts = {m.group(1): int(m.group(2)) for m in re.finditer(r"#define\s+((?:NETG|NET_LOCK|NET_ID)_[A-Z]+)\s+(\d+)\b", sdh)}
    mid = re.search(r"\$define\s+MAX\.ID\.LEN\s+(\d+)", c["syscom/keys.h"])
    ck("S2zb sd.h's constants for the entry points (spec 1.4): the statement kinds NETG_WRITE 1, NETG_DELETE 2, NETG_CLEAR 3, NETG_LOCK 4 and (S.72b) NETG_PEEK 5 - defined right after NETG_LOCK, with a comment "
       "that says what it is for (RECORDLOCKED(): the read-mode test of net_gate only); the answers of net_lock_step NET_LOCK_HELD 0, NET_LOCK_WAIT 1, "
       "NET_LOCK_LOCKED 2; NET_ID_MAX 63, which is the class's MAX.ID.LEN (syscom/keys.h) - the id a remote file can hold, tested before anything is sent",
       consts == {"NETG_WRITE": 1, "NETG_DELETE": 2, "NETG_CLEAR": 3, "NETG_LOCK": 4, "NETG_PEEK": 5, "NETG_ADMIN": 6, "NET_LOCK_HELD": 0, "NET_LOCK_WAIT": 1, "NET_LOCK_LOCKED": 2, "NET_ID_MAX": 63}   # NETG_ADMIN 6: S.73 item 3
       and re.search(r"#define NETG_LOCK 4[^\n]*\n#define NETG_PEEK 5[ \t]+/\*[^*\n]*RECORDLOCKED\(\)[^*\n]*read-mode[^*\n]*\*/\n#define NETG_ADMIN 6[ \t]+/\*[^*\n]*FCONTROL\(\)[^*\n]*\*/", srcs["sd.h"]) is not None
       and mid is not None and int(mid.group(1)) == consts.get("NET_ID_MAX"), repr(consts))
    suite = srcs["sandbox-netfile.py"]
    drv = suite[suite.find("NFH_DRIVER = r"):suite.find("NFH_SUB = r")]
    ck("S2za THE SUITE sandbox-netfile.py (spec 10 and 11): nfw and nfwb are defined MODE WRITE and nfa and nfb are not (the read-mode control stays as it was); the handler's driver calls the new operations "
       "and its prefix T makes a call inside BEGIN TRANSACTION; the marks of a record or an id are typed as place holders; the wire of the write rows is checked against encoders written in the suite from "
       "the spec (W_WRITE, W_DEL, W_LOCK - flags 3 and 2, the no-wait forms -, W_REL, W_CLEAR); the lock table is WATCHED during a session and a holder is let go a fixed time after the first lock request; the "
       "sections hwrite and kwrite run after timeout and before kernel and gaps; the refusal matrix KM and KALLOWED stand as they were",
       re.search(r'define\("nfw", A\.port, pa, [^\n]*mode="write"\)', suite) is not None and re.search(r'define\("nfa", A\.port, pa, "[^"]*", alA\)\n', suite) is not None
       and re.search(r'define\("nfb", B\.port, pb, "[^"]*", alB\)\n', suite) is not None and re.search(r'define\("nfwb", B\.port, pb, [^\n]*mode="write"\)', suite) is not None
       and re.search(r"if nm\[1,1\] = 'T' then\s*\n\s*intxn = @true", drv) is not None and "begin transaction" in drv and all(re.search(r"op = %s\b" % re.escape(k).replace(r"\$", "[$]"), drv) for k in ("NF$WRITEU", "NF$DELETEU", "NF$RELEASE"))
       and "change(b, '<F>', @fm)" in drv and "change(c, '<F>', @fm)" in drv and "NM_RX" in suite
       and "struct.pack(\"<h\", 3 if upd else 2)" in suite and all(("def %s(" % f) in suite for f in ("W_WRITE", "W_DEL", "W_LOCK", "W_REL", "W_CLEAR", "W_RLK", "W_READ", "wreset", "hw_go"))
       and "class LockWatch(" in suite and "class HolderRelease(" in suite and re.search(r"time\.sleep\(self\.delay\)\s*\n\s*self\.srv\.store\.drop_user\(self\.userno\)", suite) is not None
       and "30 in ses.requests" in suite
       and suite.find('("timeout", timeout_section)') < suite.find('("hwrite", hwrite_section)') < suite.find('("kwrite", kwrite_section)') < suite.find('("kernel", kernel_section)') < suite.find('("gaps", gaps_section)')
       and 'KALLOWED = {47, 48, 3, 4, 5, 6, 1}' in suite and 'km("write", "write \'zz\' to f, \'c1\'"' in suite and 'km("recordlocku"' in suite and 'km("release"' in suite
       and 'KWALLOWED = {47, 48, 3, 4, 5, 6, 1, 15, 16, 17, 18, 19, 30, 31, 34}' in suite, "")
    texts_ = {n: (srcs.get(n) or "") for n in ("netfiles.c", "sd.h", "op_dio2.c", "op_dio3.c", "op_lock.c", "bp:netfile", "bp:netfile.h", "sandbox-netfile.py", "netfake.py")}
    lack = [n for n, t in texts_.items() if not re.search(r"18 Oct 26 dm\s+S\.65 slice 3e", t)]
    ck("S2z the dated history lines are there: every file slice 3e changed says `18 Oct 26 dm  S.65 slice 3e` (%d files here; the six others are checked with their own checks), and this check's own file says so"
       % len(texts_), not lack and "slice 3e" in (__doc__ or "") and "S2" in (__doc__ or ""), repr(lack))


# ---- S72. S.72 (20 Oct 26): QMNet parity, tiers A and B ---------------------------------------------------------------------------------------------

S72_FILES_CHG = (7, 8, 9, 10, 16, 17, 18, 19, 30, 31, 32, 33, 34)      # the requests a files-only login may make ONLY with the write group (apifilesok files.chg): 32, 33 and, since S.72b (20 Oct 26), 34 (recordlocked)


def checks_s72(srcs, c, ck):
    """S.72 (20 Oct 26), written from the spec BEFORE the code and shown red on the unchanged tree: RECORDLOCKED() and GETLOCKS() of a remote file (tier A) and FILELOCK / FILEUNLOCK of one on a
    write-mode server (tier B).  Text only.  ***WHAT THIS CANNOT SAY: that a file lock is taken, that RECORDLOCKED() answers what the server holds, that STATUS() is the owner's number or that a
    busy file is waited for - the sections hwrite, kwrite and wgroup of sandbox-netfile.py, against the fake, and sandbox-req29.py section F against the real server.***"""
    nf, hb, hraw, hdr = c["netfiles.c"], c["bp:netfile"], srcs["bp:netfile"], srcs["bp:netfile.h"]
    lk, erh, ap, fo = c["op_lock.c"], c["err.h"], c["apisrvr"], c["apifilesok"]
    sc, scraw, suite = c["bp:sdclient"], srcs["bp:sdclient"], srcs["sandbox-netfile.py"]

    def fn(fname, name):
        return c_functions(c.get(fname) or c.get("c:" + fname, "")).get(name, "")

    def rb(label):
        return routine_body(hb, label)

    # ---- S72a. FILELOCK: op_filelock's NET branch, in order
    of = fn("op_lock.c", "op_filelock")
    nb = seg(of, "if (fvar->type == NET_FILE)", "file_id = fvar->file_id;", include_end=False)
    decl = re.search(r"u_char\s*\*\s*retry_pc\s*=\s*op_pc;", of)
    ck("S72a FILELOCK of a NET_FILE (op_lock.c op_filelock), in this ORDER: `u_char* retry_pc = op_pc;` is taken FIRST (before the file variable is found and before any net_ call: the handler's own "
       "opcodes overwrite op_pc); the NET_FILE test comes before the first FPtr( and before the local code; net_filelock_step(fvar, op_flags, retry_pc) is called; then the four answers - HELD is 0, WAIT "
       "RETURNS AT ONCE leaving the operand on the stack, LOCKED is ER_LCK (the holder is in STATUS()), anything else is the error status net_filelock_step left in process.status; then "
       "process.op_flags = 0, the operand is dismissed and the status pushed as an integer, and the opcode returns; the branch touches no file table (no FPtr, no StartExclusive), sets no pc "
       "(net_lock_result does) and calls no net_refuse",
       of != "" and nb != "" and decl is not None and 0 <= decl.start() < of.find("k_get_file(") and decl.start() < of.find("net_filelock_step(")
       and 0 <= of.find("net_filelock_step(") < of.find("FPtr(") and of.find("fvar->type == NET_FILE") < of.find("FPtr(")
       and ordered(of, "op_flags = process.op_flags;", "k_get_file(descr);", "if (fvar->type == NET_FILE)", "net_filelock_step(fvar, op_flags, retry_pc)", "file_id = fvar->file_id;", "fptr = FPtr(file_id);")
       and ordered(nb, "net_filelock_step(fvar, op_flags, retry_pc)", "case NET_LOCK_HELD:", "case NET_LOCK_WAIT:", "return;", "case NET_LOCK_LOCKED:", "status = ER_LCK;", "default:",
                   "(int16_t)process.status", "process.op_flags = 0;", "k_dismiss();", "InitDescr(e_stack, INTEGER);", "(e_stack++)->data.value = status;", "return;")
       and re.search(r"case NET_LOCK_HELD:\s*status = 0;\s*break;", nb) is not None and re.search(r"case NET_LOCK_WAIT:[^\n]*\n\s*return;", nb) is not None
       and re.search(r"case NET_LOCK_LOCKED:[^\n]*\n\s*status = ER_LCK;\s*break;", nb) is not None
       and re.search(r"default:[^\n]*\n\s*status = \(int16_t\)process\.status;\s*break;", nb) is not None
       and not re.search(r"FPtr\(|StartExclusive|net_refuse\(|(?<![\w.])pc\s*(?:--|=(?!=))", nb) and "pc = retry_pc" not in of and "net_refuse(" not in of, repr(nb[:80]))

    # ---- S72b. net_filelock_step and the tail it shares with net_lock_step
    fs, fl_ = fn("netfiles.c", "net_filelock_step"), fn("netfiles.c", "net_filelock")
    ck("S72b net_filelock_step: net_gate(fvar, NETG_LOCK, op_flags, \"FILELOCK\") is asked FIRST (a read-mode handle is 11501, a transaction 11510; the S.64 edit gate is not asked of a lock) and a nonzero "
       "answer is returned AT ONCE - the refusal has been made and raised unless ON ERROR, nothing is sent; then ONE request, with only the ON ERROR bit in process.op_flags and 0 again straight after, "
       "through the Private net_filelock, which is net_change_op(NF_FILELOCK) with lock_op TRUE and NO wait argument at all (the server is never made to block); then net_lock_result(st, op_flags, "
       "retry_pc) - the one tail net_lock_step also uses.  NF_FILELOCK is named in the request and in the define, nowhere else",
       fs != "" and fl_ != ""
       and ordered(fs, "net_gate(fvar, NETG_LOCK, op_flags, \"FILELOCK\")", "if (st != 0)", "return st;", "process.op_flags = op_flags & P_ON_ERROR;", "net_filelock(fvar)", "process.op_flags = 0;",
                   "return net_lock_result(st, op_flags, retry_pc);")
       and re.search(r"if \(st != 0\)\s*return st;", fs) is not None and fs.count("net_gate(") == 1 and fs.count("net_filelock(") == 1 and "NETG_WRITE" not in fs and "NETG_CLEAR" not in fs
       and re.search(r'return net_change_op\(fvar, NF_FILELOCK, "", 0, "", 0, NULL, FALSE, TRUE\);', fl_) is not None and nf.count("NF_FILELOCK") == 2
       and c_header(nf, "net_filelock") == "Privateintnet_filelock(FILE_VAR*)"
       and "net_lock_result(" in fn("netfiles.c", "net_lock_step") and nf.count("net_lock_result(") == 3, repr(fs[:80]))

    # ---- S72c. net_fileunlock
    fu = fn("netfiles.c", "net_fileunlock")
    swt = seg(fu, "switch (net_reply_status) {", "process.status = answer;", include_end=False)
    ck("S72c net_fileunlock: net_gate(fvar, NETG_LOCK, op_flags, \"FILEUNLOCK\") FIRST and a nonzero answer returned at once; one request (net_change_op with NF_FILEUNLOCK, lock_op FALSE: a busy answer is "
       "not understood here), with only the ON ERROR bit set and 0 again after it; an error status (negative) returned as it is; then the server's reply STATUS(), read from net_reply_status, is accepted "
       "ONLY as 0, ER_LCK or ER_NLK (the three values a local FILEUNLOCK leaves in STATUS(); ER_LCK is 3011 and ER_NLK 3012) and ANYTHING ELSE is an error - message 11507 'it gave an answer that this "
       "statement cannot use', -ER_NETWORK, raised unless the statement has ON ERROR (op_flags, not 0); process.status is set to the answer and the answer (>= 0) is returned",
       fu != "" and swt != ""
       and ordered(fu, "net_gate(fvar, NETG_LOCK, op_flags, \"FILEUNLOCK\")", "if (st != 0)", "return st;", "process.op_flags = op_flags & P_ON_ERROR;", "net_change_op(fvar, NF_FILEUNLOCK", "process.op_flags = 0;",
                   "if (st < 0)", "return st;", "switch (net_reply_status) {", "case 0:", "answer = 0;", "case ER_LCK:", "answer = ER_LCK;", "case ER_NLK:", "answer = ER_NLK;", "default:",
                   "net_set_message(MSG_HANDLER, \"it gave an answer that this statement cannot use\"", "return net_raise(-ER_NETWORK, op_flags);", "process.status = answer;", "return answer;")
       and re.findall(r"case\s+(\w+)\s*:", swt) == ["0", "ER_LCK", "ER_NLK"] and swt.count("default:") == 1
       and re.search(r'net_change_op\(fvar, NF_FILEUNLOCK, "", 0, "", 0, NULL, FALSE, FALSE\)', fu) is not None and fu.count("net_gate(") == 1 and nf.count("NF_FILEUNLOCK") == 2
       and re.search(r"#define\s+ER_LCK\s+3011\b", erh) is not None and re.search(r"#define\s+ER_NLK\s+3012\b", erh) is not None, repr(swt[:80]))

    # ---- S72d. net_recordlocked, net_lock_code, net_check_lock
    rk, lc, ncl = fn("netfiles.c", "net_recordlocked"), fn("netfiles.c", "net_lock_code"), fn("netfiles.c", "net_check_lock")
    gate_call = 'net_gate(fvar, NETG_PEEK, 0, "RECORDLOCKED")'
    gpos, lpos = rk.find(gate_call), rk.find("net_lock_code(fvar, id, id_len, &code)")
    ck("S72d net_recordlocked (RECORDLOCKED() of a remote file), S.72b: net_gate(fvar, NETG_PEEK, 0, \"RECORDLOCKED\") is asked FIRST, before net_lock_code and so before anything is sent - the read-mode test of the gate "
       "and nothing else: a read-mode handle is 11501 and -7000, a transaction is NOT refused (it is a read: the recorded choice) - with the LITERAL 0 for the statement's flags (never process.op_flags, never P_ON_ERROR: "
       "RECORDLOCKED() has no ON ERROR clause, so the refusal is always raised); it is the ONLY gate in the function, and a nonzero answer returns at once, before the request; no net_refuse; errors are RAISED ALWAYS - "
       "process.op_flags is set to 0 BEFORE the request, so that a flag a previous statement left (an ON ERROR) cannot swallow an error of a function that has no ON ERROR clause; the code is the "
       "server's, -3 to 3, and a code outside it is an error (11507, -ER_NETWORK, raised with 0); STATUS() is the owner's user number from net_reply_status ONLY when it is 0 to 32767, else 0.  The request "
       "is net_lock_code, the Private core it shares with net_check_lock (MUSTLOCK) and which asks NO gate: empty or long id first (net_bad_id), net_op_ex of NF_RECORDLOCKED with pass_status TRUE, process.op_flags back, an ELSE "
       "answer an error, a negative status raised, the code read from the answer; net_check_lock keeps its meaning (1 for the codes 2 and 3, 0 for the rest, process.status 0) and is no more than a caller of it",
       rk != "" and lc != "" and ncl != "" and rk.count("net_gate(") == 1 and rk.count(gate_call) == 1 and 0 <= gpos < lpos and re.search(r"\breturn\b", rk[gpos:lpos]) is not None
       and 0 <= rk.find("process.op_flags = 0;") < lpos and "net_gate(" not in lc + ncl and "net_refuse(" not in rk + lc + ncl
       and ordered(rk, "process.op_flags = 0;", "net_lock_code(fvar, id, id_len, &code)", "if ((code < -3) || (code > 3)) {", "net_set_message(MSG_HANDLER", "net_raise(-ER_NETWORK, 0)", "owner = net_reply_status;",
                   "process.status = ((owner >= 0) && (owner <= 32767)) ? owner : 0;", "return code;")
       and ordered(lc, "*code = 0;", "(id_len < 1) || (id_len > NET_ID_MAX)", "return net_bad_id(fvar, id_len);", "net_op_ex(fvar, NF_RECORDLOCKED, id, id_len,", "FALSE, TRUE, &out)", "process.op_flags = entry;",
                   "if (status > 0) {", "net_set_message(MSG_HANDLER", "status = -ER_NETWORK;", "if (status < 0)", "return net_raise(status, entry);", "*code = atoi(buf);", "return 0;")
       and ordered(ncl, "net_lock_code(fvar, id, id_len, &code)", "if (status < 0)", "return status;", "process.status = 0;", "((code == 2) || (code == 3)) ? 1 : 0")
       and nf.count("net_lock_code(") == 3 and "net_op_ex(" not in ncl + rk, repr(rk[:80]))

    # ---- S72e. rc<8>, the server's reply STATUS(), from the handler to the kernel
    rcm = re.search(r"typedef struct \{(.*?)\} NET_RC;", nf, re.S)
    prc, opx = fn("netfiles.c", "net_parse_rc"), fn("netfiles.c", "net_op_ex")
    readers = sorted(n for n, b in c_functions(nf).items() if "net_reply_status" in b)
    ck("S72e rc<8> (the server's reply STATUS(), trusted for exactly two operations): NET_RC has `int reply_status;` after mode_write; net_parse_rc reads field 8 after field 7 (absent is 0); the Private "
       "net_reply_status is 0 at the top of net_op_ex (before the stale test, so a call that did not run leaves 0) and is set from the reply right after the handler call (0 when it did not run) and "
       "before process.op_flags is given back; and it is READ by net_fileunlock and net_recordlocked, and (S.73 item 3) by net_last_reply_status, which hands it to the administration statements "
       "(the verb's return code, what FCONTROL left), and (S.73 item 3 D1) by net_index_query, which hands it to the index statements (0 done, 1 no such index or no further key); net_create_file sets it from its own "
       "handler call as net_op_ex does - no other function of netfiles.c mentions it",
       rcm is not None and ordered(rcm.group(1), "int mode_write;", "int reply_status;") and re.search(r"^Private int net_reply_status = 0;", nf, re.M) is not None
       and ordered(prc, "net_field(buf, 7, num, sizeof(num));", "rc->mode_write = (atoi(num) == 1);", "net_field(buf, 8, num, sizeof(num));", "rc->reply_status = atoi(num);")
       and ordered(opx, "net_reply_status = 0;", "if (net_stale(fvar))", "net_call_core(", "net_reply_status = ran ? rc.reply_status : 0;", "process.op_flags = entry;", "net_answer(")
       and readers == ["net_create_file", "net_fileunlock", "net_index_query", "net_last_reply_status", "net_op_ex", "net_recordlocked"], repr(readers))

    # ---- S72f. op_flunlock
    ofu = fn("op_lock.c", "op_flunlock")
    nb2 = seg(ofu, "if (fvar->type == NET_FILE)", "file_id = fvar->file_id;", include_end=False)
    ck("S72f FILEUNLOCK of a NET_FILE (op_flunlock): the statement's flags are taken from process.op_flags before the file variable is found; the NET_FILE test comes before the first FPtr(; net_fileunlock(fvar, "
       "op_flags) is called (the gate is its first act), then process.op_flags = 0, the operand is dismissed and the status pushed as a 16 bit integer; the branch reads no file table and calls no net_refuse "
       "(the local branch is unchanged: a local FILEUNLOCK never took ON ERROR)",
       ofu != "" and nb2 != "" and "net_refuse(" not in ofu
       and ordered(ofu, "op_flags = process.op_flags;", "k_get_file(descr);", "if (fvar->type == NET_FILE)", "net_fileunlock(fvar, op_flags)", "file_id = fvar->file_id;", "fptr = FPtr(file_id);")
       and ordered(nb2, "net_fileunlock(fvar, op_flags)", "process.op_flags = 0;", "k_dismiss();", "InitDescr(e_stack, INTEGER);", "(e_stack++)->data.value = (int16_t)", "return;")
       and "FPtr(" not in nb2, repr(nb2[:80]))

    # ---- S72g. op_reclckd
    orc = fn("op_lock.c", "op_reclckd")
    nb3 = seg(orc, "if (fvar->type == NET_FILE)", "file_id = fvar->file_id;", include_end=False)
    ck("S72g RECORDLOCKED() of a NET_FILE (op_reclckd): the empty id is k_illegal_id first, as locally; the NET_FILE test comes before the first FPtr(; net_recordlocked(fvar, id, id_len) is called (an "
       "error does not return: it is raised); then BOTH operands are dismissed (the id and the file variable - the handler ran BASIC, so they are found by e_stack) and the code is pushed as an "
       "integer; no net_refuse, no file table",
       orc != "" and nb3 != "" and "net_refuse(" not in orc
       and ordered(orc, "k_get_c_string(descr, id, sysseg->maxidlen)", "k_illegal_id(descr);", "k_get_file(descr);", "if (fvar->type == NET_FILE)", "net_recordlocked(fvar, id, id_len)", "file_id = fvar->file_id;", "fptr = FPtr(file_id);")
       and ordered(nb3, "net_recordlocked(fvar, id, id_len)", "k_dismiss();", "k_dismiss();", "InitDescr(e_stack, INTEGER);", "(e_stack++)->data.value = status;", "return;")
       and nb3.count("k_dismiss();") == 2 and "FPtr(" not in nb3, repr(nb3[:80]))

    # ---- S72h. GETLOCKS
    ogl = fn("op_lock.c", "op_getlocks")
    ck("S72h GETLOCKS(f, user) of a NET_FILE (op_getlocks) is the LOCAL view and asks the server NOTHING: NO_LOCAL_FILE is 0 (file ids start at 1: FPtr(1), `for (i = 1 ...` - so no lock, file lock or "
       "waiter carries it, and -1 stays every file); a NET_FILE is given file_id = NO_LOCAL_FILE in place of its own file_id (-1, which would list every lock of every user) and any other file variable keeps "
       "its file_id; the NET_FILE test comes first; the function calls no net_ function at all; the counters of field 1 are written as before; and the LOCK-WAITERS section is skipped for it "
       "(`if (file_id == NO_LOCAL_FILE) { lo = 1; hi = 0; }` is the FIRST arm of the block that sets lo and hi, so the loop runs no time) BEFORE the `UMap(user)` read of the last arm - the user number "
       "asked for is nobody's business for a remote file, and getlocks(f, 12345) of one faulted the process (measured: Fault type 11) when UMap() was indexed with it",
       re.search(r"#define\s+NO_LOCAL_FILE\s+0\b", lk) is not None and lk.count("NO_LOCAL_FILE") == 3 and ogl != "" and "for (i = 1, fptr = FPtr(1); i <= sysseg->used_files; i++, fptr++)" in ogl
       and re.search(r"if \(file_id == NO_LOCAL_FILE\) \{\s*lo = 1;\s*hi = 0;\s*\} else if \(user == 0\) \{\s*lo = 1;\s*hi = sysseg->max_users;\s*\} else \{\s*lo = hi = \*\(UMap\(user\)\);\s*\}", ogl) is not None
       and 0 <= ogl.find("file_id == NO_LOCAL_FILE") < ogl.find("UMap(user)") and ogl.count("UMap(") == 1 and ogl.count("for (i = lo; i <= hi; i++)") == 1
       and re.search(r"if \(descr->data\.fvar->type == NET_FILE\)\s*file_id = NO_LOCAL_FILE;\s*else\s*file_id = descr->data\.fvar->file_id;", ogl) is not None
       and ogl.find("NET_FILE") < ogl.find("descr->data.fvar->file_id") and not re.search(r"\bnet_\w+\(", ogl) and "file_id = -1;" in ogl
       and ordered(ogl, "ts_printf(\"%d\\xfd%d\\xfd%d\", sysseg->numlocks, sysseg->rl_count,", "sysseg->rl_peak);"), "")

    # ---- S72i. the four sites are not refusals any more, and each tests NET_FILE before it reads a file id
    bad4 = []
    for fname, name in sorted(NK_LOCKSITES):
        body = fn(fname, name)
        if not body:
            bad4.append("%s: function not found" % name)
            continue
        if re.search(r"net_refuse\(|refuse_net_file\(", body):
            bad4.append("%s: still refuses" % name)
        first = min([body.find(x) for x in ("FPtr(", "fvar->file_id", "descr->data.fvar->file_id") if body.find(x) >= 0] or [10 ** 9])
        if not (0 <= body.find("NET_FILE") < first):
            bad4.append("%s: NET_FILE is not tested before the first read of a file id" % name)
        dang = [body.find(x) for x in NK_DANGER if body.find(x) >= 0]      # the old NK7 rule, kept: nothing that reads or writes the file table, a lock or a select list comes first
        if dang and min(dang) < body.find("NET_FILE"):
            bad4.append("%s: %r comes before the NET_FILE test" % (name, body[min(dang):min(dang) + 24]))
    ck("S72i THE FOUR LOCK SITES (NK_LOCKSITES: op_filelock, op_flunlock, op_getlocks, op_reclckd) refuse nothing in their own body since S.72 - none calls net_refuse or refuse_net_file (a read-mode handle is "
       "refused by the gate inside net_filelock_step, net_fileunlock and, since S.72b, net_recordlocked) - and each tests for NET_FILE "
       "BEFORE its first FPtr( or read of a file id; none of them is in the census table NK_REFUSE (NK7 counts %d sites) and the table of the decided ones holds all four (NK8)" % len(NK_REFUSE),
       not bad4 and len(NK_LOCKSITES) == 4 and not (NK_LOCKSITES & set(NK_REFUSE)), repr(bad4))

    # ---- S72j. the handler: the dispatch and act.change's FILELOCK arm
    ac = rb("act.change")
    main = hb[:hb.find("\nact.open:")] if "\nact.open:" in hb else hb
    ab = seg(ac, "aud.k = 'w'", "obj = nf.s.obj(slot)", include_end=False)
    rqb = seg(ac, "obj = nf.s.obj(slot)", "lerr = obj->LastError", include_end=False)
    ck("S72j NF$FILELOCK in the handler: the dispatch sends it to act.change (and NF$FILEUNLOCK to act.fileunlock); in act.change its name is 'filelock'; it is NOT a change (changing is false: a lost reply "
       "is 11497, as for a record lock); it has NO record id, so check.id.chg is skipped for it as for CLEARFILE and an empty b is fine; it is audited ONCE for the handle - the letter 'f' and the line "
       "`netfile filelock server=<name> file=<remote file>` through audit.once, never a direct kernel(K$AUDIT) and never with an id - before the request; the request is `obj->error = ''`, the "
       "no-reply mark, then obj->filelock(nf.h.fno(hx), @false) with the wait flag the literal @false (the server is never made to block); the busy answer (LastError LOCKED) is rc.locked for it as for "
       "NF$LOCK, rc<1> 4 and rc<6> the holder - not an error",
       re.search(r"op = NF\$LOCK or op = NF\$FILELOCK\s*\n\s*gosub act\.change", main) is not None and re.search(r"case op = NF\$FILEUNLOCK\s*;\s*gosub act\.fileunlock", main) is not None
       and re.search(r"case op = NF\$FILELOCK\s*;\s*opname = 'filelock'", ac) is not None and "changing = (op # NF$LOCK and op # NF$FILELOCK)" in ac
       and re.search(r"if op # NF\$CLEARFILE and op # NF\$FILELOCK then\s*\n\s*gosub check\.id\.chg", ac) is not None
       and ordered(ab, "case op = NF$FILELOCK", "aud.k = 'f'", "aud.line = 'netfile filelock server=' : srvname : ' file=' : nf.h.file(hx)", "gosub audit.once")
       and sorted(re.findall(r"aud\.k = '(\w)'", hb)) == ["d", "f", "r", "r", "w", "w"] and "kernel(K$AUDIT, 'netfile filelock" not in hb      # S.73 item 3: admin.prepare writes 'r' and act.seqkey 'w' once more
       and ordered(rqb, "case op = NF$FILELOCK", "obj->error = ''", "obj->ServerStatus = NF$NOREPLY", "obj->filelock(nf.h.fno(hx), @false)", "case 1")
       and re.search(r"if \(op = NF\$LOCK or op = NF\$FILELOCK\) and lerr = NF\$LE\.LOCKED then\s*\n\s*gosub rc\.locked\s*\n\s*return", ac) is not None
       and ordered(ac, "gosub audit.once", "obj = nf.s.obj(slot)", "obj->filelock(", "lerr = obj->LastError"), repr(ac[:60]))

    # ---- S72k. act.fileunlock
    afu = rb("act.fileunlock")
    ck("S72k act.fileunlock (NF$FILEUNLOCK), in this ORDER: the handle of this account (a lost one will do); its name is 'fileunlock'; a handle whose mode is not write is REFUSED (act.refuse, 11501) BEFORE "
       "the gate and the connection are asked; the handle again with the gate and the connection; a transaction is 11510; the request marked with the no-reply mark; a missing reply is LOST (11497 - NOT "
       "11509: a lock changes no data); a server error; an ON ERROR reply through on.error.text; any other answer 11504; and only on success rc<8> = rq.st, the reply STATUS(), as the LAST act.  It does NOT "
       "read the definition again (no mode.now: a lock that is held must always be able to be given back, and giving it back changes no data - the rule of RELEASE), is not audited, is not a change "
       "(`changing` is not touched) and sends nothing in a transaction or for a read-mode handle",
       afu != "" and ordered(afu, "need.gate = @false ; need.conn = @false ; any.acct = @false ; allow.lost = @true", "gosub get.handle", "if failed then return", "opname = 'fileunlock'",
                             "if nf.h.mode(hx) # 'write' then", "gosub act.refuse", "return",
                             "need.gate = @true ; need.conn = @true ; any.acct = @false ; allow.lost = @false", "gosub get.handle", "if failed then return",
                             "if system(SYS$TRANS_LEVEL) # 0 then", "fail.num = 11510", "gosub fail", "return",
                             "obj = nf.s.obj(slot)", "obj->error = ''", "obj->ServerStatus = NF$NOREPLY", "obj->fileunlock(nf.h.fno(hx))", "lerr = obj->LastError", "gosub after.rq", "nf.requests += 1",
                             "if lerr = -1 then rq.lost = @true", "if rq.lost then", "gosub lost.fail", "return", "if rq.err then", "gosub server.fail", "return",
                             "if lerr = NF$LE.ERROR then", "gosub on.error.text", "gosub server.fail", "return", "if lerr # NF$LE.OK then", "fail.num = 11504", "gosub fail", "return",
                             "rc<8> = rq.st", "return")
       and not re.search(r"mode\.now|mode\.ok|K\$AUDIT|audit\.once|\bchanging\b|rc\.locked|check\.id|NF\$LE\.LOCKED", afu) and afu.count("get.handle") == 2 and afu.count("fail.num = 11510") == 1
       and afu.count("rc<8>") == 1 and re.search(r"rc<8> = rq\.st\s*\n\s*return\s*$", afu) is not None, repr(afu[:60]))

    # ---- S72l. act.recordlocked gives the owner's number
    arl = rb("act.recordlocked")
    ck("S72l act.recordlocked (NF$RECORDLOCKED) gives the server's reply STATUS() - the user number of the lock's OWNER on the server - in rc<8> on success ONLY (after the lost and the server-error exits, "
       "after `out = lk`); rc<8> is set in these two routines and, since S.73 item 3, in admin.outcome (the verb's return code or what FCONTROL left; the index queries' server STATUS() comes the same way) and, since its D1, "
       "act.indexq reads it after that and puts it back after the second request of a scan (st1), and nowhere else in the handler, so the kernel reads it for exactly "
       "those operations (RECORDLOCKED, FILEUNLOCK, the four administration operations and the index queries)",
       arl != "" and ordered(arl, "gosub after.rq", "if rq.lost then", "gosub lost.fail", "return", "if rq.err then", "gosub server.fail", "return", "out = lk", "rc<8> = rq.st", "return")
       and arl.count("rc<8>") == 1 and hb.count("rc<8>") == 6 and "rc<8>" in afu and "rc<8>" in rb("admin.outcome")
       and ordered(rb("act.indexq"), "gosub admin.outcome", "rc<8> = 0", "st1 = rc<8>", "obj->readlist(NF$LIST, e)", "out = key : @fm : lst", "rc<8> = st1") and rb("act.indexq").count("rc<8>") == 3, "")

    # ---- S72m. the class
    flk = re.search(r"public subroutine filelock\(fno, wait\)\s*\n(.*?)\nend\s*\n", sc, re.S)
    fulk = re.search(r"public subroutine fileunlock\(fno\)\s*\n(.*?)\nend\s*\n", sc, re.S)
    flk, fulk = (flk.group(1) if flk else ""), (fulk.group(1) if fulk else "")
    ck("S72m THE CLASS (gpl.bp/sdclient): filelock(fno, wait) sends request 32 (SrvrFilelock) with two 16 bit numbers, the file number and then 1 if wait else 0, and fileunlock(fno) sends request 33 "
       "(SrvrFileunlock) with the file number only; both honour quiet - the abort 'FILELOCK generated an abort event' / 'FILEUNLOCK generated an abort event' is taken on an ON ERROR reply only when "
       "not(quiet) - and are listed in the header; SrvrFilelock is 32, SrvrFileunlock 33 and SrvrRecordlocked 34 (and SrvrClearfile is still 31) and each of the first two is used by its method alone; "
       "this is the wire apisrvr reads: vb.filelock takes fno then wait, both as 'ISL' (two bytes), vb.fileunlock takes fno",
       flk != "" and fulk != ""
       and ordered(flk, "context.error(CX.CONNECTED)", "pkt = iconv(fno, 'ISL')", "if wait then 1 else 0", "'ISL')", "message.pair(SrvrFilelock, pkt)", "not(quiet)", "abort 'FILELOCK generated an abort event'")
       and re.search(r"pkt := iconv\(\(?if wait then 1 else 0\)?, 'ISL'\)", flk) is not None and flk.count("iconv(") == 2
       and ordered(fulk, "context.error(CX.CONNECTED)", "pkt = iconv(fno, 'ISL')", "message.pair(SrvrFileunlock, pkt)", "not(quiet)", "abort 'FILEUNLOCK generated an abort event'") and fulk.count("iconv(") == 1
       and re.search(r"if server\.error = SV\$ON\.ERROR and not\(quiet\) then\s*\n\s*abort 'FILELOCK generated an abort event'", flk) is not None
       and re.search(r"if server\.error = SV\$ON\.ERROR and not\(quiet\) then\s*\n\s*abort 'FILEUNLOCK generated an abort event'", fulk) is not None
       and all(re.search(r"\$define %s\s+%d\b" % (w, v), sc) is not None for w, v in (("SrvrFilelock", 32), ("SrvrFileunlock", 33), ("SrvrRecordlocked", 34), ("SrvrClearfile", 31)))
       and sc.count("SrvrFilelock") == 2 and sc.count("SrvrFileunlock") == 2
       and re.search(r"^\*\s*obj->filelock\(fno, wait\)\s*$", scraw, re.M) is not None and re.search(r"^\*\s*obj->fileunlock\(fno\)\s*$", scraw, re.M) is not None
       and re.search(r"vb\.filelock:\s*\n\s*fno = oconv\(cmnd\[1,2\], 'ISL'\)\s*\n\s*wait = oconv\(cmnd\[3,2\], 'ISL'\)", ap) is not None
       and re.search(r"vb\.fileunlock:\s*\n\s*fno = oconv\(cmnd\[1,2\], 'ISL'\)", ap) is not None, "")

    # ---- S72n. the server: 32, 33 and (S.72b) 34 are in the change set
    chg = sorted(int(x) for x in re.findall(r"^files\.chg := '(\d+),'", fo, re.M))
    ok_ = sorted(int(x) for x in re.findall(r"^files\.ok := '(\d+),'", fo, re.M))
    ck("S72n apifilesok (S.72b, 20 Oct 26: request 34 JOINS the change set; until then it was a read): a files-only login without the write group is refused the CHANGE SET %s, which holds 32 (filelock), "
       "33 (fileunlock) and 34 (recordlocked - the answer is the lock owner's user number on this server), once each; all three are in the allowed table (37 numbers since S.65, 41 with the four of S.73 item 3), so a login with the "
       "group may make them and a files-on-only login is refused 32, 33 and 34 with 11521 and audited as `api refused request=<n> route=sdfiles write=off admin=<on|off>` (apisrvr's generic refusal, not changed for them; "
       "the admin word is S.73 item 3's)" % (S72_FILES_CHG,),
       chg == sorted(S72_FILES_CHG) and 32 in chg and 33 in chg and 34 in chg and {32, 33, 34} <= set(ok_) and len(ok_) == 41 and "files.chg = ','" in fo, repr((chg, ok_)))

    # ---- S72o. the numbers agree across the files (netfile.h, netfiles.c and the suite are NF1, NK1b, NF11)
    ck("S72o the NUMBERS the three layers share: the handler's header says the rc<8> values 3011 (ER$LCK) and 3012 (ER$NLK) and the operation codes 18 and 19; ER_LCK is 3011 and ER_NLK 3012 (err.h) - "
       "the two values net_fileunlock accepts; netfiles.c defines NF_FILELOCK 18 and NF_FILEUNLOCK 19 and netfile.h NF$FILELOCK 18 and NF$FILEUNLOCK 19 (17 and 20 are unused)",
       "3011" in hdr and "3012" in hdr and re.search(r"\$define\s+NF\$FILELOCK\s+18\b", hdr) is not None and re.search(r"\$define\s+NF\$FILEUNLOCK\s+19\b", hdr) is not None
       and re.search(r"#define\s+NF_FILELOCK\s+18\b", nf) is not None and re.search(r"#define\s+NF_FILEUNLOCK\s+19\b", nf) is not None
       and re.search(r"#define\s+ER_LCK\s+3011\b", erh) is not None and re.search(r"#define\s+ER_NLK\s+3012\b", erh) is not None, "")

    # ---- S72p. the history lines
    lack = [n for n in ("netfiles.c", "op_lock.c", "sd.h", "bp:netfile", "bp:netfile.h", "bp:sdclient") if not re.search(r"20 Oct 26 dm\s+S\.72", srcs[n])]
    ck("S72p the dated history lines are there: every production file S.72 changed (netfiles.c, op_lock.c, sd.h, gpl.bp/netfile, gpl.bp/netfile.h, gpl.bp/sdclient) says `20 Oct 26 dm  S.72`, and this "
       "check's own file says so", not lack and "20 Oct 26 dm  S.72" in (__doc__ or ""), repr(lack))

    # ---- S72q. the suite
    kws = re.search(r"KW_STILL_REFUSED = \(([^)]*)\)", suite)
    still = re.findall(r'"(\w+)"', kws.group(1)) if kws else ["?"]
    ck("S72q THE SUITE sandbox-netfile.py carries the S.72 rows: class_filelocks (the class methods, requests 32 and 33), hw_filelocks (the handler's operations 18 and 19 and the rc<8> of RECORDLOCKED) and "
       "kw_filelocks (the statements, GETLOCKS() and the local control) are defined and CALLED, W_FLK and W_FUL encode the two requests, the refusal matrix KM has `recordlocked` AGAIN (S.72b: a read-mode "
       "handle stops RECORDLOCKED() with 11501 and sends nothing - the matrix holds that its packet log has nothing but the requests of KALLOWED, which does not hold 34 - beside filelock and fileunlock) "
       "and KW_STILL_REFUSED does not hold filelock, fileunlock or recordlocked (a WRITE-mode handle serves them), and the GETLOCKS row expects the program to SURVIVE",
       all(("def %s(" % f) in suite for f in ("class_filelocks", "hw_filelocks", "kw_filelocks", "W_FLK", "W_FUL"))
       and re.search(r"^[ \t]+class_filelocks\(A, alice\)[ \t]*$", suite, re.M) is not None and re.search(r"^[ \t]+hw_filelocks\(A\)[ \t]*$", suite, re.M) is not None
       and re.search(r"^[ \t]+kw_filelocks\(A\)[ \t]*$", suite, re.M) is not None
       and 'km("recordlocked"' in suite and 'km("filelock"' in suite and 'km("fileunlock"' in suite and 'KALLOWED = {47, 48, 3, 4, 5, 6, 1}' in suite
       and kws is not None and not ({"filelock", "fileunlock", "recordlocked"} & set(still))
       and "KR kj SURVIVED fields=1 values=3" in suite and "getlocks(f, '')" in suite, repr((still, 'km("recordlocked"' in suite)))

    # ---- S73i. the suite carries the D1 rows
    ck("S73i THE SUITE sandbox-netfile.py carries the S.73 item 3 D1 rows (21 Oct 26): kw_index (the six statements on a read-mode and a write-mode pointer against the local statements' answers, the wire, "
       "the query processor with and without an index) and hw_index (the handler's operation 24 by number, a read-mode handle, a lost connection) are defined and CALLED; the helpers W_IDX1, W_IDX2, W_SELV, "
       "W_SELK, W_SETIDX, W_SCAN and W_RLIST encode the requests (READLIST carries no list number on the wire: the class sends none); NF_INDEXQ is 24; the refusal matrix KM no longer has the six index statements "
       "and KW_STILL_REFUSED is fiexcl, fistaton and fistatoff; the requests the query processor makes of every file (35 and 36) are in KQALLOWED; the index the fake is given describes a SINGLE-valued "
       "left-justified D index (the query processor takes a multivalued one for another field and uses none)",
       all(("def %s(" % f) in suite for f in ("kw_index", "hw_index", "ni_fresh", "k_idx", "W_IDX1", "W_IDX2", "W_SELV", "W_SELK", "W_SETIDX", "W_SCAN", "W_RLIST"))
       and re.search(r"^[ \t]+kw_index\(A\)[ \t]*$", suite, re.M) is not None and re.search(r"^[ \t]+hw_index\(A\)[ \t]*$", suite, re.M) is not None
       and re.search(r"^NF_INDEXQ = 24$", suite, re.M) is not None and re.search(r"def W_RLIST\(lst=10\):.*?return \(14, b\"\"\)", suite, re.S) is not None
       and not any(('km("%s"' % t) in suite for t in ("selectindex", "selectindexv", "selectright", "selectleft", "setleft", "setright"))
       and still == ["fiexcl", "fistaton", "fistatoff"] and "KQALLOWED = KALLOWED | {11, 14, 35, 36}" in suite
       and re.search(r'NI_INFO = "D\\xfd\\xfd\\xfd1\\xfd0\\xfdL\\xfd\\xfe1\\xfe\\xfeName\\xfeL\\xfeS"', suite) is not None, repr(still))

    ck("S73j apisrvr's two scans (S.73 item 3 D1): vb.selectleft and vb.selectright read the file, then the list number, then ask check.list (and stop on its error) BEFORE the statement - a list number outside "
       "0 to 10 was a runtime error whose reply named a line of the program; vb.selectright ends with a RETURN on the line of its statement (it ran on into vb.mark.mapping, which switched mark mapping on, and "
       "left STATUS() 0 past the last key)",
       re.search(r"vb\.selectleft:\s*\n\s*fno = oconv\(cmnd\[1,2\], 'ISL'\)\s*\n\s*gosub check\.file\s*\n\s*if err then return\s*\n\s*listno = oconv\(cmnd\[3,2\], 'ISL'\)\s*\n\s*gosub check\.list[^\n]*\n"
                 r"\s*if err then return\s*\n\s*selectleft cmnd\[5,999\] from files\(fno\) setting response to listno\s*\n\s*return", ap) is not None
       and re.search(r"vb\.selectright:\s*\n\s*fno = oconv\(cmnd\[1,2\], 'ISL'\)\s*\n\s*gosub check\.file\s*\n\s*if err then return\s*\n\s*listno = oconv\(cmnd\[3,2\], 'ISL'\)\s*\n\s*gosub check\.list[^\n]*\n"
                   r"\s*if err then return\s*\n\s*selectright cmnd\[5,999\] from files\(fno\) setting response to listno\s*;\s*return", ap) is not None, "")

    # ---- S72r. S.72b: act.recordlocked refuses a handle that is not write-mode (the same act.refuse as act.fileunlock)
    ck("S72r act.recordlocked (NF$RECORDLOCKED), S.72b, in this ORDER as act.fileunlock is: the handle of this account (a lost one will do: no gate and no connection yet); its name is 'recordlocked' - set BEFORE the "
       "refusal, so that message 11501 names it; a handle whose mode is not write is REFUSED (act.refuse: 11501, nothing sent) BEFORE the gate and the connection are asked, so the kernel's refusal of a read-mode "
       "handle and this one say the same thing; then the handle again with the gate and the connection, the id, the request with the no-reply mark, a lost reply, a server error, `out = lk` and rc<8> last.  It "
       "does NOT read the definition again (no mode.now: a handle that was write when it was opened is asked, and the server's wall - request 34 in the change set - answers for the group), is NOT refused in a "
       "transaction (RECORDLOCKED() changes nothing: the recorded choice - no SYS$TRANS_LEVEL, no 11510), is not audited and is not a change",
       arl != "" and ordered(arl, "need.gate = @false ; need.conn = @false ; any.acct = @false ; allow.lost = @true", "gosub get.handle", "if failed then return", "opname = 'recordlocked'",
                             "if nf.h.mode(hx) # 'write' then", "gosub act.refuse", "return",
                             "need.gate = @true ; need.conn = @true ; any.acct = @false ; allow.lost = @false", "gosub get.handle", "if failed then return", "gosub check.id", "if failed then return",
                             "obj = nf.s.obj(slot)", "obj->error = ''", "obj->ServerStatus = NF$NOREPLY", "obj->recordlocked(nf.h.fno(hx), id)", "gosub after.rq", "nf.requests += 1",
                             "if rq.lost then", "gosub lost.fail", "return", "if rq.err then", "gosub server.fail", "return", "out = lk", "rc<8> = rq.st", "return")
       and re.search(r"if nf\.h\.mode\(hx\) # 'write' then\s*\n\s*gosub act\.refuse\s*\n\s*return\s*\n\s*end", arl) is not None
       and arl.count("opname = 'recordlocked'") == 1 and arl.count("gosub act.refuse") == 1 and arl.count("get.handle") == 2 and arl.count("obj->recordlocked(") == 1
       and not re.search(r"mode\.now|mode\.ok|K\$AUDIT|audit\.once|\bchanging\b|SYS\$TRANS_LEVEL|11510|rc\.locked|NF\$LE\.LOCKED", arl), repr(arl[:120]))

    # ---- S72s. S.72b: net_gate's NETG_PEEK arm
    ng = fn("netfiles.c", "net_gate")
    ck("S72s net_gate's NETG_PEEK arm (S.72b), in this ORDER: the first test of net_gate - a read-mode file variable, `!fvar->access.net.write || (fvar->flags & FV_RDONLY)`, 11501 and -ER_NETWORK - is the same for every kind, "
       "NETG_PEEK included and with no `kind` in it; the PEEK arm is the SECOND test: `if (kind == NETG_PEEK) { process.op_flags = entry; return 0; }` - it gives process.op_flags back and answers 0, nothing else - "
       "and it stands BEFORE the transaction test (11510) and the edit gate (11404 + kind), so a PEEK is never refused for any of them (RECORDLOCKED() changes nothing; "
       "inside BEGIN TRANSACTION it is served; the CREATING.SEQKEY test that stood between them went with S.73 item 3); NETG_PEEK is named ONCE in net_gate, not in the transaction or edit-gate tests",
       ng != "" and re.search(r"if \(!fvar->access\.net\.write \|\| \(fvar->flags & FV_RDONLY\)\) \{\s*st = net_refuse_with\(fvar, what, MSG_READ_ONLY, -ER_NETWORK\);", ng) is not None
       and re.search(r"if \(kind == NETG_PEEK\) \{\s*process\.op_flags = entry;\s*return 0;\s*\}", ng) is not None and ng.count("NETG_PEEK") == 1
       and ordered(ng, "MSG_READ_ONLY, -ER_NETWORK", "if (kind == NETG_PEEK) {", "process.txn_id != 0", "(kind == NETG_WRITE) || (kind == NETG_DELETE) || (kind == NETG_CLEAR) || (kind == NETG_ADMIN)")
       and ng.find("kind == NETG_PEEK") < ng.find("process.txn_id") and ng.find("kind == NETG_PEEK") < ng.find("edit_permitted"), repr(ng[:160]))

    # ---- S72t. S.72b: NETG_PEEK has one user
    peek_files = sorted(n for n, t in c.items() if (n.endswith((".c", ".h")) or n.startswith("c:")) and "NETG_PEEK" in t)
    peek_funcs = sorted((n, name) for n, t in c.items() if (n.endswith(".c") or n.startswith("c:")) for name, b in c_functions(t).items() if "NETG_PEEK" in b)
    ck("S72t NETG_PEEK has ONE user among the statements that change a file or take a lock (S.72b): every kernel source is searched and the word stands in sd.h (the define) and netfiles.c only, and in netfiles.c in "
       "net_gate (the arm), net_recordlocked (the call) and - since S.73 item 3, for the two QUESTIONS of the administration statements - net_admin (ANALYSE.FILE) and net_fcontrol (FC$VALID.ID); "
       "no write path (WRITE, DELETE, CLEARFILE, a record lock, MUSTLOCK) is given the read-mode-only test, and no other statement asks the gate for a PEEK",
       peek_files == ["netfiles.c", "sd.h"]
       and peek_funcs == [("netfiles.c", "net_admin"), ("netfiles.c", "net_fcontrol"), ("netfiles.c", "net_gate"), ("netfiles.c", "net_recordlocked")], repr((peek_files, peek_funcs)))

    # ---- S72u. S.72b: MUSTLOCK is not gated
    npc, ow_, od_ = fn("op_dio3.c", "net_pre_change_lock"), fn("op_dio3.c", "op_write"), fn("op_dio3.c", "op_delete")
    chk_callers = sorted((n, name) for n, t in c.items() if (n.endswith(".c") or n.startswith("c:")) for name, b in c_functions(t).items() if "net_check_lock(" in b and name != "net_check_lock")
    ck("S72u MUSTLOCK is NOT gated (S.72b): net_check_lock, net_lock_code (which it shares with net_recordlocked) and net_pre_change_lock mention no gate - no net_gate, refuse_net_file, net_refuse or NETG_ kind - because "
       "the check is reached only from a write path AFTER the gate has passed: net_check_lock has ONE caller, net_pre_change_lock, and op_write and op_delete call refuse_net_file(... NETG_WRITE / NETG_DELETE) BEFORE "
       "net_pre_change_lock, i.e. only with a WRITE-mode handle.  So MUSTLOCK with the write group is unchanged (3023 when the record is not locked, the write goes on when it is), and a login WITHOUT the group "
       "gets the server's refusal of request 34 (11521, shown by the program as 11500 with the request number) instead of `not locked` - the wall is the server's",
       all(b != "" and not re.search(r"net_gate\(|refuse_net_file\(|net_refuse\(|NETG_", b) for b in (ncl, lc, npc)) and chk_callers == [("op_dio3.c", "net_pre_change_lock")]
       and ordered(ow_, "refuse_net_file(fvar, op_flags, keep_lock ? \"WRITEU\" : \"WRITE\", NETG_WRITE)", "net_pre_change_lock(")
       and ordered(od_, "refuse_net_file(fvar, op_flags, \"DELETE\", NETG_DELETE)", "net_pre_change_lock("), repr((chk_callers, npc[:60])))

    # ---- S72w. S.72b: the class's recordlocked() honours quiet
    rkc = re.search(r"public function recordlocked\(fno, id\)\s*\n(.*?)\nend\s*\n", sc, re.S)
    rkc = rkc.group(1) if rkc else ""
    ck("S72w THE CLASS recordlocked(fno, id) (gpl.bp/sdclient), S.72b: it honours quiet as filelock(), fileunlock() and clearfile() do - request 34 (SrvrRecordlocked) with the file number as a 16 bit number and then the "
       "id, sent through message.pair (which empties LastError and LastText before it writes and sets them from the reply) and NOT through text.request, which aborts on an ON ERROR reply whatever quiet says and would "
       "stop the $netfile handler's own program with 'RECORDLOCKED generated an abort event' instead of giving the person message 11500 and the server's text; the answer of an OK reply is its four bytes made signed; "
       "the abort is taken on an ON ERROR reply ONLY when not(quiet); a quiet object returns 0 and LastError / LastText say what the reply was; an unconnected object and a short reply are 0",
       rkc != "" and ordered(rkc, "reply = ''", "if not(context.error(CX.CONNECTED)) then", "if message.pair(SrvrRecordlocked, iconv(fno, 'ISL') : id) then", "begin case", "case server.error = SV$OK",
                             "reply = in.pkt", "case server.error = SV$ON.ERROR", "if not(quiet) then abort 'RECORDLOCKED generated an abort event'", "end case", "if len(reply) < 4 then return 0",
                             "n = oconv(reply[1,4], 'ILL')", "if n > 2147483647 then n -= 4294967296", "return n")
       and "text.request" not in rkc and rkc.count("message.pair(") == 1 and rkc.count("abort '") == 1 and sc.count("SrvrRecordlocked") == 2 and "text.request(SrvrRecordlocked" not in sc
       and re.search(r"case server\.error = SV\$OK\s*\n\s*reply = in\.pkt\s*\n\s*case server\.error = SV\$ON\.ERROR\s*\n\s*if not\(quiet\) then abort 'RECORDLOCKED generated an abort event'\s*\n\s*end case", rkc) is not None,
       repr(rkc[:140]))

    # ---- S72x. S.72b: act.recordlocked reads the reply
    arc = rb("act.recordlocked")
    arc_seg, afu_seg = seg(arc, "if lerr = -1 then rq.lost = @true", "gosub fail"), seg(afu, "if lerr = -1 then rq.lost = @true", "gosub fail")
    ck("S72x act.recordlocked reads the REPLY (S.72b: a login without sdfileswrite is refused request 34 with an ON ERROR reply, message 11521, and the class - quiet - returns 0 and says so in LastError): "
       "`lerr = obj->LastError` straight after the request and BEFORE after.rq; a missing reply (lerr = -1) is LOST (rq.lost: 11497 through lost.fail - not 11509, a lock test changes no data), a server "
       "error (rq.err) is server.fail, an ON ERROR reply is shown through on.error.text and then server.fail - so the program stops with message 11500 naming the server, `recordlocked` and the server's own text "
       "with `(request 34)` - and any other kind but OK is 11504; only on success are `out = lk` and rc<8> = rq.st set (a refused request gives no code and no owner number); these branches are the very ones "
       "of act.fileunlock, the same words in the same order (S72k)",
       arc != "" and arc_seg != "" and nospace(arc_seg) == nospace(afu_seg)
       and ordered(arc, "lk = obj->recordlocked(nf.h.fno(hx), id)", "lerr = obj->LastError", "gosub after.rq", "nf.requests += 1", "if lerr = -1 then rq.lost = @true", "if rq.lost then", "gosub lost.fail", "return",
                   "if rq.err then", "gosub server.fail", "return", "if lerr = NF$LE.ERROR then", "gosub on.error.text", "gosub server.fail", "return", "if lerr # NF$LE.OK then", "fail.num = 11504", "gosub fail",
                   "return", "out = lk", "rc<8> = rq.st", "return")
       and arc.count("lerr = obj->LastError") == 1 and arc.count("gosub on.error.text") == 1 and arc.count("fail.num = 11504") == 1 and arc.count("out = lk") == 1 and arc.count("rc<8>") == 1, repr((arc_seg[:60], afu_seg[:60])))

    # ---- S72v. S.72b: the history lines
    lack = [n for n in ("netfiles.c", "op_lock.c", "sd.h", "bp:netfile", "bp:sdclient", "apifilesok") if not re.search(r"20 Oct 26 dm\s+S\.72b", srcs[n])]
    ck("S72v the dated history lines of S.72b are there: every production file it changed (netfiles.c, op_lock.c, sd.h, gpl.bp/netfile, gpl.bp/sdclient, gpl.bp/apifilesok) says `20 Oct 26 dm  S.72b`, and this check's own file says so",
       not lack and "20 Oct 26 dm  S.72b" in (__doc__ or ""), repr(lack))


def mutate(srcs, name, old, new=None):
    s = dict(srcs)
    if callable(old):                       # a mutant made by a function of the source text (raises KeyError when it does not apply)
        s[name] = old(s[name])
        return s
    if old not in s[name]:
        raise KeyError("mutant text not in %s: %r" % (name, old[:70]))
    s[name] = s[name].replace(old, new, 1)
    return s


def rx(pattern, repl, flags=0):
    def f(text):
        out, n = re.subn(pattern, repl, text, count=1, flags=flags)
        if n == 0:
            raise KeyError("pattern not in the source: %r" % pattern[:70])
        return out
    return f


def drop_line(pattern):
    """The first line that matches PATTERN is taken out."""
    return rx(r"^[^\n]*" + pattern + r"[^\n]*\n", "", re.M)


def every(old, new):
    """A mutant (a function of the source text) that changes EVERY place OLD stands to NEW (mutate() changes the first only); KeyError when OLD is not there."""
    def f(text):
        if old not in text:
            raise KeyError("text not in the source: %r" % old[:70])
        return text.replace(old, new)
    return f


M = []   # (label, source name, old text | function, new text | None)


def mut(label, name, old, new=None):
    M.append((label, name, old, new))


# ---- K
mut("K_NET is 128", "keys.h", rx(r"(#define\s+K_NET\s+)127", r"\g<1>128"))
mut("K_NET shares 126 with K_EDIT_OS_OK", "keys.h", rx(r"(#define\s+K_NET\s+)127", r"\g<1>126"))
mut("K$NET is 128 in int$keys.h", "int$keys.h", rx(r"(\$define\s+K\$NET\s+)127", r"\g<1>128"))
mut("ACC$NET is 14", "syscom/keys.h", rx(r"(\$define\s+ACC\$NET\s+)15", r"\g<1>14"))
mut("ACC$NET is 12 (the dict edit field)", "syscom/keys.h", rx(r"(\$define\s+ACC\$NET\s+)15", r"\g<1>12"))
mut("UG_NET is 0x0010 (a shared-gate bit)", "sysseg.h", rx(r"(#define\s+UG_NET\s+)0x0008", r"\g<1>0x0010"))
mut("UG_NET shares 0x0004 with the dict gate", "sysseg.h", rx(r"(#define\s+UG_NET\s+)0x0008", r"\g<1>0x0004"))
mut("CA$NET is 34", "createacc.h", rx(r"(\$define\s+CA\$NET\s+)35", r"\g<1>34"))
mut("CA$NET is 36", "createacc.h", rx(r"(\$define\s+CA\$NET\s+)35", r"\g<1>36"))
# ---- C
mut("K_NET can be set by a user program", "op_kernel.c", rx(r"if \(process\.program\.flags & HDR_INTERNAL\) \{(\s*)SET_MY_GATE\(UG_NET, n > 0\);", r"if (1) {\1SET_MY_GATE(UG_NET, n > 0);"))
mut("K_NET switches on the wrong bit", "op_kernel.c", "SET_MY_GATE(UG_NET, n > 0);", "SET_MY_GATE(UG_BP_EDIT, n > 0);")
mut("K_NET never switches the gate off", "op_kernel.c", "SET_MY_GATE(UG_NET, n > 0);", "SET_MY_GATE(UG_NET, 1);")
mut("K_NET always answers 1", "op_kernel.c", "      }\n      result.data.value = MY_GATE(UG_NET);", "      }\n      result.data.value = 1;")
mut("K_NET always answers 1 when it sets the gate", "op_kernel.c", "          result.data.value = MY_GATE(UG_NET);\n          n = process.status;", "          result.data.value = 1;\n          n = process.status;")
# ---- B
mut("LOGIN forgets the NET gate", "login", drop_line(r"void kernel\(K\$NET,"))
mut("LOGIN turns the gate on for a blank field", "login", "upcase(trim(acc.rec<ACC$NET>)) = 'YES')", "upcase(trim(acc.rec<ACC$NET>)) # 'NO')")
mut("LOGIN loads the gate from the wrong field", "login", "upcase(trim(acc.rec<ACC$NET>)) = 'YES')", "upcase(trim(acc.rec<ACC$SH>)) = 'YES')")
mut("CPROC's logto forgets the NET gate", "cproc", drop_line(r"void kernel\(K\$NET, upcase\(trim\(acc\.record"))
mut("CPROC's logto loads it from the old account's record", "cproc", "void kernel(K$NET, upcase(trim(acc.record<ACC$NET>)) = 'YES')", "void kernel(K$NET, upcase(trim(acc.rec<ACC$NET>)) = 'YES')")
mut("CPROC's logto loads the gate after the audit line", "cproc", rx(r"(   void kernel\(K\$NET, upcase\(trim\(acc\.record<ACC\$NET>\)\) = 'YES'\)\n(?:\*[^\n]*\n)*(?:   void kernel\(K\$SHARED\.[A-Z]+,[^\n]*\n)*)(\n   void kernel\(K\$AUDIT, 'logto account=' : new\.account\)[^\n]*\n)", r"\2\1"))
mut("CPROC never holds the gate", "cproc", drop_line(r"stk\.net = kernel"))
mut("CPROC does not give the gate back", "cproc", drop_line(r"void kernel\(K\$NET, stk\.net\)"))
mut("CPROC gives the gate back after the revert audit line", "cproc", rx(r"(   void kernel\(K\$NET, stk\.net\)[^\n]*\n)(   void kernel\(K\$AUDIT, 'logto revert account=' : who\)\n)", r"\2\1"))
mut("the API server forgets api.net.grant at every entry", "apisrvr", drop_line(r"^api\.net\.grant = @false"))
mut("the API server starts with the gate on", "apisrvr", rx(r"api\.net\.grant = @false", "api.net.grant = @true"))
mut("the API server does not read the register field", "apisrvr", drop_line(r"api\.net\.grant = \(upcase"))
mut("the API server does not load the gate", "apisrvr", drop_line(r"^void kernel\(K\$NET, api\.net\.grant\)"))
mut("the API server loads the gate only at the first entry", "apisrvr",
    rx(r"^void kernel\(K\$NET, api\.net\.grant\)[^\n]*\n", "", re.M))
mut("the API server loads the gate with the edit gates (first entry only)", "apisrvr",
    lambda t: rx(r"^void kernel\(K\$NET, api\.net\.grant\)[^\n]*\n", "", re.M)(t).replace("if not(master.login.done) then\n   void kernel(K$VOC.EDIT,", "if not(master.login.done) then\n   void kernel(K$NET, api.net.grant)\n   void kernel(K$VOC.EDIT,", 1))
mut("SDSYS over the API does not pass the NET gate", "apisrvr", drop_line(r"api\.net\.grant = @true"))
mut("a program sets K$NET to 1", "bp:basic",lambda t: t + "\n   void kernel(K$NET, 1)\n")
mut("a program turns the gate on with @true", "bp:catalog", lambda t: t + "\n   void kernel(K$NET, @true)\n")
mut("LOGIN loads the gate twice", "login", lambda t: t + "\n   void kernel(K$NET, 0)\n")
mut("an upgrade walk for the gate appears", "bp:upgrade_gates", lambda t: t + "\n   if trim(rec<ACC$NET>) = '' then rec<ACC$NET> = 'yes'\n")
mut("the installer runs an upgrade_net walk", "installsdcore.sh", lambda t: t + "\nsudo sd -internal RUN gpl.bp upgrade_net\n")
# ---- M
mut("MODIFY.ACCOUNT loses NET-OFF", "modifya", "case action = 'NET-OFF'", "case action = 'NET-OFFX'")
mut("MODIFY.ACCOUNT loses NET-ON", "modifya", "case action = 'NET-ON'", "case action = 'NET-ONX'")
mut("NET-ON switches off", "modifya", rx(r"(case action = 'NET-ON'\s*\n\s*os\.field = ACC\$NET ; os\.want = )@true", r"\1@false"))
mut("NET-ON works on the wrong field", "modifya", rx(r"(case action = 'NET-ON'\s*\n\s*os\.field = )ACC\$NET", r"\1ACC$SD.ACCOUNTS"))
mut("a group account is refused NET-ON", "modifya", " and os.field # ACC$NET and os.field # ACC$PINS then", " and os.field # ACC$PINS then")      # 24 Oct 26: ACC$PINS joined the list after NET (the home screen), so the text this mutant cut ended differently
mut("NET-ON prints the SH line", "modifya", "if os.field = ACC$NET then", "if os.field = ACC$SD.ACCOUNTS then")
mut("the NET line names the wrong state", "modifya", "if upcase(trim(acc.new<ACC$NET>)) = 'YES' then 'yes' else 'no')   ;* Account %1 has NET %2", "if upcase(trim(acc.rec<ACC$NET>)) = 'YES' then 'yes' else 'no')   ;* Account %1 has NET %2")
mut("MODIFY.ACCOUNT's syntax lines forget the words", "modifya", "modify.account <account> net-on | net-off", "modify.account <account> net")
mut("MODIFY.ACCOUNT's word list forgets them", "modifya", "dict-on, dict-off, net-on, net-off,", "dict-on, dict-off,")
mut("CREATE.ACCOUNT loses NET-ON", "createa", "case upcase(token) = 'NET-ON'", "case upcase(token) = 'NET-ONX'")
mut("NET-ON asks for CA$NET = 0", "createa", rx(r"(case upcase\(token\) = 'NET-ON'\s*\n\s*settings<CA\$NET> = )1", r"\g<1>0"))
mut("CREATE.ACCOUNT's syntax line forgets {net-on}", "createa", lambda t: t.replace("{net-on}", "", 1))
mut("a request for the gate is any non-zero", "create_account", "net.want = (settings<CA$NET> = 1)", "net.want = (settings<CA$NET> # 0)")
mut("a new user account is written with the NET field blank", "create_account", drop_line(r"acc\.rec<ACC\$NET> = if net\.want then 'yes' else 'no'"))
mut("a new user account is written 'yes'", "create_account", "acc.rec<ACC$NET> = if net.want then 'yes' else 'no'", "acc.rec<ACC$NET> = 'yes'")
mut("a group account loses the requested gate", "create_account", drop_line(r"if net\.want then acc\.rec<ACC\$NET> = 'yes'"))
mut("CREATE.ACCOUNT does not report the state", "create_account", drop_line(r"crt sysmsg\(11411,"))
mut("the manifest drops net", "acc_os_info", drop_line(r"'net: '"))
mut("the manifest says net for the group account branch only", "acc_os_info", lambda t: t.replace("         info<-1> = 'net: ':(if upcase(trim(acc.rec<ACC$NET>)) = 'YES' then 1 else 0)", "", 1).replace("      case grp[1,4] = 'sdg_'\n", "      case grp[1,4] = 'sdg_'\n         info<-1> = 'net: ':(if upcase(trim(acc.rec<ACC$NET>)) = 'YES' then 1 else 0)\n", 1))
mut("RESTORE.ACCOUNT does not read net", "restorea", drop_line(r"= 'net'\s*; m\.net = kv"))
mut("RESTORE.ACCOUNT does not hand net on", "restorea", drop_line(r"settings<CA\$NET> = m\.net"))
mut("RESTORE.ACCOUNT keeps net from the section before", "restorea", " ; m.net = ''", "")
# ---- D / S / X / L / N / P
mut("a verb's VOC entry is missing", "voc:set.server", "$setserver", "$setserve")
mut("a verb is in newvoc, for every account", "newvoc.list", lambda t: t + "\nlist.servers")
mut("delete.server points at the wrong program", "voc:delete.server", "$deleteserver", "$setserver")
mut("a second program takes the name $setserver", "bp:cd", lambda t: t + "\n$catalog $setserver\n")
mut("set.server is not internal", "setserver", "$internal\nprogram set.server", "program set.server")
mut("set.server forgets the administrator test", "setserver", rx(r"   if not\(kernel\(K\$ADMINISTRATOR, -1\)\) then\n      stop sysmsg\(2001\)[^\n]*\n   end\n", ""))
mut("set.server tests the administrator after reading the sentence", "setserver", rx(r"(   if not\(kernel\(K\$ADMINISTRATOR, -1\)\) then\n      stop sysmsg\(2001\)[^\n]*\n   end\n)(.*)(   words = trim\(@sentence\)\n)", r"\2\3\1", re.S))
mut("delete.server forgets the administrator test", "deleteserver", rx(r"   if not\(kernel\(K\$ADMINISTRATOR, -1\)\) then\n      stop sysmsg\(2001\)[^\n]*\n   end\n", ""))
mut("list.servers forgets the administrator test", "listservers", rx(r"   if not\(kernel\(K\$ADMINISTRATOR, -1\)\) then\n      stop sysmsg\(2001\)[^\n]*\n   end\n", ""))
mut("!netdefs WRITE forgets the administrator test", "netdefs", rx(r"         if not\(kernel\(K\$ADMINISTRATOR, -1\)\) then\n            err = 2001[^\n]*\n            return\n         end\n", ""))
mut("set.server does not stop on a bad field", "setserver", "if bad # 0 then stop", "if bad > 99 then stop")
mut("set.server stops on bad before the accounts are checked", "setserver",
    lambda t: rx(r"^   if bad # 0 then stop[^\n]*\n", "", re.M)(t).replace("   acc.clean = ''\n", "   if bad # 0 then stop\n   acc.clean = ''\n", 1))
mut("set.server forgets the port message", "setserver", drop_line(r"display sysmsg\(11416"))
mut("set.server forgets the pin message", "setserver", drop_line(r"display sysmsg\(11418"))
mut("set.server does not check the register for an account", "setserver", drop_line(r"display sysmsg\(11421"))
mut("set.server takes the lock before it has opened the directory", "setserver",
    rx(r"(   openpath @sdsys to sys\.f else.*?\n   end\n)(\n   readu lock\.rec.*?\n   end else\n      null\n   end\n)", r"\2\1", re.S))
mut("set.server takes the lock only after the read", "setserver",
    lambda t: t.replace("   readu lock.rec", "   null ; zz.lock.rec", 1).replace("   d = date()\n", "   readu lock.rec from sys.f, NET.LOCK.ID locked\n   end then null\n   end else null\n   d = date()\n", 1))
mut("set.server allows an 11th server", "setserver", "n.defs >= NET.MAX.SERVERS", "n.defs >= 99")
mut("the limit is 11", "setserver", "$define NET.MAX.SERVERS 10", "$define NET.MAX.SERVERS 11")
mut("set.server replaces without asking", "setserver", "if found # 0 and not(no.query) then", "if found # 0 and no.query then")
mut("a 'no' to the question goes on to write", "setserver", rx(r"(      if yn = 'N' then\n)(         gosub release\.lock\n)", r"\1         null\n"))
mut("input that ends is a yes", "setserver", "if yn = '' and status() = ER$EOF then yn = 'N'", "if yn = '' and status() = ER$EOF then yn = 'Y'")
mut("the lock is not released after the write", "setserver", rx(r"(call !netdefs\('WRITE', defs, err\)\n)   gosub release\.lock\n", r"\1"))
mut("set.server accepts a name of 17", "setserver", "len(name) > 16", "len(name) > 17")
mut("set.server accepts a name starting with a digit", "setserver", " or index(lc.set, name[1, 1], 1) = 0", "")
mut("set.server accepts a host of 254", "setserver", "len(host) > 253", "len(host) > 254")
mut("set.server accepts a host starting with a hyphen", "setserver", " or host[1, 1] = '-' or host[1, 1] = '.'", "")
mut("set.server allows a bar in a host", "setserver", "chk.set = lc.set:digits:'.-:'", "chk.set = lc.set:digits:'.-:|'")
mut("set.server accepts port 0", "setserver", "port + 0 >= 1 and", "port + 0 >= 0 and")
mut("set.server accepts port 65536", "setserver", "port + 0 <= 65535", "port + 0 <= 65536")
mut("set.server accepts a non-numeric port", "setserver", "port matches '1N0N'", "port matches '0X'")
mut("set.server accepts an account of 33", "setserver", "len(account) > 32", "len(account) > 33")
mut("set.server accepts a pin of 63", "setserver", "len(pin) # 64", "len(pin) < 63")
mut("set.server accepts a non-hex pin", "setserver", "chk.set = digits:'abcdef'", "chk.set = digits:'abcdefg'")
mut("the accounts list may be long", "setserver", "$define NET.MAX.ACCLIST 2000", "$define NET.MAX.ACCLIST 20000")
mut("an empty account name is allowed", "setserver", "if a = '' or len(a) > 32 or not(chk.ok) then list.ok = @false", "if len(a) > 32 or not(chk.ok) then list.ok = @false")
mut("mode may be anything", "setserver", "(lw = 'read' or lw = 'write') and not(mode.given)", "not(mode.given)")
mut("the default mode is write", "setserver", "   mode = 'read'\n", "   mode = 'write'\n")
mut("set.server prints the pin", "setserver", lambda t: t.replace("display sysmsg(11424, name, host, port)", "display sysmsg(11424, name, host, port) : pin", 1))
mut("set.server puts the pin on the audit trail", "setserver", "' pin=' : pin.how)", "' pin=' : pin.how : ' hash=' : pin)")
mut("set.server writes a file itself", "setserver", lambda t: t.replace("   @system.return.code = 0\n   if replaced then", "   openseq 'netpin' to pf then null\n   writeseq pin to pf else null\n   @system.return.code = 0\n   if replaced then", 1))
mut("set.server stores the pin twice", "setserver", "pin:@vm:mode", "pin:@vm:pin:@vm:mode")
mut("delete.server writes before it looks for the name", "deleteserver", rx(r"(   if found = 0 then\n.*?\n   end\n)(\n   host = defs<found,2>.*?   del defs<found>\n)", r"\2\1", re.S))
mut("delete.server does not stop on an unknown name", "deleteserver", rx(r"(   if found = 0 then\n      gosub release\.lock\n      @system\.return\.code = -ER\$FNF\n)      stop sysmsg\(11430, name\)", r"\1      null"))
mut("delete.server lets two words through", "deleteserver", "if dcount(words, ' ') # 2 then", "if dcount(words, ' ') < 2 then")
mut("delete.server keeps the name's case", "deleteserver", "name = downcase(field(words, ' ', 2))", "name = field(words, ' ', 2)")
mut("delete.server leaves the lock held", "deleteserver", rx(r"(call !netdefs\('WRITE', defs, err\)\n)   gosub release\.lock\n", r"\1"))
mut("delete.server deletes without cutting the line", "deleteserver", "   del defs<found>\n", "   null\n")
mut("list.servers takes a lock", "listservers", lambda t: t.replace("   call !netdefs('READ', defs, err)", "   readu lk from sys.f, 'netservers.lock' else null\n   call !netdefs('READ', defs, err)", 1))
mut("list.servers writes", "listservers", lambda t: t.replace("   call !netdefs('READ', defs, err)", "   call !netdefs('WRITE', defs, err)\n   call !netdefs('READ', defs, err)", 1))
mut("list.servers shows the full pin in the list", "listservers", "pin.text = defs<i,5>[1, 16] : '...'", "pin.text = defs<i,5>")
mut("list.servers shows the short pin for a named server", "listservers", "   end else\n            pin.text = defs<i,5>\n", "   end else\n            pin.text = defs<i,5>[1, 16] : '...'\n")
mut("list.servers forgets the date", "listservers", "if name # '' then crt sysmsg(11435, defs<i,8>)", "if name # '' then null")
mut("list.servers has no empty message", "listservers", "sysmsg(11433)", "sysmsg(11438)")
mut("list.servers forgets 'none'", "listservers", "sysmsg(11438)   ;* none", "''")
mut("!netdefs writes lines before checking them", "netdefs", rx(r"(         tmp = path : '\.new'\n)", r"         openseq tmp to tmp.f then null else null\n\1"))
mut("!netdefs accepts a bar inside a field", "netdefs", " or c = 124)", ")")
mut("!netdefs accepts a control character", "netdefs", "c < 32 or c > 126", "c > 126")
mut("!netdefs accepts a definition of 7 fields", "netdefs", "ok = (dcount(one, @vm) = NETDEFS.FIELDS)", "ok = (dcount(one, @vm) >= 7)")
mut("!netdefs writes the file in place", "netdefs", "tmp = path : '.new'", "tmp = path")
mut("!netdefs renames before it has written", "netdefs", rx(r"(         if not\(osrename\(tmp, path\)\) then)", r"         void osrename(tmp, path)\n\1"))
mut("!netdefs writes two ways", "netdefs", lambda t: t.replace("         closeseq tmp.f\n", "         writeseq 'x' to tmp.f else null\n         closeseq tmp.f\n", 1))
mut("!netdefs leaves the copy after a failed write", "netdefs", rx(r"if err # '' then\n\s*void ospath\(tmp, OS\$DELETE\)\n", "if err # '' then\n"))
mut("!netdefs never sets the umask", "netdefs", "         void umask(18)\n", "")
mut("!netdefs sets the umask after the copy is made", "netdefs", rx(r"(         void umask\(18\)\n)(         openseq tmp to tmp\.f then\n.*?\n         end\n)", r"\2\1", re.S))
mut("!netdefs does not put the umask back", "netdefs", "         void umask(old.umask)\n", "")
mut("!netdefs writes with umask 0", "netdefs", "void umask(18)", "void umask(0)")
mut("!netdefs READ asks for the administrator", "netdefs", lambda t: t.replace("      case mode = 'READ'\n", "      case mode = 'READ'\n         if not(kernel(K$ADMINISTRATOR, -1)) then err = 2001 ; return\n", 1))
mut("!netdefs READ keeps a mark byte", "netdefs", drop_line(r"convert char\(251\)"))
mut("!netdefs READ keeps the bar", "netdefs", drop_line(r"convert '\|' to @vm in line"))
mut("the definitions file is somewhere else", "netdefs", "$define NETDEFS.FILE   'netservers'", "$define NETDEFS.FILE   'netserver'")
mut("another program names the definitions file", "bp:cd", lambda t: t + "\n   openseq '/usr/local/sdsys/netservers' to nf else null\n")
mut("the warning about secrets is gone", "netdefs", "MUST NEVER HOLD A SECRET", "may hold what it likes")
# ---- G
mut("message 11411 is missing", "msg:11411", lambda t: None)
mut("message 11430 is empty", "msg:11430", lambda t: "")
mut("message 11425 takes two lines", "msg:11425", lambda t: t.rstrip("\n") + "\nsecond line\n")
mut("11420 is never used", "setserver", drop_line(r"display sysmsg\(11420"))
mut("11436 is never used", "netdefs", "err = 11436:@vm:i", "err = 11428:@vm:i")
mut("11411 is never printed by CREATE.ACCOUNT", "create_account", "crt sysmsg(11411,", "crt sysmsg(11409,")
mut("a verb prints a number that has no file", "listservers", "sysmsg(11433)", "sysmsg(11449)")
mut("message 11424 has a place the call does not fill", "msg:11424", lambda t: t.rstrip("\n") + " %4\n")
mut("11434 is called with three arguments", "listservers", "defs<i,4>:'/':defs<i,6>, pin.text:'  ':allowed)", "defs<i,4>:'/':defs<i,6>)")
mut("11411 loses its words", "msg:11411", lambda t: "Account %1 has gate %2\n")
mut("11423 stops asking", "msg:11423", lambda t: "Server %1 is already defined (%2)\n")
mut("11413 says no.query skips the key question", "msg:11413", lambda t: t.replace("no.query never skips that question", "no.query skips that question", 1))
mut("11439 stops naming the word", "msg:11439", lambda t: t.replace("net-on", "net-add"))
mut("11412 stops being the usage line", "msg:11412", lambda t: "Use the server verb\n")


# ---- slice 2a: CONNECT
def after(marker, old, new):
    """OLD replaced by NEW at its first place AFTER MARKER (the same text earlier in the file is not touched)."""
    def f(text):
        i = text.find(marker)
        j = text.find(old, i) if i >= 0 else -1
        if j < 0:
            raise KeyError("text not after the marker: %r / %r" % (marker[:40], old[:40]))
        return text[:j] + new + text[j + len(old):]
    return f


def last(old, new):
    """The LAST place OLD stands in the text is replaced."""
    def f(text):
        j = text.rfind(old)
        if j < 0:
            raise KeyError("text not in the source: %r" % old[:60])
        return text[:j] + new + text[j + len(old):]
    return f


CONN_BLOCK = r"   if connect\.mode then\n      gosub connect\.pin[^\n]*\n      pin\.how = 'confirmed'\n   end\n"
SPKI_FN = "int sd_tls_client_peer_spki_sha256("
# T1-T2: the order of the flow
mut("CONNECT is case sensitive", "setserver", "pin = downcase(field(words, ' ', 6))", "pin = field(words, ' ', 6)")
mut("CONNECT does not set connect mode", "setserver", "      connect.mode = @true", "      connect.mode = @false")
mut("a typed-pin check still runs for CONNECT", "setserver", "if not(connect.mode) then", "if @true then")
mut("set.server dials before the fields are checked", "setserver", "   if bad # 0 then stop", "   if connect.mode then gosub connect.pin\n   if bad # 0 then stop")
mut("set.server dials before the replace question", "setserver",
    lambda t: re.sub(r"(   if found # 0 and not\(no\.query\) then\n)", lambda m: "   if connect.mode then\n      gosub connect.pin\n      pin.how = 'confirmed'\n   end\n" + m.group(1),
                     rx(CONN_BLOCK, "", re.M)(t), count=1))
mut("the dial is not guarded by connect mode", "setserver", "   if connect.mode then\n      gosub connect.pin", "   if @true then\n      gosub connect.pin")
mut("confirmed is set before the dial", "setserver",
    lambda t: t.replace("      pin.how = 'confirmed'\n", "", 1).replace("      gosub connect.pin", "      pin.how = 'confirmed'\n      gosub connect.pin", 1))
mut("a typed pin opens a socket too", "setserver", lambda t: t.replace("   d = date()\n", "   skt = open.socket(host, port, SKT$BLOCKING + SKT$TLS, NET.CONNECT.SECS)\n   d = date()\n", 1))
mut("the sockets keys are not included", "setserver", rx(r"^\$include keys\.h\n", "", re.M))
# T3-T4: the socket
mut("the socket is opened without TLS", "setserver", "SKT$BLOCKING + SKT$TLS", "SKT$BLOCKING")
mut("the socket is opened with no timeout", "setserver", ", config('NETWAIT'))", ")")
mut("the timeout is 50 seconds whatever NETWAIT says", "setserver", "SKT$BLOCKING + SKT$TLS, config('NETWAIT'))", "SKT$BLOCKING + SKT$TLS, 50)")
mut("the timeout is the constant it used to be", "setserver", "SKT$BLOCKING + SKT$TLS, config('NETWAIT'))", "SKT$BLOCKING + SKT$TLS, NET.CONNECT.SECS)")
mut("the socket is not closed", "setserver", drop_line(r"^   close\.socket skt"))
mut("the socket is closed after the question", "setserver",
    lambda t: t.replace("   close.socket skt\n", "", 1).replace("   pin = spki\n", "   close.socket skt\n   pin = spki\n", 1))
mut("something is sent over the connection", "setserver", "   spki = downcase(trim(", "   write.socket 'x' to skt else null\n   spki = downcase(trim(")
mut("the status is not read at once", "setserver", drop_line(r"^   oserr = os\.error\(\)"))
mut("the hash is not shown", "setserver", "   display spki\n", "   display ''\n")
# T5: the key question
mut("no.query skips the key question", "setserver", "   display sysmsg(11440, host, port)", "   if no.query then\n      pin = spki\n      return\n   end\n   display sysmsg(11440, host, port)")
mut("an empty answer to the key question is a yes", "setserver", last("if yn = '' then yn = 'N'", "if yn = '' then yn = 'Y'"))
mut("input that ends is a yes to the key question", "setserver", last("if yn = '' and status() = ER$EOF then yn = 'N'", "if yn = '' and status() = ER$EOF then yn = 'Y'"))
mut("the key question is asked once", "setserver", rx(r"(   loop\n      display sysmsg\(11442\) : [^\n]*\n.*?\n)   until yn = 'Y' or yn = 'N'\n   repeat\n", r"\1   until 1\n   repeat\n", re.S))
# T6: nothing is written
mut("an n to the key question goes on to write", "setserver", "stop sysmsg(11443, name)", "display sysmsg(11443, name)")
mut("a failed connection goes on to write", "setserver", "stop sysmsg(11444, host, port, st, oserr)", "display sysmsg(11444, host, port, st, oserr)")
mut("a failed handshake is not told from a failed connection", "setserver", drop_line(r"if st = ER\$CONNECT and oserr = 0 then stop sysmsg\(11445"))
mut("every ER$CONNECT is a handshake failure", "setserver", "if st = ER$CONNECT and oserr = 0 then stop sysmsg(11445", "if st = ER$CONNECT then stop sysmsg(11445")
mut("an empty hash is accepted", "setserver", "if len(spki) # 64 or not(chk.ok) then", "if len(spki) > 64 then")
mut("the hash is not checked for hexadecimal digits", "setserver", drop_line(r"^   chk\.text = spki ; chk\.set"))
mut("the hash is not lower cased", "setserver", "spki = downcase(trim(socket.info(skt, SKT$INFO.TLS.SPKI)))", "spki = trim(socket.info(skt, SKT$INFO.TLS.SPKI))")
mut("the lock is left held after a failed connection", "setserver", rx(r"      gosub release\.lock\n(      @system\.return\.code = -ER\$FAILED\n      if st = ER\$CONNECT)", r"\1"))
mut("the lock is left held after an empty hash", "setserver", rx(r"      gosub release\.lock\n(      @system\.return\.code = -ER\$FAILED\n      stop sysmsg\(11446)", r"\1"))
mut("the routine writes the definitions", "setserver", "   pin = spki\n   return", "   call !netdefs('WRITE', defs, err)\n   pin = spki\n   return")
# T8: the audit words
mut("the audit line loses how the pin was obtained", "setserver", "' replaced=' : rep.word : ' pin=' : pin.how)", "' replaced=' : rep.word)")
mut("a confirmed pin is audited as typed", "setserver", "pin.how = 'confirmed'", "pin.how = 'typed'")
mut("the audit word confirmed is upper case", "setserver", "pin.how = 'confirmed'", "pin.how = 'CONFIRMED'")
mut("a typed pin is audited as confirmed", "setserver", "pin.how = 'typed'", "pin.how = 'confirmed'")
# C: the hash is of the key
mut("the hash is of the certificate", "sd_tls.c", "der_len = i2d_X509_PUBKEY(X509_get_X509_PUBKEY(cert), &der);", "der_len = 1; X509_digest(cert, EVP_sha256(), out, &n);")
mut("the hash is SHA-1", "sd_tls.c", after(SPKI_FN, "EVP_sha256()", "EVP_sha1()"))
mut("the hash may be short", "sd_tls.c", after(SPKI_FN, "n == 32", "n == 20"))
mut("the certificate is not freed", "sd_tls.c", after(SPKI_FN, "  X509_free(cert);\n", ""))
mut("the DER bytes are not freed", "sd_tls.c", after(SPKI_FN, "  OPENSSL_free(der);\n", ""))
mut("no certificate is not answered false", "sd_tls.c", after(SPKI_FN, "if (cert == NULL)", "if (0)"))
mut("the hash function has another signature", "sd_tls.h", "int sd_tls_client_peer_spki_sha256(SD_TLS_CLIENT* c, unsigned char* out);", "int sd_tls_client_peer_spki_sha256(SD_TLS_CLIENT* c, unsigned char* out, int n);")
mut("sd_tls_client_end no longer blocks SIGPIPE for the close_notify", "sd_tls.c", after("void sd_tls_client_end(SD_TLS_CLIENT* c) {", "pthread_sigmask(SIG_BLOCK, &pipe_only, &old_mask);", ""))
mut("sd_tls_client_end shuts down before the signal is blocked", "sd_tls.c", after("void sd_tls_client_end(SD_TLS_CLIENT* c) {", "(void)SSL_shutdown(c->ssl);", "/* gone */"))
mut("the hash digits are upper case", "op_skt.c", after("case SKT_INFO_TLS_SPKI:", '"%02x"', '"%02X"'))
mut("the answer is not emptied first", "op_skt.c", after("case SKT_INFO_TLS_SPKI:", "hex[0] = '\\0';", ""))
mut("only half the hash is written", "op_skt.c", after("case SKT_INFO_TLS_SPKI:", "i < 32", "i < 16"))
mut("a socket without TLS is not tested", "op_skt.c", after("case SKT_INFO_TLS_SPKI:", "(sockvar->tls != NULL) && ", ""))
mut("the answer is not returned", "op_skt.c", after("case SKT_INFO_TLS_SPKI:", "k_put_c_string(hex, &result_descr)", "k_put_c_string(\"\", &result_descr)"))
mut("the SOCKET.INFO key is gone", "op_skt.c", "case SKT_INFO_TLS_SPKI:", "case SKT_INFO_TLS_SPKJ:")
mut("SKT_INFO_TLS_SPKI shares 10 with the trace key", "keys.h", rx(r"(#define\s+SKT_INFO_TLS_SPKI\s+)11", r"\g<1>10"))
mut("SKT_INFO_TLS_SPKI is 12", "keys.h", rx(r"(#define\s+SKT_INFO_TLS_SPKI\s+)11", r"\g<1>12"))
mut("SKT$INFO.TLS.SPKI is 9 in the BASIC header", "syscom/keys.h", rx(r"(\$define\s+SKT\$INFO\.TLS\.SPKI\s+)11", r"\g<1>9"))
# G: the new messages
mut("11442 stops asking", "msg:11442", lambda t: "Trusted\n")
mut("11440 says something was sent", "msg:11440", lambda t: t.replace("a TLS handshake only: nothing was sent", "a TLS session", 1))
mut("11444 loses its fourth place", "msg:11444", lambda t: t.replace("(status %3, os error %4)", "(status %3)", 1))
mut("message 11446 is missing", "msg:11446", lambda t: None)
mut("11443 stops saying nothing was written", "msg:11443", lambda t: t.replace("Nothing was written: ", "", 1))
mut("11412 loses the word connect", "msg:11412", lambda t: t.replace("{pin | connect}", "pin", 1))
mut("message 11446 takes two lines", "msg:11446", lambda t: t.rstrip("\n") + "\nsecond line\n")

# ---- slice 2b: the person's login ---------------------------------------------------------------------------------------------------
FP_FN = "Private int file_private_check(const char* path, int want_dir) {"
NCR = "bp:netcred"
SNL = "bp:setnetlogin"
DNL = "bp:deletenetlogin"
NC_TRUST_READ = "         if SDEXT(path : @FM : 'FILE', @TRUE, SD_FILE_PRIVATE) # '1' then\n            err = 11454:@vm:server:@vm:path\n            return\n         end\n"
# F: the number and the case
mut("SD_FILE_PRIVATE is 112 in keys.h", "keys.h", rx(r"(#define\s+SD_FILE_PRIVATE\s+)111", r"\g<1>112"))
mut("SD_FILE_PRIVATE is 112 in the BASIC header", "syscom/keys.h", rx(r"(\$define\s+SD_FILE_PRIVATE\s+)111", r"\g<1>112"))
mut("SD_FILE_PRIVATE shares 110 with SD_TLS_CBIND", "keys.h", rx(r"(#define\s+SD_FILE_PRIVATE\s+)111", r"\g<1>110"))
mut("the BASIC header gives the neighbour another number", "syscom/keys.h", rx(r"(\$define\s+SD_TLS_CBIND\s+)110", r"\g<1>109"))
mut("the answer starts as 1", "op_sdext.c", after("case SD_FILE_PRIVATE:", "answer[0] = '0';", "answer[0] = '1';"))
mut("a wrong argument count is not looked at", "op_sdext.c", after("case SD_FILE_PRIVATE:", "argCnt != 2", "argCnt != 3"))
mut("the word FILE asks for a directory", "op_sdext.c", after("case SD_FILE_PRIVATE:", "file_private_check(SDMEArgArray[0], 0)", "file_private_check(SDMEArgArray[0], 1)"))
mut("the word DIR asks for a file", "op_sdext.c", after("case SD_FILE_PRIVATE:", "file_private_check(SDMEArgArray[0], 1)", "file_private_check(SDMEArgArray[0], 0)"))
mut("any other word is a yes", "op_sdext.c", after("case SD_FILE_PRIVATE:", "      }\n      k_put_c_string(answer, e_stack);", "      } else {\n        answer[0] = '1';\n      }\n      k_put_c_string(answer, e_stack);"))
mut("the answer is not the computed one", "op_sdext.c", after("case SD_FILE_PRIVATE:", "k_put_c_string(answer, e_stack)", "k_put_c_string(\"1\", e_stack)"))
mut("lstat is stat (a link is followed)", "op_sdext.c", after(FP_FN, "lstat(path, &st)", "stat(path, &st)"))
mut("the owner is the real uid", "op_sdext.c", after(FP_FN, "geteuid()", "getuid()"))
mut("the owner is not tested", "op_sdext.c", after(FP_FN, "if (st.st_uid != geteuid())", "if (0)"))
mut("group bits are allowed", "op_sdext.c", after(FP_FN, "(st.st_mode & 077)", "(st.st_mode & 007)"))
mut("world bits are allowed", "op_sdext.c", after(FP_FN, "(st.st_mode & 077)", "(st.st_mode & 070)"))
mut("a relative path is allowed", "op_sdext.c", after(FP_FN, "path[0] != '/'", "path[0] != 'x'"))
mut("a long path is allowed", "op_sdext.c", after(FP_FN, "len >= sizeof(parent)", "0"))
mut("a failed lstat is allowed", "op_sdext.c", after(FP_FN, "lstat(path, &st) != 0", "lstat(path, &st) != 0 && 0"))
mut("any directory passes", "op_sdext.c", after(FP_FN, "return S_ISDIR(st.st_mode) ? 1 : 0;", "return 1;"))
mut("a link to a directory passes (not S_ISDIR)", "op_sdext.c", after(FP_FN, "S_ISDIR(st.st_mode)", "(st.st_mode & S_IFMT) != 0"))
mut("a file need not be a regular file", "op_sdext.c", after(FP_FN, "!S_ISREG(st.st_mode)", "0"))
mut("the parent directory is not tested", "op_sdext.c", after(FP_FN, "return file_private_check(parent, 1);", "return 1;"))
mut("the parent is tested as a file", "op_sdext.c", after(FP_FN, "return file_private_check(parent, 1);", "return file_private_check(parent, 0);"))
mut("the parent is the file itself", "op_sdext.c", after(FP_FN, "slash = strrchr(parent, '/');", "slash = parent + len;"))
# F: who calls it
mut("a program outside $netcred and set.netlogin calls it", "bp:cd", lambda t: t + "\n   x = SDEXT(path : @FM : 'FILE', @TRUE, SD_FILE_PRIVATE) # '1'\n")
mut("set.netlogin's call is not compared with 1", SNL, "SDEXT(cred.path : @FM : 'DIR', @TRUE, SD_FILE_PRIVATE) # '1'", "SDEXT(cred.path : @FM : 'DIR', @TRUE, SD_FILE_PRIVATE)")
mut("SDEXT is a plain intrinsic in BCOMP", "bp:bcomp", lambda t: t + '\n   intrinsics<-1> = "SDEXT"\n')
mut("SDEXT is not an internal intrinsic", "bp:bcomp", 'int.intrinsics<-1> = "SDEXT"', 'int.intrinsics<-1> = "SDEXX"')
# R: $netcred, the path
mut("the credential root is /tmp/sd-net", NCR, "'/var/lib/sd-net'", "'/tmp/sd-net'")
mut("the credential root is built twice", NCR, lambda t: t.replace("   tmp = path : '.new'\n", "   tmp = path : '.new'\n   zz = '/var/lib/sd-net/x'\n", 1))
mut("the Linux user comes from @logname", NCR, "lu = kernel(K$USERNAME, 0)", "lu = @logname")
mut("root may keep a login", NCR, "lu = '' or lu = 'root' or lu = 'sdsys'", "lu = '' or lu = 'sdsys'")
mut("sdsys may keep a login", NCR, "lu = '' or lu = 'root' or lu = 'sdsys'", "lu = '' or lu = 'root'")
mut("the user name is not length checked", NCR, "len(lu) > MAX.USERNAME.LEN", "len(lu) > 9999")
mut("the path is built before the user is validated", NCR,
    lambda t: t.replace("   cred.dir = NETCRED.ROOT : '/' : lu\n", "", 1).replace("   lu = kernel(K$USERNAME, 0)\n", "   cred.dir = NETCRED.ROOT : '/' : lu\n   lu = kernel(K$USERNAME, 0)\n", 1))
mut("the server name is not validated", NCR, "len(server) < 1 or len(server) > 16 or not(chk.ok) or index(lc.set, server[1, 1], 1) = 0", "len(server) < 1")
mut("a server name may start with a digit", NCR, " or index(lc.set, server[1, 1], 1) = 0", "")
mut("a server name of 17 is allowed", NCR, "len(server) > 16", "len(server) > 17")
mut("a server name may hold a slash", NCR, "chk.text = server ; chk.set = lc.set:digits", "chk.text = server ; chk.set = lc.set:digits:'/'")
mut("the copy has the login's own name", NCR, "tmp = path : '.new'", "tmp = path")
mut("the file is somewhere else", NCR, "path = cred.dir : '/' : server", "path = cred.dir : '/' : server : '.cred'")
# R: the test comes first
mut("the directory is not tested", NCR, "if not(dir.there) or SDEXT(cred.dir : @FM : 'DIR', @TRUE, SD_FILE_PRIVATE) # '1' then", "if not(dir.there) then")
mut("a missing directory is allowed", NCR, "if not(dir.there) or SDEXT(cred.dir : @FM : 'DIR', @TRUE, SD_FILE_PRIVATE) # '1' then", "if dir.there and SDEXT(cred.dir : @FM : 'DIR', @TRUE, SD_FILE_PRIVATE) # '1' then")
mut("READ opens a file it has not tested", NCR, after("case act = 'READ'", NC_TRUST_READ, ""))
mut("READ tests the file after it opens it", NCR,
    lambda t: after("case act = 'READ'", NC_TRUST_READ, "")(t).replace("         closeseq f\n", "         closeseq f\n" + NC_TRUST_READ, 1))
mut("DELETE removes a file it has not tested", NCR, after("case act = 'DELETE'", NC_TRUST_READ, ""))
mut("EXISTS says 1 without the test", NCR, after("case act = 'EXISTS'", "SDEXT(path : @FM : 'FILE', @TRUE, SD_FILE_PRIVATE) = '1'", "1"))
mut("WRITE renames a copy it has not tested", NCR, "if SDEXT(tmp : @FM : 'FILE', @TRUE, SD_FILE_PRIVATE) # '1' then", "if 0 then")
mut("WRITE tests the copy before it is written", NCR,
    lambda t: t.replace("if SDEXT(tmp : @FM : 'FILE', @TRUE, SD_FILE_PRIVATE) # '1' then", "if 0 then", 1).replace("         writeseq line to tmp.f else\n", "         if SDEXT(tmp : @FM : 'FILE', @TRUE, SD_FILE_PRIVATE) # '1' then err = 11454\n         writeseq line to tmp.f else\n", 1))
mut("a file that fails the test is reported as damaged", NCR, after("case act = 'READ'", "err = 11454:@vm:server:@vm:path", "err = 11456:@vm:server:@vm:path"))
mut("a file is opened a third time", NCR, lambda t: t.replace("         closeseq f\n", "         closeseq f\n         openseq path to f else null\n", 1))
mut("the copy is renamed twice", NCR, lambda t: t.replace("         if err # '' then void ospath(tmp, OS$DELETE)\n", "         void osrename(tmp, path)\n         if err # '' then void ospath(tmp, OS$DELETE)\n", 1))
# R: the file never holds the password
mut("the line holds a password", NCR, "line = 'v1'", "line = 'v1' : pw")
mut("WRITE writes the record raw", NCR, "line := '|' : one<i>", "line := '|' : record<i>")
mut("a password parameter appears", NCR, "subroutine netcred(action, server, record, pin, err)", "subroutine netcred(action, server, record, pin, err, password)")
mut("a second line is written", NCR, "         writeseq line to tmp.f else\n", "         writeseq 'x' to tmp.f else null\n         writeseq line to tmp.f else\n")
# R: READ and WRITE in order
mut("READ does not need the pin argument", NCR, after("case act = 'READ'", "gosub check.pin", "pin.ok = @true"))
mut("READ accepts another pin", NCR, "if one<6> # pin then", "if one<6> # one<6> then")
mut("READ does not look at the shape of the record", NCR, after("case act = 'READ'", "         gosub check.record\n", ""))
mut("READ hands the record back before the pin test", NCR, after("case act = 'READ'", "         if one<6> # pin then", "         record = one\n         if one<6> # pin then"))
mut("READ does not look for marks", NCR, "len(convert(marks, '', line)) # len(line)", "0")
mut("READ takes any layout", NCR, "dcount(line, @fm) # 8 or line<1> # 'v1'", "0")
mut("READ opens before it looks for the file", NCR, after("case act = 'READ'", "         if not(ospath(path, OS$EXISTS)) then\n            err = 11453:@vm:server\n            return\n         end\n", ""))
mut("WRITE keeps attribute 6 of the record", NCR, "         one<6> = pin\n", "")
mut("WRITE does not need the pin argument", NCR, after("case act = 'WRITE'", "gosub check.pin", "pin.ok = @true"))
mut("WRITE does not look at the shape of the record", NCR, after("case act = 'WRITE'", "         gosub check.record\n", ""))
mut("WRITE sets no umask", NCR, "         void umask(NETCRED.UMASK)\n", "")
mut("the umask is 022", NCR, "$define NETCRED.UMASK 63", "$define NETCRED.UMASK 18")
mut("the umask is not put back", NCR, "         void umask(old.umask)\n", "")
mut("the umask is put back after the write", NCR,
    lambda t: t.replace("         void umask(old.umask)\n", "", 1).replace("         closeseq tmp.f\n", "         closeseq tmp.f\n         void umask(old.umask)\n", 1))
mut("WRITE renames whatever the error", NCR, "         if err = '' then\n            if not(osrename(tmp, path)) then", "         if @true then\n            if not(osrename(tmp, path)) then")
mut("a failed write leaves the copy", NCR, "if err # '' then void ospath(tmp, OS$DELETE)", "if err # '' then null")
mut("an old copy is not removed first", NCR, "if ospath(tmp, OS$EXISTS) then", "if 0 then")
mut("a copy that could not be made is not noticed", NCR, "         if not(made) then\n            err = 11457", "         if 0 then\n            err = 11457")
mut("check.record: iterations have no ceiling", NCR, " or what + 0 > SCRAM$MAX.ITER", "")
mut("check.record: iterations have no floor", NCR, "what + 0 < SCRAM$MIN.ITER", "what + 0 < 1")
mut("check.record: iterations need not be a number", NCR, "or not(what matches '1N0N')", "")
mut("check.record: base64 allows a bar", NCR, "digits:'+/='", "digits:'+/=|'")
mut("check.record: a key may be long", NCR, "len(what) < 4 or len(what) > 128", "len(what) < 4 or len(what) > 1280")
mut("check.record: a pin may be upper case", NCR, "hex.set = digits:'abcdef'", "hex.set = digits:'abcdefABCDEF'")
mut("check.record: a pin may be short", NCR, "len(what) # 64", "len(what) < 8")
mut("check.record: created is anything", NCR, "'4N\"-\"2N\"-\"2N'", "'0X'")
mut("check.record: a remote user may hold a space", NCR, "os.chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':lc.set:digits:'._-'", "os.chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':lc.set:digits:'._- '")
mut("an unknown action is allowed through", NCR, "err = 2018:@vm:action", "err = 11452:@vm:action")
mut("EXISTS reports an error for no directory", NCR, "if act = 'EXISTS' then return", "null")
mut("EXISTS does not start at 0", NCR, "if act = 'EXISTS' then record = 0", "null")
mut("DELETE of nothing is not told", NCR, after("case act = 'DELETE'", "err = 11453:@vm:server", "err = 11457:@vm:server"))
# U: set.netlogin, the order of the checks
mut("set.netlogin is not internal", SNL, "$internal\nprogram set.netlogin", "program set.netlogin")
mut("set.netlogin is catalogued under another name", SNL, "$catalog $setnetlogin", "$catalog $setnetlogon")
mut("the NET gate is not asked", SNL, "if not(is.admin) and not(kernel(K$NET, -1)) then", "if not(is.admin) and 0 then")
mut("the NET gate is asked with 1 (set)", SNL, "kernel(K$NET, -1)", "kernel(K$NET, 1)")
mut("the administrator test is not made", SNL, "is.admin = kernel(K$ADMINISTRATOR, -1)", "is.admin = @false")
mut("the NET gate is asked after the definition", SNL,
    lambda t: t.replace("   if not(is.admin) and not(kernel(K$NET, -1)) then\n      @system.return.code = -ER$PERM\n      stop sysmsg(11460, acc) ;* This account does not have the NET gate\n   end\n", "", 1)
    .replace("   host = defs<found,2>\n", "   if not(is.admin) and not(kernel(K$NET, -1)) then\n      @system.return.code = -ER$PERM\n      stop sysmsg(11460, acc)\n   end\n   host = defs<found,2>\n", 1))
mut("the account list is not tested", SNL, "index(',':downcase(defs<found,7>):',', ',':acc:',', 1) = 0", "0")
mut("the account list is a substring test", SNL, "index(',':downcase(defs<found,7>):',', ',':acc:',', 1) = 0", "index(downcase(defs<found,7>), acc, 1) = 0")
mut("the account list binds the administrator too", SNL, "if not(is.admin) then\n      if index(", "if @true then\n      if index(")
mut("the account name is not lower cased", SNL, "acc = downcase(@who)", "acc = @who")
mut("the server name is not validated", SNL, "len(name) < 1 or len(name) > 16 or not(chk.ok) or index(lc.set, name[1, 1], 1) = 0", "len(name) < 1")
mut("two words after the verb are allowed", SNL, "if dcount(words, ' ') # 2 then", "if dcount(words, ' ') < 2 then")
mut("the definition's pin is not tested for form", SNL, "if len(pin) # 64 or not(chk.ok) then", "if 0 then")
mut("sdsys may run it", SNL, "lu = '' or lu = 'sdsys' or lu = 'root'", "lu = ''")
mut("the Linux user comes from @logname", SNL, "lu = kernel(K$USERNAME, 0)", "lu = @logname")
mut("sudo may ask for a password", SNL, "   if elev[1, 5] = 'sudo ' then elev = 'sudo -n ' : elev[6, 9999]\n", "")
mut("the helper is run with another word", SNL, "elev : ' netcred-dir 2>&1'", "elev : ' netcred-dir all 2>&1'")
mut("a second command is run", SNL, "   stat = os.error()\n", "   stat = os.error()\n   os.execute 'id' capturing zz\n")
mut("the helper's path need not end in the user", SNL, "cred.path[len(cred.path) - len(tail) + 1, len(tail)] # tail or SDEXT", "SDEXT")
mut("the directory is not tested", SNL, " or SDEXT(cred.path : @FM : 'DIR', @TRUE, SD_FILE_PRIVATE) # '1'", "")
mut("the helper's success line is any line", SNL, "out<i>[1, 13] = 'netcred-dir: ' and ", "")
# U: prompts and the connection
mut("the password is asked before the user", SNL, lambda t: t.replace("   input ru\n", "   input pw HIDDEN\n   input ru\n", 1))
mut("the user is asked twice", SNL, lambda t: t.replace("   input ru\n", "   input ru\n   input ru\n", 1))
mut("an empty user goes on", SNL, "if ru = '' or len(ru) > MAX.USERNAME.LEN or not(chk.ok) then", "if 0 then")
mut("an empty password goes on", SNL, "   if pw = '' then\n      @system.return.code = -ER$ARGS\n      stop sysmsg(11468)", "   if 0 then\n      @system.return.code = -ER$ARGS\n      stop sysmsg(11468)")
mut("the socket is opened without TLS", SNL, "SKT$BLOCKING + SKT$TLS", "SKT$BLOCKING")
mut("the socket is opened with no timeout", SNL, ", config('NETWAIT'))", ")")
mut("the timeout is the constant it used to be", SNL, "SKT$BLOCKING + SKT$TLS, config('NETWAIT'))", "SKT$BLOCKING + SKT$TLS, NET.CONNECT.SECS)")
mut("a second socket is opened", SNL, lambda t: t.replace("   spki = downcase(", "   skt2 = open.socket(host, port, SKT$BLOCKING + SKT$TLS, NET.CONNECT.SECS)\n   spki = downcase(", 1))
mut("the host is not the definition's", SNL, "host = defs<found,2>", "host = 'localhost'")
mut("the pin is not the definition's", SNL, "pin = downcase(defs<found,5>)", "pin = ''")
mut("the pin is not compared", SNL, "if spki # pin then", "if spki # spki then")
mut("the pin is compared after the Ack", SNL,
    lambda t: t.replace("if spki # pin then", "if 0 then", 1).replace("   if not(acked) then", "   if spki # pin then\n      fail.num = 11471 ; fail.a1 = host ; fail.a2 = port ; fail.a3 = name\n      gosub give.up\n   end\n   if not(acked) then", 1))
mut("the pin is compared after the first packet", SNL,
    lambda t: t.replace("if spki # pin then", "if 0 then", 1).replace("   gosub read.packet\n", "   if spki # pin then\n      fail.num = 11471 ; fail.a1 = host ; fail.a2 = port ; fail.a3 = name\n      gosub give.up\n   end\n   gosub read.packet\n", 1))
mut("a mismatch only warns", SNL, "      fail.num = 11471 ; fail.a1 = host ; fail.a2 = port ; fail.a3 = name   ;* The key is not the key in the definition\n      gosub give.up\n", "      crt 'warning'\n")
mut("the hash is not lower cased", SNL, "spki = downcase(trim(socket.info(skt, SKT$INFO.TLS.SPKI)))", "spki = trim(socket.info(skt, SKT$INFO.TLS.SPKI))")
mut("an empty hash goes on", SNL, "if len(spki) # 64 or not(chk.ok) then", "if len(spki) > 64 then")
mut("a read has no timeout", SNL, "b = read.socket(skt, 1, SKT$BLOCKING, NET.READ.MS)", "b = read.socket(skt, 1, SKT$BLOCKING, 0)")
mut("a write has no timeout", SNL, "void write.socket(skt, pk, SKT$BLOCKING, NET.READ.MS)", "void write.socket(skt, pk, SKT$BLOCKING, 0)")
mut("a second place writes to the socket", SNL, lambda t: t.replace("   spki = downcase(", "   void write.socket(skt, 'x', SKT$BLOCKING, NET.READ.MS)\n   spki = downcase(", 1))
mut("the first packet is sent before the pin test", SNL, lambda t: t.replace("   skt.open = @true\n", "   skt.open = @true\n   ptype = SrvrScramFirst ; pdata = 'x' ; gosub send.packet\n", 1))
# U: the exchange
mut("client-first has no binding", SNL, "pdata = 'p=tls-exporter,,' : cfirst.bare", "pdata = 'n,,' : cfirst.bare")
mut("a missing binding goes on", SNL, "   if cbind = '' then", "   if 0 then")
mut("the nonce is not checked", SNL, "nonce[1, len(cnonce)] # cnonce or len(nonce) = len(cnonce)", "0")
mut("the iteration count is not bounded", SNL, "iter < SCRAM$MIN.ITER or iter > SCRAM$MAX.ITER", "iter < 1")
mut("the iteration count need not be a number", SNL, "or not(iter matches '1N0N')", "")
mut("the salt is not checked", SNL, "len(salt) < 4 or len(salt) > 128 or not(chk.ok)", "len(salt) < 0")
mut("the signature is not compared", SNL, "SDEXT(in.pkt[3, 999999] : @FM : expect.v, @TRUE, SD_CTEQUAL) # '1'", "0")
mut("the signature is compared in the open", SNL, "SDEXT(in.pkt[3, 999999] : @FM : expect.v, @TRUE, SD_CTEQUAL) # '1'", "in.pkt[3, 999999] # expect.v")
mut("a missing signature goes on", SNL, "if in.pkt[1, 2] # 'v=' then", "if 0 then")
# U: the password and the keys
mut("the password is printed", SNL, "   salted = SDEXT(pw :", "   crt pw\n   salted = SDEXT(pw :")
mut("the password is a message argument", SNL, "crt sysmsg(11477, name, ru)", "crt sysmsg(11477, name, pw)")
mut("the password is audited", SNL, "' remote=' : ru)", "' remote=' : ru : ' pw=' : pw)")
mut("the password is stored", SNL, "   rec<5> = srvr.key\n", "   rec<5> = srvr.key\n   rec<6> = pw\n")
mut("the password is kept after the derivation", SNL, "   pw = ''\n   if salted = '' then", "   if salted = '' then")
mut("give.up keeps the password", SNL, "   pw = ''\n   salted = ''\n   client.key = ''", "   salted = ''\n   client.key = ''")
mut("give.up keeps the server key", SNL, "   srvr.key = ''\n   expect.v = ''\n   proof = ''\n   rec = ''", "   expect.v = ''\n   proof = ''\n   rec = ''")
mut("give.up leaves the socket open", SNL, "   if skt.open then\n      close.socket skt\n      skt.open = @false\n   end\n   @system.return.code = -ER$FAILED", "   @system.return.code = -ER$FAILED")
mut("a key is a message argument", SNL, "fail.num = 11476 ; fail.a1 = 'the proof'", "fail.num = 11476 ; fail.a1 = client.key")
mut("the server key is displayed", SNL, "   srvr.key = SDEXT(salted : @FM : 'Server Key', @TRUE, SD_HMACSHA256)\n", "   srvr.key = SDEXT(salted : @FM : 'Server Key', @TRUE, SD_HMACSHA256)\n   display srvr.key\n")
mut("the login is written before the signature is checked", SNL, "   salted = SDEXT(pw :", "   call $netcred('WRITE', name, rec, pin, err)\n   salted = SDEXT(pw :")
mut("a failure writes", SNL, "   rec = ''\n   if skt.open then", "   call $netcred('WRITE', name, rec, pin, err)\n   rec = ''\n   if skt.open then")
mut("a failure deletes the old login", SNL, "   rec = ''\n   if skt.open then", "   call $netcred('DELETE', name, rec, pin, err)\n   rec = ''\n   if skt.open then")
mut("a refusal stops outside give.up", SNL, "      fail.num = 11475\n      gosub give.up\n", "      stop sysmsg(11475)\n")
mut("the server's text is not a failure", SNL, "   fail.num = 11474 ; fail.a1 = reason\n", "   crt reason\n   fail.num = 11474 ; fail.a1 = reason\n   return\n")
mut("the record carries the pin", SNL, "   rec<5> = srvr.key\n", "   rec<5> = srvr.key\n   rec<6> = pin\n")
mut("the record is not cleared first", SNL, "   rec = ''\n   rec<1> = ru\n", "   rec<1> = ru\n")
mut("the audit line is in upper case", SNL, "'set.netlogin server='", "'SET.NETLOGIN server='")
mut("the audit line carries the pin", SNL, "' remote=' : ru)", "' remote=' : ru : ' pin=' : pin)")
mut("the audit line is written before the login is stored", SNL,
    lambda t: t.replace("   void kernel(K$AUDIT, 'set.netlogin server=' : name : ' remote=' : ru)\n", "", 1).replace("   call $netcred('WRITE'", "   void kernel(K$AUDIT, 'set.netlogin server=' : name : ' remote=' : ru)\n   call $netcred('WRITE'", 1))
mut("a second audit line is written", SNL, "   @system.return.code = 0\n   crt sysmsg(11477", "   void kernel(K$AUDIT, 'set.netlogin done')\n   @system.return.code = 0\n   crt sysmsg(11477")
mut("success is not exit 0", SNL, "   @system.return.code = 0\n   crt sysmsg(11477", "   @system.return.code = -ER$FAILED\n   crt sysmsg(11477")
# Y: delete.netlogin
mut("delete.netlogin is not internal", DNL, "$internal\nprogram delete.netlogin", "program delete.netlogin")
mut("delete.netlogin asks for the NET gate", DNL, lambda t: t.replace("   words = trim(@sentence)\n", "   if not(kernel(K$NET, -1)) then stop\n   words = trim(@sentence)\n", 1))
mut("delete.netlogin asks for the administrator", DNL, lambda t: t.replace("   words = trim(@sentence)\n", "   if not(kernel(K$ADMINISTRATOR, -1)) then stop\n   words = trim(@sentence)\n", 1))
mut("delete.netlogin does not ask if there is one", DNL, "call $netcred('EXISTS', name, rec, '', err)", "rec = 1")
mut("delete.netlogin does not validate the name", DNL, "len(name) < 1 or len(name) > 16 or not(chk.ok) or index(lc.set, name[1, 1], 1) = 0", "len(name) < 1")
mut("delete.netlogin reads the login", DNL, "call $netcred('DELETE', name, rec, '', err)", "call $netcred('READ', name, rec, '', err)")
mut("delete.netlogin audits in upper case", DNL, "'delete.netlogin server='", "'DELETE.NETLOGIN server='")
mut("delete.netlogin audits the password", DNL, "'delete.netlogin server=' : name)", "'delete.netlogin server=' : name : ' pw=' : rec)")
mut("delete.netlogin audits before the delete", DNL,
    lambda t: t.replace("   void kernel(K$AUDIT, 'delete.netlogin server=' : name)\n", "", 1).replace("   call $netcred('DELETE'", "   void kernel(K$AUDIT, 'delete.netlogin server=' : name)\n   call $netcred('DELETE'", 1))
mut("delete.netlogin prompts", DNL, lambda t: t.replace("   words = trim(@sentence)\n", "   input zz\n   words = trim(@sentence)\n", 1))
# V: the VOC entries
mut("set.netlogin is not in newvoc", "newvoc.list", lambda t: t.replace("set.netlogin", "", 1))
mut("delete.netlogin is not in newvoc", "newvoc.list", lambda t: t.replace("delete.netlogin", "", 1))
mut("the template entry names another program", "voc:set.netlogin", "$setnetlogin", "$setnetlogon")
mut("the template entry of delete.netlogin is a paragraph", "voc:delete.netlogin", "V\n", "PA\n")
mut("the newvoc entry names another program", "newvoc:set.netlogin", "$setnetlogin", "$deletenetlogin")
mut("the newvoc entry is not a catalogued verb", "newvoc:delete.netlogin", "CA", "BA")
# H: the messages
mut("message 11450 is missing", "msg:11450", lambda t: None)
mut("message 11460 is empty", "msg:11460", lambda t: "")
mut("message 11464 takes two lines", "msg:11464", lambda t: t.rstrip("\n") + "\nsecond line\n")
mut("11464 stops saying the password is not stored", "msg:11464", lambda t: t.replace("Your password is used once here and is not stored", "Your password is used here", 1))
mut("11477 says the password is stored", "msg:11477", lambda t: t.replace("The password is not stored", "The password is stored", 1))
mut("11471 stops saying nothing was sent", "msg:11471", lambda t: t.replace("Nothing was sent to it and nothing was stored", "Nothing was stored", 1))
mut("11460 names the gate in upper case", "msg:11460", lambda t: t.replace("net-on", "NET-ON", 1))
mut("11455 stops telling the person what to do", "msg:11455", lambda t: t.replace("Run set.netlogin %1 again", "Try later", 1))
mut("11454 stops saying nothing was used", "msg:11454", lambda t: t.replace("Nothing was used", "Used", 1))
mut("message 11475 stops saying nothing was stored", "msg:11475", lambda t: t.replace("Nothing was stored", "", 1))
mut("message 11469 has a place the call does not fill", "msg:11469", lambda t: t.rstrip("\n") + " %5\n")
mut("11466 is never used", SNL, "display sysmsg(11466)", "display sysmsg(11465)")
mut("11479 is never used", SNL, "fail.num = 11479", "fail.num = 11473")
mut("11471 loses its third argument", SNL, "fail.num = 11471 ; fail.a1 = host ; fail.a2 = port ; fail.a3 = name", "fail.num = 11471 ; fail.a1 = host ; fail.a2 = port")
mut("11477 loses its second argument", SNL, "crt sysmsg(11477, name, ru)", "crt sysmsg(11477, name)")
mut("11454 loses its path", NCR, after("case act = 'READ'", "err = 11454:@vm:server:@vm:path", "err = 11454:@vm:server"))
mut("11457 loses its status", NCR, "err = 11457:@vm:server:@vm:path:@vm:status()", "err = 11457:@vm:server:@vm:path")
mut("$netcred gives a message number outside the block", NCR, "err = 11455:@vm:server", "err = 11499:@vm:server")
# E: the helper and the sudoers line
mut("the helper's root is another directory", "sd-elevate", "SD_NET_ROOT_REAL=/var/lib/sd-net", "SD_NET_ROOT_REAL=/var/lib/sdnet")
mut("the sudoers line gives netcred-dir a wildcard", "sdcore.sudoers", "/usr/local/sbin/sd-elevate netcred-dir", "/usr/local/sbin/sd-elevate netcred-dir *")
mut("the sudoers line is lost", "sdcore.sudoers", ", /usr/local/sbin/sd-elevate netcred-dir", "")
mut("the sudoers line gives netcred-dir an argument", "sdcore.sudoers", "/usr/local/sbin/sd-elevate netcred-dir", "/usr/local/sbin/sd-elevate netcred-dir --dry-run")
# B5: nobody else asks the gate
mut("another program asks K$NET", "bp:cd", lambda t: t + "\n   x = kernel(K$NET, -1)\n")


# ---- slice 2c: the files-only route ---------------------------------------------------------------------------------------------------
AFO, AP2, MOD, CRA, CAC = "apifilesok", "apisrvr", "modifya", "createa", "create_account"
# !apifilesok: every number of the list, taken out of the table, one at a time (a request the server then refuses a files-only client)
for _n in FILES_ALLOWED:
    mut("apifilesok: %d is taken out of the table" % _n, AFO, "files.ok := '%d,'" % _n, "files.ok := ''")
# ...and every kind of number that must stay refused, put into it, one at a time (the first four and the last are the ones the owner named: execute, call, logins, SDNet)
for _n in (0, 3, 20, 21, 22, 23, 24, 25, 27, 28, 29, 47, 48, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 80):
    mut("apifilesok: %d is put into the table" % _n, AFO, "files.ok := '49,'", "files.ok := '49,'\nfiles.ok := '%d,'" % _n)
mut("apifilesok: one line holds two numbers (49,21)", AFO, "files.ok := '49,'", "files.ok := '49,21,'")
mut("apifilesok: the table starts from nothing (the first number cannot match)", AFO, "files.ok = ','", "files.ok = ''")
mut("apifilesok: 3 is allowed always", AFO, "if entered then return 0", "if 0 then return 0")
mut("apifilesok: 3 is refused always", AFO, "if entered then return 0", "return 0")
mut("apifilesok: 3 is not special (it falls to the table)", AFO, "if action = 3 then", "if action = 3 and 0 then")
mut("apifilesok: an empty action is tested no more", AFO, "if action = '' then return 0\n", "")
mut("apifilesok: a non-number is tested no more", AFO, "if not(num(action)) then return 0\n", "")
mut("apifilesok: the table is searched without its commas (4 matches 49)", AFO, "',' : action : ','", "action")
mut("apifilesok: the default is yes", AFO, "if not(index(files.ok, ',' : action : ',', 1)) then return 0", "if not(index(files.ok, ',' : action : ',', 1)) then return 1")
mut("apifilesok: an unknown number is yes", AFO, "if not(index(files.ok, ',' : action : ',', 1)) then return 0", "if not(index(files.ok, ',' : action : ',', 1) or action > 69) then return 0")
mut("apifilesok: it is not $internal", AFO, "$internal\nfunction", "function")
mut("apifilesok: it is catalogued under another name", AFO, "$catalog !apifilesok", "$catalog !apifilesk")
mut("apifilesok: it asks the kernel something", AFO, "$catalog !apifilesok\n", "$catalog !apifilesok\nx = kernel(K$USERNAME, 0)\n")
mut("apifilesok: it writes something", AFO, "$catalog !apifilesok\n", "$catalog !apifilesok\nwriteseq 'x' to zz else null\n")
# apisrvr: the declaration, the mark, the order of the route
mut("apisrvr: the mark is a plain variable (not in the common block)", AP2, "files.only,         ;*", "files.zz,           ;*")
mut("apisrvr: the mark is not started false", AP2, "   files.only = @false\n", "")
mut("apisrvr: the mark is started false twice", AP2, "   files.only = @false\n", "   files.only = @false\n   files.only = @false\n")
mut("apisrvr: the mark is started at EVERY entry (an abort would clear it), not in the first-time block",
    AP2, lambda t: t.replace("   files.only = @false\n", "", 1).replace("if not(kernel(K$CPROC.LEVEL,0)) then", "files.only = @false\nif not(kernel(K$CPROC.LEVEL,0)) then", 1))
mut("apisrvr: the mark is cleared after the login", AP2, "               response = 'v=' : scram.ssig\n               logged.in = @true\n",
    "               response = 'v=' : scram.ssig\n               logged.in = @true\n               files.only = @false\n")
mut("apisrvr: the mark is cleared at an SDLogto", AP2, "if not(master.login.done) then\n   master.login.done = @true", "files.only = @false\nif not(master.login.done) then\n   master.login.done = @true")
mut("apisrvr: the mark is set for everybody", AP2, "if api.files.login then\n                  files.only = @true", "if @true then\n                  files.only = @true")
mut("apisrvr: the mark is never set", AP2, "files.only = @true", "files.zz = @true")
mut("apisrvr: the mark is set before the identity is assumed",
    AP2, lambda t: t.replace("                  files.only = @true\n", "", 1).replace("               if not(kernel(K$ASSUME.USER, scram.user)) then", "               files.only = api.files.login\n               if not(kernel(K$ASSUME.USER, scram.user)) then", 1))
mut("apisrvr: the sdusers test is gone", AP2, "if not(is_grp_member(scram.user, 'sdusers')) then", "if 0 then")
mut("apisrvr: sdfiles is read before sdapi",
    AP2, lambda t: t.replace("is_grp_member(scram.user, 'sdapi')", "is_grp_member(scram.user, 'sdfiles') ;* swapped", 1).replace("api.in.sdfiles = is_grp_member(scram.user, 'sdfiles')", "api.in.sdfiles = is_grp_member(scram.user, 'sdapi')", 1))
mut("apisrvr: sdapi does not win (the sdfiles route is read for everybody)", AP2, "                  if not(api.in.sdapi) then\n", "                  if @true then\n")
mut("apisrvr: a member of sdapi is marked files-only too", AP2, "                     api.files.login = @true\n", "                     api.files.login = @true\n                  end\n                  if api.in.sdapi then\n                     api.files.login = @true\n")
mut("apisrvr: neither group is not refused", AP2, "if not(api.in.sdfiles) then", "if 0 then")
mut("apisrvr: neither group gives another reason", AP2, "scram.refuse.reason = 'not a member of sdapi or sdfiles'", "scram.refuse.reason = 'not a member of sdfiles'")
mut("apisrvr: neither group names only sdapi (the reason before 19 Oct 26)", AP2, "scram.refuse.reason = 'not a member of sdapi or sdfiles'", "scram.refuse.reason = 'not a member of sdapi'")
mut("apisrvr: neither group gives another message", AP2, "                        scram.refuse.reason = 'not a member of sdapi or sdfiles'\n                        abort.message = sysmsg(10073, scram.user)",
    "                        scram.refuse.reason = 'not a member of sdapi or sdfiles'\n                        abort.message = sysmsg(5009)")
mut("apisrvr: the sdfiles lookup that cannot answer is not looked at", AP2, "if api.files.stat # 0 then", "if 0 then")
mut("apisrvr: the sdfiles status is not read", AP2, "api.files.stat = status()", "api.files.stat = 0")
mut("apisrvr: the sdapi lookup that cannot answer is not looked at", AP2, "if api.route.stat # 0 then", "if 0 then")
mut("apisrvr: an unreadable sdfiles route is let in", AP2, "scram.refuse.reason = 'the sdfiles route could not be read, status ' : api.files.stat\n",
    "scram.refuse.reason = 'the sdfiles route could not be read, status ' : api.files.stat\n                        api.files.login = @true\n")
mut("apisrvr: sdsys is not exempt by name", AP2, "if not(downcase(scram.user) = 'sdsys') then", "if @true then")
mut("apisrvr: sdsys's name is compared in the case it was typed", AP2, "if not(downcase(scram.user) = 'sdsys') then", "if not(scram.user = 'sdsys') then")
mut("apisrvr: the login by this route is not audited", AP2, drop_line(r"'api login route=sdfiles write='"))
mut("apisrvr: the login audit line is upper case", AP2, "'api login route=sdfiles write='", "'API LOGIN route=sdfiles write='")
mut("apisrvr: the login audit line names the wrong route", AP2, "'api login route=sdfiles write='", "'api login route=sdapi write='")
# apisrvr: the gate
mut("apisrvr: the gate is not taken", AP2, "   if files.only then\n", "   if 0 then\n")
mut("apisrvr: the gate is taken for every session", AP2, "   if files.only then\n", "   if @true then\n")
mut("apisrvr: the gate asks no function", AP2, "if not(apifilesok(action, master.login.done, files.write, files.admin)) then", "if 0 then")
mut("apisrvr: the account is always 'not yet entered' (3 allowed for ever)", AP2, "apifilesok(action, master.login.done, files.write, files.admin)", "apifilesok(action, @false, files.write, files.admin)")
mut("apisrvr: the account is always 'entered' (the first 3 is refused)", AP2, "apifilesok(action, master.login.done, files.write, files.admin)", "apifilesok(action, @true, files.write, files.admin)")
mut("apisrvr: the refusal does not skip the dispatch", AP2, "         goto return.status.set\n", "         null\n")
mut("apisrvr: the refusal is not an error answer", AP2, "         server.error = SV$ON.ERROR\n*", "*")
mut("apisrvr: the refusal says another message", AP2, "sysmsg(11480, action)", "sysmsg(5270)")
mut("apisrvr: the refusal does not name the request", AP2, "sysmsg(11480, action)", "sysmsg(11480)")
mut("apisrvr: the refusal is not audited", AP2, drop_line(r"'api refused request='"))
mut("apisrvr: the refusal audit line is upper case", AP2, "'api refused request='", "'API REFUSED request='")
mut("apisrvr: the refusal audit line has no route", AP2, "' route=sdfiles write=' : write.word : ' admin=' : admin.word : ' user=' : @logname)  ;* @logname, not logname", "' write=' : write.word : ' admin=' : admin.word : ' user=' : @logname)  ;* @logname, not logname")
mut("apisrvr: the refusal audit line uses a plain variable that an abort loses", AP2, "' route=sdfiles write=' : write.word : ' admin=' : admin.word : ' user=' : @logname)  ;* @logname, not logname", "' route=sdfiles write=' : write.word : ' admin=' : admin.word : ' user=' : logname)  ;* @logname, not logname")
mut("apisrvr: the gate comes after the dispatch",
    AP2, lambda t: t.replace(t[t.index("   if files.only then\n"):t.index("   cproc.date = date()")], "", 1).replace("   st = status()\nreturn.status.set:", t[t.index("   if files.only then\n"):t.index("   cproc.date = date()")] + "   st = status()\nreturn.status.set:", 1))
mut("apisrvr: the gate comes before the not-logged-in test",
    AP2, lambda t: t.replace(t[t.index("   if files.only then\n"):t.index("   cproc.date = date()")], "", 1).replace("   if not(logged.in) then\n      * 14 Sep 26 dm - 47 and 48", t[t.index("   if files.only then\n"):t.index("   cproc.date = date()")] + "   if not(logged.in) then\n      * 14 Sep 26 dm - 47 and 48", 1))
mut("apisrvr: a second use of the function (a second gate that lets 20 through)", AP2, "   cproc.date = date()\n", "   if files.only and action = 20 then null\n   if apifilesok(action, 1) then null\n   cproc.date = date()\n")
mut("apisrvr: master.login.done is set at another place too", AP2, "   tty = 'apisrvr'\n", "   tty = 'apisrvr'\n   master.login.done = @true\n")
# MODIFY.ACCOUNT
mut("modifya: the word FILES-ON is not a word", MOD, "case action = 'FILES-ON'", "case action = 'FILES-ONX'")
mut("modifya: the word FILES-OFF is not a word", MOD, "case action = 'FILES-OFF'", "case action = 'FILES-OFX'")
mut("modifya: FILES-ON asks for off", MOD, "files.grp = 'sdfiles'\n         files.want = @true\n         gosub set.files", "files.grp = 'sdfiles'\n         files.want = @false\n         gosub set.files")
mut("modifya: FILES-OFF asks for on", MOD, "files.grp = 'sdfiles'\n         files.want = @false\n         gosub set.files", "files.grp = 'sdfiles'\n         files.want = @true\n         gosub set.files")
mut("modifya: the syntax lines do not name the words", MOD, drop_line(r"modify\.account <account> files-on \| files-off"))
mut("modifya: the list of words does not name them", MOD, "files-on, files-off, files-write-on, files-write-off, files-admin-on, files-admin-off, ai-on, ai-off, suspended or unsuspended", "suspended or unsuspended")
mut("modifya: set.files lets a group account through", MOD, "   if group.name[1,4] # 'sdu_' then\n      @system.return.code = -ER$FAILED\n      if group.name[1,4] = 'sdg_' then",
    "   if 0 then\n      @system.return.code = -ER$FAILED\n      if group.name[1,4] = 'sdg_' then")
mut("modifya: a group account is told 10081 and not 10087", MOD, "crt sysmsg(10087, acc.name)  ;* %1 is a group account and has no remote access; reach it with logto\n      end else\n         crt sysmsg(10081, acc.name, 2)",
    "crt sysmsg(10081, acc.name, 2)\n      end else\n         crt sysmsg(10081, acc.name, 2)")
mut("modifya: the Linux user is not checked for its name", MOD, "if not(valid_os_name(files.user)) then", "if 0 then")
mut("modifya: the Linux user comes from the account name", MOD, "files.user = group.name[5,999]", "files.user = acc.name")
mut("modifya: membership is not read three-valued", MOD, "has.files = is_grp_member(files.user, 'sdfiles')\n   files.stat = status()", "has.files = is_grp_member(files.user, 'sdfiles')\n   files.stat = 0")
mut("modifya: FILES-ON does not need sdusers", MOD, "in.sdusers = is_grp_member(files.user, 'sdusers')", "in.sdusers = @true")
mut("modifya: FILES-OFF needs sdusers too", MOD, "if files.stat = 0 and files.want then\n      in.sdusers", "if files.stat = 0 then\n      in.sdusers")
mut("modifya: already in the state is not noticed", MOD, "if nothing.to.do then", "if 0 then")
mut("modifya: the group's existence is not checked", MOD, "files.found = is_group(files.grp)", "files.found = @true")
mut("modifya: FILES-ON adds to sdapi", MOD, "addgroup \" : files.user : \" \" : cg.group", "addgroup \" : files.user : \" sdapi\"")
mut("modifya: FILES-OFF takes the person out of sdapi", MOD, "delgroup \" : files.user : \" \" : cg.group", "delgroup \" : files.user : \" sdapi\"")
mut("modifya: the helper is not sd-elevate", MOD, "sudo /usr/local/sbin/sd-elevate addgroup \" : files.user", "sudo /usr/sbin/usermod -aG sdfiles \" : files.user")
mut("modifya: the change is not read back", MOD, "cg.now = is_grp_member(files.user, cg.group)", "cg.now = cg.want")
mut("modifya: a read back that differs is a success", MOD, "if files.stat = 0 and cg.now # cg.want then files.stat = 2", "null")
mut("modifya: the line shows the request and not the read back", MOD, "crt sysmsg(11482, acc.name, if now.files then 'yes' else 'no')", "crt sysmsg(11482, acc.name, if files.want then 'yes' else 'no')")
mut("modifya: the audit line is upper case",
    MOD, "void kernel(K$AUDIT, 'modify.account ' : downcase(action) : ' account=' : acc.name)\n   if admin.removed then", "void kernel(K$AUDIT, 'MODIFY.ACCOUNT ' : action : ' account=' : acc.name)\n   if admin.removed then")
mut("modifya: the audit line is written before the change",
    MOD, lambda t: t.replace("   void kernel(K$AUDIT, 'modify.account ' : downcase(action) : ' account=' : acc.name)\n   if admin.removed then", "   if admin.removed then", 1).replace("   if files.want then\n      files.found = is_group(files.grp)", "   void kernel(K$AUDIT, 'modify.account ' : downcase(action) : ' account=' : acc.name)\n   if files.want then\n      files.found = is_group(files.grp)", 1))
mut("modifya: a failed change is reported as done",     # 19 Oct 26 (finish 2): the failure block now begins with the write.removed lines, so the whole block is cut by a pattern
    MOD, lambda t: re.sub(r"   if files\.stat # 0 then\n      @system\.return\.code = -ER\$FAILED\n\*     A group above HAS gone.*?      crt sysmsg\(10081, acc\.name, files\.stat\)\n      return\n   end\n\n   @system\.return\.code = 0\n   void kernel",
                          "   @system.return.code = 0\n   void kernel", t, count=1, flags=re.S))
mut("modifya: a failure after the write group went writes no audit line for the removal", MOD, "      void kernel(K$AUDIT, 'modify.account files-write-off account=' : acc.name)\n", "")
mut("modifya: a failure after the write group went does not print the write group's line", MOD, "      gosub write.removed.line\n   end\n   return\n", "   end\n   return\n")
mut("modifya: a failure after the write group went audits the action asked for", MOD, "'modify.account files-write-off account=' : acc.name)", "'modify.account ' : downcase(action) : ' account=' : acc.name)")
# CREATEA and CREATE.ACCOUNT
mut("createa: FILES-ON is not a word", CRA, "case upcase(token) = 'FILES-ON'", "case upcase(token) = 'FILES-ONX'")
mut("createa: FILES-ON sets the NET gate", CRA, "'FILES-ON'\n            settings<CA$FILES> = 1", "'FILES-ON'\n            settings<CA$NET> = 1")   # the parser's line (19 Oct 26: the audit builder reads the same setting once more)
mut("createa: FILES-ON sets the setting to 2", CRA, "'FILES-ON'\n            settings<CA$FILES> = 1", "'FILES-ON'\n            settings<CA$FILES> = 2")
mut("createa: the syntax line does not name it", CRA, " {files-on}", "")
mut("createacc.h: CA$FILES is 35 (the NET setting's number)", "createacc.h", rx(r"(\$define\s+CA\$FILES\s+)36", r"\g<1>35"))
mut("createacc.h: CA$FILES is not defined", "createacc.h", drop_line(r"\$define\s+CA\$FILES"))
mut("create_account: any non-zero setting is a request", CAC, "files.want = (settings<CA$FILES> = 1)", "files.want = (settings<CA$FILES> # 0)")
mut("create_account: the group is not looked for", CAC, "files.found = is_group(files.grp.name)", "files.found = @true")
mut("create_account: a missing group is not told", CAC, "if not(files.found) then\n         @system.return.code = -ER$FAILED\n         err = 10024:@vm:files.grp.name", "if 0 then\n         @system.return.code = -ER$FAILED\n         err = 10024:@vm:files.grp.name")
mut("create_account: an unreadable /etc/group is not looked at", CAC, "if files.stat # 0 then\n      @system.return.code = -ER$FAILED\n      err = 10081:@vm:acc.uname:@vm:files.stat", "if 0 then\n      @system.return.code = -ER$FAILED\n      err = 10081:@vm:acc.uname:@vm:files.stat")
mut("create_account: the group is looked for AFTER the Linux user is made",
    CAC, lambda t: (lambda m: t.replace(m.group(1), "", 1).replace("      if not(is_grp_member(acc.uname,'sdusers')) then", m.group(1) + "      if not(is_grp_member(acc.uname,'sdusers')) then", 1))(
        re.search(r"(\* 17 Oct 26 dm - S\.65 slice 2c: the group sdfiles is looked for.*?\n     end\n)", t, re.S)))
# 24 Oct 26: the two tests gained "or ai.want" and a trailing comment on 23 Oct (S.69 step 2); the mutants cut the whole first line of each, as before
mut("create_account: a GROUP account is not refused", CAC, "if files.want or files.write.want or files.admin.want or ai.want then      ;* 23 Oct 26, S.69 step 2: and no AI gate to give, for the same reason\n",
    "if 0 then\n")
mut("create_account: an OTHER account is not refused", CAC, "if files.want or files.write.want or files.admin.want or ai.want then      ;* 23 Oct 26, S.69 step 2: nor an AI gate\n",
    "if 0 then\n")
mut("create_account: the join goes to sdapi", CAC, "sd-elevate addgroup \":acc.uname:\" \":files.grp.name", "sd-elevate addgroup \":acc.uname:\" sdapi\"")
mut("create_account: the join is not asked for", CAC, "      if files.want then\n         files.grp.name = 'sdfiles'\n         gosub join.files.group", "      if @true then\n         files.grp.name = 'sdfiles'\n         gosub join.files.group")
mut("create_account: a failed join is not reported", CAC, "   route.stat = OS.ERROR()\n   if route.stat # 0 then\n      @system.return.code = -ER$FAILED\n      err = 10081:@vm:acc.uname:@vm:route.stat", "   route.stat = OS.ERROR()\n   if 0 then\n      @system.return.code = -ER$FAILED\n      err = 10081:@vm:acc.uname:@vm:route.stat")
mut("create_account: the state line shows the request", CAC, "if is_grp_member(acc.uname, 'sdfiles') then 'yes' else 'no'", "if files.want then 'yes' else 'no'")
mut("create_account: the state line is not printed", CAC, drop_line(r"crt sysmsg\(11482,"))
mut("a register field ACC$FILES is added", "syscom/keys.h", lambda t: t + "\n$define ACC$FILES            16\n")
# the manifest and the restore
mut("acc_os_info: the manifest key is `files`", "acc_os_info", "'route.files: '", "'files: '")
mut("acc_os_info: the manifest asks sdapi", "acc_os_info", "is_grp_member(user, 'sdfiles')", "is_grp_member(user, 'sdapi')")
mut("acc_os_info: the manifest has no route.files", "acc_os_info", drop_line(r"'route\.files: '"))
mut("acc_os_info: route.files is written for a group account too", "acc_os_info", "      case grp[1,4] = 'sdg_'\n", "      case grp[1,4] = 'sdg_'\n         info<-1> = 'route.files: 0'\n")
mut("restorea: the key route.files is not read", "restorea", "= 'route.files' ; m.route.files = kv", "= 'route.filez' ; m.route.files = kv")
mut("restorea: the key route.files is read into the file count", "restorea", "= 'route.files' ; m.route.files = kv", "= 'route.files' ; m.files = kv")
mut("restorea: it is not handed on", "restorea", "settings<CA$FILES> = m.route.files", "settings<CA$FILES> = m.files")
mut("restorea: it is not cleared for each section", "restorea", " ; m.route.files = ''", "")
mut("restorea: the file count is lost", "restorea", "case sec.keys<s.idx,kp> = 'files'       ; m.files = kv", "case sec.keys<s.idx,kp> = 'filez'       ; m.files = kv")
mut("backupa: the file count is renamed route.files", "bp:backupa", "m<-1> = 'files: ':files", "m<-1> = 'route.files: ':files")
# the group
mut("the installer does not make sdfiles", "installsdcore.sh", "for sd_route_group in sdssh sdapi sdfiles sdfileswrite sdfilesadmin sdaiusers; do", "for sd_route_group in sdssh sdapi sdfileswrite sdfilesadmin sdaiusers; do")
mut("the installer makes sdfiles a login group", "installsdcore.sh", "sudo groupadd --system \"$sd_route_group\"", "sudo groupadd \"$sd_route_group\"")
mut("deletesdcore does not remove sdfiles", "deletesdcore.sh", "for sd_route_group in sdssh sdapi sdfiles sdfileswrite sdfilesadmin sdaiusers; do", "for sd_route_group in sdssh sdapi sdfileswrite sdfilesadmin sdaiusers; do")
mut("deletesdcore says it kept two groups", "deletesdcore.sh", "route groups sdssh, sdapi, sdfiles, sdfileswrite, sdfilesadmin and sdaiusers were kept", "route groups sdssh and sdapi were kept")
mut("deletesdcore removes sdfiles when the accounts are kept", "deletesdcore.sh", "else\n    echo \"sd ACCOUNTS were saved", "else\n    sudo groupdel sdfiles\n    echo \"sd ACCOUNTS were saved")
mut("sd-elevate does not whitelist sdfiles", "sd-elevate", "sdusers|sdssh|sdapi|sdfiles|sdfileswrite|sdfilesadmin|sdaiusers) : ;;", "sdusers|sdssh|sdapi|sdfileswrite|sdfilesadmin|sdaiusers) : ;;")
mut("sd-elevate whitelists sdfiles* (a prefix)", "sd-elevate", "sdusers|sdssh|sdapi|sdfiles|sdfileswrite|sdfilesadmin|sdaiusers) : ;;", "sdusers|sdssh|sdapi|sdfiles*|sdfileswrite|sdfilesadmin|sdaiusers) : ;;")
mut("sd-elevate lets groupdel delete sdfiles", "sd-elevate", "      sdusers|sdssh|sdapi|sdfiles|sdfileswrite|sdfilesadmin|sdaiusers)\n        die", "      sdusers|sdssh|sdapi|sdfileswrite|sdfilesadmin|sdaiusers)\n        die")
mut("sd-elevate's refusal does not name sdfiles", "sd-elevate", "(want sdusers, sdssh, sdapi, sdfiles, sdfileswrite, sdfilesadmin, sdaiusers, sdu_*, or sdg_*)", "(want sdusers, sdssh, sdapi, sdfileswrite, sdfilesadmin, sdaiusers, sdu_*, or sdg_*)")
# the messages
mut("message 11480 is missing", "msg:11480", lambda t: None)
mut("message 11480 says another thing", "msg:11480", lambda t: t.replace("files only", "files and more", 1))
mut("message 11480 loses its place for the request", "msg:11480", lambda t: t.replace("%1", "", 1))
mut("message 11482 is two lines", "msg:11482", lambda t: t.rstrip("\n") + "\nsecond line\n")
mut("message 11482 says NET", "msg:11482", lambda t: t.replace("files", "net", 1))
mut("message 11482 spells its keyword in capitals again (the lower case rule, 19 Oct 26)", "msg:11482", lambda t: t.replace("files", "FILES", 1))
mut("message 11481 is cited by a program", "bp:cd", lambda t: t + "\n   crt sysmsg(11481)\n")
mut("a program cites 11483", "bp:cd", lambda t: t + "\n   crt sysmsg(11483)\n")
mut("a second program cites 11480", "bp:cd", lambda t: t + "\n   crt sysmsg(11480, 1)\n")
mut("another program reads the mark", "bp:cd", lambda t: t + "\n   if files.only then null\n")
mut("the login prints something on success", AP2, "                  files.only = @true\n", "                  files.only = @true\n                  crt 'files only'\n")


# ---- slice 3a: the class logs in from the stored keys ---------------------------------------------------------------------------------------
SCL = "bp:sdclient"
mut("connect.keys: the parameters are by reference", SCL, "public function connect.keys(host, (port), username, (salt), (iterations), (client.key), (server.key), account, (pin))",
    "public function connect.keys(host, (port), username, salt, iterations, client.key, server.key, account, pin)")
mut("connect.keys: the pin comparison is gone", SCL, "if ('p' : spki) # ('p' : pin) then", "if 0 then")
mut("connect.keys: the pin is compared as numbers", SCL, "if ('p' : spki) # ('p' : pin) then", "if spki # pin then")
mut("connect.keys: the hash is not required", SCL, "   if spki = '' then\n      error = 'The server gave no public key hash", "   if 0 then\n      error = 'The server gave no public key hash")
mut("connect.keys: something is sent before the pin is checked", SCL, "   spki = downcase(trim(socket.info(skt, SKT$INFO.TLS.SPKI)))",
    "   void message.pair(SrvrRevision, '')\n   spki = downcase(trim(socket.info(skt, SKT$INFO.TLS.SPKI)))")
mut("connect.keys: the Ack is read before the pin is checked", SCL, "   spki = downcase(trim(socket.info(skt, SKT$INFO.TLS.SPKI)))",
    "   void read.socket(skt, 1, SKT$BLOCKING, 5000)\n   spki = downcase(trim(socket.info(skt, SKT$INFO.TLS.SPKI)))")
mut("connect.keys: the pin is not lowered", SCL, "   pin = downcase(trim(pin))", "   pin = trim(pin)")
mut("connect.keys: the pin's shape is not checked", SCL, "if len(pin) # 64 or len(convert('0123456789abcdef', '', pin)) # 0 then", "if 0 then")
mut("connect.keys: no connect timeout", SCL, "SKT$BLOCKING + SKT$TLS, config('NETWAIT'))", "SKT$BLOCKING + SKT$TLS)")
mut("connect.keys: the socket is opened without TLS", SCL, "SKT$BLOCKING + SKT$TLS, config('NETWAIT'))", "SKT$BLOCKING, config('NETWAIT'))")
mut("connect.keys: the Ack wait is for ever", SCL, "      b = read.socket(skt, 1, SKT$BLOCKING, io.ms)", "      b = read.socket(skt, 1, SKT$BLOCKING, 0)")
mut("connect.keys: the Ack loop has no limit", SCL, "   until acked or tries >= NET.ACK.TRIES", "   until acked")
mut("connect.keys: the read bound is always NETREPLY (settimeout() before it is lost)", SCL, "   if io.ms = 0 then io.ms = config('NETREPLY') * 1000", "   io.ms = config('NETREPLY') * 1000")
mut("connect.keys: the iteration bounds are not checked", SCL, "   if iterations < SCRAM$MIN.ITER or iterations > SCRAM$MAX.ITER then\n      error = 'The stored iteration count is unacceptable'",
    "   if 0 then\n      error = 'The stored iteration count is unacceptable'")
mut("connect.keys: an incomplete login is let through", SCL, "if salt = '' or client.key = '' or server.key = '' then", "if salt = '' then")
mut("connect.keys: a connected object is let through", SCL, "   if context # CX.DISCONNECTED then\n      error = 'A connection has already been established'", "   if 0 then\n      error = 'A connection has already been established'")
mut("connect.keys: the keys are not dropped after the exchange", SCL, "   client.key = ''\n   server.key = ''\n   if not(ok) then", "   if not(ok) then")
mut("connect.keys: keys.fail leaves the socket open", SCL, "keys.fail:\n   client.key = ''\n   server.key = ''\n   close.socket skt", "keys.fail:\n   client.key = ''\n   server.key = ''")
mut("connect.keys: keys.fail does not drop the keys", SCL, "keys.fail:\n   client.key = ''\n   server.key = ''\n   close.socket skt", "keys.fail:\n   close.socket skt")
mut("connect.keys: a refused account is let through", SCL, "   if server.error # SV$OK then\n      error = 'The server did not enter the account'", "   if 0 then\n      error = 'The server did not enter the account'")
mut("connect.keys: a failed account is not a failure", SCL, "   if not(message.pair(SrvrAccount, account)) then\n      if error = '' then error = 'No reply from ' : host : ':' : port : ' when entering the account'\n      goto keys.fail\n   end",
    "   void message.pair(SrvrAccount, account)")
mut("connect.keys: a failure returns without keys.fail", SCL, "         error = 'No acknowledgement from ' : host : ':' : port : ' at the start of the session'\n         goto keys.fail\n      end\n      if b = char(6)",
    "         error = 'No acknowledgement from ' : host : ':' : port : ' at the start of the session'\n         return @false\n      end\n      if b = char(6)")
mut("connect.keys: a text names the ClientKey", SCL, "error = 'Server signature did not verify'", "error = 'Server signature did not verify ' : expect.v")
mut("connect.keys: it displays the pin", SCL, "   pin = downcase(trim(pin))", "   pin = downcase(trim(pin))\n   display pin")
mut("scram.exchange: the salt is not compared", SCL, "if ('s' : salt) # ('s' : stored.salt) then", "if 0 then")
mut("scram.exchange: the salt is compared as numbers", SCL, "if ('s' : salt) # ('s' : stored.salt) then", "if salt # stored.salt then")
mut("scram.exchange: the count is not compared", SCL, "if iter + 0 # stored.iter + 0 then", "if 0 then")
mut("scram.exchange: the stored mode is never taken", SCL, "   if keys.mode then", "   if 0 then")
mut("scram.exchange: the stored mode is taken for a password", SCL, "   keys.mode = (stored.ck # '')", "   keys.mode = @true")
mut("scram.exchange: a refused salt keeps the stored keys", SCL, "error = \"The server's salt is not the stored one: the stored login is out of date or this is not the server it was made with\"\n         stored.ck = '' ; stored.sk = ''",
    "error = \"The server's salt is not the stored one: the stored login is out of date or this is not the server it was made with\"")
mut("scram.exchange: the compare comes after the nonce check no more (before client-first)", SCL, "   if not(message.pair(SrvrScramFirst, 'p=tls-exporter,,' : cfirst.bare)) then return @false",
    "   if keys.mode and ('s' : stored.salt) # ('s' : '') then return @false\n   if not(message.pair(SrvrScramFirst, 'p=tls-exporter,,' : cfirst.bare)) then return @false")
mut("scram.exchange: the working keys are not dropped", SCL, "   client.key = ''\n   srvr.key = ''\n   stored.key = ''\n   client.sig = ''", "   client.key = ''\n   srvr.key = ''\n   client.sig = ''")
mut("scram.exchange: the server signature is compared with =", SCL, "SDEXT(in.pkt[3,999999] : @FM : expect.v, @TRUE, SD_CTEQUAL) # '1'", "in.pkt[3,999999] # expect.v")
mut("scram.exchange: the server's signature is not required", SCL, "   if in.pkt[1,2] # 'v=' then", "   if 0 then")
mut("scram.login is not a wrapper", SCL, "   return scram.exchange(username, password, '', '', '', '')\nend", "   return scram.exchange(username, password, '', '', '', '') and @true\nend")
mut("connect() calls connect.keys", SCL, "   if not(scram.login(username, password)) then", "   if not(obj->connect.keys(host, port, username, '', 4096, '', '', account, '')) then")
mut("connect() waits with a bound", SCL, "      until read.socket(skt, 1, SKT$BLOCKING, 0) = char(6)", "      until read.socket(skt, 1, SKT$BLOCKING, io.ms) = char(6)")
mut("connect() opens with a timeout", SCL, "   skt = open.socket(host, port, SKT$BLOCKING + SKT$TLS)\n   if status() then", "   skt = open.socket(host, port, SKT$BLOCKING + SKT$TLS, 5)\n   if status() then")
mut("connect() asks a pin", SCL, "   if not(scram.login(username, password)) then", "   if socket.info(skt, SKT$INFO.TLS.SPKI) = '' then return @false\n   if not(scram.login(username, password)) then")
mut("read.packet's header read waits for ever", SCL, "      s = read.socket(skt, n, SKT$BLOCKING, io.ms)\n      if status() then return @false\n      pkt.header := s",
    "      s = read.socket(skt, n, SKT$BLOCKING, 0)\n      if status() then return @false\n      pkt.header := s")
mut("read.packet's data read waits for ever", SCL, "      s = read.socket(skt, n, SKT$BLOCKING, io.ms)\n      if status() then return @false\n      if debugging then",
    "      s = read.socket(skt, n, SKT$BLOCKING, 0)\n      if status() then return @false\n      if debugging then")
mut("create.object does not start io.ms", SCL, rx(r"(public subroutine create\.object\n(?:[^\n]*\n){0,6}?)   io\.ms = 0\n", r"\1"))
mut("settimeout takes a negative", SCL, "if not(num(ms)) or ms < 0 then abort 'Illegal timeout'", "if not(num(ms)) then abort 'Illegal timeout'")
mut("settimeout does not set the bound", SCL, "   io.ms = ms + 0\nend", "   null\nend")
mut("connect.keys waits 50 seconds whatever NETWAIT says", SCL, "SKT$BLOCKING + SKT$TLS, config('NETWAIT'))", "SKT$BLOCKING + SKT$TLS, 50)")
mut("connect.keys reads with no bound whatever NETREPLY says", SCL, "   if io.ms = 0 then io.ms = config('NETREPLY') * 1000", "   if io.ms = 0 then io.ms = 0")
mut("connect.keys reads NETWAIT where it should read NETREPLY", SCL, "   if io.ms = 0 then io.ms = config('NETREPLY') * 1000", "   if io.ms = 0 then io.ms = config('NETWAIT') * 1000")
mut("sdclient brings back the define of the connect timeout", SCL, "$define NET.ACK.TRIES    16", "$define NET.CONNECT.SECS  5\n$define NET.ACK.TRIES    16")
mut("NET.ACK.TRIES is 1", SCL, "$define NET.ACK.TRIES    16", "$define NET.ACK.TRIES     1")
mut("the class text for a pin mismatch changes", SCL, "'PIN MISMATCH: the public key of '", "'PIN MISSMATCH: the public key of '")
mut("the class text for a stale salt changes", SCL, "The server's salt is not the stored one: the stored login", "The server salt is not the stored one: the stored login")
mut("sdclient's history line is gone", SCL, "* 17 Oct 26 dm S.65 slice 3a: connect.keys()", "* 17 Oct 26 dm slice 3a: connect.keys()")
mut("sdclient's description does not list connect.keys", SCL, "* bool = obj->connect.keys(host, port, username, salt, iterations, client.key, server.key, account, pin)\n", "")
mut("regress.sh does not list netfile", "regress.sh", ' editgates net netfile ', ' editgates net ')
mut("regress.sh lists netfile twice", "regress.sh", ' editgates net netfile ', ' editgates net netfile netfile ')
mut("the map does not select netfile for sdclient", "regress-map.txt", "sdsys/gpl.bp/sdclient        : qmclient netfile net", "sdsys/gpl.bp/sdclient        : qmclient net")
mut("the map does not select netfile for netcred", "regress-map.txt", "sdsys/gpl.bp/netcred         : net netfile", "sdsys/gpl.bp/netcred         : net")
mut("the map does not select netfile for setnetlogin", "regress-map.txt", "sdsys/gpl.bp/setnetlogin     : net netfile", "sdsys/gpl.bp/setnetlogin     : net")
mut("the map does not select netfile for netdefs", "regress-map.txt", "sdsys/gpl.bp/netdefs         : net netfile", "sdsys/gpl.bp/netdefs         : net")
mut("the map does not select netfile for netfake.py", "regress-map.txt", "gplbld/netfake.py            : net netfile", "gplbld/netfake.py            : net")
mut("the map has no rule for the suite file", "regress-map.txt", "gplbld/sandbox-netfile.py    : @self\n", "")
mut("the suite's verdict line changes", "sandbox-netfile.py", 'say("sandbox-netfile: %d passed, %d failed" % (passed, failed))', 'say("sandbox-netfile: %d ok, %d failed" % (passed, failed))')
mut("the suite has no --build", "sandbox-netfile.py", '"--build" in sys.argv', '"--make" in sys.argv')
mut("the suite expects another text for the stale count", "sandbox-netfile.py", 'iter_err = "The server\'s iteration count is not the stored one: the stored login is out of date or this is not the server it was made with"',
    'iter_err = "The server\'s count is not the stored one"')
mut("the suite's history line is gone", "sandbox-netfile.py", "# 17 Oct 26 dm  New.  S.65 slice 3a.", "# 17 Oct 26 dm  New.")


# ---- slice 3b: the remote file handler ------------------------------------------------------------------------------------------------------
NFP, NFHD, NFSUITE, NFMAP = "bp:netfile", "bp:netfile.h", "sandbox-netfile.py", "regress-map.txt"
mut("netfile.h: NF$LOCK is 11 (the same as CLEARFILE)", NFHD, rx(r"(\$define\s+NF\$LOCK\s+)12", r"\g<1>11"))
mut("netfile.h: NF$WRITE is 14", NFHD, rx(r"(\$define\s+NF\$WRITE\s+)9", r"\g<1>14"))
mut("netfile.h: NF$MAX.SERVERS is 11", NFHD, rx(r"(\$define\s+NF\$MAX\.SERVERS\s+)10", r"\g<1>11"))
mut("netfile.h: NF$MAX.HANDLES is 101", NFHD, rx(r"(\$define\s+NF\$MAX\.HANDLES\s+)100", r"\g<1>101"))
mut("netfile.h: NF$RC.ERROR is 4", NFHD, rx(r"(\$define\s+NF\$RC\.ERROR\s+)3", r"\g<1>4"))
mut("netfile.h: NF$STATE is gone", NFHD, drop_line(r"\$define NF\$STATE\b"))
mut("netfile is not internal", NFP, "$internal\nsubroutine netfile(", "subroutine netfile(")
mut("netfile is catalogued under another name", NFP, "$catalog $netfile\n", "$catalog $netfiles\n")
mut("NF$OPEN does not ask the gate", NFP, "*  (1) THE GATE\n   gosub check.gate\n   if not(gate.ok) then", "*  (1) THE GATE\n   gate.ok = @true\n   if not(gate.ok) then")
mut("NF$OPEN asks the gate after the definition is read", NFP,
    lambda t: t.replace("   gosub check.gate\n   if not(gate.ok) then", "   gate.ok = @true\n   if not(gate.ok) then", 1).replace("   call !netdefs('READ', defs, err)\n", "   call !netdefs('READ', defs, err)\n   gosub check.gate\n", 1))
mut("the accounts list is not asked", NFP, "if index(',':downcase(accts):',', ',':acc:',', 1) = 0 then", "if 0 then")
mut("the administrator is not exempt from the list", NFP, "   if not(is.admin) then\n      if index(", "   if 1 then\n      if index(")
mut("the accounts list is compared case sensitively", NFP, "index(',':downcase(accts):',', ',':acc:',', 1)", "index(',':accts:',', ',':acc:',', 1)")
mut("the stored login is not read", NFP, "call $netcred('READ', srv, cred, pin, err)", "cred = ''")
mut("the stored login is written", NFP, "call $netcred('READ', srv, cred, pin, err)", "call $netcred('WRITE', srv, cred, pin, err)")
mut("the definitions are rewritten", NFP, "call !netdefs('READ', defs, err)", "call !netdefs('WRITE', defs, err)")
mut("the file name is not checked", NFP, "   if not(fname.ok) then\n      cred = ''", "   if 0 then\n      cred = ''")
mut("the limit on servers is not asked", NFP, "if slot = 0 and ns >= NF$MAX.SERVERS then", "if 0 then")
mut("the limit on files is not asked", NFP, "   if nh >= NF$MAX.HANDLES then\n      cred = ''", "   if 0 then\n      cred = ''")
mut("the connection is made before the file name is checked", NFP, "*  (7) THE REMOTE FILE NAME\n", "   gosub connect.new\n*  (7) THE REMOTE FILE NAME\n")
mut("the open is audited after the connection is made", NFP,
    lambda t: t.replace("   void kernel(K$AUDIT, 'netfile open server=' : srv : ' file=' : fname)\n\n   created = @false", "   created = @false", 1)
    .replace("   fno = obj->open(fname)\n", "   void kernel(K$AUDIT, 'netfile open server=' : srv : ' file=' : fname)\n   fno = obj->open(fname)\n", 1))
mut("a refusal is not audited", NFP, "   void kernel(K$AUDIT, 'netfile refused server=' : safe : ' reason=' : refused.why)\n", "")
mut("the open audit line names the pin", NFP, "      void kernel(K$AUDIT, 'netfile open server=' : srv : ' file=' : fname)\n", "      void kernel(K$AUDIT, 'netfile open server=' : srv : ' file=' : fname : ' pin=' : pin)\n")
mut("the open audit line is in capitals", NFP, "'netfile open server='", "'NETFILE OPEN server='")
mut("a refusal reason outside the six", NFP, "refused.why = 'credential' ; gosub refuse", "refused.why = 'secret' ; gosub refuse")
mut("a refusal falls through without a return", NFP, "refused.why = 'list' ; gosub refuse\n         return\n", "refused.why = 'list' ; gosub refuse\n")
mut("the audit names the server as typed", NFP, "   if name.ok then safe = srv\n", "   safe = srv\n")
mut("the password login is used", NFP, "obj->connect.keys(host, port, ruser, rsalt, riter, rck, rsk, racct, pin)", "obj->connect(host, port, ruser, rck, racct)")
mut("the copies of the keys are not cleared", NFP, "   ruser = ''\n   rsalt = ''\n   riter = ''\n   rck = ''\n   rsk = ''\n   if not(ok) then", "   if not(ok) then")
mut("the credential is not cleared before the object is made", NFP, "   cred = ''\n   obj = object('!sdclient')", "   obj = object('!sdclient')")
mut("a second place makes an object", NFP, lambda t: t + "\n   obj2 = object('!sdclient')\n")
mut("the request bound is not given to the object", NFP, "   obj->settimeout(req.ms)\n", "")
mut("the request bound is 0", NFP, "   req.ms = config('NETREPLY') * 1000\n", "   req.ms = 0\n")
mut("the request bound is read from NETWAIT", NFP, "   req.ms = config('NETREPLY') * 1000\n", "   req.ms = config('NETWAIT') * 1000\n")
mut("the request bound is in seconds, not milliseconds", NFP, "   req.ms = config('NETREPLY') * 1000\n", "   req.ms = config('NETREPLY')\n")
mut("the CLEARFILE bound may be shorter than the request bound", NFP, "   if req.ms > clear.ms then clear.ms = req.ms\n", "")
mut("the request bound is not read before the object gets it", NFP, "   gosub request.limits\n   obj->settimeout(req.ms)\n", "   obj->settimeout(req.ms)\n")
mut("a refused operation calls a write method", NFP, "   fail.num = 11501 ; fail.a1 = srvname ; fail.a2 = opname\n",
    "   obj = nf.s.obj(nf.h.slot(hx))\n   obj->write(nf.h.fno(hx), b, c)\n   fail.num = 11501 ; fail.a1 = srvname ; fail.a2 = opname\n")
mut("LOCK is no longer dispatched to act.change", NFP, "op = NF$DELETEU or op = NF$CLEARFILE or op = NF$LOCK or op = NF$FILELOCK\n         gosub act.change", "op = NF$DELETEU or op = NF$CLEARFILE or op = NF$FILELOCK\n         gosub act.change")
mut("a read takes a lock", NFP, "rec = obj->read(nf.h.fno(hx), id, e)", "rec = obj->readu(nf.h.fno(hx), id, 0, e)")
mut("the handler executes a command on the server", NFP, lambda t: t + "\n   obj->execute('x', e)\n")
mut("the handler writes a file", NFP, lambda t: t + "\n   writeseq 'x' to f else null\n")
mut("the handler shows the credential", NFP, lambda t: t + "\n   crt cred\n")
mut("the refusal message is another number", NFP, "fail.num = 11501", "fail.num = 11500")
mut("the gate is asked with a set", NFP, "kernel(K$NET, -1)", "kernel(K$NET, 1)")
mut("a second place asks the gate", NFP, lambda t: t + "\n   if kernel(K$NET, -1) then null\n")
mut("get.handle does not ask the gate", NFP, "   if need.gate then\n      gosub check.gate", "   if 0 then\n      gosub check.gate")
mut("read does not ask the gate again", NFP, "act.read:\n   need.gate = @true", "act.read:\n   need.gate = @false")
mut("select does not ask the gate again", NFP, "act.select:\n   need.gate = @true", "act.select:\n   need.gate = @false")
mut("a handle is not tied to its account", NFP, "      if nf.h.acct(hx) # acc then", "      if 0 then")
mut("the account is not stored with the handle", NFP, "   nf.h.acct(hx) = acc\n", "   nf.h.acct(hx) = ''\n")
mut("the account is the log name", NFP, "   acc = downcase(@who)", "   acc = downcase(@logname)")
mut("a request is sent without the no-reply mark", NFP, "   obj->ServerStatus = NF$NOREPLY\n   e = ''\n   rec = obj->read(", "   e = ''\n   rec = obj->read(")
mut("a lost connection is not noticed", NFP, "   rq.lost = (st = NF$NOREPLY)", "   rq.lost = (st = 0)")
mut("the no-reply mark is 0", NFP, "$define NF$NOREPLY    -2000000001", "$define NF$NOREPLY    0")
mut("a lost connection is reconnected", NFP, "   gosub drop.conn\n   if changing then", "   gosub drop.conn\n   gosub connect.new\n   if changing then")
mut("a lost connection is retried in a loop", NFP, "   gosub drop.conn\n   if changing then", "   gosub drop.conn\n   loop\n   until 1 do\n   repeat\n   if changing then")
mut("a lost handle is let through", NFP, "      if allow.lost then return\n", "")
mut("CLOSE of a lost handle is refused", NFP, "need.gate = @false ; need.conn = @false ; any.acct = @true ; allow.lost = @true", "need.gate = @false ; need.conn = @false ; any.acct = @true ; allow.lost = @false")
mut("CLOSEALL asks the gate", NFP, "act.closeall:\n   for sx = 1", "act.closeall:\n   gosub check.gate\n   for sx = 1")
mut("a dropped connection does not mark its handles lost", NFP, "                  nf.h.state(hy) = 2\n", "                  nf.h.state(hy) = 0\n")
mut("the common block holds a key", NFP, "common /$netfile/ nf.opens,", "common /$netfile/ nf.s.key(NF$MAX.SERVERS), nf.opens,")
mut("a second common block", NFP, "   out = ''\n   rc = ''\n   rc<1> = NF$RC.OK", "   common /$other/ zz.x\n   out = ''\n   rc = ''\n   rc<1> = NF$RC.OK")
mut("a message carries the pin", NFP, "fail.num = 11492 ; fail.a1 = srv ; fail.a2 = bad.field", "fail.num = 11492 ; fail.a1 = srv ; fail.a2 = pin")
mut("a slash is a character of a remote file name", NFP, "chk.set = lc.set:digits:'._-$'", "chk.set = lc.set:digits:'._-$/'")
mut("a server name may be 17 characters", NFP, "len(srv) <= 16", "len(srv) <= 17")
mut("message 11497 is missing", "msg:11497", lambda t: None)
mut("message 11501 has two lines", "msg:11501", lambda t: t.rstrip("\n") + "\nsecond line\n")
mut("message 11500 has a fourth place", "msg:11500", lambda t: t.rstrip("\n") + " %4\n")
mut("message 11509 exists", "msg:11509", lambda t: "x\n")
mut("message 11507 (the kernel's) is gone", "msg:11507", lambda t: None)
mut("message 11508 (the kernel's) has two lines", "msg:11508", lambda t: t.rstrip("\n") + "\nsecond line\n")
mut("a message of the block is not used", NFP, "fail.num = 11506 ;", "fail.num = 11507 ;")
mut("another program cites 11502", "bp:cd", lambda t: t + "\n   crt sysmsg(11502)\n")
mut("the map loses the handler rule", NFMAP, "sdsys/gpl.bp/netfile         : netfile\n", "")
mut("the map loses the header rule", NFMAP, "sdsys/gpl.bp/netfile.h       : netfile\n", "")
mut("the map loses a message rule", NFMAP, "sdsys/messages/1150*         : netfile\n", "")
# 19 Oct 26 (integration): made by a function.  The masters lane's four rules for 11560-11596 now stand between the 1151 rule and the none rule, so the
# old text "1151 rule, newline, none rule" is not there; the mutant moves the 1151 rule to after the none rule whatever stands between them.
mut("the map's 1151 message rule comes after the none rule", NFMAP,
    lambda t: t.replace("sdsys/messages/1151*         : netfile shared\n", "", 1).replace("sdsys/messages/*             : none\n", "sdsys/messages/*             : none\nsdsys/messages/1151*         : netfile shared\n", 1))
mut("the map's header rule comes after the *.h rule", NFMAP,
    lambda t: t.replace("sdsys/gpl.bp/netfile.h       : netfile\n", "", 1).replace("sdsys/gpl.bp/*.h             : @compiler @core\n", "sdsys/gpl.bp/*.h             : @compiler @core\nsdsys/gpl.bp/netfile.h       : netfile\n", 1))
mut("the suite loses a section", NFSUITE, '("lost", lost_section), ', "")
mut("the suite runs gaps by default", NFSUITE, 'OPT_IN = ("gaps",)', "OPT_IN = ()")
mut("the suite's driver loses CLEARFILE", NFSUITE, "            op = NF$CLEARFILE\n", "            op = 11\n")
mut("the suite expects a message that is not there", NFSUITE, "k_err(11501, ", "k_err(11599, ")
mut("the suite does not compile netfile", NFSUITE, "BASIC gpl.bp netcred netfile zznfh zznfhx", "BASIC gpl.bp netcred zznfh zznfhx")
mut("netfile's history line is gone", NFP, "* 17 Oct 26 dm  S.65 slice 3b: written.", "* 17 Oct 26 dm  written.")
mut("netfile.h's history line is gone", NFHD, "* 17 Oct 26 dm  S.65 slice 3b: written.", "* 17 Oct 26 dm  written.")
mut("the suite's history line is gone", NFSUITE, "# 17 Oct 26 dm  S.65 slice 3b:", "# 17 Oct 26 dm  slice 3b:")


# ---- slice 3c: the kernel half ----------------------------------------------------------------------------------------------------------------
M3C = len(M)        # the mutants from here on are slice 3c's
NFC = "netfiles.c"
mut("NET_FILE is 5", "descr.h", rx(r"(#define\s+NET_FILE\s+)4", r"\g<1>5"))
mut("NET_FILE shares 3 with SEQ_FILE", "descr.h", rx(r"(#define\s+NET_FILE\s+)4", r"\g<1>3"))
mut("a second type is 4", "descr.h", rx(r"(#define\s+SEQ_FILE\s+)3", r"\g<1>4"))
mut("the union member loses a zero word", "descr.h", "void* zero[2];", "void* zero[1];")
mut("the union member loses the epoch", "descr.h", "      u_int16_t epoch;\n", "")
mut("the server name is not NET_SERVER_LEN long", "descr.h", "char server[NET_SERVER_LEN + 1];", "char server[16];")
mut("NET_MAX_HANDLES is 101", "descr.h", rx(r"(#define\s+NET_MAX_HANDLES\s+)100", r"\g<1>101"))
mut("NET_SERVER_LEN is 17", "descr.h", rx(r"(#define\s+NET_SERVER_LEN\s+)16", r"\g<1>17"))
mut("NET_FILE_MAX is 64", NFC, rx(r"(#define\s+NET_FILE_MAX\s+)63", r"\g<1>64"))
mut("NF_READ is not netfile.h's", NFC, rx(r"(#define\s+NF_READ\s+)3", r"\g<1>4"))
mut("NF_CLOSEALL is not netfile.h's", NFC, rx(r"(#define\s+NF_CLOSEALL\s+)8", r"\g<1>9"))
mut("NF_RC_ELSE is 1", NFC, rx(r"(#define\s+NF_RC_ELSE\s+)2", r"\g<1>1"))
mut("a prototype in sd.h changes a type", "sd.h", "int net_read(FILE_VAR * fvar, char * id, int16_t id_len, STRING_CHUNK ** rec);", "int net_read(FILE_VAR * fvar, char * id, int32_t id_len, STRING_CHUNK ** rec);")
mut("a prototype in sd.h loses a function", "sd.h", "const char * net_message(void);\n", "")
mut("op_dio3.c declares net_refuse with another type", "op_dio3.c", "int net_refuse(FILE_VAR *fvar, const char *what);", "void net_refuse(FILE_VAR *fvar, const char *what);")
mut("op_dio2.c declares net_fileinfo with another type", "op_dio2.c", "STRING_CHUNK* net_fileinfo(FILE_VAR* fvar, int key);", "STRING_CHUNK* net_fileinfo(FILE_VAR* fvar, long key);")
mut("a netfiles function is defined twice", NFC, lambda t: t + "\nconst char* net_message() {\n  return \"\";\n}\n")
mut("the gate is not asked", NFC, "  if (!net_gate_ok()) {", "  if (0) {")
mut("the queue is flushed before the gate", NFC, "  /* THE GATE, before anything is loaded or called.  An $internal program is not exempt. */\n  if (!net_gate_ok()) {",
    "  net_flush_pending();\n  if (!net_gate_ok()) {")
mut("the gate exempts an $internal program", NFC, "return MY_ADMIN() ||", "return (process.program.flags & HDR_INTERNAL) || MY_ADMIN() ||")
mut("the gate is the administrator's alone", NFC, " || MY_GATE(UG_NET);", ";")
mut("the gate refusal is not audited", NFC, "    audit_message(audit);\n    return -ER_PERM;", "    return -ER_PERM;")
mut("the gate refusal falls through", NFC, "    audit_message(audit);\n    return -ER_PERM;", "    audit_message(audit);")
mut("the gate audit line is in capitals", NFC, "\"netfile refused server=%s reason=gate\"", "\"NETFILE REFUSED server=%s reason=gate\"")
mut("the server name is audited as typed", NFC, "(((server[i] >= 'a') && (server[i] <= 'z')) || ((server[i] >= '0') && (server[i] <= '9'))) ? server[i] : '?'", "server[i]")
mut("the gate message is 11461", NFC, "#define MSG_NO_GATE 11460", "#define MSG_NO_GATE 11461")
mut("the pointer's first byte is not tested", NFC, "((u_char)encoded_path[0] != 1) || ", "")
mut("a pointer with no file name is not refused", NFC, "  q = strchr(p, 1);\n  if (q == NULL) {", "  q = strchr(p, 1);\n  if (0) {")
mut("a file name may be 64 characters too long", NFC, "(n > NET_FILE_NAME_MAX) || (strchr(p, 1) != NULL)", "(n > NET_FILE_NAME_MAX + 1) || (strchr(p, 1) != NULL)")
mut("the file name test is NET_FILE_MAX again (a dictionary name is refused)", NFC, "(n > NET_FILE_NAME_MAX) || (strchr(p, 1) != NULL)", "(n > NET_FILE_MAX) || (strchr(p, 1) != NULL)")
mut("the file name buffer is too small for 'dict '", NFC, "char file[NET_FILE_NAME_MAX + 1];", "char file[NET_FILE_MAX + 1];")
mut("NET_FILE_NAME_MAX is NET_FILE_MAX + 4", NFC, "#define NET_FILE_NAME_MAX (NET_FILE_MAX + 5)", "#define NET_FILE_NAME_MAX (NET_FILE_MAX + 4)")
mut("the handler is called by another name", NFC, "k_call(\"$netfile\", 6, NULL, 0);", "k_call(\"netfile\", 6, NULL, 0);")
mut("the handler is not looked for first", NFC, "if (load_object(\"$netfile\", FALSE) == NULL) {", "if (0) {")
mut("the handler is not marked as a trigger", NFC, "  process.program.flags |= PF_IS_TRIGGER;\n", "")
mut("the handler's reference count is not given back", NFC, "if (returned && (--(hdr->ext_hdr.prog.refs) == 0) && (hdr->id < 0))", "if (returned && ((hdr->ext_hdr.prog.refs) == 0) && (hdr->id < 0))")
mut("the handler is called with five arguments", NFC, "k_call(\"$netfile\", 6, NULL, 0);", "k_call(\"$netfile\", 5, NULL, 0);")
mut("net_refuse flushes the queue (runs BASIC)", NFC, "  net_set_message(msg_no, server, op, \"\");", "  net_flush_pending();\n  net_set_message(msg_no, server, op, \"\");")
mut("net_refuse does not lower case the statement", NFC, "op[i] = ((what[i] >= 'A') && (what[i] <= 'Z')) ? (char)(what[i] - 'A' + 'a') : what[i];", "op[i] = what[i];")
mut("net_refuse returns 0", NFC, edit_func("net_refuse_with", r"  return net_raise\(status, entry\);", "  return 0;"))
mut("net_refuse reads the server of any variable", NFC, "  if ((fvar != NULL) && (fvar->type == NET_FILE))\n    server = fvar->access.net.server;", "  server = fvar->access.net.server;")
mut("the refusal message is another number", NFC, "#define MSG_READ_ONLY 11501", "#define MSG_READ_ONLY 11500")
mut("net_close talks to the server for every release", NFC, "  if (explicit_close) {\n    explicit_close = FALSE;", "  if (1) {\n    explicit_close = FALSE;")
mut("net_close does not clear the handle first", NFC, "  fvar->access.net.handle = 0;\n\n", "\n")
mut("net_close sends a stale variable", NFC, "  if (net_stale(fvar))\n    return;\n  fvar->access.net.handle = 0;", "  fvar->access.net.handle = 0;")
mut("net_close queues nothing", NFC, "    net_pending[net_pending_ct++] = handle;", "    ;")
mut("a stale variable ignores the epoch", NFC, " || (fvar->access.net.epoch != net_epoch);", ";")
mut("a stale variable ignores its type", NFC, "return (fvar->type != NET_FILE) || (fvar->access.net.handle <= 0)", "return (fvar->access.net.handle <= 0)")
mut("net_close_all does not move the epoch", NFC, "  net_epoch++;\n", "")
mut("net_close_all calls the handler even when nothing was opened", NFC, "  if (!net_used)\n    return;\n", "")
mut("net_close_all keeps the queue", NFC, "  net_pending_ct = 0;\n  net_cache_drop(0);", "  net_cache_drop(0);")
mut("net_op flushes before it asks whether the handle is stale", NFC,
    lambda t: t.replace("  net_flush_pending();\n  ran = net_call_core(op, hs,", "  ran = net_call_core(op, hs,", 1)
    .replace("  if (net_stale(fvar)) {\n    snprintf(hs, sizeof(hs), \"%d\", (int)fvar->access.net.handle);\n    net_set_message(MSG_BAD_HANDLE", "  net_flush_pending();\n  if (net_stale(fvar)) {\n    snprintf(hs, sizeof(hs), \"%d\", (int)fvar->access.net.handle);\n    net_set_message(MSG_BAD_HANDLE", 1))
mut("the type is set before the handler has answered", NFC, lambda t: t.replace("  fvar->type = NET_FILE;\n  net_used = TRUE;", "  net_used = TRUE;", 1).replace("  net_flush_pending();\n  ran = net_call_raw(NF_OPEN", "  fvar->type = NET_FILE;\n  net_flush_pending();\n  ran = net_call_raw(NF_OPEN", 1))
mut("a read-mode NET_FILE may be written", NFC, "  if (!fvar->access.net.write)\n    fvar->flags |= FV_RDONLY;\n", "")
mut("a NET_FILE may be in a transaction", NFC, "  fvar->flags |= FV_NON_TXN;\n", "")
mut("a NET_FILE has a file table entry", NFC, "  fvar->file_id = -1;\n  fvar->flags", "  fvar->file_id = 0;\n  fvar->flags")
mut("the union is not zeroed", NFC, "  memset(&fvar->access, 0, sizeof(fvar->access));\n", "")
mut("a handle may be \"3x\"", NFC, "if ((hs[i] < '0') || (hs[i] > '9'))", "if (0)")
mut("a handle may be 101", NFC, "(handle < 1) || (handle > NET_MAX_HANDLES)", "(handle < 1) || (handle > NET_MAX_HANDLES + 1)")
mut("net_read asks the handler for an empty id", NFC, "  if (id_len < 1)\n    return ER_IID; /* an empty or over-long id", "  if (0)\n    return ER_IID; /* an empty or over-long id")
mut("the accounts list is not the permission class", NFC, "    case MSG_NOT_LISTED:\n", "")
mut("the ELSE branch ignores the server's status", NFC, "return (rc->status > 0) ? rc->status : else_status;", "return else_status;")
mut("every error is ER_PERM", NFC, "  return -ER_NETWORK;\n}\n\n/* ======================================================================\n   net_answer()", "  return -ER_PERM;\n}\n\n/* ======================================================================\n   net_answer()")
# _voc_ref
VR = "bp:_voc_ref"
mut("_voc_ref: a dictionary of a NET file is refused again", VR, "            n.srv = downcase(trim(voc.rec<2>))", "            if fno = 3 then\n               set.status ER$VNF\n               return\n            end\n            n.srv = downcase(trim(voc.rec<2>))")
mut("_voc_ref: a dictionary of a NET file is not given 'dict '", VR, "            if fno = 3 then n.file = 'dict ':n.file", "            if fno = 3 then n.file = n.file")
mut("_voc_ref: every NET file is given 'dict '", VR, "            if fno = 3 then n.file = 'dict ':n.file", "            n.file = 'dict ':n.file")
mut("_voc_ref: the data part is given 'dict ' (fno 2)", VR, "            if fno = 3 then n.file = 'dict ':n.file", "            if fno = 2 then n.file = 'dict ':n.file")
mut("_voc_ref: the prefix has no space", VR, "            if fno = 3 then n.file = 'dict ':n.file", "            if fno = 3 then n.file = 'dict':n.file")
mut("_voc_ref: 'dict ' is added BEFORE the shape test", VR, "            n.file = downcase(trim(voc.rec<3>))\n            gosub check.n.pointer", "            n.file = downcase(trim(voc.rec<3>))\n            if fno = 3 then n.file = 'dict ':n.file\n            gosub check.n.pointer")
mut("_voc_ref: the shape test allows a space (a VOC entry may hold the prefix)", VR, "'._-$'", "'._-$ '")
mut("_voc_ref: the server name is not lower cased", VR, "n.srv = downcase(trim(voc.rec<2>))", "n.srv = trim(voc.rec<2>)")
mut("_voc_ref: the file name is not trimmed", VR, "n.file = downcase(trim(voc.rec<3>))", "n.file = downcase(voc.rec<3>)")
mut("_voc_ref: the pathname has no separator", VR, "pathname = char(1):'N':char(1):n.srv:char(1):n.file", "pathname = char(1):'N':char(1):n.srv:'/':n.file")
mut("_voc_ref: the pointer is not shape tested", VR, "            gosub check.n.pointer\n            if not(n.ok) then", "            n.ok = @true\n            if not(n.ok) then")
mut("_voc_ref: a bad pointer is ER$VNF", VR, "            if not(n.ok) then\n               set.status ER$NAM", "            if not(n.ok) then\n               set.status ER$VNF")
mut("_voc_ref: the N case asks the gate", VR, "            n.srv = downcase(trim(voc.rec<2>))", "            n.gate = kernel(K$NET, -1)\n            n.srv = downcase(trim(voc.rec<2>))")
mut("_voc_ref: a server name may be 17 characters", VR, "len(n.srv) > 16", "len(n.srv) > 17")
mut("_voc_ref: a file name may be 64 characters", VR, "len(n.file) > 63", "len(n.file) > 64")
mut("_voc_ref: a server name may start with a digit", VR, "if index(n.letters, n.srv[1,1], 1) = 0 then n.ok = @false", "if 0 then n.ok = @false")
mut("_voc_ref: a file name may hold a slash", VR, "'._-$'", "'._-$/'")
mut("_voc_ref: the pointer checks are not all", VR, "   n.ok = @true\n   n.letters", "   n.ok = @true\n   n.ok = @true\n   n.letters")
mut("_voc_ref: the N case comes after the default", VR, lambda t: t.replace('         case type = "N"', '         case type = "NN"', 1))
# open_file, OPENPATH, dio_close
mut("open_file does not look for the encoded path", "op_dio1.c", "if (net_path_is_net(mapped_name)) {", "if (0 && net_path_is_net(mapped_name)) {")
mut("OPENPATH looks for the encoded path", "op_dio1.c", "  open_file(FALSE);", "  open_file(TRUE);")
mut("a second place opens a NET file", "op_dio2.c", lambda t: t + "\nvoid zz_open(FILE_VAR* v) {\n  net_open(v, \"\");\n}\n")
mut("a failed net_open shows the generic message", "op_dio1.c", "    if (net_failed)\n      k_error(\"%s\", net_message());", "    if (0)\n      k_error(\"%s\", net_message());")
mut("a failed net_open is not an error", "op_dio1.c", "      net_failed = (net_status < 0);", "      net_failed = FALSE;")
mut("dio_close does more for a NET_FILE", "op_dio1.c", "      net_close(fvar);\n      break;", "      net_close(fvar);\n      fvar->file_id = -1;\n      break;")
mut("dio_close has no NET_FILE arm", "op_dio1.c", "    case NET_FILE:\n      /* 17 Oct 26 S.65 slice 3c: file_id is -1, so nothing above ran.", "    case 77:\n      /* 17 Oct 26 S.65 slice 3c: file_id is -1, so nothing above ran.")
mut("CLOSE does not set explicit_close", "op_dio1.c", "  explicit_close = TRUE; /* OPTION", "  /* OPTION")
# every census REFUSE site: the call is taken out
for (_f, _n), _v in sorted(NK_REFUSE.items()):
    mut("%s no longer refuses a NET_FILE" % _n, _f, edit_func(_n, r"\b(?:net_refuse|refuse_net_file)\((?=\w)", "nobody_refuses("))
# S.72: op_filelock, op_flunlock, op_getlocks and op_reclckd left NK_REFUSE; their mutants (a refusal that moves, a refusal that is taken out) are replaced by the mutants of the new structure at the end of the table (M_S72)
mut("op_write refuses after the edit gate", "op_dio3.c", lambda t: edit_func("op_write", r"if \(refuse_net_file\(fvar, op_flags, keep_lock \? \"WRITEU\" : \"WRITE\", NETG_WRITE\)\)\s*goto exit_op_write;", "")(t)
    .replace("    int edit_kind = edit_refusal(fvar);\n    if (edit_kind != EDIT_NONE) {\n      if (!(op_flags & P_ON_ERROR))\n        k_error(sysmsg(EDIT_REFUSED_MSG(edit_kind)));", "    int edit_kind = edit_refusal(fvar);\n    if (refuse_net_file(fvar, op_flags, \"WRITE\", NETG_WRITE))\n      goto exit_op_write;\n    if (edit_kind != EDIT_NONE) {\n      if (!(op_flags & P_ON_ERROR))\n        k_error(sysmsg(EDIT_REFUSED_MSG(edit_kind)));", 1))
# guards and supported statements
mut("the file status of a NET_FILE reads the file table", "op_dio2.c", edit_func("get_file_status", r"if \(ftype == NET_FILE\)\s*return NULL;", ""))
mut("the permissions log reads the file table of a NET_FILE", "k_error.c", edit_func("log_permissions_error", r"fvar->type == NET_FILE", "0"))
mut("the process dump reads the file table of a NET_FILE", "pdump.c", edit_func("dump_variable", r"fvar->type == NET_FILE", "0"))
mut("FILEINFO of a NET_FILE reads the file table", "op_dio2.c", edit_func("op_fileinfo", r"ftype == NET_FILE", "0"))
mut("FILEINFO FL_STATS_OFF is no longer refused for a NET_FILE", "op_dio2.c", "        case FL_STATS_OFF: /* 10003 */", "        case 99999: /* 10003 */")
mut("FILEINFO FL_NETFILE is no longer answered", "op_dio2.c", "        case FL_NETFILE:  /* 1022  A file on another server */\n", "")
mut("FILEINFO does not ask the server for the other keys", "op_dio2.c", "str = net_fileinfo(fvar, key);", "str = NULL;")
mut("READV of a NET_FILE goes through the recursive _readv", "op_dio3.c", edit_func("op_readv", r"if \(fvar->type == NET_FILE\) \{", "if (0) {"))
mut("READV of a NET_FILE does not ask the server", "op_dio3.c", "net_st = net_readv(fvar, id, id_len, field_no, &net_str);", "net_st = 0;")
mut("a NET_FILE has a transaction id", "op_dio3.c", "txn_id = ((fvar->flags & FV_NON_TXN) || (fvar->type == NET_FILE)) ? 0 : process.txn_id;", "txn_id = (fvar->flags & FV_NON_TXN) ? 0 : process.txn_id;")
mut("a locking read of a NET_FILE is not refused", "op_dio3.c", "if ((fvar->type == NET_FILE) && (op_flags & P_REC_LOCKS)) {", "if (0) {")
mut("READ of a NET_FILE has no case", "op_dio3.c", edit_func("read_record", r"case NET_FILE: \{", "case 77: {"))
mut("the helper refuses every file", "op_dio3.c", "  if ((fvar == NULL) || (fvar->type != NET_FILE))\n    return FALSE;\n\n  process.op_flags", "  if (fvar == NULL)\n    return FALSE;\n\n  process.op_flags")
mut("the helper takes a non-negative status", "op_dio3.c", "process.status = (st < 0) ? st : -ER_PERM;", "process.status = st;")
mut("the helper gives net_gate the whole op_flags", "op_dio3.c", "process.op_flags = op_flags & P_ON_ERROR; /* net_gate() raises", "process.op_flags = op_flags; /* net_gate() raises")
# the census scan
mut("a new function reads a file variable", "op_dio4.c", lambda t: t + "\nvoid op_zzz() {\n  DESCRIPTOR* d = e_stack - 1;\n  k_get_file(d);\n}\n")
mut("a new function in another kernel file reads a file variable", "c:op_seqio.c", lambda t: t + "\nvoid op_zzz() {\n  DESCRIPTOR* d = e_stack - 1;\n  k_get_file(d);\n}\n")
mut("a sequential function loses its type test", "c:op_seqio.c", edit_func("op_seek", r"SEQ_FILE", "XX_FILE", count=0))
mut("SET.TRIGGER loses its type test", "dh_misc.c", edit_func("op_settrig", r"ER_NDYN", "ER_XXX", count=0))
# messages, the Makefile list, the suite, the map, the history
mut("message 11507 has a second place", "msg:11507", lambda t: t.rstrip("\n") + " %2\n")
mut("message 11508 has no place", "msg:11508", lambda t: t.replace("%1", ""))
mut("netfiles.c names a message that is not there", NFC, "#define MSG_HANDLER 11507", "#define MSG_HANDLER 11509")
mut("gpl.src loses netfiles", "gpl.src", "netfiles\n", "")
mut("gpl.src lists netfiles before messages", "gpl.src", "messages\nnetfiles\n", "netfiles\nmessages\n")
mut("sd.h says netfiles was removed", "sd.h", "/* NETFILES.C - files on another SD server", "/* NETFILES.C removed - files on another SD server")
mut("the suite loses the kernel section", NFSUITE, '("kernel", kernel_section), ("mustlock", mustlock_section), ("gaps", gaps_section)', '("mustlock", mustlock_section), ("gaps", gaps_section)')
mut("the suite allows a write request", NFSUITE, "KALLOWED = {47, 48, 3, 4, 5, 6, 1}", "KALLOWED = {47, 48, 3, 4, 5, 6, 1, 16}")
mut("the suite loses a matrix statement", NFSUITE, 'km("delete", "delete f', 'km("deletx", "delete f')
mut("the suite expects a message that is not there (S.72: FILEUNLOCK in a transaction)", NFSUITE, 'msg(11510, "nfw", "fileunlock")', 'msg(11599, "nfw", "fileunlock")')
mut("the suite loses its hang guard (EVERY `except subprocess.TimeoutExpired:` of it: S.72b gave the suite a second runner with one)", NFSUITE, every("except subprocess.TimeoutExpired:", "except ValueError:"))
mut("the map loses the op_dio3 rule's suite", NFMAP, "gplsrc/op_dio3.c             : @files @seq prof lockown editgates netfile", "gplsrc/op_dio3.c             : @files @seq prof lockown editgates")
mut("the map loses the netfiles.c rule", NFMAP, "gplsrc/netfiles.c            : netfile\n", "")
mut("the map loses the _voc_ref rule", NFMAP, "sdsys/gpl.bp/_voc_ref        : @core netfile shared\n", "")
mut("the map's dh_ak rule is gone", NFMAP, "gplsrc/dh_ak.c               : @files netfile shared\n", "")
mut("descr.h's history line is gone", "descr.h", "S.65 slice 3c: NET_FILE (4) is back", "S.65: NET_FILE (4) is back")
mut("netfiles.c's history line is gone", NFC, "17 Oct 26 dm  S.65 slice 3c: written.", "17 Oct 26 dm  written.")
mut("_voc_ref's history line is gone", VR, "S.65 slice 3c: a new VOC pointer type N", "S.65: a new VOC pointer type N")
mut("the suite's slice 3c history line is gone", NFSUITE, "# 17 Oct 26 dm  S.65 slice 3c: the section kernel", "# 17 Oct 26 dm  the section kernel")

# ---- slice 3d: SELECT, SELECTV, the DICT form and three FILEINFO keys ----------------------------------------------------------------------------
M3D = len(M)        # the mutants from here on are slice 3d's (the rewritten 3c ones above stay where they were)
OD4, OD2 = "op_dio4.c", "op_dio2.c"
# net_select
mut("net_select asks for another operation", NFC, "status = net_op(fvar, NF_SELECT,", "status = net_op(fvar, NF_READ,")
mut("NF_SELECT is 5 in netfiles.c", NFC, rx(r"(#define\s+NF_SELECT\s+)6", r"\g<1>5"))
mut("NF$SELECT is 5 in netfile.h", NFHD, rx(r"(\$define\s+NF\$SELECT\s+)6", r"\g<1>5"))
mut("net_select calls the handler directly", NFC, edit_func("net_select", r"net_op\(fvar, NF_SELECT, \"\", 0, \"\", 0, ER_FNF, &out\)", "net_call_raw(NF_SELECT, \"\", \"\", \"\", &out, NULL)"))
mut("net_select raises even with ON ERROR", NFC, edit_func("net_select", r"net_raise\(status, entry\)", "net_raise(status, 0)"))
mut("net_select takes no flags at entry", NFC, edit_func("net_select", r"u_int16_t entry = process\.op_flags;", "u_int16_t entry = 0;"))
mut("net_select does not give the flags back", NFC, edit_func("net_select", r"process\.op_flags = entry;\n", ""))
mut("net_select does not stop on an ELSE", NFC, edit_func("net_select", r"if \(status > 0\)\s*return status;", ""))
mut("net_select does not stop on an error", NFC, edit_func("net_select", r"if \(status < 0\)\s*return net_raise\(status, entry\);", ""))
mut("net_select sets *ids before it knows", NFC, edit_func("net_select", r"  status = net_op", "  *ids = NULL;\n  status = net_op"))
mut("net_select sets *count before it knows", NFC, edit_func("net_select", r"  status = net_op", "  *count = 0;\n  status = net_op"))
mut("net_select counts an empty answer as one id", NFC, edit_func("net_select", r"int32_t n = 0;", "int32_t n = 1;"))
mut("net_select does not count the field marks", NFC, edit_func("net_select", r"== FIELD_MARK", "== 0"))
mut("sd.h declares net_select with another type", "sd.h", "int net_select(FILE_VAR * fvar, STRING_CHUNK ** ids, int32_t * count);", "int net_select(FILE_VAR * fvar, STRING_CHUNK ** ids, int32_t count);")
mut("sd.h loses net_select", "sd.h", "int net_select(FILE_VAR * fvar, STRING_CHUNK ** ids, int32_t * count);\n", "")
# op_select and the helper
mut("SELECT empties the target list before it asks the server", OD4, edit_func("op_select", r"fvar = descr->data\.fvar;", "fvar = descr->data.fvar;\n    clear_select(list_no);"))
mut("SELECT of a NET_FILE goes on after an error", OD4, "        k_dismiss();\n        goto select_status;\n      }\n    }\n\n    end_select(list_no);", "        k_dismiss();\n      }\n    }\n\n    end_select(list_no);")
mut("SELECT's switch has no NET_FILE case", OD4, "      case NET_FILE:\n        store_select_list(list_no, net_ids, net_count);", "      case 77:\n        store_select_list(list_no, net_ids, net_count);")
mut("SELECT does not store the ids", OD4, "        store_select_list(list_no, net_ids, net_count);", "        ;")
mut("SELECT's NULL guard is back (an empty file leaves the old count)", OD4, "      case NET_FILE:\n        store_select_list(list_no, net_ids, net_count);", "      case NET_FILE:\n        if (net_ids != NULL)\n          store_select_list(list_no, net_ids, net_count);")
mut("store_select_list returns before it sets the count", OD4, edit_func("store_select_list", r"  descr = Element\(process\.syscom, SYSCOM_SELECT_COUNT\);", "  if (head == NULL)\n    return;\n  descr = Element(process.syscom, SYSCOM_SELECT_COUNT);"))
mut("store_select_list has no early return for a NULL list", OD4, edit_func("store_select_list", r"  if \(head == NULL\)\s*return;", ""))
mut("SELECT calls net_select without the helper", OD4, edit_func("op_select", r"net_select_with_flags\(fvar, op_flags, &net_ids, &net_count\)", "net_select(fvar, &net_ids, &net_count)"))
mut("SELECT refuses a NET_FILE again", OD4, edit_func("op_select", r"net_st = net_select_with_flags", "net_refuse(fvar, \"SELECT\");\n      net_st = net_select_with_flags"))
mut("the helper gives net_select the whole op_flags", OD4, "process.op_flags = op_flags & P_ON_ERROR;\n  st = net_select(fvar, ids, count);", "process.op_flags = op_flags;\n  st = net_select(fvar, ids, count);")
mut("the helper leaves process.op_flags set", OD4, "  st = net_select(fvar, ids, count);\n  process.op_flags = 0;", "  st = net_select(fvar, ids, count);")
mut("dir_select no longer ends with store_select_list", OD4, edit_func("dir_select", r"store_select_list\(list_no, head, record_count\);", ";"))
mut("store_select_list is declared with another type", "sd.h", "void store_select_list(int16_t list_no, STRING_CHUNK * head, int32_t record_count);", "void store_select_list(int16_t list_no, STRING_CHUNK * head, int16_t record_count);")
mut("store_select_list is Private again in op_dio4.c", OD4, "void store_select_list(int16_t list_no, STRING_CHUNK* head, int32_t record_count) {", "Private void store_select_list(int16_t list_no, STRING_CHUNK* head, int32_t record_count) {")
mut("net_index_query is declared with another type", "sd.h", "int net_index_query(FILE_VAR * fvar, int what, const char * c, int clen, STRING_CHUNK ** answer, int * server_st);", "int net_index_query(FILE_VAR * fvar, int what, const char * c, int32_t clen, STRING_CHUNK ** answer, int * server_st);")
mut("net_select_with_flags is declared with another type", OD4, "Private int net_select_with_flags(FILE_VAR* fvar, u_int16_t op_flags, STRING_CHUNK** ids, int32_t* count);", "Private int net_select_with_flags(FILE_VAR* fvar, u_int16_t op_flags, STRING_CHUNK** ids, int32_t count);")
mut("a second place calls net_select", OD4, lambda t: t + "\nvoid zz_sel(FILE_VAR* v) {\n  net_select(v, NULL, NULL);\n}\n")
# op_selectv
mut("SELECTV does not find its target again after the call", OD4, "\n\n      /* The handler ran BASIC: the target is found again from the stack, as op_read does */\n      tgt_descr = e_stack - 1;\n      while (tgt_descr->type == ADDR)\n        tgt_descr = tgt_descr->data.d_addr;\n", "\n")
mut("SELECTV uses its target before the call", OD4, edit_func("op_selectv", r"net_ids = NULL;\n      net_count = 0;\n      net_st", "net_ids = NULL;\n      net_count = 0;\n      InitDescr(tgt_descr, SELLIST);\n      net_st"))
mut("SELECTV's target is not an empty list after an error", OD4, "      tgt_descr->data.str.saddr = NULL; /* an empty list unless the ids came */\n", "")
mut("SELECTV's list has no count", OD4, "        net_ids->offset = net_count;\n", "")
mut("SELECTV does not set @SELECTED", OD4, "        descr = Element(process.syscom, SYSCOM_SELECTED);\n        descr->data.value = net_count;\n      }\n      goto selectv_status;", "      }\n      goto selectv_status;")
mut("SELECTV sets @SELECTED only for a non-empty list", OD4, "          net_ids->offset = net_count;\n        }\n        descr = Element(process.syscom, SYSCOM_SELECTED);\n        descr->data.value = net_count;",
    "          net_ids->offset = net_count;\n          descr = Element(process.syscom, SYSCOM_SELECTED);\n          descr->data.value = net_count;\n        }")
mut("SELECTV gives the list its ids without the NULL test", OD4, "        if (net_ids != NULL) {\n          tgt_descr->data.str.saddr = net_ids;\n          net_ids->offset = net_count;\n        }", "        tgt_descr->data.str.saddr = net_ids;\n        net_ids->offset = net_count;")
mut("SELECTV of a NET_FILE goes on into the local switch", OD4, "      }\n      goto selectv_status;\n    }\n\n    /* Do the select */", "      }\n    }\n\n    /* Do the select */")
mut("SELECTV refuses a NET_FILE again", OD4, edit_func("op_selectv", r"net_st = net_select_with_flags", "net_refuse(fvar, \"SELECTV\");\n      net_st = net_select_with_flags"))
mut("SELECTV ignores the status", OD4, "      if (net_st != 0) {\n        process.status = net_st;\n      } else {", "      if (0) {\n        process.status = net_st;\n      } else {")
# INDICES of a remote file: the refusal comes back
mut("INDICES(f) refuses a NET_FILE again", "dh_ak.c", edit_func("op_indices1", r"fvar = descr->data\.fvar;", "fvar = descr->data.fvar;\n  if (fvar->type == NET_FILE)\n    net_refuse(fvar, \"INDICES\");"))
mut("INDICES(f, name) refuses a NET_FILE again", "dh_ak.c", edit_func("op_indices2", r"fvar = descr->data\.fvar;", "fvar = descr->data.fvar;\n  if (fvar->type == NET_FILE)\n    net_refuse(fvar, \"INDICES\");"))
mut("INDICES(f) refuses through the helper", "dh_ak.c", edit_func("op_indices1", r"k_dismiss\(\);", "refuse_net_file(fvar, 0, \"INDICES\");\n  k_dismiss();"))
# S.73 item 3 D1 (21 Oct 26): the six index query sites ask the server; each of these changes ONE thing NK18, NK18a, NK18b or NF14 pins
mut("INDICES(f) asks the wrong operation", "dh_ak.c", edit_func("op_indices1", r"net_index_query\(fvar, 1,", "net_index_query(fvar, 2,"))
mut("INDICES(f, name) asks the wrong operation", "dh_ak.c", edit_func("op_indices2", r"net_index_query\(fvar, 2,", "net_index_query(fvar, 1,"))
mut("INDICES(f) goes on into the local switch", "dh_ak.c", edit_func("op_indices1", r"\(e_stack\+\+\)->data\.str\.saddr = tgt;\n    return;", "(e_stack++)->data.str.saddr = tgt;"))
mut("INDICES(f, name) dismisses its operands once", "dh_ak.c", edit_func("op_indices2", r"k_dismiss\(\);\n    k_dismiss\(\);\n    InitDescr", "k_dismiss();\n    InitDescr"))
mut("SELECTINDEX does not hand over to net_selindex", "dh_ak.c", edit_func("op_selindx", r"net_selindex\(FALSE, list_no\);", ""))
mut("SELECTINDEX of a value hands over the wrong form", "dh_ak.c", edit_func("op_selindxv", r"net_selindex\(TRUE, list_no\);", "net_selindex(FALSE, list_no);"))
mut("SELECTINDEX tests the type after clear_select", "dh_ak.c", edit_func("op_selindx", r"if \(descr->data\.fvar->type == NET_FILE\) \{", "clear_select(list_no);\n  if (descr->data.fvar->type == NET_FILE) {"))
mut("SELECTLEFT / SELECTRIGHT do not hand over to net_akscan", "dh_ak.c", edit_func("akscan", r"net_akscan\(right, list_no\);", ""))
mut("SETLEFT / SETRIGHT ask the wrong operation", "dh_ak.c", edit_func("setakpos", r"right \? 6 : 5", "right ? 5 : 6"))
mut("SETLEFT / SETRIGHT forget the server's STATUS()", "dh_ak.c", edit_func("setakpos", r"process\.status = net_st;", ""))
mut("SETLEFT / SETRIGHT keep the answer", "dh_ak.c", edit_func("setakpos", r"s_free\(net_ans\);", ""))
mut("SELECTINDEX clears the list before the server answers", "dh_ak.c", edit_func("net_selindex", r"\(void\)net_index_query\(", "clear_select(list_no);\n    (void)net_index_query("))
mut("SELECTLEFT / SELECTRIGHT clear the list before the server answers", "dh_ak.c", edit_func("net_akscan", r"\(void\)net_index_query\(", "clear_select(list_no);\n  (void)net_index_query("))
mut("SELECTINDEX keeps the ids of an unknown index", "dh_ak.c", edit_func("net_selindex", r"if \(\(net_st != 0\) && \(ids != NULL\)\) \{", "if (0) {"))
mut("SELECTLEFT / SELECTRIGHT split the answer of a failed scan", "dh_ak.c", edit_func("net_akscan", r"if \(net_st == 0\)", "if (1)"))
mut("SELECTLEFT / SELECTRIGHT forget the server's STATUS()", "dh_ak.c", edit_func("net_akscan", r"process\.status = net_st;", ""))
mut("net_index_query does not clear process.op_flags", NFC, edit_func("net_index_query", r"process\.op_flags = 0;", ""))
mut("net_index_query accepts an ELSE answer", NFC, edit_func("net_index_query", r"if \(status > 0\) \{", "if (0) {"))
mut("net_index_query ignores a negative status", NFC, edit_func("net_index_query", r"if \(status < 0\)\n    return net_raise\(status, 0\);", ""))
mut("net_index_query passes the server's status on", NFC, edit_func("net_index_query", r"ER_FNF, FALSE, FALSE, &out\)", "ER_FNF, FALSE, TRUE, &out)"))
mut("net_index_query sets the answers before it raises", NFC, edit_func("net_index_query", r"status = net_op_ex\(", "*server_st = 9;\n  status = net_op_ex("))
mut("NF_INDEXQ is 25 in netfiles.c", NFC, rx(r"(#define\s+NF_INDEXQ\s+)24", r"\g<1>25"))
mut("NF$INDEXQ is 25 in netfile.h", "bp:netfile.h", rx(r"(\$define\s+NF\$INDEXQ\s+)24", r"\g<1>25"))
mut("NF$INDEXQ is not dispatched to act.indexq", NFP, rx(r"(case op = NF\$INDEXQ\s*;\s*gosub act\.)indexq", r"\1fileunlock"))
mut("act.indexq: an arm sends without its mark", NFP, "case what = 3 ; obj->ServerStatus = NF$NOREPLY ; res = obj->selectindexv(", "case what = 3 ; res = obj->selectindexv(")
mut("act.indexq: SELECTLEFT asks for SELECTRIGHT", NFP, "case what = 7 ; obj->ServerStatus = NF$NOREPLY ; res = obj->selectleft(", "case what = 7 ; obj->ServerStatus = NF$NOREPLY ; res = obj->selectright(")
mut("act.indexq: the scan's second request loses its mark", NFP, "      obj->error = ''\n      obj->ServerStatus = NF$NOREPLY\n      e = ''\n      lst = obj->readlist(NF$LIST, e)\n      gosub after.rq\n      nf.requests += 1\n      if rq.lost then\n         gosub lost.fail\n         return\n      end\n      if rq.err then\n         gosub server.fail\n         return\n      end\n      if e = 1 then\n         gosub on.error.text\n         gosub server.fail\n         return\n      end\n      if e # 0 then\n         fail.num = 11504 ; fail.a1 = srvname ; fail.a2 = opname ; fail.a3 = 'answer ':e\n         gosub fail\n         return\n      end\n      out = key : @fm : lst", "      obj->error = ''\n      e = ''\n      lst = obj->readlist(NF$LIST, e)\n      gosub after.rq\n      nf.requests += 1\n      if rq.lost then\n         gosub lost.fail\n         return\n      end\n      if rq.err then\n         gosub server.fail\n         return\n      end\n      if e = 1 then\n         gosub on.error.text\n         gosub server.fail\n         return\n      end\n      if e # 0 then\n         fail.num = 11504 ; fail.a1 = srvname ; fail.a2 = opname ; fail.a3 = 'answer ':e\n         gosub fail\n         return\n      end\n      out = key : @fm : lst")
mut("act.indexq: the scan loses the first request's status", NFP, "      rc<8> = st1\n", "")
mut("act.indexq: a what over 8 is accepted", NFP, "if what < 1 or what > 8 then", "if what < 1 or what > 9 then")
mut("act.indexq refuses a read-mode handle", NFP, "   opname = 'index'\n", "   opname = 'index'\n   if nf.h.mode(hx) # 'write' then gosub act.refuse\n")
mut("act.indexq writes an audit line", NFP, "   opname = 'index'\n", "   opname = 'index'\n   kernel(K$AUDIT, 'netfile index server=' : srvname)\n")
mut("the class: SETLEFT aborts when quiet", SCL, "         if server.error = SV$ON.ERROR and not(quiet) then\n            abort 'SETLEFT generated an abort event'", "         if server.error = SV$ON.ERROR then\n            abort 'SETLEFT generated an abort event'")
mut("the class: SELECTRIGHT aborts when quiet", SCL, "if not(quiet) then abort 'SELECTRIGHT generated an abort event'", "abort 'SELECTRIGHT generated an abort event'")
mut("SELECTV has no NET branch", OD4, edit_func("op_selectv", r"if \(fvar->type == NET_FILE\)", "if (0)"))
# FILEINFO
mut("FL_TYPE_NET is 6 in keys.h", "keys.h", rx(r"(#define\s+FL_TYPE_NET\s+)7", r"\g<1>6"))
mut("FL_TYPE_NET is 5 (the sequential file's)", "keys.h", rx(r"(#define\s+FL_TYPE_NET\s+)7", r"\g<1>5"))
mut("FL$TYPE.NET is 8 in syscom/keys.h", "syscom/keys.h", rx(r"(\$define\s+FL\$TYPE\.NET\s+)7", r"\g<1>8"))
mut("FL$TYPE.NET is gone from syscom/keys.h", "syscom/keys.h", drop_line(r"FL\$TYPE\.NET"))
mut("FL_TYPE_NET is gone from keys.h", "keys.h", drop_line(r"FL_TYPE_NET"))
mut("FILEINFO FL_TYPE answers a directory file", OD2, "n = FL_TYPE_NET;", "n = FL_TYPE_DIR;")
mut("FILEINFO FL_TYPE of a NET_FILE goes to the server", OD2, "        case FL_TYPE: /* 3  A file on another server", "        case 99998: /* 3  A file on another server")
mut("FILEINFO FL_COLLECTION answers 1", OD2, "(slice 3d) */\n          n = 0;", "(slice 3d) */\n          n = 1;")
mut("FILEINFO FL_COLLECTION of a NET_FILE goes to the server", OD2, "        case FL_COLLECTION: /* 1035  The query processor asks", "        case 99997: /* 1035  The query processor asks")
mut("FILEINFO FL_FLAGS is not restricted to $internal programs", OD2, "n = (process.program.flags & HDR_INTERNAL) ? DHF_NOCASE : 0;", "n = DHF_NOCASE;")
mut("FILEINFO FL_FLAGS answers 0 to an $internal program", OD2, "n = (process.program.flags & HDR_INTERNAL) ? DHF_NOCASE : 0;", "n = 0;")
mut("FILEINFO FL_FLAGS of a NET_FILE goes to the server", OD2, "        case FL_FLAGS: /* 10001  The query processor asks for the NOCASE bit", "        case 99996: /* 10001  The query processor asks for the NOCASE bit")
mut("FILEINFO FL_FLAGS of a NET_FILE reads the file table", OD2, "(process.program.flags & HDR_INTERNAL) ? DHF_NOCASE : 0;", "(process.program.flags & HDR_INTERNAL) ? FPtr(fvar->file_id)->flags : 0;")

# ---- 18 Oct 26: the record cache (NK19-NK24) and K_NET closing the remote files (NK25)
mut("the cache has 65 slots", NFC, "#define NET_CACHE_SLOTS 64", "#define NET_CACHE_SLOTS 65")
mut("the cache keeps a record for 3 seconds", NFC, "#define NET_CACHE_TTL 2 ", "#define NET_CACHE_TTL 3 ")
mut("the cache keeps records of 64 KB", NFC, "#define NET_CACHE_REC_MAX 32768", "#define NET_CACHE_REC_MAX 65536")
mut("netfiles.c does not include time.h", NFC, "#include <time.h>\n", "")
mut("a cache entry has no epoch", NFC, "  u_int16_t epoch;\n  int16_t id_len;", "  int16_t id_len;")
mut("a cache hit ignores the handle", NFC, "(e->handle == fvar->access.net.handle) && ", "")
mut("a cache hit ignores the epoch", NFC, " && (e->epoch == fvar->access.net.epoch)", "")
mut("a cache hit ignores the id length", NFC, " && (e->id_len == id_len)", "")
mut("a cache hit ignores the id bytes", NFC, "(memcmp(e->id, id, id_len) == 0)", "1")
mut("the cache never expires an entry", NFC, "(now < e->when) || ((now - e->when) > NET_CACHE_TTL)", "(now < e->when)")
mut("the cache trusts an entry from the future", NFC, "(now < e->when) || ((now - e->when) > NET_CACHE_TTL)", "((now - e->when) > NET_CACHE_TTL)")
mut("an expired entry is skipped but not freed", NFC, edit_func("net_cache_find", r"net_cache_free\(e\);\s*continue;", "continue;"))
mut("the cache keeps an id of length 0", NFC, "(id_len < 1) || (id_len > MAX_ID_LEN)", "(id_len > MAX_ID_LEN)")
mut("the cache keeps an id over MAX_ID_LEN", NFC, "(id_len < 1) || (id_len > MAX_ID_LEN)", "(id_len < 1)")
mut("the cache keeps a record over NET_CACHE_REC_MAX", NFC, " || ((rec != NULL) && (rec->string_len > NET_CACHE_REC_MAX))", "")
mut("the cache keeps the caller's chain, not a copy", NFC, "e->rec = (rec != NULL) ? k_copy_string(rec) : NULL;", "e->rec = rec;")
mut("a full cache does not free the old record of the slot it takes", NFC, edit_func("net_cache_put", r"net_cache_free\(e\);", ""))
mut("a full cache always takes slot 0", NFC, "e = &net_cache[net_cache_next];", "e = &net_cache[0];")
mut("the cache's ring does not advance", NFC, "net_cache_next = (net_cache_next + 1) % NET_CACHE_SLOTS;", "net_cache_next = net_cache_next;")
mut("a cache entry has no time", NFC, "  e->when = time(NULL);", "  e->when = 0;")
mut("a cache entry is stored without its epoch", NFC, "  e->epoch = fvar->access.net.epoch;\n", "")
mut("net_cache_free leaks the record", NFC, "    s_free(e->rec);", "    ;")
mut("net_cache_free leaves the entry in use", NFC, "  e->used = FALSE;\n}", "}")
mut("net_cache_drop(0) drops only handle 0", NFC, "((handle == 0) || (net_cache[i].handle == handle))", "(net_cache[i].handle == handle)")
mut("net_cache_drop(h) drops nothing", NFC, "((handle == 0) || (net_cache[i].handle == handle))", "(handle == 0)")
mut("net_cache_drop(h) drops every handle", NFC, "((handle == 0) || (net_cache[i].handle == handle))", "1")
mut("net_read consults the cache for a stale file variable", NFC, "  if (!net_stale(fvar) && !fvar->access.net.write) {\n    NET_CACHE_ENTRY* hit", "  if (!fvar->access.net.write) {\n    NET_CACHE_ENTRY* hit")
mut("net_read serves an absent entry as another status", NFC, "      if (hit->absent)\n        return ER_RNF;", "      if (hit->absent)\n        return ER_FNF;")
mut("net_read gives the cached chain itself", NFC, "*rec = (hit->rec != NULL) ? k_copy_string(hit->rec) : NULL;", "*rec = hit->rec;")
mut("net_read caches an absent entry for any positive status", NFC, "    if (status == ER_RNF)\n      net_cache_put(fvar, id, id_len, NULL, TRUE);", "    net_cache_put(fvar, id, id_len, NULL, TRUE);")
mut("net_read caches nothing it read", NFC, "  net_cache_put(fvar, id, id_len, *rec, FALSE);\n", "")
mut("net_read caches on an error", NFC, edit_func("net_read", r"  if \(status < 0\)\s*return net_raise\(status, entry\);", "  if (status < 0) {\n    net_cache_put(fvar, id, id_len, NULL, TRUE);\n    return net_raise(status, entry);\n  }"))
mut("net_read never consults the cache", NFC, "NET_CACHE_ENTRY* hit = net_cache_find(fvar, id, id_len);", "NET_CACHE_ENTRY* hit = NULL;")
mut("net_readv uses the cache", NFC, edit_func("net_readv", r"  status = net_op\(fvar, NF_READV", "  (void)net_cache_find(fvar, id, id_len);\n  status = net_op(fvar, NF_READV"))
mut("net_select does not drop the handle's entries", NFC, "  net_cache_drop(fvar->access.net.handle); /* a new query is a new look at the file */\n", "")
mut("net_select drops them after the request", NFC, lambda t: t.replace("  net_cache_drop(fvar->access.net.handle); /* a new query is a new look at the file */\n", "", 1).replace("  process.op_flags = entry;\n  if (status < 0)\n    return net_raise(status, entry);\n  if (status > 0)\n    return status;\n\n  s = net_take_string", "  net_cache_drop(fvar->access.net.handle);\n  process.op_flags = entry;\n  if (status < 0)\n    return net_raise(status, entry);\n  if (status > 0)\n    return status;\n\n  s = net_take_string", 1))
mut("net_close does not drop the handle's entries", NFC, edit_func("net_close", r"  if \(handle > 0\)\s*net_cache_drop\(handle\);\n", ""))
mut("net_close drops them after the stale test", NFC, "  if (handle > 0)\n    net_cache_drop(handle);\n  if (net_stale(fvar))\n    return;", "  if (net_stale(fvar))\n    return;\n  if (handle > 0)\n    net_cache_drop(handle);")
mut("net_close drops handle 0, which is everything", NFC, edit_func("net_close", r"  if \(handle > 0\)\s*net_cache_drop\(handle\);", "  net_cache_drop(handle);"))
mut("net_close_all keeps the cache", NFC, "  net_cache_drop(0);\n", "")
mut("net_close_all drops the cache only when something was opened", NFC, "  net_cache_drop(0);\n\n  if (!net_used)\n    return;\n", "\n  if (!net_used)\n    return;\n  net_cache_drop(0);\n")
mut("a second place drops the cache", NFC, lambda t: t + "\nvoid zz_drop(void) {\n  net_cache_drop(0);\n}\n")
# K_NET
mut("K_NET never closes the remote files", "op_kernel.c", "          net_close_all();\n", "")
mut("K_NET's ask form closes the remote files", "op_kernel.c", "      result.data.value = MY_GATE(UG_NET);\n      break;\n\n    /* K_EDIT_OK / K_EDIT_KIND", "      net_close_all();\n      result.data.value = MY_GATE(UG_NET);\n      break;\n\n    /* K_EDIT_OK / K_EDIT_KIND")
mut("K_NET closes the remote files for a caller that is not $internal", "op_kernel.c", rx(r"          net_close_all\(\);\n          process\.status = n;\n          break;\n        \}\n", "          process.status = n;\n          break;\n        }\n        net_close_all();\n"))
mut("K_NET closes the remote files before it changes the gate", "op_kernel.c", lambda t: t.replace("          net_close_all();\n", "", 1).replace("          SET_MY_GATE(UG_NET, n > 0);", "          net_close_all();\n          SET_MY_GATE(UG_NET, n > 0);", 1))
mut("K_NET does not save the caller's STATUS()", "op_kernel.c", "          n = process.status; /* the handler is BASIC and leaves its own STATUS() behind; the caller's is given back */\n", "")
mut("K_NET does not give the caller's STATUS() back", "op_kernel.c", rx(r"          process\.status = n;\n          break;", "          break;"))
mut("K_NET uses descr after the handler ran", "op_kernel.c", "          process.status = n;\n          break;", "          process.status = n;\n          result.data.value = descr->data.value;\n          break;")
mut("K_NET computes the answer after the handler ran", "op_kernel.c", lambda t: t.replace("          result.data.value = MY_GATE(UG_NET);\n          n = process.status;", "          n = process.status;", 1).replace("          net_close_all();\n          process.status = n;\n", "          net_close_all();\n          process.status = n;\n          result.data.value = MY_GATE(UG_NET);\n", 1))
mut("K_NET falls through after the close", "op_kernel.c", rx(r"          process\.status = n;\n          break;\n        \}\n", "          process.status = n;\n        }\n"))

# ---- 18 Oct 26, slice 3e: writes and locks (S2a to S2z and the checks rewritten for it) --------------------------------------------------------------
M3E_START = len(M)         # the mutants from here on are slice 3e's
SH, OLK, D3, D2, KRN, EGD, CPR = "op_sh.c", "op_lock.c", "op_dio3.c", "op_dio2.c", "op_kernel.c", "bp:edit_guard", "bp:cproc"
# ---- the codes and the messages
mut("netfile.h: NF$WRITEU is 15 (DELETEU's)", NFHD, rx(r"(\$define\s+NF\$WRITEU\s+)14", r"\g<1>15"))
mut("netfile.h: NF$DELETEU is 17", NFHD, rx(r"(\$define\s+NF\$DELETEU\s+)15", r"\g<1>17"))
mut("netfile.h: NF$RELEASE is 17", NFHD, rx(r"(\$define\s+NF\$RELEASE\s+)16", r"\g<1>17"))
mut("netfile.h: NF$RC.LOCKED is 5", NFHD, rx(r"(\$define\s+NF\$RC\.LOCKED\s+)4", r"\g<1>5"))
mut("netfile.h: NF$LOCK is 18", NFHD, rx(r"(\$define\s+NF\$LOCK\s+)12", r"\g<1>18"))
mut("netfiles.c: NF_WRITEU is 13 (STATE's)", NFC, rx(r"(#define\s+NF_WRITEU\s+)14", r"\g<1>13"))
mut("netfiles.c: NF_DELETEU is 16", NFC, rx(r"(#define\s+NF_DELETEU\s+)15", r"\g<1>16"))
mut("netfiles.c: NF_RELEASE is 17", NFC, rx(r"(#define\s+NF_RELEASE\s+)16", r"\g<1>17"))
mut("netfiles.c: NF_RC_LOCKED is 5", NFC, rx(r"(#define\s+NF_RC_LOCKED\s+)4", r"\g<1>5"))
mut("netfiles.c: NF_LOCK is 13", NFC, rx(r"(#define\s+NF_LOCK\s+)12", r"\g<1>13"))
mut("netfiles.c: NF_WRITE is 8", NFC, rx(r"(#define\s+NF_WRITE\s+)9", r"\g<1>8"))
mut("message 11509 changes its words", "msg:11509", lambda t: t.replace("not known whether", "unknown whether"))
mut("message 11509 is gone", "msg:11509", lambda t: None)
mut("message 11510 loses its server place", "msg:11510", lambda t: t.replace("server %1", "the server"))
mut("message 11510 says allowed", "msg:11510", lambda t: t.replace("cannot be changed or locked", "may be changed or locked"))
mut("message 11511 is gone", "msg:11511", lambda t: None)
mut("message 11511 has a third place", "msg:11511", lambda t: t.rstrip("\n") + " %3\n")
mut("message 11512 takes two lines", "msg:11512", lambda t: t.rstrip("\n") + "\nsecond line\n")
mut("the handler cites 11511", NFP, "fail.num = 11512 ; fail.a1 = srvname ; fail.a2 = out.txt", "fail.num = 11511 ; fail.a1 = srvname ; fail.a2 = out.txt")
mut("another program cites 11510", "bp:cd", lambda t: t + "\n   crt sysmsg(11510)\n")
# ---- the handler: the mode
mut("act.open takes the mode from field 7", NFP, "if defs<found,6> = 'write' then fmode = 'write'", "if defs<found,7> = 'write' then fmode = 'write'")
mut("act.open: the default mode is write", NFP, "   fmode = 'read'\n   if defs<found,6> = 'write' then fmode = 'write'", "   fmode = 'write'\n   if defs<found,6> = 'write' then fmode = 'write'")
mut("act.open: any mode but read is write", NFP, "if defs<found,6> = 'write' then fmode = 'write'", "if defs<found,6> # 'read' then fmode = 'write'")
mut("act.open: rc<7> is never set", NFP, "   if fmode = 'write' then rc<7> = 1\n", "")
mut("act.open: rc<7> is always set", NFP, "   if fmode = 'write' then rc<7> = 1\n", "   rc<7> = 1\n")
mut("act.open: the mode is not kept for the handle", NFP, "   nf.h.mode(hx) = fmode\n", "")
mut("act.open: the read audit line says mode=read", NFP, "      void kernel(K$AUDIT, 'netfile open server=' : srv : ' file=' : fname)\n", "      void kernel(K$AUDIT, 'netfile open server=' : srv : ' file=' : fname : ' mode=read')\n")
mut("act.open: the write audit line has no mode", NFP, " : ' mode=write')", ")")
mut("act.open: the mode is decided before the accounts list", NFP, "   fmode = 'read'\n   if defs<found,6> = 'write' then fmode = 'write'\n", "")
mut("clear.handle keeps the mode", NFP, "   nf.h.mode(hy) = ''\n", "")
mut("clear.handle keeps the audit letters", NFP, "   nf.h.aud(hy) = ''\n", "")
mut("the common block has no mode array", NFP, "nf.h.mode(NF$MAX.HANDLES),", "nf.h.modeq(NF$MAX.HANDLES),")
mut("mode.now starts true", NFP, "   mode.ok = @false\n   defs = ''", "   mode.ok = @true\n   defs = ''")
mut("mode.now accepts any mode but read", NFP, "if defs<dx,6> = 'write' then mode.ok = @true", "if defs<dx,6> # 'read' then mode.ok = @true")
mut("mode.now does not look at the server's name", NFP, " and defs<dx,1> = nf.h.srv(hx) then", " then")
mut("mode.now takes a short definition", NFP, "if dcount(defs<dx>, @vm) = 8 and defs<dx,1> = nf.h.srv(hx) then", "if defs<dx,1> = nf.h.srv(hx) then")
mut("mode.now is never asked", NFP, "   gosub mode.now\n   if not(mode.ok) then", "   mode.ok = @true\n   if not(mode.ok) then")
mut("the handle's own mode is not tested", NFP, "   if nf.h.mode(hx) # 'write' then\n      gosub act.refuse\n      return\n   end", "   if 0 then\n      gosub act.refuse\n      return\n   end")
mut("the refusal for the definition is audited directly", NFP, "      aud.line = 'netfile refused server=' : srvname : ' reason=mode'\n      gosub audit.once\n", "      void kernel(K$AUDIT, 'netfile refused server=' : srvname : ' reason=mode')\n")
mut("the refusal for the definition is not audited", NFP, "      aud.line = 'netfile refused server=' : srvname : ' reason=mode'\n      gosub audit.once\n", "")
mut("the transaction is not tested by the handler", NFP, "   if system(SYS$TRANS_LEVEL) # 0 then", "   if 0 then")
mut("the handler tests the transaction with the wrong word", NFP, "if system(SYS$TRANS_LEVEL) # 0 then", "if system(1007) # 0 then")
mut("an empty id is not an error for a change", NFP, "check.id.chg:\n   id = b\n   if id = '' then", "check.id.chg:\n   id = b\n   if 0 then")
mut("a lock kind is not checked", NFP, "      if c # 'l' and c # 'u' then", "      if 0 then")
mut("a lock kind is checked case blind", NFP, "      if c # 'l' and c # 'u' then", "      if downcase(c) # 'l' and downcase(c) # 'u' then")
mut("CLEARFILE is given an id check", NFP, "   if op # NF$CLEARFILE and op # NF$FILELOCK then\n      gosub check.id.chg", "   if op # NF$FILELOCK then\n      gosub check.id.chg")
mut("FILELOCK is given an id check", NFP, "   if op # NF$CLEARFILE and op # NF$FILELOCK then\n      gosub check.id.chg", "   if op # NF$CLEARFILE then\n      gosub check.id.chg")
# ---- the handler: the requests
mut("a lock may wait on the server", NFP, "obj->recordlock(nf.h.fno(hx), id, upd, @false)", "obj->recordlock(nf.h.fno(hx), id, upd, @true)")
mut("a lock is always an update lock", NFP, "      upd = (c = 'u')", "      upd = @true")
mut("a change is sent twice", NFP, "         obj->write(nf.h.fno(hx), id, c)\n", "         obj->write(nf.h.fno(hx), id, c)\n         obj->write(nf.h.fno(hx), id, c)\n")
mut("WRITEU is sent as WRITE", NFP, "obj->writeu(nf.h.fno(hx), id, c)", "obj->write(nf.h.fno(hx), id, c)")
mut("DELETEU is sent as DELETE", NFP, "obj->deleteu(nf.h.fno(hx), id)", "obj->delete(nf.h.fno(hx), id)")
mut("a change is sent without the no-reply mark", NFP, "         obj->ServerStatus = NF$NOREPLY\n         obj->deleteu(", "         obj->deleteu(")
mut("CLEARFILE has no long bound", NFP, "         obj->settimeout(clear.ms)\n", "")
mut("CLEARFILE keeps its long bound", NFP, "      if not(rq.lost) then obj->settimeout(req.ms)\n", "")
mut("NF$CLEAR.MIN.MS is 30000", NFP, rx(r"(\$define NF\$CLEAR\.MIN\.MS\s+)300000", r"\g<1>30000"))
mut("a missing reply (LastError -1) is not lost", NFP, "   if lerr = -1 then rq.lost = @true\n", "")
mut("a change that got no reply is 11497", NFP, "      fail.num = 11509 ; fail.a1 = srvname ; fail.a2 = opname", "      fail.num = 11497 ; fail.a1 = srvname ; fail.a2 = opname")
mut("a lock that got no reply is 11509", NFP, "   end else\n      fail.num = 11497", "   end else\n      fail.num = 11509")
mut("a lost change is not audited", NFP, "      void kernel(K$AUDIT, 'netfile lost server=' : srvname : ' op=' : opname)\n", "")
mut("a lost change is audited in capitals", NFP, "'netfile lost server='", "'NETFILE LOST server='")
mut("the unsigned status is not made negative", NFP, "      if st > 2147483647 then st -= 4294967296\n", "")
mut("the unsigned fix is off by one", NFP, "st -= 4294967296", "st -= 4294967295")
mut("lost is decided by a sign test (the defect of the first 3e build: -3023 is a reply, not a lost connection)", NFP, "   rq.lost = (st = NF$NOREPLY)\n", "   rq.lost = (st < 0)\n")
mut("an ON ERROR reply to a change shows neither its text nor its status", NFP, "      gosub on.error.text\n      gosub server.fail\n      return\n   end\n   fail.num = 11504", "      gosub server.fail\n      return\n   end\n   fail.num = 11504")
mut("an ON ERROR reply to a change shows the status again whatever the server said (the text before 19 Oct 26, K1)", NFP, "      gosub on.error.text\n      gosub server.fail\n      return\n   end\n   fail.num = 11504", "      rq.txt = 'status ':rq.st\n      gosub server.fail\n      return\n   end\n   fail.num = 11504")
mut("an ON ERROR reply to a READ shows the status again whatever the server said", NFP, "         gosub on.error.text\n         gosub server.fail\n      case 1\n", "         rq.txt = 'status ':rq.st\n         gosub server.fail\n      case 1\n")
mut("an ON ERROR reply to a SELECT shows the status again whatever the server said", NFP, "   if e = 1 then\n      gosub on.error.text", "   if e = 1 then\n      rq.txt = 'status ':rq.st")
mut("on.error.text ignores the reply's text", NFP, "   txt = obj->LastText\n   gosub clean.text", "   txt = ''\n   gosub clean.text")
mut("on.error.text shows the text without cleaning it", NFP, "   txt = obj->LastText\n   gosub clean.text\n   if out.txt = ''", "   txt = obj->LastText\n   out.txt = txt\n   if out.txt = ''")
mut("on.error.text has no status to fall back on", NFP, "   if out.txt = '' then\n      rq.txt = 'status ':rq.st\n   end else", "   if 0 then\n      rq.txt = 'status ':rq.st\n   end else")
mut("on.error.text falls back to nothing", NFP, "   if out.txt = '' then\n      rq.txt = 'status ':rq.st\n   end else", "   if out.txt = '' then\n      rq.txt = ''\n   end else")
mut("on.error.text reads the error text of the object, not the ON ERROR payload", NFP, "   txt = obj->LastText\n   gosub clean.text\n   if out.txt = ''", "   txt = obj->error\n   gosub clean.text\n   if out.txt = ''")
mut("the handler's header says again that the ON ERROR text is never shown", NFP, "is shown, cleaned, by on.error.text, and a reply with no text shows 'status <n>' (19 Oct 26).", "is never shown, it can be stale.")
mut("a busy lock is a server error", NFP, "      gosub rc.locked\n      return", "      gosub server.fail\n      return")
mut("a busy lock is not recognised", NFP, "   if (op = NF$LOCK or op = NF$FILELOCK) and lerr = NF$LE.LOCKED then", "   if 0 then")
mut("any change may be busy", NFP, "   if (op = NF$LOCK or op = NF$FILELOCK) and lerr = NF$LE.LOCKED then", "   if lerr = NF$LE.LOCKED then")
mut("rc.locked loses the holder", NFP, "   rc<1> = NF$RC.LOCKED\n   rc<6> = rq.st", "   rc<1> = NF$RC.LOCKED")
mut("rc.locked is an ELSE", NFP, "   rc<1> = NF$RC.LOCKED", "   rc<1> = NF$RC.ELSE")
mut("rc.locked sets failed", NFP, "   rc<6> = rq.st\n   return\n\n* ======================================================================\n* mode.now", "   rc<6> = rq.st\n   failed = @true\n   return\n\n* ======================================================================\n* mode.now")
mut("NF$LE.LOCKED is 3", NFP, rx(r"(\$define NF\$LE\.LOCKED\s+)4", r"\g<1>3"))
# ---- the handler: RELEASE and the quiet object
mut("act.release asks the mode", NFP, "   opname = 'release'\n   release.all", "   gosub mode.now\n   opname = 'release'\n   release.all")
mut("act.release refuses in a transaction", NFP, "   opname = 'release'\n   release.all", "   opname = 'release'\n   if system(SYS$TRANS_LEVEL) # 0 then return\n   release.all")
mut("act.release audits", NFP, "   obj->release(nf.h.fno(hx), id)\n", "   void kernel(K$AUDIT, 'netfile release server=' : srvname)\n   obj->release(nf.h.fno(hx), id)\n")
mut("act.release does not take 0 for every server", NFP, "      if len(a) <= 9 then release.all = (a + 0 = 0)", "      if len(a) <= 9 then release.all = @false")
mut("release.every includes read-mode handles", NFP, "nf.h.slot(hy) = sx and nf.h.mode(hy) = 'write'", "nf.h.slot(hy) = sx")
mut("a lost RELEASE is an error", NFP, "   obj->release(nf.h.fno(hx), id)\n   gosub after.rq\n   nf.requests += 1\n   if rq.lost then gosub drop.conn", "   obj->release(nf.h.fno(hx), id)\n   gosub after.rq\n   nf.requests += 1\n   if rq.lost then gosub lost.fail")
mut("a RELEASE of a long id is sent", NFP, "   if len(id) > MAX.ID.LEN then\n      fail.num = 11503 ; fail.a1 = srvname ; fail.a2 = 'too long'\n      gosub fail\n      return\n   end\n   if vartype", "   if vartype")
mut("the object is not quiet", NFP, "   obj->quiet = @true\n", "")
mut("the object is made quiet after the bound is set", NFP, "   obj->quiet = @true\n   obj->maxpacket = NF$MAX.PACKET\n   gosub request.limits\n   obj->settimeout(req.ms)\n", "   obj->maxpacket = NF$MAX.PACKET\n   gosub request.limits\n   obj->settimeout(req.ms)\n   obj->quiet = @true\n")
mut("a READ answered with ON ERROR is not an error", NFP, rx(r"case e = 1\n", "case e = 9\n"))
mut("a SELECT answered with ON ERROR is not an error", NFP, "   if e = 1 then\n      gosub on.error.text", "   if e = 9 then\n      gosub on.error.text")
mut("a second object is made for a write", NFP, lambda t: t + "\n   obj2 = object('!sdclient')\n")
# ---- the handler: the audit
mut("the write audit is in capitals", NFP, "'netfile write server='", "'NETFILE WRITE server='")
mut("the delete audit names the id", NFP, "aud.line = 'netfile delete server=' : srvname : ' file=' : nf.h.file(hx)", "aud.line = 'netfile delete server=' : srvname : ' file=' : nf.h.file(hx) : ' id=' : id")
mut("the write audit names the record", NFP, "aud.line = 'netfile write server=' : srvname : ' file=' : nf.h.file(hx)", "aud.line = 'netfile write server=' : srvname : ' file=' : nf.h.file(hx) : ' record=' : c")
mut("CLEARFILE is audited once only", NFP, "      void kernel(K$AUDIT, 'netfile clear server=' : srvname : ' file=' : nf.h.file(hx))", "      aud.k = 'c' ; aud.line = 'netfile clear server=' : srvname : ' file=' : nf.h.file(hx) ; gosub audit.once")
mut("a change names the credential in the audit", NFP, "aud.line = 'netfile write server=' : srvname : ' file=' : nf.h.file(hx)", "aud.line = 'netfile write server=' : srvname : ' file=' : nf.h.file(hx) : ' pin=' : pin")
# ---- the kernel: netfiles.c
mut("net_gate lets a read-mode handle through", NFC, edit_func("net_gate", r"if \(!fvar->access\.net\.write \|\| \(fvar->flags & FV_RDONLY\)\) \{", "if (0) {"))
mut("net_gate ignores FV_RDONLY", NFC, edit_func("net_gate", r" \|\| \(fvar->flags & FV_RDONLY\)", ""))
mut("net_gate does not ask the edit gate for NETG_ADMIN", NFC, edit_func("net_gate", r" \|\| \(kind == NETG_ADMIN\)", ""))
mut("net_gate tests the transaction on the local txn_id", NFC, edit_func("net_gate", r"process\.txn_id != 0", "txn_id != 0"))
mut("net_gate refuses a transaction with another status", NFC, edit_func("net_gate", r"MSG_TXN, -ER_TXN", "MSG_TXN, -ER_PERM"))
mut("net_gate does not refuse a transaction", NFC, edit_func("net_gate", r"if \(process\.txn_id != 0\) \{", "if (0) {"))
mut("net_gate does not ask the edit gate", NFC, edit_func("net_gate", r"if \(\(kind == NETG_WRITE\) \|\| \(kind == NETG_DELETE\) \|\| \(kind == NETG_CLEAR\) \|\| \(kind == NETG_ADMIN\)\) \{", "if (0) {"))
mut("net_gate asks the edit gate for a lock", NFC, edit_func("net_gate", r"\(kind == NETG_ADMIN\)\) \{", "(kind == NETG_ADMIN) || (kind == NETG_LOCK)) {"))
mut("net_gate does not exempt an $internal caller", NFC, edit_func("net_gate", r" && !\(process\.program\.flags & HDR_INTERNAL\)", ""))
mut("net_gate does not exempt the administrator", NFC, edit_func("net_gate", r" && !MY_ADMIN\(\)", ""))
mut("net_gate refuses the edit gate with another status", NFC, edit_func("net_gate", r"net_raise\(-ER_PERM,", "net_raise(-ER_NETWORK,"))
mut("net_gate names the dictionary message for every kind", NFC, edit_func("net_gate", r"11404 \+ ek", "11406"))
mut("net_gate raises the edit refusal even with ON ERROR", NFC, edit_func("net_gate", r"net_raise\(-ER_PERM, op_flags & P_ON_ERROR\)", "net_raise(-ER_PERM, 0)"))
mut("net_gate leaves process.op_flags changed", NFC, edit_func("net_gate", r"  process\.op_flags = entry;\n  return 0;", "  return 0;"))
mut("net_gate runs BASIC", NFC, edit_func("net_gate", r"  int st;\n", "  int st;\n  net_flush_pending();\n"))
mut("net_gate asks the edit kind of the wrong place", NFC, edit_func("net_gate", r"ek = fvar->access\.net\.edit_kind;", "ek = EDIT_VOC;"))
mut("net_change_op does not drop the cache before the request", NFC, edit_func("net_change_result",r"  if \(handle > 0\)\n    net_cache_drop\(handle\);\n\n  net_was_locked", "  net_was_locked"))
mut("net_change_op drops the cache after the raise", NFC, edit_func("net_change_result",r"  if \(handle > 0\)\n    net_cache_drop\(handle\);\n\n  if \(status < 0\)\n    return net_raise\(status, entry\);",
                                                       "  if (status < 0)\n    return net_raise(status, entry);\n  if (handle > 0)\n    net_cache_drop(handle);"))
mut("net_change_op drops the whole cache", NFC, edit_func("net_change_result",r"net_cache_drop\(handle\);", "net_cache_drop(0);", count=2))
mut("net_change_op trusts the server's status", NFC, edit_func("net_change_result",r"  if \(!busy\)\n    process\.status = 0;", ""))
mut("net_change_op takes an ELSE for a success", NFC, edit_func("net_change_result",r"if \(\(status > 0\) && !busy\) \{", "if (0) {"))
mut("net_change_op sends the request again", NFC, edit_func("net_change_result",r"  busy = lock_op && net_was_locked;", "  busy = lock_op && net_was_locked;\n  if (status < 0)\n    status = net_op_ex(fvar, op, b, blen, c, clen, chain, use_chain, 0, lock_op, TRUE, &out);"))
mut("net_change_op does not pass the server's status on", NFC, edit_func("net_change_result",r"lock_op, TRUE, &out\)", "lock_op, FALSE, &out)"))
mut("net_answer understands the answer 4 for any statement", NFC, edit_func("net_answer", r"if \(!lock_ok\) \{", "if (0) {"))
mut("net_answer forgets the holder", NFC, edit_func("net_answer", r"      process\.status = rc->status;\n      return ER_LCK;", "      return ER_LCK;"))
mut("net_error_status passes the status for every statement", NFC, edit_func("net_error_status", r"if \(pass_status\)", "if (1)"))
mut("net_passed_status loses ER_NOLOCK", NFC, edit_func("net_passed_status", r"    case ER_NOLOCK:\n", ""))
mut("net_passed_status loses ER_MAXRLOCK", NFC, edit_func("net_passed_status", r"    case ER_MAXRLOCK:\n", ""))
mut("net_passed_status passes a status as positive", NFC, edit_func("net_passed_status", r"      return -s;", "      return s;"))
mut("net_op passes the status", NFC, edit_func("net_op", r"FALSE, FALSE, out\)", "FALSE, TRUE, out)"))
mut("net_check_lock does not pass the status (its request is net_lock_code's since S.72)", NFC, edit_func("net_lock_code", r"FALSE, TRUE, &out\)", "FALSE, FALSE, &out)"))
mut("net_parse_rc takes any non-zero mode for write", NFC, edit_func("net_parse_rc", r"\(atoi\(num\) == 1\)", "(atoi(num) != 0)"))
mut("net_parse_rc does not read field 7", NFC, edit_func("net_parse_rc", r"  \(void\)net_field\(buf, 7, num, sizeof\(num\)\);\n", "  num[0] = '1'; num[1] = '\\0';\n"))
mut("net_parse_rc refuses the answer 4", NFC, edit_func("net_parse_rc", r" && \(rc->result != NF_RC_LOCKED\)", ""))
mut("net_write flattens the record", NFC, edit_func("net_write", r"id_len, \"\", 0, rec, TRUE, FALSE\)", "id_len, \"\", 0, NULL, FALSE, FALSE)"))
mut("net_call_core does not count its reference to the chain", NFC, edit_func("net_call_core", r"    if \(cchain != NULL\)\n      \(cchain->ref_ct\)\+\+;\n", ""))
mut("net_call_core flattens the chain", NFC, edit_func("net_call_core", r"  if \(use_chain\) \{\n", "  if (use_chain) {\n    (void)k_get_c_string(NULL, NULL, 0);\n"))
mut("net_write accepts an id of 64", NFC, edit_func("net_write", r"id_len > NET_ID_MAX", "id_len > 64"))
mut("net_delete accepts an empty id", NFC, edit_func("net_delete", r"\(id_len < 1\) \|\| ", ""))
mut("net_lock waits on the server", NFC, edit_func("net_lock", r'update \? "u" : "l"', 'update ? "uw" : "lw"'))
mut("net_lock_step does not sleep (the wait is net_lock_result's since S.72)", NFC, edit_func("net_lock_result", r"  Sleep\(250\);\n", ""))
mut("net_lock_step does not run the opcode again", NFC, edit_func("net_lock_result", r"  pc = retry_pc;\n", ""))
mut("net_lock_step leaves process.op_flags set after a lock", NFC, edit_func("net_lock_step", r"  st = net_lock\(fvar, id, id_len, update\);\n  process\.op_flags = 0;", "  st = net_lock(fvar, id, id_len, update);"))
mut("net_lock_step ignores the LOCKED clause", NFC, edit_func("net_lock_result", r"if \(op_flags & P_LOCKED\) \{", "if (0) {"))
mut("net_lock_step raises with ON ERROR", NFC, edit_func("net_lock_step", r"process\.op_flags = op_flags & P_ON_ERROR;", "process.op_flags = 0;"))
mut("net_lock_step loses the holder", NFC, edit_func("net_lock_result", r"holder = process\.status;", "holder = 0;"))
mut("net_lock_step does not process events", NFC, edit_func("net_lock_result", r"    process_events\(\);", "    ;"))
mut("net_release raises", NFC, edit_func("net_release", r"memcpy\(net_msg, msg_keep, sizeof\(net_msg\)\);", "(void)net_raise(-ER_NETWORK, entry);"))
mut("net_release forgets the status", NFC, edit_func("net_release", r"  process\.status = status_keep;\n", ""))
mut("net_release sends an id over NET_ID_MAX", NFC, edit_func("net_release", r"  if \(id_len > NET_ID_MAX\)\n    return;[^\n]*\n", ""))
mut("net_release_all ignores net_used_write", NFC, edit_func("net_release_all", r"  if \(!net_used_write\)\n    return;\n", ""))
mut("net_open_work never sets net_used_write", NFC, edit_func("net_open_work", r"    net_used_write = TRUE;", "    ;"))
mut("net_close_all keeps net_used_write", NFC, edit_func("net_close_all", r"  net_used_write = FALSE;\n", ""))
mut("net_flush_closes sends without a queue", NFC, edit_func("net_flush_closes", r"  if \(net_pending_ct == 0\)\n    return;\n\n", ""))
mut("net_flush_closes forgets the status", NFC, edit_func("net_flush_closes", r"  process\.status = status_keep;\n", ""))
mut("net_open_work: every handle is write", NFC, edit_func("net_open_work", r"rc\.mode_write \? 1 : 0", "1"))
mut("net_open_work: a write handle is read only too", NFC, edit_func("net_open_work", r"  if \(!fvar->access\.net\.write\)\n    fvar->flags \|= FV_RDONLY;", "  fvar->flags |= FV_RDONLY;"))
mut("net_open_work: a read handle is not read only", NFC, edit_func("net_open_work", r"  if \(!fvar->access\.net\.write\)\n    fvar->flags \|= FV_RDONLY;\n", ""))
mut("net_open_work: no edit kind", NFC, edit_func("net_open_work", r"  fvar->access\.net\.edit_kind = \(u_char\)edit_kind_of_net_name\(file\);\n", ""))
mut("net_open_work: the edit kind is that of the server name", NFC, edit_func("net_open_work", r"edit_kind_of_net_name\(file\)", "edit_kind_of_net_name(server)"))
mut("net_read: a write-mode handle is cached", NFC, edit_func("net_read", r" && !fvar->access\.net\.write", ""))
mut("net_refuse says read only on a write handle", NFC, edit_func("net_refuse", r"write \? MSG_UNAVAILABLE : MSG_READ_ONLY", "MSG_READ_ONLY"))
mut("net_refuse says not available on a read handle", NFC, edit_func("net_refuse", r"write \? MSG_UNAVAILABLE : MSG_READ_ONLY", "MSG_UNAVAILABLE"))
mut("MSG_UNAVAILABLE is 11512", NFC, rx(r"(#define MSG_UNAVAILABLE )11511", r"\g<1>11512"))
mut("MSG_TXN is 11509", NFC, rx(r"(#define MSG_TXN )11510", r"\g<1>11509"))
mut("sd.h: NETG_LOCK is 5", "sd.h", rx(r"(#define NETG_LOCK )4", r"\g<1>5"))
mut("sd.h: NET_ID_MAX is 64", "sd.h", rx(r"(#define NET_ID_MAX )63", r"\g<1>64"))
mut("sd.h: net_lock_step loses retry_pc", "sd.h", "bool update, u_int16_t op_flags, u_char * retry_pc);", "bool update, u_int16_t op_flags);")
mut("sd.h: net_write takes a flat record", "sd.h", "int net_write(FILE_VAR * fvar, char * id, int16_t id_len, STRING_CHUNK * rec, bool keep_lock);", "int net_write(FILE_VAR * fvar, char * id, int16_t id_len, char * rec, bool keep_lock);")
mut("sd.h loses net_gate", "sd.h", "int net_gate(FILE_VAR * fvar, int kind, u_int16_t op_flags, const char * what);\n", "")
mut("sd.h loses edit_kind_of_net_name", "sd.h", rx(r"int edit_kind_of_net_name\(const char \* name\);[^\n]*\n", ""))
mut("descr.h: the union member loses the write flag", "descr.h", rx(r"      u_char write;[^\n]*\n", ""))
mut("descr.h: the edit kind comes before the write flag", "descr.h", lambda t: t.replace("      u_char write;", "      u_char edit_kind_tmp;", 1).replace("      u_char edit_kind;", "      u_char write;", 1).replace("      u_char edit_kind_tmp;", "      u_char edit_kind;", 1))
mut("descr.h: the write flag is a word", "descr.h", rx(r"      u_char write;", "      int32_t write;"))
# ---- the kernel: op_dio3.c, op_lock.c, op_dio2.c
mut("refuse_net_file does not ask net_gate", D3, edit_func("refuse_net_file", r"st = net_gate\(fvar, kind, op_flags, what\);", "st = net_refuse(fvar, what);"))
mut("refuse_net_file loses the kind", D3, edit_func("refuse_net_file", r"net_gate\(fvar, kind, op_flags, what\)", "net_gate(fvar, NETG_WRITE, op_flags, what)"))
mut("refuse_net_file refuses everything", D3, edit_func("refuse_net_file", r"  if \(st == 0\)\n    return FALSE;\n\n", ""))
mut("op_write: the NET arm takes the lock locally", D3, edit_func("op_write", r"net_pre_change_lock\(fvar, id, id_len, op_flags, retry_pc\)", "lock_record(fvar, id, id_len, TRUE, 0, FALSE)"))
mut("op_write: an id over NET_ID_MAX is sent", D3, edit_func("op_write", r" \|\| \(id_len > NET_ID_MAX\)", ""))
mut("op_write: the record is sent flat", D3, edit_func("op_write", r"net_write\(fvar, id, id_len, src_descr->data\.str\.saddr, keep_lock\)", "net_write(fvar, id, id_len, NULL, keep_lock)"))
mut("op_write: the record is not made a string", D3, edit_func("op_write", r"    k_get_string\(src_descr\);\n\n    if \(!valid_id", "    if (!valid_id"))
mut("op_write: the status of the call is lost", D3, edit_func("op_write", r"    process\.status = net_st;\n    goto exit_op_write;", "    goto exit_op_write;"))
mut("op_write: the retry point is not taken", D3, edit_func("op_write", r"u_char \*retry_pc = op_pc;", "u_char *retry_pc = NULL;"))
mut("op_write: the opcode sets pc itself", D3, edit_func("op_write", r"    process\.op_flags = op_flags & P_ON_ERROR;\n    net_st = net_write", "    pc = retry_pc;\n    process.op_flags = op_flags & P_ON_ERROR;\n    net_st = net_write"))
mut("op_delete: the retry point is taken from pc", D3, edit_func("op_delete", r"u_char \*retry_pc = op_pc;", "u_char *retry_pc = pc;"))
mut("op_delete: an id over NET_ID_MAX is sent", D3, edit_func("op_delete", r"    if \(id_len > NET_ID_MAX\) \{\n      process\.status = -ER_IID;\n      goto exit_op_delete;\n    \}\n", ""))
mut("op_delete: the NET arm checks the local lock", D3, edit_func("op_delete", r"    switch \(net_pre_change_lock", "    (void)check_lock(fvar, id, id_len, 0);\n    switch (net_pre_change_lock"))
mut("op_delete: a keep_lock DELETE is a plain one", D3, edit_func("op_delete", r"net_delete\(fvar, id, id_len, keep_lock\)", "net_delete(fvar, id, id_len, FALSE)"))
mut("op_delete: the NET arm comes before the empty-id test", D3, edit_func("op_delete", r"  if \(id_len <= 0\) \{\n    process\.status = -ER_IID;\n    goto exit_op_delete; [^\n]*\n  \}\n", ""))
mut("op_clrfile: the NET arm reads the file table", D3, edit_func("op_clrfile", r"    net_st = net_clear\(fvar\);", "    net_st = net_clear(fvar);\n    (void)FPtr(fvar->file_id);"))
mut("op_clrfile: the status of the call is lost", D3, edit_func("op_clrfile", r"    process\.status = net_st;\n", ""))
mut("net_pre_change_lock: MUSTLOCK is not honoured", D3, edit_func("net_pre_change_lock", r"  if \(pcfg\.must_lock\) \{", "  if (0) {"))
mut("net_pre_change_lock: AUTOLOCK does not wait", D3, edit_func("net_pre_change_lock", r"      case NET_LOCK_WAIT:\n        return NETL_WAIT;", "      case NET_LOCK_WAIT:\n        return NETL_GO;"))
mut("net_pre_change_lock: AUTOLOCK takes a shared lock", D3, edit_func("net_pre_change_lock", r"net_lock_step\(fvar, id, id_len, TRUE,", "net_lock_step(fvar, id, id_len, FALSE,"))
mut("net_pre_change_lock: AUTOLOCK keeps the LOCKED clause", D3, edit_func("net_pre_change_lock", r"op_flags & ~P_LOCKED", "op_flags"))
mut("net_pre_change_lock: a missing lock is another status", D3, edit_func("net_pre_change_lock", r"process\.status = -ER_NOLOCK;\n      return NETL_FAIL;\n    \}\n    if \(st < 0\)", "process.status = -ER_PERM;\n      return NETL_FAIL;\n    }\n    if (st < 0)"))
mut("op_write does not wait for an AUTOLOCK", D3, edit_func("op_write", r"      case NETL_WAIT:\n        return;", "      case NETL_WAIT:\n        break;"))
mut("read_record: a NET_FILE locks locally", D3, edit_func("read_record", r"\(op_flags & P_REC_LOCKS\) && \(fvar->type == NET_FILE\)\) \{\n", "(op_flags & P_REC_LOCKS) && (fvar->type == 99)) {\n"))
mut("read_record: a busy remote lock is not waited for", D3, edit_func("read_record", r"        case NET_LOCK_WAIT:\n          return;", "        case NET_LOCK_WAIT:\n          break;"))
mut("read_record: the operands are not found again", D3, edit_func("read_record", r"      net_reload_read_operands\(&rid_descr, &fvar_descr, &tgt_descr\);\n      if \(!matread\)\n        str_descr = tgt_descr;\n", ""))
mut("read_record: LOCKED does not give ER_LCK", D3, edit_func("read_record", r"        case NET_LOCK_LOCKED:\n          status = ER_LCK;", "        case NET_LOCK_LOCKED:\n          status = 0;"))
mut("read_record: the gate is asked as a write", D3, edit_func("read_record", r", NETG_LOCK\)\) \{", ", NETG_WRITE)) {"))
mut("read_record: the retry point is not taken", D3, edit_func("read_record", r"u_char \*retry_pc = op_pc;", "u_char *retry_pc = NULL;"))
mut("op_readv: a plain READV is gated", D3, edit_func("op_readv", r"\(op_flags & P_REC_LOCKS\) && refuse_net_file\(", "refuse_net_file("))
mut("op_readv: READVU does not lock", D3, edit_func("op_readv", r"        if \(op_flags & P_REC_LOCKS\) \{\n          net_st = net_lock_step", "        if (0) {\n          net_st = net_lock_step"))
mut("op_readv: a busy lock overwrites the holder", D3, edit_func("op_readv", r"          if \(net_st != ER_LCK\)\n            process\.status = net_st;", "          process.status = net_st;"))
mut("op_readv: a wait does not leave", D3, edit_func("op_readv", r"            case NET_LOCK_WAIT:\n              return;", "            case NET_LOCK_WAIT:\n              break;"))
mut("op_readv: the record is read after a busy lock", D3, edit_func("op_readv", r"        if \(net_st == 0\) \{\n          process\.op_flags = op_flags & P_ON_ERROR;", "        if (1) {\n          process.op_flags = op_flags & P_ON_ERROR;"))
mut("op_lockrec: a read-mode handle reaches net_lock_step", OLK, edit_func("op_lockrec", r"if \(!fvar->access\.net\.write \|\| \(fvar->flags & FV_RDONLY\)\)", "if (0)"))
mut("op_lockrec: the gate is not asked", OLK, edit_func("op_lockrec", r"status = net_gate\(fvar, NETG_LOCK, op_flags, update \? \"RECORDLOCKU\" : \"RECORDLOCKL\"\);", "status = 0;"))
mut("op_lockrec: a busy record pushes 0", OLK, edit_func("op_lockrec", r"          status = ER_LCK;", "          status = 0;"))
mut("op_lockrec: a wait does not return", OLK, edit_func("op_lockrec", r"        case NET_LOCK_WAIT: [^\n]*\n          return;", "        case NET_LOCK_WAIT:\n          break;"))
mut("op_lockrec: the retry point is not taken", OLK, edit_func("op_lockrec", r"u_char\* retry_pc = op_pc;", "u_char* retry_pc = NULL;"))
mut("op_lockrec: the remote wait uses pc--", OLK, edit_func("op_lockrec", r"        case NET_LOCK_WAIT: [^\n]*\n          return;", "        case NET_LOCK_WAIT:\n          pc--;\n          return;"))
mut("op_lockrec: the flags are left set", OLK, edit_func("op_lockrec", r"      process\.op_flags = 0;\n    \}\n\n    k_dismiss\(\);", "    }\n\n    k_dismiss();"))
mut("op_release: a read-mode handle is not refused", OLK, edit_func("op_release", r"    if \(!fvar->access\.net\.write\)\n      net_refuse\(fvar, \"RELEASE\"\);", ""))
mut("op_release: the transaction is not looked at", OLK, edit_func("op_release", r"process\.txn_id == 0 && id_len > 0 && id_len <= NET_ID_MAX", "id_len > 0 && id_len <= NET_ID_MAX"))
mut("op_release: an id over NET_ID_MAX is sent", OLK, edit_func("op_release", r" && id_len <= NET_ID_MAX", ""))
mut("op_release: a failing RELEASE raises", OLK, edit_func("op_release", r"      net_release\(fvar, id, id_len\);", "      net_release(fvar, id, id_len);\n    (void)net_raise(-ER_NETWORK, 0);"))
mut("op_rlsfile: the transaction is not looked at", OLK, edit_func("op_rlsfile", r"    if \(process\.txn_id == 0\)\n      net_release\(fvar, NULL, 0\);", "    net_release(fvar, NULL, 0);"))
mut("op_rlsfile: a read-mode handle is not refused", OLK, edit_func("op_rlsfile", r"    if \(!fvar->access\.net\.write\)\n      net_refuse\(fvar, \"RELEASE\"\);", ""))
mut("op_rlsall never lets the remote locks go", OLK, edit_func("op_rlsall", r"    net_release_all\(\);[^\n]*\n", ""))
mut("op_rlsall lets them go outside the transaction test", OLK, edit_func("op_rlsall", r"  if \(process\.txn_id == 0\) \{\n    net_release_all\(\);[^\n]*\n", "  net_release_all();\n  if (process.txn_id == 0) {\n"))
mut("lock_record loses its NET_FILE backstop", OLK, edit_func("lock_record", r"  if \(fvar->type == NET_FILE\)", "  if (0)"))
mut("FILEINFO FL$READONLY is always 1 for a NET_FILE", D2, edit_func("op_fileinfo", r"n = \(\(fvar->flags & FV_RDONLY\) != 0\);", "n = 1;"))
mut("FILEINFO FL$SETRDONLY is open to any program", D2, edit_func("op_fileinfo", r"          if \(process\.program\.flags & HDR_INTERNAL\)\n            fvar->flags \|= FV_RDONLY;", "          fvar->flags |= FV_RDONLY;"))
mut("FILEINFO FL$SETRDONLY does nothing", D2, edit_func("op_fileinfo", r"            fvar->flags \|= FV_RDONLY;", "            ;"))
# ---- op_sh.c, op_kernel.c, CPROC, edit_guard
mut("edit_kind_of_net_name uses the path rule", SH, edit_func("edit_kind_of_net_name", r"return edit_kind_of_name\(name\);", "return edit_kind_of_path(name);"))
mut("edit_kind_of_net_name does not know a dictionary", SH, edit_func("edit_kind_of_net_name", r"strncasecmp\(name, \"dict \", 5\) == 0", "0"))
mut("edit_kind_of_net_name takes dict without the space", SH, edit_func("edit_kind_of_net_name", r"\"dict \", 5\)", "\"dict\", 4)"))
mut("K_EDIT_OK of a file variable is open", KRN, "            result.data.value = ((edit_fkind == EDIT_NONE) || edit_permitted(edit_fkind)) ? 1 : 0;", "            result.data.value = 1;")
mut("K_EDIT_OK of another file variable is open", KRN, "          else if (edit_fvar->type == NET_FILE)\n            result.data.value = ((edit_fkind", "          else\n            result.data.value = ((edit_fkind")
mut("K_EDIT_KIND of a file variable answers 0", KRN, "        } else\n          result.data.value = edit_fkind;", "        } else\n          result.data.value = 0;")
mut("K_EDIT_OK does not exempt the administrator", KRN, "          if (MY_ADMIN())\n            result.data.value = 1;\n          else if (edit_fvar->type == NET_FILE)", "          if (edit_fvar->type == NET_FILE)")
mut("K_NET -2 is open to any program", KRN, "if ((n == -2) && (process.program.flags & HDR_INTERNAL)) {", "if (n == -2) {")
mut("K_NET -2 never flushes", KRN, "        net_flush_closes();\n", "")
mut("K_NET -2 loses the caller's STATUS()", KRN, "        n = process.status;\n        net_flush_closes();\n        process.status = n;\n", "        net_flush_closes();\n")
mut("K_NET -2 answers 0", KRN, "        process.status = n;\n        result.data.value = MY_GATE(UG_NET);\n        break;", "        process.status = n;\n        result.data.value = 0;\n        break;")
mut("CPROC forgets the flush", CPR, drop_line(r"void kernel\(K\$NET, -2\)"))
mut("CPROC flushes before the OS path cache", CPR, rx(r"(   i = ospath\(\"\", os\$flush\.cache\)\n)(   void kernel\(K\$NET, -2\)[^\n]*\n)", r"\2\1"))
mut("CPROC flushes twice", CPR, lambda t: t + "\n   void kernel(K$NET, -2)\n")
mut("CPROC sets the gate to -2", CPR, "void kernel(K$NET, -2)", "void kernel(K$NET, 2)")
mut("edit_guard asks the administrator first", EGD, rx(r"(   p = fileinfo\(f, FL\$PATH\)\n   if p = '' then\n(?:\*[^\n]*\n)*)(      if fileinfo\(f, FL\$NETFILE\) then.*?\n      end\n)(      if kernel\(K\$ADMINISTRATOR, -1\) then return @true\n)", r"\1\3\2", re.S))
mut("edit_guard does not know a remote file", EGD, "      if fileinfo(f, FL$NETFILE) then", "      if 0 then")
mut("edit_guard asks for a pathname", EGD, "         if kernel(K$EDIT.OK, f) then return @true", "         if kernel(K$EDIT.OK, p) then return @true")
mut("edit_guard shows the old 11404 + kind text for a remote file", EGD, "         display edit_msg(kind) ;* 11405 VOC", "         display sysmsg(11404 + kind) ;* 11405 VOC")
mut("edit_guard lets a remote file through", EGD, "         display edit_msg(kind) ;* 11405 VOC, 11406 dictionary, 11407 program file, 11513 shared record, 11514 shared structure\n         return @false", "         display edit_msg(kind) ;* 11405 VOC, 11406 dictionary, 11407 program file, 11513 shared record, 11514 shared structure\n         return @true")
# ---- the class
mut("sdclient: quiet is not public", SCL, rx(r"       quiet,[^\n]*\n", ""))
mut("sdclient: quiet starts true", SCL, "   quiet = @false\n", "   quiet = @true\n")
mut("sdclient: LastError starts 0", SCL, "   LastError = -1\n   LastText = ''\n   maxpacket = 0\nend", "   LastError = 0\n   LastText = ''\n   maxpacket = 0\nend")
mut("sdclient: message.pair does not reset LastError", SCL, "   LastError = -1\n   LastText = ''\n   if (write.packet(pkt.type, pkt)) then", "   LastText = ''\n   if (write.packet(pkt.type, pkt)) then")
mut("sdclient: get.response forgets LastError", SCL, " LastError = server.error\n", "")
# ---- the ceiling on a reply (19 Oct 26, K8c)
mut("sdclient: read.packet does not test a length below the header", SCL, "   if pkt.bytes < 10 then return @false\n", "")
mut("sdclient: read.packet does not test the ceiling", SCL, "   if maxpacket > 0 and pkt.bytes > maxpacket then return @false\n", "")
mut("sdclient: read.packet tests the length after it has read the header's error and status",     # 20 Oct 26 (S.73 item 2): they are kept in hdr.error / hdr.status until the body is in
    SCL, lambda t: t.replace("   if pkt.bytes < 10 then return @false\n   if maxpacket > 0 and pkt.bytes > maxpacket then return @false\n", "", 1).replace(
        "   hdr.status = oconv(pkt.header[7,4], 'ILL')\n", "   hdr.status = oconv(pkt.header[7,4], 'ILL')\n   if pkt.bytes < 10 then return @false\n   if maxpacket > 0 and pkt.bytes > maxpacket then return @false\n", 1))
mut("sdclient: read.packet tests the ceiling with the wrong comparison", SCL, "if maxpacket > 0 and pkt.bytes > maxpacket then return @false", "if maxpacket > 0 and pkt.bytes < maxpacket then return @false")
mut("sdclient: maxpacket starts at 1 (every reply fails for its users)", SCL, "   LastText = ''\n   maxpacket = 0\nend", "   LastText = ''\n   maxpacket = 1\nend")
mut("sdclient: maxpacket is not declared as a public property", SCL, "       LastText,        ;* The payload of the last ON ERROR reply\n       maxpacket        ;* The longest reply, header included, this object will read: a longer one fails the call.  0 = no ceiling (the default).  19 Oct 26, K8c",
    "       LastText         ;* The payload of the last ON ERROR reply")
mut("netfile: the ceiling is not set", NFP, "   obj->maxpacket = NF$MAX.PACKET\n", "")
mut("netfile: the ceiling is set after the timeout", NFP, "   obj->maxpacket = NF$MAX.PACKET\n   gosub request.limits\n   obj->settimeout(req.ms)\n", "   gosub request.limits\n   obj->settimeout(req.ms)\n   obj->maxpacket = NF$MAX.PACKET\n")
mut("netfile: the ceiling is 3000000000 (more than a 32 bit count holds)", NFP, rx(r"(\$define NF\$MAX\.PACKET\s+)1073741832", r"\g<1>3000000000"))
mut("netfile: the ceiling is 100 MB (it would refuse a legal record)", NFP, rx(r"(\$define NF\$MAX\.PACKET\s+)1073741832", r"\g<1>104857600"))
mut("sdclient: get.response sets LastError after the SV$ERROR test", SCL, " LastError = server.error\n if server.error = SV$ON.ERROR then LastText = in.pkt\n\n if server.error = SV$ERROR then", " if server.error = SV$ON.ERROR then LastText = in.pkt\n\n if server.error = SV$ERROR then")
mut("sdclient: the abort of WRITE is not guarded", SCL, "         if server.error = SV$ON.ERROR and not(quiet) then\n            abort 'WRITE generated an abort event'", "         if server.error = SV$ON.ERROR then\n            abort 'WRITE generated an abort event'")
mut("sdclient: the abort of WRITEU is not guarded", SCL, "         if server.error = SV$ON.ERROR and not(quiet) then\n            abort 'WRITEU generated", "         if server.error = SV$ON.ERROR then\n            abort 'WRITEU generated")
mut("sdclient: the abort of DELETE is not guarded", SCL, "      if server.error = SV$ON.ERROR and not(quiet) then\n         abort 'DELETE generated an abort event'", "      if server.error = SV$ON.ERROR then\n         abort 'DELETE generated an abort event'")
mut("sdclient: the abort of RECORDLOCK is not guarded", SCL, "      if server.error = SV$ON.ERROR and not(quiet) then\n         abort 'RECORDLOCK", "      if server.error = SV$ON.ERROR then\n         abort 'RECORDLOCK")
mut("sdclient: the abort of RELEASE is not guarded", SCL, "      if server.error = SV$ON.ERROR and not(quiet) then\n         abort 'RELEASE", "      if server.error = SV$ON.ERROR then\n         abort 'RELEASE")
mut("sdclient: the abort of READ is not guarded", SCL, "case server.error = SV$ON.ERROR and not(quiet)\n               abort 'READ", "case server.error = SV$ON.ERROR\n               abort 'READ")
mut("sdclient: the abort of CLEARFILE is not guarded", SCL, "         if server.error = SV$ON.ERROR and not(quiet) then\n            abort 'CLEARFILE", "         if server.error = SV$ON.ERROR then\n            abort 'CLEARFILE")
mut("sdclient: an unrelated abort is made quiet too", SCL, "         if server.error = SV$ON.ERROR then\n            abort 'CLEARSELECT generated an abort event'", "         if server.error = SV$ON.ERROR and not(quiet) then\n            abort 'CLEARSELECT generated an abort event'")
mut("sdclient: an illegal id aborts when quiet", SCL, "         if quiet then\n            LastError = SV$ON.ERROR\n            return\n         end\n         abort 'Illegal record id'\n      end\n\n      pkt = iconv(fno, 'ISL')\n      pkt := iconv(len(id), 'ISL')\n      pkt := id : data\n\n      if message.pair(SrvrWrite, pkt)",
    "         abort 'Illegal record id'\n      end\n\n      pkt = iconv(fno, 'ISL')\n      pkt := iconv(len(id), 'ISL')\n      pkt := id : data\n\n      if message.pair(SrvrWrite, pkt)")
mut("sdclient: recordlock's wait flag is the old way round", SCL, "         if not(wait) then flags += 2", "         if wait then flags += 2")
mut("sdclient: clearfile sends the wrong request", SCL, "message.pair(SrvrClearfile, pkt)", "message.pair(SrvrClose, pkt)")
mut("sdclient: SrvrClearfile is 32", SCL, rx(r"(\$define SrvrClearfile\s+)31", r"\g<1>32"))
mut("sdclient: clearfile aborts when quiet", SCL, "         if server.error = SV$ON.ERROR and not(quiet) then\n            abort 'CLEARFILE", "         if server.error = SV$ON.ERROR then\n            abort 'CLEARFILE")
# ---- the suite, the map, the history
mut("the suite defines nfw as read", NFSUITE, 'alA, mode="write")\n    define("nfwb"', 'alA)\n    define("nfwb"')
mut("the suite defines nfa as write", NFSUITE, 'define("nfa", A.port, pa, "zznhon,zznhoff", alA)', 'define("nfa", A.port, pa, "zznhon,zznhoff", alA, mode="write")')
mut("the suite's lock request waits", NFSUITE, 'struct.pack("<h", 3 if upd else 2)', 'struct.pack("<h", 1 if upd else 0)')
mut("the suite has no lock watcher", NFSUITE, "class LockWatch(", "class LockWatchX(")
mut("the suite's holder is never released", NFSUITE, "                time.sleep(self.delay)\n                self.srv.store.drop_user(self.userno)", "                time.sleep(self.delay)")
mut("the suite's T prefix does nothing", NFSUITE, "      if nm[1,1] = 'T' then\n         intxn = @true", "      if nm[1,1] = 'T' then\n         intxn = @false")
mut("the suite's marks in an id are not converted", NFSUITE, "b = change(b, '<F>', @fm) ; ", "")
mut("the suite runs hwrite after kernel", NFSUITE, '("hwrite", hwrite_section), ("kwrite", kwrite_section), ("wgroup", wgroup_section),\n            ("kernel", kernel_section), ("mustlock", mustlock_section), ("gaps", gaps_section))', '("kernel", kernel_section), ("hwrite", hwrite_section), ("kwrite", kwrite_section), ("wgroup", wgroup_section), ("mustlock", mustlock_section), ("gaps", gaps_section))')
mut("the suite's KALLOWED changes", NFSUITE, "KALLOWED = {47, 48, 3, 4, 5, 6, 1}  ", "KALLOWED = {47, 48, 3, 4, 5, 6, 1, 16}  ")
mut("the suite's write wire allows request 32", NFSUITE, "KWALLOWED = {47, 48, 3, 4, 5, 6, 1, 15, 16, 17, 18, 19, 30, 31, 34}", "KWALLOWED = {47, 48, 3, 4, 5, 6, 1, 15, 16, 17, 18, 19, 30, 31, 32, 34}")
mut("the suite's refusal matrix loses recordlocku", NFSUITE, '    km("recordlocku", "recordlocku f', '    km("recordlockx", "recordlocku f')
mut("the map does not select netfile for op_sh.c", NFMAP, "gplsrc/op_sh.c               : gates sdaccts editgates netfile", "gplsrc/op_sh.c               : gates sdaccts editgates")
mut("the map does not select netfile for op_kernel.c", NFMAP, "editgates net netfile", "editgates net")
mut("the map does not select netfile for cproc", NFMAP, "classinit net netfile", "classinit net")
mut("the map does not select netfile for edit_guard", NFMAP, "sdsys/gpl.bp/edit_guard      : editgates @editors netfile", "sdsys/gpl.bp/edit_guard      : editgates @editors")
mut("the suite loses the hwrite section", NFSUITE, '("hwrite", hwrite_section), ', "")
mut("the suite loses the kwrite section", NFSUITE, '("kwrite", kwrite_section), ', "")
mut("the suite's driver loses WRITEU", NFSUITE, "            op = NF$WRITEU\n", "            op = 14\n")
mut("the suite's driver loses RELEASE", NFSUITE, "            op = NF$RELEASE\n", "            op = 16\n")
mut("the suite's history line for slice 3e is gone", NFSUITE, "# 18 Oct 26 dm  S.65 slice 3e: WRITES AND LOCKS", "# 18 Oct 26 dm  slice 3e: WRITES AND LOCKS")
mut("netfake's history line for slice 3e is gone", "netfake.py", "18 Oct 26 dm  S.65 slice 3e: WRITES AND LOCKS.", "18 Oct 26 dm  slice 3e: WRITES AND LOCKS.")
mut("netfiles.c's history line for slice 3e is gone", "netfiles.c", rx(r"18 Oct 26 dm\s+S\.65 slice 3e", "18 Oct 26 dm  slice 3e"))
mut("op_lock.c's history line for slice 3e is gone", "op_lock.c", rx(r"18 Oct 26 dm\s+S\.65 slice 3e", "18 Oct 26 dm  slice 3e"))
mut("netfile's history line for slice 3e is gone", NFP, rx(r"18 Oct 26 dm\s+S\.65 slice 3e", "18 Oct 26 dm  slice 3e"))

# ---- 20 Oct 26, S.72: FILELOCK, FILEUNLOCK, RECORDLOCKED() and GETLOCKS() of a remote file (S72a to S72q and the checks changed for it) --------------------------------------------
M_S72 = len(M)         # the mutants from here on are S.72's: --selftest --from=<this number> runs them alone (the 18 older ones that no longer applied were re-aimed above, not dropped)
NOREPLY_BEFORE = r"[ ]*obj->ServerStatus = NF\$NOREPLY\n(?=[ ]*obj->%s\()"      # the no-reply mark right before a request of the handler


def afu_gate_late(t):
    """act.fileunlock asks the gate and the connection AFTER the request instead of before it."""
    i = t.find("\nact.fileunlock:")
    blk = "   need.gate = @true ; need.conn = @true ; any.acct = @false ; allow.lost = @false\n   gosub get.handle\n   if failed then return\n"
    j = t.find(blk, i) if i >= 0 else -1
    req = "   obj->fileunlock(nf.h.fno(hx))\n"
    if j < 0 or t.find(req, j) < 0:
        raise KeyError("act.fileunlock's gate block or request not found")
    t = t[:j] + t[j + len(blk):]
    k = t.find(req, i) + len(req)
    return t[:k] + blk + t[k:]


# the handler: act.change's FILELOCK arm and act.fileunlock
mut("S72: the handler's FILELOCK waits on the server", NFP, "obj->filelock(nf.h.fno(hx), @false)", "obj->filelock(nf.h.fno(hx), @true)")
mut("S72: the handler's FILELOCK wait flag is a variable", NFP, "obj->filelock(nf.h.fno(hx), @false)", "obj->filelock(nf.h.fno(hx), upd)")
mut("S72: FILELOCK is sent as a record lock", NFP, "obj->filelock(nf.h.fno(hx), @false)", "obj->recordlock(nf.h.fno(hx), id, @true, @false)")
mut("S72: FILELOCK is sent without the no-reply mark", NFP, rx(NOREPLY_BEFORE % "filelock", ""))
mut("S72: FILEUNLOCK is sent without the no-reply mark", NFP, rx(NOREPLY_BEFORE % "fileunlock", ""))
mut("S72: FILELOCK is not dispatched to act.change", NFP, "op = NF$LOCK or op = NF$FILELOCK\n         gosub act.change", "op = NF$LOCK\n         gosub act.change")
mut("S72: FILEUNLOCK is dispatched to act.change", NFP, rx(r"(case op = NF\$FILEUNLOCK\s*;\s*gosub act\.)fileunlock", r"\1change"))
mut("S72: FILELOCK is a change (a lost reply is 11509)", NFP, "changing = (op # NF$LOCK and op # NF$FILELOCK)", "changing = (op # NF$LOCK)")
mut("S72: a busy file lock is a server error", NFP, "if (op = NF$LOCK or op = NF$FILELOCK) and lerr = NF$LE.LOCKED then", "if op = NF$LOCK and lerr = NF$LE.LOCKED then")
mut("S72: the file lock audit line is written every time", NFP, after("aud.k = 'f'", "gosub audit.once", "void kernel(K$AUDIT, aud.line)"))
mut("S72: the file lock audit line names the id", NFP, "aud.line = 'netfile filelock server=' : srvname : ' file=' : nf.h.file(hx)", "aud.line = 'netfile filelock server=' : srvname : ' file=' : nf.h.file(hx) : ' id=' : id")
mut("S72: the file lock audit line is in capitals", NFP, "'netfile filelock server='", "'NETFILE FILELOCK server='")
mut("S72: the file lock audit shares the write letter", NFP, "aud.k = 'f'", "aud.k = 'w'")
mut("S72: act.fileunlock is not refused for a read-mode handle", NFP, after("\nact.fileunlock:", "   if nf.h.mode(hx) # 'write' then\n      gosub act.refuse\n      return\n   end\n", ""))
mut("S72: act.fileunlock reads the definition now (mode.now)", NFP, after("\nact.fileunlock:", "   if system(SYS$TRANS_LEVEL) # 0 then", "   gosub mode.now\n   if not(mode.ok) then\n      gosub act.refuse\n      return\n   end\n   if system(SYS$TRANS_LEVEL) # 0 then"))
mut("S72: act.fileunlock is not refused in a transaction", NFP, after("\nact.fileunlock:", "if system(SYS$TRANS_LEVEL) # 0 then", "if 0 then"))
mut("S72: act.fileunlock asks the gate AFTER the request", NFP, afu_gate_late)
mut("S72: act.fileunlock is a change (a lost reply is 11509)", NFP, after("\nact.fileunlock:", "   opname = 'fileunlock'\n", "   opname = 'fileunlock'\n   changing = @true\n"))
mut("S72: act.fileunlock is audited", NFP, after("\nact.fileunlock:", "   obj = nf.s.obj(slot)\n", "   obj = nf.s.obj(slot)\n   void kernel(K$AUDIT, 'netfile fileunlock server=' : srvname)\n"))
mut("S72: act.fileunlock forgets rc<8>", NFP, after("\nact.fileunlock:", "   rc<8> = rq.st\n", ""))
mut("S72: act.fileunlock gives rc<8> the wrong value", NFP, after("\nact.fileunlock:", "   rc<8> = rq.st\n", "   rc<8> = lerr\n"))
mut("S72: act.fileunlock sets rc<8> on a lost reply too", NFP, after("\nact.fileunlock:", "   if rq.lost then\n      gosub lost.fail\n", "   if rq.lost then\n      rc<8> = rq.st\n      gosub lost.fail\n"))
mut("S72: act.fileunlock takes the busy answer as a lock", NFP, after("\nact.fileunlock:", "   if rq.err then\n", "   if lerr = NF$LE.LOCKED then\n      gosub rc.locked\n      return\n   end\n   if rq.err then\n"))
mut("S72: act.recordlocked forgets rc<8>", NFP, rx(r"(\nact\.recordlocked:.*?\n)(\*[^\n]*\n)?   rc<8> = rq\.st\n", r"\1", re.S))
mut("S72: act.recordlocked sets rc<8> before the failure exits", NFP, after("\nact.recordlocked:", "   gosub after.rq\n", "   gosub after.rq\n   rc<8> = rq.st\n"))
mut("S72: act.release sets rc<8> too", NFP, after("\nact.release:", "   obj = 0\n   return", "   rc<8> = rq.st\n   obj = 0\n   return"))
mut("S72: the dispatch loses FILEUNLOCK", NFP, rx(r"case op = NF\$FILEUNLOCK\s*;\s*gosub act\.fileunlock\n", ""))
# the codes
mut("S72: netfile.h: NF$FILELOCK is 17", NFHD, rx(r"(\$define\s+NF\$FILELOCK\s+)18", r"\g<1>17"))
mut("S72: netfile.h: NF$FILEUNLOCK is 20", NFHD, rx(r"(\$define\s+NF\$FILEUNLOCK\s+)19", r"\g<1>20"))
mut("S72: netfile.h: NF$FILEUNLOCK is 18 (FILELOCK's)", NFHD, rx(r"(\$define\s+NF\$FILEUNLOCK\s+)19", r"\g<1>18"))
mut("S72: netfiles.c: NF_FILELOCK is 17", NFC, rx(r"(#define\s+NF_FILELOCK\s+)18", r"\g<1>17"))
mut("S72: netfiles.c: NF_FILEUNLOCK is 20", NFC, rx(r"(#define\s+NF_FILEUNLOCK\s+)19", r"\g<1>20"))
mut("S72: netfiles.c: NF_FILEUNLOCK is 13 (STATE's)", NFC, rx(r"(#define\s+NF_FILEUNLOCK\s+)19", r"\g<1>13"))
mut("S72: err.h: ER_NLK is 3013", "err.h", rx(r"(#define\s+ER_NLK\s+)3012", r"\g<1>3013"))
mut("S72: err.h: ER_LCK is 3010", "err.h", rx(r"(#define\s+ER_LCK\s+)3011", r"\g<1>3010"))
# the class
mut("S72: sdclient: SrvrFilelock is 31", SCL, rx(r"(\$define SrvrFilelock\s+)32", r"\g<1>31"))
mut("S72: sdclient: SrvrFileunlock is 34", SCL, rx(r"(\$define SrvrFileunlock\s+)33", r"\g<1>34"))
mut("S72: sdclient: filelock sends the wrong request", SCL, "message.pair(SrvrFilelock, pkt)", "message.pair(SrvrClearfile, pkt)")
mut("S72: sdclient: fileunlock sends the wrong request", SCL, "message.pair(SrvrFileunlock, pkt)", "message.pair(SrvrFilelock, pkt)")
mut("S72: sdclient: filelock always asks the server to wait", SCL, "iconv(if wait then 1 else 0, 'ISL')", "iconv(1, 'ISL')")
mut("S72: sdclient: filelock sends the wait flag as a 32 bit number", SCL, "iconv(if wait then 1 else 0, 'ISL')", "iconv(if wait then 1 else 0, 'ILL')")
mut("S72: sdclient: filelock aborts when quiet", SCL, "if server.error = SV$ON.ERROR and not(quiet) then\n            abort 'FILELOCK", "if server.error = SV$ON.ERROR then\n            abort 'FILELOCK")
mut("S72: sdclient: fileunlock aborts when quiet", SCL, "if server.error = SV$ON.ERROR and not(quiet) then\n            abort 'FILEUNLOCK", "if server.error = SV$ON.ERROR then\n            abort 'FILEUNLOCK")
mut("S72: sdclient: fileunlock sends a wait flag too", SCL, after("public subroutine fileunlock(fno)", "pkt = iconv(fno, 'ISL')\n", "pkt = iconv(fno, 'ISL')\n      pkt := iconv(0, 'ISL')\n"))
mut("S72: sdclient: filelock is not public", SCL, "public subroutine filelock(fno, wait)", "subroutine filelock(fno, wait)")
mut("S72: sdclient: the header does not list filelock", SCL, "* obj->filelock(fno, wait)\n", "")
mut("S72: sdclient: the history line is gone", SCL, rx(r"20 Oct 26 dm S\.72", "20 Oct 26 dm S.7x"))
# netfiles.c: the gate, the one request, the answers
mut("S72: net_filelock_step asks the gate AFTER the request", NFC, edit_func("net_filelock_step", r'(  st = net_gate\(fvar, NETG_LOCK, op_flags, "FILELOCK"\);\n  if \(st != 0\)\n    return st;[^\n]*\n)(\n  process\.op_flags = op_flags & P_ON_ERROR;\n  st = net_filelock\(fvar\);\n  process\.op_flags = 0;\n)', r"\2\1"))
mut("S72: net_filelock_step does not ask the gate", NFC, edit_func("net_filelock_step", r'  st = net_gate\(fvar, NETG_LOCK, op_flags, "FILELOCK"\);\n  if \(st != 0\)\n    return st;[^\n]*\n', ""))
mut("S72: net_filelock_step goes on after a refusal", NFC, edit_func("net_filelock_step", r"  if \(st != 0\)\n    return st;[^\n]*\n", ""))
mut("S72: net_filelock_step asks the gate as a write", NFC, edit_func("net_filelock_step", r"NETG_LOCK", "NETG_WRITE"))
mut("S72: net_filelock_step gives net_lock_result no retry pc", NFC, edit_func("net_filelock_step", r"net_lock_result\(st, op_flags, retry_pc\)", "net_lock_result(st, op_flags, NULL)"))
mut("S72: net_filelock_step does not use net_lock_result", NFC, edit_func("net_filelock_step", r"return net_lock_result\(st, op_flags, retry_pc\);", "return st;"))
mut("S72: net_lock_step does not use net_lock_result", NFC, edit_func("net_lock_step", r"return net_lock_result\(st, op_flags, retry_pc\);", "return st;"))
mut("S72: net_filelock_step takes the whole op_flags", NFC, edit_func("net_filelock_step", r"process\.op_flags = op_flags & P_ON_ERROR;", "process.op_flags = op_flags;"))
mut("S72: net_filelock_step leaves process.op_flags set", NFC, edit_func("net_filelock_step", r"  st = net_filelock\(fvar\);\n  process\.op_flags = 0;", "  st = net_filelock(fvar);"))
mut("S72: net_filelock sends NF_LOCK", NFC, edit_func("net_filelock", r"NF_FILELOCK", "NF_LOCK"))
mut("S72: net_filelock does not understand a busy answer", NFC, edit_func("net_filelock", r"NULL, FALSE, TRUE\)", "NULL, FALSE, FALSE)"))
mut("S72: net_filelock takes a wait argument", NFC, edit_func("net_filelock", r"\(FILE_VAR\* fvar\)", "(FILE_VAR* fvar, bool wait)"))
mut("S72: net_fileunlock does not ask the gate", NFC, edit_func("net_fileunlock", r'  st = net_gate\(fvar, NETG_LOCK, op_flags, "FILEUNLOCK"\);\n  if \(st != 0\)\n    return st;\n', ""))
mut("S72: net_fileunlock asks the gate AFTER the request", NFC, edit_func("net_fileunlock", r'(  st = net_gate\(fvar, NETG_LOCK, op_flags, "FILEUNLOCK"\);\n  if \(st != 0\)\n    return st;\n)(\n  process\.op_flags = op_flags & P_ON_ERROR;\n  st = net_change_op\(fvar, NF_FILEUNLOCK[^\n]*\n  process\.op_flags = 0;\n  if \(st < 0\)\n    return st;[^\n]*\n)', r"\2\1"))
mut("S72: net_fileunlock accepts any status", NFC, edit_func("net_fileunlock", r"switch \(net_reply_status\) \{.*?\n  \}\n", "answer = net_reply_status;\n"))
mut("S72: net_fileunlock accepts 3013 too", NFC, edit_func("net_fileunlock", r"    default:", "    case 3013:\n      answer = 3013;\n      break;\n    default:"))
mut("S72: net_fileunlock takes any positive status for the default", NFC, edit_func("net_fileunlock", r"    default:\n[^\n]*\n[^\n]*\n", "    default:\n      answer = net_reply_status;\n      break;\n"))
mut("S72: net_fileunlock maps ER_NLK to 0", NFC, edit_func("net_fileunlock", r"answer = ER_NLK;", "answer = 0;"))
mut("S72: net_fileunlock does not set process.status", NFC, edit_func("net_fileunlock", r"  process\.status = answer;\n", ""))
mut("S72: net_fileunlock raises whatever ON ERROR says", NFC, edit_func("net_fileunlock", r"net_raise\(-ER_NETWORK, op_flags\)", "net_raise(-ER_NETWORK, 0)"))
mut("S72: net_fileunlock returns 0 whatever it was told", NFC, edit_func("net_fileunlock", r"  return answer;", "  return 0;"))
mut("S72: net_fileunlock understands a busy answer", NFC, edit_func("net_fileunlock", r"NULL, FALSE, FALSE\)", "NULL, FALSE, TRUE)"))
mut("S72: net_fileunlock sends NF_FILELOCK", NFC, edit_func("net_fileunlock", r"NF_FILEUNLOCK", "NF_FILELOCK"))
mut("S72: net_fileunlock takes the whole op_flags", NFC, edit_func("net_fileunlock", r"process\.op_flags = op_flags & P_ON_ERROR;", "process.op_flags = op_flags;"))
mut("S72: net_recordlocked lets process.op_flags through (an ON ERROR could swallow the error)", NFC, edit_func("net_recordlocked", r"  process\.op_flags = 0;\n", ""))
mut("S72: net_recordlocked clears process.op_flags after the request", NFC, edit_func("net_recordlocked", r"  process\.op_flags = 0;\n(.*?  \(void\)net_lock_code\(fvar, id, id_len, &code\);[^\n]*\n)", r"\1  process.op_flags = 0;\n"))
mut("S72: net_recordlocked takes any owner number", NFC, edit_func("net_recordlocked", r"\(\(owner >= 0\) && \(owner <= 32767\)\) \? owner : 0", "owner"))
mut("S72: net_recordlocked takes a negative owner number", NFC, edit_func("net_recordlocked", r"\(owner >= 0\) && ", ""))
mut("S72: net_recordlocked takes an owner number above 32767", NFC, edit_func("net_recordlocked", r"\(owner <= 32767\)", "(owner <= 65535)"))
mut("S72: net_recordlocked accepts a code outside -3 to 3", NFC, edit_func("net_recordlocked", r"if \(\(code < -3\) \|\| \(code > 3\)\) \{", "if (0) {"))
mut("S72: net_recordlocked answers the owner, not the code", NFC, edit_func("net_recordlocked", r"  return code;", "  return owner;"))
mut("S72: net_recordlocked never takes the owner", NFC, edit_func("net_recordlocked", r"  owner = net_reply_status;", "  owner = 0;"))
mut("S72: net_recordlocked refuses with net_refuse", NFC, edit_func("net_recordlocked", r"  process\.op_flags = 0;", '  (void)net_refuse(fvar, "RECORDLOCKED");\n  process.op_flags = 0;'))
mut("S72: net_check_lock has its own request again", NFC, edit_func("net_check_lock", r"int status = net_lock_code\(fvar, id, id_len, &code\);", "int status = net_op_ex(fvar, NF_RECORDLOCKED, id, id_len, \"\", 0, NULL, FALSE, 0, FALSE, TRUE, NULL);"))
mut("S72: net_lock_code asks net_gate", NFC, edit_func("net_lock_code", r"  \*code = 0;", '  *code = 0;\n  if (net_gate(fvar, NETG_LOCK, 0, "RECORDLOCKED") != 0)\n    return -ER_PERM;'))
mut("S72: net_lock_code does not raise an error", NFC, edit_func("net_lock_code", r"    return net_raise\(status, entry\);", "    return status;"))
mut("S72: net_lock_code takes an empty id", NFC, edit_func("net_lock_code", r"\(id_len < 1\) \|\| ", ""))
mut("S72: net_check_lock sets the owner's number", NFC, edit_func("net_check_lock", r"  process\.status = 0;", "  process.status = net_reply_status;"))
mut("S72: net_op_ex does not reset the reply status", NFC, edit_func("net_op_ex", r"  net_reply_status = 0;\n", ""))
mut("S72: net_op_ex trusts the reply of a call that did not run", NFC, edit_func("net_op_ex", r"net_reply_status = ran \? rc\.reply_status : 0;", "net_reply_status = rc.reply_status;"))
mut("S72: net_op_ex keeps the reply status after process.op_flags is given back", NFC, edit_func("net_op_ex", r"(  net_reply_status = ran \? rc\.reply_status : 0;[^\n]*\n)(  process\.op_flags = entry;\n)", r"\2\1"))
mut("S72: net_parse_rc reads rc<8> from field 7", NFC, edit_func("net_parse_rc", r"net_field\(buf, 8, num, sizeof\(num\)\)", "net_field(buf, 7, num, sizeof(num))"))
mut("S72: net_parse_rc never reads rc<8>", NFC, edit_func("net_parse_rc", r"  \(void\)net_field\(buf, 8, num, sizeof\(num\)\);\n", ""))
mut("S72: NET_RC loses reply_status", NFC, rx(r"  int reply_status;[^\n]*\n", ""))
mut("S72: a second function reads the reply status", NFC, lambda t: t + "\nint zz_status(void) {\n  return net_reply_status;\n}\n")
# sd.h
mut("S72: sd.h declares net_filelock_step without the retry pc", "sd.h", "int net_filelock_step(FILE_VAR * fvar, u_int16_t op_flags, u_char * retry_pc);", "int net_filelock_step(FILE_VAR * fvar, u_int16_t op_flags);")
mut("S72: sd.h loses net_fileunlock", "sd.h", rx(r"int net_fileunlock\(FILE_VAR \* fvar, u_int16_t op_flags\);\n", ""))
mut("S72: sd.h declares net_recordlocked with a 32 bit id length", "sd.h", "int net_recordlocked(FILE_VAR * fvar, char * id, int16_t id_len);", "int net_recordlocked(FILE_VAR * fvar, char * id, int32_t id_len);")
# op_lock.c
mut("S72: op_filelock reads the file table before the NET_FILE test", OLK, edit_func("op_filelock", r"  if \(fvar->type == NET_FILE\)", "  fptr = FPtr(fvar->file_id);\n  if (fvar->type == NET_FILE)"))
mut("S72: op_filelock takes retry_pc AFTER a net_ call", OLK, lambda t: edit_func("op_filelock", r"(    process\.op_flags = 0;\n    k_dismiss\(\);)", "    u_char* retry_pc = op_pc;\n\\1")(
    edit_func("op_filelock", r"  u_char\* retry_pc = op_pc;[^\n]*\n", "")(t)))
mut("S72: op_filelock does not take retry_pc", OLK, edit_func("op_filelock", r"u_char\* retry_pc = op_pc;", "u_char* retry_pc = NULL;"))
mut("S72: op_filelock sets pc itself", OLK, edit_func("op_filelock", r"(case NET_LOCK_WAIT:[^\n]*\n\s*)return;", r"\1pc = retry_pc;\n        return;"))
mut("S72: op_filelock: a wait does not return", OLK, edit_func("op_filelock", r"(case NET_LOCK_WAIT:[^\n]*\n\s*)return;", r"\1break;"))
mut("S72: op_filelock: a busy file pushes 0", OLK, edit_func("op_filelock", r"(case NET_LOCK_LOCKED:[^\n]*\n\s*)status = ER_LCK;", r"\1status = 0;"))
mut("S72: op_filelock: an error pushes ER_LCK", OLK, edit_func("op_filelock", r"status = \(int16_t\)process\.status;", "status = ER_LCK;"))
mut("S72: op_filelock leaves process.op_flags set", OLK, edit_func("op_filelock", r"    process\.op_flags = 0;\n    k_dismiss\(\);", "    k_dismiss();"))
mut("S72: op_filelock does not dismiss its operand", OLK, edit_func("op_filelock", r"    process\.op_flags = 0;\n    k_dismiss\(\);", "    process.op_flags = 0;"))
mut("S72: op_filelock gives net_filelock_step no retry pc", OLK, edit_func("op_filelock", r"net_filelock_step\(fvar, op_flags, retry_pc\)", "net_filelock_step(fvar, op_flags, NULL)"))
mut("S72: op_filelock refuses a NET_FILE again", OLK, lambda t: t.replace("net_filelock_step(fvar, op_flags, retry_pc)", 'net_refuse(fvar, "FILELOCK"), net_filelock_step(fvar, op_flags, retry_pc)', 1))
mut("S72: op_flunlock reads the file table before the NET_FILE test", OLK, edit_func("op_flunlock", r"  if \(fvar->type == NET_FILE\)", "  fptr = FPtr(fvar->file_id);\n  if (fvar->type == NET_FILE)"))
mut("S72: op_flunlock gives the gate no flags", OLK, edit_func("op_flunlock", r"net_fileunlock\(fvar, op_flags\)", "net_fileunlock(fvar, 0)"))
mut("S72: op_flunlock refuses a NET_FILE again", OLK, edit_func("op_flunlock", r"net_fileunlock\(fvar, op_flags\)", 'net_refuse(fvar, "FILEUNLOCK")'))
mut("S72: op_flunlock leaves process.op_flags set", OLK, edit_func("op_flunlock", r"    process\.op_flags = 0;\n    k_dismiss\(\);", "    k_dismiss();"))
mut("S72: op_flunlock takes the flags after the NET_FILE test", OLK, edit_func("op_flunlock", r"op_flags = process\.op_flags;", "op_flags = 0;"))
mut("S72: GETLOCKS uses fvar->file_id again (file_id -1 lists every lock of every user)", OLK, edit_func("op_getlocks", r"file_id = NO_LOCAL_FILE;", "file_id = descr->data.fvar->file_id;"))
mut("S72: op_getlocks calls net_refuse again", OLK, lambda t: t.replace("file_id = NO_LOCAL_FILE;", 'net_refuse(descr->data.fvar, "GETLOCKS");', 1))
mut("S72: op_getlocks asks the server", OLK, lambda t: t.replace("file_id = NO_LOCAL_FILE;", 'file_id = NO_LOCAL_FILE;\n      (void)net_recordlocked(descr->data.fvar, "x", 1);', 1))
mut("S72: NO_LOCAL_FILE is 1 (the first file)", OLK, rx(r"(#define NO_LOCAL_FILE )0", r"\g<1>1"))
mut("S72: NO_LOCAL_FILE is -1 (every file)", OLK, rx(r"(#define NO_LOCAL_FILE )0", r"\g<1>-1"))
mut("S72: op_getlocks gives every file variable the local view", OLK, edit_func("op_getlocks", r"if \(descr->data\.fvar->type == NET_FILE\)", "if (1)"))
mut("S72: GETLOCKS of a remote file indexes UMap(user) (the NO_LOCAL_FILE arm of the waiters block is gone)", OLK, edit_func("op_getlocks", r"if \(file_id == NO_LOCAL_FILE\) \{.*?\} else if \(user == 0\)", "if (user == 0)"))
mut("S72: GETLOCKS: the NO_LOCAL_FILE arm comes after the user == 0 arm", OLK, edit_func("op_getlocks", r"if \(file_id == NO_LOCAL_FILE\) \{(.*?)\} else if \(user == 0\) \{(.*?)\} else \{", r"if (user == 0) {\2} else if (file_id == NO_LOCAL_FILE) {\1} else {"))
mut("S72: GETLOCKS: the NO_LOCAL_FILE arm still lists the waiters of every user", OLK, edit_func("op_getlocks", r"(if \(file_id == NO_LOCAL_FILE\) \{[^}]*?lo = 1;\s*)hi = 0;", r"\1hi = sysseg->max_users;"))
mut("S72: GETLOCKS: the waiters arm is taken for every negative file id", OLK, edit_func("op_getlocks", r"if \(file_id == NO_LOCAL_FILE\) \{", "if (file_id <= NO_LOCAL_FILE) {"))
mut("S72: op_filelock takes a local lock before the NET_FILE test", OLK, edit_func("op_filelock", r"  if \(fvar->type == NET_FILE\)", '  (void)check_lock(fvar, "x", 1, 0);\n  if (fvar->type == NET_FILE)'))
mut("S72: op_reclckd reads a transaction record before the NET_FILE test", OLK, edit_func("op_reclckd", r"  if \(fvar->type == NET_FILE\)", "  (void)txn_read(fvar, id, id_len);\n  if (fvar->type == NET_FILE)"))
mut("S72: op_getlocks ends a select list before it tests for a NET_FILE", OLK, edit_func("op_getlocks", r"    if \(descr->data\.fvar->type == NET_FILE\)", "    clear_select(0);\n    if (descr->data.fvar->type == NET_FILE)"))
mut("S72: op_reclckd refuses a NET_FILE again", OLK, edit_func("op_reclckd", r"net_recordlocked\(fvar, id, id_len\)", 'net_refuse(fvar, "RECORDLOCKED")'))
mut("S72: op_reclckd reads the file table before the NET_FILE test", OLK, edit_func("op_reclckd", r"  if \(fvar->type == NET_FILE\)", "  fptr = FPtr(fvar->file_id);\n  if (fvar->type == NET_FILE)"))
mut("S72: op_reclckd dismisses one operand only", OLK, edit_func("op_reclckd", r"    k_dismiss\(\);\n    k_dismiss\(\);", "    k_dismiss();"))
mut("S72: op_reclckd pushes the owner, not the code", OLK, edit_func("op_reclckd", r"(    InitDescr\(e_stack, INTEGER\);\n    \(e_stack\+\+\)->data\.value = )status;", r"\1process.status;"))
mut("S72: op_reclckd does not test the id first", OLK, edit_func("op_reclckd", r"k_illegal_id\(descr\);", ";"))
mut("S72: op_lock.c's history line is gone", OLK, rx(r"20 Oct 26 dm\s+S\.72", "20 Oct 26 dm  S.7x"))
mut("S72: netfiles.c's history line is gone", NFC, rx(r"20 Oct 26 dm\s+S\.72", "20 Oct 26 dm  S.7x"))
mut("S72: sd.h's history line is gone", "sd.h", rx(r"20 Oct 26 dm\s+S\.72", "20 Oct 26 dm  S.7x"))
mut("S72: netfile's history line is gone", NFP, rx(r"20 Oct 26 dm\s+S\.72", "20 Oct 26 dm  S.7x"))
mut("S72: netfile.h's history line is gone", NFHD, rx(r"20 Oct 26 dm\s+S\.72", "20 Oct 26 dm  S.7x"))
# apifilesok: it does not change; the change set holds 32 and 33 and not 34
mut("S72: apifilesok: filelock leaves the change set", AFO, drop_line(r"files\.chg := '32,'"))
mut("S72: apifilesok: fileunlock leaves the change set", AFO, drop_line(r"files\.chg := '33,'"))
mut("S72b: apifilesok: recordlocked leaves the change set (S72 had it out; S.72b put it in)", AFO, drop_line(r"files\.chg := '34,'"))
# the suite
mut("S72b: the suite's matrix loses recordlocked (a read-mode handle is refused again, and the matrix must hold it)", NFSUITE, rx(r'[ \t]*km\("recordlocked"[^\n]*\n', ""))
mut("S72: the suite's matrix loses the filelock control", NFSUITE, 'km("filelock", "filelock f", None, "filelock", None),\n', "")
mut("S72: the suite's KW_STILL_REFUSED holds filelock again", NFSUITE, 'KW_STILL_REFUSED = ("fiexcl",', 'KW_STILL_REFUSED = ("filelock", "fiexcl",')
mut("D1: vb.selectleft does not ask check.list", "apisrvr", rx(r"(vb\.selectleft:.*?)gosub check\.list[^\n]*\n\s*if err then return\n", r"\1", flags=re.S))
mut("D1: vb.selectright does not ask check.list", "apisrvr", rx(r"(vb\.selectright:.*?)gosub check\.list[^\n]*\n\s*if err then return\n", r"\1", flags=re.S))
mut("D1: vb.selectright has no RETURN again", "apisrvr", rx(r"(selectright cmnd\[5,999\] from files\(fno\) setting response to listno)\s*;\s*return", r"\1"))
mut("D1: the suite's KW_STILL_REFUSED holds an index statement again", NFSUITE, 'KW_STILL_REFUSED = ("fiexcl",', 'KW_STILL_REFUSED = ("selectindex", "fiexcl",')
mut("D1: the suite's matrix has an index statement again", NFSUITE, "    km(\"fcontrol6\",", "    km(\"setleft\", \"setleft 'CITY' from f\", None, \"setleft\", None),\n    km(\"fcontrol6\",")
mut("D1: the suite loses the statements' index rows", NFSUITE, "    kw_index(A)\n", "")
mut("D1: the suite loses the handler's index rows", NFSUITE, "    hw_index(A)\n", "")
mut("D1: the suite's READLIST carries a list number", NFSUITE, 'return (14, b"")', 'return (14, struct.pack("<h", lst))')
mut("D1: the suite's NF_INDEXQ is 25", NFSUITE, "NF_INDEXQ = 24", "NF_INDEXQ = 25")
mut("D1: the suite's KQALLOWED forgets the index requests", NFSUITE, "KQALLOWED = KALLOWED | {11, 14, 35, 36}", "KQALLOWED = KALLOWED | {11, 14}")
mut("D1: the suite's index is multivalued", NFSUITE, 'NI_INFO = "D\\xfd\\xfd\\xfd1\\xfd0\\xfdL\\xfd\\xfe1\\xfe\\xfeName\\xfeL\\xfeS"', 'NI_INFO = "D\\xfd\\xfd\\xfd1\\xfd0\\xfdL\\xfd\\xfe1\\xfe\\xfeName\\xfeL\\xfeM"')
mut("S72: the suite's GETLOCKS row expects the refusal again", NFSUITE, "KR kj SURVIVED fields=1 values=3", "KR kj REFUSED")
mut("S72: the suite's NF_FILEUNLOCK is 20", NFSUITE, "NF_FILELOCK, NF_FILEUNLOCK = 18, 19", "NF_FILELOCK, NF_FILEUNLOCK = 18, 20")
mut("S72: the suite's driver names NF$FILELOCK", NFSUITE, "         case nm = 'STATE'\n            op = NF$STATE\n", "         case nm = 'STATE'\n            op = NF$STATE\n         case nm = 'FLK'\n            op = NF$FILELOCK\n")
mut("S72: the suite's driver loses the RAW line", NFSUITE, "         case nm = 'RAW'\n            op = a + 0\n", "         case nm = 'RAWX'\n            op = a + 0\n")
mut("S72: the suite loses the handler's file lock rows", NFSUITE, "    hw_filelocks(A)\n", "")
mut("S72: the suite loses the statements' file lock rows", NFSUITE, "    kw_filelocks(A)\n", "")
mut("S72: the suite loses the class's file lock rows", NFSUITE, "    class_filelocks(A, alice)\n", "")

# ---- 20 Oct 26, S.72b: RECORDLOCKED() of a remote file is write-governed (S2i, S2zb, NF6a, S72d, S72n, S72q changed; S72r to S72v new) -----------------------------------------------
M_S72B = len(M)        # --selftest --from=<this number> runs S.72b's mutants alone
PEEK_GATE = r'  if \(net_gate\(fvar, NETG_PEEK, 0, "RECORDLOCKED"\) != 0\)\n    return 0;[^\n]*\n'      # net_recordlocked's call of the gate, with the line after it that returns
PEEK_ARM = r"  if \(kind == NETG_PEEK\) \{.*?\n  \}\n\n"                                               # net_gate's arm for it (the end of the block: a brace at the margin of the function's body, a blank line)
# sd.h: the constant and its comment
mut("S72b: sd.h: NETG_PEEK is 4 (NETG_LOCK's: the gate would ask for a lock)", "sd.h", rx(r"(#define NETG_PEEK )5", r"\g<1>4"))
mut("S72b: sd.h: NETG_PEEK is 6", "sd.h", rx(r"(#define NETG_PEEK )5", r"\g<1>6"))
mut("S72b: sd.h: NETG_PEEK has no comment", "sd.h", rx(r"(#define NETG_PEEK 5)[ \t]+/\*[^\n]*\*/", r"\1"))
mut("S72b: sd.h: NETG_PEEK is not defined", "sd.h", rx(r"#define NETG_PEEK 5[^\n]*\n", ""))
# net_gate: the arm, its place, its answer
mut("S72b: net_gate: NETG_PEEK is not special (the arm is gone: it meets the transaction test)", NFC, edit_func("net_gate", PEEK_ARM, ""))
mut("S72b: net_gate: the PEEK arm stands BEFORE the read-mode test (a read-mode handle is served)", NFC,
    edit_func("net_gate", r"(  if \(!fvar->access\.net\.write .*?\n  \}\n\n)(" + PEEK_ARM + r")", r"\2\1"))
mut("S72b: net_gate: the PEEK arm stands AFTER the transaction test (RECORDLOCKED() inside BEGIN TRANSACTION is refused with 11510)", NFC,
    edit_func("net_gate", r"(" + PEEK_ARM + r")(  /\* 21 Oct 26 S\.73 item 3: step 2.*?\*/\n\n)(  if \(process\.txn_id != 0\) \{.*?\n  \}\n\n)", r"\2\3\1"))
mut("S72b: net_gate: the PEEK arm does not give process.op_flags back", NFC, edit_func("net_gate", r"(  if \(kind == NETG_PEEK\) \{[^\n]*\n)    process\.op_flags = entry;\n", r"\1"))
mut("S72b: net_gate: the PEEK arm answers a refusal, not 0", NFC, edit_func("net_gate", r"(  if \(kind == NETG_PEEK\) \{[^\n]*\n    process\.op_flags = entry;\n    )return 0;", r"\1return -ER_NETWORK;"))
mut("S72b: net_gate: the PEEK arm refuses inside a transaction", NFC,
    edit_func("net_gate", r"(  if \(kind == NETG_PEEK\) \{[^\n]*\n)", r"\1    if (process.txn_id != 0)\n      return net_refuse_with(fvar, what, MSG_TXN, -ER_TXN);\n"))
mut("S72b: net_gate: the read-mode test is skipped for NETG_PEEK (a read-mode handle asks the server)", NFC,
    edit_func("net_gate", r"if \(!fvar->access\.net\.write \|\| \(fvar->flags & FV_RDONLY\)\) \{", "if ((kind != NETG_PEEK) && (!fvar->access.net.write || (fvar->flags & FV_RDONLY))) {"))
mut("S72b: net_gate: the edit gate is asked for NETG_PEEK too", NFC, edit_func("net_gate", r"\(kind == NETG_ADMIN\)\) \{", "(kind == NETG_ADMIN) || (kind == NETG_PEEK)) {"))
# net_recordlocked: the gate, FIRST, with kind PEEK and the literal 0
mut("S72b: net_recordlocked asks no gate (a read-mode handle sends request 34)", NFC, edit_func("net_recordlocked", PEEK_GATE, ""))
mut("S72b: net_recordlocked asks the gate AFTER the request", NFC,
    edit_func("net_recordlocked", r"(" + PEEK_GATE + r")(  \(void\)net_lock_code\(fvar, id, id_len, &code\);[^\n]*\n)", r"\2\1"))
mut("S72b: net_recordlocked asks the gate as a lock (a transaction is refused: 11510)", NFC, edit_func("net_recordlocked", r"NETG_PEEK", "NETG_LOCK"))
mut("S72b: net_recordlocked asks the gate as a write (the edit gate and CREATING.SEQKEY apply)", NFC, edit_func("net_recordlocked", r"NETG_PEEK", "NETG_WRITE"))
mut("S72b: net_recordlocked gives the gate the flags a previous statement left (an ON ERROR swallows the refusal)", NFC, edit_func("net_recordlocked", r"net_gate\(fvar, NETG_PEEK, 0, ", "net_gate(fvar, NETG_PEEK, process.op_flags, "))
mut("S72b: net_recordlocked gives the gate P_ON_ERROR (the refusal is swallowed)", NFC, edit_func("net_recordlocked", r"net_gate\(fvar, NETG_PEEK, 0, ", "net_gate(fvar, NETG_PEEK, P_ON_ERROR, "))
mut("S72b: net_recordlocked goes on after a refusal (the answer of the gate is not looked at)", NFC, edit_func("net_recordlocked", PEEK_GATE, '  (void)net_gate(fvar, NETG_PEEK, 0, "RECORDLOCKED");\n'))
mut("S72b: net_recordlocked names another statement to the gate (the message says recordlock)", NFC, edit_func("net_recordlocked", r'"RECORDLOCKED"\) != 0', '"RECORDLOCK") != 0'))
# MUSTLOCK is not gated
mut("S72b: net_check_lock (MUSTLOCK) asks the gate", NFC,
    edit_func("net_check_lock", r"  int status = net_lock_code\(fvar, id, id_len, &code\);", '  int status = net_gate(fvar, NETG_PEEK, 0, "MUSTLOCK");\n\n  if (status == 0)\n    status = net_lock_code(fvar, id, id_len, &code);'))
mut("S72b: net_pre_change_lock gates the MUSTLOCK check", D3,
    edit_func("net_pre_change_lock", r"if \(pcfg\.must_lock\) \{", 'if (pcfg.must_lock) {\n    if (refuse_net_file(fvar, op_flags, "MUSTLOCK", NETG_LOCK))\n      return NETL_FAIL;'))
mut("S72b: a second kernel function asks the gate for a PEEK", OLK, edit_func("op_reclckd", r"  if \(fvar->type == NET_FILE\)", '  if ((fvar->type == NET_FILE) && (net_gate(fvar, NETG_PEEK, 0, "RECORDLOCKED") != 0))\n    return;\n  if (fvar->type == NET_FILE)'))
# the handler: the mode refusal of act.recordlocked
mut("S72b: act.recordlocked is not refused for a read-mode handle", NFP, after("\nact.recordlocked:", "   if nf.h.mode(hx) # 'write' then\n      gosub act.refuse\n      return\n   end\n", ""))
mut("S72b: act.recordlocked does not stop after the refusal (the request goes on)", NFP, after("\nact.recordlocked:", "      gosub act.refuse\n      return\n", "      gosub act.refuse\n"))
mut("S72b: act.recordlocked refuses AFTER the gate and the connection are asked", NFP,
    rx(r"(\nact\.recordlocked:\n)(   need\.gate = @false ; need\.conn = @false ; any\.acct = @false ; allow\.lost = @true\n   gosub get\.handle\n   if failed then return\n)"
       r"(   opname = 'recordlocked'\n   if nf\.h\.mode\(hx\) # 'write' then\n      gosub act\.refuse\n      return\n   end\n)(   need\.gate = @true[^\n]*\n   gosub get\.handle\n   if failed then return\n)", r"\1\4\3"))
mut("S72b: act.recordlocked asks the gate and the connection in its first get.handle only (the second is gone)", NFP,
    after("\nact.recordlocked:", "   need.gate = @true ; need.conn = @true ; any.acct = @false ; allow.lost = @false\n   gosub get.handle\n   if failed then return\n", ""))
mut("S72b: act.recordlocked does not ask the gate in its second get.handle", NFP,
    after("\nact.recordlocked:", "   need.gate = @true ; need.conn = @true ; any.acct = @false ; allow.lost = @false", "   need.gate = @false ; need.conn = @true ; any.acct = @false ; allow.lost = @false"))
mut("S72b: act.recordlocked reads the definition now (mode.now)", NFP,
    after("\nact.recordlocked:", "   need.gate = @true ; need.conn = @true", "   gosub mode.now\n   if not(mode.ok) then\n      gosub act.refuse\n      return\n   end\n   need.gate = @true ; need.conn = @true"))
mut("S72b: act.recordlocked is refused in a transaction (11510)", NFP,
    after("\nact.recordlocked:", "   obj = nf.s.obj(slot)\n", "   if system(SYS$TRANS_LEVEL) # 0 then\n      fail.num = 11510 ; fail.a1 = srvname ; fail.a2 = opname\n      gosub fail\n      return\n   end\n   obj = nf.s.obj(slot)\n"))
mut("S72b: act.recordlocked names no operation (the refusal says nothing about the statement)", NFP, after("\nact.recordlocked:", "   opname = 'recordlocked'\n", ""))
mut("S72b: act.recordlocked is audited", NFP, after("\nact.recordlocked:", "   obj = nf.s.obj(slot)\n", "   void kernel(K$AUDIT, 'netfile recordlocked server=' : srvname)\n   obj = nf.s.obj(slot)\n"))
# the handler reads the reply: a refused request 34 is an ON ERROR reply (S72x, S2k)
mut("S72b: act.recordlocked has no ON ERROR branch (a refusal is shown as 11504, or not at all)", NFP,
    after("\nact.recordlocked:", "   if lerr = NF$LE.ERROR then\n      gosub on.error.text\n      gosub server.fail\n      return\n   end\n", ""))
mut("S72b: act.recordlocked shows the ON ERROR reply without its text (the status instead)", NFP,
    after("\nact.recordlocked:", "   if lerr = NF$LE.ERROR then\n      gosub on.error.text\n", "   if lerr = NF$LE.ERROR then\n      rq.txt = 'status ':rq.st\n"))
mut("S72b: act.recordlocked does not read LastError", NFP, after("\nact.recordlocked:", "   lerr = obj->LastError\n", ""))
mut("S72b: act.recordlocked reads LastError after after.rq", NFP, after("\nact.recordlocked:", "   lerr = obj->LastError\n   gosub after.rq\n", "   gosub after.rq\n   lerr = obj->LastError\n"))
mut("S72b: act.recordlocked does not take a missing reply (lerr = -1) for a lost one", NFP, after("\nact.recordlocked:", "   if lerr = -1 then rq.lost = @true\n", ""))
mut("S72b: act.recordlocked has no unknown-answer branch (11504)", NFP,
    after("\nact.recordlocked:", "   if lerr # NF$LE.OK then\n      fail.num = 11504 ; fail.a1 = srvname ; fail.a2 = opname ; fail.a3 = 'answer ':lerr\n      gosub fail\n      return\n   end\n", ""))
mut("S72b: act.recordlocked answers a refused request with the code (out = lk before the branches)", NFP,
    after("\nact.recordlocked:", "   lerr = obj->LastError\n", "   lerr = obj->LastError\n   out = lk\n"))
mut("S72b: act.recordlocked gives the server error no message (rq.err is not looked at)", NFP,
    after("\nact.recordlocked:", "   if rq.err then\n      gosub server.fail\n      return\n   end\n", ""))
# the class: recordlocked() honours quiet
mut("S72b: sdclient: recordlocked aborts even when quiet", SCL, "if not(quiet) then abort 'RECORDLOCKED generated an abort event'", "abort 'RECORDLOCKED generated an abort event'")
mut("S72b: sdclient: recordlocked has no ON ERROR case (a refusal is read as data)", SCL,
    "            case server.error = SV$ON.ERROR\n               if not(quiet) then abort 'RECORDLOCKED generated an abort event'\n", "")
mut("S72b: sdclient: recordlocked goes back to text.request (it aborts whatever quiet says)", SCL,
    rx(r"(public function recordlocked\(fno, id\)\n).*?(   if len\(reply\) < 4 then return 0)", r"\1   reply = text.request(SrvrRecordlocked, iconv(fno, 'ISL') : id, 'RECORDLOCKED generated an abort event')\n\2", re.S))
mut("S72b: sdclient: recordlocked sends request 33", SCL, after("public function recordlocked(fno, id)", "message.pair(SrvrRecordlocked,", "message.pair(SrvrFileunlock,"))
mut("S72b: sdclient: recordlocked leaves the id out", SCL, after("public function recordlocked(fno, id)", "iconv(fno, 'ISL') : id)", "iconv(fno, 'ISL'))"))
mut("S72b: sdclient: recordlocked does not make the answer signed", SCL, after("public function recordlocked(fno, id)", "   if n > 2147483647 then n -= 4294967296\n", ""))
mut("S72b: sdclient: recordlocked takes the reply of an ON ERROR as data", SCL, after("public function recordlocked(fno, id)", "            case server.error = SV$OK\n", "            case server.error = SV$OK or server.error = SV$ON.ERROR\n"))
# the history lines
for _f, _n in (("netfiles.c", NFC), ("op_lock.c", OLK), ("sd.h", "sd.h"), ("gpl.bp/netfile", NFP), ("gpl.bp/sdclient", SCL), ("gpl.bp/apifilesok", AFO)):
    mut("S72b: %s's S.72b history line is gone" % _f, _n, rx(r"20 Oct 26 dm\s+S\.72b", "20 Oct 26 dm  S.7x"))


def run(srcs):
    return checks(srcs)


def main():
    srcs = load()
    if "--selftest" in sys.argv:
        base = run(srcs)
        bad = [i for i, ok, d in base if not ok]
        if bad:
            print("test-net-units: the unmutated source already fails: %s" % bad)
            return 2
        missed = 0
        start = int(next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--from=")), "0"))          # --from=N: only the mutants from the Nth on (M3E_START is slice 3e's first, M_S72 is S.72's first: print either to find N)
        match = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--match=")), "")      # --match=TEXT: only the mutants whose label holds TEXT (24 Oct 26: the W.11 F9 re-aim touched about a dozen of the 1,500)
        for label, name, old, new in [m for m in M[start:] if match in m[0]]:
            try:
                rows = checks(mutate(srcs, name, old, new))
            except KeyError as e:
                print("  [FAIL] mutant is not applicable: %s (%s)" % (label, e))
                missed += 1
                continue
            caught = [i for i, ok, d in rows if not ok]
            if caught:
                print("  [PASS] mutant caught: %s  <- %s" % (label, ", ".join(caught[:3])))
            else:
                print("  [FAIL] MUTANT NOT CAUGHT: %s" % label)
                missed += 1
        print("\ntest-net-units --selftest: %d mutants, %d missed" % (len(M) - start, missed))
        return 1 if missed else 0
    rows = run(srcs)
    failed = 0
    for i, ok, d in rows:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", i, "" if ok or not d else "   <- " + d))
        failed += 0 if ok else 1
    print("\ntest-net-units: %d checks, %d failed" % (len(rows), failed))
    print("NOT MEASURED HERE: whether the gate answers, or whether a verb writes or refuses.  That is sandbox-net.py (a private SD).")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
