#!/usr/bin/env python3
"""test-tlsconsts-units.py - the API's TLS wire contract, pinned across every
file that states it.

Adopted 15 Sep 2026 from the Windows port's test of the same name (its
RELEASE_1.1 41), under the owner's rule that Linux follows the Windows port's
decisions.  It goes further than the port's in one way: the probe and the two
BASIC programs carry the GS2 header as literals, so they are pinned too.

  python3 /home/don/Projects/SDCoreLinuxProject/sdcore4linux/sdb_ai/sd64/gplbld/test-tlsconsts-units.py

No sudo, no install, no sd.  These constants are one fact kept in step by
hand, and nothing in the build cross-checks them - the compiler accepts any
value.  A different exporter label derives a different binding, a different
GS2 header is refused as a downgrade, a different SDEXT key reaches the wrong
dispatch arm.  Any of those would split a Linux client from a Windows server,
or a new client from an old one, in a way the traffic does not show.

WHAT IT PINS (the values Linux S.19 and Windows RELEASE_1.1 41 share):

  gplsrc/sd_tls.h          SD_TLS_BINDING_BYTES 32, SD_TLS_BINDING_LABEL
                           "EXPORTER-Channel-Binding", SD_TLS_GS2_HEADER
                           "p=tls-exporter,,", SD_TLS_HANDSHAKE_MS 10000
  gplsrc/keys.h            SKT_TLS 0x01000000, SKT_INFO_TLS_CBIND 8,
                           SD_TLS_CBIND 110
  sdsys/syscom/keys.h      the BASIC mirror: SKT$TLS, SKT$INFO.TLS.CBIND,
                           SD_TLS_CBIND - the same three values
  gplbld/scram-probe.py    GS2_BOUND and BINDING_LABEL
  sdsys/gpl.bp/apisrvr     the literal 'p=tls-exporter,,'
  sdsys/gpl.bp/sdclient    the literal 'p=tls-exporter,,'

A CONTROL is built in: every constant must be FOUND, so a renamed or deleted
definition fails loudly rather than passing because there was nothing to
compare.

Exit 0 all agree, 1 a mismatch or a constant not found, 2 it could not run (a
file is missing, or fewer checks ran than expected - the null case).
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # sdb_ai/sd64

C_CONSTS = {
    "SD_TLS_BINDING_BYTES": "32",
    "SD_TLS_BINDING_LABEL": '"EXPORTER-Channel-Binding"',
    "SD_TLS_GS2_HEADER": '"p=tls-exporter,,"',
    "SD_TLS_HANDSHAKE_MS": "10000",
}
KEY_CONSTS = {
    "SKT_TLS": "0x01000000",
    "SKT_INFO_TLS_CBIND": "8",
    "SD_TLS_CBIND": "110",
}
BASIC_CONSTS = {
    "SKT$TLS": "0x01000000",
    "SKT$INFO.TLS.CBIND": "8",
    "SD_TLS_CBIND": "110",
}
GS2 = "p=tls-exporter,,"
LABEL = "EXPORTER-Channel-Binding"
EXPECTED_CHECKS = len(C_CONSTS) + len(KEY_CONSTS) + len(BASIC_CONSTS) + 2 + 2

checks = 0
fails = 0


def read(rel):
    path = os.path.join(ROOT, rel)
    print("  reading  : %s" % path)
    if not os.path.isfile(path):
        print("REFUSING - missing file: %s" % path)
        sys.exit(2)
    with open(path, encoding="iso-8859-1") as f:
        return f.read()


def expect(where, label, got, want):
    global checks, fails
    checks += 1
    if got is None:
        fails += 1
        print("  [FAIL] %s: %s NOT FOUND (control)" % (where, label))
    elif got != want:
        fails += 1
        print("  [FAIL] %s: %s is %r, expected %r" % (where, label, got, want))
    else:
        print("  [PASS] %s: %s = %s" % (where, label, got))


def c_define(text, name):
    m = re.search(r"^\s*#define\s+" + re.escape(name) + r"\s+(.+?)\s*(/\*.*)?$", text, re.M)
    return m.group(1).strip() if m else None


def basic_define(text, name):
    m = re.search(r"^\s*\$define\s+" + re.escape(name) + r"\s+(.+?)\s*(;\*.*)?$", text, re.M)
    return m.group(1).strip() if m else None


def py_string(text, name):
    m = re.search(r"^" + re.escape(name) + r"\s*=\s*b?\"([^\"]*)\"", text, re.M)
    return m.group(1) if m else None


def basic_literal(text, literal):
    """The literal as written, if the code (not only a comment) carries it."""
    for line in text.splitlines():
        code = line.split(";*", 1)[0]
        if code.lstrip().startswith("*"):
            continue
        if ("'%s'" % literal) in code:
            return literal
    return None


def main():
    print("test-tlsconsts-units")
    print("  root     : %s" % ROOT)
    tls_h = read("gplsrc/sd_tls.h")
    keys_h = read("gplsrc/keys.h")
    syscom = read("sdsys/syscom/keys.h")
    probe = read("gplbld/scram-probe.py")
    apisrvr = read("sdsys/gpl.bp/apisrvr")
    sdclient = read("sdsys/gpl.bp/sdclient")

    for name, want in C_CONSTS.items():
        expect("gplsrc/sd_tls.h", name, c_define(tls_h, name), want)
    for name, want in KEY_CONSTS.items():
        expect("gplsrc/keys.h", name, c_define(keys_h, name), want)
    for name, want in BASIC_CONSTS.items():
        expect("sdsys/syscom/keys.h", name, basic_define(syscom, name), want)
    expect("gplbld/scram-probe.py", "GS2_BOUND", py_string(probe, "GS2_BOUND"), GS2)
    expect("gplbld/scram-probe.py", "BINDING_LABEL", py_string(probe, "BINDING_LABEL"), LABEL)
    expect("sdsys/gpl.bp/apisrvr", "GS2 literal in code", basic_literal(apisrvr, GS2), GS2)
    expect("sdsys/gpl.bp/sdclient", "GS2 literal in code", basic_literal(sdclient, GS2), GS2)

    print("\ntest-tlsconsts-units: %d checks, %d failed" % (checks, fails))
    if checks != EXPECTED_CHECKS:
        print("REFUSING - %d checks ran, expected %d (the null case)" % (checks, EXPECTED_CHECKS))
        return 2
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
