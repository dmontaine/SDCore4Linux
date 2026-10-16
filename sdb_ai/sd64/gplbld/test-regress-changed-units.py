#!/usr/bin/env python3
#
# test-regress-changed-units.py - the selector behind  regress.sh --changed  (gplbld/regress-changed.py, gplbld/regress-map.txt).
#                                 Free: no install, no sudo, no sandbox; it makes a scratch git repository under /tmp.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-regress-changed-units.py
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-regress-changed-units.py --selftest     (7 mutants of the selector)
#
# START-HISTORY:
# 15 Oct 26 dm  New, with --changed (owner, 14 and 15 Oct 2026: regressions must be targeted).
# END-HISTORY
#
# WHAT IT CHECKS.  (A) The REAL map against the REAL regress.sh: the map parses, every suite it names is in ALL_SUITES, and every
# suite in ALL_SUITES is named by some rule other than its own file (a suite no change could ever select is a suite that has
# stopped being run); a few selections that matter are held (a new suite selects itself, the select-list kernel file selects the
# select-list suites, a changed dictionary item selects LISTF, a changelog selects nothing, an unknown file is refused).  (B) The
# SELECTOR in a scratch repository with a small map: nothing changed is refused, an unmapped file is refused and named, a sandbox
# file that is not in ALL_SUITES is refused, hunk labels choose a file's sub-rules (a label with no rule takes '*', comments only
# add nothing, unknown hunks take every sub-rule), --since reaches back, --files is conservative.  (C) regress.sh --changed --list
# in that repository, and --changed with --only refused.  With --selftest each mutant of the selector must turn a row red.

import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "regress-changed.py")
REGRESS = os.path.join(HERE, "regress.sh")
MAP = os.path.join(HERE, "regress-map.txt")
passed = failed = 0


def row(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print("  [PASS] " + name)
    else:
        failed += 1
        print("  [FAIL] " + name + ("   <- " + detail if detail else ""))


def run(cmd, cwd, **kw):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, errors="replace", **kw)


def git(repo, *args):
    p = run(["git", "-c", "user.name=t", "-c", "user.email=t@t"] + list(args), repo)
    if p.returncode != 0:
        raise SystemExit("git %s failed: %s" % (" ".join(args), p.stderr))
    return p.stdout


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


# ---------------------------------------------------------------------------------------------------------------------------
# (A) the real map

