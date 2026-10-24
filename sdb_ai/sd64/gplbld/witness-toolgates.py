#!/usr/bin/env python3
#
# witness-toolgates.py - TOOL.GATES on a REAL install: the page driven on a pseudo-terminal as SDSYS, changing the installing user's own account through the real
# modify.account, the real sudo sd-elevate and the real /etc/group.  The half of S.75 A2 that sandbox-tool-gates.py cannot show: there the helper is a script of the
# suite and the group file is a scratch file.
#
#   python3 witness-toolgates.py            (on the VM, as the installing user, with ptydrive.py and termscreen.py beside this file; sudo needs no password there)
#
# SDSYS is entered the way sdnet-wlib.sh's sd_as does it: the audit loginuid is set to sdsys's uid, then `sudo -u sdsys sd` (a plain sudo / su to sdsys is refused, 10181).
# The terminal is 140 by 43, TERM xterm, with no SSH_* variables.  Every outcome is read from the system, not from the page: `getent group`, the register record
# (/usr/local/sdsys/accounts/<user>) and the audit trail.  It restores the account at the end (and says so), whatever happened.
# Prints PASS / FAIL lines and a verdict; exit 0 only when every row passed.
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ptydrive import PtySession  # noqa: E402

SDSYS_DIR = "/usr/local/sdsys"
SD = SDSYS_DIR + "/bin/sd"
ME = subprocess.run(["id", "-un"], capture_output=True, text=True).stdout.strip()
IDS = ["ssh", "api", "sh", "os", "sd", "voc", "bp", "dict", "net", "shared-read", "shared-write", "files", "files-write", "files-admin", "ai", "sockets"]
GROUPS = {"ssh": "sdssh", "api": "sdapi", "files": "sdfiles", "files-write": "sdfileswrite", "files-admin": "sdfilesadmin", "ai": "sdaiusers"}
passed = failed = 0


def row(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print("PASS  " + name, flush=True)
    else:
        failed += 1
        print("FAIL  " + name + ("   <- " + str(detail)[:400] if detail else ""), flush=True)


def sh(cmd):
    r = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)
    return r.stdout


def members(group):
    out = sh("getent group %s" % group).strip()
    if not out:
        return None
    return [m for m in out.split(":")[-1].split(",") if m]


def reg_fields():
    txt = sh("sudo cat %s/accounts/%s" % (SDSYS_DIR, ME))
    return txt.split("\n")


def audit_tail(n=40):
    return sh("sudo tail -n %d %s/audit" % (n, SDSYS_DIR))


def sdsys_cmds(body):
    """TCL lines run as SDSYS on a pipe (sdnet-wlib.sh's sd_as); returns the output.  For the steps that need no screen."""
    inner = 'printf "%s\\n" "$(id -u sdsys)" > /proc/self/loginuid 2>/dev/null; exec sudo -u sdsys "$1"'
    r = subprocess.run(["sudo", "sh", "-c", inner, "sd-run", SD], input=("\nTERM 200,9999\n%s\nOFF\n" % body).encode(), cwd=SDSYS_DIR, capture_output=True, timeout=180)
    return re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", r.stdout.decode("latin1")).replace("\r", "")


env = dict(os.environ, TERM="xterm", LC_ALL="C", LANG="C")
for k in ("SSH_CONNECTION", "SSH_TTY", "SSH_CLIENT"):
    env.pop(k, None)
ARGV = ["/usr/bin/sudo", "/bin/sh", "-c", 'printf "%s\\n" "$(id -u sdsys)" > /proc/self/loginuid 2>/dev/null; exec sudo -u sdsys "$1"', "sd-run", SD]
S = {"s": None, "r": 0, "c": 0}


def start():
    s = PtySession(ARGV, SDSYS_DIR, env, 140, 43)
    s.settle(3.0)
    S["s"] = s
    return s


def lines():
    return S["s"].screen.lines()


def line(n):
    L = lines()
    return L[n].rstrip() if n < len(L) else ""


def text():
    return "\n".join(l.rstrip() for l in lines())


def norm():
    return re.sub(r"[|\s]+", " ", text())


def typed(x, idle=0.9):
    S["s"].type(x, idle=idle)


UP, DOWN, RIGHT, LEFT = "\x1b[A", "\x1b[B", "\x1b[C", "\x1b[D"


def rows_on_screen():
    out = {}
    for n in range(3, 17):
        l = line(n)
        nm = l[3:23].strip()
        if nm:
            out[nm] = (n, l[23:29].strip(), [l[29 + 6 * i:35 + 6 * i].strip() for i in range(16)])
    return out


