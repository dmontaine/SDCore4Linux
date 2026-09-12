#!/usr/bin/env python3
#
# verify-sysperms.py - can an ordinary SD user write into the system tree, read
#                      the audit trail, or reach SDSYS?  PORT_ADOPTION queue 22,
#                      ranked item 7: the port's ACL family (verify-sysdiracl,
#                      verify-pcodeacl, verify-sdsysgate, verify-sdsyswrite,
#                      verify-accountacl, verify-catgate) re-expressed as Linux
#                      mode, ownership and group.
#
#   python3 /home/don/Projects/sdcore4linux/sdb_ai/sd64/gplbld/verify-sysperms.py
#   python3 .../verify-sysperms.py --allow-stale      measure a stale install
#
# NO SUDO, AND NOT AS A CONVENIENCE.  Exit 0 every decisive check passed, 1 a
# decisive check failed, 2 the test could not be run.
#
# ***THE DECISIVE CHECK IS THE WRITE, NOT THE MODE BITS.***  That is the port's
# rule (verify-sysdiracl: "an ACL can be read wrong ... an icacls that has
# itself been DENIED prints nothing and reads as (none), which scored a false
# clean on 24 Aug 2026") and it transfers intact: mode 0755 does not settle
# what a caller may do, because supplementary groups, a POSIX ACL set with
# setfacl, the setgid bit and an immutable attribute all change the answer
# without changing the four digits.  So every row below ASKS THE FILESYSTEM the
# question an attacker would ask, and the owner/group/mode is printed beside it
# as DIAGNOSIS ONLY.
#
# ***WHO RUNS IT DECIDES WHAT A REFUSAL MEANS, SO IT REFUSES TWO CALLERS.***
#   * root - every write would succeed and every row would pass for the wrong
#     reason.  This is the whole of why the port's equivalents refuse
#     elevation.
#   * anyone not in `sdusers` - their refusals come from the "other" bits,
#     which is a WEAKER claim wearing the same word.  The question is what a
#     member of the SD user group can do, so measuring a non-member would
#     overstate the protection.  Section 0 prints the caller's full group list
#     because that, not the mode, is the other half of every answer here.
#
# ***THE WRITABLE CONTROL IS NOT OPTIONAL, AND ITS REASON IS MEASURED RATHER
# THAN INHERITED.***  Without a row that must come back WRITABLE this file
# passes in two opposite worlds: one where the tree is correctly locked, and
# one where something locked EVERYTHING and every session is broken.  The port
# uses $ipc and says why - every session modifies $ipc/%0.  Row W2 does not
# take that on trust: it stats $IPC/%0, runs a session, and stats it again.
# Measured 12 Sep 2026 on this install, the mtime advanced.
#
# ***AND THE READ-ONLY SET IS DERIVED, NOT LISTED.***  Everything in the system
# directory must refuse a write EXCEPT the names in EXPECT_WRITABLE below, each
# of which carries a reason and a citation.  A directory that arrives
# group-writable in some future install turns this red without anybody having
# remembered to add it - the same shape as verify-basicfuncs's coverage row,
# and for the same reason: a list somebody must maintain is a list that goes
# stale in silence.
#
import argparse
import grp
import os
import pwd
import re
import stat
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sdverify as V                                    # noqa: E402

NAME = "verify-sysperms"
CONF = "/etc/sd.conf"
SD_GROUP = "sdusers"
ADMIN_GROUP = "sdadmin"
PROBE = ".zzsysperms-probe"

# Read but never written by an ordinary session, and the mode says write-only
# for the group (0620), so an ordinary user must NOT be able to read it.
AUDIT = "audit"

