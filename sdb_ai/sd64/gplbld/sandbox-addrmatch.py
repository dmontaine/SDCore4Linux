#!/usr/bin/env python3
#
# sandbox-addrmatch.py - S.256: !addrmatch, the rule of the remote-API door for SDSYS (remote.sdsys api).  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-addrmatch.py <dir> [--build]
#
# <dir> is a sandbox made by sandbox-fromtree.py (needs a `make`d bin/sd).  With --build it is built first from THIS tree (it must be
# empty or absent).  Exit 0 every row passed, 1 a row failed, 2 it could not run.
#
# START-HISTORY:
# 16 Nov 26 dm  New (S.256).
# END-HISTORY
#
# THE ORACLE IS PYTHON'S ipaddress, NOT THIS FILE'S EXPECTATIONS: for each case the wanted answer is computed here as "the peer address is
# inside the network" (ip_address(peer) in ip_network(entry), with an IPv4-mapped peer taken as its IPv4 form and a /0 entry never matching),
# and the entries are written in the root helper's own form (str(ip_network(x, strict=False))).  The BASIC program prints 1 or 0 for each.
# The cases that cannot be in a range (a peer that is not an address, an entry of the other family, a /0, an empty list) and the word any
# are the controls: the first answer 0 and the last 1 whatever the bits are, so an instrument that printed the same answer for every row
# would fail some of them.

import ipaddress
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sandbox-fromtree.py")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
passed = failed = 0


def helper_form(x):
    """An entry as sd-elevate sdsys-api writes it."""
    return str(ipaddress.ip_network(x, strict=False))


def oracle(peer, entries):
    if "any" in entries:
        return 1
    p = peer.strip().lower()
    if p.startswith("::ffff:") and "." in p:
        p = p[7:]
    try:
        a = ipaddress.ip_address(p)
    except ValueError:
        return 0
    for e in entries:
        try:
            n = ipaddress.ip_network(e)
        except ValueError:
            continue
        if n.prefixlen == 0 or n.version != a.version:
            continue
        if a in n:
            return 1
    return 0


# (label, peer, entries as the administrator typed them; each is put in the helper's form unless it is 'any' or deliberately bad)
RAW = [
    ("an exact IPv4 address, listed", "192.168.1.20", ["192.168.1.20"]),
    ("an exact IPv4 address, another one listed", "192.168.1.21", ["192.168.1.20"]),
    ("inside a /24", "192.168.1.200", ["192.168.1.0/24"]),
    ("just outside a /24", "192.168.2.1", ["192.168.1.0/24"]),
    ("a /24 typed with host bits (the helper clears them)", "192.168.1.7", ["192.168.1.99/24"]),
    ("inside a /20 whose boundary is not on a dot", "10.1.15.254", ["10.1.0.0/20"]),
    ("just outside that /20", "10.1.16.1", ["10.1.0.0/20"]),
    ("a /31 holds both its addresses", "172.16.0.1", ["172.16.0.0/31"]),
    ("the second of several entries", "203.0.113.9", ["198.51.100.0/24", "203.0.113.9", "10.0.0.0/8"]),
    ("an IPv4-mapped IPv6 peer, compared as IPv4", "::ffff:192.168.1.20", ["192.168.1.20"]),
    ("an IPv4-mapped peer outside the range", "::ffff:192.168.9.20", ["192.168.1.0/24"]),
    ("IPv6 exact, the same spelling", "2001:db8::1", ["2001:db8::1"]),
    ("IPv6 exact, spelt in full with leading zeros", "2001:0db8:0000:0000:0000:0000:0000:0001", ["2001:db8::1"]),
    ("IPv6 in upper case", "2001:DB8::1", ["2001:db8::1"]),
    ("IPv6 inside a /64", "fd00:1:2:3:aaaa:bbbb:cccc:dddd", ["fd00:1:2:3::/64"]),
    ("IPv6 just outside that /64", "fd00:1:2:4::1", ["fd00:1:2:3::/64"]),
    ("IPv6 inside a /56 not on a group boundary", "fd00:1:2:ff::9", ["fd00:1:2::/56"]),
    ("IPv6 just outside that /56", "fd00:1:2:100::9", ["fd00:1:2::/56"]),
    ("the :: address", "::", ["::/128"]),
    ("a :: at the end", "fe80:1::", ["fe80:1::/128"]),
    ("CONTROL: the word any admits an IPv4 address", "198.51.100.77", ["any"]),
    ("CONTROL: the word any admits an IPv6 address", "2001:db8:ffff::1", ["any"]),
    ("CONTROL: the word any admits even a peer that is not an address", "nonsense", ["any"]),
    ("CONTROL: an IPv4 peer is not in an IPv6 range", "10.0.0.1", ["fd00::/8"]),
    ("CONTROL: an IPv6 peer is not in an IPv4 range", "fd00::1", ["10.0.0.0/8"]),
    ("CONTROL: a peer that is not an address", "not.an.ip", ["10.0.0.0/8"]),
    ("CONTROL: an IPv4 peer with a part over 255", "10.0.0.256", ["10.0.0.0/8"]),
    ("CONTROL: an IPv6 peer with two ::", "fd00::1::2", ["fd00::/8"]),
    ("CONTROL: an IPv6 peer with a group of five digits", "fd00::12345", ["fd00::/8"]),
    ("CONTROL: the empty list", "10.0.0.1", []),
    ("CONTROL: an empty peer", "", ["10.0.0.0/8"]),
]
BAD = [   # entries the helper would never write: the routine must not match them (wanted 0 whatever the peer)
    ("CONTROL: a /0 entry is never matched (only the word any is every address)", "10.0.0.1", ["0.0.0.0/0"]),
    ("CONTROL: an IPv6 /0 entry is never matched", "fd00::1", ["::/0"]),
    ("CONTROL: a length over the family's width", "10.0.0.1", ["10.0.0.1/33"]),
    ("CONTROL: a length that is not a number", "10.0.0.1", ["10.0.0.1/x"]),
    ("CONTROL: an entry with no length", "10.0.0.1", ["10.0.0.1"]),
]

