#!/usr/bin/env python3
#
# sandbox-auditjournal.py - W.11 F4, option B (24 Oct 2026, the owner: "b then c"): every audit record is also in the system journal, stamped by
#                           journald with the real uid and pid of the process that sent it.  A private SD, no install, no sudo.
#
#   SDBOX_KEYSET=<n> python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-auditjournal.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or absent).  Exit 0 every row passed, 1 a row failed,
# 2 it could not run - INCLUDING the null cases: no journalctl, a journal this user cannot read, the audited event that never reached the audit file.
#
# START-HISTORY:
# 24 Oct 26 dm  New.  k_error.c audit_message().  Plan: .claude/design-audit-trail-writer-24oct.md, option B.
# END-HISTORY
#
# WHAT IT DOES.  An internal probe program (gpl.bp/zzaud) calls kernel(K$AUDIT, ...) with a token, in a real `sd -internal` session of the sandbox; the line it adds to
# sys/audit is read from the disk, and the journal is asked (journalctl -o json -t sd_Log, this user's entries) for the copy.  Rows: the line is in the file (the event
# really happened); the journal has the SAME record behind the prefix "sd-audit "; its _UID is this user's and its _PID is the pid the file line names, from journald and not
# from the text; the identifier is sd_Log, the facility authpriv (10), the level notice (5); an event whose TEXT claims to be root pid 1 is still stamped with the real
# uid and pid; a token never sent finds nothing (the control that the search can fail); and every line this run added to the file has a journal copy.
# NOT HELD: a second user (a sandbox has one), journald's rate limit, whether the journal survives a reboot.

import getpass
import importlib.util
import json
import os
import re
import secrets
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
sys.path.insert(0, HERE)


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


g = _load("sandbox_gates_for_auditjournal", "sandbox-gates.py")
say, row, bail = g.say, g.row, g.bail
UID = os.getuid()
BOX = SYS = SD = None


