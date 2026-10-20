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

19 Oct 26, S.67 stage 2 (D7): group-write, the verb that gives an account's own group write on its VOC and dictionaries so that SDSYS (a member of the
group) can write a master edit into them.  TWO HALVES.  (1) the helper's own rules through --dry-run on the fixture: which directory it accepts, which
group the directory must have, and what it would change (gw_cases).  (2) THE WORK ITSELF, run for real: the python text the helper carries (between
`read -r -d '' GW_PY` and GW_PY_END) is cut out and run as the person running this on scratch trees they own, so that the modes it leaves can be
read from the disk (gw_worker_suite) - a dry run cannot say that a link is not followed or that a file of another group is left alone.  THE ONE THING
NEITHER HALF CAN SHOW is root changing files that belong to ANOTHER user, and the device check (it needs a mount): witness-masters.sh does.
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
    for k in ("SUDO_USER", "SUDO_UID", "SD_NET_ROOT_FIXTURE", "SD_GW_GROUP_FIXTURE", "SD_NOT_DRY"):
        env.pop(k, None)                     # netcred-dir rows set them; nothing leaks in from a sudo shell
    env.update(extra or {})
    dry = env.pop("SD_NOT_DRY", None) is None    # a row that must see a fixture IGNORED runs without --dry-run (as an ordinary user it can only refuse)
    p = subprocess.run(["bash", helper] + (["--dry-run"] if dry else []) + args, capture_output=True, text=True, env=env)
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


def gw_cases(root, me):
    """19 Oct 26, S.67 stage 2: sd-elevate group-write, the helper's own rules, through --dry-run.  The fixture's account directories belong to the
    person running this and to THEIR primary group, which is not sdu_<name>; SD_GW_GROUP_FIXTURE (honoured on a dry run only) names the group the
    ALLOW rows treat as the account's own.  The REFUSE rows run without it, so the real rule (the account's own group, sdu_<name> or sdg_<name>)
    is what refuses them."""
    ua, ga = os.path.join(root, "user_accounts"), os.path.join(root, "group_accounts")
    mine, team = os.path.join(ua, me), os.path.join(ga, "team")
    mygroup = grp_name(me)
    fx = {"SD_GW_GROUP_FIXTURE": mygroup}
    sdsys = None
    try:
        sdsys = pwd.getpwnam("sdsys").pw_uid
    except KeyError:
        pass
    owners = "%d%s" % (pwd.getpwnam(me).pw_uid, ",%d" % sdsys if sdsys is not None else "")
    ok_head = "group-write %s (group %s, gid %d; owners uid %s)" % (mine, mygroup, pwd.getpwnam(me).pw_gid, owners)
    return [
        # ---- ALLOW (with the group the account owns named by the fixture): the plan, as the helper prints it
        (ALLOW, ["group-write", mine], ok_head, "your account directory, its own group: the header names the group, the gid and the uids that may own what is changed", fx),
        (ALLOW, ["group-write", mine], "chmod g+rwxs voc", "the VOC directory gets group rwx and setgid", fx),
        (ALLOW, ["group-write", mine], "chmod g+rw voc/%0", "...and its subfiles group rw", fx),
        (ALLOW, ["group-write", mine], "chmod g+rwxs foo.dic", "a dictionary directory", fx),
        (ALLOW, ["group-write", mine], "chmod g+rwxs sub/bar.dic", "a dictionary below the account directory (CREATE.FILE sub/bar)", fx),
        (ALLOW, ["group-write", mine], "skipped foo.dic/lnk", "a link inside a dictionary is skipped, not followed", fx),
        (ALLOW, ["group-write", mine], "(dry run - nothing changed)", "a dry run says it changed nothing", fx, "REFUSED"),
        (ALLOW, ["group-write", team], "group-write %s (group %s" % (team, mygroup), "a group account's directory is accepted too", fx),
        # a data file's directory, a directory merely called voc below the top, and report.doc are none of its business
        (ALLOW, ["group-write", mine], "group-write: 4 directories and", "four directories would change: voc, foo.dic, sub/bar.dic and exe.dic - and no other", fx, "chmod g+rwxs data"),
        (ALLOW, ["group-write", mine], "chmod g+rw exe.dic/x", "a file with the execute bit gets group rw only", fx, "g+rwx exe.dic/x"),
        # ---- REFUSE: whose directory
        (REFUSE, ["group-write", mine], "not to the account's own group 'sdu_%s'" % me,
         "no fixture: the directory belongs to %s, not to sdu_%s - a group other accounts may be in is never given write" % (mygroup, me)),
        (REFUSE, ["group-write", team], "not to the account's own group 'sdg_team'", "a group account is held to sdg_<name>"),
        (REFUSE, ["group-write", mine], "not to the account's own group 'sdu_%s'" % me, "the fixture is IGNORED when the run is not a dry run (no --dry-run, no root: refused first)",
         {"SD_GW_GROUP_FIXTURE": mygroup, "SD_NOT_DRY": "1"}),
        (REFUSE, ["group-write", "/etc"], "not directly inside", "a system directory"),
        (REFUSE, ["group-write", "/"], "not directly inside", "the root of the machine"),
        (REFUSE, ["group-write", ua], "not directly inside", "the user-accounts root itself"),
        (REFUSE, ["group-write", os.path.join(mine, "voc")], "not directly inside", "a directory INSIDE an account"),
        (REFUSE, [ "group-write", os.path.join(root, "linked")], "not in canonical form", "a symlink to an account"),
        (REFUSE, ["group-write", mine + "/"], "not in canonical form", "a trailing slash"),
        (REFUSE, ["group-write", os.path.join(ua, "..", "user_accounts", me)], "not in canonical form", "a .. component"),
        (REFUSE, ["group-write", os.path.join(ua, "zzprobenodir")], "does not exist", "no such directory"),
        (REFUSE, ["group-write", "user_accounts/" + me], "is not absolute", "a relative path"),
        (REFUSE, ["group-write", mine, team], "privileged helper", "one directory only"),
        (REFUSE, ["group-write"], "privileged helper", "the directory is required"),
    ]


