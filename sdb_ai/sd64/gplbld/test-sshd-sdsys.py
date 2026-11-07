#!/usr/bin/env python3
# test-sshd-sdsys.py - the sshd side of the remote sdsys login (S.95 stage 2b, rewritten for S.106): gplbld/ssh-forcecommand.sh --open-sdsys, --close-sdsys, --sdsys-state,
# --clean-legacy, and --install / --remove with the sdsys arm in its forms (closed, open with the sdsys PASSWORD, and the LEGACY arm of the authenticator code that an older dev
# install wrote, together with its PAM fences).  The oracle is the REAL sshd of this machine (sshd -t, and sshd -T -C user=sdsys,...) on a scratch sshd_config with a
# throwaway host key, and scratch PAM files - no root, no running sshd.  Written 1 Nov 2026.  test-ssh-forcecommand.py (34 rows) holds the older modes.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-sshd-sdsys.py
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-sshd-sdsys.py --selftest
#
# 2 Nov 26 dm S.106 (owner: "remove the authenticator from both local and remote logins, we will depend on just password authentication for this release"): the open arm is
# password authentication alone and no PAM line is written; the rows of the code's PAM fences, its module and its login marker are gone, and the LEGACY rows take their place: an
# older install's arm and fences are written closed and taken out, in every mode that should, and byte for byte.
#
# THE REFUSAL ROWS COMPARE BYTES: a refused --open-sdsys must leave the sshd_config exactly as it was (the script puts it back when sshd's own answer is not the open arm's), and a
# row that only looked at the exit status would pass a script that refused and still left a half-open door.  The administrator's own settings that defeat the arm are real ones: a
# Match Address block above ours, an Include that sets a keyword first, a DenyUsers, an AllowUsers / AllowGroups that leaves sdsys out.
#
# WHAT THIS CANNOT SHOW (the VM witness's): that a real client is asked for the password and gets sd, and the reload of a running sshd.
# Exit 0 every row passed, 1 a row failed (or a mutant survived), 2 it could not run (no sshd or ssh-keygen).  THE NULL CASE IS REFUSED: fewer than 40 rows is a failure.

import grp
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
HELPER_REAL = os.path.join(HERE, "ssh-forcecommand.sh")

ARM_KEYWORDS = [
    ("AuthenticationMethods", "password"), ("KbdInteractiveAuthentication", "no"), ("PasswordAuthentication", "yes"), ("PubkeyAuthentication", "no"),
    ("HostbasedAuthentication", "no"), ("GSSAPIAuthentication", "no"), ("AuthorizedKeysFile", "none"), ("MaxAuthTries", "3"), ("DisableForwarding", "yes"),
    ("X11Forwarding", "no"), ("AllowAgentForwarding", "no"), ("AllowTcpForwarding", "no"), ("AllowStreamLocalForwarding", "no"), ("PermitTunnel", "no"),
    ("PermitUserRC", "no"), ("PermitTTY", "yes"),
]
# What an older dev install wrote as the open arm: the authenticator code, then the password, both through sshd's PAM stack.
LEGACY_KEYWORDS = [("AuthenticationMethods", "keyboard-interactive"), ("KbdInteractiveAuthentication", "yes"), ("PasswordAuthentication", "no")] + ARM_KEYWORDS[3:]

PAM_BEGIN = "# --- BEGIN SD sdsys authenticator code (S.95) - do not edit within this fence ---"
PAM_END = "# --- END SD sdsys authenticator code ---"
PAMS_BEGIN = "# --- BEGIN SD sdsys login marker (S.101) - do not edit within this fence ---"
PAMS_END = "# --- END SD sdsys login marker ---"

DEBIAN_PAM = """# PAM configuration for the Secure Shell service

# Standard Un*x authentication.
@include common-auth

# Disallow non-root logins when /etc/nologin exists.
account    required     pam_nologin.so
@include common-account
session [success=ok ignore=ignore module_unknown=ignore default=bad]        pam_selinux.so close

# Set the loginuid process attribute.
session    required     pam_loginuid.so

@include common-session
"""
CONSOLE_PAM = """#%PAM-1.0
auth       requisite  pam_nologin.so
auth       required   pam_unix.so
account    required   pam_unix.so
session    required   pam_loginuid.so
session    required   pam_unix.so
"""
BASE_CONFIG = """# an ordinary sshd_config
Port 22
UsePAM yes
PermitRootLogin prohibit-password
Subsystem sftp /usr/lib/openssh/sftp-server
"""
CONSOLE_FILES = ("login", "gdm-password")