def journal(token_filter=None):
    """this user's sd_Log entries of the last half hour, as a list of dicts; None when the journal cannot be read at all"""
    try:
        p = subprocess.run(["journalctl", "--no-pager", "-o", "json", "-t", "sd_Log", "--since", "-30min", "_UID=%d" % UID],
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if p.returncode != 0:
        return None
    out = []
    for ln in p.stdout.splitlines():
        try:
            d = json.loads(ln)
        except ValueError:
            continue
        m = d.get("MESSAGE")
        if isinstance(m, list):                       # journald gives bytes as a list of ints
            m = bytes(m).decode("utf-8", "replace")
        d["MESSAGE"] = m or ""
        out.append(d)
    return out


def find(token, tries=15):
    """the journal entries whose message holds the token, waiting for journald to have them"""
    for _ in range(tries):
        j = journal()
        if j is None:
            return None
        hit = [d for d in j if token in d["MESSAGE"] and d["MESSAGE"].startswith("sd-audit ")]
        if hit:
            return hit
        time.sleep(1)
    return []


def audit_lines(off):
    path = os.path.join(SYS, "audit")
    with open(path, "rb") as f:
        f.seek(off)
        return [x for x in f.read().decode("utf-8", "replace").split("\n") if x]


def main():
    global BOX, SYS, SD
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-auditjournal.py <dir> [--build]")
    BOX = os.path.abspath(args[0])
    SYS = os.path.join(BOX, "sys")
    SD = os.path.join(SYS, "bin", "sd")
    g.BOX, g.SYS, g.SD = BOX, SYS, SD
    say("sandbox-auditjournal: sandbox %s, user %s (uid %d)" % (BOX, getpass.getuser(), UID))
    if "--build" in sys.argv:
        if os.path.exists(BOX) and os.listdir(BOX):
            bail("%s is not empty" % BOX)
        r = subprocess.run([sys.executable, TOOL, BOX, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-auditjournal: built, bootstrap passed")
    elif not os.path.isfile(SD):
        bail("%s holds no built sandbox (use --build, or point it at one)" % BOX)
    subprocess.run([sys.executable, TOOL, BOX, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    if journal() is None:
        bail("journalctl is missing or this user cannot read the system journal (is the user in adm or systemd-journal?): nothing below could be measured")

    say("\n--- preparation: a probe that writes one audit record ---------------------------------------------------------")
    g.put(os.path.join(SYS, "gpl.bp", "zzaud"), "\n".join([
        "$internal", "program zzaud", "$catalog $zzaud", "$include keys.h", "$include int$keys.h",
        "   text = field(@sentence, ' ', 4, 99)", "   void kernel(K$AUDIT, 'zzjournal ':text)", "   crt 'ZZAUD sent'", "end", ""]))
    out = g.adm(["BASIC gpl.bp zzaud"], internal=True)
    if not g.has(out, r"^Compiled 1 program\(s\) with no errors"):
        bail("the probe did not compile:\n" + "\n".join(out[-8:]))
    path = os.path.join(SYS, "audit")
    if not os.path.exists(path):
        open(path, "ab").close()
    off = os.path.getsize(path)

    tok = "tok" + secrets.token_hex(6)
    tok2 = "tok" + secrets.token_hex(6)
    tok_never = "tok" + secrets.token_hex(6)
    out = g.adm(["RUN gpl.bp zzaud token=" + tok], internal=True)
    sent1 = g.has(out, r"^ZZAUD sent$")
    out = g.adm(["RUN gpl.bp zzaud token=%s user=root uid=0 pid=1" % tok2], internal=True)
    sent2 = g.has(out, r"^ZZAUD sent$")
    if not (sent1 and sent2):
        bail("the probe did not run both times")

    say("\n--- the audit file --------------------------------------------------------------------------------------------")
    lines = audit_lines(off)
    mine = [x for x in lines if ("zzjournal token=" + tok) in x]
    m = re.match(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) user=(\S+?)(?: sudo=\S+)? uid=(\S+) pid=(\d+) zzjournal token=" + tok + "$", mine[0]) if mine else None
    row("0: the event really reached the audit file (null case) - exactly one line, in the shape the readers expect", len(mine) == 1 and m is not None,
        "lines this run added: %d; matching: %r" % (len(lines), mine))
    if not m:
        bail("the audited event is not in the audit file: the journal rows would measure nothing")
    pid = int(m.group(4))
    say("    the file line: %s" % mine[0])

    say("\n--- the journal -----------------------------------------------------------------------------------------------")
    hit = find(tok)
    if hit is None:
        bail("the journal became unreadable")
    row("J1: the journal holds exactly one copy of the record, behind the prefix 'sd-audit '", len(hit) == 1, "%d entries for the token" % len(hit))
    d = hit[0] if hit else {}
    row("J1b: and it is the SAME record as the file's line (nothing added, nothing cut)", d.get("MESSAGE") == "sd-audit " + mine[0], "journal: %r" % d.get("MESSAGE"))
    row("J2: journald stamped the real uid of the sender (_UID is this user's)", d.get("_UID") == str(UID), "_UID %r, this user %d" % (d.get("_UID"), UID))
    row("J2b: and the real pid - the pid the file line names, which is the probe session's own", d.get("_PID") == str(pid), "_PID %r, the file line says %d" % (d.get("_PID"), pid))
    row("J3: identifier sd_Log, facility authpriv (10), level notice (5)",
        d.get("SYSLOG_IDENTIFIER") == "sd_Log" and d.get("SYSLOG_FACILITY") == "10" and d.get("PRIORITY") == "5",
        "identifier %r facility %r priority %r" % (d.get("SYSLOG_IDENTIFIER"), d.get("SYSLOG_FACILITY"), d.get("PRIORITY")))

    hit2 = find(tok2)
    d2 = hit2[0] if hit2 else {}
    row("J4: a record whose TEXT claims user=root uid=0 pid=1 is stamped with the real uid and a real pid, not the claim (the text is the sender's; _UID and _PID are not)",
        len(hit2 or []) == 1 and d2.get("_UID") == str(UID) and d2.get("_PID") not in (None, "1") and "user=root uid=0 pid=1" in d2.get("MESSAGE", ""),
        "_UID %r _PID %r message %r" % (d2.get("_UID"), d2.get("_PID"), d2.get("MESSAGE")))

    j = journal() or []
    row("J5: control - a token that was never sent finds nothing (the search can fail)", not [x for x in j if tok_never in x["MESSAGE"]], "")

    msgs = {x["MESSAGE"] for x in j}
    lines = audit_lines(off)
    missing = [x for x in lines if "sd-audit " + x not in msgs]
    row("J6: every line this run added to the audit file (%d) has a journal copy" % len(lines), len(lines) >= 2 and not missing, "without a copy: %r" % (missing[:3],))

    say("")
    say("sandbox-auditjournal: %d passed, %d failed" % (g.passed, g.failed))
    sys.exit(1 if g.failed else 0)


if __name__ == "__main__":
    main()
