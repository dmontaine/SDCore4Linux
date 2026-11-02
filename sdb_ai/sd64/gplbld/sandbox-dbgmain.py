#!/usr/bin/env python3
#
# sandbox-dbgmain.py - the debugger's full-screen display on a terminal with NO alternate screen (S.98 H3), driven on a PSEUDO-TERMINAL on a private SD.  No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-dbgmain.py <dir> [--build] [--mutant=NAME]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 every row passed, 1 a row
# failed, 2 it could not run.  With --mutant=NAME one change is made to the SANDBOX'S OWN COPY of `debug` and exit 0 means the rows that had to fail failed and no others.
#
# THE INSTRUMENT.  The screen is read from the terminal emulator (termscreen.py) fed with what SD wrote; the terminal type is typed at the sign-on question, as TERM can only be set
# there.  Everything is driven by typed commands (r, v, stop) so that it is the same on every terminal type: a key needs a terminfo entry that has it.  The emulator counts the
# alternate screen (alt_entered), and since 2 Nov 26 the console's clear (CSI H CSI J) as a clear.  It models no autowrap and no scrollback: the last-cell behaviour and the console's
# own clear are for the VM (witness).
#
#   M0   TERM xterm (control, the unchanged path): the alternate screen is entered, and after r the program's own text is back
#   M1   TERM linux at 140 by 43: the frame (source with its numbers, Autos, command line, key row), the alternate screen never entered and no ?1047 / ?1049 / ?47 in the bytes
#   M2   vt100, vt220, ansi: the same, one row each
#   M3   dumb and unknown: line mode (no frame)
#   M4   TERM linux at 100 by 30 (message 11602) : line mode
#   M5   a program with no library screen: ZZBEFORE is gone while the debugger is up (the stated loss), after r the screen holds ZZAFTER and no debugger text, and the cursor is shown
#   M6   a program that owns the library's screen: ZZFORM and ZZMORE are drawn again at their cells after r, and the debugger is gone
#   M7   stop: the STOP message on a cleared screen, no debugger text left
#   M8   v / F4: not owned, message 11597 and the frame stays; owned, the program's screen until a key, then the frame again
#   M9   LINE.MODE in $debug.options on linux: line mode; without it the full screen (the control is M1)
import importlib.util
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ptydrive import PtySession  # noqa: E402


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


dg = _load("sandbox_dbgui_for_dbgmain", "sandbox-dbgui.py")
say, bail, srcrow, CMD, KEYS, KEYTEXT = dg.say, dg.bail, dg.srcrow, dg.CMD, dg.KEYS, dg.KEYTEXT
TOOL = dg.TOOL
RET = "\r"
RUN = "%05d" % (os.getpid() % 100000)
PLAIN, SCR = "zzdm%sa" % RUN, "zzdm%sb" % RUN
FAILED_IDS = []

# the words the program PRINTs are built with a colon, so that the debugger's own source pane (which shows the source) never holds them: finding ZZBEFORE on the screen means the program's output
SOURCE_PLAIN = """   crt 'ZZBE':'FORE'
   x = 1
   debug
   crt 'ZZAF':'TER'
end
"""

SOURCE_SCR = """   screen open clear else crt 'NOSCREEN' ; stop
   screen text 'ZZFO':'RM' at 10,5
   debug
   screen text 'ZZMO':'RE' at 10,7
   screen key returning k
end
"""

MUTANTS = {
    # name: (old text of the sandbox's debug, new text, the row ids that must fail and no others)
    "no-repaint": ("      call $sl_repaint(ps)\n      call $sl_scr('put', ps)\n   end else", "      call $sl_scr('put', ps)\n   end else", ["M6"]),
    "no-clear-at-exit": ("      display @(-31) : sq : @(-1) :\n   end\n   return", "      display @(-31) : sq :\n   end\n   return", ["M5", "M7"]),
    # take.main's clear is not a mutant: paint.layout writes every cell of the window, so a screen not cleared looks the same (found 2 Nov 26, the first version of this mutant survived)
    "no-main-on": ("take.main:\n   main.on = @true\n", "take.main:\n   null\n", ["M5", "M6", "M7"]),
}


