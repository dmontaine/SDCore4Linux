#!/usr/bin/env python3
#
# regress-changed.py - which sandbox suites a change needs.  The selector behind  regress.sh --changed.  No install, no sudo,
#                      read only (it runs `git status` / `git diff` and reads two text files).
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/regress-changed.py                 files changed since HEAD
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/regress-changed.py --since REF     files changed since REF
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/regress-changed.py --files A B ... these files (repo paths)
#
# stdout: the suites, space separated, in regress.sh's own order (longest first).  stderr: the report - every changed file,
# the rule of regress-map.txt that took it, and what it selected.  Exit 0 suites chosen (or every change needs none), 2 it
# could not decide: nothing changed, a changed file no rule matches, a bad map, a suite the map names and regress.sh lacks.
#
# START-HISTORY:
# 15 Oct 26 dm  New.  The owner asked twice for targeted regressions (14 and 15 Oct 2026).
# END-HISTORY
#
# AN INSTRUMENT SHOWS WHAT IT DID (CLAUDE.md).  The report lists the files it was given, one line each with the rule that
# took it; a file that no rule matches is a refusal, never a silent skip; and a change that selects nothing says "no sandbox
# suite" in so many words, because "nothing was run" must not look like "everything passed".

import fnmatch
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TREE = os.path.dirname(HERE)
MAPFILE = os.path.join(HERE, "regress-map.txt")
REGRESS = os.path.join(HERE, "regress.sh")
TREE_PREFIX = "sdb_ai/sd64/"


def err(msg):
    print(msg, file=sys.stderr)


def die(msg):
    err("regress-changed: CANNOT DECIDE - " + msg)
    sys.exit(2)


def all_suites(path=REGRESS):
    """The suite names in regress.sh's ALL_SUITES, in its order."""
    with open(path, errors="replace") as f:
        m = re.search(r'(?m)^ALL_SUITES="([^"]*)"', f.read())
    if not m:
        die("no ALL_SUITES line in %s" % path)
    return m.group(1).split()


def parse_map(path=MAPFILE):
    """Returns (groups, rules, subrules).  groups: name -> [words]; rules: [(lineno, pattern, [words])]; subrules: file pattern ->
    [(lineno, label glob, [words])].  Words are suites, @group, @self, none."""
    groups, rules, subrules = {}, [], {}
    with open(path, errors="replace") as f:
        for n, raw in enumerate(f, 1):
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            m = re.match(r"^(@[\w.-]+)\s*=\s*(.*)$", line)
            if m:
                groups[m.group(1)] = m.group(2).split()
                continue
            m = re.match(r"^(\S+)\s+~\s+(\S+)\s+:\s*(.*)$", line)
            if m:
                words = m.group(3).split()
                if not words:
                    die("%s line %d names no suites: %r" % (path, n, raw.rstrip()))
                subrules.setdefault(m.group(1), []).append((n, m.group(2), words))
                continue
            m = re.match(r"^(\S+)\s+:\s*(.*)$", line)
            if not m:
                die("%s line %d is neither a group nor a rule (a rule is  pattern : suites): %r" % (path, n, raw.rstrip()))
            pat, words = m.group(1), m.group(2).split()
            if not words:
                die("%s line %d names no suites (write 'none' for no suite): %r" % (path, n, raw.rstrip()))
            rules.append((n, pat, words))
    return groups, rules, subrules


def expand(words, groups, suites, where, self_name=None, seen=()):
    """The suite names for a rule's words.  'none' alone is the empty set."""
    out = []
    for w in words:
        if w == "none":
            if len(words) != 1:
                die("%s: 'none' must stand alone" % where)
            continue
        if w == "@self":
            if self_name is None:
                die("%s: @self is for a gplbld/sandbox-*.py rule" % where)
            out.append(self_name)
        elif w.startswith("@"):
            if w not in groups:
                die("%s: unknown group %s" % (where, w))
            if w in seen:
                die("%s: group %s uses itself" % (where, w))
            out += expand(groups[w], groups, suites, where + " > " + w, self_name, seen + (w,))
        else:
            if w not in suites:
                die("%s: suite '%s' is not in regress.sh's ALL_SUITES (a stale map?)" % (where, w))
            out.append(w)
    return out


def match(rules, rel, repo_rel):
    """The first rule that takes the file: (lineno, pattern, words) or None."""
    for n, pat, words in rules:
        target = repo_rel if pat.startswith("/") else rel
        if target is None:
            continue
        p = pat[1:] if pat.startswith("/") else pat
        if fnmatch.fnmatchcase(target, p):
            return n, pat, words
    return None


def git(args, cwd):
    p = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, errors="replace")
    if p.returncode != 0:
        die("git %s failed: %s" % (" ".join(args), p.stderr.strip()))
    return p.stdout


def changed_files(since):
    """(repo-relative paths, the untracked ones among them): committed since REF (when given), the working tree against HEAD,
    and files git has not been told about."""
    root = git(["rev-parse", "--show-toplevel"], TREE).strip()
    files = set()
    if since:
        files.update(git(["diff", "--name-only", since, "HEAD"], root).split("\n"))
    files.update(git(["diff", "--name-only", "HEAD"], root).split("\n"))
    untracked = set(f for f in git(["ls-files", "--others", "--exclude-standard"], root).split("\n") if f)
    files.update(untracked)
    return sorted(f for f in files if f), untracked


