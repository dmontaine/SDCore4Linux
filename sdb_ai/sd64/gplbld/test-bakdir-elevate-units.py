#!/usr/bin/env python3
# test-bakdir-elevate-units.py - sd-elevate's bakdir-set (S.53, SET.BACKUP.DIRECTORY).
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-bakdir-elevate-units.py
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-bakdir-elevate-units.py --selftest
#
# No sudo, no install, no sd.  It CUTS the two shipped functions out of sd-elevate - the lines
# between "# BEGIN bakdir_functions" and "# END bakdir_functions" - and runs them with bash on
# scratch directories and scratch sd.conf files: bakdir_checked (which paths may be saved) and
# conf_set_backupdir (the rewrite of the file).  Root's own step is just those two plus
# "mv" onto /etc/sd.conf, so what is measured here is what decides what root writes.
# (Windows has a test-bakdir-units.py of its own for ITS editor; this is not that file.)
#
# EVERY CHECK PRINTS THE INPUT IT USED AND WHAT IT SAW.  It refuses (exit 2) when the markers
# are not found exactly once, and --selftest breaks the shipped code six ways and requires the
# checks to catch each one.
#
# Exit 0 every check passed, 1 a check failed, 2 it could not measure.

import io
import contextlib
import os
import shlex
import stat
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ELEVATE = os.path.join(HERE, "sd-elevate")
BEGIN = "# BEGIN bakdir_functions"
END = "# END bakdir_functions"


def cut_code(path):
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    b = [i for i, l in enumerate(lines) if l.strip() == BEGIN]
    e = [i for i, l in enumerate(lines) if l.strip() == END]
    if len(b) != 1 or len(e) != 1 or b[0] >= e[0]:
        print("REFUSED: %s must hold exactly one '%s' and one '%s' line, in that order (found %d and %d)"
              % (path, BEGIN, END, len(b), len(e)), file=sys.stderr)
        sys.exit(2)
    return "\n".join(lines[b[0] + 1:e[0]])


