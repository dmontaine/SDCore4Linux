#!/usr/bin/env python3
"""Find entries whose OPENING status claim is contradicted LATER IN THE SAME ENTRY.

    python3 gplbld/check-stale-leads.py              the three tracked documents
    python3 gplbld/check-stale-leads.py FILE...      named files instead

Exit 0 nothing to read, 1 there is a worklist, 2 the question could not be
answered (a document missing, or no entries found in one - which means the
shapes below have drifted and every "clean" verdict would be worthless).

PORT_ADOPTION 21.  ***THIS IS NOT THE PORT'S SCRIPT AND COULD NOT BE.***  Its
check-stale-leads.py is keyed to the port's PROJECT_STATUS - a section 7,
"> ###" START HERE items, a check-mark task table - and PRE_RELEASE 9 records
what happened when it was copied here verbatim: it exited 2 before any phase
ran, "REFUSING - could not bound section 7", and was removed rather than
committed, because a tool that always exits 2 reads like a guard the project
has.  This is written to the shapes THIS tree actually uses.

THE FAULT IT LOOKS FOR.  A reader - human or agent - reads top-down and stops
at the first status sentence.  When a correction is APPENDED to an entry rather
than the opening being struck, the entry lies to everyone who does not read all
of it.  The entries here run to thousands of characters, so that is most
readers most of the time.

***IT FOUND ONE THE DAY IT WAS WRITTEN, AND THE SESSION THAT WROTE IT HAD MADE
IT AN HOUR EARLIER.***  PORT_ADOPTION queue 19 opened "THE SWEEP IS BUILT AND
NOT WIRED, PENDING A RULING" and, 2000 characters later in the same row, said
"RULED BY THE OWNER, 12 Sep 2026: SWEEP, full port parity".  Both sentences
were written by the same session on the same day; the second was appended when
the ruling came in and the first was left standing.

WHAT IT IS NOT.  ***This does not decide staleness; it RANKS entries for
reading.***  An entry may legitimately narrate "this was open, then it closed" -
several here do it deliberately, because CLAUDE.md asks that a resolved
objection stay in the entry.  The output is a worklist and every hit is read by
hand.  Saying so matters: a script that reported these as defects would be
committing the same overconfidence it exists to catch.

WHY ONLY ONE PHASE.  The port has three; this has the first, because the other
two need structures this tree does not have (its check-mark task table) or
judgements a word-matcher cannot make.  ***A tool that does one thing and says
so is worth more here than three phases that half-run*** - which is PRE_RELEASE
9's lesson, paid for by the copy that would not start.

THE LIMIT, WORTH KNOWING BEFORE TRUSTING ANY OF IT: this compares a document
against ITSELF.  It cannot tell that an entry agrees with itself and is wrong
about the machine.  Only a measurement does that.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, os.pardir, os.pardir, os.pardir))
DEFAULT_DOCS = ["PROJECT_STATUS.md", "PORT_ADOPTION.md", "PRE_RELEASE_FIXES.md"]

# How much of an entry counts as "the opening" - what a reader sees before
# deciding whether to read on.  Generous rather than mean: a lead buried at
# character 400 of a 4000-character row is still a lead.
OPENING = 320

# ***ONLY UPPER CASE COUNTS, AND THAT IS THE PROJECT'S OWN CONVENTION RATHER
# THAN A TRICK.***  CLAUDE.md: "ALL-CAPS and bold mean 'this was paid for'".  A
# status CLAIM here is written in the emphatic voice; the same word in ordinary
# prose is usually not a claim at all.  Queue 19's row is the worked example -
# it opens "NOT WIRED, PENDING A RULING" and then says "installed as
# /usr/local/sbin/sd-reconcile-accounts", which is where a file goes, not a
# status.  Case-insensitive matching read that "installed" as the opening's
# last status word and scored the row clean.  THE COST IS REAL AND IS ACCEPTED:
# a lower-case "unrun" is a genuine claim and is missed.  Precision is worth
# more than recall in a tool nobody will keep running if it cries wolf.
#
# ***NEGATED FORMS ARE COLLAPSED FIRST, OR EVERY "NOT WITNESSED" WOULD READ AS
# "WITNESSED".***  The other half of the trick, and the part easiest to break.
NEGATED = re.compile(
    r"\bNOT\s+(?:YET\s+)?(?:RUN|INSTALLED|WIRED|COMPILED|STARTED|WITNESSED|BUILT|RULED|DONE|CLOSED)\b"
    r"|\bUN(?:WITNESSED|RUN|RULED)\b"
    r"|\bNEVER\s+(?:RUN|INSTALLED|WIRED|WITNESSED)\b")

OPEN_WORD = re.compile(
    r"§OPEN§"
    r"|\bTO\s+BUILD\b|\bPENDING\b|\bUNRULED\b"
    r"|\bOPEN\s+FOR\s+THE\s+OWNER\b|\bWAITING\s+FOR\s+THE\s+OWNER\b"
    r"|\bSTILL\s+TO\s+DO\b")

CLOSED_WORD = re.compile(
    r"\bWITNESSED\b|\bRULED\b|\bDONE\b|\bCLOSED\b|\bCOMPLETE\b|\bFIXED\b"
    r"|\bINSTALLED\b|\bBUILT\b|\bADOPTED\b")


def collapse(text):
    """Replace negated status phrases with a token, so the closed-word scan
    cannot match the tail of a negation."""
    return NEGATED.sub("§OPEN§", text)


def classify(text):
    """(class, matched-text, position) for the LAST status word in the opening.

    ***THE LAST, NOT THE FIRST, AND THAT IS THE DIFFERENCE BETWEEN THIS
    CATCHING QUEUE 19 AND MISSING IT.***  An opening often carries several:
    queue 19's read "REPORT HALF BUILT AND WITNESSED ...; THE SWEEP IS BUILT AND
    NOT WIRED, PENDING A RULING".  Taking the first gives "BUILT" and calls the
    entry closed; what a reader actually carries away is the last one, "PENDING
    A RULING".  The first version of this file took the first and scored that
    row as a harmless refinement.
    """
    last = None
    for cls, rx in (("open", OPEN_WORD), ("closed", CLOSED_WORD)):
        for m in rx.finditer(text):
            if last is None or m.start() > last[2]:
                last = (cls, m.group(0), m.start())
    return last


def entries(path):
    """Yield (label, text) for every entry in a document.

    Two shapes, because this tree has two.  A numbered TABLE ROW is one entry
    (PORT_ADOPTION's queue, PRE_RELEASE_FIXES' table).  A TOP-LEVEL BULLET plus
    its indented continuation lines is one entry (PROJECT_STATUS's START HERE).
    Anything else is not an entry and is not guessed at.
    """
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()

    row = re.compile(r"^\|\s*~{0,2}(\d+)~{0,2}\s*\|")
    bullet = re.compile(r"^- +(\S.*)$")

    i = 0
    while i < len(lines):
        line = lines[i]
        m = row.match(line)
        if m:
            yield ("%s row %s (line %d)" % (os.path.basename(path),
                                            m.group(1), i + 1), line)
            i += 1
            continue
        m = bullet.match(line)
        if m:
            buf = [m.group(1)]
            j = i + 1
            while j < len(lines) and re.match(r"^ {2,}\S", lines[j]):
                buf.append(lines[j].strip())
                j += 1
            yield ("%s bullet (line %d)" % (os.path.basename(path), i + 1),
                   " ".join(buf))
            i = j
            continue
        i += 1


def excerpt(text, pos, width=150):
    lo = max(0, pos - 40)
    return " ".join(text[lo:lo + width].split())


def main():
    docs = sys.argv[1:]
    if not docs:
        docs = [os.path.join(REPO, d) for d in DEFAULT_DOCS]

    print("check-stale-leads.py - PORT_ADOPTION 21")
    print("repo : %s" % REPO)
    print("")

    hits = 0
    refines = 0
    scanned = 0

    for path in docs:
        if not os.path.isfile(path):
            print("CANNOT ANSWER: no such document: %s" % path)
            return 2

        found = 0
        for label, raw in entries(path):
            text = collapse(raw)
            found += 1
            scanned += 1

            head = classify(text[:OPENING])
            if head is None:
                continue

            # The rest of the entry, scanned for the OPPOSITE class.
            other = CLOSED_WORD if head[0] == "open" else OPEN_WORD
            m = other.search(text, OPENING)
            if not m:
                continue

            # ***TWO TIERS, AND ONLY ONE OF THEM DECIDES.***  Direction is what
            # separates the fault from the house style:
            #
            #   opens OPEN, later CLOSED  - a STALE LEAD.  The opening says
            #       work remains and the body says it was finished.  This is
            #       the fault the file is named for and the only one that sets
            #       a non-zero exit.
            #
            #   opens CLOSED, later OPEN  - usually deliberate, and this tree
            #       does it on purpose: "WITNESSED ... NOT WITNESSED: <exactly
            #       which part>" is how an entry is supposed to read, and
            #       CLAUDE.md asks for it.  Reported, never counted, because a
            #       tool that cried wolf over the house style would be ignored
            #       within a week - and then it would miss the real ones.
            if head[0] == "open":
                hits += 1
                tier, later = "LEAD ", "closed"
            else:
                refines += 1
                tier, later = "note ", "open"
            print("%s %s" % (tier, label))
            print("      opens %-6s : ...%s..." % (head[0], excerpt(text, head[2])))
            print("      later %-6s : ...%s..." % (later, excerpt(text, m.start())))
            print("")

        # ***THE NULL CASE, REFUSED OUT LOUD.***  A document that yielded no
        # entries means the shapes above have drifted from the documents, and
        # every "clean" verdict in this run would be worth nothing.  PRE_RELEASE
        # 9 is exactly this failure in the port's copy, and it is why the
        # refusal is louder than the finding.
        if found == 0:
            print("CANNOT ANSWER: no entries found in %s." % path)
            print("The row and bullet shapes this file matches have drifted")
            print("from the documents, so a clean result would mean nothing.")
            return 2
        print("scanned %-24s %d entries" % (os.path.basename(path), found))

    print("")
    print("%d entries scanned, %d STALE LEAD(s), %d refinement(s) noted"
          % (scanned, hits, refines))
    if hits:
        print("")
        print("A LEAD is an entry that opens saying work remains and later says")
        print("it was finished - the opening was never struck when the")
        print("correction was appended.  Read each one and strike the opening.")
        print("The 'note' rows are the opposite direction and are usually the")
        print("house style ('WITNESSED ... NOT WITNESSED: which part'); they are")
        print("listed for reading and deliberately do not affect the exit.")
        return 1
    print("No entry opens with a claim its own body contradicts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
