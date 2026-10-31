#!/usr/bin/env python3
"""tapegen.py - pseudo-tape images for TAPE.IMPORT (S.92, stage S1): a writer, a strict reference reader, the name rules.

WHAT IT IS.  TAPE.IMPORT reads a save image written by the old ACCOUNT.SAVE of the deleted tape subsystem (or by a Pick-family
system).  The only independent producer here is the old code itself: `.claude/tape-ref/as-ref-1.img` was written by it on 30 Oct 2026
(README beside it).  This module holds, in one place:
  1. the byte constants of the AS layout, every one of them OBSERVED in that image (not only read from the old source);
  2. build_image(model)  - writes an AS image from a model;
  3. parse_image(data)   - reads one back, STRICTLY: it refuses what it does not understand with a named verdict (R-...);
  4. name_verdict() and fold_names() - the English-only name layer (owner, 30 Oct: ids, file names and account names only);
  5. RECIPES             - synthetic and hostile images with the verdict each must give.
The BASIC reader that ships (`!tapeimg`, stage S2) must give the same verdicts; its sandbox suite reads these images.

WHAT IT CANNOT PROVE.  parse_image(build_image(m)) == m proves the pair agree; the round trip of the REAL image
(build_image(parse_image(real)) == real, byte for byte) proves the writer matches the old writer for everything that image holds.
Neither says a Pick system writes the same bytes.  Layouts other than the 3-label AS one, and the binary item forms (O, B), are
REFUSED here (R-LAYOUT, R-UNSUPPORTED) until an image exists to read them from.

  python3 tapegen.py list                  the recipes and their verdicts
  python3 tapegen.py make NAME OUT         write one recipe's image
  python3 tapegen.py roundtrip IMAGE       parse IMAGE, rebuild it, say whether the bytes are equal
"""

import os
import re
import sys

IM, FM, VM, SM, TM = b"\xff", b"\xfe", b"\xfd", b"\xfc", b"\xfb"
PAD = 12                  # NUL bytes in front of every payload
BLKSZ = 500               # payload bytes of a block
PHYS = PAD + BLKSZ        # a physical block
LABEL_FM_AT = 77          # offset, in the payload, of the field mark that ends a label's text
BLOCKSIZE_FIELD = b"01F4"  # 500 in hex, what the old writer put in a label

MAX_IMAGE = 1 << 30       # caps a caller may raise (decision 7 of 30 Oct)
MAX_ITEM = 16 << 20
MAX_FILES = 10000
MAX_NAME = 64


class TapeError(Exception):
    """A refusal.  .code is the verdict (R-...), str() is the sentence."""

    def __init__(self, code, text=""):
        Exception.__init__(self, code + (": " + text if text else ""))
        self.code = code


# ---------------------------------------------------------------------------------------------------------------------------
# The writer.

def frame(payload, fill=b"\x00"):
    if len(payload) > BLKSZ:
        raise ValueError("payload of %d bytes" % len(payload))
    return b"\x00" * PAD + payload + fill * (BLKSZ - len(payload))


def label_block(lab, tail):
    """lab: dict(time, date, reel); tail: the text after DATA."""
    text = IM + b"L " + BLOCKSIZE_FIELD + b" " + lab["time"] + b"  " + lab["date"] + b" DATA " + tail
    text = text.ljust(LABEL_FM_AT, b" ") + FM + lab["reel"]
    return frame(text)


def eof_block():
    return b"EOF" + IM + b"\x00" * (PHYS - 4)       # the only block with no pad in front


def descriptor_block():
    return frame(IM + b"M65" + IM + b"XC", b" ")


def d_token(it):
    attrs = FM.join(it["attrs"])
    head = b"D" + FM + it["level"] + FM + it["num"] + FM
    name = it["name"]
    if it.get("llll") is not None:
        llll = it["llll"]
    else:
        # observed: the 4 digits are the token's length less 19 (less 25 for the account's own header)
        llll = len(head + b"0000" + name + FM + attrs) - (25 if it["level"] == b"1" else 19)
    return head + b"%04d" % llll + name + FM + attrs


def i_token(it):
    rec = it["id"] + (FM + FM.join(it["fields"]) if it["fields"] else b"")
    body = b"I" + it["num"] + FM + it["group"] + FM
    if it.get("llll") is not None:
        llll = it["llll"]
    else:
        # observed on 962 of 963 items: the token's length less 6 (the 963rd, the account's own copy of UMASK, is one less)
        llll = len(body) + 4 + len(rec) + 1 - 6
    return body + b"%04d" % llll + rec + FM


