#!/usr/bin/env python3
"""parity-manifest.py - a mechanical parity manifest of an SD source tree, and a diff of two.

WHY THIS EXISTS.  The Linux/Windows parity audit (Linux S.21, Windows task 47,
started 6 Oct 2026) needs a list of what each port actually ships, read from
the source tree rather than from either port's description of itself.  The
Windows first pass of 22 Sep diffed newvoc and voc_template by hand.  This
widens that to every axis that can be read from files, with one script that
runs on every tree, so each agent trusts only its own run.

It is a data check: no SD, no install, no sudo, no elevation.  Standard
library only, Python 3.6 or later, the same on Linux and Windows.  BYTES IN,
BYTES OUT (the Windows agent's counter, 6 Oct): every input is opened `rb`, CRLF
becomes LF here and not in the text layer, keys are lower-cased ASCII only and
sorted in byte order, every output is written `wb` as UTF-8 with no BOM, and
every recorded path uses `/`.  The same bytes in give the same bytes out.

  python3 gplbld/parity-manifest.py write TREE OUTDIR --side linux|windows --product full|solo
  python3 gplbld/parity-manifest.py diff DIR_A DIR_B [--out DIR] [--limit N]
  python3 gplbld/parity-manifest.py selftest

TREE is a repository root (containing sdb_ai/sd64) or an sd64 directory.
`write` makes one sorted tab-separated file per axis plus MANIFEST.txt.  Columns
are key, hash-or-value, line count, original name; keys are lower case, and
files are hashed after CRLF becomes LF so line endings are never a finding.

AXES.  verbs-newvoc, verbs-voc-template (sdsys/newvoc, sdsys/voc_template: one
file per VOC record), programs (sdsys/gpl.bp), messages (sdsys/messages),
syscom (sdsys/syscom), defines (every $define/#define in gplsrc/keys.h,
gplsrc/err.h and sdsys/syscom/*.h), language (the statement, reserved-word and
function tables in gplbld/microcfg/syntax/sdbasic.yaml, which is generated from
the compiler's own tables), changelog (entry titles), files-dicts
(gplbld/FILES_DICTS, the dictionary field lists), gplsrc (C source files),
gplbld (check and tool names, extension ignored).

INSTRUMENT RULES (CLAUDE.md).  Every run prints the inputs it really used: the
resolved sd64 path, the git commit and dirty count, and per axis the input and
the row count.  It refuses the null case out loud and exits 2: no sd64 tree, a
missing input directory, an axis with no rows, an output directory that holds
something else, a manifest whose axis file does not match its recorded hash
(a half-synced copy), two manifests from the same side or different products,
and a manifest compared with itself.

`diff` compares a linux manifest with a windows one.  Messages are judged by the
agreed number blocks (shared-number-space, W.12): 0-10029 upstream and
10030-10999 shared legacy and 13000-13999 shared new must be byte-identical on
both sides; 11000-11999 belongs to Linux and 12000-12999 to Windows and must
not appear on the other side.  Anything else on the messages axis is not a
finding on its own.  Every other axis counts any difference as a finding.

Exit codes (diff): 0 no findings, 1 findings, 2 the question cannot be answered.
write: 0 written, 2 refused.
"""

import argparse
import contextlib
import datetime
import hashlib
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOL = "parity-manifest 1"

BLOCKS = [
    ("upstream", 0, 10029, "both"),
    ("shared-legacy", 10030, 10999, "both"),
    ("linux", 11000, 11999, "linux"),
    ("windows", 12000, 12999, "windows"),
    ("shared-new", 13000, 13999, "both"),
]


# Inventories, not parity claims: the changelog is written separately by each port, the C
# sources are the mechanism layer, and the check scripts differ by OS.  They are listed in
# full but never counted as findings or allowed to decide the exit code.
INFO_AXES = ("changelog", "gplsrc", "gplbld")


class Refuse(Exception):
    """The measurement cannot be made; say so and exit 2."""


# ---------------------------------------------------------------- reading a tree

_LOWER = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")


_LOWERB = bytes.maketrans(b"ABCDEFGHIJKLMNOPQRSTUVWXYZ", b"abcdefghijklmnopqrstuvwxyz")


def alower(s):
    """ASCII-only lower case: no locale and no non-ASCII folding, so every machine agrees."""
    return s.translate(_LOWER)


def fwd(p):
    """A recorded path always uses /, so a Windows run and a Linux run print the same text."""
    return p.replace(os.sep, "/")


def norm_bytes(b):
    return b.replace(b"\r\n", b"\n")


def digest(b):
    return hashlib.sha1(b).hexdigest()[:16]


def nlines(b):
    if not b:
        return 0
    return b.count(b"\n") + (0 if b.endswith(b"\n") else 1)


def read_file(path):
    with open(path, "rb") as f:
        return f.read()


