#!/usr/bin/env python3
#
# sandbox-sortord.py - the sort gives the order it always gave, and no longer takes minutes on equal or ordered keys
#                      (20 Oct 2026, the sort and hash visit).
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-sortord.py <dir> [--build] [--record]
#
# No install, no sudo.  <dir> is a sandbox made by sandbox-fromtree.py (needs a `make`d bin/sd).  With --build it is built first
# from THIS tree (it must be empty or absent).  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 20 Oct 26 dm  New.  gplsrc/op_sort.c collects the nodes of a run in arrival order and sorts them once instead of walking an
#               unbalanced tree node by node.  100,000 equal keys took 168 s, 100,000 ordered keys 169 s, SELECT file BY a field
#               of five values 94 s (measured on the tree before the change; the report is sorthash-phase1-report.md).
# 25 Oct 26 dm  The disk rows of every case but c10 are held to the IN-MEMORY golden value (SPILL_EQ below): gplsrc/op_sort.c merge_sort_files() keeps the queue
#               of runs in the order they arrived, so a sort that spills gives the order the same sort gives in memory.  Before, 9 of the 22 disk golden values
#               (c01 c05 c08 c12 c15 c16 c17 t01 t03) differed from the memory ones: equal keys came out in an order that depended on SORTMEM and SORTMRG.
# END-HISTORY
#
# WHAT IT HOLDS THE NEW SORT TO.  GOLDEN is the MD5 of the whole output of each case (the data items in the order the sort gave
# them, and the keys), recorded with --record from a sandbox built from the tree BEFORE the change (HEAD 680747d).  So every
# MATCH row says "the new kernel gave, byte for byte, what the old kernel gave" - for random, ordered, reversed, all equal, few
# distinct, right justified (integers, decimals, negatives, descending), two keys, null keys, UNIQUE, and a right justified
# level that mixes numbers and text (where the comparison is not transitive and the old tree's shape decides the order), in
# memory and with SORTMEM=64 kb and SORTMRG=3 so that the runs spill and are merged.  The data item of every record is its
# arrival number, so the order of equal keys is part of what is compared.
# The TIME rows run 60,000 equal, ordered and few-valued keys and want each under THREE SECONDS: the old kernel needed 6-12 s
# for them (red on HEAD 680747d), the new one a fraction of a second.  A row that does not finish in 120 s is a FAIL, not a hang.
#
# THE INSTRUMENT.  Each program prints  TAG[=N=<items> MD=<md5 of the data> MK=<md5 of the keys> T=<ms of the SORTADDs>]  and a
# row passes only on the wording it prints when it ran to the end; a missing line is a FAIL, never a pass.  The programs are
# INTERNAL ones (SORTINIT / SORTADD / SORTDATA() / SORTNEXT() are restricted), run through `sd -internal` as sandbox-sortwide.py
# runs them.

import hashlib
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
MARK = "# --- sandbox-sortord below ---"
passed = failed = 0
made = []