# ***THE EXCEPTIONS, EACH WITH A REASON AND A CITATION.***  "required" means the
# run FAILS if it is not writable - that is the control.  The others are merely
# permitted: they are group-writable on purpose and must not turn the run red.
EXPECT_WRITABLE = {
    "$IPC": (True,
             "every session writes $IPC/%0 - row W2 measures that rather than "
             "asserting it; the port's sd.c:55 hands a phantom its command here"),
    "prt": (False,
            "the print spool: gplsrc/to_file.c:169 writes <sysdir>/prt/p<n>; "
            "installsdai.sh:621 sets it 775"),
    "errlog": (False,
               "sessions append errors to it; installsdai.sh:620 sets it 775"),
    # ***THE SWEEP IN SECTION 1 FOUND THIS ONE AND THAT IS THE SWEEP WORKING.***
    # The first run flagged `audit` as an unexpected writable.  It is writable
    # on purpose: 0620 is sdsys:sdusers with the GROUP holding write and NOT
    # read, and a session runs as the Unix user rather than as sdsys, so group
    # write is exactly how an audit record gets appended at all.  Required,
    # therefore: if it stops being group-writable the trail stops recording and
    # nothing else would say so.  The invariant that matters for this file -
    # that the group cannot READ it - is section 6.
    AUDIT: (True,
                 "queue 13's trail: 0620 sdsys:sdusers, group write and NOT "
                 "read.  Sessions run as the Unix user, so group write is how "
                 "a record is appended; section 6 checks it cannot be read"),
}

# gplsrc/sysseg.c builds and opens <sysdir>/bin/pcode; a writable pcode is
# arbitrary code reaching every session that starts afterwards.  This is the
# port's verify-pcodeacl, and the file list is this tree's bin.
BIN_FILES = ("pcode", "sd", "libsdcli.so")

MSG_SDSYS_GATE = "SDSYS Account access is restricted to privileged users"
# Message 2001, printed by the verb itself once it has started - so seeing it
# means the verb RAN and refused, not that it was missing.
MSG_PRIV = "Command requires administrator privileges"


def describe(path):
    """owner:group and mode, for the transcript.  DIAGNOSIS, NOT THE CHECK."""
    try:
        st = os.lstat(path)
    except OSError as e:
        return "(cannot stat: %s)" % e
    try:
        owner = pwd.getpwuid(st.st_uid).pw_name
    except KeyError:
        owner = str(st.st_uid)
    try:
        group = grp.getgrgid(st.st_gid).gr_name
    except KeyError:
        group = str(st.st_gid)
    return "%s:%s %04o" % (owner, group, stat.S_IMODE(st.st_mode))


