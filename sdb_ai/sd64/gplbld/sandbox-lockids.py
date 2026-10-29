#!/usr/bin/env python3
#
# sandbox-lockids.py - another session's lock record id reaches GETLOCKS() and LIST.READU escaped (S.88 phase 2, S1 kernel half, of ~/Documents/Audits/TUI/Opus_TUI_Plan.txt).
# No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-lockids.py <dir> [--build] [--strict]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 every row that counts
# passed, 1 a row failed, 2 it could not run.  --strict counts a row of a phase that has not landed as FAILED (tuirows.py).
#
# START-HISTORY:
# 28 Oct 26 dm  New (S.88 phase 2, S1).  Written with the kernel change (op_lock.c: lock_safe_text, getlocks_line); NOT RUN yet - the owner's rule of 28 Oct defers every sandbox
#               run to the one complete run at the end of the full-screen phases.
# 28 Oct 26 dm  S.88 phase 2 review: rows LK6-LK9, PSTAT of a SECOND ordinary session (the waiter) that waits for the planted lock after it EXECUTEd a DISPLAY sentence
#               holding control bytes and set @PSTAT to text holding them: kernel.c dump_status() wrote the command, the waited-for id and @PSTAT raw, and PSTAT printed
#               them on the administrator's terminal.  The rule is op_lock.c's, now shared (show_unsafe_byte(), sd.h).  NOT RUN (the same rule).
# 28 Oct 26 dm  The readers of $IPC: rows PL-ctl0 to PL8.  $IPC is writable by every SD user, so the administrator's planter zzpl (playing the stranger: a
#               sandbox has one OS user) writes S<n> and H<n> under the waiter's number every 50 ms while the waiter is STOPPED (SIGSTOP), and F9999 once;
#               PSTAT USER n, HSM USER n and PROFILER DISPLAY USER 9999 (answers 1 1 1 Q) are captured as BYTES.  pstat, hsm and profiler print every text
#               of the record through kernel(K$SHOW.SAFE, ...); hsm_dump() and prof_dump() write by the same rule (test-ipcsafe-units.py).  NOT RUN.
# END-HISTORY
#
# WHAT IT HOLDS.  An ORDINARY session of the fixture account zzhd (a pipe kept open) takes READU locks in its file zzlf on
#   PLAINID                                              the control: a plain id, which every reader must give back exactly
#   LKOK- ESC ]0;PWNLID BEL | ESC [2JCLRLID DEL CSI(155) x char(200)   the planted id (the file folds case, so the table holds it in upper case)
# and prints its OWN locks from FILEINFO(f, 1039) byte by byte, then waits until bp/zzlkstop2 appears.  The ADMINISTRATOR then
#   - runs a program that prints every zzlf lock GETLOCKS('', 0) gives, its id byte by byte                                          (LK-ctl1, LK2, LK3)
#   - runs LIST.READU WAIT, captured as BYTES (not text: the text capture of sandbox-gates.py takes CSI sequences out)               (LK4)
#   LK1   the holder's own FILEINFO 1039 still holds the raw bytes 27, 7, 127, 155 and 200 (unchanged: a program's own locks)
#   LK2   GETLOCKS() gives the planted id with no byte 0-31, 127, 128-159 or 248-255                                                    [phase 2]
#   LK3   ... the same length as the raw id, every one of those bytes '?' (63) and every other byte, 200 included, as it was               [phase 2]
#   LK4   LIST.READU's bytes hold the plain prefix LKOK- (control) and no ESC ] 0 ; PWNLID and no ESC [ 2 J                              [phase 2]
#   LK5   the holder ends by itself when told to (its locks are given back)
# A second ORDINARY session of zzhd, the WAITER (zzlk3), EXECUTEs  DISPLAY zzcmd- ESC ]0;pwncmd BEL -end  (the last command PSTAT shows), sets @PSTAT to
#   zzps- ESC [2jclrps CSI(155) x char(200) VM tail, prints its user number and waits (READU) for the planted id.  The administrator runs PSTAT USER n, captured as BYTES:
#   LK6-ctl PSTAT's bytes hold the plain parts: zzcmd-, ZZPS- / zzps-, and LKOK- on the record line (the instrument reached the waiter's status record)
#   LK6   no ESC ] 0 ; PWNCMD, no ESC [ 2 J CLRPS, no ESC ] 0 ; PWNLID, no ESC [ 2 J CLRLID and no byte 155 in PSTAT's output                               [phase 2]
#   LK7   the command line is  zzcmd-?]0;pwncmd?-end  (each control byte one '?', case aside)                                                              [phase 2]
#   LK8   the record line holds the id as GETLOCKS gives it (LK3's escaped form)                                                                           [phase 2]
#   LK9   the @PSTAT line is  zzps-?[2jclrps?x<200> tail  - control bytes '?', byte 200 kept, the value mark a space as sheet 492 has it                    [phase 2]
#   PL-ctl0/1 the planter writes S<n> and H<n> and ends when told to;  PL1-ctl PSTAT read the planted S<n>;  PL1 no raw sequence, no byte 155;  PL2 each
#         planted text (command, account, program, line, file, id, @PSTAT) with every byte of the rule one '?';  PL3-ctl / PL3 / PL4 the same for HSM USER n
#         (the name, and ESC c in the calls column);  PL5-ctl / PL5 / PL6 / PL7 the same for PROFILER DISPLAY of F9999 at its three levels;  PL8 F9999 removed
#   LK10  the waiter gets the lock and ends once the holder has gone
# NOT HELD HERE: tool.sessions (sandbox-termsafe.py S1-K), the deadlock message 1451 and SYSTEM(1083) (they need two sessions in a deadlock; the free check
# test-lockids-units.py holds them as text), a lock on a file whose PATH holds control bytes.
import os
import re
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import importlib.util  # noqa: E402
from tuirows import Rows  # noqa: E402


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sh = _load("sandbox_home_for_lockids", "sandbox-home.py")
g = sh.g
R = Rows("lockids")
HD = "zzhd"
UNSAFE = set(range(0, 32)) | {127} | set(range(128, 160)) | set(range(248, 256))


