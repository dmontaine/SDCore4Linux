#!/usr/bin/env python3
"""test-nomasters-units.py - S.67's master-file copies are retired (S.96 M6, 2 Nov 2026; the owner: "retire"), and stay retired.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-nomasters-units.py
  python3 .../test-nomasters-units.py --selftest

No sudo, no install, no sd.  Exit 0 every check passed, 1 a check failed, 2 it could not run.

WHAT IT HOLDS.  tool.entries edits every account's own VOC entries, dictionary items and programs in place, so the copies (voc_master, dict_master,
master_state, the journal $master.journal), the kernel's file-change hook (masters.c, K_MASTERS 150), the verbs sync.masters, check.masters and
list.master.pending and the page tool.masters were taken out.  This check says that nothing SHIPPED brings any of it back:

  N1  no CODE of the kernel (gplsrc/*.c, *.h), of SD BASIC (sdsys/gpl.bp, sdsys/syscom), of the installer, the remover or the root helper names the machinery -
      comments are taken out first: the history lines that say what was retired are allowed, a call is not
  N2  no shipped TEXT names it: the VOC records of voc_template and newvoc (names and contents), the messages, the help records
  N3  the files are gone: gplsrc/masters.c, gpl.bp masters, masters_setup, upgrade_masters, tool_masters, the help record tool.masters.page; gpl.src does not build it
  N4  each of the four verbs has its record in sdsys/voc_removed (the VOC deletion list, S.87: type V, CA, the program it ran), so every account's
      update takes it out of an old VOC; none is shipped any more
  N5  kernel key 150 is not reused: neither keys.h nor int$keys.h defines a key with that number, and both say it was K_MASTERS / K$MASTERS
  N6  the installer's RETIREDMASTERS block removes the seven names (the three files, their dictionaries, the journal) from the SDSYS directory by their
      exact names (rm -rf -- of one name, so a link is removed as a link), is there once, comes before the register is handed to sdsys, and the installer
      no longer runs upgrade_masters (test-install-retiredmasters.sh RUNS the block on scratch files)
  N7  the root helper's scheduled jobs no longer own check-masters or sync-masters
  N0  THE NULL CASE: the scan read the kernel, the BASIC programs, the VOC sources, the messages and the scripts (a check that read nothing must not pass)

The exceptions are the voc_removed records and sdsys/changelog, which name what was removed on purpose, and the RETIREDMASTERS block of the installer.
--selftest plants each kind of reference in turn (and two controls that must stay green: the same words in a comment) and requires a check to notice.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.abspath(os.path.join(HERE, os.pardir))
ROOT = os.path.dirname(os.path.dirname(SD64))
SDSYS = os.path.join(SD64, "sdsys")
GPLSRC = os.path.join(SD64, "gplsrc")

PAT = re.compile(r"K\$MASTERS|K_MASTERS|\bmasters_|voc_master|dict_master|master_state|master\.journal|sync\.masters|check\.masters|list\.master\.pending|"
                 r"tool\.masters|tool_masters|upgrade_masters|DHF_MST_|DHE_MASTER_REFUSED|\$masters\b|!masters\b", re.I)
VERBS = {"sync.masters": "$masters", "check.masters": "$masters", "list.master.pending": "$masters", "tool.masters": "$tool_masters"}
GONE = ["gplsrc/masters.c", "sdsys/gpl.bp/masters", "sdsys/gpl.bp/masters_setup", "sdsys/gpl.bp/upgrade_masters", "sdsys/gpl.bp/tool_masters",
        "sdsys/helptext/tool.masters.page"]
SEVEN = ["voc_master", "voc_master.dic", "dict_master", "dict_master.dic", "master_state", "master_state.dic", "'$master.journal'"]


def slurp(p):
    with open(p, encoding="latin-1") as f:
        return f.read()


def strip_c(src):
    src = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), src, flags=re.S)
    return re.sub(r"//[^\n]*", "", src)


def strip_bas(src):
    out = []
    for line in src.split("\n"):
        s = line.lstrip()
        if s.startswith("*") or s.startswith("!") or s.upper().startswith("REM "):
            out.append("")
            continue
        cut = line.find(";*")
        out.append(line if cut < 0 else line[:cut])
    return "\n".join(out)


def strip_sh(src):
    return "\n".join("" if l.lstrip().startswith("#") else l for l in src.split("\n"))


def load():
    t = {"code": {}, "text": {}, "names": set(), "voc_removed": {}, "raw": {}}
    for fn in sorted(os.listdir(GPLSRC)):
        if fn.endswith((".c", ".h")):
            t["code"]["gplsrc/" + fn] = ("c", slurp(os.path.join(GPLSRC, fn)))
    for d in ("gpl.bp", "syscom"):
        for fn in sorted(os.listdir(os.path.join(SDSYS, d))):
            p = os.path.join(SDSYS, d, fn)
            if os.path.isfile(p):
                t["code"]["sdsys/%s/%s" % (d, fn)] = ("bas", slurp(p))
    for rel, p in (("installsdcore.sh", os.path.join(ROOT, "installsdcore.sh")), ("deletesdcore.sh", os.path.join(ROOT, "deletesdcore.sh")),
                   ("gplbld/sd-elevate", os.path.join(HERE, "sd-elevate"))):
        t["code"][rel] = ("sh", slurp(p))
    for d in ("voc_template", "newvoc", "messages", "helptext"):
        for fn in sorted(os.listdir(os.path.join(SDSYS, d))):
            p = os.path.join(SDSYS, d, fn)
            t["names"].add("sdsys/%s/%s" % (d, fn))
            if os.path.isfile(p):
                t["text"]["sdsys/%s/%s" % (d, fn)] = slurp(p)
    for fn in sorted(os.listdir(os.path.join(SDSYS, "voc_removed"))):
        t["voc_removed"][fn] = slurp(os.path.join(SDSYS, "voc_removed", fn))
    for g in GONE:
        if os.path.exists(os.path.join(SD64, g)):
            t["names"].add(g)
    t["raw"]["gpl.src"] = slurp(os.path.join(SD64, "gpl.src"))
    t["raw"]["keys.h"] = slurp(os.path.join(GPLSRC, "keys.h"))
    t["raw"]["int$keys.h"] = slurp(os.path.join(SDSYS, "gpl.bp", "int$keys.h"))
    return t


def installer_block(text):
    a = text.find("# RETIREDMASTERS-BEGIN\n")
    b = text.find("# RETIREDMASTERS-END\n")
    return (text[a:b], text[:a] + text[b:]) if 0 <= a < b else ("", text)


def checks(t):
    rows = []

    def ck(i, ok, detail=""):
        rows.append((i, bool(ok), detail))

    counts = {"c": 0, "bas": 0, "sh": 0}
    hits = []
    ins_block = ""
    for rel, (kind, src) in sorted(t["code"].items()):
        counts[kind] += 1
        if rel == "installsdcore.sh":
            ins_block, src = installer_block(src)
        code = strip_c(src) if kind == "c" else strip_bas(src) if kind == "bas" else strip_sh(src)
        for n, line in enumerate(code.split("\n"), 1):
            if PAT.search(line):
                hits.append("%s:%d: %s" % (rel, n, line.strip()[:80]))
    ck("N0 the scan read the kernel (%d C files), the BASIC programs and headers (%d), the three scripts (%d), the VOC sources, messages and help (%d texts)"
       % (counts["c"], counts["bas"], counts["sh"], len(t["text"])),
       counts["c"] > 100 and counts["bas"] > 300 and counts["sh"] == 3 and len(t["text"]) > 1000, repr(counts))
    ck("N1 no code of the kernel, of SD BASIC, of the installer, the remover or the root helper names the master-file machinery (comments aside)", not hits, repr(hits[:8]))
    thits = sorted(rel for rel, src in t["text"].items() if PAT.search(src) or PAT.search(rel))
    nhits = sorted(n for n in t["names"] if PAT.search(os.path.basename(n)) and n.split("/")[1] in ("voc_template", "newvoc", "messages", "helptext"))
    ck("N2 no shipped VOC record, message or help record names it, by its name or in its text", not thits and not nhits, repr((thits + nhits)[:8]))
    still = [g for g in GONE if g in t["names"]]
    ck("N3 the files are gone (masters.c, masters, masters_setup, upgrade_masters, tool_masters, tool.masters.page) and gpl.src does not build masters",
       not still and re.search(r"^masters$", t["raw"]["gpl.src"], re.M) is None, repr(still))
    bad = []
    for v, prog in VERBS.items():
        rec = t["voc_removed"].get(v)
        f = rec.split("\n") if rec else []
        if not (len(f) >= 5 and f[0] == "V" and f[1] == "CA" and f[2] == prog and "tool.entries" in f[4]):
            bad.append(v)
        if ("sdsys/voc_template/" + v) in t["names"] or ("sdsys/newvoc/" + v) in t["names"]:
            bad.append(v + " (still shipped)")
    ck("N4 each of the four verbs has its voc_removed record (V, CA, the program it ran, and tool.entries to use instead) and is shipped by neither VOC source", not bad, repr(bad))
    k150 = re.findall(r"^#define\s+(K_\w+)\s+150\b", t["raw"]["keys.h"], re.M) + re.findall(r"^\s*\$define\s+(K\$[\w.]+)\s+150\b", t["raw"]["int$keys.h"], re.M)
    ck("N5 kernel key 150 is not reused (no key of keys.h or int$keys.h has it) and both headers say it was K_MASTERS / K$MASTERS",
       not k150 and "150 was K_MASTERS" in t["raw"]["keys.h"] and "150 was K$MASTERS" in t["raw"]["int$keys.h"], repr(k150))
    ins = t["code"]["installsdcore.sh"][1]
    loop = re.search(r"^for retired_masters_name in (.*); do$", ins_block, re.M)
    words = loop.group(1).split() if loop else []
    ck("N6 the installer's RETIREDMASTERS block removes exactly the seven names from the SDSYS directory, one exact name at a time with rm -rf -- (a link is removed as a link), is there once, comes "
       "before the register is handed to sdsys, and nothing runs upgrade_masters",
       ins.count("# RETIREDMASTERS-BEGIN\n") == 1 and sorted(words) == sorted(SEVEN) and 'retired_masters_dir="$sdsysdir"' in ins_block
       and 'sudo rm -rf -- "$retired_masters_dir/$retired_masters_name"; then' in ins_block and ins_block.count("rm ") == 1
       and 0 <= ins.find("# RETIREDMASTERS-BEGIN") < ins.find('sudo chown -R sdsys:sdusers "$sdsysdir/accounts"')
       and "upgrade_masters" not in strip_sh(installer_block(ins)[1]), repr(words))
    se = strip_sh(t["code"]["gplbld/sd-elevate"][1])
    ck("N7 the root helper's job ids no longer include check-masters or sync-masters", re.search(r"^\s*(check|sync)-masters\)", se, re.M) is None
       and "backup-all)" in se and "update-accounts)" in se)
    return rows


def plant_code(rel, add):
    def f(t):
        t2 = dict(t, code=dict(t["code"]))
        kind, src = t2["code"][rel]
        t2["code"][rel] = (kind, src + add)
        return t2
    return f


def plant_text(rel, text):
    def f(t):
        t2 = dict(t, text=dict(t["text"]), names=set(t["names"]))
        t2["text"][rel] = text
        t2["names"].add(rel)
        return t2
    return f


def sub_code(rel, a, b):
    def f(t):
        t2 = dict(t, code=dict(t["code"]))
        kind, src = t2["code"][rel]
        if src.count(a) != 1:
            raise KeyError("%s: %r is not there once" % (rel, a[:60]))
        t2["code"][rel] = (kind, src.replace(a, b))
        return t2
    return f


def sub_raw(key, a, b):
    def f(t):
        t2 = dict(t, raw=dict(t["raw"]))
        if t2["raw"][key].count(a) != 1:
            raise KeyError("%s: %r is not there once" % (key, a[:60]))
        t2["raw"][key] = t2["raw"][key].replace(a, b)
        return t2
    return f


def drop_removed(v):
    def f(t):
        t2 = dict(t, voc_removed=dict(t["voc_removed"]))
        del t2["voc_removed"][v]
        return t2
    return f


def add_name(n):
    def f(t):
        return dict(t, names=set(t["names"]) | {n})
    return f


MUTANTS = [
    ("a kernel file calls the hook again", plant_code("gplsrc/dh_write.c", "\nstatic void probe(void) { masters_note_record(0, 'w', \"\", 0); }\n")),
    ("op_kernel answers K_MASTERS again", plant_code("gplsrc/op_kernel.c", "\n#define K_MASTERS 150\n")),
    ("a BASIC program asks the kernel for the master files", plant_code("sdsys/gpl.bp/delacc", "\n   void kernel(K$MASTERS, 'drop' : @fm : x)\n")),
    ("a program opens voc_master", plant_code("sdsys/gpl.bp/tool_entries", "\n   openpath @sdsys:@ds:'VOC_MASTER' to f else null\n")),
    ("a program runs sync.masters", plant_code("sdsys/gpl.bp/create_account", "\n   execute 'sync.masters'\n")),
    ("a program calls !masters_setup", plant_code("sdsys/gpl.bp/restorea", "\n   call !masters_setup(rep)\n")),
    ("the installer runs upgrade_masters outside the block", plant_code("installsdcore.sh", '\nsudo "$sdsysdir/bin/sd" -internal RUN gpl.bp upgrade_masters\n')),
    ("the remover saves master_state", plant_code("deletesdcore.sh", '\nsudo cp -a "$sdsysdir/master_state" "$acct_path/"\n')),
    ("a VOC record of voc_template runs the old program", plant_text("sdsys/voc_template/sync.masters", "V\nCA\n$masters\n")),
    ("newvoc ships tool.masters", plant_text("sdsys/newvoc/zz.page", "V\nCA\n$tool_masters\n")),
    ("a message tells the reader to run check.masters", plant_text("sdsys/messages/11998", "Run check.masters to see the differences\n")),
    ("a help record names the journal", plant_text("sdsys/helptext/zz.page", "The $master.journal holds what changed\n")),
    ("masters.c is back", add_name("gplsrc/masters.c")),
    ("tool_masters is back", add_name("sdsys/gpl.bp/tool_masters")),
    ("gpl.src builds masters again", sub_raw("gpl.src", "lnxport\n", "lnxport\nmasters\n")),
    ("a verb's removal record is lost", drop_removed("check.masters")),
    ("a removal record names another program", lambda t: dict(t, voc_removed=dict(t["voc_removed"], **{"tool.masters": "V\nCA\n$tool_entries\n1.2-0\ntool.entries\n"}))),
    ("key 150 is given to a new key", sub_raw("keys.h", "/* 150 was K_MASTERS", "#define K_NEWTHING           150\n/* 150 was K_MASTERS")),
    ("key 150 is given to a new BASIC key", sub_raw("int$keys.h", "      * 150 was K$MASTERS", "      $define K$NEWTHING        150\n      * 150 was K$MASTERS")),
    ("the installer forgets the journal", sub_code("installsdcore.sh", " master_state.dic '$master.journal'; do", " master_state.dic; do")),
    ("the installer removes by a wider pattern", sub_code("installsdcore.sh", 'sudo rm -rf -- "$retired_masters_dir/$retired_masters_name"; then', 'sudo rm -rf -- "$retired_masters_dir/$retired_masters_name"*; then')),
    ("the block moves after the register is handed to sdsys", lambda t: sub_code("installsdcore.sh", "# RETIREDMASTERS-BEGIN\n", 'sudo chown -R sdsys:sdusers "$sdsysdir/accounts"\n# RETIREDMASTERS-BEGIN\n')(
        sub_code("installsdcore.sh", 'sudo chown -R sdsys:sdusers "$sdsysdir/accounts"\n', "")(t))),
    ("the helper owns sync-masters again", sub_code("gplbld/sd-elevate", "    update-accounts) JB_SENTENCE='update.accounts all' ;;",
                                                    "    update-accounts) JB_SENTENCE='update.accounts all' ;;\n    sync-masters)    JB_SENTENCE='sync.masters' ;;")),
    ("the scan reads no BASIC (the null case)", lambda t: dict(t, code={k: v for k, v in t["code"].items() if not k.startswith("sdsys/")})),
]

CONTROLS = [   # these must stay green: the same words in a comment are history, not code
    ("a C comment names masters_note_record", plant_code("gplsrc/dh_write.c", "\n/* 2 Nov 26: masters_note_record() was here until S.96 M6 */\n")),
    ("a BASIC comment names K$MASTERS", plant_code("sdsys/gpl.bp/delacc", "\n* 2 Nov 26 dm  kernel(K$MASTERS, 'drop') was here until S.96 M6.\n")),
]


def main():
    t = load()
    if "--selftest" in sys.argv:
        start = 0
        for a_ in sys.argv[1:]:
            if a_.startswith("--from="):
                start = int(a_.split("=", 1)[1])
        base = checks(t)
        if not all(ok for _, ok, _ in base):
            print("test-nomasters-units: the unmutated tree already fails: %r" % [i for i, ok, _ in base if not ok])
            return 2
        missed = n = 0
        for k_, (label, fn) in enumerate(MUTANTS):
            if k_ < start:
                continue
            n += 1
            try:
                rows = checks(fn(t))
            except KeyError as e:
                print("  [FAIL] mutant is not applicable: %s (%s)" % (label, e))
                missed += 1
                continue
            caught = [i.split(" ")[0] for i, ok, _ in rows if not ok]
            print("  [%s] %s%s" % ("PASS" if caught else "FAIL", label, ("  <- " + ", ".join(caught)) if caught else "   MUTANT NOT CAUGHT"))
            missed += 0 if caught else 1
        for label, fn in CONTROLS:
            rows = checks(fn(t))
            bad = [i.split(" ")[0] for i, ok, _ in rows if not ok]
            print("  [%s] control: %s%s" % ("PASS" if not bad else "FAIL", label, ("  <- flagged by " + ", ".join(bad)) if bad else " (not flagged)"))
            missed += 1 if bad else 0
        print("\ntest-nomasters-units --selftest: %d mutants and %d controls, %d wrong" % (n, len(CONTROLS), missed))
        return 1 if missed or n == 0 else 0
    rows = checks(t)
    failed = 0
    for i, ok, d in rows:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", i, "" if ok or not d else "   <- " + d))
        failed += 0 if ok else 1
    print("\ntest-nomasters-units: %d checks, %d failed" % (len(rows), failed))
    return 1 if failed or not rows else 0


if __name__ == "__main__":
    sys.exit(main())
