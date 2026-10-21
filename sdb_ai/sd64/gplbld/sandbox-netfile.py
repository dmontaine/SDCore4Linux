#!/usr/bin/env python3
#
# sandbox-netfile.py - the BASIC client class gpl.bp/sdclient: the login from STORED DERIVED KEYS (connect.keys) and the FILE requests, run
#                      against the Python fake API server (gplbld/netfake.py).  S.65 slice 3a.  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-netfile.py <dir> [--build] [--sections=a,b]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or absent); without it
# <dir> must already be built.  Exit 0 every row passed, 1 a row failed, 2 it could not run.  --sections= runs only the named parts
# (login, args, pin, stale, keys, shared, down, close, notfound, files, account, locks, lists, wire - the class, slice 3a; handler, readonly,
# refuse, lost, timeout, oversize (K8c) - the handler gpl.bp/netfile, slice 3b; hwrite - the handler in WRITE mode, slice 3e; kwrite - the statements on a write-mode file, slice 3e;
# kernel - the NET_FILE type through real OPEN / READ / READV / FILEINFO / CLOSE
# statements and the refusal of everything else, slice 3c; wgroup - a login without the write group; mustlock - S.72b, MUSTLOCK against that wall, always the LAST part;
# gaps - OPT-IN ONLY, see below); no flag runs all of them except gaps.
#
# START-HISTORY:
# 20 Oct 26 dm  S.72b (owner's decision of the day): RECORDLOCKED() of a remote file is write-governed.  Two walls: the SERVER's - request 34 is in the change set of gpl.bp/apifilesok, so a files-only
#               login WITHOUT sdfileswrite is refused it with message 11521 (the fake's FILES_CHANGE, netfake.py), and the CLIENT's - a read-mode handle (the definition says read, or the variable is read
#               only) is refused with message 11501 and NOTHING is sent (net_gate(NETG_PEEK), and the handler's act.recordlocked one layer down).  A write-mode handle in the group is served as before,
#               INSIDE a transaction too (NETG_PEEK skips the transaction test).  Rows are tagged [S72b-Nn] in their labels.  FLIPPED (they expected a read-mode handle, or a login without the group, to be
#               served): N0 (section handler, the nfa handle; its lock rows now open the same files through the write-mode server nfw), N1a (class, the files-only login no longer tests a lock), N2 (class,
#               the quiet object), N3 (hwrite, the nfa handle), N6 and N7 (wgroup, the handler without the group), N9 (kwrite: the read-mode handle moved out of kw_filelocks into kw_peek), the wgroup statement
#               row (FILELOCK and FILEUNLOCK only) and the kw_filelocks read-mode control.  ADDED: N1b N1c (class, the files-only login without the group: the abort and the fake's own text), N4 (hwrite, the
#               nfa handle and a record that IS locked), N5 (hwrite, the definition read again: RECORDLOCKED is still served), N6c (wgroup, the control with the group), N8 (the refusal matrix: RECORDLOCKED on
#               a NET file WITHOUT ON ERROR), N9b (a variable made read only), N10 (inside BEGIN TRANSACTION with locks really held), N11 (the server's wall for a statement), N13 (MUSTLOCK without the group: the section mustlock, which runs LAST because a red row there wedges the sandbox).
#               THE ROWS WERE RUN RED ON THE UNCHANGED SOURCE (a built copy of f64e7ff with this file and the S.72b netfake.py over it), then green on the changed tree; the counts are in PROJECT_STATUS.
#               Rows N2, N6, N7, N11 and N13 need the CLASS to be quiet-aware on request 34: sdclient's recordlocked() goes through text.request(), which aborts on an ON ERROR reply whatever quiet says, so
#               the handler's "Server nfw answered recordlocked with an error: <the text of 11521>" cannot come until recordlocked() returns for a quiet object and leaves LastError / LastText, as filelock() does.
# 20 Oct 26 dm  S.73 item 2, THE SILENT SERVER (the owner delegated it: "silent-server your choice").  The row labelled KNOWN LIMIT of the timeout section is FLIPPED: a server that completes the
#               handshake and never sends the Ack is given up on at NETREPLY=3 (5.0 s on the tree before, the fake's own close).  New rows, each printing the real seconds: a listener that accepts and
#               never answers the TLS hello (netfake.SilentListener) is given up on at NETWAIT=2 (15.0 s before: the handshake had 15 seconds fixed in op_skt.c); half of a TLS record in place of the Ack
#               and in place of the reply to client-first (netfake.PartialRecordServer; 12.0 and 12.1 s before, the server's own hold); a server that answers 1.5 s late inside NETREPLY=3 is not given
#               up on; a reply cut in the middle (netfake short_reply) is 11497 for a READ and 11509 for a WRITE within NETREPLY (the READ was "answer -1", message 11504, with the connection kept:
#               gpl.bp/sdclient read.packet took the header's error and status before the body).  RED ON THE UNCHANGED TREE (a git archive of the commit before, with these two test files over it): 6 rows;
#               green 42 of 42 on the changed tree (--sections=timeout).  Four runtime mutants on scratch copies, each killed by the rows written down before it ran (see PROJECT_STATUS S.73).
# 20 Oct 26 dm  S.72 (QMNet parity, tiers A and B): FILELOCK, FILEUNLOCK, RECORDLOCKED() and GETLOCKS() of a remote file.  Class rows (class_filelocks: requests 32 and 33 with their bytes, LOCKED with the
#               holder, FILEUNLOCK's 0 / 3011 / 3012, CLOSE of the locking number against another number, a session that ends, a login without the write group); handler rows (hw_filelocks: operations
#               18 and 19 driven by number through the RAW line so that the driver compiles on a tree that does not define them, rc<8>, the audit line once for the handle, the read-mode handle, the
#               transaction, the mode read again - FILEUNLOCK is not stopped by it -, a connection lost after the server did it); statement rows (kw_filelocks: the local control first, then the
#               statements of an ordinary session on a write-mode and a read-mode file, the wait by asking again with the wait flag always 0, the life of a file lock, RELEASE f, GETLOCKS() in an
#               internal program, MUSTLOCK with a file lock, a lost connection without ON ERROR); wgroup rows (32 and 33 refused for a login without sdfileswrite, RECORDLOCKED served).  Changed rows:
#               the matrix lost `recordlocked` and the still-refused list lost filelock / fileunlock / recordlocked; GETLOCKS of a remote file survives; the verb CLEAR.FILE now clears a write-mode
#               remote file (it locks the file first) and LIST ... LOCKING takes the file lock.  THE ROWS WERE RUN RED ON THE UNCHANGED SOURCE (a built copy of Dev 573d2d3 with these test files over it), then
#               green on the changed tree; the counts are in PROJECT_STATUS S.72.
# 19 Oct 26 dm  Finish 2 (verifier findings).  (1) Section hwrite: a SELECT whose READLIST (request 14) the server answers with an ON ERROR text - the third place the handler shows the
#               server's text (act.select) had no row; two rows and a control with no text.  (2) Section timeout, in the same restart as the NETREPLY=3 row (now NETREPLY=3 and NETWAIT=2): a
#               server that sends the Ack, reads client-first and goes silent (netfake stall_first) costs connect.keys NETREPLY seconds (no TMO first), and a listener whose accept queue is
#               full costs it NETWAIT seconds, each measured against a control (a closed port) so the session's own cost is taken off; the restart is netfake.restart_with_conf and the
#               hanging listener netfake.HangingListener.  THE FIRST VERSION OF THE NETREPLY ROW USED A SERVER THAT NEVER SENDS THE ACK AND WAS RED ON THE TREE UNDER TEST (5.0 s, not 3): that
#               wait is not bounded by NETREPLY, because TLS 1.3's session tickets end READ.SOCKET's wait and the SSL_read behind it then blocks (evidence in the section); it is kept as a
#               row labelled KNOWN LIMIT, and the question is the owner's.  (3) kwrite:
#               the row "A program READUs a record and ends without CLOSE" failed in 3 of 4 runs of an unchanged tree because the lock lived for less than one poll of LockWatch; the program
#               (KWL1_TEXT) now sleeps a second holding it.
# 19 Oct 26 dm  K1, K8b, K8c, K8d (the S.65 finish).  (K1) The handler shows the TEXT of an ON ERROR reply, or 'status <n>' when it has none: the wgroup rows now expect the
#               text of message 11521 with each request number (they expected 'status 0'), the injected ON ERROR rows expect their text, there is a control with no text, one
#               with an escape character and a long tail, and the MAXRLOCK row expects the kernel's abort text; k_srverr has a text mode that also checks rc<6>.  The read only
#               file rows follow the real server (+3018, and an abort with the kernel's text for CLEARFILE): netfake.REAL_ON_ERROR, measured by sandbox-req29.py section G.
#               (K8c) The section oversize: a reply that is a header alone announcing 3,000,000,000, 2,000,000,000 or 4 bytes is a lost connection AT ONCE (it cost the 30 seconds of a
#               body that never came), for a READ and for a WRITE (11509, the outcome unknown).  (K8d) The timeout section runs again with NETREPLY=3 in sd.conf (the daemon of the
#               sandbox is stopped and started for it, and again afterwards).  (K8b) The comments that called the suite unrun are corrected.  Red-then-green, 19 Oct 26: 12 of the
#               hwrite and wgroup rows red on the handler of HEAD, 10 of the 33 oversize rows red on the class and the handler of HEAD.
# 18 Oct 26 dm  S.65 slice 3e: WRITES AND LOCKS ON A REMOTE FILE, for a server whose definition says mode=write (spec .claude/s65-stage2-design.md, 10 and 11).  Two new
#               sections.  hwrite drives the HANDLER ($netfile) against the fake's new write requests (16 to 19, 30, 31, 15): the definition's mode at the open (rc<7>, the
#               audit line), WRITE / WRITEU / DELETE / DELETEU / CLEARFILE / LOCK / RELEASE with the exact bytes on the wire and the record, the lock and the busy answer on the
#               fake, a bad id and a bad lock kind (nothing sent), the mode READ AGAIN (a server set back to read stops a handle that is open), a transaction, a lost
#               connection before and after the change (11509, the outcome unknown, never a second request), the server's own errors (MUSTLOCK, a read only file, the server's
#               edit gate, MAXRLOCK), a success status that is not trusted, and the READ answered with an ON ERROR (the old gaps row, moved here).  kwrite drives the
#               STATEMENTS of an ordinary session (WRITE, WRITEU, MATWRITE, WRITEV, WRITEVU, DELETE, DELETEU, CLEARFILE, READU/L, MATREADU/L, READVU/L, RECORDLOCKU/L, RELEASE) on
#               a write-mode file: what each does on the fake, STATUS() afterwards, with and without ON ERROR / THEN / ELSE / LOCKED, the busy record that is waited for by
#               polling (the fake sees only lock requests, no read), a transaction (1010 and 11510), the S.64 edit gate by the remote file's NAME (voc, dict, bp) for an
#               account without the gate, one with it, the administrator and an $internal program, edit_guard, the cache (a write-mode handle is never cached), a lost
#               connection, MUSTLOCK and AUTOLOCK, the lock that outlives its file variable until the next prompt, FILEINFO, and the statements that stay refused (11511).  EVERY
#               EXISTING ROW THAT EXPECTED THE REFUSAL OF AN IN-SCOPE STATEMENT (readonly, the refusal matrix KM, KALLOWED) STANDS AS THE MODE=READ CONTROL: the definitions
#               nfa and nfb are mode read, the new nfw and nfwb are mode write.  ***NOT YET RUN*** - written without a sandbox to run it on; the first run is the first evidence for
#               the suite, the handler, the kernel and the fake's write requests together; read a red row as a wrong expectation here as well as a fault there.
# 17 Oct 26 dm  S.65 slice 3c: the section kernel - a VOC pointer of type N opened by an ORDINARY session's OPEN statement (the C gate, the handler, the
#               fake), READ / READV / MATREAD / FILEINFO / CLOSE as statements with THEN, ELSE and ON ERROR, two opens sharing a connection, a loop of 150
#               opens (the queue of released handles), a LOGTO; the NET gate off, an unlisted account, no credential, a pin mismatch, a malformed pointer
#               and a DICT open each refused without dialling; and THE REFUSAL MATRIX: about 35 statements, each given an open NET file variable in a
#               program of its own, with and without ON ERROR, and the fake's packet log required to hold nothing but login, account, open, read, close
#               and quit.  The verbs COUNT, LIST, SELECT, SORT, CLEAR.FILE, DELETE.FILE, COPY, ED ... on the VOC name.  ***NOT YET RUN*** - written
#               without a sandbox to run it on, and the kernel it tests has never been compiled by anyone but its authors' syntax check; a red row is
#               a wrong expectation here or a fault there, and the first run says which.  gaps gained the LOGTO row (the kernel key that ends the
#               connections is not built).
# 17 Oct 26 dm  New.  S.65 slice 3a.  ***NOT YET RUN*** - written on 17 Oct without a sandbox to run it on, as the slice's rule was that
#               no agent compiles SD.  The first run is the first evidence; read a red row as a possible wrong expectation in this file
#               as well as a fault in the class (the BASIC of the driver below has never been compiled either).
# 17 Oct 26 dm  S.65 slice 3b: the sections handler, readonly, refuse, lost, timeout and gaps - the handler gpl.bp/netfile ($netfile, operations in
#               netfile.h) driven by a second BASIC program, zznfh.  ***NOT YET RUN*** - written without a sandbox to run it on, and the handler
#               itself has never been compiled; the first run is the first evidence for both.  See the block "H." below for how it works and what
#               the section gaps is.
# END-HISTORY
#
# WHAT IT TESTS.  A BASIC program (the driver, zznfx) is compiled by an ORDINARY session in a fixture account and run there.  It makes an
# object of the class (object('!sdclient')) and obeys one line of input at a time - SET a stored value, KEYS (obj->connect.keys), PW
# (obj->connect, the password login that must still work), OPEN, READ, READL, READU, RLOCKED, RELEASE, SELECT, NEXT, LIST, CLEARSEL, MARKS,
# REV, CLOSE, EXEC, TMO, STAT, ERR, DISC - and prints one line "FX <op> ..." for each, so that a row reads what the PROGRAM got, not what
# the class intended.  The other end is the fake: TLS 1.3 on 127.0.0.1, the Ack byte, the packet framing, the server half of SCRAM-SHA-256
# and the file requests of apisrvr over an in-memory store (netfake.FakeServer), which RECORDS every packet it receives, so a row can say
# what the class DID on the wire and not only what it printed: the request types in order, and for the file requests the bytes.
#
# WHERE THE EXPECTED VALUES COME FROM.  Never from SD and never from the class.  The salt, ClientKey, ServerKey and the proof are computed
# in this file with hashlib and hmac (dk, my_proof; a row holds them to netfake.derive); the pins are the SHA-256 of the SubjectPublicKeyInfo
# as the openssl command line gives it; the records are the ones this file put into the store; the request numbers and the packet layouts
# are written here as numbers and struct.pack, from the apisrvr table, not read from sdclient's $defines.
#
# WHAT IT CANNOT SHOW.  (1) THE CHANNEL BINDING: Python's ssl module has no TLS exporter, so the fake takes the client's c= on trust
# (netfake.py says so); witness-release-run.sh on an install is the only test of it.  (2) Anything the class does not expose: READV,
# FILEINFO and SELECTLIST are requests the fake serves (netfake.py's own self-test holds them) but the class has no method for, so a
# row through the class cannot be written; slice 3b's handler will need them or will do without.  (3) The class's CALL against a
# files-only login: call() does not look at the reply's error field and then reads the refusal text as the list of returned arguments
# (found by reading, not run); the 11480 text is therefore shown by the fake's own Python client (rows in "files"), and the class is
# shown refusing EXECUTE, which aborts.  (4) The real SD server (apisrvr) - the fake is a model of it.
#
# THE INSTRUMENT.  Every row requires that the driver BEGAN ("FX begin"), and that it reached its end ("FX end") unless the row is about an
# abort; the fake found nothing malformed in the class's messages (netfake's `errors` list is empty, a row says when it is not); and
# EVERY CONNECTION THE FAKE ACCEPTED HAS ENDED after the session (no socket is left open by the class: busy 0, no live socket).

import base64
import datetime
import hashlib
import hmac
import importlib.util
import os
import pwd
import re
import shutil
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import netfake                      # the fake API server; self-tested: netfake.py --selftest
spec = importlib.util.spec_from_file_location("sandbox_gates", os.path.join(HERE, "sandbox-gates.py"))
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
passed = failed = 0

ACCT = "zznfx"                      # the ordinary fixture account the driver runs in
PROG = "zznfx"                      # the driver, in that account's bp
PW_ALICE = "Zq7-alice-Passw0rd-x"   # passwords that appear nowhere else
PW_BOB = "Zq7-bob-Passw0rd-y"
PW_CAROL = "Zq7-carol-Passw0rd-z"
PW_WRONG = "Wrong-Passw0rd-q3"
REVISION = "L9.9-9"                 # what the fake answers to request 49
FMC, VMC, SMC, IMC = "\xfe", "\xfd", "\xfc", "\xff"
RECS = {
    "c1": "Smith" + FMC + "100" + VMC + "200" + FMC + "x",
    "c2": "Jones" + FMC + "50",
    "c3": "Brown",
    "m1": "a" + SMC + "b" + VMC + "c" + FMC + "d" + IMC + "e",
    "big": "ab" * 35000,                                    # 70,000 bytes: more than one read of the socket
}
DICT_ITEMS = {"name": "D" + FMC + "1", "bal": "D" + FMC + "2"}
S = {}                              # the servers, users and pins this run made


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
    say("sandbox-netfile: CANNOT RUN - " + msg)
    sys.exit(2)


def msg(n, *args):
    """The text of message N as the sandbox was built with it, the %n places filled."""
    p = os.path.join(g.SYS, "messages", str(n))
    if not os.path.exists(p):
        bail("the sandbox holds no message %d (%s)" % (n, p))
    with open(p, encoding="utf-8", errors="replace") as f:
        t = f.readline().rstrip("\r\n")
    for i, a in enumerate(args, 1):
        t = t.replace("%%%d" % i, str(a))
    return t


def acct_path(name):
    return os.path.join(g.BOX, "user_accounts", name)


# ---- the independent arithmetic ----------------------------------------------------------------------------------------------------

def b64(raw):
    return base64.b64encode(raw).decode("ascii")


def dk(password, salt_b64, iterations):
    """RFC 5802 / 7677 from hashlib and hmac alone: (ClientKey, ServerKey) raw."""
    salted = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), base64.b64decode(salt_b64), int(iterations), 32)
    return (hmac.new(salted, b"Client Key", hashlib.sha256).digest(), hmac.new(salted, b"Server Key", hashlib.sha256).digest())


def my_proof(client_key, authmsg):
    """ClientProof = ClientKey XOR HMAC(SHA256(ClientKey), AuthMessage)."""
    sig = hmac.new(hashlib.sha256(client_key).digest(), authmsg.encode("latin-1"), hashlib.sha256).digest()
    return bytes(a ^ b for a, b in zip(client_key, sig))


def user_bundle(name, password, salt_b64, iterations=4096):
    ck, sk = dk(password, salt_b64, iterations)
    return {"user": name, "pw": password, "salt": salt_b64, "it": iterations, "ck": ck, "sk": sk, "ck_b64": b64(ck), "sk_b64": b64(sk)}


def flip(raw):
    return bytes([raw[0] ^ 1]) + raw[1:]


def show(s):
    """What the driver prints for a value: the four marks made visible, then cut to its first and last 40 characters when over 100."""
    for a, b in ((IMC, "<I>"), (FMC, "<F>"), (VMC, "<V>"), (SMC, "<S>")):
        s = s.replace(a, b)
    if len(s) > 100:
        s = s[:40] + ".." + s[-40:]
    return s


def rl(op, rid, e, rec):
    """The line the driver prints for a READ, READL or READU."""
    return "FX %s %s e=%d len=%d rec=[%s]" % (op, rid, e, len(rec), show(rec))


# ---- openssl, as sandbox-net.py has it ----------------------------------------------------------------------------------------------

def run_ssl(args, data=None):
    p = subprocess.run(["openssl"] + args, input=data, capture_output=True, timeout=60)
    if p.returncode != 0:
        raise RuntimeError("openssl %s failed: %s" % (" ".join(args[:3]), p.stderr.decode(errors="replace")[-300:]))
    return p.stdout


def make_key(path):
    run_ssl(["genpkey", "-algorithm", "EC", "-pkeyopt", "ec_paramgen_curve:P-256", "-out", path])


def make_cert(key, cert, cn, serial):
    run_ssl(["req", "-x509", "-new", "-key", key, "-out", cert, "-days", "2", "-subj", "/CN=" + cn, "-set_serial", str(serial)])


def expected_pin(cert):
    """The SHA-256 of the SubjectPublicKeyInfo, lower case hex, from the openssl command line, held to hashlib."""
    pub = run_ssl(["x509", "-in", cert, "-pubkey", "-noout"])
    der = run_ssl(["pkey", "-pubin", "-outform", "DER"], pub)
    dg = run_ssl(["dgst", "-sha256", "-binary"], der)
    if dg != hashlib.sha256(der).digest():
        raise RuntimeError("openssl dgst and hashlib disagree about the SubjectPublicKeyInfo of " + cert)
    return dg.hex()


def closed_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class PlainServer(threading.Thread):
    """A TCP server that is not TLS: it reads the ClientHello and answers with an HTTP error, which a TLS client cannot parse."""

    def __init__(self, life=900):
        threading.Thread.__init__(self, daemon=True)
        self.count = 0
        self.ended = threading.Event()
        self.deadline = time.time() + life
        self.lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.lsock.bind(("127.0.0.1", 0))
        self.lsock.listen(4)
        self.lsock.settimeout(0.1)
        self.port = self.lsock.getsockname()[1]
        self.start()

    def run(self):
        while not self.ended.is_set() and time.time() < self.deadline:
            try:
                conn, _a = self.lsock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            self.count += 1
            try:
                conn.settimeout(5)
                try:
                    conn.recv(4096)
                except OSError:
                    pass
                conn.sendall(b"HTTP/1.1 400 Bad Request\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
            except OSError:
                pass
            finally:
                try:
                    conn.close()
                except OSError:
                    pass
        try:
            self.lsock.close()
        except OSError:
            pass

    def shutdown(self):
        self.ended.set()
        self.join(timeout=5)


# ---- the driver -----------------------------------------------------------------------------------------------------------------------

DRIVER = r"""$include err.h
   obj = object('!sdclient')
   fns = ''
   v.host = '127.0.0.1' ; v.port = '' ; v.user = '' ; v.salt = '' ; v.iter = ''
   v.ck = '' ; v.sk = '' ; v.acct = '' ; v.pin = '' ; v.pw = ''
   crt 'FX begin'
   done = @false
   loop
      input ln
      done = (ln = 'END') or (ln = '' and status() = ER$EOF)
   until done do
      op = field(ln, '|', 1)
      a2 = field(ln, '|', 2)
      a3 = field(ln, '|', 3)
      a4 = field(ln, '|', 4)
      e = ''
      begin case
         case op = 'SET'
            begin case
               case a2 = 'host' ; v.host = a3
               case a2 = 'port' ; v.port = a3
               case a2 = 'user' ; v.user = a3
               case a2 = 'salt' ; v.salt = a3
               case a2 = 'iter' ; v.iter = a3
               case a2 = 'ck' ; v.ck = a3
               case a2 = 'sk' ; v.sk = a3
               case a2 = 'acct' ; v.acct = a3
               case a2 = 'pin' ; v.pin = a3
               case a2 = 'pw' ; v.pw = a3
            end case
         case op = 'KEYS'
            ok = obj->connect.keys(v.host, v.port, v.user, v.salt, v.iter, v.ck, v.sk, v.acct, v.pin)
            crt 'FX KEYS ok=':ok:' err=[':obj->error:']'
         case op = 'PW'
            ok = obj->connect(v.host, v.port, v.user, v.pw, v.acct)
            crt 'FX PW ok=':ok:' err=[':obj->error:']'
         case op = 'TMO'
            obj->settimeout(a2)
            crt 'FX TMO ':a2
         case op = 'QUIET'
            obj->quiet = (a2 = '1')
            crt 'FX QUIET ':a2
         case op = 'LERR'
            crt 'FX LERR ':obj->LastError:' text=[':obj->LastText:']'
         case op = 'OPEN'
            n = obj->open(a2)
            if a3 # '' then fns<a3> = n
            crt 'FX OPEN ':a2:' n=':n
         case op = 'READ' or op = 'READL' or op = 'READU'
            gosub getfn
            w = a4 + 0
            begin case
               case op = 'READ' ; rec = obj->read(fnum, a3, e)
               case op = 'READL' ; rec = obj->readl(fnum, a3, w, e)
               case op = 'READU' ; rec = obj->readu(fnum, a3, w, e)
            end case
            v = rec ; gosub shw
            crt 'FX ':op:' ':a3:' e=':e:' len=':len(rec):' rec=[':sv:']'
         case op = 'RLOCKED'
            gosub getfn
            n = obj->recordlocked(fnum, a3)
            crt 'FX RLOCKED ':a3:' n=':n
         case op = 'RELEASE'
            gosub getfn
            obj->release(fnum, a3)
            crt 'FX RELEASE ':a3
         case op = 'FLOCK'
            gosub getfn
            obj->filelock(fnum, a3 + 0)
            crt 'FX FLOCK ':a2:' wait=':a3:' err=':obj->LastError:' st=':obj->ServerStatus
         case op = 'FUNLOCK'
            gosub getfn
            obj->fileunlock(fnum)
            crt 'FX FUNLOCK ':a2:' err=':obj->LastError:' st=':obj->ServerStatus
         case op = 'SELECT'
            gosub getfn
            obj->select(fnum, a3)
            crt 'FX SELECT list=':a3
         case op = 'NEXT'
            rid = obj->readnext(a2, e)
            crt 'FX NEXT ':a2:' e=':e:' id=[':rid:']'
         case op = 'LIST'
            lst = obj->readlist(a2, e)
            v = lst ; gosub shw
            crt 'FX LIST ':a2:' e=':e:' [':sv:']'
         case op = 'CLEARSEL'
            obj->clearselect(a2)
            crt 'FX CLEARSEL ':a2
         case op = 'MARKS'
            gosub getfn
            obj->markmapping(fnum, a3)
            crt 'FX MARKS'
         case op = 'REV'
            r = obj->revision()
            v = r ; gosub shw
            crt 'FX REV [':sv:']'
         case op = 'CLOSE'
            gosub getfn
            obj->close(fnum)
            crt 'FX CLOSE ':a2
         case op = 'EXEC'
            r = obj->execute(a2, e)
            crt 'FX EXEC e=':e:' reply=[':r:']'
         case op = 'STAT'
            crt 'FX STAT ':obj->ServerStatus
         case op = 'ERR'
            crt 'FX ERR [':obj->error:']'
         case op = 'DISC'
            obj->disconnect
            crt 'FX DISC'
         case 1
            crt 'FX UNKNOWN ':op
      end case
   repeat
   crt 'FX end'
   stop

getfn: * FNUM = the file number held in slot A2, or the number itself when A2 is #n
   if a2[1,1] = '#' then
      fnum = a2[2,9]
   end else
      fnum = fns<a2>
   end
   return

shw: * SV = V with the four marks made visible, cut to its first and last 40 characters when over 100
   sv = v
   sv = change(sv, @im, '<I>')
   sv = change(sv, @fm, '<F>')
   sv = change(sv, @vm, '<V>')
   sv = change(sv, @sm, '<S>')
   if len(sv) > 100 then sv = sv[1,40] : '..' : sv[len(sv) - 39, 40]
   return

end
"""


# ---- one session --------------------------------------------------------------------------------------------------------------------

class Run:
    pass


def quiet(srv, limit=8.0):
    """Every connection the fake accepted has ended: nothing being dealt with, no live socket."""
    t0 = time.time()
    while time.time() - t0 < limit:
        with srv.lock:
            if srv.busy == 0 and not srv.live:
                return True
        time.sleep(0.05)
    return False


def bounded_sd(cwd, cmds, admin=False, internal=False, account=None, limit=120):
    """sandbox-gates.sd() with a bound that ends a session that does not come back CLEANLY (S.72b, 20 Oct 26).  g.sd waits 300 seconds and then kills the process outright, and a process killed in
    the middle of a call into the handler leaves what it held in the shared tables: on the unchanged tree ONE hung row (the class aborting inside $netfile, with MUSTLOCK left on in the process)
    made every later session of the sandbox hang, and the red run of the rows after it was worthless.  Here the session gets SIGHUP first (SD logs the user off and lets its locks go) and SIGKILL
    only if that does not end it in 10 seconds (MEASURED 20 Oct 26: SIGHUP did not end the hung session of the MUSTLOCK row, which is why mustlock_section runs LAST); the exception is the same one g.sd
    raises, so the callers' handling does not change.  The real inputs are printed as g.sd prints them."""
    argv = [g.SD] + (["-internal"] if internal else []) + (["-a" + account] if account else [])
    say("    > %s%s%s in %s: %s" % ("[admin] " if admin else "", "[internal] " if internal else "", ("-a" + account + " ") if account else "", os.path.relpath(cwd, g.BOX), " | ".join(cmds)))
    body = "\nTERM 200,9999\n" + "".join(c + "\n" for c in cmds) + "OFF\n"
    p = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd, env=g.env(admin), text=True, errors="replace")
    try:
        so, se = p.communicate(body, timeout=limit)
    except subprocess.TimeoutExpired:
        say("    [note] the session did not come back within %d seconds: SIGHUP" % limit)
        p.send_signal(signal.SIGHUP)
        try:
            p.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            say("    [note] ...and it did not end: SIGKILL (the sandbox may be wedged from here on)")
            p.kill()
            p.communicate()
        raise
    out = g.ANSI.sub("", so + se).split(":TERM 200,9999", 1)[-1]
    return [ln.rstrip() for ln in out.splitlines() if ln.strip() and not ln.startswith(":")]


def bounded_plain(acct, cmds, limit=120):
    return bounded_sd(os.path.join(g.BOX, "user_accounts", acct), cmds, account=acct, limit=limit)


def go(ops, srv, cfg=None, also=()):
    """Run the driver in the ordinary fixture account with these input lines against SRV configured as CFG (files=True unless it says
    otherwise).  Returns what the program printed (fx), what the fake saw (d, sessions), how long it took and whether every connection ended.
    ALSO are other fakes the program is going to dial: they are configured with files=True, and what they saw is r.dalso (a list of deltas)."""
    c = {"files": True}
    c.update(cfg or {})
    srv.configure(**c)
    for o in also:
        o.configure(files=True)
    m = srv.mark()
    ms = [o.mark() for o in also]
    t0 = time.time()
    hung = False
    try:
        out = bounded_plain(ACCT, ["RUN bp " + PROG] + list(ops) + ["END"], limit=300)
    except subprocess.TimeoutExpired:
        out, hung = [], True                    # (S.72b: a failed row, not the end of the run - see bounded_sd)
    el = time.time() - t0
    srv.settle(quiet=0.3)
    idle = quiet(srv)
    for o in also:
        o.settle(quiet=0.1)
        idle = quiet(o) and idle
    srv.configure()
    for o in also:
        o.configure()
    r = Run()
    r.dalso = [o.delta(mk) for o, mk in zip(also, ms)]
    r.out, r.d, r.el, r.idle, r.hung = out, srv.delta(m), el, idle, hung
    r.fx = [ln for ln in out if ln.startswith("FX ")]
    r.began = "FX begin" in r.fx
    r.ended = "FX end" in r.fx
    r.ses = r.d["sessions"]
    return r


def sane(r, need_end=True, allow_errors=False):
    """The driver ran (and ended unless the row expects an abort), the fake found nothing malformed, and no connection is left."""
    return r.began and (r.ended or not need_end) and (allow_errors or not r.d["errors"]) and r.idle


def why(r, n=8):
    return "driver began=%s ended=%s idle=%s fake errors=%r\n      fx: %r\n      tail: %r" % (r.began, r.ended, r.idle, r.d["errors"], r.fx[-n:], r.out[-3:])


def by_conn(d):
    out = {}
    for conn, t, _data in d["packets"]:
        out.setdefault(conn, []).append(t)
    return [out[k] for k in sorted(out)]


def sets(u, srv, acct="acct", pin=None, **ov):
    v = {"host": "127.0.0.1", "port": str(srv.port), "user": u["user"], "salt": u["salt"], "iter": str(u["it"]),
         "ck": u["ck_b64"], "sk": u["sk_b64"], "acct": acct, "pin": pin if pin is not None else S["pin"][id(srv)]}
    v.update(ov)
    return ["SET|%s|%s" % (k, val) for k, val in v.items()], v


def keys(u, srv, acct="acct", pin=None, **ov):
    return sets(u, srv, acct, pin, **ov)[0] + ["KEYS"]


def pwops(u, srv, acct="acct", pw=None):
    return ["SET|host|127.0.0.1", "SET|port|%d" % srv.port, "SET|user|%s" % u["user"], "SET|pw|%s" % (pw or u["pw"]), "SET|acct|%s" % acct, "PW"]


def fx_lines(r, op):
    return [ln for ln in r.fx if ln.startswith("FX %s " % op)]


def kline(ok, err):
    return "FX KEYS ok=%d err=[%s]" % (ok, err)


# ---- the setup ----------------------------------------------------------------------------------------------------------------------

def setup():
    if shutil.which("openssl") is None:
        row("SETUP: the openssl command line is needed to make the fake servers' certificates and the expected pins, and it is NOT installed: "
            "NONE of the rows can run", False, "install openssl and run again")
        return False
    work = tempfile.mkdtemp(prefix="sdnet-netfile-")
    S["work"] = work
    k1, k2, c1, c2 = (os.path.join(work, n) for n in ("k1.pem", "k2.pem", "c1.pem", "c2.pem"))
    try:
        make_key(k1)
        make_key(k2)
        make_cert(k1, c1, "sdnet-netfile-one", 21)
        make_cert(k2, c2, "sdnet-netfile-two", 22)
        pin_a, pin_b = expected_pin(c1), expected_pin(c2)
    except (RuntimeError, OSError, subprocess.SubprocessError) as e:
        row("SETUP: the certificates and the expected pins were made with the openssl command line", False, repr(e))
        return False
    A, B = netfake.FakeServer(c1, k1), netfake.FakeServer(c2, k2)
    S["A"], S["B"] = A, B
    S["certs"] = {id(A): (c1, k1), id(B): (c2, k2)}     # 20 Oct 26: netfake.PartialRecordServer is a TLS server of its own and needs a certificate and key
    S["pin"] = {id(A): pin_a, id(B): pin_b}
    S["pins"] = (pin_a, pin_b)
    for srv in (A, B):
        srv.store.add_file("customers", dict(RECS), dict_items=dict(DICT_ITEMS), path="/data/customers")
        srv.store.add_file("empty")
        srv.store.accounts = {"acct"}
        srv.revision = REVISION
    salt_a = A.add_user("alice", PW_ALICE, iterations=4096)
    salt_b = B.add_user("alice", PW_ALICE, iterations=4096)
    S["alice"] = {id(A): user_bundle("alice", PW_ALICE, salt_a), id(B): user_bundle("alice", PW_ALICE, salt_b)}
    salt_bob = b64(os.urandom(16))
    ck, sk = dk(PW_BOB, salt_bob, 4096)
    A.add_user_keys("bob", salt_bob, 4096, b64(hashlib.sha256(ck).digest()), b64(sk))           # the server knows Bob by keys alone
    S["bob"] = user_bundle("bob", PW_BOB, salt_bob)
    salt_carol = A.add_user("carol", PW_CAROL, iterations=4096, files_only=True)
    S["carol"] = user_bundle("carol", PW_CAROL, salt_carol)
    S["plain"] = PlainServer()
    S["dead"] = closed_port()
    say("  [note] fake API servers on 127.0.0.1: A %d, B %d (another key); a server that is not TLS %d; a closed port %d"
        % (A.port, B.port, S["plain"].port, S["dead"]))
    a = S["alice"][id(A)]
    nd = netfake.derive(PW_ALICE, a["salt"], 4096)
    row("SETUP: the independent computation (hashlib, hmac) agrees with netfake.derive for ClientKey and ServerKey, and the two pins are 64 lower case hex digits and differ",
        nd["client_key"] == a["ck"] and nd["server_key"] == a["sk"] and re.fullmatch(r"[0-9a-f]{64}", pin_a) and re.fullmatch(r"[0-9a-f]{64}", pin_b)
        and pin_a != pin_b and A.pin == pin_a and B.pin == pin_b, repr((pin_a, pin_b)))
    return True


def teardown():
    h_cleanup()
    for k in ("A", "B", "plain"):
        if k in S:
            S[k].shutdown()
    w = S.get("work")
    if w and os.path.isdir(w) and os.path.basename(w).startswith("sdnet-netfile-"):
        shutil.rmtree(w, ignore_errors=True)


# ---- A. the login from the stored keys, and the reads -------------------------------------------------------------------------------

def login_section():
    say("\n--- connect.keys with the right stored keys: logged in, the records read equal the store; connect(user, password) still works ---")
    A = S["A"]
    alice = S["alice"][id(A)]
    ops = keys(alice, A) + ["OPEN|customers|1", "READ|1|c1", "READ|1|c2", "READ|1|c3", "READ|1|m1", "READ|1|big",
                            "OPEN|dict customers|2", "READ|2|name", "DISC", "READ|1|c1"]
    r = go(ops, A)
    row("connect.keys with the stored salt, count, ClientKey and ServerKey and the right pin: 'ok=1 err=[]', and the driver reached its end",
        sane(r) and kline(1, "") in r.fx, why(r))
    d = r.d
    want_types = [47, 48, 3, 4, 6, 6, 6, 6, 6, 4, 6, 1]
    row("...the fake saw ONE connection, ONE handshake and exactly the packets 47, 48 (the login), 3 (the account), then the file requests the program made "
        "(4, five 6s, 4, 6) and 1 (quit) - and nothing for the READ after DISC; one proof verified, none refused",
        d["conns"] == 1 and d["handshakes"] == 1 and d["types"] == want_types and d["ok"] == 1 and d["bad"] == 0, repr(d["types"]))
    ses = r.ses[0] if r.ses else None
    row("...the session is alice's, in the account 'acct', not files-only, and it ended (the class closed its socket)",
        ses is not None and ses.user == "alice" and ses.account == "acct" and not ses.files_only and ses.closed and d["ok"] == 1 and d["bad"] == 0,
        repr(ses and (ses.user, ses.account, ses.files_only, ses.closed)))
    for rid in ("c1", "c2", "c3", "m1", "big"):
        row("the record %s read through the class equals the record in the store (%d bytes%s)" % (rid, len(RECS[rid]), ", the marks shown" if rid in ("c1", "m1") else ""),
            rl("READ", rid, 0, RECS[rid]) in r.fx, repr([x for x in r.fx if x.startswith("FX READ " + rid)]))
    row("OPEN customers gives file number 1, and OPEN 'dict customers' file number 2; READ through 2 reads the dictionary item",
        "FX OPEN customers n=1" in r.fx and "FX OPEN dict customers n=2" in r.fx and rl("READ", "name", 0, DICT_ITEMS["name"]) in r.fx, repr(r.fx[:12]))
    row("after DISC a READ is not sent: err -1, the null record, and the class says no connection was established",
        rl("READ", "c1", -1, "") in r.fx and any("no connection has been established" in ln for ln in r.out), repr(r.out[-4:]))
    ex = d["exchanges"][0] if d["exchanges"] else None
    packets = [p for p in d["packets"]]
    first = next((p[2] for p in packets if p[1] == 47), b"")
    final = next((p[2] for p in packets if p[1] == 48), b"")
    row("client-first is p=tls-exporter,,n=alice,r=<24 base64 characters>; client-final is c=<binding>,r=<the combined nonce>,p=<the proof>",
        re.fullmatch(rb"p=tls-exporter,,n=alice,r=[A-Za-z0-9+/]{24}", first) is not None and ex is not None
        and re.fullmatch(rb"c=[A-Za-z0-9+/=]+,r=[^,]+,p=[A-Za-z0-9+/]{43}=", final) is not None and ex["nonce"] == ex["cnonce"] + ex["snonce"], repr((first, final[:40])))
    row("...the ClientProof the class sent EQUALS the one computed here from the stored ClientKey alone (ClientKey XOR HMAC(SHA-256(ClientKey), AuthMessage)): "
        "the class proved itself without the password",
        ex is not None and ex["proof"] == my_proof(alice["ck"], ex["authmsg"]) and ex["verified"] is True, repr(ex and ex["proof"].hex()))

    # an upper-case pin is lowered; a pin with spaces round it is trimmed
    r = go(keys(alice, A, pin=S["pin"][id(A)].upper()) + ["OPEN|customers|1", "READ|1|c2", "DISC"], A)
    row("a pin typed in UPPER case is accepted (the class lowers it): logged in and a record read", sane(r) and kline(1, "") in r.fx and rl("READ", "c2", 0, RECS["c2"]) in r.fx, why(r))
    r = go(keys(alice, A, pin="  " + S["pin"][id(A)] + "  ") + ["OPEN|customers|1", "READ|1|c2", "DISC"], A)
    row("...and a pin with spaces round it is trimmed", sane(r) and kline(1, "") in r.fx, why(r))

    # a user the server knows by keys alone
    bob = S["bob"]
    r = go(keys(bob, A) + ["OPEN|customers|1", "READ|1|c1", "DISC"], A)
    row("a user the server holds by KEYS ALONE (no password on the server) logs in with the stored keys and reads a record",
        sane(r) and kline(1, "") in r.fx and rl("READ", "c1", 0, RECS["c1"]) in r.fx and r.d["ok"] == 1, why(r))

    # the password login of the same class
    r = go(pwops(alice, A) + ["OPEN|customers|1", "READ|1|c1", "READ|1|big", "DISC"], A)
    row("REGRESSION: obj->connect(host, port, user, password, account) still logs in against the same fake: 'ok=1', the records read equal the store",
        sane(r) and "FX PW ok=1 err=[]" in r.fx and rl("READ", "c1", 0, RECS["c1"]) in r.fx and rl("READ", "big", 0, RECS["big"]) in r.fx, why(r))
    ex = r.d["exchanges"][0] if r.d["exchanges"] else None
    row("...with the same packets (47, 48, 3, 4, 6, 6, 1) and a ClientProof equal to the one computed here from the typed password",
        r.d["types"] == [47, 48, 3, 4, 6, 6, 1] and ex is not None and ex["proof"] == my_proof(alice["ck"], ex["authmsg"]) and ex["verified"] is True, repr(r.d["types"]))
    r = go(pwops(alice, A, pw=PW_WRONG), A)
    row("REGRESSION: connect() with a wrong password: ok=0, the server's 'Authentication failed', the proof refused (47 then 48, one proof bad)",
        sane(r) and "FX PW ok=0 err=[Authentication failed]" in r.fx and r.d["types"] == [47, 48] and r.d["bad"] == 1 and r.d["ok"] == 0, why(r))
    B = S["B"]
    r = go(pwops(S["alice"][id(B)], B) + ["OPEN|customers|1", "READ|1|c3", "DISC"], B)
    row("REGRESSION: connect() asks for no pin: it logs in to the second server (another key) with no definition at all", sane(r) and "FX PW ok=1 err=[]" in r.fx
        and rl("READ", "c3", 0, RECS["c3"]) in r.fx, why(r))


# ---- B. arguments that are refused before the network is touched --------------------------------------------------------------------

def args_section():
    say("\n--- connect.keys refuses a bad argument before anything is dialled; a second connect on a connected object is refused ---")
    A = S["A"]
    alice = S["alice"][id(A)]
    base_sets, base = sets(alice, A)
    cases = [("host", "", "Invalid host name"), ("user", "bad user", "Invalid user name"), ("user", "", "Invalid user name"),
             ("pin", S["pin"][id(A)][:63], "Invalid public key pin"), ("pin", "g" * 64, "Invalid public key pin"), ("pin", S["pin"][id(A)] + "a", "Invalid public key pin"),
             ("pin", "", "Invalid public key pin"),
             ("salt", "", "The stored login is incomplete"), ("ck", "", "The stored login is incomplete"), ("sk", "", "The stored login is incomplete"),
             ("iter", "abc", "The stored iteration count is not a whole number"), ("iter", "", "The stored iteration count is not a whole number"),
             ("iter", "123456789", "The stored iteration count is not a whole number"), ("iter", "-5", "The stored iteration count is not a whole number"),
             ("iter", "40.96", "The stored iteration count is not a whole number"),
             ("iter", "4095", "The stored iteration count is unacceptable"), ("iter", "10000001", "The stored iteration count is unacceptable")]
    ops = list(base_sets)
    for f, bad, _t in cases:
        ops += ["SET|%s|%s" % (f, bad), "KEYS", "SET|%s|%s" % (f, base[f])]
    ops += ["KEYS", "KEYS", "OPEN|customers|1", "READ|1|c2", "DISC"]
    r = go(ops, A)
    got = fx_lines(r, "KEYS")
    want = [kline(0, t) for _f, _b, t in cases] + [kline(1, ""), kline(0, "A connection has already been established")]
    row("%d bad arguments, one at a time, each refused with its own text (host, user, pin, an incomplete login, the count): %d of %d lines as expected"
        % (len(cases), sum(1 for a, b in zip(got, want) if a == b), len(want)), sane(r) and got == want,
        "first difference: %r" % (next(((a, b) for a, b in zip(got, want) if a != b), None),))
    row("...NONE of them touched the network: the fake saw ONE connection in all (the good one), whose packets were 47, 48, 3, 4, 6, 1 - the second KEYS on a connected object sent nothing",
        r.d["conns"] == 1 and r.d["types"] == [47, 48, 3, 4, 6, 1], repr((r.d["conns"], r.d["types"])))
    row("...and the first connection was left usable by that refused second connect (a record read after it equals the store)", rl("READ", "c2", 0, RECS["c2"]) in r.fx, repr(r.fx[-4:]))


# ---- C. the pin ---------------------------------------------------------------------------------------------------------------------------

def pin_section():
    say("\n--- the pin: a server whose key is not the pinned one is sent NOTHING ---")
    A, B = S["A"], S["B"]
    alice_b = S["alice"][id(B)]
    alice_a = S["alice"][id(A)]
    pin_a = S["pin"][id(A)]
    near = pin_a[:-1] + ("0" if pin_a[-1] != "0" else "1")
    where = lambda srv: "PIN MISMATCH: the public key of 127.0.0.1:%d is not the key pinned in its definition; nothing was sent" % srv.port

    # server B presents key two and the stored pin is server A's
    r = go(keys(alice_b, B, pin=pin_a) + ["ERR"], B)
    row("server B presents key two, the stored pin is server A's: ok=0 and the error names a PIN MISMATCH with the host and port and says nothing was sent",
        sane(r) and fx_lines(r, "KEYS") == [kline(0, where(B))] and "FX ERR [%s]" % where(B) in r.fx, why(r))
    row("...THE FAKE RECEIVED NOTHING: one connection and a completed TLS handshake, ZERO request packets, ZERO application bytes (not even client-first), "
        "no proof, no session",
        r.d["conns"] == 1 and r.d["handshakes"] == 1 and r.d["types"] == [] and r.d["app_bytes"] == 0 and r.d["ok"] == 0 and r.d["bad"] == 0 and not r.ses, repr({k: r.d[k] for k in ("conns", "handshakes", "types", "app_bytes")}))

    # a pin one hex digit away
    r = go(keys(alice_a, A, pin=near), A)
    row("a pin one hex digit away from the right one on server A: the same refusal with A's port, and A received nothing (no packet, no byte)",
        sane(r) and fx_lines(r, "KEYS") == [kline(0, where(A))] and r.d["conns"] == 1 and r.d["types"] == [] and r.d["app_bytes"] == 0 and not r.ses, why(r))

    # the object is usable afterwards: a refusal, a refusal, then the right pin for B
    ops = keys(alice_b, B, pin=pin_a) + keys(alice_b, B, pin=near) + keys(alice_b, B) + ["OPEN|customers|1", "READ|1|c1", "DISC"]
    r = go(ops, B)
    kl = fx_lines(r, "KEYS")
    row("CONTROL: two refusals and then the right pin for B on the SAME object log in and read a record (so the refusals are the pin and not a broken server or a spoiled object)",
        sane(r) and kl == [kline(0, where(B)), kline(0, where(B)), kline(1, "")] and rl("READ", "c1", 0, RECS["c1"]) in r.fx, why(r))
    row("...the fake counted three connections, the first two with no packet at all, the third with 47, 48, 3, 4, 6, 1",
        r.d["conns"] == 3 and r.d["handshakes"] == 3 and by_conn(r.d) == [[47, 48, 3, 4, 6, 1]], repr((r.d["conns"], by_conn(r.d))))

    # a pin of digits only is a well formed pin, and a wrong one (the class compares text, with a letter put in front, because two numeric looking
    # strings would be compared as numbers; a server key whose hash is all digits cannot be made here, so only the refusal is shown)
    digits = "1" + "0" * 63
    r = go(keys(alice_a, A, pin=digits), A)
    row("a pin of 64 digits that is not the key's is refused as a mismatch like any other",
        sane(r) and fx_lines(r, "KEYS") == [kline(0, where(A))] and r.d["types"] == [], why(r))


# ---- D. the server's salt or count is not the stored one ----------------------------------------------------------------------------

def stale_section():
    say("\n--- the salt and the iteration count the server sends must EQUAL the stored ones: nothing further is sent ---")
    A = S["A"]
    alice = S["alice"][id(A)]
    salt_err = "The server's salt is not the stored one: the stored login is out of date or this is not the server it was made with"
    iter_err = "The server's iteration count is not the stored one: the stored login is out of date or this is not the server it was made with"
    r = go(keys(alice, A), A, cfg={"salt_text": "AAAAAAAAAAAAAAAAAAAAAA=="})
    row("the server offers a salt that is not the stored one: ok=0, the 'salt is not the stored one' text, and the fake saw ONLY client-first (47) - no proof, no account",
        sane(r) and kline(0, salt_err) in r.fx and r.d["types"] == [47] and r.d["ok"] == 0 and r.d["bad"] == 0 and not r.ses, why(r))
    r = go(keys(alice, A), A, cfg={"offer_iter": 5000})
    row("the server offers a count (5000) that is not the stored one (4096): the 'iteration count is not the stored one' text, only 47 sent",
        sane(r) and kline(0, iter_err) in r.fx and r.d["types"] == [47] and not r.ses, why(r))
    r = go(keys(alice, A, salt="AAAAAAAAAAAAAAAAAAAAAA=="), A)
    row("the STORED salt is the wrong one (the remote password changed, so the server's salt is a new one): the same refusal, only 47 sent",
        sane(r) and kline(0, salt_err) in r.fx and r.d["types"] == [47], why(r))
    r = go(keys(alice, A, iter="4097"), A)
    row("the STORED count is 4097 and the server's is 4096: the count refusal, only 47 sent", sane(r) and kline(0, iter_err) in r.fx and r.d["types"] == [47], why(r))
    r = go(keys(alice, A) + ["DISC"], A)
    row("CONTROL: the same stored values against the same server with nothing wrong log in (so the refusals above are the salt and the count and not a broken server)",
        sane(r) and kline(1, "") in r.fx and r.d["types"][:3] == [47, 48, 3], why(r))


# ---- E. wrong keys -------------------------------------------------------------------------------------------------------------------

def keys_section():
    say("\n--- a wrong ClientKey is refused by the server; a wrong ServerKey is refused by the class ---")
    A = S["A"]
    alice = S["alice"][id(A)]
    r = go(keys(alice, A, ck=b64(flip(alice["ck"]))), A)
    row("a wrong ClientKey: the proof does not verify, the server refuses it ('Authentication failed'), ok=0; the fake saw 47 and 48 and one BAD proof; no account was entered",
        sane(r) and kline(0, "Authentication failed") in r.fx and r.d["types"] == [47, 48] and r.d["bad"] == 1 and r.d["ok"] == 0 and not r.ses, why(r))
    r = go(keys(alice, A, ck=alice["sk_b64"], sk=alice["ck_b64"]), A)
    row("the two keys swapped: the same refusal by the server", sane(r) and kline(0, "Authentication failed") in r.fx and r.d["bad"] == 1, why(r))
    r = go(keys(alice, A, sk=b64(flip(alice["sk"]))), A)
    row("a wrong ServerKey: the server verified the proof (one good proof) and the CLASS refuses the server's signature: 'Server signature did not verify', ok=0",
        sane(r) and kline(0, "Server signature did not verify") in r.fx and r.d["types"] == [47, 48] and r.d["ok"] == 1 and r.d["bad"] == 0, why(r))
    row("...and it did not go on to enter the account: the fake's session for that login received NO request (3 was never sent) and ended",
        len(r.ses) == 1 and r.ses[0].requests == [] and r.ses[0].closed, repr([(s.requests, s.closed) for s in r.ses]))


# ---- F. the shared exchange: the same server faults, the same words from both logins --------------------------------------------------

def shared_section():
    say("\n--- the SCRAM exchange is one piece of code for both logins: every server fault gives the same text from connect.keys and from connect ---")
    A = S["A"]
    alice = S["alice"][id(A)]
    cases = [
        ("a nonce that does not extend ours", {"nonce": "wrong"}, "Server nonce does not extend the client nonce", [47]),
        ("a nonce that is ours and nothing more", {"nonce": "same"}, "Server nonce does not extend the client nonce", [47]),
        ("a server-first message with no attributes", {"first_raw": "garbage"}, "Malformed server-first message", [47]),
        ("an iteration count that is not a number", {"iter_text": "abc"}, "Server sent a non-numeric iteration count", [47]),
        ("an iteration count of 1", {"offer_iter": 1}, "Server asked for an unacceptable iteration count", [47]),
        ("an iteration count of 99999999", {"offer_iter": 99999999}, "Server asked for an unacceptable iteration count", [47]),
        ("a refusal of client-first with a text", {"first_error": (netfake.SV_ON_ERROR, "Go away")}, "Go away", [47]),
        ("a refusal of client-final with a text", {"final_error": (netfake.SV_ON_ERROR, "Nope")}, "Nope", [47, 48]),
        ("a WRONG v= signature", {"bad_v": True}, "Server signature did not verify", [47, 48]),
        ("an answer that is not v=", {"no_v": True}, "Server did not return a signature", [47, 48]),
    ]
    for label, cfg, text, types in cases:
        r = go(keys(alice, A) + pwops(alice, A), A, cfg=cfg)
        k = fx_lines(r, "KEYS")
        p = fx_lines(r, "PW")
        row("%s: connect.keys says '%s' and connect says the same; the fake saw %s from each" % (label, text, types),
            sane(r) and k == [kline(0, text)] and p == ["FX PW ok=0 err=[%s]" % text] and by_conn(r.d) == [types, types], "%r %r %r" % (k, p, by_conn(r.d)))


# ---- G. nothing there ----------------------------------------------------------------------------------------------------------------

def down_section():
    say("\n--- a server that cannot be reached, is not TLS, sends no Ack or goes away mid-login: a bounded wait and a text, never a hang ---")
    A = S["A"]
    alice = S["alice"][id(A)]
    dead, plain = S["dead"], S["plain"]
    r = go(keys(alice, A, port=str(dead)) + ["STAT"], A)
    m = re.fullmatch(r"FX KEYS ok=0 err=\[Cannot connect to 127\.0\.0\.1:%d \(status (\d+)\)\]" % dead, next(iter(fx_lines(r, "KEYS")), ""))
    row("a CLOSED port: ok=0 and 'Cannot connect to 127.0.0.1:<port> (status N)', and ServerStatus holds that N",
        sane(r) and m is not None and "FX STAT %s" % m.group(1) in r.fx and r.d["conns"] == 0, why(r))
    c0 = plain.count
    r = go(keys(alice, A, port=str(plain.port)) + ["STAT"], A)
    time.sleep(0.2)
    m = re.fullmatch(r"FX KEYS ok=0 err=\[The TLS handshake with 127\.0\.0\.1:%d did not complete \(status (\d+)\)\]" % plain.port, next(iter(fx_lines(r, "KEYS")), ""))
    row("a server that is NOT TLS: ok=0 and 'The TLS handshake with 127.0.0.1:<port> did not complete (status N)' (the open failed with no operating system error)",
        sane(r) and m is not None and "FX STAT %s" % m.group(1) in r.fx and plain.count == c0 + 1, why(r) + " plain accepted %d" % (plain.count - c0))
    no_ack = "No acknowledgement from 127.0.0.1:%d at the start of the session" % A.port
    r = go(["TMO|1500"] + keys(alice, A), A, cfg={"ack": False})
    row("a server that completes the handshake and never sends the Ack (settimeout 1500 first): ok=0, 'No acknowledgement', NOTHING sent (the class waits for the Ack before the first byte), "
        "and the wait was bounded (%.1f s)" % r.el, sane(r) and kline(0, no_ack) in r.fx and r.d["types"] == [] and r.el < 25, why(r))
    r = go(keys(alice, A), A, cfg={"close_after": "handshake"})
    row("a server that closes right after the handshake: the same text, nothing sent", sane(r) and kline(0, no_ack) in r.fx and r.d["types"] == [], why(r))
    lost = "No reply from 127.0.0.1:%d during the login (the connection failed or timed out)" % A.port
    for after, types in (("ack", None), ("first", [47]), ("final", [47, 48])):
        r = go(keys(alice, A), A, cfg={"close_after": after})
        row("the connection closes after %s: ok=0 and '%s', the socket is closed%s" % ({"ack": "the Ack byte", "first": "client-first", "final": "client-final"}[after], lost[:34] + "...",
                                                                                           "" if types is None else ", the fake saw %s" % types),
            sane(r) and kline(0, lost) in r.fx and (types is None or r.d["types"] == types), why(r))
    r = go(keys(alice, A) + ["DISC"], A)
    row("CONTROL: after all of those the same fake, with nothing wrong, logs in (so none of the refusals above left the fake or the class in a state)", sane(r) and kline(1, "") in r.fx, why(r))


# ---- H. the connection goes away in the middle ----------------------------------------------------------------------------------------

def close_section():
    say("\n--- a connection that closes or falls silent in the middle: the next request fails with an error the PROGRAM sees, and nothing hangs ---")
    A = S["A"]
    alice = S["alice"][id(A)]
    ops = keys(alice, A) + ["OPEN|customers|1", "READ|1|c1", "READ|1|c2", "OPEN|customers|2", "READ|1|c3", "ERR", "DISC"]
    r = go(ops, A, cfg={"close_after_requests": 3})
    row("the server replies to the 3rd request and closes: that READ is right (c1), the NEXT READ gives err=-1 and the null record, a new OPEN gives 0, and a READ after it -1 again",
        sane(r) and rl("READ", "c1", 0, RECS["c1"]) in r.fx and rl("READ", "c2", -1, "") in r.fx and "FX OPEN customers n=0" in r.fx and rl("READ", "c3", -1, "") in r.fx, why(r))
    row("...the program is told only by err (the error property stays null), DISC after a dead connection returns, and the fake saw 3, 4, 6 and nothing after the close",
        "FX ERR []" in r.fx and "FX DISC" in r.fx and r.ses and r.ses[0].requests == [3, 4, 6] and r.ses[0].closed and r.el < 30, repr((r.fx[-4:], [s.requests for s in r.ses], r.el)))
    r = go(keys(alice, A) + ["OPEN|customers|1", "READ|1|c1", "READ|1|c2", "DISC"], A, cfg={"drop_request": 3})
    row("the server reads the 3rd request and closes WITHOUT replying: that READ gives err=-1 (no hang), and so does the next one",
        sane(r) and rl("READ", "c1", -1, "") in r.fx and rl("READ", "c2", -1, "") in r.fx and r.ses and r.ses[0].requests == [3, 4, 6] and r.el < 30, why(r))
    r = go(["TMO|1500"] + keys(alice, A) + ["OPEN|customers|1", "READ|1|c1", "OPEN|customers|2", "DISC"], A, cfg={"no_reply": (6,)})
    row("a server that never answers a READ (settimeout 1500): the READ gives err=-1 within seconds (%.1f s for the session, not the 30 s default), and the next request is answered: OPEN gives 2" % r.el,
        sane(r) and rl("READ", "c1", -1, "") in r.fx and "FX OPEN customers n=2" in r.fx and r.el < 25 and r.ses and r.ses[0].injected == [(6, "no_reply")]
        and r.ses[0].requests == [3, 4, 6, 4, 1], why(r) + " requests %r" % [s.requests for s in r.ses])
    r = go(keys(alice, A) + ["OPEN|customers|1", "DISC", "READ|1|c1", "OPEN|customers|2"], A)
    row("after DISC the object is disconnected: READ gives err=-1 with the class's own 'no connection' message, OPEN gives 0, and nothing more is sent (3, 4, 1)",
        sane(r) and rl("READ", "c1", -1, "") in r.fx and "FX OPEN customers n=0" in r.fx and any("no connection has been established" in ln for ln in r.out)
        and r.ses and r.ses[0].requests == [3, 4, 1], why(r))
    r = go(keys(alice, A) + ["OPEN|customers|1", "READ|1|c1"], A)
    row("a session that never calls DISC: the driver ends, and the fake sees the connection END all the same (no socket left open)", sane(r) and r.ses and r.ses[0].closed, why(r))


# ---- I. not found, bad numbers ---------------------------------------------------------------------------------------------------------

def notfound_section():
    say("\n--- records and files that are not there, file numbers that are not open, ids the class refuses itself ---")
    A = S["A"]
    alice = S["alice"][id(A)]
    long_id = "x" * 64
    ops = keys(alice, A) + ["OPEN|customers|1", "READ|1|nosuch", "STAT", "OPEN|nosuch|2", "STAT", "ERR", "READ|1|" + long_id, "STAT", "READ|1|", "CLOSE|1", "READ|1|c1", "ERR",
                            "READ|#99|c1", "ERR", "DISC"]
    r = go(ops, A)
    row("READ of an id that is not there: err=2 (the ELSE case), the null record, ServerStatus 3006 (record not found)",
        sane(r) and rl("READ", "nosuch", 2, "") in r.fx and "FX STAT 3006" in r.fx, why(r))
    row("OPEN of a file that is not there: 0, ServerStatus 3003 (file not found), and the error property stays null", "FX OPEN nosuch n=0" in r.fx and "FX STAT 3003" in r.fx and "FX ERR []" in r.fx, repr(r.fx))
    row("READ of a 64 character id and of a null id: refused by the class itself (err=1, ServerStatus 3000) and NOT SENT",
        rl("READ", long_id, 1, "") in r.fx and rl("READ", "", 1, "") in r.fx and "FX STAT 3000" in r.fx, repr(r.fx[8:14]))
    row("READ through a file number that was closed, and through one that was never opened: err=-1, the null record, and the error property holds the server's own text (message 5268)",
        rl("READ", "c1", -1, "") in r.fx and r.fx.count("FX ERR [%s]" % msg(5268)) == 2, repr(r.fx[-6:]))
    row("...the fake saw exactly: 3, 4, 6 (nosuch), 4 (the file that is not there), 5 (close), 6 and its error text 2, 6 and 2, 1 - and no request for the two ids the class refused",
        r.ses and r.ses[0].requests == [3, 4, 6, 4, 5, 6, 2, 6, 2, 1], repr([s.requests for s in r.ses]))


# ---- J. the files-only login ------------------------------------------------------------------------------------------------------------

def files_section():
    say("\n--- the files-only switch of the fake (the SDNet login): execute and call are refused with message 11480, and the class sees it ---")
    A = S["A"]
    carol = S["carol"]
    alice = S["alice"][id(A)]
    r = go(keys(carol, A) + ["OPEN|customers|1", "READ|1|c1", "REV", "DISC"], A)
    row("[S72b-N1a] a files-only user logs in through connect.keys (the account request 3 is allowed once), opens and reads a record and asks the revision - nothing is refused, and no request 34 is "
        "sent (it used to test a lock here: since S.72b request 34 needs the write group, the next rows)",
        sane(r) and kline(1, "") in r.fx and rl("READ", "c1", 0, RECS["c1"]) in r.fx and r.ses and r.ses[0].files_only and r.ses[0].refused == [] and 6 in r.ses[0].requests
        and 34 not in r.ses[0].requests, why(r))
    # S.72b: request 34 is in the change set of gpl.bp/apifilesok.  Without sdfileswrite the fake refuses it (ON ERROR, message 11521) and, as for the other requests of the set, the class not being
    # quiet aborts the program.  WITH the group, and for a login that is not files-only, it is served (the controls).
    r = go(keys(carol, A) + ["OPEN|customers|1", "READ|1|c1", "RLOCKED|1|c1", "REV", "DISC"], A)
    row("[S72b-N1b] RECORDLOCKED through a files-only login WITHOUT sdfileswrite (carol, the class not quiet): the READ before it was served, then the class aborts the program ('RECORDLOCKED generated "
        "an abort event') - the fake refused request 34 and nothing else (refused [34], audit 'api refused request=34 route=sdfiles write=off user=carol'), the requests were 3, 4, 6, 34 and the Quit the "
        "class sends when the aborted program ends, and the driver did not reach its end",
        r.began and not r.ended and any("RECORDLOCKED generated an abort event" in ln for ln in r.out) and rl("READ", "c1", 0, RECS["c1"]) in r.fx and not fx_lines(r, "RLOCKED") and r.ses
        and r.ses[0].refused == [34] and r.ses[0].audit == ["api refused request=34 route=sdfiles write=off user=carol"] and r.ses[0].requests == [3, 4, 6, 34, 1] and not r.d["errors"] and r.idle,
        why(r) + " refused %r audit %r requests %r out %r" % ([s.refused for s in r.ses], [s.audit for s in r.ses], [s.requests for s in r.ses], r.out[-4:]))
    r = go(keys(carol, A) + ["OPEN|customers|1", "READ|1|c1", "RLOCKED|1|c1", "REV", "DISC"], A, cfg={"write_group": True})
    row("...CONTROL, the same login IN sdfileswrite (the connection's write_group): RECORDLOCKED is served (n=0), the driver reaches its end, nothing is refused and request 34 was sent",
        sane(r) and "FX RLOCKED c1 n=0" in r.fx and r.ses and r.ses[0].files_only and r.ses[0].refused == [] and r.ses[0].audit == [] and 34 in r.ses[0].requests, why(r))
    r = go(keys(alice, A) + ["OPEN|customers|1", "READ|1|c1", "RLOCKED|1|c1", "REV", "DISC"], A)
    row("...CONTROL, a login that is NOT files-only (alice: the sdapi route, untouched by the write group): RECORDLOCKED is served (n=0), nothing is refused and request 34 was sent",
        sane(r) and "FX RLOCKED c1 n=0" in r.fx and r.ses and not r.ses[0].files_only and r.ses[0].refused == [] and r.ses[0].audit == [] and 34 in r.ses[0].requests, why(r))
    r = go(keys(carol, A) + ["OPEN|customers|1", "EXEC|who"], A)
    row("EXECUTE through a files-only login: the class aborts ('EXECUTE generated an abort event') and the driver does not reach its end; the fake refused request 21, never dispatched it",
        r.began and not r.ended and any("EXECUTE generated an abort event" in ln for ln in r.out) and not fx_lines(r, "EXEC") and r.ses and r.ses[0].refused == [21]
        and r.ses[0].requests == [3, 4, 21, 1] and not r.d["errors"] and r.idle,        # the 1 is the Quit the class sends when the aborted program ends
        why(r) + " refused %r requests %r out %r fx %r" % ([s.refused for s in r.ses], [s.requests for s in r.ses], r.out[-6:], r.fx[-4:]))
    r = go(keys(alice, A) + ["EXEC|who", "DISC"], A)
    row("CONTROL: the same EXECUTE from a user who is NOT files-only is not refused by the gate (nothing in refused; the request reaches the fake's dispatch, which says it does not build 21), "
        "so the refusal above is the files-only switch (the reply is a SV$ERROR, whose text the class fetches with request 2; EXECUTE then returns err = 0, because that fetch "
        "overwrote the server's error code - a quirk of the class, shown here so that no caller relies on err after an SV$ERROR)", sane(r, allow_errors=True) and r.ses and r.ses[0].refused == [] and r.ses[0].requests == [3, 21, 2, 1]
        and r.d["errors"] == ["request 21 is not built in netfake"] and "FX EXEC e=0 reply=[]" in r.fx, why(r) + " requests %r" % [s.requests for s in r.ses])
    # the text of the refusal, from the fake's own Python client (the class has no way to show it)
    A.configure(files=True)
    cl = None
    try:
        cl = netfake.ApiClient(A.port, timeout=10)
        res = cl.login("carol", PW_CAROL)
        e20 = cl.req(20, b"\x00\x00")
        e21 = cl.req(21, b"who")
        a1 = cl.req(3, b"acct")
        a2 = cl.req(3, b"acct")
        o = cl.req(4, b"customers")
        cl.req(1)
    except (EOFError, OSError, RuntimeError) as e:
        res, e20, e21, a1, a2, o = ("error", repr(e)), None, None, None, None, None
    finally:
        if cl is not None:
            cl.close()
        A.configure()
    row("(the fake's own Python client, because the class cannot show the text) CALL (20) and EXECUTE (21) from the files-only user are ON ERROR replies whose data is message 11480 with the "
        "request number: '%s'" % msg(11480, 21),
        res[0] == "ok" and e20 == (1, 0, msg(11480, 20).encode("latin-1")) and e21 == (1, 0, msg(11480, 21).encode("latin-1")), repr((res, e20, e21)))
    row("...SET ACCOUNT (3) is allowed once and the second time is refused with 11480 (a LOGTO); OPEN still works after a refusal",
        a1 == (0, 0, b"") and a2 == (1, 0, msg(11480, 3).encode("latin-1")) and o is not None and o[0] == 0, repr((a1, a2, o)))
    quiet(A)
    # S.72b: the text of the refusal of request 34, from the fake's own client (the class aborts before it can show it), without the group and, as the null case, with it
    got = {}
    for grp in (False, True):
        A.configure(files=True, write_group=grp)
        cl = None
        try:
            cl = netfake.ApiClient(A.port, timeout=10)
            lg = cl.login("carol", PW_CAROL)
            cl.req(3, b"acct")
            op = cl.req(4, b"customers")
            rk = cl.req(34, FNO(1) + b"c1")
            cl.req(1)
            got[grp] = (lg[0], op[0], rk)
        except (EOFError, OSError, RuntimeError) as e:
            got[grp] = ("error", repr(e), None)
        finally:
            if cl is not None:
                cl.close()
            A.configure()
    row("[S72b-N1c] (the fake's own Python client) request 34 (recordlocked) from the files-only user WITHOUT the group is an ON ERROR reply whose data is message 11521 with the request number: '%s'; "
        "the same request from the same user IN the group is served (error field 0)" % msg(11521, 34),
        got[False][0] == "ok" and got[False][1] == 0 and got[False][2] == (1, 0, msg(11521, 34).encode("latin-1")) and got[True][0] == "ok" and got[True][1] == 0
        and got[True][2] is not None and got[True][2][0] == 0, repr(got))
    quiet(A)


# ---- K. the account ---------------------------------------------------------------------------------------------------------------------

def account_section():
    say("\n--- entering the account ---")
    A = S["A"]
    alice = S["alice"][id(A)]
    ops = keys(alice, A, acct="other") + ["ERR", "SET|acct|ACCT", "KEYS", "OPEN|customers|1", "READ|1|c3", "DISC"]
    r = go(ops, A)
    refused = msg(10003)
    row("an account the server will not let this user enter: ok=0 and the error property holds the server's own text (message 10003: '%s')" % refused,
        sane(r) and kline(0, refused) in r.fx and "FX ERR [%s]" % refused in r.fx, why(r))
    row("...the login itself had succeeded, the class asked for the account (3) and then for the error text (2), the connection was CLOSED by the class (the session ended), "
        "and no account was recorded for it",
        len(r.ses) == 2 and r.ses[0].requests == [3, 2] and r.ses[0].account is None and r.ses[0].closed, repr([(s.requests, s.account, s.closed) for s in r.ses]))
    row("...and the same object then connects to the account typed in upper case (ACCT): the fake lower-cases it, ok=1, a record is read",
        kline(1, "") in r.fx and len(r.ses) == 2 and r.ses[1].account == "acct" and rl("READ", "c3", 0, RECS["c3"]) in r.fx, why(r))


# ---- L. locks -------------------------------------------------------------------------------------------------------------------------------

def locks_section():
    say("\n--- record locks: held by this session and by another process; the LOCKED case and RECORDLOCKED; released when the connection ends ---")
    A = S["A"]
    st = A.store
    alice = S["alice"][id(A)]
    st.hold("customers", "c2", 7, "update")
    st.hold("customers", "c3", 8, "shared")
    try:
        ops = (keys(alice, A) + ["OPEN|customers|1", "READL|1|c2|0", "STAT", "READU|1|c2|0", "READ|1|c2", "RLOCKED|1|c2", "READL|1|c3|0", "RLOCKED|1|c3",
                                 "READU|1|c3|0", "STAT", "READU|1|c1|0", "RLOCKED|1|c1", "READL|1|c1|1", "RELEASE|1|c1", "RLOCKED|1|c1", "DISC"])
        r = go(ops, A)
        row("a record another process holds for UPDATE: READL with no wait gives err=4 (LOCKED) and the null record, and ServerStatus is that process's user number (7)",
            sane(r) and rl("READL", "c2", 4, "") in r.fx and "FX STAT 7" in r.fx, why(r))
        row("...READU is LOCKED the same; a plain READ ignores the lock and reads; RECORDLOCKED says -2 (another user's update lock)",
            rl("READU", "c2", 4, "") in r.fx and rl("READ", "c2", 0, RECS["c2"]) in r.fx and "FX RLOCKED c2 n=-2" in r.fx, repr(r.fx[8:14]))
        row("a record another process holds for READ only: READL shares it (err=0, the record), RECORDLOCKED says 1 (this session holds a read lock), READU is LOCKED and ServerStatus is the other holder (8)",
            rl("READL", "c3", 0, RECS["c3"]) in r.fx and "FX RLOCKED c3 n=1" in r.fx and rl("READU", "c3", 4, "") in r.fx and "FX STAT 8" in r.fx, repr(r.fx[14:20]))
        i2 = r.fx.index("FX RLOCKED c1 n=2") if "FX RLOCKED c1 n=2" in r.fx else -1
        i0 = r.fx.index("FX RLOCKED c1 n=0") if "FX RLOCKED c1 n=0" in r.fx else -1
        row("a free record: READU takes it (err=0, the record) and RECORDLOCKED says 2; READL with the wait flag (request 8) on it takes the lock down to a read lock at once; "
            "RELEASE lets it go and RECORDLOCKED then says 0",
            rl("READU", "c1", 0, RECS["c1"]) in r.fx and rl("READL", "c1", 0, RECS["c1"]) in r.fx and 0 <= i2 < i0, repr(r.fx[-8:]))
        ses = r.ses[0] if r.ses else None
        row("...the fake's lock table: nothing is left held by this connection (it ended), and the two holds planted for the other processes are still there",
            ses is not None and ses.closed and A.store.locks_of(ses.userno) == [] and ("customers", "c2", "update") in A.store.locks_of(7) and ("customers", "c3", "shared") in A.store.locks_of(8),
            repr(ses and A.store.locks_of(ses.userno)))
        ops = keys(alice, A) + ["OPEN|customers|1", "READU|1|c1|0", "READL|1|c3|0"]
        r = go(ops, A)
        ses = r.ses[0] if r.ses else None
        row("a session that ends while it holds locks (no RELEASE, no DISC): the fake lets them go when the connection ends",
            sane(r) and ses is not None and ses.closed and A.store.locks_of(ses.userno) == [] and A.store.locks_of(8) == [("customers", "c3", "shared")], repr(ses and A.store.locks_of(ses.userno)))
    finally:
        st.drop_user(7)
        st.drop_user(8)
    class_filelocks(A, alice)


def class_filelocks(A, alice):
    """S.72 (20 Oct 26): FILELOCK and FILEUNLOCK through the class, requests 32 and 33, against the fake, whose answers are held to the real server by sandbox-req29.py section F.
    The class sends the wait flag it is given; the HANDLER only ever gives it 0 (the next sections).  Expected values are written from the spec, never from the reply."""
    say("\n  -- FILELOCK / FILEUNLOCK (S.72): the class methods filelock(fno, wait) and fileunlock(fno), requests 32 and 33 --")
    st = A.store

    def w32(fno, wait=0):
        return (32, FNO(fno) + struct.pack("<h", wait))

    ops = keys(alice, A) + ["OPEN|customers|1", "FLOCK|1|0", "RLOCKED|1|c1", "FLOCK|1|0", "FUNLOCK|1", "RLOCKED|1|c1", "FUNLOCK|1", "DISC"]
    r = go(ops, A)
    row("FILELOCK (wait 0) on a free file: the reply is OK (LastError 0); RECORDLOCKED of any record then says 3 (this session holds the file lock); FILELOCK again is OK (already ours); "
        "FILEUNLOCK is OK with ServerStatus 0 and RECORDLOCKED says 0; a second FILEUNLOCK is OK with ServerStatus 3012 (ER$NLK: nobody holds it)",
        sane(r) and fx_lines(r, "FLOCK") == ["FX FLOCK 1 wait=0 err=0 st=0", "FX FLOCK 1 wait=0 err=0 st=0"]
        and fx_lines(r, "RLOCKED") == ["FX RLOCKED c1 n=3", "FX RLOCKED c1 n=0"] and fx_lines(r, "FUNLOCK") == ["FX FUNLOCK 1 err=0 st=0", "FX FUNLOCK 1 err=0 st=3012"], why(r))
    exp = [(3, b"acct"), (4, b"customers"), w32(1), (34, FNO(1) + b"c1"), w32(1), (33, FNO(1)), (34, FNO(1) + b"c1"), (33, FNO(1)), (1, b"")]
    row("...THE REQUESTS: 32 carries the file number and the wait flag as two 16 bit numbers (1, 0), 33 the file number only, and RECORDLOCKED (34) is asked in between", h_wire(r.d) == exp,
        "first difference: %r" % (next(((a, b) for a, b in zip(h_wire(r.d), exp) if a != b), (len(h_wire(r.d)), len(exp))),))
    ses = r.ses[0] if r.ses else None
    row("...the file lock is not left behind: the fake's table has no file lock for this connection, and the file name is free", ses is not None and st.filelocks.get("customers") is None, repr(dict(st.filelocks)))

    # another user holds the file lock: LOCKED with the holder in ServerStatus, FILEUNLOCK leaves it alone and says so
    st.hold_file("customers", 7)
    try:
        ops = keys(alice, A) + ["OPEN|customers|1", "FLOCK|1|0", "RLOCKED|1|c1", "FUNLOCK|1", "RLOCKED|1|c1", "DISC"]
        r = go(ops, A)
        row("a file lock held by another user (7): FILELOCK (wait 0) is LOCKED (LastError 4) with ServerStatus 7 (the holder); RECORDLOCKED says -3; FILEUNLOCK is OK with ServerStatus 3011 "
            "(ER$LCK: the lock is another user's) and the lock stays (-3 again)",
            sane(r) and fx_lines(r, "FLOCK") == ["FX FLOCK 1 wait=0 err=4 st=7"] and fx_lines(r, "RLOCKED") == ["FX RLOCKED c1 n=-3", "FX RLOCKED c1 n=-3"]
            and fx_lines(r, "FUNLOCK") == ["FX FUNLOCK 1 err=0 st=3011"] and st.filelocks.get("customers") == 7, why(r))
    finally:
        st.drop_user(7)

    # a record lock another user holds in the file keeps a file lock from being taken
    st.hold("customers", "c2", 8, "update")
    try:
        r = go(keys(alice, A) + ["OPEN|customers|1", "FLOCK|1|0", "DISC"], A)
        row("an update lock another user (8) holds on a record of the file: FILELOCK (wait 0) is LOCKED with ServerStatus 8", sane(r) and fx_lines(r, "FLOCK") == ["FX FLOCK 1 wait=0 err=4 st=8"]
            and st.filelocks.get("customers") is None, why(r))
    finally:
        st.drop_user(8)

    # closing the file number that took the lock lets it go; closing another number of the same file does not
    ops = keys(alice, A) + ["OPEN|customers|1", "OPEN|customers|2", "OPEN|customers|3", "FLOCK|1|0", "FLOCK|2|0", "CLOSE|2", "RLOCKED|3|c1", "CLOSE|1", "RLOCKED|3|c1", "DISC"]
    r = go(ops, A)
    row("CLOSE of the file number that took the file lock releases it, CLOSE of another number of the same file does not: the lock is taken through 1 and asked for again through 2 (OK both), "
        "after CLOSE 2 RECORDLOCKED through a third number says 3 (this session still holds it), after CLOSE 1 it says 0",
        sane(r) and fx_lines(r, "RLOCKED") == ["FX RLOCKED c1 n=3", "FX RLOCKED c1 n=0"] and fx_lines(r, "FLOCK") == ["FX FLOCK 1 wait=0 err=0 st=0", "FX FLOCK 2 wait=0 err=0 st=0"], why(r))

    # a session that ends while it holds the file lock lets it go
    r = go(keys(alice, A) + ["OPEN|customers|1", "FLOCK|1|0"], A)
    ses = r.ses[0] if r.ses else None
    row("a session that ends while it holds the file lock (no FILEUNLOCK, no CLOSE): the fake lets it go with the connection", sane(r, need_end=False) and ses is not None and ses.closed
        and st.filelocks.get("customers") is None and any(x == "FX FLOCK 1 wait=0 err=0 st=0" for x in r.fx), why(r) + repr(dict(st.filelocks)))

    # a login WITHOUT the write group on the target: both are refused with 11521 (an ON ERROR reply), and the class says so when it is quiet
    carol = S["carol"]
    r = go(keys(carol, A) + ["QUIET|1", "OPEN|customers|1", "FLOCK|1|0", "LERR", "FUNLOCK|1", "LERR", "DISC"], A)
    t32, t33, t34 = msg(11521, 32), msg(11521, 33), msg(11521, 34)
    row("a files-only login WITHOUT sdfileswrite: FILELOCK and FILEUNLOCK take the ON ERROR reply (LastError 1) with the text of message 11521 and the request number (32, 33) - no abort for a quiet caller",
        sane(r) and any(x.startswith("FX LERR 1 text=[%s" % t32) for x in r.fx) and any(x.startswith("FX LERR 1 text=[%s" % t33) for x in r.fx) and r.ses and r.ses[0].refused == [32, 33],
        why(r) + repr([s.refused for s in r.ses]))
    r = go(keys(carol, A) + ["QUIET|1", "OPEN|customers|1", "RLOCKED|1|c1", "LERR", "DISC"], A)
    lerr = fx_lines(r, "LERR")
    row("[S72b-N2] ...RECORDLOCKED too (request 34 is in the change set since S.72b): a QUIET class does not abort - the driver reaches its end, the call returns 0 - and leaves LastError 1 and LastText = "
        "the text of message 11521 with the request number 34 (the handler reads them to say 'Server nfw answered recordlocked with an error'); the fake refused 34 and audited it",
        sane(r) and fx_lines(r, "RLOCKED") == ["FX RLOCKED c1 n=0"] and len(lerr) == 1 and lerr[0].startswith("FX LERR 1 text=[%s" % t34) and r.ses and r.ses[0].refused == [34]
        and r.ses[0].audit == ["api refused request=34 route=sdfiles write=off user=carol"], why(r) + repr([(s.refused, s.audit) for s in r.ses]) + repr(lerr))


# ---- M. select lists --------------------------------------------------------------------------------------------------------------------------

def lists_section():
    say("\n--- SELECT, READNEXT, READLIST, CLEARSELECT: the ids the store holds, one by one and all at once ---")
    A = S["A"]
    alice = S["alice"][id(A)]
    ids = sorted(RECS)
    ops = (keys(alice, A) + ["OPEN|customers|1", "SELECT|1|0"] + ["NEXT|0"] * (len(ids) + 1) + ["SELECT|1|4", "NEXT|4", "LIST|4", "LIST|4", "NEXT|4",
                                                                                                "SELECT|1|2", "CLEARSEL|2", "NEXT|2", "SELECT|1|11", "ERR", "OPEN|empty|2", "SELECT|2|3", "NEXT|3", "DISC"])
    r = go(ops, A)
    nx = fx_lines(r, "NEXT")
    got = [re.fullmatch(r"FX NEXT 0 e=0 id=\[(.*)\]", ln).group(1) for ln in nx[:len(ids)] if re.fullmatch(r"FX NEXT 0 e=0 id=\[(.*)\]", ln)]
    row("SELECT the file into list 0 and READNEXT: every id of the store comes out once (%s - the ORDER is the fake's, not a claim about SD) and the next call is e=2 (end of list)" % ",".join(ids),
        sane(r) and sorted(got) == ids and nx[len(ids)] == "FX NEXT 0 e=2 id=[]", repr(nx))
    n4 =[ln for ln in nx if ln.startswith("FX NEXT 4 ")]
    lst = [ln for ln in r.fx if ln.startswith("FX LIST 4 ")]
    one = re.fullmatch(r"FX NEXT 4 e=0 id=\[(.*)\]", n4[0]) if n4 else None
    rest = re.fullmatch(r"FX LIST 4 e=0 \[(.*)\]", lst[0]) if lst else None
    rest_ids = rest.group(1).split("<F>") if rest else []
    row("READNEXT once from list 4, then READLIST: the REST of the list (%d ids, field marks between), the list is used up (a second READLIST is null, READNEXT is e=2)" % (len(ids) - 1),
        one is not None and rest is not None and sorted(rest_ids + [one.group(1)]) == ids and len(lst) == 2 and lst[1] == "FX LIST 4 e=0 []" and n4[-1] == "FX NEXT 4 e=2 id=[]", repr((n4, lst)))
    row("CLEARSELECT empties a list: READNEXT after it is e=2", "FX NEXT 2 e=2 id=[]" in r.fx, repr(r.fx[-9:]))
    row("a list number the server does not have (11): the select fails, the error property holds the server's text (message 5269) and the program goes on",
        "FX ERR [%s]" % msg(5269) in r.fx, repr(r.fx[-6:]))
    row("an empty file selects nothing: READNEXT on its list is e=2, and the driver went on to its end after the refused select",
        "FX OPEN empty n=2" in r.fx and "FX NEXT 3 e=2 id=[]" in r.fx and sane(r), repr(r.fx[-5:]))

    # 19 Oct 26, finish 2 (verifier): select() and readlist() honour `quiet` as read(), write() and delete() do.  A server ON ERROR reply to either used to ABORT the caller even from a quiet
    # object, so the $netfile handler's own branch for it (act.select) could never run.  The fake answers request 11 (SELECT) or 14 (READLIST) with an ON ERROR carrying the text 'boom'.
    open_ops = ["OPEN|customers|1"]
    for req, nm, abort_text, ops_after in ((14, "READLIST", "READLIST generated an abort event", ["SELECT|1|4", "LIST|4"]), (11, "SELECT", "SELECT generated an abort event", ["SELECT|1|4"])):
        cfg = {"fail": {req: (netfake.SV_ON_ERROR, "boom")}}
        r = go(keys(alice, A) + open_ops + ops_after, A, cfg=cfg)
        row("CONTROL (the default object is not quiet): a server ON ERROR reply to %s ABORTS the program as it always did - '%s' - and the driver does not reach its end" % (nm, abort_text),
            sane(r, need_end=False) and any(abort_text in ln for ln in r.out) and not r.ended and r.d["types"].count(req) == 1, why(r))
        r = go(keys(alice, A) + ["QUIET|1"] + open_ops + ops_after + ["LERR", "DISC"], A, cfg=cfg)
        want = ["FX LIST 4 e=1 []"] if req == 14 else ["FX SELECT list=4"]
        row("A QUIET object does not abort on that reply: %s returns%s, LastError is 1 (ON ERROR) and LastText is the server's text 'boom', and the driver reaches its end"
            % (nm, " with e=1 and no list" if req == 14 else ""), sane(r) and all(x in r.fx for x in want) and "FX LERR 1 text=[boom]" in r.fx and not any(abort_text in ln for ln in r.out), why(r))
        r = go(keys(alice, A) + ["QUIET|1"] + open_ops + ops_after + ["LERR", "DISC"], A, cfg={"fail": {req: (netfake.SV_ON_ERROR, "")}})
        row("...and an ON ERROR reply with NO text leaves LastText empty (LastError is still 1)", sane(r) and "FX LERR 1 text=[]" in r.fx, why(r))


# ---- N. what the class puts on the wire ------------------------------------------------------------------------------------------------------

def wire_section():
    say("\n--- every method of the class that sends a file request, and the BYTES it sends (the numbers and the layout written here from the apisrvr table) ---")
    A = S["A"]
    alice = S["alice"][id(A)]
    S1, S0 = struct.pack("<h", 1), struct.pack("<h", 0)
    ops = (keys(alice, A) + ["OPEN|customers|1", "READ|1|c1", "READL|1|c1|0", "READU|1|c2|0", "RLOCKED|1|c2", "RELEASE|1|c2", "SELECT|1|0", "NEXT|0", "LIST|0", "CLEARSEL|0",
                             "MARKS|1|0", "REV", "READL|1|c3|1", "READU|1|c3|1", "RELEASE|#0|", "CLOSE|1", "DISC"])
    r = go(ops, A)
    want = [(3, b"acct"), (4, b"customers"), (6, S1 + b"c1"), (7, S1 + b"c1"), (9, S1 + b"c2"), (34, S1 + b"c2"), (15, S1 + b"c2"), (11, S1 + S0), (12, S0), (14, S0),
            (13, S0), (46, S1 + S0), (49, b""), (8, S1 + b"c3"), (10, S1 + b"c3"), (15, S0), (5, S1), (1, b"")]
    conn = r.d["packets"][0][0] if r.d["packets"] else None
    got = [(t, data) for c, t, data in r.d["packets"] if c == conn and t not in (47, 48)]
    row("%d requests after the login, each with the type and the bytes the wire spec gives: ACCOUNT acct, OPEN customers, READ / READL / READU = file number as a signed 16 bit integer then "
        "the id, RECORDLOCKED, RELEASE, SELECT (file, list), READNEXT (list), READLIST (list), CLEARSELECT (list), MARKMAPPING (file, state), REVISION (nothing), the waiting READL (8) and "
        "READU (10), RELEASE of everything (file number 0, no id), CLOSE, QUIT" % len(want),
        sane(r) and got == want, "first difference: %r" % (next(((a, b) for a, b in zip(got, want) if a != b), (len(got), len(want))),))
    rev = [ln for ln in r.fx if ln.startswith("FX REV ")]
    row("REVISION answers the client's revision then the server's, as two values: <client><V>%s" % REVISION, len(rev) == 1 and re.fullmatch(r"FX REV \[[^<\]]+<V>%s\]" % re.escape(REVISION), rev[0]) is not None, repr(rev))
    row("the waiting reads (8 and 10) of free records answered at once and the fake holds nothing for this connection afterwards",
        rl("READL", "c3", 0, RECS["c3"]) in r.fx and rl("READU", "c3", 0, RECS["c3"]) in r.fx and r.ses and A.store.locks_of(r.ses[0].userno) == [], repr(r.fx[-7:]))


# ---- H. the handler gpl.bp/netfile (S.65 slice 3b) -----------------------------------------------------------------------------------------------
#
# HOW IT WORKS.  zznfh is a BASIC program catalogued GLOBALLY in the sandbox's gpl.bp with $internal and $catalog $zznfh (an internal program;
# an object in an account directory is no longer trusted as internal for a non-administrator).  It reads one operation for each input line,
# "NAME|a|b|c", calls $netfile(op, a, b, c, out, rc) and prints   NH <n> <name> rc=<rc<1>> m=<rc<2>> st=<rc<6>> len=<length of out> out=[<out, the
# marks shown>]   and, for each of rc<3> to rc<5> that is not null,   NA <n> <k> [<text>]   - so a row reads what the PROGRAM got.  A name
# that begins with X is made through a second program (zznfhx, $internal and $catalog $zznfhx) that only calls $netfile: the connection must
# survive a call from another program.  EXEC runs the TCL command in a; RAW gives the operation number in a.  The program is run by an ORDINARY
# session in a fixture account (zznhon: the NET gate on; zznhoff: off; zznhunl: on but not listed), as the administrator for the exemption rows.
#
# THE CREDENTIAL AND THE DEFINITIONS.  A COPY of $netcred is patched in the SANDBOX only (its root -> a scratch directory, as sandbox-net.py does) and
# the stored logins are put on the disk by hand as the user running the suite: v1|alice|salt|iterations|ClientKey|ServerKey|pin|date, the keys
# computed in this file with hashlib (user_bundle) and the pin the one the fake's certificate has.  The definitions are lines in <sandbox>/sys/netservers.
# Every expected value (the records, the request types and bytes, the counts) comes from this file and from the fake's own records, never from SD.
#
# WHAT IT CANNOT SHOW.  (1) The administrator of an INSTALL is the user sdsys, for whom $netcred refuses a login (11458); in the sandbox the
# administrator IS the sandbox user, so the exemption rows show the administrator being let through.  (2) 11496 (11458 / 11459 given with the server's
# name) cannot be reached here: the user is not sdsys and the definition's pin is checked first.  (3) That the kernel calls the handler (slice 3c).
# (4) A reply the class turns into an ABORT: the handler cannot catch it (section gaps).
#
# THE SECTION gaps IS OPT-IN (--sections=gaps).  It holds the rows that state what the plan asks of the handler where the handler as built does
# less - FILEINFO of a key it does not answer, an OPEN the server answers with an ON ERROR, a READ the server answers with an ON ERROR.  It is
# not in the default run because it is RED BY DESIGN until those are built; a default run stays a statement of what is built.

HACCT = {"zznhon": "yes", "zznhoff": "no", "zznhunl": "yes"}      # fixture account -> register field 15 (the NET gate)
HFILE, HEMPTY = "hcust", "hempty"                                  # the files the handler rows open on the fakes (own files: the class rows use "customers")
HNSV = 11                                                          # definitions nfs01 .. nfs11 for the limit rows
# slice 3e: the files the WRITE rows work on (own files again: a write must not change what a read row expects).  wreset() puts them back.
HW, HWBP, HWVOC, HWNC = "hwork", "bp", "voc", "hnocase"
HWREC = {"w1": "alpha" + FMC + "1", "w2": "beta" + FMC + "2", "w3": "gamma"}
HWFILES = ((HW, HWREC, "/data/hwork", False), (HWBP, {"prog1": "x"}, "/data/bp", False), (HWVOC, {"verb1": "V"}, "/data/voc", False), (HWNC, {"Mixed": "m"}, "/data/hnocase", True))
HNED = "zznhned"                                                   # slice 3e: the NET gate on and NO edit gate (voc.edit, bp.edit, dict.edit all off once the programs are compiled)
OPT_IN = ("gaps",)
H = {}                                                             # what the handler sections made
NH_RX = re.compile(r"^NH (\d+) (\S+) rc=(\S*) m=(\S*) st=(\S*) len=(\d+) out=\[(.*)\]$")
NA_RX = re.compile(r"^NA (\d+) (\d) \[(.*)\]$")
NM_RX = re.compile(r"^NM (\d+) \[(.*)\]$")                                 # slice 3e: rc<7>, the mode the handler reports for an open
NS_RX = re.compile(r"^NS (\d+) \[(.*)\]$")                                 # S.72: rc<8>, the server's reply STATUS() for RECORDLOCKED (the lock owner) and FILEUNLOCK (0, 3011, 3012)

NFH_DRIVER = r"""$internal
program zznfh
$catalog $zznfh
$include err.h
$include netfile.h
   done = @false
   n.call = 0
   v = ''
   sv = ''
   k = 0
   crt 'NH begin'
   loop
      input ln
      done = (ln = 'END') or (ln = '' and status() = ER$EOF)
   until done do
      nm = field(ln, '|', 1)
      a = field(ln, '|', 2)
      b = field(ln, '|', 3)
      c = field(ln, '|', 4)
*     slice 3e: a record or an id with marks in it is typed with the place holders <I> <F> <V> <S>; a terminal line cannot be trusted with the marks themselves
      b = change(b, '<I>', @im) ; b = change(b, '<F>', @fm) ; b = change(b, '<V>', @vm) ; b = change(b, '<S>', @sm)
      c = change(c, '<I>', @im) ; c = change(c, '<F>', @fm) ; c = change(c, '<V>', @vm) ; c = change(c, '<S>', @sm)
      via = @false
      if nm[1,1] = 'X' then
         via = @true
         nm = nm[2, 99]
      end
      intxn = @false
      if nm[1,1] = 'T' then
         intxn = @true
         nm = nm[2, 99]
      end
      op = -1
      begin case
         case nm = 'OPEN'
            op = NF$OPEN
         case nm = 'CLOSE'
            op = NF$CLOSE
         case nm = 'READ'
            op = NF$READ
         case nm = 'READV'
            op = NF$READV
         case nm = 'RLOCKED'
            op = NF$RECORDLOCKED
         case nm = 'SELECT'
            op = NF$SELECT
         case nm = 'FILEINFO'
            op = NF$FILEINFO
         case nm = 'CLOSEALL'
            op = NF$CLOSEALL
         case nm = 'WRITE'
            op = NF$WRITE
         case nm = 'DELETE'
            op = NF$DELETE
         case nm = 'CLEARFILE'
            op = NF$CLEARFILE
         case nm = 'LOCK'
            op = NF$LOCK
         case nm = 'WRITEU'
            op = NF$WRITEU
         case nm = 'DELETEU'
            op = NF$DELETEU
         case nm = 'RELEASE'
            op = NF$RELEASE
         case nm = 'STATE'
            op = NF$STATE
         case nm = 'EXEC'
            op = -2
         case nm = 'RAW'
            op = a + 0
            a = b
            b = c
            c = field(ln, '|', 5)
      end case
      n.call += 1
      out = ''
      rc = ''
      begin case
         case op = -1
            crt 'NH ':n.call:' ':nm:' rc=UNKNOWN m= st= len=0 out=[]'
         case op = -2
            execute a
            crt 'NH ':n.call:' ':nm:' rc= m= st= len=0 out=[]'
         case intxn = @true
*           slice 3e: the call is made INSIDE a transaction (system(SYS$TRANS_LEVEL) is not 0 in the handler)
            begin transaction
               call $netfile(op, a, b, c, out, rc)
               commit
            end transaction
            gosub show.call
         case via = @true
            call $zznfhx(op, a, b, c, out, rc)
            gosub show.call
         case 1
            call $netfile(op, a, b, c, out, rc)
            gosub show.call
      end case
   repeat
   crt 'NH end'
   stop

show.call: * the line for the call just made, and one for each argument of the message
   v = out
   gosub shw
   crt 'NH ':n.call:' ':nm:' rc=':rc<1>:' m=':rc<2>:' st=':rc<6>:' len=':len(out):' out=[':sv:']'
   for k = 3 to 5
      if rc<k> # '' then crt 'NA ':n.call:' ':(k - 2):' [':rc<k>:']'
   next k
   if rc<7> # '' then crt 'NM ':n.call:' [':rc<7>:']'
   if rc<8> # '' then crt 'NS ':n.call:' [':rc<8>:']'
   return

shw: * SV = V with the four marks made visible, cut to its first and last 40 characters when over 100
   sv = v
   sv = change(sv, @im, '<I>')
   sv = change(sv, @fm, '<F>')
   sv = change(sv, @vm, '<V>')
   sv = change(sv, @sm, '<S>')
   if len(sv) > 100 then sv = sv[1,40] : '..' : sv[len(sv) - 39, 40]
   return

end
"""

NFH_SUB = r"""$internal
subroutine zznfhx(op, a, b, c, out, rc)
$catalog $zznfhx
   call $netfile(op, a, b, c, out, rc)
   return
end
"""


def FNO(n):
    return struct.pack("<h", n)


def wreset(srv):
    """Slice 3e: the files the write rows work on, as they were at the start (a record changed, deleted or cleared is back), and no lock held by anybody.  Only between
    sessions: a session that has a file open holds the OLD file object."""
    for name, recs, path, nocase in HWFILES:
        srv.store.add_file(name, dict(recs), dict_items=dict(DICT_ITEMS), path=path, nocase=nocase)
    with srv.store.cond:
        srv.store.locks.clear()
        srv.store.filelocks.clear()


class Script:
    """The input lines of one handler session, each with what it must answer (OK: a test of the parsed call), the requests it must put on the wire
    (REQ: (type, data) after the login; a select list number is not compared, only that select and readlist agree and are 0 to 10) and the audit line
    it must leave (AUDIT)."""

    def __init__(self):
        self.items = []

    def add(self, name, a="", b="", c="", label=None, ok=None, req=(), audit=None):
        self.items.append({"line": "|".join([name, str(a), str(b), str(c)]), "label": label, "ok": ok, "req": list(req), "audit": audit})
        return len(self.items) - 1

    @property
    def lines(self):
        return [it["line"] for it in self.items]

    def wire(self):
        return [r for it in self.items for r in it["req"]]

    def audits(self):
        return [it["audit"] for it in self.items if it["audit"]]

    def nreq(self):
        """File requests expected so far (the account request and the quit are not counted by the handler)."""
        return sum(1 for it in self.items for t, _d in it["req"] if t not in (3, 1))


def k_ok(out=None, ln=None):
    """The call succeeded: rc 0, no message, no status, no arguments; out and its length as given."""
    def f(c):
        return (c["rc"] == "0" and c["m"] == "" and c["st"] == "" and c["args"] == ["", "", ""]
                and (out is None or c["out"] == out) and (ln is None or c["len"] == ln))
    return f


def k_rec(text):
    return k_ok(show(text), len(text))


def k_ids(ids):
    joined = FMC.join(ids)
    def f(c):
        return k_ok()(c) and c["len"] == len(joined) and sorted(c["out"].split("<F>")) == sorted(ids)
    return f


def k_err(n, *args):
    """rc 3 with message n and these arguments (the rest null), and nothing in out."""
    want = [str(x) for x in args] + [""] * (3 - len(args))
    def f(c):
        return c["rc"] == "3" and c["m"] == str(n) and c["args"] == want and c["len"] == 0
    return f


def k_else(st):
    """rc 2 (the ELSE branch), no message, the remote STATUS() in rc<6>."""
    def f(c):
        return c["rc"] == "2" and c["m"] == "" and c["st"] == str(st) and c["args"] == ["", "", ""] and c["len"] == 0
    return f


def k_state(servers, files, opens, requests, dropped, lost, conns=()):
    """NF$STATE: out<1> servers connected, <2> files open, <3> files opened in all, <4> requests sent, <5> connections dropped, <6> files lost,
    then one attribute for each connected server: name, the VARTYPE of its object (15 is an object), files open.  The whole answer is compared
    with the text built here and shown the way the program shows it (cut to 40 and 40 characters when over 100), so every number is held."""
    text = FMC.join([str(x) for x in (servers, files, opens, requests, dropped, lost)] + [VMC.join(str(y) for y in x) for x in conns])

    def f(c):
        return c["rc"] == "0" and c["m"] == "" and c["st"] == "" and c["len"] == len(text) and c["out"] == show(text)
    return f


def audit_size():
    """Size of the sandbox's audit file (SD appends to <sys>/audit and never creates it, so it is made empty when it is missing)."""
    path = os.path.join(g.SYS, "audit")
    try:
        if not os.path.exists(path):
            with open(path, "ab"):
                pass
        return os.path.getsize(path)
    except OSError:
        return None


def audit_since(off):
    try:
        with open(os.path.join(g.SYS, "audit"), "rb") as f:
            f.seek(off or 0)
            return f.read().decode("utf-8", errors="replace")
    except OSError:
        return None


def h_audits(text):
    """The handler's audit lines in a stretch of the trail, as   open server=nfa file=hcust   /   refused server=nfa reason=gate.  Since slice 3e also
    open server=nfw file=hwork mode=write,  write / delete / clear server=nfw file=hwork  and  lost server=nfw op=write  (the key word is the one the line has)."""
    out = []
    for m in re.finditer(r"netfile (open|refused|write|delete|clear|lost|filelock) server=(\S+) (file|reason|op)=([^\r\n]*?)\s*$", text or "", re.M):
        out.append("%s server=%s %s=%s" % (m.group(1), m.group(2), m.group(3), m.group(4)))
    return out


def h_calls(lines):
    calls, by = [], {}
    for ln in lines:
        m = NH_RX.match(ln)
        if m:
            c = {"n": int(m.group(1)), "nm": m.group(2), "rc": m.group(3), "m": m.group(4), "st": m.group(5), "len": int(m.group(6)), "out": m.group(7), "args": ["", "", ""], "r7": "", "r8": ""}
            calls.append(c)
            by[c["n"]] = c
            continue
        m = NA_RX.match(ln)
        if m and int(m.group(1)) in by:
            by[int(m.group(1))]["args"][int(m.group(2)) - 1] = m.group(3)
            continue
        m = NM_RX.match(ln)
        if m and int(m.group(1)) in by:
            by[int(m.group(1))]["r7"] = m.group(2)           # slice 3e: rc<7>, printed only when it is not null
            continue
        m = NS_RX.match(ln)
        if m and int(m.group(1)) in by:
            by[int(m.group(1))]["r8"] = m.group(2)           # S.72: rc<8>, printed only when it is not null
    return calls


def h_wire(d):
    """The requests after the login in a delta of the fake, in arrival order; a select list number is cut out (see Script)."""
    out = []
    for _c, t, data in d["packets"]:
        if t in (47, 48):
            continue
        if t == 11:
            out.append((11, data[:2]))
        elif t == 14:
            out.append((14, b""))
        else:
            out.append((t, data))
    return out


def h_lists_ok(d):
    sel = [struct.unpack("<h", data[2:4])[0] for _c, t, data in d["packets"] if t == 11 and len(data) == 4]
    rdl = [struct.unpack("<h", data[:2])[0] for _c, t, data in d["packets"] if t == 14 and len(data) == 2]
    return sel == rdl and all(0 <= n <= 10 for n in sel)


def quit_seen(d):
    """Every connection the fake served in this delta ended with a Quit (request 1): the handler ended it, the process did not just vanish."""
    return bool(d["sessions"]) and all(s.requests and s.requests[-1] == 1 for s in d["sessions"])


def h_go(acct, script, fakes=(), cfg=None, admin=False):
    """Run zznfh with the script's lines in an ordinary session of ACCT (or as the administrator).  The FAKES are configured with files=True and
    files_only=True (the SDNet login), write_group=True (18 Oct 26: the login is also in sdfileswrite, as a target's administrator gives it; the section wgroup says what
    happens without) and CFG; r.d is a list of what each saw, r.calls what the program got, r.audits what the audit trail gained."""
    c = {"files": True, "files_only": True, "write_group": True}
    c.update(cfg or {})
    for f in fakes:
        f.configure(**c)
    marks = [f.mark() for f in fakes]
    a0 = audit_size()
    t0 = time.time()
    lines = script.lines + ["END"]
    hung = False
    try:
        out = bounded_sd(g.SYS, ["RUN gpl.bp zznfh"] + lines, admin=True, internal=True) if admin else bounded_plain(acct, ["ZZNFH"] + lines)
    except subprocess.TimeoutExpired:
        # S.72b: a session that never came back (the class aborted inside the handler, which nothing can catch) is a failed row with the reason shown, not the end of the run
        out, hung = [], True
    el = time.time() - t0
    idle = True
    for f in fakes:
        f.settle(quiet=0.3)
        idle = quiet(f) and idle
    r = Run()
    r.d = [f.delta(m) for f, m in zip(fakes, marks)]
    for f in fakes:
        f.configure()
    r.out, r.el, r.idle, r.hung = out, el, idle, hung
    r.began = "NH begin" in out
    r.ended = "NH end" in out
    r.calls = h_calls(out)
    r.audit = audit_since(a0)
    r.audits = h_audits(r.audit)
    r.n = len(script.items)
    return r


def h_sane(r, need_end=True):
    """The program began and ended with one answer for each line, the fakes found nothing malformed, refused no request, and no connection is left."""
    return (r.began and (r.ended or not need_end) and (len(r.calls) == r.n or not need_end) and r.idle
            and all(not d["errors"] for d in r.d) and all(not s.refused for d in r.d for s in d["sessions"]))


def h_why(r, n=6):
    return "began=%s ended=%s calls=%d of %d idle=%s hung=%s fake errors=%r\n      tail: %r" % (r.began, r.ended, len(r.calls), r.n, r.idle, getattr(r, "hung", False), [d["errors"] for d in r.d], r.out[-n:])


def judge(r, script):
    """One row for each item of the script that has a label; the items that have an expectation and no label are one row together."""
    rest, bad = 0, []
    for i, it in enumerate(script.items):
        if it["ok"] is None:
            continue
        c = r.calls[i] if i < len(r.calls) else None
        good = c is not None and it["ok"](c)
        if it["label"] is None:
            rest += 1
            if not good:
                bad.append("call %d %r -> %r" % (i, it["line"], c))
        else:
            row(it["label"], good, "call %d %r -> %r" % (i, it["line"], c))
    if rest:
        row("...and the other %d calls of the program answered as expected" % rest, not bad, "; ".join(bad[:4]))


def secret_free(text):
    """Nothing the credential or the login holds is in this text: no key, salt, pin, hash or password."""
    bad = [v for u in (S["alice"][id(S["A"])], S["alice"][id(S["B"])]) for v in (u["ck_b64"], u["sk_b64"], u["salt"], u["pw"])]
    bad += list(S["pins"])
    return text is not None and all(v not in text for v in bad)


def h_cred_line(u, pin):
    return "|".join(["v1", u["user"], u["salt"], str(u["it"]), u["ck_b64"], u["sk_b64"], pin, datetime.date.today().isoformat()])


def h_fix_text():
    names = "'" + "':@fm:'".join(HACCT) + "'"
    return "\n".join([
        "$internal",
        "   for each a in %s" % names,
        "      openpath '%s':@ds:a:@ds:'voc' to v else crt 'HFIX no voc ':a ; stop" % os.path.join(g.BOX, "user_accounts"),
        "      write 'V':@fm:'CA':@fm:'$zznfh' to v, 'zznfh'",
        "      close v",
        "   next a",
        "   crt 'HFIX done'",
        "end", ""])


def h_prep():
    """What every handler section needs, done once: a scratch credential root and the sandbox's $netcred pointed at it, the stored logins, the
    definitions, the files on the fakes, the driver and the three fixture accounts.  Returns True when ready (a failed step is a failed row)."""
    if "ready" in H:
        return H["ready"]
    H["ready"] = False
    user = pwd.getpwuid(os.getuid()).pw_name
    if user in ("root", "sdsys") or not re.fullmatch(r"[A-Za-z0-9._-]{1,32}", user) or user[0] in ".-":
        row("SETUP: the user running this suite (%r) is one $netcred can keep a login for (not root, not sdsys, letters digits ._-)" % user, False, "run it as an ordinary user")
        return False
    A, B = S["A"], S["B"]
    pa, pb = S["pin"][id(A)], S["pin"][id(B)]
    alA, alB = S["alice"][id(A)], S["alice"][id(B)]
    work = tempfile.mkdtemp(prefix="sdnet-nfh-")
    root = os.path.join(work, "sd-net")
    H.update(work=work, made=work, user=user, root=root, dir=os.path.join(root, user))
    os.makedirs(H["dir"])
    os.chmod(root, 0o755)
    os.chmod(H["dir"], 0o700)

    # the sandbox's own copy of $netcred keeps its logins in the scratch root (the shipped one is /var/lib/sd-net, made by root)
    p = os.path.join(g.SYS, "gpl.bp", "netcred")
    with open(p, encoding="utf-8", errors="replace") as f:
        text = f.read()
    new, n = re.subn(r"(\$define NETCRED\.ROOT\s+')[^']*(')", lambda m: m.group(1) + root + m.group(2), text, flags=re.M)
    if n != 1:
        row("SETUP: the sandbox's netcred holds exactly one NETCRED.ROOT define to point at the scratch root", False, "%d matches" % n)
        return False
    with open(p, "w", encoding="utf-8") as f:
        f.write(new)

    # the files on the fakes (own files, so the class rows' "customers" is untouched) - A and B differ in one record each
    for srv, extra in ((A, ("only_a", "from A")), (B, ("only_b", "from B"))):
        recs = dict(RECS)
        recs[extra[0]] = extra[1]
        srv.store.add_file(HFILE, recs, dict_items=dict(DICT_ITEMS), path="/data/hcust")
        srv.store.add_file(HEMPTY)
        wreset(srv)                                            # slice 3e: the files the write rows work on

    # the definitions (name|host|port|account|pin|mode|accounts|date) and the stored logins
    today = datetime.date.today().isoformat()
    L = []
    cred = {}

    def define(name, port, pin, accounts, who, credpin=None, account="acct", host="127.0.0.1", mode="read"):
        L.append("|".join([name, host, str(port), account, pin, mode, accounts, today]))
        if who is not None:
            cred[name] = h_cred_line(who, credpin or pin)
    define("nfa", A.port, pa, "zznhon,zznhoff", alA)
    define("nfb", B.port, pb, "zznhon", alB)
    # slice 3e: the same two fakes as WRITE-mode servers (the mode is the deliberate act of SDSYS: set.server ... write); nfa and nfb stay read, the control
    define("nfw", A.port, pa, "zznhon,zznhoff," + HNED + ",zznhnov", alA, mode="write")
    define("nfwb", B.port, pb, "zznhon," + HNED, alB, mode="write")
    define("nfcase", A.port, pa, "ZZNHON", alA)                      # the list is upper case: the test is case blind
    define("nfnocred", A.port, pa, "zznhon,zznhoff", None)             # defined and listed, no stored login
    define("nfcpin", A.port, pa, "zznhon", alA, credpin=pb)            # the stored login was made for ANOTHER key than the definition has now
    define("nfpin", B.port, pa, "zznhon", alB)                         # B presents key two, the definition holds A's hash (and the login agrees with the definition)
    define("nfdead", S["dead"], pa, "zznhon", alA)                     # nothing listens
    define("nfadm", A.port, pa, "someoneelse", alA)                    # listed for nobody who is signed in
    define("nfbhost", A.port, pa, "zznhon", None, host="bad host")
    define("nfbport", 70000, pa, "zznhon", None)
    define("nfbacct", A.port, pa, "zznhon", None, account="a b")
    define("nfbkey", A.port, pa[:63], "zznhon", None)
    for k in range(1, HNSV + 1):
        define("nfs%02d" % k, A.port, pa, "zznhon", alA)
    sdefs = os.path.join(g.SYS, "netservers")
    try:
        with open(sdefs, "rb") as f:
            H["defs_prior"] = f.read()
    except OSError:
        H["defs_prior"] = None
    H["defs_text"] = "\n".join(L) + "\n"                      # slice 3e: what the write rows put back after they changed a mode
    with open(sdefs, "w", encoding="ascii") as f:
        f.write(H["defs_text"])
    os.chmod(sdefs, 0o644)
    for name, line in cred.items():
        cp = os.path.join(H["dir"], name)
        with open(cp, "w", encoding="ascii") as f:
            f.write(line + "\n")
        os.chmod(cp, 0o600)
    row("SETUP: %d definitions are in %s (mode 644) and %d stored logins are in the scratch root, each 600 under a 700 directory owned by the suite's user"
        % (len(L), sdefs, len(cred)), os.path.getsize(sdefs) > 0 and all(os.stat(os.path.join(H["dir"], n)).st_mode & 0o777 == 0o600 for n in cred)
        and os.stat(H["dir"]).st_mode & 0o777 == 0o700, "")

    # the programs: the driver and its second-program stand-in, with the handler and the patched $netcred
    g.put(os.path.join(g.SYS, "gpl.bp", "zznfh"), NFH_DRIVER)
    g.put(os.path.join(g.SYS, "gpl.bp", "zznfhx"), NFH_SUB)
    out = g.adm(["BASIC gpl.bp netcred netfile zznfh zznfhx"], internal=True)
    ok = g.has(out, r"^Compiled 4 program\(s\) with no errors") and not any(re.search(r"warning|not assigned", ln, re.I) for ln in out)
    row("SETUP: the sandbox's $netcred (root -> %s), the handler $netfile and the test programs zznfh and zznfhx compile with no errors and no warning" % root, ok, repr(out[-12:]))
    if not ok:
        return False

    # the fixture accounts: ordinary, with the program as a VOC verb
    for name, net in HACCT.items():
        g.EXTRA_FIXTURES[name] = ("no", "no")
        path = g.build_account(name)
        g.reg_write(name, [path, "", g.GROUP, "", "", "", "no", "no", "", "yes", "yes", "yes", "", "", net])
    g.put(os.path.join(g.SYS, "bp", "zznhfix"), h_fix_text())
    out = g.adm(["BASIC bp zznhfix", "RUN bp zznhfix"], internal=True)
    if not g.has(out, r"^HFIX done$"):
        row("SETUP: the fixture accounts hold the verb ZZNFH", False, repr(out[-6:]))
        return False
    gates = {n: (g.reg_read(n) + [""] * 16)[14] for n in HACCT}
    f = g.flags(g.plain("zznhon", ["ZZKF"]))
    row("CONTROL: a plain session in zznhon is not an administrator (admin=0) and the registers hold the NET gate as intended (%s)" % ", ".join("%s %s" % kv for kv in gates.items()),
        f is not None and f[0] == "0" and gates == HACCT, repr((f, gates)))
    if f is None or f[0] != "0":
        return False
    H["ready"] = True
    return True


def h_cleanup():
    sdefs = os.path.join(g.SYS, "netservers") if g.SYS else None
    if "defs_prior" in H and sdefs:
        try:
            if H["defs_prior"] is None:
                os.remove(sdefs)
            else:
                with open(sdefs, "wb") as f:
                    f.write(H["defs_prior"])
        except OSError:
            pass
    w = H.get("made")
    if w and os.path.isdir(w) and os.path.basename(w).startswith("sdnet-nfh-"):
        shutil.rmtree(w, ignore_errors=True)


def a_wire(r, script, i=0):
    return h_wire(r.d[i]) == script.wire() and h_lists_ok(r.d[i])


# ---- H1. the operations ---------------------------------------------------------------------------------------------------------------------

def handler_section():
    say("\n--- $netfile: open, read, readv, record locked, select, fileinfo and close through the handler - one connection, the records of the fake ---")
    if not h_prep():
        return
    A = S["A"]
    ids = list(A.store.records(HFILE))
    c1 = RECS["c1"]
    fields = c1.split(FMC)
    s = Script()
    s.add("OPEN", "nfa", HFILE, label="OPEN nfa hcust (a stored login, the right pin, the NET gate on, listed): handle 1, rc 0 and no message", ok=k_ok("1", 1),
          req=[(3, b"acct"), (4, b"hcust")], audit="open server=nfa file=hcust")
    s.add("READ", 1, "c1", label="READ c1 returns exactly the record the fake holds (the marks shown)", ok=k_rec(c1), req=[(6, FNO(1) + b"c1")])
    s.add("XREAD", 1, "c2", label="...READ c2 made from ANOTHER PROGRAM (zznfhx) on the handle the first made: the same connection answers", ok=k_rec(RECS["c2"]), req=[(6, FNO(1) + b"c2")])
    s.add("READ", 1, "m1", label="READ m1 (a record with a subvalue and an item mark) equals the store", ok=k_rec(RECS["m1"]), req=[(6, FNO(1) + b"m1")])
    s.add("READ", 1, "big", label="READ big (70,000 bytes, more than one read of the socket) equals the store: the length and its first and last 40 characters", ok=k_rec(RECS["big"]),
          req=[(6, FNO(1) + b"big")])
    s.add("READ", 1, "nosuch", label="READ of an id the file does not hold is the ELSE branch (rc 2) with the remote STATUS() 3006 in rc<6> and no message", ok=k_else(3006),
          req=[(6, FNO(1) + b"nosuch")])
    s.add("READ", 1, "", label="READ of the empty id is the ELSE branch with STATUS() 3000 and NOTHING is sent", ok=k_else(3000))
    s.add("READV", 1, "c1", 2, label="READV field 2 of c1 is that field alone: '100<V>200' (the whole record is read and cut here: the class has no readv)", ok=k_rec(fields[1]), req=[(6, FNO(1) + b"c1")])
    s.add("READV", 1, "c1", 1, label="READV field 1 is 'Smith'", ok=k_rec(fields[0]), req=[(6, FNO(1) + b"c1")])
    s.add("READV", 1, "c1", 9, label="READV of a field beyond the record is null with rc 0", ok=k_ok("", 0), req=[(6, FNO(1) + b"c1")])
    s.add("READV", 1, "c1", 0, label="READV field 0 is null with rc 0", ok=k_ok("", 0), req=[(6, FNO(1) + b"c1")])
    s.add("READV", 1, "nosuch", 1, label="READV of an id the file does not hold is the ELSE branch with STATUS() 3006", ok=k_else(3006), req=[(6, FNO(1) + b"nosuch")])
    s.add("RLOCKED", 1, "c1", label="[S72b-N0] RECORDLOCKED through a READ-mode handle (nfa) is refused (S.72b; it used to answer 0): rc 3, message 11501 naming the server (nfa) and 'recordlocked', nothing in out - "
          "and NOTHING IS SENT", ok=k_err(11501, "nfa", "recordlocked"))
    s.add("SELECT", 1, label="SELECT returns every id of the file, field marks between: %d ids equal to the fake's store" % len(ids), ok=k_ids(ids), req=[(11, FNO(1)), (14, b"")])
    s.add("FILEINFO", 1, 0, label="FILEINFO key 0 (FL$OPEN) is 1", ok=k_ok("1", 1))
    s.add("FILEINFO", 1, 1, label="FILEINFO key 1 (FL$VOC.NAME) is null: the name on the other machine is not shown", ok=k_ok("", 0))
    s.add("FILEINFO", 1, 2, label="FILEINFO key 2 (FL$PATH) is null: a path on another machine is not shown (the fake would say /data/hcust)", ok=k_ok("", 0))
    s.add("OPEN", "NFA", "DICT HCUST", label="OPEN of the dictionary in capitals ('NFA' 'DICT HCUST'): handle 2, and the name goes on the wire in lower case", ok=k_ok("2", 1),
          req=[(4, b"dict hcust")], audit="open server=nfa file=dict hcust")
    s.add("READ", 2, "name", label="READ of the dictionary item through handle 2 equals the item in the store", ok=k_rec(DICT_ITEMS["name"]), req=[(6, FNO(2) + b"name")])
    s.add("OPEN", "nfa", HEMPTY, label="a second file on the same server (hempty): handle 3, NO new connection", ok=k_ok("3", 1), req=[(4, b"hempty")], audit="open server=nfa file=hempty")
    s.add("SELECT", 3, label="SELECT of the empty file is null with rc 0", ok=k_ok("", 0), req=[(11, FNO(3)), (14, b"")])
    s.add("READ", 3, "x", label="READ in the empty file is the ELSE branch with STATUS() 3006", ok=k_else(3006), req=[(6, FNO(3) + b"x")])
    n_before = s.nreq()
    s.add("STATE", label="THE OBJECT-IN-COMMON QUESTION: after a dozen statements and calls from two programs the named common block /$netfile/ still holds the connection as an OBJECT "
          "(VARTYPE 15, the 2nd value) for server nfa with 3 files open; 1 server, 3 files, 3 opened in all, the handler's own request count equal to what the fake received (%d), "
          "none dropped, none lost" % n_before,
          ok=k_state(1, 3, 3, n_before, 0, 0, conns=[("nfa", 15, 3)]))
    s.add("CLOSE", 1, label="CLOSE handle 1: rc 0", ok=k_ok("", 0), req=[(5, FNO(1))])
    s.add("READ", 1, "c1", label="READ on the closed handle is an error: 11494 'No remote file is open with handle 1 for this account', nothing sent", ok=k_err(11494, 1))
    s.add("CLOSE", 1, label="CLOSE of the closed handle again is the same error (11494), nothing sent", ok=k_err(11494, 1))
    s.add("CLOSE", 2, ok=k_ok("", 0), req=[(5, FNO(2))])
    s.add("CLOSE", 3, ok=k_ok("", 0), req=[(5, FNO(3))])
    n_after = s.nreq()
    s.add("STATE", label="closing every file leaves the connection held for reuse: 1 server, 0 files, %d requests" % n_after, ok=k_state(1, 0, 3, n_after, 0, 0, conns=[("nfa", 15, 0)]))
    s.add("CLOSEALL", label="CLOSEALL: rc 0, and the connection is ended with a Quit", ok=k_ok("", 0), req=[(1, b"")])
    r = h_go("zznhon", s, (A,))
    row("the program ran every line (one answer each) and no connection is left", h_sane(r), h_why(r))
    judge(r, s)
    d = r.d[0]
    row("...THE CONNECTION IS REUSED: the fake saw ONE connection and ONE handshake for 3 OPENs, the reads, the select, the closes, a call from another program and the CLOSEALL; the "
        "session is alice's in the account 'acct', files-only, and ended with a Quit", d["conns"] == 1 and d["handshakes"] == 1 and len(r.d[0]["sessions"]) == 1 and r.d[0]["sessions"][0].user == "alice"
        and r.d[0]["sessions"][0].account == "acct" and r.d[0]["sessions"][0].files_only and quit_seen(d) and d["ok"] == 1 and d["bad"] == 0, repr({k: d[k] for k in ("conns", "handshakes", "ok", "bad")}))
    row("...THE REQUESTS, in order, with their bytes: ACCOUNT acct, OPEN hcust, the READs and the five READVs (a READV is a whole READ on the wire), SELECT then READLIST on one list number "
        "(0 to 10), FILEINFO sent nothing, OPEN 'dict hcust' in lower case, CLOSE with the file number, QUIT - and nothing for the empty id or the closed handle, and (S.72b) NO request 34 for the "
        "RECORDLOCKED of the read-mode handle",
        a_wire(r, s) and 34 not in d["types"], "first difference: %r types %r" % (next(((a, b) for a, b in zip(h_wire(d), s.wire()) if a != b), (len(h_wire(d)), len(s.wire()))), d["types"]))
    row("...the audit trail gained one 'netfile open server=<name> file=<file>' line for each OPEN, in order (%s), and nothing in it is a key, a hash, a salt or a password" % ", ".join(s.audits()),
        r.audits == s.audits() and secret_free(r.audit), repr(r.audits))

    # a record lock held by another user is reported with the class's codes; the handler takes none of its own
    A.store.hold(HFILE, "c2", 7, "update")
    A.store.hold(HFILE, "c3", 8, "shared")
    A.store.hold_file(HEMPTY, 9)
    try:
        # S.72b: RECORDLOCKED is for a WRITE-mode handle (nfw): the same two files, opened through the write-mode definition of the same fake.  The read-mode refusals are N0, N3 and N4.
        s = Script()
        s.add("OPEN", "nfw", HFILE, ok=k_open_w(1), req=[(3, b"acct"), (4, b"hcust")], audit="open server=nfw file=hcust mode=write")
        s.add("OPEN", "nfw", HEMPTY, ok=k_open_w(2), req=[(4, b"hempty")], audit="open server=nfw file=hempty mode=write")
        s.add("RLOCKED", 1, "c2", label="RECORDLOCKED (a write-mode handle) of a record another user holds an UPDATE lock on is -2", ok=k_ok("-2", 2), req=[(34, FNO(1) + b"c2")])
        s.add("RLOCKED", 1, "c3", label="...a record another user holds a READ lock on is -1", ok=k_ok("-1", 2), req=[(34, FNO(1) + b"c3")])
        s.add("RLOCKED", 1, "c1", label="...a record nobody holds is 0 (the other holds do not spill over)", ok=k_ok("0", 1), req=[(34, FNO(1) + b"c1")])
        s.add("RLOCKED", 2, "anything", label="...any record of a file another user holds the FILE lock on is -3", ok=k_ok("-3", 2), req=[(34, FNO(2) + b"anything")])
        s.add("CLOSEALL", ok=k_ok("", 0), req=[(1, b"")])
        r = h_go("zznhon", s, (A,))
        row("the lock rows ran to the end and no connection is left", h_sane(r), h_why(r))
        judge(r, s)
        ses = r.d[0]["sessions"][0] if r.d[0]["sessions"] else None
        row("...the handler took NO lock of its own: the fake holds nothing for the session, and the requests were the ones listed", ses is not None and A.store.locks_of(ses.userno) == [] and a_wire(r, s),
            repr(ses and A.store.locks_of(ses.userno)))
    finally:
        for u in (7, 8, 9):
            A.store.drop_user(u)

    # the record routes to the server the handle belongs to
    B = S["B"]
    s = Script()
    s.add("OPEN", "nfa", HFILE, ok=k_ok("1", 1), req=[(3, b"acct"), (4, b"hcust")], audit="open server=nfa file=hcust")
    s.add("OPEN", "nfb", HFILE, ok=k_ok("2", 1), audit="open server=nfb file=hcust")
    s.add("READ", 1, "only_a", label="TWO SERVERS: handle 1 (nfa) reads the record only server A holds", ok=k_rec("from A"))
    s.add("READ", 1, "only_b", label="...handle 1 does not find the record only server B holds (ELSE, 3006)", ok=k_else(3006))
    s.add("READ", 2, "only_b", label="...handle 2 (nfb) reads the record only server B holds", ok=k_rec("from B"))
    s.add("READ", 2, "only_a", label="...handle 2 does not find the record only server A holds", ok=k_else(3006))
    s.add("READ", 1, "c1", ok=k_rec(c1))
    s.add("READ", 2, "c1", ok=k_rec(c1))
    s.add("STATE", label="STATE shows two servers (nfa and nfb), each an object, one file each, 2 opened in all, 8 requests (2 opens and 6 reads)",
          ok=k_state(2, 2, 2, 8, 0, 0, conns=[("nfa", 15, 1), ("nfb", 15, 1)]))
    s.add("CLOSEALL", ok=k_ok("", 0))
    r = h_go("zznhon", s, (A, B))
    row("the two-server program ran to the end and no connection is left", h_sane(r), h_why(r))
    judge(r, s)
    da, db = r.d
    row("...TWO SERVERS ARE TWO CONNECTIONS: each fake saw ONE connection; each got ACCOUNT acct, OPEN hcust, three READs and a Quit, nothing meant for the other",
        da["conns"] == 1 and db["conns"] == 1 and by_conn(da) == [[47, 48, 3, 4, 6, 6, 6, 1]] and by_conn(db) == [[47, 48, 3, 4, 6, 6, 6, 1]] and quit_seen(da) and quit_seen(db),
        repr((by_conn(da), by_conn(db))))
    row("...each server was logged in with ITS stored login (alice on B has another salt than on A) and one proof verified on each, none refused",
        da["ok"] == 1 and db["ok"] == 1 and da["bad"] == 0 and db["bad"] == 0, repr((da["ok"], db["ok"])))

    # a file that is not there: the connection made for the call is ended again, and the next open reconnects through OPEN
    s = Script()
    s.add("OPEN", "nfa", "nosuchfile", label="OPEN of a file the server does not have is the ELSE branch (rc 2) with STATUS() 3003", ok=k_else(3003), req=[(3, b"acct"), (4, b"nosuchfile")], audit="open server=nfa file=nosuchfile")
    s.add("STATE", label="...and the connection that call made for nothing was ended: 0 servers, 0 files, nothing opened", ok=k_state(0, 0, 0, 1, 0, 0))
    s.add("OPEN", "nfa", HFILE, label="the next OPEN dials again and gets handle 1", ok=k_ok("1", 1), audit="open server=nfa file=hcust")
    s.add("READ", 1, "c3", ok=k_rec(RECS["c3"]))
    s.add("CLOSEALL", ok=k_ok("", 0))
    r = h_go("zznhon", s, (A,))
    row("the missing-file program ran to the end and no connection is left", h_sane(r), h_why(r))
    judge(r, s)
    d = r.d[0]
    row("...the fake saw TWO connections: the first ACCOUNT, OPEN, then a Quit from the handler (nothing else); the second ACCOUNT, OPEN, READ, Quit",
        d["conns"] == 2 and by_conn(d) == [[47, 48, 3, 4, 1], [47, 48, 3, 4, 6, 1]] and quit_seen(d) and r.audits == s.audits(), repr(by_conn(d)))

    # the administrator is exempt from the gate and the list
    s = Script()
    s.add("OPEN", "nfadm", HFILE, label="THE ADMINISTRATOR (the sandbox's: the OS user) opens a server whose list names nobody who is signed in: handle 1 - exempt from the gate and the list",
          ok=k_ok("1", 1), req=[(3, b"acct"), (4, b"hcust")], audit="open server=nfadm file=hcust")
    s.add("READ", 1, "c1", ok=k_rec(c1), req=[(6, FNO(1) + b"c1")])
    s.add("CLOSEALL", ok=k_ok("", 0), req=[(1, b"")])
    r = h_go(None, s, (A,), admin=True)
    row("the administrator's program ran to the end and no connection is left", h_sane(r), h_why(r))
    judge(r, s)
    row("...the fake saw one connection with exactly those requests and the audit trail has the open line", a_wire(r, s) and r.audits == s.audits(), repr(r.audits))

    # case blind list, case blind names
    s = Script()
    s.add("OPEN", "nfcase", "HCUST", label="a definition whose accounts list is in capitals (ZZNHON) lists the account zznhon: the test is case blind; the file name in capitals goes to the wire in lower case",
          ok=k_ok("1", 1), req=[(3, b"acct"), (4, b"hcust")], audit="open server=nfcase file=hcust")
    s.add("CLOSEALL", ok=k_ok("", 0), req=[(1, b"")])
    r = h_go("zznhon", s, (A,))
    row("the case-blind program ran to the end", h_sane(r), h_why(r))
    judge(r, s)
    row("...with the requests listed", a_wire(r, s), "")


# ---- H2. read only ----------------------------------------------------------------------------------------------------------------------------

def readonly_section():
    say("\n--- MODE READ (the delivered default, THE CONTROL for slice 3e): write, writeu, delete, deleteu, clear.file and lock on a handle of a read-mode server are refused with "
        "message 11501 and NOTHING is sent ---")
    if not h_prep():
        return
    A = S["A"]
    before = A.store.records(HFILE)
    c1 = RECS["c1"]
    s = Script()
    s.add("OPEN", "nfa", HFILE, ok=k_ok("1", 1), req=[(3, b"acct"), (4, b"hcust")], audit="open server=nfa file=hcust")
    s.add("READ", 1, "c1", ok=k_rec(c1), req=[(6, FNO(1) + b"c1")])
    s.add("WRITE", 1, "c1", "changed", label="MODE READ: WRITE is refused: 11501 naming the server and the operation (write)", ok=k_err(11501, "nfa", "write"))
    s.add("WRITEU", 1, "c1", "changed", label="MODE READ: WRITEU is refused: 11501 (writeu)", ok=k_err(11501, "nfa", "writeu"))
    s.add("DELETE", 1, "c1", label="MODE READ: DELETE is refused: 11501 (delete)", ok=k_err(11501, "nfa", "delete"))
    s.add("DELETEU", 1, "c1", label="MODE READ: DELETEU is refused: 11501 (deleteu)", ok=k_err(11501, "nfa", "deleteu"))
    s.add("CLEARFILE", 1, label="MODE READ: CLEARFILE is refused: 11501 (clear.file)", ok=k_err(11501, "nfa", "clear.file"))
    s.add("LOCK", 1, "c1", "u", label="MODE READ: LOCK is refused: 11501 (lock), whatever the lock kind", ok=k_err(11501, "nfa", "lock"))
    s.add("WRITE", 99, "c1", "x", label="WRITE on a handle that is not open is 11494, not a refusal that hides it", ok=k_err(11494, 99))
    s.add("RAW", 9, 1, "c1", label="the same operation by its number (RAW 9) is the refusal too", ok=k_err(11501, "nfa", "write"))
    s.add("RAW", 99, label="an operation number the handler does not know is 11490 naming it", ok=k_err(11490, 99))
    s.add("RAW", 0, label="...and operation 0 is not known either", ok=k_err(11490, 0))
    s.add("READ", 1, "c1", label="the handle still works after the refusals", ok=k_rec(c1), req=[(6, FNO(1) + b"c1")])
    s.add("CLOSEALL", ok=k_ok("", 0), req=[(1, b"")])
    r = h_go("zznhon", s, (A,))
    row("the read-only program ran to the end and no connection is left", h_sane(r), h_why(r))
    judge(r, s)
    d = r.d[0]
    ses = d["sessions"][0] if d["sessions"] else None
    row("...THE FAKE SAW NO REQUEST FOR THEM: only ACCOUNT, OPEN, READ, READ, Quit (types 3 4 6 6 1; none of 16 to 19 the writes and deletes, 5 close, 7 8 9 10 locking reads)",
        a_wire(r, s) and ses is not None and set(ses.requests) <= {1, 3, 4, 6}, repr(ses and ses.requests))
    row("...and the file on the fake is the very dictionary it was (every record equal) and the session holds no lock", A.store.records(HFILE) == before and ses is not None and A.store.locks_of(ses.userno) == [], "")


# ---- H3. everything is checked before anything is dialled ---------------------------------------------------------------------------------

def refuse_section():
    say("\n--- every local check refuses BEFORE anything is dialled: zero connections, zero packets, and the audit trail says why ---")
    if not h_prep():
        return
    A, B = S["A"], S["B"]

    def nothing_dialled(r, label):
        row(label, all(d["conns"] == 0 and d["handshakes"] == 0 and d["types"] == [] and d["app_bytes"] == 0 for d in r.d),
            repr([{k: d[k] for k in ("conns", "handshakes", "types", "app_bytes")} for d in r.d]))

    # -- the NET gate
    s = Script()
    s.add("OPEN", "nfa", HFILE, label="THE NET GATE OFF (zznhoff, listed for nfa): 11460 'This account does not have the NET gate' with the account and the server", ok=k_err(11460, "zznhoff", "nfa"),
          audit="refused server=nfa reason=gate")
    s.add("OPEN", "nosuch", HFILE, label="...the gate is asked BEFORE the definition: an undefined server is still 11460, not 11430", ok=k_err(11460, "zznhoff", "nosuch"), audit="refused server=nosuch reason=gate")
    s.add("OPEN", "1abc", HFILE, label="...and before the shape of the name: server=invalid in the audit line, never the bytes typed", ok=k_err(11460, "zznhoff", "invalid"),
          audit="refused server=invalid reason=gate")
    s.add("OPEN", "NFA", "a/b", label="...and before the file name; the server's name is lower cased in the message", ok=k_err(11460, "zznhoff", "nfa"), audit="refused server=nfa reason=gate")
    s.add("STATE", ok=k_state(0, 0, 0, 0, 0, 0))
    r = h_go("zznhoff", s, (A, B))
    row("the gate-off program ran to the end", h_sane(r), h_why(r))
    judge(r, s)
    nothing_dialled(r, "...NOTHING WAS DIALLED: neither fake saw a connection, a handshake or a byte")
    row("...the audit trail has exactly the four refusals, in order, each with its reason, and no key, hash, salt or password", r.audits == s.audits() and secret_free(r.audit), repr(r.audits))

    # -- the accounts list, and the order of the checks
    s = Script()
    s.add("OPEN", "nfa", HFILE, label="AN ACCOUNT NOT IN THE LIST (zznhunl: the gate on, nfa lists zznhon and zznhoff): 11461 with the account and the server", ok=k_err(11461, "zznhunl", "nfa"),
          audit="refused server=nfa reason=list")
    s.add("OPEN", "nfb", HFILE, ok=k_err(11461, "zznhunl", "nfb"), audit="refused server=nfb reason=list")
    s.add("OPEN", "nfnocred", HFILE, label="...the list is asked BEFORE the stored login: nfnocred has none, and an unlisted account is told 11461, not 11453", ok=k_err(11461, "zznhunl", "nfnocred"),
          audit="refused server=nfnocred reason=list")
    s.add("OPEN", "nosuch", HFILE, label="...the definition is asked BEFORE the list: an undefined server is 11430 'No server is defined with the name nosuch'", ok=k_err(11430, "nosuch"),
          audit="refused server=nosuch reason=server")
    s.add("OPEN", "nfbhost", HFILE, label="...and a definition that cannot be used (host 'bad host') is 11492 before the list is looked at", ok=k_err(11492, "nfbhost", "host"),
          audit="refused server=nfbhost reason=server")
    r = h_go("zznhunl", s, (A, B))
    row("the unlisted-account program ran to the end", h_sane(r), h_why(r))
    judge(r, s)
    nothing_dialled(r, "...NOTHING WAS DIALLED")
    row("...the audit trail has exactly those refusals in order", r.audits == s.audits() and secret_free(r.audit), repr(r.audits))

    # -- the server, the definition, the credential and the file name, in this order
    s = Script()
    s.add("OPEN", "1abc", HFILE, label="a server name that starts with a digit is 11452, with the name as typed (the audit line says server=invalid)", ok=k_err(11452, "1abc"), audit="refused server=invalid reason=server")
    s.add("OPEN", "bad name", HFILE, label="a server name with a space is 11452", ok=k_err(11452, "bad name"), audit="refused server=invalid reason=server")
    s.add("OPEN", "nosuch", HFILE, label="a server nobody defined is 11430", ok=k_err(11430, "nosuch"), audit="refused server=nosuch reason=server")
    for nm, fld in (("nfbhost", "host"), ("nfbport", "port"), ("nfbacct", "account"), ("nfbkey", "key")):
        s.add("OPEN", nm, HFILE, label="a definition whose %s is not valid is 11492 naming the server and the field (%s)" % (fld, fld), ok=k_err(11492, nm, fld), audit="refused server=%s reason=server" % nm)
    s.add("OPEN", "nfnocred", HFILE, label="NO STORED LOGIN: 11453 'There is no login stored for server nfnocred'", ok=k_err(11453, "nfnocred"), audit="refused server=nfnocred reason=credential")
    s.add("OPEN", "nfcpin", HFILE, label="A STORED LOGIN MADE FOR ANOTHER KEY than the definition has now: 11455 (the pin of the login differs from the definition's)", ok=k_err(11455, "nfcpin"),
          audit="refused server=nfcpin reason=credential")
    s.add("OPEN", "nfnocred", "a/b", label="the stored login is asked BEFORE the file name: a bad file name on a server with no login is 11453", ok=k_err(11453, "nfnocred"),
          audit="refused server=nfnocred reason=credential")
    for bad in ("a/b", "../../etc/passwd", "", "x" * 64, "dict a/b", "bad name", "a;b"):
        s.add("OPEN", "nfa", bad, label="the remote file name %r is 11491 (letters, digits and . _ - $ up to 63, dict in front for a dictionary; no slash)" % (bad if len(bad) < 20 else bad[:8] + "..."),
              ok=k_err(11491, "nfa", bad), audit="refused server=nfa reason=file")
    s.add("STATE", label="after all of them the process holds nothing: 0 servers, 0 files, nothing opened, nothing sent", ok=k_state(0, 0, 0, 0, 0, 0))
    r = h_go("zznhon", s, (A, B))
    row("the refusals program ran to the end", h_sane(r), h_why(r))
    judge(r, s)
    nothing_dialled(r, "...NOTHING WAS DIALLED, for any of them: neither fake saw a connection, a handshake or an application byte")
    row("...the audit trail has one 'netfile refused' line for each of the %d refusals, in order, with the reason, and no 'netfile open' line" % len(s.audits()),
        r.audits == s.audits() and secret_free(r.audit), repr(r.audits))

    # -- the shapes of the arguments of the other operations, with a file open: nothing is sent for any of them
    s = Script()
    s.add("OPEN", "nfa", HFILE, ok=k_ok("1", 1), req=[(3, b"acct"), (4, b"hcust")], audit="open server=nfa file=hcust")
    for hv in ("0", "101", "abc", "", "-1", "2"):
        s.add("READ", hv, "c1", label="READ with the handle %r is 11494 (not an open handle), nothing sent" % hv, ok=k_err(11494, hv))
    s.add("READ", 1, "x" * 64, label="a record id of 64 characters is 11503 'too long', nothing sent", ok=k_err(11503, "nfa", "too long"))
    for fv in ("x", "-1", "", "1234567", "1.5"):
        s.add("READV", 1, "c1", fv, label="READV with the field number %r is 11506, nothing sent" % fv, ok=k_err(11506, "nfa", fv))
    s.add("FILEINFO", 1, "abc", label="FILEINFO with a key that is not a number is 11502, nothing sent", ok=k_err(11502, "nfa", "abc"))
    s.add("RAW", 17, label="an operation number that is kept free (17, for a possible combined lock-and-read; 14 to 16 are WRITEU, DELETEU and RELEASE since slice 3e) is 11490", ok=k_err(11490, 17))
    s.add("CLOSEALL", ok=k_ok("", 0), req=[(1, b"")])
    r = h_go("zznhon", s, (A,))
    row("the argument-shape program ran to the end and no connection is left", h_sane(r), h_why(r))
    judge(r, s)
    row("...THE FAKE SAW ONLY the login, ACCOUNT, OPEN and the Quit: not one request for a refused argument", a_wire(r, s), repr(h_wire(r.d[0])))

    # -- the limits
    s = Script()
    for k in range(1, 11):
        s.add("OPEN", "nfs%02d" % k, HFILE, label=("TEN SERVERS: OPEN of nfs01 to nfs10 each gives handle 1 to 10 (ten connections)" if k == 1 else None), ok=k_ok(str(k), len(str(k))),
              audit="open server=nfs%02d file=hcust" % k)
    s.add("OPEN", "nfs11", HFILE, label="THE 11TH SERVER is refused: 11493 'This process already holds connections to 10 servers, so server nfs11 cannot be added'",
          ok=k_err(11493, 10, "nfs11"), audit="refused server=nfs11 reason=limit")
    s.add("OPEN", "nfs01", HFILE, label="...but a second file on a server already connected is not a new server: handle 11", ok=k_ok("11", 2), audit="open server=nfs01 file=hcust")
    s.add("READ", 11, "c1", ok=k_rec(RECS["c1"]))
    s.add("STATE", label="STATE: 10 servers, 11 files, 11 opened in all; nfs01 holds two files and every connection is an object", ok=k_state(
        10, 11, 11, 12, 0, 0, conns=[("nfs01", 15, 2)] + [("nfs%02d" % k, 15, 1) for k in range(2, 11)]))
    s.add("CLOSEALL", ok=k_ok("", 0))
    r = h_go("zznhon", s, (A,))
    row("the ten-servers program ran to the end and no connection is left", h_sane(r), h_why(r))
    judge(r, s)
    d = r.d[0]
    row("...THE 11TH WAS NOT DIALLED: the fake accepted exactly 10 connections, each ended with a Quit after CLOSEALL", d["conns"] == 10 and len(d["sessions"]) == 10 and quit_seen(d), repr((d["conns"], len(d["sessions"]))))
    row("...the audit trail: ten opens, the refusal for the limit, the eleventh open", r.audits == s.audits() and secret_free(r.audit), repr(r.audits[-4:]))

    s = Script()
    for k in range(1, 101):
        s.add("OPEN", "nfa", HFILE, label=("ONE HUNDRED FILES on one server: 100 OPENs give handles 1 to 100 on one connection" if k == 1 else None), ok=k_ok(str(k), len(str(k))),
              audit="open server=nfa file=hcust")
    s.add("OPEN", "nfa", HFILE, label="THE 101ST FILE is refused: 11505 naming the server and the 100 files open", ok=k_err(11505, "nfa", 100), audit="refused server=nfa reason=limit")
    s.add("CLOSE", 100, label="after one is closed the next OPEN gets handle 100 again (the lowest free)", ok=k_ok("", 0))
    s.add("OPEN", "nfa", HFILE, ok=k_ok("100", 3), audit="open server=nfa file=hcust")
    s.add("CLOSEALL", ok=k_ok("", 0))
    r = h_go("zznhon", s, (A,))
    row("the hundred-files program ran to the end and no connection is left", h_sane(r), h_why(r))
    judge(r, s)
    row("...one connection served all of it", r.d[0]["conns"] == 1 and r.audits == s.audits(), repr((r.d[0]["conns"], len(r.audits))))

    # -- a key that is not the pinned one, and a port nobody listens on: these DIAL (all local checks passed) and are refused by the class
    s = Script()
    s.add("OPEN", "nfpin", HFILE, label="PIN MISMATCH: server B presents key two, the definition holds A's hash: 11498 'Cannot log in to server nfpin' with the class's text naming the host and port, "
          "and saying nothing was sent (the handler shows the first 100 characters of the class's text)",
          ok=k_err(11498, "nfpin", ("PIN MISMATCH: the public key of 127.0.0.1:%d is not the key pinned in its definition; nothing was sent" % B.port)[:100]),
          audit="open server=nfpin file=hcust")
    s.add("STATE", label="...and the failed login left nothing in common: 0 servers, nothing opened", ok=k_state(0, 0, 0, 0, 0, 0))
    r = h_go("zznhon", s, (A, B))
    row("the pin-mismatch program ran to the end", h_sane(r), h_why(r))
    judge(r, s)
    da, db = r.d
    row("...THE FAKE THAT PRESENTED THE WRONG KEY RECEIVED NOTHING: one connection and a completed handshake, ZERO request packets, ZERO application bytes (not even client-first), no proof, "
        "no session; server A saw no connection at all", db["conns"] == 1 and db["handshakes"] == 1 and db["types"] == [] and db["app_bytes"] == 0 and db["ok"] == 0 and db["bad"] == 0 and not db["sessions"]
        and da["conns"] == 0, repr({k: db[k] for k in ("conns", "handshakes", "types", "app_bytes")}))
    row("...the audit trail has the open line (every local check passed) and nothing secret", r.audits == s.audits() and secret_free(r.audit), repr(r.audits))
    s = Script()
    s.add("OPEN", "nfdead", HFILE, label="a port nobody listens on: 11498 naming the server and the class's 'Cannot connect to 127.0.0.1:<port>'",
          ok=lambda c: c["rc"] == "3" and c["m"] == "11498" and c["args"][0] == "nfdead" and c["args"][1].startswith("Cannot connect to 127.0.0.1:%d" % S["dead"]) and c["args"][2] == "" and c["len"] == 0,
          audit="open server=nfdead file=hcust")
    s.add("STATE", ok=k_state(0, 0, 0, 0, 0, 0))
    r = h_go("zznhon", s, (A, B))
    row("the dead-port program ran to the end", h_sane(r), h_why(r))
    judge(r, s)
    row("...neither fake saw a connection", all(d["conns"] == 0 for d in r.d) and r.audits == s.audits(), repr(r.audits))


# ---- H4. a lost connection, CLOSEALL, the end of the session ---------------------------------------------------------------------------------

def lost_section():
    say("\n--- a connection that is lost is reported on the next use and never silently reconnected; CLOSEALL; the end of a session ---")
    if not h_prep():
        return
    A, B = S["A"], S["B"]
    c1 = RECS["c1"]

    # -- the fake reads the 4th request of the session (ACCOUNT, OPEN, READ, READ) and closes without answering it
    s = Script()
    s.add("OPEN", "nfa", HFILE, ok=k_ok("1", 1), audit="open server=nfa file=hcust")
    s.add("READ", 1, "c1", ok=k_rec(c1))
    s.add("READ", 1, "c2", label="A CONNECTION THE SERVER CLOSES WITHOUT A REPLY: the READ is 11497 'The connection to server nfa was lost during read'", ok=k_err(11497, "nfa", "read"))
    s.add("READ", 1, "c1", label="...the next use of the handle is 11495 (the connection was lost earlier), not a new connection", ok=k_err(11495, "nfa", 1))
    s.add("STATE", label="...STATE: 0 servers, 0 files, 1 opened, 3 requests sent (the lost one counted), 1 connection dropped, 1 file lost", ok=k_state(0, 0, 1, 3, 1, 1))
    s.add("OPEN", "nfa", HFILE, label="OPEN reconnects, and gets handle 2 (handle 1 is still the lost one)", ok=k_ok("2", 1), audit="open server=nfa file=hcust")
    s.add("READ", 2, "c1", label="...and the new connection answers", ok=k_rec(c1))
    s.add("CLOSE", 1, label="CLOSE of the lost handle frees it without a word (rc 0)", ok=k_ok("", 0))
    s.add("STATE", label="...STATE: 1 server, 1 file, 2 opened, nothing lost now, 1 dropped in all", ok=k_state(1, 1, 2, 5, 1, 0, conns=[("nfa", 15, 1)]))
    s.add("CLOSEALL", ok=k_ok("", 0))
    r = h_go("zznhon", s, (A,), cfg={"drop_request": 4})
    row("the lost-connection program ran to the end and no connection is left", h_sane(r), h_why(r))
    judge(r, s)
    d = r.d[0]
    row("...THERE WAS NO SILENT RECONNECT: the fake saw exactly TWO connections (the first, and the one the explicit OPEN made), the first with ACCOUNT, OPEN, READ and the dropped READ, the second "
        "with ACCOUNT, OPEN, READ and a Quit", d["conns"] == 2 and by_conn(d) == [[47, 48, 3, 4, 6, 6], [47, 48, 3, 4, 6, 1]], repr(by_conn(d)))

    # -- the server closes a connection after replying: the handler cannot know until the next request
    s = Script()
    s.add("OPEN", "nfa", HFILE, ok=k_ok("1", 1), audit="open server=nfa file=hcust")
    s.add("READ", 1, "c1", ok=k_rec(c1))
    s.add("OPEN", "nfa", HEMPTY, label="A CONNECTION THAT DIED UNNOTICED (the server closed it after its 3rd reply): the next OPEN on it fails ONCE, with 11497 'lost during open'",
          ok=k_err(11497, "nfa", "open"), audit="open server=nfa file=hempty")
    s.add("STATE", ok=k_state(0, 0, 1, 3, 1, 1))
    s.add("OPEN", "nfa", HEMPTY, label="...and the OPEN after that dials again and succeeds (handle 2)", ok=k_ok("2", 1), audit="open server=nfa file=hempty")
    s.add("READ", 2, "x", ok=k_else(3006))
    s.add("CLOSEALL", ok=k_ok("", 0))
    r = h_go("zznhon", s, (A,), cfg={"close_after_requests": 3})
    row("the died-unnoticed program ran to the end and no connection is left", h_sane(r), h_why(r))
    judge(r, s)
    d = r.d[0]
    row("...the fake saw two connections, the second with ACCOUNT, OPEN, READ", d["conns"] == 2 and by_conn(d)[-1][:5] == [47, 48, 3, 4, 6] and r.audits == s.audits(), repr(by_conn(d)))

    # -- CLOSEALL
    s = Script()
    s.add("OPEN", "nfa", HFILE, ok=k_ok("1", 1))
    s.add("OPEN", "nfb", HFILE, ok=k_ok("2", 1))
    s.add("READ", 1, "c1", ok=k_rec(c1))
    s.add("READ", 2, "c1", ok=k_rec(c1))
    s.add("CLOSEALL", label="CLOSEALL with two connections held: rc 0", ok=k_ok("", 0))
    s.add("STATE", label="...nothing is held afterwards: 0 servers, 0 files", ok=k_state(0, 0, 2, 4, 0, 0))
    s.add("READ", 1, "c1", label="...a handle from before it is 11494", ok=k_err(11494, 1))
    s.add("READ", 2, "c1", ok=k_err(11494, 2))
    s.add("CLOSEALL", label="CLOSEALL with nothing held is rc 0, no error", ok=k_ok("", 0))
    s.add("OPEN", "nfa", HFILE, label="OPEN after CLOSEALL dials again (handle 1)", ok=k_ok("1", 1))
    s.add("READ", 1, "c2", ok=k_rec(RECS["c2"]))
    s.add("CLOSEALL", ok=k_ok("", 0))
    r = h_go("zznhon", s, (A, B))
    row("the CLOSEALL program ran to the end and no connection is left", h_sane(r), h_why(r))
    judge(r, s)
    da, db = r.d
    row("...CLOSEALL ENDED THE CONNECTIONS: server A saw two connections and server B one, every one ended with a Quit (ACCOUNT, OPEN, READ, Quit)",
        da["conns"] == 2 and db["conns"] == 1 and by_conn(da) == [[47, 48, 3, 4, 6, 1]] * 2 and by_conn(db) == [[47, 48, 3, 4, 6, 1]] and quit_seen(da) and quit_seen(db), repr((by_conn(da), by_conn(db))))

    # -- the end of the session with connections still held
    s = Script()
    s.add("OPEN", "nfa", HFILE, ok=k_ok("1", 1))
    s.add("OPEN", "nfb", HFILE, ok=k_ok("2", 1))
    s.add("READ", 1, "c1", ok=k_rec(c1))
    r = h_go("zznhon", s, (A, B))
    row("A SESSION THAT ENDS WITH TWO CONNECTIONS HELD (no CLOSEALL): the program reached its end, and no socket is left open on either fake - every served session ended (the Quit is not required; "
        "the process ending closes the socket, which is what the kernel's CLOSEALL before the e-stack is freed is for)", h_sane(r) and all(x.closed for d in r.d for x in d["sessions"]),
        h_why(r) + " | requests " + repr([[x.requests for x in d["sessions"]] for d in r.d]))

    # -- the handle belongs to the account that opened it
    s = Script()
    s.add("OPEN", "nfa", HFILE, ok=k_ok("1", 1))
    s.add("EXEC", "LOGTO zznhunl", label="(LOGTO zznhunl: the NET gate on there, not listed for nfa)", ok=lambda c: c["rc"] == "")
    s.add("READ", 1, "c1", label="A HANDLE DOES NOT SURVIVE A LOGTO: from another account, READ on handle 1 is 11494 (the gate is on there, so it is the account that is refused)", ok=k_err(11494, 1))
    s.add("OPEN", "nfa", HFILE, label="...and the other account is held to ITS list: OPEN nfa is 11461", ok=k_err(11461, "zznhunl", "nfa"), audit="refused server=nfa reason=list")
    s.add("CLOSE", 1, label="...CLOSE of the first account's handle is allowed (so that the connection can be cleaned up): rc 0", ok=k_ok("", 0))
    s.add("CLOSEALL", ok=k_ok("", 0))
    r = h_go("zznhon", s, (A,))
    row("the LOGTO program ran to the end and no connection is left", h_sane(r), h_why(r))
    judge(r, s)


# ---- H5. the time a silent server is waited for ------------------------------------------------------------------------------------------------

def timeout_section():
    say("\n--- a server that reads a request and never answers: the handler gives up after its 30 seconds and reports the connection lost (this section takes about 35 s) ---")
    if not h_prep():
        return
    A = S["A"]
    s = Script()
    s.add("OPEN", "nfa", HFILE, ok=k_ok("1", 1))
    s.add("READ", 1, "c1", label="THE REQUEST TIMEOUT: a READ the server never answers is 11497 'lost during read'", ok=k_err(11497, "nfa", "read"))
    s.add("STATE", label="...and the connection is dropped: 0 servers, 1 file lost", ok=k_state(0, 0, 1, 2, 1, 1))
    r = h_go("zznhon", s, (A,), cfg={"no_reply": (6,), "idle": 60.0})
    row("the silent-server program ran to the end and no connection is left", h_sane(r), h_why(r))
    judge(r, s)
    row("...it waited about 30 seconds and not for ever or for 1: the whole session took %.0f s (28 to 60 expected)" % r.el, 28 <= r.el <= 60, "%.1f s" % r.el)

    # 19 Oct 26, K8d: the wait is the configuration parameter NETREPLY, 30 seconds by default.  A session takes its configuration from the shared memory the daemon filled when it
    # STARTED (sysseg.c copies pcfg), so a line in sd.conf needs the sandbox's daemon stopped and started again, here and again afterwards to put the file and the daemon back.
    conf = os.path.join(g.BOX, "sd.conf")
    with open(conf) as f:
        original = f.read()

    def daemon(*lines):
        return netfake.restart_with_conf(g.BOX, g.TOOL, original, lines)
    try:
        started = daemon("NETREPLY=3", "NETWAIT=2")
        row("SD starts with NETREPLY=3 and NETWAIT=2 in sd.conf (a row below that needs the new values fails if it did not)", started, "")
        # 19 Oct 26, finish 2 (verifier): nothing showed NETREPLY bounding the LOGIN exchange of connect.keys, or NETWAIT bounding the connection it makes; the source-text checks of
        # test-net-units were the only guard (a hard-coded 5 and a hard-coded 30 left every suite green).  The class driver is used (op KEYS), with no TMO first, so the waits are the
        # configuration's: a server that goes silent after the Ack costs NETREPLY, a listener whose accept queue is full costs NETWAIT.  A control (a closed port, refused at once) gives the
        # session's own cost, which is taken off.
        A_ = S["A"]
        alice_ = S["alice"][id(A_)]
        hang = netfake.HangingListener()
        try:
            row("SETUP: a connect to the full listener on port %d hangs (so a row can show a timeout; a machine that does not hang a connect that way fails the NETWAIT row, it does not pass it)" % hang.port,
                hang.hangs(), "the connect completed or failed at once")
            base = go(keys(alice_, A_, port=str(S["dead"])), A_)
            row("CONTROL (the session's own cost): a connect to a closed port is refused at once, ok=0 'Cannot connect' (%.1f s for the whole session)" % base.el,
                sane(base) and any(ln.startswith("FX KEYS ok=0 err=[Cannot connect") for ln in base.fx), why(base))
            r = go(keys(alice_, A_, port=str(hang.port)), A_)
            took = r.el - base.el
            m = re.fullmatch(r"FX KEYS ok=0 err=\[Cannot connect to 127\.0\.0\.1:%d \(status (\d+)\)\]" % hang.port, next(iter(fx_lines(r, "KEYS")), ""))
            row("NETWAIT=2 BOUNDS THE CONNECTION connect.keys makes (a listener whose accept queue is full): ok=0 'Cannot connect to 127.0.0.1:%d', about 2 seconds more than the control - %.1f s "
                "(1.5 to 3.9 expected; the 5 it used to be fixed at would be 5)" % (hang.port, took), sane(r) and m is not None and 1.5 <= took <= 3.9, why(r) + " took %.1f s over the control" % took)
        finally:
            hang.close()
        # THE LOGIN EXCHANGE.  First what is bounded: the fake sends the Ack, reads client-first and then says nothing for up to 12 seconds (netfake stall_first; it lets go as soon as the client
        # does).  The wait for the server's first message is a read after the Ack, so NETREPLY applies: 3 seconds, and 'No reply ... during the login'.  A client that waited the 30 seconds it
        # used to be fixed at would still be waiting when the fake lets go at 12, so the window ends well below that.
        no_reply = "No reply from 127.0.0.1:%d during the login (the connection failed or timed out)" % A_.port
        r = go(keys(alice_, A_), A_, cfg={"stall_first": 12.0})
        took = r.el - base.el
        row("NETREPLY=3 BOUNDS THE LOGIN EXCHANGE of connect.keys (no TMO first): a server that sends the Ack, reads client-first and then says nothing - ok=0 'No reply ... during the login', "
            "the fake saw packet 47 only, about 3 seconds more than the control - %.1f s (2.5 to 4.5 expected; the fake holds the connection for 12, and the 30 it used to be fixed at would run to that)" % took,
            sane(r) and kline(0, no_reply) in r.fx and r.d["types"] == [47] and 2.5 <= took <= 4.5, why(r) + " took %.1f s over the control" % took)
        # THE SILENT SERVER AFTER THE HANDSHAKE (found by this row's first version, 19 Oct 26, and kept as a KNOWN LIMIT until 20 Oct 26): a server that completes the TLS 1.3 handshake and
        # never sends the Ack.  After the handshake the server sends the session tickets; they make the socket readable, READ.SOCKET's wait (op_skt.c, socket_wait) ends, and the SSL_read behind
        # it took the tickets and then blocked without a timeout until the server sent something or closed.  THE FAKE CLOSES A SILENT CONNECTION AT 5 SECONDS (netfake.FakeServer.handle:
        # tls.settimeout(5) while it waits for client-first), so the wait ended at 5.0 s here, not at 3 (measured 19 Oct 26: 5.0 s; with the tickets turned off in a scratch copy of the fake, 3.0).
        # S.73 item 2 (the owner delegated the choice, 20 Oct 26: "silent-server your choice"): READ.SOCKET reads a TLS socket with a non-blocking SSL_read and waits on the descriptor for the time
        # that is LEFT, so the tickets and a half record cost the wait they have used and no more.  The row is the old known-limit row, flipped: it expects NETREPLY.
        no_ack = "No acknowledgement from 127.0.0.1:%d at the start of the session" % A_.port
        r = go(keys(alice_, A_), A_, cfg={"ack": False})
        took = r.el - base.el
        say("      [timing] silent AFTER the handshake (the Ack never comes), NETREPLY=3: the session took %.2f s, the control (a closed port) %.2f s, so the wait was %.2f s" % (r.el, base.el, took))
        row("A SERVER THAT COMPLETES THE HANDSHAKE AND NEVER SENDS THE ACK IS GIVEN UP ON AT NETREPLY=3 (it ran to the fake's own close at 5 s until 20 Oct 26): ok=0 'No acknowledgement', NOTHING sent, "
            "%.1f s more than the control (2.5 to 4.5 expected; the fake would have closed at 5.0)" % took,
            sane(r) and kline(0, no_ack) in r.fx and r.d["types"] == [] and 2.5 <= took <= 4.5, why(r) + " took %.1f s over the control" % took)
        r = go(keys(alice_, A_) + ["DISC"], A_)
        row("CONTROL: the same fake, nothing wrong, logs in while those values are in force", sane(r) and kline(1, "") in r.fx, why(r))
        # THE SILENCE AT THE HANDSHAKE (S.73 item 2): a listener that accepts the connection and never answers the TLS hello.  NETWAIT is "the connection" (set.server connect, set.netlogin and the
        # first use of a defined server all say so) but the handshake had a bound of its own, 15 seconds fixed in op_skt.c (SD_TLS_HANDSHAKE_MS + 5000), so NETWAIT=2 did not bound it.  It does now.
        silent = netfake.SilentListener()
        try:
            r = go(keys(alice_, A_, port=str(silent.port)), A_)
            took = r.el - base.el
            time.sleep(0.5)
            m = re.fullmatch(r"FX KEYS ok=0 err=\[The TLS handshake with 127\.0\.0\.1:%d did not complete \(status (\d+)\)\]" % silent.port, next(iter(fx_lines(r, "KEYS")), ""))
            say("      [timing] silent AT the handshake (TCP accepted, the hello never answered), NETWAIT=2: the session took %.2f s, the control %.2f s, so the wait was %.2f s (the listener accepted %d, saw the client close %d)"
                % (r.el, base.el, took, silent.accepted, silent.count_closed()))
            row("NETWAIT=2 BOUNDS THE TLS HANDSHAKE: a server that accepts the connection and never answers the hello - ok=0 'The TLS handshake with 127.0.0.1:%d did not complete', %.1f s more than the control "
                "(1.5 to 3.9 expected; the 15 s that were fixed would be 15)" % (silent.port, took),
                sane(r) and m is not None and silent.accepted == 1 and 1.5 <= took <= 3.9, why(r) + " took %.1f s over the control; accepted %d" % (took, silent.accepted))
            row("...and the client closed the connection itself (the listener saw the close)", silent.count_closed() == 1, "closed %d" % silent.count_closed())
        finally:
            silent.close()
        # HALF A TLS RECORD (S.73 item 2): the socket is readable and what is in it is not a record, so a blocking SSL_read waits for the rest: the same hang as the tickets, from a server that
        # dies or stalls in the middle of a record.  netfake.PartialRecordServer sends the Ack as half a record (cut='ack'), or the reply to client-first as half a record (cut='first').
        # The evidence of the time is the server's own log, from the cut to the client's close, as well as the session's.
        c_, k_ = S["certs"][id(A_)]
        for cut, what, wants in (("ack", "the Ack as half of a TLS record", "No acknowledgement from 127.0.0.1:%d at the start of the session"),
                                 ("first", "the reply to client-first as half of a TLS record (MID-REPLY)", "No reply from 127.0.0.1:%d during the login (the connection failed or timed out)")):
            ps = netfake.PartialRecordServer(c_, k_, cut=cut, hold=12.0)
            try:
                r = go(keys(alice_, A_, port=str(ps.port)), A_)
                took = r.el - base.el
                time.sleep(0.6)
                e = ps.log[-1] if ps.log else {}
                say("      [timing] silent after %s, NETREPLY=3: the session took %.2f s, the control %.2f s, so the wait was %.2f s; the server sent %s of %s bytes of the record and the client closed %s s after"
                    % (what, r.el, base.el, took, e.get("sent"), e.get("whole"), ("%.2f" % e["closed_after"]) if e.get("closed_after") is not None else "never"))
                row("NETREPLY=3 BOUNDS A READ THAT HOLDS HALF A TLS RECORD - %s: ok=0 '%s', %.1f s more than the control and the client closed %s s after the cut (2.5 to 4.5 expected; the server would have held it 12 s)"
                    % (what, wants.split(" from ")[0], took, ("%.1f" % e["closed_after"]) if e.get("closed_after") is not None else "never"),
                    sane(r) and kline(0, wants % ps.port) in r.fx and e.get("handshake") is True and e.get("sent") is not None and 0 < e["sent"] < e["whole"]
                    and 2.5 <= took <= 4.5 and e.get("closed_after") is not None and 2.0 <= e["closed_after"] <= 4.5,
                    why(r) + " took %.1f s over the control; server log %r" % (took, e))
            finally:
                ps.close()
        # THE LEGITIMATE SLOW SERVER (S.73 item 2): a server that answers inside NETREPLY must not be given up on.  The fake holds the reply to a READ back 1.5 s (delay {6: 1.5}; the fake's delay
        # is for the requests after the login) with NETREPLY=3 in force: the READ returns its record, and the session takes about that long more than the same session with no delay.
        ops = keys(alice_, A_) + ["OPEN|customers|1", "READ|1|c1", "DISC"]
        r0 = go(ops, A_)
        r = go(ops, A_, cfg={"delay": {6: 1.5}})
        extra = r.el - r0.el
        say("      [timing] a SLOW server (1.5 s before the reply to a READ), NETREPLY=3: the session took %.2f s, the same session with no delay %.2f s, so the extra was %.2f s" % (r.el, r0.el, extra))
        row("A SLOW SERVER INSIDE NETREPLY IS NOT GIVEN UP ON: the reply to a READ comes after 1.5 s, NETREPLY=3 - the record is read (err 0), %.1f s more than the same session with no delay (1.2 to 2.6 expected)" % extra,
            sane(r) and sane(r0) and rl("READ", "c1", 0, RECS["c1"]) in r.fx and 1.2 <= extra <= 2.6, why(r) + " extra %.1f s" % extra)
        s = Script()
        s.add("OPEN", "nfa", HFILE, ok=k_ok("1", 1))
        s.add("READ", 1, "c1", label="THE REQUEST TIMEOUT FROM THE CONFIGURATION (NETREPLY=3 in sd.conf): a READ the server never answers is 11497 'lost during read'", ok=k_err(11497, "nfa", "read"))
        s.add("STATE", label="...and the connection is dropped, as after the 30 seconds", ok=k_state(0, 0, 1, 2, 1, 1))
        r = h_go("zznhon", s, (A,), cfg={"no_reply": (6,), "idle": 60.0})
        # MID-REPLY, THE HANDLER (S.73 item 2): the server executes the request and sends only the first 14 bytes of the reply packet (the 10 byte header and 4 bytes of the record), then nothing.
        # A READ is 11497 'lost during read'; a WRITE whose reply is cut in its header (6 of 10 bytes) is 11509, the outcome unknown, and is never sent a second time.  Both within NETREPLY=3.
        s2 = Script()
        s2.add("OPEN", "nfa", HFILE, ok=k_ok("1", 1))
        s2.add("READ", 1, "c1", label="MID-REPLY, NETREPLY=3: a READ whose reply stops after 14 of its bytes is 11497 'lost during read'", ok=k_err(11497, "nfa", "read"))
        s2.add("STATE", label="...and the connection is dropped: 0 servers, 1 file lost", ok=k_state(0, 0, 1, 2, 1, 1))
        r2 = h_go("zznhon", s2, (A,), cfg={"short_reply": {6: 14}, "short_reply_hold": 45.0, "idle": 60.0})
        r3 = s3 = None
        if hw_prep():
            s3 = Script()
            s3.add("OPEN", "nfw", HW, ok=k_open_w(1), audit=OPEN_W_AUD)
            s3.add("WRITE", 1, "w1", "changed", label="MID-REPLY, NETREPLY=3: a WRITE whose reply stops after 6 of its 10 header bytes is 11509 (the outcome is UNKNOWN: never sent a second time)",
                   ok=k_err(11509, "nfw", "write"), audit="write server=nfw file=hwork")
            s3.add("CLOSEALL", ok=k_ok("", 0))
            r3 = hw_go("zznhon", s3, (A,), cfg={"short_reply": {16: 6}, "short_reply_hold": 45.0, "idle": 60.0})
    finally:
        daemon()
    row("the NETREPLY=3 program ran to the end and no connection is left", h_sane(r), h_why(r))
    judge(r, s)
    row("...it waited about 3 seconds and not 30: the whole session took %.0f s (2 to 20 expected)" % r.el, 2 <= r.el <= 20, "%.1f s" % r.el)
    say("      [timing] a READ whose reply is cut after 14 bytes, NETREPLY=3: the whole session took %.2f s" % r2.el)
    row("the mid-reply READ program ran to the end and no connection is left", h_sane(r2), h_why(r2))
    judge(r2, s2)
    ses2 = r2.d[0]["sessions"] if r2.d else []
    row("...the fake cut the reply (it saw the READ once, injected short_reply, and the client CLOSED the connection - the fake's hold is 45 s) and the session took %.0f s (2 to 20 expected)" % r2.el,
        len(ses2) == 1 and ses2[0].requests.count(6) == 1 and ses2[0].injected == [(6, "short_reply")] and ses2[0].closed and 2 <= r2.el <= 20, repr(([x.requests for x in ses2], [x.injected for x in ses2], r2.el)))
    if r3 is not None:
        say("      [timing] a WRITE whose reply is cut after 6 bytes, NETREPLY=3: the whole session took %.2f s" % r3.el)
        row("the mid-reply WRITE program ran to the end and no connection is left", h_sane(r3), h_why(r3))
        judge(r3, s3)
        ses3 = r3.d[0]["sessions"] if r3.d else []
        row("...the audit trail: the open, the write, and 'lost server=nfw op=write'", r3.audits == [OPEN_W_AUD, "write server=nfw file=hwork", "lost server=nfw op=write"], repr(r3.audits))
        row("...the fake executed the WRITE exactly ONCE (the record holds the new text) and the client closed the connection; the session took %.0f s (2 to 20 expected)" % r3.el,
            len(ses3) == 1 and ses3[0].requests.count(16) == 1 and ses3[0].injected == [(16, "short_reply")] and ses3[0].closed and r3.stores[0][HW].get("w1") == "changed" and 2 <= r3.el <= 20,
            repr(([x.requests for x in ses3], [x.injected for x in ses3], r3.el, r3.stores[0][HW].get("w1"))))


# ---- H5b. the ceiling on a reply (19 Oct 26, K8c; this section takes about 15 s) -------------------------------------------------------------------

def oversize_section():
    say("\n--- a reply whose header announces a length that cannot be true (K8c, 19 Oct 26): the handler drops the connection AT ONCE and does not wait 30 s for a body that is not coming ---")
    if not hw_prep():
        return
    A = S["A"]
    for announced, why in ((3000000000, "3,000,000,000 (the count is read as a SIGNED 32 bit value, so it arrives negative)"),
                           (2000000000, "2,000,000,000 (positive, and more than the largest string SD holds plus a header: the ceiling NF$MAX.PACKET)"),
                           (4, "4 (less than the 10 byte header it is part of)")):
        s = Script()
        s.add("OPEN", "nfw", HW, ok=k_open_w(1), audit=OPEN_W_AUD)
        s.add("READ", 1, "w1", label="a READ answered with a header that announces %s: the connection is lost, 11497 'lost during read' naming the server" % why, ok=k_err(11497, "nfw", "read"))
        s.add("STATE", label="...the connection is dropped: no server connected, the file lost", ok=k_state(0, 0, 1, 2, 1, 1))
        s.add("CLOSEALL", ok=k_ok("", 0))
        r = hw_go("zznhon", s, (A,), cfg={"bad_length": {6: announced}, "bad_length_hold": 45.0, "idle": 60.0})
        row("announcing %d: the program ran to the end and no connection is left" % announced, h_sane(r), h_why(r))
        judge(r, s)
        ses = r.d[0]["sessions"] if r.d else []
        row("...the fake sent the bogus header for the READ and saw the client CLOSE the connection (a client without the ceiling would have waited out its 30 seconds)",
            len(ses) == 1 and ses[0].injected == [(6, "bad_length")] and ses[0].requests.count(6) == 1 and ses[0].closed, repr([(x.requests, x.injected, x.closed) for x in ses]))
        row("...it took %.0f s in all, not the 30 s or more a body that never comes costs (under 20 s expected)" % r.el, r.el < 20, "%.1f s" % r.el)

    s = Script()
    s.add("OPEN", "nfw", HW, ok=k_open_w(1), audit=OPEN_W_AUD)
    s.add("WRITE", 1, "w1", "changed", label="a WRITE answered with a header that announces 3,000,000,000: the outcome is UNKNOWN, 11509 naming the server and 'write' (never a second request)",
          ok=k_err(11509, "nfw", "write"), audit="write server=nfw file=hwork")
    s.add("CLOSEALL", ok=k_ok("", 0))
    r = hw_go("zznhon", s, (A,), cfg={"bad_length": {16: 3000000000}, "bad_length_hold": 45.0, "idle": 60.0})
    row("the WRITE program ran to the end and no connection is left", h_sane(r), h_why(r))
    judge(r, s)
    ses = r.d[0]["sessions"] if r.d else []
    row("...the audit trail: the open, the write, and 'lost server=nfw op=write'", r.audits == [OPEN_W_AUD, "write server=nfw file=hwork", "lost server=nfw op=write"], repr(r.audits))
    row("...the fake executed the WRITE exactly ONCE (the record holds the new text - the client cannot know) and saw the client close the connection at once",
        len(ses) == 1 and ses[0].requests.count(16) == 1 and ses[0].closed and r.stores[0][HW].get("w1") == "changed" and r.el < 20, repr(([x.requests for x in ses], r.el, r.stores[0][HW].get("w1"))))


# ---- H6. what the plan asks and the handler does not do yet (OPT-IN: --sections=gaps) -----------------------------------------------------------

def gaps_section():
    say("\n--- gaps (opt-in, RED BY DESIGN until built): what the plan asks of the handler where the handler as built does less ---")
    if not h_prep():
        return
    A = S["A"]
    n = len(A.store.records(HFILE))
    s = Script()
    s.add("OPEN", "nfa", HFILE, ok=k_ok("1", 1))
    s.add("FILEINFO", 1, 3, label="GAP: FILEINFO key 3 (the file type) is answered as the server answers it (3, a dynamic file); the handler answers 11502 (the class has no fileinfo method)", ok=k_ok("3", 1))
    s.add("FILEINFO", 1, 1008, label="GAP: FILEINFO key 1008 (case folding) is answered by the server (0)", ok=k_ok("0", 1))
    s.add("FILEINFO", 1, 1015, label="GAP: FILEINFO key 1015 (the record count) is answered by the server (%d)" % n, ok=k_ok(str(n), len(str(n))))
    s.add("CLOSEALL", ok=k_ok("", 0))
    r = h_go("zznhon", s, (A,))
    judge(r, s)
    s = Script()
    s.add("OPEN", "nfa", HFILE, label="GAP: an OPEN the server answers with an ON ERROR (file access disabled, 5262) is an ERROR (rc 3), not file-not-found (rc 2): the class returns 0 for both",
          ok=lambda c: c["rc"] == "3")
    r = h_go("zznhon", s, (A,), cfg={"no_file_access": True})
    judge(r, s)
    # (18 Oct 26, slice 3e: the row that stood here - a READ the server answers with an ON ERROR is an error rc 3 / 11500 and does not abort the handler - is built: the class is
    # QUIET since slice 3e.  It is in the normal section hwrite now, H14.)

    # the connection object sits in a named common block that ANY program can name (the kernel slice is to refuse that: op_common in op_array.c)
    path = os.path.join(acct_path("zznhon"), "bp", "zznsniff")
    g.put(path, "\n".join([
        "common /$netfile/ nf.opens, nf.requests, nf.lost, nf.s.state(10), nf.s.name(10), nf.s.obj(10), nf.h.state(100), nf.h.slot(100), nf.h.fno(100), "
        "nf.h.srv(100), nf.h.file(100), nf.h.acct(100)",
        "   crt 'SNIFF name=':nf.s.name(1):' vt=':vartype(nf.s.obj(1))", "end", ""]))
    try:
        cout = g.plain("zznhon", ["BASIC bp zznsniff"])
        compiled = g.has(cout, r"^Compiled 1 program\(s\) with no errors")
        s = Script()
        s.add("OPEN", "nfa", HFILE, ok=k_ok("1", 1))
        s.add("EXEC", "RUN bp zznsniff", ok=lambda c: c["rc"] == "")
        s.add("CLOSEALL", ok=k_ok("", 0))
        r = h_go("zznhon", s, (A,))
        seen = [ln for ln in r.out if ln.startswith("SNIFF ")]
        row("GAP (SECURITY): an ORDINARY program that names the common block /$netfile/ cannot get at the live connection of the handler (it either does not compile, or sees no object); "
            "today it sees the object (VARTYPE 15) and could call write, delete or execute on a logged-in remote connection, past every check of the handler and the read-only rule",
            not (compiled and any(ln.endswith("vt=15") for ln in seen)), repr((compiled, seen, cout[-3:])))
    finally:
        for d in ("bp", "bp.out"):
            p = os.path.join(acct_path("zznhon"), d, "zznsniff")
            if os.path.exists(p):
                os.remove(p)

    # slice 3c: the kernel starts a new epoch and sends NF$CLOSEALL at a LOGTO only if cproc calls the kernel key that is to reach net_close_all();
    # that key (K_NET_CLOSEALL, suggested 128) is not built, so a LOGTO leaves the connections where they were
    if kn_prep():
        r = kn_drive("zznhon", ["OPEN|1|zznet1", "READ|1|c1", "EXEC|LOGTO zznhunl", "EXEC|LOGTO zznhon", "READ|1|c1"], (A,))
        row("GAP: LOGTO ENDS THE CONNECTIONS (net_close_all, via a kernel key called beside kernel(K$NET, ...) in cproc): after LOGTO to another account and back to zznhon the variable opened "
            "before is STALE - the READ is an error (STATUS() 7000) and never reaches the fake (one READ in all); without the hook the handle is the same account's again and the READ is answered",
            kn_sane(r) and r.kr.count(kn_read_line("c1", "", "error", 7000)) == 1 and kn_wire(r.d[0]) == [(3, b"acct"), (4, b"hcust"), (6, FNO(1) + b"c1")], kn_why(r) + " wire=%r" % (kn_wire(r.d[0]),))


# ---- H7. the handler in WRITE mode (S.65 slice 3e, section hwrite) ---------------------------------------------------------------------------------
#
# The definitions nfw (on fake A) and nfwb (on fake B) say MODE WRITE; nfa and nfb, which every section above uses, say read and are the control.  The same driver zznfh
# calls $netfile with the new operations (WRITE, WRITEU, DELETE, DELETEU, CLEARFILE, LOCK, RELEASE; the prefix T makes the call INSIDE a transaction; <F> <V> <S> <I> in an
# id or a record are the marks).  THE FAKE IS THE WITNESS: its packet log says what was sent, byte for byte (W_WRITE and the others below write the layouts of apisrvr as
# numbers and struct.pack, from the spec, not from the class), and its store and lock table say what the requests did - RECORDLOCKED (request 34) asks it, in the middle of a
# session, whether this session holds a lock.  After every session the files are put back (wreset).  EXPECTED VALUES come from this file.
#
# WHAT IT CANNOT SHOW.  (1) That the KERNEL reaches the handler for these operations (kwrite).  (2) The 5 minute bound of a CLEARFILE (the 30 second one is the section
# timeout's).  (3) A reply cut in the middle (the handler counts LastError -1 as lost; the fake has no such fault).  (4) Anything on a real apisrvr: the fake is a model of it.

def W_WRITE(fno, rid, rec, keep=False):
    return (17 if keep else 16, FNO(fno) + struct.pack("<h", len(rid)) + rid.encode("latin-1") + rec.encode("latin-1"))


def W_DEL(fno, rid, keep=False):
    return (19 if keep else 18, FNO(fno) + rid.encode("latin-1"))


def W_CLEAR(fno):
    return (31, FNO(fno))


def W_LOCK(fno, rid, upd):
    return (30, FNO(fno) + struct.pack("<h", 3 if upd else 2) + rid.encode("latin-1"))        # flags: 1 update, 2 NO wait - the handler only ever asks without waiting


def W_REL(fno, rid=""):
    return (15, FNO(fno) + rid.encode("latin-1"))


def W_RLK(fno, rid):
    return (34, FNO(fno) + rid.encode("latin-1"))


# S.72 (20 Oct 26).  The handler's operations 18 (NF$FILELOCK) and 19 (NF$FILEUNLOCK) are driven by number (the RAW line of the driver), so that the driver compiles on a tree that does
# not define them yet.  Request 32 carries the file number and the wait flag (always 0: the handler never makes the server block), request 33 the file number only.
NF_FILELOCK, NF_FILEUNLOCK = 18, 19


def W_FLK(fno, wait=0):
    return (32, FNO(fno) + struct.pack("<h", wait))


def W_FUL(fno):
    return (33, FNO(fno))


def W_READ(fno, rid):
    return (6, FNO(fno) + rid.encode("latin-1"))


def W_OPEN(name):
    return (4, name.encode("latin-1"))


ACCT_REQ = (3, b"acct")
NEWREC_PH = "new<F>rec<V>x<S>y<I>z"                                 # typed with place holders: a terminal line is not trusted with the marks
NEWREC = "new" + FMC + "rec" + VMC + "x" + SMC + "y" + IMC + "z"
OPEN_W_AUD = "open server=nfw file=hwork mode=write"


def k_open_w(hx):
    """An OPEN of a write-mode handle: handle hx, rc<7> = 1."""
    return lambda c: k_ok(str(hx), len(str(hx)))(c) and c["r7"] == "1"


def k_open_r(hx):
    """An OPEN of a read-mode handle: handle hx and NO rc<7>."""
    return lambda c: k_ok(str(hx), len(str(hx)))(c) and c["r7"] == ""


def k_locked(holder):
    """rc 4: another user holds the record; rc<6> is its number; no message, no arguments, nothing in out."""
    return lambda c: c["rc"] == "4" and c["m"] == "" and c["st"] == str(holder) and c["args"] == ["", "", ""] and c["len"] == 0


def k_srverr(op, st, text=None, srv="nfw"):
    """The server answered with an error (11500 naming the server and the operation).  An ON ERROR reply WITHOUT a text shows 'status <n>' and rc<6> is n; one WITH a text
    (a refusal such as 11521, an abort, a server's edit gate) shows the text cut to 100 characters (19 Oct 26, K1: it showed 'status <n>' whatever the server said) and rc<6> is
    its status, 0 unless the row says otherwise."""
    def f(c):
        if not (c["rc"] == "3" and c["m"] == "11500" and c["args"][0] == srv and c["args"][1] == op and c["len"] == 0):
            return False
        if text is None:
            return c["args"][2] == "status %d" % st and c["st"] == str(st)
        return c["args"][2] == text[:100] and c["st"] == str(st)
    return f


def hw_go(acct, script, fakes=(), cfg=None, admin=False):
    """h_go, then what each fake's files held at the end (r.stores), then the files put back."""
    r = h_go(acct, script, fakes, cfg, admin)
    r.stores = [{n: f.store.records(n) for n in (HW, HWBP, HWVOC, HWNC)} for f in fakes]
    for f in fakes:
        wreset(f)
    return r


def hw_wires(r, expected):
    """Row text and verdict for a list of per-fake request lists: each fake's requests after the login equal the expected list."""
    return all(h_wire(d) == e for d, e in zip(r.d, expected))


def hw_first_diff(d, exp):
    got = h_wire(d)
    return next(((a, b) for a, b in zip(got, exp) if a != b), (len(got), len(exp)))


def hw_defs(mode):
    """The text of the definitions file with the mode of nfw (and only nfw) set to MODE."""
    out = []
    for ln in H["defs_text"].splitlines():
        f = ln.split("|")
        if f[0] == "nfw" and len(f) == 8:
            f[5] = mode
        out.append("|".join(f))
    return "\n".join(out) + "\n"


def hw_flip_files():
    """Prepare the two files the helper programs rename over the definitions: .h9a says nfw is read, .h9b says write (each is used up by its program)."""
    sdefs = os.path.join(g.SYS, "netservers")
    for suffix, mode in ((".h9a", "read"), (".h9b", "write")):
        with open(sdefs + suffix, "w", encoding="ascii") as f:
            f.write(hw_defs(mode))
        os.chmod(sdefs + suffix, 0o644)


def hw_restore_defs():
    sdefs = os.path.join(g.SYS, "netservers")
    with open(sdefs, "w", encoding="ascii") as f:
        f.write(H["defs_text"])
    os.chmod(sdefs, 0o644)
    for suffix in (".h9a", ".h9b"):
        try:
            os.remove(sdefs + suffix)
        except OSError:
            pass


def hw_prep():
    """The two helper programs that flip the mode of nfw in the definitions file (H9): zznfhm1 makes it read, zznfhm2 write again; each renames a prepared file over
    <sandbox>/sys/netservers.  Written by the suite, compiled by the administrator (they are $internal: OSRENAME is)."""
    if "hw_ready" in H:
        return H["hw_ready"]
    H["hw_ready"] = False
    if not h_prep():
        return False
    sdefs = os.path.join(g.SYS, "netservers")
    for n, suffix in ((1, ".h9a"), (2, ".h9b")):
        g.put(os.path.join(g.SYS, "bp", "zznfhm%d" % n), "\n".join([
            "$internal", "   src = '%s'" % (sdefs + suffix), "   dst = '%s'" % sdefs,
            "   if osrename(src, dst) then crt 'HFM %d renamed' else crt 'HFM %d FAILED'" % (n, n), "end", ""]))
    out = g.adm(["BASIC bp zznfhm1 zznfhm2"], internal=True)
    ok = g.has(out, r"^Compiled 2 program\(s\) with no errors") and not any(re.search(r"warning|not assigned", ln, re.I) for ln in out)
    row("SETUP: the two helper programs that flip the mode of nfw in the definitions file compile (administrator, $internal)", ok, repr(out[-6:]))
    H["hw_ready"] = ok
    return ok


def hwrite_section():
    say("\n--- $netfile in WRITE mode (slice 3e): the definition says write, and WRITE, WRITEU, DELETE, DELETEU, CLEARFILE, LOCK and RELEASE are sent to the fake - read mode is the control ---")
    if not hw_prep():
        return
    A, B = S["A"], S["B"]
    hw_open(A)
    hw_writes(A)
    hw_deletes(A)
    hw_locks(A, B)
    hw_filelocks(A)
    hw_ids(A)
    hw_mode(A)
    hw_txn(A)
    hw_lost(A)
    hw_errors(A)
    hw_misc(A)


def hw_open(A):
    say("\n  -- the open: the mode is told to the kernel (rc<7>) and audited; read mode is unchanged --")
    s = Script()
    s.add("OPEN", "nfw", HW, label="MODE WRITE: OPEN of nfw (the definition says write; a stored login, the gate, listed) is handle 1 with rc<7> = 1 - the mode, told to the kernel",
          ok=k_open_w(1), req=[ACCT_REQ, W_OPEN(HW)], audit=OPEN_W_AUD)
    s.add("OPEN", "nfa", HFILE, label="CONTROL: OPEN of nfa (mode read) is handle 2 with NO rc<7>, and its audit line is the line of slice 3b byte for byte (no ' mode=' in it)",
          ok=k_open_r(2), req=[ACCT_REQ, W_OPEN(HFILE)], audit="open server=nfa file=hcust")
    s.add("OPEN", "NFW", "DICT HWORK", label="the dictionary of a write-mode file opens in write mode too (handle 3, the name in lower case on the wire, the same connection)",
          ok=k_open_w(3), req=[W_OPEN("dict hwork")], audit="open server=nfw file=dict hwork mode=write")
    s.add("CLOSEALL", ok=k_ok("", 0), req=[(1, b""), (1, b"")])
    r = hw_go("zznhon", s, (A,))
    row("the open program ran to the end and no connection is left", h_sane(r), h_why(r))
    judge(r, s)
    row("...the requests were those listed (two connections: nfw and nfa), and the audit trail has exactly the three open lines in order", a_wire(r, s) and r.audits == s.audits(),
        repr((hw_first_diff(r.d[0], s.wire()), r.audits)))


def hw_writes(A):
    say("\n  -- WRITE and WRITEU: the exact bytes, the record on the fake, the lock the server lets go of or keeps --")
    s = Script()
    s.add("OPEN", "nfw", HW, ok=k_open_w(1), req=[ACCT_REQ, W_OPEN(HW)], audit=OPEN_W_AUD)
    s.add("LOCK", 1, "w1", "u", ok=k_ok("", 0), req=[W_LOCK(1, "w1", True)])
    s.add("RLOCKED", 1, "w1", label="(setup) the fake holds an UPDATE lock for this session on w1: RECORDLOCKED is 2", ok=k_ok("2", 1), req=[W_RLK(1, "w1")])
    s.add("WRITE", 1, "w1", NEWREC_PH, label="WRITE: rc 0, no message, nothing in out - and the request is request 16 with the file number, the id length, the id and the record WITH ITS FOUR MARKS "
          "(a record is any bytes)", ok=k_ok("", 0), req=[W_WRITE(1, "w1", NEWREC)], audit="write server=nfw file=hwork")
    s.add("RLOCKED", 1, "w1", label="...a plain WRITE let go of the lock the session held: RECORDLOCKED 0", ok=k_ok("0", 1), req=[W_RLK(1, "w1")])
    s.add("LOCK", 1, "w2", "u", ok=k_ok("", 0), req=[W_LOCK(1, "w2", True)])
    s.add("WRITEU", 1, "w2", "kept", label="WRITEU: rc 0, request 17", ok=k_ok("", 0), req=[W_WRITE(1, "w2", "kept", True)])
    s.add("RLOCKED", 1, "w2", label="...WRITEU KEPT the lock: RECORDLOCKED 2", ok=k_ok("2", 1), req=[W_RLK(1, "w2")])
    s.add("WRITE", 1, "wnew", "created", label="WRITE of an id the file does not hold creates the record", ok=k_ok("", 0), req=[W_WRITE(1, "wnew", "created")])
    s.add("WRITE", 1, "w3", "", label="WRITE of a null record: the request ends after the id (no record bytes), the record becomes null", ok=k_ok("", 0), req=[W_WRITE(1, "w3", "")])
    s.add("WRITE", 1, "a" * 63, "edge", label="an id of exactly 63 bytes is accepted (the server's limit)", ok=k_ok("", 0), req=[W_WRITE(1, "a" * 63, "edge")])
    n_req = s.nreq()
    s.add("STATE", label="STATE: 1 server, 1 file, 1 opened, %d requests - the handler's own count equals what the fake received - none dropped or lost; the connection is still an object" % n_req,
          ok=k_state(1, 1, 1, n_req, 0, 0, conns=[("nfw", 15, 1)]))
    s.add("CLOSEALL", ok=k_ok("", 0), req=[(1, b"")])
    r = hw_go("zznhon", s, (A,))
    row("the write program ran to the end and no connection is left", h_sane(r), h_why(r))
    judge(r, s)
    d = r.d[0]
    row("...THE REQUESTS, in order, with their bytes: ACCOUNT, OPEN, then LOCK (30, flags 3), RECORDLOCKED, WRITE (16), RECORDLOCKED, LOCK, WRITEU (17), RECORDLOCKED, three WRITEs, Quit",
        a_wire(r, s), "first difference: %r" % (hw_first_diff(d, s.wire()),))
    exp = dict(HWREC)
    exp.update({"w1": NEWREC, "w2": "kept", "w3": "", "wnew": "created", "a" * 63: "edge"})
    row("...THE FILE ON THE FAKE holds exactly what was written: w1 with its marks, w2 'kept', w3 null, wnew 'created', the 63 byte id - and nothing else changed", r.stores[0][HW] == exp,
        repr({k: v for k, v in r.stores[0][HW].items() if exp.get(k) != v}))
    row("...the audit trail has the open line and ONE 'netfile write server=nfw file=hwork' line (the first WRITE through the handle; WRITEU and the other writes add none), no id and no record in it, "
        "and nothing secret", r.audits == s.audits() and secret_free(r.audit), repr(r.audits))
    row("...the other files of the fake are as they were", all(r.stores[0][n] == dict(rec) for n, rec, _p, _c in HWFILES if n != HW), "")


def hw_deletes(A):
    say("\n  -- DELETE, DELETEU and CLEARFILE --")
    s = Script()
    s.add("OPEN", "nfw", HW, ok=k_open_w(1), req=[ACCT_REQ, W_OPEN(HW)], audit=OPEN_W_AUD)
    s.add("LOCK", 1, "w1", "u", ok=k_ok("", 0), req=[W_LOCK(1, "w1", True)])
    s.add("DELETE", 1, "w1", label="DELETE: rc 0, request 18 with the file number and the id", ok=k_ok("", 0), req=[W_DEL(1, "w1")], audit="delete server=nfw file=hwork")
    s.add("RLOCKED", 1, "w1", label="...a plain DELETE let go of the lock: RECORDLOCKED 0", ok=k_ok("0", 1), req=[W_RLK(1, "w1")])
    s.add("LOCK", 1, "w2", "u", ok=k_ok("", 0), req=[W_LOCK(1, "w2", True)])
    s.add("DELETEU", 1, "w2", label="DELETEU: rc 0, request 19", ok=k_ok("", 0), req=[W_DEL(1, "w2", True)])
    s.add("RLOCKED", 1, "w2", label="...DELETEU KEPT the lock: RECORDLOCKED 2", ok=k_ok("2", 1), req=[W_RLK(1, "w2")])
    s.add("DELETE", 1, "nosuch", label="DELETE of a record that is not there is a SUCCESS (rc 0): the request is still sent", ok=k_ok("", 0), req=[W_DEL(1, "nosuch")])
    s.add("CLEARFILE", 1, label="CLEARFILE: rc 0, request 31 with the file number only", ok=k_ok("", 0), req=[W_CLEAR(1)], audit="clear server=nfw file=hwork")
    s.add("READ", 1, "w3", label="...and the connection is still served after it (the 30 second bound was put back): READ of w3 is the ELSE branch, the file is empty", ok=k_else(3006),
          req=[W_READ(1, "w3")])
    s.add("CLEARFILE", 1, label="CLEARFILE again: audited again (every CLEARFILE is)", ok=k_ok("", 0), req=[W_CLEAR(1)], audit="clear server=nfw file=hwork")
    s.add("CLOSEALL", ok=k_ok("", 0), req=[(1, b"")])
    r = hw_go("zznhon", s, (A,))
    row("the delete program ran to the end and no connection is left", h_sane(r), h_why(r))
    judge(r, s)
    row("...THE REQUESTS, in order, with their bytes", a_wire(r, s), "first difference: %r" % (hw_first_diff(r.d[0], s.wire()),))
    row("...THE FILE ON THE FAKE is empty, and the other files are as they were", r.stores[0][HW] == {} and all(r.stores[0][n] == dict(rec) for n, rec, _p, _c in HWFILES if n != HW), repr(r.stores[0][HW]))
    row("...the audit trail: the open line, ONE 'delete' line (DELETE and DELETEU share it), TWO 'clear' lines, in order - no id", r.audits == s.audits(), repr(r.audits))


def hw_locks(A, B):
    say("\n  -- LOCK (the no-wait form only), the busy answer, RELEASE in its three forms --")
    A.store.hold(HW, "w2", 7, "update")
    A.store.hold(HW, "w3", 8, "shared")
    s = Script()
    s.add("OPEN", "nfw", HW, ok=k_open_w(1), req=[ACCT_REQ, W_OPEN(HW)], audit=OPEN_W_AUD)
    s.add("LOCK", 1, "w1", "l", label="LOCK l of a free record: rc 0, request 30 with flags 2 (shared, NO WAIT)", ok=k_ok("", 0), req=[W_LOCK(1, "w1", False)])
    s.add("LOCK", 1, "w1", "u", label="...LOCK u by the same session raises it: rc 0, flags 3 (update, no wait)", ok=k_ok("", 0), req=[W_LOCK(1, "w1", True)])
    s.add("LOCK", 1, "w2", "u", label="LOCK u of a record another user (7) holds an update lock on: rc 4 (not an error), rc<6> the holder's number, no message", ok=k_locked(7), req=[W_LOCK(1, "w2", True)])
    s.add("LOCK", 1, "w2", "l", label="...LOCK l of it is busy too: holder 7", ok=k_locked(7), req=[W_LOCK(1, "w2", False)])
    s.add("LOCK", 1, "w3", "l", label="LOCK l of a record another user holds a READ lock on is granted (shared with shared): rc 0", ok=k_ok("", 0), req=[W_LOCK(1, "w3", False)])
    s.add("LOCK", 1, "w3", "u", label="...LOCK u of it is busy: holder 8", ok=k_locked(8), req=[W_LOCK(1, "w3", True)])
    s.add("LOCK", 1, "w1", "x", label="a lock kind that is not l or u (x) is 11512 naming the server and the kind; NOTHING is sent", ok=k_err(11512, "nfw", "x"))
    s.add("LOCK", 1, "w1", "uu", label="...'uu' is 11512 too", ok=k_err(11512, "nfw", "uu"))
    s.add("LOCK", 1, "w1", "", label="...and so is a null kind", ok=k_err(11512, "nfw", ""))
    s.add("LOCK", 1, "w1", "U", label="...and an upper case U (the kinds are exactly one lower case letter)", ok=k_err(11512, "nfw", "U"))
    s.add("CLOSEALL", ok=k_ok("", 0), req=[(1, b"")])
    r = hw_go("zznhon", s, (A,))
    row("the lock program ran to the end and no connection is left", h_sane(r), h_why(r))
    judge(r, s)
    row("...THE REQUESTS, in order: every lock is request 30 with flags 2 or 3 - never 0 or 1, which WAIT on the server - and the four bad kinds sent nothing", a_wire(r, s),
        "first difference: %r" % (hw_first_diff(r.d[0], s.wire()),))
    row("...the file on the fake is as it was (a lock changes nothing)", r.stores[0][HW] == dict(HWREC), "")

    # RELEASE: record form, file form, and 0 = every lock of the session on every connected server
    s = Script()
    s.add("OPEN", "nfw", HW, ok=k_open_w(1), audit=OPEN_W_AUD)
    s.add("OPEN", "nfwb", HW, ok=k_open_w(2), audit="open server=nfwb file=hwork mode=write")
    s.add("LOCK", 1, "w1", "u", ok=k_ok("", 0))
    s.add("LOCK", 1, "w2", "u", ok=k_ok("", 0))
    s.add("LOCK", 2, "w1", "u", ok=k_ok("", 0))
    s.add("RELEASE", 1, "w1", label="RELEASE (record form): rc 0", ok=k_ok("", 0))
    s.add("RLOCKED", 1, "w1", label="...the lock on w1 is gone (0)", ok=k_ok("0", 1))
    s.add("RLOCKED", 1, "w2", label="...the lock on w2 is still held (2)", ok=k_ok("2", 1))
    s.add("RELEASE", 1, label="RELEASE (file form, no id): rc 0", ok=k_ok("", 0))
    s.add("RLOCKED", 1, "w2", label="...every lock on the file is gone", ok=k_ok("0", 1))
    s.add("LOCK", 1, "w1", "u", ok=k_ok("", 0))
    s.add("LOCK", 2, "w3", "u", ok=k_ok("", 0))
    s.add("RELEASE", 0, label="RELEASE with the handle 0 (RELEASE alone): rc 0 - the request goes to EVERY connection that has a write-mode handle open", ok=k_ok("", 0))
    s.add("RLOCKED", 1, "w1", label="...server A holds nothing for the session now", ok=k_ok("0", 1))
    s.add("RLOCKED", 2, "w1", label="...server B: w1 is free", ok=k_ok("0", 1))
    s.add("RLOCKED", 2, "w3", label="...server B: w3 is free", ok=k_ok("0", 1))
    s.add("RELEASE", 99, label="RELEASE on a handle that is not open is the ordinary 11494 (rc 3), nothing sent", ok=k_err(11494, 99))
    s.add("CLOSEALL", ok=k_ok("", 0))
    r = hw_go("zznhon", s, (A, B))
    row("the release program ran to the end and no connection is left", h_sane(r), h_why(r))
    judge(r, s)
    expA = [ACCT_REQ, W_OPEN(HW), W_LOCK(1, "w1", True), W_LOCK(1, "w2", True), W_REL(1, "w1"), W_RLK(1, "w1"), W_RLK(1, "w2"), W_REL(1), W_RLK(1, "w2"), W_LOCK(1, "w1", True), W_REL(0),
            W_RLK(1, "w1"), (1, b"")]
    expB = [ACCT_REQ, W_OPEN(HW), W_LOCK(1, "w1", True), W_LOCK(1, "w3", True), W_REL(0), W_RLK(1, "w1"), W_RLK(1, "w3"), (1, b"")]
    row("...THE REQUESTS on each server: the record form carries file number and id (15), the file form the file number only, the 0 form file number 0 and no id (15) - on BOTH servers",
        hw_wires(r, [expA, expB]), "A %r / B %r" % (hw_first_diff(r.d[0], expA), hw_first_diff(r.d[1], expB)))


def k_rlk(code, owner=None):
    """RECORDLOCKED through the handler (S.72): out is the code, no message, no rc<6>; rc<8> is the server's STATUS(), the owner's user number: OWNER when it is given, 0 when the code is 0,
    and for a lock of this session (codes 1 to 3) any whole number above 0 (the fake numbers its connections itself)."""
    def f(c):
        if not (c["rc"] == "0" and c["m"] == "" and c["st"] == "" and c["args"] == ["", "", ""] and c["out"] == str(code) and c["len"] == len(str(code))):
            return False
        if owner is not None:
            return c["r8"] == str(owner)
        if code == 0:
            return c["r8"] == "0"
        return re.fullmatch(r"[1-9][0-9]*", c["r8"]) is not None
    return f


def k_unlocked(status):
    """FILEUNLOCK through the handler: rc 0, nothing in out, rc<8> the server's reply STATUS(): 0 it was ours and is free, 3011 another user's (left held), 3012 nobody's."""
    return lambda c: c["rc"] == "0" and c["m"] == "" and c["st"] == "" and c["args"] == ["", "", ""] and c["len"] == 0 and c["r8"] == str(status)


def hw_filelocks(A):
    say("\n  -- FILELOCK and FILEUNLOCK (S.72): operations 18 and 19, the no-wait form only; RECORDLOCKED on a read-mode and a write-mode handle --")
    s = Script()
    s.add("OPEN", "nfw", HW, ok=k_open_w(1), req=[ACCT_REQ, W_OPEN(HW)], audit=OPEN_W_AUD)
    s.add("RAW", NF_FILELOCK, 1, label="FILELOCK of a free file: rc 0, request 32 with the file number and the wait flag 0 (NO WAIT - the handler never makes the server block)", ok=k_ok("", 0),
          req=[W_FLK(1)], audit="filelock server=nfw file=hwork")
    s.add("RAW", NF_FILELOCK, 1, label="...a second FILELOCK of the same handle is rc 0 (already ours), request 32 again, and NO second audit line (one for each handle)", ok=k_ok("", 0), req=[W_FLK(1)])
    s.add("RLOCKED", 1, "w1", label="...RECORDLOCKED of any record now says 3 (this session holds the file lock) and rc<8> is a user number", ok=k_rlk(3), req=[W_RLK(1, "w1")])
    s.add("RAW", NF_FILEUNLOCK, 1, label="FILEUNLOCK of the lock this session holds: rc 0, nothing in out, rc<8> = 0, request 33 with the file number only", ok=k_unlocked(0), req=[W_FUL(1)])
    s.add("RLOCKED", 1, "w1", label="...RECORDLOCKED says 0 and rc<8> is 0", ok=k_rlk(0), req=[W_RLK(1, "w1")])
    s.add("RAW", NF_FILEUNLOCK, 1, label="FILEUNLOCK when nobody holds the lock: rc 0 (not an error), rc<8> = 3012 (ER$NLK)", ok=k_unlocked(3012), req=[W_FUL(1)])
    s.add("CLOSEALL", ok=k_ok("", 0), req=[(1, b"")])
    r = hw_go("zznhon", s, (A,))
    row("the file lock program ran to the end and no connection is left", h_sane(r), h_why(r))
    judge(r, s)
    row("...THE REQUESTS, in order, with their bytes: 32 (file, wait 0) twice, 34, 33, 34, 33 - never a request 32 with the wait flag set", a_wire(r, s), "first difference: %r" % (hw_first_diff(r.d[0], s.wire()),))
    row("...the audit trail: the open line and ONE 'filelock' line (written before the first request, once for the handle), no id and no record data", r.audits == s.audits(), repr(r.audits))
    row("...the file is as it was (a lock changes nothing)", r.stores[0][HW] == dict(HWREC), repr(r.stores[0][HW]))

    # another user holds the file lock / a record lock in the file
    A.store.hold_file(HW, 7)
    s = Script()
    s.add("OPEN", "nfw", HW, ok=k_open_w(1), req=[ACCT_REQ, W_OPEN(HW)], audit=OPEN_W_AUD)
    s.add("RAW", NF_FILELOCK, 1, label="FILELOCK when user 7 holds the file lock: rc 4 (NF$RC.LOCKED, not an error), rc<6> the holder's number (7), no message", ok=k_locked(7), req=[W_FLK(1)],
          audit="filelock server=nfw file=hwork")
    s.add("RLOCKED", 1, "w1", label="...RECORDLOCKED says -3 (another user holds the file lock) and rc<8> is 7", ok=k_rlk(-3, 7), req=[W_RLK(1, "w1")])
    s.add("RAW", NF_FILEUNLOCK, 1, label="...FILEUNLOCK is rc 0 with rc<8> = 3011 (ER$LCK: the lock is another user's) - it is sent, it is the server that knows - and the lock stays", ok=k_unlocked(3011),
          req=[W_FUL(1)])
    s.add("RLOCKED", 1, "w1", label="...RECORDLOCKED still says -3", ok=k_rlk(-3, 7), req=[W_RLK(1, "w1")])
    s.add("CLOSEALL", ok=k_ok("", 0), req=[(1, b"")])
    try:
        r = hw_go("zznhon", s, (A,))
    finally:
        A.store.drop_user(7)
    row("the busy-file program ran to the end and no connection is left", h_sane(r), h_why(r))
    judge(r, s)
    row("...THE FAKE: the requests as listed, and the audit trail has the open and the filelock line (that user 7 still held the lock after the FILEUNLOCK is the last RECORDLOCKED: -3)",
        a_wire(r, s) and r.audits == s.audits(), repr((hw_first_diff(r.d[0], s.wire()), r.audits)))
    A.store.hold(HW, "w2", 8, "update")
    s = Script()
    s.add("OPEN", "nfw", HW, ok=k_open_w(1), req=[ACCT_REQ, W_OPEN(HW)], audit=OPEN_W_AUD)
    s.add("RAW", NF_FILELOCK, 1, label="FILELOCK when user 8 holds an update lock on a record of the file: rc 4 with rc<6> 8", ok=k_locked(8), req=[W_FLK(1)], audit="filelock server=nfw file=hwork")
    s.add("CLOSEALL", ok=k_ok("", 0), req=[(1, b"")])
    try:
        r = hw_go("zznhon", s, (A,))
    finally:
        A.store.drop_user(8)
    row("the record-lock program ran to the end and no connection is left", h_sane(r), h_why(r))
    judge(r, s)

    # RECORDLOCKED: another user's record locks, a READ-mode handle, a bad id
    A.store.hold(HW, "w2", 7, "update")
    A.store.hold(HW, "w3", 8, "shared")
    s = Script()
    s.add("OPEN", "nfw", HW, ok=k_open_w(1), req=[ACCT_REQ, W_OPEN(HW)], audit=OPEN_W_AUD)
    s.add("OPEN", "nfa", HFILE, ok=k_open_r(2), req=[ACCT_REQ, W_OPEN(HFILE)], audit="open server=nfa file=hcust")
    s.add("RLOCKED", 1, "w2", label="RECORDLOCKED of a record another user (7) holds an update lock on: out -2, rc<8> 7", ok=k_rlk(-2, 7), req=[W_RLK(1, "w2")])
    s.add("RLOCKED", 1, "w3", label="...a read lock of user 8: out -1, rc<8> 8", ok=k_rlk(-1, 8), req=[W_RLK(1, "w3")])
    s.add("RLOCKED", 1, "w1", label="...a record nobody holds: out 0, rc<8> 0", ok=k_rlk(0), req=[W_RLK(1, "w1")])
    s.add("RLOCKED", 2, "c1", label="[S72b-N3] A READ-MODE handle (nfa): RECORDLOCKED is REFUSED by the handler (S.72b; it was served): rc 3, message 11501 naming the server (nfa) and 'recordlocked', nothing in out - "
          "and NOTHING IS SENT", ok=k_err(11501, "nfa", "recordlocked"))
    s.add("RLOCKED", 1, "", label="an empty id is the ELSE branch with the remote status 3000, as for a READ - nothing is sent", ok=k_else(3000))
    s.add("RLOCKED", 1, "x" * 64, label="an id of 64 bytes is 11503 'too long' - nothing is sent", ok=k_err(11503, "nfw", "too long"))
    s.add("CLOSEALL", ok=k_ok("", 0), req=[(1, b""), (1, b"")])
    try:
        r = hw_go("zznhon", s, (A,))
    finally:
        A.store.drop_user(7)
        A.store.drop_user(8)
    row("the RECORDLOCKED program ran to the end and no connection is left", h_sane(r), h_why(r))
    judge(r, s)
    row("...THE REQUESTS: 34 for the three good ones of the write-mode handle (file number and id), none for the read-mode handle, the empty and the long id", a_wire(r, s),
        "first difference: %r" % (hw_first_diff(r.d[0], s.wire()),))
    cn = by_conn(r.d[0])
    row("...[S72b-N3] and PER CONNECTION: the write-mode connection (nfw, the first) carried three requests 34 (so the null case - a handle that is asked - is there), the read-mode connection (nfa, the "
        "second) carried none: it sent the account, the open and the quit only", len(cn) == 2 and cn[0].count(34) == 3 and 34 not in cn[1] and cn[1][-3:] == [3, 4, 1], repr(cn))

    # S.72b: the same refusal when the file DOES have a lock on that record - a handler that asked the server would be told -2 with user 7's number; the row above answers 0 either way
    A.store.hold(HFILE, "c1", 7, "update")
    s = Script()
    s.add("OPEN", "nfa", HFILE, ok=k_open_r(1), req=[ACCT_REQ, W_OPEN(HFILE)], audit="open server=nfa file=hcust")
    s.add("RLOCKED", 1, "c1", label="[S72b-N4] A READ-MODE handle and a record user 7 holds an UPDATE lock on (a request would have answered -2 with user 7): REFUSED with 11501 naming 'nfa' and 'recordlocked' - "
          "the answer is the refusal and not -2 - and nothing is sent", ok=k_err(11501, "nfa", "recordlocked"))
    s.add("READ", 1, "c1", label="...the read-mode handle is still good for a READ afterwards (the refusal did not drop the handle or the connection)", ok=k_rec(RECS["c1"]), req=[W_READ(1, "c1")])
    s.add("CLOSEALL", ok=k_ok("", 0), req=[(1, b"")])
    try:
        r = hw_go("zznhon", s, (A,))
    finally:
        A.store.drop_user(7)
    row("the read-mode RECORDLOCKED program ran to the end and no connection is left", h_sane(r), h_why(r))
    judge(r, s)
    row("...THE FAKE SAW the open, the READ and the quit - and in its packet log no request 34 at all (types %r)" % (r.d[0]["types"],), a_wire(r, s) and 34 not in r.d[0]["types"] and 6 in r.d[0]["types"],
        repr((hw_first_diff(r.d[0], s.wire()), r.d[0]["types"])))

    # a read-mode handle: both lock statements are refused with 11501 and nothing is sent (the read-mode control)
    s = Script()
    s.add("OPEN", "nfa", HFILE, ok=k_open_r(1), req=[ACCT_REQ, W_OPEN(HFILE)], audit="open server=nfa file=hcust")
    s.add("RAW", NF_FILELOCK, 1, label="A READ-MODE handle: FILELOCK is refused with 11501 naming the server and 'filelock'; nothing is sent, nothing is audited", ok=k_err(11501, "nfa", "filelock"))
    s.add("RAW", NF_FILEUNLOCK, 1, label="...FILEUNLOCK is refused too (fileunlock): a read-mode handle can hold no file lock", ok=k_err(11501, "nfa", "fileunlock"))
    s.add("CLOSEALL", ok=k_ok("", 0), req=[(1, b"")])
    r = hw_go("zznhon", s, (A,))
    row("the read-mode program ran to the end and no connection is left", h_sane(r), h_why(r))
    judge(r, s)
    row("...THE FAKE SAW only the open and the quit, and the audit trail has the open line only", a_wire(r, s) and r.audits == s.audits(), repr((hw_first_diff(r.d[0], s.wire()), r.audits)))

    # inside a transaction: refused, nothing sent
    s = Script()
    s.add("OPEN", "nfw", HW, ok=k_open_w(1), req=[ACCT_REQ, W_OPEN(HW)], audit=OPEN_W_AUD)
    s.add("TRAW", NF_FILELOCK, 1, label="INSIDE A TRANSACTION: FILELOCK is refused with 11510 naming the server and 'filelock'; nothing is sent", ok=k_err(11510, "nfw", "filelock"))
    s.add("TRAW", NF_FILEUNLOCK, 1, label="...FILEUNLOCK too (fileunlock)", ok=k_err(11510, "nfw", "fileunlock"))
    s.add("TRLOCKED", 1, "w1", label="...RECORDLOCKED is served in the same transaction (it changes nothing)", ok=k_rlk(0), req=[W_RLK(1, "w1")])
    s.add("CLOSEALL", ok=k_ok("", 0), req=[(1, b"")])
    r = hw_go("zznhon", s, (A,))
    row("the transaction program ran to the end and no connection is left", h_sane(r), h_why(r))
    judge(r, s)
    row("...THE FAKE SAW only the open, the RECORDLOCKED and the quit, and no 'filelock' audit line was written", a_wire(r, s) and r.audits == s.audits(), repr((hw_first_diff(r.d[0], s.wire()), r.audits)))

    # the mode read again: FILELOCK stops, FILEUNLOCK does not (giving a lock back changes no data - and RELEASE is the same)
    hw_flip_files()
    s = Script()
    s.add("OPEN", "nfw", HW, ok=k_open_w(1), req=[ACCT_REQ, W_OPEN(HW)], audit=OPEN_W_AUD)
    s.add("RAW", NF_FILELOCK, 1, label="(setup) FILELOCK while the definition says write: rc 0", ok=k_ok("", 0), req=[W_FLK(1)], audit="filelock server=nfw file=hwork")
    s.add("EXEC", "RUN bp zznfhm1", label="(the administrator's helper makes nfw MODE READ in the definitions file)", ok=lambda c: c["rc"] == "")
    s.add("RAW", NF_FILELOCK, 1, label="THE MODE IS READ AGAIN: FILELOCK on the open handle is refused with 11501 naming the server and 'filelock'; nothing is sent",
          ok=k_err(11501, "nfw", "filelock"), audit="refused server=nfw reason=mode")
    s.add("RLOCKED", 1, "w1", label="[S72b-N5] ...RECORDLOCKED is NOT refused for the mode either: the handle was opened in write mode and the handler does not read the definition again for it (like FILEUNLOCK) - "
          "request 34 is sent and answers 3, the file lock the session still holds (a served answer that is not 0: the null case)", ok=k_rlk(3), req=[W_RLK(1, "w1")])
    s.add("RAW", NF_FILEUNLOCK, 1, label="...FILEUNLOCK is NOT refused for the mode (it changes no data and gives the lock back): rc 0, request 33 is sent, rc<8> 0", ok=k_unlocked(0), req=[W_FUL(1)])
    s.add("EXEC", "RUN bp zznfhm2", label="(the helper makes nfw MODE WRITE again)", ok=lambda c: c["rc"] == "")
    s.add("CLOSEALL", ok=k_ok("", 0), req=[(1, b"")])
    try:
        r = hw_go(None, s, (A,), admin=True)
    finally:
        hw_restore_defs()
    row("the mode-flip program ran to the end and no connection is left", h_sane(r), h_why(r))
    judge(r, s)
    row("...THE FAKE SAW the first FILELOCK, the RECORDLOCKED and the FILEUNLOCK only, and the audit trail has the open, ONE 'filelock' line and ONE 'refused ... reason=mode' line (RECORDLOCKED adds none)",
        a_wire(r, s) and r.audits == s.audits(), repr((hw_first_diff(r.d[0], s.wire()), r.audits)))

    # a lock that is asked for through a handle whose id or lock table the fake has lost: the connection dropped
    lost_cases =(("FILELOCK", "drop_after", 32, ("RAW", NF_FILELOCK, 1, ""), "filelock"), ("FILEUNLOCK", "drop_after", 33, ("RAW", NF_FILEUNLOCK, 1, ""), "fileunlock"))
    for what, kind, req_type, stmt, op in lost_cases:
        s = Script()
        s.add("OPEN", "nfw", HW, ok=k_open_w(1))
        s.add(*stmt, label="%s whose connection is lost after the server did it: 11497 naming the server and '%s' (a lock changes no data: the message of a read, not 11509)" % (what, op),
              ok=k_err(11497, "nfw", op))
        s.add("RAW", NF_FILELOCK, 1, label="...a second call on the lost handle is 11495: THE REQUEST IS NEVER SENT AGAIN", ok=k_err(11495, "nfw", 1))
        s.add("OPEN", "nfw", HW, label="...a new OPEN dials again (handle 2)", ok=k_open_w(2))
        s.add("RLOCKED", 2, "w1", label="...whatever the first connection held went with it: RECORDLOCKED through the new connection says 0 (the file lock of a FILELOCK that was done and lost is gone)", ok=k_rlk(0))
        s.add("CLOSE", 1, ok=k_ok("", 0))
        s.add("CLOSEALL", ok=k_ok("", 0))
        r = hw_go("zznhon", s, (A,), cfg={kind: {req_type: 1}})
        row("%s lost: the program ran to the end and no connection is left" % what, r.began and r.ended and len(r.calls) == r.n and r.idle and all(not d["errors"] for d in r.d), h_why(r))
        judge(r, s)
        ses = r.d[0]["sessions"]
        row("...the fake saw TWO connections and request type %d exactly ONCE (never retried)" % req_type,
            len(ses) == 2 and sum(x.requests.count(req_type) for x in ses) == 1, repr([x.requests for x in ses]))
        aud = [OPEN_W_AUD] + (["filelock server=nfw file=hwork"] if what == "FILELOCK" else []) + [OPEN_W_AUD]
        row("...the audit trail: the opens%s and NO 'lost' line (a lock changes no data: message 11497, not 11509)" % (", the 'filelock' line" if what == "FILELOCK" else ""), r.audits == aud, repr(r.audits))


def hw_ids(A):
    say("\n  -- a record id that is not valid is refused BEFORE anything is sent --")
    s = Script()
    s.add("OPEN", "nfw", HW, ok=k_open_w(1), req=[ACCT_REQ, W_OPEN(HW)], audit=OPEN_W_AUD)
    for nm, extra in (("WRITE", "x"), ("WRITEU", "x"), ("DELETE", ""), ("DELETEU", ""), ("LOCK", "u")):
        s.add(nm, 1, "", extra, label="%s with an EMPTY id is an error 11503 'empty' - not the ELSE branch (a write has none)" % nm, ok=k_err(11503, "nfw", "empty"))
    for nm, extra in (("WRITE", "x"), ("DELETE", ""), ("LOCK", "u")):
        s.add(nm, 1, "x" * 64, extra, label="%s with an id of 64 bytes is 11503 'too long'" % nm, ok=k_err(11503, "nfw", "too long"))
    for nm, extra in (("WRITE", "x"), ("DELETEU", ""), ("LOCK", "l")):
        s.add(nm, 1, "a<F>b", extra, label="%s with a mark in the id is 11503 'holds a mark'" % nm, ok=k_err(11503, "nfw", "holds a mark"))
    s.add("CLOSEALL", ok=k_ok("", 0), req=[(1, b"")])
    r = hw_go("zznhon", s, (A,))
    row("the bad-id program ran to the end and no connection is left", h_sane(r), h_why(r))
    judge(r, s)
    row("...THE FAKE SAW only ACCOUNT, OPEN and the Quit: not one request for a refused id", a_wire(r, s), repr(h_wire(r.d[0])))
    row("...and the file on the fake is as it was, and the audit trail has no 'write' or 'delete' line (a refused call is not audited as a change)", r.stores[0][HW] == dict(HWREC) and r.audits == s.audits(),
        repr(r.audits))


def hw_mode(A):
    say("\n  -- the mode is read AGAIN at every change: a server set back to read stops a handle that is open (the definitions file is rewritten by the administrator in the session) --")
    hw_flip_files()
    s = Script()
    s.add("OPEN", "nfw", HW, ok=k_open_w(1), req=[ACCT_REQ, W_OPEN(HW)], audit=OPEN_W_AUD)
    s.add("WRITE", 1, "w1", "first", label="(setup) WRITE while the definition says write: rc 0", ok=k_ok("", 0), req=[W_WRITE(1, "w1", "first")], audit="write server=nfw file=hwork")
    s.add("EXEC", "RUN bp zznfhm1", label="(the administrator's helper makes nfw MODE READ in the definitions file)", ok=lambda c: c["rc"] == "")
    s.add("WRITE", 1, "w1", "second", label="THE MODE IS READ AGAIN: WRITE on the open handle is refused with 11501 (the read-mode text) naming the server and the operation; NOTHING is sent",
          ok=k_err(11501, "nfw", "write"), audit="refused server=nfw reason=mode")
    s.add("WRITE", 1, "w1", "third", label="...the refusal is repeated, and the audit line 'refused ... reason=mode' is written ONCE for the handle", ok=k_err(11501, "nfw", "write"))
    s.add("DELETE", 1, "w1", label="...DELETE, CLEARFILE and LOCK are refused the same way (delete, clear.file, lock)", ok=k_err(11501, "nfw", "delete"))
    s.add("CLEARFILE", 1, ok=k_err(11501, "nfw", "clear.file"))
    s.add("LOCK", 1, "w1", "u", ok=k_err(11501, "nfw", "lock"))
    s.add("READ", 1, "w1", label="...a READ is not affected by the mode: it is served and shows the record the first WRITE made", ok=k_rec("first"), req=[W_READ(1, "w1")])
    s.add("RELEASE", 1, "w1", label="...and RELEASE is never refused for the mode (it changes no data): rc 0, the request is sent", ok=k_ok("", 0), req=[W_REL(1, "w1")])
    s.add("EXEC", "RUN bp zznfhm2", label="(the helper makes nfw MODE WRITE again)", ok=lambda c: c["rc"] == "")
    s.add("WRITE", 1, "w1", "fourth", label="set back to write, the same handle writes again: rc 0", ok=k_ok("", 0), req=[W_WRITE(1, "w1", "fourth")])
    s.add("CLOSEALL", ok=k_ok("", 0), req=[(1, b"")])
    try:
        r = hw_go(None, s, (A,), admin=True)
    finally:
        hw_restore_defs()
    row("the mode-flip program ran to the end and no connection is left", h_sane(r), h_why(r))
    row("...both helper programs renamed their file (the definitions changed twice)", g.has(r.out, r"^HFM 1 renamed$") and g.has(r.out, r"^HFM 2 renamed$"), repr([ln for ln in r.out if ln.startswith("HFM")]))
    judge(r, s)
    row("...THE FAKE SAW ONLY the two good WRITEs (16), the READ and the RELEASE - not the three refused changes", a_wire(r, s), "first difference: %r" % (hw_first_diff(r.d[0], s.wire()),))
    row("...the audit trail: the open line, one 'write' line, ONE 'refused ... reason=mode' line", r.audits == s.audits(), repr(r.audits))
    row("...the file holds the last good write", r.stores[0][HW].get("w1") == "fourth", repr(r.stores[0][HW].get("w1")))

    # a handle opened while the mode was read never writes after the mode becomes write (it must be opened again)
    hw_flip_files()
    s = Script()
    s.add("EXEC", "RUN bp zznfhm1", ok=lambda c: c["rc"] == "")
    s.add("OPEN", "nfw", HW, label="OPEN while the definition says READ: handle 1 with NO rc<7>, and the read form of the audit line", ok=k_open_r(1), req=[ACCT_REQ, W_OPEN(HW)],
          audit="open server=nfw file=hwork")
    s.add("EXEC", "RUN bp zznfhm2", ok=lambda c: c["rc"] == "")
    s.add("WRITE", 1, "w1", "x", label="...set to write afterwards, the OLD handle is still read: WRITE is 11501 (it must be opened again), nothing sent, and NO 'reason=mode' line (the refusal is the handle's own)",
          ok=k_err(11501, "nfw", "write"))
    s.add("OPEN", "nfw", HW, label="...a new OPEN now is a write-mode handle (rc<7> = 1)", ok=k_open_w(2), req=[W_OPEN(HW)], audit=OPEN_W_AUD)
    s.add("CLOSEALL", ok=k_ok("", 0), req=[(1, b"")])
    try:
        r = hw_go(None, s, (A,), admin=True)
    finally:
        hw_restore_defs()
    row("the open-while-read program ran to the end and no connection is left", h_sane(r), h_why(r))
    judge(r, s)
    row("...the requests and the audit trail are as listed", a_wire(r, s) and r.audits == s.audits(), repr((hw_first_diff(r.d[0], s.wire()), r.audits)))


def hw_txn(A):
    say("\n  -- a change or a lock inside a transaction is refused (11510), a read is not --")
    s = Script()
    s.add("OPEN", "nfw", HW, ok=k_open_w(1), req=[ACCT_REQ, W_OPEN(HW)], audit=OPEN_W_AUD)
    for nm, extra, op in (("WRITE", "x", "write"), ("WRITEU", "x", "writeu"), ("DELETE", "", "delete"), ("DELETEU", "", "deleteu"), ("CLEARFILE", "", "clear.file")):
        s.add("T" + nm, 1, "w1" if nm != "CLEARFILE" else "", extra, label="INSIDE A TRANSACTION: %s is refused with 11510 naming the server and the operation (%s); nothing is sent" % (nm, op),
              ok=k_err(11510, "nfw", op))
    s.add("TLOCK", 1, "w1", "u", label="...LOCK is refused too (lock)", ok=k_err(11510, "nfw", "lock"))
    s.add("TREAD", 1, "w1", label="...but a READ in the same transaction is served", ok=k_rec(HWREC["w1"]), req=[W_READ(1, "w1")])
    s.add("TRELEASE", 1, "w1", label="...and RELEASE is not refused (it changes no data): rc 0", ok=k_ok("", 0), req=[W_REL(1, "w1")])
    s.add("WRITE", 1, "w1", "after", label="after the transaction the same handle writes: rc 0", ok=k_ok("", 0), req=[W_WRITE(1, "w1", "after")], audit="write server=nfw file=hwork")
    s.add("CLOSEALL", ok=k_ok("", 0), req=[(1, b"")])
    r = hw_go("zznhon", s, (A,))
    row("the transaction program ran to the end and no connection is left", h_sane(r), h_why(r))
    judge(r, s)
    row("...THE FAKE SAW only the READ, the RELEASE and the good WRITE after the transaction", a_wire(r, s), "first difference: %r" % (hw_first_diff(r.d[0], s.wire()),))
    row("...no audit line for the refused changes (the handler's own test is a defence; the kernel refuses first)", r.audits == s.audits(), repr(r.audits))


def hw_lost(A):
    say("\n  -- a connection lost DURING a change: 11509, the outcome unknown, never sent twice --")

    def case(label, kind, req_type, stmt, op, reads_new, audits, store_check):
        # kind: drop_before or drop_after (the first request of that type in the session); stmt: the script line that makes the request; audits: the whole audit trail expected
        s = Script()
        s.add("OPEN", "nfw", HW, ok=k_open_w(1))
        nm, a, b, c = stmt
        msg_ = 11497 if op == "lock" else 11509
        s.add(nm, a, b, c, label="%s: %s is %d naming the server and '%s'%s" % (label, nm, msg_, op, "" if msg_ == 11509 else " (a lock changes no data: the old message, as for a read)"),
              ok=k_err(msg_, "nfw", op))
        s.add("READ", 1, "w1", label="...the next use of the handle is 11495 (the connection was lost; it is not reopened)", ok=k_err(11495, "nfw", 1))
        s.add(nm, a, b, c, label="...a second %s on the lost handle is 11495 too: THE REQUEST IS NEVER SENT AGAIN" % nm, ok=k_err(11495, "nfw", 1))
        s.add("OPEN", "nfw", HW, label="...a new OPEN dials again (handle 2)", ok=k_open_w(2))
        s.add("READ", 2, "w1", label=reads_new[0], ok=reads_new[1])
        s.add("CLOSE", 1, ok=k_ok("", 0))
        s.add("CLOSEALL", ok=k_ok("", 0))
        r = hw_go("zznhon", s, (A,), cfg={kind: {req_type: 1}})
        row("%s: the program ran to the end and no connection is left" % label, r.began and r.ended and len(r.calls) == r.n and r.idle and all(not d["errors"] for d in r.d), h_why(r))
        judge(r, s)
        ses = r.d[0]["sessions"]
        row("...the fake saw TWO connections and request type %d exactly ONCE (never retried); the first connection's last request is that one" % req_type,
            len(ses) == 2 and sum(x.requests.count(req_type) for x in ses) == 1 and ses[0].requests[-1] == req_type, repr([x.requests for x in ses]))
        row("...the audit trail: %s" % " / ".join(audits), r.audits == audits, repr(r.audits))
        row("...THE FILE: %s" % store_check[0], store_check[1](r.stores[0][HW]), repr(r.stores[0][HW]))
        return r

    case("DROPPED BEFORE the WRITE was executed", "drop_before", 16, ("WRITE", 1, "w1", "lost"), "write",
         ("a READ through the new connection finds the record UNCHANGED (the change was not made)", k_rec(HWREC["w1"])),
         [OPEN_W_AUD, "write server=nfw file=hwork", "lost server=nfw op=write", OPEN_W_AUD], ("w1 is unchanged", lambda st: st.get("w1") == HWREC["w1"]))
    case("DROPPED AFTER the WRITE was executed", "drop_after", 16, ("WRITE", 1, "w1", "lost"), "write",
         ("a READ through the new connection finds the record CHANGED (the change was made - the same message 11509 cannot say which)", k_rec("lost")),
         [OPEN_W_AUD, "write server=nfw file=hwork", "lost server=nfw op=write", OPEN_W_AUD], ("w1 holds the new record", lambda st: st.get("w1") == "lost"))
    case("DROPPED AFTER the WRITEU was executed", "drop_after", 17, ("WRITEU", 1, "w1", "lost"), "writeu",
         ("a READ through the new connection finds the record CHANGED", k_rec("lost")),
         [OPEN_W_AUD, "write server=nfw file=hwork", "lost server=nfw op=writeu", OPEN_W_AUD], ("w1 holds the new record", lambda st: st.get("w1") == "lost"))
    case("DROPPED AFTER the DELETE was executed", "drop_after", 18, ("DELETE", 1, "w1", ""), "delete",
         ("a READ through the new connection finds the record GONE", k_else(3006)),
         [OPEN_W_AUD, "delete server=nfw file=hwork", "lost server=nfw op=delete", OPEN_W_AUD], ("w1 is gone", lambda st: "w1" not in st))
    case("DROPPED BEFORE the CLEARFILE", "drop_before", 31, ("CLEARFILE", 1, "", ""), "clear.file",
         ("a READ through the new connection finds the record (the file was not cleared)", k_rec(HWREC["w1"])),
         [OPEN_W_AUD, "clear server=nfw file=hwork", "lost server=nfw op=clear.file", OPEN_W_AUD], ("the file still holds its three records", lambda st: st == HWREC))
    case("DROPPED AFTER the LOCK was executed", "drop_after", 30, ("LOCK", 1, "w1", "u"), "lock",
         ("a READ through the new connection works", k_rec(HWREC["w1"])),
         [OPEN_W_AUD, OPEN_W_AUD], ("w1 is unchanged (a lock changes nothing)", lambda st: st.get("w1") == HWREC["w1"]))


def hw_errors(A):
    say("\n  -- the server's own errors are errors of the call (11500 with the status), never an abort of the handler --")
    s = Script()
    s.add("OPEN", "nfw", HW, ok=k_open_w(1), audit=OPEN_W_AUD)
    s.add("WRITE", 1, "w1", "x", label="MUSTLOCK on the server, no lock held: WRITE is an error, rc 3, message 11500 naming the server and the operation, 'status -3023', rc<6> -3023 (signed)",
          ok=k_srverr("write", -3023), audit="write server=nfw file=hwork")
    s.add("DELETE", 1, "w2", label="...DELETE: -3023", ok=k_srverr("delete", -3023), audit="delete server=nfw file=hwork")
    s.add("LOCK", 1, "w1", "u", ok=k_ok("", 0))
    s.add("WRITEU", 1, "w1", "y", label="...with the update lock held the same WRITEU is done", ok=k_ok("", 0))
    s.add("READ", 1, "w1", label="...and the handler goes on: the record is 'y'", ok=k_rec("y"))
    s.add("CLOSEALL", ok=k_ok("", 0))
    r = hw_go("zznhon", s, (A,), cfg={"must_lock": True})
    row("the MUSTLOCK program ran to the end (no abort) and no connection is left", h_sane(r), h_why(r))
    judge(r, s)
    row("...the file: w1 'y', w2 untouched", r.stores[0][HW].get("w1") == "y" and r.stores[0][HW].get("w2") == HWREC["w2"], repr(r.stores[0][HW]))
    row("...the audit trail: the open, the first write and the first delete - the refused attempts are audited like the good ones (the line is written BEFORE the request)", r.audits == s.audits(), repr(r.audits))

    s = Script()
    s.add("OPEN", "nfw", HW, ok=k_open_w(1))
    s.add("WRITE", 1, "w1", "x", label="a file the server's OS user cannot write: WRITE is +3018 and no text, so 'status 3018', rc<6> 3018 (the real server's, REAL_ON_ERROR - measured 19 Oct 26)",
          ok=k_srverr("write", 3018))
    s.add("DELETE", 1, "w1", label="...DELETE: 'status 3018'", ok=k_srverr("delete", 3018))
    s.add("CLEARFILE", 1, label="...CLEARFILE has no ON ERROR clause and aborts: STATUS() 0 and the kernel's TEXT, shown (19 Oct 26, K1), rc<6> 0",
          ok=k_srverr("clear.file", 0, text=netfake.abort_text("CLEARFILE on read-only file", 2099)))
    s.add("LOCK", 1, "w1", "u", label="...a lock on it is granted (a lock needs no write permission)", ok=k_ok("", 0))
    s.add("CLOSEALL", ok=k_ok("", 0))
    r = hw_go("zznhon", s, (A,), cfg={"readonly": (HW,)})
    row("the read-only-file program ran to the end and no connection is left", h_sane(r), h_why(r))
    judge(r, s)
    row("...nothing changed on the fake", r.stores[0][HW] == dict(HWREC), "")

    s = Script()
    s.add("OPEN", "nfw", HWBP, ok=k_open_w(1))
    s.add("OPEN", "nfw", HWVOC, ok=k_open_w(2))
    s.add("OPEN", "nfw", "dict " + HW, ok=k_open_w(3))
    s.add("OPEN", "nfw", HW, ok=k_open_w(4))
    s.add("WRITE", 1, "prog1", "x", label="THE SERVER'S OWN EDIT GATE (the files-only login has none by default): WRITE to the file bp is an error with the server's text (11407), nothing written",
          ok=k_srverr("write", 0, text=msg(11407)))
    s.add("WRITE", 2, "verb1", "x", label="...to voc: the text of 11405", ok=k_srverr("write", 0, text=msg(11405)))
    s.add("WRITE", 3, "name", "x", label="...to a dictionary (dict hwork): 11406", ok=k_srverr("write", 0, text=msg(11406)))
    s.add("DELETE", 1, "prog1", label="...DELETE from bp: 11407", ok=k_srverr("delete", 0, text=msg(11407)))
    s.add("CLEARFILE", 2, label="...CLEARFILE of voc: 11405", ok=k_srverr("clear.file", 0, text=msg(11405)))
    s.add("WRITE", 4, "w1", "plain", label="CONTROL: an ordinary file is written", ok=k_ok("", 0))
    s.add("CLOSEALL", ok=k_ok("", 0))
    r = hw_go("zznhon", s, (A,))
    row("the server-edit-gate program ran to the end and no connection is left", h_sane(r), h_why(r))
    judge(r, s)
    row("...nothing changed on bp, voc or the dictionary, and the ordinary file holds the control write", r.stores[0][HWBP] == {"prog1": "x"} and r.stores[0][HWVOC] == {"verb1": "V"}
        and r.stores[0][HW].get("w1") == "plain", repr(r.stores[0]))
    s = Script()
    s.add("OPEN", "nfw", HWBP, ok=k_open_w(1))
    s.add("WRITE", 1, "prog1", "changed", label="CONTROL: with the server's gate for program files (bp.edit) open the same WRITE is done", ok=k_ok("", 0))
    s.add("CLOSEALL", ok=k_ok("", 0))
    r = hw_go("zznhon", s, (A,), cfg={"edit_allow": frozenset(["prog"])})
    judge(r, s)
    row("...and bp holds the record", r.stores[0][HWBP].get("prog1") == "changed", repr(r.stores[0][HWBP]))

    s = Script()
    s.add("OPEN", "nfw", HW, ok=k_open_w(1))
    s.add("LOCK", 1, "w1", "u", label="MAXRLOCK on the server (1 lock): the first lock is granted", ok=k_ok("", 0))
    s.add("LOCK", 1, "w2", "u", label="...a SECOND, new lock (request 30 has no ON ERROR clause: an abort) shows the kernel's TEXT with message 11162 in it (19 Oct 26, K1; it was 'status -3060', a status "
          "the real server does not send for this request), rc<6> 0", ok=k_srverr("lock", 0, text=netfake.abort_text(msg(11162), 2077)))
    s.add("LOCK", 1, "w1", "u", label="...a lock the session already holds is not a new one: rc 0", ok=k_ok("", 0))
    s.add("READ", 1, "w1", label="...and the handler goes on", ok=k_rec(HWREC["w1"]))
    s.add("CLOSEALL", ok=k_ok("", 0))
    r = hw_go("zznhon", s, (A,), cfg={"maxrlock": 1})
    row("the MAXRLOCK program ran to the end (no abort) and no connection is left", h_sane(r), h_why(r))
    judge(r, s)

    # the answer to a READ that the server gave with an ON ERROR: the old gaps row, built since the class is quiet
    s = Script()
    s.add("OPEN", "nfa", HFILE, ok=k_ok("1", 1))
    s.add("OPEN", "nfw", HW, ok=k_open_w(2))
    s.add("READ", 1, "c1", label="A READ the server answers with an ON ERROR that has a TEXT (read mode handle): rc 3 with 11500 naming the server, the operation and THE TEXT 'boom' (19 Oct 26, K1; it showed "
          "'status 0'), rc<6> 0 - the handler does NOT abort (the class is quiet)", ok=k_srverr("read", 0, text="boom", srv="nfa"))
    s.add("READ", 2, "w1", label="...the same on a write-mode handle", ok=k_srverr("read", 0, text="boom"))
    s.add("CLOSEALL", ok=k_ok("", 0))
    r = hw_go("zznhon", s, (A,), cfg={"fail": {6: (netfake.SV_ON_ERROR, "boom")}})
    row("the program that made those READs reached its end", r.began and r.ended and r.idle, h_why(r))
    judge(r, s)

    # an ON ERROR reply with NO text (the server's ON ERROR clause had nothing to say, and the server empties its message at the top of every request): the status is shown, as before
    s = Script()
    s.add("OPEN", "nfa", HFILE, ok=k_ok("1", 1))
    s.add("OPEN", "nfw", HW, ok=k_open_w(2))
    s.add("READ", 1, "c1", label="CONTROL: the same READ answered with an ON ERROR with NO text shows 'status 0' - the status is what is left to show, as it was before 19 Oct 26",
          ok=k_srverr("read", 0, srv="nfa"))
    s.add("READ", 2, "w1", label="...the same on a write-mode handle", ok=k_srverr("read", 0))
    s.add("CLOSEALL", ok=k_ok("", 0))
    r = hw_go("zznhon", s, (A,), cfg={"fail": {6: (netfake.SV_ON_ERROR, "")}})
    row("the program that made those READs reached its end", r.began and r.ended and r.idle, h_why(r))
    judge(r, s)

    # 19 Oct 26, finish 2 (verifier): the third place that shows an ON ERROR reply's text is act.select, which sends two requests - the SELECT (11) and the READLIST (14) - and either can be
    # answered with an ON ERROR.  Replacing its call of on.error.text with 'status <n>' left this suite green, because no row sent either request an ON ERROR.  The first row of this kind
    # found why: the class ABORTED on such a reply even from a quiet object ("READLIST generated an abort event"), so the branch could not run; select() and readlist() honour quiet now
    # (gpl.bp/sdclient) and act.select looks at obj->LastError after the SELECT too.
    for req, which in ((14, "READLIST (request 14, the second of the two)"), (11, "SELECT (request 11, the first of the two)")):
        s = Script()
        s.add("OPEN", "nfa", HFILE, ok=k_ok("1", 1))
        s.add("SELECT", 1, label="A SELECT whose %s the server answers with an ON ERROR that has a TEXT: rc 3 with 11500 naming the server, 'select' and THE TEXT 'boom' (not 'status 0'), "
              "and the program is not aborted" % which, ok=k_srverr("select", 0, text="boom", srv="nfa"))
        s.add("CLOSEALL", ok=k_ok("", 0))
        r = hw_go("zznhon", s, (A,), cfg={"fail": {req: (netfake.SV_ON_ERROR, "boom")}})
        row("the program that made that SELECT reached its end (it was aborted before: 'READLIST generated an abort event')", r.began and r.ended and r.idle, h_why(r))
        judge(r, s)
        inj = r.d[0]["sessions"][0].injected if r.d and r.d[0]["sessions"] else None
        row("...the fake received the %s request once and answered it with the injected ON ERROR%s" % ("READLIST" if req == 14 else "SELECT", " (the SELECT before it was served)" if req == 14 else " (and no READLIST followed)"),
            r.d[0]["types"].count(11) == 1 and r.d[0]["types"].count(14) == (1 if req == 14 else 0) and inj == [(req, "fail")], repr((r.d[0]["types"], inj)))
        s = Script()
        s.add("OPEN", "nfa", HFILE, ok=k_ok("1", 1))
        s.add("SELECT", 1, label="CONTROL: the same SELECT with the ON ERROR on request %d having NO text shows 'status 0'" % req, ok=k_srverr("select", 0, srv="nfa"))
        s.add("CLOSEALL", ok=k_ok("", 0))
        r = hw_go("zznhon", s, (A,), cfg={"fail": {req: (netfake.SV_ON_ERROR, "")}})
        row("the program that made that SELECT reached its end", r.began and r.ended and r.idle, h_why(r))
        judge(r, s)

    # a text with characters a terminal would act on, and one longer than 100: cleaned and cut like any text from another machine
    raw_text = "\x1b[31mred " + "z" * 150
    want_text = "".join(ch for ch in raw_text[:100] if 32 <= ord(ch) <= 126)        # clean.text cuts to 100 characters FIRST, then keeps the printable ones
    s = Script()
    s.add("OPEN", "nfw", HW, ok=k_open_w(1))
    s.add("READ", 1, "c1", label="an ON ERROR text with an escape character and a long tail: printable ASCII only and at most 100 characters (cut to 100 first, then the escape is dropped: %d "
          "characters)" % len(want_text), ok=lambda c: c["rc"] == "3" and c["m"] == "11500" and c["args"][1] == "read" and c["args"][2] == want_text and len(want_text) == 99 and "\x1b" not in c["args"][2])
    s.add("CLOSEALL", ok=k_ok("", 0))
    r = hw_go("zznhon", s, (A,), cfg={"fail": {6: (netfake.SV_ON_ERROR, raw_text)}})
    row("the program that made that READ reached its end", r.began and r.ended and r.idle, h_why(r))
    judge(r, s)


def hw_misc(A):
    say("\n  -- a success status the client must not read; STATE; the other statements of the gate --")
    s = Script()
    s.add("OPEN", "nfw", HW, ok=k_open_w(1))
    s.add("WRITE", 1, "w1", "x", label="the fake sends STATUS() 3006 with every successful change: WRITE is still rc 0 with NO status (the client never reads the status of a success)", ok=k_ok("", 0))
    s.add("DELETE", 1, "w2", ok=k_ok("", 0))
    s.add("LOCK", 1, "w3", "u", label="...LOCK too", ok=k_ok("", 0))
    s.add("RELEASE", 1, "w3", ok=k_ok("", 0))
    s.add("CLEARFILE", 1, ok=k_ok("", 0))
    s.add("CLOSEALL", ok=k_ok("", 0))
    r = hw_go("zznhon", s, (A,), cfg={"success_status": 3006})
    row("the success-status program ran to the end and no connection is left", h_sane(r), h_why(r))
    judge(r, s)

    # the account that is not listed or has no gate cannot change a thing
    s = Script()
    s.add("OPEN", "nfw", HW, label="THE NET GATE OFF (zznhoff): OPEN of the write-mode server is 11460 - the mode loosens nothing the gate holds", ok=k_err(11460, "zznhoff", "nfw"),
          audit="refused server=nfw reason=gate")
    s.add("WRITE", 1, "w1", "x", label="...and a WRITE on a handle that is not open is 11494", ok=k_err(11494, 1))
    r = hw_go("zznhoff", s, (A,))
    row("the gate-off program ran to the end", h_sane(r), h_why(r))
    judge(r, s)
    row("...nothing was dialled", all(d["conns"] == 0 for d in r.d) and r.audits == s.audits(), repr(r.audits))


# ---- K. the kernel: a NET_FILE through real statements (slice 3c) ---------------------------------------------------------------------------------
#
# S.65 slice 3c.  Until now nothing in the kernel called the handler: the sections above drive $netfile from a BASIC program that CALLs it.  Here an
# ORDINARY session's OPEN statement names a VOC record of type N (field 2 the server, field 3 the file there), and the kernel's NET_FILE file
# variable type does the rest: open_file() recognises the encoded path _voc_ref returns, net_open() asks the NET gate in C and then runs $netfile,
# and READ, READV, MATREAD, FILEINFO and CLOSE go to it.  Every other statement is REFUSED before it touches anything (message 11501).
#
# THE INSTRUMENT.  (1) The driver zznk1 reads one line at a time and prints "KR <op> ..." for what the STATEMENT gave it - which of THEN, ELSE and
# ON ERROR ran, STATUS(), the length and the (mark-shown) text of what it got - so a row reads the program's view and not the kernel's intent.
# (2) The refusal matrix puts each statement in a program of its own: A (no ON ERROR: the program must stop with the kernel's message and never
# print SURVIVED) and E (ON ERROR: the program must go on, print the STATUS() the branch saw, read a record from the same file afterwards and reach
# its end).  (3) THE FAKE'S PACKET LOG decides what reached the other machine: whatever the program thinks happened, the log may hold only login
# (47, 48), account (3), open (4), read (6), close (5) and quit (1); a write, delete, clear, lock, select or record-locked request in it is a
# failed row, and the records on the fake must equal what they were.  (4) Every session is required to have ended every connection.
# EXPECTED VALUES come from this file (the records it put into the store, the numbers err.h and the design give) and from the sandbox's own messages.
#
# WHAT IT CANNOT SHOW.  (1) That the kernel's own C gate is asked BEFORE the handler is loaded: the handler repeats the test with the same text, so
# a row cannot tell them apart; test-net-units.py reads the order in netfiles.c.  (2) The verbs (COUNT, LIST ... on the VOC name): their output is
# not known in advance, so a row requires the session to SURVIVE, the packet log to be clean, the data unchanged, and for CLEAR.FILE and DELETE.FILE
# the verb's own refusal text.  (3) Statements only an $internal program can write (AKREAD, AKWRITE, AKDELETE, CLEAR.AK, AKENABLE, AKMAP): the
# test-net-units.py checks read their refusals in the C; only GETLOCKS is run here.

KN = {}                                             # what the kernel section made
KDRV = "zznk1"                                      # the input driven program (OPEN READ READV MATREAD FI CLOSE EXEC)
KLOOP, KTXN, KVOC, KSENT, KGATE = "zznkl", "zznkt", "zznkv", "zznksent", "zznkg"
KOFF = "zznhnov"                                    # the NET gate on, voc.edit OFF
KSLOTS = 4                                          # the driver's file variables f1 .. f4
KALLOWED = {47, 48, 3, 4, 5, 6, 1}                  # the requests a read only session may send: login, account, open, close, read, quit.  Since slice 3e this is the set of a
                                                    # session on a MODE READ server (nfa, nfb): the refusal matrix below is the mode=read CONTROL of the section kwrite
KBAD = [("zznbad1", "1abc", HFILE), ("zznbad2", "nfa b", HFILE), ("zznbad3", "", HFILE), ("zznbad4", "nfa", ""), ("zznbad5", "nfa", "a/b"),
        ("zznbad6", "nfa", "dict hcust"), ("zznbad7", "nfa", "x" * 64), ("zznbad8", "a" + "b" * 16, HFILE), ("zznbad9", "nfa", "a;b")]


def kn_voc():
    """The VOC records the administrator writes into the fixture accounts: account -> [(id, fields)]."""
    def n(srv, fil):
        return ["N", srv, fil]
    verbs = [("zznki", ["V", "CA", "$zznki"]), ("zznkj", ["V", "CA", "$zznkj"])]
    on = [("zznet1", n("nfa", HFILE)), ("zznetempty", n("nfa", HEMPTY)), ("zznetb", n("nfb", HFILE)), ("zznetmiss", n("nfa", "nosuchfile")),
          ("zznetnc", n("nfnocred", HFILE)), ("zznetcp", n("nfcpin", HFILE)), ("zznetpin", n("nfpin", HFILE)), ("zznetunl", n("nfadm", HFILE)),
          ("zznetup", n("NFA", "HCUST")), ("zznetsp", n(" nfa ", " hcust "))]
    on += [(v, n(s, f)) for v, s, f in KBAD]
    return {"zznhon": on + verbs,
            "zznhoff": [("zznet1", n("nfa", HFILE)), ("zznqon", ["Q", "zznhon", "zznet1"])] + verbs,
            "zznhunl": [("zznet1", n("nfa", HFILE))] + verbs}


def kn_fix_text():
    root = os.path.join(g.BOX, "user_accounts")
    out = ["$internal"]
    for acct, recs in kn_voc().items():
        out.append("   openpath '%s' to v else crt 'KFIX no voc %s' ; stop" % (os.path.join(root, acct, "voc"), acct))
        for rid, flds in recs:
            out.append("   write %s to v, '%s'" % (":@fm:".join("'%s'" % x for x in flds), rid))
        out.append("   close v")
    out += ["   crt 'KFIX done'", "end", ""]
    return "\n".join(out)


def kn_case(op, tmpl, show_lines, pre=()):
    """One case of the driver: the statement TMPL once for each of the four file variables (the slot picks one), then the lines that print."""
    out = ["         case op = '%s'" % op] + ["            " + p for p in pre] + ["            begin case"]
    for n in range(1, KSLOTS + 1):
        out.append("               case slot = %d" % n)
        out += ["                  " + ln.replace("{f}", "f%d" % n) for ln in tmpl.split("\n")]
    out.append("            end case")
    return out + ["            " + s for s in show_lines]


def kn_driver():
    L = ["$include err.h", "   dim m(4)"] + ["   f%d = ''" % n for n in range(1, KSLOTS + 1)]
    L += ["   crt 'KR begin'", "   done = @false", "   loop", "      input ln", "      done = (ln = 'END') or (ln = '' and status() = ER$EOF)", "   until done do",
          "      op = field(ln, '|', 1)", "      a2 = field(ln, '|', 2)", "      a3 = field(ln, '|', 3)", "      a4 = field(ln, '|', 4)",
          "      slot = 0", "      if op # 'EXEC' then slot = a2 + 0", "      oc = 'then'", "      rec = ''", "      mat m = ''", "      begin case"]
    eo = "on error oc = 'error' else oc = 'else'"
    L += kn_case("OPEN", "open a3 to {f} " + eo, ["st = status()", "crt 'KR OPEN ':a3:' ':oc:' st=':st"])
    L += kn_case("ODICT", "open 'DICT', a3 to {f} " + eo, ["st = status()", "crt 'KR ODICT ':a3:' ':oc:' st=':st"])
    L += kn_case("READ", "read rec from {f}, a3 " + eo,
                 ["st = status()", "v = rec ; gosub shw", "crt 'KR READ ':a3:' ':oc:' st=':st:' len=':len(rec):' rec=[':sv:']'"])
    L += kn_case("READV", "readv rec from {f}, a3, fld " + eo,
                 ["st = status()", "v = rec ; gosub shw", "crt 'KR READV ':a3:'/':a4:' ':oc:' st=':st:' len=':len(rec):' rec=[':sv:']'"], pre=["fld = a4 + 0"])
    L += kn_case("MATREAD", "matread m from {f}, a3 " + eo, ["st = status()", "crt 'KR MATREAD ':a3:' ':oc:' st=':st:' [':m(1):'][':m(2):'][':m(3):']'"])
    L += kn_case("FI", "x = fileinfo({f}, fkey)", ["v = x ; gosub shw", "crt 'KR FI ':a3:' [':sv:']'"], pre=["fkey = a3 + 0"])      # not `key`: KEY() is a function
    L += kn_case("IDX", "x = indices({f})", ["v = x ; gosub shw", "crt 'KR IDX [':sv:']'"])
    L += kn_case("IDX2", "x = indices({f}, 'CITY')", ["v = x ; gosub shw", "crt 'KR IDX2 [':sv:']'"])
    L += kn_case("CLOSE", "close {f}", ["crt 'KR CLOSE ':slot"])
    # slice 3d: SELECT / SELECTV / SSELECT of the file in the slot into list a3 (or a variable); the ids come out sorted by READNEXT as the list holds them
    for tag, stmt, src in (("SELECT", "select {f} to lno on error oc = 'error'", "lno"), ("SELECTV", "selectv {f} to lv on error oc = 'error'", "lv"), ("SSELECT", "sselect {f} to lno", "lno")):
        L += kn_case(tag, stmt, ["st = status()", "ids = ''", "n.sel = @selected", "loop", "   readnext x from %s else exit" % src, "   ids<-1> = x", "repeat",
                                 "crt 'KR %s ':oc:' st=':st:' n=':n.sel:' ids=[':change(ids, @fm, ','):']'" % tag], pre=["lno = a3 + 0"])
    L += ["         case op = 'SLEEP'", "            sleep a2 + 0", "            crt 'KR SLEEP ':a2"]
    L += ["         case op = 'EXEC'", "            execute a2", "            crt 'KR EXEC ':a2:' who=':@who",
          "         case 1", "            crt 'KR UNKNOWN ':op", "      end case", "   repeat", "   crt 'KR end'", "   stop", "",
          "shw: * SV = V with the four marks made visible, cut to its first and last 40 characters when over 100",
          "   sv = v", "   sv = change(sv, @im, '<I>')", "   sv = change(sv, @fm, '<F>')", "   sv = change(sv, @vm, '<V>')", "   sv = change(sv, @sm, '<S>')",
          "   if len(sv) > 100 then sv = sv[1,40] : '..' : sv[len(sv) - 39, 40]", "   return", "", "end", ""]
    return "\n".join(L)


KLOOP_TEXT = """   crt 'KR zznkl begin'
   bad = 0
   for i = 1 to 150
      open 'zznet1' to f on error bad += 1 else bad += 1
   next i
   crt 'KR zznkl opened bad=':bad
   read r from f, 'c1' then crt 'KR zznkl read len=':len(r) else crt 'KR zznkl read else'
   crt 'KR zznkl end'
end
"""

KTXN_TEXT = """   crt 'KR zznkt begin'
   open 'zznet1' to f else crt 'KR zznkt openfail st=':status() ; stop
   begin transaction
      read r from f, 'c1' then crt 'KR zznkt read len=':len(r) else crt 'KR zznkt read else'
      x = fileinfo(f, 1038)
      crt 'KR zznkt txnupdate=':x
      commit
   end transaction
   crt 'KR zznkt end'
end
"""

# an ordinary program writes a pointer into its own VOC and opens it: the edit gate (voc.edit) and the NET gate are each asked of the ACCOUNT
KVOC_TEXT = """   crt 'KR v begin'
   open 'voc' to v else crt 'KR v novoc' ; stop
   ok = @true
   write 'N':@fm:'nfa':@fm:'hcust' to v, 'zznetself' on error ok = @false
   read x from v, 'zznetself' then p = 1 else p = 0
   crt 'KR v write ':(if ok then 'OK' else 'REFUSED'):' P=':p
   oc = 'then'
   open 'zznetself' to f on error oc = 'error' else oc = 'else'
   st = status()
   crt 'KR v open ':oc:' st=':st
   if oc = 'then' then
      read r from f, 'c1' then crt 'KR v read len=':len(r) else crt 'KR v read else'
   end
   crt 'KR v end'
end
"""

KGATE_TEXT = """   crt 'KR g begin'
   open 'zznet1' to f else crt 'KR g ELSE st=':status() ; stop
   crt 'KR g SURVIVED'
end
"""

KSENT_TEXT = "   crt 'KR sent'\nend\n"

KI_TEXT = """$internal
program zznki
$catalog $zznki
   oc = 'then'
   crt 'KR ki begin'
   open 'zznet1' to f on error oc = 'error' else oc = 'else'
   st = status()
   crt 'KR ki open ':oc:' st=':st
   if oc = 'then' then
      read r from f, 'c1' then crt 'KR ki read len=':len(r) else crt 'KR ki read else'
      crt 'KR ki flags=':fileinfo(f, 10001):' type=':fileinfo(f, 3):' coll=':fileinfo(f, 1035)
   end
   crt 'KR ki end'
end
"""

KJ_TEXT = """$internal
program zznkj
$catalog $zznkj
   crt 'KR kj begin'
   open 'zznet1' to f else crt 'KR kj openfail st=':status() ; stop
   locks = getlocks(f, '')
   crt 'KR kj SURVIVED fields=':dcount(locks, @fm):' values=':dcount(locks<1>, @vm):' numeric=':num(change(locks<1>, @vm, '')):' null=':(locks = '')
end
"""

# programs that are not refusals of a statement but must not be taken for a remote file either: the VOC name is not a path, and a char(1) typed into
# a path is only a path (OPENPATH never looks for the encoded form)
KX_TEXT = {
    "zznkx1": """   crt 'KR oseq begin'
   openseq 'zznet1', 'c1' to sq then crt 'KR oseq THEN' else crt 'KR oseq ELSE st=':status()
   crt 'KR oseq end'
end
""",
    "zznkx2": """   crt 'KR opath begin'
   openpath char(1):'N':char(1):'nfa':char(1):'hcust' to g then crt 'KR opath THEN' else crt 'KR opath ELSE st=':status()
   crt 'KR opath end'
end
""",
    "zznkx3": """   crt 'KR callfile begin'
   call 'zznet1 zzprog'
   crt 'KR callfile SURVIVED'
end
""",
}

# The refusal matrix.  (tag, lines before the open, the statement lines WITHOUT an ON ERROR clause, the lines WITH one (None: the statement has no
# such clause), the messages the abort may give as (number, second argument), the STATUS() the ON ERROR branch sees).  The server in every message
# is nfa, the server of zznet1.  7000 is ER_NETWORK, 3035 ER_PERM: the statements that take the S.64 edit-gate convention (RECORDLOCKU / L)
# give 3035, the others the net_refuse() status.  SELECT and SELECTV are not here since slice 3d: they work (kn_query).  Every statement uses the open file variable f and the record c1.
# 18 Oct 26 (slice 3e): nfa is MODE READ, so EVERY ROW OF THE MATRIX STANDS UNCHANGED AS THE MODE=READ CONTROL - the write, delete, lock and release statements are refused with 11501 (or 3035)
# and nothing reaches the server.  The same statements on a MODE WRITE server are the section kwrite's; the ones that stay refused there (11511) are re-run from this table by kw_prep.


def km(tag, a, e, op, st, pre=(), num=11501):
    ops = list(op) if isinstance(op, (list, tuple)) else [op]
    return (tag, list(pre), a if isinstance(a, list) else [a], (e if isinstance(e, list) or e is None else [e]), [(num, o) for o in ops], st)


KM = [
    km("write", "write 'zz' to f, 'c1'", "write 'zz' to f, 'c1' on error null", "write", 7000),
    km("writeu", "writeu 'zz' to f, 'c1'", "writeu 'zz' to f, 'c1' on error null", "writeu", 7000),
    km("writev", "writev 'zz' to f, 'c1', 2", "writev 'zz' to f, 'c1', 2 on error null", "writev", 7000),
    km("writevu", "writevu 'zz' to f, 'c1', 2", "writevu 'zz' to f, 'c1', 2 on error null", "writevu", 7000),
    km("matwrite", "matwrite m to f, 'c1'", "matwrite m to f, 'c1' on error null", ("write", "writeu"), 7000, pre=["dim m(3)", "mat m = 'zz'"]),
    km("delete", "delete f, 'c1'", "delete f, 'c1' on error null", "delete", 7000),
    km("clearfile", "clearfile f", "clearfile f on error null", "clearfile", 7000),
    km("readu", "readu r from f, 'c1' else null", "readu r from f, 'c1' on error null else null", "readu", 7000),
    km("readl", "readl r from f, 'c1' else null", "readl r from f, 'c1' on error null else null", "readl", 7000),
    km("readvu", "readvu v from f, 'c1', 2 else null", "readvu v from f, 'c1', 2 on error null else null", "readvu", 7000),
    km("readvl", "readvl v from f, 'c1', 2 else null", "readvl v from f, 'c1', 2 on error null else null", "readvl", 7000),
    km("matreadu", "matreadu m from f, 'c1' else null", "matreadu m from f, 'c1' on error null else null", "matreadu", 7000, pre=["dim m(3)"]),
    km("matreadl", "matreadl m from f, 'c1' else null", "matreadl m from f, 'c1' on error null else null", "matreadl", 7000, pre=["dim m(3)"]),
    km("recordlocku", "recordlocku f, 'c1'", "recordlocku f, 'c1' on error null", "recordlocku", 3035),
    km("recordlockl", "recordlockl f, 'c1'", "recordlockl f, 'c1' on error null", "recordlockl", 3035),
    km("release", "release f, 'c1'", None, "release", None),
    km("releasef", "release f", None, "release", None),
    km("filelock", "filelock f", None, "filelock", None),
    km("fileunlock", "fileunlock f", None, "fileunlock", None),
    # S.72 (20 Oct 26): RECORDLOCKED() was no longer refused on a read-mode handle, and GETLOCKS() is the local view (kn_gates, kw_filelocks).  FILELOCK and FILEUNLOCK stay in this matrix as the
    # MODE=READ CONTROL: a read-mode handle still refuses both with 11501.
    # S.72b (20 Oct 26): RECORDLOCKED() is write-governed and is back in the matrix: a read-mode handle stops the program with 11501 and the fake's packet log must hold no request 34 (KALLOWED has none).
    # It has no ON ERROR clause, so it is an A row only; kw_peek has the write-mode side and the lock held by user 7.
    km("recordlocked", "x = recordlocked(f, 'c1')", None, "recordlocked", None),
    km("selectindex", "selectindex 'CITY' from f to 5", None, "selectindex", None),
    km("selectindexv", "selectindex 'CITY', 'Paris' from f to 5", None, "selectindex", None),
    km("selectright", "selectright 'CITY' from f to 5", None, "selectright/selectleft", None),
    km("selectleft", "selectleft 'CITY' from f to 5", None, "selectright/selectleft", None),
    km("setleft", "setleft 'CITY' from f", None, "setleft", None),
    km("setright", "setright 'CITY' from f", None, "setright", None),
    km("fcontrol6", "void fcontrol(f, 6, 'c1')", None, "fcontrol", None),
    km("fcontrol1", "void fcontrol(f, 1, -1)", None, "fcontrol", None),
    km("fiexcl", "x = fileinfo(f, 10000)", None, "fileinfo", None),
    km("fistaton", "x = fileinfo(f, 10002)", None, "fileinfo", None),
    km("fistatoff", "x = fileinfo(f, 10003)", None, "fileinfo", None),
    # a transaction: the WRITE is refused before the transaction code is reached
    km("txnwrite", ["begin transaction", "write 'zz' to f, 'c1'", "end transaction"],
       ["begin transaction", "write 'zz' to f, 'c1' on error null", "st = status()", "rollback", "end transaction"], "write", 7000),
]
# the FILEINFO keys the handler does not answer (stage 1 answers 0, 1, 2): 11502 names the server and the key, and the key is not guessed at
KFI_KEYS = (5, 1013, 1015, 1019, 1021, 1039, 1100)      # 3 (type), 1035 (collection) and 10001 (flags) are answered from the file variable since slice 3d
KM += [km("fikey%d" % k, "x = fileinfo(f, %d)" % k, None, str(k), None, num=11502) for k in KFI_KEYS]

# the verbs on the VOC name: (the command, its extra lines, a message number the verb is known to refuse with or None)
KVERBS = [("LIST.ITEM zznet1 c1", [], None), ("CT zznet1 c1", [], None), ("CONFIGURE.FILE zznet1 MINIMUM.MODULUS 7", [], None), ("ANALYSE.FILE zznet1", [], None),
          ("CLEAR.FILE zznet1", [], 1431), ("DELETE.FILE zznet1", [], 2015), ("DELETE zznet1 c1", [], None),
          ("COPY FROM zznet1 TO zznetempty c1", [], None), ("ED zznet1 zznewrec", ["I hello", "FI", "Q", "Y"], None)]


def kn_prog(tag, pre, middle, tail):
    """The text of a matrix program: PRE, the begin line, the open of zznet1 into f, MIDDLE, TAIL, end."""
    L = ["   " + p for p in pre]
    L += ["   crt 'KR %s begin'" % tag, "   open 'zznet1' to f else crt 'KR %s openfail st=':status() ; stop" % tag]
    L += ["   " + x for x in middle] + ["   " + x for x in tail] + ["end", ""]
    return "\n".join(L)


def kn_matrix_programs():
    """name -> (text, kind, entry index) for the A programs (no ON ERROR) and the E programs (with it)."""
    out = {}
    for i, (tag, pre, a_lines, e_lines, _want, _st) in enumerate(KM, 1):
        out["zznka%02d" % i] = (kn_prog(tag, pre, a_lines, ["crt 'KR %s SURVIVED st=':status()" % tag]), "A", i - 1)
        if e_lines is not None:
            mid = list(e_lines)
            if not any(x.startswith("st = ") for x in mid):
                mid.append("st = status()")
            tail = ["crt 'KR %s st=':st" % tag, "read r2 from f, 'c1' then crt 'KR %s back len=':len(r2) else crt 'KR %s back else'" % (tag, tag),
                    "crt 'KR %s end'" % tag]
            out["zznke%02d" % i] = (kn_prog(tag, pre, mid, tail), "E", i - 1)
    return out


def kn_compile(acct, names):
    """Compile programs already written to the account's bp in an ORDINARY session.  Returns (output, names with no object afterwards)."""
    out = []
    for i in range(0, len(names), 10):
        out += g.plain(acct, ["BASIC bp " + " ".join(names[i:i + 10])])
    return out, [n for n in names if not os.path.exists(os.path.join(acct_path(acct), "bp.out", n))]


def kn_prep():
    """What every kernel row needs, once: the handler section's preparation (credentials, definitions, fakes' files, three accounts), a fourth account
    with voc.edit off, the pointers the administrator writes, and the programs compiled in an ordinary session."""
    if "ready" in KN:
        return KN["ready"]
    KN["ready"] = False
    if not h_prep():
        return False
    g.EXTRA_FIXTURES[KOFF] = ("no", "no")
    path = g.build_account(KOFF)
    g.reg_write(KOFF, [path, "", g.GROUP, "", "", "", "no", "no", "", "no", "yes", "yes", "", "", "yes"])        # voc.edit NO, bp.edit yes, dict.edit yes, NET yes

    matrix = kn_matrix_programs()
    KN["matrix"] = matrix
    drv = kn_driver()
    plan = {"zznhon": {KDRV: drv, KLOOP: KLOOP_TEXT, KTXN: KTXN_TEXT, KVOC: KVOC_TEXT, KSENT: KSENT_TEXT},
            "zznhoff": {KDRV: drv, KVOC: KVOC_TEXT, KGATE: KGATE_TEXT, KSENT: KSENT_TEXT},
            "zznhunl": {KDRV: drv, KGATE: KGATE_TEXT, KSENT: KSENT_TEXT},
            KOFF: {KVOC: KVOC_TEXT}}
    plan["zznhon"].update(KX_TEXT)
    plan["zznhon"].update({n: t for n, (t, _k, _i) in matrix.items()})
    missing, warn, total = {}, [], 0
    for acct, progs in plan.items():
        for name, text in progs.items():
            g.put(os.path.join(acct_path(acct), "bp", name), text)
        out, miss = kn_compile(acct, list(progs))
        total += len(progs)
        warn += [ln for ln in out if re.search(r"warning|not assigned", ln, re.I)]
        if miss:
            missing[acct] = (miss, [ln for ln in out if any(n in ln for n in miss) or re.search(r"error", ln, re.I)][:10])
    row("SETUP: the %d kernel test programs (the driver, the loop, the transaction, the voc.edit control, the gate probes and the refusal matrix of %d statements) compile "
        "in ORDINARY sessions with no error and no warning" % (total, len(matrix)), not missing and not warn, repr((missing, warn[:4])))

    # the internal programs and the pointers: written by the administrator
    g.put(os.path.join(g.SYS, "gpl.bp", "zznki"), KI_TEXT)
    g.put(os.path.join(g.SYS, "gpl.bp", "zznkj"), KJ_TEXT)
    out = g.adm(["BASIC gpl.bp zznki zznkj"], internal=True)
    ok_i = g.has(out, r"^Compiled 2 program\(s\) with no errors") and not any(re.search(r"warning|not assigned", ln, re.I) for ln in out)
    g.put(os.path.join(g.SYS, "bp", "zznkfix"), kn_fix_text())
    out2 = g.adm(["BASIC bp zznkfix", "RUN bp zznkfix"], internal=True)
    ok_f = g.has(out2, r"^KFIX done$")
    npt = sum(len(v) for v in kn_voc().values())
    row("SETUP: the two $internal test programs compile into gpl.bp, and the administrator wrote %d VOC records (pointers of type N - eleven of them badly made on purpose - a "
        "Q-pointer, and the two verbs) into three accounts" % npt, ok_i and ok_f, repr((out[-4:], out2[-4:])))
    if missing or not ok_i or not ok_f:
        return False
    KN["ready"] = True
    return True


# ---- running a session ------------------------------------------------------------------------------------------------------------------------

def kn_run(acct, cmds, fakes, cfg=None):
    """Run these TCL commands in one ordinary session of ACCT.  Returns what the program printed (r.kr: the lines that begin "KR "), what each fake saw (r.d),
    the audit lines the session added (r.audits), whether the session hung (r.hung) and whether every connection ended (r.idle).  write_group=True from 18 Oct 26 (see h_go)."""
    c = {"files": True, "files_only": True, "write_group": True}
    c.update(cfg or {})
    for f in fakes:
        f.configure(**c)
    marks = [f.mark() for f in fakes]
    a0 = audit_size()
    t0 = time.time()
    hung = False
    try:
        out = bounded_plain(acct, list(cmds))
    except subprocess.TimeoutExpired:
        out, hung = [], True
    el = time.time() - t0
    idle = True
    for f in fakes:
        f.settle(quiet=0.3)
        idle = quiet(f) and idle
    r = Run()
    r.d = [f.delta(m) for f, m in zip(fakes, marks)]
    for f in fakes:
        f.configure()
    r.out, r.el, r.idle, r.hung = out, el, idle, hung
    r.kr = [ln for ln in out if ln.startswith("KR ")]
    r.crash = [ln for ln in out if re.search(r"double free|corruption|Segmentation|Aborted|core dumped|glibc|fatal signal", ln, re.I)]       # the process died, whatever it printed first
    if r.crash:
        KN.setdefault("crashes", []).append((acct, list(cmds)[:2], r.crash[:2]))
    r.audit = audit_since(a0)
    r.audits = h_audits(r.audit)
    return r


def kn_drive(acct, lines, fakes, cfg=None):
    return kn_run(acct, ["RUN bp " + KDRV] + list(lines) + ["END"], fakes, cfg)


def kn_sane(r, need_end=True):
    """The driver began and ended, the session did not hang, no fake found anything malformed or refused a request, and no connection is left."""
    return (not r.hung and "KR begin" in r.kr and ("KR end" in r.kr or not need_end) and r.idle
            and all(not d["errors"] for d in r.d) and all(not s.refused for d in r.d for s in d["sessions"]))


def kn_why(r, n=6):
    return "hung=%s began=%s ended=%s idle=%s fake errors=%r\n      kr: %r\n      tail: %r" % (
        r.hung, "KR begin" in r.kr, "KR end" in r.kr, r.idle, [d["errors"] for d in r.d], r.kr[-n:], r.out[-3:])


def kn_wire(d):
    """The requests after the login, a trailing Quit left out (a process that ends closes its socket; whether the handler's last word is a Quit is not the question)."""
    w = h_wire(d)
    return w[:-1] if w and w[-1][0] == 1 else w


def kn_conns(d):
    """by_conn() with a trailing Quit (1) of each connection left out."""
    return [c[:-1] if c and c[-1] == 1 else c for c in by_conn(d)]


def kn_opens(r):
    return [(m.group(1), m.group(2), int(m.group(3))) for m in (re.match(r"^KR OPEN (\S+) (\S+) st=(\d+)$", ln) for ln in r.kr) if m]


def kn_read_line(rid, rec, oc="then", st=0):
    return "KR READ %s %s st=%d len=%d rec=[%s]" % (rid, oc, st, len(rec), show(rec))


def kn_readv_line(rid, fld, rec, oc="then", st=0):
    return "KR READV %s/%s %s st=%d len=%d rec=[%s]" % (rid, fld, oc, st, len(rec), show(rec))


def kn_segments(out):
    """The lines each matrix program printed, by its tag: from its  KR <tag> begin  line to the next one."""
    segs, cur = {}, None
    for ln in out:
        m = re.match(r"^KR (\S+) begin$", ln)
        if m:
            cur = m.group(1)
            segs[cur] = []
        elif cur is not None:
            segs[cur].append(ln)
    return segs


def kn_abort(lines):
    """The text of the kernel's abort line in these lines ("0000001A: <message> at line N of <program>"), or None."""
    for ln in lines:
        m = re.match(r"^[0-9A-F]{8}: (.*?)(?: at line \d+ of| in) \S+$", ln)       # sysmsg 1121, or 1122 when the line is not known
        if m:
            return m.group(1)
    return None


def kn_snapshot(A):
    return {n: A.store.records(n) for n in (HFILE, HEMPTY)}


# ---- the section ------------------------------------------------------------------------------------------------------------------------------------

def kernel_section():
    say("\n--- kernel: a VOC pointer of type N opened by an ordinary OPEN statement; READ, READV, MATREAD, FILEINFO and CLOSE reach the handler; everything else is refused ---")
    if not kn_prep():
        return
    A, B = S["A"], S["B"]
    kn_runtime(A, B)
    kn_opens_refused(A, B)
    kn_gates(A, B)
    kn_matrix(A)
    kn_verbs(A)
    kn_query(A, B)
    kn_after(A)


def kn_runtime(A, B):
    say("\n  -- the statements that are supported --")
    c1, c2, c3, m1, big = (RECS[k] for k in ("c1", "c2", "c3", "m1", "big"))
    fields = c1.split(FMC)
    fkeys = (0, 1, 2, 1001, 1009, 1022, 1030, 1032, 1038)
    lines = ["OPEN|1|zznet1"] + ["READ|1|" + k for k in ("c1", "c2", "c3", "m1", "big", "nosuch")]
    # SLEEP|3 lets the record cache's entries (2 seconds) go, so that every READ below goes to the server whatever the machine's speed; the cache is the
    # subject of its own rows in kn_query
    lines += ["READV|1|c1|2", "READV|1|c1|1", "READV|1|c1|9", "READV|1|c1|0", "READV|1|nosuch|1", "SLEEP|3", "MATREAD|1|c2", "MATREAD|1|nosuch"]
    lines += ["FI|1|%d" % k for k in fkeys]
    lines += ["OPEN|2|zznetempty", "READ|2|x", "OPEN|3|zznet1", "READ|3|c3", "CLOSE|1", "READ|3|c2", "SLEEP|3", "READ|2|x", "CLOSE|2", "CLOSE|3"]
    want = ["KR OPEN zznet1 then st=0", kn_read_line("c1", c1), kn_read_line("c2", c2), kn_read_line("c3", c3), kn_read_line("m1", m1), kn_read_line("big", big),
            kn_read_line("nosuch", "", "else", 3006),
            kn_readv_line("c1", 2, fields[1]), kn_readv_line("c1", 1, fields[0]), kn_readv_line("c1", 9, ""), kn_readv_line("c1", 0, "c1"),
            kn_readv_line("nosuch", 1, "", "else", 3006), "KR SLEEP 3",
            "KR MATREAD c2 then st=0 [Jones][50][]", "KR MATREAD nosuch else st=3006 [][][]"]
    want += ["KR FI 0 [1]", "KR FI 1 [zznet1]", "KR FI 2 []", "KR FI 1001 [1]", "KR FI 1009 [-1]", "KR FI 1022 [1]", "KR FI 1030 [0]", "KR FI 1032 [1]", "KR FI 1038 [0]"]
    want += ["KR OPEN zznetempty then st=0", kn_read_line("x", "", "else", 3006), "KR OPEN zznet1 then st=0", kn_read_line("c3", c3),
             "KR CLOSE 1", kn_read_line("c2", c2), "KR SLEEP 3", kn_read_line("x", "", "else", 3006), "KR CLOSE 2", "KR CLOSE 3"]
    W = [(3, b"acct"), (4, b"hcust")] + [(6, FNO(1) + k.encode()) for k in ("c1", "c2", "c3", "m1", "big", "nosuch")]
    W += [(6, FNO(1) + b"c1")] * 4 + [(6, FNO(1) + b"nosuch")] + [(6, FNO(1) + b"c2"), (6, FNO(1) + b"nosuch")]
    W += [(4, b"hempty"), (6, FNO(2) + b"x"), (4, b"hcust"), (6, FNO(3) + b"c3"), (5, FNO(1)), (6, FNO(3) + b"c2"), (6, FNO(2) + b"x"), (5, FNO(2)), (5, FNO(3))]
    before = kn_snapshot(A)
    r = kn_drive("zznhon", lines, (A,))
    row("an ordinary session in zznhon (the NET gate on, listed for nfa, a stored login) ran the driver to its end: no hang, nothing malformed, no connection left", kn_sane(r), kn_why(r))
    got = [x for x in r.kr if not x.startswith(("KR begin", "KR end"))]
    row("OPEN 'zznet1' (a VOC record N nfa hcust) succeeds: THEN ran, STATUS() 0 - and FILEINFO(f, FL$OPEN) is 1, FL$VOCNAME is the name opened with (zznet1), "
        "FL$PATH is null (a path on another machine is not shown)", "KR OPEN zznet1 then st=0" in r.kr and "KR FI 0 [1]" in r.kr and "KR FI 1 [zznet1]" in r.kr and "KR FI 2 []" in r.kr,
        repr(got[:3]))
    for rid in ("c1", "c2", "c3", "m1", "big"):
        row("READ of %s through the NET file is exactly the record the fake holds (%d bytes%s)" % (rid, len(RECS[rid]), ", the marks shown" if rid in ("c1", "m1") else ""),
            kn_read_line(rid, RECS[rid]) in r.kr, repr([x for x in r.kr if x.startswith("KR READ %s " % rid)]))
    row("READ of an id the file does not hold takes the ELSE branch with STATUS() 3006 (the local not-found code) and leaves a null record, as a local READ does",
        kn_read_line("nosuch", "", "else", 3006) in r.kr, repr([x for x in r.kr if x.startswith("KR READ nosuch")]))
    row("READV of field 2 is that field alone ('100<V>200'), field 1 is 'Smith', a field beyond the record is null with THEN, and field 0 (the record-exists test) leaves the id in the target",
        all(kn_readv_line(a, b, c) in r.kr for a, b, c in (("c1", 2, fields[1]), ("c1", 1, fields[0]), ("c1", 9, ""), ("c1", 0, "c1"))), repr([x for x in r.kr if x.startswith("KR READV")]))
    row("READV of a record the file does not hold takes the ELSE branch with STATUS() 3006", kn_readv_line("nosuch", 1, "", "else", 3006) in r.kr, repr([x for x in r.kr if x.startswith("KR READV nosuch")]))
    row("MATREAD of c2 fills the array (Jones, 50), and of a missing record takes ELSE with 3006", "KR MATREAD c2 then st=0 [Jones][50][]" in r.kr and "KR MATREAD nosuch else st=3006 [][][]" in r.kr,
        repr([x for x in r.kr if x.startswith("KR MATREAD")]))
    row("FILEINFO answered by the file variable itself: READONLY 1, NON.TXN 1, NETFILE 1, FILENO -1 (there is no file table entry), INDEX.SCAN 0, TXN.UPDATE 0",
        all(x in r.kr for x in ("KR FI 1001 [1]", "KR FI 1032 [1]", "KR FI 1022 [1]", "KR FI 1009 [-1]", "KR FI 1030 [0]", "KR FI 1038 [0]")), repr([x for x in r.kr if x.startswith("KR FI")]))
    row("the whole script printed exactly what was expected, line for line (%d lines)" % len(want), got == want, "first difference: %r" % (next(((a, b) for a, b in zip(got, want) if a != b), (len(got), len(want))),))
    d = r.d[0]
    row("TWO OPENS SHARE THE CONNECTION: the fake saw ONE connection and ONE handshake for three OPENs of two files (one of them twice), the session is alice's in the account 'acct', "
        "files-only, and it ended", d["conns"] == 1 and d["handshakes"] == 1 and len(d["sessions"]) == 1 and d["sessions"][0].user == "alice" and d["sessions"][0].account == "acct"
        and d["sessions"][0].files_only and d["sessions"][0].closed and d["ok"] == 1, repr({k: d[k] for k in ("conns", "handshakes", "ok")}))
    row("...THE REQUESTS, in order, with their bytes: ACCOUNT, OPEN, the READs, the five READVs and the two MATREADs (each a whole READ on the wire), the second and third OPEN, and the CLOSE of "
        "handle 1 SENT AT THE STATEMENT (before the next READ), CLOSE 2, CLOSE 3 - FILEINFO and the refused empty cases sent nothing", kn_wire(d) == W,
        "first difference: %r" % (next(((a, b) for a, b in zip(kn_wire(d), W) if a != b), (len(kn_wire(d)), len(W))),))
    row("...the audit trail has one 'netfile open server=nfa file=<name>' line for each OPEN, in order, and no key, hash, salt or password", r.audits == ["open server=nfa file=hcust", "open server=nfa file=hempty", "open server=nfa file=hcust"]
        and secret_free(r.audit), repr(r.audits))
    row("...and nothing on the fake changed (every record of both files equal)", kn_snapshot(A) == before, "")

    # two servers: each pointer reaches its own
    lines = ["OPEN|1|zznet1", "OPEN|2|zznetb", "READ|1|only_a", "READ|1|only_b", "READ|2|only_b", "READ|2|only_a", "CLOSE|1", "CLOSE|2"]
    r = kn_drive("zznhon", lines, (A, B))
    want = ["KR OPEN zznet1 then st=0", "KR OPEN zznetb then st=0", kn_read_line("only_a", "from A"), kn_read_line("only_b", "", "else", 3006), kn_read_line("only_b", "from B"),
            kn_read_line("only_a", "", "else", 3006), "KR CLOSE 1", "KR CLOSE 2"]
    got = [x for x in r.kr if not x.startswith(("KR begin", "KR end"))]
    row("TWO SERVERS: zznet1 (nfa) and zznetb (nfb) are two connections; each file variable reads its own server's record and not the other's", kn_sane(r) and got == want, kn_why(r) + " got=%r" % got)
    row("...each fake saw ONE connection with ACCOUNT, OPEN, two READs and CLOSE, nothing meant for the other", r.d[0]["conns"] == 1 and r.d[1]["conns"] == 1
        and kn_wire(r.d[0]) == [(3, b"acct"), (4, b"hcust"), (6, FNO(1) + b"only_a"), (6, FNO(1) + b"only_b"), (5, FNO(1))]
        and kn_wire(r.d[1]) == [(3, b"acct"), (4, b"hcust"), (6, FNO(1) + b"only_b"), (6, FNO(1) + b"only_a"), (5, FNO(1))], repr((kn_wire(r.d[0]), kn_wire(r.d[1]))))

    # a loop of 150 opens into one variable: the released handles are queued and sent, so the 100 a process may hold are never reached
    before = kn_snapshot(A)
    r = kn_run("zznhon", ["RUN bp " + KLOOP], (A,))
    d = r.d[0]
    n_open, n_close = d["types"].count(4), d["types"].count(5)
    row("A LOOP OF 150 OPENS into one variable (each OPEN lets the last file variable go): all 150 succeed, none takes ELSE or ON ERROR, and a record is read at the end - the 100 handles "
        "a process may hold are not exhausted", not r.hung and "KR zznkl opened bad=0" in r.kr and "KR zznkl read len=%d" % len(RECS["c1"]) in r.kr and "KR zznkl end" in r.kr, kn_why(r))
    row("...the fake saw 150 OPEN requests and (148 to 150) CLOSE requests - the released handles were sent, the last variable's at the end of the process or not at all (opens %d, closes %d)"
        % (n_open, n_close), n_open == 150 and 148 <= n_close <= 150 and d["conns"] == 1 and set(d["types"]) <= KALLOWED and r.idle, repr(sorted(set(d["types"]))))

    # a transaction: a READ inside it works and FL$TXN.UPDATE is 0
    r = kn_run("zznhon", ["RUN bp " + KTXN], (A,))
    row("a READ inside BEGIN TRANSACTION ... END TRANSACTION works (the NET file is never in the transaction): the record is read and FILEINFO(f, FL$TXN.UPDATE) is 0",
        not r.hung and "KR zznkt read len=%d" % len(RECS["c1"]) in r.kr and "KR zznkt txnupdate=0" in r.kr and "KR zznkt end" in r.kr and r.idle, kn_why(r))
    row("...and after all of these nothing on the fake changed", kn_snapshot(A) == before, "")


def kn_opens_refused(A, B):
    say("\n  -- OPEN refused or failed: ELSE and ON ERROR as for a local failure, and what was dialled --")
    lines = ["OPEN|1|zznetmiss", "OPEN|1|zznetnc", "OPEN|1|zznetcp", "OPEN|1|zznetpin", "OPEN|1|zznetunl", "OPEN|1|zznetup", "FI|1|1", "OPEN|2|zznetsp", "READ|1|c3", "READ|2|c3"]
    lines += ["OPEN|3|" + v for v, _s, _f in KBAD] + ["ODICT|3|zznet1", "ODICT|3|zznetup"]
    before = kn_snapshot(A)
    r = kn_drive("zznhon", lines, (A, B))
    row("the open-failures driver ran to its end and no connection is left", kn_sane(r), kn_why(r))
    op = {}
    for nm, oc, st in kn_opens(r):
        op[nm] = (oc, st)
    row("a pointer to a file the server does not have (N nfa nosuchfile): the ELSE branch with STATUS() 3003 (file not found)", op.get("zznetmiss") == ("else", 3003), repr(op.get("zznetmiss")))
    row("NO STORED LOGIN for the server (N nfnocred ...): refused at OPEN - ON ERROR ran (not THEN, not ELSE) with an error STATUS() (3035 or 7000)",
        op.get("zznetnc", ("", 0))[0] == "error" and op.get("zznetnc", ("", 0))[1] in (3035, 7000), repr(op.get("zznetnc")))
    row("A STORED LOGIN MADE FOR ANOTHER KEY than the definition has now (N nfcpin ...): ON ERROR ran with an error STATUS()", op.get("zznetcp", ("", 0))[0] == "error" and op.get("zznetcp", ("", 0))[1] in (3035, 7000),
        repr(op.get("zznetcp")))
    row("A PIN MISMATCH (N nfpin ...: the server presents key two, the definition holds A's hash): ON ERROR ran with an error STATUS()", op.get("zznetpin", ("", 0))[0] == "error" and op.get("zznetpin", ("", 0))[1] in (3035, 7000),
        repr(op.get("zznetpin")))
    row("AN ACCOUNT NOT IN THE DEFINITION'S LIST (N nfadm ...: listed for nobody who is signed in): ON ERROR with STATUS() 3035 (ER_PERM)", op.get("zznetunl") == ("error", 3035), repr(op.get("zznetunl")))
    row("an upper case pointer (N NFA HCUST) is folded to lower case and opens; a pointer with spaces round both names (N ' nfa ' ' hcust ') opens too; FILEINFO(f, FL$VOCNAME) is the VOC name",
        op.get("zznetup") == ("then", 0) and op.get("zznetsp") == ("then", 0) and "KR FI 1 [zznetup]" in r.kr, repr((op.get("zznetup"), op.get("zznetsp"))))
    row("...both read the record: the file is hcust (the lower case name went to the wire)", kn_read_line("c3", RECS["c3"]) in r.kr and r.kr.count(kn_read_line("c3", RECS["c3"])) == 2, repr([x for x in r.kr if "READ" in x]))
    bad_ok = {v: op.get(v) for v, _s, _f in KBAD}
    row("ALL NINE badly made pointers (a server name starting with a digit, holding a space, empty or 17 characters; a file name empty, with a slash, a space, 64 characters or a semicolon) are "
        "refused in the VOC step: the ELSE branch with STATUS() 3002 (bad file name)", all(v == ("else", 3002) for v in bad_ok.values()), repr(bad_ok))
    row("OPEN 'DICT', 'zznet1' (slice 3d: the dictionary of a remote file is opened as 'dict hcust' on the server) is the THEN branch with STATUS() 0, and so is the dictionary of the upper case pointer",
        "KR ODICT zznet1 then st=0" in r.kr and "KR ODICT zznetup then st=0" in r.kr, repr([x for x in r.kr if x.startswith("KR ODICT")]))
    da, db = r.d
    expect_a = [[47, 48, 3, 4], [47, 48, 3, 4, 4, 6, 6, 4, 5, 4, 5, 5, 5]]
    row("...WHAT WAS DIALLED: server A saw two connections - the first ACCOUNT and OPEN nosuchfile (then the handler's Quit), the second ACCOUNT, OPEN, OPEN, READ, READ, the first dictionary OPEN, the CLOSE "
        "of it that the second one's assignment queued, and the second dictionary OPEN, then (slice 3e: CPROC flushes the queued closes at the prompt, kernel(K$NET, -2)) the three CLOSEs of the file variables the "
        "driver let go, and "
        "nothing else (so no pointer of the refused kind and none of the nine bad ones made a request; a Quit at the end of a connection is not compared)", kn_conns(da) == expect_a, repr(by_conn(da)))
    row("...server B (the pin mismatch) saw one connection and a completed handshake, ZERO request packets and ZERO application bytes: nothing was sent to a server whose key is not the pinned one",
        db["conns"] == 1 and db["handshakes"] == 1 and db["types"] == [] and db["app_bytes"] == 0, repr({k: db[k] for k in ("conns", "handshakes", "types", "app_bytes")}))
    want_audit = ["open server=nfa file=nosuchfile", "refused server=nfnocred reason=credential", "refused server=nfcpin reason=credential", "open server=nfpin file=hcust",
                  "refused server=nfadm reason=list", "open server=nfa file=hcust", "open server=nfa file=hcust", "open server=nfa file=dict hcust", "open server=nfa file=dict hcust"]
    row("...the audit trail has the handler's line for each of the seven pointers that reached it and for the two dictionary opens, in order, and NONE for the nine bad ones (the VOC step refused them "
        "before any gate or handler); nothing secret", r.audits == want_audit and secret_free(r.audit), repr(r.audits))
    row("...and nothing on the fake changed", kn_snapshot(A) == before, "")


def kn_gates(A, B):
    say("\n  -- the NET gate in C, an unlisted account, the pointer an account wrote for itself, the internal program --")
    before = kn_snapshot(A)

    # the gate off
    r = kn_drive("zznhoff", ["OPEN|1|zznet1", "OPEN|2|zznqon"], (A, B))
    op = dict((nm, (oc, st)) for nm, oc, st in kn_opens(r))
    row("THE NET GATE OFF (zznhoff, listed for nfa; the pointer was written by the administrator): OPEN takes ON ERROR with STATUS() 3035 (ER_PERM) and the program goes on", kn_sane(r) and op.get("zznet1") == ("error", 3035), kn_why(r))
    row("...a Q-pointer in zznhoff to zznhon's pointer gives it NOTHING: it is not opened (not THEN)", op.get("zznqon", ("then", 0))[0] in ("error", "else"), repr(op.get("zznqon")))
    row("...NOTHING WAS DIALLED: neither fake saw a connection, a handshake or a byte, and the audit trail says 'refused server=nfa reason=gate' for the pointer",
        all(d["conns"] == 0 and d["handshakes"] == 0 and d["types"] == [] and d["app_bytes"] == 0 for d in r.d) and "refused server=nfa reason=gate" in r.audits and secret_free(r.audit),
        repr((r.audits, [d["conns"] for d in r.d])))

    # the abort form, gate off and unlisted: the kernel's own message
    r = kn_run("zznhoff", ["RUN bp " + KGATE], (A, B))
    seg = kn_segments(r.out).get("g", [])
    row("the same OPEN without ON ERROR stops the program with message 11460 (%r) and prints nothing after it" % msg(11460, "zznhoff"), not r.hung and kn_abort(seg) == msg(11460, "zznhoff") and not any("SURVIVED" in x for x in seg)
        and all(d["conns"] == 0 for d in r.d), repr(seg))
    r = kn_run("zznhunl", ["RUN bp " + KGATE], (A, B))
    seg = kn_segments(r.out).get("g", [])
    row("AN ACCOUNT NOT IN THE LIST (zznhunl: the gate on, nfa lists zznhon and zznhoff): without ON ERROR the program stops with message 11461 (%r), nothing is dialled"
        % msg(11461, "zznhunl", "nfa"), not r.hung and kn_abort(seg) == msg(11461, "zznhunl", "nfa") and not any("SURVIVED" in x for x in seg) and all(d["conns"] == 0 for d in r.d), repr(seg))
    r = kn_drive("zznhunl", ["OPEN|1|zznet1"], (A, B))
    row("...and with ON ERROR: STATUS() 3035, the audit trail has 'refused server=nfa reason=list'", kn_sane(r) and ("zznet1", "error", 3035) in kn_opens(r) and r.audits == ["refused server=nfa reason=list"]
        and all(d["conns"] == 0 for d in r.d), kn_why(r))

    # the edit gate: a pointer an account writes into its own VOC
    r = kn_run("zznhnov", ["RUN bp " + KVOC], (A,))
    seg = kn_segments(r.out).get("v", [])
    row("CONTROL (the edit gate): an account WITHOUT voc.edit writes a pointer into its own VOC and is REFUSED, the record is not there afterwards (P=0), and opening it is the ELSE branch - nothing dialled",
        not r.hung and "KR v write REFUSED P=0" in seg and any(x.startswith("KR v open else") for x in seg) and "KR v end" in seg and r.d[0]["conns"] == 0, repr(seg))
    r = kn_run("zznhoff", ["RUN bp " + KVOC], (A,))
    seg = kn_segments(r.out).get("v", [])
    row("AN ACCOUNT WITH voc.edit AND NO NET GATE writes the pointer (P=1) and cannot make it work: OPEN is ON ERROR with STATUS() 3035 and the fake saw no connection - a VOC entry an account "
        "wrote for itself gives it nothing it was not granted", not r.hung and "KR v write OK P=1" in seg and "KR v open error st=3035" in seg and "KR v end" in seg and r.d[0]["conns"] == 0
        and "refused server=nfa reason=gate" in r.audits, repr(seg))
    r = kn_run("zznhon", ["RUN bp " + KVOC], (A,))
    seg = kn_segments(r.out).get("v", [])
    row("CONTROL: the account with both gates writes its own pointer and opens it: the record is read (the same pointer, from an ordinary program)",
        not r.hung and "KR v write OK P=1" in seg and "KR v open then st=0" in seg and "KR v read len=%d" % len(RECS["c1"]) in seg and r.idle, repr(seg))

    # an $internal program is not exempt from the gate
    r = kn_run("zznhoff", ["ZZNKI"], (A,))
    seg = kn_segments(r.out).get("ki", [])
    row("AN $INTERNAL PROGRAM IS NOT EXEMPT (the S.63 lesson): the verb ZZNKI, catalogued $internal, run in zznhoff (gate off), opens the pointer and takes ON ERROR with STATUS() 3035; nothing dialled",
        not r.hung and "KR ki open error st=3035" in seg and "KR ki end" in seg and r.d[0]["conns"] == 0, repr(seg))
    r = kn_run("zznhon", ["ZZNKI"], (A,))
    seg = kn_segments(r.out).get("ki", [])
    row("CONTROL: the same internal program in zznhon (gate on) opens it and reads the record", not r.hung and "KR ki open then st=0" in seg and "KR ki read len=%d" % len(RECS["c1"]) in seg and r.idle, repr(seg))
    r = kn_run("zznhon", ["ZZNKJ"], (A,))
    seg = kn_segments(r.out).get("kj", [])
    row("GETLOCKS(f, '') on a NET file from an internal program (S.72, 20 Oct 26: it was refused with 11501 until then) is the LOCAL view: the program goes on and gets ONE field of three numbers "
        "(NUMLOCKS, the current record lock count, the peak) and no lock line - without the special case file_id -1 would mean ALL FILES and list every lock of every user",
        not r.hung and kn_abort(seg) is None and "KR kj SURVIVED fields=1 values=3 numeric=1 null=0" in seg, repr(seg))
    row("...and the fake was asked nothing for it: not a request after the OPEN and the CLOSE", all(set(d["types"]) <= {47, 48, 3, 4, 5, 1} for d in r.d), repr([d["types"] for d in r.d]))

    # LOGTO: the handle does not follow the user
    lines = ["OPEN|1|zznet1", "READ|1|c1", "EXEC|LOGTO zznhunl", "READ|1|c1", "OPEN|2|zznet1", "CLOSE|1"]
    r = kn_drive("zznhon", lines, (A,))
    got = [x for x in r.kr if not x.startswith(("KR begin", "KR end"))]
    row("A FILE VARIABLE DOES NOT SURVIVE A LOGTO: after LOGTO zznhunl a READ on the variable opened in zznhon is an ERROR (ON ERROR ran, STATUS() 7000, 'no remote file is open with handle'), and an OPEN there "
        "of the same pointer is refused (not in the list: 3035)", kn_sane(r) and got[:2] == ["KR OPEN zznet1 then st=0", kn_read_line("c1", RECS["c1"])] and kn_read_line("c1", "", "error", 7000) in got
        and "KR OPEN zznet1 error st=3035" in got, kn_why(r) + " got=%r" % got)
    row("...the first account's variable can still be closed (CLOSE ran), and the process ended with its connection closed", "KR CLOSE 1" in r.kr and r.idle, repr(r.kr[-3:]))
    row("...the fake never saw a request for the account zznhunl: one connection, ACCOUNT acct only once", r.d[0]["conns"] == 1 and kn_wire(r.d[0])[:3] == [(3, b"acct"), (4, b"hcust"), (6, FNO(1) + b"c1")], repr(kn_wire(r.d[0])[:4]))
    row("...and nothing on the fake changed", kn_snapshot(A) == before, "")

    # LOGTO drops the connections (18 Oct 26: the NET gate is reloaded at LOGTO, and the kernel key that sets it calls net_close_all()): going to another account
    # and BACK to the first is not a way to keep a file variable - it is an ERROR on return, the connection of the first visit is closed, and a new OPEN dials again
    r = kn_drive("zznhon", ["OPEN|1|zznet1", "READ|1|c1", "EXEC|LOGTO zznhunl", "EXEC|LOGTO zznhon", "READ|1|c1", "OPEN|2|zznet1", "READ|2|c1", "CLOSE|2"], (A,))
    got = [x for x in r.kr if not x.startswith(("KR begin", "KR end"))]
    d = r.d[0]
    row("LOGTO DROPS THE CONNECTIONS: out to zznhunl and back to zznhon, a READ on the variable opened before is an ERROR (STATUS() 7000), while a new OPEN works and reads c1 - "
        "and the fake saw TWO connections, the first one ended by LOGTO's CLOSEALL (it holds no session after the second connection began)",
        kn_sane(r) and kn_read_line("c1", "", "error", 7000) in got and got.count(kn_read_line("c1", RECS["c1"])) == 2 and "KR OPEN zznet1 then st=0" in got and d["conns"] == 2
        and len(d["sessions"]) == 2 and all(s.closed for s in d["sessions"]), kn_why(r) + " got=%r conns=%s" % (got, d["conns"]))
    row("...and nothing on the fake changed", kn_snapshot(A) == before, "")


def kn_matrix(A):
    say("\n  -- THE REFUSAL MATRIX: every other statement given an open NET file variable --")
    matrix = KN["matrix"]
    a_names = sorted(n for n, (_t, k, _i) in matrix.items() if k == "A")
    e_names = sorted(n for n, (_t, k, _i) in matrix.items() if k == "E")
    before = kn_snapshot(A)
    c1len = len(RECS["c1"])

    # --- A: no ON ERROR.  One session runs every program; each aborts and the next RUN goes on.
    xs = ["zznkx1", "zznkx2", "zznkx3"]
    r = kn_run("zznhon", ["RUN bp " + n for n in a_names + xs], (A,))
    segs = kn_segments(r.out)
    row("the %d no-ON-ERROR programs and the three path programs ran in ONE session, each aborting and the next going on: every program printed its begin line, the session did not hang, no connection is left"
        % len(a_names), not r.hung and r.idle and all(KM[matrix[n][2]][0] in segs for n in a_names) and all(t in segs for t in ("oseq", "opath", "callfile")),
        "missing: %r hung=%s" % ([KM[matrix[n][2]][0] for n in a_names if KM[matrix[n][2]][0] not in segs][:6], r.hung))
    for n in a_names:
        tag, _pre, _a, _e, want, _st = KM[matrix[n][2]]
        seg = segs.get(tag, [])
        texts = [msg(num, "nfa", arg) for num, arg in want]
        got = kn_abort(seg)
        opened = not any("openfail" in x for x in seg)
        row("%s on a NET file WITHOUT ON ERROR: the program stops with %r and prints nothing after it" % (tag.upper(), texts[0] if len(texts) == 1 else texts),
            opened and got in texts and not any("SURVIVED" in x for x in seg), repr(seg[-3:]))
    seg = segs.get("oseq", [])
    row("OPENSEQ 'zznet1', 'c1' (the VOC name of a NET file used for a sequential file) is not THEN: the encoded path is no path (ELSE, a status shown: %s), the program goes on"
        % ([x for x in seg if "ELSE" in x][:1]), "KR oseq THEN" not in seg and "KR oseq end" in seg, repr(seg))
    seg = segs.get("opath", [])
    row("OPENPATH of the encoded string typed by the program (char(1) 'N' char(1) nfa char(1) hcust) is not THEN: OPENPATH never looks for the encoded form", "KR opath THEN" not in seg and "KR opath end" in seg, repr(seg))
    seg = segs.get("callfile", [])
    row("CALL 'zznet1 zzprog' (CALL \"file program\" through the NET VOC name) does not run anything: the program stopped (an abort line, no SURVIVED)", kn_abort(seg) is not None and not any("SURVIVED" in x for x in seg), repr(seg))
    types = set(r.d[0]["types"])
    row("...A: THE FAKE SAW NO WRITE, DELETE, CLEAR, LOCK, SELECT OR RECORD-LOCKED REQUEST: of everything the %d programs did, its packet log holds only login, account, open, close and quit (request types seen: %s)"
        % (len(a_names) + 3, sorted(types)), types and types <= KALLOWED - {6} and r.d[0]["types"].count(4) >= 1, repr(sorted(types - KALLOWED)))
    row("...A: the records on the fake are exactly what they were (both files)", kn_snapshot(A) == before, "")

    # --- E: ON ERROR
    r = kn_run("zznhon", ["RUN bp " + n for n in e_names], (A,))
    segs = kn_segments(r.out)
    row("the %d ON ERROR programs ran in one session and no connection is left" % len(e_names), not r.hung and r.idle and all(KM[matrix[n][2]][0] in segs for n in e_names), "hung=%s idle=%s" % (r.hung, r.idle))
    for n in e_names:
        tag, _pre, _a, _e, want, st = KM[matrix[n][2]]
        seg = segs.get(tag, [])
        m = next((re.match(r"^KR %s st=(\d+)$" % re.escape(tag), x) for x in seg if re.match(r"^KR %s st=(\d+)$" % re.escape(tag), x)), None)
        good = (m is not None and int(m.group(1)) == st and "KR %s back len=%d" % (tag, c1len) in seg and "KR %s end" % tag in seg and kn_abort(seg) is None)
        extra = ""
        row("%s on a NET file WITH ON ERROR: the ON ERROR clause ran and STATUS() was %d, the program went on, read a record from the same file afterwards (%d bytes) and reached its end%s"
            % (tag.upper(), st, c1len, extra), good, repr(seg))
    types = set(r.d[0]["types"])
    row("...E: THE FAKE SAW ONLY login, account, open, close, read and quit (request types seen: %s) - not one write, delete, clear, lock, select or record-locked request" % sorted(types),
        types and types <= KALLOWED and r.d[0]["types"].count(6) >= len(e_names), repr(sorted(types - KALLOWED)))
    row("...E: the records on the fake are exactly what they were, and the session held no lock on the fake", kn_snapshot(A) == before and all(A.store.locks_of(s.userno) == [] for s in r.d[0]["sessions"]), "")


def kn_verbs(A):
    say("\n  -- the verbs on the VOC name: the session survives, the fake sees nothing it must not, the data is unchanged --")
    before = kn_snapshot(A)
    for cmd, extra, num in KVERBS:
        r = kn_run("zznhon", [cmd] + extra + ["RUN bp " + KSENT], (A,))
        shown = [x for x in r.out if not x.startswith("KR ")][:3]
        say("    [note] %s -> %r" % (cmd, shown))
        types = set(r.d[0]["types"])
        row("%s: the session survived (the next command ran), the fake saw only login, account, open, read, close and quit%s, and the data on the fake is unchanged"
            % (cmd, "" if num is None else ", and the verb refused with its own text (message %d: %r)" % (num, msg(num, "zznet1"))),
            not r.hung and "KR sent" in r.kr and types <= KALLOWED and r.idle and kn_snapshot(A) == before and (num is None or any(msg(num, "zznet1") in ln for ln in r.out)),
            "hung=%s sent=%s types=%s out=%r" % (r.hung, "KR sent" in r.kr, sorted(types - KALLOWED), r.out[:6]))


KQALLOWED = KALLOWED | {11, 14}                       # slice 3d: and the two requests a SELECT makes (select, then readlist)
KQ_RX = re.compile(r"^KR (SELECT|SELECTV|SSELECT) (\S+) st=(\d+) n=(\d+) ids=\[(.*)\]$")


def kn_sel(r):
    """The SELECT / SELECTV / SSELECT lines the driver printed: [(verb, outcome, status, count, [ids in the order READNEXT gave them])]."""
    out = []
    for ln in r.kr:
        m = KQ_RX.match(ln)
        if m:
            out.append((m.group(1), m.group(2), int(m.group(3)), int(m.group(4)), m.group(5).split(",") if m.group(5) else []))
    return out


def kn_query(A, B):
    say("\n  -- slice 3d: SELECT, SELECTV and SSELECT of a remote file, FILEINFO, its dictionary, and the query verbs on the VOC name --")
    all_ids = sorted(A.store.records(HFILE))
    before = kn_snapshot(A)
    r = kn_drive("zznhon", ["OPEN|1|zznet1", "OPEN|2|zznetempty", "SELECT|1|2", "SELECT|2|3", "SELECTV|1|0", "SSELECT|1|4", "SELECT|1|2", "SELECT|2|2", "CLOSE|1", "CLOSE|2"], (A,))
    sel = kn_sel(r)
    say("    [note] the driver printed %r" % [x[:120] for x in r.kr])
    row("the SELECT driver ran to its end, nothing is left open, and no fake saw anything malformed", kn_sane(r) and not r.crash, kn_why(r))
    row("SELECT zznet1 TO 2: THEN, STATUS() 0, @SELECTED %d, and READNEXT gives every id of the remote file once (%s) - the ORDER is the fake's" % (len(all_ids), ",".join(all_ids)),
        len(sel) >= 1 and sel[0][:4] == ("SELECT", "then", 0, len(all_ids)) and sorted(sel[0][4]) == all_ids and len(set(sel[0][4])) == len(all_ids), repr(sel[:1]))
    row("SELECT of the empty remote file: THEN, STATUS() 0, @SELECTED 0, READNEXT takes ELSE at once", len(sel) >= 2 and sel[1] == ("SELECT", "then", 0, 0, []), repr(sel[1:2]))
    row("SELECTV zznet1 TO a variable gives the same ids and the same count", len(sel) >= 3 and sel[2][:4] == ("SELECTV", "then", 0, len(all_ids)) and sorted(sel[2][4]) == all_ids, repr(sel[2:3]))
    row("SSELECT zznet1 TO 4 gives them SORTED by id (SD's order: %s); STATUS() after an SSELECT is the count, as for a local file" % ",".join(all_ids),
        len(sel) >= 4 and sel[3][:4] == ("SSELECT", "then", len(all_ids), len(all_ids)) and sel[3][4] == all_ids, repr(sel[3:4]))
    row("SELECT into list 2 AGAIN gives the same ids (nothing doubled), and a SELECT of the empty file into list 2 afterwards EMPTIES it: the new ids replace the old list",
        len(sel) >= 6 and sorted(sel[4][4]) == all_ids and len(sel[4][4]) == len(all_ids) and sel[5] == ("SELECT", "then", 0, 0, []), repr(sel[4:6]))
    d = r.d[0]
    types = d["types"]
    row("...THE FAKE SAW only login, account, open, close, select and readlist (request types seen: %s): SIX selects (the empty file's two included), each followed by its READLIST, and nothing that writes, "
        "locks or reads a record" % sorted(set(types)), set(types) <= KQALLOWED and types.count(11) == 6 and types.count(14) == 6 and types.count(6) == 0, repr((sorted(set(types)), types.count(11), types.count(14))))
    row("...and nothing on the fake changed", kn_snapshot(A) == before, "")

    # FILEINFO: the three keys the query processor asks, from the file variable, nothing dialled for them
    r = kn_drive("zznhon", ["OPEN|1|zznet1", "FI|1|3", "FI|1|1035", "IDX|1", "IDX2|1", "CLOSE|1"], (A,))
    row("FILEINFO(f, FL$TYPE) is 7 (FL$TYPE.NET) and FL$COLLECTION is 0; INDICES(f) and INDICES(f, name) are the null string (the query processor asks both of every file); no request but the open and the "
        "close went to the server", kn_sane(r) and "KR FI 3 [7]" in r.kr and "KR FI 1035 [0]" in r.kr and "KR IDX []" in r.kr and "KR IDX2 []" in r.kr and set(r.d[0]["types"]) <= KALLOWED
        and r.d[0]["types"].count(6) == 0, kn_why(r))
    r = kn_run("zznhon", ["ZZNKI"], (A,))
    seg = kn_segments(r.out).get("ki", [])
    row("...and an $internal program gets FL$FLAGS 16 (DHF_NOCASE: every hashed file is NOCASE), type 7 and coll 0", not r.hung and "KR ki flags=16 type=7 coll=0" in seg, repr(seg))

    # the record cache (18 Oct 26): a READ answered a moment ago is not asked again
    def reads(run):
        return run.d[0]["types"].count(6)

    r = kn_drive("zznhon", ["OPEN|1|zznet1", "READ|1|c1", "READ|1|c1", "READ|1|c1", "READ|1|nosuch", "READ|1|nosuch", "READ|1|big", "READ|1|big", "CLOSE|1"], (A,))
    row("THE RECORD CACHE: three READs of c1 are ONE request, two READs of an id the server does not have are ONE request, and every answer is the same (the record each time, ELSE with STATUS() 3006 each time); "
        "a 70,000 byte record is over the limit and is asked for twice - 4 read requests in all",
        kn_sane(r) and r.kr.count(kn_read_line("c1", RECS["c1"])) == 3 and [x for x in r.kr if x.startswith("KR READ nosuch")] == ["KR READ nosuch else st=3006 len=0 rec=[]"] * 2
        and r.kr.count(kn_read_line("big", RECS["big"])) == 2 and reads(r) == 4, "reads=%d %s" % (reads(r), kn_why(r)))
    r = kn_drive("zznhon", ["OPEN|1|zznet1", "READ|1|c1", "SELECT|1|2", "READ|1|c1", "CLOSE|1", "OPEN|1|zznet1", "READ|1|c1", "CLOSE|1"], (A,))
    row("...a SELECT of the file, and a CLOSE and a new OPEN, each start the cache again: READ, SELECT, READ, CLOSE, OPEN, READ is THREE read requests",
        kn_sane(r) and r.kr.count(kn_read_line("c1", RECS["c1"])) == 3 and reads(r) == 3, "reads=%d %s" % (reads(r), kn_why(r)))
    r = kn_drive("zznhon", ["OPEN|1|zznet1", "READ|1|c1", "SLEEP|3", "READ|1|c1", "READ|1|c1", "CLOSE|1"], (A,))
    row("...an entry is kept for 2 seconds: READ, three seconds later READ, READ is TWO read requests (the second READ sees what the server holds NOW)",
        kn_sane(r) and r.kr.count(kn_read_line("c1", RECS["c1"])) == 3 and reads(r) == 2, "reads=%d %s" % (reads(r), kn_why(r)))
    r = kn_drive("zznhon", ["OPEN|1|zznet1", "OPEN|2|zznet1", "ODICT|3|zznet1", "READ|1|c1", "READ|2|c1", "READ|3|name", "READ|1|name", "CLOSE|1", "CLOSE|2", "CLOSE|3"], (A,))
    row("...an entry belongs to ONE file variable: two opens of the same file each ask once, and the dictionary's 'name' and the data file's 'name' (absent there) are two requests - 4 in all",
        kn_sane(r) and reads(r) == 4 and kn_read_line("name", DICT_ITEMS["name"]) in r.kr and "KR READ name else st=3006 len=0 rec=[]" in r.kr, "reads=%d %s" % (reads(r), kn_why(r)))

    # the dictionary
    r = kn_drive("zznhon", ["OPEN|1|zznet1", "ODICT|2|zznet1", "READ|2|name", "READ|2|bal", "READ|2|nosuch", "READV|2|name|2", "FI|2|1", "FI|2|3", "SELECT|2|2", "CLOSE|2", "CLOSE|1"], (A,))
    dsel = kn_sel(r)
    row("OPEN 'DICT', 'zznet1' opens the dictionary of the remote file: its items READ (name, bal), an item that is not there takes ELSE with STATUS() 3006, READV cuts a field",
        kn_sane(r) and "KR ODICT zznet1 then st=0" in r.kr and kn_read_line("name", DICT_ITEMS["name"]) in r.kr and kn_read_line("bal", DICT_ITEMS["bal"]) in r.kr
        and any(ln.startswith("KR READ nosuch else") for ln in r.kr) and kn_readv_line("name", 2, "1") in r.kr, kn_why(r))
    row("...SELECT of the dictionary file variable gives the dictionary's own ids (%s), not the data file's" % ",".join(sorted(DICT_ITEMS)),
        len(dsel) == 1 and dsel[0][:3] == ("SELECT", "then", 0) and sorted(dsel[0][4]) == sorted(DICT_ITEMS), repr(dsel))
    row("...the audit trail names the dictionary open ('open server=nfa file=dict hcust'), and the data file is a different open", "open server=nfa file=dict hcust" in r.audits and "open server=nfa file=hcust" in r.audits, repr(r.audits))
    r = kn_drive("zznhoff", ["ODICT|1|zznet1"], (A, B))
    row("THE NET GATE applies to the dictionary: in the account without it OPEN 'DICT' takes ON ERROR with STATUS() 3035 and nothing is dialled",
        kn_sane(r) and "KR ODICT zznet1 error st=3035" in r.kr and all(d["conns"] == 0 for d in r.d) and "refused server=nfa reason=gate" in r.audits, kn_why(r))

    # the query verbs, typed at the command prompt: the dictionary, the select and the records all come from the server
    def tcl(cmd):
        r = kn_run("zznhon", [cmd, "RUN bp " + KSENT], (A,))
        shown = [x for x in r.out if not x.startswith("KR ")]
        say("    [note] %s -> %r" % (cmd, shown[:6]))
        say("    [note] requests for it: %s (4 open, 5 close, 6 read, 11 select, 14 readlist)" % {t: r.d[0]["types"].count(t) for t in sorted(set(r.d[0]["types"])) if t not in (1, 47, 48, 3)})
        return r, shown

    def clean(r, shown):
        return (not r.hung and "KR sent" in r.kr and not r.crash and r.idle and set(r.d[0]["types"]) <= KQALLOWED and kn_snapshot(A) == before
                and not any(re.search(r"not answered|cannot open|not found|Unexpected|corrupt|free", x, re.I) for x in shown))

    r, shown = tcl("COUNT zznet1")
    row("COUNT zznet1: the session goes on, the count is %d, the query asked the server for a select" % len(all_ids),
        clean(r, shown) and any(re.search(r"\b%d\b" % len(all_ids), x) for x in shown) and r.d[0]["types"].count(11) >= 1, repr(shown[:6]))
    r, shown = tcl('LIST zznet1 NAME WITH NAME = "Smith"')
    row("LIST zznet1 NAME WITH NAME = \"Smith\": one row, c1 and Smith, and not Jones or Brown (the dictionary came from the server, the records were read from it)",
        clean(r, shown) and any("c1" in x and "Smith" in x for x in shown) and not any("Jones" in x or "Brown" in x for x in shown) and r.d[0]["types"].count(6) >= 1, repr(shown[:8]))
    r, shown = tcl('SORT zznet1 BY NAME NAME WITH NAME = "Brown" OR WITH NAME = "Jones" OR WITH NAME = "Smith"')
    pos = [next((i for i, x in enumerate(shown) if w in x), -1) for w in ("Brown", "Jones", "Smith")]
    row("SORT zznet1 BY NAME ...: Brown, Jones, Smith, in that order", clean(r, shown) and -1 not in pos and pos == sorted(pos), repr((pos, shown[:10])))
    r, shown = tcl('SELECT zznet1 WITH NAME = "Jones"')
    row("SELECT zznet1 WITH NAME = \"Jones\": one record selected and the session goes on", clean(r, shown) and any(re.search(r"\b1 record", x) for x in shown), repr(shown[:6]))
    r, shown = tcl('LIST zznet1 NAME WITH NAME = "Nobody"')
    row("LIST zznet1 ... WITH NAME = \"Nobody\": no records, the session goes on", clean(r, shown) and not any("c1" in x or "Smith" in x for x in shown), repr(shown[:6]))
    r, shown = tcl("LIST DICT zznet1")
    row("LIST DICT zznet1 lists the dictionary of the remote file: both items, name and bal", clean(r, shown) and any("name" in x for x in shown) and any("bal" in x for x in shown), repr(shown[:8]))
    r, shown = tcl("LIST zznet1 'c2' NAME")
    row("LIST zznet1 'c2' NAME: an id given on the command line is read, not selected (no select request), and the row shows Jones",
        clean(r, shown) and any("Jones" in x for x in shown) and r.d[0]["types"].count(11) == 0, repr((shown[:6], r.d[0]["types"].count(11))))


def kn_after(A):
    say("\n  -- after all of it --")
    before = kn_snapshot(A)
    r = kn_drive("zznhon", ["OPEN|1|zznet1", "READ|1|c1", "CLOSE|1"], (A,))
    row("THE POINTER STILL WORKS: the VOC record zznet1 is intact after every verb and the refusals (DELETE.FILE and CLEAR.FILE did not remove or empty anything), the file still opens and reads",
        kn_sane(r) and kn_read_line("c1", RECS["c1"]) in r.kr, kn_why(r))
    row("...and the records on the fake are what they were when the section began", kn_snapshot(A) == before and A.store.records(HFILE).get("c1") == RECS["c1"], "")
    row("NO SESSION OF THE KERNEL SECTION ENDED IN A CRASH: not one printed a double free, a corruption, a fatal signal or an abort (a session that opened a remote file once died at exit with a "
        "double free, after every row had its answer; the class objects the handler keeps in common ran their destroy code on a freed e-stack)", not KN.get("crashes"), repr(KN.get("crashes")))


# ---- K2. the kernel on a WRITE-mode file: real statements (S.65 slice 3e, section kwrite) -----------------------------------------------------------
#
# An ORDINARY session's OPEN statement names a VOC record of type N whose server is nfw (mode write).  The statements WRITE, WRITEU, MATWRITE, WRITEV, WRITEVU, DELETE, DELETEU,
# CLEARFILE, READU, READL, MATREADU, MATREADL, READVU, READVL, RECORDLOCKU, RECORDLOCKL and RELEASE are then SENT to the server (through the kernel's net_gate and net_write ...,
# and the handler).  THE FAKE IS THE WITNESS, as in hwrite: its packet log (what was sent, in order, byte for byte), its store (what was done) and its lock table.  The lock
# table is watched DURING a session by a thread that polls it every 50 ms (LockWatch) while the driver SLEEPs a second between statements, so that the lock a statement took is
# seen while it is held and not only the empty table after the session ended.  A record that is busy (held by a user number the test made up: store.hold) is waited for by the
# kernel, which polls with lock requests every 250 ms - the fake must see lock requests and NO read until the holder lets go (HolderRelease does that, a fixed time after the
# first lock request).  The driver zznk2 prints "KW <op> <id> <outcome> st=<STATUS()> ..." for each statement: the outcome is which of THEN, ELSE, LOCKED and ON ERROR ran.
# STATUS() after an ON ERROR is the positive number (abs).  The S.64 gates are tried in three accounts: zznhon (all on), zznhnov (voc.edit off) and zznhned (all three off).
# The read-mode control is the existing sections (the refusal matrix KM), which stand unchanged on nfa.
#
# WHAT IT CANNOT SHOW.  (1) That the break key ends a wait. (2) The 5 minute CLEARFILE bound. (3) COLL values written to a remote file (no collection is made here).
# (4) The cost of the handler asking the definitions file at every change.

KW = {}                                                    # what the section made
KWDRV = "zznk2"                                            # the input driven program
KWALLOWED = {47, 48, 3, 4, 5, 6, 1, 15, 16, 17, 18, 19, 30, 31, 34}      # the requests a write-mode session of these rows may send: ours plus RECORDLOCKED (MUSTLOCK)
KW_PTRS = (("zznw1", "nfw", HW), ("zznwb", "nfwb", HW), ("zznwr", "nfa", HW), ("zznwbp", "nfw", HWBP), ("zznwvoc", "nfw", HWVOC), ("zznwnc", "nfw", HWNC))
KW_EO = "on error oc = 'error'"
KW_LK = " locked oc = 'locked'"
KW_EL = " else oc = 'else'"
# the statements the driver runs: name -> (lines before, the statement with {f} for the file variable, how the outcome is shown)
KW_STMTS = {
    "OPEN": ([], "open a3 to {f} " + KW_EO + KW_EL, "plain"),
    "ODICT": ([], "open 'DICT', a3 to {f} " + KW_EO + KW_EL, "plain"),
    "READ": ([], "read rec from {f}, a3 " + KW_EO + KW_EL, "rec"),
    "READU": ([], "readu rec from {f}, a3 " + KW_EO + KW_LK + KW_EL, "rec"),
    "READL": ([], "readl rec from {f}, a3 " + KW_EO + KW_LK + KW_EL, "rec"),
    "READUW": ([], "readu rec from {f}, a3 " + KW_EO + KW_EL, "rec"),                  # no LOCKED clause: a busy record is waited for
    "READLW": ([], "readl rec from {f}, a3 " + KW_EO + KW_EL, "rec"),
    "READVU": (["fld = a4 + 0"], "readvu rec from {f}, a3, fld " + KW_EO + KW_LK + KW_EL, "rec"),
    "READVL": (["fld = a4 + 0"], "readvl rec from {f}, a3, fld " + KW_EO + KW_LK + KW_EL, "rec"),
    "READVUW": (["fld = a4 + 0"], "readvu rec from {f}, a3, fld " + KW_EO + KW_EL, "rec"),
    "MATREADU": ([], "matreadu m from {f}, a3 " + KW_EO + KW_LK + KW_EL, "mat"),
    "MATREADL": ([], "matreadl m from {f}, a3 " + KW_EO + KW_LK + KW_EL, "mat"),
    "WRITE": ([], "write a4 to {f}, a3 " + KW_EO, "plain"),
    "WRITEU": ([], "writeu a4 to {f}, a3 " + KW_EO, "plain"),
    "MATWRITE": (["mw(1) = field(a4, @fm, 1)", "mw(2) = field(a4, @fm, 2)"], "matwrite mw to {f}, a3 " + KW_EO, "plain"),
    "WRITEV": (["fld = a5 + 0"], "writev a4 to {f}, a3, fld " + KW_EO, "plain"),
    "WRITEVU": (["fld = a5 + 0"], "writevu a4 to {f}, a3, fld " + KW_EO, "plain"),
    "DELETE": ([], "delete {f}, a3 " + KW_EO, "plain"),
    "DELETEU": ([], "deleteu {f}, a3 " + KW_EO, "plain"),
    "CLEARFILE": ([], "clearfile {f} " + KW_EO, "plain"),
    "RLOCKU": ([], "recordlocku {f}, a3 " + KW_EO + KW_LK, "plain"),
    "RLOCKL": ([], "recordlockl {f}, a3 " + KW_EO + KW_LK, "plain"),
    "RLOCKUW": ([], "recordlocku {f}, a3 " + KW_EO, "plain"),
    "RELEASE": ([], "release {f}, a3", "plain"),
    "RELEASEF": ([], "release {f}", "plain"),
    "RELEASEA": ([], "release", "plain"),
    # S.72 (20 Oct 26): FILELOCK with a LOCKED clause, without one (a busy file is waited for), FILEUNLOCK, and RECORDLOCKED() whose value and STATUS() are printed
    "FLOCK": ([], "filelock {f} " + KW_EO + KW_LK, "plain"),
    "FLOCKW": ([], "filelock {f} " + KW_EO, "plain"),
    "FUNLOCK": ([], "fileunlock {f} " + KW_EO, "plain"),
    "RLCKD": ([], "x = recordlocked({f}, a3)", "x"),
    "CLOSE": ([], "close {f}", "close"),
    "FI": (["fkey = a3 + 0"], "x = fileinfo({f}, fkey)", "fi"),
}
KW_TXN_OPS = ("WRITE", "WRITEU", "MATWRITE", "WRITEV", "WRITEVU", "DELETE", "DELETEU", "CLEARFILE", "READ", "READU", "READL", "READVU", "MATREADU", "RLOCKU", "RLOCKL", "RELEASE", "RELEASEF",
              "FLOCK", "FUNLOCK", "RLCKD")


def kw_show(name, kind):
    """The lines that print the outcome of a statement; tid is the id as it was TYPED (place holders and all), never the marks themselves."""
    if kind == "rec":
        return ["v = rec ; gosub shw", "crt 'KW %s ':tid:' ':oc:' st=':st:' len=':len(rec):' rec=[':sv:']'" % name]
    if kind == "mat":
        return ["crt 'KW %s ':tid:' ':oc:' st=':st:' [':m(1):'][':m(2):'][':m(3):']'" % name]
    if kind == "close":
        return ["crt 'KW %s ':slot" % name]
    if kind == "fi":
        return ["v = x ; gosub shw", "crt 'KW %s ':tid:' [':sv:']'" % name]
    if kind == "x":
        return ["crt 'KW %s ':tid:' x=':x:' st=':st" % name]
    return ["crt 'KW %s ':tid:' ':oc:' st=':st" % name]


def kw_case(name, pre, stmt, kind, txn=False):
    """One case of the driver: the statement once for each of the four file variables (the slot picks one); inside a transaction when TXN, then the lines that print."""
    shown = ("T" if txn else "") + name
    out = ["         case op = '%s'" % shown] + ["            " + p for p in pre]
    pad = "               " if txn else "            "
    if txn:
        out.append("            begin transaction")
    out.append(pad + "begin case")
    for n in range(1, KSLOTS + 1):
        out.append(pad + "   case slot = %d" % n)
        out.append(pad + "      " + stmt.replace("{f}", "f%d" % n))
        out.append(pad + "      st = status()")
    out.append(pad + "end case")
    if txn:
        out += ["               rollback", "            end transaction"]
    return out + ["            " + s for s in kw_show(shown, kind)]


def kw_driver():
    L = ["$include err.h", "   dim m(4)", "   dim mw(2)"] + ["   f%d = ''" % n for n in range(1, KSLOTS + 1)]
    L += ["   x = ''", "   fkey = 0", "   v = ''", "   sv = ''", "   tid = ''", "   rec = ''"]                    # assigned first for BCOMP: a warning fails the bootstrap
    L += ["   crt 'KW begin'", "   done = @false", "   loop", "      input ln", "      done = (ln = 'END') or (ln = '' and status() = ER$EOF)", "   until done do",
          "      op = field(ln, '|', 1)", "      a2 = field(ln, '|', 2)", "      a3 = field(ln, '|', 3)", "      a4 = field(ln, '|', 4)", "      a5 = field(ln, '|', 5)", "      tid = a3"]
    for v in ("a3", "a4"):
        for ph, mk in (("<I>", "@im"), ("<F>", "@fm"), ("<V>", "@vm"), ("<S>", "@sm")):
            L.append("      %s = change(%s, '%s', %s)" % (v, v, ph, mk))
    L += ["      slot = 0", "      if op # 'EXEC' and op # 'SLEEP' and op # 'TIME' then slot = a2 + 0", "      oc = 'then'", "      rec = ''", "      st = 0", "      fld = 0",
          "      mat m = ''", "      mat mw = ''", "      begin case"]
    for name, (pre, stmt, kind) in KW_STMTS.items():
        L += kw_case(name, pre, stmt, kind)
        if name in KW_TXN_OPS:
            L += kw_case(name, pre, stmt, kind, txn=True)
    L += ["         case op = 'SLEEP'", "            sleep a2 + 0", "            crt 'KW SLEEP ':a2", "         case op = 'TIME'", "            crt 'KW TIME ':time()",
          "         case op = 'EXEC'", "            execute a2", "            crt 'KW EXEC ':a2:' who=':@who",
          "         case 1", "            crt 'KW UNKNOWN ':op", "      end case", "   repeat", "   crt 'KW end'", "   stop", "",
          "shw: * SV = V with the four marks made visible, cut to its first and last 40 characters when over 100",
          "   sv = v", "   sv = change(sv, @im, '<I>')", "   sv = change(sv, @fm, '<F>')", "   sv = change(sv, @vm, '<V>')", "   sv = change(sv, @sm, '<S>')",
          "   if len(sv) > 100 then sv = sv[1,40] : '..' : sv[len(sv) - 39, 40]", "   return", "", "end", ""]
    return "\n".join(L)


def kw_prog(tag, ptr, middle, pre=(), dict_open=False):
    """A small program that opens the pointer ptr into f, runs MIDDLE and says SURVIVED when it was not stopped by the statement."""
    L = ["   " + p for p in pre]
    opn = ("open 'DICT', '%s' to f" if dict_open else "open '%s' to f") % ptr
    L += ["   crt 'KW %s begin'" % tag, "   %s else crt 'KW %s openfail st=':status() ; stop" % (opn, tag)]
    L += ["   " + x for x in middle] + ["   crt 'KW %s SURVIVED st=':status()" % tag, "end", ""]
    return "\n".join(L)


# programs that must STOP (no ON ERROR): (tag, pointer, statements, lines before, DICT open, accounts, the abort message (a function), the pre lines)
def _txn(*stmts):
    return ["begin transaction"] + list(stmts) + ["rollback", "end transaction"]


KWA = [
    # a change or a lock inside a transaction: 11510 naming the server and the statement (net_gate), nothing sent
    ("tw", "zznw1", _txn("write 'x' to f, 'w1'"), (), False, ("zznhon",), lambda: [msg(11510, "nfw", "write")]),
    ("twu", "zznw1", _txn("writeu 'x' to f, 'w1'"), (), False, ("zznhon",), lambda: [msg(11510, "nfw", "writeu")]),
    ("tmw", "zznw1", _txn("matwrite mw to f, 'w1'"), ("dim mw(2)", "mat mw = 'a'"), False, ("zznhon",), lambda: [msg(11510, "nfw", "write"), msg(11510, "nfw", "writeu")]),
    ("twv", "zznw1", _txn("writev 'x' to f, 'w1', 1"), (), False, ("zznhon",), lambda: [msg(11510, "nfw", "writev")]),
    ("tdl", "zznw1", _txn("delete f, 'w1'"), (), False, ("zznhon",), lambda: [msg(11510, "nfw", "delete")]),
    ("tdu", "zznw1", _txn("deleteu f, 'w1'"), (), False, ("zznhon",), lambda: [msg(11510, "nfw", "delete"), msg(11510, "nfw", "deleteu")]),
    ("tcl", "zznw1", _txn("clearfile f"), (), False, ("zznhon",), lambda: [msg(11510, "nfw", "clearfile")]),
    ("tru", "zznw1", _txn("readu r from f, 'w1' else null"), (), False, ("zznhon",), lambda: [msg(11510, "nfw", "readu")]),
    ("trl", "zznw1", _txn("readl r from f, 'w1' else null"), (), False, ("zznhon",), lambda: [msg(11510, "nfw", "readl")]),
    ("trv", "zznw1", _txn("readvu v from f, 'w1', 1 else null"), (), False, ("zznhon",), lambda: [msg(11510, "nfw", "readvu")]),
    ("tlu", "zznw1", _txn("recordlocku f, 'w1'"), (), False, ("zznhon",), lambda: [msg(11510, "nfw", "recordlocku")]),
    ("tll", "zznw1", _txn("recordlockl f, 'w1'"), (), False, ("zznhon",), lambda: [msg(11510, "nfw", "recordlockl")]),
    # S.72: a file lock and its release inside a transaction are refused as every other lock is
    ("tfl", "zznw1", _txn("filelock f"), (), False, ("zznhon",), lambda: [msg(11510, "nfw", "filelock")]),
    ("tfu", "zznw1", _txn("fileunlock f"), (), False, ("zznhon",), lambda: [msg(11510, "nfw", "fileunlock")]),
    # the S.64 edit gate of the REMOTE file's name, asked of the account that is signed in: no ON ERROR, the abort says which gate
    ("gb", "zznwbp", ["write 'x' to f, 'prog1'"], (), False, ("zznhned",), lambda: [msg(11407)]),
    ("gv", "zznwvoc", ["write 'x' to f, 'verb1'"], (), False, ("zznhned", KOFF), lambda: [msg(11405)]),
    ("gd", "zznw1", ["write 'x' to f, 'name'"], (), True, ("zznhned",), lambda: [msg(11406)]),
    ("gbd", "zznwbp", ["delete f, 'prog1'"], (), False, ("zznhned",), lambda: [msg(11407)]),
    ("gvc", "zznwvoc", ["clearfile f"], (), False, ("zznhned", KOFF), lambda: [msg(11405)]),
    ("gbv", "zznwbp", ["writev 'x' to f, 'prog1', 1"], (), False, ("zznhned",), lambda: [msg(11407)]),
    ("gbm", "zznwbp", ["matwrite mw to f, 'prog1'"], ("dim mw(2)", "mat mw = 'a'"), False, ("zznhned",), lambda: [msg(11407)]),
    # an id that cannot be sent: the statement stops (no ON ERROR), nothing is sent
    ("iw", "zznw1", ["write 'x' to f, ''"], (), False, ("zznhon",), None),
    ("iw64", "zznw1", ["write 'x' to f, str('a', 64)"], (), False, ("zznhon",), None),
    ("id", "zznw1", ["delete f, ''"], (), False, ("zznhon",), None),
    # S.72: RECORDLOCKED() of an id of 64 bytes stops the program (the function has no ON ERROR clause) and sends nothing
    ("irl", "zznw1", ["x = recordlocked(f, str('a', 64))"], (), False, ("zznhon",), None),
    # S.72b: RECORDLOCKED() is write-governed (kw_peek runs these two).  "rrd": a READ-mode handle (zznwr: the definition nfa says read) is refused by the kernel with 11501 and nothing is sent, whatever the
    # file holds (kw_peek has user 7 hold w2, so that a served answer would be -2).  "rwg": a WRITE-mode handle is served for a login in sdfileswrite (x is printed, and the program survives) and, for one
    # WITHOUT the group (kw_peek runs it with write_group off), the request goes out and the SERVER's wall stops the program with 11500 and the text of 11521.
    ("rrd", "zznwr", ["x = recordlocked(f, 'w2')"], (), False, ("zznhon",), lambda: [msg(11501, "nfa", "recordlocked")]),
    ("rwg", "zznw1", ["x = recordlocked(f, 'w2')", "crt 'KW rwg x=':x:' st=':status()"], (), False, ("zznhon",), lambda: [msg(11500, "nfw", "recordlocked", msg(11521, 34))]),
]
# statements that stay refused on a write-mode handle (message 11511 'not available', not 11501 'read only'): the matrix KM's entries, taken to the pointer zznw1
KW_STILL_REFUSED = ("selectindex", "selectindexv", "selectright", "selectleft", "setleft", "setright", "fcontrol6", "fcontrol1",
                    "fiexcl", "fistaton", "fistatoff")      # S.72: filelock, fileunlock and recordlocked are not here any more - they work on a write-mode handle (kw_filelocks)
# internal programs (global catalogue, verbs in the accounts): a gate that must not exempt them, the MUSTLOCK setting only they can make, the S.64 key edit_guard asks
KWI_TEXT = """$internal
program zznkwi
$catalog $zznkwi
   oc = 'then'
   crt 'KW i begin'
   open 'zznwbp' to f else crt 'KW i openfail st=':status() ; stop
   write 'viaint' to f, 'prog1' on error oc = 'error'
   crt 'KW i bp ':oc:' st=':status()
   open 'zznw1' to f2 else crt 'KW i openfail2 st=':status() ; stop
   x = fileinfo(f2, 10005)
   crt 'KW i setrdonly answer=':x
   oc = 'then'
   write 'x' to f2, 'w1' on error oc = 'error'
   crt 'KW i setrdonly ':oc:' st=':status()
   crt 'KW i readonly=':fileinfo(f2, 1001)
   crt 'KW i end'
end
"""
KWG_TEXT = """$internal
program zznkwg
$catalog $zznkwg
deffun edit_guard(f) calling '!edit_guard'
   crt 'KW g begin'
   open 'zznwbp' to f1 else crt 'KW g openfail st=':status() ; stop
   ok = edit_guard(f1)
   crt 'KW g bp ok=':ok
   open 'zznwvoc' to f2 else crt 'KW g openfail st=':status() ; stop
   ok = edit_guard(f2)
   crt 'KW g voc ok=':ok
   open 'DICT', 'zznw1' to f3 else crt 'KW g openfail st=':status() ; stop
   ok = edit_guard(f3)
   crt 'KW g dict ok=':ok
   open 'zznw1' to f4 else crt 'KW g openfail st=':status() ; stop
   ok = edit_guard(f4)
   crt 'KW g data ok=':ok
   crt 'KW g end'
end
"""
KWM_TEXT = """$internal
program zznkwm
$catalog $zznkwm
   oc = 'then'
   crt 'KW m begin'
   open 'zznw1' to f else crt 'KW m openfail st=':status() ; stop
   if pconfig('MUSTLOCK', 1) then null
   write 'x' to f, 'w1' on error oc = 'error'
   crt 'KW m write-nolock ':oc:' st=':status()
   oc = 'then'
   delete f, 'w2' on error oc = 'error'
   crt 'KW m delete-nolock ':oc:' st=':status()
   oc = 'then'
   readu rec from f, 'w1' on error oc = 'error' locked oc = 'locked' else oc = 'else'
   crt 'KW m readu ':oc:' st=':status():' rec=[':rec:']'
   oc = 'then'
   write 'y' to f, 'w1' on error oc = 'error'
   crt 'KW m write-locked ':oc:' st=':status()
   if pconfig('MUSTLOCK', 0) then null      ;* MUSTLOCK belongs to the whole process: left on, the command processor's own WRITEs are refused (3023) and it never gets back to the prompt
   crt 'KW m end'
end
"""
# AUTOLOCK: $MODE AUTOLOCK makes a WRITE and a DELETE take the update lock themselves (compile time; an ordinary program)
KWAL_TEXT = """$mode autolock
   crt 'KW al begin'
   open 'zznw1' to f else crt 'KW al openfail st=':status() ; stop
   write 'by-autolock' to f, 'w1' on error crt 'KW al write error st=':status()
   crt 'KW al write st=':status()
   delete f, 'w2' on error crt 'KW al delete error st=':status()
   crt 'KW al delete st=':status()
   crt 'KW al end'
end
"""
KWAL2_TEXT = """$mode autolock
   crt 'KW al2 begin'
   open 'zznw1' to f else crt 'KW al2 openfail st=':status() ; stop
   crt 'KW al2 time ':time()
   write 'after-wait' to f, 'w3' on error crt 'KW al2 write error st=':status()
   crt 'KW al2 write st=':status()
   crt 'KW al2 time ':time()
   crt 'KW al2 end'
end
"""
# the lock that outlives its file variable until the next prompt, and the program that keeps the session alive after it
KWL1_TEXT = """   crt 'KW l1 begin'
   open 'zznw1' to f else crt 'KW l1 openfail st=':status() ; stop
   readu rec from f, 'w1' else null
   crt 'KW l1 locked'
   sleep 1
end
"""
# 19 Oct 26 (verifier, finish 2): the `sleep 1` above is the fix for the row "A program READUs a record and ends without CLOSE", which failed in 3 of 4 runs of --sections=kwrite on an
# unchanged tree.  LockWatch polls the fake's lock table every 50 ms; the program used to end the moment it had the lock, the queued close went at the next prompt, and the whole life of the lock
# was shorter than a poll, so the watcher saw no lock at all (states empty) and the row failed with nothing wrong in the code.  The lock is now held for a second while the program is still
# running, which the watcher cannot miss; the row's claim (it is GONE after the next command while the session is open) is unchanged.
KWL2_TEXT = """   crt 'KW l2 begin'
   sleep 4
   crt 'KW l2 end'
end
"""
# S.72 (20 Oct 26): the same two programs for a FILE lock - the first takes it, holds it for a second and ends without CLOSE or FILEUNLOCK; the second keeps the session alive
KWF1_TEXT = """   crt 'KW f1 begin'
   open 'zznw1' to f else crt 'KW f1 openfail st=':status() ; stop
   filelock f locked crt 'KW f1 LOCKED'
   crt 'KW f1 locked'
   sleep 1
end
"""
KWF2_TEXT = """   crt 'KW f2 begin'
   sleep 4
   crt 'KW f2 end'
end
"""
# S.72: GETLOCKS() is an internal function.  A remote file (write mode and read mode), a LOCAL file with a record lock this session holds, and 'not a file' (every file): the remote view is the
# counters only, never another file's locks.  readu locks the record zznw1 of the account's own VOC, a local lock the remote answers must not show.
KWK_TEXT = """$internal
program zznkwk
$catalog $zznkwk
   crt 'KW k begin'
   open 'zznw1' to f else crt 'KW k openfail st=':status() ; stop
   open 'zznwr' to fr else crt 'KW k openfail2 st=':status() ; stop
   open 'voc' to lf else crt 'KW k novoc' ; stop
   readu x from lf, 'zznw1' else crt 'KW k voc-else' ; stop
   if len(x) = 0 then crt 'KW k voc-empty'        ;* (x is used: an assigned and unused variable is a compiler warning, and a warning fails the setup row)
   a = getlocks(f, 0)
   b = getlocks(fr, 0)
   c = getlocks(lf, 0)
   d = getlocks(0, 0)
   e = getlocks(f, 12345)
   crt 'KW k remote fields=':dcount(a, @fm):' values=':dcount(a<1>, @vm)
   crt 'KW k remote-read fields=':dcount(b, @fm):' values=':dcount(b<1>, @vm)
   crt 'KW k remote-user fields=':dcount(e, @fm):' values=':dcount(e<1>, @vm)
   crt 'KW k local fields=':dcount(c, @fm):' id=':c<2,5>:' type=':c<2,4>
   crt 'KW k all fields=':dcount(d, @fm):' has-local=':(index(upcase(d), 'ZZNW1', 1) # 0)       ;* the VOC is a no-case file: the lock is held under the upper case id
   crt 'KW k counters-equal=':(a<1> = b<1> and a<1> = c<1> and a<1> = d<1> and a<1> = e<1>)
   crt 'KW k remote-has-local-lock=':(index(upcase(a), 'ZZNW1', 1) # 0)
   release lf
   crt 'KW k end'
end
"""
# S.72: MUSTLOCK (the client's, set by an internal program) and a file lock: the file lock this session holds covers every record (as check_lock() does for a local file), so a WRITE is made;
# after FILEUNLOCK the same WRITE is refused with 3023
KWM2_TEXT = """$internal
program zznkwm2
$catalog $zznkwm2
   oc = 'then'
   crt 'KW m2 begin'
   open 'zznw1' to f else crt 'KW m2 openfail st=':status() ; stop
   if pconfig('MUSTLOCK', 1) then null
   filelock f locked oc = 'locked'
   crt 'KW m2 filelock ':oc
   oc = 'then'
   write 'viafilelock' to f, 'w1' on error oc = 'error'
   crt 'KW m2 write-under-filelock ':oc:' st=':status()
   fileunlock f
   oc = 'then'
   write 'afterunlock' to f, 'w1' on error oc = 'error'
   crt 'KW m2 write-after-unlock ':oc:' st=':status()
   if pconfig('MUSTLOCK', 0) then null
   crt 'KW m2 end'
end
"""
# S.72: THE LOCAL CONTROL.  The same statements on a LOCAL file (the account's own VOC): what a remote file must give back, from the kernel that has no remote file in it.  FILELOCK leaves STATUS()
# alone when it succeeds (locally), so it is not printed; the rest is what kw_filelocks expects of the remote file.
KWC_TEXT = """   crt 'KW c begin'
   open 'voc' to f else crt 'KW c novoc' ; stop
   filelock f locked crt 'KW c LOCKED'
   x = recordlocked(f, 'zznw1')
   crt 'KW c recordlocked-own-filelock x=':x
   fileunlock f
   crt 'KW c unlock-own st=':status()
   x = recordlocked(f, 'zznw1')
   crt 'KW c recordlocked-free x=':x:' st=':status()
   fileunlock f
   crt 'KW c unlock-nobody st=':status()
   crt 'KW c end'
end
"""
# S.72b: the variable made READ ONLY after the open (FILEINFO FL$SETRDONLY, from an internal program only) is a read-mode handle for RECORDLOCKED() as well: served before, refused (11501) after
KWR_TEXT = """$internal
program zznkwr
$catalog $zznkwr
   crt 'KW r begin'
   open 'zznw1' to f else crt 'KW r openfail st=':status() ; stop
   x = recordlocked(f, 'w2')
   crt 'KW r before x=':x:' st=':status()
   y = fileinfo(f, 10005)
   crt 'KW r setrdonly answer=':y
   x = recordlocked(f, 'w2')
   crt 'KW r SURVIVED x=':x
   crt 'KW r end'
end
"""
KWADM_TEXT = """   crt 'KW adm begin'
   oc = 'then'
   open 'voc' to v else crt 'KW adm novoc' ; stop
   write 'N':@fm:'nfw':@fm:'hwork' to v, 'zznwadm'
   write 'N':@fm:'nfw':@fm:'bp' to v, 'zznwadmbp'
   open 'zznwadm' to f else crt 'KW adm openfail st=':status() ; stop
   open 'zznwadmbp' to fb else crt 'KW adm openfail2 st=':status() ; stop
   write 'one' to f, 'w1' on error oc = 'error'
   crt 'KW adm write1 ':oc:' st=':status()
   oc = 'then'
   write 'viaadmin' to fb, 'prog1' on error oc = 'error'
   crt 'KW adm bp ':oc:' st=':status()
   execute 'RUN bp zznfhm1'
   oc = 'then'
   write 'two' to f, 'w1' on error oc = 'error'
   crt 'KW adm write2 ':oc:' st=':status()
   execute 'RUN bp zznfhm2'
   oc = 'then'
   write 'three' to f, 'w1' on error oc = 'error'
   crt 'KW adm write3 ':oc:' st=':status()
   crt 'KW adm end'
end
"""


def kw_voc():
    """The VOC records the administrator writes: account -> [(id, fields)]."""
    ptrs = [(v, ["N", s, f]) for v, s, f in KW_PTRS]
    return {"zznhon": ptrs + [("zznkwm", ["V", "CA", "$zznkwm"]), ("zznkwg", ["V", "CA", "$zznkwg"]), ("zznkwk", ["V", "CA", "$zznkwk"]), ("zznkwm2", ["V", "CA", "$zznkwm2"]), ("zznkwr", ["V", "CA", "$zznkwr"])],
            HNED: ptrs + [("zznkwi", ["V", "CA", "$zznkwi"]), ("zznkwg", ["V", "CA", "$zznkwg"])],
            KOFF: ptrs}


def kw_fix_text():
    root = os.path.join(g.BOX, "user_accounts")
    out = ["$internal"]
    for acct, recs in kw_voc().items():
        out.append("   openpath '%s' to v else crt 'KWFIX no voc %s' ; stop" % (os.path.join(root, acct, "voc"), acct))
        for rid, flds in recs:
            out.append("   write %s to v, '%s'" % (":@fm:".join("'%s'" % x for x in flds), rid))
        out.append("   close v")
    out += ["   crt 'KWFIX done'", "end", ""]
    return "\n".join(out)


def kw_prep():
    """Once: the account with the NET gate and no edit gate (HNED), the driver, the programs that must stop, the internal programs and the pointers."""
    if "ready" in KW:
        return KW["ready"]
    KW["ready"] = False
    if not kn_prep() or not hw_prep():
        return False
    g.EXTRA_FIXTURES[HNED] = ("no", "no")
    path = g.build_account(HNED)
    gates_on = [path, "", g.GROUP, "", "", "", "no", "no", "", "yes", "yes", "yes", "", "", "yes"]
    g.reg_write(HNED, gates_on)                                    # while the programs are compiled: they need bp.edit
    drv = kw_driver()
    plan = {"zznhon": {KWDRV: drv, "zznkwal": KWAL_TEXT, "zznkwal2": KWAL2_TEXT, "zznkwl1": KWL1_TEXT, "zznkwl2": KWL2_TEXT, "zznkwf1": KWF1_TEXT, "zznkwf2": KWF2_TEXT, "zznkwc": KWC_TEXT},
            HNED: {KWDRV: drv}, KOFF: {KWDRV: drv}}
    KW["abort"] = {}
    for i, (tag, ptr, middle, pre, dict_open, accts, _m) in enumerate(KWA, 1):
        name = "zznkwa%02d" % i
        KW["abort"][name] = i - 1
        for a in accts:
            plan.setdefault(a, {})[name] = kw_prog(tag, ptr, middle, pre, dict_open)
    # the refusals that remain on a write-mode handle: the matrix' programs, taken to the pointer zznw1 (write mode)
    KW["still"] = {}
    for i, (tag, pre, a_lines, _e, want, _st) in enumerate(KM, 1):
        if tag in KW_STILL_REFUSED:
            name = "zznkws%02d" % i
            KW["still"][name] = (tag, want)
            plan["zznhon"][name] = kw_prog(tag, "zznw1", a_lines, pre)
    missing, warn, total = {}, [], 0
    for acct, progs in plan.items():
        for name, text in progs.items():
            g.put(os.path.join(acct_path(acct), "bp", name), text)
        out, miss = kn_compile(acct, list(progs))
        total += len(progs)
        warn += [ln for ln in out if re.search(r"warning|not assigned", ln, re.I)]
        if miss:
            missing[acct] = (miss, [ln for ln in out if any(n in ln for n in miss) or re.search(r"error", ln, re.I)][:10])
    row("SETUP: the %d programs of the write section (the driver in three accounts, %d that must stop, %d refusals that remain, AUTOLOCK, the lock lifetime) compile in ORDINARY sessions "
        "with no error and no warning" % (total, len(KWA), len(KW["still"])), not missing and not warn, repr((missing, warn[:4])))

    # the internal programs, the pointers (written by the administrator) and the admin's program
    g.put(os.path.join(g.SYS, "gpl.bp", "zznkwi"), KWI_TEXT)
    g.put(os.path.join(g.SYS, "gpl.bp", "zznkwg"), KWG_TEXT)
    g.put(os.path.join(g.SYS, "gpl.bp", "zznkwm"), KWM_TEXT)
    g.put(os.path.join(g.SYS, "gpl.bp", "zznkwk"), KWK_TEXT)
    g.put(os.path.join(g.SYS, "gpl.bp", "zznkwm2"), KWM2_TEXT)
    g.put(os.path.join(g.SYS, "gpl.bp", "zznkwr"), KWR_TEXT)
    out = g.adm(["BASIC gpl.bp zznkwi zznkwg zznkwm zznkwk zznkwm2 zznkwr"], internal=True)
    ok_i = g.has(out, r"^Compiled 6 program\(s\) with no errors") and not any(re.search(r"warning|not assigned", ln, re.I) for ln in out)
    g.put(os.path.join(g.SYS, "bp", "zznkwadm"), KWADM_TEXT)
    out1 = g.adm(["BASIC bp zznkwadm"], internal=True)
    ok_a = g.has(out1, r"^Compiled 1 program\(s\) with no errors")
    g.put(os.path.join(g.SYS, "bp", "zznkwfix"), kw_fix_text())
    out2 = g.adm(["BASIC bp zznkwfix", "RUN bp zznkwfix"], internal=True)
    ok_f = g.has(out2, r"^KWFIX done$")
    npt = sum(len(v) for v in kw_voc().values())
    row("SETUP: the six internal test programs (S.72: GETLOCKS and MUSTLOCK with a file lock were added; S.72b: RECORDLOCKED() on a variable made read only) and the administrator's program compile, and the administrator wrote %d VOC records (pointers to the write-mode files and the verbs) into three accounts"
        % npt, ok_i and ok_a and ok_f, repr((out[-4:], out1[-4:], out2[-4:], [ln for ln in out if re.search(r"warning|not assigned", ln, re.I)][:6])))
    if missing or not (ok_i and ok_a and ok_f):
        return False
    g.reg_write(HNED, [path, "", g.GROUP, "", "", "", "no", "no", "", "no", "no", "no", "", "", "yes"])        # NOW the account has the NET gate and NO edit gate
    f = g.flags(g.plain(HNED, ["ZZKF"]))
    row("CONTROL: the account %s is an ordinary session (admin=0) and its edit gates are off: it cannot write the VOC, a program file or a dictionary of its own" % HNED,
        f is not None and f[0] == "0", repr(f))
    KW["ready"] = f is not None and f[0] == "0"
    return KW["ready"]


# ---- running a session on the write-mode files ------------------------------------------------------------------------------------------------

class LockWatch(threading.Thread):
    """Polls a fake's lock table every 50 ms for the lock set of the FIRST session begun after it was started, and keeps each change as (locks, session already ended)."""

    def __init__(self, srv):
        threading.Thread.__init__(self, daemon=True)
        self.srv = srv
        with srv.lock:
            self.n0 = len(srv.sessions)
        self.states = []
        self.closed_at = None                     # when the connection was first seen ended
        self.stop_ev = threading.Event()

    def run(self):
        last = None
        while not self.stop_ev.is_set():
            with self.srv.lock:
                ses = self.srv.sessions[self.n0] if len(self.srv.sessions) > self.n0 else None
            if ses is not None:
                st = (tuple(self.srv.store.locks_of(ses.userno)), ses.closed)
                if st != last:
                    self.states.append(st)
                    last = st
                if ses.closed and self.closed_at is None:
                    self.closed_at = time.time()
            time.sleep(0.05)

    def seq(self):
        """The lock sets seen, one after the other, a repeat left out."""
        out = []
        for locks, _closed in self.states:
            if not out or out[-1] != locks:
                out.append(locks)
        return out

    def alive_empty_after_lock(self):
        """Was a state with NO locks seen while the session was still open, after one with locks?"""
        seen = False
        for locks, closed in self.states:
            if locks:
                seen = True
            elif seen and not closed:
                return True
        return False


class HolderRelease(threading.Thread):
    """Lets user USERNO (a lock the test made with store.hold) go DELAY seconds after the first session begun after this was started has sent its first lock request."""

    def __init__(self, srv, userno, delay):
        threading.Thread.__init__(self, daemon=True)
        self.srv, self.userno, self.delay = srv, userno, delay
        with srv.lock:
            self.n0 = len(srv.sessions)
        self.released = None

    def run(self):
        t0 = time.time()
        while time.time() - t0 < 90:
            with self.srv.lock:
                ses = self.srv.sessions[self.n0] if len(self.srv.sessions) > self.n0 else None
            if ses is not None and (30 in ses.requests or 32 in ses.requests):
                time.sleep(self.delay)
                self.srv.store.drop_user(self.userno)
                self.released = time.time()
                return
            time.sleep(0.05)


def kw_run(acct, cmds, fakes, cfg=None, watch=(), holders=()):
    """kn_run, with the lock watchers and holder releases started before it; r.kw is what the driver printed, r.watch the watchers, r.stores what each fake's files held at the end."""
    ws = [LockWatch(f) for f in watch]
    hs = [HolderRelease(f, u, dl) for f, u, dl in holders]
    for t in ws + hs:
        t.start()
    try:
        r = kn_run(acct, cmds, fakes, cfg)
        t_end = time.time()
    finally:
        for w in ws:
            w.stop_ev.set()
        for w in ws:
            w.join(timeout=2)
    r.watch, r.holders, r.t_end = ws, hs, t_end
    r.kw = [ln for ln in r.out if ln.startswith("KW ")]
    r.stores = [{n: f.store.records(n) for n in (HW, HWBP, HWVOC, HWNC)} for f in fakes]
    for f in fakes:
        wreset(f)
    return r


def kw_drive(acct, lines, fakes, cfg=None, watch=(), holders=()):
    return kw_run(acct, ["RUN bp " + KWDRV] + list(lines) + ["END"], fakes, cfg, watch, holders)


def kw_sane(r, need_end=True):
    """The driver began and ended, the session did not hang, no fake found anything malformed or refused a request, no connection is left."""
    return (not r.hung and "KW begin" in r.kw and ("KW end" in r.kw or not need_end) and r.idle and not r.crash
            and all(not d["errors"] for d in r.d) and all(not s.refused for d in r.d for s in d["sessions"]))


def kw_why(r, n=6):
    return "hung=%s began=%s ended=%s idle=%s crash=%s fake errors=%r\n      kw: %r\n      tail: %r" % (
        r.hung, "KW begin" in r.kw, "KW end" in r.kw, r.idle, r.crash, [d["errors"] for d in r.d], r.kw[-n:], r.out[-3:])


def kw_rec(op, rid, rec, oc="then", st=0):
    return "KW %s %s %s st=%d len=%d rec=[%s]" % (op, rid, oc, st, len(rec), show(rec))


def kw_plain(op, rid="", oc="then", st=0):
    return "KW %s %s %s st=%d" % (op, rid, oc, st)


def kw_segments(out):
    """The lines each program printed, by its tag: from its  KW <tag> begin  line to the next one."""
    segs, cur = {}, None
    for ln in out:
        m = re.match(r"^KW (\S+) begin$", ln)
        if m:
            cur = m.group(1)
            segs[cur] = []
        elif cur is not None:
            segs[cur].append(ln)
    return segs


def kw_types_ok(r, allowed=KWALLOWED):
    return all(set(d["types"]) <= allowed for d in r.d)


def kwrite_section():
    say("\n--- kernel, WRITE mode (slice 3e): WRITE, WRITEU, MATWRITE, WRITEV, WRITEVU, DELETE, DELETEU, CLEARFILE, READU/L, MATREADU/L, READVU/L, RECORDLOCKU/L and RELEASE on a file of a "
        "server whose definition says write ---")
    if not kw_prep():
        return
    A, B = S["A"], S["B"]
    kw_basic(A)
    kw_writev(A)
    kw_locks(A)
    kw_busy(A)
    kw_release(A, B)
    kw_txn(A)
    kw_gate(A)
    kw_lost(A)
    kw_lifetime(A)
    kw_fileinfo(A)
    kw_locking_modes(A)
    kw_mode_admin(A)
    kw_refused(A)
    kw_misc(A)
    kw_filelocks(A)
    kw_peek(A)


def kw_basic(A):
    say("\n  -- WRITE, WRITEU, MATWRITE, DELETE, DELETEU on a write-mode file: the request, the record, STATUS(), no cache --")
    rec_new = NEWREC
    lines = ["OPEN|1|zznw1", "READ|1|w1", "WRITE|1|w1|" + NEWREC_PH, "READ|1|w1", "WRITE|1|wnew|created", "MATWRITE|1|wmat|p<F>q", "READ|1|wmat", "WRITEU|1|w2|kept",
             "DELETE|1|w3", "READ|1|w3", "DELETEU|1|wnew", "READ|1|wnew", "DELETE|1|nosuch", "WRITE|1|a<F>b|x", "WRITE|1||x", "DELETE|1||", "WRITE|1|" + "a" * 63 + "|edge", "WRITE|1|" + "a" * 64 + "|toolong", "CLOSE|1"]
    want = ["KW OPEN zznw1 then st=0", kw_rec("READ", "w1", HWREC["w1"]), kw_plain("WRITE", "w1"), kw_rec("READ", "w1", rec_new),
            kw_plain("WRITE", "wnew"), kw_plain("MATWRITE", "wmat"), kw_rec("READ", "wmat", "p" + FMC + "q"), kw_plain("WRITEU", "w2"),
            kw_plain("DELETE", "w3"), kw_rec("READ", "w3", "", "else", 3006), kw_plain("DELETEU", "wnew"), kw_rec("READ", "wnew", "", "else", 3006),
            kw_plain("DELETE", "nosuch"), "KW WRITE a<F>b error st=3000", "KW WRITE  error st=3000", "KW DELETE  error st=3000", kw_plain("WRITE", "a" * 63), "KW WRITE " + "a" * 64 + " error st=3000", "KW CLOSE 1"]
    wire = [ACCT_REQ, W_OPEN(HW), W_READ(1, "w1"), W_WRITE(1, "w1", rec_new), W_READ(1, "w1"), W_WRITE(1, "wnew", "created"), W_WRITE(1, "wmat", "p" + FMC + "q"), W_READ(1, "wmat"),
            W_WRITE(1, "w2", "kept", True), W_DEL(1, "w3"), W_READ(1, "w3"), W_DEL(1, "wnew", True), W_READ(1, "wnew"), W_DEL(1, "nosuch"), W_WRITE(1, "a" * 63, "edge"), (5, FNO(1))]
    r = kw_drive("zznhon", lines, (A,))
    row("an ordinary session in zznhon (the NET gate on, listed for nfw) ran the write driver to its end: no hang, nothing malformed, no connection left", kw_sane(r), kw_why(r))
    got = [x for x in r.kw if not x.startswith(("KW begin", "KW end"))]
    row("...EVERY STATEMENT DID WHAT IT SHOULD, line for line (%d lines): OPEN, READ, WRITE then READ AT ONCE (the record just written: a write-mode handle is not cached), WRITE of a new id, MATWRITE, "
        "WRITEU, DELETE and READ (ELSE 3006), DELETEU, DELETE of a record that is not there (THEN, STATUS() 0), an id with a mark / an empty id (ON ERROR, STATUS() 3000, nothing sent)" % len(want),
        got == want, "first difference: %r" % (next(((a, b) for a, b in zip(got, want) if a != b), (len(got), len(want))),))
    d = r.d[0]
    row("...THE REQUESTS, in order, with their bytes: only what the statements need - WRITE is 16, WRITEU 17, DELETE 18, DELETEU 19, a READ after a WRITE is a new READ (no cache), the three bad ids "
        "sent NOTHING, CLOSE is 5", kn_wire(d) == wire, "first difference: %r" % (next(((a, b) for a, b in zip(kn_wire(d), wire) if a != b), (len(kn_wire(d)), len(wire))),))
    exp = dict(HWREC)
    exp.update({"w1": rec_new, "w2": "kept", "wmat": "p" + FMC + "q", "a" * 63: "edge"})
    del exp["w3"]
    row("...THE FILE ON THE FAKE: w1 with its four marks, w2 'kept', wmat 'p<F>q', w3 gone, wnew created and deleted, the 63 byte id written - and nothing else (not the 64 byte id)", r.stores[0][HW] == exp,
        repr({k: v for k, v in r.stores[0][HW].items() if exp.get(k) != v}))
    row("...the audit trail: the open line (mode=write), one 'write', one 'delete' - no id, no record", r.audits == [OPEN_W_AUD, "write server=nfw file=hwork", "delete server=nfw file=hwork"] and secret_free(r.audit),
        repr(r.audits))
    row("...and every request type the session sent is one of: login, account, open, close, read, release, write, writeu, delete, deleteu, lock, clearfile, recordlocked", kw_types_ok(r), repr(sorted(set(r.d[0]["types"]))))

    # a write-mode handle is never cached, a read-mode handle of the same file is (the control), and then it can show a record up to 2 seconds old
    r = kw_drive("zznhon", ["OPEN|1|zznw1", "OPEN|2|zznwr", "READ|2|w1", "WRITE|1|w1|changed", "READ|2|w1", "READ|1|w1", "SLEEP|3", "READ|2|w1", "CLOSE|1", "CLOSE|2"], (A,))
    got = [x for x in r.kw if not x.startswith(("KW begin", "KW end", "KW SLEEP"))]
    want = ["KW OPEN zznw1 then st=0", "KW OPEN zznwr then st=0", kw_rec("READ", "w1", HWREC["w1"]), kw_plain("WRITE", "w1"), kw_rec("READ", "w1", HWREC["w1"]), kw_rec("READ", "w1", "changed"),
            kw_rec("READ", "w1", "changed"), "KW CLOSE 1", "KW CLOSE 2"]
    row("THE CACHE: a READ-mode handle (zznwr, nfa) of the same file shows the record it read a moment ago for up to 2 seconds - after another handle's WRITE its second READ is the OLD record "
        "(the documented limit, the CONTROL), the write-mode handle reads the NEW one at once, and 3 seconds later the read-mode handle sees it too", kw_sane(r) and got == want,
        kw_why(r) + " got=%r" % got)
    row("...THE FAKE SAW THREE READ requests in all: the read-mode handle's first READ, the write-mode handle's READ, and the read-mode handle's READ after the entry had expired - its second "
        "READ was answered from the cache (%d)" % r.d[0]["types"].count(6), r.d[0]["types"].count(6) == 3, repr(r.d[0]["types"]))
    row("...nothing in the session wrote to any file but hwork: the control files are as they were", all(r.stores[0][n] == dict(rec) for n, rec, _p, _c in HWFILES if n != HW), "")

    # a NOCASE remote file keeps the key it already has
    r = kw_drive("zznhon", ["OPEN|1|zznwnc", "WRITE|1|MIXED|new", "READ|1|mixed", "CLOSE|1"], (A,))
    row("A NOCASE remote file: WRITE under another spelling (MIXED) goes to the record that is there (Mixed), and a READ under a third (mixed) finds it - the file, not the client, folds the case",
        kw_sane(r) and kw_rec("READ", "mixed", "new") in r.kw and r.stores[0][HWNC] == {"Mixed": "new"}, kw_why(r) + " store=%r" % (r.stores[0][HWNC],))


def kw_writev(A):
    say("\n  -- WRITEV and WRITEVU go through the recursive pcode: READ, change the field, WRITE or WRITEU --")
    lines = ["OPEN|1|zznw1", "WRITEV|1|w1|zz|2", "READ|1|w1", "WRITEV|1|nonew|v|3", "READ|1|nonew", "WRITEV|1|w2|x|0", "READ|1|w2", "WRITEV|1|w2|app|-1", "READ|1|w2",
             "WRITEVU|1|w3|u|2", "READ|1|w3", "CLOSE|1"]
    want = ["KW OPEN zznw1 then st=0", kw_plain("WRITEV", "w1"), kw_rec("READ", "w1", "alpha" + FMC + "zz"), kw_plain("WRITEV", "nonew"), kw_rec("READ", "nonew", FMC + FMC + "v"),
            kw_plain("WRITEV", "w2"), kw_rec("READ", "w2", "x" + FMC + "2"), kw_plain("WRITEV", "w2"), kw_rec("READ", "w2", "x" + FMC + "2" + FMC + "app"),
            kw_plain("WRITEVU", "w3"), kw_rec("READ", "w3", "gamma" + FMC + "u"), "KW CLOSE 1"]
    r = kw_drive("zznhon", lines, (A,))
    got = [x for x in r.kw if not x.startswith(("KW begin", "KW end"))]
    row("WRITEV of field 2 changes that field only (alpha<F>zz), of a record that is not there CREATES it (field 3: <F><F>v), field 0 is field 1, a negative field appends, WRITEVU keeps working "
        "- each with STATUS() 0 and the READ that follows showing the result", kw_sane(r) and got == want, kw_why(r) + " first difference: %r" % (next(((a, b) for a, b in zip(got, want) if a != b), (len(got), len(want))),))
    d = r.d[0]
    n16, n17 = d["types"].count(16), d["types"].count(17)
    row("...the fake saw only reads and writes for them: four WRITEs (16) and one WRITEU (17) in all - the inner READ and the inner WRITE of each WRITEV are ordinary statements (%d, %d)" % (n16, n17),
        kw_types_ok(r) and n16 == 4 and n17 == 1, repr(d["types"]))
    row("...THE FILE: w1, nonew, w2 and w3 as the READs showed, the other records untouched", r.stores[0][HW].get("w1") == "alpha" + FMC + "zz" and r.stores[0][HW].get("nonew") == FMC + FMC + "v"
        and r.stores[0][HW].get("w2") == "x" + FMC + "2" + FMC + "app" and r.stores[0][HW].get("w3") == "gamma" + FMC + "u", repr(r.stores[0][HW]))


def kw_locks(A):
    say("\n  -- locking reads and RECORDLOCK: the lock first (30), then the read; the lock watched in the fake's table while the session is open --")
    lines = ["OPEN|1|zznw1", "SLEEP|1", "READU|1|w1", "SLEEP|1", "READL|1|w2", "SLEEP|1", "READVU|1|w3|1", "SLEEP|1", "MATREADU|1|nosuch", "SLEEP|1", "RELEASE|1|w1", "SLEEP|1", "RELEASEF|1", "SLEEP|1",
             "READU|1|w1", "SLEEP|1", "CLOSE|1", "SLEEP|1"]
    wire = [ACCT_REQ, W_OPEN(HW), W_LOCK(1, "w1", True), W_READ(1, "w1"), W_LOCK(1, "w2", False), W_READ(1, "w2"), W_LOCK(1, "w3", True), W_READ(1, "w3"), W_LOCK(1, "nosuch", True),
            W_READ(1, "nosuch"), W_REL(1, "w1"), W_REL(1), W_LOCK(1, "w1", True), W_READ(1, "w1"), (5, FNO(1))]
    r = kw_drive("zznhon", lines, (A,), watch=(A,))
    got = [x for x in r.kw if not x.startswith(("KW begin", "KW end", "KW SLEEP"))]
    want = ["KW OPEN zznw1 then st=0", kw_rec("READU", "w1", HWREC["w1"]), kw_rec("READL", "w2", HWREC["w2"]), kw_rec("READVU", "w3", "gamma"),
            "KW MATREADU nosuch else st=3006 [][][]", kw_plain("RELEASE", "w1"), kw_plain("RELEASEF", ""), kw_rec("READU", "w1", HWREC["w1"]), "KW CLOSE 1"]
    row("the locking statements ran to the end and no connection is left", kw_sane(r), kw_why(r))
    row("...READU, READL, READVU (field 1) and MATREADU gave the record with STATUS() 0; MATREADU of a record that is not there took ELSE with STATUS() 3006 (the lock is held all the same, as locally)",
        got == want, "first difference: %r" % (next(((a, b) for a, b in zip(got, want) if a != b), (len(got), len(want))),))
    row("...THE REQUESTS: each locking read is a LOCK request (30, flags 3 for U, 2 for L: no wait) and then a READ (6) - never request 7 to 10 (the server's own locking reads) or 41; RELEASE w1 is 15 with "
        "the id, RELEASE f is 15 with the file number only, CLOSE is 5", kn_wire(r.d[0]) == wire, "first difference: %r" % (next(((a, b) for a, b in zip(kn_wire(r.d[0]), wire) if a != b), (len(kn_wire(r.d[0])), len(wire))),))
    ls = r.watch[0].seq()
    e = lambda *ids: tuple(sorted((HW, i, k) for i, k in ids))
    exp = [(), e(("w1", "update")), e(("w1", "update"), ("w2", "shared")), e(("w1", "update"), ("w2", "shared"), ("w3", "update")),
           e(("nosuch", "update"), ("w1", "update"), ("w2", "shared"), ("w3", "update")), e(("nosuch", "update"), ("w2", "shared"), ("w3", "update")), (), e(("w1", "update")), ()]
    row("...THE LOCK TABLE OF THE FAKE, watched while the session ran: none, w1 update, + w2 shared, + w3 update, + nosuch update (the lock on a missing record), - w1 (RELEASE f, id), none (RELEASE f), "
        "w1 update, none (CLOSE)", ls == exp, repr(ls))
    row("...the lock was held on the server DURING the session and gone BEFORE it ended (CLOSE let it go): a state with no lock was seen while the session was still open", r.watch[0].alive_empty_after_lock(),
        repr(r.watch[0].states[-3:]))

    # a busy record with a LOCKED clause: the branch is taken, STATUS() is the holder, nothing is read
    A.store.hold(HW, "w2", 7, "update")
    A.store.hold(HW, "w3", 8, "shared")
    lines = ["OPEN|1|zznw1", "READU|1|w2", "READL|1|w2", "READVU|1|w2|1", "MATREADU|1|w2", "RLOCKU|1|w2", "RLOCKL|1|w2", "RLOCKU|1|w3", "READL|1|w3", "READU|1|w1", "CLOSE|1"]
    r = kw_drive("zznhon", lines, (A,))
    got = [x for x in r.kw if not x.startswith(("KW begin", "KW end"))]
    want = ["KW OPEN zznw1 then st=0", "KW READU w2 locked st=7 len=0 rec=[]", "KW READL w2 locked st=7 len=0 rec=[]", "KW READVU w2 locked st=7 len=0 rec=[]", "KW MATREADU w2 locked st=7 [][][]",
            "KW RLOCKU w2 locked st=7", "KW RLOCKL w2 locked st=7", "KW RLOCKU w3 locked st=8", kw_rec("READL", "w3", HWREC["w3"]), kw_rec("READU", "w1", HWREC["w1"]), "KW CLOSE 1"]
    row("A BUSY RECORD WITH A LOCKED CLAUSE (user 7 holds w2 for update, user 8 holds w3 for read): READU, READL, READVU, MATREADU, RECORDLOCKU and RECORDLOCKL take the LOCKED branch with STATUS() the "
        "holder's number (7), the target is left empty; RECORDLOCKU of a record held shared is busy (8), READL of it is granted", kw_sane(r) and got == want,
        kw_why(r) + " first difference: %r" % (next(((a, b) for a, b in zip(got, want) if a != b), (len(got), len(want))),))
    ww = kn_wire(r.d[0])
    exp_w = [ACCT_REQ, W_OPEN(HW), W_LOCK(1, "w2", True), W_LOCK(1, "w2", False), W_LOCK(1, "w2", True), W_LOCK(1, "w2", True), W_LOCK(1, "w2", True), W_LOCK(1, "w2", False), W_LOCK(1, "w3", True),
             W_LOCK(1, "w3", False), W_READ(1, "w3"), W_LOCK(1, "w1", True), W_READ(1, "w1"), (5, FNO(1))]
    row("...THE FAKE SAW only lock requests for the busy records (no READ of w2 - the record is not read when the lock is refused), then LOCK and READ for the two that were granted",
        ww == exp_w, "first difference: %r" % (next(((a, b) for a, b in zip(ww, exp_w) if a != b), (len(ww), len(exp_w))),))


def kw_busy(A):
    say("\n  -- a busy record without a LOCKED clause is WAITED FOR by polling: lock requests every 250 ms, no read, until the holder lets go --")
    # (the statement as written, the driver's name for the form without a LOCKED clause, the line it must print, whether a record is read)
    for what, opname, lines, want_line, reads in (
            ("READU", "READUW", ["OPEN|1|zznw1", "TIME", "READUW|1|w2", "TIME", "CLOSE|1"], kw_rec("READUW", "w2", HWREC["w2"]), 1),
            ("READL", "READLW", ["OPEN|1|zznw1", "TIME", "READLW|1|w2", "TIME", "CLOSE|1"], kw_rec("READLW", "w2", HWREC["w2"]), 1),
            ("READVU", "READVUW", ["OPEN|1|zznw1", "TIME", "READVUW|1|w2|1", "TIME", "CLOSE|1"], kw_rec("READVUW", "w2", "beta"), 1),
            ("RECORDLOCKU", "RLOCKUW", ["OPEN|1|zznw1", "TIME", "RLOCKUW|1|w2", "TIME", "CLOSE|1"], kw_plain("RLOCKUW", "w2"), 0)):
        A.store.hold(HW, "w2", 7, "update")
        r = kw_drive("zznhon", lines, (A,), holders=((A, 7, 3.0),))
        times = [int(m.group(1)) for m in (re.match(r"^KW TIME (\d+)$", x) for x in r.kw) if m]
        types = r.d[0]["types"]
        n30 = types.count(30)
        row("%s on a record another user holds, no LOCKED clause: the statement WAITS (the holder lets go about 3 seconds after the first lock request) and then succeeds with STATUS() 0 - %s"
            % (what, "the record is read" if reads else "the lock is held"), kw_sane(r) and want_line in r.kw and len(times) == 2 and 2 <= (times[1] - times[0]) % 86400 <= 30, kw_why(r) + " times=%r" % times)
        row("...THE FAKE SAW %d LOCK requests (one every 250 ms or so), NO request of type 7 to 10 (the server's own locking reads, which wait on the server) and exactly %d READ, after the lock was taken: %s"
            % (n30, reads, sorted(set(types))), n30 >= 5 and not {7, 8, 9, 10} & set(types) and types.count(6) == reads, repr(types))

    # AUTOLOCK: $MODE AUTOLOCK makes a WRITE and a DELETE take the lock themselves
    r = kw_run("zznhon", ["RUN bp zznkwal"], (A,))
    seg = kw_segments(r.out).get("al", [])
    wire = [ACCT_REQ, W_OPEN(HW), W_LOCK(1, "w1", True), W_WRITE(1, "w1", "by-autolock"), W_LOCK(1, "w2", True), W_DEL(1, "w2")]
    row("$MODE AUTOLOCK: a WRITE and a DELETE of a remote record take the update lock first (30, flags 3) and then write (16) or delete (18) - the lock is let go by the plain WRITE and DELETE; "
        "STATUS() 0 for both", not r.hung and "KW al write st=0" in seg and "KW al delete st=0" in seg and "KW al end" in seg and kn_wire(r.d[0])[:len(wire)] == wire and r.idle,
        repr((seg, kn_wire(r.d[0])[:8])))
    row("...the file: w1 written, w2 gone", r.stores[0][HW].get("w1") == "by-autolock" and "w2" not in r.stores[0][HW], repr(r.stores[0][HW]))
    A.store.hold(HW, "w3", 8, "update")
    r = kw_run("zznhon", ["RUN bp zznkwal2"], (A,), holders=((A, 8, 3.0),))
    seg = kw_segments(r.out).get("al2", [])
    tms = [int(m.group(1)) for m in (re.match(r"^KW al2 time (\d+)$", x) for x in seg) if m]
    row("...AUTOLOCK on a record another user holds: the WRITE waits for the lock (polling) and is then made", not r.hung and "KW al2 write st=0" in seg and len(tms) == 2 and 2 <= (tms[1] - tms[0]) % 86400 <= 30
        and r.stores[0][HW].get("w3") == "after-wait" and r.d[0]["types"].count(30) >= 5 and r.d[0]["types"].count(16) == 1, repr((seg, r.d[0]["types"])))

    # MUSTLOCK on the CLIENT (pconfig, an internal program): a write without the lock is refused as it would be for a local file
    r = kw_run("zznhon", ["ZZNKWM"], (A,))
    seg = kw_segments(r.out).get("m", [])
    ww = kn_wire(r.d[0])
    row("MUSTLOCK (the client's, set by an internal program): WRITE and DELETE of a record the session has NOT locked take ON ERROR with STATUS() 3023 and send NO change (the server is asked whether the "
        "lock is held: request 34); after READU the same WRITE is made", not r.hung and "KW m write-nolock error st=3023" in seg and "KW m delete-nolock error st=3023" in seg
        and "KW m write-locked then st=0" in seg and "KW m end" in seg and r.stores[0][HW].get("w1") == "y" and r.stores[0][HW].get("w2") == HWREC["w2"], repr(seg))
    exp_w = [ACCT_REQ, W_OPEN(HW), W_RLK(1, "w1"), W_RLK(1, "w2"), W_LOCK(1, "w1", True), W_READ(1, "w1"), W_RLK(1, "w1"), W_WRITE(1, "w1", "y")]
    row("...THE FAKE: two RECORDLOCKED requests (34) for the two refused changes, then LOCK, READ, RECORDLOCKED and the WRITE (16): exactly one change on the wire",
        ww[:len(exp_w)] == exp_w and r.idle and sum(1 for t in r.d[0]["types"] if t in (16, 17, 18, 19)) == 1, "first difference: %r" % (next(((a, b) for a, b in zip(ww, exp_w) if a != b), (len(ww), len(exp_w))),))


def kw_release(A, B):
    say("\n  -- RELEASE in its three forms, and in a transaction --")
    lines = ["OPEN|1|zznw1", "OPEN|2|zznwb", "READU|1|w1", "READU|1|w2", "READU|2|w3", "SLEEP|1", "RELEASE|1|w1", "SLEEP|1", "RELEASEF|1", "SLEEP|1", "READU|1|w1", "READU|2|w1", "SLEEP|1",
             "RELEASEA|1", "SLEEP|1", "READU|1|w2", "SLEEP|1", "TRELEASE|1|w2", "SLEEP|1", "TRELEASEF|1", "SLEEP|1", "CLOSE|1", "CLOSE|2"]
    r = kw_drive("zznhon", lines, (A, B), watch=(A, B))
    row("the release program ran to the end and no connection is left", kw_sane(r), kw_why(r))
    e = lambda *ids: tuple(sorted((HW, i, "update") for i in ids))
    sa, sb = r.watch[0].seq(), r.watch[1].seq()
    row("...SERVER A's lock table, watched: none, w1, w1+w2, (RELEASE f, id) w2, (RELEASE f) none, w1, (RELEASE alone) none, w2, (RELEASE inside a transaction: NOTHING SENT) w2, (RELEASE f in a transaction: "
        "nothing sent) w2, (CLOSE) none", sa == [(), e("w1"), e("w1", "w2"), e("w2"), (), e("w1"), (), e("w2"), ()], repr(sa))
    row("...SERVER B: none, w3, w1+w3, (RELEASE alone sent to every connection with a write-mode file) none", sb[:4] == [(), e("w3"), e("w1", "w3"), ()], repr(sb))
    types = r.d[0]["types"]
    row("...A received exactly three RELEASE requests (record form, file form, and the 0 form) - the two inside the transaction sent nothing", types.count(15) == 3, repr(types))
    row("...and the transaction's RELEASE statements gave STATUS() 0", kw_plain("TRELEASE", "w2") in r.kw and kw_plain("TRELEASEF", "") in r.kw, repr([x for x in r.kw if "RELEASE" in x]))
    # (RELEASE on a READ-mode handle is refused as in slice 3c: the refusal matrix KM has "release" and "releasef" on zznet1, which is nfa - the control stands)


def kw_txn(A):
    say("\n  -- a change or a lock inside a transaction: refused (STATUS() 1010 / message 11510), a READ is not --")
    ops = ["TWRITE|1|w1|x", "TWRITEU|1|w1|x", "TMATWRITE|1|w1|a<F>b", "TWRITEV|1|w1|x|1", "TWRITEVU|1|w1|x|1", "TDELETE|1|w1", "TDELETEU|1|w1", "TCLEARFILE|1", "TREADU|1|w1", "TREADL|1|w1",
           "TREADVU|1|w1|1", "TMATREADU|1|w1", "TRLOCKU|1|w1", "TRLOCKL|1|w1"]
    r = kw_drive("zznhon", ["OPEN|1|zznw1"] + ops + ["TREAD|1|w1", "TRELEASE|1|w1", "TRELEASEF|1", "WRITE|1|w1|after", "CLOSE|1"], (A,))
    got = [x for x in r.kw if not x.startswith(("KW begin", "KW end"))]
    names = [o.split("|")[0] for o in ops]
    refused_ok = all(any(re.match(r"^KW %s \S* error st=1010( len=0 rec=\[\]| \[\]\[\]\[\])?$" % re.escape(nm), x) for x in got) for nm in names)
    row("INSIDE BEGIN TRANSACTION every one of WRITE, WRITEU, MATWRITE, WRITEV, WRITEVU, DELETE, DELETEU, CLEARFILE, READU, READL, READVU, MATREADU, RECORDLOCKU and RECORDLOCKL took ON ERROR with "
        "STATUS() 1010 (ER_TXN)", kw_sane(r) and refused_ok, kw_why(r) + " got=%r" % [x for x in got if "error" not in x][:4])
    row("...a READ in a transaction is served (the record), RELEASE gave STATUS() 0 and sent nothing, and after the transaction the same handle writes", kw_rec("TREAD", "w1", HWREC["w1"]) in got and kw_plain("TRELEASE", "w1") in got
        and kw_plain("TRELEASEF", "") in got and kw_plain("WRITE", "w1") in got, repr(got[-6:]))
    wire = kn_wire(r.d[0])
    row("...THE FAKE SAW only the OPEN, the READ in the transaction and the WRITE after it: not one change, lock or release request", wire == [ACCT_REQ, W_OPEN(HW), W_READ(1, "w1"), W_WRITE(1, "w1", "after"), (5, FNO(1))],
        "first difference: %r" % (wire,))
    row("...and the file holds the last write only", r.stores[0][HW].get("w1") == "after" and r.stores[0][HW].get("w2") == HWREC["w2"], repr(r.stores[0][HW]))

    # the abort forms: no ON ERROR
    names_ = [n for n, i in sorted(KW["abort"].items(), key=lambda kv: kv[1]) if KWA[i][0][0] == "t"]
    r = kw_run("zznhon", ["RUN bp " + n for n in names_], (A,))
    segs = kw_segments(r.out)
    row("the %d transaction programs ran in ONE session, each aborting and the next going on, and no connection is left" % len(names_),
        not r.hung and r.idle and all(KWA[KW["abort"][n]][0] in segs for n in names_), "hung=%s missing=%r" % (r.hung, [KWA[KW["abort"][n]][0] for n in names_ if KWA[KW["abort"][n]][0] not in segs][:6]))
    for n in names_:
        tag, _p, _m, _pre, _d, _a, texts = KWA[KW["abort"][n]]
        seg = segs.get(tag, [])
        got = kn_abort(seg)
        row("%s INSIDE A TRANSACTION without ON ERROR: the program stops with %r and prints nothing after it" % (tag, texts()[0]), got in texts() and not any("SURVIVED" in x for x in seg), repr(seg[-3:]))
    row("...and the fake saw nothing but login, account, open, close and quit for all of them", all(set(d["types"]) <= {47, 48, 3, 4, 5, 1} for d in r.d), repr(sorted(set(r.d[0]["types"]))))


def kw_gate(A):
    say("\n  -- the S.64 edit gates apply to a remote file by its NAME (voc, a dictionary, bp), asked of the account that is signed in --")
    allow = {"edit_allow": frozenset(["voc", "dict", "prog"])}          # the REMOTE gates are open: only the client's decide
    lines = ["OPEN|1|zznwbp", "OPEN|2|zznwvoc", "ODICT|3|zznw1", "OPEN|4|zznw1", "WRITE|1|prog1|x", "WRITE|2|verb1|x", "WRITE|3|name|x", "WRITE|4|w1|plain", "DELETE|1|prog1", "CLEARFILE|2",
             "WRITEV|1|prog1|x|1", "MATWRITE|1|prog1|a<F>b", "WRITEU|3|name|x", "READ|1|prog1", "CLOSE|1"]
    r = kw_drive(HNED, lines, (A,), cfg=allow)
    got = [x for x in r.kw if not x.startswith(("KW begin", "KW end"))]
    want = ["KW OPEN zznwbp then st=0", "KW OPEN zznwvoc then st=0", "KW ODICT zznw1 then st=0", "KW OPEN zznw1 then st=0", "KW WRITE prog1 error st=3035", "KW WRITE verb1 error st=3035",
            "KW WRITE name error st=3035", kw_plain("WRITE", "w1"), "KW DELETE prog1 error st=3035", "KW CLEARFILE  error st=3035", "KW WRITEV prog1 error st=3035", "KW MATWRITE prog1 error st=3035",
            "KW WRITEU name error st=3035", kw_rec("READ", "prog1", "x"), "KW CLOSE 1"]
    row("AN ACCOUNT WITHOUT THE EDIT GATES (zznhned: the NET gate only): WRITE to the file bp, to voc and to the dictionary of a data file each take ON ERROR with STATUS() 3035 (ER_PERM); DELETE, CLEARFILE, "
        "WRITEV, MATWRITE and WRITEU the same; WRITE to an ordinary data file is made; a READ of bp is not asked", kw_sane(r) and got == want,
        kw_why(r) + " first difference: %r" % (next(((a, b) for a, b in zip(got, want) if a != b), (len(got), len(want))),))
    row("...THE FAKE SAW exactly ONE change request (the WRITE to the ordinary data file): nothing was sent for a refused change, and bp and voc are as they were",
        sum(1 for t in r.d[0]["types"] if t in (16, 17, 18, 19, 31)) == 1 and r.d[0]["types"].count(16) == 1 and r.stores[0][HWBP] == {"prog1": "x"} and r.stores[0][HWVOC] == {"verb1": "V"}
        and r.stores[0][HW].get("w1") == "plain", repr(r.d[0]["types"]))

    # the same account, abort forms: the message names the gate
    names_ = [n for n, i in sorted(KW["abort"].items(), key=lambda kv: kv[1]) if KWA[i][0][0] == "g" and HNED in KWA[i][5]]
    r = kw_run(HNED, ["RUN bp " + n for n in names_], (A,), cfg=allow)
    segs = kw_segments(r.out)
    row("the %d gate programs ran in one session in zznhned, each aborting, and no connection is left" % len(names_), not r.hung and r.idle and all(KWA[KW["abort"][n]][0] in segs for n in names_), "hung=%s" % r.hung)
    for n in names_:
        tag, _p, _m, _pre, _d, _a, texts = KWA[KW["abort"][n]]
        seg = segs.get(tag, [])
        row("%s without ON ERROR: the program stops with %r (the gate named by the remote file's name) and prints nothing after it" % (tag, texts()[0][:60]), kn_abort(seg) in texts() and not any("SURVIVED" in x for x in seg), repr(seg[-3:]))
    row("...and nothing reached the fake that changes anything: only login, account, open, close and quit", all(set(d["types"]) <= {47, 48, 3, 4, 5, 1} for d in r.d), repr(sorted(set(r.d[0]["types"]))))

    # with the gates: zznhon (all on) writes; the account without voc.edit writes bp and the dictionary but not voc
    r = kw_drive("zznhon", ["OPEN|1|zznwbp", "OPEN|2|zznwvoc", "ODICT|3|zznw1", "WRITE|1|prog1|ok1", "WRITE|2|verb1|ok2", "WRITE|3|name|ok3", "CLOSE|1"], (A,), cfg=allow)
    row("CONTROL: the account with all three gates (zznhon) writes bp, voc and the dictionary", kw_sane(r) and kw_plain("WRITE", "prog1") in r.kw and kw_plain("WRITE", "verb1") in r.kw and kw_plain("WRITE", "name") in r.kw
        and r.stores[0][HWBP] == {"prog1": "ok1"} and r.stores[0][HWVOC] == {"verb1": "ok2"}, kw_why(r))
    r = kw_drive(KOFF, ["OPEN|1|zznwbp", "OPEN|2|zznwvoc", "ODICT|3|zznw1", "WRITE|1|prog1|ok1", "WRITE|2|verb1|ok2", "WRITE|3|name|ok3", "CLOSE|1"], (A,), cfg=allow)
    row("...the account with bp.edit and dict.edit but NOT voc.edit (zznhnov) writes bp and the dictionary and is refused voc (STATUS() 3035)", kw_sane(r) and kw_plain("WRITE", "prog1") in r.kw
        and "KW WRITE verb1 error st=3035" in r.kw and kw_plain("WRITE", "name") in r.kw and r.stores[0][HWVOC] == {"verb1": "V"}, kw_why(r))
    names_ = [n for n, i in sorted(KW["abort"].items(), key=lambda kv: kv[1]) if KOFF in KWA[i][5]]
    r = kw_run(KOFF, ["RUN bp " + n for n in names_], (A,), cfg=allow)
    segs = kw_segments(r.out)
    for n in names_:
        tag, _p, _m, _pre, _d, _a, texts = KWA[KW["abort"][n]]
        seg = segs.get(tag, [])
        row("...in the account without voc.edit (zznhnov) %s without ON ERROR stops with %r" % (tag, texts()[0][:60]), not r.hung and kn_abort(seg) in texts() and not any("SURVIVED" in x for x in seg), repr(seg[-3:]))

    # the REMOTE gate is a second layer: the same account (all gates) and the server's own default (no gates) is refused by the server
    r = kw_drive("zznhon", ["OPEN|1|zznwbp", "WRITE|1|prog1|x", "READ|1|prog1", "CLOSE|1"], (A,))
    row("THE SECOND LAYER: the client's gate passes (zznhon) and the server's own gate for a files-only login (off by default) refuses: WRITE takes ON ERROR with STATUS() 7000, the message is the "
        "server's (11500 with the text of 11407), nothing is written", kw_sane(r) and "KW WRITE prog1 error st=7000" in r.kw and kw_rec("READ", "prog1", "x") in r.kw, kw_why(r))

    # the administrator and an $internal program are exempt from the CLIENT's gate; edit_guard asks the key
    r = kw_run(HNED, ["ZZNKWI"], (A,), cfg=allow)
    seg = kw_segments(r.out).get("i", [])
    row("AN $INTERNAL PROGRAM IS EXEMPT from the client's edit gate (as for a local file): in zznhned it writes bp (THEN, STATUS() 0); FILEINFO(f, FL$SETRDONLY) from it makes the handle read only: the next "
        "WRITE takes ON ERROR with STATUS() 7000 and FL$READONLY is 1", not r.hung and "KW i bp then st=0" in seg and "KW i setrdonly error st=7000" in seg and "KW i readonly=1" in seg and r.stores[0][HWBP] == {"prog1": "viaint"}, repr(seg))
    r = kw_run(HNED, ["ZZNKWG"], (A,))
    seg = kw_segments(r.out).get("g", [])
    row("edit_guard (asked by the $internal verbs ED, COPY, DELETE, CLEAR.FILE for a file the user names) of a remote file: in zznhned it answers 0 for bp, voc and a dictionary and 1 for a data file, and shows "
        "the messages 11407, 11405 and 11406", not r.hung and "KW g bp ok=0" in seg and "KW g voc ok=0" in seg and "KW g dict ok=0" in seg and "KW g data ok=1" in seg
        and all(any(msg(n) in ln for ln in r.out) for n in (11405, 11406, 11407)), repr(seg))
    r = kw_run("zznhon", ["ZZNKWG"], (A,))
    seg = kw_segments(r.out).get("g", [])
    row("...and in zznhon (all three gates) it answers 1 for all four", not r.hung and all(("KW g %s ok=1" % w) in seg for w in ("bp", "voc", "dict", "data")), repr(seg))


def kw_lost(A):
    say("\n  -- a lost connection during a change: ON ERROR 7000 / message 11509, the next READ on the variable is an error, a new OPEN reconnects, nothing is sent twice --")
    lines = ["OPEN|1|zznw1", "WRITE|1|w1|lost", "READ|1|w1", "WRITE|1|w1|again", "OPEN|2|zznw1", "READ|2|w1", "CLOSE|1", "CLOSE|2"]
    r = kw_drive("zznhon", lines, (A,), cfg={"drop_after": {16: 1}})
    got = [x for x in r.kw if not x.startswith(("KW begin", "KW end"))]
    want = ["KW OPEN zznw1 then st=0", "KW WRITE w1 error st=7000", kw_rec("READ", "w1", "", "error", 7000), "KW WRITE w1 error st=7000", "KW OPEN zznw1 then st=0", kw_rec("READ", "w1", "lost"),
            "KW CLOSE 1", "KW CLOSE 2"]
    row("A CONNECTION DROPPED AFTER A WRITE WAS EXECUTED: the WRITE takes ON ERROR with STATUS() 7000, the READ and the second WRITE on the same variable are errors (7000: the handle is lost), a new OPEN "
        "reconnects and reads the record the dropped WRITE DID make", kw_sane(r) and got == want, kw_why(r) + " first difference: %r" % (next(((a, b) for a, b in zip(got, want) if a != b), (len(got), len(want))),))
    ses = r.d[0]["sessions"]
    row("...the fake saw two connections and exactly ONE WRITE (16): the lost one was not sent again, and the second WRITE on the lost variable sent nothing", len(ses) == 2 and sum(x.requests.count(16) for x in ses) == 1, repr([x.requests for x in ses]))
    row("...the audit trail: open, write, lost (op=write), open", r.audits == [OPEN_W_AUD, "write server=nfw file=hwork", "lost server=nfw op=write", OPEN_W_AUD], repr(r.audits))


def kw_lifetime(A):
    say("\n  -- a lock does not outlive its file variable past the next prompt; LOGTO drops the connections and the locks --")
    r = kw_run("zznhon", ["RUN bp zznkwl1", "RUN bp zznkwl2"], (A,), watch=(A,))
    seg1, seg2 = kw_segments(r.out).get("l1", []), kw_segments(r.out).get("l2", [])
    w = r.watch[0]
    e = ((HW, "w1", "update"),)
    row("A program READUs a record and ends without CLOSE: the lock is on the fake while it runs, and is GONE after the next command at the prompt - while the SESSION IS STILL OPEN (the next program sleeps "
        "4 seconds): the queued close is sent by kernel(K$NET, -2) in CPROC's paragraph that resets the environment", not r.hung and "KW l1 locked" in seg1 and "KW l2 end" in seg2 and e in w.seq() and w.alive_empty_after_lock(), repr((w.states, seg1, seg2)))
    r = kw_drive("zznhon", ["OPEN|1|zznw1", "READU|1|w1", "SLEEP|2", "EXEC|LOGTO zznhunl", "SLEEP|3", "EXEC|LOGTO zznhon", "SLEEP|1"], (A,), watch=(A,))
    w = r.watch[0]
    row("LOGTO to another account closes the connections: the lock on w1 was on the fake, and the CONNECTION (with its locks) was closed at least 3 seconds before the session ended (the driver goes on "
        "sleeping after the LOGTO)", kw_sane(r) and e in w.seq() and w.seq()[-1] == () and w.closed_at is not None and r.t_end - w.closed_at >= 3.0, repr((w.states, w.closed_at, r.t_end, r.kw[-4:])))


def kw_fileinfo(A):
    say("\n  -- FILEINFO of a write-mode and a read-mode handle --")
    keys = (1001, 1022, 1032, 1038, 1009, 3)
    r = kw_drive("zznhon", ["OPEN|1|zznw1", "OPEN|2|zznwr"] + ["FI|1|%d" % k for k in keys] + ["FI|2|1001", "FI|2|1022", "CLOSE|1", "CLOSE|2"], (A,))
    got = [x for x in r.kw if x.startswith("KW FI")]
    want = ["KW FI 1001 [0]", "KW FI 1022 [1]", "KW FI 1032 [1]", "KW FI 1038 [0]", "KW FI 1009 [-1]", "KW FI 3 [7]", "KW FI 1001 [1]", "KW FI 1022 [1]"]
    row("FILEINFO: FL$READONLY is 0 on the write-mode handle and 1 on the read-mode one (the control); FL$NETFILE 1, FL$NON.TXN 1, FL$TXN.UPDATE 0, FL$FILENO -1 and FL$TYPE 7 as before", kw_sane(r) and got == want, kw_why(r) + " got=%r" % got)


def kw_locking_modes(A):
    say("\n  -- the lock table of the server when the session just ends --")
    r = kw_drive("zznhon", ["OPEN|1|zznw1", "READU|1|w1", "READU|1|w2", "SLEEP|2"], (A,), watch=(A,))
    w = r.watch[0]
    row("a session that ends while it holds locks (no CLOSE, no RELEASE) lets them go with its connection: the fake's table ends empty and a state with two locks was seen", kw_sane(r, need_end=False) and w.seq()[-1] == ()
        and any(len(x) == 2 for x in w.seq()), repr(w.states))


def kw_mode_admin(A):
    say("\n  -- the mode read again at a statement: the administrator's session, the definitions file changed in the middle --")
    hw_flip_files()
    try:
        A.configure(files=True, files_only=True, write_group=True, edit_allow=frozenset(["prog"]))          # the server's own gate for program files is open: only the client's decides
        m = A.mark()
        a0 = audit_size()
        out = g.adm(["RUN bp zznkwadm"], internal=True)
        A.settle(quiet=0.3)
        idle = quiet(A)
        d = A.delta(m)
        A.configure()
        audits = h_audits(audit_since(a0))
        stores = {n: A.store.records(n) for n in (HW, HWBP)}
        wreset(A)
    finally:
        hw_restore_defs()
    kw = [ln for ln in out if ln.startswith("KW ")]
    row("THE ADMINISTRATOR, a pointer written at run time: WRITE (THEN, 0), WRITE to bp (exempt from the edit gate: THEN, 0), then the definitions make nfw MODE READ: WRITE takes ON ERROR with STATUS() 7000, "
        "then MODE WRITE again: WRITE is made", "KW adm write1 then st=0" in kw and "KW adm bp then st=0" in kw and "KW adm write2 error st=7000" in kw and "KW adm write3 then st=0" in kw and "KW adm end" in kw
        and idle and not d["errors"], repr((kw, out[-3:])))
    row("...the fake saw THREE changes only in all (the refused one was not sent), the file holds the third value and bp the administrator's", d["types"].count(16) == 3 and stores[HW].get("w1") == "three"
        and stores[HWBP].get("prog1") == "viaadmin", repr((d["types"], stores)))
    row("...the audit trail: the open of each pointer, the first write, ONE 'refused ... reason=mode' line", audits.count("refused server=nfw reason=mode") == 1 and "write server=nfw file=hwork" in audits, repr(audits))


def kw_refused(A):
    say("\n  -- what stays refused on a WRITE-mode handle says 11511 ('not available'), not 11501 ('read only'); the read-mode control is the existing refusal matrix --")
    names_ = sorted(KW["still"])
    r = kw_run("zznhon", ["RUN bp " + n for n in names_], (A,))
    segs = kw_segments(r.out)
    row("the %d programs ran in ONE session, each aborting and the next going on, and no connection is left" % len(names_), not r.hung and r.idle and all(KW["still"][n][0] in segs for n in names_),
        "hung=%s missing=%r" % (r.hung, [KW["still"][n][0] for n in names_ if KW["still"][n][0] not in segs][:6]))
    for n in names_:
        tag, want = KW["still"][n]
        seg = segs.get(tag, [])
        texts = [msg(11511, "nfw", op) for _num, op in want]
        got = kn_abort(seg)
        row("%s on a WRITE-mode handle: the program stops with %r and prints nothing after it" % (tag.upper(), texts[0] if len(texts) == 1 else texts), got in texts and not any("SURVIVED" in x for x in seg), repr(seg[-3:]))
    row("...the fake saw no request for any of them (only login, account, open, close and quit)", all(set(d["types"]) <= {47, 48, 3, 4, 5, 1} for d in r.d), repr(sorted(set(r.d[0]["types"]))))

    # an id that cannot be sent without ON ERROR
    names2 = [n for n, i in sorted(KW["abort"].items(), key=lambda kv: kv[1]) if KWA[i][0][0] == "i"]
    r = kw_run("zznhon", ["RUN bp " + n for n in names2], (A,))
    segs = kw_segments(r.out)
    for n in names2:
        tag = KWA[KW["abort"][n]][0]
        seg = segs.get(tag, [])
        row("%s: a record id that cannot be sent (empty, or 64 bytes) without ON ERROR stops the program and nothing is sent" % tag, kn_abort(seg) is not None and not any("SURVIVED" in x for x in seg), repr(seg[-3:]))
    row("...the fake saw only login, account, open, close and quit", all(set(d["types"]) <= {47, 48, 3, 4, 5, 1} for d in r.d), repr(sorted(set(r.d[0]["types"]))))


def kw_misc(A):
    say("\n  -- a connection lost without ON ERROR, the verbs, and the whole write section's wire --")
    # the abort form of a lost connection needs its own program in its own session
    g.put(os.path.join(acct_path("zznhon"), "bp", "zznkwlw"), kw_prog("lw", "zznw1", ["write 'x' to f, 'w1'"]))
    out, miss = kn_compile("zznhon", ["zznkwlw"])
    r = kw_run("zznhon", ["RUN bp zznkwlw"], (A,), cfg={"drop_after": {16: 1}}) if not miss else None
    if r is not None:
        seg = kw_segments(r.out).get("lw", [])
        row("A WRITE whose connection is lost, without ON ERROR: the program stops with message 11509 (%r) - the outcome is not known - and prints nothing after it" % msg(11509, "nfw", "write"),
            not r.hung and kn_abort(seg) == msg(11509, "nfw", "write") and not any("SURVIVED" in x for x in seg) and r.idle, repr(seg[-3:]))
    else:
        row("A WRITE whose connection is lost, without ON ERROR: the program compiled", False, repr(out[-4:]))
    # CLEAR.FILE and DELETE as verbs on the VOC name: they only use the statements above; the spec calls them untried
    for cmd in ("CLEAR.FILE zznwbp", "CLEAR.FILE zznw1"):
        acct = HNED if cmd.endswith("zznwbp") else "zznhon"
        r = kw_run(acct, [cmd], (A,), cfg={"edit_allow": frozenset(["voc", "dict", "prog"])})
        say("    [note] %s -> %r (requests: %s)" % (cmd, [x for x in r.out if not x.startswith("KW ")][:4], sorted(set(r.d[0]["types"]))))
        # S.72 (20 Oct 26): the verb CLEAR.FILE locks the file first ($clearfl: filelock, clearfile, fileunlock), so 32 and 33 are requests this section knows now; until then the lock was refused
        # ("filelock is not available for a file on server nfw") and the verb could not clear a write-mode remote file
        row("%s: the session survived, and the fake saw only requests the section knows%s" % (cmd, " (the gate of the account refused the verb: no CLEARFILE request)" if cmd.endswith("zznwbp") else ""),
            not r.hung and kw_types_ok(r, KWALLOWED | {32, 33}) and (not cmd.endswith("zznwbp") or 31 not in r.d[0]["types"]) and r.idle, repr(r.out[-4:]))
        if cmd.endswith("zznw1"):
            t = r.d[0]["types"]
            i32, i31, i33 = (t.index(n) if n in t else -1 for n in (32, 31, 33))
            row("...the verb now CLEARS the write-mode remote file (S.72: it locks the file first, FILELOCK 32, then CLEARFILE 31, then FILEUNLOCK 33, in that order) and the file on the fake is empty "
                "- the same login could already do it with a CLEARFILE statement; before 20 Oct 2026 the verb stopped at its FILELOCK with 'filelock is not available'",
                0 <= i32 < i31 < i33 and r.stores[0][HW] == {} and "not available" not in " ".join(r.out), repr((t, r.stores[0][HW], r.out[-4:])))
    # the LOCKING keyword of the query verbs locks the source file first (qproc: filelock data.f)
    r = kw_run("zznhon", ["LIST zznw1 LOCKING"], (A,))
    t = r.d[0]["types"]
    say("    [note] LIST zznw1 LOCKING -> %r (requests: %s)" % ([x for x in r.out if not x.startswith("KW ")][:6], sorted(set(t))))
    row("LIST zznw1 LOCKING (S.72, the query processor's LOCKING keyword locks the source file): the session survived, the list was printed (3 records), the file lock was asked for (request 32) before the "
        "select (11) and the reads of the records, and the fake saw only requests the section knows (the query's own: the dictionary reads, select, readlist, reads)",
        not r.hung and kw_types_ok(r, KWALLOWED | {11, 14, 32, 33}) and 32 in t and 11 in t and t.index(32) < t.index(11) and any(re.match(r"^3 record\(s\) listed", x) for x in r.out) and r.idle,
        repr((t, r.out[-6:])))


def kw_filelocks(A):
    say("\n  -- FILELOCK, FILEUNLOCK, RECORDLOCKED() and GETLOCKS() (S.72, 20 Oct 26): the statements of an ordinary session on a write-mode file, and on a read-mode one --")
    FL = (HW, "", "file")                                              # how the fake's lock table shows a file lock (FakeStore.locks_of)
    own = r"[1-9][0-9]*"                                                  # a user number of the fake (it numbers its connections itself)

    # THE LOCAL CONTROL: the same statements on a local file say what a remote one must say
    r = kw_run("zznhon", ["RUN bp zznkwc"], (A,))
    seg = kw_segments(r.out).get("c", [])
    row("CONTROL (a LOCAL file, the account's VOC): FILELOCK, RECORDLOCKED() 3 while this session holds it, FILEUNLOCK leaves STATUS() 0, RECORDLOCKED() 0 with STATUS() 0 once free, a second "
        "FILEUNLOCK leaves STATUS() 3012 (ER$NLK) - the values the rows below require of a remote file",
        not r.hung and seg == ["KW c recordlocked-own-filelock x=3", "KW c unlock-own st=0", "KW c recordlocked-free x=0 st=0", "KW c unlock-nobody st=3012", "KW c end"] and r.idle, repr(seg))

    # 1. a free file, the whole life of a file lock, the wire and the audit trail
    lines = ["OPEN|1|zznw1", "FLOCK|1", "SLEEP|1", "RLCKD|1|w1", "FLOCK|1", "FUNLOCK|1", "SLEEP|1", "RLCKD|1|w1", "FUNLOCK|1", "CLOSE|1"]
    r = kw_drive("zznhon", lines, (A,), watch=(A,))
    got = [x for x in r.kw if not x.startswith(("KW begin", "KW end", "KW SLEEP"))]
    want_re = [r"^KW OPEN zznw1 then st=0$", r"^KW FLOCK  then st=0$", r"^KW RLCKD w1 x=3 st=%s$" % own, r"^KW FLOCK  then st=0$", r"^KW FUNLOCK  then st=0$", r"^KW RLCKD w1 x=0 st=0$",
               r"^KW FUNLOCK  then st=3012$", r"^KW CLOSE 1$"]
    row("FILELOCK on a free file of a write-mode server: THEN, STATUS() 0; RECORDLOCKED() 3 (this session holds the file lock) with STATUS() the server's user number; FILELOCK again: still 0; "
        "FILEUNLOCK: STATUS() 0; RECORDLOCKED() 0 with STATUS() 0; a second FILEUNLOCK leaves STATUS() 3012 - the values of the local control above",
        kw_sane(r) and len(got) == len(want_re) and all(re.match(p, x) for p, x in zip(want_re, got)), kw_why(r) + " got=%r" % got)
    wire = kn_wire(r.d[0])
    exp = [ACCT_REQ, W_OPEN(HW), W_FLK(1), W_RLK(1, "w1"), W_FLK(1), W_FUL(1), W_RLK(1, "w1"), W_FUL(1), (5, FNO(1))]
    row("...THE REQUESTS: 32 (file number, wait flag 0) twice, 34 for each RECORDLOCKED(), 33 twice, then the CLOSE (5) - the wait flag is never set", wire == exp,
        "first difference: %r" % (next(((a, b) for a, b in zip(wire, exp) if a != b), (len(wire), len(exp))),))
    ls = r.watch[0].seq()
    row("...THE FAKE'S LOCK TABLE, watched during the session: no lock, the FILE lock (%s), no lock again after FILEUNLOCK" % (FL,), ls == [(), (FL,), ()], repr(ls))
    row("...the audit trail: the open line and ONE 'filelock server=nfw file=hwork' line (once for the handle, written before the first request; no id, no record)",
        r.audits == [OPEN_W_AUD, "filelock server=nfw file=hwork"], repr(r.audits))

    # 2. another user holds the file lock, or a record lock in the file
    A.store.hold_file(HW, 7)
    try:
        r = kw_drive("zznhon", ["OPEN|1|zznw1", "FLOCK|1", "RLCKD|1|w1", "FUNLOCK|1", "RLCKD|1|w1", "CLOSE|1"], (A,))
    finally:
        A.store.drop_user(7)
    got = [x for x in r.kw if not x.startswith(("KW begin", "KW end"))]
    want = ["KW OPEN zznw1 then st=0", "KW FLOCK  locked st=7", "KW RLCKD w1 x=-3 st=7", "KW FUNLOCK  then st=3011", "KW RLCKD w1 x=-3 st=7", "KW CLOSE 1"]
    row("A FILE LOCK ANOTHER USER (7) HOLDS: FILELOCK takes the LOCKED branch with STATUS() 7 (the holder); RECORDLOCKED() -3 with STATUS() 7; FILEUNLOCK leaves STATUS() 3011 (ER$LCK) and the lock "
        "is still user 7's (the last RECORDLOCKED() says -3 again, with 7)", kw_sane(r) and got == want, kw_why(r) + " got=%r" % (got,))
    row("...THE REQUESTS: 32, 34, 33, 34 and the close", kn_wire(r.d[0]) == [ACCT_REQ, W_OPEN(HW), W_FLK(1), W_RLK(1, "w1"), W_FUL(1), W_RLK(1, "w1"), (5, FNO(1))], repr(kn_wire(r.d[0])))
    A.store.hold(HW, "w2", 8, "update")
    try:
        r = kw_drive("zznhon", ["OPEN|1|zznw1", "SLEEP|1", "FLOCK|1", "SLEEP|1", "CLOSE|1"], (A,), watch=(A,))
    finally:
        A.store.drop_user(8)
    row("AN UPDATE LOCK ANOTHER USER (8) HOLDS ON A RECORD of the file: FILELOCK takes the LOCKED branch with STATUS() 8, and no file lock was taken (the fake's table, watched, never held one for this session)",
        kw_sane(r) and "KW FLOCK  locked st=8" in r.kw and all(FL not in locks for locks in r.watch[0].seq()), kw_why(r) + repr(r.watch[0].seq()))

    # 3. no LOCKED clause: a busy file is waited for by asking again, never by making the server wait
    A.store.hold_file(HW, 7)
    r = kw_drive("zznhon", ["OPEN|1|zznw1", "TIME", "FLOCKW|1", "TIME", "RLCKD|1|w1", "CLOSE|1"], (A,), holders=((A, 7, 3.0),))
    times = [int(m.group(1)) for m in (re.match(r"^KW TIME (\d+)$", x) for x in r.kw) if m]
    types = r.d[0]["types"]
    waits = [struct.unpack("<h", d[2:4])[0] for _c, t, d in r.d[0]["packets"] if t == 32]
    row("FILELOCK with no LOCKED clause on a file another user holds: the statement WAITS (the holder lets go about 3 seconds after the first request) and then succeeds with STATUS() 0, and the file "
        "lock is this session's (RECORDLOCKED() 3)", kw_sane(r) and "KW FLOCKW  then st=0" in r.kw and len(times) == 2 and 2 <= (times[1] - times[0]) % 86400 <= 30
        and any(re.match(r"^KW RLCKD w1 x=3 st=%s$" % own, x) for x in r.kw), kw_why(r) + " times=%r" % times)
    row("...THE FAKE SAW %d requests of type 32, every one with the wait flag 0 (%s) - the server was never asked to block - and none of the server's own waiting forms (30, 7 to 10)" % (len(waits), sorted(set(waits))),
        len(waits) >= 5 and set(waits) == {0} and not {7, 8, 9, 10, 30} & set(types), repr((types, waits)))

    # 4. how long a file lock lives
    r = kw_drive("zznhon", ["OPEN|1|zznw1", "FLOCK|1", "SLEEP|1", "CLOSE|1", "SLEEP|1"], (A,), watch=(A,))
    w = r.watch[0]
    row("CLOSE of the file variable releases the file lock: it was on the fake's table during the session and gone BEFORE the session ended (a state with no lock was seen while it was still open)",
        kw_sane(r) and (FL,) in w.seq() and w.alive_empty_after_lock(), repr(w.states))
    r = kw_run("zznhon", ["RUN bp zznkwf1", "RUN bp zznkwf2"], (A,), watch=(A,))
    seg1, seg2 = kw_segments(r.out).get("f1", []), kw_segments(r.out).get("f2", [])
    w = r.watch[0]
    row("A program takes the file lock and ends without CLOSE or FILEUNLOCK: the lock is on the fake while it runs and is GONE after the next command at the prompt, while the session is still open "
        "(the next program sleeps 4 seconds)", not r.hung and "KW f1 locked" in seg1 and "KW f2 end" in seg2 and (FL,) in w.seq() and w.alive_empty_after_lock(), repr((w.states, seg1, seg2)))
    r = kw_drive("zznhon", ["OPEN|1|zznw1", "FLOCK|1", "SLEEP|2", "EXEC|LOGTO zznhunl", "SLEEP|3", "EXEC|LOGTO zznhon", "SLEEP|1"], (A,), watch=(A,))
    w = r.watch[0]
    row("LOGTO to another account closes the connection and the file lock goes with it: the lock was on the fake, and the connection ended at least 3 seconds before the session did",
        kw_sane(r) and (FL,) in w.seq() and w.seq()[-1] == () and w.closed_at is not None and r.t_end - w.closed_at >= 3.0, repr((w.states, w.closed_at, r.t_end, r.kw[-4:])))
    r = kw_drive("zznhon", ["OPEN|1|zznw1", "FLOCK|1", "SLEEP|2"], (A,), watch=(A,))
    w = r.watch[0]
    row("a session that ends while it holds the file lock (no FILEUNLOCK, no CLOSE) lets it go with its connection: the fake's table, watched, showed the lock and then none", kw_sane(r, need_end=False)
        and (FL,) in w.seq() and w.seq()[-1] == (), repr(w.states))

    # RELEASE f and a bare RELEASE give a file lock back too (measured on the real server by sandbox-req29.py F44-F47: the server's RELEASE does)
    r = kw_drive("zznhon", ["OPEN|1|zznw1", "FLOCK|1", "RLCKD|1|w1", "RELEASEF|1", "RLCKD|1|w1", "FLOCK|1", "RLCKD|1|w1", "RELEASEA|1", "RLCKD|1|w1", "CLOSE|1"], (A,))
    got = [x for x in r.kw if x.startswith("KW RLCKD")]
    want_re = [r"^KW RLCKD w1 x=3 st=%s$" % own, r"^KW RLCKD w1 x=0 st=0$", r"^KW RLCKD w1 x=3 st=%s$" % own, r"^KW RLCKD w1 x=0 st=0$"]
    row("RELEASE f (the file form) and a bare RELEASE give the file lock back, as on the server's own files: RECORDLOCKED() says 3 while it is held and 0 after each",
        kw_sane(r) and len(got) == 4 and all(re.match(p, x) for p, x in zip(want_re, got)), kw_why(r) + " got=%r" % got)
    exp = [ACCT_REQ, W_OPEN(HW), W_FLK(1), W_RLK(1, "w1"), W_REL(1), W_RLK(1, "w1"), W_FLK(1), W_RLK(1, "w1"), W_REL(0), W_RLK(1, "w1"), (5, FNO(1))]
    row("...THE REQUESTS: RELEASE f is request 15 with the file number only, a bare RELEASE is request 15 with file number 0", kn_wire(r.d[0]) == exp,
        "first difference: %r" % (next(((a, b) for a, b in zip(kn_wire(r.d[0]), exp) if a != b), (len(kn_wire(r.d[0])), len(exp))),))

    # 5. RECORDLOCKED() on a write-mode handle, and the record locks of other users (S.72b: the READ-mode handle that used to be here is refused now - kw_peek, the matrix KM)
    A.store.hold(HW, "w2", 7, "update")
    A.store.hold(HW, "w3", 8, "shared")
    try:
        lines = ["OPEN|1|zznw1", "RLCKD|1|w1", "RLCKD|1|w2", "RLCKD|1|w3", "READU|1|w1", "RLCKD|1|w1", "RELEASE|1|w1", "RLCKD|1|w1", "READL|1|w1", "RLCKD|1|w1", "CLOSE|1"]
        r = kw_drive("zznhon", lines, (A,))
    finally:
        A.store.drop_user(7)
        A.store.drop_user(8)
    got = [x for x in r.kw if x.startswith("KW RLCKD")]
    want_re = [r"^KW RLCKD w1 x=0 st=0$", r"^KW RLCKD w2 x=-2 st=7$", r"^KW RLCKD w3 x=-1 st=8$", r"^KW RLCKD w1 x=2 st=%s$" % own, r"^KW RLCKD w1 x=0 st=0$", r"^KW RLCKD w1 x=1 st=%s$" % own]
    row("RECORDLOCKED() on a write-mode handle: free 0 (STATUS() 0), another user's update lock -2 (STATUS() 7), another user's read lock -1 (8), this session's update lock 2 and read lock 1 (STATUS() its own "
        "server user number), 0 after RELEASE",
        kw_sane(r) and len(got) == len(want_re) and all(re.match(p, x) for p, x in zip(want_re, got)), kw_why(r) + " got=%r" % got)
    exp = [ACCT_REQ, W_OPEN(HW), W_RLK(1, "w1"), W_RLK(1, "w2"), W_RLK(1, "w3"), W_LOCK(1, "w1", True), W_READ(1, "w1"), W_RLK(1, "w1"), W_REL(1, "w1"), W_RLK(1, "w1"), W_LOCK(1, "w1", False),
           W_READ(1, "w1"), W_RLK(1, "w1"), (5, FNO(1))]
    row("...THE REQUESTS: every RECORDLOCKED() is request 34 with the file number and the id", kn_wire(r.d[0]) == exp,
        "first difference: %r; the last three on the wire: %r" % (next(((a, b) for a, b in zip(kn_wire(r.d[0]), exp) if a != b), (len(kn_wire(r.d[0])), len(exp))), kn_wire(r.d[0])[-3:]))
    r = kw_drive("zznhon", ["OPEN|1|zznwr", "FLOCK|1", "FUNLOCK|1", "CLOSE|1"], (A,))
    row("CONTROL, a READ-mode handle: FILELOCK and FILEUNLOCK take ON ERROR with STATUS() 7000 (message 11501, nothing sent), like RECORDLOCKED() since S.72b (kw_peek: it stops the program); the fake saw "
        "login, account, open, close and quit only", kw_sane(r) and "KW FLOCK  error st=7000" in r.kw and "KW FUNLOCK  error st=7000" in r.kw and set(r.d[0]["types"]) <= {47, 48, 3, 4, 5, 1}, kw_why(r))

    # 6. RECORDLOCKED() in a transaction is a read and is served (S.72b: for a write-mode handle, NETG_PEEK skips the transaction test); FILELOCK and FILEUNLOCK there are refused
    r = kw_drive("zznhon", ["OPEN|1|zznw1", "TFLOCK|1", "TFUNLOCK|1", "TRLCKD|1|w1", "FLOCK|1", "FUNLOCK|1", "CLOSE|1"], (A,))
    row("INSIDE A TRANSACTION FILELOCK and FILEUNLOCK take ON ERROR with STATUS() 1010 (ER_TXN, message 11510), RECORDLOCKED() is served (a read); after it the same handle locks and unlocks",
        kw_sane(r) and "KW TFLOCK  error st=1010" in r.kw and "KW TFUNLOCK  error st=1010" in r.kw and "KW TRLCKD w1 x=0 st=0" in r.kw and "KW FLOCK  then st=0" in r.kw
        and "KW FUNLOCK  then st=0" in r.kw and kn_wire(r.d[0]) == [ACCT_REQ, W_OPEN(HW), W_RLK(1, "w1"), W_FLK(1), W_FUL(1), (5, FNO(1))], kw_why(r) + repr(kn_wire(r.d[0])))
    # the null case of the row above: with a lock REALLY held the answer inside the transaction is 2 (this session's update lock) and -2 (user 7's), not 0 - a refused or empty answer would be neither
    A.store.hold(HW, "w2", 7, "update")
    try:
        r = kw_drive("zznhon", ["OPEN|1|zznw1", "READU|1|w1", "TRLCKD|1|w1", "TRLCKD|1|w2", "TRLCKD|1|w3", "READL|1|w3", "TRLCKD|1|w3", "RELEASE|1|w1", "TRLCKD|1|w1", "CLOSE|1"], (A,))
    finally:
        A.store.drop_user(7)
    got = [x for x in r.kw if x.startswith("KW TRLCKD")]
    want_re = [r"^KW TRLCKD w1 x=2 st=%s$" % own, r"^KW TRLCKD w2 x=-2 st=7$", r"^KW TRLCKD w3 x=0 st=0$", r"^KW TRLCKD w3 x=1 st=%s$" % own, r"^KW TRLCKD w1 x=0 st=0$"]
    exp = [ACCT_REQ, W_OPEN(HW), W_LOCK(1, "w1", True), W_READ(1, "w1"), W_RLK(1, "w1"), W_RLK(1, "w2"), W_RLK(1, "w3"), W_LOCK(1, "w3", False), W_READ(1, "w3"), W_RLK(1, "w3"), W_REL(1, "w1"),
           W_RLK(1, "w1"), (5, FNO(1))]
    row("[S72b-N10] INSIDE BEGIN TRANSACTION RECORDLOCKED() of a WRITE-mode handle is still SERVED (NETG_PEEK skips the transaction test: it is a read and changes nothing - the recorded choice): the lock this "
        "session took with READU shows as 2 and its READL as 1 (STATUS() its own user number), user 7's update lock as -2 (STATUS() 7), a free record as 0, and 0 after RELEASE; the requests are 34 each, with their bytes",
        kw_sane(r) and len(got) == len(want_re) and all(re.match(p, x) for p, x in zip(want_re, got)) and kn_wire(r.d[0]) == exp,
        kw_why(r) + " got=%r wire first difference %r" % (got, next(((a, b) for a, b in zip(kn_wire(r.d[0]), exp) if a != b), (len(kn_wire(r.d[0])), len(exp)))))
    r = kw_drive("zznhon", ["OPEN|1|zznw1", "FLOCK|1", "TRLCKD|1|w1", "FUNLOCK|1", "TRLCKD|1|w1", "CLOSE|1"], (A,))
    got = [x for x in r.kw if x.startswith("KW TRLCKD")]
    want_re = [r"^KW TRLCKD w1 x=3 st=%s$" % own, r"^KW TRLCKD w1 x=0 st=0$"]
    row("[S72b-N10] ...and the FILE lock this session holds shows as 3 inside the transaction (STATUS() its own user number), 0 after FILEUNLOCK",
        kw_sane(r) and len(got) == len(want_re) and all(re.match(p, x) for p, x in zip(want_re, got)), kw_why(r) + " got=%r" % got)

    # 7. GETLOCKS(): the local view
    r = kw_run("zznhon", ["ZZNKWK"], (A,))
    seg = kw_segments(r.out).get("k", [])
    want = ["KW k remote fields=1 values=3", "KW k remote-read fields=1 values=3", "KW k remote-user fields=1 values=3", "KW k local fields=2 id=ZZNW1 type=RU", "KW k all fields=2 has-local=1",
            "KW k counters-equal=1", "KW k remote-has-local-lock=0", "KW k end"]
    row("GETLOCKS() (an internal function) of a remote file, write mode or read mode, with a user number or without, is the LOCAL view: ONE field of three numbers (NUMLOCKS, the lock count, the peak) and "
        "no lock line - not the local record lock this session holds, which GETLOCKS() of a local file and of 'every file' do list (the control) - and the counters are the local table's own",
        not r.hung and seg == want, repr(seg))
    row("...and the fake was asked NOTHING for it: only the two opens and the closes", all(set(d["types"]) <= {47, 48, 3, 4, 5, 1} for d in r.d) and r.idle, repr([d["types"] for d in r.d]))

    # 8. MUSTLOCK: a file lock covers every record, as locally
    r = kw_run("zznhon", ["ZZNKWM2"], (A,))
    seg = kw_segments(r.out).get("m2", [])
    wire = kn_wire(r.d[0])
    exp = [ACCT_REQ, W_OPEN(HW), W_FLK(1), W_RLK(1, "w1"), W_WRITE(1, "w1", "viafilelock"), W_FUL(1), W_RLK(1, "w1")]
    row("MUSTLOCK (the client's) and a file lock: with the file lock held a WRITE of a record the session has NOT locked is made (the server says 3: the session holds the file lock), after FILEUNLOCK the same "
        "WRITE is refused with 3023 and sends no change", not r.hung and seg == ["KW m2 filelock then", "KW m2 write-under-filelock then st=0", "KW m2 write-after-unlock error st=3023", "KW m2 end"]
        and wire[:len(exp)] == exp and sum(1 for t in r.d[0]["types"] if t in (16, 17, 18, 19)) == 1 and r.stores[0][HW].get("w1") == "viafilelock", repr((seg, wire[:8])))

    # 9. a connection lost without ON ERROR: the lock statements stop with 11497, not 11509 (they change no data)
    for tag, stmt, cfg, op in (("lf", "filelock f", {"drop_after": {32: 1}}, "filelock"), ("lu", "fileunlock f", {"drop_after": {33: 1}}, "fileunlock"),
                               ("lr", "x = recordlocked(f, 'w1')", {"drop_after": {34: 1}}, "recordlocked")):
        name = "zznkwx" + tag
        g.put(os.path.join(acct_path("zznhon"), "bp", name), kw_prog(tag, "zznw1", [stmt]))
        out, miss = kn_compile("zznhon", [name])
        if miss:
            row("%s with the connection lost, without ON ERROR: the program compiled" % op, False, repr(out[-4:]))
            continue
        r = kw_run("zznhon", ["RUN bp " + name], (A,), cfg=cfg)
        seg = kw_segments(r.out).get(tag, [])
        row("%s whose connection is lost after the server did it, without ON ERROR: the program stops with message 11497 (%r) and prints nothing after it" % (op.upper(), msg(11497, "nfw", op)),
            not r.hung and kn_abort(seg) == msg(11497, "nfw", op) and not any("SURVIVED" in x for x in seg) and r.idle, repr(seg[-3:]))


def kw_peek(A):
    """S.72b: RECORDLOCKED() of a remote file is write-governed.  The CLIENT's line: a read-mode handle (the definition says read, or the variable was made read only) stops the program with 11501 and
    nothing is sent; a write-mode handle is served.  The SERVER's wall: a files-only login WITHOUT sdfileswrite is refused request 34 (message 11521), whatever this machine does, and MUSTLOCK, which asks the
    same question before a write, runs into the same wall.  Every refusal row has its null case: the same lock asked through a handle that is served says -2 (user 7's lock), never 0."""
    say("\n  -- RECORDLOCKED() is write-governed (S.72b): a read-mode handle is refused at the client and nothing is sent; a login without the write group is refused by the server; MUSTLOCK meets the same wall --")
    nm = {KWA[i][0]: n for n, i in KW["abort"].items()}

    # 1. a READ-mode handle (the definition nfa says read): refused by the kernel, nothing sent.  User 7 holds w2 so that a request would have been answered -2.
    # (every kw_run puts the files and the lock table back at its end, so the hold is planted again before each run)
    A.store.hold(HW, "w2", 7, "update")
    try:
        r = kw_run("zznhon", ["RUN bp " + nm["rrd"]], (A,))
        A.store.hold(HW, "w2", 7, "update")
        c = kw_drive("zznhon", ["OPEN|1|zznw1", "RLCKD|1|w2", "CLOSE|1"], (A,))
    finally:
        A.store.drop_user(7)
    seg = kw_segments(r.out).get("rrd", [])
    row("[S72b-N9] RECORDLOCKED() on a READ-MODE handle (zznwr: the definition nfa says read) of a record user 7 holds an update lock on stops the program (the function has no ON ERROR clause) with message 11501 "
        "naming nfa and 'recordlocked' (%r) and prints nothing after it" % msg(11501, "nfa", "recordlocked"),
        not r.hung and kn_abort(seg) == msg(11501, "nfa", "recordlocked") and not any("SURVIVED" in x for x in seg) and r.idle, repr(seg[-3:]))
    row("...[S72b-N9] NOTHING WAS SENT: the fake's packet log holds login, account, open, close and quit only - no request 34 (types %r)" % sorted(set(r.d[0]["types"])),
        set(r.d[0]["types"]) <= {47, 48, 3, 4, 5, 1} and 4 in r.d[0]["types"] and 34 not in r.d[0]["types"], repr(r.d[0]["types"]))
    row("...NULL CASE: the same lock asked through a WRITE-mode handle (zznw1, the same file) is served: x=-2 with STATUS() 7, and the request 34 is on the wire",
        kw_sane(c) and "KW RLCKD w2 x=-2 st=7" in c.kw and 34 in c.d[0]["types"], kw_why(c))

    # 2. the variable made READ ONLY after the open (FILEINFO FL$SETRDONLY, internal programs only): served before, refused after, ONE request 34 in all
    A.store.hold(HW, "w2", 7, "update")
    try:
        r = kw_run("zznhon", ["ZZNKWR"], (A,))
    finally:
        A.store.drop_user(7)
    seg = kw_segments(r.out).get("r", [])
    row("[S72b-N9b] RECORDLOCKED() on a variable made READ ONLY after the open (FL$SETRDONLY): before it x=-2 with STATUS() 7 (served), after it the program stops with message 11501 naming nfw and 'recordlocked' "
        "(%r) and prints nothing after it; the fake saw exactly ONE request 34" % msg(11501, "nfw", "recordlocked"),
        not r.hung and "KW r before x=-2 st=7" in seg and kn_abort(seg) == msg(11501, "nfw", "recordlocked") and not any("SURVIVED" in x for x in seg) and r.d[0]["types"].count(34) == 1 and r.idle,
        repr(seg[-4:]) + repr(r.d[0]["types"]))

    # 3. a WRITE-mode handle and a login WITHOUT sdfileswrite: the request goes out and the SERVER refuses it (11500 with the text of 11521); WITH the group it is served
    A.store.hold(HW, "w2", 7, "update")
    try:
        r_no = kw_run("zznhon", ["RUN bp " + nm["rwg"]], (A,), cfg={"write_group": False})
        A.store.hold(HW, "w2", 7, "update")
        r_yes = kw_run("zznhon", ["RUN bp " + nm["rwg"]], (A,))
    finally:
        A.store.drop_user(7)
    seg = kw_segments(r_no.out).get("rwg", [])
    sess = r_no.d[0]["sessions"]
    text = msg(11500, "nfw", "recordlocked", msg(11521, 34))
    row("[S72b-N11] RECORDLOCKED() on a WRITE-mode handle by a files-only login WITHOUT sdfileswrite: the program stops with message 11500 %r (the server's text, with the request number 34) and prints nothing "
        "after it" % text, not r_no.hung and kn_abort(seg) == text and not any("SURVIVED" in x or "x=" in x for x in seg) and r_no.idle, repr(seg[-3:]))
    row("...[S72b-N11] THE REQUEST WENT OUT AND THE SERVER REFUSED IT (the wall is the server's): exactly one request 34 on the wire, the fake refused [34] and audited 'api refused request=34 route=sdfiles write=off "
        "user=alice'", r_no.d[0]["types"].count(34) == 1 and len(sess) == 1 and sess[0].refused == [34] and sess[0].audit == ["api refused request=34 route=sdfiles write=off user=alice"]
        and set(r_no.d[0]["types"]) <= {47, 48, 3, 4, 34, 5, 1}, repr((r_no.d[0]["types"], [(s.refused, s.audit) for s in sess])))
    seg = kw_segments(r_yes.out).get("rwg", [])
    row("...NULL CASE, the same program IN sdfileswrite: served - x=-2 with STATUS() 7 (user 7's lock), the program survives, nothing is refused",
        not r_yes.hung and "KW rwg x=-2 st=7" in seg and any(x.startswith("KW rwg SURVIVED") for x in seg) and kn_abort(seg) is None and all(not s.refused and not s.audit for s in r_yes.d[0]["sessions"]), repr(seg[-3:]))



def mustlock_section():
    """S.72b, N13: MUSTLOCK (the client's, set by an internal program) asks the same question (request 34) before a write: WITH the group it is unchanged (the row of kw_busy: 3023, then the write
    goes on); WITHOUT it the question is refused by the server, so the write or delete ends with ON ERROR / STATUS() 7000 and NOTHING is written.  THIS SECTION RUNS LAST, and the reason is a fact: if the
    refusal of request 34 is NOT turned into an ON ERROR status (the class aborting inside the handler, as on the unchanged tree), the program ZZNKWM dies with MUSTLOCK still on in its process, the
    command processor's own writes are then refused (3023) and the session never comes back; the session killed after the time limit leaves the sandbox wedged and every later session hangs - measured
    20 Oct 26 on the unchanged tree.  Put anywhere else, one red row here would turn all the rows after it red for no reason of their own."""
    say("\n--- MUSTLOCK meets the server's wall (S.72b, last because a red row here wedges the sandbox) ---")
    if not kw_prep():
        return
    A = S["A"]
    r = kw_run("zznhon", ["ZZNKWM"], (A,), cfg={"write_group": False})
    seg = kw_segments(r.out).get("m", [])
    sess = r.d[0]["sessions"]
    want = ["KW m write-nolock error st=7000", "KW m delete-nolock error st=7000", "KW m readu error st=7000 rec=[]", "KW m write-locked error st=7000", "KW m end"]
    row("[S72b-N13] MUSTLOCK, a files-only login WITHOUT sdfileswrite: the WRITE and the DELETE of a record the session has not locked end with ON ERROR / STATUS() 7000 (they were 3023: the server refused the "
        "request-34 question), READU (the lock) is refused as well, and the WRITE after it is again 7000 - the lines the program printed, in order", not r.hung and seg == want and r.idle, repr(seg))
    row("...[S72b-N13] NOTHING WAS WRITTEN (the fake's file as it is, not the printed text): w1 and w2 hold their first records, the fake saw no change request (16 to 19) and refused 34, 34, 30, 34 "
        "(the MUSTLOCK question twice, the lock, the MUSTLOCK question again)", r.stores[0][HW] == dict(HWREC) and not {16, 17, 18, 19} & set(r.d[0]["types"]) and len(sess) == 1 and sess[0].refused == [34, 34, 30, 34]
        and sess[0].audit == ["api refused request=%d route=sdfiles write=off user=alice" % n for n in (34, 34, 30, 34)], repr((r.stores[0][HW], r.d[0]["types"], [s.refused for s in sess])))


# ---- W. the write group (18 Oct 26, section wgroup) ---------------------------------------------------------------------------------------------
#
# A files-only login on the TARGET server may change files and take locks only if the user is also in the Linux group sdfileswrite (gpl.bp/apifilesok's third argument;
# the owner's yes of 18 Oct 2026).  A server DEFINITION that says mode=write on the client is necessary and no longer enough: the target's administrator decides.  The fake
# models the target with the cfg write_group (False is the real default), and refuses the change set with message 11521 as an ON ERROR reply.  WHAT THE FAKE CANNOT SHOW:
# that the REAL apisrvr does the same for a real files-only login (the group is read from /etc/group at the SCRAM login), which is the VM witness.  What the CLIENT shows
# for a refusal is "11500 ... <the text of 11521>" since 19 Oct 26 (K1): the handler shows the text of an ON ERROR reply, and message 11521 is short enough (98 characters) not to
# be cut at 100.  Until then it showed "status 0" and the person at the client only saw that the change failed; the administrator of the target also sees the request number in
# the target's audit trail (api refused request=N route=sdfiles write=off).  The rows build the expected text from the sandbox's own message file, never from the reply.
# S.72b (20 Oct 26): request 34 (recordlocked) is in the change set as well - the holder's user number on the target is not for a login that cannot lock - so the rows below that used to say
# "RECORDLOCKED is served" say "refused, 11521 with the request number 34", and the fake (FileSession.refuse) keeps the target's audit line for each refusal (ses.audit).

def wgroup_section():
    say("\n--- the write group (18 Oct 26): a files-only login on the target WITHOUT sdfileswrite can read and select but every change and every lock is refused; WITH it the same program changes the file ---")
    if not hw_prep() or not kw_prep():
        return
    A = S["A"]
    row("INSTRUMENT: message 11521 (the refusal's text) is at most 100 characters for each request number below, so the rows compare the WHOLE text the client shows and not its first 100 - "
        "a text that was cut would agree with itself", all(0 < len(msg(11521, n)) <= 100 for n in (16, 17, 18, 19, 30, 31, 32, 33, 34)), repr([len(msg(11521, n)) for n in (16, 17, 18, 19, 30, 31, 32, 33, 34)]))
    s = Script()
    s.add("OPEN", "nfw", HW, ok=k_open_w(1), audit=OPEN_W_AUD)
    s.add("READ", 1, "w1", label="WITHOUT the group: a READ is served (the record comes back) - reading needs sdfiles alone", ok=k_rec(HWREC["w1"]))
    s.add("WRITE", 1, "w1", "x", label="...WRITE is refused: rc 3, message 11500 naming the server and 'write', and the TEXT of message 11521 with the request number (16) - the target's reason, "
          "shown to the person at the client since 19 Oct 26 (K1; it was 'status 0'), rc<6> 0", ok=k_srverr("write", 0, text=msg(11521, 16)), audit="write server=nfw file=hwork")
    s.add("WRITEU", 1, "w2", "x", label="...WRITEU is refused (request 17)", ok=k_srverr("writeu", 0, text=msg(11521, 17)))
    s.add("DELETE", 1, "w3", label="...DELETE is refused (request 18)", ok=k_srverr("delete", 0, text=msg(11521, 18)), audit="delete server=nfw file=hwork")
    s.add("DELETEU", 1, "w3", label="...DELETEU is refused (request 19)", ok=k_srverr("deleteu", 0, text=msg(11521, 19)))
    s.add("LOCK", 1, "w1", "u", label="...a LOCK (update) is refused: a lock is a change of state on the target (request 30)", ok=k_srverr("lock", 0, text=msg(11521, 30)))
    s.add("LOCK", 1, "w1", "l", label="...a LOCK (shared) is refused too (request 30)", ok=k_srverr("lock", 0, text=msg(11521, 30)))
    s.add("CLEARFILE", 1, label="...CLEARFILE is refused (request 31)", ok=k_srverr("clear.file", 0, text=msg(11521, 31)), audit="clear server=nfw file=hwork")
    s.add("READ", 1, "w1", label="...and the handler goes on: the same READ is served again, the record unchanged", ok=k_rec(HWREC["w1"]))
    # (RECORDLOCKED is the LAST call before CLOSEALL on purpose: where the class aborts instead of reporting the server's refusal - the unchanged tree - the program stops at it, and the rows above are
    # still judged for what they are)
    s.add("RLOCKED", 1, "w1", label="[S72b-N6] ...RECORDLOCKED is REFUSED too (S.72b: request 34 is in the change set - the lock owner's number is not for a login that cannot lock; it was served): rc 3, message 11500 "
          "naming the server and 'recordlocked', and the TEXT of message 11521 with the request number (34), rc<6> 0", ok=k_srverr("recordlocked", 0, text=msg(11521, 34)))
    s.add("CLOSEALL", ok=k_ok("", 0))
    for it, rq in zip(s.items, [[ACCT_REQ, W_OPEN(HW)], [W_READ(1, "w1")], [W_WRITE(1, "w1", "x")], [W_WRITE(1, "w2", "x", True)], [W_DEL(1, "w3")],
                                [W_DEL(1, "w3", True)], [W_LOCK(1, "w1", True)], [W_LOCK(1, "w1", False)], [W_CLEAR(1)], [W_READ(1, "w1")], [W_RLK(1, "w1")], [(1, b"")]]):
        it["req"] = rq
    r = hw_go("zznhon", s, (A,), cfg={"write_group": False})
    row("the program that made those calls ran to its end and no connection is left", r.began and r.ended and r.idle, h_why(r))
    judge(r, s)
    d = r.d[0]
    sess = d["sessions"]
    want_ref = [16, 17, 18, 19, 30, 30, 31, 34]
    row("...THE FAKE (the target) saw the requests, in order, with their bytes, and REFUSED the eight: 16, 17, 18, 19, 30, 30, 31 and 34 (the RECORDLOCKED, S.72b; and nothing else), and audited each as "
        "'api refused request=N route=sdfiles write=off user=alice'",
        a_wire(r, s) and len(sess) == 1 and sess[0].files_only and not sess[0].write_ok and sess[0].refused == want_ref
        and sess[0].audit == ["api refused request=%d route=sdfiles write=off user=alice" % n for n in want_ref],
        "first difference: %r refused %r audit %r" % (hw_first_diff(d, s.wire()), [x.refused for x in sess], [x.audit for x in sess]))
    row("...THE FILE ON THE FAKE IS AS IT WAS (the records are the evidence, not the replies): no record written, w3 still there, nothing cleared, no lock in the table",
        r.stores[0][HW] == dict(HWREC) and all(r.stores[0][n] == dict(rec) for n, rec, _p, _c in HWFILES if n != HW), repr(r.stores[0][HW]))
    row("...the audit trail on the client: the open, one write line, one delete line, one clear line (the refused attempts are audited like the good ones: the line is written BEFORE the request)",
        r.audits == s.audits(), repr(r.audits))

    s = Script()
    s.add("OPEN", "nfw", HW, ok=k_open_w(1), audit=OPEN_W_AUD)
    s.add("WRITE", 1, "w1", "x", label="CONTROL, the same target WITH sdfileswrite (write_group=True): WRITE is done", ok=k_ok("", 0), audit="write server=nfw file=hwork")
    s.add("LOCK", 1, "w2", "u", label="...a LOCK is granted", ok=k_ok("", 0))
    s.add("RLOCKED", 1, "w2", label="[S72b-N6c] ...RECORDLOCKED is SERVED (the group is the whole difference to the rows above): the lock just granted shows as 2 (this session's update lock), not 0 and not a refusal",
          ok=k_rlk(2))
    s.add("WRITEU", 1, "w2", "y", label="...WRITEU is done", ok=k_ok("", 0))
    s.add("DELETE", 1, "w3", label="...DELETE is done", ok=k_ok("", 0), audit="delete server=nfw file=hwork")
    s.add("CLEARFILE", 1, label="...CLEARFILE is done", ok=k_ok("", 0), audit="clear server=nfw file=hwork")
    s.add("CLOSEALL", ok=k_ok("", 0))
    r = hw_go("zznhon", s, (A,), cfg={"write_group": True})
    row("the control program ran to its end and no connection is left", r.began and r.ended and r.idle, h_why(r))
    judge(r, s)
    row("...nothing was refused, and the file on the fake is empty (every change was done, the clear last)",
        all(x.write_ok and x.refused == [] for x in r.d[0]["sessions"]) and r.stores[0][HW] == {}, repr(([x.refused for x in r.d[0]["sessions"]], r.stores[0][HW])))

    # the statements of an ordinary session, as kwrite drives them, against a target without the group
    say("\n  -- the statements (WRITE, DELETE, READU, CLEARFILE ...) on a write-mode file whose target does not allow changes: ON ERROR, the file unchanged, the session goes on --")
    lines = ["OPEN|1|zznw1", "READ|1|w1", "WRITE|1|w1|x", "READ|1|w1", "DELETE|1|w2", "READ|1|w2", "READU|1|w3", "CLEARFILE|1", "READ|1|w1", "CLOSE|1"]
    r = kw_drive("zznhon", lines, (A,), cfg={"write_group": False})
    say("    [note] the driver printed %r" % [x[:110] for x in r.kw])
    d = r.d[0]
    row("the statement driver ran to its end, nothing hung, no connection is left, and the fake (target) refused exactly the changes the statements sent (WRITE 16, DELETE 18, the lock of READU 30, CLEARFILE 31)",
        not r.hung and "KW begin" in r.kw and "KW end" in r.kw and r.idle and not r.crash and all(not x["errors"] for x in r.d)
        and d["sessions"] and d["sessions"][0].refused == [16, 18, 30, 31], kw_why(r) + " refused %r" % [x.refused for x in d["sessions"]])
    row("...the file on the fake is as it was: w1 and w2 still hold their records, and the READs after the refused WRITE and DELETE show them unchanged",
        r.stores[0][HW] == dict(HWREC) and kw_rec("READ", "w1", HWREC["w1"]) in r.kw and kw_rec("READ", "w2", HWREC["w2"]) in r.kw, repr((r.stores[0][HW], r.kw[-8:])))
    row("...and the refused statements took their ON ERROR branch with STATUS() 7000 (ER$NETWORK: the server refused, as for any server error that is not one of the passed-on statuses): "
        "WRITE, DELETE and READU (the lock) each printed 'error st=7000', none printed 'then'",
        "KW WRITE w1 error st=7000" in r.kw and "KW DELETE w2 error st=7000" in r.kw and "KW READU w3 error st=7000 len=0 rec=[]" in r.kw
        and not any(x.startswith(("KW WRITE w1 then", "KW DELETE w2 then", "KW READU w3 then", "KW CLEARFILE then")) for x in r.kw),
        repr([x for x in r.kw if x.startswith(("KW WRITE", "KW DELETE", "KW READU", "KW CLEARFILE"))]))

    # S.72 (20 Oct 26): FILELOCK and FILEUNLOCK are in the same change set (apifilesok 32 and 33): refused for a login without the group.  S.72b: request 34 (RECORDLOCKED) is in it too.
    s = Script()
    s.add("OPEN", "nfw", HW, ok=k_open_w(1), req=[ACCT_REQ, W_OPEN(HW)], audit=OPEN_W_AUD)
    s.add("RAW", NF_FILELOCK, 1, label="WITHOUT the group: FILELOCK is refused (S.72): rc 3, message 11500 naming the server and 'filelock', and the TEXT of message 11521 with the request number (32), rc<6> 0",
          ok=k_srverr("filelock", 0, text=msg(11521, 32)), req=[W_FLK(1)], audit="filelock server=nfw file=hwork")
    s.add("RAW", NF_FILEUNLOCK, 1, label="...FILEUNLOCK is refused too (request 33)", ok=k_srverr("fileunlock", 0, text=msg(11521, 33)), req=[W_FUL(1)])
    s.add("RLOCKED", 1, "w1", label="[S72b-N7] ...RECORDLOCKED is refused as well (request 34, S.72b; it was served, out 0): rc 3, message 11500 naming the server and 'recordlocked', the TEXT of message 11521 with "
          "the request number (34), rc<6> 0 - the request went out and the SERVER said no", ok=k_srverr("recordlocked", 0, text=msg(11521, 34)), req=[W_RLK(1, "w1")])
    s.add("CLOSEALL", ok=k_ok("", 0), req=[(1, b"")])
    r = hw_go("zznhon", s, (A,), cfg={"write_group": False})
    row("the file-lock program ran to its end and no connection is left", r.began and r.ended and r.idle, h_why(r))
    judge(r, s)
    sess = r.d[0]["sessions"]
    row("...THE FAKE (the target) saw the requests with their bytes and REFUSED exactly 32, 33 and 34 (no lock was taken), audited each as 'api refused request=N route=sdfiles write=off user=alice', and the "
        "client's audit trail has the open and the 'filelock' line (written before the request, as for a change; RECORDLOCKED adds none)",
        a_wire(r, s) and len(sess) == 1 and not sess[0].write_ok and sess[0].refused == [32, 33, 34] and r.audits == s.audits()
        and sess[0].audit == ["api refused request=%d route=sdfiles write=off user=alice" % n for n in (32, 33, 34)],
        "first difference: %r refused %r %r audit %r" % (hw_first_diff(r.d[0], s.wire()), [x.refused for x in sess], r.audits, [x.audit for x in sess]))
    r = kw_drive("zznhon", ["OPEN|1|zznw1", "FLOCK|1", "FUNLOCK|1", "CLOSE|1"], (A,), cfg={"write_group": False})
    row("the statements FILELOCK and FILEUNLOCK on a write-mode file whose target does not allow changes take ON ERROR with STATUS() 7000 (the server refused), and the fake refused exactly 32 and 33",
        not r.hung and "KW begin" in r.kw and "KW end" in r.kw and r.idle and not r.crash and all(not x["errors"] for x in r.d) and "KW FLOCK  error st=7000" in r.kw and "KW FUNLOCK  error st=7000" in r.kw
        and r.d[0]["sessions"] and r.d[0]["sessions"][0].refused == [32, 33], kw_why(r) + " refused %r" % [x.refused for x in r.d[0]["sessions"]])


# ---- main -------------------------------------------------------------------------------------------------------------------------------------

SECTIONS = (("login", login_section), ("args", args_section), ("pin", pin_section), ("stale", stale_section), ("keys", keys_section), ("shared", shared_section),
            ("down", down_section), ("close", close_section), ("notfound", notfound_section), ("files", files_section), ("account", account_section),
            ("locks", locks_section), ("lists", lists_section), ("wire", wire_section),
            ("handler", handler_section), ("readonly", readonly_section), ("refuse", refuse_section), ("lost", lost_section), ("timeout", timeout_section), ("oversize", oversize_section),
            ("hwrite", hwrite_section), ("kwrite", kwrite_section), ("wgroup", wgroup_section),
            ("kernel", kernel_section), ("mustlock", mustlock_section), ("gaps", gaps_section))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-netfile.py <dir> [--build] [--sections=a,b]   (parts: %s)" % ", ".join(n for n, _f in SECTIONS))
    g.BOX = os.path.abspath(args[0])
    g.SYS = os.path.join(g.BOX, "sys")
    g.SD = os.path.join(g.SYS, "bin", "sd")
    sections = next((set(a.split("=", 1)[1].split(",")) for a in sys.argv[1:] if a.startswith("--sections=")), None)
    say("sandbox-netfile: sandbox %s%s" % (g.BOX, "" if sections is None else "  (parts: %s)" % ",".join(sorted(sections))))
    say("sandbox-netfile: tree    %s" % os.path.dirname(HERE))
    if "--build" in sys.argv:
        if os.path.exists(g.BOX) and os.listdir(g.BOX):
            bail("%s is not empty" % g.BOX)
        r = subprocess.run([sys.executable, g.TOOL, g.BOX, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-netfile: built, bootstrap passed")
    elif not os.path.isfile(g.SD):
        bail("%s holds no built sandbox (use --build, or point it at one)" % g.BOX)
    subprocess.run([sys.executable, g.TOOL, g.BOX, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    say("\n--- preparation: a CPROC that is not the install build, the fixture account, the driver, the fake servers ---")
    g.prepare()
    g.EXTRA_FIXTURES[ACCT] = ("no", "no")
    path = g.build_account(ACCT)
    g.reg_write(ACCT, [path, "", g.GROUP, "", "", "", "no", "no", "", "yes", "yes", "yes", "", ""])        # ordinary: no sh, no os.execute; the edit gates on so it can compile
    f = g.flags(g.plain(ACCT, ["ZZKF"]))
    row("CONTROL: a plain session in %s is not an administrator (admin=0), so no row below passes merely because the session may do anything" % ACCT, f is not None and f[0] == "0", repr(f))
    if f is None or f[0] != "0":
        bail("the plain session is an administrator (or printed nothing): every row below would be meaningless")
    g.put(os.path.join(acct_path(ACCT), "bp", PROG), DRIVER)
    out = g.plain(ACCT, ["BASIC bp " + PROG])
    ok = g.has(out, r"^Compiled 1 program\(s\) with no errors")
    row("SETUP: the driver compiles in an ORDINARY session with no errors (it names obj->connect.keys: if the dotted public name does not compile, the class's name must change)", ok, repr(out[-8:]))
    if not ok:
        bail("the driver did not compile:\n" + "\n".join(out[-12:]))
    try:
        if not setup():
            sys.exit(2)
        for name, fn in SECTIONS:
            if (sections is None and name not in OPT_IN) or (sections is not None and name in sections):
                fn()
        say("\n--- the end: every connection of every fake has ended ---")
        for k in ("A", "B"):
            srv = S[k]
            with srv.lock:
                live, busy = len(srv.live), srv.busy
            row("fake %s: %d connections accepted, none being dealt with (%d), no socket left open (%d), every served session ended (%d of %d)"
                % (k, srv.conns, busy, live, sum(1 for s in srv.sessions if s.closed), len(srv.sessions)),
                quiet(srv) and all(s.closed for s in srv.sessions), "")
        row("the fakes never found a message of the class malformed over the whole run (apart from the one the EXECUTE control reached the dispatch with)",
            all(e == "request 21 is not built in netfake" for k in ("A", "B") for e in S[k].errors), repr([S[k].errors for k in ("A", "B")]))
    finally:
        teardown()
        for d in ("bp", "bp.out"):
            p = os.path.join(acct_path(ACCT), d, PROG)
            if os.path.exists(p):
                os.remove(p)
    say("")
    say("sandbox-netfile: %d passed, %d failed" % (passed, failed))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
