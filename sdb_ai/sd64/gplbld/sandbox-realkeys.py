#!/usr/bin/env python3
#
# sandbox-realkeys.py - the keys a REAL terminal sends (S.88 phase 0 and 1: the input layer).  No install, no sudo.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-realkeys.py <dir> [--build] [--strict]
#
# <dir> is a sandbox made by sandbox-fromtree.py (with --build it is built first from THIS tree; it must be empty or absent; keep the path SHORT).  Exit 0 every
# row passed (or is pending a later phase, see tuirows.py), 1 a row failed, 2 it could not run.  --strict counts the pending rows as failed: the red run.
#
# WHY IT EXISTS.  Every suite before it sent the bytes SD's own terminfo entry expects (ESC O A for Up, ESC O P for F1), after typing TERM xterm.  A real terminal
# (xterm, GNOME Terminal, Konsole) in its default normal mode sends ESC [ A and ESC O P, and every account's LOGIN paragraph set TERM LINUX, so on the owner's own
# GNOME Terminal (28 Oct 26) F1 arrived as alt-o then P, F2 as alt-o then Q, F5 as ~, Home as nothing and Ctrl+Right as 5 then C (PROJECT_STATUS S.88; plan K1-K7).
#
# THE INSTRUMENT.  tool.keys, the toolkit's own key tester, names every key the screen library gives a program ($sl_key) and lists the newest first; this suite sends
# the emulator's bytes and reads the NEW entries of that list, so what it judges is what the library reported, not what the screen drew.  Every row prints the bytes
# it sent.  The CONTROLS (a letter, a real mouse click, Up as a linux console sends it) pass on the tree before the fix: they prove the page was reached and the
# list was read, so a key that "names nothing" is a result and not a missing page.  A row that names the phase of the plan that fixes it is pending until it lands.
#
# START-HISTORY:
# 28 Oct 26 dm  New (S.88 phase 0; the rows of phase 1).
# END-HISTORY
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ptydrive import PtySession  # noqa: E402
from tuirows import Rows  # noqa: E402

TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
RUN = "%05d" % (os.getpid() % 100000)
E = "\x1b"
R = Rows("realkeys")


def say(s=""):
    print(s, flush=True)


def bail(msg):
    say("sandbox-realkeys: CANNOT RUN - " + msg)
    sys.exit(2)


# What a real xterm-compatible emulator sends in its default (normal cursor key) mode, and what tool.keys must then name.  The names of the modified keys are the
# library's new ones (phase 1).
PLAIN = [("up", E + "[A"), ("down", E + "[B"), ("right", E + "[C"), ("left", E + "[D"), ("home", E + "[H"), ("end", E + "[F"),
         ("ins", E + "[2~"), ("del", E + "[3~"), ("pgup", E + "[5~"), ("pgdn", E + "[6~"), ("btab", E + "[Z"),
         ("f1", E + "OP"), ("f2", E + "OQ"), ("f3", E + "OR"), ("f4", E + "OS"), ("f5", E + "[15~"), ("f6", E + "[17~"), ("f7", E + "[18~"),
         ("f8", E + "[19~"), ("f9", E + "[20~"), ("f10", E + "[21~"), ("f11", E + "[23~"), ("f12", E + "[24~")]
APPMODE = [("up", E + "OA"), ("down", E + "OB"), ("right", E + "OC"), ("left", E + "OD"), ("home", E + "OH"), ("end", E + "OF"), ("home", E + "[1~"), ("end", E + "[4~")]
MODIFIED = [("ctrl-left", E + "[1;5D"), ("ctrl-right", E + "[1;5C"), ("ctrl-home", E + "[1;5H"), ("ctrl-end", E + "[1;5F"), ("ctrl-pgup", E + "[5;5~"),
            ("ctrl-pgdn", E + "[6;5~"), ("shift-up", E + "[1;2A"), ("shift-down", E + "[1;2B"), ("alt-left", E + "[1;3D"), ("ctrl-del", E + "[3;5~")]