def row(rid, name, ok, detail=""):
    dg.row("%s %s" % (rid, name), ok, detail)
    if not ok:
        FAILED_IDS.append(rid)


class Term:
    def __init__(self, box, cmd, term, cols=140, rows=43):
        env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"), TERM=term)
        self.s = PtySession([os.path.join(box, "sys", "bin", "sd")], os.path.join(box, "user_accounts"), env, cols, rows)
        self.s.settle(1.5)
        self.s.type("TERM %s\r" % term, idle=0.8)
        self.s.type("TERM %d,%d\r" % (cols, rows), idle=0.8)
        self.s.type(cmd + "\r", idle=2.5)

    def type(self, text, idle=1.2):
        self.s.type(text, idle=idle)
        return self.lines()

    def lines(self):
        return self.s.screen.lines()

    def text(self):
        return "\n".join(l for l in self.lines() if l.strip())

    def alt_entered(self):
        return getattr(self.s.screen, "alt_entered", 0)

    def alt_bytes(self):
        return [m for m in (b"[?1049", b"[?1047", b"[?47h") if m in self.s.raw]

    def end(self):
        self.s.type("\rOFF\r", idle=0.5)
        self.s.finish()


def frame_ok(L):
    return (len(L) > KEYS and srcrow(L, 4) is not None and L[CMD].startswith(">") and KEYTEXT in L[KEYS]
            and any("Autos" in l for l in L[1:4]))


def sess(box, *cmds):
    return dg.sess(box, *cmds)


def put(box, name, body):
    with open(os.path.join(box, "sys", "bp", name), "w") as fh:
        fh.write(body)


def mutate(box, name):
    old, new, _kills = MUTANTS[name]
    path = os.path.join(box, "sys", "gpl.bp", "debug")
    src = open(path, encoding="utf-8", errors="replace").read()
    if src.count(old) != 1:
        bail("mutant %s: the text to change is found %d times, not once" % (name, src.count(old)))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(src.replace(old, new))
    # a program of gpl.bp is compiled by an INTERNAL administrator session (SDTEST_ADMIN), as the other suites' mutants are
    env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"), SDTEST_ADMIN="1")
    env.pop("SSH_CONNECTION", None)
    env.pop("SSH_TTY", None)
    say("    > [admin] [internal] in sys: BASIC gpl.bp debug")
    p = subprocess.run([os.path.join(box, "sys", "bin", "sd"), "-internal"], input="\nTERM 200,9999\nBASIC gpl.bp debug\nOFF\n", cwd=os.path.join(box, "sys"), env=env,
                       capture_output=True, text=True, errors="replace", timeout=300)
    out = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", p.stdout + p.stderr)
    if "Compiled 1 program(s) with no errors" not in out:
        bail("the mutant debugger did not compile:\n" + out[-600:])


