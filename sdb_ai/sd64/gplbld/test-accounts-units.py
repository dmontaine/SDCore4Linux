#!/usr/bin/env python3
#
# test-accounts-units.py - the pure logic verify-accounts.py grew of its own.
#                          PORT_ADOPTION queue 22, ranked item 6.
#
#   python3 /home/don/Projects/sdcore4linux/sdb_ai/sd64/gplbld/test-accounts-units.py
#
# No sudo, no install, no sd.  Exit 0 all cases passed, 1 a case failed.
#
# ***TWO FUNCTIONS HERE HAVE A TRAP IN THEM AND BOTH TRAPS ARE SILENT.***
#
#   fields() - a directory-file record's fields are separated by "\n" and the
#   last one is TERMINATED by one.  Splitting without dropping that terminator
#   invents a trailing empty field, so a 5-field record reads as 6 and
#   `len(rec) >= n` starts answering yes for a field that is not there.  Nothing
#   about that is visible in a transcript: the rows just quietly compare '' to
#   ''.  Cases 1-7.
#
#   group_members() - grp.getgrnam only lists the SUPPLEMENTARY members of a
#   group.  A user whose PRIMARY group is the one being asked about is absent
#   from gr_mem, so a naive membership test calls a real member a non-member -
#   and here that would fail U4/U5 against a perfectly correct system, or, in
#   the direction that matters, pass a row asserting somebody is NOT a member
#   when they are.  Cases 8-11 use the real /etc/group, because a synthetic one
#   cannot reproduce the primary-group half.
#
import os
import sys
import grp
import pwd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import importlib.util                                    # noqa: E402
_spec = importlib.util.spec_from_file_location(
    "verify_accounts", os.path.join(HERE, "verify-accounts.py"))
VA = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(VA)

FAILS = []
CASES = [0]


def ck(name, got, want):
    CASES[0] += 1
    if got != want:
        FAILS.append("%s:\n      got  %r\n      want %r" % (name, got, want))
        print("  FAIL %s" % name)
    else:
        print("  pass %s" % name)


def main():
    print("--- fields(): the terminator is not a field ---")

    # The real bytes of @SDSYS/ACCOUNTS/PETE, measured with od(1) 12 Sep 2026:
    # 8 fields in 55 bytes, "\n" throughout, no 0xFE anywhere.
    PETE = ("/home/sd/user_accounts/pete\n\nsdu_pete\n\nSTANDARD\n\nno\nno\n")
    f = VA.fields(PETE)
    ck("1 the real PETE record is 8 fields, not 9", len(f), 8)
    ck("2 ACC$PATH", VA.field(f, VA.ACC_PATH), "/home/sd/user_accounts/pete")
    ck("3 ACC$GROUP", VA.field(f, VA.ACC_GROUP), "sdu_pete")
    ck("4 ACC$TIER", VA.field(f, VA.ACC_TIER), "STANDARD")
    ck("5 ACC$SH and ACC$OS.EXEC",
       (VA.field(f, VA.ACC_SH), VA.field(f, VA.ACC_OS_EXEC)), ("no", "no"))

    # TPROG really does stop at field 5 - it has no SH/OS.EXEC at all - so
    # asking past the end must give '' and not raise.
    TPROG = "/home/sd/user_accounts/tprog\n\nsdu_tprog\n\nPROGRAMMER\n"
    f = VA.fields(TPROG)
    ck("6 a short record is 5 fields", len(f), 5)
    ck("7 a field past the end reads '' rather than raising",
       VA.field(f, VA.ACC_OS_EXEC), "")

    # A record with no terminator at all must read the same way: the byte is a
    # terminator, not a separator, so its absence changes nothing.
    ck("7b an unterminated record parses identically",
       VA.fields("a\nb"), VA.fields("a\nb\n"))

    print("--- group_members(): the primary group is a membership too ---")

    ck("8 a group that does not exist returns None",
       VA.group_members("zznosuchgroup"), None)

    # ***THE REAL SYSTEM, BECAUSE A SYNTHETIC GROUP CANNOT SHOW THIS.***  Every
    # user's own primary group is normally a group of the same name whose
    # gr_mem is EMPTY; getgrnam alone would report nobody in it.
    me = pwd.getpwuid(os.getuid())
    primary = grp.getgrgid(me.pw_gid).gr_name
    members = VA.group_members(primary)
    ck("9 the caller is in their own primary group (%s)" % primary,
       me.pw_name in members, True)
    # ***THE FIRST DRAFT OF ROW 10 COMPARED A VALUE WITH ITSELF*** - `ck(name,
    # X, X)` - so it could not fail whatever the function did.  The real
    # invariant is that group_members() is a SUPERSET of getgrnam's gr_mem: it
    # adds the primary-group members and takes nothing away.  Whether the
    # caller happens to be listed in gr_mem as WELL as by gid is a property of
    # the machine, not of this function, so it is printed rather than asserted.
    gr_mem = set(grp.getgrnam(primary).gr_mem)
    print("      getgrnam(%s).gr_mem = %r  (the caller is %sin it)"
          % (primary, sorted(gr_mem), "" if me.pw_name in gr_mem else "NOT "))
    ck("10 group_members() never drops a supplementary member",
       gr_mem <= members, True)

    # And on a group with real supplementary members, every one is still found.
    sup_mem = set(grp.getgrnam("sdusers").gr_mem)
    sup = VA.group_members("sdusers")
    ck("11 sdusers has supplementary members to check against",
       len(sup_mem) > 0, True)
    ck("11b every one of them is found", sup_mem <= (sup or set()), True)

    print("--- sysmsg_ids(): comments are not calls ---")

    ck("12 a program that does not exist returns None",
       VA.sysmsg_ids("ZZNOSUCHPROGRAM"), None)

    real = VA.sysmsg_ids("DELACC")
    ck("13 DELACC asks for messages", real is not None and len(real) > 0, True)
    ck("14 ... and every one of them is a bare number",
       all(i.isdigit() for i in (real or [])), True)
    # DELACC's header names 10084 and 10085 in PROSE as well as calling them;
    # a scan that read comments would find ids no code path ever prints.
    ck("15 the ids are sorted and unique", real, sorted(set(real or [])))

    print("")
    print("test-accounts-units: %d cases, %d failed" % (CASES[0], len(FAILS)))
    for f in FAILS:
        print("  FAIL %s" % f)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
