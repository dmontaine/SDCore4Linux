#!/usr/bin/env python3
"""netfake.py - a FAKE SD API SERVER for the SDNet login rows (S.65 slice 2b).  Shared by sandbox-net.py.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/netfake.py --selftest

No sd, no sudo.  The self-test needs the openssl command line (it makes a throw-away certificate) and the loopback interface.

20 Oct 26 dm  S.72 (QMNet parity, tier B): requests 32 FILELOCK and 33 FILEUNLOCK are served, as gpl.bp/apisrvr's vb.filelock and vb.fileunlock do with the kernel's op_filelock() and
              op_flunlock() (gplsrc/op_lock.c): FILELOCK is fno and wait (two signed 16 bit integers); wait 0 answers SV$LOCKED with STATUS() the holder's user number (another user's file
              lock, else the owner of a record lock in the file held by ANOTHER user), a wait that is not 0 waits cfg lock_wait seconds and then gives up with the ON ERROR reply the
              other waits use; the success STATUS() is cfg success_status (apisrvr sends whatever the last statement left); a second FILELOCK of a file the session already holds succeeds
              and does not change which file number owns the lock.  FILEUNLOCK answers SV$OK with STATUS() 0 (it was ours: let go, waiters woken), 3011 (ER$LCK: another user holds it, left
              held) or 3012 (ER$NLK: nobody holds it); that STATUS() is the answer and success_status never replaces it.  The lock is bound to the FILE NUMBER that took it (the kernel binds
              it to the file variable, fptr->fvar_index): CLOSE of that file number lets it go (op_dio1.c dio_close), CLOSE of another file number of the same file does not; request 15 with
              file number 0 lets go of every file lock of the session and request 15 with an empty id lets go of the file lock if THAT file number took it (op_lock.c unlock_record(), what
              RLSALL and RLSFILE call); the end of the session lets it go (clopts.c).  FakeStore.locks_of(userno) lists a file lock as (lock name, "", "file").  The gate is as before:
              32 and 33 are in FILES_CHANGE.  The self-test rows are in selftest_writes, section W16; sandbox-req29.py section F holds the facts to a real `sd -Q`.
19 Oct 26 dm  Verifier finding (finish 2): stall_first (the Ack is sent and client-first read, then silence: the wait for the first reply of the login) beside ack=False (silence before the Ack).
              With ack=False a client of this fake waits to the fake's own 5 second close, not to NETREPLY, because the TLS 1.3 session tickets the server sends after the handshake make the
              socket readable and READ.SOCKET's timeout is then spent (op_skt.c; measured by turning the tickets off in a scratch copy: 3.0 s).
19 Oct 26 dm  Verifier finding (finish 2): HangingListener (a listener whose accept queue is full, so a connect to it hangs) and restart_with_conf (sd.conf plus lines, SD restarted), the two
              things the NETWAIT and NETREPLY rows of sandbox-net.py and sandbox-netfile.py share; sandbox-netfile.py's own copy of the restart is gone.
19 Oct 26 dm  Verifier finding (finish 2): the ids this fake refuses are those holding the FIVE MARKS, bytes 251 to 255 (sddefs.h TEXT_MARK to ITEM_MARK), not 248 to 255: the real
              server accepts 248, 249 and 250 in an id (measured, sandbox-req29.py section G, which sends 250 and 251 to a real `sd -Q`).
19 Oct 26 dm  K1, K8b, K8c.  (1) The ON ERROR replies this fake imitates now follow the REAL server (REAL_ON_ERROR, measured by sandbox-req29.py section G on a real `sd -Q`): the
              sign of STATUS() (+3000 and +3018, not -3000 and -3018), no text for a statement with an ON ERROR clause, and for one without (CLEARFILE, request 30) STATUS() 0
              and the kernel's text with the program and line.  (2) The text of an ON ERROR reply is shown by the $netfile handler since this change, so the message of the
              files-only refusal (11521) reaches the person at the client.  (3) bad_length: a reply that is a header alone with a length that cannot be true, then silence.
              (4) The "NOT YET RUN AGAINST SD" notes below were true when written and are not now.
18 Oct 26 dm  S.65 write group (the owner's yes of that day): config write_group, and add_user(write_group=...), is the login's membership of the Linux group
              sdfileswrite.  A files-only login WITHOUT it is refused the change set (FILES_CHANGE: 7 to 10, 16 to 19, 30 to 33, and any nonzero flag of 41) with
              message 11521 as an ON ERROR reply, as gpl.bp/apifilesok's third argument and vb.readv do; sdapi-style (not files-only) sessions are untouched.  The
              default is False, the real default, so a row that writes through a files-only login must say write_group=True.  And the dictionary open: "dict <name>"
              (any case, one space) is OPEN 'DICT', name and any other name is opened as it stands; the REAL server did not understand the lower case form until
              vb.open was fixed (the same day), and this fake had always accepted it.
17 Oct 26 dm  New.  S.65 slice 2b.  (RUN AGAINST SD since: sandbox-net.py section netlogin drives set.netlogin against it - 19 Oct 26, K8b.)  The self-test runs it
              against a Python client built from RFC 7677's own vectors.

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

17 Oct 26 dm  S.65 slice 3a: THE FILE REQUESTS.  (RUN AGAINST SD since: sandbox-netfile.py drives the BASIC class and the $netfile handler against it, and
              19 Oct 26 sandbox-req29.py section G holds its ON ERROR replies to what a real `sd -Q` answers - K8b; the self-test drives it with a Python client
              written from gpl.bp/apisrvr and gpl.bp/sdclient.)  With configure(files=True) a connection that has logged in is SERVED instead of listened to: the
              requests of apisrvr that a files-only session needs, in the reply formats apisrvr writes (see FileSession; every handler
              names the apisrvr label it copies), against an in-memory store (FakeStore: files, records, dictionary items, a lock table
              that lives across connections, so that a second connection is told a record is locked and by whom).  Such a connection
              gets a thread of its own (the lock rows need two at once); a connection with files=False is handled inline as before.
              files_only=True (or a user added with files_only=True) is the SDNet login: every request outside gpl.bp/apifilesok's
              allow list is answered with message 11480 and never dispatched.  Faults: close_after_requests, drop_request, delay,
              no_reply, fail (see DEFAULTS).  A user can be added from derived keys alone (add_user_keys): the exchange on the wire is
              the same, so a client proving itself from ClientKey is accepted exactly as one proving itself from the password.
              ***WHAT IT DOES NOT BE FAITHFUL TO*** (stated once): (1) STATUS() after a successful request is 0 here; apisrvr sends
              whatever the last statement of the session left in it.  (2) The text of an ABORT reply is the bare message (1010 for an
              unknown FILEINFO key); the real one is the kernel's error text, which names the program and line.  (3) A waiting lock
              request (8, 10, and 41 with an update or shared flag) gives up after cfg lock_wait seconds with an ON ERROR reply that
              says so; the real server waits for ever.  (4) [changed by slice 3e, below] A connection that
              ends releases all of its locks.
              (5) SELECT returns the ids in insertion order; the real order is the hash order, so a test must not depend on either.
              (6) NOT BUILT, answered with an error that says so and noted in errors: the indices
              (26, 35, 36, 38, 39, 42 to 45), and everything from 20 on that apisrvr offers (call, execute, sequential files,
              trans, transactions ...).  [Writes, deletes, record locks and CLEARFILE, 16 to 19, 30 and 31, are built since slice 3e;
              the file locks of 32 and 33 since S.72, 20 Oct 26.]

18 Oct 26 dm  S.65 slice 3e: WRITES AND LOCKS.  (RUN AGAINST SD since: sandbox-netfile.py sections hwrite, kwrite and wgroup drive the $netfile handler and the kernel's
              NET_FILE statements against them - 19 Oct 26, K8b.)
              Requests 16 WRITE, 17 WRITEU, 18 DELETE, 19 DELETEU, 30 RECORDLOCK and 31 CLEARFILE are served in the reply formats of
              gpl.bp/apisrvr (vb.write, vb.writeu, vb.delete, vb.deleteu, vb.lock.record, vb.clearfile), from the spec
              .claude/s65-stage2-design.md section 10.  What a WRITE does: the session's record lock on the id (read or update) is let go,
              WRITEU / DELETEU keep it; a DELETE of a record that is not there is a success; a NOCASE file keeps the key it already holds.
              CLOSE now lets go of the record locks taken through THAT file number (FileSession.taken: {file number: {(lock name, lock
              id)}}); a RELEASE and a plain WRITE or DELETE through any slot prune the sets by file and id, as unlock_record does.
              ***WHAT IT DOES NOT BE FAITHFUL TO, added by 3e***  (7) STATUS() after a success is cfg success_status (0 unless a row says
              otherwise), never what the last statement left; the real server sends whatever it left, which is why the client must not
              read it.  (8) If two file numbers of one session both hold the same record lock (the second asked for what it already
              had), closing either one lets it go; the real CLOSE was not traced.  (9) CLEARFILE does not look at record locks, only at
              another user's file lock, and does not touch the lock table.  (10) A request packet may be up to 16 MB (the old limit was
              64 KB, enough for requests that carry an id).  (11) The text of an ON ERROR reply for a read only file, an id that is not
              valid and a lock on a null id is the fake's own wording (the real one is the kernel's, with the program and line).
              Faults added: success_status, must_lock, readonly, edit_allow, maxrlock, drop_before, drop_after (see DEFAULTS).

20 Oct 26 dm  ***WHAT IT DOES NOT BE FAITHFUL TO, added by S.72***  (12) FILELOCK with a wait flag that is not 0 gives up after cfg lock_wait seconds with an ON ERROR reply (the real
              server waits for ever; the S.72 client never sends it, it asks again every 250 ms with the flag 0).  (13) When record locks of several OTHER users stand in the way of a
              FILELOCK the user number reported is the lowest; the kernel reports the first one in the lock table's own order.  (14) A file lock does not count toward cfg maxrlock
              (the kernel's MAXRLOCK counts record locks).
"""

import base64
import hashlib
import hmac
import os
import re
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

# Replies: gpl.bp/sdclient $define SV$OK .. SV$PROMPT.  SV_LOCKED is the LOCKED clause, SV_ELSE the ELSE clause, SV_ERROR "text to be fetched with
# request 2" (the reply has no data), SV_ON_ERROR the ON ERROR clause or an abort (the reply data is the message).
SV_ELSE, SV_LOCKED = 2, 4
# Request numbers: gpl.bp/sdclient $define Srvr...; apisrvr's dispatch table.
R_QUIT, R_GETERROR, R_ACCOUNT, R_OPEN, R_CLOSE = 1, 2, 3, 4, 5
R_READ, R_READL, R_READLW, R_READU, R_READUW = 6, 7, 8, 9, 10
R_SELECT, R_READNEXT, R_CLEARSELECT, R_READLIST, R_RELEASE = 11, 12, 13, 14, 15
R_RECORDLOCKED, R_SELECTLIST, R_FILEINFO, R_READV, R_MARKMAPPING, R_REVISION = 34, 37, 40, 41, 46, 49
# 18 Oct 26 S.65 slice 3e: the changing and locking requests.
R_WRITE, R_WRITEU, R_DELETE, R_DELETEU, R_LOCKRECORD, R_CLEARFILE = 16, 17, 18, 19, 30, 31
# 20 Oct 26, S.72: the file lock requests.
R_FILELOCK, R_FILEUNLOCK = 32, 33
# The requests apisrvr has a handler for that this fake does not build (see the module text); a number apisrvr has no handler for is "illegal".
NOT_BUILT = frozenset(list(range(20, 27)) + [29, 35, 36, 38, 39] + list(range(42, 46)) + [47, 48] + list(range(50, 70)))
# The requests whose successful reply carries cfg success_status (the STATUS() apisrvr leaves for the client, which the client must not trust).  R_FILEUNLOCK is NOT here: its STATUS() is the answer.
STATUS_REQUESTS = frozenset([R_RELEASE, R_WRITE, R_WRITEU, R_DELETE, R_DELETEU, R_LOCKRECORD, R_CLEARFILE, R_FILELOCK])
MAX_PACKET = 16 * 1024 * 1024   # the largest request packet this server reads; a WRITE carries the whole record
MAX_ID = 63                     # the server's longest record id (MAXIDLEN); the client refuses a longer one before it sends
KIND_NAMES = ("", "voc", "dict", "prog")       # the edit gate kinds, by apisrvr's numbering: 11404 + kind is the message
# gpl.bp/apifilesok's allow table, number by number (3, set account, is allowed once and handled in FileSession.allowed).  The self-test
# parses the program and holds this to it, so a request added there and not here is found.
FILES_OK = frozenset([1, 2] + list(range(4, 20)) + [26] + list(range(30, 47)) + [49])
# 18 Oct 26, S.65 write group: the part of that table a files-only login may use only if it is ALSO in the Linux group sdfileswrite (gpl.bp/apifilesok's third
# argument, `files.chg`): the locking reads 7 to 10, the writes and deletes 16 to 19, the record lock 30, clearfile 31, filelock 32 and fileunlock 33.  Written
# here and held to the program by the self-test.  Request 41 (readv) is in FILES_OK for a plain READV; its flags 1, 2, 5 and 6 take a lock and apisrvr's vb.readv
# refuses any nonzero flag itself (FileSession.r_readv).
FILES_CHANGE = frozenset([7, 8, 9, 10, 16, 17, 18, 19, 30, 31, 32, 33])
# err.h
ER_IID, ER_RNF, ER_NAM, ER_FNF = 3000, 3006, 3002, 3003
ER_RDONLY, ER_NOLOCK, ER_MAXRLOCK = 3018, 3023, 3060
ER_LCK, ER_NLK = 3011, 3012     # FILEUNLOCK: another user holds the file lock / nobody does

# 19 Oct 26 (K1).  WHAT THE REAL SERVER ANSWERS where this fake imitates an ON ERROR reply, MEASURED on a real `sd -Q` by sandbox-req29.py section G: one row there for each
# entry, which compares the server with THESE values, so that a change in the server turns that row red and this table cannot go stale quietly.  (error field, STATUS() as
# the wire carries it, the whole text as a regex).  Three things the first versions of this fake got wrong: (1) the SIGN - an over-long or empty id and a read only file
# answer +3000 and +3018 (MUSTLOCK, -3023, is from op_dio3.c and was not measured on a real server); (2) a statement WITH an ON ERROR clause (write, delete, readu ...) sends
# NO text - the server empties its message at the top of each request - while one WITHOUT (clearfile, lock record) aborts, and an abort's reply is STATUS() 0 and the
# KERNEL's text, "<8 hex digits>: <message> at line <n> of $apisrvr"; (3) MAXRLOCK is the first kind for a locking read and the second for request 30.
REAL_ON_ERROR = {
    "write_bad_id": (1, ER_IID, r""),
    "delete_bad_id": (1, ER_IID, r""),
    "write_readonly": (1, ER_RDONLY, r""),
    "delete_readonly": (1, ER_RDONLY, r""),
    "clearfile_readonly": (1, 0, r"[0-9A-F]{8}: CLEARFILE on read-only file at line \d+ of \$apisrvr"),
    "readu_maxrlock": (1, ER_MAXRLOCK, r""),
    "lockrecord_maxrlock": (1, 0, r"[0-9A-F]{8}: Record lock limit \(MAXRLOCK\) reached at line \d+ of \$apisrvr"),
}


def abort_text(message, line):
    """The text of an abort reply as the real server sends it, with a stand-in address; the line is the line apisrvr had on 19 Oct 26 and no row depends on it."""
    return "%08X: %s at line %d of $apisrvr" % (0x25DD, message, line)
FL_TYPE_DH, FL_TYPE_DIR = 3, 4
# FILEINFO keys op_dio2.c knows (a key outside this set is an abort: "Illegal action key", message 1010).  The key is cut to a signed 16 bit
# integer first, as op_dio2.c does ((int16_t)).
FL_KNOWN = frozenset([0, 1, 2, 3] + list(range(5, 12)) + [13, 14] + list(range(1000, 1041)) + [1100] + list(range(10000, 10006)))
FM = "\xfe"
USERNO_BASE = 100               # the user number of the first connection is USERNO_BASE + 1: the number a lock holder is known by

# The messages this fake sends, read from the tree's own message files so that a changed text is followed; the copy is for a tree that is
# not there (the self-test holds the copy to the files when they exist).
_MSG_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sdsys", "messages"))
_MSG_COPY = {1010: "Illegal action key", 5037: "Invalid account name", 5262: "File access is disabled", 5268: "Invalid file number",
             5269: "Invalid select list number", 10003: "User not allowed in requested account",
             11480: "This login is for files only: request %1 is not allowed",
             11521: "This login cannot change or lock files here: ask the administrator for files-write-on (request %1)",
             11162: "Record lock limit (MAXRLOCK) reached",
             11405: "The VOC can only be changed by an account that has voc.edit (SDSYS can give it: modify.account <account> voc-on)",
             11406: "A dictionary can only be changed by an account that has dict.edit (SDSYS can give it: modify.account <account> dict-on)",
             11407: "A program file can only be changed by an account that has bp.edit (SDSYS can give it: modify.account <account> bp-on)",
             11410: "The pathname of the file cannot be read, so a change to it is refused"}
_LOW = {c: c + 32 for c in range(65, 91)}
_UP = {c: c - 32 for c in range(97, 123)}


def msg(num, *args):
    """sysmsg(num, args): the first line of sdsys/messages/<num>, %1 .. %n replaced."""
    text = None
    try:
        with open(os.path.join(_MSG_DIR, str(num)), encoding="latin-1") as fh:
            text = fh.readline().rstrip("\r\n")
    except OSError:
        pass
    if text is None:
        text = _MSG_COPY[num]
    for i, a in enumerate(args, 1):
        text = text.replace("%" + str(i), str(a))
    return text


def _lower(s):
    """ASCII only: SD is English only."""
    return s.translate(_LOW)


def _upper(s):
    return s.translate(_UP)


def _short(data, pos):
    """oconv(cmnd[pos+1, 2], 'ISL'): a signed 16 bit integer; a request that is too short reads as if padded with nulls."""
    b = data[pos:pos + 2]
    return struct.unpack("<h", b + b"\0" * (2 - len(b)))[0]


def _long(data, pos):
    """oconv(cmnd[pos+1, 4], 'ILL'): an unsigned 32 bit integer."""
    b = data[pos:pos + 4]
    return struct.unpack("<I", b + b"\0" * (4 - len(b)))[0]


def _rid(data, pos):
    """cmnd[pos+1, 99]: a record id."""
    return data[pos:pos + 99].decode("latin-1")


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


class FakeFile:
    """One file of the store.  name is the VOC name (lower case); records {id: record text, marks as characters 248-255 of the latin-1 text};
    dict_items the items of its dictionary (opened as "dict <name>"); path what FILEINFO(.., 2) answers; info {FILEINFO key: value} overrides
    what the fake would answer; nocase folds ids (ASCII) for the lookup and the lock table; ftype 3 (dynamic) or 4 (directory)."""

    def __init__(self, name, records=None, dict_items=None, path=None, info=None, nocase=False, ftype=FL_TYPE_DH, fileid=0):
        self.name = name
        self.vocname = name
        self.lockname = name
        self.records = dict(records or {})
        self.dict_items = dict(dict_items or {})
        self.path = path if path is not None else "/fake/" + name
        self.info = dict(info or {})
        self.nocase = bool(nocase)
        self.ftype = ftype
        self.fileid = fileid
        self._dict = None

    def find(self, rid):
        """The id as the file holds it (a nocase file matches ids that differ in ASCII case), or None."""
        if rid in self.records:
            return rid
        if self.nocase:
            u = _upper(rid)
            for k in self.records:
                if _upper(k) == u:
                    return k
        return None

    def get(self, rid):
        k = self.find(rid)
        return None if k is None else self.records[k]

    def lockid(self, rid):
        return _upper(rid) if self.nocase else rid

    def dictionary(self):
        """The file as opened by "dict <name>": its own records are the dictionary items (the same dict object, so a change shows), and it
        has its own lock table namespace."""
        if self._dict is None:
            d = FakeFile("dict " + self.name, None, None, "/fake/dict." + self.name, self.info, self.nocase, self.ftype, self.fileid)
            d.records = self.dict_items
            d.vocname = self.name
            self._dict = d
        return self._dict

    def edit_kind(self):
        """The S.64 edit gate this file falls under, by apisrvr's numbering: 0 none, 1 VOC, 2 dictionary, 3 program file.  The real server
        answers by the LAST COMPONENT OF THE PATHNAME of the open file (so a Q-pointer to a VOC is caught): voc, *.dic, bp, bp.out, *.bp,
        *.bp.out; a file opened as "dict <name>" is a dictionary whatever its path."""
        leaf = self.path.replace("\\", "/").rsplit("/", 1)[-1].lower()
        if self.name.startswith("dict ") or leaf.endswith(".dic"):
            return 2
        if leaf == "voc":
            return 1
        if leaf in ("bp", "bp.out") or leaf.endswith(".bp") or leaf.endswith(".bp.out"):
            return 3
        return 0


