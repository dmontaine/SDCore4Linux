#!/usr/bin/env python3
#
# sandbox-autologout.py - AUTOLOGOUT ends a session that waits with timeouts, and real input keeps it (S.88 phase 2, S3 of ~/Documents/Audits/TUI/Opus_TUI_Plan.txt).
# No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-autologout.py <dir> [--build] [--strict]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 every row that counts
# passed, 1 a row failed, 2 it could not run.  --strict counts a row of a phase that has not landed as FAILED (tuirows.py); that is how the red run on the tree before is made.
# It idles for about two minutes: eight sessions wait side by side.
#
# START-HISTORY:
# 28 Oct 26 dm  New (S.88 phase 2, S3).  Written with the kernel change (linuxio.c keyin(): the idle clock carried across a wait that ended by its own timeout); NOT RUN yet - the
#               owner's rule of 28 Oct defers every sandbox run to the one complete run at the end of the full-screen phases.
# 28 Oct 26 dm  S.88 phase 2 review: session H, a timed wait EQUAL to the AUTOLOGOUT period (keyin(60) under AUTOLOGOUT 1).  Its first wait must return a plain
#               timeout, as it always did (the first build logged it out: "idle_left <= timeout" with nothing carried); the clock it carries then ends the
#               second wait.  NOT RUN (the same rule).
# END-HISTORY
#
# KNOWN AND INTENDED (not tested as a fault): a program that polls the keyboard with very short timed KEYINs and works between them counts as waiting - the polls
# add up and AUTOLOGOUT eventually logs it out (F is that case with no work between the polls).
#
# WHAT IT HOLDS.  Eight ORDINARY sessions of the fixture account zzhd (sandbox-home.py's), each on its own pseudo-terminal:
#   H  AUTOLOGOUT 1, then a program that waits with keyin(60) - EQUAL to the period - idle -> its first wait returns a plain timeout (the program prints
#      "ZZAL3 timeout 1" about 60 s in, the session still there), then the carried clock ends the second wait at once, saying message 2503      [review]
#   A  AUTOLOGOUT 1, then a program that waits with keyin(1) for ever, idle          -> ends between 55 and 85 s after the command, saying message 2503     [phase 2]
#   F  AUTOLOGOUT 1, then a program that waits with keyin(0.3) (shorter than a second), idle -> ends                                                          [phase 2]
#   G  AUTOLOGOUT 1, then tool.keys (a screen library page: $sl_key's one-second slices), idle -> ends                                                        [phase 2]
#   E  AUTOLOGOUT 1, the keyin(1) program, a key every 0.5 s for the first 30 s, then idle -> alive 80 s in (the keys started the clock again), ended by 125 s  [phase 2]
#   B  AUTOLOGOUT 1, the keyin(1) program, a key every 0.5 s all the time -> alive at the end, and the program counted the keys (real input keeps a session)
#   C  AUTOLOGOUT 1 at the TCL prompt, idle -> ends (CONTROL: the instrument can see an AUTOLOGOUT; this worked before the change)
#   D  no AUTOLOGOUT, the keyin(1) program, idle -> alive at the end (CONTROL: what ends A is AUTOLOGOUT, not the program)
# Every session that ended must also be gone from the user table (LISTU, read by the administrator), and the sandbox's errlog must have gained exactly one
# "Inactivity timer expired" line for each session whose terminal showed it (the same message and log line as a plain prompt's logout, from the same code).
#
# THE INSTRUMENT.  A session has ended when its pseudo-terminal reports end of file (ptydrive's `exited`); the time is taken when that is first seen.  The keys sent are printed with
# their count; B's program prints a running count, which is the evidence the keys arrived.  The user table is read before (all eight listed, else the table rows are not believed) and
# after.  Programs are compiled in zzhd by its own ordinary session; a program that did not compile stops the suite (exit 2), never a quiet pass.
# NOT HELD HERE: the IDE and the home screen by name (their waits are $sl_key's, which G covers); a wait inside SED (SED keeps its own work-around: it waits for the key alone).
import os
import re
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


