#!/usr/bin/env python3
#
# sandbox-oq2.py - 1.2-0, second sitting (12 Oct 2026): the openQM items built with SD's own syntax because the
#                  release notes give none (owner: "implement the functionality as much as possible - the method or
#                  syntax can be different than in openQM").  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-oq2.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (needs a `make`d bin/sd).  With --build it is built first from
# THIS tree (it must be empty or absent).  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 12 Oct 26 dm  Written: 336 names with two underscores, 407 INCLUDE in $BASIC.OPTIONS.
# END-HISTORY
#
# Each case is (label, files, program body, wanted).  files = {name: text} written to the sandbox's bp directory
# first (source, includes and option records); the body is compiled as program zzoqNN and the value it leaves in x
# is printed between brackets.  A COMPILE ERROR is read from the compiler's own "Compiled N program(s) with
# errors" line, and a case that wants one gives wanted = the line number the compiler must report.

import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
passed = failed = 0

CASES = [
    ("CONTROL: a name with one underscore", {}, "a_b = 5\nx = a_b", "5"),
    ("336: a name with two consecutive underscores", {}, "a__b = 7\nx = a__b", "7"),
    ("336: and three, mixed with digits", {}, "a1___b2 = 9\nx = a1___b2", "9"),
    ("407 CONTROL: without the option record the constant is not defined", {}, "x = unassigned(zzk)", "1"),
    ("407: an INCLUDE line in $BASIC.OPTIONS puts the record at the top of the program",
     {"$BASIC.OPTIONS": "X\nINCLUDE zzincl\n", "zzincl": "zzk = 41\n"}, "x = zzk + 1", "42"),
]

# Not through the option record: a compile error must keep its own line number with includes in front
ERRCASE = ("407: an error on line 4 of the program (the probe's own first line is 1) is still reported as line 4 with two automatic includes in front",
           {"$BASIC.OPTIONS": "X\nINCLUDE zzincl\nINCLUDE zzincl2\n", "zzincl": "zzk = 41\n", "zzincl2": "zzm = 2\n"},
           "x = 1\nx = 2\nx = = 3\n", "4")


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
    say("sandbox-oq2: CANNOT RUN - " + msg)
    sys.exit(2)


def sess(box, *cmds):
    p = subprocess.run([sys.executable, TOOL, box, "sess", os.path.join(box, "user_accounts")] + list(cmds),
                       capture_output=True, text=True, timeout=900)
    out = ANSI.sub("", p.stdout + p.stderr)
    return out.split(":TERM 200,9999", 1)[-1]


def write(path, text):
    with open(path, "w") as f:
        f.write(text)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-oq2.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    bp = os.path.join(sysd, "bp")
    say("sandbox-oq2: sandbox %s" % box)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-oq2: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    # The $BASIC.OPTIONS record is read from the source file of the program being compiled, so a case that has one
    # gets its own source file (a directory file under the account); the others compile from bp.
    say("\n--- the items -----------------------------------------------------------------")
    made = []
    try:
        for i, (label, files, body, want) in enumerate(CASES + [ERRCASE]):
            iserr = (label == ERRCASE[0])
            dirname = "zzoqd%02d" % i if files else None
            if dirname:
                out0 = sess(box, "CREATE.FILE %s DIRECTORY" % dirname)
                d = os.path.join(sysd, dirname)   # the sandbox's account is the system directory
                made.append(d + ".dic")
                made.append(d)
                for nm, text in files.items():
                    write(os.path.join(d, nm), text)
                srcdir, srcname = dirname, "zzoq%02d" % i
                prog = os.path.join(d, srcname)
            else:
                srcdir, srcname = "bp", "zzoq%02d" % i
                prog = os.path.join(bp, srcname)
                made.append(prog)
            text = "   x = ''\n" + "".join("   %s\n" % ln for ln in body.split("\n") if ln) + \
                   ("" if iserr else "   crt 'C%02d[':x:']'\n" % i) + "end\n"
            write(prog, text)
            out = sess(box, "BASIC %s %s" % (srcdir, srcname), "RUN %s %s" % (srcdir, srcname))
            if iserr:
                m = re.search(r"(?m)^(\d+): ", out)
                row("%s: wanted line %s" % (label, want), m is not None and m.group(1) == want,
                    "got %r" % (m.group(1) if m else None))
            else:
                m = re.search(r"(?m)^C%02d\[(.*)\]\s*$" % i, out)
                got = m.group(1) if m else None
                row("%s: wanted %r" % (label, want), got == want, "got %r" % got if m else "no output")
    finally:
        for p in made:
            if os.path.isdir(p):
                shutil.rmtree(p)
                if os.path.isdir(p + ".out"):
                    shutil.rmtree(p + ".out")
            elif os.path.exists(p):
                os.remove(p)
        # the VOC pointers of the scratch directory files
        sess(box, *["DELETE.FILE zzoqd%02d" % i for i in range(len(CASES) + 1)])
        for f in os.listdir(os.path.join(sysd, "bp.out")):
            if f.startswith("zzoq"):
                os.remove(os.path.join(sysd, "bp.out", f))

    run_verbs(box, sysd, bp)

    say("\nsandbox-oq2: %d passed, %d failed" % (passed, failed))
    sys.exit(0 if failed == 0 else 1)