class FakeStore:
    """The data and the lock table of the fake server, shared by every connection (it is the server's, not the session's).  A test
    configures it before it connects:

        st = srv.store
        st.add_file("customers", {"c1": "Smith" + FM + "100"}, dict_items={"name": "D" + FM + "1"})   # a file, its records, its dictionary
        st.put("customers", "c2", "Jones")  /  st.delete("customers", "c2")  /  st.records("customers")
        st.accounts = {"acct"}                    # the accounts request 3 accepts; None (the default) accepts any valid name
        st.hold("customers", "c1", userno=7)      # another process holds an update lock (kind="shared" for a read lock)
        st.hold_file("customers", userno=7)       # ... or the file lock;  st.drop_user(7) lets everything of that user go
        st.locks_of(userno) -> [(file, id, "update"|"shared")] and, since S.72, (file, "", "file") for a file lock     srv.sessions[i].userno is a connection's user number
        st.filelock_try(st.file("customers"), 7)  # 0: user 7 now holds the file lock (or already did); else the holder in the way (S.72; filelock_acquire waits, filelock_release unlocks)
    """

    def __init__(self):
        self.cond = threading.Condition()
        self.files = {}
        self.locks = {}                 # (lockname, lock id) -> {"u": user number holding the update lock or None, "s": set of read lock holders}
        self.filelocks = {}             # lockname -> user number holding the file lock
        self.accounts = None

    # ---- the data ---------------------------------------------------------------------------------------------------------------
    def add_file(self, name, records=None, dict_items=None, **kw):
        name = _lower(name)
        with self.cond:
            f = FakeFile(name, records, dict_items, fileid=len(self.files) + 1, **kw)
            self.files[name] = f
        return f

    def file(self, name):
        with self.cond:
            return self.files.get(_lower(name))

    def put(self, name, rid, text):
        with self.cond:
            self.files[_lower(name)].records[rid] = text

    def delete(self, name, rid):
        with self.cond:
            self.files[_lower(name)].records.pop(rid, None)

    def records(self, name):
        with self.cond:
            return dict(self.files[_lower(name)].records)

    # ---- what a served WRITE, DELETE and CLEARFILE do (18 Oct 26, slice 3e) ---------------------------------------------------------
    def write_rec(self, f, rid, text):
        """A nocase file keeps the key it already holds (the new text goes under it); a new record gets the id as sent."""
        with self.cond:
            k = f.find(rid)
            f.records[rid if k is None else k] = text

    def delete_rec(self, f, rid):
        with self.cond:
            k = f.find(rid)
            if k is not None:
                del f.records[k]

    def clear_file(self, f):
        with self.cond:
            f.records.clear()

    def filelock_wait(self, f, me, timeout):
        """0 when no OTHER user holds the file lock (at once, or within timeout seconds); else the holder still in the way."""
        end = time.time() + timeout
        with self.cond:
            while True:
                h = self.filelocks.get(f.lockname, 0)
                if h == 0 or h == me:
                    return 0
                left = end - time.time()
                if left <= 0:
                    return h
                self.cond.wait(min(left, 0.1))

    def holds(self, f, rid, me):
        """True when user me holds a read or an update lock on the record."""
        with self.cond:
            ent = self.locks.get((f.lockname, f.lockid(rid)))
            return bool(ent) and (ent["u"] == me or me in ent["s"])

    def holds_update(self, f, rid, me):
        with self.cond:
            ent = self.locks.get((f.lockname, f.lockid(rid)))
            return bool(ent) and ent["u"] == me

    def count_locks(self, me):
        """How many RECORD locks user me holds (MAXRLOCK counts these; a file lock is not one of them)."""
        with self.cond:
            return sum((ent["u"] == me) + (me in ent["s"]) for ent in self.locks.values())

    # ---- the lock table: op_lock.c lock_record() ---------------------------------------------------------------------------------
    def _try(self, f, rid, update, me):
        """0 when the lock is taken (or already held, upgraded or taken down to a read lock as lock_record() does), else the user number of
        the process in the way.  The caller holds self.cond."""
        fl = self.filelocks.get(f.lockname, 0)
        if fl and fl != me:
            return fl
        key = (f.lockname, f.lockid(rid))
        ent = self.locks.setdefault(key, {"u": None, "s": set()})
        try:
            if ent["u"] == me:
                if not update:
                    ent["u"] = None
                    ent["s"].add(me)
                return 0
            if me in ent["s"]:
                if not update:
                    return 0
                others = sorted(ent["s"] - {me})
                if others:
                    return others[0]
                ent["s"].discard(me)
                ent["u"] = me
                return 0
            if ent["u"] is not None:
                return ent["u"]
            if update:
                if ent["s"]:
                    return sorted(ent["s"])[0]
                ent["u"] = me
                return 0
            ent["s"].add(me)
            return 0
        finally:
            if ent["u"] is None and not ent["s"]:
                self.locks.pop(key, None)

    def lock_try(self, f, rid, update, me):
        with self.cond:
            return self._try(f, rid, update, me)

    def lock_wait(self, f, rid, update, me, timeout):
        """0 when the lock was taken within timeout seconds, else the holder in the way."""
        end = time.time() + timeout
        with self.cond:
            while True:
                h = self._try(f, rid, update, me)
                if h == 0:
                    return 0
                left = end - time.time()
                if left <= 0:
                    return h
                self.cond.wait(min(left, 0.1))

    def recordlocked(self, f, rid, me):
        """(RECORDLOCKED() code, STATUS()) as op_lock.c op_reclckd() leaves them: -3 -2 -1 another user holds a file, update or read lock,
        0 none, 1 2 3 this session holds a read, update or file lock; the status is the owner's user number (0 when nothing is held)."""
        with self.cond:
            fl = self.filelocks.get(f.lockname, 0)
            if fl:
                return (3 if fl == me else -3), fl
            ent = self.locks.get((f.lockname, f.lockid(rid)))
            if not ent:
                return 0, 0
            if ent["u"] == me:
                return 2, me
            if me in ent["s"]:
                return 1, me
            if ent["u"] is not None:
                return -2, ent["u"]
            if ent["s"]:
                return -1, sorted(ent["s"])[-1]
            return 0, 0

    # ---- 20 Oct 26, S.72: the file lock, op_lock.c op_filelock() and op_flunlock() ---------------------------------------------------
    def filelock_holder(self, f):
        """The user number that holds the file lock on f, 0 when nobody does."""
        with self.cond:
            return self.filelocks.get(f.lockname, 0)

    def _filelock_try(self, f, me):
        """op_filelock(): 0 when user me holds the file lock afterwards (it is taken now, or it was already mine), else the user number in the way: the holder of another
        user's file lock, or the owner of a record lock in the file held by ANOTHER user (when several, the lowest number: the kernel reports the first in its lock table).
        The caller holds self.cond."""
        h = self.filelocks.get(f.lockname, 0)
        if h:
            return 0 if h == me else h
        others = set()
        for (name, _lid), ent in self.locks.items():
            if name != f.lockname:
                continue
            if ent["u"] is not None and ent["u"] != me:
                others.add(ent["u"])
            others.update(s for s in ent["s"] if s != me)
        if others:
            return min(others)
        self.filelocks[f.lockname] = me
        return 0

    def filelock_try(self, f, me):
        """0 when the file lock on f is user me's (taken now, or it already was), else the holder in the way (not waiting)."""
        with self.cond:
            return self._filelock_try(f, me)

    def filelock_acquire(self, f, me, timeout):
        """As filelock_try, but waits up to timeout seconds for the one in the way to let go (every release notifies)."""
        end = time.time() + timeout
        with self.cond:
            while True:
                h = self._filelock_try(f, me)
                if h == 0:
                    return 0
                left = end - time.time()
                if left <= 0:
                    return h
                self.cond.wait(min(left, 0.1))

    def filelock_release(self, lockname, me):
        """op_flunlock(): 0 when user me held the file lock (now let go, waiters woken), ER$LCK 3011 when another user holds it (left held), ER$NLK 3012 when nobody does."""
        with self.cond:
            h = self.filelocks.get(lockname, 0)
            if h == me:
                del self.filelocks[lockname]
                self.cond.notify_all()
                return 0
            return ER_LCK if h else ER_NLK

    def release_filelocks(self, me):
        """RLSALL: every file lock of user me goes; the other users' are not touched."""
        with self.cond:
            for k in [k for k, v in self.filelocks.items() if v == me]:
                del self.filelocks[k]
            self.cond.notify_all()

    def release_one(self, f, rid, me):
        self.release_key(f.lockname, f.lockid(rid), me)

    def release_key(self, lockname, lockid, me):
        """Let go of user me's lock (read or update) on one (lock name, lock id); the other users' are not touched."""
        with self.cond:
            key = (lockname, lockid)
            ent = self.locks.get(key)
            if ent:
                if ent["u"] == me:
                    ent["u"] = None
                ent["s"].discard(me)
                if ent["u"] is None and not ent["s"]:
                    del self.locks[key]
            self.cond.notify_all()

    def release_file(self, f, me):
        with self.cond:
            for key in [k for k in self.locks if k[0] == f.lockname]:
                ent = self.locks[key]
                if ent["u"] == me:
                    ent["u"] = None
                ent["s"].discard(me)
                if ent["u"] is None and not ent["s"]:
                    del self.locks[key]
            self.cond.notify_all()

    def release_all(self, me):
        with self.cond:
            for key in list(self.locks):
                ent = self.locks[key]
                if ent["u"] == me:
                    ent["u"] = None
                ent["s"].discard(me)
                if ent["u"] is None and not ent["s"]:
                    del self.locks[key]
            self.cond.notify_all()

    def drop_user(self, me):
        """Everything user number me held, as the end of a process lets it go."""
        self.release_all(me)
        with self.cond:
            for k in [k for k, v in self.filelocks.items() if v == me]:
                del self.filelocks[k]
            self.cond.notify_all()

    # ---- for tests: a lock held by a process that is not a connection of this server ------------------------------------------------
    def hold(self, name, rid, userno, kind="update"):
        f = self.file(name)
        h = self.lock_try(f, rid, kind == "update", userno)
        if h:
            raise RuntimeError("netfake: %s/%s is held by user %d" % (name, rid, h))

    def hold_file(self, name, userno):
        with self.cond:
            self.filelocks[_lower(name)] = userno

    def locks_of(self, userno):
        """Every lock of the user, sorted: (lock name, id, "update" | "shared") for a record lock and, since S.72, (lock name, "", "file") for a file lock."""
        with self.cond:
            out = []
            for (name, lid), ent in self.locks.items():
                if ent["u"] == userno:
                    out.append((name, lid, "update"))
                if userno in ent["s"]:
                    out.append((name, lid, "shared"))
            for name, holder in self.filelocks.items():
                if holder == userno:
                    out.append((name, "", "file"))
            return sorted(out)


class FileSession:
    """The requests of one served connection: gpl.bp/apisrvr's labels vb.account .. vb.revision, each handler naming its label.  dispatch()
    returns (reply error field, STATUS, reply data); the error field is SV_OK, SV_ELSE (the ELSE clause), SV_LOCKED, SV_ERROR (no data:
    the text comes with request 2, which returns error_msg) or SV_ON_ERROR (the data is the abort message)."""

    def __init__(self, server, conn, userno, user, cfg, files_only, write_ok=False):
        self.server = server
        self.store = server.store
        self.cfg = cfg
        self.conn = conn
        self.userno = userno
        self.user = user
        self.files_only = files_only
        self.write_ok = bool(write_ok)  # apisrvr's files.write: the login is also in the Linux group sdfileswrite (read at login; only a files-only login is gated by it)
        self.slots = []                 # slots[fno - 1] is the FakeFile open as file number fno, or None (apisrvr's files() array)
        self.lastid = {}                # the id of the last record read through each file number (FILEINFO 1012)
        self.lists = [None] * 12        # select lists 0 to 10 and the internal 11: [ids, position] or None
        self.marks = {}                 # fno -> mark mapping state set by request 46
        self.error_msg = ""             # apisrvr's error.msg: what request 2 returns
        self.entered = False            # apisrvr's master.login.done: true once request 3 has succeeded
        self.account = None
        self.requests = []              # every request type received after the login, in order
        self.refused = []               # the types the files-only gate refused
        self.injected = []              # (type, "no_reply" | "fail") for faults this session injected
        self.fail_counts = {}
        self.type_counts = {}           # request type -> how many of that type this session has sent (drop_before / drop_after count these)
        self.taken = {}                 # file number -> {(lock name, lock id)}: the record locks taken through that slot (CLOSE lets them go)
        self.flslot = {}                # lock name -> the file number that TOOK this session's file lock (the kernel's fptr->fvar_index): CLOSE of that number lets it go (S.72)
        self.nreq = 0
        self.done = False
        self.closed = False
        self.err = SV_OK
        self.st = 0
        self.abort_msg = ""
        self.cur_fno = 0

    # ---- the gate: gpl.bp/apifilesok ---------------------------------------------------------------------------------------------
    def allowed(self, ptype, write_ok=None):
        """!apifilesok(action, entered, writeok): 3 (set account) once only, the table for the rest, anything else (47 and 48 included) refused, and the change set
        (FILES_CHANGE) only when the login is also in sdfileswrite (write_ok; the session's own when not given)."""
        if write_ok is None:
            write_ok = self.write_ok
        if ptype == R_ACCOUNT:
            return not self.entered
        if ptype not in FILES_OK:
            return False
        return write_ok or ptype not in FILES_CHANGE

    def refusal(self, ptype):
        """The ON ERROR text apisrvr gives a request the gate refuses: 11521 when the write group is all that was missing (the same request with it would be
        allowed), 11480 otherwise."""
        if not self.write_ok and self.allowed(ptype, True):
            return msg(11521, ptype)
        return msg(11480, ptype)

    # ---- helpers -----------------------------------------------------------------------------------------------------------------
    def _fail(self, text):
        """server.error = SV$ERROR; error.msg = text."""
        self.err = SV_ERROR
        self.error_msg = text
        return ""

    def _file(self, data):
        """apisrvr check.file: the FakeFile for the file number in the first two bytes, else SV$ERROR 5268."""
        fno = _short(data, 0)
        if fno < 1 or fno > len(self.slots) or self.slots[fno - 1] is None:
            return self._fail(msg(5268)) or None
        self.cur_fno = fno
        return self.slots[fno - 1]

    def _list(self, listno):
        """apisrvr check.list: True when listno is 0 to 10, else SV$ERROR 5269."""
        if listno < 0 or listno > 10:
            self._fail(msg(5269))
            return False
        return True

    def _lock(self, f, rid, update, wait, as_abort=False):
        """The lock a locking read takes before it reads (op_dio3.c: the lock first, so a record that is not there is locked all the same).
        True when held.  Not waiting: the LOCKED clause with STATUS() the holder's user number (op_lock.c / op_dio3.c: process.status =
        lock_record()).  Waiting: the real server waits for ever; this one gives up after cfg lock_wait seconds (module text, 3).
        cfg maxrlock: a NEW lock (the session holds nothing on the record yet) when the session already holds that many is an ON ERROR
        reply before the lock table is looked at.  AS THE REAL SERVER ANSWERS (REAL_ON_ERROR, measured 19 Oct 26): a locking READ has an ON ERROR clause, so it is STATUS()
        +3060 and no text; request 30 (as_abort) has none, so it aborts: STATUS() 0 and the kernel's text, message 11162 with the program and line."""
        limit = self.cfg["maxrlock"]
        if limit is not None and not self.store.holds(f, rid, self.userno) and self.store.count_locks(self.userno) >= limit:
            self.err = SV_ON_ERROR
            if as_abort:
                self.st = 0
                self.abort_msg = abort_text(msg(11162), 2077)
            else:
                self.st = ER_MAXRLOCK
                self.abort_msg = ""
            return False
        if wait:
            h = self.store.lock_wait(f, rid, update, self.userno, self.cfg["lock_wait"])
        else:
            h = self.store.lock_try(f, rid, update, self.userno)
        if h == 0:
            self.taken.setdefault(self.cur_fno, set()).add((f.lockname, f.lockid(rid)))
            return True
        if wait:
            self.err = SV_ON_ERROR
            self.abort_msg = "netfake: gave up after %s seconds waiting for the lock on %s held by user %d" % (self.cfg["lock_wait"], rid, h)
            self.server.note(self.abort_msg)
        else:
            self.err = SV_LOCKED
            self.st = h
        return False

    def _unlock(self, f, rid):
        """A plain WRITE or DELETE lets go of the session's lock on the id (read or update), whichever slot took it: unlock_record() goes by
        file and id."""
        self.store.release_one(f, rid, self.userno)
        key = (f.lockname, f.lockid(rid))
        for s in self.taken.values():
            s.discard(key)

    def _fail_on_error(self, status, text):
        """The ON ERROR reply: server.error = SV$ON.ERROR, the abort message, and the (negative) STATUS() of the statement."""
        self.err = SV_ON_ERROR
        self.st = status
        self.abort_msg = text
        return ""

    def _change_gate(self, f, rid=None):
        """What stands between a changing request and the file, in the order of the real server: check.edit (the session's edit gates, by
        the pathname; an empty path is 11410), then the statement itself - the file read only for the OS user (STATUS() +3018, no text; CLEARFILE has no ON ERROR clause and
        aborts: STATUS() 0 and the kernel's text), a record id that is not valid (+3000, no text: empty, over 63 bytes, or holding one of the five marks, bytes 251 to 255 -
        the real server accepts 248 to 250, measured by sandbox-req29.py section G), and MUSTLOCK (-3023: no update lock held on the record; from op_dio3.c, not
        measured on a real server).  The signs and texts are REAL_ON_ERROR's.  rid None is CLEARFILE.  True when the change may go on; otherwise the reply is set."""
        if not f.path:
            self._fail(msg(11410))
            return False
        k = f.edit_kind()
        if k and KIND_NAMES[k] not in self.cfg["edit_allow"]:
            self._fail(msg(11404 + k))
            return False
        if f.vocname in self.cfg["readonly"] or f.name in self.cfg["readonly"]:
            if rid is None:
                self._fail_on_error(0, abort_text("CLEARFILE on read-only file", 2099))
            else:
                self._fail_on_error(ER_RDONLY, "")
            return False
        if rid is None:
            return True
        if rid == "" or len(rid) > MAX_ID or any(251 <= ord(ch) <= 255 for ch in rid):
            self._fail_on_error(ER_IID, "")
            return False
        if self.cfg["must_lock"] and not self.store.holds_update(f, rid, self.userno):
            self._fail_on_error(-ER_NOLOCK, "")
            return False
        return True

    def _found(self, f, rid, rec):
        if rec is None:
            self.err = SV_ELSE
            self.st = ER_RNF
            return ""
        self.lastid[self.cur_fno] = f.find(rid)
        return rec

    # ---- the dispatch ------------------------------------------------------------------------------------------------------------
    def dispatch(self, ptype, data):
        self.err, self.st, self.abort_msg = SV_OK, 0, ""
        h = self.HANDLERS.get(ptype)
        if h is None:
            if ptype in NOT_BUILT:
                self.server.note("request %d is not built in netfake" % ptype)
                self._fail("netfake: request %d is not implemented" % ptype)
            else:
                self._fail("Illegal action code (%d)" % ptype)         # apisrvr vb.illegal.action
            return self.err, self.st, ""
        resp = h(self, data)
        if self.err == SV_OK and ptype in STATUS_REQUESTS:
            self.st = self.cfg["success_status"]          # apisrvr sends whatever the last statement left in STATUS(); a client must not read it
        if self.err == SV_ON_ERROR:
            resp = self.abort_msg            # apisrvr return.status.set: response = @abort.message
        elif self.err == SV_ERROR:
            resp = ""
        return self.err, self.st, resp

    # ---- the handlers ------------------------------------------------------------------------------------------------------------
    def r_quit(self, data):
        """vb.quit: done = true; the reply is still written."""
        self.done = True
        return ""

    def r_geterror(self, data):
        """vb.geterror: response = error.msg."""
        return self.error_msg

    def r_account(self, data):
        """vb.account: an account name is lower cased unless it is a path (it holds a '/'); 1 to 32 characters (5037); one the server does not
        know, or the user may not enter, is 10003 whichever it is.  The first success is "entered": the files-only gate allows request 3 once."""
        name = data.decode("latin-1")
        if "/" not in name:
            name = _lower(name)
        if len(name) < 1 or len(name) > 32:
            return self._fail(msg(5037))
        accts = self.store.accounts
        if accts is not None and name not in accts:
            return self._fail(msg(10003))
        self.account = name
        self.entered = True
        return ""

    def r_open(self, data):
        """vb.open: the file number (a short) of the lowest free slot of the files() array; "dict <name>" opens the dictionary; a file that is
        not there is the ELSE clause with STATUS() ER$FNF, an empty name ER$NAM; the access-disabled switch is 5262 as an ON ERROR."""
        if self.cfg["no_file_access"]:
            self.err = SV_ON_ERROR
            self.abort_msg = msg(5262)
            return ""
        # 18 Oct 26: the real rule, apisrvr's vb.open: a name whose first five characters are the word dict (any case) and a space is OPEN 'DICT', trim(the rest);
        # any other name is opened as it stands (OPEN cmnd), so "wf dict" is a file of that name, not wf
        text = data.decode("latin-1")
        want_dict = text[:5].upper() == "DICT "
        base = text[5:].strip() if want_dict else text.strip()
        if base == "":
            self.err, self.st = SV_ELSE, ER_NAM
            return ""
        f = self.store.file(base)
        if f is None:
            self.err, self.st = SV_ELSE, ER_FNF
            return ""
        if want_dict:
            f = f.dictionary()
        for i, s in enumerate(self.slots):
            if s is None:
                self.slots[i] = f
                return struct.pack("<h", i + 1).decode("latin-1")
        self.slots.append(f)
        return struct.pack("<h", len(self.slots)).decode("latin-1")

    def r_close(self, data):
        """vb.close: check.file, then the slot is free for the next open."""
        f = self._file(data)
        if f is not None:
            for name, lid in self.taken.pop(self.cur_fno, ()):          # slice 3e: the locks taken through THIS slot go with it
                self.store.release_key(name, lid, self.userno)
            if self.flslot.get(f.lockname) == self.cur_fno:             # S.72, op_dio1.c dio_close(): the file lock goes with the file number that took it, and only with that one
                del self.flslot[f.lockname]
                self.store.filelock_release(f.lockname, self.userno)
            self.slots[self.cur_fno - 1] = None
        return ""

    def _read(self, data, update=None, wait=False):
        f = self._file(data)
        if f is None:
            return ""
        rid = _rid(data, 2)
        if rid == "":
            self.err, self.st = SV_ELSE, ER_IID          # op_dio3.c: an empty id is ER$IID and the ELSE clause
            return ""
        if update is not None and not self._lock(f, rid, update, wait):
            return ""
        return self._found(f, rid, f.get(rid))

    def r_read(self, data):
        """vb.read: READ; not found is the ELSE clause with STATUS() ER$RNF (3006)."""
        return self._read(data)

    def r_readl(self, data):
        """vb.readl: READL with a LOCKED clause (no waiting)."""
        return self._read(data, False, False)

    def r_readlw(self, data):
        """vb.readlw: READL with no LOCKED clause: it waits."""
        return self._read(data, False, True)

    def r_readu(self, data):
        """vb.readu: READU with a LOCKED clause."""
        return self._read(data, True, False)

    def r_readuw(self, data):
        """vb.readuw: READU, waiting."""
        return self._read(data, True, True)

    def r_select(self, data):
        """vb.select: check.file, check.list, then SELECT file TO listno.  Replaces the list."""
        f = self._file(data)
        if f is None:
            return ""
        listno = _short(data, 2)
        if not self._list(listno):
            return ""
        self.lists[listno] = [list(f.records), 0]
        return ""

    def r_readnext(self, data):
        """vb.readnext: the next id of the list; the end of the list (or no list) is the ELSE clause."""
        listno = _short(data, 0)
        if not self._list(listno):
            return ""
        lst = self.lists[listno]
        if lst is None or lst[1] >= len(lst[0]):
            self.lists[listno] = None
            self.err = SV_ELSE
            return ""
        rid = lst[0][lst[1]]
        lst[1] += 1
        return rid

    def r_clearselect(self, data):
        """vb.clearselect."""
        listno = _short(data, 0)
        if self._list(listno):
            self.lists[listno] = None
        return ""

    def r_readlist(self, data):
        """vb.readlist: what is left of the list, ids separated by field marks, and the list is used up; no list is the null string."""
        listno = _short(data, 0)
        if not self._list(listno):
            return ""
        lst = self.lists[listno]
        self.lists[listno] = None
        return "" if lst is None else FM.join(lst[0][lst[1]:])

    def r_release(self, data):
        """vb.release: file number 0 releases every lock of the session; an empty id every lock on the file; else the one record's.  Since S.72 (20 Oct 26; gplsrc/op_lock.c
        unlock_record(), which RLSALL and RLSFILE call): file number 0 lets go of every FILE lock of the session too, and an empty id lets go of the file lock if the
        file number it is sent through is the one that TOOK it; one record's id never touches a file lock."""
        fno = _short(data, 0)
        f = None
        if fno:
            f = self._file(data)
            if f is None:
                return ""
        rid = _rid(data, 2)
        if fno == 0:
            self.store.release_all(self.userno)
            self.store.release_filelocks(self.userno)
            self.taken.clear()
            self.flslot.clear()
        elif rid == "":
            self.store.release_file(f, self.userno)
            for s in self.taken.values():
                s.difference_update([k for k in s if k[0] == f.lockname])
            if self.flslot.get(f.lockname) == fno:
                del self.flslot[f.lockname]
                self.store.filelock_release(f.lockname, self.userno)
        else:
            self._unlock(f, rid)
        return ""

    # ---- 18 Oct 26, S.65 slice 3e: the changing and locking requests ------------------------------------------------------------
    def _write(self, data, keep):
        """vb.write / vb.writeu: fno (short), id length (short), the id (no padding), the record is the rest.  check.edit, then the statement."""
        f = self._file(data)
        if f is None:
            return ""
        n = max(_short(data, 2), 0)
        rid = data[4:4 + n].decode("latin-1")
        rec = data[4 + n:].decode("latin-1")
        if not self._change_gate(f, rid):
            return ""
        self.store.write_rec(f, rid, rec)
        if not keep:
            self._unlock(f, rid)
        return ""

    def _delete(self, data, keep):
        """vb.delete / vb.deleteu: fno (short), the id is the rest (99 bytes at most).  A record that is not there is a success."""
        f = self._file(data)
        if f is None:
            return ""
        rid = _rid(data, 2)
        if not self._change_gate(f, rid):
            return ""
        self.store.delete_rec(f, rid)
        if not keep:
            self._unlock(f, rid)
        return ""

    def r_write(self, data):
        return self._write(data, False)

    def r_writeu(self, data):
        return self._write(data, True)

    def r_delete(self, data):
        return self._delete(data, False)

    def r_deleteu(self, data):
        return self._delete(data, True)

    def r_clearfile(self, data):
        """vb.clearfile: check.file, check.edit, then CLEARFILE: waits (here: cfg lock_wait seconds) while ANOTHER user holds the file lock,
        then every record goes.  The lock table is not touched."""
        f = self._file(data)
        if f is None:
            return ""
        if not self._change_gate(f):
            return ""
        h = self.store.filelock_wait(f, self.userno, self.cfg["lock_wait"])
        if h:
            self.err = SV_ON_ERROR
            self.abort_msg = "netfake: gave up after %s seconds waiting for the file lock on %s held by user %d" % (self.cfg["lock_wait"], f.vocname, h)
            self.server.note(self.abort_msg)
            return ""
        self.store.clear_file(f)
        return ""

    def r_lockrecord(self, data):
        """vb.lock.record: fno (short), flags (short: 1 = update lock, 2 = no wait), the id.  0 and 1 wait (here: lock_wait seconds, then an ON
        ERROR reply), 2 and 3 are the LOCKED clause: SV$LOCKED with STATUS() the holder's user number.  Any other flags value does nothing
        and succeeds, as the begin case of apisrvr has no branch for it."""
        f = self._file(data)
        if f is None:
            return ""
        flags = _short(data, 2)
        rid = _rid(data, 4)
        if flags not in (0, 1, 2, 3):
            return ""
        if rid == "":
            return self._fail_on_error(0, "netfake: null record id")
        self._lock(f, rid, bool(flags & 1), not (flags & 2), as_abort=True)
        return ""

    def r_filelock(self, data):
        """vb.filelock (20 Oct 26, S.72): fno (short), wait (short).  wait 0 is FILELOCK with a LOCKED clause: SV$LOCKED with STATUS() the user number in the way - the holder of another
        user's file lock, else the owner of a record lock in the file held by ANOTHER user (op_lock.c op_filelock()); a user who holds the file lock already succeeds.  A wait that
        is not 0 waits (here: lock_wait seconds, then the ON ERROR reply the other waits give; the real server waits for ever).  The file number that TAKES the lock is
        remembered (the kernel's fptr->fvar_index): a second FILELOCK of a lock the user already holds, through any number, leaves the owner as it was.  The success STATUS() is
        cfg success_status (STATUS_REQUESTS)."""
        f = self._file(data)
        if f is None:
            return ""
        wait = _short(data, 2)
        mine = self.store.filelock_holder(f) == self.userno
        if wait:
            h = self.store.filelock_acquire(f, self.userno, self.cfg["lock_wait"])
        else:
            h = self.store.filelock_try(f, self.userno)
        if h == 0:
            if not mine:
                self.flslot[f.lockname] = self.cur_fno
            return ""
        if wait:
            self.err = SV_ON_ERROR
            self.abort_msg = "netfake: gave up after %s seconds waiting for the file lock on %s held by user %d" % (self.cfg["lock_wait"], f.vocname, h)
            self.server.note(self.abort_msg)
        else:
            self.err = SV_LOCKED
            self.st = h
        return ""

    def r_fileunlock(self, data):
        """vb.fileunlock (20 Oct 26, S.72): fno (short).  SV$OK with STATUS() 0 when the session held the file lock (now let go, waiters woken), ER$LCK 3011 when another user holds
        it (left held), ER$NLK 3012 when nobody does (op_lock.c op_flunlock()).  The STATUS() is the answer: success_status never replaces it.  It goes by the USER, not the file
        number, so any number of the file may unlock."""
        f = self._file(data)
        if f is None:
            return ""
        self.st = self.store.filelock_release(f.lockname, self.userno)
        if self.st == 0:
            self.flslot.pop(f.lockname, None)
        return ""

    def r_recordlocked(self, data):
        """vb.recordlocked: RECORDLOCKED() as four bytes (the signed code as an unsigned long), STATUS() the owner's user number."""
        f = self._file(data)
        if f is None:
            return ""
        code, self.st = self.store.recordlocked(f, _rid(data, 2), self.userno)
        return struct.pack("<I", code & 0xFFFFFFFF).decode("latin-1")

    def r_selectlist(self, data):
        """vb.selectlist: SELECT file TO 11, READLIST: every id, field marks between."""
        f = self._file(data)
        if f is None:
            return ""
        return FM.join(f.records)

    def r_fileinfo(self, data):
        """vb.fileinfo: FILEINFO(file, key) with the key a long, cut to a signed 16 bits as op_dio2.c does; the answer is the value as text.
        A key op_dio2.c does not know is an abort, 1010 (the ON ERROR reply).  Modelled: 0 1 2 3 1001 1008 1009 1012 1014 1015; every other
        known key is 0 unless FakeFile.info gives it."""
        f = self._file(data)
        if f is None:
            return ""
        key = struct.unpack("<h", struct.pack("<H", _long(data, 2) & 0xFFFF))[0]
        if key not in FL_KNOWN:
            self.err = SV_ON_ERROR
            self.abort_msg = msg(1010)
            return ""
        if key in f.info:
            return str(f.info[key])
        if key == 0:
            return "1"
        if key == 1:
            return f.vocname
        if key == 2:
            return f.path
        if key == 3:
            return str(f.ftype)
        if key == 1008:
            return "1" if f.nocase else "0"
        if key == 1009:
            return str(f.fileid)
        if key == 1012:
            return self.lastid.get(self.cur_fno, "")
        if key == 1014:
            return ("1" if self.marks.get(self.cur_fno, True) else "0") if f.ftype == FL_TYPE_DIR else "0"
        if key == 1015:
            return str(len(f.records)) if f.ftype == FL_TYPE_DH else "-1"
        return "0"

    def r_readv(self, data):
        """vb.readv: flags 0 READV, 1 READVU, 2 READVL (the last two wait), 5 and 6 the same with a LOCKED clause; any other flag does
        nothing and answers success with no data, as the begin case of apisrvr does.  The answer is rec<field>: field 0 or less is null."""
        f = self._file(data)
        if f is None:
            return ""
        flags = _short(data, 2)
        if self.files_only and not self.write_ok and flags != 0:
            # 18 Oct 26, S.65 write group: apisrvr's vb.readv, after check.file: a locking form (any nonzero flag) is a change of state, refused as 7 to 10 are
            self.refused.append(R_READV)
            self.err, self.abort_msg = SV_ON_ERROR, msg(11521, R_READV)
            return ""
        field = _long(data, 4)
        rid = _rid(data, 8)
        modes = {0: None, 1: (True, True), 2: (False, True), 5: (True, False), 6: (False, False)}
        if flags not in modes:
            return ""
        if rid == "":
            self.err, self.st = SV_ELSE, ER_IID
            return ""
        if modes[flags] is not None and not self._lock(f, rid, modes[flags][0], modes[flags][1]):
            return ""
        rec = self._found(f, rid, f.get(rid))
        if self.err != SV_OK:
            return ""
        parts = rec.split(FM)
        return parts[field - 1] if 1 <= field <= len(parts) else ""

    def r_markmapping(self, data):
        """vb.mark.mapping: check.file; the state is kept and changes FILEINFO 1014 for a directory file; ignored for any other (op_mapmarks)."""
        f = self._file(data)
        if f is not None:
            self.marks[self.cur_fno] = _short(data, 2) != 0
        return ""

    def r_revision(self, data):
        """vb.revision: response = system(1012)."""
        return self.server.revision

    HANDLERS = {R_QUIT: r_quit, R_GETERROR: r_geterror, R_ACCOUNT: r_account, R_OPEN: r_open, R_CLOSE: r_close, R_READ: r_read,
                R_READL: r_readl, R_READLW: r_readlw, R_READU: r_readu, R_READUW: r_readuw, R_SELECT: r_select, R_READNEXT: r_readnext,
                R_CLEARSELECT: r_clearselect, R_READLIST: r_readlist, R_RELEASE: r_release, R_RECORDLOCKED: r_recordlocked,
                R_SELECTLIST: r_selectlist, R_FILEINFO: r_fileinfo, R_READV: r_readv, R_MARKMAPPING: r_markmapping, R_REVISION: r_revision,
                R_WRITE: r_write, R_WRITEU: r_writeu, R_DELETE: r_delete, R_DELETEU: r_deleteu, R_LOCKRECORD: r_lockrecord,
                R_CLEARFILE: r_clearfile, R_FILELOCK: r_filelock, R_FILEUNLOCK: r_fileunlock}


