#!/usr/bin/env python3
#
# sandbox-gpm.py - S.94 (31 Oct 2026): the Linux console's mouse through the gpm daemon, with a STAND-IN daemon.  No install, no sudo, no console.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-gpm.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 every row passed, 1 a row failed,
# 2 it could not run.
#
# START-HISTORY:
# 31 Oct 26 dm  New with gplsrc/gpmmouse.c.
# END-HISTORY
#
# WHAT RUNS.  The sandbox build carries a socket path of its own and may talk to a pseudo terminal (sandbox-txnfail.py SANDBOX_PATCHES: SD_GPM_SOCK, SD_GPM_ANY_TTY; the shipped build asks for
# a text console and /dev/gpmctl).  gpmfake.py listens there, and a session of TERM linux opens tool.keys, the toolkit's key tester, whose Mouse box counts what the screen library was given.
# THE INSTRUMENT IS THAT BOX, as in sandbox-realkeys.py: every row reads what $sl_key reported (its last event and its counters), not what the daemon was told to send.
#
#   G1  the session connects once, with the record libgpm would send (every event wanted, MOVE and HARD left to gpm so that it draws the pointer, the session's pid)
#   G2  a press and a release of each button, with the cell
#   G3  a drag, a wheel up and a wheel down, modifiers, a press of two buttons in one record
#   G4  what is NOT a report: a plain move; half a record (nothing until the rest comes); a record of another kind
#   G5  the daemon stops: the session lives on and still takes keys
#   G6  leaving the page disconnects; a session of another terminal type never connects (the control)
import importlib.util
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


rk = _load("sandbox_realkeys_for_gpm", "sandbox-realkeys.py")
from tuirows import Rows  # noqa: E402
import gpmfake as gf  # noqa: E402

R = Rows("gpm")
say = rk.say
KEYSET = int(os.environ.get("SDBOX_KEYSET", "0"))
SOCK = "/tmp/sdbox-gpm-%d/gpm.sock" % KEYSET


def mouse_state(t):
    """(events, press, release, drag, up, down, last) read off the Mouse box and the Terminal box of tool.keys"""
    L = t.lines()
    text = "\n".join(L)
    m = re.search(r"Mouse\s+(\d+) events", text)
    p = re.search(r"Press (\d+)\s+release (\d+)", text)
    d = re.search(r"Drag\s+(\d+)\s+wheel up (\d+)\s+down (\d+)", text)
    last = ""
    for l in L:
        if "│ Last " in l:
            last = l.split("│ Last", 1)[1].strip().rstrip("│").strip()
            break
    if not (m and p and d):
        return None
    return int(m.group(1)), int(p.group(1)), int(p.group(2)), int(d.group(1)), int(d.group(2)), int(d.group(3)), last


def tool_keys(box, label, term="linux"):
    t = rk.Term(box, label, term=term)
    t.s.type("tool.keys\r", idle=1.5)
    t.wait(1.5)
    return t if t.keys_box() is not None else None


def settle(t, secs=1.0):
    t.wait(secs)
    return mouse_state(t)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        rk.bail("usage: sandbox-gpm.py <dir> [--build]")
    box = os.path.abspath(args[0])
    say("sandbox-gpm: sandbox %s   tree %s   stand-in daemon %s" % (box, os.path.dirname(HERE), SOCK))
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            rk.bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, rk.TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=1200)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            rk.bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-gpm: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(box, "sys", "bin", "sd")):
        rk.bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, rk.TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)
    # (no test that the binary carries the stand-in path: the compiler writes a short constant string into the code and the text is not in the file.  A build that did not take the patches
    #  never connects, and G1a says so.)
    fake = gf.FakeGpm(SOCK)
    try:
        run_rows(box, fake)
    finally:
        fake.close()
    return R.finish()


