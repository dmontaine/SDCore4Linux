#!/usr/bin/env python3
"""Unit test for gplbld/sd-elevate, SD Core for Linux.

Written 09 Sep 26 for PRE_RELEASE 14.

26 Oct 26 dm F12 (the security review, route R-C: the helper's verbs reach more than their callers need): three families, each with mutants of its own and each row labelled ALLOW: (a caller's
argument list, still accepted) or REFUSE: - `stamp` (setpw, passwd and userdel want the "SD account" stamp, through a getent of the test's own on PATH), `chown-group` (chown-account's sdsys shape
takes only a group account's files, in its own group, on a scratch accounts root) and `groupadd` (sdu_<user> is made for an SD user that exists, holding root and that user).  The SD-user probe of
the older families is `_is_sd_user` (addgroup), not `passwd`, which asks the stamp now.  `--selftest --only=stamp,chown-group,groupadd` runs just those families.
26 Oct 26 dm F12b, F12c, F12e: `ownedby` (chown-account root sdusers takes only what the sdsys user owns - SD_SDSYS_UID_FIXTURE stands for its uid on a dry run - and the real run's worker FC_PY is run
here on scratch files), `pwunset` (setpw sets a first password only; the stub answers `getent shadow`) and `envtrust` (PATH is fixed; SD_ACCT_ROOT, SD_ACCARCHIVE and SD_PATH_PREPEND are read on a dry
run or from a process that is not root; root is played by `unshare -Ur` where allowed).  The getent stub is now put first by SD_PATH_PREPEND, not by PATH, which the helper no longer takes from
the caller.  `--selftest --only=ownedby,pwunset,envtrust` runs just those.
19 Oct 26 dm INTEGRATION of the S.67 rows below with 981a36a's record-file rows (record_rows, RECORD_MUTANTS): one run() that takes `env` and `dry`, and
one `--selftest` loop over the three families (group, record-file, sdsys-join) with _kill_mutants; a null guard on the record-file rows in the plain run too.
26 Oct 26 dm F6 (S.67 stage 2, alternative C): rows for `sdsys-leave` (leave_rows; who is in the group is read from a getent of the test's own put first on PATH),
the log lines of sdsys-join, sdsys-leave and group-write (log_rows, read off the helper's text), their mutants in `--selftest`, and `--selftest --only=FAMILY`.
19 Oct 26 dm S.67 stage 2 (D7): rows for `sdsys-join` (sdsys_rows), the one verb that puts the sdsys user into a group - only sdu_<user>, only for
an existing SD user, only an existing group - with their own mutants in `--selftest` (SDSYS_MUTANTS).
17 Oct 26 dm S.65 slice 2c: rows for the route group sdfiles (group_rows) and
`--selftest`, which runs them against eight mutated copies of the helper.
18 Oct 26 dm S.65 write group: the same rows for sdfileswrite, lookalike names, and three more mutants (eleven in all).
21 Oct 26 dm S.73 item 3: the same rows for sdfilesadmin (the fifth route group), its lookalike names, and three more mutants (fourteen in all).

WHAT IT IS FOR.  sd-elevate is the one command the sdsys user (SD's
administrator) may run as root, so everything that stops that being a root
shell lives in its argument validation.  This drives that validation through
--dry-run, which acts on nothing and needs no privilege, so the escalation
attempts below can be run safely as an ordinary user.

THE TWO HALVES MATTER EQUALLY.  The REFUSE rows are the point of the helper.
The ALLOW rows are the control: a script that refused everything would pass
every REFUSE row and be useless, and that failure mode is invisible without
them.  This is CLAUDE.md's rule that a test which passes because it did nothing
must fail - so the run REFUSES ITS OWN NULL CASE at the bottom if either half
is empty, or if the helper is missing, rather than reporting 0 of 0 as success.
"""

import os
import shlex
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HELPER = os.path.join(HERE, "sd-elevate")

ALLOW, REFUSE = "ALLOW", "REFUSE"


def run(args, helper=None, env=None, dry=True, stdin=None):
    """Run the helper in dry-run mode.  Returns (exit_code, stdout+stderr).

    `helper` is a mutated copy when --selftest drives the group rows.  `env` is added to the environment (a fixture the helper honours on a
    dry run only: SD_ACCT_ROOT for the record-file rows, SD_GROUP_FIXTURE and SD_GW_GROUP_FIXTURE for the sdsys group rows); `dry` False runs
    the helper WITHOUT --dry-run, which as an ordinary user can only refuse (its checks come before its test for root) - the rows that need
    to see a fixture ignored use it."""
    e = dict(os.environ)
    for k in ("SD_GROUP_FIXTURE", "SD_GW_GROUP_FIXTURE", "STUB_GROUPS", "STUB_MEMBERS", "STUB_PW_USER", "STUB_PW_GECOS", "STUB_LOG", "STUB_SHADOW_HASH", "STUB_SHADOW_SET",
              "STUB_SHADOW_FAIL", "SD_PATH_PREPEND", "SD_SDSYS_UID_FIXTURE", "SD_ACCARCHIVE"):
        e.pop(k, None)                      # nothing leaks in; a row sets what it needs
    e.update(env or {})
    p = subprocess.run(
        ["bash", helper or HELPER] + (["--dry-run"] if dry else []) + args,
        capture_output=True, text=True, env=e, input=stdin,
    )
    return p.returncode, (p.stdout or "") + (p.stderr or "")


# ---- 17 Oct 26, S.65 slice 2c: THE ROUTE GROUPS, asked without asking the
# ---- machine.  sdfiles is the SDNet files-only API route, a third group beside
# ---- sdssh and sdapi.  Whether it exists on this box depends on whether an
# ---- install has made it, so no row asserts the helper CREATES it; each row
# ---- asserts the REASON, which is the whitelist's own sentence:
# ----   "not an SD group"          the name is not on the whitelist
# ----   "never deleted here"       the group is a system group, not destroyable
# ----   (anything else, or exit 0) the name was accepted
# ---- A user for addgroup/delgroup is the account running the test, if the
# ---- helper takes it as an SD user at all; otherwise those rows are SKIPPED
# ---- out loud and the groupadd / groupdel rows still run.
def _accepted(code, out):
    return ("not an SD group" not in out and "not a valid name" not in out
            and (code == 0 or "already exists" in out or "does not exist" in out))


def _name_refused(code, out):
    return code != 0 and "not an SD group" in out


def _undeletable(code, out):
    return code != 0 and "never deleted here" in out


def _bad_name(code, out):
    return code != 0 and "not a valid name" in out


def _is_sd_user(who, helper=None):
    """26 Oct 26, F12.  Returns (ok, first line of what the helper said).  Whether the helper takes `who` as an SD user (require_sd_user: it exists, is not root or sdsys and is above UID_MIN),
    asked through addgroup, which does not want the "SD account" stamp.  The rows used `passwd <who>` for this, which asks the stamp now, and a person's own login does not have it."""
    code, out = run(["addgroup", who, "sdusers"], helper)
    refused = ("never a target", "below UID_MIN", "has uid 0", "could not read a uid", "user '%s' does not exist" % who, "is not a valid name")
    first = out.strip().splitlines()[0] if out.strip() else "no output"
    return not any(t in out for t in refused), first


# Names that merely begin with, end with, or look like sdfiles.
NOT_SDFILES = ["sdfilesx", "sdfiles2", "sdfiles-x", "sdfile", "xsdfiles",
               # 18 Oct 26, S.65 write group: lookalikes of sdfileswrite
               "sdfileswrit", "sdfileswritex", "sdfileswrite2", "sdfileswrite-x", "xsdfileswrite",
               # 21 Oct 26, S.73 item 3: lookalikes of sdfilesadmin
               "sdfilesadmi", "sdfilesadminx", "sdfilesadmin2", "sdfilesadmin-x", "xsdfilesadmin",
               # 23 Oct 26, S.69 step 2: lookalikes of sdaiusers
               "sdaiuser", "sdaiusersx", "sdaiusers2", "sdaiusers-x", "xsdaiusers"]


def group_rows(helper=None):
    """Returns (rows, skipped).  A row is (label, ok, detail)."""
    import getpass
    rows = []
    skipped = []

    def ask(label, argv, check):
        code, out = run(argv, helper)
        first = out.strip().splitlines()[0] if out.strip() else "(no output)"
        rows.append((label, check(code, out), f"exit {code}: {first}"))

    who = getpass.getuser()
    is_sd, why_not = _is_sd_user(who, helper)
    if not is_sd:
        skipped.append(f"addgroup/delgroup: '{who}' is not an SD user here ({why_not})")
        who = None

    ask("groupadd sdfiles is on the whitelist", ["groupadd", "sdfiles"], _accepted)
    # 18 Oct 26, S.65 write group: sdfileswrite, the right to change files over the files-only route, is the fourth route group.
    ask("groupadd sdfileswrite is on the whitelist", ["groupadd", "sdfileswrite"], _accepted)
    # 21 Oct 26, S.73 item 3: sdfilesadmin, the right to administer files over the files-only route, is the fifth route group.
    ask("groupadd sdfilesadmin is on the whitelist", ["groupadd", "sdfilesadmin"], _accepted)
    # 23 Oct 26, S.69 step 2: sdaiusers, the right to use the AI provider's API, is the sixth.
    ask("groupadd sdaiusers is on the whitelist", ["groupadd", "sdaiusers"], _accepted)
    if who:
        ask("addgroup <me> sdfiles is on the whitelist", ["addgroup", who, "sdfiles"], _accepted)
        ask("delgroup <me> sdfiles is on the whitelist", ["delgroup", who, "sdfiles"], _accepted)
        ask("addgroup <me> sdfileswrite is on the whitelist", ["addgroup", who, "sdfileswrite"], _accepted)
        ask("delgroup <me> sdfileswrite is on the whitelist", ["delgroup", who, "sdfileswrite"], _accepted)
        ask("addgroup <me> sdfilesadmin is on the whitelist", ["addgroup", who, "sdfilesadmin"], _accepted)
        ask("delgroup <me> sdfilesadmin is on the whitelist", ["delgroup", who, "sdfilesadmin"], _accepted)
        ask("addgroup <me> sdaiusers is on the whitelist", ["addgroup", who, "sdaiusers"], _accepted)
        ask("delgroup <me> sdaiusers is on the whitelist", ["delgroup", who, "sdaiusers"], _accepted)
    for grp in ("sdfiles", "sdfileswrite", "sdfilesadmin", "sdaiusers", "sdusers", "sdssh", "sdapi"):
        ask(f"groupdel {grp} is never deleted", ["groupdel", grp], _undeletable)
    for bad in NOT_SDFILES:
        ask(f"groupadd {bad} is not an SD group", ["groupadd", bad], _name_refused)
        ask(f"groupdel {bad} is not an SD group", ["groupdel", bad], _name_refused)
        if who:
            ask(f"addgroup <me> {bad} is not an SD group", ["addgroup", who, bad], _name_refused)
            ask(f"delgroup <me> {bad} is not an SD group", ["delgroup", who, bad], _name_refused)
    ask("groupadd SDFILES is not a valid name (lower case only)", ["groupadd", "SDFILES"], _bad_name)
    return rows, skipped


# Each mutant is (name, old text, new text) applied to the helper's source; the
# old text must occur exactly once, or the selftest refuses.
_WL = "sdusers|sdssh|sdapi|sdfiles|sdfileswrite|sdfilesadmin|sdaiusers) : ;;"
_UD = "      sdusers|sdssh|sdapi|sdfiles|sdfileswrite|sdfilesadmin|sdaiusers)\n        die"
GROUP_MUTANTS = [
    ("sdfiles dropped from the whitelist", _WL, "sdusers|sdssh|sdapi|sdfileswrite|sdfilesadmin|sdaiusers) : ;;"),
    ("sdfiles matched as a prefix", _WL, "sdusers|sdssh|sdapi|sdfiles*|sdfileswrite|sdfilesadmin|sdaiusers) : ;;"),
    ("whitelist widened to sd*", _WL, "sdusers|sdssh|sdapi|sd*) : ;;"),
    ("whitelist refuses nothing",
     "*) die \"'$group' is not an SD group", "*) : ;; # \"'$group' is not an SD group"),
    ("sdfiles made deletable", _UD, "      sdusers|sdssh|sdapi|sdfileswrite|sdfilesadmin|sdaiusers)\n        die"),
    ("sdapi made deletable", _UD, "      sdusers|sdssh|sdfiles|sdfileswrite|sdfilesadmin|sdaiusers)\n        die"),
    ("sdssh made deletable", _UD, "      sdusers|sdapi|sdfiles|sdfileswrite|sdfilesadmin|sdaiusers)\n        die"),
    ("sdusers made deletable", _UD, "      sdssh|sdapi|sdfiles|sdfileswrite|sdfilesadmin|sdaiusers)\n        die"),
    # 18 Oct 26, S.65 write group
    ("sdfileswrite dropped from the whitelist", _WL, "sdusers|sdssh|sdapi|sdfiles|sdfilesadmin|sdaiusers) : ;;"),
    ("sdfileswrite matched as a prefix", _WL, "sdusers|sdssh|sdapi|sdfiles|sdfileswrite*|sdfilesadmin|sdaiusers) : ;;"),
    ("sdfileswrite made deletable", _UD, "      sdusers|sdssh|sdapi|sdfiles|sdfilesadmin|sdaiusers)\n        die"),
    # 21 Oct 26, S.73 item 3: the fifth route group
    ("sdfilesadmin dropped from the whitelist", _WL, "sdusers|sdssh|sdapi|sdfiles|sdfileswrite|sdaiusers) : ;;"),
    ("sdfilesadmin matched as a prefix", _WL, "sdusers|sdssh|sdapi|sdfiles|sdfileswrite|sdfilesadmin*|sdaiusers) : ;;"),
    ("sdfilesadmin made deletable", _UD, "      sdusers|sdssh|sdapi|sdfiles|sdfileswrite|sdaiusers)\n        die"),
    # 23 Oct 26, S.69 step 2: the sixth, the right to use the AI provider's API
    ("sdaiusers dropped from the whitelist", _WL, "sdusers|sdssh|sdapi|sdfiles|sdfileswrite|sdfilesadmin) : ;;"),
    ("sdaiusers matched as a prefix", _WL, "sdusers|sdssh|sdapi|sdfiles|sdfileswrite|sdfilesadmin|sdaiusers*) : ;;"),
    ("sdaiusers made deletable", _UD, "      sdusers|sdssh|sdapi|sdfiles|sdfileswrite|sdfilesadmin)\n        die"),
]


# ---- 19 Oct 26, the group-account warning seen in the w21 witness: `create.account group witg` printed
# ---- "Unable change ownership of directory error .../voc/%1 err: 0" four times, and the four files (voc/%0, voc/%1,
# ---- $hold.dic/%0, $hold.dic/%1) stayed sdsys:sdusers 664, writable by every SD user.  chown-account's sdsys shape went through
# ---- require_sd_path, which is also setgid's check and wants a DIRECTORY; the user shape had no such rule, so a user account's
# ---- same four files were chowned without complaint.  The rows run against a scratch accounts root (SD_ACCT_ROOT) so they need
# ---- no install, and each REFUSE names the reason the helper must give, because "is not a directory" is what it said before.
def record_rows(helper=None):
    """Returns (rows, skipped).  A row is (label, ok, detail)."""
    rows = []
    td = tempfile.mkdtemp(prefix="sdelev-rec-")
    try:
        root = os.path.realpath(td)
        acc = os.path.join(root, "sd", "group_accounts", "probe")
        outside = os.path.join(root, "outside")
        dirs = {n: os.path.join(acc, n) for n in ("voc", "$hold.dic", "lnk", "lnk2", "hl")}
        for d in list(dirs.values()) + [outside]:
            os.makedirs(d)

        def touch(path):
            with open(path, "w", encoding="utf-8") as f:
                f.write("x")
        for d in ("voc", "$hold.dic"):
            for n in ("%0", "%1"):
                touch(os.path.join(dirs[d], n))
        touch(os.path.join(dirs["voc"], "readme"))
        touch(os.path.join(dirs["voc"], "%2"))
        touch(os.path.join(outside, "%0"))
        touch(os.path.join(outside, "secret"))
        touch(os.path.join(acc, "hlsrc"))
        os.symlink(os.path.join(outside, "secret"), os.path.join(dirs["lnk"], "%0"))
        os.symlink(os.path.join(dirs["voc"], "readme"), os.path.join(dirs["lnk2"], "%1"))
        os.link(os.path.join(acc, "hlsrc"), os.path.join(dirs["hl"], "%0"))
        env = {"SD_ACCT_ROOT": os.path.join(root, "sd")}

        def ask(label, argv, check):
            code, out = run(argv, helper, env)
            first = out.strip().splitlines()[0] if out.strip() else "(no output)"
            rows.append((label, check(code, out), f"exit {code}: {first}"))

        def allowed(real):
            return lambda code, out: code == 0 and f"chown -- sdsys:sdg_probe {real}" in out

        def refused(reason):
            return lambda code, out: code != 0 and "REFUSED" in out and reason in out

        grp = "sdg_probe"
        for rel, why in (("", "the group account's directory (control: always allowed)"),
                         ("voc", "its voc directory (control)"),
                         ("voc/%0", "voc/%0, a dictionary record file"),
                         ("voc/%1", "voc/%1, the file the witness named"),
                         ("$hold.dic/%0", "$hold.dic/%0"),
                         ("$hold.dic/%1", "$hold.dic/%1")):
            path = os.path.join(acc, rel) if rel else acc
            ask(f"sdsys chowns {why}", ["chown-account", "sdsys", grp, path], allowed(path))
        ask("a file with any other name is refused: only %0 and %1",
            ["chown-account", "sdsys", grp, os.path.join(dirs["voc"], "readme")], refused("only the dictionary record files"))
        ask("a file called %2 is refused: the names are %0 and %1, not a pattern",
            ["chown-account", "sdsys", grp, os.path.join(dirs["voc"], "%2")], refused("only the dictionary record files"))
        ask("a file outside the accounts root is refused even when it is called %0",
            ["chown-account", "sdsys", grp, os.path.join(outside, "%0")], refused("outside the accounts root"))
        ask("a %0 that is a symlink to a file outside the root is refused",
            ["chown-account", "sdsys", grp, os.path.join(dirs["lnk"], "%0")], refused("outside the accounts root"))
        ask("a %1 that is a symlink to a file with another name is refused",
            ["chown-account", "sdsys", grp, os.path.join(dirs["lnk2"], "%1")], refused("only the dictionary record files"))
        ask("a %0 with a second hard link is refused",
            ["chown-account", "sdsys", grp, os.path.join(dirs["hl"], "%0")], refused("more than one hard link"))
        ask("setgid still wants a directory: a record file is refused (the other user of the shared check)",
            ["setgid", os.path.join(dirs["voc"], "%0")], refused("is not a directory"))
    finally:
        shutil.rmtree(td, ignore_errors=True)
    return rows, []


