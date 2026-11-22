#!/usr/bin/env python3
# test-tkrestart-units.py - the restart box and the root helper's sd-restart (S.301; SD Core for Windows' row 382), read off the source as text,
# and the helper's verb through its own --dry-run.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-tkrestart-units.py [--selftest]
#
#   No sudo.  It restarts nothing: the helper is run with --dry-run only, as whoever runs this.
#
#   R1  THE HELPER'S VERB: sd-restart takes no argument; the dry run ends before anything is asked of systemd; then root, then the caller (sdsys, or
#       root with no sudo), then "the unit is active", then systemctl restart --no-block of the unit, in that order; the success line is printed only
#       after systemd took the job
#   R2  THE UNIT IS THE HELPER'S OWN: SD_SERVICE_UNIT=sd.service, assigned once, not from the environment and not reset from it
#   R3  THE DRY RUN, run for real: "sd-elevate --dry-run sd-restart" prints the resolved command and exits 0; with an argument it is REFUSED, exit 2;
#       its usage lists the verb
#   R4  SUDOERS: no rule names sd-restart, so only the sdsys line (the whole helper) reaches it and %sdusers cannot
#   R5  $tk_restart is $internal, catalogued, takes four arguments, and starts as 'later'
#   R6  THE BOX: Restart and Not now, NOT NOW LAST (the default); anything but Restart returns before the page is closed or the helper asked
#   R7  THE ORDER ON RESTART: the page is closed, the screen cleared, the line shown, THEN the helper - one os.execute, of the fixed text, with no
#       variable in it; no execute, perform or chain
#   R8  SUCCESS IS THE HELPER'S OWN LINE, the same text the helper prints, and a non-zero status is never success
#   R9  ONE AUDIT LINE, lower case, after the helper answered: sd restart app=<page> status=asked|refused
#   R10 AFTER THE HELPER: a wait of a minute only when it was asked; then 'failed', the reason shown, Press Enter - never 'later'
#   R11 tool.config: ONE call, only under "takes effect: restart" AND the file and the running SD differing (the row's own mark), inside the branch
#       where the file is known to hold the new value, the status line drawn first, and take.screen when the answer is 'failed'; take.screen opens
#       the page for the administrator again
#   R12 ONLY AN ADMINISTRATOR'S PAGE: every program that calls $tk_restart opens with $tk_open(..., 'admin', ...), and nothing but $tk_restart asks the
#       helper for sd-restart
#
# It cannot say that SD restarts, that the session ends or what the screen shows: no sandbox is root or has a systemd unit.  That is the real-install
# witness (the Debian 13 VM): tool.config, E on LGNWAIT, Restart.  Exit 0 every check held, 1 one did not, 2 it could not run.

import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TREE = os.path.dirname(HERE)
BP = os.path.join(TREE, "sdsys", "gpl.bp")
ELEVATE = os.path.join(HERE, "sd-elevate")
ME = "test-tkrestart-units"


def read(path):
    try:
        with open(path, encoding="latin-1") as f:
            return f.read()
    except OSError:
        print("%s: CANNOT RUN - no %s" % (ME, path))
        sys.exit(2)


def code(src):
    """BASIC without comment lines and ;* tails."""
    return "\n".join(re.sub(r"\s*;\*.*$", "", ln) for ln in src.split("\n") if not ln.lstrip().startswith("*"))


def shcode(src):
    """bash without whole-line comments."""
    return "\n".join(ln for ln in src.split("\n") if not ln.lstrip().startswith("#"))


def ordered(text, *needles):
    at = 0
    for n in needles:
        at = text.find(n, at)
        if at < 0:
            return False
        at += len(n)
    return True


def load():
    raw = {"sd-elevate": read(ELEVATE), "sudoers": read(os.path.join(HERE, "sdcore.sudoers"))}
    for name in sorted(os.listdir(BP)):
        p = os.path.join(BP, name)
        if os.path.isfile(p) and not name.endswith(".h"):
            raw[name] = read(p)
    return raw


