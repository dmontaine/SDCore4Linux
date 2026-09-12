#!/usr/bin/env python3
#
# assert-current.py - refuse to trust a measurement taken against an installed
#                     system that the source has moved past.
#
#   python3 gplbld/assert-current.py            check, say what was compared
#   python3 gplbld/assert-current.py --quiet     print only on failure
#   python3 gplbld/assert-current.py --fetch     git fetch first (network)
#   python3 gplbld/assert-current.py --sdsys DIR --repo DIR    point elsewhere
#
# Exit 0 the install is current, 1 it is STALE, 2 the question CANNOT BE
# ANSWERED.  Those are three answers, not two, and collapsing the third into
# either of the others is the defect this file is most likely to grow.
#
# WHY THIS EXISTS AS CODE RATHER THAN A RULE.  CLAUDE.md has required since the
# port's rule of 15 Aug 2026 that a test cycle begin with a fresh install, and
# says of this project: "nothing checks, so the discipline is yours.  Writing
# that guard is worth a session."  A rule says when a cycle BEGINS and says
# nothing about what ENDS one, so "install, start testing, edit source, keep
# reading results" obeys it while producing measurements of a tree that no
# longer exists.  A result from a stale tree is worse than no result: it looks
# like evidence.
#
# ***THE QUESTION HERE IS NOT THE PORT'S QUESTION, AND COPYING ITS ANSWER WOULD
# BE WRONG.***  assert-current.ps1 compares the installed binary with bin\sd.exe
# because there the installer stages what is in bin\.  ***HERE THE INSTALLER
# CLONES main FROM GITHUB AND BUILDS THAT*** (owner, 9 Sep 2026; CLAUDE.md
# "Project constraints"; PRE_RELEASE 15).  So bin/sd in the working tree is NOT
# what got installed even when both are perfectly current, and comparing them
# would report stale on a good tree and current on a bad one.
#
# The Linux question has three parts and they fail for different reasons:
#
#   A. Is the working tree committed?      An uncommitted change cannot be in
#                                          an install, because the installer
#                                          never sees the working tree.
#   B. Is HEAD pushed to origin/main?      Same reason, one step further out.
#   C. Was the install built from HEAD?    Exact when the install left a stamp;
#                                          one-directional without one.
#   D. Is bin/sd newer than gplsrc?        A DIFFERENT question - it is about
#                                          the tree you compile BASIC against,
#                                          not the one you measure.  Kept
#                                          because it is the port's check A2,
#                                          which was paid for: a C edit reached
#                                          a commit having never been compiled.
#
# THE BIAS IS DELIBERATE AND IT IS THE PORT'S.  A false "stale" costs one
# install; a false "current" costs an investigation into a bug that was fixed
# hours ago.  So anything that cannot be shown to be current is not current.
#
# ***OWNER'S RULING, 12 SEP 2026: CHECK C STAYS STRICT COMMIT IDENTITY. DO NOT
# MAKE IT CLEVERER.***  The question had been put: C compares the install's
# stamp with HEAD, so ANY commit makes it STALE - including a
# documentation-only one - and every verifier then needs its --allow-stale
# flag.  The proposal was to have C ask instead whether the delta touches
# anything the install actually CONTAINS.  ***THE RULING WAS FOR THE MOST
# TRUSTED OPTION, WHICH IS THIS ONE***, and the reason is the paragraph above:
# a cleverer C would have to decide, per commit, which files reach an install,
# and every wrong answer in that decision is a FALSE "current" - the expensive
# direction.  A blunt check that is sometimes pessimistic cannot lie in the
# direction that costs.
#
# SO THE FRICTION IS PAID WHERE IT IS VISIBLE INSTEAD.  A caller who has
# reasoned about the delta says so out loud with its own --allow-stale, which
# prints a banner, and states the commit and the reason when quoting the
# result.  ***THE REASONING IS THEN IN THE TRANSCRIPT RATHER THAN INSIDE THIS
# FILE***, where nobody would see it.  The port's $neverShipped list is NOT
# the same mechanism and does not answer this: it is about a FILE existing,
# not about a COMMIT differing.
#
import argparse
import os
import subprocess
import sys
import time

