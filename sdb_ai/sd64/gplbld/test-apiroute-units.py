#!/usr/bin/env python3
"""test-apiroute-units.py - the sdapi gate in APISRVR, as invariants.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-apiroute-units.py
  python3 .../test-apiroute-units.py --selftest

No sudo, no install, no sd.  Exit 0 all checks passed, 1 a check failed, 2 it
could not run.  Written 20 Sep 26 for S.29 part 3.

17 Nov 26 dm  S.62 (P-1277): rows R0-R5 hold request 3's new order (every name
              folded; account.path and acc.rec cleared before the register read;
              no register record refused with the branch=1 audit line and 10003
              before account.entry.check and OS$CD; no typed name in account.path),
              with six mutants from M_S62: --selftest --from=5 runs only those.
17 Nov 26 dm  S.62 (P-4638, P-4639): rows E0-E3 hold account.entry.check's
              empty-group refusal (branch=3 no.group.in.register, after the
              suspended test, before is_grp_member, SDSYS's own entry exempt),
              with five mutants from M_S62B: --selftest --from=11.

***WHAT THIS IS AND, MORE IMPORTANTLY, WHAT IT IS NOT.***  It reads
sdsys/gpl.bp/apisrvr as text.  ***IT DOES NOT RUN BASIC, SO IT CANNOT SAY THE
GATE REFUSES ANYBODY*** - only that the gate is still written, still in the
right place, and still shaped the way S.29 needs.  The refusal itself is
measured on an install, by witness-release-run.sh section 13f, which drives a
real SCRAM login for an account whose route has been taken away.  A green run
here is not evidence that the API is gated; it is evidence that nothing has
quietly deleted or reordered the gate since the cycle that measured it.

WHY A TEXT CHECK IS WORTH HAVING ANYWAY.  There is no way to compile or run
GPL.BP without an install (the two-stage bootstrap, CLAUDE.md "Testing"), so
between cycles the only guard on this code is a reader.  Three of these
invariants are ORDERING, which is exactly the kind of thing a later edit breaks
silently: a gate moved below K$SET.USERNAME still compiles, still looks right in
a diff, and admits a session that has already become the user.

***AND THE CHECKS ARE THEMSELVES CHECKED.***  --selftest mutates the source in
the ways this gate could plausibly be broken and requires each mutation to be
CAUGHT.  A structural test nobody has driven against a broken input is the
"test that passes because it did nothing" CLAUDE.md names: it would pass just as
happily against a file it had failed to understand.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SDSYS = os.path.abspath(os.path.join(HERE, os.pardir, "sdsys"))
APISRVR = os.path.join(SDSYS, "gpl.bp", "apisrvr")
MESSAGES = os.path.join(SDSYS, "messages")

# The anchors, each written once so a check and its mutant cannot drift apart.
GATE = "is_grp_member(scram.user, 'sdapi')"
SDUSERS = "is_grp_member(scram.user, 'sdusers')"
REFUSAL = "sysmsg(10073, scram.user)"
EXEMPT = "not(downcase(scram.user) = 'sdsys')"
IDENTITY = "kernel(K$SET.USERNAME, scram.user)"


def code_lines(src):
    """The source with full-line comments dropped.

    A gate that exists only inside a comment is not a gate, and the comments
    above this one quote every anchor string - so a check reading the raw text
    would pass against a file whose code had been deleted entirely.  Line
    numbers are kept so the ordering checks still report something a reader can
    open.
    """
    out = []
    for i, line in enumerate(src.splitlines(), 1):
        if line.lstrip().startswith("*"):
            continue
        out.append((i, line))
    return out


def find(lines, needle):
    """Line number of the first code line containing needle, or None."""
    for n, line in lines:
        if needle in line:
            return n
    return None


def checks(src, messages=MESSAGES):
    """[(name, ok, detail)] - every invariant S.29 part 3 rests on."""
    lines = code_lines(src)
    out = []

    def ck(name, ok, detail):
        out.append((name, bool(ok), detail))

    gate = find(lines, GATE)
    sdusers = find(lines, SDUSERS)
    refusal = find(lines, REFUSAL)
    exempt = find(lines, EXEMPT)
    identity = find(lines, IDENTITY)

    ck("A1 the sdapi membership test is in the code", gate is not None,
       f"{GATE} at line {gate}")
    ck("A2 it refuses with 10073, the port's number", refusal is not None,
       f"{REFUSAL} at line {refusal}")

    # status() has to be read straight after the lookup, or "could not tell"
    # arrives as "not a member" and the audit trail says the wrong thing.
    near = None
    if gate is not None:
        near = any("status()" in line for n, line in lines
                   if gate < n <= gate + 3)
    ck("A3 status() is read within 3 lines of the lookup", near,
       "so a register that cannot be read is not reported as 'not a member'")

    ck("A4 sdsys is exempt by name", exempt is not None,
       f"{EXEMPT} at line {exempt}")

    ck("A5 the gate comes AFTER the sdusers test (5009 keeps first word)",
       gate is not None and sdusers is not None and sdusers < gate,
       f"sdusers {sdusers}, sdapi {gate}")
    ck("A6 the gate comes BEFORE the identity is taken",
       gate is not None and identity is not None and gate < identity,
       f"sdapi {gate}, K$SET.USERNAME {identity}")
    ck("A7 the refusal comes BEFORE the identity is taken",
       refusal is not None and identity is not None and refusal < identity,
       f"10073 {refusal}, K$SET.USERNAME {identity}")

    # The messages the two enforcement points call.  A call to a missing
    # message errors at run time; both numbers are the pair S.29 restored.
    for num, what in (("10073", "the API refusal"), ("10074", "the ssh refusal")):
        path = os.path.join(messages, num)
        try:
            with open(path) as f:
                body = f.read().strip()
        except OSError as exc:
            ck(f"A8 message {num} exists ({what})", False, str(exc))
            continue
        ck(f"A8 message {num} exists and is not empty ({what})", body != "",
           repr(body[:60]))
        ck(f"A9 message {num} carries the %1 the caller substitutes", "%1" in body,
           repr(body[:60]))

    account_entry_checks(lines, ck)
    empty_group_checks(lines, ck)
    return out


# ------------------------------------------- account.entry.check: no group
#
# 17 Nov 26 dm - S.62 (P-4638, P-4639): an account whose register record has
# an EMPTY group is refused by its own test, audited branch=3
# no.group.in.register (the Windows port's words), after the suspended test and
# before the membership test, and never for SDSYS entering its own account.
EG_OWN = "ent.sdsys.own = (downcase(@logname) = 'sdsys' and ent.name = 'sdsys')"
EG_TEST = "if not(ent.sdsys.own) and ent.rec<ACC$GROUP> = '' then"
EG_AUDIT = "'account refused branch=3 no.group.in.register account=' : ent.name"
EG_SUSP = "'account refused branch=2 suspended account=' : ent.name"
EG_MEMBER = "if not(is_grp_member(@logname, ent.rec<ACC$GROUP>)) then"


def empty_group_checks(lines, ck):
    """E0-E3: the empty-group refusal in account.entry.check (its label to the next label)."""
    start = find(lines, "account.entry.check:")
    stop = None
    if start is not None:
        stop = next((n for n, ln in lines if n > start and re.match(r"^[a-z][a-z0-9.]*:\s*$", ln)), None)
    block = [(n, ln) for n, ln in lines if start is not None and start < n and (stop is None or n < stop)]
    ck("E0 the account.entry.check block is found", start is not None and bool(block),
       f"account.entry.check {start}, next label {stop}, {len(block)} code lines")
    if not block:
        return

    def at(needle):
        return next((n for n, ln in block if needle in ln), None)

    own, test, susp, member = at(EG_OWN), at(EG_TEST), at(EG_SUSP), at(EG_MEMBER)
    ck("E1 the empty-group test is written, guarded by the SDSYS-own-account exemption",
       own is not None and test is not None and own < test,
       f"exemption {own}, test {test}")
    ck("E2 it comes AFTER the suspended refusal and BEFORE the membership test",
       None not in (test, susp, member) and susp < test < member,
       f"suspended {susp}, empty group {test}, is_grp_member {member}")
    body = []
    if test is not None:
        for n, ln in block:
            if n <= test:
                continue
            if ln.strip() == "end":
                break
            body.append(ln.strip())
    text = "\n".join(body)
    ck("E3 it audits 'branch=3 no.group.in.register', answers 10003, refuses and returns",
       ("void kernel(K$AUDIT, " + EG_AUDIT + ")") in text and "sysmsg(10003)" in text
       and "ent.refused = @true" in text and "return" in body,
       repr(text[:160]))


# --------------------------------------------------- request 3: by name only
#
# 17 Nov 26 dm - S.62 (P-1277, P-1278, P-1275, P-1276): request 3 (vb.account)
# enters an account by its REGISTERED NAME only.  A name holding a '/' used to
# be taken as a path: account.path was set to it before the register was read,
# and the entry test then judged an acc.rec an earlier call had left.  The
# rows below hold the new order as text; whether a path is refused is
# netfake.py's model and a real `sd -Q` (sandbox-req29.py's login()).
RQ3_FOLD = "new.account = downcase(cmnd)"
RQ3_READ = "read acc.rec from acc.f, downcase(new.account)"
RQ3_REFUSE = "if account.path = '' then"
RQ3_AUDIT = "'account refused branch=1 no.path.in.register account=' : new.account"
RQ3_ENTRY = "gosub account.entry.check"
RQ3_CD = "ospath(account.path, OS$CD)"


def account_entry_checks(lines, ck):
    """R1-R5: request 3's order, read from the vb.account block (its label to the private catalogue)."""
    start = find(lines, "vb.account:")
    stop = None
    if start is not None:
        stop = next((n for n, ln in lines if n > start and "K$PRIVATE.CATALOGUE" in ln), None)
    block = [(n, ln) for n, ln in lines if start is not None and stop is not None and start < n < stop]
    ck("R0 the vb.account block is found (its label, and the private catalogue after it)", bool(block),
       f"vb.account {start}, K$PRIVATE.CATALOGUE {stop}, {len(block)} code lines")
    if not block:
        return

    def at(needle, cond=lambda ln: True):
        return next((n for n, ln in block if needle in ln and cond(ln)), None)

    fold = at(RQ3_FOLD)
    old_fold = [n for n, ln in block if re.search(r"index\(new\.account,\s*@ds,\s*1\)\s*=\s*0\s+then\s+new\.account\s*=", ln)]
    ck("R1 every name is folded: new.account = downcase(cmnd), and no 'unless it is a path' fold",
       fold is not None and not old_fold, f"fold at {fold}, path-exempt fold at {old_fold}")

    read = at(RQ3_READ)
    clr_path = at("account.path = ''", lambda ln: re.match(r"^\s*account\.path\s*=\s*''", ln) is not None)
    clr_rec = at("acc.rec = ''", lambda ln: re.match(r"^\s*acc\.rec\s*=\s*''", ln) is not None)
    ck("R2 account.path = '' and acc.rec = '' are set BEFORE the register is read",
       None not in (read, clr_path, clr_rec) and clr_path < read and clr_rec < read,
       f"account.path '' {clr_path}, acc.rec '' {clr_rec}, read {read}")

    refuse = at(RQ3_REFUSE)
    entry = at(RQ3_ENTRY)
    cd = at(RQ3_CD)
    body = []
    if refuse is not None:
        for n, ln in block:
            if n <= refuse:
                continue
            if ln.strip() == "end":
                break
            body.append(ln)
    text = "\n".join(body)
    ck("R3 a name with no register record is refused AFTER the read and BEFORE account.entry.check and OS$CD",
       None not in (refuse, read, entry, cd) and read < refuse < entry and refuse < cd,
       f"read {read}, refusal {refuse}, entry check {entry}, OS$CD {cd}")
    ck("R4 the refusal audits 'account refused branch=1 no.path.in.register', answers 10003 and goes back",
       RQ3_AUDIT in text and "kernel(K$AUDIT" in text and "sysmsg(10003)" in text and "goto revert.to.old.account" in text,
       repr(text[:160]))
    typed = [n for n, ln in block if re.match(r"^\s*account\.path\s*=\s*(new\.account|cmnd)\b", ln)]
    ck("R5 no line gives account.path the typed name (it is set only from a register record)", not typed,
       f"assignments at {typed}")


