#!/usr/bin/env python3
#
# sandbox-gcatmode.py - W.11 F2 (security-model evaluation, 24 Oct 2026): the kernel does not load a global catalogue object that others or the
# group sdusers can write.  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-gcatmode.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or absent).  Exit 0 every row
# passed, 1 a row failed, 2 it could not run.  It needs the group sdusers to exist and the person running it to be in it (the rule is about that
# group; a machine without it cannot run the group rows, and says so).
#
# START-HISTORY:
# 25 Oct 26 dm  Two rows for an object made by CATALOG itself: not group- or other-writable under CPROC's umask 002, and the umask put back.  The real-install witness
#               found Dev could not be installed (gpl.bp/catalog wrote the object 0664).
# 24 Oct 26 dm  New.  object.c gcat_object_writable(), message 11930.
# END-HISTORY
#
# THE VERDICTS.  The command is LIST.TERM.TYPES, whose program ($lstterm) is a global catalogue object.  A refusal is anchored on the words of message
# 11930 ("was not loaded"), which only the new kernel code prints; a success is the same output as the baseline run (taken first, and refused if it
# is empty or already carries the refusal).  The modes are set on the sandbox's own gcat file with chmod and chgrp, and put back at the end.

import grp
import importlib.util
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
sys.path.insert(0, HERE)


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
passed = failed = 0
CMD = "LIST.TERM.TYPES"
REFUSAL = "was not loaded"


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
    say("sandbox-gcatmode: CANNOT RUN - " + msg)
    sys.exit(2)


def sess(box, *cmds):
    say("    > " + " | ".join(cmds))
    p = subprocess.run([sys.executable, TOOL, box, "sess", os.path.join(box, "user_accounts")] + list(cmds),
                       capture_output=True, text=True, errors="replace", timeout=600)
    out = ANSI.sub("", p.stdout + p.stderr)
    return out.split(":TERM 200,9999", 1)[-1]