def has(out, pat):
    return re.search(pat, out, re.M) is not None


def slurp(path):
    try:
        with open(path, "rb") as f:
            return f.read()
    except OSError:
        return None


def run_verbs(box, sysd, bp):
    """The new commands and subroutines (A-14): OSCOPY, IOSCOPY, COMPARE.FILES, FIXDIR, MULTISORT."""
    say("\n--- the new commands ----------------------------------------------------------")
    d = os.path.join(sysd, "zzoqw")
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    a, b = os.path.join(d, "a"), os.path.join(d, "b")
    write(a, "hello\n")
    probe = os.path.join(bp, "zzoqp1")
    made = [probe]
    try:
        # --- OSCOPY (517) -------------------------------------------------------------------------------
        out = sess(box, "OSCOPY %s %s" % (a, b))
        row("517: OSCOPY copies a file", has(out, r"copied to") and slurp(b) == b"hello\n", out[-120:])
        out = sess(box, "OSCOPY %s %s" % (a, b))
        row("517: and refuses to replace it without an option", has(out, r"already exists") and slurp(b) == b"hello\n", out[-120:])
        out = sess(box, "OSCOPY %s %s APPEND" % (a, b))
        row("517: APPEND adds the source to the end of the target", slurp(b) == b"hello\nhello\n", repr(slurp(b)))
        write(a, "new\n")
        out = sess(box, "OSCOPY %s %s OVERWRITE" % (a, b))
        row("517: OVERWRITE replaces it", slurp(b) == b"new\n", repr(slurp(b)))
        out = sess(box, "OSCOPY %s %s" % (os.path.join(d, "none"), os.path.join(d, "c")))
        row("517: a missing source is reported", has(out, r"not found") and slurp(os.path.join(d, "c")) is None, out[-120:])

        # --- !IOSCOPY (369) and !MULTISORT (568) through a probe program --------------------------------------
        sub = os.path.join(d, "tree", "sub")
        os.makedirs(sub)
        write(os.path.join(d, "tree", "f1"), "one\n")
        write(os.path.join(sub, "f2"), "two\n")
        write(probe, ("   call !ioscopy('%s', '%s', st1)\n"
                      "   data = 'b':@vm:'c':@vm:'a':@fm:'2':@vm:'3':@vm:'1':@fm:'x':@vm:'y':@vm:'z'\n"
                      "   call !multisort(data, 1, 'AL')\n"
                      "   crt 'P1[':st1:'/':change(change(data, @fm, '|'), @vm, ','):']'\n"
                      "   data2 = '10':@vm:'9':@vm:'100':@fm:'p':@vm:'q':@vm:'r'\n"
                      "   call !multisort(data2, 1, 'DR')\n"
                      "   crt 'P2[':change(change(data2, @fm, '|'), @vm, ','):']'\n"
                      "end\n") % (os.path.join(d, "tree"), os.path.join(d, "tree2")))
        out = sess(box, "BASIC bp zzoqp1", "RUN bp zzoqp1")
        row("369: IOSCOPY copies a directory tree",
            slurp(os.path.join(d, "tree2", "sub", "f2")) == b"two\n" and slurp(os.path.join(d, "tree2", "f1")) == b"one\n",
            "tree2 not copied")
        row("369: and says status 0", has(out, r"^P1\[0/"), out[-200:])
        row("568: MULTISORT sorts list 1 and carries the others (stable, ascending left)",
            has(out, r"^P1\[0/a,b,c\|1,2,3\|z,x,y\]"), out[-200:])
        row("568: DR sorts numerically descending, and the related list follows",
            has(out, r"^P2\[100,10,9\|r,p,q\]"), out[-200:])

        # --- FIXDIR (458) ---------------------------------------------------------------------------------
        sess(box, "DELETE.FILE zzoqfd", "CREATE.FILE zzoqfd DIRECTORY")
        fd = os.path.join(sysd, "zzoqfd")
        write(os.path.join(fd, "r1"), "a\r\nb\r\n")
        write(os.path.join(fd, "r2"), "clean\n")
        out = sess(box, "FIXDIR zzoqfd")
        row("458: FIXDIR removes the carriage returns", slurp(os.path.join(fd, "r1")) == b"a\nb\n", repr(slurp(os.path.join(fd, "r1"))))
        row("458: and leaves a clean record alone and says how many it fixed",
            slurp(os.path.join(fd, "r2")) == b"clean\n" and has(out, r"1 record\(s\) fixed in zzoqfd"), out[-150:])

        # --- COMPARE.FILES (534) --------------------------------------------------------------------------
        write(probe, ("   execute 'CREATE.FILE zzoqc1' capturing j1\n"
                      "   execute 'CREATE.FILE zzoqc2' capturing j2\n"
                      "   open 'zzoqc1' to f1 else stop\n"
                      "   open 'zzoqc2' to f2 else stop\n"
                      "   write 'same' on f1, 'k1'\n   write 'same' on f2, 'k1'\n"
                      "   write 'left' on f1, 'k2'\n   write 'right' on f2, 'k2'\n"
                      "   write 'x' on f1, 'k3'\n"
                      "   write 'y' on f2, 'k4'\n"
                      "end\n"))
        sess(box, "BASIC bp zzoqp1", "RUN bp zzoqp1")
        out = sess(box, "COMPARE.FILES zzoqc1 zzoqc2 DETAIL")
        row("534: COMPARE.FILES counts the records only in the first", has(out, r"Records only in zzoqc1: 1") and has(out, r"^   k3"), out[-300:])
        row("534: only in the second", has(out, r"Records only in zzoqc2: 1") and has(out, r"^   k4"), out[-300:])
        row("534: those that differ", has(out, r"Records in both that differ: 1") and has(out, r"^   k2"), out[-300:])
        row("534: and those that are the same", has(out, r"Records that are the same: 1"), out[-300:])
        out = sess(box, "COMPARE.FILES zzoqc1 zzoqc1")
        row("534: a file against itself differs in nothing",
            has(out, r"Records only in zzoqc1: 0") and has(out, r"Records in both that differ: 0") and has(out, r"same: 3"), out[-300:])

        # --- inline prompts: control letters in any case, quoted prompt text (171, 377) ---------------------------
        out = sess(box, "SH echo cap_<<A,Name>>_end", "xyz")
        row("171 CONTROL: <<A,Name>> prompts and substitutes the answer", has(out, r"^cap_xyz_end") and has(out, r"Name="), out[-200:])
        out = sess(box, "SH echo low_<<a,Name>>_end", "xyz")
        row("171: <<a,Name>> is the same with a lower case control", has(out, r"^low_xyz_end") and has(out, r"Name="), out[-200:])
        out = sess(box, "SH echo u_<<u,Name>>_end", "xyz")
        row("171: <<u,Name>> (lower case) makes the answer upper case", has(out, r"^u_XYZ_end"), out[-200:])
        out = sess(box, 'SH echo quo_<<A,"Name, please">>_end', "xyz")
        row("377: a quoted prompt text may hold a comma and is shown whole",
            has(out, r"^quo_xyz_end") and has(out, r"Name, please="), out[-250:])

        # --- COMO APPEND, IN, mapped names (8, 361, 9) ----------------------------------------------------------
        sess(box, "DELETE.FILE zzcd", "CREATE.FILE zzcd DIRECTORY")
        como_dir = os.path.join(sysd, "$COMO")
        sess(box, "COMO ON zzoqm1", "SH echo MARK_ONE", "COMO OFF")
        first = slurp(os.path.join(como_dir, "zzoqm1")) or b""
        row("8 CONTROL: COMO ON writes the session to the record", b"MARK_ONE" in first, repr(first[-80:]))
        sess(box, "COMO ON zzoqm1 APPEND", "SH echo MARK_TWO", "COMO OFF")
        both = slurp(os.path.join(como_dir, "zzoqm1")) or b""
        row("8: COMO ON ... APPEND adds to the existing record", b"MARK_ONE" in both and b"MARK_TWO" in both, repr(both[-120:]))
        sess(box, "COMO ON zzoqm1", "SH echo MARK_THREE", "COMO OFF")
        again = slurp(os.path.join(como_dir, "zzoqm1")) or b""
        row("8: without APPEND the record is replaced as before", b"MARK_THREE" in again and b"MARK_ONE" not in again, repr(again[-120:]))
        sess(box, "COMO ON zzoqm2 IN zzcd", "SH echo MARK_FOUR", "COMO OFF")
        alt = slurp(os.path.join(sysd, "zzcd", "zzoqm2")) or b""
        row("361: COMO ON ... IN dirfile writes to that directory file", b"MARK_FOUR" in alt, repr(alt[-80:]))
        # (9, mapped record names: map_t1_id() maps only when the file's own mapping flag is on, and the como path
        #  carries no file, so COMO calls ospath(..., OS$MAPPED.NAME) and gets the map the session has; no row)
        for n in ("zzoqm1",):
            if os.path.exists(os.path.join(como_dir, n)):
                os.remove(os.path.join(como_dir, n))
        sess(box, "DELETE.FILE zzcd")

        # --- paragraph IF: EXISTS, IN, NO.CASE (28, 230, 426, 476) -------------------------------------------
        paras = [
            ("IF EXISTS zzpf r1 THEN SH echo HIT_E1", "HIT_E1", True, "28: IF EXISTS finds a record that is there"),
            ("IF EXISTS zzpf r2 THEN SH echo HIT_E2", "HIT_E2", False, "28: IF EXISTS does not fire for a record that is not"),
            ("IF NOT.EXISTS zzpf r2 THEN SH echo HIT_E3", "HIT_E3", True, "28: IF NOT.EXISTS fires for a missing record"),
            ("IF NOT.EXISTS zzpf r1 THEN SH echo HIT_E4", "HIT_E4", False, "28: and not for one that is there"),
            ("IF b IN a b c THEN SH echo HIT_I1", "HIT_I1", True, "230: IF value IN list, a member"),
            ("IF x IN a b c THEN SH echo HIT_I2", "HIT_I2", False, "230: IN, not a member"),
            ("IF x NOT.IN a b c THEN SH echo HIT_I3", "HIT_I3", True, "230: NOT.IN, not a member"),
            ("IF b NOT.IN a b c THEN SH echo HIT_I4", "HIT_I4", False, "230: NOT.IN, a member"),
            ("IF B IN a b c THEN SH echo HIT_I5", "HIT_I5", False, "426 CONTROL: IN is case sensitive without NO.CASE"),
            ("IF B IN a b c NO.CASE THEN SH echo HIT_I6", "HIT_I6", True, "426: IN with NO.CASE ignores case"),
            ("IF b IN a b AND c IN c d THEN SH echo HIT_I7", "HIT_I7", True, "230: two IN tests joined by AND"),
            ("IF Hello EQ hello THEN SH echo HIT_C1", "HIT_C1", False, "476 CONTROL: a comparison is case sensitive"),
            ("IF Hello EQ hello NO.CASE THEN SH echo HIT_C2", "HIT_C2", True, "476: NO.CASE makes it ignore case"),
            ("IF Hello NE hello NO.CASE THEN SH echo HIT_C3", "HIT_C3", False, "476: and NE then says they are alike"),
        ]
        write(probe, ("   execute 'CREATE.FILE zzpf' capturing j1\n   open 'zzpf' to f else stop\n   write 'x' on f, 'r1'\n"
                      "   open 'VOC' to v else stop\n" +
                      "".join("   write 'PA':@fm:'%s' on v, 'zzpa%d'\n" % (p[0].replace("'", "''") if False else p[0], i)
                              for i, p in enumerate(paras)) + "end\n"))
        sess(box, "BASIC bp zzoqp1", "RUN bp zzoqp1")
        out = sess(box, *["ZZPA%d" % i for i in range(len(paras))])
        for i, (cmd, hit, want, label) in enumerate(paras):
            row("%s (%s)" % (label, cmd), has(out, r"^%s\s*$" % hit) == want, "hit=%s" % has(out, r"^%s\s*$" % hit))
        sess(box, "DELETE.FILE zzpf")

        # --- DELETE with a record locked by someone else (50) -----------------------------------------------
        holder = os.path.join(bp, "zzoqh1")
        made.append(holder)
        write(holder, ("   open 'zzoqc1' to f else stop\n   readu x from f, 'k2' else null\n   sleep 12\n   release\nend\n"))
        sess(box, "BASIC bp zzoqh1")
        p = subprocess.Popen([sys.executable, TOOL, box, "sess", os.path.join(box, "user_accounts"), "RUN bp zzoqh1"],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        time.sleep(4)   # the holder has the lock by now
        out = sess(box, "DELETE zzoqc1 k2 k3 NO.QUERY", "DELETE zzoqc1 ALL NO.QUERY")
        p.wait(timeout=60)
        row("50: DELETE of a locked record warns and goes on to the next one", has(out, r"Record 'k2' is locked by another user"), out[-300:])
        row("50: the unlocked record was deleted", has(out, r"1 record\(s\) deleted"), out[-300:])
        row("50: and ALL skips the locked one with the same warning, rather than waiting",
            out.count("is locked by another user") >= 2, out[-300:])

        # --- DELETE.COMMON ALL EXCEPT (425) -----------------------------------------------------------------
        write(probe, ("   common /zzca/ a\n   common /zzcb/ b\n   common /zzcc/ c\n   a = 1 ; b = 2 ; c = 3\n   crt 'made'\nend\n"))
        out = sess(box, "BASIC bp zzoqp1", "RUN bp zzoqp1", "LIST.COMMON",
                   "DELETE.COMMON ALL EXCEPT zzcb", "LIST.COMMON")
        shown = out.split("DELETE.COMMON ALL EXCEPT", 1)
        before, after = shown[0], (shown[1] if len(shown) > 1 else "")
        row("425 CONTROL: all three blocks exist before", has(before, r"^ZZCA") and has(before, r"^ZZCB") and has(before, r"^ZZCC"),
            before[-200:])
        row("425: DELETE.COMMON ALL EXCEPT zzcb keeps zzcb and removes the others",
            has(after, r"^ZZCB") and not has(after, r"^ZZCA") and not has(after, r"^ZZCC"), after[-200:])
        sess(box, "DELETE.COMMON zzcb")
    finally:
        sess(box, "DELETE.FILE zzoqfd", "DELETE.FILE zzoqc1", "DELETE.FILE zzoqc2")
        shutil.rmtree(d, ignore_errors=True)
        for p in made:
            if os.path.exists(p):
                os.remove(p)
        for f in ("zzoqp1",):
            p = os.path.join(sysd, "bp.out", f)
            if os.path.exists(p):
                os.remove(p)


if __name__ == "__main__":
    main()