class FakeServer(threading.Thread):
    """See the module text.  Users: add_user(), add_user_keys().  Behaviour per connection: configure() - every call starts from the defaults,
    so a row names only what it changes.  The store, the lock table and the account list: self.store (FakeStore).  What a served connection
    did: self.sessions (FileSession objects: userno, requests, refused, injected, account, files_only, closed)."""

    DEFAULTS = {
        "ack": True,              # send the Ack byte after the handshake
        "close_after": None,      # 'handshake' (before the Ack) | 'ack' | 'first' (after reading client-first) | 'final' | None
        "stall_first": None,      # N seconds: the Ack is sent and client-first read, then NOTHING is sent; the connection is held N seconds or until the client closes it (19 Oct 26, finish 2)
        "nonce": "extend",        # 'extend' | 'wrong' (does not start with the client's) | 'same' (the client's, nothing added)
        "offer_iter": None,       # iteration count offered (and used) instead of the user's
        "iter_text": None,        # i= text instead of a number (the derivation still uses the user's count)
        "salt_text": None,        # s= text instead of the user's salt
        "first_raw": None,        # the whole server-first message, instead of r=,s=,i=
        "first_error": None,      # (error field, text): answer client-first with an error
        "final_error": None,      # (error field, text): answer client-final with an error without looking at the proof
        "bad_v": False,           # a wrong ServerSignature
        "no_v": False,            # an answer that is not v=
        # ---- 17 Oct 26 S.65 slice 3a: the file requests (module text) ----
        "files": False,           # serve the requests after a good login (False: record them and say nothing, as before)
        "files_only": False,      # the SDNet login: only gpl.bp/apifilesok's requests are dispatched, the rest get message 11480
        "write_group": False,     # 18 Oct 26, S.65 write group: the files-only login is ALSO in the Linux group sdfileswrite, so it may change files and take locks
                                  # (apifilesok's third argument).  False is the real default of a files-only login: the change requests get message 11521.
        "no_file_access": False,  # request 4 (open) answers 5262 "File access is disabled" (config SDCLIENT / the SDNet mark of apisrvr)
        "idle": 20.0,             # seconds a served connection may be silent before the server closes it
        "lock_wait": 3.0,         # seconds a waiting lock request (8, 10, 41 with flags 1 or 2) waits before it gives up with an ON ERROR reply
        "close_after_requests": None,   # N: close the connection after replying to the Nth request of the session
        "drop_request": None,     # N: read the Nth request of the session and close the connection without replying
        "delay": None,            # seconds before each reply: a number, or {request type: seconds, "*": seconds for any other}
        "no_reply": (),           # request types that are read, recorded and never answered (the client's timeout is the test)
        "fail": None,             # {request type or "*": (error field, text) or (error field, text, count)}: answer with that error and do not
                                  # dispatch; count = the first COUNT times only.  Error field SV_ERROR makes text the answer to request 2.
        # ---- 18 Oct 26 S.65 slice 3e: writes, record locks and CLEARFILE (module text) ----
        "success_status": 0,      # the STATUS() sent with every successful 15 to 19, 30 and 31 reply (a row sets it non-zero to prove the client never reads it)
        "must_lock": False,       # 16 to 19: no update lock held on the record -> ON ERROR, STATUS() -3023, nothing changed (the server's MUSTLOCK=1)
        "readonly": (),           # VOC names (lower case) of files 16 to 19 and 31 refuse: ON ERROR, STATUS() +3018 and no text (31, which aborts: STATUS() 0 and the kernel's text) - REAL_ON_ERROR
        "edit_allow": frozenset(),  # the edit gates the session has: any of "voc" "dict" "prog".  Empty is the real default of a files-only login.
        "maxrlock": None,         # N: a session holding N record locks that asks for another NEW one gets ON ERROR - STATUS() +3060 for a locking read, STATUS() 0 and the kernel's text for 30
        "drop_before": None,      # {request type: n}: the n-th request of that type is read and the connection closed WITHOUT executing or replying
        "drop_after": None,       # {request type: n}: the n-th is executed (the store changes) and the connection closed WITHOUT replying
        # ---- 19 Oct 26 K8c ----
        "bad_length": None,       # {request type: N}: the request is executed, and the reply is its 10 byte HEADER ALONE with the total length field N (any 32 bit value) and then silence: the
                                  # connection is held open for bad_length_hold seconds or until the client closes it.  A client with no ceiling waits for the body (its own timeout); one with a
                                  # ceiling, or that tests for a length below 10, drops the connection at once, which is what the rows time.
        "bad_length_hold": 45.0,
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
        self.busy = 0                   # connections being dealt with (a count since 17 Oct 26; every user tests it for truth only)
        self.store = FakeStore()
        self.sessions = []              # FileSession of every served connection, in order
        self.live = set()               # accepted sockets still open, so that shutdown() can close them
        self.userno_base = USERNO_BASE
        self.revision = "L1.1-3"        # what request 49 answers (system(1012))
        self.cert = cert
        self._pin = None
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
    def add_user(self, name, password, salt=None, iterations=4096, files_only=False, write_group=False):
        """A user the server knows.  Returns the salt as base64 (the one in s=).  files_only=True makes every login of this user the SDNet
        one (the sdfiles route) whatever the connection's configuration says; write_group=True puts the user in the group sdfileswrite as well
        (18 Oct 26, S.65 write group), whatever the connection's configuration says."""
        salt = salt if salt is not None else os.urandom(16)
        with self.lock:
            self.users[name] = {"password": password, "salt": salt, "iterations": int(iterations), "files_only": bool(files_only),
                                "write_group": bool(write_group)}
        return b64(salt)

    def add_user_keys(self, name, salt_b64, iterations, stored_key_b64, server_key_b64, files_only=False, write_group=False):
        """A user the server knows by what $cred holds and not by the password: the salt, the iteration count, StoredKey and ServerKey (all
        base64 as the credential file keeps them).  The exchange on the wire is the one a password user has; a client that proves itself
        from ClientKey (SHA-256 of which is StoredKey) is accepted, a client with any other key is not.  The iteration count the server
        OFFERS (cfg offer_iter) cannot change the verification of such a user: there is no password to derive from again."""
        with self.lock:
            self.users[name] = {"password": None, "salt": base64.b64decode(salt_b64), "iterations": int(iterations),
                                "stored_key": base64.b64decode(stored_key_b64), "server_key": base64.b64decode(server_key_b64),
                                "files_only": bool(files_only), "write_group": bool(write_group)}

    @property
    def pin(self):
        """The pin of this server's certificate as set.server wants it: SHA-256 of the SubjectPublicKeyInfo, 64 lower case hex digits.  Made
        with the openssl command line (x509 -pubkey | pkey -pubin -outform DER) and hashlib, as sandbox-net.py makes it."""
        if self._pin is None:
            self._pin = spki_pin(self.cert)
        return self._pin

    def configure(self, **kw):
        bad = [k for k in kw if k not in self.DEFAULTS]
        if bad:
            raise KeyError("netfake: unknown setting %r" % bad)
        with self.lock:
            self.cfg = dict(self.DEFAULTS)
            self.cfg.update(kw)

    def mark(self):
        with self.lock:
            return (self.conns, self.handshakes, len(self.packets), self.app_bytes, self.scram_ok, self.scram_bad, len(self.exchanges), len(self.errors),
                    len(self.sessions))

    def delta(self, m):
        """What happened since MARK: connection and handshake counts, the TYPES of the packets received, the application bytes, proofs that
        verified and that did not, the exchanges, and what this server found wrong in the client's messages; and, since slice 3a, the
        served sessions begun since (FileSession objects)."""
        with self.lock:
            return {"conns": self.conns - m[0], "handshakes": self.handshakes - m[1], "types": [p[1] for p in self.packets[m[2]:]],
                    "packets": list(self.packets[m[2]:]), "app_bytes": self.app_bytes - m[3], "ok": self.scram_ok - m[4],
                    "bad": self.scram_bad - m[5], "exchanges": list(self.exchanges[m[6]:]), "errors": list(self.errors[m[7]:]),
                    "sessions": list(self.sessions[m[8]:])}

    def settle(self, quiet=0.7, limit=8.0):
        """Wait until a connection the client has just made has been accepted and dealt with (a 'no connection' row waits the same time)."""
        time.sleep(quiet)
        t0 = time.time()
        while self.busy and time.time() - t0 < limit:
            time.sleep(0.05)

    def shutdown(self):
        self.ended.set()
        self.join(timeout=5)
        with self.lock:
            live = list(self.live)
        for c in live:                  # a served connection has a thread of its own: end it
            try:
                c.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    # ---- the server ------------------------------------------------------------------------------------------------------------
    def run(self):
        while not self.ended.is_set() and time.time() < self.deadline:
            try:
                conn, _addr = self.lsock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            with self.lock:
                self.busy += 1
                self.conns += 1
                n = self.conns
                cfg = dict(self.cfg)
                self.live.add(conn)
            if cfg["files"]:
                # a served connection lives as long as its client does, and the lock rows need two of them at once
                threading.Thread(target=self.one_connection, args=(conn, n, cfg), daemon=True).start()
            else:
                self.one_connection(conn, n, cfg)
        try:
            self.lsock.close()
        except OSError:
            pass

    def one_connection(self, conn, n, cfg):
        try:
            conn.settimeout(10)
            self.handle(conn, n, cfg)
        except Exception:               # a client that goes away in the middle of an exchange is not this server's concern
            pass
        finally:
            try:
                conn.close()
            except OSError:
                pass
            with self.lock:
                self.busy -= 1
                self.live.discard(conn)

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
            if length < 6 or length > MAX_PACKET:
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
    def reply(tls, data, err=SV_OK, status=0):
        data = data.encode("latin-1") if isinstance(data, str) else data
        tls.sendall(struct.pack("<IHI", 10 + len(data), err, status & 0xFFFFFFFF) + data)

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
            if cfg["stall_first"]:
                # 19 Oct 26 (finish 2): the Ack went, client-first was read, and the reply never comes.  The connection is held for stall_first seconds, or until the client closes it
                # (a recv with a short timeout, so that the fake lets go as soon as the client gives up and the rows can say that no socket is left open)
                end = time.time() + cfg["stall_first"]
                tls.settimeout(0.2)
                while time.time() < end:
                    try:
                        if tls.recv(1) == b"":
                            break
                    except socket.timeout:
                        continue
                    except (OSError, ssl.SSLError):
                        break
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
                  "cbind": None, "proof": None, "cfinal_bare": None, "authmsg": None, "verified": None, "iterations": iters, "final_text": text,
                  "conn": n}
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
            if rec["password"] is None:         # a user known by keys alone (add_user_keys): nothing to derive from
                keys = {"stored_key": rec["stored_key"], "server_key": rec["server_key"]}
            else:
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
            ses = None
            if cfg["files"]:
                # registered BEFORE the reply that tells the client it is in, so that a test which looks at self.sessions after its login
                # has returned always finds the session (and its user number)
                ses = FileSession(self, n, self.userno_base + n, user, cfg, bool(cfg["files_only"] or rec.get("files_only")),
                                  bool(cfg["write_group"] or rec.get("write_group")))
                with self.lock:
                    self.sessions.append(ses)
            self.reply(tls, ("x=" if cfg["no_v"] else "v=") + b64(v))
            if ses is not None:
                self.serve(tls, n, ses)
            else:
                # anything more the client sends is recorded (a client that has what it came for closes at once)
                while self.read_packet(tls, n) is not None:
                    pass
        finally:
            try:
                tls.close()
            except (OSError, ssl.SSLError):
                pass

    # ---- the served connection ---------------------------------------------------------------------------------------------------
    def serve(self, tls, n, ses):
        """apisrvr's main loop for one logged-in connection.  Order for each request: read and record it; drop_request; drop_before; no_reply;
        the files-only gate (apisrvr: after the logged-in test and before the dispatch, so nothing goes round it); fail; the dispatch;
        drop_after (the request has been executed, the connection closes without a reply); the delay; the reply; then quit and
        close_after_requests end the connection.  The session's locks are let go when it ends, as a process's are."""
        cfg = ses.cfg
        tls.settimeout(cfg["idle"])
        try:
            while not self.ended.is_set():
                pk = self.read_packet(tls, n)
                if pk is None:
                    break
                ptype, data = pk
                ses.nreq += 1
                ses.requests.append(ptype)
                ses.type_counts[ptype] = ses.type_counts.get(ptype, 0) + 1
                if cfg["drop_request"] == ses.nreq:
                    break
                if (cfg["drop_before"] or {}).get(ptype) == ses.type_counts[ptype]:
                    ses.injected.append((ptype, "drop_before"))
                    break
                if ptype in cfg["no_reply"]:
                    ses.injected.append((ptype, "no_reply"))
                    continue
                if ses.files_only and not ses.allowed(ptype):
                    ses.refused.append(ptype)
                    # apisrvr: server.error = SV$ON.ERROR, abort.message = sysmsg(11480, action), or sysmsg(11521, action) when the write group is all that was missing
                    res = (SV_ON_ERROR, 0, ses.refusal(ptype))
                else:
                    res = self.injected_fault(ses, ptype)
                    if res is None:
                        res = ses.dispatch(ptype, data)
                if (cfg["drop_after"] or {}).get(ptype) == ses.type_counts[ptype]:
                    ses.injected.append((ptype, "drop_after"))      # the request was executed (the store has changed); the reply is never sent
                    break
                self.pause(cfg, ptype)
                bl = (cfg["bad_length"] or {}).get(ptype)
                if bl is not None:
                    ses.injected.append((ptype, "bad_length"))
                    tls.sendall(struct.pack("<IHI", bl & 0xFFFFFFFF, res[0], res[1] & 0xFFFFFFFF))        # the header only: the length it announces is not the length that follows
                    self.hold_open(tls, cfg["bad_length_hold"])
                    break
                self.reply(tls, res[2], res[0], res[1])
                if ses.done or cfg["close_after_requests"] == ses.nreq:
                    break
        finally:
            ses.closed = True
            self.store.drop_user(ses.userno)

    @staticmethod
    def injected_fault(ses, ptype):
        """The fail setting: (error field, status, data) for a request it covers, else None."""
        spec = ses.cfg["fail"] or {}
        key = ptype if ptype in spec else "*"
        if key not in spec:
            return None
        err, text = spec[key][0], spec[key][1]
        limit = spec[key][2] if len(spec[key]) > 2 else None
        count = ses.fail_counts.get(key, 0)
        if limit is not None and count >= limit:
            return None
        ses.fail_counts[key] = count + 1
        ses.injected.append((ptype, "fail"))
        if err == SV_ERROR:
            ses.error_msg = text
            return (SV_ERROR, 0, "")
        return (err, 0, text)

    @staticmethod
    def hold_open(tls, seconds):
        """Say nothing more and read whatever the client sends until it closes the connection or SECONDS have passed (a client that gives up sends a quit and closes)."""
        end = time.time() + seconds
        tls.settimeout(1.0)
        while time.time() < end:
            try:
                if tls.recv(4096) == b"":
                    return
            except socket.timeout:
                continue
            except (OSError, ssl.SSLError):
                return

    @staticmethod
    def pause(cfg, ptype):
        d = cfg["delay"]
        if isinstance(d, dict):
            d = d.get(ptype, d.get("*"))
        if d:
            time.sleep(d)


