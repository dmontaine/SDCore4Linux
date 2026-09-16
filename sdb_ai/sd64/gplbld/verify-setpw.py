#!/usr/bin/env python3
#
# verify-setpw.py - does MODIFY.PASSWORD refuse a trailing token, and ONLY a
#                   trailing token?  PORT_ADOPTION queue 17, queue 22's
#                   ranked worklist item 1.
#
#   python3 /home/don/Projects/SDCoreLinuxProject/sdcore4linux/sdb_ai/sd64/gplbld/verify-setpw.py
#   python3 .../verify-setpw.py --peer PETE       another account to be refused
#   python3 .../verify-setpw.py --allow-stale     measure a stale install
#
# NO SUDO.  Exit 0 every decisive check passed, 1 a decisive check failed,
# 2 the test could not be run.
#
# 14 Sep 2026 - THE CONTROL ROWS WERE REWRITTEN WHEN MODIFY.PASSWORD BECAME THE
# WINDOWS PORT'S (W.4 SCRAM phase 2).  It no longer runs passwd(1): it sets SD's
# own API credential in $cred, which is root:root 0700, and CPROC gives it
# euid 0 only in a root session.  So an unprivileged run can no longer reach a
# password prompt at all - the old C1-C5 (PAM refusing a wrong current
# password) measured behaviour that was deliberately removed, and would have
# failed for that reason alone.
#
# ***THE CONTROL IS STILL THE WHOLE POINT, AND IT IS THE PORT'S POINT.***  "It
# refused" proves nothing on its own - a verb that refused EVERYTHING would
# score every refusal row a pass.  So the same command without the extra token
# has to get PAST the syntax check and the privilege check and reach the
# credential register's gate.  As an ordinary session it is then refused THERE,
# with "MODIFY.PASSWORD needs sudo sd" - the port's "ordinary console NO,
# deliberately" (its secure-cred.ps1).  Rows C1-C4 are that control: C2 shows
# the gate was reached, C3 that nothing was set and no password asked for, C4
# that the register is root-only.
#
# ***C2 AND C3 FAILED ON THEIR FIRST RUN, 14 Sep 2026 on 74c60d4, AND THE
# PRODUCT WAS WRONG, NOT THE INSTRUMENT.***  They expected "Cannot open the
# $cred register"; the verb instead said "has no password set" and prompted,
# because a directory file opens without permission and the refused read looks
# like a missing record.  SET_ACC_PASSWORD now refuses on the real uid before
# any prompt, and C2 matches that refusal's wording.
#
# ***WHAT AN UNPRIVILEGED RUN CANNOT REACH, SAID OUT LOUD RATHER THAN SCORED
# AS A PASS.***  SET_ACC_PASSWORD tests in this order: trailing token (5276),
# then "not own and not administrator" (2001), then "not in the register"
# (5018), then the $cred open.  Because the privilege test comes SECOND, a
# non-administrator naming ANY account but their own is refused 2001 and never
# reaches 5018.  ***SO 5018 AND THE CREDENTIAL WRITE ARE NOT REACHABLE FROM THIS
# FILE*** - they need "sudo sd", and witness-release-run.sh section 13 measures
# the write (C0-C7).
#
# ***THE ORDERING ITSELF IS A CHECK, AND IT IS ROW T3.***  "MODIFY.PASSWORD
# <peer> somethingextra" must answer 5276 and NOT 2001.  If it answered 2001
# the refusal would be about privilege rather than about grammar, and T1 would
# no longer prove what it claims.
#
# ***AND THE NULL CASE HAS ITS OWN ROW, N1.***  If MODIFY.PASSWORD were not in
# this account's VOC, every refusal row would "pass" for the wrong reason: SD
# answers "<verb> is not in your VOC", which contains none of the message text
# the disqualifiers look for.  N1 reads the VOC record, and every treatment row
# also carries "is not in your VOC" as a disqualifier.
#
import argparse
import os
import stat
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sdverify as V                                    # noqa: E402

NAME = "verify-setpw"