def say(text=""):
    print(text)


def rd(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def wr(path, text, mode=None):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    if mode is not None:
        os.chmod(path, mode)


def effective(sshd, cfg, user="sdsys"):
    """sshd's own answer for a user: keyword (lower case) -> value."""
    p = subprocess.run([sshd, "-T", "-f", cfg, "-C", "user=%s,host=sdcheck,addr=192.0.2.1" % user], capture_output=True, text=True)
    d = {}
    for line in p.stdout.splitlines():
        kw, _, val = line.partition(" ")
        d[kw.lower()] = val
    return p.returncode, d


def fenced(text, module="/usr/local/lib/sd/pam_sdtotp.so", opts=""):
    """The PAM text as an older install left it: the auth fence above the first auth line, the session fence directly after the pam_loginuid session line."""
    auth = [PAM_BEGIN, "auth [success=1 default=ignore] pam_succeed_if.so quiet user notin sdsys", "auth required %s%s" % (module, opts), PAM_END]
    sess = [PAMS_BEGIN, "session [success=1 default=ignore] pam_succeed_if.so quiet user notin sdsys", "session optional %s%s" % (module, opts), PAMS_END]
    out, did_a, did_s = [], False, False
    for line in text.splitlines():
        if not did_a and (re.match(r"^\s*-?auth\s", line) or re.match(r"^\s*@include\s+\S*auth", line)):
            out += auth
            did_a = True
        out.append(line)
        if not did_s and re.match(r"^\s*-?session\s+[^#]*pam_loginuid\.so", line):
            out += sess
            did_s = True
    assert did_a and did_s, "the sample PAM text has no place for the fences"
    return "\n".join(out) + "\n"


class Env:
    """A scratch machine: an sshd_config with a host key, a PAM file for sshd and a directory of console PAM files, stub sd and refusal commands."""

    def __init__(self, base, n, ctx, config_extra="", groups="sdusers"):
        self.ctx = ctx
        self.d = os.path.join(base, "e%d" % n)
        os.makedirs(self.d)
        self.hostkey = os.path.join(self.d, "hostkey")
        subprocess.run([ctx["keygen"], "-q", "-t", "ed25519", "-N", "", "-f", self.hostkey], check=True, capture_output=True)
        self.cfg = os.path.join(self.d, "sshd_config")
        self.pamf = os.path.join(self.d, "pam_sshd")
        self.pamd = os.path.join(self.d, "pam.d")
        os.makedirs(self.pamd)
        self.sd = os.path.join(self.d, "sd")
        self.ref = os.path.join(self.d, "ssh-forcecommand")
        wr(self.sd, "#!/bin/sh\nexit 0\n", 0o755)
        wr(self.ref, "#!/bin/sh\nexit 0\n", 0o755)
        self.base_cfg = "HostKey %s\n%s%s" % (self.hostkey, config_extra, BASE_CONFIG)
        wr(self.cfg, self.base_cfg)
        self.pam_text = DEBIAN_PAM
        wr(self.pamf, DEBIAN_PAM)
        for name in CONSOLE_FILES:
            wr(os.path.join(self.pamd, name), CONSOLE_PAM)
        self.groups = groups

    def run(self, mode, **env):
        e = dict(os.environ, SD_SSHD_CONFIG=self.cfg, SD_PAM_SSHD=self.pamf, SD_PAM_DIR=self.pamd, SD_SSHD_BIN=self.ctx["sshd"],
                 SD_SSH_FORCECOMMAND=self.sd, SD_SSH_REFUSE_BIN=self.ref, SD_SDSYS_GROUPS=self.groups)
        e.update(env)
        p = subprocess.run(["bash", self.ctx["helper"], mode], capture_output=True, text=True, env=e)
        return p.returncode, (p.stdout or "") + (p.stderr or "")

    def arm(self):
        """The lines of the sdsys arm in the written config."""
        out, inside = [], False
        for line in rd(self.cfg).splitlines():
            if line == "Match User sdsys":
                inside = True
            elif inside and line.startswith("Match "):
                break
            if inside:
                out.append(line)
        return out

    def state(self):
        code, out = self.run("--sdsys-state")
        return dict(l.split("=", 1) for l in out.splitlines() if "=" in l)

    def snap(self):
        return (rd(self.cfg), rd(self.pamf), tuple(rd(os.path.join(self.pamd, n)) for n in CONSOLE_FILES))

    def pristine_pam(self):
        return (rd(self.pamf) == DEBIAN_PAM) and all(rd(os.path.join(self.pamd, n)) == CONSOLE_PAM for n in CONSOLE_FILES)

    def make_legacy(self):
        """What an older dev install left: the open arm of the authenticator code and its fences in sshd's PAM file and in each console service."""
        self.run("--install")
        t = rd(self.cfg)
        closed = "Match User sdsys\n    DenyUsers sdsys\n"
        assert closed in t
        arm = "Match User sdsys\n" + "".join("    %s %s\n" % kv for kv in LEGACY_KEYWORDS) + "    ForceCommand %s\n" % self.sd
        wr(self.cfg, t.replace(closed, arm))
        wr(self.pamf, fenced(DEBIAN_PAM))
        for name in CONSOLE_FILES:
            wr(os.path.join(self.pamd, name), fenced(CONSOLE_PAM, opts=" local"))


def rows_for(ctx):
    rows = []

    def row(label, ok, detail=""):
        rows.append((label, bool(ok), detail))

    base = tempfile.mkdtemp(prefix="sshd-sdsys-")
    cnt = [0]

    def env(**kw):
        cnt[0] += 1
        return Env(base, cnt[0], ctx, **kw)

    try:
        # ---------------------------------------------------------------- the ordinary path
        e = env()
        code, out = e.run("--install")
        row("install into a pristine config writes the CLOSED arm and leaves every PAM file alone (byte for byte, no backup of them)",
            code == 0 and e.arm() == ["Match User sdsys", "    DenyUsers sdsys"] and e.pristine_pam() and not os.path.exists(e.pamf + ".before-sd"), out.strip()[:120])
        row("--sdsys-state: closed", e.state() == {"sdsys-arm": "closed"}, "%s" % e.state())
        # 7 Nov 26 (S.157): root is in sdusers (the installer puts it there), so without "User *,!root" the refusal arm caught it.  The real
        # sshd, asked about root, must give NO ForceCommand; asked about a member of sdusers and sdssh, the sd command.  Both need this
        # machine's groups: root in sdusers and outside sdssh (else the root row proves nothing), and a user in both.
        try:
            su_members = grp.getgrnam("sdusers").gr_mem
            ssh_members = grp.getgrnam("sdssh").gr_mem
        except KeyError:
            su_members, ssh_members = [], []
        both = sorted(u for u in su_members if u in ssh_members and u not in ("root", "sdsys"))
        if "root" not in su_members or "root" in ssh_members or not both:
            row("S.157 CANNOT RUN: needs root in sdusers and not in sdssh, and a user in both (sdusers=%s sdssh=%s)" % (su_members, ssh_members), False)
        else:
            rc, eff = effective(ctx["sshd"], e.cfg, "root")
            row("S.157 the REAL sshd gives root (in sdusers, not in sdssh) no ForceCommand: root's ssh is the machine's own",
                rc == 0 and eff.get("forcecommand", "none") == "none", "forcecommand=%r" % eff.get("forcecommand"))
            rc, eff = effective(ctx["sshd"], e.cfg, both[0])
            row("S.157 ... and still forces %s (in sdusers and sdssh) into sd" % both[0], rc == 0 and eff.get("forcecommand") == e.sd,
                "forcecommand=%r" % eff.get("forcecommand"))
        cfg_closed = rd(e.cfg)
        rc, alice_before = effective(ctx["sshd"], e.cfg, "alice")
        code, out = e.run("--open-sdsys")
        row("--open-sdsys on an installed block: exit 0", code == 0 and "OPENED" in out, out.strip()[:200])
        want = ["Match User sdsys"] + ["    %s %s" % kv for kv in ARM_KEYWORDS] + ["    ForceCommand %s" % e.sd]
        row("... the sdsys arm is exactly the 17 lines of the open arm (this test's own list: the password alone)", e.arm() == want, "\n".join(e.arm()))
        row("... --sdsys-state: open", e.state() == {"sdsys-arm": "open"}, "%s" % e.state())
        rc, eff = effective(ctx["sshd"], e.cfg)
        # a build of sshd without GSSAPI does not print that keyword at all; where it does print it, it must say no
        bad = [(k, eff.get(k.lower()), v) for k, v in ARM_KEYWORDS if eff.get(k.lower(), "").lower() != v and not (k == "GSSAPIAuthentication" and k.lower() not in eff)] + \
              ([("forcecommand", eff.get("forcecommand"), e.sd)] if eff.get("forcecommand") != e.sd else [])
        row("... the REAL sshd, asked about sdsys, gives every one of those values", rc == 0 and not bad, "%s" % bad)
        rc, alice_after = effective(ctx["sshd"], e.cfg, "alice")
        row("... and gives another user exactly what it gave before: the arm touches nobody else", rc == 0 and alice_before == alice_after, "")
        row("... NO PAM line was written: sshd's PAM file and the console files are the originals, and no PAM backup was made",
            e.pristine_pam() and not os.path.exists(e.pamf + ".before-sd"), "")
        row("... the original config is kept once (sshd_config.before-sd holds the pristine config)", rd(e.cfg + ".before-sd") == e.base_cfg, "")
        s_open = e.snap()
        code, out = e.run("--open-sdsys")
        row("a second --open-sdsys changes nothing (one block, the same bytes)", code == 0 and e.snap() == s_open and s_open[0].count("# --- END SD ssh-only model ---") == 1, "")
        code, out = e.run("--install")
        row("--install over the open arm keeps it open (and one block)", code == 0 and e.state()["sdsys-arm"] == "open" and rd(e.cfg).count("# --- END SD ssh-only model ---") == 1, out.strip()[:120])
        code, out = e.run("--check")
        row("--check reports the form, and prints the block it would write for that form (the password, never keyboard-interactive)",
            code == 0 and "sdsys arm         open" in out and "AuthenticationMethods password" in out and "keyboard-interactive" not in out, out.strip()[:100])
        code, out = e.run("--close-sdsys")
        row("--close-sdsys: the arm is closed again (the same bytes as the first install)", code == 0 and rd(e.cfg) == cfg_closed and e.state() == {"sdsys-arm": "closed"}, out.strip()[:120])
        rc, eff = effective(ctx["sshd"], e.cfg)
        row("... and the REAL sshd now denies sdsys network login", rc == 0 and "sdsys" in eff.get("denyusers", "").split(), "%s" % eff.get("denyusers"))
        e.run("--open-sdsys")
        code, out = e.run("--remove")
        row("--remove gives back the pristine files, byte for byte", code == 0 and rd(e.cfg) == e.base_cfg and e.pristine_pam(), out.strip()[:140])
        code, out = e.run("--remove")
        row("... and a second --remove is a clean no-op", code == 0, out.strip()[:100])

        # ---------------------------------------------------------------- refusals: the config exactly as it was
        def refused(label, e, mode="--open-sdsys", words=None, **kw):
            before = e.snap()
            code, out = e.run(mode, **kw)
            same = e.snap() == before
            row("REFUSE: " + label + " - exit non-zero, sshd_config and the PAM files byte for byte as they were",
                code != 0 and same and (words is None or words in out), "exit %d, %s: %s" % (code, "same" if same else "CHANGED", out.strip()[:200]))

        e = env()
        refused("--open-sdsys with no SD block in the config", e, words="--install first")
        e = env()
        e.run("--install")
        t = rd(e.cfg)
        i = t.index("# --- BEGIN SD ssh-only model")
        wr(e.cfg, t[:i] + "Match Address 192.0.2.0/24\n    PasswordAuthentication no\n" + t[i:])
        refused("an administrator's Match Address block ABOVE ours sets PasswordAuthentication first", e, words="passwordauthentication")

        e = env()
        extra = os.path.join(e.d, "extra.conf")
        wr(extra, "Match all\n    AuthenticationMethods publickey\n")
        e.run("--install")
        wr(e.cfg, "Include %s\n" % extra + rd(e.cfg))
        refused("an Include at the top brings a Match block that sets AuthenticationMethods first", e, words="authenticationmethods")
        e = env()
        extra = os.path.join(e.d, "extra.conf")
        wr(extra, "AuthenticationMethods publickey\nPasswordAuthentication no\n")
        e.run("--install")
        wr(e.cfg, "Include %s\n" % extra + rd(e.cfg))
        code, out = e.run("--open-sdsys")
        row("ALLOW: an Include that sets the same keywords GLOBALLY is no obstacle (a Match block overrides the global value; the real sshd says so)",
            code == 0 and e.state()["sdsys-arm"] == "open", out.strip()[:140])

        e = env()
        e.run("--install")
        wr(e.cfg, rd(e.cfg).replace("UsePAM yes", "UsePAM no"))
        code, out = e.run("--open-sdsys")
        row("ALLOW: UsePAM off is no obstacle any more (sshd checks the password itself; there is no PAM line to ask for a code)", code == 0 and e.state()["sdsys-arm"] == "open", out.strip()[:140])

        e = env()
        e.run("--install")
        wr(e.cfg, "DenyUsers sdsys\n" + rd(e.cfg))
        refused("an administrator's DenyUsers names sdsys", e, words="DenyUsers")

        for what, line in (("AllowUsers alice bob", "AllowUsers alice bob"), ("AllowUsers * !sdsys", "AllowUsers * !sdsys")):
            e = env()
            e.run("--install")
            wr(e.cfg, line + "\n" + rd(e.cfg))
            refused("an administrator's '%s' leaves sdsys out (the shut door the OpenSSH manual does not warn of)" % what, e, words="AllowUsers")
        e = env(groups="sdusers")
        e.run("--install")
        wr(e.cfg, "AllowGroups wheel admin\n" + rd(e.cfg))
        refused("an AllowGroups that names none of sdsys's groups", e, words="AllowGroups")
        e = env(groups="sdusers")
        e.run("--install")
        wr(e.cfg, "DenyGroups sdusers\n" + rd(e.cfg))
        refused("a DenyGroups that names a group of sdsys", e, words="DenyGroups")
        e = env(groups="")
        e.run("--install")
        wr(e.cfg, "AllowGroups sdusers\n" + rd(e.cfg))
        refused("an AllowGroups when sdsys's groups cannot be read", e, words="cannot be read")
        e = env()
        e.run("--install")
        refused("no sshd found to ask", e, SD_SSHD_BIN="")

        # ---------------------------------------------------------------- closing is read back too
        # A DenyUsers cannot be overridden by anything an administrator writes (the lists add up across blocks), so the read-back of the CLOSED arm is driven with a stand-in sshd
        # that accepts the file (-t) and answers -T with no DenyUsers at all, and one whose -T fails.
        stub = os.path.join(base, "sshd-stub")
        wr(stub, '#!/bin/sh\nfor a in "$@"; do [ "$a" = "-T" ] && { [ -n "$STUB_T_FAIL" ] && exit 1; echo "usepam yes"; exit 0; }; done\nexit 0\n', 0o755)
        e = env()
        e.run("--install")
        e.run("--open-sdsys")
        refused("--close-sdsys when sshd's own answer shows no DenyUsers for sdsys", e, mode="--close-sdsys", words="NOT CLOSED", SD_SSHD_BIN=stub)
        e = env()
        e.run("--install")
        refused("--open-sdsys when sshd -T cannot read the result", e, words="NOT OPENED", SD_SSHD_BIN=stub, STUB_T_FAIL="1")
        e = env()
        e.run("--install")
        e.run("--open-sdsys")
        refused("--close-sdsys when sshd -T cannot read the result", e, mode="--close-sdsys", words="NOT CLOSED", SD_SSHD_BIN=stub, STUB_T_FAIL="1")

        # ---------------------------------------------------------------- controls: the refusals above are about the settings, not about everything
        e = env()
        e.run("--install")
        wr(e.cfg, "AllowUsers sdsys alice\n" + rd(e.cfg))
        code, out = e.run("--open-sdsys")
        row("ALLOW: an AllowUsers that names sdsys is no obstacle", code == 0 and e.state()["sdsys-arm"] == "open", out.strip()[:140])
        e = env(groups="wheel sdusers")
        e.run("--install")
        wr(e.cfg, "AllowGroups sdusers\n" + rd(e.cfg))
        code, out = e.run("--open-sdsys")
        row("ALLOW: an AllowGroups that names one of sdsys's groups is no obstacle", code == 0 and e.state()["sdsys-arm"] == "open", out.strip()[:140])
        e = env()
        e.run("--install")
        os.unlink(e.pamf)
        code, out = e.run("--open-sdsys")
        row("ALLOW: no PAM file at all is no obstacle (nothing here writes one)", code == 0 and e.state()["sdsys-arm"] == "open" and not os.path.exists(e.pamf), out.strip()[:140])
        e = env()
        e.run("--install")
        code, out = e.run("--sdsys-state")
        row("--sdsys-state needs no root and changes nothing", code == 0 and rd(e.cfg) == e.snap()[0], out.strip()[:100])

        # ---------------------------------------------------------------- S.106: what an older dev install left (the arm of the authenticator code and its PAM fences)
        e = env()
        e.make_legacy()
        row("LEGACY: an open arm of keyboard-interactive is told apart from both other forms", e.state() == {"sdsys-arm": "legacy"}, "%s" % e.state())
        before = e.snap()
        code, out = e.run("--clean-legacy")
        row("LEGACY: --clean-legacy REFUSES while the arm is still the code's, and changes no file (the lines are what keep that arm asking for the code)",
            code != 0 and e.snap() == before and "authenticator" in out, "exit %d: %s" % (code, out.strip()[:140]))
        code, out = e.run("--install")
        row("LEGACY: --install writes the arm CLOSED, not open, and takes every fence out of sshd's PAM file and the console files, leaving the originals byte for byte",
            code == 0 and e.arm() == ["Match User sdsys", "    DenyUsers sdsys"] and e.pristine_pam(), out.strip()[:140])
        e = env()
        e.make_legacy()
        code, out = e.run("--close-sdsys")
        row("LEGACY: --close-sdsys closes the arm and takes every fence out", code == 0 and e.state() == {"sdsys-arm": "closed"} and e.pristine_pam(), out.strip()[:140])
        e = env()
        e.make_legacy()
        code, out = e.run("--open-sdsys")
        rc, eff = effective(ctx["sshd"], e.cfg)
        row("LEGACY: --open-sdsys writes the password arm over it, takes every fence out, and the REAL sshd gives the password arm",
            code == 0 and e.state() == {"sdsys-arm": "open"} and e.pristine_pam() and eff.get("authenticationmethods") == "password", out.strip()[:140])
        e = env()
        e.make_legacy()
        code, out = e.run("--remove")
        row("LEGACY: --remove gives back the pristine config and PAM files, byte for byte", code == 0 and rd(e.cfg) == e.base_cfg and e.pristine_pam(), out.strip()[:140])
        # a machine whose arm is already right but whose fences were left (a failed earlier cleanup): --clean-legacy takes them out
        e = env()
        e.make_legacy()
        e.run("--install")
        wr(e.pamf, fenced(DEBIAN_PAM))
        for name in CONSOLE_FILES:
            wr(os.path.join(e.pamd, name), fenced(CONSOLE_PAM, opts=" local"))
        cfg_before = rd(e.cfg)
        code, out = e.run("--clean-legacy")
        row("LEGACY: --clean-legacy with the arm closed takes every fence out of sshd's PAM file and the console files, byte for byte, and leaves the config alone",
            code == 0 and e.pristine_pam() and rd(e.cfg) == cfg_before, out.strip()[:140])
        s1 = e.snap()
        code, out = e.run("--clean-legacy")
        row("LEGACY: ... and a second --clean-legacy changes nothing (the null case: nothing to clean is exit 0)", code == 0 and e.snap() == s1, out.strip()[:100])
        e = env()
        e.run("--install")
        e.run("--open-sdsys")
        s2 = e.snap()
        code, out = e.run("--clean-legacy")
        row("LEGACY: --clean-legacy on an arm that is open with the password changes nothing", code == 0 and e.snap() == s2 and e.state() == {"sdsys-arm": "open"}, out.strip()[:100])
        e = env()
        e.make_legacy()
        os.unlink(os.path.join(e.pamd, "gdm-password"))
        code, out = e.run("--install")
        row("LEGACY: a console service whose file is not there is passed over, and the others are cleaned",
            code == 0 and rd(os.path.join(e.pamd, "login")) == CONSOLE_PAM and rd(e.pamf) == DEBIAN_PAM, out.strip()[:140])

        # ---------------------------------------------------------------- the script's own text
        src = rd(ctx["helper"])
        arm = src[src.find("sdsys_arm_lines() {"):src.find("block_lines() {")]
        row("TEXT: the open arm and the closed arm are the only two forms written, and the closed one is exactly 'Match User sdsys' / 'DenyUsers sdsys'",
            '"Match User sdsys" \\\n      "    DenyUsers sdsys"' in arm and arm.count("Match User sdsys") == 2, "")
        op = src[src.find("  --open-sdsys)"):src.find("  --close-sdsys)")]
        row("TEXT: --open-sdsys takes its copy before it writes, writes the config, asks sshd, and puts the config back on a bad answer",
            0 < op.find('cp -- "$CONFIG" "$prev"') < op.find('commit_file "$tmp"') < op.find('verify_open "$sshd"') < op.find('cp -- "$prev" "$CONFIG"'), "")
        code_only = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))          # the history comments name what went
        row("TEXT S.106: nothing writes a PAM line or names the module any more (the code, not the history comments)",
            not any(w in code_only for w in ("pam_with_block", "pam_block_lines", "pam_session_lines", "module_ok", "PAM_MODULE", "SD_TOTP_MODULE", "--open-local", "--close-local", "--local-state")), "")
    finally:
        shutil.rmtree(base, ignore_errors=True)
    return rows


