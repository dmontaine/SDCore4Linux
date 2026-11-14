#!/usr/bin/env python3
#
# sandbox-pipefds.py - S.241 (found by the Windows port, mail 14 Nov 2026 T1030): a process SD detaches with daemon(1, 1) - the daemon sdlnxd,
# a phantom - gives back a PIPE it was handed on fds 0-2, so a caller that captures "sd -start" or a session through a pipe sees end of file.
# A file and a terminal are kept.  No install, no sudo.
#
#   SDBOX_KEYSET=<n> python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-pipefds.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or absent).  Exit 0 every row
# passed, 1 a row failed, 2 it could not run (including the null cases: no sdlnxd after a start, no phantom alive while the reader waits).
#
# START-HISTORY:
# 14 Nov 26 dm  New.  sysseg.c release_pipe_fds(), called after daemon() in start_lnxd(), the startup command's fork and op_phantom().
# END-HISTORY
#
# THE EVIDENCE is the reader's end of file (select() on the pipe, with a time limit) and /proc/<pid>/fd/0..2 of the sandbox's own sdlnxd and
# phantom, found by /proc/<pid>/exe under <dir>.  sd is started here directly with SD_CONFIG=<dir>/sd.conf (sandbox-fromtree.py's "start"
# kills the daemon, which is the process under test).  RED BEFORE THE FIX: on Dev e7fa80b7 the same measurement of "sd -start" on a pipe saw
# no end of file in 15 s and sdlnxd's fds 1 and 2 were the pipe (14 Nov 2026, by hand); the phantom rows were not run red, and may well
# pass without the fix: a phantom moves its own 1 and 2 to its COMO file soon after it starts (P8), so its hold on a pipe was brief.
# NOT SAID HERE: the startup command's fork (STARTUP= in sd.conf) - a sandbox cannot run "sd -asdsys" as an ordinary user, so that process
# ends at once; test-pipefds-units.py holds the call there.

import os
import re
import select
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
passed = failed = 0


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


def bail(msg):
    say("sandbox-pipefds: CANNOT RUN - " + msg)
    sys.exit(2)


class Box:
    def __init__(self, root):
        self.root = root
        self.sd = os.path.join(root, "sys", "bin", "sd")
        self.env = dict(os.environ, SD_CONFIG=os.path.join(root, "sd.conf"))
        self.acct = os.path.join(root, "user_accounts")

    def procs(self):
        """[(pid, exe basename, cmdline)] of the processes running this sandbox's binaries"""
        out = []
        for pid in os.listdir("/proc"):
            if not pid.isdigit():
                continue
            try:
                exe = os.readlink("/proc/%s/exe" % pid)
                with open("/proc/%s/cmdline" % pid, "rb") as fh:
                    cmd = fh.read().replace(b"\0", b" ").decode(errors="replace").strip()
            except OSError:
                continue
            if exe.startswith(self.root + os.sep):
                out.append((int(pid), os.path.basename(exe), cmd))
        return out

    def daemon(self):
        return [p for p in self.procs() if p[1] == "sdlnxd"]

    def phantoms(self):
        return [p for p in self.procs() if p[1] == "sd" and re.search(r"(^|\s)-p\d+", p[2])]

    def stop(self):
        subprocess.run([self.sd, "-stop"], env=self.env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=60)
        time.sleep(1)
        for pid, _, _ in self.procs():
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
        time.sleep(0.5)


def fds(pid):
    """{0: target, 1: target, 2: target} of a process, as /proc shows them"""
    out = {}
    for fd in (0, 1, 2):
        try:
            out[fd] = os.readlink("/proc/%d/fd/%d" % (pid, fd))
        except OSError:
            out[fd] = None
    return out