CASES = []
for label, peer, ents in RAW:
    written = [e if e == "any" else helper_form(e) for e in ents]
    CASES.append((label, peer, written, oracle(peer, written)))
for label, peer, ents in BAD:
    CASES.append((label, peer, ents, 0))


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
    say("sandbox-addrmatch: CANNOT RUN - " + msg)
    sys.exit(2)


def basic_str(s):
    return "'" + s + "'" if "'" not in s else '"' + s + '"'


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        bail("usage: sandbox-addrmatch.py <dir> [--build]")
    box = os.path.abspath(args[0])
    sysd = os.path.join(box, "sys")
    say("sandbox-addrmatch: sandbox %s" % box)
    if "--build" in sys.argv:
        if os.path.exists(box) and os.listdir(box):
            bail("%s is not empty" % box)
        r = subprocess.run([sys.executable, TOOL, box, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-addrmatch: built, bootstrap passed")
    elif not os.path.isfile(os.path.join(sysd, "bin", "sd")):
        bail("%s holds no built sandbox (use --build, or point it at one)" % box)
    subprocess.run([sys.executable, TOOL, box, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    # The null case: the sandbox must hold the routine, or every row would be a compile error
    if not os.path.isfile(os.path.join(sysd, "gpl.bp", "addrmatch")):
        bail("the sandbox's gpl.bp has no addrmatch")

    nm = "zzaddrm"
    lines = []
    for i, (_l, peer, ents, _w) in enumerate(CASES):
        lines.append("   lst = ''")
        for e in ents:
            lines.append("   lst<-1> = %s" % basic_str(e))
        lines.append("   ok = 9")
        lines.append("   call !addrmatch(%s, lst, ok)" % basic_str(peer))
        lines.append("   crt 'A%03d[':(if ok then 1 else 0):']'" % i)
    with open(os.path.join(sysd, "bp", nm), "w") as f:
        f.write("\n".join(lines) + "\n   crt 'ADDRM.END'\nend\n")
    try:
        p = subprocess.run([sys.executable, TOOL, box, "sess", os.path.join(box, "user_accounts"), "BASIC bp %s" % nm, "RUN bp %s" % nm],
                           capture_output=True, text=True, errors="replace", timeout=600)
        out = ANSI.sub("", p.stdout + p.stderr)
        row("setup: the test program compiled and ran to its end (null case: no answers would fail every row anyway)",
            "ADDRM.END" in out, out[-600:])
        say("\n--- !addrmatch against Python's ipaddress --------------------------------------")
        for i, (label, peer, ents, want) in enumerate(CASES):
            m = re.search(r"(?m)^A%03d\[(\d)\]\s*$" % i, out)
            got = int(m.group(1)) if m else None
            row("%s: peer %r, list %r, wanted %d" % (label, peer, ents, want), got == want, "got %r" % got if m else "no output")
    finally:
        for d in ("bp", "bp.out"):
            pth = os.path.join(sysd, d, nm)
            if os.path.exists(pth):
                os.remove(pth)

    nyes = sum(1 for c in CASES if c[3] == 1)
    say("\n(%d cases want 1 and %d want 0)" % (nyes, len(CASES) - nyes))
    say("\nsandbox-addrmatch: %d passed, %d failed" % (passed, failed))
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
