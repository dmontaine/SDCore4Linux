#!/usr/bin/env python3
"""test-relayfinish-units.py - sd waits for its TLS relay before it exits (26 Oct 26).

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-relayfinish-units.py
  python3 .../test-relayfinish-units.py --selftest

No sudo, no install, no sd.  Exit 0 all checks passed, 1 a check failed, 2 it could not run.

THE DEFECT (found 26 Oct 2026 by witness-release-run.sh rows S4, S6, T9, T11, T12, T13, a different two to four of them red on each run): a
refused SCRAM login printed "TLS read failed (SSL_get_error 1)" in the probe instead of the server's refusal text.  sdclient@.service has the
default KillMode (control-group).  sd -n -q forks the TLS relay (sd_tlssrv.c) and writes its reply into the socketpair; the refusal ends the
session, sd exits at once, systemd sends SIGTERM to the relay still in the cgroup, and when the relay had not yet read that reply the client saw
the connection close with no close_notify and no reply (OpenSSL 3 reports that as SSL_ERROR_SSL).  Measured on the Debian 13 VM with
gplbld/scram-probe.py --final-only, 60 refusals four at a time: 9 lost their reply under the shipped unit, 0 under a drop-in KillMode=process.
The fix is in the code, not the unit: clean_stop() ends with sd_tls_relay_finish(), which shuts the socketpair for writing, waits a bounded
time for the relay to forward what is queued and say close_notify, and reaps it.

***WHAT THIS IS AND IS NOT.***  It reads gplsrc/sd_tlssrv.c, sd_tls.h and sd.c as text.  It cannot say a refusal arrives; that is the
witness (scram-flake-ab.py style loop, and witness-release-run.sh S4 / S6 / T9 / T11 / T12 / T13 on a real install) because the kill belongs to
systemd.  It says the form is still written.  --selftest mutates the source and requires each mutant to be caught.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GPLSRC = os.path.abspath(os.path.join(HERE, os.pardir, "gplsrc"))
PATHS = {"srv": "sd_tlssrv.c", "hdr": "sd_tls.h", "sd": "sd.c"}


def strip_comments(text):
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


def body_of(src, head):
    m = re.search(r"^" + head + r" \{\n(.*?)^\}\n", src, re.S | re.M)
    return m.group(1) if m else None


def checks(f):
    srv, hdr, sd = f["srv"], f["hdr"], f["sd"]
    out = []

    def ck(name, ok, detail=""):
        out.append((name, bool(ok), detail))

    # --- sd_tlssrv.c: the pid is kept ---------------------------------------
    code_srv = strip_comments(srv)
    ck("relay_pid is a static pid_t, 0 until a relay is forked",
       re.search(r"^static pid_t relay_pid = 0;", code_srv, re.M) is not None)
    assigns = re.findall(r"relay_pid\s*=\s*([^;]+);", code_srv)
    ck("relay_pid is initialised to 0, given the forked pid once and cleared once, nowhere else",
       sorted(a.strip() for a in assigns) == ["0", "0", "pid"], "%r" % assigns)
    start = body_of(code_srv, r"int sd_tls_relay_start\(const char\* identity_dir, int timeout_ms,\s*char\* errmsg, size_t errlen\)")
    ck("sd_tls_relay_start() is there", start is not None)
    if start is not None:
        i_fork = start.find("fork()")
        i_child = start.find("relay_process(identity_dir")
        i_set = start.find("relay_pid = pid;")
        i_read = start.find("while (got < SD_TLS_BINDING_BYTES)")
        ck("the pid is kept in the parent: after the child's branch, before sd waits for the binding",
           -1 < i_fork < i_child < i_set < i_read, "fork %d child %d set %d read %d" % (i_fork, i_child, i_set, i_read))

    # --- sd_tlssrv.c: the wait ----------------------------------------------
    m = re.search(r"^#define RELAY_DRAIN_MS (\d+)", srv, re.M)
    ck("the drain bound is a number of milliseconds between 500 and 10000", m is not None and 500 <= int(m.group(1)) <= 10000,
       m.group(1) if m else "no #define")
    fin = body_of(code_srv, r"void sd_tls_relay_finish\(void\)")
    ck("sd_tls_relay_finish() is there", fin is not None)
    if fin is not None:
        i_take = fin.find("pid_t pid = relay_pid;")
        i_none = re.search(r"if \(pid <= 0\)\s*return;", fin)
        i_clear = fin.find("relay_pid = 0;")
        i_shut = fin.find("shutdown(0, SHUT_WR)")
        i_wait = fin.find("waitpid(pid, &status, WNOHANG)")
        ck("it takes the pid, returns when there is none, then clears it (a second call does nothing)",
           -1 < i_take and i_none is not None and i_take < i_none.start() < i_clear, "take %d none %s clear %d" % (i_take, bool(i_none), i_clear))
        ck("it shuts the socketpair for writing BEFORE it waits (the relay sees the end even if a child of sd holds a copy of descriptor 0)",
           -1 < i_shut < i_wait, "shutdown %d wait %d" % (i_shut, i_wait))
        ck("it does not close descriptors 0 or 1", re.search(r"\bclose\(\s*[01]\s*\)", fin) is None)
        ck("the wait polls with WNOHANG inside a loop, so it can be bounded", re.search(r"for \(;;\) \{.*waitpid\(pid, &status, WNOHANG\)", fin, re.S) is not None)
        ck("the wait is bounded by RELAY_DRAIN_MS and leaves the loop at the bound",
           re.search(r"if \(waited_ms >= RELAY_DRAIN_MS\)\s*break;", fin) is not None)
        ck("the wait counts its sleeps", re.search(r"waited_ms \+= RELAY_POLL_MS;", fin) is not None)
        ck("the relay being gone (reaped here, or by the kernel's SIGCHLD handler: ECHILD) ends the wait",
           re.search(r"if \(r == pid \|\| \(r < 0 && errno != EINTR\)\)\s*return;", fin) is not None)
        ck("after the bound the relay is killed and reaped", re.search(r"\(void\)kill\(pid, SIGKILL\);\s*\(void\)waitpid\(pid, &status, 0\);", fin) is not None)

    # --- the header and the call --------------------------------------------
    ck("sd_tls.h declares void sd_tls_relay_finish(void);", re.search(r"^void sd_tls_relay_finish\(void\);", strip_comments(hdr), re.M) is not None)
    code_sd = strip_comments(sd)
    ck('sd.c includes "sd_tls.h"', re.search(r'^#include "sd_tls\.h"', code_sd, re.M) is not None)
    stop = body_of(code_sd, r"void clean_stop\(void\)")
    ck("clean_stop() is there", stop is not None)
    if stop is not None:
        calls = [m.start() for m in re.finditer(r"sd_tls_relay_finish\(\);", stop)]
        ck("clean_stop() calls sd_tls_relay_finish() once", len(calls) == 1, "%d" % len(calls))
        i_dh, i_un, i_sc = stop.find("dh_shutdown();"), stop.find("unbind_sysseg();"), stop.find("shut_console();")
        ck("the call is the LAST step of clean_stop(): after dh_shutdown, unbind_sysseg and shut_console, with nothing after it",
           len(calls) == 1 and -1 < i_dh < i_un < i_sc < calls[0] and stop[calls[0]:].strip() == "sd_tls_relay_finish();",
           "%r" % stop[calls[0]:] if calls else "")
    ck("nothing else in sd.c calls it (every exit path goes through clean_stop)", len(re.findall(r"sd_tls_relay_finish\(", code_sd)) == 1)
    return out


def mutants(f):
    res = []

    def mut(name, key, old, new, count=1):
        g = dict(f)
        g[key] = f[key].replace(old, new, count)
        res.append((name, g, g[key] != f[key]))

    mut("sd.c no longer calls it", "sd", "  sd_tls_relay_finish();", "")
    mut("the call comes before the rest of clean_stop", "sd",
        "  dh_shutdown();\n  unbind_sysseg();\n  shut_console();\n  sd_tls_relay_finish();",
        "  sd_tls_relay_finish();\n  dh_shutdown();\n  unbind_sysseg();\n  shut_console();")
    mut("the header loses the declaration", "hdr", "void sd_tls_relay_finish(void);", "")
    mut("sd.c does not include the header", "sd", '#include "sd_tls.h"\n', "")
    mut("the pid is never kept", "srv", "  relay_pid = pid;\n", "")
    g = dict(f)       # kept only after sd has read the binding: a session refused before that has no pid to wait for
    g["srv"] = f["srv"].replace("  relay_pid = pid;\n", "", 1).replace("  have_binding = true;", "  relay_pid = pid;\n  have_binding = true;", 1)
    res.append(("the pid is kept only after the binding is read", g, g["srv"] != f["srv"]))
    mut("the socketpair is not shut for writing", "srv", "  (void)shutdown(0, SHUT_WR);        /* descriptors 0 and 1 are the one socket */\n", "")
    mut("descriptor 0 is closed instead of shut", "srv", "(void)shutdown(0, SHUT_WR);", "(void)close(0);")
    mut("the wait is not bounded", "srv", "    if (waited_ms >= RELAY_DRAIN_MS)\n      break;\n", "")
    mut("the wait is a blocking waitpid", "srv", "waitpid(pid, &status, WNOHANG)", "waitpid(pid, &status, 0)")
    mut("the relay is never killed after the bound", "srv", "  (void)kill(pid, SIGKILL);\n", "")
    mut("a relay already reaped is not recognised", "srv", " || (r < 0 && errno != EINTR)", "")
    mut("the pid is not cleared, so a second call waits again", "srv", "  relay_pid = 0;\n  (void)shutdown", "  (void)shutdown")
    mut("the bound is ten minutes", "srv", "#define RELAY_DRAIN_MS 2000", "#define RELAY_DRAIN_MS 600000")
    return res


def load():
    f = {}
    for key, name in PATHS.items():
        p = os.path.join(GPLSRC, name)
        if not os.path.isfile(p):
            print("test-relayfinish-units: CANNOT RUN - no %s" % p)
            return None
        f[key] = open(p).read()
    return f


def main():
    f = load()
    if f is None:
        return 2
    if "--selftest" in sys.argv:
        base = checks(f)
        if not all(ok for _, ok, _ in base):
            print("selftest: CANNOT RUN - the unmutated source already fails:")
            for n, ok, d in base:
                if not ok:
                    print("  FAIL %s (%s)" % (n, d))
            return 2
        bad = 0
        ms = mutants(f)
        for name, g, applied in ms:
            if not applied:
                print("  [NOT APPLIED] %s" % name)
                bad += 1
                continue
            caught = [n for n, ok, _ in checks(g) if not ok]
            if caught:
                print("  [caught] %s  (%d check(s) failed)" % (name, len(caught)))
            else:
                print("  [MISSED] %s" % name)
                bad += 1
        print("test-relayfinish-units --selftest: %d mutant(s), %d not caught" % (len(ms), bad))
        return 1 if bad else 0
    for key, name in PATHS.items():
        print("%-8s: %s" % (key, os.path.join(GPLSRC, name)))
    res = checks(f)
    fails = 0
    for name, ok, detail in res:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, "" if ok or not detail else "  (" + str(detail) + ")"))
        fails += 0 if ok else 1
    print("test-relayfinish-units: %d checks, %d failed" % (len(res), fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
