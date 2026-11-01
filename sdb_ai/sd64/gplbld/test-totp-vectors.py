#!/usr/bin/env python3
# test-totp-vectors.py - compiles and runs the TOTP engine's checks: gplbld/verify-totp.c
# with gplsrc/sd_totp.c against the RFC 4226, RFC 6238 and RFC 4648 vectors and the rules
# the engine adds (window, a code used once, malformed input, the provisioning link); then
# compares the engine with a SECOND implementation written here in Python (hmac, hashlib,
# base64) on random keys, counters and byte strings; then reads the source for the three
# things a vector cannot see.  Written 1 Nov 2026 for S.95 stage 0.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-totp-vectors.py
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-totp-vectors.py --selftest
#
# No sudo, no install, no sd.  Needs a C compiler and the OpenSSL headers (libssl-dev).
# Exit 0 every check passed, 1 a check failed (or, with --selftest, a mutant survived),
# 2 it could not run (no compiler, no OpenSSL, a compile error, a mutant that does not apply).
#
# THE NULL CASE IS REFUSED: the C program's summary line must say how many checks ran, the
# count must be above zero and none may have failed; a cross-check that compared nothing
# fails; a mutant whose text is not found exactly once in the source is not a mutant.
#
# --selftest makes the engine wrong in 18 small ways, one at a time, in a COPY under a
# temporary directory, and demands that the C program fail for each.  The unmutated copy
# must pass first.

import base64
import hashlib
import hmac
import os
import random
import re
import shutil
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.dirname(HERE)
INC = os.path.join(SD64, "gplsrc")
VERIFY = os.path.join(HERE, "verify-totp.c")
ENGINE_C = os.path.join(INC, "sd_totp.c")
ENGINE_H = os.path.join(INC, "sd_totp.h")

CFLAGS = ["-std=gnu17", "-Wall", "-Wextra", "-O2"]

# (name, file, old text, new text) - each old text must occur exactly once in its file
MUTANTS = [
    ("mask-7f-to-ff", "c", "mac[off] & 0x7f", "mac[off] & 0xff"),
    ("offset-mask-0f-to-07", "c", "mac[19] & 0x0f", "mac[19] & 0x07"),
    ("counter-little-endian", "c", "msg[7 - i]", "msg[i]"),
    ("window-1-to-2", "h", "SD_TOTP_WINDOW      1 ", "SD_TOTP_WINDOW      2 "),
    ("window-1-to-0", "h", "SD_TOTP_WINDOW      1 ", "SD_TOTP_WINDOW      0 "),
    ("replay-newer-or-equal", "c", "(int64_t)step > last_step", "(int64_t)step >= last_step"),
    ("replay-reported-as-nomatch", "c", "return matched ? SD_TOTP_REPLAY : SD_TOTP_NOMATCH;", "return SD_TOTP_NOMATCH;"),
    ("compare-first-three-only", "c", "CRYPTO_memcmp(want, given, SD_TOTP_DIGITS) == 0", "CRYPTO_memcmp(want, given, 3) == 0"),
    ("non-digits-allowed", "c", "if (given[i] < '0' || given[i] > '9') return SD_TOTP_BAD;", "if (0) return SD_TOTP_BAD;"),
    ("length-check-loosened", "c", "strlen(given) != SD_TOTP_DIGITS", "strlen(given) < SD_TOTP_DIGITS"),
    ("no-leading-zero-pad", "c", '"%06u"', '"%6u"'),
    ("time-zero-underflow", "c", "(now > SD_TOTP_WINDOW) ? now - SD_TOTP_WINDOW : 0", "now - SD_TOTP_WINDOW"),
    ("base32-alphabet-swapped", "c", '"ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"', '"ABCDEFGHIJKLMNOPQRSTUVWXZY234567"'),
    ("base32-leftover-bits-allowed", "c", "bits > 0 && (buf & ((1u << bits) - 1)) != 0", "0"),
    ("base32-odd-length-allowed", "c", "if (o == 0 || bits >= 5)", "if (o == 0)"),
    ("secret-of-one-byte-allowed", "c", "n < 16", "n < 1"),
    ("link-at-sign-encoded", "c", " || *u == '@'", ""),
    ("key-length-unbounded", "c", "keylen == 0 || keylen > MAX_KEY || digits", "keylen == 0 || digits"),
]


def say(text=""):
    print(text)


def find_cc():
    return shutil.which("cc") or shutil.which("gcc")


