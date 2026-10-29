#!/usr/bin/env python3
"""test-sudostub-units.py - the sandbox harness keeps the HOST'S sudo out of every sandbox session (S.85, 28 Oct 2026), read off the harness as text.  Free: no install, no sudo, no sd.

    python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-sudostub-units.py [--selftest]

THE DEFECT.  On a host with a real SD install, gpl.bp/remoteapi, remotessh, settings_os (accos.h), acc_os_bakdir and acc_archive run `sudo /usr/local/sbin/sd-elevate ...`; a sandbox page
reached the REAL helper and sudo-rs asked the sandbox user for a password, so tool-remote and docs could not draw and tool-config and tool-backups failed 4 and 6 rows (26 Oct 2026).

THE FIX HELD HERE.  `sandbox-tk-base.py` (the harness every page suite loads through `sandbox-home.py`) copies `sudo-stub.sh` as `sudo` into a private directory and puts it first in PATH once, at
import; its `sudo_null_case()` is a setup row that proves it three ways (PATH, a child shell, an SD session) and STOPS the suite when it is not so; `sandbox-tk-base.py`'s own main and
`sandbox-home.py`'s `setup()` call it before anything else.  ***IT READS TEXT AND RUNS NOTHING***: that the row really stops a suite on a host whose sudo is reachable is the suite's own run, which
the 28 Oct testing rule did not allow when this was written (WRITTEN, NOT RUN).

Written 28 Oct 2026 (S.85).  Rows R1 to R3 run the stub machinery in a child interpreter (no sandbox, no SD): the fresh interpreter's PATH, `command -v sudo`, a call of the stub, the directory's removal
at exit, a second load in one process, and a harness with no stub file beside it (the null case: it must stop).

--selftest breaks each invariant in the way an edit plausibly would and requires a check to notice.  Exit 0 every check passed, 1 a check failed, 2 it could not run.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.normpath(os.path.join(HERE, ".."))
REPO = os.path.normpath(os.path.join(SD64, "..", ".."))
FILES = {
    "tkb": os.path.join(HERE, "sandbox-tk-base.py"),
    "home": os.path.join(HERE, "sandbox-home.py"),
    "stub": os.path.join(HERE, "sudo-stub.sh"),
    "remote": os.path.join(HERE, "sandbox-tool-remote.py"),
    "backups": os.path.join(HERE, "sandbox-tool-backups.py"),
    "config": os.path.join(HERE, "sandbox-tool-config.py"),
    "docs": os.path.join(HERE, "sandbox-docs.py"),
}
PRIVATE_STUB = os.path.join(REPO, ".claude", "fake-sudo-stub.sh")         # private repository: absent in a --snapshot copy, which holds sdb_ai only
PAGE_SUITES = ("remote", "backups", "config", "docs")                     # the four that stopped at '[sudo: authenticate] Password:'
SOURCE_DIRS = [os.path.join(SD64, "gplsrc"), os.path.join(SD64, "sdsys", "gpl.bp"), os.path.join(SD64, "sdsys", "syscom")]
ABS_SUDO = re.compile(r"/(usr/)?(local/)?s?bin/sudo\b")


def load():
    raw, missing = {}, []
    for k, p in FILES.items():
        try:
            with open(p, encoding="latin-1") as f:
                raw[k] = f.read()
        except OSError:
            missing.append(p)
    if missing:
        print("test-sudostub-units: CANNOT RUN - missing: " + ", ".join(missing))
        sys.exit(2)
    try:
        with open(PRIVATE_STUB, encoding="latin-1") as f:
            raw["private"] = f.read()
    except OSError:
        raw["private"] = None
    src = {}
    for d in SOURCE_DIRS:
        for n in sorted(os.listdir(d)):
            p = os.path.join(d, n)
            if os.path.isfile(p) and not n.endswith((".o", ".so")):
                with open(p, encoding="latin-1") as f:
                    src[os.path.relpath(p, SD64)] = f.read()
    raw["sources"] = src
    return raw


def code(py):
    """The module with its whole-line comments removed (a docstring is code to this reader, so a check anchors on tokens only the code holds)."""
    return "\n".join(l for l in py.split("\n") if not l.lstrip().startswith("#"))


def sh_code(txt):
    return [l.strip() for l in txt.split("\n") if l.strip() and not l.lstrip().startswith("#")]


def body(text, header):
    """The text of the def that begins with `header`, up to the next top-level def, class or assignment."""
    i = text.find(header)
    if i < 0:
        return ""
    m = re.search(r"\n(?=\S)", text[i + len(header):])
    return text[i:i + len(header) + (m.start() if m else len(text))]


def ordered(text, *needles):
    pos = -1
    for n in needles:
        p = text.find(n, pos + 1)
        if p < 0:
            return False
        pos = p
    return True


def checks(raw):
    out = []

    def add(cid, name, ok, detail=""):
        out.append((cid, name, bool(ok), detail))

    tkb, home, stub = code(raw["tkb"]), code(raw["home"]), sh_code(raw["stub"])

    # --- S1 the stub itself
    add("S1a", "sudo-stub.sh is a /bin/sh script whose only commands are the message to stderr and exit 1", raw["stub"].startswith("#!/bin/sh\n")
        and stub == ['echo "sudo: \'$1\': command not found" >&2', "exit 1"], repr(stub))
    if raw["private"] is None:
        add("S1b", "(NOT COMPARED: .claude/fake-sudo-stub.sh is private and absent here, as in a --snapshot copy) the tree's stub equals the private one", True, "not compared")
    else:
        add("S1b", ".claude/fake-sudo-stub.sh holds the same commands as sudo-stub.sh", sh_code(raw["private"]) == stub, repr(sh_code(raw["private"])))

    # --- S2 the installation of the stub, at import, in PATH, first
    inst = body(tkb, "def install_sudo_stub():")
    add("S2a", "the stub comes from sudo-stub.sh beside the harness", 'SUDO_STUB_SRC = os.path.join(HERE, "sudo-stub.sh")' in tkb)
    add("S2b", "install_sudo_stub copies it as `sudo` into a directory made per run and makes it executable", ordered(inst, "tempfile.mkdtemp(", "shutil.copyfile(SUDO_STUB_SRC, os.path.join(d, \"sudo\"))",
                                                                                                "os.chmod(os.path.join(d, \"sudo\"), 0o755)"), inst[:200])
    add("S2c", "the private directory is FIRST in PATH, set on os.environ (every session copies it)", 'os.environ["PATH"] = ":".join([d] + [x for x in parts if x != d])' in inst, inst[-400:])
    add("S2d", "it is called once at module level, before any session helper is defined", re.search(r"^install_sudo_stub\(\)$", tkb, re.M) is not None
        and tkb.find("\ninstall_sudo_stub()\n") < tkb.find("\ndef sess("), "")
    add("S2e", "a missing stub file stops the suite (exit 2) and does not run without it", ordered(inst, "if not os.path.isfile(SUDO_STUB_SRC):", "bail("), inst[:200])
    add("S2f", "the harness assigns PATH nowhere else (a later assignment could put the host's sudo first again)", tkb.count('["PATH"] =') == 1 and '["PATH"] =' not in home
        and 'PATH=' not in tkb and 'PATH=' not in home, "")

    # --- S3 the null case
    nc = body(tkb, "def sudo_null_case(box):")
    probe = tkb[tkb.find("SUDO_PROBE = "):tkb.find("def sudo_null_case")]
    add("S3a", "the null case asks a child shell with the harness's environment: command -v sudo", '["/bin/sh", "-c", "command -v sudo"], env=env' in nc, nc[:300])
    add("S3b", "...and an SD session, through a $internal program whose os.execute asks the same and prints it", "$internal" in probe and "os.execute 'command -v sudo' capturing out" in probe
        and "crt 'ZZSUDO [' :" in probe and 'sess(box, "BASIC bp zzsudo", "RUN bp zzsudo")' in nc, probe[:200])
    add("S3c", "PATH starts with the private directory", "parts[0] == SUDO_DIR" in nc)
    add("S3d", "the child shell's answer is the stub's path", "from_shell == want" in nc)
    add("S3e", "the SD session's answer is the stub's path", "from_sd == want" in nc)
    add("S3f", "the stub is called and must exit 1 with 'command not found' (the stub is not a no-op)", "called.returncode == 1" in nc and '"command not found" in called.stderr' in nc)
    add("S3g", "the directory still holds the stub, byte for byte", "_stub_there(SUDO_DIR)" in nc)
    add("S3h", "a failure STOPS the suite (bail, exit 2) after the row, instead of failing a row and going on", ordered(nc, "row(", "if not ok:", "bail("), nc[-300:])
    add("S3i", "the row prints what it measured: PATH, the shell's answer, the SD session's answer, the host's own sudo, the stub's reply", ordered(nc, "say(", "parts[0]", "from_shell", "from_sd", "behind", "called.stderr"), "")

    # --- S4 where the row runs
    m = body(tkb, "def main():")
    add("S4a", "sandbox-tk-base.py's main runs it once the sandbox is started and before its first session", ordered(m, '"start"], capture_output', "sudo_null_case(box)", "sess(box"), m[:200])
    s = body(home, "def setup(name):")
    add("S4b", "sandbox-home.py's setup runs it once the sandbox is started and before g.prepare() and any fixture account", ordered(s, '"start"], capture_output', "tkb.sudo_null_case(BOX)", "g.prepare()", "g.build_account("), s[:200])
    add("S4c", "sandbox-home.py loads the module that installs the stub", 'os.path.join(HERE, "sandbox-tk-base.py")' in home, "")
    for k in PAGE_SUITES:
        t = code(raw[k])
        add("S4-" + k, "the %s suite sets up through sandbox-home.py's setup (so it gets the stub and the row)" % k, '"sandbox-home.py"' in t and "sh.setup(" in t, "")

    # --- S5 nothing reaches the host's sudo by a path
    bad = sorted(n for n, t in raw["sources"].items() if ABS_SUDO.search(t))
    add("S5", "no source the sessions run (gplsrc, gpl.bp, syscom) names sudo by absolute path: PATH decides, and the stub is first in it", not bad, ", ".join(bad[:5]))
    return out


def run(raw):
    res = checks(raw)
    for cid, name, ok, detail in res:
        print("  [%s] %s %s%s" % ("PASS" if ok else "FAIL", cid, name, "" if ok or not detail else "   <- " + detail[:240]))
    return res


def mutate(raw, where, old, new, sources=None):
    r = dict(raw)
    if where == "sources":
        s = dict(raw["sources"])
        s[sources] = old
        r["sources"] = s
        return r
    if raw[where] is None or raw[where].count(old) != 1:
        raise RuntimeError("mutant text found %d times in %s: %r" % (0 if raw[where] is None else raw[where].count(old), where, old[:60]))
    r[where] = raw[where].replace(old, new)
    return r


MUTANTS = [
    # name, file key, old text, new text, the check ids that must fail
    ("install-call-removed", "tkb", "\ninstall_sudo_stub()\n", "\n", ["S2d"]),
    ("path-last", "tkb", 'os.environ["PATH"] = ":".join([d] + [x for x in parts if x != d])', 'os.environ["PATH"] = ":".join([x for x in parts if x != d] + [d])', ["S2c"]),
    ("no-chmod", "tkb", '    os.chmod(os.path.join(d, "sudo"), 0o755)\n', "", ["S2b"]),
    ("other-source", "tkb", 'SUDO_STUB_SRC = os.path.join(HERE, "sudo-stub.sh")', 'SUDO_STUB_SRC = os.path.join(HERE, "fake-sudo-stub.sh")', ["S2a"]),
    ("missing-stub-runs-on", "tkb", "    if not os.path.isfile(SUDO_STUB_SRC):\n        bail(", "    if not os.path.isfile(SUDO_STUB_SRC):\n        say(", ["S2e"]),
    ("path-set-again", "tkb", 'def _remove_sudo_stub():', 'os.environ["PATH"] = "/usr/bin"\n\n\ndef _remove_sudo_stub():', ["S2f"]),
    ("shell-answer-unchecked", "tkb", "and from_shell == want and from_sd == want", "and from_sd == want", ["S3d"]),
    ("sd-answer-unchecked", "tkb", "from_shell == want and from_sd == want", "from_shell == want", ["S3e"]),
    ("path-unchecked", "tkb", "and parts[0] == SUDO_DIR and _stub_there(SUDO_DIR)", "and _stub_there(SUDO_DIR)", ["S3c"]),
    ("stub-not-called", "tkb", "and called.returncode == 1 and \"command not found\" in called.stderr)", ")", ["S3f"]),
    ("stub-content-unchecked", "tkb", "parts[0] == SUDO_DIR and _stub_there(SUDO_DIR) and", "parts[0] == SUDO_DIR and", ["S3g"]),
    ("no-stop", "tkb", "    if not ok:\n        bail(", "    if not ok:\n        say(", ["S3h"]),
    ("probe-asks-nothing", "tkb", "os.execute 'command -v sudo' capturing out", "os.execute 'true' capturing out", ["S3b"]),
    ("shell-probe-dropped", "tkb", '["/bin/sh", "-c", "command -v sudo"], env=env', '["/bin/sh", "-c", "true"], env=env', ["S3a"]),
    ("tkb-main-no-row", "tkb", "    made = []\n    sudo_null_case(box)\n", "    made = []\n", ["S4a"]),
    ("home-no-row", "home", "    tkb.sudo_null_case(BOX)       # S.85", "    pass       # S.85", ["S4b"]),
    ("home-row-late", "home", "    tkb.sudo_null_case(BOX)       # S.85: the host's sudo is not reachable from any session below (the stub is first in PATH; a suite that cannot show it stops here)\n    g.prepare()\n",
     "    g.prepare()\n    tkb.sudo_null_case(BOX)\n", ["S4b"]),
    ("stub-succeeds", "stub", "exit 1", "exit 0", ["S1a"]),
    ("stub-silent", "stub", "command not found", "ok", ["S1a"]),
    ("stub-extra-command", "stub", "exit 1", "/usr/bin/sudo \"$@\"\nexit 1", ["S1a"]),
    ("private-stub-differs", "private", "exit 1", "exit 0", ["S1b"]),
    ("remote-own-setup", "remote", "sh.setup(", "setup_own(", ["S4-remote"]),
    ("backups-own-harness", "backups", '"sandbox_home_for_toolbackups", "sandbox-home.py"', '"sandbox_home_for_toolbackups", "sandbox-gates.py"', ["S4-backups"]),
    ("absolute-sudo", "sources", "os.execute '/usr/bin/sudo /usr/local/sbin/sd-elevate x'", None, ["S5"]),
]


def selftest(raw):
    base = [c for c, _, ok, _ in checks(raw) if not ok]
    if base:
        print("selftest: the unchanged tree fails %s, so a mutant's own failure cannot be told from the tree's; run the plain check first" % base)
        return 1
    if raw["private"] is None:
        print("selftest: NOTE .claude/fake-sudo-stub.sh is absent, so the mutant 'private-stub-differs' is skipped")
    holes = 0
    for name, where, old, new, want in MUTANTS:
        if where == "private" and raw["private"] is None:
            continue
        try:
            r = mutate(raw, where, old, new, sources="gplsrc/zz-mutant.c") if where == "sources" else mutate(raw, where, old, new)
        except RuntimeError as exc:
            print("  [FAIL] selftest: %s  <- %s" % (name, exc))
            holes += 1
            continue
        failed = sorted(c for c, _, ok, _ in checks(r) if not ok)
        hit = all(w in failed for w in want)
        holes += 0 if hit else 1
        print("  [%s] selftest: %s is caught by %s (failed: %s)" % ("PASS" if hit else "FAIL", name, " ".join(want), " ".join(failed) or "none"))
    print("selftest: %d mutants, %d not caught" % (len(MUTANTS), holes))
    return 1 if holes else 0


CHILD = r'''
import importlib.util, os, subprocess, sys
def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(sys.argv[1], "sandbox-tk-base.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod
a = load("tkb_a")
b = load("tkb_b") if len(sys.argv) > 2 else a
p = os.environ["PATH"].split(":")
sh = subprocess.run(["/bin/sh", "-c", "command -v sudo"], capture_output=True, text=True).stdout.strip()
st = subprocess.run(["sudo", "/usr/local/sbin/sd-elevate", "x"], capture_output=True, text=True, stdin=subprocess.DEVNULL)
print("DIR", a.SUDO_DIR, b.SUDO_DIR, a.SUDO_OWNER, b.SUDO_OWNER)
print("PATH0", p[0])
print("SH", sh)
print("STUB", st.returncode, st.stderr.strip())
print("EXISTS", os.path.isfile(os.path.join(a.SUDO_DIR, "sudo")))
'''


def runtime(raw):
    """No sandbox and no SD: the stub machinery itself, run in a child interpreter.  (Mutants of these rows are not made: the text checks above carry the self-test.)"""
    import shutil
    import subprocess
    import tempfile
    out = []
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")

    def child(src_dir, two):
        return subprocess.run([sys.executable, "-c", CHILD, src_dir] + (["two"] if two else []), env=env, capture_output=True, text=True, timeout=60)

    def facts(r):
        d = {}
        for ln in r.stdout.split("\n"):
            if " " in ln:
                k, v = ln.split(" ", 1)
                d[k] = v
        return d

    r = child(HERE, False)
    f = facts(r)
    sd = f.get("DIR", "").split(" ")[0]
    out.append(("R1a", "a fresh interpreter that loads the harness has the stub first in PATH and `command -v sudo` names it", r.returncode == 0 and f.get("PATH0") == sd != "" and f.get("SH") == sd + "/sudo",
                repr((r.returncode, f, r.stderr[-200:]))))
    out.append(("R1b", "...calling it fails with exit 1 and 'command not found' (not the host's sudo asking for a password)", f.get("STUB", "").startswith("1 ") and "command not found" in f.get("STUB", ""), repr(f.get("STUB"))))
    out.append(("R1c", "...the private directory is gone when the interpreter has ended (only the two files it made were removed)", sd != "" and not os.path.exists(sd), sd))
    r2 = child(HERE, True)
    f2 = facts(r2)
    ds = f2.get("DIR", "").split(" ")
    out.append(("R2", "loading the module twice in one process keeps ONE directory, owned by the first load", r2.returncode == 0 and len(ds) == 4 and ds[0] == ds[1] != "" and ds[2] == "True" and ds[3] == "False", repr(f2.get("DIR"))))
    tmp = tempfile.mkdtemp(prefix="test-sudostub-")
    try:
        for n in ("sandbox-tk-base.py", "ptydrive.py", "termscreen.py"):
            shutil.copyfile(os.path.join(HERE, n), os.path.join(tmp, n))
        r3 = child(tmp, False)
        out.append(("R3", "NULL CASE: a harness with no sudo-stub.sh beside it stops (exit 2, CANNOT RUN) and does not run on the host's sudo", r3.returncode == 2 and "CANNOT RUN" in r3.stdout, repr((r3.returncode, r3.stdout[-200:], r3.stderr[-200:]))))
    finally:
        for n in os.listdir(tmp):
            os.remove(os.path.join(tmp, n))
        os.rmdir(tmp)
    return out


def main(argv):
    raw = load()
    res = run(raw)
    for cid, name, ok, detail in runtime(raw):
        print("  [%s] %s %s%s" % ("PASS" if ok else "FAIL", cid, name, "" if ok or not detail else "   <- " + detail[:300]))
        res.append((cid, name, ok, detail))
    print("test-sudostub-units: %d passed, %d failed" % (sum(1 for r in res if r[2]), sum(1 for r in res if not r[2])))
    rc = 1 if any(not ok for _, _, ok, _ in res) else 0
    if "--selftest" in argv:
        rc = selftest(raw) or rc
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
