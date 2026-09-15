#!/usr/bin/env python3
"""scram-probe.py - one SD API session that logs in with SCRAM-SHA-256.

W.4 SCRAM phase 3, 14 Sep 2026.  The Windows port's order of work exercises the
server's requests 47 and 48 "by a throwaway client that speaks the exchange
directly" before the client library learns it (its verify-scramlogin).  This is
that client: the SD wire protocol over TCP, and the RFC 5802 / 7677 exchange
from Python's standard library - no SD code on the client side, so a pass
cannot be the client agreeing with itself.

  SD_SCRAM_PASSWORD=... python3 /home/don/Projects/sdcore4linux/sdb_ai/sd64/gplbld/scram-probe.py \
      --user <name> [--account <name>] [--hold SECONDS] [--final-only] [--] COMMAND...

No sudo of its own.  THE PASSWORD COMES FROM THE ENVIRONMENT, never the command
line.  Only its length is printed.

IT PRINTS WHAT IT DID: host, port, user, account; the TLS version and the
channel binding it computed; every request's number, server_error, status and
reply text; the server-first it received; and ONE verdict line whose wording
appears only on its own path:

  SCRAM: server signature VERIFIED          the login succeeded, mutually
  SCRAM: login REFUSED at request <n>: ...   the server refused it
  SCRAM: server signature MISMATCH           the server replied v= wrongly

--final-only sends request 48 with no 47 before it, which the server must
refuse as a sequence error.

--legacy (added with phase 4) sends the OLD cleartext request 24 instead of
SCRAM, exactly as sdclilib's SDConnect built it before 14 Sep 2026: int16
length and name, padded to even, then int16 length and password, padded.
Since phase 4 the client library no longer sends it, so this is the only way
left to reach request 24.  Its verdict lines are its own:

  LEGACY: login ACCEPTED                     request 24 logged in
  LEGACY: login REFUSED at request 24: ...   request 24 refused

--unix PATH (added with S.18, 14 Sep 2026) connects to the API's Unix socket
instead of TCP - the same protocol, the socket sdclient.socket also listens
on.  The "transport" line names what was actually connected to.

--pause SECONDS (added with S.13, 14 Sep 2026) waits after the login and the
account and BEFORE the commands, so a command's output proves the connection
survived whatever happened during the pause - REMOTE.API restarting the socket.

TLS (S.19, 15 Sep 2026).  Every API connection is TLS 1.3 and the login binds
to it: GS2 header 'p=tls-exporter,,' and c= base64(header + RFC 9266 binding).
PYTHON'S ssl MODULE CANNOT DO THIS - measured 15 Sep 2026, python 3.14.7:
ssl.CHANNEL_BINDING_TYPES is ['tls-unique'] and nothing exports keying
material - so the TLS session is driven through libssl directly with ctypes.
Still no SD code: the library is the system's OpenSSL.  SD_PROBE_LIBSSL names
the library to load if the default search picks the wrong one.

--no-tls (S.19) connects WITHOUT TLS, as every client did before S.19, and
waits for the plaintext ACK.  Its verdicts are its own:

  PLAINTEXT: no ACK - connection closed      the server refused plaintext
  PLAINTEXT: ACK RECEIVED                    the server spoke without TLS

--no-binding (S.19) logs in over TLS but with the old unbound header 'n,,'
and c=biws - the downgrade the server must refuse at request 47.

Exit 0 logged in (and the account, if given, entered), 1 refused (login or
account; and --no-tls's "no ACK"), 2 could not run, 3 the server's signature
did not verify (and --no-tls's "ACK RECEIVED").

Wire format, from gplsrc/sdclilib.c: a request is int32 length (including its
6-byte header), int16 request type, then the body, all little-endian; a reply
is int32 length (including 10 bytes of header), int16 server_error, int32
status, then the body.  The API server sends one ACK byte (0x06) first.
"""

import argparse
import base64
import ctypes
import ctypes.util
import hashlib
import hmac
import os
import socket
import struct
import sys
import time

REQ_QUIT = 1
REQ_GETERROR = 2
REQ_ACCOUNT = 3
REQ_EXECUTE = 21
REQ_LOGIN = 24
REQ_SCRAM_FIRST = 47
REQ_SCRAM_FINAL = 48

MIN_ITER = 4096          # the port's client bounds, sdclilib.c SCRAM_MIN/MAX
MAX_ITER = 10000000

GS2_BOUND = "p=tls-exporter,,"
BINDING_LABEL = b"EXPORTER-Channel-Binding"


def say(text):
    print(text)
    sys.stdout.flush()


