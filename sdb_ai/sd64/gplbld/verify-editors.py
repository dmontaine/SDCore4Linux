#!/usr/bin/env python3
#
# verify-editors.py - is the SD BASIC syntax highlighting actually PLACED where
#                     the editors will read it, is the EDIT verb wired to NANO
#                     and MICRO, and does find.editor's premise hold?
#                     PORT_ADOPTION queue 22; intent from the port's
#                     gplbld/verify-editors.ps1.
#
#   python3 /home/don/Projects/sdcore4linux/sdb_ai/sd64/gplbld/verify-editors.py
#   python3 .../verify-editors.py --allow-stale
#
# NO SUDO, no fixtures, no account state - everything here is a READ, plus two
# sd sessions that only reach refusal paths.  Exit 0 / 1 / 2 as the others.
#
# ***IT FAILS THE QUIET WAY, WHICH IS THE WHOLE REASON IT IS WORTH A STEP.***
# That is the port's argument and it transfers exactly.  If the nanorc stopped
# being installed, or /etc/nanorc's include were commented out, or the micro
# syntax master moved, ***NOTHING WOULD BREAK***: nano and micro would still
# open the record and every verb would go on working, against an editor with no
# SD BASIC highlighting at all.  There would be no error, no status and no log
# line - only a feature quietly absent. A defect with no symptom is the kind
# that comes back unnoticed, so it needs an instrument rather than a memory.
#
# ***THE PORT'S QUESTION DOES NOT TRANSFER WHOLE, AND THE DIFFERENCE IS THE
# POINT.***  SD Core for Windows BUNDLES micro and Microsoft Edit into
# {app}\usr\bin, SHA-256 pinned, because its defect 66 was that they used to be
# DOWNLOADED at install time and a user got whatever winget had that day; its
# verifier therefore asks "is the bundled copy the one EDIT resolves, rather
# than whatever is on PATH".  ***HERE THEY ARE NOT BUNDLED AND DELIBERATELY
# SO*** - Microsoft Edit is not packaged for Linux, nano replaces it (owner,
# 10 Sep 2026), and both come from the distribution.  find.editor is
# "command -v" with an ABSOLUTE path required (EDIT:394-397).  So the Linux
# question is not "which copy" but "is there one at all, and is the SYNTAX
# CONFIGURATION - the part this project actually ships - placed where the
# editor will read it".
#
# ***AND ONE ROW IS A GAP THE PORT DOES NOT HAVE: A2.***  Shipping
# /usr/share/nano/sdbasic.nanorc achieves nothing unless /etc/nanorc INCLUDES
# it, and that include is Debian's file, not this project's - a distribution
# change or a local edit could comment it out and the install would go on
# succeeding.  A2 reads the include and requires it to be UNCOMMENTED and to
# glob-match the file actually installed.
#
# WHAT IT CANNOT COVER, SAID OUT LOUD RATHER THAN SCORED.  Nobody can drive a
# full-screen editor down a pipe, so the things a person sees - colour on the
# screen, a "~~" mark surviving a round trip through the editor, the working
# copy being removed on exit - are NOT tested here.  What IS tested is
# everything that happens before the screen is drawn, and the refusal that
# happens INSTEAD of drawing it.
#
import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sdverify as V                                    # noqa: E402

NAME = "verify-editors"

NANORC = "/usr/share/nano/sdbasic.nanorc"
ETC_NANORC = "/etc/nanorc"
MICRO_YAML = os.path.join(V.SDSYS, "microcfg", "syntax", "sdbasic.yaml")
GCAT_EDIT = os.path.join(V.SDSYS, "gcat", "$EDIT")
SRC_EDIT = os.path.join(V.SDSYS, "GPL.BP", "EDIT")
SRC_MICRO = os.path.join(V.SDSYS, "GPL.BP", "MICRO")
VOCT = os.path.join(V.SDSYS, "VOC_TEMPLATE")
OMIT = os.path.join(V.SDSYS, "NEWVOC", "TIER.OMIT.STANDARD")

# The suffix GPL.BP/EDIT gives the working copy so the editor can detect the
# language (EDIT:41-43, :190-191).  The nanorc's own syntax regex has to match
# it or the highlighting never fires.
WORKING_SUFFIX = ".sdbasic"


def readfile(p):
    try:
        with open(p, "r", errors="replace") as f:
            return f.read()
    except OSError:
        return None


def voc_template(name):
    """VOC_TEMPLATE/<name> as a list of fields, or None."""
    t = readfile(os.path.join(VOCT, name))
    return None if t is None else [ln.rstrip("\r") for ln in
                                   t.rstrip("\n").split("\n")]


def active_includes(nanorc_text):
    """The include paths /etc/nanorc actually applies.

    ***A COMMENTED-OUT include IS THE CASE THIS EXISTS FOR***, and Debian's
    shipped /etc/nanorc has three of them sitting right below the live one.  A
    substring search for the filename would find a commented line and report a
    highlighting file as reachable when nano never reads it."""
    out = []
    for ln in (nanorc_text or "").split("\n"):
        m = re.match(r'^\s*include\s+"([^"]+)"', ln)
        if m:
            out.append(m.group(1))
    return out


