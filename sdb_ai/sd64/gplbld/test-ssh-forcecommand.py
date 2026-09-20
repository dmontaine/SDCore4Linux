#!/usr/bin/env python3
"""Unit test for gplbld/ssh-forcecommand.sh, SD Core for Linux.

Written 10 Sep 26 for PRE_RELEASE 13.

WHAT IT IS FOR.  ssh-forcecommand.sh edits sshd_config, the most lock-out-
sensitive file this project touches.  Its safety rests on four things: it writes
a byte-stable, exactly-reversible fenced block; it REFUSES a customised config
rather than stomping it; it validates a candidate with sshd -t BEFORE the live
file changes and never corrupts the live file; and it refuses to write at all
when it cannot validate.  This drives all four against a scratch sshd_config and
a stub sshd, so no root and no real ssh server are needed.

THE TWO HALVES MATTER EQUALLY (CLAUDE.md).  The REFUSE rows are the point; the
ALLOW/round-trip rows are the control, because a script that refused everything
would pass every REFUSE row and be useless.  The run REFUSES ITS OWN NULL CASE
at the end if either half is empty or the helper is missing, rather than
reporting 0 of 0 as a pass.

20 Sep 26 - S.29 PART 3 ADDS THE ROUTE ARM, AND ONE ROW HERE MEASURES sshd
ITSELF.  The block now has three arms and the narrow "Match Group
sdusers,!sdsys,!sdssh" one has to come FIRST, because sshd takes the first
obtained value for a keyword; get the order wrong and every SD account still
reaches sd, so the route words go back to being bookkeeping and nothing in the
transcript says so.  Two kinds of row cover it:

  * STRUCTURE rows read the written block - three arms, the narrow one before
    the general one, forwarding shut on the narrow one.  They test OUR string.
  * THE ORDER row asks the REAL sshd on this machine which of two identical
    Match arms wins, with a throwaway host key and no root.  It tests the
    ASSUMPTION the block is built on, which our own string cannot.  Where
    there is no sshd or no ssh-keygen it reports SKIP and is counted and
    printed as a skip - never as a pass.

And --refuse, the mode the refusal arm runs, is driven directly: it must exit
non-zero, name the user, and take its wording from the message file rather than
carry a copy.  A row drives it with the message file missing too, because a
refusal that fails open when it cannot find its text is not a refusal.
"""

import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HELPER = os.path.join(HERE, "ssh-forcecommand.sh")
MESSAGES = os.path.abspath(os.path.join(HERE, os.pardir, "sdsys", "messages"))
END_MARKER = "# --- END SD ssh-only model ---"
NARROW_ARM = "Match Group sdusers,!sdsys,!sdssh"
GENERAL_ARM = "Match Group sdusers,!sdsys"

# A stub sshd: `sshd -t -f FILE`.  Exits 0, or 1 when STUB_FAIL=1, so the
# rollback path can be driven without a config sshd would genuinely reject.
STUB_SSHD = """#!/bin/bash
exit ${STUB_FAIL:-0}
"""

PRISTINE = """# a perfectly ordinary sshd_config
Port 22
PermitRootLogin prohibit-password
Subsystem sftp /usr/lib/openssh/sftp-server
"""

results = []  # (kind, desc, ok)  kind in {"allow","refuse","state","order"}
skipped = []  # (desc, why) - printed, counted, never scored as a pass


