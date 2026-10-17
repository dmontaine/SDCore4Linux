#!/usr/bin/env python3
#
# sandbox-terminfo-ext.py - eblink, eprot, edim, erev and ebold end ONE terminal attribute (QM4 Fixes item 47).
#
#   SD ended blink, half intensity, reverse video and bold with sgr0, which ends every attribute AND the colours at once.
#   A terminfo entry can now define eblink, edim, erev and ebold (and eprot, which no @() function uses yet): @(-6), @(-12),
#   @(-14) and @(-59) send that capability, or sgr0 when the entry has none.  Nothing changes for an entry that has none,
#   which is every stock entry: the internal programs that use @(-14) to put the colours back (QUERY styles, SED, the pick
#   lists) keep doing so.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-terminfo-ext.py <dir> [--build]
#
# No install, no sudo.  <dir> is a sandbox made by sandbox-fromtree.py (needs a `make`d bin/sd and bin/sdtic).  With --build it
# is built first from THIS tree (it must be empty or absent).  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 16 Oct 26 dm  New.
# END-HISTORY
#
# THE INSTRUMENT.  Two terminals are made from the stock `ansi` entry of terminfo.src: zzstock (the same entry under another
# name: it has none of the five capabilities) and zzext (the same entry with all five).  A third, zzpart, has only erev.  They
# are compiled with the sandbox's own sdtic into the sandbox's terminfo directory.  An internal program run with TERM set to
# each prints the type SD chose (so a row cannot pass on a terminal that was not the one asked for) and the bytes that the
# four @() functions give, in hex.  CONTROL rows: the same program with the stock `ansi` entry itself, and the start
# functions @(-5) and @(-13), which did not change.

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
SRC = os.path.join(HERE, "..", "terminfo.src")

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
passed = failed = 0
made = []


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
    say("sandbox-terminfo-ext: CANNOT RUN - " + msg)
    sys.exit(2)


def tool(box, *args, **kw):
    return subprocess.run([sys.executable, TOOL, box] + list(args), capture_output=True, text=True, errors="replace",
                          timeout=kw.pop("timeout", 900), **kw)


def hexof(s):
    return "".join("%02X" % ord(c) for c in s)


def ansi_entry():
    """The text of the stock ansi entry, from the name line to the blank line after it."""
    with open(SRC) as f:
        lines = f.read().split("\n")
    start = next(i for i, ln in enumerate(lines) if ln.startswith("ansi|"))
    end = start
    while lines[end].strip():
        end += 1
    return lines[start:end]


def renamed(name, extra):
    body = ansi_entry()
    body[0] = name + "|test terminal made from ansi,"
    if extra:
        body[-1] = body[-1].rstrip(",") + ","
        body.append("    " + extra)
    return "\n".join(body) + "\n"


PROG = """$internal
   void kernel(11, '@TERM@')    ;* K$TERM.TYPE (gpl.bp/int$keys.h)
   crt 'T[=':terminfo('')<1>:']'
   crt 'A[=':oconv(@(-6), 'MX0C'):']'
   crt 'B[=':oconv(@(-12), 'MX0C'):']'
   crt 'C[=':oconv(@(-14), 'MX0C'):']'
   crt 'D[=':oconv(@(-59), 'MX0C'):']'
   crt 'E[=':oconv(@(-5), 'MX0C'):']'
   crt 'F[=':oconv(@(-13), 'MX0C'):']'
   crt 'G[=':oconv(terminfo('eprot'), 'MX0C'):']'
   crt 'H[=':oconv(terminfo('erev'), 'MX0C'):']'
end
"""

# the bytes the entries are given (\E[25m and so on)
# (no comma after the last token: a line that ends with a comma continues on the next one)
EXT = "eblink=\\E[25m, eprot=\\E[4m, edim=\\E[22m, erev=\\E[27m, ebold=\\E[22m"
PART = "erev=\\E[27m"


