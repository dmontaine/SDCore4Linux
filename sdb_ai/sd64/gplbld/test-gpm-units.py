#!/usr/bin/env python3
"""test-gpm-units.py - S.94: the Linux console's mouse through gpm (gplsrc/gpmmouse.c) and the console's own key forms (_keycode), read off the source as text.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-gpm-units.py
  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-gpm-units.py --selftest

No sudo, no install, no sd.  Exit 0 every check passed, 1 a check failed, 2 it could not run.

START-HISTORY:
31 Oct 26 dm  New (S.94).
END-HISTORY

WHAT IT HOLDS.  The shipped build talks to /dev/gpmctl and only from a text console (character device 4:1 to 4:63), and reads no environment variable for either; the connect record asks for
every event and leaves MOVE and HARD to gpm; a record is taken only when whole (MSG_PEEK first) and a daemon that never finishes one is dropped; every report is ESC [ < b ; x ; y M or m, the
coordinates held to 1..9999, a wheel 64 and 65, a drag 32 more than its button, a plain move nothing; the reports go into the input ring whole and only where there is room; the input wait is on
the keyboard and the daemon; `sl_mouse` asks the kernel only for the linux terminal type; kernel key 170 is the same in keys.h and int$keys.h; the sandbox patches that point a test build at
a stand-in daemon exist; and the two console key forms (Shift-F1 to F8 as F13 to F20, Esc Tab as Shift-Tab) are decoded for the linux type only.

IT READS THE SOURCE AS TEXT.  That the reports reach the screen library is sandbox-gpm.py (a stand-in daemon); that a real gpm daemon sends what the layout says is
.claude/vmtools/console-gpmprobe.py and console-mouse.py on a real console.  --selftest requires each mutation to match its text exactly once and to be caught.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SD = os.path.join(HERE, os.pardir)
SRC = os.path.join(SD, "gplsrc")
GPL = os.path.join(SD, "sdsys", "gpl.bp")
FILES = {"gpm": os.path.join(SRC, "gpmmouse.c"), "gpmh": os.path.join(SRC, "gpmmouse.h"), "lio": os.path.join(SRC, "linuxio.c"), "opk": os.path.join(SRC, "op_kernel.c"),
         "keysh": os.path.join(SRC, "keys.h"), "defs": os.path.join(SRC, "sddefs.h"), "ikeys": os.path.join(GPL, "int$keys.h"), "slm": os.path.join(GPL, "sl_mouse"),
         "kc": os.path.join(GPL, "_keycode"), "list": os.path.join(SD, "gpl.src"), "patch": os.path.join(HERE, "sandbox-txnfail.py")}


def strip_c(s):
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    return re.sub(r"//[^\n]*", "", s)


def strip_b(src):
    out = []
    for ln in src.split("\n"):
        if ln.lstrip().startswith("*"):
            continue
        out.append(re.sub(r"\s*;\*.*$", "", ln))
    return "\n".join(out)


def ordered(text, *parts):
    pos = -1
    for p in parts:
        i = text.find(p, pos + 1)
        if i < 0:
            return False
        pos = i
    return True


def squash(s):
    return re.sub(r"\s+", " ", s)


def checks(src):
    rows = []

    def ck(name, ok, detail=""):
        rows.append((name, bool(ok), detail))

    g, lio, opk = strip_c(src["gpm"]), strip_c(src["lio"]), strip_c(src["opk"])
    slm, kc = strip_b(src["slm"]), strip_b(src["kc"])
    ck("G0 NULL CASE: the reader sees the daemon code (over 3 KB), linuxio.c's code (over 12 KB), the key decoder and sl_mouse", len(g) > 3000 and len(lio) > 12000 and len(kc) > 3000 and len(slm) > 300, repr((len(g), len(lio), len(kc), len(slm))))
    kh, ik = src["keysh"], src["ikeys"]
    ck("G1 kernel key 170: K_GPM in keys.h and K$GPM in int$keys.h are the same number, nothing else has it, and op_kernel.c has the case",
       re.search(r"#define K_GPM\s+170\b", kh) is not None and re.search(r"\$define K\$GPM\s+170\b", ik) is not None and len(re.findall(r"#define K_\w+\s+170\b", kh)) == 1
       and len(re.findall(r"\$define K\$\S+\s+170\b", ik)) == 1 and "case K_GPM:" in opk, "")
    ck("G2 the wire layout: a 16-byte Gpm_Connect and a 28-byte Gpm_Event, the fields in gpm.h's order, asserted at compile time",
       "unsigned short eventMask, defaultMask, minMod, maxMod; int pid; int vc;" in squash(g) and "unsigned char buttons, modifiers; unsigned short vc; short dx, dy, x, y; int type; int clicks; int margin; short wdx, wdy;" in squash(g)
       and "sizeof(GPM_CONNECT) == 16" in g and "sizeof(GPM_EVENT) == 28" in g, "")
    ck("G3 the shipped build: the socket is /dev/gpmctl, a session on anything but a text console may not talk to it, and gpmmouse.c reads no environment variable",
       '#define SD_GPM_SOCK "/dev/gpmctl"' in src["defs"] and re.search(r"#define SD_GPM_ANY_TTY\s+0\b", src["defs"]) and "getenv" not in g and g.count("SD_GPM_SOCK") >= 2, "")
    ck("G4 a text console is character device 4:1 to 4:63, tested before any socket is made",
       "major(st.st_rdev) != 4 || minor(st.st_rdev) < 1 || minor(st.st_rdev) > 63" in g and ordered(g, "vt = console_vt();", "if (vt == 0)", "return 0;", "socket(AF_UNIX"), "")
    ck("G5 the connect record: every event wanted, MOVE and HARD left to gpm, no modifier filter, this process and this console",
       "conn.eventMask = 0xFFFF;" in g and "conn.defaultMask = GPM_MOVE | GPM_HARD;" in g and "conn.minMod = 0;" in g and "conn.maxMod = 0xFFFF;" in g and "conn.pid = (int)getpid();" in g and "conn.vc = vt;" in g, "")
    ck("G6 every report is ESC [ < b ; x ; y M or m and nothing else is ever put in the input, with x and y held to 1..9999",
       g.count("snprintf(") == 1 and r'"\033[<%d;%d;%d%c"' in g and "if (x > 9999)" in g and "if (y > 9999)" in g and "if (x < 1)" in g and "if (y < 1)" in g, "")
    ck("G7 a wheel turn is 64 (up) or 65 (down) from a MOVE record with a displacement; a button is 0, 1, 2 for left, middle, right; a drag adds 32; shift 4, meta 8, control 16; a plain move is nothing",
       "(pending.wdy > 0) ? 64 : 65" in g and ordered(g, "if (gpm_button & GPM_B_LEFT)", "return 0;", "GPM_B_MIDDLE", "return 1;", "return 2;") and "sgr_button(bit) + 32 + mods" in g
       and ordered(g, "if (m & GPM_MOD_SHIFT)", "r += 4;", "if (m & GPM_MOD_ALT)", "r += 8;", "if (m & GPM_MOD_CTRL)", "r += 16;") and "a plain move: SD asked for no motion without a button" in src["gpm"], "")
    ck("G8 a record is taken only when whole (MSG_PEEK first, then the consuming read), and a daemon that never finishes one is dropped after two seconds",
       ordered(g, "MSG_PEEK | MSG_DONTWAIT", "if (got < (ssize_t)sizeof(ev))", "partial_since = time(NULL)", "> 2", "gpm_disable()", "partial_since = 0;", "recv(gpm_sock, &ev, sizeof(ev), MSG_DONTWAIT)"), "")
    ck("G9 linuxio.c: the reports go into the ring whole and only where there is room; keyready and do_input take them first; the wait is on the keyboard and the daemon",
       ordered(lio, "Private void gpm_to_ring() {", "room = (ring_out - ring_in - 1 + RING_SIZE) % RING_SIZE;", "if (room < len)", "gpm_report_done();")
       and ordered(lio, "bool keyready() {", "gpm_to_ring();", "if (sdpoll(0, 0) > 0)") and ordered(lio, "Private void do_input() {", "gpm_to_ring();", "again:")
       and "poll_ret = input_poll(" in lio and ordered(lio, "Private int input_poll(int timeout) {", "fds[0].fd = 0;", "fds[1].fd = gpm_fd();", "return poll(fds, nfds, timeout);"), "")
    ck("G10 sl_mouse asks the kernel only for the linux terminal type: 1 when the mouse goes on, 0 when it goes off",
       "if downcase(@term.type) = 'linux' then gpm.on = kernel(K$GPM, 1)" in slm and "if downcase(@term.type) = 'linux' then gpm.on = kernel(K$GPM, 0)" in slm and "$include int$keys.h" in slm, "")
    ck("G11 gpmmouse is in the list of sources, and the sandbox patches that point a test build at a stand-in daemon exist for both definitions",
       re.search(r"(?m)^gpmmouse$", src["list"]) is not None and "#define SD_GPM_SOCK" in src["patch"] and "sdbox-gpm-%d" in src["patch"] and "#define SD_GPM_ANY_TTY 1" in src["patch"], "")
    ck("G12 the console's Shift-Tab (Esc Tab) is the back-tab key, for the linux terminal type and the screen library's read only",
       ordered(kc, "if kc.alt and key.string = char(27) : char(9) and downcase(@term.type) = 'linux' then return value char(K$CTRL.TAB)", "if kc.alt and len(key.string) = 2"), "")
    ck("G13 the console's Shift-F1 to Shift-F8 (F13 to F20: ESC [ 25 ~, 26, 28, 29, 31, 32, 33, 34 ~) are shift-f1 to shift-f8, for the linux terminal type only",
       ordered(kc, "if fin = '~' and md < 2 and base = '' and downcase(@term.type) = 'linux' then", "case p1 = 25 ; sfn = 1", "case p1 = 26 ; sfn = 2", "case p1 = 28 ; sfn = 3", "case p1 = 29 ; sfn = 4",
               "case p1 = 31 ; sfn = 5", "case p1 = 32 ; sfn = 6", "case p1 = 33 ; sfn = 7", "case p1 = 34 ; sfn = 8", "got = char(27) : char(2) : 'shift-f' : sfn"), "")
    return rows


MUTANTS = [
    ("defs", "a shipped build may talk to any terminal", "#define SD_GPM_ANY_TTY 0", "#define SD_GPM_ANY_TTY 1"),
    ("gpm", "the daemon's socket comes from the environment", "  strcpy(sa.sun_path, SD_GPM_SOCK);", "  strcpy(sa.sun_path, getenv(\"SD_GPM_SOCK\") ? getenv(\"SD_GPM_SOCK\") : SD_GPM_SOCK);"),
    ("gpm", "a serial line counts as a console", "minor(st.st_rdev) > 63)\n    return 0;", "minor(st.st_rdev) > 255)\n    return 0;"),
    ("gpm", "no test that this is a console before the socket", "  vt = console_vt();\n  if (vt == 0)\n    return 0;\n", "  vt = console_vt();\n"),
    ("gpm", "gpm is told to leave every event to us and to draw nothing", "conn.defaultMask = GPM_MOVE | GPM_HARD;", "conn.defaultMask = 0;"),
    ("gpm", "the console number is not given", "  conn.vc = vt;", "  conn.vc = 0;"),
    ("gpm", "the wheel directions are swapped", "(pending.wdy > 0) ? 64 : 65", "(pending.wdy > 0) ? 65 : 64"),
    ("gpm", "the column is not held to 9999", "  if (x > 9999)\n    x = 9999;\n", ""),
    ("gpm", "a record is consumed before it is known to be whole", "recv(gpm_sock, &ev, sizeof(ev), MSG_PEEK | MSG_DONTWAIT)", "recv(gpm_sock, &ev, sizeof(ev), MSG_DONTWAIT)"),
    ("gpm", "a daemon that never finishes a record is waited on for ever", "else if (time(NULL) - partial_since > 2)\n        gpm_disable();", "else if (time(NULL) - partial_since > 2)\n        partial_since = 0;"),
    ("gpm", "a drag adds nothing to its button", "sgr_button(bit) + 32 + mods", "sgr_button(bit) + mods"),
    ("lio", "keyready does not take the daemon's reports", "  gpm_to_ring();\n\n  /* Check if there is anything pending on stdin.", "  /* Check if there is anything pending on stdin."),
    ("lio", "the wait is on the keyboard alone", "poll_ret = input_poll((timeout && timeout < 1000) ? timeout : 1000);", "poll_ret = sdpoll(0, (timeout && timeout < 1000) ? timeout : 1000);"),
    ("lio", "a report goes into a ring that has no room for it", "    if (room < len)\n      return;", "    if (0)\n      return;"),
    ("slm", "the mouse goes on for every terminal type", "         if downcase(@term.type) = 'linux' then gpm.on = kernel(K$GPM, 1)", "         gpm.on = kernel(K$GPM, 1)"),
    ("slm", "the connection is never closed", "if downcase(@term.type) = 'linux' then gpm.on = kernel(K$GPM, 0)", "if downcase(@term.type) = 'linux' then gpm.on = kernel(K$GPM, 2)"),
    ("kc", "Esc Tab is the back-tab for every terminal type", "if kc.alt and key.string = char(27) : char(9) and downcase(@term.type) = 'linux' then", "if kc.alt and key.string = char(27) : char(9) then"),
    ("kc", "Shift-F6 is Shift-F5", "case p1 = 32 ; sfn = 6", "case p1 = 32 ; sfn = 5"),
    ("kc", "F13 to F20 are Shift-F1 to Shift-F8 for every terminal type", "if fin = '~' and md < 2 and base = '' and downcase(@term.type) = 'linux' then", "if fin = '~' and md < 2 and base = '' then"),
    ("ikeys", "K$GPM has another number than K_GPM", "$define K$GPM             170", "$define K$GPM             171"),
]


def load():
    src = {}
    for k, p in FILES.items():
        with open(p, encoding="latin-1") as f:
            src[k] = f.read()
    return src


def report(rows):
    bad = 0
    for name, ok, detail in rows:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, ("   <- " + detail) if detail and not ok else ""))
        bad += 0 if ok else 1
    return bad


def selftest():
    src = load()
    if any(not ok for _, ok, _ in checks(src)):
        print("REFUSING - the unmutated source already fails", file=sys.stderr)
        return 2
    holes = 0
    print("--- self-test: each mutation must be CAUGHT and match its text once ---")
    for fk, name, old, new in MUTANTS:
        n = src[fk].count(old)
        if n != 1:
            print("  [FAIL] %s: the text matches %d times in %s, not once" % (name, n, fk))
            holes += 1
            continue
        mut = dict(src)
        mut[fk] = src[fk].replace(old, new)
        caught = [x.split(" ")[0] for x, ok, _ in checks(mut) if not ok]
        print("  [%s] %s%s" % ("pass" if caught else "FAIL", name, ": caught by " + ", ".join(caught[:3]) if caught else ": NOT CAUGHT"))
        holes += 0 if caught else 1
    print("\n%d of %d mutants caught, %d missed" % (len(MUTANTS) - holes, len(MUTANTS), holes))
    return 1 if holes else 0


def main():
    missing = [p for p in FILES.values() if not os.path.isfile(p)]
    if missing:
        print("test-gpm-units: CANNOT RUN - not readable: %s" % missing, file=sys.stderr)
        return 2
    if "--selftest" in sys.argv[1:]:
        return selftest()
    rows = checks(load())
    bad = report(rows)
    print("\nNOT MEASURED HERE: that the reports reach the screen library (sandbox-gpm.py) and what a real gpm daemon sends (console-gpmprobe.py, console-mouse.py on a real console).")
    print("test-gpm-units: %d checks, %d failed" % (len(rows), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
