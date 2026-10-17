#!/usr/bin/env python3
#
# sandbox-sync.py - forced writes of a hashed file (QM4 Fixes item 102).  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-sync.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (needs strace; without it the rows are SKIPPED and the run exits 2).  With
# --build it is built first from THIS tree (it must be empty or absent).  Exit 0 every row passed, 1 a row failed, 2 it could not
# run.
#
# START-HISTORY:
# 16 Oct 26 dm  New.  OPEN / OPENPATH ... SYNC, FCONTROL(f, FC$SYNC, state), the S flag in field 6 of the VOC entry, FILEINFO(f,
#               FL$SYNC), and the FSYNC configuration parameter's bit 4 (every file, after every write).
# END-HISTORY
#
# THE INSTRUMENT.  A program writes 40 records to a hashed file and deletes them again, and the session runs under
# `strace -f -e trace=fsync,fdatasync`, which counts the fsync calls the process made.  The session's own fsyncs (its start, its end,
# closing the file) are the same in every variant, so the COUNT of the plain run is the baseline and a forced-write run must add at
# least one fsync per write and per delete (80).  THE CONTROLS: the plain run, a run where SYNC was asked for and then turned off with
# FCONTROL (back to the baseline), and FILEINFO(f, FL$SYNC) reading what was asked.  Each variant is a session of its own.
#
#   plain           OPEN f TO fvar                       baseline, FL$SYNC 0
#   open            OPEN f SYNC TO fvar                  baseline + 80 or more, FL$SYNC 1
#   fcontrol        FCONTROL(f, FC$SYNC, @true)          the same
#   voc             an F entry of the VOC with S in field 6, opened with a plain OPEN        the same
#   off             OPEN f SYNC, then FCONTROL(f, FC$SYNC, @false)                           baseline again
#   fsync4          sd.conf FSYNC=4 and a plain OPEN     the same as open (every file)

import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
MARK = "# --- sandbox-sync below ---"
passed = failed = 0
made = []
OPS = 80        # 40 writes and 40 deletes


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
    say("sandbox-sync: CANNOT RUN - " + msg)
    sys.exit(2)


def tool(box, *args, **kw):
    return subprocess.run([sys.executable, TOOL, box] + list(args), capture_output=True, text=True, errors="replace",
                          timeout=kw.pop("timeout", 900), **kw)


def status(box):
    env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"))
    p = subprocess.run([os.path.join(box, "sys", "bin", "sd"), "-status"], capture_output=True, text=True, errors="replace",
                       env=env, timeout=60)
    return p.stdout + p.stderr


def restart(box, *extra):
    conf = os.path.join(box, "sd.conf")
    tool(box, "stop", timeout=120)
    with open(conf) as f:
        base = f.read().split(MARK)[0].rstrip("\n") + "\n"
    with open(conf, "w") as f:
        f.write(base + ((MARK + "\n" + "".join(l + "\n" for l in extra)) if extra else ""))
    tool(box, "start", timeout=180)
    ok = re.search(r"(?m)^Started\s+20\d\d-", status(box)) is not None
    say("  -- sd.conf %s: SD %s" % (("+ " + " ".join(extra)) if extra else "as built", "started" if ok else "NOT STARTED"))
    return ok


def isess(box, cmds, trace=None):
    """A session in internal mode; with trace= the name of a file, under strace counting the fsync calls."""
    env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"))
    body = "\nTERM 200,9999\n" + "".join(c + "\n" for c in cmds) + "OFF\n"
    argv = [os.path.join(box, "sys", "bin", "sd"), "-internal"]
    if trace:
        argv = ["strace", "-f", "-e", "trace=fsync,fdatasync", "-o", trace] + argv
    p = subprocess.run(argv, input=body, cwd=os.path.join(box, "sys"), env=env, capture_output=True, text=True, errors="replace",
                       timeout=300)
    out = ANSI.sub("", p.stdout + p.stderr)
    return re.sub(r"\x1b\[[0-9;?]*[A-Za-z]|\[[0-9;]*[A-Za-z]", "", out.split(":TERM 200,9999", 1)[-1])


def fsyncs(trace):
    n = 0
    with open(trace, errors="replace") as f:
        for ln in f:
            if re.search(r"\b(fsync|fdatasync)\(", ln):
                n += 1
    return n


SETUP = """$internal
   execute 'DELETE.FILE zzsy' capturing junk
   execute 'CREATE.FILE DATA zzsy DYNAMIC NO.QUERY' capturing junk
   open 'VOC' to vf else crt 'S[=NO VOC]' ; stop
   read v from vf, 'zzsy' else crt 'S[=NO ENTRY]' ; stop
   v<6> = 'S'
   write v to vf, 'zzsys'
   crt 'S[=DONE ':v<6>:']'
end
"""