CURRENT, STALE, UNKNOWN = 0, 1, 2

DEFAULT_SDSYS = "/usr/local/sdsys"
STAMP_NAME = ".sdcore-install"


def run(args, cwd=None):
    """Return (rc, stdout) with stderr folded in.  Never raises."""
    try:
        p = subprocess.run(args, cwd=cwd, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, text=True)
        return p.returncode, p.stdout.strip()
    except OSError as e:
        return 127, str(e)


def newest(root, skip=()):
    """(path, mtime) of the newest regular file under root, or (None, 0)."""
    best, best_t = None, 0.0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for name in filenames:
            p = os.path.join(dirpath, name)
            try:
                t = os.lstat(p).st_mtime
            except OSError:
                continue
            if t > best_t:
                best, best_t = p, t
    return best, best_t


def when(t):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t)) if t else "-"


def read_stamp(path):
    """key=value lines -> dict, or None if there is no stamp."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return None
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out or None


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--fetch", action="store_true",
                    help="git fetch origin first; without it, origin/main is "
                         "whatever your last fetch left and may be behind")
    ap.add_argument("--sdsys", default=DEFAULT_SDSYS)
    ap.add_argument("--repo", default=None)
    args = ap.parse_args()

    # --repo implies the tree layout rather than needing a second flag, which
    # is what makes every arm below drivable from a fixture: the unit test
    # builds <repo>/sdb_ai/sd64/{bin,gplsrc} and a fake sdsys, and nothing has
    # to know it is being tested.
    if args.repo:
        repo = os.path.abspath(args.repo)
        sd64 = os.path.join(repo, "sdb_ai", "sd64")
    else:
        here = os.path.dirname(os.path.abspath(__file__))       # .../sd64/gplbld
        sd64 = os.path.dirname(here)                            # .../sd64
        repo = os.path.dirname(os.path.dirname(sd64))           # the git root
    sdsys = args.sdsys

    out = []
    def note(m):
        out.append(m)
    def bad(m):
        out.append("STALE: " + m)

    note("assert-current")
    note("  repo      : %s" % repo)
    note("  sdsys     : %s" % sdsys)
    note("  gplsrc    : %s" % os.path.join(sd64, "gplsrc"))

    def finish(code):
        if code != CURRENT or not args.quiet:
            print("\n".join(out))
        return code

    # ---------------------------------------------------------------- can we?
    # ABSENT AND FORBIDDEN ARE DIFFERENT ANSWERS.  The port's entry 182 was
    # exactly this: a good install reported as "nothing installed" because the
    # existence test failed for a permissions reason.  The two want opposite
    # cures, so they are told apart here rather than merged into "no".
    if not os.path.exists(sdsys):
        note("CANNOT ANSWER: nothing installed at %s" % sdsys)
        return finish(UNKNOWN)
    if not os.access(sdsys, os.R_OK | os.X_OK):
        note("CANNOT ANSWER: %s exists but this user cannot read it." % sdsys)
        note("  That is NOT a stale tree and NOT a missing one.  Check group")
        note("  membership, or re-run after signing in again.")
        return finish(UNKNOWN)

    rc, head = run(["git", "-C", repo, "rev-parse", "HEAD"])
    if rc != 0:
        note("CANNOT ANSWER: %s is not a git repository (%s)" % (repo, head))
        return finish(UNKNOWN)

    if args.fetch:
        frc, fout = run(["git", "-C", repo, "fetch", "origin", "--quiet"])
        note("  fetch     : %s" % ("ok" if frc == 0 else "FAILED - " + fout))

    stale = False

    # ------------------------------------------------------- A. working tree
    rc, dirty = run(["git", "-C", repo, "status", "--porcelain"])
    if rc != 0:
        note("CANNOT ANSWER: git status failed (%s)" % dirty)
        return finish(UNKNOWN)
    if dirty:
        n = len(dirty.splitlines())
        bad("the working tree has %d uncommitted change(s); an install can "
            "never contain them, because the installer clones origin/main "
            "and never sees this tree." % n)
        for line in dirty.splitlines()[:10]:
            note("         %s" % line)
        stale = True
    else:
        note("  A working tree clean")

    # ------------------------------------------------------------ B. pushed?
    rc, origin_main = run(["git", "-C", repo, "rev-parse", "origin/main"])
    if rc != 0:
        note("CANNOT ANSWER: no origin/main ref (%s).  Fetch once." % origin_main)
        return finish(UNKNOWN)
    if head != origin_main:
        rc, ahead = run(["git", "-C", repo, "rev-list", "--count",
                         "origin/main..HEAD"])
        rc2, behind = run(["git", "-C", repo, "rev-list", "--count",
                           "HEAD..origin/main"])
        bad("HEAD %s is not origin/main %s (ahead %s, behind %s). An install "
            "builds origin/main, so anything only in HEAD cannot be in it."
            % (head[:12], origin_main[:12], ahead, behind))
        if not args.fetch:
            note("         origin/main here is your last fetch; --fetch to refresh.")
        stale = True
    else:
        note("  B HEAD == origin/main  %s" % head[:12])

    # ------------------------------------------- C. what did the install run?
    stamp_path = os.path.join(sdsys, STAMP_NAME)
    stamp = read_stamp(stamp_path)
    installed_bin = os.path.join(sdsys, "bin", "sd")
    try:
        inst_t = os.lstat(installed_bin).st_mtime
    except OSError:
        note("CANNOT ANSWER: no %s - is this an SD system directory?"
             % installed_bin)
        return finish(UNKNOWN)

    if stamp and stamp.get("commit"):
        got = stamp["commit"]
        if got == head:
            note("  C install built from HEAD  %s  (%s)"
                 % (got[:12], stamp.get("installed", "time unrecorded")))
        else:
            bad("the install was built from %s, HEAD is %s."
                % (got[:12], head[:12]))
            stale = True
    else:
        # NO STAMP.  This is one-directional and says so.  Older than the
        # commit is decisive; newer is NOT evidence of anything, because the
        # install could have been built from any commit or any branch.
        rc, ct = run(["git", "-C", repo, "show", "-s", "--format=%ct", head])
        if rc != 0 or not ct.isdigit():
            note("CANNOT ANSWER: could not read HEAD's commit time (%s)" % ct)
            return finish(UNKNOWN)
        commit_t = int(ct)
        note("  C no %s stamp in the installed tree." % STAMP_NAME)
        note("      install %s   HEAD committed %s"
             % (when(inst_t), when(commit_t)))
        if inst_t < commit_t:
            bad("the install predates HEAD, so it cannot contain it.")
            stale = True
        else:
            note("CANNOT ANSWER: the install is newer than HEAD's commit, but "
                 "without a stamp there is nothing that says WHICH commit it "
                 "was built from - a newer mtime is not evidence.")
            note("  Re-install once; installsdai.sh writes the stamp now.")
            return finish(UNKNOWN)

    # --------------------------------------------- D. is bin/sd even rebuilt?
    # The port's check A2, and it is about a different tree: bin/sd is what you
    # compile BASIC against and what "make" produces, not what is installed.
    # A C edit that was never compiled reached a commit in the port this way.
    built = os.path.join(sd64, "bin", "sd")
    src, src_t = newest(os.path.join(sd64, "gplsrc"))
    if src is None:
        note("CANNOT ANSWER: no source files under gplsrc")
        return finish(UNKNOWN)
    try:
        built_t = os.lstat(built).st_mtime
    except OSError:
        bad("no bin/sd - run make.  (This is the tree you compile against, "
            "not the installed one.)")
        stale = True
    else:
        if built_t < src_t:
            bad("bin/sd (%s) is older than %s (%s) - run make."
                % (when(built_t), os.path.relpath(src, sd64), when(src_t)))
            stale = True
        else:
            note("  D bin/sd %s newer than newest gplsrc file %s"
                 % (when(built_t), when(src_t)))

    if stale:
        note("assert-current: STALE - do not trust a measurement from this tree.")
        return finish(STALE)
    note("assert-current: current.")
    return finish(CURRENT)


if __name__ == "__main__":
    sys.exit(main())
