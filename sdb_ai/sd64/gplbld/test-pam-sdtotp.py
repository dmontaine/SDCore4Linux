#!/usr/bin/env python3
# test-pam-sdtotp.py - SD's own PAM module for the remote sdsys login (S.95 stage 2): gplsrc/pam_sdtotp.c built as a shared object
# (-Wall -Wextra, hidden symbols but the two PAM entry points) and driven through a REAL PAM stack (pam_start_confdir, on a service file of
# this test's own) by gplbld/verify-pamtotp.c, which plays sshd: it answers the module's prompts, calls pam_authenticate and, when the
# whole login "worked", pam_setcred.  The store is a scratch directory enrolled with the real sd-totp command; the expected codes come
# from Python's own HMAC; the audit daemon is a datagram socket this test listens on.  Written 1 Nov 2026.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-pam-sdtotp.py
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-pam-sdtotp.py --selftest
#
# No sudo, no install, no sshd, no root.  Needs a C compiler, libssl-dev and libpam0g-dev (pam-devel); exit 2 without them.
# Exit 0 every row passed, 1 a row failed (or a mutant survived), 2 it could not run.
#
# WHAT THIS CANNOT SHOW (the VM witness's): that real sshd asks for the code before the password and calls pam_setcred after the
# whole login, that a store owned by root is read as root, and what a real ssh client sees.  The module reads the clock itself, so a row
# that needs a fresh code asks for the code of the step it wants, computed from the same clock a moment before; two successful logins in
# one scene use the current step's code and then the next step's, in that order, which the one-step window accepts across a step change.
# THE NULL CASE IS REFUSED: fewer than 40 rows is a failure, a compile that warns is a failure, a mutant's text must occur exactly once.

import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.dirname(HERE)
INC = os.path.join(SD64, "gplsrc")
MODULE_SRC = ("pam_sdtotp.c", "sd_totp_store.c", "sd_totp.c")
ALL_SRC = MODULE_SRC + ("sd_totp.h", "sd_totp_store.h", "sd_totp_cmd.c")
CFLAGS = ["-std=gnu17", "-Wall", "-Wextra", "-Wformat=2", "-Wno-format-nonliteral", "-O2"]

PAM_SUCCESS, PAM_AUTH_ERR, PAM_IGNORE = 0, 7, 25
PROMPT = "Verification code: "

# the oracle and the code helpers of test-totp-store.py, kept in step by hand (this file runs alone)
import base64
import hashlib
import hmac
import struct


