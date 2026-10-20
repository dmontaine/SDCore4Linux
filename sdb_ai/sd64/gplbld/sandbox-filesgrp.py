#!/usr/bin/env python3
#
# sandbox-filesgrp.py - MODIFY.ACCOUNT files-on / files-off / files-write-on / files-write-off, the program itself, run against a SCRATCH group file and a stand-in for the
#                       privileged helper (S.65 follow-up K4a, 19 Oct 26).  No install, no sudo.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/sandbox-filesgrp.py <dir> [--build] [--mutant=NAME]
#
# <dir> is a sandbox made by sandbox-fromtree.py.  With --build it is built first from THIS tree (it must be empty or absent).  Exit 0 every row passed, 1 a row failed, 2 it could
# not run.  With --mutant=NAME exit 0 means the mutant was killed by exactly the rows listed for it (MUTANTS below).
#
# START-HISTORY:
# 19 Oct 26 dm  Finish 2 (verifier findings).  (1) A failure of the SECOND removal after the write group had gone printed only the 10081 line and wrote no audit line (C4, C10b, and the new
#               C11b for files-on); the audit trail is now read in every case (want_audit / deny_audit).  (2) The header said "No install" and the real sd-elevate's dry run asks
#               `getent group <g>` for addgroup and delgroup, so a machine without the groups sdfiles and sdfileswrite made the cases fail for the wrong reason; the shim now gives that dry run a
#               getent of this suite first on its PATH, answered from the scratch group file (row S1 shows it both ways).
# 19 Oct 26 dm  Written.  The write group (18 Oct) removed the person from sdfileswrite on files-off, but only AFTER a real removal from sdfiles, so (1) a person who was in
#               sdfileswrite and NOT in sdfiles got "already had that access" and kept the membership, (2) a failure of the second removal left exactly that orphan, and (3) a later
#               files-on added sdfiles and never looked at sdfileswrite, so the orphan became write access that the administrator had not given.  test-fileswrite-units.py reads the
#               program as text; this suite RUNS the real modifya.  Real group changes need root (set.files calls `sudo /usr/local/sbin/sd-elevate` and reads /etc/group), so
#               the SANDBOX'S OWN COPY of modifya is patched in two ways, and nothing else: the helper is a script of this suite that runs the REAL sd-elevate with --dry-run
#               first (every argument rule is the real one) and then edits a scratch group file, and the two group lookups read that file.  What a sandbox cannot show -
#               that the real helper, the sudoers line and /etc/group do the same - is the VM witness (gplbld/witness-sdnet-writegroup.sh).
# END-HISTORY
#
# THE INSTRUMENT.  Every case prints its real inputs: the scratch group file before, the command, the failures injected into the helper, the helper's calls in order, the output
# and the group file after.  The person is whoever runs this (DON IS TRANSITORY: the name is never typed here), because the real helper's dry run only accepts a user that exists.
# The expected values are written in CASES from the rule, never from what the program printed.  NULL CASES REFUSED OUT LOUD: the control case C0 must see the SCRATCH file (its
# answer differs from what /etc/group would give, which the suite checks first), a case that expects helper calls and sees none fails, and the helper counts its calls.
#
#   C0  control: in sdfiles only, files-off: sdfiles is removed (the scratch file is what modifya reads)
#   C1  THE ORPHAN: in sdfileswrite and not in sdfiles, files-off: it is removed (it used to answer "already had that access")
#   C2  in both, files-off: the write group goes FIRST, then sdfiles
#   C3  in both, the removal from sdfileswrite fails: nothing changed, sdfiles is not touched (it used to remove sdfiles first and leave the orphan)
#   C4  in both, the removal from sdfiles fails after the write group went: the person is left in sdfiles alone, read access, never write without read
#   C5  a stray sdfileswrite and files-on: the write group is removed BEFORE sdfiles is added (it used to be added with the write access already in place)
#   C6  control: in neither, files-on: sdfiles is added, nothing else
#   C7  control: in both, files-on: "already had that access", nothing called, the write group stays (it was given on purpose)
#   C8  control: in neither, files-off: "already had that access", nothing called
#   C9  the write words: files-write-on needs sdfiles (11523), then adds only the write group; files-write-off removes only it
#   C10 the helper says yes and changes nothing: the read back catches it (10081), at the step it happened
#   C11 files-on with a stray write group that cannot be removed: sdfiles is NOT added

