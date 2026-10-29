#!/usr/bin/env python3
#
# sandbox-themeroles.py - S.88 3.7a: CONFIG() reads SCREENTHEME, the five role styles have a look in every theme, $sl_theme answers 'list' and 'next', and a program that
# asks for no theme still gets mono.  No install, no sudo.  WRITTEN WITH THE CHANGE AND NOT RUN (the owner's rule of 28 Oct 2026); the first run is the main session's.
#
#   SDBOX_KEYSET=n python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-themeroles.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (SHORT path under /tmp).  With --build it is built first from THIS tree (it must be empty or absent), which compiles every
# program against the new SL.CODES: a sandbox built from an older tree gives mono in every row and the suite says so.  Exit 0 every row passed, 1 a row failed, 2 it could not
# run.  Remove the directory afterwards.
#
# START-HISTORY:
# 29 Oct 26 dm  New (S.88 3.7a).
# END-HISTORY
#
# WHAT IT MEASURES.
#   C  CONFIG('SCREENTHEME') on an INTERNAL program (sd -internal, SDTEST_ADMIN=1): '' with status 0 while the sandbox's sd.conf has no such line, 'blue' once a line is added
#      (a new session reads the file), 'mono' for an explicit mono; BACKUPDIR and SDSYS and a 17-character name stay 'not found' (status # 0); the 11-character name is the one
#      that never worked
#   L  $sl_theme 'list' is five names in the one order; 'next' on a pipe (no terminal) is mono whatever it is asked
#   P  on a pseudo-terminal (xterm, then linux, which has dim; then vt100, which has no colour): 'next' walks mono blue classic dark light mono, a vt100 never leaves mono; the
#      escape sequence of every role in every theme ($sl_sgr) is printed with control characters as <n>; in mono the six role sequences differ from one another and from normal, hold no
#      dim sequence (linux), and in every colour theme the roles differ from one another and from normal
#   D  SCREEN OPEN's default (an internal probe, since the theme name is read with $sl_theme): with SCREENTHEME=blue in sd.conf a program that opens a screen and asks for nothing is in
#      blue; with no line, in mono (a user program keeps the library's unset default); with SCREENTHEME=mono on a colour terminal, in mono; blue on a vt100 is mono
# THE INSTRUMENT.  Every probe line starts with a tag no echo carries (CFG, LST, NXT, SEQ, DEF); a row that finds no such line FAILS (a missing line is exit 2 for the fixture, a
# failed row otherwise).  The sandbox's sd.conf is restored when the suite ends.

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ptydrive import PtySession  # noqa: E402

TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
RUN = "%05d" % (os.getpid() % 100000)
PCFG = "zztc" + RUN       # CONFIG() of several names
PSEQ = "zzts" + RUN       # the list, 'next', the sequences
PDEF = "zztd" + RUN       # SCREEN OPEN with nothing asked
passed = failed = 0
ROLES = ["warning", "success", "readonly", "busy", "focus", "error"]
THEMES = ["mono", "blue", "classic", "dark", "light"]

SRC_CFG = """$internal
   names = 'SCREENTHEME' : @fm : 'BACKUPDIR' : @fm : 'SDSYS' : @fm : 'ABCDEFGHIJKLMNOPQ' : @fm : 'NOSUCHKEY' : @fm : 'GRPSIZE'
   for i = 1 to dcount(names, @fm)
      v = config(names<i>)
      crt 'CFG ' : names<i> : ' value=<' : v : '> status=' : status()
   next i
end
"""

