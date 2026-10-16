#!/usr/bin/env python3
#
# sandbox-sdfixseq.py - the counter of WRITE ... CREATING.SEQKEY (the header field seq_key): sdfix's H command shows it, and the
#                       audit of 15 Oct 26 - which writers of a hashed file's header keep it.  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-sdfixseq.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or
# absent).  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 15 Oct 26 dm  Written for the audit of seq_key and sdfix's H line for it.
# 15 Oct 26 dm  Leg 6: an id in use is skipped by WRITE ... CREATING.SEQKEY; CLEAR.FILE keeps the counter (owner's decisions).
# END-HISTORY
#
#   1  sdfix -I, command H: "Next seq id" at the field's own offset, the value CONFIGURE.FILE NEXT set, and no warning
#   2  a counter that is negative (patched on disk at the offset H printed) gives the warning; 0 and a positive value do not
#   3  the counter survives CLEAR.FILE, a CONFIGURE.FILE that rebuilds the file, SET.TRIGGER and an index created and deleted
#   4  a read-only file variable refused for CREATING.SEQKEY leaves the counter where it was
#   5  the counter is not put back by another writer of the header: a process writing under CREATING.SEQKEY while another
#      creates and deletes an index on the same file (create_ak and delete_ak wrote the header they had read at the start)
#   6  an id that already names a record is skipped, and the old records are not overwritten; CLEAR.FILE keeps the counter

import os
import re
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
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
    say("sandbox-sdfixseq: CANNOT RUN - " + msg)
    sys.exit(2)


def sess_cmd(box, cmds):
    return [sys.executable, TOOL, box, "sess", os.path.join(box, "user_accounts")] + list(cmds)


def clean(p_out):
    out = ANSI.sub("", p_out)
    return out.split(":TERM 200,9999", 1)[-1]


def sess(box, *cmds, quiet=False):
    if not quiet:
        say("    > " + " | ".join(cmds))
    p = subprocess.run(sess_cmd(box, cmds), capture_output=True, text=True, timeout=900)
    out = clean(p.stdout + p.stderr)
    if not quiet:
        for line in out.splitlines():
            if line.strip() and not line.startswith(":") and not line.startswith("exit "):
                say("      | " + line.rstrip()[:130])
    return out


