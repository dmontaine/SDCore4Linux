#!/usr/bin/env python3
"""api-threads-probe.py - the client library used by several threads over TCP.

QMClient sheet 456, 15 Oct 2026.  The same checks as part R of sandbox-qmclient.py
(local sessions in a sandbox), but every session is a real TCP login to the
installed listener with SDConnect, which is what only an owner-run witness can reach.

  SD_PROBE_PASSWORD=... python3 -I /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/api-threads-probe.py \
      --user <name> --account <name> --file <name> [--threads N]

No sudo of its own.  It needs a Linux user with an SD password (a throwaway made by
witness-release-run.sh section 13l) and a hashed or dynamic file <name> in the account,
which the probe writes and deletes records in: thr0, thr1, ...

UNRUN when written (15 Oct 26): it compiles, and nothing more is claimed until
witness-release-run.sh 13l has run it.

THE PASSWORD COMES FROM THE ENVIRONMENT, NEVER THE COMMAND LINE.  Only its length is
printed.  IT PRINTS WHAT IT DID: the library, host, port, user, account and file passed;
each thread's connect result, session index and user number; the counts behind every
verdict.  A line "T<n> PASS ..." or "T<n> FAIL ..." is one verdict.

  T1 every thread connects at the same moment and is given a session index of its own and
     a user number of its own (the user number is the server process's, so it also shows
     that the sessions are distinct on the SERVER)
  T2 each thread's current session stays its own through 100 rounds of asking while the
     others do the same (SDGetSession and @USERNO never name another thread's)
  T3 each thread writes a record of its own size (3 KB upwards) and reads it back 40 times
     at the same moment as the others: every read is exactly what it wrote
  T4 a connect that fails (the wrong password, refused by the server) keeps its error text
     for its own thread while another thread connects and disconnects ten times
  T5 CONTROL: afterwards one thread connects, asks @WHO and disconnects, as before
  T6 the threads ended normally: no exception, no broken barrier

Exit 0 every verdict passed, 1 one failed, 2 it could not run (no password, no library,
fewer than 2 threads, or no thread connected at all - a probe that measured nothing).
"""

import argparse
import ctypes
import os
import sys
import threading

DEFAULT_LIB = "/usr/local/sdsys/bin/sdclilib.so"
ROUNDS = 100
READS = 40
CHURN = 10

LOCK = threading.Lock()


def say(text):
    with LOCK:
        print(text)
        sys.stdout.flush()


