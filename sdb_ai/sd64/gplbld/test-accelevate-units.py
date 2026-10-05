#!/usr/bin/env python3
"""test-accelevate-units.py - sd-elevate's S.50 verbs, through --dry-run.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-accelevate-units.py
  python3 .../test-accelevate-units.py --selftest     each mutant must go red

No sudo, no install, no sd.  Exit 0 every row passed, 1 a row failed, 2 it
could not run.  Written 01 Oct 26 for S.50 (BACKUP.ACCOUNT / RESTORE.ACCOUNT).

WHAT IT MEASURES.  tree-count, backup-pack, restore-place and akpath-set run as
root, so their argument checks are what keeps sdsys from reading or moving
anything but account directories.  Each row runs the real helper with
--dry-run against a FIXTURE accounts root (SD_ACCT_ROOT, a scratch directory
holding user_accounts/<you>, group_accounts/team and a staged restore), prints
the command line and what came back, and matches the helper's own refusal
reason - never a bare non-zero exit.

THE USER IS WHOEVER RUNS IT (getpass.getuser()).  It must be an ordinary
account (uid at or above UID_MIN), because the user-account rows need one that
require_sd_user accepts; run as root or a system account, it refuses to run.

THE NULL CASE IS REFUSED: no ALLOW or no REFUSE rows, or a missing helper, exits
2.  --selftest runs the rows against mutant copies of the helper (the
staged-path pattern gone, the owner check gone, the cross-account akpath check
gone, backup-pack's name check gone) and requires each to fail a row.
"""

import getpass
import os
import pwd
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HELPER = os.path.join(HERE, "sd-elevate")
ALLOW, REFUSE = "ALLOW", "REFUSE"
R = {"pass": 0, "fail": 0, ALLOW: 0, REFUSE: 0}


def say(s=""):
    print(s)
    sys.stdout.flush()


def uid_min():
    try:
        with open("/etc/login.defs") as f:
            for line in f:
                p = line.split()
                if len(p) >= 2 and p[0] == "UID_MIN" and p[1].isdigit():
                    return int(p[1])
    except OSError:
        pass
    return 1000


OTHER = None   # another ordinary account on this machine; set in main()


def other_user(me):
    """An existing account, not you, that require_sd_user accepts (uid at or
    above UID_MIN, not root or sdsys) - 'nobody' on most systems."""
    lo = uid_min()
    for p in sorted(pwd.getpwall(), key=lambda p: p.pw_uid):
        if p.pw_name not in (me, "root", "sdsys") and p.pw_uid >= lo \
                and len(p.pw_name) <= 32 and p.pw_name.replace("_", "a").replace("-", "a").isalnum() \
                and p.pw_name[0].isalpha() and p.pw_name == p.pw_name.lower():
            return p.pw_name
    return None


def run(helper, root, args, extra=None):
    env = dict(os.environ, SD_ACCT_ROOT=root)
    env.pop("SD_TLS_PEM_FIXTURE", None)      # a row sets it itself, or runs without it
    env.update(extra or {})
    p = subprocess.run(["bash", helper, "--dry-run"] + args, capture_output=True, text=True, env=env)
    return p.returncode, p.stdout, p.stderr


