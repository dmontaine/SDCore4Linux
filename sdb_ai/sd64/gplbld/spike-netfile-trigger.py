#!/usr/bin/env python3
#
# THIS FILE IS A SPIKE RECORD, NOT A SUITE.  It was written as sandbox-netspike.py and renamed spike-netfile-trigger.py so that it is not a
# registered suite: two of its rows are EXPECTED RED (they are the findings), so it exits 1 by design and must never be in regress.sh.  Run it
# by hand with the name below replaced by this file's.  First run, 17 Oct 26: 70 passed, 2 failed (exactly the two expected-red rows).
#
# sandbox-netspike.py - S.65 stage 1 SPIKE: can remote files be served by a catalogued BASIC trigger subroutine, with no C change?
#                       No install, no sudo.  AN EXPERIMENT, NOT A REGRESSION SUITE: it is not in regress.sh or regress-map.txt.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-netspike.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or absent);
# without it <dir> must already be built.  Exit 0 every row passed, 1 a row failed, 2 it could not run.  Only one private SD can exist on
# a machine (shared memory keys 0x53434c91/92): stop it afterwards with sandbox-fromtree.py <dir> stop.
#
# START-HISTORY:
# 17 Oct 26 dm  New (written by a workflow agent that could not compile or run anything).
#               ***NOT YET RUN*** - the first run is the first evidence.  Read a red row as a possible WRONG EXPECTATION in this file as
#               well as a fault in the tree; every row's name says what was expected and the header below says why, with file:line.
# END-HISTORY
#
# THE QUESTION.  The plan for SDNet stage 1 is that a remote file is served by a catalogued BASIC subroutine called from the kernel's
# file opcodes the way a TRIGGER function is (gplsrc/op_dio3.c call_trigger(), line 2378).  Three things were not known:
#   Q1  can such a subroutine keep a SOCKET in NAMED COMMON, so that one connection serves many separate READ / WRITE statements of one
#       run, and survives from one program to the next in a session?
#   Q2  what happens to that socket when the SERVER has closed the connection, how does the subroutine find out, and how does it make
#       the READ or WRITE fail so that the program's ON ERROR clause runs?
#   Q3  does the trigger's updatable DATA parameter let it replace the record the program receives with text from the network?
# This suite answers them with a plain TCP server of its own (a thread in this process; the client sends one line `REQ R <id>` or
# `REQ W <id> <data>`, the server answers one line `RESP <text>`) and a fixture ORDINARY account (zzspa) holding a dynamic file zzspk
# with the local records a, b, c, s ('local-a' ...) and one trigger, zzspktrg, set with `SET.TRIGGER zzspk zzspktrg READ PRE.WRITE`
# (modes 16 and 1).  The trigger finds the server's port in the environment (ZZSPK_PORT) - a session is an `sd -a<account>` process that
# inherits this suite's environment, as SDTEST_ADMIN does for sandbox-gates.py - so each scenario can aim it at a different port.
#
# THE INSTRUMENTS.  (1) The SERVER counts connections and records every request line with the connection it came on, so "one
# connection" is the server's own count, not the program's.  (2) The programs print one line per operation (OP ... THEN/ELSE/ONERROR/
# WRITTEN) with STATUS() and @TRIGGER.RETURN.CODE read immediately, and the trigger prints TRGIN/TRG lines with the COMMON block's
# contents on entry and exit, so the PROCESS'S view (conns=, calls=, rst=, wst=) can be set beside the server's.  (3) Every scenario
# must reach its END line, or its rows fail (a probe that stopped halfway must not pass), and the plain session is proved ordinary and
# the server proved to answer before any scenario runs.  (4) Every session is ended (the input ends with OFF) and the suite then waits
# for the server to see every client disconnect, and a row says so.
#
# WHAT IS EXPECTED, AND WHY (read from the source; a red row against one of these is a wrong expectation OR a finding):
#
# Q1  COMMON.  op_array.c:71 op_common() looks the block up BY NAME on process.named_common (146-154) and creates it only if absent
#     (157-200); a block is a PROCESS list, not a program's: a second program or a second call links to the same block (202-210).  A
#     program ending decrements the block's ref_ct (k_funcs.c:1275-1280, `case COMMON`) but frees the block only if its name begins with
#     an underscore (AH_AUTO_DELETE, op_array.c:162), so zzspk survives until DELETE.COMMON or the end of the process
#     (kernel.c:565 free_common).  The block starts as ZERO, not unassigned (project note), so the first call's `have` is 0.  A socket
#     assigned to a COMMON element is a SOCK descriptor with a ref count (op_skt.c:580-634); nothing releases it at the end of a program or
#     of a trigger call, so the SAME connection serves every call.  CLOSE.SOCKET (op_skt.c:320-341) and DELETE.COMMON (op_array.c:220-281)
#     both end in k_release(), which closes the socket (k_funcs.c:1329-1332 -> close_skt op_skt.c:1468) and leaves the variable
#     UNASSIGNED - so the suite keeps a separate integer flag (spk.have) and never reads spk.skt unless the flag is set.
#     Expected: one connection for the 3 reads and the write (S1); one connection across two programs of one session (S2); a second
#     SESSION is a second process and a second connection (S3); the block survives a call to ANOTHER subroutine (S1 op 2) and that
#     subroutine sees the same values by linking the same block; DELETE.COMMON closes the socket before the session ends (S9).
# Q2  FAILURE.  call_trigger() resets @TRIGGER.RETURN.CODE to 0 (op_dio3.c:2416-2419), runs the subroutine, and the call FAILED if the
#     code is not INTEGER 0 (2473); a failing trigger prints `Data validation error: <code>` (2474-2483, message 1411) unless the
#     statement has an ON ERROR clause (on_error = op_flags & P_ON_ERROR).
#       WRITE: the pre-write failure sets process.status = -ER_TRIGGER (3022) and goes to exit_op_write (op_dio3.c:1041-1046), which
#       pushes process.status (1152) - negative, so the ON ERROR clause runs (JPZ jumps on >= 0, op_jumps.c:711), STATUS() is 3022, and
#       nothing is written (dh_write is skipped).  Expected: works as the plan needs.
#       READ: the failure does `process.status = -ER_TRIGGER; goto exit_op_read` (1460-1465, directory file 1561-1566) but the LOCAL
#       variable `status`, which is what exit_op_read pushes (1603-1604) and tests (1615), was set to 0 at 1308 and is not touched on this
#       path.  So the READ reports SUCCESS: THEN runs, ON ERROR does NOT, record `r` holds whatever the trigger left (the local record if
#       it failed before replacing it), and the only signs are STATUS() = 3022 (op_misc.c:1598-1613, abs(process.status)) and
#       @TRIGGER.RETURN.CODE.  THE PLAN NEEDS A ONE-LINE C CHANGE HERE (`status = (int16_t)process.status` on the three READ failure
#       paths) OR it must treat a failed remote READ as a read of stale local data.  Two rows say so: one measures what happens, one
#       ("PLAN ROW", marked EXPECTED RED) asserts the behaviour the plan wants.
#     The reason a dead socket is detected: READ.SOCKET waits with select() (op_skt.c:1484-1546, a timeout in milliseconds) and recv()
#     returns 0 for an orderly close -> STATUS() 7013 (ER$SKT.CLOSED), or -1 -> 1008 (ER$FAILED), op_skt.c:754-759; a timeout is 1011
#     (op_skt.c:1526).  WRITE.SOCKET uses send(MSG_NOSIGNAL) (1441), so a dead peer is a status 1008 (1444), never a signal.  The FIRST
#     send into a socket whose peer has closed normally SUCCEEDS (the kernel accepts it and the peer answers RST), so the failure
#     appears at the READ.SOCKET after it (7013); a SECOND reuse of the same dead socket fails at the send (1008).  The trigger does not
#     rely on either: it checks the status of both calls.  Its policy here is to close a failed socket (unless ZZSPK_KEEP=1, which is the
#     measurement of a dead socket held and reused), so the NEXT call makes a new connection.
#     A connect that fails: OPEN.SOCKET returns 0 and STATUS() is 7005 (op_skt.c:531, 545, 552, 560).  With a connect timeout argument
#     (4th argument, seconds) the plain `connect_with_timeout` path is used and NOTHING is printed (529-533); with the argument 0 the
#     other branch runs and, because op_skt.c:106 defines SOCKET_DEBUG, k_error("!Failed to connect: ...") prints a message on the
#     terminal - non-fatal, the '!' prefix (k_error.c:367) - and the program goes on.  The trigger therefore passes 5.
# Q3  DATA.  call_trigger() pushes an ADDR to the READ's target descriptor for an updatable trigger (op_dio3.c:2436-2438; the READ passes
#     updatable=TRUE at 1461), so `data = <text>` in the trigger assigns THROUGH to the program's variable: the program receives the
#     server's text, not the local record.  Expected: yes (S1).
#
# AND THREE FACTS THE PLAN NEEDS, MEASURED HERE (S10):
#     - a READ of an id the local file does not hold NEVER calls the read trigger (op_dio3.c:1468-1470: DHE_RECORD_NOT_FOUND goes to
#       ER_RNF without a trigger; a directory file the same at 1503-1506), so a remote file would need local stand-in records or a C hook.
#       Row "PLAN ROW 2" asserts the wanted behaviour and is EXPECTED RED.
#     - SELECT / READNEXT do not call a trigger at all, so the id list is the local one.
#     - a WRITE of a NEW id calls the pre-write trigger (the local record does not need to exist), and on success the record is ALSO
#       written locally (dh_write follows the trigger, op_dio3.c:1069).
#
# SD STATEMENTS USED (all are used the same way by gpl.bp/sdclient and gpl.bp/setserver):
#     skt = OPEN.SOCKET('127.0.0.1', port, SKT$BLOCKING, 5)          ; fail: skt = 0, STATUS() 7005 (op_skt.c:391-645)
#     void WRITE.SOCKET(skt, request : char(10), SKT$BLOCKING, 5000) ; op_skt.c:1355
#     s = READ.SOCKET(skt, 4096, SKT$BLOCKING, 1500)                 ; milliseconds; op_skt.c:651 (0 would mean wait for ever)
#     CLOSE.SOCKET skt                                               ; op_skt.c:320
#     COMMON /zzspk/ spk.have, spk.skt, spk.conns, spk.calls, spk.rst, spk.wst, spk.keep, spk.last
#     SET.TRIGGER zzspk zzspktrg READ PRE.WRITE                      ; gpl.bp/settrig; modes 16 + 1 (dh_fmt.h:134-140)
#     CATALOG bp zzspktrg LOCAL                                      ; run by the administrator, as sandbox-editgates.py does
#     DELETE.COMMON zzspk                                            ; an ordinary verb (gpl.bp/delcom); the BASIC statement is restricted