# tag -> (N, retrieval, key code, modes, time limit ms or None)
#   modes: BT flags of SORTINIT, one per key: 1 right justified, 2 descending, 4 unique, 8 data (first key)
#   key code: BASIC that sets keys(1).. from i (1..N), n, r and r2 (two Park-Miller streams)
PAD7 = "'K':(str('0',7):%s)[7]"
CASES = {
    "c01": (20000, "data", "keys(1) = " + PAD7 % "mod(r,10000000)", [8], None),
    "c02": (20000, "data", "keys(1) = " + PAD7 % "i", [8], None),
    "c03": (20000, "data", "keys(1) = " + PAD7 % "n+1-i", [8], None),
    "c04": (20000, "data", "keys(1) = 'SAME'", [8], None),
    "c05": (20000, "data", "keys(1) = 'V':mod(r,5)", [8], None),
    "c06": (20000, "data", "keys(1) = mod(r,1000000)+1", [9], None),
    "c07": (20000, "data", "keys(1) = (mod(r,200001)-100000)/100", [9], None),
    "c08": (20000, "data", "keys(1) = mod(r,5)+1", [9], None),
    "c09": (20000, "data", "keys(1) = mod(r,1000000)+1", [11], None),
    "c10": (3000, "data", "m = mod(r,6)\n      begin case\n         case m = 0 ; keys(1) = '1x'\n         case m = 1 ; keys(1) = '11'\n"
                          "         case m = 2 ; keys(1) = '0010'\n         case m = 3 ; keys(1) = 'N/A'\n"
                          "         case 1 ; keys(1) = mod(r,40)\n      end case", [9], None),
    "c11": (20000, "data", "keys(1) = 'V':mod(r,50)\n      keys(2) = " + PAD7 % "mod(r2,10000000)", [8, 0], None),
    "c12": (20000, "next", "keys(1) = 'V':mod(r,5)\n      keys(2) = mod(r2,100000)+1", [8, 3], None),
    "c13": (20000, "data", "keys(1) = 'SAME'\n      keys(2) = " + PAD7 % "i", [8, 0], None),
    "c14": (20000, "data", "keys(1) = 'V':mod(r,300)", [12], None),
    "c15": (20000, "next", "if mod(r,7) = 0 then keys(1) = '' else keys(1) = 'K':mod(r,50)", [8], None),
    "c16": (20000, "data", "if mod(r,7) = 0 then keys(1) = '' else keys(1) = mod(r,300)", [9], None),
    "c17": (20000, "data", "keys(1) = 'V':mod(r,50)", [10], None),
    # 25 Oct 26: UNIQUE with MANY distinct keys, so that the spilled runs are more than SORTMRG and the same key is in several of them (c14 has 300 keys: its
    # whole sort is one run of about 9 kb and never spills).  Which record of a key survives is its data item, the arrival number: the FIRST.
    "c18": (60000, "data", "keys(1) = " + PAD7 % "mod(r,20000)", [12], None),
    "t01": (60000, "data", "keys(1) = 'SAME'", [8], 3000),
    "t02": (60000, "data", "keys(1) = " + PAD7 % "i", [8], 3000),
    "t03": (60000, "data", "keys(1) = 'V':mod(r,5)", [8], 1000),
    "t04": (60000, "data", "keys(1) = i", [9], 3000),
    "t05": (60000, "data", "keys(1) = 'V':mod(r,2)\n      keys(2) = " + PAD7 % "i", [8, 0], 3000),
}
# The "mem" lines are written out so that the rows do not depend on what the sandbox's sd.conf held before (a sandbox that an
# earlier measurement left at SORTMEM=256 spilled these sorts, and the first recording of the golden values was taken so).
CONFIGS = [("mem", ["SORTMEM=4096", "SORTMRG=4"]), ("disk", ["SORTMEM=64", "SORTMRG=3"])]

# 25 Oct 26: the cases whose output must be the SAME whether the sort stays in memory or spills.  Until this date the merge put each merged run at the end
# of the queue, where the next pass took it for the newest, so equal keys came out in an order that depended on SORTMEM and SORTMRG (c01, c05, c08, c12,
# c15 to c17, t01 and t03 differed between the two configurations in GOLDEN below, as recorded from HEAD 680747d) and a UNIQUE sort could keep a
# later record than the first.  Every case but c10 (a right justified level that mixes numbers and text: the comparison is not transitive, so the order
# there depends on how the runs were cut) now has to give, spilled, exactly its in-memory output.
SPILL_EQ = [t for t in sorted(CASES) if t != "c10"]

