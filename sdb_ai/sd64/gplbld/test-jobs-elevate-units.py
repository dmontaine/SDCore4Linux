#!/usr/bin/env python3
"""test-jobs-elevate-units.py - sd-elevate's job-set, job-delete and job-list (S.102 stage 2): the DEFINITIONS of the administrator's scheduled jobs, in /etc/sdcore/jobs.d.

    python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-jobs-elevate-units.py
    python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-jobs-elevate-units.py --selftest

No sudo, no install, no sd.  It CUTS the functions between "# BEGIN jobs_functions" and "# END jobs_functions" out of sd-elevate and runs them with bash on scratch directories, as
test-confset-elevate-units.py does for conf-set (the worker's Python is taken out of the same block, so what runs is the shipped text), and it drives the real script with --dry-run for
the verbs' argument rules.  ***IT CANNOT SAY THAT ROOT WRITES /etc/sdcore/jobs.d***: the directory's real owner and the sudo call are the VM witness's rows, and so is a directory owned by
ANOTHER user (a test user cannot make one).  NOTHING HERE SAYS A JOB RUNS: stage 2 writes no timer and no service.

WHAT IS HELD.  (1) THE NAME: 1 to 32 characters, a lower case letter first, lower case letters, digits and dashes, no trailing dash; nothing else (a dot, a slash, an upper case
letter, a newline, a non-ASCII byte are each refused).  (2) THE COMMAND IS AN ID FROM THE HELPER'S LIST and never text: exactly four ids, each with its one sentence; the sentence
itself, another case, a trailing blank or a second command are refused.  (3) THE SCHEDULE is one of five shapes with the exact ranges (every 5/10/15/20/30 minutes; hourly; daily HH:MM;
weekly mon..sun HH:MM; monthly 1..28 HH:MM), each turned into its OnCalendar; every other spelling is refused; and systemd-analyze (when this machine has it) accepts every OnCalendar the
helper can produce.  (4) THE WRITE on real scratch directories: the directory is made 0755, a file is the definition and nothing else with mode 0644 and no temp file left, a second
set replaces, a delete removes and a delete of a name that is not there changes nothing, the 33rd job is refused and a replacement at 32 is not; a directory that is a link, a name that
is a link or a directory, a directory writable by group or other are refused and the link's target is untouched.  (5) THE LIST shows a good definition as one line and every damaged
one (a stray key, a missing key, a name that is not the file's, a command or a calendar that is not the helper's own, a link, a stray file, a file over 4 KB) as damaged, never as a job.
(6) THE VERBS (the real script): argument counts, the dry run prints what it resolved and writes nothing, a real run as an ordinary user dies at need_root before anything is made; the
order job_check, need_root, job_caller, the write; SD_JOBS_DIR is reset in main unless a dry run or a non-root process; sudoers gives these verbs to nobody new; the deleter removes
/etc/sdcore/jobs.d before it removes /etc/sdcore.

--selftest breaks the helper and the deleter 24 ways and requires a named check to go red for each one.  Exit 0 every check passed, 1 a check failed, 2 it could not measure.
"""

import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir, os.pardir))      # the repository root: gplbld, sd64, sdb_ai, then the root
ELEVATE = os.path.join(HERE, "sd-elevate")
SUDOERS = os.path.join(HERE, "sdcore.sudoers")
DELETER = os.path.join(ROOT, "deletesdcore.sh")
BEGIN = "# BEGIN jobs_functions"
END = "# END jobs_functions"