def build_gw_fixture(mine, team):
    """The shapes group-write meets, below the fixture account directories (the worker's own tree is gw_tree)."""
    def mk(path, mode, text=b""):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(text)
        os.chmod(path, mode)
    for acct in (mine, team):
        for d in ("voc", "foo.dic", "sub/bar.dic", "exe.dic", "data", "report.doc", "sub/voc"):
            os.makedirs(os.path.join(acct, d), exist_ok=True)
            os.chmod(os.path.join(acct, d), 0o755)
        for f in ("voc/%0", "voc/%1", "foo.dic/%0", "foo.dic/%1", "sub/bar.dic/%0", "sub/bar.dic/%1", "data/%0", "report.doc/%0", "sub/voc/%0"):
            mk(os.path.join(acct, f), 0o644)
        mk(os.path.join(acct, "exe.dic", "x"), 0o755)
        os.symlink("/etc/passwd", os.path.join(acct, "foo.dic", "lnk"))


# ---- the work itself --------------------------------------------------------------------------------------------------------------------------

GW_START, GW_END = "read -r -d '' GW_PY <<'GW_PY_END' || true\n", "\nGW_PY_END\n"


def gw_worker_text(src):
    """The python3 text group-write carries, or None when the markers are not there once each."""
    if src.count(GW_START) != 1 or src.count(GW_END) != 1:
        return None
    a = src.index(GW_START) + len(GW_START)
    return src[a:src.index(GW_END, a)] + "\n"


def second_group():
    """A group of this person's other than the primary one, or None."""
    for g in os.getgroups():
        if g != os.getgid():
            return g
    return None


