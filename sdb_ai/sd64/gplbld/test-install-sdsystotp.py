#!/usr/bin/env python3
# test-install-sdsystotp.py - the installer's and the deleter's part of the remote sdsys login (S.95 stage 3, 1 Nov 2026): the question asked up front (TOTP-ASK), the
# install of SD's PAM module (PAMMODULE) and the enrolment at the end (SDSYS-ENROL), cut out of installsdcore.sh by their marker lines and run under the installer's OWN
# `set` and IFS (a block tested without them once passed while the installer's loop failed) with `sudo` a function that logs what it was asked and answers like the helper;
# and the deleter's order, read as text.  FREE: no sudo, no install, no sd, no tty (the code is read from a file named by SD_TOTP_TTY, as SD_PW_TTY does for the passwords).
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-install-sdsystotp.py [--selftest]
#
# NOT MEASURED HERE: that make builds the module on a machine that has the PAM headers (the build is `make pam_sdtotp.so`, shown by test-pam-sdtotp.py), that the real
# sd-elevate verbs do what the stubs say (test-sd-elevate.py, test-totp-store.py), and what a
# real terminal shows.  Exit 0 every row passed (or every mutant killed), 1 a row failed, 2 it could not run.

import os
import re
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
INST_REAL = os.path.join(ROOT, "installsdcore.sh")
DEL_REAL = os.path.join(ROOT, "deletesdcore.sh")
HELPER = "/usr/local/sbin/sd-elevate"

STUB = r'''
sudo() {
  local IFS=' '                                   # the installer's IFS is newline and tab: "$*" would join with a newline
  printf 'sudo %s\n' "$*" >> "$LOG"
  case "$*" in
    "$HELPER totp-begin")
      echo "secret=ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"; echo "uri=otpauth://totp/x?secret=ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
      return "${BEGIN_RC:-0}" ;;
    "$HELPER totp-confirm")
      code=$(cat); printf 'stdin=%s\n' "$code" >> "$LOG"
      case $code in
        111111) echo ok; echo recovery=AAAAA-BBBBB; return 0 ;;
        222222) echo ok; echo "the sshd arm was NOT opened"; return 3 ;;
        *)      echo refused=wrong; return 1 ;;
      esac ;;
    "install -o root -g root -m 0644 bin/pam_sdtotp.so /usr/local/lib/sd/pam_sdtotp.so") return "${INSTALL_RC:-0}" ;;
    *) return 0 ;;
  esac
}
'''


def blocks(text):
    out = {}
    for name in ("TOTP-ASK", "PAMMODULE", "SDSYS-ENROL"):
        m = re.search(r"^# %s-BEGIN\n(.*?)^# %s-END\n" % (name, name), text, re.S | re.M)
        out[name] = m.group(1) if m else None
    return out


def run(inst_text, name, setup, answers="", tty_lines=None, env=None):
    """Runs one block. Returns (exit status, stdout+stderr, the sudo log, variables printed)."""
    opts = "\n".join([l for l in inst_text.splitlines() if re.match(r"^(set -|IFS=)", l)][:2])
    blk = blocks(inst_text)[name]
    if blk is None:
        raise RuntimeError("block %s not found" % name)
    with tempfile.TemporaryDirectory() as td:
        log = os.path.join(td, "log")
        open(log, "w").close()
        tty = os.path.join(td, "tty")
        with open(tty, "w") as f:
            f.write("".join(l + "\n" for l in (tty_lines or [])))
        script = os.path.join(td, "run.sh")
        show = {"TOTP-ASK": "enrol_sdsys", "PAMMODULE": "pam_module_installed", "SDSYS-ENROL": "sdsys_totp_state"}[name]
        with open(script, "w") as f:
            f.write("%s\nLOG=%s\nHELPER=%s\nYELLOW=''\nNC=''\n%s\n%s\n%s\nprintf 'VAR %s=%%s\\n' \"$%s\"\n" % (opts, log, HELPER, STUB, setup, blk, show, show))
        e = dict(os.environ, SD_TOTP_TTY=tty)
        e.update(env or {})
        p = subprocess.run(["bash", script], input=answers, capture_output=True, text=True, env=e, timeout=60)
        lg = open(log).read()
    var = re.search(r"^VAR %s=(.*)$" % show, p.stdout, re.M)
    return p.returncode, p.stdout + p.stderr, lg, (var.group(1) if var else None)


