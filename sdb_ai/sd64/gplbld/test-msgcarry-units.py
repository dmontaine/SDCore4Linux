#!/usr/bin/env python3
"""test-msgcarry-units.py - a program shipped in BOTH Linux products never cites a message number that means two things.

    python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-msgcarry-units.py
    python3 .../test-msgcarry-units.py --selftest
    python3 .../test-msgcarry-units.py --core DIR --solo DIR      (two sdsys directories to read instead)

Exit 0 every row passed, 1 a program cites a number whose text differs between the products, 2 it measured nothing.
NO INSTALL, NO SUDO, NO SD.

WHY (Core-vs-Solo audit, 9 Oct 2026).  The 11000-11999 block belongs to Linux, and BOTH Linux products allocate
from it on their own: 11002 and 11010-11037 are one thing in the full product (restore, the case walk) and
another in Solo (the password dialogue, the global catalogue).  Nothing is wrong while each product's programs
cite their own numbers.  The hazard is a CARRY: a fix copied from one tree to the other with its sysmsg(N)
calls, which then print the other product's text.  Solo renumbers when it carries (upgrade_nocase uses 11060-11065),
but that was by hand.  This check looks for the failure itself: a program present in both gpl.bp directories that
cites a number on both sides while the two messages/N files differ.

A DELIBERATE difference is listed in ALLOWED with its reason (the same program, the same number, the wording is
Solo's on purpose).  Anything else fails.  A number cited on one side only is not a finding: the other tree's
program is different code and cites its own.

NULL CASE: fewer than 20 shared programs, or no differing message at all, means the reader or the trees are
wrong, not that all is well - exit 2.
"""
import filecmp
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CORE = os.path.normpath(os.path.join(HERE, "..", "sdsys"))
SOLO = "/home/don/Projects/SDCore4LinuxSolo/sdb_ai/sd64/sdsys"
CITE = re.compile(r"sysmsg\(\s*(\d+)")
ALLOWED = {
    ("login", "10002"): "SDSYS is entered by sudo in Core; Solo has no sdsys and says type admin",
    ("login", "10172"): "update.accounts all: Core says log in as sdsys, Solo says the installer runs it",
    ("backupa", "13006"): "the syntax line: Solo has one account, so no names",
    ("restorea", "13016"): "the syntax line: Solo has one account, so no names",
}
passed = failed = 0


