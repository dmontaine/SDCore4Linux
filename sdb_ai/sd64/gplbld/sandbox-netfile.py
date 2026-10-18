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
# refuse, lost, timeout - the handler gpl.bp/netfile, slice 3b; kernel - the NET_FILE type through real OPEN / READ / READV / FILEINFO / CLOSE
# statements and the refusal of everything else, slice 3c; gaps - OPT-IN ONLY, see below); no flag runs all of them except gaps.
#
# START-HISTORY:
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
    out = g.plain(ACCT, ["RUN bp " + PROG] + list(ops) + ["END"])
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
    r.out, r.d, r.el, r.idle = out, srv.delta(m), el, idle
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
    r = go(keys(carol, A) + ["OPEN|customers|1", "READ|1|c1", "RLOCKED|1|c1", "REV", "DISC"], A)
    row("a files-only user logs in through connect.keys (the account request 3 is allowed once), opens and reads a record, tests a lock and asks the revision",
        sane(r) and kline(1, "") in r.fx and rl("READ", "c1", 0, RECS["c1"]) in r.fx and "FX RLOCKED c1 n=0" in r.fx and r.ses and r.ses[0].files_only
        and r.ses[0].refused == [], why(r))
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
OPT_IN = ("gaps",)
H = {}                                                             # what the handler sections made
NH_RX = re.compile(r"^NH (\d+) (\S+) rc=(\S*) m=(\S*) st=(\S*) len=(\d+) out=\[(.*)\]$")
NA_RX = re.compile(r"^NA (\d+) (\d) \[(.*)\]$")

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
      via = @false
      if nm[1,1] = 'X' then
         via = @true
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
    """The handler's audit lines in a stretch of the trail, as   open server=nfa file=hcust   /   refused server=nfa reason=gate."""
    out = []
    for m in re.finditer(r"netfile (open|refused) server=(\S+) (?:file|reason)=([^\r\n]*?)\s*$", text or "", re.M):
        out.append("%s server=%s %s=%s" % (m.group(1), m.group(2), "file" if m.group(1) == "open" else "reason", m.group(3)))
    return out