def find_sd64(tree):
    tree = os.path.abspath(tree)
    for cand in (os.path.join(tree, "sdb_ai", "sd64"), os.path.join(tree, "sd64"), tree):
        if (os.path.isdir(os.path.join(cand, "sdsys", "newvoc"))
                and os.path.isdir(os.path.join(cand, "gplsrc"))):
            return cand
    raise Refuse("no sd64 tree under %s (looked for sdsys/newvoc and gplsrc)" % tree)


def git(tree, *args):
    try:
        r = subprocess.run(["git", "-C", tree] + list(args), stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, universal_newlines=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def unique_keys(rows):
    """Two names that fold to one key (a case twin), or one name defined twice, must all survive."""
    seen = set()
    out = []
    for r in sorted(rows, key=lambda r: (r[0], r[3])):
        k = r[0]
        if k in seen:
            base = k + "~" + r[3]
            k = base
            n = 1
            while k in seen:
                n += 1
                k = "%s#%d" % (base, n)
            r = (k,) + tuple(r[1:])
        seen.add(k)
        out.append(r)
    return out


def code_hash(b):
    """Hash of the BASIC source with whole-line comments, blank lines and spacing removed.

    A dated START-HISTORY line makes two ports' copies of one program differ byte for
    byte without changing what it does; two programs with the same code hash differ only
    in comments.  A trailing ;* comment is kept, so this can only over-report code
    differences, never hide one."""
    keep = []
    for raw in b.split(b"\n"):
        s = b" ".join(raw.split())
        if not s or s[:1] in (b"*", b"!"):
            continue
        u = s.upper()
        if u == b"REM" or u.startswith(b"REM "):
            continue
        keep.append(s)
    return digest(b"\n".join(keep))


def flat_dir(sd64, rel, code=False):
    d = os.path.join(sd64, *rel.split("/"))
    if not os.path.isdir(d):
        raise Refuse("missing input directory %s" % d)
    rows = []
    for name in os.listdir(d):
        p = os.path.join(d, name)
        if os.path.isdir(p):
            rows.append((alower(name), "DIR", "0", name, "", "", ""))
            continue
        b = norm_bytes(read_file(p))
        lb = b.translate(_LOWERB)
        rows.append((alower(name), digest(b), str(nlines(b)), name, code_hash(b) if code else "",
                     digest(lb), code_hash(lb) if code else ""))
    return unique_keys(rows)


def gplbld_names(sd64):
    d = os.path.join(sd64, "gplbld")
    if not os.path.isdir(d):
        raise Refuse("missing input directory %s" % d)
    rows = []
    for dirpath, dirnames, filenames in os.walk(d):
        dirnames[:] = [x for x in dirnames if x not in ("__pycache__", "FILES_DICTS")]
        for fn in filenames:
            if fn.endswith(".pyc"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, fn), d).replace(os.sep, "/")
            stem = os.path.splitext(rel)[0]
            rows.append((alower(stem), "-", "0", rel, "", "", ""))
    return unique_keys(rows)


DEF_RE = re.compile(r"^\s*[$#]define\s+([A-Za-z0-9_.$%]+)\s*(.*)$")


def strip_comment(s):
    s = re.sub(r"/\*.*?\*/", "", s)
    s = re.sub(r"/\*.*$", "", s)
    s = s.split(";*")[0]
    return " ".join(s.split())


def defines(sd64):
    files = ["gplsrc/keys.h", "gplsrc/err.h"]
    sc = os.path.join(sd64, "sdsys", "syscom")
    if not os.path.isdir(sc):
        raise Refuse("missing input directory %s" % sc)
    files += ["sdsys/syscom/" + f for f in sorted(os.listdir(sc)) if f.endswith(".h")]
    rows = []
    for rel in files:
        p = os.path.join(sd64, *rel.split("/"))
        if not os.path.isfile(p):
            raise Refuse("missing input file %s" % p)
        text = norm_bytes(read_file(p)).decode("latin-1")
        for line in text.split("\n"):
            m = DEF_RE.match(line)
            if m:
                rows.append((rel + ":" + alower(m.group(1)), strip_comment(m.group(2)),
                             "0", m.group(1), "", "", ""))
    return unique_keys(rows)


def language(sd64):
    p = os.path.join(sd64, "gplbld", "microcfg", "syntax", "sdbasic.yaml")
    if not os.path.isfile(p):
        raise Refuse("missing input file %s" % p)
    text = norm_bytes(read_file(p)).decode("latin-1")
    bs2 = "\\" * 2
    rows = []
    for kind in ("statement", "special", "identifier"):
        pat = r'^\s*-\s*' + kind + r':\s*"\(\?i\)' + re.escape(bs2) + r'b\(([^)]*)\)'
        m = re.search(pat, text, re.M)
        if not m:
            raise Refuse("no %s table found in %s" % (kind, p))
        for name in m.group(1).split("|"):
            name = name.replace(bs2 + ".", ".")
            if name:
                rows.append((kind + ":" + alower(name), "", "0", name, "", "", ""))
    return unique_keys(rows)


