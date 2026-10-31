#!/usr/bin/env python3
#
# sandbox-tapeimport.py - TAPE.IMPORT (S.92) stage S3: the filler !tape_fill (gpl.bp/tape_fill) held to a Python oracle.  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-tapeimport.py <dir> [--build] [--mutant=NAME]
#
# <dir> is a sandbox made by sandbox-fromtree.py, SHORT path under /tmp.  With --build it is built first from THIS tree (it must be empty or absent).
# Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 30 Oct 26 dm  Written for S.92 stage S3.
# END-HISTORY
#
# THE INSTRUMENT.  A sandbox cannot make Linux users, so create_account (which calls the filler through CA$AFTER) is not run here: the VM witness of tape.import runs it.  What
# this suite runs is the filler itself, on a directory that stands for the new account (an empty directory holding a VOC with one entry in it, 'cust', that an imported file of the
# same name must not replace).  A BASIC driver calls !tape_fill for each image, then READS THE ACCOUNT BACK THROUGH SD (every VOC entry, every record of every file and dictionary
# it points at, the counts and the log that the filler leaves in COMMON), and writes one dump per image; this file makes the dump it EXPECTS from the parsed image with the rules of
# the design (the name layer, the folding, the renames, the conversion of SD-D items, md.import) and the two texts are compared.  The directory tree the filler made is walked
# on the disk and must be exactly the list it returned in `made` (what create_account hands over one path at a time).
#   - the 2 real images the old ACCOUNT.SAVE wrote (private .claude/tape-ref; exit 2 without them), the second with a log limit of 3,
#   - one image built to hold every case: a name the account already has, names that cannot be used, a dictionary without data, a duplicate part, a directory file with an id that
#     holds a quote, a binary item, pointers and verbs of the old VOC, ids that fold together.
# THE NULL CASE: a row fails when its dump is missing or empty, or when the filler made nothing at all for an image that must produce files.

import importlib.util
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
TREE_SRC = os.path.normpath(os.path.join(HERE, os.pardir, "sdsys", "gpl.bp", "tape_fill"))
REAL = {"real1": "/home/don/Projects/SDCore4Linux/.claude/tape-ref/as-ref-1.img",
        "real2": "/home/don/Projects/SDCore4Linux/.claude/tape-ref/as-ref-2.img"}
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
passed = failed = 0


