#!/usr/bin/env python3
"""Unit test for gplbld/sd-elevate, SD Core for Linux.

Written 09 Sep 26 for PRE_RELEASE 14.

WHAT IT IS FOR.  sd-elevate is the one command a member of sdadmin may run as
root, so everything that stops that being a root shell lives in its argument
validation.  This drives that validation through --dry-run, which acts on
nothing and needs no privilege, so the escalation attempts below can be run
safely as an ordinary user.

THE TWO HALVES MATTER EQUALLY.  The REFUSE rows are the point of the helper.
The ALLOW rows are the control: a script that refused everything would pass
every REFUSE row and be useless, and that failure mode is invisible without
them.  This is CLAUDE.md's rule that a test which passes because it did nothing
must fail - so the run REFUSES ITS OWN NULL CASE at the bottom if either half
is empty, or if the helper is missing, rather than reporting 0 of 0 as success.
"""

import os
import shlex
import subprocess
import sys

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
    (REFUSE, ["addgroup", "don", "sudo"],   "add yourself to sudo - the classic"),
    (REFUSE, ["addgroup", "don", "wheel"],  "the RHEL/Arch spelling of the same"),
    (REFUSE, ["addgroup", "don", "docker"], "docker group is root-equivalent"),
    (REFUSE, ["addgroup", "don", "lxd"],    "lxd group is root-equivalent"),
    (REFUSE, ["addgroup", "don", "adm"],    "log-reading group, still not SD's"),
    (REFUSE, ["groupadd", "sudo"],          "not an SD group"),
    (REFUSE, ["groupdel", "sudo"],          "not an SD group"),
    (REFUSE, ["delgroup", "don", "sudo"],   "not an SD group"),

    # ---- sdadmin, added to the whitelist 09 Sep 26.  It is the OS half of an
    # ---- SD administrator, so it is the one group whose entry has to be
    # ---- deliberate.  These four rows are what make it deliberate: the
    # ---- operation is allowed for a real SD user and for nobody else, and
    # ---- REMOVING the group from the whitelist would fail two of them, which
    # ---- is the drift this guards against.
    (REFUSE, ["addgroup", "root", "sdadmin"],  "root can never be made an SD administrator"),
    (REFUSE, ["addgroup", "sdsys", "sdadmin"], "sdsys is an account, not a person"),
    (REFUSE, ["groupdel", "sdadmin"],          "the group SD's own sudoers rule names must not be deletable"),
    (REFUSE, ["groupdel", "sdusers"],          "deleting it unregisters every SD user at once - exposed BEFORE sdadmin joined"),
    (ALLOW,  ["addgroup", "don", "sdadmin"],   "the point of the whitelist entry: an administrator may make one"),
    (ALLOW,  ["delgroup", "don", "sdadmin"],   "and unmake one - MODIFY.ACCOUNT's demotion path"),
    (REFUSE, ["setgid", "/etc"],            "outside the accounts root"),
    (REFUSE, ["setgid", "/"],               "outside the accounts root"),
    (REFUSE, ["setgid", "/usr/local/sdsys"], "SD's own tree is still not the accounts root"),

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
