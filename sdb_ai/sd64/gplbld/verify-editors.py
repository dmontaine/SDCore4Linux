#!/usr/bin/env python3
#
# verify-editors.py - is micro's SD BASIC syntax file actually PLACED where the editor will read it, is the
#                     MICRO verb wired to $edit, and does find.editor's premise hold?
#                     PORT_ADOPTION queue 22; intent from the port's gplbld/verify-editors.ps1.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/verify-editors.py
#   python3 .../verify-editors.py --allow-stale
#
# START-HISTORY:
# 27 Oct 26 dm  S.87 batch 14: the NANO verb is gone (owner), so nano's syntax file, the /etc/nanorc include and the NANO rows are
#               gone with it; micro is the one external editor.  test-editors-units.py, which drove the nanorc include logic,
#               was deleted.
# END-HISTORY
#
# NO SUDO, no fixtures, no account state - everything here is a READ, plus two sd sessions that only reach refusal
# paths.  Exit 0 / 1 / 2 as the others.
#
# ***IT FAILS THE QUIET WAY, WHICH IS THE WHOLE REASON IT IS WORTH A STEP.***  If micro's syntax master moved,
# ***NOTHING WOULD BREAK***: micro would still open the record and every verb would go on working, against an
# editor with no SD BASIC highlighting at all.  There would be no error, no status and no log line - only a feature
# quietly absent.  A defect with no symptom is the kind that comes back unnoticed, so it needs an instrument rather
# than a memory.
#
# ***HERE THE EDITOR IS NOT BUNDLED AND DELIBERATELY SO*** - micro comes from the distribution.  find.editor is
# "command -v" with an ABSOLUTE path required.  So the Linux question is "is there one at all, and is the SYNTAX
# CONFIGURATION - the part this project actually ships - placed where the editor will read it".
#
# WHAT IT CANNOT COVER, SAID OUT LOUD RATHER THAN SCORED.  Nobody can drive a full-screen editor down a pipe, so the
# things a person sees - colour on the screen, a "~~" mark surviving a round trip through the editor, the working copy
# being removed on exit - are NOT tested here.  What IS tested is everything that happens before the screen is drawn,
# and the refusal that happens INSTEAD of drawing it.
#
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sdverify as V                                    # noqa: E402

NAME = "verify-editors"