_ONLYDIR = "  [[ -d $real ]] || die \"path '$real' is not a directory\"\n"
RECORD_MUTANTS = [
    ("files refused again (directories only)",
     "  [[ -f $real ]] || die \"path '$real' is neither a directory nor a file\"\n", "  die \"path '$real' is not a directory\"\n"),
    ("any regular file accepted", "    %0|%1) : ;;\n", "    *) : ;;\n"),
    ("the names widened to %*", "    %0|%1) : ;;\n", "    %*) : ;;\n"),
    ("the hard link check removed",
     "  [[ $(stat -c %h -- \"$real\") == 1 ]] || die \"path '$real' has more than one hard link\"\n", "  :\n"),
    ("the accounts-root check removed",
     "  [[ $real == \"$root\"/* ]] || die \"path '$real' is outside the accounts root '$root'\"\n", "  :\n"),
    ("chown-account's sdsys shape back on the directory check",
     "      require_sd_chown_path \"$path\"\n", "      require_sd_path \"$path\"\n"),
    ("setgid made to accept a file", _ONLYDIR, _ONLYDIR.replace("-d", "-e", 1)),
]


# ---- 19 Oct 26, S.67 stage 2 (D7): sdsys-join.  THE ONE VERB THAT PUTS THE sdsys USER INTO A GROUP.  The owner chose that sdsys is a member of
# ---- every account's group so that SDSYS can write a master edit into an account's own file; this is the whole of what the helper allows toward
# ---- it.  The REFUSE rows are run with SD_GROUP_FIXTURE naming every group they use, so that the ONLY thing which can refuse them is the rule
# ---- under test (a group that does not exist would refuse them all, and a rule removed would go unnoticed).  The one row that asks whether the
# ---- group exists uses a user whose sdu_ group is NOT on this machine, found rather than assumed: this box may have an SD install, and
# ---- sdu_<you> may be a real group here.
def _reason(code, out, text):
    return code != 0 and text in out


def _no_group_user():
    """An existing account the helper accepts as an SD user whose sdu_<name> group is not on this machine, or None."""
    import grp
    import pwd
    for p in sorted(pwd.getpwall(), key=lambda p: p.pw_uid):
        if p.pw_name in ("root", "sdsys") or p.pw_uid < 1000 or not p.pw_name[:1].isalpha() or p.pw_name != p.pw_name.lower() or len(p.pw_name) > 27:
            continue
        if not p.pw_name.replace("_", "a").replace("-", "a").isalnum():
            continue
        try:
            grp.getgrnam("sdu_" + p.pw_name)
        except KeyError:
            return p.pw_name
    return None


def sdsys_rows(helper=None):
    """Returns (rows, skipped).  A row is (label, ok, detail)."""
    import getpass
    rows = []
    skipped = []

    def ask(label, argv, check, env=None, dry=True):
        code, out = run(argv, helper, env=env, dry=dry)
        first = out.strip().splitlines()[0] if out.strip() else "(no output)"
        rows.append((label, check(code, out), f"exit {code}: {first}"))

    who = getpass.getuser()
    is_sd, why_not = _is_sd_user(who, helper)
    if not is_sd:
        skipped.append(f"sdsys-join: '{who}' is not an SD user here ({why_not})")
        return rows, skipped
    every = ",".join(["sdusers", "sdssh", "sdapi", "sdfiles", "sdfileswrite", "sdfilesadmin", "sdg_probe", "sudo", "wheel", "docker", "lxd", "adm", "root", "sdu_",
                      "sdu_root", "sdu_sdsys", "sdu_daemon", "sdu_zzprobenouser", "sdu_-rf", "sdu_" + who])
    fx = {"SD_GROUP_FIXTURE": every}
    mine = "sdu_" + who

    # ---- ALLOW: the control.  A helper that refused everything would pass every REFUSE row below.
    ask(f"sdsys-join {mine} is accepted (its group exists)", ["sdsys-join", mine],
        lambda c, o: c == 0 and f"usermod -aG {mine} -- sdsys" in o, fx)
    ask("...and the command it resolves puts sdsys, and only sdsys, in the group: usermod -aG GROUP -- sdsys", ["sdsys-join", mine],
        lambda c, o: c == 0 and o.strip().splitlines()[-1].endswith(" -aG %s -- sdsys" % mine) and " -G " not in o, fx)
    ask("...whoever asked: SUDO_USER and USER set to somebody else change nothing (the user is written in the helper, not taken from the environment)",
        ["sdsys-join", mine], lambda c, o: c == 0 and o.strip().splitlines()[-1].endswith(" -aG %s -- sdsys" % mine) and "attacker" not in o,
        dict(fx, SUDO_USER="attacker", USER="attacker", LOGNAME="attacker"))
    # ---- REFUSE: groups that are not an account's own.  The reason is the rule's own sentence.
    for g in ("sdusers", "sdssh", "sdapi", "sdfiles", "sdfileswrite", "sdfilesadmin"):
        ask(f"sdsys-join {g} is refused: SD's own groups are not account groups", ["sdsys-join", g],
            lambda c, o: _reason(c, o, "is not an account group"), fx)
    ask("sdsys-join sdg_probe is refused: a group account's group is made with sdsys in it, and is not this verb's", ["sdsys-join", "sdg_probe"],
        lambda c, o: _reason(c, o, "is not an account group"), fx)
    for g in ("sudo", "wheel", "docker", "lxd", "adm", "root"):
        ask(f"sdsys-join {g} is refused: not one of SD's groups", ["sdsys-join", g], lambda c, o: _reason(c, o, "is not an account group"), fx)
    ask("sdsys-join sdu_ (no user) is refused", ["sdsys-join", "sdu_"], lambda c, o: _reason(c, o, "is not an account group"), fx)
    # ---- REFUSE: the user part must be an SD user
    ask("sdsys-join sdu_root is refused: root is never a target", ["sdsys-join", "sdu_root"], lambda c, o: _reason(c, o, "root is never a target"), fx)
    ask("sdsys-join sdu_sdsys is refused: sdsys is SD's own administrator account (it joins no group of its own name)", ["sdsys-join", "sdu_sdsys"],
        lambda c, o: _reason(c, o, "sdsys is SD's own administrator account"), fx)
    ask("sdsys-join sdu_daemon is refused: a system account (below UID_MIN) or no such user", ["sdsys-join", "sdu_daemon"],
        lambda c, o: _reason(c, o, "below UID_MIN") or _reason(c, o, "does not exist"), fx)
    ask("sdsys-join sdu_zzprobenouser is refused: there is no such user", ["sdsys-join", "sdu_zzprobenouser"],
        lambda c, o: _reason(c, o, "does not exist"), fx)
    ask("sdsys-join sdu_-rf is refused: a leading dash in the user part would read as an option", ["sdsys-join", "sdu_-rf"],
        lambda c, o: _reason(c, o, "is not a valid name"), fx)
    ask("sdsys-join -rf is refused: a leading dash", ["sdsys-join", "-rf"], lambda c, o: _reason(c, o, "is not a valid name"), fx)
    ask("sdsys-join SDU_%s is refused: upper case is not a valid name" % who.upper(), ["sdsys-join", "SDU_" + who.upper()],
        lambda c, o: _reason(c, o, "is not a valid name"), fx)
    ask("sdsys-join with no group is refused", ["sdsys-join"], lambda c, o: _reason(c, o, "privileged helper"), fx)
    ask("sdsys-join takes one group: a second argument is refused (the user is never an argument)", ["sdsys-join", mine, "don"],
        lambda c, o: _reason(c, o, "privileged helper"), fx)
    ask("sdsys-join takes one group: sdsys cannot be named a second time as 'the user'", ["sdsys-join", "sdsys", mine],
        lambda c, o: _reason(c, o, "privileged helper"), fx)
    # ---- the group must exist, and the fixture is for a dry run only
    nogrp = _no_group_user()
    if nogrp is None:
        skipped.append("sdsys-join: every ordinary user on this machine has an sdu_ group, so the 'group does not exist' rows are left out")
    else:
        ask(f"sdsys-join sdu_{nogrp} is refused when sdu_{nogrp} is not a group on this machine", ["sdsys-join", "sdu_" + nogrp],
            lambda c, o: _reason(c, o, "does not exist"))
        ask(f"a fixture naming sdu_{nogrp} is honoured on a dry run", ["sdsys-join", "sdu_" + nogrp],
            lambda c, o: c == 0 and f"usermod -aG sdu_{nogrp} -- sdsys" in o, {"SD_GROUP_FIXTURE": "sdu_" + nogrp})
        ask(f"...and IGNORED when the run is not a dry run (the group is still not there; the helper refuses before it asks for root)",
            ["sdsys-join", "sdu_" + nogrp], lambda c, o: _reason(c, o, "does not exist"), {"SD_GROUP_FIXTURE": "sdu_" + nogrp}, dry=False)
    return rows, skipped


SDSYS_MUTANTS = [
    ("the account-group pattern widened to sd*", "[[ $group == sdu_?* ]] || die \"'$group' is not an account group", "[[ $group == sd* ]] || die \"'$group' is not an account group"),
    ("sdg_ groups accepted too", "[[ $group == sdu_?* ]] || die \"'$group' is not an account group", "[[ $group == sd[ug]_?* ]] || die \"'$group' is not an account group"),
    ("the pattern test gone", "[[ $group == sdu_?* ]] || die \"'$group' is not an account group", "true || die \"'$group' is not an account group"),
    ("the user part is not checked as an SD user", "  user=${group#sdu_}\n  require_sd_user \"$user\"\n", "  user=${group#sdu_}\n"),
    ("the group need not exist", "  group_exists \"$group\" || die \"group '$group' does not exist\"\n", ""),
    ("the group name is not checked", "  require_name \"group\" \"$group\"\n  [[ $group == sdu_?* ]]", "  [[ $group == sdu_?* ]]"),
    ("the user is taken from the caller", "cmd=(usermod -aG \"$1\" -- sdsys)", "cmd=(usermod -aG \"$1\" -- \"${SUDO_USER:-sdsys}\")"),
    ("the group is REPLACED, not added to (usermod -G)", "cmd=(usermod -aG \"$1\" -- sdsys)", "cmd=(usermod -G \"$1\" -- sdsys)"),
    ("a second argument is accepted", "sdsys-join)\n    [[ $# -eq 1 ]] || usage", "sdsys-join)\n    [[ $# -ge 1 ]] || usage"),
    ("the group fixture is honoured on a real run too", "if [[ $DRY -eq 1 && -n ${SD_GROUP_FIXTURE:-} ]]; then\n    [[ \",$SD_GROUP_FIXTURE,\"",
     "if [[ -n ${SD_GROUP_FIXTURE:-} ]]; then\n    [[ \",$SD_GROUP_FIXTURE,\""),
]


# ---- 26 Oct 26, F6 (S.67 stage 2, alternative C): sdsys-leave.  THE OTHER HALF OF sdsys-join: it takes the sdsys user OUT of an account's group, so that sdsys
# ---- is in no user account's group as delivered and `modify.account <name> sdsys-on` is a deliberate act.  Who is in the group is asked of getent (field 4
# ---- of the group entry), on a dry run too, so a getent of this test's own is put first on PATH: it answers `getent group NAME` for the names in
# ---- STUB_GROUPS with the members in STUB_MEMBERS and passes every other question to the real one.  The REFUSE rows give sdsys as a member, so that
# ---- "sdsys is not in the group" can never be what refuses them (that answer is exit 0), and a rule removed shows as a gpasswd line.
def _getent_stub(td):
    path = os.path.join(td, "getent")
    real = shutil.which("getent") or "/usr/bin/getent"
    with open(path, "w", encoding="utf-8") as f:
        f.write("#!/bin/bash\n"
                # 26 Oct 26, F12e: STUB_LOG names a file this stub appends its arguments to, so that a row can show the stub WAS (or was not) reached
                '[[ -z ${STUB_LOG:-} ]] || echo "$*" >> "$STUB_LOG"\n'
                'if [[ $1 == group && ",${STUB_GROUPS:-}," == *",$2,"* ]]; then echo "$2:x:54321:${STUB_MEMBERS:-}"; exit 0; fi\n'
                # 26 Oct 26, F12c: `getent shadow USER` for the one user STUB_PW_USER: field 2 is STUB_SHADOW_HASH (STUB_SHADOW_FAIL set: exit 2, as getent does when it may not read shadow)
                'if [[ $1 == shadow && -n ${STUB_SHADOW_FAIL:-} ]]; then exit 2; fi\n'
                'if [[ $1 == shadow && -n ${STUB_PW_USER:-} && $2 == "$STUB_PW_USER" && -n ${STUB_SHADOW_SET:-} ]]; then echo "$2:${STUB_SHADOW_HASH-}:19000:0:99999:7:::"; exit 0; fi\n'
                # 26 Oct 26, F12: `getent passwd USER` for the one user STUB_PW_USER, with the comment STUB_PW_GECOS (uid and gid are the real ones, so only the stamp can differ)
                'if [[ $1 == passwd && -n ${STUB_PW_USER:-} && $2 == "$STUB_PW_USER" ]]; then echo "$2:x:$(id -u "$2"):$(id -g "$2"):${STUB_PW_GECOS:-}:/home/$2:/bin/bash"; exit 0; fi\n'
                'exec %s "$@"\n' % real)
    os.chmod(path, 0o755)


