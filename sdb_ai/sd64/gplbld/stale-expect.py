#!/usr/bin/env python3
#
# stale-expect.py - a suite that still expects wording SD no longer prints (S.186).  No install, no sudo, no sd: git and the files.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/stale-expect.py [--since REF] [--selftest]
#
# START-HISTORY:
# 9 Nov 26 dm  New (S.186; the owner, 9 Nov: "is there a check that we could add before suites are run to avoid simple failures like spelling").  The
#              US spelling sweep changed what SD prints and 20 suites failed only on the old wording, after 50 minutes; two NEGATIVE checks (not has
#              "added to local catalogue", "Catalogued" not in the status) passed whatever SD did, because SD no longer printed the text at all.
#              Same day: SD's text "now" is the messages, the help and the LITERALS of the programs and C files, not their comments ('* Unrecognised
#              statement' had kept a removed wording alive); and a suite literal SHORTER than a removed text, regex escapes taken out, is found inside
#              it.  Together they found 21 more stale lines in 12 suites.
# END-HISTORY
#
# WHAT IT DOES.  The text SD prints is in sdsys/messages/*, sdsys/helptext/*, the string literals of sdsys/gpl.bp/* and of gplsrc/*.c.  From the change
# since REF (the working tree against REF; HEAD when no REF is given) it takes every REMOVED line of those files and the wording on it: a message line
# whole, the literals of a program or C line; each is cut at its substitutions (%1, %s, %d) into pieces of 12 characters or more.  A piece that still
# appears anywhere in SD's text now is not gone and is dropped.  What is left is wording the change took away.  It then looks for each piece in what
# the suites EXPECT - the string literals of gplbld/sandbox-*.py that are not the title of a row (the first argument of row, arow, say, bail ...) and
# not a docstring - and in the fenced blocks of the agent pack's guide, which the guide suite compares with SD's output.  Every piece found is printed
# with its file and line, and the exit is 1: the suite would fail, or worse, a check that the text is NOT there would pass for nothing.
#
# WHAT IT DOES NOT.  It cannot see a suite that builds the text it expects from pieces, or a wording SD makes at run time; it does not judge whether
# a removed text was printed at all (a removed literal may have been a name: that piece is reported, and the reader decides).  Exit 0 nothing stale,
# 1 stale expectations, 2 it could not run (no git, no change base).

import ast
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.dirname(HERE)
MIN = 12
TITLE = re.compile(r"(?:^|\.)(row|arow|say|bail|ck|add|optadd|mut|mutant|case)$")


def git(*args):
    p = subprocess.run(["git", "-C", SD64] + list(args), capture_output=True, text=True, errors="replace")
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or "git %s failed" % " ".join(args))
    return p.stdout


def literals_basic(line):
    st = line.lstrip()
    if st.startswith("*") or st.startswith("!"):
        return []
    out, i, n = [], 0, len(line)
    while i < n:
        ch = line[i]
        if ch == ";" and line[i:i + 2] == ";*":
            break
        if ch in "'\"":
            j = line.find(ch, i + 1)
            if j < 0:
                break
            out.append(line[i + 1:j])
            i = j + 1
            continue
        i += 1
    return out


def literals_c(line):
    if line.lstrip().startswith(("/*", "*", "//")):
        return []
    return re.findall(r'"((?:[^"\\\n]|\\.)*)"', line)


def pieces(text):
    return [p.strip() for p in re.split(r"%[0-9sdfcux]|\\n|\\t", text) if len(p.strip()) >= MIN]


def removed_pieces(diff):
    """diff: unified diff text.  Returns {piece: 'path'} for the wording on removed lines."""
    out = {}
    path = ""
    for line in diff.split("\n"):
        if line.startswith("+++ b/"):
            path = line[6:]
            continue
        if not line.startswith("-") or line.startswith("---"):
            continue
        body = line[1:]
        if "/messages/" in path or "/helptext/" in path:
            texts = [body]
        elif "/gpl.bp/" in path:
            texts = literals_basic(body)
        elif path.endswith(".c"):
            texts = literals_c(body)
        else:
            texts = []
        for t in texts:
            for p in pieces(t):
                out.setdefault(p, path)
    return out