DATE_RE = re.compile(r"^(\d{2} [A-Z][a-z]{2} \d{2})\s\s+(\S.*)$")
SECTION_RE = re.compile(r"^(\S+) - (\S.*)$")


def changelog(sd64):
    p = os.path.join(sd64, "sdsys", "changelog")
    if not os.path.isfile(p):
        raise Refuse("missing input file %s" % p)
    lines = norm_bytes(read_file(p)).decode("latin-1").split("\n")
    rows = []
    section = ""
    i = 0
    while i < len(lines):
        line = lines[i]
        m = DATE_RE.match(line)
        if m:
            parts = [m.group(2).strip()]
            while i + 1 < len(lines) and lines[i + 1].strip() and lines[i + 1][:1] in (" ", "\t"):
                i += 1
                parts.append(lines[i].strip())
            title = " ".join(" ".join(parts).split())
            rows.append((alower(title)[:160], m.group(1), section, title[:160], "", "", ""))
        else:
            s = SECTION_RE.match(line)
            if s and i + 1 < len(lines) and lines[i + 1].startswith("---"):
                section = s.group(1)
        i += 1
    return unique_keys(rows)


def build_axes(sd64):
    axes = [
        ("verbs-newvoc", flat_dir(sd64, "sdsys/newvoc"), "sdsys/newvoc"),
        ("verbs-voc-template", flat_dir(sd64, "sdsys/voc_template"), "sdsys/voc_template"),
        ("programs", flat_dir(sd64, "sdsys/gpl.bp", code=True), "sdsys/gpl.bp"),
        ("messages", flat_dir(sd64, "sdsys/messages"), "sdsys/messages"),
        ("syscom", flat_dir(sd64, "sdsys/syscom"), "sdsys/syscom"),
        ("defines", defines(sd64), "gplsrc/keys.h gplsrc/err.h sdsys/syscom/*.h"),
        ("language", language(sd64), "gplbld/microcfg/syntax/sdbasic.yaml"),
        ("changelog", changelog(sd64), "sdsys/changelog"),
        ("files-dicts", flat_dir(sd64, "gplbld/FILES_DICTS"), "gplbld/FILES_DICTS"),
        ("gplsrc", flat_dir(sd64, "gplsrc"), "gplsrc"),
        ("gplbld", gplbld_names(sd64), "gplbld"),
    ]
    for name, rows, inp in axes:
        if not rows:
            raise Refuse("axis %s read %s and found no rows" % (name, inp))
    return axes


# ---------------------------------------------------------------- writing

def clean(x):
    return str(x).replace("\t", " ").replace("\n", " ").replace("\r", " ")


def serialise(rows):
    return "".join("\t".join(clean(x) for x in r) + "\n" for r in rows).encode("utf-8")


