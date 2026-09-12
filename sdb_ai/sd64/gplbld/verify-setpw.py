#!/usr/bin/env python3
#
# verify-setpw.py - does MODIFY.PASSWORD refuse a trailing token, and ONLY a
#                   trailing token?  PORT_ADOPTION queue 17, queue 22's
#                   ranked worklist item 1.
#
#   python3 /home/don/Projects/sdcore4linux/sdb_ai/sd64/gplbld/verify-setpw.py
#   python3 .../verify-setpw.py --peer PETE       another account to be refused
#   python3 .../verify-setpw.py --allow-stale     measure a stale install
#
# NO SUDO.  Exit 0 every decisive check passed, 1 a decisive check failed,
# 2 the test could not be run.
#
# ***THE CONTROL IS THE WHOLE POINT, AND IT IS THE PORT'S POINT.***  "It
# refused" proves nothing on its own - a verb that refused EVERYTHING would
# score every refusal row a pass.  So the same command without the extra token
# has to get PAST the syntax check and reach passwd(1).  Rows C1-C5 are that
# control, and a run in which they do not fire proves nothing about rows T1-T3.
#
# ***THE CONTROL CANNOT CHANGE A PASSWORD, AND THAT IS MEASURED RATHER THAN
# ASSUMED.***  The non-administrator arm runs "passwd -- <user>" as the user
# itself, so PAM demands the CURRENT password; this feeds it a deliberately
# wrong one, once.  passwd answers "Authentication token manipulation error",
# "password unchanged", and SD reports 10915.  Row C5 proves it independently
# of anything SD said, by comparing "passwd -S <user>"'s last-change date
# BEFORE and AFTER - the instrument rule's before/after, not just the verdict.
# One wrong attempt is deliberate: pam_faillock guards login and su, not
# passwd's own current-password check, so there is no lockout to trip.
#
# ***WHAT AN UNPRIVILEGED RUN CANNOT REACH, SAID OUT LOUD RATHER THAN SCORED
# AS A PASS.***  SET_ACC_PASSWORD tests in this order: trailing token (5276),
# then "not own and not administrator" (2001), then "not in the register"
# (5018), then "no Linux user of its own" (10913).  Because the privilege test
# comes SECOND, a non-administrator naming ANY account but their own is
# refused 2001 and never reaches 5018 or 10913 at all.  ***SO 5018 AND 10913
# ARE NOT REACHABLE FROM THIS FILE*** - they need "sudo sd", and they are
# listed as owed rather than quietly skipped.  Same for the administrator arm
# (!set_passwd -> sd-elevate), which needs K$ADMINISTRATOR and therefore sudo.
#
# ***THE ORDERING ITSELF IS A CHECK, AND IT IS ROW T3.***  "MODIFY.PASSWORD
# <peer> somethingextra" must answer 5276 and NOT 2001.  If it answered 2001
# the refusal would be about privilege rather than about grammar, and T1 would
# no longer prove what it claims - a password on the command line would still
# be discarded in silence for anyone who DID hold the privilege.
#
# ***AND THE NULL CASE HAS ITS OWN ROW, N1.***  If MODIFY.PASSWORD were not in
# this account's VOC, every refusal row would "pass" for the wrong reason: SD
# answers "<verb> is not in your VOC", which contains none of the message text
# the disqualifiers look for.  N1 reads the VOC record, and every treatment row
# also carries "is not in your VOC" as a disqualifier.
#
import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sdverify as V                                    # noqa: E402

NAME = "verify-setpw"

# Quoted from sdsys/MESSAGES so a change there fails this file rather than
# silently weakening it.
M5276 = (r"A password is never given on the command line; MODIFY\.PASSWORD "
         r"prompts for it")
M2001 = r"Command requires administrator privileges"
M5018 = r"Account .* not in register"
M10913 = r"has no Linux user of its own"
M10914 = r"The password for .* was changed"
M10915 = r"The password for .* was NOT changed; passwd ended with status"
MNOVOC = r"is not in your VOC"
MPROMPT = r"[Cc]urrent [Pp]assword:"


def passwd_status(user):
    """'passwd -S <user>' field 3 - the last-change date.  Readable by the
    user for their own account with no sudo; returns None if it cannot be
    read, which the caller treats as "cannot answer", never as "unchanged"."""
    try:
        p = subprocess.run(["passwd", "-S", user], stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, universal_newlines=True,
                           timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if p.returncode != 0:
        return None
    parts = p.stdout.split()
    return parts[2] if len(parts) > 2 else None


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
    run.say("")

    run.heading("0. preconditions")
    if peer == me:
        run.refuse("--peer is the caller's own account (%s)" % peer,
                   "Row T2 asserts that naming SOMEBODY ELSE'S account is"
                   " refused 2001.  Naming your own reaches passwd instead,"
                   " and the row would pass only by not testing anything.")
        return run.verdict()
    if V.require_not_root(
            run,
            "The non-administrator arm is the one measured here: as root the"
            " verb takes the !set_passwd arm instead and asks for no current"
            " password, so a root run answers a different question."):
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
    run.note("T1c did NOT reach passwd", True, not V.says(s.text, MPROMPT))
    run.note("T1d nothing was changed (no 10914)", True,
             not V.says(s.text, M10914))
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
    run.note("T2d did NOT reach passwd", True, not V.says(s.text, MPROMPT))

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
    run.heading("5. CONTROL - the same command WITHOUT the token gets through")
    before = passwd_status(user)
    run.note("C0 the last-change date could be read BEFORE (else C5 cannot"
             " answer)", True, before is not None)
    run.say("      passwd -S %s last change: %s" % (user, before))

    s = V.show_sd(run, "MODIFY.PASSWORD %s + a deliberately WRONG password" % me,
                  ["MODIFY.PASSWORD %s" % me,
                   "definitely-not-the-password",
                   ""],
                  cwd=acct, timeout=a.timeout)
    V.session_ok(run, "C session", s)
    run.note("C1 NOT refused with 5276 - it got past the syntax check",
             True, not V.says(s.text, M5276))
    run.note("C2 it reached passwd(1) - the prompt or 10915 proves it",
             True, V.says(s.text, MPROMPT) or V.says(s.text, M10915))
    run.note("C3 passwd refused the wrong password (10915, not 10914)",
             True, V.says(s.text, M10915) and not V.says(s.text, M10914))
    # ***PAM ENFORCES IT, NOT SD - AND THIS IS THE ROW THAT SHOWS IT.***  SD
    # never prompts and never sees a password; the current-password demand
    # comes from passwd(1) through PAM.  PORT_ADOPTION 17 states this as a
    # premise; here it is measured.
    run.note("C4 the current-password demand came from passwd, not from SD",
             True, V.says(s.text, MPROMPT))

    after = passwd_status(user)
    run.say("      passwd -S %s last change: %s" % (user, after))
    run.note("C5 the password really did NOT change (last-change date is"
             " unmoved)", True,
             before is not None and after is not None and before == after)

    rc = run.verdict()
    run.say("")
    run.say("  NOT REACHABLE WITHOUT sudo, and therefore NOT claimed above:")
    run.say("    - 5018  (account not in the register)  } the privilege test")
    run.say("    - 10913 (account has no Linux user)    } fires first for any")
    run.say("                                           } account but your own")
    run.say("    - the administrator arm (!set_passwd -> sd-elevate passwd),")
    run.say("      which needs K$ADMINISTRATOR and therefore 'sudo sd'.")
    if a.allow_stale:
        run.say("  (measured with --allow-stale: the install is NOT current.)")
    return rc


if __name__ == "__main__":
    sys.exit(main())