def leave_rows(helper=None):
    """Returns (rows, skipped).  A row is (label, ok, detail)."""
    import getpass
    rows = []
    skipped = []

    def ask(label, argv, check, env=None, dry=True):
        code, out = run(argv, helper, env=env, dry=dry)
        first = out.strip().splitlines()[0] if out.strip() else "(no output)"
        rows.append((label, check(code, out), f"exit {code}: {first}"))

    who = getpass.getuser()
    is_sd, why_not = _is_sd_user(who, helper)
    if not is_sd or os.geteuid() == 0:
        skipped.append(f"sdsys-leave: '{who}' is not an SD user here, or this is root ({why_not})")
        return rows, skipped
    mine = "sdu_" + who
    td = tempfile.mkdtemp(prefix="sdelev-leave-")
    try:
        _getent_stub(td)
        names = ["sdusers", "sdssh", "sdapi", "sdfiles", "sdfileswrite", "sdfilesadmin", "sdg_probe", "sudo", "wheel", "docker", "lxd", "adm", "root", "sdu_",
                 "sdu_root", "sdu_sdsys", "sdu_daemon", "sdu_zzprobenouser", "sdu_-rf", mine]
        def env(members, groups=None, **more):
            e = {"SD_PATH_PREPEND": td, "STUB_GROUPS": ",".join(names if groups is None else groups), "STUB_MEMBERS": members}      # 26 Oct 26, F12e: the stub goes in SD_PATH_PREPEND; the helper fixes its own PATH
            e.update(more)
            return e

        def leaves(c, o):
            return c == 0 and o.strip().splitlines()[-1].endswith(" -d sdsys %s" % mine) and " -G " not in o and "usermod" not in o

        def stays(c, o):
            return c == 0 and ("sdsys is not in %s" % mine) in o and "gpasswd" not in o

        # ---- ALLOW: the control, and the membership read as a whole name from field 4
        ask(f"sdsys-leave {mine} is accepted when the group lists sdsys: gpasswd -d sdsys GROUP", ["sdsys-leave", mine], leaves, env("root,sdsys," + who))
        ask("...a group whose only member is sdsys", ["sdsys-leave", mine], leaves, env("sdsys"))
        ask("...sdsys the first member", ["sdsys-leave", mine], leaves, env("sdsys,root"))
        ask("...sdsys the last member", ["sdsys-leave", mine], leaves, env("root," + who + ",sdsys"))
        ask("...whoever asked: SUDO_USER and USER set to somebody else change nothing (the user is written in the helper, not taken from the environment)",
            ["sdsys-leave", mine], lambda c, o: leaves(c, o) and "attacker" not in o, env("root,sdsys", SUDO_USER="attacker", USER="attacker", LOGNAME="attacker"))
        ask("a group that does not list sdsys is left alone: exit 0, 'sdsys is not in GROUP', no gpasswd", ["sdsys-leave", mine], stays, env("root," + who))
        ask("...a group with no members at all", ["sdsys-leave", mine], stays, env(""))
        ask("...a member called sdsys2 is not sdsys (a whole name, not a prefix)", ["sdsys-leave", mine], stays, env("sdsys2,root"))
        ask("...a member called xsdsys is not sdsys (a whole name, not a suffix)", ["sdsys-leave", mine], stays, env("root,xsdsys"))
        # ---- REFUSE: groups that are not an account's own.  sdsys is a member of each, so only the rule can refuse.
        listed = "root,sdsys"
        for g in ("sdusers", "sdssh", "sdapi", "sdfiles", "sdfileswrite", "sdfilesadmin"):
            ask(f"sdsys-leave {g} is refused: SD's own groups are not account groups", ["sdsys-leave", g],
                lambda c, o: _reason(c, o, "is not an account group"), env(listed))
        ask("sdsys-leave sdg_probe is refused: a group account's group is not this verb's", ["sdsys-leave", "sdg_probe"],
            lambda c, o: _reason(c, o, "is not an account group"), env(listed))
        for g in ("sudo", "wheel", "docker", "lxd", "adm", "root"):
            ask(f"sdsys-leave {g} is refused: not one of SD's groups", ["sdsys-leave", g], lambda c, o: _reason(c, o, "is not an account group"), env(listed))
        ask("sdsys-leave sdu_ (no user) is refused", ["sdsys-leave", "sdu_"], lambda c, o: _reason(c, o, "is not an account group"), env(listed))
        ask("sdsys-leave sdu_root is refused: root is never a target", ["sdsys-leave", "sdu_root"], lambda c, o: _reason(c, o, "root is never a target"), env(listed))
        ask("sdsys-leave sdu_sdsys is refused: sdsys is SD's own administrator account", ["sdsys-leave", "sdu_sdsys"],
            lambda c, o: _reason(c, o, "sdsys is SD's own administrator account"), env(listed))
        ask("sdsys-leave sdu_daemon is refused: a system account (below UID_MIN) or no such user", ["sdsys-leave", "sdu_daemon"],
            lambda c, o: _reason(c, o, "below UID_MIN") or _reason(c, o, "does not exist"), env(listed))
        ask("sdsys-leave sdu_zzprobenouser is refused: there is no such user", ["sdsys-leave", "sdu_zzprobenouser"],
            lambda c, o: _reason(c, o, "does not exist"), env(listed))
        ask("sdsys-leave sdu_-rf is refused: a leading dash in the user part would read as an option", ["sdsys-leave", "sdu_-rf"],
            lambda c, o: _reason(c, o, "is not a valid name"), env(listed))
        ask("sdsys-leave -rf is refused: a leading dash", ["sdsys-leave", "-rf"], lambda c, o: _reason(c, o, "is not a valid name"), env(listed))
        ask("sdsys-leave SDU_%s is refused: upper case is not a valid name" % who.upper(), ["sdsys-leave", "SDU_" + who.upper()],
            lambda c, o: _reason(c, o, "is not a valid name"), env(listed))
        ask("sdsys-leave with no group is refused", ["sdsys-leave"], lambda c, o: _reason(c, o, "privileged helper"), env(listed))
        ask("sdsys-leave takes one group: a second argument is refused (the user is never an argument)", ["sdsys-leave", mine, "don"],
            lambda c, o: _reason(c, o, "privileged helper"), env(listed))
        ask("sdsys-leave takes one group: sdsys cannot be named a second time as 'the user'", ["sdsys-leave", "sdsys", mine],
            lambda c, o: _reason(c, o, "privileged helper"), env(listed))
        # ---- the group must exist (asked before the membership), and the group fixture is for a dry run only
        # these three need a group that is NOT on this machine (sdu_<you> may be a real group here), found rather than assumed
        nogrp = _no_group_user()
        if nogrp is None:
            skipped.append("sdsys-leave: every ordinary user on this machine has an sdu_ group, so the 'group does not exist' rows are left out")
        else:
            ng = "sdu_" + nogrp
            ask(f"sdsys-leave {ng} is refused when the group is not there ('sdsys is not in' is not the answer: the group is asked for first)", ["sdsys-leave", ng],
                lambda c, o: _reason(c, o, "does not exist") and "sdsys is not in" not in o, env("root,sdsys", groups=[]))
            ask("a group fixture is honoured on a dry run: the group exists, and lists nobody", ["sdsys-leave", ng],
                lambda c, o: c == 0 and ("sdsys is not in %s" % ng) in o and "gpasswd" not in o, env("", groups=[], SD_GROUP_FIXTURE=ng))
            ask("...and IGNORED when the run is not a dry run (the group is still not there; the helper refuses before it asks for root)", ["sdsys-leave", ng],
                lambda c, o: _reason(c, o, "does not exist"), env("root,sdsys", groups=[], SD_GROUP_FIXTURE=ng), dry=False)
        # ---- a run that is not a dry run, as an ordinary user, goes as far as the command and then refuses to be anyone but root: nothing is changed
        try:
            import pwd
            pwd.getpwnam("sdsys")
            have_sdsys = True
        except KeyError:
            have_sdsys = False
        ask("a real run by an ordinary user prints the command and is refused for want of root (the membership was seen, nothing is changed)",
            ["sdsys-leave", mine],
            lambda c, o: c != 0 and (("gpasswd -d sdsys %s" % mine in o and "must run as root" in o) if have_sdsys else "the user sdsys does not exist" in o),
            env("root,sdsys"), dry=False)
        ask("...and a real run for a group that does not list sdsys changes nothing and asks for no root", ["sdsys-leave", mine], stays, env("root"), dry=False)
    finally:
        shutil.rmtree(td, ignore_errors=True)
    return rows, skipped


_LEAVE_BRANCH = "    require_account_group \"$1\"\n    if ! group_lists_sdsys \"$1\"; then\n"
LEAVE_MUTANTS = [
    ("leave: the user is taken from the caller", "cmd=(gpasswd -d sdsys \"$1\")", "cmd=(gpasswd -d \"${SUDO_USER:-sdsys}\" \"$1\")"),
    ("leave: usermod -G replaces the whole group list", "cmd=(gpasswd -d sdsys \"$1\")", "cmd=(usermod -G \"\" -- sdsys)"),
    ("leave: the account-group rule is skipped", _LEAVE_BRANCH, "    if ! group_lists_sdsys \"$1\"; then\n"),
    ("leave: sdusers and the route groups accepted (require_sd_group)", _LEAVE_BRANCH, "    require_sd_group \"$1\"\n    if ! group_lists_sdsys \"$1\"; then\n"),
    ("leave: sdu_root and a leading dash accepted (a pattern test only)", _LEAVE_BRANCH,
     "    [[ $1 == sdu_?* ]] || die \"'$1' is not an account group\"\n    if ! group_lists_sdsys \"$1\"; then\n"),
    ("leave: a group that does not list sdsys is still changed", "    if ! group_lists_sdsys \"$1\"; then\n", "    if false; then\n"),
    ("leave: sdsys matched anywhere in the member list", "[[ \",$members,\" == *\",sdsys,\"* ]]", "[[ \"$members\" == *sdsys* ]]"),
    ("leave: the member list is read from the wrong field", "cut -d: -f4)\n  [[ \",$members,\"", "cut -d: -f1)\n  [[ \",$members,\""),
    ("leave: the group need not exist", "  group_exists \"$group\" || die \"group '$group' does not exist\"\n", ""),
    ("leave: a second argument is accepted", "sdsys-leave)\n    [[ $# -eq 1 ]] || usage", "sdsys-leave)\n    [[ $# -ge 1 ]] || usage"),
    ("leave: the group fixture is honoured on a real run too", "if [[ $DRY -eq 1 && -n ${SD_GROUP_FIXTURE:-} ]]; then\n    [[ \",$SD_GROUP_FIXTURE,\"",
     "if [[ -n ${SD_GROUP_FIXTURE:-} ]]; then\n    [[ \",$SD_GROUP_FIXTURE,\""),
]


# ---- 26 Oct 26, F6: the log lines.  sdsys-join, sdsys-leave and group-write left no trace of their own (the helper's sudo line says only that it ran);
# ---- each now writes one line with `logger -t sd-elevate` AFTER the change was made, never on a dry run and never for a group that was already right,
# ---- and a missing logger cannot fail the change.  A root run cannot be made here, so the rows read the helper's text: where the line is, what it
# ---- says, what precedes it.
def log_rows(helper=None):
    """Returns (rows, skipped).  A row is (label, ok, detail)."""
    import re
    src = open(helper or HELPER, encoding="utf-8").read()
    rows = []

    def branch(verb):
        m = re.search(r"\n  %s\)\n(.*?)\n    ;;\n" % re.escape(verb), src, re.S)
        return m.group(1) if m else ""
    join, leave, gw = branch("sdsys-join"), branch("sdsys-leave"), branch("group-write")
    run_at = src.find('"${cmd[@]}" || exit $?')
    tail_log = 'logger -t sd-elevate "$LOG_LINE" 2>/dev/null || true'
    rows.append(("LG0 the three branches are found (a test that did nothing must fail)", bool(join and leave and gw and run_at > 0), f"{len(join)} {len(leave)} {len(gw)} {run_at}"))
    rows.append(("LG1 sdsys-join sets its log line, and it begins 'sdsys-join:'", 'LOG_LINE="sdsys-join: ' in join, join[-120:]))
    rows.append(("LG2 sdsys-leave sets its log line, and it begins 'sdsys-leave:'", 'LOG_LINE="sdsys-leave: ' in leave, leave[-120:]))
    rows.append(("LG3 the log line names the group and no caller: SUDO_USER is not in either branch or in the tail's line",
                 "SUDO_USER" not in join + leave and "SUDO_USER" not in tail_log and "$1" in join and "$1" in leave, ""))
    k = leave.find("LOG_LINE=")
    rows.append(("LG4 sdsys-leave answers 'sdsys is not in GROUP' and exits 0 BEFORE it sets a log line: nothing is logged when nothing changed",
                 0 < leave.find("sdsys is not in") < leave.find("exit 0") < k, leave[:200]))
    first = src.find('logger -t sd-elevate "$LOG_LINE"')
    rows.append(("LG5 the tail writes the line AFTER the command ran (the first LOG_LINE logger comes after the command, and ends the run before exit 0)",
                 run_at > 0 and first > run_at and src.count('logger -t sd-elevate "$LOG_LINE"') == 1 and src.rstrip().endswith("exit 0") and first < src.rfind("\nexit 0"), ""))
    rows.append(("LG6 a missing or failing logger cannot fail the change: the tail's line ends 2>/dev/null || true", tail_log in src, ""))
    p = gw.find('python3 -I -c "$GW_PY"')
    g = gw.find('logger -t sd-elevate "group-write: ')
    rows.append(("LG7 group-write writes its line after the worker ran, and only when the worker succeeded (|| exit $? before the logger)",
                 0 < p < g and 'python3 -I -c "$GW_PY" "$ACCT_REAL" "$GW_GID" "$GW_OWNERS" "$DRY" || exit $?\n' in gw, gw[-200:]))
    rows.append(("LG8 group-write does not write the line on a dry run, and a failing logger cannot fail it",
                 "[[ $DRY -eq 1 ]] || logger -t sd-elevate \"group-write: " in gw and gw.rstrip().endswith("exit 0") and "2>/dev/null || true" in gw[g:], gw[-200:]))
    return rows, []


LOG_MUTANTS = [
    ("log: the tail writes the line before the command", '"${cmd[@]}" || exit $?',
     '[[ -z ${LOG_LINE:-} ]] || logger -t sd-elevate "$LOG_LINE" 2>/dev/null || true\n"${cmd[@]}" || exit $?'),
    ("log: a failing logger fails the change", 'logger -t sd-elevate "$LOG_LINE" 2>/dev/null || true', 'logger -t sd-elevate "$LOG_LINE"'),
    ("log: sdsys-join logs under the wrong name", 'LOG_LINE="sdsys-join: ', 'LOG_LINE="sdsys-leave: '),
    ("log: sdsys-leave logs the caller", 'LOG_LINE="sdsys-leave: the user sdsys is no longer in $1"', 'LOG_LINE="sdsys-leave: the user sdsys is no longer in $1 (by $SUDO_USER)"'),
    ("log: group-write logs on a dry run too", '[[ $DRY -eq 1 ]] || logger -t sd-elevate "group-write: ', 'logger -t sd-elevate "group-write: '),
    ("log: group-write logs a failed run", 'python3 -I -c "$GW_PY" "$ACCT_REAL" "$GW_GID" "$GW_OWNERS" "$DRY" || exit $?\n',
     'python3 -I -c "$GW_PY" "$ACCT_REAL" "$GW_GID" "$GW_OWNERS" "$DRY"\n'),
    ("log: group-write's line is lost", '[[ $DRY -eq 1 ]] || logger -t sd-elevate "group-write: the VOC', '[[ $DRY -eq 1 ]] || : "group-write: the VOC'),
]


# ---- 26 Oct 26, F12 (the security review of 24-26 Oct 26, route R-C: sdsys may run the helper with ANY arguments, so each verb is a wall only as far as its own checks go).
# ---- Three families, each with mutants of its own; every row's label begins ALLOW: (a caller's argument list, which must still be accepted) or REFUSE: (what the review found
# ---- accepted and no caller sends).  A REFUSE row names the helper's own words, never a bare exit status, and each is built so that only the rule under test can refuse it.
# ----   stamp       setpw, passwd and userdel act only on a user whose comment is "SD account" (userdel-home always did).  The helper asks `getent passwd USER`, so a getent of this
# ----               test's own is first on PATH (_getent_stub): for the one user STUB_PW_USER it answers with the comment STUB_PW_GECOS and the real uid and gid, which leaves the stamp
# ----               as the only thing that can differ between a row that goes through and one that is refused.  The user is whoever runs this.
# ----   chown-group chown-account's sdsys shape takes only the files of a GROUP account, in that account's own group (sdg_<name>; sdusers for shared), on a scratch accounts root.
# ----   groupadd    sdu_<user> is made only for an SD user that exists, with root and that user in it.
def stamp_rows(helper=None):
    """Returns (rows, skipped).  A row is (label, ok, detail)."""
    import getpass
    rows = []
    skipped = []
    who = getpass.getuser()
    is_sd, why_not = _is_sd_user(who, helper)
    if not is_sd or os.geteuid() == 0:
        skipped.append(f"stamp: '{who}' is not an SD user here, or this is root ({why_not})")
        return rows, skipped
    td = tempfile.mkdtemp(prefix="sdelev-stamp-")
    try:
        _getent_stub(td)
        def env(gecos, user=None, shadow="!"):
            # 26 Oct 26, F12c/F12e: the stub is put in front by SD_PATH_PREPEND; the user's shadow hash is "!" (locked, a first password may be set) unless a row says otherwise
            return {"SD_PATH_PREPEND": td, "STUB_PW_USER": user or who, "STUB_PW_GECOS": gecos, "STUB_SHADOW_SET": "1", "STUB_SHADOW_HASH": shadow}

        def ask(label, argv, check, e, stdin=None):
            code, out = run(argv, helper, env=e, stdin=stdin)
            first = out.strip().splitlines()[0] if out.strip() else "(no output)"
            rows.append((label, check(code, out), f"exit {code}: {first}"))

        def goes(needle):
            return lambda c, o: c == 0 and needle in o

        def stamp_refused(tail):
            return lambda c, o: c != 0 and "REFUSED" in o and "was not created by SD" in o and tail in o

        stamped, unstamped = env("SD account"), env("Some Person")
        good = "Abcdef1!\n"
        tails = {"passwd": "its password is never changed here", "userdel": "it is never deleted here", "setpw": "its Linux password is never set here",
                 "userdel-home": "its home is never removed here"}
        # ---- ALLOW: what the callers send, for a user that carries the stamp (the control: a helper that refused everything would pass every REFUSE row below)
        ask(f"ALLOW: passwd {who} goes through for a user with the stamp", ["passwd", who], goes(f"passwd -- {who}"), stamped)
        ask(f"ALLOW: userdel {who} goes through for a user with the stamp (create.account's unwind, delete.account)", ["userdel", who], goes(f"userdel -- {who}"), stamped)
        ask(f"ALLOW: setpw {who} goes through for a user with the stamp, a good password on stdin (create.account)", ["setpw", who], goes(f"chpasswd for {who}"), stamped, good)
        # ---- REFUSE: a user without the stamp, and every way of nearly having it
        for gecos, why in (("Some Person", "an ordinary login"), ("", "no comment at all"), ("SD account ", "a trailing space"), ("sd account", "lower case"),
                           ("SD Account", "another capital"), ("SD account,,,", "chfn's extra fields"), ("xSD account", "a prefix"), ("SD", "a part of it")):
            for verb in ("passwd", "userdel"):
                ask(f"REFUSE: {verb} {who} is refused for {why} ({gecos!r})", [verb, who], stamp_refused(tails[verb]), env(gecos))
            ask(f"REFUSE: setpw {who} is refused for {why} ({gecos!r}), with a good password on stdin", ["setpw", who], stamp_refused(tails["setpw"]), env(gecos), good)
        ask("REFUSE: userdel-home keeps its words (the stamp test it always made, now shared with the others)", ["userdel-home", who], stamp_refused(tails["userdel-home"]), unstamped)
        ask("REFUSE: setpw asks the stamp BEFORE it reads the password: a weak password for an out-of-reach user is refused for the stamp, and its text is not judged",
            ["setpw", who], lambda c, o: stamp_refused(tails["setpw"])(c, o) and "does not meet SD's rule" not in o, unstamped, "weakpass\n")
        # ---- the user rules come first, whatever the stamp says: root, sdsys and a system account keep their own words
        for verb in ("passwd", "userdel"):
            ask(f"REFUSE: {verb} root is refused as root even when the passwd database calls it stamped", [verb, "root"],
                lambda c, o: c != 0 and "root is never a target" in o and "was not created by SD" not in o, env("SD account", "root"))
            ask(f"REFUSE: {verb} sdsys is refused as SD's administrator even when the passwd database calls it stamped", [verb, "sdsys"],
                lambda c, o: c != 0 and "sdsys is SD's own administrator account" in o and "was not created by SD" not in o, env("SD account", "sdsys"))
            ask(f"REFUSE: {verb} root with no stub is refused as root, not for the stamp (the user rules are asked first)", [verb, "root"],
                lambda c, o: c != 0 and "root is never a target" in o and "was not created by SD" not in o, {})
        ask("REFUSE: setpw root is refused as root before the stamp or the password is looked at", ["setpw", "root"],
            lambda c, o: c != 0 and "root is never a target" in o and "was not created by SD" not in o, {}, good)
        ask("REFUSE: a user that does not exist is refused as not existing", ["passwd", "zzf12nouser"],
            lambda c, o: c != 0 and "does not exist" in o and "was not created by SD" not in o, {})
    finally:
        shutil.rmtree(td, ignore_errors=True)
    return rows, skipped


