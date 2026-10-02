#!/usr/bin/env python3
"""test-accarchive-units.py - gplbld/sd-accarchive, the archive step of S.50.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-accarchive-units.py
  python3 .../test-accarchive-units.py --selftest     each mutant must go red

No sudo, no install, no sd.  Exit 0 every row passed, 1 a row failed, 2 it
could not run.  Written 01 Oct 26 for S.50 (BACKUP.ACCOUNT / RESTORE.ACCOUNT).

WHAT IT MEASURES.  The tool runs as root for pack, so its refusals are the
security boundary; the format is agreed with SD Core for Windows, so its
round trip is the interop contract.  Every row runs the REAL tool in a scratch
directory and prints the command line and what came back:

  ALLOW rows  - pack/count agree; an empty directory, a case-only pair and a
                binary file survive a round trip byte for byte; a zip written
                the way the Windows tool writes one (no extra fields, stored
                directory entries, a non-Unix create_system) extracts.
  REFUSE rows - every extract refusal in the tool's header, each on an
                archive that differs from a good one in that one respect, and
                pack's argument refusals.  A refusal must name its reason: a
                row matches the reason text, never just a non-zero exit.
  SYMLINK row - a symlink to a file outside the tree is skipped and named,
                and its target's content is nowhere in the zip.

THE NULL CASE IS REFUSED.  If either half has no rows, or the tool is missing,
the run exits 2 rather than reporting 0 of 0.  --selftest builds mutant copies
of the tool (the '..' check gone, symlinks followed, the existing-target check
gone, the manifest requirement gone) and requires each to fail at least one row.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sd-accarchive")

RESULTS = {"pass": 0, "fail": 0, "allow": 0, "refuse": 0}


def say(s=""):
    print(s)
    sys.stdout.flush()


def run(tool, args, stdin=b""):
    cmd = [sys.executable, tool] + args
    p = subprocess.run(cmd, input=stdin, capture_output=True)
    return p.returncode, p.stdout, p.stderr.decode("utf-8", "replace"), cmd


def row(kind, name, ok, detail):
    RESULTS[kind] += 1
    RESULTS["pass" if ok else "fail"] += 1
    say("  [%s] %-6s %s" % ("PASS" if ok else "FAIL", kind.upper(), name))
    for line in detail:
        say("         | " + line)


def make_tree(top):
    os.makedirs(os.path.join(top, "bp"))
    os.makedirs(os.path.join(top, "empty"))
    os.makedirs(os.path.join(top, "voc"))
    with open(os.path.join(top, "bp", "MyProg"), "wb") as f:
        f.write(b"crt 'upper'\n")
    with open(os.path.join(top, "bp", "myprog"), "wb") as f:
        f.write(b"crt 'lower'\n")
    with open(os.path.join(top, "voc", "%0"), "wb") as f:
        f.write(bytes(range(256)) * 300)


def counts_of(stderr_or_out):
    out = {}
    for line in stderr_or_out.splitlines():
        p = line.split()
        if len(p) == 5 and p[0] == "COUNT":
            out[p[1]] = tuple(int(x) for x in p[2:])
    return out


def good_zip(path, entries):
    """Write a zip by hand.  entries: [(name, data or None for a directory)]."""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries:
            zi = zipfile.ZipInfo(name)
            zi.create_system = 0          # as the Windows tool writes it
            if data is None:
                zi.compress_type = zipfile.ZIP_STORED
                zf.writestr(zi, b"")
            else:
                zi.compress_type = zipfile.ZIP_DEFLATED
                zf.writestr(zi, data)


BASE = [("manifest.txt", b"format: 1\n"), ("accounts/zz/", None), ("accounts/zz/bp/", None),
        ("accounts/zz/bp/a", b"A")]


def symlink_zip(path):
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("manifest.txt", b"format: 1\n")
        zi = zipfile.ZipInfo("accounts/zz/link")
        zi.create_system = 3
        zi.external_attr = (0o120777) << 16
        zf.writestr(zi, b"/etc/passwd")


def suite(tool, work):
    # ---------------------------------------------------------------- ALLOW
    src = os.path.join(work, "src")
    make_tree(src)
    rc, out, err, cmd = run(tool, ["count", src])
    cnt = counts_of(out.decode())
    rc2, zbytes, err2, cmd2 = run(tool, ["pack", "zz=" + src], b"format: 1\n")
    pk = counts_of(err2)
    zpath = os.path.join(work, "t.zip")
    with open(zpath, "wb") as f:
        f.write(zbytes)
    row("allow", "pack and count report the same files/bytes/dirs",
        rc == 0 and rc2 == 0 and cnt.get(".") == pk.get("zz") == (3, 24 + 76800, 3),
        ["$ " + " ".join(cmd), "  -> exit %d %s" % (rc, cnt), "$ " + " ".join(cmd2),
         "  -> exit %d %s" % (rc2, pk), "  expected (3, %d, 3) from both" % (24 + 76800)])

    names = []
    if rc2 == 0:
        with zipfile.ZipFile(zpath) as zf:
            names = [(i.filename, i.compress_type, i.file_size) for i in zf.infolist()]
    dirs_ok = ("accounts/zz/empty/", 0, 0) in names and ("accounts/zz/", 0, 0) in names
    row("allow", "every directory has a stored, empty 'name/' entry (the empty one too)",
        dirs_ok and names[:1] and names[0][0] == "manifest.txt",
        ["entries: %s" % [n[0] for n in names]])

    out_dir = os.path.join(work, "out")
    rc, out, err, cmd = run(tool, ["extract", zpath, out_dir])
    ex = counts_of(out.decode())
    same = True
    for rel in ("bp/MyProg", "bp/myprog", "voc/%0"):
        a = os.path.join(src, rel)
        b = os.path.join(out_dir, "accounts", "zz", rel)
        if not os.path.isfile(b) or open(a, "rb").read() != open(b, "rb").read():
            same = False
    row("allow", "round trip: case-only pair, binary file and empty directory come back",
        rc == 0 and same and os.path.isdir(os.path.join(out_dir, "accounts", "zz", "empty"))
        and ex.get("zz") == pk.get("zz"),
        ["$ " + " ".join(cmd), "  -> exit %d %s (pack said %s); bytes equal: %s" % (rc, ex, pk.get("zz"), same)])

    # Directory modes.  pack stores each directory's mode; extract must apply it, or a restore
    # turns an account's 0700 directories into 0775 (measured on a real Solo, 2 Oct 2026: the
    # extractor created every directory 0775 under umask 002 and never read the archived mode).
    msrc = os.path.join(work, "msrc")
    want_modes = {"": 0o700, "priv": 0o700, "shared": 0o750, "ro": 0o700}   # "ro" is stored 0500: the owner keeps rwx
    for rel in ("priv", "shared", "ro"):
        os.makedirs(os.path.join(msrc, rel))
    for rel, perm in (("priv", 0o700), ("shared", 0o750), ("ro", 0o500), ("", 0o700)):
        os.chmod(os.path.join(msrc, rel), perm)
    rc, zb, err, cmd = run(tool, ["pack", "zz=" + msrc], b"format: 1\n")
    mzip = os.path.join(work, "modes.zip")
    with open(mzip, "wb") as f:
        f.write(zb)
    mout = os.path.join(work, "modesout")
    rc2, out2, err2, cmd2 = run(tool, ["extract", mzip, mout])

    def mode_of(rel):
        try:
            return os.stat(os.path.join(mout, "accounts", "zz", rel)).st_mode & 0o777
        except OSError:
            return None
    got = {rel: mode_of(rel) for rel in want_modes}
    stored = {}                 # read back out of the zip itself, so a pack that stored nothing cannot pass
    if rc == 0:
        with zipfile.ZipFile(mzip) as zf:
            for zi in zf.infolist():
                if zi.filename.startswith("accounts/zz") and zi.is_dir():
                    stored[zi.filename[len("accounts/zz/"):].rstrip("/")] = (zi.external_attr >> 16) & 0o777
    want_stored = {"": 0o700, "priv": 0o700, "shared": 0o750, "ro": 0o500}
    row("allow", "extract applies each archived directory mode (0700 stays 0700, 0750 stays 0750, 0500 becomes 0700)",
        rc == 0 and rc2 == 0 and stored == want_stored and got == want_modes,
        ["$ " + " ".join(cmd), "$ " + " ".join(cmd2),
         "  stored in the zip:      %s" % {rel: oct(p) for rel, p in sorted(stored.items())},
         "  expected after extract: %s" % {rel: oct(p) for rel, p in want_modes.items()},
         "  got after extract:      %s" % {rel: (oct(p) if p is not None else None) for rel, p in got.items()}])
    os.chmod(os.path.join(msrc, "ro"), 0o700)

    win = os.path.join(work, "win.zip")
    good_zip(win, BASE + [("accounts/zz/empty/", None)])
    wout = os.path.join(work, "wout")
    rc, out, err, cmd = run(tool, ["extract", win, wout])
    f_a = os.path.join(wout, "accounts", "zz", "bp", "a")
    row("allow", "a zip written the Windows way (create_system 0, no extras) extracts",
        rc == 0 and os.path.isfile(f_a) and counts_of(out.decode()).get("zz") == (1, 1, 2),
        ["$ " + " ".join(cmd), "  -> exit %d out=%r err=%r" % (rc, out.decode().strip(), err.strip())])

    # -------------------------------------------------------------- SYMLINK
    lsrc = os.path.join(work, "lsrc")
    os.makedirs(lsrc)
    secret = os.path.join(work, "secret.txt")
    with open(secret, "wb") as f:
        f.write(b"SECRET-CONTENT-12345")
    os.symlink(secret, os.path.join(lsrc, "evil"))
    with open(os.path.join(lsrc, "ok"), "wb") as f:
        f.write(b"ok")
    rc, zb, err, cmd = run(tool, ["pack", "zz=" + lsrc], b"format: 1\n")
    row("refuse", "a symlink is skipped and named, and its target is not in the zip",
        rc == 0 and "SKIPPED zz/evil (symlink)" in err and b"SECRET-CONTENT-12345" not in zb
        and b"accounts/zz/evil" not in zb,
        ["$ " + " ".join(cmd), "  -> exit %d, stderr %r, secret in zip: %s"
         % (rc, err.strip(), b"SECRET-CONTENT-12345" in zb)])

    # --------------------------------------------------------------- REFUSE
    cases = [
        ("no manifest.txt", [e for e in BASE if e[0] != "manifest.txt"], "has no manifest.txt"),
        ("a '..' segment", BASE + [("accounts/zz/../../x", b"x")], "'..' segment"),
        ("an absolute name", BASE + [("/accounts/zz/x", b"x")], "absolute path"),
        ("a backslash", BASE + [("accounts/zz/a\\b", b"x")], "backslash"),
        ("a control character", BASE + [("accounts/zz/a\x01b", b"x")], "control character"),
        ("outside accounts/", BASE + [("etc/passwd", b"x")], "outside manifest.txt and accounts/"),
        ("an upper-case account name", BASE + [("accounts/ZZ/a", b"x")], "not a lower-case SD account name"),
        ("an empty segment", BASE + [("accounts/zz//a", b"x")], "empty, '.' or '..' segment"),
    ]
    for label, entries, want in cases:
        zp = os.path.join(work, "bad.zip")
        good_zip(zp, entries)
        tgt = os.path.join(work, "badout")
        rc, out, err, cmd = run(tool, ["extract", zp, tgt])
        row("refuse", "extract refuses " + label,
            rc == 2 and want in err and not os.path.exists(tgt),
            ["$ " + " ".join(cmd[1:]), "  -> exit %d %r; target created: %s" % (rc, err.strip(), os.path.exists(tgt))])
        shutil.rmtree(tgt, ignore_errors=True)

    zp = os.path.join(work, "dup.zip")
    with zipfile.ZipFile(zp, "w") as zf:
        for name, data in BASE:
            zf.writestr(name, data or b"")
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            zf.writestr("accounts/zz/bp/a", b"again")
    tgt = os.path.join(work, "dupout")
    rc, out, err, cmd = run(tool, ["extract", zp, tgt])
    row("refuse", "extract refuses a duplicate name", rc == 2 and "appears twice" in err and not os.path.exists(tgt),
        ["$ " + " ".join(cmd[1:]), "  -> exit %d %r" % (rc, err.strip())])

    zp = os.path.join(work, "link.zip")
    symlink_zip(zp)
    tgt = os.path.join(work, "linkout")
    rc, out, err, cmd = run(tool, ["extract", zp, tgt])
    row("refuse", "extract refuses a symlink entry", rc == 2 and "is a symlink" in err and not os.path.exists(tgt),
        ["$ " + " ".join(cmd[1:]), "  -> exit %d %r" % (rc, err.strip())])

    os.makedirs(os.path.join(work, "exists"))
    rc, out, err, cmd = run(tool, ["extract", win, os.path.join(work, "exists")])
    row("refuse", "extract refuses an existing target", rc == 2 and "already exists" in err,
        ["$ " + " ".join(cmd[1:]), "  -> exit %d %r" % (rc, err.strip())])

    pack_cases = [
        ("an upper-case account name", ["ZZ=" + src], b"format: 1\n", "not a lower-case SD account name"),
        ("the same account twice", ["zz=" + src, "zz=" + src], b"format: 1\n", "named twice"),
        ("a relative directory", ["zz=src"], b"format: 1\n", "is not an absolute directory"),
        ("an empty manifest", ["zz=" + src], b"", "manifest on stdin is empty"),
        ("a non-ASCII manifest", ["zz=" + src], "format: é\n".encode("utf-8"), "not plain ASCII"),
    ]
    for label, args, stdin, want in pack_cases:
        rc, out, err, cmd = run(tool, ["pack"] + args, stdin)
        row("refuse", "pack refuses " + label, rc == 2 and want in err and out == b"",
            ["$ " + " ".join(cmd[1:]), "  -> exit %d %r, %d bytes on stdout" % (rc, err.strip(), len(out))])

    swap_suite(tool, work)


def swap_suite(tool, work):
    """SD Core Solo's start-up swap.  A good marker swaps and cleans up; a bad
    one moves NOTHING and keeps the marker."""
    def fixture(tag, staged_rel="/.sdrestore.5/accounts/zz", target_rel="/user_accounts/zz", fmt="format: 1",
                make_staged=True):
        root = os.path.join(work, "swap-" + tag)
        os.makedirs(os.path.join(root, "user_accounts", "zz"))
        with open(os.path.join(root, "user_accounts", "zz", "data"), "w") as f:
            f.write("OLD")
        if make_staged:
            os.makedirs(os.path.join(root, ".sdrestore.5", "accounts", "zz"))
            with open(os.path.join(root, ".sdrestore.5", "accounts", "zz", "data"), "w") as f:
                f.write("NEW")
            with open(os.path.join(root, ".sdrestore.5", "manifest.txt"), "w") as f:
                f.write("format: 1\n")
        marker = os.path.join(root, ".sdrestore.pending")
        with open(marker, "w") as f:
            f.write("%s\n%s%s\n%s%s\nzz\n2026-10-02 10:00:00\n/x/SD-h-zz.zip\n" % (fmt, root, staged_rel, root, target_rel))
        return root, marker

    def read(p):
        try:
            return open(p).read()
        except OSError:
            return None

    root, marker = fixture("good")
    rc, out, err, cmd = run(tool, ["swap", marker])
    tgt, prev = os.path.join(root, "user_accounts", "zz", "data"), os.path.join(root, ".sdrestore.previous", "data")
    log = read(os.path.join(root, "sdrestore.log")) or ""
    row("allow", "swap: the staged tree goes in, the old one to .sdrestore.previous, marker and staging gone",
        rc == 0 and read(tgt) == "NEW" and read(prev) == "OLD" and not os.path.exists(marker)
        and not os.path.exists(os.path.join(root, ".sdrestore.5")) and "DONE" in log and b"RESTORED" in out,
        ["$ " + " ".join(cmd[1:]), "  -> exit %d out=%r err=%r" % (rc, out.decode().strip(), err.strip()),
         "  target=%r previous=%r marker kept=%s log tail=%r" % (read(tgt), read(prev), os.path.exists(marker),
                                                                 log.strip().splitlines()[-1:] )])

    bad = [
        ("a staged tree outside .sdrestore.<n>", dict(staged_rel="/elsewhere/zz"), "is not"),
        ("a target outside the accounts root", dict(target_rel="/../../etc/zz"), "the target"),
        ("a marker of another format", dict(fmt="format: 2"), "not a format-1 marker"),
        ("a staged tree that is not there", dict(make_staged=False), "is not a directory"),
    ]
    for i, (label, kw, want) in enumerate(bad):
        root, marker = fixture("bad%d" % i, **kw)
        if kw.get("staged_rel") == "/elsewhere/zz":
            os.makedirs(os.path.join(root, "elsewhere", "zz"))
        rc, out, err, cmd = run(tool, ["swap", marker])
        tgt = os.path.join(root, "user_accounts", "zz", "data")
        row("refuse", "swap refuses " + label + "; nothing moves, the marker stays",
            rc == 2 and want in err and read(tgt) == "OLD" and os.path.exists(marker)
            and not os.path.exists(os.path.join(root, ".sdrestore.previous")),
            ["$ " + " ".join(cmd[1:]), "  -> exit %d %r; target=%r marker kept=%s" % (rc, err.strip(), read(tgt),
                                                                                 os.path.exists(marker))])


MUTANTS = [
    ("swap staged check gone", 'if not m or m.group(2) != name or not NAME_RE.match(name):', 'if False:'),
    ("swap target check gone", 'if os.path.dirname(os.path.dirname(target)) != root or os.path.basename(target) != name:',
     'if False:'),
    ("'..' allowed", 'if any(s in ("", ".", "..") for s in segs):', 'if any(s in ("",) for s in segs):'),
    ("symlinks followed", "if stat.S_ISLNK(st.st_mode):", "if False:"),
    ("existing target reused", "if os.path.lexists(target):", "if False:"),
    ("manifest not required", "if not has_manifest:", "if False:"),
    ("directory modes not applied", "os.chmod(dest, dperm)", "pass"),
]


def main():
    selftest = "--selftest" in sys.argv[1:]
    say("test-accarchive-units: %s" % TOOL)
    if not os.path.isfile(TOOL):
        say("CANNOT RUN - the tool is missing")
        return 2
    with tempfile.TemporaryDirectory(prefix="accarch-") as work:
        say("  scratch: %s\n" % work)
        real = os.path.join(work, "real")
        os.makedirs(real)
        suite(TOOL, real)
        if RESULTS["allow"] == 0 or RESULTS["refuse"] == 0:
            say("\nREFUSED: the null case - %(allow)d allow rows, %(refuse)d refuse rows" % RESULTS)
            return 2
        say("\n%(pass)d passed, %(fail)d failed (%(allow)d allow, %(refuse)d refuse rows)" % RESULTS)
        if RESULTS["fail"]:
            return 1
        if not selftest:
            return 0
        src = open(TOOL).read()
        red = 0
        for label, old, new in MUTANTS:
            if src.count(old) != 1:
                say("CANNOT RUN - mutant '%s': expected one match, found %d" % (label, src.count(old)))
                return 2
            mpath = os.path.join(work, "mutant")
            with open(mpath, "w") as f:
                f.write(src.replace(old, new))
            for k in RESULTS:
                RESULTS[k] = 0
            mwork = os.path.join(work, "m-" + label.replace(" ", "-").replace("'", ""))
            os.makedirs(mwork)
            say("\n--- mutant: %s" % label)
            suite(mpath, mwork)
            went_red = RESULTS["fail"] > 0
            red += went_red
            say("--- mutant '%s': %s (%d rows failed)" % (label, "RED as it must be" if went_red else "STILL GREEN - the test misses it", RESULTS["fail"]))
        say("\nselftest: %d of %d mutants went red" % (red, len(MUTANTS)))
        return 0 if red == len(MUTANTS) else 1


if __name__ == "__main__":
    sys.exit(main())
