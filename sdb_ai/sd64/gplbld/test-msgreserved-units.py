#!/usr/bin/env python3
"""test-msgreserved-units.py - the message-number space convention, checked.

  python3 /home/don/Projects/SDCoreLinuxProject/sdcore4linux/sdb_ai/sd64/gplbld/test-msgreserved-units.py

No sudo, no install, no sd.  Exit 0 the convention holds, 1 a violation, 2 it
could not run.  Written 20 Sep 26, W.12.

THE CONVENTION (agreed by mail, 2026-09-20T1605 / 2026-09-20T1609), because
first-come-and-tell-the-other-side had collided four times without either
side noticing three of them were deliberate and the fourth was not:

    0-10029      upstream's own (sdb64 never goes past 10029 here) - neither
                 port allocates into it.
    10030-10999  shared legacy.  Everything either port had already shipped
                 before the convention keeps its number - some of it (10919,
                 10920, 10921) was deliberately taken as the SAME number on
                 both sides, mailed at the time; a NEW collision inside this
                 range from now on is a defect, not a repeat of the old
                 practice.
    11000-11999  this port's block.  Every message THIS tree allocates from
                 today takes its next number from here.
    12000-12999  the Windows port's block, mirror image.  This is the one
                 this script can actually check FROM HERE: nothing in this
                 tree may use a number that belongs to their block, because
                 that is the collision the convention exists to rule out.

WHAT THIS DOES NOT DO.  It cannot see the Windows tree, so it cannot confirm
their side keeps out of 11000-11999 - that is their own
test-msgreserved-units.py's job, mailed as built and free-tier guarded
2026-09-20T1609.  It also does not distinguish a genuinely new allocation from
a pre-convention shared-legacy one within 10030-10999 - by design: the
09-19/09-20 mail thread is the record of which of those were deliberate
(10919-10921) and which was not (10922, since moved to the port's 12000), and
re-deriving that from the numbers alone is not this check's job.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MESSAGES = os.path.abspath(os.path.join(HERE, os.pardir, "sdsys", "messages"))

UPSTREAM = range(0, 10030)
SHARED_LEGACY = range(10030, 11000)
OUR_BLOCK = range(11000, 12000)
WINDOWS_BLOCK = range(12000, 13000)


def message_ids(messages_dir):
    """[(id, path)] for every all-digit filename, sorted."""
    out = []
    for name in os.listdir(messages_dir):
        if name.isdigit():
            out.append((int(name), os.path.join(messages_dir, name)))
    return sorted(out)


def main():
    if not os.path.isdir(MESSAGES):
        print(f"CANNOT RUN - no message directory at {MESSAGES}", file=sys.stderr)
        return 2

    ids = message_ids(MESSAGES)
    if not ids:
        print("REFUSING - no numeric message files found; the null case "
              "would pass this check by having nothing to violate it",
              file=sys.stderr)
        return 2

    print(f"reading {MESSAGES}: {len(ids)} numeric messages, "
          f"{ids[0][0]}-{ids[-1][0]}\n")

    counts = {"upstream (0-10029)": 0, "shared legacy (10030-10999)": 0,
              "this port's block (11000-11999)": 0}
    violations = []
    for num, path in ids:
        if num in UPSTREAM:
            counts["upstream (0-10029)"] += 1
        elif num in SHARED_LEGACY:
            counts["shared legacy (10030-10999)"] += 1
        elif num in OUR_BLOCK:
            counts["this port's block (11000-11999)"] += 1
        elif num in WINDOWS_BLOCK:
            violations.append((num, path))
        else:
            violations.append((num, path))  # above 12999 - nobody's block yet

    for label, n in counts.items():
        print(f"  {label}: {n}")

    if violations:
        print(f"\n[FAIL] {len(violations)} message(s) outside the agreed ranges:",
              file=sys.stderr)
        for num, path in violations:
            where = ("the Windows port's reserved block (12000-12999)"
                     if num in WINDOWS_BLOCK else "above any agreed block (13000+)")
            print(f"  {num} ({path}) - in {where}", file=sys.stderr)
        return 1

    print(f"\n[PASS] all {len(ids)} messages sit inside the agreed ranges; "
          f"none in the Windows port's block (12000-12999)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
