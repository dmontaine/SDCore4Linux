#!/usr/bin/env python3
#
# sandbox-tk-phase0.py - Phase 0 MEASUREMENTS P3, P4 and P7 of the full-screen toolkit plan (.claude/plan-fullscreen-toolkit.md, section 3).  No install, no sudo.
#
#   SDBOX_KEYSET=<n> python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-tk-phase0.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent).  Exit 0 every probe ran and printed its
# numbers, 1 a probe did not, 2 it could not run.  THESE ARE MEASUREMENTS, NOT TESTS: no row passes or fails on a number; a probe fails only when it did not reach
# what it claims to measure (its own line never appeared), and the numbers are for PROJECT_STATUS.
#
# START-HISTORY:
# 21 Oct 26 dm  New (Phase 0 of the toolkit, one sitting; questions P3, P4, P7; P1 is a VM run, P2 is answered by sandbox-editgates.py, P5, P6, P8 by reading).
# END-HISTORY
#
#   P3  A timed refresh: `screen wait f timeout 1 ... else`, then `screen set f, 'tbl' items rows`, a table of 30 rows by 4 columns at 140x43.  For six ticks the bytes
#       and the printable characters the terminal received per tick: ticks 1-3 change ONE cell of every row (the tick number), ticks 4-6 set the table to exactly what
#       it holds.  The question: does the library write the whole table each time or only what changed, and does a refresh that changes nothing cost anything?
#   P4  A table of 5,000 and of 50,000 rows: the time the program takes to build the dynamic array, the time until the table is on the screen, and the time a Page
#       Down takes to show.  (The sort is not timed here: the key that sorts is the library's own; the plan's falsifier is the size, which this answers.)
#   P7  The audit file's way in: a 150 MB fixture of audit-shaped lines, opened with OPENSEQ in an administrator session, SEEK from the end, the last lines read; and
#       a SEEK to the middle.  Times in milliseconds from the program's own clock.
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ptydrive import PtySession    # noqa: E402

TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b[()][0-9A-B]|\x1b[=>78M]")
bad = 0


def say(s=""):
    print(s, flush=True)


def bail(msg):
    say("sandbox-tk-phase0: CANNOT RUN - " + msg)
    sys.exit(2)


def sess(box, *cmds):
    p = subprocess.run([sys.executable, TOOL, box, "sess", os.path.join(box, "sys")] + list(cmds), capture_output=True, text=True, errors="replace", timeout=900)
    return ANSI.sub("", p.stdout + p.stderr).split(":TERM 200,9999", 1)[-1]


def put(box, name, text):
    with open(os.path.join(box, "sys", "bp", name), "w", encoding="latin-1") as f:
        f.write(text)


def printable(b):
    """Characters a terminal would put in cells: the bytes with the escape sequences and the control characters taken out."""
    t = ANSI.sub("", b.decode("latin-1", "replace"))
    return len(re.sub(r"[\x00-\x1f\x7f]", "", t))


class Pty:
    def __init__(self, box, cmd, cols=140, rows=43):
        env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"), TERM="xterm")
        self.s = PtySession([os.path.join(box, "sys", "bin", "sd")], os.path.join(box, "user_accounts"), env, cols, rows)
        self.s.settle(1.0)
        self.s.type("TERM xterm\r")
        self.s.type("TERM %d,%d\r" % (cols, rows))
        self.mark = len(self.s.raw)
        self.t0 = time.time()
        self.s.type(cmd + "\r", idle=0.2)

    def lines(self):
        return self.s.screen.lines()

    def end(self):
        self.s.type("\r\r", idle=0.3)
        self.s.type("OFF\r", idle=0.5)
        self.s.finish()