def rows_for(inst_path, del_path):
    inst = open(inst_path, encoding="utf-8").read()
    dele = open(del_path, encoding="utf-8").read()
    rows = []

    def row(label, ok, detail=""):
        rows.append((label, bool(ok), detail))

    b = blocks(inst)
    row("the three blocks are in the installer, once each", all(v is not None for v in b.values()) and all(len(re.findall("^# %s-BEGIN$" % n, inst, re.M)) == 1 for n in b), "%s" % [k for k, v in b.items() if v is None])

    # ---------------------------------------------------------------- the question
    for ans, want in (("y", "y"), ("Y", "y"), ("yes", "y"), ("YES", "y"), ("Yes", "y"), ("", "n"), ("n", "n"), ("N", "n"), ("no", "n"), ("yy", "n"), ("maybe", "n"), ("1", "n")):
        rc, out, lg, v = run(inst, "TOTP-ASK", "", answers=ans + "\n")
        row("the question: %r -> %s (the default is NO)" % (ans, "y" if want == "y" else "n"), rc == 0 and v == want, "exit %d, %r" % (rc, v))
    rc, out, lg, v = run(inst, "TOTP-ASK", "", answers="y\n")
    row("the question names the authenticator code, ssh, the order (code before password) and the command for later, and is asked once (read -p prints nothing without a terminal: the prompt is read from the block)",
        blocks(inst)["TOTP-ASK"].count("(y/N)") == 1 and blocks(inst)["TOTP-ASK"].count("read -r -p") == 1 and "authenticator code" in out and "ssh" in out
        and "BEFORE its password" in out and "sudo sd-elevate totp-begin" in out, out[-300:])

    # ---------------------------------------------------------------- the module
    rc, out, lg, v = run(inst, "PAMMODULE", "pam_module_built=1\npam_module_installed=0\n")
    calls = [l for l in lg.splitlines() if l.startswith("sudo")]
    row("module built: /usr/local/lib/sd and /etc/sdcore are made root:root 0755 and the module is installed root:root 0644 at /usr/local/lib/sd/pam_sdtotp.so",
        rc == 0 and v == "1" and "sudo install -d -o root -g root -m 0755 /usr/local/lib/sd" in calls and "sudo install -d -o root -g root -m 0755 /etc/sdcore" in calls
        and "sudo install -o root -g root -m 0644 bin/pam_sdtotp.so /usr/local/lib/sd/pam_sdtotp.so" in calls, "%s" % calls)
    rc, out, lg, v = run(inst, "PAMMODULE", "pam_module_built=0\npam_module_installed=0\n")
    row("module not built: nothing is installed and the flag stays 0", rc == 0 and v == "0" and "sudo" not in lg, lg)
    rc, out, lg, v = run(inst, "PAMMODULE", "pam_module_built=1\npam_module_installed=0\n", env={"INSTALL_RC": "1"})
    row("the install of the module fails: a WARNING, the flag stays 0, and the installer does not stop", rc == 0 and v == "0" and "WARNING" in out, "exit %d, %r" % (rc, v))

    # ---------------------------------------------------------------- the enrolment
    base = "enrol_sdsys=y\npam_module_installed=1\nssh_boundary_ok=1\n"

    def enrol(setup, lines, env=None):
        return run(inst, "SDSYS-ENROL", setup, tty_lines=lines, env=env)

    rc, out, lg, v = enrol("enrol_sdsys=n\npam_module_installed=1\nssh_boundary_ok=1\n", ["111111"])
    row("not asked for: nothing is run and the state stays 'not set up'", rc == 0 and v == "not set up" and "sudo" not in lg, "%r %r" % (v, lg))
    rc, out, lg, v = enrol("enrol_sdsys=y\npam_module_installed=0\nssh_boundary_ok=1\n", ["111111"])
    row("asked for but the module is not installed: nothing is run, the state says why", rc == 0 and "PAM module is not installed" in (v or "") and "sudo" not in lg, "%r" % v)
    rc, out, lg, v = enrol("enrol_sdsys=y\npam_module_installed=1\nssh_boundary_ok=0\n", ["111111"])
    row("asked for but the ssh boundary was not applied: nothing is run, the state says why", rc == 0 and "ssh boundary was not applied" in (v or "") and "sudo" not in lg, "%r" % v)
    rc, out, lg, v = enrol(base, ["111111"], env={"SD_TOTP_TTY": "/nonexistent/tty"})
    row("no terminal to read at: nothing is run, the state says so", rc == 0 and "no terminal" in (v or "") and "sudo" not in lg, "%r" % v)
    rc, out, lg, v = enrol(base, ["111111"])
    row("a right first code: totp-begin once, totp-confirm once with the code on STANDARD INPUT and not as an argument, the state is 'set up', the recovery codes are shown",
        rc == 0 and (v or "").startswith("set up") and lg.count("totp-begin") == 1 and lg.count("totp-confirm") == 1 and "sudo %s totp-confirm\n" % HELPER in lg
        and "stdin=111111" in lg and "recovery=AAAAA-BBBBB" in out and "Write the recovery codes down" in out, "%r %r" % (v, lg))
    row("... the secret is shown once, on the terminal, and the block writes it nowhere (no tee, no redirection of the helper's output)",
        len(re.findall(r"^secret=ABCDEF", out, re.M)) == 1 and not re.search(r"totp-begin[^\n]*(>|tee)", inst[inst.find("# SDSYS-ENROL-BEGIN"):inst.find("# SDSYS-ENROL-END")]), "")
    rc, out, lg, v = enrol(base, ["000000", "111111"])
    row("a wrong code and then a right one: two confirms, then set up", (v or "").startswith("set up") and lg.count("totp-confirm") == 2 and "That code was not accepted" in out, "%r" % v)
    rc, out, lg, v = enrol(base, ["000000", "000001", "000002", "111111"])
    row("three wrong codes: three confirms, no fourth (the helper throws the secret away at five), the state says how to go on",
        lg.count("totp-confirm") == 3 and (v or "").startswith("not confirmed") and "totp-confirm" in (v or "") and "stdin=111111" not in lg, "%r %r" % (v, lg))
    rc, out, lg, v = enrol(base, [""])
    row("Enter at the first prompt stops: no confirm, 'not confirmed'", lg.count("totp-confirm") == 0 and (v or "").startswith("not confirmed"), "%r" % v)
    rc, out, lg, v = enrol(base, [])
    row("a terminal that ends: no confirm, 'not confirmed', no hang", rc == 0 and lg.count("totp-confirm") == 0 and (v or "").startswith("not confirmed"), "%r" % v)
    rc, out, lg, v = enrol(base, ["222222"])
    row("a code that enrolled but the ssh door would not open (exit 3): the state says the door was NOT opened, and no further tries",
        "NOT opened" in (v or "") and lg.count("totp-confirm") == 1, "%r" % v)
    rc, out, lg, v = enrol(base, ["111111"], env={"BEGIN_RC": "1"})
    row("totp-begin fails: no code is asked for, no confirm, the state says so", rc == 0 and lg.count("totp-confirm") == 0 and "totp-begin failed" in (v or ""), "%r" % v)

    # ---------------------------------------------------------------- order in the two scripts (text)
    def at(text, s, start=0):
        return text.find(s, start)

    gates_end = at(inst, "# GATES-ASK-END")
    ask = at(inst, "# TOTP-ASK-BEGIN")
    row("TEXT: the question is asked up front, straight after the gates question", 0 < gates_end < ask < gates_end + 3000, "%d %d" % (gates_end, ask))
    row("TEXT: the module is built after the main make, before the system directory is copied from the clone, and the build is not fatal",
        0 < at(inst, "if make -B; then") < at(inst, "if make pam_sdtotp.so") < at(inst, 'sudo cp -R bin "$sdsysdir"')
        and "exit 1" not in inst[at(inst, "if make pam_sdtotp.so"):at(inst, "if make pam_sdtotp.so") + 600], "")
    row("TEXT: the module goes in after ssh-forcecommand is installed, the stray copy in the sealed bin is removed right after the tree copy",
        0 < at(inst, "gplbld/ssh-forcecommand.sh /usr/local/sbin/ssh-forcecommand") < at(inst, "# PAMMODULE-BEGIN") < at(inst, 'sudo cp -R bin "$sdsysdir"')
        < at(inst, 'sudo rm -f "$sdsysdir/bin/pam_sdtotp.so"') < at(inst, "# ROOTBIN-BEGIN"), "")
    enrol_at = at(inst, "# SDSYS-ENROL-BEGIN")
    row("TEXT: the enrolment runs after the ssh boundary is applied, after the files root runs are sealed (sd-totp is in them), after the last password step, and before sd is restarted",
        0 < at(inst, "    ssh_boundary_ok=1\n") < enrol_at and 0 < at(inst, "# ROOTBIN-END") < enrol_at and 0 < at(inst, 'sdsys_sd_pw_state="set"') < enrol_at < at(inst, 'if sudo systemctl restart sd.service'), "")
    row("TEXT: the closing text no longer says sdsys cannot log in over ssh, and reports the state", "sdsys cannot log in over ssh" not in inst and 'echo "SDSYS over ssh: $sdsys_totp_state."' in inst, "")
    a = at(dele, "ssh-forcecommand --remove")
    row("TEXT: the deleter takes both fences out first, removes the secret always, and the module only when the fences are out",
        0 < a < at(dele, "sudo rm -rf /etc/sdcore/totp") < at(dele, 'if [ "$ssh_fences_out" = 1 ]; then\n    sudo rm -rf /usr/local/lib/sd') and "ssh_fences_out=0" in dele, "")
    return rows


