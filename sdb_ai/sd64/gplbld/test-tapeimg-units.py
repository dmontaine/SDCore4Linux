#!/usr/bin/env python3
"""test-tapeimg-units.py - S.92 stage S1: the tape-image writer, the strict reference reader and the name layer (gplbld/tapegen.py).

A free check: no SD, no install, no sudo.  It holds three things.
  1. THE REAL IMAGE.  `.claude/tape-ref/as-ref-1.img` was written by the old ACCOUNT.SAVE (30 Oct 2026).  The reader must parse it,
     the writer must rebuild it BYTE FOR BYTE, the LLLL length rule the writer uses must give the real image's own numbers, and the
     fixture's records must come back as the fixture program wrote them.  The image is a private file; when it is missing this check
     says CANNOT RUN and exits 2 - it never passes without it.
  2. THE RECIPES.  Every synthetic and hostile image in tapegen.RECIPES gets exactly the verdict it is listed with (a refusal is
     compared by its code, not by "some error"), and every refusal code the reader can give is exercised by at least one recipe.
  3. THE NAME LAYER.  Hostile names get their own reason, good names pass, folded names keep the first.

Caveat (the instrument rule): everything here is the old writer agreeing with our reading of it.  It says nothing about what another
system writes.

  python3 test-tapeimg-units.py              the checks
  python3 test-tapeimg-units.py --selftest   the checks run against mutants of tapegen.py; each mutant must fail at least one

Exit 0 all passed, 1 a check failed, 2 cannot run (no reference image).
"""