_SW = '  require_sd_stamp "$user" "its Linux password is never set here"\n'
_SP = '    require_sd_stamp "$1" "its password is never changed here"\n'
_SD = '    require_sd_stamp "$1" "it is never deleted here"\n'
_SH = '  require_sd_stamp "$user" "its home is never removed here"\n'
_PU = '  require_pw_unset "$user"\n'
_PWL = ('  IFS= read -r pw || die "setpw wants the password on stdin"\n  IFS= read -r extra && die "setpw wants exactly one line on stdin; there were more"\n'
        '  pw_complex "$pw" || die "the password does not meet SD\'s rule (10920): 8+ characters with a lower-case letter, an upper-case letter, a digit and a symbol"\n')
_GE = 'gecos=$(printf \'%s\\n\' "$ent" | cut -d: -f5)\n  [[ $gecos == "SD account" ]] || die "\'$user\' was not created by SD'
STAMP_MUTANTS = [
    ("stamp: setpw no longer asks it", _SW, ""),
    ("stamp: passwd no longer asks it", _SP, ""),
    ("stamp: userdel no longer asks it", _SD, ""),
    ("stamp: userdel-home no longer asks it", _SH, ""),
    ("stamp: a comment that only begins with it is enough", '[[ $gecos == "SD account" ]] || die "\'$user\' was not created by SD', '[[ $gecos == "SD account"* ]] || die "\'$user\' was not created by SD'),
    ("stamp: upper and lower case are the same", '[[ $gecos == "SD account" ]] || die "\'$user\' was not created by SD', '[[ ${gecos,,} == "sd account" ]] || die "\'$user\' was not created by SD'),
    ("stamp: the home field is read instead of the comment", _GE, _GE.replace("-f5", "-f6")),
    ("stamp: setpw asks it before the user rules", '  require_sd_user "$user"\n' + _SW, _SW + '  require_sd_user "$user"\n'),
    ("stamp: passwd asks it before the user rules", '    require_sd_user "$1"\n' + _SP, _SP + '    require_sd_user "$1"\n'),
    ("stamp: setpw judges the password before it asks it", _SW + _PU + _PWL, _PWL + _SW + _PU),
]


def chowngrp_rows(helper=None):
    """Returns (rows, skipped).  A row is (label, ok, detail)."""
    import getpass
    rows = []
    skipped = []
    td = tempfile.mkdtemp(prefix="sdelev-chg-")
    try:
        root = os.path.realpath(td)
        sd = os.path.join(root, "sd")
        who = getpass.getuser()
        g_team, g_shared = os.path.join(sd, "group_accounts", "team"), os.path.join(sd, "group_accounts", "shared")
        u_victim, u_me = os.path.join(sd, "user_accounts", "victim"), os.path.join(sd, "user_accounts", who)
        outside = os.path.join(root, "outside")
        for acct in (g_team, g_shared, u_victim, u_me):
            for sub in ("voc", "$hold.dic"):
                os.makedirs(os.path.join(acct, sub))
                for n in ("%0", "%1"):
                    open(os.path.join(acct, sub, n), "w", encoding="utf-8").close()
        os.makedirs(outside)
        os.symlink(u_victim, os.path.join(g_team, "lnk"))          # inside a group account, leading into a user account
        env = {"SD_ACCT_ROOT": sd, "SD_SDSYS_UID_FIXTURE": str(os.getuid())}       # F12b: the root shape wants the sdsys uid's file; the runner's scratch files stand for them

        def ask(label, argv, check):
            code, out = run(argv, helper, env)
            first = out.strip().splitlines()[0] if out.strip() else "(no output)"
            rows.append((label, check(code, out), f"exit {code}: {first}"))

        def allowed(user, grp, real):
            return lambda c, o: c == 0 and f"chown -- {user}:{grp} {real}" in o

        def refused(reason):
            return lambda c, o: c != 0 and "REFUSED" in o and reason in o and "chown --" not in o

        not_group = "is not in a group account"
        # ---- ALLOW: what create.account (a GROUP account) and the installer's repair send
        for rel, why in (("", "the account directory"), ("voc", "its voc"), ("voc/%0", "voc/%0"), ("voc/%1", "voc/%1"), ("$hold.dic", "its $hold.dic"),
                         ("$hold.dic/%0", "$hold.dic/%0"), ("$hold.dic/%1", "$hold.dic/%1")):
            p = os.path.join(g_team, rel) if rel else g_team
            ask(f"ALLOW: sdsys chowns group account team, {why}, to sdg_team", ["chown-account", "sdsys", "sdg_team", p], allowed("sdsys", "sdg_team", p))
        for rel, why in (("", "directory"), ("voc/%0", "voc/%0")):
            p = os.path.join(g_shared, rel) if rel else g_shared
            ask(f"ALLOW: the shared account's {why} is sdsys:sdusers (the group create.account gives it)", ["chown-account", "sdsys", "sdusers", p], allowed("sdsys", "sdusers", p))
        # ---- the other shapes are as they were
        if _is_sd_user(who, helper)[0]:
            ask("ALLOW: the user shape, a person's own account directory (as it was)", ["chown-account", who, "sdu_" + who, u_me], allowed(who, "sdu_" + who, u_me))
            ask("ALLOW: ...and a record file inside it (as it was)", ["chown-account", who, "sdu_" + who, os.path.join(u_me, "voc", "%0")],
                allowed(who, "sdu_" + who, os.path.join(u_me, "voc", "%0")))
        else:
            skipped.append(f"chown-group: '{who}' is not an SD user here, so the user-shape controls are left out")
        ask("ALLOW: the root shape, an attached path (as it was)", ["chown-account", "root", "sdusers", outside], allowed("root", "sdusers", outside))
        # ---- REFUSE: a user account's files, in every group the review tried or a caller could name
        for rel, why in (("", "its directory"), ("voc", "its voc"), ("voc/%0", "voc/%0")):
            p = os.path.join(u_victim, rel) if rel else u_victim
            for grp in ("sdu_victim", "sdusers", "sdg_team"):
                ask(f"REFUSE: sdsys {grp} on user account victim, {why}, is not a group account's", ["chown-account", "sdsys", grp, p], refused(not_group))
        ask("REFUSE: the container group_accounts itself is not a group account", ["chown-account", "sdsys", "sdg_team", os.path.join(sd, "group_accounts")], refused(not_group))
        ask("REFUSE: the container user_accounts is not a group account", ["chown-account", "sdsys", "sdusers", os.path.join(sd, "user_accounts")], refused(not_group))
        ask("REFUSE: a link inside a group account that leads into a user account (the path is resolved first)", ["chown-account", "sdsys", "sdg_team", os.path.join(g_team, "lnk", "voc")],
            refused(not_group))
        ask("REFUSE: a .. out of a group account into a user account", ["chown-account", "sdsys", "sdg_team", g_team + "/../../user_accounts/victim/voc"], refused(not_group))
        # ---- REFUSE: a group account in a group that is not its own
        ask("REFUSE: another group account's group is not team's", ["chown-account", "sdsys", "sdg_other", os.path.join(g_team, "voc")], refused("belongs to the group sdg_team"))
        ask("REFUSE: sdusers is not an ordinary group account's group", ["chown-account", "sdsys", "sdusers", g_team], refused("belongs to the group sdg_team"))
        ask("REFUSE: team's group on the shared account's files", ["chown-account", "sdsys", "sdg_team", os.path.join(g_shared, "voc")], refused("belongs to the group sdusers"))
        ask("REFUSE: sdg_shared is not what create.account gives the shared account (its group is sdusers)", ["chown-account", "sdsys", "sdg_shared", g_shared],
            refused("belongs to the group sdusers"))
        ask("REFUSE: a path outside the accounts root is still refused first", ["chown-account", "sdsys", "sdg_team", outside], refused("outside the accounts root"))
    finally:
        shutil.rmtree(td, ignore_errors=True)
    return rows, skipped


_GA = '  [[ $rel == group_accounts/?* ]] \\\n    || die "path \'$real\' is not in a group account'
CHOWNGRP_MUTANTS = [
    ("chown-group: the group-account test is gone", _GA, _GA.replace('[[ $rel == group_accounts/?* ]]', 'true')),
    ("chown-group: any *_accounts directory is taken", _GA, _GA.replace('group_accounts/?*', '*_accounts/?*')),
    ("chown-group: the container itself is taken", _GA, _GA.replace('group_accounts/?*', 'group_accounts*')),
    ("chown-group: the group is not compared", '  [[ $group == "$want" ]] || die "group account', '  true || die "group account'),
    ("chown-group: any sdg_ group is taken", '  [[ $group == "$want" ]] || die "group account', '  [[ $group == sdg_?* || $group == "$want" ]] || die "group account'),
    ("chown-group: shared is held to sdg_shared too", '  if [[ $name == shared ]]; then want=sdusers; else want=sdg_$name; fi\n', '  want=sdg_$name\n'),
    ("chown-group: sdusers is taken for every account", '  if [[ $name == shared ]]; then want=sdusers; else want=sdg_$name; fi\n',
     '  if [[ $name == shared || $group == sdusers ]]; then want=sdusers; else want=sdg_$name; fi\n'),
    ("chown-group: the sdsys shape does not call it", '      require_sd_chown_path "$path"\n      require_group_account_files "$group" "$path"\n', '      require_sd_chown_path "$path"\n'),
]


def groupadd_rows(helper=None):
    """Returns (rows, skipped).  A row is (label, ok, detail)."""
    import getpass
    import pwd
    rows = []
    skipped = []
    u = _no_group_user()
    if u is None or not _is_sd_user(u, helper)[0]:
        skipped.append("groupadd: every ordinary user on this machine has an sdu_ group, so the rows that make one are left out")
        return rows, skipped
    g = "sdu_" + u
    other = None
    for p in sorted(pwd.getpwall(), key=lambda p: p.pw_uid):
        if p.pw_name not in (u, "root", "sdsys") and p.pw_uid >= 1000 and p.pw_name == p.pw_name.lower() and p.pw_name[:1].isalpha() \
                and p.pw_name.replace("_", "a").replace("-", "a").isalnum() and len(p.pw_name) <= 32 and _is_sd_user(p.pw_name, helper)[0]:
            other = p.pw_name
            break

    def ask(label, argv, check):
        code, out = run(argv, helper)
        first = out.strip().splitlines()[0] if out.strip() else "(no output)"
        rows.append((label, check(code, out), f"exit {code}: {first}"))

    def goes(*needles):
        return lambda c, o: c == 0 and all(n in o for n in needles)

    def refused(reason):
        return lambda c, o: c != 0 and "REFUSED" in o and reason in o and "groupadd --" not in o

    cant = "cannot be a member"
    # ---- ALLOW: what create.account sends, and the shapes that stay as they were
    ask(f"ALLOW: groupadd {g} root,{u} is the call create.account makes for a user account", ["groupadd", g, f"root,{u}"],
        goes(f"groupadd -- {g}", f"gpasswd -a root {g}", f"gpasswd -a {u} {g}"))
    ask(f"ALLOW: groupadd {g} with no member", ["groupadd", g], goes(f"groupadd -- {g}"))
    ask(f"ALLOW: groupadd {g} {u}, the user alone", ["groupadd", g, u], goes(f"gpasswd -a {u} {g}"))
    ask(f"ALLOW: groupadd {g} root, root alone", ["groupadd", g, "root"], goes(f"gpasswd -a root {g}"))
    ask("ALLOW: groupadd sdg_probe_f12 root,sdsys, the call for a group account (sdsys is a member of a group account's group; as it was)",
        ["groupadd", "sdg_probe_f12", "root,sdsys"], goes("groupadd -- sdg_probe_f12", "gpasswd -a sdsys sdg_probe_f12"))
    ask(f"ALLOW: groupadd sdg_probe_f12 {u}, an SD user in an sdg_ group (as it was: only sdu_ groups are narrowed)", ["groupadd", "sdg_probe_f12", u], goes(f"gpasswd -a {u} sdg_probe_f12"))
    # ---- REFUSE: the sdsys user is never a member of an account's group when it is made
    ask(f"REFUSE: groupadd {g} root,{u},sdsys: the sdsys user joins an account's group through sdsys-join", ["groupadd", g, f"root,{u},sdsys"], refused(cant))
    ask(f"REFUSE: groupadd {g} root,sdsys", ["groupadd", g, "root,sdsys"], refused(cant))
    ask(f"REFUSE: groupadd {g} sdsys", ["groupadd", g, "sdsys"], refused(cant))
    if other:
        ask(f"REFUSE: groupadd {g} {other}: another person is added with addgroup, not when the group is made", ["groupadd", g, other], refused(cant))
        ask(f"REFUSE: groupadd {g} root,{u},{other}", ["groupadd", g, f"root,{u},{other}"], refused(cant))
    else:
        skipped.append("groupadd: this machine has no second ordinary user, so the 'another person' rows are left out")
    # ---- REFUSE: the group is made for an SD user that exists
    ask("REFUSE: groupadd sdu_zzprobenouser root: there is no such user", ["groupadd", "sdu_zzprobenouser", "root"], refused("does not exist"))
    ask("REFUSE: ...and with no member at all", ["groupadd", "sdu_zzprobenouser"], refused("does not exist"))
    ask("REFUSE: groupadd sdu_root: root is never a target", ["groupadd", "sdu_root", "root"], refused("root is never a target"))
    ask("REFUSE: groupadd sdu_sdsys: sdsys is SD's own administrator account", ["groupadd", "sdu_sdsys", "root,sdsys"], refused("sdsys is SD's own administrator account"))
    ask("REFUSE: groupadd sdu_daemon: a system account (below UID_MIN) or no such user", ["groupadd", "sdu_daemon", "root"],
        lambda c, o: refused("below UID_MIN")(c, o) or refused("does not exist")(c, o))
    ask("REFUSE: groupadd sdu_-rf: a leading dash in the user part would read as an option", ["groupadd", "sdu_-rf", "root"], refused("is not a valid name"))
    return rows, skipped


_RG = '[[ $1 != sdu_* ]] || require_own_account_group "$1" "${2:-}"\n'
GROUPADD_MUTANTS = [
    ("groupadd: the sdu_ rule is not called", _RG, ""),
    ("groupadd: the user part need not exist", '  require_sd_user "$user"\n  if [[ -n $members ]]; then', '  if [[ -n $members ]]; then'),
    ("groupadd: the members are not looked at", "  if [[ -n $members ]]; then\n    IFS=',' read -r -a list", "  if false; then\n    IFS=',' read -r -a list"),
    ("groupadd: sdsys is taken as a member", '[[ -z $m || $m == root || $m == "$user" ]] \\', '[[ -z $m || $m == root || $m == sdsys || $m == "$user" ]] \\'),
    ("groupadd: any member is taken", '[[ -z $m || $m == root || $m == "$user" ]] \\', '[[ -n $m || -z $m ]] \\'),
    ("groupadd: the rule runs for sdg_ groups too", _RG, '[[ $1 != sd[ug]_* ]] || require_own_account_group "$1" "${2:-}"\n'),
]


# ---- 26 Oct 26, F12b, F12c, F12e (the coordinator's second order), three more families in the same shape (labels begin ALLOW:, REFUSE: or TEXT:).
# ----   ownedby   chown-account root sdusers (the OTHER account's shape) takes only a directory or a plain file that the sdsys user owns, wherever it is.  The sdsys uid is given by
# ----             SD_SDSYS_UID_FIXTURE (dry run only; the scratch files are the runner's own), so the helper's refusals of /etc/shadow, /etc/passwd, /etc/sudoers and /etc/ssh/sshd_config
# ----             are the OWNER rule's and nothing else.  The real run's worker (FC_PY, lifted from the helper) is run here on scratch files: it chowns through the file it opened.
# ----   pwunset   setpw sets a first password only: a user whose shadow entry holds a hash is refused (getent shadow, which the stub answers).
# ----   envtrust  the helper fixes its PATH; SD_ACCT_ROOT, SD_ACCARCHIVE and SD_PATH_PREPEND are read on a dry run or from a process that is not root.  A root process is played
# ----             with `unshare -Ur` where the machine allows it (SKIPPED out loud where it does not) and by lifting trust_fixtures, which takes the effective uid as an argument.
FC_START, FC_END = "read -r -d '' FC_PY <<'FC_PY_END' || true\n", "\nFC_PY_END\n"


