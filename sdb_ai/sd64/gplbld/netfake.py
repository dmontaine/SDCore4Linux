#!/usr/bin/env python3
"""netfake.py - a FAKE SD API SERVER for the SDNet login rows (S.65 slice 2b).  Shared by sandbox-net.py.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/netfake.py --selftest

No sd, no sudo.  The self-test needs the openssl command line (it makes a throw-away certificate) and the loopback interface.

17 Oct 26 dm  New.  S.65 slice 2b.  ***NOT YET RUN AGAINST SD*** - the self-test runs it against a Python client built from RFC 7677's
              own vectors; whether SD's set.netlogin talks to it is the first run of sandbox-net.py.

WHAT IT IS.  A TLS 1.3 server on 127.0.0.1 (the ssl module, a certificate and key the caller made, no client certificate) that does what
the other end of a set.netlogin does, byte for byte as gpl.bp/sdclient and gpl.bp/apisrvr speak it:

  1. after the TLS handshake it sends ONE Ack byte, char(6);
  2. a request packet is   4 bytes length (LE, the data and these 6 header bytes)  +  2 bytes type (LE)  +  data;
  3. a reply packet is     4 bytes length (LE, the data and these 10 header bytes)  +  2 bytes error (LE)  +  4 bytes status (LE)  +  data;
  4. type 47 is SCRAM client-first  "p=tls-exporter,,n=<user>,r=<client nonce>"       -> reply  "r=<nonce>,s=<salt b64>,i=<iterations>"
     type 48 is SCRAM client-final  "c=<binding>,r=<nonce>,p=<ClientProof b64>"      -> reply  "v=<ServerSignature b64>"
     (RFC 5802 / 7677; the error field is 0 for success, 1 with the error text as data, 3 with no data = "text to be fetched").

THE SERVER SIDE OF SCRAM-SHA-256 is computed here with hashlib and hmac and nothing else: SaltedPassword = PBKDF2-HMAC-SHA-256(password,
salt, i); ClientKey = HMAC(SaltedPassword, "Client Key"); ServerKey = HMAC(SaltedPassword, "Server Key"); StoredKey = SHA-256(ClientKey).
It recovers the candidate ClientKey from the proof (proof XOR HMAC(StoredKey, AuthMessage)), checks its SHA-256 against StoredKey, and
answers v = HMAC(ServerKey, AuthMessage).  The self-test holds those functions to RFC 7677's section 3 vectors.

***THE LIMIT, STATED ONCE: THE CHANNEL BINDING IS NOT VERIFIED.***  The client's c= is base64("p=tls-exporter,," + the TLS exporter value for
its session).  Python's ssl module has no TLS exporter API (no export_keying_material), so this server cannot compute what the exporter
value should be.  It takes the c= the client sends, checks only its SHAPE (base64, the GS2 header "p=tls-exporter,," first, at least one
byte after it) and uses it verbatim in the AuthMessage, as the RFC does.  The binding itself - that a login relayed by a man in the middle
fails - is covered only by witness-release-run.sh on an install, where the real apisrvr recomputes it.

WHAT IT RECORDS (so that a row can say what the client DID, not only what it printed):
  conns        connections accepted                 handshakes   TLS handshakes completed
  packets      every request packet received: (connection number, type, data)
  app_bytes    decrypted application bytes received (0 for a client that shakes hands and goes away)
  exchanges    for each client-final: the messages, the binding, the proof, and whether it verified
  scram_ok / scram_bad   proofs that verified / that did not;   errors   things this server found wrong with the CLIENT's messages
It is a daemon thread with a lifetime limit, handles one connection at a time, and puts a 10 second limit on every connection.
"""

import base64
import hashlib
import hmac
import os
import socket
import ssl
import struct
import subprocess
import sys
import tempfile
import threading
import time

ACK = b"\x06"
PKT_FIRST, PKT_FINAL = 47, 48
SV_OK, SV_ON_ERROR, SV_ERROR = 0, 1, 3
GS2 = b"p=tls-exporter,,"
BASE64_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")