def hunk_labels(path, since, untracked):
    """The label (the first word of git's hunk-header function name: the nearest line before the hunk that starts in column 1
    with a letter, '_' or '$') of every hunk changed in PATH, as a sorted list - empty when the hunks lie in comments before
    the first such line.  None when it cannot be known (a file git has not been told about, or no diff to read): the caller
    then takes every sub-rule."""
    if path in untracked:
        return None
    root = git(["rev-parse", "--show-toplevel"], TREE).strip()
    labels, seen_hunk = set(), False
    for ref in ([since] if since else []) + ["HEAD"]:
        for line in git(["diff", "-U0", ref, "--", path], root).split("\n"):
            m = re.match(r"^@@ [^@]*@@ ?(.*)$", line)
            if m:
                seen_hunk = True
                words = re.split(r"[\s:(]", m.group(1).strip(), maxsplit=1)
                if words and words[0]:
                    labels.add(words[0])
    return sorted(labels) if seen_hunk else None


def sub_suites(subs, labels, groups, suites):
    """The suites a file's sub-rules add for its changed hunk LABELS.  Labels None: all of them (nothing is known).  A label no
    sub-rule but '*' matches takes the '*' rule; with no '*' rule it adds nothing."""
    out = []
    if labels is None:
        for n, glob, words in subs:
            out += expand(words, groups, suites, "line %d" % n)
        return out
    for lab in labels:
        taken = False
        for n, glob, words in subs:
            if glob != "*" and fnmatch.fnmatchcase(lab, glob):
                out += expand(words, groups, suites, "line %d" % n)
                taken = True
        if not taken:
            for n, glob, words in subs:
                if glob == "*":
                    out += expand(words, groups, suites, "line %d" % n)
    return out


def select(files, groups, rules, suites, subrules=None, labels_of=None):
    """Returns (chosen suites in ALL_SUITES order, unmapped files, lines of the report).  SUBRULES: file pattern -> hunk label
    rules; LABELS_OF(path) gives a file's changed hunk labels (None when unknown)."""
    subrules = subrules or {}
    chosen, unmapped, lines = set(), [], []
    for f in files:
        rel = f[len(TREE_PREFIX):] if f.startswith(TREE_PREFIX) else None
        repo_rel = f
        hit = match(rules, rel, repo_rel)
        if hit is None:
            unmapped.append(f)
            lines.append("  %-62s NO RULE" % f)
            continue
        n, pat, words = hit
        self_name = None
        m = re.match(r"^gplbld/sandbox-(.+)\.py$", rel or "")
        if m and m.group(1) in suites:
            self_name = m.group(1)
        if "@self" in words and self_name is None:
            # a sandbox-*.py that is no suite in regress.sh: a new suite not yet registered, or a tool with no rule of its
            # own.  Either is a decision for a person, not something to pass over.
            unmapped.append(f)
            lines.append("  %-62s line %-3d NOT A SUITE in ALL_SUITES (register it, or give the tool a rule)" % (f, n))
            continue
        sel = expand(words, groups, suites, "line %d" % n, self_name)
        note = ""
        if pat in subrules:
            labels = labels_of(f) if labels_of else None
            sel += sub_suites(subrules[pat], labels, groups, suites)
            note = " [hunks: %s]" % ("unknown, every sub-rule" if labels is None else (", ".join(labels) or "comments only"))
        chosen.update(sel)
        shown = "no sandbox suite" if not sel else "%d: %s" % (len(set(sel)), " ".join(s for s in suites if s in set(sel)))
        lines.append("  %-62s line %-3d %s%s" % (f, n, shown, note))
    return [s for s in suites if s in chosen], unmapped, lines


def main(argv):
    since, files = None, None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--since":
            since = argv[i + 1]
            i += 2
        elif a == "--files":
            files = argv[i + 1:]
            break
        elif a in ("-h", "--help"):
            print(open(__file__).read().split("# START-HISTORY")[0])
            return 0
        else:
            die("unknown argument %r" % a)
    suites = all_suites()
    groups, rules, subrules = parse_map()
    untracked = set()
    explicit = files is not None
    if files is None:
        files, untracked = changed_files(since)
    err("regress-changed: map %s, %d rules, %d groups; %d suites in regress.sh" % (MAPFILE, len(rules), len(groups), len(suites)))
    if not files:
        die("nothing has changed%s: there is nothing to select (use --since REF, or regress.sh --only NAME)"
            % (" since " + since if since else " since HEAD"))
    # --files names files, not changes: nothing is known about their hunks, so a file with sub-rules takes all of them
    labels_of = None if explicit else (lambda p: hunk_labels(p, since, untracked))
    chosen, unmapped, lines = select(files, groups, rules, suites, subrules, labels_of)
    err("regress-changed: %d changed file(s)%s" % (len(files), " since " + since if since else " (working tree against HEAD)"))
    for l in lines:
        err(l)
    if unmapped:
        die("%d changed file(s) match no rule in %s: %s (add a rule - 'none' if it needs no suite - or run regress.sh --only)"
            % (len(unmapped), os.path.basename(MAPFILE), ", ".join(unmapped)))
    if not chosen:
        err("regress-changed: NO SANDBOX SUITE is needed for these changes (the free checks are the check); nothing selected")
    else:
        err("regress-changed: %d of %d suites selected" % (len(chosen), len(suites)))
    print(" ".join(chosen))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