def stream_bytes(model):
    out = b""
    for it in model["items"]:
        out += IM + (d_token(it) if it["kind"] == "D" else i_token(it))
    return out + IM + b"XX"


def build_image(model):
    lab = model["label"]
    stream = stream_bytes(model)
    blocks = [label_block(lab, lab["account"]), eof_block(), label_block(lab, lab["account"]), descriptor_block(),
              label_block(lab, lab["account"] + b" " + lab["account"])]
    for i in range(0, len(stream), BLKSZ):
        blocks.append(frame(stream[i:i + BLKSZ], b" "))
    blocks.append(eof_block())
    return b"".join(blocks)


# ---------------------------------------------------------------------------------------------------------------------------
# The reader.

LABEL_RE = re.compile(rb"\xffL ([0-9A-F]{4}) (\d\d:\d\d:\d\d)  (\d\d [A-Za-z]{3} \d{4}) DATA ([!-~]+)(?: ([!-~]+))? *\xfe(\d\d)")
DIGITS = re.compile(rb"[0-9]{1,9}")


def _payload(blk, what):
    if blk[:PAD] != b"\x00" * PAD:
        raise TapeError("R-PAD", "%s has no pad" % what)
    return blk[PAD:]


def _is_eof(blk):
    return blk[:4] == b"EOF" + IM and blk[4:] == b"\x00" * (PHYS - 4)


def _label(blk, n):
    pl = _payload(blk, "block %d" % n).rstrip(b"\x00")
    m = LABEL_RE.fullmatch(pl)
    if not m:
        raise TapeError("R-LABEL", "block %d is not a label" % n)
    if m.group(1) != BLOCKSIZE_FIELD:
        raise TapeError("R-BLOCKSIZE", "block size field %s" % m.group(1).decode())
    return {"time": m.group(2), "date": m.group(3), "account": m.group(4), "second": m.group(5), "reel": m.group(6)}


