#!/usr/bin/env python3
"""Unit test for SD's password rule, SD Core for Linux.  Free - no install,
no sudo, no sd.

Written 19 Sep 2026, on the SD Core for Windows agent's mail of 14:30 the same
day.  It took this tree's `pw_complex` case block verbatim and asked for two
rows back: one proving an arm-order mutation is not vacuous, and one showing
the OLD shape accepting the TAB row the new one refuses.  Both are here (B2,
B3, S2, S3), and the port has the equivalent as `test-pwcomplex-units`.

WHAT IT IS FOR.  The owner's ruling of 19 Sep 2026 is that SD requires a
complex password whatever the operating system allows: 8+ characters with a
lower-case letter, an upper-case letter, a digit and a symbol (any other
printable ASCII, space included); a byte outside 32-126 fails outright.  ONE
RULE, WRITTEN TWICE IN THIS TREE, and they cannot be merged: `gpl.bp/pw_complex`
serves everything inside SD, and `gplbld/sd-elevate`'s `pw_complex` serves the
installer's sdsys prompt, which runs before SD can be reached at all.  A third
copy is the Windows port's.  So the table below is the rule's SPEC and both
implementations are driven through it.

THE BASIC IS CHECKED WITHOUT BEING RUN, AND THE LIMIT IS STATED RATHER THAN
GLOSSED.  Nothing in a session can execute SD BASIC - a GPL.BP change is proven
by commit, push and reinstall.  So this reads the RANGES and the ARM ORDER out
of `gpl.bp/pw_complex` and drives the table through what the file says.  That
is weaker than running it: it proves the rule the file states, not the rule the
compiler emits.  The compiled behaviour is witnessed on an install
(`witness-absence.sh` M2e/f, M11a-d).

WHY THE ARM ORDER IS WORTH A TEST AT ALL.  The port's first shape tested
out-of-range in the FIRST arm and let the catch-all mean "symbol".  That is
correct only while nobody reorders the arms: move it and a byte outside 32-126
falls through to the catch-all and SATISFIES the symbol requirement it exists
to fail - it fails OPEN.  This tree's shape names 32-126 in the symbol arm and
returns false from the catch-all, so an unmatched byte is refused whatever the
order.  B2 drives EVERY permutation of the arms and requires the non-printable
rows to be refused by all of them; B3 shows the old shape accepting the tab row
once its guard arm is no longer first.  Mutants run on text.  THE LIVE FILES
ARE ASSERTED BYTE-IDENTICAL AFTERWARDS.

Null case refused out loud: a run with no ALLOW rows, no REFUSE rows, no
permutations, or a mutant that stayed green, exits 2 rather than reporting
success.

  python3 /home/don/Projects/SDCoreLinuxProject/sdcore4linux/sdb_ai/sd64/gplbld/test-pwcomplex-units.py

No sudo.  Exit 0 all rows passed, 1 a row failed, 2 a premise was not found in
the source or the run established nothing.
"""

import itertools
import os
import re
import subprocess
import sys

ALLOW, REFUSE = "ALLOW", "REFUSE"

HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.dirname(HERE)
BASIC = os.path.join(SD64, "sdsys", "gpl.bp", "pw_complex")
HELPER = os.path.join(HERE, "sd-elevate")


