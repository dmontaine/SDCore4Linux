#!/usr/bin/env python3
"""test-sdai-units.py - the OS user sdai, which the installer makes and the uninstaller removes (AI integration slice 1, 21 Oct 2026).

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-sdai-units.py
  python3 .../test-sdai-units.py --selftest

No sudo, no install, no sd.  Exit 0 every check passed, 1 a check failed, 2 it could not run.

WHAT IT HOLDS (the owner's D6 of 21 Oct 2026): the OS user sdai is a SYSTEM user with its own group, no login shell, no home directory made, and in no SD group;
an existing one is left alone; the uninstaller takes the user and its group away only in the branch where the accounts are deleted too, and says it kept them when the
accounts are kept.  It is for the in-SD model call that a later slice builds; nothing runs as it yet.

(This file began the same day as test-agentdoor-units.py and also held the group sdagent and the ssh arm for an MCP door.  The owner dropped the MCP door at the server
the same day, and those parts and their checks were taken out.)

***IT READS SCRIPTS AS TEXT AND RUNS NOTHING***: that useradd makes the user that way is a real-install row, not this file's.

--selftest runs every check on the real files and then on a copy with one deliberate fault at a time: each must make a check fail.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
FILES = {"install": os.path.join(ROOT, "installsdcore.sh"), "delete": os.path.join(ROOT, "deletesdcore.sh")}


def code_lines(text):
    return [ln for ln in text.split("\n") if not ln.lstrip().startswith("#")]


def checks(raw):
    inst = "\n".join(code_lines(raw["install"]))
    dele = "\n".join(code_lines(raw["delete"]))
    out = []

    def add(i, what, ok, detail=""):
        out.append((i, what, bool(ok), detail))

    m = re.search(r"useradd ([^\n]*\bsdai\b)[^\n]*", inst)
    ua = m.group(0) if m else ""
    seg = dele[dele.find("for sd_route_group in"):]
    deleted_part = seg.split("\nelse\n", 1)[0]
    kept_part = seg.split("\nelse\n", 1)[-1].split("\nfi", 1)[0]
    add("S0", "NULL CASE: the installer's useradd of sdai and the uninstaller's route-group branch were both found", bool(ua) and "for sd_route_group in" in dele, ua)
    add("S1", "the installer makes sdai as a SYSTEM user with its own group, no login shell and no home directory made",
        "--system" in ua and "--user-group" in ua and "--shell /usr/sbin/nologin" in ua and "--no-create-home" in ua, ua)
    add("S2", "sdai is in no SD group: no -G, -g or --groups on its useradd, and no usermod puts it anywhere",
        bool(ua) and not re.search(r"\s(-G|-g|--groups|--gid)\b", ua) and not re.search(r"usermod[^\n]*\bsdai\b", inst + dele), ua)
    add("S3", "the installer leaves an existing sdai alone (it tests getent passwd first)", re.search(r"if ! getent passwd sdai[^\n]*\n[^\n]*\n[^\n]*useradd", inst) is not None, "")
    add("S4", "the uninstaller removes the user sdai and its group in the branch where the accounts are deleted, and not in the other one",
        "userdel sdai" in deleted_part and "groupdel sdai" in deleted_part and "userdel sdai" not in kept_part and "sdai" in kept_part, "")
    return out


def load():
    raw = {}
    for k, p in FILES.items():
        with open(p, encoding="utf-8", errors="replace") as f:
            raw[k] = f.read()
    return raw


def run(raw, quiet=False):
    rows = checks(raw)
    bad = [r for r in rows if not r[2]]
    if not quiet:
        for i, what, ok, detail in rows:
            print("  [%s] %s %s%s" % ("PASS" if ok else "FAIL", i, what, ("   <- " + detail) if (detail and not ok) else ""))
    return rows, bad


MUT = [
    ("install", "sdai is not a system user", "useradd --system --user-group", "useradd --user-group"),
    ("install", "sdai gets a login shell", "--shell /usr/sbin/nologin", "--shell /bin/bash"),
    ("install", "sdai gets a home directory made", "--no-create-home sdai", "--create-home sdai"),
    ("install", "sdai is put in sdusers", "--user-group --shell", "--user-group -G sdusers --shell"),
    ("install", "an existing sdai is made again", "if ! getent passwd sdai &>/dev/null; then", "if true; then"),
    ("delete", "sdai is removed even when the accounts are kept", "    echo \"The user sdai was kept with them.\"", "    sudo userdel sdai\n    echo \"The user sdai was kept with them.\""),
    ("delete", "sdai is never removed", "        sudo userdel sdai || true\n", "        true\n"),
    ("delete", "the group sdai is left behind", "        sudo groupdel sdai || true\n", "        true\n"),
]


def selftest():
    raw = load()
    rows, bad = run(raw)
    if bad:
        print("selftest: the real files already fail %d check(s)" % len(bad))
        return 1
    killed, missed = 0, []
    for fname, what, old, new in MUT:
        if raw[fname].count(old) != 1:
            print("  [CANNOT] %s: the text to change is found %d times in %s, not once" % (what, raw[fname].count(old), fname))
            return 2
        m = dict(raw)
        m[fname] = raw[fname].replace(old, new)
        rows_m, bad_m = run(m, quiet=True)
        if bad_m:
            killed += 1
            print("  [killed] %s  <- %s" % (what, ", ".join(r[0] for r in bad_m)))
        else:
            missed.append(what)
            print("  [MISSED] %s" % what)
    print("selftest: %d mutants, %d killed, %d missed" % (len(MUT), killed, len(missed)))
    return 0 if not missed else 1


def main():
    for p in FILES.values():
        if not os.path.isfile(p):
            print("CANNOT RUN: %s is not there" % p)
            return 2
    if "--selftest" in sys.argv:
        return selftest()
    rows, bad = run(load())
    print("test-sdai-units: %d passed, %d failed" % (len(rows) - len(bad), len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