def parse_image(data, max_image=MAX_IMAGE, max_item=MAX_ITEM, max_files=MAX_FILES):
    if len(data) > max_image:
        raise TapeError("R-IMAGESIZE", "%d bytes" % len(data))
    if len(data) == 0:
        raise TapeError("R-EMPTY")
    if len(data) % PHYS:
        raise TapeError("R-SHAPE", "%d bytes is not a whole number of %d byte blocks" % (len(data), PHYS))
    blks = [data[i:i + PHYS] for i in range(0, len(data), PHYS)]
    if len(blks) < 6:
        raise TapeError("R-SHAPE", "%d blocks" % len(blks))
    lab = _label(blks[0], 0)
    if not _is_eof(blks[1]):
        raise TapeError("R-LAYOUT", "block 1 is not an end-of-file block")
    lab2 = _label(blks[2], 2)
    if _payload(blks[3], "block 3")[:7] != IM + b"M65" + IM + b"XC" or _payload(blks[3], "block 3")[7:] != b" " * (BLKSZ - 7):
        raise TapeError("R-LAYOUT", "block 3 is not the descriptor")
    lab3 = _label(blks[4], 4)
    if lab3["second"] != lab3["account"] or lab2["account"] != lab["account"] or lab3["account"] != lab["account"]:
        raise TapeError("R-LAYOUT", "the three labels name different accounts")
    end = None
    for n in range(5, len(blks)):
        if _is_eof(blks[n]):
            end = n
            break
    if end is None:
        raise TapeError("R-NOEOF", "no end-of-file block after the data")
    if end != len(blks) - 1:
        raise TapeError("R-TRAILING", "blocks after the end-of-file block")
    stream = b"".join(_payload(blks[n], "block %d" % n) for n in range(5, end))
    cut = stream.find(IM + b"XX")
    if cut < 0:
        raise TapeError("R-NOEND", "the data has no end-of-account mark")
    if stream[cut + 3:].strip(b" "):
        raise TapeError("R-TRAILING", "bytes after the end-of-account mark")
    body = stream[:cut]
    items = []
    files = {}
    if body:
        if body[:1] != IM:
            raise TapeError("R-STREAM", "the data does not start with an item mark")
        for tok in body.split(IM)[1:]:
            if len(tok) > max_item:
                raise TapeError("R-ITEMCAP", "an item of %d bytes" % len(tok))
            t = tok[:1]
            f = tok.split(FM)
            if t == b"D":
                if len(f) < 6 or f[0] != b"D":
                    raise TapeError("R-HEADER", "a file header with %d fields" % len(f))
                if f[1] not in (b"1", b"2", b"3"):
                    raise TapeError("R-LEVEL", "level %r" % f[1][:8])
                if not DIGITS.fullmatch(f[2]):
                    raise TapeError("R-FILENUM", "file number %r" % f[2][:12])
                if not re.fullmatch(rb"[0-9]{4}.*", f[3], re.S):
                    raise TapeError("R-HEADER", "no length in front of the file name")
                it = {"kind": "D", "level": f[1], "num": f[2], "name": f[3][4:], "attrs": f[4:], "llll": int(f[3][:4])}
                files[f[2]] = it
                if len(files) > max_files:
                    raise TapeError("R-FILECAP", "more than %d files" % max_files)
            elif t == b"I":
                if len(f) < 4 or not DIGITS.fullmatch(f[0][1:]):
                    raise TapeError("R-HEADER", "an item header with %d fields" % len(f))
                if not DIGITS.fullmatch(f[1]):
                    raise TapeError("R-FILENUM", "group %r" % f[1][:12])
                if f[0][1:] not in files:
                    raise TapeError("R-NOFILE", "an item for file %s, which has no header" % f[0][1:].decode())
                if not re.fullmatch(rb"[0-9]{4}.*", f[2], re.S):
                    raise TapeError("R-HEADER", "no length in front of the record id")
                rest = f[3:]
                if rest and rest[-1] == b"":
                    rest = rest[:-1]
                it = {"kind": "I", "num": f[0][1:], "group": f[1], "id": f[2][4:], "fields": rest, "llll": int(f[2][:4])}
            elif t in (b"O", b"B", b"L", b"R", b"H", b"F", b"E"):
                raise TapeError("R-UNSUPPORTED", "an item of type %s" % t.decode())
            else:
                raise TapeError("R-BLOCKTYPE", "an item of unknown type %r" % t[:4])
            items.append(it)
    return {"label": {"time": lab["time"], "date": lab["date"], "account": lab["account"], "reel": lab["reel"]},
            "items": items, "blocks": len(blks)}


def parse_path(path, max_image=MAX_IMAGE, **caps):
    """parse_image on a file, the size asked of the file system BEFORE anything is read (a sparse 2 GB image costs nothing)."""
    size = os.path.getsize(path)
    if size > max_image:
        raise TapeError("R-IMAGESIZE", "%d bytes" % size)
    with open(path, "rb") as fu:
        return parse_image(fu.read(), max_image=max_image, **caps)


# ---------------------------------------------------------------------------------------------------------------------------
# The name layer: English only, and nothing that can leave the staging directory.

def name_verdict(raw, maxlen=MAX_NAME):
    """None when the name may be used, else the reason (a word the log prints)."""
    if raw == b"":
        return "empty"
    if raw == b".":
        return "dot"
    if raw == b"..":
        return "dotdot"
    if b"\x00" in raw:
        return "nul"
    if b"/" in raw:
        return "slash"
    if raw[:1] == b".":
        return "leading-dot"
    if len(raw) > maxlen:
        return "too-long"
    for c in raw:
        if c < 32 or c == 127:
            return "control"
        if c > 127:
            return "high-byte"
    return None


def fold_names(names):
    """Fold case like the files do and keep the FIRST of any that collide: (kept, dropped)."""
    seen = {}
    kept = []
    dropped = []
    for n in names:
        k = n.lower()
        if k in seen:
            dropped.append(n)
        else:
            seen[k] = n
            kept.append(n)
    return kept, dropped


# ---------------------------------------------------------------------------------------------------------------------------
# Models and recipes.

