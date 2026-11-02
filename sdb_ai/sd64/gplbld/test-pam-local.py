#!/usr/bin/env python3
# test-pam-local.py - the console half of S.101 stage C (2 Nov 2026): gplbld/ssh-forcecommand.sh --open-local, --close-local, --local-state, and --remove taking the console
# fences out.  The script is run on a scratch PAM directory (SD_PAM_DIR) holding Debian-shaped login and gdm-password files, a common-auth that must never be touched, and a
# scratch module file (SD_TOTP_MODULE); SD_SSHD_CONFIG names a scratch path so nothing real can be reached.  No root, no sshd.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-pam-local.py
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-pam-local.py --selftest
#
# THE REFUSAL ROWS COMPARE BYTES OF EVERY FILE IN THE DIRECTORY: --open-local makes every file's new text before it writes any, so a display manager it cannot place the lines
# in must leave login unwritten too.  WHAT THIS CANNOT SHOW (the VM witness's): that login and GDM really ask for the code with the scope 'all' and ask nothing with 'remote', the
# marker a real console session writes, a root-owned module.  Exit 0 every row passed, 1 a row failed (or a mutant survived), 2 it could not run.  Fewer than 20 rows is a failure.

import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
HELPER_REAL = os.path.join(HERE, "ssh-forcecommand.sh")

# The shapes of this machine's Debian 13 files (comments shortened).
LOGIN = """#
# The PAM configuration file for the Shadow `login' service
#
auth       optional   pam_faildelay.so  delay=3000000
auth       requisite  pam_nologin.so
session [success=ok ignore=ignore module_unknown=ignore default=bad] pam_selinux.so close
# Sets the loginuid process attribute
session    required     pam_loginuid.so
session    optional   pam_motd.so motd=/run/motd.dynamic
@include common-auth
auth       optional   pam_group.so
@include common-account
@include common-session
@include common-password
"""
GDM = """#%PAM-1.0
auth    requisite       pam_nologin.so
auth\trequired\tpam_succeed_if.so user != root quiet_success
@include common-auth
auth    optional        pam_gnome_keyring.so
@include common-account
session [success=ok ignore=ignore module_unknown=ignore default=bad]        pam_selinux.so close
session required        pam_loginuid.so
session optional        pam_keyinit.so force revoke
@include common-session
@include common-password
"""
COMMON_AUTH = "auth\t[success=1 default=ignore]\tpam_unix.so nullok\nauth\trequisite\t\t\tpam_deny.so\nauth\trequired\t\t\tpam_permit.so\n"

A_BEGIN = "# --- BEGIN SD sdsys authenticator code (S.95) - do not edit within this fence ---"
A_END = "# --- END SD sdsys authenticator code ---"
S_BEGIN = "# --- BEGIN SD sdsys login marker (S.101) - do not edit within this fence ---"
S_END = "# --- END SD sdsys login marker ---"
GUARD_A = "auth [success=1 default=ignore] pam_succeed_if.so quiet user notin sdsys"
GUARD_S = "session [success=1 default=ignore] pam_succeed_if.so quiet user notin sdsys"


def say(s):
    print(s, flush=True)


def wr(p, text, mode=0o644):
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    os.chmod(p, mode)