def der_tlv(buf, pos):
    """(tag, start of content, end of content) of the ASN.1 DER element at pos."""
    tag = buf[pos]
    ln = buf[pos + 1]
    pos += 2
    if ln & 0x80:
        k = ln & 0x7F
        ln = int.from_bytes(buf[pos:pos + k], "big")
        pos += k
    return tag, pos, pos + ln


def spki_der(cert_der):
    """The SubjectPublicKeyInfo of a DER certificate, header included, found by walking the ASN.1 (Certificate / TBSCertificate): version
    [0] (when present), serial, signature, issuer, validity, subject, subjectPublicKeyInfo."""
    _t, c0, _e = der_tlv(cert_der, 0)                   # Certificate SEQUENCE
    _t, p, _e = der_tlv(cert_der, c0)                   # TBSCertificate SEQUENCE
    items = []
    while len(items) < 6:
        s = p
        tag, a, b = der_tlv(cert_der, p)
        if tag == 0xA0 and not items:                   # the optional version, which is not one of the six that count
            p = b
            continue
        items.append((s, b))
        p = b
    s, e = items[5]                                     # serial, signature, issuer, validity, subject, SPKI: the sixth
    return cert_der[s:e]


def spki_pin(cert_path):
    """The pin set.server takes: SHA-256 of the certificate's SubjectPublicKeyInfo as 64 lower case hex digits, from the openssl command line
    (x509 -pubkey | pkey -pubin -outform DER), as sandbox-net.py makes it."""
    pub = _openssl(["x509", "-in", cert_path, "-pubkey", "-noout"])
    der = _openssl(["pkey", "-pubin", "-outform", "DER"], pub)
    return hashlib.sha256(der).hexdigest()


# ---- the self-test ------------------------------------------------------------------------------------------------------------------

def _openssl(args, data=None):
    p = subprocess.run(["openssl"] + args, input=data, capture_output=True, timeout=60)
    if p.returncode != 0:
        raise RuntimeError("openssl %s failed: %s" % (" ".join(args[:3]), p.stderr.decode(errors="replace")[-300:]))
    return p.stdout


class ApiClient:
    """A minimal API client for the self-test, written from RFC 7677, the packet text above and gpl.bp/sdclient, not from the fake's own code:
    TLS 1.3 to 127.0.0.1, the Ack, login() (SCRAM from a password or from derived keys), then req(type, data) -> (error field, status, data).
    Usable by a test of the BASIC class's behaviour as a reference for what the wire should look like.  It leaves the connection open."""

    def __init__(self, port, timeout=10):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.minimum_version = ssl.TLSVersion.TLSv1_3
        raw = socket.create_connection(("127.0.0.1", port), timeout=10)
        self.tls = ctx.wrap_socket(raw, server_hostname="127.0.0.1")
        self.tls.settimeout(timeout)
        self.peer_der = self.tls.getpeercert(binary_form=True)       # the certificate presented (CERT_NONE still returns it)

    def _rd(self, n):
        buf = b""
        while len(buf) < n:
            c = self.tls.recv(n - len(buf))
            if not c:
                raise EOFError
            buf += c
        return buf

    def send(self, ptype, data):
        d = data.encode("latin-1") if isinstance(data, str) else data
        self.tls.sendall(struct.pack("<IH", len(d) + 6, ptype) + d)

    def recv(self):
        length, err, st = struct.unpack("<IHI", self._rd(10))
        return err, st, (self._rd(length - 10) if length > 10 else b"")

    def req(self, ptype, data=b""):
        """One request and its reply: (error field, status, data as bytes).  EOFError / OSError when the server has gone or says nothing in time."""
        self.send(ptype, data)
        return self.recv()

    def error_text(self):
        """Request 2: the text of the last SV$ERROR."""
        return self.req(R_GETERROR)[2].decode("latin-1")

    def login(self, user, password=None, keys=None):
        """SCRAM-SHA-256 over TLS.  With keys = {"salt": b64, "iterations": n, "client_key": raw, "server_key": raw} no password is used: the
        server's salt and iteration count must equal the stored ones or the client stops with 'stale' and sends nothing more.  Returns
        (outcome, detail): 'ok', 'error' with the server's text, 'closed', 'bad-v', 'stale'."""
        try:
            if self._rd(1) != ACK:
                return "closed", "no ack"
            cnonce = b64(os.urandom(18))
            bare = "n=%s,r=%s" % (user, cnonce)
            self.send(PKT_FIRST, "p=tls-exporter,," + bare)
            err, _st, d = self.recv()
            sfirst = d.decode("latin-1")
            if err != SV_OK:
                return "error", sfirst
            attrs = dict(a.split("=", 1) for a in sfirst.split(","))
            if keys is not None:
                if attrs["s"] != keys["salt"] or attrs["i"] != str(keys["iterations"]):
                    return "stale", sfirst
                ck, sk = keys["client_key"], keys["server_key"]
                stored = hashlib.sha256(ck).digest()
            else:
                k = derive(password, attrs["s"], attrs["i"])
                ck, stored, sk = k["client_key"], k["stored_key"], k["server_key"]
            cfinal_bare = "c=%s,r=%s" % (b64(GS2 + os.urandom(32)), attrs["r"])
            authmsg = bare + "," + sfirst + "," + cfinal_bare
            proof = client_proof(ck, stored, authmsg)
            self.send(PKT_FINAL, cfinal_bare + ",p=" + b64(proof))
            err, _st, d = self.recv()
            final = d.decode("latin-1")
            if err != SV_OK:
                return "error", final
            if final != "v=" + b64(server_signature(sk, authmsg)):
                return "bad-v", final
            return "ok", final
        except (EOFError, OSError):         # a close without close_notify arrives as an SSLError, which is an OSError
            return "closed", "the server closed"

    def close(self):
        try:
            self.tls.close()
        except OSError:
            pass


def _probe(port, user, password, tamper_v=False, keys=None):
    """One login and goodbye, for the self-test: (outcome, detail) of ApiClient.login()."""
    c = ApiClient(port)
    try:
        return c.login(user, password, keys)
    finally:
        c.close()


def _S(n):
    return struct.pack("<h", n)


def _L(n):
    return struct.pack("<I", n & 0xFFFFFFFF)


def _apifilesok_numbers():
    """The request numbers gpl.bp/apifilesok allows, read from its `files.ok := 'N,'` lines (None when the tree is not there)."""
    path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sdsys", "gpl.bp", "apifilesok"))
    try:
        with open(path, encoding="latin-1") as fh:
            text = fh.read()
    except OSError:
        return None
    return frozenset(int(x) for x in re.findall(r"^files\.ok := '(\d+),'", text, re.M))


def _apifilesok_change():
    """The request numbers gpl.bp/apifilesok refuses to a login without the write group, read from its `files.chg := 'N,'` lines (None when the tree is not there)."""
    path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sdsys", "gpl.bp", "apifilesok"))
    try:
        with open(path, encoding="latin-1") as fh:
            text = fh.read()
    except OSError:
        return None
    return frozenset(int(x) for x in re.findall(r"^files\.chg := '(\d+),'", text, re.M))


def selftest_files(srv, cert, row):
    """The slice 3a rows: users from derived keys, every file request against apisrvr's reply formats (read from gpl.bp/apisrvr, each row's
    label names its vb. label), the lock table across two connections, the files-only gate, the fault switches, the pin."""
    FMc, VMc = "\xfe", "\xfd"
    st = srv.store
    rec_c1 = "Smith" + FMc + "100" + VMc + "200" + FMc + "x"
    st.add_file("customers", {"c1": rec_c1, "c2": "Jones" + FMc + "50", "c3": "Brown"}, dict_items={"name": "D" + FMc + "1", "bal": "D" + FMc + "2"},
                path="/data/acct/customers")
    st.add_file("empty")
    st.add_file("mixed", {"ABC": "upper"}, nocase=True)
    st.add_file("dirfile", {"r": "x"}, ftype=FL_TYPE_DIR)
    st.accounts = {"acct"}
    salt_alice = b64(srv.users["alice"]["salt"])
    salt_bob = b64(os.urandom(16))
    kb = derive("pw-bob", salt_bob, 4096)
    srv.add_user_keys("bob", salt_bob, 4096, kb["stored_key_b64"], kb["server_key_b64"])
    keys_bob = {"salt": salt_bob, "iterations": 4096, "client_key": kb["client_key"], "server_key": kb["server_key"]}
    srv.add_user("carol", "pw-carol", files_only=True)

    def login_row(label, want, user, pw=None, keys=None, cfg=None, types=None, ok=None, bad=None):
        srv.configure(**(cfg or {}))
        m = srv.mark()
        res = _probe(srv.port, user, pw, keys=keys)
        srv.settle(quiet=0.3)
        d = srv.delta(m)
        good = res[0] == want and d["errors"] == []
        if types is not None:
            good = good and d["types"] == types
        if ok is not None:
            good = good and d["ok"] == ok and d["bad"] == bad
        row(label, good, "client saw %r, server saw %r" % (res, {x: d[x] for x in ("types", "ok", "bad", "errors")}))

    # ---- A  the login from derived keys -------------------------------------------------------------------------------------------
    login_row("keys alone (add_user_keys): a client proving itself from ClientKey is accepted, the same two packets 47 and 48", "ok", "bob",
              keys=keys_bob, types=[47, 48], ok=1, bad=0)
    ka = derive("pw-one", salt_alice, 4096)
    login_row("a password user is accepted from the keys the password gives (the exchange is the same)", "ok", "alice",
              keys={"salt": salt_alice, "iterations": 4096, "client_key": ka["client_key"], "server_key": ka["server_key"]}, types=[47, 48], ok=1, bad=0)
    login_row("a user known by keys alone is accepted from the password too", "ok", "bob", pw="pw-bob", types=[47, 48], ok=1, bad=0)
    bad_keys = dict(keys_bob, client_key=bytes([keys_bob["client_key"][0] ^ 1]) + keys_bob["client_key"][1:])
    login_row("a wrong ClientKey: the proof does not verify, the server answers an error", "error", "bob", keys=bad_keys, types=[47, 48], ok=0, bad=1)
    login_row("a salt that differs from the stored one: the keys client stops after client-first and sends nothing more", "stale", "bob",
              keys=keys_bob, cfg={"salt_text": "AAAAAAAAAAAAAAAAAAAAAA=="}, types=[47], ok=0, bad=0)
    login_row("an iteration count that differs from the stored one: the same", "stale", "bob", keys=keys_bob, cfg={"offer_iter": 5000},
              types=[47], ok=0, bad=0)
    srv.configure()

    # ---- B  one served connection -------------------------------------------------------------------------------------------------
    def connect(user="alice", pw="pw-one", timeout=5, **cfg):
        srv.configure(files=True, **cfg)
        cl = ApiClient(srv.port, timeout=timeout)
        r = cl.login(user, pw)
        if r[0] != "ok":
            raise RuntimeError("netfake self-test: login of %s gave %r" % (user, r))
        return cl

    def closed_by_server(cl, ptype=R_READ, data=b"\x01\x00c1"):
        try:
            cl.req(ptype, data)
        except (EOFError, OSError):
            return True
        return False

    def wait_closed(ses, limit=4.0):
        t0 = time.time()
        while not ses.closed and time.time() - t0 < limit:
            time.sleep(0.05)
        return ses.closed

    m_b = srv.mark()
    c = connect()
    ses = srv.sessions[-1]
    row("a served connection is registered with a user number before the login reply, and is not files-only", ses.userno == USERNO_BASE + ses.conn and not ses.files_only)
    r = c.req(R_ACCOUNT, "ACCT")
    row("vb.account: the configured name, typed in upper case, is accepted: error 0, no data", r == (0, 0, b""), repr(r))
    r = c.req(R_ACCOUNT, "other")
    row("vb.account: another name is SV$ERROR with no data, and request 2 returns 10003", r == (3, 0, b"") and c.error_text() == msg(10003), repr(r))
    r = c.req(R_ACCOUNT, "x" * 33)
    row("vb.account: 33 characters is 5037", r[0] == 3 and c.error_text() == msg(5037), repr(r))
    r = c.req(R_ACCOUNT, "")
    row("vb.account: no name is 5037", r[0] == 3 and c.error_text() == msg(5037), repr(r))
    r1, r2 = c.req(R_OPEN, "customers"), c.req(R_OPEN, "CUSTOMERS")
    row("vb.open: file numbers are handed out from 1, the name is case blind", r1 == (0, 0, _S(1)) and r2 == (0, 0, _S(2)), repr((r1, r2)))
    r = c.req(R_OPEN, "nosuch")
    row("vb.open: a file that is not there is SV$ELSE with STATUS() ER$FNF 3003 and no data", r == (SV_ELSE, 3003, b""), repr(r))
    r = c.req(R_OPEN, "")
    row("vb.open: no name is SV$ELSE with ER$NAM 3002", r == (SV_ELSE, 3002, b""), repr(r))
    r = c.req(R_OPEN, "dict customers")
    row("vb.open: \"dict name\" opens the dictionary", r == (0, 0, _S(3)), repr(r))
    r = c.req(R_CLOSE, _S(2))
    r2 = c.req(R_READ, _S(2) + b"c1")
    row("vb.close: the slot is closed, a read through it is SV$ERROR and request 2 returns 5268", r == (0, 0, b"") and r2[0] == 3 and c.error_text() == msg(5268), repr((r, r2)))
    r = c.req(R_OPEN, "empty")
    row("vb.open: the lowest free file number is reused", r == (0, 0, _S(2)), repr(r))
    r = c.req(R_CLOSE, _S(9))
    row("vb.close: a file number that was never opened is 5268", r[0] == 3 and c.error_text() == msg(5268), repr(r))
    r = c.req(R_READ, _S(1) + b"c1")
    row("vb.read: the record, marks as they are stored: error 0, STATUS 0", r == (0, 0, rec_c1.encode("latin-1")), repr(r))
    r = c.req(R_READ, _S(1) + b"c9")
    row("vb.read: a record that is not there is SV$ELSE, STATUS() ER$RNF 3006, no data", r == (SV_ELSE, 3006, b""), repr(r))
    r = c.req(R_READ, _S(1))
    row("vb.read: an empty id is SV$ELSE with ER$IID 3000", r == (SV_ELSE, 3000, b""), repr(r))
    r = c.req(R_READ, _S(3) + b"name")
    row("vb.read: through the dictionary's file number it reads the dictionary item", r == (0, 0, ("D" + FMc + "1").encode("latin-1")), repr(r))
    r = c.req(R_OPEN, "mixed")
    fm = struct.unpack("<h", r[2])[0]
    r2, r3 = c.req(R_READ, _S(fm) + b"abc"), c.req(R_READ, _S(fm) + b"ABC")
    row("vb.read: a nocase file finds the record whatever the case of the id", r[0] == 0 and r2 == (0, 0, b"upper") and r3 == (0, 0, b"upper"), repr((r, r2, r3)))
    r = [c.req(R_READV, _S(1) + _S(0) + _L(f) + b"c1")[2] for f in (1, 2, 3, 5, 0)]
    row("vb.readv: rec<field> (the value marks stay); a field beyond the record and field 0 are null", r == [b"Smith", b"100\xfd200", b"x", b"", b""], repr(r))
    r = c.req(R_READV, _S(1) + _S(0) + _L(1) + b"c9")
    row("vb.readv: a record that is not there is SV$ELSE with ER$RNF", r == (SV_ELSE, 3006, b""), repr(r))
    r = c.req(R_READV, _S(1) + _S(3) + _L(1) + b"c1")
    row("vb.readv: a flag value the begin case does not list does nothing: success, no data", r == (0, 0, b""), repr(r))
    r = c.req(R_SELECT, _S(1) + _S(0))
    ids = []
    for _ in range(4):
        rn = c.req(R_READNEXT, _S(0))
        ids.append(rn)
    row("vb.select / vb.readnext: the ids one by one, then SV$ELSE at the end of the list",
        r == (0, 0, b"") and [x[2] for x in ids[:3]] == [b"c1", b"c2", b"c3"] and ids[3][0] == SV_ELSE and all(x[0] == 0 for x in ids[:3]), repr(ids))
    c.req(R_SELECT, _S(1) + _S(4))
    first = c.req(R_READNEXT, _S(4))
    rest = c.req(R_READLIST, _S(4))
    again = c.req(R_READLIST, _S(4))
    nxt = c.req(R_READNEXT, _S(4))
    row("vb.readlist: what is left of the list, field marks between, and the list is used up (a second readlist is null, readnext is SV$ELSE)",
        first[2] == b"c1" and rest == (0, 0, b"c2\xfec3") and again == (0, 0, b"") and nxt[0] == SV_ELSE, repr((first, rest, again, nxt)))
    r = c.req(R_SELECTLIST, _S(1))
    row("vb.selectlist: every id, field marks between", r == (0, 0, b"c1\xfec2\xfec3"), repr(r))
    r = c.req(R_SELECTLIST, _S(2))
    row("vb.selectlist: an empty file gives no data and success", r == (0, 0, b""), repr(r))
    c.req(R_SELECT, _S(1) + _S(2))
    r = c.req(R_CLEARSELECT, _S(2))
    r2 = c.req(R_READNEXT, _S(2))
    row("vb.clearselect: the list is gone", r == (0, 0, b"") and r2[0] == SV_ELSE, repr((r, r2)))
    r = c.req(R_SELECT, _S(1) + _S(11))
    t1 = c.error_text()
    r2 = c.req(R_READNEXT, _S(-1))
    row("vb.select / vb.readnext: a list number outside 0 to 10 is SV$ERROR, request 2 returns 5269", r[0] == 3 and t1 == msg(5269) and r2[0] == 3 and c.error_text() == msg(5269), repr((r, r2)))
    r = c.req(R_SELECT, _S(9) + _S(0))
    row("vb.select: the file number is checked first (5268)", r[0] == 3 and c.error_text() == msg(5268), repr(r))
    c.req(R_READ, _S(1) + b"c2")
    fi = {k: c.req(R_FILEINFO, _S(1) + _L(k)) for k in (0, 1, 2, 3, 1008, 1009, 1012, 1014, 1015)}
    row("vb.fileinfo: 0 open, 1 VOC name, 2 path, 3 type, 1008 nocase, 1009 file number, 1012 last id read, 1014 mark mapping (0: not a directory file), 1015 record count",
        {k: v[2] for k, v in fi.items()} == {0: b"1", 1: b"customers", 2: b"/data/acct/customers", 3: b"3", 1008: b"0", 1009: b"1", 1012: b"c2", 1014: b"0", 1015: b"3"}
        and all(v[:2] == (0, 0) for v in fi.values()), repr(fi))
    r = c.req(R_FILEINFO, _S(1) + _L(4))
    r2 = c.req(R_FILEINFO, _S(1) + _L(99999))
    row("vb.fileinfo: a key op_dio2.c does not know (4; 99999 cut to 16 bits) is an abort: the ON ERROR reply with message 1010", r == (1, 0, msg(1010).encode()) and r2[0] == 1, repr((r, r2)))
    st.file("customers").info[1001] = 1
    r = c.req(R_FILEINFO, _S(1) + _L(1001))
    row("vb.fileinfo: FakeFile.info overrides what the fake would answer", r[2] == b"1", repr(r))
    fd = struct.unpack("<h", c.req(R_OPEN, "dirfile")[2])[0]
    a = c.req(R_FILEINFO, _S(fd) + _L(1014))[2]
    c.req(R_MARKMAPPING, _S(fd) + _S(0))
    b = c.req(R_FILEINFO, _S(fd) + _L(1014))[2]
    r = c.req(R_MARKMAPPING, _S(fd) + _S(1))
    d_ = c.req(R_FILEINFO, _S(fd) + _L(1014))[2]
    r9 = c.req(R_MARKMAPPING, _S(9) + _S(1))
    row("vb.mark.mapping: a directory file starts with it on, 0 turns it off, 1 on again; a bad file number is 5268",
        (a, b, d_) == (b"1", b"0", b"1") and r == (0, 0, b"") and r9[0] == 3 and c.error_text() == msg(5268), repr((a, b, d_, r, r9)))
    r = c.req(R_REVISION)
    row("vb.revision: system(1012)", r == (0, 0, srv.revision.encode()), repr(r))
    r0, r27 = c.req(0), c.req(27)
    row("vb.illegal.action: 0 and 27 are SV$ERROR with no data and \"Illegal action code (N)\" for request 2",
        r0[0] == 3 and r27[0] == 3 and c.error_text() == "Illegal action code (27)", repr((r0, r27)))
    r = c.req(20, b"\x00\x00")
    row("a request apisrvr has and this fake does not build (20, call) is SV$ERROR saying so, and is noted", r[0] == 3 and "not implemented" in c.error_text()
        and any("request 20" in e for e in srv.errors), repr(r))
    r = c.req(R_QUIT)
    gone = closed_by_server(c)
    row("vb.quit: the reply is still written (error 0), then the connection is closed", r == (0, 0, b"") and gone and wait_closed(ses), repr(r))
    c.close()
    d = srv.delta(m_b)
    row("the session recorded its requests, in order, and every packet reached the packet log",
        ses.requests[:6] == [R_ACCOUNT, R_ACCOUNT, R_GETERROR, R_ACCOUNT, R_GETERROR, R_ACCOUNT] and d["types"][:2] == [47, 48]
        and ses.requests[-1] == R_QUIT and d["types"][2:] == ses.requests, repr(ses.requests[:6]))
    row("nothing was found wrong with the client except the one request the fake does not build", d["errors"] == ["request 20 is not built in netfake"], repr(d["errors"]))
    srv.errors.clear()

    # ---- C  the lock table, two connections ------------------------------------------------------------------------------------
    def open2():
        a_ = connect()
        b_ = connect()
        for x in (a_, b_):
            x.req(R_OPEN, "customers")
        return a_, b_, srv.sessions[-2].userno, srv.sessions[-1].userno
    c1, c2, u1, u2 = open2()
    row("two connections get different user numbers", u1 != u2 and u1 == srv.sessions[-2].userno)
    r = c1.req(R_READU, _S(1) + b"c1")
    row("vb.readu: the record comes back and the lock is taken", r == (0, 0, rec_c1.encode("latin-1")) and st.locks_of(u1) == [("customers", "c1", "update")], repr(r))
    r, rl = c2.req(R_READU, _S(1) + b"c1"), c2.req(R_READL, _S(1) + b"c1")
    row("a second connection's readu and readl are SV$LOCKED, no data, and STATUS() is the holder's user number", r == (SV_LOCKED, u1, b"") and rl == (SV_LOCKED, u1, b""), repr((r, rl)))
    rp = c2.req(R_READ, _S(1) + b"c1")
    row("a plain read ignores the lock", rp[0] == 0 and rp[2] == rec_c1.encode("latin-1"), repr(rp))
    a_, b_, z_ = c2.req(R_RECORDLOCKED, _S(1) + b"c1"), c1.req(R_RECORDLOCKED, _S(1) + b"c1"), c2.req(R_RECORDLOCKED, _S(1) + b"c2")
    row("vb.recordlocked: -2 (another user's update lock) with the holder in STATUS(), 2 for the holder, 0 and STATUS 0 for a free record",
        a_ == (0, u1, _L(-2)) and b_ == (0, u1, _L(2)) and z_ == (0, 0, _L(0)), repr((a_, b_, z_)))
    c1.req(R_READL, _S(1) + b"c1")
    r = c2.req(R_READL, _S(1) + b"c1")
    s1, s2 = c1.req(R_RECORDLOCKED, _S(1) + b"c1"), c2.req(R_RECORDLOCKED, _S(1) + b"c1")
    row("readl by the holder takes the update lock down to a read lock; another connection's readl then shares it (recordlocked 1 for both)",
        r[0] == 0 and s1[2] == _L(1) and s2[2] == _L(1), repr((r, s1, s2)))
    r = c2.req(R_READU, _S(1) + b"c1")
    row("a readu cannot take a record others hold a read lock on: SV$LOCKED naming a holder", r[0] == SV_LOCKED and r[1] in (u1,), repr(r))
    c1.req(R_RELEASE, _S(1) + b"c1")
    r = c2.req(R_RECORDLOCKED, _S(1) + b"c1")
    c2.req(R_RELEASE, _S(1) + b"c1")
    r2 = c2.req(R_RECORDLOCKED, _S(1) + b"c1")
    row("vb.release (one record): c1 lets go (c2 still holds a read lock), then c2 does", r[2] == _L(1) and r2[2] == _L(0), repr((r, r2)))
    r = c1.req(R_READU, _S(1) + b"zz")
    r2 = c2.req(R_READU, _S(1) + b"zz")
    row("a readu on a record that is not there takes the lock and the ELSE clause; the lock stays, so another connection is told it is locked",
        r == (SV_ELSE, 3006, b"") and r2 == (SV_LOCKED, u1, b""), repr((r, r2)))
    c1.req(R_RELEASE, _S(1))
    r = c2.req(R_READU, _S(1) + b"zz")
    row("vb.release with an empty id lets go of every lock on the file", r[0] == SV_ELSE and ("customers", "zz", "update") in st.locks_of(u2), repr(r))
    c1.req(R_READU, _S(1) + b"c1")
    c2.req(R_READU, _S(1) + b"c3")
    c1.req(R_RELEASE, _S(0))
    row("vb.release with file number 0 lets go of every lock of the session and of no other", st.locks_of(u1) == [] and ("customers", "c3", "update") in st.locks_of(u2),
        repr((st.locks_of(u1), st.locks_of(u2))))
    c2.req(R_RELEASE, _S(0))
    c1.req(R_READU, _S(1) + b"c1")
    r5, r6 = c2.req(R_READV, _S(1) + _S(5) + _L(1) + b"c1"), c2.req(R_READV, _S(1) + _S(6) + _L(1) + b"c1")
    row("vb.readv with flags 5 and 6 (update / shared lock, LOCKED clause) against a held record: SV$LOCKED with the holder in STATUS()",
        r5 == (SV_LOCKED, u1, b"") and r6 == (SV_LOCKED, u1, b""), repr((r5, r6)))
    c1.req(R_RELEASE, _S(0))
    r = c2.req(R_READV, _S(1) + _S(1) + _L(1) + b"c1")
    row("vb.readv with flags 1 (update lock, waiting) on a free record takes it and returns the field", r == (0, 0, b"Smith") and ("customers", "c1", "update") in st.locks_of(u2), repr(r))
    c2.req(R_RELEASE, _S(0))
    st.hold("customers", "c2", 7)
    st.hold_file("empty", 8)
    r = c1.req(R_READU, _S(1) + b"c2")
    oe = struct.unpack("<h", c1.req(R_OPEN, "empty")[2])[0]
    rf = c1.req(R_READL, _S(oe) + b"anything")
    rk = c1.req(R_RECORDLOCKED, _S(oe) + b"anything")
    row("a lock held by a process that is not a connection (FakeStore.hold, hold_file) is reported by its user number; a file lock is -3 in recordlocked",
        r == (SV_LOCKED, 7, b"") and rf == (SV_LOCKED, 8, b"") and rk == (0, 8, _L(-3)), repr((r, rf, rk)))
    st.drop_user(7)
    st.drop_user(8)
    r = c1.req(R_READU, _S(1) + b"c2")
    row("drop_user lets everything of that user go", r[0] == 0, repr(r))
    c1.req(R_RELEASE, _S(0))
    c1.req(R_READU, _S(1) + b"c1")
    box = {}

    def waiter():
        t0 = time.time()
        try:
            box["r"] = c2.req(R_READUW, _S(1) + b"c1")
        except Exception as ex_:
            box["r"] = ex_
        box["t"] = time.time() - t0
    th = threading.Thread(target=waiter)
    th.start()
    time.sleep(0.6)
    c1.req(R_RELEASE, _S(1) + b"c1")
    th.join(8)
    row("vb.readuw waits for the lock and gets the record when the holder lets go (about 0.6 s here)",
        box.get("r") == (0, 0, rec_c1.encode("latin-1")) and 0.4 <= box.get("t", 0) < 3.0, repr(box))
    c1.close()
    c2.close()
    c3 = connect(lock_wait=0.6)
    c4 = connect(lock_wait=0.6)
    ses3, ses4 = srv.sessions[-2], srv.sessions[-1]
    for x in (c3, c4):
        x.req(R_OPEN, "customers")
    c3.req(R_READU, _S(1) + b"c1")
    t0 = time.time()
    r = c4.req(R_READUW, _S(1) + b"c1")
    el = time.time() - t0
    row("a waiting request that is not satisfied in lock_wait seconds gives up with an ON ERROR reply that says so, and the fake notes it",
        r[0] == 1 and r[2].startswith(b"netfake: gave up") and 0.5 <= el < 3.0 and any("gave up" in e for e in srv.errors), repr((r, el)))
    srv.errors.clear()
    c3.close()
    wait_closed(ses3)
    r = c4.req(R_READU, _S(1) + b"c1")
    row("the locks of a connection that ends are let go", r[0] == 0 and st.locks_of(ses3.userno) == [], repr(r))
    c4.close()
    wait_closed(ses4)

    # ---- D  the files-only gate ----------------------------------------------------------------------------------------------------
    c = connect(files_only=True, write_group=True)        # 18 Oct 26: a request the gate allows reaches the dispatch only for a login in sdfileswrite (the group rows are in section D2)
    ses = srv.sessions[-1]
    refusal = "This login is for files only: request 20 is not allowed"
    r = c.req(20, b"\x00\x00")
    row("files-only: request 20 (call) is answered with message 11480, the ON ERROR reply, and is not dispatched",
        r == (1, 0, refusal.encode()) and msg(11480, 20) == refusal and ses.refused == [20], repr(r))
    r = [c.req(n) for n in (0, 21, 27, 47, 50, 61, 69, 70)]
    row("files-only: 0, 21, 27, 47, 50, 61, 69 and 70 are refused the same way", all(x[0] == 1 and x[2].startswith(b"This login is for files only") for x in r) and
        ses.refused == [20, 0, 21, 27, 47, 50, 61, 69, 70], repr(r))
    r1 = c.req(R_ACCOUNT, "acct")
    r2 = c.req(R_ACCOUNT, "acct")
    row("files-only: request 3 is allowed the first time and refused the second (the session has entered an account)",
        r1 == (0, 0, b"") and r2 == (1, 0, msg(11480, 3).encode()) and ses.refused[-1] == 3, repr((r1, r2)))
    r = c.req(R_OPEN, "customers")
    r2 = c.req(R_READ, r[2] + b"c1")
    row("files-only: open and read are allowed through", r2 == (0, 0, rec_c1.encode("latin-1")), repr((r, r2)))
    r = c.req(35, _S(1))
    row("files-only: a request the gate allows and the fake does not build (35, indices) reaches the dispatch: SV$ERROR \"not implemented\"",
        r[0] == 3 and "not implemented" in c.error_text() and 35 not in ses.refused, repr(r))
    c.close()
    wait_closed(ses)
    row("... and the indices request is the one thing the fake noted (S.72, 20 Oct 26: it was the file lock, request 32, until that was built)",
        srv.errors == ["request 35 is not built in netfake"], repr(srv.errors))
    srv.errors.clear()
    c = connect(user="carol", pw="pw-carol")
    ses = srv.sessions[-1]
    r = c.req(21, b"x")
    row("a user added with files_only=True gets the files-only login whatever the connection says", ses.files_only and r[0] == 1 and ses.refused == [21], repr(r))
    c.close()
    wait_closed(ses)
    c = connect(files_only=True, fail={21: (1, "injected"), 6: (1, "injected")})
    ses = srv.sessions[-1]
    r = c.req(21, b"x")
    row("files-only is before fail: a refused request is never injected", r[2].startswith(b"This login is for files only"), repr(r))
    r = c.req(R_READ, _S(1) + b"c1")
    row("... and an allowed request is", r == (1, 0, b"injected"), repr(r))
    c.close()
    wait_closed(ses)
    row("... and the refusals and injections noted nothing", srv.errors == [], repr(srv.errors))
    want = _apifilesok_numbers()
    if want is None:
        print("  [SKIP] gpl.bp/apifilesok is not there: the allow list is not compared")
    else:
        row("FILES_OK is gpl.bp/apifilesok's table, number for number (and 3 is allowed once)", FILES_OK == want, repr(sorted(FILES_OK ^ want)))
    row("FileSession.HANDLERS covers exactly the requests the module text says: 1 to 19, 30 to 34, 37, 40, 41, 46, 49 (32 and 33, the file locks, since S.72)",
        set(FileSession.HANDLERS) == set(range(1, 20)) | {30, 31, 32, 33, 34, 37, 40, 41, 46, 49}, repr(sorted(FileSession.HANDLERS)))
    row("NOT_BUILT and the built requests do not overlap", not (NOT_BUILT & set(FileSession.HANDLERS)), repr(sorted(NOT_BUILT & set(FileSession.HANDLERS))))
    bad_msgs = []
    for num, copy in _MSG_COPY.items():
        try:
            with open(os.path.join(_MSG_DIR, str(num)), encoding="latin-1") as fh:
                if fh.readline().rstrip("\r\n") != copy:
                    bad_msgs.append(num)
        except OSError:
            pass
    row("the copies of the messages in this file are what sdsys/messages holds (a file that is not there is not compared)", bad_msgs == [], repr(bad_msgs))

    # ---- E fault injection --------------------------------------------------------------------------------------------------------
    c = connect(close_after_requests=2)
    ses = srv.sessions[-1]
    r1 = c.req(R_OPEN, "customers")
    r2 = c.req(R_READ, _S(1) + b"c1")
    gone = closed_by_server(c)
    row("close_after_requests=2: two requests are answered, the third finds the connection closed", r1[0] == 0 and r2[0] == 0 and gone and wait_closed(ses), repr((r1, r2, gone)))
    c.close()
    c = connect(drop_request=2)
    ses = srv.sessions[-1]
    r1 = c.req(R_OPEN, "customers")
    try:
        c.req(R_READ, _S(1) + b"c1")
        r2 = "answered"
    except (EOFError, OSError):
        r2 = "closed"
    row("drop_request=2: the second request is read and recorded and never answered: the connection closes", r1[0] == 0 and r2 == "closed" and ses.requests == [R_OPEN, R_READ], repr((r1, r2, ses.requests)))
    c.close()
    c = connect(delay=0.5)
    t0 = time.time()
    c.req(R_REVISION)
    el = time.time() - t0
    row("delay=0.5: every reply is held back (measured %.2f s)" % el, 0.45 <= el < 3.0, repr(el))
    c.close()
    c = connect(delay={R_READ: 0.5})
    c.req(R_OPEN, "customers")
    t0 = time.time()
    c.req(R_REVISION)
    fast = time.time() - t0
    t0 = time.time()
    c.req(R_READ, _S(1) + b"c1")
    slow = time.time() - t0
    row("delay={6: 0.5}: only reads are held back (revision %.2f s, read %.2f s)" % (fast, slow), fast < 0.4 and 0.45 <= slow < 3.0, repr((fast, slow)))
    c.close()
    c = connect(fail={R_READ: (1, "boom", 1)})
    ses = srv.sessions[-1]
    c.req(R_OPEN, "customers")
    r1 = c.req(R_READ, _S(1) + b"c1")
    r2 = c.req(R_READ, _S(1) + b"c1")
    row("fail={6: (1, 'boom', 1)}: the first read gets the ON ERROR reply with that text, the second is dispatched; open is untouched",
        r1 == (1, 0, b"boom") and r2[0] == 0 and r2[2] == rec_c1.encode("latin-1") and ses.injected == [(R_READ, "fail")], repr((r1, r2, ses.injected)))
    c.close()
    c = connect(fail={R_READ: (SV_ERROR, "bad thing")})
    c.req(R_OPEN, "customers")
    r = c.req(R_READ, _S(1) + b"c1")
    row("fail with the SV$ERROR field: no data, and request 2 returns the text", r == (3, 0, b"") and c.error_text() == "bad thing", repr(r))
    c.close()
    c = connect(fail={"*": (1, "all")})
    r = c.req(R_OPEN, "customers")
    row("fail={'*': ...}: every request that has no entry of its own is answered with it", r == (1, 0, b"all"), repr(r))
    c.close()
    c = connect(no_reply=(R_READ,), timeout=1)
    ses = srv.sessions[-1]
    c.req(R_OPEN, "customers")
    try:
        c.req(R_READ, _S(1) + b"c1")
        outcome = "answered"
    except TimeoutError:
        outcome = "timeout"
    except (EOFError, OSError):
        outcome = "closed"
    row("no_reply=(6,): the read is recorded and never answered, the client's own timeout is what it sees", outcome == "timeout" and ses.requests == [R_OPEN, R_READ]
        and ses.injected == [(R_READ, "no_reply")], repr((outcome, ses.requests, ses.injected)))
    c.close()
    c = connect(no_file_access=True)
    r = c.req(R_OPEN, "customers")
    row("no_file_access: open answers 5262 as an ON ERROR reply", r == (1, 0, msg(5262).encode()), repr(r))
    c.close()

    # ---- F  files=False: the old behaviour --------------------------------------------------------------------------------------------
    srv.configure()
    m_f = srv.mark()
    cl = ApiClient(srv.port, timeout=1)
    ok_login = cl.login("alice", "pw-one")
    try:
        cl.req(R_READ, _S(1) + b"c1")
        outcome = "answered"
    except TimeoutError:
        outcome = "timeout"
    except (EOFError, OSError):
        outcome = "closed"
    cl.close()
    srv.settle(quiet=0.3)
    d = srv.delta(m_f)
    row("files=False (the default): a request after the login is recorded and not answered, no session is made",
        ok_login[0] == "ok" and outcome == "timeout" and d["types"] == [47, 48, 6] and d["sessions"] == [], repr((ok_login, outcome, d["types"])))

    # ---- G  the pin ------------------------------------------------------------------------------------------------------------------
    cl = ApiClient(srv.port)
    seen = hashlib.sha256(spki_der(cl.peer_der)).hexdigest()
    cl.close()
    row("srv.pin is the SHA-256 of the SubjectPublicKeyInfo of the certificate the TLS peer presents (found here by walking the ASN.1), 64 lower case hex digits",
        srv.pin == seen and re.fullmatch(r"[0-9a-f]{64}", srv.pin) is not None, "%s vs %s" % (srv.pin, seen))
    srv.configure()