def b64(raw):
    return base64.b64encode(raw).decode("ascii")


def derive(password, salt_b64, iterations):
    """RFC 5802 / 7677, from hashlib alone.  Returns raw bytes: salted, client_key, stored_key, server_key (and the b64 text of the three keys)."""
    salted = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), base64.b64decode(salt_b64), int(iterations), 32)
    ck = hmac.new(salted, b"Client Key", hashlib.sha256).digest()
    sk = hmac.new(salted, b"Server Key", hashlib.sha256).digest()
    stored = hashlib.sha256(ck).digest()
    return {"salted": salted, "client_key": ck, "stored_key": stored, "server_key": sk,
            "client_key_b64": b64(ck), "server_key_b64": b64(sk), "stored_key_b64": b64(stored)}


def client_proof(client_key, stored_key, authmsg):
    """ClientProof = ClientKey XOR HMAC(StoredKey, AuthMessage)."""
    sig = hmac.new(stored_key, authmsg.encode("latin-1"), hashlib.sha256).digest()
    return bytes(a ^ b for a, b in zip(client_key, sig))


def server_signature(server_key, authmsg):
    return hmac.new(server_key, authmsg.encode("latin-1"), hashlib.sha256).digest()


class FakeServer(threading.Thread):
    """See the module text.  Users: add_user().  Behaviour per connection: configure() - every call starts from the defaults, so a row
    names only what it changes."""

    DEFAULTS = {
        "ack": True,              # send the Ack byte after the handshake
        "close_after": None,      # 'handshake' (before the Ack) | 'ack' | 'first' (after reading client-first) | 'final' | None
        "nonce": "extend",        # 'extend' | 'wrong' (does not start with the client's) | 'same' (the client's, nothing added)
        "offer_iter": None,       # iteration count offered (and used) instead of the user's
        "iter_text": None,        # i= text instead of a number (the derivation still uses the user's count)
        "salt_text": None,        # s= text instead of the user's salt
        "first_raw": None,        # the whole server-first message, instead of r=,s=,i=
        "first_error": None,      # (error field, text): answer client-first with an error
        "final_error": None,      # (error field, text): answer client-final with an error without looking at the proof
        "bad_v": False,           # a wrong ServerSignature
        "no_v": False,            # an answer that is not v=
    }

    def __init__(self, cert, key, life=1800):
        threading.Thread.__init__(self, daemon=True)
        self.ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.ctx.minimum_version = ssl.TLSVersion.TLSv1_3
        self.ctx.maximum_version = ssl.TLSVersion.TLSv1_3
        self.ctx.load_cert_chain(cert, key)
        self.users = {}
        self.cfg = dict(self.DEFAULTS)
        self.lock = threading.Lock()
        self.conns = 0
        self.handshakes = 0
        self.app_bytes = 0
        self.packets = []
        self.exchanges = []
        self.scram_ok = 0
        self.scram_bad = 0
        self.errors = []
        self.busy = False
        self.ended = threading.Event()
        self.deadline = time.time() + life
        self.lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.lsock.bind(("127.0.0.1", 0))
        self.lsock.listen(8)
        self.lsock.settimeout(0.1)
        self.port = self.lsock.getsockname()[1]
        self.start()

    # ---- configuration and records --------------------------------------------------------------------------------------------
    def add_user(self, name, password, salt=None, iterations=4096):
        """A user the server knows.  Returns the salt as base64 (the one in s=)."""
        salt = salt if salt is not None else os.urandom(16)
        with self.lock:
            self.users[name] = {"password": password, "salt": salt, "iterations": int(iterations)}
        return b64(salt)

    def configure(self, **kw):
        bad = [k for k in kw if k not in self.DEFAULTS]
        if bad:
            raise KeyError("netfake: unknown setting %r" % bad)
        with self.lock:
            self.cfg = dict(self.DEFAULTS)
            self.cfg.update(kw)

    def mark(self):
        with self.lock:
            return (self.conns, self.handshakes, len(self.packets), self.app_bytes, self.scram_ok, self.scram_bad, len(self.exchanges), len(self.errors))

    def delta(self, m):
        """What happened since MARK: connection and handshake counts, the TYPES of the packets received, the application bytes, proofs that
        verified and that did not, the exchanges, and what this server found wrong in the client's messages."""
        with self.lock:
            return {"conns": self.conns - m[0], "handshakes": self.handshakes - m[1], "types": [p[1] for p in self.packets[m[2]:]],
                    "packets": list(self.packets[m[2]:]), "app_bytes": self.app_bytes - m[3], "ok": self.scram_ok - m[4],
                    "bad": self.scram_bad - m[5], "exchanges": list(self.exchanges[m[6]:]), "errors": list(self.errors[m[7]:])}

    def settle(self, quiet=0.7, limit=8.0):
        """Wait until a connection the client has just made has been accepted and dealt with (a 'no connection' row waits the same time)."""
        time.sleep(quiet)
        t0 = time.time()
        while self.busy and time.time() - t0 < limit:
            time.sleep(0.05)

    def shutdown(self):
        self.ended.set()
        self.join(timeout=5)

    # ---- the server ------------------------------------------------------------------------------------------------------------
    def run(self):
        while not self.ended.is_set() and time.time() < self.deadline:
            try:
                conn, _addr = self.lsock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            self.busy = True
            with self.lock:
                self.conns += 1
                n = self.conns
                cfg = dict(self.cfg)
            try:
                conn.settimeout(10)
                self.handle(conn, n, cfg)
            except Exception:           # a client that goes away in the middle of an exchange is not this server's concern
                pass
            finally:
                try:
                    conn.close()
                except OSError:
                    pass
                self.busy = False
        try:
            self.lsock.close()
        except OSError:
            pass

    def note(self, text):
        with self.lock:
            self.errors.append(text)

    def read_exact(self, tls, n):
        buf = b""
        while len(buf) < n:
            chunk = tls.recv(n - len(buf))
            if not chunk:
                return None
            with self.lock:
                self.app_bytes += len(chunk)
            buf += chunk
        return buf

    def read_packet(self, tls, n):
        """(type, data) of the next request packet, or None when the client closed or the time ran out."""
        try:
            head = self.read_exact(tls, 6)
            if head is None:
                return None
            length, ptype = struct.unpack("<IH", head)
            if length < 6 or length > 65536:
                self.note("a request packet of length %d" % length)
                return None
            data = self.read_exact(tls, length - 6) if length > 6 else b""
            if data is None:
                return None
        except (OSError, ssl.SSLError):
            return None
        with self.lock:
            self.packets.append((n, ptype, data))
        return ptype, data

    @staticmethod
    def reply(tls, data, err=SV_OK):
        data = data.encode("latin-1") if isinstance(data, str) else data
        tls.sendall(struct.pack("<IHI", 10 + len(data), err, 0) + data)

    def handle(self, conn, n, cfg):
        tls = self.ctx.wrap_socket(conn, server_side=True)
        with self.lock:
            self.handshakes += 1
        tls.settimeout(5)
        try:
            if cfg["close_after"] == "handshake":
                return
            if cfg["ack"]:
                tls.sendall(ACK)
            if cfg["close_after"] == "ack":
                return
            pk = self.read_packet(tls, n)
            if pk is None:
                return
            ptype, data = pk
            if ptype != PKT_FIRST:
                self.note("the first packet is type %d, not 47" % ptype)
                self.reply(tls, "unexpected packet", SV_ON_ERROR)
                return
            if cfg["close_after"] == "first":
                return
            if cfg["first_error"] is not None:
                self.reply(tls, cfg["first_error"][1], cfg["first_error"][0])
                return
            text = data.decode("latin-1")
            if not text.startswith(GS2.decode()):
                self.note("client-first does not start with the GS2 header: %r" % text[:30])
                self.reply(tls, "bad message", SV_ON_ERROR)
                return
            cfirst_bare = text[len(GS2):]
            parts = cfirst_bare.split(",")
            if len(parts) != 2 or not parts[0].startswith("n=") or not parts[1].startswith("r=") or len(parts[1]) < 3:
                self.note("client-first-bare is not n=,r=: %r" % cfirst_bare[:60])
                self.reply(tls, "bad message", SV_ON_ERROR)
                return
            user, cnonce = parts[0][2:], parts[1][2:]
            with self.lock:
                rec = self.users.get(user)
            if rec is None:
                self.reply(tls, "Authentication failed", SV_ON_ERROR)
                return
            iters = cfg["offer_iter"] if cfg["offer_iter"] is not None else rec["iterations"]
            snonce = b64(os.urandom(18))
            nonce = {"extend": cnonce + snonce, "wrong": b64(os.urandom(18)) + snonce, "same": cnonce}[cfg["nonce"]]
            salt_text = cfg["salt_text"] if cfg["salt_text"] is not None else b64(rec["salt"])
            iter_text = cfg["iter_text"] if cfg["iter_text"] is not None else str(iters)
            sfirst = cfg["first_raw"] if cfg["first_raw"] is not None else "r=%s,s=%s,i=%s" % (nonce, salt_text, iter_text)
            self.reply(tls, sfirst)

            pk = self.read_packet(tls, n)
            if pk is None:
                return
            ptype, data = pk
            if ptype != PKT_FINAL:
                self.note("the second packet is type %d, not 48" % ptype)
                self.reply(tls, "unexpected packet", SV_ON_ERROR)
                return
            if cfg["close_after"] == "final":
                return
            text = data.decode("latin-1")
            fparts = text.split(",")
            ex = {"user": user, "cfirst_bare": cfirst_bare, "sfirst": sfirst, "nonce": nonce, "cnonce": cnonce, "snonce": snonce,
                  "cbind": None, "proof": None, "cfinal_bare": None, "authmsg": None, "verified": None, "iterations": iters, "final_text": text}
            with self.lock:
                self.exchanges.append(ex)
            if cfg["final_error"] is not None:
                self.reply(tls, cfg["final_error"][1], cfg["final_error"][0])
                return
            if len(fparts) != 3 or not fparts[0].startswith("c=") or fparts[1] != "r=" + nonce or not fparts[2].startswith("p="):
                self.note("client-final is not c=,r=<nonce>,p=: %r" % text[:80])
                self.reply(tls, "bad message", SV_ON_ERROR)
                return
            # the shape of the binding only - see the module text: this server cannot compute the exporter value
            try:
                cbind = base64.b64decode(fparts[0][2:], validate=True)
            except Exception:
                cbind = b""
            ex["cbind"] = cbind
            if not cbind.startswith(GS2) or len(cbind) <= len(GS2):
                self.note("c= is not base64('p=tls-exporter,,' + a binding): %r" % fparts[0][:60])
                self.reply(tls, "bad message", SV_ON_ERROR)
                return
            try:
                proof = base64.b64decode(fparts[2][2:], validate=True)
            except Exception:
                proof = b""
            ex["proof"] = proof
            ex["cfinal_bare"] = fparts[0] + "," + fparts[1]
            authmsg = cfirst_bare + "," + sfirst + "," + ex["cfinal_bare"]
            ex["authmsg"] = authmsg
            keys = derive(rec["password"], b64(rec["salt"]), iters)
            sig = hmac.new(keys["stored_key"], authmsg.encode("latin-1"), hashlib.sha256).digest()
            if len(proof) != 32:
                ok = False
            else:
                ck = bytes(a ^ b for a, b in zip(proof, sig))
                ok = hmac.compare_digest(hashlib.sha256(ck).digest(), keys["stored_key"])
            ex["verified"] = ok
            with self.lock:
                if ok:
                    self.scram_ok += 1
                else:
                    self.scram_bad += 1
            if not ok:
                self.reply(tls, "Authentication failed", SV_ON_ERROR)
                return
            v = server_signature(keys["server_key"], authmsg)
            if cfg["bad_v"]:
                v = bytes([v[0] ^ 1]) + v[1:]
            self.reply(tls, ("x=" if cfg["no_v"] else "v=") + b64(v))
            # anything more the client sends is recorded (a client that has what it came for closes at once)
            while self.read_packet(tls, n) is not None:
                pass
        finally:
            try:
                tls.close()
            except (OSError, ssl.SSLError):
                pass