def h_calls(lines):
    calls, by = [], {}
    for ln in lines:
        m = NH_RX.match(ln)
        if m:
            c = {"n": int(m.group(1)), "nm": m.group(2), "rc": m.group(3), "m": m.group(4), "st": m.group(5), "len": int(m.group(6)), "out": m.group(7), "args": ["", "", ""]}
            calls.append(c)
            by[c["n"]] = c
            continue
        m = NA_RX.match(ln)
        if m and int(m.group(1)) in by:
            by[int(m.group(1))]["args"][int(m.group(2)) - 1] = m.group(3)
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
    files_only=True (the SDNet login) and CFG; r.d is a list of what each saw, r.calls what the program got, r.audits what the audit trail gained."""
    c = {"files": True, "files_only": True}
    c.update(cfg or {})
    for f in fakes:
        f.configure(**c)
    marks = [f.mark() for f in fakes]
    a0 = audit_size()
    t0 = time.time()
    lines = script.lines + ["END"]
    out = g.adm(["RUN gpl.bp zznfh"] + lines, internal=True) if admin else g.plain(acct, ["ZZNFH"] + lines)
    el = time.time() - t0
    idle = True
    for f in fakes:
        f.settle(quiet=0.3)
        idle = quiet(f) and idle
    r = Run()
    r.d = [f.delta(m) for f, m in zip(fakes, marks)]
    for f in fakes:
        f.configure()
    r.out, r.el, r.idle = out, el, idle
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
    return "began=%s ended=%s calls=%d of %d idle=%s fake errors=%r\n      tail: %r" % (r.began, r.ended, len(r.calls), r.n, r.idle, [d["errors"] for d in r.d], r.out[-n:])


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

    # the definitions (name|host|port|account|pin|mode|accounts|date) and the stored logins
    today = datetime.date.today().isoformat()
    L = []
    cred = {}

    def define(name, port, pin, accounts, who, credpin=None, account="acct", host="127.0.0.1"):
        L.append("|".join([name, host, str(port), account, pin, "read", accounts, today]))
        if who is not None:
            cred[name] = h_cred_line(who, credpin or pin)
    define("nfa", A.port, pa, "zznhon,zznhoff", alA)
    define("nfb", B.port, pb, "zznhon", alB)
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
    with open(sdefs, "w", encoding="ascii") as f:
        f.write("\n".join(L) + "\n")
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
    s.add("RLOCKED", 1, "c1", label="RECORDLOCKED of a record nobody holds is 0", ok=k_ok("0", 1), req=[(34, FNO(1) + b"c1")])
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
    row("...THE REQUESTS, in order, with their bytes: ACCOUNT acct, OPEN hcust, the READs and the five READVs (a READV is a whole READ on the wire), RECORDLOCKED, SELECT then READLIST on one list number "
        "(0 to 10), FILEINFO sent nothing, OPEN 'dict hcust' in lower case, CLOSE with the file number, QUIT - and nothing for the empty id or the closed handle",
        a_wire(r, s), "first difference: %r" % (next(((a, b) for a, b in zip(h_wire(d), s.wire()) if a != b), (len(h_wire(d)), len(s.wire()))),))
    row("...the audit trail gained one 'netfile open server=<name> file=<file>' line for each OPEN, in order (%s), and nothing in it is a key, a hash, a salt or a password" % ", ".join(s.audits()),
        r.audits == s.audits() and secret_free(r.audit), repr(r.audits))

    # a record lock held by another user is reported with the class's codes; the handler takes none of its own
    A.store.hold(HFILE, "c2", 7, "update")
    A.store.hold(HFILE, "c3", 8, "shared")
    A.store.hold_file(HEMPTY, 9)
    try:
        s = Script()
        s.add("OPEN", "nfa", HFILE, ok=k_ok("1", 1), req=[(3, b"acct"), (4, b"hcust")], audit="open server=nfa file=hcust")
        s.add("OPEN", "nfa", HEMPTY, ok=k_ok("2", 1), req=[(4, b"hempty")], audit="open server=nfa file=hempty")
        s.add("RLOCKED", 1, "c2", label="RECORDLOCKED of a record another user holds an UPDATE lock on is -2", ok=k_ok("-2", 2), req=[(34, FNO(1) + b"c2")])
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
    say("\n--- $netfile is READ ONLY in this stage: write, delete, clear.file and lock are refused with message 11501 and NOTHING is sent ---")
    if not h_prep():
        return
    A = S["A"]
    before = A.store.records(HFILE)
    c1 = RECS["c1"]
    s = Script()
    s.add("OPEN", "nfa", HFILE, ok=k_ok("1", 1), req=[(3, b"acct"), (4, b"hcust")], audit="open server=nfa file=hcust")
    s.add("READ", 1, "c1", ok=k_rec(c1), req=[(6, FNO(1) + b"c1")])
    s.add("WRITE", 1, "c1", "changed", label="WRITE is refused: 11501 naming the server and the operation (write)", ok=k_err(11501, "nfa", "write"))
    s.add("DELETE", 1, "c1", label="DELETE is refused: 11501 (delete)", ok=k_err(11501, "nfa", "delete"))
    s.add("CLEARFILE", 1, label="CLEARFILE is refused: 11501 (clear.file)", ok=k_err(11501, "nfa", "clear.file"))
    s.add("LOCK", 1, "c1", label="LOCK is refused: 11501 (lock)", ok=k_err(11501, "nfa", "lock"))
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
    s.add("RAW", 14, label="an operation number the kernel might mistake (14) is 11490", ok=k_err(11490, 14))
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
    s = Script()
    s.add("OPEN", "nfa", HFILE, ok=k_ok("1", 1))
    s.add("READ", 1, "c1", label="GAP: a READ the server answers with an ON ERROR is rc 3 with 11500 naming the server, the operation and the text; the class ABORTS the calling program instead and "
          "the handler cannot catch it", ok=k_err(11500, "nfa", "read", "boom"))
    s.add("CLOSEALL", ok=k_ok("", 0))
    r = h_go("zznhon", s, (A,), cfg={"fail": {6: (netfake.SV_ON_ERROR, "boom")}})
    row("GAP: the program that made that READ reached its end", r.began and r.ended, h_why(r))
    judge(r, s)

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
KALLOWED = {47, 48, 3, 4, 5, 6, 1}                  # the requests a read only session may send: login, account, open, close, read, quit
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
    L += kn_case("CLOSE", "close {f}", ["crt 'KR CLOSE ':slot"])
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
   crt 'KR kj SURVIVED ':locks
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
# is nfa, the server of zznet1.  7000 is ER_NETWORK, 3035 ER_PERM: the statements that take the S.64 edit-gate convention (RECORDLOCKU / L, SELECT,
# SELECTV) give 3035, the others the net_refuse() status.  Every statement uses the open file variable f and the record c1.


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
    km("select", "select f to 5", ["select f to 5 on error null", "st = status()", "readnext x from 5 then crt 'KR select readnext THEN' else crt 'KR select readnext ELSE'"],
       "select", 3035),
    km("selectv", "selectv f to lst", "selectv f to lst on error null", "selectv", 3035),
    km("release", "release f, 'c1'", None, "release", None),
    km("releasef", "release f", None, "release", None),
    km("filelock", "filelock f", None, "filelock", None),
    km("fileunlock", "fileunlock f", None, "fileunlock", None),
    km("recordlocked", "x = recordlocked(f, 'c1')", None, "recordlocked", None),
    km("selectindex", "selectindex 'CITY' from f to 5", None, "selectindex", None),
    km("selectindexv", "selectindex 'CITY', 'Paris' from f to 5", None, "selectindex", None),
    km("selectright", "selectright 'CITY' from f to 5", None, "selectright/selectleft", None),
    km("selectleft", "selectleft 'CITY' from f to 5", None, "selectright/selectleft", None),
    km("setleft", "setleft 'CITY' from f", None, "setleft", None),
    km("setright", "setright 'CITY' from f", None, "setright", None),
    km("indices", "x = indices(f)", None, "indices", None),
    km("indices2", "x = indices(f, 'CITY')", None, "indices", None),
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
KFI_KEYS = (3, 5, 1013, 1015, 1019, 1021, 1039, 1100)
KM += [km("fikey%d" % k, "x = fileinfo(f, %d)" % k, None, str(k), None, num=11502) for k in KFI_KEYS]

# the verbs on the VOC name: (the command, its extra lines, a message number the verb is known to refuse with or None)
KVERBS = [("COUNT zznet1", [], None), ("LIST zznet1", [], None), ("SELECT zznet1", [], None), ("SORT zznet1", [], None),
          ("LIST.ITEM zznet1 c1", [], None), ("CT zznet1 c1", [], None), ("CONFIGURE.FILE zznet1 MINIMUM.MODULUS 7", [], None), ("ANALYSE.FILE zznet1", [], None),
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
    the audit lines the session added (r.audits), whether the session hung (r.hung) and whether every connection ended (r.idle)."""
    c = {"files": True, "files_only": True}
    c.update(cfg or {})
    for f in fakes:
        f.configure(**c)
    marks = [f.mark() for f in fakes]
    a0 = audit_size()
    t0 = time.time()
    hung = False
    try:
        out = g.plain(acct, list(cmds))
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
    kn_after(A)


