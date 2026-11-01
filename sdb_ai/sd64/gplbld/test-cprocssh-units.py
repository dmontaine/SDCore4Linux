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
    row("K$ADMINISTRATOR is set at three places and all are in CPROC (the install arm, the local arm, the ssh arm)", sites == {"cproc": 3}, "%s" % sites)
    row("the local arm's line is exactly the one the sandbox tools patch by its text", code.count(LOCAL_LINE) == 1, "")
    i = code.find("\n      end else", code.find(LOCAL_LINE))      # the OUTER else (six spaces): the inner one of the local arm has nine
    arm = code[i:code.find("$endif", i)]
    row("the ssh arm is the else of the local test and is for the user sdsys only", arm.count("if downcase(kernel(K$USERNAME, 0)) = 'sdsys' then") == 1, "")
    a = arm.find("if kernel(K$LOGIN.UID, 'sdsys') = 1 then")
    g = arm.find("kernel(K$ADMINISTRATOR, 1)")
    row("the ssh arm asks the kernel whether the login was sdsys's own BEFORE it grants, and grants once", 0 <= a < g and arm.count("kernel(K$ADMINISTRATOR, 1)") == 1, "")
    after = arm[g:]
    e = after.find("end else")
    refusal = after[e:]
    row("a login that was not sdsys's gets 10195 and abort.cproc, with the audit line of the local arm",
        e > 0 and "sysmsg(10195)" in refusal and "goto abort.cproc" in refusal and "elevation refused reason=sdsys session without a sdsys login" in refusal, "")
    row("the grant is audited as a login over ssh, from the first field of SSH_CONNECTION, 'unknown' when there is none",
        "from.addr = field(env('SSH_CONNECTION'), ' ', 1)" in arm and "if from.addr = '' then from.addr = 'unknown'" in arm
        and "'elevation granted reason=sdsys login over ssh from=' : from.addr" in arm and arm.find("from.addr =") < arm.find("K$AUDIT"), "")
    row("the grant is audited AFTER the administrator bit is set (a trail must not record rights not yet given)", g < arm.find("elevation granted"), "")
    row("the old refusal 10191 is used nowhere in CPROC any more", "10191" not in code, "")
    return rows


MUTANTS = [
    ("the ssh arm grants without asking the kernel", "if kernel(K$LOGIN.UID, 'sdsys') = 1 then\n               void kernel(K$ADMINISTRATOR, 1)", "if 1 then\n               void kernel(K$ADMINISTRATOR, 1)"),
    ("the ssh arm does not refuse a login that was not sdsys's", "               void kernel(K$AUDIT, 'elevation refused reason=sdsys session without a sdsys login')\n               goto abort.cproc\n            end\n         end\n      end",
     "               void kernel(K$AUDIT, 'elevation refused reason=sdsys session without a sdsys login')\n            end\n         end\n      end"),
    ("the ssh arm refuses with the old message", "refuse.msg = sysmsg(10195)   ;* several lines: one DISPLAY each\n               loop", "refuse.msg = sysmsg(10191)   ;* several lines: one DISPLAY each\n               loop"),
    ("the grant is not said to be over ssh", "'elevation granted reason=sdsys login over ssh from=' : from.addr", "'elevation granted reason=sdsys login from=' : from.addr"),
    ("no address when there is none", "               if from.addr = '' then from.addr = 'unknown'\n", ""),
    ("the address is the second field", "field(env('SSH_CONNECTION'), ' ', 1)", "field(env('SSH_CONNECTION'), ' ', 2)"),
    ("a second grant is added", "               admin.notice<-1> = sysmsg(10916)\n            end else\n               refuse.msg", "               admin.notice<-1> = sysmsg(10916)\n               void kernel(K$ADMINISTRATOR, 1)\n            end else\n               refuse.msg"),
    ("the local arm's line changes", LOCAL_LINE, LOCAL_LINE.replace("env('SSH_TTY') = ''", "env('SSH_TTY') = \"\"")),
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
