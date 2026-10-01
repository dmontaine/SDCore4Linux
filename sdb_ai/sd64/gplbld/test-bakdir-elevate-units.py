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
import grp as grpmod
import os
import pwd
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

    def roots(self, f, uid):
        return self.bash("bakdir_roots %s %d" % (shlex.quote(f), uid))

    def plan(self, path, rootsfile, uid):
        return self.bash('bakdir_plan %s %s %d && printf "REAL=%%s REST=%%s\\n" "$BAK_REAL" "$BAK_REST"'
                         % (shlex.quote(path), shlex.quote(rootsfile), uid))

    def make(self, path, rootsfile, uid, owner, group):
        return self.bash('bakdir_plan %s %s %d && bakdir_make %s %s && printf "MADE=%%s\\n" "$BAK_MADE"'
                         % (shlex.quote(path), shlex.quote(rootsfile), uid, shlex.quote(owner), shlex.quote(group)))

    # bakdir-make: where ROOT may create a backup directory.  Everything runs as the person who
    # runs the test, so "root" and "sdsys" are played by that person (the owner and group come
    # in as arguments, and the roots file's owner is checked against this uid, not 0).
    def suite_make(self):
        S = self
        uid = os.getuid()
        me = pwd.getpwuid(uid).pw_name
        mygrp = grpmod.getgrgid(os.getgid()).gr_name
        with tempfile.TemporaryDirectory() as tmp0:
            tmp = os.path.realpath(tmp0)
            allowed, forbidden = os.path.join(tmp, "allowed"), os.path.join(tmp, "forbidden")
            os.mkdir(allowed)
            os.mkdir(forbidden)
            rf = os.path.join(tmp, "roots")

            def roots_file(text, mode=0o644):
                if os.path.lexists(rf):
                    os.unlink(rf)
                with open(rf, "w") as fh:
                    fh.write(text)
                os.chmod(rf, mode)
                return rf

            defaults = {os.path.realpath(p) for p in ("/media", "/run/media", "/mnt", "/var/backups", "/srv", "/opt", "/home/sdsys")}
            # ---- bakdir_roots
            r = S.roots(os.path.join(tmp, "no-such-file"), uid)
            got = set(r.stdout.split("\n")) - {""}
            S.check("R1 no list file: exactly the built-in places", "7 places incl. /var/backups /mnt /media /run/media",
                    r.returncode == 0 and got == defaults, "exit %d %s" % (r.returncode, sorted(got)))
            r = S.roots(roots_file("# a comment\n\n  %s  # trailing comment\n" % allowed), uid)
            got = set(r.stdout.split("\n")) - {""}
            S.check("R2 a list file adds its (canonical) places, comments and blanks ignored", "built-ins + %s" % allowed,
                    r.returncode == 0 and got == defaults | {allowed}, "exit %d %s" % (r.returncode, sorted(got - defaults)))
            r = S.roots(roots_file("%s\n" % allowed, 0o666), uid)
            S.check("R3 a list file anyone can write is refused", "exit 2 'writable by someone besides its owner'",
                    r.returncode == 2 and "writable by someone besides its owner" in r.stderr, "exit %d %s" % (r.returncode, r.stderr.strip()))
            r = S.roots(roots_file("%s\n" % allowed, 0o664), uid)
            S.check("R3b ... and one only its group can write", "exit 2", r.returncode == 2, "exit %d" % r.returncode)
            r = S.roots(roots_file("%s\n" % allowed), uid + 1)
            S.check("R4 a list file the wrong user owns is refused", "exit 2 'is not owned by'",
                    r.returncode == 2 and "is not owned by" in r.stderr, "exit %d %s" % (r.returncode, r.stderr.strip()))
            for name, line in (("R5 a root of / (the whole machine)", "/"), ("R5b a relative line", "relative/dir"),
                               ("R5c a .. line", "/a/../b"), ("R5d a trailing /", allowed + "/"),
                               ("R5e a quote", "/bad'quote"), ("R5f a . line (/. is /, the whole machine)", "/.")):
                r = S.roots(roots_file(line + "\n"), uid)
                S.check(name, "exit 2 'not a usable directory'", r.returncode == 2 and "not a usable directory" in r.stderr,
                        "exit %d %s" % (r.returncode, r.stderr.strip()))
            root_link = os.path.join(tmp, "rootlink")
            os.symlink("/", root_link)
            r = S.roots(roots_file(root_link + "\n"), uid)
            S.check("R5g a place that is a symlink to / is refused once resolved", "exit 2 'resolves to /'",
                    r.returncode == 2 and "resolves to /" in r.stderr, "exit %d %s" % (r.returncode, r.stderr.strip()))
            os.unlink(root_link)
            real_rf = roots_file("%s\n" % allowed)
            link_rf = os.path.join(tmp, "roots.link")
            os.symlink(real_rf, link_rf)
            r = S.roots(link_rf, uid)
            S.check("R6 a list file that is a symlink is refused", "exit 2 'not a regular file'",
                    r.returncode == 2 and "not a regular file" in r.stderr, "exit %d %s" % (r.returncode, r.stderr.strip()))
            os.unlink(link_rf)

            # ---- bakdir_plan: is this path below a place root may make things in
            roots_file("%s\n" % allowed)
            nested = os.path.join(allowed, "a", "b", "c")
            r = S.plan(nested, rf, uid)
            S.check("P1 a path below an allowed place: planned from its deepest existing directory",
                    "REAL=%s REST=/a/b/c" % allowed, r.returncode == 0 and r.stdout.strip() == "REAL=%s REST=/a/b/c" % allowed,
                    "exit %d %s %s" % (r.returncode, r.stdout.strip(), r.stderr.strip()))
            r = S.plan(os.path.join(forbidden, "x"), rf, uid)
            S.check("P2 a path outside every allowed place is refused", "exit 2 'is not below a place'",
                    r.returncode == 2 and "is not below a place" in r.stderr, "exit %d %s" % (r.returncode, r.stderr.strip()[:150]))
            r = S.plan(allowed, rf, uid)
            S.check("P3 a directory that already exists is not made again", "exit 2 'already exists'",
                    r.returncode == 2 and "already exists" in r.stderr, "exit %d %s" % (r.returncode, r.stderr.strip()))
            link = os.path.join(allowed, "escape")
            os.symlink(forbidden, link)
            r = S.plan(os.path.join(link, "new"), rf, uid)
            S.check("P4 a symlink inside an allowed place that leads OUT of it does not smuggle the path in",
                    "exit 2 'is not below a place' (the link is resolved first)",
                    r.returncode == 2 and "is not below a place" in r.stderr, "exit %d %s" % (r.returncode, r.stderr.strip()[:150]))
            dang = os.path.join(allowed, "dangling")
            os.symlink(os.path.join(tmp, "does-not-exist"), dang)
            r = S.plan(os.path.join(dang, "x"), rf, uid)
            S.check("P5 a dangling symlink in the path is refused", "exit 2 'dangling symlink'",
                    r.returncode == 2 and "dangling symlink" in r.stderr, "exit %d %s" % (r.returncode, r.stderr.strip()[:150]))
            ghost = os.path.join(tmp, "ghost")
            roots_file("%s\n" % ghost)
            r = S.plan(ghost, rf, uid)
            S.check("P6 the listed place ITSELF is not made (only things below it)", "exit 2 'is not below a place'",
                    r.returncode == 2 and "is not below a place" in r.stderr, "exit %d %s" % (r.returncode, r.stderr.strip()[:150]))
            roots_file("%s\n" % allowed)
            r = S.plan(allowed + "/../forbidden/x", rf, uid)
            S.check("P7 a .. path is refused before anything is looked at", "exit 2 'or .. path component'",
                    r.returncode == 2 and "or .. path component" in r.stderr, "exit %d %s" % (r.returncode, r.stderr.strip()[:150]))
            r = S.plan("relative/x", rf, uid)
            S.check("P8 a relative path is refused", "exit 2 'not a full path'",
                    r.returncode == 2 and "not a full path" in r.stderr, "exit %d %s" % (r.returncode, r.stderr.strip()[:150]))

            # ---- bakdir_make: what root makes
            r = S.make(nested, rf, uid, me, mygrp)
            ok = r.returncode == 0 and r.stdout.strip() == "MADE=%s" % nested
            modes = [stat.S_IMODE(os.stat(p).st_mode) for p in (os.path.join(allowed, "a"), os.path.join(allowed, "a", "b"), nested)]
            S.check("M1 the whole path is made; the directories on the way 0755, the last one 0700", "MADE=<path>, modes 755 755 700",
                    ok and modes == [0o755, 0o755, 0o700], "exit %d %s modes %s %s" % (r.returncode, r.stdout.strip(), [oct(m) for m in modes], r.stderr.strip()))
            st = os.stat(nested)
            S.check("M2 the last directory is owned by the owner and group it was given", "%s:%s" % (me, mygrp),
                    st.st_uid == uid and st.st_gid == os.getgid(), "uid %d gid %d" % (st.st_uid, st.st_gid))
            spaced = os.path.join(allowed, "my backups", "2026")
            r = S.make(spaced, rf, uid, me, mygrp)
            S.check("M3 a space inside a component is made as given", "MADE=<path>",
                    r.returncode == 0 and os.path.isdir(spaced) and r.stdout.strip() == "MADE=%s" % spaced, "exit %d %s" % (r.returncode, r.stderr.strip()))
            single = os.path.join(allowed, "x")
            r = S.make(single, rf, uid, me, mygrp)
            S.check("M4 one new component: 0700", "mode 700", r.returncode == 0 and stat.S_IMODE(os.stat(single).st_mode) == 0o700,
                    "exit %d %s" % (r.returncode, r.stderr.strip()))
            r = S.make(os.path.join(forbidden, "y"), rf, uid, me, mygrp)
            S.check("M5 outside the allowed places nothing is made", "exit 2 and no directory",
                    r.returncode == 2 and not os.path.exists(os.path.join(forbidden, "y")), "exit %d %s" % (r.returncode, r.stderr.strip()[:120]))
            r = S.make(os.path.join(link, "z"), rf, uid, me, mygrp)
            S.check("M6 through the escaping symlink nothing is made either", "exit 2 and no directory in the target",
                    r.returncode == 2 and not os.path.exists(os.path.join(forbidden, "z")), "exit %d %s" % (r.returncode, r.stderr.strip()[:120]))

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

        self.suite_make()


