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

IT PRINTS WHAT IT DID: host, port, user, account; every request's number,
server_error, status and reply text; the server-first it received; and ONE
verdict line whose wording appears only on its own path:

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
on.  Its server side used to read the peer's uid with getpeereid() for the
retired APILOGIN=0 login; that code is removed, so this is how a witness shows
the socket still serves SCRAM and still refuses request 24.  The "transport"
line names what was actually connected to.

Exit 0 logged in (and the account, if given, entered), 1 refused (login or
account), 2 could not run, 3 the server's signature did not verify.

Wire format, from gplsrc/sdclilib.c: a request is int32 length (including its
6-byte header), int16 request type, then the body, all little-endian; a reply
is int32 length (including 10 bytes of header), int16 server_error, int32
status, then the body.  The API server sends one ACK byte (0x06) first.
"""

import argparse
import base64
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


def say(text):
    print(text)
    sys.stdout.flush()


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
    ap.add_argument("--final-only", action="store_true",
                    help="send request 48 without 47 (must be refused)")
    ap.add_argument("--legacy", action="store_true",
                    help="send the old cleartext request 24 instead of SCRAM")
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
    say("  mode     : %s" % ("request 24, the old cleartext login" if a.legacy
                             else "request 48 ONLY, no 47" if a.final_only else "47 then 48"))
    say("  commands : %d   hold: %gs" % (len(a.commands), a.hold))
    if pw is None or pw == "":
        say("scram-probe: CANNOT RUN - SD_SCRAM_PASSWORD is not set or empty.")
        return 2
    if a.commands and not a.account:
        say("scram-probe: CANNOT RUN - commands need --account.")
        return 2

    try:
        if a.unix:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(30)
            sock.connect(a.unix)
        else:
            sock = socket.create_connection((a.host, a.port), timeout=30)
        ack = recv_exact(sock, 1)
    except (OSError, ConnectionError) as e:
        say("scram-probe: CANNOT RUN - cannot connect: %s" % e)
        return 2
    if ack != b"\x06":
        say("scram-probe: CANNOT RUN - expected ACK 0x06, got %r" % ack)
        return 2

    cnonce = b64(os.urandom(18))
    cfirst_bare = "n=%s,r=%s" % (a.user, cnonce)

    try:
        if a.legacy:
            def field(text):
                raw = text.encode("utf-8")
                return struct.pack("<h", len(raw)) + raw + (b"\0" if len(raw) & 1 else b"")
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
            except OSError:
                pass
            say("disconnected")
            return 0

        if a.final_only:
            err, _, text = request(sock, REQ_SCRAM_FINAL,
                                   "c=biws,r=%sAAAA,p=%s" % (cnonce, b64(b"\0" * 32)))
            if err != 0:
                say("SCRAM: login REFUSED at request 48: %s" % text)
                return 1
            say("scram-probe: request 48 without 47 was ACCEPTED - server_error 0")
            return 3

        err, _, sfirst = request(sock, REQ_SCRAM_FIRST, "n,," + cfirst_bare)
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
        cfinal_bare = "c=biws,r=%s" % nonce
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
        except OSError:
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
