#!/usr/bin/env python3
#
# sandbox-footpause.py - OPTION QUERY.FOOTER.PAUSE (1.2-0 bundle A-4, sheet 429).  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-footpause.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (empty or absent).
# Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 14 Oct 26 dm  Written for sheet 429.
# END-HISTORY
#
# THE INSTRUMENT IS THE EMULATED SCREEN of a pseudo-terminal session (ptydrive.py).  A report with a FOOTING
# on a terminal ends with its footer and then "n record(s) listed"; with the option set the prompt
# "Press RETURN to continue" must be on the screen and "record(s) listed" must NOT be until RETURN is typed.
# Controls: option off (no prompt, the count line appears at once), NO.PAGE with the option on (ignored),
# and a report with no footer with the option on (no prompt).

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ptydrive import PtySession  # noqa: E402

TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
passed = failed = 0
F = "zzfp%05d" % (os.getpid() % 100000)


def say(s=""):
    print(s)


def row(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        say("  [PASS] " + name)
    else:
        failed += 1
        say("  [FAIL] " + name + ("   <- " + detail if detail else ""))


def bail(msg):
    say("sandbox-footpause: CANNOT RUN - " + msg)
    sys.exit(2)


def sess(box, *cmds):
    say("    > " + " | ".join(cmds))
    p = subprocess.run([sys.executable, TOOL, box, "sess", os.path.join(box, "user_accounts")] + list(cmds),
                       capture_output=True, text=True, errors="replace", timeout=600)
    return ANSI.sub("", p.stdout + p.stderr)


def report(box, *cmds):
    """Run the commands on a terminal; return (screen text after the last command, screen after one RETURN)."""
    env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"), TERM="xterm")
    s = PtySession([os.path.join(box, "sys", "bin", "sd")], os.path.join(box, "user_accounts"), env, 100, 24)
    s.settle(1.0)
    s.type("TERM xterm\r")
    s.type("TERM 100,24\r")
    for c in cmds[:-1]:
        s.type(c + "\r", idle=0.8)
    s.type(cmds[-1] + "\r", idle=1.2)
    before = "\n".join(l for l in s.screen.lines() if l.strip())
    s.type("\r", idle=0.8)
    after = "\n".join(l for l in s.screen.lines() if l.strip())
    s.type("OFF\r", idle=0.5)
    s.finish()
    return before, after


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-footpause.py <dir> [--build]")
    box = os.path.abspath(args[0])
    say("sandbox-footpause: sandbox %s" % box)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-footpause: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(box, "sys", "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    bp = os.path.join(box, "sys", "bp")
    prog = "   open '%s' to f else stop 'no file'\n   for i = 1 to 3\n      write 'v':i on f, 'r':i\n   next i\n   crt 'FIXTURE DONE'\nend\n" % F
    with open(os.path.join(bp, F + "mk"), "w") as fh:
        fh.write(prog)
    out = sess(box, "DELETE.FILE %s" % F, "CREATE.FILE %s" % F, "BASIC bp %smk" % F, "RUN bp %smk" % F)
    if "FIXTURE DONE" not in out:
        bail("fixture not made:\n" + out[-500:])

    PROMPT = "Press RETURN to continue"
    LIST = "LIST %s FOOTING \"end of report\"" % F
    say("\n--- the option ---------------------------------------------------------------------------")
    b, a = report(box, LIST)
    row("CONTROL: option off - the footer is followed by the count line and no prompt",
        "end of report" in b and PROMPT not in b and "record(s) listed" in b, b[-300:])
    b, a = report(box, "OPTION QUERY.FOOTER.PAUSE", LIST)
    row("THE ROW: option on - the footer is shown and the prompt waits", "end of report" in b and PROMPT in b, b[-300:])
    # (SD prints the count line above the footer, so it is on the screen before the prompt: the row is that the prompt
    # comes AFTER the footer and that nothing follows the prompt until RETURN)
    row("THE ROW: option on - the prompt comes after the footer and is the last thing before RETURN",
        b.find(PROMPT) > b.find("end of report") >= 0 and b.rstrip().endswith(PROMPT), b[-300:])
    row("THE ROW: after RETURN the prompt is gone and the count line appears",
        PROMPT not in a and "3 record(s) listed" in a, a[-300:])
    say("\n--- controls with the option on --------------------------------------------------------")
    b, a = report(box, "OPTION QUERY.FOOTER.PAUSE", LIST + " NO.PAGE")
    row("NO.PAGE: the option is ignored", PROMPT not in b and "record(s) listed" in b, b[-300:])
    b, a = report(box, "OPTION QUERY.FOOTER.PAUSE", "LIST %s" % F)
    row("no footer: no prompt", PROMPT not in b and "record(s) listed" in b, b[-300:])
    b, a = report(box, "OPTION QUERY.FOOTER.PAUSE", "OPTION", "LIST %s FOOTING \"x\" NO.PAGE" % F)
    row("OPTION with no name lists QUERY.FOOTER.PAUSE", "QUERY.FOOTER.PAUSE" in b, b[-300:])

    say("\nsandbox-footpause: %d passed, %d failed" % (passed, failed))
    sys.exit(0 if failed == 0 else 1)


main()