def run_rows(box, fake):
    say("\n--- G1: the connection")
    t = tool_keys(box, "G")
    if t is None:
        R.row("G0 the instrument: tool.keys is reached under TERM linux", False, "the page did not draw")
        return
    R.row("G0 the instrument: tool.keys is reached, SD's terminal type is linux", t.sd_type() == "linux", repr(t.sd_type()))
    c = fake.wait_client(10)
    R.row("G1a the session connected to the daemon, once", c is not None and fake.connections == 1, repr((c, fake.connections)))
    if c is None:
        t.end()
        return
    R.row("G1b the record asks for every event, leaves MOVE and HARD to gpm (so that gpm draws the pointer) and no modifier filter",
          c["eventMask"] == 0xFFFF and c["defaultMask"] == (gf.MOVE | 256) and c["minMod"] == 0 and c["maxMod"] == 0xFFFF, repr(c))
    R.row("G1c it names the session's own process and a console number", c["pid"] > 1 and c["vc"] >= 1 and os.path.exists("/proc/%d" % c["pid"]), repr(c))
    s0 = settle(t, 0.5)
    R.row("G1d control: nothing has been counted yet", s0 is not None and s0[0] == 0, repr(s0))
    if s0 is None:
        t.end()
        return

    say("\n--- G2: presses and releases")
    n = 0
    for name, btn, want in (("left", gf.B_LEFT, 1), ("middle", gf.B_MIDDLE, 2), ("right", gf.B_RIGHT, 3)):
        fake.event(gf.DOWN | gf.SINGLE, 21, 11, buttons=btn)
        s = settle(t, 0.8)
        n += 1
        R.row("G2 %s press at gpm cell 21,11 is `press button %d at 20,10` (gpm counts from 1, the library from 0)" % (name, want),
              s is not None and s[6].startswith("press button %d at 20,10" % want) and s[0] == n, repr(s))
        fake.event(gf.UP | gf.SINGLE, 21, 11, buttons=btn)
        s = settle(t, 0.8)
        n += 1
        R.row("G2 %s release is `release button %d at 20,10`" % (name, want), s is not None and s[6].startswith("release button %d at 20,10" % want) and s[0] == n, repr(s))
    R.row("G2d the counters: 3 presses, 3 releases", s is not None and s[1] == 3 and s[2] == 3, repr(s))

    say("\n--- G3: drag, wheel, modifiers, two buttons at once")
    fake.event(gf.DOWN | gf.SINGLE, 31, 6, buttons=gf.B_LEFT)
    fake.event(gf.DRAG | gf.SINGLE | gf.MFLAG, 36, 6, buttons=gf.B_LEFT, dx=5)
    fake.event(gf.UP | gf.SINGLE | gf.MFLAG, 36, 6, buttons=gf.B_LEFT)
    s = settle(t, 1.2)
    R.row("G3a a press, a drag with the button held and a release: the drag is `drag button 1 at 35,5`, counted once", s is not None and s[3] == 1 and s[1] == 4 and s[2] == 4, repr(s))
    fake.event(gf.MOVE, 11, 11, wdy=1)
    s = settle(t, 0.8)
    R.row("G3b a MOVE that carries a wheel displacement of +1 is a wheel up at 10,10", s is not None and s[4] == 1 and s[6].startswith("wheel button up at 10,10"), repr(s))
    fake.event(gf.MOVE, 11, 11, wdy=-1)
    s = settle(t, 0.8)
    R.row("G3c a displacement of -1 is a wheel down", s is not None and s[5] == 1 and s[6].startswith("wheel button down"), repr(s))
    fake.event(gf.DOWN | gf.SINGLE, 5, 5, buttons=gf.B_LEFT, mods=gf.MOD_SHIFT | gf.MOD_CTRL)
    s = settle(t, 0.8)
    R.row("G3d shift and control held at a press are `(sc)` in the library's event", s is not None and s[6].endswith("(sc)") and "press button 1 at 4,4" in s[6], repr(s))
    fake.event(gf.UP | gf.SINGLE, 5, 5, buttons=gf.B_LEFT)
    before = settle(t, 0.5)
    fake.event(gf.DOWN | gf.SINGLE, 7, 7, buttons=gf.B_LEFT | gf.B_RIGHT)
    s = settle(t, 1.0)
    R.row("G3e a record that names two buttons is two presses (left, then right)", before is not None and s is not None and s[1] == before[1] + 2 and s[0] == before[0] + 2, repr((before, s)))
    fake.event(gf.UP | gf.SINGLE, 7, 7, buttons=gf.B_LEFT | gf.B_RIGHT)
    settle(t, 0.5)

    say("\n--- G4: what is not a report")
    before = settle(t, 0.5)
    fake.event(gf.MOVE, 50, 20)
    fake.event(gf.MOVE, 51, 21, dx=1, dy=1)
    s = settle(t, 1.0)
    R.row("G4a a plain move (no button, no wheel) is nothing: the session asked for reports with a button down only", before is not None and s == before, repr((before, s)))
    ev = gf.EVENT.pack(gf.B_LEFT, 0, 1, 0, 0, 40, 12, gf.DOWN | gf.SINGLE, 0, 0, 0, 0)
    fake.raw(ev[:10])
    s = settle(t, 1.5)
    R.row("G4b half of a record changes nothing, and the session does not spin on it (it is still answering a key)", s == before, repr((before, s)))
    fake.raw(ev[10:])
    s = settle(t, 1.0)
    R.row("G4c the other half makes the press at 39,11", s is not None and before is not None and s[1] == before[1] + 1 and "press button 1 at 39,11" in s[6], repr((before, s)))
    fake.event(gf.UP | gf.SINGLE, 40, 12, buttons=gf.B_LEFT)
    settle(t, 0.5)
    typed = t.press("a", "a")[0]
    R.row("G4d nothing was typed by any of it and a letter is still the key a", typed == ["a"], repr(typed))

    say("\n--- G5: the daemon stops")
    fake.drop()
    t.wait(1.5)
    typed = t.press("b", "b")[0]
    R.row("G5 the daemon's connection closes: the session lives on and names the next key", t.alive() and typed == ["b"], repr(typed))
    t.send("\x11", wait=1.0, show="Ctrl-Q")
    t.end()

    say("\n--- G6: leaving the page, and another terminal type")
    t2 = tool_keys(box, "G6")
    c2 = fake.wait_client(10)
    R.row("G6a a second session connects", t2 is not None and c2 is not None and fake.connections == 2, repr((c2, fake.connections)))
    t2.send("\x11", wait=1.5, show="Ctrl-Q (leave tool.keys: screen close)")
    R.row("G6b leaving the page closes the connection (mouse reporting off)", fake.closed_by_client(5), "the daemon's side never saw the end")
    t2.end()
    n_before = fake.connections
    t3 = tool_keys(box, "G6x", term="xterm-256color")
    time.sleep(2.0)
    R.row("G6c control: a session of terminal type xterm does not connect (the console's mouse is for the linux type only)", t3 is not None and fake.connections == n_before, repr((fake.connections, n_before)))
    if t3 is not None:
        t3.send("\x11", wait=1.0, show="Ctrl-Q")
        t3.end()


if __name__ == "__main__":
    sys.exit(main())
