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
"""

import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HELPER = os.path.join(HERE, "ssh-forcecommand.sh")
END_MARKER = "# --- END SD ssh-only model ---"

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

results = []  # (kind, desc, ok)  kind in {"allow","refuse","state"}


def record(kind, desc, ok):
    results.append((kind, desc, ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {kind:6} {desc}")


def run(mode, config, *, sshd, force_cmd=None, stub_fail=False):
    env = dict(os.environ)
    env["SD_SSHD_CONFIG"] = config
    env["SD_SSHD_BIN"] = sshd            # set => authoritative (empty => none)
    env["SD_SSH_FORCECOMMAND"] = force_cmd if force_cmd is not None else sshd
    if stub_fail:
        env["STUB_FAIL"] = "1"
    p = subprocess.run(["bash", HELPER, mode], capture_output=True, text=True, env=env)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


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
           "ForceCommand" in read(cfg) and "Match Group sdusers,!sdadmin" in read(cfg))

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
    write(cfg, PRISTINE + "Match Group sdadmin\n    X11Forwarding yes\n")
    code, out = run("--install", cfg, sshd=stub)
    record("refuse", "install refuses a pre-existing Match rule naming an SD group",
           code == 2)

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

    print(f"{passed} passed, {failed} failed "
          f"({n_refuse} refusals, {n_allow} writes, "
          f"{len(results) - n_allow - n_refuse} state checks)")

    if failed:
        print("\nfailures:", file=sys.stderr)
        for kind, desc, ok in results:
            if not ok:
                print(f"  [{kind}] {desc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
