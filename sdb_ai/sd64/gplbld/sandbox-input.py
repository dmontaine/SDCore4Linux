#!/usr/bin/env python3
#
# sandbox-input.py - does the INPUT statement erase a character on Backspace, whichever byte the terminal
#                    sends for it, under a terminal type that names the OTHER one?  PAL-21 (S.62), the Windows
#                    port's _input fix of 22 Aug 2026 and the INPUT twin of verify-keys.py.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-input.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (a private SD built from a tree: no sudo, its own IPC keys,
# never the live system).  With --build the sandbox is built first from THIS tree and <dir> must be empty or
# absent.  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# THE DEFECT.  _input erased only on the byte the terminal type's kbs names.  A terminal that sends the other
# one (DEL under vt100, whose kbs is ^H; ^H under a type that names DEL) got NO erase, and because a
# single-line INPUT has no forward delete, the unmatched byte fell through to the catch-all and was APPENDED to
# the string.  On "INPUT pw HIDDEN" - the password prompts of MODIFY.PASSWORD - a mistake could not be
# corrected and the attempt to correct it made the entry longer.  _keycode (the command line) was fixed for
# this on 14 Sep 2026 (verify-keys.py); _input, a different routine, was not.
#
# THE INSTRUMENT IS THE VALUE THE PROGRAM GOT, not what the screen echoed: a program does INPUT x and INPUT y
# HIDDEN and prints GOT[<x>] and HID[<y>].  Each terminal type (vt100: kbs ^H; linux and xterm: kbs DEL) is
# sent "ab<erase>c" and "pq<erase>r" with each erase byte; a pass is GOT[ac] and HID[pr].  THE CONTROL sends
# no erase ("abc", "pqr") and must give GOT[abc] and HID[pqr], so the rows cannot pass by the program reading
# nothing.  Each session asks the type with TERM and the "Device" line must name it, or that row measured the
# wrong terminal and fails (SD ignores the environment's TERM; it is set inside the session).

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
RUN = "%05d" % (os.getpid() % 100000)
PROG = "zzin" + RUN
TYPES = ("vt100", "linux", "xterm")
ERASES = (("^H", "\x08"), ("DEL", "\x7f"))
passed = failed = 0


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
    say("sandbox-input: CANNOT RUN - " + msg)
    sys.exit(2)


def session(box, *cmds):
    say("    > [sd -internal] " + " | ".join(repr(c) for c in cmds))
    env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"))
    body = "\nTERM 200,9999\n" + "".join(c + "\n" for c in cmds) + "OFF\n"
    p = subprocess.run([os.path.join(box, "sys", "bin", "sd"), "-internal"], input=body,
                       cwd=os.path.join(box, "sys"), env=env, capture_output=True, text=True,
                       errors="replace", timeout=180)
    out = ANSI.sub("", p.stdout + p.stderr)
    out = out.split(":TERM 200,9999", 1)[-1]
    for line in out.splitlines():
        if line.strip() and not line.startswith(":") and not line.startswith("exit ") and not line.startswith("sd: SANDBOX"):
            say("      | " + repr(line.rstrip())[:150])
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-input.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-input: sandbox %s" % box)
    say("sandbox-input: tree    %s" % os.path.dirname(HERE))
    say("sandbox-input: program %s, terminal types %s" % (PROG, ", ".join(TYPES)))
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-input: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    src = os.path.join(sysd, "bp", PROG)
    try:
        say("\n--- setup ---------------------------------------------------------------------")
        with open(src, "wb") as f:
            f.write(("   input x\n   crt 'GOT[':x:']'\n   input y HIDDEN\n   crt 'HID[':y:']'\nend\n").encode("ascii"))
        out = session(box, "BASIC bp " + PROG)
        compiled = re.search(r"(?m)^Compiled 1 program\(s\) with no errors", out) is not None
        row("setup: the probe program compiled with no errors", compiled, "no success wording")
        if not compiled:
            bail("the probe did not compile")

        for t in TYPES:
            say("\n--- terminal type %s ------------------------------------------------------" % t)
            for label, erase in (("none", None),) + ERASES:
                a1 = "abc" if erase is None else "ab" + erase + "c"
                a2 = "pqr" if erase is None else "pq" + erase + "r"
                want_x, want_y = ("abc", "pqr") if erase is None else ("ac", "pr")
                say("  typed answers: %r and %r  (erase %s)" % (a1, a2, label))
                out = session(box, "TERM " + t, "TERM", "RUN bp " + PROG, a1, a2)
                dev = re.search(r"Device\s*:\s*(\S+)", out)
                row("%s/%s the session really is type %s" % (t, label, t), dev is not None and dev.group(1) == t,
                    "Device line: %r" % (dev.group(1) if dev else None))
                gx = re.search(r"(?m)^GOT\[(.*)\]\s*$", out)
                gy = re.search(r"(?m)^HID\[(.*)\]\s*$", out)
                if label == "none":
                    row("%s control: no erase byte -> INPUT got %r" % (t, want_x), gx is not None and gx.group(1) == want_x,
                        "got %r" % (gx.group(1) if gx else None))
                    row("%s control: and INPUT HIDDEN got %r" % (t, want_y), gy is not None and gy.group(1) == want_y,
                        "got %r" % (gy.group(1) if gy else None))
                else:
                    row("%s/%s THE ROW: INPUT erased, got %r" % (t, label, want_x), gx is not None and gx.group(1) == want_x,
                        "got %r" % (gx.group(1) if gx else None))
                    row("%s/%s and INPUT HIDDEN erased, got %r" % (t, label, want_y), gy is not None and gy.group(1) == want_y,
                        "got %r" % (gy.group(1) if gy else None))
                    # what the SCREEN was told: back, blank, back - not a bare blank (the Windows console's fault)
                    ex = "?ab\x08 \x08c"
                    ey = "?**\x08 \x08*"
                    row("%s/%s the screen echo was backspace, space, backspace: %r" % (t, label, ex),
                        re.search(r"(?m)^%s\s*$" % re.escape(ex), out) is not None, "no such echo line")
                    row("%s/%s and for the masked entry: %r" % (t, label, ey),
                        re.search(r"(?m)^%s\s*$" % re.escape(ey), out) is not None, "no such echo line")
    finally:
        for d in ("bp", "bp.out"):
            p = os.path.join(sysd, d, PROG)
            if os.path.exists(p):
                os.remove(p)

    say("\nsandbox-input: %d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        bail("no row ran - a broken test, not a pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
