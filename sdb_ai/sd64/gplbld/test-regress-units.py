#!/usr/bin/env python3
#
# test-regress-units.py - regress.sh's verdicts, on STUB suites.  No install, no sudo, no sd, a second or two.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-regress-units.py            the cases
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-regress-units.py --selftest the cases against 20 broken copies
#
# Exit 0 all passed, 1 a case failed.
#
# START-HISTORY:
# 12 Oct 26 dm  New with regress.sh.
# 14 Oct 26 dm  --jobs: the keyset each worker is given, the refusal of a bad count, every pair of keys checked, a suite
#               taken by one worker only, the cap at the number of suites, a worker that vanishes (a stub that kills
#               it) counted as not run; five more broken copies.
# 14 Oct 26 dm  --snapshot: the suite runs in a copy that holds a file git has not seen, the ignored header and the
#               documents at the top; the copy is removed; outside a work tree and a failed build are refused (a stub
#               git repository in a scratch directory); five more broken copies.
# 14 Oct 26 dm  pieces: with more than one worker the screen suite is cut into five, each given the --only= of its parts;
#               the pieces are checked against the parts sandbox-screen.py runs by default (11), so a part added to the
#               suite and not to a piece fails here; three more broken copies.
# END-HISTORY
#
# WHY.  regress.sh is the instrument that says the tree is fine.  An instrument that reports a pass for a suite that
# printed nothing, or for one that passed no row, or that exited non-zero, is worse than none (CLAUDE.md: it must refuse
# the null case out loud).  So it is run here on a tree of stub suites whose behaviour is known, and the verdict, the
# exit status and the lines it prints are read.  The stubs are:
#   okay    prints "sandbox-okay: 3 passed, 0 failed", exits 0                      -> PASS
#   bad     prints a [FAIL] row and "2 passed, 1 failed", exits 1                    -> FAIL
#   badzero prints "2 passed, 1 failed" but exits 0                                  -> FAIL (the count is the count)
#   liar    prints "5 passed, 0 failed" but exits 1                                  -> FAIL (the exit status is the status)
#   silent  prints nothing, exits 0                                                  -> FAIL (no verdict line)
#   zero    prints "0 passed, 0 failed", exits 0                                     -> FAIL (a run that passed nothing)
#   cannot  prints "CANNOT RUN - ..." and exits 2                                    -> NOT RUN, exit 2
#   echo    writes the arguments it was given, and whether its directory existed, to a file, then passes
#   napa-f  each notes the SDBOX_KEYSET it was given and that it ran, sleeps 1.5 s, then passes
#   murder  kills the worker that is running it (its grandparent), without a verdict                -> NOT RUN, exit 2
#   where   says which tree it runs in and what that tree holds (for --snapshot, in a stub git repository)
# The shared memory keys are read with ipcs; the cases put a fake ipcs first on PATH, so the result does not depend
# on whether a real sandbox is running while this check does.
#
# --selftest breaks a copy of regress.sh twenty ways, each by one replacement that must match exactly once, and runs
# the cases against it: every broken copy must FAIL a case, or the cases do not test what they claim.

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "regress.sh")
passed = failed = 0
quiet = False       # during a mutant's pass its own rows are counted, not shown: only whether it was caught is a result


