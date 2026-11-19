#!/usr/bin/env python3
# test-ownaddr-units.py - S.264 (18 Nov 2026; owner: "yes" to closing it in the code).  A connection from one of THIS machine's own addresses
# came from this machine (an ssh tunnel aimed at its own network address is the case), so !peer_local calls it local and the SDSYS API sign-in
# meets the local door's tests instead of the remote address list.
#   O   gplsrc/sd_ownaddr.c built with -Wall -Wextra -Werror together with gplbld/verify-ownaddr.c and driven as a black box: equal addresses
#       match as BITS (IPv4, IPv6 in any compression, IPv4-mapped IPv6 as its IPv4 form), different ones do not, a non-address is -1, an
#       empty list is 0; the LIVE call answers 1 for 127.0.0.1 (every Linux machine has lo) and 0 for a TEST-NET-3 address (203.0.113.1)
#   P   gpl.bp/peer_local asks kernel(K$OWN.ADDR, peer.addr) = 1 inside its case and includes int$keys.h; the key is 176 in keys.h and int$keys.h
#   A   apisrvr's remote door is still entered only when not(api.peer.local), so an own-address peer goes to the local door
# FREE CHECK: needs a C compiler (exit 2 without one).  It cannot say a real tunnel is refused: that is a VM row.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-ownaddr-units.py
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-ownaddr-units.py --selftest
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.normpath(os.path.join(HERE, ".."))
GPLSRC = os.path.join(SD64, "gplsrc")
BP = os.path.join(SD64, "sdsys", "gpl.bp")
CASES = [  # (address, own list, expected)
    ("10.0.2.15", ["127.0.0.1", "10.0.2.15"], 1),
    ("10.0.2.16", ["127.0.0.1", "10.0.2.15"], 0),
    ("::ffff:10.0.2.15", ["10.0.2.15"], 1),
    ("10.0.2.15", ["::ffff:10.0.2.15"], 1),
    ("fe80::1", ["fe80:0:0:0:0:0:0:1"], 1),
    ("fe80::2", ["fe80::1"], 0),
    ("2001:db8::1", ["10.0.2.15"], 0),
    ("010.0.2.15", ["10.0.2.15"], -1),
    ("not-an-address", ["10.0.2.15"], -1),
    ("", ["10.0.2.15"], -1),
    ("10.0.2.15", [], 0),
]


def read(p):
    with open(p, encoding="latin-1") as f:
        return f.read()


def build(src_c, d):
    cc = shutil.which("cc") or shutil.which("gcc")
    if cc is None:
        return None, "no C compiler"
    with open(os.path.join(d, "sd_ownaddr.c"), "w", encoding="latin-1") as f:
        f.write(src_c)
    shutil.copy(os.path.join(GPLSRC, "sd_ownaddr.h"), d)
    exe = os.path.join(d, "verify-ownaddr")
    p = subprocess.run([cc, "-Wall", "-Wextra", "-Werror", "-I" + d, os.path.join(d, "sd_ownaddr.c"), os.path.join(HERE, "verify-ownaddr.c"),
                        "-o", exe], capture_output=True, text=True)
    return (exe if p.returncode == 0 else None), p.stderr


def run(exe, *args):
    p = subprocess.run([exe] + list(args), capture_output=True, text=True)
    m = re.search(r"^result=(-?\d+)$", p.stdout, re.M)
    return int(m.group(1)) if m else None


