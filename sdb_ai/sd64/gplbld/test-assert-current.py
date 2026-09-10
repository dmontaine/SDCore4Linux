#!/usr/bin/env python3
#
# test-assert-current.py - drive every arm of assert-current.py against a
#                          fixture tree, including the arms that must FAIL.
#
#   cd sdb_ai/sd64 && python3 gplbld/test-assert-current.py
#
# Exit 0 all rows passed, 1 a row failed, 2 the harness could not run.
#
# WHY A GUARD NEEDS ITS OWN TEST, WHICH IS NOT AN OBVIOUS THING TO SPEND TIME
# ON.  assert-current exists to stop a green result being believed.  If IT is
# wrong in the "current" direction it does not merely fail to help - it signs
# off the exact measurement it was written to refuse, and it does so quietly.
# So each row below names the answer AND the reason, and the fixture is built
# to produce that reason and no other.
#
# EVERY ROW BUILDS A REAL GIT REPOSITORY.  Nothing is stubbed: the checks run
# git for real, so a fixture that git would reject is a fixture that proves
# nothing.  origin/main is a real remote-tracking ref, made with update-ref.
#
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
GUARD = os.path.join(HERE, "assert-current.py")

CURRENT, STALE, UNKNOWN = 0, 1, 2
NAMES = {0: "CURRENT", 1: "STALE", 2: "UNKNOWN"}

passed = failed = 0


def git(repo, *args):
    p = subprocess.run(["git", "-C", repo] + list(args),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       text=True)
    if p.returncode != 0:
        raise RuntimeError("git %s failed: %s" % (" ".join(args), p.stdout))
    return p.stdout.strip()


def touch(path, mtime=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write("x\n")
    if mtime is not None:
        os.utime(path, (mtime, mtime))


def build(tmp, *, dirty=False, pushed=True, stamp="head",
          install_after_commit=True, built_current=True):
    """Make a fixture repo + fake sdsys.  Returns (repo, sdsys)."""
    repo = os.path.join(tmp, "repo")
    sd64 = os.path.join(repo, "sdb_ai", "sd64")
    os.makedirs(os.path.join(sd64, "gplsrc"), exist_ok=True)
    os.makedirs(os.path.join(sd64, "bin"), exist_ok=True)

    git_init = subprocess.run(["git", "init", "-q", "-b", "main", repo],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True)
    if git_init.returncode != 0:
        raise RuntimeError(git_init.stdout)
    git(repo, "config", "user.email", "t@example.invalid")
    git(repo, "config", "user.name", "test")

    # THE FIXTURE MUST IGNORE bin/ BECAUSE THE REAL REPOSITORY DOES.  Without
    # this the very first row failed: a freshly built bin/sd showed up as an
    # untracked file and check A called a clean tree dirty.  That is a fixture
    # that does not reproduce the real shape, and it would have made the one
    # CURRENT row unreachable - leaving nine rows that a guard which always
    # says STALE would pass.  CLAUDE.md: sd64/bin/ is gitignored, and a clean
    # git status is a working instrument here.
    with open(os.path.join(repo, ".gitignore"), "w", encoding="utf-8") as f:
        f.write("sdb_ai/sd64/bin/\n")

    touch(os.path.join(sd64, "gplsrc", "sd.c"))
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "fixture")
    head = git(repo, "rev-parse", "HEAD")

    # origin/main: same as HEAD unless the row wants HEAD unpushed.
    if pushed:
        git(repo, "update-ref", "refs/remotes/origin/main", head)
    else:
        git(repo, "update-ref", "refs/remotes/origin/main", head)
        touch(os.path.join(sd64, "gplsrc", "later.c"))
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "not pushed")
        head = git(repo, "rev-parse", "HEAD")

    commit_t = int(git(repo, "show", "-s", "--format=%ct", head))

    # bin/sd, and whether it is newer than gplsrc.
    src_t = commit_t
    for dirpath, _, names in os.walk(os.path.join(sd64, "gplsrc")):
        for n in names:
            src_t = max(src_t, os.lstat(os.path.join(dirpath, n)).st_mtime)
    touch(os.path.join(sd64, "bin", "sd"),
          src_t + 60 if built_current else src_t - 60)

    # the fake installed tree
    sdsys = os.path.join(tmp, "sdsys")
    inst_t = commit_t + 120 if install_after_commit else commit_t - 120
    touch(os.path.join(sdsys, "bin", "sd"), inst_t)

    if stamp is not None:
        sha = head if stamp == "head" else stamp
        with open(os.path.join(sdsys, ".sdcore-install"), "w",
                  encoding="utf-8") as f:
            f.write("commit=%s\nbranch=main\ninstalled=%s\n"
                    % (sha, time.strftime("%Y-%m-%d %H:%M:%S")))

    if dirty:
        touch(os.path.join(sd64, "gplsrc", "uncommitted.c"))

    return repo, sdsys


