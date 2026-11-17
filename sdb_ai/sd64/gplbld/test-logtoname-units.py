#!/usr/bin/env python3
"""test-logtoname-units.py - CPROC's LOGTO takes a registered account name and nothing else.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-logtoname-units.py
  python3 .../test-logtoname-units.py --selftest [--from=N]

No sudo, no install, no sd.  Exit 0 every check passed, 1 a check failed, 2 it could not run.

17 Nov 26 dm  Written for S.62 (P-1280, P-1283, P-1282).  A name the register lacked used to be taken as a
              pathname to change directory to (the read's ELSE set acc.rec to the typed name), which let the
              administrator enter any directory holding a voc without the register; the Windows port refused it from
              13 Aug 26 and the tighter behaviour is kept.  The refusal is the 10003 an ungranted account gives, with
              the audit line 'logto refused account=<name> reason=not in the register'.  LOGTO SDSYS (into.sdsys) is
              unchanged: the administrator's way back is the system directory itself.

WHAT THIS IS NOT.  It reads sdsys/gpl.bp/cproc as TEXT, so it cannot say LOGTO refuses anybody.  The runtime rows
are sandbox-listu-a5.py section A (the administrator's LOGTO to a path refused with 10003 and the audit line, the
LOGTO by the registered name as the control) and sandbox-shared.py section L (an ordinary user's LOGTO to a path).
What this holds is the ORDER, which a later edit could break while still compiling: the refusal after the register
read and the SDSYS substitution, before the group test and before the first change of directory.

--selftest mutates the source in the ways this could plausibly be broken and requires each mutation to be CAUGHT.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CPROC = os.path.normpath(os.path.join(HERE, os.pardir, "sdsys", "gpl.bp", "cproc"))

# The anchors, each written once so that a check and its mutant cannot drift apart.
READ = "read acc.record from acc.f, downcase(new.account) then"
REFUSE = "if acc.rec = '' then"
AUDIT = "'logto refused account=' : downcase(new.account) : ' reason=not in the register'"
GROUP = "is_grp_member(@logname,acc.record<ACC$GROUP>)"
ENTER = "ospath(acc.rec, OS$CD)"
SDSYS_LINES = [
    'into.sdsys = (downcase(new.account) = "sdsys")',
    "if into.sdsys and not(kernel(K$ADMINISTRATOR, -1)) then",
    "if into.sdsys then",
    "acc.rec = @sdsys",
    "new.account = 'sdsys'",
]


def code_lines(src):
    """[(line number, text)] of int.logto, from its label to the line that sets WHO, full-line comments dropped
    (the comments quote the anchors, so a check reading them would pass on a file whose code was gone)."""
    out = []
    inside = False
    for i, line in enumerate(src.splitlines(), 1):
        if line.startswith("int.logto:"):
            inside = True
            continue
        if not inside or line.lstrip().startswith("*"):
            continue
        out.append((i, line))
        if re.match(r"^\s*who\s*=\s*new\.account\b", line):
            break
    return out


def checks(src):
    """[(name, ok, detail)]"""
    lines = code_lines(src)
    out = []

    def ck(name, ok, detail):
        out.append((name, bool(ok), detail))

    def at(needle, after=0):
        return next((n for n, ln in lines if n > after and needle in ln), None)

    ck("L0 the int.logto block is found (its label to 'who = new.account')", len(lines) > 20 and
       re.match(r"^\s*who\s*=", lines[-1][1]) is not None, f"{len(lines)} code lines, last {lines[-1] if lines else None}")
    if not lines:
        return out

    read = at(READ)
    sd = [at(s) for s in SDSYS_LINES]
    ck("L1 LOGTO SDSYS is unchanged: into.sdsys, its 10002 refusal of a non-administrator before the register read, and"
       " acc.rec = @sdsys / new.account = 'sdsys' after it",
       None not in sd and read is not None and sd[0] < sd[1] < read < sd[2] < sd[3] < sd[4],
       f"into.sdsys {sd}, read {read}")

    clear = next((n for n, ln in lines if re.match(r"^\s*acc\.rec\s*=\s*''\s*$", ln)), None)
    as_path = [n for n, ln in lines if re.match(r"^\s*acc\.rec\s*=\s*(new\.account|token)\b", ln)]
    ck("L2 acc.rec = '' before the register is read, and no line takes the typed name as the account's path",
       clear is not None and read is not None and clear < read and not as_path,
       f"acc.rec '' {clear}, read {read}, acc.rec = <typed name> at {as_path}")

    refuse = at(REFUSE)
    group = at(GROUP)
    enter = at(ENTER)
    ck("L3 a name with no register record is refused AFTER the read and the SDSYS substitution, BEFORE the group test"
       " and the first change of directory",
       None not in (refuse, read, sd[3], group, enter) and read < refuse and sd[3] < refuse < group and refuse < enter,
       f"read {read}, acc.rec = @sdsys {sd[3]}, refusal {refuse}, group test {group}, OS$CD {enter}")

    body = []
    if refuse is not None:
        for n, ln in lines:
            if n <= refuse:
                continue
            if ln.strip() == "end":
                break
            body.append(ln.strip())
    text = "\n".join(body)
    lit = re.findall(r"'([^']*)'", AUDIT)
    ck("L4 the refusal shows 10003, audits 'logto refused account=<name> reason=not in the register' in lower case,"
       " and goes back to the account it came from",
       "display sysmsg(10003)" in text and ("void kernel(K$AUDIT, " + AUDIT + ")") in text
       and all(s == s.lower() for s in lit) and "if ospath(account.path, OS$CD) then return" in text,
       repr(text[:200]))

    old = [n for n, ln in lines if re.match(r"^\s*if\s+new\.account\s*=\s*''\s+then", ln)]
    ck("L5 no name is made from the path's last directory (the old LOGTO-by-path ending is gone)", not old,
       f"'if new.account = '' then' at {old}")
    return out


def _move_refusal_below_group(src):
    """Move the not-in-the-register refusal (its if to its end) to just after the group test's block."""
    lines = src.splitlines(keepends=True)
    start = next((i for i, ln in enumerate(lines) if ln.strip() == REFUSE), None)
    if start is None:
        return src
    end = next((i for i in range(start + 1, len(lines)) if lines[i].strip() == "end"), None)
    if end is None:
        return src
    block = lines[start:end + 1]
    rest = lines[:start] + lines[end + 1:]
    g = next((i for i, ln in enumerate(rest) if GROUP in ln and i > start), None)
    if g is None:
        return src
    ge = next((i for i in range(g + 1, len(rest)) if rest[i].strip() == "end"), None)
    if ge is None:
        return src
    return "".join(rest[:ge + 1] + block + rest[ge + 1:])