# Quoted from sdsys/MESSAGES and SET_ACC_PASSWORD so a change there fails this
# file rather than silently weakening it.
M5276 = (r"A password is never given on the command line; MODIFY\.PASSWORD "
         r"prompts for it")
M2001 = r"Command requires administrator privileges"
MCRED = r"MODIFY\.PASSWORD needs sudo sd"
MSET = r"Password set for account"
MNEWPW = r"New password:"
MNOVOC = r"is not in your VOC"


def cred_mode():
    """(owner, group, mode) of $cred, read with stat - the parent directory
    is world-searchable, so this needs no privilege.  None if it cannot be
    read, which the caller treats as "cannot answer", never as a pass."""
    path = os.path.join(V.SDSYS, "$cred")
    try:
        st = os.stat(path)
    except OSError:
        return None
    import grp
    import pwd
    try:
        owner = pwd.getpwuid(st.st_uid).pw_name
        group = grp.getgrgid(st.st_gid).gr_name
    except KeyError:
        return None
    return (owner, group, "%o" % stat.S_IMODE(st.st_mode))


def main():
    ap = argparse.ArgumentParser(
        description="does MODIFY.PASSWORD refuse a trailing token, and only that")
    ap.add_argument("--peer", default="PETE",
                    help="an account that is NOT the caller's, to be refused "
                         "with 2001 (default PETE)")
    ap.add_argument("--account", default=None,
                    help="account directory to run in")
    ap.add_argument("--allow-stale", action="store_true",
                    help="measure an install assert-current calls stale")
    ap.add_argument("--timeout", type=int, default=45,
                    help="seconds per sd session (default 45)")
    a = ap.parse_args()

    run = V.Run(NAME)

    user = os.environ.get("USER") or "?"
    acct = a.account or os.path.join(V.ACCOUNTS, user)
    me = user.upper()
    peer = a.peer.upper()

    run.say("%s: as %s (uid %d), NOT elevated" % (NAME, user, os.geteuid()))
    run.say("  sd        %s" % V.SD)
    run.say("  account   %s" % acct)
    run.say("  own       %s   (the account this session is logged in to)" % me)
    run.say("  peer      %s   (must be refused, and must NOT be the caller)" % peer)
    run.say("  register  %s" % os.path.join(V.SDSYS, "$cred"))
    run.say("")

    run.heading("0. preconditions")
    if peer == me:
        run.refuse("--peer is the caller's own account (%s)" % peer,
                   "Row T2 asserts that naming SOMEBODY ELSE'S account is"
                   " refused 2001.  Naming your own reaches the register"
                   " instead, and the row would pass only by not testing"
                   " anything.")
        return run.verdict()
    if V.require_not_root(
            run,
            "The unprivileged session is the one measured here: as root CPROC"
            " restores euid 0 for MODIFY.PASSWORD and the verb would open"
            " $cred and prompt, which answers a different question."):
        return run.verdict()
    if V.require_paths(run, V.SD, V.SDSYS, acct):
        return run.verdict()
    if a.allow_stale:
        run.say("  *** --allow-stale: assert-current is NOT being enforced.")
        run.say("  *** Say which commit the install was built from, and why")
        run.say("  *** the delta cannot affect this check, when quoting this.")
        V.require_current(run)
        run.blocked = None
    elif V.require_current(run):
        return run.verdict()

    # ------------------------------------------------------- N1, the null case
    run.heading("1. the null case - is the verb even here?")
    s = V.show_sd(run, "read the VOC record",
                  ["CT VOC MODIFY.PASSWORD"], cwd=acct, timeout=a.timeout)
    V.session_ok(run, "N session", s)
    run.note("N1 MODIFY.PASSWORD is in this account's VOC", True,
             V.says(s.text, r"^3: \$MODIFY\.PASSWORD"))
    run.note("N2 and it is a verb (V) catalogued CA", True,
             V.says(s.text, r"^1: V") and V.says(s.text, r"^2: CA"))

    # ------------------------------------------------ T1, the trailing token
    run.heading("2. treatment - a trailing token is refused")
    s = V.show_sd(run, "MODIFY.PASSWORD %s somethingextra" % me,
                  ["MODIFY.PASSWORD %s somethingextra" % me],
                  cwd=acct, timeout=a.timeout)
    V.session_ok(run, "T1 session", s)
    run.note("T1a refused with 5276", True, V.says(s.text, M5276))
    run.note("T1b the verb resolved (not 'is not in your VOC')",
             True, not V.says(s.text, MNOVOC))
    run.note("T1c did NOT reach the credential register", True,
             not V.says(s.text, MCRED))
    run.note("T1d nothing was set", True, not V.says(s.text, MSET))
    run.note("T1e it was the GRAMMAR that refused, not privilege (no 2001)",
             True, not V.says(s.text, M2001))

    # ---------------------------------------------- T2, somebody else's account
    run.heading("3. treatment - another account needs administrator rights")
    s = V.show_sd(run, "MODIFY.PASSWORD %s" % peer,
                  ["MODIFY.PASSWORD %s" % peer], cwd=acct, timeout=a.timeout)
    V.session_ok(run, "T2 session", s)
    run.note("T2a refused with 2001", True, V.says(s.text, M2001))
    run.note("T2b the verb resolved", True, not V.says(s.text, MNOVOC))
    run.note("T2c not the trailing-token refusal (no 5276)",
             True, not V.says(s.text, M5276))
    run.note("T2d did NOT reach the credential register", True,
             not V.says(s.text, MCRED))

    # ------------------------------------------------------ T3, the ordering
    run.heading("4. treatment - the grammar is checked BEFORE the privilege")
    s = V.show_sd(run, "MODIFY.PASSWORD %s somethingextra" % peer,
                  ["MODIFY.PASSWORD %s somethingextra" % peer],
                  cwd=acct, timeout=a.timeout)
    V.session_ok(run, "T3 session", s)
    run.note("T3a refused with 5276, not 2001", True, V.says(s.text, M5276))
    run.note("T3b and 2001 did NOT appear - so T1 is about grammar",
             True, not V.says(s.text, M2001))

    # ---------------------------------------------------------- the CONTROL
    #
    # Without this the rows above prove nothing: a verb that refused everything
    # would have scored them all.
    run.heading("5. CONTROL - the same command WITHOUT the token gets through,"
                " to the register")
    before = cred_mode()
    run.say("      $cred before: %s" % (before,))
    s = V.show_sd(run, "MODIFY.PASSWORD %s (own account, no extra token)" % me,
                  ["MODIFY.PASSWORD %s" % me], cwd=acct, timeout=a.timeout)
    V.session_ok(run, "C session", s)
    run.note("C1 NOT refused with 5276 or 2001 - it got past grammar and"
             " privilege", True,
             not V.says(s.text, M5276) and not V.says(s.text, M2001))
    run.note("C2 it reached the credential register and was refused there",
             True, V.says(s.text, MCRED))
    run.note("C3 nothing was set, and no password was asked for", True,
             not V.says(s.text, MSET) and not V.says(s.text, MNEWPW))
    after = cred_mode()
    run.say("      $cred after : %s" % (after,))
    # ***THE REFUSAL IS THE REGISTER'S MODE AND THIS IS THE ROW THAT SHOWS IT.***
    # An ordinary session cannot open a root:root 0700 directory; if the
    # register were anything wider, C2 would be a different failure.
    run.note("C4 the register is root:root 700, before and after", True,
             before == ("root", "root", "700") and after == before)

    rc = run.verdict()
    run.say("")
    run.say("  NOT REACHABLE WITHOUT sudo, and therefore NOT claimed above:")
    run.say("    - 5018  (account not in the register) - the privilege test")
    run.say("      fires first for any account but your own")
    run.say("    - the credential write itself (!CRED_SET under euid 0), which")
    run.say("      needs 'sudo sd'; witness-release-run.sh section 13 has it.")
    if a.allow_stale:
        run.say("  (measured with --allow-stale: the install is NOT current.)")
    return rc


if __name__ == "__main__":
    sys.exit(main())
