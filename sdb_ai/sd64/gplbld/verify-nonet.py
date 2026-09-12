#!/usr/bin/env python3
#
# verify-nonet.py - prove the SHRINK happened, that nothing sharing its
#                   neighbourhood went with it, and that SDNet's surviving
#                   config knob cannot turn anything back on.
#                   PORT_ADOPTION queue 22; intent from the port's
#                   gplbld/verify-nonet.ps1.
#
#   python3 /home/don/Projects/sdcore4linux/sdb_ai/sd64/gplbld/verify-nonet.py
#   python3 .../verify-nonet.py --allow-stale
#
# NO SUDO.  Reads the source tree and the install, plus one sd session that
# only reads.  Exit 0 / 1 / 2 as the others.
#
# ***THE CONTROLS ARE THE POINT OF THIS FILE, AND THAT IS THE PORT'S OWN
# SENTENCE: "proving three verbs are absent is easy and proves little - a
# botched removal that took APISRVR or the catalogue with it would pass every
# 'is it gone?' check ever written."***  So section 2 asks what SURVIVED, and
# it is not decoration: a green section 1 with a red section 2 is a disaster,
# and a file that only had section 1 would call it a success.
#
# ***AND THIS PROJECT HAS A SHARPER CONTROL THAN THE PORT DOES, BECAUSE IT HAS
# A DOCUMENTED NEAR-MISS TRAP.***  CLAUDE.md, "Conventions": *"Mind the
# near-miss names.  GPL.BP/MODIFY is the record editor and is being removed;
# GPL.BP/MODIFYA is MODIFY.ACCOUNT and stays.  MODIFY.PASSWORD stays."*  A
# removal keyed on the string "MODIFY" takes all three.  Rows B1-B3 are that
# trap, asserted rather than remembered.
#
# WHAT WENT, on the owner's stance of 8 Sep 2026: the TAPE/RESTORE subsystem,
# PROC, SED, UPDATE.RECORD, MODIFY, SDNet, the VFS scaffolding, OPGEN and the
# SDSYS BP test programs.  SDNet is the one with a security story: a VOC entry
# of the form "server;file" made op_dio1.c split on the semicolon and call
# net_open(), which read a user name and password from sd.conf - obscured by
# letter substitution, not encrypted - and connected on port 4245.
#
# ***THE KNOB SURVIVED THE MECHANISM, IN BOTH TREES, AND SECTION 3 IS ABOUT
# THAT.***  NETFILES is still parsed (config.c:219-220), still copied into
# shared memory (sysseg.c:217) and still reportable by CONFIG('NETFILES')
# (op_config.c:135) - and is consulted by NOTHING.  The port keeps it too
# (its config.c:276-277, header.h:64), so under the owner's conformance ruling
# it STAYS, and this file does not fail it.  What section 3 proves is the part
# that matters: ***the knob is inert.***  Setting NETFILES=1 cannot reach a
# remote file, because net_open, netfiles.c, the NET_FILE descriptor type and
# the semicolon dispatch are all gone.  A dead parameter is untidy; a live one
# nobody noticed would be a hole.
#
# WHY THE SEMICOLON CASE IS NOT EXERCISED, and the port says the same: reaching
# it needs a VOC F-pointer whose path contains a ";", and VOC is a hashed file,
# so a record cannot be planted from outside SD.  The branch that read the
# semicolon is deleted outright rather than disabled, so what is checked is
# that the code behind it is gone and that ordinary file access still works.
#
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sdverify as V                                    # noqa: E402

NAME = "verify-nonet"
TREE = os.path.dirname(HERE)                 # .../sdb_ai/sd64
GPLSRC = os.path.join(TREE, "gplsrc")
SRC_BP = os.path.join(TREE, "sdsys", "GPL.BP")
SRC_VOCT = os.path.join(TREE, "sdsys", "VOC_TEMPLATE")

# The owner's stance list, 8 Sep 2026.  Each name is checked in the SOURCE tree
# and in the INSTALL, because a removal that reached only one of them leaves
# the other shipping.
REMOVED_PROGRAMS = ["MODIFY", "PROC", "SED", "UPDATE.RECORD", "TAPE",
                    "RESTORE", "OPGEN", "SDNET", "NETWORK"]
REMOVED_VERBS = ["MODIFY", "PROC", "SED", "UPDATE.RECORD", "TAPE", "RESTORE",
                 "OPGEN"]

# ***THE CONTROLS.***  Every one of these is a near neighbour of something
# above - by name, by function, or by having shipped in the same cycle.
SURVIVING_PROGRAMS = ["MODIFYA", "SET_ACC_PASSWORD", "ED", "EDIT", "APISRVR",
                      "CPROC", "LOGIN", "SETPTR"]
