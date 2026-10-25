#!/usr/bin/env python3
# test-lnxdunit-units.py - the restart of a dead audit daemon, option A (25 Oct 2026, the owner: "Build option A: sdlnxd as its own systemd unit with Restart=on-failure"):
# sdlnxd is run by sd-lnxd.service, which systemd starts again when it fails; "sd -start -nodaemon" (what sd.service runs) leaves the fork of the daemon to that unit.
# FREE CHECK, text only (comments removed), no install, no sudo, no systemd.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-lnxdunit-units.py
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-lnxdunit-units.py --selftest         (mutants)
#
#   U  sd-lnxd.service: Type=simple, the daemon with no arguments, Restart=on-failure (NEVER always: "sd -stop" ends the daemon with SIGTERM and it exits 0), a pause, a
#      start limit, UMask=0022, After= and BindsTo= sd.service, no [Install] section.  sd.service: "sd -start -nodaemon", still oneshot, wants sd-lnxd.service, stops with sd -stop
#   C  sysseg.c / sd.h: start_sd(bool with_daemon) forks the daemon (start_lnxd) only when asked, runs the STARTUP command either way, and a child whose exec fails ends
#   D  sd.c: "-nodaemon" is read only after -start and only as that word; -restart still forks the daemon
#   G  sdlnxd.c: one daemon at a time: it ends with status 0 (not a failure, so the service does not start it again) when the segment names a live process running the same
#      executable, and asks that BEFORE it writes its own pid into the segment
#   I  installsdcore.sh: the first-install block gives sd-lnxd.service its owner and mode; the LNXDUNIT block puts this release's two units in place over an sd.service that
#      does not mention it; test-install-lnxdunit.sh runs that block
#   X  deletesdcore.sh stops sd-lnxd.service before sd.service and removes its file
# NOT SAID HERE: that systemd restarts the daemon, that stop leaves nothing running, that the installer's units work - the VM witness (witness-w11.py section C1R); that
# "sd -start -nodaemon" leaves the daemon out and a second daemon ends - sandbox-auditwriter.py W12 and W13.
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.normpath(os.path.join(HERE, ".."))
TREE = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
REAL = {
    "sd-lnxd.service": os.path.join(SD64, "usr", "lib", "systemd", "system", "sd-lnxd.service"),
    "sd.service": os.path.join(SD64, "usr", "lib", "systemd", "system", "sd.service"),
    "sysseg.c": os.path.join(SD64, "gplsrc", "sysseg.c"),
    "sd.c": os.path.join(SD64, "gplsrc", "sd.c"),
    "sd.h": os.path.join(SD64, "gplsrc", "sd.h"),
    "sdlnxd.c": os.path.join(SD64, "gplsrc", "sdlnxd.c"),
    "installsdcore.sh": os.path.join(TREE, "installsdcore.sh"),
    "deletesdcore.sh": os.path.join(TREE, "deletesdcore.sh"),
}
FILES = {k: os.environ.get("LU_" + re.sub(r"\W", "_", k).upper(), v) for k, v in REAL.items()}
passed = failed = 0