def load_twin():
    spec = importlib.util.spec_from_file_location("tapegen", os.path.join(HERE, "tapegen.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


tg = load_twin()
FM, VM, SM, IM = tg.FM, tg.VM, tg.SM, tg.IM


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
    say("sandbox-tapeimport: CANNOT RUN - " + msg)
    sys.exit(2)


def sess(box, *cmds):
    p = subprocess.run([sys.executable, TOOL, box, "sess", os.path.join(box, "user_accounts")] + list(cmds),
                       capture_output=True, text=True, errors="replace", timeout=1800)
    return ANSI.sub("", p.stdout + p.stderr)


def internal(box, *args, stdin=None):
    env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"))
    feed = {"input": stdin} if stdin is not None else {"stdin": subprocess.DEVNULL}
    p = subprocess.run([os.path.join(box, "sys", "bin", "sd"), "-internal"] + list(args), cwd=os.path.join(box, "sys"), env=env,
                       capture_output=True, text=True, errors="replace", timeout=120, **feed)
    return ANSI.sub("", (p.stdout + p.stderr).replace("\r", ""))


def message(n):
    """The text of message n from the tree, with %1.. left as they are."""
    return open(os.path.join(os.path.dirname(TREE_SRC), os.pardir, "messages", str(n)), encoding="utf-8").read()


# ---------------------------------------------------------------------------------------------------------------------------
# The image that holds every case.

def mix_image(layout="as", flat=False):
    """Every case in one image.  For a layout other than AS the binary item (not read there) is left out and a header token, an F and an E item and a file with a hex number are added."""
    m = tg.small_model(account=b"MIX", records=0)
    items = [{"kind": "D", "level": b"1", "num": b"10", "name": b"MIX", "attrs": [b"D", b"101", b"101", b"", b"", b"", b"", b"SYS2", b"L", b"12", b""]}]

    def hdr(level, num, name, dtype=b"D"):
        items.append({"kind": "D", "level": level, "num": num, "name": name, "attrs": [dtype, b"101", b"1", b"", b"", b"", b"", b"", b"L", b"10", b""]})

    def rec(num, rid, fields, grp=b"11"):
        items.append({"kind": "I", "num": num, "group": grp, "id": rid, "fields": fields})

    sdd = [b"A", b"3", b"Qty", b"", b"", b"", b"", b"", b"R", b"8", b"", b"", b"", b"", b"", b"", b"SD-D" + VM + b"M" + VM + b"asso" + VM + b"usr"]
    hdr(b"2", b"11", b"CUST")
    rec(b"11", b"@id", sdd)
    rec(b"11", b"NAME", [b"D", b"1", b"Name", b"20L", b"S"])
    hdr(b"3", b"12", b"CUST")
    rec(b"12", b"C1", [b"first", b"x" + VM + b"y" + SM + b"z"])
    rec(b"12", b"c1", [b"folds onto C1"])
    rec(b"12", b"C 2", [b"space in the id", b""])
    rec(b"12", b"bad\x01id", [b"a control byte"])
    rec(b"12", b"caf\xe9", [b"a byte above 127"])
    rec(b"12", b"x" * 70, [b"too long"])
    rec(b"12", b"", [b"no id"])
    rec(b"12", b"../up", [b"a slash"])
    items.append({"kind": "O", "num": b"12", "group": b"11", "id": b"BIN", "data": b"ab" + IM + b"cd"})
    hdr(b"3", b"13", b"../evil")
    rec(b"13", b"R1", [b"a file whose name is a path"])
    hdr(b"3", b"14", b"Odd Name")
    rec(b"14", b"R1", [b"a file whose name has a space"])
    hdr(b"2", b"15", b"ABC")
    rec(b"15", b"F1", sdd)
    hdr(b"3", b"16", b"DOCS", b"DQ")
    rec(b"16", b"note.txt", [b"hello", b"second line", b""])
    rec(b"16", b"it's", [b"a quote in a directory file id"])
    rec(b"16", b"two words", [b"a space in a directory file id"])
    rec(b"16", b"UPPER", [b"folds"])
    rec(b"16", b"upper", [b"folds onto UPPER"])
    hdr(b"3", b"17", b"DOCS", b"DQ")
    rec(b"17", b"never", [b"a second data part of the same name"])
    hdr(b"3", b"11", b"AGAIN")                          # a second header for file number 11
    hdr(b"3", b"18", b"md.import")
    rec(b"18", b"K", [b"a file called like the one the old VOC goes to"])
    hdr(b"3", b"19", b"tape.cust")
    rec(b"19", b"K", [b"folds onto the name cust is renamed to"])
    hdr(b"3", b"20", b"007")
    rec(b"20", b"K", [b"numeric name"])
    hdr(b"3", b"21", b"7")
    rec(b"21", b"K", [b"another numeric name"])
    hdr(b"3", b"22", b"Zed")
    rec(b"22", b"z1", [b"in a file"])
    rec(b"10", b"F1", [b"F", b"PATH"], grp=b"12")      # the old VOC: a pointer, skipped
    rec(b"10", b"Q1", [b"Q", b"ACC", b"FILE"], grp=b"12")
    rec(b"10", b"X1", [b"V", b"CA", b"$prog"], grp=b"12")
    rec(b"10", b"x1", [b"V", b"CA", b"$other"], grp=b"12")   # folds onto X1
    rec(b"10", b"bad/id", [b"V"], grp=b"12")
    rec(b"10", b"PA1", [b"PA", b"DISPLAY hi"], grp=b"12")
    if layout != "as":
        items = [i for i in items if i["kind"] != "O"]
        hdr(b"3", b"1F", b"hexfile")
        rec(b"1F", b"K1", [b"in a file whose number is hex"], grp=b"A0")
        rec(b"1F", b"K2", [b"read like an I item"], grp=b"A0")
        items[-1]["tag"] = b"F"
        rec(b"1F", b"K3", [b"read like an I item, too"], grp=b"A0")
        items[-1]["tag"] = b"E"
        items.insert(0, {"kind": "H", "text": b"mvBase header"})
        items.append({"kind": "H", "text": b""})
    m["items"] = items
    return tg.build_image(m, layout, flat=flat)


# ---------------------------------------------------------------------------------------------------------------------------
# The oracle: what the account must hold after the filler.

ON_DISK = {b"voc"}      # what the fixture's account directory holds besides what the VOC names (a real one has more: $svlists, cat)


def esc(b, limit):
    return bytes(c if (32 <= c <= 126 and c != 0x7C) else 0x3F for c in b[:limit]).decode("latin-1")


def expected(data, initial_voc, logcap=10000, layout="as"):
    m = tg.parse_image(data, layout=layout)
    voc = dict(initial_voc)            # id (lower) -> record bytes
    files = {}                         # final -> {"data": {id: rec} or None, "dict": ..., "dir": bool}
    log = []
    suppressed = 0
    counts = {"files": 0, "dicts": 0, "recs": 0, "skip": 0, "md": 0, "bin": 0}
    keys = {}                          # num -> {"kind", "name", "final", "isdir"}
    fl = []                            # {"base", "final", "hasdict", "hasdata"}
    md = {}
    md_n = 0

    def addlog(kind, f, i, why):
        nonlocal suppressed
        if len(log) >= logcap:
            suppressed += 1
            return
        log.append("%s|%s|%s|%s" % (kind, esc(f, 80), esc(i, 60), why))

    for it in m["items"]:
        if it["kind"] == "H":
            counts["skip"] += 1
            addlog("header", b"", b"", "a header token of the image (%d bytes) was left out" % len(it["text"]))
            continue
        if it["kind"] == "D":
            num = it["num"]
            level = it["level"]
            base = it["name"].lower()
            if num in keys:
                addlog("file", base, b"", "a second header for file number " + num.decode())
                continue
            if level == b"1":
                keys[num] = {"kind": "md", "name": b"md"}
                continue
            keys[num] = {"kind": "skip", "name": base}
            why = tg.file_name_verdict(base)
            if why:
                addlog("file", base, b"", "the file name cannot be used (%s)" % why)
                continue
            k = next((f for f in fl if f["base"] == base), None)
            if k is None:
                final = base
                if final in voc or final in ON_DISK:
                    final = b"tape." + base
                if final == b"md.import":
                    final = b"tape.md.import"
                if final in voc or final in ON_DISK:
                    addlog("file", base, b"", "the name is taken, and so is tape." + base.decode())
                    continue
                if any(f["final"] == final for f in fl):
                    addlog("file", base, b"", "the name folds to a file already made")
                    continue
                k = {"base": base, "final": final, "hasdict": False, "hasdata": False}
                fl.append(k)
                files[final] = {"data": None, "dict": None, "dir": False}
                if final != base:
                    addlog("file", base, b"", "the name is one the account already has; the file is called " + final.decode())
            final = k["final"]
            dtype = it["attrs"][0]
            if level == b"2":
                if k["hasdict"]:
                    addlog("file", base, b"", "a second dictionary of the same name")
                    continue
                files[final]["dict"] = {}
                k["hasdict"] = True
                counts["dicts"] += 1
                keys[num] = {"kind": "dict", "name": final + b".dic", "final": final, "isdir": False}
            else:
                if k["hasdata"]:
                    addlog("file", base, b"", "a second data part of the same name")
                    continue
                files[final]["data"] = {}
                files[final]["dir"] = (dtype == b"DQ")
                k["hasdata"] = True
                counts["files"] += 1
                keys[num] = {"kind": "data", "name": final, "final": final, "isdir": dtype == b"DQ"}
            continue
        # an item
        e = keys.get(it["num"])
        if e is None:
            addlog("item", it["num"], it["id"], "an item of a file with no usable header")
            counts["skip"] += 1
            continue
        if it["kind"] == "O":
            counts["bin"] += 1
            addlog("item", e["name"], it["id"], "binary item (%d bytes) skipped" % len(it["data"]))
            continue
        rid = it["id"]
        rec = FM.join(it["fields"])
        if e["kind"] == "skip":
            counts["skip"] += 1
        elif e["kind"] == "md":
            t1 = it["fields"][0] if it["fields"] else b""
            if t1 in (b"F", b"Q"):
                addlog("item", b"md", rid, "a pointer of the old VOC, skipped")
                counts["skip"] += 1
                continue
            why = tg.name_verdict(rid)
            if why:
                addlog("item", b"md", rid, "record id cannot be used (%s)" % why)
                counts["skip"] += 1
                continue
            if rid.lower() in md:
                addlog("item", b"md", rid, "a record with this id (case folded) is already there")
                counts["skip"] += 1
                continue
            md[rid.lower()] = rec
            md_n += 1
            counts["md"] += 1
        else:
            why = tg.name_verdict(rid)
            if why is None and e["isdir"] and b"'" in rid:
                why = "quote"
            if why:
                addlog("item", e["name"], rid, "record id cannot be used (%s)" % why)
                counts["skip"] += 1
                continue
            part = files[e["final"]]["dict" if e["kind"] == "dict" else "data"]
            if rid.lower() in part:
                addlog("item", e["name"], rid, "a record with this id (case folded) is already there")
                counts["skip"] += 1
                continue
            if e["kind"] == "dict" and it["fields"] and it["fields"][0] == b"A":
                f17 = it["fields"][16] if len(it["fields"]) > 16 else b""
                if f17.split(VM)[0][:4] in (b"SD-D", b"QM-D"):
                    sub = f17.split(VM)
                    g = lambda n: it["fields"][n - 1] if len(it["fields"]) >= n else b""
                    rec = FM.join([b"D", g(2), g(8), g(3), g(10) + g(9), sub[1] if len(sub) > 1 else b"", sub[2] if len(sub) > 2 else b"", sub[3] if len(sub) > 3 else b""])
            part[rid.lower()] = rec
            counts["recs"] += 1
    for k in fl:
        f = k["final"]
        if not k["hasdata"]:
            files[f]["data"] = {}
            k["hasdata"] = True
            counts["files"] += 1
            addlog("file", f, b"", "the image has a dictionary and no data part: an empty data file was made")
        voc[f] = b"F" + FM + f + ((FM + f + b".dic") if k["hasdict"] else b"")
    if md_n > 0:
        voc[b"md.import"] = b"F" + FM + b"md.import"
        files[b"md.import"] = {"data": md, "dict": None, "dir": False}
    if suppressed:
        log.append("*|*||%d more lines were not kept" % suppressed)
    return voc, files, log, counts


def dump_expected(data, initial_voc, logcap=10000, layout="as"):
    voc, files, log, c = expected(data, initial_voc, logcap, layout)
    lines = ["C|%d|%d|%d|%d|%d|%d|%d" % (c["files"], c["dicts"], c["recs"], c["skip"], c["md"], c["bin"], len([l for l in log if not l.startswith("*|*")])),
             "E|"]
    lines += ["L|" + l for l in log]
    for vid, vrec in voc.items():
        lines.append("V|%s|%s" % (vid.hex().upper(), vrec.hex().upper()))
    for final, f in files.items():
        for part, name in (("data", final), ("dict", final + b".dic")):
            if f[part] is None:
                continue
            for rid, rec in f[part].items():
                lines.append("R|%s|%s|%s" % (name.hex().upper(), rid.hex().upper(), rec.hex().upper()))
    return lines


def normalise(text, dirfiles=()):
    """The dump of the driver, as sorted comparable pieces: the log in order, the rest sorted."""
    lines = [l for l in text.split("\n") if l != ""]
    keep = [l for l in lines if l.startswith("L|")]
    rest = sorted(l for l in lines if not l.startswith("L|") and not l.startswith("M|"))
    return keep, rest


# ---------------------------------------------------------------------------------------------------------------------------
# The BASIC driver.

DRIVER = r"""* ZZTIFILL - calls !tape_fill for each case of a list, reads the account back and writes one dump per case (sandbox-tapeimport.py)
   common /tapeimp/ tf.log, tf.nlog, tf.nfiles, tf.ndicts, tf.nrecs, tf.nskip, tf.nmd, tf.nbin, tf.logcap, tf.suppressed, tf.src
   listp = '%(list)s'
   hexd = '0123456789ABCDEF'
   nl = char(10)
   open 'zzticout' to outf else
      crt 'NOOUT'
      stop
   end
   openseq listp readonly to lf else
      crt 'NOLIST'
      stop
   end
   crt 'DRIVER STARTED'
   n.case = 0
   loop
      readseq line from lf else exit
      name = field(line, '|', 1)
      img = field(line, '|', 2)
      acct = field(line, '|', 3)
      cap = field(line, '|', 4)
      lay = field(line, '|', 5)
      create.file acct : '/voc' dynamic on error
         crt 'CANNOT MAKE VOC ' : name
         continue
      end
      openpath acct : '/voc' to vf else
         crt 'CANNOT OPEN VOC ' : name
         continue
      end
      write 'V' : @fm : 'CA' : @fm : 'x' to vf, 'cust'
      close vf
      arg = img : @fm : @fm : @fm : @fm : cap : @fm : lay
      made = '' ; ferr = ''
      call !tape_fill(acct, arg, made, ferr)
      txt = 'C|' : tf.nfiles : '|' : tf.ndicts : '|' : tf.nrecs : '|' : tf.nskip : '|' : tf.nmd : '|' : tf.nbin : '|' : tf.nlog
      txt := nl : 'E|' : ferr
      for j = 1 to dcount(tf.log, @fm)
         if tf.log = '' then exit
         txt := nl : 'L|' : tf.log<j>
      next j
      for j = 1 to dcount(made, @fm)
         if made = '' then exit
         txt := nl : 'M|' : made<j>[len(acct) + 2, 999999]
      next j
      * read the account back: the VOC, then every file and dictionary it points at
      openpath acct : '/voc' to vf else
         crt 'CANNOT REOPEN VOC ' : name
         continue
      end
      vids = ''
      select vf
      loop
         readnext vid else exit
         vids<-1> = vid
      repeat
      for v = 1 to dcount(vids, @fm)
         if vids = '' then exit
         vid = vids<v>
         read vrec from vf, vid else vrec = ''
         s = vid
         gosub hexify
         hid = hx
         s = vrec
         gosub hexify
         txt := nl : 'V|' : hid : '|' : hx
         if vrec<1> = 'F' and vid # 'cust' then
            for part = 2 to 3
               fpath = vrec<part>
               if fpath # '' then
                  openpath acct : '/' : fpath to df then
                     rids = ''
                     select df
                     loop
                        readnext rid else exit
                        rids<-1> = rid
                     repeat
                     for r = 1 to dcount(rids, @fm)
                        if rids = '' then exit
                        rid = rids<r>
                        read rrec from df, rid else rrec = ''
                        s = fpath
                        gosub hexify
                        hf = hx
                        s = rid
                        gosub hexify
                        hi = hx
                        s = rrec
                        gosub hexify
                        txt := nl : 'R|' : hf : '|' : hi : '|' : hx
                     next r
                     close df
                  end else
                     txt := nl : 'X|cannot open ' : fpath
                  end
               end
            next part
         end
      next v
      close vf
      write txt to outf, name
      n.case += 1
   repeat
   crt 'DRIVER DONE ' : n.case
   stop

hexify:
   hx = ''
   for j2 = 1 to len(s)
      v2 = seq(s[j2, 1])
      hx := hexd[int(v2 / 16) + 1, 1] : hexd[mod(v2, 16) + 1, 1]
   next j2
   return
"""


def main():
    global passed, failed
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = [a for a in sys.argv[1:] if a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-tapeimport.py <dir> [--build] [--mutant=NAME]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    mutant = None
    for o in opts:
        if o.startswith("--mutant="):
            mutant = o.split("=", 1)[1]
    for k, p in REAL.items():
        if not os.path.isfile(p) or os.path.getsize(p) == 0:
            bail("the reference image %s is missing" % p)
    say("sandbox-tapeimport: sandbox %s" % box)
    if "--build" in opts:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-tapeimport: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    # the programs of THIS tree, compiled into the sandbox's catalogue (a mutant changes the sandbox's copy of the filler only)
    for prog in ("tapeimg", "tape_fill"):
        src = open(os.path.join(os.path.dirname(TREE_SRC), prog), encoding="utf-8").read()
        if mutant and prog == "tape_fill":
            old, new = MUTANTS[mutant]
            if src.count(old) != 1:
                bail("mutant %s: the old text occurs %d times" % (mutant, src.count(old)))
            src = src.replace(old, new)
            say("sandbox-tapeimport: MUTANT %s" % mutant)
        open(os.path.join(sysd, "gpl.bp", prog), "w", encoding="utf-8").write(src)
        out = internal(box, "BASIC", "GPL.BP", prog)
        row("setup: !%s compiled with no errors" % prog, re.search(r"(?m)^Compiled 1 program\(s\) with no errors", out) is not None, out[-300:])

    work = os.path.join(sysd, "zzfill")
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    imgdir = os.path.join(work, "img")
    os.mkdir(imgdir)
    try:
        cases = [("real1", open(REAL["real1"], "rb").read(), "", "as"), ("real2", open(REAL["real2"], "rb").read(), "3", "as"),
                 ("mix", mix_image(), "", "as"),
                 # S4a: the other layouts, the same cases with a header token, F and E items and a hex file number (the binary item is not read there)
                 ("mix-mv", mix_image("mv"), "", "mv"), ("mix-r83-flat", mix_image("r83", flat=True), "", "r83"),
                 ("gen-small", tg.build_image(tg.gen_model(), "jbs"), "", "jbs"), ("mix-mv-cap", mix_image("mv"), "4", "mv")]
        initial = {b"cust": b"V" + FM + b"CA" + FM + b"x"}
        lines = []
        for name, data, cap, layout in cases:
            ip = os.path.join(imgdir, name + ".img")
            open(ip, "wb").write(data)
            ap = os.path.join(work, "acct-" + name)
            os.mkdir(ap)
            lines.append("%s|%s|%s|%s|%s" % (name, ip, ap, cap, layout if layout != "as" else ""))
        listf = os.path.join(work, "list.txt")
        open(listf, "w").write("\n".join(lines) + "\n")
        open(os.path.join(sysd, "bp", "zztifill"), "w").write(DRIVER % {"list": listf})
        sess(box, "DELETE.FILE zzticout", "CREATE.FILE zzticout DIRECTORY")
        out = sess(box, "BASIC bp zztifill")
        row("setup: the driver compiled with no errors", re.search(r"(?m)^Compiled 1 program\(s\) with no errors", out) is not None, out[-300:])
        out = sess(box, "RUN bp zztifill")
        if "DRIVER STARTED" not in out:
            bail("the driver never started:\n" + out[-600:])
        m = re.search(r"DRIVER DONE (\d+)", out)
        row("the driver filled every case", m is not None and int(m.group(1)) == len(cases) and "CANNOT" not in out,
            "done=%s of %d; %s" % (m.group(1) if m else None, len(cases), out[-300:].replace("\n", " | ")))

        for name, data, cap, layout in cases:
            say("\n--- %s " % name + "-" * (90 - len(name)))
            fp = os.path.join(sysd, "zzticout", name)
            got = open(fp, "rb").read().decode("latin-1") if os.path.isfile(fp) else None
            row("%s: the filler left a dump" % name, got is not None and got != "", "no dump")
            if not got:
                continue
            want = dump_expected(data, initial, int(cap) if cap else 10000, layout)
            g_log, g_rest = normalise(got)
            w_log, w_rest = normalise("\n".join(want))
            row("%s: no error from the filler" % name, "E|" in got.split("\n") and not any(l.startswith("E|") and len(l) > 2 for l in got.split("\n")),
                [l for l in got.split("\n") if l.startswith("E|")][0] if got else "")
            row("%s: counts equal (%s)" % (name, [l for l in want if l.startswith("C|")][0]),
                [l for l in got.split("\n") if l.startswith("C|")] == [l for l in want if l.startswith("C|")],
                "got %s" % [l for l in got.split("\n") if l.startswith("C|")])
            row("%s: the log equal, in order (%d lines)" % (name, len(w_log)), g_log == w_log,
                "first difference: got %r want %r" % (next((a for a, b in zip(g_log, w_log) if a != b), g_log[len(w_log):][:1]), next((b for a, b in zip(g_log, w_log) if a != b), w_log[len(g_log):][:1])))
            sg, sw = set(g_rest), set(w_rest)
            diff_g = [l for l in g_rest if l not in sw]
            diff_w = [l for l in w_rest if l not in sg]

            def by_file(ls):
                out = {}
                for l in ls:
                    p = l.split("|")
                    k = bytes.fromhex(p[1]).decode("latin-1") if p[0] == "R" else p[0]
                    out[k] = out.get(k, 0) + 1
                return out
            wg, ww = dict((l.split("|")[1] + "|" + l.split("|")[2], l) for l in diff_g if l.startswith("R|")), dict((l.split("|")[1] + "|" + l.split("|")[2], l) for l in diff_w if l.startswith("R|"))
            both = [k for k in wg if k in ww]
            ex = ("; same record, different content: %s\n        account %s\n        expected %s" % (bytes.fromhex(both[0].split("|")[1]).decode("latin-1"), wg[both[0]].split("|")[3][:140], ww[both[0]].split("|")[3][:140])) if both else ""
            row("%s: the VOC and every record of every file equal (%d lines)" % (name, len(w_rest)), g_rest == w_rest,
                "%d only in the account %s, %d only expected %s; %d records differ in content%s" % (len(diff_g), by_file(diff_g), len(diff_w), by_file(diff_w), len(both), ex))
            # the tree on disk is what the filler said it made
            acct = os.path.join(work, "acct-" + name)
            on_disk = set()
            for root, dirs, files in os.walk(acct):
                rel = os.path.relpath(root, acct)
                if rel == "voc" or rel.startswith("voc" + os.sep):
                    continue
                for d in dirs:
                    if not (rel == "." and d == "voc"):
                        on_disk.add(os.path.normpath(os.path.join(rel, d)))
                for f in files:
                    on_disk.add(os.path.normpath(os.path.join(rel, f)))
            said = set(l[2:] for l in got.split("\n") if l.startswith("M|"))
            row("%s: the list it returned is exactly the tree it made (%d paths)" % (name, len(on_disk)), on_disk == said and len(said) > 0,
                "%d only on disk (%r), %d only said (%r)" % (len(on_disk - said), sorted(on_disk - said)[:2], len(said - on_disk), sorted(said - on_disk)[:2]))

        # ---------------------------------------------------------------------------------------------------------------------------
        say("\n--- the verb: syntax, LIST, refusals and the question (none of these makes an account) -------------------")
        tree_gp = os.path.dirname(TREE_SRC)
        for n in list(range(11919, 11930)) + list(range(11938, 11943)):
            shutil.copy(os.path.join(tree_gp, os.pardir, "messages", str(n)), os.path.join(sysd, "messages", str(n)))
        shutil.copy(os.path.join(tree_gp, os.pardir, "syscom", "createacc.h"), os.path.join(sysd, "syscom", "createacc.h"))
        shutil.copy(os.path.join(tree_gp, "tapeimp"), os.path.join(sysd, "gpl.bp", "tapeimp"))
        out = internal(box, "BASIC", "GPL.BP", "tapeimp")
        row("setup: $tapeimp compiled with no errors", re.search(r"(?m)^Compiled 1 program\(s\) with no errors", out) is not None, out[-300:])
        open(os.path.join(sysd, "bp", "zzvoc"), "w").write("   open 'VOC' to vf else crt 'NOVOC' ; stop\n   write 'V' : @fm : 'CA' : @fm : '$tapeimp' to vf, 'tape.import'\n   crt 'WROTE'\n")
        out = sess(box, "BASIC bp zzvoc", "RUN bp zzvoc")
        row("setup: tape.import is in the SDSYS VOC", "WROTE" in out, out[-200:])
        m1, m2 = tg.parse_image(open(REAL["real1"], "rb").read()), tg.parse_image(open(REAL["real2"], "rb").read())

        def counts(m):
            return (len([i for i in m["items"] if i["kind"] == "D" and i["level"] == b"3"]), len([i for i in m["items"] if i["kind"] == "I"]),
                    len([i for i in m["items"] if i["kind"] == "O"]))
        img1, img2 = REAL["real1"], REAL["real2"]
        users_before = sorted(os.listdir(os.path.join(box, "user_accounts"))) if os.path.isdir(os.path.join(box, "user_accounts")) else []

        out = internal(box, "TAPE.IMPORT")
        row("no argument: the syntax", "Syntax: tape.import" in out, out[-200:])
        for tag, img, mm in (("real1", img1, m1), ("real2", img2, m2)):
            nf, ni, nb = counts(mm)
            out = internal(box, "TAPE.IMPORT", img, "LIST")
            row("LIST %s: %d files, %d records" % (tag, nf, ni), "Image %s: account DON, %d file(s), %d record(s)" % (img, nf, ni) in out, out[-300:])
            row("LIST %s: the file names" % tag, all(re.search(r"(?m)^  %s$" % n, out) for n in ("docs", "bp", "cust", "ord", "voc")), out[-300:])
            row("LIST %s: %d binary item(s) said%s" % (tag, nb, "" if nb else " (none, so nothing said)"),
                (("%d binary item(s) are left out." % nb) in out) if nb else ("binary item" not in out), out[-300:])
        bad = os.path.join(work, "img", "refused.img")
        open(bad, "wb").write(tg.RECIPES["truncated-at-block-boundary"][0]())
        out = internal(box, "TAPE.IMPORT", bad, "LIST")
        row("LIST of a refused image: R-NOEOF and nothing else", "The image was refused: R-NOEOF" in out and "Image " not in out, out[-300:])
        out = internal(box, "TAPE.IMPORT", "relative/path.img", "LIST")
        row("a path that is not written in the one form: R-PATH", "The image was refused: R-PATH" in out, out[-300:])
        out = internal(box, "TAPE.IMPORT", os.path.join(work, "img", "no-such.img"), "LIST")
        row("a file that is not there: R-OPEN", "The image was refused: R-OPEN" in out, out[-300:])
        out = internal(box, "TAPE.IMPORT", img1, "FROM", "someoneelse", "LIST")
        row("FROM another account is refused", "The image holds the account DON, not someoneelse." in out, out[-300:])
        out = internal(box, "TAPE.IMPORT", img1, "FROM", "don", "LIST")
        row("FROM the account it holds (any case) goes on", "account DON, " in out and "The image holds the account" not in out, out[-300:])
        out = internal(box, "TAPE.IMPORT", img1)
        row("no TO: the syntax", "Syntax: tape.import" in out, out[-200:])
        out = internal(box, "TAPE.IMPORT", img1, "TO", "newone", stdin="N\n")
        row("the question is asked and N imports nothing", "Import the image into the NEW user account newone? (Y/N)" in out and "Nothing was imported." in out, out[-300:])
        out = internal(box, "TAPE.IMPORT", img1, "TO", "newone", stdin="")
        row("the question at the end of the input imports nothing (it does not loop)", "Nothing was imported." in out, out[-300:])
        # S4a: FORMAT takes the other layouts.  The images are written by tapegen (no real image of them has been seen).
        gen_jbs = os.path.join(work, "img", "gen-jbs.img")
        gen_mv = os.path.join(work, "img", "gen-mv.img")
        gen_r83 = os.path.join(work, "img", "gen-r83.img")
        open(gen_jbs, "wb").write(tg.build_image(tg.gen_model(), "jbs"))
        open(gen_mv, "wb").write(tg.build_image(tg.gen_model(head=[{"kind": "H", "text": b"mvBase header"}]), "mv"))
        open(gen_r83, "wb").write(tg.build_image(tg.gen_model(), "r83", flat=True))
        out = internal(box, "TAPE.IMPORT", img1, "TO", "newone", "FORMAT", "R83")
        row("FORMAT R83 over an image of the AS layout: the reader refuses it with a code, it is not a syntax error",
            "The image was refused: R-" in out and "Syntax: tape.import" not in out, out[-300:])
        out = internal(box, "TAPE.IMPORT", img1, "TO", "newone", "FORMAT", "XYZ")
        row("FORMAT with a word that is no layout: the syntax", "Syntax: tape.import" in out, out[-200:])
        out = internal(box, "TAPE.IMPORT", gen_jbs, "TO", "newone", "FORMAT", "ULTFS")
        row("FORMAT ULTFS is refused by name (R-UNSUPPORTED, and the sentence says ultfs)", "The image was refused: R-UNSUPPORTED" in out and "ultfs" in out, out[-300:])
        for word, path in (("JBS", gen_jbs), ("FS", gen_jbs), ("MV", gen_mv), ("R83", gen_r83)):
            out = internal(box, "TAPE.IMPORT", path, "LIST", "FORMAT", word)
            row("LIST FORMAT %s: the account its file header names, 1 file, 3 records" % word,
                "Image %s: account DEMO, 1 file(s), 3 record(s)" % path in out and "The image was refused" not in out, out[-300:])
        out = internal(box, "TAPE.IMPORT", gen_jbs, "LIST")
        row("an image of another layout asked for as AS: refused with a code, nothing listed", "The image was refused: R-" in out and "Image " not in out, out[-300:])
        out = internal(box, "TAPE.IMPORT", gen_jbs, "FROM", "other", "LIST", "FORMAT", "JBS")
        row("FROM another account is refused for a layout whose file header names the account", "The image holds the account DEMO, not other." in out, out[-300:])
        out = internal(box, "TAPE.IMPORT", gen_jbs, "FROM", "demo", "LIST", "FORMAT", "jbs")
        row("FROM the account the file header names (any case) goes on; the layout word in lower case", "account DEMO, " in out and "The image holds the account" not in out, out[-300:])
        # The administrator check is not run here: a sandbox session is the administrator (the sandbox user plays sdsys), so a refusal cannot be shown;
        # test-tapeimport-units.py holds the check as text (it comes first) and the VM witness shows it for an ordinary account.
        users_after = sorted(os.listdir(os.path.join(box, "user_accounts"))) if os.path.isdir(os.path.join(box, "user_accounts")) else []
        row("none of these made an account or a log", users_before == users_after and not os.path.exists(os.path.join(sysd, "tape.log")),
            "%r -> %r" % (users_before, users_after))
    finally:
        for n in ("zztifill", "zzvoc"):
            for d in ("bp", "bp.out"):
                p = os.path.join(sysd, d, n)
                if os.path.exists(p):
                    os.remove(p)
        sess(box, "DELETE.FILE zzticout")
        shutil.rmtree(work, ignore_errors=True)
        if mutant:
            open(os.path.join(sysd, "gpl.bp", "tape_fill"), "w", encoding="utf-8").write(open(TREE_SRC, encoding="utf-8").read())
            internal(box, "BASIC", "GPL.BP", "tape_fill")

    say("\nsandbox-tapeimport: %d passed, %d failed" % (passed, failed))
    sys.exit(0 if failed == 0 else 1)


# (name, old text, new text) - mutants of gpl.bp/tape_fill, each applied to the sandbox's copy only
MUTANTS = {
    "no-case-fold": ("   lid = downcase(id)\n   read dup from cur.f, lid then", "   lid = id\n   read dup from cur.f, lid then"),
    "no-rename": ("      if taken then final = 'tape.' : base\n", "      if 0 then final = 'tape.' : base\n"),
    "no-disk-check": ("   locate '#' : final in ex.names<1> setting ex.at then taken = 1 else null\n", ""),
    "no-quote-rule": ("   if why = '' and nm.isdir<mp> and index(id, \"'\", 1) then why = 'quote'", "   if 0 then why = 'quote'"),
    "binary-written": ("   if kind = 'O' then\n      tf.nbin += 1\n", "   if 0 then\n      tf.nbin += 1\n"),
    "pointers-kept": ("   if t1 = 'F' or t1 = 'Q' then\n", "   if 0 then\n"),
    "no-sd-d-conversion": ("      if tag = 'SD-D' or tag = 'QM-D' then\n", "      if tag = 'XXXX' then\n"),
    "file-name-as-id": ("call !tapeimg('name', base : fm : 'file' : fm : maxid, k1, k2, k3, k4, why, v)", "call !tapeimg('name', base : fm : 'id' : fm : maxid, k1, k2, k3, k4, why, v)"),
    "second-data-part": ("      if fl.hasdata<k> then\n         add.kind", "      if 0 then\n         add.kind"),
    "no-log-cap": ("   if tf.nlog >= tf.logcap then\n", "   if 0 then\n"),
    "md-import-clash": ("      if final = 'md.import' then final = 'tape.md.import'\n", ""),
    "h-token-as-item": ("         case kind = 'H'\n            gosub do.hdr\n", ""),
    "layout-not-passed": ("arg<3> : fm : arg<4> : fm : arg<6>\n", "arg<3> : fm : arg<4>\n"),
}


if __name__ == "__main__":
    main()