def say(s=""):
    print(s, flush=True)


def bail(msg):
    say("sandbox-lockids: CANNOT RUN - " + msg)
    sys.exit(2)


def acct_dir(a):
    return os.path.join(sh.BOX, "user_accounts", a)


# the id as the program builds it (lower case; the lock table keeps it upper case in a file that folds case)
PLANT = (b"lkok-" + b"\x1b]0;pwnlid\x07|" + b"\x1b[2jclrlid" + bytes([127, 155]) + b"x" + bytes([200]))

ZZLK2 = """   open 'zzlf' to f else
      crt 'ZZLK2 nofile'
      stop
   end
   open 'bp' to bpf else
      crt 'ZZLK2 nobp'
      stop
   end
   id = 'lkok-' : char(27) : ']0;pwnlid' : char(7) : '|' : char(27) : '[2jclrlid' : char(127) : char(155) : 'x' : char(200)
   readu r from f, id else null
   readu r2 from f, 'plainid' else null
   own = fileinfo(f, 1039)
   no = dcount(own, @fm)
   for i = 1 to no
      t = own<i, 2>
      out = ''
      for j = 1 to len(t)
         out := seq(t[j, 1]) : ','
      next j
      crt 'ZZOWN ' : own<i, 1> : ' ' : out
   next i
   crt 'ZZLK2 holding'
   loop
      sleep 1
      read s from bpf, 'zzlkstop2' then exit else null
   repeat
   crt 'ZZLK2 done'
end
"""