P3 = """   screen open clear else crt 'NOTERM' ; stop
   cols = 'Name':@sm:'12L':@vm:'Tick':@sm:'8R':@vm:'Status':@sm:'10L':@vm:'Note':@sm:'20L'
   tick = 0
   gosub build
   screen form title 'P3 refresh' at 2,2 size 120,36 returning f
   screen table f, 'tbl', cols, rows at 2,1 size 110,32
   screen button f, 'ok', '&OK' at 2,34 default
   loop
      screen wait f timeout 1 returning ev then
         exit
      end else
         tick += 1
         if tick <= 3 then gosub build
         screen set f, 'tbl' items rows
         if tick >= 6 then exit
      end
   repeat
   screen hide f
   crt @(0, 41) : 'P3 DONE ticks=' : tick
   stop
build:
   rows = ''
   for i = 1 to 30
      rows<i> = 'name':fmt(i, 'R%3'):@vm:tick:@vm:'ok':@vm:'a note for row ':i
   next i
   return
end
"""

P4 = """   screen open clear else crt 'NOTERM' ; stop
   n = %d
   t0 = system(1081)
   rows = ''
   for i = 1 to n
      rows := 'name':fmt(i, 'R%%6'):@vm:i:@vm:'ok':@vm:'a note for row ':i:@fm
   next i
   rows = rows[1, len(rows) - 1]
   built = system(1081) - t0
   cols = 'Name':@sm:'12L':@vm:'Num':@sm:'8R':@vm:'Status':@sm:'10L':@vm:'Note':@sm:'24L'
   screen form title 'P4 rows' at 2,2 size 120,36 returning f
   screen label f, 'info', 'BUILT ':n:' rows in ':built:' ms, ':len(rows):' bytes' at 2,34 width 80
   screen table f, 'tbl', cols, rows at 2,1 size 110,32
   screen run f returning pressed else null
   screen hide f
   crt @(0, 41) : 'P4 DONE n=' : n
   stop
end
"""

P7 = """   t0 = system(1081)
   openseq 'audit.big' to f else crt 'P7 OPEN-FAIL ':status() ; stop
   t1 = system(1081)
   seek f, -3000, 2 else crt 'P7 SEEK-FAIL ':status() ; stop
   readseq line from f else null
   n = 0 ; last = ''
   loop
      readseq line from f else exit
      n += 1 ; last = line
   repeat
   t2 = system(1081)
   crt 'P7 TAIL open=':(t1 - t0):' ms seek+read=':(t2 - t1):' ms lines=':n:' last=[':last[1, 70]:']'
   seek f, 75000000, 0 else crt 'P7 SEEK2-FAIL ' ; stop
   readseq line from f else null
   readseq line from f else line = 'EOF'
   t3 = system(1081)
   crt 'P7 MIDDLE seek+read=':(t3 - t2):' ms line=[':line[1, 70]:']'
   close f
end
"""