import importlib.util
import os
import re
import socket
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("sandbox_gates", os.path.join(HERE, "sandbox-gates.py"))
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

ACCT = "zzspa"
FILE = "zzspk"
passed = failed = red_failed = 0

ER_FAILED, ER_TIMEOUT, ER_TRIGGER, ER_CONNECT, ER_SKT_CLOSED = 1008, 1011, 3022, 7005, 7013

COMMON = "   common /zzspk/ spk.have, spk.skt, spk.conns, spk.calls, spk.rst, spk.wst, spk.keep, spk.last\n"

# ---------------------------------------------------------------------------------------------------------------------------------
# the BASIC programs

TRIGGER = """subroutine zzspktrg(mode, id, data, on.error, fvar)
* zzspktrg - the spike trigger (sandbox-netspike.py).  READ (16): the server's answer replaces the record.  PRE.WRITE (1): the new
* data goes to the server first.  The socket lives in the named common block zzspk, which is a PROCESS list.
$include keys.h
""" + COMMON + """   crt 'TRGIN ':mode:'|':id:'|have=':spk.have:'|conns=':spk.conns:'|calls=':spk.calls
   spk.calls += 1
   spk.rst = 0
   spk.wst = 0
   spk.keep = (env('ZZSPK_KEEP') = '1')
   rc = 0
   gosub do.work
   @trigger.return.code = rc
   crt 'TRG ':mode:'|':id:'|code=':rc:'|have=':spk.have:'|conns=':spk.conns:'|calls=':spk.calls:'|wst=':spk.wst:'|rst=':spk.rst
   return

do.work:
   begin case
      case mode = 16
         req = 'REQ R ':id
      case mode = 1
         req = 'REQ W ':id:' ':convert(@fm:@vm:@sm, '~~~', data)
      case 1
         return
   end case
   if not(spk.have) then
      port = env('ZZSPK_PORT') + 0
      cto = env('ZZSPK_CTO')
      if cto = '' then cto = 5 else cto = cto + 0
      spk.skt = open.socket('127.0.0.1', port, SKT$BLOCKING, cto)
      st = status()
      if st # 0 then
         rc = st
         spk.last = 'open ':st
         return
      end
      spk.have = 1
      spk.conns += 1
   end
   void write.socket(spk.skt, req:char(10), SKT$BLOCKING, 5000)
   spk.wst = status()
   if spk.wst # 0 then
      rc = spk.wst
      gosub do.drop
      return
   end
   resp = ''
   loop
      s = read.socket(spk.skt, 4096, SKT$BLOCKING, 1500)
      st = status()
      if st = 0 then resp := s
   until st # 0 or index(resp, char(10), 1) # 0 repeat
   spk.rst = st
   if st # 0 then
      rc = st
      gosub do.drop
      return
   end
   rline = field(resp, char(10), 1)
   if rline[1,5] # 'RESP ' then
      rc = 9002
      gosub do.drop
      return
   end
   body = rline[6, 9999]
   if body = 'NO' then
      rc = 9001
      return
   end
   if mode = 16 then data = body
   return

do.drop:
   spk.last = 'drop ':rc
   if not(spk.keep) then
      close.socket spk.skt
      spk.have = 0
   end
   return
end
"""