import getpass
import importlib.util
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TREE = os.path.dirname(HERE)
spec = importlib.util.spec_from_file_location("q3", os.path.join(HERE, "sandbox-stmt-q3.py"))
q3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q3)
say, has, put = q3.say, q3.has, q3.put

FAILED_IDS = []
ME = getpass.getuser()
ACCT = "zzgrp"


def row(name, ok, detail=""):
    q3.row(name, ok, detail)
    if not ok:
        FAILED_IDS.append(name.split()[0])


def msg(n, *args):
    """The text of message N as this sandbox was built with it, the arguments put in."""
    with open(os.path.join(q3.SYS, "messages", str(n)), encoding="utf-8", errors="replace") as f:
        t = f.read().strip("\n")
    for i, a in enumerate(args, 1):
        t = t.replace("%%%d" % i, str(a))
    return t


SHIM = r'''#!/usr/bin/env python3
# the stand-in for `sudo /usr/local/sbin/sd-elevate` in the sandbox's copy of modifya (sandbox-filesgrp.py): the REAL sd-elevate with --dry-run first, then an edit of the scratch group file
import json, os, subprocess, sys
BOX = %(box)r
args = sys.argv[1:]
with open(os.path.join(BOX, "grp", "calls.log"), "a") as f:
    f.write(" ".join(args) + "\n")
# the real sd-elevate asks `getent group <g>` for addgroup and delgroup even in a dry run, so it needs the Linux groups sdfiles and sdfileswrite that only an install makes; the dry run
# is given a getent of this suite's first on its PATH, which answers `getent group` from the SCRATCH group file (and sends every other getent to the real one)
env = dict(os.environ, PATH=os.path.join(BOX, "grp", "fakebin") + os.pathsep + os.environ.get("PATH", ""))
rc = subprocess.run(["bash", %(elevate)r, "--dry-run"] + args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env).returncode
if rc != 0:
    sys.exit(2)
if len(args) != 3 or args[0] not in ("addgroup", "delgroup"):
    sys.exit(3)
verb, user, group = args
inj_path = os.path.join(BOX, "grp", "inject.json")
inject = json.load(open(inj_path)) if os.path.exists(inj_path) else {}
modes = inject.get(verb + " " + group, [])
mode = modes.pop(0) if modes else "ok"
json.dump(inject, open(inj_path, "w"))
if mode == "fail":
    sys.stderr.write("shim: injected failure\n")
    sys.exit(1)
if mode == "noop":
    sys.exit(0)
path = os.path.join(BOX, "grp", "group")
lines = open(path).read().split("\n")
out, done = [], False
for ln in lines:
    p = ln.split(":")
    if len(p) == 4 and p[0] == group:
        mem = [m for m in p[3].split(",") if m]
        if verb == "addgroup" and user not in mem:
            mem.append(user)
        if verb == "delgroup":
            mem = [m for m in mem if m != user]
        p[3] = ",".join(mem)
        ln = ":".join(p)
        done = True
    out.append(ln)
if not done:
    sys.exit(4)
open(path + ".new", "w").write("\n".join(out))
os.replace(path + ".new", path)
sys.exit(0)
'''


GETENT = r'''#!/usr/bin/env python3
# a stand-in for getent on the PATH of the real sd-elevate's dry run (sandbox-filesgrp.py): `getent group NAME` is answered from the SCRATCH group file, anything else by the real getent
import os, sys
BOX = %(box)r
a = sys.argv[1:]
if len(a) == 2 and a[0] == "group":
    try:
        lines = open(os.path.join(BOX, "grp", "group")).read().split("\n")
    except OSError:
        sys.exit(2)
    for ln in lines:
        p = ln.split(":")
        if len(p) == 4 and p[0] == a[1]:
            print(ln)
            sys.exit(0)
    sys.exit(2)
real = next((c for c in ("/usr/bin/getent", "/bin/getent") if os.path.exists(c)), None)
if real is None:
    sys.exit(2)
os.execv(real, [real] + a)
'''


def audit_off():
    """Size of the sandbox's audit file.  SD APPENDS to <sys>/audit and never creates it, so without one every audit line is dropped: it is made, empty, when it is missing.  None when it cannot be."""
    path = os.path.join(q3.SYS, "audit")
    try:
        if not os.path.exists(path):
            with open(path, "ab"):
                pass
        return os.path.getsize(path)
    except OSError:
        return None