def cases(root, me):
    ua, ga = os.path.join(root, "user_accounts"), os.path.join(root, "group_accounts")
    mine, team = os.path.join(ua, me), os.path.join(ga, "team")
    st_me = os.path.join(root, ".sdrestore.7", "accounts", me)
    st_team = os.path.join(root, ".sdrestore.7", "accounts", "team")
    link = os.path.join(root, "linked")
    return [
        # ------------------------------------------------------------ ALLOW
        (ALLOW, ["tree-count", mine], "count " + mine, "your own account directory"),
        (ALLOW, ["tree-count", team], "count " + team, "a group account directory"),
        (ALLOW, ["backup-pack", me + "=" + mine, "team=" + team], "pack %s=%s team=%s" % (me, mine, team),
         "two accounts, each named for its own directory"),
        (ALLOW, ["restore-place", me, "sdu_" + me, st_me, mine], "restored " + mine,
         "a user account back to <user>:sdu_<user>"),
        (ALLOW, ["restore-place", "sdsys", "sdg_team", st_team, team], "restored " + team,
         "a group account back to sdsys:sdg_<name>"),
        (ALLOW, ["akpath-set", os.path.join(mine, "data"), os.path.join(mine, "idx")], "sdidx -p",
         "an index path inside the file's own account"),
        # An ordinary user cannot see into /etc/sd-tls, so only root may call the file absent: this
        # row must print the command and must NOT claim "not yet generated" (the last element is
        # text that must not appear - the failure wording, refused as well as the success wording).
        (ALLOW, ["tls-show"], "openssl x509 -noout -subject", "the API certificate's fields, -noout; an ordinary user is never told it is absent",
         None, "not yet generated"),
        # 05 Oct 26: no certificate yet (the API makes it at the first TLS connection) is one plain
        # line, not openssl's "Could not open file or uri".  SD_TLS_PEM_FIXTURE is honoured on a dry run only.
        (ALLOW, ["tls-show"], "certificate: not yet generated", "no certificate yet: one plain line, as Windows' report prints it",
         {"SD_TLS_PEM_FIXTURE": os.path.join(root, "absent", "api.pem")}, "Could not open"),
        (ALLOW, ["tls-show"], "-in " + os.path.join(root, "elsewhere", "present.pem"), "a certificate there: openssl still runs on the path",
         {"SD_TLS_PEM_FIXTURE": os.path.join(root, "elsewhere", "present.pem")}, "not yet generated"),
        (REFUSE, ["tls-show", "/etc/shadow"], "privileged helper", "tls-show takes no path from the caller"),
        # S.53: bakdir-set saves one validated line in /etc/sd.conf (the functions are measured
        # on scratch files by test-bakdir-elevate-units.py; these are the real command line).
        (ALLOW, ["bakdir-set", mine], "set BACKUPDIR=%s in /etc/sd.conf" % mine,
         "an existing full path, saved in the fixed /etc/sd.conf"),
        # ----------------------------------------------------------- REFUSE
        (REFUSE, ["bakdir-set", "backups/x"], "is not a full path", "a relative path"),
        (REFUSE, ["bakdir-set", os.path.join(root, "nope")], "is not an existing directory",
         "bakdir-set saves only: a directory that does not exist is not saved, and not made here"),
        # bakdir-make: root makes a directory SDSYS cannot, only below the allowed places.
        (ALLOW, ["bakdir-make", "/var/backups/sd-test-zz"], "make /var/backups/sd-test-zz (below", "a new directory below /var/backups"),
        (ALLOW, ["bakdir-make", "/media/zz/usb/sd"], "make /media/zz/usb/sd (below /media)", "a removable drive's path"),
        (REFUSE, ["bakdir-make", "/etc/systemd/system/ssh.service.d"], "is not below a place where root may make a backup directory",
         "a systemd drop-in directory: a directory sdsys owns there would run as root"),
        (REFUSE, ["bakdir-make", "/etc/zz-backups"], "is not below a place where root may make a backup directory", "/etc"),
        (REFUSE, ["bakdir-make", "/var/backups/../etc/zz"], "or .. path component", "a .. out of an allowed place"),
        (REFUSE, ["bakdir-make", mine], "already exists", "a directory that is already there is not made"),
        (REFUSE, ["bakdir-make", "relative"], "is not a full path", "a relative path"),
        (REFUSE, ["bakdir-make", "/var/backups/a", "/etc/sd.conf"], "privileged helper", "bakdir-make takes one path"),
        (REFUSE, ["bakdir-set", mine + "\nSDSYS=/evil"], "may hold only", "a newline: a second line for sd.conf"),
        (REFUSE, ["bakdir-set", mine, "/etc/sd.conf"], "privileged helper", "bakdir-set takes one path and no file name"),
        (REFUSE, ["tree-count", "/etc"], "not directly inside", "a system directory"),
        (REFUSE, ["tree-count", ua], "not directly inside", "the user-accounts root itself"),
        (REFUSE, ["tree-count", os.path.join(mine, "bp")], "not directly inside", "a directory INSIDE an account"),
        (REFUSE, ["tree-count", link], "not in canonical form", "a symlink to an account"),
        (REFUSE, ["backup-pack", "x=/etc"], "not directly inside", "/etc packed as root"),
        (REFUSE, ["backup-pack", "team=" + mine], "is not the account whose directory", "a name that is not the directory's"),
        (REFUSE, ["backup-pack", mine], "is not <name>=<account directory>", "no name"),
        (REFUSE, ["restore-place", me, "sdu_" + me, os.path.join(root, "elsewhere", me), mine],
         ".sdrestore.<n>/accounts/<name>", "a staged tree outside .sdrestore.<n>"),
        (REFUSE, ["restore-place", me, "sdu_" + me, st_team, mine], "the staged tree is account 'team'",
         "a staged tree for another account"),
        (REFUSE, ["restore-place", me, "sdu_" + me, st_me, "/etc"], "but the target is 'etc'",
         "/etc as the target"),
        (REFUSE, ["restore-place", me, "sdu_" + me, st_me, os.path.join(root, "elsewhere", me)],
         "is not directly inside", "a same-named directory outside the account roots"),
        (REFUSE, ["restore-place", "root", "sdu_root", st_me, mine], "root is never a target",
         "root as the owner"),
        (REFUSE, ["restore-place", OTHER, "sdu_" + OTHER, st_me, mine], "belongs to user '%s'" % me,
         "another real user given your account"),
        (REFUSE, ["restore-place", "sdsys", "sdg_team", st_me, mine], "sdsys is SD's own administrator account",
         "sdsys owning a user account"),
        (REFUSE, ["restore-place", me, "sdusers", st_me, mine], "owns its own files through sdu_",
         "the shared sdusers group"),
        (REFUSE, ["restore-place", me, "sdu_" + me, st_team, team], "a group account's owner is sdsys",
         "a person owning a group account"),
        (REFUSE, ["restore-place", "sdsys", "sdu_" + me, st_team, team], "group is sdg_<name>",
         "a group account given a person's group"),
        (REFUSE, ["akpath-set", os.path.join(mine, "data"), os.path.join(team, "idx")], "not in the file's own account",
         "indices pointed into another account"),
        (REFUSE, ["akpath-set", "/etc/passwd", os.path.join(mine, "idx")], "outside the accounts root",
         "a data path outside the accounts root"),
    ]


