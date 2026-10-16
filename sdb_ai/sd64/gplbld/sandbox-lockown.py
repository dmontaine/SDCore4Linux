#!/usr/bin/env python3
#
# sandbox-lockown.py - $MODE AUTOLOCK and OPTION INHERIT.OWNERSHIP (openQM 4, QM4 gaps 213 and 239).  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-lockown.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty
# or absent); without it <dir> must already be built.  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 16 Oct 26 dm  New.  bcomp: $MODE AUTOLOCK sets P_AUTOLOCK on a WRITE, MATWRITE or DELETE; op_dio3.c takes the update lock
#               when the record is not locked.  op_dio1.c inherit_ownership_of(): OPTION INHERIT.OWNERSHIP.
# END-HISTORY
#
# AUTOLOCK.  A record write inside a transaction needs a lock the program holds, and a plain WRITE with none is refused with
# a run-time error.  So the program does the same WRITE and DELETE in a transaction, with and without the mode: the control
# (no mode) is refused, the mode takes the lock and the write is there (read back afterwards).  Lists of locks held afterwards
# (LIST.READU) must be empty: the lock a plain WRITE takes is let go.
# INHERIT.OWNERSHIP.  The sandbox user's primary group is not the only one it belongs to.  The sandbox account directory is
# given one of the others (chgrp as the user), a file is made with and without the option, and the group of the file's directory
# and of its subfiles is read from the disk.  If the user belongs to no other group the rows are SKIPPED, said so.

import grp
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
RUN = "%05d" % (os.getpid() % 100000)
passed = failed = skipped = 0


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
    say("sandbox-lockown: CANNOT RUN - " + msg)
    sys.exit(2)


def sess(box, *cmds, quiet=False):
    if not quiet:
        say("    > " + " | ".join(cmds))
    p = subprocess.run([sys.executable, TOOL, box, "sess", os.path.join(box, "user_accounts")] + list(cmds),
                       capture_output=True, text=True, errors="replace", timeout=600)
    out = ANSI.sub("", p.stdout + p.stderr)
    return out.split(":TERM 200,9999", 1)[-1]


def main():
    global skipped
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-lockown.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    bp = os.path.join(sysd, "bp")
    say("sandbox-lockown: sandbox %s" % box)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-lockown: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    f = "zzal" + RUN
    made = []

    def put(name, text):
        with open(os.path.join(bp, name), "w") as fh:
            fh.write(text)
        made.append(name)

    body = ("   open '%s' to f else crt 'NOFILE' ; stop\n"
            "   begin transaction\n"
            "   write 'one' on f, 'k1' on error crt 'WRITE-REFUSED'\n"
            "   delete f, 'k2' on error crt 'DELETE-REFUSED'\n"
            "   commit\n"
            "   end transaction\n"
            "   read r from f, 'k1' then crt 'K1=':r else crt 'K1-ABSENT'\n"
            "   read r from f, 'k2' then crt 'K2-STILL-THERE' else crt 'K2-GONE'\n"
            "   execute 'LIST.READU' capturing out\n"
            "   crt 'LOCKS ':(if index(upcase(out), 'K1', 1) or index(upcase(out), 'K2', 1) then 'HELD' else 'NONE')\n"
            "end\n") % f
    put("zzal_off", body)
    put("zzal_on", "$mode autolock\n" + body)
    put("zzal_seed", "   open '%s' to f else crt 'NOFILE' ; stop\n   write 'two' to f, 'k2'\n   delete f, 'k1'\n   crt 'SEEDED'\nend\n" % f)
    try:
        say("\n--- $MODE AUTOLOCK -----------------------------------------------------------------------------------")
        out = sess(box, "DELETE.FILE %s" % f, "CREATE.FILE %s" % f, "BASIC bp zzal_off", "BASIC bp zzal_on", "BASIC bp zzal_seed", quiet=True)
        row("setup: the three programs compiled", out.count("Compiled 1 program(s) with no errors") == 3, out[-400:])
        o = sess(box, "RUN bp zzal_seed", "RUN bp zzal_off")
        row("CONTROL, no mode: a WRITE in a transaction with no lock held is refused",
            re.search(r"(?m)^WRITE-REFUSED\s*$", o) is not None, o[-400:])
        row("CONTROL, no mode: a DELETE with no lock held is refused and the record is still there",
            re.search(r"(?m)^DELETE-REFUSED\s*$", o) is not None and re.search(r"(?m)^K2-STILL-THERE\s*$", o) is not None, o[-400:])
        o = sess(box, "RUN bp zzal_seed", "RUN bp zzal_on")
        row("$MODE AUTOLOCK: the WRITE locks the record itself and is made (K1=one)",
            re.search(r"(?m)^K1=one\s*$", o) is not None and "WRITE-REFUSED" not in o, o[-400:])
        row("$MODE AUTOLOCK: the DELETE is made as well (k2 is gone)",
            re.search(r"(?m)^K2-GONE\s*$", o) is not None and "DELETE-REFUSED" not in o, o[-400:])
        row("...and nothing is left locked after the commit", re.search(r"(?m)^LOCKS NONE\s*$", o) is not None, o[-400:])

        say("\n--- OPTION INHERIT.OWNERSHIP -------------------------------------------------------------------------")
        acct = sysd      # the sandbox session's working directory is its account
        others = [g for g in os.getgroups() if g != os.getgid()]
        grp_gid = None
        for g in others:
            try:
                if grp.getgrgid(g).gr_name not in ("root",):
                    grp_gid = g
                    break
            except KeyError:
                pass
        if grp_gid is None:
            skipped += 1
            say("  [SKIP] the sandbox user belongs to no group but its own: the ownership rows cannot be staged")
        else:
            say("    account directory %s given group %d (%s); the user's primary group is %d" % (acct, grp_gid, grp.getgrgid(grp_gid).gr_name, os.getgid()))
            os.chown(acct, -1, grp_gid)
            g1, g2 = "zzow1" + RUN, "zzow2" + RUN
            sess(box, "CREATE.FILE %s" % g1, "OPTION INHERIT.OWNERSHIP", "CREATE.FILE %s" % g2, quiet=True)

            def gids(name):
                p = os.path.join(acct, name)
                if not os.path.isdir(p):
                    return None
                found = {os.stat(p).st_gid}
                for root, dirs, files in os.walk(p):
                    for n in dirs + files:
                        found.add(os.lstat(os.path.join(root, n)).st_gid)
                return found
            a, b = gids(g1), gids(g2)
            row("CONTROL: without the option the new file is in the user's own group (%d)" % os.getgid(), a == {os.getgid()}, repr(a))
            row("with the option the file and everything in it is in the account directory's group (%d)" % grp_gid, b == {grp_gid}, repr(b))
            sess(box, "DELETE.FILE %s" % g1, "DELETE.FILE %s" % g2, quiet=True)
    finally:
        sess(box, "DELETE.FILE %s" % f, quiet=True)
        for n in made:
            for d in ("bp", "bp.out"):
                p = os.path.join(sysd, d, n)
                if os.path.exists(p):
                    os.remove(p)

    say("")
    say("sandbox-lockown: %d passed, %d failed%s" % (passed, failed, (", %d skipped" % skipped) if skipped else ""))
    if passed + failed == 0:
        bail("no row ran - a broken test, not a pass")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