SRC_SEQ = """$internal
$include sl.h
   call $sl_theme('list', '', '', '', '', l)
   crt 'LST ' : change(l, @fm, ',')
   call $sl_theme('name', '', '', '', '', cur)
   crt 'NXT start=' : cur
   for i = 1 to 6
      call $sl_theme('next', cur, '', '', '', nx)
      crt 'NXT ' : cur : '->' : nx
      call $sl_theme('set', nx, '', '', '', r)
      crt 'NXT set ' : nx : ' ret=' : r
      cur = nx
   next i
   names = 'normal' : @fm : 'warning' : @fm : 'success' : @fm : 'readonly' : @fm : 'busy' : @fm : 'focus' : @fm : 'error'
   themes = 'mono' : @fm : 'blue' : @fm : 'classic' : @fm : 'dark' : @fm : 'light'
   for t = 1 to 5
      call $sl_theme('set', themes<t>, '', '', '', r)
      if r # 0 then
         crt 'SEQ ' : themes<t> : ' refused ret=' : r
         continue
      end
      for k = 1 to 7
         call $sl_theme('code', names<k>, '', '', '', code)
         call $sl_sgr(code, sq)
         out = ''
         for j = 1 to len(sq)
            c = sq[j, 1]
            if seq(c) < 32 then out := '<' : seq(c) : '>' else out := c
         next j
         crt 'SEQ ' : themes<t> : ' ' : names<k> : ' code=' : code : ' ' : out
      next k
   next t
   call $sl_theme('reset', '', '', '', '', r)
   dm = @(-11)
   out = ''
   for j = 1 to len(dm)
      c = dm[j, 1]
      if seq(c) < 32 then out := '<' : seq(c) : '>' else out := c
   next j
   crt 'SEQ dim ' : out
end
"""

SRC_DEF = """$internal
   screen open
   call $sl_theme('name', '', '', '', '', n)
   crt 'DEF open theme=' : n
   screen close
   call $sl_theme('name', '', '', '', '', n)
   crt 'DEF after close theme=' : n
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
    say("sandbox-themeroles: CANNOT RUN - " + msg)
    sys.exit(2)


def sdenv(box, term=None):
    e = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"), SDTEST_ADMIN="1", LC_ALL="C")
    e.pop("LINES", None)
    e.pop("COLUMNS", None)
    if term:
        e["TERM"] = term
    return e


def sess(box, *cmds):
    p = subprocess.run([sys.executable, TOOL, box, "sess", os.path.join(box, "user_accounts")] + list(cmds),
                       capture_output=True, text=True, errors="replace", timeout=600)
    return ANSI.sub("", p.stdout + p.stderr)


def isess(box, *cmds, term=None):
    """INTERNAL mode on a pipe: no terminal"""
    body = "\nTERM 200,9999\n" + "".join(c + "\n" for c in cmds) + "OFF\n"
    p = subprocess.run([os.path.join(box, "sys", "bin", "sd"), "-internal"], input=body, cwd=os.path.join(box, "sys"), env=sdenv(box, term),
                       capture_output=True, text=True, errors="replace", timeout=300)
    return ANSI.sub("", p.stdout + p.stderr)


def pty_internal(box, term, cmds):
    """INTERNAL mode on a pseudo-terminal of 140 by 60 (room for every probe line); returns the screen's lines"""
    s = PtySession([os.path.join(box, "sys", "bin", "sd"), "-internal"], os.path.join(box, "sys"), sdenv(box, term), 140, 60)
    s.settle(1.0)
    s.type("TERM %s\r" % term)
    for c in cmds:
        s.type(c + "\r", idle=1.0)
    lines = s.screen.lines()
    s.type("\rOFF\r", idle=0.5)
    s.finish()
    return lines


def tagged(text, tag):
    """the probe lines that BEGIN with the tag (the echo of the command begins with RUN, never with a tag)"""
    return [ln.rstrip() for ln in (text if isinstance(text, list) else text.split("\n")) if ln.startswith(tag + " ")]


def conf_path(box):
    return os.path.join(box, "sd.conf")


def read_conf(box):
    with open(conf_path(box)) as fh:
        return fh.read()


def write_conf(box, text):
    with open(conf_path(box), "w") as fh:
        fh.write(text)


def cfg(out):
    d = {}
    for ln in tagged(out, "CFG"):
        m = re.match(r"CFG (\S+) value=<(.*)> status=(-?\d+)$", ln)
        if m:
            d[m.group(1)] = (m.group(2), int(m.group(3)))
    return d