def body(out):
    """what the command printed: the lines after its echo, without the prompts"""
    tail = out.split(CMD, 1)[-1]
    return [l.strip() for l in tail.split("\n") if l.strip() and not l.strip().startswith(":")]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-gcatmode.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-gcatmode: sandbox %s" % box)
    try:
        sdusers = grp.getgrnam("sdusers").gr_gid
    except KeyError:
        bail("there is no group sdusers on this machine (the group rows cannot run)")
    if sdusers not in os.getgroups() and sdusers != os.getgid():
        bail("this user is not in the group sdusers, so it cannot give a file to it")
    mygid = os.getgid()
    if mygid == sdusers:
        bail("this user's own group IS sdusers, so the control of a file with another group cannot be made")
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-gcatmode: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    obj = os.path.join(sysd, "gcat", "$lstterm")
    cproc = os.path.join(sysd, "gcat", "$cproc")
    if not os.path.isfile(obj) or not os.path.isfile(cproc):
        bail("the sandbox's gcat holds no $lstterm or no $cproc")
    saved = {p: (os.stat(p).st_mode & 0o7777, os.stat(p).st_gid) for p in (obj, cproc)}

    def setmode(path, mode, gid):
        os.chown(path, -1, gid)
        os.chmod(path, mode)
        st = os.stat(path)
        say("    gcat/%s is now %o group %d" % (os.path.basename(path), st.st_mode & 0o7777, st.st_gid))

    try:
        say("\n--- the global catalogue object $lstterm (LIST.TERM.TYPES) ------------------------------------------------")
        setmode(obj, 0o755, mygid)
        base = body(sess(box, CMD))
        row("CONTROL: the command prints something (a baseline of %d lines) and no refusal" % len(base),
            len(base) >= 1 and not any(REFUSAL in l for l in base), " | ".join(base[:3]))
        if not base or any(REFUSAL in l for l in base):
            bail("the baseline run is empty or already refused")

        def check(name, mode, gid, refused):
            setmode(obj, mode, gid)
            out = sess(box, CMD)
            b = body(out)
            if refused:
                row(name, any(REFUSAL in l and "$lstterm" in l for l in b) and not (b == base), out[-300:])
            else:
                row(name, b == base and not any(REFUSAL in l for l in b), out[-300:])

        check("0664, group sdusers: refused, and the message names the object", 0o664, sdusers, True)
        check("0755, group sdusers: loaded as before", 0o755, sdusers, False)
        check("0775, group sdusers: refused", 0o775, sdusers, True)
        check("0644, group sdusers (readable, not writable): loaded", 0o644, sdusers, False)
        check("0666, the user's own group (others can write): refused", 0o666, mygid, True)
        check("0664, the user's own group, not sdusers (a sandbox's usual state): loaded", 0o664, mygid, False)
        check("0646, group sdusers (others can write, group cannot): refused", 0o646, sdusers, True)
        check("0755 again: loaded (the refusal leaves nothing behind)", 0o755, mygid, False)

        say("\n--- the command processor itself, gcat/$cproc (the case of a fresh install before the fix) ------------------")
        setmode(cproc, 0o664, sdusers)
        out = sess(box, "WHO")
        row("$cproc 0664 group sdusers: a session does not start on it, and says which object", REFUSAL in out and "$cproc" in out, out[-300:])
        setmode(cproc, 0o755, mygid)
        out = sess(box, "WHO")
        row("$cproc 0755: the session starts again", REFUSAL not in out and re.search(r"\bWHO\b", out) is not None and len(out.strip()) > 10, out[-300:])

        # 25 Oct 26, the real-install witness: CPROC sets umask 002 for every session, so CATALOG made a global object 0664 - and, on an install, group sdusers - and the check
        # above refused to load it in the middle of the installer's own bootstrap (Dev could not be installed).  A sandbox's group is the user's own, which is why nothing
        # here saw it; the MODE BITS are visible all the same, with no group needed.
        say("\n--- an object made by CATALOG itself (the case the installer's bootstrap is in) -------------------------------")
        g = _load("sandbox_gates_for_gcatmode", "sandbox-gates.py")
        g.BOX, g.SYS, g.SD = box, sysd, os.path.join(sysd, "bin", "sd")
        g.put(os.path.join(sysd, "bp", "zzgcatm"), "program zzgcatm\n   crt 'ZZGCATM ran'\nend\n")
        g.put(os.path.join(sysd, "bp", "zzgcatu"), "program zzgcatu\n   crt 'ZZUMASK ':fmt(oconv(umask(-1), 'MO'), \"3'0'R\")\nend\n")
        out = g.adm(["BASIC bp zzgcatu", "BASIC bp zzgcatm", "CATALOG bp zzgcatm GLOBAL", "RUN bp zzgcatu"])
        made = os.path.join(sysd, "gcat", "zzgcatm")
        compiled = sum(1 for ln in out if re.match(r"^Compiled 1 program\(s\) with no errors", ln))
        said = any("added to global catalogue" in ln for ln in out)
        row("CONTROL: both programs compiled, the second was catalogued globally (the verb said so) and its object is in gcat", compiled == 2 and said and os.path.isfile(made),
            "compiled %d, said so: %s, object there: %s, output tail %r" % (compiled, said, os.path.isfile(made), out[-5:]))
        if compiled != 2 or not said or not os.path.isfile(made):
            bail("the test program was not catalogued: the rows below would measure nothing")
        mode = os.stat(made).st_mode & 0o7777
        row("a global object made by CATALOG is not writable by group or others, whatever the session's umask (mode %o)" % mode, mode & 0o022 == 0, "mode %o" % mode)
        um = [ln for ln in out if re.match(r"^ZZUMASK \d+$", ln)]
        row("and the session's umask is back at 002 afterwards (a RUN in the same session answers it)", um == ["ZZUMASK 002"], "answered %r" % um)
    finally:
        for p, (m, g) in saved.items():
            try:
                os.chown(p, -1, g)
                os.chmod(p, m)
            except OSError as e:
                say("    could not put %s back: %s" % (p, e))

    say("")
    say("sandbox-gcatmode: %d passed, %d failed" % (passed, failed))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
