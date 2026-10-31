#!/usr/bin/env python3
#
# sandbox-tapeimg.py - TAPE.IMPORT (S.92) stage S2: the BASIC reader !tapeimg (gpl.bp/tapeimg) against its Python twin
#                      (gplbld/tapegen.py).  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-tapeimg.py <dir> [--build] [--mutant=NAME] [--fuzz=N]
#
# <dir> is a sandbox made by sandbox-fromtree.py, SHORT path under /tmp.  With --build it is built first from THIS tree (it must be empty
# or absent).  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 30 Oct 26 dm  Written for S.92 stage S2.
# END-HISTORY
#
# THE INSTRUMENT.  One BASIC program (zztidrv) calls !tapeimg over a list of images, item by item, and writes for each image a text file:
# the verdict ('V|R-...') or the label and every item (kind, file number, level or group, id and record, all in hex).  This file
# makes the same dump with tapegen.parse_image.  A row passes when the two texts are EQUAL, so the BASIC reader is held to the
# twin on every byte it returns, not only on the verdict.  The images are
#   - the 42 recipes of tapegen.RECIPES (synthetic and hostile, each with its own verdict),
#   - the two images the old ACCOUNT.SAVE wrote (the private .claude/tape-ref; this suite exits 2 without them),
#   - N images made by changing one thing in a valid image at a time (a seeded generator: one byte, a block's pad, a digit, a mark),
#     where the twin is the oracle and the BASIC may not disagree with it,
#   - the operating system's own refusals, which the twin does not model (no file, a directory, an unreadable file, a path written
#     in more than one form).
# THE NULL CASE: a row also fails when its dump file is missing or empty, and the suite stops with exit 2 if the driver printed nothing.

import importlib.util
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
TREE_SRC = os.path.normpath(os.path.join(HERE, os.pardir, "sdsys", "gpl.bp", "tapeimg"))
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
    say("sandbox-tapeimg: CANNOT RUN - " + msg)
    sys.exit(2)


def sess(box, *cmds):
    p = subprocess.run([sys.executable, TOOL, box, "sess", os.path.join(box, "user_accounts")] + list(cmds),
                       capture_output=True, text=True, errors="replace", timeout=1800)
    return ANSI.sub("", p.stdout + p.stderr)


def internal(box, *args):
    """`sd -internal ...` in the sandbox, as the sandbox builder does (the program being compiled is not run)."""
    env = dict(os.environ, SD_CONFIG=os.path.join(box, "sd.conf"))
    p = subprocess.run([os.path.join(box, "sys", "bin", "sd"), "-internal"] + list(args), cwd=os.path.join(box, "sys"), env=env,
                       capture_output=True, text=True, errors="replace", timeout=600, stdin=subprocess.DEVNULL)
    return ANSI.sub("", p.stdout + p.stderr)


# ---------------------------------------------------------------------------------------------------------------------------
# What the twin says about an image, in the one text format both sides write.

def dump_twin(data, opts):
    try:
        m = tg.parse_image(data, **opts)
    except tg.TapeError as e:
        return "V|" + e.code
    lab = m["label"]
    lines = ["H|%s|%s|%d|%s %s" % (lab["account"].decode(), lab["reel"].decode(), m["blocks"], lab["time"].decode(), lab["date"].decode())]
    for it in m["items"]:
        if it["kind"] == "D":
            lines.append("D|%s|%s|%s|%s" % (it["num"].decode(), it["level"].decode(), it["name"].hex().upper(), tg.FM.join(it["attrs"]).hex().upper()))
        elif it["kind"] == "I":
            lines.append("I|%s|%s|%s|%s" % (it["num"].decode(), it["group"].decode(), it["id"].hex().upper(), tg.FM.join(it["fields"]).hex().upper()))
        else:
            lines.append("O|%s|%s/%d|%s|%s" % (it["num"].decode(), it["group"].decode(), it["blocks"], it["id"].hex().upper(), it["data"].hex().upper()))
    lines.append("E")
    return "\n".join(lines)


# ---------------------------------------------------------------------------------------------------------------------------
# The images.