# ---------------------------------------------------------------------------
# THE SPEC.  The owner's rule of 19 Sep 2026, as one table.  Every REFUSE row
# lacks exactly ONE thing, so an implementation that stopped checking any one
# class fails here; the ALLOW rows are the control - a rule that refused
# everything would pass every REFUSE row and be useless.
#
# Rows 5 and 6 are the SD Core for Windows agent's additions of 19 Sep 2026:
# the two ends of the symbol range, which no other row pins.
# `test-sd-elevate.py` imports this table rather than keeping its own copy.
SPEC = [
    (ALLOW,  "Abcdef1!",       "exactly 8, all four kinds"),
    (ALLOW,  "zZ9 zzzz",       "a space is a symbol"),
    (ALLOW,  "Pass:word1",     "a colon (chpasswd's separator) is only a symbol"),
    (ALLOW,  "Aa1~" * 30,      "long is fine - no maximum"),
    (ALLOW,  "Abcdef1 ",       "a trailing SPACE, chr 32 - the symbol range's low end"),
    (ALLOW,  "Abcdef1~",       "a trailing TILDE, chr 126 - its high end"),
    (REFUSE, "Abcde1!",        "7 characters - one short"),
    (REFUSE, "abcdef1!",       "no upper-case letter"),
    (REFUSE, "ABCDEF1!",       "no lower-case letter"),
    (REFUSE, "Abcdefg!",       "no digit"),
    (REFUSE, "Abcdefg1",       "no symbol"),
    (REFUSE, "Abcdef1\t",      "a tab is not printable ASCII"),
    (REFUSE, "Abcdef\x7f1!",   "chr 127 (DEL) is one past the range"),
    (REFUSE, "Abcdéf1!",  "a non-ASCII letter"),
    (REFUSE, "",               "empty"),
]

# The two rows the mutants turn on, looked up by note rather than by index so
# a reordering of SPEC cannot silently point them at something else.
TAB_ROW = "Abcdef1\t"
GOOD_ROW = "Abcdef1!"


def refuse(why):
    print("REFUSED: %s" % why, file=sys.stderr)
    sys.exit(2)


# ---------------------------------------------------------------------------
# The BASIC, read rather than run.

ALWAYS, RANGE, OUTSIDE = "always", "range", "outside"
SET, REJECT = "set", "reject"

ARM_RE = re.compile(r"^\s*case\s+(?P<cond>.+?)\s*;\s*(?P<act>[^;]+?)\s*(?:;\*.*)?$")
COND_RANGE = re.compile(r"^c\s*>=\s*(\d+)\s+and\s+c\s*<=\s*(\d+)$")
COND_OUTSIDE = re.compile(r"^c\s*<\s*(\d+)\s+or\s+c\s*>\s*(\d+)$")
ACT_SET = re.compile(r"^has\.(lower|upper|digit|symbol)\s*=\s*@true$")
ACT_REJECT = re.compile(r"^return\s+@false$")


def parse_cond(text, where):
    if text == "1":
        return (ALWAYS, None, None)
    m = COND_RANGE.match(text)
    if m:
        return (RANGE, int(m.group(1)), int(m.group(2)))
    m = COND_OUTSIDE.match(text)
    if m:
        return (OUTSIDE, int(m.group(1)), int(m.group(2)))
    refuse("%s: a case condition this test cannot read: %r" % (where, text))


def parse_act(text, where):
    m = ACT_SET.match(text)
    if m:
        return (SET, m.group(1))
    if ACT_REJECT.match(text):
        return (REJECT, None)
    refuse("%s: a case action this test cannot read: %r" % (where, text))


def parse_basic(text, where):
    """Lift (minlen, arms, required) out of the BASIC source.

    ANY PREMISE NOT FOUND IS A REFUSAL, not a guess - the whole point is that
    the model is the file's, not this test's.
    """
    m = re.search(r"if\s+len\(pw\)\s*<\s*(\d+)\s+then\s+return\s+@false", text)
    if not m:
        refuse("%s: no minimum-length guard 'if len(pw) < N then return @false'" % where)
    minlen = int(m.group(1))

    # The rule must look at EVERY byte, or a table row could pass for the
    # wrong reason.  Both premises are read, neither assumed.
    if not re.search(r"for\s+i\s*=\s*1\s+to\s+n", text):
        refuse("%s: no 'for i = 1 to n' - nothing proves every character is examined" % where)
    if not re.search(r"c\s*=\s*seq\(pw\[i,1\]\)", text):
        refuse("%s: no 'c = seq(pw[i,1])' - nothing proves c is the character's code" % where)

    block = re.search(r"^\s*begin case\s*$(.*?)^\s*end case\s*$", text, re.S | re.M)
    if not block:
        refuse("%s: no 'begin case' ... 'end case' block" % where)
    arms = []
    for line in block.group(1).split("\n"):
        if not line.strip():
            continue
        m = ARM_RE.match(line)
        if not m:
            refuse("%s: a line inside the case block this test cannot read: %r" % (where, line))
        arms.append((parse_cond(m.group("cond"), where),
                     parse_act(m.group("act"), where),
                     line.strip()))
    if not arms:
        refuse("%s: the case block is empty" % where)

    m = re.search(r"return\s*\(\s*(has\.[a-z.\s]+?)\s*\)", text)
    if not m:
        refuse("%s: no final 'return (has.… and has.…)' conjunction" % where)
    required = [p.strip() for p in m.group(1).split(" and ")]
    for r in required:
        if not re.match(r"^has\.(lower|upper|digit|symbol)$", r):
            refuse("%s: an unreadable term in the final conjunction: %r" % (where, r))
    return minlen, arms, [r.split(".")[1] for r in required]


