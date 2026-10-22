#!/usr/bin/env python3
"""test-agentdoor-units.py - the pieces of the agent door that slice 1 of the AI integration puts in the installer, the uninstaller and the ssh block (21 Oct 2026).

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-agentdoor-units.py
  python3 .../test-agentdoor-units.py --selftest

No sudo, no install, no sd.  Exit 0 every check passed, 1 a check failed, 2 it could not run.

WHAT IT HOLDS (the owner's D5 and D6 of 21 Oct 2026): the group sdagent is made by the installer (empty, in the loop of route groups) and removed by the
uninstaller only when the accounts are deleted too; the OS user sdai is a SYSTEM user with its own group, no login shell, no home directory made, and in no
SD group; the uninstaller takes it away in the same branch as the groups; and the ssh block's agent arm is written and nothing in the generator READS the
client's own command (no dispatcher).  ***IT READS SCRIPTS AS TEXT AND RUNS NOTHING***: that sshd really picks the arm first, that useradd makes the user
that way, and that a member of sdagent reaches only the agent door are the VM witness's rows, not this file's.

--selftest runs every check on the real files and then on a copy with one deliberate fault at a time: each must make a check fail.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
FILES = {"install": os.path.join(ROOT, "installsdcore.sh"), "delete": os.path.join(ROOT, "deletesdcore.sh"), "ssh": os.path.join(HERE, "ssh-forcecommand.sh")}


def code_lines(text):
    return [ln for ln in text.split("\n") if not ln.lstrip().startswith("#")]


def checks(raw):
    inst = "\n".join(code_lines(raw["install"]))
    dele = "\n".join(code_lines(raw["delete"]))
    ssh = "\n".join(code_lines(raw["ssh"]))
    out = []

    def add(i, what, ok, detail=""):
        out.append((i, what, bool(ok), detail))

    loop = re.search(r"for sd_route_group in ([a-z ]+); do", inst)
    names = loop.group(1).split() if loop else []
    add("A0", "NULL CASE: the installer's route-group loop, the uninstaller's and the ssh block's lines were all found",
        bool(loop) and "for sd_route_group in" in dele and "block_lines()" in ssh, repr(names))
    add("A1", "the installer makes sdagent as a system group in a block of its own (it is not a route group of an SD account) and leaves the route-group loop as it was, the five names",
        "sudo groupadd --system sdagent" in inst and "if ! getent group sdagent" in inst and names == ["sdssh", "sdapi", "sdfiles", "sdfileswrite", "sdfilesadmin"]
        and "sudo groupadd --system \"$sd_route_group\"" in inst, repr(names))
    m = re.search(r"useradd ([^\n]*\bsdai\b)[^\n]*", inst)
    ua = m.group(0) if m else ""
    add("A2", "the installer makes sdai as a SYSTEM user with its own group, no login shell and no home directory made",
        "--system" in ua and "--user-group" in ua and "--shell /usr/sbin/nologin" in ua and "--no-create-home" in ua, ua)
    add("A3", "sdai is in no SD group: no -G, -g or --groups on its useradd, and no usermod puts it anywhere",
        bool(ua) and not re.search(r"\s(-G|-g|--groups|--gid)\b", ua) and not re.search(r"usermod[^\n]*\bsdai\b", inst + dele), ua)
    add("A4", "the installer leaves an existing sdai alone (it tests getent passwd first)", re.search(r"if ! getent passwd sdai[^\n]*\n[^\n]*\n[^\n]*useradd", inst) is not None, "")
    branch = dele.split("else", 1)[0] if "for sd_route_group in" in dele else ""
    seg = dele[dele.find("for sd_route_group in"):]
    deleted_part = seg.split("\nelse\n", 1)[0]
    add("A5", "the uninstaller removes sdagent in the branch where the accounts are deleted, and says it kept it in the kept-accounts branch",
        "groupdel sdagent" in deleted_part and "sdagent" in seg.split("\nelse\n", 1)[-1].split("\nfi", 1)[0], "")
    add("A6", "the uninstaller removes the user sdai and its group in that same branch, and not in the other one",
        "userdel sdai" in deleted_part and "groupdel sdai" in deleted_part and "userdel sdai" not in seg.split("\nelse\n", 1)[-1].split("\nfi", 1)[0], "")
    add("A7", "the ssh block writes an agent arm for the group sdagent with its own ForceCommand, first after sdsys's arm",
        ssh.find('"Match User sdsys"') < ssh.find('"Match Group sdagent,!sdsys"') < ssh.find('"Match Group sdusers,!sdsys,!sdssh"') < ssh.find('"Match Group sdusers,!sdsys"')
        and '"    ForceCommand $MCP_BIN"' in ssh, "")
    add("A8", "the generator READS nothing the client typed: SSH_ORIGINAL_COMMAND is not in its code (D5: no dispatcher)", "SSH_ORIGINAL_COMMAND" not in ssh, "")
    add("A9", "the install does not require the sd-mcp program to exist (it arrives in a later slice and the arm fails closed without it)",
        not re.search(r"-x\s+\"?\$MCP_BIN|-e\s+\"?\$MCP_BIN|-f\s+\"?\$MCP_BIN", ssh), "")
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
    ("install", "sdagent is not made", "  sudo groupadd --system sdagent\n", "  true\n"),
    ("install", "sdagent is slipped into the route-group loop", "for sd_route_group in sdssh sdapi sdfiles sdfileswrite sdfilesadmin; do", "for sd_route_group in sdssh sdapi sdfiles sdfileswrite sdfilesadmin sdagent; do"),
    ("install", "sdai is not a system user", "useradd --system --user-group", "useradd --user-group"),
    ("install", "sdai gets a login shell", "--shell /usr/sbin/nologin", "--shell /bin/bash"),
    ("install", "sdai gets a home directory made", "--no-create-home sdai", "--create-home sdai"),
    ("install", "sdai is put in sdusers", "--user-group --shell", "--user-group -G sdusers --shell"),
    ("delete", "sdagent stays after a full delete", "        sudo groupdel sdagent || true\n", "        true\n"),
    ("delete", "sdai is removed even when the accounts are kept", "    echo \"The group sdagent and the user sdai were kept with them.\"",
     "    sudo userdel sdai\n    echo \"The group sdagent and the user sdai were kept with them.\""),
    ("delete", "sdai is never removed", "        sudo userdel sdai || true\n", "        true\n"),
    ("ssh", "the agent arm is after the general arm", '    "Match Group sdagent,!sdsys" \\\n    "    ForceCommand $MCP_BIN" \\\n', ""),
    ("ssh", "a dispatcher reads the client's command", 'MCP_BIN=${SD_SSH_MCP_BIN:-/usr/local/sdsys/bin/sd-mcp}', 'MCP_BIN=${SD_SSH_MCP_BIN:-/usr/local/sdsys/bin/sd-mcp}\ncase $SSH_ORIGINAL_COMMAND in sd-mcp) exec $MCP_BIN;; esac'),
    ("ssh", "the install insists on sd-mcp existing", 'MCP_BIN=${SD_SSH_MCP_BIN:-/usr/local/sdsys/bin/sd-mcp}', 'MCP_BIN=${SD_SSH_MCP_BIN:-/usr/local/sdsys/bin/sd-mcp}\n[[ -x $MCP_BIN ]] || die "no sd-mcp"'),
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
    print("test-agentdoor-units: %d passed, %d failed" % (len(rows) - len(bad), len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