# bytes that are not keys: dropped, never named, never typed
JUNK = [("a lone high byte 0x80 (was f1)", "\x80"), ("0xC8 (was the mouse key)", "\xc8"), ("0xCB (was up)", "\xcb"),
        ("a UTF-8 bullet E2 80 A2", "\xe2\x80\xa2"), ("an unknown CSI sequence ESC [ 9 9 ; 9 z", E + "[99;9z"), ("an unknown SS3 sequence ESC O z", E + "Oz")]


def sess(box, *cmds):
    """A plain scripted session through a pipe, for setting up and reading back (no keys)."""
    p = subprocess.run([sys.executable, TOOL, box, "sess", os.path.join(box, "user_accounts")] + list(cmds),
                       capture_output=True, text=True, errors="replace", timeout=600,
                       env=dict(os.environ))
    return ANSI.sub("", p.stdout + p.stderr).split(":TERM 200,9999", 1)[-1]


class Term:
    """One sign-on on a pseudo-terminal at 140 by 43, as a GNOME Terminal user has it: TERM=xterm-256color in the environment, a UTF-8 locale."""

    def __init__(self, box, label, type_lines=(), argv_extra=(), term="xterm-256color"):
        self.label = label
        env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"), TERM=term, LC_ALL="en_US.UTF-8", LANG="en_US.UTF-8")
        for k in ("SSH_CONNECTION", "SSH_TTY", "TMUX", "SDTEST_ADMIN"):
            env.pop(k, None)
        self.argv = [os.path.join(box, "sys", "bin", "sd")] + list(argv_extra)
        say("  [%s] START argv=%r cwd=%s/user_accounts TERM(env)=%s LC_ALL=%s window=140x43 SDBOX_KEYSET=%s typed=%r" % (
            label, self.argv, box, term, env["LC_ALL"], env.get("SDBOX_KEYSET"), list(type_lines)))
        self.s = PtySession(self.argv, os.path.join(box, "user_accounts"), env, 140, 43, utf8=True)       # a UTF-8 terminal: the box borders are one cell, not three
        self.wait(1.5)
        for t in type_lines:
            self.s.type(t + "\r", idle=0.5)
        self.wait(0.5)

    def wait(self, secs):
        end = time.time() + secs                    # PtySession._pump returns at the first byte: a real deadline loop
        while time.time() < end and not self.s.exited:
            self.s._pump(min(0.2, max(0.01, end - time.time())))

    def send(self, data, wait=0.8, show=""):
        say("  [%s] SEND %s %r" % (self.label, show, data))
        mark = len(self.s.raw)
        if isinstance(data, str):
            data = data.encode("latin-1")
        try:
            os.write(self.s.fd, data)
        except OSError:
            self.s.exited = True
        self.wait(wait)
        return self.s.raw[mark:]

    def lines(self):
        return self.s.screen.lines()

    def alive(self):
        self.s._pump(0.2)
        return not self.s.exited

    def sd_type(self):
        for l in self.lines():
            m = re.search(r"TERM \(SD\)\s+(\S+)", l)
            if m:
                return m.group(1)
        return None

    def keys_box(self):
        """The entries of tool.keys's Last keys box, newest first: [(number, name, rest)]."""
        L = self.lines()
        top = next((i for i, l in enumerate(L) if "Last keys" in l), None)
        if top is None:
            return None
        out = []
        for l in L[top + 1:]:
            m = re.match(r"^\s*(\d+)\s+(\S+)\s*(.*)$", l[2:46].rstrip())
            if not m:
                break
            out.append((int(m.group(1)), m.group(2), m.group(3).strip()))
        return out

    def newest_no(self):
        b = self.keys_box()
        return (b[0][0] if b else 0) if b is not None else None

    def press(self, data, show="", wait=0.8):
        """Send bytes and return the names tool.keys listed for them, oldest first."""
        before = self.newest_no()
        raw = self.send(data, wait=wait, show=show)
        box = self.keys_box()
        if box is None or before is None:
            return None, raw
        return [e[1] for e in reversed(box) if e[0] > before], raw

    def end(self):
        st = self.s.finish()
        say("  [%s] END status=%r" % (self.label, st))