def corpus():
    parts = []
    for sub in ("sdsys/messages", "sdsys/helptext", "sdsys/gpl.bp", "gplsrc"):
        d = os.path.join(SD64, sub)
        for nm in os.listdir(d):
            f = os.path.join(d, nm)
            if os.path.isfile(f):
                with open(f, encoding="latin-1") as fh:
                    txt = fh.read()
                # only the text SD prints: a comment that still quotes the old wording ('* Unrecognised statement') does not keep it alive
                if sub == "sdsys/gpl.bp":
                    txt = "\n".join(x for ln in txt.split("\n") for x in literals_basic(ln))
                elif sub == "gplsrc":
                    txt = "\n".join(x for ln in txt.split("\n") for x in literals_c(ln)) if nm.endswith((".c", ".h")) else ""
                parts.append(txt)
    return "\n".join(parts)


def expectations(path):
    """[(line, text)] of the string literals of a suite that are not titles or docstrings."""
    with open(path, encoding="utf-8", errors="replace") as f:
        src = f.read()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    skip = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            nm = fn.attr if isinstance(fn, ast.Attribute) else (fn.id if isinstance(fn, ast.Name) else "")
            if TITLE.search(nm or "") and node.args:
                for a in ast.walk(node.args[0]):
                    skip.add(id(a))
        if isinstance(node, (ast.FunctionDef, ast.Module, ast.ClassDef)) and node.body and isinstance(node.body[0], ast.Expr) \
                and isinstance(getattr(node.body[0], "value", None), ast.Constant):
            skip.add(id(node.body[0].value))
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skip:
            out.append((node.lineno, node.value))
    return out


def guide_blocks(path):
    out, fenced, n0 = [], False, 0
    if not os.path.isfile(path):
        return out
    with open(path, encoding="utf-8", errors="replace") as f:
        for n, line in enumerate(f, 1):
            if line.lstrip().startswith("```"):
                fenced = not fenced
                continue
            if fenced:
                out.append((n, line.rstrip("\n")))
    return out


def unregex(text):
    """A suite's expectation is often a regular expression: a backslash before punctuation is taken out, and the anchors, so that its words can be compared."""
    t = re.sub(r"\\([^A-Za-z0-9])", r"\1", text)
    return t.strip("^$")


def find_stale(gone, suites, guide, now=""):
    """gone: {piece: source}; suites: {name: [(line, text)]}; guide: [(line, text)]; now: SD's text as it is.  Returns [(file, line, piece, source)].
    Both ways round: a removed piece inside a suite's literal, and a suite literal of MIN characters or more inside a removed piece (a shorter
    expectation, such as 'initialisation value must be', of a longer text) that SD's text no longer holds anywhere."""
    hits = []
    for name, lits in sorted(suites.items()):
        for ln, text in lits:
            plain = unregex(text)
            for p, src in gone.items():
                if p in text or p in plain:
                    hits.append((name, ln, p, src))
                elif len(plain.strip()) >= MIN and plain.strip() in p and plain.strip() not in now:
                    hits.append((name, ln, plain.strip(), src))
    for ln, text in guide:
        for p, src in gone.items():
            if p in text:
                hits.append(("agent-pack/guide/sd-basic-guide.md", ln, p, src))
    return hits


