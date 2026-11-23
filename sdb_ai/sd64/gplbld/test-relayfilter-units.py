#!/usr/bin/env python3
# test-relayfilter-units.py - S.272 (19 Nov 2026): the TLS relay's seccomp filter, RUN, not read.
#
#   python3 /home/don/SDCoreProject/SDCore4Linux/sdb_ai/sd64/gplbld/test-relayfilter-units.py [--selftest]
#
# WHY.  On Ubuntu 24.04 (OpenSSL 3.0.13) every API connection was refused "TLS relay ended before the session started": the relay
# called setsockopt() in the TLS 1.3 handshake and the filter killed it (kernel audit type 1326, syscall 54, SIGSYS).  The fix answers
# setsockopt() and getsockopt() with EPERM; everything off the list still kills.  Nothing ran this filter before: a sandbox's relay never
# met that OpenSSL, and this machine's OpenSSL does not make the call.
#
# WHAT IT RUNS.  The code between "#if defined(__x86_64__)" (RELAY_AUDIT_ARCH) and the "#else" that follows confine() is CUT OUT of
# gplsrc/sd_tlssrv.c, compiled with a harness, and run in a child process:
#   R0  control: with no filter, setsockopt and open both work (the harness can tell a refusal from success)
#   R1  confine() succeeds
#   R2  setsockopt() on a socket the process holds returns -1 with EPERM, and the process LIVES
#   R3  getsockopt() the same
#   R4  read() and write() on the held socketpair still work (the relay's own work)
#   R5  open() - not on the list - KILLS the process with SIGSYS
# No sudo, no install, no sd.  x86-64 only (the filter is built for one architecture at a time); exit 2 elsewhere or without gcc.
# --selftest makes the filter's errno rule a kill again and the setsockopt name a wrong number, and requires each to fail a row.

import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), "gplsrc", "sd_tlssrv.c")

HARNESS = r'''
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <sys/prctl.h>
#include <sys/socket.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <syslog.h>
#include <time.h>
#include <unistd.h>
#include <linux/audit.h>
#include <linux/filter.h>
#include <linux/seccomp.h>
%(cut)s
int main(int argc, char** argv) {
  int sv[2]; char buf[8]; int one = 1; socklen_t ol = sizeof(one); char err[200] = "";
  if (socketpair(AF_UNIX, SOCK_STREAM, 0, sv) != 0) { printf("socketpair failed\n"); return 3; }
  if (argc > 1 && !strcmp(argv[1], "nofilter")) {
    printf("R0 setsockopt=%%d\n", setsockopt(sv[0], SOL_SOCKET, SO_KEEPALIVE, &one, sizeof(one)));
    int fd = open("/etc/hostname", O_RDONLY); printf("R0 open=%%s\n", fd >= 0 ? "ok" : "failed"); fflush(stdout); return 0;
  }
  printf("start\n"); fflush(stdout);   /* stdio's first use checks stdout (fstat), which the filter forbids: done before it, as the relay never prints */
  bool ok = confine(err, sizeof(err));
  printf("R1 confine=%%d %%s\n", (int)ok, err); fflush(stdout);
  errno = 0; int r = setsockopt(sv[0], SOL_SOCKET, SO_KEEPALIVE, &one, sizeof(one));
  printf("R2 setsockopt=%%d errno=%%s\n", r, errno == EPERM ? "EPERM" : strerror(errno)); fflush(stdout);
  errno = 0; r = getsockopt(sv[0], SOL_SOCKET, SO_KEEPALIVE, &one, &ol);
  printf("R3 getsockopt=%%d errno=%%s\n", r, errno == EPERM ? "EPERM" : strerror(errno)); fflush(stdout);
  r = (int)write(sv[0], "x", 1); int r2 = (int)read(sv[1], buf, 1);
  printf("R4 write=%%d read=%%d\n", r, r2); fflush(stdout);
  printf("R5 before open\n"); fflush(stdout);
  int fd = open("/etc/hostname", O_RDONLY);
  printf("R5 open returned %%d - NOT KILLED\n", fd); fflush(stdout);
  return 0;
}
'''