def audit_new(off):
    """What the audit trail gained since OFF; None when it cannot be read (a row that needs it then FAILS, it does not pass for want of a line to look at)."""
    if off is None:
        return None
    try:
        with open(os.path.join(q3.SYS, "audit"), "rb") as f:
            f.seek(off)
            return f.read().decode("utf-8", errors="replace")
    except OSError:
        return None


def grp_line(name, gid, members):
    return "%s:x:%d:%s" % (name, gid, ",".join(members))


def write_group(sf, sw, extra_sdusers=True):
    """The scratch group file: SF the members of sdfiles, SW the members of sdfileswrite, ME in sdusers."""
    lines = ["root:x:0:", grp_line("sdusers", 2000, [ME]), grp_line("sdfiles", 2001, sf), grp_line("sdfileswrite", 2002, sw), grp_line("wheel", 10, [])]
    put(os.path.join(q3.BOX, "grp", "group"), "\n".join(lines))


def read_group():
    """{group: [members]} from the scratch file."""
    out = {}
    with open(os.path.join(q3.BOX, "grp", "group")) as f:
        for ln in f.read().split("\n"):
            p = ln.split(":")
            if len(p) == 4:
                out[p[0]] = [m for m in p[3].split(",") if m]
    return out


def read_calls():
    path = os.path.join(q3.BOX, "grp", "calls.log")
    try:
        with open(path) as f:
            return [ln for ln in f.read().split("\n") if ln]
    except OSError:
        return []


def run_case(cid, label, sf, sw, command, inject, want_groups, want_calls, want_lines, deny_lines=(), want_fail=False, want_audit=(), deny_audit=(), audit_checked=False):
    """One case.  sf / sw: ME in sdfiles / sdfileswrite before; inject: {"delgroup sdfileswrite": ["fail"]}; want_groups: (ME in sdfiles, ME in sdfileswrite) after;
    want_calls: [(verb, group)] in order; want_lines: whole lines that must be in the output; deny_lines: whole lines that must not; want_fail: the 10081 line is expected.
    want_audit / deny_audit: regular expressions (multi-line, `$` = end of a line) that must / must not match what the audit trail gained during the command; audit_checked makes the audit
    row appear even when both lists are empty (a case that must leave NO `modify.account` line says so with deny_audit)."""
    write_group([ME] if sf else [], [ME] if sw else [])
    put(os.path.join(q3.BOX, "grp", "calls.log"), "")
    put(os.path.join(q3.BOX, "grp", "inject.json"), json.dumps(inject))
    before = read_group()
    say("\n  %s %s" % (cid, label))
    say("    [inputs] scratch group file before: sdfiles=%r sdfileswrite=%r sdusers=%r; command %r; injected into the helper: %r" % (before["sdfiles"], before["sdfileswrite"], before["sdusers"], command, inject))
    off = audit_off()
    out = q3.adm([command])
    new = audit_new(off)
    after = read_group()
    calls = read_calls()
    say("    [outputs] helper calls: %r; group file after: sdfiles=%r sdfileswrite=%r; output tail: %r" % (calls, after["sdfiles"], after["sdfileswrite"], out[-4:]))
    say("    [audit] gained during the command: %r" % (new,))
    got = (ME in after["sdfiles"], ME in after["sdfileswrite"])
    row("%so %s: the output has %s%s" % (cid, label, "; ".join(repr(x) for x in want_lines) if want_lines else "no line that is asked for",
                                          ("" if not deny_lines else " and none of " + "; ".join(repr(x) for x in deny_lines))),
        all(any(ln == x for ln in out) for x in want_lines) and not any(any(ln == x for ln in out) for x in deny_lines), repr(out[-6:]))
    if want_audit or deny_audit or audit_checked:
        row("%sa %s: the audit trail %s%s" % (cid, label, ("has " + "; ".join(want_audit)) if want_audit else "has no line that is asked for",
                                               ("" if not deny_audit else " and has none of " + "; ".join(deny_audit))),
            new is not None and all(re.search(x, new, re.M) for x in want_audit) and not any(re.search(x, new, re.M) for x in deny_audit), repr(new))
    if want_fail:
        pat = re.escape(msg(10081, ACCT, "\x00")).replace("\x00", r"\d+")
        row("%sf %s: and the failure is reported as 10081 with a status (never as a success)" % (cid, label), any(re.fullmatch(pat, ln) for ln in out), repr(out[-4:]))
    row("%sg %s: the person is afterwards in sdfiles=%s sdfileswrite=%s" % (cid, label, want_groups[0], want_groups[1]), got == want_groups, repr((got, after)))
    exp = ["%s %s %s" % (v, ME, g) for v, g in want_calls]
    row("%sc %s: the helper was called %s" % (cid, label, ("in this order: " + ", ".join("%s %s" % x for x in want_calls)) if want_calls else "NEVER"), calls == exp, repr(calls))
    return out


