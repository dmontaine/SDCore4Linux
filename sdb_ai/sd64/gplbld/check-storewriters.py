#!/usr/bin/env python3
#
# check-storewriters.py - does every program that WRITES a root-only system
#                         store run with euid 0?  PORT_ADOPTION queue 22, the
#                         port's verify-sdsyswrite re-expressed for Linux.
#
#   python3 /home/don/Projects/sdcore4linux/sdb_ai/sd64/gplbld/check-storewriters.py
#   python3 .../check-storewriters.py --selftest
#
# No sudo, no install, no sd.  Exit 0 every writer is privileged, 1 a writer is
# not, 2 the check could not run (or found nothing to check).
#
# ===========================================================================
# WHAT IT CATCHES
# ===========================================================================
# The port's PRE_RELEASE_FIXES 68: an administrative verb whose store write was
# a plain openpath/write by the SD process, in a session whose token never had
# the right to it - so the verb "worked" through its helper half and silently
# failed its file half.  On Linux the shape is the euid.  A "sudo sd" session
# drops to euid sdsys at entry (CPROC's root-entry block, !EUID_SET), and CPROC
# raises it back to 0 only around the verbs in privileged_commands.  accounts
# and $cred are root-owned (installsdai.sh), so a write to either from any
# other verb fails however administrative the session is.
#
# WHY A STATIC CHECK AND NOT ONLY A WITNESS.  The witness (witness-release-run.sh
# section 13g) proves the four verbs that exist today land their writes.  It
# cannot see the fifth verb somebody adds tomorrow.  This reads the source, so
# it runs on every change, which is when that verb would appear.
#
# ===========================================================================
# HOW IT DECIDES
# ===========================================================================
# 1. STORES: the root-owned directories in the system tree, named below with the
#    installer line that makes them so.  Printed.
# 2. WRITERS: a gpl.bp record that opens one of them - openpath @sdsys:@ds:'x'
#    to VAR - and then writes or deletes on THAT variable (write/writeu/writev/
#    writevu/matwrite ... to|on VAR, delete VAR).  Reading is not writing: LOGIN,
#    TIERGATE and APISRVR open the register and are rightly not writers.
# 3. CALLERS: a writer catalogued as a subroutine (!NAME) is followed to every
#    record that calls it (call !NAME, or deffun ... calling '!NAME'), until a
#    verb ($NAME) is reached.  A subroutine nobody calls is reported, not passed.
# 4. VERDICT: each verb reached must be in CPROC's privileged_commands.
#
# ***IT REFUSES THE NULL CASE OUT LOUD.***  No stores found on disk, no writers
# found, or an empty privileged_commands list each exit 2: a sweep that found
# nothing cannot tell "all privileged" from "looked in the wrong place".
#
# LIMITS, STATED: a write through a file variable passed in from elsewhere, or a
# store path built at run time rather than written literally, is invisible to
# this.  None exists today (the sweep prints every openpath it saw).
#

import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.dirname(HERE)

# The root-only stores.  installsdai.sh makes the register root:root and $cred
# root:root 0700; verify-sysperms.py and witness-release-run.sh C7 measure them.
STORES = ["accounts", "$cred"]

OPEN_RE = re.compile(r"""openpath\s+@sdsys\s*:\s*@ds\s*:\s*['"]([^'"]+)['"]\s+to\s+([a-z0-9._$]+)""", re.I)
CATALOG_RE = re.compile(r"^\s*\$catalog\s+(\S+)", re.I | re.M)
PRIV_RE = re.compile(r"""privileged_commands\s*<\s*-1\s*>\s*=\s*['"]([^'"]+)['"]""", re.I)


def write_re(var):
    v = re.escape(var)
    return re.compile(
        r"^\s*(?:(?:write|writeu|writev|writevu|matwrite|matwriteu)\b.*\b(?:to|on)\s+" + v + r"\s*,"
        r"|delete\s+" + v + r"\s*,)", re.I)


def strip_comment(line):
    s = line.lstrip()
    if s.startswith("*") or s.startswith("!"):
        return ""
    # a trailing ";*" comment
    cut = line.find(";*")
    return line if cut < 0 else line[:cut]


def load(bp):
    recs = {}
    for name in sorted(os.listdir(bp)):
        path = os.path.join(bp, name)
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                recs[name] = f.read().split("\n")
    return recs