def gw_tree(base):
    """A scratch account directory with every shape the worker meets, all owned by this person.  Returns (top, outside, paths)."""
    top, outside = os.path.join(base, "acct"), os.path.join(base, "outside")
    g2 = second_group()

    def mk(rel, mode, isdir=False):
        p = os.path.join(top, rel)
        if isdir:
            os.makedirs(p, exist_ok=True)
        else:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "wb").close()
        os.chmod(p, mode)
        return p
    for d in ("voc", "foo.dic", "foo.dic/nested.dic", "sub/bar.dic", "sub/voc", "exe.dic", "data", "report.doc", "voc/inner"):
        mk(d, 0o755, True)
    for f, m in (("voc/%0", 0o644), ("voc/%1", 0o644), ("foo.dic/%0", 0o644), ("foo.dic/%1", 0o644), ("foo.dic/nested.dic/%0", 0o644),
                 ("sub/bar.dic/%0", 0o640), ("sub/bar.dic/%1", 0o644), ("sub/voc/%0", 0o644), ("data/%0", 0o644), ("report.doc/%0", 0o644),
                 ("exe.dic/x", 0o755), ("foo.dic/%2", 0o644), ("file.dic", 0o644), ("voc/inner/%0", 0o644)):
        mk(f, m)
    os.makedirs(os.path.join(outside, "dir"))
    for f, m in (("target", 0o600), ("dir/%0", 0o644)):
        p = os.path.join(outside, f)
        open(p, "wb").close()
        os.chmod(p, m)
    os.symlink(os.path.join(outside, "target"), os.path.join(top, "foo.dic", "lnk"))      # a link to a file, inside a dictionary
    os.symlink(os.path.join(outside, "dir"), os.path.join(top, "evil.dic"))               # a dictionary that is a link to a directory
    os.mkfifo(os.path.join(top, "foo.dic", "fifo"), 0o644)
    if g2 is not None:
        os.chown(os.path.join(top, "foo.dic", "%2"), -1, g2)                              # a file of another group
    return top, outside


def modes(top):
    """{relative path: mode} of everything below top, links not followed."""
    out = {}
    for dp, dn, fn in os.walk(top, followlinks=False):
        for n in dn + fn:
            p = os.path.join(dp, n)
            out[os.path.relpath(p, top)] = stat_mode(p)
    out["."] = stat_mode(top)
    return out


def stat_mode(p):
    import stat
    return stat.S_IMODE(os.lstat(p).st_mode)