def cases():
    """The cases, with the rule's answer written in.  ME is the person; ACCT the account whose person is ME."""
    t_no, t_yes = msg(11482, ACCT, "no"), msg(11482, ACCT, "yes")
    w_no, w_yes = msg(11522, ACCT, "no"), msg(11522, ACCT, "yes")
    already, need_files = msg(10080, ACCT), msg(11523, ACCT)

    def aud(word):
        """The audit line modifya writes for WORD on ACCT: `modify.account <word> account=<acct>` at the end of a line (the line has a prefix before it)."""
        return r"modify\.account %s account=%s$" % (re.escape(word), re.escape(ACCT))
    any_mod = r"modify\.account files-[a-z-]+ account=%s$" % re.escape(ACCT)         # any audit line of these four words for ACCT: a case that changed nothing leaves none

    run_case("C0", "CONTROL, in sdfiles only, files-off", True, False, "MODIFY.ACCOUNT %s FILES-OFF" % ACCT, {}, (False, False), [("delgroup", "sdfiles")], [t_no], [already, w_no],
             want_audit=[aud("files-off")], deny_audit=[aud("files-write-off")])
    run_case("C1", "THE ORPHAN: in sdfileswrite and NOT in sdfiles, files-off", False, True, "MODIFY.ACCOUNT %s FILES-OFF" % ACCT, {}, (False, False), [("delgroup", "sdfileswrite")],
             [w_no, t_no], [already], want_audit=[aud("files-off")])
    run_case("C2", "in both, files-off", True, True, "MODIFY.ACCOUNT %s FILES-OFF" % ACCT, {}, (False, False), [("delgroup", "sdfileswrite"), ("delgroup", "sdfiles")], [w_no, t_no], [already],
             want_audit=[aud("files-off")], deny_audit=[aud("files-write-off")])
    run_case("C3", "in both, files-off, the removal from sdfileswrite FAILS", True, True, "MODIFY.ACCOUNT %s FILES-OFF" % ACCT, {"delgroup sdfileswrite": ["fail"]}, (True, True),
             [("delgroup", "sdfileswrite")], [], [t_no, w_no], want_fail=True, deny_audit=[any_mod], audit_checked=True)
    # 19 Oct 26, finish 2 (verifier): when the write group WENT and the removal from sdfiles then failed, the person had lost write access and the command printed only the 10081 line and
    # wrote no audit line.  The write group's line and an audit line for what did happen are now given; the line for files-off is still written only when both removals worked.
    run_case("C4", "in both, files-off, the removal from sdfileswrite works and the removal from sdfiles FAILS", True, True, "MODIFY.ACCOUNT %s FILES-OFF" % ACCT, {"delgroup sdfiles": ["fail"]},
             (True, False), [("delgroup", "sdfileswrite"), ("delgroup", "sdfiles")], [w_no], [t_no], want_fail=True, want_audit=[aud("files-write-off")], deny_audit=[aud("files-off")])
    run_case("C5", "a stray sdfileswrite, files-on", False, True, "MODIFY.ACCOUNT %s FILES-ON" % ACCT, {}, (True, False), [("delgroup", "sdfileswrite"), ("addgroup", "sdfiles")],
             [w_no, t_yes], [already, w_yes], want_audit=[aud("files-on")], deny_audit=[aud("files-write-off")])
    run_case("C6", "CONTROL, in neither, files-on", False, False, "MODIFY.ACCOUNT %s FILES-ON" % ACCT, {}, (True, False), [("addgroup", "sdfiles")], [t_yes], [already, w_no, w_yes])
    run_case("C7", "CONTROL, in both, files-on", True, True, "MODIFY.ACCOUNT %s FILES-ON" % ACCT, {}, (True, True), [], [already], [t_yes, w_no])
    run_case("C8", "CONTROL, in neither, files-off", False, False, "MODIFY.ACCOUNT %s FILES-OFF" % ACCT, {}, (False, False), [], [already], [t_no, w_no])
    run_case("C9a", "files-write-on for a person who is not in sdfiles", False, False, "MODIFY.ACCOUNT %s FILES-WRITE-ON" % ACCT, {}, (False, False), [], [need_files], [w_yes])
    run_case("C9b", "files-write-on for a person in sdfiles", True, False, "MODIFY.ACCOUNT %s FILES-WRITE-ON" % ACCT, {}, (True, True), [("addgroup", "sdfileswrite")], [w_yes], [need_files, already])
    run_case("C9c", "files-write-off for a person in both", True, True, "MODIFY.ACCOUNT %s FILES-WRITE-OFF" % ACCT, {}, (True, False), [("delgroup", "sdfileswrite")], [w_no], [t_no, t_yes],
             want_audit=[aud("files-write-off")])
    run_case("C9d", "files-write-off for a person in sdfiles only", True, False, "MODIFY.ACCOUNT %s FILES-WRITE-OFF" % ACCT, {}, (True, False), [], [already], [w_no],
             deny_audit=[any_mod], audit_checked=True)
    run_case("C10a", "in both, files-off, the helper says yes to the removal from sdfileswrite and changes NOTHING", True, True, "MODIFY.ACCOUNT %s FILES-OFF" % ACCT,
             {"delgroup sdfileswrite": ["noop"]}, (True, True), [("delgroup", "sdfileswrite")], [], [t_no, w_no], want_fail=True, deny_audit=[any_mod], audit_checked=True)
    run_case("C10b", "in both, files-off, the helper says yes to the removal from sdfiles and changes NOTHING", True, True, "MODIFY.ACCOUNT %s FILES-OFF" % ACCT,
             {"delgroup sdfiles": ["noop"]}, (True, False), [("delgroup", "sdfileswrite"), ("delgroup", "sdfiles")], [w_no], [t_no], want_fail=True,
             want_audit=[aud("files-write-off")], deny_audit=[aud("files-off")])
    run_case("C11", "a stray sdfileswrite that cannot be removed, files-on", False, True, "MODIFY.ACCOUNT %s FILES-ON" % ACCT, {"delgroup sdfileswrite": ["fail"]}, (False, True),
             [("delgroup", "sdfileswrite")], [], [t_yes, w_no], want_fail=True, deny_audit=[any_mod], audit_checked=True)
    # a stray write membership that WAS removed, and then sdfiles cannot be added: the person ends in neither group (the stray write access is gone, no read was given), the command says
    # so and the audit trail has the removal and not a files-on
    run_case("C11b", "a stray sdfileswrite is removed and then the ADD of sdfiles FAILS, files-on", False, True, "MODIFY.ACCOUNT %s FILES-ON" % ACCT, {"addgroup sdfiles": ["fail"]}, (False, False),
             [("delgroup", "sdfileswrite"), ("addgroup", "sdfiles")], [w_no], [t_yes], want_fail=True, want_audit=[aud("files-write-off")], deny_audit=[aud("files-on")])