def selftest_writes(srv, row):
    """The slice 3e rows (18 Oct 26): requests 16 to 19, 30 and 31 in apisrvr's reply formats (each row names its vb. label), the lock
    bookkeeping per file number, and the gates and faults added to DEFAULTS: success_status, must_lock, readonly, edit_allow, maxrlock,
    drop_before, drop_after.  Every group has a control (the behaviour with the setting off, or the neighbouring request).  The statuses
    of an ON ERROR reply are compared as the 32 bit unsigned the wire carries (-3023 is 2**32 - 3023)."""
    FMc = "\xfe"
    marks = "".join(chr(x) for x in range(248, 256))
    st = srv.store
    base = {"wf": {"a": "one", "b": "two", "c": "three"}, "wn": {"Key": "orig"}, "wcs": {"Key": "orig"}, "voc": {"x": "v"},
            "wbp": {"p": "prog"}, "ptr": {"q": "v"}, "nopath": {"z": "1"}, "wtmp": {"t1": "x", "t2": "y"}}
    st.add_file("wf", base["wf"], dict_items={"d1": "D" + FMc + "1"})
    st.add_file("wn", base["wn"], nocase=True)
    st.add_file("wcs", base["wcs"])
    st.add_file("voc", base["voc"])                                    # the path /fake/voc: the last component is voc
    st.add_file("wbp", base["wbp"], path="/data/acct/wbp.bp")
    st.add_file("ptr", base["ptr"], path="/data/acct/voc")             # a Q-pointer to a VOC: caught by the PATHNAME
    st.add_file("nopath", base["nopath"], path="")
    st.add_file("wtmp", base["wtmp"])
    NEG = lambda n: (2 ** 32 - n) & 0xFFFFFFFF                           # a negative STATUS() as the reply carries it

    def reset():
        for name, recs in base.items():
            f = st.file(name)
            f.records.clear()
            f.records.update(recs)
        d = st.file("wf").dict_items
        d.clear()
        d["d1"] = "D" + FMc + "1"
        for u in (7, 8):
            st.drop_user(u)

    def connect(timeout=5, user="alice", pw="pw-one", **cfg):
        srv.configure(files=True, **cfg)
        cl = ApiClient(srv.port, timeout=timeout)
        r = cl.login(user, pw)
        if r[0] != "ok":
            raise RuntimeError("netfake self-test: login gave %r" % (r,))
        return cl

    def wait_closed(ses, limit=4.0):
        t0 = time.time()
        while not ses.closed and time.time() - t0 < limit:
            time.sleep(0.05)
        return ses.closed

    def bye(cl, ses):
        cl.close()
        wait_closed(ses)

    def gone(cl, ses, ptype, data):
        """The request is sent and the server closes without a reply."""
        try:
            cl.req(ptype, data)
            return False
        except (EOFError, OSError):
            return wait_closed(ses)

    def W(fno, rid, rec):
        return _S(fno) + _S(len(rid)) + rid.encode("latin-1") + rec.encode("latin-1")

    def D(fno, rid):
        return _S(fno) + rid.encode("latin-1")

    def K(fno, flags, rid):
        return _S(fno) + _S(flags) + rid.encode("latin-1")

    def opened(cl, *names):
        """Open each name; the file numbers, which are 1, 2 ... on a fresh connection."""
        return [struct.unpack("<h", cl.req(R_OPEN, n)[2])[0] for n in names]

    # ---- W1  WRITE / WRITEU / DELETE / DELETEU: the formats and what each does to the lock ---------------------------------------
    reset()
    c = connect()
    ses = srv.sessions[-1]
    u = ses.userno
    f1, = opened(c, "wf")
    rec = "A" + FMc + "b\xfdc" + marks
    r = c.req(R_WRITE, W(f1, "new", rec))
    row("vb.write: error 0, STATUS 0, no data; the record is stored with its marks (field, value and the eight characters 248-255) as sent",
        r == (0, 0, b"") and st.records("wf").get("new") == rec, repr((r, st.records("wf").get("new"))))
    r = c.req(R_WRITE, W(f1, "a", ""))
    row("vb.write: a null record is a record (stored as the null string), the id the same file already holds is replaced",
        r == (0, 0, b"") and st.records("wf").get("a") == "" and "a" in st.records("wf"), repr(st.records("wf")))
    r = c.req(R_READ, _S(f1) + b"new")
    row("a record written is read back by request 6 at once, byte for byte", r == (0, 0, rec.encode("latin-1")), repr(r))
    r2 = c.req(R_SELECTLIST, _S(f1))
    row("... and request 37 lists its id", b"new" in r2[2].split(b"\xfe"), repr(r2))
    reset()
    c.req(R_READU, _S(f1) + b"a")
    row("CONTROL for the lock rows: a readu took the update lock", st.locks_of(u) == [("wf", "a", "update")], repr(st.locks_of(u)))
    r = c.req(R_WRITE, W(f1, "a", "w1"))
    row("vb.write lets go of the session's update lock on the id", r == (0, 0, b"") and st.locks_of(u) == [] and st.records("wf")["a"] == "w1",
        repr((r, st.locks_of(u))))
    c.req(R_READL, _S(f1) + b"b")
    r = c.req(R_WRITE, W(f1, "b", "w2"))
    row("vb.write lets go of a READ lock too (unlock_record() goes by id)", r == (0, 0, b"") and st.locks_of(u) == [], repr(st.locks_of(u)))
    c.req(R_READU, _S(f1) + b"a")
    r = c.req(R_WRITEU, W(f1, "a", "w3"))
    row("vb.writeu writes and KEEPS the lock (the control for the two rows above)",
        r == (0, 0, b"") and st.records("wf")["a"] == "w3" and st.locks_of(u) == [("wf", "a", "update")], repr((r, st.locks_of(u))))
    r = c.req(R_WRITEU, W(f1, "fresh", "w4"))
    row("vb.writeu of a record that is not there creates it and takes no lock", r == (0, 0, b"") and st.records("wf")["fresh"] == "w4" and
        st.locks_of(u) == [("wf", "a", "update")], repr(st.locks_of(u)))
    r = c.req(R_DELETE, D(f1, "a"))
    row("vb.delete: error 0, STATUS 0, no data; the record is gone and the lock with it",
        r == (0, 0, b"") and "a" not in st.records("wf") and st.locks_of(u) == [], repr((r, st.locks_of(u))))
    r = c.req(R_DELETE, D(f1, "no-such-record"))
    row("vb.delete of a record that is not there is a success (error 0, STATUS 0) and changes nothing", r == (0, 0, b"") and set(st.records("wf")) == {"b", "c", "fresh"},
        repr((r, sorted(st.records("wf")))))
    c.req(R_READU, _S(f1) + b"b")
    r = c.req(R_DELETEU, D(f1, "b"))
    row("vb.deleteu removes the record and KEEPS the lock", r == (0, 0, b"") and "b" not in st.records("wf") and st.locks_of(u) == [("wf", "b", "update")],
        repr((r, st.locks_of(u))))
    r = c.req(R_DELETEU, D(f1, "never-there"))
    row("vb.deleteu of a record that is not there is a success too", r == (0, 0, b""), repr(r))
    c.req(R_RELEASE, _S(0))
    bye(c, ses)

    # ---- W2  ids ---------------------------------------------------------------------------------------------------------------
    reset()
    c = connect()
    ses = srv.sessions[-1]
    f1, = opened(c, "wf")
    row("ids: an EMPTY id is refused for write, writeu, delete and deleteu: ON ERROR (error 1), STATUS +3000 and NO text (REAL_ON_ERROR, measured on the real server 19 Oct 26), nothing stored",
        all(c.req(t, d) == (1, 3000, b"") for t, d in ((R_WRITE, W(f1, "", "x")), (R_WRITEU, W(f1, "", "x")), (R_DELETE, D(f1, "")), (R_DELETEU, D(f1, ""))))
        and st.records("wf") == base["wf"], repr(st.records("wf")))
    i63, i64 = "i" * 63, "j" * 64
    r63, r64 = c.req(R_WRITE, W(f1, i63, "x")), c.req(R_WRITE, W(f1, i64, "x"))
    row("ids: 63 bytes is stored, 64 is refused with +3000 and no text (the server's MAXIDLEN)", r63 == (0, 0, b"") and i63 in st.records("wf") and r64 == (1, 3000, b"")
        and i64 not in st.records("wf"), repr((r63, r64)))
    rm = c.req(R_WRITE, W(f1, "m" + chr(251), "x"))
    rn = [c.req(R_WRITE, W(f1, "n" + chr(x), "x")) for x in (248, 249, 250)]
    rh = c.req(R_WRITE, W(f1, "h" + chr(247), "x"))
    rall = [c.req(R_WRITE, W(f1, "k" + chr(x), "x")) for x in range(251, 256)]
    row("ids: a MARK byte (251 to 255, the five marks) is refused with +3000, every one of the five (measured on the real server by sandbox-req29.py section G: 247 to 250 accepted, 251 refused - "
        "the fake refused 248 to 255 before 19 Oct 26); a byte of 128-250 is an ordinary character (the owner's 12 Oct exception)",
        rm == (1, 3000, b"") and all(x == (1, 3000, b"") for x in rall) and rh == (0, 0, b"") and all(x == (0, 0, b"") for x in rn) and "h" + chr(247) in st.records("wf")
        and all("n" + chr(x) in st.records("wf") for x in (248, 249, 250)) and "m" + chr(251) not in st.records("wf") and not any("k" + chr(x) in st.records("wf") for x in range(251, 256)),
        repr((rm, rn, rh, rall)))
    bye(c, ses)

    # ---- W3  nocase ------------------------------------------------------------------------------------------------------------
    reset()
    c = connect()
    ses = srv.sessions[-1]
    u = ses.userno
    fn, fc = opened(c, "wn", "wcs")
    c.req(R_WRITE, W(fn, "KEY", "new1"))
    row("a write to a NOCASE file under another spelling replaces the record it already holds and keeps ITS key", st.records("wn") == {"Key": "new1"}, repr(st.records("wn")))
    c.req(R_WRITE, W(fn, "Other", "o"))
    row("... a new id is stored as it was sent", st.records("wn") == {"Key": "new1", "Other": "o"}, repr(st.records("wn")))
    c.req(R_WRITE, W(fc, "KEY", "new2"))
    row("CONTROL: a file that is not nocase keeps the two spellings apart", st.records("wcs") == {"Key": "orig", "KEY": "new2"}, repr(st.records("wcs")))
    c.req(R_DELETE, D(fn, "oTHER"))
    row("vb.delete finds the record whatever the case in a nocase file", st.records("wn") == {"Key": "new1"}, repr(st.records("wn")))
    c.req(R_LOCKRECORD, K(fn, 3, "KEY"))
    held = st.locks_of(u)
    c.req(R_WRITE, W(fn, "key", "new3"))
    row("a lock on a nocase file is by the folded id: a write under another spelling lets it go",
        held == [("wn", "KEY", "update")] and st.locks_of(u) == [] and st.records("wn") == {"Key": "new3"}, repr((held, st.locks_of(u))))
    bye(c, ses)

    # ---- W4  request 30, RECORDLOCK ---------------------------------------------------------------------------------------------
    reset()
    c = connect(lock_wait=0.5)
    ses = srv.sessions[-1]
    u = ses.userno
    f1, f2 = opened(c, "wf", "wtmp")
    out = []
    for flags, kind in ((0, "shared"), (1, "update"), (2, "shared"), (3, "update")):
        r = c.req(R_LOCKRECORD, K(f1, flags, "a"))
        out.append((flags, r, st.locks_of(u)))
        c.req(R_RELEASE, D(f1, "a"))
        if r != (0, 0, b"") or out[-1][2] != [("wf", "a", kind)]:
            out.append("BAD")
    row("vb.lock.record: flags 0 shared + wait, 1 update + wait, 2 shared no-wait, 3 update no-wait each take that lock on a free record: error 0, no data",
        "BAD" not in out and len(out) == 4, repr(out))
    r = c.req(R_LOCKRECORD, K(f1, 9, "b"))
    row("vb.lock.record: any other flags value does nothing and succeeds (the begin case has no branch)", r == (0, 0, b"") and st.locks_of(u) == [], repr((r, st.locks_of(u))))
    r = c.req(R_LOCKRECORD, K(f1, 3, ""))
    row("vb.lock.record: a null id is an ON ERROR reply, not a lock", r[0] == 1 and st.locks_of(u) == [], repr(r))
    st.hold("wf", "a", 7)
    r2, r3 = c.req(R_LOCKRECORD, K(f1, 2, "a")), c.req(R_LOCKRECORD, K(f1, 3, "a"))
    row("a no-wait lock on a record another user holds is SV$LOCKED, no data, STATUS() the HOLDER's user number (flags 2 and 3)",
        r2 == (SV_LOCKED, 7, b"") and r3 == (SV_LOCKED, 7, b"") and st.locks_of(u) == [], repr((r2, r3)))
    t0 = time.time()
    r0 = c.req(R_LOCKRECORD, K(f1, 0, "a"))
    r1 = c.req(R_LOCKRECORD, K(f1, 1, "a"))
    el = time.time() - t0
    row("a WAITING lock (flags 0, 1) on a held record gives up after lock_wait with an ON ERROR reply that says so, and the fake notes it (measured %.2f s)" % el,
        r0[0] == 1 and r1[0] == 1 and r0[2].startswith(b"netfake: gave up") and 0.9 <= el < 4 and sum("gave up" in e for e in srv.errors) == 2, repr((r0, r1, el)))
    srv.errors.clear()
    st.drop_user(7)
    st.hold("wf", "a", 7, kind="shared")
    ra, rb = c.req(R_LOCKRECORD, K(f1, 2, "a")), c.req(R_LOCKRECORD, K(f1, 3, "a"))
    row("CONTROL: another user's READ lock lets a shared no-wait lock through (error 0) and blocks an update one (SV$LOCKED, the holder)",
        ra == (0, 0, b"") and rb == (SV_LOCKED, 7, b""), repr((ra, rb)))
    c.req(R_RELEASE, _S(0))
    st.drop_user(7)
    st.hold_file("wf", 8)
    r = c.req(R_LOCKRECORD, K(f1, 3, "b"))
    row("another user's FILE lock blocks a record lock: SV$LOCKED with the file lock holder's number", r == (SV_LOCKED, 8, b""), repr(r))
    st.drop_user(8)
    c.req(R_LOCKRECORD, K(f1, 3, "a"))
    box = {}
    ses2 = None
    c2 = connect(lock_wait=5)
    ses2 = srv.sessions[-1]
    g1, = opened(c2, "wf")

    def waiter():
        t1 = time.time()
        try:
            box["r"] = c2.req(R_LOCKRECORD, K(g1, 1, "a"))
        except Exception as ex_:
            box["r"] = ex_
        box["t"] = time.time() - t1
    th = threading.Thread(target=waiter)
    th.start()
    time.sleep(0.6)
    c.req(R_RELEASE, D(f1, "a"))
    th.join(8)
    row("flags 1 (update, waiting) waits for the holder and gets the lock when it lets go (about 0.6 s here)",
        box.get("r") == (0, 0, b"") and 0.4 <= box.get("t", 0) < 3.0 and st.locks_of(ses2.userno) == [("wf", "a", "update")], repr(box))
    bye(c2, ses2)
    c.req(R_RELEASE, _S(0))
    row("CONTROL: the lock table is empty again for the first session", st.locks_of(u) == [], repr(st.locks_of(u)))
    bye(c, ses)

    # ---- W5  the locks of a file number: CLOSE, RELEASE, a write through another slot -------------------------------------------------
    reset()
    c = connect()
    ses = srv.sessions[-1]
    u = ses.userno
    s1, s2 = opened(c, "wf", "wf")
    c.req(R_LOCKRECORD, K(s1, 3, "a"))
    c.req(R_LOCKRECORD, K(s2, 3, "b"))
    c.req(R_READU, _S(s1) + b"c")
    row("two slots of one file: the locks taken through each are in the lock table and in that slot's set",
        st.locks_of(u) == [("wf", "a", "update"), ("wf", "b", "update"), ("wf", "c", "update")] and ses.taken == {s1: {("wf", "a"), ("wf", "c")}, s2: {("wf", "b")}},
        repr((st.locks_of(u), ses.taken)))
    r = c.req(R_CLOSE, _S(s1))
    row("vb.close lets go of the record locks taken through THAT file number and no other (a and c go, b stays)",
        r == (0, 0, b"") and st.locks_of(u) == [("wf", "b", "update")], repr((r, st.locks_of(u))))
    c.req(R_CLOSE, _S(s2))
    row("... and closing the other slot lets go of b", st.locks_of(u) == [], repr(st.locks_of(u)))
    s1, s2 = opened(c, "wf", "wf")
    c.req(R_LOCKRECORD, K(s1, 3, "a"))
    r = c.req(R_WRITE, W(s2, "a", "via-2"))
    row("a lock taken through slot 1 is let go by a plain write through slot 2 of the same file (by file and id), and slot 1's set forgets it",
        r == (0, 0, b"") and st.locks_of(u) == [] and ses.taken.get(s1, set()) == set(), repr((st.locks_of(u), ses.taken)))
    c.req(R_LOCKRECORD, K(s1, 3, "a"))
    c.req(R_LOCKRECORD, K(s1, 3, "b"))
    c.req(R_RELEASE, D(s2, "a"))
    row("vb.release through slot 2 lets go of what slot 1 took on that id and prunes the set (b stays)",
        st.locks_of(u) == [("wf", "b", "update")] and ses.taken[s1] == {("wf", "b")}, repr((st.locks_of(u), ses.taken)))
    c.req(R_LOCKRECORD, K(s1, 3, "c"))
    c.req(R_RELEASE, _S(s2))
    row("vb.release with an empty id lets go of every lock on the file and empties the sets", st.locks_of(u) == [] and ses.taken[s1] == set(), repr((st.locks_of(u), ses.taken)))
    c.req(R_LOCKRECORD, K(s1, 3, "c"))
    c.req(R_RELEASE, _S(0))
    row("vb.release with file number 0 lets go of everything and clears the sets", st.locks_of(u) == [] and ses.taken == {}, repr((st.locks_of(u), ses.taken)))
    c.req(R_LOCKRECORD, K(s1, 3, "a"))
    c.req(R_WRITEU, W(s2, "a", "kept"))
    row("CONTROL: writeu through the other slot does not let the lock go, and the set keeps it", st.locks_of(u) == [("wf", "a", "update")] and ses.taken[s1] == {("wf", "a")},
        repr((st.locks_of(u), ses.taken)))
    c.close()
    wait_closed(ses)
    row("a connection that ends lets go of everything it held", st.locks_of(u) == [], repr(st.locks_of(u)))

    # ---- W6  CLEARFILE ----------------------------------------------------------------------------------------------------------
    reset()
    c = connect(lock_wait=0.5)
    ses = srv.sessions[-1]
    u = ses.userno
    f1, f2 = opened(c, "wf", "wtmp")
    c.req(R_LOCKRECORD, K(f2, 3, "t1"))
    r = c.req(R_CLEARFILE, _S(f2))
    row("vb.clearfile: error 0, STATUS 0, no data; every record goes, the other file is untouched, and the lock table is not touched",
        r == (0, 0, b"") and st.records("wtmp") == {} and st.records("wf") == base["wf"] and st.locks_of(u) == [("wtmp", "t1", "update")], repr((r, st.records("wtmp"), st.locks_of(u))))
    r = c.req(R_CLEARFILE, _S(f2))
    row("vb.clearfile of an empty file is a success", r == (0, 0, b""), repr(r))
    r = c.req(R_READ, _S(f2) + b"t1")
    row("... a read after it is the ELSE clause (ER$RNF)", r == (SV_ELSE, 3006, b""), repr(r))
    c.req(R_RELEASE, _S(0))
    st.hold_file("wtmp", 8)
    reset_recs = st.file("wtmp").records
    reset_recs.update(base["wtmp"])
    t0 = time.time()
    r = c.req(R_CLEARFILE, _S(f2))
    el = time.time() - t0
    row("vb.clearfile while ANOTHER user holds the file lock waits lock_wait seconds, then an ON ERROR reply that says so; nothing is cleared (measured %.2f s)" % el,
        r[0] == 1 and r[2].startswith(b"netfake: gave up") and 0.4 <= el < 3.0 and st.records("wtmp") == base["wtmp"] and any("gave up" in e for e in srv.errors),
        repr((r, el, st.records("wtmp"))))
    srv.errors.clear()
    st.drop_user(8)
    r = c.req(R_CLEARFILE, _S(f2))
    row("... and once that user is gone the clear goes through", r == (0, 0, b"") and st.records("wtmp") == {}, repr((r, st.records("wtmp"))))
    bye(c, ses)
    reset()
    c = connect(lock_wait=5)
    ses = srv.sessions[-1]
    f2, = opened(c, "wtmp")
    st.hold_file("wtmp", 8)
    box = {}

    def clearer():
        t1 = time.time()
        try:
            box["r"] = c.req(R_CLEARFILE, _S(f2))
        except Exception as ex_:
            box["r"] = ex_
        box["t"] = time.time() - t1
    th = threading.Thread(target=clearer)
    th.start()
    time.sleep(0.6)
    st.drop_user(8)
    th.join(8)
    row("vb.clearfile waits for the other user's file lock and clears when it is let go (about 0.6 s here)",
        box.get("r") == (0, 0, b"") and 0.4 <= box.get("t", 0) < 3.0 and st.records("wtmp") == {}, repr(box))
    bye(c, ses)

    # ---- W7  a file number that is not open, in every new request ----------------------------------------------------------------
    c = connect()
    ses = srv.sessions[-1]
    bad = {t: c.req(t, d) for t, d in ((R_WRITE, W(9, "a", "x")), (R_WRITEU, W(9, "a", "x")), (R_DELETE, D(9, "a")), (R_DELETEU, D(9, "a")),
                                      (R_LOCKRECORD, K(9, 3, "a")), (R_CLEARFILE, _S(9)))}
    row("a file number that was never opened is SV$ERROR with no data in 16, 17, 18, 19, 30 and 31, and request 2 returns 5268 each time",
        all(v == (3, 0, b"") for v in bad.values()) and all((c.req(t, d)[0] == 3 and c.error_text() == msg(5268)) for t, d in ((R_WRITE, W(9, "a", "x")), (R_CLEARFILE, _S(9)))),
        repr(bad))
    bye(c, ses)

    # ---- W8  success_status: the STATUS() of a good reply is configuration, and a client must not read it -------------------------------
    reset()
    c = connect(success_status=4242)
    ses = srv.sessions[-1]
    f1, f2 = opened(c, "wf", "wtmp")
    got = {"write": c.req(R_WRITE, W(f1, "a", "x")), "writeu": c.req(R_WRITEU, W(f1, "a", "y")), "delete": c.req(R_DELETE, D(f1, "b")),
           "deleteu": c.req(R_DELETEU, D(f1, "c")), "lock": c.req(R_LOCKRECORD, K(f1, 3, "a")), "badflags": c.req(R_LOCKRECORD, K(f1, 9, "a")),
           "release": c.req(R_RELEASE, D(f1, "a")), "clear": c.req(R_CLEARFILE, _S(f2))}
    row("success_status=4242: the reply to 15, 16, 17, 18, 19, 30 (also an unknown flags value) and 31 carries that STATUS(); data and error field unchanged",
        all(v == (0, 4242, b"") for v in got.values()), repr(got))
    r, rr, re_ = c.req(R_READ, _S(f1) + b"a"), c.req(R_READ, _S(f1) + b"nope"), c.req(R_WRITE, W(f1, "", "x"))
    row("CONTROL: a read still has STATUS 0, a read that finds nothing 3006 (ER$RNF), and an ON ERROR reply its own status (+3000), never 4242",
        r == (0, 0, b"y") and rr == (SV_ELSE, 3006, b"") and re_[:2] == (1, 3000), repr((r, rr, re_)))
    bye(c, ses)

    # ---- W9  must_lock ---------------------------------------------------------------------------------------------------------------
    reset()
    c = connect(must_lock=True)
    ses = srv.sessions[-1]
    u = ses.userno
    f1, f2, fn = opened(c, "wf", "wtmp", "wn")
    refused = [c.req(t, d) for t, d in ((R_WRITE, W(f1, "a", "x")), (R_WRITEU, W(f1, "a", "x")), (R_DELETE, D(f1, "a")), (R_DELETEU, D(f1, "a")))]
    row("must_lock: a write, writeu, delete and deleteu without the update lock are ON ERROR with STATUS -3023 and no data, and change nothing",
        all(v == (1, NEG(3023), b"") for v in refused) and st.records("wf") == base["wf"], repr((refused, st.records("wf"))))
    c.req(R_READL, _S(f1) + b"a")
    r = c.req(R_WRITE, W(f1, "a", "x"))
    row("must_lock: a READ lock is not enough (the update lock is what MUSTLOCK wants)", r == (1, NEG(3023), b"") and st.records("wf") == base["wf"], repr(r))
    c.req(R_READU, _S(f1) + b"a")
    r = c.req(R_WRITE, W(f1, "a", "x"))
    row("must_lock: with the update lock (taken by readu) the write goes through, and releases it", r == (0, 0, b"") and st.records("wf")["a"] == "x" and st.locks_of(u) == [], repr(r))
    c.req(R_LOCKRECORD, K(f1, 3, "b"))
    r = c.req(R_DELETE, D(f1, "b"))
    row("must_lock: an update lock taken by request 30 counts too, for delete", r == (0, 0, b"") and "b" not in st.records("wf"), repr(r))
    c.req(R_LOCKRECORD, K(fn, 3, "KEY"))
    r = c.req(R_WRITE, W(fn, "key", "x"))
    row("must_lock: on a nocase file the lock is by the folded id", r == (0, 0, b"") and st.records("wn") == {"Key": "x"}, repr(r))
    r = c.req(R_CLEARFILE, _S(f2))
    row("must_lock does not apply to CLEARFILE (it has no record)", r == (0, 0, b"") and st.records("wtmp") == {}, repr(r))
    bye(c, ses)
    reset()
    c = connect()
    ses = srv.sessions[-1]
    f1, = opened(c, "wf")
    r = c.req(R_WRITE, W(f1, "a", "x"))
    row("CONTROL: with must_lock off (the default) the same write without a lock goes through", r == (0, 0, b"") and st.records("wf")["a"] == "x", repr(r))
    bye(c, ses)

    # ---- W10  readonly ------------------------------------------------------------------------------------------------------------------
    reset()
    c = connect(readonly=("wf",))
    ses = srv.sessions[-1]
    f1, f2 = opened(c, "wf", "wcs")
    ro = [c.req(t, d) for t, d in ((R_WRITE, W(f1, "a", "x")), (R_WRITEU, W(f1, "a", "x")), (R_DELETE, D(f1, "a")), (R_DELETEU, D(f1, "a")), (R_CLEARFILE, _S(f1)))]
    row("readonly=('wf',): 16, 17, 18 and 19 are ON ERROR with STATUS +3018 and no text, and 31 (CLEARFILE, which has no ON ERROR clause) aborts: ON ERROR, STATUS 0 and the kernel's "
        "text with the program and line - as REAL_ON_ERROR, measured on the real server 19 Oct 26 - and nothing changes",
        all(v == (1, 3018, b"") for v in ro[:4]) and ro[4][:2] == (1, 0) and re.fullmatch(REAL_ON_ERROR["clearfile_readonly"][2], ro[4][2].decode("latin-1")) is not None
        and st.records("wf") == base["wf"], repr((ro, st.records("wf"))))
    rd, rl = c.req(R_READ, _S(f1) + b"a"), c.req(R_READU, _S(f1) + b"a")
    rw = c.req(R_WRITE, W(f2, "n", "x"))
    row("CONTROL: reads and locks on that file still work, and a write to another file goes through",
        rd == (0, 0, b"one") and rl == (0, 0, b"one") and rw == (0, 0, b"") and st.records("wcs").get("n") == "x", repr((rd, rl, rw)))
    bye(c, ses)

    # ---- W11  edit_allow: check.edit by the pathname ------------------------------------------------------------------------------------
    def change_all(cl, fno, rid):
        """The five changing requests on one file: [(reply, the text request 2 gives right after it when the reply is SV$ERROR)]."""
        out_ = []
        for t, d in ((R_WRITE, W(fno, rid, "x")), (R_WRITEU, W(fno, rid, "x")), (R_DELETE, D(fno, rid)), (R_DELETEU, D(fno, rid)), (R_CLEARFILE, _S(fno))):
            r_ = cl.req(t, d)
            out_.append((r_, cl.error_text() if r_[0] == SV_ERROR else None))
        return out_

    def denied(cl, rs, num):
        """Every reply is SV$ERROR with no data and request 2 gave message num right after it."""
        return all(v[0] == (3, 0, b"") and v[1] == msg(num) for v in rs)
    reset()
    c = connect()
    ses = srv.sessions[-1]
    fv, fp, fb, fd, fnp, fok = opened(c, "voc", "ptr", "wbp", "dict wf", "nopath", "wcs")
    rv, rp, rb, rd_, rn = change_all(c, fv, "x"), change_all(c, fp, "q"), change_all(c, fb, "p"), change_all(c, fd, "d1"), change_all(c, fnp, "z")
    row("edit_allow empty (the files-only default): all five changing requests on the VOC are SV$ERROR, request 2 gives 11405, nothing changes",
        denied(c, rv, 11405) and st.records("voc") == base["voc"], repr(rv))
    row("... on a Q-pointer to a VOC (a file called ptr whose PATH ends voc) the same: the gate goes by the pathname", denied(c, rp, 11405) and st.records("ptr") == base["ptr"], repr(rp))
    row("... on a program file (path ends .bp): 11407", denied(c, rb, 11407) and st.records("wbp") == base["wbp"], repr(rb))
    row("... on a dictionary (opened as 'dict wf'): 11406", denied(c, rd_, 11406) and st.file("wf").dict_items == {"d1": "D" + FMc + "1"}, repr(rd_))
    row("... on a file whose path cannot be read: 11410", denied(c, rn, 11410) and st.records("nopath") == base["nopath"], repr(rn))
    rc = change_all(c, fok, "n")
    row("CONTROL: a file of no special kind is changed by an empty edit_allow (write, writeu, delete, deleteu, clear all succeed)",
        all(v[0] == (0, 0, b"") for v in rc) and st.records("wcs") == {}, repr(rc))
    rr = [c.req(R_READ, _S(fv) + b"x"), c.req(R_READ, _S(fb) + b"p"), c.req(R_LOCKRECORD, K(fv, 3, "x"))]
    row("CONTROL: reads and record locks of those files are never gated", rr[0] == (0, 0, b"v") and rr[1] == (0, 0, b"prog") and rr[2] == (0, 0, b""), repr(rr))
    bye(c, ses)
    reset()
    c = connect(edit_allow=frozenset({"voc", "dict", "prog"}))
    ses = srv.sessions[-1]
    fv, fp, fb, fd, fnp = opened(c, "voc", "ptr", "wbp", "dict wf", "nopath")
    rv, rb, rd_ = c.req(R_WRITE, W(fv, "x", "new")), c.req(R_WRITE, W(fb, "p", "new")), c.req(R_WRITE, W(fd, "d2", "new"))
    row("edit_allow=voc, dict, prog: a write to the VOC, a program file and a dictionary goes through (the dictionary item is stored)",
        rv == (0, 0, b"") and rb == (0, 0, b"") and rd_ == (0, 0, b"") and st.records("voc")["x"] == "new" and st.records("wbp")["p"] == "new"
        and st.file("wf").dict_items.get("d2") == "new", repr((rv, rb, rd_)))
    rn = c.req(R_WRITE, W(fnp, "z", "new"))
    row("... but a file whose path cannot be read is still 11410 (the gates do not matter without a path)", rn == (3, 0, b"") and c.error_text() == msg(11410) and st.records("nopath") == base["nopath"], repr(rn))
    bye(c, ses)
    reset()
    c = connect(edit_allow=frozenset({"dict"}))
    ses = srv.sessions[-1]
    fv, fb, fd = opened(c, "voc", "wbp", "dict wf")
    rd_, rv = c.req(R_DELETE, D(fd, "d1")), c.req(R_DELETE, D(fv, "x"))
    rb = c.req(R_CLEARFILE, _S(fb))
    row("edit_allow=dict: the dictionary delete goes through, the VOC (11405) and the program file clear (11407) do not - each kind is its own gate",
        rd_ == (0, 0, b"") and "d1" not in st.file("wf").dict_items and rv == (3, 0, b"") and st.records("voc") == base["voc"] and rb == (3, 0, b"")
        and c.error_text() == msg(11407) and st.records("wbp") == base["wbp"], repr((rd_, rv, rb)))
    bye(c, ses)

    # ---- W12  maxrlock ----------------------------------------------------------------------------------------------------------------
    reset()
    c = connect(maxrlock=2)
    ses = srv.sessions[-1]
    u = ses.userno
    f1, = opened(c, "wf")
    c.req(R_LOCKRECORD, K(f1, 3, "a"))
    c.req(R_LOCKRECORD, K(f1, 2, "b"))
    # AS THE REAL SERVER ANSWERS (REAL_ON_ERROR, measured 19 Oct 26): request 30 has no ON ERROR clause and aborts - STATUS() 0 and the kernel's text with message 11162 in it;
    # a locking READ has the clause - STATUS() +3060 and no text
    want_read = (1, 3060, b"")

    def want_abort(v):
        return v[:2] == (1, 0) and re.fullmatch(REAL_ON_ERROR["lockrecord_maxrlock"][2], v[2].decode("latin-1")) is not None and msg(11162) in v[2].decode("latin-1")
    r = c.req(R_LOCKRECORD, K(f1, 3, "c"))
    row("maxrlock=2: a third NEW lock by request 30 is ON ERROR, STATUS 0 and the abort text '<address>: Record lock limit (MAXRLOCK) reached at line <n> of $apisrvr'",
        want_abort(r) and len(st.locks_of(u)) == 2, repr(r))
    rs = [c.req(R_READU, _S(f1) + b"c"), c.req(R_READL, _S(f1) + b"c"), c.req(R_READUW, _S(f1) + b"c"), c.req(R_READLW, _S(f1) + b"c"),
          c.req(R_READV, _S(f1) + _S(1) + _L(1) + b"c"), c.req(R_READV, _S(f1) + _S(6) + _L(1) + b"c")]
    row("... and by readu, readl, readuw, readlw and readv with a lock flag (requests 9, 7, 10, 8, 41) it is ON ERROR, STATUS +3060 and NO text", all(v == want_read for v in rs) and len(st.locks_of(u)) == 2, repr(rs))
    ru = c.req(R_LOCKRECORD, K(f1, 3, "b"))
    row("CONTROL: a lock the session already holds is not a NEW lock: upgrading b from a read lock to an update lock is allowed", ru == (0, 0, b"") and ("wf", "b", "update") in st.locks_of(u), repr((ru, st.locks_of(u))))
    rp = c.req(R_READ, _S(f1) + b"c")
    row("CONTROL: a plain read takes no lock and is never refused", rp == (0, 0, b"three"), repr(rp))
    st.hold("wf", "c", 7)
    rh = c.req(R_LOCKRECORD, K(f1, 2, "c"))
    row("the count is checked before the lock table: a record someone else holds is refused with the MAXRLOCK abort too, not SV$LOCKED", want_abort(rh), repr(rh))
    st.drop_user(7)
    c.req(R_RELEASE, D(f1, "a"))
    rg = c.req(R_LOCKRECORD, K(f1, 3, "c"))
    row("after one lock is released the third goes through", rg == (0, 0, b"") and len(st.locks_of(u)) == 2, repr((rg, st.locks_of(u))))
    bye(c, ses)
    reset()
    c = connect()
    ses = srv.sessions[-1]
    f1, = opened(c, "wf")
    for rid in "abc":
        c.req(R_LOCKRECORD, K(f1, 3, rid))
    row("CONTROL: with maxrlock off (the default) three locks are taken", len(st.locks_of(ses.userno)) == 3, repr(st.locks_of(ses.userno)))
    bye(c, ses)

    # ---- W13  drop_before and drop_after ----------------------------------------------------------------------------------------------
    reset()
    c = connect(drop_before={R_WRITE: 2}, timeout=3)
    ses = srv.sessions[-1]
    f1, = opened(c, "wf")
    c.req(R_LOCKRECORD, K(f1, 3, "c"))
    r1 = c.req(R_WRITE, W(f1, "x1", "one"))
    r_d = c.req(R_DELETE, D(f1, "b"))
    dropped = gone(c, ses, R_WRITE, W(f1, "x2", "two"))
    row("drop_before={16: 2}: the first write is served, the second is read and recorded and the connection closes - the store is NOT changed",
        r1 == (0, 0, b"") and dropped and "x1" in st.records("wf") and "x2" not in st.records("wf") and ses.injected == [(R_WRITE, "drop_before")]
        and ses.requests.count(R_WRITE) == 2, repr((r1, dropped, ses.injected, ses.requests)))
    row("... and the session's locks went with the connection, as a process's do; a delete (another type) between the writes did not count",
        r_d == (0, 0, b"") and st.locks_of(ses.userno) == [], repr(st.locks_of(ses.userno)))
    c.close()
    reset()
    c = connect(drop_after={R_WRITE: 1}, timeout=3)
    ses = srv.sessions[-1]
    f1, = opened(c, "wf")
    dropped = gone(c, ses, R_WRITE, W(f1, "x1", "one"))
    row("drop_after={16: 1}: the write is EXECUTED (the store has the record) and the connection closes without a reply - the client cannot tell this from drop_before",
        dropped and st.records("wf").get("x1") == "one" and ses.injected == [(R_WRITE, "drop_after")], repr((dropped, st.records("wf"), ses.injected)))
    c.close()
    for ptype, data_of, check, label in (
            (R_WRITEU, lambda f: W(f, "a", "wu"), lambda: st.records("wf")["a"] == "wu", "writeu"),
            (R_DELETE, lambda f: D(f, "a"), lambda: "a" not in st.records("wf"), "delete"),
            (R_DELETEU, lambda f: D(f, "a"), lambda: "a" not in st.records("wf"), "deleteu"),
            (R_CLEARFILE, lambda f: _S(f), lambda: st.records("wf") == {}, "clearfile")):
        reset()
        c = connect(drop_after={ptype: 1}, timeout=3)
        ses = srv.sessions[-1]
        f1, = opened(c, "wf")
        dropped = gone(c, ses, ptype, data_of(f1))
        row("drop_after on %s: executed, then closed with no reply" % label, dropped and check(), repr((dropped, st.records("wf"))))
        c.close()
    reset()
    c = connect(drop_after={R_LOCKRECORD: 1}, timeout=3)
    ses = srv.sessions[-1]
    f1, = opened(c, "wf")
    dropped = gone(c, ses, R_LOCKRECORD, K(f1, 3, "a"))
    row("drop_after on a lock: recorded as injected and the lock goes with the connection", dropped and ses.injected == [(R_LOCKRECORD, "drop_after")]
        and st.locks_of(ses.userno) == [], repr((dropped, ses.injected, st.locks_of(ses.userno))))
    c.close()
    reset()
    c = connect(drop_before={R_DELETE: 1}, timeout=3)
    ses = srv.sessions[-1]
    f1, = opened(c, "wf")
    dropped = gone(c, ses, R_DELETE, D(f1, "a"))
    row("drop_before on a delete: closed, the record is still there", dropped and "a" in st.records("wf") and ses.injected == [(R_DELETE, "drop_before")], repr((dropped, st.records("wf"))))
    c.close()
    reset()
    c = connect(drop_before={R_WRITE: 1}, timeout=3)
    ses = srv.sessions[-1]
    f1, = opened(c, "wf")
    r = c.req(R_DELETE, D(f1, "a"))
    r2 = c.req(R_READ, _S(f1) + b"b")
    row("CONTROL: drop_before names a request TYPE: other requests are served as usual and nothing is dropped", r == (0, 0, b"") and r2 == (0, 0, b"two") and ses.injected == [], repr((r, r2, ses.injected)))
    bye(c, ses)

    # ---- W14  the older fault switches reach the new requests; the files-only gate lets them through ---------------------------------
    reset()
    c = connect(fail={R_WRITE: (1, "boom")})
    ses = srv.sessions[-1]
    f1, = opened(c, "wf")
    r = c.req(R_WRITE, W(f1, "x", "y"))
    row("fail={16: ...}: the write is answered with the injected error and NOT executed", r == (1, 0, b"boom") and "x" not in st.records("wf") and ses.injected == [(R_WRITE, "fail")], repr((r, ses.injected)))
    bye(c, ses)
    c = connect(no_reply=(R_WRITE,), timeout=1)
    ses = srv.sessions[-1]
    f1, = opened(c, "wf")
    try:
        c.req(R_WRITE, W(f1, "x", "y"))
        outcome = "answered"
    except TimeoutError:
        outcome = "timeout"
    except (EOFError, OSError):
        outcome = "closed"
    row("no_reply=(16,): the write is recorded and never answered, and (as for a read) not executed", outcome == "timeout" and ses.requests[-1] == R_WRITE and "x" not in st.records("wf"), repr((outcome, ses.requests)))
    c.close()
    wait_closed(ses)
    reset()
    c = connect(files_only=True, write_group=True)
    ses = srv.sessions[-1]
    f1, f2 = opened(c, "wf", "wtmp")
    rs = [c.req(R_WRITE, W(f1, "fo", "1")), c.req(R_WRITEU, W(f1, "fo", "2")), c.req(R_LOCKRECORD, K(f1, 3, "a")), c.req(R_DELETEU, D(f1, "fo")),
          c.req(R_DELETE, D(f1, "fo")), c.req(R_CLEARFILE, _S(f2)), c.req(R_RELEASE, _S(0))]
    row("files-only: 16, 17, 18, 19, 30 and 31 are all on the gate's allow list and are DISPATCHED (served, none refused); a plain file is of no gated kind",
        all(v == (0, 0, b"") for v in rs) and ses.refused == [] and "fo" not in st.records("wf") and st.records("wtmp") == {}, repr((rs, ses.refused)))
    bye(c, ses)

    # ---- W15  bad_length (19 Oct 26, K8c): a reply that is its header alone, with a length that is not the length that follows, then silence ------------------------------
    for announced in (3000000000, 2000000000, 4):
        reset()
        c = connect(bad_length={R_READ: announced}, bad_length_hold=6.0, timeout=3)
        ses = srv.sessions[-1]
        f1, = opened(c, "wf")
        c.send(R_READ, _S(f1) + b"a")
        hdr = c._rd(10)
        length, err, status = struct.unpack("<IHI", hdr)
        c.tls.settimeout(0.5)
        try:
            more = c.tls.recv(10)
        except (socket.timeout, TimeoutError):
            more = None
        row("bad_length={6: %d}: the reply to a READ is the 10 header bytes alone, announcing %d and error 0 status 0, and then NOTHING (the connection stays open and silent)" % (announced, announced),
            length == announced and (err, status) == (0, 0) and more is None and ses.injected == [(R_READ, "bad_length")] and not ses.closed, repr((length, err, status, more, ses.injected)))
        t0 = time.time()
        c.close()
        row("...and the server lets go as soon as the client closes (inside 4 s, not at the end of its %s second hold)" % 6, wait_closed(ses, 4.0) and time.time() - t0 < 4.0, "")
    reset()
    c = connect(bad_length={R_WRITE: 3000000000}, bad_length_hold=6.0, timeout=3)
    ses = srv.sessions[-1]
    f1, = opened(c, "wf")
    c.send(R_WRITE, W(f1, "bl", "1"))
    hdr = c._rd(10)
    row("bad_length on a WRITE: the write is EXECUTED first (the record is stored) and the reply is the bogus header - the client cannot tell this from a lost reply",
        struct.unpack("<IHI", hdr)[0] == 3000000000 and st.records("wf").get("bl") == "1", repr((hdr, st.records("wf"))))
    c.close()
    wait_closed(ses, 4.0)

    # ---- W12  the write group (18 Oct 26, S.65): a files-only login WITHOUT sdfileswrite is refused every change and lock ---------------------------------
    reset()
    c = connect(files_only=True)
    ses = srv.sessions[-1]
    f1, f2 = opened(c, "wf", "wtmp")
    before = {n: dict(st.records(n)) for n in ("wf", "wtmp")}
    reqs = [("write", R_WRITE, W(f1, "gw", "x")), ("writeu", R_WRITEU, W(f1, "gw2", "x")), ("delete", R_DELETE, D(f1, "a")), ("deleteu", R_DELETEU, D(f1, "b")),
            ("lock record", R_LOCKRECORD, K(f1, 1, "c")), ("clearfile", R_CLEARFILE, _S(f2)), ("readl", R_READL, _S(f1) + b"a"), ("readlw", R_READLW, _S(f1) + b"a"),
            ("readu", R_READU, _S(f1) + b"a"), ("readuw", R_READUW, _S(f1) + b"a"), ("filelock", 32, _S(f1) + _S(0)), ("fileunlock", 33, _S(f1))]
    rs = {name: c.req(pt, data) for name, pt, data in reqs}
    want = {name: (1, 0, msg(11521, pt).encode("latin-1")) for name, pt, data in reqs}
    row("files-only without sdfileswrite: write, writeu, delete, deleteu, lock record, clearfile, readl, readlw, readu, readuw, filelock and fileunlock are each answered with "
        "the ON ERROR reply that carries message 11521 naming the request, and none is dispatched",
        rs == want and ses.refused == [pt for _, pt, _ in reqs], repr({k: v for k, v in rs.items() if v != want[k]}))
    row("... and the store is as it was: no record written, none deleted, nothing cleared, no lock taken (the disk is the evidence)",
        {n: dict(st.records(n)) for n in before} == before and st.locks_of(ses.userno) == [], repr((st.records("wf"), st.records("wtmp"), st.locks_of(ses.userno))))
    r = c.req(R_READV, _S(f1) + _S(1) + _L(1) + b"a")
    row("... readv with a lock flag (1) is refused too, with 11521 naming request 41, and takes no lock",
        r == (1, 0, msg(11521, R_READV).encode("latin-1")) and ses.refused[-1] == R_READV and st.locks_of(ses.userno) == [], repr((r, st.locks_of(ses.userno))))
    rr = [c.req(R_READV, _S(f1) + _S(f) + _L(1) + b"a") for f in (2, 5, 6, 3)]
    row("... and so are readv flags 2, 5, 6 and 3 (apisrvr's vb.readv refuses any nonzero flag)", all(x == (1, 0, msg(11521, R_READV).encode("latin-1")) for x in rr), repr(rr))
    reads = [c.req(R_READ, _S(f1) + b"a"), c.req(R_READV, _S(f1) + _S(0) + _L(1) + b"a"), c.req(R_RECORDLOCKED, _S(f1) + b"a"),
             c.req(R_SELECTLIST, _S(f1)), c.req(R_FILEINFO, _S(f1) + _L(0)), c.req(R_RELEASE, _S(0)), c.req(R_REVISION)]
    row("CONTROL: the same login still reads - read, readv with flag 0, recordlocked, selectlist, fileinfo, release and revision are served, none refused (only the 13 above)",
        all(x[0] == 0 for x in reads) and reads[0][2] == b"one" and len(ses.refused) == len(reqs) + 5, repr((reads, ses.refused)))
    r = c.req(20, b"\x00\x00")
    row("CONTROL: a request that is not allowed to ANY files-only login (20, call) keeps message 11480: the new text is only for the write group",
        r == (1, 0, msg(11480, 20).encode("latin-1")) and r[2] != msg(11521, 20).encode("latin-1"), repr(r))
    bye(c, ses)
    c = connect(files_only=True, write_group=True)
    ses = srv.sessions[-1]
    f1, f2 = opened(c, "wf", "wtmp")
    rs = [c.req(R_READU, _S(f1) + b"a"), c.req(R_WRITE, W(f1, "gw", "x")), c.req(R_DELETE, D(f1, "b")), c.req(R_READV, _S(f1) + _S(1) + _L(1) + b"c"),
          c.req(R_LOCKRECORD, K(f1, 1, "c")), c.req(R_CLEARFILE, _S(f2))]
    row("the same requests from a login IN sdfileswrite (write_group=True): all dispatched, none refused; the record is written, the other deleted, the file cleared",
        all(x[0] == 0 for x in rs) and ses.refused == [] and st.records("wf").get("gw") == "x" and "b" not in st.records("wf") and st.records("wtmp") == {}, repr((rs, ses.refused)))
    bye(c, ses)
    reset()
    c = connect(files_only=False)
    ses = srv.sessions[-1]
    f1, = opened(c, "wf")
    rs = [c.req(R_WRITE, W(f1, "api", "x")), c.req(R_READU, _S(f1) + b"a"), c.req(R_READV, _S(f1) + _S(1) + _L(1) + b"b")]
    row("CONTROL: an sdapi login (not files-only) is untouched by the write group, with write_group off: write, readu and a locking readv are served, none refused",
        all(x[0] == 0 for x in rs) and ses.refused == [] and st.records("wf").get("api") == "x", repr((rs, ses.refused)))
    bye(c, ses)
    reset()
    srv.add_user("dave", "pw-dave", files_only=True, write_group=True)
    srv.add_user("erin", "pw-erin", files_only=True)
    cd = connect(user="dave", pw="pw-dave")
    sesd = srv.sessions[-1]
    fd, = opened(cd, "wf")
    rd = cd.req(R_WRITE, W(fd, "dv", "x"))
    ce = connect(user="erin", pw="pw-erin", files_only=False)
    sese = srv.sessions[-1]
    fe, = opened(ce, "wf")
    re_ = ce.req(R_WRITE, W(fe, "er", "x"))
    row("the group belongs to the USER too (add_user(write_group=...)): dave, files-only and in the group, writes; erin, files-only and not, is refused with 11521",
        rd == (0, 0, b"") and re_ == (1, 0, msg(11521, R_WRITE).encode("latin-1")) and "dv" in st.records("wf") and "er" not in st.records("wf")
        and sesd.files_only and sese.files_only and sesd.write_ok and not sese.write_ok, repr((rd, re_, sesd.write_ok, sese.write_ok)))
    bye(cd, sesd)
    bye(ce, sese)
    reset()
    srv.configure()
    # ---- W13  the dictionary open (18 Oct 26, S.65): the real server's rule, as gpl.bp/apisrvr's vb.open now applies it ------------------------------------------
    # The fake accepted "dict <name>" from the first day; the REAL server did not (the single-argument OPEN looked the VOC for a file called "dict wf", which _voc_ref
    # understands only with an upper case DICT, so a remote dictionary was never opened and every row here passed).  The server now opens a name that begins with the
    # word dict (any case) and one space as OPEN 'DICT', <rest, trimmed>.  These rows pin the fake to that rule, so it cannot be wrong in the other direction.
    reset()
    c = connect(files_only=True)
    ses = srv.sessions[-1]
    rs = [c.req(R_OPEN, n) for n in ("dict wf", "DICT wf", "Dict wf", "dict  wf")]
    items = [c.req(R_READ, _S(i) + b"d1") for i in (1, 2, 3, 4)]
    row("vb.open: \"dict wf\", \"DICT wf\", \"Dict wf\" and \"dict  wf\" (two spaces) each open the dictionary of wf, in four file numbers, and a read of its item d1 through each gives the item",
        [x[:2] for x in rs] == [(0, 0)] * 4 and [x[2] for x in rs] == [_S(1), _S(2), _S(3), _S(4)] and all(x == (0, 0, ("D" + FMc + "1").encode("latin-1")) for x in items),
        repr((rs, items)))
    nots = [c.req(R_OPEN, n) for n in ("dictwf", "dict", "dict nosuch", "dicts wf", "wf dict")]
    row("... and a name that is not that form is a plain file name: \"dictwf\", \"dict\", \"dict nosuch\", \"dicts wf\" and \"wf dict\" are SV$ELSE, no file number",
        all(x[0] == SV_ELSE and x[2] == b"" for x in nots), repr(nots))
    r = c.req(R_READ, _S(1) + b"a")
    row("... and the dictionary's file number holds the dictionary, not the data: its records are the items, so the data record a is not there", r[0] == SV_ELSE, repr(r))
    bye(c, ses)

    # ---- W16  the file locks, requests 32 and 33 (20 Oct 26, S.72) ---------------------------------------------------------------------------------------------
    # The expected values are written from the spec (gpl.bp/apisrvr vb.filelock and vb.fileunlock, gplsrc/op_lock.c op_filelock() and op_flunlock(), op_dio1.c dio_close(),
    # unlock_record()), not from this file's own handlers; sandbox-req29.py section F holds the same facts to a real `sd -Q`.  Every request is printed as it crosses: the session,
    # the request number, the bytes sent, and the reply (error field, STATUS(), data).  The rows use plain numbers and the names SV$LOCKED = 4 and the messages 5268, 11521.
    FL, FU = 32, 33

    def FLK(fno, wait=0):
        return _S(fno) + _S(wait)

    def tx(cl, who, ptype, data):
        rep = cl.req(ptype, data)
        print("      %s sent %d [%s] -> %r" % (who, ptype, data.hex(" "), rep))
        return rep

    reset()
    c1 = connect()
    s1 = srv.sessions[-1]
    c2 = connect(lock_wait=0.5)
    s2 = srv.sessions[-1]
    u1, u2 = s1.userno, s2.userno
    a1, = opened(c1, "wf")
    a2, = opened(c2, "wf")
    row("W16 setup (the null state): two sessions with different user numbers, wf open as file number 1 in each, and NO file lock held by anybody - so a 'held' below is not a pass over nothing",
        u1 != u2 and (a1, a2) == (1, 1) and st.locks_of(u1) == [] and st.locks_of(u2) == [] and st.filelocks == {}, repr((u1, u2, a1, a2, st.filelocks)))

    # -- a free file, and the holder asking again
    r = tx(c1, "c1", FL, FLK(a1))
    row("vb.filelock, wait 0, a free file: error 0, STATUS 0, no data; c1 now holds the file lock and locks_of lists it as (wf, '', file)",
        r == (0, 0, b"") and st.locks_of(u1) == [("wf", "", "file")] and st.filelocks == {"wf": u1}, repr((r, st.locks_of(u1), st.filelocks)))
    r = tx(c1, "c1", FL, FLK(a1))
    row("vb.filelock by the holder again: success (op_filelock: file_lock is mine -> locked_it), still one file lock, still c1's",
        r == (0, 0, b"") and st.locks_of(u1) == [("wf", "", "file")] and st.filelocks == {"wf": u1}, repr((r, st.filelocks)))

    # -- another session: LOCKED with the holder's number; the wait flag
    r = tx(c2, "c2", FL, FLK(a2))
    row("a second session's filelock (wait 0) is SV$LOCKED (4), no data, STATUS() the HOLDER's user number (c1's); c2 holds nothing and the lock is still c1's",
        r == (4, u1, b"") and st.locks_of(u2) == [] and st.filelocks == {"wf": u1}, repr((r, u1, st.filelocks)))
    t0 = time.time()
    r = tx(c2, "c2", FL, FLK(a2, 1))
    el = time.time() - t0
    row("filelock with a wait flag that is not 0 on a file another user holds waits lock_wait (0.5 s) and then gives up with the ON ERROR reply that says so, and the fake notes it (measured %.2f s)" % el,
        r[0] == 1 and r[2].startswith(b"netfake: gave up") and ("held by user %d" % u1).encode() in r[2] and 0.4 <= el < 3.0 and any("gave up" in e for e in srv.errors)
        and st.filelocks == {"wf": u1}, repr((r, el, srv.errors)))
    srv.errors.clear()

    # -- the file lock blocks another session's record lock
    ru = tx(c2, "c2", R_READU, _S(a2) + b"c")
    rl = tx(c2, "c2", R_LOCKRECORD, K(a2, 3, "c"))
    rk2 = tx(c2, "c2", R_RECORDLOCKED, _S(a2) + b"c")
    rk1 = tx(c1, "c1", R_RECORDLOCKED, _S(a1) + b"c")
    row("c1's file lock blocks c2's record lock: readu and request 30 (flags 3, no wait) are SV$LOCKED with STATUS() c1's number; recordlocked gives c2 -3 and c1 3, STATUS() c1's number for both",
        ru == (4, u1, b"") and rl == (4, u1, b"") and rk2 == (0, u1, _L(-3)) and rk1 == (0, u1, _L(3)) and st.locks_of(u2) == [], repr((ru, rl, rk2, rk1)))
    ro = tx(c1, "c1", R_READU, _S(a1) + b"a")
    row("... but c1's own record lock under its own file lock is allowed, and locks_of lists the file lock and the record lock together, sorted ((wf, '', file) first)",
        ro == (0, 0, b"one") and st.locks_of(u1) == [("wf", "", "file"), ("wf", "a", "update")], repr((ro, st.locks_of(u1))))

    # -- fileunlock: 3011, 0, 3012
    r = tx(c2, "c2", FU, _S(a2))
    row("vb.fileunlock by a session that does NOT hold it while another does: SV$OK with STATUS() 3011 (ER$LCK), no data, and the lock is still c1's",
        r == (0, 3011, b"") and st.filelocks == {"wf": u1}, repr((r, st.filelocks)))
    r = tx(c1, "c1", FU, _S(a1))
    row("vb.fileunlock by the holder: SV$OK with STATUS() 0; the file lock is gone and the record lock c1 also holds is not touched",
        r == (0, 0, b"") and st.filelocks == {} and st.locks_of(u1) == [("wf", "a", "update")], repr((r, st.filelocks, st.locks_of(u1))))
    r = tx(c1, "c1", FU, _S(a1))
    row("vb.fileunlock when nobody holds the lock: SV$OK with STATUS() 3012 (ER$NLK), no data", r == (0, 3012, b"") and st.filelocks == {}, repr((r, st.filelocks)))
    ru = tx(c2, "c2", R_READU, _S(a2) + b"c")
    row("CONTROL for the blocking rows: with the file lock let go, the same readu by c2 takes its record lock and reads it (error 0, 'three')",
        ru == (0, 0, b"three") and st.locks_of(u2) == [("wf", "c", "update")], repr((ru, st.locks_of(u2))))
    tx(c2, "c2", R_RELEASE, _S(a2) + b"c")

    # -- a record lock held by another user blocks the file lock (an update lock, then a read lock); the holder's own do not
    r = tx(c2, "c2", FL, FLK(a2))
    row("a record lock held by ANOTHER user blocks the file lock: c2's filelock (wait 0) is SV$LOCKED with STATUS() the record lock owner's number (c1, who holds wf/a); c2 holds no file lock",
        r == (4, u1, b"") and st.locks_of(u2) == [] and st.filelocks == {}, repr((r, st.locks_of(u2), st.filelocks)))
    tx(c1, "c1", R_RELEASE, _S(a1) + b"a")
    r = tx(c2, "c2", FL, FLK(a2))
    row("CONTROL: once c1 lets that record lock go the same filelock succeeds (error 0) and is c2's", r == (0, 0, b"") and st.filelocks == {"wf": u2}, repr((r, st.filelocks)))
    tx(c2, "c2", FU, _S(a2))
    tx(c1, "c1", R_READL, _S(a1) + b"b")
    r = tx(c2, "c2", FL, FLK(a2))
    row("a READ lock held by another user blocks the file lock too: SV$LOCKED, STATUS() c1's number", r == (4, u1, b"") and st.filelocks == {}, repr((r, st.filelocks)))
    tx(c1, "c1", R_RELEASE, _S(a1) + b"b")
    tx(c2, "c2", R_READU, _S(a2) + b"c")
    r = tx(c2, "c2", FL, FLK(a2))
    row("record locks held by the SAME user do not block the file lock: c2 holds wf/c and takes the file lock (error 0)",
        r == (0, 0, b"") and st.locks_of(u2) == [("wf", "", "file"), ("wf", "c", "update")], repr((r, st.locks_of(u2))))
    tx(c2, "c2", FU, _S(a2))
    tx(c2, "c2", R_RELEASE, _S(a2) + b"c")
    row("W16 CONTROL: every lock is gone again (the next rows start from the null state)", st.filelocks == {} and st.locks_of(u1) == [] and st.locks_of(u2) == [], repr((st.filelocks, st.locks_of(u1), st.locks_of(u2))))

    # -- a waiting filelock is woken by the holder's fileunlock
    c3 = connect(lock_wait=5)
    s3 = srv.sessions[-1]
    u3 = s3.userno
    a3, = opened(c3, "wf")
    tx(c1, "c1", FL, FLK(a1))
    box = {}

    def fl_waiter():
        t1 = time.time()
        try:
            box["r"] = c3.req(FL, FLK(a3, 1))
        except Exception as ex_:
            box["r"] = ex_
        box["t"] = time.time() - t1
    th = threading.Thread(target=fl_waiter)
    th.start()
    time.sleep(0.6)
    held_while_waiting = dict(st.filelocks)
    tx(c1, "c1", FU, _S(a1))
    th.join(8)
    print("      c3 sent %d [%s] (waiting) -> %r after %.2f s" % (FL, FLK(a3, 1).hex(" "), box.get("r"), box.get("t", -1)))
    row("filelock with the wait flag on a held file waits, and the holder's fileunlock wakes it: c3 gets it (error 0) after about 0.6 s and holds it",
        held_while_waiting == {"wf": u1} and box.get("r") == (0, 0, b"") and 0.4 <= box.get("t", 0) < 3.0 and st.filelocks == {"wf": u3}, repr((held_while_waiting, box, st.filelocks)))
    tx(c3, "c3", FU, _S(a3))
    bye(c3, s3)

    # -- the lock belongs to the FILE NUMBER that took it: close of that number lets it go, close of another number of the same file does not
    c4 = connect()
    s4 = srv.sessions[-1]
    u4 = s4.userno
    p1, p2 = opened(c4, "wf", "wf")
    row("W16 setup: c4 has wf open twice, as file numbers 1 and 2", (p1, p2) == (1, 2), repr((p1, p2)))
    for first, second, order in ((p1, p2, "number 1, then number 2"), (p2, p1, "number 2, then number 1")):
        ra = tx(c4, "c4", FL, FLK(first))
        rb = tx(c4, "c4", FL, FLK(second))
        rv = tx(c2, "c2", FL, FLK(a2))
        row("filelock through %s of one file: both succeed (the second finds it already c4's), the rival c2 is SV$LOCKED with c4's number" % order,
            ra == (0, 0, b"") and rb == (0, 0, b"") and rv == (4, u4, b"") and st.filelocks == {"wf": u4}, repr((ra, rb, rv, st.filelocks)))
        rc = tx(c4, "c4", R_CLOSE, _S(second))
        rv2 = tx(c2, "c2", FL, FLK(a2))
        row("... closing the file number that did NOT take the lock (number %d) leaves it held: the rival is still SV$LOCKED with c4's number" % second,
            rc == (0, 0, b"") and rv2 == (4, u4, b"") and st.filelocks == {"wf": u4}, repr((rc, rv2, st.filelocks)))
        rd = tx(c4, "c4", R_CLOSE, _S(first))
        rv3 = tx(c2, "c2", FL, FLK(a2))
        row("... closing the file number that TOOK it (number %d) lets it go: the rival gets the lock (error 0) and holds it" % first,
            rd == (0, 0, b"") and rv3 == (0, 0, b"") and st.filelocks == {"wf": u2}, repr((rd, rv3, st.filelocks)))
        tx(c2, "c2", FU, _S(a2))
        p1, p2 = opened(c4, "wf", "wf")
    tx(c4, "c4", FL, FLK(p1))
    rx = tx(c4, "c4", FU, _S(p2))
    row("filelock through number 1, fileunlock through number 2: SV$OK, STATUS() 0 (op_flunlock goes by the user, not the file variable); the lock is gone",
        rx == (0, 0, b"") and st.filelocks == {}, repr((rx, st.filelocks)))
    tx(c4, "c4", FL, FLK(p2))
    tx(c4, "c4", R_CLOSE, _S(p1))
    rv = tx(c2, "c2", FL, FLK(a2))
    row("... locked again through number 2 it belongs to number 2: closing number 1 leaves it held (the rival is SV$LOCKED)", rv == (4, u4, b"") and st.filelocks == {"wf": u4}, repr((rv, st.filelocks)))
    tx(c4, "c4", R_CLOSE, _S(p2))
    rv = tx(c2, "c2", FL, FLK(a2))
    row("... and closing number 2 lets it go", rv == (0, 0, b"") and st.filelocks == {"wf": u2}, repr((rv, st.filelocks)))
    tx(c2, "c2", FU, _S(a2))

    # -- the end of a session lets it go; so does FakeStore.drop_user
    p1, = opened(c4, "wf")
    tx(c4, "c4", FL, FLK(p1))
    rv = tx(c2, "c2", FL, FLK(a2))
    c4.close()
    wait_closed(s4)
    rv2 = tx(c2, "c2", FL, FLK(a2))
    row("a session that ends (its connection closes) lets go of its file lock: before, the rival was SV$LOCKED with c4's number; after, it gets the lock",
        rv == (4, u4, b"") and rv2 == (0, 0, b"") and st.filelocks == {"wf": u2} and st.locks_of(u4) == [], repr((rv, rv2, st.filelocks)))
    tx(c2, "c2", FU, _S(a2))
    wfile = st.file("wf")
    try:
        got = (st.filelock_try(wfile, 7), st.filelock_try(wfile, 8), st.filelock_try(wfile, 7))
    except AttributeError as ex_:          # a store without the method is a failed row, not a stopped self-test
        got = ("no filelock_try", str(ex_))
    row("FakeStore.filelock_try: 0 for the first taker (user 7), the holder's number (7) for another user (8), 0 for the holder asking again", got == (0, 7, 0) and st.filelocks == {"wf": 7}, repr((got, st.filelocks)))
    if got != (0, 7, 0):
        st.hold_file("wf", 7)              # the rows below still run when the row above failed: put the lock there the way a test does
    rv = tx(c2, "c2", FL, FLK(a2))
    st.drop_user(7)
    rv2 = tx(c2, "c2", FL, FLK(a2))
    row("a file lock held by a process that is not a connection is reported by its number, and drop_user lets it go: SV$LOCKED with 7, then the lock is c2's",
        rv == (4, 7, b"") and rv2 == (0, 0, b"") and st.filelocks == {"wf": u2}, repr((rv, rv2, st.filelocks)))
    tx(c2, "c2", FU, _S(a2))

    # -- request 15, RELEASE: file number 0 lets go of every file lock of the session; an empty id lets go of it only through the file number that took it; one record's id does not
    c5 = connect()
    s5 = srv.sessions[-1]
    u5 = s5.userno
    q1, q2 = opened(c5, "wf", "wf")
    b2, = opened(c2, "wtmp")
    q3, = opened(c5, "wtmp")
    tx(c5, "c5", FL, FLK(q1))
    rr = tx(c5, "c5", R_RELEASE, _S(q2))
    rv = tx(c2, "c2", FL, FLK(a2))
    row("release of the file with an empty id through a file number that did NOT take the file lock leaves it held (reply error 0): the rival is SV$LOCKED with c5's number",
        rr == (0, 0, b"") and rv == (4, u5, b"") and st.filelocks == {"wf": u5}, repr((rr, rv, st.filelocks)))
    rr = tx(c5, "c5", R_RELEASE, _S(q1))
    rv = tx(c2, "c2", FL, FLK(a2))
    row("release of the file with an empty id through the file number that TOOK it lets the file lock go: the rival gets it", rr == (0, 0, b"") and rv == (0, 0, b"") and st.filelocks == {"wf": u2}, repr((rr, rv, st.filelocks)))
    tx(c2, "c2", FU, _S(a2))
    tx(c5, "c5", FL, FLK(q1))
    rr = tx(c5, "c5", R_RELEASE, _S(q1) + b"a")
    rv = tx(c2, "c2", FL, FLK(a2))
    row("release of ONE record's id does not touch the file lock: the rival is SV$LOCKED with c5's number", rr == (0, 0, b"") and rv == (4, u5, b"") and st.filelocks == {"wf": u5}, repr((rr, rv, st.filelocks)))
    tx(c2, "c2", FL, FLK(b2))
    rl = tx(c5, "c5", FL, FLK(q3))
    rr = tx(c5, "c5", R_RELEASE, _S(0))
    rv = tx(c2, "c2", FL, FLK(a2))
    rl2 = tx(c5, "c5", FL, FLK(q3))
    row("release with file number 0 lets go of EVERY file lock of the session (c5's on wf) and of no other user's: the rival takes wf, while c2's own lock on wtmp is still c2's (c5 is SV$LOCKED on wtmp with c2's number, before and after)",
        rl == (4, u2, b"") and rr == (0, 0, b"") and rv == (0, 0, b"") and rl2 == (4, u2, b"") and st.filelocks == {"wf": u2, "wtmp": u2}, repr((rl, rr, rv, rl2, st.filelocks)))
    tx(c2, "c2", FU, _S(a2))
    tx(c2, "c2", FU, _S(b2))
    bye(c5, s5)

    # -- the gate: a files-only login without sdfileswrite is refused 32 and 33 with message 11521 (control: one in the group is served)
    cg = connect(files_only=True)
    sg = srv.sessions[-1]
    g1, = opened(cg, "wf")
    rs = [tx(cg, "cg", FL, FLK(g1)), tx(cg, "cg", FU, _S(g1))]
    row("files-only login WITHOUT sdfileswrite: filelock (32) and fileunlock (33) are each the ON ERROR reply with message 11521 naming the request, not dispatched, and no file lock is taken",
        rs == [(1, 0, msg(11521, 32).encode("latin-1")), (1, 0, msg(11521, 33).encode("latin-1"))] and sg.refused == [32, 33] and st.filelocks == {} and st.locks_of(sg.userno) == [],
        repr((rs, sg.refused, st.filelocks)))
    bye(cg, sg)
    cg = connect(files_only=True, write_group=True)
    sg = srv.sessions[-1]
    g1, = opened(cg, "wf")
    rl = tx(cg, "cg", FL, FLK(g1))
    held = dict(st.filelocks)
    ru = tx(cg, "cg", FU, _S(g1))
    row("CONTROL: the same two requests from a files-only login IN sdfileswrite are dispatched and served: filelock error 0 (the lock is the login's), fileunlock STATUS() 0, nothing refused",
        rl == (0, 0, b"") and held == {"wf": sg.userno} and ru == (0, 0, b"") and sg.refused == [] and st.filelocks == {}, repr((rl, held, ru, sg.refused)))
    bye(cg, sg)

    # -- the success STATUS() of filelock is cfg success_status (never to be read by a client); the status of fileunlock is its answer and is not replaced
    cs = connect(success_status=4242)
    ss = srv.sessions[-1]
    z1, = opened(cs, "wf")
    r_lock = tx(cs, "cs", FL, FLK(z1))
    r_again = tx(cs, "cs", FL, FLK(z1))
    r_unl = tx(cs, "cs", FU, _S(z1))
    r_none = tx(cs, "cs", FU, _S(z1))
    tx(c1, "c1", FL, FLK(a1))
    r_other = tx(cs, "cs", FU, _S(z1))
    tx(c1, "c1", FU, _S(a1))
    row("success_status=4242: a successful filelock carries STATUS() 4242 (twice: new, and already ours); fileunlock's answers are NOT replaced: 0 when it was ours, 3012 when nobody held it, 3011 when c1 did",
        r_lock == (0, 4242, b"") and r_again == (0, 4242, b"") and r_unl == (0, 0, b"") and r_none == (0, 3012, b"") and r_other == (0, 3011, b""),
        repr((r_lock, r_again, r_unl, r_none, r_other)))
    tx(c1, "c1", FL, FLK(a1))
    r_busy = tx(cs, "cs", FL, FLK(z1))
    tx(c1, "c1", FU, _S(a1))
    row("... and the LOCKED reply keeps the holder's number in STATUS() (c1's), not 4242", r_busy == (4, u1, b""), repr(r_busy))
    bye(cs, ss)

    # -- a file number that is not open
    r1_ = tx(c1, "c1", FL, FLK(9))
    t1_ = c1.error_text()
    r2_ = tx(c1, "c1", FU, _S(9))
    t2_ = c1.error_text()
    row("a file number that was never opened is SV$ERROR with no data for filelock and for fileunlock, and request 2 returns 5268 each time",
        r1_ == (3, 0, b"") and r2_ == (3, 0, b"") and t1_ == msg(5268) and t2_ == msg(5268), repr((r1_, t1_, r2_, t2_)))

    # -- a file lock does not count toward maxrlock (the limit is on record locks)
    cm = connect(maxrlock=2)
    sm = srv.sessions[-1]
    m1, = opened(cm, "wf")
    tx(cm, "cm", R_READU, _S(m1) + b"a")
    rfl = tx(cm, "cm", FL, FLK(m1))
    rb = tx(cm, "cm", R_READU, _S(m1) + b"b")
    rc = tx(cm, "cm", R_READU, _S(m1) + b"c")
    row("maxrlock=2: one record lock and the file lock, then a second record lock is allowed (the file lock is not counted); the THIRD record lock is refused (+3060, no text): the limit still bites",
        rfl == (0, 0, b"") and rb == (0, 0, b"two") and rc == (1, 3060, b"") and st.locks_of(sm.userno) == [("wf", "", "file"), ("wf", "a", "update"), ("wf", "b", "update")],
        repr((rfl, rb, rc, st.locks_of(sm.userno))))
    bye(cm, sm)

    bye(c1, s1)
    bye(c2, s2)
    row("W16 CONTROL: with every session ended no lock of any kind is left, and the fake noted nothing wrong with the client", st.filelocks == {} and srv.errors == [] and
        all(st.locks_of(s.userno) == [] for s in (s1, s2, s3, s4, s5, sg, ss, sm)), repr((st.filelocks, srv.errors)))
    reset()
    want_chg = _apifilesok_change()
    if want_chg is None:
        print("  [SKIP] gpl.bp/apifilesok is not there: the change set is not compared")
    else:
        row("FILES_CHANGE is gpl.bp/apifilesok's change set (files.chg), number for number, and a subset of FILES_OK", FILES_CHANGE == want_chg and FILES_CHANGE <= FILES_OK,
            repr(sorted(FILES_CHANGE ^ want_chg)))
    row("the copy of message 11521 in this file is the one sdsys/messages holds, and it names the verb that gives the group", msg(11521, 16) == _MSG_COPY[11521].replace("%1", "16")
        and "files-write-on" in msg(11521, 16), repr(msg(11521, 16)))
    row("the fake noted nothing wrong with the client in the write rows", srv.errors == [], repr(srv.errors))


