#!/usr/bin/env python3
#
# sandbox-fixes-b12.py - QM4 Fixes tab, batches 1 and 2 (16 Oct 2026): the small defects and options that needed a test first.
#
#   532  NUMLOCKS is range checked (1 to 32767): the lock table's cells are int16, so 40000 wrapped        SD must refuse it
#   342  an inherited public variable is found when the parent also has a function of the same name        (already true)
#   266  a hangup at the break key prompt ends the process                                                  (already true)
#   280  a phantom started while SD is suspended gives its user table cell back
#   279  SELECT of a directory file at the operating system's open-file limit still gives the list
#   531  the U format in a query processor report wraps like L and T                                        (already true)
#   32   SET.FILE may point at a Q-pointer (a chain), and the chain opens
#   217  CATALOG with a hyphen prefix is global, callable, and DELETE.CATALOG removes it
#   172  CONFIGURE.FILE ... REPORTING shows progress
#   33   sdfix -Z clears the dead space at the end of each group and leaves every record readable
#   181  DIR_DICT: DAYS, DTM and OWNER items for a directory file
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-fixes-b12.py <dir> [--build]
#
# No install, no sudo.  <dir> is a sandbox made by sandbox-fromtree.py (needs a `make`d bin/sd and bin/sdfix).  With --build it is
# built first from THIS tree (it must be empty or absent).  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 16 Oct 26 dm  New.
# END-HISTORY
#
# THE INSTRUMENT.  Every row prints what it read.  Rows marked CONTROL show the instrument counts what it claims to: the
# same probe on the case that was always right.  The rows for 532, 280, 279, 32, 217, 172, 33 and 181 are the ones that
# were red on the tree before this change; 342, 266 and 531 were green first time (the items were already true).  THE
# SANDBOX MUST BE BUILT FROM THE TREE UNDER TEST.

import getpass
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
sys.path.insert(0, HERE)
from ptydrive import PtySession  # noqa: E402

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
MARK = "# --- sandbox-fixes-b12 below ---"
passed = failed = 0
made = []


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
    say("sandbox-fixes-b12: CANNOT RUN - " + msg)
    sys.exit(2)


def tool(box, *args, **kw):
    return subprocess.run([sys.executable, TOOL, box] + list(args), capture_output=True, text=True, errors="replace",
                          timeout=kw.pop("timeout", 900), **kw)


def sess(box, *cmds):
    say("    > %s" % " | ".join(c if len(c) < 60 else c[:57] + "..." for c in cmds))
    p = subprocess.run([sys.executable, TOOL, box, "sess", os.path.join(box, "user_accounts")] + list(cmds),
                       capture_output=True, text=True, errors="replace", timeout=900)
    return ANSI.sub("", p.stdout + p.stderr).split(":TERM 200,9999", 1)[-1]


def tagged(out, tag):
    m = re.search(r"(?m)^%s\[(.*)\]\s*$" % tag, out)
    return m.group(1) if m else None


def put(box, name, text):
    with open(os.path.join(box, "sys", "bp", name), "w") as f:
        f.write(text)
    made.append(name)


def compile_all(box, names):
    out = sess(box, *["BASIC bp %s" % n for n in names])
    n = len(re.findall(r"(?m)^Compiled 1 program\(s\) with no errors", out))
    if n != len(names):
        bail("%d of %d programs compiled:\n%s" % (n, len(names), out[-1500:]))


def status(box):
    p = subprocess.run([os.path.join(box, "sys", "bin", "sd"), "-status"], capture_output=True, text=True, errors="replace",
                       env=dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf")), timeout=60)
    return p.stdout + p.stderr


def started(box):
    return re.search(r"(?m)^Started\s+20\d\d-", status(box)) is not None


def restart(box, *extra):
    """Stop the sandbox, put `extra` lines in sd.conf below the marker, start it, and say whether SD is running."""
    conf = os.path.join(box, "sd.conf")
    tool(box, "stop", timeout=120)
    with open(conf) as f:
        base = f.read().split(MARK)[0].rstrip("\n") + "\n"
    with open(conf, "w") as f:
        f.write(base + ((MARK + "\n" + "".join(l + "\n" for l in extra)) if extra else ""))
    tool(box, "start", timeout=180)
    ok = started(box)
    say("  -- sd.conf %s: SD %s" % (("+ " + " ".join(extra)) if extra else "as built", "started" if ok else "NOT STARTED"))
    return ok


def sd_env(box):
    return dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"))


def live(box, cmds, limit_fds=None):
    """A session on a pipe, started the way sandbox-lock-b6 does; returns (Popen, output path)."""
    out = os.path.join(box, "live-b12.out")
    fh = open(out, "w")
    sdbin = os.path.join(box, "sys", "bin", "sd")
    argv = [sdbin] if not limit_fds else ["bash", "-c", "ulimit -n %d; exec \"$0\"" % limit_fds, sdbin]
    p = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=fh, stderr=subprocess.STDOUT, cwd=os.path.join(box, "user_accounts"),
                         env=sd_env(box), text=True)
    p.stdin.write("\nTERM 200,9999\n" + "".join(c + "\n" for c in cmds) + "OFF\n")
    p.stdin.flush()
    say("    > live: %s" % " | ".join(cmds))
    return p, out, fh


