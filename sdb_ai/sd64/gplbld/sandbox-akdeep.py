#!/usr/bin/env python3
#
# sandbox-akdeep.py - deleting records from a LARGE index (three tree levels) must leave every other key findable.  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-akdeep.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or absent); without it <dir> must
# already be built, which is how the same script is run against an OLD tree to prove it can fail.  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 25 Oct 26 dm  Written for the defect the Kimi / DeepSeek audit of the index code reported and a probe measured: deleting the highest 3,000 of 120,000 records
#               left an index that still listed 119,846 keys and could not find two surviving records (v0110000, v0116999), because update_internal_node()
#               told the parent "no key" when it removed the LAST child of a node that had others, and the parent read that as "remove this node" (a whole
#               subtree vanished from every lookup).  The same function copied the only child of a node over the node without telling the neighbours of a
#               child that was a terminal node (the chain of terminal nodes led into the free list).  Fixed in dh_ak.c (update_internal_node(), relink_term_neighbours()).
# END-HISTORY
#
# WHAT IT MEASURES.  A file with 60,000 records (ids r1..r60000, field 1 'v0000001'..'v0060000' in step, so every key is different and the index has three
# levels: several hundred terminal nodes, several internal nodes under the root).  An index VAL on field 1 is BUILT.  Then, each scenario starting from an index
# BUILT again from the file as it then is, records are deleted or written ONE AT A TIME (the index is kept by the writes) and the index is compared with the FILE:
#   A the highest 1,500 records          the rightmost terminal nodes of the whole tree (the original fault)
#   B 25,000 records from the middle     whole internal nodes of the lowest level emptied, a node left with one terminal child
#   C the lowest 2,500 records           the leftmost terminal nodes
#   D 600 records written back           inserts into a tree that has lost nodes, and past the old maximum
#   E everything except those 600        the tree shrinks, levels are taken away
#   F the 600, then 300 new ones         an index emptied completely and filled again
#   G all 60,000 back, all but three deleted from the left     a lowest-level node loses leaf after leaf until ONE is left, which is copied over it
#   H the same, from the right           (the neighbours of that terminal node must be told its new node number)
# THE ORACLE IS THE FILE, not a model: after each scenario (1) SELECTINDEX VAL (all values, in the index's own order) must equal the field 1 of every record that
# exists, in key order, (2) the same keys walked from the right (SETRIGHT, SELECTLEFT: the left links of the terminal nodes) must come out in the reverse order, and
# (3) a lookup of each 11th key (SELECTINDEX VAL, value) must answer exactly that record's id, or nothing when the record is gone.
# Row S0 is the control that the fixture and the printing work: the freshly BUILT index must pass both tests, with the file holding 60,000 records; if it does not
# the run stops with exit 2 and no verdict.  The final row builds the index again from the file and checks it with the same program: an index built from the file
# must pass, or the instrument is wrong.  Every row also requires the number of records the file holds to be the number the scenario should have left (a
# scenario whose deletes did nothing must not pass).

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
RUN = "%05d" % (os.getpid() % 100000)
F = "zzdp" + RUN
N = 60000
passed = failed = 0


def say(s=""):
    print(s, flush=True)


