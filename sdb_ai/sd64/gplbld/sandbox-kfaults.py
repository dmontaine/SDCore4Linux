#!/usr/bin/env python3
#
# sandbox-kfaults.py - three small kernel faults, run for real (S.178, S.194, S.195).  No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-kfaults.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or absent).  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 10 Nov 26 dm  New.  S.178: a session idle on a PIPE leaves on SIGTERM (keyin() blocked in read(), which a signal does not wake).  S.194: a run-time error on a common-block variable in a
#               program with an array names the variable without that array's subscript.  S.195: a program with a bad object leaves no file open in the session.
# END-HISTORY
#
# THE INSTRUMENT.  Each session is a real sd process on a pipe that this suite keeps open, so it can be signalled, and its descriptors counted from /proc, while it waits.  S0 is the control of
# the live session itself: a line sent after a pause must still be answered, or the rows below it say nothing.  A count of open files is read while the session is idle at its prompt.

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
lives = []


def say(s=""):
    print(s, flush=True)


def row(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        say("  [PASS] " + name)
    else:
        failed += 1
        say("  [FAIL] " + name + ("   <- " + detail if detail else ""))
    return ok


def bail(msg):
    say("sandbox-kfaults: CANNOT RUN - " + msg)
    sys.exit(2)


class Live:
    """A session on a pipe kept open."""

    def __init__(self, box, tag):
        self.out = os.path.join(box, "live-%s.out" % tag)
        env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"))
        self.fh = open(self.out, "w")
        self.p = subprocess.Popen([os.path.join(box, "sys", "bin", "sd")], stdin=subprocess.PIPE, stdout=self.fh, stderr=subprocess.STDOUT, cwd=os.path.join(box, "sys"), env=env, text=True)
        say("    > session %s, pid %d, cwd %s" % (tag, self.p.pid, os.path.join(box, "sys")))
        lives.append(self)
        self.send("", "TERM 200,9999")

    def send(self, *lines):
        say("    > sent: %s" % " | ".join(lines))
        self.p.stdin.write("".join(c + "\n" for c in lines))
        self.p.stdin.flush()

    def text(self):
        self.fh.flush()
        return ANSI.sub("", open(self.out, errors="replace").read())

    def until(self, pattern, seconds=30):
        end = time.time() + seconds
        while time.time() < end:
            if re.search(pattern, self.text()):
                return True
            if self.p.poll() is not None:
                return bool(re.search(pattern, self.text()))
            time.sleep(0.1)
        return False

    def wait(self, seconds):
        try:
            self.p.wait(timeout=seconds)
            return True
        except subprocess.TimeoutExpired:
            return False

    def fds(self):
        return len(os.listdir("/proc/%d/fd" % self.p.pid))

    def kill(self):
        if self.p.poll() is None:
            self.p.kill()
            self.p.wait()


def sec_sigterm(box):
    say("\n--- S.178: a session idle on a pipe leaves on SIGTERM ---------------------------------------------------------")
    s = Live(box, "term")
    s.send("DISPLAY FIRST.LINE.OK")
    up = s.until(r"(?m)^FIRST\.LINE\.OK", 60)
    time.sleep(2.5)                                  # idle: past the one second the wait looks at the events
    s.send("DISPLAY AFTER.A.PAUSE")
    late = s.until(r"(?m)^AFTER\.A\.PAUSE", 10)
    c = row("S0 the control: the session answered a line, and a line sent after 2.5 s idle", up and late, s.text()[-300:])
    time.sleep(2.0)
    alive = s.p.poll() is None
    row("S1 the control: idle on the pipe it is still running 2 s later", alive and c, "returncode %r" % s.p.returncode)
    if not alive:
        return
    t0 = time.time()
    s.p.send_signal(signal.SIGTERM)
    gone = s.wait(6)
    took = time.time() - t0
    say("    measured: SIGTERM sent, gone=%r after %.1f s, returncode %r" % (gone, took, s.p.returncode))
    row("S2 SIGTERM ends it within 6 s of its own accord (no SIGKILL was sent; before the fix it was still waiting)", gone and s.p.returncode != -9, "gone=%r returncode=%r took=%.1f" % (gone, s.p.returncode, took))
    s.kill()


def write(box, name, body):
    with open(os.path.join(box, "sys", "bp", name), "w") as fh:
        fh.write(body)


def sec_varname(box):
    say("\n--- S.194: the name of a common variable in a program with an array ------------------------------------------")
    write(box, "zzkf1", "   dim arr(3)\n   common /zzkfc/ cv\n   arr(2) = 1\n   cv = 'abc'\n   x = cv + 1\n   crt 'NOT.REACHED'\nend\n")
    write(box, "zzkf2", "   dim arr(3)\n   common /zzkfd/ cv\n   cv = 1\n   arr(2) = 'abc'\n   x = arr(2) + 1\n   crt 'NOT.REACHED'\nend\n")
    s = Live(box, "name")
    s.send("BASIC bp zzkf1", "RUN bp zzkf1", "DISPLAY ONE.DONE")
    s.until(r"(?m)^ONE\.DONE", 40)
    one = s.text()
    s.send("BASIC bp zzkf2", "RUN bp zzkf2", "DISPLAY TWO.DONE")
    s.until(r"(?m)^TWO\.DONE", 40)
    two = s.text()[len(one):]
    s.send("OFF")
    s.wait(10)
    s.kill()
    c = row("V0 the control: both programs compiled, and neither went past the error", one.count("with no errors") == 1 and two.count("with no errors") == 1 and "NOT.REACHED" not in one + two, (one + two)[-500:])
    msg1 = [ln for ln in one.split("\n") if re.search(r"[Nn]on-numeric", ln) and "BASIC" not in ln]
    msg2 = [ln for ln in two.split("\n") if re.search(r"[Nn]on-numeric", ln) and "BASIC" not in ln]
    say("    the error lines: %r %r" % (msg1, msg2))
    row("V1 the control: an element of the array is named with its subscript (arr(2))", c and any(re.search(r"\barr\(2\)", ln, re.I) for ln in msg2), repr(msg2))
    row("V2 the common variable is named cv, with no subscript from the array before it", c and any(re.search(r"\bcv\b(?!\()", ln, re.I) for ln in msg1) and not any(re.search(r"\bcv\(", ln, re.I) for ln in msg1), repr(msg1))


def sec_badobj(box):
    say("\n--- S.195: a program with a bad object leaves no file open in the session ------------------------------------")
    os.makedirs(os.path.join(box, "sys", "bp.out"), exist_ok=True)
    with open(os.path.join(box, "sys", "bp.out", "zzkfbad"), "wb") as fh:
        fh.write(b"x" * 200)
    s = Live(box, "bad")
    s.send("RUN bp zzkfbad", "DISPLAY WARM.DONE")
    s.until(r"(?m)^WARM\.DONE", 30)
    time.sleep(0.5)
    before = s.fds()
    n = 12
    s.send(*(["RUN bp zzkfbad"] * n + ["DISPLAY RUNS.DONE"]))
    s.until(r"(?m)^RUNS\.DONE", 40)
    time.sleep(0.5)
    after = s.fds()
    text = s.text()
    say("    measured: %d descriptors open before, %d after %d more runs" % (before, after, n))
    s.send("OFF")
    s.wait(10)
    s.kill()
    bad = len(re.findall(r"Unable to load '[^']*zzkfbad' object code", text))
    c = row("B0 the control: every run reached the refusal (Unable to load ... object code, %d times; %d runs were made)" % (bad, n + 1), bad == n + 1, text[-400:])
    row("B1 no descriptor was lost by %d failed loads" % n, c and before > 0 and after == before, "before %d after %d" % (before, after))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-kfaults.py <dir> [--build]")
    box = os.path.abspath(args[0])
    say("sandbox-kfaults: sandbox %s" % box)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-kfaults: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(box, "sys", "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)
    try:
        sec_sigterm(box)
        sec_varname(box)
        sec_badobj(box)
    finally:
        for s in lives:
            s.kill()
        subprocess.run([sys.executable, TOOL, box, "stop"], capture_output=True, text=True, errors="replace", timeout=120)
    say("\nsandbox-kfaults: %d passed, %d failed" % (passed, failed))
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
