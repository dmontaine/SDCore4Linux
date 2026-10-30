#!/usr/bin/env python3
# test-clientunit-units.py - the per-connection server's unit, usr/lib/systemd/system/sdclient@.service, holds the SAFE hardening set and nothing that would stop a session working
# (W.11 F5, Opus's decision 1b, 30 Oct 2026), read off the file as text.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-clientunit-units.py
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-clientunit-units.py --selftest
#
# FREE CHECK: no install, no sudo, no systemd.  WHY IT EXISTS.  The server runs as root until a session has logged in and dropped to its user, and a session may run `sudo sd-elevate`, write the
# system directory under /usr/local and an account under /home/sd.  So the unit may narrow what the pre-login reader can reach (kernel tunables, modules and log, the control groups, the clock, the
# host name, real-time scheduling, new namespaces, the execution domain, other architectures' system calls) and may NOT set NoNewPrivileges, a capability bound, ProtectSystem, ProtectHome, PrivateTmp,
# PrivateDevices or any path list: those stop the sudo, the writes or the terminal and break the product in ways only a real install shows.  This check holds both halves; whether the directives take
# effect is the VM's (`systemctl show sdclient@x.service -p ...`) and the release witness's API rows are the proof the product still works.
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
UNIT = os.environ.get("CLIENT_UNIT", os.path.normpath(os.path.join(HERE, "..", "usr", "lib", "systemd", "system", "sdclient@.service")))
WANT = [("ProtectKernelTunables", "yes"), ("ProtectKernelModules", "yes"), ("ProtectKernelLogs", "yes"), ("ProtectControlGroups", "yes"), ("ProtectClock", "yes"),
        ("ProtectHostname", "yes"), ("RestrictRealtime", "yes"), ("RestrictNamespaces", "yes"), ("LockPersonality", "yes"), ("SystemCallArchitectures", "native")]
FORBIDDEN = ["NoNewPrivileges", "CapabilityBoundingSet", "AmbientCapabilities", "ProtectSystem", "ProtectHome", "PrivateTmp", "PrivateDevices", "PrivateNetwork", "PrivateUsers", "ReadOnlyPaths",
             "ReadWritePaths", "InaccessiblePaths", "TemporaryFileSystem", "User", "Group", "DynamicUser", "MemoryDenyWriteExecute", "RestrictAddressFamilies", "RestrictSUIDSGID", "SystemCallFilter",
             "ProtectProc", "ProcSubset", "UMask", "RootDirectory", "RootImage"]


def settings(text):
    """{section: [(key, value)]} with comment lines and blank lines dropped."""
    out, sec = {}, None
    for l in text.split("\n"):
        s = l.strip()
        if not s or s.startswith("#") or s.startswith(";"):
            continue
        m = re.match(r"^\[(\w+)\]$", s)
        if m:
            sec = m.group(1)
            out.setdefault(sec, [])
            continue
        if sec and "=" in s:
            k, v = s.split("=", 1)
            out[sec].append((k.strip(), v.strip()))
    return out


def checks(text):
    rows = []

    def row(name, ok, detail=""):
        rows.append((name, bool(ok), detail))

    st = settings(text)
    svc = st.get("Service", [])
    keys = [k for k, v in svc]
    row("U1 the unit has a [Unit] and a [Service] section and the server is still `sd -n -q` on the socket (ExecStart and StandardInput as they were)",
        "Unit" in st and "Service" in st and ("ExecStart", "/usr/local/sdsys/bin/sd -n -q") in svc and ("StandardInput", "socket") in svc, repr(svc[:3]))
    for k, v in WANT:
        row("U2 %s=%s, once" % (k, v), svc.count((k, v)) == 1 and keys.count(k) == 1, repr([x for x in svc if x[0] == k]))
    bad = sorted(set(k for k in keys if k in FORBIDDEN))
    row("U3 none of the settings that would stop a session working is set (%s ...)" % ", ".join(FORBIDDEN[:6]), not bad, repr(bad))
    row("U4 the server is still started as root: no User= (the pre-login stage is root's by design, the session drops its own privileges)", "User" not in keys and "DynamicUser" not in keys, repr(keys))
    row("U5 the Service section holds only the two lines it had and the ten of the set: nothing else crept in", sorted(keys) == sorted(["ExecStart", "StandardInput"] + [k for k, v in WANT]), repr(sorted(set(keys) - {"ExecStart", "StandardInput"} - {k for k, v in WANT})))
    row("U6 the file is plain text: no CR, no BOM, ends with a line feed", "\r" not in text and not text.startswith("﻿") and text.endswith("\n"), "")
    return rows


def read():
    with open(UNIT, encoding="utf-8") as f:
        return f.read()


def run():
    rows = checks(read())
    bad = 0
    for name, ok, detail in rows:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, "" if ok else "   <- " + detail))
        bad += 0 if ok else 1
    print("test-clientunit-units: %d passed, %d failed" % (len(rows) - bad, bad))
    return 1 if bad or not rows else 0


def selftest():
    text = read()
    if not all(ok for _, ok, _ in checks(text)):
        print("  [FAIL] the real unit does not pass")
        return 1
    print("  [ok] the real unit passes")
    caught = missed = 0

    def mutant(name, old, new, prefix):
        nonlocal caught, missed
        if old not in text:
            print("  [MISSED] %s: the text to change is not there" % name)
            missed += 1
            return
        failing = [n for n, ok, _ in checks(text.replace(old, new, 1)) if not ok]
        if failing and all(n.startswith(tuple(prefix.split("|"))) for n in failing):      # "U2|U5": the rows a mutant may fail (an added or removed line trips the count row too)
            print("  [caught] %s (%s)" % (name, ", ".join(n.split()[0] for n in failing)))
            caught += 1
        else:
            print("  [MISSED] %s: failing rows %s" % (name, failing))
            missed += 1

    mutant("a directive of the set is missing", "ProtectClock=yes\n", "", "U2|U5")
    mutant("a directive is switched off", "LockPersonality=yes", "LockPersonality=no", "U2")
    mutant("a directive is given twice", "ProtectClock=yes\n", "ProtectClock=yes\nProtectClock=yes\n", "U2|U5")
    mutant("NoNewPrivileges would stop sudo", "LockPersonality=yes\n", "LockPersonality=yes\nNoNewPrivileges=yes\n", "U3|U5")
    mutant("ProtectSystem would stop the writes under /usr/local", "LockPersonality=yes\n", "LockPersonality=yes\nProtectSystem=strict\n", "U3|U5")
    mutant("a capability bound would stop sudo", "LockPersonality=yes\n", "LockPersonality=yes\nCapabilityBoundingSet=CAP_NET_BIND_SERVICE\n", "U3|U5")
    mutant("the server would not be root", "StandardInput=socket\n", "StandardInput=socket\nUser=sdsys\n", "U")
    mutant("the server is another program", "ExecStart=/usr/local/sdsys/bin/sd -n -q", "ExecStart=/usr/local/sdsys/bin/sd -n", "U1")
    mutant("the socket is not the input", "StandardInput=socket\n", "", "U1|U5")
    mutant("an unknown extra line", "LockPersonality=yes\n", "LockPersonality=yes\nTimeoutStopSec=5\n", "U5")
    mutant("a CR byte", "ProtectClock=yes\n", "ProtectClock=yes\r\n", "U6")
    print("selftest: %d of %d mutants caught, %d missed" % (caught, caught + missed, missed))
    return 0 if missed == 0 else 1


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else run())