import importlib.util
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REAL = "/home/don/Projects/SDCore4Linux/.claude/tape-ref/as-ref-1.img"
REAL2 = "/home/don/Projects/SDCore4Linux/.claude/tape-ref/as-ref-2.img"
SRC = os.path.join(HERE, "tapegen.py")


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_checks(tg, big):
    """Return (passed, failed list of (label, detail)).  tg is the module under test."""
    res = []

    def check(label, ok, detail=""):
        res.append((label, bool(ok), detail))

    VM, SM = tg.VM, tg.SM

    # ---- 1. the real image
    data = open(REAL, "rb").read()
    try:
        m = tg.parse_image(data)
    except Exception as e:  # noqa: BLE001 - a mutant may break the reader in any way
        check("A1 the real image parses", False, "%s: %s" % (type(e).__name__, e))
        return res
    items = m["items"]
    ds = [i for i in items if i["kind"] == "D"]
    ii = [i for i in items if i["kind"] == "I"]
    check("A1 the real image parses: 85 blocks, account DON, 13 headers, 963 items",
          m["blocks"] == 85 and m["label"]["account"] == b"DON" and len(ds) == 13 and len(ii) == 963,
          "blocks=%s account=%s D=%d I=%d" % (m["blocks"], m["label"]["account"], len(ds), len(ii)))
    check("A1b every level is present (a parse that found nothing would pass the counts above only by luck)",
          sorted(set(d["level"] for d in ds)) == [b"1", b"2", b"3"])
    try:
        again = tg.build_image(m)
    except Exception as e:  # noqa: BLE001
        again = b""
        check("A2 the writer rebuilds the real image", False, "%s: %s" % (type(e).__name__, e))
    else:
        first = next((k for k in range(min(len(again), len(data))) if again[k] != data[k]), None)
        check("A2 the writer rebuilds the real image byte for byte (%d bytes)" % len(data), again == data,
              "lengths %d/%d, first difference at %s" % (len(again), len(data), first))
    # the LLLL rule: rebuild every token without the number the image carried
    odd = []
    for it in items:
        plain = dict(it)
        plain["llll"] = None
        tok = tg.d_token if it["kind"] == "D" else tg.i_token
        if tok(plain) != tok(it):
            odd.append((it["kind"], it.get("num"), it.get("id") or it.get("name"), it["llll"] - int(tok(plain).split(tg.FM)[2 if it["kind"] == "I" else 3][:4])))
    check("A3 the length rule gives the real image's own LLLL for all but one of %d tokens (the account's own UMASK, one less)" % len(items),
          odd == [("I", b"173", b"UMASK", -1)], "differ: %r" % odd)
    cust = [i for i in ii if i["num"] == b"180"]
    byid = dict((i["id"], i) for i in cust)
    check("A4a CUST data: C001 holds its value and subvalue marks",
          byid.get(b"C001", {}).get("fields") == [b"Acme Ltd", b"red" + VM + b"dark" + SM + b"lime" + VM + b"blue", b"x", b"12.50"],
          repr(byid.get(b"C001")))
    check("A4b an id with a space (C 002)", byid.get(b"C 002", {}).get("fields") == [b"Second one", b"plain"])
    big_rec = byid.get(b"C003", {}).get("fields", [])
    check("A4c the record longer than a block is one item of 60 lines and the empty field its last mark leaves",
          len(big_rec) == 61 and big_rec[0].startswith(b"line 1 of the big record") and big_rec[59].startswith(b"line 60 of") and big_rec[60] == b"",
          "%d fields" % len(big_rec))
    check("A4d a byte above 127 comes back unchanged", byid.get(b"C004", {}).get("fields") == [b"caf\xe9", b"tail"])
    check("A4e an empty first field", byid.get(b"C005", {}).get("fields") == [b"", b"only second"])
    docs = [i for i in ii if i["id"] == b"note.txt"]
    check("A4f a directory file's newlines are field marks", len(docs) == 1 and docs[0]["fields"] == [b"hello", b"second line", b""],
          repr(docs))
    check("A4g ORD holds its 100 records", len([i for i in ii if i["num"] == b"184"]) == 100)

    # ---- 1b. the second real image: records that hold an item mark, which the old writer saves in the binary form
    data2 = open(REAL2, "rb").read()
    try:
        m2 = tg.parse_image(data2)
    except Exception as e:  # noqa: BLE001
        check("A5 the second real image parses", False, "%s: %s" % (type(e).__name__, e))
        m2 = None
    if m2 is not None:
        IMk, FMk = tg.IM, tg.FM
        want = {b"BIN1": b"abc" + IMk + b"def" + FMk + b"x", b"BIN2": b"z" * 1500 + IMk + b"y" * 10, b"BIN3": IMk,
                b"BIN4": b"a" + IMk + IMk + b"b", b"BIN5": b"q" * 999 + IMk, b"BIN6": b"tail" + IMk + b"X" + IMk + b"\x82FF",
                b"BIN7": b"w" * 998 + IMk + b"k" + FMk + b"second field"}
        got = dict((i["id"], i) for i in m2["items"] if i["kind"] == "O")
        # the eighth is the object code of FIXBIN itself, in BP.OUT: compiled code holds item marks too
        check("A5a the second real image holds the seven binary records and the object code of the program that made them",
              sorted(got) == sorted(list(want) + [b"FIXBIN"]) and got.get(b"FIXBIN", {}).get("num") != b"180", "got %r" % sorted(got))
        check("A5b each binary item comes back with its data and no padding",
              all(got.get(k, {}).get("data") == v for k, v in want.items()),
              "; ".join("%s %d/%d" % (k.decode(), len(got.get(k, {}).get("data", b"")), len(v)) for k, v in want.items() if got.get(k, {}).get("data") != v))
        check("A5c the block counts are the old writer's (1000 bytes exactly is one block, 1001 two)",
              [got.get(k, {}).get("blocks") for k in (b"BIN1", b"BIN2", b"BIN3", b"BIN4", b"BIN5", b"BIN6", b"BIN7")] == [1, 2, 1, 1, 1, 1, 2])
        try:
            again2 = tg.build_image(m2)
        except Exception as e:  # noqa: BLE001
            again2 = b""
            check("A5d the writer rebuilds the second real image", False, "%s: %s" % (type(e).__name__, e))
        else:
            first = next((k for k in range(min(len(again2), len(data2))) if again2[k] != data2[k]), None)
            check("A5d the writer rebuilds the second real image byte for byte (%d bytes)" % len(data2), again2 == data2,
                  "lengths %d/%d, first difference at %s" % (len(again2), len(data2), first))
        keys1 = set((i["num"], i["id"]) for i in ii)
        keys2 = set((i["num"], i["id"]) for i in m2["items"] if i["kind"] == "I")
        check("A5e the second image holds the same 13 headers and every ordinary item of the first",
              len([i for i in m2["items"] if i["kind"] == "D"]) == 13 and keys1 <= keys2, "%d of %d items missing" % (len(keys1 - keys2), len(keys1)))

    # ---- 2. the recipes
    codes_used = set()
    for name, (build, verdict, opts) in sorted(tg.RECIPES.items()):
        try:
            img = build()
        except Exception as e:  # noqa: BLE001
            check("B %s: the recipe builds" % name, False, "%s: %s" % (type(e).__name__, e))
            continue
        try:
            got = tg.parse_image(img, **opts)
            result = "parses"
            again = tg.build_image(got)
            rt = (again == img)
        except tg.TapeError as e:
            got, result, rt = None, e.code, True
        except Exception as e:  # noqa: BLE001
            got, result, rt = None, "CRASH %s: %s" % (type(e).__name__, e), True
        want = verdict or "parses"
        if verdict:
            codes_used.add(verdict)
        check("B %-28s %6d bytes -> %s (want %s)" % (name, len(img), result, want), result == want)
        if verdict is None:
            check("B %-28s parse then build gives the same bytes" % name, rt)
    src = open(tg.__file__, encoding="utf-8").read()
    in_reader = set(re.findall(r'TapeError\("(R-[A-Z]+)"', src))
    check("B0 every refusal code the reader can give has a recipe", in_reader <= codes_used,
          "no recipe for %s" % sorted(in_reader - codes_used))

    # ---- the file route: the size is asked of the file system first
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "sparse.img")
        size = (2 << 30) if big else (64 << 20)
        with open(p, "wb") as fu:
            fu.truncate(size)
        os.chmod(p, 0)       # unreadable: a reader that opens it before it asks the size fails with something else than R-IMAGESIZE
        try:
            tg.parse_path(p, max_image=(1 << 30) if big else (16 << 20))
            r = "parses"
        except tg.TapeError as e:
            r = e.code
        except Exception as e:  # noqa: BLE001
            r = "CRASH %s" % type(e).__name__
        check("B1 a sparse image of %d MB is refused as R-IMAGESIZE before it is read" % (size >> 20), r == "R-IMAGESIZE", r)
        good = os.path.join(d, "good.img")
        open(good, "wb").write(tg.RECIPES["ok-small"][0]())
        check("B2 parse_path reads an ordinary image", len(tg.parse_path(good)["items"]) == 6)

    # ---- 3. the name layer
    for raw, why in tg.HOSTILE_NAMES:
        check("C name %-14r is refused as %s" % (raw[:14], why), tg.name_verdict(raw) == why, "got %r" % tg.name_verdict(raw))
    for raw in tg.GOOD_NAMES:
        check("C name %-14r is accepted" % raw[:14], tg.name_verdict(raw) is None, "got %r" % tg.name_verdict(raw))
    kept, dropped = tg.fold_names([b"Jack", b"JACK", b"jill", b"jack", b"Jill"])
    check("C fold keeps the first of each", kept == [b"Jack", b"jill"] and dropped == [b"JACK", b"jack", b"Jill"], "%r %r" % (kept, dropped))
    return res


