#!/usr/bin/env python3
#
# sandbox-escdata.py - text that comes from DATA never reaches the terminal as a control character (S.88 phase 2, S1): $sl_put and SCREEN TEXT.  No install, no sudo.  WRITTEN 28 Oct 2026,
# NOT RUN (the owner's testing rule of that day: one complete run after the last phase).
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-escdata.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or absent).  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 28 Oct 26 dm  Written for the control-character scrub of gpl.bp/sl_put (plan 2.1, defect S1).
# 28 Oct 26 dm  The C1 controls (rows C1a-C1h): bytes 128-159 outside UTF-8 mode, C2 80..C2 9F in UTF-8 mode; session_raw takes an environment.
# END-HISTORY
#
# THE DEFECT.  A record, a record id, a lock id, a file name or an answer of the AI is drawn through $sl_put (every widget does, and SCREEN TEXT). An escape sequence in it went to the terminal
# as it was: an OSC string retitled the window, ESC [ 2 J wiped the screen, a bell rang.  Now a control character is shown - the letter 64 above it, in reverse, one cell for one character -
# and never sent.
#
# WHAT RUNS.  A BASIC program (bp zzescdata, compiled and run by an internal session on a pipe) puts text holding escape sequences on a blank screen context with $sl_put and with the SCREEN
# TEXT statement.  The suite reads the RAW BYTES the session wrote:
#   E1  the injected sequences (ESC [ 777 z, ESC [ 778 z, an OSC title, a bell, SO) are NOT in the raw bytes - each is a sequence no terminal entry of SD's writes
#   E2  what is shown instead: with the library's own sequences taken out, the text reads A[[777zB[]0;PWNGC D@?MJE - ESC as [, BEL as G, a tab as a blank, NUL as @, DEL as ?, return as M,
#       line feed as J, everything else as typed
#   E3  one cell for one character: the shadow of the screen holds the text with the SAME LENGTH, no control character in it, and exactly one CHAR(14) (the library's stand-in, kept)
#   E4  the same through the SCREEN TEXT statement
#   E5  CONTROLS: printable ASCII and UTF-8 bytes (195 169) pass unchanged; a line-drawing stand-in is still turned into a line character or +-+ ; a text with no control character in
#       it is written once, as before
#   C1  THE C1 CONTROLS (28 Oct 26, a review of the first version, which scrubbed 0-31 and 127 only; WRITTEN, NOT RUN): the same program run twice, with LC_ALL=C (a terminal that is not in
#       UTF-8 mode: the single bytes 155 (CSI), 128 and 159 must not be written - shown as [ @ _, reverse, same length; 160 and 233 pass) and with LC_ALL=en_US.UTF-8 (only the two-byte
#       forms C2 9B and C2 80 are replaced - a dot and the letter, two cells for two bytes -; a curly quote pair E2 80 9C / E2 80 9D, a lone C2 and a lone byte 155 pass; the shadow agrees)
# RED BEFORE: on the sl_put before this change E1 fails (all five sequences are in the output), E2 and E3 fail; E5 passes (it is the control).  Not measured: no run has been made.

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
# the library's own sequences: CSI ... letter, a character set designation (ESC ( B) and the two-byte ESC = / ESC >
ANSI = re.compile(r"\x1b(?:\[[0-9;?]*[A-Za-z]|[()][A-Za-z0-9]|[=>])")
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
    say("sandbox-escdata: CANNOT RUN - " + msg)
    sys.exit(2)


def session_raw(box, *cmds, **extra):
    """The session's output as BYTES, untouched: the rows are about the bytes that would reach a terminal.  extra: environment variables for the session (the C1 rows set the locale)."""
    say("    > " + " | ".join(cmds) + ("   with " + " ".join("%s=%s" % kv for kv in sorted(extra.items())) if extra else ""))
    env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"))
    if extra:
        for k in ("LC_ALL", "LC_CTYPE", "LANG"):
            env.pop(k, None)
        env.update(extra)
    body = ("\nTERM 140,42\n" + "".join(c + "\n" for c in cmds) + "OFF\n").encode("latin-1")
    p = subprocess.run([os.path.join(box, "sys", "bin", "sd"), "-internal"], input=body, cwd=os.path.join(box, "sys"), env=env, capture_output=True, timeout=600)
    return p.stdout + p.stderr


def tag(text, name):
    m = re.search(r"(?m)^%s\[(.*)\]\s*$" % name, text)
    return None if m is None else m.group(1)


def counts(s):
    d = {}
    if s is None:
        return d
    for m in re.finditer(r"(\w+)=(\S*)", s):
        d[m.group(1)] = m.group(2)
    return d


