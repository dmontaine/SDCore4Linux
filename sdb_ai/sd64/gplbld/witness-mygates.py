#!/usr/bin/env python3
#
# witness-mygates.py - TOOL.GATES for an ACCOUNT HOLDER on a REAL install: the read-only page ($tool_mygates) in the installing user's own ordinary session, on a pseudo-terminal,
# against the real kernel, the real /etc/group and the real register.  The half of S.75 A2's holder view that sandbox-tool-mygates.py cannot show (there the group lookup is a copy
# that reads a scratch file).
#
#   python3 witness-mygates.py       (on the VM, as the installing user, with ptydrive.py and termscreen.py beside this file; sudo needs no password there)
#
# The ordinary session is `sd` run by the installing user (not an administrator).  SDSYS is used only to change the account from outside, on a pipe, the way sdnet-wlib.sh's sd_as
# does it (the loginuid bridge); every change is undone at the end whatever happened.  The start default is set to terminal for the run (the page is reached from the prompt) and put back.
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
passed = failed = 0
TITLES = ["Remote terminal", "API server", "Shell", "OS.EXECUTE", "Other accounts", "Save VOC", "Save programs", "Save dictionaries", "Remote files", "Read shared", "Write shared",
          "Files route", "Files write", "Files admin", "AI", "Raw sockets"]
F5 = "\x1b[[E"      # SD's own terminfo entry for xterm reads F5 as this (sandbox-home.py's key table); \x1b[15~ is ignored, which showed ssh off after a refresh (24 Oct, probed on the VM)


