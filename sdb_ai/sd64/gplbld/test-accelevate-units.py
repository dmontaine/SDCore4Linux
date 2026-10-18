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

17 Oct 26, S.65 slice 2b: also netcred-dir (the caller's own /var/lib/sd-net/<user>, mode 0700), driven with SUDO_USER /
SUDO_UID as sudo would set them and SD_NET_ROOT_FIXTURE standing for /var/lib/sd-net.  The commands it would run are
printed by the helper itself, so the owner and the mode are asserted from that line.  WHAT A DRY RUN CANNOT SHOW: that
the directory really appears, that a second run changes nothing (idempotence), and that root:root really owns the root
- the rows check that a dry run leaves the fixture as it was, and the real run is the install witness's.

THE NULL CASE IS REFUSED: no ALLOW or no REFUSE rows, or a missing helper, exits
2.  --selftest runs the rows against mutant copies of the helper (the
staged-path pattern gone, the owner check gone, the cross-account akpath check
gone, backup-pack's name check gone) and requires each to fail a row.
"""

import getpass
import hashlib
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
REAL_SPKI = [None]       # build_fixture() sets it: the SHA-256 of a real fixture certificate's public key, or None without openssl


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
    for k in ("SUDO_USER", "SUDO_UID", "SD_NET_ROOT_FIXTURE"):
        env.pop(k, None)                     # netcred-dir rows set them; nothing leaks in from a sudo shell
    env.update(extra or {})
    p = subprocess.run(["bash", helper, "--dry-run"] + args, capture_output=True, text=True, env=env)
    return p.returncode, p.stdout, p.stderr


def system_user(lo):
    """An existing account with a uid above 0 and below UID_MIN and a name the helper's name rule accepts
    ('daemon', 'bin'), or None."""
    for p in sorted(pwd.getpwall(), key=lambda p: p.pw_uid):
        if 0 < p.pw_uid < lo and p.pw_name[:1].isalpha() and p.pw_name.isalnum() and p.pw_name == p.pw_name.lower():
            return p
    return None


def netcred_cases(root, me):
    """17 Oct 26, S.65 slice 2b: sd-elevate netcred-dir.  The caller is whoever sudo says (SUDO_USER, SUDO_UID), so each
    row sets both; SD_NET_ROOT_FIXTURE stands for /var/lib/sd-net and, on a dry run, for root's own directory, so it
    belongs to the person running this.  The commands printed are the ones a real run would execute (they go through
    step), which is where the mode and the owner are asserted.  A dry run cannot show idempotence or that a directory
    appears: that is the install witness's row (and sandbox-free)."""
    uid, grp = pwd.getpwnam(me).pw_uid, grp_name(me)
    ouid = pwd.getpwnam(OTHER).pw_uid
    sysu = system_user(uid_min())
    n = lambda d: os.path.join(root, d)
    sudo_me = {"SUDO_USER": me, "SUDO_UID": str(uid)}
    def env(fixture, **kw):
        e = dict(sudo_me, SD_NET_ROOT_FIXTURE=n(fixture))
        e.update(kw)
        return e
    rows = [
        # ---- ALLOW: what a real run would do
        (ALLOW, ["netcred-dir"], "install -d -o %s -g %s -m 0700 -- %s" % (me, grp, os.path.join(n("net-new"), me)),
         "nothing there yet: the caller's directory is made owned by the caller, mode 0700", env("net-new"), "REFUSED"),
        (ALLOW, ["netcred-dir"], "install -d -o root -g root -m 0755 -- " + n("net-new"),
         "nothing there yet: the root of the logins is made root:root, mode 0755", env("net-new"), "REFUSED"),
        (ALLOW, ["netcred-dir"], "chmod 0700 -- " + os.path.join(n("net-open"), me),
         "the caller's directory is there with mode 770: set back to 0700", env("net-open"), "install -d"),
        (ALLOW, ["netcred-dir"], "%s is in place (owner uid %d, mode 700)" % (os.path.join(n("net-open7"), me), uid),
         "the caller's directory is there already and right: left as it is, no command", env("net-open7"), "chmod"),
        (ALLOW, ["netcred-dir"], "(dry run - nothing made or changed)", "a dry run says it made nothing", env("net-new"), "netcred-dir: "),
        # ---- REFUSE: who may ask
        (REFUSE, ["netcred-dir"], "only through sudo", "no SUDO_USER or SUDO_UID: not reached through sudo", {"SD_NET_ROOT_FIXTURE": n("net-new")}),
        (REFUSE, ["netcred-dir"], "only through sudo", "SUDO_UID missing", {"SUDO_USER": me, "SD_NET_ROOT_FIXTURE": n("net-new")}),
        (REFUSE, ["netcred-dir"], "is not a number", "SUDO_UID is not a number", env("net-new", SUDO_UID="12x")),
        (REFUSE, ["netcred-dir"], "root is never a target", "root is not given a directory", env("net-new", SUDO_USER="root", SUDO_UID="0")),
        (REFUSE, ["netcred-dir"], "sdsys is SD's own administrator account", "sdsys is not given one (it is refused by name)",
         env("net-new", SUDO_USER="sdsys", SUDO_UID="999")),
        (REFUSE, ["netcred-dir"], "does not exist", "SUDO_USER is nobody on this machine", env("net-new", SUDO_USER="zz-no-such-user", SUDO_UID="31999")),
        (REFUSE, ["netcred-dir"], "does not match SUDO_UID", "SUDO_UID is another person's uid", env("net-new", SUDO_UID=str(ouid))),
        (REFUSE, ["netcred-dir"], "does not match SUDO_UID", "SUDO_UID is root's, SUDO_USER an ordinary account", env("net-new", SUDO_UID="0")),
        (REFUSE, ["netcred-dir", "/etc"], "privileged helper", "netcred-dir takes no argument (not a path, not a user)", env("net-new")),
        (REFUSE, ["netcred-dir", OTHER], "privileged helper", "a user name as an argument is not the way to name another person", env("net-new")),
        (REFUSE, ["netcred-dir"], "is not an absolute directory", "the fixture root must be absolute", env("net-new", SD_NET_ROOT_FIXTURE="relative/dir")),
        # ---- REFUSE: what is already there
        (REFUSE, ["netcred-dir"], "is not a plain directory", "the root of the logins is a link", env("net-link")),
        (REFUSE, ["netcred-dir"], "is not a plain directory", "the root of the logins is a file", env("net-file")),
        (REFUSE, ["netcred-dir"], "is writable by its group or by everyone", "the root of the logins is group-writable (mode 775)", env("net-wide")),
        (REFUSE, ["netcred-dir"], "is not a plain directory", "the caller's directory is a link", env("net-linkdir")),
        (REFUSE, ["netcred-dir"], "is not a plain directory", "the caller's directory is a file", env("net-filedir")),
        (REFUSE, ["netcred-dir"], "owned by uid %d, not uid %d" % (uid, ouid), "the directory is owned by somebody else: root does not take it over",
         env("net-foreign", SUDO_USER=OTHER, SUDO_UID=str(ouid))),
    ]
    if sysu:
        rows.append((REFUSE, ["netcred-dir"], "below UID_MIN", "a system account (%s, uid %d) is not given a directory" % (sysu.pw_name, sysu.pw_uid),
                     env("net-new", SUDO_USER=sysu.pw_name, SUDO_UID=str(sysu.pw_uid))))
    else:
        say("  (no system account between uid 1 and UID_MIN on this machine: the below-UID_MIN row is left out)")
    return rows


def grp_name(user):
    import grp
    return grp.getgrgid(pwd.getpwnam(user).pw_gid).gr_name


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
        # 17 Oct 26 (S.65 slice 2a): tls-key, the hash of the API certificate's public key.  An ordinary user's dry run prints the command only
        # (it must not say the certificate is absent, nor print a figure), a fixture that is absent is one plain line, a real certificate gives
        # the figure an independent computation gives, and it takes no argument.
        (ALLOW, ["tls-key"], "openssl pkey -pubin -outform DER", "the pipeline it would run; an ordinary user is never told the certificate is absent",
         None, "not yet generated"),
        (ALLOW, ["tls-key"], "certificate: not yet generated", "no certificate yet: one plain line",
         {"SD_TLS_PEM_FIXTURE": os.path.join(root, "absent", "api.pem")}, "public key sha256"),
        (ALLOW, ["tls-key"], "public key sha256: %s" % (REAL_SPKI[0] or "<openssl is missing: this row cannot pass>"),
         "a real certificate: the figure is the SHA-256 of the key's DER, computed here independently",
         {"SD_TLS_PEM_FIXTURE": os.path.join(root, "elsewhere", "real.pem")}, "not yet generated"),
        (REFUSE, ["tls-key", "/etc/shadow"], "privileged helper", "tls-key takes no path from the caller"),
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
    # 17 Oct 26 (S.65 slice 2b): the roots netcred-dir is pointed at.  net-new is NOT made (a dry run must leave it so; main() checks).
    for d, mode in (("net-open", 0o755), ("net-open7", 0o755), ("net-wide", 0o775), ("net-linkdir", 0o755), ("net-filedir", 0o755),
                    ("net-foreign", 0o755), ("net-dirtarget", 0o755)):
        os.makedirs(os.path.join(root, d))
        os.chmod(os.path.join(root, d), mode)
    os.makedirs(os.path.join(root, "net-open", me));  os.chmod(os.path.join(root, "net-open", me), 0o770)
    os.makedirs(os.path.join(root, "net-open7", me)); os.chmod(os.path.join(root, "net-open7", me), 0o700)
    os.symlink(os.path.join(root, "net-dirtarget"), os.path.join(root, "net-linkdir", me))     # the caller's directory is a link
    open(os.path.join(root, "net-filedir", me), "w").close()                                    # ... or a file
    os.makedirs(os.path.join(root, "net-foreign", OTHER))                                       # ... or made by somebody else (this runner)
    os.chmod(os.path.join(root, "net-foreign", OTHER), 0o700)
    os.symlink(os.path.join(root, "net-open7"), os.path.join(root, "net-link"))                 # the root of the logins is a link
    open(os.path.join(root, "net-file"), "w").close()                                           # ... or a file
    open(os.path.join(root, "elsewhere", "present.pem"), "w").close()   # tls-show's "a certificate is there" row
    # 17 Oct 26 (S.65 slice 2a): a REAL certificate for tls-key, whose figure is checked against an independent computation (the key's
    # DER from openssl, hashed here by hashlib, not by openssl dgst).  Without openssl the rows say so and fail: no null pass.
    try:
        subprocess.run(["openssl", "req", "-x509", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:P-256", "-nodes",
                        "-keyout", os.path.join(root, "elsewhere", "real.key"), "-out", os.path.join(root, "elsewhere", "real.pem"),
                        "-days", "2", "-subj", "/CN=sd-elevate-test"], check=True, capture_output=True)
        pub = subprocess.run(["openssl", "x509", "-in", os.path.join(root, "elsewhere", "real.pem"), "-noout", "-pubkey"],
                             check=True, capture_output=True).stdout
        der = subprocess.run(["openssl", "pkey", "-pubin", "-outform", "DER"], input=pub, check=True, capture_output=True).stdout
        REAL_SPKI[0] = hashlib.sha256(der).hexdigest()
    except (OSError, subprocess.CalledProcessError):
        REAL_SPKI[0] = None


def suite(helper, root, me, quiet=False):
    for case in cases(root, me) + netcred_cases(root, me):
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
    # The state AFTER: the netcred-dir dry runs above were pointed at net-new, which did not exist, and must have left it so.
    made = os.path.lexists(os.path.join(root, "net-new"))
    ok = not made
    R[ALLOW] += 1
    R["pass" if ok else "fail"] += 1
    if not (quiet and ok):
        say("  [%s] %-6s netcred-dir dry runs made nothing" % ("PASS" if ok else "FAIL", ALLOW))
        say("         | %s %s after the dry runs" % (os.path.join(root, "net-new"), "exists" if made else "does not exist"))


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
    # 17 Oct 26, S.65 slice 2b: netcred-dir.
    ("netcred-dir: sudo identity not required", '[[ -n $user && -n $suid ]] || die "netcred-dir is reached', 'true || die "netcred-dir is reached'),
    ("netcred-dir: SUDO_UID need not be a number", '[[ $suid =~ ^[0-9]+$ ]] || die "netcred-dir: SUDO_UID', 'true || die "netcred-dir: SUDO_UID'),
    ("netcred-dir: the user is not checked (root, sdsys, system accounts)",
     'require_sd_user "$user"\n  [[ $(id -u "$user" 2>/dev/null) == "$suid" ]] || die "netcred-dir:',
     'true\n  [[ $(id -u "$user" 2>/dev/null) == "$suid" ]] || die "netcred-dir:'),
    ("netcred-dir: SUDO_UID need not match the user", '[[ $(id -u "$user" 2>/dev/null) == "$suid" ]] || die "netcred-dir:',
     '[[ 1 ]] || die "netcred-dir:'),
    ("netcred-dir: the fixture root need not be absolute", '[[ $SD_NET_ROOT_FIXTURE == /* && $SD_NET_ROOT_FIXTURE != / ]] || die', 'true || die'),
    ("netcred-dir: a link is used as a directory", '[[ -d $p && ! -L $p ]] || die "netcred-dir: $p is not', '[[ -d $p ]] || die "netcred-dir: $p is not'),
    ("netcred-dir: the owner of an existing directory is not checked", '[[ ${ids% *} -eq $2 ]] || die', '[[ 1 ]] || die'),
    ("netcred-dir: a writable root is accepted", '(( (8#$NET_MODE & 8#$3) == 0 )) ||', 'true ||'),
    ("netcred-dir: the root of the logins is made 0777", 'install -d -o root -g root -m 0755', 'install -d -o root -g root -m 0777'),
    ("netcred-dir: the caller's directory is made 0755", 'install -d -o "$user" -g "$grp" -m 0700', 'install -d -o "$user" -g "$grp" -m 0755'),
    ("netcred-dir: the caller's directory is made root's", 'install -d -o "$user" -g "$grp"', 'install -d -o root -g "$grp"'),
    ("netcred-dir: an open directory is set to 0750", 'step chmod 0700 -- "$dir"', 'step chmod 0750 -- "$dir"'),
    ("netcred-dir: a dry run goes on to act",
     """  if [[ $DRY -eq 1 ]]; then\n    printf '%s: (dry run - nothing made or changed)""",
     """  if false; then\n    printf '%s: (dry run - nothing made or changed)"""),
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
