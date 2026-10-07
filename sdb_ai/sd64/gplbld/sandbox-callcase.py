#!/usr/bin/env python3
#
# sandbox-callcase.py - program and catalogue names are LOWER case: what SD produces, read back
# case-sensitively.  RELEASE_1.1 5 stage 3a (PAL-1), the Linux form of the Windows port's
# verify-callcase.ps1.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-callcase.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (a private SD built from a tree, no sudo, its own IPC
# keys: never the live system).  With --build the sandbox is built first from THIS tree; <dir> must
# then be empty or absent.  Without it <dir> must already be built, which is how the same script is
# run against an OLD build to prove it can fail.  Fixture names are unique to the run.
#
# Exit 0 every row passed, 1 a row failed, 2 it could not run (setup is not what the rows assume).
#
# WHY IT READS NAMES AND DOES NOT ONLY CHECK THAT THINGS RUN.  A call to a catalogued program that
# used the wrong case would have to fail on ext4, so a missed C site is loud here, where on NTFS it
# was silent.  That is no reason to measure only behaviour: a stored name in the wrong case
# is still a defect, and every DECISIVE row reads a stored or printed NAME case-sensitively:
#   A. the gcat directory listing           - no entry with an upper-case letter (README is a text file)
#   B. the bin/pcode library's header names - every item lower
#   C. the runtime's own error text         - "Unable to load '!zznosuchsub3a'"
#   D. CATALOG into the private catalogue   - 3031 names zzcc3ap; cat/ holds that exact name
#   E. CATALOG LOCAL                        - 3029 names zzcl3a; the VOC id is stored lower
#   F. the local entry, called typed upper  - and a second CATALOG LOCAL leaves ONE entry
#   G. DELETE.CATALOG                       - 3042 / 3040 name the lower id; nothing stored remains
#   H. LINUX ONLY, until D2 makes VOC case blind: an entry catalogued BEFORE stage 3a is stored under
#      the upper-case VOC id.  H1 re-catalogues over it - one entry, lower, the old one gone.
#      H2 DELETE.CATALOG of a name that exists only as the upper-case id removes it.  Windows retired
#      its plant when D2 made the second spelling unreachable; here it is still reachable, and
#      the hunks that handle it (catalog's old.local.id, delcat's local.id) are otherwise unwitnessed.
#
# THE INSTRUMENT.  It prints the commands it sent and what came back.  A stored id is read from
# LIST VOC's ROWS: CATALOG's 3029 and DELETE.CATALOG's 3040 also begin "<id> added ..." and
# "<id> deleted ...", which an "any line that starts with the id" match would count (the Windows red
# run reported "stored: ZZCL3A ZZCL3A" that way).  A row is the id followed by two or more spaces, or
# by the end of the line; a message has one space.  The matcher is driven on both shapes first.

import os
import re
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
passed = failed = 0
PROGS = ["zzcc3ap", "zzrn3a", "zzlc3a"]
# A selection on Linux is case sensitive (measured 7 Oct 2026: LIKE "zzcl..." printed 0 records over an id
# stored ZZCL3A), so it names both spellings, or an upper-case twin would be invisible to every row.
LISTV = 'LIST VOC WITH @ID LIKE "zzcl..." OR WITH @ID LIKE "ZZCL..."'


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
    say("sandbox-callcase: CANNOT RUN - " + msg)
    sys.exit(2)


def sess(box, *cmds):
    say("    > " + " | ".join(cmds))
    p = subprocess.run([sys.executable, TOOL, box, "sess", os.path.join(box, "user_accounts")] + list(cmds),
                       capture_output=True, text=True, timeout=600)
    out = ANSI.sub("", p.stdout + p.stderr)
    out = out.split(":TERM 200,9999", 1)[-1]
    for line in out.splitlines():
        if line.strip() and not line.startswith(":") and not line.startswith("exit "):
            say("      | " + line.rstrip()[:110])
    return out


def stored_ids(text, name):
    """The VOC ids printed by a LIST row for <name>, in the case SD stored them."""
    return re.findall(r"(?im)^(" + re.escape(name) + r")(?:[ \t]{2,}|[ \t]*$)", text)


def write(path, lines):
    with open(path, "wb") as f:
        f.write(("\n".join(lines) + "\n").encode("ascii"))