def record(kind, desc, ok):
    results.append((kind, desc, ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {kind:6} {desc}")


def skip(desc, why):
    skipped.append((desc, why))
    print(f"  [SKIP] {'order':6} {desc}: {why}")


def run(mode, config, *, sshd, force_cmd=None, stub_fail=False,
        refuse_bin=None, msg_dir=None):
    env = dict(os.environ)
    env["SD_SSHD_CONFIG"] = config
    env["SD_SSHD_BIN"] = sshd            # set => authoritative (empty => none)
    env["SD_SSH_FORCECOMMAND"] = force_cmd if force_cmd is not None else sshd
    # 20 Sep 26 - the refusal arm's command must exist for --install to write
    # the block, so it defaults to the same stub the other target does.
    env["SD_SSH_REFUSE_BIN"] = refuse_bin if refuse_bin is not None else sshd
    if msg_dir is not None:
        env["SD_MESSAGE_DIR"] = msg_dir
    if stub_fail:
        env["STUB_FAIL"] = "1"
    p = subprocess.run(["bash", HELPER, mode], capture_output=True, text=True, env=env)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def arm_order(text):
    """Line numbers of the narrow and the general Match arm, or (None, None).

    Line-based, because GENERAL_ARM is a PREFIX of NARROW_ARM - a substring
    search for the general arm finds the narrow one and the ordering row would
    compare a line with itself and pass whatever the block said.
    """
    narrow = general = None
    for i, line in enumerate(text.splitlines()):
        stripped = line.strip()
        if stripped == NARROW_ARM and narrow is None:
            narrow = i
        elif stripped == GENERAL_ARM and general is None:
            general = i
    return narrow, general


def read(path):
    with open(path) as f:
        return f.read()


def write(path, text):
    with open(path, "w") as f:
        f.write(text)


def main():
    if not os.path.exists(HELPER):
        print(f"REFUSING - helper not found at {HELPER}", file=sys.stderr)
        return 2

    print(f"driving {HELPER} against scratch configs as uid {os.getuid()}\n")

    tmp = tempfile.mkdtemp(prefix="sd-sshfc-")
    stub = os.path.join(tmp, "sshd")
    write(stub, STUB_SSHD)
    os.chmod(stub, 0o755)

    cfg = os.path.join(tmp, "sshd_config")

    # 1. Pristine config: --install appends the block and reports success.
    write(cfg, PRISTINE)
    code, out = run("--install", cfg, sshd=stub)
    record("allow", "install into a pristine config succeeds",
           code == 0 and END_MARKER in read(cfg))
    record("state", "backup sshd_config.before-sd was created",
           os.path.exists(cfg + ".before-sd"))
    record("state", "the ForceCommand line is present",
           "ForceCommand" in read(cfg) and "Match Group sdusers,!sdsys" in read(cfg))
    record("state", "sdsys is denied network login in the block",
           "Match User sdsys" in read(cfg) and "DenyUsers sdsys" in read(cfg))

    # 1b. 20 Sep 26 (S.29 part 3): the route arm, and its ORDER.  The narrow
    #     arm has to precede the general one or sshd's first-obtained-value
    #     rule hands every SD account the sd ForceCommand and the sdssh route
    #     enforces nothing.  Both line numbers are required to exist: a block
    #     missing an arm must FAIL here, not compare None with None.
    narrow, general = arm_order(read(cfg))
    record("state", "the block carries the no-sdssh arm and the general arm",
           narrow is not None and general is not None)
    record("state", "the no-sdssh arm comes FIRST (sshd takes the first value)",
           narrow is not None and general is not None and narrow < general)
    record("state", "the no-sdssh arm's ForceCommand is --refuse, not sd",
           f"ForceCommand {stub} --refuse" in read(cfg))
    for directive in ("AllowTcpForwarding no", "AllowStreamLocalForwarding no",
                      "AllowAgentForwarding no", "PermitTunnel no"):
        record("state", f"no ssh route also means no tunnel: {directive}",
               directive in read(cfg))

    # 2. Idempotent: a second install does not stack a second block.
    code, out = run("--install", cfg, sshd=stub)
    record("allow", "a second install is idempotent (exactly one block)",
           code == 0 and read(cfg).count(END_MARKER) == 1)

    # 3. Exact inverse: remove returns the file to byte-for-byte the original.
    code, out = run("--remove", cfg, sshd=stub)
    record("allow", "remove succeeds", code == 0)
    record("state", "remove restores the config byte-for-byte",
           read(cfg) == PRISTINE)

    # 4. Remove when there is no block: nothing to do, still exit 0.
    code, out = run("--remove", cfg, sshd=stub)
    record("allow", "remove with no block present is a clean no-op", code == 0)

    # 5. Conflict: an existing ForceCommand is the admin's policy -> REFUSE.
    write(cfg, PRISTINE + "ForceCommand /usr/bin/tmux\n")
    before = read(cfg)
    code, out = run("--install", cfg, sshd=stub)
    record("refuse", "install refuses when a ForceCommand already exists", code == 2)
    record("state", "the refused config is left untouched", read(cfg) == before)

    # 6. Conflict: an existing Match rule naming an SD group -> REFUSE.
    write(cfg, PRISTINE + "Match Group sdusers\n    X11Forwarding yes\n")
    code, out = run("--install", cfg, sshd=stub)
    record("refuse", "install refuses a pre-existing Match rule naming an SD group",
           code == 2)

    # 6b. 18 Sep 26 (S.28): a pre-existing DenyUsers sdsys says the same thing
    #    the block says, so it is NOT a conflict - install proceeds, and the
    #    block is still written exactly once.
    write(cfg, PRISTINE + "DenyUsers sdsys\n")
    code, out = run("--install", cfg, sshd=stub)
    record("allow", "install proceeds past a matching pre-existing DenyUsers sdsys",
           code == 0 and read(cfg).count(END_MARKER) == 1)

    # 7. Control: a benign connection restriction is NOT a conflict.  Guards
    #    against over-refusing, which would make the feature unusable on any
    #    machine whose admin set AllowGroups for unrelated reasons.
    write(cfg, PRISTINE + "AllowGroups sdusers sdadmin staff\n")
    code, out = run("--install", cfg, sshd=stub)
    record("allow", "install proceeds past an unrelated AllowGroups line",
           code == 0 and END_MARKER in read(cfg))

    # 8. sshd -t rejects the candidate: FAIL, and the live file is untouched.
    write(cfg, PRISTINE)
    before = read(cfg)
    code, out = run("--install", cfg, sshd=stub, stub_fail=True)
    record("refuse", "install fails when sshd -t rejects the candidate", code == 1)
    record("state", "a rejected candidate never reaches the live config",
           read(cfg) == before and END_MARKER not in read(cfg))

    # 9. No sshd to validate with: REFUSE rather than write blind.
    write(cfg, PRISTINE)
    before = read(cfg)
    code, out = run("--install", cfg, sshd="")   # empty => none found
    record("refuse", "install refuses when no sshd can validate the result", code == 2)
    record("state", "nothing is written when validation is impossible",
           read(cfg) == before)

    # 10. ForceCommand target missing: refuse to point at an absent sd.
    write(cfg, PRISTINE)
    code, out = run("--install", cfg, sshd=stub,
                    force_cmd=os.path.join(tmp, "no-such-sd"))
    record("refuse", "install refuses to write a ForceCommand to a missing sd",
           code == 2)

    # 11. 20 Sep 26 - the same rule for the refusal arm's command.  A block
    #     naming a command that is not there closes the connection with no
    #     explanation, so a withdrawn ssh route is indistinguishable from a
    #     broken install.
    write(cfg, PRISTINE)
    before = read(cfg)
    code, out = run("--install", cfg, sshd=stub,
                    refuse_bin=os.path.join(tmp, "no-such-refusal"))
    record("refuse", "install refuses to point the no-sdssh arm at a missing command",
           code == 2)
    record("state", "and nothing is written in that case", read(cfg) == before)

    # 12. --refuse itself: the mode an ssh login without the route actually
    #     runs.  Non-zero exit, the user named, the wording taken from the
    #     message file.  The repository's own sdsys/messages is used, so a row
    #     here fails if 10074 is ever deleted or reworded past recognition.
    if os.path.isfile(os.path.join(MESSAGES, "10074")):
        env_user = os.environ.get("USER") or str(os.getuid())
        p = subprocess.run(["bash", HELPER, "--refuse"], capture_output=True,
                           text=True, env={**os.environ, "SD_MESSAGE_DIR": MESSAGES})
        said = (p.stdout or "") + (p.stderr or "")
        record("refuse", "--refuse exits non-zero", p.returncode != 0)
        record("state", "--refuse says 10074's words",
               "is not permitted to reach SD over ssh" in said)
        record("state", "--refuse names the user in place of %1",
               env_user in said and "%1" not in said)
        record("state", "--refuse says nothing on stdout (stderr is the channel)",
               (p.stdout or "") == "")
    else:
        skip("--refuse reads message 10074", f"no 10074 under {MESSAGES}")

    # 13. --refuse with no readable message file STILL refuses.  A refusal that
    #     falls open when it cannot find its text is not a refusal, and this is
    #     the row that would catch it.
    p = subprocess.run(["bash", HELPER, "--refuse"], capture_output=True, text=True,
                       env={**os.environ, "SD_MESSAGE_DIR": os.path.join(tmp, "no-such-dir")})
    said = (p.stdout or "") + (p.stderr or "")
    record("refuse", "--refuse still exits non-zero with the message file missing",
           p.returncode != 0)
    record("state", "and it names the file it could not read",
           os.path.join(tmp, "no-such-dir", "10074") in said)

    # 14. THE ORDER ROW: the real sshd on this machine, not our own string.
    #     Two identical Match arms with different ForceCommands; whichever the
    #     server reports is the rule the block is built on.  Match User, not
    #     Match Group, because a unit test cannot create Linux groups - the
    #     keyword-precedence rule is the same either way.
    real_sshd = None
    for cand in ("/usr/sbin/sshd", "/usr/bin/sshd", "/sbin/sshd"):
        if os.access(cand, os.X_OK):
            real_sshd = cand
            break
    keygen = subprocess.run(["sh", "-c", "command -v ssh-keygen"],
                            capture_output=True, text=True).stdout.strip()
    if real_sshd and keygen:
        hostkey = os.path.join(tmp, "orderkey")
        kg = subprocess.run([keygen, "-q", "-t", "ed25519", "-N", "", "-f", hostkey],
                            capture_output=True, text=True)
        if kg.returncode != 0:
            skip("sshd takes the FIRST matching arm's ForceCommand",
                 "ssh-keygen could not make a throwaway host key")
        else:
            who = os.environ.get("USER") or subprocess.run(
                ["id", "-un"], capture_output=True, text=True).stdout.strip()
            probe = os.path.join(tmp, "order.conf")
            write(probe, f"HostKey {hostkey}\n"
                         f"Match User {who}\n    ForceCommand /bin/sd-first\n"
                         f"Match User {who}\n    ForceCommand /bin/sd-second\n")
            q = subprocess.run([real_sshd, "-T", "-f", probe,
                                "-C", f"user={who},host=h,addr=127.0.0.1"],
                               capture_output=True, text=True)
            lines = [ln.strip() for ln in (q.stdout or "").splitlines()
                     if ln.strip().lower().startswith("forcecommand ")]
            if q.returncode != 0 or not lines:
                skip("sshd takes the FIRST matching arm's ForceCommand",
                     f"{real_sshd} -T did not report a ForceCommand: "
                     f"{(q.stderr or '').strip()[:120] or 'no output'}")
            else:
                print(f"  ({real_sshd} -T reported: {lines[0]})")
                record("order", "sshd takes the FIRST matching arm's ForceCommand",
                       lines[0] == "ForceCommand /bin/sd-first")
    else:
        skip("sshd takes the FIRST matching arm's ForceCommand",
             "no sshd binary and/or no ssh-keygen on this machine")

    # ---- tally + null-case refusal --------------------------------------
    print()
    n_allow = sum(1 for k, _, _ in results if k == "allow")
    n_refuse = sum(1 for k, _, _ in results if k == "refuse")
    passed = sum(1 for _, _, ok in results if ok)
    failed = len(results) - passed

    if n_allow == 0:
        print("REFUSING - no ALLOW rows ran; nothing proved the helper writes at all",
              file=sys.stderr)
        return 2
    if n_refuse == 0:
        print("REFUSING - no REFUSE rows ran; nothing tested the safety refusals",
              file=sys.stderr)
        return 2

    print(f"{passed} passed, {failed} failed, {len(skipped)} skipped "
          f"({n_refuse} refusals, {n_allow} writes, "
          f"{len(results) - n_allow - n_refuse} state/order checks)")

    # 20 Sep 26 - A SKIP IS PRINTED AGAIN AT THE END, not buried mid-transcript.
    # The order row is the only one that can skip, and it is the one whose
    # absence a reader must not mistake for a pass.
    if skipped:
        print("skipped (NOT passed):")
        for desc, why in skipped:
            print(f"  {desc}: {why}")

    if failed:
        print("\nfailures:", file=sys.stderr)
        for kind, desc, ok in results:
            if not ok:
                print(f"  [{kind}] {desc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