MUTANTS = [
    ("the open arm asks for keyboard-interactive again", '"    AuthenticationMethods password" \\', '"    AuthenticationMethods keyboard-interactive" \\'),
    ("the open arm leaves password authentication off", '"    PasswordAuthentication yes" \\', '"    PasswordAuthentication no" \\'),
    ("the open arm leaves PubkeyAuthentication on", '"    PubkeyAuthentication no" \\', '"    PubkeyAuthentication yes" \\'),
    ("the open arm leaves out GSSAPIAuthentication", '      "    GSSAPIAuthentication no" \\\n', ""),
    ("the open arm leaves out the ForceCommand", '      "    PermitTTY yes" \\\n      "    ForceCommand $SD_BIN"', '      "    PermitTTY yes"'),
    ("the open arm leaves out DisableForwarding", '      "    DisableForwarding yes" \\\n', ""),
    ("sshd is not asked after the write", 'if ! why=$(verify_open "$sshd"); then', "if false; then"),
    ("the config is not put back", '      cp -- "$prev" "$CONFIG"\n      fail "NOT OPENED', '      fail "NOT OPENED'),
    ("an AllowUsers that leaves sdsys out is not noticed", 'if [[ -n ${EFF[allowusers]-} ]] && ! list_admits user "${EFF[allowusers]}"; then', "if false; then"),
    ("an AllowGroups is not noticed", "  if [[ -n ${EFF[allowgroups]-} ]]; then\n", "  if false; then\n"),
    ("a DenyUsers is not noticed", 'if [[ -n ${EFF[denyusers]-} ]] && list_admits user "${EFF[denyusers]}"; then      # "admits" here means: the list names sdsys', "if false; then"),
    ("a DenyGroups is not noticed", "  if [[ -n ${EFF[denygroups]-} ]]; then\n", "  if false; then\n"),
    ("--open-sdsys works without a block", '    has_block || die "the SD block is not in $CONFIG: run --install first"\n', ""),
    ("--install forgets that the arm was open", "    [[ $(sdsys_mode_now) == open ]] && SDSYS_MODE=open     # an install over an open arm keeps it open", "    # an install over an open arm keeps it open"),
    ("--remove leaves the PAM fence", "    pam_has_block && remove_pam_block                    # the door is shut", "    # the door is shut"),
    ("the closed arm is not read back", 'if ! why=$(verify_closed "$sshd"); then', "if false; then"),
    # S.106: the legacy arm and its fences
    ("the legacy arm reads as closed", 'found = "legacy"', 'found = "closed"'),
    ("--clean-legacy does not refuse while the arm is the code's", '[[ $(sdsys_mode_now) != legacy ]] || die "the sdsys arm in', 'true || die "the sdsys arm in'),
    ("--clean-legacy leaves the console files", '    { pam_has_block || pam_has_session; } && remove_pam_block\n    local_remove_all\n    say "CLEAN', '    { pam_has_block || pam_has_session; } && remove_pam_block\n    say "CLEAN'),
    ("--clean-legacy leaves sshd's PAM file", '    { pam_has_block || pam_has_session; } && remove_pam_block\n    local_remove_all\n    say "CLEAN', '    local_remove_all\n    say "CLEAN'),
    ("--install leaves the fences", "    pam_has_block && remove_pam_block                      # S.106: the door is as it should be", "    # S.106: the door is as it should be"),
    ("--install leaves the console files' fences", "    local_remove_all                                       # and the console services' lines\n", ""),
    ("--close-sdsys leaves the console files' fences", "# S.106: an older install's PAM fences go, now that the door is shut\n    local_remove_all\n", "# S.106: an older install's PAM fences go, now that the door is shut\n"),
    ("--open-sdsys leaves the fences", "    pam_has_block && remove_pam_block\n    local_remove_all\n    exit 0\n    ;;\n\n  --close-sdsys)", "    exit 0\n    ;;\n\n  --close-sdsys)"),
    # S.157: root out of the Match Group arms
    ("the refusal arm catches root again", '"Match Group sdusers,!sdsys,!sdssh User *,!root"', '"Match Group sdusers,!sdsys,!sdssh"'),
    ("the fence stripper takes the session fence's text", '    $0 == b || $0 == sb { drop = 1; next }', '    $0 == b { drop = 1; next }'),
]


