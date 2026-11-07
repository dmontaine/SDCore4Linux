#!/usr/bin/env python3
# test-pathfix-units.py - S.159 (7 Nov 2026): the seven C defects of the Kimi review of Dev fae12324, held against the REAL routines.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-pathfix-units.py [--selftest]
#
# The routines are CUT OUT of the shipped sources by their signatures (delete_path, fullpath_n, make_path of op_dio2.c; sdrealpath of
# linuxlb.c; audit_rotate_file of audit_rot.c; sysdir of sdclilib.c), compiled with -fsanitize=address into one harness with stubs for
# what they call, and run on scratch files - so an overrun is a failed row, not a quiet pass:
#   1 delete_path() removes a symbolic link and never deletes under its target (the review's tree-link -> ../victim)
#   2 fullpath_n() copies only what fits: a 330-byte link target gives "" and FALSE, not 331 bytes in 256; a name that cannot be
#     resolved (a link loop) is kept as given
#   3 make_path() makes a 255-byte path (the "/" after its last part used to be written past the buffer) and refuses 256
#   4 audit_rotate_file() whose new trail cannot be made (its O_EXCL open made to fail) returns -1 and puts the old trail back
#   5 sysdir() of the client library passes over an 80-character section name and a header with no ']'
#   6 sdrealpath() reads a link's target as part of the path: it equals Python's os.path.realpath on a tree of links
#   7 delete_ak() (dh_ak.c) tests the index map with & after a range check - TEXT only (the runtime rows would need a hashed file)
# WHAT IT CANNOT SHOW: the routines inside a running SD (DELETE.ACCOUNT, OPENSEQ, the audit daemon, a client program); the targeted
# regression is that.  Exit 0 all rows passed (or every mutant killed), 1 a row failed (or a mutant survived), 2 it could not run
# (no gcc or no AddressSanitizer).  Fewer than 25 rows is a failure.

import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), "gplsrc")
FILES = ["op_dio2.c", "linuxlb.c", "audit_rot.c", "sdclilib.c", "dh_ak.c"]
MIN_ROWS = 25

SIGS = {
    "delete_path": ("op_dio2.c", "bool delete_path(char* path) {"),
    "fullpath_n": ("op_dio2.c", "bool fullpath_n(char* path,"),
    "make_path": ("op_dio2.c", "bool make_path(char* tgt) {"),
    "sdrealpath": ("linuxlb.c", "char* sdrealpath(char* inpath,"),
    "audit_rotate_file": ("audit_rot.c", "int audit_rotate_file(const char* path, long limit) {"),
    "sysdir": ("sdclilib.c", "Private char* sysdir() {"),
    "delete_ak": ("dh_ak.c", "Private bool delete_ak(char *pathname, /* File"),
}

PRELUDE = r'''
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <time.h>
#include <dirent.h>
#include <unistd.h>
#include <stdbool.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/ioctl.h>
#include <linux/fs.h>
#define TRUE 1
#define FALSE 0
#define Private static
#define THREAD_LOCAL __thread
#define DS '/'
#define DSS "/"
#define FOPEN_READ_MODE "r"
#define MAX_PATHNAME_LEN 255
#define MakeDirectory(path) mkdir(path, 0777)
#define UpperCase(c) ((char)toupper((unsigned char)(c)))
typedef unsigned char u_char;
static void k_error(const char* s) { fprintf(stderr, "k_error: %s\n", s); }
static struct { char sderror[512]; } session[1];
static int session_idx = 0;
static int fail_excl = 0;
static int test_open(const char* p, int flags, ...) {
  va_list ap; int mode = 0;
  va_start(ap, flags); if (flags & O_CREAT) mode = va_arg(ap, int); va_end(ap);
  if (fail_excl && (flags & O_EXCL)) { errno = EACCES; return -1; }
  return open(p, flags, mode);
}
char* sdrealpath(char* inpath, char* outpath);
'''

