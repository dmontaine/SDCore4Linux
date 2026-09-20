#!/usr/bin/env python3
"""Unit test for gplbld/sd-elevate, SD Core for Linux.

Written 09 Sep 26 for PRE_RELEASE 14.

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


def run(args):
    """Run the helper in dry-run mode.  Returns (exit_code, stdout+stderr)."""
    p = subprocess.run(
        ["bash", HELPER, "--dry-run"] + args,
        capture_output=True, text=True,
    )
    return p.returncode, (p.stdout or "") + (p.stderr or "")


# Each row: (expectation, argv, note).  `note` says WHY the row exists, so a
# later reader can tell a deliberate case from a filler one.
CASES = [
    # ---- the escalation attempts.  Every one of these is a way the eight
    # ---- raw sudo commands would have handed out root.
    (REFUSE, ["passwd", "root"],            "sudo passwd root - own the machine"),
    (REFUSE, ["passwd", "sdsys"],           "SD's own system account"),
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
    (ALLOW,  ["groupadd", "sdssh"],          "SD may create its own ssh route group"),
    (ALLOW,  ["groupadd", "sdapi"],          "SD may create its own API route group"),

    # ---- remote-api / remote-ssh, 14 Sep 26 (S.13).  A fixed keyword and
    # ---- nothing else reaches them, so the refusals are the wrong word, a
    # ---- missing word and an extra argument; the content of the allowed ones
    # ---- is asserted below (REMOTE_CONTENT), not just their exit code.
    (REFUSE, ["remote-api", "wide"],           "not one of on/local/off/show"),
    (REFUSE, ["remote-api", "0.0.0.0:4243"],   "an address is never taken from the caller"),
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

    # ---- 14 Sep 26: WHAT THE REMOTE VERBS WOULD DO, read off the dry run.  An
    # ---- exit code of 0 says the word was accepted, not that ON opens the
    # ---- firewall and LOCAL binds loopback - a swapped pair would pass every
    # ---- ALLOW row above.  Each needle must appear, and each forbidden one must
    # ---- not.
    REMOTE_CONTENT = [
        (["remote-api", "on"], ["ListenStream=0.0.0.0:4243", "ufw allow 4243/tcp", "systemctl restart sdclient.socket"],
         ["127.0.0.1:4243", "delete allow"]),
        (["remote-api", "local"], ["ListenStream=127.0.0.1:4243", "ufw delete allow 4243/tcp"],
         ["0.0.0.0:4243", "ufw allow 4243/tcp\n"]),
        (["remote-api", "off"], ["systemctl disable --now sdclient.socket", "ufw delete allow 4243/tcp"],
         ["ListenStream", "ufw allow 4243/tcp\n"]),
        (["remote-ssh", "on"], ["ufw allow 22/tcp"], ["delete", "4243"]),
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
                    "'ufw allow 4243/tcp' 'ufw allow OpenSSH' 'ufw allow 2222/tcp' "
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
            ("U1 4243/tcp is found while ufw is inactive", "ufw_has_allow 4243/tcp", 0, None),
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
    sys.exit(main())