def row(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        say("  [PASS] " + name)
    else:
        failed += 1
        say("  [FAIL] " + name + ("   <- " + detail if detail else ""))


def bail(msg):
    say("sandbox-akdeep: CANNOT RUN - " + msg)
    sys.exit(2)


def sess(box, *cmds):
    say("    > " + " | ".join(cmds))
    p = subprocess.run([sys.executable, TOOL, box, "sess", os.path.join(box, "user_accounts")] + list(cmds),
                       capture_output=True, text=True, errors="replace", timeout=1800)
    out = ANSI.sub("", p.stdout + p.stderr)
    return out.split(":TERM 200,9999", 1)[-1]


def key(i):
    return "v%07d" % i


PROG_LOAD = """   open '%(f)s' to f else stop 'no file'
   open 'DICT %(f)s' to d else stop 'no dict'
   write 'D':@fm:'1':@fm:'':@fm:'Val':@fm:'9L':@fm:'S' on d, 'VAL'
   for i = 1 to %(n)d
      write 'v':('000000':i)[7] on f, 'r':i
   next i
   crt 'LOADED[':%(n)d:']'
end
"""

# The check.  ex is every key the FILE holds, in key order (the ids run in key order); res is the index's own list; the lookups are every 11th key.
PROG_CHECK = """   open '%(f)s' to f else stop 'no file'
   ex = ''
   exr = ''
   nf = 0
   for i = 1 to %(n)d
      read rec from f, 'r':i then
         ex := rec<1>:@fm
         nf += 1
      end
   next i
   for i = %(n)d to 1 step -1
      read rec from f, 'r':i then exr := rec<1>:@fm
   next i
   selectindex 'VAL' from f to 5
   readlist l from 5 else l = ''
   ni = dcount(l, @fm)
   if l = '' then ni = 0
   res = 'BAD'
   if nf = 0 then
      if ni = 0 then res = 'OK'
   end else
      if l:@fm = ex then res = 'OK'
   end
   * the same keys walked from the right by the left links of the terminal nodes
   setright 'VAL' from f
   rv = ''
   loop
      selectleft 'VAL' from f setting kv to 6
      readlist l3 from 6 else l3 = ''
   until l3 = '' do
      rv := kv:@fm
   repeat
   rres = 'BAD'
   if rv = exr then rres = 'OK'
   bad = 0
   tested = 0
   for i = 11 to %(n)d step 11
      read rec from f, 'r':i then want = 'r':i else want = ''
      selectindex 'VAL', 'v':('000000':i)[7] from f to 5
      readlist l2 from 5 else l2 = ''
      tested += 1
      if l2 # want then
         bad += 1
         if bad <= 3 then crt 'BADLOOK ':i:' want [':want:'] got [':l2:']'
      end
   next i
   crt 'CHK[%(tag)s scan=':res:' back=':rres:' idx=':ni:' file=':nf:' badlook=':bad:' of ':tested:']'
end
"""


def prog_changes(ops):
    """ops: ('del', a, b) deletes ids a..b in that direction; ('put', a, b) writes them with their own key"""
    out = "   open '%s' to f else stop 'no file'\n   nd = 0\n" % F
    for kind, a, b in ops:
        step = " step -1" if b < a else ""
        out += "   for i = %d to %d%s\n" % (a, b, step)
        if kind == "del":
            out += "      delete f, 'r':i\n"
        else:
            out += "      write 'v':('000000':i)[7] on f, 'r':i\n"
        out += "      nd += 1\n   next i\n"
    out += "   crt 'DONE[':nd:']'\nend\n"
    return out


# name, what it does, operations, records the file should hold afterwards, whether all 60,000 records are written back first
SCENARIOS = [
    ("A", "the highest 1,500 records deleted", [("del", 60000, 58501)], 58500, False),
    ("B", "25,000 records deleted from the middle", [("del", 15001, 40000)], 33500, False),
    ("C", "the lowest 2,500 records deleted", [("del", 1, 2500)], 31000, False),
    ("D", "600 records written back (inserts into a tree that has lost nodes, and past the old maximum)", [("put", 15001, 15300), ("put", 59001, 59300)], 31600, False),
    ("E", "everything deleted except those 600 (the tree loses its levels)", [("del", 2501, 15000), ("del", 58500, 40001)], 600, False),
    ("F", "the 600 deleted (an index emptied), then 300 new records written", [("del", 15001, 15300), ("del", 59001, 59300), ("put", 30001, 30300)], 300, False),
    ("G", "all 60,000 back, then all but r20000, r40000 and r60000 deleted from the left (each lowest node is left with one terminal node)",
     [("del", 1, 19999), ("del", 20001, 39999), ("del", 40001, 59999)], 3, True),
    ("H", "all 60,000 back, then all but the same three deleted from the right",
     [("del", 59999, 40001), ("del", 39999, 20001), ("del", 19999, 1)], 3, True),
]


def parse(out, tag):
    m = re.search(r"(?m)^CHK\[%s scan=(OK|BAD) back=(OK|BAD) idx=(\d+) file=(\d+) badlook=(\d+) of (\d+)\]" % tag, out)
    if not m:
        return None
    return {"scan": m.group(1), "back": m.group(2), "idx": int(m.group(3)), "file": int(m.group(4)), "bad": int(m.group(5)), "tested": int(m.group(6))}


def verdict(r, want_file):
    if r is None:
        return False, "the check printed nothing"
    ok = r["scan"] == "OK" and r["back"] == "OK" and r["bad"] == 0 and r["file"] == want_file and r["tested"] > 0
    return ok, "scan right %s, scan left %s (index lists %d keys, file holds %d, wanted %d), %d of %d lookups wrong" % (
        r["scan"], r["back"], r["idx"], r["file"], want_file, r["bad"], r["tested"])


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-akdeep.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-akdeep: sandbox %s" % box)
    say("sandbox-akdeep: tree    %s" % os.path.dirname(HERE))
    say("sandbox-akdeep: file    %s, %d records" % (F, N))
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=1800)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-akdeep: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    ctx = {"f": F, "n": N}
    progs = {"zzdpl": PROG_LOAD % ctx, "zzdpr": prog_changes([("put", 1, N)]), "zzdpc0": PROG_CHECK % dict(ctx, tag="S0"), "zzdpcz": PROG_CHECK % dict(ctx, tag="Z")}
    for sc, _, ops, _, _ in SCENARIOS:
        progs["zzdp" + sc.lower()] = prog_changes(ops)
        progs["zzdpc" + sc.lower()] = PROG_CHECK % dict(ctx, tag=sc)
    for nm, body in progs.items():
        with open(os.path.join(sysd, "bp", nm), "w") as fh:
            fh.write(body)
    try:
        say("\n--- the fixture: %d records, an index VAL BUILT from them ------------------------------------" % N)
        out = sess(box, "DELETE.FILE %s" % F, "CREATE.FILE %s" % F, *["BASIC bp %s" % nm for nm in progs])
        clean = len(re.findall(r"(?m)^Compiled 1 program\(s\) with no errors", out))
        row("setup: the %d programs compiled with no errors" % len(progs), clean == len(progs), "clean compiles: %d of %d" % (clean, len(progs)))
        if clean != len(progs):
            bail("the programs did not compile - nothing below would read an index:\n" + out[-600:])
        out = sess(box, "RUN bp zzdpl")
        m = re.search(r"(?m)^LOADED\[(\d+)\]", out)
        if not m or int(m.group(1)) != N:
            bail("the file was not loaded:\n" + out[-600:])
        out = sess(box, "CREATE.INDEX %s VAL" % F, "BUILD.INDEX %s VAL" % F, "RUN bp zzdpc0")
        r0 = parse(out, "S0")
        for ln in re.findall(r"(?m)^BADLOOK.*$", out):
            say("    " + ln)
        ok, why = verdict(r0, N)
        if not ok:
            bail("the control step S0 (a freshly BUILT index, %d records) is not clean - the fixture or the printing is wrong, so no verdict would mean anything: %s\n%s" % (N, why, out[-500:]))
        row("S0 (control): the index built from the file lists every key and answers every lookup (%s)" % why, True)

        for sc, what, ops, want, reload in SCENARIOS:
            say("\n--- %s: %s ------------------------------------------------------------" % (sc, what))
            if reload:
                sess(box, "RUN bp zzdpr")
            out = sess(box, "BUILD.INDEX %s VAL" % F, "RUN bp zzdp%s" % sc.lower(), "RUN bp zzdpc%s" % sc.lower())
            m = re.search(r"(?m)^DONE\[(\d+)\]", out)
            say("    changes made one at a time: %s" % (m.group(1) if m else "NOT PRINTED"))
            for ln in re.findall(r"(?m)^BADLOOK.*$", out):
                say("    " + ln)
            ok, why = verdict(parse(out, sc), want)
            row("%s: %s - the index says what the file says" % (sc, what), ok and m is not None, why)

        say("\n--- Z: the index built again from the file, checked by the same program (the instrument's own control) --------")
        out = sess(box, "BUILD.INDEX %s VAL" % F, "RUN bp zzdpcz")
        ok, why = verdict(parse(out, "Z"), SCENARIOS[-1][3])
        row("Z (control): an index BUILT from the file passes the same check", ok, why)
    finally:
        say("\n--- cleanup -------------------------------------------------------------------------------------")
        sess(box, "DELETE.FILE %s" % F)
        for nm in progs:
            for d in ("bp", "bp.out"):
                pth = os.path.join(sysd, d, nm)
                if os.path.exists(pth):
                    os.remove(pth)
        left = [nm for nm in progs if any(os.path.exists(os.path.join(sysd, d, nm)) for d in ("bp", "bp.out"))]
        row("cleanup: the fixture programs are gone", not left, " ".join(left))

    say("\nsandbox-akdeep: %d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        bail("no row ran - a broken test, not a pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
