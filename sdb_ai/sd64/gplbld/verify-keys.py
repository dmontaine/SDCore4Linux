#!/usr/bin/env python3
#
# verify-keys.py - does the backspace key erase a character at the command line,
#                  whichever byte the terminal sends for it, under a terminal
#                  type that names the other one?  PORT_ADOPTION queue 22, the
#                  port's verify-keys.ps1 (its PROJECT_STATUS 5.17).
#
#   python3 /home/don/Projects/SDCoreLinuxProject/sdcore4linux/sdb_ai/sd64/gplbld/verify-keys.py
#   python3 .../verify-keys.py --allow-stale     measure a stale install
#
# NO SUDO.  Exit 0 every decisive check passed, 1 a decisive check failed,
# 2 the test could not be run.
#
# THE DEFECT.  A terminal sends Ctrl-H (8) or DEL (127) for backspace.  _keycode
# bound only the byte the terminal type's kbs named, so the key did nothing on a
# terminal that disagreed with its type.  MEASURED 14 Sep 2026 on install
# d704658: after TERM vt100 (kbs ^H), DEL did NOT erase; under linux (the default
# type here) and xterm both bytes did.  Linux emulators send DEL by default.
# _keycode now binds both bytes before the terminfo binds (the port's fix).
#
# THE INSTRUMENT IS WHAT SD EXECUTES, not what it echoes (the port's design).
# "COUNTX<erase> VOC" runs COUNT VOC and answers "N record(s) counted" if the
# erase worked, and "COUNTX is not in your VOC" if it did not - two different
# answers, so a row cannot pass by accident.
#
# ***THE TYPE IS SET INSIDE THE SESSION, AND CONFIRMED.***  SD ignores the
# environment's TERM here - measured: TERM=vt100 in the environment still gave
# "Device : linux".  So each session sends TERM <type> and then TERM, and the
# "Device" line must name the type asked for, or that row measured the wrong
# terminal and is refused.
#
# THE CONTROL sends no erase at all and must get "not in your VOC" under every
# type; without it, a VOC that happened to hold COUNTX would pass everything.
#
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sdverify as V                                    # noqa: E402

NAME = "verify-keys"
COUNTED = r"^\s*\d+ record\(s\) counted"
# ***ANY "is not in your VOC", NOT THE EXACT NAME.***  The red run of 14 Sep on
# the pre-fix install printed "COUNTX^? is not in your VOC" - an unbound DEL
# stays IN the verb - so matching "COUNTX is not in your VOC" let the failure
# row pass beside the failing one.  The failure wording is matched loosely on
# purpose; the success wording ("record(s) counted") stays exact.
NOT_IN_VOC = r"is not in your VOC"
# vt100 is the type the defect was measured on (kbs ^H); linux is the default
# here and xterm is what most emulators claim (kbs DEL both).
TYPES = ("vt100", "linux", "xterm")
ERASES = (("^H", "\x08"), ("DEL", "\x7f"))


def attempt(run, acct, ttype, label, erase, timeout):
    """One session: set the type, show it, then COUNTX<erase> VOC.
    Returns (device, counted, not_in_voc, session)."""
    cmd = "COUNTX" + erase + " VOC"
    run.say("  typed bytes: %r  (erase %s)" % (cmd, label))
    s = V.show_sd(run, "TERM %s, then COUNTX<%s> VOC" % (ttype, label),
                  ["TERM " + ttype, "TERM", cmd], cwd=acct, timeout=timeout)
    m = re.search(r"Device\s*:\s*(\S+)", s.text)
    device = m.group(1) if m else None
    return (device, V.says(s.text, COUNTED), V.says(s.text, NOT_IN_VOC), s)


def main():
    ap = argparse.ArgumentParser(description="backspace erases, either byte")
    ap.add_argument("--allow-stale", action="store_true",
                    help="measure an install assert-current calls stale")
    ap.add_argument("--timeout", type=int, default=30,
                    help="seconds per sd session (default 30)")
    a = ap.parse_args()

    run = V.Run(NAME)
    user = os.environ.get("USER") or "?"
    acct = os.path.join(V.ACCOUNTS, user)
    run.say("%s: as %s (uid %d), NOT elevated" % (NAME, user, os.geteuid()))
    run.say("  sd        %s" % V.SD)
    run.say("  account   %s" % acct)
    run.say("  types     %s" % ", ".join(TYPES))

    run.heading("0. preconditions")
    if V.require_not_root(run, "An ordinary user's command line is what is measured."):
        return run.verdict()
    if V.require_paths(run, V.SD, acct):
        return run.verdict()
    if a.allow_stale:
        run.say("  *** --allow-stale: assert-current is NOT being enforced.")
        V.require_current(run)
        run.blocked = None
    elif V.require_current(run):
        return run.verdict()
    if V.require_running(run, acct):
        return run.verdict()

    for ttype in TYPES:
        run.heading("type %s" % ttype)
        # The control first: no erase, so COUNTX must be refused.
        dev, counted, refused, s = attempt(run, acct, ttype, "none", "", a.timeout)
        V.session_ok(run, "%s control session" % ttype, s)
        run.note("%s.0 the session really is type %s" % (ttype, ttype), ttype, dev)
        run.note("%s.C control: no erase -> COUNTX refused" % ttype, True, refused)
        run.note("%s.C' control: and nothing was counted" % ttype, False, counted)
        for label, erase in ERASES:
            dev, counted, refused, s = attempt(run, acct, ttype, label, erase, a.timeout)
            V.session_ok(run, "%s %s session" % (ttype, label), s)
            run.note("%s.%s type confirmed" % (ttype, label), ttype, dev)
            run.note("%s.%s THE ROW: %s erased, so COUNT VOC ran" % (ttype, label, label),
                     True, counted)
            run.note("%s.%s and COUNTX was not what ran" % (ttype, label), False, refused)

    rc = run.verdict()
    if a.allow_stale:
        run.say("  (measured with --allow-stale: the install is NOT current.)")
    return rc


if __name__ == "__main__":
    sys.exit(main())