def build_fixture(root, me):
    for d in ("user_accounts/%s/bp" % me, "user_accounts/%s/data" % me, "user_accounts/%s/idx" % me,
              "group_accounts/team/idx", ".sdrestore.7/accounts/%s" % me, ".sdrestore.7/accounts/team",
              "elsewhere/%s" % me):
        os.makedirs(os.path.join(root, d))
    os.symlink(os.path.join(root, "user_accounts", me), os.path.join(root, "linked"))
    open(os.path.join(root, "elsewhere", "present.pem"), "w").close()   # tls-show's "a certificate is there" row


def suite(helper, root, me, quiet=False):
    for case in cases(root, me):
        kind, args, want, why = case[:4]
        extra, bad = (case[4:] + (None, None))[:2]
        rc, out, err = run(helper, root, args, extra)
        both = out + err
        if kind == ALLOW:
            ok = rc == 0 and want in both and not (bad and bad in both)
            if args[0] == "backup-pack":
                ok = ok and out == ""   # the zip is stdout; status must not touch it
        else:
            ok = rc != 0 and want in both
        R[kind] += 1
        R["pass" if ok else "fail"] += 1
        if quiet and ok:
            continue
        say("  [%s] %-6s %s" % ("PASS" if ok else "FAIL", kind, why))
        say("         | $ %ssd-elevate --dry-run %s" % ("".join("%s=%s " % kv for kv in (extra or {}).items()), " ".join(args)))
        say("         | -> exit %d; looked for %r%s; got %r"
            % (rc, want, "" if not bad else " and not %r" % bad, both.strip()[-240:]))


MUTANTS = [
    ("staged pattern gone", r'[[ $sreal =~ ^"$root"/\.sdrestore\.([0-9]+)/accounts/([^/]+)$ ]]',
     r'[[ $sreal =~ /()([^/]+)$ ]]'),
    ("owner check gone", '[[ $owner == "$tname" ]] || die', '[[ 1 ]] || die'),
    ("cross-account akpath allowed", '[[ $ACCT_REAL == "$data_acct" ]] || die', '[[ 1 ]] || die'),
    ("pack name check gone", '[[ ${pair%%=*} == "$ACCT_NAME" ]] || die', '[[ 1 ]] || die'),
    ("bakdir character check gone", '[[ $p =~ $re ]] || die', '[[ 1 ]] || die'),
    ("bakdir allowed-places check gone", '[[ $ok -eq 1 ]] || die', 'true || die'),
    ("tls-show absent test gone", 'if [[ $tls_can_see -eq 1 && ! -e $tls_pem ]]; then', 'if false; then'),
    ("tls-show says absent to a non-root user", '[[ ${EUID:-$(id -u)} -eq 0 ]] && tls_can_see=1', 'tls_can_see=1'),
]


def main():
    me = getpass.getuser()
    say("test-accelevate-units: %s, as %s" % (HELPER, me))
    if not os.path.isfile(HELPER):
        say("CANNOT RUN - the helper is missing")
        return 2
    uid = pwd.getpwnam(me).pw_uid
    if me in ("root", "sdsys") or uid < uid_min():
        say("CANNOT RUN - %s (uid %d) is not an ordinary account; the user rows need one" % (me, uid))
        return 2
    global OTHER
    OTHER = other_user(me)
    if OTHER is None:
        say("CANNOT RUN - no second ordinary account (uid >= UID_MIN) for the owner-mismatch row")
        return 2
    say("  second account for the owner-mismatch row: %s" % OTHER)
    work = tempfile.mkdtemp(prefix="accelev-")
    try:
        root = os.path.join(work, "sd")
        build_fixture(root, me)
        say("  fixture accounts root: %s\n" % root)
        suite(HELPER, root, me)
        if R[ALLOW] == 0 or R[REFUSE] == 0:
            say("REFUSED: the null case")
            return 2
        say("\n%(pass)d passed, %(fail)d failed" % R)
        if R["fail"]:
            return 1
        if "--selftest" not in sys.argv[1:]:
            return 0
        src = open(HELPER).read()
        red = 0
        for label, old, new in MUTANTS:
            if src.count(old) != 1:
                say("CANNOT RUN - mutant '%s': expected one match, found %d" % (label, src.count(old)))
                return 2
            mp = os.path.join(work, "mutant")
            with open(mp, "w") as f:
                f.write(src.replace(old, new))
            for k in R:
                R[k] = 0
            say("\n--- mutant: %s (failing rows only)" % label)
            suite(mp, root, me, quiet=True)
            red += R["fail"] > 0
            say("--- mutant '%s': %s" % (label, "RED as it must be" if R["fail"] else "STILL GREEN - the test misses it"))
        say("\nselftest: %d of %d mutants went red" % (red, len(MUTANTS)))
        return 0 if red == len(MUTANTS) else 1
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