def fuzz_images(count):
    rnd = random.Random(30102026)
    bases = [(n, tg.RECIPES[n][0]()) for n in ("ok-small", "ok-long-record", "ok-marks-and-high-byte", "ok-binary-forms", "ok-binary-lookalikes")]
    bases.append(("real1", open(REAL["real1"], "rb").read()[: 512 * 9] + tg.eof_block()))
    interesting = [0x00, 0xFF, 0xFE, 0xFD, 0x20, 0x58, 0x82, 0x30, 0x39, 0x4F, 0x44, 0x49, 0x42, 0x4C, 0x31, 0x32, 0x33, 0x34, 0x46]
    out = []
    for i in range(count):
        name, img = rnd.choice(bases)
        b = bytearray(img)
        kind = rnd.choice(("byte", "byte", "byte", "interesting", "interesting", "label", "pad", "swap", "trunc", "dupblock", "dropblock"))
        if kind == "byte":
            b[rnd.randrange(len(b))] = rnd.randrange(256)
        elif kind == "interesting":
            b[rnd.randrange(len(b))] = rnd.choice(interesting)
        elif kind == "label":
            blk = rnd.choice((0, 2, 4)) * tg.PHYS
            b[blk + tg.PAD + rnd.randrange(80)] = rnd.choice(interesting + [0x20, 0x41, 0x61])
        elif kind == "pad":
            blk = rnd.randrange(len(b) // tg.PHYS) * tg.PHYS
            b[blk + rnd.randrange(tg.PAD)] = rnd.choice((0x20, 0x01, 0xFF))
        elif kind == "swap":
            x, y = rnd.randrange(len(b)), rnd.randrange(len(b))
            b[x], b[y] = b[y], b[x]
        elif kind == "trunc":
            k = rnd.choice((1, 7, 100, 512, 1024))
            b = b[:-k] if k < len(b) else b
        elif kind == "dupblock":
            n = rnd.randrange(len(b) // tg.PHYS)
            b[n * tg.PHYS:n * tg.PHYS] = b[n * tg.PHYS:(n + 1) * tg.PHYS]
        else:
            n = rnd.randrange(len(b) // tg.PHYS)
            del b[n * tg.PHYS:(n + 1) * tg.PHYS]
        out.append(("fz%03d-%s-%s" % (i, name.replace("ok-", ""), kind), bytes(b), {}))
    return out


# ---------------------------------------------------------------------------------------------------------------------------
# The BASIC driver.

DRIVER = r"""* ZZTIDRV - drives !tapeimg over the images of a list and writes one dump per image (sandbox-tapeimg.py)
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
   kind = '' ; num = '' ; aux = '' ; id = '' ; rec = '' ; verdict = ''
   n.img = 0
   loop
      readseq line from lf else exit
      name = field(line, '|', 1)
      arg = field(line, '|', 2) : @fm : field(line, '|', 3) : @fm : field(line, '|', 4) : @fm : field(line, '|', 5)
      call !tapeimg('open', arg, kind, num, aux, id, rec, verdict)
      if verdict # '' then
         txt = 'V|' : verdict
      end else
         txt = 'H|' : id : '|' : aux : '|' : num : '|' : rec
         done = 0
         loop while not(done) do
            call !tapeimg('next', '', kind, num, aux, id, rec, verdict)
            begin case
               case verdict # ''
                  txt = 'V|' : verdict
                  done = 1
               case kind = 'E'
                  txt := nl : 'E'
                  done = 1
               case kind = 'D' or kind = 'I' or kind = 'O'
                  s = id
                  gosub hexify
                  hid = hx
                  s = rec
                  gosub hexify
                  txt := nl : kind : '|' : num : '|' : aux : '|' : hid : '|' : hx
               case 1
                  txt = 'V|NOKIND'
                  done = 1
            end case
         repeat
         call !tapeimg('close', '', kind, num, aux, id, rec, verdict)
      end
      write txt to outf, name
      n.img += 1
   repeat
   crt 'DRIVER DONE ' : n.img
   stop

hexify:
   hx = ''
   for j = 1 to len(s)
      v = seq(s[j, 1])
      hx := hexd[int(v / 16) + 1, 1] : hexd[mod(v, 16) + 1, 1]
   next j
   return
"""


def main():
    global passed, failed
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = [a for a in sys.argv[1:] if a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-tapeimg.py <dir> [--build] [--mutant=NAME] [--fuzz=N]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    n_fuzz = 450
    mutant = None
    for o in opts:
        if o.startswith("--fuzz="):
            n_fuzz = int(o.split("=", 1)[1])
        if o.startswith("--mutant="):
            mutant = o.split("=", 1)[1]
    for k, p in REAL.items():
        if not os.path.isfile(p) or os.path.getsize(p) == 0:
            bail("the reference image %s is missing" % p)
    say("sandbox-tapeimg: sandbox %s" % box)
    if "--build" in opts:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-tapeimg: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    # the reader of THIS tree, compiled into the sandbox's catalogue (a mutant changes the sandbox's copy only)
    src = open(TREE_SRC, encoding="utf-8").read()
    if mutant:
        old, new = MUTANTS[mutant]
        if src.count(old) != 1:
            bail("mutant %s: the old text occurs %d times" % (mutant, src.count(old)))
        src = src.replace(old, new)
        say("sandbox-tapeimg: MUTANT %s" % mutant)
    open(os.path.join(sysd, "gpl.bp", "tapeimg"), "w", encoding="utf-8").write(src)
    out = internal(box, "BASIC", "GPL.BP", "tapeimg")
    row("setup: !tapeimg compiled with no errors", re.search(r"(?m)^Compiled 1 program\(s\) with no errors", out) is not None, out[-300:])

    work = tempfile.mkdtemp(prefix="zzti")
    made = ["zztidrv"]
    try:
        os.mkdir(os.path.join(work, "in"))
        os.mkdir(os.path.join(work, "out"))
        cases = []     # (name, path, optstring, expected dump or None for 'V|code' given)
        # 1. the recipes
        for rname, (build, verdict, ropts) in sorted(tg.RECIPES.items()):
            cases.append(("rc-" + rname, build(), ropts))
        # 2. the two real images
        for k, p in sorted(REAL.items()):
            cases.append((k, open(p, "rb").read(), {}))
        # 3. the generated ones
        cases.extend(fuzz_images(n_fuzz))
        lines = []
        expect = {}
        for name, data, o in cases:
            path = os.path.join(work, "in", name + ".img")
            open(path, "wb").write(data)
            lines.append("%s|%s|%s|%s|%s" % (name, path, o.get("max_image", ""), o.get("max_item", ""), o.get("max_files", "")))
            expect[name] = dump_twin(data, o)
        # 4. what only the operating system can refuse
        good = os.path.join(work, "in", "rc-ok-small.img")
        unread = os.path.join(work, "in", "unreadable.img")
        open(unread, "wb").write(b"x")
        os.chmod(unread, 0)
        os_cases = [("os-nofile", os.path.join(work, "in", "no-such-file.img"), "V|R-OPEN"),
                    ("os-directory", os.path.join(work, "in"), "V|R-NOTFILE"),
                    ("os-unreadable", unread, "V|R-OPEN"),
                    ("os-relative", "in/rc-ok-small.img", "V|R-PATH"),
                    ("os-dotdot", os.path.join(work, "in", "..", "in", "rc-ok-small.img"), "V|R-PATH"),
                    ("os-slash-end", good + "/", "V|R-PATH"),
                    ("os-doubled-slash", os.path.join(work, "in") + "//rc-ok-small.img", "V|R-PATH"),
                    ("os-empty-path", "", "V|R-PATH")]
        for name, path, want in os_cases:
            lines.append("%s|%s|||" % (name, path))
            expect[name] = want
        listf = os.path.join(work, "list.txt")
        open(listf, "w").write("\n".join(lines) + "\n")

        prog = DRIVER % {"list": listf}
        open(os.path.join(sysd, "bp", "zztidrv"), "w").write(prog)
        outdir = os.path.join(sysd, "zzticout")      # a directory file of the SDSYS account: each record is an OS file
        sess(box, "DELETE.FILE zzticout", "CREATE.FILE zzticout DIRECTORY")
        out = sess(box, "BASIC bp zztidrv")
        row("setup: the driver compiled with no errors", re.search(r"(?m)^Compiled 1 program\(s\) with no errors", out) is not None, out[-300:])
        t_cases = len(lines)
        say("sandbox-tapeimg: %d images (%d recipes, 2 real, %d generated, %d operating system cases)" % (t_cases, len(tg.RECIPES), n_fuzz, len(os_cases)))
        out = sess(box, "RUN bp zztidrv")
        if "DRIVER STARTED" not in out:
            bail("the driver never started:\n" + out[-600:])
        m = re.search(r"DRIVER DONE (\d+)", out)
        row("the driver reached its end and read every image of the list", m is not None and int(m.group(1)) == t_cases,
            "done=%s of %d; tail: %s" % (m.group(1) if m else None, t_cases, out[-300:].replace("\n", " | ")))
        row("the driver found its output file", "NOOUT" not in out and os.path.isdir(outdir))

        say("\n--- every image: the BASIC dump equals the twin's ----------------------------------------------")
        bad = []
        groups = {"rc": [0, 0], "real": [0, 0], "fz": [0, 0], "os": [0, 0]}
        verdicts = {}
        for name in expect:
            g = "rc" if name.startswith("rc-") else "real" if name.startswith("real") else "fz" if name.startswith("fz") else "os"
            fp = os.path.join(outdir, name)
            got = open(fp, "rb").read().decode("latin-1").rstrip("\n") if os.path.isfile(fp) else None
            ok = got is not None and got != "" and got == expect[name]
            groups[g][0 if ok else 1] += 1
            verdicts[expect[name].split("\n")[0] if expect[name].startswith("V|") else "parses"] = verdicts.get(
                expect[name].split("\n")[0] if expect[name].startswith("V|") else "parses", 0) + 1
            if not ok:
                bad.append((name, got, expect[name]))
        for g, label in (("rc", "the recipes"), ("real", "the two real images"), ("fz", "the generated images"), ("os", "the operating system cases")):
            ok_n, bad_n = groups[g]
            row("%s: %d of %d equal" % (label, ok_n, ok_n + bad_n), bad_n == 0)
        for name, got, want in bad[:12]:
            say("    MISMATCH %s" % name)
            say("      basic: %s" % (("%s ... (%d bytes)" % (got[:150], len(got))) if got is not None else "NO FILE"))
            say("      twin : %s ... (%d bytes)" % (want[:150], len(want)))
        say("    twin verdicts over all images: " + ", ".join("%s %d" % kv for kv in sorted(verdicts.items())))
        row("the generated images are not all alike (at least 8 different outcomes among all)", len(verdicts) >= 8, str(sorted(verdicts)))
        row("the parsing outcome is not rare: at least 20 images parse", verdicts.get("parses", 0) >= 20, str(verdicts.get("parses")))
    finally:
        for n in made:
            for d in ("bp", "bp.out"):
                p = os.path.join(sysd, d, n)
                if os.path.exists(p):
                    os.remove(p)
        shutil.rmtree(work, ignore_errors=True)
        sess(box, "DELETE.FILE zzticout")
        if mutant:
            open(os.path.join(sysd, "gpl.bp", "tapeimg"), "w", encoding="utf-8").write(open(TREE_SRC, encoding="utf-8").read())
            internal(box, "BASIC", "GPL.BP", "tapeimg")

    say("\nsandbox-tapeimg: %d passed, %d failed" % (passed, failed))
    sys.exit(0 if failed == 0 else 1)


# (name, old text, new text) - mutants of gpl.bp/tapeimg, each applied to the sandbox's copy only
MUTANTS = {
    "trailing-fm": ("   if body[len(body), 1] = fm then body = body[1, len(body) - 1]\n", "   null\n"),
    "bin-length": ("   if o.len < 1 or o.len > o.blocks * TI.BIN or (o.blocks > 1 and o.len <= (o.blocks - 1) * TI.BIN) then\n", "   if o.len < 1 then\n"),
    "bin-padding": ("   if convert(nul, '', raw[o.len + 1, 999999999]) # '' then\n", "   if 0 then\n"),
    "level-as-number": ("   if lv # '#1' and lv # '#2' and lv # '#3' then\n", "   if level + 0 < 1 or level + 0 > 3 then\n"),
    "item-cap": ("   if len(tok) > ti.maxitem then\n", "   if 0 then\n"),
    "pad-scan": ("         if not(pad.ok) then pad.bad = j\n", "         if 0 then pad.bad = j\n"),
    "accounts-as-numbers": ("   if ('#' : l.second) # ('#' : l.acct) or ('#' : lab2.acct) # ('#' : lab.acct) or ('#' : l.acct) # ('#' : lab.acct) then\n",
                            "   if l.second # l.acct or lab2.acct # lab.acct or l.acct # lab.acct then\n"),
    "file-key-by-prefix": ("   if not(index(ti.files, ',' : fnum : ',', 1)) then\n      verdict = 'R-NOFILE'\n",
                           "   if not(index(ti.files, fnum, 1)) then\n      verdict = 'R-NOFILE'\n"),
    "trailer-by-search": ("   t1 = d1 + o.blocks * TI.BIN             ;* where the trailer must begin\n",
                          "   t1 = index(ti.buf, im : im : im : 'X', 1)\n"),
}


if __name__ == "__main__":
    main()