def compile_prog(cc, tmp, name, sources, include_dirs):
    exe = os.path.join(tmp, name)
    cmd = [cc] + CFLAGS + ["-o", exe] + sources + ["-I" + d for d in include_dirs] + ["-lcrypto"]
    build = subprocess.run(cmd, capture_output=True, text=True)
    return exe, cmd, build


def run_c_checks(exe):
    run = subprocess.run([exe], capture_output=True, text=True, timeout=120)
    m = re.search(r"^(\d+) checks, (\d+) failed$", run.stdout, re.M)
    return run, (int(m.group(1)), int(m.group(2))) if m else None


def python_hotp(key, counter, digits):
    mac = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    off = mac[19] & 15
    return (int.from_bytes(mac[off:off + 4], "big") & 0x7fffffff) % (10 ** digits)


def cross_check(exe):
    """The engine against Python's own HMAC and base64 on random input.  Returns (compared, failed)."""
    rng = random.Random(20261101)
    compared = failed = 0
    key_lengths = [1, 16, 20, 31, 63, 64, 65, 100, 128, 1024]
    counters = [0, 1, 2 ** 32 - 1, 2 ** 32, 2 ** 53, 2 ** 63, 2 ** 64 - 1]
    for _ in range(80):
        key = bytes(rng.getrandbits(8) for _ in range(rng.choice(key_lengths)))
        counter = rng.choice(counters + [rng.getrandbits(64)])
        digits = rng.choice([6, 6, 6, 7, 8, 9])
        want = str(python_hotp(key, counter, digits))
        got = subprocess.run([exe, "hotp", key.hex(), str(counter), str(digits)], capture_output=True, text=True).stdout.strip()
        compared += 1
        if got != want:
            failed += 1
            say("  [FAIL] hotp key=%d bytes counter=%d digits=%d: python %s, engine %s" % (len(key), counter, digits, want, got))
    for _ in range(80):
        raw = bytes(rng.getrandbits(8) for _ in range(rng.randint(1, 48)))
        want = base64.b32encode(raw).decode().rstrip("=")
        got = subprocess.run([exe, "b32", raw.hex()], capture_output=True, text=True).stdout.strip()
        back = subprocess.run([exe, "unb32", want], capture_output=True, text=True).stdout.strip()
        compared += 2
        if got != want:
            failed += 1
            say("  [FAIL] b32 of %s: python %s, engine %s" % (raw.hex(), want, got))
        if back != raw.hex():
            failed += 1
            say("  [FAIL] unb32 of %s: wanted %s, engine %s" % (want, raw.hex(), back))
    return compared, failed


def source_rules():
    """What no vector can see.  Returns (rules checked, failures)."""
    text = open(ENGINE_C).read()
    code = re.sub(r"/\*.*?\*/", "", text, flags=re.S)           # comments out
    rules = [
        ("the code is compared with CRYPTO_memcmp", "CRYPTO_memcmp(" in code),
        ("no strcmp, strncmp, memcmp or bcmp anywhere in the engine", re.search(r"\b(strcmp|strncmp|memcmp|bcmp)\s*\(", code) is None),
        ("the secret comes from RAND_bytes", "RAND_bytes(" in code),
        ("no rand, random or srand in the engine", re.search(r"\b(s?rand|s?random|rand_r)\s*\(", code) is None),
        ("the engine reads no file and writes no log or output",
         re.search(r"\b(fopen|open|fread|fwrite|fprintf|printf|puts|syslog|getenv|system|popen)\s*\(", code) is None),
        ("the comparison loop has no early return after a match",
         re.search(r"CRYPTO_memcmp\([^)]*\)\s*==\s*0\)\s*\{[^}]*return", code) is None),
    ]
    failed = 0
    for what, ok in rules:
        say("  [%s] %s" % ("PASS" if ok else "FAIL", what))
        if not ok:
            failed += 1
    return len(rules), failed


