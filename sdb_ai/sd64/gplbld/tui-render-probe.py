#!/usr/bin/env python3
#
# tui-render-probe.py - S.1 stage 1, the measurement the design note puts FIRST:
#                       can a double-buffered, minimal-diff renderer written in
#                       SD BASIC redraw 160x48 fast enough to be interactive?
#                       Also: does an xterm SGR mouse report reach KEYIN intact?
#
#   python3 /home/don/Projects/sdcore4linux/sdb_ai/sd64/gplbld/tui-render-probe.py --sandbox <dir>
#
# The <dir> is a sandbox built by sandbox-txnfail.py --keep and STARTED
# (SCARLET_CONFIG=<dir>/sd.conf <dir>/sys/bin/sd -start, its sdlnxd killed).
# No sudo, never the live system.  Exit 0 measured, 2 could not run.  It gives
# NUMBERS, not a verdict: the threshold is stated beside them and the decision
# is written into PROJECT_STATUS, where it can be argued with.
#
# WHAT IT RUNS AND HOW IT READS IT
#   sd runs inside a pty (TERM=xterm-256color, 200x60), so SD's terminal code
#   takes the same path it takes for a person, and this reads the pty as fast
#   as the bytes come - a sink that never slows the writer, so what is timed is
#   SD, not an emulator.  The probe program prints its own CPU milliseconds per
#   workload after leaving the alternate screen; this adds the WALL time
#   between markers and the byte count that actually arrived.
#
#   MOUSE: after the renderer, a second program KEYINs for 3 s while this writes
#   "ESC [ < 0 ; 12 ; 5 M" (an xterm 1006 button-press report) into the pty; the
#   program prints every byte it received as decimal codes.  The report is
#   intact when those codes are exactly 27 91 60 48 59 49 50 59 53 77.

import argparse
import os
import pty
import re
import select
import shutil
import sys
import termios
import struct
import fcntl
import time

HERE = os.path.dirname(os.path.abspath(__file__))

MOUSE_SRC = r"""* ZZMOUSE - print, as decimal codes, every byte KEYIN delivers for 3 s.
crt 'ZZMOUSE.READY'
got = ''
t0 = time()
loop
while time() - t0 < 4
   if keyready() then
      k = keyin()
      got := seq(k):' '
   end else
      sleep 0.05
   end
repeat
crt 'ZZMOUSE.GOT ':trim(got)
end
"""

MOUSE_REPORT = b"\x1b[<0;12;5M"


def say(s=""):
    print(s)
    sys.stdout.flush()