WORK = """$include keys.h
   mode = '%s'
   begin case
      case mode = 'open'
         open 'zzsy' sync to f else stop 'no file'
      case mode = 'fcontrol'
         open 'zzsy' to f else stop 'no file'
         void fcontrol(f, FC$SYNC, @true)
      case mode = 'voc'
         open 'zzsys' to f else stop 'no file'
      case mode = 'off'
         open 'zzsy' sync to f else stop 'no file'
         void fcontrol(f, FC$SYNC, @false)
      case 1
         open 'zzsy' to f else stop 'no file'
   end case
   for i = 1 to 40
      write 'record ':i to f, 'R':i
   next i
   for i = 1 to 40
      delete f, 'R':i
   next i
   crt 'W[=':mode:' SYNC=':fileinfo(f, FL$SYNC):']'
end
"""


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-sync.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-sync: sandbox %s" % box)
    if shutil.which("strace") is None:
        bail("strace is not installed: the rows count fsync calls with it")
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = tool(box, "all")
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-sync: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)

    modes = ["plain", "open", "fcontrol", "voc", "off"]
    with open(os.path.join(sysd, "bp", "zzsyset"), "w") as f:
        f.write(SETUP)
    made.append("zzsyset")
    for m in modes:
        nm = "zzsy_" + m
        with open(os.path.join(sysd, "bp", nm), "w") as f:
            f.write(WORK % m)
        made.append(nm)

    def tag(out):
        m = re.search(r"(?m)^W\[=(.*)\]\s*$", out)
        return m.group(1) if m else None

    counts = {}
    try:
        if not restart(box):
            bail("SD does not start with the sandbox's own sd.conf")
        out = isess(box, ["BASIC bp zzsyset", "RUN bp zzsyset"] + ["BASIC bp zzsy_" + m for m in modes])
        if not re.search(r"(?m)^S\[=DONE S\]", out) or len(re.findall(r"(?m)^Compiled 1 program\(s\) with no errors", out)) != 6:
            bail("the setup did not work:\n" + out[-1200:])

        say("\n--- fsync calls of a session that writes 40 records and deletes them -------------------------------------------")
        for m in modes:
            trace = os.path.join(box, "strace-%s.out" % m)
            out = isess(box, ["RUN bp zzsy_" + m], trace=trace)
            counts[m] = fsyncs(trace)
            say("    %-9s %4d fsync calls   %s" % (m, counts[m], tag(out)))
            os.remove(trace)
            counts[m + "_tag"] = tag(out)
        base = counts["plain"]
        row("the instrument: every variant ran its program to the end", all(counts[m + "_tag"] for m in modes), repr({m: counts[m + "_tag"] for m in modes}))
        row("CONTROL  a plain OPEN: FL$SYNC 0", counts["plain_tag"] == "plain SYNC=0", repr(counts["plain_tag"]))
        row("102  OPEN ... SYNC: FL$SYNC 1, and at least one fsync for each of the %d writes and deletes (%d against the baseline %d)" % (OPS, counts["open"], base),
            counts["open_tag"] == "open SYNC=1" and counts["open"] >= base + OPS, repr((counts["open_tag"], counts["open"], base)))
        row("102  FCONTROL(f, FC$SYNC, @true) on a plain OPEN: FL$SYNC 1 and the same (%d)" % counts["fcontrol"],
            counts["fcontrol_tag"] == "fcontrol SYNC=1" and counts["fcontrol"] >= base + OPS, repr((counts["fcontrol_tag"], counts["fcontrol"], base)))
        row("102  an F entry of the VOC with S in field 6, opened by a plain OPEN: FL$SYNC 1 and the same (%d)" % counts["voc"],
            counts["voc_tag"] == "voc SYNC=1" and counts["voc"] >= base + OPS, repr((counts["voc_tag"], counts["voc"], base)))
        row("CONTROL  SYNC asked for and turned off with FCONTROL: FL$SYNC 0 and back to the baseline (%d against %d)" % (counts["off"], base),
            counts["off_tag"] == "off SYNC=0" and counts["off"] < base + OPS // 4, repr((counts["off_tag"], counts["off"], base)))

        say("\n--- FSYNC=4 in sd.conf: every file, after every write -------------------------------------------------------")
        if not restart(box, "FSYNC=4"):
            bail("SD does not start with FSYNC=4")
        trace = os.path.join(box, "strace-fsync4.out")
        out = isess(box, ["RUN bp zzsy_plain"], trace=trace)
        n4 = fsyncs(trace)
        os.remove(trace)
        say("    fsync4    %4d fsync calls   %s" % (n4, tag(out)))
        row("102  FSYNC=4 syncs a file that was opened plainly (%d against the baseline %d); FL$SYNC stays 0, being the file's own" % (n4, base),
            n4 >= base + OPS and tag(out) == "plain SYNC=0", repr((n4, base, tag(out))))
    finally:
        restart(box)
        for nm in made:
            for d in ("bp", "bp.out"):
                p = os.path.join(sysd, d, nm)
                if os.path.exists(p):
                    os.remove(p)
        isess(box, ["DELETE.FILE zzsy"])

    say("\nsandbox-sync: %d passed, %d failed" % (passed, failed))
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