# --------------------------------------------------------------- self-test
#
# Each mutant is (name, transform).  A mutant that no check catches is a hole
# in this file, reported as a FAILURE of the self-test - the point is not that
# the mutants are broken, it is that the checks notice.
MUTANTS = [
    ("the gate is deleted outright",
     lambda s: s.replace("                  api.in.sdapi = " + GATE,
                         "                  api.in.sdapi = @true")),
    ("status() is no longer read",
     lambda s: s.replace("                  api.route.stat = status()",
                         "                  api.route.stat = 0")),
    ("the refusal is renumbered",
     lambda s: s.replace(REFUSAL, "sysmsg(10003, scram.user)")),
    ("the sdsys exemption is dropped",
     lambda s: s.replace("if " + EXEMPT + " then", "if @true then")),
    ("the gate moves below K$SET.USERNAME",
     lambda s: _move_gate_after_identity(s)),
]

# 17 Nov 26 dm - S.62: request 3 by name only.  --selftest --from=5 runs these alone.
M_S62 = len(MUTANTS)
MUTANTS += [
    ("S.62: a path is not folded again",
     lambda s: s.replace("new.account = downcase(cmnd)\n",
                         "new.account = cmnd\nif index(new.account, @ds, 1) = 0 then new.account = downcase(new.account)\n")),
    ("S.62: acc.rec is not cleared before the read",
     lambda s: s.replace("\nacc.rec = ''            ;*", "\n* acc.rec = ''          ;*")),
    ("S.62: the typed name goes back into account.path",
     lambda s: s.replace("\naccount.path = ''       ;*", "\naccount.path = new.account       ;*")),
    ("S.62: the refusal moves below account.entry.check",
     lambda s: _move_refusal_after_entry(s)),
    ("S.62: the refusal writes no audit line",
     lambda s: s.replace("   void kernel(K$AUDIT, " + RQ3_AUDIT + ")", "*  no audit")),
    ("S.62: the refusal answers another message",
     lambda s: s.replace("   error.msg = sysmsg(10003) ;* User not allowed in requested account\n   abort.message = error.msg",
                         "   error.msg = sysmsg(5037) ;* Invalid account name\n   abort.message = error.msg")),
]