def otp(b32, t):
    mac = hmac.new(base64.b32decode(b32), struct.pack(">Q", int(t) // 30), hashlib.sha1).digest()
    o = mac[19] & 15
    return "%06d" % ((int.from_bytes(mac[o:o + 4], "big") & 0x7fffffff) % 1000000)


def not_in_window(b32, t):
    ok = {otp(b32, t + d) for d in (-60, -30, 0, 30, 60)}
    n = 0
    while "%06d" % n in ok:
        n += 1
    return "%06d" % n


def say(text=""):
    print(text)


def cc_run(cc, args):
    return subprocess.run([cc] + args, capture_output=True, text=True)


def build_module(cc, tmp, src_dir, name):
    so = os.path.join(tmp, name + ".so")
    cmd = CFLAGS + ["-fPIC", "-fvisibility=hidden", "-shared", "-I" + src_dir] + [os.path.join(src_dir, f) for f in MODULE_SRC] + \
        ["-lpam", "-lcrypto", "-Wl,-z,relro,-z,now", "-Wl,--no-undefined", "-o", so]
    return so, cmd, cc_run(cc, cmd)


class Sink:
    """The audit daemon: a datagram socket the module sends to."""

    def __init__(self, path):
        self.s = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.s.bind(path)
        self.s.setblocking(False)

    def drain(self):
        out = []
        while True:
            try:
                out.append(self.s.recv(4096).decode("utf-8", "replace"))
            except BlockingIOError:
                return out

    def close(self):
        self.s.close()


class Scene:
    """One scratch store, one PAM service file and one audit socket."""

    def __init__(self, ctx, base, n, extra="delay_ms=0", enrol=True, audit=None):
        self.ctx = ctx
        self.d = os.path.join(base, "s%d" % n)
        self.store = os.path.join(self.d, "store")
        self.conf = os.path.join(self.d, "pam.d")
        self.sock = os.path.join(self.d, "audit.sock")
        os.makedirs(self.conf)
        with open(os.path.join(self.conf, "sdtest"), "w") as f:
            # the second line stands for the rest of sshd's stack (the password): without it a module that answers PAM_IGNORE leaves libpam saying PAM_PERM_DENIED
            f.write("auth required %s dir=%s audit=%s %s\nauth required pam_permit.so\n" % (ctx["so"], self.store, audit or self.sock, extra))
        self.sink = Sink(self.sock)
        self.secret = None
        self.recovery = []
        if enrol:
            self.enrol()

    def tool(self, *args, stdin=None, now=None):
        e = dict(os.environ, SD_TOTP_DIR=self.store, SD_TOTP_NOW=str(int(now if now is not None else time.time())))
        return subprocess.run([self.ctx["tool"]] + list(args), input=stdin, capture_output=True, text=True, env=e)

    def begin(self, now=None):
        p = self.tool("begin", "SD Core", "sdsys@testhost", now=now)
        m = re.search(r"secret=([A-Z2-7]{32})", p.stdout)
        return m.group(1) if m else None

    def enrol(self):
        """Enrolled two minutes ago, so that the codes of the next steps are all newer than the last used."""
        then = int(time.time()) - 120
        self.secret = self.begin(now=then)
        p = self.tool("confirm", stdin=otp(self.secret, then) + "\n", now=then)
        self.recovery = re.findall(r"recovery=(\S+)", p.stdout)

    def code(self, steps=0):
        return otp(self.secret, time.time() + 30 * steps)

    def wrong(self):
        return not_in_window(self.secret, time.time())

    def run(self, src, replies, mode="login", user="sdsys"):
        p = subprocess.run([self.ctx["harness"], self.conf, user, src, mode] + list(replies), capture_output=True, text=True, timeout=60)
        r = {"prompts": re.findall(r"^prompt=(.*)$", p.stdout, re.M), "echo": re.findall(r"^echo=(.*)$", p.stdout, re.M)}
        for k in ("authenticate", "setcred", "elapsed_ms"):
            m = re.search(r"^%s=(-?\d+)$" % k, p.stdout, re.M)
            r[k] = int(m.group(1)) if m else None
        r["audit"] = self.sink.drain()
        r["raw"] = (p.stdout + p.stderr).strip().replace("\n", " | ")[:200]
        return r

    def fail_path(self):
        return os.path.join(self.store, "sdsys.fail")

    def fail_text(self):
        try:
            return open(self.fail_path()).read()
        except FileNotFoundError:
            return ""

    def write_fail(self, text):
        with open(self.fail_path(), "w") as f:
            f.write(text)
        os.chmod(self.fail_path(), 0o600)

    def close(self):
        self.sink.close()


def audit_has(r, *needles):
    return any(all(n in line for n in needles) for line in r["audit"])


def rows_for(ctx):
    rows = []

    def row(label, ok, detail=""):
        rows.append((label, bool(ok), detail))

    base = tempfile.mkdtemp(prefix="totp-pam-")
    scenes = []
    cnt = [0]

    def scene(**kw):
        cnt[0] += 1
        s = Scene(ctx, base, cnt[0], **kw)
        scenes.append(s)
        return s

    try:
        # ---------------------------------------------------------------- a good login
        sc = scene()
        code = sc.code()
        r = sc.run("10.0.0.1", [code])
        row("a right code from a source: pam_authenticate and pam_setcred both succeed, and the ONE prompt is 'Verification code: ' with the answer hidden",
            r["authenticate"] == PAM_SUCCESS and r["setcred"] == PAM_SUCCESS and r["prompts"] == [PROMPT] and r["echo"] == ["off"], r["raw"])
        row("... two audit datagrams: the code accepted and the login succeeded, both naming the source",
            audit_has(r, "code accepted source=10.0.0.1") and audit_has(r, "login succeeded source=10.0.0.1") and len(r["audit"]) == 2, "%s" % r["audit"])
        row("... each is a datagram in the audit daemon's form (the magic, a '?', the text) with no code in it",
            all(l.startswith("SDAUDIT1 ? remote sdsys login ") and code not in l and "\n" not in l for l in r["audit"]), "%s" % r["audit"])
        row("... the whole login forgot the source: no 'src' line is left in sdsys.fail", "src " not in sc.fail_text() and "\nall 0 " in sc.fail_text(), sc.fail_text().replace("\n", " | "))
        r2 = sc.run("10.0.0.9", [code])
        row("the same code again, from another source: refused as a used code, and the answer is PAM_AUTH_ERR",
            r2["authenticate"] == PAM_AUTH_ERR and audit_has(r2, "refused source=10.0.0.9 reason=used code"), r2["raw"])
        r3 = sc.run("10.0.0.9", [sc.code(1)])
        row("... the next step's code is accepted (the window), from the same source", r3["authenticate"] == PAM_SUCCESS and r3["setcred"] == PAM_SUCCESS, r3["raw"])

        # ---------------------------------------------------------------- a wrong code
        sc = scene()
        r = sc.run("10.0.0.2", [sc.wrong()])
        row("a wrong code: PAM_AUTH_ERR, one audit line with the source and the reason 'wrong code', no setcred",
            r["authenticate"] == PAM_AUTH_ERR and r["setcred"] is None and audit_has(r, "remote sdsys login code refused source=10.0.0.2 reason=wrong code") and len(r["audit"]) == 1, r["raw"])
        row("... the attempt is counted: sdsys.fail has the source with a count of 1", re.search(r"\nsrc 10\.0\.0\.2 1 \d+ 0\n", sc.fail_text()) is not None, sc.fail_text().replace("\n", " | "))
        for what, text in (("five digits", "12345"), ("letters", "abcdef"), ("a long answer", "9" * 40)):
            r = sc.run("10.0.0.3", [text])
            row("an answer of %s is refused as a bad code" % what, r["authenticate"] == PAM_AUTH_ERR and audit_has(r, "reason=bad code"), r["raw"])
        r = sc.run("10.0.0.3", [])
        row("a client that gives no answer: refused, 'no answer', the prompt was shown", r["authenticate"] == PAM_AUTH_ERR and r["prompts"] == [PROMPT] and audit_has(r, "reason=no answer"), r["raw"])

        # ---------------------------------------------------------------- the lock
        sc = scene()
        for i in range(5):
            r = sc.run("10.0.0.4", [sc.wrong()])
        row("five wrong codes from one source were each asked for and refused", r["authenticate"] == PAM_AUTH_ERR and r["prompts"] == [PROMPT], r["raw"])
        good = sc.code()
        r = sc.run("10.0.0.4", [good])
        row("the sixth attempt, with the RIGHT code, is refused as locked and nothing is asked",
            r["authenticate"] == PAM_AUTH_ERR and r["prompts"] == [] and audit_has(r, "refused source=10.0.0.4 reason=locked"), r["raw"])
        r = sc.run("10.0.0.5", [good])
        row("... the locked source did not use the code up: another source gets in with it", r["authenticate"] == PAM_SUCCESS and r["setcred"] == PAM_SUCCESS, r["raw"])

        def set_last(sc, src, ago):
            t = re.sub(r"(\nsrc %s \d+ )\d+( \d+\n)" % re.escape(src), lambda m: "%s%d%s" % (m.group(1), int(time.time()) - ago, m.group(2)), sc.fail_text())
            sc.write_fail(t)

        set_last(sc, "10.0.0.4", 590)
        r = sc.run("10.0.0.4", [sc.code(1)])
        row("a lock whose last attempt was 590 seconds ago (of 600) still holds", r["authenticate"] == PAM_AUTH_ERR and r["prompts"] == [], r["raw"])
        set_last(sc, "10.0.0.4", 610)
        r = sc.run("10.0.0.4", [sc.code(1)])
        row("... one whose last attempt was 610 seconds ago has run out: the code is asked for and accepted, and the failures are forgotten",
            r["authenticate"] == PAM_SUCCESS and r["setcred"] == PAM_SUCCESS and "src 10.0.0.4 " not in sc.fail_text(), r["raw"] + " " + sc.fail_text().replace("\n", " | "))

        # ---------------------------------------------------------------- both factors count
        sc = scene()
        r1 = sc.run("10.0.0.6", [sc.code()], mode="auth")
        r2 = sc.run("10.0.0.6", [sc.code(1)], mode="auth")
        row("two logins whose code was right but whose password stage 'failed' (no setcred): both authenticate, and the failures are NOT forgotten (count 2, marked)",
            r1["authenticate"] == PAM_SUCCESS and r2["authenticate"] == PAM_SUCCESS and re.search(r"\nsrc 10\.0\.0\.6 2 \d+ [1-9]\d*\n", sc.fail_text()) is not None, sc.fail_text().replace("\n", " | "))
        for i in range(3):
            r = sc.run("10.0.0.6", [sc.wrong()], mode="auth")
        r = sc.run("10.0.0.6", [sc.wrong()], mode="auth")
        row("... three wrong codes after them make five, and the next attempt is locked: a right code does not undo what a wrong password cost", r["prompts"] == [] and audit_has(r, "reason=locked"), r["raw"])
        sc = scene()
        sc.run("10.0.0.7", [sc.code()], mode="auth")
        r = sc.run("10.0.0.7", [], mode="cred")
        row("setcred (the whole login worked) after a right code forgets the source", r["setcred"] == PAM_SUCCESS and "src 10.0.0.7 " not in sc.fail_text() and audit_has(r, "login succeeded source=10.0.0.7"), r["raw"])
        sc = scene()
        sc.run("10.0.0.8", [sc.code()], mode="auth")
        t = re.sub(r"(\nsrc 10\.0\.0\.8 \d+ \d+ )\d+\n", lambda m: "%s%d\n" % (m.group(1), int(time.time()) - 400), sc.fail_text())
        sc.write_fail(t)
        r = sc.run("10.0.0.8", [], mode="cred")
        row("setcred with a mark 400 seconds old (of 300) forgets nothing", "src 10.0.0.8 " in sc.fail_text() and not audit_has(r, "login succeeded"), sc.fail_text().replace("\n", " | "))
        sc = scene()
        r = sc.run("10.0.0.8", [], mode="cred")
        row("setcred with no mark at all changes nothing and still answers PAM_SUCCESS (it never fails a login)", r["setcred"] == PAM_SUCCESS and sc.fail_text() == "", r["raw"])

        # ---------------------------------------------------------------- recovery codes
        sc = scene()
        rc = sc.recovery[0]
        r = sc.run("10.0.0.10", [rc])
        row("a recovery code is accepted, and the audit line says a RECOVERY code was used",
            r["authenticate"] == PAM_SUCCESS and audit_has(r, "recovery code used source=10.0.0.10") and rc not in "".join(r["audit"]), r["raw"])
        r = sc.run("10.0.0.10", [rc])
        row("... and only once", r["authenticate"] == PAM_AUTH_ERR and audit_has(r, "reason=wrong code"), r["raw"])

        # ---------------------------------------------------------------- who and what is not asked
        sc = scene()
        r = sc.run("10.0.0.11", [sc.code()], user="alice")
        row("any user but sdsys: the module takes no part (the rest of the stack decides: here a permissive line), nothing is asked, audited or counted",
            r["authenticate"] == PAM_SUCCESS and r["prompts"] == [] and r["audit"] == [] and sc.fail_text() == "", r["raw"])
        sc = scene(enrol=False)
        r = sc.run("10.0.0.12", [])
        row("a store that does not exist (nobody enrolled): refused as not enrolled, nothing asked", r["authenticate"] == PAM_AUTH_ERR and r["prompts"] == [] and audit_has(r, "reason=not enrolled"), r["raw"])
        sc.begin()
        r = sc.run("10.0.0.12", [])
        row("a store with a pending secret only: still not enrolled", r["authenticate"] == PAM_AUTH_ERR and r["prompts"] == [] and audit_has(r, "reason=not enrolled"), r["raw"])
        sc = scene()
        os.chmod(sc.store, 0o755)
        r = sc.run("10.0.0.13", [sc.code()])
        row("a store directory open to others: refused as unsafe even with the right code, nothing asked", r["authenticate"] == PAM_AUTH_ERR and r["prompts"] == [] and audit_has(r, "reason=store unsafe"), r["raw"])
        os.chmod(sc.store, 0o700)
        sc = scene()
        sc.write_fail("not the memory of failed logins\n")
        r = sc.run("10.0.0.14", [sc.code()])
        row("a damaged sdsys.fail: refused as unsafe even with the right code (fail closed), nothing asked", r["authenticate"] == PAM_AUTH_ERR and r["prompts"] == [] and audit_has(r, "reason=store unsafe"), r["raw"])

        # ---------------------------------------------------------------- the global slow-down
        sc = scene()
        sc.write_fail("sdtotp 1\nall 31 %d\n" % (int(time.time()) - 10))
        r = sc.run("10.0.0.15", [sc.wrong()])
        row("more than 30 attempts from anywhere in the hour: a refusal says slow=yes", r["authenticate"] == PAM_AUTH_ERR and audit_has(r, "reason=wrong code slow=yes"), r["raw"])
        r = sc.run("10.0.0.15", [sc.code()])
        row("... and a right code is still accepted (a slow-down, not a lock-out)", r["authenticate"] == PAM_SUCCESS, r["raw"])
        sc = scene()
        r = sc.run("10.0.0.16", [sc.wrong()])
        row("without it a refusal does not say slow=yes", "slow=yes" not in "".join(r["audit"]), "%s" % r["audit"])

        # ---------------------------------------------------------------- the wait after a failure
        sc = scene(extra="delay_ms=400")
        r = sc.run("10.0.0.17", [sc.wrong()])
        row("a failure waits (delay_ms=400; libpam varies a wait by a quarter either way, so at least 280 ms)",
            r["authenticate"] == PAM_AUTH_ERR and r["elapsed_ms"] is not None and r["elapsed_ms"] >= 280, "%s ms" % r["elapsed_ms"])
        r = sc.run("10.0.0.17", [sc.code()])
        row("... a success does not", r["authenticate"] == PAM_SUCCESS and r["elapsed_ms"] is not None and r["elapsed_ms"] < 300, "%s ms" % r["elapsed_ms"])
        sc = scene(extra="delay_ms=0 bogus=1 delay_ms=x")
        r = sc.run("10.0.0.18", [sc.code()])
        row("an argument the module does not know, or a bad delay, is ignored: the login still works", r["authenticate"] == PAM_SUCCESS, r["raw"])
        sc = scene(audit="/nonexistent-dir/audit.sock")
        r = sc.run("10.0.0.19", [sc.code()])
        row("an audit daemon that is not there does not stop a login (the syslog line is the other record)", r["authenticate"] == PAM_SUCCESS and r["setcred"] == PAM_SUCCESS, r["raw"])

        # ---------------------------------------------------------------- what the source can be
        sc = scene()
        r = sc.run("1.2.3.4\nevil;x", [sc.wrong()])
        row("a source with a newline and a ';' in it is kept as '1.2.3.4?evil?x': one audit line, no control characters",
            audit_has(r, "source=1.2.3.4?evil?x") and all("\n" not in l for l in r["audit"]) and "src 1.2.3.4?evil?x 1 " in sc.fail_text(), "%s" % r["audit"])
        r = sc.run("a" * 200, [sc.wrong()])
        row("a source of 200 characters is cut to 63", re.search(r"\nsrc a{63} 1 ", sc.fail_text()) is not None, sc.fail_text().replace("\n", " | ")[:120])
        r = sc.run("-", [sc.wrong()])
        row("no source at all is 'unknown'", audit_has(r, "source=unknown"), "%s" % r["audit"])
        sc = scene()
        now = int(time.time())
        lines = ["sdtotp 1", "all 3 %d" % now] + ["src 10.1.%d.%d 1 %d 0" % (i // 250, i % 250, now - 100 + i) for i in range(64)]
        sc.write_fail("\n".join(lines) + "\n")
        r = sc.run("10.2.2.2", [sc.wrong()])
        t = sc.fail_text()
        row("a full table (64 sources) makes room for a new one by dropping the one tried longest ago, and stays 64",
            r["authenticate"] == PAM_AUTH_ERR and t.count("\nsrc ") == 64 and "src 10.2.2.2 1 " in t and "src 10.1.0.0 " not in t, "%d sources" % t.count("\nsrc "))
        sc = scene()
        sc.write_fail("sdtotp 1\nall 1 %d\nsrc 10.3.3.3 2 %d 0\n" % (int(time.time()), int(time.time()) - 90000))
        r = sc.run("10.3.3.3", [sc.wrong()])
        row("a source nobody tried for a day is forgotten (an old count of 2 starts again at 1, not 3)", r["prompts"] == [PROMPT] and "src 10.3.3.3 1 " in sc.fail_text(), sc.fail_text().replace("\n", " | "))

        # ---------------------------------------------------------------- the file itself and its source
        nm = subprocess.run(["nm", "-D", "--defined-only", ctx["so"]], capture_output=True, text=True)
        syms = sorted(l.split()[-1] for l in nm.stdout.splitlines() if l.strip())
        row("the shared object exports pam_sm_authenticate and pam_sm_setcred and nothing else", syms == ["pam_sm_authenticate", "pam_sm_setcred"], "%s" % syms)
        src = open(os.path.join(ctx["src_dir"], "pam_sdtotp.c"), encoding="utf-8").read()
        code_only = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
        defs = open(os.path.join(ctx["src_dir"], "sddefs.h"), encoding="utf-8").read() if os.path.exists(os.path.join(ctx["src_dir"], "sddefs.h")) else \
            open(os.path.join(INC, "sddefs.h"), encoding="utf-8").read()
        row("TEXT: the audit socket path and the datagram magic are the audit daemon's (gplsrc/sddefs.h)",
            re.search(r'#define SD_AUDIT_SOCK "([^"]+)"', defs).group(1) in code_only and re.search(r'#define AUDIT_MAGIC "([^"]+)"', defs).group(1) in code_only, "")
        row("TEXT: the module prints nothing and reads no environment", re.search(r"(?<![sn])printf\(|\bputs\(|\bfputs\(|\bfprintf\(|getenv", code_only) is None, "")
        row("TEXT: the code is asked for with the answer hidden (ECHO_OFF, never ECHO_ON), and the answer is wiped before it is freed",
            "PAM_PROMPT_ECHO_OFF" in code_only and "PAM_PROMPT_ECHO_ON" not in code_only and code_only.find("OPENSSL_cleanse(resp") != -1 and code_only.find("OPENSSL_cleanse(resp") < code_only.find("free(resp)"), "")
        a = code_only[code_only.find("int pam_sm_authenticate"):code_only.find("int pam_sm_setcred")]
        order = [a.find(k) for k in ("who(pamh, src)", "sd_totps_info(", "sd_totps_attempt(", "pam_prompt(", "sd_totps_check(")]
        row("TEXT: authenticate asks who, then what is enrolled, then counts the attempt, then prompts, then checks - in that order", all(o >= 0 for o in order) and order == sorted(order), "%s" % order)
        row("TEXT: authenticate never forgets failures itself (only setcred does), and setcred answers PAM_SUCCESS for a user it handles", "sd_totps_clear" not in a and "return PAM_SUCCESS;" in code_only[code_only.find("int pam_sm_setcred"):], "")
    finally:
        for s in scenes:
            s.close()
        shutil.rmtree(base, ignore_errors=True)
    return rows


MUTANTS = [
    ("any user is asked", "pam_sdtotp.c", " || strcmp(user, SD_USER) != 0", ""),
    ("not enrolled is asked anyway", "pam_sdtotp.c", '    if (!info.has_active) return refuse(pamh, &o, 0, src, "not enrolled");\n', ""),
    ("attempts are not counted", "pam_sdtotp.c", "r = sd_totps_attempt(o.dir, now, src, &slow);", "r = SD_TOTPS_OK;"),
    ("a locked source is not refused as locked", "pam_sdtotp.c", '    if (r == SD_TOTPS_LOCKED) return refuse(pamh, &o, slow, src, "locked");\n', ""),
    ("the right code forgets the failures at once", "pam_sdtotp.c", "(void)sd_totps_ok(o.dir, now, src);", "(void)sd_totps_ok(o.dir, now, src);\n        (void)sd_totps_clear(o.dir, now, src);"),
    ("no mark is left for setcred", "pam_sdtotp.c", "        (void)sd_totps_ok(o.dir, now, src);\n", ""),
    ("the code is echoed", "pam_sdtotp.c", "PAM_PROMPT_ECHO_OFF", "PAM_PROMPT_ECHO_ON"),
    ("the answer is not wiped", "pam_sdtotp.c", "    OPENSSL_cleanse(resp, strlen(resp));\n", ""),
    ("a wrong code is accepted", "pam_sdtotp.c", "if (r == SD_TOTPS_OK || r == SD_TOTPS_USED) {", "if (r == SD_TOTPS_OK || r == SD_TOTPS_USED || r == SD_TOTPS_WRONG) {"),
    ("there is no wait after a failure", "pam_sdtotp.c", "    if (usec != 0) (void)pam_fail_delay(pamh, (unsigned int)usec);\n", ""),
    ("the slow-down is not said", "pam_sdtotp.c", 'slow ? " slow=yes" : ""', '""'),
    ("setcred never forgets", "pam_sdtotp.c", "if (sd_totps_clear(o.dir, (uint64_t)time(NULL), src) == SD_TOTPS_OK) {", "if (0) {"),
    ("the source is not cleaned", "sd_totp_store.c", "c == '_' || c == '-') ? c : '?';", "c == '_' || c == '-') ? c : c;"),
    ("the lock lasts ten times as long", "sd_totp_store.h", "#define SD_TOTPS_LOCK_SECS      600", "#define SD_TOTPS_LOCK_SECS      6000"),
    ("six attempts before the lock", "sd_totp_store.h", "#define SD_TOTPS_FAIL_MAX       5", "#define SD_TOTPS_FAIL_MAX       6"),
    ("old sources are never forgotten", "sd_totp_store.c", "if (f.r[i].last + SD_TOTPS_FORGET_SECS < now) fail_drop(&f, i);", ";"),
    ("a stale mark still forgets", "sd_totp_store.c", " && now - f.r[i].ok <= SD_TOTPS_OK_SECS", ""),
    ("the global count never slows", "sd_totp_store.c", "    if (slow != NULL) *slow = f.all_count > SD_TOTPS_GLOBAL_MAX;\n    rc = store_fail(dfd, &f);", "    rc = store_fail(dfd, &f);"),
]


def prepare(cc, tmp, src_dir, tag):
    """Builds the module from src_dir; the harness and the sd-totp command are always the real ones (built once by the caller)."""
    so, cmd, p = build_module(cc, tmp, src_dir, tag)
    return so, cmd, p


def selftest(cc, harness, tool, tmp):
    say("test-pam-sdtotp --selftest")
    originals = {f: open(os.path.join(INC, f), encoding="utf-8").read() for f in ALL_SRC}
    for name, fname, old, new in MUTANTS:
        if originals[fname].count(old) != 1:
            say("  CANNOT RUN - mutant %s: its text occurs %d times in %s (wanted 1)" % (name, originals[fname].count(old), fname))
            return 2
    survivors = []
    d0 = os.path.join(tmp, "src-base")
    os.makedirs(d0)
    for f, t in originals.items():
        open(os.path.join(d0, f), "w", encoding="utf-8").write(t)
    shutil.copy(os.path.join(INC, "sddefs.h"), d0)
    so, cmd, p = build_module(cc, tmp, d0, "base")
    if p.returncode != 0 or p.stderr:
        say("  CANNOT RUN - the unmutated copy does not build cleanly:\n" + p.stderr)
        return 2
    rows = rows_for({"so": so, "harness": harness, "tool": tool, "src_dir": d0})
    bad = [r for r in rows if not r[1]]
    say("  control : the real source, %d rows, %d failed" % (len(rows), len(bad)))
    for label, ok, detail in bad:
        say("    FAIL %s | %s" % (label, detail))
    if bad or len(rows) < 40:
        return 1
    for i, (name, fname, old, new) in enumerate(MUTANTS):
        d = os.path.join(tmp, "m%d" % i)
        os.makedirs(d)
        for f, t in originals.items():
            open(os.path.join(d, f), "w", encoding="utf-8").write(t.replace(old, new) if f == fname else t)
        shutil.copy(os.path.join(INC, "sddefs.h"), d)
        so, cmd, p = build_module(cc, tmp, d, "mut%d" % i)
        if p.returncode != 0:
            say("  CANNOT RUN - mutant %s does not compile:\n%s" % (name, p.stderr))
            return 2
        try:
            mrows = rows_for({"so": so, "harness": harness, "tool": tool, "src_dir": d})
        except Exception as ex:
            mrows = [("the rows stopped: %s: %s" % (type(ex).__name__, ex), False, "")]
        caught = [r for r in mrows if not r[1]]
        say("  [%s] %-44s %s" % ("KILLED  " if caught else "SURVIVED", name, ("%d row(s), first: %s" % (len(caught), caught[0][0][:80])) if caught else ""))
        if not caught:
            survivors.append(name)
        shutil.rmtree(d, ignore_errors=True)
    say("")
    if survivors:
        say("test-pam-sdtotp --selftest: FAILED - %d of %d mutants survived: %s" % (len(survivors), len(MUTANTS), ", ".join(survivors)))
        return 1
    say("test-pam-sdtotp --selftest: PASSED - %d of %d mutants killed." % (len(MUTANTS), len(MUTANTS)))
    return 0


def main():
    cc = shutil.which("cc") or shutil.which("gcc")
    say("test-pam-sdtotp")
    say("  compiler : %s" % (cc or "(none found)"))
    if cc is None:
        say("test-pam-sdtotp: CANNOT RUN - no C compiler on PATH.")
        return 2
    for f in ALL_SRC + ("sddefs.h",):
        if not os.path.isfile(os.path.join(INC, f)):
            say("test-pam-sdtotp: CANNOT RUN - missing %s" % os.path.join(INC, f))
            return 2
    if not os.path.isfile("/usr/include/security/pam_modules.h"):
        say("test-pam-sdtotp: CANNOT RUN - the PAM headers are not installed (libpam0g-dev, or pam-devel).")
        return 2
    tmp = tempfile.mkdtemp(prefix="totp-pam-bin-")
    try:
        harness = os.path.join(tmp, "verify-pamtotp")
        p = cc_run(cc, CFLAGS + [os.path.join(HERE, "verify-pamtotp.c"), "-lpam", "-o", harness])
        if p.returncode != 0 or p.stderr:
            say("test-pam-sdtotp: CANNOT RUN - the harness did not build cleanly:\n" + p.stdout + p.stderr)
            return 2
        tool = os.path.join(tmp, "sd-totp")
        p = cc_run(cc, CFLAGS + ["-I" + INC, os.path.join(INC, "sd_totp_cmd.c"), os.path.join(INC, "sd_totp_store.c"), os.path.join(INC, "sd_totp.c"), "-lcrypto", "-o", tool])
        if p.returncode != 0 or p.stderr:
            say("test-pam-sdtotp: CANNOT RUN - sd-totp did not build cleanly:\n" + p.stdout + p.stderr)
            return 2
        if "--selftest" in sys.argv[1:]:
            return selftest(cc, harness, tool, tmp)
        so, cmd, p = build_module(cc, tmp, INC, "pam_sdtotp")
        say("  module   : %s" % " ".join(cmd))
        if p.returncode != 0:
            say("test-pam-sdtotp: CANNOT RUN - the module did not compile:\n" + p.stdout + p.stderr)
            return 2
        if p.stderr:
            say("test-pam-sdtotp: FAILED - the module compiled with a warning:\n" + p.stderr)
            return 1
        rows = rows_for({"so": so, "harness": harness, "tool": tool, "src_dir": INC})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    bad = 0
    for label, ok, detail in rows:
        say("  [%s] %s%s" % ("PASS" if ok else "FAIL", label, "" if ok or not detail else "\n         " + detail))
        bad += 0 if ok else 1
    say("")
    if len(rows) < 40:
        say("test-pam-sdtotp: FAILED - only %d rows ran; a test that did almost nothing must fail." % len(rows))
        return 1
    say("test-pam-sdtotp: %d passed, %d failed" % (len(rows) - bad, bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
