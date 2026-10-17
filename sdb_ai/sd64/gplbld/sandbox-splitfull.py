#!/usr/bin/env python3
#
# sandbox-splitfull.py - a hashed file whose split cannot be written is left whole (QM4 Fixes item 329).
#
#   gplsrc/dh_split.c advanced the file's modulus, then wrote the new group at the end of the primary subfile.  When that
#   write failed (a full disk) the modulus stayed advanced and the header was never written, so the records that hashed to
#   the new group could not be found.  dh_split() now writes the new, empty group BEFORE it advances the modulus and does
#   nothing if that cannot be done (or if the file system holds less than 1 MB), and it logs and flushes the header when
#   a split fails later.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-splitfull.py <dir> [--build]
#
# No install, no sudo.  <dir> is a sandbox made by sandbox-fromtree.py (needs a `make`d bin/sd).  With --build it is built
# first from THIS tree (it must be empty or absent).  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# A FULL DISK without root: the program runs as `sd -internal` with RLIMIT_FSIZE set and SIGXFSZ ignored, so a write past
# the limit fails with EFBIG exactly as a write to a full file system fails with ENOSPC.  A file size limit stops the
# primary subfile and the overflow subfile each at the limit; the free-space check (statvfs) cannot be driven this way.
#
# START-HISTORY:
# 16 Oct 26 dm  New.
# END-HISTORY
#
# THE INSTRUMENT.  The program reports how many writes were accepted, how many failed, and how many of the accepted
# records can be read back whole.  A write the file refused is not a loss; an accepted record that cannot be read is.
# THE CONTROL runs the same program with no limit: all 20000 accepted and read back, and the file split (modulus grew).
# The records are about 100 bytes so that the PRIMARY subfile (one group of 1 kb per modulus) reaches the limit while the
# overflow subfile still has room: with big records the overflow subfile filled first and no split was ever refused.
# THE SANDBOX MUST BE BUILT FROM THE TREE UNDER TEST.

import os
import re
import resource
import signal
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
passed = failed = 0
made = []
LIMIT = 1 << 20     # bytes: no file may grow past 1 MB in the limited run


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
    say("sandbox-splitfull: CANNOT RUN - " + msg)
    sys.exit(2)


def tool(box, *args, **kw):
    return subprocess.run([sys.executable, TOOL, box] + list(args), capture_output=True, text=True, errors="replace",
                          timeout=kw.pop("timeout", 900), **kw)


def limited():
    """In the child, before exec: no file may grow past LIMIT bytes, and a write past it fails (EFBIG) instead of killing."""
    resource.setrlimit(resource.RLIMIT_FSIZE, (LIMIT, LIMIT))
    signal.signal(signal.SIGXFSZ, signal.SIG_IGN)