def dry(script_text, *args):
    """Run the helper text given, --dry-run, as this user.  Returns (status, output)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("SD_") and k not in ("SUDO_USER", "SUDO_UID")}
    with tempfile.TemporaryDirectory(prefix="tkrestart-") as d:
        path = os.path.join(d, "sd-elevate")
        with open(path, "w", encoding="latin-1") as f:
            f.write(script_text)
        try:
            r = subprocess.run(["bash", path, "--dry-run"] + list(args), capture_output=True, text=True, timeout=60, env=env)
        except (OSError, subprocess.TimeoutExpired) as e:
            return 99, str(e)
    return r.returncode, r.stdout + r.stderr


def checks(raw, run_helper=True):
    out = []

    def ck(n, what, ok):
        out.append((n, what, bool(ok)))

    el = shcode(raw["sd-elevate"])
    m = re.search(r"\n  sd-restart\)\n(.*?)\n    ;;\n", el, re.S)
    vb = m.group(1) if m else ""
    ck("R1", "the helper's verb: no argument, the dry run ends first, then root, the caller, the unit active, systemctl restart --no-block, the success line last",
       el.count("\n  sd-restart)\n") == 1 and ordered(
           vb, '[[ $# -eq 0 ]] || die "sd-restart takes no argument"', "[[ $DRY -eq 1 ]] && exit 0", "need_root",
           '[[ -z ${SUDO_USER:-} || ${SUDO_USER:-} == sdsys ]] || die "sd-restart is the administrator\'s',
           'systemctl is-active --quiet "$SD_SERVICE_UNIT" || die "', 'if ! systemctl restart --no-block "$SD_SERVICE_UNIT"; then', "exit 3", "fi",
           "printf '%s: restart of %s asked of systemd\\n' \"$PROG\" \"$SD_SERVICE_UNIT\"", "exit 0")
       and len(re.findall(r"(?m)^\s*(?:if ! )?systemctl ", vb)) == 2 and vb.count("asked of systemd\\n'") == 1 and "$1" not in vb and "$@" not in vb and "$*" not in vb)
    ck("R2", "the unit is the helper's own: SD_SERVICE_UNIT=sd.service, assigned once, never from the environment",
       len(re.findall(r"(?m)^SD_SERVICE_UNIT=sd\.service(\s|$)", el)) == 1 and len(re.findall(r"\bSD_SERVICE_UNIT=", el)) == 1 and "${SD_SERVICE_UNIT:-" not in el)
    if run_helper:
        s0, o0 = dry(raw["sd-elevate"], "sd-restart")
        s1, o1 = dry(raw["sd-elevate"], "sd-restart", "now")
        s2, o2 = dry(raw["sd-elevate"])
        ck("R3", "the dry run, run: resolved command and exit 0 (%d); an argument REFUSED, exit 2 (%d); the usage lists the verb" % (s0, s1),
           s0 == 0 and "sd-restart: systemctl restart --no-block sd.service, only when it is active" in o0 and "asked of systemd" not in o0
           and s1 == 2 and "REFUSED - sd-restart takes no argument" in o1 and s2 != 0 and "sd-elevate [--dry-run] sd-restart" in o2)
    su = shcode(raw["sudoers"])
    ck("R4", "sudoers: no rule names sd-restart; the sdsys line is the whole helper",
       "sd-restart" not in su and re.search(r"(?m)^sdsys ALL=\(root\) NOPASSWD: /usr/local/sbin/sd-elevate\s*$", su) is not None)

    tk = code(raw.get("tk_restart", ""))
    ck("R5", "$tk_restart is $internal, catalogued, takes four arguments and starts as 'later'",
       ordered(tk, "$internal", "subroutine tk_restart(ctx, why, res, msg)", "$catalog $tk_restart", "res = 'later'", "msg = ''", "call $tk_confirm("))
    ck("R6", "the box: Restart and Not now, Not now last; anything but Restart returns before the page is closed or the helper asked",
       ordered(tk, "call $tk_confirm('systemctl restart sd.service', lines, '', cres, cmsg, 'Restart SD?', '&Restart,&Not now')", "if cres # 'run' then", "return", "end",
               "call $tk_close(ctx)", "os.execute")
       and tk.count("call $tk_confirm(") == 1 and "signs out everyone, this session too." in tk)
    ck("R7", "the order on Restart: page closed, screen cleared, the line, then the helper - one os.execute of fixed text; no execute, perform or chain",
       ordered(tk, "call $tk_close(ctx)", "display @(-1) :", "display 'SD is restarting.", "os.execute ACCOS$ELEVATE : ' sd-restart 2>&1' capturing out", "stat = os.error()")
       and tk.count("os.execute") == 1 and tk.count("call $tk_close(") == 1 and not re.search(r"(?m)^\s*(execute|perform|chain)\b", tk))
    ck("R8", "success is the helper's own line, the text the helper prints, and a non-zero status is never success",
       "anchor = 'sd-elevate: restart of sd.service asked of systemd'" in tk and "if ln = anchor then asked = @true" in tk
       and ordered(tk, "asked = @false", "if ln = anchor then asked = @true", "next i", "if stat # 0 then asked = @false", "kernel(K$AUDIT")
       and "printf '%s: restart of %s asked of systemd\\n' \"$PROG\" \"$SD_SERVICE_UNIT\"" in vb and tk.count("asked = @true") == 1)
    ck("R9", "one audit line, lower case, after the helper answered",
       tk.count("K$AUDIT") == 1
       and "void kernel(K$AUDIT, 'sd restart app=' : downcase(app) : ' status=' : (if asked then 'asked' else 'refused'))" in tk
       and ordered(tk, "app = ctx<TK.C.APP>", "call $tk_close(ctx)", "stat = os.error()", "void kernel(K$AUDIT"))
    ck("R10", "after the helper: the wait only when asked; then 'failed', the reason, Press Enter; 'later' is never set again",
       ordered(tk, "void kernel(K$AUDIT", "if asked then", "for w = 1 to 60", "sleep 1", "next w", "end", "res = 'failed'", "display why.not", "display sysmsg(11865) :", "input junk",
               "msg = 'SD was not restarted: ' : why.not", "return")
       and tk.count("res = 'later'") == 1 and tk.count("res = 'failed'") == 1)

    pg = code(raw.get("tool_config", ""))
    cp = pg[pg.find("\nchange.param:"):]
    ck("R11", "tool.config: one call, under 'restart' inside the branch where the file holds the new value, the status line first, take.screen on 'failed'",
       pg.count("call $tk_restart(") == 1
       and ordered(cp, "call $tk_run(allow, sent, out, stat, err)", "if stat = 0 and ('S' : trim(now.f)) = ('S' : nv) then", "differs = 0", "if rj > 0 then differs = pdiff<rj>",
                   "\n      if k.eff = 'restart' and differs then\n         why = ",
                   "call $tk_frame(ctx, keys, panes<view>, msg)", "call $tk_restart(ctx, why, rres, rmsg)", "if rres = 'failed' then gosub take.screen", "end", "end else",
                   "msg = 'sd.conf was not changed'")
       and ordered(pg, "\ntake.screen:", "call $tk_open('tool.config', 'admin', ctx, err)", "if err # '' then", "done = 1", "return", "end", "call $tk_aipage('again', ctx, keys, '', '', aout)",
                   "gosub lay.declare", "gosub read.all", "gosub draw.all", "return"))

    callers = sorted(n for n, s in raw.items() if n not in ("sd-elevate", "sudoers", "tk_restart") and "$tk_restart(" in code(s))
    askers = sorted(n for n, s in raw.items() if n not in ("sd-elevate", "sudoers") and "sd-restart" in code(s))
    admin = all(re.search(r"call \$tk_open\('[a-z.]+', 'admin', ctx, err\)", code(raw[n])) is not None
                and not re.search(r"call \$tk_open\('[a-z.]+', '(?!admin')", code(raw[n])) for n in callers)
    ck("R12", "only an administrator's page calls it (%s), and only $tk_restart asks the helper (%s)" % (", ".join(callers) or "none", ", ".join(askers) or "none"),
       len(callers) >= 1 and admin and askers == ["tk_restart"])
    return out


VERB_ORDER_OLD = ("    need_root\n    [[ -z ${SUDO_USER:-} || ${SUDO_USER:-} == sdsys ]] || die \"sd-restart is the administrator's")
MUTANTS = [
    ("the verb takes an argument", "sd-elevate", '    [[ $# -eq 0 ]] || die "sd-restart takes no argument"\n', ""),
    ("the dry run restarts", "sd-elevate", "only when it is active\\n' \"$PROG\" \"$SD_SERVICE_UNIT\"\n    [[ $DRY -eq 1 ]] && exit 0\n", "only when it is active\\n' \"$PROG\" \"$SD_SERVICE_UNIT\"\n"),
    ("any caller may restart", "sd-elevate", VERB_ORDER_OLD, "    need_root\n    true || die \"sd-restart is the administrator's"),
    ("an inactive unit is restarted", "sd-elevate", '    systemctl is-active --quiet "$SD_SERVICE_UNIT" || die "', '    true || die "'),
    ("the helper waits for the restart", "sd-elevate", 'if ! systemctl restart --no-block "$SD_SERVICE_UNIT"; then', 'if ! systemctl restart "$SD_SERVICE_UNIT"; then'),
    ("the unit comes from the environment", "sd-elevate", "\nSD_SERVICE_UNIT=sd.service ", "\nSD_SERVICE_UNIT=${SD_SERVICE_UNIT:-sd.service} "),
    ("another unit", "sd-elevate", "\nSD_SERVICE_UNIT=sd.service ", "\nSD_SERVICE_UNIT=sdclient.socket "),
    ("the success line before systemd answered", "sd-elevate", '    systemctl is-active --quiet "$SD_SERVICE_UNIT" || die "',
     "    printf '%s: restart of %s asked of systemd\\n' \"$PROG\" \"$SD_SERVICE_UNIT\"; exit 0\n" + '    systemctl is-active --quiet "$SD_SERVICE_UNIT" || die "'),
    ("the helper's success words changed", "sd-elevate", "restart of %s asked of systemd\\n' \"$PROG\" \"$SD_SERVICE_UNIT\"\n    exit 0", "restart of %s queued\\n' \"$PROG\" \"$SD_SERVICE_UNIT\"\n    exit 0"),
    ("sudoers gives sd-restart to sdusers", "sudoers", "/usr/local/sbin/sd-elevate netcred-dir,", "/usr/local/sbin/sd-elevate netcred-dir, /usr/local/sbin/sd-elevate sd-restart,"),
    ("not internal", "tk_restart", "$internal\nsubroutine tk_restart", "subroutine tk_restart"),
    ("Restart is the default", "tk_restart", "'&Restart,&Not now'", "'&Not now,&Restart'"),
    ("any answer restarts", "tk_restart", "   if cres # 'run' then\n      msg = 'SD was not restarted: the change takes effect when SD is next started'\n      return\n   end\n", ""),
    ("the helper before the page is closed", "tk_restart", "   app = ctx<TK.C.APP>\n   call $tk_close(ctx)\n   display @(-1) :\n",
     "   app = ctx<TK.C.APP>\n   os.execute ACCOS$ELEVATE : ' sd-restart 2>&1' capturing out\n   call $tk_close(ctx)\n   display @(-1) :\n"),
    ("the screen not cleared", "tk_restart", "   display @(-1) :\n", ""),
    ("a variable on the helper's command line", "tk_restart", "os.execute ACCOS$ELEVATE : ' sd-restart 2>&1' capturing out", "os.execute ACCOS$ELEVATE : ' sd-restart ' : why : ' 2>&1' capturing out"),
    ("success by status alone", "tk_restart", "      if ln = anchor then asked = @true\n", "      asked = @true\n"),
    ("the status ignored", "tk_restart", "   if stat # 0 then asked = @false\n", ""),
    ("the anchor is not the helper's line", "tk_restart", "anchor = 'sd-elevate: restart of sd.service asked of systemd'", "anchor = 'sd-elevate: sd-restart'"),
    ("no audit line", "tk_restart", "   void kernel(K$AUDIT, 'sd restart app='", "   dummy = ('sd restart app='"),
    ("the audit line in capitals", "tk_restart", "'sd restart app=' : downcase(app)", "'SD RESTART app=' : app"),
    ("no wait for SD", "tk_restart", "      for w = 1 to 60\n         sleep 1\n      next w\n", ""),
    ("a failed restart says later", "tk_restart", "   res = 'failed'\n", "   res = 'later'\n"),
    ("it runs a sentence too", "tk_restart", "   stat = os.error()\n", "   stat = os.error()\n   execute 'who'\n"),
    ("the page asks after a session parameter too", "tool_config", "      if k.eff = 'restart' and differs then\n         why = ", "      if differs then\n         why = "),
    ("the page asks when SD already runs with the value", "tool_config", "      if k.eff = 'restart' and differs then\n         why = ", "      if k.eff = 'restart' then\n         why = "),
    ("differs is read from another row", "tool_config", "      if rj > 0 then differs = pdiff<rj>\n", "      differs = 1\n"),
    ("the page asks when the file was not changed", "tool_config", "      msg = 'sd.conf was not changed' : (if lastl = '' then '' else ': ' : lastl)\n",
     "      msg = 'sd.conf was not changed' : (if lastl = '' then '' else ': ' : lastl)\n      call $tk_restart(ctx, why, rres, rmsg)\n"),
    ("the page is not taken again", "tool_config", "         if rres = 'failed' then gosub take.screen", "         if rres = 'failed' then null"),
    ("the page comes back for anyone", "tool_config", "take.screen:\n   call $tk_open('tool.config', 'admin', ctx, err)", "take.screen:\n   call $tk_open('tool.config', '', ctx, err)"),
    ("the status line not drawn first", "tool_config", "         call $tk_frame(ctx, keys, panes<view>, msg)             ;* the status line under the box says what was done\n", ""),
    ("another program asks the helper", "tool_remote", "$internal\n", "$internal\n* x\n   os.execute 'sudo /usr/local/sbin/sd-elevate sd-restart'\n"),
]


def main():
    raw = load()
    if "--selftest" in sys.argv:
        if not all(ok for _, _, ok in checks(raw)):
            print("%s: the real tree does not pass" % ME)
            return 1
        missed = 0
        for label, name, old, new in MUTANTS:
            if old not in raw.get(name, ""):
                print("  [MISSED] %s: nothing to change" % label)
                missed += 1
                continue
            changed = dict(raw)
            changed[name] = raw[name].replace(old, new, 1)
            caught = not all(ok for _, _, ok in checks(changed, run_helper=(name == "sd-elevate")))
            print("  [%s] %s" % ("caught" if caught else "MISSED", label))
            missed += not caught
        print("selftest: %d caught, %d missed" % (len(MUTANTS) - missed, missed))
        return 1 if missed else 0
    print("%s: tree %s" % (ME, TREE))
    res = checks(raw)
    for n, what, ok in res:
        print("  [%s] %s %s" % ("PASS" if ok else "FAIL", n, what))
    bad = sum(1 for r in res if not r[2])
    print("%s: %d passed, %d failed" % (ME, len(res) - bad, bad))
    return 1 if bad or not res else 0


if __name__ == "__main__":
    sys.exit(main())