MUTANTS = [
    ("the read's ELSE takes the typed name as a path again",
     lambda s: s.replace("         new.account = downcase(new.account)\n      end\n",
                         "         new.account = downcase(new.account)\n      end else\n"
                         "         acc.rec = new.account\n         new.account = ''\n      end\n", 1)),
    ("acc.rec is not cleared before the read",
     lambda s: s.replace("\n   acc.rec = ''\n   acc.record = ''\n", "\n   acc.record = ''\n", 1)),
    ("the refusal moves below the group test",
     _move_refusal_below_group),
    ("the refusal writes no audit line",
     lambda s: s.replace("      void kernel(K$AUDIT, " + AUDIT + ")\n", "", 1)),
    ("the audit words are upper case",
     lambda s: s.replace(AUDIT, "'LOGTO REFUSED ACCOUNT=' : downcase(new.account) : ' REASON=NOT IN THE REGISTER'", 1)),
    ("the refusal answers another message",
     lambda s: s.replace(REFUSE + "\n      display sysmsg(10003)", REFUSE + "\n      display sysmsg(10107, new.account)", 1)),
    ("LOGTO SDSYS loses its system directory",
     lambda s: s.replace("      acc.rec = @sdsys\n", "", 1)),
    ("the old name-from-path ending comes back",
     lambda s: s.replace("   who = new.account                     ;*",
                         "   if new.account = '' then new.account = 'x'\n   who = new.account                     ;*", 1)),
]


def selftest(src, first=0):
    print("--- self-test: each mutation must be CAUGHT by at least one check ---")
    base_bad = [n for n, ok, _ in checks(src) if not ok]
    if base_bad:
        print("REFUSING - the unmutated source already fails: %s" % ", ".join(base_bad), file=sys.stderr)
        return 2
    chosen = MUTANTS[first:]
    if not chosen:
        print(f"REFUSING - --from={first} selects no mutant (there are {len(MUTANTS)})", file=sys.stderr)
        return 2
    holes = 0
    for name, fn in chosen:
        mutated = fn(src)
        if mutated == src:
            print(f"  [FAIL] {name}: the mutation did not change the file (this test no longer understands the source)")
            holes += 1
            continue
        caught = [n.split(" ")[0] for n, ok, _ in checks(mutated) if not ok]
        if caught:
            print(f"  [pass] {name}: caught by {', '.join(caught)}")
        else:
            print(f"  [FAIL] {name}: NOT CAUGHT by any check")
            holes += 1
    print(f"\n{len(chosen) - holes} of {len(chosen)} mutants caught")
    return 1 if holes else 0


def main(argv):
    if not os.path.isfile(CPROC):
        print(f"CANNOT RUN - no {CPROC}", file=sys.stderr)
        return 2
    with open(CPROC, "rb") as f:
        src = f.read().replace(b"\r\n", b"\n").decode("latin-1")
    print(f"reading  {CPROC} ({len(src.splitlines())} lines)\n")
    if "--selftest" in argv:
        first = 0
        for a in argv:
            if a.startswith("--from="):
                try:
                    first = int(a[7:])
                except ValueError:
                    print(f"REFUSING - {a} is not a number", file=sys.stderr)
                    return 2
        return selftest(src, first)
    rows = checks(src)
    if not rows:
        print("REFUSING - no checks ran", file=sys.stderr)
        return 2
    failed = 0
    for name, ok, detail in rows:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")
        failed += 0 if ok else 1
    print(f"\n{len(rows) - failed} passed, {failed} failed")
    print("NOT MEASURED HERE: whether LOGTO refuses anybody.  That is sandbox-listu-a5.py section A.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
