#!/usr/bin/env python3
# test-cprocssh-units.py - CPROC's arm for an sdsys session that came over ssh (S.95, 1 Nov 2026), read off sdsys/gpl.bp/cproc as TEXT with the comments taken out:
# the administrator bit is set at three places only and all three are in CPROC; the ssh arm grants ONLY after the kernel has said the login was sdsys's own
# (K$LOGIN.UID), refuses with 10195 and goes to abort.cproc when it was not (su sdsys without a dash keeps SSH_CONNECTION), audits the grant with the client address of
# SSH_CONNECTION ('unknown' when there is none) and no longer uses the old refusal 10191; and the local arm's line is the one the sandbox tools patch by its exact text.
# It cannot say the arm grants or refuses at run time: sandbox-gates.py rows 0c, 0c' and 0d drive it as the sandbox user (the login test patched true), and
# witness-absence.sh M12 does it on a real install.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-cprocssh-units.py [--selftest]
# Free: no install, no sudo.  Exit 0 all rows pass (or every mutant killed), 1 a row failed (a mutant survived), 2 it could not run.

import os
import re
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
BP = os.path.join(os.path.dirname(HERE), "sdsys", "gpl.bp")
CPROC = os.path.join(BP, "cproc")
LOCAL_LINE = "if downcase(kernel(K$USERNAME, 0)) = 'sdsys' and env('SSH_CONNECTION') = '' and env('SSH_TTY') = '' then"


def strip_comments(text):
    return "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("*"))


