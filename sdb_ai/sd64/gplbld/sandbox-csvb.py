#!/usr/bin/env python3
#
# sandbox-csvb.py - CSV in BASIC: the DELIMITER, QUOTE and ESCAPE clauses of READCSV, WRITECSV, MATREADCSV and MATWRITECSV, CSV.MODE's quote
#                   and escape characters, a quoted field that holds a line break, and CSVPARSE() / CSVBUILD() / CSVOPEN() / CSVDQ() with
#                   a dialect (the owner's CSV / JSON / XML task of 17 and 20 Oct 2026).  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-csvb.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (needs a `make`d bin/sd).  With --build it is built first from THIS tree (it must be
# empty or absent).  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 20 Oct 26 dm  New.  op_csv.c (FORMCSV in C, CSVDQ with a quote and an escape character, CSVPARSE, CSVBUILD, CSVOPEN), op_sys.c (SYSTEM 1090
#               and 1091), bcomp (the clauses, the statements' join-then-format form, !readcsvrow), matwritecsv.
# END-HISTORY
#
# THE INSTRUMENT.  What a program WRITES is read back from the disk byte for byte; what it READS is printed by the program in a tag,
# name[value], with a line feed shown as ~ and a value mark as ^, and anchored to the start of a line.  The rows that must pass on the
# tree before the change (the controls) are in programs of their own, because a program that uses a new clause does not compile there.

import os
import re
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
    say("sandbox-csvb: CANNOT RUN - " + msg)
    sys.exit(2)


def sess(box, *cmds):
    say("    > " + " | ".join(c if len(c) < 90 else c[:87] + "..." for c in cmds))
    p = subprocess.run([sys.executable, TOOL, box, "sess", os.path.join(box, "sys")] + list(cmds),
                       capture_output=True, text=True, errors="replace", timeout=900)
    out = ANSI.sub("", p.stdout + p.stderr).split(":TERM 200,9999", 1)[-1]
    return [ln.rstrip("\r") for ln in out.splitlines() if ln.strip() and not ln.startswith(":")]


def tag(lines, name):
    for ln in lines:
        m = re.match(r"^%s\[(.*)\]\s*$" % re.escape(name), ln)
        if m:
            return m.group(1)
    return None


def has(lines, pattern):
    return any(re.search(pattern, ln) for ln in lines)


def diskfile(sysd, name):
    p = os.path.join(sysd, name)
    return open(p, "rb").read().decode("latin-1") if os.path.exists(p) else None


# ---- the programs ---------------------------------------------------------------------------------------------------------------
# Every value comes out through TAG(): a line feed shown as ~, a value mark as ^.
PRE = ("   lf = char(10) ; cr = char(13)\n"
       "   tilde = '~' ; caret = '^' ; dollar = '$' ; grave = '`'\n"
       "   sq = char(39) ; bs = char(92)\n")


def T(name, expr):
    # a line feed is ~, a carriage return $, a value mark ^ and a field mark `
    return "   crt '%s[':convert(@fm, grave, convert(cr, dollar, convert(@vm, caret, convert(lf, tilde, %s)))):']'\n" % (name, expr)


PROGS = {}

# CONTROLS: statements and functions that existed before; they compile and run on the tree before the change
PROGS["zzcbc"] = PRE + (
    "   openseq 'zzcbc.txt' to f then null else create f else stop 'nocreate'\n"
    "   weofseq f\n"
    "   writecsv 'a', 'b,c', 'say \"hi\"', '' to f else stop 'c1'\n"
    "   csv.mode 2, ';'\n"
    "   writecsv 'x', 7, 'a;b', '', '1,5' to f else stop 'c2'\n"
    "   csv.mode 2\n"
    "   writecsv 'x', 7, 'a;b', '', '1,5' to f else stop 'c3'\n"
    "   csv.mode 1\n"
    "   weofseq f ; close f\n"
    "   openseq 'zzcbc.txt' to f else stop 'noopen'\n"
    "   readcsv from f to a1, a2, a3, a4 else stop 'r1'\n" +
    T("C1", "a1 : '|' : a2 : '|' : a3 : '|' : a4") +
    "   readseq skip from f else stop 'r2'\n"
    "   readcsv from f to b1, b2, b3, b4, b5 else stop 'r3'\n" +
    T("C2", "b1 : '|' : b2 : '|' : b3 : '|' : b4 : '|' : b5") +
    "   close f\n"
    "   crt 'CP:'\n"
    "   printcsv 'a', 'b,c', 'x\"y'\n"
    "   x = csvdq('p,\"q,r\",s')\n" +
    T("CQ", "x") +
    "   crt 'CEND'\n"
    "end\n")