# (name, old text, new text) - each old text occurs exactly once in tapegen.py
MUTANTS = [
    ("blocksize check out", 'if m.group(1) != BLOCKSIZE_FIELD:', 'if False:'),
    ("level range widened", 'if f[1] not in (b"1", b"2", b"3"):', 'if f[1] not in (b"0", b"1", b"2", b"3", b"4"):'),
    ("unknown item type skipped", 'raise TapeError("R-BLOCKTYPE", "an item of unknown type %r" % t[:4])', 'continue'),
    ("end-of-account check out", 'if not done:', 'if False:'),
    ("binary: length rule loosened", 'if ln < 1 or ln > nblocks * BINBLK or (nblocks > 1 and ln <= (nblocks - 1) * BINBLK):', 'if ln < 1:'),
    ("binary: padding unchecked", 'if raw[ln:].strip(b"\\x00"):', 'if False:'),
    ("binary: trailer searched for", 'tm = O_TRAIL.match(stream, dend) if dend <= size else None', 'tm = O_TRAIL.search(stream, dstart)'),
    ("binary: block cap out", 'if nblocks * BINBLK > max_item:', 'if False:'),
    ("binary: zero blocks allowed", 'if nblocks < 1:', 'if False:'),
    ("binary: file header unchecked", 'if num not in files:', 'if False:'),
    ("binary: length read as hex", 'BINLEN_BASE = 10', 'BINLEN_BASE = 16'),
    ("file number check out", 'if not DIGITS.fullmatch(f[2]):', 'if False:'),
    ("file cap out", 'if len(files) > max_files:', 'if False:'),
    ("item cap out", 'if len(tok) > max_item:', 'if False:'),
    ("image cap out", 'if len(data) > max_image:', 'if False:'),
    ("file-size asked after the open", 'size = os.path.getsize(path)\n    if size > max_image:\n        raise TapeError("R-IMAGESIZE", "%d bytes" % size)\n    with open(path, "rb") as fu:',
     'with open(path, "rb") as fu:\n        size = 0'),
    ("item without header allowed", 'if f[0][1:] not in files:', 'if False:'),
    ("pad changed", 'PAD = 12 ', 'PAD = 13 '),
    ("item length rule changed", 'len(rec) + 1 - 6', 'len(rec) + 1 - 5'),
    ("header length rule changed", '(25 if it["level"] == b"1" else 19)', '19'),
    ("trailing field mark kept", 'if rest and rest[-1] == b"":', 'if False:'),
    ("descriptor check out", 'if _payload(blks[3], "block 3")[:7] != IM + b"M65" + IM + b"XC" or', 'if False and _payload(blks[3], "block 3")[:7] != IM + b"M65" + IM + b"XC" or'),
    ("blocks after end allowed", 'if end != len(blks) - 1:', 'if False:'),
    ("bytes after end mark allowed", 'if tok[2:].strip(b" "):', 'if False:'),
    ("missing end-of-file block allowed", 'if end is None:', 'if False:'),
    ("short image allowed", 'if len(data) % PHYS:', 'if False:'),
    ("pad check out", 'if blk[:PAD] != b"\\x00" * PAD:', 'if False:'),
    ("name: .. allowed", 'if raw == b"..":', 'if False:'),
    ("name: slash allowed", 'if b"/" in raw:', 'if False:'),
    ("name: NUL allowed", 'if b"\\x00" in raw:', 'if False:'),
    ("name: high bytes allowed", 'if c > 127:', 'if c > 247:'),
    ("name: length unchecked", 'if len(raw) > maxlen:', 'if len(raw) > maxlen + 1000:'),
    ("name: leading dot allowed", 'if raw[:1] == b".":', 'if False:'),
    ("fold keeps everything", 'if k in seen:', 'if False:'),
    ("fold keeps the last", 'dropped.append(n)', 'dropped.append(kept.pop(kept.index(seen[k]))); seen[k] = n; kept.append(n)'),
]


