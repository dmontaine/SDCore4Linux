#!/usr/bin/env python3
#
# verify-accounts.py - is the account register true about the operating system,
#                      and do the account verbs refuse a session that is not
#                      root?  PORT_ADOPTION queue 22, ranked item 6 - the
#                      NO-SUDO HALF of the port's account family
#                      (verify-createaccount, verify-delaccount,
#                      verify-acctmsgs, verify-accountrules).
#
#   python3 /home/don/Projects/sdcore4linux/sdb_ai/sd64/gplbld/verify-accounts.py
#   python3 .../verify-accounts.py --allow-stale      measure a stale install
#
# NO SUDO.  Exit 0 every decisive check passed, 1 a decisive check failed,
# 2 the test could not be run.
#
# ***WHY IT IS A HALF, AND THE SPLIT IS MEASURED RATHER THAN ASSUMED.***  The
# port's four scripts CREATE and DELETE a throwaway account; here that needs
# root, and it is not a preference.  Measured 12 Sep 2026 as `don`, an
# ADMINISTRATOR, in a plain `sd` session: `CREATE.ACCOUNT` and `DELETE.ACCOUNT`
# both answer ***2001 "Command requires administrator privileges"*** and do
# nothing.  ***THAT REFUSAL IS NOT A VOC MISS*** - `CT VOC CREATE.ACCOUNT`
# returns `V / CA / $CREATEA`, so the verb resolved, ran, and stopped at
# CREATEA's own check; the control is that an invented verb answers
# "is not in your VOC" instead.  Section 4 is that measurement, and it is one
# of the few decisive things this side of the line can say about the verbs.
#
# ***THE CREATE-AND-DELETE HALF BELONGS IN AN OWNER-RUN WITNESS SCRIPT***, per
# the model PORT_ADOPTION 12 and 14 used: one script, backs up what it changes,
# PASS/FAIL on the success wording, restores on failure, tees to a log.  It
# also wants the FULL delete->install this project already owes, because a
# keep-accounts cycle never runs `installsdai.sh`'s seeding block.
#
# ***WHAT THIS HALF CAN STILL DECIDE, AND IT IS MORE THAN IT LOOKS.***  The
# register `@SDSYS/ACCOUNTS` is a DIRECTORY file and world-readable
# (`-rw-r--r-- root root`), so every claim it makes about the operating system
# can be checked against the operating system by an ordinary user, with no
# session at all.  Three of those checks are invariants nothing else enforces:
#
#   1. ***BOTH DIRECTIONS.***  `gplbld/reconcile-accounts.sh` (queue 19) finds
#      a register record whose Linux user has GONE.  Nothing looks the other
#      way - an account DIRECTORY with no register record - and that is the
#      direction a keep-accounts delete->install could produce, since the
#      directories survive the cycle and the register is rewritten by it.
#   2. ***FIELD 4 IS NEVER WRITTEN.***  `SYSCOM/KEYS.H:277-278` says so in a
#      comment: the retired `ACC$USERS` slot must stay empty, because "a new
#      meaning there would read old data as new".  A comment cannot enforce
#      itself; row R4 can.
#   3. ***THE `sdadmin` GROUP FOLLOWS THE TIER.***  `MODIFYA set.tier` writes
#      `ACC$TIER` and then reconciles `sdadmin` - register first, group second
#      (PRE_RELEASE_FIXES, MODIFYA table).  Two writes that can be interrupted
#      between them, and nothing re-checks the pair afterwards.
#
# RUN IT UNELEVATED, AND THAT IS NOT A PREFERENCE EITHER.  Section 4 asks what
# a NON-ROOT session is refused; from a root shell every row in it would pass
# for the wrong reason, because `sudo sd` is exactly the session the verbs are
# meant to allow.
#
import argparse
import grp
import os
import pwd
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sdverify as V                                    # noqa: E402

NAME = "verify-accounts"
REGISTER = os.path.join(V.SDSYS, "ACCOUNTS")
GPLBP = os.path.join(HERE, os.pardir, "sdsys", "GPL.BP")
MESSAGES = os.path.join(HERE, os.pardir, "sdsys", "MESSAGES")

# SYSCOM/KEYS.H:264-301.  One-based, as the BASIC is.
ACC_PATH, ACC_DESCR, ACC_GROUP = 1, 2, 3
ACC_USERS_RETIRED = 4
ACC_TIER, ACC_PRIOR_TIER, ACC_SH, ACC_OS_EXEC = 5, 6, 7, 8

TIERS = ("STANDARD", "PROGRAMMER", "ADMINISTRATOR", "SUSPENDED")
ADMIN_GROUP = "sdadmin"
ALL_GROUP = "sdusers"