# ---- a connection that hangs, and the sandbox's sd.conf (19 Oct 26, finish 2: the NETWAIT and NETREPLY rows of sandbox-net.py and sandbox-netfile.py) ------------------------------

class HangingListener:
    """A TCP listener on 127.0.0.1 whose accept queue is FULL, so that a further connect() neither completes nor is refused (the SYN is dropped): the connection NETWAIT is for.  Nothing ever
    accepts.  hangs() is the precondition a row depends on, shown by a connect of its own that must time out; on a machine that does not behave so it is False and the row that needed it FAILS (it
    does not pass over nothing).  fill=False leaves the queue empty: hangs() must then say False (the instrument can say no).  The technique is sandbox-opensock.py's."""

    def __init__(self, fill=True):
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(0 if fill else 16)
        self.port = self.sock.getsockname()[1]
        self.keep = []
        for _ in range(6 if fill else 0):
            c = socket.socket()
            c.setblocking(False)
            try:
                c.connect(("127.0.0.1", self.port))
            except BlockingIOError:
                pass
            self.keep.append(c)
            time.sleep(0.1)

    def hangs(self):
        """True when a connect to this listener, given one second, neither completes nor fails."""
        probe = socket.socket()
        probe.settimeout(1)
        try:
            probe.connect(("127.0.0.1", self.port))
            return False             # it completed: the queue is not full
        except socket.timeout:
            return True
        except OSError:
            return False             # refused, or failed at once
        finally:
            probe.close()

    def close(self):
        for c in self.keep:
            try:
                c.close()
            except OSError:
                pass
        self.keep = []
        try:
            self.sock.close()
        except OSError:
            pass