def run_pty(sd, conf, cwd, script_lines, feed=None, timeout=300):
    """Run sd in a pty, send the lines, collect everything.  feed=(marker, bytes)
    writes bytes once marker has been seen in the output."""
    pid, fd = pty.fork()
    if pid == 0:
        os.chdir(cwd)
        # TERM=xterm: SD resolves the type through its own terminfo tree, which
        # ships xterm and not xterm-256color - with the latter the session stalls
        # at its first prompt (measured 14 Sep 2026).
        env = dict(os.environ, SCARLET_CONFIG=conf, TERM="xterm", LINES="60", COLUMNS="200")
        os.execve(sd, [sd], env)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", 60, 200, 0, 0))
    out = b""
    stamps = []
    t0 = time.time()
    queue = list(script_lines)
    seen_at_send = -1
    fed = False
    while time.time() - t0 < timeout:
        r, _, _ = select.select([fd], [], [], 0.05)
        if r:
            try:
                chunk = os.read(fd, 65536)
            except OSError:
                break
            if not chunk:
                break
            out += chunk
            stamps.append((time.time() - t0, len(out)))
        # ONE LINE PER PROMPT: the next line goes only when the prompt has come
        # back after the previous one, so nothing is typed ahead.  THE PROMPT IS
        # THE TWO BYTES "\r:" - a bare ":" matched a colon inside rendered frame
        # text, typed OFF into the middle of the 160x48 run, and cut it off
        # (measured 14 Sep 2026).
        if queue and len(out) > seen_at_send and out.endswith(b"\r:"):
            time.sleep(0.1)
            os.write(fd, (queue.pop(0) + "\r").encode())
            seen_at_send = len(out)
        if feed and not fed and feed[0] in out:
            time.sleep(0.5)
            os.write(fd, feed[1])
            fed = True
        try:
            wpid, _ = os.waitpid(pid, os.WNOHANG)
            if wpid:
                break
        except ChildProcessError:
            break
    return out, stamps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sandbox", required=True)
    ap.add_argument("--frames", type=int, default=50)
    a = ap.parse_args()
    box = os.path.abspath(a.sandbox)
    sd = os.path.join(box, "sys", "bin", "sd")
    conf = os.path.join(box, "sd.conf")
    acct = os.path.join(box, "accounts", "box")
    say("tui-render-probe")
    say("  sandbox : %s" % box)
    say("  sd      : %s" % sd)
    if not (os.path.exists(sd) and os.path.isdir(acct)):
        say("tui-render-probe: CANNOT RUN - no sandbox at %s" % box)
        return 2
    shutil.copy(os.path.join(HERE, "tui-render-probe.bp"), os.path.join(acct, "bp", "zztui"))
    with open(os.path.join(acct, "bp", "zzmouse"), "w") as f:
        f.write(MOUSE_SRC)

    out, _ = run_pty(sd, conf, acct, ["BASIC BP ZZTUI ZZMOUSE", "CATALOG BP zztui LOCAL",
                                      "CATALOG BP zzmouse LOCAL", "OFF"], timeout=60)
    text = re.sub(rb"\x1b\[[0-9;?]*[A-Za-z]", b"", out).decode(errors="replace")
    ok = "Compiled 2 program(s) with no errors" in text
    say("  compile : %s" % ("both programs compiled" if ok else "FAILED"))
    if not ok:
        say(text[-1500:])
        return 2

    say("")
    for w, h in ((80, 24), (160, 48)):
        out, stamps = run_pty(sd, conf, acct, ["ZZTUI %d %d %d" % (w, h, a.frames), "OFF"], timeout=300)
        text = re.sub(rb"\x1b\[[0-9;?]*[A-Za-z]", b"", out).decode(errors="replace")
        rows = re.findall(r"ZZTUI\.(\w+) w=(\d+) h=(\d+) frames=(\d+) cpu\.ms=(-?\d+) bytes=(\d+)", text)
        if len(rows) != 4:
            say("  %dx%d: the probe did not report four workloads; tail of output:" % (w, h))
            say(text[-800:])
            return 2
        # WALL TIME, alternate screen open to close: all four workloads plus the
        # pty transfer, which CPU time leaves out (a blocked write is not CPU).
        t_open = t_close = None
        for t, n in stamps:
            if t_open is None and b"\x1b[?1049h" in out[:n]:
                t_open = t
            if t_close is None and b"\x1b[?1049l" in out[:n]:
                t_close = t
        wall = (t_close - t_open) * 1000 if (t_open is not None and t_close is not None) else None
        say("  %dx%d, %d frames each, %d bytes arrived in the pty in total; wall %s for all %d frames"
            % (w, h, a.frames, len(out), ("%.0f ms" % wall) if wall is not None else "not measured",
               4 * a.frames))
        for name, _, _, fr, cpu, nbytes in rows:
            per = int(cpu) / int(fr)
            say("    %-6s cpu %6s ms  = %6.2f ms/frame   %8s bytes = %7.0f bytes/frame"
                % (name, cpu, per, nbytes, int(nbytes) / int(fr)))
        say("")

    out, _ = run_pty(sd, conf, acct, ["ZZMOUSE", "OFF"], feed=(b"ZZMOUSE.READY", MOUSE_REPORT), timeout=30)
    text = out.decode(errors="replace")
    m = re.search(r"ZZMOUSE\.GOT ([0-9 ]*)", text)
    got = m.group(1).strip() if m else "(no report)"
    want = " ".join(str(b) for b in MOUSE_REPORT)
    say("  mouse   : sent %s" % want)
    say("            KEYIN delivered %s" % got)
    say("            %s" % ("INTACT - pure BASIC can read SGR 1006 mouse reports" if got == want
                            else "NOT INTACT - the input path changes the report"))
    say("")
    say("  THRESHOLD, stated rather than scored: 16 ms/frame is one 60 Hz frame; 50 ms/frame")
    say("  is the usual ceiling for typing to feel immediate.  CPU here is SD's own cost;")
    say("  a terminal emulator's paint time is added on top and is not SD's.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