# The account verbs, their catalogued names, and the program that owns each.
VERBS = (("CREATE.ACCOUNT", "$CREATEA", "CREATEA"),
         ("DELETE.ACCOUNT", "$DELACC", "DELACC"),
         ("MODIFY.ACCOUNT", "$MODIFYA", "MODIFYA"))

# ***THE REFUSAL WORDINGS, AND THEY MUST NOT SHARE A SUBSTRING.***  2001 is the
# privilege refusal the verbs print themselves; the VOC miss is CPROC's and
# means the verb never ran at all.  A check that matched both would pass on the
# wrong one, which is the whole of the instrument rule.
MSG_PRIV = "Command requires administrator privileges"
MSG_NOVOC = "is not in your VOC"
ABSENT_VERB = "ZZNOSUCHVERB"


def fields(text):
    """A directory-file record's fields.

    ***@fm IS STORED AS "\\n" IN A DIRECTORY FILE*** - measured 12 Sep 2026 with
    od(1) on @SDSYS/ACCOUNTS/PETE, which is 8 fields in 55 bytes and carries no
    0xFE at all.  A trailing newline terminates the last field rather than
    starting an empty one."""
    if text.endswith("\n"):
        text = text[:-1]
    return text.split("\n")


def field(rec, n):
    """Field N (one-based), or '' if the record is shorter than N."""
    return rec[n - 1] if len(rec) >= n else ""


def read_register(path):
    """{ID: [fields]} for every record in the register."""
    out = {}
    for name in sorted(os.listdir(path)):
        full = os.path.join(path, name)
        if not os.path.isfile(full):
            continue
        with open(full, encoding="latin-1") as f:
            out[name] = fields(f.read())
    return out


def group_members(name):
    """The members of a Unix group, or None if there is no such group.

    ***THE PRIMARY-GROUP MEMBERS ARE INCLUDED.***  getgrnam only lists the
    SUPPLEMENTARY members, so a user whose primary group is this one is absent
    from gr_mem and a naive check calls them a non-member."""
    try:
        g = grp.getgrnam(name)
    except KeyError:
        return None
    members = set(g.gr_mem)
    for p in pwd.getpwall():
        if p.pw_gid == g.gr_gid:
            members.add(p.pw_name)
    return members


def sysmsg_ids(program):
    """Every message id the program asks for, comment lines excluded."""
    path = os.path.join(GPLBP, program)
    if not os.path.exists(path):
        return None
    with open(path, encoding="latin-1") as f:
        src = f.read()
    code = "\n".join(l for l in src.split("\n") if not l.strip().startswith("*"))
    return sorted(set(re.findall(r"sysmsg\(\s*(\d+)", code, re.IGNORECASE)))