MUTANTS = [
    ("inst", "ask answers yes by default", "# TOTP-ASK-BEGIN\nenrol_sdsys=n", "# TOTP-ASK-BEGIN\nenrol_sdsys=y"),
    ("inst", "ask accepts anything", "case $yn_totp in [yY]|[yY][eE][sS] ) enrol_sdsys=y;; esac", "case $yn_totp in * ) enrol_sdsys=y;; esac"),
    ("inst", "ask accepts only a lower case y", "case $yn_totp in [yY]|[yY][eE][sS] ) enrol_sdsys=y;; esac", "case $yn_totp in y ) enrol_sdsys=y;; esac"),
    ("inst", "the module is installed though it was not built", 'if [ "$pam_module_built" = 1 ]; then\n    echo "Installing SD\'s PAM module', 'if true; then\n    echo "Installing SD\'s PAM module'),
    ("inst", "the module is group writable", "-m 0644 bin/pam_sdtotp.so", "-m 0664 bin/pam_sdtotp.so"),
    ("inst", "the module is sdsys's", "install -o root -g root -m 0644 bin/pam_sdtotp.so", "install -o sdsys -g sdusers -m 0644 bin/pam_sdtotp.so"),
    ("inst", "a failed install of the module is called installed", "if sudo install -o root -g root -m 0644 bin/pam_sdtotp.so /usr/local/lib/sd/pam_sdtotp.so; then", "if true; then"),
    ("inst", "/etc/sdcore is not made", "    sudo install -d -o root -g root -m 0755 /etc/sdcore          # sd-totp makes /etc/sdcore/totp (0700) itself, and only that last directory\n", ""),
    ("inst", "enrolling without the module", 'if [ "$pam_module_installed" != 1 ]; then\n        sdsys_totp_state', 'if false; then\n        sdsys_totp_state'),
    ("inst", "enrolling without the ssh boundary", 'elif [ "$ssh_boundary_ok" != 1 ]; then', "elif false; then"),
    ("inst", "enrolling with no terminal", 'elif ! { exec 8<"$totp_tty"; } 2>/dev/null; then', "elif false; then"),
    ("inst", "the code is an argument", "printf '%s\\n' \"$totp_code\" | sudo /usr/local/sbin/sd-elevate totp-confirm || totp_rc=$?", 'sudo /usr/local/sbin/sd-elevate totp-confirm "$totp_code" || totp_rc=$?'),
    ("inst", "any number of tries", 'while [ "$totp_try" -le 3 ]; do', 'while [ "$totp_try" -le 30 ]; do'),
    ("inst", "a door that did not open is not noticed", 'elif [ "$totp_rc" -eq 3 ]; then', "elif false; then"),
    ("inst", "any answer is a success", 'if [ "$totp_rc" -eq 0 ]; then\n                    sdsys_totp_state="set up', 'if true; then\n                    sdsys_totp_state="set up'),
    ("inst", "the block writes the secret to a file", "if sudo /usr/local/sbin/sd-elevate totp-begin; then", "if sudo /usr/local/sbin/sd-elevate totp-begin | tee /tmp/secret; then"),
    ("inst", "the closing text says sdsys cannot log in over ssh", 'echo "su route into it.  sdsys can log in over ssh only after an authenticator code"', 'echo "su route into it.  sdsys cannot log in over ssh, and an authenticator code"'),
    ("del", "the module is removed whatever happened to the fences", 'if [ "$ssh_fences_out" = 1 ]; then\n    sudo rm -rf /usr/local/lib/sd', 'if true; then\n    sudo rm -rf /usr/local/lib/sd'),
    ("del", "the secret is left behind", "sudo rm -rf /etc/sdcore/totp\n", ""),
    ("del", "a failed removal of the fences is not noticed", "        ssh_fences_out=0\n", ""),
]