def row(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        if not quiet:
            print("  [PASS] " + name)
    else:
        failed += 1
        if not quiet:
            print("  [FAIL] " + name + ("   <- " + detail if detail else ""))


STUBS = {
    "okay": 'print("sandbox-okay: 3 passed, 0 failed")',
    "bad": 'print("  [FAIL] a row that failed"); print("sandbox-bad: 2 passed, 1 failed"); sys.exit(1)',
    "badzero": 'print("sandbox-badzero: 2 passed, 1 failed")',
    "liar": 'print("sandbox-liar: 5 passed, 0 failed"); sys.exit(1)',
    "silent": "pass",
    "zero": 'print("sandbox-zero: 0 passed, 0 failed")',
    "cannot": 'print("sandbox-cannot: CANNOT RUN - no sandbox"); sys.exit(2)',
    "echo": ('open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "echo.args"), "w").write('
             '" ".join(sys.argv[1:]) + " | existed=" + str(os.path.exists(sys.argv[1])))\n'
             'print("sandbox-echo: 1 passed, 0 failed")'),
    "murder": ('import signal\n'
               'grandparent = int(open("/proc/%d/stat" % os.getppid()).read().rsplit(")", 1)[1].split()[1])\n'
               'os.kill(grandparent, signal.SIGKILL)\n'
               'print("sandbox-murder: 1 passed, 0 failed")'),
    "screen": ('open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "screen.args"), "a").write('
               '" ".join(sys.argv[2:]) + "\\n")\n'
               'print("sandbox-screen: 1 passed, 0 failed")'),
    "where": ('here = os.path.dirname(os.path.abspath(__file__))\n'
              'tree = os.path.dirname(here)\n'
              'top = os.path.dirname(os.path.dirname(tree))\n'
              'print("WHERE " + tree + " untracked=" + str(os.path.exists(os.path.join(here, "untracked.txt")))'
              ' + " header=" + str(os.path.exists(os.path.join(tree, "gplsrc", "sdext_python_inc.h")))'
              ' + " installer=" + str(os.path.exists(os.path.join(top, "installsdcore.sh")))'
              ' + " status=" + str(os.path.exists(os.path.join(top, "PROJECT_STATUS.md"))))\n'
              'print("sandbox-where: 1 passed, 0 failed")'),
}
NAP = ('import time\n'
       'me = os.path.basename(sys.argv[0])[len("sandbox-"):-3]\n'
       'root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")\n'
       'open(os.path.join(root, "ks." + me), "w").write(os.environ.get("SDBOX_KEYSET", "unset"))\n'
       'open(os.path.join(root, "runs.log"), "a").write(me + "\\n")\n'
       'time.sleep(1.5)\n'
       'print("sandbox-%s: 1 passed, 0 failed" % me)')
NAPS = ["nap" + c for c in "abcdef"]
for _n in NAPS:
    STUBS[_n] = NAP


def make_tree(root, script_text):
    """A tree of stub suites with a copy of regress.sh (the real one, or a broken one) and a fake ipcs."""
    gb = os.path.join(root, "gplbld")
    os.makedirs(gb)
    for name, body in STUBS.items():
        with open(os.path.join(gb, "sandbox-%s.py" % name), "w") as f:
            f.write("import os, sys\n%s\n" % body)
    with open(os.path.join(gb, "regress.sh"), "w") as f:
        f.write(script_text)
    os.chmod(os.path.join(gb, "regress.sh"), 0o755)
    for kind, out in (("none", ""), ("held", "0x53434c91 1 don 666 102272 1\n"), ("held1", "0x53434cb1 1 don 666 102272 1\n")):
        bindir = os.path.join(root, "bin-" + kind)
        os.makedirs(bindir)
        with open(os.path.join(bindir, "ipcs"), "w") as f:
            f.write("#!/bin/sh\nprintf '%s' '" + out + "'\n")
        os.chmod(os.path.join(bindir, "ipcs"), 0o755)
    return gb


def make_repo(repo, script_text):
    """A git work tree <repo>/sdb_ai/sd64 of stub suites, for --snapshot: a Makefile that does nothing, the one header
    git ignores, two of the four documents at the top, and a file git has not been told about.  Returns the sd64 path."""
    sd64 = os.path.join(repo, "sdb_ai", "sd64")
    make_tree(sd64, script_text)
    os.makedirs(os.path.join(sd64, "gplsrc"))
    with open(os.path.join(sd64, "Makefile"), "w") as f:
        f.write("all:\n\ttrue\n")
    with open(os.path.join(sd64, "gplsrc", "sdext_python_inc.h"), "w") as f:
        f.write("/* ignored by git, needed by the build */\n")
    with open(os.path.join(repo, ".gitignore"), "w") as f:
        f.write("sdb_ai/sd64/gplsrc/sdext_python_inc.h\n")
    for name in ("installsdcore.sh", "PROJECT_STATUS.md"):
        with open(os.path.join(repo, name), "w") as f:
            f.write("x\n")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    with open(os.path.join(sd64, "gplbld", "untracked.txt"), "w") as f:
        f.write("new\n")
    return sd64


def run(root, args, held=False, tree=None):
    """held: False (no keys held), True (keyset 0's pair is) or "held1" (keyset 1's pair is).  tree: the sd64 directory
    when it is not root itself (a repository, for --snapshot); scratch files then go into root."""
    kind = "held1" if held == "held1" else ("held" if held else "none")
    top = tree or root
    env = dict(os.environ, PATH=os.path.join(top, "bin-" + kind) + ":" + os.environ["PATH"], TMPDIR=root)
    p = subprocess.run(["bash", os.path.join(top, "gplbld", "regress.sh"), "--tree", top] + args, capture_output=True, text=True, env=env, timeout=120)
    return p.returncode, p.stdout + p.stderr


def cases(label, script_text):
    """Run every case on a tree using script_text.  Returns the number of cases that failed."""
    before = failed
    root = tempfile.mkdtemp(prefix="regress-units.")
    repo = tempfile.mkdtemp(prefix="regress-units-repo.")
    try:
        make_tree(root, script_text)

        def verdict(out, suite):
            m = re.search(r"(?m)^\[\s*\d+/\d+\] %s\s+(PASS|FAIL|NOT RUN)\b" % re.escape(suite), out)
            return m.group(1) if m else None

        rc, out = run(root, ["--only", "okay"])
        row(label + "a suite that passes is PASS and the run exits 0", rc == 0 and verdict(out, "okay") == "PASS", "rc %d  %s" % (rc, out[-200:]))
        rc, out = run(root, ["--only", "okay,bad"])
        row(label + "a suite with a failed row is FAIL, its [FAIL] row is shown, the run exits 1",
            rc == 1 and verdict(out, "bad") == "FAIL" and "a row that failed" in out and verdict(out, "okay") == "PASS", "rc %d  %s" % (rc, out[-300:]))
        rc, out = run(root, ["--only", "badzero"])
        row(label + "a suite that exits 0 but says 1 failed is FAIL", rc == 1 and verdict(out, "badzero") == "FAIL", "rc %d  %s" % (rc, out[-200:]))
        rc, out = run(root, ["--only", "liar"])
        row(label + "a suite that says 0 failed but exits 1 is FAIL", rc == 1 and verdict(out, "liar") == "FAIL", "rc %d  %s" % (rc, out[-200:]))
        rc, out = run(root, ["--only", "silent"])
        row(label + "a suite that printed no verdict line is FAIL, and the line says so",
            rc == 1 and verdict(out, "silent") == "FAIL" and "no verdict line" in out, "rc %d  %s" % (rc, out[-200:]))
        rc, out = run(root, ["--only", "zero"])
        row(label + "a suite that passed no row is FAIL (the null case)", rc == 1 and verdict(out, "zero") == "FAIL", "rc %d  %s" % (rc, out[-200:]))
        rc, out = run(root, ["--only", "cannot"])
        row(label + "a suite that said CANNOT RUN is NOT RUN and the run exits 2", rc == 2 and verdict(out, "cannot") == "NOT RUN", "rc %d  %s" % (rc, out[-200:]))
        rc, out = run(root, ["--only", "cannot,bad"])
        row(label + "a failure outranks a suite that could not run: exit 1", rc == 1, "rc %d  %s" % (rc, out[-200:]))
        rc, out = run(root, ["--only", "nosuchsuite"])
        row(label + "an unknown suite is refused (exit 2), not skipped", rc == 2 and "no suite 'nosuchsuite'" in out, "rc %d  %s" % (rc, out[-200:]))
        rc, out = run(root, ["--only", "okay,bad", "--skip", "bad"])
        row(label + "--skip leaves a suite out: only the one left runs, and passes", rc == 0 and verdict(out, "bad") is None and verdict(out, "okay") == "PASS", "rc %d  %s" % (rc, out[-200:]))
        rc, out = run(root, ["--only", "okay"], held=True)
        row(label + "a sandbox already holding the shared memory keys is refused (exit 2) before any suite runs",
            rc == 2 and "already holds the shared memory keys" in out and verdict(out, "okay") is None, "rc %d  %s" % (rc, out[-200:]))
        rc, out = run(root, ["--only", "echo"])
        try:
            with open(os.path.join(root, "echo.args")) as f:
                seen = f.read()
        except OSError:
            seen = ""
        m = re.match(r"^(\S+) --build \| existed=False$", seen)
        row(label + "each suite is given a fresh directory that does not exist yet, and --build",
            rc == 0 and bool(m) and "sbx-echo" in seen, "rc %d  args %r" % (rc, seen))
        row(label + "...and that directory is gone afterwards", bool(m) and not os.path.exists(m.group(1)), repr(seen))
        rc, out = run(root, ["--list", "--only", "okay,bad", "--skip", "bad"])
        row(label + "--list prints the suites that would run and runs none", rc == 0 and out.split() == ["okay"], "rc %d  %r" % (rc, out))

        # --jobs
        for bad in ("0", "9", "x"):
            rc, out = run(root, ["--only", "okay", "--jobs", bad])
            row(label + "--jobs %s is refused (exit 2) before any suite runs" % bad,
                rc == 2 and "--jobs must be 1 to 8" in out and verdict(out, "okay") is None, "rc %d  %s" % (rc, out[-200:]))
        rc, out = run(root, ["--only", "okay,bad", "--jobs", "2"], held="held1")
        row(label + "--jobs 2 refuses a sandbox holding the SECOND pair of keys, and names the keyset",
            rc == 2 and "keyset 1" in out and verdict(out, "okay") is None, "rc %d  %s" % (rc, out[-200:]))
        rc, out = run(root, ["--only", "okay", "--jobs", "1"], held="held1")
        row(label + "--jobs 1 does not mind a sandbox on the second pair: that keyset is not used",
            rc == 0 and verdict(out, "okay") == "PASS", "rc %d  %s" % (rc, out[-200:]))

        def clean():
            for n in NAPS:
                for p in (os.path.join(root, "ks." + n), os.path.join(root, "runs.log")):
                    if os.path.exists(p):
                        os.remove(p)

        def seen_keysets(names):
            got = set()
            for n in names:
                try:
                    with open(os.path.join(root, "ks." + n)) as f:
                        got.add(f.read())
                except OSError:
                    got.add("(did not run)")
            return got

        def runs():
            try:
                with open(os.path.join(root, "runs.log")) as f:
                    return sorted(f.read().split())
            except OSError:
                return []

        clean()
        t0 = time.time()
        rc, out = run(root, ["--only", ",".join(NAPS), "--jobs", "3"])
        dt = time.time() - t0
        row(label + "--jobs 3: six suites, three workers on keysets 0, 1 and 2, all PASS, the run exits 0",
            rc == 0 and seen_keysets(NAPS) == {"0", "1", "2"} and all(verdict(out, n) == "PASS" for n in NAPS),
            "rc %d  keysets %s  %s" % (rc, sorted(seen_keysets(NAPS)), out[-300:]))
        row(label + "...each suite is run exactly once (the claim is taken by one worker only)", runs() == sorted(NAPS), repr(runs()))
        row(label + "...and they ran side by side: six 1.5 s suites took under 7 s, not 9", dt < 7, "%.1f s" % dt)
        clean()
        rc, out = run(root, ["--only", ",".join(NAPS[:3]), "--jobs", "1"])
        row(label + "--jobs 1: every suite is given keyset 0, and each runs once",
            rc == 0 and seen_keysets(NAPS[:3]) == {"0"} and runs() == sorted(NAPS[:3]), "rc %d  keysets %s  runs %r" % (rc, sorted(seen_keysets(NAPS[:3])), runs()))
        clean()
        rc, out = run(root, ["--only", ",".join(NAPS[:2]), "--jobs", "8"])
        row(label + "--jobs 8 with two suites starts two workers, not eight",
            rc == 0 and seen_keysets(NAPS[:2]) == {"0", "1"}, "rc %d  keysets %s" % (rc, sorted(seen_keysets(NAPS[:2]))))
        clean()
        rc, out = run(root, ["--only", "murder,okay", "--jobs", "1"])
        row(label + "a worker that dies leaves its suites NOT RUN with no verdict, never a pass; the run exits 2",
            rc == 2 and verdict(out, "murder") == "NOT RUN" and verdict(out, "okay") == "NOT RUN" and "no verdict was written" in out,
            "rc %d  %s" % (rc, out[-300:]))

        # pieces: the long screen suite is cut when there is more than one worker
        want = {"dialogs", "mouse,resize", "forms,tabs", "memo,scroll,owned", "table,themes,events"}
        rc, out = run(root, ["--list", "--only", "screen", "--jobs", "2"])
        row(label + "--list with two workers shows the screen suite as its pieces",
            rc == 0 and len(out.split()) == 5 and all(w.startswith("screen~") for w in out.split()), "rc %d  %r" % (rc, out))
        rc, out = run(root, ["--list", "--only", "screen"])
        row(label + "--list with one worker shows the screen suite whole", rc == 0 and out.split() == ["screen"], "rc %d  %r" % (rc, out))
        screen_args = os.path.join(root, "screen.args")

        def screen_runs():
            """The argument lines the screen stub wrote since it was last cleared, and clear them."""
            try:
                with open(screen_args) as f:
                    lines = f.read().split("\n")[:-1]
                os.remove(screen_args)
                return lines
            except OSError:
                return []

        screen_runs()
        rc, out = run(root, ["--only", "screen", "--jobs", "5"])
        got = screen_runs()
        row(label + "--jobs 5: five pieces run, each given --build and the --only= of its own parts, all PASS",
            rc == 0 and sorted(got) == sorted("--build --only=" + w for w in want) and len(re.findall(r"(?m)^\[\s*\d+/5\] screen~\S+\s+PASS", out)) == 5,
            "rc %d  args %r  %s" % (rc, got, out[-300:]))
        rc, out = run(root, ["--only", "screen", "--jobs", "1"])
        got = screen_runs()
        row(label + "--jobs 1: the screen suite runs whole, with --build and no --only=", rc == 0 and got == ["--build"], "rc %d  args %r" % (rc, got))
        pieces = re.search(r'(?m)^PIECES\[screen\]="([^"]*)"', script_text)
        with open(os.path.join(HERE, "sandbox-screen.py")) as f:
            default = re.search(r'else \[("owned"[^\]]*)\]', f.read())
        listed = sorted(re.sub(r"[+]", ",", pieces.group(1)).replace(" ", ",").split(",")) if pieces else []
        default_parts = sorted(re.findall(r'"([a-z0-9]+)"', default.group(1))) if default else []
        row(label + "the pieces hold every part sandbox-screen.py runs by default, each once, and nothing else",
            bool(pieces) and bool(default) and listed == default_parts and len(default_parts) == 11, "pieces %r  default %r" % (listed, default_parts))

        # --snapshot
        rc, out = run(root, ["--snapshot", "--only", "okay"])
        row(label + "--snapshot outside a git work tree is refused (exit 2) before any suite runs",
            rc == 2 and "inside a git work tree" in out and verdict(out, "okay") is None, "rc %d  %s" % (rc, out[-200:]))
        sd64 = make_repo(repo, script_text)
        logs = os.path.join(repo, "snaplogs")

        def leftovers():
            return [d for d in os.listdir(repo) if d.startswith("sdregress.")]

        rc, out = run(repo, ["--snapshot", "--only", "where", "--logs", logs], tree=sd64)
        try:
            with open(os.path.join(logs, "where.out")) as f:
                where = f.read()
        except OSError:
            where = ""
        m = re.search(r"WHERE (\S+) untracked=(\w+) header=(\w+) installer=(\w+) status=(\w+)", where)
        row(label + "--snapshot: the suite runs in a COPY of the tree, not in the live one, and passes",
            rc == 0 and verdict(out, "where") == "PASS" and bool(m) and m.group(1) != sd64 and "/snap/sdb_ai/sd64" in m.group(1),
            "rc %d  %r  %s" % (rc, where, out[-200:]))
        row(label + "...the copy holds a file git has not been told about, the ignored header, and the documents at the top",
            bool(m) and m.groups()[1:] == ("True", "True", "True", "True"), repr(where))
        row(label + "...and the copy is gone when the run ends", leftovers() == [] and "snapshot " in out, "%r  %s" % (leftovers(), out[-200:]))
        makefile = os.path.join(sd64, "Makefile")
        with open(makefile, "w") as f:
            f.write("all:\n\tfalse\n")
        rc, out = run(repo, ["--snapshot", "--only", "where", "--logs", logs], tree=sd64)
        row(label + "--snapshot whose build fails is refused (exit 2), runs no suite, and removes the copy",
            rc == 2 and "make failed in the snapshot" in out and verdict(out, "where") is None and not [d for d in os.listdir(repo) if d.startswith("sdregress.") and os.path.exists(os.path.join(repo, d, "snap"))],
            "rc %d  %s" % (rc, out[-200:]))
    finally:
        shutil.rmtree(repo, ignore_errors=True)
        shutil.rmtree(root, ignore_errors=True)
    return failed - before


# The seven breakages: (name, the text to find - exactly once - and what to put in its place)
MUTANTS = [
    ("the exit status is ignored", 'elif [ "$rc" -ne 0 ]; then', "elif false; then"),
    ("a failed count is ignored", 'elif [ "$failed" -ne 0 ]; then', "elif false; then"),
    ("a missing verdict line is not a failure", 'elif [ -z "$verdict" ]; then', "elif false; then"),
    ("a suite that passed no row is not a failure", 'elif [ "$passed" -eq 0 ]; then', "elif false; then"),
    ("CANNOT RUN is not recognised", 'if [ "$rc" -eq 2 ] || grep -q \'CANNOT RUN\' "$log"; then', "if false; then"),
    ("the held-keys refusal is gone", 'if [ -n "$held" ]; then', "if false; then"),
    ("a failed suite does not make the run exit 1", 'if [ "$failed_suites" -gt 0 ] || [ "$free_failed" -gt 0 ]; then exit 1; fi', "if false; then exit 1; fi"),
    ("every worker is given keyset 0", "export SDBOX_KEYSET=$ks", "export SDBOX_KEYSET=0"),
    ("only the first pair of keys is checked", 'while [ $k -lt "$JOBS" ]; do\n    shm=', 'while [ $k -lt 1 ]; do\n    shm='),
    ("a suite can be claimed twice", 'mkdir "$CLAIMS/$s" 2>/dev/null || continue', 'mkdir -p "$CLAIMS/$s" 2>/dev/null || continue'),
    ("a worker that vanished counts as a pass", 'status="NOT RUN"; passed=0; secs=0; why="no verdict was written (the worker ended)"', 'status="PASS"; passed=1; secs=0; why=""'),
    ("--jobs is not checked", "  [1-8]) ;;\n", "  *) ;;\n"),
    ("a file git has not been told about is left out of the snapshot",
     '--cached --others --exclude-standard sdb_ai | rsync -a --from0 --files-from=- ./ "$SNAP"/)',
     '--cached --exclude-standard sdb_ai | rsync -a --from0 --files-from=- ./ "$SNAP"/)'),
    ("the snapshot is not removed", '[ -n "$SNAP" ] && rm -rf "$SNAP"\nrmdir "$RUN/logs"', 'rmdir "$RUN/logs"'),
    ("a snapshot that did not build is used", 'if ! (cd "$SNAP/sdb_ai/sd64" && make > "$LOGS/snapshot-make.log" 2>&1); then', "if false; then"),
    ("the suites run in the live tree, not the snapshot", '  TREE="$SNAP/sdb_ai/sd64"\n', "  : live\n"),
    ("the documents at the top are not copied", "for f in installsdcore.sh PROJECT_STATUS.md PRE_RELEASE_FIXES.md PORT_ADOPTION.md; do", "for f in ; do"),
    ("a part of the screen suite is in no piece", "memo+scroll+owned", "memo+scroll"),
    ("a piece is not given its parts", 'only="--only=$(echo "${s#*~}" | tr \'+\' \',\')"', 'only=""'),
    ("the screen suite is cut even for one worker", 'if [ "$JOBS" -gt 1 ]; then\n  EXPANDED=""', 'if true; then\n  EXPANDED=""'),
]


def main():
    with open(SCRIPT) as f:
        real = f.read()
    print("test-regress-units: %s" % SCRIPT)
    cases("", real)
    if "--selftest" in sys.argv:
        print("\n--selftest: %d broken copies of regress.sh, each of which must fail a case" % len(MUTANTS))
        global passed, failed, quiet
        for name, find, put in MUTANTS:
            if real.count(find) != 1:
                row("mutant '%s': the text to break occurs once in regress.sh" % name, False, "found %d times" % real.count(find))
                continue
            keep = (passed, failed)
            quiet = True
            broken = cases("", real.replace(find, put))
            quiet = False
            caught = broken > 0
            passed, failed = keep
            row("mutant '%s' is caught by a case" % name, caught, "every case passed on the broken copy")
    print("\ntest-regress-units: %d passed, %d failed" % (passed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