# MUTANTS: one fault in the SANDBOX's copy of modifya (never the tree), and the rows that must fail - written before the first run, from reading the program and the cases.  The
# text to change must be in the tree's modifya exactly once.  A mutant that fails fewer rows is a rule no row guards; one that fails more is a row that guards the wrong thing.
#   name                   text of modifya that is changed                                  its replacement                                                       the rows that must fail, and nothing else
MUTANTS = {
    # FILES-OFF ignores the write group when it decides there is nothing to do (the 18 Oct build)
    # (19 Oct 26, finish 2: the lists of the first four mutants grew by the AUDIT rows and by case C11b, which exist since this change - a mutated command that goes on, or does not remove what it
    #  should, writes the audit line of the whole command or none, and those rows say what the audit trail must hold.  The rows added to each list are marked +.)
    "orphan-ignored": ("nothing.to.do = not(has.files) and not(has.write)", "nothing.to.do = not(has.files)", ("C1o", "C1g", "C1c", "C1a")),       # + C1a: no audit line, the command did nothing
    # FILES-ON leaves a stray write membership alone (the third hole of K4a); the person is then in both, and the case that cannot remove it adds sdfiles all the same
    "stray-kept": ("if files.grp = 'sdfiles' and has.write then\n      cg.group = 'sdfileswrite'", "if files.grp = 'sdfiles' and has.write and not(files.want) then\n      cg.group = 'sdfileswrite'",
                   ("C5o", "C5g", "C5c", "C11o", "C11f", "C11g", "C11c",
                    "C11a",                                                                       # + sdfiles is added, so the files-on audit line a refused command must not have is there
                    "C11bo", "C11bc", "C11bg", "C11ba")),                                         # + C11b: the stray is not removed, so the output, the calls, the groups and the audit differ
    # a group change is not read back
    "no-step-readback": ("if files.stat = 0 and cg.now # cg.want then files.stat = 2", "if 0 then files.stat = 2", ("C10ao", "C10af", "C10ag", "C10ac", "C10bf",
                                                                                                                   "C10aa", "C10ba")),   # + the command believes the helper and audits a success
    # a failure of the write group's removal does not stop the command: sdfiles goes next and the orphan is made
    "write-failure-ignored": ("      gosub change.files.group\n      if files.stat # 0 then\n         @system.return.code = -ER$FAILED\n         crt sysmsg(10081, acc.name, files.stat)\n         return\n      end\n      now.write = cg.now",
                              "      gosub change.files.group\n      now.write = cg.now", ("C3o", "C3f", "C3g", "C3c", "C10ao", "C10af", "C10ag", "C10ac", "C11o", "C11f", "C11g", "C11c",
                                                                                                           "C3a", "C10aa", "C11a")),     # + the command goes on and audits a success
    # sdfiles is taken from a person who is not in it
    "sdfiles-for-nonmember": ("if files.grp = 'sdfiles' and not(files.want) and not(has.files) then\n      now.files = @false\n      files.stat = 0\n   end else",
                              "if 0 then\n      now.files = @false\n      files.stat = 0\n   end else", ("C1c",)),
    # the line for the write group that went is not printed when the whole command worked
    "silent-write-removal": ("if write.removed then gosub write.removed.line  ;* the write group went too", "if 0 then gosub write.removed.line  ;* the write group went too",
                             ("C1o", "C2o", "C5o")),
    # finish 2 (verifier), written BEFORE the first run: the step after the write removal fails and the command does not say that the write group went (C4: files-off, sdfiles cannot be taken
    # away; C10b: the helper says yes and changes nothing; C11b: files-on, sdfiles cannot be added after a stray write membership was removed)
    "failure-silent": ("         gosub write.removed.line\n      end\n      crt sysmsg(10081, acc.name, files.stat)", "      end\n      crt sysmsg(10081, acc.name, files.stat)", ("C4o", "C10bo", "C11bo")),
    # ... and the removal that happened has no audit line
    "failure-unaudited": ("         void kernel(K$AUDIT, 'modify.account files-write-off account=' : acc.name)\n", "", ("C4a", "C10ba", "C11ba")),
    # ... or the audit line names the action that was ASKED for (files-off / files-on), which says the whole command worked
    "failure-audit-asked": ("'modify.account files-write-off account=' : acc.name)", "'modify.account ' : downcase(action) : ' account=' : acc.name)", ("C4a", "C10ba", "C11ba")),
}