def section_frames(box):
    say("\n--- M0: the control, xterm (alternate screen)")
    t = Term(box, "RUN bp %s" % PLAIN, "xterm")
    L = t.lines()
    row("M0a", "the frame is up and the alternate screen was entered", frame_ok(L) and t.alt_entered() >= 1, "\n".join(L[:6]) + repr(t.alt_entered()))
    L = t.type("r" + RET, idle=1.5)
    T = t.text()
    row("M0b", "after r the program's own text is back: ZZBEFORE (kept by the terminal) and ZZAFTER, and no debugger text", "ZZBEFORE" in T and "ZZAFTER" in T and "Autos" not in T, T[-300:])
    t.end()

    say("\n--- M1/M2: terminals with no alternate screen get the frame")
    for rid, term in (("M1", "linux"), ("M2a", "vt100"), ("M2b", "vt220"), ("M2c", "ansi")):
        t = Term(box, "RUN bp %s" % PLAIN, term)
        L = t.lines()
        row(rid, "TERM %s at 140 by 43: the frame is drawn, the alternate screen never entered (%s), and no ?1047 / ?1049 / ?47 was sent" % (term, t.alt_entered()),
            frame_ok(L) and t.alt_entered() == 0 and not t.alt_bytes(), "\n".join(L[:6]) + repr((t.alt_entered(), t.alt_bytes())))
        t.end()

    say("\n--- M3/M4: line mode where it has to stay")
    for rid, term, cols, rows in (("M3a", "dumb", 140, 43), ("M3b", "unknown", 140, 43), ("M4", "linux", 100, 30)):
        t = Term(box, "RUN bp %s" % PLAIN, term, cols, rows)
        L = t.lines()
        T = t.text()
        why = " and says it uses line mode (11602)" if rid == "M4" else ""
        row(rid, "TERM %s at %d by %d: line mode, no frame%s" % (term, cols, rows, why),
            not frame_ok(L) and "Autos" not in T and re.search(r"(?m)^4: ", T) is not None and (rid != "M4" or "using line mode" in T.replace("\n", " ") or "line mode" in T), T[-400:])
        t.end()


def section_screens(box):
    say("\n--- M5: a program with no library screen")
    t = Term(box, "RUN bp %s" % PLAIN, "linux")
    L = t.lines()
    row("M5a", "the debugger is up and ZZBEFORE is gone (the stated loss: the terminal cannot be asked what it showed)", frame_ok(L) and "ZZBEFORE" not in t.text(), t.text()[:300])
    L = t.type("r" + RET, idle=1.5)
    T = t.text()
    first = next((l for l in L if l.strip()), "")
    row("M5", "after r: ZZAFTER is the first line, nothing of the debugger is left, and the cursor is shown",
        first.strip() == "ZZAFTER" and "Autos" not in T and "[Command]" not in T and not any(l.startswith(">") and "ZZ" not in l and len(l.strip()) > 1 for l in L[1:])
        and getattr(t.s.screen, "cursor_visible", True) is True, repr((first, t.s.screen.cursor_visible if hasattr(t.s.screen, "cursor_visible") else None)) + "\n" + T[-300:])
    t.end()

    say("\n--- M6: a program that owns the library's screen")
    t = Term(box, "RUN bp %s" % SCR, "linux")
    L = t.lines()
    row("M6a", "the debugger is up over the program's screen", frame_ok(L) or srcrow(L, 4) is not None, t.text()[:300])
    L = t.type("r" + RET, idle=2.0)
    T = t.text()
    row("M6", "after r: ZZFORM at its cell (10,5), ZZMORE at (10,7), and nothing of the debugger", len(L) > 7 and L[5][10:16] == "ZZFORM" and L[7][10:16] == "ZZMORE" and "Autos" not in T and "[Command]" not in T,
        repr((L[5][:30], L[7][:30])) + "\n" + T[-300:])
    t.end()

    say("\n--- M7: stop")
    t = Term(box, "RUN bp %s" % PLAIN, "linux")
    L = t.type("stop" + RET, idle=1.5)
    T = t.text()
    row("M7", "stop: the STOP message is on a cleared screen and nothing of the debugger is left", "STOP : Debugging terminated" in T and "Autos" not in T and "[Command]" not in T, T[-400:])
    t.end()


