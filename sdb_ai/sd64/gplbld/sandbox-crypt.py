#!/usr/bin/env python3
#
# sandbox-crypt.py - encryption layers 2 and 3: SDSALT / SDKEY / SDRANDKEY for any program.  No install, no sudo.
#
#   SDBOX_KEYSET=<n> python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-crypt.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (needs a `make`d bin/sd).  With --build it is built first from
# THIS tree (it must be empty or absent).  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 18 Oct 26 dm  Written for encryption layer 2 (.claude/plan-encryption-layers.md): SDSALT(), SDKEY(passphrase, salt),
#               SDRANDKEY() and the way they meet SDENCRYPT / SDDECRYPT.
# END-HISTORY
#
# THE INSTRUMENT is the value a BASIC program printed between brackets (as sandbox-func-b4.py).  A row that compares two
# keys prints 1 or 0 and wants 1 or 0, so that the key itself does not have to be known to the table; the ONE row that
# pins a key (the fixed vector) wants a value computed OUTSIDE SD, by libsodium loaded through ctypes with the limits
# written out in this file (2 passes, 64 MiB, argon2id) - so a change of the limits in the C source fails it.
# EVERY RELATION HAS ITS CONTROL: a derived key is checked to differ for a different salt and passphrase (the
# "equal" row alone would pass for a function that returned a constant); the "refused" rows wait for the empty string AND
# the status, and a good call after a refusal must read STATUS() 0 again.  A program that does not compile prints
# nothing, so the compile-refusal rows want NO output line, with the same shape written correctly as the control.

import base64
import ctypes
import ctypes.util
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
passed = failed = 0

# the reference key: libsodium, outside SD.  passphrase "correct horse battery staple", salt = bytes 0..15
REF_PW = b"correct horse battery staple"
REF_SALT = bytes(range(16))
REF_SALT_B64 = base64.b64encode(REF_SALT).decode()
OPSLIMIT, MEMLIMIT, ALG_ARGON2ID13 = 2, 67108864, 2


def reference_key():
    path = ctypes.util.find_library("sodium")
    if not path:
        return None
    lib = ctypes.CDLL(path)
    if lib.sodium_init() < 0:
        return None
    out = ctypes.create_string_buffer(32)
    rc = lib.crypto_pwhash(out, ctypes.c_ulonglong(32), REF_PW, ctypes.c_ulonglong(len(REF_PW)), REF_SALT,
                           ctypes.c_ulonglong(OPSLIMIT), ctypes.c_size_t(MEMLIMIT), ctypes.c_int(ALG_ARGON2ID13))
    return base64.b64encode(out.raw).decode() if rc == 0 else None


B64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="

# Prefix of every case: a salt and two keys made from it.
PRE = ("salt = sdsalt()\n"
       "   k1 = sdkey('first passphrase', salt)\n"
       "   k2 = sdkey('second passphrase', salt)\n")