def rd(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def strip_fences(text):
    text = re.sub(re.escape(A_BEGIN) + r".*?" + re.escape(A_END) + r"\n", "", text, flags=re.S)
    return re.sub(re.escape(S_BEGIN) + r".*?" + re.escape(S_END) + r"\n", "", text, flags=re.S)


class Env:
    """A scratch PAM directory, a module, and a scratch sshd_config path that does not exist."""

    def __init__(self, base, n, helper, files=None):
        self.d = os.path.join(base, "e%d" % n)
        self.pamd = os.path.join(self.d, "pam.d")
        os.makedirs(self.pamd)
        self.helper = helper
        self.module = os.path.join(self.d, "pam_sdtotp.so")
        wr(self.module, "not really a module\n", 0o644)
        self.cfg = os.path.join(self.d, "sshd_config")             # never made: --remove's no-config branch
        self.orig = dict(files if files is not None else {"login": LOGIN, "gdm-password": GDM, "common-auth": COMMON_AUTH})
        for name, text in self.orig.items():
            wr(os.path.join(self.pamd, name), text)

    def run(self, mode, **extra):
        env = dict(os.environ, SD_SSHD_CONFIG=self.cfg, SD_PAM_DIR=self.pamd, SD_TOTP_MODULE=self.module, SD_PAM_SSHD=os.path.join(self.d, "pam_sshd"))
        env.update(extra)
        p = subprocess.run(["bash", self.helper, mode], capture_output=True, text=True, env=env, timeout=60)
        return p.returncode, p.stdout + p.stderr

    def f(self, name):
        return os.path.join(self.pamd, name)

    def snap(self):
        out = {}
        for name in sorted(os.listdir(self.pamd)):
            p = self.f(name)
            out[name] = ("link:" + os.readlink(p)) if os.path.islink(p) else rd(p)
        return out

    def state(self):
        code, out = self.run("--local-state")
        return dict(l.split("=", 1) for l in out.splitlines() if "=" in l)


def rows_for(helper):
    rows = []

    def row(label, ok, detail=""):
        rows.append((label, bool(ok), detail))

    base = tempfile.mkdtemp(prefix="pam-local-")
    cnt = [0]

    def env(**kw):
        cnt[0] += 1
        return Env(base, cnt[0], helper, **kw)

    try:
        # ---------------------------------------------------------------- the ordinary path
        e = env()
        row("--local-state before: login and gdm-password absent, lightdm and sddm have no file",
            e.state() == {"local-login": "absent", "local-gdm-password": "absent", "local-lightdm": "none", "local-sddm": "none"}, "%s" % e.state())
        code, out = e.run("--open-local")
        row("--open-local: exit 0 and says OPENED", code == 0 and "OPENED" in out, out.strip()[:200])
        for name, first_auth in (("login", "auth       optional   pam_faildelay.so  delay=3000000"), ("gdm-password", "auth    requisite       pam_nologin.so")):
            lines = rd(e.f(name)).splitlines()
            i = lines.index(first_auth)
            row("... %s: the auth fence (guard, then the module with the word 'local') is directly above the first auth line" % name,
                lines[i - 4] == A_BEGIN and lines[i - 3] == GUARD_A and lines[i - 2] == "auth required %s local" % e.module and lines[i - 1] == A_END,
                "\n".join(lines[max(0, i - 5):i + 1]))
            j = [k for k, l in enumerate(lines) if re.match(r"session\s+required\s+pam_loginuid\.so", l)][0]
            row("... %s: the session fence (guard, then 'session optional' module 'local') is directly AFTER the pam_loginuid line" % name,
                lines[j + 1] == S_BEGIN and lines[j + 2] == GUARD_S and lines[j + 3] == "session optional %s local" % e.module and lines[j + 4] == S_END,
                "\n".join(lines[j:j + 6]))
            row("... %s: take both fences out and it is the original, byte for byte; the original is kept once in %s.before-sd" % (name, name),
                strip_fences(rd(e.f(name))) == e.orig[name] and rd(e.f(name) + ".before-sd") == e.orig[name], "")
        row("... common-auth (which su and sudo share) is not touched and gets no backup",
            rd(e.f("common-auth")) == COMMON_AUTH and not os.path.exists(e.f("common-auth.before-sd")), "")
        row("... --local-state: login and gdm-password present, the two absent display managers none",
            e.state() == {"local-login": "present", "local-gdm-password": "present", "local-lightdm": "none", "local-sddm": "none"}, "%s" % e.state())
        s1 = e.snap()
        code, out = e.run("--open-local")
        row("a second --open-local changes nothing (one fence of each kind, the same bytes)", code == 0 and e.snap() == s1, out.strip()[:120])
        code, out = e.run("--close-local")
        row("--close-local: every file is back to the original byte for byte (the backups stay)",
            code == 0 and all(rd(e.f(n)) == t for n, t in e.orig.items()) and "CLOSED" in out, out.strip()[:200])
        row("... --local-state: absent again", e.state()["local-login"] == "absent" and e.state()["local-gdm-password"] == "absent", "%s" % e.state())
        code, out = e.run("--close-local")
        row("... a second --close-local is a clean no-op", code == 0 and all(rd(e.f(n)) == t for n, t in e.orig.items()), out.strip()[:120])

        e = env()
        e.run("--open-local")
        code, out = e.run("--remove")
        row("--remove (the deleter's mode) on a machine with no sshd_config still takes the console fences out, byte for byte",
            code == 0 and all(rd(e.f(n)) == t for n, t in e.orig.items()), out.strip()[:200])

        e = env(files={"login": LOGIN, "lightdm": GDM.replace("#%PAM-1.0\n", ""), "sddm": GDM})
        code, out = e.run("--open-local")
        row("lightdm and sddm get the fences when their files exist (gdm-password absent: passed over)",
            code == 0 and e.state() == {"local-login": "present", "local-gdm-password": "none", "local-lightdm": "present", "local-sddm": "present"}, "%s | %s" % (e.state(), out.strip()[:120]))

        e = env()
        wr(e.f("login"), strip_fences(LOGIN).replace("session    required     pam_loginuid.so\n", "session    required     pam_loginuid.so\n" + S_BEGIN + "\n" + GUARD_S + "\nsession optional /x local\n" + S_END + "\n"))
        row("--local-state says partial for a file with one of the two fences", e.state()["local-login"] == "partial", "%s" % e.state())

        # ---------------------------------------------------------------- refusals: every file in the directory exactly as it was
        def refused(label, e, words=None, **kw):
            before = e.snap()
            code, out = e.run("--open-local", **kw)
            row("REFUSE: " + label + " - exit non-zero, every file byte for byte as it was",
                code != 0 and e.snap() == before and (words is None or words in out), "exit %d: %s" % (code, out.strip()[:160]))

        refused("gdm-password has no pam_loginuid session line (login, which could take the lines, is not written either)",
                env(files={"login": LOGIN, "gdm-password": GDM.replace("session required        pam_loginuid.so\n", "")}), words="pam_loginuid")
        refused("login has no auth line", env(files={"login": "# nothing\nsession required pam_loginuid.so\n", "gdm-password": GDM}), words="no auth line")
        refused("there is no login file (the text console has no PAM stack)", env(files={"gdm-password": GDM}), words="login")
        e = env()
        os.unlink(e.f("gdm-password"))
        os.symlink(e.f("common-auth"), e.f("gdm-password"))
        refused("gdm-password is a link (to common-auth): not followed, not edited", e, words="not a plain file")
        e = env()
        os.chmod(e.module, 0o664)
        refused("the module is writable by its group", e)
        e = env()
        os.unlink(e.module)
        refused("the module is not there", e)

        # ---------------------------------------------------------------- the script's own text
        src = rd(helper)
        op = src[src.find("  --open-local)"):src.find("  --close-local)")]
        row("TEXT: --open-local makes every file's new text (the loop over local_files) before the first pam_commit_file, and checks the module and login first",
            0 < op.find("module_ok ||") < op.find("$PAM_DIR/login") < op.find("done < <(local_files)") < op.find('pam_commit_file "$work/'), "")
        row("TEXT: the console services are exactly login, gdm-password, lightdm, sddm - never a common-* file",
            "LOCAL_SERVICES=(login gdm-password lightdm sddm)" in src and not re.search(r"LOCAL_SERVICES=\([^)]*common", src), "")
    finally:
        shutil.rmtree(base, ignore_errors=True)
    return rows


MUTANTS = [
    ("the word 'local' is left off", '      pam_with_block "$f" local > "$work/$s.new"', '      pam_with_block "$f" > "$work/$s.new"'),
    ("a link is followed and edited", '      [[ -f $f && ! -L $f ]] || die "$f is not a plain file (a link?)', '      [[ -f $f ]] || die "$f is not a plain file (a link?)'),
    ("a file that cannot take the session line is passed over",
     "        5) die \"$f has no 'session ... pam_loginuid.so' line to put the login marker after; not guessing where it goes, and nothing changed\" ;;", "        5) continue ;;"),
    ("login is not required", '    [[ -f $PAM_DIR/login && ! -L $PAM_DIR/login ]] || die', '    true || die'),
    ("the module is not checked", '    module_ok || die "$PAM_MODULE is not a plain file (not a link), owned by root, closed to anyone else\'s writing, with a plain path; not putting it in the PAM stack"\n    [[ -f $PAM_DIR/login',
     '    [[ -f $PAM_DIR/login'),
    ("--close-local leaves the fences", '    local_remove_all\n    say "CLOSED - no console', '    say "CLOSED - no console'),
    ("--remove with no sshd_config leaves the console fences", "      local_remove_all                                   # S.101 stage C: a machine with no sshd", "      true                                   # S.101 stage C: a machine with no sshd"),
    ("common-auth is a console service", "LOCAL_SERVICES=(login gdm-password lightdm sddm)", "LOCAL_SERVICES=(login gdm-password lightdm sddm common-auth)"),
    ("--local-state never says partial", "      elif pam_has_block \"$f\" || pam_has_session \"$f\"; then st=partial\n", ""),
]


def selftest():
    say("test-pam-local --selftest")
    src = rd(HELPER_REAL)
    for name, old, new in MUTANTS:
        if src.count(old) != 1:
            say("  CANNOT RUN - mutant %s: its text occurs %d times (wanted 1)" % (name, src.count(old)))
            return 2
    tmp = tempfile.mkdtemp(prefix="pam-local-mut-")
    survivors = []
    try:
        base = os.path.join(tmp, "base.sh")
        wr(base, src, 0o755)
        rows = rows_for(base)
        bad = [r for r in rows if not r[1]]
        say("  control : the real script, %d rows, %d failed" % (len(rows), len(bad)))
        for label, ok, detail in bad:
            say("    FAIL %s | %s" % (label, detail))
        if bad or len(rows) < 20:
            return 1
        for i, (name, old, new) in enumerate(MUTANTS):
            path = os.path.join(tmp, "m%d.sh" % i)
            wr(path, src.replace(old, new), 0o755)
            p = subprocess.run(["bash", "-n", path], capture_output=True, text=True)
            if p.returncode != 0:
                say("  CANNOT RUN - mutant %s does not parse:\n%s" % (name, p.stderr))
                return 2
            try:
                mrows = rows_for(path)
            except Exception as ex:
                mrows = [("the rows stopped: %s: %s" % (type(ex).__name__, ex), False, "")]
            caught = [r for r in mrows if not r[1]]
            say("  [%s] %-58s %s" % ("KILLED  " if caught else "SURVIVED", name, ("%d row(s), first: %s" % (len(caught), caught[0][0][:70])) if caught else ""))
            if not caught:
                survivors.append(name)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    say("")
    if survivors:
        say("test-pam-local --selftest: FAILED - %d of %d mutants survived: %s" % (len(survivors), len(MUTANTS), ", ".join(survivors)))
        return 1
    say("test-pam-local --selftest: PASSED - %d of %d mutants killed." % (len(MUTANTS), len(MUTANTS)))
    return 0


def main():
    if not os.path.isfile(HELPER_REAL):
        say("test-pam-local: CANNOT RUN - missing %s" % HELPER_REAL)
        return 2
    if "--selftest" in sys.argv[1:]:
        return selftest()
    say("test-pam-local")
    say("  helper: %s (SD_PAM_DIR, SD_TOTP_MODULE and SD_SSHD_CONFIG point into a scratch directory)" % HELPER_REAL)
    rows = rows_for(HELPER_REAL)
    bad = [r for r in rows if not r[1]]
    for label, ok, detail in rows:
        say("  [%s] %s%s" % ("PASS" if ok else "FAIL", label, "" if ok or not detail else "  <- " + detail))
    if len(rows) < 20:
        say("test-pam-local: FAILED - only %d rows ran (the null case)" % len(rows))
        return 1
    say("test-pam-local: %d passed, %d failed" % (len(rows) - len(bad), len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