def report(res, quiet=False):
    failed = [r for r in res if not r[1]]
    if not quiet:
        for label, ok, detail in res:
            print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label, ("  " + detail) if (detail and not ok) else ""))
    return failed


def main(argv):
    for img in (REAL, REAL2):
        if not os.path.isfile(img) or os.path.getsize(img) == 0:
            print("CANNOT RUN: the reference image %s is missing or empty; nothing was checked." % img)
            return 2
    print("test-tapeimg-units: images %s (%d bytes) and %s (%d bytes), module %s" % (REAL, os.path.getsize(REAL), REAL2, os.path.getsize(REAL2), SRC))
    tg = load(SRC, "tapegen_real")
    res = run_checks(tg, big=True)
    failed = report(res)
    print("%d passed, %d failed" % (len(res) - len(failed), len(failed)))
    if failed:
        return 1
    if "--selftest" not in argv:
        return 0
    text = open(SRC, encoding="utf-8").read()
    survivors = []
    with tempfile.TemporaryDirectory() as d:
        for n, (name, old, new) in enumerate(MUTANTS):
            if text.count(old) != 1:
                print("  [BAD ] mutant %d (%s): the old text occurs %d times" % (n, name, text.count(old)))
                survivors.append(name)
                continue
            p = os.path.join(d, "tapegen_m%d.py" % n)
            open(p, "w", encoding="utf-8").write(text.replace(old, new))
            try:
                mod = load(p, "tapegen_m%d" % n)
                bad = report(run_checks(mod, big=False), quiet=True)
            except Exception as e:  # noqa: BLE001 - a mutant that cannot even run is killed
                bad = [("crash", False, str(e))]
            print("  [%s] mutant %2d %-36s %s" % ("KILL" if bad else "LIVE", n, name, ("%d check(s) failed, first: %s" % (len(bad), bad[0][0][:50])) if bad else ""))
            if not bad:
                survivors.append(name)
    print("%d mutants, %d survived" % (len(MUTANTS), len(survivors)))
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