# 17 Nov 26 dm - S.62 (P-4638, P-4639): the empty-group refusal.  --selftest --from=11 runs these alone.
M_S62B = len(MUTANTS)
MUTANTS += [
    ("S.62b: the empty-group test is gone",
     lambda s: s.replace(EG_TEST, "if @false then")),
    ("S.62b: SDSYS's own entry is no longer exempt from it",
     lambda s: s.replace(EG_TEST, "if ent.rec<ACC$GROUP> = '' then")),
    ("S.62b: it audits as branch=4",
     lambda s: s.replace(EG_AUDIT, "'account refused branch=4 not.in.group group= account=' : ent.name")),
    ("S.62b: it does not return",
     lambda s: s.replace("   ent.refused = @true\n   return\nend\n\n* rev 0.9.0",
                         "   ent.refused = @true\nend\n\n* rev 0.9.0")),
    ("S.62b: it moves below the membership test",
     lambda s: _move_empty_group_after_member(s)),
]


def _move_empty_group_after_member(src):
    """Move the empty-group test (its if to its end) to just before the membership test's closing return."""
    lines = src.splitlines(keepends=True)
    start = next((i for i, ln in enumerate(lines) if ln.strip() == EG_TEST), None)
    if start is None:
        return src
    end = next((i for i in range(start + 1, len(lines)) if lines[i].strip() == "end"), None)
    if end is None:
        return src
    block = lines[start:end + 1]
    rest = lines[:start] + lines[end + 1:]
    at = next((i for i, ln in enumerate(rest) if EG_MEMBER in ln.strip() and i >= start), None)
    if at is None:
        return src
    return "".join(rest[:at + 1] + block + rest[at + 1:])


