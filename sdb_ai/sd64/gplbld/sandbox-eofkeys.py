#!/usr/bin/env python3
#
# sandbox-eofkeys.py - SED, the IDE and a user program's SCREEN WAIT end when their input ends.  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-eofkeys.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (needs a `make`d bin/sd).  With --build it is built first from
# THIS tree (it must be empty or absent).  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 19 Oct 26 dm  Written for the verifier's finding F8 of the 140x42 branch (owner: "fix 100% cpu problem"): a SED or IDE session whose
#               input was a pipe that had ended spun at 100% CPU for as long as it was let run (8.0 s of CPU in 8.3 s, measured on
#               the merged tree before the fix).  Two causes: SED's key loop took the null key of an ended input for "no key yet"
#               and asked again; $sl_form's wait turned the null key into a TIMEOUT event whenever the caller had given a timeout,
#               and the IDE waits a second at a time.
# END-HISTORY
#
# THE INSTRUMENT.  Each session is the sandbox's `sd` started as a child with a PIPE for its input: the lines, then the pipe is CLOSED, so
# the input ends and there is no OFF line to end the session politely.  The child is waited for with wait4(), so its own user + system CPU
# comes back (not the CPU of everything this script ever started), and it is killed after 8 s if it is still there.  A row that
# judges "ended by itself" first checks that the program really started (a word only that program draws), so a session that never
# got as far as the program cannot pass; the numbers (wall seconds, CPU seconds) are printed in every row.
#
# NOT HERE: that a timeout still happens as a timeout.  A pipe has no timeouts (keyin() reads with no limit when the input is not a
# terminal), so the other direction is `sandbox-screen.py` (the wait that times out: ELSE timeout) and `sandbox-ide.py` (the status line
# follows what is typed, which is the IDE's one-second timeout) on a pseudo-terminal.  ED, the classic line editor, is NOT under test:
# it has about fifteen INPUT statements and none of them tests for the end of input; it spins in the same way (known, not fixed).

import os
import re
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
passed = failed = 0
DEADLINE = 8.0          # seconds a session may take before it is killed
CPU_OK = 3.0            # CPU seconds a session that ended by itself may have used


def say(s=""):
    print(s)


