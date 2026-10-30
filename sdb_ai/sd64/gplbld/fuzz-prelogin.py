#!/usr/bin/env python3
# fuzz-prelogin.py - a ONE-OFF fuzz of the API server's packet parser before any login (W.11 F5, Opus's decision 1a of 30 Oct 2026: "the fuzz is the cheap evidence").
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/fuzz-prelogin.py <sandbox dir> [--n 1500] [--seed 20261030]
#
# NO sudo, NO install: the sandbox is one built by `sandbox-fromtree.py <dir> all` and running (this tool starts it if it is stopped; SDBOX_KEYSET as for every suite).  It is not a regression
# suite and is not in regress.sh: run it by hand when the packet reader (apisrvr, the request loop, the client library's wire format) changes.
#
# WHAT IT DOES.  For each iteration it starts the sandbox's own `sd -Q -C<out>!<in>` (what SDConnectLocal does), writes bytes the parser should refuse or ignore, closes the write end,
# and judges the PROCESS: it must end by itself within 6 seconds with an exit status (not a signal: a crash is a signal), and it must not take the sandbox down.  The inputs are
# generated from a seed (printed), so a failing case is rerun with the same --seed and --n; every crash or hang writes its bytes, in hex, to the output and to fuzz-prelogin.cases.
#   kinds: random bytes; a header with a random type and a random (negative, short, huge, exact) length and a random body; a valid first request (25, local login) then garbage; a valid
#   login sequence (25 then 3 <account>) with one byte flipped or the tail cut; a packet cut short; oversize lengths.
# WHAT IT DOES NOT COVER.  The TLS record layer and the SCRAM exchange of the remote route (sd -n -q, the relay): those need a socket and are test-scramprobe / sandbox-net / the VM's
# witnesses.  This is the LOCAL pipe route's parser, which is the same request loop.
#
# THE INSTRUMENT (CLAUDE.md): it prints the exact command it started, the seed, the number of iterations, a histogram of what the server did (answered / closed / exit status), and the
# NULL CASE - the control, a valid request 25 on a fresh server, must be answered with error 0 before and after the run, and at least a third of the iterations must have produced
# an answer or a clean close, else the run says the harness did not reach the parser and exits 2.
#
# Exit 0 no crash and no hang, 1 a crash or a hang (the cases are printed), 2 the harness could not run or did not reach the parser.
import collections
import os
import random
import select
import signal
import struct
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")


def say(s=""):
    print(s, flush=True)


WAIT_EXIT = 6        # seconds a server may take to end after its input is closed
STUB = None          # --selftest sets a shell command that stands in for the server, to show the judge sees a crash, a hang and a clean exit