def pcode_names(path):
    """OBJECT_HEADER (gplsrc/header.h): object_size int32 at 24, program_name at 36; items padded to 4."""
    b = open(path, "rb").read()
    i, names = 0, []
    while i < len(b):
        if b[i] != 0x64:
            names.append("<bad magic at %d>" % i)
            break
        size = struct.unpack_from("<i", b, i + 24)[0]
        e = i + 36
        while e < len(b) and b[e] != 0:
            e += 1
        names.append(b[i + 36:e].decode("ascii", "replace"))
        if size <= 0:
            break
        i += (size + 3) & ~3
    return names


def sweep(box):
    sysd = os.path.join(box, "sys")
    for d in ("bp", "bp.out", "cat"):
        dd = os.path.join(sysd, d)
        if os.path.isdir(dd):
            for n in os.listdir(dd):
                if re.fullmatch(r"(?i)zz(cc3ap|rn3a|lc3a|cl3a|pl3a)", n):
                    os.remove(os.path.join(dd, n))
                    say("    swept %s/%s" % (d, n))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-callcase.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-callcase: sandbox  %s" % box)
    say("sandbox-callcase: tree     %s" % os.path.dirname(HERE))
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-callcase: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, timeout=120)
    say("\n--- sweep leftovers --------------------------------------------------------")
    sweep(box)
    sess(box, "DELETE.CATALOG zzcc3ap", "DELETE.CATALOG zzcl3a LOCAL", "DELETE.CATALOG ZZCL3A LOCAL")

    try:
        # --- A. the global catalogue ---------------------------------------------
        say("\n--- A. gcat listing ---------------------------------------------------------")
        gcat = sorted(os.listdir(os.path.join(sysd, "gcat")))
        upper = [n for n in gcat if re.search("[A-Z]", n) and n != "README"]
        say("  entries: %d; with an upper-case letter (README apart): %d" % (len(gcat), len(upper)))
        if upper:
            say("  first upper-case entries: " + " ".join(upper[:10]))
        row("CONTROL A: gcat holds a full catalogue (100 or more entries)", len(gcat) >= 100, "entries: %d" % len(gcat))
        cp = os.path.join(sysd, "gcat", "$cproc")
        row("A: gcat holds $cproc under that exact name, non-empty", "$cproc" in gcat and os.path.getsize(cp) > 0,
            "no entry named exactly $cproc")
        row("A: gcat holds $apisrvr and $bbproc under those exact names", "$apisrvr" in gcat and "$bbproc" in gcat)
        row("A: no gcat entry name carries an upper-case letter", bool(gcat) and not upper, " ".join(upper[:10]))

        # --- B. the pcode library ----------------------------------------------
        say("\n--- B. bin/pcode header names -------------------------------------------------")
        pn = pcode_names(os.path.join(sysd, "bin", "pcode"))
        pup = [n for n in pn if re.search("[A-Z<]", n)]
        say("  items: %d; names: %s" % (len(pn), " ".join(pn)))
        row("CONTROL B: the pcode library parsed into 50 or more items", len(pn) >= 50, "items: %d" % len(pn))
        row("B: 'ak' and 'voc_cat' are there under exactly those names", pn.count("ak") == 1 and pn.count("voc_cat") == 1)
        row("B: no pcode header name carries an upper-case letter", bool(pn) and not pup, " ".join(pup))

        # --- the stored-id matcher on known text ---------------------------------------
        say("\n--- the stored-id matcher, on known text -------------------------------------")
        probe = ("zzcl3a added to local catalogue\nZZCL3A deleted from the local catalogue\n"
                 ':LIST VOC WITH @ID = "zzcl3a"\nZZCL3A               \nzzcl3a')
        hit = stored_ids(probe, "zzcl3a")
        say("  matched: " + " ".join(hit))
        row("CONTROL: the matcher takes LIST rows and ignores 3029/3040 message lines",
            hit == ["ZZCL3A", "zzcl3a"], " ".join(hit))

        # --- fixtures -------------------------------------------------------------------
        say("\n--- fixtures -----------------------------------------------------------------")
        bp = os.path.join(sysd, "bp")
        write(os.path.join(bp, "zzcc3ap"), ["subroutine zzcc3ap(r)", "   r = 'ok3a'", "   return", "end"])
        write(os.path.join(bp, "zzrn3a"), [
            "   x = '!USERNAME'", "   r = ''", "   call @x(r, @userno)", "   crt 'CTL3A [':r:']'",
            "   y = 'ZZCC3AP'", "   s = ''", "   call @y(s)", "   crt 'PRIV3A [':s:']'",
            "   n = '!zzNoSuchSub3a'", "   call @n(t, @userno)", "   crt 'NOT REACHED3A'", "end"])
        write(os.path.join(bp, "zzlc3a"), ["   y = 'ZZCL3A'", "   s = ''", "   call @y(s)", "   crt 'LOCAL3A [':s:']'", "end"])
        out = sess(box, *["BASIC bp " + p for p in PROGS])
        clean = len(re.findall(r"(?m)^Compiled 1 program\(s\) with no errors", out))
        row("setup: all %d fixture programs compiled with no errors" % len(PROGS), clean == len(PROGS),
            "clean compiles: %d of %d" % (clean, len(PROGS)))
        if clean != len(PROGS):
            bail("the fixtures did not compile - nothing below would measure the names")

        # --- C, D. the private catalogue, and the runtime's own spelling ----------------------
        say("\n--- C, D. CATALOG into the private catalogue; the runtime's error text ----------")
        out = sess(box, "CATALOG bp ZZCC3AP", "RUN bp zzrn3a")
        cats = sorted(os.listdir(os.path.join(sysd, "cat")))
        say("  cat/ holds: " + " ".join(cats))
        row("D: CATALOG said 'zzcc3ap added to private catalogue' (3031, lower case)",
            re.search(r"(?m)^zzcc3ap added to private catalogue", out) is not None, "no 3031 line naming zzcc3ap in lower case")
        row("D: the private catalogue file is named exactly 'zzcc3ap', and there is only one",
            cats.count("zzcc3ap") == 1 and [c for c in cats if c.lower() == "zzcc3ap"] == ["zzcc3ap"], " ".join(cats))
        row("CONTROL C: !USERNAME (typed upper) still answers", re.search(r"(?m)^CTL3A \[\S+\]", out) is not None,
            "no CTL3A line with a value")
        row("D: the private entry answers a call typed ZZCC3AP", re.search(r"(?m)^PRIV3A \[ok3a\]", out) is not None,
            "no PRIV3A [ok3a] line")
        row("C: the runtime names a missing call '!zznosuchsub3a' - lower case",
            "Unable to load '!zznosuchsub3a'" in out, "no load error naming '!zznosuchsub3a' in lower case")

        # --- E, F. local catalogue -----------------------------------------------------------
        say("\n--- E, F. CATALOG LOCAL, a call typed upper, and a second CATALOG LOCAL -----------")
        out = sess(box, "CATALOG bp zzcl3a zzcc3ap LOCAL", LISTV)
        row("E: CATALOG said 'zzcl3a added to local catalogue' (3029, lower case)",
            re.search(r"(?m)^zzcl3a added to local catalogue", out) is not None, "no 3029 line naming zzcl3a in lower case")
        ids = stored_ids(out, "zzcl3a")
        row("E: the VOC stores 'zzcl3a' and no other spelling", ids == ["zzcl3a"], "stored: " + " ".join(ids))
        out = sess(box, "RUN bp zzlc3a")
        row("F: a call typed ZZCL3A finds the local entry", re.search(r"(?m)^LOCAL3A \[ok3a\]", out) is not None,
            "no LOCAL3A [ok3a] line")
        out = sess(box, "CATALOG bp zzcl3a zzcc3ap LOCAL", LISTV)
        ids = stored_ids(out, "zzcl3a")
        row("F: re-cataloguing left exactly one entry, stored 'zzcl3a'", ids == ["zzcl3a"], "stored: " + " ".join(ids))

        # --- H1. an entry catalogued before stage 3a -----------------------------------------
        say("\n--- H1. an entry catalogued before stage 3a (upper-case VOC id) --------------------")
        # zzpl3a.. plants the OLD shape: the local entry stored under the UPPER-case id, as a pre-3a
        # CATALOG LOCAL wrote it.  The program is the lower-case one's twin: it reads the record E made,
        # writes it under ZZCL3A and deletes zzcl3a.
        write(os.path.join(bp, "zzpl3a"), [
            "   open 'VOC' to v else crt 'PLANT3A no voc' ; stop",
            "   read r from v, 'zzcl3a' else crt 'PLANT3A no zzcl3a' ; stop",
            "   write r on v, 'ZZCL3A'", "   delete v, 'zzcl3a'", "   crt 'PLANT3A done [':r<2>:']'", "end"])
        out = sess(box, "BASIC bp zzpl3a", "RUN bp zzpl3a", LISTV)
        ids = stored_ids(out, "zzcl3a")
        row("H1 setup: the plant ran and the VOC now stores ONLY 'ZZCL3A' (a pre-3a entry)",
            re.search(r"(?m)^PLANT3A done \[CS\]", out) is not None and ids == ["ZZCL3A"], "stored: " + " ".join(ids))
        if ids != ["ZZCL3A"]:
            bail("the plant did not make an old-style entry - nothing below would measure it")
        out = sess(box, "CATALOG bp zzcl3a zzcc3ap LOCAL", LISTV)
        ids = stored_ids(out, "zzcl3a")
        row("H1: CATALOG LOCAL over it leaves ONE entry, stored 'zzcl3a' (renamed, not twinned)",
            ids == ["zzcl3a"], "stored: " + " ".join(ids))
        out = sess(box, "RUN bp zzlc3a")
        row("H1: the renamed entry answers a call typed ZZCL3A", re.search(r"(?m)^LOCAL3A \[ok3a\]", out) is not None,
            "no LOCAL3A [ok3a] line")

        # --- H2. DELETE.CATALOG of an entry that exists only under the upper-case id -----------
        say("\n--- H2. DELETE.CATALOG of an old entry that exists only under the upper-case id ---")
        out = sess(box, "RUN bp zzpl3a", LISTV)
        ids = stored_ids(out, "zzcl3a")
        row("H2 setup: the VOC stores ONLY 'ZZCL3A' again", ids == ["ZZCL3A"], "stored: " + " ".join(ids))
        if ids != ["ZZCL3A"]:
            bail("the plant did not make an old-style entry - H2 would measure nothing")
        out = sess(box, "DELETE.CATALOG zzcl3a LOCAL", LISTV)
        ids = stored_ids(out, "zzcl3a")
        row("H2: DELETE.CATALOG zzcl3a LOCAL removed the upper-case entry", ids == [], "stored: " + " ".join(ids))
        row("H2: the refusal wording 3041 ('is not in the local catalogue') did not appear",
            "is not in the local catalogue" not in out, "DELETE.CATALOG could not find the old entry")

        # --- G. DELETE.CATALOG, both catalogues ------------------------------------------------
        say("\n--- G. DELETE.CATALOG, typed upper -----------------------------------------------")
        sess(box, "CATALOG bp zzcl3a zzcc3ap LOCAL")
        out = sess(box, "DELETE.CATALOG ZZCC3AP", "DELETE.CATALOG ZZCL3A LOCAL", LISTV)
        row("G: 3042 names 'zzcc3ap' deleted from the private catalogue",
            re.search(r"(?m)^zzcc3ap deleted from the private catalogue", out) is not None, "no 3042 line naming zzcc3ap")
        row("G: 3040 names 'zzcl3a' deleted from the local catalogue, typed ZZCL3A",
            re.search(r"(?m)^zzcl3a deleted from the local catalogue", out) is not None, "no 3040 line naming zzcl3a")
        row("G: no zzcl3a entry is stored in any case", stored_ids(out, "zzcl3a") == [], "a VOC entry remains")
        row("G: cat/ no longer holds zzcc3ap in any case",
            not [c for c in os.listdir(os.path.join(sysd, "cat")) if c.lower() == "zzcc3ap"], "the private catalogue file remains")
    finally:
        say("\n--- cleanup ------------------------------------------------------------------")
        sess(box, "DELETE.CATALOG zzcc3ap", "DELETE.CATALOG zzcl3a LOCAL")
        sweep(box)
        left = [n for d in ("bp", "bp.out", "cat") for n in os.listdir(os.path.join(sysd, d))
                if re.fullmatch(r"(?i)zz(cc3ap|rn3a|lc3a|cl3a|pl3a)", n)]
        row("cleanup: no fixture file is left in bp, bp.out or cat", not left, " ".join(left))

    say("\nsandbox-callcase: %d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        bail("no row ran - a broken test, not a pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
