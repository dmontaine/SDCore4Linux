#!/usr/bin/env python3
#
# sandbox-csvq.py - CSV and DELIMITER reports in the query processor: AS file id, and a multivalued item split over lines
#                   (openQM 4 manual, CSV and DELIMITER; the owner's CSV query-processor task of 17 and 20 Oct 2026).  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-csvq.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or absent);
# without it <dir> must already be built.  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 20 Oct 26 dm  New.  qproc: AS file id on CSV and DELIMITER (APPENDING, NO.QUERY, either order, never both), written as a record of
#               a directory file through edit_guard and the record lock OPENSEQ takes; show.delimited splits a multivalued item
#               over lines, one value per line, the other columns blank (RPT / REPEATING repeat them); messages 11850-11852.
# END-HISTORY
#
# THE INSTRUMENT.  A report that goes to TO or AS is read back FROM THE DISK (the sandbox's directory file is an ordinary directory),
# byte for byte; a report to the screen is read from the session.  The expected lines are written out in full.  The fixture is three
# records, one of which holds quote and comma characters, one with no multivalued data, one whose second multivalued item is longer
# than the first.  The CONTROLS are the same reports on single valued data, a report of totals and breaks (which must stay one
# line each), and the TO form that worked before.  A refusal row checks that NOTHING was created or changed.

import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
RUN = "%05d" % (os.getpid() % 100000)
FIL = "zzcq" + RUN           # the data file, three records
DIR = "zzcd" + RUN           # a directory file for AS
VM = "\xfd"
passed = failed = 0
lives = []


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
    for lv in lives:
        lv.kill()
    say("sandbox-csvq: CANNOT RUN - " + msg)
    sys.exit(2)


def sess(box, *cmds, quiet=False):
    if not quiet:
        say("    > " + " | ".join(c if len(c) < 90 else c[:87] + "..." for c in cmds))
    p = subprocess.run([sys.executable, TOOL, box, "sess", os.path.join(box, "user_accounts")] + list(cmds),
                       capture_output=True, text=True, errors="replace", timeout=600)
    out = ANSI.sub("", p.stdout + p.stderr)
    return out.split(":TERM 200,9999", 1)[-1]


def write(path, text):
    with open(path, "wb") as f:
        f.write(text.encode("latin-1"))   # a value mark is the byte 253


class Live:
    """A session on a pipe kept open, so what it holds stays held until kill()."""

    def __init__(self, box, tag, cmds):
        self.out = os.path.join(box, "live-%s.out" % tag)
        env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"))
        self.fh = open(self.out, "w")
        self.p = subprocess.Popen([os.path.join(box, "sys", "bin", "sd")], stdin=subprocess.PIPE, stdout=self.fh,
                                  stderr=subprocess.STDOUT, cwd=os.path.join(box, "user_accounts"), env=env, text=True)
        self.p.stdin.write("\nTERM 200,9999\n" + "".join(c + "\n" for c in cmds))
        self.p.stdin.flush()
        say("    > live %s: %s" % (tag, " | ".join(cmds)))
        lives.append(self)

    def text(self):
        self.fh.flush()
        return ANSI.sub("", open(self.out, errors="replace").read())

    def kill(self):
        if self.p.poll() is None:
            try:
                self.p.stdin.write("\n")
                self.p.stdin.write("OFF\n")
                self.p.stdin.flush()
                self.p.wait(timeout=10)
            except Exception:
                self.p.kill()
                self.p.wait()
        try:
            self.fh.close()
        except OSError:
            pass


def reply(out, cmd):
    """What the session printed for the command cmd: from the line after its echo to the next prompt line."""
    part = out.split(":" + cmd, 1)[-1]
    lines = []
    seen = False
    for ln in part.splitlines():
        if not seen:
            seen = True
            if ln.strip() == "":
                continue
        if ln.startswith(":"):
            break
        lines.append(ln.rstrip("\r"))     # not a tab: a delimited line may end in one
    return [x for x in lines if x != ""] if not lines or lines[0] != "" else lines