# The test program.  Array position 4 of a screen context is the shadow (SL.S.SHADOW): value y + 1 is the text of row y.
PROG = r"""$internal
   call $sl_scr('get', scr)
   esc = char(27)
   t1 = 'A' : esc : '[777z' : 'B' : esc : ']0;PWN' : char(7) : 'C' : char(9) : 'D' : char(0) : char(127) : char(13) : char(10) : 'E' : char(14) : 'F'
   expect = 'A' : '[' : '[777z' : 'B' : '[' : ']0;PWN' : 'G' : 'C' : ' ' : 'D' : '@' : '?' : 'M' : 'J' : 'E' : char(14) : 'F'
   crt char(10) : 'BEGIN1'
   call $sl_put(scr, 3, 2, t1, 'n')
   crt char(10) : 'END1'
   seg = scr<4, 3>[4, len(t1)]
   same = (if compare(seg, expect) = 0 then 1 else 0)
   nctl = 0 ; nso = 0
   for i = 1 to len(seg)
      sq = seq(seg[i, 1])
      if sq < 32 or sq = 127 then nctl += 1
      if sq = 14 then nso += 1
   next i
   crt char(10) : 'SHADOW[SAME=':same:' LEN=':len(seg):' WANT=':len(t1):' CTRL=':nctl:' STANDIN=':nso:']'
   * controls: printable text, UTF-8 bytes, a line-drawing stand-in
   u = 'caf' : char(195) : char(169) : ' [ok] ~ ' : char(34)
   crt char(10) : 'BEGIN2'
   call $sl_put(scr, 3, 3, u, 'n')
   crt char(10) : 'END2'
   seg2 = scr<4, 4>[4, len(u)]
   crt char(10) : 'PLAIN[SAME=':(if compare(seg2, u) = 0 then 1 else 0):']'
   box = char(14) : char(18) : char(15)
   crt char(10) : 'BEGIN3'
   call $sl_put(scr, 3, 4, box, 'n')
   crt char(10) : 'END3'
   * the SCREEN TEXT statement
   t2 = 'X' : esc : '[778z' : 'Y' : esc : ']2;PWN2' : char(7) : 'Z'
   crt char(10) : 'BEGIN4'
   screen text t2 at 3,6
   crt char(10) : 'END4'
   * the C1 controls (28 Oct 26, review): t3 has the single bytes 155 ('2J' after it), 128, 159, then 160 and 233 (which pass in any mode); t4 has the two-byte forms C2 9B and C2 80, a curly
   *   quote pair E2 80 9C ... E2 80 9D (which must pass in UTF-8 mode) and a C2 at the end
   t3 = 'P' : char(155) : '2J' : char(128) : char(159) : char(160) : char(233) : 'Q'
   crt char(10) : 'BEGIN5'
   call $sl_put(scr, 3, 7, t3, 'n')
   crt char(10) : 'END5'
   t4 = 'R' : char(194) : char(155) : '2J' : char(194) : char(128) : char(226) : char(128) : char(156) : 'hi' : char(226) : char(128) : char(157) : char(194) : 'S' : char(194)
   crt char(10) : 'BEGIN6'
   call $sl_put(scr, 3, 8, t4, 'n')
   crt char(10) : 'END6'
   s3 = scr<4, 8>[4, len(t3)]
   codes = ''
   for i = 1 to len(s3)
      if i > 1 then codes := ','
      codes := seq(s3[i, 1])
   next i
   crt char(10) : 'SH3[LEN=':len(s3):' CODES=':codes:']'
   s4 = scr<4, 9>[4, len(t4)]
   codes = ''
   for i = 1 to len(s4)
      if i > 1 then codes := ','
      codes := seq(s4[i, 1])
   next i
   crt char(10) : 'SH4[LEN=':len(s4):' CODES=':codes:']'
   crt char(10) : 'DONE'
   stop
end
"""