ZZGL = """$internal
   locks = getlocks('', 0)
   del locks<1>
   nl = dcount(locks, @fm)
   for i = 1 to nl
      s = locks<i>
      if index(s<1, 2>, 'zzlf', 1) then
         t = s<1, 5>
         out = ''
         for j = 1 to len(t)
            out := seq(t[j, 1]) : ','
         next j
         crt 'ZZGL ' : s<1, 4> : ' ' : out
      end
   next i
   crt 'ZZGL done'
end
"""


# 28 Oct 26 review: the waiter whose status record PSTAT reads (its command, the id it waits for, @PSTAT)
ZZLK3 = """   open 'zzlf' to f else
      crt 'ZZLK3 nofile'
      stop
   end
   execute 'DISPLAY zzcmd-' : char(27) : ']0;pwncmd' : char(7) : '-end'
   @pstat = 'zzps-' : char(27) : '[2jclrps' : char(155) : 'x' : char(200) : @vm : 'tail'
   id = 'lkok-' : char(27) : ']0;pwnlid' : char(7) : '|' : char(27) : '[2jclrlid' : char(127) : char(155) : 'x' : char(200)
   crt 'ZZLK3 user ' : @userno
   crt 'ZZLK3 waiting'
   readu r from f, id else null
   crt 'ZZLK3 got'
   release f, id
end
"""

PSTAT_CMD = b"zzcmd-?]0;pwncmd?-end"
PSTAT_TEXT = b"zzps-?[2jclrps?x" + bytes([200]) + b" tail"

# 28 Oct 26 (the readers of $IPC): the administrator's planter.  $IPC is writable by every SD user, so a record in it is not the kernel's word; this
# program plays the stranger (a sandbox has one OS user) and writes S<n> and H<n> every 50 ms until bp/zzplstop appears (60 s at most), or F<n> once,
# or removes F<n>.  It is $internal for the common block that holds $IPC's file variable (syscom.h ipc.f), as zzgl is for GETLOCKS().
ZZPL = """$internal
program zzpl
$include syscom.h
   args = trim(@sentence)
   kind = field(args, ' ', 4)
   n = field(args, ' ', 5)
   open 'bp' to bpf else
      crt 'ZZPL nobp'
      stop
   end
   esc = char(27)
   srec = '0':@vm:'0':@vm:'0'
   srec<2> = 'zzplcmd-':esc:']0;pwnplc':char(7):'-end'
   srec<3> = 'zzplprog-':esc:'[2jclrpp':@sm:'10':@tm:'7':esc:'[2jclrln'
   srec<4> = '5':@vm:'zzplfile-':esc:']0;pwnplf':char(7):@vm:'zzplid-':esc:'[2jclrpi'
   srec<5> = 'zzplacct-':esc:']0;pwnpla':char(7)
   srec<6> = 'zzplps-':esc:'[2jclrpz':char(155)
   hrec = 'zzplhsm-':esc:'[2jclrph':char(155):@vm:'9':esc:'c':@vm:'2000':@vm:'1':@vm:'2':@vm:'3':@vm:'4'
   frec = 'PROFILE':@vm:'1023':@vm:'1':@vm:'0'
   frec<2> = 'zzplev-':esc:']0;pwnpe':char(7):@vm:'zzplq-':esc:'[2jclrpq':@vm:'zzplp-':esc:'[2jclrpr':char(155):@vm:'12':@vm:'3'
   begin case
      case kind = 'SH'
         crt 'ZZPL writing ' : n
         tries = 0
         loop
            write srec to ipc.f, 'S':n
            write hrec to ipc.f, 'H':n
            read s from bpf, 'zzplstop' then exit else null
            tries += 1
         until tries > 1200
            nap 50
         repeat
         delete ipc.f, 'S':n
         delete ipc.f, 'H':n
         delete bpf, 'zzplstop'
         crt 'ZZPL done'
      case kind = 'F'
         write frec to ipc.f, 'F':n
         crt 'ZZPL planted ' : n
      case kind = 'X'
         delete ipc.f, 'F':n
         crt 'ZZPL removed ' : n
   end case
end
"""