def start_server(box):
    r1, w1 = os.pipe()          # server -> us
    r2, w2 = os.pipe()          # us -> server
    env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"))
    env.pop("SDTEST_ADMIN", None)
    argv = [os.path.join(box, "sys", "bin", "sd"), "-Q", "-C%d!%d" % (w1, r2)]
    if STUB:
        argv = ["sh", "-c", STUB]
        env["FUZZ_OUT"] = str(w1)
    p = subprocess.Popen(argv, pass_fds=(w1, r2), env=env, cwd=box, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.close(w1)
    os.close(r2)
    return p, r1, w2, argv


def drain(fd, secs):
    """Everything the server wrote within SECS (until it closes the pipe or nothing more comes for 0.15 s after something did)."""
    out = b""
    end = time.time() + secs
    closed = False
    while time.time() < end:
        r, _, _ = select.select([fd], [], [], 0.1)
        if not r:
            if out:
                break
            continue
        try:
            b = os.read(fd, 65536)
        except OSError:
            closed = True
            break
        if not b:
            closed = True
            break
        out += b
    return out, closed


def packet(ptype, data=b"", length=None):
    n = len(data) + 6 if length is None else length
    return struct.pack("<iH", n, ptype & 0xFFFF) + data


def gen_case(rng, account):
    k = rng.randrange(8)
    if k == 0:
        return "random bytes", bytes(rng.randrange(256) for _ in range(rng.randrange(0, 80)))
    if k == 1:
        return "random header, honest length", packet(rng.randrange(0, 100), bytes(rng.randrange(256) for _ in range(rng.randrange(0, 60))))
    if k == 2:
        n = rng.choice([-2147483648, -1, 0, 1, 5, 6, 7, 65535, 65536, 1 << 20, 1 << 30, 2147483647])
        return "random header, length %d" % n, packet(rng.randrange(0, 100), bytes(rng.randrange(256) for _ in range(rng.randrange(0, 40))), n)
    if k == 3:
        return "valid 25 then garbage", packet(25) + bytes(rng.randrange(256) for _ in range(rng.randrange(0, 60)))
    if k == 4:
        good = packet(25) + packet(3, account.encode())
        b = bytearray(good)
        for _ in range(rng.randrange(1, 4)):
            b[rng.randrange(len(b))] = rng.randrange(256)
        return "login sequence, bytes flipped", bytes(b)
    if k == 5:
        good = packet(25) + packet(3, account.encode())
        return "login sequence, cut short", good[:rng.randrange(1, len(good))]
    if k == 6:
        return "type %d with a long body" % 3, packet(rng.choice([3, 4, 6, 25, 29, 32]), bytes(rng.randrange(256) for _ in range(rng.randrange(200, 4000))))
    return "many small packets", b"".join(packet(rng.randrange(0, 100), bytes(rng.randrange(256) for _ in range(rng.randrange(0, 8)))) for _ in range(rng.randrange(2, 12)))


def run_one(box, data, rng):
    p, rd, wr, argv = start_server(box)
    try:
        # the bytes in chunks of random size, with a pause so that the server reads them as separate reads
        i = 0
        while i < len(data):
            n = rng.randrange(1, max(2, len(data) - i + 1))
            try:
                os.write(wr, data[i:i + n])
            except OSError:
                break
            i += n
            time.sleep(0.003)
        out, closed = drain(rd, 0.5)
        try:
            os.close(wr)
        except OSError:
            pass
        wr = -1
        end = time.time() + WAIT_EXIT
        while p.poll() is None and time.time() < end:
            more, c2 = drain(rd, 0.2)
            out += more
        if p.poll() is None:
            p.kill()
            p.wait()
            return "HANG", out, argv
        if p.returncode < 0:
            return "CRASH signal %d (%s)" % (-p.returncode, signal.Signals(-p.returncode).name), out, argv
        return ("answered, exit %d" % p.returncode if out else "silent, exit %d" % p.returncode), out, argv
    finally:
        for fd in (rd, wr):
            if fd >= 0:
                try:
                    os.close(fd)
                except OSError:
                    pass
        if p.poll() is None:
            p.kill()
            p.wait()


def control(box):
    """A valid request 25 must be answered with error 0: the harness reaches the parser."""
    p, rd, wr, argv = start_server(box)
    try:
        os.write(wr, packet(25))
        out, closed = drain(rd, 5)
        ok = len(out) >= 10 and struct.unpack("<ihi", out[:10])[1] == 0
        return ok, out[:16].hex(" ")
    finally:
        os.close(wr)
        os.close(rd)
        try:
            p.wait(timeout=6)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait()


def selftest():
    """The judge must see what it is for: a server that dies of a signal is a CRASH, one that never ends is a HANG, one that ends by itself is clean."""
    global STUB, WAIT_EXIT
    WAIT_EXIT = 4                 # a crash that dumps core can take a moment to end (the core handler holds the process)
    rng = random.Random(1)
    rows = []
    for name, stub, want in (("a segmentation fault", "kill -SEGV $$", "CRASH signal 11"), ("an abort", "kill -ABRT $$", "CRASH signal 6"),
                             ("a server that never ends", "sleep 30", "HANG"), ("a server that ends at once, silent", "exit 0", "silent, exit 0"),
                             ("a server that answers and ends", "printf x >&$FUZZ_OUT; exit 3", "answered, exit 3")):
        STUB = stub
        got, out, argv = run_one("/tmp", b"\x00" * 8, rng)
        rows.append((name, got.startswith(want), got))
        say("  [%s] %s: the judge says %r (wanted %r)" % ("PASS" if got.startswith(want) else "FAIL", name, got, want))
    STUB = None
    bad = [r for r in rows if not r[1]]
    say("fuzz-prelogin --selftest: %d of %d judged right" % (len(rows) - len(bad), len(rows)))
    return 1 if bad else 0


def main():
    if "--selftest" in sys.argv:
        return selftest()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    n = 1500
    seed = 20261030
    for i, a in enumerate(sys.argv):
        if a == "--n":
            n = int(sys.argv[i + 1])
            args = [x for x in args if x != sys.argv[i + 1]]
        if a == "--seed":
            seed = int(sys.argv[i + 1])
            args = [x for x in args if x != sys.argv[i + 1]]
    if len(args) != 1:
        say("usage: fuzz-prelogin.py <sandbox dir> [--n 1500] [--seed 20261030]")
        return 2
    box = os.path.abspath(args[0])
    if not os.path.isfile(os.path.join(box, "sys", "bin", "sd")):
        say("CANNOT RUN: %s holds no built sandbox" % box)
        return 2
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, timeout=120)
    import getpass
    account = getpass.getuser()
    rng = random.Random(seed)
    say("fuzz-prelogin: sandbox %s, seed %d, %d iterations, the server is `%s -Q -C<out>!<in>` as %s" % (box, seed, n, os.path.join(box, "sys", "bin", "sd"), account))
    ok0, raw0 = control(box)
    say("control before: request 25 answered with error 0: %s (%s)" % (ok0, raw0))
    if not ok0:
        say("CANNOT RUN: the control request was not answered - the harness does not reach the parser")
        return 2
    hist = collections.Counter()
    bad = []
    kinds = collections.Counter()
    t0 = time.time()
    for i in range(n):
        kind, data = gen_case(rng, account)
        verdict, out, argv = run_one(box, data, rng)
        hist[verdict] += 1
        kinds[kind] += 1
        if verdict.startswith("CRASH") or verdict == "HANG":
            bad.append((i, kind, verdict, data))
            say("  !! iteration %d (%s): %s   input %d bytes: %s" % (i, kind, verdict, len(data), data[:96].hex(" ")))
        if (i + 1) % 250 == 0:
            say("  %d iterations, %d s, so far: %s" % (i + 1, time.time() - t0, dict(hist)))
    ok1, raw1 = control(box)
    say("control after : request 25 answered with error 0: %s (%s)" % (ok1, raw1))
    say("\nwhat the server did: %s" % dict(hist))
    say("what was sent   : %s" % dict(kinds))
    reached = sum(v for k, v in hist.items() if k.startswith("answered") or k.startswith("silent"))
    answered = sum(v for k, v in hist.items() if k.startswith("answered"))
    say("answered %d of %d (the share that proves the bytes reached the parser)" % (answered, n))
    if bad:
        with open("fuzz-prelogin.cases", "w") as f:
            for i, kind, verdict, data in bad:
                f.write("%d\t%s\t%s\t%s\n" % (i, kind, verdict, data.hex()))
        say("\nFAILED: %d crash(es) or hang(s); the cases are in fuzz-prelogin.cases (hex)" % len(bad))
        return 1
    if not ok1:
        say("\nFAILED: the server no longer answers after the run")
        return 1
    if answered < n // 3:
        say("\nCANNOT JUDGE: only %d of %d iterations were answered - the harness may not have reached the parser" % (answered, n))
        return 2
    say("\nfuzz-prelogin: %d iterations, no crash, no hang, and the server still answers" % n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