PROGS["zzcbw"] = PRE + (
    "   openseq 'zzcbw.txt' to f then null else create f else stop 'nocreate'\n"
    "   weofseq f\n"
    "   writecsv 'a', 'b,c', 'say \"hi\"', '' to f else stop 'w1'\n"
    "   writecsv 'x;y', 'z' to f delimiter ';' else stop 'w2'\n"
    "   writecsv \"it's\", 'q\"r', \"t'u\" to f quote \"'\" escape '\\' else stop 'w3'\n"
    "   writecsv 'a\\b', 'c' to f quote \"'\" escape '\\' else stop 'w4'\n"
    "   writecsv 'p,q', 'r' to f delimiter '|' else stop 'w5'\n"
    "   writecsv 'multi' : lf : 'line', 'k' to f else stop 'w6'\n"
    "   csv.mode 3\n"
    "   writecsv 'a', '', 'b' to f else stop 'w7'\n"
    "   writecsv '' to f else stop 'w8'\n"
    "   csv.mode 2\n"
    "   writecsv 'x', 7, '1,5', '', \"it's\" to f else stop 'w9'\n"
    "   csv.mode 1, ';', \"'\", '\\'\n" +
    T("SYS", "system(1043) : system(1046) : system(1090) : system(1091)") +
    "   writecsv \"it's;\", 'v' to f else stop 'w10'\n"
    "   writecsv 'p\"q', 'r' to f quote '\"' else stop 'w11'\n"
    "   csv.mode 1\n" +
    T("SYS2", "system(1043) : system(1046) : system(1090) : system(1091)") +
    "   dim m(3)\n"
    "   m(1) = 'a,b' ; m(2) = 'c' ; m(3) = \"d'e\"\n"
    "   matwritecsv m to f delimiter '|' quote \"'\" else stop 'w12'\n"
    "   weofseq f ; close f\n"
    "   crt 'WEND'\n"
    "end\n")

PROGS["zzcbr"] = PRE + (
    "   openseq 'zzcbr.txt' to f else stop 'noopen'\n"
    "   readcsv from f to a1, a2, a3, a4, a5 else stop 'r1'\n" +
    T("R1", "a1 : '|' : a2 : '|' : a3 : '|' : a4 : '|' : a5") +
    "   readcsv from f delimiter ';' to b1, b2, b3 else stop 'r2'\n" +
    T("R2", "b1 : '|' : b2 : '|' : b3") +
    "   readcsv from f quote \"'\" escape '\\' to c1, c2, c3 else stop 'r3'\n" +
    T("R3", "c1 : '|' : c2 : '|' : c3") +
    "   readcsv from f to d1, d2 else stop 'r4'\n" +
    T("R4", "d1 : '|' : d2") +
    "   readcsv from f to e1, e2 else stop 'r5'\n" +
    T("R5", "e1 : '|' : e2") +
    "   readcsv from f to g1, g2 else stop 'r6'\n" +
    T("R6", "g1 : '|' : g2") +
    "   readcsv from f to h1 else crt 'EOF1'\n"
    "   close f\n"
    "   openseq 'zzcbr2.txt' to f else stop 'noopen2'\n"
    "   readcsv from f to a1, a2 else stop 'q1'\n" +
    T("Q1", "a1 : '|' : a2") +
    "   readcsv from f to a1, a2 else stop 'q2'\n" +
    T("Q2", "a1 : '|' : a2") +
    "   readcsv from f to a1, a2 else crt 'EOF2'\n"
    "   close f\n"
    "   openseq 'zzcbr3.txt' to f else stop 'noopen3'\n"
    "   dim m(3)\n"
    "   matreadcsv m from f delimiter ';' else stop 'm1'\n" +
    T("M1", "m(1) : '|' : m(2) : '|' : m(3)") +
    "   matreadcsv m from f quote \"'\" else stop 'm2'\n" +
    T("M2", "m(1) : '|' : m(2) : '|' : m(3)") +
    "   close f\n"
    "   crt 'REND'\n"
    "end\n")

