#!/usr/bin/env python3
# test-jobmark-units.py - S.102 stage 3 (2 Nov 2026): gplsrc/sd_jobmark.c, the kernel's answer to "is THIS process a scheduled administrator job of SD's?"
# (kernel(K$JOB.MARK)), built with -Wall -Wextra together with gplbld/verify-jobmark.c and driven as a black box on scratch files: a cgroup file as systemd
# writes it, a definitions directory and its parent, a definition.  The owner the driver asks for is the test's own uid (the kernel asks for root's).
# Then the source rules a black box cannot see: the kernel passes its own single_command and owner 0, CPROC's arm, and audit_message's job= suffix.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-jobmark-units.py [--selftest]
#
# WHAT THIS CANNOT SHOW (the VM witness's): that systemd really puts a job's process in that cgroup and nobody else can (measured 2 Nov 26 on Debian 13 by
# .claude/vmtools/probe-s102-unit.py and probe-s102-sudo.py), a root-owned definition, and a real job's run.  Exit 0 every row passed (or every mutant
# killed), 1 a row failed (or a mutant survived), 2 it could not run (no C compiler).  Fewer than 25 rows is a failure.

import os
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.dirname(HERE)
INC = os.path.join(SD64, "gplsrc")
SRC = "sd_jobmark.c"
DRIVER = os.path.join(HERE, "verify-jobmark.c")
CFLAGS = ["-std=gnu17", "-Wall", "-Wextra", "-Wformat=2", "-O2"]
UNIT = "0::/system.slice/sdcore-job-nightly.service\n"


def say(s=""):
    print(s, flush=True)


def build(cc, tmp, src_dir, name):
    exe = os.path.join(tmp, name)
    cmd = [cc] + CFLAGS + ["-I" + src_dir, os.path.join(src_dir, SRC), DRIVER, "-o", exe]
    p = subprocess.run(cmd, capture_output=True, text=True)
    return exe, p