MAIN = r'''
int main(int argc, char** argv) {
  char out[PATH_MAX + 1];
  if (argc < 3) return 9;
  if (!strcmp(argv[1], "del")) { printf("ret=%d\n", (int)delete_path(argv[2])); return 0; }
  if (!strcmp(argv[1], "mk")) { printf("ret=%d\n", (int)make_path(argv[2])); return 0; }
  if (!strcmp(argv[1], "real")) { char* r = sdrealpath(argv[2], out); printf("out=[%s]\n", r ? r : "(NULL)"); return 0; }
  if (!strcmp(argv[1], "full")) {
    size_t n = (size_t)atoi(argv[3]);
    char* buf = malloc(n);                 /* exactly the caller's size: AddressSanitizer sees one byte past it */
    bool ok = fullpath_n(buf, argv[2], n);
    printf("ret=%d out=[%s]\n", (int)ok, buf); free(buf); return 0;
  }
  if (!strcmp(argv[1], "rot")) { fail_excl = atoi(argv[3]); printf("ret=%d\n", audit_rotate_file(argv[2], 10)); return 0; }
  if (!strcmp(argv[1], "sysdir")) { setenv("SD_CONFIG", argv[2], 1); char* r = sysdir(); printf("out=[%s]\n", r ? r : "(NULL)"); return 0; }
  return 9;
}
'''


def say(s=""):
    print(s, flush=True)


def cut(text, sig):
    """The function whose definition starts at sig, to its closing brace (comments, strings and char literals skipped)."""
    i = text.find(sig)
    if i < 0 or text.find(sig, i + 1) >= 0:
        return None
    j = text.index("{", i + len(sig) - 1 if sig.endswith("{") else i)
    depth, k, n = 0, j, len(text)
    while k < n:
        c = text[k]
        if text.startswith("/*", k):
            k = text.index("*/", k) + 2
            continue
        if text.startswith("//", k):
            k = text.index("\n", k)
            continue
        if c in "\"'":
            k += 1
            while text[k] != c:
                k += 2 if text[k] == "\\" else 1
            k += 1
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[i:k + 1]
        k += 1
    return None


def build(texts, tmp):
    parts = {}
    for name, (f, sig) in SIGS.items():
        if name == "delete_ak":
            continue
        body = cut(texts[f], sig)
        if body is None:
            return None, "could not cut %s out of %s" % (name, f)
        if name == "audit_rotate_file":
            body = re.sub(r"\bopen\(", "test_open(", body)
        parts[name] = body
    order = ["sdrealpath", "delete_path", "fullpath_n", "make_path", "audit_rotate_file", "sysdir"]
    src = PRELUDE + "\n".join(parts[o] for o in order) + MAIN
    c = os.path.join(tmp, "h.c")
    with open(c, "w") as fh:
        fh.write(src)
    exe = os.path.join(tmp, "h")
    p = subprocess.run(["gcc", "-std=gnu17", "-g", "-O1", "-fsanitize=address", "-fno-omit-frame-pointer", "-w", c, "-o", exe],
                       capture_output=True, text=True)
    if p.returncode != 0:
        return None, "compile failed: " + p.stderr[-1500:]
    return exe, ""


def run(exe, *args):
    env = dict(os.environ, ASAN_OPTIONS="detect_leaks=0:abort_on_error=0")
    p = subprocess.run([exe] + list(args), capture_output=True, text=True, env=env)
    asan = "AddressSanitizer" in p.stderr
    return p.returncode, p.stdout.strip(), asan, p.stderr