def basic_verdict(model, pw):
    """Evaluate the parsed BASIC against one password.  Bytes, as seq() sees."""
    minlen, arms, required = model
    raw = pw.encode("utf-8")
    if len(raw) < minlen:
        return REFUSE
    flags = set()
    for c in raw:
        for cond, act, _ in arms:
            kind, lo, hi = cond
            hit = (kind == ALWAYS
                   or (kind == RANGE and lo <= c <= hi)
                   or (kind == OUTSIDE and (c < lo or c > hi)))
            if not hit:
                continue
            if act[0] == REJECT:
                return REFUSE
            flags.add(act[1])
            break
        # No arm matched: SD BASIC's begin case simply falls through, so the
        # character is silently ignored.  That is the fail-open shape, modelled
        # faithfully rather than defended against here.
    return ALLOW if all(f in flags for f in required) else REFUSE


# The port's ORIGINAL shape, quoted from its mail of 19 Sep 2026 13:40: the
# out-of-range test in the FIRST arm, the catch-all meaning "symbol".  Correct
# as written; the mutant is what happens when it is reordered.
OLD_SHAPE = """      begin case
         case c < 32 or c > 126 ; return @false
         case c >= 97 and c <= 122 ; has.lower = @true
         case c >= 65 and c <= 90  ; has.upper = @true
         case c >= 48 and c <= 57  ; has.digit = @true
         case 1 ; has.symbol = @true
      end case
"""


def with_block(text, block):
    """Return text with its begin case ... end case replaced by block."""
    return re.sub(r"^\s*begin case\s*$.*?^\s*end case\s*$\n",
                  block, text, count=1, flags=re.S | re.M)


# ---------------------------------------------------------------------------
# The bash, run for real.

def helper_verdict(pw):
    """The LIVE helper's own answer, through its documented door."""
    p = subprocess.run(["bash", HELPER, "--dry-run", "pw-check"],
                       input=pw + "\n", capture_output=True, text=True)
    out = (p.stdout or "") + (p.stderr or "")
    # Anchor on the wording the tool prints on the POSITIVE path, and refuse if
    # the failure wording appears - not on the exit code alone.
    if p.returncode == 0 and "meets the rule" in out:
        return ALLOW
    if p.returncode != 0 and "does not meet the rule" in out:
        return REFUSE
    refuse("sd-elevate --dry-run pw-check said neither thing (exit %d): %r"
           % (p.returncode, out.strip()[:200]))


BASH_FN = re.compile(r"^pw_complex\(\)\s*\{\n(?P<body>.*?)^\}\s*$", re.S | re.M)
BASH_BRANCHES = re.compile(
    r"^\s*(?:if|elif)\s+\(\(\s*(?P<cond>[^)]*?)\s*\)\);\s*then\s+(?P<act>\S+)\s*$", re.M)


def bash_parts(text):
    """Lift the branch list out of sd-elevate's pw_complex, or refuse."""
    m = BASH_FN.search(text)
    if not m:
        refuse("sd-elevate: no 'pw_complex() { ... }' function")
    body = m.group("body")
    branches = [(b.group("cond"), b.group("act")) for b in BASH_BRANCHES.finditer(body)]
    if len(branches) < 4:
        refuse("sd-elevate: expected four class branches in pw_complex, found %d"
               % len(branches))
    if not re.search(r"^\s*else\s+return 1\s*$", body, re.M):
        refuse("sd-elevate: pw_complex has no 'else return 1' catch-all")
    return branches