def main(argv):
    ap = argparse.ArgumentParser(description="The SD client library from several threads over TCP.")
    ap.add_argument("--lib", default=DEFAULT_LIB)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=4247)
    ap.add_argument("--user", required=True)
    ap.add_argument("--account", required=True)
    ap.add_argument("--file", required=True, help="a file of the account the threads write records in")
    ap.add_argument("--threads", type=int, default=4)
    a = ap.parse_args(argv)

    pw = os.environ.get("SD_PROBE_PASSWORD")
    say("api-threads-probe")
    say("  lib      : %s" % a.lib)
    say("  host     : %s  port %d" % (a.host, a.port))
    say("  user     : %s" % a.user)
    say("  account  : %s" % a.account)
    say("  file     : %s" % a.file)
    say("  threads  : %d" % a.threads)
    say("  password : %s" % ("from SD_PROBE_PASSWORD, %d characters" % len(pw)
                             if pw is not None else "SD_PROBE_PASSWORD is not set"))
    if pw is None:
        say("api-threads-probe: CANNOT RUN - SD_PROBE_PASSWORD is not set.")
        return 2
    if a.threads < 2:
        say("api-threads-probe: CANNOT RUN - fewer than 2 threads would measure nothing about threads.")
        return 2
    try:
        lib = ctypes.CDLL(a.lib)
    except OSError as e:
        say("api-threads-probe: CANNOT RUN - cannot load %s: %s" % (a.lib, e))
        return 2

    need = ("SDConnect", "SDDisconnect", "SDConnected", "SDGetSession", "SDGetVar", "SDOpen", "SDRead", "SDWrite", "SDDelete",
            "SDError", "SDFree")
    missing = [fn for fn in need if not hasattr(lib, fn)]
    if missing:
        say("api-threads-probe: CANNOT RUN - %s has no %s (an older install than the one this probe is for)" % (a.lib, ", ".join(missing)))
        return 2

    nt = a.threads
    host, port = a.host.encode(), a.port
    user, account, fname = a.user.encode(), a.account.encode(), a.file.encode()
    good, bad_pw = pw.encode(), (pw + "x").encode()

    for fn in ("SDGetVar", "SDRead", "SDError"):
        getattr(lib, fn).restype = ctypes.c_void_p
    for fn in ("SDOpen", "SDConnect", "SDGetSession", "SDConnected"):
        getattr(lib, fn).restype = ctypes.c_int
    lib.SDConnect.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]

    def text(p):
        if not p:
            return None
        b = ctypes.string_at(p)
        lib.SDFree(ctypes.c_void_p(p))
        return b

    def err():
        p = lib.SDError()
        return ctypes.string_at(p) if p else b""

    errors = []
    bar = threading.Barrier(nt, timeout=90)
    sess = [None] * nt

    def phases(i):
        s = {"ok": None, "idx": None, "who": None, "bad": None, "wrong": None, "wrote": None}
        sess[i] = s
        bar.wait()                                    # everyone connects at the same moment
        s["ok"] = lib.SDConnect(host, port, user, good, account)
        s["idx"] = lib.SDGetSession()
        who = text(lib.SDGetVar(b"@USERNO"))
        s["who"] = None if who is None else who.decode("latin-1")
        bar.wait()                                    # then everyone asks which session is its own, over and over
        bad = 0
        for _ in range(ROUNDS):
            if lib.SDGetSession() != s["idx"]:
                bad += 1
            w = text(lib.SDGetVar(b"@USERNO"))
            if w is None or w.decode("latin-1") != s["who"]:
                bad += 1
        s["bad"] = bad
        fno = lib.SDOpen(fname)                       # then everyone writes and reads back a record of its own size
        rid = ("thr%d" % i).encode()
        data = bytes([65 + i]) * (3000 + 7000 * i)
        s["wrote"] = len(data) if fno >= 1 else 0
        lib.SDWrite(fno, rid, data)
        bar.wait()
        wrong = 0
        for _ in range(READS):
            got = text(lib.SDRead(fno, rid, ctypes.byref(ctypes.c_int())))
            if got != data:
                wrong += 1
        s["wrong"] = wrong
        bar.wait()
        lib.SDDelete(fno, rid)
        lib.SDDisconnect()

    def guard(fn, *args):
        try:
            fn(*args)
        except Exception as e:                        # a broken barrier included
            errors.append(repr(e))

    ts = [threading.Thread(target=guard, args=(phases, i)) for i in range(nt)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(150)

    ss = [x for x in sess if x]
    for i, x in enumerate(sess):
        say("  thread %d: %r" % (i, x))

    if not ss or not any(x["ok"] == 1 for x in ss):
        say("api-threads-probe: CANNOT RUN - no thread connected, so nothing about threads was measured. errors %r" % errors)
        return 2

    passed = failed = 0

    def verdict(n, name, ok, detail):
        nonlocal passed, failed
        if ok:
            passed += 1
        else:
            failed += 1
        say("T%s %s %s: %s" % (n, "PASS" if ok else "FAIL", name, detail))

    verdict("1", "distinct sessions", len(ss) == nt and all(x["ok"] == 1 for x in ss)
            and len({x["idx"] for x in ss}) == nt and len({x["who"] for x in ss}) == nt and None not in {x["who"] for x in ss},
            repr([(x["ok"], x["idx"], x["who"]) for x in ss]))
    verdict("2", "the current session is per thread", len(ss) == nt and all(x["bad"] == 0 for x in ss),
            "%d rounds each, wrong answers %r" % (ROUNDS, [x["bad"] for x in ss]))
    verdict("3", "no mixed buffers", len(ss) == nt and all(x["wrong"] == 0 and x["wrote"] for x in ss),
            "%d reads each, sizes %r, wrong reads %r" % (READS, [x["wrote"] for x in ss], [x["wrong"] for x in ss]))

    # a connect that fails keeps its error for its own thread while another thread connects and disconnects
    bar4 = threading.Barrier(2, timeout=120)
    box = {}

    def failer():
        box["r"] = lib.SDConnect(host, port, user, bad_pw, account)       # refused by the server: slow on purpose (a delay)
        box["e1"] = err().decode("latin-1")
        bar4.wait()                                   # the other thread connects and disconnects ten times now
        bar4.wait()
        box["e2"] = err().decode("latin-1")           # before SDConnected(), which clears the error text
        box["connected"] = lib.SDConnected()

    def churner():
        bar4.wait()
        n = 0
        for _ in range(CHURN):
            if lib.SDConnect(host, port, user, good, account) == 1:
                n += 1
                lib.SDDisconnect()
        box["churn"] = n
        bar4.wait()

    t1 = threading.Thread(target=guard, args=(failer,))
    t2 = threading.Thread(target=guard, args=(churner,))
    t1.start()
    t2.start()
    t1.join(240)
    t2.join(240)
    say("  failed-connect thread: %r" % box)
    verdict("4", "a failed connect keeps its error", box.get("r") == 0 and box.get("e1", "") != ""
            and box.get("e2") == box.get("e1") and box.get("churn") == CHURN and box.get("connected") == 0, repr(box))

    ok = lib.SDConnect(host, port, user, good, account)
    who = text(lib.SDGetVar(b"@WHO"))
    lib.SDDisconnect()
    verdict("5", "control, one thread as before", ok == 1 and who is not None and who.decode("latin-1") == a.account,
            "connect %r, @WHO %r" % (ok, who))
    verdict("6", "the threads ended normally", not errors and not any(t.is_alive() for t in ts), "errors %r" % errors)

    say("api-threads-probe: %d passed, %d failed" % (passed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