def goto(account, gate):
    """Move the cursor to (account, gate) using the order of the rows on the screen."""
    names = sorted(rows_on_screen())
    want_r, want_c = names.index(account), IDS.index(gate)
    while S["r"] < want_r:
        typed(DOWN, 0.4)
        S["r"] += 1
    while S["r"] > want_r:
        typed(UP, 0.4)
        S["r"] -= 1
    while S["c"] < want_c:
        typed(RIGHT, 0.4)
        S["c"] += 1
    while S["c"] > want_c:
        typed(LEFT, 0.4)
        S["c"] -= 1


def cell(account, gate):
    return rows_on_screen().get(account, (0, "", [""] * 16))[2][IDS.index(gate)]


def run_queue(expect_words, name_typed, label):
    """R opens the box, r runs it (and the name is typed when asked for).  Returns the box text."""
    typed("r", 1.6)
    box = norm()
    ok = ("modify.account %s %s" % (ME, expect_words)) in box
    row("%s: the box shows 'modify.account %s %s'" % (label, ME, expect_words), ok, box[-500:])
    typed("r", 1.4)
    if name_typed:
        row("%s: the box asks for the name before it runs" % label, "type" in norm().lower() or ME in norm(), norm()[-300:])
        typed(ME + "\r", 4.0)
    else:
        time.sleep(3.0)
        S["s"].settle(1.0)
    return box