IDS = {"backup-all": "backup.account all", "check-masters": "check.masters", "sync-masters": "sync.masters", "update-accounts": "update.accounts all"}
GOOD_SCHED = [
    (["every", "5", "minutes"], "every 5 minutes", "*-*-* *:0/5:00"), (["every", "10", "minutes"], "every 10 minutes", "*-*-* *:0/10:00"),
    (["every", "15", "minutes"], "every 15 minutes", "*-*-* *:0/15:00"), (["every", "20", "minutes"], "every 20 minutes", "*-*-* *:0/20:00"),
    (["every", "30", "minutes"], "every 30 minutes", "*-*-* *:0/30:00"), (["hourly"], "hourly", "*-*-* *:00:00"),
    (["daily", "00:00"], "daily 00:00", "*-*-* 00:00:00"), (["daily", "02:30"], "daily 02:30", "*-*-* 02:30:00"), (["daily", "23:59"], "daily 23:59", "*-*-* 23:59:00"),
    (["weekly", "mon", "03:00"], "weekly mon 03:00", "Mon *-*-* 03:00:00"), (["weekly", "tue", "03:00"], "weekly tue 03:00", "Tue *-*-* 03:00:00"),
    (["weekly", "wed", "03:00"], "weekly wed 03:00", "Wed *-*-* 03:00:00"), (["weekly", "thu", "03:00"], "weekly thu 03:00", "Thu *-*-* 03:00:00"),
    (["weekly", "fri", "03:00"], "weekly fri 03:00", "Fri *-*-* 03:00:00"), (["weekly", "sat", "03:00"], "weekly sat 03:00", "Sat *-*-* 03:00:00"),
    (["weekly", "sun", "23:59"], "weekly sun 23:59", "Sun *-*-* 23:59:00"),
    (["monthly", "1", "04:15"], "monthly 1 04:15", "*-*-1 04:15:00"), (["monthly", "9", "04:15"], "monthly 9 04:15", "*-*-9 04:15:00"),
    (["monthly", "10", "04:15"], "monthly 10 04:15", "*-*-10 04:15:00"), (["monthly", "19", "04:15"], "monthly 19 04:15", "*-*-19 04:15:00"),
    (["monthly", "20", "04:15"], "monthly 20 04:15", "*-*-20 04:15:00"), (["monthly", "28", "04:15"], "monthly 28 04:15", "*-*-28 04:15:00"),
]
BAD_SCHED = [
    [], ["yearly"], ["every"], ["every", "5"], ["every", "0", "minutes"], ["every", "1", "minutes"], ["every", "7", "minutes"], ["every", "05", "minutes"], ["every", "60", "minutes"],
    ["every", "5", "minute"], ["every", "5", "minutes", "now"], ["hourly", "now"], ["daily"], ["daily", "2:30"], ["daily", "24:00"], ["daily", "12:60"], ["daily", "12:5"], ["daily", "1230"],
    ["daily", "02:30", "extra"], ["daily", "02:30:00"], ["weekly"], ["weekly", "sun"], ["weekly", "Sun", "03:00"], ["weekly", "sunday", "03:00"], ["weekly", "03:00", "sun"],
    ["monthly"], ["monthly", "1"], ["monthly", "0", "01:00"], ["monthly", "29", "01:00"], ["monthly", "31", "01:00"], ["monthly", "01", "01:00"], ["monthly", "1", "25:00"],
    ["daily", "*:00"], ["daily", "$(id)"], ["daily", "02:30\n"], ["Daily", "02:30"], ["*", "*"],
]
GOOD_NAMES = ["a", "z9", "nightly-backup", "a1b2", "a" + "b" * 30 + "c", "x" * 32]
BAD_NAMES = ["", "A", "1a", "-a", "a-", "a_b", "a.b", "a b", "a/b", "../x", "a\nb", "é", "x" * 33, "a--", "Ab", ".hidden", "a;ls"]
BAD_IDS = ["", "rm", "backup.account all", "BACKUP-ALL", "backup-all ", "backup-all;ls", "backup", "check.masters", "sync-masters sync-masters", "$(id)"]


def block_of(text):
    a, b = text.find(BEGIN), text.find(END)
    return text[a:b + len(END)] if 0 <= a < b else None


def bash(script, env=None, inp=None):
    p = subprocess.run(["bash", "-c", script], capture_output=True, text=True, env=env or dict(os.environ), input=inp, timeout=120)
    return p.returncode, p.stdout, p.stderr


HEAD = 'die() { printf "REFUSED %s\\n" "$*" >&2; exit 1; }\n'


def jobs_py(text):
    rc, out, err = bash(HEAD + block_of(text) + '\nprintf "%s" "$JOBS_PY"')
    return out if rc == 0 else None