sh = _load("sandbox_home_for_autologout", "sandbox-home.py")
g, H = sh.g, sh.H
R = Rows("autologout")
HD = "zzhd"
MSG = b"Inactivity timer expired"
IDLE_TOTAL = 125.0          # seconds from the start of the idle period to the last look
E_KEYS_UNTIL = 30.0         # E stops typing this many seconds in
E_ALIVE_AT = 80.0           # ... and must still be there this many seconds in (60 s after its last key is about 90 s)


def say(s=""):
    print(s, flush=True)


def bail(msg):
    say("sandbox-autologout: CANNOT RUN - " + msg)
    sys.exit(2)


def bpfile(a, n):
    return os.path.join(sh.BOX, "user_accounts", a, "bp", n)


ZZAL1 = """   n = 0
   crt 'ZZAL1 ready'
   loop
      k = keyin(1)
      if k # '' then
         n += 1
         crt 'ZZAL1 key ' : n
      end
   repeat
end
"""

ZZAL2 = """   n = 0
   crt 'ZZAL2 ready'
   loop
      k = keyin(0.3)
      if k # '' then
         n += 1
         crt 'ZZAL2 key ' : n
      end
   repeat
end
"""


# 28 Oct 26 review: a timed wait of exactly the AUTOLOGOUT period (AUTOLOGOUT 1 is 60 s); each plain timeout is counted on the terminal
ZZAL3 = """   n = 0
   crt 'ZZAL3 ready'
   loop
      k = keyin(60)
      if k = '' then
         n += 1
         crt 'ZZAL3 timeout ' : n
      end
   repeat
end
"""


def compile_progs():
    for n, body in (("zzal1", ZZAL1), ("zzal2", ZZAL2), ("zzal3", ZZAL3)):
        g.put(bpfile(HD, n), body)
    out = g.plain(HD, ["BASIC bp zzal1", "BASIC bp zzal2", "BASIC bp zzal3"])
    n_ok = sum(1 for ln in out if re.match(r"^Compiled 1 program\(s\) with no errors", ln))
    say("    compiled %d of 3 programs in %s with no errors" % (n_ok, HD))
    if n_ok != 3:
        bail("the wait programs did not compile in %s: %s" % (HD, " | ".join(out[-12:])))


def open_h(label):
    h = H(account=HD, cols=140, rows=43)
    say("  [pty %s] argv=%s -a%s cwd=%s TERM=xterm LC_ALL=C window=140x43 SDTEST_ADMIN=unset SDBOX_KEYSET=%s SD_CONFIG=%s pid=%d" % (
        label, os.path.join(sh.SYS, "bin", "sd"), HD, os.path.join(sh.BOX, "user_accounts", HD), os.environ.get("SDBOX_KEYSET", "(unset)"),
        os.path.join(sh.BOX, "sd.conf"), h.s.pid))
    return h


def send(h, label, data, idle=1.0):
    say("  [key %s] %r" % (label, data))
    h.s.type(data, idle=idle)


def listu_pids():
    out = g.adm(["LISTU"])
    pids = set()
    for ln in out:
        m = re.match(r"^\*?\s*(\d+)\s+(\d+)\s", ln)
        if m:
            pids.add(int(m.group(2)))
    return pids


def errlog_count():
    p = os.path.join(sh.SYS, "errlog")
    if not os.path.isfile(p):
        return None
    with open(p, "rb") as fh:
        return fh.read().count(MSG)