PROGS["zzcbf"] = PRE + (
    "$include keys.h\n"
    "   c = csvparse('')\n" +
    T("E0", "jbuild(c) : ' ' : status()") +
    "   c = csvparse('a,b,' : lf : ',,' : lf : lf : 'x')\n" +
    T("P1", "jbuild(c)") +
    "   c = csvparse('a,b' : cr : lf : 'c,d' : cr : 'e,f')\n" +
    T("P2", "jbuild(c)") +
    "   c = csvparse('a,b' : lf : lf : 'c', csv$keepblank)\n" +
    T("P3", "jbuild(c)") +
    "   c = csvparse('007,1.5,-3,1e3,12345678901,,abc,0,-0,1.,.5,+4', csv$number)\n" +
    T("P4", "jbuild(c)") +
    "   c = csvparse('007,1.5')\n" +
    T("P4A", "jbuild(c)") +
    "   c = csvparse('a,\"b\"x,\"c\"')\n" +
    T("P5", "jbuild(c)") +
    "   c = csvparse('a\"b,c')\n" +
    T("P6", "jbuild(c)") +
    "   c = csvparse('\"a\\\"b\",c', 0, ',\"\\')\n" +
    T("P7", "jbuild(c)") +
    "   c = csvparse('h1,,h1' : lf : '1,2,3,4' : lf : '5', csv$header)\n" +
    T("P8", "jbuild(c)") +
    "   c = csvparse('x', csv$header)\n" +
    T("P9", "jbuild(c)") +
    "   t = 'name,qty,note' : lf : 'Ann,3,\"x, y\"' : lf : '\"Bob \"\"B\"\"\",5,\"line1' : lf : 'line2\"' : lf : 'Cy,,' : lf\n"
    "   h = csvparse(t, csv$header)\n" +
    T("H1", "h{'columns',1} : ',' : h{'columns',2} : ',' : h{'columns',3} : ' ' : inmat(h{'rows'})") +
    T("H2", "h{'rows',2,'name'} : '|' : h{'rows',2,'note'} : '|' : h{'rows',1,'note'} : '|' : h{'rows',3,'qty'}") +
    "   n = csvparse(t, csv$header + csv$number)\n" +
    T("H3", "jtype(n{'rows',1,'qty'}) : ' ' : jtype(n{'rows',1,'name'}) : ' ' : n{'rows',2,'qty'} + 1") +
    "   d = csvparse(t, csv$dynamic)\n" +
    T("D1", "dcount(d, @fm) : ' ' : dcount(d<1>, @vm) : ' ' : d<2,3>") +
    "   crt 'ROUND:'\n"
    "   crt csvbuild(h)\n" +
    T("B1", "csvbuild(jparse('[[1,\"a,b\",true,null,2.5],[\"x\"]]'))") +
    T("B2", "csvbuild(jparse('[{\"b\":2,\"a\":\"x\"},{\"a\":\"y\",\"c\":3}]'))") +
    T("B3", "csvbuild(jparse('[[\"a\",\"b\"]]'), csv$quote2 + csv$crlf)") +
    T("B4", "csvbuild(jparse('[[\"a\",1]]'), csv$quote3)") +
    T("B5", "csvbuild('a' : @vm : 'b' : @fm : 'c', csv$dynamic)") +
    T("B6", "csvbuild('x') : '] ' : status() : '[' ") +
    T("B7", "csvbuild(jparse('[[{\"a\":1}]]')) : '] ' : status() : '['") +
    T("B8", "csvbuild(jparse('{\"columns\":[\"z\",\"a\"],\"rows\":[{\"a\":1,\"z\":2}]}'))") +
    T("B9", "csvbuild(jparse('{\"columns\":[\"z\",\"a\"],\"rows\":[{\"a\":1,\"z\":2}]}'), csv$noheader)") +
    T("B10", "csvbuild(jparse('[[\"a;b\",\"c\"]]'), 0, ';')") +
    T("B11", "csvbuild(jparse('[[\"it' : sq : 's\",\"x\"]]'), 0, ',' : sq : bs)") +
    T("B12", "csvbuild(jparse('[[\"a\",\"b\"]]'), csv$header)") +
    T("B13", "csvbuild(jparse('[]'))") +
    T("O1", "csvopen('a,\"b') : csvopen('a,\"b\"') : csvopen('5\" x,\"y') : csvopen('') : csvopen('a;\"b', ';') : csvopen(\"a,'b\", ',', \"'\")") +
    "   x = csvparse('a,\"b')\n" +
    T("BAD", "x : '] ' : status() : ' at ' : inmat() : '['") +
    T("DQ", "csvdq(\"a;'b;c';d\", ';', \"'\")") +
    T("DQ2", "csvdq('a,\"b\\\"c\",d', ',', '\"', '\\')") +
    T("DQ3", "csvdq('p,\"q,r\",s')") +
    "   csv.mode 2, ';'\n" +
    T("M1", "csvbuild(jparse('[[\"a\",\"b;c\",3]]'))") +
    "   c = csvparse('p;q,r')\n" +
    T("M2", "jbuild(c)") +
    "   csv.mode 1\n"
    "   crt 'FEND'\n"
    "end\n")