def selftest(cc):
    say("test-totp-vectors --selftest")
    originals = {"c": open(ENGINE_C).read(), "h": open(ENGINE_H).read()}
    tmp = tempfile.mkdtemp(prefix="totp-mutants-")
    survivors = []
    try:
        for kind, text in originals.items():
            open(os.path.join(tmp, "sd_totp." + kind), "w").write(text)
        exe, cmd, build = compile_prog(cc, tmp, "baseline", [VERIFY, os.path.join(tmp, "sd_totp.c")], [tmp])
        if build.returncode != 0 or build.stderr:
            say("  CANNOT RUN - the unmutated copy does not build cleanly:\n" + build.stderr)
            return 2
        run, counts = run_c_checks(exe)
        if counts is None or counts[0] == 0 or counts[1] != 0 or run.returncode != 0:
            say("  CANNOT RUN - the unmutated copy does not pass: %s" % (counts,))
            return 2
        say("  baseline : %d checks, 0 failed" % counts[0])
        for i, (name, kind, old, new) in enumerate(MUTANTS):
            src = originals[kind]
            if src.count(old) != 1:
                say("  CANNOT RUN - mutant %s: its text occurs %d times (wanted 1): %r" % (name, src.count(old), old))
                return 2
            mut = dict(originals)
            mut[kind] = src.replace(old, new)
            for k, t in mut.items():
                open(os.path.join(tmp, "sd_totp." + k), "w").write(t)
            exe, cmd, build = compile_prog(cc, tmp, "mutant%d" % i, [VERIFY, os.path.join(tmp, "sd_totp.c")], [tmp])
            if build.returncode != 0:
                say("  CANNOT RUN - mutant %s does not compile:\n%s" % (name, build.stderr))
                return 2
            run, counts = run_c_checks(exe)
            caught = run.returncode != 0 or (counts is not None and counts[1] > 0)
            say("  [%s] %-34s %s" % ("caught" if caught else "SURVIVED", name,
                                     ("%d of %d checks failed" % (counts[1], counts[0])) if counts else "no summary line"))
            if not caught:
                survivors.append(name)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    say("")
    if survivors:
        say("test-totp-vectors --selftest: FAILED - %d of %d mutants survived: %s" % (len(survivors), len(MUTANTS), ", ".join(survivors)))
        return 1
    say("test-totp-vectors --selftest: PASSED - %d of %d mutants caught." % (len(MUTANTS), len(MUTANTS)))
    return 0


def main():
    cc = find_cc()
    say("test-totp-vectors")
    say("  compiler : %s" % (cc or "(none found)"))
    if cc is None:
        say("test-totp-vectors: CANNOT RUN - no C compiler on PATH.")
        return 2
    for path in (VERIFY, ENGINE_C, ENGINE_H):
        if not os.path.isfile(path):
            say("test-totp-vectors: CANNOT RUN - missing %s" % path)
            return 2
    if "--selftest" in sys.argv[1:]:
        return selftest(cc)

    tmp = tempfile.mkdtemp(prefix="totp-vectors-")
    try:
        exe, cmd, build = compile_prog(cc, tmp, "verify-totp", [VERIFY, ENGINE_C], [INC])
        say("  command  : %s" % " ".join(cmd))
        if build.stdout or build.stderr:
            say("  --- compiler output ---")
            sys.stdout.write(build.stdout + build.stderr)
        if build.returncode != 0:
            say("test-totp-vectors: CANNOT RUN - compile failed (exit %d); libssl-dev installed?" % build.returncode)
            return 2
        if "warning" in (build.stdout + build.stderr).lower():
            say("test-totp-vectors: FAILED - the compile produced a warning.")
            return 1

        say("")
        say("== verify-totp (the vectors and the engine's rules)")
        run, counts = run_c_checks(exe)
        sys.stdout.write(run.stdout + run.stderr)
        if counts is None:
            say("test-totp-vectors: FAILED - no summary line, so no checks can be counted.")
            return 1
        ran, failed = counts
        if ran == 0:
            say("test-totp-vectors: FAILED - zero checks ran.")
            return 1
        if run.returncode != 0 or failed != 0:
            say("test-totp-vectors: FAILED - %d of %d checks failed (exit %d)." % (failed, ran, run.returncode))
            return 1

        say("")
        say("== the engine against Python's hmac and base64 (80 HOTP cases, 80 byte strings)")
        compared, cfailed = cross_check(exe)
        if compared == 0:
            say("test-totp-vectors: FAILED - nothing was compared.")
            return 1
        say("  %d comparisons, %d failed" % (compared, cfailed))

        say("")
        say("== the source rules")
        rules, rfailed = source_rules()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    say("")
    if cfailed or rfailed:
        say("test-totp-vectors: FAILED - %d cross-check and %d source-rule failures." % (cfailed, rfailed))
        return 1
    say("test-totp-vectors: PASSED - %d vector checks, %d comparisons, %d source rules." % (ran, compared, rules))
    return 0


if __name__ == "__main__":
    sys.exit(main())