def selftest(ctx):
    say("test-sshd-sdsys --selftest")
    src = rd(HELPER_REAL)
    for name, old, new in MUTANTS:
        if src.count(old) != 1:
            say("  CANNOT RUN - mutant %s: its text occurs %d times (wanted 1)" % (name, src.count(old)))
            return 2
    tmp = tempfile.mkdtemp(prefix="sshd-sdsys-mut-")
    survivors = []
    try:
        base_ctx = dict(ctx, helper=os.path.join(tmp, "base.sh"))
        wr(base_ctx["helper"], src)
        rows = rows_for(base_ctx)
        bad = [r for r in rows if not r[1]]
        say("  control : the real script, %d rows, %d failed" % (len(rows), len(bad)))
        for label, ok, detail in bad:
            say("    FAIL %s | %s" % (label, detail))
        if bad or len(rows) < 40:
            return 1
        for i, (name, old, new) in enumerate(MUTANTS):
            path = os.path.join(tmp, "m%d.sh" % i)
            wr(path, src.replace(old, new))
            p = subprocess.run(["bash", "-n", path], capture_output=True, text=True)
            if p.returncode != 0:
                say("  CANNOT RUN - mutant %s does not parse:\n%s" % (name, p.stderr))
                return 2
            try:
                mrows = rows_for(dict(ctx, helper=path))
            except Exception as ex:
                mrows = [("the rows stopped: %s: %s" % (type(ex).__name__, ex), False, "")]
            caught = [r for r in mrows if not r[1]]
            say("  [%s] %-52s %s" % ("KILLED  " if caught else "SURVIVED", name, ("%d row(s), first: %s" % (len(caught), caught[0][0][:70])) if caught else ""))
            if not caught:
                survivors.append(name)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    say("")
    if survivors:
        say("test-sshd-sdsys --selftest: FAILED - %d of %d mutants survived: %s" % (len(survivors), len(MUTANTS), ", ".join(survivors)))
        return 1
    say("test-sshd-sdsys --selftest: PASSED - %d of %d mutants killed." % (len(MUTANTS), len(MUTANTS)))
    return 0