def read_to_eof(r, limit):
    """read the pipe until end of file or the limit: (saw_eof, bytes, seconds)"""
    data, t0 = b"", time.time()
    while time.time() - t0 < limit:
        rd, _, _ = select.select([r], [], [], 0.25)
        if rd:
            chunk = os.read(r, 4096)
            if not chunk:
                return True, data, time.time() - t0
            data += chunk
    return False, data, time.time() - t0


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-pipefds.py <dir> [--build]")
    root = os.path.abspath(args[0])
    if "--build" in sys.argv:
        if os.path.exists(root) and os.listdir(root):
            bail("%s is not empty" % root)
        r = subprocess.run([sys.executable, TOOL, root, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-pipefds: built, bootstrap passed")
    box = Box(root)
    if not os.path.isfile(box.sd):
        bail("%s holds no built sandbox (use --build, or point it at one)" % root)
    say("sandbox-pipefds: binary %s, SD_CONFIG %s, keyset %s" % (box.sd, box.env["SD_CONFIG"], os.environ.get("SDBOX_KEYSET", "0")))
    box.stop()
    if box.procs():
        bail("processes of this sandbox are still running after a stop: %s" % box.procs())

    say("\n--- sd -start with its output on a pipe -------------------------------------------------------------------")
    r, w = os.pipe()
    p = subprocess.Popen([box.sd, "-start"], env=box.env, stdin=subprocess.DEVNULL, stdout=w, stderr=w)
    os.close(w)
    rc = p.wait(timeout=60)
    eof, data, secs = read_to_eof(r, 10)
    os.close(r)
    say("    sd -start exited %d, printed %r" % (rc, data.decode(errors="replace")))
    d = box.daemon()
    if not d:
        bail("no sdlnxd is running after sd -start (the null case: there is nothing to have held the pipe)")
    f = fds(d[0][0])
    say("    sdlnxd pid %d, fds %s" % (d[0][0], f))
    row("P1 the reader sees end of file while sdlnxd runs (it waited until sd -stop)", eof and "has been started" in data.decode(errors="replace"),
        "no end of file in %.1f s" % secs if not eof else "the success line is missing")
    row("P2 none of sdlnxd's fds 0-2 is a pipe", all(t is not None and not t.startswith("pipe:") for t in f.values()), str(f))
    row("P3 sdlnxd's stdout and stderr are /dev/null", f[1] == "/dev/null" and f[2] == "/dev/null", str(f))
    box.stop()

    say("\n--- CONTROL: sd -start with its output on a file ----------------------------------------------------------")
    log = os.path.join(root, "pipefds-start.log")
    with open(log, "w") as fh:
        subprocess.run([box.sd, "-start"], env=box.env, stdin=subprocess.DEVNULL, stdout=fh, stderr=fh, timeout=60)
    d = box.daemon()
    f = fds(d[0][0]) if d else {}
    say("    sdlnxd %s, fds %s" % (d[0][0] if d else None, f))
    row("P4 CONTROL: a file is kept - sdlnxd's stdout is the caller's file", bool(d) and f.get(1) == log, str(f))
    box.stop()

    say("\n--- CONTROL: sd -start with its output on a terminal ------------------------------------------------------")
    mfd, sfd = os.openpty()
    tty = os.ttyname(sfd)
    subprocess.run([box.sd, "-start"], env=box.env, stdin=subprocess.DEVNULL, stdout=sfd, stderr=sfd, timeout=60)
    os.close(sfd)
    d = box.daemon()
    f = fds(d[0][0]) if d else {}
    say("    terminal %s, sdlnxd %s, fds %s" % (tty, d[0][0] if d else None, f))
    row("P5 CONTROL: a terminal is kept - sdlnxd's stdout is the caller's terminal", bool(d) and f.get(1) == tty, str(f))
    os.close(mfd)

    say("\n--- a session on a pipe that starts a phantom -------------------------------------------------------------")
    # SD is still running from P5.  The phantom sleeps; the session signs off at once.
    r, w = os.pipe()
    body = b"\nTERM 200,9999\nPHANTOM SLEEP 40\nOFF\n"
    p = subprocess.Popen([box.sd], env=box.env, cwd=box.acct, stdin=subprocess.PIPE, stdout=w, stderr=w)
    os.close(w)
    p.stdin.write(body)
    p.stdin.close()
    p.wait(timeout=60)
    eof, data, secs = read_to_eof(r, 15)
    os.close(r)
    out = data.decode(errors="replace")
    say("    session exited %d; output tail %r" % (p.returncode, out[-200:]))
    ph = box.phantoms()
    if not ph:
        bail("no phantom is alive after the session (the null case): output %r" % out[-400:])
    f = fds(ph[0][0])
    say("    phantom pid %d (%s), fds %s" % (ph[0][0], ph[0][2], f))
    row("P6 the session's reader sees end of file while its phantom runs", eof, "no end of file in %.1f s" % secs)
    row("P7 none of the phantom's fds 0-2 is a pipe", all(t is not None and not t.startswith("pipe:") for t in f.values()), str(f))

    say("\n--- a phantom's own log: its stdout and stderr a moment later -----------------------------------------------")
    # Measured 14 Nov 26: a phantom points 1 and 2 at its COMO file itself (op_tio.c) soon after it starts, so the session's
    # file is not kept there - the control of "a file is kept" is P4.  This row says where the phantom's output goes.
    time.sleep(1)
    alive = [p for p in box.phantoms() if p[0] == ph[0][0]]
    f = fds(ph[0][0]) if alive else {}
    say("    phantom %s a second later, fds %s" % (ph[0][0] if alive else None, f))
    row("P8 a second later the phantom's stdout and stderr are its own file in $COMO",
        bool(alive) and all(f.get(n) and "/$COMO/" in f[n] for n in (1, 2)), str(f))

    box.stop()
    say("\n    after: sandbox processes %s" % box.procs())
    say("")
    say("sandbox-pipefds: %d passed, %d failed" % (passed, failed))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