def rows_for(exe, texts, base):
    rows = []

    def row(label, ok, detail=""):
        rows.append((label, bool(ok), detail))

    # ---- 1 delete_path ----
    d1 = os.path.join(base, "d1")
    victim = os.path.join(d1, "victim")
    tree = os.path.join(d1, "del")
    os.makedirs(os.path.join(tree, "sub"))
    os.makedirs(victim)
    open(os.path.join(victim, "keep.txt"), "w").write("keep")
    open(os.path.join(tree, "f.txt"), "w").write("f")
    open(os.path.join(tree, "sub", "g"), "w").write("g")
    os.symlink("../victim", os.path.join(tree, "tree-link"))
    os.symlink("../nowhere", os.path.join(tree, "dangling"))
    rc, out, asan, err = run(exe, "del", tree)
    row("1a delete of a tree holding a link to a directory: ret=1  [del %s]" % tree, out == "ret=1" and not asan, out)
    row("1b the tree is gone", not os.path.lexists(tree))
    row("1c the link's TARGET keeps its file (victim/keep.txt)", os.path.isfile(os.path.join(victim, "keep.txt")))
    os.symlink("victim", os.path.join(d1, "lone-link"))
    rc, out, asan, err = run(exe, "del", os.path.join(d1, "lone-link"))
    row("1d delete of a link itself: ret=1, the link gone, the target whole",
        out == "ret=1" and not os.path.lexists(os.path.join(d1, "lone-link")) and os.path.isfile(os.path.join(victim, "keep.txt")), out)
    row("1e control: the review's case before the fix would have emptied victim - it still holds 1 file",
        os.listdir(victim) == ["keep.txt"], str(os.listdir(victim)))

    # ---- 2 fullpath_n ----
    d2 = os.path.join(base, "d2")
    os.makedirs(d2)
    long_target = "/" + "/".join(["x" * 32] * 10)  # 330 bytes in parts a filesystem allows (one 329-byte name is ENAMETOOLONG)
    os.symlink(long_target, os.path.join(d2, "l"))
    rc, out, asan, err = run(exe, "full", os.path.join(d2, "l"), "256")
    row("2a a short name through a 330-byte link target into 256 bytes: ret=0 out=[]  (no overrun)", out == "ret=0 out=[]" and not asan,
        out + (" ASAN" if asan else ""))
    rc, out, asan, err = run(exe, "full", os.path.join(d2, "l"), "400")
    row("2b the same into 400 bytes: ret=1 and the 330-byte target", out == "ret=1 out=[%s]" % long_target and not asan, out[:60])
    os.symlink("loop", os.path.join(d2, "loop"))
    # "./" in the name: the half-resolved buffer (what the old code copied) would read .../d2/loop, the name as given does not
    rc, out, asan, err = run(exe, "full", d2 + "/./loop", "256")
    row("2c a name that cannot be resolved (a link loop): ret=0 and the name as given, ./ and all",
        out == "ret=0 out=[%s/./loop]" % d2 and not asan, out)
    rc, out, asan, err = run(exe, "full", d2 + "/./x/..", "256")
    row("2d control: an ordinary name resolves: ret=1 out=[%s]" % os.path.realpath(d2), out == "ret=1 out=[%s]" % os.path.realpath(d2), out)

    # ---- 3 make_path ----
    d3 = os.path.realpath(os.path.join(base, "d3"))
    os.makedirs(d3)

    def path_of(total):
        p = d3
        while len(p) + 41 <= total:
            p += "/" + "a" * 40
        return p + "/" + "b" * (total - len(p) - 1)
    p255 = path_of(255)
    rc, out, asan, err = run(exe, "mk", p255)
    row("3a make_path of a 255-byte path: ret=1, no overrun  [len %d]" % len(p255), out == "ret=1" and not asan,
        out + (" ASAN" if asan else ""))
    row("3b the 255-byte directory exists", os.path.isdir(p255))
    p256 = path_of(256)
    rc, out, asan, err = run(exe, "mk", p256)
    row("3c a 256-byte path is refused: ret=0, no overrun", out == "ret=0" and not asan, out)
    rc, out, asan, err = run(exe, "mk", os.path.join(d3, "x", "y", "z"))
    row("3d control: a short path is made", out == "ret=1" and os.path.isdir(os.path.join(d3, "x", "y", "z")), out)

    # ---- 4 audit_rotate_file ----
    for tag, fail in (("4a", "1"), ("4b", "0")):
        d4 = os.path.join(base, "d4" + tag)
        os.makedirs(d4)
        trail = os.path.join(d4, "audit")
        open(trail, "w").write("line one of the old trail\n")
        os.chmod(trail, 0o640)
        rc, out, asan, err = run(exe, "rot", trail, fail)
        rotated = [f for f in os.listdir(d4) if f.startswith("audit.")]
        content = open(trail).read() if os.path.isfile(trail) else None
        if fail == "1":
            row("4a the new trail cannot be made: ret=-1 (was 1)  [rot %s fail_excl=1]" % trail, out == "ret=-1", out)
            row("4a the old trail is back under its name with its lines", content == "line one of the old trail\n", repr(content))
            row("4a no rotated file is left", rotated == [], str(rotated))
        else:
            row("4b control: a rotation that works: ret=1, an empty new trail, one rotated file",
                out == "ret=1" and content == "" and len(rotated) == 1, "%s %r %s" % (out, content, rotated))
            row("4b the new trail has the old one's mode (640)", oct(os.stat(trail).st_mode & 0o7777) == "0o640", oct(os.stat(trail).st_mode))

    # ---- 5 sysdir ----
    d5 = os.path.join(base, "d5")
    os.makedirs(d5)

    def conf(name, body):
        f = os.path.join(d5, name)
        open(f, "w").write(body)
        return f
    rc, out, asan, err = run(exe, "sysdir", conf("long", "[" + "s" * 80 + "]\nSDSYS=/wrong\n[sd]\nSDSYS=/right\n"))
    row("5a an 80-character section name: no overrun, and [sd] after it is read", out == "out=[/right]" and not asan,
        out + (" ASAN" if asan else ""))
    rc, out, asan, err = run(exe, "sysdir", conf("nobr", "[sd]\nX=1\n[sd\nSDSYS=/wrong\n[sd]\nSDSYS=/right\n"))
    row("5b a header with no ']' is no section: what follows it is not read as [sd]", out == "out=[/right]" and not asan, out)
    rc, out, asan, err = run(exe, "sysdir", conf("ok", "# c\n[sd]\nSDSYS=/usr/local/sdsys\n"))
    row("5c control: an ordinary file", out == "out=[/usr/local/sdsys]", out)
    rc, out, asan, err = run(exe, "sysdir", conf("exact", "[" + "q" * 49 + "]\nSDSYS=/wrong\n"))
    row("5d a 49-character name (the most section[50] holds) is a section, not [sd]: no SDSYS", out == "out=[(NULL)]" and not asan, out)

    # ---- 6 sdrealpath ----
    d6 = os.path.realpath(os.path.join(base, "d6"))
    for sub in ("a", "outside", "b/c"):
        os.makedirs(os.path.join(d6, sub))
    os.symlink("../outside", os.path.join(d6, "a", "link"))          # the review's case
    os.symlink("../b", os.path.join(d6, "outside", "l2"))            # a link inside a link's target
    os.symlink(os.path.join(d6, "b", "c"), os.path.join(d6, "abs"))  # absolute
    os.symlink("link", os.path.join(d6, "a", "chain"))               # a link to a link
    os.symlink("./../a/./link/../b", os.path.join(d6, "a", "dots"))  # . and .. inside a target
    cases = ["a/link", "a/link/l2", "a/link/l2/c", "a/link/../a", "abs", "abs/../c", "a/chain/l2", "a/dots",
             "a/link/new/../x", "a/link/l2/none/..", "outside/l2/c/..", "a/./link/./l2"]
    for i, rel in enumerate(cases):
        full = os.path.join(d6, rel)
        want = os.path.realpath(full)
        rc, out, asan, err = run(exe, "real", full)
        row("6%s sdrealpath(%s) equals realpath: %s" % (chr(97 + i), rel, want[len(d6):] or "/"), out == "out=[%s]" % want and not asan,
            out[len("out=["):][len(d6):] if out.startswith("out=[" + d6) else out)

    # ---- 7 delete_ak, text ----
    body = cut(texts["dh_ak.c"], SIGS["delete_ak"][1]) or ""
    row("7a delete_ak() is found in dh_ak.c", body != "")
    row("7b no logical && on the index map", re.search(r"ak_map\s*&&", body) is None)
    row("7c the test is bitwise: header.ak_map & (1u << akno)", "(header.ak_map & (1u << akno)) == 0" in body)
    row("7d the number is checked against MAX_INDICES before the shift",
        re.search(r"\(akno < 0\) \|\| \(akno >= MAX_INDICES\) \|\|", body) is not None)
    row("7e the bit is cleared (&= ~), not flipped (^=)", "header.ak_map &= ~(1u << akno);" in body and "ak_map ^=" not in body)
    row("7f the pragma that silenced -Wint-in-bool-context is gone", "Wint-in-bool-context" not in body)
    return rows