def small_model(account=b"DEMO", records=3):
    lab = {"time": b"09:30:00", "date": b"30 Oct 2026", "account": account, "reel": b"01"}
    attrs = lambda base, mod: [b"D", base, mod, b"", b"", b"", b"", b"", b"L", b"10", b""]
    items = [
        {"kind": "D", "level": b"1", "num": b"100", "name": account, "attrs": [b"D", b"101", b"101", b"", b"", b"", b"", b"SYS2", b"L", b"12", b""]},
        {"kind": "D", "level": b"2", "num": b"101", "name": b"CUST", "attrs": attrs(b"101", b"1")},
        {"kind": "D", "level": b"3", "num": b"102", "name": b"CUST", "attrs": attrs(b"101", b"1")},
    ]
    for i in range(records):
        items.append({"kind": "I", "num": b"102", "group": b"103", "id": b"C%03d" % (i + 1), "fields": [b"Name " + str(i).encode(), b"x"]})
    return {"label": lab, "items": items}


def _with(model, **changes):
    m = {"label": dict(model["label"]), "items": [dict(i) for i in model["items"]]}
    m.update(changes)
    return m


def _patch_header(model, index, **fields):
    m = _with(model)
    m["items"][index] = dict(m["items"][index], **fields)
    return m


def _stream_image(stream, label_account=b"DEMO"):
    """An image whose data stream is exactly `stream` (for what build_image will not write)."""
    lab = small_model(label_account)["label"]
    blocks = [label_block(lab, lab["account"]), eof_block(), label_block(lab, lab["account"]), descriptor_block(),
              label_block(lab, lab["account"] + b" " + lab["account"])]
    for i in range(0, len(stream), BLKSZ):
        blocks.append(frame(stream[i:i + BLKSZ], b" "))
    blocks.append(eof_block())
    return b"".join(blocks)


def _valid_stream():
    return stream_bytes(small_model())


def _replace_in_image(data, old, new):
    assert data.count(old) == 1, (old, data.count(old))
    return data.replace(old, new)


def _random_bytes(n):
    x = 20261030
    out = bytearray()
    for _ in range(n):
        x = (x * 1103515245 + 12345) & 0x7FFFFFFF
        out.append((x >> 16) & 0xFF)
    return bytes(out)


def _many_files(n):
    m = small_model(records=0)
    base = m["items"][:1]
    for i in range(n):
        base.append({"kind": "D", "level": b"2", "num": b"%d" % (1000 + i), "name": b"F%d" % i,
                     "attrs": [b"D", b"101", b"1", b"", b"", b"", b"", b"", b"L", b"10", b""]})
    m["items"] = base
    return build_image(m)


def _big_item():
    m = small_model(records=0)
    m["items"].append({"kind": "I", "num": b"102", "group": b"103", "id": b"BIG", "fields": [b"z" * 40000]})
    return build_image(m)


def _bad_blocksize(code):
    return build_image(small_model()).replace(b"L 01F4 ", b"L " + code + b" ")


