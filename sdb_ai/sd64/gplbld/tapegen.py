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
Neither says a Pick system writes the same bytes.

OTHER LAYOUTS (stage S4a, 30 Oct 2026).  `layout=` takes r83, jbs, fs or mv besides as.  They are READ AS THE ORIGINAL READER READ THEM and NO REAL IMAGE OF ANY OF THEM HAS
BEEN SEEN (the owner has none; he vouches for the old code): what is built is the label count it positioned for (r83 two, jbs / fs / mv one), a label that only has to start
`IM L SP size SP` and carry some text, a pad of NULs or SPACEs (mvBase's has spaces) or none (size field 0200), file numbers and groups in hex, an `IM H` header token that is
skipped (mv), item types F and E that are read like I, and an end mark of X, XX or XC.  The account is named by the first file header (level 1) of the data, where ACCOUNT.RESTORE
took it from, not by the label.  REFUSED with a reason: ultfs (SETDEV counts two labels before the data, ACCRST reads three), and the item forms L (two possible shapes in the old
code), B, R and the foreign O form (their ends depend on the old code's own "fragile" arithmetic), T-DUMP streams.  Only AS is checked against an image another program wrote.

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
BLOCKSIZE_FLAT = b"0200"   # 512 in hex: an image with no pad (the old reader took pad = 0 for every size but 500)
LAYOUTS = {"as": 3, "r83": 2, "jbs": 1, "fs": 1, "mv": 1}     # the labels each layout reads before its data
LAYOUT_REFUSED = ("ultfs",)                                     # a word the owner may use, and a layout this reader will not guess

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

def frame(payload, fill=b"\x00", flat=False):
    if flat:
        if len(payload) > PHYS:
            raise ValueError("payload of %d bytes" % len(payload))
        return payload + fill * (PHYS - len(payload))
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


def generic_label_block(text, flat=False):
    """A label of a layout other than AS: IM L SP size SP text, NUL padded.  Nothing more is required of the text."""
    return frame(IM + b"L " + (BLOCKSIZE_FLAT if flat else BLOCKSIZE_FIELD) + b" " + text, flat=flat)


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
    body = it.get("tag", b"I") + it["num"] + FM + it["group"] + FM
    if it.get("llll") is not None:
        llll = it["llll"]
    else:
        # observed on 962 of 963 items: the token's length less 6 (the 963rd, the account's own copy of UMASK, is one less)
        llll = len(body) + 4 + len(rec) + 1 - 6
    return body + b"%04d" % llll + rec + FM


def h_token(it):
    return b"H" + it["text"]


def o_token(it):
    blocks = it.get("blocks") or max(1, (len(it["data"]) + BINBLK - 1) // BINBLK)
    return (b"I" + it["num"] + FM + it["group"] + FM + b"O%d" % blocks + FM + it["id"] + FM +
            it["data"].ljust(blocks * BINBLK, b"\x00") + IM + IM + IM + b"X" + IM + b"\x82" + b"%d" % len(it["data"]))


def stream_bytes(model, end=b"XX"):
    out = b""
    for it in model["items"]:
        out += IM + {"D": d_token, "I": i_token, "O": o_token, "H": h_token}[it["kind"]](it)
    return out + IM + end


def gen_image(stream, lab, layout, flat=False, eofs=1):
    """An image of a layout other than AS whose data stream is exactly `stream`: the layout's labels with `eofs` end-of-file blocks between them, the data, an end-of-file block."""
    text = lab["time"] + b" " + lab["date"] + b" DATA " + lab["account"]
    blocks = [generic_label_block(text, flat)]
    for _ in range(LAYOUTS[layout] - 1):
        blocks += [eof_block()] * eofs + [generic_label_block(text, flat)]
    pay = PHYS if flat else BLKSZ
    for i in range(0, len(stream), pay):
        blocks.append(frame(stream[i:i + pay], b" ", flat=flat))
    blocks.append(eof_block())
    return b"".join(blocks)


def build_image(model, layout="as", flat=False, eofs=1, end=b"XX"):
    """layout 'as' is what the old ACCOUNT.SAVE wrote (flat, eofs and end are ignored); any other layout is gen_image of the model's stream."""
    lab = model["label"]
    stream = stream_bytes(model, end)
    if layout != "as":
        return gen_image(stream, lab, layout, flat, eofs)
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
# the other layouts: file numbers and groups are hex (the old reader converted them with MCXD), the length in front of a name is 4 hex digits,
# and a label is only `IM L SP size SP text` (printable bytes and at most field marks), the text is not looked at
KEYS_HEX = re.compile(rb"[0-9A-F]{1,9}")
LEN_DEC = re.compile(rb"[0-9]{4}.*", re.S)
LEN_HEX = re.compile(rb"[0-9A-F]{4}.*", re.S)
GEN_LABEL_RE = re.compile(rb"\xffL ([0-9A-F]{4}) ([\x20-\x7e\xfe]*)")
# The binary form of an item (the old writer used it for any record holding an item mark), observed in as-ref-2.img:
#   IM I<num> FM <group> FM O<blocks> FM <id> FM <data, padded with NUL to 1000 * blocks bytes> IM IM IM X IM \x82 <true length> IM ...
# The data may itself hold IM, FM, even a copy of the trailer, so the end is found by the block count, never by a search.
O_HEAD = re.compile(rb"\xffI([0-9]{1,9})\xfe([0-9]{1,9})\xfeO([0-9]{1,9})\xfe([^\xfe\xff]*)\xfe")
O_TRAIL = re.compile(rb"\xff\xff\xffX\xff\x82([0-9]{1,9})(?=\xff)")
BINBLK = 1000
# The old writer meant the numbers of this form to be hex (it called oconv(n, "MCDX")) and wrote DECIMAL digits: in its image 1511 is 1511.
# A Pick system's image would hold hex; only decimal has been seen, so decimal is what is read until an image says otherwise.
BINLEN_BASE = 10


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


def _gen_payload(blk, flat, what):
    """The payload of a block of a layout other than AS: the whole block when there is no pad, else what follows a pad of NULs and SPACEs."""
    if flat:
        return blk
    if blk[:PAD].strip(b"\x00 "):
        raise TapeError("R-PAD", "%s has no pad" % what)
    return blk[PAD:]


def _gen_label(blk, flat, n):
    pl = _gen_payload(blk, flat, "block %d" % n).rstrip(b"\x00")
    m = GEN_LABEL_RE.fullmatch(pl)
    if not m or not m.group(2).strip(b" "):
        raise TapeError("R-LABEL", "block %d is not a label" % n)
    if m.group(1) != (BLOCKSIZE_FLAT if flat else BLOCKSIZE_FIELD):
        raise TapeError("R-BLOCKSIZE", "block size field %s" % m.group(1).decode())


def parse_image(data, max_image=MAX_IMAGE, max_item=MAX_ITEM, max_files=MAX_FILES, layout="as"):
    if layout not in LAYOUTS:
        raise TapeError("R-UNSUPPORTED" if layout in LAYOUT_REFUSED else "R-FORMAT", "layout %s" % layout)
    gen = layout != "as"
    if len(data) > max_image:
        raise TapeError("R-IMAGESIZE", "%d bytes" % len(data))
    if len(data) == 0:
        raise TapeError("R-EMPTY")
    if len(data) % PHYS:
        raise TapeError("R-SHAPE", "%d bytes is not a whole number of %d byte blocks" % (len(data), PHYS))
    blks = [data[i:i + PHYS] for i in range(0, len(data), PHYS)]
    if len(blks) < (LAYOUTS[layout] + 2 if gen else 6):
        raise TapeError("R-SHAPE", "%d blocks" % len(blks))
    flat = False
    if not gen:
        lab = _label(blks[0], 0)
        if not _is_eof(blks[1]):
            raise TapeError("R-LAYOUT", "block 1 is not an end-of-file block")
        lab2 = _label(blks[2], 2)
        if _payload(blks[3], "block 3")[:7] != IM + b"M65" + IM + b"XC" or _payload(blks[3], "block 3")[7:] != b" " * (BLKSZ - 7):
            raise TapeError("R-LAYOUT", "block 3 is not the descriptor")
        lab3 = _label(blks[4], 4)
        if lab3["second"] != lab3["account"] or lab2["account"] != lab["account"] or lab3["account"] != lab["account"]:
            raise TapeError("R-LAYOUT", "the three labels name different accounts")
        first = 5
    else:
        # the first byte of the first block tells a padded image (NUL, or SPACE for mvBase) from one with no pad
        flat = blks[0][:1] not in (b"\x00", b" ")
        _gen_label(blks[0], flat, 0)
        first = 1
        for _ in range(1, LAYOUTS[layout]):
            while first < len(blks) and _is_eof(blks[first]):
                first += 1
            if first >= len(blks):
                raise TapeError("R-LAYOUT", "the layout reads %d labels" % LAYOUTS[layout])
            _gen_label(blks[first], flat, first)
            first += 1
        lab = {"time": b"", "date": b"", "account": b"", "reel": b""}
    end = None
    for n in range(first, len(blks)):
        if _is_eof(blks[n]):
            end = n
            break
    if end is None:
        raise TapeError("R-NOEOF", "no end-of-file block after the data")
    if end != len(blks) - 1:
        raise TapeError("R-TRAILING", "blocks after the end-of-file block")
    stream = b"".join((_gen_payload(blks[n], flat, "block %d" % n) if gen else _payload(blks[n], "block %d" % n)) for n in range(first, end))
    items = []
    files = {}
    pos = 0
    size = len(stream)
    done = False
    keys = KEYS_HEX if gen else DIGITS
    lens = LEN_HEX if gen else LEN_DEC
    while pos < size:
        if stream[pos:pos + 1] != IM:
            raise TapeError("R-STREAM", "the data has bytes between two items")
        om = None if gen else O_HEAD.match(stream, pos)
        if om:
            # the binary form: the length is the block count, never a search for the trailer (a record may hold a copy of it)
            num, group, nblocks, rid = om.group(1), om.group(2), int(om.group(3)), om.group(4)
            if num not in files:
                raise TapeError("R-NOFILE", "a binary item for file %s, which has no header" % num.decode())
            if nblocks < 1:
                raise TapeError("R-HEADER", "a binary item of no blocks")
            if nblocks * BINBLK > max_item:
                raise TapeError("R-ITEMCAP", "a binary item of %d blocks" % nblocks)
            dstart = om.end()
            dend = dstart + nblocks * BINBLK
            tm = O_TRAIL.match(stream, dend) if dend <= size else None
            if not tm:
                raise TapeError("R-ITEMEND", "no trailer after %d blocks of data" % nblocks)
            ln = int(tm.group(1), BINLEN_BASE)
            if ln < 1 or ln > nblocks * BINBLK or (nblocks > 1 and ln <= (nblocks - 1) * BINBLK):
                raise TapeError("R-ITEMEND", "length %d does not fit %d blocks" % (ln, nblocks))
            raw = stream[dstart:dend]
            if raw[ln:].strip(b"\x00"):
                raise TapeError("R-ITEMEND", "the padding of a binary item is not NUL")
            items.append({"kind": "O", "num": num, "group": group, "blocks": nblocks, "id": rid, "data": raw[:ln]})
            pos = tm.end()
            continue
        end = stream.find(IM, pos + 1)
        if end < 0:
            end = size
        tok = stream[pos + 1:end]
        # the end of the account: XX and spaces; in the other layouts also XC (Ultimate's) or a bare X, each with only spaces after it
        if tok[:2] == b"XX" or (gen and tok[:1] == b"X" and (tok[1:2] == b"C" or not tok[1:].strip(b" "))):
            rest = tok[2:] if tok[1:2] in (b"X", b"C") else tok[1:]
            if rest.strip(b" "):
                raise TapeError("R-TRAILING", "bytes after the end-of-account mark")
            done = True
            break
        pos = end
        if len(tok) > max_item:
            raise TapeError("R-ITEMCAP", "an item of %d bytes" % len(tok))
        t = tok[:1]
        f = tok.split(FM)
        if t == b"D":
            if len(f) < 6 or f[0] != b"D":
                raise TapeError("R-HEADER", "a file header with %d fields" % len(f))
            if f[1] not in (b"1", b"2", b"3"):
                raise TapeError("R-LEVEL", "level %r" % f[1][:8])
            if not keys.fullmatch(f[2]):
                raise TapeError("R-FILENUM", "file number %r" % f[2][:12])
            if not lens.fullmatch(f[3]):
                raise TapeError("R-HEADER", "no length in front of the file name")
            it = {"kind": "D", "level": f[1], "num": f[2], "name": f[3][4:], "attrs": f[4:], "llll": None if gen else int(f[3][:4])}
            files[f[2]] = it
            if len(files) > max_files:
                raise TapeError("R-FILECAP", "more than %d files" % max_files)
        elif t == b"I" or (gen and t in (b"F", b"E")):
            if len(f) < 4 or not keys.fullmatch(f[0][1:]):
                raise TapeError("R-HEADER", "an item header with %d fields" % len(f))
            if not keys.fullmatch(f[1]):
                raise TapeError("R-FILENUM", "group %r" % f[1][:12])
            if f[0][1:] not in files:
                raise TapeError("R-NOFILE", "an item for file %s, which has no header" % f[0][1:].decode())
            if gen and f[2][:1] in (b"O", b"L"):
                raise TapeError("R-UNSUPPORTED", "a binary or large item")
            if not lens.fullmatch(f[2]):
                raise TapeError("R-HEADER", "no length in front of the record id")
            rest = f[3:]
            if rest and rest[-1] == b"":
                rest = rest[:-1]
            it = {"kind": "I", "num": f[0][1:], "group": f[1], "id": f[2][4:], "fields": rest, "llll": None if gen else int(f[2][:4]), "tag": t}
        elif gen and t == b"H":
            it = {"kind": "H", "text": tok[1:]}
        elif t in (b"O", b"B", b"L", b"R", b"H", b"F", b"E"):
            raise TapeError("R-UNSUPPORTED", "an item of type %s" % t.decode())
        else:
            raise TapeError("R-BLOCKTYPE", "an item of unknown type %r" % t[:4])
        # the first thing that is not a header token must be the account's own file header: it names the account, and the name is printed and logged, so it is printable
        if gen and it["kind"] != "H" and not any(i["kind"] != "H" for i in items):
            if it["kind"] != "D" or it["level"] != b"1" or not re.fullmatch(rb"[!-~]{1,64}", it["name"]):
                raise TapeError("R-LAYOUT", "the data does not begin with the file header of a named account")
        items.append(it)
    if not done:
        raise TapeError("R-NOEND", "the data has no end-of-account mark")
    if gen:
        named = next((i for i in items if i["kind"] != "H"), None)
        if named is None:
            raise TapeError("R-LAYOUT", "the data holds no file header")
        lab["account"] = named["name"]
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


FILE_NAME_CHARS = b"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._$-"


def file_name_verdict(raw, maxlen=MAX_NAME):
    """The name of a FILE: the id rules and, besides, only the characters a file of the account can carry ('unsafe' otherwise)."""
    why = name_verdict(raw, maxlen)
    if why is None and any(c not in FILE_NAME_CHARS for c in raw):
        return "unsafe"
    return why


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


def _o_item(rid, data, num=b"102"):
    return {"kind": "O", "num": num, "group": b"103", "id": rid, "data": data}


def _raw_o(num=b"102", blocks=b"1", rid=b"B1", data=b"ab", pad=b"\x00", declared=b"2", x=b"X"):
    """A binary item written by hand so that one part of it can be wrong."""
    nb = int(blocks)
    body = data.ljust(nb * BINBLK, pad) if nb <= 5 else data
    return IM + b"I" + num + FM + b"103" + FM + b"O" + blocks + FM + rid + FM + body + IM + IM + IM + x + IM + b"\x82" + declared


def _o_image(raw):
    """An image of the small account whose last item is `raw`."""
    return _stream_image(stream_bytes(small_model(records=0))[:-3] + raw + IM + b"XX")


def _bad_blocksize(code):
    return build_image(small_model()).replace(b"L 01F4 ", b"L " + code + b" ")


def gen_model(account=b"DEMO", head=(), extra=()):
    """What only the other layouts read: file numbers and groups in hex, an F and an E item, header tokens (`head` first, `extra` last)."""
    attrs = [b"D", b"1A1", b"1", b"", b"", b"", b"", b"", b"L", b"10", b""]
    items = list(head) + [
        {"kind": "D", "level": b"1", "num": b"1A0", "name": account, "attrs": [b"D", b"1A1", b"1A1", b"", b"", b"", b"", b"SYS2", b"L", b"12", b""]},
        {"kind": "D", "level": b"2", "num": b"1A1", "name": b"CUST", "attrs": attrs},
        {"kind": "D", "level": b"3", "num": b"1A2", "name": b"CUST", "attrs": attrs},
        {"kind": "I", "num": b"1A2", "group": b"1B", "id": b"C001", "fields": [b"Name 0", b"x"]},
        {"kind": "I", "num": b"1A2", "group": b"1B", "id": b"C002", "fields": [b"Name 1", b"y"], "tag": b"F"},
        {"kind": "I", "num": b"1A2", "group": b"1C", "id": b"C003", "fields": [b"Name 2", b"z"], "tag": b"E"},
    ] + list(extra)
    return {"label": small_model()["label"], "items": items}


def _gen(layout, model=None, **kw):
    return build_image(model or gen_model(), layout, **kw)


def _gen_bad(tail, layout="jbs", end=b"XX", flat=False):
    """A valid data stream of the other layouts with `tail` (tokens written by hand) in front of its end mark."""
    return gen_image(stream_bytes(gen_model(), end)[:-(1 + len(end))] + tail + IM + end, small_model()["label"], layout, flat)


def _gen_blocks(img):
    return [img[i:i + PHYS] for i in range(0, len(img), PHYS)]


def _space_pad(img):
    """The same image with four SPACEs where the pad of every padded block begins (what mvBase wrote)."""
    return b"".join(b"    " + b[4:] if b[:1] == b"\x00" else b for b in _gen_blocks(img))


def _pad_junk(img, block=2):
    b = _gen_blocks(img)
    b[block] = b[block][:5] + b"x" + b[block][6:]
    return b"".join(b)


def _gen_d(level, num, name=b"X"):
    return IM + d_token({"level": level, "num": num, "name": name, "attrs": [b"D", b"1", b"1", b"", b"", b"", b"", b"", b"L", b"10", b""]})


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
    "ok-binary-forms": (lambda: build_image(_with(small_model(records=0), items=small_model(records=0)["items"] + [
        _o_item(b"B9", b"abc" + IM + b"def" + FM + b"x"), _o_item(b"B1000", b"q" * 999 + IM), _o_item(b"B1001", b"w" * 1000 + IM),
        _o_item(b"B2000", IM * 2000)])), None, {}),
    "ok-binary-lookalikes": (lambda: build_image(_with(small_model(records=0), items=small_model(records=0)["items"] + [
        _o_item(b"TRAILER", b"tail" + IM + b"X" + IM + b"\x82" + b"FF"), _o_item(b"ENDMARK", b"a" + IM + b"XX" + b"b"),
        _o_item(b"FULLTRAIL", b"k" + IM + IM + IM + b"X" + IM + b"\x82" + b"7" + IM + b"m"), _o_item(b"AFTER", b"z")])), None, {}),
    "binary-trailer-missing": (lambda: _o_image(_raw_o(x=b"Y")), "R-ITEMEND", {}),
    "binary-length-too-big": (lambda: _o_image(_raw_o(declared=b"1500")), "R-ITEMEND", {}),
    "binary-length-fits-fewer-blocks": (lambda: _o_image(_raw_o(blocks=b"2", declared=b"5")), "R-ITEMEND", {}),
    "binary-padding-not-nul": (lambda: _o_image(_raw_o(pad=b"x")), "R-ITEMEND", {}),
    "binary-data-runs-off-the-end": (lambda: _o_image(_raw_o(blocks=b"999")), "R-ITEMEND", {}),
    "binary-block-count-over-cap": (lambda: _o_image(_raw_o(blocks=b"999999999")), "R-ITEMCAP", {}),
    "binary-for-unknown-file": (lambda: _o_image(_raw_o(num=b"555")), "R-NOFILE", {}),
    "binary-zero-blocks": (lambda: _o_image(_raw_o(blocks=b"0")), "R-HEADER", {}),
    "bytes-after-end-mark": (lambda: _stream_image(_valid_stream() + b"junk"), "R-TRAILING", {}),
    "blocksize-ffff": (lambda: _bad_blocksize(b"FFFF"), "R-BLOCKSIZE", {}),
    "blocksize-0000": (lambda: _bad_blocksize(b"0000"), "R-BLOCKSIZE", {}),
    "level-4": (lambda: build_image(_patch_header(small_model(), 1, level=b"4")), "R-LEVEL", {}),
    "level-0": (lambda: build_image(_patch_header(small_model(), 1, level=b"0")), "R-LEVEL", {}),
    # strings that look like numbers are not numbers: a reader that compares them as numbers takes these for the right answer
    "level-01": (lambda: build_image(_patch_header(small_model(), 1, level=b"01")), "R-LEVEL", {}),
    "filenum-0102-vs-102": (lambda: build_image(_patch_header(small_model(), 2, num=b"0102")), "R-NOFILE", {}),
    "label-account-7-vs-007": (lambda: build_image(small_model(account=b"007")).replace(b"DATA 007 007", b"DATA 7 7    "), "R-LAYOUT", {}),
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


def _gen_long(layout, flat=False):
    """A record of 60 lines: the data runs over nine blocks, the item over several."""
    return _gen(layout, gen_model(extra=[{"kind": "I", "num": b"1A2", "group": b"1D", "id": b"LONG", "fields": [b"line %d " % i + b"y" * 60 for i in range(60)]}]), flat=flat)


def _gl():
    return small_model()["label"]


# Stage S4a, the other layouts.  Every one is the original reader's reading, built by our writer: no image of any of them has been seen.
RECIPES.update({
    "g-ok-jbs": (lambda: _gen("jbs"), None, {"layout": "jbs"}),
    "g-ok-fs": (lambda: _gen("fs"), None, {"layout": "fs"}),
    "g-ok-r83": (lambda: _gen("r83"), None, {"layout": "r83"}),
    "g-ok-r83-two-eofs": (lambda: _gen("r83", eofs=2), None, {"layout": "r83"}),
    "g-ok-r83-no-eof": (lambda: _gen("r83", eofs=0), None, {"layout": "r83"}),
    "g-ok-mv-with-h": (lambda: _gen("mv", gen_model(head=[{"kind": "H", "text": b"mvBase header"}], extra=[{"kind": "H", "text": b""}])), None, {"layout": "mv"}),
    "g-ok-long-padded": (lambda: _gen_long("jbs"), None, {"layout": "jbs"}),
    "g-ok-long-flat": (lambda: _gen_long("r83", flat=True), None, {"layout": "r83"}),
    "g-ok-flat-jbs": (lambda: _gen("jbs", flat=True), None, {"layout": "jbs"}),
    "g-ok-space-pad": (lambda: _space_pad(_gen_long("mv")), None, {"layout": "mv"}),
    "g-ok-end-xc": (lambda: _gen("jbs", end=b"XC"), None, {"layout": "jbs"}),
    "g-ok-end-x": (lambda: _gen("jbs", end=b"X"), None, {"layout": "jbs"}),
    "g-ok-label-text-free": (lambda: gen_image(stream_bytes(gen_model()), {"time": b"ACCOUNT-SAVE", "date": b"30-OCT-26", "account": b"whatever"}, "r83"), None, {"layout": "r83"}),
    "g-ok-hex-length": (lambda: _gen_bad(IM + b"D" + FM + b"2" + FM + b"2A0" + FM + b"00AFNAME" + FM + b"D" + FM + b"1" + FM + b"1" + FM), None, {"layout": "jbs"}),
    "g-ultfs": (lambda: _gen("jbs"), "R-UNSUPPORTED", {"layout": "ultfs"}),
    "g-unknown-format": (lambda: _gen("jbs"), "R-FORMAT", {"layout": "xyz"}),
    "g-an-as-image-read-as-jbs": (lambda: build_image(small_model()), "R-TRAILING", {"layout": "jbs"}),
    "g-a-jbs-image-read-as-as": (lambda: _gen_long("jbs"), "R-LABEL", {}),
    "g-r83-over-a-jbs-image": (lambda: _gen_long("jbs"), "R-LABEL", {"layout": "r83"}),
    "g-r83-runs-out-of-blocks": (lambda: generic_label_block(b"a b") + eof_block() * 3, "R-LAYOUT", {"layout": "r83"}),
    "g-too-short": (lambda: generic_label_block(b"a b") + eof_block(), "R-SHAPE", {"layout": "jbs"}),
    "g-no-eof-block": (lambda: _gen_long("jbs")[:-PHYS], "R-NOEOF", {"layout": "jbs"}),
    "g-blocks-after-eof": (lambda: _gen("jbs") + frame(b"x"), "R-TRAILING", {"layout": "jbs"}),
    "g-pad-junk": (lambda: _pad_junk(_gen_long("jbs")), "R-PAD", {"layout": "jbs"}),
    "g-pad-junk-in-label": (lambda: _pad_junk(_gen("jbs"), 0), "R-PAD", {"layout": "jbs"}),
    "g-blocksize-flat-in-padded": (lambda: _gen("jbs").replace(b"L 01F4 ", b"L 0200 "), "R-BLOCKSIZE", {"layout": "jbs"}),
    "g-blocksize-padded-in-flat": (lambda: _gen("jbs", flat=True).replace(b"L 0200 ", b"L 01F4 "), "R-BLOCKSIZE", {"layout": "jbs"}),
    "g-blocksize-other": (lambda: _gen("jbs").replace(b"L 01F4 ", b"L 0400 "), "R-BLOCKSIZE", {"layout": "jbs"}),
    "g-label-blank": (lambda: generic_label_block(b"   ") + _gen("jbs")[PHYS:], "R-LABEL", {"layout": "jbs"}),
    "g-label-control-byte": (lambda: generic_label_block(b"ab\x01cd") + _gen("jbs")[PHYS:], "R-LABEL", {"layout": "jbs"}),
    "g-no-level-1": (lambda: gen_image(_gen_d(b"2", b"1A1") + IM + b"XX", _gl(), "jbs"), "R-LAYOUT", {"layout": "jbs"}),
    "g-only-end": (lambda: gen_image(IM + b"XX", _gl(), "jbs"), "R-LAYOUT", {"layout": "jbs"}),
    "g-only-h-then-end": (lambda: gen_image(IM + b"Habc" + IM + b"XX", _gl(), "jbs"), "R-LAYOUT", {"layout": "jbs"}),
    "g-no-end-mark": (lambda: gen_image(stream_bytes(gen_model())[:-3] + b"   ", _gl(), "jbs"), "R-NOEND", {"layout": "jbs"}),
    "g-end-junk": (lambda: _gen_bad(b"", end=b"XXabc"), "R-TRAILING", {"layout": "jbs"}),
    "g-end-xq": (lambda: _gen_bad(IM + b"XQ"), "R-BLOCKTYPE", {"layout": "jbs"}),
    "g-type-b": (lambda: _gen_bad(IM + b"B" + FM + b"x"), "R-UNSUPPORTED", {"layout": "jbs"}),
    "g-type-r": (lambda: _gen_bad(IM + b"R" + FM + b"x"), "R-UNSUPPORTED", {"layout": "jbs"}),
    "g-type-l": (lambda: _gen_bad(IM + b"L1" + FM + b"x"), "R-UNSUPPORTED", {"layout": "jbs"}),
    "g-item-subtype-o": (lambda: _gen_bad(IM + b"I1A2" + FM + b"1B" + FM + b"O1" + FM + b"ID" + FM + b"data"), "R-UNSUPPORTED", {"layout": "jbs"}),
    "g-item-subtype-l": (lambda: _gen_bad(IM + b"I1A2" + FM + b"1B" + FM + b"L12" + FM + b"ID"), "R-UNSUPPORTED", {"layout": "jbs"}),
    "g-f-for-unknown-file": (lambda: _gen_bad(IM + b"F7F" + FM + b"1" + FM + b"0010id" + FM + b"x" + FM), "R-NOFILE", {"layout": "jbs"}),
    "g-lowercase-hex-file-number": (lambda: _gen_bad(_gen_d(b"2", b"1a")), "R-FILENUM", {"layout": "jbs"}),
    "g-account-name-escape": (lambda: _gen("jbs", gen_model(account=b"EVIL\x1b[2J")), "R-LAYOUT", {"layout": "jbs"}),
    "g-account-name-too-long": (lambda: _gen("jbs", gen_model(account=b"A" * 65)), "R-LAYOUT", {"layout": "jbs"}),
    "g-ok-account-name-64": (lambda: _gen("jbs", gen_model(account=b"A" * 64)), None, {"layout": "jbs"}),
    "g-h-token-over-cap": (lambda: _gen_bad(IM + b"H" + b"h" * 400), "R-ITEMCAP", {"layout": "jbs", "max_item": 150}),
})

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