def run(since):
    diff = git("diff", "-U0", since or "HEAD", "--", "sdsys/messages", "sdsys/helptext", "sdsys/gpl.bp", "gplsrc")
    gone_all = removed_pieces(diff)
    now = corpus()
    gone = {p: s for p, s in gone_all.items() if p not in now}
    suites = {nm: expectations(os.path.join(HERE, nm)) for nm in sorted(os.listdir(HERE)) if nm.startswith("sandbox-") and nm.endswith(".py")}
    guide = guide_blocks(os.path.join(SD64, "agent-pack", "guide", "sd-basic-guide.md"))
    print("stale-expect: change since %s: %d removed piece(s) of wording, %d no longer anywhere in SD; %d suites, %d guide lines read"
          % (since or "HEAD", len(gone_all), len(gone), len(suites), len(guide)))
    if not suites:
        print("stale-expect: CANNOT RUN - no sandbox-*.py was read")
        return 2
    hits = find_stale(gone, suites, guide, now)
    for f, ln, p, src in hits:
        print("  STALE %s:%s expects %r, which %s no longer has" % (f, ln, p, src))
    print("stale-expect: %d stale expectation(s)" % len(hits))
    return 1 if hits else 0


def selftest():
    bad = 0
    diff = ("+++ b/sdb_ai/sd64/sdsys/messages/3029\n-%1 added to local catalogue\n+%1 added to local catalog\n"
            "+++ b/sdb_ai/sd64/sdsys/gpl.bp/zz\n-   crt 'Program is in the catalogue' ; * not this\n"
            "+++ b/sdb_ai/sd64/gplsrc/zz.c\n-   printf(\"Unrecognised argument '%s'\\n\", a);\n")
    gone = removed_pieces(diff)
    cases = [
        ("a removed message line gives its wording", " added to local catalogue" in gone or "added to local catalogue" in gone),
        ("a removed BASIC literal gives its wording", "Program is in the catalogue" in gone),
        ("a removed C literal gives its wording, cut at %s", "Unrecognised argument '" in gone),
    ]
    suites = {"sandbox-a.py": [(10, "zz added to local catalogue"), (11, "unrelated text here")],
              "sandbox-b.py": [(5, "Unrecognized argument 'x'")]}
    g = {p: s for p, s in gone.items()}
    hits = find_stale(g, suites, [(3, "Program is in the catalogue")])
    cases.append(("a suite literal holding removed wording is reported", any(h[0] == "sandbox-a.py" and h[1] == 10 for h in hits)))
    cases.append(("a guide line holding removed wording is reported", any(h[0].endswith("sd-basic-guide.md") for h in hits)))
    cases.append(("CONTROL: a suite that expects the new wording is not reported", not any(h[0] == "sandbox-b.py" for h in hits)))
    h2 = find_stale({"An initialisation value must be a numeric constant": "m"}, {"sandbox-c.py": [(7, r"initialisation value must\ be")],
                                                                                  "sandbox-d.py": [(8, "value must be a")]},
                    [], now="An initialization value must be a numeric constant")
    cases.append(("a SHORTER expectation (a regex) inside removed wording is reported", any(h[0] == "sandbox-c.py" for h in h2)))
    cases.append(("CONTROL: a shorter expectation that SD's text still holds is not", not any(h[0] == "sandbox-d.py" for h in h2)))
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as t:
        t.write('"""docstring added to local catalogue"""\nrow("title added to local catalogue", "x added to local catalogue" in out)\n')
        tp = t.name
    lits = expectations(tp)
    os.unlink(tp)
    cases.append(("CONTROL: a row's title and a docstring are not expectations; the compared literal is", [x for _l, x in lits] == ["x added to local catalogue"]))
    for name, ok in cases:
        print("  [%s] selftest: %s" % ("pass" if ok else "MISS", name))
        bad += 0 if ok else 1
    print("selftest: %d cases, %d missed" % (len(cases), bad))
    return 1 if bad else 0


def main():
    if "--selftest" in sys.argv:
        return selftest()
    since = ""
    if "--since" in sys.argv:
        i = sys.argv.index("--since")
        since = sys.argv[i + 1] if i + 1 < len(sys.argv) else ""
    try:
        return run(since)
    except RuntimeError as e:
        print("stale-expect: CANNOT RUN - %s" % e)
        return 2


if __name__ == "__main__":
    sys.exit(main())