def load_tool(path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("regress_changed_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def part_a():
    print("\n--- (A) the real map against the real regress.sh -------------------------------------")
    rc = load_tool(TOOL)
    suites = rc.all_suites(REGRESS)
    try:
        groups, rules, subrules = rc.parse_map(MAP)
        row("the map parses (%d rules, %d groups, %d files with sub-rules)" % (len(rules), len(groups), len(subrules)), True)
    except SystemExit:
        row("the map parses", False, "parse_map exited")
        return
    named, bad = set(), []
    allrules = [(n, p, w) for n, p, w in rules] + [(n, g, w) for subs in subrules.values() for n, g, w in subs]
    for n, p, w in allrules:
        words = [x for x in w if x != "@self"]
        try:
            named.update(rc.expand(words, groups, suites, "line %d" % n))
        except SystemExit:
            bad.append("line %d" % n)
    for gname, w in groups.items():
        try:
            named.update(rc.expand(w, groups, suites, gname))
        except SystemExit:
            bad.append(gname)
    row("every suite and group the map names exists (none stale)", not bad, "stale: %s" % ", ".join(bad))
    orphans = [s for s in suites if s not in named]
    row("every suite in ALL_SUITES is named by a rule other than its own file (%d suites)" % len(suites), not orphans,
        "no rule names: %s" % " ".join(orphans))
    self_rules = [n for n, p, w in rules if p == "gplbld/sandbox-*.py" and w == ["@self"]]
    row("the rule that makes a sandbox-*.py its own suite is there", len(self_rules) == 1, "found %d" % len(self_rules))

    def pick(files, labels=None):
        lab = (lambda p: labels) if labels is not None else None
        return rc.select(files, groups, rules, suites, subrules, lab)

    p = "sdb_ai/sd64/"
    sel, un, _ = pick([p + "gplbld/sandbox-selectv-mode.py"])
    row("a changed suite file selects that suite and only it", sel == ["selectv-mode"] and not un, repr(sel))
    sel, un, _ = pick([p + "gplsrc/op_dio4.c"])
    row("the select-list kernel file selects the select-list suites", {"sselectv", "pickrn", "list-q2", "selectv-mode"} <= set(sel), repr(sel))
    sel, un, _ = pick([p + "sdsys/gpl.bp/ftype"])
    row("LISTF's type program selects the LISTF suite", "listf-mult" in sel, repr(sel))
    sel, un, _ = pick([p + "gplbld/FILES_DICTS/voc.dic^trigger"])
    row("a shipped VOC dictionary item selects the LISTF and dictionary suites", {"listf-mult", "dictfold"} <= set(sel), repr(sel))
    sel, un, _ = pick([p + "sdsys/changelog", p + "gplbld/regress.sh", "PROJECT_STATUS.md"])
    row("the changelog, regress.sh and a document at the root select no sandbox suite", sel == [] and not un, "%r %r" % (sel, un))
    sel, un, _ = pick([p + "zzz/unknown.bin"])
    row("a file no rule matches is unmapped, not skipped", un == [p + "zzz/unknown.bin"] and sel == [], "%r %r" % (sel, un))
    sel, un, _ = pick([p + "gplbld/sandbox-notasuite.py"])
    row("a sandbox-*.py that is not in ALL_SUITES is refused (register it)", un == [p + "gplbld/sandbox-notasuite.py"], "%r %r" % (sel, un))
    bc = p + "sdsys/gpl.bp/bcomp"
    sel, _, _ = pick([bc], ["st.input.common"])
    row("bcomp, a hunk under st.input.common: the INPUT suites, not the select-list ones", "inputtrap" in sel and "selectv-mode" not in sel, repr(sel))
    sel, _, _ = pick([bc], ["st.select.common", "st.readnext"])
    row("bcomp, hunks under st.select.common and st.readnext: the select-list suites, not the INPUT ones",
        "selectv-mode" in sel and "inputtrap" not in sel and "classas" not in sel, repr(sel))
    sel, _, _ = pick([bc], [])
    row("bcomp, hunks in comments only: the small compiler check and nothing more", sorted(sel) == sorted(["bcomp-a1", "stmt-q3", "func-q1", "mode-q16"]), repr(sel))
    sel, _, _ = pick([bc], ["some.label.nobody.named"])
    row("bcomp, a hunk under a label no sub-rule names: the whole compiler group", {"classas", "inputtrap", "lang-a15", "try"} <= set(sel), repr(sel))
    sel, _, _ = pick([bc], None)
    row("bcomp, hunks unknown: every sub-rule applies", {"inputtrap", "screen", "try", "selectv-mode"} <= set(sel), repr(sel))


# ---------------------------------------------------------------------------------------------------------------------------
# (B) and (C): a scratch repository

SCRATCH_MAP = """\
@pair = alpha beta
gplbld/sandbox-*.py : @self
gplbld/regress.sh : none
gplbld/regress-map.txt : none
gplbld/regress-changed.py : none
sdsys/gpl.bp/prog : alpha
sdsys/gpl.bp/prog ~ st.one* : beta
sdsys/gpl.bp/prog ~ st.two  : gamma
sdsys/gpl.bp/prog ~ *       : @pair
gplsrc/*.c : alpha
gplsrc/* : delta
docs/* : none
/ROOT.md : none
"""

SCRATCH_REGRESS = 'ALL_SUITES="alpha beta gamma delta"\n'

PROG_V1 = """\
* comment line
st.one:
   a = 1
   return

st.two:
   b = 1
   return

st.three:
   c = 1
   return
"""


def make_repo(tool_path):
    d = tempfile.mkdtemp(prefix="regchg-")
    t = os.path.join(d, "sdb_ai", "sd64")
    write(os.path.join(t, "gplbld", "regress.sh"), SCRATCH_REGRESS)
    write(os.path.join(t, "gplbld", "regress-map.txt"), SCRATCH_MAP)
    shutil.copy(tool_path, os.path.join(t, "gplbld", "regress-changed.py"))
    for s in ("alpha", "beta", "gamma", "delta"):
        write(os.path.join(t, "gplbld", "sandbox-%s.py" % s), "# suite\n")
    write(os.path.join(t, "sdsys", "gpl.bp", "prog"), PROG_V1)
    write(os.path.join(t, "gplsrc", "x.c"), "int x;\n")
    write(os.path.join(t, "docs", "a.txt"), "a\n")
    write(os.path.join(d, "ROOT.md"), "root\n")
    git(d, "init", "-q")
    git(d, "add", "-A")
    git(d, "commit", "-q", "-m", "base")
    return d, t


def tool(t, *args):
    p = run([sys.executable, os.path.join(t, "gplbld", "regress-changed.py")] + list(args), t)
    return p.returncode, p.stdout.split(), p.stderr


def part_b(tool_path, label):
    print("\n--- (B) the selector in a scratch repository (%s) ---------------------------------" % label)
    d, t = make_repo(tool_path)
    try:
        rc, out, err = tool(t)
        row("nothing changed is refused (exit 2), not a pass over nothing", rc == 2 and "nothing has changed" in err, "rc=%d %s" % (rc, err[-200:]))

        write(os.path.join(t, "gplsrc", "x.c"), "int x;\nint y;\n")
        rc, out, err = tool(t)
        row("a changed kernel file selects its suite and the report names the file", rc == 0 and out == ["alpha"] and "gplsrc/x.c" in err, "rc=%d %r" % (rc, out))

        write(os.path.join(t, "docs", "a.txt"), "changed\n")
        rc, out, err = tool(t)
        row("a changed file with rule 'none' adds nothing", rc == 0 and out == ["alpha"], "rc=%d %r" % (rc, out))

        write(os.path.join(t, "zzz", "mystery.bin"), "?\n")
        rc, out, err = tool(t)
        row("a file no rule matches stops the run (exit 2) and is named", rc == 2 and "zzz/mystery.bin" in err and "NO RULE" in err, "rc=%d %s" % (rc, err[-300:]))
        os.remove(os.path.join(t, "zzz", "mystery.bin"))
        os.rmdir(os.path.join(t, "zzz"))

        write(os.path.join(t, "gplbld", "sandbox-newsuite.py"), "# not registered\n")
        rc, out, err = tool(t)
        row("a sandbox file that is not in ALL_SUITES is refused as NOT A SUITE", rc == 2 and "NOT A SUITE" in err, "rc=%d %s" % (rc, err[-300:]))
        os.remove(os.path.join(t, "gplbld", "sandbox-newsuite.py"))

        # restore the two files, then hunk labels
        write(os.path.join(t, "gplsrc", "x.c"), "int x;\n")
        write(os.path.join(t, "docs", "a.txt"), "a\n")
        write(os.path.join(t, "sdsys", "gpl.bp", "prog"), PROG_V1.replace("   a = 1", "   a = 2"))
        rc, out, err = tool(t)
        row("a hunk under st.one selects the base suite and st.one's (alpha beta), not st.two's", rc == 0 and out == ["alpha", "beta"], "rc=%d %r" % (rc, out))
        write(os.path.join(t, "sdsys", "gpl.bp", "prog"), PROG_V1.replace("   b = 1", "   b = 2"))
        rc, out, err = tool(t)
        row("a hunk under st.two selects alpha and gamma", rc == 0 and out == ["alpha", "gamma"], "rc=%d %r" % (rc, out))
        write(os.path.join(t, "sdsys", "gpl.bp", "prog"), PROG_V1.replace("   c = 1", "   c = 2"))
        rc, out, err = tool(t)
        row("a hunk under st.three (no sub-rule but '*') selects the '*' group: alpha beta", rc == 0 and out == ["alpha", "beta"], "rc=%d %r" % (rc, out))
        write(os.path.join(t, "sdsys", "gpl.bp", "prog"), PROG_V1.replace("* comment line", "* a different comment"))
        rc, out, err = tool(t)
        row("a hunk in comments before the first label adds nothing beyond the base suite", rc == 0 and out == ["alpha"], "rc=%d %r" % (rc, out))
        write(os.path.join(t, "sdsys", "gpl.bp", "prog"), PROG_V1.replace("   a = 1", "   a = 2").replace("   b = 1", "   b = 2"))
        rc, out, err = tool(t)
        row("hunks in two labels take both sub-rules (alpha beta gamma)", rc == 0 and out == ["alpha", "beta", "gamma"], "rc=%d %r" % (rc, out))

        git(d, "add", "-A")
        git(d, "commit", "-q", "-m", "second")
        rc, out, err = tool(t)
        row("with everything committed and nothing newer, nothing has changed (exit 2)", rc == 2, "rc=%d %r" % (rc, out))
        rc, out, err = tool(t, "--since", "HEAD~1")
        row("--since HEAD~1 reaches back to the committed change", rc == 0 and out == ["alpha", "beta", "gamma"], "rc=%d %r %s" % (rc, out, err[-200:]))

        rc, out, err = tool(t, "--files", "sdb_ai/sd64/sdsys/gpl.bp/prog")
        row("--files knows no hunks, so every sub-rule applies (alpha beta gamma)", rc == 0 and out == ["alpha", "beta", "gamma"], "rc=%d %r" % (rc, out))

        write(os.path.join(t, "sdsys", "gpl.bp", "newprog"), "x\n")
        rc, out, err = tool(t)
        row("a new file git has not been told about, with no rule, is unmapped", rc == 2 and "newprog" in err, "rc=%d %s" % (rc, err[-200:]))
        os.remove(os.path.join(t, "sdsys", "gpl.bp", "newprog"))
    finally:
        shutil.rmtree(d, ignore_errors=True)
    return d


def part_c():
    print("\n--- (C) regress.sh --changed in a scratch repository ---------------------------------")
    d, t = make_repo(TOOL)
    try:
        shutil.copy(REGRESS, os.path.join(t, "gplbld", "regress.sh"))
        write(os.path.join(t, "gplbld", "regress-map.txt"), SCRATCH_MAP.replace("alpha", "coll").replace("beta", "try").replace("gamma", "gates").replace("delta", "oq2"))
        for s in ("coll", "try", "gates"):
            write(os.path.join(t, "gplbld", "sandbox-%s.py" % s), "# suite\n")
        git(d, "add", "-A")
        git(d, "commit", "-q", "-m", "regress.sh and the real names")
        write(os.path.join(t, "gplsrc", "x.c"), "int x;\nint y;\n")
        p = run(["bash", os.path.join(t, "gplbld", "regress.sh"), "--changed", "--list"], t)
        row("regress.sh --changed --list prints the selected suite", p.returncode == 0 and p.stdout.split() == ["coll"], "rc=%d %r %s" % (p.returncode, p.stdout, p.stderr[-200:]))
        p = run(["bash", os.path.join(t, "gplbld", "regress.sh"), "--changed", "--only", "coll", "--list"], t)
        row("--changed with --only is refused (exit 2)", p.returncode == 2 and "alternatives" in p.stderr, "rc=%d %s" % (p.returncode, p.stderr[-200:]))
        git(d, "checkout", "-q", "--", "sdb_ai/sd64/gplsrc/x.c")
        p = run(["bash", os.path.join(t, "gplbld", "regress.sh"), "--changed", "--list"], t)
        row("--changed with nothing changed is refused (exit 2) and lists nothing", p.returncode == 2 and p.stdout.strip() == "", "rc=%d %r" % (p.returncode, p.stdout))
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------------------------------------------------------------
# --selftest: mutants of the selector.  Each is a text replacement; part (B) must fail on it.

MUTANTS = [
    ("unmapped files are skipped, not refused", "    if unmapped:\n        die(", "    if False:\n        die("),
    ("nothing changed is not refused", "    if not files:\n        die(", "    if False:\n        die("),
    ("the LAST matching rule wins", "    for n, pat, words in rules:\n        target", "    for n, pat, words in reversed(rules):\n        target"),
    ("hunk labels are ignored (every sub-rule always)", "    out = []\n    if labels is None:", "    out = []\n    labels = None\n    if labels is None:"),
    ("a label with no sub-rule adds nothing (no '*' fallback)", "        if not taken:\n            for n, glob, words in subs:", "        if False:\n            for n, glob, words in subs:"),
    ("a sandbox file that is not a suite is accepted", 'if "@self" in words and self_name is None:', "if False:"),
    ("--since is ignored", '    if since:\n        files.update(git(["diff", "--name-only", since, "HEAD"], root).split("\\n"))', "    if False:\n        pass"),
]


def selftest():
    global passed, failed
    caught = 0
    with open(TOOL) as f:
        src = f.read()
    for name, old, new in MUTANTS:
        if src.count(old) != 1:
            print("  [FAIL] mutant '%s': its anchor text occurs %d times in the selector (it must occur once)" % (name, src.count(old)))
            failed += 1
            continue
        tmp = tempfile.mkdtemp(prefix="regchg-mut-")
        mpath = os.path.join(tmp, "regress-changed.py")
        write(mpath, src.replace(old, new))
        before_f = failed
        saved_p = passed
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            try:
                part_b(mpath, "mutant")
            except SystemExit:
                failed += 1
        killed = failed > before_f
        failed, passed = before_f, saved_p
        shutil.rmtree(tmp, ignore_errors=True)
        row("mutant killed: %s" % name, killed, "every row of part B still passed on this mutant")
        caught += killed
    print("\nselftest: %d of %d mutants killed" % (caught, len(MUTANTS)))


def main():
    if "--selftest" in sys.argv:
        selftest()
    else:
        part_a()
        part_b(TOOL, "real selector")
        part_c()
    print("\ntest-regress-changed-units: %d passed, %d failed" % (passed, failed))
    if passed + failed == 0:
        print("no row ran - a broken test, not a pass")
        return 2
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
