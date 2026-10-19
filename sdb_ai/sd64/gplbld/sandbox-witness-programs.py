#!/usr/bin/env python3
#
# sandbox-witness-programs.py - do the SD BASIC programs the SDNet witness scripts write into an account COMPILE?  (19 Oct 26, the S.65 finish.)
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-witness-programs.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (a private SD built from a tree: no sudo, its own IPC keys, never the live system).  With --build the sandbox is built
# first from THIS tree and <dir> must be empty or absent.  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# WHY.  gplbld/witness-sdnet-files-route.sh and witness-sdnet-two-machines.sh write a dozen small programs into the client account's bp and compile them on a real
# install, in a run the owner makes with sudo on a VM.  A typo in one costs that run.  The programs are plain text inside the scripts (quoted here-documents), so they can
# be compiled HERE, by the sandbox's own compiler, before anybody runs a witness.  This does NOT run them: they need a second server (witness) - what it proves is that the
# compiler accepts them, with the compiler of THIS tree.
#
# THE INSTRUMENT.  It extracts the programs from the scripts itself (the here-document after "prog NAME" or after "tee .../bp/NAME"), prints each name and its size, and
# refuses the null case: it must find exactly the number it expects (a count that drifted is a script that changed without this suite hearing of it), a program with no
# lines is a failure, and a CONTROL - a program with a deliberate syntax error - must NOT compile, so a compiler call that accepts everything cannot pass.
#
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
SCRIPTS = {"witness-sdnet-files-route.sh": 9, "witness-sdnet-two-machines.sh": 3, "witness-sdnet-gaps.sh": 0, "witness-sdnet-writegroup.sh": 0, "witness-sdnet-groups.sh": 0}
HEREDOC = re.compile(r"""^(?:prog (\w+)|sudo -u "\$CUSER" tee "\$CDIR/bp/(\w+)" >/dev/null) <<'EOP'\n(.*?)\nEOP$""", re.S | re.M)
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
    say("sandbox-witness-programs: CANNOT RUN - " + msg)
    sys.exit(2)


def session(box, *cmds):
    env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"))
    body = "\nTERM 200,9999\n" + "".join(c + "\n" for c in cmds) + "OFF\n"
    p = subprocess.run([os.path.join(box, "sys", "bin", "sd"), "-internal"], input=body, cwd=os.path.join(box, "sys"), env=env,
                       capture_output=True, text=True, errors="replace", timeout=180)
    out = ANSI.sub("", p.stdout + p.stderr)
    return out.split(":TERM 200,9999", 1)[-1]


def scripts_dir():
    """The directory the scripts are read from: this one, or --scripts=DIR (a copy with one program broken, to see the suite fail on it)."""
    for a in sys.argv[1:]:
        if a.startswith("--scripts="):
            return os.path.abspath(a[len("--scripts="):])
    return HERE


def extract():
    found = []
    for script, want in SCRIPTS.items():
        with open(os.path.join(scripts_dir(), script), encoding="utf-8") as f:
            text = f.read()
        progs = [(m.group(1) or m.group(2), m.group(3)) for m in HEREDOC.finditer(text)]
        say("  %-34s %d program(s): %s" % (script, len(progs), " ".join(n for n, _b in progs)))
        row("%s holds exactly %d program(s) (the count this suite was written for)" % (script, want), len(progs) == want,
            "found %d: %s" % (len(progs), " ".join(n for n, _b in progs)))
        found += [(script, n, b) for n, b in progs]
    return found


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-witness-programs.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-witness-programs: sandbox %s" % box)
    say("sandbox-witness-programs: tree    %s" % os.path.dirname(HERE))
    say("\n--- the programs in the scripts -----------------------------------------------")
    progs = extract()
    names = [n for _s, n, _b in progs]
    row("no program name is used twice (a clash would overwrite one with another in the same bp)",
        len(names) == len(set(names)), "duplicates: %s" % sorted(n for n in set(names) if names.count(n) > 1))
    if not progs:
        bail("no program was found in any script: a broken extractor, not a pass")
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-witness-programs: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    written = []
    try:
        say("\n--- compile each program with this tree's compiler -------------------------------")
        for script, name, body in progs:
            lines = [ln for ln in body.split("\n") if ln.strip()]
            row("%s / %s has program text (%d lines)" % (script, name, len(lines)), len(lines) >= 3, "empty")
            path = os.path.join(sysd, "bp", name)
            with open(path, "wb") as f:
                f.write((body + "\n").encode("ascii"))
            written.append(name)
            out = session(box, "BASIC bp " + name)
            ok = re.search(r"(?m)^0 error\(s\)", out) is not None and re.search(r"(?m)^Compiled 1 program\(s\) with no errors", out) is not None
            row("%s / %s compiles with 0 errors" % (script, name), ok, out.strip().replace("\n", " | ")[-300:])
        say("\n--- the control: a program with a deliberate syntax error must NOT compile ------")
        ctl = "zzwpctl"
        with open(os.path.join(sysd, "bp", ctl), "wb") as f:
            f.write(b"   if then\n   crt 'x'\nend\n")
        written.append(ctl)
        out = session(box, "BASIC bp " + ctl)
        bad = re.search(r"(?m)^Compiled 1 program\(s\) with no errors", out) is None and re.search(r"(?m)^0 error\(s\)", out) is None
        row("CONTROL: the broken program is refused (no '0 error(s)', no 'with no errors')", bad, out.strip().replace("\n", " | ")[-300:])
    finally:
        for name in written:
            for d in ("bp", "bp.out"):
                p = os.path.join(sysd, d, name)
                if os.path.exists(p):
                    os.remove(p)

    say("\nsandbox-witness-programs: %d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        bail("no row ran - a broken test, not a pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