def kn_runtime(A, B):
    say("\n  -- the statements that are supported --")
    c1, c2, c3, m1, big = (RECS[k] for k in ("c1", "c2", "c3", "m1", "big"))
    fields = c1.split(FMC)
    fkeys = (0, 1, 2, 1001, 1009, 1022, 1030, 1032, 1038)
    lines = ["OPEN|1|zznet1"] + ["READ|1|" + k for k in ("c1", "c2", "c3", "m1", "big", "nosuch")]
    lines += ["READV|1|c1|2", "READV|1|c1|1", "READV|1|c1|9", "READV|1|c1|0", "READV|1|nosuch|1", "MATREAD|1|c2", "MATREAD|1|nosuch"]
    lines += ["FI|1|%d" % k for k in fkeys]
    lines += ["OPEN|2|zznetempty", "READ|2|x", "OPEN|3|zznet1", "READ|3|c3", "CLOSE|1", "READ|3|c2", "READ|2|x", "CLOSE|2", "CLOSE|3"]
    want = ["KR OPEN zznet1 then st=0", kn_read_line("c1", c1), kn_read_line("c2", c2), kn_read_line("c3", c3), kn_read_line("m1", m1), kn_read_line("big", big),
            kn_read_line("nosuch", "", "else", 3006),
            kn_readv_line("c1", 2, fields[1]), kn_readv_line("c1", 1, fields[0]), kn_readv_line("c1", 9, ""), kn_readv_line("c1", 0, "c1"),
            kn_readv_line("nosuch", 1, "", "else", 3006),
            "KR MATREAD c2 then st=0 [Jones][50][]", "KR MATREAD nosuch else st=3006 [][][]"]
    want += ["KR FI 0 [1]", "KR FI 1 [zznet1]", "KR FI 2 []", "KR FI 1001 [1]", "KR FI 1009 [-1]", "KR FI 1022 [1]", "KR FI 1030 [0]", "KR FI 1032 [1]", "KR FI 1038 [0]"]
    want += ["KR OPEN zznetempty then st=0", kn_read_line("x", "", "else", 3006), "KR OPEN zznet1 then st=0", kn_read_line("c3", c3),
             "KR CLOSE 1", kn_read_line("c2", c2), kn_read_line("x", "", "else", 3006), "KR CLOSE 2", "KR CLOSE 3"]
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
    row("OPEN 'DICT', 'zznet1' (the dictionary of a remote file is not supported in this slice) takes ELSE with STATUS() 3009, and nothing is dialled for it",
        "KR ODICT zznet1 else st=3009" in r.kr, repr([x for x in r.kr if x.startswith("KR ODICT")]))
    da, db = r.d
    expect_a = [[47, 48, 3, 4], [47, 48, 3, 4, 4, 6, 6]]
    row("...WHAT WAS DIALLED: server A saw two connections - the first ACCOUNT and OPEN nosuchfile (then the handler's Quit), the second ACCOUNT, OPEN, OPEN, READ, READ and nothing else (so no pointer of "
        "the refused kind and none of the nine bad ones, nor the DICT open, made a request; a Quit at the end of a connection is not compared)", kn_conns(da) == expect_a, repr(by_conn(da)))
    row("...server B (the pin mismatch) saw one connection and a completed handshake, ZERO request packets and ZERO application bytes: nothing was sent to a server whose key is not the pinned one",
        db["conns"] == 1 and db["handshakes"] == 1 and db["types"] == [] and db["app_bytes"] == 0, repr({k: db[k] for k in ("conns", "handshakes", "types", "app_bytes")}))
    want_audit = ["open server=nfa file=nosuchfile", "refused server=nfnocred reason=credential", "refused server=nfcpin reason=credential", "open server=nfpin file=hcust",
                  "refused server=nfadm reason=list", "open server=nfa file=hcust", "open server=nfa file=hcust"]
    row("...the audit trail has the handler's line for each of the seven pointers that reached it, in order, and NONE for the nine bad ones or the DICT open (the VOC step refused them before any "
        "gate or handler); nothing secret", r.audits == want_audit and secret_free(r.audit), repr(r.audits))
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
    row("GETLOCKS(f, '') on a NET file from an internal program stops with 11501 (getlocks) - without the refusal file_id -1 would mean ALL FILES and list every lock of every user",
        not r.hung and kn_abort(seg) == msg(11501, "nfa", "getlocks") and not any("SURVIVED" in x for x in seg), repr(seg))

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
        if tag == "select":
            good = good and "KR select readnext ELSE" in seg
            extra = "; the default select list is untouched (READNEXT takes ELSE)"
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


