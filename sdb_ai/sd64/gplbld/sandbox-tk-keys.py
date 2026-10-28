#!/usr/bin/env python3
#
# sandbox-tk-keys.py - tool.keys, the toolkit's first app (S.75, TK-1, plan A1): the terminal and keyboard diagnostic, on a pseudo-terminal.  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-tk-keys.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent).  Exit 0 every row passed, 1 a row failed, 2 it
# could not run.  tool.keys is a verb of the product (sdsys/newvoc and sdsys/voc_template), so the sandbox's VOC already has it: nothing is registered here.
#
# START-HISTORY:
# 22 Oct 26 dm  New (S.75, TK-1).
# END-HISTORY
#
# WHAT IS HELD.  The screen is read from the emulator (termscreen.py) after the bytes a terminal of each type sends for a key were typed (the sequences are those of
# gplsrc/terminfo.src for xterm, linux and vt100): the newest line of "Last keys" (row 14) must carry the name the screen library reports; the grid, the counters, the
# raw-bytes mode, the mouse reports (SGR), the theme, a window made smaller (the cursor lock) and larger again, a window that is too small to start in, the end of a piped
# input.  A key a terminal type does not name (the End sequence of xterm sent to a vt100) must NOT be named end.  NOT HELD: a real terminal's bytes (the sequences above are
# the terminfo source's own, which is what SD decodes with, not a measurement of any emulator), UTF-8 line drawing, the bell.
import importlib.util
import os
import re
import resource
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("tkb", os.path.join(HERE, "sandbox-tk-base.py"))
tkb = importlib.util.module_from_spec(spec)
sys.modules["tkb"] = tkb
spec.loader.exec_module(tkb)
say, row, bail, Term, TOOL = tkb.say, tkb.row, tkb.bail, tkb.Term, tkb.TOOL

E = "\x1b"
# the sequences of terminfo.src
XTERM = {"up": E + "OA", "down": E + "OB", "right": E + "OC", "left": E + "OD", "home": E + "[1~", "end": E + "[4~", "pgup": E + "[5~", "pgdn": E + "[6~", "ins": E + "[2~",
         "del": E + "[3~", "btab": E + "[Z", "f1": E + "OP", "f2": E + "OQ", "f3": E + "OR", "f4": E + "OS", "f5": E + "[15~", "f6": E + "[17~", "f7": E + "[18~",
         "f8": E + "[19~", "f9": E + "[20~", "f10": E + "[21~", "f11": E + "[23~", "f12": E + "[24~"}
LINUX = dict(XTERM, up=E + "[A", down=E + "[B", right=E + "[C", left=E + "[D", f1=E + "[[A", f2=E + "[[B", f3=E + "[[C", f4=E + "[[D", f5=E + "[[E")
VT100 = {"up": E + "OA", "down": E + "OB", "right": E + "OC", "left": E + "OD", "home": E + "[H", "f1": E + "OP", "f2": E + "OQ", "f3": E + "OR", "f4": E + "OS", "f5": E + "OT",
         "f6": E + "OU", "f7": E + "OV", "f8": E + "OL", "f9": E + "OW", "f10": E + "OX"}
PLAIN = {"tab": "\t", "enter": "\r", "bs": "\x7f", "esc": E, "ctrl-a": "\x01", "ctrl-g": "\x07", "alt-s": E + "s"}


def newest(t):
    """(count, name, rest) of the newest line of Last keys (row 14, columns 2 to 44), or None."""
    m = re.match(r"\s*(\d+)\s+(\S+)\s?(.*)$", t.line(14)[2:45])
    return (int(m.group(1)), m.group(2), m.group(3).strip()) if m else None


def press(t, seq, idle=0.35):
    t.s.type(seq, idle=idle)


def text(t):
    return "\n".join(t.lines())