def ownedby_rows(helper=None):
    """Returns (rows, skipped).  A row is (label, ok, detail)."""
    import grp
    rows = []
    skipped = []
    if os.geteuid() == 0:
        skipped.append("ownedby: this is root")
        return rows, skipped
    me = os.getuid()
    src = open(helper or HELPER, encoding="utf-8").read()
    td = tempfile.mkdtemp(prefix="sdelev-own-")
    try:
        root = os.path.realpath(td)
        acc = os.path.join(root, "other", "ledger")                       # an OTHER account's path, outside any accounts root
        for sub in ("voc", "$hold.dic"):
            os.makedirs(os.path.join(acc, sub))
            for n in ("%0", "%1"):
                open(os.path.join(acc, sub, n), "w", encoding="utf-8").close()
        plain = os.path.join(acc, "readme")
        open(plain, "w", encoding="utf-8").close()
        fifo = os.path.join(acc, "pipe")
        os.mkfifo(fifo)
        lnk_dir = os.path.join(root, "lnk_dir")
        os.symlink(acc, lnk_dir)
        lnk_shadow = os.path.join(acc, "lnk_shadow")
        os.symlink("/etc/shadow", lnk_shadow)
        fx = {"SD_SDSYS_UID_FIXTURE": str(me)}

        def ask(label, argv, check, env=None, dry=True):
            code, out = run(argv, helper, env, dry=dry)
            first = out.strip().splitlines()[0] if out.strip() else "(no output)"
            rows.append((label, check(code, out), f"exit {code}: {first}"))

        def allowed(real):
            return lambda c, o: c == 0 and f"chown -- root:sdusers {real}" in o and f"found to belong to uid {me}" in o

        def refused(*reasons):
            return lambda c, o: c != 0 and "REFUSED" in o and any(r in o for r in reasons) and "chown --" not in o

        owner_rule = "not to the user sdsys"
        # ---- ALLOW: what create.account sends for an OTHER account - everything create.file and make.account have just made as sdsys, at a path the administrator named
        for rel, why in (("", "account directory"), ("voc", "voc directory"), ("voc/%0", "voc/%0"), ("voc/%1", "voc/%1"), ("$hold.dic", "$hold.dic directory"),
                         ("$hold.dic/%0", "$hold.dic/%0"), ("readme", "plain file")):
            p = os.path.join(acc, rel) if rel else acc
            ask(f"ALLOW: root sdusers on an OTHER account's {why}, owned by the sdsys uid, outside any accounts root", ["chown-account", "root", "sdusers", p], allowed(p), fx)
        ask("ALLOW: ...a link to the account directory is resolved first, and the real path is the one chowned", ["chown-account", "root", "sdusers", lnk_dir], allowed(acc), fx)
        # ---- REFUSE: root's files, by the owner rule
        sysfiles = [p for p in ("/etc/shadow", "/etc/passwd", "/etc/sudoers", "/etc/ssh/sshd_config") if os.path.exists(p)]
        if len(sysfiles) < 2:
            skipped.append("ownedby: fewer than two of /etc/shadow, /etc/passwd, /etc/sudoers and /etc/ssh/sshd_config are visible here")
        for p in sysfiles:
            ask(f"REFUSE: root sdusers on {p} (root's: it was accepted before F12b) is refused by the owner rule", ["chown-account", "root", "sdusers", p],
                refused(owner_rule), fx)
        ask("REFUSE: a link inside the account that leads to /etc/shadow is resolved first and refused as root's", ["chown-account", "root", "sdusers", lnk_shadow],
            lambda c, o: refused(owner_rule)(c, o) and "/etc/shadow" in o, fx)
        ask("REFUSE: a file of this account that the fixture says belongs to somebody else (uid+1) is refused", ["chown-account", "root", "sdusers", plain],
            refused("belongs to uid %d" % me), {"SD_SDSYS_UID_FIXTURE": str(me + 1)})
        ask("REFUSE: a named pipe is neither a directory nor a plain file", ["chown-account", "root", "sdusers", fifo], refused("neither a directory nor a plain file"), fx)
        ask("REFUSE: a fixture that is not a number", ["chown-account", "root", "sdusers", acc], refused("is not a number"), {"SD_SDSYS_UID_FIXTURE": "sdsys"})
        ask("REFUSE: with no fixture the sdsys user's own uid decides (the runner's scratch files are not its) - refused, and no chown line", ["chown-account", "root", "sdusers", acc],
            lambda c, o: c != 0 and "REFUSED" in o and "chown --" not in o and ("belongs to uid" in o or "sdsys does not exist" in o or "user sdsys does not exist" in o))
        ask("REFUSE: the fixture is IGNORED when the run is not a dry run (an ordinary user is refused before it could act: the owner, or no sdsys user)",
            ["chown-account", "root", "sdusers", acc], refused("belongs to uid", "user sdsys does not exist"), fx, dry=False)
        ask("REFUSE: a group other than sdusers is still refused first", ["chown-account", "root", "sdu_" + str(me), acc], refused("owner is root:sdusers"), fx)
        # ---- the worker the real run uses (FC_PY, lifted from the helper): run on scratch files, as an ordinary user who owns them
        if src.count(FC_START) != 1 or src.count(FC_END) != 1:
            rows.append(("TEXT: the real run's worker is found once between its markers", False, "markers not found once"))
            return rows, skipped
        a = src.index(FC_START) + len(FC_START)
        py = src[a:src.index(FC_END, a)] + "\n"
        rows.append(("TEXT: the real run's worker is found once between its markers (a test that lifted nothing must fail)", len(py) > 400, f"{len(py)} bytes"))
        g1 = os.getgid()
        g2 = next((g for g in os.getgroups() if g != g1), None)
        gname = lambda g: grp.getgrgid(g).gr_name
        wd = os.path.join(root, "worker")
        os.makedirs(wd)

        def worker(path, owner=me, group=None, newuid=me):
            p = subprocess.run(["python3", "-c", py, path, str(owner), group or gname(g1), str(newuid)], capture_output=True, text=True)
            return p.returncode, (p.stdout or "") + (p.stderr or "")

        def mkfile(name):
            p = os.path.join(wd, name)
            open(p, "w", encoding="utf-8").close()
            return p

        def wrow(label, path, check, **kw):
            code, out = worker(path, **kw)
            first = out.strip().splitlines()[0] if out.strip() else "(no output)"
            rows.append((label, check(code, out), f"exit {code}: {first}"))

        if g2 is None:
            skipped.append("ownedby: this person is in no group but the primary one, so the rows that see a group change are left out")
        else:
            f1 = mkfile("f1")
            wrow("ALLOW: the worker chowns a plain file the sdsys uid owns, through the open file: the group changes", f1,
                 lambda c, o: c == 0 and "chowned" in o and os.stat(f1).st_gid == g2, group=gname(g2))
            d1 = os.path.join(wd, "d1")
            os.makedirs(d1)
            wrow("ALLOW: ...and a directory", d1, lambda c, o: c == 0 and "chowned" in o and os.stat(d1).st_gid == g2, group=gname(g2))
            f2 = mkfile("f2")
            wrow("REFUSE: the worker refuses a file of somebody else (owner argument uid+1) and changes nothing", f2,
                 lambda c, o: c == 2 and "belongs to uid" in o and os.stat(f2).st_gid == g1, owner=me + 1, group=gname(g2))
            f3 = mkfile("f3")
            l3 = os.path.join(wd, "l3")
            os.symlink(f3, l3)
            wrow("REFUSE: a link at the end of the path is not followed (the file behind it is not changed)", l3,
                 lambda c, o: c == 2 and "without following a link" in o and os.stat(f3).st_gid == g1, group=gname(g2))
            f4 = mkfile("f4")
            sub = os.path.join(wd, "sub")
            os.makedirs(sub)
            os.rename(f4, os.path.join(sub, "f4"))
            lsub = os.path.join(wd, "lsub")
            os.symlink(sub, lsub)
            wrow("REFUSE: a link in a directory ABOVE the file (the path names another place than the file opened) is found, and nothing is changed", os.path.join(lsub, "f4"),
                 lambda c, o: c == 2 and "not where it was when it was checked" in o and os.stat(os.path.join(sub, "f4")).st_gid == g1, group=gname(g2))
        wf = os.path.join(wd, "pipe")
        os.mkfifo(wf)
        wrow("REFUSE: the worker refuses a named pipe", wf, lambda c, o: c == 2 and "neither a directory nor a plain file" in o)
        wrow("REFUSE: the worker refuses a group that does not exist", mkfile("f5"), lambda c, o: c == 2 and "does not exist" in o, group="zzf12nogroup")
        wrow("REFUSE: the worker refuses a path that is not there (a worker that never opened anything must not say it chowned)", os.path.join(wd, "nothere"),
             lambda c, o: c == 2 and "cannot open" in o and "chowned" not in o)
        # ---- the tail: the real run calls the worker with the path, the owner, the group and 0, in that order, only for this shape
        tail = 'if [[ -n $FC_PATH ]]; then\n  python3 -I -c "$FC_PY" "$FC_PATH" "$FC_OWNER" "$FC_GROUP" 0 || exit $?\nelse\n  "${cmd[@]}" || exit $?\nfi\n'
        rows.append(("TEXT: the real run chowns through the worker when FC_PATH is set (path, owner, group, 0 - the order the worker reads them) and runs the command otherwise", tail in src, ""))
        rows.append(("TEXT: every python3 the helper runs from a string is run with -I (sudo keeps the caller's current directory, and `python3 -c` would import a planted grp.py from it as root); "
                     "none without; and the worker refuses, rather than skips the link check, when /proc cannot be read",
                     src.count("python3 -c") == 0 and src.count("python3 -I -c") == 2 and 'refuse("cannot tell where the open file is' in src and "here = path" not in src,
                     f"python3 -c: {src.count('python3 -c')}, python3 -I -c: {src.count('python3 -I -c')}"))
        root_case = src[src.find("    root)\n      [[ $group == sdusers ]]"):src.find("    sdsys)\n      require_sd_chown_path")]
        rows.append(("TEXT: FC_PATH is set in the root case of require_account_owner and nowhere else, after the owner has been checked",
                     src.count("FC_PATH=$real") == 1 and 0 < root_case.find("require_sdsys_owned") < root_case.find("FC_PATH=$real"), root_case[-120:]))
    finally:
        shutil.rmtree(td, ignore_errors=True)
    return rows, skipped


_FW = 'fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_NOCTTY)'
OWNEDBY_MUTANTS = [
    ("ownedby: the worker follows a link at the end", _FW, _FW.replace(" | os.O_NOFOLLOW", "")),
    ("ownedby: the worker does not ask the open file who owns it", "    if st.st_uid != owner:\n        refuse(", "    if False:\n        refuse("),
    ("ownedby: the worker takes any kind of file", "    if not (stat.S_ISDIR(st.st_mode) or stat.S_ISREG(st.st_mode)):\n", "    if False:\n"),
    ("ownedby: the worker does not check that the path still names the open file", "    if here != path:\n        refuse(", "    if False:\n        refuse("),
    ("ownedby: the helper's own owner check is gone", '  [[ $have == "$SDSYS_UID" ]] \\\n    || die "path', '  true \\\n    || die "path'),
    ("ownedby: the root shape does not ask for the owner", '      require_sdsys_owned "$real"\n', ''),
    ("ownedby: the fixture is honoured on a real run", "if [[ $DRY -eq 1 && -n ${SD_SDSYS_UID_FIXTURE:-} ]]; then", "if [[ -n ${SD_SDSYS_UID_FIXTURE:-} ]]; then"),
    ("ownedby: a fixture that is not a number is taken", '[[ $SD_SDSYS_UID_FIXTURE =~ ^[0-9]+$ ]] || die "SD_SDSYS_UID_FIXTURE is not a number"', 'true || die "SD_SDSYS_UID_FIXTURE is not a number"'),
    ("ownedby: any kind of file passes the helper's own check", '  [[ -d $real || -f $real ]] || die "path \'$real\' is neither a directory nor a plain file"\n', ''),
    ("ownedby: the real run runs the command and not the worker", 'python3 -I -c "$FC_PY" "$FC_PATH" "$FC_OWNER" "$FC_GROUP" 0 || exit $?', '"${cmd[@]}" || exit $?'),
    ("ownedby: the worker runs without -I (a grp.py in the caller's current directory would be imported as root)", 'python3 -I -c "$FC_PY"', 'python3 -c "$FC_PY"'),
    ("ownedby: group-write's worker runs without -I", 'python3 -I -c "$GW_PY"', 'python3 -c "$GW_PY"'),
    ("ownedby: the worker goes on when /proc cannot say where the open file is", 'refuse("cannot tell where the open file is (is /proc mounted?): %s" % e.strerror)', 'here = path'),
    ("ownedby: the worker is given the arguments in another order", '"$FC_PATH" "$FC_OWNER" "$FC_GROUP" 0 || exit $?', '"$FC_PATH" "$FC_GROUP" "$FC_OWNER" 0 || exit $?'),
]


def pwunset_rows(helper=None):
    """Returns (rows, skipped).  A row is (label, ok, detail)."""
    import getpass
    rows = []
    skipped = []
    who = getpass.getuser()
    is_sd, why_not = _is_sd_user(who, helper)
    if not is_sd or os.geteuid() == 0:
        skipped.append(f"pwunset: '{who}' is not an SD user here, or this is root ({why_not})")
        return rows, skipped
    td = tempfile.mkdtemp(prefix="sdelev-pwu-")
    try:
        _getent_stub(td)
        good = "Abcdef1!\n"

        def env(hash_, gecos="SD account", **more):
            e = {"SD_PATH_PREPEND": td, "STUB_PW_USER": who, "STUB_PW_GECOS": gecos, "STUB_SHADOW_SET": "1", "STUB_SHADOW_HASH": hash_}
            e.update(more)
            return e

        def ask(label, argv, check, e, stdin=good):
            code, out = run(argv, helper, env=e, stdin=stdin)
            first = out.strip().splitlines()[0] if out.strip() else "(no output)"
            rows.append((label, check(code, out), f"exit {code}: {first}"))

        def goes(needle):
            return lambda c, o: c == 0 and needle in o

        def refused(reason):
            return lambda c, o: c != 0 and "REFUSED" in o and reason in o and "chpasswd for" not in o

        already = "already has a Linux password"
        # ---- ALLOW: a user with no password yet, in every spelling of it (useradd leaves ! or !!)
        for h in ("!", "!!", "*", "!*", ""):
            ask(f"ALLOW: setpw {who} goes through while the shadow hash is {h!r} (no password yet: create.account's first password)", ["setpw", who], goes(f"chpasswd for {who}"), env(h))
        # ---- REFUSE: a user that has a hash, locked or not
        for h, why in (("$6$abc$defghijklmnop", "sha512"), ("$y$j9T$saltsalt$hashhashhash", "yescrypt"), ("$1$a$b", "md5"), ("!$6$abc$defghijklmnop", "a locked account that still has its hash"),
                       ("!!$6$abc$def", "two bangs and a hash"), ("x", "a bare x"), ("LK", "a word"), ("$", "a dollar")):
            ask(f"REFUSE: setpw {who} is refused when the shadow hash is {h!r} ({why}): a reset", ["setpw", who], refused(already), env(h))
        ask("REFUSE: setpw is refused when the shadow entry cannot be read (a dry run that could not judge is not a pass)", ["setpw", who], refused("cannot read the shadow entry"),
            env("!", STUB_SHADOW_FAIL="1"))
        # ---- the order: stamp first, then the password state, then the password
        ask("REFUSE: a user without the stamp AND with a hash is refused for the stamp (the stamp is asked first)", ["setpw", who],
            lambda c, o: refused("was not created by SD")(c, o) and already not in o, env("$6$abc$def", gecos="Some Person"))
        ask("REFUSE: a user with a hash and a weak password is refused for the hash, and the password's text is not judged", ["setpw", who],
            lambda c, o: refused(already)(c, o) and "does not meet SD's rule" not in o, env("$6$abc$def"), "weakpass\n")
        # ---- the other verbs do not ask it: passwd and userdel work on a user with a hash (userdel is how delete.account takes a user away)
        ask(f"ALLOW: userdel {who} still goes through for a user with a hash (delete.account, the unwind)", ["userdel", who], goes(f"userdel -- {who}"), env("$6$abc$def"), None)
        ask(f"ALLOW: passwd {who} still goes through for a user with a hash (it is not the first-password rule's)", ["passwd", who], goes(f"passwd -- {who}"), env("$6$abc$def"), None)
    finally:
        shutil.rmtree(td, ignore_errors=True)
    return rows, skipped


PWUNSET_MUTANTS = [
    ("pwunset: setpw no longer asks it", _PU, ""),
    ("pwunset: any hash is accepted", "    *) die \"'$user' already has a Linux password", "    *) : \"'$user' already has a Linux password"),
    ("pwunset: a locked hash is taken as no password", "    ''|'*'|'!'|'!!'|'!*') : ;;", "    ''|'*'|'!'|'!!'|'!*'|'!'*) : ;;"),
    ("pwunset: the empty field is refused", "    ''|'*'|'!'|'!!'|'!*') : ;;", "    '*'|'!'|'!!'|'!*') : ;;"),
    ("pwunset: !! is refused (Fedora's spelling)", "    ''|'*'|'!'|'!!'|'!*') : ;;", "    ''|'*'|'!'|'!*') : ;;"),
    ("pwunset: an entry that cannot be read passes", 'ent=$(getent shadow "$user" 2>/dev/null) || die "cannot read the shadow entry', 'ent=$(getent shadow "$user" 2>/dev/null) || : "cannot read the shadow entry'),
    ("pwunset: the wrong field is read", "| cut -d: -f2)\n  case $hash in", "| cut -d: -f3)\n  case $hash in"),
    ("pwunset: asked after the password is read and judged", _PU + _PWL, _PWL + _PU),
    ("pwunset: asked before the stamp", _SW + _PU, _PU + _SW),
]


