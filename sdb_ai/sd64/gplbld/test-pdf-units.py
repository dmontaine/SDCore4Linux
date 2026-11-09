#!/usr/bin/env python3
"""test-pdf-units.py - DOCS.INSTALL and the shared account's pdf directory (S.75, plan .claude/plan-fullscreen-toolkit.md section 14.7), as invariants read off the source.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-pdf-units.py
  python3 .../test-pdf-units.py --selftest

No sudo, no install, no sd.  Exit 0 every check passed, 1 a check failed, 2 it could not run.

WHAT IT HOLDS.  DOCS.INSTALL asks for the administrator first, reads only a plain absolute directory, copies only lower case .pdf files that start with %PDF- into the pdf
directory of the shared account and never makes that directory; DOCS.INSTALL and LOAD.HELP are SDSYS's verbs only; the installer's content block makes the pdf directory
sdsys:sdusers mode 755 (no SD user can add a document) and runs load.help so that it cannot stop the install.

9 Nov 26 (S.187): the pdf verb, !viewlist, SET.VIEWER and the Bypass programs page (tool.viewers) were REMOVED from Core (owner, 9 Nov 2026: the pdf verb only works at the
machine's own display), with messages 11843-11849, 11887, 11888 and 11890-11899 and the installer's VIEWER-ASK block.  Their checks (D1-D11, D14, D17, D19 and the viewer half of
D15, D16 and D18) and their mutants went with them; the checks of what stays (DOCS.INSTALL, LOAD.HELP's entry, the pdf directory, messages 11720-11724) are kept under their old
names.  D15 now also holds that the removed VOC records are in neither VOC source.

***IT READS THE SOURCE AS TEXT AND DOES NOT RUN BASIC OR THE INSTALLER.***  The installer's content block runs under its own shell options in test-install-docs.sh.

--selftest mutates the source in the ways this could plausibly be broken and requires each mutation to be CAUGHT and to match its text exactly once.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SDSYS = os.path.abspath(os.path.join(HERE, os.pardir, "sdsys"))
GPL = os.path.join(SDSYS, "gpl.bp")
INSTALLER = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir, os.pardir, "installsdcore.sh"))
PROGS = ("docsinst",)
MSGS = tuple(str(n) for n in range(11720, 11725))
VOC_SDSYS_ONLY = ("docs.install", "load.help")
VOC_REMOVED = ("pdf", "set.viewer", "tool.viewers")          # S.187, 9 Nov 26


def strip(src):
    """The code: full-line comments and ;* tails removed."""
    out = []
    for ln in src.split("\n"):
        if ln.lstrip().startswith("*"):
            continue
        out.append(re.sub(r"\s*;\*.*$", "", ln))
    return "\n".join(out)


def read(path):
    with open(path, encoding="latin-1") as f:
        return f.read()


def between(text, a, b):
    i = text.find(a)
    if i < 0:
        return ""
    j = text.find(b, i + len(a))
    return text[i:j] if j >= 0 else text[i:]


def load():
    src = {n: read(os.path.join(GPL, n)) for n in PROGS}
    src["installer"] = read(INSTALLER)
    src["msgs"] = {n: (read(os.path.join(SDSYS, "messages", n)) if os.path.exists(os.path.join(SDSYS, "messages", n)) else None) for n in MSGS}
    src["voc"] = {(d + "/" + n): os.path.exists(os.path.join(SDSYS, d, n)) for d in ("newvoc", "voc_template") for n in VOC_SDSYS_ONLY + VOC_REMOVED}
    return src


def checks(s):
    rows = []

    def ck(name, ok, detail=""):
        rows.append((name, bool(ok), detail))

    di = strip(s["docsinst"])
    ins = s["installer"]

    ck("D0 the sources were found (the null case: nothing to compare passes every row)", len(di) > 2000 and len(ins) > 50000, repr((len(di), len(ins))))

    # DOCS.INSTALL
    j_adm = di.find("kernel(K$ADMINISTRATOR, -1)")
    j_words = di.find("words = trim(@sentence)")
    ck("D12 DOCS.INSTALL asks for the administrator first; the directory is a plain absolute path; the destination is the pdf directory of the shared account and is never made here; no sub-directory is read",
       0 < j_adm < j_words and "src[1, 1] # @ds or len(src) > 200 or trim(convert(okc, space(len(okc)), src)) # '' or index(src, '..', 1) > 0" in di and "dest = spath : @ds : 'pdf'" in di
       and "mkdir" not in di and "if entries<i, 2> # 'F' then continue" in di)
    ck("D13 ...a file is copied only if its name is lower case letters, digits and . _ - ending in .pdf and not starting with a dot, and the file starts with %PDF- ; cp is given quoted checked parts after --, the copy is mode 0644, and what is not there afterwards counts as skipped",
       "nm = downcase(nm)" in di and "if magic[1, 5] # '%PDF-' then" in di and di.find("if magic[1, 5] # '%PDF-' then") < di.find("os.execute \"cp -f -- '\"") and "chmod 0644 '" in di and "not(ospath(dest : @ds : nm, OS$EXISTS))" in di)

    # the entries
    v = s["voc"]
    ck("D15 the VOC: DOCS.INSTALL and LOAD.HELP for SDSYS ONLY (voc_template, not newvoc); PDF, SET.VIEWER and TOOL.VIEWERS in neither (removed, S.187)",
       all(v["voc_template/" + n] and not v["newvoc/" + n] for n in VOC_SDSYS_ONLY) and not any(v[d + "/" + n] for d in ("newvoc", "voc_template") for n in VOC_REMOVED), repr(v))
    m = s["msgs"]
    ck("D16 messages 11720 to 11724 exist, each one line", all(m[n] and m[n].count("\n") == 1 for n in MSGS), repr([n for n in MSGS if not m[n] or m[n].count("\n") != 1]))

    # the installer
    cont = between(ins, "# SHARED-CONTENT-BEGIN", "# SHARED-CONTENT-END")
    ck("D18 the installer's content block (after the shared account is made): the pdf directory is owner sdsys, group sdusers, mode 755; load.help runs with input from /dev/null and cannot stop the install",
       ins.find("# SHARED-CREATE-END") < ins.find("# SHARED-CONTENT-BEGIN") < ins.find("# 11 Sep 26  AN UPGRADE BRINGS EVERY ACCOUNT'S VOC FORWARD")
       and 'sudo mkdir -p "${shared_dir}/pdf"' in cont and 'sudo chown sdsys:sdusers "${shared_dir}/pdf"' in cont and 'sudo chmod 755 "${shared_dir}/pdf"' in cont
       and "sudo bin/sd -internal load.help < /dev/null || true" in cont, repr(len(cont)))
    return rows


MUTANTS = [
    ("DOCS.INSTALL does not ask for the administrator", "docsinst", "   if not(kernel(K$ADMINISTRATOR, -1)) then\n      stop sysmsg(2001) ;* Command requires administrator privileges\n   end\n", ""),
    ("DOCS.INSTALL copies a file that is not a PDF", "docsinst", "   if magic[1, 5] # '%PDF-' then", "   if @false then"),
    ("DOCS.INSTALL copies a name with a capital", "docsinst", " and nm = downcase(nm))", ")"),
    ("DOCS.INSTALL makes the directory", "docsinst", "   dest = spath : @ds : 'pdf'\n", "   dest = spath : @ds : 'pdf'\n   os.execute \"mkdir -p '\" : dest : \"'\" capturing mo\n"),
    ("DOCS.INSTALL reads a path with .. in it", "docsinst", " or index(src, '..', 1) > 0", ""),
    ("the installer's pdf directory is writable by the group", "installer", 'sudo chmod 755 "${shared_dir}/pdf"', 'sudo chmod 775 "${shared_dir}/pdf"'),
    ("load.help can stop the install", "installer", "sudo bin/sd -internal load.help < /dev/null || true", "sudo bin/sd -internal load.help < /dev/null"),
]


def selftest():
    s = load()
    base = [n for n, ok, _ in checks(s) if not ok]
    if base:
        print("REFUSING - the unmutated source already fails: %s" % ", ".join(base), file=sys.stderr)
        return 2
    holes = 0
    print("--- self-test: the unmutated source passes; each mutation must be CAUGHT and match its text once ---")
    for name, which, old, new in MUTANTS:
        if s[which].count(old) != 1:
            print("  [FAIL] %s: the text to mutate matches %d times in %s, not once" % (name, s[which].count(old), which))
            holes += 1
            continue
        s2 = dict(s)
        s2[which] = s[which].replace(old, new)
        caught = [n for n, ok, _ in checks(s2) if not ok]
        if caught:
            print("  [pass] %s: caught by %s" % (name, ", ".join(caught[:3])))
        else:
            print("  [FAIL] %s: NOT CAUGHT by any check" % name)
            holes += 1
    print("self-test: %d mutants, %d not caught" % (len(MUTANTS), holes))
    return 1 if holes else 0


def main():
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    s = load()
    rows = checks(s)
    bad = 0
    for name, ok, detail in rows:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, ("   <- " + detail) if (detail and not ok) else ""))
        bad += 0 if ok else 1
    print("test-pdf-units: %d checks, %d failed" % (len(rows), bad))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