class Tls:
    """TLS 1.3 client over a connected socket, through libssl with ctypes.

    No certificate check, as sdclilib: the SCRAM login bound to this session
    is what proves the server (gplsrc/sd_tls.c)."""

    SSL_CTRL_SET_MIN_PROTO_VERSION = 123
    SSL_CTRL_SET_MAX_PROTO_VERSION = 124
    TLS1_3_VERSION = 0x0304
    SSL_ERROR_ZERO_RETURN = 6

    def __init__(self, sock):
        self.lib_name, lib = self._load()
        vp, i, sz = ctypes.c_void_p, ctypes.c_int, ctypes.c_size_t
        sig = {
            "TLS_client_method": ([], vp),
            "SSL_CTX_new": ([vp], vp),
            "SSL_CTX_ctrl": ([vp, i, ctypes.c_long, vp], ctypes.c_long),
            "SSL_CTX_set_verify": ([vp, i, vp], None),
            "SSL_CTX_free": ([vp], None),
            "SSL_new": ([vp], vp),
            "SSL_set_fd": ([vp, i], i),
            "SSL_connect": ([vp], i),
            "SSL_get_error": ([vp, i], i),
            "SSL_read": ([vp, ctypes.c_char_p, i], i),
            "SSL_write": ([vp, ctypes.c_char_p, i], i),
            "SSL_get_version": ([vp], ctypes.c_char_p),
            "SSL_export_keying_material": ([vp, ctypes.c_char_p, sz, ctypes.c_char_p,
                                            sz, vp, sz, i], i),
            "SSL_shutdown": ([vp], i),
            "SSL_free": ([vp], None),
        }
        for name, (args, res) in sig.items():
            fn = getattr(lib, name)
            fn.argtypes = args
            fn.restype = res
        self.lib = lib
        self.sock = sock
        self.ctx = lib.SSL_CTX_new(lib.TLS_client_method())
        if not self.ctx:
            raise ConnectionError("TLS: cannot create a context")
        lib.SSL_CTX_ctrl(self.ctx, self.SSL_CTRL_SET_MIN_PROTO_VERSION, self.TLS1_3_VERSION, None)
        lib.SSL_CTX_ctrl(self.ctx, self.SSL_CTRL_SET_MAX_PROTO_VERSION, self.TLS1_3_VERSION, None)
        lib.SSL_CTX_set_verify(self.ctx, 0, None)
        self.ssl = lib.SSL_new(self.ctx)
        # libssl needs a blocking descriptor; a stalled server is bounded by
        # the socket's own timeouts instead of Python's.
        sock.setblocking(True)
        tv = struct.pack("ll", 30, 0)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO, tv)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDTIMEO, tv)
        if not self.ssl or lib.SSL_set_fd(self.ssl, sock.fileno()) != 1:
            raise ConnectionError("TLS: cannot attach to the socket")
        r = lib.SSL_connect(self.ssl)
        if r != 1:
            raise ConnectionError("TLS handshake failed (SSL_get_error %d)"
                                  % lib.SSL_get_error(self.ssl, r))
        self.version = lib.SSL_get_version(self.ssl).decode("ascii")
        out = ctypes.create_string_buffer(32)
        if lib.SSL_export_keying_material(self.ssl, out, 32, BINDING_LABEL,
                                          len(BINDING_LABEL), None, 0, 0) != 1:
            raise ConnectionError("TLS: cannot export the channel binding")
        self.binding = out.raw

    @staticmethod
    def _load():
        names = [os.environ.get("SD_PROBE_LIBSSL", ""), "libssl.so.4", "libssl.so.3",
                 ctypes.util.find_library("ssl") or ""]
        for name in names:
            if not name:
                continue
            try:
                return name, ctypes.CDLL(name)
            except OSError:
                continue
        raise ConnectionError("TLS: no libssl could be loaded (tried %s)"
                              % ", ".join(n for n in names if n))

    def sendall(self, data):
        while data:
            n = self.lib.SSL_write(self.ssl, data, len(data))
            if n <= 0:
                raise ConnectionError("TLS write failed (SSL_get_error %d)"
                                      % self.lib.SSL_get_error(self.ssl, n))
            data = data[n:]

    def recv(self, n):
        buf = ctypes.create_string_buffer(n)
        r = self.lib.SSL_read(self.ssl, buf, n)
        if r > 0:
            return buf.raw[:r]
        e = self.lib.SSL_get_error(self.ssl, r)
        if e == self.SSL_ERROR_ZERO_RETURN:
            return b""
        raise ConnectionError("TLS read failed (SSL_get_error %d)" % e)

    def close(self):
        if self.ssl:
            self.lib.SSL_shutdown(self.ssl)
            self.lib.SSL_free(self.ssl)
            self.ssl = None
        if self.ctx:
            self.lib.SSL_CTX_free(self.ctx)
            self.ctx = None
        self.sock.close()


