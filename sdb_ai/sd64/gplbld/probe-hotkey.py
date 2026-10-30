#!/usr/bin/env python3
#
# probe-hotkey.py - S.84: how much does ONE online write cost when the index key it touches already holds many ids?  A MEASUREMENT, not a test: it changes no program,
# prints a table and exits 0 (2 when it cannot run).  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/probe-hotkey.py <dir> [--build] [--sizes=10000,50000,100000] [--control=100000]
#
# <dir> is a sandbox made by sandbox-fromtree.py (it must be empty or absent with --build).  Run it with SDBOX_KEYSET=n set, as the suites are.
#
# START-HISTORY:
# 30 Oct 26 dm  New.  S.84's first step ("MEASURE FIRST: online writes into an index whose key holds 10k, 50k and 100k ids"), written from sandbox-akdeep.py's harness.
# END-HISTORY
#
# WHAT IT MEASURES.  For each size S: a file of S records that ALL carry the same value 'HOT' in field 1 is loaded with no index (fast), an index VAL on field 1 is created
# and BUILT from the file (the time is printed: a hot key may make the BUILD itself slow), and then records are written and deleted ONE AT A TIME with the index kept by
# the writes, in two batches of different sizes (100 and 400).  The cost of one write is (time of the batch of 400 - time of the batch of 100) / 300: the
# fixed cost of starting a session cancels.  The same is done for the deletes.  The CONTROL is the same file size with a DIFFERENT value in every record (so every key
# holds one id): if a write costs about the same there at S = 100000 as at S = 10000, the file size is not the cost and the list length is.
#
# THE INSTRUMENT SHOWS WHAT IT DID: every program prints the number of changes it made ('DONE[n]') and the file's record count afterwards; a batch that made fewer
# changes than it should makes the probe say so and leave that cell out.  It reads nothing back about the INDEX's contents (sandbox-akdeep.py is the test of that).

import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
RUN = "%05d" % (os.getpid() % 100000)
F = "zzhk" + RUN
SMALL, BIG = 100, 400


def say(s=""):
    print(s, flush=True)


def bail(msg):
    say("probe-hotkey: CANNOT RUN - " + msg)
    sys.exit(2)


def sess(box, *cmds, timeout=3600):
    p = subprocess.run([sys.executable, TOOL, box, "sess", os.path.join(box, "user_accounts")] + list(cmds),
                       capture_output=True, text=True, errors="replace", timeout=timeout)
    out = ANSI.sub("", p.stdout + p.stderr)
    return out.split(":TERM 200,9999", 1)[-1]