def rows_for(exe, base):
    rows = []

    def row(label, ok, detail=""):
        rows.append((label, bool(ok), detail))

    n = [0]

    def scene(defn="name=nightly\ncommand=update.accounts all\n", dmode=0o644, cg=UNIT, jmode=0o755, pmode=0o755, dname="nightly"):
        n[0] += 1
        d = os.path.join(base, "s%d" % n[0])
        etc = os.path.join(d, "etc")
        jd = os.path.join(etc, "jobs.d")
        os.makedirs(jd)
        os.chmod(etc, pmode)
        os.chmod(jd, jmode)
        if defn is not None:
            f = os.path.join(jd, dname)
            with open(f, "wb") as fh:
                fh.write(defn.encode() if isinstance(defn, str) else defn)
            os.chmod(f, dmode)
        cgf = os.path.join(d, "cgroup")
        with open(cgf, "w", encoding="utf-8") as fh:
            fh.write(cg)
        return cgf, jd

    def ask(cgf, jd, command="update.accounts all"):
        p = subprocess.run([exe, cgf, jd, command], capture_output=True, text=True)
        return p.returncode, p.stdout.strip()

    cgf, jd = scene()
    rc, out = ask(cgf, jd)
    row("ALLOW: the cgroup of sdcore-job-nightly.service, a closed definitions directory, a definition naming nightly and this very command: job=nightly", rc == 0 and out == "job=nightly", out)
    for command, why in (("update.accounts all ", "with a trailing space"), ("UPDATE.ACCOUNTS ALL", "in capitals"), ("update.accounts all; backup.account all", "with a second command"),
                         ("backup.account all", "another job's command"), ("", "empty")):
        rc, out = ask(cgf, jd, command)
        row("REFUSE: the session's command is %s: no job" % why, rc == 1 and out == "job=", out)
    for cg, why in (("0::/system.slice/sdcore-job-other.service\n", "another job's unit (no definition by that name)"),
                    ("0::/user.slice/user-979.slice/user@979.service/app.slice/sdcore-job-nightly.service\n", "sdsys's own user manager"),
                    ("0::/user.slice/user-1000.slice/session-3.scope\n", "a login session"),
                    ("0::/system.slice/sdcore-job-nightly.service\n1:name=systemd:/\n", "two lines (a hybrid layout)"),
                    ("0::/system.slice/sdcore-job-nightly.service", "one line with no newline"),
                    ("0::/system.slice/sdcore-job-nightly.service.d/x.service\n", "a path below the unit"),
                    ("0::/system.slice/sdcore-job-Nightly.service\n", "a name in capitals"),
                    ("0::/system.slice/sdcore-job-nightly-.service\n", "a name ending in a dash"),
                    ("0::/system.slice/sdcore-job-" + "a" * 33 + ".service\n", "a name of 33 characters"),
                    ("0::/system.slice/sdcore-job-.service\n", "no name"),
                    ("", "an empty file")):
        c2, j2 = scene(cg=cg)
        rc, out = ask(c2, j2)
        row("REFUSE: the cgroup is %s: no job" % why, rc == 1 and out == "job=", repr(cg[:60]) + " " + out)
    for defn, dmode, why in (("name=nightly\ncommand=update.accounts all\n", 0o664, "writable by its group"),
                             ("name=nightly\ncommand=update.accounts all\n", 0o646, "writable by others"),
                             ("name=other\ncommand=update.accounts all\n", 0o644, "naming another job"),
                             ("command=update.accounts all\n", 0o644, "with no name line"),
                             ("name=nightly\n", 0o644, "with no command line"),
                             ("name=nightly\ncommand=update.accounts all\ncommand=backup.account all\n", 0o644, "with two command lines"),
                             ("name=nightly\nname=nightly\ncommand=update.accounts all\n", 0o644, "with two name lines"),
                             (b"name=nightly\ncommand=update.accounts all\x00x\n", 0o644, "holding a NUL byte"),
                             ("name=nightly\ncommand=update.accounts all\n" + "#" * 5000 + "\n", 0o644, "over 4 KB")):
        c2, j2 = scene(defn=defn, dmode=dmode)
        rc, out = ask(c2, j2)
        row("REFUSE: the definition is %s: no job" % why, rc == 1 and out == "job=", out)
    c2, j2 = scene(jmode=0o775)
    rc, out = ask(c2, j2)
    row("REFUSE: the definitions' directory is writable by its group: no job", rc == 1 and out == "job=", out)
    c2, j2 = scene(pmode=0o777)
    rc, out = ask(c2, j2)
    row("REFUSE: the directory above it is writable by others: no job", rc == 1 and out == "job=", out)
    c2, j2 = scene(defn=None)
    rc, out = ask(c2, j2)
    row("REFUSE: no definition by the unit's name: no job", rc == 1 and out == "job=", out)
    c2, j2 = scene()
    f = os.path.join(j2, "nightly")
    os.rename(f, os.path.join(base, "elsewhere-%d" % n[0]))
    os.symlink(os.path.join(base, "elsewhere-%d" % n[0]), f)
    rc, out = ask(c2, j2)
    row("REFUSE: the definition is a LINK to a right-looking file: no job", rc == 1 and out == "job=", out)
    c2, j2 = scene()
    os.link(os.path.join(j2, "nightly"), os.path.join(base, "hard-%d" % n[0]))
    rc, out = ask(c2, j2)
    row("REFUSE: the definition has a second hard link: no job", rc == 1 and out == "job=", out)
    c2, j2 = scene()
    real = j2 + ".real"
    os.rename(j2, real)
    os.symlink(real, j2)
    rc, out = ask(c2, j2)
    row("REFUSE: the definitions' directory is a link: no job", rc == 1 and out == "job=", out)
    c2, j2 = scene(defn="name=nightly-\ncommand=update.accounts all\n", cg="0::/system.slice/sdcore-job-nightly-.service\n", dname="nightly-")
    rc, out = ask(c2, j2)
    row("REFUSE: a unit and a definition both named 'nightly-' (a name may not end in a dash): no job", rc == 1 and out == "job=", out)
    c2, j2 = scene(defn="name=nightly\ncommand=backup.account all\n")
    rc, out = ask(c2, j2, "backup.account all")
    row("ALLOW: a command with a space (backup.account all) matches exactly: job=nightly", rc == 0 and out == "job=nightly", out)
    return rows