def recv_exact(sock, n):
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("connection closed by server after %d of %d bytes"
                                  % (len(data), n))
        data += chunk
    return data


def request(sock, req, body):
    if isinstance(body, str):
        body = body.encode("utf-8")
    sock.sendall(struct.pack("<ih", 6 + len(body), req) + body)
    length, server_error, status = struct.unpack("<ihi", recv_exact(sock, 10))
    if length < 10 or length > 64 * 1024 * 1024:
        raise ConnectionError("invalid reply length %d" % length)
    text = recv_exact(sock, length - 10).decode("utf-8", errors="replace")
    say("  request %d -> server_error %d, status %d, %d byte(s)"
        % (req, server_error, status, len(text)))
    return server_error, status, text


def b64(raw):
    return base64.b64encode(raw).decode("ascii")


def main(argv):
    ap = argparse.ArgumentParser(description="One SCRAM-SHA-256 SD API session.")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=4243)
    ap.add_argument("--unix", default="",
                    help="connect to this Unix socket path instead of host:port")
    ap.add_argument("--user", required=True)
    ap.add_argument("--account", default="")
    ap.add_argument("--hold", type=float, default=0.0)
    ap.add_argument("--pause", type=float, default=0.0,
                    help="wait this long AFTER login and account, BEFORE the commands")
    ap.add_argument("--final-only", action="store_true",
                    help="send request 48 without 47 (must be refused)")
    ap.add_argument("--legacy", action="store_true",
                    help="send the old cleartext request 24 instead of SCRAM")
    ap.add_argument("--no-tls", action="store_true",
                    help="connect without TLS and wait for a plaintext ACK (must not come)")
    ap.add_argument("--no-binding", action="store_true",
                    help="log in over TLS with the unbound 'n,,' header (must be refused)")
    ap.add_argument("commands", nargs="*")
    a = ap.parse_args(argv)

    pw = os.environ.get("SD_SCRAM_PASSWORD")
    say("scram-probe")
    if a.unix:
        say("  transport: unix socket %s" % a.unix)
    else:
        say("  transport: tcp %s port %d" % (a.host, a.port))
    say("  user     : %s" % a.user)
    say("  account  : %s" % (a.account or "(none - authentication only)"))
    say("  password : %s" % ("from SD_SCRAM_PASSWORD, %d characters" % len(pw)
                             if pw is not None else "SD_SCRAM_PASSWORD is not set"))
    say("  mode     : %s" % ("connect WITHOUT TLS, expect no ACK" if a.no_tls
                             else "request 24, the old cleartext login" if a.legacy
                             else "request 48 ONLY, no 47" if a.final_only
                             else "47 then 48, UNBOUND 'n,,' over TLS" if a.no_binding
                             else "47 then 48, bound to TLS"))
    say("  commands : %d   hold: %gs   pause: %gs" % (len(a.commands), a.hold, a.pause))
    if pw is None or pw == "":
        say("scram-probe: CANNOT RUN - SD_SCRAM_PASSWORD is not set or empty.")
        return 2
    if a.commands and not a.account:
        say("scram-probe: CANNOT RUN - commands need --account.")
        return 2

    try:
        if a.unix:
            raw = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            raw.settimeout(30)
            raw.connect(a.unix)
        else:
            raw = socket.create_connection((a.host, a.port), timeout=30)
    except (OSError, ConnectionError) as e:
        say("scram-probe: CANNOT RUN - cannot connect: %s" % e)
        return 2

    if a.no_tls:
        try:
            ack = raw.recv(1)
        except OSError as e:
            ack = b""
            say("  recv: %s" % e)
        finally:
            raw.close()
        if ack == b"\x06":
            say("PLAINTEXT: ACK RECEIVED - the server spoke without TLS")
            return 3
        say("PLAINTEXT: no ACK - connection closed (got %r)" % ack)
        return 1

    try:
        sock = Tls(raw)
    except (OSError, ConnectionError) as e:
        raw.close()
        say("scram-probe: CANNOT RUN - %s" % e)
        return 2
    gs2 = "n,," if a.no_binding else GS2_BOUND
    cbind = "biws" if a.no_binding else b64(GS2_BOUND.encode("ascii") + sock.binding)
    say("  tls      : %s via %s, binding %s..." % (sock.version, sock.lib_name,
                                                  sock.binding[:8].hex()))
    say("  c=       : %s" % cbind)

    try:
        ack = recv_exact(sock, 1)
    except (OSError, ConnectionError) as e:
        sock.close()
        say("scram-probe: CANNOT RUN - no ACK inside TLS: %s" % e)
        return 2
    if ack != b"\x06":
        sock.close()
        say("scram-probe: CANNOT RUN - expected ACK 0x06, got %r" % ack)
        return 2

    cnonce = b64(os.urandom(18))
    cfirst_bare = "n=%s,r=%s" % (a.user, cnonce)

    try:
        if a.legacy:
            def field(text):
                raw_field = text.encode("utf-8")
                return (struct.pack("<h", len(raw_field)) + raw_field
                        + (b"\0" if len(raw_field) & 1 else b""))
            err, _, text = request(sock, REQ_LOGIN, field(a.user) + field(pw))
            if err != 0:
                say("LEGACY: login REFUSED at request 24: %s" % text)
                return 1
            say("LEGACY: login ACCEPTED")
            if a.account:
                err, _, text = request(sock, REQ_ACCOUNT, a.account)
                if err != 0:
                    say("account %s: REFUSED" % a.account)
                    return 1
                say("account %s: entered" % a.account)
            try:
                sock.sendall(struct.pack("<ih", 6, REQ_QUIT))
            except (OSError, ConnectionError):
                pass
            say("disconnected")
            return 0

        if a.final_only:
            err, _, text = request(sock, REQ_SCRAM_FINAL,
                                   "c=%s,r=%sAAAA,p=%s" % (cbind, cnonce, b64(b"\0" * 32)))
            if err != 0:
                say("SCRAM: login REFUSED at request 48: %s" % text)
                return 1
            say("scram-probe: request 48 without 47 was ACCEPTED - server_error 0")
            return 3

        err, _, sfirst = request(sock, REQ_SCRAM_FIRST, gs2 + cfirst_bare)
        if err != 0:
            say("SCRAM: login REFUSED at request 47: %s" % sfirst)
            return 1
        say("  server-first: %s" % sfirst)

        attrs = {}
        for part in sfirst.split(","):
            if len(part) > 2 and part[1] == "=":
                attrs[part[0]] = part[2:]
        nonce, salt_b64, iter_s = attrs.get("r", ""), attrs.get("s", ""), attrs.get("i", "")
        if not nonce.startswith(cnonce) or len(nonce) <= len(cnonce):
            say("scram-probe: server nonce does not extend ours - refusing to continue")
            return 3
        try:
            iterations = int(iter_s)
            salt = base64.b64decode(salt_b64, validate=True)
        except ValueError:
            say("scram-probe: malformed server-first")
            return 3
        if not MIN_ITER <= iterations <= MAX_ITER:
            say("scram-probe: iteration count %d outside %d..%d" % (iterations, MIN_ITER, MAX_ITER))
            return 3

        t0 = time.time()
        salted = hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), salt, iterations, 32)
        say("  PBKDF2 %d iterations: %.2f s" % (iterations, time.time() - t0))
        client_key = hmac.new(salted, b"Client Key", hashlib.sha256).digest()
        stored_key = hashlib.sha256(client_key).digest()
        server_key = hmac.new(salted, b"Server Key", hashlib.sha256).digest()
        cfinal_bare = "c=%s,r=%s" % (cbind, nonce)
        auth = ("%s,%s,%s" % (cfirst_bare, sfirst, cfinal_bare)).encode("utf-8")
        client_sig = hmac.new(stored_key, auth, hashlib.sha256).digest()
        proof = bytes(x ^ y for x, y in zip(client_key, client_sig))
        expected_v = "v=" + b64(hmac.new(server_key, auth, hashlib.sha256).digest())

        err, _, sfinal = request(sock, REQ_SCRAM_FINAL, "%s,p=%s" % (cfinal_bare, b64(proof)))
        if err != 0:
            say("SCRAM: login REFUSED at request 48: %s" % sfinal)
            return 1
        if not hmac.compare_digest(sfinal, expected_v):
            say("SCRAM: server signature MISMATCH (got %r)" % sfinal)
            return 3
        say("SCRAM: server signature VERIFIED")

        if a.account:
            err, _, text = request(sock, REQ_ACCOUNT, a.account)
            if err != 0:
                _, _, detail = request(sock, REQ_GETERROR, "")
                say("account %s: REFUSED: %s" % (a.account, detail or text))
                return 1
            say("account %s: entered" % a.account)

        if a.pause > 0:
            say("pausing %gs before the commands" % a.pause)
            time.sleep(a.pause)

        for cmd in a.commands:
            say("> %s" % cmd)
            err, _, out = request(sock, REQ_EXECUTE, cmd)
            for line in out.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
                if line != "":
                    say("| %s" % line)
            say("  (server_error %d)" % err)

        if a.hold > 0:
            say("holding the connection %gs" % a.hold)
            time.sleep(a.hold)
        try:
            sock.sendall(struct.pack("<ih", 6, REQ_QUIT))
        except (OSError, ConnectionError):
            pass
        say("disconnected")
        return 0
    except (OSError, ConnectionError) as e:
        say("scram-probe: connection failed part way: %s" % e)
        return 1
    finally:
        sock.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