def data(lines):
    """The lines of a report on the screen without the closing 'n record(s) listed' line."""
    return [x for x in lines if not re.match(r"^\d+ record\(s\) listed$", x)]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-csvq.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    bp = os.path.join(sysd, "bp")
    say("sandbox-csvq: sandbox %s" % box)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-csvq: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    # record: fields 1 name, 2 qty (m), 3 price (m), 4 note (m), 5 tags (s, holds value marks), 6 city
    recs = [("r1", ["Ann", "1" + VM + "2" + VM + "3", "1.50" + VM + "2.00" + VM + "3.00", "x" + VM + "y", "p" + VM + "q", "Oslo"]),
            ("r2", ['Bob "B", Jr', "5", "3.25", "", "z", ""]),
            ("r3", ["Cy", "", "", "u" + VM + "v" + VM + "w" + VM + "x", "", "Rome"])]
    # (field number, heading, format, S or M, association)
    items = [(1, "name", "10L", "S", ""), (2, "qty", "5R", "M", "lines"), (3, "price", "8R", "M", "lines"),
             (4, "note", "5L", "M", ""), (5, "tags", "5L", "S", ""), (6, "city", "6L", "S", "")]
    made = []
    for rid, flds in recs:
        write(os.path.join(bp, "zzcqr" + RUN + rid), "\n".join(flds) + "\n")
        made.append("zzcqr" + RUN + rid)
    for n, nm, fmt, sm, assoc in items:
        write(os.path.join(bp, "zzcqd%s%d" % (RUN, n)), "D\n%d\n\n%s\n%s\n%s\n%s\n" % (n, nm, fmt, sm, assoc))
        made.append("zzcqd%s%d" % (RUN, n))
    cmds = ["DELETE.FILE DICT %s" % FIL, "DELETE.FILE %s" % FIL, "CREATE.FILE %s" % FIL,
            "DELETE.FILE DICT %s" % DIR, "DELETE.FILE %s" % DIR, "CREATE.FILE %s DIRECTORY" % DIR]
    for rid, _ in recs:
        cmds.append("COPY FROM BP TO %s zzcqr%s%s,%s" % (FIL, RUN, rid, rid))
    for n, nm, fmt, sm, assoc in items:
        cmds.append("COPY FROM BP TO DICT %s zzcqd%s%d,%s" % (FIL, RUN, n, nm))
    dirpath = os.path.join(sysd, DIR)

    def disk(rid):
        p = os.path.join(dirpath, rid)
        return open(p, "rb").read().decode("latin-1") if os.path.exists(p) else None

    def plant(rid, text):
        write(os.path.join(dirpath, rid), text)

    def lines_of(text):
        return None if text is None else text.split("\n")

    base = "LIST %s BY @ID " % FIL
    try:
        say("\n--- setup ---------------------------------------------------------------------")
        out = sess(box, *cmds, quiet=True)
        copied = len(re.findall(r"(?m)^1 record\(s\) copied\.", out))
        row("setup: three records and six dictionary items were copied", copied == len(recs) + len(items), "copied %d" % copied)
        row("setup: the directory file exists on the disk", os.path.isdir(dirpath), dirpath)

        # ---- the reports on the screen ------------------------------------------------------------------------------------
        say("\n--- a multivalued item is split over lines (CSV and DELIMITER) ---------------------------------------------")
        cA = base + "name qty price CSV"
        cB = base + "name qty note CSV"
        cC = base + "name tags CSV"
        cD = base + "name tags MULTI.VALUE CSV"
        cE = base + "name qty SINGLE.VALUE CSV"
        cF = base + "name RPT qty CSV"
        cG = base + "name qty REPEATING CSV"
        cH = base + "name city qty CSV"
        cI = base + "name qty CSV 3"
        cJ = base + 'name qty price DELIMITER ";"'
        cK = base + "BREAK.ON name TOTAL qty CSV"
        cL = base + "name qty CSV 2 ';'"
        cM = base + 'name qty price DELIMITER "<tab>"'
        out = sess(box, cA, cB, cC, cD, cE, cF, cG, cH, cI, cJ, cK, cL, cM)
        H = FIL

        got = data(reply(out, cA))
        exp = [H + ",name,qty,price", "r1,Ann,1,1.50", ",,2,2.00", ",,3,3.00", 'r2,"Bob ""B"", Jr",5,3.25', "r3,Cy,,"]
        row("CSV: qty and price (one association) are split over three lines, the id and the name blank on the continuation lines",
            got == exp, "\n".join(got))
        got = data(reply(out, cB))
        exp = [H + ",name,qty,note", "r1,Ann,1,x", ",,2,y", ",,3,", 'r2,"Bob ""B"", Jr",5,', "r3,Cy,,u", ",,,v", ",,,w", ",,,x"]
        row("CSV: a second multivalued item that is longer adds lines, a shorter one leaves blank cells", got == exp, "\n".join(got))
        got = data(reply(out, cC))
        exp = [H + ",name,tags", "r1,Ann,p" + "�" + "q", 'r2,"Bob ""B"", Jr",z', "r3,Cy,"]
        row("CONTROL (the manual): a single valued item whose data holds value marks stays ONE element, the marks as data",
            got == exp, "\n".join(got))
        got = data(reply(out, cD))
        exp = [H + ",name,tags", "r1,Ann,p", ",,q", 'r2,"Bob ""B"", Jr",z', "r3,Cy,"]
        row("MULTI.VALUE makes that item split", got == exp, "\n".join(got))
        got = data(reply(out, cE))
        exp = [H + ",name,qty", "r1,Ann,1" + "�" + "2" + "�" + "3", 'r2,"Bob ""B"", Jr",5', "r3,Cy,"]
        row("SINGLE.VALUE keeps the value marks of a multivalued item in one element, one line (the manual's second example)",
            got == exp, "\n".join(got))
        got = data(reply(out, cF))
        exp = [H + ",name,qty", "r1,Ann,1", ",Ann,2", ",Ann,3", 'r2,"Bob ""B"", Jr",5', "r3,Cy,"]
        row("RPT repeats that single valued item on every line, the id still blank", got == exp, "\n".join(got))
        got = data(reply(out, cG))
        exp = [H + ",name,qty", "r1,Ann,1", "r1,Ann,2", "r1,Ann,3", 'r2,"Bob ""B"", Jr",5', "r3,Cy,"]
        row("REPEATING repeats every single valued item, the id too", got == exp, "\n".join(got))
        got = data(reply(out, cH))
        exp = [H + ",name,city,qty", "r1,Ann,Oslo,1", ",,,2", ",,,3", 'r2,"Bob ""B"", Jr",,5', "r3,Cy,Rome,"]
        row("a second single valued item is blank on the continuation lines as well", got == exp, "\n".join(got))
        got = data(reply(out, cI))
        row("CSV 3 quotes the blank cells too: \"\",\"\",\"2\"", '"","","2"' in got and '"","","3"' in got and '"r1","Ann","1"' in got,
            "\n".join(got))
        got = data(reply(out, cL))
        row("CSV 2 with an other delimiter splits the same way, a blank cell stays blank",
            ['"r1";"Ann";1', ";;2", ";;3", '"r2";"Bob ""B"", Jr";5', '"r3";"Cy";'] == got[1:], "\n".join(got))
        got = data(reply(out, cJ))
        exp = [H + ";name;qty;price", "r1;Ann;1;1.50", ";;2;2.00", ";;3;3.00", 'r2;Bob "B", Jr;5;3.25', "r3;Cy;;"]
        row("DELIMITER: the same split by the same code (no quoting)", got == exp, "\n".join(got))
        got = data(reply(out, cM))
        exp = [H + "\tname\tqty\tprice", "r1\tAnn\t1\t1.50", "\t\t2\t2.00", "\t\t3\t3.00", 'r2\tBob "B", Jr\t5\t3.25', "r3\tCy\t\t"]
        row("DELIMITER \"<tab>\": a tab between the cells, the same split", got == exp, "\n".join(got))
        got = data(reply(out, cK))
        eq = [x for x in got if "=====" in x]
        sub = [x for x in got if "-----" in x]
        row("CONTROL: the grand total line is ONE line and keeps its value mark; so does each subtotal line",
            len(eq) == 1 and "�" in eq[0] and "11" in eq[0] and len(sub) == 3 and all("�" in x for x in sub),
            "\n".join(got))
        details = [x for x in got if x.startswith("r1,Ann,") or x.startswith(",,2") or x.startswith(",,3")]
        row("... and the detail lines of the same report are split", details[:3] == ["r1,Ann,1", ",,2", ",,3"], "\n".join(got))

        # ---- TO: the same lines, from the disk ----------------------------------------------------------------------------
        say("\n--- TO pathname: the same split in the file, both options in either order --------------------------------")
        for f in ("zzcq1.txt", "zzcq2.txt", "zzcq3.txt", "zzcq4.txt"):
            if os.path.exists(os.path.join(sysd, f)):
                os.remove(os.path.join(sysd, f))
        t1 = cA + " TO zzcq1.txt"
        out = sess(box, t1)
        txt = open(os.path.join(sysd, "zzcq1.txt"), "rb").read().decode("latin-1") if os.path.exists(os.path.join(sysd, "zzcq1.txt")) else None
        row("TO: the file holds the split lines (the same code as the screen)",
            lines_of(txt) == [H + ",name,qty,price", "r1,Ann,1,1.50", ",,2,2.00", ",,3,3.00", 'r2,"Bob ""B"", Jr",5,3.25', "r3,Cy,,", ""],
            repr(txt))
        for order in ("NO.QUERY APPENDING", "APPENDING NO.QUERY"):
            write(os.path.join(sysd, "zzcq2.txt"), "OLD\n")
            out = sess(box, cA + " TO zzcq2.txt " + order)
            txt = open(os.path.join(sysd, "zzcq2.txt"), "rb").read().decode("latin-1")
            rep = " ".join(reply(out, cA + " TO zzcq2.txt " + order))
            row("TO ... %s is refused with its own message before the file is touched" % order,
                txt == "OLD\n" and "cannot be used together" in rep and "not found" not in rep, "file %r reply %r" % (txt, rep))
        write(os.path.join(sysd, "zzcq3.txt"), "OLD\n")
        out = sess(box, cA + " TO zzcq3.txt APPENDING")
        txt = open(os.path.join(sysd, "zzcq3.txt"), "rb").read().decode("latin-1")
        row("CONTROL: TO ... APPENDING adds to what is there", txt.startswith("OLD\n" + H + ",name,qty,price\nr1,Ann,1"), repr(txt))
        write(os.path.join(sysd, "zzcq4.txt"), "OLD\n")
        out = sess(box, cA + " TO zzcq4.txt NO.QUERY")
        txt = open(os.path.join(sysd, "zzcq4.txt"), "rb").read().decode("latin-1")
        row("CONTROL: TO ... NO.QUERY replaces it with no question", txt.startswith(H + ",name,qty,price\nr1,Ann,1") and "OLD" not in txt,
            repr(txt))

        # ---- AS file id ---------------------------------------------------------------------------------------------------
        say("\n--- AS file id: the report as a record of a directory file --------------------------------------------------")
        exp_a = H + ",name,qty,price\nr1,Ann,1,1.50\n,,2,2.00\n,,3,3.00\nr2,\"Bob \"\"B\"\", Jr\",5,3.25\nr3,Cy,,\n"
        c1 = cA + " AS %s out1" % DIR
        out = sess(box, c1, "LIST.READU")
        rep = reply(out, c1)
        row("AS: the record lock OPENSEQ took is given back when the command ends (LIST.READU in the same session lists none)",
            "out1" not in out.split("LIST.READU", 1)[-1], out.split("LIST.READU", 1)[-1][-300:])
        row("AS: the record holds the report, the column headings and no page heading", disk("out1") == exp_a, repr(disk("out1")))
        row("AS: the session shows only the count of records, nothing of the report", data(rep) == [] and any(re.match(r"^3 record\(s\) listed", x) for x in rep), "\n".join(rep))
        c2 = base + 'name qty price DELIMITER "|" AS %s out2' % DIR
        out = sess(box, c2)
        row("DELIMITER ... AS: the same record by the same code, with the delimiter",
            disk("out2") == H + "|name|qty|price\nr1|Ann|1|1.50\n||2|2.00\n||3|3.00\nr2|Bob \"B\", Jr|5|3.25\nr3|Cy||\n", repr(disk("out2")))
        c2b = base + "name tags CSV 2 ';' AS %s out2b" % DIR
        out = sess(box, c2b)
        row("CSV mode and delimiter before AS: the quoting and the delimiter of the screen report",
            disk("out2b") == H + ";name;tags\n\"r1\";\"Ann\";\"p" + VM + "q\"\n\"r2\";\"Bob \"\"B\"\", Jr\";\"z\"\n\"r3\";\"Cy\";\n", repr(disk("out2b")))

        plant("out3", "OLD\n")
        c3 = cA + " AS %s out3" % DIR
        out = sess(box, c3, "n")
        rep = " ".join(reply(out, c3))
        row("AS on an existing record asks; the answer n leaves it as it was",
            disk("out3") == "OLD\n" and re.search(r"out3 already exists\. Overwrite\(y/<n>\)\?", rep) is not None, "%r %r" % (disk("out3"), rep))
        out = sess(box, c3, "y")
        row("... the answer y replaces it", disk("out3") == exp_a, repr(disk("out3")))
        plant("out3", "OLD\n")
        out = sess(box, c3, "")
        row("... Enter is N, as it is for TO", disk("out3") == "OLD\n", repr(disk("out3")))
        plant("out4", "OLD\n")
        c4 = cA + " AS %s out4 NO.QUERY" % DIR
        out = sess(box, c4, "WHO")
        row("AS ... NO.QUERY replaces it with no question (the next command is not eaten as an answer)",
            disk("out4") == exp_a and "already exists" not in out and re.search(r"(?m)^\d+ \w+\s*$", out.split(c4, 1)[-1]) is not None, "%r" % disk("out4"))
        plant("out5", "OLD\n")
        c5 = cA + " AS %s out5 APPENDING" % DIR
        out = sess(box, c5)
        row("AS ... APPENDING adds to the record (and does not ask)", disk("out5") == "OLD\n" + exp_a and "already exists" not in out, repr(disk("out5")))
        c5b = cA + " AS %s out5b APPENDING" % DIR
        out = sess(box, c5b)
        row("AS ... APPENDING makes the record when it is not there", disk("out5b") == exp_a, repr(disk("out5b")))
        for order in ("NO.QUERY APPENDING", "APPENDING NO.QUERY"):
            plant("out6", "OLD\n")
            c6 = cA + " AS %s out6 %s" % (DIR, order)
            out = sess(box, c6)
            rep = " ".join(reply(out, c6))
            row("AS ... %s is refused: the message, the record untouched, no listing" % order,
                disk("out6") == "OLD\n" and "cannot be used together" in rep and "record(s) listed" not in rep and "not found" not in rep,
                "%r %r" % (disk("out6"), rep))
        c6n = cA + " AS %s out6n NO.QUERY APPENDING" % DIR
        out = sess(box, c6n)
        row("... and nothing is created when the record was not there", disk("out6n") is None, repr(disk("out6n")))
        c7 = cA + " TO zzcq7.txt AS %s out7" % DIR
        c7b = cA + " AS %s out7 TO zzcq7.txt" % DIR
        out = sess(box, c7, c7b)
        row("TO and AS together are refused, in either order, and nothing is made",
            "Multiple specification of output filename" in out and disk("out7") is None and not os.path.exists(os.path.join(sysd, "zzcq7.txt")),
            "%r %r" % (disk("out7"), os.path.exists(os.path.join(sysd, "zzcq7.txt"))))
        c8 = cA + " AS %s out8" % FIL
        out = sess(box, c8)
        rep = " ".join(reply(out, c8))
        row("AS on a hashed file is refused with its own message and no record is written",
            "directory file" in rep and "record(s) listed" not in rep, rep)
        out = sess(box, "SELECT %s WITH @ID = 'out8'" % FIL)
        row("... the hashed file holds no record out8", re.search(r"(?m)^0 record\(s\) selected", out) is not None or "No records" in out or "0 record" in out, out[-200:])
        c9 = cA + " AS zznofile%s out9" % RUN
        out = sess(box, c9)
        rep = " ".join(reply(out, c9))
        row("AS on a file that is not there: Cannot open", ("Cannot open zznofile%s" % RUN) in rep and "record(s) listed" not in rep, rep)
        c10 = cA + " AS %s" % DIR
        out = sess(box, c10)
        rep = " ".join(reply(out, c10))
        row("AS with the file and no record id is refused", "record id required" in rep and "record(s) listed" not in rep, rep)
        c11 = "LIST %s AS %s out11 name" % (FIL, DIR)
        out = sess(box, c11)
        rep = " ".join(reply(out, c11))
        row("AS in a report that is neither CSV nor DELIMITER is refused (the TO wording) and makes nothing",
            "can only be specified in a delimited report" in rep and disk("out11") is None, "%r %r" % (rep, disk("out11")))
        c12 = cA + " AS %s out12 LPTR" % DIR
        out = sess(box, c12)
        rep = " ".join(reply(out, c12))
        row("AS with LPTR is refused (the TO wording) and makes nothing", "cannot be used with LPTR" in rep and disk("out12") is None,
            "%r %r" % (rep, disk("out12")))
        c13 = base + "name qty XML AS %s out13" % DIR
        out = sess(box, c13)
        row("AS on an XML report is refused and makes nothing (an XML report has no delimited lines to put there)",
            disk("out13") is None, repr(disk("out13")))
        c14 = base + 'name AS Who qty WITH Who = "Ann" CSV'
        out = sess(box, c14)
        got = data(reply(out, c14))
        row("CONTROL: a synonym `name AS Who` after an item is still a synonym (the WITH finds only Ann)",
            got[:2] == [H + ",name,qty", "r1,Ann,1"] and not any(x.startswith("r2") for x in got), "\n".join(got))
        c15 = base + 'name AS Who qty WITH Who = "Ann" CSV AS %s out15' % DIR
        out = sess(box, c15)
        row("... and both uses in one command: the synonym and the output record",
            disk("out15") == H + ",name,qty\nr1,Ann,1\n,,2\n,,3\n", repr(disk("out15")))
        c16 = base + "name qty CSV AS %s OUT16" % DIR
        out = sess(box, c16)
        row("an upper case record id is accepted (SD folds the case of ids it writes: the record is there under one spelling)",
            (disk("out16") is not None) != (disk("OUT16") is not None), "%r %r" % (disk("out16"), disk("OUT16")))

        # ---- the lock -------------------------------------------------------------------------------------------------------
        say("\n--- the record is locked while another session holds it -----------------------------------------------------")
        write(os.path.join(bp, "zzcqhold" + RUN), "   openseq '%s', 'out17' to f then null else null\n   crt 'HELD'\n   input x\n   crt 'DONE'\nend\n" % DIR)
        made.append("zzcqhold" + RUN)
        plant("out17", "OLD\n")
        out = sess(box, "BASIC bp zzcqhold" + RUN, quiet=True)
        holder = Live(box, "csvq", ["RUN bp zzcqhold" + RUN])
        for _ in range(100):
            if "HELD" in holder.text():
                break
            time.sleep(0.2)
        row("setup: the holder session has the record open and is waiting", "HELD" in holder.text(), holder.text()[-300:])
        c17 = cA + " AS %s out17 NO.QUERY" % DIR
        t0 = time.time()
        out = sess(box, c17)
        rep = " ".join(reply(out, c17))
        row("AS on a record another session holds says who, does not hang, and writes nothing",
            time.time() - t0 < 60 and re.search(r"locked by user \d+", rep) is not None and disk("out17") == "OLD\n" and "record(s) listed" not in rep,
            "%r %r %.0fs" % (rep, disk("out17"), time.time() - t0))
        holder.kill()
        out = sess(box, c17)
        row("... when the holder has gone the same command works", disk("out17") == exp_a, repr(disk("out17")))
    finally:
        for lv in lives:
            lv.kill()
        for nm in made:
            for d in ("bp", "bp.out"):
                pth = os.path.join(sysd, d, nm)
                if os.path.exists(pth):
                    os.remove(pth)
        sess(box, "DELETE.FILE DICT %s" % FIL, "DELETE.FILE %s" % FIL, "DELETE.FILE DICT %s" % DIR, "DELETE.FILE %s" % DIR, quiet=True)
        for f in ("zzcq1.txt", "zzcq2.txt", "zzcq3.txt", "zzcq4.txt", "zzcq7.txt"):
            if os.path.exists(os.path.join(sysd, f)):
                os.remove(os.path.join(sysd, f))
        subprocess.run([sys.executable, TOOL, box, "stop"], capture_output=True, text=True, errors="replace", timeout=120)

    say("\nsandbox-csvq: %d passed, %d failed" % (passed, failed))
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