# What the three readers must show of the planted records (each control byte, DEL, C1 byte or mark one '?'), and the raw sequences they must not
PL_S_SAFE = [b"zzplcmd-?]0;pwnplc?-end", b"zzplacct-?]0;pwnpla?", b"zzplprog-?[2jclrpp", b"7?[2jclrln", b"zzplfile-?]0;pwnplf?", b"zzplid-?[2jclrpi",
             b"zzplps-?[2jclrpz?"]
PL_S_RAW = [b"\x1b]0;pwnplc", b"\x1b]0;pwnpla", b"\x1b[2jclrpp", b"\x1b[2jclrln", b"\x1b]0;pwnplf", b"\x1b[2jclrpi", b"\x1b[2jclrpz"]
PL_H_SAFE = [b"zzplhsm-?[2jclrph?", b"9?c"]
PL_H_RAW = [b"\x1b[2jclrph", b"\x1bc"]
PL_F_SAFE = [b"zzplev-?]0;pwnpe?", b"zzplq-?[2jclrpq", b"zzplp-?[2jclrpr?"]
PL_F_RAW = [b"\x1b]0;pwnpe", b"\x1b[2jclrpq", b"\x1b[2jclrpr"]
PL_FUSER = "9999"


def codes(s):
    s = (s or "").strip().strip(",")
    return bytes(int(x) for x in s.split(",")) if s else b""


def upper_ascii(b):
    return bytes((c - 32) if 97 <= c <= 122 else c for c in b)


class Holder:
    """An ORDINARY session on a pipe, kept open, that runs a program (zzlk2, the holder: it stops when bp/zzlkstop2 appears; zzlk3, the waiter: it ends when
    it gets the lock)."""

    def __init__(self, account, prog="zzlk2", label="holder"):
        env = dict(os.environ, SD_CONFIG=os.path.join(sh.BOX, "sd.conf"))
        for k in ("SDTEST_ADMIN", "SSH_CONNECTION", "SSH_TTY"):
            env.pop(k, None)
        self.out = os.path.join(sh.BOX, "%s-lockids.out" % label)
        self.fh = open(self.out, "wb")
        argv = [os.path.join(sh.SYS, "bin", "sd"), "-a" + account]
        self.p = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=self.fh, stderr=subprocess.STDOUT, cwd=acct_dir(account), env=env)
        self.p.stdin.write(("\nTERM 200,9999\nRUN bp %s\nOFF\n" % prog).encode())
        self.p.stdin.flush()
        say("  [%s] argv=%s cwd=%s SDTEST_ADMIN=unset pid=%d stdin: TERM 200,9999 | RUN bp %s | OFF" % (label, argv, acct_dir(account), self.p.pid, prog))

    def raw(self):
        try:
            self.fh.flush()
        except ValueError:          # closed by stop(): the file is complete
            pass
        with open(self.out, "rb") as f:
            return f.read()

    def stop(self):
        try:
            self.p.wait(timeout=20)
            return True
        except subprocess.TimeoutExpired:
            self.p.kill()
            self.p.wait()
            return False
        finally:
            try:
                self.fh.close()
            except OSError:
                pass


def adm_raw(cmds):
    """The administrator's session with the commands on stdin; returns the BYTES it wrote."""
    env = dict(os.environ, SD_CONFIG=os.path.join(sh.BOX, "sd.conf"), SDTEST_ADMIN="1")
    for k in ("SSH_CONNECTION", "SSH_TTY"):
        env.pop(k, None)
    argv = [os.path.join(sh.SYS, "bin", "sd")]
    say("    > [admin, bytes] %s in %s: %s" % (argv, sh.SYS, " | ".join(cmds)))
    body = ("\nTERM 200,9999\n" + "".join(c + "\n" for c in cmds) + "OFF\n").encode()
    p = subprocess.run(argv, input=body, cwd=sh.SYS, env=env, capture_output=True, timeout=300)
    return p.stdout + p.stderr