def gw_worker_suite(helper, work, quiet=False):
    """Runs the helper's python text on scratch trees.  Counts into R like suite()."""
    import stat
    src = open(helper).read()
    text = gw_worker_text(src)
    wpy = os.path.join(work, "gw_worker.py")
    uid, gid = os.getuid(), os.getgid()

    def row(label, ok, detail=""):
        R[REFUSE if label.split()[0] in ("W9", "W10", "W11", "W12") else ALLOW] += 1     # the rows that expect the worker to leave things alone or to refuse
        R["pass" if ok else "fail"] += 1
        if not (quiet and ok):
            say("  [%s] %-6s %s%s" % ("PASS" if ok else "FAIL", "WORK", label, ("   <- " + detail) if detail and not ok else ""))
    if text is None:
        row("W0 the helper carries its worker text once between the markers", False, "markers found %d and %d times" % (src.count(GW_START), src.count(GW_END)))
        return
    with open(wpy, "w") as f:
        f.write(text)

    def work_run(top, owners=None, dry=False, g=None):
        p = subprocess.run([sys.executable, wpy, top, str(gid if g is None else g), ",".join(str(x) for x in (owners if owners is not None else [uid])), "1" if dry else "0"],
                           capture_output=True, text=True)
        return p.returncode, p.stdout, p.stderr

    # W1: the real run
    base = tempfile.mkdtemp(prefix="gw1-", dir=work)
    top, outside = gw_tree(base)
    before = modes(top)
    outside_before = modes(outside)
    rc, out, err = work_run(top)
    after = modes(top)
    sg = stat.S_ISGID
    want_dirs = {"voc", "foo.dic", "sub/bar.dic", "exe.dic"}
    want_files = {"voc/%0": 0o664, "voc/%1": 0o664, "foo.dic/%0": 0o664, "foo.dic/%1": 0o664, "sub/bar.dic/%0": 0o660, "sub/bar.dic/%1": 0o664, "exe.dic/x": 0o775}
    row("W1 the VOC and dictionaries are changed: directories g+rwxs (2775 from 755), files g+rw (664, 660 from 640, 775 from 755), exit 0",
        rc == 0 and all(after[d] == before[d] | 0o2070 for d in want_dirs) and all(after[f] == m for f, m in want_files.items()), "rc=%d dirs=%r files=%r %s" % (
            rc, {d: oct(after[d]) for d in want_dirs}, {f: oct(after[f]) for f in want_files}, err.strip()[-120:]))
    untouched = {k: v for k, v in before.items() if k not in want_dirs and k not in want_files}
    row("W2 NOTHING ELSE changes: not the account directory, a data file's directory, a directory called voc below the top, report.doc, a dictionary inside a "
        "dictionary, a plain file called x.dic, the file of another group, the other bits of anything", all(after[k] == v for k, v in untouched.items()),
        repr({k: (oct(untouched[k]), oct(after[k])) for k in untouched if after[k] != untouched[k]}))
    row("W3 a link inside a dictionary is not followed: its target (mode 600) is as it was, and so is a dictionary that is a link to a directory and the file in that directory",
        modes(outside) == outside_before and "skipped foo.dic/lnk" in out, repr((modes(outside), outside_before, out[-200:])))
    row("W4 the plan says what it did: 4 directories and 7 file(s) changed, nothing already right, and the skipped (a link, a fifo, a file of another group)",
        "group-write: 4 directories and 7 file(s) changed, 0 already right, 3 skipped" in out, out.strip()[-160:])
    row("W5 a fifo in a dictionary is skipped and not opened for reading (the run did not hang, and says so)", "skipped foo.dic/fifo" in out, out.strip()[-160:])
    row("W6 a file of ANOTHER group is skipped and keeps its mode (the dictionary around it is changed)",
        "skipped foo.dic/%2" in out and after["foo.dic/%2"] == before["foo.dic/%2"] and after["foo.dic"] & 0o2070 == 0o2070, out.strip()[-160:])
    rc2, out2, err2 = work_run(top)
    row("W7 run again it changes nothing: 0 directories and 0 files, 11 already right", rc2 == 0 and "0 directories and 0 file(s) changed, 11 already right" in out2 and modes(top) == after, out2.strip()[-160:])
    # W8: a dry run
    base = tempfile.mkdtemp(prefix="gw8-", dir=work)
    top, outside = gw_tree(base)
    before = modes(top)
    rc, out, err = work_run(top, dry=True)
    row("W8 a dry run changes no mode at all, and says what WOULD change", rc == 0 and modes(top) == before and "would be changed" in out and "(dry run - nothing changed)" in out, out.strip()[-200:])
    # W9: owners
    base = tempfile.mkdtemp(prefix="gw9-", dir=work)
    top, outside = gw_tree(base)
    before = modes(top)
    rc, out, err = work_run(top, owners=[uid + 1])
    row("W9 what the account's owner (and sdsys) do not own is not changed: with other uids as the owners no mode moves", rc == 0 and modes(top) == before and "skipped voc: not owned" in out, out.strip()[-200:])
    # W10: the top
    base = tempfile.mkdtemp(prefix="gw10-", dir=work)
    top, outside = gw_tree(base)
    before = modes(top)
    link = os.path.join(base, "acct-link")
    os.symlink(top, link)
    rc, out, err = work_run(link)
    row("W10 refuse when the account directory is a link: exit 2, REFUSED, nothing changed", rc == 2 and "REFUSED" in err and modes(top) == before, "rc=%d %s" % (rc, err.strip()[-160:]))
    other_gid = second_group()
    rc, out, err = work_run(top, g=other_gid if other_gid is not None else gid + 1)
    row("W11 refuse when the account directory's group is not the one given: exit 2, nothing changed", rc == 2 and "REFUSED" in err and modes(top) == before, "rc=%d %s" % (rc, err.strip()[-160:]))
    rc, out, err = work_run(os.path.join(base, "no-such-dir"))
    row("W12 refuse a directory that is not there: exit 2", rc == 2 and "REFUSED" in err, "rc=%d %s" % (rc, err.strip()[-160:]))