class Suite:
    def __init__(self, code):
        self.code = code
        self.checks = 0
        self.failed = 0
        self.quiet = False

    def check(self, name, expected, ok, saw):
        self.checks += 1
        if not ok:
            self.failed += 1
        if not self.quiet or not ok:
            saw = repr(saw) if not isinstance(saw, str) else saw
            print("  [%s] %s | expected: %s | saw: %s" % ("PASS" if ok else "FAIL", name, expected, saw[:230]))

    def bash(self, call):
        script = ('set -uo pipefail\ndie() { printf "REFUSED - %%s\\n" "$1" >&2; exit 2; }\n%s\n%s\n' % (self.code, call))
        return subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=60)

    def verdict(self, path):
        r = self.bash("bakdir_checked %s" % shlex.quote(path))
        return r.returncode, r.stderr.strip()

    def conf(self, f, p):
        return self.bash("conf_set_backupdir %s %s" % (shlex.quote(f), shlex.quote(p)))

    def suite(self):
        S = self
        with tempfile.TemporaryDirectory() as tmp:
            good = os.path.join(tmp, "backups")
            os.mkdir(good)
            spaced = os.path.join(tmp, "my backups")
            os.mkdir(spaced)
            afile = os.path.join(tmp, "afile")
            open(afile, "w").write("x")

            # ---- bakdir_checked: which paths may be saved
            rc, err = S.verdict(good)
            S.check("V1 an existing full path is accepted", "exit 0", rc == 0, "exit %d %s" % (rc, err))
            rc, err = S.verdict(spaced)
            S.check("V2 a space inside a component is accepted", "exit 0", rc == 0, "exit %d %s" % (rc, err))
            refusals = [
                ("V3 empty", "", "no directory"),
                ("V4 relative", "backups/x", "not a full path"),
                ("V5 does not exist", os.path.join(tmp, "nope"), "not an existing directory"),
                ("V6 a file, not a directory", afile, "not an existing directory"),
                ("V7 a .. component", good + "/../backups", "or .. path component"),
                ("V8 a . component", good + "/.", "or .. path component"),
                ("V9 an empty component (//)", tmp + "//backups", "empty path component"),
                ("V10 a trailing /", good + "/", "must not end with /"),
                ("V11 a NEWLINE (would add a second line to sd.conf)", good + "\nSDSYS=/evil", "may hold only"),
                ("V12 a single quote", good + "'x", "may hold only"),
                ("V13 a dollar sign", good + "$x", "may hold only"),
                ("V14 a backtick", good + "`x", "may hold only"),
                ("V15 a semicolon", good + ";x", "may hold only"),
                ("V16 a hash (a comment in sd.conf)", good + "#x", "may hold only"),
                ("V17 a backslash", good + "\\x", "may hold only"),
                ("V18 a component that starts with a space", tmp + "/ lead", "starts or ends with a space"),
                ("V19 a path that ends with a space", good + " ", "starts or ends with a space"),
                ("V20 181 characters", "/" + "a" * 180, "longer than 180"),
            ]
            for name, path, want in refusals:
                rc, err = S.verdict(path)
                S.check(name, "exit 2 and '%s'" % want, rc == 2 and want in err, "exit %d %s" % (rc, err))
            longdir = os.path.join(tmp, "l" * 160)
            os.mkdir(longdir)
            full = longdir
            if len(full) <= 180:
                rc, err = S.verdict(full)
                S.check("V21 a path of %d characters (inside the limit) is accepted" % len(full), "exit 0", rc == 0, "exit %d %s" % (rc, err))

            # ---- conf_set_backupdir: what root writes
            def conf_with(text, mode=0o644):
                f = os.path.join(tmp, "sd.conf")
                with open(f, "w", newline="") as fh:
                    fh.write(text)
                os.chmod(f, mode)
                return f

            base = "# SD configuration\nSDSYS=/usr/local/sdsys\nUMASK=027\nDUMPDIR=/usr/local/sdsys/dumps\n"
            f = conf_with(base)
            r = S.conf(f, good)
            got = open(f).read()
            S.check("C1 a file with no key: the line is appended, every other line kept",
                    "base + 'BACKUPDIR=<dir>' as the last line", r.returncode == 0 and got == base + "BACKUPDIR=%s\n" % good,
                    "exit %d %r" % (r.returncode, got))

            f = conf_with("# c\nBACKUPDIR=/old/one\nSDSYS=/usr/local/sdsys\nUMASK=027\n")
            r = S.conf(f, good)
            got = open(f).read()
            S.check("C2 the key is present: replaced, one line, others in order",
                    "'# c', SDSYS, UMASK, then the new BACKUPDIR", r.returncode == 0
                    and got == "# c\nSDSYS=/usr/local/sdsys\nUMASK=027\nBACKUPDIR=%s\n" % good, "exit %d %r" % (r.returncode, got))

            f = conf_with("BACKUPDIR=/a\nUMASK=027\n  BACKUPDIR=/b\nBACKUPDIR=/c\n")
            r = S.conf(f, good)
            got = open(f).read()
            S.check("C3 duplicates (one indented) collapse to one line", "UMASK=027 then one BACKUPDIR=<dir>",
                    r.returncode == 0 and got == "UMASK=027\nBACKUPDIR=%s\n" % good, "exit %d %r" % (r.returncode, got))

            keep = "# BACKUPDIR=/in/a/comment\nBACKUPDIRX=1\nMYBACKUPDIR=/z\n"
            f = conf_with(keep)
            r = S.conf(f, good)
            got = open(f).read()
            S.check("C4 a comment, BACKUPDIRX= and MYBACKUPDIR= are NOT the key and are kept", "keep + the new line",
                    r.returncode == 0 and got == keep + "BACKUPDIR=%s\n" % good, "exit %d %r" % (r.returncode, got))

            f = conf_with("UMASK=027")      # no trailing newline
            r = S.conf(f, good)
            got = open(f).read()
            S.check("C5 a last line with no newline is kept and the new line starts on its own line",
                    "UMASK=027\\nBACKUPDIR=<dir>\\n", r.returncode == 0 and got == "UMASK=027\nBACKUPDIR=%s\n" % good, "exit %d %r" % (r.returncode, got))

            f = conf_with("")
            r = S.conf(f, good)
            got = open(f).read()
            S.check("C6 an empty file gets just the line", "BACKUPDIR=<dir>\\n", r.returncode == 0 and got == "BACKUPDIR=%s\n" % good, "exit %d %r" % (r.returncode, got))

            for mode in (0o644, 0o600, 0o640):
                f = conf_with(base, mode)
                r = S.conf(f, good)
                m = stat.S_IMODE(os.stat(f).st_mode)
                S.check("C7 the file's mode %s is kept" % oct(mode), "same mode after the rewrite", r.returncode == 0 and m == mode,
                        "exit %d mode %s" % (r.returncode, oct(m)))
            left = [n for n in os.listdir(tmp) if n.startswith("sd.conf.")]
            S.check("C8 no temporary file is left beside it", "none", not left, left)

            real = conf_with(base)
            link = os.path.join(tmp, "link.conf")
            if os.path.lexists(link):
                os.unlink(link)
            os.symlink(real, link)
            r = S.conf(link, good)
            S.check("C9 a symlink is refused and the target is untouched", "exit 2 'not a regular file', target unchanged",
                    r.returncode == 2 and "not a regular file" in r.stderr and open(real).read() == base,
                    "exit %d %s" % (r.returncode, r.stderr.strip()))

            r = S.conf(os.path.join(tmp, "absent.conf"), good)
            S.check("C10 a missing file is refused, and none is made", "exit 2 and no file", r.returncode == 2 and not os.path.exists(os.path.join(tmp, "absent.conf")),
                    "exit %d %s" % (r.returncode, r.stderr.strip()))