def section_view(box):
    say("\n--- M8: v (F4)")
    t = Term(box, "RUN bp %s" % PLAIN, "linux")
    L = t.type("v" + RET, idle=1.2)
    T = t.text().replace("\n", " ")
    row("M8a", "not owned: the message says there is no second screen, and the frame is still there", "no second screen" in T and frame_ok(L), T[-300:])
    t.end()
    t = Term(box, "RUN bp %s" % SCR, "linux")
    L = t.type("v" + RET, idle=1.5)
    T = t.text()
    row("M8b", "owned: the program's screen is shown (ZZFORM, no debugger text) until a key", len(L) > 5 and L[5][10:16] == "ZZFORM" and "Autos" not in T, T[-300:])
    L = t.type(" ", idle=1.5)
    row("M8c", "...and a key brings the frame back", frame_ok(L) or srcrow(L, 4) is not None, t.text()[:300])
    t.end()


def section_option(box):
    say("\n--- M9: LINE.MODE")
    put(box, "zzdmlm", "   open 'voc' to v else crt 'ZZLM no voc' ; stop\n   write 'LINE.MODE' on v, '$debug.options'\n   crt 'ZZLM set'\nend\n")
    out = sess(box, "BASIC bp zzdmlm", "RUN bp zzdmlm")
    if "ZZLM set" not in out:
        bail("could not write $debug.options:\n" + out[-400:])
    try:
        t = Term(box, "RUN bp %s" % PLAIN, "linux")
        L = t.lines()
        T = t.text()
        row("M9", "with LINE.MODE in $debug.options the terminal that has the full screen (M1) gets line mode", not frame_ok(L) and "Autos" not in T and re.search(r"(?m)^4: ", T) is not None, T[-400:])
        t.end()
    finally:
        put(box, "zzdmlm", "   open 'voc' to v else stop\n   delete v, '$debug.options'\n   crt 'ZZLM gone'\nend\n")
        out = sess(box, "BASIC bp zzdmlm", "RUN bp zzdmlm")
        if "ZZLM gone" not in out:
            say("WARNING: $debug.options was not removed from the sandbox's VOC")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    mutant = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mutant=")), None)
    if len(args) != 1 or (mutant is not None and mutant not in MUTANTS):
        bail("usage: sandbox-dbgmain.py <dir> [--build] [--mutant=%s]" % "|".join(MUTANTS))
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-dbgmain: sandbox %s" % box)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-dbgmain: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)
    try:
        put(box, PLAIN, SOURCE_PLAIN)
        put(box, SCR, SOURCE_SCR)
        out = sess(box, "BASIC bp %s DEBUGGING" % PLAIN, "BASIC bp %s DEBUGGING" % SCR)
        dg.row("setup: both programs compiled in debug mode", out.count("with no errors") == 2, out[-300:])
        if mutant is not None:
            mutate(box, mutant)
            say("sandbox-dbgmain: MUTANT %s: the rows that must fail, and nothing else: %s" % (mutant, ", ".join(MUTANTS[mutant][2])))
            section_screens(box)
        else:
            section_frames(box)
            section_screens(box)
            section_view(box)
            section_option(box)
    finally:
        for d in ("bp", "bp.out"):
            for base in (PLAIN, SCR):
                for nm in (base, base + "w"):
                    pth = os.path.join(sysd, d, nm)
                    if os.path.exists(pth):
                        os.remove(pth)
        subprocess.run([sys.executable, TOOL, box, "stop"], capture_output=True, text=True, errors="replace", timeout=120)
    say("\nsandbox-dbgmain: %d passed, %d failed" % (dg.passed, dg.failed))
    if dg.passed + dg.failed == 0:
        bail("no row ran - a broken test, not a pass")
    if mutant is not None:
        want = sorted(set(MUTANTS[mutant][2]))
        got = sorted({re.match(r"M\d", i).group(0) for i in FAILED_IDS})
        ok = want == got
        say("sandbox-dbgmain: MUTANT %s: the rows that failed are %s; they had to be exactly %s -> %s" % (mutant, got, want, "KILLED BY ITS OWN ROWS" if ok else "NOT AS EXPECTED"))
        return 0 if ok else 1
    return 1 if dg.failed else 0


if __name__ == "__main__":
    sys.exit(main())