SD_CONF_MARK = "# --- sd.conf lines of the SDNet timeout rows below ---"


def restart_with_conf(box, tool, original, lines):
    """Stop the sandbox's SD, write its sd.conf as ORIGINAL (the text it had) plus LINES below a marker (none: the file as it was), start it again, and say whether SD is running.  A session takes its
    configuration from the shared memory the daemon filled when it STARTED, so a line in sd.conf needs the daemon stopped and started.  tool is sandbox-fromtree.py.  Used by sandbox-net.py and
    sandbox-netfile.py for NETWAIT and NETREPLY; a row that needs the new value must fail when this says False."""
    subprocess.run([sys.executable, tool, box, "stop"], capture_output=True, text=True, errors="replace", timeout=120)
    conf = os.path.join(box, "sd.conf")
    with open(conf, "w") as f:
        f.write(original.rstrip("\n") + "\n" + (SD_CONF_MARK + "\n" + "".join(x + "\n" for x in lines) if lines else ""))
    subprocess.run([sys.executable, tool, box, "start"], capture_output=True, text=True, errors="replace", timeout=180)
    p = subprocess.run([os.path.join(box, "sys", "bin", "sd"), "-status"], capture_output=True, text=True, errors="replace", env=dict(os.environ, SD_CONFIG=conf), timeout=60)
    return re.search(r"(?m)^Started\s+20\d\d-", p.stdout + p.stderr) is not None