def selftest(code):
    mutants = [
        ("the character check is gone (a newline gets through)", "  [[ $p =~ $re ]] || die \"the directory path may hold only letters, digits and . _ @ + = , : / - and a space\"\n", ""),
        ("the .. check is gone", "*/./*|*/../*) die", "*/./*) die"),
        ("the existing-directory check is gone", "  [[ -d $p ]] || die", "  true || die"),
        ("the old BACKUPDIR line is not removed", "grep -v -E '^[[:space:]]*BACKUPDIR=' -- \"$f\"", "cat -- \"$f\""),
        ("the file's mode is not kept", "&& chmod --reference=\"$f\" -- \"$tmp\" ", ""),
        ("a symlink is followed", "[[ -f $f && ! -L $f ]]", "[[ -f $f ]]"),
    ]
    bad = 0
    for name, old, new in mutants:
        if code.count(old) != 1:
            print("REFUSED: mutant '%s' could not be applied (the text appears %d times)" % (name, code.count(old)), file=sys.stderr)
            sys.exit(2)
        s = Suite(code.replace(old, new))
        s.quiet = True
        with contextlib.redirect_stdout(io.StringIO()):
            s.suite()
        caught = s.failed > 0
        print("  mutant '%s': %s (%d of %d checks failed)" % (name, "CAUGHT" if caught else "NOT CAUGHT", s.failed, s.checks))
        bad += 0 if caught else 1
    print("selftest: %d mutants, %d not caught" % (len(mutants), bad))
    return 0 if bad == 0 else 1


def main(argv):
    code = cut_code(ELEVATE)
    print("test-bakdir-elevate-units inputs:")
    print("  sd-elevate : %s  (%d lines between '%s' and '%s')" % (ELEVATE, len(code.split("\n")), BEGIN, END))
    print("  bash       : %s" % subprocess.run(["bash", "--version"], capture_output=True, text=True).stdout.split("\n")[0])
    if "bakdir_checked" not in code or "conf_set_backupdir" not in code:
        print("REFUSED: the cut code does not define the two functions; nothing could be measured", file=sys.stderr)
        return 2
    if argv[1:] == ["--selftest"]:
        return selftest(code)
    if argv[1:]:
        print("usage: %s [--selftest]" % argv[0], file=sys.stderr)
        return 2
    s = Suite(code)
    s.suite()
    print("\n%d checks, %d failed" % (s.checks, s.failed))
    if s.checks == 0:
        print("REFUSED: no check ran", file=sys.stderr)
        return 2
    print("PASSED" if s.failed == 0 else "FAILED")
    return 0 if s.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