def patch_modifya(mutant=None):
    """The sandbox's modifya from the tree's: the helper and the two group lookups pointed at the scratch directory (the only differences from the shipped program), and the mutant's
    change when there is one; compiled there as the administrator.  The lookups are two new programs, copies of !is_grp_member and !is_group reading the scratch directory."""
    with open(os.path.join(TREE, "sdsys", "gpl.bp", "modifya"), encoding="utf-8", errors="replace") as f:
        src = f.read()
    shim = os.path.join(q3.BOX, "grp", "elevate-shim")
    n_el = src.count("sudo /usr/local/sbin/sd-elevate")
    for old, new in (("calling '!is_grp_member'", "calling '!zzgm'"), ("calling '!is_group'", "calling '!zzgg'")):
        if src.count(old) != 1:
            q3.bail("the tree's modifya has %r %d times, not once" % (old, src.count(old)))
        src = src.replace(old, new)
    src = src.replace("sudo /usr/local/sbin/sd-elevate", shim)
    if mutant is not None:
        old, new, _kills = MUTANTS[mutant]
        if src.count(old) != 1:
            q3.bail("mutant %s: the text to change is found %d times, not once: %r" % (mutant, src.count(old), old[:70]))
        src = src.replace(old, new)
    put(os.path.join(q3.SYS, "gpl.bp", "modifya"), src)
    for real, fake, cat in (("is_grp_member", "zzgm", "!zzgm"), ("is_group", "zzgg", "!zzgg")):
        with open(os.path.join(TREE, "sdsys", "gpl.bp", real), encoding="utf-8", errors="replace") as f:
            t = f.read()
        if t.count('openpath "/etc" to etc then') != 1 or t.count("$catalog !" + real) != 1 or t.count("function %s(" % real) != 1:
            q3.bail("the tree's %s is not in the shape this suite patches" % real)
        t = t.replace('openpath "/etc" to etc then', 'openpath "%s" to etc then' % os.path.join(q3.BOX, "grp")).replace("$catalog !" + real, "$catalog " + cat).replace("function %s(" % real, "function %s(" % fake)
        put(os.path.join(q3.SYS, "gpl.bp", fake), t)
    out = q3.adm(["BASIC gpl.bp zzgm zzgg modifya"], internal=True)
    ok = has(out, r"^Compiled 3 program\(s\) with no errors")
    say("  [setup] the sandbox's modifya: %d call(s) of the helper pointed at the stand-in, the lookups at the scratch group file%s; compile: %r" % (n_el, (" - MUTANT " + mutant) if mutant else "", out[-3:]))
    if not ok:
        q3.bail("the patched modifya did not compile:\n" + "\n".join(out[-8:]))
    return n_el


