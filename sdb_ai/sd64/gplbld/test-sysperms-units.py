#!/usr/bin/env python3
#
# test-sysperms-units.py - prove verify-sysperms.py's probes cannot damage what
#                          they measure.  PORT_ADOPTION queue 22, item 7.
#
#   python3 /home/don/Projects/sdcore4linux/sdb_ai/sd64/gplbld/test-sysperms-units.py
#
# No sudo, no install, no sd.  Exit 0 all cases passed, 1 a case failed.
#
# ***THIS EXISTS FOR ONE PROPERTY, AND IT IS THE ONE THAT WOULD BE
# CATASTROPHIC RATHER THAN MERELY WRONG.***  verify-sysperms asks "can I write
# this?" by TRYING - that is the port's rule and the reason the mode bits are
# not trusted - and it asks it of `bin/sd`, `bin/pcode` and `bin/libsdcli.so`.
# A probe that answered correctly while truncating the interpreter would pass
# its own run and take the system down with it.  So file_writable() opens in
# APPEND mode and writes nothing, and cases 1-6 prove that leaves the content,
# the length AND the mtime untouched - on a file it CAN write, which is the
# only case where damage is possible at all.
#
# ***THE SECOND PROPERTY IS THAT A PROBE LEAVES NOTHING BEHIND.***  A stray
# .zzsysperms-probe in $IPC or prt would be litter in a live system directory,
# and in $IPC it sits beside the files every session reads.  Cases 7-10.
#
# The refusal paths are tested too (cases 11-13): a probe that returned False
# because of a BUG rather than a permission would report a locked system that
# is in fact wide open - the direction that fails quietly.
#
import os
import stat
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import importlib.util                                    # noqa: E402
_spec = importlib.util.spec_from_file_location(
    "verify_sysperms", os.path.join(HERE, "verify-sysperms.py"))
VS = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(VS)

FAILS = []
CASES = [0]


def ck(name, got, want):
    CASES[0] += 1
    if got != want:
        FAILS.append("%s:\n      got  %r\n      want %r" % (name, got, want))
        print("  FAIL %s" % name)
    else:
        print("  pass %s" % name)


def main():
    tmp = tempfile.mkdtemp(prefix="zzsysperms-units-")

    print("--- file_writable(): it must not change a byte ---")

    target = os.path.join(tmp, "interpreter")
    CONTENT = b"\x7fELF pretend this is bin/sd\n\x00\x01\x02"
    with open(target, "wb") as f:
        f.write(CONTENT)
    # Backdate it so a probe that touched the file would move the mtime
    # measurably rather than within a timer's resolution.
    old = time.time() - 10000
    os.utime(target, (old, old))
    before_mtime = os.stat(target).st_mtime
    before_size = os.stat(target).st_size

    ok, detail = VS.file_writable(target)
    ck("1 a writable file reports writable", ok, True)
    ck("2 ... and the content is byte-for-byte unchanged",
       open(target, "rb").read(), CONTENT)
    ck("3 ... and the length is unchanged", os.stat(target).st_size, before_size)
    # ***THE ONE THAT MATTERS MOST.***  Append mode must not even mark the file
    # as touched; anything that moved the mtime would mean something was
    # written.
    ck("4 ... and the mtime did not move", os.stat(target).st_mtime, before_mtime)

    empty = os.path.join(tmp, "empty")
    open(empty, "wb").close()
    ok, _ = VS.file_writable(empty)
    ck("5 an empty writable file reports writable", ok, True)
    ck("6 ... and is still empty", os.stat(empty).st_size, 0)

    print("--- dir_writable(): it must leave nothing behind ---")

    d = os.path.join(tmp, "spool")
    os.mkdir(d)
    before = sorted(os.listdir(d))
    ok, detail = VS.dir_writable(d)
    ck("7 a writable directory reports writable", ok, True)
    ck("8 ... and the directory is exactly as it was",
       sorted(os.listdir(d)), before)
    ck("9 ... and the probe name is gone specifically",
       VS.PROBE in os.listdir(d), False)

    populated = os.path.join(tmp, "ipc")
    os.mkdir(populated)
    for n in ("%0", "%1"):
        with open(os.path.join(populated, n), "wb") as f:
            f.write(b"session state")
    VS.dir_writable(populated)
    ck("10 an existing file beside the probe is untouched",
       open(os.path.join(populated, "%0"), "rb").read(), b"session state")

    print("--- the refusal paths: False must mean 'refused', not 'bug' ---")

    ro = os.path.join(tmp, "readonly")
    os.mkdir(ro)
    os.chmod(ro, 0o555)
    ok, detail = VS.dir_writable(ro)
    ck("11 an unwritable directory reports refused", ok, False)
    ck("12 ... and says why, in the OS's own words",
       "denied" in detail.lower(), True)

    rof = os.path.join(tmp, "readonly.bin")
    with open(rof, "wb") as f:
        f.write(b"x")
    os.chmod(rof, 0o444)
    ok, _ = VS.file_writable(rof)
    ck("13 an unwritable file reports refused", ok, False)

    unreadable = os.path.join(tmp, "audit")
    with open(unreadable, "wb") as f:
        f.write(b"secret")
    os.chmod(unreadable, 0o220)
    ok, _ = VS.file_readable(unreadable)
    ck("14 a write-only file reports NOT readable", ok, False)
    ok, _ = VS.file_readable(rof)
    ck("15 ... while a readable one does", ok, True)

    print("--- describe(): diagnosis, and it must never raise ---")

    ck("16 it reports owner:group and a four-digit mode",
       bool(__import__("re").match(r"^\S+:\S+ \d{4}$", VS.describe(rof))), True)
    ck("17 a missing path is described, not raised",
       VS.describe(os.path.join(tmp, "nosuch")).startswith("(cannot stat"), True)
    ck("18 the mode it prints is the real one",
       VS.describe(rof).split()[-1],
       "%04o" % stat.S_IMODE(os.stat(rof).st_mode))

    print("--- my_groups() ---")

    g = VS.my_groups()
    ck("19 it returns a non-empty set of names", len(g) > 0, True)
    ck("20 ... including the caller's primary group",
       __import__("grp").getgrgid(os.getgid()).gr_name in g, True)

    # Tidy up: chmod back first, or the read-only directory cannot be removed.
    for p in (ro, rof, unreadable):
        try:
            os.chmod(p, 0o700)
        except OSError:
            pass
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)

    print("")
    print("test-sysperms-units: %d cases, %d failed" % (CASES[0], len(FAILS)))
    for f in FAILS:
        print("  FAIL %s" % f)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