# Recorded 20 Oct 26 from a sandbox built from HEAD 680747d (the tree before the change): config -> tag -> "N=.. MD=.. MK=..".
GOLDEN = {
    'mem': {
        'c01': 'N=20000 MD=731ab3e016c36aed561d142e8fe910bd MK=d41d8cd98f00b204e9800998ecf8427e',
        'c02': 'N=20000 MD=bbaeda80fe5bef469312566ed6373efe MK=d41d8cd98f00b204e9800998ecf8427e',
        'c03': 'N=20000 MD=d1f13ddeebd86f76102bf63059044118 MK=d41d8cd98f00b204e9800998ecf8427e',
        'c04': 'N=20000 MD=d1f13ddeebd86f76102bf63059044118 MK=d41d8cd98f00b204e9800998ecf8427e',
        'c05': 'N=20000 MD=9a317393ecb23cb3ce867c406aabf5a2 MK=d41d8cd98f00b204e9800998ecf8427e',
        'c06': 'N=20000 MD=cff7b9167f7e3c52cc78eb1363c143c2 MK=d41d8cd98f00b204e9800998ecf8427e',
        'c07': 'N=20000 MD=520ba2a46996b65dea17ff7a1091ac3e MK=d41d8cd98f00b204e9800998ecf8427e',
        'c08': 'N=20000 MD=9a317393ecb23cb3ce867c406aabf5a2 MK=d41d8cd98f00b204e9800998ecf8427e',
        'c09': 'N=20000 MD=d58b735f9a7fccc8d17a59f99d044553 MK=d41d8cd98f00b204e9800998ecf8427e',
        'c10': 'N=3000 MD=eb04437c8cce848ec23a6a0e9a5aba08 MK=d41d8cd98f00b204e9800998ecf8427e',
        'c11': 'N=20000 MD=c85c99cb17fd47ac3935098dda45abe4 MK=d41d8cd98f00b204e9800998ecf8427e',
        'c12': 'N=20000 MD=db19c55956e14868fc2ec4ca067df317 MK=85a41f4b0b792d7c866f22d4d9d61300',
        'c13': 'N=20000 MD=bbaeda80fe5bef469312566ed6373efe MK=d41d8cd98f00b204e9800998ecf8427e',
        'c14': 'N=300 MD=e76f6cde34ecce212ae732a432c6977a MK=d41d8cd98f00b204e9800998ecf8427e',
        'c15': 'N=20000 MD=99beb1110daf7929f6177b69645b63ad MK=ead7d1353621f3ba444c3855196f8c6f',
        'c16': 'N=20000 MD=3a937970f8c0c6e92eb41b880c48c5a4 MK=d41d8cd98f00b204e9800998ecf8427e',
        'c17': 'N=20000 MD=c28ace93834e03007a4dce6c70de3270 MK=d41d8cd98f00b204e9800998ecf8427e',
        'c18': 'N=18956 MD=b5ad67ec356955915de6d89ec1639c29 MK=d41d8cd98f00b204e9800998ecf8427e',   # 25 Oct 26, recorded in memory (the in-memory sort is unchanged)
        't01': 'N=60000 MD=36069c6d76dbdb2d11a70215ca9bf2fc MK=d41d8cd98f00b204e9800998ecf8427e',
        't02': 'N=60000 MD=1414d2a41e1c3883bf76c9eeab279ad7 MK=d41d8cd98f00b204e9800998ecf8427e',
        't03': 'N=60000 MD=7c2caa12e73a6c0c66cedbdc213e8567 MK=d41d8cd98f00b204e9800998ecf8427e',
        't04': 'N=60000 MD=1414d2a41e1c3883bf76c9eeab279ad7 MK=d41d8cd98f00b204e9800998ecf8427e',
        't05': 'N=60000 MD=ab5f954ef8301fc3a4bd65acd99f9812 MK=d41d8cd98f00b204e9800998ecf8427e',
    },
    'disk': {
        'c01': 'N=20000 MD=155c07ee705a77b526bee73579a0397c MK=d41d8cd98f00b204e9800998ecf8427e',
        'c02': 'N=20000 MD=bbaeda80fe5bef469312566ed6373efe MK=d41d8cd98f00b204e9800998ecf8427e',
        'c03': 'N=20000 MD=d1f13ddeebd86f76102bf63059044118 MK=d41d8cd98f00b204e9800998ecf8427e',
        'c04': 'N=20000 MD=d1f13ddeebd86f76102bf63059044118 MK=d41d8cd98f00b204e9800998ecf8427e',
        'c05': 'N=20000 MD=83f598ab03f6a8a5d13ef0760a401c58 MK=d41d8cd98f00b204e9800998ecf8427e',
        'c06': 'N=20000 MD=cff7b9167f7e3c52cc78eb1363c143c2 MK=d41d8cd98f00b204e9800998ecf8427e',
        'c07': 'N=20000 MD=520ba2a46996b65dea17ff7a1091ac3e MK=d41d8cd98f00b204e9800998ecf8427e',
        'c08': 'N=20000 MD=83f598ab03f6a8a5d13ef0760a401c58 MK=d41d8cd98f00b204e9800998ecf8427e',
        'c09': 'N=20000 MD=d58b735f9a7fccc8d17a59f99d044553 MK=d41d8cd98f00b204e9800998ecf8427e',
        'c10': 'N=3000 MD=eb04437c8cce848ec23a6a0e9a5aba08 MK=d41d8cd98f00b204e9800998ecf8427e',
        'c11': 'N=20000 MD=c85c99cb17fd47ac3935098dda45abe4 MK=d41d8cd98f00b204e9800998ecf8427e',
        'c12': 'N=20000 MD=636f01e1ea20a3702988adebb43dd858 MK=85a41f4b0b792d7c866f22d4d9d61300',
        'c13': 'N=20000 MD=bbaeda80fe5bef469312566ed6373efe MK=d41d8cd98f00b204e9800998ecf8427e',
        'c14': 'N=300 MD=e76f6cde34ecce212ae732a432c6977a MK=d41d8cd98f00b204e9800998ecf8427e',
        'c15': 'N=20000 MD=ae2857af236f14b583ff4ed292d146cc MK=ead7d1353621f3ba444c3855196f8c6f',
        'c16': 'N=20000 MD=85be15496616af0f3d1a557d40bd0a16 MK=d41d8cd98f00b204e9800998ecf8427e',
        'c17': 'N=20000 MD=baab66327c50999da4410ba4e705965d MK=d41d8cd98f00b204e9800998ecf8427e',
        't01': 'N=60000 MD=75b348bfa5dde672905892f771f12d15 MK=d41d8cd98f00b204e9800998ecf8427e',
        't02': 'N=60000 MD=1414d2a41e1c3883bf76c9eeab279ad7 MK=d41d8cd98f00b204e9800998ecf8427e',
        't03': 'N=60000 MD=cd1e6dc2e1ed53001a829975bb1b7c10 MK=d41d8cd98f00b204e9800998ecf8427e',
        't04': 'N=60000 MD=1414d2a41e1c3883bf76c9eeab279ad7 MK=d41d8cd98f00b204e9800998ecf8427e',
        't05': 'N=60000 MD=ab5f954ef8301fc3a4bd65acd99f9812 MK=d41d8cd98f00b204e9800998ecf8427e',
    },
}


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
    say("sandbox-sortord: CANNOT RUN - " + msg)
    sys.exit(2)