def main():
    ap = argparse.ArgumentParser(
        description="the account register against the operating system")
    ap.add_argument("--accounts-root", default=V.ACCOUNTS,
                    help="where account directories live (default %s)" % V.ACCOUNTS)
    ap.add_argument("--register", default=REGISTER,
                    help="the ACCOUNTS register (default %s)" % REGISTER)
    ap.add_argument("--allow-stale", action="store_true",
                    help="measure an install assert-current calls stale")
    ap.add_argument("--timeout", type=int, default=60,
                    help="seconds per sd session (default 60)")
    a = ap.parse_args()

    run = V.Run(NAME)
    user = os.environ.get("USER") or "?"
    acct = os.path.join(a.accounts_root, user)

    run.say("%s: as %s (uid %d), NOT elevated" % (NAME, user, os.geteuid()))
    run.say("  sd         %s" % V.SD)
    run.say("  register   %s" % a.register)
    run.say("  accounts   %s" % a.accounts_root)
    run.say("  own acct   %s" % acct)
    run.say("")

    # ---------------------------------------------------------- 0. refusals
    run.heading("0. preconditions")
    if V.require_not_root(
            run,
            "Section 4 asks what a NON-ROOT session is refused.  From a root"
            " shell every row in it would pass for the wrong reason, because"
            " `sudo sd` is the session the account verbs are meant to allow."):
        return run.verdict()
    if V.require_paths(run, V.SD, V.SDSYS, a.register, a.accounts_root, acct,
                       GPLBP, MESSAGES):
        return run.verdict()
    if a.allow_stale:
        run.say("  *** --allow-stale: assert-current is NOT being enforced.")
        V.require_current(run)
        run.blocked = None
    elif V.require_current(run):
        return run.verdict()

    reg = read_register(a.register)
    dirs = sorted(d for d in os.listdir(a.accounts_root)
                  if os.path.isdir(os.path.join(a.accounts_root, d)))
    run.say("  register holds %d record(s): %s" % (len(reg), ", ".join(sorted(reg))))
    run.say("  %s holds %d directory(ies): %s"
            % (a.accounts_root, len(dirs), ", ".join(dirs)))

    # ***THE NULL CASE, NAMED.***  Every row below is "for each record"; an
    # empty register would record no rows at all and the harness would already
    # report FAILED, but it would not say why.
    if not reg:
        run.refuse("the register holds no records at all",
                   "Every check below is per-record, so this run would measure"
                   " nothing.  An install always registers at least SDSYS.")
        return run.verdict()

    # ------------------------------------------------- 1. the register itself
    run.heading("1. the register's own shape (SYSCOM/KEYS.H:264-301)")
    for aid in sorted(reg):
        rec = reg[aid]
        path, group = field(rec, ACC_PATH), field(rec, ACC_GROUP)
        tier = field(rec, ACC_TIER)
        run.say("      %-6s path=%-32s group=%-11s tier=%-13s sh=%s os=%s"
                % (aid, path or "(none)", group or "(none)", tier or "(none)",
                   field(rec, ACC_SH) or "-", field(rec, ACC_OS_EXEC) or "-"))

    run.note("R1 every record has an ACC$PATH", [],
             sorted(i for i in reg if not field(reg[i], ACC_PATH)))
    run.note("R2 every record has an ACC$GROUP", [],
             sorted(i for i in reg if not field(reg[i], ACC_GROUP)))
    run.note("R3 every record id is upper case", [],
             sorted(i for i in reg if i != i.upper()))
    # ***R4 ENFORCES A COMMENT.***  KEYS.H:277-278: field 4 is the retired
    # ACC$USERS and "IN THIS TREE FIELD 4 WAS NEVER WRITTEN", because a new
    # meaning there would read old data as new.
    run.note("R4 field 4 (retired ACC$USERS) is empty everywhere", [],
             sorted(i for i in reg if field(reg[i], ACC_USERS_RETIRED)))
    # SDSYS is the system account and carries no tier; every other record must.
    users = sorted(i for i in reg if os.path.normpath(field(reg[i], ACC_PATH))
                   != os.path.normpath(V.SDSYS))
    run.note("R5 the register has user accounts, not only SDSYS", True,
             len(users) > 0)
    run.note("R6 every user account's tier is one of %s" % (TIERS,), [],
             sorted(i for i in users if field(reg[i], ACC_TIER) not in TIERS))
    # A SUSPENDED account keeps the tier it displaced, and only a SUSPENDED one
    # has somewhere to keep it (queue 12).
    run.note("R7 only a SUSPENDED account carries ACC$PRIOR.TIER", [],
             sorted(i for i in users
                    if field(reg[i], ACC_PRIOR_TIER)
                    and field(reg[i], ACC_TIER) != "SUSPENDED"))

    # --------------------------------------- 2. register <-> the filesystem
    run.heading("2. the register against the filesystem, BOTH directions")
    run.say("  reconcile-accounts.sh checks the first direction only; the")
    run.say("  second is what a keep-accounts delete->install could break.")

    run.note("F1 every registered path exists", [],
             sorted(i for i in reg if not os.path.isdir(field(reg[i], ACC_PATH))))
    # ***THE DIRECTION NOTHING ELSE LOOKS.***
    registered_dirs = set(os.path.normpath(field(reg[i], ACC_PATH)) for i in reg)
    orphans = sorted(d for d in dirs
                     if os.path.normpath(os.path.join(a.accounts_root, d))
                     not in registered_dirs)
    run.note("F2 every account DIRECTORY has a register record", [], orphans)
    run.note("F3 a registered path's basename is the record id, lower cased", [],
             sorted(i for i in users
                    if os.path.basename(os.path.normpath(field(reg[i], ACC_PATH)))
                    != i.lower()))

    # ------------------------------------------------ 3. register <-> Unix
    run.heading("3. the register against the operating system")
    admins = group_members(ADMIN_GROUP)
    everyone = group_members(ALL_GROUP)
    run.note("U0 the %s and %s groups exist" % (ADMIN_GROUP, ALL_GROUP), True,
             admins is not None and everyone is not None)
    if admins is None or everyone is None:
        run.refuse("a group the register's claims are checked against is missing",
                   "%s: %s, %s: %s" % (ADMIN_GROUP, admins is not None,
                                       ALL_GROUP, everyone is not None))
        return run.verdict()

    bad_group, bad_owner, bad_sgid, not_in_all, wrong_admin = [], [], [], [], []
    for aid in users:
        rec = reg[aid]
        path = field(rec, ACC_PATH)
        gname = field(rec, ACC_GROUP)
        if not os.path.isdir(path):
            continue                       # already failed F1; do not double-count
        st = os.stat(path)
        owner = pwd.getpwuid(st.st_uid).pw_name
        actual_group = grp.getgrgid(st.st_gid).gr_name
        run.say("      %-6s dir owner=%-6s group=%-11s mode=%04o"
                % (aid, owner, actual_group, st.st_mode & 0o7777))
        if actual_group != gname:
            bad_group.append("%s: register says %s, disk says %s"
                             % (aid, gname, actual_group))
        if owner != aid.lower():
            bad_owner.append("%s: owned by %s" % (aid, owner))
        # ***THE SETGID BIT IS LOAD-BEARING, NOT COSMETIC.***  Without it a
        # record written into the account lands in the writer's own group and
        # the account's group loses access to it.
        if not st.st_mode & 0o2000:
            bad_sgid.append("%s: mode %04o has no setgid" % (aid, st.st_mode & 0o7777))
        if owner not in everyone:
            not_in_all.append("%s: %s not in %s" % (aid, owner, ALL_GROUP))
        is_admin = field(rec, ACC_TIER) == "ADMINISTRATOR"
        if is_admin != (owner in admins):
            wrong_admin.append("%s: tier %s, %s in %s = %s"
                               % (aid, field(rec, ACC_TIER) or "(none)", owner,
                                  ADMIN_GROUP, owner in admins))

    run.note("U1 the directory's group is the one the register names", [], bad_group)
    run.note("U2 the directory is owned by the account's own Unix user", [], bad_owner)
    run.note("U3 every account directory is setgid", [], bad_sgid)
    run.note("U4 every account's user is in %s" % ALL_GROUP, [], not_in_all)
    # ***U5 IS THE PAIR MODIFYA WRITES IN TWO STEPS.***
    run.note("U5 %s membership matches ACC$TIER exactly" % ADMIN_GROUP,
             [], wrong_admin)

    # ------------------------------------------- 4. the gate, measured
    run.heading("4. the account verbs refuse a session that is not root")
    run.say("  An ADMINISTRATOR account is not a privileged SESSION here:")
    run.say("  CPROC:328 grants K$ADMINISTRATOR only when system(27) = 0.")

    # ***ONE SESSION PER VERB, AND THE FIRST DRAFT OF THIS SECTION IS WHY.***
    # It ran all three in ONE session and asked, for each, whether the refusal
    # appeared ANYWHERE in the transcript - so all three rows were the same
    # check wearing three names, and a tree where only CREATE.ACCOUNT still
    # refused would have scored three passes.  Only the count row would have
    # noticed, and a count is not what the row claimed to measure.  A session
    # each costs 0.06 s and makes each row true of its own verb.
    for (verb, cat, prog) in VERBS:
        s = V.show_sd(run, verb, [verb], cwd=acct, timeout=a.timeout)
        V.session_ok(run, "G:%s session" % verb, s)
        # ANCHOR ON THE REFUSAL THE PROGRAM ITSELF PRINTS.  Matching the verb
        # name would match sd's echo of the command, which is on every path.
        run.note("G:%s refused with 2001" % verb, 1,
                 V.say_count(s.text, re.escape(MSG_PRIV)))
        # ***THIS IS WHAT STOPS THE ROW ABOVE BEING TRUE FOR THE WRONG
        # REASON.***  A verb missing from the VOC is also "refused", and a
        # check that could not tell the two apart would pass on a tree where
        # the verbs had simply been removed.
        run.note("G:%s and it RAN - not a VOC miss" % verb, 0,
                 V.say_count(s.text, re.escape(MSG_NOVOC)))

    # The control: the same session shape, a verb that really is absent.  It is
    # what makes "not a VOC miss" a discriminating claim rather than a guess
    # that the wording never appears.
    s = V.show_sd(run, "control: a verb that is in no VOC", [ABSENT_VERB],
                  cwd=acct, timeout=a.timeout)
    V.session_ok(run, "G control session", s)
    run.note("G1 the control IS a VOC miss", True,
             V.says(s.text, re.escape("%s %s" % (ABSENT_VERB, MSG_NOVOC))))
    run.note("G2 and it is NOT refused for privilege", 0,
             V.say_count(s.text, re.escape(MSG_PRIV)))

    # ---------------------------------------- 5. the messages they will print
    run.heading("5. every message the account verbs ask for resolves")
    run.say("  A sysmsg() with no file prints NOTHING, so a missing id is a")
    run.say("  verb that refuses or confirms in silence.")
    have = set(os.listdir(MESSAGES))
    run.note("M0 the MESSAGES directory was readable", True, len(have) > 0)
    for (verb, cat, prog) in VERBS:
        ids = sysmsg_ids(prog)
        if ids is None:
            run.note("M:%s the program exists" % prog, True, False)
            continue
        missing = [i for i in ids if i not in have]
        run.say("      %-8s %3d id(s) asked for" % (prog, len(ids)))
        run.note("M:%s every id it asks for exists" % prog, [], missing)
        # A program that asks for no messages is not being checked at all.
        run.note("M:%s asks for messages (not the null case)" % prog, True,
                 len(ids) > 0)

    return run.verdict()


if __name__ == "__main__":
    sys.exit(main())