def cut(text):
    """The filter: from RELAY_AUDIT_ARCH's #if to the #else after confine()."""
    a = text.find("#if defined(__x86_64__)\n#define RELAY_AUDIT_ARCH")
    b = text.find("\n#else\nstatic bool confine(", a)
    if a < 0 or b < 0:
        return None
    return text[a:b] + "\n#endif\n"


def run_once(text):
    """Returns (rows, detail) - rows a dict name -> bool."""
    block = cut(text)
    if block is None:
        return None, "could not cut the filter out of sd_tlssrv.c"
    tmp = tempfile.mkdtemp(prefix="relayfilter-")
    try:
        c = os.path.join(tmp, "h.c")
        open(c, "w").write(HARNESS % {"cut": block})
        exe = os.path.join(tmp, "h")
        cc = subprocess.run(["gcc", "-std=gnu17", "-o", exe, c], capture_output=True, text=True)
        if cc.returncode != 0:
            return None, "the harness did not compile: " + cc.stderr[-600:]
        p0 = subprocess.run([exe, "nofilter"], capture_output=True, text=True, timeout=30)
        p = subprocess.run([exe], capture_output=True, text=True, timeout=30)
        out = p.stdout
        rows = {
            "R0 control: with no filter setsockopt returns 0 and open works": "R0 setsockopt=0" in p0.stdout and "R0 open=ok" in p0.stdout,
            "R1 confine() succeeds": "R1 confine=1" in out,
            "R2 setsockopt() is refused with EPERM and the process lives": "R2 setsockopt=-1 errno=EPERM" in out,
            "R3 getsockopt() is refused with EPERM": "R3 getsockopt=-1 errno=EPERM" in out,
            "R4 read() and write() on the held sockets still work": "R4 write=1 read=1" in out,
            "R5 open() kills the process with SIGSYS (and no line after it)": p.returncode == -31 and "R5 before open" in out and "NOT KILLED" not in out,
        }
        return rows, "control: %r | run: rc=%d %r" % (p0.stdout, p.returncode, out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    if platform.machine() != "x86_64" or not shutil.which("gcc"):
        print("test-relayfilter-units: CANNOT RUN - needs x86-64 and gcc (the filter is built for one architecture)")
        return 2
    text = open(SRC, encoding="utf-8", errors="replace").read()
    print("test-relayfilter-units: %s" % SRC)
    if "--selftest" in sys.argv:
        mutants = [
            ("the errno rule kills again", "SECCOMP_RET_ERRNO | (EPERM & SECCOMP_RET_DATA)", "SECCOMP_RET_KILL_PROCESS"),
            ("the refused list names the wrong call", "relay_refused[] = { SYS_setsockopt,", "relay_refused[] = { SYS_socket,"),
            ("open joins the allowed list", "SYS_read, SYS_write, SYS_close,", "SYS_read, SYS_write, SYS_close, SYS_open, SYS_openat,"),
        ]
        bad = 0
        for name, old, new in mutants:
            if text.count(old) != 1:
                print("  [MISSED] %s: the text is there %d times" % (name, text.count(old))); bad += 1; continue
            rows, detail = run_once(text.replace(old, new))
            if rows is None:   # a mutant that does not even build proves nothing about the rows
                print("  [MISSED] %s: could not run (%s)" % (name, detail[:160])); bad += 1; continue
            caught = not all(rows.values())
            print("  [%s] %s" % ("caught" if caught else "MISSED", name)); bad += (not caught)
        print("selftest: %d mutants, %d missed" % (len(mutants), bad))
        return 0 if bad == 0 else 1
    rows, detail = run_once(text)
    if rows is None:
        print("test-relayfilter-units: CANNOT RUN - " + detail); return 2
    for name, ok in rows.items():
        print("  [%s] %s" % ("PASS" if ok else "FAIL", name))
    failed = sum(1 for ok in rows.values() if not ok)
    if failed:
        print("  detail: " + detail[:800])
    print("test-relayfilter-units: %d passed, %d failed" % (len(rows) - failed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