def rows_for(path, bp_dir):
    text = open(path, encoding="utf-8", errors="replace").read()
    code = strip_comments(text)
    rows = []

    def row(label, ok, detail=""):
        rows.append((label, bool(ok), detail))

    sites = {}
    for name in sorted(os.listdir(bp_dir)):
        p = path if name == "cproc" else os.path.join(bp_dir, name)
        if os.path.isfile(p):
            n = strip_comments(open(p, encoding="utf-8", errors="replace").read()).count("kernel(K$ADMINISTRATOR, 1)")
            if n:
                sites[name] = n
    row("K$ADMINISTRATOR is set at four places and all are in CPROC (the install arm, the scheduled job, the local arm, the ssh arm)", sites == {"cproc": 4}, "%s" % sites)
    row("the local arm's line is exactly the one the sandbox tools patch by its text", code.count(LOCAL_LINE) == 1, "")
    i = code.find("\n      end else", code.find(LOCAL_LINE))      # the OUTER else (six spaces): the inner one of the local arm has nine
    arm = code[i:code.find("$endif", i)]
    row("the ssh arm is the else of the local test and is for the user sdsys only", arm.count("if downcase(kernel(K$USERNAME, 0)) = 'sdsys' then") == 1, "")
    a = arm.find("if kernel(K$LOGIN.UID, 'sdsys') = 1 then\n")      # the grant's own test (2 Nov 26: S.101's line also begins so, and is not followed by a newline)
    g = arm.find("kernel(K$ADMINISTRATOR, 1)")
    row("the ssh arm asks the kernel whether the login was sdsys's own BEFORE it grants, and grants once", 0 <= a < g and arm.count("kernel(K$ADMINISTRATOR, 1)") == 1, "")
    after = arm[g:]
    e = after.find("end else")
    refusal = after[e:]
    row("a login that was not sdsys's gets 10195 and abort.cproc, with the audit line of the local arm",
        e > 0 and "sysmsg(10195)" in refusal and "goto abort.cproc" in refusal and "elevation refused reason=sdsys session without a sdsys login" in refusal, "")
    row("the grant is audited as a login over ssh, from the first field of SSH_CONNECTION, 'unknown' when there is none",
        "from.addr = field(env('SSH_CONNECTION'), ' ', 1)" in arm and "if from.addr = '' then from.addr = 'unknown'" in arm
        and "'elevation granted reason=sdsys login over ssh from=' : from.addr" in arm and arm.find("from.addr =") < arm.find("'elevation granted reason=sdsys login over ssh"), "")
    # 2 Nov 26 (S.101 stage B): each arm asks K$LOGIN.MARK for a login that is sdsys's own, BEFORE the grant, and refuses with 11190
    loc = code[code.find(LOCAL_LINE):i]                    # the local arm: its line to the outer else
    for name, part, kind in (("local", loc, "local"), ("ssh", arm, "ssh")):
        mk = part.find("if kernel(K$LOGIN.UID, 'sdsys') = 1 then lm.ok = kernel(K$LOGIN.MARK, '%s')" % kind)
        rf = part.find("if not(lm.ok) then")
        gr = part.find("kernel(K$ADMINISTRATOR, 1)", max(rf, 0))     # 2 Nov 26: the scheduled job's grant comes earlier in the local arm (S.102)
        row("S.101: the %s arm asks K$LOGIN.MARK('%s') only for a login that is sdsys's, refuses with 11190 and abort.cproc without it, all BEFORE the grant" % (name, kind),
            0 <= mk < rf < gr and "sysmsg(11190)" in part[rf:gr] and "goto abort.cproc" in part[rf:gr]
            and ("elevation refused reason=sdsys login without the authenticator code kind=%s" % kind) in part[rf:gr], "mark %d refuse %d grant %d" % (mk, rf, gr))
    keys_c = open(os.path.join(os.path.dirname(os.path.dirname(bp_dir)), "gplsrc", "keys.h"), encoding="utf-8").read()
    keys_b = open(os.path.join(bp_dir, "int$keys.h"), encoding="utf-8", errors="replace").read()
    m11190 = os.path.join(os.path.dirname(bp_dir), "messages", "11190")
    row("S.101: K$LOGIN.MARK is 171 in both gplsrc/keys.h and gpl.bp/int$keys.h, and message 11190 exists and says the code was not given",
        re.search(r"#define K_LOGIN_MARK\s+171\b", keys_c) is not None and re.search(r"\$define K\$LOGIN\.MARK\s+171\b", keys_b) is not None
        and os.path.isfile(m11190) and "authenticator code" in open(m11190, encoding="utf-8").read(), "")
    opk = open(os.path.join(os.path.dirname(os.path.dirname(bp_dir)), "gplsrc", "op_kernel.c"), encoding="utf-8").read()
    row("S.101: the kernel's test opens the status file and the marker without following a link, wants them root's and not writable by group or others, "
        "and an absent status file (no code enrolled) is the only absence that answers yes",
        "O_RDONLY | O_NOFOLLOW | O_CLOEXEC" in opk and "(st.st_uid != 0) || ((st.st_mode & 022) != 0)" in opk
        and "return absent;" in opk and 'snprintf(want, sizeof(want), "uid=%s ", luid);' in opk, "")
    # 2 Nov 26 (S.102 stage 3): the scheduled job's grant
    jb = loc.find("job.name = kernel(K$JOB.MARK, 0)")
    jg = loc.find("void kernel(K$ADMINISTRATOR, 1)", jb)
    ja = loc.find("void kernel(K$AUDIT, 'elevation granted reason=scheduled job')", jb)
    jgo = loc.find("goto elevation.done", jb)
    row("S.102: the local arm asks K$JOB.MARK FIRST (before any login question), grants only on a name, audits after the grant and jumps past the refusals to elevation.done",
        0 <= jb < jg < ja < jgo < loc.find("lm.ok = 1") and "if job.name # '' then" in loc[jb:jg] and code.count("elevation.done:") == 1
        and code.find("elevation.done:") > code.find("elevation refused reason=sdsys session without a sdsys login", code.find(LOCAL_LINE) + 1), "job %d grant %d audit %d goto %d" % (jb, jg, ja, jgo))
    row("S.102: K$JOB.MARK is 172 in gplsrc/keys.h and int$keys.h; the kernel compares the session's own single_command (no argument from BASIC), with sd_job_name, "
        "and audit_message() ends every record with job=<name>",
        re.search(r"#define K_JOB_MARK\s+172\b", keys_c) is not None and re.search(r"\$define K\$JOB\.MARK\s+172\b", keys_b) is not None
        and "sd_job_name(SD_JOB_CGROUP_FILE, SD_JOB_DIR, single_command, 0, jn, sizeof(jn))" in opk
        and 'snprintf(jmsg, sizeof(jmsg), "%s job=%s", msg, sd_job_active);' in open(os.path.join(os.path.dirname(os.path.dirname(bp_dir)), "gplsrc", "k_error.c"), encoding="utf-8").read(), "")
    row("S.101: the console's code is opt-in (owner, 2 Nov 26) - the kernel asks a local login for its marker only when the status file says 'scope all'",
        '(strcmp(kind, "local") == 0) && (strstr(pub, "\\nscope all\\n") == NULL)' in opk and "scope remote" not in opk, "")
    row("the grant is audited AFTER the administrator bit is set (a trail must not record rights not yet given)", g < arm.find("elevation granted"), "")
    row("the old refusal 10191 is used nowhere in CPROC any more", "10191" not in code, "")
    m11795 = os.path.join(os.path.dirname(bp_dir), "messages", "11795")
    txt = open(m11795, encoding="utf-8", errors="replace").read() if os.path.isfile(m11795) else ""
    row("the ssh arm's notice is 11795 with the client address, never the local arm's 10916 (which says 'a local session'); 11795 says over ssh and keeps the words witnesses find (SD administration granted)",
        "admin.notice<-1> = sysmsg(11795, from.addr)" in arm[:max(e + g, 0)] and "sysmsg(10916)" not in arm[:max(e + g, 0)] and txt.startswith("SD administration granted") and "over ssh" in txt and "%1" in txt, "")
    return rows