class Planter:
    """The administrator's session, internal mode (as zzgl runs), in the background: RUN bp zzpl SH n, which writes S<n> and H<n> until told to stop."""

    def __init__(self, user):
        env = dict(os.environ, SD_CONFIG=os.path.join(sh.BOX, "sd.conf"), SDTEST_ADMIN="1")
        for k in ("SSH_CONNECTION", "SSH_TTY"):
            env.pop(k, None)
        self.out = os.path.join(sh.BOX, "planter-lockids.out")
        self.fh = open(self.out, "wb")
        argv = [os.path.join(sh.SYS, "bin", "sd"), "-internal"]
        self.p = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=self.fh, stderr=subprocess.STDOUT, cwd=sh.SYS, env=env)
        self.p.stdin.write(("\nTERM 200,9999\nRUN bp zzpl SH %s\nOFF\n" % user).encode())
        self.p.stdin.flush()
        say("  [planter] argv=%s cwd=%s SDTEST_ADMIN=1 pid=%d stdin: TERM 200,9999 | RUN bp zzpl SH %s | OFF" % (argv, sh.SYS, self.p.pid, user))

    def raw(self):
        try:
            self.fh.flush()
        except ValueError:
            pass
        with open(self.out, "rb") as f:
            return f.read()

    def stop(self):
        g.put(os.path.join(sh.SYS, "bp", "zzplstop"), "stop\n")
        try:
            self.p.wait(timeout=30)
            return True
        except subprocess.TimeoutExpired:
            self.p.kill()
            self.p.wait()
            return False
        finally:
            try:
                self.fh.close()
            except OSError:
                pass