MICRO_YAML = os.path.join(V.SDSYS, "microcfg", "syntax", "sdbasic.yaml")
GCAT_EDIT = os.path.join(V.SDSYS, "gcat", "$edit")   # lower case since PAL-1 stage 3a (6 Oct 26)
SRC_EDIT = os.path.join(V.SDSYS, "gpl.bp", "edit")     # record names lower since 13 Sep 26
SRC_MICRO = os.path.join(V.SDSYS, "gpl.bp", "micro")
VOCT = os.path.join(V.SDSYS, "voc_template")
NEWVOC = os.path.join(V.SDSYS, "newvoc")   # 18 Sep 26: the one VOC layer (S.25)


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
    yaml_text = readfile(MICRO_YAML)
    run.note("A3a micro's syntax master is installed under sdsys",
             True, yaml_text is not None)
    run.note("A3b and it is not empty", True,
             bool(yaml_text and yaml_text.strip()))

    # --------------------------------------------------- 2. the verb wiring
    run.heading("2. the verb wiring in the INSTALLED tree")
    # A NAME IN gcat IS THERE ONLY BECAUSE SD COMPILED THE PROGRAM AND RAN ITS
    # $catalog - files copied into place prove nothing about the bootstrap.
    run.note("B1 $EDIT is CATALOGUED", True, os.path.exists(GCAT_EDIT))
    run.note("B2 GPL.BP/EDIT source is installed", True, os.path.exists(SRC_EDIT))
    # THE SHRINK IS A CHECK TOO: GPL.BP/MICRO was deleted when EDIT took over.
    # GONE IN EITHER CASE: record names are lower since 13 Sep 26, so testing
    # only one spelling would pass on a tree that ships the other.
    run.note("B3 GPL.BP/MICRO is GONE (EDIT replaced it), either case",
             False, os.path.exists(SRC_MICRO)
             or os.path.exists(os.path.join(V.SDSYS, "gpl.bp", "MICRO")))

    # The VOC ids (file names here, entries in the omit list) are lower case
    # since plan M3, 12 Sep 2026; field 3, the CATALOGUE name, is lower case
    # since PAL-1 stage 3b, 7 Oct 2026 ($EDIT before it).
    for verb, target in (("MICRO", "$edit"), ("EDIT", "$ed"), ("ED", "$ed")):
        rec = voc_template(verb.lower())
        ok = (rec is not None and len(rec) >= 3
              and rec[0][:1] == "V" and rec[1] == "CA" and rec[2] == target)
        run.note("B4 VOC_TEMPLATE/%-5s is a V/CA verb calling %s"
                 % (verb, target), True, ok)
        if rec is not None and not ok:
            run.say("      got: %r" % (rec,))

    # 18 Sep 26 - S.25 (the owner's teardown): THE OMIT LIST WENT WITH THE TIER
    # MODEL; there is one VOC layer now - NEWVOC as shipped, which every
    # account gets - so the rows assert that micro is IN that layer.  (The tier
    # machinery's own absence is witness-absence.sh M1, not this file's question.)
    run.note("B6 MICRO is in NEWVOC, the one layer every account gets (S.25)",
             True, readfile(os.path.join(NEWVOC, "micro")) is not None)
    # 27 Oct 26: and the NANO verb is not.
    run.note("B7 NANO is GONE from NEWVOC and VOC_TEMPLATE (S.87 batch 14)",
             False, os.path.exists(os.path.join(NEWVOC, "nano"))
             or os.path.exists(os.path.join(VOCT, "nano")))

    # ------------------------------------------- 3. find.editor's premise
    run.heading("3. find.editor's premise - an ABSOLUTE path from command -v")
    import subprocess
    for exe in ("micro",):
        p = subprocess.run(["sh", "-c", "command -v " + exe],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           universal_newlines=True)
        path = p.stdout.strip()
        run.say("      command -v %-5s -> %r" % (exe, path))
        # find.editor discards anything that does not start with "/", so a shell
        # builtin or an alias would be treated as "not found".
        run.note("C %s resolves to an ABSOLUTE path" % exe,
                 True, path.startswith("/") and os.path.exists(path))

    # ------------------------------------- 4. the verb, driven down a pipe
    #
    # Only refusal paths are reached: a full-screen editor cannot be driven
    # down a pipe, and EDIT knows it - which is itself one of the checks.
    run.heading("4. the verb, as far as a pipe can take it")
    s = V.show_sd(run, "MICRO with no arguments",
                  ["MICRO"], cwd=acct, timeout=a.timeout)
    V.session_ok(run, "D session", s)
    # ***THE USAGE LINE NAMES THE VERB AS TYPED, WHICH IS WHAT PROVES THE VOC
    # ENTRY REACHES $EDIT.***  A check that only looked for "Usage:" would pass
    # on any message.
    run.note("D2 MICRO resolved and printed ITS OWN usage line", True,
             V.says(s.text, r"Usage: micro \{dict\} <file> <record>"))
    run.note("D3 it did not say 'is not in your VOC'", True,
             not V.says(s.text, r"is not in your VOC"))

    # ***THE TERMINAL GATE IS WHY THIS FILE IS SAFE TO RUN AT ALL.***  Given a
    # file, EDIT checks for a terminal BEFORE it opens anything, and refuses in
    # words naming ed as the alternative.  Without that gate this session would
    # launch micro into a pipe.
    s = V.show_sd(run, "MICRO with a file, from a session with no terminal",
                  ["MICRO zznosuchfile zznosuchrec"], cwd=acct, timeout=a.timeout)
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