def kn_after(A):
    say("\n  -- after all of it --")
    before = kn_snapshot(A)
    r = kn_drive("zznhon", ["OPEN|1|zznet1", "READ|1|c1", "CLOSE|1"], (A,))
    row("THE POINTER STILL WORKS: the VOC record zznet1 is intact after every verb and the refusals (DELETE.FILE and CLEAR.FILE did not remove or empty anything), the file still opens and reads",
        kn_sane(r) and kn_read_line("c1", RECS["c1"]) in r.kr, kn_why(r))
    row("...and the records on the fake are what they were when the section began", kn_snapshot(A) == before and A.store.records(HFILE).get("c1") == RECS["c1"], "")
    row("NO SESSION OF THE KERNEL SECTION ENDED IN A CRASH: not one printed a double free, a corruption, a fatal signal or an abort (a session that opened a remote file once died at exit with a "
        "double free, after every row had its answer; the class objects the handler keeps in common ran their destroy code on a freed e-stack)", not KN.get("crashes"), repr(KN.get("crashes")))


# ---- main -------------------------------------------------------------------------------------------------------------------------------------

SECTIONS = (("login", login_section), ("args", args_section), ("pin", pin_section), ("stale", stale_section), ("keys", keys_section), ("shared", shared_section),
            ("down", down_section), ("close", close_section), ("notfound", notfound_section), ("files", files_section), ("account", account_section),
            ("locks", locks_section), ("lists", lists_section), ("wire", wire_section),
            ("handler", handler_section), ("readonly", readonly_section), ("refuse", refuse_section), ("lost", lost_section), ("timeout", timeout_section),
            ("kernel", kernel_section), ("gaps", gaps_section))


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