def include_covers(includes, target):
    """Does any active include cause nano to read TARGET?

    A glob counts only when it is in the SAME DIRECTORY as the target: nano's
    include globs do not recurse, so /usr/share/nano/extra/*.nanorc does not
    reach /usr/share/nano/sdbasic.nanorc."""
    for inc in includes:
        if inc == target:
            return True
        if inc.endswith("*.nanorc") and \
                os.path.dirname(inc) == os.path.dirname(target):
            return True
    return False


def grep_e_compiles(rx):
    """Can grep -E compile this regex?  The same question mknanosyntax.py asks
    before it writes one, asked again of the file that was actually
    INSTALLED - which is not necessarily the one that was generated."""
    try:
        p = subprocess.run(["grep", "-E", rx], input="", stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, universal_newlines=True,
                           timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return False
    # grep exits 1 for "no match", which is success for our purposes; 2 is a
    # bad regex.  Anchor on the exit code, not on empty output - an empty
    # stdout is what BOTH outcomes produce.
    return p.returncode in (0, 1)


def main():
    ap = argparse.ArgumentParser(description="editor wiring and syntax placement")
    ap.add_argument("--account", default=None)
    ap.add_argument("--allow-stale", action="store_true")
    ap.add_argument("--timeout", type=int, default=45)
    a = ap.parse_args()

    run = V.Run(NAME)
    user = os.environ.get("USER") or "?"
    acct = a.account or os.path.join(V.ACCOUNTS, user)

    run.say("%s: as %s (uid %d), NOT elevated" % (NAME, user, os.geteuid()))
    run.say("  sdsys     %s" % V.SDSYS)
    run.say("  account   %s" % acct)
    run.say("  nanorc    %s" % NANORC)
    run.say("  micro     %s" % MICRO_YAML)
    run.say("")

    run.heading("0. preconditions")
    if V.require_not_root(
            run,
            "find.editor resolves on the CALLER'S PATH and place.syntax writes"
            " into the CALLER'S config, so root would measure root's."):
        return run.verdict()
    if V.require_paths(run, V.SD, V.SDSYS, acct):
        return run.verdict()
    if a.allow_stale:
        run.say("  *** --allow-stale: assert-current is NOT being enforced.")
        V.require_current(run)
        run.blocked = None
    elif V.require_current(run):
        return run.verdict()

    # ------------------------------------------- 1. the syntax configuration
    run.heading("1. is the syntax configuration PLACED where it is read?")
    rc_text = readfile(NANORC)
    run.note("A1a the nano syntax file is installed", True, rc_text is not None)
    run.note("A1b and it is not empty", True, bool(rc_text and rc_text.strip()))

    # ***A2: SHIPPING THE FILE ACHIEVES NOTHING IF NOTHING INCLUDES IT.***
    includes = active_includes(readfile(ETC_NANORC))
    run.say("      active includes in %s: %s" % (ETC_NANORC, includes or "none"))
    run.note("A2 %s has an UNCOMMENTED include that covers it" % ETC_NANORC,
             True, include_covers(includes, NANORC))

    yaml_text = readfile(MICRO_YAML)
    run.note("A3a micro's syntax master is installed under sdsys",
             True, yaml_text is not None)
    run.note("A3b and it is not empty", True,
             bool(yaml_text and yaml_text.strip()))

    # A4: every regex in the INSTALLED nanorc must compile.  mknanosyntax.py
    # refuses to WRITE one grep -E cannot compile; this asks the same of the
    # file that is actually on disk.
    rxs = re.findall(r'^\s*i?color\s+\S+\s+"(.*)"\s*$', rc_text or "",
                     re.MULTILINE)
    bad = [r for r in rxs if not grep_e_compiles(r)]
    run.note("A4a the nanorc has colour rules at all (not a stub)",
             True, len(rxs) > 0)
    run.say("      %d colour regex(es), %d that grep -E rejects"
            % (len(rxs), len(bad)))
    run.note("A4b every colour regex compiles", 0, len(bad))
    for r in bad[:3]:
        run.say("      REJECTED: %s" % r[:100])

    # A5: the syntax must DETECT the name EDIT actually gives the working copy.
    m = re.search(r'^\s*syntax\s+(\S+)\s+"([^"]+)"', rc_text or "", re.MULTILINE)
    run.note("A5a the nanorc declares a syntax", True, m is not None)
    if m:
        run.say("      syntax %s matching %s" % (m.group(1), m.group(2)))
        try:
            detects = re.search(m.group(2), "record" + WORKING_SUFFIX) is not None
        except re.error:
            detects = False
        run.note("A5b and it matches the '%s' working copy EDIT writes"
                 % WORKING_SUFFIX, True, detects)

    # --------------------------------------------------- 2. the verb wiring
    run.heading("2. the verb wiring in the INSTALLED tree")
    # A NAME IN gcat IS THERE ONLY BECAUSE SD COMPILED THE PROGRAM AND RAN ITS
    # $catalog - files copied into place prove nothing about the bootstrap.
    run.note("B1 $EDIT is CATALOGUED", True, os.path.exists(GCAT_EDIT))
    run.note("B2 GPL.BP/EDIT source is installed", True, os.path.exists(SRC_EDIT))
    # THE SHRINK IS A CHECK TOO: GPL.BP/MICRO was deleted when EDIT took over.
    run.note("B3 GPL.BP/MICRO is GONE (EDIT replaced it)",
             False, os.path.exists(SRC_MICRO))

    for verb, target in (("NANO", "$EDIT"), ("MICRO", "$EDIT"),
                         ("EDIT", "$ED"), ("ED", "$ED")):
        rec = voc_template(verb)
        ok = (rec is not None and len(rec) >= 3
              and rec[0][:1] == "V" and rec[1] == "CA" and rec[2] == target)
        run.note("B4 VOC_TEMPLATE/%-5s is a V/CA verb calling %s"
                 % (verb, target), True, ok)
        if rec is not None and not ok:
            run.say("      got: %r" % (rec,))

    omit = readfile(OMIT)
    omit_names = set((omit or "").split("\n"))
    # MEMBERSHIP, NOT THE COUNT.  PROJECT_STATUS recorded 43 names when NANO
    # was added and the file holds 44 today; a count drifts as the tier list
    # grows and would fail this file for someone else's correct change.
    run.note("B5 NANO is withheld from STANDARD", True, "NANO" in omit_names)
    run.note("B6 MICRO is withheld from STANDARD", True, "MICRO" in omit_names)

    # ------------------------------------------- 3. find.editor's premise
    run.heading("3. find.editor's premise - an ABSOLUTE path from command -v")
    for exe in ("nano", "micro"):
        p = subprocess.run(["sh", "-c", "command -v " + exe],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           universal_newlines=True)
        path = p.stdout.strip()
        run.say("      command -v %-5s -> %r" % (exe, path))
        # EDIT:397 discards anything that does not start with "/", so a shell
        # builtin or an alias would be treated as "not found".
        run.note("C %s resolves to an ABSOLUTE path" % exe,
                 True, path.startswith("/") and os.path.exists(path))

    # ------------------------------------- 4. the verb, driven down a pipe
    #
    # Only refusal paths are reached: a full-screen editor cannot be driven
    # down a pipe, and EDIT knows it - which is itself one of the checks.
    run.heading("4. the verbs, as far as a pipe can take them")
    s = V.show_sd(run, "NANO and MICRO with no arguments",
                  ["NANO", "MICRO"], cwd=acct, timeout=a.timeout)
    V.session_ok(run, "D session", s)
    # ***EACH USAGE LINE NAMES THE VERB AS TYPED, WHICH IS WHAT PROVES BOTH VOC
    # ENTRIES REACH $EDIT AND THAT IT TELLS THEM APART.***  A single shared
    # message would pass a check that only looked for "Usage:".
    run.note("D1 NANO resolved and printed ITS OWN usage line", True,
             V.says(s.text, r"Usage: nano \{dict\} <file> <record>"))
    run.note("D2 MICRO resolved and printed ITS OWN usage line", True,
             V.says(s.text, r"Usage: micro \{dict\} <file> <record>"))
    run.note("D3 neither said 'is not in your VOC'", True,
             not V.says(s.text, r"is not in your VOC"))

    # ***THE TERMINAL GATE IS WHY THIS FILE IS SAFE TO RUN AT ALL.***  Given a
    # file, EDIT checks for a terminal BEFORE it opens anything, and refuses in
    # words naming ed as the alternative.  Without that gate this session would
    # launch nano into a pipe.
    s = V.show_sd(run, "NANO with a file, from a session with no terminal",
                  ["NANO zznosuchfile zznosuchrec"], cwd=acct, timeout=a.timeout)
    V.session_ok(run, "E session", s)
    run.note("D4 the terminal gate fired", True,
             V.says(s.text, r"needs a terminal to draw on, and this session has none"))
    run.note("D5 and it named the alternative that does work", True,
             V.says(s.text, r"\bed\b, the line editor, works anywhere"))
    # The gate fires BEFORE the file is opened - the non-existent file is never
    # reported.  That ordering is what makes the refusal safe rather than lucky.
    run.note("D6 it refused BEFORE touching the file (no file error)", True,
             not V.says(s.text, r"not found|does not exist|Cannot open"))

    rc = run.verdict()
    run.say("")
    run.say("  NOT COVERED, and not claimed: anything a person would SEE.")
    run.say("    - colour actually drawn on a screen (needs a pty or a person)")
    run.say("    - a '~~' mark surviving a round trip through the editor")
    run.say("      (test-edittokens-units.py models that grammar separately)")
    run.say("    - the working copy being removed on exit")
    if a.allow_stale:
        run.say("  (measured with --allow-stale: the install is NOT current.)")
    return rc


if __name__ == "__main__":
    sys.exit(main())