def dir_writable(path):
    """Can THIS caller create a file here?  Returns (bool, detail).

    It creates a probe and removes it again.  Asking os.access() instead would
    be asking about the mode, which is the thing this file refuses to treat as
    the answer."""
    probe = os.path.join(path, PROBE)
    try:
        fd = os.open(probe, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except OSError as e:
        return False, "%s" % e.strerror
    os.close(fd)
    try:
        os.unlink(probe)
        return True, "created and removed %s" % PROBE
    except OSError as e:
        # Writable but not removable is still writable, and the leftover has to
        # be said out loud rather than tidied away in silence.
        return True, "created %s but COULD NOT REMOVE IT (%s)" % (probe, e.strerror)


def file_writable(path):
    """Can THIS caller open the file for writing?  Returns (bool, detail).

    ***APPEND MODE, AND NOTHING IS WRITTEN.***  Opening "ab" proves the
    permission without changing a byte, without truncating, and without even
    moving the mtime - which matters when the files under test are the
    interpreter and the pcode library."""
    try:
        f = open(path, "ab")
    except OSError as e:
        return False, "%s" % e.strerror
    f.close()
    return True, "opened for append (nothing written)"


def file_readable(path):
    try:
        with open(path, "rb") as f:
            f.read(1)
        return True, "read 1 byte"
    except OSError as e:
        return False, "%s" % e.strerror


def my_groups():
    names = set()
    for g in os.getgroups():
        try:
            names.add(grp.getgrgid(g).gr_name)
        except KeyError:
            names.add(str(g))
    try:
        names.add(grp.getgrgid(os.getgid()).gr_name)
    except KeyError:
        pass
    return names


def main():
    ap = argparse.ArgumentParser(
        description="what an ordinary SD user can do to the system tree")
    ap.add_argument("--sdsys", default=V.SDSYS,
                    help="the system directory (default %s)" % V.SDSYS)
    ap.add_argument("--conf", default=CONF,
                    help="the configuration file (default %s)" % CONF)
    ap.add_argument("--allow-stale", action="store_true",
                    help="measure an install assert-current calls stale")
    ap.add_argument("--timeout", type=int, default=60,
                    help="seconds per sd session (default 60)")
    a = ap.parse_args()

    run = V.Run(NAME)
    user = os.environ.get("USER") or "?"
    acct = os.path.join(V.ACCOUNTS, user)
    groups = my_groups()

    run.say("%s: as %s (uid %d), NOT elevated" % (NAME, user, os.geteuid()))
    run.say("  sd        %s" % V.SD)
    run.say("  sdsys     %s" % a.sdsys)
    run.say("  conf      %s" % a.conf)
    run.say("  account   %s" % acct)
    # ***THE GROUP LIST IS AN INPUT, NOT DECORATION.***  Every "refused" below
    # is a statement about THIS subject; a reader who cannot see the subject
    # cannot check the claim.
    run.say("  groups    %s" % ", ".join(sorted(groups)))
    run.say("")

    # ---------------------------------------------------------- 0. refusals
    run.heading("0. preconditions - who is asking decides what a refusal means")
    if V.require_not_root(
            run,
            "Every write below would SUCCEED as root, so every row would pass"
            " for the wrong reason.  This measures what an ordinary SD user"
            " can do."):
        return run.verdict()
    if V.require_paths(run, V.SD, a.sdsys, a.conf, acct):
        return run.verdict()
    # A caller outside sdusers is refused by the "other" bits, which is a
    # weaker claim wearing the same word.
    if SD_GROUP not in groups:
        run.refuse("the caller is not in %s" % SD_GROUP,
                   "Every refusal below would come from the 'other' bits"
                   " rather than from the group policy, which would OVERSTATE"
                   " the protection this measures.",
                   "Run it as a user with an SD account.")
        return run.verdict()
    run.say("  caller IS in %s, so a refusal below is the group policy"
            " refusing, not the 'other' bits." % SD_GROUP)
    if ADMIN_GROUP in groups:
        run.say("  caller is ALSO in %s - which makes the SDSYS gate in"
                " section 5 a STRONGER result, not a weaker one." % ADMIN_GROUP)
    if a.allow_stale:
        run.say("  *** --allow-stale: assert-current is NOT being enforced.")
        V.require_current(run)
        run.blocked = None
    elif V.require_current(run):
        return run.verdict()

    try:
        entries = sorted(os.listdir(a.sdsys))
    except OSError as e:
        run.refuse("cannot list %s (%s)" % (a.sdsys, e))
        return run.verdict()
    run.note("S0 the system directory has contents to measure", True,
             len(entries) > 0)

    # ------------------------------------------- 1. the derived read-only set
    run.heading("1. everything in the system tree refuses a write, except the"
                " named exceptions")
    run.say("  %d entr(ies) in %s; %d are expected writable and are checked in"
            " section 2." % (len(entries), a.sdsys, len(EXPECT_WRITABLE)))
    run.say("  The write is the check.  owner:group mode is diagnosis.")

    leaked = []
    for name in entries:
        if name in EXPECT_WRITABLE:
            continue
        path = os.path.join(a.sdsys, name)
        if os.path.isdir(path):
            ok, detail = dir_writable(path)
        elif os.path.isfile(path):
            ok, detail = file_writable(path)
        else:
            continue
        run.say("      %-16s %-24s %s" % (name, describe(path),
                                          "WRITABLE - " + detail if ok
                                          else "refused (" + detail + ")"))
        if ok:
            leaked.append(name)
    # ***ONE ROW, NAMING EVERY LEAK.***  A row per entry would bury the answer
    # in forty passes; the failure has to carry the names, so it does.
    run.note("S1 nothing outside the expected set is writable", [], leaked)

    # --------------------------------------------- 2. the writable control(s)
    run.heading("2. the writable exceptions - the control this file needs")
    run.say("  Without a row that must come back WRITABLE, section 1 passes")
    run.say("  both when the tree is correctly locked AND when something has")
    run.say("  locked everything and every session is broken.")
    for name, (required, why) in sorted(EXPECT_WRITABLE.items()):
        path = os.path.join(a.sdsys, name)
        if not os.path.exists(path):
            run.note("W:%s exists" % name, True, False)
            continue
        if os.path.isdir(path):
            ok, detail = dir_writable(path)
        else:
            ok, detail = file_writable(path)
        run.say("      %-10s %-24s %s" % (name, describe(path), detail))
        run.say("           why: %s" % why)
        if required:
            # Named per entry, not "W1" for all of them: two required controls
            # sharing one row name means a failure cannot be told from the
            # other's pass, and a name is how a failure gets found.
            run.note("W1:%s IS writable (a required control)" % name, True, ok)
        else:
            run.note("W:%s writable as expected" % name, True, ok,
                     decisive=False)

    # ***W2: THE CONTROL'S REASON, MEASURED.***  "$IPC must stay writable
    # because sessions write it" is the port's claim; this checks it here.
    ipc0 = os.path.join(a.sdsys, "$IPC", "%0")
    if os.path.exists(ipc0):
        try:
            before = os.stat(ipc0).st_mtime
        except OSError:
            before = None
        V.show_sd(run, "a session, to see whether it touches $IPC/%0",
                  ["WHO"], cwd=acct, timeout=a.timeout)
        try:
            after = os.stat(ipc0).st_mtime
        except OSError:
            after = None
        run.say("      $IPC/%%0 mtime before %s, after %s" % (before, after))
        run.note("W2 a session really does write $IPC/%0", True,
                 before is not None and after is not None and after > before)
    else:
        run.note("W2 $IPC/%0 exists to measure", True, False)

    # ------------------------------------------------- 3. the pcode library
    run.heading("3. the interpreter and the pcode library (the port's pcodeacl)")
    run.say("  gplsrc/sysseg.c builds and opens <sysdir>/bin/pcode.  A writable")
    run.say("  pcode is arbitrary code reaching every session started after it.")
    hot = []
    for f in BIN_FILES:
        path = os.path.join(a.sdsys, "bin", f)
        if not os.path.exists(path):
            run.note("B:%s exists" % f, True, False)
            continue
        ok, detail = file_writable(path)
        run.say("      bin/%-14s %-24s %s" % (f, describe(path), detail))
        if ok:
            hot.append(f)
    run.note("B1 no file in bin is writable by an ordinary SD user", [], hot)

    # ------------------------------------------------------ 4. sd.conf
    run.heading("4. the configuration file")
    ok, detail = file_writable(a.conf)
    run.say("      %-20s %-24s %s" % (a.conf, describe(a.conf), detail))
    run.note("C1 sd.conf is not writable by an ordinary SD user", False, ok)

    # ------------------------------------------------- 5. the SDSYS gate
    run.heading("5. SDSYS refuses an ordinary session (the port's sdsysgate)")
    run.say("  CPROC:328 grants K$ADMINISTRATOR only when system(27) = 0 (real")
    run.say("  uid 0), so there is no such thing as a plain-sd administrator")
    run.say("  session here.  Message 10002, LOGIN:322 and CPROC:2752.")
    s = V.show_sd(run, "LOGTO SDSYS, then WHO", ["LOGTO SDSYS", "WHO"],
                  cwd=acct, timeout=a.timeout)
    V.session_ok(run, "G session", s)
    run.note("G1 SDSYS refused, in message 10002's words", True,
             V.says(s.text, re.escape(MSG_SDSYS_GATE)))
    # ***G2 IS THE ROW THAT MATTERS.***  A printed refusal is not proof the
    # refusal HELD; WHO says which account the session is actually in, and if
    # LOGTO had succeeded despite the message this is what would show it.
    run.note("G2 and the session stayed in %s - the refusal HELD" % user.upper(),
             True, V.says(s.text, r"^\s*\d+\s+%s\s*$" % re.escape(user.upper())))
    run.note("G3 it never reported being in SDSYS", False,
             V.says(s.text, r"^\s*\d+\s+SDSYS\s*$"))

    # ------------------------------------------------- 6. the audit trail
    run.heading("6. the audit trail is write-only to the group (queue 13)")
    run.say("  Mode 0620 sdsys:sdusers: the group may append, and must NOT")
    run.say("  read.  An ordinary user being able to read it would expose")
    run.say("  every sign-on, LOGTO and privilege change on the system.")
    audit = os.path.join(a.sdsys, AUDIT)
    if os.path.exists(audit):
        run.say("      %-10s %s" % (AUDIT, describe(audit)))
        ok, detail = file_readable(audit)
        run.say("      read attempt: %s" % detail)
        run.note("A1 an ordinary SD user cannot READ the audit trail", False, ok)
        # ***AND THE LIMIT IS STATED RATHER THAN PAPERED OVER.***  The append
        # side is deliberately NOT exercised: 0620 lets the group append by
        # design (a known limit, recorded in queue 13 and the port's), and
        # writing a line of this file's own into a live audit trail to prove it
        # would corrupt the evidence the trail exists to hold.  chattr +a
        # cannot be read either - lsattr is refused to a non-owner.
        run.say("      NOT exercised: the append side.  0620 permits it by")
        run.say("      design (queue 13's known limit), and writing into a live")
        run.say("      audit trail to prove it would corrupt the evidence.")
    else:
        run.note("A1 the audit trail exists to measure", True, False)

    # ------------------------------------------- 7. the global catalogue gate
    run.heading("7. the GLOBAL catalogue needs administrator rights (catgate)")
    run.say("  The port's verify-catgate: reaching the global catalogue must")
    run.say("  require administrator rights by every route.  On this tree the")
    run.say("  gate answers 2001 before CATALOG does anything at all.")
    # ***TWO SESSIONS, NOT ONE, AND verify-accounts PAID FOR THAT LESSON.***
    # Run together, "did 2001 appear?" and "did 2001 NOT appear?" are asked of
    # the same transcript and the second can never be true.
    s = V.show_sd(run, "CATALOG ... GLOBAL", ["CATALOG BP ZZNOPROG GLOBAL"],
                  cwd=acct, timeout=a.timeout)
    V.session_ok(run, "K:GLOBAL session", s)
    run.note("K1 GLOBAL is refused for privilege", 1,
             V.say_count(s.text, re.escape(MSG_PRIV)))

    # ***THE CONTROL, AND IT IS WHAT MAKES K1 A CLAIM ABOUT "GLOBAL".***
    # Without it K1 passes on a tree where CATALOG refuses everybody, or where
    # the program name is what is being rejected.  LOCAL takes the same verb
    # and the same absent program and must fail for a DIFFERENT, ordinary
    # reason.
    s = V.show_sd(run, "CATALOG ... LOCAL (the control)",
                  ["CATALOG BP ZZNOPROG LOCAL"], cwd=acct, timeout=a.timeout)
    V.session_ok(run, "K:LOCAL session", s)
    run.note("K2 LOCAL is NOT refused for privilege", 0,
             V.say_count(s.text, re.escape(MSG_PRIV)))
    run.note("K3 and it failed for its own ordinary reason instead", True,
             V.says(s.text, re.escape("File BP.OUT not found")))
    # Neither attempt may leave anything behind in the caller's account.
    run.note("K4 no BP.OUT was created by either attempt", False,
             os.path.exists(os.path.join(acct, "BP.OUT")))

    return run.verdict()


if __name__ == "__main__":
    sys.exit(main())