# (label, BASIC statements one per line leaving the value in x, wanted).  wanted None = the program must NOT compile.
CASES = [
    # ---- SDSALT, SDRANDKEY ------------------------------------------------------------------------------------------
    ("SDSALT is 24 characters (base64 of 16 bytes) and STATUS() is 0 after it",
     "s = sdsalt()\n   x = len(s):'|':status()", "24|0"),
    ("SDSALT uses only base64 characters",
     "s = sdsalt() ; x = 1\n   for i = 1 to len(s) ; if index('%s', s[i,1], 1) = 0 then x = 0\n   next i" % B64, "1"),
    ("SDSALT gives a different salt each time (CONTROL for the equality rows below)",
     "x = (sdsalt() # sdsalt())", "1"),
    ("SDRANDKEY is 44 characters and STATUS() is 0 after it",
     "k = sdrandkey()\n   x = len(k):'|':status()", "44|0"),
    ("SDRANDKEY uses only base64 characters",
     "k = sdrandkey() ; x = 1\n   for i = 1 to len(k) ; if index('%s', k[i,1], 1) = 0 then x = 0\n   next i" % B64, "1"),
    ("SDRANDKEY gives a different key each time",
     "x = (sdrandkey() # sdrandkey())", "1"),
    ("SDRANDKEY ends in the one '=' that base64 of 32 bytes ends in",
     "k = sdrandkey()\n   x = k[44,1]:'|':count(k, '=')", "=|1"),
    # ---- SDKEY -------------------------------------------------------------------------------------------------------
    ("SDKEY is 44 characters and STATUS() is 0",
     PRE + "   x = len(k1):'|':status()", "44|0"),
    ("SDKEY: the same passphrase and salt give the same key",
     PRE + "   x = (sdkey('first passphrase', salt) = k1)", "1"),
    ("SDKEY: the same salt and a different passphrase give a different key (CONTROL)",
     PRE + "   x = (k1 # k2)", "1"),
    ("SDKEY: the same passphrase and a different salt give a different key (CONTROL)",
     PRE + "   x = (sdkey('first passphrase', sdsalt()) # k1)", "1"),
    ("SDKEY: a passphrase that differs only in case gives a different key",
     PRE + "   x = (sdkey('FIRST PASSPHRASE', salt) # k1)", "1"),
    ("SDKEY: a trailing space is part of the passphrase",
     PRE + "   x = (sdkey('first passphrase ', salt) # k1)", "1"),
    ("SDKEY: a number is the passphrase it prints as",
     "salt = sdsalt()\n   x = (sdkey(12345, salt) = sdkey('12345', salt))", "1"),
    ("SDKEY: a passphrase holding a value mark is accepted and differs from the same text without it",
     PRE + "   a = sdkey('ab':@vm:'cd', salt) ; x = (a # sdkey('abcd', salt)):'|':len(a):'|':status()", "1|44|0"),
    ("SDKEY: 65536 characters are accepted",
     "salt = sdsalt()\n   k = sdkey(str('a', 65536), salt)\n   x = len(k):'|':status()", "44|0"),
    ("SDKEY: the fixed vector - the key libsodium makes outside SD (argon2id, 2 passes, 64 MiB)",
     "x = sdkey('%s', '%s')" % (REF_PW.decode(), REF_SALT_B64), "REFERENCE"),
    ("SDKEY: a key made by SDKEY is accepted by SDENCRYPT and SDDECRYPT as a base64 key",
     PRE + "   c = sdencrypt('salary 41250', k1, 202)\n   x = sddecrypt(c, k1, 202):'|':status()", "salary 41250|0"),
    # ---- the salt and passphrase refusals ----------------------------------------------------------------------------
    ("SDKEY: an empty salt gives the null string and STATUS() 10206",
     "x = 'old'\n   x = sdkey('pw', '')\n   x = len(x):'|':status()", "0|10206"),
    ("SDKEY: a salt that is not base64 gives the null string and 10206",
     "x = sdkey('pw', '!!!!!!!!!!!!!!!!!!!!!!!!'):'|':status()", "|10206"),
    ("SDKEY: a salt for 15 bytes (20 characters) gives 10206",
     "x = sdkey('pw', 'AAAAAAAAAAAAAAAAAAAA'):'|':status()", "|10206"),
    ("SDKEY: a salt for 32 bytes (44 characters) gives 10206",
     "x = sdkey('pw', 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA='):'|':status()", "|10206"),
    ("SDKEY: a salt of 100 characters gives 10206",
     "x = sdkey('pw', str('A', 100)):'|':status()", "|10206"),
    ("SDKEY: the right-length salt (CONTROL for the three rows above) gives a key",
     "x = len(sdkey('pw', 'AAAAAAAAAAAAAAAAAAAAAA==')):'|':status()", "44|0"),
    ("SDKEY: an empty passphrase gives the null string and STATUS() 10207",
     "x = sdkey('', sdsalt()):'|':status()", "|10207"),
    ("SDKEY: 65537 characters give the null string and 10207",
     "x = sdkey(str('a', 65537), sdsalt()):'|':status()", "|10207"),
    ("SDKEY: a refusal is not sticky - the next good call reads STATUS() 0 and gives a key",
     "s = sdsalt()\n   z = sdkey('', s)\n   w = status()\n   y = sdkey('pw', s)\n   x = w:'|':status():'|':len(y)", "10207|0|44"),
    ("SDKEY: a failed call leaves the target empty, not what it held",
     "x = 'old value'\n   x = sdkey('pw', 'bad')\n   x = '[':x:']':len(x)", "[]0"),
    # ---- meeting SDENCRYPT / SDDECRYPT --------------------------------------------------------------------------------
    ("SDENCRYPT: the ciphertext is not the plaintext, and encrypting twice gives two different values (a fresh nonce)",
     PRE + "   p = 'salary 41250'\n   c1 = sdencrypt(p, k1, 202) ; c2 = sdencrypt(p, k1, 202)\n"
     "   x = (c1 # p):'|':(c1 # c2):'|':(index(c1, 'salary', 1) = 0)", "1|1|1"),
    ("SDDECRYPT: both ciphertexts return the plaintext",
     PRE + "   p = 'salary 41250'\n   c1 = sdencrypt(p, k1, 202) ; c2 = sdencrypt(p, k1, 202)\n"
     "   x = sddecrypt(c1, k1, 202):'|':sddecrypt(c2, k1, 202)", "salary 41250|salary 41250"),
    ("SDDECRYPT: a key from another passphrase is refused with 10201 and gives the null string",
     PRE + "   c = sdencrypt('salary 41250', k1, 202)\n   x = len(sddecrypt(c, k2, 202)):'|':status()", "0|10201"),
    ("SDDECRYPT: the right key after the refusal works (CONTROL)",
     PRE + "   c = sdencrypt('salary 41250', k1, 202)\n   z = sddecrypt(c, k2, 202)\n   x = sddecrypt(c, k1, 202):'|':status()",
     "salary 41250|0"),
    ("SDDECRYPT: ciphertext with one character changed in the middle is refused with 10201",
     PRE + "   c = sdencrypt('salary 41250', k1, 202)\n   m = int(len(c) / 2)\n   ch = if c[m,1] = 'A' then 'B' else 'A'\n"
     "   t = c[1, m - 1]:ch:c[m + 1, len(c)]\n   x = (t # c):'|':len(sddecrypt(t, k1, 202)):'|':status()", "1|0|10201"),
    ("SDDECRYPT: ciphertext cut short is refused",
     PRE + "   c = sdencrypt('salary 41250', k1, 202)\n   x = len(sddecrypt(c[1, 20], k1, 202)):'|':(status() # 0)", "0|1"),
    ("SDENCRYPT: a passphrase passed straight as the key is still refused with 10204 (CONTROL)",
     "x = len(sdencrypt('salary', 'first passphrase', 202)):'|':status()", "0|10204"),
    ("SDENCRYPT: a base64 key with encoding 201 (hex) is refused with 10204 - a derived key is for 202",
     PRE + "   x = len(sdencrypt('salary', k1, 201)):'|':status()", "0|10204"),
    ("SDRANDKEY: a random key works as a key for 202",
     "k = sdrandkey()\n   c = sdencrypt('abc def', k, 202)\n   x = sddecrypt(c, k, 202):'|':status()", "abc def|0"),
    ("SDRANDKEY: two random keys do not decrypt each other's ciphertext",
     "k = sdrandkey() ; j = sdrandkey()\n   c = sdencrypt('abc def', k, 202)\n   x = len(sddecrypt(c, j, 202)):'|':status()", "0|10201"),
    ("SDENCRYPT: a value holding every kind of mark and a high-bit byte survives the round trip",
     PRE + "   p = 'a':@fm:'b':@vm:'c':@sm:'d':@tm:'e':@im:char(200):'z'\n   c = sdencrypt(p, k1, 202)\n"
     "   x = (sddecrypt(c, k1, 202) = p):'|':(index(c, @fm, 1) + index(c, @vm, 1) + index(c, @sm, 1))", "1|0"),
    ("SDENCRYPT: a 40000 character value survives the round trip",
     PRE + "   p = str('0123456789', 4000)\n   c = sdencrypt(p, k1, 202)\n   x = (sddecrypt(c, k1, 202) = p):'|':status()", "1|0"),
    ("SDENCRYPT: an empty value is refused with 10200 (as before)",
     PRE + "   x = len(sdencrypt('', k1, 202)):'|':status()", "0|10200"),
    # ---- compile ------------------------------------------------------------------------------------------------------
    ("CONTROL: SDSALT() with its brackets and nothing in them compiles", "x = len(sdsalt())", "24"),
    ("SDSALT(1) does not compile", "x = sdsalt(1)", ("ERR", "Right bracket not found where expected")),
    ("SDRANDKEY(1) does not compile", "x = sdrandkey(1)", ("ERR", "Right bracket not found where expected")),
    ("SDKEY with one argument does not compile", "x = sdkey('pw')", ("ERR", "Comma not found where expected")),
    ("SDKEY with three arguments does not compile", "x = sdkey('pw', sdsalt(), 3)", ("ERR", "Right bracket not found where expected")),
    ("a function call can be an argument of another: SDKEY('pw', SDSALT()) is a key",
     "x = len(sdkey('pw', sdsalt())):'|':status()", "44|0"),
    ("the same call twice in one expression: SDSALT() # SDSALT() is true (the compiler keeps its rows apart)",
     "x = (sdkey('pw', sdsalt()) # sdkey('pw', sdsalt()))", "1"),
]

