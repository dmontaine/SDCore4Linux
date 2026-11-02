#!/usr/bin/env python3
"""test-sdsysaccess-units.py - the sdsys user's write access to the user accounts, as invariants read off the source.

  python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-sdsysaccess-units.py
  python3 .../test-sdsysaccess-units.py --selftest

No sudo, no install, no sd.  Exit 0 every check passed, 1 a check failed, 2 it could not run.  Written 2 Nov 26 (S.96 M6).

WHERE IT CAME FROM.  These rows were part of test-masters-units.py (S.67 and F6, then S.103), which went with the master-file copies on 2 Nov 26
(S.96 M6, the owner's "retire").  What they hold is not about the copies and is still live: the administrator edits each account's own VOC,
dictionaries and programs in place (tool.entries), which needs the sdsys operating-system user in the account's group (S.103: "sdsys always read/write
access to the /home/sd tree") and needs a new VOC or dictionary to be writable by that group.  Rows S3b, S17g, S18, S18a, S19, S20, S20a and S21 keep
their old numbers so that the record can still be followed; the function masters_fix_modes is now dh_creat.c's acct_group_modes.

***WHAT IT IS NOT.***  It reads the C, BASIC and shell sources as text, with comments removed.  It cannot say that a group is joined, that a mode is
right on the disk or that sd-elevate refuses anybody: test-sd-elevate.py, test-accelevate-units.py and test-install-sdsysgroups.sh run those pieces,
and a real install (the VM) is the only place the groups and owners are real.

--selftest breaks each fact in the way an edit plausibly would and requires some check to notice; a mutant nothing catches, or that changes nothing,
is a FAILURE of the self-test.  --selftest --from=N runs the mutants from number N on.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.abspath(os.path.join(HERE, os.pardir))
SDSYS = os.path.join(SD64, "sdsys")
GPL = os.path.join(SDSYS, "gpl.bp")
GPLSRC = os.path.join(SD64, "gplsrc")
ROOT = os.path.dirname(os.path.dirname(SD64))
MSGDIR = os.path.join(SDSYS, "messages")


def strip_c(src):
    def blank(m):
        return "\n" * m.group(0).count("\n")
    src = re.sub(r"/\*.*?\*/", blank, src, flags=re.S)
    return re.sub(r"//[^\n]*", "", src)


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


def code(name, text):
    if name.startswith("c:"):
        return strip_c(text)
    if name.startswith(("sh:", "txt:")):
        return strip_sh(text)
    if name.startswith("bp:"):
        return strip_bas(text)
    return text


def ordered(text, *needles):
    """Every needle found, each after the one before it."""
    pos = -1
    for n in needles:
        p = text.find(n, pos + 1)
        if p < 0:
            return False
        pos = p
    return True


def func_body(text, signature):
    """The text of the C function that begins at SIGNATURE, up to the matching close brace (comments already removed)."""
    m = re.search(re.escape(signature) + r"\s*\{", text)
    i = m.start() if m else -1
    if i < 0:
        return ""
    j = text.find("{", i)
    depth = 0
    for k in range(j, len(text)):
        if text[k] == "{":
            depth += 1
        elif text[k] == "}":
            depth -= 1
            if depth == 0:
                return text[i:k + 1]
    return text[i:]


def between(text, a, b):
    i = text.find(a)
    if i < 0:
        return ""
    j = text.find(b, i + len(a))
    return text[i:j] if j >= 0 else ""


def load():
    srcs = {}

    def get(name, path):
        if not os.path.exists(path):
            print("test-sdsysaccess-units: CANNOT RUN - %s is missing" % path)
            sys.exit(2)
        with open(path, encoding="utf-8", errors="replace") as f:
            srcs[name] = f.read()
    get("c:dh_creat.c", os.path.join(GPLSRC, "dh_creat.c"))
    for n in ("create_account", "modifya"):
        get("bp:" + n, os.path.join(GPL, n))
    get("sh:installsdcore.sh", os.path.join(ROOT, "installsdcore.sh"))
    get("sh:sd-elevate", os.path.join(HERE, "sd-elevate"))
    get("txt:regress-map.txt", os.path.join(HERE, "regress-map.txt"))
    for n in (11579, 11977, 11978, 11979, 11980):
        get("msg:%d" % n, os.path.join(MSGDIR, str(n)))
    p = os.path.join(HERE, "test-install-sdsysgroups.sh")
    srcs["file:test-install-sdsysgroups.sh"] = open(p, encoding="utf-8", errors="replace").read() if os.path.exists(p) else None
    return srcs


def checks(srcs):
    rows = []

    def ck(i, ok, detail=""):
        rows.append((i, bool(ok), detail))

    c = {name: code(name, text) for name, text in srcs.items() if isinstance(text, str)}
    t2 = {n: srcs["msg:%d" % n] for n in (11579, 11977, 11978, 11979, 11980)}
    md = c["bp:modifya"]

    # ---- the messages of modify.account's sdsys-on / sdsys-off and of create.account's join
    ck("S3b 11977 to 11980 are written for BASIC (%1 and the like, never a %s) and are one line each: 11977 and 11978 say master edits are on or off, 11979 says it is not a user "
       "account, 11980 has the account, the step and the status; modify.account cites each of them; 11579 (%1 and %2, the verb that repairs it) is cited once, by create_account's join.sdsys",
       all(t2.get(n) and t2[n].count("\n") == 1 and "%s" not in t2[n] for n in (11579, 11977, 11978, 11979, 11980))
       and "%1" in t2[11977] and "master edits are on" in t2[11977] and "master edits are off" in t2[11978] and "%1" in t2[11978]
       and "is not a user account" in t2[11979] and "%1" in t2[11979] and all(x in t2[11980] for x in ("%1", "%2", "%3"))
       and "%1" in t2[11579] and "%2" in t2[11579] and "sdsys-join" in t2[11579]
       and all(("sysmsg(%d" % n) in md for n in (11977, 11978, 11979, 11980))
       and c["bp:create_account"].count("sysmsg(11579") == 1,
       repr({n: (t2.get(n) or "MISSING")[:40] for n in t2}))

    # ---- the group write of a new VOC or dictionary (masters_fix_modes until 2 Nov 26; dh_creat.c's acct_group_modes since)
    dc = c["c:dh_creat.c"]
    fm = func_body(dc, "Private void acct_group_modes(const char *path)")
    ck("S17g (F6, C2) acct_group_modes forces group write only where the sdsys user is in the account directory's group: the test comes after the account directory's own group-write "
       "test and before the directory is opened, and returns without changing anything",
       ordered(fm, "ra.st_mode & S_IWGRP", "!acct_sdsys_in_group(ra.st_gid)", "return;", "O_DIRECTORY | O_NOFOLLOW", "fchmod(dfd"), fm[:120])
    ck("S18 acct_group_modes adds GROUP bits only (g+rwx and setgid on the directory, g+rw on %0 and %1) and takes nothing away: the bits OR-ed in are S_IRWXG | S_ISGID and S_IRGRP | S_IWGRP, "
       "there is no mask, no other bit (S_IRWXO, S_IROTH, S_IWOTH, S_IXOTH, S_ISUID), no chmod() by name - only fchmod on descriptors opened O_NOFOLLOW",
       "(ds.st_mode & 07777) | S_IRWXG | S_ISGID" in fm and "(fs.st_mode & 07777) | S_IRGRP | S_IWGRP" in fm and re.search(r"S_IRWXO|S_IROTH|S_IWOTH|S_IXOTH|S_ISUID|~", fm) is None
       and re.search(r"(?<![\w_])chmod\s*\(", fm) is None and fm.count("fchmod(") == 2 and fm.count("O_NOFOLLOW") == 2, "")
    ck("S18a ...only where the account's own directory lets its group write, and only what THIS process made and what has that directory's group: S_IWGRP of the account directory, owner = "
       "the effective user, group = the account directory's; and only the VOC itself (rel is voc) or a directory whose last component ends .dic, in a REGISTERED account (the register is "
       "read, the nearest account's directory a whole-component prefix of the path)",
       ordered(fm, "acct_root_for_path(full, root, sizeof(root), &rel)", 'strcmp(rel, "voc") == 0', "stat(root, &ra)", "ra.st_mode & S_IWGRP", "O_DIRECTORY | O_NOFOLLOW",
               "ds.st_uid != geteuid()", "ds.st_gid != ra.st_gid", "fchmod(dfd")
       and "fs.st_uid == geteuid()" in fm and "fs.st_gid == ra.st_gid" in fm and "S_ISREG(fs.st_mode)" in fm and "S_ISDIR(ds.st_mode)" in fm
       and ordered(func_body(dc, "Private bool acct_root_for_path(const char *canon, char *root, size_t rootsz, const char **rel)"), '"accounts"', "realpath(body, real)",
                   "(canon[n] == '/') || (canon[n] == '\\0')"), "")
    rp = func_body(dc, "Private bool acct_root_for_path(const char *canon, char *root, size_t rootsz, const char **rel)")
    ck("S18c (2 Nov 26, the M6 review: the old D12) the NEAREST account wins: a candidate no longer than the best so far is skipped and a match becomes the best, so a nested "
       "account's file is judged by the nested account, not the outer one",
       "(n <= best)" in rp and ordered(rp, "(n <= best)", "memcpy(root, real, n + 1);", "best = n;"), "")
    sg = func_body(dc, "Private bool acct_sdsys_in_group(gid_t gid)")
    ck("S18d (2 Nov 26, the M6 review: the old S17d) no sdsys user on the machine counts as in the group (a sandbox on a machine with no install): getpwnam of sdsys, NULL gives TRUE "
       "before the group is looked at", ordered(sg, "getpwnam(ACCT_SDSYS_USER)", "if (pw == NULL)\n    return TRUE;", "getgrgid(gid)"), "")
    ck("S18b dh_create_file calls acct_group_modes(path) ONCE, after the file is made (status = TRUE) and before the exit label, never as an error",
       dc.count("acct_group_modes(path);") == 1 and ordered(dc, "bool dh_create_file(", "status = TRUE;", "acct_group_modes(path);", "exit_dh_create_file:"), "")

    # ---- create.account
    ca2 = c["bp:create_account"]
    ck("S19 (S.103, 1 Nov) create_account puts the sdsys user in a USER account's group: the group is made with root and the user only (groupadd ... root,<user>, which the helper holds it to), "
       "the GROUP account's with root,sdsys (sdsys owns the files of a group account), and join.sdsys - called once, right after the user group is made - joins through sd-elevate "
       "sdsys-join (the one verb), says 11011, and on failure 11012 and 11579 and goes on",
       ordered(ca2, 'group_name = "sdu_":downcase(acc.uname)', "gosub create.group", "gosub join.sdsys", 'case acc.type = "GROUP"', "gosub make.account")
       and 'groupadd ": group_name :" root,":acc.uname' in ca2 and 'groupadd ": group_name :" root,sdsys"' in ca2 and ca2.count("root,sdsys") == 1 and "root,sdsys," not in ca2
       and ca2.count("gosub join.sdsys") == 1 and ca2.count("sd-elevate sdsys-join") == 1 and ca2.count("sd-elevate sdsys") == 1
       and ordered(between(ca2, "join.sdsys:", "\nend"), "is_grp_member('sdsys', group_name)", "sd-elevate sdsys-join", "OS.ERROR()", "sysmsg(11011", "sysmsg(11012", "sysmsg(11579"), "")

    # ---- the installer's default
    ins2 = c["sh:installsdcore.sh"]
    raw_ins = srcs["sh:installsdcore.sh"]                       # the markers are comment lines, which `ins2` has lost
    jf = re.search(r"^sdsys_groups_default\(\) \{.*?^\}", ins2, re.M | re.S)
    jf = jf.group(0) if jf else ""
    call = 'sdsys_groups_default "$ACCT_PATH/\\$sdsys.access"'
    ck("S20 (S.103) the installer's default, sdsys_groups_default: TWO verbs, sdsys-join (a group named sdu_<something> that /etc/group does NOT list sdsys in, a whole name) and group-write "
       "(that account's directory, when it exists), each judged on sd-elevate's own words; only when the marker is absent; the marker is written (touch, chown sdsys:sdusers, chmod 644) only "
       "when no account failed (a failure returns before it); never exits; no sdsys-leave and no question; called once, with the marker in /home/sd (ACCT_PATH, not the sdsys directory, which "
       "deletesdcore.sh removes), after upgrade_editgates and before the register is handed to sdsys",
       len(jf) > 1200 and jf.count('sudo /usr/local/sbin/sd-elevate sdsys-join "$group"') == 1 and jf.count('sudo /usr/local/sbin/sd-elevate group-write "$dir"') == 1 and "sdsys-leave" not in jf
       and "read " not in jf
       and ordered(jf, 'if [ -e "$marker" ]; then', "return 0", "getent group", '$1 ~ /^sdu_./', '!~ /,sdsys,/', 'sdsys-join "$group"', 'usermod -aG ${group} -- sdsys', 'group-write "$dir"',
                   'sd-elevate: group-write: ', 'if [ "$n_fail" -gt 0 ]; then', "return 0", 'sudo touch "$marker"', 'sudo chown sdsys:sdusers "$marker"', 'sudo chmod 644 "$marker"')
       and re.search(r"\b(exit|return 1)\b", jf) is None and ins2.count(call) == 1 and "sdsysdir/\\$sdsys.access" not in ins2
       and ordered(ins2, "-internal RUN gpl.bp upgrade_editgates", call, 'sudo chown -R sdsys:sdusers "$sdsysdir/accounts"'), "")
    ck("S20a (S.103) the F6 question is GONE: no SDSYSGROUPS-ASK markers, no sdsys_keep or sdsys_listed, no sdsys_groups_ruling, no $groups.ruled, no read of an answer about keeping the "
       "sdsys user in the groups",
       "SDSYSGROUPS-ASK" not in raw_ins and "sdsys_keep" not in ins2 and "sdsys_listed" not in ins2 and "sdsys_groups_ruling" not in ins2 and "$groups.ruled" not in ins2
       and re.search(r"read[^\n|]*[Kk]eep the sdsys", ins2) is None, "")

    # ---- the helper
    se = c["sh:sd-elevate"]
    ck("S21 sd-elevate has the three verbs: sdsys-join builds usermod -aG GROUP -- sdsys (the user written in the helper, never an argument; -aG appends) after require_account_group; "
       "sdsys-leave the other way, gpasswd -d sdsys GROUP, after the same rule, and a group that does not list sdsys is answered 'sdsys is not in' with exit 0 before any command is built; "
       "group-write runs the worker on one validated account directory and exits with its status; the three leave a line in the system log after the change (logger -t sd-elevate)",
       ordered(between(se, "sdsys-join)", ";;"), "[[ $# -eq 1 ]] || usage", 'require_account_group "$1"', 'cmd=(usermod -aG "$1" -- sdsys)', "LOG_LINE=") and "SUDO_USER" not in between(se, "sdsys-join)", ";;")
       and ordered(between(se, "sdsys-leave)", ";;"), "[[ $# -eq 1 ]] || usage", 'require_account_group "$1"', 'group_lists_sdsys "$1"', "sdsys is not in", "exit 0", 'cmd=(gpasswd -d sdsys "$1")', "LOG_LINE=")
       and "SUDO_USER" not in between(se, "sdsys-leave)", ";;")
       and ordered(between(se, "group-write)", ";;"), "[[ $# -eq 1 ]] || usage", 'require_group_write_target "$1"', "need_root", 'python3 -I -c "$GW_PY"', "|| exit $?", "logger -t sd-elevate", "exit 0")
       and ordered(se, '"${cmd[@]}" || exit $?', 'logger -t sd-elevate "$LOG_LINE"'), "")

    # ---- wiring
    mp_ = srcs["txt:regress-map.txt"]
    ck("S22 wiring: the map has a rule for message 11579 and for 11977-11980, sd-elevate and dh_creat.c select suites, and the installer test names the default's function",
       re.search(r"^sdsys/messages/11579\s*:\s*\S", mp_, re.M) is not None and re.search(r"^sdsys/messages/1197\[7-9\]\s*:\s*\S", mp_, re.M) is not None
       and re.search(r"^gplbld/sd-elevate\s*:\s*\S", mp_, re.M) is not None and re.search(r"^gplsrc/dh_\*\.c\s*:\s*\S", mp_, re.M) is not None
       and "sdsys_groups_default" in (srcs.get("file:test-install-sdsysgroups.sh") or ""), "")
    return rows


def mutate(srcs, name, a, b, count=1):
    """A copy of SRCS with a change made to one file.  A change that finds nothing, or changes nothing, is an error: a mutant that does not apply tests nothing."""
    s = dict(srcs)
    if name not in s or s[name] is None:
        raise KeyError("no such source: %s" % name)
    old = s[name]
    if a not in old:
        raise KeyError("mutant text not in %s: %r" % (name, a[:80]))
    new = old.replace(a, b, count)
    if new == old:
        raise KeyError("the mutation changed nothing in %s" % name)
    s[name] = new
    return s


# (label, source, old, new)
MUTANTS = [
    # ---- the messages
    ("11977 forgets to say master edits are on", "msg:11977", "master edits are on", "it is done"),
    ("11979 takes a %s", "msg:11979", "%1 is not a user account", "%s is not a user account"),
    ("11980 loses the status", "msg:11980", ", status %3", ""),
    ("11579 no longer names the verb that repairs it", "msg:11579", "sdsys-join", "usermod"),
    ("modify.account stops saying it is off", "bp:modifya", "sysmsg(11978", "sysmsg(11977"),
    # ---- the modes of what SD makes
    ("the other bits are added too", "c:dh_creat.c", "(ds.st_mode & 07777) | S_IRWXG | S_ISGID", "(ds.st_mode & 07777) | S_IRWXG | S_ISGID | S_IRWXO"),
    ("the mode is set by name", "c:dh_creat.c", "  (void)fchmod(dfd, (mode_t)((ds.st_mode & 07777) | S_IRWXG | S_ISGID));", "  chmod(full, 0775);\n  (void)fchmod(dfd, (mode_t)((ds.st_mode & 07777) | S_IRWXG | S_ISGID));"),
    ("a link can take the place of the directory", "c:dh_creat.c", "open(full, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)", "open(full, O_RDONLY | O_DIRECTORY | O_CLOEXEC)"),
    ("the account directory's group write is not asked", "c:dh_creat.c", "  if ((stat(root, &ra) != 0) || !(ra.st_mode & S_IWGRP))\n    return;", "  if (stat(root, &ra) != 0)\n    return;"),
    ("what another user made is changed", "c:dh_creat.c", "(ds.st_uid != geteuid()) || ", ""),
    ("what another group has is changed", "c:dh_creat.c", " || (ds.st_gid != ra.st_gid)", ""),
    ("a file of another group is changed", "c:dh_creat.c", " && (fs.st_gid == ra.st_gid)", ""),
    ("any path with voc in it is the VOC", "c:dh_creat.c", 'if (!((strcmp(rel, "voc") == 0) ||', 'if (!((strstr(rel, "voc") != NULL) ||'),
    ("C2 is gone, group write is forced wherever the account directory allows it", "c:dh_creat.c",
     "  if (!acct_sdsys_in_group(ra.st_gid)) /* F6 (C2): group write is forced only where the sdsys user is in the group */\n    return;\n", ""),
    ("C2 asks the wrong group", "c:dh_creat.c", "!acct_sdsys_in_group(ra.st_gid)", "!acct_sdsys_in_group(getegid())"),
    ("an account directory is a text prefix of another's (acme of acme2)", "c:dh_creat.c", "((canon[n] == '/') || (canon[n] == '\\0'))", "1"),
    ("the new file's modes are no longer fixed", "c:dh_creat.c", "  acct_group_modes(path);\n\nexit_dh_create_file:", "\nexit_dh_create_file:"),
    # ---- create.account
    ("create_account puts the sdsys user in a user account's group when it makes it", "bp:create_account", 'groupadd ": group_name :" root,":acc.uname', 'groupadd ": group_name :" root,sdsys,":acc.uname'),
    ("create_account makes a group account's group without sdsys", "bp:create_account", 'groupadd ": group_name :" root,sdsys"', 'groupadd ": group_name :" root"'),
    ("create_account never joins the sdsys user to a user account's group", "bp:create_account", "      gosub join.sdsys\n", ""),
    ("create_account does not say a failed join", "bp:create_account", "      crt sysmsg(11579, acc.name, group_name)", "      null"),
    ("create_account joins by some other verb", "bp:create_account", "os.execute \"sudo /usr/local/sbin/sd-elevate sdsys-join \":group_name", "os.execute \"sudo /usr/local/sbin/sd-elevate usermod \":group_name"),
    # ---- the installer
    ("the default counts group accounts too", "sh:installsdcore.sh", "    missing=$(getent group 2>/dev/null | awk -F: '$1 ~ /^sdu_./", "    missing=$(getent group 2>/dev/null | awk -F: '$1 ~ /^sd[ug]_./"),
    ("the default matches a prefix of sdsys", "sh:installsdcore.sh", "(\",\" $4 \",\") !~ /,sdsys,/", "(\",\" $4 \",\") !~ /sdsys/"),
    ("the default ignores the marker", "sh:installsdcore.sh", '    if [ -e "$marker" ]; then', '    if false; then'),
    ("the default takes the sdsys user out instead of putting it in", "sh:installsdcore.sh", 'sd-elevate sdsys-join "$group"', 'sd-elevate sdsys-leave "$group"'),
    ("the default does not repair the modes", "sh:installsdcore.sh", 'sd-elevate group-write "$dir"', 'sd-elevate stat "$dir"'),
    ("the marker is not handed to sdsys", "sh:installsdcore.sh", '    sudo chown sdsys:sdusers "$marker"\n', ""),
    ("the marker is open to everybody", "sh:installsdcore.sh", '    sudo chmod 644 "$marker"', '    sudo chmod 666 "$marker"'),
    ("the default can stop the install", "sh:installsdcore.sh", '        echo "  The sdsys user was put in the group of ', '        exit 1; echo "  The sdsys user was put in the group of '),
    ("the default is called twice", "sh:installsdcore.sh", 'sdsys_groups_default "$ACCT_PATH/\\$sdsys.access"\n', 'sdsys_groups_default "$ACCT_PATH/\\$sdsys.access"\nsdsys_groups_default "$ACCT_PATH/\\$sdsys.access"\n'),
    ("the default's marker is in the sdsys directory", "sh:installsdcore.sh", 'sdsys_groups_default "$ACCT_PATH/\\$sdsys.access"', 'sdsys_groups_default "$sdsysdir/\\$sdsys.access"'),
    ("the default is never called", "sh:installsdcore.sh", 'sdsys_groups_default "$ACCT_PATH/\\$sdsys.access"\n', "true\n"),
    # ---- sd-elevate
    ("sdsys-join replaces the groups", "sh:sd-elevate", 'cmd=(usermod -aG "$1" -- sdsys)', 'cmd=(usermod -G "$1" -- sdsys)'),
    ("sdsys-join takes the user from sudo", "sh:sd-elevate", 'cmd=(usermod -aG "$1" -- sdsys)', 'cmd=(usermod -aG "$1" -- "${SUDO_USER:-sdsys}")'),
    ("sdsys-leave replaces the groups", "sh:sd-elevate", 'cmd=(gpasswd -d sdsys "$1")', 'cmd=(usermod -G "" -- sdsys)'),
    ("sdsys-leave changes a group that does not list sdsys", "sh:sd-elevate", '    if ! group_lists_sdsys "$1"; then', '    if false; then'),
    ("sdsys-join leaves no line in the log", "sh:sd-elevate", '    LOG_LINE="sdsys-join: the user sdsys is now in $1"\n', ""),
    ("group-write needs no root", "sh:sd-elevate", '    need_root\n    python3 -I -c "$GW_PY"', '    python3 -I -c "$GW_PY"'),
    ("group-write forgets the worker's status", "sh:sd-elevate", '"$GW_OWNERS" "$DRY" || exit $?\n', '"$GW_OWNERS" "$DRY"\n'),
    # ---- wiring
    ("the map forgets message 11579", "txt:regress-map.txt", "sdsys/messages/11579 ", "sdsys/messages/11578 "),
    # ---- 2 Nov 26, the M6 review: S18c and S18d
    ("the OUTER account wins (a shorter match replaces a longer one)", "c:dh_creat.c", "(n <= best))", "(0))"),
    ("no sdsys user means not in the group", "c:dh_creat.c", "if (pw == NULL)\n    return TRUE;", "if (pw == NULL)\n    return FALSE;"),
]


def main():
    srcs = load()
    if "--selftest" in sys.argv:
        base = checks(srcs)
        bad = [i for i, ok, d in base if not ok]
        if bad:
            print("test-sdsysaccess-units: the unmutated source already fails: %s" % bad)
            return 2
        start = 0
        for a_ in sys.argv[1:]:
            if a_.startswith("--from="):
                start = int(a_.split("=", 1)[1])
        missed = n = 0
        for k_, (label, name, old, new) in enumerate(MUTANTS):
            if k_ < start:
                continue
            n += 1
            try:
                rows = checks(mutate(srcs, name, old, new))
            except KeyError as e:
                print("  [FAIL] mutant is not applicable: %s (%s)" % (label, e))
                missed += 1
                continue
            caught = [i for i, ok, d in rows if not ok]
            if caught:
                print("  [PASS] mutant caught: %s  <- %s" % (label, ", ".join(c_.split(" ")[0] for c_ in caught[:3])))
            else:
                print("  [FAIL] MUTANT NOT CAUGHT: %s" % label)
                missed += 1
        print("\ntest-sdsysaccess-units --selftest: %d mutants, %d missed" % (n, missed))
        return 1 if missed or n == 0 else 0
    rows = checks(srcs)
    failed = 0
    for i, ok, d in rows:
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", i, "" if ok or not d else "   <- " + d))
        failed += 0 if ok else 1
    print("\ntest-sdsysaccess-units: %d checks, %d failed" % (len(rows), failed))
    print("NOT MEASURED HERE: that a group is joined, a mode is right on the disk or the helper refuses anybody (test-sd-elevate.py, test-accelevate-units.py,\n"
          "test-install-sdsysgroups.sh, and a real install on the VM).")
    return 1 if failed or not rows else 0


if __name__ == "__main__":
    sys.exit(main())