def checks(src):
    rows = []
    with tempfile.TemporaryDirectory() as d:
        exe, err = build(src["c"], d)
        if exe is None:
            rows.append(("O0 sd_ownaddr.c builds with -Wall -Wextra -Werror", False, err[-300:]))
            return rows
        bad = [(a, o, e, run(exe, a, *o)) for a, o, e in CASES]
        bad = [b for b in bad if b[3] != b[2]]
        rows.append(("O1 %d cases: bits compared, mapped IPv4 as IPv4, a non-address -1, an empty list 0" % len(CASES), not bad, repr(bad)))
        rows.append(("O2 LIVE: 127.0.0.1 is one of this machine's own (lo)", run(exe, "--live", "127.0.0.1") == 1, ""))
        rows.append(("O3 LIVE CONTROL: 203.0.113.1 (TEST-NET-3) is not", run(exe, "--live", "203.0.113.1") == 0, ""))
    pl = "\n".join(l for l in src["peer"].split("\n") if not l.lstrip().startswith("*"))
    rows.append(("P1 peer_local: a case 'kernel(K$OWN.ADDR, peer.addr) = 1' sets is.local, inside the begin case",
                 re.search(r"begin case.*case kernel\(K\$OWN\.ADDR, peer\.addr\) = 1\s*(;\*[^\n]*)?\n\s*is\.local = @true.*end case", pl, re.S) is not None, ""))
    rows.append(("P2 peer_local includes int$keys.h", re.search(r"^\$include int\$keys\.h", pl, re.M) is not None, ""))
    rows.append(("P3 the key is 176 in gplsrc/keys.h and gpl.bp/int$keys.h",
                 re.search(r"#define K_OWN_ADDR\s+176\b", src["ck"]) is not None and re.search(r"\$define K\$OWN\.ADDR\s+176\b", src["bk"]) is not None, ""))
    rows.append(("A1 apisrvr enters the remote door only when not(api.peer.local)",
                 "if downcase(scram.user) = 'sdsys' and not(api.peer.local) then" in src["api"], ""))
    return rows


MUTANTS = [
    ("only the first byte compared", "c", lambda t: t.replace("return memcmp(a, b, (fa == AF_INET) ? 4 : 16) == 0;", "return memcmp(a, b, 1) == 0;", 1)),
    ("mapped not folded", "c", lambda t: t.replace("if (memcmp(a6.s6_addr, mapped, 12) == 0) {", "if ((memcmp(a6.s6_addr, mapped, 12) == 0) && (a6.s6_addr[0] == 0xfe)) {", 1)),
    ("empty is mine", "c", lambda t: t.replace("  return 0;\n}\n\nint sd_own_address(", "  return 1;\n}\n\nint sd_own_address(", 1)),
    ("peer_local does not ask", "peer", lambda t: t.replace("case kernel(K$OWN.ADDR, peer.addr) = 1", "case 0", 1)),
    ("key number differs", "bk", lambda t: t.replace("$define K$OWN.ADDR       176", "$define K$OWN.ADDR       177", 1)),
]


def report(rows, quiet=False):
    bad = [n for n, ok, _ in rows if not ok]
    if not quiet:
        for n, ok, why in rows:
            print("  [%s] %s%s" % ("PASS" if ok else "FAIL", n, ("   <- " + why) if (not ok and why) else ""))
    return bad


def main():
    if not (shutil.which("cc") or shutil.which("gcc")):
        print("test-ownaddr-units: CANNOT RUN - no C compiler")
        return 2
    src = {"c": read(os.path.join(GPLSRC, "sd_ownaddr.c")), "peer": read(os.path.join(BP, "peer_local")), "ck": read(os.path.join(GPLSRC, "keys.h")),
           "bk": read(os.path.join(BP, "int$keys.h")), "api": read(os.path.join(BP, "apisrvr"))}
    print("test-ownaddr-units: gplsrc %s, gpl.bp %s" % (GPLSRC, BP))
    rows = checks(src)
    bad = report(rows)
    if "--selftest" in sys.argv:
        missed = 0
        for name, key, f in MUTANTS:
            m = dict(src)
            m[key] = f(src[key])
            if m[key] == src[key]:
                print("  [MUTANT %s] DID NOT APPLY" % name)
                missed += 1
                continue
            b = report(checks(m), quiet=True)
            print("  [MUTANT %s] %s" % (name, ("killed by " + ", ".join(x.split()[0] for x in b)) if b else "MISSED"))
            missed += 0 if b else 1
        if missed:
            print("test-ownaddr-units: SELFTEST FAILED - %d mutant(s) missed or not applied" % missed)
            return 1
        print("test-ownaddr-units: selftest - %d of %d mutants killed" % (len(MUTANTS), len(MUTANTS)))
    print("test-ownaddr-units: %d passed, %d failed" % (len(rows) - len(bad), len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