OTHER = """subroutine zzspkoth(msg)
* zzspkoth - ANOTHER subroutine, called between reads: it links the same named common block and reports what it finds.
""" + COMMON + """   junk = 'a local variable of its own'
   msg = 'have=':spk.have:' conns=':spk.conns:' calls=':spk.calls
   return
end
"""

PROBE = """* @@NAME@@ - the probe of sandbox-netspike.py: the operations named in ZZSPK_OPS, one after the other
*   r:<id> READ   w:<id>:<data> WRITE   x: call zzspkoth   l: SELECT the file and list the ids
""" + COMMON + """   open 'zzspk' to f else
      crt 'P open-failed ':status()
      stop
   end
   ops = env('ZZSPK_OPS')
   nops = dcount(ops, ',')
   for ix = 1 to nops
      one = field(ops, ',', ix)
      kind = field(one, ':', 1)
      rid = field(one, ':', 2)
      wdat = field(one, ':', 3)
      shown = rid
      if shown = '' then shown = '-'
      @trigger.return.code = 0
      begin case
         case kind = 'r'
            r = 'UNTOUCHED'
@@READ@@
         case kind = 'w'
            wok = 1
            write wdat to f, rid on error
               wok = 0
               crt 'OP ':ix:' w ':shown:' ONERROR st=':status():' trg=':@trigger.return.code
            end
            if wok then crt 'OP ':ix:' w ':shown:' WRITTEN trg=':@trigger.return.code
         case kind = 'x'
            msg = ''
            call zzspkoth(msg)
            crt 'OP ':ix:' x - OTH ':msg
         case kind = 'l'
            select f to 1
            ids = ''
            loop
               readnext sid from 1 else exit
               ids<-1> = sid
            repeat
            crt 'OP ':ix:' l - LIST ':convert(@fm, ',', ids)
         case 1
            crt 'OP ':ix:' ? - BADOP ':one
      end case
   next ix
   crt 'CM have=':spk.have:' conns=':spk.conns:' calls=':spk.calls:' last=':spk.last
   crt 'END'
end
"""

READ_ONERR = """            read r from f, rid on error
               crt 'OP ':ix:' r ':shown:' ONERROR st=':status():' trg=':@trigger.return.code
            end then
               crt 'OP ':ix:' r ':shown:' THEN [':r:'] st=':status():' trg=':@trigger.return.code:' rst=':spk.rst:' wst=':spk.wst
            end else
               crt 'OP ':ix:' r ':shown:' ELSE st=':status():' trg=':@trigger.return.code
            end"""

READ_PLAIN = """            read r from f, rid then
               crt 'OP ':ix:' r ':shown:' THEN [':r:'] st=':status():' trg=':@trigger.return.code:' rst=':spk.rst:' wst=':spk.wst
            end else
               crt 'OP ':ix:' r ':shown:' ELSE st=':status():' trg=':@trigger.return.code
            end"""

CLEAR = """* zzspkclr - deletes the records a scenario added, leaving a, b, c and s (no trigger mode is set for DELETE)
   open 'zzspk' to f else
      crt 'CLR open-failed'
      stop
   end
   select f to 1
   loop
      readnext sid from 1 else exit
      if sid # 'a' and sid # 'b' and sid # 'c' and sid # 's' then delete f, sid
   repeat
   crt 'CLR done'
end
"""

FIXTURE = """* zzspkfix - the local records, written BEFORE the trigger is set (so no network is needed)
   open 'zzspk' to f else
      crt 'FIX open-failed'
      stop
   end
   write 'local-a' to f, 'a'
   write 'local-b' to f, 'b'
   write 'local-c' to f, 'c'
   write 'local-s' to f, 's'
   crt 'FIX done'
end
"""

SLEEP = """* zzspksl - keeps the session alive for three seconds
   sleep 3
   crt 'SLEPT'
end
"""

PROGRAMS = {
    "zzspktrg": TRIGGER,
    "zzspkoth": OTHER,
    "zzspkp1": PROBE.replace("@@NAME@@", "zzspkp1").replace("@@READ@@", READ_ONERR),
    "zzspkp2": PROBE.replace("@@NAME@@", "zzspkp2").replace("@@READ@@", READ_PLAIN),
    "zzspkclr": CLEAR,
    "zzspkfix": FIXTURE,
    "zzspksl": SLEEP,
}


# ---------------------------------------------------------------------------------------------------------------------------------
# reporting

def say(s=""):
    print(s, flush=True)


def row(name, ok, detail="", red=False):
    """RED marks a PLAN ROW the kernel reading says will fail: it counts as failed (the suite exits 1) and says why."""
    global passed, failed, red_failed
    if ok:
        passed += 1
        say("  [PASS] " + name)
    else:
        failed += 1
        if red:
            red_failed += 1
        say("  [FAIL] " + name + ("   <- " + detail if detail else ""))


def note(s):
    say("      [observed] " + s)