def text_rows():
    rows = []
    opk = open(os.path.join(INC, "op_kernel.c"), encoding="utf-8").read()
    ker = open(os.path.join(INC, "k_error.c"), encoding="utf-8").read()
    cp = open(os.path.join(SD64, "sdsys", "gpl.bp", "cproc"), encoding="utf-8", errors="replace").read()
    src = open(os.path.join(SD64, "gpl.src"), encoding="utf-8").read().split()
    case = opk[opk.find("    case K_JOB_MARK:"):]
    case = case[:case.find("      break;")]
    rows.append(("TEXT: the kernel compares its OWN single_command (no argument from BASIC) and asks for root's ownership (0), once per process",
                 "sd_job_name(SD_JOB_CGROUP_FILE, SD_JOB_DIR, single_command, 0, jn, sizeof(jn)) == 0" in case and "sd_job_active[0] == '\\0'" in case
                 and "k_get_c_string" not in case, case[:120]))
    rows.append(("TEXT: audit_message() ends every record of a job's run with job=<name>, before the record goes to the daemon, the file or the journal",
                 'snprintf(jmsg, sizeof(jmsg), "%s job=%s", msg, sd_job_active);' in ker and ker.find("msg = jmsg;") < ker.find("audit_to_daemon(msg)"), ""))
    rows.append(("TEXT: sd_jobmark is part of the sd binary (gpl.src) and its paths are /proc/self/cgroup and /etc/sdcore/jobs.d",
                 "sd_jobmark" in src and '#define SD_JOB_CGROUP_FILE  "/proc/self/cgroup"' in open(os.path.join(INC, "sd_jobmark.h")).read()
                 and '#define SD_JOB_DIR          "/etc/sdcore/jobs.d"' in open(os.path.join(INC, "sd_jobmark.h")).read(), ""))
    rows.append(("TEXT: CPROC grants a job only in the local arm, and only on a name from K$JOB.MARK", cp.count("kernel(K$JOB.MARK, 0)") == 1 and "if job.name # '' then" in cp, ""))
    return rows


MUTANTS = [
    ("the command is not compared", "    if (!line_value(def, \"command\", val, sizeof val) || strcmp(val, command) != 0) return -1;\n", ""),
    ("the name line is not compared", "    if (!line_value(def, \"name\", val, sizeof val) || strcmp(val, cand) != 0) return -1;\n", ""),
    ("a group-writable file is believed", "if (st.st_uid != owner || (st.st_mode & 022) != 0) return 0;", "if (st.st_uid != owner) return 0;"),
    ("a second hard link is believed", "if (type == S_IFREG && (st.st_nlink != 1 || st.st_size >= DEF_MAX)) return 0;", "if (type == S_IFREG && (st.st_size >= DEF_MAX)) return 0;"),
    ("the definition is followed through a link", "    fd = openat(dfd, cand, O_RDONLY | O_NOFOLLOW | O_CLOEXEC);", "    fd = openat(dfd, cand, O_RDONLY | O_CLOEXEC);"),
    ("the directory is followed through a link", "    dfd = open(jobs_dir, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);", "    dfd = open(jobs_dir, O_RDONLY | O_DIRECTORY | O_CLOEXEC);"),
    ("the parent is not checked", "    if (!safe_fd(pfd, S_IFDIR, owner)) { close(pfd); return -1; }\n", ""),
    # (no mutant for the one-line test of the cgroup file: name_ok() refuses a newline in the name anyway, so taking it out changes no answer - an equivalent mutant)
    ("any slice is a job", "#define CG_PREFIX  \"0::/system.slice/sdcore-job-\"", "#define CG_PREFIX  \"0::/\""),
    ("a name may end in a dash", "    if (n[len - 1] == '-') return 0;\n", ""),
    ("a duplicate key is taken", "            if (found != NULL) return 0;\n", ""),
    ("a NUL is allowed", "    if (memchr(def, '\\0', (size_t)n) != NULL) return -1;\n", ""),
]