def selftest_hanging(row):
    """HangingListener on its own: a full queue hangs a connect, an empty one does not, and a listener with room completes at once."""
    hl, empty = HangingListener(), HangingListener(fill=False)
    free = socket.socket()
    free.bind(("127.0.0.1", 0))
    free.listen(16)
    try:
        t0 = time.time()
        hangs = hl.hangs()
        el = time.time() - t0
        no_hang = empty.hangs()
        c = socket.socket()
        c.settimeout(1)
        try:
            c.connect(("127.0.0.1", free.getsockname()[1]))
            control = True
        except OSError:
            control = False
        finally:
            c.close()
        row("HangingListener: a connect to a listener whose accept queue is FULL neither completes nor is refused within a second (the connection NETWAIT is for); one to a listener with an empty queue "
            "completes (hangs() says False: the instrument can say no), and so does one with room (the control)", hangs and not no_hang and control and 0.9 <= el < 3, repr((hangs, no_hang, control, el)))
    finally:
        hl.close()
        empty.close()
        free.close()


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
        srv = FakeServer(c, k, life=300)
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
        # stall_first: the reply to client-first never comes.  The probe's own wait is long, so the fake holds the connection for 1.5 s and then closes it: the probe sees the close after
        # 1.5 s and not at once (the hold), and the fake saw packet 47 only.  (That the fake lets go as soon as a client gives up first is seen in sandbox-netfile.py, by its "no socket left open" rows.)
        srv.configure(stall_first=1.5)
        m = srv.mark()
        t0 = time.time()
        res = _probe(srv.port, "alice", "pw-one")
        el = time.time() - t0
        srv.settle(quiet=0.3)
        d = srv.delta(m)
        row("stall_first=1.5: the Ack is sent, client-first is read and nothing more is sent; the connection is held and then closed (the probe saw it closed after %.1f s, 1.4 to 4 expected)" % el,
            res[0] == "closed" and 1.4 <= el < 4 and d["types"] == [47] and d["conns"] == 1 and d["errors"] == [], "client saw %r after %.1f s, server saw %r" % (res, el, d))
        srv.configure()
        run("first_error: the error field and text reach the client", "error", cfg={"first_error": (SV_ON_ERROR, "no thanks")}, types=[47])
        run("an iteration count of 5000 is used by both ends", "ok", cfg={"offer_iter": 5000}, types=[47, 48], ok=1, bad=0)
        ex = srv.exchanges[-1]
        row("the exchange record holds the binding shape the client sent and an independent proof check agrees",
            ex["cbind"].startswith(GS2) and ex["verified"] is True and ex["iterations"] == 5000 and len(ex["proof"]) == 32, repr(ex)[:200])
        selftest_files(srv, c, row)
        selftest_writes(srv, row)
        selftest_hanging(row)
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
