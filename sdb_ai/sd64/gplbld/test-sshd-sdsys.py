#!/usr/bin/env python3
# test-sshd-sdsys.py - the sshd side of the remote sdsys login (S.95 stage 2b): gplbld/ssh-forcecommand.sh --open-sdsys, --close-sdsys, --sdsys-state, and --install /
# --remove with the sdsys arm in its two forms and the fenced PAM lines.  The oracle is the REAL sshd of this machine (sshd -t, and sshd -T -C user=sdsys,...) on a scratch
# sshd_config with a throwaway host key, and a scratch PAM file - no root, no running sshd.  Written 1 Nov 2026.  test-ssh-forcecommand.py (34 rows) holds the older modes.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-sshd-sdsys.py
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-sshd-sdsys.py --selftest
#
# THE REFUSAL ROWS COMPARE BYTES: a refused --open-sdsys must leave the sshd_config AND the PAM file exactly as they were (the script puts both back when sshd's own answer is not
# the open arm's), and a row that only looked at the exit status would pass a script that refused and still left a half-open door.  The administrator's own settings that defeat
# the arm are real ones: UsePAM off, a Match Address block above ours, an Include that sets a keyword first, a DenyUsers, an AllowUsers / AllowGroups that leaves sdsys out.
#
# WHAT THIS CANNOT SHOW (the VM witness's): that a real client is asked for the code and then the password, a root-owned module (and one owned by ANOTHER user, which a non-root run
# cannot make), and the reload of a running sshd.  There is no mutant for the explicit "not a link" test of the module: stat reports a link's own mode (0777), so the write-bit test
# refuses a link anyway - the explicit test is belt and braces, and its row (a module that is a link is refused) still runs.
# Exit 0 every row passed, 1 a row failed (or a mutant survived), 2 it could not run (no sshd or ssh-keygen).  THE NULL CASE IS REFUSED: fewer than 40 rows is a failure.

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
    ("AuthenticationMethods", "keyboard-interactive"), ("KbdInteractiveAuthentication", "yes"), ("PasswordAuthentication", "no"), ("PubkeyAuthentication", "no"),
    ("HostbasedAuthentication", "no"), ("GSSAPIAuthentication", "no"), ("AuthorizedKeysFile", "none"), ("MaxAuthTries", "3"), ("DisableForwarding", "yes"),
    ("X11Forwarding", "no"), ("AllowAgentForwarding", "no"), ("AllowTcpForwarding", "no"), ("AllowStreamLocalForwarding", "no"), ("PermitTunnel", "no"),
    ("PermitUserRC", "no"), ("PermitTTY", "yes"),
]

DEBIAN_PAM = """# PAM configuration for the Secure Shell service

# Standard Un*x authentication.
@include common-auth

# Disallow non-root logins when /etc/nologin exists.
account    required     pam_nologin.so
@include common-account
session [success=ok ignore=ignore module_unknown=ignore default=bad]        pam_selinux.so close
"""
# 2 Nov 26 - S.105: the Fedora sample (auth substack password-auth) went with Fedora support.  This is an administrator's own Debian file in its place: a '#%PAM-1.0' header and
# an explicit "auth" line instead of "@include common-auth", the other branch of the fence's first-auth-line test, which no other row reaches.
CUSTOM_PAM = """#%PAM-1.0
auth       required     pam_unix.so
account    required     pam_nologin.so
account    required     pam_unix.so
"""
BASE_CONFIG = """# an ordinary sshd_config
Port 22
UsePAM yes
PermitRootLogin prohibit-password
Subsystem sftp /usr/lib/openssh/sftp-server
"""


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