def row(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print("  [PASS] " + name)
    else:
        failed += 1
        print("  [FAIL] " + name + ("   <- " + detail if detail else ""))


def cites(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return set()
    out = set()
    for line in text.split("\n"):
        s = line.strip()
        if s.startswith("*") or s.startswith("!"):
            continue
        out.update(CITE.findall(line))
    return out


def differing(core, solo):
    a = set(os.listdir(os.path.join(core, "messages")))
    b = set(os.listdir(os.path.join(solo, "messages")))
    return {n for n in a & b
            if not filecmp.cmp(os.path.join(core, "messages", n), os.path.join(solo, "messages", n), shallow=False)}


def findings(core, solo):
    """Returns (shared program count, differing message count, [(program, number)] cited on both sides)."""
    diff = differing(core, solo)
    ga, gb = os.path.join(core, "gpl.bp"), os.path.join(solo, "gpl.bp")
    shared = sorted(p for p in set(os.listdir(ga)) & set(os.listdir(gb)) if os.path.isfile(os.path.join(ga, p)))
    bad = []
    for p in shared:
        for n in sorted(cites(os.path.join(ga, p)) & cites(os.path.join(gb, p)) & diff):
            bad.append((p, n))
    return len(shared), len(diff), bad


def run(core, solo):
    global passed, failed
    passed = failed = 0
    print("Core %s\nSolo %s" % (core, solo))
    for d in (core, solo):
        if not os.path.isdir(os.path.join(d, "gpl.bp")) or not os.path.isdir(os.path.join(d, "messages")):
            print("test-msgcarry-units: NOTHING MEASURED - no gpl.bp/messages under %s" % d)
            return 2
    n_shared, n_diff, bad = findings(core, solo)
    print("%d programs in both trees, %d message numbers whose text differs" % (n_shared, n_diff))
    if n_shared < 20 or n_diff == 0:
        print("test-msgcarry-units: NOTHING MEASURED - a reader that sees so little is broken, or the trees are not what they were")
        return 2
    unexpected = [(p, n) for p, n in bad if (p, n) not in ALLOWED]
    for p, n in bad:
        if (p, n) in ALLOWED:
            print("  allowed: %s cites %s on both sides - %s" % (p, n, ALLOWED[(p, n)]))
    row("no shared program cites a number whose text differs, apart from the %d listed" % len(ALLOWED),
        not unexpected, repr(unexpected[:6]))
    stale = [k for k in ALLOWED if k not in bad] if (core, solo) == (CORE, SOLO) else []
    row("every ALLOWED entry is still a real difference (a stale one hides nothing, but should go)", not stale, repr(stale))
    print("test-msgcarry-units: %d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


def selftest():
    base = tempfile.mkdtemp(prefix="msgcarry-")
    ok = True
    try:
        def tree(name, texts, progs):
            d = os.path.join(base, name)
            os.makedirs(os.path.join(d, "gpl.bp"))
            os.makedirs(os.path.join(d, "messages"))
            for n, t in texts.items():
                with open(os.path.join(d, "messages", n), "w") as f:
                    f.write(t)
            for p, body in progs.items():
                with open(os.path.join(d, "gpl.bp", p), "w") as f:
                    f.write(body)
            return d

        progs = {"prog%d" % i: "crt sysmsg(%d)\n" % (11000 + i) for i in range(25)}
        same = {str(11000 + i): "text %d" % i for i in range(25)}
        c = tree("core", same, progs)
        s = tree("solo", same, progs)
        # a difference nobody cites on both sides is only a difference: the control, exit 2 when none differ at all
        sys.stdout = open(os.devnull, "w")
        try:
            rc_none = run(c, s)
        finally:
            sys.stdout = sys.__stdout__
        print("  [%s] null case: no message differs, so nothing is measured (exit %d)" % ("ok" if rc_none == 2 else "MISSED", rc_none))
        ok &= rc_none == 2
        # mutant: the same program cites the same number on both sides and the text differs
        with open(os.path.join(s, "messages", "11003"), "w") as f:
            f.write("a different meaning")
        sys.stdout = open(os.devnull, "w")
        try:
            rc_bad = run(c, s)
        finally:
            sys.stdout = sys.__stdout__
        print("  [%s] mutant: prog3 cites 11003 in both and the text differs (exit %d)" % ("caught" if rc_bad == 1 else "MISSED", rc_bad))
        ok &= rc_bad == 1
        # control: the same difference, but only the Core program cites it
        with open(os.path.join(s, "gpl.bp", "prog3"), "w") as f:
            f.write("crt sysmsg(11999)\n")
        with open(os.path.join(s, "messages", "11999"), "w") as f:
            f.write("solo only")
        with open(os.path.join(c, "messages", "11999"), "w") as f:
            f.write("core only")
        # prog3 now cites 11999 on both sides (different text) -> still a finding; make Core's cite something else
        with open(os.path.join(c, "gpl.bp", "prog3"), "w") as f:
            f.write("crt sysmsg(11003)\n")
        sys.stdout = open(os.devnull, "w")
        try:
            rc_ctl = run(c, s)
        finally:
            sys.stdout = sys.__stdout__
        print("  [%s] control: a differing number cited on one side only is not a finding (exit %d)" % ("ok" if rc_ctl == 0 else "MISSED", rc_ctl))
        ok &= rc_ctl == 0
        sys.stdout = open(os.devnull, "w")
        try:
            rc_real = run(CORE, SOLO)
        finally:
            sys.stdout = sys.__stdout__
        print("  [%s] the real trees (exit %d)" % ("ok" if rc_real == 0 else "MISSED", rc_real))
        ok &= rc_real == 0
        print("selftest: %s" % ("all behaved" if ok else "A ROW DID NOT BEHAVE"))
        return 0 if ok else 1
    finally:
        shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    core, solo = CORE, SOLO
    if "--core" in sys.argv:
        core = sys.argv[sys.argv.index("--core") + 1]
    if "--solo" in sys.argv:
        solo = sys.argv[sys.argv.index("--solo") + 1]
    sys.exit(run(core, solo))