def check(label, expect, reason_fragment=None, **kw):
    """Build a fixture, run the guard, assert the exit AND the reason."""
    global passed, failed
    tmp = tempfile.mkdtemp(prefix="sdac-")
    try:
        repo, sdsys = build(tmp, **kw)
        p = subprocess.run([sys.executable, GUARD, "--repo", repo,
                            "--sdsys", sdsys],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True)
        ok = (p.returncode == expect)
        # THE EXIT CODE ALONE IS NOT THE CHECK.  Three rows below expect STALE
        # and a guard that returned STALE for every input would pass all three.
        # The reason has to match too, or the row is not testing what it says.
        if ok and reason_fragment:
            ok = reason_fragment.lower() in p.stdout.lower()
        if ok:
            passed += 1
            print("  [PASS] %-46s %s" % (label, NAMES[expect]))
        else:
            failed += 1
            print("  [FAIL] %-46s wanted %s%s, got %s"
                  % (label, NAMES[expect],
                     (" + %r" % reason_fragment) if reason_fragment else "",
                     NAMES.get(p.returncode, p.returncode)))
            for line in p.stdout.splitlines():
                print("         | %s" % line)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def check_raw(label, expect, reason_fragment, repo, sdsys):
    global passed, failed
    p = subprocess.run([sys.executable, GUARD, "--repo", repo,
                        "--sdsys", sdsys],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       text=True)
    ok = p.returncode == expect and reason_fragment.lower() in p.stdout.lower()
    if ok:
        passed += 1
        print("  [PASS] %-46s %s" % (label, NAMES[expect]))
    else:
        failed += 1
        print("  [FAIL] %-46s wanted %s, got %s"
              % (label, NAMES[expect], NAMES.get(p.returncode, p.returncode)))
        for line in p.stdout.splitlines():
            print("         | %s" % line)


def main():
    if not os.path.exists(GUARD):
        print("cannot run: %s is missing" % GUARD)
        return 2

    print("test-assert-current: driving %s" % GUARD)

    # ---- the one that must say CURRENT.  Without it every other row could be
    # ---- satisfied by a guard that always says STALE.
    check("clean, pushed, stamp==HEAD, built", CURRENT, "current.")

    # ---- STALE, each for a DIFFERENT stated reason.
    check("uncommitted change", STALE, "uncommitted", dirty=True)
    check("HEAD not pushed to origin/main", STALE, "not origin/main",
          pushed=False)
    check("stamp names another commit", STALE, "was built from",
          stamp="0" * 40)
    check("no stamp, install predates HEAD", STALE, "predates head",
          stamp=None, install_after_commit=False)
    check("bin/sd older than gplsrc", STALE, "run make", built_current=False)

    # ---- UNKNOWN.  The third answer, and the one most likely to get collapsed
    # ---- into one of the other two by a later edit.
    check("no stamp, install newer - cannot tell", UNKNOWN, "not evidence",
          stamp=None, install_after_commit=True)

    tmp = tempfile.mkdtemp(prefix="sdac-")
    try:
        repo, sdsys = build(tmp)
        shutil.rmtree(sdsys)
        check_raw("nothing installed", UNKNOWN, "nothing installed", repo, sdsys)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    tmp = tempfile.mkdtemp(prefix="sdac-")
    try:
        repo, sdsys = build(tmp)
        shutil.rmtree(os.path.join(repo, ".git"))
        check_raw("not a git repository", UNKNOWN, "not a git repository",
                  repo, sdsys)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    tmp = tempfile.mkdtemp(prefix="sdac-")
    try:
        repo, sdsys = build(tmp)
        os.remove(os.path.join(sdsys, "bin", "sd"))
        check_raw("sdsys with no bin/sd", UNKNOWN, "is this an sd system",
                  repo, sdsys)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n%d passed, %d failed (%d rows)"
          % (passed, failed, passed + failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
