#!/usr/bin/env python3
"""test-semlock-units.py - a removed semaphore set ends a process; sd -stop ends what outlives SIGTERM (8 Nov 26, S.177).

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-semlock-units.py
  python3 .../test-semlock-units.py --selftest

No sudo, no install, no sd.  Exit 0 all checks passed, 1 a check failed, 2 it could not run.

THE DEFECT (found 8 Nov 2026 on the test VPS): four SD sessions ran at 84-92% CPU for 8-10 hours.  strace showed each in
semtimedop(...IPC_NOWAIT) -> EINVAL, sched_yield, about 36,000 times a second: LockSemaphore (sdsem.c) retried on EVERY
error, and stop_sd (sysseg.c) had removed the set after its ten-second wait although the sessions were still attached -
they had had a SIGHUP, after which signal_handler (linuxio.c) ignores SIGTERM.  SIGTERM could not end them; SIGKILL did.

THE FIX, AS HELD HERE: (1) LockSemaphore retries only on EAGAIN and EINTR (semaphore_busy) and otherwise calls
semaphores_gone, which logs and calls _exit - never exit(), whose handlers may lock, and never anything that locks;
(2) "sd -stop" and "sd -restart" call stop_sd_ex(TRUE), which after the wait SIGKILLs only processes whose
/proc/<pid>/maps holds SD's segment key (/SYSV<SD_SHM_KEY>), before the segment and the semaphores are removed; plain
stop_sd() - the failure paths of bind_sysseg() - is stop_sd_ex(FALSE) and kills nobody.

***WHAT THIS IS AND IS NOT.***  It reads gplsrc/sdsem.c, sysseg.c and sd.c as text.  It cannot say a process ends when its
set is removed or that sd -stop ends a survivor: a sandbox start / stop is the runtime row, and the real case (a
hung-up session outliving a service stop) is a VPS or VM witness.  --selftest mutates the source and requires each
mutant to be caught.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, os.pardir, "gplsrc"))
FILES = ("sdsem.c", "sysseg.c", "sd.c")


def strip_comments(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def body(code, signature):
    """The body of the C function whose definition starts with signature (comments already stripped)."""
    i = code.find(signature)
    if i < 0:
        return None
    j = code.find("{", i)
    depth = 0
    for k in range(j, len(code)):
        if code[k] == "{":
            depth += 1
        elif code[k] == "}":
            depth -= 1
            if depth == 0:
                return code[j + 1:k]
    return None


def checks(src):
    out = []

    def ck(name, ok, detail=""):
        out.append((name, bool(ok), detail))

    sem = strip_comments(src["sdsem.c"])
    seg = strip_comments(src["sysseg.c"])
    sdc = strip_comments(src["sd.c"])

    # --- sdsem.c
    busy = body(sem, "static bool semaphore_busy(int err)")
    ck("semaphore_busy() is there", busy is not None)
    if busy is not None:
        names = sorted(set(re.findall(r"\bE[A-Z]+\b", busy)))
        ck("semaphore_busy() is true for EAGAIN and EINTR and no other errno", names == ["EAGAIN", "EINTR"], names)
    gone = body(sem, "static void semaphores_gone(int semno, int err)")
    ck("semaphores_gone() is there", gone is not None)
    if gone is not None:
        ck("semaphores_gone() ends with _exit()", re.search(r"\b_exit\s*\(", gone) is not None)
        ck("semaphores_gone() never calls exit() (its handlers may lock)", re.search(r"(?<![_\w])exit\s*\(", gone) is None)
        locking = [w for w in ("LockSemaphore", "StartExclusive", "log_printf", "log_message", "audit_message")
                   if re.search(r"\b%s\s*\(" % w, gone)]
        ck("semaphores_gone() calls nothing that takes a semaphore", not locking, locking)
        ck("semaphores_gone() says why, in syslog", re.search(r"\bsyslog\s*\(", gone) is not None)
    lock = body(sem, "void LockSemaphore(int semno)")
    ck("LockSemaphore() is there", lock is not None)
    if lock is not None:
        loop = re.search(r"while\s*\(\s*semop\s*\(\s*semid\s*,\s*&sem_lock\s*,\s*1\s*\)\s*\)\s*\{(.*?)\}", lock, re.S)
        ck("LockSemaphore() loops on semop(semid, &sem_lock, 1)", loop is not None)
        if loop:
            inner = loop.group(1)
            test = re.search(r"if\s*\(\s*!\s*semaphore_busy\s*\(\s*errno\s*\)\s*\)\s*semaphores_gone\s*\(", inner)
            ck("inside the loop a non-busy errno calls semaphores_gone()", test is not None)
            yld = inner.find("RelinquishTimeslice")
            ck("the semaphores_gone() test comes before the yield", test is not None and yld > test.start(), yld)

    # --- sysseg.c
    plain = body(seg, "bool stop_sd()")
    ck("stop_sd() is there", plain is not None)
    if plain is not None:
        ck("stop_sd() is stop_sd_ex(FALSE) and nothing else",
           re.fullmatch(r"\s*return\s+stop_sd_ex\s*\(\s*FALSE\s*\)\s*;\s*", plain) is not None, plain.strip())
    ex = body(seg, "bool stop_sd_ex(bool kill_survivors)")
    ck("stop_sd_ex() is there", ex is not None)
    if ex is not None:
        calls = [m.start() for m in re.finditer(r"\bend_attached_survivors\s*\(", ex)]
        ck("stop_sd_ex() calls end_attached_survivors() once", len(calls) == 1, len(calls))
        guard = re.search(r"if\s*\(\s*kill_survivors\s*&&[^\n]*\n[^\n]*end_attached_survivors\s*\(", ex)
        ck("the call is guarded by kill_survivors", guard is not None)
        rmid = ex.find("IPC_RMID")
        delsem = ex.find("delete_semaphores")
        ck("the survivors are ended before the segment and the semaphores are removed",
           calls and rmid > calls[0] and delsem > calls[0], (calls, rmid, delsem))
    ends = body(seg, "static int end_attached_survivors(void)")
    ck("end_attached_survivors() is there", ends is not None)
    if ends is not None:
        ck("the tag is SD's own segment key as /proc/<pid>/maps writes it",
           re.search(r'"/SYSV%08x"\s*,\s*\(unsigned int\)\s*SD_SHM_KEY', ends) is not None)
        ck("it reads /proc/<pid>/maps", '"/proc/%d/maps"' in ends)
        ck("it skips itself and pids 0 and 1", re.search(r"pid\s*<=\s*1\s*\)\s*\|\|\s*\(\s*pid\s*==\s*self", ends) is not None)
        kills = re.findall(r"\bkill\s*\(([^)]*)\)", ends)
        ck("its one kill() is SIGKILL", kills == ["pid, SIGKILL"], kills)
        ck("a pid is killed only when its maps held the tag",
           re.search(r"if\s*\(\s*attached\s*&&\s*\(\s*kill\s*\(", ends) is not None
           and re.search(r"strstr\s*\(\s*line\s*,\s*tag\s*\)[^;]*\{\s*attached\s*=\s*TRUE", ends) is not None)
    bind = body(seg, "bool bind_sysseg(bool create, char* errmsg)")
    ck("bind_sysseg()'s failure path uses plain stop_sd(), not the killing form",
       bind is not None and re.search(r"\bstop_sd\s*\(\s*\)", bind) is not None and "stop_sd_ex" not in bind)

    # --- sd.c
    for opt in ("-STOP", "-RESTART"):
        m = re.search(r'stricmp\(argv\[arg\],\s*"%s"\)[^{]*\{(.*?)\n\s{10}\}' % opt, sdc, re.S)
        ck("sd %s calls stop_sd_ex(TRUE)" % opt.lower(), m is not None and "stop_sd_ex(TRUE)" in m.group(1)
           and re.search(r"\bstop_sd\s*\(", m.group(1)) is None)
    every = sum(len(re.findall(r"stop_sd_ex\s*\(\s*TRUE\s*\)", strip_comments(t))) for t in src.values())
    ck("stop_sd_ex(TRUE) is called from exactly those two places", every == 2, every)
    return out


def mutants(src):
    def mut(name, fname, old, new):
        m = dict(src)
        m[fname] = src[fname].replace(old, new, 1)
        return (name, m, m[fname] != src[fname])
    return [
        mut("EINVAL counted as busy (the old spin)", "sdsem.c",
            "return (err == EAGAIN) || (err == EINTR);", "return (err == EAGAIN) || (err == EINTR) || (err == EINVAL);"),
        mut("the gone test taken out of the loop", "sdsem.c",
            "    if (!semaphore_busy(errno))\n      semaphores_gone(semno, errno);\n", ""),
        mut("exit() instead of _exit()", "sdsem.c", "  _exit(3);", "  exit(3);"),
        mut("semaphores_gone() logs through log_printf (it locks)", "sdsem.c",
            '  syslog(LOG_ERR, "%s", msg);', '  log_printf("%s", msg);'),
        mut("plain stop_sd() kills", "sysseg.c", "return stop_sd_ex(FALSE);", "return stop_sd_ex(TRUE);"),
        mut("the kill_survivors guard dropped", "sysseg.c",
            "if (kill_survivors && !shmctl(", "if (!shmctl("),
        mut("a pid killed without the maps test", "sysseg.c",
            "if (attached && (kill(pid, SIGKILL) == 0))", "if ((kill(pid, SIGKILL) == 0))"),
        mut("the tag made from the semaphore key", "sysseg.c",
            "(unsigned int)SD_SHM_KEY);", "(unsigned int)SD_SEM_KEY);"),
        mut("SIGTERM again instead of SIGKILL", "sysseg.c",
            "kill(pid, SIGKILL)", "kill(pid, SIGTERM)"),
        mut("sd -stop back to plain stop_sd()", "sd.c",
            "if (stop_sd_ex(TRUE)) {\n              printf(\"SD (%s) has been shut down",
            "if (stop_sd()) {\n              printf(\"SD (%s) has been shut down"),
        mut("sd -restart back to plain stop_sd()", "sd.c",
            "if (stop_sd_ex(TRUE) && start_sd(TRUE))", "if (stop_sd() && start_sd(TRUE))"),
    ]


def main():
    src = {}
    for f in FILES:
        p = os.path.join(SRC, f)
        if not os.path.isfile(p):
            print("test-semlock-units: CANNOT RUN - no %s" % p)
            return 2
        src[f] = open(p).read()
    if "--selftest" in sys.argv:
        base = checks(src)
        if not all(ok for _, ok, _ in base):
            print("selftest: CANNOT RUN - the unmutated source already fails:")
            for n, ok, d in base:
                if not ok:
                    print("  FAIL %s (%s)" % (n, d))
            return 2
        bad = 0
        ms = mutants(src)
        for name, msrc, applied in ms:
            if not applied:
                print("  [NOT APPLIED] %s" % name)
                bad += 1
                continue
            caught = [n for n, ok, _ in checks(msrc) if not ok]
            print("  [%s] %s%s" % ("caught" if caught else "MISSED", name,
                                   "  (%d check(s) failed)" % len(caught) if caught else ""))
            bad += 0 if caught else 1
        print("test-semlock-units --selftest: %d mutant(s), %d not caught" % (len(ms), bad))
        return 1 if bad else 0
    print("sources : %s (%s)" % (SRC, ", ".join(FILES)))
    res = checks(src)
    fails = 0
    for name, ok, detail in res:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, "" if ok or detail == "" else "  (" + str(detail) + ")"))
        fails += 0 if ok else 1
    if len(res) < 20:
        print("test-semlock-units: only %d checks ran - a function was not found" % len(res))
        return 2
    print("test-semlock-units: %d checks, %d failed" % (len(res), fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