def run_all(texts, quiet=False):
    if shutil.which("gcc") is None:
        say("CANNOT RUN: no gcc")
        sys.exit(2)
    tmp = tempfile.mkdtemp(prefix="pathfix-")
    try:
        exe, why = build(texts, tmp)
        if exe is None:
            return None, why
        base = os.path.join(tmp, "w")
        os.makedirs(base)
        return rows_for(exe, texts, base), ""
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def read_texts():
    t = {}
    for f in FILES:
        with open(os.path.join(SRC, f), encoding="utf-8", errors="replace") as fh:
            t[f] = fh.read()
    return t


MUTANTS = [
    ("delete_path follows links again (stat)", "op_dio2.c", "if (lstat(path, &stat_buf) != 0)", "if (stat(path, &stat_buf) != 0)"),
    ("fullpath_n copies a result that does not fit", "op_dio2.c", "  if (n >= size) {\n    path[0] = '\\0';", "  if (0) {\n    path[0] = '\\0';"),
    ("fullpath_n copies the unset buffer on failure", "op_dio2.c", "    if (path != name) {\n      n = strlen(name);",
     "    if (path != name) {\n      strcpy(path, buff); return FALSE;\n      n = strlen(name);"),
    ("make_path appends the / with no room", "op_dio2.c", "    if (strlen(new_path) + 1 > MAX_PATHNAME_LEN)", "    if (0)"),
    ("make_path takes a name of any length", "op_dio2.c", "  if (strlen(tgt) > MAX_PATHNAME_LEN)\n    return FALSE;", ""),
    ("sdrealpath ignores the spliced target", "linuxlb.c", "        p = pending;\n        continue;", "        p = q;\n        continue;"),
    ("rotation reports success when the new trail fails", "audit_rot.c", "          } else {\n            result = -1;", "          } else {\n            result = 1;"),
    ("rotation does not put the trail back", "audit_rot.c", "              (void)rename(rotated, path);", "              ;"),
    ("sysdir copies a section of any length", "sdclilib.c", "if ((p == NULL) || ((size_t)(p - (rec + 1)) >= sizeof(section))) {",
     "if (p == NULL) {"),
    ("delete_ak uses && again", "dh_ak.c", "((header.ak_map & (1u << akno)) == 0)", "((header.ak_map && (1u << akno)) == 0)"),
    ("delete_ak flips the bit", "dh_ak.c", "header.ak_map &= ~(1u << akno);", "header.ak_map ^= (1u << akno);"),
    ("delete_ak loses the range check", "dh_ak.c", "(akno < 0) || (akno >= MAX_INDICES) || ", ""),
]