def _move_refusal_after_entry(src):
    """Move the 'no register record' refusal (its if to its end) to just after the account.entry.check line."""
    lines = src.splitlines(keepends=True)
    start = next((i for i, ln in enumerate(lines) if ln.strip() == RQ3_REFUSE), None)
    if start is None:
        return src
    end = next((i for i in range(start + 1, len(lines)) if lines[i].strip() == "end"), None)
    if end is None:
        return src
    block = lines[start:end + 1]
    rest = lines[:start] + lines[end + 1:]
    at = next((i for i, ln in enumerate(rest) if RQ3_ENTRY in ln and i > start), None)
    if at is None:
        return src
    return "".join(rest[:at + 1] + block + rest[at + 1:])


def _move_gate_after_identity(src):
    """Move the whole gate block to just after the identity is taken.

    Textual and crude on purpose: it only has to produce a file in which the
    gate is present, compiles to the eye, and sits in the wrong place.
    """
    lines = src.splitlines(keepends=True)
    start = end = ident = None
    for i, line in enumerate(lines):
        if EXEMPT in line and line.lstrip().startswith("if "):
            start = i
        if start is not None and end is None and line.rstrip() == " " * 15 + "end":
            end = i
        if IDENTITY in line:
            ident = i
    if start is None or end is None or ident is None or ident <= end:
        return src
    block = lines[start:end + 1]
    rest = lines[:start] + lines[end + 1:]
    at = next(i for i, line in enumerate(rest) if IDENTITY in line)
    return "".join(rest[:at + 1] + block + rest[at + 1:])