def selftest(cc):
    say("test-jobmark-units --selftest")
    orig = open(os.path.join(INC, SRC), encoding="utf-8").read()
    for name, old, new in MUTANTS:
        if orig.count(old) != 1:
            say("  CANNOT RUN - mutant %s: its text occurs %d times (wanted 1)" % (name, orig.count(old)))
            return 2
    tmp = tempfile.mkdtemp(prefix="jobmark-mut-")
    survivors = []
    try:
        d0 = os.path.join(tmp, "base")
        os.makedirs(d0)
        shutil.copy(os.path.join(INC, SRC), d0)
        shutil.copy(os.path.join(INC, "sd_jobmark.h"), d0)
        exe, p = build(cc, tmp, d0, "base-exe")
        if p.returncode != 0 or p.stderr:
            say("  CANNOT RUN - the unmutated copy does not build cleanly:\n" + p.stderr)
            return 2
        base = os.path.join(tmp, "scenes-base")
        os.makedirs(base)
        rows = rows_for(exe, base)
        bad = [r for r in rows if not r[1]]
        say("  control : the real source, %d rows, %d failed" % (len(rows), len(bad)))
        if bad or len(rows) < 25:
            return 1
        for i, (name, old, new) in enumerate(MUTANTS):
            d = os.path.join(tmp, "m%d" % i)
            os.makedirs(d)
            open(os.path.join(d, SRC), "w", encoding="utf-8").write(orig.replace(old, new))
            shutil.copy(os.path.join(INC, "sd_jobmark.h"), d)
            exe, p = build(cc, tmp, d, "mut%d" % i)
            if p.returncode != 0:
                say("  [KILLED  ] %-50s (does not build)" % name)
                continue
            sc = os.path.join(tmp, "scenes-%d" % i)
            os.makedirs(sc)
            caught = [r for r in rows_for(exe, sc) if not r[1]]
            say("  [%s] %-50s %s" % ("KILLED  " if caught else "SURVIVED", name, ("%d row(s), first: %s" % (len(caught), caught[0][0][:70])) if caught else ""))
            if not caught:
                survivors.append(name)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    say("")
    if survivors:
        say("test-jobmark-units --selftest: FAILED - %d of %d mutants survived: %s" % (len(survivors), len(MUTANTS), ", ".join(survivors)))
        return 1
    say("test-jobmark-units --selftest: PASSED - %d of %d mutants killed." % (len(MUTANTS), len(MUTANTS)))
    return 0


def main():
    cc = shutil.which("cc") or shutil.which("gcc")
    if not cc:
        say("test-jobmark-units: CANNOT RUN - no C compiler")
        return 2
    if "--selftest" in sys.argv[1:]:
        return selftest(cc)
    say("test-jobmark-units")
    tmp = tempfile.mkdtemp(prefix="jobmark-")
    try:
        exe, p = build(cc, tmp, INC, "verify-jobmark")
        say("  built: %s (%s)" % (exe, "clean" if p.returncode == 0 and not p.stderr else "FAILED"))
        if p.returncode != 0 or p.stderr:
            say(p.stderr)
            return 1
        base = os.path.join(tmp, "scenes")
        os.makedirs(base)
        rows = rows_for(exe, base) + text_rows()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    bad = [r for r in rows if not r[1]]
    for label, ok, detail in rows:
        say("  [%s] %s%s" % ("PASS" if ok else "FAIL", label, "" if ok or not detail else "  <- " + detail))
    if len(rows) < 25:
        say("test-jobmark-units: FAILED - only %d rows (the null case)" % len(rows))
        return 1
    say("test-jobmark-units: %d passed, %d failed" % (len(rows) - len(bad), len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