def envtrust_rows(helper=None):
    """Returns (rows, skipped).  A row is (label, ok, detail)."""
    import getpass
    rows = []
    skipped = []
    who = getpass.getuser()
    hp = helper or HELPER
    src = open(hp, encoding="utf-8").read()
    is_sd, why_not = _is_sd_user(who, helper)
    if not is_sd or os.geteuid() == 0:
        skipped.append(f"envtrust: '{who}' is not an SD user here, or this is root ({why_not})")
        return rows, skipped
    td = tempfile.mkdtemp(prefix="sdelev-env-")
    try:
        stubdir = os.path.join(td, "stub")
        os.makedirs(stubdir)
        _getent_stub(stubdir)
        log = os.path.join(td, "stub.log")
        base = {"STUB_PW_USER": who, "STUB_PW_GECOS": "SD account", "STUB_SHADOW_SET": "1", "STUB_SHADOW_HASH": "!", "STUB_LOG": log}

        def seen():
            return os.path.exists(log) and "passwd" in open(log, encoding="utf-8").read()

        # ---- PATH: a getent in front of the caller's PATH is NOT used; the same getent given in SD_PATH_PREPEND is (and the log shows the stub was reached)
        code, out = run(["passwd", who], helper, dict(base, PATH=stubdir + os.pathsep + os.environ.get("PATH", "")))
        rows.append(("REFUSE: a getent put first on the CALLER'S PATH is not used: the stamp the stub would give is not seen (refused for the real comment), and the stub was never reached",
                     code != 0 and "was not created by SD" in out and not os.path.exists(log), f"exit {code}: {out.strip()[:100]}"))
        if os.path.exists(log):
            os.unlink(log)
        code, out = run(["passwd", who], helper, dict(base, SD_PATH_PREPEND=stubdir))
        rows.append(("ALLOW: ...the same getent given in SD_PATH_PREPEND IS used (dry run): accepted, and the stub's log shows it was asked about passwd",
                     code == 0 and f"passwd -- {who}" in out and seen(), f"exit {code}: {out.strip()[:100]}"))
        # ---- trust_fixtures, lifted: a dry run, or a process that is not root
        for dry, euid, want, why in ((1, 0, 0, "a dry run as root"), (1, 1000, 0, "a dry run as an ordinary user"), (0, 1000, 0, "a real run as an ordinary user (it cannot act)"),
                                     (0, 0, 1, "a real run as root: nothing from the environment")):
            p = subprocess.run(["bash", "-c", 'eval "$(sed -n \'/^trust_fixtures()/,/^}/p\' "$1")"; type trust_fixtures >/dev/null 2>&1 || exit 9; trust_fixtures "$2" "$3"',
                                "lift", hp, str(dry), str(euid)], capture_output=True, text=True)
            rows.append((f"{'REFUSE' if want else 'ALLOW'}: trust_fixtures({dry}, {euid}) - {why} - says {'no' if want else 'yes'}", p.returncode == want, f"exit {p.returncode}"))
        # ---- main: the block, in its place
        block = ('if trust_fixtures "$DRY" "${EUID:-$(id -u)}"; then\n  [[ -z ${SD_PATH_PREPEND:-} ]] || PATH=$SD_PATH_PREPEND:$PATH\nelse\n'
                 '  SD_ACCT_ROOT=$SD_ACCT_ROOT_REAL\n  SD_ACCARCHIVE=$SD_ACCARCHIVE_REAL\n  SD_SOCKET_UNIT=$SD_SOCKET_UNIT_REAL\nfi\n')
        dryword = src.find("if [[ ${1:-} == --dry-run ]]; then DRY=1; shift; fi")
        rows.append(("TEXT: main reads SD_PATH_PREPEND only where trust_fixtures says yes, and puts the real accounts root and the real archiver back where it says no - right after the dry-run word and before the verb",
                     block in src and 0 < dryword < src.find(block) < src.find("\nverb=${1:-}"), ""))
        top = src.find("\nPATH=/usr/sbin:/usr/bin:/sbin:/bin\nexport PATH\n")
        rows.append(("TEXT: PATH is fixed once, after set -uo pipefail and before the first function",
                     src.count("PATH=/usr/sbin:/usr/bin:/sbin:/bin") == 1 and 0 < src.find("\nset -uo pipefail\n") < top < src.find("\nuid_min() {"), f"at {top}"))
        rows.append(("TEXT: the environment's SD_ACCT_ROOT and SD_ACCARCHIVE are read once each, into variables that main resets",
                     'SD_ACCT_ROOT=${SD_ACCT_ROOT:-$SD_ACCT_ROOT_REAL}' in src and 'SD_ACCARCHIVE=${SD_ACCARCHIVE:-$SD_ACCARCHIVE_REAL}' in src
                     and 'SD_SOCKET_UNIT=${SD_SOCKET_UNIT:-$SD_SOCKET_UNIT_REAL}' in src
                     and src.count("${SD_ACCT_ROOT:-") == 1 and src.count("${SD_ACCARCHIVE:-") == 1 and src.count("${SD_SOCKET_UNIT:-") == 1, ""))
        # ---- a root process, played by a user namespace (uid 0 inside it, the runner's own privileges outside): SD_ACCT_ROOT means nothing to it unless the run is a dry run
        acct = os.path.join(td, "sd", "user_accounts", "x")
        os.makedirs(acct)
        try:
            ok_ns = subprocess.run(["unshare", "-Ur", "true"], capture_output=True).returncode == 0
        except OSError:
            ok_ns = False
        if not ok_ns:
            skipped.append("envtrust: `unshare -Ur` is not allowed here, so the rows that play root are left out (the lifted trust_fixtures rows and the text rows still run)")
        else:
            e = dict(os.environ, SD_ACCT_ROOT=os.path.join(td, "sd"))
            p = subprocess.run(["unshare", "-Ur", "bash", hp, "--dry-run", "tree-count", acct], capture_output=True, text=True, env=e)
            o = (p.stdout or "") + (p.stderr or "")
            rows.append(("ALLOW: as 'root' (a user namespace) a DRY run reads SD_ACCT_ROOT: tree-count of the scratch account is accepted (the control for the row below)",
                         p.returncode == 0 and "count" in o and acct in o, f"exit {p.returncode}: {o.strip()[:100]}"))
            p = subprocess.run(["unshare", "-Ur", "bash", hp, "tree-count", acct], capture_output=True, text=True, env=e)
            o = (p.stdout or "") + (p.stderr or "")
            rows.append(("REFUSE: as 'root' a REAL run does not read SD_ACCT_ROOT: the same tree-count is refused (outside /home/sd) and nothing is run",
                         p.returncode != 0 and "REFUSED" in o and "python3" not in o, f"exit {p.returncode}: {o.strip()[:100]}"))
    finally:
        shutil.rmtree(td, ignore_errors=True)
    return rows, skipped


_TB = ('if trust_fixtures "$DRY" "${EUID:-$(id -u)}"; then\n  [[ -z ${SD_PATH_PREPEND:-} ]] || PATH=$SD_PATH_PREPEND:$PATH\nelse\n'
       '  SD_ACCT_ROOT=$SD_ACCT_ROOT_REAL\n  SD_ACCARCHIVE=$SD_ACCARCHIVE_REAL\n  SD_SOCKET_UNIT=$SD_SOCKET_UNIT_REAL\nfi\n')
ENVTRUST_MUTANTS = [
    ("envtrust: PATH is not fixed", "\nPATH=/usr/sbin:/usr/bin:/sbin:/bin\nexport PATH\n", "\n"),
    ("envtrust: PATH is fixed with /usr/local/bin first", "\nPATH=/usr/sbin:/usr/bin:/sbin:/bin\nexport PATH\n", "\nPATH=/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\nexport PATH\n"),
    ("envtrust: trust_fixtures always says yes", "  [[ $1 -eq 1 || $2 -ne 0 ]]\n", "  true\n"),
    ("envtrust: trust_fixtures wants a dry run AND a non-root process", "  [[ $1 -eq 1 || $2 -ne 0 ]]\n", "  [[ $1 -eq 1 && $2 -ne 0 ]]\n"),
    ("envtrust: a real run as root still reads SD_ACCARCHIVE", "  SD_ACCARCHIVE=$SD_ACCARCHIVE_REAL\n", ""),
    ("envtrust: a real run as root still reads SD_SOCKET_UNIT (remote-api reads its ListenStream as root)", "  SD_SOCKET_UNIT=$SD_SOCKET_UNIT_REAL\nfi\n", "fi\n"),
    ("envtrust: a real run as root still reads SD_ACCT_ROOT", "  SD_ACCT_ROOT=$SD_ACCT_ROOT_REAL\n", ""),
    ("envtrust: SD_PATH_PREPEND is read whatever trust_fixtures says", _TB.split("else\n")[0],
     '[[ -z ${SD_PATH_PREPEND:-} ]] || PATH=$SD_PATH_PREPEND:$PATH\nif trust_fixtures "$DRY" "${EUID:-$(id -u)}"; then\n  :\n'),
    ("envtrust: main never asks trust_fixtures", _TB, ""),
    ("envtrust: main tells trust_fixtures it is never a dry run", 'if trust_fixtures "$DRY" "${EUID:-$(id -u)}"; then', 'if trust_fixtures 0 "${EUID:-$(id -u)}"; then'),
]


def selftest():
    """The group rows must pass on the real helper and fail on every mutant."""
    if not os.path.exists(HELPER):
        print(f"REFUSING - helper not found at {HELPER}", file=sys.stderr)
        return 2
    src = open(HELPER, encoding="utf-8").read()
    survivors = 0
    total = 0
    # 19 Oct 26: three families of rows, each with the mutants that must break it: the route groups (S.65), the record files of a group
    # account (981a36a) and sdsys-join (S.67 stage 2).  The control comes first for each: the real helper must pass every row.
    # 26 Oct 26, F6: sdsys-leave and the log lines are two more.  `--only=FAMILY` (group, record-file, sdsys-join, sdsys-leave, log) runs one family, so a
    # sitting that changes one does not pay for the others.
    only = [x for a in sys.argv[1:] if a.startswith("--only=") for x in a.split("=", 1)[1].split(",")]      # 26 Oct 26, F12: a comma list is allowed
    # 26 Oct 26, F12: three more families, `--only=stamp,chown-group,groupadd` runs just those.
    for family, rows_fn, mutants in (("group", group_rows, GROUP_MUTANTS), ("record-file", record_rows, RECORD_MUTANTS),
                                     ("sdsys-join", sdsys_rows, SDSYS_MUTANTS), ("sdsys-leave", leave_rows, LEAVE_MUTANTS), ("log", log_rows, LOG_MUTANTS),
                                     ("stamp", stamp_rows, STAMP_MUTANTS), ("chown-group", chowngrp_rows, CHOWNGRP_MUTANTS), ("groupadd", groupadd_rows, GROUPADD_MUTANTS),
                                     ("ownedby", ownedby_rows, OWNEDBY_MUTANTS), ("pwunset", pwunset_rows, PWUNSET_MUTANTS), ("envtrust", envtrust_rows, ENVTRUST_MUTANTS)):
        if only and family not in only:
            continue
        rows, skipped = rows_fn()
        for s in skipped:
            print(f"  SKIPPED {s}")
        if len(rows) < (8 if family == "log" else 10):
            print(f"REFUSING - only {len(rows)} {family} rows ran", file=sys.stderr)
            return 2
        bad = [r for r in rows if not r[1]]
        print(f"  control: the real helper, {len(rows)} {family} rows, {len(bad)} failed")
        for label, ok, detail in bad:
            print(f"    FAIL {label} | {detail}")
        if bad:
            return 1
        left = _kill_mutants(src, mutants, rows_fn)
        if left is None:
            return 2
        survivors += left
        total += len(mutants)
    print(f"{total - survivors} of {total} mutants killed")
    return 1 if survivors else 0


def _kill_mutants(src, mutants, rows_fn):
    """Applies each (name, old, new) to the helper's text and runs rows_fn on the copy.  Returns the number that SURVIVED
    (no row went red), or None when a mutant's text does not occur exactly once (a refusal, printed)."""
    survivors = 0
    with tempfile.TemporaryDirectory() as td:
        for name, old, new in mutants:
            if src.count(old) != 1:
                print(f"REFUSING - mutant '{name}': its text occurs {src.count(old)} times, not once",
                      file=sys.stderr)
                return None
            path = os.path.join(td, "sd-elevate-mutant")
            with open(path, "w", encoding="utf-8") as f:
                f.write(src.replace(old, new))
            mrows, _ = rows_fn(path)
            caught = [r for r in mrows if not r[1]]
            if caught:
                print(f"  [KILLED  ] {name:42} | {len(caught)} row(s), first: {caught[0][0]}")
            else:
                survivors += 1
                print(f"  [SURVIVED] {name}")
    return survivors


# Each row: (expectation, argv, note).  `note` says WHY the row exists, so a
# later reader can tell a deliberate case from a filler one.
CASES = [
    # ---- the escalation attempts.  Every one of these is a way the eight
    # ---- raw sudo commands would have handed out root.
    (REFUSE, ["passwd", "root"],            "sudo passwd root - own the machine"),
    (REFUSE, ["passwd", "sdsys"],           "SD's own administrator account (by NAME - S.38 puts its uid above UID_MIN)"),
    (REFUSE, ["userdel", "root"],           "delete root"),
    (REFUSE, ["userdel", "sdsys"],          "delete SD's system account"),
    (REFUSE, ["useradd", "root"],           "root already exists"),

    # ---- userdel-home, 10 Sep 26 (DELETE.ACCOUNT REMOVE.HOME).  userdel -r
    # ---- removes a home directory, so the helper wants SD's stamp AND a home
    # ---- of exactly <HOME base>/<user>.  NO ALLOW ROW IS POSSIBLE HERE: a dev
    # ---- box has no stamped user, so the allowed half is witnessed at install
    # ---- by DELETE.ACCOUNT on a user SD created.  The "don" row is the one that
    # ---- discriminates - don exists, is an ordinary SD user, and is refused
    # ---- ONLY for lacking the stamp; its printed reason must say so.
    (REFUSE, ["userdel-home", "root"],      "root is never a target, home or not"),
    (REFUSE, ["userdel-home", "sdsys"],     "SD's own system account"),
    (REFUSE, ["userdel-home", "bin"],       "uid < UID_MIN"),
    (REFUSE, ["userdel-home", "don"],       "an existing SD user without the stamp: its home is never removed"),
    (REFUSE, ["userdel-home", "sdprobe_nonexistent"], "no such user"),
    (REFUSE, ["addgroup", "don", "sudo"],   "add yourself to sudo - the classic"),
    (REFUSE, ["addgroup", "don", "wheel"],  "the RHEL/Arch spelling of the same"),
    (REFUSE, ["addgroup", "don", "docker"], "docker group is root-equivalent"),
    (REFUSE, ["addgroup", "don", "lxd"],    "lxd group is root-equivalent"),
    (REFUSE, ["addgroup", "don", "adm"],    "log-reading group, still not SD's"),
    (REFUSE, ["groupadd", "sudo"],          "not an SD group"),
    (REFUSE, ["groupdel", "sudo"],          "not an SD group"),
    (REFUSE, ["delgroup", "don", "sudo"],   "not an SD group"),

    # ---- 18 Sep 26 (S.26): sdadmin and sdapi left the whitelist with the
    # ---- teardown - the groups no longer exist.  addgroup to either is
    # ---- refused as a non-SD group, and that is now the whole of the drift
    # ---- guard: re-adding them to the whitelist would fail these rows.
    (REFUSE, ["addgroup", "don", "sdadmin"], "sdadmin no longer exists (teardown S.26)"),
    # 20 Sep 26, S.29: the "sdapi no longer exists" row is gone.  It passed
    # because the teardown had deleted the group, so it would have FLIPPED to
    # a failure the moment an install created it again - a row that measures
    # this machine's state rather than the helper's rules.  The rules for
    # sdssh/sdapi are the groupadd/groupdel rows below.
    (REFUSE, ["groupdel", "sdusers"],        "deleting it unregisters every SD user at once"),

    # ---- 20 Sep 26, S.29: sdssh and sdapi are SD's own groups again, and are
    # ---- the authority for a per-account remote route.  Deleting one would
    # ---- not narrow a route, it would remove the register the route is read
    # ---- from - sdusers' own reason - so both are undeletable here.
    (REFUSE, ["groupdel", "sdssh"],          "the ssh route register is not deletable"),
    (REFUSE, ["groupdel", "sdapi"],          "the API route register is not deletable"),
    (REFUSE, ["groupdel", "sdfiles"],        "the SDNet files-only route register is not deletable (S.65 slice 2c)"),
    (REFUSE, ["groupdel", "sdfileswrite"],   "the SDNet write register is not deletable (S.65 write group)"),
    (REFUSE, ["groupdel", "sdfilesadmin"],   "the SDNet administration register is not deletable (S.73 item 3)"),
    # 20 Sep 26 - ***THESE TWO ROWS MEASURED THIS MACHINE, NOT THE HELPER, AND
    # THEY FLIPPED THE DAY AN INSTALL CREATED THE GROUPS.***  They asserted
    # ALLOW for `groupadd sdssh|sdapi`; sd-elevate refuses "group already
    # exists", so they passed only while no install had made them and failed
    # from 14:12 on 20 Sep onward.  S.29 part 1 deleted a row for exactly this
    # fault in the other direction and the same trap caught these.  The
    # whitelist question they were asking is existence-independent and is now
    # asked that way, in WHITELIST_BY_NAME below.

    # ---- remote-api / remote-ssh, 14 Sep 26 (S.13).  A fixed keyword and
    # ---- nothing else reaches them, so the refusals are the wrong word, a
    # ---- missing word and an extra argument; the content of the allowed ones
    # ---- is asserted below (REMOTE_CONTENT), not just their exit code.
    (REFUSE, ["remote-api", "wide"],           "not one of on/local/off/show"),
    (REFUSE, ["remote-api", "0.0.0.0:4247"],   "an address is never taken from the caller"),
    (REFUSE, ["remote-api"],                   "the keyword is required"),
    (REFUSE, ["remote-api", "on", "22"],       "no extra argument"),
    (REFUSE, ["remote-ssh", "local"],          "ssh has no LOCAL - on/off/show only"),
    (REFUSE, ["remote-ssh", "on", "--force"],  "no extra argument"),
    (ALLOW,  ["remote-api", "show"],           "the report form"),
    (ALLOW,  ["remote-api", "off"],            "OFF"),
    (ALLOW,  ["remote-ssh", "show"],           "the report form"),
    (REFUSE, ["setgid", "/etc"],            "outside the accounts root"),
    (REFUSE, ["setgid", "/"],               "outside the accounts root"),
    (REFUSE, ["setgid", "/usr/local/sdsys"], "SD's own tree is still not the accounts root"),

    # ---- chown-account (18 Sep 26, the A4 finding of the first fresh cycle's
    # ---- witness run).  createa's set.owner could only chown with the OS$CHOWN
    # ---- intrinsic, which needs root, and the administrator is a local sdsys
    # ---- session and is never root (S.26) - so every account made after an
    # ---- install came out sdsys:sdusers instead of <account>:sdu_<account>.
    # ---- The three shapes set.owner computes are allowed; everything else,
    # ---- and every way of escaping the account's own directory, is refused.
    (REFUSE, ["chown-account", "don", "sdu_don"],            "three arguments are required"),
    (REFUSE, ["chown-account", "don", "sdu_don", "/home/sd/user_accounts/don", "x"],
                                                        "no extra argument"),
    (REFUSE, ["chown-account", "sdsys", "sdg_probe", "/etc"],
                                                        "sdsys is confined to the accounts root"),
    (REFUSE, ["chown-account", "sdsys", "sdg_probe", "/usr/local/sdsys"],
                                                        "SD's own tree is not the accounts root"),
    (REFUSE, ["chown-account", "root", "sdu_don", "/home/sd/user_accounts/don"],
                                                        "the OTHER shape is root:sdusers, nothing else"),
    (REFUSE, ["chown-account", "don", "sdusers", "/home/sd/user_accounts/don"],
                                                        "sdusers is the group EVERY account is in"),
    (REFUSE, ["chown-account", "don", "sdu_zzprobe", "/home/sd/user_accounts/don"],
                                                        "a person owns through its own sdu_ group"),
    (REFUSE, ["chown-account", "don", "sdu_don", "/etc"],
                                                        "a person's path is its own account directory"),
    (REFUSE, ["chown-account", "don", "sdu_don", "/home/sd/user_accounts"],
                                                        "the accounts root itself is not an account directory"),
    (REFUSE, ["chown-account", "zzprobenouser", "sdu_zzprobenouser", "/home/sd/user_accounts/don"],
                                                        "a user that does not exist"),
    (REFUSE, ["chown-account", "daemon", "sdu_daemon", "/home/sd/user_accounts/don"],
                                                        "uid < UID_MIN"),

    # ---- rmtree-account (19 Sep 26, the fifth cycle's witness run).  delacc's
    # ---- OS$DELETE runs as the sdsys session, which cannot remove what the
    # ---- account's user made without group write, so the directory survived
    # ---- DELETE.ACCOUNT.  Exactly one account directory, canonical, or nothing.
    (REFUSE, ["rmtree-account"],                                  "the path is required"),
    (REFUSE, ["rmtree-account", "/home/sd/user_accounts/don", "x"], "no extra argument"),
    (REFUSE, ["rmtree-account", "/"],                             "the root of the machine"),
    (REFUSE, ["rmtree-account", "/etc"],                          "outside the accounts root"),
    (REFUSE, ["rmtree-account", "/home/sd"],                      "the accounts root itself"),
    (REFUSE, ["rmtree-account", "/home/sd/user_accounts"],        "the user accounts root itself"),
    (REFUSE, ["rmtree-account", "/home/sd/group_accounts"],       "the group accounts root itself"),
    (REFUSE, ["rmtree-account", "/home/sd/user_accounts/don/voc"], "inside an account, not the account"),
    (REFUSE, ["rmtree-account", "/home/sd/user_accounts/../user_accounts/don"],
                                                        "not canonical - a .. is refused, not resolved"),
    (REFUSE, ["rmtree-account", "/home/sd/user_accounts/don/"],   "not canonical - a trailing slash"),
    (REFUSE, ["rmtree-account", "home/sd/user_accounts/don"],     "a relative path"),
    (REFUSE, ["rmtree-account", "/home/sd/user_accounts/zzprobenodir"], "does not exist"),
    (REFUSE, ["rmtree-account", "/usr/local/sdsys"],              "SD's own tree"),

    # ---- system accounts are out of reach by uid, not by name, so the rule
    # ---- holds for accounts this test never enumerated.
    (REFUSE, ["passwd", "daemon"],          "uid < UID_MIN"),
    (REFUSE, ["userdel", "bin"],            "uid < UID_MIN"),

    # ---- malformed input.  A leading dash is the one that would otherwise be
    # ---- read as an option by the command underneath.
    (REFUSE, ["passwd", "-rf"],             "leading dash would read as an option"),
    (REFUSE, ["useradd", "../root"],        "path traversal in a name"),
    (REFUSE, ["passwd", "Don"],             "upper case is not a valid name here"),
    (REFUSE, ["passwd", ""],                "empty name"),
    (REFUSE, ["frobnicate", "don"],         "unknown verb"),
    (REFUSE, [],                            "no verb at all"),

    # ---- THE CONTROLS.  If any of these is refused, the helper is not
    # ---- discriminating and every REFUSE above is worthless.
    # 26 Oct 26, F12: passwd/userdel/setpw want the "SD account" stamp now, which an ordinary login does not have - `passwd don` was this file's ALLOW control and is a REFUSE row
    # (the stamped control, with its reasons, is the stamp family: stamp_rows).  groupadd of sdu_<user> wants the user to exist, so the control is a group account's sdg_ group.
    (REFUSE, ["passwd", "don"],                        "an existing user above UID_MIN that SD did not make: no stamp (F12)"),
    (ALLOW,  ["addgroup", "don", "sdusers"],           "SD's own group"),
    (ALLOW,  ["delgroup", "don", "sdusers"],           "SD's own group"),
    (ALLOW,  ["useradd", "sdprobe_nonexistent"],       "a name that does not exist yet"),
    (ALLOW,  ["groupadd", "sdg_probe_nonexistent"],    "an SD group that does not exist yet"),
    (REFUSE, ["groupadd", "sdu_probe_nonexistent"],    "an sdu_ group for a user that does not exist (F12)"),
    (ALLOW,  ["setgid", "/home/sd/user_accounts/don"], "inside the accounts root"),
    (ALLOW,  ["chown-account", "don", "sdu_don", "/home/sd/user_accounts/don"],
                                                        "the USER shape: the account's own directory"),
    (ALLOW,  ["chown-account", "don", "sdu_don", "/home/sd/user_accounts/don/voc"],
                                                        "and a path inside it (the intrinsic's step)"),
    # 26 Oct 26, F12: the sdsys shape is for a GROUP account's files only (its ALLOW rows, on a scratch accounts root, are the chown-group family: chowngrp_rows).
    (REFUSE, ["chown-account", "sdsys", "sdg_probe_nonexistent", "/home/sd/user_accounts/don"],
                                                        "a user account's directory is not a group account's (F12)"),
    # 26 Oct 26, F12b: the OTHER shape takes only what the sdsys user owns, and don's account directory belongs to don (its ALLOW rows, on scratch files with the sdsys uid
    # given by a fixture, are the ownedby family: ownedby_rows).
    (REFUSE, ["chown-account", "root", "sdusers", "/home/sd/user_accounts/don"],
                                                        "the OTHER shape: a directory that belongs to a person, not to sdsys (F12b)"),
    (REFUSE, ["chown-account", "root", "sdusers", "/etc/shadow"],
                                                        "the OTHER shape on root's password hashes (F12b: it was accepted)"),
    (ALLOW,  ["rmtree-account", "/home/sd/user_accounts/don"],   "an account directory (dry run: never acts)"),
]