def isess(box, *cmds, limit=False):
    say("    > [sd -internal%s] %d commands" % (", file size limited to %d KB" % (LIMIT // 1024) if limit else "", len(cmds)))
    env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"))
    body = "\nTERM 200,9999\n" + "".join(c + "\n" for c in cmds) + "OFF\n"
    try:
        p = subprocess.run([os.path.join(box, "sys", "bin", "sd"), "-internal"], input=body, cwd=os.path.join(box, "sys"),
                           env=env, capture_output=True, text=True, errors="replace", timeout=600,
                           preexec_fn=limited if limit else None)
    except subprocess.TimeoutExpired:
        say("    !! the session did not end in 600 seconds (a hang is a failure; the process was killed)")
        return ""
    out = ANSI.sub("", p.stdout + p.stderr)
    return re.sub(r"\x1b\[[0-9;?]*[A-Za-z]|\[[0-9;]*[A-Za-z]", "", out.split(":TERM 200,9999", 1)[-1])


MAKE = """$internal
   execute 'CREATE.FILE DATA zzsf DYNAMIC GROUP.SIZE 1 NO.QUERY' capturing junk
   open 'zzsf' to f else crt 'M[=NOT OPENED]' ; stop
   crt 'M[=MODULUS=':fileinfo(f, 5):']'
end
"""

# FL$MODULUS is key 5 of FILEINFO() (syscom keys.h).
FILL = """$internal
   open 'zzsf' to f else crt 'F[=NOT OPENED]' ; stop
   m0 = fileinfo(f, 5)
   pad = str('x', 80)
   written = 0 ; failed = 0 ; ids = ''
   for i = 1 to 20000
      id = 'R':right('0000':i, 5)
      rec = id:@fm:pad:@fm:i
      ok = 1
      write rec on f, id on error ok = 0
      if ok then
         written += 1 ; ids<-1> = id
      end else
         failed += 1
      end
   next i
   bad = 0 ; good = 0
   n = dcount(ids, @fm)
   for j = 1 to n
      id = ids<j>
      st = 0
      read r from f, id on error st = 0 then
         if field(r, @fm, 1) = id and field(r, @fm, 2) = pad then st = 1 else st = 2
      end else st = 0
      if st = 1 then good += 1 else bad += 1
   next j
   crt 'F[=WRITTEN=':written:' FAILED=':failed:' READABLE=':good:' UNREADABLE=':bad:' MOD0=':m0:' MOD1=':fileinfo(f, 5):']'
end
"""


def kv(text):
    return {k: int(v) for k, v in re.findall(r"([A-Z0-9]+)=(-?\d+)", text or "")}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-splitfull.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-splitfull: sandbox %s" % box)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = tool(box, "all")
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-splitfull: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    tool(box, "start", timeout=180)

    for nm, text in (("zzsfm", MAKE), ("zzsff", FILL)):
        with open(os.path.join(sysd, "bp", nm), "w") as f:
            f.write(text)
        made.append(nm)

    def tag(out, t):
        m = re.search(r"(?m)^%s\[=(.*)\]\s*$" % t, out)
        return m.group(1) if m else None

    try:
        say("\n--- the control: no limit, the file splits as it grows ---------------------------------")
        out = isess(box, "BASIC bp zzsfm", "BASIC bp zzsff", "DELETE.FILE zzsf", "RUN bp zzsfm", "RUN bp zzsff")
        if len(re.findall(r"(?m)^Compiled 1 program\(s\) with no errors", out)) != 2:
            bail("the programs did not compile:\n" + out[-1200:])
        m = tag(out, "M")
        say("    made: %s" % m)
        row("the instrument: the file was made and opened", m is not None and "MODULUS=" in m, "got %r" % m)
        c = kv(tag(out, "F"))
        say("    control: %s" % tag(out, "F"))
        row("CONTROL  20000 records written, all 20000 read back whole", c.get("WRITTEN") == 20000 and c.get("READABLE") == 20000
            and c.get("UNREADABLE") == 0, "got %r" % c)
        row("CONTROL  the file split as it grew (modulus %s to %s)" % (c.get("MOD0"), c.get("MOD1")),
            c.get("MOD1", 0) > c.get("MOD0", 0), "got %r" % c)

        say("\n--- the file size limit stops the primary subfile and the overflow subfile at %d KB ---------" % (LIMIT // 1024))
        out = isess(box, "DELETE.FILE zzsf", "RUN bp zzsfm", "RUN bp zzsff", limit=True)
        got = tag(out, "F")
        say("    limited: %s" % got)
        c = kv(got)
        row("the instrument: the limit bit (some writes were refused, some accepted)",
            0 < c.get("WRITTEN", 0) < 20000 and c.get("FAILED", 0) > 0, "got %r" % c)
        row("329  every record the file accepted can still be read back whole", c.get("UNREADABLE") == 0 and c.get("READABLE") == c.get("WRITTEN"),
            "got %r" % c)
        say("    modulus %s -> %s" % (c.get("MOD0"), c.get("MOD1")))
        row("329  the modulus never went past what the primary subfile can hold (%d groups of 1 kb)" % (LIMIT // 1024 - 1),
            0 < c.get("MOD1", 0) <= LIMIT // 1024 - 1, "got %r" % c)
        out = isess(box, "DELETE.FILE zzsf")
    finally:
        for nm in made:
            for d in ("bp", "bp.out"):
                p = os.path.join(sysd, d, nm)
                if os.path.exists(p):
                    os.remove(p)

    say("\nsandbox-splitfull: %d passed, %d failed" % (passed, failed))
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