def sdfix_h(box, path, conf):
    """Run the built sdfix in its interactive mode (-I needs DEBUG=2 in the config), give it H and Q."""
    sdfix = os.path.join(box, "sys", "bin", "sdfix")
    env = dict(os.environ, SD_CONFIG=conf)
    cmd = [sdfix, "-I", path]
    say("    > SD_CONFIG=%s %s   (stdin: H, Q)" % (conf, " ".join(cmd)))
    p = subprocess.run(cmd, input="H\nQ\n", capture_output=True, text=True, env=env, timeout=60)
    out = p.stdout + p.stderr
    for line in out.splitlines():
        if re.search(r"seq id|WARNING|Record count|Modulus", line):
            say("      | " + line.rstrip()[:130])
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-sdfixseq.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    bp = os.path.join(sysd, "bp")
    ua = os.path.join(box, "user_accounts")
    say("sandbox-sdfixseq: sandbox %s" % box)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-sdfixseq: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    if not os.path.isfile(os.path.join(sysd, "bin", "sdfix")):
        bail("%s has no bin/sdfix" % sysd)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    conf = os.path.join(box, "sd.conf")
    dconf = os.path.join(box, "sd-debug.conf")      # sdfix -I needs DEBUG & 2; the sandbox's own sd.conf is left as it is
    with open(conf) as f:
        base = f.read()
    with open(dconf, "w") as f:
        f.write(base.rstrip("\n") + "\nDEBUG=2\n")

    made = []

    def prog(name, text):
        with open(os.path.join(bp, name), "w") as f:
            f.write(text)
        made.append(name)

    try:
        # ---- the programs ----
        prog("zzsq_last", "   open 'zzsq' to f else stop 'no file'\n   crt 'LAST[':fileinfo(f, 1031):']'\nend\n")
        prog("zzsq_w3", "   open 'zzsq' to f else stop 'no file'\n   for i = 1 to 3\n      write 'r':i to f creating.seqkey id\n"
                        "   next i\n   crt 'W3[':id:']'\nend\n")
        prog("zzsq_ro", "   open 'zzsq' readonly to f else stop 'no file'\n   id = ''\n"
                        "   write 'x' to f creating.seqkey id on error crt 'RO_REFUSED[':status():']'\n"
                        "   crt 'RO_ID[':id:']'\n   open 'zzsq' to g else stop 'no file'\n   crt 'RO_LAST[':fileinfo(g, 1031):']'\nend\n")
        prog("zzsq_trg", "subroutine zzsq_trg(a, b, c, d, e)\n   return\nend\n")
        prog("zzsq_fill", "   open 'zzsq' to f else stop 'no file'\n   for i = 1 to 4000\n      write i * 7 to f, 'k':i\n   next i\n"
                          "   open 'DICT', 'zzsq' to dd else stop 'no dict'\n   write 'D':@fm:1:@fm:@fm:'FLD':@fm:'10L':@fm:'S' to dd, 'FLD'\n"
                          "   crt 'FILLED[':fileinfo(f, 1031):']'\nend\n")
        prog("zzsq_race", "   open 'zzsq' to f else stop 'no file'\n   for i = 1 to 2500\n      write 'seq':i to f creating.seqkey id\n"
                          "   next i\n   crt 'RACE_LAST[':fileinfo(f, 1031):']'\n"
                          "   n = 0\n   select f to 5\n   loop readnext k from 5 else exit\n      if num(k) then n += 1\n   repeat\n"
                          "   crt 'RACE_COUNT[':n:']'\nend\n")

        prog("zzsq_skip", "   open 'zzsq' to f else stop 'no file'\n   write 'old1' to f, '1'\n   write 'old2' to f, '2'\n   write 'old5' to f, '5'\n"
                          "   ids = ''\n   for i = 1 to 4\n      write 'new':i to f creating.seqkey id\n      ids := id : ','\n   next i\n"
                          "   crt 'SKIP_IDS[':ids:']'\n"
                          "   read a from f, '1' else a = '-'\n   read b from f, '2' else b = '-'\n   read c from f, '5' else c = '-'\n"
                          "   crt 'SKIP_OLD[':a:'/':b:'/':c:']'\n"
                          "   read d from f, '3' else d = '-'\n   read e from f, '4' else e = '-'\n   read g from f, '6' else g = '-'\n"
                          "   read h from f, '7' else h = '-'\n   crt 'SKIP_NEW[':d:'/':e:'/':g:'/':h:']'\n"
                          "   crt 'SKIP_LAST[':fileinfo(f, 1031):']'\nend\n")

        sess(box, "BASIC bp zzsq_last", "BASIC bp zzsq_w3", "BASIC bp zzsq_ro", "BASIC bp zzsq_trg", "BASIC bp zzsq_fill",
             "BASIC bp zzsq_race", "BASIC bp zzsq_skip", "CATALOG bp zzsq_trg LOCAL", quiet=True)

        say("\n--- leg 1: sdfix H shows the counter ----------------------------------------------------")
        out = sess(box, "DELETE.FILE DICT zzsq", "DELETE.FILE zzsq", "CREATE.FILE zzsq", "CONFIGURE.FILE zzsq NEXT 100", "RUN bp zzsq_last")
        row("setup: CONFIGURE.FILE NEXT 100 is held (FILEINFO key 1031 reads 99, the id last given)",
            re.search(r"LAST\[99\]", out) is not None, "got %r" % out[-200:])
        fpath = os.path.join(ua, "sdsys", "zzsq") if os.path.isdir(os.path.join(ua, "sdsys")) else None
        # the account the session runs in is the sandbox user's; find the file's directory
        cand = []
        for d, ds, fs in os.walk(box):
            if os.path.basename(d) == "zzsq" and "%0" in fs:
                cand.append(d)
        if len(cand) != 1:
            bail("expected one directory zzsq with a %%0 subfile under %s, found %r" % (box, cand))
        fpath = cand[0]
        subprocess.run([sys.executable, TOOL, box, "stop"], capture_output=True, text=True, timeout=120)
        h = sdfix_h(box, fpath, dconf)
        m = re.search(r"(?m)^([0-9A-F]{4}): Next seq id\s+(-?\d+)\s*$", h)
        row("THE ROW: H prints a 'Next seq id' line holding 100", m is not None and m.group(2) == "100", "H output: %r" % h[-400:])
        row("and no warning for a positive counter", "WARNING" not in h and "negative" not in h)
        row("CONTROL: H still lists its neighbours (Record count line)", re.search(r"Record count", h) is not None, "got %r" % h[-300:])
        off = int(m.group(1), 16) if m else None
        # the offset H printed must be where the four bytes really are
        if off is not None:
            with open(os.path.join(fpath, "%0"), "rb") as f:
                f.seek(off)
                disk = struct.unpack("<i", f.read(4))[0]
            row("the offset on the line is where the counter lies on disk (4 bytes there read 100)", disk == 100, "disk value %d" % disk)

        say("\n--- leg 2: a negative counter is warned about -------------------------------------------")
        if off is not None:
            with open(os.path.join(fpath, "%0"), "r+b") as f:
                f.seek(off)
                f.write(struct.pack("<i", -5))
            h = sdfix_h(box, fpath, dconf)
            row("THE ROW: a counter of -5 prints 'Next seq id   -5' and the warning",
                re.search(r"Next seq id\s+-5", h) is not None and re.search(r"WARNING: .*negative", h) is not None, "got %r" % h[-400:])
            with open(os.path.join(fpath, "%0"), "r+b") as f:
                f.seek(off)
                f.write(struct.pack("<i", 0))
            h = sdfix_h(box, fpath, dconf)
            row("CONTROL: a counter of 0 (none yet) prints 0 and no warning",
                re.search(r"Next seq id\s+0\s*$", h, re.M) is not None and "WARNING" not in h, "got %r" % h[-300:])
        subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

        say("\n--- leg 3: writers of the header keep the counter ---------------------------------------")
        sess(box, "DELETE.FILE DICT zzsq", "DELETE.FILE zzsq", "CREATE.FILE zzsq", quiet=True)
        out = sess(box, "RUN bp zzsq_w3", "RUN bp zzsq_last")
        row("setup: three CREATING.SEQKEY writes give ids 1 to 3", re.search(r"W3\[3\]", out) is not None and "LAST[3]" in out, "got %r" % out[-200:])
        steps = [("CLEAR.FILE zzsq", "CLEAR.FILE"),
                 ("CONFIGURE.FILE zzsq MINIMUM.MODULUS 7", "CONFIGURE.FILE (a rebuild)"),
                 ("SET.TRIGGER zzsq zzsq_trg PRE.WRITE", "SET.TRIGGER")]
        for cmd, label in steps:
            out = sess(box, "RUN bp zzsq_w3", cmd, "RUN bp zzsq_last")
            m = re.search(r"LAST\[(\d+)\]", out)
            before = re.search(r"W3\[(\d+)\]", out)
            row("%s keeps the counter (last id still %s)" % (label, before.group(1) if before else "?"),
                m is not None and before is not None and m.group(1) == before.group(1), "got %r" % out[-250:])
        out = sess(box, "RUN bp zzsq_w3", "RUN bp zzsq_fill", "CREATE.INDEX zzsq FLD", "BUILD.INDEX zzsq FLD", "DELETE.INDEX zzsq FLD", "RUN bp zzsq_last")
        m = re.search(r"LAST\[(\d+)\]", out)
        w = re.findall(r"W3\[(\d+)\]", out)
        row("an index created, built and deleted keeps the counter", m is not None and w and m.group(1) == w[-1], "got %r" % out[-250:])

        say("\n--- leg 4: a refused read-only write does not use up an id ------------------------------")
        sess(box, "DELETE.FILE DICT zzsq", "DELETE.FILE zzsq", "CREATE.FILE zzsq", "RUN bp zzsq_w3", quiet=True)
        out = sess(box, "RUN bp zzsq_ro")
        refused = re.search(r"RO_REFUSED\[", out) is not None
        row("CONTROL: the read-only variable is refused", refused, "got %r" % out[-250:])
        row("THE ROW: and the counter is where it was (last id 3, not 4)", "RO_LAST[3]" in out, "got %r" % out[-250:])

        say("\n--- leg 5: the counter is not put back by an index being made on the same file ------------")
        sess(box, "DELETE.FILE DICT zzsq", "DELETE.FILE zzsq", "CREATE.FILE zzsq", "RUN bp zzsq_fill", quiet=True)
        total = 0
        bad = 0
        runs = 3
        for r in range(runs):
            sess(box, "DELETE.FILE DICT zzsq", "DELETE.FILE zzsq", "CREATE.FILE zzsq", "RUN bp zzsq_fill", quiet=True)
            a = subprocess.Popen(sess_cmd(box, ["RUN bp zzsq_race"]), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            b = subprocess.Popen(sess_cmd(box, ["CREATE.INDEX zzsq FLD", "BUILD.INDEX zzsq FLD", "DELETE.INDEX zzsq FLD",
                                                "CREATE.INDEX zzsq FLD", "BUILD.INDEX zzsq FLD", "DELETE.INDEX zzsq FLD",
                                                "CREATE.INDEX zzsq FLD", "BUILD.INDEX zzsq FLD", "DELETE.INDEX zzsq FLD"]),
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            ao = clean(a.communicate(timeout=900)[0])
            b.communicate(timeout=900)
            ml = re.search(r"RACE_LAST\[(\d+)\]", ao)
            mc = re.search(r"RACE_COUNT\[(\d+)\]", ao)
            say("      run %d: RACE_LAST=%s RACE_COUNT=%s (4000 k-records are not counted; 2500 writes were made)"
                % (r + 1, ml.group(1) if ml else None, mc.group(1) if mc else None))
            if not ml or not mc:
                bail("the writer program printed no result: %r" % ao[-300:])
            if int(ml.group(1)) != 2500 or int(mc.group(1)) != 2500:
                bad += 1
        row("THE ROW: in %d runs of 2500 writes against an index being made and deleted, every id is new "
            "(the counter ends at 2500 and 2500 records exist)" % runs, bad == 0, "%d of %d runs lost the counter" % (bad, runs))

        say("\n--- leg 6: an id that already names a record is skipped (owner's choice, 15 Oct 26) -------")
        sess(box, "DELETE.FILE DICT zzsq", "DELETE.FILE zzsq", "CREATE.FILE zzsq", quiet=True)
        out = sess(box, "RUN bp zzsq_skip")
        row("THE ROW: records 1, 2 and 5 are there, four CREATING.SEQKEY writes are given 3, 4, 6 and 7",
            "SKIP_IDS[3,4,6,7,]" in out, "got %r" % out[-300:])
        row("and the three old records are as they were (not overwritten)", "SKIP_OLD[old1/old2/old5]" in out, "got %r" % out[-300:])
        row("and the four new records are under the ids given", "SKIP_NEW[new1/new2/new3/new4]" in out, "got %r" % out[-300:])
        row("FILEINFO key 1031 is the last id used (7)", "SKIP_LAST[7]" in out, "got %r" % out[-300:])
        sess(box, "DELETE.FILE DICT zzsq", "DELETE.FILE zzsq", "CREATE.FILE zzsq", quiet=True)
        out = sess(box, "RUN bp zzsq_w3", "CLEAR.FILE zzsq", "RUN bp zzsq_w3")
        w = re.findall(r"W3\[(\d+)\]", out)
        row("CLEAR.FILE keeps the counter (owner's decision 15 Oct 26): three ids, a clear, then the next three go on from 4 to 6",
            w == ["3", "6"], "got %r" % w)
    finally:
        for n in made:
            for d in ("bp", "bp.out"):
                p = os.path.join(sysd, d, n)
                if os.path.exists(p):
                    os.remove(p)
        sess(box, "DELETE.FILE DICT zzsq", "DELETE.FILE zzsq", quiet=True)

    say("\nsandbox-sdfixseq: %d passed, %d failed" % (passed, failed))
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