def row(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print("PASS  " + name, flush=True)
    else:
        failed += 1
        print("FAIL  " + name + ("   <- " + str(detail)[:400] if detail else ""), flush=True)


def sh(cmd):
    return subprocess.run(["bash", "-c", cmd], capture_output=True, text=True).stdout


def sdsys_cmds(body):
    inner = 'printf "%s\\n" "$(id -u sdsys)" > /proc/self/loginuid 2>/dev/null; exec sudo -u sdsys "$1"'
    r = subprocess.run(["sudo", "sh", "-c", inner, "sd-run", SD], input=("\nTERM 200,9999\n%s\nOFF\n" % body).encode(), cwd=SDSYS_DIR, capture_output=True, timeout=180)
    return re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", r.stdout.decode("latin1")).replace("\r", "")


env = dict(os.environ, TERM="xterm", LC_ALL="C", LANG="C")
for k in ("SSH_CONNECTION", "SSH_TTY", "SSH_CLIENT"):
    env.pop(k, None)


class Page:
    def __init__(self):
        self.s = PtySession([SD], os.path.expanduser("~"), env, 140, 43)
        self.s.settle(3.0)

    def line(self, n):
        L = self.s.screen.lines()
        return L[n].rstrip() if n < len(L) else ""

    def text(self):
        return "\n".join(l.rstrip() for l in self.s.screen.lines())

    def typed(self, x, idle=0.9):
        self.s.type(x, idle=idle)

    def table(self):
        out = {}
        for n in range(3, 19):
            l = self.line(n)
            t = l[3:27].strip()
            if t:
                out[t] = l[27:33].strip()
        return out

    def end(self):
        try:
            self.s.finish()
        except Exception:
            pass


def main():
    print("witness-mygates: user %s, SD %s, %s" % (ME, SD, time.strftime("%F %T")))
    if not os.path.exists(SD):
        print("witness-mygates: CANNOT RUN - no SD at " + SD)
        return 2
    old_default = sh("sudo cat %s/start.default 2>/dev/null" % SDSYS_DIR).strip()
    sdsys_cmds("set.start.default terminal")
    row("set.start.default terminal was accepted", sh("sudo cat %s/start.default" % SDSYS_DIR).strip() == "terminal")
    rc = 1
    p = None
    try:
        p = Page()
        row("the user's own session is at the prompt (an ordinary session, not the home screen)", re.search(r"^:", p.text(), re.M) is not None or ":" in p.line(41) or ":" in p.line(42), p.text()[-300:])
        who = sh("printf '\\nTERM 200,9999\\nWHO.AM.I\\nOFF\\n' | timeout 60 %s 2>&1 | sed -e 's/\\x1b\\[[0-9;?]*[A-Za-z]//g'" % SD)
        row("this user is NOT an administrator (WHO.AM.I says Admin? No), so what follows is the holder's page", re.search(r"Admin\?\s*:\s*No", who) is not None, who[-300:])
        p.typed("tool.gates\r", 3.5)
        T = p.text()
        row("tool.gates in the user's own account draws the HOLDER's page, not the matrix", "What this account may do" in T and "Gates by account" not in T, T[-500:])
        tb = p.table()
        row("the sixteen gates are listed, in the table's order", list(tb) == TITLES, repr(list(tb)))
        row("the delivered state: every gate off, shared-read ON, sockets planned", {k: v for k, v in tb.items()} == {t: ("ON" if t == "Read shared" else "plan" if t == "Raw sockets" else "off") for t in TITLES}, repr(tb))
        row("the count line says who and where: 'Signed on as %s in the account %s.  1 of 16 gates are on'" % (ME, ME), re.search(r"Signed on as %s in the account %s\.  1 of 16 gates are on" % (ME, ME), p.line(19)) is not None, p.line(19))

        # ---- the administrator changes the account from outside: a route group shows at once, a register gate waits for the next entry
        out = sdsys_cmds("modify.account %s ssh sh-on" % ME)
        row("modify.account (as SDSYS, on a pipe) ssh + sh-on was carried out", "2 actions carried out" in out, out[-300:])
        p.typed(F5, 2.0)
        tb2 = p.table()
        row("F5: ssh is ON now (membership of sdssh is read from the system each time) and sh is still off (this session loaded its gates when it entered the account)", tb2.get("Remote terminal") == "ON" and tb2.get("Shell") == "off", repr((tb2.get("Remote terminal"), tb2.get("Shell"))))
        row("the real /etc/group agrees about ssh", ME in ((sh("getent group sdssh").strip().split(":")[-1]).split(",")), sh("getent group sdssh"))
        p.typed("\x11", 1.5)
        p.typed("exit\r", 1.0)
        p.end()

        p = Page()
        p.typed("tool.gates\r", 3.5)
        tb3 = p.table()
        row("a NEW session of the same user shows sh ON (the register is read at entry)", tb3.get("Shell") == "ON" and tb3.get("Remote terminal") == "ON", repr((tb3.get("Shell"), tb3.get("Remote terminal"))))
        row("the page has changed nothing: the register still has sh yes only because SDSYS said so, and the groups are as SDSYS left them", ME in sh("getent group sdssh") and sh("sudo cat %s/accounts/%s" % (SDSYS_DIR, ME)).split("\n")[6].strip().lower() == "yes")
        p.typed("\x11", 1.5)
        p.typed("exit\r", 1.0)
        p.end()
        p = None
        rc = 0
    finally:
        if p is not None:
            p.end()
        sdsys_cmds("modify.account %s sh-off none" % ME)
        if old_default:
            sdsys_cmds("set.start.default %s" % old_default)
        else:
            sdsys_cmds("set.start.default menu")
            sh("sudo rm -f %s/start.default" % SDSYS_DIR)
        left = [g for g in ("sdssh", "sdapi") if ME in sh("getent group %s" % g)]
        print("witness-mygates: after the cleanup the user is in these route groups: %s; sh in the register: %s" % (left or "none", sh("sudo cat %s/accounts/%s" % (SDSYS_DIR, ME)).split("\n")[6].strip()))
    print("witness-mygates: %d passed, %d failed -> %s" % (passed, failed, "PASSED" if failed == 0 and passed > 0 and rc == 0 else "FAILED"))
    return 0 if failed == 0 and passed > 0 and rc == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