# Files the canary must not reach.  The passphrase is built at run time, so the program source does not hold it.
CANARY_A, CANARY_B = "Canary", "Phrase-7f3a91"
CONTROL_FRAG = "zzcryptsourcefrag"


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
    say("sandbox-crypt: CANNOT RUN - " + msg)
    sys.exit(2)


def sess(box, *cmds):
    say("    > %d commands" % len(cmds))
    p = subprocess.run([sys.executable, TOOL, box, "sess", os.path.join(box, "user_accounts")] + list(cmds),
                       capture_output=True, text=True, timeout=1800)
    out = ANSI.sub("", p.stdout + p.stderr)
    return out.split(":TERM 200,9999", 1)[-1]


def grep_tree(root, needle):
    """Files under root holding needle (bytes).  The sandbox's own tree/ (a copy of the source) is not data."""
    hits = []
    skip = os.path.join(root, "tree")
    nb = needle.encode("latin-1")
    for d, dirs, files in os.walk(root):
        if d == root and "tree" in dirs:
            dirs.remove("tree")
        for f in files:
            pth = os.path.join(d, f)
            try:
                if os.path.islink(pth) or os.path.getsize(pth) > 64 * 1024 * 1024:
                    continue
                with open(pth, "rb") as fh:
                    if nb in fh.read():
                        hits.append(pth)
            except OSError:
                pass
    return hits


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-crypt.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-crypt: sandbox %s (SDBOX_KEYSET %s)" % (box, os.environ.get("SDBOX_KEYSET", "0")))
    ref = reference_key()
    if ref is None:
        bail("libsodium could not be loaded through ctypes: the fixed-vector row has no reference")
    say("sandbox-crypt: reference key for the fixed vector (libsodium via ctypes): %s" % ref)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=1800)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-crypt: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    cmds, names = [], []
    for i, (_, body, _w) in enumerate(CASES):
        nm = "zzcr%02d" % i
        names.append(nm)
        with open(os.path.join(sysd, "bp", nm), "w") as f:
            f.write("   x = ''\n" + "".join("   %s\n" % ln for ln in body.split("\n")) + "   crt 'C%02d[':x:']'\nend\n" % i)
        cmds += ["BASIC bp %s" % nm, "RUN bp %s" % nm]
    # the canary program: derives a key from a passphrase built at run time and prints it, so the key is known to this script
    canary = "zzcrcan"
    names.append(canary)
    with open(os.path.join(sysd, "bp", canary), "w") as f:
        f.write("   * %s\n   pw = '%s':'-':'%s'\n   k = sdkey(pw, sdsalt())\n   c = sdencrypt('plain canary value', k, 202)\n"
                "   crt 'KEY[':k:']'\n   crt 'PW[':pw:']'\nend\n" % (CONTROL_FRAG, CANARY_A, CANARY_B))
    cmds += ["BASIC bp %s" % canary, "RUN bp %s" % canary]
    try:
        out = sess(box, *cmds)
        say("\n--- the functions -------------------------------------------------------------")
        starts = [(mm.start(), mm.group(1)) for mm in re.finditer(r"(?m)^:BASIC bp (zzcr\d+)\s*$", out)]
        segs = {}
        for (a, nm), (b, _n2) in zip(starts, starts[1:] + [(len(out), "")]):
            segs[int(nm[4:])] = out[a:b]
        row("the compile output of every case was found in the session (%d programs)" % len(CASES), len(segs) == len(CASES),
            "found %d" % len(segs))
        for i, (label, _body, want) in enumerate(CASES):
            m = re.search(r"(?m)^C%02d\[(.*)\]\s*$" % i, out)
            got = m.group(1) if m else None
            if want == "REFERENCE":
                want = ref
            if isinstance(want, tuple):
                # a compile refusal: the compiler's own output for THIS program must say "with errors" and give the reason
                # wanted - a program that did not compile because the function is unknown (the tree before the change) says
                # something else - and the program must not have run
                seg = segs.get(i, "")
                reason = re.search(want[1], seg)
                row("%s (compiler says /%s/)" % (label, want[1]), m is None and "with errors" in seg and reason is not None,
                    "ran and printed %r" % got if m else "compiler output: %s" % " / ".join(seg.split("\n")[1:6]))
            else:
                row("%s: wanted %r" % (label, want), got == want, "got %r" % got if m else "no output")
        say("\n--- key hygiene: nothing is written to disk ---------------------------------------")
        mk = re.search(r"(?m)^KEY\[(.*)\]\s*$", out)
        mp = re.search(r"(?m)^PW\[(.*)\]\s*$", out)
        key = mk.group(1) if mk else None
        pw = mp.group(1) if mp else None
        row("the canary program ran and printed a 44 character key and its passphrase",
            key is not None and len(key) == 44 and pw == "%s-%s" % (CANARY_A, CANARY_B), "key %r pw %r" % (key, pw))
        if key and pw:
            ctl = grep_tree(box, CONTROL_FRAG)
            row("CONTROL: the search finds a string that IS on disk (the canary program's source)", len(ctl) >= 1, "no file holds it")
            hits_pw = grep_tree(box, pw)
            row("the passphrase appears in no file of the sandbox (audit trail, errlog, como, work files)", not hits_pw, "found in %s" % hits_pw[:3])
            hits_key = grep_tree(box, key)
            row("the derived key appears in no file of the sandbox", not hits_key, "found in %s" % hits_key[:3])
    finally:
        for nm in names:
            for d in ("bp", "bp.out"):
                pth = os.path.join(sysd, d, nm)
                if os.path.exists(pth):
                    os.remove(pth)

    say("\nsandbox-crypt: %d passed, %d failed" % (passed, failed))
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
