#!/usr/bin/env python3
#
# verify-semaphores.py - does a session that dies HOLDING an SD semaphore give it
#                        back?  Task table W.0, owner's ruling of 14 Sep 2026:
#                        SEM_UNDO on the lock (sdsem.c) AND a release on the
#                        fatal-signal path (kernel.c fatal_signal_handler).
#
#   python3 /home/don/Projects/SDCoreLinuxProject/sdcore4linux/sdb_ai/sd64/gplbld/verify-semaphores.py
#   python3 .../verify-semaphores.py --allow-stale     measure a stale install
#
# NO SUDO.  Exit 0 every decisive check passed, 1 a decisive check failed,
# 2 the test could not be run.
#
# ***DO NOT RUN THIS AGAINST AN INSTALL WITHOUT THE FIX.***  Before W.0 a session
# killed while holding a semaphore left it taken, and every SD process then spun
# for ever - the system-wide wedge of 11 Sep 2026, which needed a reboot.  This
# file sets out to kill a session at exactly that moment.  assert-current is
# enforced for that reason, not only for honesty.
#
# THE INSTRUMENT IS THE KERNEL'S OWN VIEW OF THE SET: `ipcs -s -i <semid>` prints
# each semaphore's value and the pid of its last operation, readable without
# sudo (the set is 0666).  An SD semaphore is a mutex: 1 free, 0 held.
#
# ***HOW IT CATCHES A HOLD, AND THE SAFETY RULE THAT GOES WITH IT.***  It starts
# its own piped sessions (as the caller, in the caller's account) that take
# semaphores constantly.  When a sample shows a value of 0 whose last operator
# is ONE OF ITS OWN SESSIONS, it SIGSTOPs that session and samples again; if the
# value is still 0 with the same pid, that session is frozen holding it - a
# CONFIRMED hold.  Then:
#   KILL round  SIGKILL it.  Nothing in SD runs; only the kernel's SEM_UNDO can
#               give the semaphore back.  The value must return to 1.
#   FAULT round SIGSEGV it, then SIGCONT.  fatal_signal_handler runs first and
#               releases what the owner table says it holds; the value must
#               return to 1 and must never reach 2 (a release of something not
#               held, or SEM_UNDO undoing a release the handler already made).
# ***IT NEVER SIGNALS A PROCESS IT DID NOT START***, and a stop that does not
# confirm is followed by SIGCONT at once.
#
# ***THE NULL CASE IS REFUSED OUT LOUD.***  Holds last microseconds and ipcs runs
# in milliseconds, so a round can end without catching one.  Such a round's
# release row FAILS as "no hold was caught" - it is not a pass.  Run it again.
#
# ***AND NO VALUE MAY EVER READ ABOVE 1***, in any sample of the whole run.  That
# is the risk the change itself carries: SEM_UNDO on one half of a lock/unlock
# pair and not the other, or a release of a semaphore that was not held, turns a
# mutex into a count of 2 - two holders at once - and nothing else would say so.
#
# Killed and faulted sessions leave user-table slots; sdlnxd reaps them within
# about a minute (sdlnxd.c:97, :134).  A SIGSEGV also writes "Fault type" to the
# error log.
#
import argparse
import os
import re
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sdverify as V                                    # noqa: E402

NAME = "verify-semaphores"
SEM_KEY = "0x716d0302"          # gplsrc/sddefs.h:78 SD_SEM_KEY
NSEMS = 6                       # gplsrc/sysseg.h:125 NUM_SEMAPHORES
WORKERS = 10
ROUND_SECS = 40
# Each worker repeats commands that open files and read them - FILE_TABLE_LOCK,
# SHORT_CODE and the DH paths - so semaphores are taken all the time.
WORK = ["COUNT VOC", "LIST VOC SAMPLE 3", "COUNT $hold"] * 150


def semid_for_key():
    out = subprocess.run(["ipcs", "-s"], stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, universal_newlines=True).stdout
    for line in out.splitlines():
        f = line.split()
        if len(f) >= 5 and f[0].lower() == SEM_KEY:
            return f[1], line.strip()
    return None, out


def sample(semid):
    """[(semnum, value, pid)] from ipcs -s -i, or None if it could not be read."""
    p = subprocess.run(["ipcs", "-s", "-i", semid], stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, universal_newlines=True)
    rows = []
    for line in p.stdout.splitlines():
        m = re.match(r"^\s*(\d+)\s+(-?\d+)\s+\d+\s+\d+\s+(\d+)\s*$", line)
        if m:
            rows.append((int(m.group(1)), int(m.group(2)), int(m.group(3))))
    return rows if len(rows) == NSEMS else None


def start_workers(acct):
    body = V.build_session(WORK)
    procs = []
    for _ in range(WORKERS):
        p = subprocess.Popen([V.SD], cwd=acct, stdin=subprocess.PIPE,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             universal_newlines=True)
        try:
            p.stdin.write(body)
            p.stdin.close()
        except (BrokenPipeError, OSError):
            pass
        procs.append(p)
    return procs


def stop_workers(procs):
    for p in procs:
        if p.poll() is None:
            try:
                p.send_signal(signal.SIGCONT)
            except OSError:
                pass
    deadline = time.time() + 60
    for p in procs:
        try:
            p.wait(timeout=max(1, deadline - time.time()))
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait()


