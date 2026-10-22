#!/usr/bin/env python3
"""Unit test for gplbld/sd-elevate, SD Core for Linux.

Written 09 Sep 26 for PRE_RELEASE 14.

19 Oct 26 dm INTEGRATION of the S.67 rows below with 981a36a's record-file rows (record_rows, RECORD_MUTANTS): one run() that takes `env` and `dry`, and
one `--selftest` loop over the three families (group, record-file, sdsys-join) with _kill_mutants; a null guard on the record-file rows in the plain run too.
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


def run(args, helper=None, env=None, dry=True):
    """Run the helper in dry-run mode.  Returns (exit_code, stdout+stderr).

    `helper` is a mutated copy when --selftest drives the group rows.  `env` is added to the environment (a fixture the helper honours on a
    dry run only: SD_ACCT_ROOT for the record-file rows, SD_GROUP_FIXTURE and SD_GW_GROUP_FIXTURE for the sdsys group rows); `dry` False runs
    the helper WITHOUT --dry-run, which as an ordinary user can only refuse (its checks come before its test for root) - the rows that need
    to see a fixture ignored use it."""
    e = dict(os.environ)
    for k in ("SD_GROUP_FIXTURE", "SD_GW_GROUP_FIXTURE"):
        e.pop(k, None)                      # nothing leaks in; a row sets what it needs
    e.update(env or {})
    p = subprocess.run(
        ["bash", helper or HELPER] + (["--dry-run"] if dry else []) + args,
        capture_output=True, text=True, env=e,
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


# Names that merely begin with, end with, or look like sdfiles.
NOT_SDFILES = ["sdfilesx", "sdfiles2", "sdfiles-x", "sdfile", "xsdfiles",
               # 18 Oct 26, S.65 write group: lookalikes of sdfileswrite
               "sdfileswrit", "sdfileswritex", "sdfileswrite2", "sdfileswrite-x", "xsdfileswrite",
               # 21 Oct 26, S.73 item 3: lookalikes of sdfilesadmin
               "sdfilesadmi", "sdfilesadminx", "sdfilesadmin2", "sdfilesadmin-x", "xsdfilesadmin"]


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
    code, out = run(["passwd", who], helper)
    if code != 0:
        skipped.append(f"addgroup/delgroup: '{who}' is not an SD user here ({out.strip().splitlines()[0] if out.strip() else 'no output'})")
        who = None

    ask("groupadd sdfiles is on the whitelist", ["groupadd", "sdfiles"], _accepted)
    # 18 Oct 26, S.65 write group: sdfileswrite, the right to change files over the files-only route, is the fourth route group.
    ask("groupadd sdfileswrite is on the whitelist", ["groupadd", "sdfileswrite"], _accepted)
    # 21 Oct 26, S.73 item 3: sdfilesadmin, the right to administer files over the files-only route, is the fifth route group.
    ask("groupadd sdfilesadmin is on the whitelist", ["groupadd", "sdfilesadmin"], _accepted)
    if who:
        ask("addgroup <me> sdfiles is on the whitelist", ["addgroup", who, "sdfiles"], _accepted)
        ask("delgroup <me> sdfiles is on the whitelist", ["delgroup", who, "sdfiles"], _accepted)
        ask("addgroup <me> sdfileswrite is on the whitelist", ["addgroup", who, "sdfileswrite"], _accepted)
        ask("delgroup <me> sdfileswrite is on the whitelist", ["delgroup", who, "sdfileswrite"], _accepted)
        ask("addgroup <me> sdfilesadmin is on the whitelist", ["addgroup", who, "sdfilesadmin"], _accepted)
        ask("delgroup <me> sdfilesadmin is on the whitelist", ["delgroup", who, "sdfilesadmin"], _accepted)
    for grp in ("sdfiles", "sdfileswrite", "sdfilesadmin", "sdusers", "sdssh", "sdapi"):
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
_WL = "sdusers|sdssh|sdapi|sdfiles|sdfileswrite|sdfilesadmin) : ;;"
_UD = "      sdusers|sdssh|sdapi|sdfiles|sdfileswrite|sdfilesadmin)\n        die"
GROUP_MUTANTS = [
    ("sdfiles dropped from the whitelist", _WL, "sdusers|sdssh|sdapi|sdfileswrite|sdfilesadmin) : ;;"),
    ("sdfiles matched as a prefix", _WL, "sdusers|sdssh|sdapi|sdfiles*|sdfileswrite|sdfilesadmin) : ;;"),
    ("whitelist widened to sd*", _WL, "sdusers|sdssh|sdapi|sd*) : ;;"),
    ("whitelist refuses nothing",
     "*) die \"'$group' is not an SD group", "*) : ;; # \"'$group' is not an SD group"),
    ("sdfiles made deletable", _UD, "      sdusers|sdssh|sdapi|sdfileswrite|sdfilesadmin)\n        die"),
    ("sdapi made deletable", _UD, "      sdusers|sdssh|sdfiles|sdfileswrite|sdfilesadmin)\n        die"),
    ("sdssh made deletable", _UD, "      sdusers|sdapi|sdfiles|sdfileswrite|sdfilesadmin)\n        die"),
    ("sdusers made deletable", _UD, "      sdssh|sdapi|sdfiles|sdfileswrite|sdfilesadmin)\n        die"),
    # 18 Oct 26, S.65 write group
    ("sdfileswrite dropped from the whitelist", _WL, "sdusers|sdssh|sdapi|sdfiles|sdfilesadmin) : ;;"),
    ("sdfileswrite matched as a prefix", _WL, "sdusers|sdssh|sdapi|sdfiles|sdfileswrite*|sdfilesadmin) : ;;"),
    ("sdfileswrite made deletable", _UD, "      sdusers|sdssh|sdapi|sdfiles|sdfilesadmin)\n        die"),
    # 21 Oct 26, S.73 item 3: the fifth route group
    ("sdfilesadmin dropped from the whitelist", _WL, "sdusers|sdssh|sdapi|sdfiles|sdfileswrite) : ;;"),
    ("sdfilesadmin matched as a prefix", _WL, "sdusers|sdssh|sdapi|sdfiles|sdfileswrite|sdfilesadmin*) : ;;"),
    ("sdfilesadmin made deletable", _UD, "      sdusers|sdssh|sdapi|sdfiles|sdfileswrite)\n        die"),
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
    code, out = run(["passwd", who], helper)
    if code != 0:
        skipped.append(f"sdsys-join: '{who}' is not an SD user here ({out.strip().splitlines()[0] if out.strip() else 'no output'})")
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
    for family, rows_fn, mutants in (("group", group_rows, GROUP_MUTANTS), ("record-file", record_rows, RECORD_MUTANTS),
                                     ("sdsys-join", sdsys_rows, SDSYS_MUTANTS)):
        rows, skipped = rows_fn()
        for s in skipped:
            print(f"  SKIPPED {s}")
        if len(rows) < 10:
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
    (ALLOW,  ["passwd", "don"],                        "an ordinary SD user"),
    (ALLOW,  ["addgroup", "don", "sdusers"],           "SD's own group"),
    (ALLOW,  ["delgroup", "don", "sdusers"],           "SD's own group"),
    (ALLOW,  ["useradd", "sdprobe_nonexistent"],       "a name that does not exist yet"),
    (ALLOW,  ["groupadd", "sdu_probe_nonexistent"],    "an SD group that does not exist yet"),
    (ALLOW,  ["setgid", "/home/sd/user_accounts/don"], "inside the accounts root"),
    (ALLOW,  ["chown-account", "don", "sdu_don", "/home/sd/user_accounts/don"],
                                                        "the USER shape: the account's own directory"),
    (ALLOW,  ["chown-account", "don", "sdu_don", "/home/sd/user_accounts/don/voc"],
                                                        "and a path inside it (the intrinsic's step)"),
    (ALLOW,  ["chown-account", "sdsys", "sdg_probe_nonexistent", "/home/sd/user_accounts/don"],
                                                        "the GROUP shape: sdsys, inside the accounts root"),
    (ALLOW,  ["chown-account", "root", "sdusers", "/home/sd/user_accounts/don"],
                                                        "the OTHER shape: to root, which grants the caller nothing"),
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
    for expect, argv, stdin, needle, note in SETPW:
        cmd = ["bash", HELPER] + (argv if argv == ["pw-check"] else ["--dry-run"] + argv)
        p = subprocess.run(cmd, input=stdin, capture_output=True, text=True)
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