# ---- the self-test ------------------------------------------------------------------------------------------------------------------

def _openssl(args, data=None):
    p = subprocess.run(["openssl"] + args, input=data, capture_output=True, timeout=60)
    if p.returncode != 0:
        raise RuntimeError("openssl %s failed: %s" % (" ".join(args[:3]), p.stderr.decode(errors="replace")[-300:]))
    return p.stdout


def _probe(port, user, password, tamper_v=False):
    """A minimal SCRAM client, for the self-test only: written from RFC 7677 and the packet text above, not from SD's code.  Returns
    (outcome, detail): 'ok', or 'error' with the server's text, 'closed', 'bad-v'."""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    raw = socket.create_connection(("127.0.0.1", port), timeout=10)
    tls = ctx.wrap_socket(raw, server_hostname="127.0.0.1")
    tls.settimeout(10)

    def rd(n):
        buf = b""
        while len(buf) < n:
            c = tls.recv(n - len(buf))
            if not c:
                raise EOFError
            buf += c
        return buf

    def send(ptype, data):
        d = data.encode("latin-1")
        tls.sendall(struct.pack("<IH", len(d) + 6, ptype) + d)

    def recv():
        length, err, _st = struct.unpack("<IHI", rd(10))
        return err, rd(length - 10).decode("latin-1") if length > 10 else ""
    try:
        if rd(1) != ACK:
            return "closed", "no ack"
        cnonce = b64(os.urandom(18))
        bare = "n=%s,r=%s" % (user, cnonce)
        send(PKT_FIRST, "p=tls-exporter,," + bare)
        err, sfirst = recv()
        if err != SV_OK:
            return "error", sfirst
        attrs = dict(a.split("=", 1) for a in sfirst.split(","))
        keys = derive(password, attrs["s"], attrs["i"])
        cfinal_bare = "c=%s,r=%s" % (b64(GS2 + os.urandom(32)), attrs["r"])
        authmsg = bare + "," + sfirst + "," + cfinal_bare
        proof = client_proof(keys["client_key"], keys["stored_key"], authmsg)
        send(PKT_FINAL, cfinal_bare + ",p=" + b64(proof))
        err, final = recv()
        if err != SV_OK:
            return "error", final
        if final != "v=" + b64(server_signature(keys["server_key"], authmsg)):
            return "bad-v", final
        return "ok", final
    except (EOFError, OSError):         # a close without close_notify arrives as an SSLError, which is an OSError
        return "closed", "the server closed"
    finally:
        try:
            tls.close()
        except OSError:
            pass