# name -> (builder, verdict or None when it must parse, reader options).
RECIPES = {
    "ok-small": (lambda: build_image(small_model()), None, {}),
    "ok-empty-account": (lambda: build_image(small_model(records=0)), None, {}),
    "ok-long-record": (lambda: build_image(_with(small_model(records=0), items=small_model(records=0)["items"] +
                       [{"kind": "I", "num": b"102", "group": b"103", "id": b"LONG", "fields": [b"line %d " % i + b"y" * 60 for i in range(60)]}])), None, {}),
    "ok-marks-and-high-byte": (lambda: build_image(_with(small_model(records=0), items=small_model(records=0)["items"] +
                       [{"kind": "I", "num": b"102", "group": b"103", "id": b"C 9", "fields": [b"a" + VM + b"b" + SM + b"c", b"caf\xe9", b""]}])), None, {}),
    "empty": (lambda: b"", "R-EMPTY", {}),
    "random-bytes": (lambda: _random_bytes(PHYS * 8), "R-PAD", {}),
    "label-text-garbage": (lambda: b"\x00" * PAD + b"not a label".ljust(BLKSZ, b"\x00") + build_image(small_model())[PHYS:], "R-LABEL", {}),
    "random-odd-length": (lambda: _random_bytes(1000), "R-SHAPE", {}),
    "truncated-mid-block": (lambda: build_image(small_model())[:-100], "R-SHAPE", {}),
    "truncated-at-block-boundary": (lambda: build_image(small_model())[:-PHYS], "R-NOEOF", {}),
    "no-end-mark": (lambda: _stream_image(_valid_stream()[:-3] + b"   "), "R-NOEND", {}),
    "blocks-after-eof": (lambda: build_image(small_model()) + frame(b"x"), "R-TRAILING", {}),
    "stream-not-starting-with-mark": (lambda: _stream_image(b"junk" + IM + b"XX"), "R-STREAM", {}),
    "file-header-too-short": (lambda: _stream_image(IM + b"D" + FM + b"1" + IM + b"XX"), "R-HEADER", {}),
    "file-header-without-length": (lambda: _stream_image(IM + b"D" + FM + b"1" + FM + b"5" + FM + b"name" + FM + b"D" + FM + b"1" + FM + b"1" + FM + IM + b"XX"),
                                   "R-HEADER", {}),
    "bytes-after-end-mark": (lambda: _stream_image(_valid_stream() + b"junk"), "R-TRAILING", {}),
    "blocksize-ffff": (lambda: _bad_blocksize(b"FFFF"), "R-BLOCKSIZE", {}),
    "blocksize-0000": (lambda: _bad_blocksize(b"0000"), "R-BLOCKSIZE", {}),
    "level-4": (lambda: build_image(_patch_header(small_model(), 1, level=b"4")), "R-LEVEL", {}),
    "level-0": (lambda: build_image(_patch_header(small_model(), 1, level=b"0")), "R-LEVEL", {}),
    "filenum-ffffffff": (lambda: build_image(_patch_header(small_model(), 1, num=b"FFFFFFFF")), "R-FILENUM", {}),
    "filenum-20-digits": (lambda: build_image(_patch_header(small_model(), 1, num=b"9" * 20)), "R-FILENUM", {}),
    "item-without-header": (lambda: build_image(_patch_header(small_model(), 3, num=b"555")), "R-NOFILE", {}),
    "unknown-item-type": (lambda: _stream_image(_valid_stream()[:-3] + IM + b"Z" + FM + b"junk" + IM + b"XX"), "R-BLOCKTYPE", {}),
    "stray-item-mark": (lambda: _stream_image(_valid_stream()[:-3] + IM + IM + b"XX"), "R-BLOCKTYPE", {}),
    "binary-item-form": (lambda: _stream_image(_valid_stream()[:-3] + IM + b"O" + FM + b"x" + IM + b"XX"), "R-UNSUPPORTED", {}),
    "third-label-names-another": (lambda: build_image(small_model()).replace(b"DATA DEMO DEMO", b"DATA DEMO OTHR"), "R-LAYOUT", {}),
    "descriptor-missing": (lambda: _replace_in_image(build_image(small_model()), IM + b"M65" + IM + b"XC", IM + b"M66" + IM + b"XC"), "R-LAYOUT", {}),
    "item-over-cap": (lambda: _big_item(), "R-ITEMCAP", {"max_item": 30000}),
    "files-over-cap": (lambda: _many_files(1001), "R-FILECAP", {"max_files": 1000}),
    "files-at-cap": (lambda: _many_files(999), None, {"max_files": 1000}),
    "image-over-cap": (lambda: build_image(small_model()), "R-IMAGESIZE", {"max_image": PHYS * 5}),
}

# Names the name layer must refuse, and one it must accept.
HOSTILE_NAMES = [(b"../../etc/x", "slash"), (b"..", "dotdot"), (b".", "dot"), (b"a/b", "slash"), (b"a\x00b", "nul"), (b"", "empty"),
                 (b".hidden", "leading-dot"), (b"caf\xe9", "high-byte"), (b"tab\there", "control"), (b"x" * 65, "too-long")]
GOOD_NAMES = [b"CUST", b"C 002", b"O100", b"VOC", b"x" * 64]


def main(argv):
    if len(argv) >= 2 and argv[1] == "list":
        for name, (build, verdict, opts) in RECIPES.items():
            print("%-28s %-14s %s" % (name, verdict or "parses", opts or ""))
        return 0
    if len(argv) == 4 and argv[1] == "make" and argv[2] in RECIPES:
        data = RECIPES[argv[2]][0]()
        open(argv[3], "wb").write(data)
        print("wrote %d bytes to %s" % (len(data), argv[3]))
        return 0
    if len(argv) == 3 and argv[1] == "roundtrip":
        data = open(argv[2], "rb").read()
        again = build_image(parse_image(data))
        print("image %d bytes, rebuilt %d bytes, %s" % (len(data), len(again), "IDENTICAL" if again == data else "DIFFERENT"))
        return 0 if again == data else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