def bail(msg):
    say("sandbox-netspike: CANNOT RUN - " + msg)
    sys.exit(2)


# ---------------------------------------------------------------------------------------------------------------------------------
# the server: one request line in, one answer line out

class Server:
    def __init__(self):
        self.ls = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ls.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.ls.bind(("127.0.0.1", 0))
        self.ls.listen(16)
        self.port = self.ls.getsockname()[1]
        self.lock = threading.Lock()
        self.gen = 0
        self.stopping = False
        self.reset()
        threading.Thread(target=self.accept_loop, daemon=True).start()

    def reset(self, close_after=None, silent=("s",), refuse=("refuse",)):
        with self.lock:
            self.gen += 1
            self.conns = 0
            self.reqs = []          # (connection, number on it, line)
            self.eof = {}           # connection -> when its client closed it
            self.srvclosed = set()  # connections the SERVER closed
            self.leaked = set()     # connections that sat silent for a minute
            self.store = {}
            self.close_after = close_after
            self.silent = set(silent)
            self.refuse = set(refuse)

    def accept_loop(self):
        while not self.stopping:
            try:
                conn, _ = self.ls.accept()
            except OSError:
                return
            with self.lock:
                self.conns += 1
                cid, gen = self.conns, self.gen
            threading.Thread(target=self.handle, args=(conn, cid, gen), daemon=True).start()

    def answer(self, cid, n, line):
        parts = line.split(" ", 3)
        if len(parts) >= 3 and parts[0] == "REQ" and parts[1] == "R":
            if parts[2] in self.silent:
                return None
            return "RESP srv-%s-c%d-n%d" % (parts[2], cid, n)
        if len(parts) >= 3 and parts[0] == "REQ" and parts[1] == "W":
            if parts[2] in self.refuse:
                return "RESP NO"
            self.store[parts[2]] = parts[3] if len(parts) > 3 else ""
            return "RESP OK"
        return "RESP ERR"

    def handle(self, conn, cid, gen):
        n = 0
        buf = b""
        conn.settimeout(60)
        try:
            while True:
                try:
                    d = conn.recv(4096)
                except socket.timeout:
                    with self.lock:
                        if gen == self.gen:
                            self.leaked.add(cid)
                    return
                except OSError:
                    d = b""
                if not d:
                    with self.lock:
                        if gen == self.gen and cid not in self.srvclosed:
                            self.eof[cid] = time.monotonic()
                    return
                buf += d
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    line = line.decode("latin-1")
                    n += 1
                    with self.lock:
                        if gen != self.gen:
                            return
                        self.reqs.append((cid, n, line))
                        reply = self.answer(cid, n, line)
                    if reply is not None:
                        conn.sendall((reply + "\n").encode("latin-1"))
                    if self.close_after and n >= self.close_after:
                        with self.lock:
                            self.srvclosed.add(cid)
                        try:
                            conn.shutdown(socket.SHUT_RDWR)
                        except OSError:
                            pass
                        return
        finally:
            try:
                conn.close()
            except OSError:
                pass

    def settle(self, seconds=6.0):
        """Wait until every connection has been closed by one end; return a copy of what the server saw."""
        end = time.monotonic() + seconds
        while True:
            with self.lock:
                opn = [c for c in range(1, self.conns + 1) if c not in self.eof and c not in self.srvclosed]
                if not opn or time.monotonic() >= end:
                    return {"conns": self.conns, "reqs": list(self.reqs), "eof": dict(self.eof), "srvclosed": set(self.srvclosed),
                            "open": opn, "store": dict(self.store), "leaked": set(self.leaked)}
            time.sleep(0.05)

    def stop(self):
        self.stopping = True
        try:
            self.ls.close()
        except OSError:
            pass


def closed_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


# ---------------------------------------------------------------------------------------------------------------------------------
# running a scenario and reading what the programs printed

OPRE = re.compile(r"^OP (\d+) (\w) (\S+) (\w+)(?: \[([^\]]*)\])?(?: (.*))?$", re.M)
TRGRE = re.compile(r"^TRG (\d+)\|([^|]*)\|code=(\d+)\|have=(\d+)\|conns=(\d+)\|calls=(\d+)\|wst=(\d+)\|rst=(\d+)$", re.M)
TRGINRE = re.compile(r"^TRGIN (\d+)\|([^|]*)\|have=(\S+)\|conns=(\S+)\|calls=(\S+)$", re.M)
CMRE = re.compile(r"^CM have=(\S+) conns=(\S+) calls=(\S+) last=(.*)$", re.M)


class Run:
    pass


def kv(rest):
    return dict(re.findall(r"(\w+)=(\S+)", rest or ""))


def run(srv, label, ops, cmds=("RUN bp zzspkp1",), port=None, keep=False, cto=None, reset=True, **cfg):
    """One session.  Prints the real inputs: the environment the trigger reads, the commands, and the server's settings."""
    if reset:
        srv.reset(**cfg)
    env = {"ZZSPK_OPS": ops, "ZZSPK_PORT": str(srv.port if port is None else port), "ZZSPK_KEEP": "1" if keep else "0"}
    if cto is not None:
        env["ZZSPK_CTO"] = str(cto)
    saved = {k: os.environ.get(k) for k in ("ZZSPK_OPS", "ZZSPK_PORT", "ZZSPK_KEEP", "ZZSPK_CTO")}
    for k in saved:
        os.environ.pop(k, None)
    os.environ.update(env)
    say("\n  == %s ==" % label)
    say("    server 127.0.0.1:%d  close_after=%r silent=%r refuse=%r   env %r" % (srv.port, srv.close_after, sorted(srv.silent),
                                                                                  sorted(srv.refuse), env))
    r = Run()
    r.label = label
    try:
        try:
            out = g.plain(ACCT, ["RUN bp zzspkclr"] + list(cmds))
        except subprocess.TimeoutExpired:
            out = []
            row("%s: the session ended by itself" % label, False, "timed out")
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    r.t_end = time.monotonic()
    r.out = out
    r.text = "\n".join(out)
    r.snap = srv.settle()
    r.ops = [dict(ix=int(m.group(1)), kind=m.group(2), id=m.group(3), word=m.group(4), data=m.group(5), rest=m.group(6) or "",
                  kv=kv(m.group(6))) for m in OPRE.finditer(r.text)]
    r.trg = [tuple(m.groups()) for m in TRGRE.finditer(r.text)]
    r.trgin = [tuple(m.groups()) for m in TRGINRE.finditer(r.text)]
    r.cm = [dict(have=m.group(1), conns=m.group(2), calls=m.group(3), last=m.group(4)) for m in CMRE.finditer(r.text)]
    r.ended = len(re.findall(r"(?m)^END$", r.text))
    r.reqs = [(c, n, line) for c, n, line in r.snap["reqs"]]
    say("    server saw: %d connection(s), requests %r, closed by the server %r, by the client %r"
        % (r.snap["conns"], ["c%d:%s" % (c, l) for c, _n, l in r.reqs], sorted(r.snap["srvclosed"]), sorted(r.snap["eof"])))
    for o in r.ops:
        say("    op %(ix)d %(kind)s %(id)s %(word)s%(d)s %(rest)s" % dict(o, d=(" [%s]" % o["data"]) if o["data"] is not None else ""))
    for t in r.trg:
        say("    trigger exit: mode %s id %s code %s have %s conns %s calls %s wst %s rst %s" % t)
    for c in r.cm:
        say("    process view at the end: %r" % (c,))
    return r