PROGS["zzcbp"] = PRE + (
    "$include keys.h\n"
    "   t = ''\n"
    "   for i = 1 to 20000\n"
    "      t := 'row' : i : ',\"v,' : i : '\",' : i * 2 : lf\n"
    "   next i\n"
    "   t1 = time()\n"
    "   c = csvparse(t, csv$number)\n"
    "   t2 = time()\n"
    "   x = csvbuild(c)\n"
    "   t3 = time()\n" +
    T("PN", "inmat(c) : ' ' : c{20000, 3} : ' ' : (x = t)") +
    T("PT", "if (t3 - t1) < 20 then 'fast' else 'slow ' : (t3 - t1)") +
    "   crt 'PEND'\n"
    "end\n")

PROGS["zzcbs"] = PRE + (
    "   csv.mode 2, ';', \"'\", '\\'\n"
    "   call zzcbs1\n" +
    T("S1", "system(1043) : system(1046) : system(1090) : system(1091)") +
    "   execute 'RUN bp zzcbx'\n" +
    T("S2", "system(1043) : system(1046) : system(1090) : system(1091)") +
    "   csv.mode 1, ';'\n" +
    T("S3", "system(1043) : system(1046) : system(1090) : system(1091)") +
    "   crt 'SEND'\n"
    "end\n")
PROGS["zzcbs1"] = "   subroutine zzcbs1\n" + PRE + (
    T("  I1", "system(1043) : system(1046) : system(1090) : system(1091)") +
    "   csv.mode 3, '#', '|', ''\n" +
    T("  I2", "system(1043) : system(1046) : system(1090) : system(1091)") +
    "   return\n"
    "end\n")
PROGS["zzcbx"] = PRE + (
    T("  X0", "system(1043) : system(1046) : system(1090) : system(1091)") +
    "end\n")

READER = ("a,\"b,c\",\"say \"\"hi\"\"\",d\n"
          "x;y;z\n"
          "'it\\'s',q\"r,'t\\'u'\n"
          "\"multi\n"
          "line\",k\n"
          "5\" pipe,next\n"
          "\"unterminated")