def plant_rows(waiter, user):
    """28 Oct 26, the readers of $IPC (PL rows): records planted in $IPC under the waiter's number, read by PSTAT USER n and HSM USER n while the waiter is
    STOPPED (SIGSTOP: it cannot answer, so the command reads what the planter wrote after its own DELETEU - the planter writes every 50 ms, and a WRITE
    does not wait for another session's record lock), and F9999 read by PROFILER DISPLAY USER 9999 (no process needed: DISPLAY reads the record at once).
    The output is BYTES.  Each reader must show the planted texts with every byte of the one rule as '?' and none of the raw sequences."""
    g.put(os.path.join(sh.SYS, "bp", "zzpl"), ZZPL)
    out = g.adm(["BASIC bp zzpl"], internal=True)
    if not any(re.match(r"^Compiled 1 program\(s\) with no errors", ln) for ln in out):
        bail("zzpl did not compile: " + " | ".join(out[-8:]))
    planter = Planter(user)
    stopped = False
    try:
        for _ in range(40):
            if b"ZZPL writing" in planter.raw() or b"ZZPL no" in planter.raw():
                break
            time.sleep(0.5)
        pr = planter.raw()
        R.row("PL-ctl0 the planter is writing S%s and H%s in $IPC" % (user, user), b"ZZPL writing " + user.encode() in pr, repr(pr[-200:]))
        if b"ZZPL writing" not in pr:
            return
        os.kill(waiter.p.pid, signal.SIGSTOP)
        stopped = True
        say("  the waiter (pid %d) is STOPPED: it cannot answer PSTAT or HSM" % waiter.p.pid)
        ps = adm_raw(["PSTAT USER " + user])
        say("  PSTAT USER %s wrote %d bytes: %r" % (user, len(ps), ps[-900:]))
        hs = adm_raw(["HSM USER " + user])
        say("  HSM USER %s wrote %d bytes: %r" % (user, len(hs), hs[-600:]))
    finally:
        if stopped:
            os.kill(waiter.p.pid, signal.SIGCONT)
            say("  the waiter is running again")
        ended = planter.stop()
        say("  planter output: %r" % planter.raw()[-300:])
    R.row("PL-ctl1 the planter ended by itself when told to, and removed what it wrote", ended and b"ZZPL done" in planter.raw(), repr(planter.raw()[-200:]))
    psu = ps.upper()
    ctl = all(p in psu for p in (b"ZZPLCMD-", b"ZZPLACCT-", b"ZZPLPROG-", b"ZZPLFILE-", b"ZZPLID-", b"ZZPLPS-"))
    R.row("PL1-ctl PSTAT read the PLANTED S%s: ZZPLCMD-, ZZPLACCT-, ZZPLPROG-, ZZPLFILE-, ZZPLID- and ZZPLPS- are all in its output" % user, ctl, "not all in %d bytes" % len(ps))
    hits = [b for b in PL_S_RAW if b.upper() in psu] + ([155] if 155 in ps else [])
    R.row("PL1 PSTAT writes none of the planted record's sequences and no byte 155", ctl and not hits, "raw: %r" % hits, phase=2)
    miss = [t for t in PL_S_SAFE if t.upper() not in psu]
    R.row("PL2 PSTAT shows every planted text with each byte of the rule one '?': command, account, program, line, file, record id, @PSTAT",
          ctl and not miss, "missing %r" % miss, phase=2)
    hsu = hs.upper()
    hctl = b"ZZPLHSM-" in hsu
    R.row("PL3-ctl HSM USER %s read the PLANTED H%s (ZZPLHSM- is in its output)" % (user, user), hctl, "not in %d bytes" % len(hs))
    hits = [b for b in PL_H_RAW if b in hs] + ([155] if 155 in hs else [])
    miss = [t for t in PL_H_SAFE if t not in hs]
    R.row("PL3 HSM writes neither of the planted sequences (ESC [ 2 j in the name, ESC c in the calls column) and no byte 155", hctl and not hits, "raw: %r" % hits, phase=2)
    R.row("PL4 HSM shows the name and the calls column with each byte of the rule one '?' (%r)" % PL_H_SAFE, hctl and not miss, "missing %r" % miss, phase=2)
    # The profile: F9999 planted once; DISPLAY walks down three levels (1, 1, 1) to the lines and quits
    out = g.adm(["RUN bp zzpl F " + PL_FUSER], internal=True)
    planted = any(("ZZPL planted " + PL_FUSER) in ln for ln in out)
    R.row("PL5-ctl the planter wrote F%s" % PL_FUSER, planted, " | ".join(out[-6:]))
    fs = adm_raw(["PROFILER DISPLAY USER " + PL_FUSER, "1", "1", "1", "Q"])
    say("  PROFILER DISPLAY USER %s (answers 1 1 1 Q) wrote %d bytes: %r" % (PL_FUSER, len(fs), fs[-900:]))
    fsu = fs.upper()
    fctl = planted and all(p in fsu for p in (b"ZZPLEV-", b"ZZPLQ-", b"ZZPLP-"))
    R.row("PL5 PROFILER DISPLAY reached the three levels of the planted profile (ZZPLEV-, ZZPLQ-, ZZPLP-)", fctl, "not all in %d bytes" % len(fs))
    hits = [b for b in PL_F_RAW if b in fs] + ([155] if 155 in fs else [])
    miss = [t for t in PL_F_SAFE if t not in fs]
    R.row("PL6 PROFILER DISPLAY writes none of the planted sequences and no byte 155", fctl and not hits, "raw: %r" % hits, phase=2)
    R.row("PL7 PROFILER DISPLAY shows the event, the qualifier and the program with each byte of the rule one '?' (%r)" % PL_F_SAFE, fctl and not miss,
          "missing %r" % miss, phase=2)
    out = g.adm(["RUN bp zzpl X " + PL_FUSER], internal=True)
    R.row("PL8 the planter removed F%s" % PL_FUSER, any(("ZZPL removed " + PL_FUSER) in ln for ln in out), " | ".join(out[-6:]))


