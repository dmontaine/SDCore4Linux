#!/usr/bin/env python3
#
# sandbox-dbgui.py - the debugger's full-screen display, on the screen library, on a pseudo-terminal.  No install,
# no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-dbgui.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or
# absent).  Exit 0 every row passed, 1 a row failed, 2 it could not run.  Only one private SD can exist on a machine
# (shared memory keys 0x53434c91/92): stop the sandbox afterwards with sandbox-fromtree.py <dir> stop.
#
# START-HISTORY:
# 13 Oct 26 dm  Written when the debugger's drawing moved onto the screen library (owner: "use the TUI on ced and
#               debugger").  The debugger's own command-by-command suite is sandbox-dbgcoll.py, which has no terminal and
#               so never reaches the full-screen code.
# END-HISTORY
#
# HOW IT DRIVES THE DEBUGGER.  A program compiled with BASIC ... DEBUGGING and holding a DEBUG statement is run on a
# pseudo-terminal (ptydrive.py) and stops at the debugger, which on a terminal with a scrolling region (xterm's)
# takes the whole screen: the title on the top row, the source, five rows of messages, the command line.  The screen is
# read from the emulator in termscreen.py: its text and the colours of its cells.  Each row that turns something on
# has a control row; a program that never reached the debugger makes its rows fail, not pass.

import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ptydrive import PtySession  # noqa: E402

TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
PROG = "zzdu" + "%05d" % (os.getpid() % 100000)
passed = failed = 0
RET, F1 = "\r", "\x1bOP"

SOURCE = """   s = 'plain' ; t = 'a':char(9):'b'
   n = 5
   debug
   crt 'AFTER-ONE'
   crt 'AFTER-TWO'
end
"""


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
    say("sandbox-dbgui: CANNOT RUN - " + msg)
    sys.exit(2)


def sess(box, *cmds):
    say("    > " + " | ".join(cmds))
    p = subprocess.run([sys.executable, TOOL, box, "sess", os.path.join(box, "user_accounts")] + list(cmds),
                       capture_output=True, text=True, errors="replace", timeout=600)
    out = ANSI.sub("", p.stdout + p.stderr)
    return out.split(":TERM 200,9999", 1)[-1]


class Term:
    def __init__(self, box, cmd, cols=100, rows=30):
        env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"), TERM="xterm")
        self.s = PtySession([os.path.join(box, "sys", "bin", "sd")], os.path.join(box, "user_accounts"), env, cols, rows)
        self.s.settle(1.5)
        self.s.type("TERM xterm\r", idle=0.8)
        self.s.type("TERM %d,%d\r" % (cols, rows), idle=0.8)
        self.s.type(cmd + "\r", idle=2.5)

    def keys(self, *chunks, idle=0.6):
        for c in chunks:
            self.s.type(c, idle=idle)
        return self.lines()

    def lines(self):
        return self.s.screen.lines()

    def style(self, r, c):
        return self.s.screen.style(r, c)

    def end(self):
        self.s.type("\rOFF\r", idle=0.5)
        self.s.finish()