def selftest(code):
    mutants = [
        ("the character check is gone (a newline gets through)", "  [[ $p =~ $re ]] || die \"the directory path may hold only letters, digits and . _ @ + = , : / - and a space\"\n", ""),
        ("the .. check is gone", "*/./*|*/../*) die", "*/./*) die"),
        ("the existing-directory check is gone", "  [[ -d $1 ]] || die", "  true || die"),
        ("the allowed-places check is gone", "  [[ $ok -eq 1 ]] || die", "  true || die"),
        ("symlinks are not resolved before the test", "BAK_REAL=$(realpath -e -- \"$anc\") || die \"cannot resolve $anc\"", "BAK_REAL=$anc"),
        ("the last directory is made world-readable", "mkdir -m 0700 -- \"$cur\"", "mkdir -m 0755 -- \"$cur\""),
        ("the list file's mode is not checked", "  (( (8#$mode & 8#022) == 0 )) || die", "  true || die"),
        ("the list file's owner is not checked", "  [[ $(stat -c '%u' -- \"$f\") == \"$owner_uid\" ]] || die", "  true || die"),
        ("a listed place that resolves to / is accepted", "[[ $r != / ]] || die", "true || die"),
        ("a listed place is not validated as a path", "( bakdir_valid \"$line\" ) 2>/dev/null || die", "true || die"),
        ("a dangling symlink is stepped over", "    [[ ! -L $anc ]] || die \"$anc is a dangling symlink\"\n", ""),
        ("the listed place itself may be made", "[[ $target == \"$r\"/* ]] && ok=1", "[[ $target == \"$r\"/* || $target == \"$r\" ]] && ok=1"),
        ("the old BACKUPDIR line is not removed", "grep -v -E '^[[:space:]]*BACKUPDIR=' -- \"$f\"", "cat -- \"$f\""),
        ("the file's mode is not kept", "&& chmod --reference=\"$f\" -- \"$tmp\" ", ""),
        ("a symlink is followed", "  [[ -f $f && ! -L $f ]] || die \"$f is not a regular file\"\n  tmp=", "  [[ -f $f ]] || die \"$f is not a regular file\"\n  tmp="),
        ("a list file that is a symlink is read", "  [[ -f $f && ! -L $f ]] || die \"$f is not a regular file\"\n  [[ $(stat", "  [[ -f $f ]] || die \"$f is not a regular file\"\n  [[ $(stat"),
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