def selftest(src, first=0):
    print("--- self-test: each mutation must be CAUGHT by at least one check ---")
    if first:
        print(f"    (--from={first}: mutants {first} to {len(MUTANTS) - 1} only)")
    base = checks(src)
    base_bad = [n for n, ok, _ in base if not ok]
    if base_bad:
        print("REFUSING - the unmutated source already fails: %s" % ", ".join(base_bad),
              file=sys.stderr)
        return 2
    holes = 0
    chosen = MUTANTS[first:]
    if not chosen:
        print(f"REFUSING - --from={first} selects no mutant (there are {len(MUTANTS)})", file=sys.stderr)
        return 2
    for name, fn in chosen:
        mutated = fn(src)
        if mutated == src:
            print(f"  [FAIL] {name}: the mutation did not change the file "
                  f"(this test no longer understands the source)")
            holes += 1
            continue
        caught = [n for n, ok, _ in checks(mutated) if not ok]
        if caught:
            print(f"  [pass] {name}: caught by {', '.join(caught)}")
        else:
            print(f"  [FAIL] {name}: NOT CAUGHT by any check")
            holes += 1
    print(f"\n{len(chosen) - holes} of {len(chosen)} mutants caught")
    return 1 if holes else 0


def main(argv):
    if not os.path.isfile(APISRVR):
        print(f"CANNOT RUN - no {APISRVR}", file=sys.stderr)
        return 2
    with open(APISRVR) as f:
        src = f.read()

    print(f"reading  {APISRVR} ({len(src.splitlines())} lines)")
    print(f"messages {MESSAGES}\n")

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
    failed = 0
    for name, ok, detail in rows:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")
        if not ok:
            failed += 1
    if not rows:
        print("REFUSING - no checks ran", file=sys.stderr)
        return 2
    print(f"\n{len(rows) - failed} passed, {failed} failed")
    print("NOT MEASURED HERE: whether the gate refuses anybody.  That is "
          "witness-release-run.sh section 13f, on an install.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