SURVIVING_VERBS = ["MODIFY.ACCOUNT", "MODIFY.PASSWORD", "ED", "EDIT"]
SURVIVING_CATALOGUE = ["$MODIFYA", "$APISRVR", "$EDIT", "$ED"]

# The SDNet machinery itself.
GONE_FROM_C = ["net_open", "NET_FILE"]


_BLOCK = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE = re.compile(r"//[^\n]*")


def strip_c_comments(text):
    """Blank out C comments, KEEPING the line count so hits still cite the
    right line.

    ***THIS EXISTS BECAUSE THE FIRST RUN OF THIS FILE FAILED ON ITS OWN
    TOMBSTONES.***  `op_dio1.c`'s START-HISTORY says, in prose, *"the ';'
    network-file dispatch and net_open() call are gone"* and *"netfiles.c and
    the NET_FILE type are deleted"* - so a search for `net_open(` found the
    sentence announcing its removal and reported the removal as incomplete.
    Measured 12 Sep 2026: 4 decisive rows failed, every one of them on a
    comment.  ***A REMOVAL CHECK MUST READ CODE, NOT PROSE***, and prose is
    exactly where a removal is most likely to be described."""
    def blank(m):
        return re.sub(r"[^\n]", " ", m.group(0))
    return _LINE.sub(blank, _BLOCK.sub(blank, text))


def grep_tree(pattern, root, exts=(".c", ".h")):
    """Files under ROOT whose CODE matches PATTERN - comments are blanked
    first, see strip_c_comments."""
    hits = []
    rx = re.compile(pattern)
    for dirpath, _dirs, files in os.walk(root):
        for fn in files:
            if not fn.endswith(exts):
                continue
            p = os.path.join(dirpath, fn)
            try:
                with open(p, "r", errors="replace") as f:
                    code = strip_c_comments(f.read())
            except OSError:
                continue
            for i, line in enumerate(code.split("\n"), 1):
                if rx.search(line):
                    hits.append("%s:%d" % (os.path.relpath(p, root), i))
    return hits