class Env:
    """A scratch machine: an sshd_config with a host key, a PAM file, a module file, stub sd and refusal commands."""

    def __init__(self, base, n, ctx, config_extra="", pam=DEBIAN_PAM, groups="sdusers"):
        self.ctx = ctx
        self.d = os.path.join(base, "e%d" % n)
        os.makedirs(self.d)
        self.hostkey = os.path.join(self.d, "hostkey")
        subprocess.run([ctx["keygen"], "-q", "-t", "ed25519", "-N", "", "-f", self.hostkey], check=True, capture_output=True)
        self.cfg = os.path.join(self.d, "sshd_config")
        self.pamf = os.path.join(self.d, "pam_sshd")
        self.module = os.path.join(self.d, "pam_sdtotp.so")
        self.sd = os.path.join(self.d, "sd")
        self.ref = os.path.join(self.d, "ssh-forcecommand")
        wr(self.sd, "#!/bin/sh\nexit 0\n", 0o755)
        wr(self.ref, "#!/bin/sh\nexit 0\n", 0o755)
        wr(self.module, "not really a module\n", 0o644)
        self.base_cfg = "HostKey %s\n%s%s" % (self.hostkey, config_extra, BASE_CONFIG)
        wr(self.cfg, self.base_cfg)
        self.pam_text = pam
        wr(self.pamf, pam)
        self.groups = groups

    def run(self, mode, **env):
        e = dict(os.environ, SD_SSHD_CONFIG=self.cfg, SD_PAM_SSHD=self.pamf, SD_TOTP_MODULE=self.module, SD_SSHD_BIN=self.ctx["sshd"],
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
        return (rd(self.cfg), rd(self.pamf))


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
        pam0 = e.pam_text
        code, out = e.run("--install")
        row("install into a pristine config writes the CLOSED arm and leaves the PAM file alone (byte for byte, no backup of it)",
            code == 0 and e.arm() == ["Match User sdsys", "    DenyUsers sdsys"] and rd(e.pamf) == pam0 and not os.path.exists(e.pamf + ".before-sd"), out.strip()[:120])
        row("--sdsys-state: closed, no PAM fence", e.state() == {"sdsys-arm": "closed", "pam": "absent"}, "%s" % e.state())
        cfg_closed = rd(e.cfg)
        rc, alice_before = effective(ctx["sshd"], e.cfg, "alice")
        code, out = e.run("--open-sdsys")
        row("--open-sdsys on an installed block: exit 0", code == 0 and "OPENED" in out, out.strip()[:200])
        want = ["Match User sdsys"] + ["    %s %s" % kv for kv in ARM_KEYWORDS] + ["    ForceCommand %s" % e.sd]
        row("... the sdsys arm is exactly the 17 lines of the open arm (this test's own list)", e.arm() == want, "\n".join(e.arm()))
        row("... --sdsys-state: open, PAM fence present", e.state() == {"sdsys-arm": "open", "pam": "present"}, "%s" % e.state())
        rc, eff = effective(ctx["sshd"], e.cfg)
        # a build of sshd without GSSAPI does not print that keyword at all; where it does print it, it must say no
        bad = [(k, eff.get(k.lower()), v) for k, v in ARM_KEYWORDS if eff.get(k.lower(), "").lower() != v and not (k == "GSSAPIAuthentication" and k.lower() not in eff)] + \
              ([("forcecommand", eff.get("forcecommand"), e.sd)] if eff.get("forcecommand") != e.sd else [])
        row("... the REAL sshd, asked about sdsys, gives every one of those values (and UsePAM yes)", rc == 0 and not bad and eff.get("usepam", "").lower() == "yes", "%s" % bad)
        rc, alice_after = effective(ctx["sshd"], e.cfg, "alice")
        row("... and gives another user exactly what it gave before: the arm touches nobody else", rc == 0 and alice_before == alice_after, "")
        pam1 = rd(e.pamf)
        lines = pam1.splitlines()
        i = lines.index("@include common-auth")
        row("... the PAM fence is the two lines, the guard first, directly above the first auth line (@include common-auth)",
            lines[i - 4].startswith("# --- BEGIN SD sdsys authenticator code")
            and lines[i - 3] == "auth [success=1 default=ignore] pam_succeed_if.so quiet user notin sdsys"
            and lines[i - 2] == "auth required %s" % e.module
            and lines[i - 1] == "# --- END SD sdsys authenticator code ---", "\n".join(lines[max(0, i - 5):i + 1]))
        row("... nothing else in the PAM file changed (take the fence out and it is the original, byte for byte)",
            re.sub(r"# --- BEGIN SD sdsys.*?# --- END SD sdsys authenticator code ---\n", "", pam1, flags=re.S) == pam0, "")
        row("... the originals are kept once (sshd_config.before-sd holds the pristine config)", rd(e.cfg + ".before-sd") == e.base_cfg and rd(e.pamf + ".before-sd") == pam0, "")
        s_open = e.snap()
        code, out = e.run("--open-sdsys")
        row("a second --open-sdsys changes nothing (one block, one fence, the same bytes)", code == 0 and e.snap() == s_open and s_open[0].count("# --- END SD ssh-only model ---") == 1, "")
        code, out = e.run("--install")
        row("--install over the open arm keeps it open (and one block)", code == 0 and e.state()["sdsys-arm"] == "open" and rd(e.cfg).count("# --- END SD ssh-only model ---") == 1, out.strip()[:120])
        code, out = e.run("--check")
        row("--check reports the form and the fence, and prints the block it would write for that form",
            code == 0 and "sdsys arm         open" in out and "PAM fence         yes" in out and "AuthenticationMethods keyboard-interactive" in out, out.strip()[:100])
        code, out = e.run("--close-sdsys")
        row("--close-sdsys: the arm is closed again (the same bytes as the first install) and the PAM fence STAYS",
            code == 0 and rd(e.cfg) == cfg_closed and e.state() == {"sdsys-arm": "closed", "pam": "present"}, out.strip()[:120])
        rc, eff = effective(ctx["sshd"], e.cfg)
        row("... and the REAL sshd now denies sdsys network login", rc == 0 and "sdsys" in eff.get("denyusers", "").split(), "%s" % eff.get("denyusers"))
        e.run("--open-sdsys")
        code, out = e.run("--remove")
        row("--remove takes BOTH fences out and gives back the pristine files, byte for byte", code == 0 and rd(e.cfg) == e.base_cfg and rd(e.pamf) == pam0, out.strip()[:140])
        code, out = e.run("--remove")
        row("... and a second --remove is a clean no-op", code == 0, out.strip()[:100])

        e = env(pam=CUSTOM_PAM)
        e.run("--install")
        code, out = e.run("--open-sdsys")
        lines = rd(e.pamf).splitlines()
        row("an administrator's PAM file whose first auth line is a plain 'auth required pam_unix.so': the fence goes above that line and the '#%PAM-1.0' line stays first",
            code == 0 and lines[0] == "#%PAM-1.0" and lines[1].startswith("# --- BEGIN SD sdsys") and lines[4].startswith("# --- END SD sdsys") and lines[5].startswith("auth       required     pam_unix.so"), "\n".join(lines[:7]))

        # ---------------------------------------------------------------- refusals: both files exactly as they were
        def refused(label, e, mode="--open-sdsys", words=None, **kw):
            before = e.snap()
            existed = os.path.exists(e.pamf + ".before-sd")
            code, out = e.run(mode, **kw)
            same = e.snap() == before
            row("REFUSE: " + label + " - exit non-zero, sshd_config and PAM file byte for byte as they were",
                code != 0 and same and (words is None or words in out), "exit %d, %s: %s" % (code, "same" if same else "CHANGED", out.strip()[:200]))

        e = env()
        refused("--open-sdsys with no SD block in the config", e, words="--install first")
        e.run("--install")
        wr(e.cfg, rd(e.cfg).replace("UsePAM yes", "UsePAM no"))
        refused("UsePAM is off", e, words="UsePAM")

        e = env()
        e.run("--install")
        t = rd(e.cfg)
        i = t.index("# --- BEGIN SD ssh-only model")
        wr(e.cfg, t[:i] + "Match Address 192.0.2.0/24\n    PasswordAuthentication yes\n" + t[i:])
        refused("an administrator's Match Address block ABOVE ours sets PasswordAuthentication first", e, words="passwordauthentication")

        e = env()
        extra = os.path.join(e.d, "extra.conf")
        wr(extra, "Match all\n    AuthenticationMethods publickey\n")
        e.run("--install")
        wr(e.cfg, "Include %s\n" % extra + rd(e.cfg))
        refused("an Include at the top brings a Match block that sets AuthenticationMethods first", e, words="authenticationmethods")
        e = env()
        extra = os.path.join(e.d, "extra.conf")
        wr(extra, "AuthenticationMethods publickey\nPasswordAuthentication yes\n")
        e.run("--install")
        wr(e.cfg, "Include %s\n" % extra + rd(e.cfg))
        code, out = e.run("--open-sdsys")
        row("ALLOW: an Include that sets the same keywords GLOBALLY is no obstacle (a Match block overrides the global value; the real sshd says so)",
            code == 0 and e.state()["sdsys-arm"] == "open", out.strip()[:140])

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

        for what, mk in (("no module file", lambda e: os.unlink(e.module)),
                         ("a module that is a link", lambda e: (os.unlink(e.module), os.symlink(e.sd, e.module))),
                         ("a module others can write (0666)", lambda e: os.chmod(e.module, 0o666)),
                         ("a module group can write (0664)", lambda e: os.chmod(e.module, 0o664))):
            e = env()
            e.run("--install")
            mk(e)
            refused("%s" % what, e, words="PAM")
        e = env()
        e.run("--install")
        spaced = os.path.join(e.d, "with space")
        os.makedirs(spaced)
        shutil.copy(e.module, os.path.join(spaced, "m.so"))
        refused("a module path with a space in it (it would split the PAM line)", e, SD_TOTP_MODULE=os.path.join(spaced, "m.so"))
        e = env(pam="# a PAM file with no auth line\naccount required pam_permit.so\n")
        e.run("--install")
        refused("a PAM file with no auth line (not guessing where the code goes)", e, words="no auth line")
        e = env()
        e.run("--install")
        os.unlink(e.pamf)
        before = rd(e.cfg)
        code, out = e.run("--open-sdsys")
        row("REFUSE: no PAM file at all - exit non-zero and the sshd_config untouched", code != 0 and rd(e.cfg) == before, out.strip()[:140])
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

        # ---------------------------------------------------------------- a control: the refusals above are about the settings, not about everything
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
        os.chmod(e.module, 0o755)
        e.run("--install")
        code, out = e.run("--open-sdsys")
        row("ALLOW: a module at 0755 is fine", code == 0, out.strip()[:100])
        code, out = e.run("--sdsys-state")
        row("--sdsys-state needs no root and changes nothing", code == 0 and e.snap()[0] == rd(e.cfg), out.strip()[:100])

        # ---------------------------------------------------------------- the script's own text
        src = rd(ctx["helper"])
        arm = src[src.find("sdsys_arm_lines() {"):src.find("block_lines() {")]
        row("TEXT: the open arm and the closed arm are the only two forms, and the closed one is exactly 'Match User sdsys' / 'DenyUsers sdsys'",
            '"Match User sdsys" \\\n      "    DenyUsers sdsys"' in arm and arm.count("Match User sdsys") == 2, "")
        op = src[src.find("  --open-sdsys)"):src.find("  --close-sdsys)")]
        row("TEXT: --open-sdsys takes its copies before it writes, writes the PAM file, then the config, asks sshd, and puts both back on a bad answer",
            0 < op.find('cp -- "$CONFIG" "$prev"') < op.find('pam_commit_file "$ptmp"') < op.find('commit_file "$tmp"') < op.find('verify_open "$sshd"') < op.find('cp -- "$pprev" "$PAM_FILE"'), "")
    finally:
        shutil.rmtree(base, ignore_errors=True)
    return rows


MUTANTS = [
    ("the guard line is left out", "    \"auth [success=1 default=ignore] pam_succeed_if.so quiet user notin sdsys\" \\\n", ""),
    ("the open arm leaves PubkeyAuthentication on", '"    PubkeyAuthentication no" \\', '"    PubkeyAuthentication yes" \\'),
    ("the open arm leaves out GSSAPIAuthentication", '      "    GSSAPIAuthentication no" \\\n', ""),
    ("the open arm leaves out the ForceCommand", '      "    PermitTTY yes" \\\n      "    ForceCommand $SD_BIN"', '      "    PermitTTY yes"'),
    ("the open arm leaves out DisableForwarding", '      "    DisableForwarding yes" \\\n', ""),
    ("sshd is not asked after the write", 'if ! why=$(verify_open "$sshd"); then', "if false; then"),
    ("the config is not put back", '      cp -- "$prev" "$CONFIG"\n      cp -- "$pprev" "$PAM_FILE"\n      fail "NOT OPENED', '      cp -- "$pprev" "$PAM_FILE"\n      fail "NOT OPENED'),
    ("the PAM file is not put back", '      cp -- "$prev" "$CONFIG"\n      cp -- "$pprev" "$PAM_FILE"\n      fail "NOT OPENED', '      cp -- "$prev" "$CONFIG"\n      fail "NOT OPENED'),
    ("an AllowUsers that leaves sdsys out is not noticed", 'if [[ -n ${EFF[allowusers]-} ]] && ! list_admits user "${EFF[allowusers]}"; then', "if false; then"),
    ("an AllowGroups is not noticed", "  if [[ -n ${EFF[allowgroups]-} ]]; then\n", "  if false; then\n"),
    ("a DenyUsers is not noticed", 'if [[ -n ${EFF[denyusers]-} ]] && list_admits user "${EFF[denyusers]}"; then      # "admits" here means: the list names sdsys', "if false; then"),
    ("a DenyGroups is not noticed", "  if [[ -n ${EFF[denygroups]-} ]]; then\n", "  if false; then\n"),
    ("a module others can write is accepted", "(( (8#$mode & 8#022) == 0 ))", "true"),
    ("a module path with a space is accepted", "  [[ $PAM_MODULE =~ ^/[A-Za-z0-9._/-]+$ ]] || return 1\n", ""),
    ("--open-sdsys works without a block", '    has_block || die "the SD block is not in $CONFIG: run --install first"\n', ""),
    ("--install forgets that the arm was open", "    [[ $(sdsys_mode_now) == open ]] && SDSYS_MODE=open     # an install over an open arm keeps it open: the form is changed only by --open-sdsys and --close-sdsys\n", ""),
    ("--remove leaves the PAM fence", "    pam_has_block && remove_pam_block                    # the door is shut and sshd has the new config before the lines that ask for the code go\n", ""),
    ("the closed arm is not read back", 'if ! why=$(verify_closed "$sshd"); then', "if false; then"),
    ("the fence goes below the first auth line", "      while ((getline line < blk) > 0) print line\n      close(blk)\n      done = 1\n    }\n    { print }", "      done = 1\n    }\n    { print }\n    done == 1 && !wrote { while ((getline line < blk) > 0) print line; close(blk); wrote = 1 }"),
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