def main():
    if not os.path.exists(HELPER):
        print(f"REFUSING - helper not found at {HELPER}", file=sys.stderr)
        return 2

    passed = failed = 0
    n_allow = n_refuse = 0
    failures = []

    print(f"driving {HELPER} --dry-run as uid {os.getuid()}\n")

    for expect, argv, note in CASES:
        code, out = run(argv)
        got = ALLOW if code == 0 else REFUSE
        ok = got == expect

        if expect == ALLOW:
            n_allow += 1
        else:
            n_refuse += 1

        if ok:
            passed += 1
        else:
            failed += 1
            failures.append((argv, expect, got, out.strip()))

        first = out.strip().splitlines()[0] if out.strip() else "(no output)"
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {expect:6} sd-elevate {shlex.join(argv):46} | {first}")
        if not ok:
            print(f"         ^ {note}")

    # ---- 10 Sep 26: THE STAMP.  DELETE.ACCOUNT removes a Linux user only when
    # ---- its GECOS reads exactly "SD account" (GPL.BP/IS_SD_USER), so a useradd
    # ---- that stopped writing it would make every later account's user
    # ---- undeletable without a word.  Asserted on the dry run's printed
    # ---- command, which is the command the real run executes.
    stamp_argv = ["useradd", "sdprobe_nonexistent"]
    code, out = run(stamp_argv)
    stamp_ok = code == 0 and "SD account" in out
    first = out.strip().splitlines()[0] if out.strip() else "(no output)"
    print(f"  [{'PASS' if stamp_ok else 'FAIL'}] STAMP  sd-elevate {shlex.join(stamp_argv):46} | {first}")
    if stamp_ok:
        passed += 1
    else:
        failed += 1
        failures.append((stamp_argv, "STAMP 'SD account'", "absent", out.strip()))

    # ---- 20 Sep 26: THE NAME WHITELIST, ASKED WITHOUT ASKING THE MACHINE.
    # ---- sdssh and sdapi are SD's own groups (S.29 part 1), so sd-elevate must
    # ---- accept the NAMES.  Whether it then creates them depends on whether an
    # ---- install already did - which is a fact about this box and has no place
    # ---- in a free check.  So the assertion is on the REASON: the helper may
    # ---- allow, or refuse for existence, but it must never say "not an SD
    # ---- group".  That sentence is the whitelist talking, and it is the only
    # ---- answer that would be a defect.
    for grp in ("sdssh", "sdapi"):
        code, out = run(["groupadd", grp])
        rejected_by_name = "not an SD group" in out
        exists = "already exists" in out
        ok = not rejected_by_name and (code == 0 or exists)
        why = ("created" if code == 0 else
               "refused: already exists (this box has it)" if exists else
               "REFUSED BY THE WHITELIST" if rejected_by_name else
               out.strip().splitlines()[0] if out.strip() else "(no output)")
        print(f"  [{'PASS' if ok else 'FAIL'}] NAME   sd-elevate {shlex.join(['groupadd', grp]):46} | {why}")
        if ok:
            passed += 1
            n_allow += 1
        else:
            failed += 1
            failures.append((["groupadd", grp], "name accepted by the whitelist", why, out.strip()))

    # ---- 17 Oct 26, S.65 slice 2c: sdfiles, the SDNet files-only API route.
    # ---- The same question for the third route group, plus the other half: a
    # ---- name that merely resembles it (a prefix, a suffix, a hyphen, a digit)
    # ---- is not on the whitelist, and none of the four system groups is
    # ---- deletable.  See group_rows() above; `--selftest` runs these same rows
    # ---- against eight mutated copies of the helper.
    grows, gskipped = group_rows()
    for s in gskipped:
        print(f"  SKIPPED {s}")
    for label, ok, detail in grows:
        print(f"  [{'PASS' if ok else 'FAIL'}] GROUP  {label:52} | {detail}")
        if ok:
            passed += 1
            if "is on the whitelist" in label:
                n_allow += 1
            else:
                n_refuse += 1
        else:
            failed += 1
            failures.append(([label], "group rule", "broken", detail))

    # ---- 19 Oct 26: THE RECORD FILES OF A GROUP ACCOUNT.  See record_rows() above; `--selftest` runs the same rows
    # ---- against mutated copies of the helper.
    rrows, _ = record_rows()
    for label, ok, detail in rrows:
        print(f"  [{'PASS' if ok else 'FAIL'}] RECORD {label:60} | {detail}")
        if ok:
            passed += 1
            if label.startswith("sdsys chowns"):
                n_allow += 1
            else:
                n_refuse += 1
        else:
            failed += 1
            failures.append(([label], "record-file rule", "broken", detail))
    if not rrows:
        failed += 1
        failures.append((["record-file"], "rows", "none ran", "the record-file rows did not run: a test that did nothing must fail"))

    # ---- 19 Oct 26, S.67 stage 2 (D7): sdsys-join, see sdsys_rows() above.  The ALLOW rows are the control that makes the REFUSE rows mean something.
    srows, sskipped = sdsys_rows()
    for s in sskipped:
        print(f"  SKIPPED {s}")
    for label, ok, detail in srows:
        print(f"  [{'PASS' if ok else 'FAIL'}] SDSYS  {label:52} | {detail}")
        if ok:
            passed += 1
            if label.startswith("sdsys-join") and " is accepted" in label or label.startswith("...and the command") or "honoured on a dry run" in label:
                n_allow += 1
            else:
                n_refuse += 1
        else:
            failed += 1
            failures.append(([label], "sdsys-join rule", "broken", detail))
    if not srows:
        failed += 1
        failures.append((["sdsys-join"], "rows", "none ran", "the sdsys-join rows did not run: a test that did nothing must fail"))

    # ---- 26 Oct 26, F6: sdsys-leave (leave_rows) and the log lines (log_rows).  The rows that expect the verb to go through are the controls.
    # 26 Oct 26, F12: the stamp, chown-group and groupadd families (their labels begin ALLOW: or REFUSE:).
    for family, rows_fn in (("sdsys-leave", leave_rows), ("log", log_rows), ("stamp", stamp_rows), ("chown-group", chowngrp_rows), ("groupadd", groupadd_rows),
                            ("ownedby", ownedby_rows), ("pwunset", pwunset_rows), ("envtrust", envtrust_rows)):
        lrows, lskipped = rows_fn()
        for s in lskipped:
            print(f"  SKIPPED {s}")
        for label, ok, detail in lrows:
            print(f"  [{'PASS' if ok else 'FAIL'}] {family.upper():11} {label:52} | {detail}")
            if ok:
                passed += 1
                if family in ("stamp", "chown-group", "groupadd", "ownedby", "pwunset", "envtrust"):
                    if label.startswith("ALLOW:"):
                        n_allow += 1
                    else:
                        n_refuse += 1
                elif family == "sdsys-leave" and (" is accepted" in label or label.startswith("...") and "refused" not in label
                                                  or label.startswith("a group that does not list") or "honoured on a dry run" in label):
                    n_allow += 1
                else:
                    n_refuse += 1
            else:
                failed += 1
                failures.append(([label], f"{family} rule", "broken", detail))
        if not lrows:
            failed += 1
            failures.append(([family], "rows", "none ran", f"the {family} rows did not run: a test that did nothing must fail"))

    # ---- 14 Sep 26: WHAT THE REMOTE VERBS WOULD DO, read off the dry run.  An
    # ---- exit code of 0 says the word was accepted, not that ON opens the
    # ---- firewall and LOCAL binds loopback - a swapped pair would pass every
    # ---- ALLOW row above.  Each needle must appear, and each forbidden one must
    # ---- not.
    REMOTE_CONTENT = [
        # 02 Oct 26 - the API port is 4247, fixed (owner); 4243 must not appear.
        (["remote-api", "on"], ["ListenStream=0.0.0.0:4247", "ufw allow 4247/tcp", "systemctl restart sdclient.socket"],
         ["127.0.0.1:4247", "delete allow", "4243"]),
        (["remote-api", "local"], ["ListenStream=127.0.0.1:4247", "ufw delete allow 4247/tcp"],
         ["0.0.0.0:4247", "ufw allow 4247/tcp\n", "4243"]),
        (["remote-api", "off"], ["systemctl disable --now sdclient.socket", "ufw delete allow 4247/tcp"],
         ["ListenStream", "ufw allow 4247/tcp\n", "4243"]),
        (["remote-ssh", "on"], ["ufw allow 22/tcp"], ["delete", "4247"]),
        (["remote-ssh", "off"], ["ufw delete allow 22/tcp"], ["ufw allow 22/tcp\n", "systemctl"]),
    ]
    for argv, needles, forbidden in REMOTE_CONTENT:
        code, out = run(argv)
        missing = [n for n in needles if n not in out]
        present = [f for f in forbidden if f in out]
        ok = code == 0 and not missing and not present
        print(f"  [{'PASS' if ok else 'FAIL'}] PLAN   sd-elevate {shlex.join(argv):46} | "
              f"{'as designed' if ok else ('missing %s, forbidden %s, exit %d' % (missing, present, code))}")
        if ok:
            passed += 1
        else:
            failed += 1
            failures.append((argv, "plan %s" % needles, "missing %s forbidden %s" % (missing, present), out.strip()))

    # ---- 15 Sep 26: RULE DETECTION WHILE ufw IS INACTIVE (witness 13h H5c).
    # ---- The dry run never reads the firewall, so the helpers are lifted out
    # ---- of the script and run against a fake ufw that answers "status" the
    # ---- way an inactive one does - no rules - and "show added" with the
    # ---- rules it has configured.  A helper still reading "ufw status" finds
    # ---- nothing and fails U1 and U4.
    fake_dir = tempfile.mkdtemp(prefix="sdelev-ufw-")
    try:
        fake = os.path.join(fake_dir, "ufw")
        with open(fake, "w") as f:
            f.write("#!/bin/bash\n"
                    "case \"$*\" in\n"
                    "  status|'status verbose') echo 'Status: inactive' ;;\n"
                    "  'show added') printf '%s\\n' "
                    "\"Added user rules (see 'ufw status' for running firewall):\" "
                    "'ufw allow 4247/tcp' 'ufw allow OpenSSH' 'ufw allow 2222/tcp' "
                    "'ufw allow from 192.168.0.0/24 to any port 22 proto tcp' ;;\n"
                    "  *) exit 1 ;;\n"
                    "esac\n")
        os.chmod(fake, 0o755)
        lift = ("eval \"$(sed -n '/^ufw_added()/,/^}/p;/^ufw_has_allow()/,/^}/p;"
                "/^ufw_ssh_rules()/,/^}/p' \"$1\")\"; "
                "type ufw_has_allow >/dev/null 2>&1 && type ufw_ssh_rules >/dev/null 2>&1 "
                "|| { echo 'NOT LIFTED'; exit 9; }; ")
        env = dict(os.environ, PATH=fake_dir + os.pathsep + os.environ.get("PATH", ""))
        UFW_ROWS = [
            ("U1 4247/tcp is found while ufw is inactive", "ufw_has_allow 4247/tcp", 0, None),
            ("U2 a rule that is not configured is not found", "ufw_has_allow 443/tcp", 1, None),
            ("U3 22/tcp is not claimed from 2222/tcp", "ufw_has_allow 22/tcp", 1, None),
            ("U4 the ssh rules are OpenSSH and the port 22 rule, not 2222",
             "ufw_ssh_rules", 0,
             "allow OpenSSH\nallow from 192.168.0.0/24 to any port 22 proto tcp"),
        ]
        for name, call, want_rc, want_out in UFW_ROWS:
            p = subprocess.run(["bash", "-c", lift + call, "lift", HELPER],
                               capture_output=True, text=True, env=env)
            out = (p.stdout or "").strip()
            ok = p.returncode == want_rc and (want_out is None or out == want_out)
            shown = out.replace("\n", " | ") if out else "(no output)"
            print(f"  [{'PASS' if ok else 'FAIL'}] UFW    {name:60} | exit {p.returncode}: {shown}")
            if ok:
                passed += 1
            else:
                failed += 1
                failures.append(([call], "exit %d %r" % (want_rc, want_out),
                                 "exit %d %r" % (p.returncode, out), p.stderr.strip()))
    finally:
        shutil.rmtree(fake_dir, ignore_errors=True)

    # ---- 4 Oct 26: FIREWALLD (owner, 4 Oct: "yes - for both sd core and sd solo").
    # ---- The same lesson as the ufw rows: rules come from the SAVED
    # ---- configuration.  A fake firewall-cmd answers rule queries ONLY with
    # ---- --permanent, and while "stopped" only firewall-offline-cmd knows the
    # ---- rules - so a helper that asked the live firewall would fail F2, F4, F7.
    # ---- PATH is the fakes plus /usr/bin:/bin, so the host's /usr/sbin/ufw is
    # ---- not seen by fw_kind.
    fake_dir = tempfile.mkdtemp(prefix="sdelev-fwd-")
    try:
        with open(os.path.join(fake_dir, "firewall-cmd"), "w") as f:
            f.write("#!/bin/bash\n"
                    "case \"$*\" in\n"
                    "  --state) if [ \"$FAKE_FWD\" = running ]; then echo running; else echo 'not running'; exit 252; fi ;;\n"
                    "  --get-default-zone) echo FedoraServer ;;\n"
                    "  '--permanent --zone=FedoraServer --get-target') echo \"${FAKE_TARGET:-default}\" ;;\n"
                    "  '--permanent --query-port=4247/tcp'|'--permanent --query-service=ssh') [ \"$FAKE_FWD\" = running ] ;;\n"
                    "  '--permanent --list-ports') [ \"$FAKE_FWD\" = running ] || exit 252\n"
                    "     if [ \"${FAKE_RANGE:-}\" = 1 ]; then echo '1025-65535/tcp 1025-65535/udp'; else echo '4247/tcp 4251/tcp'; fi ;;\n"
                    "  *) exit 1 ;;\n"
                    "esac\n")
        with open(os.path.join(fake_dir, "firewall-offline-cmd"), "w") as f:
            f.write("#!/bin/bash\n"
                    "case \"$*\" in\n"
                    "  --query-port=4247/tcp|--query-service=ssh) exit 0 ;;\n"
                    "  *) exit 1 ;;\n"
                    "esac\n")
        for n in ("firewall-cmd", "firewall-offline-cmd"):
            os.chmod(os.path.join(fake_dir, n), 0o755)
        lift = ("eval \"$(sed -n '/^fwd_running()/p;/^fwd_perm()/,/^}/p;/^fwd_state()/,/^}/p;"
                "/^fwd_has_allow()/,/^}/p;/^fwd_has_rule()/,/^}/p;/^fwd_ssh_rules()/,/^}/p;/^fw_kind()/,/^}/p' \"$1\")\"; "
                "type fwd_state >/dev/null 2>&1 && type fwd_ssh_rules >/dev/null 2>&1 && type fw_kind >/dev/null 2>&1 "
                "|| { echo 'NOT LIFTED'; exit 9; }; ")
        base = "/usr/bin" + os.pathsep + "/bin"
        FWD_ROWS = [
            ("F1 a stopped firewalld is 'inactive'", "fwd_state", 0, "inactive", "stopped", True),
            ("F2 stopped: 4247/tcp found in the saved config", "fwd_has_allow 4247/tcp", 0, None, "stopped", True),
            ("F3 stopped: a rule not configured is not found", "fwd_has_allow 443/tcp", 1, None, "stopped", True),
            ("F4 stopped: the ssh service is reported, no port 22", "fwd_ssh_rules", 0, "service ssh", "stopped", True),
            ("F5 running, zone target default -> active-deny", "fwd_state", 0, "active-deny", "running", True),
            ("F6 running, zone target ACCEPT -> active-allow", "FAKE_TARGET=ACCEPT fwd_state", 0, "active-allow", "running", True),
            ("F7 running: 4247/tcp read with --permanent", "fwd_has_allow 4247/tcp", 0, None, "running", True),
            ("F8 fw_kind: no ufw, firewalld running -> firewalld", "fw_kind", 0, "firewalld", "running", True),
            ("F9 fw_kind: neither installed -> none", "fw_kind", 0, "none", "stopped", False),
            # 4 Oct 26: Fedora Workstation's zone carries 1025-65535/tcp.  ALLOWED is
            # not SD'S RULE: removing 4247 there split the distro's range (measured).
            ("F10 Workstation range: 4247 allowed", "FAKE_RANGE=1 fwd_has_allow 4247/tcp", 0, None, "running", True),
            ("F11 Workstation range: but no SD rule to remove", "FAKE_RANGE=1 fwd_has_rule 4247/tcp", 1, None, "running", True),
            ("F12 SD's exact 4247/tcp entry is SD's rule", "fwd_has_rule 4247/tcp", 0, None, "running", True),
            ("F13 4249/tcp is not claimed from the entries", "fwd_has_rule 4249/tcp", 1, None, "running", True),
        ]
        for name, call, want_rc, want_out, state, with_fakes in FWD_ROWS:
            path = (fake_dir + os.pathsep + base) if with_fakes else base
            env = dict(os.environ, PATH=path, FAKE_FWD=state)
            p = subprocess.run(["/bin/bash", "-c", lift + call, "lift", HELPER],
                               capture_output=True, text=True, env=env)
            out = (p.stdout or "").strip()
            ok = p.returncode == want_rc and (want_out is None or out == want_out)
            shown = out.replace("\n", " | ") if out else "(no output)"
            print(f"  [{'PASS' if ok else 'FAIL'}] FWD    {name:60} | exit {p.returncode}: {shown}")
            if ok:
                passed += 1
            else:
                failed += 1
                failures.append(([call], "exit %d %r" % (want_rc, want_out),
                                 "exit %d %r" % (p.returncode, out), p.stderr.strip()))
    finally:
        shutil.rmtree(fake_dir, ignore_errors=True)

    # ---- 19 Sep 26: CRED-OWN (W.10), a person's OWN SD password.  Driven
    # ---- through --dry-run against a fixture SD_SYS_ROOT (a register and a
    # ---- $cred), with SUDO_USER/SUDO_UID as sudo would set them.  The REFUSE
    # ---- rows are the confinement - wrong person, wrong account shape, wrong
    # ---- current password, malformed input; the ALLOW rows are the control,
    # ---- and each must also print the write line naming the caller's OWN
    # ---- record, so an ALLOW that did nothing cannot pass.
    import base64
    fx = tempfile.mkdtemp(prefix="sdelev-cred-")
    try:
        me, my_uid = "don", None
        try:
            import pwd
            my_uid = pwd.getpwnam(me).pw_uid
        except KeyError:
            pass
        os.makedirs(os.path.join(fx, "accounts"))
        os.makedirs(os.path.join(fx, "$cred"))
        def reg(name, group, susp=""):
            with open(os.path.join(fx, "accounts", name), "w") as f:
                f.write(f"/home/sd/user_accounts/{name}\n\n{group}\n\n{susp}\n")
        reg("don", "sdu_don")
        k_old = base64.b64encode(b"\x01" * 32).decode()
        k_new = base64.b64encode(b"\x02" * 32).decode()
        salt = base64.b64encode(b"\x03" * 16).decode()
        def cred_run(mode, lines=None, user=me, uid=my_uid):
            env = dict(os.environ, SD_SYS_ROOT_FIXTURE=fx)
            env.pop("SUDO_USER", None); env.pop("SUDO_UID", None)
            if user is not None:
                env["SUDO_USER"] = user
                env["SUDO_UID"] = str(uid)
            inp = None if lines is None else "\n".join(lines) + "\n"
            p = subprocess.run(["bash", HELPER, "--dry-run", "cred-own", mode],
                               input=inp, capture_output=True, text=True, env=env)
            return p.returncode, (p.stdout or "") + (p.stderr or "")
        def rec(cur, ver="2", mech="SCRAM-SHA-256", s=salt, it="600000", sk=k_new, svk=k_new):
            return [cur, ver, mech, s, it, sk, svk]
        own_write = f"write {fx}/$cred/{me} "
        if my_uid is None:
            print("  [SKIP] cred-own rows: this box has no user 'don' to be the caller")
        else:
            CRED = [
                # (expect, mode, lines, user, uid, needle, note)
                (ALLOW,  "query", None, me, my_uid, "none", "no credential yet: says none"),
                (ALLOW,  "set", rec(""), me, my_uid, own_write, "the FIRST password needs no current one"),
                (REFUSE, "set", rec(""), None, None, "only through sudo", "no SUDO_USER: not reached through sudo"),
                (REFUSE, "set", rec(""), me, my_uid + 1, "does not match", "SUDO_UID disagrees with the user"),
                (REFUSE, "query", None, "root", 0, "root has no SD password", "root is never the caller"),
                (REFUSE, "query", None, "sdsys", 999, "administrator", "sdsys uses MODIFY.PASSWORD as administrator"),
                (REFUSE, "set", rec("")[:-1], me, my_uid, "ended early", "six lines, not seven"),
                (REFUSE, "set", rec("") + ["x"], me, my_uid, "exactly seven", "an eighth line"),
                (REFUSE, "set", rec("", ver="1"), me, my_uid, "version must be 2", "another record version"),
                (REFUSE, "set", rec("", mech="PLAIN"), me, my_uid, "SCRAM-SHA-256", "another mechanism"),
                (REFUSE, "set", rec("", it="12"), me, my_uid, "outside 4096", "iterations below the floor"),
                (REFUSE, "set", rec("", sk="not base64!"), me, my_uid, "StoredKey", "a malformed key"),
                (REFUSE, "set", rec("", svk=base64.b64encode(b"x" * 31).decode()), me, my_uid, "ServerKey", "a 31-byte key"),
                (REFUSE, "set", rec("", s="$(id)"), me, my_uid, "salt", "shell text as a salt"),
                (REFUSE, "verify", [k_old], me, my_uid, "no SD password to check", "verify with no credential"),
            ]
            # then a credential exists: the current password becomes required
            CRED_AFTER = [
                (ALLOW,  "query", None, me, my_uid, "salt " + salt, "the salt and iterations come back"),
                (REFUSE, "set", rec(""), me, my_uid, "current one is required", "a password exists: current required"),
                (REFUSE, "set", rec(k_new), me, my_uid, "not correct", "the wrong current password"),
                # 19 Sep 26: verify, the current password checked before the
                # new one is asked for (the owner at the keyboard, fifth cycle)
                (REFUSE, "verify", [k_new], me, my_uid, "not correct", "verify: the wrong current password"),
                (REFUSE, "verify", [""], me, my_uid, "not correct", "verify: an empty current password"),
                (REFUSE, "verify", [k_old, "x"], me, my_uid, "exactly one line", "verify: a second line"),
                (REFUSE, "verify", [k_old], None, None, "only through sudo", "verify: not reached through sudo"),
                (ALLOW,  "verify", [k_old], me, my_uid, "the current password is correct", "verify: the right one"),
                (ALLOW,  "set", rec(k_old), me, my_uid, own_write, "the right current password"),
            ]
            def drive(rows):
                nonlocal passed, failed, n_allow, n_refuse
                for expect, mode, lines, user, uid, needle, note in rows:
                    code, out = cred_run(mode, lines, user, uid)
                    got = ALLOW if code == 0 else REFUSE
                    ok = got == expect and needle in out
                    n_allow += expect == ALLOW
                    n_refuse += expect == REFUSE
                    passed += ok
                    failed += not ok
                    first = out.strip().splitlines()[0] if out.strip() else "(no output)"
                    print(f"  [{'PASS' if ok else 'FAIL'}] {expect:6} cred-own {mode:5} as {str(user):6} | {first[:70]}")
                    if not ok:
                        print(f"         ^ {note} (wanted {needle!r})")
                        failures.append((["cred-own", mode], f"{expect} + {needle!r}", got, out.strip()))
            drive(CRED)
            with open(os.path.join(fx, "$cred", me), "w") as f:
                f.write(f"2\nSCRAM-SHA-256\n{salt}\n600000\n{k_old}\n{k_old}\n")
            drive(CRED_AFTER)
            reg("don", "sdu_don", susp="S")
            drive([(REFUSE, "query", None, me, my_uid, "suspended", "a suspended account")])
            reg("don", "sdg_team")
            drive([(REFUSE, "query", None, me, my_uid, "not a user's own account", "a register record that is not the user's own")])
    finally:
        shutil.rmtree(fx, ignore_errors=True)

    # ---- 19 Sep 26: SD'S PASSWORD RULE (owner's ruling: 8+ characters, a-z,
    # ---- A-Z, 0-9 and a symbol; printable ASCII only).  Each REFUSE row lacks
    # ---- exactly ONE thing, so a rule that stopped checking any one class
    # ---- fails here; the ALLOW rows are the control.
    # ---- 19 Sep 26: THE TABLE IS NO LONGER KEPT HERE.  It is the rule's spec,
    # ---- it must hold for GPL.BP/PW_COMPLEX and for the port as well, and two
    # ---- copies of a spec drift.  test-pwcomplex-units.py owns it and drives
    # ---- the BASIC through the same rows.  A table that cannot be imported is
    # ---- a REFUSAL, not a silently skipped section.
    spec_path = os.path.join(HERE, "test-pwcomplex-units.py")
    try:
        import importlib.util
        mspec = importlib.util.spec_from_file_location("pwcomplex_units", spec_path)
        pwmod = importlib.util.module_from_spec(mspec)
        mspec.loader.exec_module(pwmod)
        PW_RULE = pwmod.SPEC
    except Exception as e:                                # noqa: BLE001
        print("REFUSING - cannot read the password rule's spec table from %s: %s"
              % (spec_path, e), file=sys.stderr)
        return 2
    if not PW_RULE:
        print("REFUSING - the imported password rule table is empty", file=sys.stderr)
        return 2
    print("  (password rule: %d rows, imported from %s)" % (len(PW_RULE), spec_path))
    for expect, pw, note in PW_RULE:
        p = subprocess.run(["bash", HELPER, "--dry-run", "pw-check"],
                           input=pw + "\n", capture_output=True, text=True)
        got = ALLOW if p.returncode == 0 else REFUSE
        needle = "meets the rule" if expect == ALLOW else "does not meet the rule"
        out = (p.stdout or "") + (p.stderr or "")
        ok = got == expect and needle in out
        n_allow += expect == ALLOW
        n_refuse += expect == REFUSE
        passed += ok
        failed += not ok
        print(f"  [{'PASS' if ok else 'FAIL'}] {expect:6} pw-rule {note}")
        if not ok:
            failures.append((["pw-check", repr(pw)], f"{expect} + {needle!r}", got, out.strip()))

    # ---- setpw: the rule again at the helper's door, the user rules, and one
    # ---- line on stdin only.  Dry run: validates and prints, sets nothing.
    SETPW = [
        (REFUSE, ["setpw", "don"],   "weakpass\n",              "does not meet SD's rule", "a weak password"),
        (REFUSE, ["setpw", "root"],  "Abcdef1!\n",              "root is never a target",  "root"),
        (REFUSE, ["setpw", "sdsys"], "Abcdef1!\n",              "never a target",          "sdsys"),
        (REFUSE, ["setpw", "don"],   "Abcdef1!\nAbcdef1!\n",    "exactly one line",        "a second line"),
        (REFUSE, ["setpw", "don"],   "",                        "on stdin",                "nothing on stdin"),
        (REFUSE, ["setpw", "don", "Abcdef1!"], "",              "SD Core's privileged helper", "the password as an argument"),
        (REFUSE, ["pw-check"],       "Abcdef1!\n",              "for --dry-run only",      "pw-check outside a dry run"),
        (ALLOW,  ["setpw", "don"],   "Abcdef1!\n",              "chpasswd for don",        "a good password (dry run)"),
    ]
    # 26 Oct 26, F12: setpw wants the stamp, which "don" (an ordinary login) does not have, so these rows run with a getent of this test's own that gives "don" the stamp - the rows
    # below it are about the rule and the user rules, as they were.  The stamp itself is the stamp family's (stamp_rows).
    stub_td = tempfile.mkdtemp(prefix="sdelev-setpw-")
    _getent_stub(stub_td)
    setpw_env = dict(os.environ, SD_PATH_PREPEND=stub_td, STUB_PW_USER="don", STUB_PW_GECOS="SD account", STUB_SHADOW_SET="1", STUB_SHADOW_HASH="!")      # F12c/F12e: and no password yet
    for expect, argv, stdin, needle, note in SETPW:
        cmd = ["bash", HELPER] + (argv if argv == ["pw-check"] else ["--dry-run"] + argv)
        p = subprocess.run(cmd, input=stdin, capture_output=True, text=True, env=setpw_env)
        got = ALLOW if p.returncode == 0 else REFUSE
        out = (p.stdout or "") + (p.stderr or "")
        ok = got == expect and needle in out
        n_allow += expect == ALLOW
        n_refuse += expect == REFUSE
        passed += ok
        failed += not ok
        print(f"  [{'PASS' if ok else 'FAIL'}] {expect:6} {' '.join(argv)[:30]:30} | {note}")
        if not ok:
            failures.append((argv, f"{expect} + {needle!r}", got, out.strip()))
    shutil.rmtree(stub_td, ignore_errors=True)

    print()

    # ---- refuse the null case, out loud.  A run that established nothing must
    # ---- not report success.
    if n_allow == 0:
        print("REFUSING - no ALLOW rows ran; nothing proved the helper "
              "discriminates rather than refusing everything", file=sys.stderr)
        return 2
    if n_refuse == 0:
        print("REFUSING - no REFUSE rows ran; nothing tested the validation",
              file=sys.stderr)
        return 2

    print(f"{passed} passed, {failed} failed "
          f"({n_refuse} refusals, {n_allow} controls)")

    if failed:
        print("\nfailures:", file=sys.stderr)
        for argv, expect, got, out in failures:
            print(f"  sd-elevate {shlex.join(argv)}: expected {expect}, got {got}",
                  file=sys.stderr)
            print(f"    {out}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv[1:] else main())
