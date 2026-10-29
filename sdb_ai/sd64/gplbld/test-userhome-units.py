#!/usr/bin/env python3
"""test-userhome-units.py - SDEXT SD_USER_HOME (112): op_sdext.c user_home_dir(), the test the editors' recovery store makes of the person's home and the
directories below it (28 Oct 2026, the store moved to the person's Linux home on the owner's approval of that day).

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-userhome-units.py
  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-userhome-units.py --selftest

No sudo, no install, no sd.  Exit 0 every check passed, 1 a check failed, 2 it could not run (no C compiler, the function not found, a compile error).

START-HISTORY:
28 Oct 26 dm  New with SD_USER_HOME.
END-HISTORY

WHAT IT DOES.  It CUTS user_home_dir() out of gplsrc/op_sdext.c (from its signature to the closing brace at the start of a line), compiles it with a small
main() in which geteuid() and getpwuid_r() are stand-ins (the effective uid and the password database's home come from the environment: a test cannot be
another user or edit /etc/passwd), and RUNS it against scratch directories it makes with the modes each row needs.  Everything else - realpath, stat, lstat,
the owner and mode tests - is the real C library on the real disk.  Each row prints the inputs it used (the home, the relative path, the uid) and the answer.

  the trusted answers:  a 0755 or 0700 home of the uid, with '' and with a path of 0700 and 0755 directories below it; a home that is a link to such a
                        directory (realpath: the answer is the resolved path)
  the refusals:         uid 0; no password entry; a relative home; a home somebody else owns; a home group or other can write; a missing directory; a
                        directory group or other can write; a link on the way; a file on the way; an empty word, '.', '..', a leading or a trailing slash

THE NULL CASE IS REFUSED: the cut must be found and must hold the getpwuid_r call, and every row must have run (a row whose program printed nothing fails).
--selftest makes each mutation of the C text (it must match once), compiles it and requires a row to fail.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.dirname(HERE)
SRC = os.path.join(SD64, "gplsrc", "op_sdext.c")
KEYS_C = os.path.join(SD64, "gplsrc", "keys.h")
KEYS_B = os.path.join(SD64, "sdsys", "syscom", "keys.h")

MAIN = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
#include <pwd.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
#define Private static

/* the stand-ins: the uid and the home the password database would give */
static uid_t fake_geteuid(void) { return (uid_t)atol(getenv("UH_UID")); }
static int fake_getpwuid_r(uid_t uid, struct passwd* pw, char* buf, size_t n, struct passwd** res) {
  const char* h = getenv("UH_HOME");
  (void)uid;
  if (h == NULL || strcmp(h, "-") == 0) { *res = NULL; return 0; }
  if (strlen(h) + 1 > n) { *res = NULL; return 34; }
  strcpy(buf, h);
  memset(pw, 0, sizeof(*pw));
  pw->pw_dir = buf;
  *res = pw;
  return 0;
}
#define geteuid fake_geteuid
#define getpwuid_r fake_getpwuid_r

@FUNCTION@

int main(int argc, char** argv) {
  char out[PATH_MAX + 1];
  int ok;
  (void)argc;
  ok = user_home_dir(argv[1], out, sizeof(out));
  printf("answer=%d path=[%s]\n", ok, out);
  return 0;
}
'''


def cut(src):
    m = re.search(r"^Private int user_home_dir\(const char\* rel, char\* out, size_t out_sz\) \{\n.*?^\}\n", src, re.M | re.S)
    return m.group(0) if m else ""


def build(cc, tmp, func, tag):
    c = os.path.join(tmp, "uh_%s.c" % tag)
    exe = os.path.join(tmp, "uh_%s" % tag)
    with open(c, "w") as f:
        f.write(MAIN.replace("@FUNCTION@", func))
    r = subprocess.run([cc, "-std=gnu17", "-Wall", "-o", exe, c], capture_output=True, text=True)
    if r.returncode != 0:
        return None, r.stderr
    return exe, r.stderr


def scenario(tmp):
    """the scratch tree; returns (rows) of (name, home, rel, uid, expect_ok, expect_path)"""
    me = os.geteuid()
    other = me + 1 if me + 1 != 0 else me + 2
    b = os.path.join(tmp, "t")
    os.mkdir(b)

    def d(path, mode):
        os.makedirs(path, exist_ok=True)
        os.chmod(path, mode)
        return path

    good = d(os.path.join(b, "home"), 0o755)
    d(os.path.join(good, ".local"), 0o755)
    d(os.path.join(good, ".local", "state"), 0o700)
    d(os.path.join(good, ".local", "state", "sd"), 0o700)
    d(os.path.join(good, "gw"), 0o775)
    d(os.path.join(good, "ow"), 0o757)
    d(os.path.join(good, "gw", "x"), 0o700)
    os.symlink(os.path.join(good, ".local"), os.path.join(good, "lnk"))
    with open(os.path.join(good, "afile"), "w") as f:
        f.write("x")
    gwhome = d(os.path.join(b, "gwhome"), 0o775)
    owhome = d(os.path.join(b, "owhome"), 0o757)
    home700 = d(os.path.join(b, "home700"), 0o700)
    os.symlink(good, os.path.join(b, "homelink"))
    rgood = os.path.realpath(good)
    rows = [
        ("T1 a 0755 home of the uid, '' -> the home", good, "", me, 1, rgood),
        ("T2 a 0700 home -> the home", home700, "", me, 1, os.path.realpath(home700)),
        ("T3 0755 then 0700 directories below -> the path", good, ".local/state/sd", me, 1, rgood + "/.local/state/sd"),
        ("T4 a home that is a link -> the resolved home and path below", os.path.join(b, "homelink"), ".local/state", me, 1, rgood + "/.local/state"),
        ("F1 uid 0 is refused", good, "", 0, 0, ""),
        ("F2 no password entry", "-", "", me, 0, ""),
        ("F3 a relative home (one that exists from where the program runs)", "home", "", me, 0, ""),
        ("F4 a home somebody else owns (another uid)", good, "", other, 0, ""),
        ("F5 a home group can write", gwhome, "", me, 0, ""),
        ("F6 a home other can write", owhome, "", me, 0, ""),
        ("F7 a missing directory below", good, ".local/state/none", me, 0, ""),
        ("F8 a directory group can write on the way", good, "gw/x", me, 0, ""),
        ("F9 the last directory other can write", good, "ow", me, 0, ""),
        ("F10 a link on the way (to a good directory)", good, "lnk/state", me, 0, ""),
        ("F11 a file on the way", good, "afile", me, 0, ""),
        ("F12 '..'", good, ".local/..", me, 0, ""),
        ("F13 '.'", good, "./.local", me, 0, ""),
        ("F14 an empty word", good, ".local//state", me, 0, ""),
        ("F15 a leading slash", good, "/.local", me, 0, ""),
        ("F16 a trailing slash", good, ".local/", me, 0, ""),
    ]
    return rows


def run_rows(exe, rows, quiet=False):
    bad = 0
    ran = 0
    for name, home, rel, uid, want_ok, want_path in rows:
        env = dict(os.environ, UH_UID=str(uid), UH_HOME=home)
        r = subprocess.run([exe, rel], capture_output=True, text=True, env=env, cwd=os.path.join(os.path.dirname(exe), "t"))
        m = re.match(r"answer=(\d) path=\[(.*)\]$", r.stdout.strip())
        if m is None:
            ok = False
            got = "NO ANSWER: %r %r" % (r.stdout[:80], r.stderr[:80])
        else:
            ran += 1
            got_ok, got_path = int(m.group(1)), m.group(2)
            ok = (got_ok == want_ok and got_path == want_path)
            got = "answer %d path %r" % (got_ok, got_path)
        bad += 0 if ok else 1
        if not quiet:
            print("  [%s] %s   (home %r, rel %r, uid %d) -> %s%s" % ("PASS" if ok else "FAIL", name, home, rel, uid, got,
                                                                   "" if ok else "   <- wanted %d %r" % (want_ok, want_path)))
    return bad, ran


# (name, old, new): a mutation of the function's text; each must match once and fail a row
MUTANTS = [
    ("root is let through", "  if (me == 0)\n    return 0;\n", ""),
    ("the home may be group-writable", "(st.st_uid != me) || ((st.st_mode & 022) != 0))\n    return 0;\n\n  len", "(st.st_uid != me))\n    return 0;\n\n  len"),
    ("the home's owner is not asked", "!S_ISDIR(st.st_mode) || (st.st_uid != me) || ((st.st_mode & 022) != 0))\n    return 0;\n\n  len", "!S_ISDIR(st.st_mode) || ((st.st_mode & 022) != 0))\n    return 0;\n\n  len"),
    ("a relative home is taken", "(pw->pw_dir[0] != '/')", "(pw->pw_dir[0] == '\\0')"),
    ("a link on the way is followed", "if ((lstat(work, &st) != 0)", "if ((stat(work, &st) != 0)"),
    ("'..' is taken", "((e - p == 2) && (p[0] == '.') && (p[1] == '.'))", "0"),
    ("a directory below may be group-writable", "(st.st_uid != me) || ((st.st_mode & 022) != 0))\n      return 0;\n    if ((*e == '/')", "(st.st_uid != me))\n      return 0;\n    if ((*e == '/')"),
    ("a trailing slash is taken", "    if ((*e == '/') && (e[1] == '\\0'))\n      return 0; /* a trailing slash */\n", ""),
]


def text_checks(src, kc, kb):
    rows = []
    sw = src[src.find("case SD_USER_HOME: {"):]
    sw = sw[: sw.find("break;\n    }") + 1]
    rows.append(("K1 keys.h (C) and syscom/keys.h (BASIC) define SD_USER_HOME as 112, and nothing else in either has 112",
                 re.search(r"#define SD_USER_HOME\s+112\b", kc) is not None and re.search(r"\$define SD_USER_HOME\s+112\b", kb) is not None
                 and len(re.findall(r"define\s+SD_\w+\s+112\b", kc)) == 1 and len(re.findall(r"define\s+SD_\w+\s+112\b", kb)) == 1))
    rows.append(("K2 the SDEXT case takes exactly one argument (more sets process.status), answers '' unless user_home_dir trusts the path",
                 "if (argCnt != 1)" in sw and "process.status = SD_EXT_ARG_CNT;" in sw and "user_home_dir(SDMEArgArray[0], home_out, sizeof(home_out))" in sw
                 and "home_out[0] = '\\0';" in sw))
    fn = cut(src)
    rows.append(("K3 the home is the password database's (getpwuid_r of the EFFECTIVE uid) and never $HOME: no getenv in the function or the case",
                 "getpwuid_r(me, &pwbuf, pwstrings, sizeof(pwstrings), &pw)" in fn and "me = geteuid();" in fn and "getenv" not in fn and "getenv" not in sw
                 and "HOME" not in fn))
    rows.append(("K4 an effective uid of 0 is refused before anything is looked up (no row can show it: an ordinary user cannot make a root-owned home)",
                 re.search(r"me = geteuid\(\);\n  if \(me == 0\)\n    return 0;\n  if \(\(getpwuid_r", fn) is not None))
    return rows


def main(argv):
    cc = shutil.which("cc") or shutil.which("gcc")
    try:
        with open(SRC, encoding="latin-1") as f:
            src = f.read()
        with open(KEYS_C, encoding="latin-1") as f:
            kc = f.read()
        with open(KEYS_B, encoding="latin-1") as f:
            kb = f.read()
    except OSError as exc:
        print("test-userhome-units: CANNOT RUN - %s" % exc)
        return 2
    func = cut(src)
    if cc is None or "getpwuid_r" not in func:
        print("test-userhome-units: CANNOT RUN - %s" % ("no C compiler" if cc is None else "user_home_dir() was not found in %s" % SRC))
        return 2
    print("test-userhome-units: %s, the function cut from %s (%d characters), compiler %s, effective uid %d" % (SRC, SRC, len(func), cc, os.geteuid()))
    if os.geteuid() == 0:
        print("test-userhome-units: CANNOT RUN - as root every directory is root's and the uid-0 refusal hides the rest; run it as an ordinary user")
        return 2
    bad = 0
    for name, ok in text_checks(src, kc, kb):
        print("  [%s] %s" % ("PASS" if ok else "FAIL", name))
        bad += 0 if ok else 1
    tmp = tempfile.mkdtemp(prefix="userhome-")
    try:
        exe, err = build(cc, tmp, func, "real")
        if exe is None:
            print("test-userhome-units: CANNOT RUN - the cut did not compile:\n%s" % err)
            return 2
        rows = scenario(tmp)
        b, ran = run_rows(exe, rows)
        bad += b
        if ran != len(rows):
            print("  [FAIL] NULL CASE: %d of %d rows produced an answer" % (ran, len(rows)))
            bad += 1
        print("\ntest-userhome-units: %d rows and %d text checks, %d failed" % (len(rows), len(text_checks(src, kc, kb)), bad))
        rc = 1 if bad else 0
        if "--selftest" in argv:
            if bad:
                print("selftest: the unchanged function fails, so a mutant's failure cannot be told from it")
                return 1
            holes = 0
            for i, (name, old, new) in enumerate(MUTANTS):
                if func.count(old) != 1:
                    print("  [FAIL] selftest: %s - the text matches %d times, not once" % (name, func.count(old)))
                    holes += 1
                    continue
                mexe, merr = build(cc, tmp, func.replace(old, new), "m%d" % i)
                if mexe is None:
                    print("  [FAIL] selftest: %s - the mutant did not compile: %s" % (name, merr[:200]))
                    holes += 1
                    continue
                mb, _ = run_rows(mexe, rows, quiet=True)
                mb += sum(1 for _, ok in text_checks(src.replace(old, new), kc, kb) if not ok)      # a refusal no row can reach as an ordinary user (uid 0)
                print("  [%s] selftest: %s - %d row(s) failed" % ("PASS" if mb else "FAIL", name, mb))
                holes += 0 if mb else 1
            print("selftest: %d mutants, %d not caught" % (len(MUTANTS), holes))
            rc = 1 if holes else rc
        return rc
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
