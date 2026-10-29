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
#   LK10  the waiter gets the lock and ends once the holder has gone
# NOT HELD HERE: tool.sessions (sandbox-termsafe.py S1-K), the deadlock message 1451 and SYSTEM(1083) (they need two sessions in a deadlock; the free check
# test-lockids-units.py holds them as text), a lock on a file whose PATH holds control bytes.
import os
import re
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