def main():
    print("witness-toolgates: user %s, SD %s, %s" % (ME, SD, time.strftime("%F %T")))
    if not os.path.exists(SD):
        print("witness-toolgates: CANNOT RUN - no SD at " + SD)
        return 2
    pre = {g: members(g) for g in GROUPS.values()}
    print("witness-toolgates: groups before:", {g: (None if m is None else sorted(m)) for g, m in pre.items()}, flush=True)
    row("the six route groups exist on this install", all(m is not None for m in pre.values()), repr(pre))
    row("the installing user is in none of them to begin with (the delivered state)", all(m is not None and ME not in m for m in pre.values()), repr(pre))
    reg0 = reg_fields()
    row("the user's register record has sh, os, sd, voc, bp, dict, net all not yes (the delivered state)", all(reg0[i - 1].strip().lower() != "yes" for i in (7, 8, 9, 10, 11, 12, 15)), repr(reg0[:16]))

    # ---- an ordinary session has no tool.gates
    out = sh("printf '\\nTERM 200,60\\ntool.gates\\nOFF\\n' | timeout 60 %s 2>&1 | sed -e 's/\\x1b\\[[0-9;?]*[A-Za-z]//g'" % SD)      # 60 rows, not 9999: the page draws the whole window
    row("an ordinary session (this user, not an administrator) does not get the matrix: its verb is the holder's page (or, on an install older than 24 Oct, absent)", "Gates by account" not in out, out[-300:])

    # ---- the page as SDSYS
    # SDSYS's session starts at the home screen on a real install; the page is reached from the prompt, so the start default is set to terminal for this run and put back
    S["old_default"] = sh("sudo cat %s/start.default 2>/dev/null" % SDSYS_DIR).strip()
    sdsys_cmds("set.start.default terminal")
    row("set.start.default terminal was accepted (the file says terminal)", sh("sudo cat %s/start.default" % SDSYS_DIR).strip() == "terminal", sh("sudo cat %s/start.default" % SDSYS_DIR))
    s = start()
    typed("tool.gates\r", 3.5)
    T = text()
    if "Gates by account" not in T:
        print(T)
        row("tool.gates draws its page for SDSYS on a real terminal", False, T[-600:])
        return finish(1)
    row("tool.gates draws its page for SDSYS on a real terminal (administrator, 140 by 43)", True)
    rows = rows_on_screen()
    row("the installing user's account is a row, as a person's account, with the delivered cells", ME in rows and rows[ME][1] == "user" and rows[ME][2][IDS.index("shared-read")] == "ON"
        and all(rows[ME][2][IDS.index(k)] == "off" for k in ("ssh", "api", "sh", "os", "files", "files-write", "files-admin", "ai")), repr(rows.get(ME)))
    row("SDSYS is not a row", "sdsys" not in rows, repr(sorted(rows)))
    audit_new = sh("sudo grep -c 'tool start app=tool.gates' %s/audit" % SDSYS_DIR).strip()
    row("the page wrote its audit line", audit_new not in ("", "0"), audit_new)

    # ---- ssh ON (a group change through the real sd-elevate)
    goto(ME, "ssh")
    typed("\r", 0.8)
    row("Enter queues ssh: the cell says ON*", cell(ME, "ssh") == "ON*", cell(ME, "ssh"))
    run_queue("ssh", True, "ssh ON")
    m = members("sdssh") or []
    row("the REAL /etc/group has the user in sdssh, and not in sdapi", ME in m and ME not in (members("sdapi") or []), repr((members("sdssh"), members("sdapi"))))
    row("the page shows ssh ON after reading the system again", cell(ME, "ssh") == "ON", repr(rows_on_screen().get(ME)))

    # ---- ssh OFF and api ON in one queue: one word, api
    goto(ME, "ssh")
    typed("\r", 0.6)
    goto(ME, "api")
    typed("\r", 0.8)
    run_queue("api", True, "ssh OFF + api ON")
    row("the user is out of sdssh and in sdapi", ME not in (members("sdssh") or []) and ME in (members("sdapi") or []), repr((members("sdssh"), members("sdapi"))))

    # ---- api OFF: the word is none, no name
    goto(ME, "api")
    typed("\r", 0.8)
    run_queue("none", False, "api OFF")
    row("neither route group holds the user", ME not in (members("sdssh") or []) and ME not in (members("sdapi") or []), repr((members("sdssh"), members("sdapi"))))

    # ---- files, files-write, files-admin and ai together
    for gate in ("files", "files-write", "files-admin", "ai"):
        goto(ME, gate)
        typed("\r", 0.6)
    run_queue("files-on files-write-on files-admin-on ai-on", True, "files + write + admin + ai")
    mm = {g: members(g) or [] for g in ("sdfiles", "sdfileswrite", "sdfilesadmin", "sdaiusers")}
    row("the REAL groups sdfiles, sdfileswrite, sdfilesadmin and sdaiusers hold the user", all(ME in v for v in mm.values()), repr(mm))

    # ---- register gates with the real register: sh, os, voc
    for gate in ("sh", "os", "voc"):
        goto(ME, gate)
        typed("\r", 0.6)
    run_queue("sh-on os-on voc-on", True, "sh + os + voc")
    reg1 = reg_fields()
    row("the register record has yes in fields 7, 8 and 10 (read with sudo from the system directory)", [reg1[i - 1].strip().lower() for i in (7, 8, 10)] == ["yes", "yes", "yes"], repr(reg1[:12]))

    # ---- T: tighten, R: run -> everything back
    typed("t", 1.2)
    tc = rows_on_screen()[ME][2]
    stars = sorted(IDS[i] for i, x in enumerate(tc) if x.endswith("*"))
    row("T queued OFF for exactly the gates that are on and off as delivered", stars == sorted(["sh", "os", "voc", "files", "files-write", "files-admin", "ai"]), repr(stars))
    run_queue("sh-off os-off voc-off files-off files-write-off files-admin-off ai-off", False, "tighten")
    mm = {g: members(g) or [] for g in GROUPS.values()}
    reg2 = reg_fields()
    row("everything is back to the delivered state in the real groups and the real register (shared-read untouched)", all(ME not in v for v in mm.values())
        and all(reg2[i - 1].strip().lower() != "yes" for i in (7, 8, 9, 10, 11, 12, 15)), repr((mm, reg2[:16])))

    # ---- the audit trail has the verb's lines
    a = audit_tail(120)
    want = ["ssh", "api", "none", "files-on", "files-write-on", "files-admin-on", "ai-on", "sh-on", "os-on", "voc-on", "sh-off", "os-off", "voc-off", "files-off", "ai-off"]
    lost = [w for w in want if not re.search(r"modify\.account (route )?%s account=%s" % (re.escape(w), re.escape(ME)), a)]
    row("the audit trail has a line from modify.account for each change (the verb's own lines)", not lost, "missing: %s" % lost)

    typed("\x11", 1.5)
    typed("OFF\r", 1.5)
    return finish(0)


def finish(rc):
    """Restore the account whatever happened (sh, os, voc off; the six groups), say so, and print the verdict."""
    try:
        if S["s"] is not None:
            S["s"].finish()
    except Exception:
        pass
    sdsys_cmds("modify.account %s sh-off os-off voc-off none files-off ai-off" % ME)
    old = S.get("old_default")
    if old is not None:
        sdsys_cmds("set.start.default %s" % old if old else "set.start.default menu")
        if not old:
            sh("sudo rm -f %s/start.default" % SDSYS_DIR)
    left = {g: members(g) for g in GROUPS.values() if members(g) and ME in members(g)}
    print("witness-toolgates: after the cleanup the user is in these route groups: %s" % (sorted(left) or "none"))
    print("witness-toolgates: %d passed, %d failed -> %s" % (passed, failed, "PASSED" if failed == 0 and passed > 0 and rc == 0 else "FAILED"))
    return 0 if failed == 0 and passed > 0 and rc == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