def main():
    print("test-install-sdsystotp")
    for p in (INST_REAL, DEL_REAL):
        if not os.path.isfile(p):
            print("  CANNOT RUN - missing %s" % p)
            return 2
    if "--selftest" not in sys.argv[1:]:
        rows = rows_for(INST_REAL, DEL_REAL)
        bad = [r for r in rows if not r[1]]
        for label, ok, detail in rows:
            print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label, "" if ok or not detail else "\n         " + detail))
        print("test-install-sdsystotp: %d passed, %d failed" % (len(rows) - len(bad), len(bad)))
        return 1 if bad or len(rows) < 30 else 0
    inst = open(INST_REAL, encoding="utf-8").read()
    dele = open(DEL_REAL, encoding="utf-8").read()
    base = rows_for(INST_REAL, DEL_REAL)
    bad = [r for r in base if not r[1]]
    print("  control : the real scripts, %d rows, %d failed" % (len(base), len(bad)))
    for label, ok, detail in bad:
        print("    FAIL %s | %s" % (label, detail))
    if bad:
        return 1
    survivors = 0
    with tempfile.TemporaryDirectory() as td:
        for which, name, old, new in MUTANTS:
            src = inst if which == "inst" else dele
            if src.count(old) != 1:
                print("  CANNOT RUN - mutant %s: its text occurs %d times (wanted 1)" % (name, src.count(old)))
                return 2
            ip, dp = os.path.join(td, "i.sh"), os.path.join(td, "d.sh")
            open(ip, "w", encoding="utf-8").write(src.replace(old, new) if which == "inst" else inst)
            open(dp, "w", encoding="utf-8").write(src.replace(old, new) if which == "del" else dele)
            try:
                caught = [r for r in rows_for(ip, dp) if not r[1]]
            except Exception as ex:
                caught = [("rows stopped: %s" % ex, False, "")]
            print("  [%s] %-60s %s" % ("KILLED  " if caught else "SURVIVED", name, ("%d row(s)" % len(caught)) if caught else ""))
            survivors += 0 if caught else 1
    print("%d of %d mutants killed" % (len(MUTANTS) - survivors, len(MUTANTS)))
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main())