def one_round(run, semid, acct, mode, state):
    """Catch a hold, then KILL or FAULT the holder.  Returns a dict."""
    procs = start_workers(acct)
    ours = {p.pid: p for p in procs}
    run.say("  %s round: %d sessions started, pids %s"
            % (mode, len(procs), " ".join(str(p) for p in sorted(ours))))
    caught = None
    samples = 0
    deadline = time.time() + ROUND_SECS
    try:
        while time.time() < deadline and caught is None:
            rows = sample(semid)
            if rows is None:
                continue
            samples += 1
            state["max"] = max(state["max"], max(v for _, v, _ in rows))
            for semnum, value, pid in rows:
                if value != 0 or pid not in ours or ours[pid].poll() is not None:
                    continue
                os.kill(pid, signal.SIGSTOP)
                again = sample(semid)
                if again and again[semnum][1] == 0 and again[semnum][2] == pid:
                    caught = (semnum, pid)
                    break
                os.kill(pid, signal.SIGCONT)
        run.say("    %d samples taken; hold caught: %s" % (samples, caught))
        if caught is None:
            return {"caught": False, "samples": samples}
        semnum, pid = caught
        run.say("    CONFIRMED: session %d is stopped holding semaphore %d (value 0)"
                % (pid, semnum))
        if mode == "KILL":
            os.kill(pid, signal.SIGKILL)
        else:
            os.kill(pid, signal.SIGSEGV)
            os.kill(pid, signal.SIGCONT)
        ours[pid].wait(timeout=30)
        rc = ours[pid].returncode
        run.say("    holder %d ended with %s" % (pid, rc))
        back = None
        t0 = time.time()
        while time.time() - t0 < 10:
            rows = sample(semid)
            if rows:
                state["max"] = max(state["max"], max(v for _, v, _ in rows))
                if rows[semnum][1] >= 1:
                    back = rows[semnum]
                    break
            time.sleep(0.05)
        run.say("    semaphore %d after: %s (%.2f s)"
                % (semnum, back, time.time() - t0))
        return {"caught": True, "semnum": semnum, "pid": pid, "rc": rc,
                "back": back}
    finally:
        stop_workers(procs)


def main():
    ap = argparse.ArgumentParser(description="a dead holder gives back its semaphore")
    ap.add_argument("--allow-stale", action="store_true",
                    help="measure an install assert-current calls stale (NOT one without W.0)")
    a = ap.parse_args()

    run = V.Run(NAME)
    user = os.environ.get("USER") or "?"
    acct = os.path.join(V.ACCOUNTS, user)
    run.say("%s: as %s (uid %d), NOT elevated" % (NAME, user, os.geteuid()))
    run.say("  sd        %s" % V.SD)
    run.say("  account   %s" % acct)
    run.say("  key       %s, %d semaphores; %d sessions per round, %d s to catch a hold"
            % (SEM_KEY, NSEMS, WORKERS, ROUND_SECS))

    run.heading("0. preconditions")
    if V.require_not_root(run, "Only the caller's own sessions may be signalled."):
        return run.verdict()
    if V.require_paths(run, V.SD, acct):
        return run.verdict()
    if a.allow_stale:
        run.say("  *** --allow-stale: assert-current is NOT being enforced.")
        V.require_current(run)
        run.blocked = None
    elif V.require_current(run):
        return run.verdict()
    if V.require_running(run, acct):
        return run.verdict()
    semid, line = semid_for_key()
    if semid is None:
        run.refuse("no semaphore set with key %s" % SEM_KEY, line)
        return run.verdict()
    run.say("  ipcs: %s" % line)

    state = {"max": 0}
    run.heading("1. baseline: idle, every semaphore free")
    rows = None
    for _ in range(40):
        rows = sample(semid)
        if rows and all(v == 1 for _, v, _ in rows):
            break
        time.sleep(0.25)
    run.say("      %s" % rows)
    if rows is None:
        run.refuse("ipcs -s -i %s could not be read" % semid)
        return run.verdict()
    state["max"] = max(v for _, v, _ in rows)
    run.note("B1 every semaphore reads 1 before the test", True,
             all(v == 1 for _, v, _ in rows))

    run.heading("2. KILL: a session killed while holding - only SEM_UNDO can release")
    k = one_round(run, semid, acct, "KILL", state)
    run.note("K0 a hold was caught (not the null case)", True, k["caught"])
    if k["caught"]:
        run.note("K1 the holder was killed (-9)", -9, k["rc"])
        run.note("K2 THE ROW: its semaphore came back to 1", True,
                 bool(k["back"]) and k["back"][1] == 1)

    run.heading("3. FAULT: SIGSEGV while holding - fatal_signal_handler releases")
    f = one_round(run, semid, acct, "FAULT", state)
    run.note("F0 a hold was caught (not the null case)", True, f["caught"])
    if f["caught"]:
        run.note("F1 the holder died of SIGSEGV (-11)", -11, f["rc"])
        run.note("F2 THE ROW: its semaphore came back to 1", True,
                 bool(f["back"]) and f["back"][1] == 1)

    run.heading("4. afterwards: idle again, and never a count of 2")
    rows = None
    for _ in range(80):
        rows = sample(semid)
        if rows:
            state["max"] = max(state["max"], max(v for _, v, _ in rows))
            if all(v == 1 for _, v, _ in rows):
                break
        time.sleep(0.25)
    run.say("      %s" % rows)
    run.note("A1 every semaphore reads 1 once the sessions have gone", True,
             bool(rows) and all(v == 1 for _, v, _ in rows))
    run.note("A2 no sample in the whole run read above 1 (no double release)",
             True, state["max"] <= 1)
    run.say("      highest value seen in any sample: %d" % state["max"])
    run.say("  Killed and faulted sessions' user slots are reaped by sdlnxd within")
    run.say("  about a minute; the SIGSEGV also logged \"Fault type\" to errlog.")

    rc = run.verdict()
    if a.allow_stale:
        run.say("  (measured with --allow-stale: the install is NOT current.)")
    return rc


if __name__ == "__main__":
    sys.exit(main())