def cmd_write(args):
    sd64 = find_sd64(args.tree)
    out = os.path.abspath(args.outdir)
    if os.path.exists(out):
        if not os.path.isdir(out):
            raise Refuse("%s exists and is not a directory" % out)
        if os.listdir(out) and not os.path.isfile(os.path.join(out, "MANIFEST.txt")):
            raise Refuse("%s holds files but no MANIFEST.txt: not overwriting what is not a manifest" % out)
    head = git(sd64, "rev-parse", "--short", "HEAD") or "unknown"
    st = git(sd64, "status", "--porcelain")
    dirty = str(len([x for x in st.split("\n") if x.strip()])) if st is not None else "unknown"
    tree_s = fwd(os.path.abspath(args.tree))
    print("%s write" % TOOL)
    print("  tree     %s" % tree_s)
    print("  sd64     %s" % fwd(sd64))
    print("  side     %s   product %s" % (args.side, args.product))
    print("  commit   %s   dirty files %s" % (head, dirty))
    axes = build_axes(sd64)
    os.makedirs(out, exist_ok=True)
    man = ["tool: %s" % TOOL, "side: %s" % args.side, "product: %s" % args.product,
           "tree: %s" % tree_s, "sd64: %s" % fwd(sd64),
           "head: %s" % head, "dirty: %s" % dirty,
           "written: %s" % datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")]
    for name, rows, inp in axes:
        data = serialise(rows)
        with open(os.path.join(out, name + ".tsv"), "wb") as f:
            f.write(data)
        man.append("axis\t%s\t%d\t%s\t%s" % (name, len(rows), digest(data), inp))
        print("  %-20s %6d lines  %s  from %s" % (name + ".tsv", len(rows), digest(data), inp))
    with open(os.path.join(out, "MANIFEST.txt"), "wb") as f:
        f.write(("\n".join(man) + "\n").encode("utf-8"))
    print("wrote %d axis files and MANIFEST.txt to %s" % (len(axes), fwd(out)))
    return 0


# ---------------------------------------------------------------- diffing

def load_manifest(d):
    d = os.path.abspath(d)
    mp = os.path.join(d, "MANIFEST.txt")
    if not os.path.isfile(mp):
        raise Refuse("%s has no MANIFEST.txt" % d)
    head = {}
    axes = []
    for line in read_file(mp).decode("utf-8").split("\n"):
        if line.startswith("axis\t"):
            axes.append(line.split("\t"))
        elif ": " in line:
            k, v = line.split(": ", 1)
            head[k] = v
    for need in ("side", "product", "tree", "head", "written"):
        if need not in head:
            raise Refuse("%s: MANIFEST.txt lacks %s" % (d, need))
    if not axes:
        raise Refuse("%s: MANIFEST.txt lists no axes" % d)
    data = {}
    for _, name, nrows, h, inp in axes:
        p = os.path.join(d, name + ".tsv")
        if not os.path.isfile(p):
            raise Refuse("%s: axis file %s.tsv is missing" % (d, name))
        b = read_file(p)
        if digest(b) != h:
            raise Refuse("%s: %s.tsv does not match the hash recorded in MANIFEST.txt "
                         "(a half-synced or edited copy)" % (d, name))
        rows = {}
        for line in b.decode("utf-8").split("\n"):
            if line:
                c = (line.split("\t") + [""] * 7)[:7]
                rows[c[0]] = c
        if len(rows) != int(nrows):
            raise Refuse("%s: %s.tsv holds %d rows, MANIFEST.txt says %s" % (d, name, len(rows), nrows))
        data[name] = rows
    head["dir"] = d
    return head, [a[1] for a in axes], data


def block_of(key):
    if re.match(r"^[0-9]+$", key):
        n = int(key)
        for name, lo, hi, who in BLOCKS:
            if lo <= n <= hi:
                return name, who
    return "unassigned", "both"


def compare_plain(lin, win):
    same = []
    differ = []
    comment_only = []
    case_only = []
    case_comment = []
    case = []
    for k in sorted(set(lin) & set(win)):
        a, b = lin[k], win[k]
        if a[1] == b[1] and a[2] == b[2]:
            same.append(k)
        elif a[5] and b[5] and a[5] == b[5]:
            case_only.append(k)
        elif a[4] and b[4] and a[4] == b[4]:
            comment_only.append(k)
        elif a[6] and b[6] and a[6] == b[6]:
            case_comment.append(k)
        else:
            differ.append(k)
        if a[3] != b[3] and alower(a[3]) == alower(b[3]):
            case.append(k)
    only_l = sorted(set(lin) - set(win))
    only_w = sorted(set(win) - set(lin))
    return same, differ, comment_only, case_only, case_comment, only_l, only_w, case


NUM_RE = re.compile(r"^-?[0-9]+$")
KEYS_PREFIX = "gplsrc/keys.h:"


def number_space(rows):
    """{namespace: {value: set of names}} for the K_ (kernel key) and SD_ (SDEXT call)
    numbers in gplsrc/keys.h.  Numeric values only."""
    out = {"k_": {}, "sd_": {}}
    for k, r in rows.items():
        if not k.startswith(KEYS_PREFIX) or not NUM_RE.match(r[1]):
            continue
        name = k[len(KEYS_PREFIX):]
        for ns in out:
            if name.startswith(ns):
                out[ns].setdefault(r[1], set()).add(r[3])
    return out


def number_clashes(lin_defs, win_defs):
    """One number, two meanings.  WITHIN-<side>: two names of one side share a value.
    CLASH: a value that both sides use and that no name is common to, so a program
    both ports ship byte for byte would silently mean two things (PAL-7: K_LOGIN_UID
    and K_OS_ELEVATED were both 65).  Found by the Windows agent's suggestion."""
    ls, ws = number_space(lin_defs), number_space(win_defs)
    rows = []
    for ns in ("k_", "sd_"):
        for side, sp in (("LINUX", ls), ("WINDOWS", ws)):
            for val in sorted(sp[ns], key=int):
                if len(sp[ns][val]) > 1:
                    rows.append("WITHIN-%s\t%s %s\t%s" % (side, ns.upper(), val, " ".join(sorted(sp[ns][val]))))
        for val in sorted(set(ls[ns]) & set(ws[ns]), key=int):
            if not (ls[ns][val] & ws[ns][val]):
                rows.append("CLASH\t%s %s\tlinux %s | windows %s"
                            % (ns.upper(), val, " ".join(sorted(ls[ns][val])), " ".join(sorted(ws[ns][val]))))
    return rows


def privilege_split(dl, dw):
    """A verb that one port keeps for SDSYS alone (in voc_template, not in newvoc) and
    the other gives to every account (in its newvoc): who may run it differs.  Asked by
    the Windows agent (its 22:35 read of the identity programs), answered by hand first,
    then made a check."""
    rows = []
    for side, mine, other in (("LINUX", dl, dw), ("WINDOWS", dw, dl)):
        sysonly = set(mine["verbs-voc-template"]) - set(mine["verbs-newvoc"])
        for k in sorted(sysonly & set(other["verbs-newvoc"])):
            rows.append("%s-RESTRICTS\t%s\tSDSYS only on %s, every account on the other port"
                        % (side, k, side.lower()))
    return rows


def fmt_pair(a, b):
    return "%s (%s lines) | %s (%s lines)" % (a[1][:16] or "-", a[2], b[1][:16] or "-", b[2])


def cmd_diff(args):
    ha, axa, da = load_manifest(args.dir_a)
    hb, axb, db = load_manifest(args.dir_b)
    if ha["dir"] == hb["dir"] or (ha["tree"] == hb["tree"] and ha["head"] == hb["head"]
                                  and ha["written"] == hb["written"]):
        raise Refuse("both manifests are the same run: comparing a manifest with itself proves nothing")
    if ha["side"] == hb["side"]:
        raise Refuse("both manifests are from the %s side: a parity diff compares a linux manifest with a windows one"
                     % ha["side"])
    if ha["product"] != hb["product"]:
        raise Refuse("products differ (%s against %s): compare full with full, solo with solo"
                     % (ha["product"], hb["product"]))
    if set(axa) != set(axb):
        raise Refuse("the two manifests list different axes: %s against %s" % (sorted(axa), sorted(axb)))
    if ha["side"] == "linux":
        hl, hw, dl, dw = ha, hb, da, db
    else:
        hl, hw, dl, dw = hb, ha, db, da
    lines = []

    def say(s=""):
        lines.append(s)
        print(s)

    say("%s diff   product %s" % (TOOL, ha["product"]))
    for lab, h in (("linux  ", hl), ("windows", hw)):
        say("  %s  commit %s  dirty %s  written %s" % (lab, h["head"], h.get("dirty", "?"), h["written"]))
        say("           tree %s" % h["tree"])
    say("")
    total = 0
    detail = {}
    for name in axa:
        lin, win = dl[name], dw[name]
        if name == "messages":
            blocks = {}
            bad = []
            for k in sorted(set(lin) | set(win), key=lambda x: (not x.isdigit(), int(x) if x.isdigit() else 0, x)):
                bname, who = block_of(k)
                t = blocks.setdefault(bname, {"both": 0, "differ": 0, "only-linux": 0,
                                              "only-windows": 0, "bad": 0})
                a, b = lin.get(k), win.get(k)
                if a and b:
                    t["both" if (a[1] == b[1]) else "differ"] += 1
                elif a:
                    t["only-linux"] += 1
                else:
                    t["only-windows"] += 1
                if who == "both":
                    unexpected = (not a) or (not b) or a[1] != b[1]
                elif who == "linux":
                    unexpected = bool(b)
                else:
                    unexpected = bool(a)
                if unexpected:
                    t["bad"] += 1
                    bad.append((k, bname, "linux" if a else "-", "windows" if b else "-",
                                "text differs" if (a and b and a[1] != b[1]) else ""))
            nb = len(bad)
            total += nb
            say("AXIS %-20s linux=%d windows=%d  findings=%d" % (name, len(lin), len(win), nb))
            for bname, lo, hi, who in BLOCKS + [("unassigned", 0, 0, "both")]:
                if bname in blocks:
                    t = blocks[bname]
                    say("    block %-14s identical=%-5d differ=%-4d only-linux=%-5d only-windows=%-5d unexpected=%d"
                        % (bname, t["both"], t["differ"], t["only-linux"], t["only-windows"], t["bad"]))
            detail[name] = ["%s\t%s\tlinux:%s\twindows:%s\t%s" % (k, b, l, w, n) for k, b, l, w, n in bad]
            for row in detail[name][:args.limit]:
                say("      " + row)
            if len(detail[name]) > args.limit:
                say("      ... %d more (use --out for the full list)" % (len(detail[name]) - args.limit))
            continue
        same, differ, comment_only, case_only, case_comment, only_l, only_w, case = compare_plain(lin, win)
        nb = (len(differ) + len(case_only) + len(case_comment) + len(only_l) + len(only_w) + len(case))
        info = name in INFO_AXES
        if not info:
            total += nb
        say("AXIS %-20s linux=%d windows=%d  same=%d differ=%d case-only=%d case+comment=%d comment-only=%d "
            "only-linux=%d only-windows=%d name-case=%d  findings=%d%s"
            % (name, len(lin), len(win), len(same), len(differ), len(case_only), len(case_comment),
               len(comment_only), len(only_l), len(only_w), len(case), 0 if info else nb,
               ("  [info axis: %d listed, not counted]" % nb) if info else ""))
        rows = []
        for k in differ:
            rows.append("DIFFER\t%s\t%s" % (k, fmt_pair(lin[k], win[k])))
        for k in case_only:
            rows.append("CASE-ONLY\t%s\t%s" % (k, fmt_pair(lin[k], win[k])))
        for k in case_comment:
            rows.append("CASE+COMMENT\t%s\t%s" % (k, fmt_pair(lin[k], win[k])))
        for k in only_l:
            rows.append("ONLY-LINUX\t%s\t%s" % (k, lin[k][1][:60]))
        for k in only_w:
            rows.append("ONLY-WINDOWS\t%s\t%s" % (k, win[k][1][:60]))
        for k in case:
            rows.append("CASE\t%s\tlinux %s | windows %s" % (k, lin[k][3], win[k][3]))
        detail[name] = rows + ["COMMENT-ONLY\t%s\t%s" % (k, fmt_pair(lin[k], win[k])) for k in comment_only]
        for row in rows[:args.limit]:
            say("      " + row)
        if len(rows) > args.limit:
            say("      ... %d more (use --out for the full list)" % (len(rows) - args.limit))
    clash = number_clashes(dl["defines"], dw["defines"]) if "defines" in dl else []
    total += len(clash)
    say("AXIS %-20s kernel key and SDEXT numbers: one value, two meanings  findings=%d" % ("number-clash", len(clash)))
    for row in clash[:args.limit]:
        say("      " + row)
    detail["number-clash"] = clash
    split = (privilege_split(dl, dw)
             if all(a in dl and a in dw for a in ("verbs-newvoc", "verbs-voc-template")) else [])
    total += len(split)
    say("AXIS %-20s verbs kept for SDSYS on one port and open to every account on the other  findings=%d"
        % ("privilege-split", len(split)))
    for row in split[:args.limit]:
        say("      " + row)
    detail["privilege-split"] = split
    say("")
    say("findings %d  ->  exit %d" % (total, 1 if total else 0))
    if args.out:
        od = os.path.abspath(args.out)
        os.makedirs(od, exist_ok=True)
        for name, rows in detail.items():
            with open(os.path.join(od, name + ".diff.txt"), "wb") as f:
                f.write(("\n".join(rows) + ("\n" if rows else "")).encode("utf-8"))
        with open(os.path.join(od, "SUMMARY.txt"), "wb") as f:
            f.write(("\n".join(lines) + "\n").encode("utf-8"))
        print("full lists written to %s" % od)
    return 1 if total else 0


# ---------------------------------------------------------------- self test

YAML = ('rules:\n'
        '    - statement: "(?i)\\\\b(ABORT|DELETE\\\\.COMMON|SET\\\\.EXIT\\\\.STATUS)\\\\b"\n'
        '    - special: "(?i)\\\\b(APPEND|WHILE)\\\\b"\n'
        '    - identifier: "(?i)\\\\b(ABS|ACCEPT\\\\.SOCKET\\\\.CONNECTION)\\\\b"\n')
KEYS_C = "#define IN_FIELD_MODE 0x0001   /* a note */\n#define ER_ARGS 1\n#define K_LOGIN_UID 9\n#define SD_SALT 100\n"
KEYS_B = "      $define FL$OPEN 0  ;* open\n      $define FL$PATH 2\n"
CHANGELOG = ("L1.1-3 - in progress\n-------------\n\n"
             "05 Oct 26  FIRST TITLE\n           CONTINUED HERE.\n\n           Body.\n\n"
             "04 Oct 26  SECOND TITLE\n\n           Body.\n")


def put(root, rel, text):
    p = os.path.join(root, "sdb_ai", "sd64", *rel.split("/"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(text.encode("latin-1"))


def make_tree(root, side):
    for rec in ("abort", "list", "ED"):
        put(root, "sdsys/newvoc/" + rec, "V\n@SDSYS/" + rec + "\n")
        put(root, "sdsys/voc_template/" + rec, "V\n@SDSYS/" + rec + "\n")
    put(root, "sdsys/gpl.bp/prog1", "* one\nprint 1\nend\n")
    put(root, "sdsys/gpl.bp/prog2", "* two\nprint 2\nend\n")
    put(root, "sdsys/messages/1000", "Hello\n")
    put(root, "sdsys/messages/10031", "Shared old\n")
    put(root, "sdsys/messages/13001", "Shared new\n")
    put(root, "sdsys/messages/11001" if side == "linux" else "sdsys/messages/12001", "Own block\n")
    put(root, "sdsys/syscom/keys.h", KEYS_B)
    put(root, "sdsys/syscom/err.h", "      $define E.ONE 1\n")
    put(root, "gplbld/FILES_DICTS/accounts", "D\nF1\n")
    put(root, "gplsrc/keys.h", KEYS_C)
    put(root, "gplsrc/err.h", KEYS_C + "#define ER_ARGS 1\n#define ER_ARGS 1\n")
    put(root, "gplsrc/op_a.c", "int a;\n")
    put(root, "gplbld/check.py" if side == "linux" else "gplbld/check.ps1", "x\n")
    put(root, "gplbld/microcfg/syntax/sdbasic.yaml", YAML)
    put(root, "sdsys/changelog", CHANGELOG)


def selftest():
    work = tempfile.mkdtemp(prefix="parity-selftest-")
    results = []

    def check(name, cond, detail=""):
        results.append((name, bool(cond), detail))
        print("  %s  %s%s" % ("PASS" if cond else "FAIL", name, ("   [" + detail + "]") if (detail and not cond) else ""))

    def run(argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            try:
                code = main(argv)
            except SystemExit as e:
                code = e.code
        return code, buf.getvalue()

    def mk(side, mutate=None, name=None):
        name = name or side
        root = os.path.join(work, name + "-tree")
        shutil.rmtree(root, ignore_errors=True)
        make_tree(root, side)
        if mutate:
            mutate(root)
        out = os.path.join(work, name + "-man")
        shutil.rmtree(out, ignore_errors=True)
        code, text = run(["write", root, out, "--side", side, "--product", "full"])
        return code, out, text

    def finding(text, axis):
        m = re.search(r"^AXIS %s\s.*findings=(\d+)" % re.escape(axis), text, re.M)
        return int(m.group(1)) if m else -1

    try:
        print("parity-manifest selftest (scratch %s)" % work)
        cl, dl, tl = mk("linux")
        cw, dw, tw = mk("windows")
        check("control: write linux", cl == 0 and "wrote 11 axis files" in tl, tl[-200:])
        check("control: write windows", cw == 0)
        check("write prints its real inputs", "sd64 " in tl and "commit " in tl and "sdsys/newvoc" in tl)
        code, text = run(["diff", dl, dw])
        check("control: baseline diff is clean (a probe that cannot pass proves nothing)",
              code == 0 and "findings 0" in text, text[-400:])
        check("control: expected one-sided blocks 11001/12001 are not findings",
              finding(text, "messages") == 0)

        def mutant(label, side_mut, axis, want_exit=1, want_findings=None, info=False, has=None):
            cw2, dw2, _ = mk("windows", side_mut, name="mut")
            code, text = run(["diff", dl, dw2])
            if info:
                m = re.search(r"^AXIS %s\s.*only-windows=(\d+)" % re.escape(axis), text, re.M)
                seen = int(m.group(1)) if m else 0
                check(label + " (listed, not counted)",
                      cw2 == 0 and code == 0 and seen >= 1 and finding(text, axis) == 0,
                      "exit %s listed %s findings %s" % (code, seen, finding(text, axis)))
                return
            got = finding(text, axis)
            ok = cw2 == 0 and code == want_exit and (got >= 1 if want_findings is None else got == want_findings)
            if has:
                m = re.search(r"^AXIS %s\s.*%s" % (re.escape(axis), has), text, re.M)
                ok = ok and bool(m)
            check(label, ok, "exit %s findings %s" % (code, got))

        mutant("mutant: a verb only on windows", lambda r: put(r, "sdsys/newvoc/zap", "V\n"), "verbs-newvoc")
        mutant("mutant: a program differs", lambda r: put(r, "sdsys/gpl.bp/prog1", "* one\nprint 9\nend\n"), "programs")
        mutant("mutant: a case twin of a verb name",
               lambda r: (os.replace(os.path.join(r, "sdb_ai", "sd64", "sdsys", "newvoc", "ED"),
                                     os.path.join(r, "sdb_ai", "sd64", "sdsys", "newvoc", "ed"))),
               "verbs-newvoc")
        mutant("mutant: a verb body differs only in case",
               lambda r: put(r, "sdsys/newvoc/abort", "V\n@SDSYS/ABORT\n"), "verbs-newvoc", has="case-only=1 ")
        mutant("mutant: shared message text differs", lambda r: put(r, "sdsys/messages/10031", "Changed\n"), "messages")
        mutant("mutant: a shared message missing on windows",
               lambda r: os.remove(os.path.join(r, "sdb_ai", "sd64", "sdsys", "messages", "13001")), "messages")
        mutant("mutant: windows holds a linux-block number", lambda r: put(r, "sdsys/messages/11002", "x\n"), "messages")
        mutant("mutant: a define differs", lambda r: put(r, "sdsys/syscom/keys.h", KEYS_B + "      $define FL$X 9\n"), "defines")
        mutant("mutant: a language word dropped",
               lambda r: put(r, "gplbld/microcfg/syntax/sdbasic.yaml", YAML.replace("|WHILE", "")), "language")
        mutant("mutant: a changelog entry only on windows",
               lambda r: put(r, "sdsys/changelog", CHANGELOG + "\n03 Oct 26  THIRD TITLE\n\n           Body.\n"),
               "changelog", info=True)
        mutant("mutant: a C source file only on windows", lambda r: put(r, "gplsrc/op_b.c", "int b;\n"),
               "gplsrc", info=True)
        mutant("mutant: a program differs only in a comment is not a finding",
               lambda r: put(r, "sdsys/gpl.bp/prog1", "* one, reworded\n*  more history\nprint 1\nend\n"),
               "programs", want_exit=0, want_findings=0)
        mutant("mutant: one kernel key number, two meanings (the PAL-7 shape)",
               lambda r: put(r, "gplsrc/keys.h", KEYS_C.replace("K_LOGIN_UID", "K_OS_ELEVATED")), "number-clash",
               has="kernel key and SDEXT numbers")
        mutant("mutant: two names of one side share a key number",
               lambda r: put(r, "gplsrc/keys.h", KEYS_C + "#define K_ALSO_NINE 9\n"), "number-clash")
        mutant("mutant: a verb SDSYS-only on one port and open to every account on the other",
               lambda r: os.remove(os.path.join(r, "sdb_ai", "sd64", "sdsys", "newvoc", "list")),
               "privilege-split", has="SDSYS on one port")
        mutant("mutant: a dictionary field list differs", lambda r: put(r, "gplbld/FILES_DICTS/accounts", "D\nF2\n"),
               "files-dicts")

        cw3, dw3, _ = mk("windows", lambda r: put(r, "sdsys/gpl.bp/prog1", "* one\r\nprint 1\r\nend\r\n"), name="crlf")
        code, text = run(["diff", dl, dw3])
        check("control: CRLF is not a finding", cw3 == 0 and code == 0 and finding(text, "programs") == 0,
              "exit %s" % code)

        empty = os.path.join(work, "empty-tree")
        os.makedirs(empty, exist_ok=True)
        code, text = run(["write", empty, os.path.join(work, "empty-man"), "--side", "linux", "--product", "full"])
        check("null: an empty tree is refused (exit 2)", code == 2 and "REFUSED" in text, text[-200:])
        stray = os.path.join(work, "stray")
        os.makedirs(stray, exist_ok=True)
        with open(os.path.join(stray, "keep.txt"), "w") as f:
            f.write("not a manifest\n")
        root = os.path.join(work, "linux-tree")
        code, text = run(["write", root, stray, "--side", "linux", "--product", "full"])
        check("null: an output directory holding other files is not overwritten",
              code == 2 and os.path.isfile(os.path.join(stray, "keep.txt")))
        code, text = run(["diff", dl, dl])
        check("null: a manifest against itself is refused (exit 2)", code == 2 and "REFUSED" in text)
        cl2, dl2, _ = mk("linux", name="linux2")
        code, text = run(["diff", dl, dl2])
        check("null: two linux manifests are refused (exit 2)", code == 2 and "linux" in text)
        half = os.path.join(work, "half-man")
        shutil.rmtree(half, ignore_errors=True)
        shutil.copytree(dw, half)
        p = os.path.join(half, "messages.tsv")
        with open(p, "rb") as f:
            b = f.read()
        with open(p, "wb") as f:
            f.write(b[:len(b) // 2])
        code, text = run(["diff", dl, half])
        check("null: a half-synced axis file is refused (exit 2)", code == 2 and "hash" in text, text[-200:])
    finally:
        shutil.rmtree(work, ignore_errors=True)
    failed = [r for r in results if not r[1]]
    print("selftest: %d rows, %d failed" % (len(results), len(failed)))
    return 1 if failed else 0


# ---------------------------------------------------------------- entry

def main(argv):
    ap = argparse.ArgumentParser(prog="parity-manifest.py", description="parity manifest of an SD source tree")
    sub = ap.add_subparsers(dest="cmd")
    w = sub.add_parser("write")
    w.add_argument("tree")
    w.add_argument("outdir")
    w.add_argument("--side", required=True, choices=["linux", "windows"])
    w.add_argument("--product", required=True, choices=["full", "solo"])
    d = sub.add_parser("diff")
    d.add_argument("dir_a")
    d.add_argument("dir_b")
    d.add_argument("--out")
    d.add_argument("--limit", type=int, default=25)
    sub.add_parser("selftest")
    args = ap.parse_args(argv)
    if not args.cmd:
        ap.print_usage()
        return 2
    try:
        if args.cmd == "write":
            return cmd_write(args)
        if args.cmd == "diff":
            return cmd_diff(args)
        return selftest()
    except Refuse as e:
        print("REFUSED: %s" % e)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