def main():
    texts = read_texts()
    for f in FILES:
        say("source: %s (%d bytes)" % (os.path.join(SRC, f), len(texts[f])))
    if "--selftest" in sys.argv[1:]:
        missed = 0
        for label, f, old, new in MUTANTS:
            if texts[f].count(old) != 1:
                say("MUTANT CANNOT APPLY (%s): the text is in %s %d times" % (label, f, texts[f].count(old)))
                missed += 1
                continue
            mt = dict(texts)
            mt[f] = texts[f].replace(old, new)
            rows, why = run_all(mt)
            if rows is None:
                say("killed (build): %s" % label)
                continue
            failed = [r[0] for r in rows if not r[1]]
            if failed:
                say("killed: %-50s by %d row(s): %s" % (label, len(failed), failed[0]))
            else:
                say("SURVIVED: %s" % label)
                missed += 1
        say("\nselftest: %d mutants, %d killed, %d missed" % (len(MUTANTS), len(MUTANTS) - missed, missed))
        sys.exit(1 if missed else 0)

    rows, why = run_all(texts)
    if rows is None:
        say("CANNOT RUN: " + why)
        sys.exit(2)
    bad = 0
    for label, ok, detail in rows:
        say("%s  %s%s" % ("PASS" if ok else "FAIL", label, "" if ok or not detail else "   [" + detail + "]"))
        bad += 0 if ok else 1
    short = len(rows) < MIN_ROWS
    if short:
        say("FAIL  only %d rows ran (fewer than %d)" % (len(rows), MIN_ROWS))
    say("\n%d passed, %d failed" % (len(rows) - bad, bad + (1 if short else 0)))
    sys.exit(1 if bad or short else 0)


if __name__ == "__main__":
    main()