def main():
    say("test-sshd-sdsys")
    sshd = next((c for c in ("/usr/sbin/sshd", "/usr/bin/sshd", "/sbin/sshd") if os.access(c, os.X_OK)), None)
    keygen = shutil.which("ssh-keygen")
    if not sshd or not keygen:
        say("test-sshd-sdsys: CANNOT RUN - needs the real sshd and ssh-keygen (found: %s, %s)." % (sshd, keygen))
        return 2
    if not os.path.isfile(HELPER_REAL):
        say("test-sshd-sdsys: CANNOT RUN - missing %s" % HELPER_REAL)
        return 2
    ver = subprocess.run([sshd, "-V"], capture_output=True, text=True)
    say("  sshd     : %s (%s)" % (sshd, (ver.stderr or ver.stdout).strip().splitlines()[0] if (ver.stderr or ver.stdout).strip() else "version unknown"))
    ctx = {"sshd": sshd, "keygen": keygen, "helper": HELPER_REAL}
    if "--selftest" in sys.argv[1:]:
        return selftest(ctx)
    rows = rows_for(ctx)
    bad = 0
    for label, ok, detail in rows:
        say("  [%s] %s%s" % ("PASS" if ok else "FAIL", label, "" if ok or not detail else "\n         " + detail))
        bad += 0 if ok else 1
    say("")
    if len(rows) < 40:
        say("test-sshd-sdsys: FAILED - only %d rows ran; a test that did almost nothing must fail." % len(rows))
        return 1
    say("test-sshd-sdsys: %d passed, %d failed" % (len(rows) - bad, bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