def main():
    global bad
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-tk-phase0.py <dir> [--build]")
    box = os.path.abspath(args[0])
    say("sandbox-tk-phase0: sandbox %s" % box)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-tk-phase0: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(box, "sys", "bin", "sd")):
        bail("%s holds no built sandbox" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)
    made = []
    try:
        for name, text in (("zztkp3", P3), ("zztkp4a", P4 % 5000), ("zztkp4b", P4 % 50000), ("zztkp7", P7)):
            put(box, name, text)
            made.append(name)
        out = sess(box, *["BASIC bp %s" % n for n in made])
        say("compile: %s" % ("ok" if out.count("Compiled 1 program(s) with no errors") == len(made) else "FAILED\n" + out[-600:]))
        if out.count("Compiled 1 program(s) with no errors") != len(made):
            bail("a probe program did not compile")

        say("\n--- P3: a timed refresh of a 30 x 4 table at 140x43 (ticks 1-3 change the Tick cell of every row, ticks 4-6 change nothing)")
        # 22 Oct 26: the first version let settle() run to quiet, which never came while the ticks went on, so six ticks were counted as "the first draw".  A timeline now:
        # the bytes the terminal receives in each quarter second from the moment the command is typed, bucketed by the second of the run, and the screen read at 2.5 s.
        t = Pty(box, "RUN bp zztkp3")
        stamps = []                       # (seconds since the command, bytes so far)
        t_start = t.t0
        screen_mid = None
        while time.time() - t_start < 10.0:
            t.s._pump(0.25)
            stamps.append((time.time() - t_start, len(t.s.raw)))
            if screen_mid is None and time.time() - t_start > 2.5:
                screen_mid = [l for l in t.lines() if "name" in l]
        say("    the table showed %d rows containing 'name' at 2.5 s (30 expected)" % len(screen_mid or []))
        per = {}
        for sec, n in stamps:
            per.setdefault(int(sec), []).append(n)
        prev = t.mark
        for sec in sorted(per):
            cur = per[sec][-1]
            say("    second %d: %6d bytes, %6d printable characters" % (sec, cur - prev, printable(t.s.raw[prev:cur])))
            prev = cur
        done = any("P3 DONE" in l for l in t.lines())
        say("    the program reached its end: %s   (the timer ticks at 1 s; ticks 1-3 change the Tick cell of every row, 4-6 set the table to what it holds)" % done)
        bad += 0 if done else 1
        t.end()
        if "--only=p3" in sys.argv:
            say("\nsandbox-tk-phase0: --only=p3, %d probe(s) did not reach what they measure" % bad)
            sys.exit(1 if bad else 0)

        for name, n in (("zztkp4a", 5000), ("zztkp4b", 50000)):
            say("\n--- P4: a table of %d rows at 140x43" % n)
            t = Pty(box, "RUN bp %s" % name)
            t0 = time.time()
            seen = None
            while time.time() - t0 < 180:
                t.s.settle(idle=0.4, limit=2.0)
                L = t.lines()
                seen = [l for l in L if "BUILT" in l]
                if seen:
                    break
            took = time.time() - t0
            say("    first screen with the table after %.1f s (the session start is not counted; the label says: %s)" % (took, seen[0].strip() if seen else "NEVER SHOWN"))
            if not seen:
                bad += 1
                t.end()
                continue
            rows_on = [l for l in t.lines() if "name" in l]
            say("    rows on the screen: %d" % len(rows_on))
            for key, label in (("\x1b[6~", "Page Down"), ("\x1b[6~", "Page Down"), ("\x1b[F", "End")):
                a = time.time()
                before = "\n".join(t.lines())
                t.s.type(key, idle=0.25)
                for _ in range(40):
                    if "\n".join(t.lines()) != before:
                        break
                    t.s.settle(idle=0.25, limit=1.0)
                say("    %-9s shows its result after %.2f s (screen changed: %s)" % (label, time.time() - a, "\n".join(t.lines()) != before))
            say("    the last rows on the screen: %s" % [l.strip()[:40] for l in t.lines() if "name" in l][-2:])
            t.end()

        say("\n--- P7: the audit file's way in (a 150 MB fixture of audit-shaped lines)")
        big = os.path.join(box, "sys", "audit.big")
        line = "2026-10-21T22:00:00 login user=zzuser account=zzacct tty=pts/9 ok route=ssh extra=%s\n"
        with open(big, "w", encoding="latin-1") as f:
            for i in range(1500000):
                f.write(line % ("%07d" % i))
        say("    fixture %s: %d bytes" % (big, os.path.getsize(big)))
        out = sess(box, "RUN bp zztkp7")
        for l in out.splitlines():
            if l.startswith("P7"):
                say("    " + l)
        got = [l for l in out.splitlines() if l.startswith("P7 TAIL")]
        bad += 0 if got else 1
        say("    (the installed audit file is owned by sdsys, group sdusers, mode 0620; SDSYS opens it as its owner)")
    finally:
        for nm in made:
            for d in ("bp", "bp.out"):
                p = os.path.join(box, "sys", d, nm)
                if os.path.exists(p):
                    os.remove(p)
        big = os.path.join(box, "sys", "audit.big")
        if os.path.exists(big):
            os.remove(big)
        subprocess.run([sys.executable, TOOL, box, "stop"], capture_output=True, text=True, errors="replace", timeout=120)
    say("\nsandbox-tk-phase0: %d probe(s) did not reach what they measure" % bad)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