def keys_session(box, label, type_lines=()):
    t = Term(box, label, type_lines)
    t.s.type("tool.keys\r", idle=1.5)
    t.wait(1.5)
    if t.keys_box() is None:
        say("  [%s] NULL CASE: tool.keys did not draw:\n%s" % (label, "\n".join(l.rstrip() for l in t.lines() if l.strip())[:900]))
        t.end()
        return None
    return t


def run_keys(box, label, type_lines, expect_type):
    say("\n--- %s --------------------------------------------------------------------------------------------" % label)
    t = keys_session(box, label, type_lines)
    if t is None:
        R.row("%s: tool.keys is reached (the instrument)" % label, False, "the page did not draw")
        return
    R.row("%s: tool.keys is reached and its Last keys box is read (control)" % label, True)
    if expect_type:
        R.row("%s: SD's terminal type is %s" % (label, expect_type), t.sd_type() == expect_type, "TERM (SD) = %r" % t.sd_type(), phase=1)
    # controls: a letter, and Up as the type's own entry sends it, are named today
    names, _ = t.press("a", "a")
    R.row("%s: control: the letter a is named" % label, names is not None and len(names) == 1 and names[0] == "a", repr(names))
    for want, seq in PLAIN:
        names, raw = t.press(seq, want)
        ok = names == [want]
        R.row("%s: %s sent as %r is the one key %s" % (label, want, seq, want), ok, "named %r" % (names,), phase=1)
    for want, seq in APPMODE:
        names, raw = t.press(seq, want + " (application / console form)")
        R.row("%s: %s sent as %r is the one key %s" % (label, want, seq, want), names == [want], "named %r" % (names,), phase=1)
    for want, seq in MODIFIED:
        names, raw = t.press(seq, want)
        R.row("%s: %s sent as %r is the one key %s, nothing is typed" % (label, want, seq, want), names == [want], "named %r" % (names,), phase=1)
    t.press("\x15", "(Ctrl-U: clear)", wait=0.3)
    for what, seq in JUNK:
        names, raw = t.press(seq, what)
        R.row("%s: %s names no key and types nothing" % (label, what), names == [], "named %r" % (names,), phase=1)
    t.send("\x11", wait=1.0, show="Ctrl-Q")
    t.end()


def run_mouse_paste(box):
    say("\n--- mouse reports and paste -------------------------------------------------------------------------")
    t = keys_session(box, "M")
    if t is None:
        R.row("M: tool.keys is reached (the instrument)", False, "the page did not draw")
        return
    start = len(t.s.raw)
    names, _ = t.press(E + "[<0;20;20M" + E + "[<0;20;20m", "a real click (control)")
    R.row("M: control: a real click is the key mouse", names is not None and "mouse" in names, repr(names))
    for what, seq in [("a partial report ESC [ < 0 ; 5 and nothing more", E + "[<0;5"), ("a malformed report ESC [ < z z ; q ; w M", E + "[<zz;q;wM")]:
        t.send(seq, wait=1.5, show=what)
        R.row("M: %s: tool.keys is still running (never read as the end of the input)" % what, t.alive() and t.keys_box() is not None, "alive=%r" % t.alive(), phase=1)
        names, _ = t.press("a", "a (the page still takes keys)")
        R.row("M: after %s a typed a is named" % what, names is not None and "a" in names, repr(names), phase=1)
    names, _ = t.press(E + "[<66;5;5M", "a horizontal wheel (66)")
    R.row("M: a horizontal wheel is not read as the wheel down", names is None or "mouse" not in names, repr(names), phase=1)
    raw_on = t.s.raw[start - 1:] if start else t.s.raw
    R.row("M: bracketed paste is switched on while the page runs (ESC [ ? 2004 h was written)", (E + "[?2004h").encode() in t.s.raw, "not found", phase=1)
    names, _ = t.press(E + "[200~hi" + E + "OP" + "\x80" + E + "[201~", "a paste of 'hi', an F1 sequence and a high byte")
    R.row("M: a paste is one key, paste, and its contents run nothing (no f1 among the keys)", names is not None and "paste" in names and "f1" not in names, repr(names), phase=1)
    mark = len(t.s.raw)
    t.send("\x11", wait=1.2, show="Ctrl-Q")
    R.row("M: bracketed paste is switched off again when the page ends (ESC [ ? 2004 l)", (E + "[?2004l").encode() in t.s.raw[mark - 1:], "not found", phase=1)
    t.end()