def read_out(path):
    return ANSI.sub("", open(path, errors="replace").read())


PROGS = {
    # 342: a class whose public variable and public function share a name, inherited once and twice
    "zzb12p": 'class zzb12p\n   public foo\n   public function foo()\n      return "FUNC"\n   end\n   public subroutine setfoo(v)\n      foo = v\n   end\nend\n',
    "zzb12c": 'class zzb12c inherits zzb12p\n   public function bar()\n      return "BAR"\n   end\nend\n',
    "zzb12v": ('class zzb12v\n   public v\n   public subroutine v(x)\n      crt "PUT ":x\n   end\n   public subroutine init()\n      v = "INITVAL"\n   end\nend\n'),
    "zzb12w": 'class zzb12w inherits zzb12v\n   public function other()\n      return "OTHER"\n   end\nend\n',
    "zzb12x": 'class zzb12x inherits zzb12w\nend\n',
    "zzb12r342": ('   p = object("zzb12p")\n   p->setfoo("VAL")\n   crt "PGOT[":p->foo:"]"\n   o = object("zzb12c")\n   o->setfoo("VAL")\n'
                  '   crt "CGOT[":o->foo:"]"\n   crt "CBAR[":o->bar():"]"\n'
                  '   g = object("zzb12x")\n   g->init()\n   crt "GV[":g->v:"]"\n   crt "GO[":g->other():"]"\n'
                  '   q = object("zzb12v")\n   q->init()\n   crt "QV[":q->v:"]"\n   crt "DONE342"\nend\n'),
    # 266: a loop for the break key prompt to interrupt
    "zzb12loop": "   crt 'LOOPING'\n   for i = 1 to 100000\n      sleep 1\n   next i\n   crt 'LOOPDONE'\nend\n",
    # 280: the phantom is started while SD is suspended (the harness suspends it between READY and the call)
    "zzb12ph": ("   crt 'READY'\n   sleep 5\n   execute 'PHANTOM NO.MSG SLEEP 3' capturing j\n   sleep 9\n"
                "   execute 'LISTU' capturing out\n   crt 'LPN[':dcount(out, @fm):']'\n   crt 'LPT[':change(out, @fm, '|'):']'\n"
                "   crt 'DONE280'\nend\n"),
    # 279: fifty DH files kept open, then a SELECT of a directory file
    "zzb12fd": ("   dim fv(50)\n   for i = 1 to 50\n      nm = 'zzb12f':i\n      execute 'DELETE.FILE ':nm capturing j\n      execute 'CREATE.FILE ':nm capturing j\n"
                "      open nm to fv(i) else stop 'no ':nm\n      write 'x' on fv(i), 'r1'\n   next i\n"
                "   execute 'DELETE.FILE zzb12dir' capturing j\n   execute 'CREATE.FILE zzb12dir DIRECTORY' capturing j\n"
                "   open 'zzb12dir' to d else stop 'no dir'\n   write 'a' on d, 'one.txt'\n   write 'b' on d, 'two.txt'\n   write 'c' on d, 'three.txt'\n"),
    "zzb12fd2": ("   dim fv(60)\n   n = 0\n   for i = 1 to 50\n      nm = 'zzb12f':i\n      open nm to fv(i) then\n         read z from fv(i), 'r1' then n += 1\n      end\n   next i\n"
                 "   crt 'OPENED[':n:']'\n   open 'zzb12dir' to d else stop 'no dir'\n   select d to 1\n   cnt = 0\n   loop\n      readnext id from 1 else exit\n      cnt += 1\n   repeat\n"
                 "   crt 'SELECTED[':cnt:']'\n   crt 'DONE279'\nend\n"),
    # 32: a Q-pointer chain
    "zzb12q": ("   for i = 1 to 3\n      delete @voc, 'zzb12p':i\n   next i\n   execute 'DELETE.FILE zzb12q1' capturing j\n   execute 'CREATE.FILE zzb12q1' capturing j\n   open 'zzb12q1' to f else stop 'no f'\n"
               "   write 'CHAINED' on f, 'rec'\n   crt 'MADE'\nend\n"),
    "zzb12qr": ("   open 'zzb12p3' to f else stop 'chain would not open'\n   read r from f, 'rec' then crt 'CHAIN[':r:']' else crt 'CHAIN[missing]'\n   crt 'DONE32'\nend\n"),
    # 217: a subroutine to be catalogued under a hyphen name
    "zzb12sub": "subroutine zzb12sub(a)\n   a = 'HYPHEN-SAID-HI'\n   return\nend\n",
    "zzb12cs": "   nm = '-zzb12sub'\n   x = ''\n   call @nm(x)\n   crt 'CALLED[':x:']'\n   crt 'DONE217'\nend\n",
    # 360: a file held to three groups with 1500 records of 100 bytes (all of its groups overflow), and one with room to spare
    "zzb12an": ("   execute 'DELETE.FILE zzb12an' capturing j\n   execute 'CREATE.FILE zzb12an DYNAMIC MINIMUM.MODULUS 3' capturing j\n"
                "   execute 'CONFIGURE.FILE zzb12an NO.RESIZE' capturing j\n   open 'zzb12an' to f else stop 'no f'\n"
                "   for i = 1 to 1500\n      write str('x', 100) on f, 'k':i\n   next i\n"
                "   close f\n"
                "   execute 'DELETE.FILE zzb12an2' capturing j\n   execute 'CREATE.FILE zzb12an2 DYNAMIC MINIMUM.MODULUS 7' capturing j\n"
                "   open 'zzb12an2' to f2 else stop 'no f2'\n   write 'a' on f2, 'one'\n   close f2\n   crt 'DONE360'\nend\n"),
    # 414: merges of select lists with duplicates and ids that look like paths; and two big lists, timed
    "zzb12ml": ("   execute 'SELECT VOC SAMPLE 1' capturing j\n   execute 'SAVE.LIST zzb12init COUNT.SUP' capturing j\n"
                "   open '$savedlists' to f else stop 'no $savedlists'\n"
                "   a = 'b':@fm:'a/b':@fm:'c*':@fm:'b':@fm:'d':@fm:'x y'\n   b = 'a/b':@fm:'e':@fm:'a/b':@fm:'d':@fm:'b':@fm:\"q'q\"\n"
                "   write a on f, 'zzb12la'\n   write b on f, 'zzb12lb'\n"
                "   getlist 'zzb12la' to 1 then null else crt 'GL FAILED'\n   getlist 'zzb12lb' to 2 then null else crt 'GL FAILED'\n"
                "   execute 'MERGE.LIST 1 UNION 2 TO 3 COUNT.SUP' capturing j\n   readlist r from 3 else r = 'none'\n   crt 'UNION[':change(r, @fm, '|'):']'\n"
                "   getlist 'zzb12la' to 1 then null else crt 'GL FAILED'\n   getlist 'zzb12lb' to 2 then null else crt 'GL FAILED'\n"
                "   execute 'MERGE.LIST 1 INTERSECT 2 TO 4 COUNT.SUP' capturing j\n   readlist r from 4 else r = 'none'\n   crt 'INTER[':change(r, @fm, '|'):']'\n"
                "   getlist 'zzb12la' to 1 then null else crt 'GL FAILED'\n   getlist 'zzb12lb' to 2 then null else crt 'GL FAILED'\n"
                "   execute 'MERGE.LIST 1 DIFF 2 TO 5 COUNT.SUP' capturing j\n   readlist r from 5 else r = 'none'\n   crt 'DIFF[':change(r, @fm, '|'):']'\n"
                "   crt 'DONE414'\nend\n"),
    "zzb12mb": ("   open '$savedlists' to f else stop 'no $savedlists'\n   big1 = '' ; big2 = ''\n"
                "   for i = 1 to 15000\n      big1<i> = 'id':i\n      big2<i> = 'id':(i + 7500)\n   next i\n"
                "   write big1 on f, 'zzb12b1'\n   write big2 on f, 'zzb12b2'\n"
                "   t0 = time()\n   getlist 'zzb12b1' to 1 then null else crt 'GL FAILED'\n   getlist 'zzb12b2' to 2 then null else crt 'GL FAILED'\n"
                "   execute 'MERGE.LIST 1 UNION 2 TO 3 COUNT.SUP' capturing j\n   t1 = time()\n"
                "   getlist 'zzb12b1' to 1 then null else crt 'GL FAILED'\n   getlist 'zzb12b2' to 2 then null else crt 'GL FAILED'\n"
                "   execute 'MERGE.LIST 1 INTERSECT 2 TO 4 COUNT.SUP' capturing j\n"
                "   getlist 'zzb12b1' to 1 then null else crt 'GL FAILED'\n   getlist 'zzb12b2' to 2 then null else crt 'GL FAILED'\n"
                "   execute 'MERGE.LIST 1 DIFF 2 TO 5 COUNT.SUP' capturing j\n   t2 = time()\n"
                "   readlist u from 3 else u = ''\n   readlist n from 4 else n = ''\n   readlist d from 5 else d = ''\n"
                "   crt 'BIG[':dcount(u, @fm):' ':dcount(n, @fm):' ':dcount(d, @fm):']'\n   crt 'SECS[':int(t2 - t0):']'\n   crt 'DONE414B'\nend\n"),
    # 172: a conversion of 2500 records with REPORTING and without
    "zzb12cf": ("   execute 'DELETE.FILE zzb12cv' capturing j\n   execute 'CREATE.FILE zzb12cv DYNAMIC' capturing j\n   open 'zzb12cv' to f else stop 'no f'\n"
                "   for i = 1 to 2500\n      write 'rec':i on f, 'k':i\n   next i\n   close f\n   crt 'FILLED'\nend\n"),
}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-fixes-b12.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-fixes-b12: sandbox %s" % box)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = tool(box, "all")
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-fixes-b12: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)

    try:
        tool(box, "start", timeout=180)
        for nm, text in PROGS.items():
            put(box, nm, text)

        # ------------------------------------------------------------------------------------------------ 342
        say("\n--- 342 an inherited public variable beside a function of the same name -----------------------------")
        compile_all(box, ["zzb12p", "zzb12c", "zzb12v", "zzb12w", "zzb12x"])
        sess(box, *["CATALOG bp %s LOCAL" % n for n in ("zzb12p", "zzb12c", "zzb12v", "zzb12w", "zzb12x")])
        compile_all(box, ["zzb12r342"])
        out = sess(box, "RUN bp zzb12r342")
        row("342: the parent answers its function for the name it shares with its variable (PGOT)", tagged(out, "PGOT") == "FUNC", out[-300:])
        row("342: the child answers the same (CGOT), and its own function is found (CBAR)",
            tagged(out, "CGOT") == "FUNC" and tagged(out, "CBAR") == "BAR", out[-300:])
        row("342: a variable beside a SUBROUTINE of its name is read through a grandchild (GV) and the grandchild's parent's function (GO)",
            tagged(out, "GV") == "INITVAL" and tagged(out, "GO") == "OTHER", out[-300:])
        row("CONTROL: the same variable read from the class itself (QV) gives the same value", tagged(out, "QV") == "INITVAL" and "DONE342" in out, out[-300:])

        # ------------------------------------------------------------------------------------------------ 531
        say("\n--- 531 the U format in a query processor report --------------------------------------------------------")
        put(box, "zzb12u", ('   execute "DELETE.FILE zzb12ud" capturing j\n   execute "CREATE.FILE zzb12ud" capturing j\n   execute "CREATE.FILE DICT zzb12ud" capturing j\n'
                            '   open "DICT","zzb12ud" to d else stop "nodict"\n'
                            '   write "D":@fm:"1":@fm:"":@fm:"Uu":@fm:"10U":@fm:"S":@fm:"" on d, "UU"\n'
                            '   write "D":@fm:"2":@fm:"":@fm:"Tt":@fm:"10T":@fm:"S":@fm:"" on d, "TT"\n'
                            '   write "D":@fm:"3":@fm:"":@fm:"Ll":@fm:"10L":@fm:"S":@fm:"" on d, "LL"\n'
                            '   open "zzb12ud" to f else stop "nofile"\n'
                            '   write "abcdefghij0123456789xyz":@fm:"abcdefghij0123456789xyz":@fm:"abcdefghij0123456789xyz" on f, "k1"\n   crt "SET"\nend\n'))
        compile_all(box, ["zzb12u"])
        sess(box, "RUN bp zzb12u")
        out = sess(box, "LIST zzb12ud UU TT LL NO.PAGE")
        lines = [l for l in out.splitlines() if l.startswith("k1") or l.startswith("             ")]
        row("531: the report wraps the 23 character value in three rows of the 10 character column, as T and L do",
            len(lines) == 3 and lines[0].split()[1:] == ["abcdefghij"] * 3 and lines[1].split() == ["0123456789"] * 3
            and lines[2].split() == ["xyz"] * 3, repr(lines))

        # ------------------------------------------------------------------------------------------------ 32
        say("\n--- 32 SET.FILE with a Q-pointer as the target ----------------------------------------------------------")
        compile_all(box, ["zzb12q", "zzb12qr"])
        sess(box, "RUN bp zzb12q")
        out = sess(box, "SET.FILE sdsys zzb12q1 zzb12p1", "SET.FILE sdsys zzb12p1 zzb12p2", "SET.FILE sdsys zzb12p2 zzb12p3",
                   "LIST VOC WITH @ID LIKE \"zzb12p...\" NO.PAGE", "RUN bp zzb12qr")
        row("CONTROL: SET.FILE of an F-pointer target makes the first link (zzb12p1)", re.search(r"(?m)^zzb12p1\s+Q\s*$", out) is not None, out[-500:])
        row("32: SET.FILE with the Q-pointer zzb12p1 as target makes zzb12p2, and zzb12p2 makes zzb12p3",
            re.search(r"(?m)^zzb12p2\s+Q\s*$", out) is not None and re.search(r"(?m)^zzb12p3\s+Q\s*$", out) is not None, out[-500:])
        row("32: a program opens the end of the three-link chain and reads the record", tagged(out, "CHAIN") == "CHAINED" and "DONE32" in out, out[-400:])
        out = sess(box, "SET.FILE sdsys zzb12nosuch zzb12p9")
        row("CONTROL: a target that is not in the VOC is still refused (6872)", re.search(r"(?i)not in target VOC", out) is not None, out[-300:])

        # ------------------------------------------------------------------------------------------------ 217
        say("\n--- 217 a hyphen as a global catalogue prefix -----------------------------------------------------------")
        compile_all(box, ["zzb12sub", "zzb12cs"])
        out = sess(box, "CATALOG bp -zzb12sub", "RUN bp zzb12cs")
        gcat = os.path.join(sysd, "gcat", "-zzb12sub")
        row("217: CATALOG bp -zzb12sub catalogues the program globally under the hyphen name (an entry in gcat)", os.path.exists(gcat), out[-500:])
        row("217: ... and a program calls it by that name", tagged(out, "CALLED") == "HYPHEN-SAID-HI" and "DONE217" in out, out[-400:])
        out = sess(box, "DELETE.CATALOG -zzb12sub")
        row("217: DELETE.CATALOG -zzb12sub removes it", not os.path.exists(gcat), out[-300:])
        out = sess(box, "CATALOG bp zzb12sub")
        row("CONTROL: a name with no prefix is catalogued privately, not globally",
            not os.path.exists(os.path.join(sysd, "gcat", "zzb12sub")), out[-300:])

        # ------------------------------------------------------------------------------------------------ 360
        say("\n--- 360 ANALYSE.FILE: a histogram of group utilisation ----------------------------------------------------")
        compile_all(box, ["zzb12an"])
        out = sess(box, "RUN bp zzb12an")
        row("setup: both files were made", "DONE360" in out, out[-300:])
        out = sess(box, "ANALYZE.FILE zzb12an STATISTICS", "S")          # S: no more pauses between the pages of the report
        def hist(text):
            counts = dict((m.group(1), int(m.group(2))) for m in re.finditer(r"(?m)^(over 100%|up to \d+%)\s+(\d+)\| >*\s*$", text))
            mod = re.search(r"(?m)^Current modulus\s*:\s*(\d+)", text)
            return counts, (int(mod.group(1)) if mod else None)
        counts, mod = hist(out)
        say("    group counts: %r, modulus %r" % (counts, mod))
        row("360: ANALYSE.FILE ... STATISTICS shows a histogram of group utilisation, 11 bars", "Histogram of group utilisation" in out and len(counts) == 11, out[-600:])
        row("360: its counts add up to the modulus of the file (%s)" % mod, mod is not None and sum(counts.values()) == mod, repr(counts))
        row("360: a file held to 3 groups (NO.RESIZE) with 150000 bytes in it has all three over 100%: each has overflow blocks",
            mod == 3 and counts.get("over 100%") == 3, repr(counts))
        out = sess(box, "ANALYZE.FILE zzb12an2 STATISTICS", "S")
        counts, mod = hist(out)
        row("CONTROL: a file of seven groups holding one record has all seven in the first bar, up to 10%",
            mod == 7 and counts.get("up to 10%") == 7 and sum(counts.values()) == 7, repr((mod, counts)))

        # ------------------------------------------------------------------------------------------------ 414
        say("\n--- 414 merging select lists ------------------------------------------------------------------------------")
        compile_all(box, ["zzb12ml", "zzb12mb"])
        out = sess(box, "RUN bp zzb12ml")
        # a = b, a/b, c*, b, d, x y      b = a/b, e, a/b, d, b, q'q
        row("414: UNION keeps the first list and adds each new key of the second once, in its order",
            tagged(out, "UNION") == "b|a/b|c*|b|d|x y|e|q'q", out[-300:])
        row("414: INTERSECTION gives the keys of the second list that are in the first, a repeated one repeated",
            tagged(out, "INTER") == "a/b|a/b|d|b", out[-300:])
        row("414: DIFFERENCE takes away one occurrence in the first list for each key of the second",
            tagged(out, "DIFF") == "c*|b|x y", out[-300:])
        out = sess(box, "RUN bp zzb12mb")
        row("414: two lists of 15000 keys, 7500 in common, give 22500, 7500 and 7500 keys", tagged(out, "BIG") == "22500 7500 7500", out[-300:])
        secs = tagged(out, "SECS")
        row("414: ... and all three merges together take under 20 seconds (%s s)" % secs, secs is not None and secs.isdigit() and int(secs) < 20, out[-300:])

        # ------------------------------------------------------------------------------------------------ 172
        say("\n--- 172 CONFIGURE.FILE ... REPORTING --------------------------------------------------------------------")
        compile_all(box, ["zzb12cf"])
        sess(box, "RUN bp zzb12cf")
        out = sess(box, "CONFIGURE.FILE zzb12cv DIRECTORY REPORTING")
        lines = re.findall(r"(?m)^(\d+) records converted\s*$", out)
        row("172: a conversion with REPORTING shows a line at 1000 and 2000 records and the total 2500",
            lines == ["1000", "2000", "2500"], "got %r\n%s" % (lines, out[-400:]))
        sess(box, "RUN bp zzb12cf")
        out = sess(box, "CONFIGURE.FILE zzb12cv DIRECTORY")
        row("CONTROL: the same conversion without REPORTING shows no such line", re.search(r"records converted", out) is None, out[-300:])

        # ------------------------------------------------------------------------------------------------ 181
        say("\n--- 181 DIR_DICT: DAYS, DTM and OWNER -------------------------------------------------------------------")
        # the three items come from the installer's dictionary file (gplbld/FILES_DICTS): look at what the sandbox build wrote
        put(box, "zzb12dr", ("   openpath @sdsys:@ds:'dir_dict' to dd else stop 'no dir_dict'\n"
                             "   for each id in 'days,dtm,owner' delimiter ','\n      read r from dd, id then crt 'ITEM ':id:'[':r<2>:']' else crt 'ITEM ':id:'[missing]'\n   next id\n   crt 'DONE181A'\nend\n"))
        out = sess(box, "BASIC bp zzb12dr", "RUN bp zzb12dr")
        row("181: the dir_dict dictionary holds the three items, each calling !dirinfo",
            all(re.search(r'(?m)^ITEM %s\[SUBR\("!dirinfo","%s",@FILE\.NAME,@ID\)\]\s*$' % (k, k), out) for k in ("days", "dtm", "owner")), out[-600:])
        put(box, "zzb12ddr", ('   deffun dirinfo(a, b, c) calling "!dirinfo"\n'
                              '   execute "DELETE.FILE zzb12dd" capturing j\n   execute "CREATE.FILE zzb12dd DIRECTORY" capturing j\n'
                              '   open "zzb12dd" to f else stop "nofile"\n   write "hello" on f, "note.txt"\n'
                              '   crt "DAYS[":dirinfo("days", "zzb12dd", "note.txt"):"]"\n'
                              '   crt "OWNER[":dirinfo("owner", "zzb12dd", "note.txt"):"]"\n'
                              '   crt "DTM[":dirinfo("dtm", "zzb12dd", "note.txt"):"]"\n'
                              '   crt "NONE[":dirinfo("days", "zzb12dd", "nosuch.txt"):"]"\n   crt "DONE181"\nend\n'))
        out = sess(box, "BASIC bp zzb12ddr", "RUN bp zzb12ddr")
        user = getpass.getuser()
        row("181: !dirinfo(days) of a record just written is 0", tagged(out, "DAYS") == "0", out[-400:])
        row("181: !dirinfo(owner) is the user who wrote it (%s)" % user, tagged(out, "OWNER") == user, out[-400:])
        row("181: !dirinfo(dtm) is a date and a time (D4- then MTS)", re.fullmatch(r"\S+ \d\d:\d\d:\d\d", tagged(out, "DTM") or "") is not None,
            out[-400:])
        row("CONTROL: a record that is not there gives null", tagged(out, "NONE") == "" and "DONE181" in out, out[-400:])

        # ------------------------------------------------------------------------------------------------ 33
        say("\n--- 33 sdfix -Z -----------------------------------------------------------------------------------------")
        sdfix = os.path.join(sysd, "bin", "sdfix")
        if not os.path.isfile(sdfix):
            row("33: bin/sdfix exists in the sandbox", False, sdfix)
        else:
            put(box, "zzb12z", ("   execute 'DELETE.FILE zzb12zf' capturing j\n   execute 'CREATE.FILE zzb12zf DYNAMIC' capturing j\n   open 'zzb12zf' to f else stop 'no f'\n"
                                "   for i = 1 to 400\n      write str('ab', 60):i on f, 'k':i\n   next i\n"
                                "   for i = 1 to 400 step 2\n      delete f, 'k':i\n   next i\n   crt 'ZFILLED'\nend\n"),)
            compile_all(box, ["zzb12z"])
            sess(box, "RUN bp zzb12z")
            tool(box, "stop", timeout=120)
            fdir = os.path.join(box, "user_accounts", "zzb12zf")
            if not os.path.isdir(fdir):
                fdir = os.path.join(sysd, "zzb12zf")
            say("    file directory: %s" % fdir)
            copy = os.path.join(box, "zzb12zf.copy")
            shutil.rmtree(copy, ignore_errors=True)
            shutil.copytree(fdir, copy)
            env = sd_env(box)
            before = {n: open(os.path.join(copy, n), "rb").read() for n in sorted(os.listdir(copy))}
            r = subprocess.run([sdfix, "-B", "-Z", copy], capture_output=True, text=True, errors="replace", env=env, timeout=300)
            say("    sdfix -B -Z: exit %d, %s" % (r.returncode, (r.stdout + r.stderr).strip().replace("\n", " | ")[-300:]))
            after = {n: open(os.path.join(copy, n), "rb").read() for n in sorted(os.listdir(copy))}
            nz_before = sum(1 for n in before for b in before[n] if b)
            nz_after = sum(1 for n in after for b in after[n] if b)
            row("33: sdfix -Z says how many blocks it cleared", re.search(r"Dead space cleared in (\d+) block", r.stdout + r.stderr) is not None
                and int(re.search(r"Dead space cleared in (\d+) block", r.stdout + r.stderr).group(1)) > 0, (r.stdout + r.stderr)[-300:])
            row("33: ... the file holds fewer non-zero bytes afterwards (%d -> %d)" % (nz_before, nz_after), nz_after < nz_before)
            r2 = subprocess.run([sdfix, "-B", "-Z", copy], capture_output=True, text=True, errors="replace", env=env, timeout=300)
            row("33: a second run finds nothing left to clear", re.search(r"Dead space cleared in 0 block", r2.stdout + r2.stderr) is not None,
                (r2.stdout + r2.stderr)[-300:])
            r3 = subprocess.run([sdfix, "-B", "-C", copy], capture_output=True, text=True, errors="replace", env=env, timeout=300)
            row("CONTROL: a plain check of the cleared file finds no error", r3.returncode == 0 and not re.search(r"(?i)\b(invalid|incorrect|error)", r3.stdout + r3.stderr),
                (r3.stdout + r3.stderr)[-300:])
            # the cleared file must still hold every record: put it in place of the original and count
            shutil.rmtree(fdir)
            shutil.copytree(copy, fdir)
            tool(box, "start", timeout=180)
            out = sess(box, "COUNT zzb12zf")
            row("33: the cleared file, put back, still holds the 200 records that were not deleted",
                re.search(r"(?m)^\s*200 record\(s\) counted", out) is not None or re.search(r"\b200\b", out) is not None, out[-300:])

        # ------------------------------------------------------------------------------------------------ 532
        say("\n--- 532 NUMLOCKS -------------------------------------------------------------------------------------------")
        ok = restart(box, "NUMLOCKS=20000")
        row("CONTROL: NUMLOCKS=20000 starts SD", ok)
        if ok:
            put(box, "zzb12nl", "   crt 'NL[':config('NUMLOCKS'):']'\nend\n")
            compile_all(box, ["zzb12nl"])
            out = sess(box, "RUN bp zzb12nl")
            row("CONTROL: ... and CONFIG('NUMLOCKS') is 20000", tagged(out, "NL") == "20000", out[-200:])
        ok = restart(box, "NUMLOCKS=40000")
        row("532: NUMLOCKS=40000 (more than int16 holds) is refused: SD does not start", not ok)
        ok = restart(box, "NUMLOCKS=65636")
        row("532: NUMLOCKS=65636, which an int16 holds as 100, is refused", not ok)
        ok = restart(box, "NUMLOCKS=0")
        row("532: NUMLOCKS=0 is refused too", not ok)
        ok = restart(box)
        if not ok:
            bail("SD does not start again with the built sd.conf")

        # ------------------------------------------------------------------------------------------------ 266
        say("\n--- 266 a hangup at the break key prompt ------------------------------------------------------------------")
        compile_all(box, ["zzb12loop"])
        env = dict(sd_env(box), TERM="xterm")
        s = PtySession([os.path.join(sysd, "bin", "sd")], os.path.join(box, "user_accounts"), env, 100, 24)
        s.settle(1.0)
        s.type("TERM xterm\r")
        s.type("RUN bp zzb12loop\r", idle=1.0)
        s.type("\x03", idle=1.0)
        screen = "\n".join(s.screen.lines())
        row("266: CONTROL: Ctrl-C shows the break key prompt", "G to continue" in screen, screen[-300:])
        s.finish(limit=0.5)
        row("266: after the terminal is hung up the process ends by itself (not killed)", s.exited and not getattr(s, "killed", False),
            "killed=%r exited=%r" % (getattr(s, "killed", None), s.exited))
        s2 = PtySession([os.path.join(sysd, "bin", "sd")], os.path.join(box, "user_accounts"), env, 100, 24)
        s2.settle(1.0)
        s2.type("TERM xterm\r")
        s2.type("RUN bp zzb12loop\r", idle=1.0)
        s2.type("\x03", idle=1.0)
        s2.type("G", idle=1.0)
        screen2 = "\n".join(s2.screen.lines())
        row("266: CONTROL: G continues the program (the prompt works, only the hangup was in question)", "LOOPING" in screen2, screen2[-300:])
        s2.finish(limit=0.5)

        # ------------------------------------------------------------------------------------------------ 279
        say("\n--- 279 SELECT of a directory file at the open-file limit --------------------------------------------------")
        compile_all(box, ["zzb12fd", "zzb12fd2"])
        sess(box, "RUN bp zzb12fd")
        p, outp, fh = live(box, ["RUN bp zzb12fd2"], limit_fds=48)
        try:
            p.wait(timeout=120)
        except subprocess.TimeoutExpired:
            p.kill()
        fh.close()
        out = read_out(outp)
        say("    " + " | ".join(l for l in out.splitlines() if "OPENED" in l or "SELECTED" in l or "DONE279" in l))
        row("279: CONTROL: the program really did open files up to the limit of 48 descriptors (OPENED is 50 files read)", tagged(out, "OPENED") == "50", out[-400:])
        row("279: the SELECT of the directory file gives its three records, not an empty list", tagged(out, "SELECTED") == "3", out[-400:])

        # ------------------------------------------------------------------------------------------------ 280
        say("\n--- 280 a phantom started while SD is suspended ------------------------------------------------------------")
        compile_all(box, ["zzb12ph"])
        sdbin = os.path.join(sysd, "bin", "sd")
        p, outp, fh = live(box, ["RUN bp zzb12ph"])
        t0 = time.time()
        while time.time() - t0 < 60 and "READY" not in read_out(outp):
            time.sleep(0.2)
        r = subprocess.run([sdbin, "-suspend"], env=sd_env(box), capture_output=True, text=True, errors="replace", timeout=60)
        say("    sd -suspend: exit %d %s" % (r.returncode, (r.stdout + r.stderr).strip()[:100]))
        time.sleep(10)
        r = subprocess.run([sdbin, "-resume"], env=sd_env(box), capture_output=True, text=True, errors="replace", timeout=60)
        say("    sd -resume: exit %d %s" % (r.returncode, (r.stdout + r.stderr).strip()[:100]))
        try:
            p.wait(timeout=90)
        except subprocess.TimeoutExpired:
            p.kill()
        fh.close()
        out = read_out(outp)
        say("    " + " | ".join(l for l in out.splitlines() if l.startswith(("READY", "LPN", "LPT", "DONE280"))))
        row("280: CONTROL: the run reached its end after the resume", "DONE280" in out, out[-300:])
        listed = tagged(out, "LPT") or ""
        # a cell that nothing runs in has no process id and the date 31 Dec 00:00; a session that was only hung up (the 266 rows) is another matter
        ghost = re.search(r"\|\s*\d+\s+0\s+\d+\s+31 Dec", listed)
        row("280: the phantom that found SD suspended left no entry in the user table (no row with process id 0 in LISTU)",
            ghost is None and "DONE280" in out, "listed: %s" % listed)
    finally:
        tool(box, "stop", timeout=120)
        for nm in made:
            for d in ("bp", "bp.out"):
                pth = os.path.join(sysd, d, nm)
                if os.path.exists(pth):
                    os.remove(pth)

    say("\nsandbox-fixes-b12: %d passed, %d failed" % (passed, failed))
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