def names_row(box, term, table):
    t = Term(box, "tool.keys", term=term)
    if "Last keys" not in text(t):
        say("\n".join(l.rstrip() for l in t.lines() if l.strip())[:900])
        bail("tool.keys never drew its screen under %s, so no row below can be believed" % term)
    bad = []
    for name, seq in table.items():
        before = newest(t)
        press(t, seq)
        after = newest(t)
        if not after or after[1] != name or (before and after[0] != before[0] + 1) or (not before and after[0] != 1):
            bad.append("%s -> %r (was %r)" % (name, after, before))
    row("%s: the %d keys of its terminal type (arrows, home, end, paging, insert, delete, back-tab and the function keys it names) are each named as expected, one line added for each" % (term, len(table)),
        not bad, "; ".join(bad)[:700])
    t.end()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-tk-keys.py <dir> [--build]")
    box = os.path.abspath(args[0])
    say("sandbox-tk-keys: sandbox %s" % box)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-tk-keys: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(box, "sys", "bin", "sd")):
        bail("%s holds no built sandbox" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)
    try:
        say("\n--- the first screen (xterm, 140 by 43)")
        t = Term(box, "tool.keys")
        L = text(t)
        if "Last keys" not in L:
            say("\n".join(l.rstrip() for l in t.lines() if l.strip())[:900])
            bail("tool.keys never drew its screen, so no row below can be believed")
        row("the screen has its seven boxes: Terminal, Last keys, Keys seen, Mouse, Box drawing, Help, Styles", all(s in L for s in ("Terminal", "Last keys", "Keys seen", "Mouse", "Box drawing", "Help", "Styles")), L[:300])
        row("the function-key row (row 42) names exactly Ctrl-L, Ctrl-R, Ctrl-T and Ctrl-Q: '^L clear  ^R raw/names  ^T theme  ^Q quit'", t.line(42) == "^L clear  ^R raw/names  ^T theme  ^Q quit", repr(t.line(42)))
        row("the status line says [Keys] and 'press any key'; row 0 ends with the app's name and the audience (the user, not 'administrator')",
            t.line(40).startswith("[Keys]") and "press any key" in t.line(40) and "tool.keys" in t.line(0) and "administrator" not in t.line(0), repr((t.line(40), t.line(0)[-50:])))
        for want in ("TERM (SD)   xterm", "TERM (env)  xterm", "Window      140 x 43  (layout 140 x 43)", "Borders     + - | (not UTF-8)", "Colour      yes", "Theme       mono",
                     "Reading     names ($sl_key)", "Keys seen   0 of 52, 0 pressed", "Mouse       0 events"):
            row("Terminal box: %r" % want, want in L, "")
        row("the grid starts unticked ('[ ] f1', '[ ] ctrl-g', '[ ] mouse') and Last keys is empty", "[ ] f1" in L and "[ ] ctrl-g" in L and "[ ] mouse" in L and newest(t) is None, repr(newest(t)))
        row("the 52 cells of the grid are all there (13 rows of 4 columns): '[ ] up' first, '[ ] mouse' last", L.count("[ ] ") == 52 and "[ ] up" in L, str(L.count("[ ] ")))
        sc = t.s.screen
        sty = {}
        for nm in ("normal", "reverse", "underline", "bold"):
            for r_, l_ in enumerate(t.lines()):
                c_ = l_.find(nm.ljust(12) + " sample text")
                if c_ >= 0:
                    sty[nm] = sc.style(r_, c_ + 14)
        say("    [measured] mono styles: %r" % sty)
        row("the Styles box draws the sixteen styles each in itself: sixteen sample lines, and 'reverse' differs from 'normal' (mono: reverse video)", len(re.findall(r"sample text 0123456789", L)) == 16 and sty.get("reverse") != sty.get("normal"), repr(sty))
        row("the Box drawing box shows the plain border and says so: 'The borders are + - | (not UTF-8).'", "The borders are + - | (not UTF-8)." in L, "")
        t.end()

        say("\n--- the keys of three terminal types, by name")
        names_row(box, "xterm", dict(XTERM, **PLAIN))
        names_row(box, "linux", LINUX)
        names_row(box, "vt100", VT100)

        say("\n--- a character, the grid, the counters")
        t = Term(box, "tool.keys")
        press(t, "a")
        n1 = newest(t)
        row("the character a: named a, with its code: 'a  code 97'; count 1", n1 == (1, "a", "code 97"), repr(n1))
        press(t, XTERM["f1"])
        press(t, XTERM["f2"])
        press(t, E + "s")
        n4 = newest(t)
        row("an Alt-letter (Esc s) is named alt-s, with what it was: 'alt-s  Esc then s'; count 4", n4 == (4, "alt-s", "Esc then s"), repr(n4))
        press(t, E + "S")
        row("Alt+Shift+S is the same key: named alt-s (lower case); count 5", newest(t) == (5, "alt-s", "Esc then s"), repr(newest(t)))
        L = text(t)
        row("the grid ticks what was pressed and nothing else: [x] f1, [x] f2, [x] alt-x, [x] char; still [ ] f3 and [ ] mouse",
            all(s in L for s in ("[x] f1", "[x] f2", "[x] alt-x", "[x] char", "[ ] f3", "[ ] mouse")), "")
        row("the Terminal box counts them: 'Keys seen   4 of 52, 5 pressed'", "Keys seen   4 of 52, 5 pressed" in L, "")
        row("the status line says the last one: 'key alt-s'", "key alt-s" in t.line(40), repr(t.line(40)))
        sc = t.s.screen
        rf, cf = next(((r_, l_.find("[x] f1")) for r_, l_ in enumerate(t.lines()) if "[x] f1" in l_), (0, 0))
        ru, cu = next(((r_, l_.find("[ ] f3")) for r_, l_ in enumerate(t.lines()) if "[ ] f3" in l_), (0, 0))
        row("a ticked cell is drawn bold and an unticked one is not", sc.style(rf, cf + 5) != sc.style(ru, cu + 5), repr((sc.style(rf, cf + 5), sc.style(ru, cu + 5))))
        press(t, "\x0c")
        L = text(t)
        row("Ctrl-L clears what has been seen: the grid is unticked, Last keys empty, 'Keys seen   0 of 52, 0 pressed', and the status line says 'cleared'",
            "[x] " not in L and newest(t) is None and "Keys seen   0 of 52, 0 pressed" in L and "cleared" in t.line(40), repr(t.line(40)))
        t.end()

        say("\n--- the mouse (SGR reports)")
        t = Term(box, "tool.keys")
        press(t, E + "[<0;20;10M")
        row("a press of the left button at column 20, row 10 (the library counts from 0): named mouse, 'press button 1 at 19,9'", newest(t) == (1, "mouse", "press button 1 at 19,9"), repr(newest(t)))
        press(t, E + "[<0;20;10m")
        press(t, E + "[<32;22;10M")
        press(t, E + "[<64;20;10M")
        press(t, E + "[<65;20;10M")
        press(t, E + "[<65;20;10M")
        L = text(t)
        row("release, drag, wheel up and two wheel downs are counted: 'Press 1  release 1' and 'Drag  1  wheel up 1  down 2'; 'Mouse       6 events'",
            "Press 1  release 1" in L and "Drag  1  wheel up 1  down 2" in L and "Mouse       6 events" in L, "")
        row("the last event is shown in the Mouse box: 'Last   wheel button down at 19,9'", "Last   wheel button down at 19,9" in L, "")
        row("and the grid ticks [x] mouse", "[x] mouse" in L, "")
        t.end()

        say("\n--- raw bytes (Ctrl-R)")
        t = Term(box, "tool.keys")
        press(t, "\x12")
        row("Ctrl-R switches to raw: the pane is [Raw], the Terminal box says 'Reading     raw bytes (KEYIN)'", t.line(40).startswith("[Raw]") and "Reading     raw bytes (KEYIN)" in text(t), repr(t.line(40)))
        press(t, XTERM["f5"])
        n = newest(t)
        row("F5 of xterm in raw mode: the bytes the terminal sent, '1b 5b 31 35 7e', and the characters beside them '.[15~'", n is not None and "1b 5b 31 35 7e" in n[1] + " " + n[2] and ".[15~" in t.line(14), repr(t.line(14)[2:45]))
        press(t, "a")
        row("a in raw mode: '61' and 'a'", "61" in t.line(14)[2:45] and t.line(14)[2:45].rstrip().endswith("a"), repr(t.line(14)[2:45]))
        press(t, E + "s")
        row("Esc s in raw mode: '1b 73' and '.s' (an Alt-letter is two bytes)", "1b 73" in t.line(14)[2:45] and ".s" in t.line(14)[2:45], repr(t.line(14)[2:45]))
        press(t, E + "[<0;20;10M")
        row("a mouse report in raw mode is its bytes, the first eight that fit the line: '1b 5b 3c 30 3b 32 30 3b' and '.[<0;20;'", "1b 5b 3c 30 3b 32 30 3b" in t.line(14)[2:45] and ".[<0;20;" in t.line(14)[2:45], repr(t.line(14)[2:45]))
        row("raw mode does not tick the grid: only the Ctrl-R that switched to it is in it ('Keys seen   1 of 52, 5 pressed')", "Keys seen   1 of 52, 5 pressed" in text(t), "")
        press(t, "\x12")
        row("Ctrl-R again is back to names: [Keys]", t.line(40).startswith("[Keys]") and "Reading     names ($sl_key)" in text(t), repr(t.line(40)))
        press(t, "\x12")
        press(t, "\x11")
        t.s.settle(0.8)
        row("Ctrl-Q in raw mode leaves as well: the screen is gone", "Last keys" not in text(t), "")
        t.end()

        say("\n--- the theme (Ctrl-T) and a terminal with no colour")
        t = Term(box, "tool.keys")
        press(t, "\x14")
        row("Ctrl-T on xterm: the theme is classic (the Terminal box and the keys' message)", "Theme       classic" in text(t), repr(t.line(40)))
        sc = t.s.screen
        rw, cw = next(((r_, l_.find("window       sample")) for r_, l_ in enumerate(t.lines()) if "window       sample" in l_), (0, 0))
        say("    [measured] classic window style: %r" % (sc.style(rw, cw + 14),))
        row("...and the Styles box is drawn in it: the window style has colours now", sc.style(rw, cw + 14)[0] is not None or sc.style(rw, cw + 14)[1] is not None, repr(sc.style(rw, cw + 14)))
        press(t, "\x14")
        press(t, "\x14")
        row("Ctrl-T twice more: blue, then mono again", "Theme       mono" in text(t), "")
        t.end()
        t = Term(box, "tool.keys", term="vt100")
        press(t, "\x14")
        row("Ctrl-T on a vt100 (no colour): the theme stays mono and the status line says why", "Theme       mono" in text(t) and "cannot show colour" in t.line(40) and "Colour      no" in text(t), repr(t.line(40)))
        say("\n--- a key the terminal type does not name")
        before = newest(t)
        press(t, XTERM["end"])
        after = newest(t)
        say("    [measured] vt100, the End sequence of xterm (Esc [ 4 ~): newest line before %r, after %r" % (before, after))
        # 28 Oct 26 (S.88 phase 1): this row said the OPPOSITE ("is NOT named end: the type does not know it").  _keycode now binds the keys of every terminal in both modes before
        # the type's own, so a vt100 session understands an xterm's End; what the type does not name is only what no terminal sends (a function key nobody binds).
        row("the End sequence of xterm sent to a vt100 IS named end (every type accepts the usual keys of the others)", after is not None and after[1] == "end", repr(after))
        press(t, "\x12")
        press(t, XTERM["end"])
        row("...and raw mode shows the bytes it sent, '1b 5b 34 7e', which is how to find out", "1b 5b 34 7e" in t.line(14)[2:45], repr(t.line(14)[2:45]))
        t.end()

        say("\n--- Ctrl-Q, and a window that is too small")
        t = Term(box, "tool.keys")
        press(t, "\x11")
        t.s.settle(0.8)
        row("Ctrl-Q leaves and gives the prompt back: the screen is gone and SD answers a command", "Last keys" not in text(t), "")
        t.s.type("WHO\r", idle=0.8)
        row("...the session is alive after it", "WHO" in text(t), text(t)[-200:])
        t.end()
        t = Term(box, "tool.keys", cols=100, rows=30)
        row("a window of 100 by 30 is refused with the library's message: 'tool.keys needs a window of at least 140 columns by 43 lines'", "tool.keys needs a window of at least 140 columns by 43 lines" in text(t), text(t)[-300:])
        row("...and nothing was drawn: no boxes", "Last keys" not in text(t), "")
        t.end()

        say("\n--- the window made smaller while it runs, and larger again")
        t = Term(box, "tool.keys")
        press(t, "a")
        t.s.resize(100, 30, idle=1.0)
        row("a window made smaller puts the cursor off the screen: the library's cursor lock says the window is 100 by 30 and tool.keys is laid out for 140 by 43", "is laid out for 140 by 43" in text(t), text(t)[-300:])
        t.s.resize(140, 43, idle=1.2)
        L = text(t)
        row("made larger again, the app is back with everything: the boxes, the function-key row, and the key pressed before (a)", "Last keys" in L and t.line(42) == "^L clear  ^R raw/names  ^T theme  ^Q quit" and newest(t) is not None and newest(t)[1] == "a", repr((t.line(42), newest(t))))
        press(t, "b")
        row("and it takes keys again: b is named b, count 2", newest(t) == (2, "b", "code 98"), repr(newest(t)))
        t.s.resize(100, 30, idle=1.0)
        press(t, "\x11", idle=0.8)
        press(t, "y", idle=0.8)
        row("in the lock Ctrl-Q, y leaves the app (guardquit): the boxes are gone", "Last keys" not in text(t), text(t)[-200:])
        t.end()

        say("\n--- the end of the input ends the app (a pipe; TERM 140,43 typed so that the window is big enough)")
        env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"), TERM="xterm", LC_ALL="C")
        r0 = resource.getrusage(resource.RUSAGE_CHILDREN)
        p = subprocess.Popen([os.path.join(box, "sys", "bin", "sd")], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=os.path.join(box, "user_accounts"), env=env)
        t0 = time.time()
        p.stdin.write(b"\nTERM 140,43\ntool.keys\n")
        p.stdin.flush()
        p.stdin.close()
        ended = False
        while time.time() - t0 < 15:
            if p.poll() is not None:
                ended = True
                break
            time.sleep(0.2)
        took = time.time() - t0
        if not ended:
            os.kill(p.pid, 1)
            time.sleep(1)
            if p.poll() is None:
                p.kill()
        p.wait()
        r1 = resource.getrusage(resource.RUSAGE_CHILDREN)
        cpu = (r1.ru_utime - r0.ru_utime) + (r1.ru_stime - r0.ru_stime)
        say("    [measured] ended: %s after %.1f s, the child's CPU %.2f s" % (ended, took, cpu))
        row("a piped session whose input ENDS ends the app within 15 s", ended, "%.1f s" % took)
        row("...and did not spin: under 3 s of CPU", ended and cpu < 3.0, "%.2f s" % cpu)
    finally:
        subprocess.run([sys.executable, TOOL, box, "stop"], capture_output=True, text=True, errors="replace", timeout=120)
    say("\nsandbox-tk-keys: %d passed, %d failed, %d skipped" % (tkb.passed, tkb.failed, tkb.skipped))
    sys.exit(1 if tkb.failed else 0)


if __name__ == "__main__":
    main()