def between(raw, a, b):
    i = raw.find(a)
    j = raw.find(b, i + 1) if i >= 0 else -1
    return b"" if i < 0 or j < 0 else raw[i + len(a):j]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-escdata.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-escdata: sandbox %s" % box)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-escdata: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    made = []
    try:
        with open(os.path.join(sysd, "bp", "zzescdata"), "w") as fh:
            fh.write(PROG)
        made.append("zzescdata")
        out = session_raw(box, "BASIC bp zzescdata").decode("latin-1")
        row("setup: the test program compiles with no errors", "Compiled 1 program(s) with no errors" in out, out[-700:])
        if "Compiled 1 program(s) with no errors" not in out:
            bail("the test program did not compile:\n" + out[-900:])
        raw = session_raw(box, "RUN bp zzescdata")
        text = raw.decode("latin-1")
        row("setup: control - the program ran to its end (it printed DONE)", re.search(r"(?m)^DONE\s*$", ANSI.sub("", text)) is not None, ANSI.sub("", text)[-400:])
        r1 = between(raw, b"BEGIN1", b"END1")
        r4 = between(raw, b"BEGIN4", b"END4")
        row("setup: control - the bytes between the markers are there (null case: the rows below read %d and %d bytes)" % (len(r1), len(r4)), len(r1) > 20 and len(r4) > 5, repr((r1[:60], r4[:60])))
        bad = [n for n, seq in (("ESC [ 777 z", b"\x1b[777z"), ("OSC title", b"\x1b]0;PWN"), ("bell", b"\x07"), ("SO", b"\x0e")) if seq in r1]
        row("E1: none of the injected sequences is in the bytes $sl_put wrote (ESC [ 777 z, the OSC title, the bell, SO)", not bad, "in the output: " + ", ".join(bad))
        shown = ANSI.sub("", r1.decode("latin-1"))
        shown = shown.replace("\r", "").replace("\n", "")
        row("E2: ... what is shown instead reads A[[777zB[]0;PWNGC D@?MJE (ESC as [, BEL as G, tab as a blank, NUL as @, DEL as ?, return as M, line feed as J)", "A[[777zB[]0;PWNGC D@?MJE" in shown, repr(shown[:120]))
        sh = counts(tag(ANSI.sub("", text), "SHADOW"))
        row("E3: one cell for one character: the shadow holds the text at the same length (%s of %s), the same text as the expected one, no control character, and the one stand-in CHAR(14) kept"
            % (sh.get("LEN"), sh.get("WANT")), sh.get("SAME") == "1" and sh.get("LEN") == sh.get("WANT") and sh.get("CTRL") == "1" and sh.get("STANDIN") == "1", repr(tag(ANSI.sub("", text), "SHADOW")))
        bad4 = [n for n, seq in (("ESC [ 778 z", b"\x1b[778z"), ("OSC title", b"\x1b]2;PWN2"), ("bell", b"\x07")) if seq in r4]
        sh4 = ANSI.sub("", r4.decode("latin-1")).replace("\r", "").replace("\n", "")
        row("E4: the SCREEN TEXT statement: none of the injected sequences is written and the text reads X[[778zY[]2;PWN2GZ", not bad4 and "X[[778zY[]2;PWN2GZ" in sh4, repr((bad4, sh4[:80])))
        r2 = between(raw, b"BEGIN2", b"END2")
        pl = counts(tag(ANSI.sub("", text), "PLAIN"))
        row("E5a (control): printable ASCII and the UTF-8 bytes 195 169 pass unchanged - they are in the written bytes and in the shadow", b"caf\xc3\xa9 [ok] ~ \"" in r2 and pl.get("SAME") == "1",
            repr((r2[:60], tag(ANSI.sub("", text), "PLAIN"))))
        r3 = between(raw, b"BEGIN3", b"END3")
        row("E5b (control): the stand-ins of $sl_line are still turned into line characters (UTF-8 box bytes) or + - + (an older terminal), and SO is never written",
            (b"\xe2\x94\x8c" in r3 or b"+-+" in r3) and b"\x0e" not in r3 and b"\x0f" not in r3, repr(r3[:60]))

        # --- the C1 controls (28 Oct 26, review).  The first run above is made with LC_ALL=C: a terminal that is NOT in UTF-8 mode; the second with a UTF-8 locale.
        # the style sequences are the theme's, so "reverse" is judged as a style sequence the plain run (r2: style n only) does not have
        sgr = re.compile(rb"\x1b\[[0-9;]*m")
        plain_sgr = set(sgr.findall(r2))

        def rev(r):
            return bool(set(sgr.findall(r)) - plain_sgr)
        out_c = session_raw(box, "RUN bp zzescdata", LC_ALL="C")
        out_u = session_raw(box, "RUN bp zzescdata", LC_ALL="en_US.UTF-8")
        row("setup: control - both C1 runs ran to their end (DONE) and wrote the markers (null case: %d and %d bytes)" % (len(out_c), len(out_u)),
            all(re.search(r"(?m)^DONE\s*$", ANSI.sub("", o.decode("latin-1"))) is not None and b"END6" in o for o in (out_c, out_u)), repr((out_c[-80:], out_u[-80:])))

        def shadow(out, tg):
            m = re.search(r"(?m)^%s\[LEN=(\d+) CODES=([0-9,]*)\]" % tg, ANSI.sub("", out.decode("latin-1")))
            return None if m is None else (int(m.group(1)), [int(x) for x in m.group(2).split(",") if x])

        def stripped(out, a, b):
            return ANSI.sub("", between(out, a, b).decode("latin-1")).replace("\r", "").replace("\n", "").encode("latin-1")

        # t3 = P 155 2 J 128 159 160 233 Q ; t4 = R C2 9B 2 J C2 80 E2 80 9C h i E2 80 9D C2 S C2
        t3 = [80, 155, 50, 74, 128, 159, 160, 233, 81]
        t4 = [82, 194, 155, 50, 74, 194, 128, 226, 128, 156, 104, 105, 226, 128, 157, 194, 83, 194]
        t3_c = [80, 91, 50, 74, 64, 95, 160, 233, 81]
        t4_c = [82, 194, 91, 50, 74, 194, 64, 226, 64, 92, 104, 105, 226, 64, 93, 194, 83, 194]
        t4_u = [82, 46, 91, 50, 74, 46, 64, 226, 128, 156, 104, 105, 226, 128, 157, 194, 83, 194]
        r5c, r6c = between(out_c, b"BEGIN5", b"END5"), between(out_c, b"BEGIN6", b"END6")
        r5u, r6u = between(out_u, b"BEGIN5", b"END5"), between(out_u, b"BEGIN6", b"END6")
        row("C1a: NOT UTF-8 - the single bytes 155, 128 and 159 are not in the bytes written (0x9B is CSI there); the bytes 160 and 233 are (null case: %d bytes read)" % len(r5c),
            len(r5c) > 5 and not any(0x80 <= c <= 0x9F for c in r5c) and b"\xa0\xe9" in r5c, repr(r5c[:60]))
        row("C1b: NOT UTF-8 - what is shown reads P[2J@_ then the bytes 160 and 233 and Q (0x9B as [, 128 as @, 159 as _), and the second text has no byte 128 to 159 either",
            stripped(out_c, b"BEGIN5", b"END5") == bytes(t3_c) and not any(0x80 <= c <= 0x9F for c in r6c), repr((stripped(out_c, b"BEGIN5", b"END5"), r6c[:60])))
        row("C1c: NOT UTF-8 - one cell for one character: the shadow of both texts holds the shown codes at the SAME length (%s)" % (shadow(out_c, "SH3"),),
            shadow(out_c, "SH3") == (len(t3), t3_c) and shadow(out_c, "SH4") == (len(t4), t4_c), repr((shadow(out_c, "SH3"), shadow(out_c, "SH4"))))
        row("C1d: NOT UTF-8 - the replaced cells are drawn in the reverse style (a reverse SGR is in the written bytes), the control run of plain text is not",
            rev(r5c) and not rev(r2), repr(r5c[:80]))
        row("C1e: UTF-8 - the two-byte forms C2 9B and C2 80 are not in the bytes written (C2 followed by 0x80-0x9F), and the shown text reads R.[2J.@ then the curly quote pair and hi intact, "
            "a lone C2 before S and at the end untouched",
            len(r6u) > 5 and not re.search(rb"\xc2[\x80-\x9f]", r6u) and stripped(out_u, b"BEGIN6", b"END6") == bytes(t4_u), repr((stripped(out_u, b"BEGIN6", b"END6"), r6u[:80])))
        row("C1f: UTF-8 - the shadow holds the same: the replaced pairs are two cells for two bytes (same length), the curly quotes E2 80 9C and E2 80 9D are there byte for byte (%s)" % (shadow(out_u, "SH4"),),
            shadow(out_u, "SH4") == (len(t4), t4_u), repr(shadow(out_u, "SH4")))
        row("C1g (control): UTF-8 - a LONE byte 155 or 128 is not a C1 control there: the first text passes unchanged, in the bytes written and in the shadow",
            stripped(out_u, b"BEGIN5", b"END5") == bytes(t3) and shadow(out_u, "SH3") == (len(t3), t3), repr((stripped(out_u, b"BEGIN5", b"END5"), shadow(out_u, "SH3"))))
        row("C1h: UTF-8 - the replaced pairs are drawn in reverse; the control run of plain text is not", rev(r6u) and not rev(r2), repr(r6u[:80]))
    finally:
        for nm in made:
            for d in ("bp", "bp.out"):
                p = os.path.join(sysd, d, nm)
                if os.path.exists(p):
                    os.remove(p)

    say("\nsandbox-escdata: %d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        bail("no row ran - a broken test, not a pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