def stand_in_rows():
    """The real sd-elevate's dry run asks `getent group <g>` for addgroup and delgroup (before it looks at --dry-run), so a suite that calls it needs the Linux groups sdfiles and sdfileswrite -
    which only an install makes.  The shim puts this suite's getent first on that dry run's PATH, which answers from the SCRATCH group file.  Shown here with the shim itself, both ways, so that
    the result does not depend on the groups of the machine: a scratch file that lacks sdfileswrite must make `addgroup` refuse (a machine that has the group would say yes), and one that holds
    it must make it accept (a machine that lacks the group would say no)."""
    shim = os.path.join(q3.BOX, "grp", "elevate-shim")
    path = os.path.join(q3.BOX, "grp", "group")
    write_group([], [])
    with_group = subprocess.run([shim, "addgroup", ME, "sdfileswrite"], capture_output=True, text=True, timeout=60).returncode
    put(path, "\n".join(["root:x:0:", grp_line("sdusers", 2000, [ME]), grp_line("sdfiles", 2001, [])]))                  # no sdfileswrite in the file
    without_group = subprocess.run([shim, "addgroup", ME, "sdfileswrite"], capture_output=True, text=True, timeout=60).returncode
    mem = read_group()
    say("  [setup] the dry run of the real sd-elevate, through the shim: scratch file with sdfileswrite -> exit %d, without it -> exit %d; the person is in sdfileswrite afterwards: %s (the machine's own groups: %s)"
        % (with_group, without_group, ME in mem.get("sdfileswrite", []), "sdfiles " + ("present" if subprocess.run(["getent", "group", "sdfiles"], capture_output=True).returncode == 0 else "absent")
           + ", sdfileswrite " + ("present" if subprocess.run(["getent", "group", "sdfileswrite"], capture_output=True).returncode == 0 else "absent")))
    row("S1 the shim's dry run reads the SCRATCH group file and not the machine's /etc/group: addgroup of sdfileswrite is accepted (exit 0) when the scratch file holds the group and refused (exit 2) "
        "when it does not - so this suite needs no install and no Linux group of its own", with_group == 0 and without_group == 2, repr((with_group, without_group)))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    mutant = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mutant=")), None)
    if len(args) != 1 or (mutant is not None and mutant not in MUTANTS):
        q3.bail("usage: sandbox-filesgrp.py <dir> [--build] [--mutant=%s]" % "|".join(MUTANTS))
    q3.BOX = os.path.abspath(args[0])
    q3.SYS = os.path.join(q3.BOX, "sys")
    q3.SD = os.path.join(q3.SYS, "bin", "sd")
    say("sandbox-filesgrp: sandbox %s" % q3.BOX)
    say("sandbox-filesgrp: tree    %s" % TREE)
    say("sandbox-filesgrp: person  %s (whoever runs this; the real helper's dry run only accepts a user that exists)" % ME)
    if "--build" in sys.argv:
        if os.path.exists(q3.BOX) and os.listdir(q3.BOX):
            q3.bail("%s is not empty" % q3.BOX)
        r = subprocess.run([sys.executable, q3.TOOL, q3.BOX, "all"], capture_output=True, text=True, errors="replace", timeout=900)
        if "[FAIL]" in r.stdout or r.returncode != 0 or "[PASS] THIRD.COMPILE" not in r.stdout:
            q3.bail("the sandbox build did not pass:\n" + r.stdout[-800:])
        say("sandbox-filesgrp: built, bootstrap passed")
    elif not os.path.isfile(q3.SD):
        q3.bail("%s holds no built sandbox (use --build, or point it at one)" % q3.BOX)
    subprocess.run([sys.executable, q3.TOOL, q3.BOX, "start"], capture_output=True, text=True, errors="replace", timeout=120)

    os.makedirs(os.path.join(q3.BOX, "grp"), exist_ok=True)
    shim = os.path.join(q3.BOX, "grp", "elevate-shim")
    put(shim, SHIM % {"box": q3.BOX, "elevate": os.path.join(HERE, "sd-elevate")})
    os.chmod(shim, 0o755)
    os.makedirs(os.path.join(q3.BOX, "grp", "fakebin"), exist_ok=True)
    getent = os.path.join(q3.BOX, "grp", "fakebin", "getent")
    put(getent, GETENT % {"box": q3.BOX})
    os.chmod(getent, 0o755)
    put(os.path.join(q3.BOX, "grp", "calls.log"), "")
    try:
        say("\n--- preparation: a CPROC that is not the install build, the fixture account, the patched modifya ---")
        q3.prepare()
        put(os.path.join(q3.SYS, "accounts", ACCT), "\n".join([os.path.join(q3.BOX, "user_accounts", ACCT), "", "sdu_" + ME, "", "", "", "no", "no"]) + "\n")
        patch_modifya(mutant)
        # NULL CASE REFUSED: the scratch file must be what modifya reads.  The person is put in sdfiles ONLY in the scratch file; if modifya read /etc/group instead it would answer
        # from there.  The rows of C0 then see a removal that only the scratch file could cause; here the premise is shown: the real /etc/group does not say the same.
        real = subprocess.run(["id", "-nG", ME], capture_output=True, text=True).stdout.split()
        say("  [setup] the real groups of %s: %s" % (ME, " ".join(real)))
        if "sdusers" in real and "sdfiles" in real and "sdfileswrite" in real:
            q3.bail("%s is really in sdusers, sdfiles AND sdfileswrite, so a case could pass by reading /etc/group instead of the scratch file" % ME)
        if mutant is not None:
            say("sandbox-filesgrp: MUTANT %s: %r -> %r; the rows that must fail, and nothing else: %s" % (mutant, MUTANTS[mutant][0][:70], MUTANTS[mutant][1][:70], ", ".join(MUTANTS[mutant][2])))
        stand_in_rows()
        cases()
    finally:
        subprocess.run([sys.executable, q3.TOOL, q3.BOX, "stop"], capture_output=True, text=True, errors="replace", timeout=120)
    say("\nsandbox-filesgrp: %d passed, %d failed" % (q3.passed, q3.failed))
    if mutant is not None:
        want, got = sorted(set(MUTANTS[mutant][2])), sorted(set(FAILED_IDS))
        ok = want == got
        say("sandbox-filesgrp: MUTANT %s: the rows that failed are %s; they had to be exactly %s -> %s" % (mutant, got, want, "KILLED BY ITS OWN ROWS" if ok else "NOT AS EXPECTED"))
        return 0 if ok else 1
    return 1 if q3.failed else 0


if __name__ == "__main__":
    sys.exit(main())