def run_worker(py, *args):
    p = subprocess.run([sys.executable, "-I", "-c", py] + list(args), capture_output=True, text=True, timeout=60)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def case_lines(text, calls):
    """run bash function calls on the cut block: each call is a bash snippet that prints one result; returns {label: (rc, output)}"""
    pre = ('t() { local o r; o=$( ( "$@" ) 2>&1 ); r=$?; printf "CASE\\t%s\\t%d\\t%s\\n" "$T" "$r" "${o//$\'\\n\'/ }"; }\n'
           'jc() { job_command "$1" && printf "%s" "$JB_SENTENCE"; }\n'
           'js() { job_schedule "$@" && printf "%s|%s" "$JB_SCHED" "$JB_CAL"; }\n')
    script = HEAD + block_of(text) + "\n" + pre + "".join(calls)
    rc, out, err = bash(script)
    res = {}
    for ln in out.splitlines():
        if ln.startswith("CASE\t"):
            _, label, r, o = (ln.split("\t", 3) + [""])[:4]
            res[label] = (int(r), o)
    return res, err


def checks(elev, deleter, sudoers):
    out = []

    def ck(name, ok, detail=""):
        out.append((name, bool(ok), detail))

    blk = block_of(elev)
    if blk is None:
        return [("the jobs block exists", False, "no markers")]
    py = jobs_py(elev) or ""

    # ---- (1) names, (2) ids, (3) schedules
    calls = []
    for i, n in enumerate(GOOD_NAMES + BAD_NAMES):
        calls.append("T=N%d; t job_name_ok %s\n" % (i, shlex.quote(n)))
    res, err = case_lines(elev, calls)
    bad = [n for i, n in enumerate(GOOD_NAMES) if res.get("N%d" % i, (9, ""))[0] != 0] + [n for i, n in enumerate(BAD_NAMES) if res.get("N%d" % (i + len(GOOD_NAMES)), (0, ""))[0] == 0]
    ck("N1 a job name is 1 to 32 characters, a lower case letter first, then lower case letters, digits and dashes, no trailing dash; nothing else is a name", not bad and len(res) == len(GOOD_NAMES) + len(BAD_NAMES), repr((bad, err[:200])))

    calls = ["T=C%d; t job_command %s\n" % (i, shlex.quote(k)) for i, k in enumerate(IDS)] + ["T=B%d; t job_command %s\n" % (i, shlex.quote(k)) for i, k in enumerate(BAD_IDS)]
    res, err = case_lines(elev, calls)
    ok_ids = all(res.get("C%d" % i, (9, ""))[0] == 0 for i in range(len(IDS))) and all(res.get("B%d" % i, (0, ""))[0] != 0 for i in range(len(BAD_IDS)))
    calls = ["T=S%d; t jc %s\n" % (i, shlex.quote(k)) for i, k in enumerate(IDS)]
    res2, _ = case_lines(elev, calls)
    sent = all(res2.get("S%d" % i, (9, ""))[1] == v for i, v in enumerate(IDS.values()))
    ck("N2 the command is one of exactly four ids, each with its one sentence; the sentence itself, another case, a blank or a second command are not ids", ok_ids and sent, repr((res, res2)))

    calls = []
    for i, (w, _s, _c) in enumerate(GOOD_SCHED):
        calls.append("T=G%d; t js %s\n" % (i, " ".join(shlex.quote(x) for x in w)))
    for i, w in enumerate(BAD_SCHED):
        calls.append("T=X%d; t job_schedule %s\n" % (i, " ".join(shlex.quote(x) for x in w)))
    res, err = case_lines(elev, calls)
    badg = [GOOD_SCHED[i][0] for i in range(len(GOOD_SCHED)) if res.get("G%d" % i, (9, ""))[1] != "%s|%s" % (GOOD_SCHED[i][1], GOOD_SCHED[i][2])]
    badx = [BAD_SCHED[i] for i in range(len(BAD_SCHED)) if res.get("X%d" % i, (0, ""))[0] == 0]
    ck("S1 the five schedule shapes give their one spelling and their OnCalendar, with the exact ranges", not badg and len(res) == len(GOOD_SCHED) + len(BAD_SCHED), repr((badg, err[:200])))
    ck("S2 every other spelling is refused (a seven-minute interval, a leading zero, 24:00, 29 to 31, a capital, a glob, a command substitution, an extra word)", not badx, repr(badx))

    cal = shutil.which("systemd-analyze")
    if cal:
        bad = []
        for _w, _s, c in GOOD_SCHED:
            p = subprocess.run([cal, "calendar", c], capture_output=True, text=True, timeout=30)
            if p.returncode != 0 or "Next elapse" not in p.stdout:
                bad.append((c, p.stderr.strip()[:80]))
        ck("S3 systemd-analyze on this machine accepts every OnCalendar the helper can produce and gives it a next run", not bad, repr(bad))
    else:
        print("  [SKIPPED] S3 systemd-analyze is not on this machine: the OnCalendar forms are not checked against systemd here (the VM rows do)")

    # ---- (4) the write
    tmp = tempfile.mkdtemp(prefix="jobs-t-")
    try:
        base = os.path.join(tmp, "etc", "sdcore")
        d = os.path.join(base, "jobs.d")
        os.makedirs(tmp, exist_ok=True)
        text1 = "# t\nname=a\njob=backup-all\ncommand=backup.account all\nschedule=daily 02:30\noncalendar=*-*-* 02:30:00\n"
        rc, o, e = run_worker(py, "set", d, "a", text1, "32")
        parent_missing_ok = rc != 0                                    # /tmp/jobs-t-x/etc does not exist: the worker makes the last two components only
        os.makedirs(os.path.join(tmp, "etc"))
        old_umask = os.umask(0o077)                                    # a strict umask (sudo can pass one on): the modes are the worker's own, not the umask's
        try:
            rc, o, e = run_worker(py, "set", d, "a", text1, "32")
        finally:
            os.umask(old_umask)
        st = os.stat(d) if os.path.isdir(d) else None
        f = os.path.join(d, "a")
        mode = stat.S_IMODE(os.stat(f).st_mode) if os.path.exists(f) else None
        ck("W1 set makes the directory (0755) and the file (0644) holding the definition and nothing else, says created, and leaves no temp file",
           rc == 0 and o == "created" and st and stat.S_IMODE(st.st_mode) == 0o755 and mode == 0o644 and open(f).read() == text1 and os.listdir(d) == ["a"] and parent_missing_ok,
           repr((rc, o, e, os.listdir(d) if os.path.isdir(d) else None, mode)))
        rc, o, e = run_worker(py, "set", d, "a", text1.replace("02:30", "03:30"), "32")
        ck("W2 a second set of the same name replaces and says so", rc == 0 and o == "replaced" and "03:30" in open(f).read() and os.listdir(d) == ["a"], repr((rc, o, e)))
        rc, o, e = run_worker(py, "delete", d, "a")
        rc2, o2, e2 = run_worker(py, "delete", d, "a")
        ck("W3 delete removes it; a delete of a name that is not there says absent and fails nothing", rc == 0 and o == "deleted" and not os.path.exists(f) and rc2 == 0 and o2 == "absent", repr((rc, o, rc2, o2)))

        for i in range(32):
            run_worker(py, "set", d, "j%02d" % i, text1, "32")
        names = sorted(os.listdir(d))
        rc, o, e = run_worker(py, "set", d, "overflow", text1, "32")
        rc2, o2, e2 = run_worker(py, "set", d, "j05", text1, "32")
        ck("W4 the 33rd job is refused and a replacement at 32 is not", len(names) == 32 and rc != 0 and "32 jobs" in e and not os.path.exists(os.path.join(d, "overflow")) and rc2 == 0 and o2 == "replaced", repr((len(names), rc, e, rc2, o2)))
        for n in names:
            os.unlink(os.path.join(d, n))

        victim = os.path.join(tmp, "victim")
        open(victim, "w").write("untouched\n")
        os.symlink(victim, os.path.join(d, "lnk"))
        rc, o, e = run_worker(py, "set", d, "lnk", text1, "32")
        ck("W5 a name that is a link is refused and the link's target is not touched", rc != 0 and "not a plain file" in e and open(victim).read() == "untouched\n", repr((rc, e)))
        rc, o, e = run_worker(py, "delete", d, "lnk")
        ck("W6 delete of a link is refused too and leaves the link", rc != 0 and os.path.islink(os.path.join(d, "lnk")) and open(victim).read() == "untouched\n", repr((rc, e)))
        if os.path.lexists(os.path.join(d, "lnk")):
            os.unlink(os.path.join(d, "lnk"))
        os.mkdir(os.path.join(d, "dirjob"))
        rc, o, e = run_worker(py, "set", d, "dirjob", text1, "32")
        ck("W7 a name that is a directory is refused", rc != 0 and "not a plain file" in e and os.path.isdir(os.path.join(d, "dirjob")), repr((rc, e)))
        shutil.rmtree(os.path.join(d, "dirjob"), ignore_errors=True)
        if os.path.isfile(os.path.join(d, "dirjob")):
            os.unlink(os.path.join(d, "dirjob"))

        realdir = os.path.join(tmp, "real")
        os.mkdir(realdir, 0o755)
        link = os.path.join(tmp, "etc", "linkd")
        os.symlink(realdir, link)
        open(os.path.join(realdir, "a"), "w").write(text1)
        rc, o, e = run_worker(py, "set", link, "b", text1, "32")
        rcd, od, ed = run_worker(py, "delete", link, "a")
        rcl, ol, el = run_worker(py, "list", link)
        ck("W8 a jobs directory that is a link is refused by set, delete and list: nothing is made, removed or read behind it", rc != 0 and rcd != 0 and rcl != 0 and ol == "" and os.listdir(realdir) == ["a"],
           repr((rc, rcd, rcl, os.listdir(realdir))))
        wd = os.path.join(tmp, "etc", "wd")
        os.mkdir(wd)
        os.chmod(wd, 0o777)
        rc, o, e = run_worker(py, "set", wd, "a", text1, "32")
        os.chmod(wd, 0o775)
        rc3, o3, e3 = run_worker(py, "set", wd, "a", text1, "32")
        ck("W9 a directory that group or other can write is refused (0777 and 0775), nothing written", rc != 0 and rc3 != 0 and os.listdir(wd) == [], repr((rc, rc3, e3)))
        rc, o, e = run_worker(py, "set", d, "Bad", text1, "32")
        ck("W10 the worker re-checks the name itself", rc != 0 and "Bad" not in os.listdir(d), repr((rc, e)))

        # ---- (5) the list
        run_worker(py, "set", d, "good", "# t\nname=good\njob=check-masters\ncommand=check.masters\nschedule=hourly\noncalendar=*-*-* *:00:00\n", "32")
        variants = {
            "extrakey": "# t\nname=extrakey\njob=check-masters\ncommand=check.masters\nschedule=hourly\noncalendar=*-*-* *:00:00\nextra=1\n",
            "missing": "# t\nname=missing\njob=check-masters\ncommand=check.masters\nschedule=hourly\n",
            "othername": "# t\nname=zzz\njob=check-masters\ncommand=check.masters\nschedule=hourly\noncalendar=*-*-* *:00:00\n",
            "badcmd": "# t\nname=badcmd\njob=check-masters\ncommand=rm -rf /\nschedule=hourly\noncalendar=*-*-* *:00:00\n",
            "badcal": "# t\nname=badcal\njob=check-masters\ncommand=check.masters\nschedule=hourly\noncalendar=*-*-* *:07:00\n",
            "badid": "# t\nname=badid\njob=evil\ncommand=check.masters\nschedule=hourly\noncalendar=*-*-* *:00:00\n",
            "dupkey": "# t\nname=dupkey\nname=dupkey\njob=check-masters\ncommand=check.masters\nschedule=hourly\noncalendar=*-*-* *:00:00\n",
            "big": "# " + "x" * 5000 + "\nname=big\n",
        }
        for n, t in variants.items():
            open(os.path.join(d, n), "w").write(t)
        open(os.path.join(d, "Stray"), "w").write("x")
        open(os.path.join(d, ".new.123"), "w").write("x")
        os.symlink(victim, os.path.join(d, "linked"))
        rc, o, e = run_worker(py, "list", d)
        rows = [ln.split("\t") for ln in o.splitlines()]
        kinds = {r[1]: r[0] for r in rows}
        # run the helper's own list_line on each row, as the verb does
        script = HEAD + blk + "\nwhile IFS=$'\\t' read -r a b c d2 e f g; do job_list_line \"$a\" \"$b\" \"$c\" \"$d2\" \"$e\" \"$f\" \"$g\"; done <<<\"$ROWS\"\n"
        env = dict(os.environ, ROWS=o)
        _rc, shown, serr = bash(script, env=env)
        lines = {ln.split(":")[0].split(" ", 1)[1]: ln for ln in shown.splitlines() if ln.startswith(("job ", "damaged "))}
        good_line = lines.get("good", "")
        damaged = [n for n in list(variants) + ["Stray", "linked"] if not lines.get(n, "").startswith("damaged ")]
        ck("L1 a good definition is shown as one 'job' line with its schedule, its sentence and its id", good_line == "job good: hourly: check.masters (check-masters)", repr(good_line))
        ck("L2 every damaged definition (a stray or missing or doubled key, another name, a command or a calendar that is not the helper's, an unknown id, over 4 KB), a stray file and a link is 'damaged', never a job",
           not damaged and "linked" in kinds and kinds.get("linked") == "BAD", repr((damaged, kinds, serr[:200])))
        ck("L3 a dotfile (the worker's temp file) is not listed", ".new.123" not in kinds and ".new.123" not in shown, repr(shown[:200]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # ---- (6) the verbs, through the real script
    td = tempfile.mkdtemp(prefix="jobs-s-")
    try:
        script = os.path.join(td, "sd-elevate")
        open(script, "w").write(elev)
        os.chmod(script, 0o755)
        jd = os.path.join(td, "scratch", "jobs.d")
        env = dict(os.environ, SD_JOBS_DIR=jd)

        def run(*a):
            p = subprocess.run([script] + list(a), capture_output=True, text=True, env=env, timeout=60)
            return p.returncode, p.stdout + p.stderr

        rc, o = run("--dry-run", "job-set", "nightly", "backup-all", "daily", "02:30")
        ck("V1 job-set --dry-run prints the name, the sentence, the id, the schedule, the OnCalendar and where the definition would go, and writes nothing",
           rc == 0 and 'job-set nightly: runs "backup.account all" (backup-all) daily 02:30, OnCalendar=*-*-* 02:30:00, definition in %s/nightly' % jd in o and not os.path.exists(os.path.dirname(jd)), repr((rc, o)))
        refused = []
        for args in (["job-set"], ["job-set", "a", "backup-all"], ["job-set", "A", "backup-all", "hourly"], ["job-set", "a", "rm", "hourly"], ["job-set", "a", "backup-all", "every", "7", "minutes"],
                     ["job-set", "a", "backup-all", "monthly", "31", "01:00"], ["job-delete"], ["job-delete", "a", "b"], ["job-delete", "A"], ["job-delete", "../x"], ["job-list", "x"]):
            rc, o = run("--dry-run", *args)
            if rc == 0:
                refused.append(args)
        ck("V2 a missing or extra argument, a bad name, a command that is not an id and a schedule that is not one of the five are refused (dry run)", not refused, repr(refused))
        rc, o = run("--dry-run", "job-delete", "nightly")
        rc2, o2 = run("--dry-run", "job-list")
        ck("V3 job-delete and job-list --dry-run say what they would do and touch nothing", rc == 0 and "removes %s/nightly" % jd in o and rc2 == 0 and "the definitions in %s" % jd in o2 and not os.path.exists(os.path.dirname(jd)), repr((o, o2)))
        rc, o = run("job-set", "nightly", "backup-all", "daily", "02:30")
        rc2, o2 = run("job-delete", "nightly")
        rc3, o3 = run("job-list")
        ck("V4 a real run as an ordinary user dies at need_root, before anything is made", rc != 0 and rc2 != 0 and rc3 != 0 and "must run as root" in o and "must run as root" in o2 and "must run as root" in o3 and not os.path.exists(os.path.dirname(jd)), repr((o, o2, o3)))

        verb = elev[elev.find("  job-set)"):elev.find("  totp-status|totp-begin")]
        a, b, c, e_ = (verb.find(p) for p in ("job_check", "need_root", "job_caller", "python3 -I -c \"$JOBS_PY\" set"))
        ck("V5 job-set: the checks, then need_root, then the caller, then the write; the worker runs under python3 -I", 0 <= a < b < c < e_, repr((a, b, c, e_)))
        d1, d2 = verb.find("job_name_ok"), verb.find("python3 -I -c \"$JOBS_PY\" delete")
        l1, l2 = verb.find("job-list)"), verb.find("python3 -I -c \"$JOBS_PY\" list")
        ck("V6 job-delete checks the name before need_root and the caller before the delete; job-list asks the caller before it reads", 0 <= d1 < verb.find("need_root", d1) < verb.find("job_caller", d1) < d2 and verb.find("job_caller", l1) < l2, "")
        ck("V7 the success lines are the ones the jobs page will anchor on: 'job NAME created|replaced|deleted' and 'no job named NAME; nothing was changed'",
           "printf '%s: job %s %s\\n' \"$PROG\" \"$JB_NAME\" \"$js_how\"" in verb and "no job named %s; nothing was changed" in verb, "")
        ck("V8 SD_JOBS_DIR is the real directory unless a dry run or a non-root process (reset in main next to the other knobs), and is /etc/sdcore/jobs.d",
           re.search(r"else\n(?:  SD_[A-Z_]+=\$SD_[A-Z_]+_REAL\n)*  SD_JOBS_DIR=\$SD_JOBS_DIR_REAL\nfi", elev) is not None and "SD_JOBS_DIR_REAL=/etc/sdcore/jobs.d" in elev, "")
        ck("V9 the worker is only ever given the helper's own directory variable and a name that job_check passed (no verb passes a caller's path)", len(re.findall(r'JOBS_PY" (set|delete|list) "\$SD_JOBS_DIR"', elev)) == 3, "")
    finally:
        shutil.rmtree(td, ignore_errors=True)

    ck("U1 sudoers gives the job verbs to nobody new: no line names job-set, job-delete or job-list, and %sdusers' lines are not widened", "job-" not in sudoers, "")
    ck("U2 the usage text lists the three verbs", all(("sd-elevate [--dry-run] %s" % v) in elev for v in ("job-set", "job-delete", "job-list")), "")
    jr = deleter.find("rm -rf /etc/sdcore/jobs.d")
    rd = deleter.find("rmdir /etc/sdcore ")
    ck("U3 the deleter removes /etc/sdcore/jobs.d before it removes /etc/sdcore (rmdir), and says so", 0 <= jr < rd and "jobs.d" in deleter[jr:rd + 200], repr((jr, rd)))
    return out


def mutants(elev, deleter, sudoers):
    res = []

    def mut(name, target, old, new, count=1):
        text = {"elev": elev, "del": deleter, "sudo": sudoers}[target]
        if old not in text:
            res.append((name, None))
            return
        t = text.replace(old, new, count)
        res.append((name, (t if target == "elev" else elev, t if target == "del" else deleter, t if target == "sudo" else sudoers)))

    mut("N1 a trailing dash is allowed", "elev", "^[a-z]([a-z0-9-]{0,30}[a-z0-9])?$", "^[a-z]([a-z0-9-]{0,31})?$")
    mut("N1 an upper case letter is allowed", "elev", "^[a-z]([a-z0-9-]{0,30}[a-z0-9])?$", "^[A-Za-z]([A-Za-z0-9-]{0,30}[a-z0-9])?$")
    mut("N2 the sentence is accepted as an id", "elev", "    *) JB_SENTENCE=; return 1 ;;", "    'backup.account all') JB_SENTENCE='backup.account all' ;;\n    *) JB_SENTENCE=; return 1 ;;")
    mut("N2 an id gets another sentence", "elev", "sync-masters)    JB_SENTENCE='sync.masters' ;;", "sync-masters)    JB_SENTENCE='sync.masters now' ;;")
    mut("S1 a 7-minute interval is allowed", "elev", "$2 =~ ^(5|10|15|20|30)$", "$2 =~ ^([0-9]|[1-5][0-9])$")
    mut("S1 daily 24:00 is allowed", "elev", "^([01][0-9]|2[0-3]):([0-5][0-9])$", "^([01][0-9]|2[0-4]):([0-5][0-9])$")
    mut("S1 monthly 31 is allowed", "elev", "^([1-9]|1[0-9]|2[0-8])$", "^([1-9]|[12][0-9]|3[01])$")
    mut("S1 weekly sun is Mon", "elev", "sun) d=Sun ;;", "sun) d=Mon ;;")
    mut("S1 the OnCalendar of an interval drops the zero", "elev", 'JB_CAL="*-*-* *:0/$2:00"', 'JB_CAL="*-*-* *:/$2:00"')
    mut("W1 the file mode is not set", "elev", "            os.fchmod(f, 0o644)\n", "")
    mut("W4 the limit is off by one", "elev", ">= int(sys.argv[5])", "> int(sys.argv[5])")
    mut("W1 the directories are left to the umask", "elev", "                os.chmod(p, 0o755)\n", "")
    mut("W5 any file type may be replaced", "elev", 'die(name + " is not a plain file; it was left as it is")\n            existed = True', "existed = True")
    mut("W8 the directory may be a link", "elev", "fd = os.open(d, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)", "fd = os.open(d, os.O_RDONLY | os.O_DIRECTORY)")
    mut("W9 a group-writable directory is accepted", "elev", "(st.st_mode & 0o022)", "(st.st_mode & 0o002)")
    mut("W10 the worker does not re-check the name", "elev", '        if not NAME.match(name):\n            die("not a job name")\n        try:\n            old = os.stat(name, dir_fd=fd, follow_symlinks=False)\n            if not', "        try:\n            old = os.stat(name, dir_fd=fd, follow_symlinks=False)\n            if not")
    mut("L2 a definition with a command of its own is shown as a job", "elev", "[[ $f_cmd == \"$JB_SENTENCE\" ]] && ", "")
    mut("L2 the stored calendar is not compared", "elev", ' && [[ $f_sched == "$JB_SCHED" && $f_cal == "$JB_CAL" ]]', ' && [[ $f_sched == "$JB_SCHED" ]]')
    mut("L2 the name key need not be the file name", "elev", "[[ $f_name == \"$n\" ]] && job_command", "job_command")
    mut("V5 need_root comes before the checks", "elev", "    job_check \"$@\"\n    printf '%s: job-set", "    need_root\n    job_check \"$@\"\n    printf '%s: job-set")
    mut("V5 job-set does not ask the caller", "elev", "    need_root\n    job_caller\n    js_how=$(python3 -I -c \"$JOBS_PY\" set", "    need_root\n    js_how=$(python3 -I -c \"$JOBS_PY\" set")
    mut("V8 SD_JOBS_DIR is never reset", "elev", "  SD_JOBS_DIR=$SD_JOBS_DIR_REAL\nfi", "fi")
    mut("U1 sudoers names a job verb", "sudo", "ALL=(root)", "ALL=(root) /usr/local/sbin/sd-elevate job-set *, ", 1)
    mut("U3 the deleter keeps the jobs", "del", "rm -rf /etc/sdcore/jobs.d", "true")
    return res


def main():
    for p in (ELEVATE, SUDOERS, DELETER):
        if not os.path.isfile(p):
            print("test-jobs-elevate-units: CANNOT RUN - no %s" % p)
            return 2
    elev, sudoers, deleter = open(ELEVATE).read(), open(SUDOERS).read(), open(DELETER).read()
    if "--selftest" in sys.argv:
        base = checks(elev, deleter, sudoers)
        if not all(ok for _, ok, _ in base):
            print("selftest: CANNOT RUN - the unmutated sources already fail:")
            for n, ok, d in base:
                if not ok:
                    print("  FAIL %s (%s)" % (n, d))
            return 2
        bad = 0
        ms = mutants(elev, deleter, sudoers)
        for name, trio in ms:
            if trio is None:
                print("  [NOT APPLIED] %s" % name)
                bad += 1
                continue
            caught = [n[:3] for n, ok, _ in checks(*trio) if not ok]
            print("  [%s] %s%s" % ("caught" if caught else "MISSED", name, "  (%s)" % ", ".join(caught[:4]) if caught else ""))
            bad += 0 if caught else 1
        print("test-jobs-elevate-units --selftest: %d mutant(s), %d not caught" % (len(ms), bad))
        return 1 if bad else 0
    res = checks(elev, deleter, sudoers)
    fails = 0
    for name, ok, detail in res:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, "" if ok or not detail else "  (" + str(detail)[:400] + ")"))
        fails += 0 if ok else 1
    print("test-jobs-elevate-units: %d checks, %d failed" % (len(res), fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