def bash_harness(branches, catch_all):
    """A standalone script defining a pw_complex of the given branch order."""
    lines = ["pw_complex() {",
             "  local p=$1 i c lo=0 up=0 di=0 sy=0",
             "  local LC_ALL=C",
             "  (( ${#p} >= 8 )) || return 1",
             "  for (( i = 0; i < ${#p}; i++ )); do",
             "    printf -v c '%d' \"'${p:i:1}\""]
    for n, (cond, act) in enumerate(branches):
        kw = "if  " if n == 0 else "elif"
        lines.append("    %s (( %s )); then %s" % (kw, cond, act))
    lines.append("    else %s" % catch_all)
    lines.append("    fi")
    lines.append("  done")
    lines.append("  (( lo && up && di && sy ))")
    lines.append("}")
    lines.append('pw_complex "$1" && { echo "meets the rule"; exit 0; }')
    lines.append('echo "does not meet the rule"; exit 1')
    return "\n".join(lines) + "\n"


def run_harness(script, pw):
    p = subprocess.run(["bash", "-c", script, "bash", pw],
                       capture_output=True, text=True)
    out = (p.stdout or "") + (p.stderr or "")
    if "meets the rule" in out and "does not" not in out:
        return ALLOW
    if "does not meet the rule" in out:
        return REFUSE
    refuse("a bash mutant harness said neither thing: %r" % out.strip()[:200])


# ---------------------------------------------------------------------------