def row(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print("  [PASS] " + name)
    else:
        failed += 1
        print("  [FAIL] " + name + ("   <- " + detail if detail else ""))


def raw(name):
    return open(FILES[name], encoding="latin-1").read()


def code(name):
    s = raw(name)
    if name.endswith((".c", ".h")):
        s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
        return re.sub(r"//[^\n]*", "", s)
    return "\n".join(l for l in s.split("\n") if not l.lstrip().startswith("#"))      # units and shell: whole-line comments


def func(src, head):
    m = re.search(re.escape(head) + r"[^;{]*\{.*?\n\}", src, re.S)
    return m.group(0) if m else ""


def keys(unit_text, section):
    """the Key=Value lines of one section of a unit"""
    out, cur = [], None
    for l in unit_text.split("\n"):
        m = re.match(r"^\[(\w+)\]\s*$", l.strip())
        if m:
            cur = m.group(1)
        elif cur == section and "=" in l:
            out.append(l.strip())
    return out


def run():
    u = code("sd-lnxd.service")
    s = code("sd.service")
    row("U1 sd-lnxd.service runs the daemon in the foreground: Type=simple, ExecStart=/usr/local/sdsys/bin/sdlnxd with no arguments, nothing else for ExecStart",
        keys(u, "Service").count("Type=simple") == 1 and [k for k in keys(u, "Service") if k.startswith("ExecStart")] == ["ExecStart=/usr/local/sdsys/bin/sdlnxd"], str(keys(u, "Service")))
    row("U2 it is restarted on failure and NOT always: Restart=on-failure once, no Restart=always",
        keys(u, "Service").count("Restart=on-failure") == 1 and not any(k.startswith("Restart=") and k != "Restart=on-failure" for k in keys(u, "Service")), str(keys(u, "Service")))
    row("U3 with a pause before the restart (RestartSec=2) and a limit on a start that keeps failing (5 in 60 s)",
        "RestartSec=2" in keys(u, "Service") and "StartLimitIntervalSec=60" in keys(u, "Unit") and "StartLimitBurst=5" in keys(u, "Unit"), str(keys(u, "Unit")))
    row("U4 it makes its directory and files under UMask=0022", "UMask=0022" in keys(u, "Service"), "")
    row("U5 it starts after sd.service (the segment must exist) and stops with it", "After=sd.service" in keys(u, "Unit") and "BindsTo=sd.service" in keys(u, "Unit"), str(keys(u, "Unit")))
    row("U6 it has no [Install] section (sd.service wants it)", "[Install]" not in u, "")
    row("U7 sd.service runs 'sd -start -nodaemon' (and only that for ExecStart), is still oneshot with RemainAfterExit, and stops with 'sd -stop'",
        [k for k in keys(s, "Service") if k.startswith("ExecStart=")] == ["ExecStart=/usr/local/sdsys/bin/sd -start -nodaemon"] and "Type=oneshot" in keys(s, "Service")
        and "RemainAfterExit=yes" in keys(s, "Service") and "ExecStop=/usr/local/sdsys/bin/sd -stop" in keys(s, "Service"), str(keys(s, "Service")))
    row("U8 sd.service wants sd-lnxd.service, and still sweeps stale accounts before it starts",
        "Wants=sd-lnxd.service" in keys(s, "Unit") and "ExecStartPre=-/usr/local/sbin/sd-reconcile-accounts --sweep" in keys(s, "Service"), str(keys(s, "Unit")))

    y = code("sysseg.c")
    sl = func(y, "Private bool start_lnxd(void)")
    ss = func(y, "bool start_sd(bool with_daemon)")
    row("C1 start_lnxd() is the old fork: fork, daemon(1, 1), the sdlnxd path, execl; a failed fork is reported and a child whose exec fails ENDS (_exit(1))",
        bool(sl) and "fork()" in sl and "daemon(1, 1);" in sl and "/bin/sdlnxd" in sl and "execl(path, path, NULL);\n    _exit(1);" in sl and "return FALSE;" in sl
        and "Cannot start sdlnxd - fork() failed" in sl, "")
    i_pid, i_if, i_start = ss.find("sysseg->sdlnxd_pid = -1;"), ss.find("if (with_daemon && !start_lnxd())"), ss.find("if (sysseg->startup[0] != '\\0')")
    row("C2 start_sd(with_daemon) forks the daemon only when asked (after the pid is set to -1), and the STARTUP command is run either way (outside that test)",
        0 <= i_pid < i_if < i_start and "return FALSE;" in ss[i_if:i_start], "positions %d %d %d" % (i_pid, i_if, i_start))
    row("C3 sd.h declares start_sd(bool with_daemon)", "bool start_sd(bool with_daemon);" in code("sd.h"), "")

    d = code("sd.c")
    row("D1 '-nodaemon' is read after -start only, as that exact word (stricmp, the next argument), and start_sd() is given the answer",
        "bool with_daemon = !((arg + 1 < argc) && !stricmp(argv[arg + 1], \"-NODAEMON\"));" in d and "start_sd(with_daemon)" in d and d.count("-NODAEMON") == 1, "")
    row("D2 -restart still starts the daemon itself (start_sd(TRUE))", "stop_sd() && start_sd(TRUE)" in d, "")

    z = code("sdlnxd.c")
    ag = func(z, "static bool another_daemon_runs(void)")
    mn = func(z, "int main()")
    row("G1 another_daemon_runs() looks at the pid in the segment, ignores 0, -1 and its own, needs the process to exist (kill 0) and to run THIS executable (/proc/<pid>/exe against /proc/self/exe)",
        bool(ag) and "sysseg->sdlnxd_pid" in ag and "(pid <= 0) || (pid == getpid())" in ag and "kill(pid, 0)" in ag and "/proc/%d/exe" in ag and "/proc/self/exe" in ag
        and "memcmp(other, mine, (size_t)n_mine) == 0" in ag, "")
    i_g, i_set = mn.find("if (another_daemon_runs()) {"), mn.find("sysseg->sdlnxd_pid = getpid();")
    gb = mn[i_g:i_set] if 0 <= i_g < i_set else ""
    row("G2 main() asks it BEFORE it writes its own pid into the segment, and a second daemon returns 0 (a clean end, which the service does not restart)",
        0 <= i_g < i_set and "return 0;" in gb and "exit(" not in gb, "positions %d %d" % (i_g, i_set))

    inst = code("installsdcore.sh")
    first = inst[inst.find('echo "Installing sd.service for systemd."'):inst.find("# LNXDUNIT-BEGIN") if "# LNXDUNIT-BEGIN" in raw("installsdcore.sh") else None]
    row("I1 the first-install block gives sd-lnxd.service its owner (root:root) and mode (644) like the other units",
        'chown root:root "$SYSTEMDPATH/sd-lnxd.service"' in inst and 'chmod 644 "$SYSTEMDPATH/sd-lnxd.service"' in inst, "")
    m = re.search(r"# LNXDUNIT-BEGIN\n(.*?)\n# LNXDUNIT-END", raw("installsdcore.sh"), re.S)
    blk = "\n".join(l for l in m.group(1).split("\n") if not l.lstrip().startswith("#")) if m else ""
    row("I2 the LNXDUNIT block exists and acts only when sd.service is there and does not mention sd-lnxd.service",
        bool(blk) and "if [ -f \"$SYSTEMDPATH/sd.service\" ] && ! grep -q 'sd-lnxd\\.service' \"$SYSTEMDPATH/sd.service\"; then" in blk, blk[:200])
    row("I3 and then puts BOTH of this release's files in place, owner root, mode 0644, and reloads systemd",
        "install -o root -g root -m 0644 usr/lib/systemd/system/sd.service \"$SYSTEMDPATH/sd.service\"" in blk
        and "install -o root -g root -m 0644 usr/lib/systemd/system/sd-lnxd.service \"$SYSTEMDPATH/sd-lnxd.service\"" in blk and "systemctl daemon-reload" in blk, "")
    row("I4 the block sits after the first-install copy and before the API listener's rebind (the block that daemon-reloads for the units)",
        0 <= raw("installsdcore.sh").find('echo "Installing sd.service for systemd."') < raw("installsdcore.sh").find("# LNXDUNIT-BEGIN")
        < raw("installsdcore.sh").find("# Remote-access prompts (owner, 10 Sep 2026, approach B) - API listener bind."), "")

    dl = code("deletesdcore.sh")
    i1, i2 = dl.find("systemctl stop sd-lnxd.service"), dl.find("systemctl stop sd.service")
    row("X1 deletesdcore.sh stops sd-lnxd.service before sd.service", 0 <= i1 < i2, "positions %d %d" % (i1, i2))
    row("X2 and removes the unit file with the others", '"${systemd_dir}/sd-lnxd.service"' in dl, "")
    print("test-lnxdunit-units: %d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


MUTANTS = [   # name, file, old, new
    # the unit's header comment mentions these words, so each mutant is anchored on the line itself
    ("unit-restart-always", "sd-lnxd.service", "\nRestart=on-failure\n", "\nRestart=always\n"),
    ("unit-no-restart", "sd-lnxd.service", "\nRestart=on-failure\n", "\n"),
    ("unit-restart-on-abnormal-only", "sd-lnxd.service", "\nRestart=on-failure\n", "\nRestart=on-abnormal\n"),
    ("unit-umask-077", "sd-lnxd.service", "\nUMask=0022\n", "\nUMask=0077\n"),
    ("unit-no-bindsto", "sd-lnxd.service", "BindsTo=sd.service\n", ""),
    ("unit-before-sd", "sd-lnxd.service", "After=sd.service", "Before=sd.service"),
    ("unit-daemon-with-argument", "sd-lnxd.service", "ExecStart=/usr/local/sdsys/bin/sdlnxd\n", "ExecStart=/usr/local/sdsys/bin/sdlnxd -x\n"),
    ("unit-forking", "sd-lnxd.service", "Type=simple", "Type=forking"),
    ("unit-no-start-limit", "sd-lnxd.service", "StartLimitBurst=5\n", ""),
    ("unit-installs-itself", "sd-lnxd.service", "UMask=0022\n", "UMask=0022\n\n[Install]\nWantedBy=multi-user.target\n"),
    ("service-forks-the-daemon", "sd.service", "ExecStart=/usr/local/sdsys/bin/sd -start -nodaemon", "ExecStart=/usr/local/sdsys/bin/sd -start"),
    ("service-does-not-want-the-unit", "sd.service", "Wants=sd-lnxd.service\n", ""),
    ("sysseg-always-forks", "sysseg.c", "if (with_daemon && !start_lnxd())", "if (!start_lnxd())"),
    ("sysseg-never-forks", "sysseg.c", "if (with_daemon && !start_lnxd())", "if (FALSE && !start_lnxd())"),
    ("sysseg-child-returns-after-failed-exec", "sysseg.c", "execl(path, path, NULL);\n    _exit(1);", "execl(path, path, NULL);"),
    ("sysseg-startup-only-with-daemon", "sysseg.c", "  /* Run startup command, if defined */\n\n  if (sysseg->startup[0] != '\\0') {", "  /* Run startup command, if defined */\n\n  if (with_daemon && sysseg->startup[0] != '\\0') {"),
    ("sd-h-old-prototype", "sd.h", "bool start_sd(bool with_daemon);", "bool start_sd(void);"),
    ("sd-nodaemon-misspelt", "sd.c", '!stricmp(argv[arg + 1], "-NODAEMON")', '!stricmp(argv[arg + 1], "-NODAEMOX")'),
    ("sd-restart-without-daemon", "sd.c", "stop_sd() && start_sd(TRUE)", "stop_sd() && start_sd(FALSE)"),
    ("sd-start-ignores-the-option", "sd.c", "if (start_sd(with_daemon)) {", "if (start_sd(TRUE)) {"),
    ("guard-off", "sdlnxd.c", "if (another_daemon_runs()) {", "if (FALSE) {"),
    ("guard-no-executable-check", "sdlnxd.c", "return memcmp(other, mine, (size_t)n_mine) == 0;", "return TRUE;"),
    ("guard-no-liveness-check", "sdlnxd.c", "if ((kill(pid, 0) != 0) && (errno != EPERM))\n    return FALSE;\n", ""),
    ("guard-ends-as-a-failure", "sdlnxd.c", "    shmdt((void*)sysseg);\n    return 0;\n  }\n\n  /* Set process id", "    shmdt((void*)sysseg);\n    return 1;\n  }\n\n  /* Set process id"),
    ("guard-after-registering", "sdlnxd.c", "  if (another_daemon_runs()) {", "  sysseg->sdlnxd_pid = getpid();\n  if (another_daemon_runs()) {"),
    ("installer-block-always", "installsdcore.sh", " && ! grep -q 'sd-lnxd\\.service' \"$SYSTEMDPATH/sd.service\"; then", "; then"),
    ("installer-block-only-the-unit", "installsdcore.sh", '    sudo install -o root -g root -m 0644 usr/lib/systemd/system/sd.service "$SYSTEMDPATH/sd.service"\n', ""),
    ("installer-no-mode", "installsdcore.sh", 'sudo chmod 644 "$SYSTEMDPATH/sd-lnxd.service"\n', ""),
    ("deleter-stops-it-last", "deletesdcore.sh", "sudo systemctl stop sd-lnxd.service 2>/dev/null || true\nsudo systemctl stop sd.service sdclient.socket 2>/dev/null || true",
     "sudo systemctl stop sd.service sdclient.socket 2>/dev/null || true\nsudo systemctl stop sd-lnxd.service 2>/dev/null || true"),
    ("deleter-keeps-the-unit-file", "deletesdcore.sh", '           "${systemd_dir}/sd-lnxd.service" \\\n', ""),
]


def selftest(start=0):
    import shutil
    t = tempfile.mkdtemp()
    caught = missed = 0
    print("selftest: the real files first (must pass), then mutants from number %d (each must not)" % start)
    r = subprocess.run([sys.executable, os.path.abspath(__file__)], capture_output=True, text=True)
    if r.returncode != 0:
        print("  [FAIL] the real files do not pass:\n" + r.stdout[-900:])
        return 1
    print("  [ok] the real files pass")
    for name, which, old, new in MUTANTS[start:]:
        real = open(REAL[which], encoding="latin-1").read()
        if old not in real:
            print("  [MISSED] %s: the text to change is not there" % name)
            missed += 1
            continue
        f = os.path.join(t, name + "-" + which)
        open(f, "w", encoding="latin-1").write(real.replace(old, new, 1))
        env = dict(os.environ)
        env["LU_" + re.sub(r"\W", "_", which).upper()] = f
        r = subprocess.run([sys.executable, os.path.abspath(__file__)], env=env, capture_output=True, text=True)
        if r.returncode != 0:
            print("  [caught] %s (exit %d)" % (name, r.returncode))
            caught += 1
        else:
            print("  [MISSED] %s: the check still passed" % name)
            missed += 1
    shutil.rmtree(t, ignore_errors=True)
    print("selftest: %d of %d mutants caught, %d missed" % (caught, caught + missed, missed))
    return 0 if missed == 0 and caught > 0 else 1


if __name__ == "__main__":
    _from = [int(a.split("=", 1)[1]) for a in sys.argv[1:] if a.startswith("--from=")]
    sys.exit(selftest(_from[0] if _from else 0) if "--selftest" in sys.argv else run())
