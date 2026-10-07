#!/usr/bin/env python3
"""test-privcmd-units.py - CPROC's privileged-command match must not depend on the case of a name.

WHY THIS EXISTS (PAL-1 stage 3a, 6 Oct 2026).  CPROC raises root privilege for five catalogued verbs
(CREATE.ACCOUNT, DELETE.ACCOUNT, MODIFY.ACCOUNT, MODIFY.PASSWORD, RESTORE.ACCOUNT) by LOCATE-ing the
catalogue name in field 3 of the verb's VOC record in an upper-case list.  LOCATE is case sensitive.
When program names became lower case, a record carrying "$createa" would have matched nothing, the
privilege step would have been skipped, and the verb would have run without the privilege it needs -
silently.  The match is now `locate upcase(s) in privileged_commands<1>`.  This check keeps it so.

It reads source only: no SD, no install, no sudo.  Exit 0 all rows passed, 1 a row failed.

  python3 gplbld/test-privcmd-units.py
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SDSYS = os.path.normpath(os.path.join(HERE, os.pardir, "sdsys"))
CPROC = os.path.join(SDSYS, "gpl.bp", "cproc")
LAYERS = [os.path.join(SDSYS, "newvoc"), os.path.join(SDSYS, "voc_template")]

passed = failed = 0


def row(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print("  [PASS] " + name)
    else:
        failed += 1
        print("  [FAIL] " + name + ("   <- " + detail if detail else ""))


def read(p):
    with open(p, "rb") as f:
        return f.read().replace(b"\r\n", b"\n").decode("latin-1")


LOCATE_NEW = re.compile(r"^\s*locate\s+upcase\(\s*s\s*\)\s+in\s+privileged_commands<1>\s+setting\s+priv_required\s+then\s*$",
                        re.I | re.M)
LOCATE_OLD = re.compile(r"^\s*locate\s+s\s+in\s+privileged_commands<1>", re.I | re.M)


def privileged_list(src):
    return re.findall(r'^\s*privileged_commands<-1>\s*=\s*"([^"]+)"', src, re.M)


def voc_ca_names():
    """{layer/record: field-3 name} for every CA (catalogued program) VOC record."""
    out = {}
    for d in LAYERS:
        for n in sorted(os.listdir(d)):
            p = os.path.join(d, n)
            if os.path.isfile(p):
                lines = read(p).split("\n")
                if len(lines) >= 3 and lines[1].strip().upper() == "CA":
                    out[os.path.basename(d) + "/" + n] = lines[2].strip()
    return out


def matches(field3, listed, case_blind):
    return (field3.upper() if case_blind else field3) in listed


def main():
    if not os.path.isfile(CPROC):
        print("test-privcmd-units: CANNOT RUN - %s is missing" % CPROC)
        return 2
    src = read(CPROC)
    listed = privileged_list(src)
    print("test-privcmd-units: cproc   %s" % CPROC)
    print("test-privcmd-units: listed  %s" % " ".join(listed))
    row("the list holds the five privileged catalogue names, upper case",
        sorted(listed) == sorted(["$CREATEA", "$DELACC", "$MODIFYA", "$MODIFY.PASSWORD", "$RESTOREA"])
        and all(x == x.upper() for x in listed), repr(listed))
    row("the match is case blind: locate upcase(s) in privileged_commands", LOCATE_NEW.search(src) is not None,
        "the locate line is not `locate upcase(s) in privileged_commands<1> setting priv_required then`")
    row("and the exact-case form is gone", LOCATE_OLD.search(src) is None, "a `locate s in privileged_commands` is still there")

    ca = voc_ca_names()
    for entry in listed:
        hits = sorted(k for k, v in ca.items() if v.upper() == entry)
        row("%s is reachable: a VOC record names it (%s)" % (entry, ", ".join(hits) or "none"), bool(hits))

    # the model of why: the same list, a record spelt three ways
    for entry in listed:
        variants = [entry, entry.lower(), entry[:2] + entry[2:].lower()]
        row("%s: case-blind match finds all of %s" % (entry, variants),
            all(matches(v, listed, True) for v in variants))
        row("%s: the OLD exact match misses the lower-case spelling (this is the hole)" % entry,
            not matches(entry.lower(), listed, False))

    # CONTROL: the check can fail.  A cproc with the old line must be refused by the first two rows.
    mutant = LOCATE_NEW.sub("                  locate s in privileged_commands<1> setting priv_required then", src)
    row("CONTROL: a cproc with the old exact locate is refused by this check",
        LOCATE_NEW.search(mutant) is None and LOCATE_OLD.search(mutant) is not None)
    print("test-privcmd-units: %d passed, %d failed" % (passed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
