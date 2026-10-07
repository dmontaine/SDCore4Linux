#!/usr/bin/env python3
#
# sandbox-dictfold.py - does a dictionary read fold case?  RELEASE_1.1 5 stage 2a (PAL-1).
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-dictfold.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (a private SD built from a tree, no sudo, its own
# IPC keys: never the live system).  With --build the sandbox is built first from THIS tree; <dir>
# must then be empty or absent.  Without it <dir> must already be built, which is how the same
# script is run against an OLD build to prove it can fail.  The fixture files have a name unique to
# the run, so a sandbox that was used before is fine.
#
# Exit 0 every row passed, 1 a row failed, 2 it could not run (setup is not what the rows assume).
#
# WHAT IT MEASURES.  The Windows port's stage 2a (its verify-dictfold.ps1, 14 Sep 2026): a dictionary
# item stored in lower case is found when a query, CD or an I-type names it in upper case, and the
# other way round.  Every DECISIVE row is red on a build without the fold; the names are read from
# what SD printed, case-sensitively, because ext4 does not hide a miss the way NTFS did.
#
# THE INSTRUMENT.  It prints the commands it sent and what came back.  Every no-error row also
# requires the "Compiling" line, because a COPY can carry a compiled object across and a row that only
# looks for the absence of an error passes when nothing was compiled.

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
RUN = "%05d" % (os.getpid() % 100000)
F = "ZZF" + RUN          # dictionary stores f1, f3, xtype in LOWER case
G = "ZZG" + RUN          # dictionary stores F1 in UPPER case
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
    say("sandbox-dictfold: CANNOT RUN - " + msg)
    sys.exit(2)


def sess(box, *cmds, cwd=None):
    say("    > " + " | ".join(cmds) + ("   [cwd " + os.path.relpath(cwd, box) + "]" if cwd else ""))
    p = subprocess.run([sys.executable, TOOL, box, "sess", cwd or os.path.join(box, "user_accounts")] + list(cmds),
                       capture_output=True, text=True, timeout=600)
    out = ANSI.sub("", p.stdout + p.stderr)
    out = out.split(":TERM 200,9999", 1)[-1]
    for line in out.splitlines():
        if line.strip() and not line.startswith(":") and not line.startswith("exit "):
            say("      | " + line.rstrip()[:110])
    return out


def heads(text, file):
    """The column headings printed by LIST <file> <field>: 'zzf00001.......   F1...' -> 'F1...'."""
    return re.findall(r"(?m)^" + re.escape(file.lower()) + r"\.*\s+(\S+)\s*$", text)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-dictfold.py <dir> [--build]")
    box = os.path.abspath(args[0])
    say("sandbox-dictfold: sandbox  %s" % box)
    say("sandbox-dictfold: tree     %s" % os.path.dirname(HERE))
    say("sandbox-dictfold: files    %s (lower-case dictionary), %s (upper-case dictionary)" % (F, G))
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-dictfold: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(box, "sys", "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, timeout=120)
    if "--solo" in sys.argv:
        # LSOLO 43: Solo's own programs, messages and shipped dictionaries on the full sandbox's kernel (see
        # solo_swap.py), then Solo's write_install_dicts writes Solo's dictionaries; the rows are unchanged.
        import importlib.util
        spec = importlib.util.spec_from_file_location("solo_swap", os.path.join(HERE, "solo_swap.py"))
        ss = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ss)
        ok, why = ss.swap(box, programs=("acomp", "bcomp", "cd", "cname", "generate", "icomp", "listi", "mkindx", "qproc", "show",
                                         "_nextptr", "createf", "write_install_dicts"), messages=(6129,), dictdir=True)
        say("sandbox-dictfold: SOLO MODE - " + why.splitlines()[0])
        if not ok:
            bail(why)
        wr = subprocess.run([sys.executable, TOOL, box, "sess", os.path.join(box, "sys"), "RUN gpl.bp write_install_dicts NO.PAGE"],
                            capture_output=True, text=True, errors="replace", timeout=300)
        if not re.search(r"(?m)^COMPLETE\s*$", ANSI.sub("", wr.stdout + wr.stderr)):
            bail("Solo's write_install_dicts did not reach COMPLETE")
    xt = "zzxt" + RUN
    # the I-type: its expression names F1 and F3 in UPPER case, the dictionary stores f1 and f3 lower
    with open(os.path.join(box, "sys", "bp", xt), "wb") as f:
        f.write(b"I\nF1 : '-' : F3\n\nXtype\n12L\nS\n")
    # F1 and F3 as D-type items, written here and copied from bp: COPY does not fold, and the shipped
    # DICT VOC stores f1 in lower case on a build that has stage 2b and F1 in upper case on one that has
    # not, so copying it would make the fixture differ between the builds this script is run against.
    f1, f3 = "zzf1" + RUN, "zzf3" + RUN
    for rec, num, nm in ((f1, b"1", b"F1"), (f3, b"3", b"F3")):
        with open(os.path.join(box, "sys", "bp", rec), "wb") as f:
            f.write(b"D\n" + num + b"\n\n" + nm + b"\n5L\nS\n")
    try:
        say("\n--- setup: %s stores f1, f3 and xtype in LOWER case; %s stores F1 in UPPER case ----------" % (F, G))
        out = sess(box,
                   "CREATE.FILE " + F, "COPY FROM BP TO DICT %s %s,f1" % (F, f1), "COPY FROM BP TO DICT %s %s,f3" % (F, f3),
                   "COPY FROM BP TO DICT %s %s,xtype" % (F, xt), "COPY FROM VOC TO %s who,r1" % F, "LIST DICT " + F,
                   "CREATE.FILE " + G, "COPY FROM BP TO DICT %s %s,F1" % (G, f1), "COPY FROM VOC TO %s who,r1" % G,
                   "LIST DICT " + G)
        copied = len(re.findall(r"(?m)^1 record\(s\) copied\.", out))
        row("setup: all six COPY commands each copied one record", copied == 6, "copied lines: %d" % copied)
        for ident in ("f1", "f3", "xtype"):
            row("setup: %s's dictionary holds '%s' in lower case" % (F, ident),
                re.search(r"(?m)^" + ident + r"\s{2,}[DI]\s", out) is not None, "no LIST DICT row for " + ident)
        row("setup: %s's dictionary holds 'F1' in upper case" % G,
            re.search(r"(?m)^F1\s{2,}D\s", out) is not None, "no upper-case F1 row")
        if failed:
            bail("the fixture is not what the rows assume - nothing below would measure the fold")

        say("\n--- leg 1: LIST names the field in upper case; the dictionary stores it lower case ----------")
        out = sess(box, "LIST %s F1" % F, "LIST %s f1" % F)
        h = heads(out, F)
        say("    column headings, in order: %s" % " | ".join(h))
        row("leg 1: both LISTs printed a column heading", len(h) == 2, "got %d" % len(h))
        row("CONTROL leg 1: f1 typed lower uses the dictionary item (heading 'F1...')",
            len(h) == 2 and h[1] == "F1...", " | ".join(h))
        row("leg 1: F1 typed UPPER uses the same dictionary item (heading 'F1...')",
            len(h) == 2 and h[0] == "F1...", " | ".join(h))

        say("\n--- leg 2: CD of an I-type whose expression names F1 and F3 in upper case --------------------")
        out = sess(box, "CD %s xtype" % F)
        compiled = re.search(r"(?m)^Compiling xtype\s*$", out) is not None
        row("leg 2: CD reached the compiler ('Compiling xtype')", compiled, "no Compiling line: nothing below is measured")
        row("leg 2: the expression's F1 and F3 resolved to f1 and f3 (no error)",
            compiled and "is not defined" not in out and "Compilation error" not in out,
            "a field name in the expression was not found")
        out = sess(box, "LIST %s xtype" % F)
        row("leg 2: LIST xtype evaluates it (field 1 and 3 of VOC's WHO, joined by '-')",
            re.search(r"(?m)^r1\s+\S.*-\s*\S", out) is not None, "no r1 row with a '-' in it")

        say("\n--- leg 3: the other way round - %s stores F1 in upper case, the query names f1 in lower ---" % G)
        out = sess(box, "LIST %s f1" % G, "LIST %s F1" % G)
        h = heads(out, G)
        say("    column headings, in order: %s" % " | ".join(h))
        row("leg 3: both LISTs printed a column heading", len(h) == 2, "got %d" % len(h))
        row("CONTROL leg 3: F1 typed UPPER uses the stored item (heading 'F1...')",
            len(h) == 2 and h[1] == "F1...", " | ".join(h))
        row("leg 3: f1 typed lower uses the same stored item (heading 'F1...')",
            len(h) == 2 and h[0] == "F1...", " | ".join(h))

        # ---- stage 2b: the shipped ids are lower case, and an upgrade replaces rather than twins ------
        H = "ZZH" + RUN
        say("\n--- leg 4 (stage 2b): the shipped dictionary ids are lower case; CREATE.FILE writes @id ---------")
        out = sess(box, "CREATE.FILE " + H, "LIST DICT " + H, "LIST DICT VOC")
        row("leg 4: CREATE.FILE said it added '@id' (6129)",
            re.search(r"(?m)^Added default '@id' record to dictionary", out) is not None, "no 6129 line naming '@id'")
        row("leg 4: the new dictionary stores '@id' and no '@ID'",
            re.search(r"(?m)^@id\s{2,}D\s", out) is not None and re.search(r"(?m)^@ID\s{2,}D\s", out) is None,
            "LIST DICT shows '@ID' or no '@id'")
        for ident in ("type", "f1", "data.name", "ftype"):
            row("leg 4: DICT VOC holds '%s' in lower case, and no upper-case twin" % ident,
                re.search(r"(?m)^" + re.escape(ident) + r"\s{2,}[DI]\s", out) is not None
                and re.search(r"(?m)^" + re.escape(ident.upper()) + r"\s{2,}[DI]\s", out) is None,
                "the shipped id is not stored lower case")

        say("\n--- leg 5 (stage 2b): an UPGRADE replaces the old upper-case ids; an item of the administrator's is kept")
        ctl = "zzc" + RUN
        out = sess(box, "COUNT DICT VOC")
        m = re.search(r"(?m)^(\d+) record\(s\) counted", out)
        n0 = int(m.group(1)) if m else -1
        # 07 Oct 26 - PAL-1 D2.  The plant used to COPY type to TYPE beside it, which made a twin pair on a
        # case-sensitive dictionary.  Under D2 the dictionary is case insensitive: that COPY overwrites type
        # in place and the stored spelling stays 'type'.  So the plant is a program that READS the shipped
        # item, DELETES it and WRITES it back under the upper-case id: an item stored as TYPE (the upgraded
        # dictionary of an earlier install) on a build of either kind.  The size is n0 + 1 on both: the two
        # old-style items replace the two shipped ones, and the control is new.
        plant = "zzpl%s" % RUN
        with open(os.path.join(box, "sys", "bp", plant), "wb") as f:
            f.write(("\n".join([
                "   open 'DICT', 'VOC' to d else crt 'PLANT5 cannot open DICT VOC' ; stop",
                "   ids = 'type':@fm:'@id'",
                "   for i = 1 to 2",
                "      read r from d, ids<i> else crt 'PLANT5 no ':ids<i> ; stop",
                "      delete d, ids<i>",
                "      write r on d, upcase(ids<i>)",
                "   next i",
                "   write r on d, '%s'" % ctl,
                "   crt 'PLANT5 done'", "end"]) + "\n").encode("ascii"))
        out = sess(box, "BASIC bp " + plant, "RUN bp " + plant, "COUNT DICT VOC")
        os.remove(os.path.join(box, "sys", "bp", plant))
        m = re.search(r"(?m)^(\d+) record\(s\) counted", out)
        n1 = int(m.group(1)) if m else -1
        row("leg 5: TYPE and @ID stored in upper case, and a control the shipped data does not know, planted",
            re.search(r"(?m)^PLANT5 done\s*$", out) is not None and n0 > 0 and n1 == n0 + 1, "count %d -> %d" % (n0, n1))
        out = sess(box, "LIST DICT VOC")
        row("leg 5: the listing shows the two old items under their UPPER-case ids (TYPE, @ID) and not type, @id",
            re.search(r"(?m)^TYPE\s{2,}", out) is not None and re.search(r"(?m)^@ID\s{2,}", out) is not None
            and re.search(r"(?m)^type\s{2,}", out) is None and re.search(r"(?m)^@id\s{2,}", out) is None,
            "the plant did not leave TYPE and @ID as the stored spellings")
        out = sess(box, "RUN gpl.bp write_install_dicts NO.PAGE", cwd=os.path.join(box, "sys"))
        row("leg 5: write_install_dicts finished (COMPLETE)", re.search(r"(?m)^COMPLETE\s*$", out) is not None, "no COMPLETE")
        row("leg 5: it reported 'REPLACED OLD ID: voc.dic TYPE BY type'",
            re.search(r"(?m)^REPLACED OLD ID: voc\.dic TYPE BY type\s*$", out) is not None, "no such line")
        row("leg 5: it reported 'REPLACED OLD ID: voc.dic @ID BY @id'",
            re.search(r"(?m)^REPLACED OLD ID: voc\.dic @ID BY @id\s*$", out) is not None, "no such line")
        row("leg 5: it replaced only those two (no REPLACED line for the control)",
            ctl not in out and len(re.findall(r"(?m)^REPLACED OLD ID:", out)) == 2,
            "REPLACED lines: %d" % len(re.findall(r"(?m)^REPLACED OLD ID:", out)))
        out = sess(box, "COUNT DICT VOC", "LIST DICT VOC WITH @ID LIKE \"%s...\" @ID" % ctl)
        m = re.search(r"(?m)^(\d+) record\(s\) counted", out)
        n2 = int(m.group(1)) if m else -1
        row("leg 5: the dictionary is back to its size plus the control (%d)" % (n0 + 1), n2 == n0 + 1, "count %d" % n2)
        row("leg 5: the control item is still there", re.search(r"(?m)^" + ctl + r"\s", out) is not None, "control gone")
    finally:
        subprocess.run([sys.executable, TOOL, box, "stop"], capture_output=True, text=True, timeout=120)
    say("\nsandbox-dictfold: %d passed, %d failed" % (passed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
