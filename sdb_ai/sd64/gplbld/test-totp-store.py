#!/usr/bin/env python3
# test-totp-store.py - the root-only store of the sdsys user's second factor (S.95 stage 1):
# gplsrc/sd_totp_store.c and the sd-totp command (gplsrc/sd_totp_cmd.c), built here with
# -Wall -Wextra and driven as a black box on a scratch store.  Written 1 Nov 2026.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-totp-store.py
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-totp-store.py --selftest
#
# No sudo, no install, no sd.  Needs a C compiler and libssl-dev.  Exit 0 every row passed,
# 1 a row failed (or, with --selftest, a mutant survived), 2 it could not run.
#
# THE EXPECTED CODES COME FROM PYTHON, NOT FROM THE ENGINE: the oracle below is hmac + hashlib
# (RFC 4226 in six lines), so a code the command accepts was computed twice, by two programs.
# The clock is SD_TOTP_NOW and the store is SD_TOTP_DIR, which the command honours only when it
# is not root.  Every row prints what it did (the command, its exit and its output) in its detail.
#
# WHAT THIS CANNOT SHOW: a file or directory owned by ANOTHER user (a non-root run cannot make
# one) - that check, and a real root run on /etc/sdcore/totp, are the VM witness's.  A root run
# is played by `unshare -Ur` to show that the command then ignores both knobs.
#
# THE NULL CASE IS REFUSED: fewer than 60 rows is a failure, a compile that warns is a failure,
# and every mutant's text must occur exactly once in the source it changes.

import base64
import hashlib
import hmac
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.dirname(HERE)
INC = os.path.join(SD64, "gplsrc")
SRC = ("sd_totp_cmd.c", "sd_totp_store.c", "sd_totp.c")
HDR = ("sd_totp.h", "sd_totp_store.h")
CFLAGS = ["-std=gnu17", "-Wall", "-Wextra", "-Wformat=2", "-Wno-format-nonliteral", "-O2"]

T0 = 1700000010                    # the frozen clock; its step is T0 // 30
CODE = re.compile(r"^[A-Z2-7]{5}-[A-Z2-7]{5}$")


def say(text=""):
    print(text)