def check(bp, cproc_path, out=print):
    out("check-storewriters")
    out("  gpl.bp   : %s" % bp)
    out("  cproc    : %s" % cproc_path)
    out("  stores   : %s" % ", ".join(STORES))
    if not os.path.isdir(bp) or not os.path.isfile(cproc_path):
        out("check-storewriters: CANNOT RUN - gpl.bp or cproc not found.")
        return 2

    recs = load(bp)
    with open(cproc_path, "r", encoding="utf-8", errors="replace") as f:
        priv = [p.upper() for p in PRIV_RE.findall(f.read())]
    out("  privileged_commands: %s" % (", ".join(priv) or "(none)"))
    if not priv:
        out("check-storewriters: CANNOT RUN - no privileged_commands found in cproc.")
        return 2

    catalog = {}
    for name, lines in recs.items():
        m = CATALOG_RE.search("\n".join(lines))
        catalog[name] = m.group(1).upper() if m else ""

    # 2. writers
    writers = {}   # record -> [(lineno, text)]
    opens_seen = 0
    for name, lines in recs.items():
        vars_ = {}
        for i, raw in enumerate(lines, 1):
            line = strip_comment(raw)
            for store, var in OPEN_RE.findall(line):
                if store in STORES:
                    vars_[var.lower()] = store
                    opens_seen += 1
        for var, store in vars_.items():
            rx = write_re(var)
            for i, raw in enumerate(lines, 1):
                line = strip_comment(raw)
                if line and rx.search(line):
                    writers.setdefault(name, []).append((i, "%s <- %s" % (store, raw.strip())))
    out("  opens of a store seen: %d" % opens_seen)
    if not writers:
        out("check-storewriters: CANNOT RUN - no record writes a store, which cannot be true "
            "of a tree that sets passwords; the sweep is looking in the wrong place.")
        return 2

    # 3. callers of a subroutine
    def callers(sub):
        bare = re.escape(sub.lstrip("!"))
        rx = re.compile(r"(?:call\s+!" + bare + r"\b|calling\s+['\"]!" + bare + r"['\"])", re.I)
        found = []
        for name, lines in recs.items():
            for raw in lines:
                if strip_comment(raw) and rx.search(raw):
                    found.append(name)
                    break
        return found

    bad = 0
    for name in sorted(writers):
        cat = catalog.get(name, "")
        out("")
        out("  WRITER %s  (catalogued as %s)" % (name, cat or "nothing"))
        for ln, text in writers[name]:
            out("      %s:%d  %s" % (name, ln, text[:110]))
        verbs, seen, todo = set(), set(), [(name, cat)]
        orphan = False
        while todo:
            rec, c = todo.pop()
            if rec in seen:
                continue
            seen.add(rec)
            if c.startswith("$"):
                verbs.add(c)
            elif c.startswith("!"):
                cs = [x for x in callers(c) if x != rec]
                out("      %s is a subroutine; called from: %s" % (c, ", ".join(cs) or "NOBODY"))
                if not cs:
                    orphan = True
                for x in cs:
                    todo.append((x, catalog.get(x, "")))
            else:
                out("      %s has no $catalog name, so no verb can be found for it" % rec)
                orphan = True
        for v in sorted(verbs):
            ok = v in priv
            out("      verb %-20s %s" % (v, "PRIVILEGED" if ok else "NOT IN privileged_commands"))
            if not ok:
                bad += 1
        if orphan:
            bad += 1
            out("      FAIL: a path to this writer ends somewhere that is not a verb")

    out("")
    out("  writers: %d   failures: %d" % (len(writers), bad))
    if bad:
        out("check-storewriters: FAILED - a store is written from a verb that runs with euid sdsys.")
        return 1
    out("check-storewriters: PASSED - every store writer runs inside a privileged verb.")
    return 0


def selftest():
    """Fixture trees: one clean, and each red case firing on its own."""
    cproc = 'privileged_commands<-1> = "$GOOD"\n'
    cases = [
        ("clean: a privileged verb writes the register", 0, {
            "good": "$catalog $GOOD\nopenpath @sdsys:@ds:'accounts' to acc.f else stop\nwrite r to acc.f, id\n"}),
        ("clean: a subroutine writes $cred, called only by a privileged verb", 0, {
            "good": "$catalog $GOOD\ncall !CSET(a)\n",
            "cset": "$catalog !CSET\nopenpath @sdsys:@ds:'$cred' to c.f else return\nwrite r to c.f, id\n"}),
        ("red: an unprivileged verb writes the register", 1, {
            "good": "$catalog $GOOD\nopenpath @sdsys:@ds:'accounts' to acc.f else stop\nread r from acc.f, id else null\n",
            "bad": "$catalog $BAD\nopenpath @sdsys:@ds:'accounts' to acc.f else stop\nwrite r to acc.f, id\n"}),
        ("red: the subroutine is also called by an unprivileged verb", 1, {
            "good": "$catalog $GOOD\ncall !CSET(a)\n",
            "bad": "$catalog $BAD\ndeffun cset(a) calling '!CSET'\n",
            "cset": "$catalog !CSET\nopenpath @sdsys:@ds:'$cred' to c.f else return\ndelete c.f, id\n"}),
        ("red: a subroutine that writes and that nobody calls", 1, {
            "cset": "$catalog !CSET\nopenpath @sdsys:@ds:'$cred' to c.f else return\nwrite r to c.f, id\n"}),
        ("null: nothing writes a store", 2, {
            "good": "$catalog $GOOD\nopenpath @sdsys:@ds:'accounts' to acc.f else stop\nread r from acc.f, id else null\n"}),
        ("not a write: a commented-out write", 2, {
            "good": "$catalog $GOOD\nopenpath @sdsys:@ds:'accounts' to acc.f else stop\n* write r to acc.f, id\n"}),
    ]
    failed = 0
    for title, want, files in cases:
        with tempfile.TemporaryDirectory() as d:
            bp = os.path.join(d, "gpl.bp")
            os.mkdir(bp)
            for n, body in files.items():
                with open(os.path.join(bp, n), "w") as f:
                    f.write(body)
            cp = os.path.join(d, "cproc")
            with open(cp, "w") as f:
                f.write(cproc)
            got = check(bp, cp, out=lambda s: None)
        ok = got == want
        failed += 0 if ok else 1
        print("  [%s] %s: expected exit %d, got %d" % ("PASS" if ok else "FAIL", title, want, got))
    print("selftest: %d cases, %d failed" % (len(cases), failed))
    return 1 if failed else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv[1:]:
        sys.exit(selftest())
    bp = os.path.join(SD64, "sdsys", "gpl.bp")
    sys.exit(check(bp, os.path.join(bp, "cproc")))
