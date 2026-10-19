#!/usr/bin/env python3
"""test-fileswrite-units.py - the server-side WRITE GROUP of the files-only (SDNet) login, S.65, as invariants read off the source.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-fileswrite-units.py
  python3 .../test-fileswrite-units.py --selftest

No sudo, no install, no sd.  Exit 0 every check passed, 1 a check failed, 2 it could not run.  Written 18 Oct 26.

19 Oct 26 (K1, K4a): F15 bounds message 11521 at 100 characters (the SDNet client shows an ON ERROR reply's text cut there); F11 is rewritten for set.files after K4a - the write
group is read before the 'already had it' answer, FILES-OFF has nothing to do only for a person in neither group, the write group goes out FIRST and every group change is
change.files.group, which reads the membership back - with 13 new mutants (60 in all), one of which moves the write block after the group change (the 18 Oct order).  The
program itself is RUN by sandbox-filesgrp.py against a scratch group file.

THE RULE (owner, 18 Oct 2026, "yes"): a files-only login (the Linux group sdfiles) may CHANGE files on this server and take record or file locks only if
the user is ALSO in the Linux group sdfileswrite, which is off for a new account and given by SDSYS (modify.account <account> files-write-on).  The change
set is requests 7 to 10 (the locking reads), 16 to 19 (write, writeu, delete, deleteu), 30 (lock record), 31 (clearfile), 32 (filelock), 33 (fileunlock),
and any nonzero flag of 41 (readv takes a lock with flags 1, 2, 5 and 6).  Reads, selects, readv with flag 0, fileinfo, the indices, recordlocked and
release (15) need sdfiles alone.  A member of sdapi has the whole API as before.  And the dictionary open: apisrvr's vb.open takes "dict <file>" in any case.

***WHAT THIS IS, AND WHAT IT IS NOT.***  It reads the BASIC and shell sources as text with the comments removed, so a gate that survives only in a comment
does not count.  IT RUNS NOTHING, so it cannot say that the gate refuses anybody: sandbox-net.py (the REAL !apifilesok compiled and asked about every number
with the write flag 0 and 1; the words where no root is needed), sandbox-netfile.py section wgroup and netfake.py --selftest (the refusal and its evidence, on
the fake), sandbox-qmclient.py rows H0a to H0d (the dictionary open on a REAL API server) and the VM witness (a real files-only login refused on the wire).
What a text check is for here is ORDER and EXACT NAMES: the group name is spelt the same in nine places, the write flag is read in the one place that reads
the other group, the gate passes the login's own flag and not a constant, and the dictionary branch comes before the plain open.

--selftest runs every check on the real sources and then on a copy of them with one deliberate fault at a time: each must make a check fail.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.normpath(os.path.join(HERE, ".."))
ROOT = os.path.normpath(os.path.join(SD64, "..", ".."))
GPL = os.path.join(SD64, "sdsys", "gpl.bp")
SDSYS = os.path.join(SD64, "sdsys")

BP = ("apifilesok", "apisrvr", "modifya", "createa", "create_account", "acc_os_info", "restorea")
SH = {"installsdcore.sh": ROOT, "deletesdcore.sh": ROOT, "sd-elevate": HERE}

CHANGE = (7, 8, 9, 10, 16, 17, 18, 19, 30, 31, 32, 33)        # written here from the spec, not read from the program
ALLOWED = (1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 26, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 49)


def strip_bas(src):
    out = []
    for line in src.split("\n"):
        s = line.lstrip()
        if s.startswith("*") or s.startswith("!"):
            out.append("")
            continue
        cut = line.find(";*")
        out.append(line if cut < 0 else line[:cut])
    return "\n".join(out)


def strip_sh(src):
    return "\n".join("" if l.lstrip().startswith("#") else l for l in src.split("\n"))


def strip_strings(src):
    return re.sub(r"'[^'\n]*'|\"[^\"\n]*\"", "''", src)


def ordered(text, *needles):
    pos = -1
    for n in needles:
        p = text.find(n, pos + 1)
        if p < 0:
            return False
        pos = p
    return True


def routine_body(text, label):
    """From the line `label:` to the next line that starts a label (a word and a colon in column 1) or the end."""
    m = re.search(r"^%s:\s*$" % re.escape(label), text, re.M)
    if not m:
        return ""
    n = re.search(r"^[A-Za-z][A-Za-z0-9.$_]*:\s*$", text[m.end():], re.M)
    return text[m.start(): m.end() + (n.start() if n else len(text))]


def load():
    raw = {}
    for n in BP:
        with open(os.path.join(GPL, n), encoding="utf-8", errors="replace") as f:
            raw[n] = f.read()
    for n, d in SH.items():
        with open(os.path.join(d, n), encoding="utf-8", errors="replace") as f:
            raw[n] = f.read()
    with open(os.path.join(SDSYS, "syscom", "createacc.h"), encoding="utf-8", errors="replace") as f:
        raw["createacc.h"] = f.read()
    for num in (11480, 11521, 11522, 11523):
        try:
            with open(os.path.join(SDSYS, "messages", str(num)), encoding="utf-8", errors="replace") as f:
                raw["msg:%d" % num] = f.read()
        except OSError:
            raw["msg:%d" % num] = ""          # a message that is not there is a failed check (F15), not a program that cannot run
    return raw


def code(name, text):
    if name in SH:
        return strip_sh(text)
    if name.startswith("msg:") or name == "createacc.h":
        return text if name.startswith("msg:") else strip_bas(text)
    return strip_bas(text)


def model_filesok(fo, action, entered, writeok):
    """What !apifilesok answers, run in Python on the tables read from its source (the tests after them are held to this order by F2)."""
    ok = ",".join([""] + re.findall(r"^files\.ok := '(\d+),'", fo, re.M)) + ","
    chg = ",".join([""] + re.findall(r"^files\.chg := '(\d+),'", fo, re.M)) + ","
    if action == "":
        return 0
    if not re.fullmatch(r"[+-]?(?:\d+\.?\d*|\.\d+)", action):
        return 0
    if float(action) == 3:
        return 0 if entered else 1
    if ("," + action + ",") not in ok:
        return 0
    if writeok != 1 and ("," + action + ",") in chg:
        return 0
    return 1


def sysmsg_calls(text):
    out = []
    for m in re.finditer(r"sysmsg\(\s*(\d+)\s*(?:,([^)\n]*))?\)", text):
        args = [a.strip() for a in (m.group(2) or "").split(",") if a.strip()]
        out.append((int(m.group(1)), args))
    return out


def run_checks(raw):
    """{label: (ok, detail)} for every check, on these sources."""
    c = {n: code(n, t) for n, t in raw.items()}
    fo, ap, mo, cr, ca2, ai, rs = (c[n] for n in ("apifilesok", "apisrvr", "modifya", "createa", "create_account", "acc_os_info", "restorea"))
    inst, dele, se, hdr = c["installsdcore.sh"], c["deletesdcore.sh"], c["sd-elevate"], c["createacc.h"]
    res = {}

    def ck(label, ok, detail=""):
        res[label] = (bool(ok), detail)

    # ---- F1-F2. !apifilesok -------------------------------------------------------------------------------------------------------------
    chg = [int(x) for x in re.findall(r"^files\.chg := '(\d+),'", fo, re.M)]
    ok_nums = [int(x) for x in re.findall(r"^files\.ok := '(\d+),'", fo, re.M)]
    ck("F1 the change set is exactly 7 8 9 10 16 17 18 19 30 31 32 33, once each, starts from ',', and is a subset of the allow table (the table's own 37 numbers are untouched)",
       sorted(chg) == sorted(CHANGE) and re.search(r"^files\.chg = ','\s*$", fo, re.M) is not None and set(chg) <= set(ok_nums) and sorted(ok_nums) == sorted(ALLOWED),
       repr((sorted(set(chg) ^ set(CHANGE)), sorted(set(ok_nums) ^ set(ALLOWED)))))
    wrong = []
    for n in range(0, 81):
        for e in (0, 1):
            for w in (1, 0, 2):
                got = model_filesok(fo, str(n), e, w)
                if n == 3:
                    want = 0 if e else 1
                elif n not in ALLOWED:
                    want = 0
                elif w != 1 and n in CHANGE:
                    want = 0
                else:
                    want = 1
                if got != want:
                    wrong.append((n, e, w, got, want))
    ck("F2a the program's tables, run in Python for every request number 0 to 80, the account entered and not, the write flag exactly 1, 0 and 2, agree with the lists written "
       "out in this file: the change set is refused unless the flag is exactly 1, 3 is allowed once, everything else as before (a number wrong in either direction fails)",
       not wrong, repr(wrong[:6]))
    ck("F2b ...and the tests after the tables are exactly these, in this order: empty is 0, not a number is 0, 3 once, a number outside the allow table is 0, THEN a flag that is "
       "not exactly 1 (`writeok # 1`) refuses a number in the change set (commas on both sides), and the default is 1 - so the write group can only take away from the "
       "table, never add to it, and 7 cannot match 17",
       re.search(r"if action = '' then return 0\s*\n\s*if not\(num\(action\)\) then return 0\s*\n\s*if action = 3 then\s*\n\s*if entered then return 0\s*\n\s*return 1\s*\n"
                 r"\s*end\s*\n\s*if not\(index\(files\.ok, ',' : action : ',', 1\)\) then return 0\s*\n"
                 r"\s*if writeok # 1 then\s*\n\s*if index\(files\.chg, ',' : action : ',', 1\) then return 0\s*\n\s*end\s*\n\s*return 1\s*\n\s*end\s*$", fo) is not None
       and ordered(fo, "files.ok := ", "files.chg := ", "if action = '' then return 0"), "")
    ck("F2c ...it is still a $internal function catalogued once as !apifilesok with three parameters, and still PURE (no read, write, open, kernel call, execute, prompt)",
       "$internal" in fo and re.search(r"^function apifilesok\(action, entered, writeok\)\s*$", fo, re.M) is not None and re.search(r"^\$catalog !apifilesok\s*$", fo, re.M) is not None
       and not re.search(r"\b(?:kernel|read|readv|readu|open|openseq|openpath|write|writeu|writev|delete|execute|os\.execute|select|readnext|input|crt|display|print|call|gosub|goto|void)\b",
                         strip_strings(fo)), "")

    # ---- F3-F8. apisrvr -----------------------------------------------------------------------------------------------------------------
    cm_i = ap.find("common /$APISRVR/")
    cm = ap[cm_i:ap.find("seq.unbuf(SEQ.MAX)", cm_i)] if cm_i >= 0 else ""
    fi = ap.find("\nvb.scram.final:")
    fin = ap[fi:] if fi >= 0 else ""
    ck("F3 apisrvr declares the three-argument function, keeps the write flag in the COMMON block /$APISRVR/ beside files.only (a plain variable is set afresh by a runtime abort, "
       "which would hand a login the write group it has not got), and starts it false ONCE in the first-time block beside files.only",
       re.search(r"^deffun apifilesok\(action, entered, writeok\) calling '!apifilesok'\s*$", ap, re.M) is not None and re.search(r"^files\.write,", cm, re.M) is not None
       and len(re.findall(r"(?<![\w.])files\.write = @false", ap)) == 1 and ordered(ap, "if not(kernel(K$CPROC.LEVEL,0)) then", "files.only = @false", "files.write = @false", 'openpath "voc" to voc else'), "")
    ck("F4 THE READ: the group sdfileswrite is read ONCE, by scram.user, three-valued (the status read at once; a lookup that cannot answer refuses the login with its own reason and 10073), "
       "INSIDE the sdfiles route - after `api.files.login = @true`, inside `if not(api.in.sdapi) then`, and before the identity is assumed - so a member of sdapi never reads it "
       "and keeps the whole API; the flag starts false before the route is read",
       ap.count("is_grp_member(scram.user, 'sdfileswrite')") == 1
       and ordered(fin, "api.files.login = @false", "api.files.write = @false", "api.in.sdapi = is_grp_member(scram.user, 'sdapi')", "if not(api.in.sdapi) then",
                   "api.files.login = @true", "api.files.write = is_grp_member(scram.user, 'sdfileswrite')", "kernel(K$ASSUME.USER, scram.user)")
       and re.search(r"api\.files\.write = is_grp_member\(scram\.user, 'sdfileswrite'\)\s*\n\s*api\.write\.stat = status\(\)\s*\n\s*if api\.write\.stat # 0 then\s*\n"
                     r"\s*scram\.refuse\.reason = 'the sdfileswrite route could not be read, status ' : api\.write\.stat\s*\n\s*abort\.message = sysmsg\(10073, scram\.user\)\s*\n"
                     r"\s*server\.error = SV\$ON\.ERROR\s*\n\s*goto exit\.vb\.scram\.fail", fin) is not None, "")
    ck("F5 THE MARK: files.write takes the value api.files.write in the one place files.only is made true (inside `if api.files.login then`), after K$ASSUME.USER and before logged.in, "
       "is never cleared, and is assigned in exactly two places (the initialisation and that one); no other program mentions it",
       len(re.findall(r"(?<![\w.])files\.write\s*=(?!=)", ap)) == 2 and re.search(r"if api\.files\.login then\s*\n\s*files\.only = @true\s*\n\s*files\.write = api\.files\.write\s*\n", fin) is not None
       and ordered(fin, "kernel(K$ASSUME.USER, scram.user)", "if api.files.login then", "files.write = api.files.write", "logged.in = @true")
       and not any(re.search(r"(?<![\w.])files\.write(?![\w.])", t) for n, t in c.items() if n not in ("apisrvr",) and n in BP), "")
    gi = ap.find("if files.only then")
    gb = ap[gi:ap.find("cproc.date = date()", gi)] if gi >= 0 else ""
    ck("F6 THE GATE passes the LOGIN'S OWN flag (files.write), not a constant; the refusal is audited with write=on|off (lower case) BEFORE the error is set; the text is 11521 only when "
       "the same request WOULD be allowed with the group (the flag is false and the call with @true says yes), 11480 otherwise; both go to return.status.set",
       "if not(apifilesok(action, master.login.done, files.write)) then" in gb
       and re.search(r"if files\.write then write\.word = 'on' else write\.word = 'off'\s*\n\s*void kernel\(K\$AUDIT, 'api refused request=' : action : ' route=sdfiles write=' : write\.word : ' user=' : @logname\)", gb) is not None
       and re.search(r"if not\(files\.write\) and apifilesok\(action, master\.login\.done, @true\) then\s*\n\s*abort\.message = sysmsg\(11521, action\)[^\n]*\n\s*end else\s*\n"
                     r"\s*abort\.message = sysmsg\(11480, action\)", gb) is not None
       and ordered(gb, "kernel(K$AUDIT", "server.error = SV$ON.ERROR", "sysmsg(11521, action)", "sysmsg(11480, action)", "st = status()", "goto return.status.set")
       and ap.count("apifilesok(") == 3, "")
    ck("F7 the login is audited with the flag: 'api login route=sdfiles write=' : on|off : ' user=' - after the mark, before logged.in; no other audit line of the route lacks it",
       "void kernel(K$AUDIT, 'api login route=sdfiles write=' : write.word : ' user=' : scram.user)" in fin
       and ordered(fin, "if files.write then write.word = 'on' else write.word = 'off'", "'api login route=sdfiles write='", "logged.in = @true")
       and ap.count("route=sdfiles") == 3, "")
    rv = ap.find("\nvb.readv:")
    rvb = ap[rv: ap.find("case flags = 0", rv)] if rv >= 0 else ""
    ck("F8 vb.readv: request 41 is in the allow table for a plain READV, so the LOCKING forms (flags 1, 2, 5, 6; the code refuses any nonzero flag) are refused HERE for a files-only login "
       "without the group - after check.file and the flags are read, BEFORE any read or lock, audited as request 41 with write=off, answered with 11521 naming 41",
       ordered(rvb, "gosub check.file", "flags = oconv(cmnd[3,2], 'ISL')", "if files.only and not(files.write) and flags # 0 then",
               "'api refused request=41 route=sdfiles write=off user=' : @logname", "server.error = SV$ON.ERROR", "abort.message = sysmsg(11521, 41)", "return", "id = cmnd[9,99]"), repr(rvb[-300:]))
    vo = ap.find("\nvb.open:")
    vob = ap[vo: ap.find("\nvb.close:", vo)] if vo >= 0 else ""
    ck("F9 THE DICTIONARY OPEN: vb.open takes a name that begins with the word dict in ANY case and one space (upcase(cmnd[1,5]) = 'DICT ') as OPEN 'DICT', trim(the rest), BEFORE the plain "
       "`open cmnd`, which stays for every other name; both arms keep the trusted-file refusal and the same ELSE; the SDCLIENT / SDNet test above them is untouched, so the dictionary "
       "is as gated as the file",
       ordered(vob, "if kernel(K$SDNET, -1)  or config(\"SDCLIENT\") # 0 then", "if upcase(cmnd[1,5]) = 'DICT ' then", "open 'DICT', trim(cmnd[6,9999]) to files(i)", "end else", "open cmnd to files(i)")
       and vob.count("FL$FLAGS.TRUSTED") == 2 and vob.count("else server.error = SV$ELSE") == 2 and "cmnd[1,5] = 'DICT '" not in vob, repr(vob[-400:]))

    # ---- F10-F13. the words -------------------------------------------------------------------------------------------------------------
    sf = routine_body(mo, "set.files")
    ck("F10 MODIFY.ACCOUNT: FILES-WRITE-ON and FILES-WRITE-OFF are words (files.grp = 'sdfileswrite', files.want true / false, set.files, stop), in the syntax lines and in the list of words; "
       "FILES-ON / FILES-OFF set files.grp = 'sdfiles' (the helper takes the group from it)",
       all(re.search(r"case action = '%s'\s*\n\s*files\.grp = '%s'\s*\n\s*files\.want = @%s\s*\n\s*gosub set\.files\s*\n\s*stop" % (w, g_, b), mo)
           for w, g_, b in (("FILES-ON", "sdfiles", "true"), ("FILES-OFF", "sdfiles", "false"), ("FILES-WRITE-ON", "sdfileswrite", "true"), ("FILES-WRITE-OFF", "sdfileswrite", "false")))
       and "modify.account <account> files-on | files-off | files-write-on | files-write-off" in mo
       and "files-on, files-off, files-write-on, files-write-off, suspended or unsuspended" in mo and sf != "", "")
    cgf = routine_body(mo, "change.files.group")
    ck("F11 set.files: FILES-WRITE-ON is refused for a person who is not in sdfiles (11523, read three-valued) BEFORE the 'already had it' answer and before anything is run; "
       "(K4a, 19 Oct 26) for FILES-ON and FILES-OFF the write group is read too, three-valued (10081 when it cannot be read), BEFORE that answer, and FILES-OFF has nothing to do only for a "
       "person who is in NEITHER group - the orphan, in sdfileswrite and not in sdfiles, was told 'nothing changed' and kept the membership; the write group is taken out FIRST, before the group "
       "itself, so a failure of the second removal leaves read access and never write access without read; FILES-ON takes a stray write membership away BEFORE it adds sdfiles and stops "
       "with 10081 when it cannot; every group change is change.files.group, which reads the membership back; the line printed is 11522 for the write group (first, when it was taken "
       "away) and 11482 for the other, read back",
       ordered(sf, "has.files = is_grp_member(files.user, files.grp)", "has.write = is_grp_member(files.user, 'sdfileswrite')", "if files.grp = 'sdfileswrite' and files.want then",
               "in.files = is_grp_member(files.user, 'sdfiles')", "sysmsg(11523, acc.name)", "nothing.to.do = not(has.files) and not(has.write)", "nothing.to.do = (has.files = files.want)",
               "if nothing.to.do then", "sysmsg(10080, acc.name)", "files.found = is_group(files.grp)", "gosub change.files.group")
       and re.search(r"in\.files = is_grp_member\(files\.user, 'sdfiles'\)\s*\n\s*files\.stat = status\(\)\s*\n\s*if files\.stat # 0 then\s*\n\s*@system\.return\.code = -ER\$FAILED\s*\n"
                     r"\s*crt sysmsg\(10081, acc\.name, files\.stat\)\s*\n\s*return\s*\n\s*end\s*\n\s*if not\(in\.files\) then\s*\n\s*@system\.return\.code = -ER\$FAILED\s*\n"
                     r"\s*crt sysmsg\(11523, acc\.name\)[^\n]*\n\s*return\s*\n\s*end", sf) is not None
       and re.search(r"if files\.grp = 'sdfiles' then\s*\n\s*has\.write = is_grp_member\(files\.user, 'sdfileswrite'\)\s*\n\s*files\.stat = status\(\)\s*\n\s*if files\.stat # 0 then\s*\n"
                     r"\s*@system\.return\.code = -ER\$FAILED\s*\n\s*crt sysmsg\(10081, acc\.name, files\.stat\)\s*\n\s*return\s*\n\s*end", sf) is not None
       and ordered(sf, "write.removed = @false", "if files.grp = 'sdfiles' and has.write then", "cg.group = 'sdfileswrite'", "cg.want = @false", "gosub change.files.group",
                   "if files.stat # 0 then", "sysmsg(10081, acc.name, files.stat)", "return", "now.write = cg.now", "write.removed = @true",
                   "if files.grp = 'sdfiles' and not(files.want) and not(has.files) then", "now.files = @false", "end else", "cg.group = files.grp", "cg.want = files.want",
                   "gosub change.files.group", "now.files = cg.now")
       and sf.count("gosub change.files.group") == 2 and sf.count("os.execute") == 0 and cgf.count("os.execute") == 2
       and ordered(cgf, "cg.now = @false", "if cg.want then", 'sd-elevate addgroup " : files.user : " " : cg.group', "end else", 'sd-elevate delgroup " : files.user : " " : cg.group',
                   "files.stat = OS.ERROR()", "cg.now = is_grp_member(files.user, cg.group)", "files.stat = status()", "if files.stat = 0 and cg.now # cg.want then files.stat = 2")
       and ordered(sf, "sysmsg(11522, acc.name, if now.files then 'yes' else 'no')", "if write.removed then crt sysmsg(11522, acc.name, if now.write then 'yes' else 'no')",
                   "sysmsg(11482, acc.name, if now.files then 'yes' else 'no')"), "")
    ck("F12 createacc.h defines CA$FILESWRITE as 39 (after CA$SHARED.WRITE 38, unique); CREATEA: FILES-WRITE-ON sets it to 1 (nothing else does) and the syntax line names it; "
       "CREATE.ACCOUNT: a request is exactly 1, it needs FILES-ON (11523, before anything is made), the group sdfileswrite is looked for before the Linux user is made (10024), a group or "
       "other account is refused as for FILES-ON, the join is sd-elevate addgroup <user> sdfileswrite AFTER the sdfiles join, and the state line 11522 is read off /etc/group",
       re.search(r"\$define\s+CA\$FILESWRITE\s+39\b", hdr) is not None and len(re.findall(r"\$define\s+\S+\s+39\b", hdr)) == 1
       and re.search(r"case upcase\(token\) = 'FILES-WRITE-ON'\s*\n\s*settings<CA\$FILESWRITE> = 1\s*\n", cr) is not None and len(re.findall(r"settings<CA\$FILESWRITE>\s*=", cr)) == 1
       and "{files-on} {files-write-on} {no.query}" in cr
       and "files.write.want = (settings<CA$FILESWRITE> = 1)" in ca2
       and re.search(r"if files\.write\.want then\s*\n\s*if not\(files\.want\) then\s*\n\s*@system\.return\.code = -ER\$ARGS\s*\n\s*err = 11523:@vm:acc\.name[^\n]*\n\s*goto exit\.create\s*\n\s*end", ca2) is not None
       and ordered(ca2, "files.found = is_group('sdfiles')", "if files.write.want then", "err = 11523:@vm:acc.name", "files.found = is_group('sdfileswrite')", "err = 10024:@vm:'sdfileswrite'",
                   "if not(create_user(acc.uname)) then")
       and ca2.count("if files.want or files.write.want then") == 2
       and ordered(ca2, 'addgroup ":acc.uname:" sdfiles"', "if files.write.want then", 'addgroup ":acc.uname:" sdfileswrite"')
       and "sysmsg(11522, acc.name, if is_grp_member(acc.uname, 'sdfileswrite') then 'yes' else 'no')" in ca2, "")
    ck("F13 the manifest: route.files.write: 1|0 for a USER account from membership of sdfileswrite, right after route.files and before os.sh; RESTORE.ACCOUNT reads it (and clears it for each "
       "section), hands it on as CA$FILESWRITE only when route.files is 1 too, so a manifest without the key, or with the write group and no files route, restores as NOT in the group",
       ordered(ai, "'route.files: '", "'route.files.write: ':(if is_grp_member(user, 'sdfileswrite') then 1 else 0)", "'os.sh: '")
       and re.search(r"= 'route\.files\.write'\s*; m\.route\.files\.write = kv", rs) is not None and "m.route.files = '' ; m.route.files.write = ''" in rs
       and "if m.route.files = '1' and m.route.files.write = '1' then settings<CA$FILESWRITE> = 1" in rs and rs.count("CA$FILESWRITE") == 1, "")

    # ---- F14-F16. the group: installer, deletesdcore, sd-elevate; the messages ------------------------------------------------------------------
    ck("F14 the installer makes sdfileswrite with the other route groups (the one loop, groupadd --system, only when missing, so an upgrade install creates it empty and adds nobody); "
       "deletesdcore removes it with them only on a full DELETE and says it kept it otherwise; sd-elevate whitelists it by exact name for addgroup, delgroup and groupadd, never deletes it, "
       "and has no prefix pattern for it",
       re.search(r'for sd_route_group in sdssh sdapi sdfiles sdfileswrite; do\s*\n\s*if ! getent group "\$sd_route_group" &>/dev/null; then\s*\n(?:[^\n]*\n){0,2}?\s*sudo groupadd --system "\$sd_route_group"', inst) is not None
       and inst.count("for sd_route_group in") == 1 and "usermod" not in inst[inst.find("for sd_route_group in"): inst.find("for sd_route_group in") + 400].replace("sudo usermod -a -G sdusers root", "")
       and re.search(r'if \[ "\$keep_accts" = "DELETE" \]; then.*?for sd_route_group in sdssh sdapi sdfiles sdfileswrite; do.*?sudo groupdel "\$sd_route_group".*?\n\s*else\s*\n[^\n]*sdssh, sdapi, sdfiles and sdfileswrite were kept', dele, re.S) is not None
       and re.search(r"case \$group in\s*\n\s*sdusers\|sdssh\|sdapi\|sdfiles\|sdfileswrite\) : ;;", se) is not None
       and re.search(r"case \$1 in\s*\n\s*sdusers\|sdssh\|sdapi\|sdfiles\|sdfileswrite\)\s*\n\s*die", se) is not None and "sdfileswrite*" not in se and "sdfiles*" not in se, "")
    m21, m22, m23 = (raw["msg:%d" % n].strip("\n") for n in (11521, 11522, 11523))
    stray = []                                    # any other program of gpl.bp that writes one of the three numbers
    for fname in sorted(os.listdir(GPL)):
        if fname in ("apisrvr", "modifya", "create_account"):
            continue
        p = os.path.join(GPL, fname)
        if os.path.isfile(p):
            with open(p, encoding="utf-8", errors="replace") as f:
                if re.search(r"\b1152[123]\b", strip_bas(f.read())):
                    stray.append(fname)
    ck("F15 messages 11521 to 11523 exist, ONE line each, with the words they name in lower case (files-write-on, files-on); 11521 names the request (%1) and what the administrator can do, "
       "and is AT MOST 100 CHARACTERS with a request number in it (19 Oct 26, K1: the SDNet client shows an ON ERROR reply's text cut to 100 characters, gpl.bp/netfile clean.text, and the first text "
       "was 175 - the person at the client saw 'status 0' where the reason should have been); "
       "11522 is 'Account %1 has files-write %2' (lower case, the owner's rule: a keyword SD prints); and each is used where it should be and nowhere else: 11521 by apisrvr only, twice (the gate, ONE argument; vb.readv, request 41), "
       "11522 by MODIFY.ACCOUNT (twice since 19 Oct 26: the write words, and FILES-OFF / FILES-ON when the write group went too) and CREATE.ACCOUNT (once) with the account and yes or no, 11523 by MODIFY.ACCOUNT (sysmsg) and CREATE.ACCOUNT (err =) once each with the account",
       "\n" not in m21 and "\n" not in m22 and "\n" not in m23 and "%1" in m21 and "files-write-on" in m21 and m22 == "Account %1 has files-write %2" and "files-on" in m23 and "%1" in m23 and "FILES" not in m21 + m22 + m23
       and len(m21.replace("%1", "41")) <= 100 and len(m21.replace("%1", "41")) > 40
       and len(re.findall(r"sysmsg\(11521, (?:action|41)\)", ap)) == 2 and ap.count("11521") == 2 and mo.count("sysmsg(11522, acc.name, if now.files then 'yes' else 'no')") == 1
       and ca2.count("sysmsg(11522, acc.name, if is_grp_member(acc.uname, 'sdfileswrite') then 'yes' else 'no')") == 1 and mo.count("sysmsg(11523, acc.name)") == 1
       and ca2.count("err = 11523:@vm:acc.name") == 1 and mo.count("11522") == 2 and mo.count("sysmsg(11522, acc.name, if now.write then 'yes' else 'no')") == 1 and ca2.count("11522") == 1 and mo.count("11523") == 1 and ca2.count("11523") == 1
       and not any(re.search(r"\b1152[123]\b", c[n_]) for n_ in ("createa", "acc_os_info", "restorea", "apifilesok")) and not stray,
       repr((m21, m22, m23, stray)))
    return res


def mutants(raw):
    """(name, file, old, new): one deliberate fault at a time, applied to the RAW source (old must occur exactly once)."""
    M = []

    def m(name, f, old, new):
        M.append((name, f, old, new))
    # apifilesok
    m("a number of the change set is dropped (30)", "apifilesok", "files.chg := '30,'   ;* lock record\n", "")
    m("a plain read joins the change set (6)", "apifilesok", "files.chg := '7,'    ;* readl\n", "files.chg := '6,'    ;* read\nfiles.chg := '7,'    ;* readl\n")
    m("clearfile is no longer in the change set (31)", "apifilesok", "files.chg := '31,'   ;* clearfile\n", "")
    m("filelock is no longer in the change set (32)", "apifilesok", "files.chg := '32,'   ;* filelock\n", "")
    m("a number joins the change set that the table does not allow (20, call)", "apifilesok", "files.chg := '7,'    ;* readl\n", "files.chg := '20,'   ;* call\nfiles.chg := '7,'    ;* readl\n")
    m("the write flag is tested as a boolean, not as exactly 1", "apifilesok", "if writeok # 1 then", "if not(writeok) then")
    m("the write flag is ignored", "apifilesok", "if writeok # 1 then", "if 0 then")
    m("the change set is tested BEFORE the table (a number outside the table is answered by the wrong test)", "apifilesok",
      "if not(index(files.ok, ',' : action : ',', 1)) then return 0\n", "")
    m("the change set is refused without the commas (7 matches 17)", "apifilesok", "if index(files.chg, ',' : action : ',', 1) then return 0", "if index(files.chg, action, 1) then return 0")
    m("the default is 0", "apifilesok", "return 1\n\nend\n\n* END-CODE", "return 0\n\nend\n\n* END-CODE")
    m("the parameter is dropped", "apifilesok", "function apifilesok(action, entered, writeok)", "function apifilesok(action, entered)")
    # apisrvr
    m("the flag is not in the common block", "apisrvr", "files.write,        ;* 18 Oct 26", "filesx.write,        ;* 18 Oct 26")
    m("the flag is not started false", "apisrvr", "   files.write = @false       ;*", "   files.writex = @false       ;*")
    m("the login is given the write group unconditionally", "apisrvr", "files.write = api.files.write   ;*", "files.write = @true   ;*")
    m("the wrong group is read for the write flag", "apisrvr", "api.files.write = is_grp_member(scram.user, 'sdfileswrite')", "api.files.write = is_grp_member(scram.user, 'sdfiles')")
    m("the write group is not read three-valued", "apisrvr", "if api.write.stat # 0 then", "if 0 then")
    m("the gate passes true instead of the login's flag", "apisrvr", "if not(apifilesok(action, master.login.done, files.write)) then", "if not(apifilesok(action, master.login.done, @true)) then")
    m("the gate passes false instead of the login's flag", "apisrvr", "if not(apifilesok(action, master.login.done, files.write)) then", "if not(apifilesok(action, master.login.done, @false)) then")
    m("the refusal has no write word in the audit line", "apisrvr", "' route=sdfiles write=' : write.word : ' user=' : @logname)", "' route=sdfiles user=' : @logname)")
    m("the refusal always says 11480", "apisrvr", "abort.message = sysmsg(11521, action)", "abort.message = sysmsg(11480, action)")
    m("the login line has no write word", "apisrvr", "'api login route=sdfiles write=' : write.word : ' user='", "'api login route=sdfiles user='")
    m("the readv lock test is gone", "apisrvr", "if files.only and not(files.write) and flags # 0 then", "if 0 then")
    m("the readv test refuses only flag 1", "apisrvr", "if files.only and not(files.write) and flags # 0 then", "if files.only and not(files.write) and flags = 1 then")
    m("the readv test refuses a plain READV too", "apisrvr", "if files.only and not(files.write) and flags # 0 then", "if files.only and not(files.write) then")
    m("the readv test is made for every session, sdapi included", "apisrvr", "if files.only and not(files.write) and flags # 0 then", "if not(files.write) and flags # 0 then")
    m("the dictionary test is case sensitive", "apisrvr", "if upcase(cmnd[1,5]) = 'DICT ' then", "if cmnd[1,5] = 'DICT ' then")
    m("the dictionary open uses the whole name", "apisrvr", "open 'DICT', trim(cmnd[6,9999]) to files(i)", "open 'DICT', cmnd to files(i)")
    m("the dictionary open is not a dictionary open", "apisrvr", "open 'DICT', trim(cmnd[6,9999]) to files(i)", "open trim(cmnd[6,9999]) to files(i)")
    # modifya
    m("FILES-WRITE-ON sets the wrong group", "modifya", "         files.grp = 'sdfileswrite'\n         files.want = @true", "         files.grp = 'sdfiles'\n         files.want = @true")
    m("FILES-WRITE-OFF is not a word", "modifya", "case action = 'FILES-WRITE-OFF'", "case action = 'FILES-WRITE-OFFX'")
    m("the person need not be in sdfiles", "modifya", "      if not(in.files) then", "      if 0 then")
    m("files-off leaves the write group", "modifya", "if files.grp = 'sdfiles' and has.write then\n      cg.group = 'sdfileswrite'", "if 0 then\n      cg.group = 'sdfileswrite'")
    m("files-on leaves a stray write membership (K4a: it became write access at the next files-on)", "modifya", "if files.grp = 'sdfiles' and has.write then\n      cg.group = 'sdfileswrite'",
      "if files.grp = 'sdfiles' and has.write and not(files.want) then\n      cg.group = 'sdfileswrite'")
    m("the orphan (write group, not sdfiles) is told nothing changed", "modifya", "nothing.to.do = not(has.files) and not(has.write)", "nothing.to.do = not(has.files)")
    m("the write group is not read for the pair", "modifya", "if files.grp = 'sdfiles' then\n      has.write = is_grp_member(files.user, 'sdfileswrite')", "if 0 then\n      has.write = is_grp_member(files.user, 'sdfileswrite')")
    m("the write group is not read three-valued", "modifya", "has.write = is_grp_member(files.user, 'sdfileswrite')\n      files.stat = status()", "has.write = is_grp_member(files.user, 'sdfileswrite')\n      files.stat = 0")
    m("a failed removal of the write group does not stop the command", "modifya",
      "      gosub change.files.group\n      if files.stat # 0 then\n         @system.return.code = -ER$FAILED\n         crt sysmsg(10081, acc.name, files.stat)\n         return\n      end\n      now.write = cg.now",
      "      gosub change.files.group\n      now.write = cg.now")
    m("sdfiles is taken from a person who is not in it", "modifya", "if files.grp = 'sdfiles' and not(files.want) and not(has.files) then", "if 0 then")
    m("a group change is not read back", "modifya", "cg.now = is_grp_member(files.user, cg.group)", "cg.now = cg.want")
    m("a read back that differs is a success", "modifya", "if files.stat = 0 and cg.now # cg.want then files.stat = 2", "null")
    m("set.files runs the helper itself again (a second place that changes a group)", "modifya", "   write.removed = @false\n", "   write.removed = @false\n   os.execute \"sudo /usr/local/sbin/sd-elevate delgroup \" : files.user : \" sdfileswrite\"\n")
    m("the line for the write group that went is not printed", "modifya", "if write.removed then crt sysmsg(11522, acc.name, if now.write then 'yes' else 'no')", "if 0 then crt sysmsg(11522, acc.name, if now.write then 'yes' else 'no')")

    def write_group_last(t):
        """The block that takes the person out of sdfileswrite is moved to AFTER the group change: the order of the 18 Oct build."""
        i = t.index("   write.removed = @false\n")
        j = t.index("\n* The group itself")
        k = t.index("   if files.stat # 0 then\n      @system.return.code = -ER$FAILED\n      crt sysmsg(10081, acc.name, files.stat)\n      return\n   end\n\n   @system.return.code = 0")
        return t[:i] + t[j + 1:k] + t[i:j + 1] + t[k:]
    m("the write group is taken out AFTER sdfiles (the order that could leave the orphan)", "modifya", write_group_last, None)
    m("the write group's line is the other message", "modifya", "crt sysmsg(11522, acc.name, if now.files then 'yes' else 'no')", "crt sysmsg(11482, acc.name, if now.files then 'yes' else 'no')")
    # createa / create_account / restorea / acc_os_info
    m("FILES-WRITE-ON sets nothing", "createa", "settings<CA$FILESWRITE> = 1", "settings<CA$FILES> = 1")
    m("the write group is joined before the files group", "create_account", "      if files.write.want then\n         os.execute \"sudo /usr/local/sbin/sd-elevate addgroup \":acc.uname:\" sdfileswrite\"",
      "      if files.write.want then\n         os.execute \"sudo /usr/local/sbin/sd-elevate addgroup \":acc.uname:\" sdfiles\"")
    m("the write group needs no files-on", "create_account", "       if not(files.want) then\n         @system.return.code = -ER$ARGS\n         err = 11523",
      "       if 0 then\n         @system.return.code = -ER$ARGS\n         err = 11523")
    m("a group account is no longer refused the write group", "create_account", "     if files.want or files.write.want then\n       @system.return.code = -ER$ARGS\n       err = 10087",
      "     if files.want then\n       @system.return.code = -ER$ARGS\n       err = 10087")
    m("the manifest has no write key", "acc_os_info", "         info<-1> = 'route.files.write: ':(if is_grp_member(user, 'sdfileswrite') then 1 else 0)", "")
    m("the restore gives the write group without the files route", "restorea", "if m.route.files = '1' and m.route.files.write = '1' then", "if m.route.files.write = '1' then")
    # installers
    m("the installer does not make the group", "installsdcore.sh", "for sd_route_group in sdssh sdapi sdfiles sdfileswrite; do", "for sd_route_group in sdssh sdapi sdfiles; do")
    m("deletesdcore does not remove the group", "deletesdcore.sh", "for sd_route_group in sdssh sdapi sdfiles sdfileswrite; do", "for sd_route_group in sdssh sdapi sdfiles; do")
    m("sd-elevate does not whitelist the group", "sd-elevate", "    sdusers|sdssh|sdapi|sdfiles|sdfileswrite) : ;;", "    sdusers|sdssh|sdapi|sdfiles) : ;;")
    m("sd-elevate may delete the group", "sd-elevate", "      sdusers|sdssh|sdapi|sdfiles|sdfileswrite)\n        die", "      sdusers|sdssh|sdapi|sdfiles)\n        die")
    # messages
    m("message 11521 does not name the verb", "msg:11521", "files-write-on", "the-write-word")
    m("message 11521 is longer than the 100 characters the client shows (the first text was 175)", "msg:11521", "ask the administrator for", "ask the administrator of this server, who can allow it, for")
    m("message 11521 loses its place for the request", "msg:11521", "(request %1)", "(request)")
    m("message 11522 is another text", "msg:11522", "Account %1 has files-write %2", "Account %1 has write %2")
    m("message 11522 spells its keyword in capitals (the lower case rule)", "msg:11522", "Account %1 has files-write %2", "Account %1 has FILES-WRITE %2")
    m("message 11523 spells its keywords in capitals (the lower case rule)", "msg:11523", "so it cannot be given files-write:", "so it cannot be given FILES-WRITE:")
    return M


def main():
    raw = load()
    res = run_checks(raw)
    failed = [k for k, (ok, _d) in res.items() if not ok]
    for k, (ok, d) in res.items():
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", k[:400], "" if ok or not d else "   <- " + d[:500]))
    print("\ntest-fileswrite-units: %d checks, %d failed" % (len(res), len(failed)))
    print("NOT MEASURED HERE: whether the gate refuses anybody.  That is sandbox-net.py (the real !apifilesok), sandbox-netfile.py wgroup and netfake.py (the refusal on the fake), "
          "sandbox-qmclient.py H0a-H0d (the dictionary open on a real API server) and the VM witness.")
    if "--selftest" not in sys.argv:
        return 1 if failed else 0
    if failed:
        print("selftest: the real sources already fail %d check(s); the mutants say nothing until they pass" % len(failed))
        return 1
    survivors = 0
    ms = mutants(raw)
    for name, f, old, new in ms:
        if f not in raw:
            print("  [REFUSED ] %s - no such file %s" % (name, f))
            return 2
        if not callable(old) and raw[f].count(old) != 1:
            print("  [REFUSED ] %s - its text occurs %d times in %s, not once" % (name, raw[f].count(old), f))
            return 2
        mr = dict(raw)
        if callable(old):                      # a mutant made by a function of the source (19 Oct 26: the order of two blocks cannot be changed by one replacement)
            mr[f] = old(raw[f])
            if mr[f] == raw[f]:
                print("  [REFUSED ] %s - the function changed nothing in %s" % (name, f))
                return 2
        else:
            mr[f] = raw[f].replace(old, new)
        got = run_checks(mr)
        caught = [k.split(" ")[0] for k, (ok, _d) in got.items() if not ok]
        if caught:
            print("  [KILLED  ] %-84s | %s" % (name, " ".join(caught)))
        else:
            survivors += 1
            print("  [SURVIVED] %s" % name)
    print("%d of %d mutants killed" % (len(ms) - survivors, len(ms)))
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main())