def main():
    say("sandbox-autologout: S.88 phase 2 (S3) - AUTOLOGOUT across waits with a timeout.  strict=%s SDBOX_KEYSET=%s" % ("--strict" in sys.argv, os.environ.get("SDBOX_KEYSET", "(unset)")))
    S = {}
    try:
        sh.setup("sandbox-autologout.py")
        if sh.tkb.failed:
            bail("the sandbox setup did not pass its own row")
        compile_progs()
        log0 = errlog_count()
        say("  errlog %s: %s line(s) holding %r before" % (os.path.join(sh.SYS, "errlog"), log0, MSG.decode()))
        for k in "ABCDEFGH":
            S[k] = open_h(k)
        for k in "ABCEFGH":
            send(S[k], k, "AUTOLOGOUT 1\r")
        cmd_at = {}                     # when each session's last command went in: the idle clock of a session starts there, and t0 (below) is taken after the later sessions were started
        for k in "ABDE":
            send(S[k], k, "RUN bp zzal1\r", idle=1.5)
            cmd_at[k] = time.time()
        send(S["F"], "F", "RUN bp zzal2\r", idle=1.5)
        send(S["G"], "G", "tool.keys\r", idle=2.0)
        send(S["H"], "H", "RUN bp zzal3\r", idle=1.5)
        ready = {k: (b"ZZAL1 ready" in S[k].s.raw) for k in "ABDE"}
        ready["F"] = b"ZZAL2 ready" in S["F"].s.raw
        ready["G"] = not S["G"].s.exited and len(S["G"].s.raw) > 0
        ready["H"] = b"ZZAL3 ready" in S["H"].s.raw
        say("  started: %r" % ready)
        R.row("AL-ctl0 every waiting program started (ZZAL1 / ZZAL2 / ZZAL3 ready on its terminal; tool.keys drew)", all(ready.values()), repr(ready))
        t0 = time.time()
        before = listu_pids()
        pids = {k: S[k].s.pid for k in S}
        seen = all(p in before for p in pids.values())
        say("  pids %r; the user table (LISTU) before: %r; all %d listed: %s" % (pids, sorted(before), len(pids), seen))
        R.row("AL-ctl1 the user table lists all %d sessions before the idle period (the instrument sees them)" % len(pids), seen, "pids %r table %r" % (pids, sorted(before)))
        ended = {}
        keys = {"B": 0, "E": 0}
        alive_e80 = None
        h_timeout_at = None   # when H's terminal first showed "ZZAL3 timeout 1"
        h_alive_then = None   # ... and whether H was still there at that moment
        next_key = t0
        while time.time() < t0 + IDLE_TOTAL:
            now = time.time()
            if now >= next_key:
                for k in ("B", "E"):
                    if k == "E" and now - t0 >= E_KEYS_UNTIL:
                        continue
                    if not S[k].s.exited:
                        S[k].s.type("x", settle=False)
                        keys[k] += 1
                next_key = now + 0.5
            for k, h in S.items():
                h.s._pump(0.02)
                if h.s.exited and k not in ended:
                    ended[k] = time.time() - t0
                    say("  session %s ended %.1f s into the idle period" % (k, ended[k]))
            if h_timeout_at is None and b"ZZAL3 timeout 1" in S["H"].s.raw:
                h_timeout_at = time.time() - t0
                h_alive_then = ("H" not in ended) or (ended["H"] >= h_timeout_at)
                say("  H's first wait returned a plain timeout %.1f s in (H %s then)" % (h_timeout_at, "alive" if h_alive_then else "already gone"))
            if alive_e80 is None and now - t0 >= E_ALIVE_AT:
                alive_e80 = not S["E"].s.exited
                say("  %.0f s in: E is %s" % (now - t0, "alive" if alive_e80 else "gone"))
        after = listu_pids()
        say("  keys sent: B %d, E %d (E only in the first %.0f s); ended: %r; the user table after: %r" % (keys["B"], keys["E"], E_KEYS_UNTIL, ended, sorted(after)))

        def gone(k):
            return S[k].s.exited and (not seen or pids[k] not in after)

        def said(k):
            return MSG in S[k].s.raw

        # controls
        R.row("AL-C AUTOLOGOUT 1 ended the session idle at the TCL prompt (CONTROL), and its terminal said %r" % MSG.decode(), gone("C") and said("C"),
              "ended=%r said=%s in table=%s" % (ended.get("C"), said("C"), pids["C"] in after))
        R.row("AL-D with no AUTOLOGOUT the keyin(1) program is alive after %.0f s of idling (CONTROL)" % IDLE_TOTAL, not S["D"].s.exited and (not seen or pids["D"] in after),
              "exited=%s" % S["D"].s.exited)
        mcount = re.findall(rb"ZZAL1 key (\d+)", S["B"].s.raw)
        bcount = int(mcount[-1]) if mcount else 0
        R.row("AL-B a key every 0.5 s keeps the session (alive after %.0f s) and the program saw the keys (counted %d of %d sent)" % (IDLE_TOTAL, bcount, keys["B"]),
              not S["B"].s.exited and bcount >= keys["B"] // 2 and keys["B"] >= 100, "exited=%s counted=%d sent=%d" % (S["B"].s.exited, bcount, keys["B"]))
        # the fault
        ta = None if ended.get("A") is None else ended["A"] + (t0 - cmd_at["A"])      # seconds after A's own RUN, not after t0 (29 Oct 26: A ended at 53.0 s from t0, 62.6 s from its command)
        R.row("AL-A AUTOLOGOUT 1 ended the idle keyin(1) program between 55 and 85 s after its command (ended at %s s after it, %s s after the idle period began)" % (None if ta is None else "%.1f" % ta, ended.get("A")),
              ta is not None and 55.0 <= ta <= 85.0 and gone("A"), "ended=%r in table=%s" % (ta, pids["A"] in after), phase=2 if gone("C") else None)
        R.row("AL-Am the ended keyin(1) session's terminal said %r, as a plain prompt's does" % MSG.decode(), said("A"), "not in %d bytes" % len(S["A"].s.raw),
              phase=2 if said("C") else None)
        R.row("AL-F AUTOLOGOUT 1 ended the idle keyin(0.3) program (ended at %r s)" % ended.get("F"), gone("F") and said("F"), "ended=%r" % ended.get("F"),
              phase=2 if gone("C") else None)
        R.row("AL-G AUTOLOGOUT 1 ended the idle tool.keys page (a screen library wait; ended at %r s)" % ended.get("G"), gone("G") and said("G"), "ended=%r" % ended.get("G"),
              phase=2 if gone("C") else None)
        R.row("AL-Ea %.0f s in, the session whose last key was at %.0f s is still there (a key starts the clock again)" % (E_ALIVE_AT, E_KEYS_UNTIL), alive_e80 is True,
              "alive at %.0f s: %r, ended at %r" % (E_ALIVE_AT, alive_e80, ended.get("E")))
        R.row("AL-Eb ... and it was ended by %.0f s (ended at %r s)" % (IDLE_TOTAL, ended.get("E")), gone("E") and said("E"), "ended=%r" % ended.get("E"),
              phase=2 if gone("C") else None)
        # 28 Oct 26 review: a wait EQUAL to the period, nothing carried, is a plain timeout (the old strict test); only the carried clock ends the next wait
        hcount = len(re.findall(rb"ZZAL3 timeout (\d+)", S["H"].s.raw))
        R.row("AL-Ha keyin(60) under AUTOLOGOUT 1 (a wait EQUAL to the period, nothing carried) returned a plain timeout to the program, about 60 s in "
              "(ZZAL3 timeout 1 shown at %r s)" % (None if h_timeout_at is None else round(h_timeout_at, 1)),
              h_timeout_at is not None and 50.0 <= h_timeout_at <= 80.0 and h_alive_then is True,
              "timeout at %r alive then %r ended %r" % (h_timeout_at, h_alive_then, ended.get("H")))
        R.row("AL-Hb ... and the clock it carried ended the SECOND wait at once: the session ended within 10 s of that timeout, saying %r, with exactly "
              "one timeout shown (%d)" % (MSG.decode(), hcount),
              h_timeout_at is not None and ended.get("H") is not None and 0.0 <= ended["H"] - h_timeout_at <= 10.0 and gone("H") and said("H") and hcount == 1,
              "timeout at %r ended %r timeouts shown %d" % (h_timeout_at, ended.get("H"), hcount), phase=2 if gone("C") else None)
        log1 = errlog_count()
        n_said = sum(1 for k in S if S[k].s.exited and said(k))
        say("  errlog: %s line(s) holding %r after; sessions whose terminal said it: %d" % (log1, MSG.decode(), n_said))
        R.row("AL-L the errlog gained exactly one %r line for each session that showed it (%r -> %r, %d sessions)" % (MSG.decode(), log0, log1, n_said),
              log0 is not None and log1 is not None and n_said >= 1 and log1 - log0 == n_said, "before %r after %r said %d" % (log0, log1, n_said))
    finally:
        for h in S.values():
            try:
                if not h.s.exited:
                    h.s.type("\x11", idle=0.5)
                h.end()
            except Exception:
                pass
        sh.teardown()
    sys.exit(R.finish())


if __name__ == "__main__":
    main()