def main():
    ap = argparse.ArgumentParser(description="the shrink, and its controls")
    ap.add_argument("--account", default=None)
    ap.add_argument("--allow-stale", action="store_true")
    ap.add_argument("--timeout", type=int, default=45)
    a = ap.parse_args()

    run = V.Run(NAME)
    user = os.environ.get("USER") or "?"
    acct = a.account or os.path.join(V.ACCOUNTS, user)
    inst_bp = os.path.join(V.SDSYS, "GPL.BP")
    inst_voct = os.path.join(V.SDSYS, "VOC_TEMPLATE")
    inst_gcat = os.path.join(V.SDSYS, "gcat")

    run.say("%s: as %s (uid %d)" % (NAME, user, os.geteuid()))
    run.say("  source tree  %s" % TREE)
    run.say("  install      %s" % V.SDSYS)
    run.say("  account      %s" % acct)
    run.say("")

    run.heading("0. preconditions")
    if V.require_paths(run, V.SD, V.SDSYS, GPLSRC, SRC_BP, SRC_VOCT,
                       inst_bp, inst_voct, inst_gcat):
        return run.verdict()
    if a.allow_stale:
        run.say("  *** --allow-stale: assert-current is NOT being enforced.")
        V.require_current(run)
        run.blocked = None
    elif V.require_current(run):
        return run.verdict()

    # ------------------------------------------------------- 1. what went
    run.heading("1. what the shrink removed")
    for n in REMOVED_PROGRAMS:
        # BOTH trees: a removal that reached only the source leaves the install
        # shipping the program, and only the install leaves it coming back on
        # the next build.
        run.note("A source GPL.BP/%-13s is gone" % n,
                 False, os.path.exists(os.path.join(SRC_BP, n)))
        run.note("A install GPL.BP/%-12s is gone" % n,
                 False, os.path.exists(os.path.join(inst_bp, n)))
    for n in REMOVED_VERBS:
        run.note("A VOC_TEMPLATE/%-13s is gone" % n,
                 False, os.path.exists(os.path.join(SRC_VOCT, n)))

    run.heading("1b. SDNet's own machinery")
    # ***CODE ONLY - COMMENTS ARE BLANKED FIRST.***  descr.h keeps "4 was
    # NET_FILE" and op_dio1.c's history says net_open() "are gone"; matching
    # prose reports the tombstone as the corpse, which is exactly what the
    # first run of this file did (see strip_c_comments).
    for sym, pat in (("net_open()", r"\bnet_open\s*\("),
                     ("NET_FILE as a type", r"\bNET_FILE\b")):
        hits = grep_tree(pat, GPLSRC)
        run.say("      %s: %s" % (sym, hits or "no hits"))
        run.note("A %s is gone from gplsrc" % sym, 0, len(hits))
    run.note("A gplsrc/netfiles.c is gone", False,
             os.path.exists(os.path.join(GPLSRC, "netfiles.c")))

    # ------------------------------------------------ 2. THE CONTROLS
    #
    # A green section 1 with a red section 2 is a botched removal, and a file
    # with only section 1 would call it a success.
    run.heading("2. THE CONTROLS - what had to survive, and did")
    for n in SURVIVING_PROGRAMS:
        run.note("B source GPL.BP/%-17s survived" % n,
                 True, os.path.exists(os.path.join(SRC_BP, n)))
        run.note("B install GPL.BP/%-16s survived" % n,
                 True, os.path.exists(os.path.join(inst_bp, n)))
    for n in SURVIVING_VERBS:
        run.note("B VOC_TEMPLATE/%-17s survived" % n,
                 True, os.path.exists(os.path.join(SRC_VOCT, n)))
    # A NAME IN gcat IS THERE ONLY BECAUSE SD COMPILED THE PROGRAM AND RAN ITS
    # $catalog, so this is a stronger statement than "the file is present".
    for c in SURVIVING_CATALOGUE:
        run.note("B %-10s is still CATALOGUED" % c,
                 True, os.path.exists(os.path.join(inst_gcat, c)))
    ncat = len(os.listdir(inst_gcat))
    run.say("      the global catalogue holds %d entries" % ncat)
    run.note("B the catalogue was not emptied", True, ncat > 100)

    # ------------------------------------------- 3. the knob that survived
    run.heading("3. NETFILES survived the mechanism - prove it is inert")
    cfg = os.path.join(GPLSRC, "config.c")
    parsed = bool(grep_tree(r'NETFILES=%d', GPLSRC))
    # NOT A FAILURE.  The port keeps it too, so under the conformance ruling it
    # stays; this row records the fact so nobody "fixes" it as a divergence.
    run.note("C NETFILES is still parsed (conformant with the port, recorded"
             " not failed)", True, parsed, decisive=False)
    # ***THE DECISIVE PART: THE KNOB CANNOT REACH ANYTHING.***
    run.note("C and nothing acts on it - no net_open call survives", 0,
             len(grep_tree(r"\bnet_open\s*\(", GPLSRC)))
    dio1 = os.path.join(GPLSRC, "op_dio1.c")
    try:
        with open(dio1, "r", errors="replace") as f:
            dio1_text = strip_c_comments(f.read())
    except OSError:
        dio1_text = ""
    # The dispatch was a split on ';' feeding a remote open.  Anything left
    # would show as a net_* call in this file.
    run.note("C op_dio1.c has no remote-open dispatch left", 0,
             len(re.findall(r"\bnet_[a-z_]+\s*\(", dio1_text)))

    # ---------------------------------- 4. ordinary file access is untouched
    #
    # The port's closing point: what the removal must NOT have broken is the
    # thing the removed code sat inside.
    run.heading("4. ordinary file access still works")
    s = V.show_sd(run, "open and read a file the ordinary way",
                  ["CT VOC SYSCOM", "COUNT VOC"],
                  cwd=acct, timeout=a.timeout)
    V.session_ok(run, "D session", s)
    run.note("D1 a VOC pointer still reads", True,
             V.says(s.text, r"^2: @SDSYS/SYSCOM"))
    run.note("D2 the file layer still counts records", True,
             V.says(s.text, r"^[1-9][0-9]* record\(s\) counted"))
    run.note("D3 nothing complained about a network file", True,
             not V.says(s.text, r"[Nn]etwork|[Rr]emote host|net_open"))

    rc = run.verdict()
    run.say("")
    run.say("  NOT EXERCISED, deliberately, and the port says the same: the")
    run.say("  \"server;file\" VOC form itself.  Reaching it needs an F-pointer")
    run.say("  whose path contains a ';' and VOC is a hashed file, so the")
    run.say("  record cannot be planted from outside SD.  The branch was")
    run.say("  DELETED rather than disabled, which is what sections 1b and 3")
    run.say("  check instead.")
    if a.allow_stale:
        run.say("  (measured with --allow-stale: the install is NOT current.)")
    return rc


if __name__ == "__main__":
    sys.exit(main())