def row(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        say("  [PASS] " + name)
    else:
        failed += 1
        say("  [FAIL] " + name + ("   <- " + detail if detail else ""))


def bail(msg):
    say("sandbox-eofkeys: CANNOT RUN - " + msg)
    sys.exit(2)


def pipe_session(box, label, *lines):
    """Run the sandbox's sd with these lines on a pipe that is then closed.  Returns (ended, wall, cpu, text)."""
    sysd = os.path.join(box, "sys")
    sd = os.path.join(sysd, "bin", "sd")
    env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"))
    body = "TERM 140,42\n" + "".join(l + "\n" for l in lines)
    outf = os.path.join(box, "eofkeys-%s.out" % label)
    say("    > %s  (cwd %s, input %s, then the pipe is closed)" % (sd, sysd, repr(body)))
    with open(outf, "wb") as fo:
        p = subprocess.Popen([sd], cwd=sysd, env=env, stdin=subprocess.PIPE, stdout=fo, stderr=subprocess.STDOUT)
        p.stdin.write(body.encode())
        p.stdin.close()
        t0 = time.time()
        while True:
            wpid, _status, ru = os.wait4(p.pid, os.WNOHANG)
            if wpid:
                ended = True
                break
            if time.time() - t0 > DEADLINE:
                os.kill(p.pid, signal.SIGKILL)
                _w, _status, ru = os.wait4(p.pid, 0)
                ended = False
                break
            time.sleep(0.05)
        p.returncode = 0                      # (waited for here, not by Popen)
    wall = time.time() - t0
    cpu = ru.ru_utime + ru.ru_stime
    with open(outf, "rb") as fi:
        text = ANSI.sub("", fi.read().decode("utf-8", "replace"))
    os.remove(outf)
    return ended, wall, cpu, text


def judge(name, started_re, res):
    """Two rows: the program started (so the next row is about it), and it ended by itself without spinning."""
    ended, wall, cpu, text = res
    started = re.search(started_re, text) is not None
    row("%s: it started (%s)" % (name, started_re), started, repr(text[-300:]))
    row("%s: it ended by itself, within %.0f s, using under %.0f s of CPU   [wall %.1f s, cpu %.1f s]" % (name, DEADLINE, CPU_OK, wall, cpu),
        started and ended and cpu < CPU_OK, "ended=%s wall=%.1f cpu=%.1f" % (ended, wall, cpu))


PROG = (
    "   screen open clear else\n      crt 'OPENFAILED'\n      stop\n   end\n"
    "   screen form title 'Eof' at 10,3 size 30,6 returning f\n"
    "   screen button f, 'ok', '&OK' at 2,4 default\n"
    "   n = 0\n   last = ''\n"
    "   loop\n"
    "      screen wait f timeout 1 returning ev then\n         last = 'event ':ev<1>\n      end else\n         last = ev<1>\n      end\n"
    "      n += 1\n"
    "   until last = 'end' or n >= 2000 do\n   repeat\n"
    "   screen close\n"
    "   crt 'EOFLAST[':last:'] EOFN[':n:']'\n"
    "end\n")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-eofkeys.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-eofkeys: sandbox %s" % box)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-eofkeys: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    made = []
    try:
        with open(os.path.join(sysd, "bp", "zzeofu"), "w") as fh:
            fh.write(PROG)
        made.append("zzeofu")

        ended, wall, cpu, text = pipe_session(box, "setup", "create.file zzeof", "basic bp zzeofu")
        row("setup: the file zzeof was made", "Created DATA part as zzeof" in text and ended, repr(text[-300:]))
        row("setup: the probe program compiles with no errors", "Compiled 1 program(s) with no errors" in text, repr(text[-300:]))

        say("\n  SED, a new record")
        res = pipe_session(box, "sed1", "sed zzeof t1")
        judge("SED", r"File\s+Edit\s+Search\s+Buffer\s+Window\s+Tools", res)

        say("\n  SED, a record with typed text in it (the buffer is changed)")
        res = pipe_session(box, "sed2", "sed zzeof t2", "hello")
        judge("SED with typed text", r"File\s+Edit\s+Search\s+Buffer\s+Window\s+Tools", res)
        _e, _w, _c, text = pipe_session(box, "ct2", "ct zzeof t2")
        row("SED with typed text: the text was not written to the record (nobody was there to answer 'save?')",
            "Record 't2' not found" in text, repr(text[-300:]))
        _e, _w, _c, text = pipe_session(box, "sed2b", "sed zzeof t2")
        row("SED with typed text: the record's lock was given back (a second session opens it as a new record)",
            "New record" in text and "locked" not in text, repr(text[-400:]))

        say("\n  the IDE")
        res = pipe_session(box, "ide1", "ide")
        judge("IDE", r"IDE: sdsys", res)
        res = pipe_session(box, "ide2", "ide zzeof t5")
        judge("IDE with a record named", r"IDE: sdsys", res)

        say("\n  a user program: SCREEN WAIT f TIMEOUT 1 in a loop")
        res = pipe_session(box, "user", "run bp zzeofu")
        ended, wall, cpu, text = res
        m = re.search(r"EOFLAST\[(.*?)\] EOFN\[(\d+)\]", text)
        row("user program: it ran to its end (the line it prints was found)", m is not None, repr(text[-300:]))
        row("user program: the wait answered END, not TIMEOUT, when the input had ended   [last %s, waits %s]" %
            (m.group(1) if m else "?", m.group(2) if m else "?"), m is not None and m.group(1) == "end", repr(m.group(0) if m else None))
        row("user program: ... at once, with little CPU   [wall %.1f s, cpu %.1f s]" % (wall, cpu), ended and cpu < CPU_OK,
            "ended=%s wall=%.1f cpu=%.1f" % (ended, wall, cpu))

        say("\n  CONTROL: CED already ended at the end of input")
        res = pipe_session(box, "ced", "ced zzeof c1")
        ended, wall, cpu, text = res
        row("CONTROL: CED ended by itself and its screen was drawn (the word array)", ended and cpu < CPU_OK and "array" in text,
            "ended=%s wall=%.1f cpu=%.1f %s" % (ended, wall, cpu, repr(text[-200:])))
    finally:
        for nm in made:
            for d in ("bp", "bp.out"):
                pth = os.path.join(sysd, d, nm)
                if os.path.exists(pth):
                    os.remove(pth)
        pipe_session(box, "clean", "delete.file zzeof")

    say("\nsandbox-eofkeys: %d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