def seqs(lines):
    """{theme: {style: sequence}} from SEQ lines"""
    d = {}
    for ln in tagged(lines, "SEQ"):
        m = re.match(r"SEQ (\S+) (\S+) code=(\S) (.*)$", ln)
        if m:
            d.setdefault(m.group(1), {})[m.group(2)] = m.group(4)
    return d


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-themeroles.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-themeroles: sandbox %s" % box)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-themeroles: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    original = read_conf(box)
    if re.search(r"(?m)^SCREENTHEME=", original):
        bail("the sandbox's sd.conf already has a SCREENTHEME line, so the 'unset' rows cannot be measured")
    for nm, body in ((PCFG, SRC_CFG), (PSEQ, SRC_SEQ), (PDEF, SRC_DEF)):
        with open(os.path.join(sysd, "bp", nm), "w") as fh:
            fh.write(body)
    try:
        say("\n--- setup ---------------------------------------------------------------------------------------")
        iout = isess(box, "BASIC bp " + PCFG, "BASIC bp " + PSEQ, "BASIC bp " + PDEF)
        uout = ""
        row("setup: the three probes (all internal: a user program cannot call $sl_theme) compiled with no errors", len(re.findall(r"(?m)^Compiled 1 program\(s\) with no errors", iout + uout)) == 3, (iout + uout)[-600:])
        if len(re.findall(r"(?m)^Compiled 1 program\(s\) with no errors", iout + uout)) != 3:
            bail("the probes did not compile:\n" + (iout + uout)[-800:])

        say("\n--- C: CONFIG() of SCREENTHEME ----------------------------------------------------------------------")
        c = cfg(isess(box, "RUN bp " + PCFG))
        row("the probe answered for all six names (the null case: the instrument measured)", len(c) == 6, repr(c))
        row("SCREENTHEME with no line in sd.conf: empty, status 0 (it was 'not found' for ever: the name is 11 characters)", c.get("SCREENTHEME") == ("", 0), repr(c.get("SCREENTHEME")))
        row("CONTROL: GRPSIZE is read", c.get("GRPSIZE", ("", 1))[1] == 0 and c.get("GRPSIZE", ("", 1))[0] != "", repr(c.get("GRPSIZE")))
        row("BACKUPDIR and SDSYS (no branch), a 17-character name and an unknown name are still not found", all(c.get(k, ("", 0))[1] != 0 for k in ("BACKUPDIR", "SDSYS", "ABCDEFGHIJKLMNOPQ", "NOSUCHKEY")), repr(c))
        write_conf(box, original.rstrip("\n") + "\nSCREENTHEME=blue\n")
        c = cfg(isess(box, "RUN bp " + PCFG))
        row("with SCREENTHEME=blue in the file a new session reads 'blue', status 0", c.get("SCREENTHEME") == ("blue", 0), repr(c.get("SCREENTHEME")))
        write_conf(box, original.rstrip("\n") + "\nSCREENTHEME=mono\n")
        c = cfg(isess(box, "RUN bp " + PCFG))
        row("with SCREENTHEME=mono it reads 'mono'", c.get("SCREENTHEME") == ("mono", 0), repr(c.get("SCREENTHEME")))
        write_conf(box, original)

        say("\n--- L: the list, and 'next' with no terminal -------------------------------------------------------")
        out = isess(box, "RUN bp " + PSEQ)
        lst = tagged(out, "LST")
        row("$sl_theme 'list' is blue,classic,dark,light,mono", lst == ["LST blue,classic,dark,light,mono"], repr(lst))
        nx = tagged(out, "NXT")
        row("on a pipe (no terminal) 'next' is mono whatever it is asked, and mono is the theme the program starts in",
            nx and nx[0] == "NXT start=mono" and all(re.match(r"NXT (mono->mono|set mono ret=0)$", x) for x in nx[1:]), repr(nx))

        say("\n--- P: a colour terminal ----------------------------------------------------------------------------")
        for term in ("xterm", "linux"):
            lines = pty_internal(box, term, ["RUN bp " + PSEQ])
            nx = [x for x in tagged(lines, "NXT") if "->" in x]
            walk = [re.match(r"NXT (\S+)->(\S+)$", x).groups() for x in nx]
            row("%s: 'next' walks mono -> blue -> classic -> dark -> light -> mono -> blue" % term,
                [b for _, b in walk] == ["blue", "classic", "dark", "light", "mono", "blue"], repr(walk))
            sq = seqs(lines)
            row("%s: the probe printed the sequences of all five themes and all seven styles" % term, sorted(sq) == sorted(THEMES) and all(len(v) == 7 for v in sq.values()), repr({k: len(v) for k, v in sq.items()}))
            if not sq:
                continue
            dim = (tagged(lines, "SEQ dim") or ["SEQ dim "])[0][len("SEQ dim "):]
            for t in THEMES:
                if t not in sq:
                    continue
                rs = [sq[t][r] for r in ROLES]
                row("%s %s: the six role sequences differ from one another" % (term, t), len(set(rs)) == 6, repr(rs))
                row("%s %s: ... and from normal's" % (term, t), sq[t]["normal"] not in rs, repr((sq[t]["normal"], rs)))
            if "mono" in sq:
                row("%s mono: no role asks for dim%s" % (term, "" if dim else " (this terminal has none: the row proves nothing here)"),
                    all(not dim or dim not in sq["mono"][r] for r in ROLES), repr((dim, {r: sq["mono"][r] for r in ROLES})))
                row("%s mono: the roles use flags and no colour (no 'setf' or 'setb' sequence differs from normal's start)" % term,
                    all(sq["mono"][r].count("<27>[3") == 0 and sq["mono"][r].count("<27>[4") == 0 for r in ROLES), repr({r: sq["mono"][r] for r in ROLES}))
        lines = pty_internal(box, "vt100", ["RUN bp " + PSEQ])
        nx = [re.match(r"NXT (\S+)->(\S+)$", x).groups() for x in tagged(lines, "NXT") if "->" in x]
        row("vt100 (no colour): 'next' never leaves mono, and the colour themes are refused (ret 1)", nx and all(b == "mono" for _, b in nx) and any("refused ret=1" in x for x in tagged(lines, "SEQ")), repr(nx))

        say("\n--- D: SCREEN OPEN with nothing asked -------------------------------------------------------------------")
        for conf, want, why in ((original, "mono", "no SCREENTHEME line: a user program keeps the library's unset default"),
                                (original.rstrip("\n") + "\nSCREENTHEME=blue\n", "blue", "SCREENTHEME=blue"),
                                (original.rstrip("\n") + "\nSCREENTHEME=mono\n", "mono", "an explicit SCREENTHEME=mono")):
            write_conf(box, conf)
            lines = pty_internal(box, "xterm", ["RUN bp " + PDEF])
            d = tagged(lines, "DEF")
            row("xterm, %s: the program opens in %s, and SCREEN CLOSE gives it back as mono" % (why, want), len(d) == 2 and d[0] == "DEF open theme=" + want and d[1] == "DEF after close theme=mono", repr(d))
        write_conf(box, original.rstrip("\n") + "\nSCREENTHEME=blue\n")
        lines = pty_internal(box, "vt100", ["RUN bp " + PDEF])
        d = tagged(lines, "DEF")
        row("vt100 with SCREENTHEME=blue: no colour, so the program is in mono", len(d) == 2 and d[0] == "DEF open theme=mono", repr(d))
    finally:
        write_conf(box, original)
        subprocess.run([sys.executable, TOOL, box, "stop"], capture_output=True, text=True, errors="replace", timeout=120)

    say("")
    say("sandbox-themeroles: %d passed, %d failed" % (passed, failed))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