# the work's own mutants: each must make a row above fail
GW_WORKER_MUTANTS = [
    ("worker: the file open follows links", "os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_NOCTTY, dir_fd=dirfd", "os.O_RDONLY | os.O_NONBLOCK | os.O_NOCTTY, dir_fd=dirfd"),
    ("worker: the directory is opened without O_NOFOLLOW", "os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW", "os.O_RDONLY | os.O_DIRECTORY"),
    ("worker: a file of another group or owner is changed", "stat.S_ISREG(fst.st_mode) and ours(fst) and fst.st_dev == dev", "stat.S_ISREG(fst.st_mode) and fst.st_dev == dev"),
    ("worker: a fifo or a device is changed", "stat.S_ISREG(fst.st_mode) and ours(fst)", "ours(fst)"),
    ("worker: a directory of another group or owner is changed", "stat.S_ISDIR(dst.st_mode) and ours(dst)", "stat.S_ISDIR(dst.st_mode)"),
    ("worker: the owner is not looked at", "return st.st_gid == gid and st.st_uid in owners", "return st.st_gid == gid"),
    ("worker: the group is not looked at", "return st.st_gid == gid and st.st_uid in owners", "return st.st_uid in owners"),
    ("worker: a dry run changes the modes", "    if not dry:\n        os.fchmod(fd, new)", "    if True:\n        os.fchmod(fd, new)"),
    ("worker: directories get the other bits too", "D_BITS = stat.S_IRWXG | stat.S_ISGID", "D_BITS = stat.S_IRWXG | stat.S_ISGID | stat.S_IRWXO"),
    ("worker: directories do not get setgid", "D_BITS = stat.S_IRWXG | stat.S_ISGID", "D_BITS = stat.S_IRWXG"),
    ("worker: files get group execute", "F_BITS = stat.S_IRGRP | stat.S_IWGRP", "F_BITS = stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP"),
    ("worker: files get the other write bit", "F_BITS = stat.S_IRGRP | stat.S_IWGRP", "F_BITS = stat.S_IRGRP | stat.S_IWGRP | stat.S_IWOTH"),
    ("worker: the account directory's group is not checked", "if tst.st_gid != gid:\n    refuse(", "if False:\n    refuse("),
    ("worker: it goes down into a dictionary", "    dirnames[:] = []\n    if not (stat.S_ISDIR", "    if not (stat.S_ISDIR"),
    ("worker: any directory called voc is the VOC", "if dirpath == top or not (rel == \"voc\" or", "if dirpath == top or not (os.path.basename(dirpath) == \"voc\" or"),
    ("worker: any name ending c is a dictionary", "os.path.basename(dirpath).endswith(\".dic\"))", "os.path.basename(dirpath).endswith(\"c\"))"),
]

# the helper's own bash rules
GW_BASH_MUTANTS = [
    ("group-write: the account's own group is not required", "  [[ $dirgroup == \"$GW_GROUP\" ]] \\\n    || die", "  true \\\n    || die"),
    ("group-write: a group account is held to sdu_ too", "if [[ $kind == user_accounts ]]; then GW_GROUP=sdu_$ACCT_NAME; else GW_GROUP=sdg_$ACCT_NAME; fi",
     "GW_GROUP=sdu_$ACCT_NAME"),
    ("group-write: the group fixture is honoured on a real run", "if [[ $DRY -eq 1 && -n ${SD_GW_GROUP_FIXTURE:-} ]]; then GW_GROUP=$SD_GW_GROUP_FIXTURE; fi",
     "if [[ -n ${SD_GW_GROUP_FIXTURE:-} ]]; then GW_GROUP=$SD_GW_GROUP_FIXTURE; fi"),
    ("group-write: the directory is not checked as an account directory", "  local kind dirgroup sdsys_uid\n  account_dir_checked \"$1\"\n", "  local kind dirgroup sdsys_uid\n  ACCT_REAL=$1; ACCT_NAME=${1##*/}\n"),
    ("group-write: a second argument is accepted", "group-write)\n    [[ $# -eq 1 ]] || usage", "group-write)\n    [[ $# -ge 1 ]] || usage"),
]


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
    build_gw_fixture(os.path.join(root, "user_accounts", me), os.path.join(root, "group_accounts", "team"))   # 19 Oct 26: group-write's shapes
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
    for case in cases(root, me) + netcred_cases(root, me) + gw_cases(root, me):
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
    if second_group() is None:
        say("CANNOT RUN - this person is in no group but their primary one, so the group-write rows for a file of another group cannot be made")
        return 2
    work = tempfile.mkdtemp(prefix="accelev-")
    try:
        root = os.path.join(work, "sd")
        build_fixture(root, me)
        say("  fixture accounts root: %s\n" % root)
        suite(HELPER, root, me)
        gw_worker_suite(HELPER, work)
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
        ALL_MUTANTS = MUTANTS + GW_BASH_MUTANTS + GW_WORKER_MUTANTS
        for label, old, new in ALL_MUTANTS:
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
            gw_worker_suite(mp, work, quiet=True)
            red += R["fail"] > 0
            say("--- mutant '%s': %s" % (label, "RED as it must be" if R["fail"] else "STILL GREEN - the test misses it"))
        say("\nselftest: %d of %d mutants went red" % (red, len(ALL_MUTANTS)))
        return 0 if red == len(ALL_MUTANTS) else 1
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