def timed(box, *cmds, timeout=3600):
    t0 = time.monotonic()
    try:
        out = sess(box, *cmds, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, "TIMEOUT after %d s" % timeout
    return time.monotonic() - t0, out


PROG_LOAD = """   open '%(f)s' to f else stop 'no file'
   open 'DICT %(f)s' to d else stop 'no dict'
   write 'D':@fm:'1':@fm:'':@fm:'Val':@fm:'9L':@fm:'S' on d, 'VAL'
   for i = 1 to %(n)d
      write %(val)s on f, 'r':i
   next i
   nrec = 0
   select f
   loop
      readnext id else exit
      nrec += 1
   repeat
   crt 'LOADED[':%(n)d:'] RECORDS[':nrec:']'
end
"""

# How many ids the index holds for the hot value, and how many records the file holds: the fixture's own control (a probe that times a fixture it did not check is worth nothing).
PROG_COUNT = """   open '%(f)s' to f else stop 'no file'
   selectindex 'VAL', 'HOT' from f to 5
   readlist l from 5 else l = ''
   ni = dcount(l, @fm)
   if l = '' then ni = 0
   nrec = 0
   select f
   loop
      readnext id else exit
      nrec += 1
   repeat
   crt 'IDS[':ni:'] RECORDS[':nrec:']'
end
"""

PROG_CHANGE = """   open '%(f)s' to f else stop 'no file'
   nd = 0
   for i = %(a)d to %(b)d
      %(op)s
      nd += 1
   next i
   crt 'DONE[':nd:']'
end
"""


def prog_change(op, a, b, val):
    stmt = {"put": "write %s on f, 'r':i" % val, "del": "delete f, 'r':i"}[op]
    return PROG_CHANGE % {"f": F, "a": a, "b": b, "op": stmt}


def measure_size(box, sysd, n, hot, label):
    """one table row: build time, ms per online write, ms per online delete (None where a batch was short)"""
    val = "'HOT'" if hot else "'v':('0000000':i)[8]"
    wval = "'HOT'" if hot else "'w':('0000000':i)[8]"
    progs = {"zzhkl": PROG_LOAD % {"f": F, "n": n, "val": val}}
    a1, b1 = n + 1, n + SMALL
    a2, b2 = n + SMALL + 1, n + SMALL + BIG
    progs["zzhkw1"] = prog_change("put", a1, b1, wval)
    progs["zzhkw2"] = prog_change("put", a2, b2, wval)
    progs["zzhkd1"] = prog_change("del", a1, b1, wval)
    progs["zzhkd2"] = prog_change("del", a2, b2, wval)
    progs["zzhkc"] = PROG_COUNT % {"f": F}
    for nm, body in progs.items():
        with open(os.path.join(sysd, "bp", nm), "w") as fh:
            fh.write(body)
    out = sess(box, "DELETE.FILE %s" % F, "CREATE.FILE %s" % F, *["BASIC bp %s" % nm for nm in progs])
    if len(re.findall(r"(?m)^Compiled 1 program\(s\) with no errors", out)) != len(progs):
        bail("the probe programs did not compile:\n" + out[-500:])
    t, out = timed(box, "RUN bp zzhkl")
    m = re.search(r"(?m)^LOADED\[(\d+)\] RECORDS\[(\d+)\]", out) if t is not None else None
    if not m or int(m.group(1)) != n or int(m.group(2)) != n:
        bail("%s: the file was not loaded (%s)" % (label, "no answer" if t is None else out[-300:]))
    say("  %s: %d records loaded in %.1f s" % (label, n, t))
    tb, out = timed(box, "CREATE.INDEX %s VAL" % F, "BUILD.INDEX %s VAL" % F)
    if tb is None:
        say("  %s: BUILD.INDEX %s" % (label, out))
        return {"label": label, "n": n, "build": None, "w": None, "d": None}
    say("  %s: CREATE.INDEX + BUILD.INDEX took %.1f s" % (label, tb))
    res = {"label": label, "n": n, "build": tb, "ids": None}

    def count(tag, want_ids):
        t, o = timed(box, "RUN bp zzhkc")
        mm = re.search(r"(?m)^IDS\[(\d+)\] RECORDS\[(\d+)\]", o) if t is not None else None
        if not mm:
            say("  %s: %s: the count printed nothing" % (label, tag))
            return None
        ids, recs = int(mm.group(1)), int(mm.group(2))
        flag = "" if (want_ids is None or ids == want_ids) else "   <== THE INDEX HOLDS %d IDS, THE FILE %d RECORDS: the fixture or the index is wrong" % (ids, recs)
        say("  %s: %s: the index holds %d ids for the value, the file %d records%s" % (label, tag, ids, recs, flag))
        return ids

    res["ids"] = count("after BUILD.INDEX", n if hot else None)
    times = {}
    for nm, want in (("zzhkw1", SMALL), ("zzhkw2", BIG), ("zzhkd1", SMALL), ("zzhkd2", BIG)):
        t, out = timed(box, "RUN bp %s" % nm)
        m = re.search(r"(?m)^DONE\[(\d+)\]", out) if t is not None else None
        if t is None or not m or int(m.group(1)) != want:
            say("  %s: %s made %s changes, wanted %d (%s)" % (label, nm, m.group(1) if m else "NO", want, "timeout" if t is None else "short batch"))
            times[nm] = None
        else:
            times[nm] = t
            say("  %s: %s %d changes in %.2f s" % (label, nm, want, t))
        if nm == "zzhkw2":
            res["ids_after_writes"] = count("after the 500 writes", n + SMALL + BIG if hot else None)
    res["ids_end"] = count("after the 500 deletes", n if hot else None)
    for key, (small, big) in (("w", ("zzhkw1", "zzhkw2")), ("d", ("zzhkd1", "zzhkd2"))):
        res[key] = None if times[small] is None or times[big] is None else (times[big] - times[small]) / (BIG - SMALL) * 1000.0
    return res


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: probe-hotkey.py <dir> [--build] [--sizes=10000,50000,100000] [--control=100000]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    sizes = [10000, 50000, 100000]
    control = 100000
    for a in sys.argv[1:]:
        if a.startswith("--sizes="):
            sizes = [int(x) for x in a[8:].split(",") if x]
        if a.startswith("--control="):
            control = int(a[10:])
    say("probe-hotkey: sandbox %s  tree %s  file %s  sizes %s  control %d" % (box, os.path.dirname(HERE), F, sizes, control))
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=1800)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("probe-hotkey: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)
    rows = []
    try:
        for n in sizes:
            say("\n--- HOT KEY: %d records, every one carries the same value in field 1 ---------------------------------" % n)
            rows.append(measure_size(box, sysd, n, True, "hot %d" % n))
        say("\n--- CONTROL: %d records, a different value in every record (every key holds one id) -------------------" % control)
        rows.append(measure_size(box, sysd, control, False, "unique %d" % control))
    finally:
        sess(box, "DELETE.FILE %s" % F)
        for nm in ("zzhkl", "zzhkw1", "zzhkw2", "zzhkd1", "zzhkd2", "zzhkc"):
            for d in ("bp", "bp.out"):
                p = os.path.join(sysd, d, nm)
                if os.path.exists(p):
                    os.remove(p)
        subprocess.run([sys.executable, TOOL, box, "stop"], capture_output=True, text=True, errors="replace", timeout=120)
    say("\nprobe-hotkey: RESULT (ms per ONE online change with the index kept by the write; BUILD in seconds)")
    say("  %-18s %10s %12s %14s %14s %24s" % ("case", "records", "BUILD s", "write ms", "delete ms", "ids: built/+500/-500"))
    for r in rows:
        f = lambda v, w=1: "n/a" if v is None else ("%.*f" % (w, v))
        say("  %-18s %10d %12s %14s %14s %24s" % (r["label"], r["n"], f(r["build"]), f(r["w"], 2), f(r["d"], 2),
                                               "%s/%s/%s" % (r.get("ids"), r.get("ids_after_writes"), r.get("ids_end"))))
    say("probe-hotkey: done (a measurement; no verdict)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