MUTANTS = [
    ("the ssh arm grants without asking the kernel", "if kernel(K$LOGIN.UID, 'sdsys') = 1 then\n               void kernel(K$ADMINISTRATOR, 1)", "if 1 then\n               void kernel(K$ADMINISTRATOR, 1)"),
    ("the ssh arm does not refuse a login that was not sdsys's", "               void kernel(K$AUDIT, 'elevation refused reason=sdsys session without a sdsys login')\n               goto abort.cproc\n            end\n         end\n      end",
     "               void kernel(K$AUDIT, 'elevation refused reason=sdsys session without a sdsys login')\n            end\n         end\n      end"),
    ("the ssh arm refuses with the old message", "refuse.msg = sysmsg(10195)   ;* several lines: one DISPLAY each\n               loop", "refuse.msg = sysmsg(10191)   ;* several lines: one DISPLAY each\n               loop"),
    ("the grant is not said to be over ssh", "'elevation granted reason=sdsys login over ssh from=' : from.addr", "'elevation granted reason=sdsys login from=' : from.addr"),
    ("no address when there is none", "               if from.addr = '' then from.addr = 'unknown'\n", ""),
    ("the address is the second field", "field(env('SSH_CONNECTION'), ' ', 1)", "field(env('SSH_CONNECTION'), ' ', 2)"),
    ("a second grant is added", "               admin.notice<-1> = sysmsg(11795, from.addr)\n            end else\n               refuse.msg", "               admin.notice<-1> = sysmsg(11795, from.addr)\n               void kernel(K$ADMINISTRATOR, 1)\n            end else\n               refuse.msg"),
    ("the ssh arm says 'a local session' again", "               admin.notice<-1> = sysmsg(11795, from.addr)\n", "               admin.notice<-1> = sysmsg(10916)\n"),
    ("the local arm's line changes", LOCAL_LINE, LOCAL_LINE.replace("env('SSH_TTY') = ''", "env('SSH_TTY') = \"\"")),
    # S.101 stage B (2 Nov 26)
    ("the local arm does not ask the marker", "lm.ok = kernel(K$LOGIN.MARK, 'local')", "lm.ok = 1"),
    ("the ssh arm does not ask the marker", "lm.ok = kernel(K$LOGIN.MARK, 'ssh')", "lm.ok = 1"),
    # S.102 stage 3 (2 Nov 26)
    ("any job name is granted without the kernel", "         job.name = kernel(K$JOB.MARK, 0)\n", "         job.name = 'x'\n"),
    ("the job's grant falls into the login refusals", "            goto elevation.done\n", ""),
    ("the job is asked after the login questions", "         job.name = kernel(K$JOB.MARK, 0)\n         if job.name # '' then", "         job.name = ''\n         if job.name # '' then"),
    ("the job is granted without the audit line", "            void kernel(K$AUDIT, 'elevation granted reason=scheduled job')   ;* the kernel ends the line with job=<name>\n", ""),
    ("a login without the code is refused but kept", "            void kernel(K$AUDIT, 'elevation refused reason=sdsys login without the authenticator code kind=local')\n            goto abort.cproc\n",
     "            void kernel(K$AUDIT, 'elevation refused reason=sdsys login without the authenticator code kind=local')\n"),
]


def main():
    print("test-cprocssh-units")
    if not os.path.isfile(CPROC):
        print("  CANNOT RUN - missing %s" % CPROC)
        return 2
    if "--selftest" not in sys.argv[1:]:
        rows = rows_for(CPROC, BP)
        bad = [r for r in rows if not r[1]]
        for label, ok, detail in rows:
            print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label, "" if ok or not detail else "  <- " + detail))
        print("test-cprocssh-units: %d passed, %d failed" % (len(rows) - len(bad), len(bad)))
        return 1 if bad or len(rows) < 8 else 0
    src = open(CPROC, encoding="utf-8", errors="replace").read()
    base = rows_for(CPROC, BP)
    if any(not r[1] for r in base):
        print("  control FAILED on the real source")
        return 1
    survivors = 0
    with tempfile.TemporaryDirectory() as td:
        for name, old, new in MUTANTS:
            if src.count(old) != 1:
                print("  CANNOT RUN - mutant %s: its text occurs %d times (wanted 1)" % (name, src.count(old)))
                return 2
            p = os.path.join(td, "cproc")
            open(p, "w", encoding="utf-8").write(src.replace(old, new))
            caught = [r for r in rows_for(p, BP) if not r[1]]
            print("  [%s] %s" % ("KILLED  " if caught else "SURVIVED", name))
            survivors += 0 if caught else 1
    print("%d of %d mutants killed" % (len(MUTANTS) - survivors, len(MUTANTS)))
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main())