def where(L, text):
    for r, l in enumerate(L):
        c = l.find(text)
        if c >= 0:
            return r, c
    return None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-dbgui.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-dbgui: sandbox %s" % box)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-dbgui: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    with open(os.path.join(sysd, "bp", PROG), "w") as fh:
        fh.write(SOURCE)
    try:
        say("\n--- setup -------------------------------------------------------------------------------------------")
        out = sess(box, "BASIC bp %s DEBUGGING" % PROG)
        row("setup: the program compiled in debug mode", "with no errors" in out, out[-300:])

        say("\n--- the screen when the debugger takes over ---------------------------------------------------------")
        t = Term(box, "RUN bp %s" % PROG)
        L = t.lines()
        sr = where(L, "debug")
        row("setup: the debugger is up, full screen: the source is on the screen with its line numbers",
            sr is not None and any(re.match(r"^\s*1:\s+s = 'plain'", l) for l in L), "\n".join(L[:8]))
        row("the title is on the top row (the program's pathname, cut to the screen: the line number may be off the end)",
            L[0].strip() != "" and L[0].lstrip().startswith("/"), repr(L[0]))
        fg0, bg0, fl0 = t.style(0, 2)
        row("the title bar is black on white (the 'bar' style of the classic theme the debugger uses while it is up)",
            (fg0, bg0) == (0, 7), repr(t.style(0, 2)))
        r3 = next((i for i, l in enumerate(L) if re.match(r"^\s*4: ", l)), None)
        row("the line about to run (4, the one after DEBUG) is in the highlight style (white on green); its neighbour is not",
            r3 is not None and t.style(r3, 10) != t.style(r3 - 1, 10) and t.style(r3, 10)[1] == 2, repr((r3, t.style(r3 or 0, 10), t.style((r3 or 1) - 1, 10))))
        row("the source is white on blue (the 'text' style)", sr is not None and t.style(sr[0] - 1, 10)[1] == 4, repr(t.style((sr or (1, 0))[0] - 1, 10)))
        last = max(i for i, l in enumerate(L) if l.strip())
        cl = 28                                         # the command line: the last row but one is the data area's last
        row("the command line is on the last row, with the > prompt, in the bar style",
            L[29].startswith(">") and t.style(29, 0)[:2] == (0, 7), repr((L[29], t.style(29, 0))))

        say("\n--- commands ------------------------------------------------------------------------------------------")
        L = t.keys("/s", RET)
        row("a variable's value appears in the data area, above the command line", any("String (5 bytes)" in l and "plain" in l for l in L[22:29]), "\n".join(L[22:30]))
        row("...and the command typed is echoed there with its prompt", any(l.startswith(">/s") for l in L[22:29]), "\n".join(L[22:30]))
        # 16 Oct 26: QM4 Fixes 550 (the ^ command) and 193 (WINDOW n)
        L = t.keys("/t", RET)
        row("550: CONTROL: a tab in a string is shown as ?", any('String (3 bytes): "a?b"' in l for l in L[22:29]), "\n".join(L[22:30]))
        L = t.keys("^", RET)
        row("550: ^ says the characters are now shown as ^nnn", any("Non-printing characters are shown as ^nnn" in l for l in L[22:29]), "\n".join(L[22:30]))
        L = t.keys("/t", RET)
        row("550: ... and the tab is shown as ^9, the length still 3", any('String (3 bytes): "a^9b"' in l for l in L[22:29]), "\n".join(L[22:30]))
        L = t.keys("^", RET, "/t", RET)
        row("550: a second ^ puts the ? back", any('String (3 bytes): "a?b"' in l for l in L[22:29]), "\n".join(L[22:30]))
        before = t.style(20, 0)[:2]
        L = t.keys("window 10", RET)
        row("193: CONTROL: with the usual 5 rows, row 20 was source (white on blue)", before == (7, 4) or before[1] == 4, repr(before))
        row("193: WINDOW 10 makes the data area ten rows: row 20 is now in the command style (black on white)", t.style(20, 0)[:2] == (0, 7), repr(t.style(20, 0)))
        row("193: ... the command line is still the last row", L[29].startswith(">"), repr(L[29]))
        L = t.keys("/s", RET)
        row("193: ... and a value shows in the larger area", any("String (5 bytes)" in l and "plain" in l for l in L[19:29]), "\n".join(L[18:30]))
        row("193: ... the source is still shown above it", any(re.match(r"^\s*1:\s+s = 'plain'", l) for l in L[1:19]), "\n".join(L[:6]))
        L = t.keys("window 3", RET)
        row("193: WINDOW 3 is refused with the message of the range", any("The data area must be 5 to 15 lines" in l for l in L[19:29]), "\n".join(L[19:30]))
        L = t.keys("window 5", RET, "/s", RET)
        row("193: WINDOW 5 puts it back: row 20 is source again", t.style(20, 0)[1] == 4, repr(t.style(20, 0)))
        L = t.keys("brk 5", RET)
        r5 = next((i for i, l in enumerate(L) if re.match(r"^\s*5: ", l)), None)
        r6 = next((i for i, l in enumerate(L) if re.match(r"^\s*6: ", l)), None)
        r5 = r5 if r5 is not None else 0
        r6 = r6 if r6 is not None else 0
        row("BRK 5 puts line 5's number in the breakpoint style (set apart from line 6's)",
            r5 > 0 and t.style(r5, 0) != t.style(r6, 0), repr((r5, r6, t.style(r5, 0), t.style(r6, 0))))
        row("...the breakpoint's number is in a different colour from an ordinary number", r5 > 0 and t.style(r5, 0)[0] != t.style(r6, 0)[0], repr((t.style(r5, 0), t.style(r6, 0))))

        say("\n--- help --------------------------------------------------------------------------------------------")
        L = t.keys(F1)
        row("F1 shows the help in a box with an OK button, over the debugger's screen", "[ OK ]" in "\n".join(L), "\n".join(L[:20]))
        L = t.keys(RET)
        row("Return closes it: the source and the command line are back", "[ OK ]" not in "\n".join(L) and L[29].startswith(">"), "\n".join(L[:4] + L[28:30]))

        say("\n--- leaving ------------------------------------------------------------------------------------------")
        L = t.keys("r", RET, idle=1.0)
        row("R with a breakpoint on line 5 runs to it: the program printed AFTER-ONE on its own screen, and the debugger is "
            "up again on the alternate one with line 5 about to run",
            re.search(r"(?m)^\s*5:\s+crt 'AFTER-TWO'", "\n".join(L)) is not None and t.style(next(i for i, l in enumerate(L) if re.match(r"^\s*5: ", l)), 10)[1] == 2,
            "\n".join(l for l in L if l.strip())[-300:])
        L = t.keys("clr", RET, "r", RET, idle=1.0)
        row("CLR then R runs on to the end: the debugger's screen is gone and the program's own output is on the terminal's own screen",
            any(l.strip() == "AFTER-TWO" for l in L) and not any(re.match(r"^\s*\d+:\s", l) for l in L), "\n".join(l for l in L if l.strip())[-300:])
        ra = where(L, "AFTER-ONE")
        row("...and in the terminal's own colours: the debugger's theme was given back",
            ra is not None and t.style(ra[0], ra[1])[:2] == (None, None),
            repr([(i, l.rstrip()[:50], t.style(i, max(l.find("AFTER"), 0))) for i, l in enumerate(L) if "AFTER" in l]))
        t.end()

        say("\n--- MESSAGE ... IMMEDIATE (the same alternate screen, once AccuTerm's was gone) ---------------------")
        # The receiver is at the command prompt (the kernel takes the event when the next key arrives, as it always has).
        # 'x' is that key: it is not a button letter, so the box stays up until Return.
        a = Term(box, "WHO")
        before = [l for l in a.lines() if l.strip()]
        sess(box, "MESSAGE ALL IMMEDIATE hello-imm")
        L = a.keys("x", idle=1.0)
        row("control: nothing of the message was on the receiver's screen before a key arrived", not any("hello-imm" in l for l in before), repr(before[-3:]))
        row("a message sent IMMEDIATE is shown in a box over the receiver's screen, with its text and an OK button",
            any("hello-imm" in l for l in L) and any("[ OK ]" in l for l in L), "\n".join(l for l in L if l.strip())[-400:])
        row("...with where it came from (Message from user)", any("Message from user" in l for l in L), "\n".join(l for l in L if l.strip())[-300:])
        row("...on the alternate screen: the receiver's own screen (its WHO) is not under the box", not any("WHO" in l for l in L), "\n".join(l for l in L if l.strip())[-300:])
        L = a.keys(RET, idle=1.0)
        row("Return closes it and the receiver's own screen is back, without the message",
            not any("[ OK ]" in l for l in L) and not any("hello-imm" in l for l in L) and any("WHO" in l for l in L),
            "\n".join(l for l in L if l.strip())[-300:])
        a.end()
    finally:
        say("\n--- cleanup ---------------------------------------------------------------------------------------")
        for d in ("bp", "bp.out"):
            for nm in (PROG, PROG + "w"):
                pth = os.path.join(sysd, d, nm)
                if os.path.exists(pth):
                    os.remove(pth)

    say("\nsandbox-dbgui: %d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        bail("no row ran - a broken test, not a pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