def run_ide(box, rec):
    say("\n--- the IDE, typed to as a GNOME Terminal user types ----------------------------------------------")
    t = Term(box, "I")
    t.s.type("IDE bp %s\r" % rec, idle=2.0)
    t.wait(2.0)
    L = t.lines()
    ok = any(("bp %s" % rec) in l for l in L[-3:])
    R.row("I: the IDE opened bp %s (the instrument)" % rec, ok, "\n".join(l.rstrip() for l in L if l.strip())[:500])
    if not ok:
        t.end()
        return
    t.send("hello", wait=1.5, show="hello")
    R.row("I: control: typed letters reach the record (status line has the star)", any(" *" in l for l in t.lines()[-3:]), "\n".join(t.lines()[-3:]))
    t.send(E + "OQ", wait=2.0, show="F2 as GNOME Terminal sends it")
    disk = sess(box, "CT bp %s" % rec)
    R.row("I: F2 saves the record (it did not type a Q)", "helloQ" not in "".join(t.lines()) and "hello" in disk and "Q" not in disk.replace("Saved", ""), disk[-200:], phase=1)
    t.send(E + "[H", wait=1.2, show="Home as GNOME Terminal sends it")
    t.send("X", wait=1.5, show="X")
    L = "\n".join(t.lines())
    R.row("I: Home moves to the start of the line (the next letter lands before hello)", "Xhello" in L, L[:400], phase=1)
    t.send("\x1b[1;5C", wait=1.2, show="Ctrl+Right")
    t.send("Z", wait=1.5, show="Z")
    L = "\n".join(t.lines())
    R.row("I: Ctrl+Right is a word move and types no 5 or C", "5C" not in L, L[:400], phase=1)
    t.send("\x11", wait=1.0, show="Ctrl-Q")
    t.send("d", wait=1.0, show="d (Discard)")
    t.end()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-realkeys.py <dir> [--build] [--strict]")
    box = os.path.abspath(args[0])
    say("sandbox-realkeys: sandbox %s   tree %s   strict=%s" % (box, os.path.dirname(HERE), "--strict" in sys.argv))
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=1200)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-realkeys: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(box, "sys", "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    rec = "zzrk" + RUN
    fix = "zzrkfx" + RUN
    with open(os.path.join(box, "sys", "bp", fix), "w") as fh:
        fh.write("   open 'bp' to f else stop 'no bp'\n   write 'line one':@fm:'line two' on f, '%s'\n   crt 'FIXTURE DONE'\nend\n" % rec)
    out = sess(box, "BASIC bp %s" % fix, "RUN bp %s" % fix)
    if "FIXTURE DONE" not in out:
        bail("the fixture was not made:\n" + out[-600:])

    # the sign-on a real user takes: TERM=xterm-256color in the environment and nothing typed; then both types typed by hand
    run_keys(box, "A delivered sign-on", (), "xterm")
    run_keys(box, "B after TERM linux", ("TERM linux",), "linux")
    run_keys(box, "C after TERM xterm", ("TERM xterm",), "xterm")
    run_mouse_paste(box)
    run_ide(box, rec)
    return R.finish()


if __name__ == "__main__":
    sys.exit(main())