def run(box, term):
    """Run the probe as `term`: the program sets the terminal type itself (kernel(K$TERM.TYPE)), since an internal session
    takes no TERM from the environment."""
    with open(os.path.join(box, "sys", "bp", "zzti"), "w") as f:
        f.write(PROG.replace("@TERM@", term))
    env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"))
    body = "\nTERM 200,9999\nBASIC bp zzti\nRUN bp zzti\nOFF\n"
    p = subprocess.run([os.path.join(box, "sys", "bin", "sd"), "-internal"], input=body, cwd=os.path.join(box, "sys"), env=env,
                       capture_output=True, text=True, errors="replace", timeout=300)
    out = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]|\[[0-9;]*[A-Za-z]", "", ANSI.sub("", p.stdout + p.stderr).split(":TERM 200,9999", 1)[-1])
    got = {}
    for k in "TABCDEFGH":
        m = re.search(r"(?m)^%s\[=(.*)\]\s*$" % k, out)
        got[k] = m.group(1) if m else None
    say("    TERM=%-8s  type %s  @(-6) %s  @(-12) %s  @(-14) %s  @(-59) %s" % (term, got["T"], got["A"], got["B"], got["C"], got["D"]))
    return got, out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-terminfo-ext.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-terminfo-ext: sandbox %s" % box)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = tool(box, "all")
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-terminfo-ext: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    tool(box, "start", timeout=180)

    src = os.path.join(box, "zzti.src")
    with open(src, "w") as f:
        f.write(renamed("zzstock", "") + "\n" + renamed("zzext", EXT) + "\n" + renamed("zzpart", PART))
    made.append("zzti")
    r = subprocess.run([os.path.join(sysd, "bin", "sdtic"), "-p" + os.path.join(sysd, "terminfo"), src], capture_output=True,
                       text=True, errors="replace", timeout=120)
    say("    sdtic: %s" % (r.stdout + r.stderr).strip().replace("\n", " | ")[:200])
    for t in ("zzstock", "zzext", "zzpart"):
        if not os.path.isfile(os.path.join(sysd, "terminfo", t[0], t)):
            bail("sdtic did not make %s:\n%s" % (t, r.stdout + r.stderr))

    SGR0 = hexof("\x1b[0;10m")
    try:
        say("\n--- the stock entry, and a copy of it without the new capabilities (CONTROL) ----------------")
        stock, _ = run(box, "ansi")
        copy, _ = run(box, "zzstock")
        row("the instrument: TERM=ansi gave type ansi and TERM=zzstock gave zzstock", stock["T"] == "ansi" and copy["T"] == "zzstock",
            "got %r %r" % (stock["T"], copy["T"]))
        for who, g in (("ansi", stock), ("zzstock", copy)):
            row("CONTROL  %s: @(-6), @(-12), @(-14) and @(-59) all send sgr0 (%s), as before" % (who, SGR0),
                all(g[k] == SGR0 for k in "ABCD"), "got %r" % ([g[k] for k in "ABCD"],))
        row("CONTROL  @(-5) (start blink) and @(-13) (start reverse) are untouched", stock["E"] == hexof("\x1b[5m") and
            stock["F"] == hexof("\x1b[7m"), "got %r %r" % (stock["E"], stock["F"]))
        row("TERMINFO('erev') of an entry without it is the null string", stock["H"] == "" and stock["G"] == "", "got %r %r" % (stock["H"], stock["G"]))

        say("\n--- an entry with all five ----------------------------------------------------------------")
        ext, _ = run(box, "zzext")
        row("the instrument: TERM=zzext gave type zzext", ext["T"] == "zzext", "got %r" % ext["T"])
        row("47  @(-6) sends eblink (ESC [ 25 m)", ext["A"] == hexof("\x1b[25m"), "got %r" % ext["A"])
        row("47  @(-12) sends edim (ESC [ 22 m)", ext["B"] == hexof("\x1b[22m"), "got %r" % ext["B"])
        row("47  @(-14) sends erev (ESC [ 27 m)", ext["C"] == hexof("\x1b[27m"), "got %r" % ext["C"])
        row("47  @(-59) sends ebold (ESC [ 22 m)", ext["D"] == hexof("\x1b[22m"), "got %r" % ext["D"])
        row("47  TERMINFO('eprot') and TERMINFO('erev') return the strings of the entry", ext["G"] == hexof("\x1b[4m") and
            ext["H"] == hexof("\x1b[27m"), "got %r %r" % (ext["G"], ext["H"]))
        row("@(-5) and @(-13) are still the start sequences", ext["E"] == hexof("\x1b[5m") and ext["F"] == hexof("\x1b[7m"),
            "got %r %r" % (ext["E"], ext["F"]))

        say("\n--- an entry with only erev: each attribute falls back by itself ------------------------------")
        part, _ = run(box, "zzpart")
        row("47  zzpart: @(-14) sends erev", part["C"] == hexof("\x1b[27m"), "got %r" % part["C"])
        row("47  zzpart: @(-6), @(-12) and @(-59) still send sgr0", all(part[k] == SGR0 for k in "ABD"),
            "got %r" % ([part[k] for k in "ABD"],))
    finally:
        for nm in made:
            for d in ("bp", "bp.out"):
                p = os.path.join(sysd, d, nm)
                if os.path.exists(p):
                    os.remove(p)

    say("\nsandbox-terminfo-ext: %d passed, %d failed" % (passed, failed))
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