def op(r, i):
    return r.ops[i] if i < len(r.ops) else dict(ix=0, kind="?", id="?", word="MISSING", data=None, rest="", kv={})


def reached_end(r, n=1):
    row("%s: the probe reached its END line%s (a probe that stopped halfway must not pass)" % (r.label, "" if n == 1 else " in each of %d programs" % n),
        r.ended == n, "END lines %d; output tail %r" % (r.ended, r.out[-6:]))


def nothing_open(r):
    row("%s: NO RESOURCE LEFT OPEN - the server saw every connection end (the client closed it at the end of the session, or the "
        "server had closed it)" % r.label, not r.snap["open"] and not r.snap["leaked"], "still open %r, leaked %r" % (r.snap["open"], r.snap["leaked"]))


# ---------------------------------------------------------------------------------------------------------------------------------
# the fixture

def build():
    path = os.path.join(g.BOX, "user_accounts", ACCT)
    g.EXTRA_FIXTURES[ACCT] = ("no", "no")
    path = g.build_account(ACCT)
    for name, text in PROGRAMS.items():
        g.put(os.path.join(path, "bp", name), text)
    out = g.sd(path, ["BASIC bp " + " ".join(PROGRAMS)], admin=True, account=ACCT)
    if not g.has(out, r"^Compiled %d program\(s\) with no errors" % len(PROGRAMS)):
        bail("the %d programs did not compile in %s:\n%s" % (len(PROGRAMS), ACCT, "\n".join(out[-30:])))
    out = g.sd(path, ["CATALOG bp zzspktrg LOCAL", "CATALOG bp zzspkoth LOCAL"], admin=True, account=ACCT)
    if not (g.has(out, r"zzspktrg added to local catalogue") and g.has(out, r"zzspkoth added to local catalogue")):
        bail("zzspktrg and zzspkoth were not catalogued in %s:\n%s" % (ACCT, "\n".join(out[-8:])))
    out = g.sd(path, ["CREATE.FILE " + FILE, "RUN bp zzspkfix"], admin=True, account=ACCT)
    if not g.has(out, r"^FIX done$"):
        bail("the file %s was not made and filled:\n%s" % (FILE, "\n".join(out[-8:])))
    out = g.sd(path, ["SET.TRIGGER %s zzspktrg READ PRE.WRITE" % FILE, "SET.TRIGGER " + FILE], admin=True, account=ACCT)
    text = "\n".join(out)
    row("setup: SET.TRIGGER zzspk zzspktrg READ PRE.WRITE is set and the report names the function and both modes",
        "zzspktrg" in text and "READ" in text and "PRE.WRITE" in text, text[-400:])
    return path


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-netspike.py <dir> [--build]")
    g.BOX = os.path.abspath(args[0])
    g.SYS = os.path.join(g.BOX, "sys")
    g.SD = os.path.join(g.SYS, "bin", "sd")
    say("sandbox-netspike: sandbox %s" % g.BOX)
    if "--build" in sys.argv:
        if os.path.exists(g.BOX) and os.listdir(g.BOX):
            bail("%s is not empty" % g.BOX)
        r = subprocess.run([sys.executable, g.TOOL, g.BOX, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-netspike: built, bootstrap passed")
    elif not os.path.isfile(g.SD):
        bail("%s holds no built sandbox (use --build, or point it at one)" % g.BOX)
    subprocess.run([sys.executable, g.TOOL, g.BOX, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    say("\n--- preparation: an ordinary session is not an administrator, the server answers, the fixture account -------------------")
    g.prepare()
    build()
    f = g.flags(g.plain(ACCT, ["ZZKF"]))
    row("control: a plain session in %s is NOT an administrator (admin=0)" % ACCT, f is not None and f[0] == "0", "KFLAGS line: %r" % (f,))
    if f is None or f[0] != "0":
        bail("the plain session is an administrator (or printed nothing): every row below would be meaningless")

    srv = Server()
    try:
        # the instrument: the server itself, asked by Python (so a row that sees no answer later is not a dead server)
        c = socket.create_connection(("127.0.0.1", srv.port), 5)
        c.sendall(b"REQ R probe\n")
        c.settimeout(5)
        got = c.recv(100)
        c.close()
        row("control: the test server answers a request line itself (RESP srv-probe-c1-n1)", got == b"RESP srv-probe-c1-n1\n", repr(got))
        srv.settle(2)

        # ---- S1 -------------------------------------------------------------------------------------------------------------
        say("\n--- S1: three reads, a call to ANOTHER subroutine, a write, in ONE run (Q1, Q3, and the write side of Q2) ---------------")
        r = run(srv, "S1", "r:a,x:,r:b,r:c,w:w1:newdata,l:")
        reached_end(r)
        row("Q1  THREE READS AND A WRITE IN ONE RUN MAKE ONE CONNECTION: the server accepted 1", r.snap["conns"] == 1, "server saw %d" % r.snap["conns"])
        row("Q1  ...and exactly the requests, in order, all on that connection: REQ R a, REQ R b, REQ R c, REQ W w1 newdata",
            [l for _c, _n, l in r.reqs] == ["REQ R a", "REQ R b", "REQ R c", "REQ W w1 newdata"] and {c for c, _n, _l in r.reqs} == {1},
            repr(r.reqs))
        row("Q1  the PROCESS'S view agrees: the trigger made 1 connection in 4 calls and holds it at the end (have=1)",
            len(r.cm) == 1 and r.cm[0]["have"] == "1" and r.cm[0]["conns"] == "1" and r.cm[0]["calls"] == "4", repr(r.cm))
        row("Q1  COMMON STARTS AS ZERO, NOT UNASSIGNED: the first call saw have=0 conns=0 calls=0 (and did not stop with 'Unassigned variable')",
            bool(r.trgin) and r.trgin[0][2:] == ("0", "0", "0"), repr(r.trgin[:1]))
        row("Q1  and the second call saw the block as the first left it: have=1 conns=1 calls=1",
            len(r.trgin) > 1 and r.trgin[1][2:] == ("1", "1", "1"), repr(r.trgin[:2]))
        row("Q3  THE PROGRAM RECEIVES THE SERVER'S TEXT: READ a, b, c gave srv-a-c1-n1, srv-b-c1-n2, srv-c-c1-n3 (the trigger replaced the record)",
            [op(r, i)["data"] for i in (0, 2, 3)] == ["srv-a-c1-n1", "srv-b-c1-n2", "srv-c-c1-n3"] and
            all(op(r, i)["word"] == "THEN" and op(r, i)["kv"].get("trg") == "0" for i in (0, 2, 3)),
            repr([(op(r, i)["word"], op(r, i)["data"], op(r, i)["kv"].get("trg")) for i in (0, 2, 3)]))
        row("Q3  ...and NOT the local record (the control: the file holds local-a, local-b, local-c, and none of them reached the program)",
            not any(("local-" + x) in r.text for x in "abc"), "a local record text appears in the output")
        row("Q1  THE HANDLE SURVIVES A CALL TO ANOTHER SUBROUTINE between the reads: zzspkoth, linking the same block, saw have=1 conns=1 calls=1, "
            "and read b used the SAME connection (c1, not c2)",
            op(r, 1)["word"] == "OTH" and kv(op(r, 1)["rest"]) == {"have": "1", "conns": "1", "calls": "1"} and "c1-n2" in (op(r, 2)["data"] or ""),
            repr((op(r, 1)["rest"], op(r, 2)["data"])))
        row("Q2 (write side)  A WRITE REACHES THE SERVER and completes with no ON ERROR: 'REQ W w1 newdata' was received and stored, trg=0",
            op(r, 4)["word"] == "WRITTEN" and op(r, 4)["kv"].get("trg") == "0" and r.snap["store"] == {"w1": "newdata"},
            repr((op(r, 4), r.snap["store"])))
        ids = set(op(r, 5)["rest"].split(","))
        row("a successful PRE.WRITE trigger is followed by the LOCAL write, so w1 is now in the local file too (SELECT lists a, b, c, s and w1)",
            ids == {"a", "b", "c", "s", "w1"}, repr(ids))
        eof = r.snap["eof"].get(1)
        row("Q1  the connection was closed by the END OF THE PROCESS (the common block is freed with it, kernel.c:565): the server saw EOF within 2 s "
            "of the session returning", eof is not None and (r.t_end - eof) < 2.0, "eof %r, session end %r" % (eof, r.t_end))
        nothing_open(r)

        # ---- S2 -------------------------------------------------------------------------------------------------------------
        say("\n--- S2: two DIFFERENT programs in ONE session (Q1, across programs) ------------------------------------------------------")
        r = run(srv, "S2", "r:a,r:b", cmds=("RUN bp zzspkp1", "RUN bp zzspkp2"))
        reached_end(r, 2)
        row("Q1  THE CONNECTION PERSISTS FROM ONE PROGRAM TO THE NEXT: the server accepted 1 connection for four reads by two programs",
            r.snap["conns"] == 1 and len(r.reqs) == 4, "connections %d, requests %r" % (r.snap["conns"], r.reqs))
        row("Q1  the second program's reads are requests 3 and 4 of that connection (srv-a-c1-n3, srv-b-c1-n4); the first program's are n1 and n2",
            [op(r, i)["data"] for i in range(4)] == ["srv-a-c1-n1", "srv-b-c1-n2", "srv-a-c1-n3", "srv-b-c1-n4"],
            repr([op(r, i)["data"] for i in range(4)]))
        row("Q1  the second program found the socket already held: its process view is have=1 conns=1 calls=4",
            len(r.cm) == 2 and (r.cm[1]["have"], r.cm[1]["conns"], r.cm[1]["calls"]) == ("1", "1", "4"), repr(r.cm))
        nothing_open(r)

        # ---- S3 -------------------------------------------------------------------------------------------------------------
        say("\n--- S3: a second SESSION (a new process) ---------------------------------------------------------------------------------")
        r1 = run(srv, "S3 first session", "r:a")
        r2 = run(srv, "S3 second session", "r:a", reset=False)
        reached_end(r1)
        reached_end(r2)
        row("Q1  A SECOND SESSION IS A SECOND CONNECTION: the server accepted 2 in all; the second session's read was request 1 of connection 2",
            r2.snap["conns"] == 2 and op(r1, 0)["data"] == "srv-a-c1-n1" and op(r2, 0)["data"] == "srv-a-c2-n1",
            repr((r2.snap["conns"], op(r1, 0)["data"], op(r2, 0)["data"])))
        row("Q1  ...and each session's own count is 1 (the block is per process)",
            r1.cm and r2.cm and r1.cm[0]["conns"] == "1" and r2.cm[0]["conns"] == "1", repr((r1.cm, r2.cm)))
        nothing_open(r2)

        # ---- S4 -------------------------------------------------------------------------------------------------------------
        say("\n--- S4: THE SERVER CLOSES after its 2nd request, then the program reads again, with an ON ERROR clause (Q2, read side) ---")
        r = run(srv, "S4", "r:a,r:b,r:c,r:a", close_after=2)
        reached_end(r)
        c3 = op(r, 2)
        code = c3["kv"].get("trg")
        note("third READ: %r" % (c3,))
        row("Q2  after the server closed the connection the NEXT call finds out: the trigger's code is 7013 (ER$SKT.CLOSED, READ.SOCKET got 0 bytes) "
            "or 1008 (ER$FAILED)", code in (str(ER_SKT_CLOSED), str(ER_FAILED)), "trg=%r" % code)
        row("Q2  EXPECTATION (op_skt.c:1441, 754): the first send into the closed peer SUCCEEDS (wst=0) and the failure is at READ.SOCKET (rst=7013)",
            c3["kv"].get("wst") == "0" and c3["kv"].get("rst") == str(ER_SKT_CLOSED), "wst=%r rst=%r" % (c3["kv"].get("wst"), c3["kv"].get("rst")))
        row("Q2  STATUS() in the program after the failed READ is 3022 (ER$TRIGGER: process.status = -ER_TRIGGER, op_dio3.c:1462)",
            c3["kv"].get("st") == str(ER_TRIGGER), "st=%r" % c3["kv"].get("st"))
        row("Q2  MEASURED, as op_dio3.c:1460-1465 and 1603 predict: the failed READ takes THEN, NOT ON ERROR (the local status is 0), and the program "
            "is left with the LOCAL record text 'local-c' - a stale read, not an error", c3["word"] == "THEN" and c3["data"] == "local-c",
            "branch %r data %r" % (c3["word"], c3["data"]))
        row("PLAN ROW 1  [EXPECTED RED: op_dio3.c:1461-1464 never sets the local status] a READ whose trigger fails runs the ON ERROR clause",
            c3["word"] == "ONERROR", "branch %r, STATUS() %r, trg %r - the plan needs 'status = process.status' on the READ trigger failure "
            "paths (dynamic file 1462, directory file 1563)" % (c3["word"], c3["kv"].get("st"), code), red=True)
        row("Q2  a failing trigger does NOT end the program, and the trigger closed the dead socket, so the NEXT READ reconnects: the 4th operation "
            "is request 1 of connection 2 (srv-a-c2-n1) and the process made 2 connections",
            op(r, 3)["word"] == "THEN" and op(r, 3)["data"] == "srv-a-c2-n1" and r.snap["conns"] == 2 and r.cm and r.cm[0]["conns"] == "2",
            repr((op(r, 3), r.snap["conns"], r.cm)))
        row("Q2  the server never saw the request that went into the closed connection (REQ R c is not in its log)",
            [l for _c, _n, l in r.reqs] == ["REQ R a", "REQ R b", "REQ R a"], repr(r.reqs))
        nothing_open(r)

        say("\n--- S4b: the same, with NO ON ERROR clause (what the user sees) ---------------------------------------------------------")
        r = run(srv, "S4b", "r:a,r:b,r:c", cmds=("RUN bp zzspkp2",), close_after=2)
        reached_end(r)
        m = re.search(r"Data validation error:\s*(\d+)", r.text)
        row("Q2  with no ON ERROR clause the kernel prints 'Data validation error: <code>' (op_dio3.c:2474-2483, message 1411) with the trigger's code",
            m is not None and m.group(1) in (str(ER_SKT_CLOSED), str(ER_FAILED)), "message %r, tail %r" % (m and m.group(0), r.out[-6:]))
        row("Q2  ...and the program CARRIES ON as if the READ had worked (THEN, local text): the message is the only sign",
            op(r, 2)["word"] == "THEN" and op(r, 2)["data"] == "local-c" and r.ended == 1, repr(op(r, 2)))
        nothing_open(r)

        # ---- S4w ------------------------------------------------------------------------------------------------------------
        say("\n--- S4w: the server closes after EACH request; a failing WRITE (Q2, write side) ---------------------------------------")
        r = run(srv, "S4w", "r:a,r:b,r:c,w:w1:x,l:", close_after=1)
        reached_end(r)
        wr = op(r, 3)
        note("the write: %r" % (wr,))
        row("Q2  a PRE.WRITE trigger that fails makes the WRITE take ON ERROR: STATUS() 3022 and the trigger's code 7013 or 1008",
            wr["word"] == "ONERROR" and wr["kv"].get("st") == str(ER_TRIGGER) and wr["kv"].get("trg") in (str(ER_SKT_CLOSED), str(ER_FAILED)), repr(wr))
        ids = set(op(r, 4)["rest"].split(","))
        row("Q2  ...and the record was NOT written locally (SELECT lists a, b, c, s and no w1)", ids == {"a", "b", "c", "s"}, repr(ids))
        row("Q2  the reads: a on connection 1; b into the closed connection FAILED (trigger code 7013 or 1008); c on a NEW connection (srv-c-c2-n1)",
            op(r, 0)["data"] == "srv-a-c1-n1" and op(r, 1)["kv"].get("trg") in (str(ER_SKT_CLOSED), str(ER_FAILED)) and op(r, 2)["data"] == "srv-c-c2-n1",
            repr([(op(r, i)["data"], op(r, i)["kv"].get("trg")) for i in range(3)]))
        row("Q2  the process made 2 connections and the server received only the two requests that reached a live connection",
            r.snap["conns"] == 2 and [l for _c, _n, l in r.reqs] == ["REQ R a", "REQ R c"], repr((r.snap["conns"], r.reqs)))
        nothing_open(r)

        # ---- S5 -------------------------------------------------------------------------------------------------------------
        say("\n--- S5: the SERVER REFUSES a write (an answer, not a dead connection) ---------------------------------------------------")
        r = run(srv, "S5", "w:refuse:zzz,w:w2:okdata,l:")
        reached_end(r)
        row("Q2  a server that answers NO makes the WRITE take ON ERROR with the trigger's own code (9001) and STATUS() 3022",
            op(r, 0)["word"] == "ONERROR" and op(r, 0)["kv"].get("trg") == "9001" and op(r, 0)["kv"].get("st") == str(ER_TRIGGER), repr(op(r, 0)))
        ids = set(op(r, 2)["rest"].split(","))
        row("Q2  the refused record was not written locally; the next write (accepted) was, and on the SAME connection (a refusal costs no connection)",
            op(r, 1)["word"] == "WRITTEN" and ids == {"a", "b", "c", "s", "w2"} and r.snap["conns"] == 1, repr((op(r, 1)["word"], ids, r.snap["conns"])))
        nothing_open(r)

        # ---- S6 -------------------------------------------------------------------------------------------------------------
        say("\n--- S6: a DEAD socket held and REUSED (ZZSPK_KEEP=1: the trigger does not close it) --------------------------------------")
        r = run(srv, "S6", "r:a,r:b,r:c", keep=True, close_after=1)
        reached_end(r)
        b, c = op(r, 1), op(r, 2)
        note("first reuse %r" % (b,))
        note("second reuse %r" % (c,))
        row("Q2  the first reuse of a socket whose peer closed is detected: trigger code 7013 or 1008",
            b["kv"].get("trg") in (str(ER_SKT_CLOSED), str(ER_FAILED)), repr(b))
        row("Q2  the SECOND reuse is detected too, and does not kill the process with SIGPIPE (op_skt.c:1441 MSG_NOSIGNAL): code 1008 expected "
            "(the send itself fails, EPIPE); 7013 would also be a detection", c["kv"].get("trg") in (str(ER_FAILED), str(ER_SKT_CLOSED)) and r.ended == 1, repr(c))
        row("a held dead socket is NEVER replaced by this policy: the process made 1 connection and still holds it (have=1)",
            r.snap["conns"] == 1 and r.cm and r.cm[0]["have"] == "1" and r.cm[0]["conns"] == "1", repr((r.snap["conns"], r.cm)))
        nothing_open(r)

        # ---- S7 -------------------------------------------------------------------------------------------------------------
        say("\n--- S7: a trigger that CANNOT CONNECT (a closed port) ---------------------------------------------------------------------")
        dead = closed_port()
        r = run(srv, "S7 connect timeout 5", "r:a,r:b", port=dead)
        reached_end(r)
        row("Q2  a closed port fails the READ cleanly: OPEN.SOCKET gives 0 and STATUS() 7005 (ER$CONNECT), which is the trigger's code; the program "
            "goes on with the local text ('local-a') and STATUS() 3022",
            all(op(r, i)["kv"].get("trg") == str(ER_CONNECT) and op(r, i)["data"] == "local-" + "ab"[i] and op(r, i)["kv"].get("st") == str(ER_TRIGGER)
                for i in (0, 1)), repr(r.ops[:2]))
        row("Q2  the process made no connection and holds none (conns=0 have=0 calls=2), and the server saw nothing",
            r.cm and (r.cm[0]["conns"], r.cm[0]["have"], r.cm[0]["calls"]) == ("0", "0", "2") and r.snap["conns"] == 0, repr((r.cm, r.snap["conns"])))
        row("Q2  with a connect TIMEOUT argument nothing is printed on the terminal (op_skt.c:529-533)", "Failed to connect" not in r.text, r.text[-300:])
        r = run(srv, "S7b connect timeout 0", "r:a", port=dead, cto=0)
        reached_end(r)
        row("Q2  WITHOUT a connect timeout (argument 0) OPEN.SOCKET prints 'Failed to connect' on the terminal - non-fatal - because op_skt.c:106 "
            "defines SOCKET_DEBUG (op_skt.c:560-562); the READ still fails the same way (code 7005)",
            "Failed to connect" in r.text and op(r, 0)["kv"].get("trg") == str(ER_CONNECT), r.text[-400:])

        # ---- S8 -------------------------------------------------------------------------------------------------------------
        say("\n--- S8: the answer never comes (the server is silent for the id s) ------------------------------------------------------")
        r = run(srv, "S8", "r:a,r:s,r:a")
        reached_end(r)
        row("Q2  an answer that does not come fails the READ after the read timeout (1.5 s): code 1011 (ER$TIMEOUT), local text, STATUS() 3022",
            op(r, 1)["kv"].get("trg") == str(ER_TIMEOUT) and op(r, 1)["data"] == "local-s" and op(r, 1)["kv"].get("st") == str(ER_TRIGGER), repr(op(r, 1)))
        row("Q2  the trigger dropped that connection (a late answer would be taken for the next request's), so the next READ is on connection 2",
            op(r, 2)["data"] == "srv-a-c2-n1" and r.snap["conns"] == 2, repr((op(r, 2)["data"], r.snap["conns"])))
        nothing_open(r)

        # ---- S9 -------------------------------------------------------------------------------------------------------------
        say("\n--- S9: DELETE.COMMON closes the socket while the session goes on ---------------------------------------------------------")
        r = run(srv, "S9", "r:a", cmds=("RUN bp zzspkp1", "DELETE.COMMON zzspk", "RUN bp zzspksl"))
        row("%s: the sleeper ran (the session lasted 3 s after DELETE.COMMON)" % r.label, "SLEPT" in r.text, r.text[-300:])
        eof = r.snap["eof"].get(1)
        row("Q1  DELETE.COMMON zzspk (a verb, after the program ended) closed the socket: the server saw EOF at least 2.5 s BEFORE the session ended "
            "(the control is S1, where it saw EOF within 2 s of the end)", eof is not None and (r.t_end - eof) >= 2.5,
            "eof %r, session end %r, lag %s" % (eof, r.t_end, None if eof is None else round(r.t_end - eof, 2)))
        nothing_open(r)

        # ---- S10 ------------------------------------------------------------------------------------------------------------
        say("\n--- S10: what the trigger does NOT reach (facts the plan needs) -------------------------------------------------------------")
        r = run(srv, "S10", "r:nosuch,l:,r:a")
        reached_end(r)
        row("MEASURED  a READ of an id the local file does not hold takes ELSE and NEVER reaches the trigger: the server's only request is REQ R a "
            "(op_dio3.c:1468-1470)", op(r, 0)["word"] == "ELSE" and [l for _c, _n, l in r.reqs] == ["REQ R a"], repr((op(r, 0), r.reqs)))
        row("PLAN ROW 2  [EXPECTED RED: dh_read reports 'not found' before the trigger is considered] a READ of an id only the SERVER holds "
            "reaches the server", any(l == "REQ R nosuch" for _c, _n, l in r.reqs), "the server saw %r" % ([l for _c, _n, l in r.reqs],), red=True)
        ids = set(op(r, 1)["rest"].split(","))
        row("MEASURED  SELECT / READNEXT call no trigger: the list is the LOCAL ids (a, b, c, s) and the server saw no request for it",
            ids == {"a", "b", "c", "s"}, repr(ids))
        nothing_open(r)
    finally:
        srv.stop()

    if red_failed:
        say("\nsandbox-netspike: %d of the failures are rows marked EXPECTED RED: the kernel reading says the plan needs a C change there "
            "(op_dio3.c READ failure paths, and the not-found READ); they are findings, not faults of the suite" % red_failed)
    say("\nsandbox-netspike: %d passed, %d failed" % (passed, failed))
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