def main():
    passed = failed = 0
    n_allow = n_refuse = n_mutant = 0
    failures = []

    def row(tag, ok, said):
        nonlocal passed, failed
        passed += ok
        failed += not ok
        print("  [%s] %s | %s" % ("PASS" if ok else "FAIL", tag, said))
        if not ok:
            failures.append((tag, said))

    for path in (BASIC, HELPER):
        if not os.path.exists(path):
            refuse("%s is missing - there is nothing to test" % path)

    basic_text = open(BASIC, "rb").read().decode("utf-8")
    helper_text = open(HELPER, "rb").read().decode("utf-8")

    print("inputs, as used this run:")
    print("  BASIC    : %s" % BASIC)
    print("  helper   : %s   (driven as: bash %s --dry-run pw-check)" % (HELPER, HELPER))
    print("  spec     : %d rows (%d ALLOW, %d REFUSE)"
          % (len(SPEC), sum(1 for r in SPEC if r[0] == ALLOW),
             sum(1 for r in SPEC if r[0] == REFUSE)))

    model = parse_basic(basic_text, "gpl.bp/pw_complex")
    minlen, arms, required = model
    print("  premises read out of gpl.bp/pw_complex:")
    print("    minimum length  : %d" % minlen)
    print("    required classes: %s" % ", ".join(required))
    for i, (_, _, src) in enumerate(arms, 1):
        print("    arm %d           : %s" % (i, src))
    branches = bash_parts(helper_text)
    print("  branches read out of sd-elevate's pw_complex:")
    for i, (cond, act) in enumerate(branches, 1):
        print("    branch %d        : (( %s )) -> %s" % (i, cond, act))
    print()

    # ---- A: the live BASIC, as the file states it.
    print("A - gpl.bp/pw_complex, read out of the file:")
    for expect, pw, note in SPEC:
        got = basic_verdict(model, pw)
        n_allow += expect == ALLOW
        n_refuse += expect == REFUSE
        row("A %-6s basic " % expect, got == expect,
            "%-14s %s (said %s)" % (repr(pw)[:14], note, got))

    # ---- S: the live helper, run for real.
    print("S - sd-elevate pw_complex, run through --dry-run pw-check:")
    for expect, pw, note in SPEC:
        got = helper_verdict(pw)
        n_allow += expect == ALLOW
        n_refuse += expect == REFUSE
        row("S %-6s bash  " % expect, got == expect,
            "%-14s %s (said %s)" % (repr(pw)[:14], note, got))

    # ---- S1: the extraction control.  Everything below drives a REBUILT
    # ---- function rather than the helper itself, so the rebuild must first
    # ---- agree with the helper on every row, or the mutants prove nothing
    # ---- about the shipped code.
    print("S1 - the extracted function, unmutated, must agree with the helper:")
    live_script = bash_harness(branches, "return 1")
    disagree = [pw for _, pw, _ in SPEC
                if run_harness(live_script, pw) != helper_verdict(pw)]
    row("S1 control    ", not disagree,
        "rebuilt from the file's own branches; disagreements: %s"
        % (", ".join(repr(d) for d in disagree) if disagree else "none"))

    # ---- B2 / S2: THE ARM ORDER CANNOT LET A NON-PRINTABLE BYTE THROUGH.
    # ---- Every permutation of the arms, not one chosen reordering.
    print("B2 - every permutation of the BASIC arms still refuses a non-printable byte:")
    nonprintable = [pw for expect, pw, note in SPEC
                    if expect == REFUSE and any(c < 32 or c > 126 for c in pw.encode("utf-8"))]
    if not nonprintable:
        refuse("no SPEC row carries a byte outside 32-126, so B2 would measure nothing")
    perms = list(itertools.permutations(range(len(arms))))
    leaked = []
    live_refused_good = 0
    for p in perms:
        m2 = (minlen, [arms[i] for i in p], required)
        for pw in nonprintable:
            if basic_verdict(m2, pw) != REFUSE:
                leaked.append((p, pw))
        if basic_verdict(m2, GOOD_ROW) == REFUSE:
            live_refused_good += 1
    n_mutant += len(perms)
    row("B2 order      ", not leaked,
        "%d permutations x %d non-printable rows, all refused; leaks: %s"
        % (len(perms), len(nonprintable),
           "none" if not leaked else repr(leaked[:3])))

    # ---- B2b: AND THE PERMUTATION DRIVER IS NOT VACUOUS.  If reordering the
    # ---- arms changed nothing at all, B2 would pass on a driver that does
    # ---- nothing.  The Windows agent's row: a scrambled order must still
    # ---- REFUSE A GOOD PASSWORD, or the order row proves nothing.
    print("B2b - the permutation driver is live (some order refuses a GOOD password):")
    row("B2b liveness  ", live_refused_good > 0,
        "%d of %d permutations refuse %r; the shipped order accepts it (%s)"
        % (live_refused_good, len(perms), GOOD_ROW, basic_verdict(model, GOOD_ROW)))

    # ---- B3: THE OLD SHAPE, AND WHAT REORDERING DOES TO IT.  Control first:
    # ---- as the port wrote it, it must agree with ours on every row - so the
    # ---- mutant below is the ORDER, not a shape this test broke.
    print("B3 - the port's original shape: identical as written, fails OPEN when reordered:")
    old_model = parse_basic(with_block(basic_text, OLD_SHAPE), "the old shape")
    old_disagree = [pw for _, pw, _ in SPEC
                    if basic_verdict(old_model, pw) != basic_verdict(model, pw)]
    n_mutant += 1
    row("B3 control    ", not old_disagree,
        "as written it agrees with ours on all %d rows; disagreements: %s"
        % (len(SPEC), ", ".join(repr(d) for d in old_disagree) if old_disagree else "none"))

    # Its guard arm demoted past the catch-all - the reordering it cannot
    # survive.  A tab now reaches `case 1` and is counted as a SYMBOL.
    old_arms = old_model[1]
    guard = [a for a in old_arms if a[0][0] == OUTSIDE]
    if len(guard) != 1:
        refuse("the old shape did not parse with exactly one out-of-range arm")
    demoted = (old_model[0], [a for a in old_arms if a[0][0] != OUTSIDE] + guard, old_model[2])
    n_mutant += 1
    got = basic_verdict(demoted, TAB_ROW)
    row("B3 mutant     ", got == ALLOW,
        "guard arm demoted past the catch-all: %r -> %s (ours: %s)"
        % (TAB_ROW, got, basic_verdict(model, TAB_ROW)))

    # ---- S2 / S3: the same two, in bash, EXECUTED.
    print("S2 - the helper's symbol branch moved to the front (executed):")
    order = [i for i, (cond, _) in enumerate(branches) if "32" in cond and "126" in cond]
    if len(order) != 1:
        refuse("sd-elevate: could not identify exactly one 32..126 branch")
    sy = order[0]
    scrambled = [branches[sy]] + [b for i, b in enumerate(branches) if i != sy]
    s2 = bash_harness(scrambled, "return 1")
    n_mutant += 1
    got_tab, got_good = run_harness(s2, TAB_ROW), run_harness(s2, GOOD_ROW)
    row("S2 fails-closed", got_tab == REFUSE,
        "%r still refused with the symbol branch first (said %s)" % (TAB_ROW, got_tab))
    row("S2 liveness   ", got_good == REFUSE,
        "%r now refused too, so the reordering really ran (said %s)" % (GOOD_ROW, got_good))

    print("S3 - the old bash shape with its guard no longer first (executed):")
    old_branches = [b for i, b in enumerate(branches) if i != sy]
    s3 = bash_harness(old_branches, "sy=1")
    n_mutant += 1
    got = run_harness(s3, TAB_ROW)
    row("S3 mutant     ", got == ALLOW,
        "catch-all means symbol, guard not first: %r -> %s (ours: %s)"
        % (TAB_ROW, got, helper_verdict(TAB_ROW)))

    # ---- P: THE PARTITION.  Every prompt that sets a password runs the rule.
    # ---- This is the regression no row about the rule itself can see: the
    # ---- rule can be perfect and simply not reached.
    print("P - every password prompt in the tree applies the rule:")
    gplbp = os.path.join(SD64, "sdsys", "gpl.bp")
    prompts = []
    for name in sorted(os.listdir(gplbp)):
        path = os.path.join(gplbp, name)
        if not os.path.isfile(path):
            continue
        body = open(path, "rb").read().decode("latin-1")
        if re.search(r"^\s*input\s+\S+\s+HIDDEN\s*$", body, re.M | re.I):
            prompts.append(("sdsys/gpl.bp/" + name, body, r"pw_complex\("))
    installer = os.path.join(os.path.dirname(SD64), "..", "installsdai.sh")
    installer = os.path.normpath(installer)
    inst_body = open(installer, "rb").read().decode("latin-1")
    if re.search(r"read\s+-r\s+-s", inst_body):
        prompts.append(("installsdai.sh", inst_body, r"pw-check"))
    if not prompts:
        refuse("no password prompt was found anywhere - the partition check measured nothing")
    for where, body, needle in prompts:
        row("P  partition  ", re.search(needle, body) is not None,
            "%-28s prompts for a password and calls %s" % (where, needle.replace("\\", "")))

    # ---- THE LIVE FILES ARE UNCHANGED.  Mutants ran on text; if any of this
    # ---- reached the tree, every verdict above is void.
    print("Z - the live files are byte-identical after the mutants:")
    row("Z  untouched  ",
        open(BASIC, "rb").read().decode("utf-8") == basic_text
        and open(HELPER, "rb").read().decode("utf-8") == helper_text,
        "gpl.bp/pw_complex and gplbld/sd-elevate unchanged on disk")

    print()

    # ---- refuse the null case, out loud.
    if n_allow == 0:
        refuse("no ALLOW rows ran; nothing proved the rule discriminates "
               "rather than refusing everything")
    if n_refuse == 0:
        refuse("no REFUSE rows ran; nothing tested the rule")
    if n_mutant == 0:
        refuse("no mutants ran; nothing proved these rows can go red")

    print("%d passed, %d failed (%d ALLOW rows, %d REFUSE rows, %d mutants)"
          % (passed, failed, n_allow, n_refuse, n_mutant))

    if failed:
        print("\nfailures:", file=sys.stderr)
        for tag, said in failures:
            print("  %s: %s" % (tag.strip(), said), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