def main():
    say("sandbox-lockids: S.88 phase 2 (S1 kernel half) - lock ids of another session.  strict=%s SDBOX_KEYSET=%s" % ("--strict" in sys.argv, os.environ.get("SDBOX_KEYSET", "(unset)")))
    hold = None
    waiter = None
    try:
        sh.setup("sandbox-lockids.py")
        if sh.tkb.failed:
            bail("the sandbox setup did not pass its own row")
        g.put(os.path.join(acct_dir(HD), "bp", "zzlk2"), ZZLK2)
        g.put(os.path.join(acct_dir(HD), "bp", "zzlk3"), ZZLK3)
        out = g.plain(HD, ["CREATE.FILE zzlf", "BASIC bp zzlk2", "BASIC bp zzlk3"])
        n_ok = sum(1 for ln in out if re.match(r"^Compiled 1 program\(s\) with no errors", ln))
        if n_ok != 2:
            bail("zzlk2 / zzlk3 did not compile (%d of 2): %s" % (n_ok, " | ".join(out[-8:])))
        g.put(os.path.join(sh.SYS, "bp", "zzgl"), ZZGL)
        out = g.adm(["BASIC bp zzgl"], internal=True)          # GETLOCKS() is an internal function (as LIST.READU and tool.sessions use it): $internal, sd -internal
        if not any(re.match(r"^Compiled 1 program\(s\) with no errors", ln) for ln in out):
            bail("zzgl did not compile: " + " | ".join(out[-8:]))
        hold = Holder(HD)
        for _ in range(40):
            if b"ZZLK2 holding" in hold.raw() or b"ZZLK2 no" in hold.raw():
                break
            time.sleep(0.5)
        hr = hold.raw()
        say("  holder output: %r" % hr[-400:])
        if b"ZZLK2 holding" not in hr:
            bail("the ordinary holder did not reach 'holding', so no lock exists to read: %r" % hr[-200:])
        raw_up = upper_ascii(PLANT)
        own = [codes(m) for m in re.findall(rb"ZZOWN RU (\S*)", hr)]
        say("  the holder's own locks (FILEINFO 1039): %r" % own)
        R.row("LK-ctl0 the ordinary holder took its two locks and listed them (FILEINFO 1039 gave %d)" % len(own), len(own) == 2, repr(own))
        R.row("LK1 a program's OWN lock ids are still given raw by FILEINFO(f, 1039) (27, 7, 127, 155 and 200 are there)",
              any(all(c in o for c in (27, 7, 127, 155, 200)) for o in own), repr(own))
        out = g.adm(["RUN bp zzgl"], internal=True)
        got = {}
        for ln in out:
            m = re.match(r"^ZZGL (\S+) (\S*)$", ln.strip())
            if m:
                got.setdefault(m.group(1), []).append(codes(m.group(2)))
        say("  GETLOCKS for zzlf, as the administrator: %r" % got)
        ids = got.get("RU", [])
        plain = [i for i in ids if i in (b"PLAINID", b"plainid")]
        R.row("LK-ctl1 GETLOCKS gives the control lock's id exactly (PLAINID)", len(plain) == 1, repr(ids))
        planted = [i for i in ids if i.upper().startswith(b"LKOK-")]
        bad = [c for i in planted for c in i if c in UNSAFE]
        R.row("LK2 GETLOCKS gives the other session's planted id with no control byte, DEL, C1 byte or mark", len(planted) == 1 and not bad,
              "planted %r unsafe bytes %r" % (planted, bad), phase=2 if plain else None)
        want = bytes(63 if c in UNSAFE else c for c in raw_up)
        R.row("LK3 ... the same length as the raw id, each such byte '?' and every other byte (200 included) as the lock table holds it",
              len(planted) == 1 and upper_ascii(planted[0]) == want, "got %r want %r" % (planted, want), phase=2 if plain else None)
        lr = adm_raw(["LIST.READU WAIT"])
        pre = b"LKOK-" in lr.upper()
        say("  LIST.READU wrote %d bytes; the plain prefix LKOK- is there: %s" % (len(lr), pre))
        R.row("LK4-ctl LIST.READU listed the planted lock (its plain prefix LKOK- reached the output)", pre, "not in %d bytes" % len(lr))
        lu = lr.upper()
        hits = [b for b in (b"\x1b]0;PWNLID", b"\x1b[2JCLRLID") if b in lu]
        R.row("LK4 LIST.READU writes no ESC ] 0 ; PWNLID and no ESC [ 2 J of another session's id", pre and not hits, "raw: %r" % hits, phase=2 if pre else None)

        # 28 Oct 26 review: PSTAT of a second session that waits for the planted lock (kernel.c dump_status())
        waiter = Holder(HD, "zzlk3", "waiter")
        for _ in range(40):
            if b"ZZLK3 waiting" in waiter.raw() or b"ZZLK3 no" in waiter.raw():
                break
            time.sleep(0.5)
        time.sleep(1.0)                     # let the READU reach its wait
        wr = waiter.raw()
        say("  waiter output: %r" % wr[-400:])
        mu = re.search(rb"ZZLK3 user (\d+)", wr)
        if b"ZZLK3 waiting" not in wr or not mu or b"ZZLK3 got" in wr:
            bail("the ordinary waiter is not waiting for the planted lock, so PSTAT has nothing to show: %r" % wr[-200:])
        ps = adm_raw(["PSTAT USER " + mu.group(1).decode()])
        psu = ps.upper()
        say("  PSTAT USER %s wrote %d bytes: %r" % (mu.group(1).decode(), len(ps), ps[-900:]))
        ctl_cmd = b"ZZCMD-" in psu
        ctl = b"ZZPS-" in psu and b"LKOK-" in psu
        R.row("LK6-ctl PSTAT reached the waiter's status record: its @PSTAT (zzps-) and the record line (LKOK-) are in the output; command zzcmd- there: %s" % ctl_cmd,
              ctl, "not in %d bytes" % len(ps))
        hits = [b for b in (b"\x1b]0;PWNCMD", b"\x1b[2JCLRPS", b"\x1b]0;PWNLID", b"\x1b[2JCLRLID") if b in psu] + ([155] if 155 in ps else [])
        R.row("LK6 PSTAT writes none of the waiter's sequences (ESC ] 0 ; PWNCMD, ESC [ 2 J CLRPS, ESC ] 0 ; PWNLID, ESC [ 2 J CLRLID) and no byte 155",
              ctl and not hits, "raw: %r" % hits, phase=2 if ctl else None)
        R.row("LK7 the command line is the DISPLAY sentence with each control byte one '?' (%r, case aside)" % PSTAT_CMD,
              PSTAT_CMD.upper() in psu, "not in output", phase=2 if ctl_cmd else None)
        R.row("LK8 the record line holds the waited-for id as GETLOCKS gives it (%r)" % want,
              want.upper() in psu, "not in output", phase=2 if ctl else None)
        R.row("LK9 the @PSTAT line is %r: control bytes '?', byte 200 kept, the value mark a space (sheet 492)" % PSTAT_TEXT,
              PSTAT_TEXT in ps, "not in output", phase=2 if ctl else None)

        # 28 Oct 26: records PLANTED in $IPC under the waiter's number (and F9999), read by PSTAT, HSM and PROFILER DISPLAY
        plant_rows(waiter, mu.group(1).decode())
    finally:
        if hold is not None:
            g.put(os.path.join(acct_dir(HD), "bp", "zzlkstop2"), "stop\n")
            R.row("LK5 the holder ended by itself once told to (its locks were given back)", hold.stop(), "the holder had to be killed")
        if waiter is not None:
            ended = waiter.stop()
            R.row("LK10 the waiter got the lock once the holder had gone, and ended", ended and b"ZZLK3 got" in waiter.raw(), "ended=%s output %r" % (ended, waiter.raw()[-200:]))
        sh.teardown()
    sys.exit(R.finish())


if __name__ == "__main__":
    main()
