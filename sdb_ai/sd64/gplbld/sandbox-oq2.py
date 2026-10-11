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
    ("63: MD5 of abc is the 32 character lower case digest", {}, "x = md5('abc')", "900150983cd24fb0d6963f7d28e17f72"),
    ("63: MD5 of the openQM example Hello World", {}, "x = md5('Hello World')", "b10a8db164e0754105b7a99be72e3fe5"),
    ("63: MD5 of the null string", {}, "x = md5('')", "d41d8cd98f00b204e9800998ecf8427e"),
    ("63: MD5 of a string with a field mark in it (bytes, not text)", {}, "x = len(md5('a':@fm:'b'))", "32"),
    ("581 CONTROL: TIME() is a whole number of seconds without the mode", {}, "t = time()\nx = (t = int(t))", "1"),
    ("581: $MODE TIME.MS makes TIME() seconds to the millisecond, within half a second of SYSTEM(1020)/1000",
     {}, "$mode time.ms\nt = time()\nx = (abs(t - system(1020) / 1000) < 0.5)", "1"),
    ("581: and it is not a whole number (tried three times; a whole second is one chance in a thousand)",
     {}, "$mode time.ms\nx = 0\nfor i = 1 to 3\n   t = time()\n   if t # int(t) then x = 1\n   sleep 1\nnext i", "1"),
    ("52 CONTROL: a named common block holds its value", {}, "common /zzcn/ a, b\ncommon /zzcm/ c\na = 5 ; b = 6 ; c = 7\nx = a + b + c", "18"),
    ("52: CLEARCOMMON name sets that block to zero and leaves the others",
     {}, "common /zzcn/ a, b\ncommon /zzcm/ c\na = 5 ; b = 6 ; c = 7\nclearcommon zzcn\nx = a:'/':b:'/':c", "0/0/7"),
    ("52: CLEARCOMMON alone still clears the unnamed block only",
     {}, "common a, b\ncommon /zzcm/ c\na = 5 ; b = 6 ; c = 7\nclearcommon\nx = a:'/':b:'/':c", "0/0/7"),
    ("391: SADD of two numbers longer than any float", {},
     "x = sadd('123456789012345678901234567890', '987654321098765432109876543210')", "1111111110111111111011111111100"),
    ("391: SADD with signs", {}, "x = sadd('5', '-8')", "-3"),
    ("391: SSUB", {}, "x = ssub('1000000000000000000000', '1')", "999999999999999999999"),
    ("391: SSUB going negative", {}, "x = ssub('3', '10')", "-7"),
    ("391: SMUL of two 20 digit numbers", {}, "x = smul('12345678901234567890', '98765432109876543210')",
     "1219326311370217952237463801111263526900"),
    ("391: SMUL by zero is 0, not -0", {}, "x = smul('-5', '0')", "0"),
    ("391: SDIV with a fraction, 15 places, trailing zeros dropped", {}, "x = sdiv('10', '4')", "2.5"),
    ("391: SDIV that does not end", {}, "x = sdiv('1', '3')", "0.333333333333333"),
    ("391: SDIV of a negative", {}, "x = sdiv('-7', '2')", "-3.5"),
    ("391: SCMP less, equal, greater", {}, "x = scmp('9', '10'):'/':scmp('5.0', '5'):'/':scmp('-1', '-2')", "-1/0/1"),
    ("468: SADD with decimals", {}, "x = sadd('0.1', '0.2')", "0.3"),
    ("468: SMUL with decimals", {}, "x = smul('1.5', '-2.25')", "-3.375"),
    ("468: SSUB with decimals of different lengths", {}, "x = ssub('10', '0.001')", "9.999"),
    ("472: EREPLACE, the openQM example", {}, "x = ereplace('The quick brown fox jumps over the lazy dog.', 'fox', 'cat')",
     "The quick brown cat jumps over the lazy dog."),
    ("472: EREPLACE replaces every occurrence by default", {}, "x = ereplace('a-b-c-d', '-', '+')", "a+b+c+d"),
    ("472: with an occurrence count", {}, "x = ereplace('a-b-c-d', '-', '+', 2)", "a+b+c-d"),
    ("472: with a count and a start", {}, "x = ereplace('a-b-c-d', '-', '+', 1, 3)", "a-b-c+d"),
    ("472: a count below 1 means all", {}, "x = ereplace('a-b-c-d', '-', '+', 0)", "a+b+c+d"),
    ("472: a null NEW deletes", {}, "x = ereplace('a-b-c', '-', '')", "abc"),
    ("472: a null OLD puts NEW in front of the string", {}, "x = ereplace('world', '', 'hello ')", "hello world"),
    ("472 FIX: the openQM example, default precision 4 rounds 37.73629273 to 37.7363", {}, "x = fix(37.73629273)", "37.7363"),
    ("472 FIX: precision 2 rounds up", {}, "x = fix(37.73629273, 2)", "37.74"),
    ("472 FIX: mode 1 truncates", {}, "x = fix(37.73629273, 2, 1)", "37.73"),
    ("472 FIX: the places asked for are kept, zeros included", {}, "x = fix(37.5, 2)", "37.50"),
    ("472 FIX: precision 0 gives a whole number, rounded", {}, "x = fix(2.5, 0):'/':fix(2.4, 0)", "3/2"),
    ("472 FIX: a negative number rounds away from zero and truncates toward it", {}, "x = fix(-2.675, 2):'/':fix(-2.675, 2, 1)", "-2.68/-2.67"),
    ("472 FIX: the program's PRECISION is the default", {}, "precision 2\nx = fix(1.23456)", "1.23"),
    ("509 MATSTR: the openQM example, a 3 x 2 matrix: a field for each row, a value for each column", {},
     "dim data(3, 2)\ndata(1, 1) = 'John' ; data(1, 2) = 'Doe'\ndata(2, 1) = 'Jane' ; data(2, 2) = 'Smith'\n"
     "data(3, 1) = 'Bob' ; data(3, 2) = 'Johnson'\nx = change(change(matstr(data), @vm, ','), @fm, '/')", "John,Doe/Jane,Smith/Bob,Johnson"),
    ("509 MATSTR: an empty cell in a 2 x 2 keeps its place", {},
     "dim m(2, 2)\nmat m = ''\nm(1, 2) = 'b' ; m(2, 1) = 'c'\nx = change(change(matstr(m), @vm, ','), @fm, '/')", ",b/c,"),
    ("509 MATSTR: a one dimensional matrix is an FM list like MATBUILD, trailing nulls off", {},
     "dim v(5)\nmat v = ''\nv(1) = 'a' ; v(2) = 'b' ; v(3) = 'c'\nx = change(matstr(v), @fm, '/')", "a/b/c"),
    ("509 CONTROL: MATBUILD of the same one dimensional matrix", {},
     "dim v(5)\nmat v = ''\nv(1) = 'a' ; v(2) = 'b' ; v(3) = 'c'\nmatbuild s from v\nx = change(s, @fm, '/')", "a/b/c"),
    ("509 MATSTR: the zero element of a one dimensional matrix is not used", {},
     "dim v(2)\nv(0) = 'zero' ; v(1) = 'a' ; v(2) = 'b'\nx = change(matstr(v), @fm, '/')", "a/b"),
    ("472 CONTROL: CHANGE gives the same as EREPLACE for a non-null OLD", {}, "x = change('a-b-c-d', '-', '+', 2)", "a+b+c-d"),
    ("510: REGEX finds a match anywhere", {}, "x = regex('hello world', 'wor')", "1"),
    ("510: REGEX with an anchor and a class", {}, "x = regex('abc123', '^[a-z]+[0-9]+$'):regex('abc123x', '^[a-z]+[0-9]+$')", "10"),
    ("510: REGEX is case sensitive unless the pattern begins (?i)", {}, "x = regex('ABC', 'abc'):regex('ABC', '(?i)abc')", "01"),
    ("315 CONTROL: a single template that matches leaves INMAT() at 1", {}, "y = ('abc' matches '3A')\nx = inmat()", "1"),
    ("315: MATCHES with a multivalued template - INMAT() is the first value that matched", {},
     "y = ('123' matches '3N':@vm:'3A')\nx = y:'/':inmat()", "1/1"),
    ("315: and the second value", {}, "y = ('abc' matches '3N':@vm:'3A')\nx = y:'/':inmat()", "1/2"),
    ("315: and the third, when the first two do not match", {},
     "y = ('ab12' matches '3N':@vm:'3A':@vm:'2A2N')\nx = y:'/':inmat()", "1/3"),
    ("315: the first value that matches wins when two would", {},
     "y = ('abc' matches '3A':@vm:'3X')\nx = y:'/':inmat()", "1/1"),
    ("315: no value matches - INMAT() is 0, not what the previous MATCHES left", {},
     "y = ('abc' matches '3N':@vm:'3A')\nz = ('a1' matches '3N':@vm:'3A')\nx = z:'/':inmat()", "0/0"),
    ("315: MATCHFIELD sets it too, and still returns the component", {},
     "y = matchfield('abc123', '3N3A':@vm:'3A3N', 2)\nx = inmat():'/':y", "2/123"),
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

        # --- MAP NO.PAGE / LOCAL, CATALOG RELATIVE, OPTION CATALOGUE.LOCAL, OPTION DIR.SEL.OMIT.HIDDEN ----------
        lc = os.path.join(bp, "zzoqlc")
        lr = os.path.join(bp, "zzoqlr")
        made += [lc, lr]
        write(lc, "   crt 'RAN_LC'\nend\n")
        write(lr, "   crt 'RAN_LR'\nend\n")
        out = sess(box, "BASIC bp zzoqlc", "BASIC bp zzoqlr", "CATALOG bp zzoqlc LOCAL", "MAP LOCAL NO.PAGE")
        row("287: MAP LOCAL lists the locally catalogued programs", has(out, r"^L\s+zzoqlc") and not has(out, r"^\*"), out[-300:])
        row("153: MAP ... NO.PAGE runs and still ends with its total", has(out, r"Total:"), out[-300:])
        out = sess(box, "CATALOG bp zzoqlr LOCAL RELATIVE", "ZZOQLR")
        read_voc = sess(box, "CT VOC zzoqlr")
        row("131: CATALOG ... LOCAL RELATIVE keeps a relative path in the VOC pointer",
            has(read_voc, r"^1: V") and has(read_voc, r"^3: bp\.out/zzoqlr") and not has(read_voc, r"^3: /"), read_voc[-300:])
        row("131: and the program still runs through it", has(out, r"RAN_LR"), out[-200:])
        sess(box, "DELETE.CATALOG zzoqlc LOCAL", "DELETE.CATALOG zzoqlr LOCAL")
        out = sess(box, "OPTION CATALOGUE.LOCAL", "CATALOG bp zzoqlc", "DELETE.CATALOG zzoqlc")
        row("288: with OPTION CATALOGUE.LOCAL, CATALOG with no mode catalogues locally", has(out, r"added to local catalogue"), out[-300:])
        row("288: and DELETE.CATALOG deletes the local entry by default", not has(out, r"not found|not in"), out[-300:])
        out = sess(box, "MAP LOCAL")
        row("288: after that no local entry is left", not has(out, r"zzoqlc"), out[-200:])
        hd = os.path.join(sysd, "zzoqhd")
        sess(box, "DELETE.FILE zzoqhd", "CREATE.FILE zzoqhd DIRECTORY")
        write(os.path.join(hd, "visible"), "x\n")
        write(os.path.join(hd, ".hidden"), "x\n")
        out = sess(box, "SELECT zzoqhd", "OPTION DIR.SEL.OMIT.HIDDEN", "SELECT zzoqhd")
        counts = re.findall(r"(\d+) record\(s\) selected", out)
        row("445: SELECT of a directory file sees the dot file without the option and not with it",
            counts[:2] == ["2", "1"], repr(counts) + out[-200:])
        sess(box, "DELETE.FILE zzoqhd")

        # --- PHANTOM NO.MSG / DATA / LOG and !PHLOG (483, 137, 364, 87) ----------------------------------------
        got = os.path.join(bp, "zzoqph")
        made.append(got)
        write(got, "   input x\n   open 'VOC' to v else stop\n   write 'Y':@fm:x on v, 'zzph_got'\nend\n")
        sess(box, "BASIC bp zzoqph", "CATALOG bp zzoqph LOCAL", "DELETE.FILE zzcd2", "CREATE.FILE zzcd2 DIRECTORY")
        write(probe, ("   execute 'PHANTOM LIST.FILES' capturing o1\n   crt 'M1[':o1:']'\n"
                      "   execute 'PHANTOM NO.MSG LIST.FILES' capturing o2\n   uid = @system.return.code\n   crt 'M2[':o2:']'\n"
                      "   data 'zz_data_line'\n   execute 'PHANTOM NO.MSG DATA RUN bp zzoqph' capturing o3\n"
                      "   execute 'PHANTOM NO.MSG LOG zzcd2 LIST.FILES' capturing o4\n"
                      "   sleep 8\n"
                      "   call !phlog(uid, nm)\n   crt 'PHL[':nm:']'\n"
                      "   open 'VOC' to v else stop\n   read r from v, 'zzph_got' then crt 'GOT[':r<2>:']' else crt 'GOT[none]'\n"
                      "   delete v, 'zzph_got'\n   crt 'UID[':uid:']'\n"
                      "   crt 'LEFT[':@data.pending:']'\nend\n"))
        out = sess(box, "BASIC bp zzoqp1", "RUN bp zzoqp1")
        row("483 CONTROL: PHANTOM says that it started a phantom", has(out, r"^M1\[Started phantom user \d+"), out[-600:])
        row("483: PHANTOM NO.MSG does not", has(out, r"^M2\[\]"), out[-600:])
        row("137: PHANTOM DATA passes the DATA queue to the phantom, which read it with INPUT",
            has(out, r"^GOT\[zz_data_line\]"), out[-600:])
        row("137: and the parent's queue is empty afterwards", has(out, r"^LEFT\[\]"), out[-600:])
        row("87: !PHLOG returns the phantom's log record, PH<user>_...",
            re.search(r"(?m)^PHL\[(PH(\d+)_\S+)\]", out) is not None and
            re.search(r"(?m)^UID\[(\d+)\]", out) is not None and
            re.search(r"(?m)^PHL\[PH(\d+)_", out).group(1) == re.search(r"(?m)^UID\[(\d+)\]", out).group(1), out[-600:])
        zl = [n for n in os.listdir(os.path.join(sysd, "zzcd2"))] if os.path.isdir(os.path.join(sysd, "zzcd2")) else []
        row("364: PHANTOM LOG zzcd2 puts the phantom's log in that directory file", any(n.startswith("PH") for n in zl), repr(zl))
        sess(box, "DELETE.CATALOG zzoqph LOCAL", "DELETE.FILE zzcd2")

        # --- PDUMP statement, string length and environment in the dump (439, 22, 569) --------------------------
        import glob
        for old in glob.glob(os.path.join(sysd, "dumps", "sddump.*")):
            os.remove(old)
        write(probe, "   zzvar = 'abcdefghij'\n   pdump\n   crt 'AFTER_PDUMP'\nend\n")
        os.environ["ZZ_OQ_TOKEN"] = "s3cr3tvalue"
        out = sess(box, "BASIC bp zzoqp1", "RUN bp zzoqp1")
        del os.environ["ZZ_OQ_TOKEN"]
        dumps = glob.glob(os.path.join(sysd, "dumps", "sddump.*"))
        dtxt = (slurp(dumps[0]) or b"").decode("latin-1") if dumps else ""
        row("439: the PDUMP statement writes a process dump file and the program goes on",
            len(dumps) == 1 and has(out, r"AFTER_PDUMP") and "SD Process Dump" in dtxt, "dumps=%r out=%r" % (dumps, out[-200:]))
        row("22: the dump shows the length of a string variable", re.search(r'(?i)zzvar: String \(len=10\): "abcdefghij"', dtxt) is not None,
            dtxt[:600])
        row("569: the dump lists the environment, and hides the value of a name that looks like a secret",
            "\nEnvironment\n" in dtxt and re.search(r"(?m)^  PATH=", dtxt) is not None and "=(not shown)" not in "".join(
                l for l in dtxt.splitlines() if l.startswith("  PATH=")), dtxt[:400])
        row("569: a variable named TOKEN is listed with its value left out",
            "ZZ_OQ_TOKEN=(not shown)" in dtxt and "s3cr3tvalue" not in dtxt, dtxt[:300])
        for old in dumps:
            os.remove(old)

        # --- Q-pointer with a null file name means VOC (435) ------------------------------------------------
        write(probe, ("   open 'VOC' to v else stop\n   write 'Q':@fm:'':@fm:'' on v, 'zzqnull'\n"
                      "   open 'zzqnull' to f then\n      read r from f, 'zzqnull' then crt 'QN[':r<1>:']' else crt 'QN[norec]'\n"
                      "   end else crt 'QN[noopen]'\n   delete v, 'zzqnull'\nend\n"))
        out = sess(box, "BASIC bp zzoqp1", "RUN bp zzoqp1")
        row("435: a Q-pointer whose file name is null opens the VOC of the account (here: reads its own record, a Q)",
            has(out, r"^QN\[Q\]"), out[-300:])

        # --- LOGOUT n GROUP (386) ---------------------------------------------------------------------------
        sl = os.path.join(bp, "zzoqsl")
        gp = os.path.join(bp, "zzoqgp")
        gc = os.path.join(bp, "zzoqgc")
        made += [sl, gp, gc]
        write(sl, "   sleep 60\nend\n")
        write(gp, ("   execute 'PHANTOM NO.MSG RUN bp zzoqsl'\n   execute 'PHANTOM NO.MSG RUN bp zzoqsl'\n"
                   "   open 'VOC' to v else stop\n   write 'Y':@fm:@userno on v, 'zzgrp_parent'\n   sleep 40\nend\n"))
        write(gc, ("   include_users = 0\n   open 'VOC' to v else stop\n   read r from v, 'zzgrp_parent' else stop\n   n = r<2>\n"
                   "   gosub count\n   crt 'G1[':c:']'\n"
                   "   execute 'LOGOUT ':n:' GROUP'\n   sleep 4\n   gosub count\n   crt 'G2[':c:']'\n"
                   "   delete v, 'zzgrp_parent'\n   stop\n"
                   "count:\n   c = 0\n   call !listu(u)\n   for i = 1 to dcount(u, @fm)\n"
                   "      if u<i,5> + 0 = n then c += 1\n   next i\n   return\nend\n"))
        sess(box, "BASIC bp zzoqsl", "BASIC bp zzoqgp", "BASIC bp zzoqgc")
        pg = subprocess.Popen([sys.executable, TOOL, box, "sess", os.path.join(box, "user_accounts"), "RUN bp zzoqgp"],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        time.sleep(9)
        out = sess(box, "RUN bp zzoqgc")
        try:
            pg.wait(timeout=90)
        except subprocess.TimeoutExpired:
            pg.kill()
        row("386 CONTROL: the parent has two phantoms before the LOGOUT", has(out, r"^G1\[2\]"), out[-400:])
        row("386: LOGOUT n GROUP logs out the parent's phantoms as well", has(out, r"^G2\[0\]"), out[-400:])

        # --- OPENSEQ CREATING and SHARED (485, 397) --------------------------------------------------------
        sq = os.path.join(d, "sq.txt")
        sh = os.path.join(d, "shared.txt")
        hp = []
        for tag in ("A", "B"):
            pth = os.path.join(bp, "zzoqs" + tag)
            made.append(pth)
            hp.append(pth)
            write(pth, ("   openseq '%s' shared to f else stop\n   for i = 1 to 300\n      writeseq '%s' : i : ' ' : str('x', 40) to f else stop\n"
                        "   next i\n   closeseq f\nend\n") % (sh, tag))
        write(probe, ("   openseq '%s' to f then crt 'EXISTS_BEFORE' else crt 'MISSING_BEFORE'\n"
                      "   openseq '%s' creating to g then crt 'THEN_G' else crt 'ELSE_G'\n"
                      "   closeseq g\nend\n") % (sq, sq))
        out = sess(box, "BASIC bp zzoqp1", "RUN bp zzoqp1")
        row("485: OPENSEQ without CREATING of a file that is not there takes the ELSE", has(out, r"MISSING_BEFORE"), out[-300:])
        row("485: OPENSEQ ... CREATING makes the file at once and takes the THEN", has(out, r"THEN_G") and os.path.exists(sq), out[-300:])
        sess(box, "BASIC bp zzoqsA", "BASIC bp zzoqsB")
        pa = subprocess.Popen([sys.executable, TOOL, box, "sess", os.path.join(box, "user_accounts"), "RUN bp zzoqsA"],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        pb = subprocess.Popen([sys.executable, TOOL, box, "sess", os.path.join(box, "user_accounts"), "RUN bp zzoqsB"],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        pa.wait(timeout=120)
        pb.wait(timeout=120)
        body = (slurp(sh) or b"").decode("latin-1")
        lines = [l for l in body.split("\n") if l]
        row("397: two processes appending with SHARED lose no line (600 written, 600 found)", len(lines) == 600,
            "found %d lines" % len(lines))
        row("397: and every line is whole (a number, a space and 40 x)",
            all(re.fullmatch(r"[AB]\d+ x{40}", l) for l in lines), "a damaged line: %r" % [l for l in lines if not re.fullmatch(r"[AB]\d+ x{40}", l)][:2])

        # --- LIST.TRIGGERS with a directory file (321) ----------------------------------------------------------
        trg = os.path.join(bp, "zzoqtr")
        made.append(trg)
        write(trg, "subroutine zzoqtr(mode, file, id, rec, ctl)\n   return\nend\n")
        out = sess(box, "BASIC bp zzoqtr", "CATALOG bp zzoqtr LOCAL", "CREATE.FILE zzoqtd DIRECTORY",
                   "SET.TRIGGER zzoqtd zzoqtr PRE.WRITE", "LIST.TRIGGERS zzoqtd")
        row("321 (a finding, no change): SD refuses a trigger on a directory file, so LIST.TRIGGERS has none to show",
            has(out, r"Dynamic file required") and not has(out, r"^zzoqtd\s+\S+\s+PRE"), out[-500:])
        sess(box, "DELETE.CATALOG zzoqtr LOCAL", "DELETE.FILE zzoqtd")

        # --- CREATE.FILE COMMENT, MULTIFILE and a relative PATHNAME (383, 522, 278) ----------------------------
        os.makedirs(os.path.join(sysd, "zzoqreld"), exist_ok=True)
        sess(box, "DELETE.FILE zzoqcm", "DELETE.FILE zzoqmf", "DELETE.FILE zzoqrp")
        out = sess(box, 'CREATE.FILE zzoqcm COMMENT "Test file here"', "CT VOC zzoqcm", "CREATE.FILE zzoqmf MULTIFILE",
                   "CT VOC zzoqmf", "CREATE.FILE zzoqrp PATHNAME zzoqreld", "CT VOC zzoqrp")
        row("383: CREATE.FILE ... COMMENT puts the text after the type code in the VOC record", has(out, r"^1: F Test file here"), out[-700:])
        row("522: CREATE.FILE ... MULTIFILE makes the data portion a multifile named for the file",
            has(out, r"^4: zzoqmf"), out[-700:])
        row("278: a relative PATHNAME stays relative in the VOC record", has(out, r"^2: zzoqreld/zzoqrp"), out[-700:])
        sess(box, "DELETE.FILE zzoqcm", "DELETE.FILE zzoqmf", "DELETE.FILE zzoqrp")
        shutil.rmtree(os.path.join(sysd, "zzoqreld"), ignore_errors=True)

        # --- saved lists IN file (494), CREATE.INDEX DELETING and $INDEX.PATH (424, 184), LIST.INDEX LPTR (73) ----
        write(probe, ("   execute 'CREATE.FILE zzix' capturing j1\n   open 'zzix' to f else stop\n"
                      "   open 'DICT', 'zzix' to dv else stop\n"
                      "   write 'D':@fm:'1':@fm:'':@fm:'Fld':@fm:'10L':@fm:'S' on dv, 'FLD'\n"
                      "   write 'b' on f, 'r1'\n   write 'a' on f, 'r2'\n"
                      "   execute 'CREATE.FILE zzsl' capturing j2\n"
                      "   formlist 'p':@fm:'q':@fm:'r' to 0\nend\n"))
        sess(box, "BASIC bp zzoqp1", "RUN bp zzoqp1")
        out = sess(box, "CREATE.INDEX zzix FLD", "CREATE.INDEX zzix FLD")
        row("424 CONTROL: a second CREATE.INDEX of the same index is refused", has(out, r"Duplicate field name \(FLD\)"), out[-400:])
        out = sess(box, "CREATE.INDEX zzix FLD DELETING", "LIST.INDEX zzix ALL")
        row("424: CREATE.INDEX ... DELETING replaces it", not has(out, r"Duplicate field name") and has(out, r"Number of indices = 1"), out[-400:])
        out = sess(box, "LIST.INDEX zzix ALL LPTR")
        row("73: LIST.INDEX ... LPTR sends the report to the printer, not the screen",
            not has(out, r"Alternate key indices for file") and not has(out, r"(?i)unexpected"), out[-300:])
        ixd = os.path.join(d, "ixdir")      # must not exist yet: the first index makes the directory
        sess(box, "DELETE.INDEX zzix ALL")
        write(probe, ("   open 'VOC' to v else stop\n   write 'X':@fm:'%s' on v, '$INDEX.PATH'\nend\n" % ixd))
        sess(box, "BASIC bp zzoqp1", "RUN bp zzoqp1")
        out = sess(box, "CREATE.INDEX zzix FLD", "LIST.INDEX zzix ALL")
        row("184: CREATE.INDEX with no PATHNAME uses the $INDEX.PATH record", has(out, r"Indices relocated to") and ixd in out, out[-400:])
        sess(box, "DELETE.INDEX zzix ALL")
        write(probe, "   open 'VOC' to v else stop\n   delete v, '$INDEX.PATH'\nend\n")
        sess(box, "BASIC bp zzoqp1", "RUN bp zzoqp1")
        out = sess(box, "CREATE.INDEX zzix FLD", "LIST.INDEX zzix ALL")
        row("184: and without that record there is no relocation", not has(out, r"Indices relocated to"), out[-300:])
        write(probe, "   formlist 'p':@fm:'q':@fm:'r' to 0\nend\n")
        out = sess(box, "BASIC bp zzoqp1", "RUN bp zzoqp1", "SAVE.LIST zzsl1 IN zzsl", "GET.LIST zzsl1 IN zzsl", "GET.LIST zzsl1")
        row("494: SAVE.LIST ... IN file saves in that file and GET.LIST ... IN file reads it back",
            has(out, r"3 record\(s\) selected"), out[-400:])
        row("494: the default saved lists file does not hold it (there is none here, or the list is not in it)",
            has(out, r"Error \d+ opening \$savedlists|Saved select list 'zzsl1' not found"), out[-400:])
        out = sess(box, "DELETE.LIST zzsl1 IN zzsl")
        row("494: DELETE.LIST ... IN file deletes it", has(out, r"Deleted saved select list 'zzsl1'"), out[-300:])
        sess(box, "DELETE.FILE zzix", "DELETE.FILE zzsl")

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

        # --- !OPTION, !VOCPATH, DIR() size (224, 473, 86, 366) ----------------------------------------------------
        sz = os.path.join(d, "sizedir")
        os.makedirs(sz, exist_ok=True)
        write(os.path.join(sz, "f5"), "abcde")
        write(probe, ("   st = ''\n   call !option(40, st)\n   crt 'O1[':st:']'\n"
                      "   st = 1\n   call !option(40, st)\n   st = ''\n   call !option(40, st)\n   crt 'O2[':st:']'\n"
                      "   st = 0\n   call !option(40, st)\n   crt 'O3[':st:']'\n"
                      "   st = ''\n   call !option(999, st)\n   crt 'O4[':st:']'\n"
                      "   call !vocpath('bp', p, s)\n   crt 'V1[':s:'/':(p[len(p) - 1, 2] = 'bp'):']'\n"
                      "   call !vocpath('nonesuchfile', p, s)\n   crt 'V2[':(s # 0):'/':p:']'\n"
                      "   e = dir('%s')\n   crt 'D1[':e<1,1>:'/':e<1,2>:'/':e<1,3>:']'\nend\n") % sz)
        out = sess(box, "BASIC bp zzoqp1", "RUN bp zzoqp1")
        row("224 CONTROL: !OPTION reads an option that is off", has(out, r"^O1\[0\]"), out[-400:])
        row("473: !OPTION sets an option and reads it back as on", has(out, r"^O2\[1\]"), out[-400:])
        row("473: and clears it again", has(out, r"^O3\[0\]"), out[-400:])
        row("473: a number that is not an option comes back -1", has(out, r"^O4\[-1\]"), out[-400:])
        row("86: !VOCPATH gives the path of a VOC file name and status 0", has(out, r"^V1\[0/1\]"), out[-400:])
        row("86: and a status and a null path for a name that is not there", has(out, r"^V2\[1/\]"), out[-400:])
        row("366: DIR() returns the size in bytes as a third value", has(out, r"^D1\[f5/F/5\]"), out[-400:])

        # --- MATSTR of a matrix passed to a subroutine (509) -----------------------------------------------------
        ms = os.path.join(bp, "zzoqms")
        made.append(ms)
        write(ms, "   subroutine zzoqms(mat a, out)\n   dim a(2, 2)\n   out = matstr(a)\n   return\nend\n")
        write(probe, ("   dim m(2, 2)\n   m(1, 1) = 'p' ; m(1, 2) = 'q' ; m(2, 1) = 'r' ; m(2, 2) = 's'\n"
                      "   call zzoqms(mat m, r)\n   crt 'MS[':change(change(r, @vm, ','), @fm, '/'):']'\nend\n"))
        out = sess(box, "BASIC bp zzoqms", "CATALOG bp zzoqms LOCAL", "BASIC bp zzoqp1", "RUN bp zzoqp1", "DELETE.CATALOG zzoqms LOCAL")
        row("509: MATSTR of a matrix passed into a subroutine", has(out, r"^MS\[p,q/r,s\]"), out[-400:])

        # --- SETPTR INFORM and EJECT (51, 59) --------------------------------------------------------------------
        hold = os.path.join(sysd, "$hold")
        for nm in ("zzoqjob", "zzoqjob2"):
            if os.path.exists(os.path.join(hold, nm)):
                os.remove(os.path.join(hold, nm))
        write(probe, "   printer on\n   print 'line one'\n   printer close\nend\n")
        out = sess(box, "SETPTR 0,80,60,0,0,3,AS zzoqjob,INFORM,EJECT,BRIEF", "BASIC bp zzoqp1", "RUN bp zzoqp1")
        body = slurp(os.path.join(hold, "zzoqjob")) or b""
        row("51: SETPTR ... INFORM says where the output file is when the job starts",
            has(out, r"Print output is going to .*zzoqjob"), out[-300:])
        row("59: SETPTR ... EJECT ends the job with a form feed", b"line one" in body and body.endswith(b"\f"), repr(body[-30:]))
        out = sess(box, "SETPTR 0,80,60,0,0,3,AS zzoqjob2,BRIEF", "RUN bp zzoqp1")
        body2 = slurp(os.path.join(hold, "zzoqjob2")) or b""
        row("51/59 CONTROL: without the options there is no message and no form feed at the end",
            not has(out, r"Print output is going to") and b"line one" in body2 and not body2.endswith(b"\f"), repr(body2[-30:]) + out[-200:])
        for nm in ("zzoqjob", "zzoqjob2"):
            if os.path.exists(os.path.join(hold, nm)):
                os.remove(os.path.join(hold, nm))
        sess(box, "DELETE.FILE zzoqhf", "CREATE.FILE zzoqhf DIRECTORY")
        sess(box, "SETPTR 0,80,60,0,0,3,AS zzjob3 IN zzoqhf,BRIEF", "RUN bp zzoqp1")
        body3 = slurp(os.path.join(sysd, "zzoqhf", "zzjob3")) or b""
        row("448: SETPTR ... AS name IN dirfile keeps the job in that directory file, not $HOLD",
            b"line one" in body3 and not os.path.exists(os.path.join(hold, "zzjob3")), repr(body3))
        sess(box, "DELETE.FILE zzoqhf")
        sess(box, "SETPTR 0,80,60,0,0,1,BRIEF")

        # --- !TESTLOCK (42) -------------------------------------------------------------------------------------
        write(probe, ("   call !testlock(7, o1)\n   lock 7\n   call !testlock(7, o2)\n   unlock 7\n   call !testlock(7, o3)\n"
                      "   crt 'TL[':o1:'/':(o2 = @userno):'/':o3:']'\nend\n"))
        out = sess(box, "BASIC bp zzoqp1", "RUN bp zzoqp1")
        row("42: !TESTLOCK is 0 for a free task lock, the owner's user number while held, and 0 again",
            has(out, r"^TL\[0/1/0\]"), out[-300:])

        # --- !MERGELIST (420, 539, 566) -------------------------------------------------------------------------
        def lst(s):
            return "'" + "':@fm:'".join(s.split(",")) + "'" if s else "''"
        merges = [
            ("a,c,e", "b,c,d", "", "a,b,c,d,e", "420: the default merge is the union, in order"),
            ("a,c,e", "b,c,d", "A", "a,b,c,c,d,e", "420: mode A keeps duplicates"),
            ("a,c,e", "b,c,d", "I", "c", "420: mode I is the items in both"),
            ("a,c,e", "b,c,d", "D", "a,e", "420: mode D is list 1 without list 2"),
            ("a,c,e", "b,c,d", "X", "a,b,d,e", "420: mode X is the items in one only"),
            ("a,c,e", "b,c,d", "U DL", "e,d,c,b,a", "420: DL puts the result in descending order"),
            ("10,9", "100,1", "AR", "1,9,10,100", "420: AR orders numerically"),
            ("", "b,a", "U", "a,b", "539: an empty first list"),
            ("a,b", "", "U", "a,b", "539: an empty second list"),
            ("", "b,a", "I", "", "539: an empty list gives no items in both"),
            ("", "", "U", "", "539: two empty lists"),
            ("e,a,c", "d,b", "U N", "a,b,c,d,e", "566: lists that are not in order, with the N word"),
        ]
        body = ""
        for i, (a, b, m, want, label) in enumerate(merges):
            body += ("   l1 = %s\n   l2 = %s\n   call !mergelist(r, l1, l2, '%s')\n   crt 'ML%d[':change(r, @fm, ','):']'\n"
                     % (lst(a), lst(b), m, i))
        write(probe, body + "end\n")
        out = sess(box, "BASIC bp zzoqp1", "RUN bp zzoqp1")
        for i, (a, b, m, want, label) in enumerate(merges):
            row("%s (%s | %s | %r)" % (label, a, b, m), has(out, r"^ML%d\[%s\]" % (i, re.escape(want))), out[-300:])

        # --- PHANTOM statement (390) ----------------------------------------------------------------------------
        write(probe, ("   phantom 'NO.MSG LIST.FILES' capturing o\n   uid = @system.return.code\n   sleep 6\n"
                      "   call !phlog(uid, nm)\n   crt 'PS[':(uid > 0):'/':(nm[1,2] = 'PH'):']'\nend\n"))
        out = sess(box, "BASIC bp zzoqp1", "RUN bp zzoqp1")
        row("390: the PHANTOM statement starts a phantom (a user number comes back and it makes its log)",
            has(out, r"^PS\[1/1\]"), out[-300:])

        # --- REBUILD.ALL.INDICES (58) and REDO (188) -------------------------------------------------------
        write(probe, ("   execute 'CREATE.FILE zzrb' capturing j1\n   open 'zzrb' to f else stop\n"
                      "   open 'DICT', 'zzrb' to dv else stop\n"
                      "   write 'D':@fm:'1':@fm:'':@fm:'Fld':@fm:'10L':@fm:'S' on dv, 'FLD'\n"
                      "   write 'b' on f, 'r1'\n   write 'a' on f, 'r2'\nend\n"))
        sess(box, "BASIC bp zzoqp1", "RUN bp zzoqp1", "CREATE.INDEX zzrb FLD")
        out = sess(box, "REBUILD.ALL.INDICES NO.QUERY")
        row("58: REBUILD.ALL.INDICES rebuilds the indices of a file that has them and says so",
            has(out, r"Indices of zzrb rebuilt") and re.search(r"(?m)^[1-9]\d* file\(s\) had their indices rebuilt", out) is not None, out[-500:])
        out = sess(box, "REBUILD.ALL.INDICES", "N")
        row("58: without NO.QUERY it asks, and N rebuilds nothing", has(out, r"Rebuild the indices of all files") and
            not has(out, r"Indices of zzrb rebuilt"), out[-400:])
        sess(box, "DELETE.INDEX zzrb ALL", "DELETE.FILE zzrb")
        t0 = time.time()
        out = sess(box, "REDO TIMES 3 EVERY 1 SH echo REDO_RAN")
        took = time.time() - t0
        row("188: REDO TIMES 3 runs the command three times", len(re.findall(r"(?m)^REDO_RAN\s*$", out)) == 3, out[-300:])
        row("188: and EVERY 1 spaces the runs a second apart (the whole took at least two seconds)", took >= 2.0, "took %.1f s" % took)

        # --- private vocabulary (1) -------------------------------------------------------------------------
        write(probe, ("   execute 'CREATE.FILE zzpv' capturing j1\n   open 'zzpv' to f else stop\n"
                      "   write 'PA':@fm:'SH echo PV_RAN' on f, 'zzpverb'\nend\n"))
        sess(box, "BASIC bp zzoqp1", "RUN bp zzoqp1")
        out = sess(box, "ZZPVERB")
        row("1 CONTROL: a command in no vocabulary is not run", not has(out, r"^PV_RAN") , out[-300:])
        write(probe, "   open 'VOC' to v else stop\n   write 'X':@fm:'zzpv' on v, '$PRIVATE.VOC'\nend\n")
        sess(box, "BASIC bp zzoqp1", "RUN bp zzoqp1")
        out = sess(box, "ZZPVERB", "zzpverb")
        row("1: with $PRIVATE.VOC naming the file, the command in it is found and run (typed either case)",
            len(re.findall(r"(?m)^PV_RAN\s*$", out)) == 2, out[-300:])
        write(probe, "   open 'VOC' to v else stop\n   delete v, '$PRIVATE.VOC'\nend\n")
        sess(box, "BASIC bp zzoqp1", "RUN bp zzoqp1", "DELETE.FILE zzpv")

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
        sess(box, "COMO ON zzoq=m3", "SH echo MARK_FIVE", "COMO OFF")
        names = os.listdir(como_dir)
        row("9: a record name with a restricted character (=) is mapped (%E) as in any directory file",
            "zzoq%Em3" in names and "zzoq=m3" not in names, repr(names))
        for n in ("zzoqm1", "zzoq%Em3"):
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

        # --- LISTDICT (10, 75): the Pick style dictionary listing, a paragraph over LIST DICT ----------------------
        write(probe, ("   execute 'CREATE.FILE zzoqld' capturing j1\n"
                      "   open 'DICT', 'zzoqld' to f else stop\n"
                      "   write 'D':@fm:1:@fm:'':@fm:'Name':@fm:'10L':@fm:'S' on f, 'name'\n"
                      "   write 'D':@fm:2:@fm:'MD0':@fm:'Qty':@fm:'5R':@fm:'S' on f, 'qty'\n"
                      "   write 'A':@fm:3:@fm:'Price':@fm:'':@fm:'':@fm:'':@fm:'MD2':@fm:'':@fm:'':@fm:'10':@fm:'R' on f, 'price'\n"
                      "   write 'I':@fm:'QTY * PRICE':@fm:'':@fm:'Total':@fm:'10R':@fm:'S' on f, 'total'\n"
                      "   write 'S':@fm:4:@fm:'Code' on f, 'code'\n"
                      "   write 'PH':@fm:'NAME QTY' on f, 'short'\n"
                      "   write 'X':@fm:'a comment' on f, 'note'\n"
                      "end\n"))
        sess(box, "BASIC bp zzoqp1", "RUN bp zzoqp1")
        out = sess(box, "LISTDICT zzoqld")
        full = sess(box, "LIST DICT zzoqld")
        row("10: LISTDICT lists an A-type record with its field number and conversion", has(out, r"^price\s+A\s+3\s+MD2\s+Price"), out[-400:])
        row("75: ...and D-type records", has(out, r"^name\s+D\s+1\s+Name\s+10L\s+S") and has(out, r"^qty\s+D\s+2\s+MD0\s+Qty"), out[-400:])
        row("75: ...and an I-type record with its expression", has(out, r"^total\s+I\s+QTY \* PRICE\s+Total"), out[-400:])
        row("10: ...and an S-type record", has(out, r"^code\s+S\s+4\s+Code"), out[-400:])
        row("10: ...and no phrase and no other type", not has(out, r"^short\s") and not has(out, r"^note\s"), out[-400:])
        row("10 CONTROL: LIST DICT of the same file does show the phrase and the other type",
            has(full, r"^short\s+PH") and has(full, r"^note\s+X"), full[-400:])
        row("10: the A, D, I and S records come to six with the dictionary's own @id", has(out, r"6 record\(s\) listed"), out[-300:])
        row("10: the records come in the order A, D, I, S",
            re.search(r"(?s)^price\s+A.*^name\s+D.*^total\s+I.*^code\s+S", out, re.M) is not None, out[-400:])
        row("10: an upper case file name works", has(sess(box, "LISTDICT ZZOQLD"), r"^price\s+A\s+3"), "")
        row("10: a file that does not exist is reported", has(sess(box, "LISTDICT zzoqnone"), r"File not found"), "")
        out = sess(box, "LISTDICT zzoqld LPTR")
        row("10: LPTR sends the listing to the printer: nothing of it on the screen, and no complaint about the word",
            not has(out, r"^price\s") and not has(out, r"record\(s\) listed") and not has(out, r"(?i)unrecognised|illegal|not found"), out[-300:])

        # --- COPY.LISTP (72): COPYP with the source file defaulting to $savedlists ----------------------------
        out = sess(box, 'SELECT VOC WITH @ID = "copyp" "list" "sort"', "SAVE.LIST zzoqla",
                   'SELECT VOC WITH @ID = "copy"', "SAVE.LIST zzoqlb")
        row("72 CONTROL: the two saved lists were made", has(out, r"3 record\(s\) selected") and not has(out, r"(?i)error|not found|cannot"), out[-300:])
        out = sess(box, "COPY.LISTP zzoqla (T")
        row("72: COPY.LISTP name (T shows the saved list of that name, the source file being $savedlists",
            has(out, r"Item zzoqla") and has(out, r"^0001 copyp") and has(out, r"^0002 list") and has(out, r"^0003 sort")
            and has(out, r"1 record\(s\) copied"), out[-400:])
        out = sess(box, "COPY.LISTP zzoqla (ST")
        row("72: S leaves out the field numbers", has(out, r"^copyp$") and not has(out, r"^0001 copyp"), out[-300:])
        out = sess(box, "COPY.LISTP zzoqla (IT")
        row("72: ...and I the id", not has(out, r"Item zzoqla") and has(out, r"copyp"), out[-300:])
        out = sess(box, "COPY.LISTP $savedlists zzoqla (T")
        row("72: a first word that opens as a file, with a list name after it, is the source file",
            has(out, r"Item zzoqla") and has(out, r"1 record\(s\) copied"), out[-300:])
        out = sess(box, "COPY.LISTP zzoqla zzoqlb (T")
        row("72: two list names are both in $savedlists, whichever of them could be a file",
            has(out, r"Item zzoqla") and has(out, r"Item zzoqlb") and has(out, r"2 record\(s\) copied"), out[-400:])
        out = sess(box, "COPY.LISTP * (T")
        row("72: * is every saved list", has(out, r"Item zzoqla") and has(out, r"Item zzoqlb"), out[-400:])
        out = sess(box, "COPY.LISTP zzoqnone (T")
        row("72: a list that does not exist is reported", has(out, r'Record "zzoqnone" not found') and has(out, r"0 record\(s\) copied"), out[-300:])
        out = sess(box, "COPY.LISTP zzoqla", "zzoqlc")
        row("72: with neither P nor T it asks for the destination and copies within $savedlists",
            has(out, r"Copied item zzoqla from \$savedlists to \$savedlists item zzoqlc"), out[-400:])
        out = sess(box, "COPY.LISTP zzoqlc (ST")
        row("72: and the copy holds the same list", has(out, r"^copyp$") and has(out, r"^list$") and has(out, r"^sort$"), out[-300:])
        out = sess(box, "COPY.LISTP zzoqla", "zzoqlc")
        row("72: an existing destination is not overwritten without O", has(out, r"Item zzoqla already exists in target file"), out[-300:])
        out = sess(box, "COPY.LISTP zzoqla (D", "zzoqld2")
        row("72: D moves the list", has(out, r"Moved item zzoqla from \$savedlists to \$savedlists item zzoqld2"), out[-300:])
        out = sess(box, "COPY.LISTP zzoqla (T")
        row("72: ...so the source list is gone", has(out, r'Record "zzoqla" not found'), out[-300:])
        out = sess(box, "COPY.LISTP DICT zzoqld name (ST")
        row("72: DICT names the dictionary of the file that follows", has(out, r"^D$") and has(out, r"^Name$"), out[-300:])
        out = sess(box, "COPYP voc copyp (ST")
        row("72 CONTROL: COPYP still wants its file name first", has(out, r"^CA$") and has(out, r"1 record\(s\) copied"), out[-300:])

        # --- SELECTINDEX command (119): the values of an AK index, or the ids that have one value ------------------
        write(probe, ("   execute 'CREATE.FILE zzoqix' capturing j1\n"
                      "   open 'zzoqix' to f else stop 'no file'\n"
                      "   open 'DICT', 'zzoqix' to df else stop 'no dict'\n"
                      "   write 'D':@fm:1:@fm:'':@fm:'Colour':@fm:'10L':@fm:'S' on df, 'colour'\n"
                      "   write 'red' on f, 'a'\n   write 'blue' on f, 'b'\n   write 'red' on f, 'c'\n   write 'green' on f, 'd'\n"
                      "   crt 'IX FILE MADE'\n"
                      "end\n"))
        out = sess(box, "BASIC bp zzoqp1", "RUN bp zzoqp1", "CREATE.INDEX zzoqix colour", "BUILD.INDEX zzoqix colour")
        row("119 CONTROL: the file and its index were made and built",
            has(out, r"IX FILE MADE") and has(out, r"Added index for colour") and has(out, r"4 records processed"), out[-300:])

        def listed(no, *cmds):
            """Run the commands, then show select list no as ITEMS[a,b,c]; returns (text, set of items or None)."""
            write(probe, ("   readlist items from %d else items = 'NONE'\n"
                          "   crt 'ITEMS[':change(items, @fm, ','):']'\n"
                          "end\n") % no)
            text = sess(box, "BASIC bp zzoqp1", *(list(cmds) + ["RUN bp zzoqp1"]))
            m = re.search(r"(?m)^ITEMS\[(.*)\]\s*$", text)
            return text, (set(m.group(1).split(",")) - {""} if m else None)

        text, items = listed(0, "SELECTINDEX zzoqix colour")
        row("119: SELECTINDEX file index gives the values held in the index", items == {"red", "blue", "green"}, "%r %s" % (items, text[-300:]))
        row("119: ...and says how many", has(text, r"3 record\(s\) selected to select list 0"), text[-300:])
        text, items = listed(0, "SELECTINDEX zzoqix colour red")
        row("119: with a value it gives the ids of the records that have it", items == {"a", "c"}, "%r %s" % (items, text[-300:]))
        row("119: ...and says how many", has(text, r"2 record\(s\) selected to select list 0"), text[-300:])
        text, items = listed(0, "SELECTINDEX zzoqix colour purple")
        row("119: a value no record has gives no list (READLIST finds none) and the count says 0",
            items == {"NONE"} and has(text, r"0 record\(s\) selected to select list 0"), "%r %s" % (items, text[-300:]))
        text, items = listed(0, "SELECTINDEX ZZOQIX COLOUR red")
        row("119: the file and index names are found in whichever case", items == {"a", "c"}, "%r %s" % (items, text[-300:]))
        text, items = listed(1, "SELECTINDEX zzoqix colour blue TO 1")
        row("119: TO n builds that list instead", items == {"b"} and has(text, r"1 record\(s\) selected to select list 1"), "%r %s" % (items, text[-300:]))
        text = sess(box, "SELECTINDEX zzoqix nosuchindex")
        row("119: an index that does not exist is reported", has(text, r"Unrecognised index name \(nosuchindex\)"), text[-300:])
        text = sess(box, "SELECTINDEX zzoqnone colour")
        row("119: a file that does not exist is reported", has(text, r"File not found"), text[-300:])
        text = sess(box, "SELECTINDEX zzoqix")
        row("119: no index name is reported", has(text, r"Index name required"), text[-300:])
        text = sess(box, "SELECTINDEX")
        row("119: no file name is reported", has(text, r"File name required"), text[-300:])
        text = sess(box, "SELECTINDEX zzoqix colour red TO")
        row("119: TO with no number is reported", has(text, r"Select list number missing or invalid"), text[-300:])
        text = sess(box, "SELECTINDEX zzoqix colour red blue")
        row("119: a further word is reported", has(text, r"Unexpected token \(blue\)"), text[-300:])
        text = sess(box, "SELECT.DIR /tmp TO", "GET.LIST zzoqnone TO")
        row("119 (found on the way): SELECT.DIR and GET.LIST said 'Error writing saved list record' for a missing list number; they say what 3271 says",
            text.count("Select list number missing or invalid") == 2 and not has(text, r"writing saved list record"), text[-300:])
    finally:
        sess(box, "DELETE.FILE zzoqfd", "DELETE.FILE zzoqc1", "DELETE.FILE zzoqc2", "DELETE.FILE zzoqld", "DELETE.FILE zzoqix",
             "DELETE.LIST zzoqla", "DELETE.LIST zzoqlb", "DELETE.LIST zzoqlc", "DELETE.LIST zzoqld2")
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