READER2 = "a,b\r\nc,\"d\r\ne\"\r\n"
READER3 = "p;q;r\n'a,b',c,d\n"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-csvb.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-csvb: sandbox %s" % box)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-csvb: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    made = []
    try:
        for nm, text in PROGS.items():
            with open(os.path.join(sysd, "bp", nm), "w") as f:
                f.write(text)
            made.append(nm)
        for nm, text in (("zzcbr.txt", READER), ("zzcbr2.txt", READER2), ("zzcbr3.txt", READER3)):
            with open(os.path.join(sysd, nm), "wb") as f:
                f.write(text.encode("latin-1"))
        controls = ["zzcbc"]
        news = ["zzcbw", "zzcbr", "zzcbf", "zzcbp", "zzcbs", "zzcbs1", "zzcbx"]
        out = sess(box, "BASIC bp " + " ".join(controls))
        row("setup: the control program compiles on any tree", has(out, r"^Compiled 1 program\(s\) with no errors"), "\n".join(out[-6:]))
        out = sess(box, "BASIC bp " + " ".join(news), "CATALOG bp zzcbs1 LOCAL")
        row("setup: the programs that use the new clauses and functions compile with no errors",
            has(out, r"^Compiled %d program\(s\) with no errors" % len(news)), "\n".join(out[-10:]))

        say("\n--- controls: what CSV in BASIC did before ---------------------------------------------------------------------")
        out = sess(box, "RUN bp zzcbc")
        row("the control program ran to its end", has(out, r"^CEND$"), "\n".join(out[-5:]))
        d = diskfile(sysd, "zzcbc.txt")
        row("CONTROL: writecsv quotes only what needs it and doubles the quotes: a,\"b,c\",\"say \"\"hi\"\"\",",
            d is not None and d.split("\n")[0] == 'a,"b,c","say ""hi""",', repr(d))
        row("CONTROL: CSV.MODE 2 with ;: \"x\";7;\"a;b\";;\"1,5\"", d is not None and d.split("\n")[1] == '"x";7;"a;b";;"1,5"', repr(d))
        row("CONTROL: CSV.MODE 2 with a comma: \"x\",7,\"a;b\",,\"1,5\"", d is not None and d.split("\n")[2] == '"x",7,"a;b",,"1,5"', repr(d))
        row("CONTROL: readcsv gives the fields back", tag(out, "C1") == 'a|b,c|say "hi"|' and tag(out, "C2") == 'x|7|a;b||1,5',
            "%r %r" % (tag(out, "C1"), tag(out, "C2")))
        row("CONTROL: printcsv shows a,\"b,c\",\"x\"\"y\"", 'a,"b,c","x""y"' in out, "\n".join(out))
        row("CONTROL: csvdq takes p,\"q,r\",s apart (three items, field marks)", tag(out, "CQ") == "p`q,r`s", repr(tag(out, "CQ")))

        say("\n--- WRITECSV and MATWRITECSV with a delimiter, a quote and an escape character -----------------------------------")
        out = sess(box, "RUN bp zzcbw")
        row("the writer ran to its end", has(out, r"^WEND$"), "\n".join(out[-6:]))
        d = diskfile(sysd, "zzcbw.txt")
        lines = d.split("\n") if d is not None else []
        want = ['a,"b,c","say ""hi""",',                 # 1  control
                '"x;y";z',                               # 2  DELIMITER ';'
                "'it\\'s',q\"r,'t\\'u'",                 # 3  QUOTE ' ESCAPE \
                "'a\\\\b',c",                            # 4  a field holding the escape character is enclosed and the character doubled
                'p,q|r',                                 # 5  a comma is not special when the delimiter is |
                '"multi',                                # 6  a line break in a field encloses it
                'line",k',                               # 7
                '"a","","b"',                            # 8  mode 3: an empty item too
                '""',                                    # 9  ... a lone empty item too
                '"x",7,"1,5",,"it\'s"',                  # 10 mode 2
                "'it\\'s;';v",                           # 11 CSV.MODE 1, ';', quote ', escape \
                '"p\\"q";r',                             # 12 QUOTE '"' on the statement, the escape character of the mode still on
                "a,b|c|'d''e'",                          # 13 MATWRITECSV m DELIMITER '|' QUOTE "'"
                ""]
        for i, w in enumerate(want):
            row("line %d of the file is %r" % (i + 1, w), i < len(lines) and lines[i] == w,
                "have %r" % (lines[i] if i < len(lines) else None))
        row("the file has no more lines than that", len(lines) == len(want), repr(d))
        row("SYSTEM(1043), (1046), (1090) and (1091) read the setting back: mode 1, ;, ' and \\",
            tag(out, "SYS") == "1;'\\", repr(tag(out, "SYS")))
        row("CSV.MODE 1 with nothing more is mode 1, a comma, the double quote and no escape character",
            tag(out, "SYS2") == '1,"', repr(tag(out, "SYS2")))

        say("\n--- READCSV and MATREADCSV: the clauses, and a field that holds a line break ----------------------------------------")
        out = sess(box, "RUN bp zzcbr")
        row("the reader ran to its end", has(out, r"^REND$"), "\n".join(out[-6:]))
        row("READCSV: quotes, doubled quotes and the comma inside a field", tag(out, "R1") == 'a|b,c|say "hi"|d|', repr(tag(out, "R1")))
        row("READCSV ... DELIMITER ';'", tag(out, "R2") == "x|y|z", repr(tag(out, "R2")))
        row("READCSV ... QUOTE \"'\" ESCAPE '\\': it's, a lone double quote, t'u", tag(out, "R3") == "it's|q\"r|t'u", repr(tag(out, "R3")))
        row("a field that holds a line break: the two lines are one row, the break kept as a line feed", tag(out, "R4") == "multi~line|k", repr(tag(out, "R4")))
        row("a quote in the MIDDLE of an unquoted field does not join the next line on (the old rule: the quote is dropped)",
            tag(out, "R5") == "5 pipe|next", repr(tag(out, "R5")))
        row("a quote still open at the end of the file gives the row as far as it went", tag(out, "R6") == "unterminated|", repr(tag(out, "R6")))
        row("... and the next READCSV takes the ELSE branch", has(out, r"^EOF1$"), "\n".join(out))
        row("a CRLF file: the rows, and a quoted CRLF read as a line feed", tag(out, "Q1") == "a|b" and tag(out, "Q2") == "c|d~e" and has(out, r"^EOF2$"),
            "%r %r" % (tag(out, "Q1"), tag(out, "Q2")))
        row("MATREADCSV ... DELIMITER ';'", tag(out, "M1") == "p|q|r", repr(tag(out, "M1")))
        row("MATREADCSV ... QUOTE \"'\" takes the comma inside the quotes", tag(out, "M2") == "a,b|c|d", repr(tag(out, "M2")))

        say("\n--- CSVPARSE() ---------------------------------------------------------------------------------------------------")
        out = sess(box, "RUN bp zzcbf")
        row("the function program ran to its end", has(out, r"^FEND$"), "\n".join(out[-6:]))
        row("CSVPARSE('') is an empty array, status 0", tag(out, "E0") == "[] 0", repr(tag(out, "E0")))
        row("rows of arrays; a trailing delimiter is an empty last field; a blank line is skipped",
            tag(out, "P1") == '[["a","b",""],["","",""],["x"]]', repr(tag(out, "P1")))
        row("CRLF, LF and a lone CR each end a line", tag(out, "P2") == '[["a","b"],["c","d"],["e","f"]]', repr(tag(out, "P2")))
        row("csv$keepblank: a blank line is a row of one empty field", tag(out, "P3") == '[["a","b"],[""],["c"]]', repr(tag(out, "P3")))
        row("csv$number: a number is a number, 007 / 1. / .5 / +4 / an empty field / text stay strings",
            tag(out, "P4") == '[["007",1.5,-3,1000,12345678901,"","abc",0,0,"1.",".5","+4"]]', repr(tag(out, "P4")))
        row("without csv$number every field is a string", tag(out, "P4A") == '[["007","1.5"]]', repr(tag(out, "P4A")))
        row("text after a closing quote is kept: \"b\"x is bx", tag(out, "P5") == '[["a","bx","c"]]', repr(tag(out, "P5")))
        row("a quote inside an unquoted field is data (RFC 4180 rules; CSVDQ() drops it)", tag(out, "P6") == '[["a\\"b","c"]]', repr(tag(out, "P6")))
        row("a dialect with an escape character: \\\" inside a quoted field", tag(out, "P7") == '[["a\\"b","c"]]', repr(tag(out, "P7")))
        row("csv$header: columns in the order of the file, a column used twice keeps the later value, a column with no name is _n, "
            "an extra field is _n, a short row has empty cells",
            tag(out, "P8") == '{"columns":["h1","_2","h1"],"rows":[{"_2":"2","_4":"4","h1":"3"},{"_2":"","h1":"5"}]}', repr(tag(out, "P8")))
        row("csv$header with a header and no rows", tag(out, "P9") == '{"columns":["x"],"rows":[]}', repr(tag(out, "P9")))
        row("by column name: the columns, the count of rows, a quoted comma and quoted line break, an empty cell",
            tag(out, "H1") == "name,qty,note 3" and tag(out, "H2") == 'Bob "B"|line1~line2|x, y|', "%r %r" % (tag(out, "H1"), tag(out, "H2")))
        row("csv$header + csv$number: 3 is a number, Ann a string", tag(out, "H3") == "number string 6", repr(tag(out, "H3")))
        row("csv$dynamic: rows by field mark, fields by value mark", tag(out, "D1") == "4 3 x, y", repr(tag(out, "D1")))
        row("an unclosed quote: a null string, STATUS() 1020 and INMAT() the place of the quote that opened it (the third character)",
            tag(out, "BAD") == "] 1020 at 3[", repr(tag(out, "BAD")))

        say("\n--- CSVBUILD(), CSVOPEN(), CSVDQ() -----------------------------------------------------------------------------")
        row("an array of arrays: numbers, true, null, a quoted comma, a short row", tag(out, "B1") == '1,"a,b",true,,2.5~x~', repr(tag(out, "B1")))
        row("an array of objects: the header is the names in order of name, a missing value is empty", tag(out, "B2") == "a,b,c~x,2,~y,,3~", repr(tag(out, "B2")))
        row("csv$quote2 + csv$crlf: every text field enclosed and the line ends with a carriage return and a line feed", tag(out, "B3") == '"a","b"$~', repr(tag(out, "B3")))
        row("csv$quote3 encloses numbers too", tag(out, "B4") == '"a","1"~', repr(tag(out, "B4")))
        row("a dynamic array (csv$dynamic)", tag(out, "B5") == "a,b~c~", repr(tag(out, "B5")))
        row("a string where a collection is needed: a null string, STATUS() 1019", tag(out, "B6") == "] 1019[", repr(tag(out, "B6")))
        row("a value that is a collection: a null string, STATUS() 1019", tag(out, "B7") == "] 1019[", repr(tag(out, "B7")))
        row("{columns, rows}: the columns in the order given, the header row", tag(out, "B8") == "z,a~2,1~", repr(tag(out, "B8")))
        row("csv$noheader leaves the header row out", tag(out, "B9") == "2,1~", repr(tag(out, "B9")))
        row("a dialect with a semicolon: a field holding one is enclosed", tag(out, "B10") == '"a;b";c~', repr(tag(out, "B10")))
        row("a dialect with a quote and an escape character", tag(out, "B11") == "'it\\'s',x~", repr(tag(out, "B11")))
        row("csv$header on rows of arrays has no names to write: no header row", tag(out, "B12") == "a,b~", repr(tag(out, "B12")))
        row("an empty array gives no text", tag(out, "B13") == "", repr(tag(out, "B13")))
        row("csvopen(): 1 for an open quote at the end, 0 for a closed one, a quote in the middle of a field is no quote",
            tag(out, "O1") == "101011", repr(tag(out, "O1")))
        row("csvdq with a quote: the semicolon inside the quotes stays", tag(out, "DQ") == "a`b;c`d", repr(tag(out, "DQ")))
        row("csvdq with a quote and an escape character: \\\" inside the quotes is a quote", tag(out, "DQ2") == 'a`b"c`d', repr(tag(out, "DQ2")))
        row("CSVBUILD follows CSV.MODE (mode 2, a semicolon)", tag(out, "M1") == '"a";"b;c";3~', repr(tag(out, "M1")))
        row("CSVPARSE does not (a comma, whatever CSV.MODE says)", tag(out, "M2") == '[["p;q","r"]]', repr(tag(out, "M2")))
        out = sess(box, "RUN bp zzcbp")
        row("20000 rows: parsed, built and the text is the same, in under 20 seconds",
            tag(out, "PN") == "20000 40000 1" and tag(out, "PT") == "fast", "%r %r" % (tag(out, "PN"), tag(out, "PT")))

        say("\n--- the setting goes with the program ----------------------------------------------------------------------------")
        out = sess(box, "RUN bp zzcbs")
        row("the run reached its end", has(out, r"^SEND$"), "\n".join(out[-6:]))
        row("a called program starts with the caller's quote and escape character", tag(out, "  I1") == "2;'\\", repr(tag(out, "  I1")))
        row("... changes its own, and back in the caller they are as they were", tag(out, "  I2") == "3#|" and tag(out, "S1") == "2;'\\",
            "%r %r" % (tag(out, "  I2"), tag(out, "S1")))
        row("EXECUTE starts at the defaults", tag(out, "  X0") == '1,"', repr(tag(out, "  X0")))
        row("... and the caller's come back after it", tag(out, "S2") == "2;'\\", repr(tag(out, "S2")))
        row("CSV.MODE 1, ';' gives the quote and escape character back their defaults too", tag(out, "S3") == '1;"', repr(tag(out, "S3")))
    finally:
        sess(box, "DELETE.CATALOG zzcbs1 LOCAL")
        for nm in ("zzcbc.txt", "zzcbw.txt", "zzcbr.txt", "zzcbr2.txt", "zzcbr3.txt"):
            if os.path.exists(os.path.join(sysd, nm)):
                os.remove(os.path.join(sysd, nm))
        for nm in made:
            for d in ("bp", "bp.out"):
                pth = os.path.join(sysd, d, nm)
                if os.path.exists(pth):
                    os.remove(pth)
        subprocess.run([sys.executable, TOOL, box, "stop"], capture_output=True, text=True, errors="replace", timeout=120)

    say("\nsandbox-csvb: %d passed, %d failed" % (passed, failed))
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