def tool(box, *args, **kw):
    return subprocess.run([sys.executable, TOOL, box] + list(args), capture_output=True, text=True, errors="replace",
                          timeout=kw.pop("timeout", 900), **kw)


def status(box):
    env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"))
    p = subprocess.run([os.path.join(box, "sys", "bin", "sd"), "-status"], capture_output=True, text=True,
                       errors="replace", env=env, timeout=60)
    return p.stdout + p.stderr


def restart(box, *extra):
    """Stop the sandbox, put `extra` lines in sd.conf below the marker, start it, and say whether SD is running."""
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


def isess(box, cmds, timeout=120):
    """A session in internal mode (sd -internal), where the restricted sort statements compile.  "" if it did not end."""
    env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"))
    body = "\nTERM 200,9999\n" + "".join(c + "\n" for c in cmds) + "OFF\n"
    p = subprocess.Popen([os.path.join(box, "sys", "bin", "sd"), "-internal"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, cwd=os.path.join(box, "sys"), env=env)
    try:
        out, _ = p.communicate(body.encode("latin-1"), timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
        p.communicate()
        return None
    out = ANSI.sub("", out.decode("latin-1", "replace"))
    return out.split(":TERM 200,9999", 1)[-1]


def program(tag, spec):
    n, ret, code, modes, _lim = spec
    nk = len(modes)
    L = ["$internal", "   dim modes(%d)" % nk, "   dim keys(%d)" % nk]
    L += ["   modes(%d) = %d" % (j + 1, m) for j, m in enumerate(modes)]
    L += ["   sortinit %d, modes" % nk, "   n = %d" % n, "   r = 12345", "   r2 = 54321", "   t0 = system(1081)",
          "   for i = 1 to n", "      r = mod(r * 16807, 2147483647)", "      r2 = mod(r2 * 16807, 2147483647)", "      " + code,
          "      sortadd keys, 'D':i", "   next i", "   tadd = system(1081) - t0"]
    if ret == "data":
        L += ["   all = sortdata()", "   cnt = status()", "   allk = ''"]
    else:
        L += ["   all = ''; allk = ''; cnt = 0", "   loop", "      d = sortnext(keys)", "   until status() do",
              "      all := d:@fm; cnt += 1"]
        L += ["      allk := keys(%d):@fm" % (j + 1) for j in range(nk)]
        L += ["   repeat"]
    L += ["   sortclear", "   crt '%s[=N=':cnt:' MD=':digest(all, 0, 'MD5'):' MK=':digest(allk, 0, 'MD5'):' T=':tadd:']'" % tag.upper(), "end"]
    return "\n".join(L) + "\n"


def run_cases(box, label, tags):
    """Compile and run each program in its own session.  Returns tag -> (fields dict or None)."""
    res = {}
    sysd = os.path.join(box, "sys")
    for tag in tags:
        nm = "zzso" + tag
        with open(os.path.join(sysd, "bp", nm), "w") as f:
            f.write(program(tag, CASES[tag]))
        made.append(nm)
        out = isess(box, ["BASIC bp " + nm, "RUN bp " + nm])
        if out is None:
            say("    %s %s: the session did not end in 120 s (killed)" % (label, tag))
            res[tag] = None
            continue
        if "Compiled 1 program(s) with no errors" not in out:
            say("    %s %s: did not compile:\n%s" % (label, tag, out[-600:]))
            res[tag] = None
            continue
        m = re.search(r"(?m)^%s\[=N=(\d+) MD=([0-9a-f]{32}) MK=([0-9a-f]{32}) T=(\d+)\]\s*$" % tag.upper(), out)
        res[tag] = None if not m else {"n": m.group(1), "md": m.group(2), "mk": m.group(3), "t": int(m.group(4))}
        say("    %s %s: %s" % (label, tag, "no result line" if not m else "N=%s T=%d ms" % (m.group(1), int(m.group(4)))))
    return res


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-sortord.py <dir> [--build] [--record]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    record = "--record" in sys.argv
    say("sandbox-sortord: sandbox %s%s" % (box, "  (RECORDING the golden values)" if record else ""))
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = tool(box, "all")
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-sortord: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)

    tags = sorted(CASES)
    for a in sys.argv[1:]:
        if a.startswith("--tags="):      # --record --tags=t01,t02 records only those (the rest of GOLDEN is kept by hand)
            tags = [t for t in tags if t in a[7:].split(",")]
    cfgs = CONFIGS
    for a in sys.argv[1:]:
        if a.startswith("--configs="):   # --record --configs=mem records only that configuration
            cfgs = [c for c in CONFIGS if c[0] in a[10:].split(",")]
    got = {}
    try:
        for label, extra in cfgs:
            say("\n--- %s ---------------------------------------------------------------------" % (
                "SORTMEM=4096 kb (the sort stays in memory)" if label == "mem" else "SORTMEM=64 kb, SORTMRG=3 (every run spills, the work files are merged)"))
            if not restart(box, *extra):
                bail("SD does not start with the sandbox's own sd.conf")
            got[label] = run_cases(box, label, tags)
    finally:
        for nm in made:
            for d in ("bp", "bp.out"):
                pth = os.path.join(sysd, d, nm)
                if os.path.exists(pth):
                    os.remove(pth)
        restart(box)

    if record:
        say("\nGOLDEN = {")
        for label, _e in cfgs:
            say("    %r: {" % label)
            for tag in tags:
                g = got[label][tag]
                say("        %r: %r," % (tag, None if g is None else "N=%s MD=%s MK=%s" % (g["n"], g["md"], g["mk"])))
            say("    },")
        say("}")
        sys.exit(0)

    say("\n--- the whole output is what the old kernel gave ---------------------------------")
    for label, _e in CONFIGS:
        for tag in tags:
            g = got[label][tag]
            want = GOLDEN.get(label, {}).get(tag)
            if label == "disk" and tag in SPILL_EQ:
                want = GOLDEN["mem"].get(tag)   # 25 Oct 26: a sort that spills gives the order the same sort in memory gives
            have = None if g is None else "N=%s MD=%s MK=%s" % (g["n"], g["md"], g["mk"])
            row("MATCH %-4s %s (%s)" % (label, tag, CASES[tag][2].split("\n")[0].strip()[:48]), want is not None and have == want,
                "got %s wanted %s" % (have, want))
    say("\n--- time: 60,000 equal / ordered / few-valued keys in under 3 s ---------------------")
    for tag in [t for t in tags if CASES[t][4]]:
        g = got["mem"][tag]
        row("TIME  %s %d ms (limit %d)" % (tag, -1 if g is None else g["t"], CASES[tag][4]),
            g is not None and g["t"] < CASES[tag][4], "no result" if g is None else "")
    say("\nsandbox-sortord: %d passed, %d failed" % (passed, failed))
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