def otp(b32, t):
    key = base64.b32decode(b32)
    mac = hmac.new(key, struct.pack(">Q", t // 30), hashlib.sha1).digest()
    o = mac[19] & 15
    return "%06d" % ((int.from_bytes(mac[o:o + 4], "big") & 0x7fffffff) % 1000000)


def not_in_window(b32, t):
    """A six-digit code that is none of the three the window accepts at time t."""
    ok = {otp(b32, t + d) for d in (-30, 0, 30)}
    n = 0
    while "%06d" % n in ok:
        n += 1
    return "%06d" % n


def parse(out):
    d = {}
    for line in out.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            d.setdefault(k, []).append(v)
    return d


class Store:
    """One scratch store and the command that drives it; every output is kept so that a row can ask whether a secret was ever printed again."""

    def __init__(self, tool, base):
        self.tool = tool
        self.base = base
        self.dir = os.path.join(base, "store")
        self.outputs = []

    def run(self, *args, stdin=None, now=T0, env=None, tool=None):
        e = dict(os.environ, SD_TOTP_DIR=self.dir, SD_TOTP_NOW=str(now))
        e.update(env or {})
        p = subprocess.run([tool or self.tool] + list(args), input=stdin, capture_output=True, text=True, env=e,
                           preexec_fn=lambda: os.umask(0))
        self.outputs.append(p.stdout + p.stderr)
        return p.returncode, p.stdout, p.stderr

    def names(self):
        return sorted(os.listdir(self.dir)) if os.path.isdir(self.dir) else []

    def path(self, name):
        return os.path.join(self.dir, name)

    def text(self, name):
        try:
            with open(self.path(name), encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return ""                   # a row that wants the file then fails on its comparison, instead of the whole run stopping

    def enrol(self, now=T0):
        """begin, then confirm with the right code.  Returns (secret, recovery codes)."""
        _, out, _ = self.run("begin", "SD Core", "sdsys@testhost", now=now)
        secret = parse(out)["secret"][0]
        _, out, _ = self.run("confirm", stdin=otp(secret, now) + "\n", now=now)
        return secret, parse(out).get("recovery", [])


def build(cc, tmp, src_dir, name):
    exe = os.path.join(tmp, name)
    cmd = [cc] + CFLAGS + ["-I" + src_dir] + [os.path.join(src_dir, f) for f in SRC] + ["-lcrypto", "-o", exe]
    p = subprocess.run(cmd, capture_output=True, text=True)
    return exe, cmd, p


def mode(path):
    return os.stat(path).st_mode & 0o777


def rows_for(tool, src_dir):
    """Returns the rows (label, ok, detail) for the command `tool`, whose source is in src_dir."""
    rows = []

    def row(label, ok, detail=""):
        rows.append((label, bool(ok), detail))

    def cmd_text(r):
        return "exit %d: %s" % (r[0], (r[1] + r[2]).strip().replace("\n", " | ")[:140])

    base = tempfile.mkdtemp(prefix="totp-store-")
    n = [0]

    def fresh():
        n[0] += 1
        d = os.path.join(base, "s%d" % n[0])
        os.makedirs(d)
        return Store(tool, d)

    try:
        # ---------------------------------------------------------------- nothing enrolled, and a pending secret
        st = fresh()
        r = st.run("status")
        row("status of a store that does not exist: nothing active, nothing pending, and the directory is not made",
            r[0] == 0 and r[1] == "active=no\npending=no\nrecovery=0\n" and not os.path.exists(st.dir), cmd_text(r))
        r = st.run("check", stdin="123456\n")
        row("check with nothing enrolled is refused as nothing (exit 1), not as wrong", r[0] == 1 and "refused=nothing" in r[1], cmd_text(r))
        r = st.run("confirm", stdin="123456\n")
        row("confirm with nothing pending is refused as nothing", r[0] == 1 and "refused=nothing" in r[1], cmd_text(r))
        r = st.run("recovery")
        row("new recovery codes with nothing enrolled are refused as nothing", r[0] == 1 and "refused=nothing" in r[1], cmd_text(r))
        r = st.run("begin", "SD Core", "sdsys@testhost")
        kv = parse(r[1])
        secret = kv.get("secret", [""])[0]
        uri = kv.get("uri", [""])[0]
        row("begin: a secret of 32 base32 characters and a link that carries it, issuer, SHA1, 6 digits, 30 s",
            r[0] == 0 and re.fullmatch(r"[A-Z2-7]{32}", secret) is not None and ("secret=" + secret) in uri and uri.startswith("otpauth://totp/SD%20Core:sdsys@testhost?")
            and "digits=6" in uri and "period=30" in uri and "algorithm=SHA1" in uri, cmd_text(r))
        row("begin made the directory 0700 and one file, sdsys.pending, 0600, and nothing else (no .new- leftovers)",
            mode(st.dir) == 0o700 and st.names() == ["sdsys.pending"] and mode(st.path("sdsys.pending")) == 0o600, "%s %s" % (oct(mode(st.dir)), st.names()))
        r = st.run("status")
        row("status: pending, not active", r[1] == "active=no\npending=yes\nrecovery=0\n", cmd_text(r))
        r = st.run("begin", "SD Core", "sdsys@testhost")
        secret2 = parse(r[1]).get("secret", [""])[0]
        row("a second begin makes a NEW pending secret (different) and still one pending file", secret2 != secret and st.names() == ["sdsys.pending"], cmd_text(r))
        for what, args in (("an empty issuer", ("begin", "", "a")), ("an empty account", ("begin", "SD", "")), ("a newline in the account", ("begin", "SD", "a\nb")),
                           ("an issuer of 65 bytes", ("begin", "x" * 65, "a")), ("a byte above 0x7e", ("begin", "SD", "caf\xe9"))):
            r = st.run(*args)
            row("begin refuses %s (exit 1, refused=bad)" % what, r[0] == 1 and "refused=bad" in r[1], cmd_text(r))
        r = st.run("begin", "SD", "a", "extra")
        row("begin with a stray argument is a usage error (exit 2)", r[0] == 2, cmd_text(r))

        # ---------------------------------------------------------------- confirming
        st = fresh()
        _, out, _ = st.run("begin", "SD Core", "sdsys@testhost")
        secret = parse(out)["secret"][0]
        wrong = not_in_window(secret, T0)
        r = st.run("confirm", stdin=wrong + "\n")
        row("confirm with a wrong code: refused=wrong, exit 1, still pending, the failure counted (tries 1), nothing active",
            r[0] == 1 and "refused=wrong" in r[1] and st.names() == ["sdsys.pending"] and "tries 1" in st.text("sdsys.pending"), cmd_text(r))
        for what, text in (("five digits", "12345"), ("seven digits", "1234567"), ("letters", "abcdef"), ("nothing", "")):
            r = st.run("confirm", stdin=text + "\n")
            row("confirm with %s: refused=bad, and NOT counted as a try" % what, r[0] == 1 and "refused=bad" in r[1] and "tries 1" in st.text("sdsys.pending"), cmd_text(r))
        r = st.run("confirm", stdin="")
        row("confirm with no input at all: refused=bad", r[0] == 1 and "refused=bad" in r[1], cmd_text(r))
        for i in range(2, 5):
            st.run("confirm", stdin=wrong + "\n")
        r = st.run("confirm", stdin=wrong + "\n")
        row("the fifth wrong code throws the pending secret away: refused=discarded and the file is gone",
            r[0] == 1 and "refused=discarded" in r[1] and st.names() == [], cmd_text(r))
        r = st.run("confirm", stdin=otp(secret, T0) + "\n")
        row("... and the right code for the thrown-away secret then finds nothing pending", r[0] == 1 and "refused=nothing" in r[1], cmd_text(r))

        st = fresh()
        _, out, _ = st.run("begin", "SD Core", "sdsys@testhost")
        secret = parse(out)["secret"][0]
        code = otp(secret, T0)
        r = st.run("confirm", stdin=code[:3] + " " + code[3:] + "\n")
        kv = parse(r[1])
        rcodes = kv.get("recovery", [])
        row("confirm with the right code typed as '123 456': ok, and EIGHT recovery codes in the form XXXXX-XXXXX, all different",
            r[0] == 0 and r[1].startswith("ok\n") and len(rcodes) == 8 and len(set(rcodes)) == 8 and all(CODE.match(c) for c in rcodes), cmd_text(r))
        row("... the store is now sdsys.active and sdsys.recovery (0600), the pending file is gone, the directory still 0700",
            st.names() == ["sdsys.active", "sdsys.recovery"] and all(mode(st.path(f)) == 0o600 for f in st.names()) and mode(st.dir) == 0o700, "%s" % st.names())
        active = st.text("sdsys.active")
        row("... sdsys.active holds the secret that begin showed (not another) and the step of the code just used",
            active == "sdtotp 1\nsecret %s\nlast %d\n" % (secret, T0 // 30), repr(active))
        rtext = st.text("sdsys.recovery")
        row("... sdsys.recovery holds a salt and eight 64-digit hashes, and NO recovery code and NOT the secret in the clear",
            re.fullmatch(r"sdtotp 1\nsalt [0-9a-f]{32}\n(code [0-9a-f]{64}\n){8}", rtext) is not None
            and not any(c in rtext or c.replace("-", "") in rtext for c in rcodes) and secret not in rtext, "%d bytes" % len(rtext))
        r = st.run("status")
        row("status: active, eight recovery codes", r[1] == "active=yes\npending=no\nrecovery=8\n", cmd_text(r))

        # ---------------------------------------------------------------- checking a code
        r = st.run("check", stdin=code + "\n")
        row("check: the code that confirmed is already used (refused=replay)", r[0] == 1 and "refused=replay" in r[1], cmd_text(r))
        r = st.run("check", stdin=otp(secret, T0 + 30) + "\n", now=T0 + 30)
        row("check: the next step's code is accepted (ok), and the step is recorded",
            r[0] == 0 and r[1] == "ok\n" and st.text("sdsys.active").endswith("last %d\n" % (T0 // 30 + 1)), cmd_text(r))
        r = st.run("check", stdin=otp(secret, T0 + 30) + "\n", now=T0 + 30)
        row("check: ... and it cannot be used again", r[0] == 1 and "refused=replay" in r[1], cmd_text(r))
        r = st.run("check", stdin=otp(secret, T0) + "\n", now=T0 + 30)
        row("check: an OLDER step's code after a newer one was used is refused (refused=replay)", r[0] == 1 and "refused=replay" in r[1], cmd_text(r))
        r = st.run("check", stdin=not_in_window(secret, T0 + 60) + "\n", now=T0 + 60)
        row("check: a wrong code is refused (refused=wrong)", r[0] == 1 and "refused=wrong" in r[1], cmd_text(r))
        r = st.run("check", stdin=otp(secret, T0 + 60) + "\n", now=T0 + 60)
        row("check: the code of the clock's own step is accepted", r[0] == 0 and r[1] == "ok\n", cmd_text(r))
        r = st.run("check", stdin=otp(secret, T0 + 60) + "\n", now=T0 + 149)
        row("check: a code two steps old (the clock is at the end of the step after next) is refused (the window is one step either side)",
            r[0] == 1 and "refused=wrong" in r[1], cmd_text(r))
        for what, text in (("five digits", "12345"), ("seven digits", "1234567"), ("letters", "abcdef"), ("a long line", "1" * 40)):
            r = st.run("check", stdin=text + "\n")
            row("check with %s is refused as bad" % what, r[0] == 1 and "refused=bad" in r[1], cmd_text(r))
        before = st.text("sdsys.active")
        st.run("check", stdin=not_in_window(secret, T0 + 90) + "\n", now=T0 + 90)
        row("a refused check leaves the active file as it was", st.text("sdsys.active") == before)

        # ---------------------------------------------------------------- recovery codes
        r = st.run("check", stdin=rcodes[0] + "\n")
        row("a recovery code is accepted ('ok recovery')", r[0] == 0 and r[1] == "ok recovery\n", cmd_text(r))
        r = st.run("check", stdin=rcodes[0] + "\n")
        row("... and only once (refused=wrong)", r[0] == 1 and "refused=wrong" in r[1], cmd_text(r))
        r = st.run("check", stdin=rcodes[1].replace("-", "").lower() + "\n")
        row("a recovery code typed in lower case without the hyphen is accepted", r[0] == 0 and r[1] == "ok recovery\n", cmd_text(r))
        r = st.run("status")
        row("status counts them: six left", "recovery=6" in r[1], cmd_text(r))
        r = st.run("check", stdin="AAAAA-AAAAA\n")
        row("a recovery-shaped code that is not one is refused (refused=wrong)", r[0] == 1 and "refused=wrong" in r[1], cmd_text(r))
        r = st.run("recovery")
        newcodes = parse(r[1]).get("recovery", [])
        row("recovery: a new set of eight, all different from the old set", r[0] == 0 and len(newcodes) == 8 and not (set(newcodes) & set(rcodes)), cmd_text(r))
        r = st.run("check", stdin=rcodes[2] + "\n")
        row("... and a code of the OLD set no longer works", r[0] == 1 and "refused=wrong" in r[1], cmd_text(r))
        r = st.run("check", stdin=newcodes[0] + "\n")
        row("... a code of the new set does", r[0] == 0 and r[1] == "ok recovery\n", cmd_text(r))
        row("the secret was never printed again after begin showed it (every later output searched, 'ok' lines included)",
            not any(secret in o for o in st.outputs[2:]), "%d outputs" % len(st.outputs))

        # ---------------------------------------------------------------- enrolling again
        _, out, _ = st.run("begin", "SD Core", "sdsys@testhost", now=T0 + 600)
        secret_b = parse(out)["secret"][0]
        row("begin while enrolled makes a pending secret and leaves the active one alone",
            st.names() == ["sdsys.active", "sdsys.pending", "sdsys.recovery"] and "secret %s" % secret in st.text("sdsys.active"), "%s" % st.names())
        r = st.run("status")
        row("status: active AND pending", r[1].startswith("active=yes\npending=yes"), cmd_text(r))
        r = st.run("check", stdin=otp(secret_b, T0 + 600) + "\n", now=T0 + 600)
        row("the pending secret's code is NOT accepted by check", r[0] == 1 and "refused=wrong" in r[1], cmd_text(r))
        r = st.run("check", stdin=otp(secret, T0 + 600) + "\n", now=T0 + 600)
        row("the active secret's code still is", r[0] == 0 and r[1] == "ok\n", cmd_text(r))
        r = st.run("confirm", stdin=otp(secret_b, T0 + 660) + "\n", now=T0 + 660)
        row("confirm with the pending secret's code makes it the active one (new recovery codes, pending gone)",
            r[0] == 0 and len(parse(r[1]).get("recovery", [])) == 8 and st.names() == ["sdsys.active", "sdsys.recovery"] and "secret %s" % secret_b in st.text("sdsys.active"), cmd_text(r))
        r = st.run("check", stdin=otp(secret, T0 + 720) + "\n", now=T0 + 720)
        row("... and the old secret's code is no longer accepted", r[0] == 1 and "refused=wrong" in r[1], cmd_text(r))
        r = st.run("check", stdin=otp(secret_b, T0 + 720) + "\n", now=T0 + 720)
        row("... the new one's is", r[0] == 0 and r[1] == "ok\n", cmd_text(r))
        r = st.run("off")
        row("off removes everything", r[0] == 0 and r[1] == "off\n" and st.names() == [], cmd_text(r))
        r = st.run("check", stdin=otp(secret_b, T0 + 780) + "\n", now=T0 + 780)
        row("... and nothing is accepted afterwards (refused=nothing)", r[0] == 1 and "refused=nothing" in r[1], cmd_text(r))
        r = st.run("off")
        row("off on an empty store is not an error", r[0] == 0, cmd_text(r))

        # ---------------------------------------------------------------- the same code at the same moment
        # The processes are started first and all wait for their code on standard input (the command reads it before it touches the store), then the codes are written to all of them
        # together, so that they reach the lock at about the same moment; three rounds, each on a store of its own.
        accepted = replays = 0
        rounds = 3
        for _ in range(rounds):
            st = fresh()
            secret, _ = st.enrol()
            code = otp(secret, T0 + 30)
            procs = [subprocess.Popen([tool, "check"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                      env=dict(os.environ, SD_TOTP_DIR=st.dir, SD_TOTP_NOW=str(T0 + 30))) for _ in range(16)]
            for p in procs:
                p.stdin.write(code + "\n")
            for p in procs:
                p.stdin.flush()
                p.stdin.close()
            for p in procs:
                o = p.stdout.read()
                p.wait()
                p.stdout.close()
                p.stderr.close()
                accepted += 1 if p.returncode == 0 and o == "ok\n" else 0
                replays += 1 if p.returncode == 1 and "refused=replay" in o else 0
        row("sixteen checks of the same fresh code at once, three rounds: exactly one is accepted in each, every other is a replay (the lock)",
            accepted == rounds and replays == rounds * 15, "accepted %d of %d rounds, replays %d of %d" % (accepted, rounds, replays, rounds * 15))

        # ---------------------------------------------------------------- a store that is not what it should be
        def enrolled():
            s = fresh()
            sec, rc = s.enrol()
            return s, sec, rc

        def snapshot(st):
            snap = {}
            for f in st.names():
                p = st.path(f)
                snap[f] = open(p, "rb").read() if os.path.isfile(p) and not os.path.islink(p) else ("not a plain file", os.path.islink(p))
            return snap

        def unsafe(label, st, sec, level="active", rcode=None):
            """The verbs that read what was tampered with must exit 2 and never accept, and nothing in the store may change.  level: "dir" (every verb),
            "active" (status, check of a code, recovery) or "recovery" (status, check of a recovery code).  begin is NOT in the last two: it writes only the
            pending file, and enrolling again is how a damaged store is mended (the rows after these)."""
            if level == "dir":
                cases = ((("status",), None), (("check",), otp(sec, T0 + 3000) + "\n"), (("begin", "SD", "a"), None), (("recovery",), None),
                         (("confirm",), "123456\n"), (("off",), None))
            elif level == "active":
                cases = ((("status",), None), (("check",), otp(sec, T0 + 3000) + "\n"), (("recovery",), None))
            else:
                cases = ((("status",), None), (("check",), rcode + "\n"))
            before = snapshot(st)
            results = [st.run(*args, stdin=stdin, now=T0 + 3000) for args, stdin in cases]
            good = all(r[0] == 2 and "ok" not in r[1] and "secret=" not in r[1] and "recovery=" not in r[1] for r in results)
            same = snapshot(st) == before
            row(label, good and same, "; ".join("%s -> %d" % (a[0], r[0]) for (a, _), r in zip(cases, results)) + ("" if same else " (CHANGED)"))

        st, sec, _ = enrolled()
        os.chmod(st.dir, 0o755)
        unsafe("a directory open to others (0755): every verb refuses with exit 2 and changes nothing", st, sec, "dir")
        os.chmod(st.dir, 0o700)
        r = st.run("check", stdin=otp(sec, T0 + 30) + "\n", now=T0 + 30)
        row("... the same store at 0700 again is accepted (the refusal was the mode)", r[0] == 0, cmd_text(r))

        st, sec, _ = enrolled()
        os.rename(st.dir, st.dir + ".real")
        os.symlink(st.dir + ".real", st.dir)
        unsafe("the directory is a symbolic link: every verb refuses with exit 2", st, sec, "dir")

        st, sec, _ = enrolled()
        os.chmod(st.path("sdsys.active"), 0o644)
        unsafe("sdsys.active at 0644: refused, exit 2", st, sec)
        st, sec, rcs = enrolled()
        os.chmod(st.path("sdsys.recovery"), 0o640)
        unsafe("sdsys.recovery at 0640: status and a recovery code refuse with exit 2", st, sec, "recovery", rcs[0])

        st, sec, _ = enrolled()
        os.link(st.path("sdsys.active"), os.path.join(st.base, "elsewhere"))
        unsafe("sdsys.active with a second hard link: refused, exit 2", st, sec)

        st, sec, _ = enrolled()
        shutil.copy(st.path("sdsys.active"), st.path("copy"))
        os.chmod(st.path("copy"), 0o600)
        os.unlink(st.path("sdsys.active"))
        os.symlink("copy", st.path("sdsys.active"))
        unsafe("sdsys.active is a symbolic link to a good file: refused, exit 2", st, sec)

        st, sec, _ = enrolled()
        os.unlink(st.path("sdsys.active"))
        os.mkdir(st.path("sdsys.active"))
        unsafe("sdsys.active is a directory: refused, exit 2", st, sec)

        good = "sdtotp 1\nsecret %s\nlast 1\n"
        variants = (("a wrong first line", "sdtotp 2\nsecret %s\nlast 1\n"), ("an extra line", good + "extra 1\n"), ("no 'last' line", "sdtotp 1\nsecret %s\n"),
                    ("a secret of 31 characters", "sdtotp 1\nsecret %s\nlast 1\n"), ("a lower-case secret", "sdtotp 1\nsecret %s\nlast 1\n"),
                    ("a last that is not a number", "sdtotp 1\nsecret %s\nlast x\n"), ("a last of -2", "sdtotp 1\nsecret %s\nlast -2\n"),
                    ("the secret twice", "sdtotp 1\nsecret %s\nsecret %s\nlast 1\n"), ("a blank line in the middle", "sdtotp 1\n\nsecret %s\nlast 1\n"),
                    ("a NUL byte", "sdtotp 1\nsecret %s\nlast 1\n\0"), ("no text at all", ""), ("a file of 5000 bytes", good + "#" * 5000))
        for what, text in variants:
            st, sec, _ = enrolled()
            s = sec
            if "31 characters" in what:
                s = sec[:-1]
            if "lower-case" in what:
                s = sec.lower()
            body = text.replace("%s", s)
            with open(st.path("sdsys.active"), "w", encoding="latin-1") as f:
                f.write(body)
            os.chmod(st.path("sdsys.active"), 0o600)
            unsafe("sdsys.active holding %s: refused, exit 2, never ok" % what, st, sec)

        st, sec, rcs = enrolled()
        with open(st.path("sdsys.recovery"), "w") as f:
            f.write("sdtotp 1\nsalt zz\n")
        os.chmod(st.path("sdsys.recovery"), 0o600)
        unsafe("sdsys.recovery with a salt that is not 32 hex digits: status and a recovery code refuse with exit 2", st, sec, "recovery", rcs[0])

        # ---------------------------------------------------------------- a damaged store is mended by enrolling again
        for what, damage in (("sdsys.active at 0644", lambda s: os.chmod(s.path("sdsys.active"), 0o644)),
                             ("sdsys.active holding rubbish", lambda s: open(s.path("sdsys.active"), "w").write("rubbish\n")),
                             ("sdsys.recovery with a salt that is not hex", lambda s: open(s.path("sdsys.recovery"), "w").write("sdtotp 1\nsalt zz\n"))):
            st, sec, _ = enrolled()
            damage(st)
            r0 =st.run("begin", "SD Core", "sdsys@testhost", now=T0 + 3000)
            sec2 = parse(r0[1]).get("secret", [""])[0]
            r1 = st.run("confirm", stdin=otp(sec2, T0 + 3000) + "\n", now=T0 + 3000)
            r2 = st.run("check", stdin=otp(sec2, T0 + 3030) + "\n", now=T0 + 3030)
            row("%s does not block enrolling again: begin works, confirm replaces the files (0600) and the new secret then checks out" % what,
                r0[0] == 0 and bool(sec2) and r1[0] == 0 and r2[0] == 0 and r2[1] == "ok\n"
                and all(mode(st.path(f)) == 0o600 for f in ("sdsys.active", "sdsys.recovery")), "%s | %s | %s" % (cmd_text(r0)[:40], cmd_text(r1)[:50], cmd_text(r2)[:50]))

        # ---------------------------------------------------------------- a leftover of an interrupted write, and the knobs
        st = fresh()
        os.mkdir(st.dir, 0o700)
        with open(st.path(".new-sdsys.pending"), "w") as f:
            f.write("half a file")
        r = st.run("begin", "SD Core", "sdsys@testhost")
        row("a leftover .new- file of an interrupted write does not stop begin and is gone afterwards",
            r[0] == 0 and st.names() == ["sdsys.pending"], "%s: %s" % (cmd_text(r), st.names()))
        st.run("off")
        row("off also removes a leftover .new- file", st.names() == [], "%s" % st.names())

        st = fresh()
        st.enrol()
        default_dir = "/etc/sdcore/totp"
        if os.path.exists(default_dir) or shutil.which("unshare") is None or subprocess.run(["unshare", "-Ur", "true"], capture_output=True).returncode != 0:
            row("(not played: this machine has %s or no `unshare -Ur`) a root run ignores SD_TOTP_DIR and SD_TOTP_NOW" % default_dir, True, "skipped")
        else:
            p = subprocess.run(["unshare", "-Ur", tool, "status"], capture_output=True, text=True,
                               env=dict(os.environ, SD_TOTP_DIR=st.dir, SD_TOTP_NOW=str(T0)))
            row("a ROOT run (played by `unshare -Ur`) ignores SD_TOTP_DIR: it reports the real default store (none), not the scratch one that is enrolled",
                p.returncode == 0 and p.stdout == "active=no\npending=no\nrecovery=0\n", "exit %d: %s" % (p.returncode, p.stdout.replace("\n", " | ")))
        r = st.run("check", stdin="000000\n", env={"SD_TOTP_DIR": ""})
        row("an empty SD_TOTP_DIR means the default (not the current directory): nothing enrolled there", r[0] == 1 and "refused=nothing" in r[1], cmd_text(r))
        for args in ((), ("frobnicate",), ("status", "x"), ("confirm", "123456"), ("check", "123456"), ("off", "now")):
            r = st.run(*args)
            row("usage: %s is a usage error (exit 2) and the code is never an argument" % (" ".join(args) or "no verb"), r[0] == 2, cmd_text(r))

        # ---------------------------------------------------------------- the source, for what a black box cannot see
        store_c = open(os.path.join(src_dir, "sd_totp_store.c"), encoding="utf-8").read()
        cmd_c = open(os.path.join(src_dir, "sd_totp_cmd.c"), encoding="utf-8").read()
        code_store = re.sub(r"/\*.*?\*/", "", store_c, flags=re.S)
        code_cmd = re.sub(r"/\*.*?\*/", "", cmd_c, flags=re.S)
        loop = re.search(r"for \(i = 0; i < r\.n; i\+\+\) \{[^}]*\}", code_store)
        row("TEXT: a recovery hash is compared with CRYPTO_memcmp, in a loop over every hash with no break or return in it",
            "CRYPTO_memcmp(want, r.hash[i], HEX_HASH)" in code_store and loop is not None and "break" not in loop.group(0) and "return" not in loop.group(0), "")
        opens = re.findall(r"\bopen(?:at)?\([^;]*;", code_store)
        row("TEXT: every open and openat in the store passes O_NOFOLLOW (%d of them)" % len(opens), len(opens) >= 4 and all("O_NOFOLLOW" in o for o in opens), "")
        w0 = code_store.find("static int write_file")
        w = code_store[w0:code_store.find("\n}\n", w0)]
        row("TEXT: a file is replaced by a new one made with O_EXCL and mode 0600, written out (fsync) before the rename",
            "O_EXCL" in w and "0600" in w and "fchmod(fd, 0600)" in w and 0 < w.find("fsync(fd)") < w.find("renameat("), "")
        row("TEXT: the store reads no environment and prints nothing (the command does that)",
            "getenv" not in code_store and re.search(r"(?<![sn])printf\(|\bputs\(|\bfputs\(|\bfprintf\(", code_store) is None, "")
        row("TEXT: the directory is locked exclusively before anything is read, and its mode and owner are asked of the open descriptor",
            "flock(fd, LOCK_EX)" in code_store and "fstat(fd, &st)" in code_store and "st.st_uid != geteuid()" in code_store, "")
        gp = code_cmd.find("if (geteuid() != 0)")
        env_uses = [m.start() for m in re.finditer(r"getenv\(", code_cmd)]
        row("TEXT: the command reads SD_TOTP_DIR and SD_TOTP_NOW only inside the block that is skipped by a root run",
            gp > 0 and len(env_uses) == 2 and all(gp < u < code_cmd.find("if (strcmp(argv[1], \"status\")") for u in env_uses), "%s" % env_uses)
        row("TEXT: the secret is printed in one place only, by begin", code_cmd.count('"secret=') == 1 and 'printf("secret=%s\\nuri=%s\\n", b32, uri)' in code_cmd, "")
        row("TEXT: the code is read from standard input, not from an argument", "argv[2]" not in code_cmd[code_cmd.find('"confirm"'):code_cmd.find('"recovery"')], "")
    finally:
        shutil.rmtree(base, ignore_errors=True)
    return rows


# (name, file, old text, new text) - each old text must occur exactly once in its file
MUTANTS = [
    ("file-mode-not-asked", "sd_totp_store.c", "st.st_uid != geteuid() || (st.st_mode & 077) != 0\n        || st.st_nlink != 1", "st.st_uid != geteuid()\n        || st.st_nlink != 1"),
    ("hard-links-allowed", "sd_totp_store.c", "\n        || st.st_nlink != 1", ""),
    ("file-link-followed", "sd_totp_store.c", "openat(dfd, name, O_RDONLY | O_NOFOLLOW | O_CLOEXEC)", "openat(dfd, name, O_RDONLY | O_CLOEXEC)"),
    ("directory-link-followed", "sd_totp_store.c", "fd = open(dir, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);\n    if (fd < 0 && errno == ENOENT && create) {",
     "fd = open(dir, O_RDONLY | O_DIRECTORY | O_CLOEXEC);\n    if (fd < 0 && errno == ENOENT && create) {"),
    ("directory-mode-not-asked", "sd_totp_store.c", "st.st_uid != geteuid() || (st.st_mode & 077) != 0) {\n        close(fd);\n        return DIR_UNSAFE;",
     "st.st_uid != geteuid()) {\n        close(fd);\n        return DIR_UNSAFE;"),
    ("no-lock", "sd_totp_store.c", "if (flock(fd, LOCK_EX) != 0) {", "if (0) {"),
    ("step-not-recorded", "sd_totp_store.c", "if (step >= 0) rc = store_active(dfd, a.b32, step);", "if (step >= 0) rc = 0;"),
    ("replay-reported-as-wrong", "sd_totp_store.c", "else if (step == SD_TOTP_REPLAY) rc = SD_TOTPS_REPLAY;", "else if (step == SD_TOTP_REPLAY) rc = SD_TOTPS_WRONG;"),
    ("wrong-codes-not-counted", "sd_totp_store.c", "p.tries++;", ";"),
    ("six-wrong-codes-allowed", "sd_totp_store.c", "p.tries >= SD_TOTPS_TRIES", "p.tries > SD_TOTPS_TRIES"),
    ("wrong-code-activates", "sd_totp_store.c", "if (step < 0) {", "if (0) {"),
    ("pending-kept-after-confirm", "sd_totp_store.c", "if (rc == 0 && unlinkat(dfd, NAME_PENDING, 0) != 0 && errno != ENOENT) rc = SD_TOTPS_ERROR;", ";"),
    ("recovery-code-not-used-up", "sd_totp_store.c", "    r.n--;\n", ""),
    ("recovery-compare-stops-early", "sd_totp_store.c", "if (CRYPTO_memcmp(want, r.hash[i], HEX_HASH) == 0) hit = i;", "if (CRYPTO_memcmp(want, r.hash[i], HEX_HASH) == 0) { hit = i; break; }"),
    ("begin-writes-the-active-file", "sd_totp_store.c", "rc = store_pending(dfd, text, 0);", "rc = store_active(dfd, text, -1);"),
    ("stale-new-file-stops-a-write", "sd_totp_store.c", "    if (unlinkat(dfd, tmp, 0) != 0 && errno != ENOENT) return SD_TOTPS_ERROR;\n", ""),
    ("files-made-world-readable", "sd_totp_store.c", "O_CLOEXEC, 0600);\n    if (fd < 0) return SD_TOTPS_ERROR;\n    if (fchmod(fd, 0600) != 0) goto fail;",
     "O_CLOEXEC, 0666);\n    if (fd < 0) return SD_TOTPS_ERROR;"),
    ("knobs-read-by-root", "sd_totp_cmd.c", "if (geteuid() != 0) {", "if (1) {"),
    ("replay-printed-as-wrong", "sd_totp_cmd.c", 'case SD_TOTPS_REPLAY:    return refuse_word("replay");', 'case SD_TOTPS_REPLAY:    return refuse_word("wrong");'),
    ("unsafe-store-exits-1", "sd_totp_cmd.c", "            return 2;\n        default:", "            return 1;\n        default:"),
]


def selftest(cc):
    say("test-totp-store --selftest")
    originals = {f: open(os.path.join(INC, f), encoding="utf-8").read() for f in SRC + HDR}
    tmp = tempfile.mkdtemp(prefix="totp-store-mut-")
    survivors = []
    try:
        for i, (name, fname, old, new) in enumerate(MUTANTS):
            if originals[fname].count(old) != 1:
                say("  CANNOT RUN - mutant %s: its text occurs %d times in %s (wanted 1)" % (name, originals[fname].count(old), fname))
                return 2
        d0 = os.path.join(tmp, "src-base")
        os.makedirs(d0)
        for f, t in originals.items():
            open(os.path.join(d0, f), "w", encoding="utf-8").write(t)
        exe, cmd, p = build(cc, tmp, d0, "base")
        if p.returncode != 0 or p.stderr:
            say("  CANNOT RUN - the unmutated copy does not build cleanly:\n" + p.stderr)
            return 2
        rows = rows_for(exe, d0)
        bad = [r for r in rows if not r[1]]
        say("  control : the real source, %d rows, %d failed" % (len(rows), len(bad)))
        for label, ok, detail in bad:
            say("    FAIL %s | %s" % (label, detail))
        if bad or len(rows) < 60:
            return 1
        for i, (name, fname, old, new) in enumerate(MUTANTS):
            d = os.path.join(tmp, "m%d" % i)
            os.makedirs(d)
            for f, t in originals.items():
                open(os.path.join(d, f), "w", encoding="utf-8").write(t.replace(old, new) if f == fname else t)
            exe, cmd, p = build(cc, tmp, d, "mut%d" % i)
            if p.returncode != 0:
                say("  CANNOT RUN - mutant %s does not compile:\n%s" % (name, p.stderr))
                return 2
            try:
                mrows = rows_for(exe, d)
            except Exception as ex:                 # a mutant that breaks the rows' own assumptions (no recovery codes to index, say) is caught by that
                mrows = [("the rows stopped: %s: %s" % (type(ex).__name__, ex), False, "")]
            caught = [r for r in mrows if not r[1]]
            say("  [%s] %-34s %s" % ("KILLED  " if caught else "SURVIVED", name, ("%d row(s), first: %s" % (len(caught), caught[0][0][:90])) if caught else ""))
            if not caught:
                survivors.append(name)
            shutil.rmtree(d, ignore_errors=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    say("")
    if survivors:
        say("test-totp-store --selftest: FAILED - %d of %d mutants survived: %s" % (len(survivors), len(MUTANTS), ", ".join(survivors)))
        return 1
    say("test-totp-store --selftest: PASSED - %d of %d mutants killed." % (len(MUTANTS), len(MUTANTS)))
    return 0


def main():
    cc = shutil.which("cc") or shutil.which("gcc")
    say("test-totp-store")
    say("  compiler : %s" % (cc or "(none found)"))
    if cc is None:
        say("test-totp-store: CANNOT RUN - no C compiler on PATH.")
        return 2
    for f in SRC + HDR:
        if not os.path.isfile(os.path.join(INC, f)):
            say("test-totp-store: CANNOT RUN - missing %s" % os.path.join(INC, f))
            return 2
    if "--selftest" in sys.argv[1:]:
        return selftest(cc)
    tmp = tempfile.mkdtemp(prefix="totp-store-bin-")
    try:
        exe, cmd, p = build(cc, tmp, INC, "sd-totp")
        say("  command  : %s" % " ".join(cmd))
        if p.stdout or p.stderr:
            say("  --- compiler output ---")
            sys.stdout.write(p.stdout + p.stderr)
        if p.returncode != 0:
            say("test-totp-store: CANNOT RUN - compile failed (exit %d); libssl-dev installed?" % p.returncode)
            return 2
        if p.stderr:
            say("test-totp-store: FAILED - the compile produced a warning.")
            return 1
        rows = rows_for(exe, INC)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    bad = 0
    for label, ok, detail in rows:
        say("  [%s] %s%s" % ("PASS" if ok else "FAIL", label, "" if ok or not detail else "\n         " + detail))
        bad += 0 if ok else 1
    say("")
    if len(rows) < 60:
        say("test-totp-store: FAILED - only %d rows ran; a test that did almost nothing must fail." % len(rows))
        return 1
    say("test-totp-store: %d passed, %d failed" % (len(rows) - bad, bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