def selftest():
    passed = failed = 0

    def row(name, ok, detail=""):
        nonlocal passed, failed
        if ok:
            passed += 1
            print("  [PASS] " + name)
        else:
            failed += 1
            print("  [FAIL] " + name + ("   <- " + detail if detail else ""))
    # RFC 7677 section 3
    salt, it = "W22ZaJ0SNY7soEsUEjb6gQ==", 4096
    keys = derive("pencil", salt, it)
    cfirst_bare = "n=user,r=rOprNGfwEbeRWgbNEkqO"
    sfirst = "r=rOprNGfwEbeRWgbNEkqO%hvYDpWUa2RaTCAfuxFIlj)hNlF$k0,s=W22ZaJ0SNY7soEsUEjb6gQ==,i=4096"
    cfinal_bare = "c=biws,r=rOprNGfwEbeRWgbNEkqO%hvYDpWUa2RaTCAfuxFIlj)hNlF$k0"
    auth = cfirst_bare + "," + sfirst + "," + cfinal_bare
    row("RFC 7677 vector: the ClientProof", b64(client_proof(keys["client_key"], keys["stored_key"], auth)) == "dHzbZapWIk4jUhN+Ute9ytag9zjfMHgsqmmiz7AndVQ=",
        b64(client_proof(keys["client_key"], keys["stored_key"], auth)))
    row("RFC 7677 vector: the ServerSignature", b64(server_signature(keys["server_key"], auth)) == "6rriTRBi23WpRR/wtup+mMhUZUn/dB5nLTJRsjl95G4=",
        b64(server_signature(keys["server_key"], auth)))
    if not any(os.access(os.path.join(p, "openssl"), os.X_OK) for p in os.environ.get("PATH", "").split(os.pathsep)):
        print("netfake: CANNOT RUN the server rows - the openssl command line is not installed")
        return 2
    work = tempfile.mkdtemp(prefix="netfake-")
    srv = None
    try:
        k, c = os.path.join(work, "k.pem"), os.path.join(work, "c.pem")
        _openssl(["genpkey", "-algorithm", "EC", "-pkeyopt", "ec_paramgen_curve:P-256", "-out", k])
        _openssl(["req", "-x509", "-new", "-key", k, "-out", c, "-days", "2", "-subj", "/CN=netfake", "-set_serial", "1"])
        srv = FakeServer(c, k, life=120)
        srv.add_user("alice", "pw-one", iterations=4096)

        def run(label, want, cfg=None, user="alice", pw="pw-one", types=None, ok=None, bad=None):
            srv.configure(**(cfg or {}))
            m = srv.mark()
            res = _probe(srv.port, user, pw)
            srv.settle(quiet=0.3)
            d = srv.delta(m)
            good = res[0] == want and d["conns"] == 1 and d["errors"] == []
            if types is not None:
                good = good and d["types"] == types
            if ok is not None:
                good = good and d["ok"] == ok and d["bad"] == bad
            row(label, good, "client saw %r, server saw %r" % (res, {k: d[k] for k in ("conns", "types", "ok", "bad", "errors")}))
        run("a correct password: the exchange completes, two packets, 47 then 48, the proof verified, the client verified v=", "ok", types=[47, 48], ok=1, bad=0)
        run("a wrong password: the server answers an error, the proof did not verify", "error", pw="wrong", types=[47, 48], ok=0, bad=1)
        run("an unknown user: an error after the first packet only", "error", user="mallory", types=[47], ok=0, bad=0)
        run("a wrong v=: the client sees the signature differ", "bad-v", cfg={"bad_v": True}, types=[47, 48], ok=1, bad=0)
        run("no Ack: the client sees the connection closed", "closed", cfg={"close_after": "handshake"}, types=[])
        run("closed after client-first", "closed", cfg={"close_after": "first"}, types=[47])
        run("first_error: the error field and text reach the client", "error", cfg={"first_error": (SV_ON_ERROR, "no thanks")}, types=[47])
        run("an iteration count of 5000 is used by both ends", "ok", cfg={"offer_iter": 5000}, types=[47, 48], ok=1, bad=0)
        ex = srv.exchanges[-1]
        row("the exchange record holds the binding shape the client sent and an independent proof check agrees",
            ex["cbind"].startswith(GS2) and ex["verified"] is True and ex["iterations"] == 5000 and len(ex["proof"]) == 32, repr(ex)[:200])
    finally:
        if srv is not None:
            srv.shutdown()
        for f in os.listdir(work):
            os.remove(os.path.join(work, f))
        os.rmdir(work)
    print("\nnetfake --selftest: %d passed, %d failed" % (passed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    print(__doc__)
    sys.exit(0)
