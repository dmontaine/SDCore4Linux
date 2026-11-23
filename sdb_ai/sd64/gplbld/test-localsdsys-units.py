#!/usr/bin/env python3
# test-localsdsys-units.py - S.267 (18 Nov 2026): SDSYS reached from this computer by the Linux users the administrator lists (local.sdsys; the owner,
# 17-18 Nov 2026: "restricted to only usernames listed in a text field rather than a gate", "delivered with that access off").  FREE: no install, no
# sudo, no SD.
#
#   python3 /home/don/SDCoreProject/SDCore4Linux/sdb_ai/sd64/gplbld/test-localsdsys-units.py [--selftest]
#
# WHAT IT HOLDS
#   K  the kernel's answer: gplsrc/sd_localsdsys.c built with -Wall -Wextra together with gplbld/verify-localsdsys.c and driven as a black box on
#      scratch fixtures (a list, a login uid, an audit session id, a cgroup, logind's session directory and record).  The owner the driver asks for is
#      the test's own uid (the kernel asks for root's); the listed user is the test's own user, the group its own primary group.  EVERY refusal row
#      wants its own reason word, so a run that read nothing (every answer list-empty) fails row after row; K0 shows a fixture is read.
#   H  the helper: the functions between "# BEGIN sdsys_local_functions" and its END in gplbld/sd-elevate, cut out and run on the same kind of scratch
#      files with die and logger stubbed: the name rules, add / remove / clear / status, 32 names and the 33rd, idempotence, a link in place of the
#      file, a group-writable file, --dry-run; and sdsys-session's decision (sdsys_local_decide, its facts as arguments) on the SAME fixtures as K,
#      where the helper's reason word must equal the kernel's (A rows).
#   T  text: cproc asks the kernel before the 10195 refusal, the password before the grant, the grant before its audit line, an empty answer leaves
#      the old refusal; apisrvr asks the API list while root (before K$ASSUME.USER), only on the Unix socket and only for a peer that is not sdsys,
#      and compares the peer's login; loopback TCP is still refused; nothing reads an environment variable for this; the keys; the kernel's case;
#      sd.c; ssh-forcecommand; the wrapper; the installer and the deleter.
#   S  sdcore.sudoers: %sdusers gains exactly "sd-elevate sdsys-session", nothing else; visudo -cf accepts the file (SKIPPED where there is no visudo).
#   V  the verb local.sdsys: the administrator first, the words, the name checked before the shell, the question before an add, the audit line,
#      voc_template has the record and newvoc does not, the messages exist.
# WHAT IT CANNOT SHOW: a file owned by another user (the test is not root: SKIPPED, said out loud), a real logind session of sshd, sudo, setpriv, the
# grant itself.  Those are gplbld/witness-localsdsys.sh on the Debian 13 VM.  Exit 0 every row passed (or every mutant killed), 1 a row failed (or a
# mutant survived), 2 it could not run.

import grp
import os
import pwd
import re
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
SD64 = os.path.dirname(HERE)
REPO = os.path.normpath(os.path.join(SD64, "..", ".."))
INC = os.path.join(SD64, "gplsrc")
BP = os.path.join(SD64, "sdsys", "gpl.bp")
MSG = os.path.join(SD64, "sdsys", "messages")
CFLAGS = ["-std=gnu17", "-Wall", "-Wextra", "-Wformat=2", "-O2"]
MIN_ROWS = 120

FILES = {
    "c": os.path.join(INC, "sd_localsdsys.c"),
    "h": os.path.join(INC, "sd_localsdsys.h"),
    "elevate": os.path.join(HERE, "sd-elevate"),
    "cproc": os.path.join(BP, "cproc"),
    "apisrvr": os.path.join(BP, "apisrvr"),
    "verb": os.path.join(BP, "localsdsys"),
    "sudoers": os.path.join(HERE, "sdcore.sudoers"),
    "opkernel": os.path.join(INC, "op_kernel.c"),
    "keysc": os.path.join(INC, "keys.h"),
    "keysb": os.path.join(BP, "int$keys.h"),
    "sdc": os.path.join(INC, "sd.c"),
    "gplsrc_list": os.path.join(SD64, "gpl.src"),
    "fc": os.path.join(HERE, "ssh-forcecommand.sh"),
    "wrapper": os.path.join(HERE, "sd-sdsys"),
    "installer": os.path.join(REPO, "installsdcore.sh"),
    "deleter": os.path.join(REPO, "deletesdcore.sh"),
    "voct": os.path.join(SD64, "sdsys", "voc_template", "local.sdsys"),
}
NEWVOC_REC = os.path.join(SD64, "sdsys", "newvoc", "local.sdsys")
MESSAGES = [str(n) for n in range(14175, 14185)]

ME = pwd.getpwuid(os.getuid()).pw_name
MYUID = os.getuid()
MYGROUP = grp.getgrgid(os.getgid()).gr_name


def say(s=""):
    print(s, flush=True)


def load():
    src = {}
    for k, p in FILES.items():
        try:
            with open(p, encoding="latin-1") as f:
                src[k] = f.read()
        except OSError:
            src[k] = ""
    return src


def code(s):
    """BASIC text with comment lines and ;* tails taken out."""
    out = []
    for line in s.split("\n"):
        t = line.lstrip()
        if t.startswith("*"):
            continue
        c = line.find(";*")
        out.append(line if c < 0 else line[:c])
    return "\n".join(out)


def ordered(text, *needles):
    pos = -1
    for n in needles:
        i = text.find(n, pos + 1)
        if i < 0:
            return False
        pos = i
    return True


def not_my_group():
    mine = set(os.getgroups()) | {os.getgid()}
    for g in grp.getgrall():
        if g.gr_gid not in mine and re.match(r"^[a-z_][a-z0-9_-]{0,31}$", g.gr_name):
            return g.gr_name
    return None


def unused_uid():
    for u in (99991, 99992, 99993, 123457, 2000000):
        try:
            pwd.getpwuid(u)
        except KeyError:
            return u
    return None


# ------------------------------------------------------------------------------------------------ the fixtures
SESSION_OK = {"UID": None, "USER": None, "ACTIVE": "1", "STATE": "active", "REMOTE": "1", "SCOPE": "session-7.scope",
              "SERVICE": "sshd", "REMOTE_HOST": "127.0.0.1", "AUDIT": "7", "LEADER": "4242"}


class Scene:
    """One scratch world: etc/sdcore/sdsys-local-ssh (and -api), run/systemd/sessions/<id>, a loginuid, a sessionid and a cgroup file."""
    n = 0

    def __init__(self, base, names=(None,), session=None, sid="7", lu=None, cg=None, extra_lines=None, raw_list=None, raw_session=None):
        Scene.n += 1
        self.d = os.path.join(base, "s%d" % Scene.n)
        self.etc = os.path.join(self.d, "etc")
        self.sdcore = os.path.join(self.etc, "sdcore")
        self.list = os.path.join(self.sdcore, "sdsys-local-ssh")
        self.api = os.path.join(self.sdcore, "sdsys-local-api")
        self.run = os.path.join(self.d, "run", "systemd")
        self.sessions = os.path.join(self.run, "sessions")
        for p in (self.sdcore, self.sessions):
            os.makedirs(p)
        for p in (self.d, self.etc, self.sdcore, os.path.join(self.d, "run"), self.run, self.sessions):
            os.chmod(p, 0o755)
        if raw_list is not None:
            self.write(self.list, raw_list)
        elif names is not None:
            ns = [ME if x is None else x for x in names]
            self.write(self.list, "".join(x + "\n" for x in ns))
            self.write(self.api, "".join(x + "\n" for x in ns))
        sess = dict(SESSION_OK)
        sess["UID"] = str(MYUID)
        sess["USER"] = ME
        if session:
            for k, v in session.items():
                if v is None:
                    sess.pop(k, None)
                else:
                    sess[k] = v
        text = "# This is private data. Do not parse.\n" + "".join("%s=%s\n" % kv for kv in sess.items()) + (extra_lines or "")
        self.session_file = os.path.join(self.sessions, "7")
        self.write(self.session_file, raw_session if raw_session is not None else text)
        self.loginuid = os.path.join(self.d, "loginuid")
        self.lu_text = str(MYUID) if lu is None else lu
        if self.lu_text is not False:
            self.write(self.loginuid, self.lu_text)
        self.sessionid = os.path.join(self.d, "sessionid")
        self.sid_text = sid
        self.write(self.sessionid, sid)
        self.cgroup = os.path.join(self.d, "cgroup")
        self.cg_text = ("0::/user.slice/user-%d.slice/session-7.scope\n" % MYUID) if cg is None else cg
        self.write(self.cgroup, self.cg_text)

    @staticmethod
    def write(path, text, mode=0o644):
        with open(path, "wb") as f:
            f.write(text.encode("latin-1") if isinstance(text, str) else text)
        os.chmod(path, mode)


def k_ssh(exe, s, group=None, owner=None):
    args = [exe, "ssh", s.list, s.loginuid, s.sessionid, s.cgroup, s.sessions, group or MYGROUP] + ([] if owner is None else [str(owner)])
    p = subprocess.run(args, capture_output=True, text=True)
    return p.returncode, p.stdout.strip()


def k_api(exe, s, user, group=None):
    p = subprocess.run([exe, "api", s.api, user, group or MYGROUP], capture_output=True, text=True)
    return p.returncode, p.stdout.strip()


# ------------------------------------------------------------------------------------------------ the helper's block
HARNESS = r'''set -uo pipefail
DRY=${DRY:-0}
PROG=sd-elevate
die() { printf '%s: REFUSED - %s\n' "$PROG" "$1" >&2; exit 2; }
logger() { :; }
decide() { sdsys_local_decide "$@"; local rc=$?; printf 'user=%s why=%s\n' "$SL_USER" "$SL_WHY"; return $rc; }
'''


def helper_block(elevate):
    m = re.search(r"\n# BEGIN sdsys_local_functions\n(.*?)\n# END sdsys_local_functions\n", elevate, re.S)
    return m.group(1) if m else ""


def hrun(block, *args, dry=0):
    script = HARNESS + block + '\n"$@"\n'
    env = dict(os.environ)
    env["DRY"] = str(dry)
    p = subprocess.run(["bash", "-c", script, "x"] + [str(a) for a in args], capture_output=True, text=True, env=env, timeout=60)
    return p.returncode, (p.stdout + p.stderr).strip()


def h_decide(block, s, su=None, group=None, owner=None):
    lu = "" if s.lu_text is False else s.lu_text.rstrip("\n")
    return hrun(block, "decide", MYUID if owner is None else owner, s.list, group or MYGROUP, s.sessions, lu, lu if su is None else su,
                s.sid_text.rstrip("\n"), s.cg_text.rstrip("\n"))


def build(cc, tmp, csrc, hsrc, tag):
    d = os.path.join(tmp, "src-" + tag)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "sd_localsdsys.c"), "w", encoding="latin-1") as f:
        f.write(csrc)
    with open(os.path.join(d, "sd_localsdsys.h"), "w", encoding="latin-1") as f:
        f.write(hsrc)
    exe = os.path.join(tmp, "verify-" + tag)
    p = subprocess.run([cc] + CFLAGS + ["-I" + d, os.path.join(d, "sd_localsdsys.c"), os.path.join(HERE, "verify-localsdsys.c"), "-o", exe],
                       capture_output=True, text=True)
    return exe, p


# ------------------------------------------------------------------------------------------------ the rows
def kernel_and_helper_rows(exe, block, base):
    rows = []
    skipped = []

    def row(i, label, ok, detail=""):
        rows.append((i, label, bool(ok), detail))

    ALLOW = "user=%s why=" % ME

    def both(i, label, scene, want_why, su=None, group=None, agree=True, owner=None):
        rc, out = k_ssh(exe, scene, group, owner)
        if want_why == "":
            row("K" + i, "ALLOW: " + label + ": the kernel answers the user", rc == 0 and out == ALLOW, out)
        else:
            row("K" + i, "REFUSE: " + label + ": the kernel answers '' with why=" + want_why, rc == 1 and out == "user= why=" + want_why, out)
        if agree:
            hrc, hout = h_decide(block, scene, su=su, group=group, owner=owner)
            last = hout.splitlines()[-1] if hout else ""
            if want_why == "":
                row("A" + i, "the helper's decision agrees (" + label + "): admitted as " + ME, hrc == 0 and last == ALLOW, hout[-200:])
            else:
                row("A" + i, "the helper's decision agrees (" + label + "): refused, why=" + want_why, hrc != 0 and last == "user= why=" + want_why, hout[-200:])

    # K0: a fixture is read at all (the null case): the same allowed scene answers list-empty once the list is taken away
    s = Scene(base)
    rc, out = k_ssh(exe, s)
    os.unlink(s.list)
    rc2, out2 = k_ssh(exe, s)
    row("K0", "NULL CASE: the allowed scene answers the user, and the same scene with its list file removed answers why=list-empty (so the fixtures are read)",
        rc == 0 and out == ALLOW and rc2 == 1 and out2 == "user= why=list-empty", "%s | %s" % (out, out2))

    both("1", "a listed user's sshd session from 127.0.0.1", Scene(base), "")
    both("2", "from ::1", Scene(base, session={"REMOTE_HOST": "::1"}), "")
    both("3", "from 127.5.6.7 (all of 127.0.0.0/8 is loopback)", Scene(base, session={"REMOTE_HOST": "127.5.6.7"}), "")
    both("4", "32 names, this user the last", Scene(base, names=["u%02d" % k for k in range(31)] + [None]), "")
    both("5", "a list file with no newline after the last name", Scene(base, raw_list=ME), "")
    # the list
    both("10", "no list file (absent is empty)", Scene(base, names=None), "list-empty")
    s = Scene(base, names=None)
    shutil.rmtree(s.sdcore)
    both("11", "no /etc/sdcore directory at all", s, "list-empty")
    both("12", "an empty list file", Scene(base, raw_list=""), "list-empty")
    both("13", "a name in capitals (Don) on the list", Scene(base, names=[None, "Don"]), "list-unsafe")
    both("14", "33 names on the list", Scene(base, names=["u%02d" % k for k in range(32)] + [None]), "list-unsafe")
    both("15", "a blank line inside the list", Scene(base, raw_list="%s\n\nx\n" % ME), "list-unsafe")
    both("16", "a NUL byte in the list", Scene(base, raw_list=b"x\x00y\n" + (ME + "\n").encode()), "list-unsafe")
    both("17", "a name with a space after it", Scene(base, raw_list=ME + " \n"), "list-unsafe")
    s = Scene(base)
    os.chmod(s.list, 0o664)
    both("18", "the list is writable by its group", s, "list-unsafe")
    s = Scene(base)
    os.chmod(s.list, 0o646)
    both("19", "the list is writable by others", s, "list-unsafe")
    s = Scene(base)
    os.link(s.list, os.path.join(s.d, "second-link"))
    both("20", "the list has a second hard link", s, "list-unsafe")
    s = Scene(base)
    real = os.path.join(s.d, "elsewhere")
    os.rename(s.list, real)
    os.symlink(real, s.list)
    both("21", "the list is a symbolic link to a right-looking file", s, "list-unsafe")
    s = Scene(base)
    os.chmod(s.sdcore, 0o775)
    both("22", "/etc/sdcore is writable by its group", s, "list-unsafe")
    s = Scene(base)
    os.chmod(s.etc, 0o777)
    both("23", "the directory above /etc/sdcore is writable by others", s, "list-unsafe")
    s = Scene(base)
    os.rename(s.sdcore, s.sdcore + ".real")
    os.symlink(s.sdcore + ".real", s.sdcore)
    both("24", "/etc/sdcore is a link", s, "list-unsafe")
    s = Scene(base)
    os.unlink(s.list)
    os.mkfifo(s.list, 0o644)
    both("25", "the list is a FIFO, not a regular file (and nothing hangs)", s, "list-unsafe")
    # a file of another owner: the test is not root and cannot make one, so it asks for another OWNER instead (the verify program's argument,
    # the helper's): its own files are then the wrong owner's
    both("26", "every file belongs to a user other than the owner asked for (the owner asked is uid %d)" % (MYUID + 1), Scene(base), "list-unsafe", owner=MYUID + 1)
    skipped.append("a list or a session record really owned by another user (root's own files with a non-root owner asked): the test is not root; "
                   "K26 / A26 ask for another owner instead, and the VM witness has root's files")
    # who logged in
    both("30", "the login uid is unset (4294967295)", Scene(base, lu="4294967295"), "no-login")
    both("31", "the login uid is not a number", Scene(base, lu="abc"), "no-login")
    both("32", "there is no login uid file", Scene(base, lu=False), "no-login")
    nu = unused_uid()
    if nu is not None:
        both("33", "the login uid belongs to no user", Scene(base, lu=str(nu), cg="0::/user.slice/user-%d.slice/session-7.scope\n" % nu,
                                                              session={"UID": str(nu)}), "no-user")
    both("34", "the login is root's (uid 0)", Scene(base, lu="0", names=["root", None]), "not-sd-user")
    both("35", "the login is a system account's (daemon, uid 1)", Scene(base, lu="1", names=["daemon", None]), "not-sd-user")
    try:
        dgroup = grp.getgrgid(pwd.getpwnam("daemon").pw_gid).gr_name
    except KeyError:
        dgroup = None
    if dgroup:
        both("35b", "the login is daemon's (uid 1), asked with daemon's own group (%s): the uid floor alone refuses it" % dgroup,
             Scene(base, lu="1", names=["daemon", None]), "not-sd-user", group=dgroup)
    other = not_my_group()
    if other:
        both("36", "the user is not in the group the kernel asks for (%s)" % other, Scene(base), "not-sd-user", group=other)
    both("37", "the user is not on the list (others are)", Scene(base, names=["alice", "bob"]), "not-listed")
    # the session
    both("40", "the cgroup is the user manager's, not a login session's",
         Scene(base, cg="0::/user.slice/user-%d.slice/user@%d.service/app.slice/x.scope\n" % (MYUID, MYUID)), "no-session")
    both("41", "the cgroup is another uid's session scope", Scene(base, cg="0::/user.slice/user-%d.slice/session-7.scope\n" % (MYUID + 1)), "no-session")
    both("42", "the cgroup file has two lines", Scene(base, cg="0::/user.slice/user-%d.slice/session-7.scope\n1:name=systemd:/\n" % MYUID), "no-session")
    both("43", "the cgroup is a system service's", Scene(base, cg="0::/system.slice/ssh.service\n"), "no-session")
    both("44", "the session id has a capital (session-X7.scope)", Scene(base, cg="0::/user.slice/user-%d.slice/session-X7.scope\n" % MYUID), "no-session")
    s = Scene(base, cg="0::/user.slice/user-%d.slice/session-7.scope" % MYUID)
    rc, out = k_ssh(exe, s)
    row("K45", "REFUSE: the cgroup line has no newline: the kernel answers '' with why=no-session (the helper reads it through $(cat), which strips newlines)",
        rc == 1 and out == "user= why=no-session", out)
    s = Scene(base)
    os.unlink(s.session_file)
    both("46", "logind has no record of the session", s, "no-session")
    both("47", "the record names another scope", Scene(base, session={"SCOPE": "session-8.scope"}), "no-session")
    both("48", "the record has no SCOPE line", Scene(base, session={"SCOPE": None}), "no-session")
    s = Scene(base)
    os.chmod(s.session_file, 0o664)
    both("49", "the record is writable by its group", s, "session-unsafe")
    s = Scene(base)
    os.chmod(s.sessions, 0o777)
    both("50", "the sessions directory is writable by others", s, "session-unsafe")
    s = Scene(base)
    real = os.path.join(s.d, "fake-record")
    os.rename(s.session_file, real)
    os.symlink(real, s.session_file)
    both("51", "the record is a link to a right-looking file", s, "session-unsafe")
    s = Scene(base)
    os.chmod(s.run, 0o775)
    both("52", "the directory above the sessions directory is writable by its group", s, "session-unsafe")
    both("53", "the record names another uid", Scene(base, session={"UID": str(MYUID + 1)}), "other-user")
    both("54", "the record names another audit session", Scene(base, session={"AUDIT": "8"}), "other-session")
    both("55", "this process has no audit session (4294967295)", Scene(base, sid="4294967295"), "other-session")
    both("56", "the record has no AUDIT line", Scene(base, session={"AUDIT": None}), "other-session")
    both("57", "the session is the console's (SERVICE=login)", Scene(base, session={"SERVICE": "login", "REMOTE": "0", "REMOTE_HOST": None}), "not-ssh")
    both("58", "a desktop session (SERVICE=gdm-password)", Scene(base, session={"SERVICE": "gdm-password"}), "not-ssh")
    both("59", "sshd, but REMOTE=0", Scene(base, session={"REMOTE": "0"}), "not-ssh")
    both("60", "two SERVICE lines (login, then sshd): a key given twice is no answer", Scene(base, session={"SERVICE": "login"}, extra_lines="SERVICE=sshd\n"), "not-ssh")
    both("61", "from another computer (192.168.1.5)", Scene(base, session={"REMOTE_HOST": "192.168.1.5"}), "not-local")
    both("62", "from a host NAME, localhost", Scene(base, session={"REMOTE_HOST": "localhost"}), "not-local")
    both("63", "from a host name that ends in 127.0.0.1 (x.127.0.0.1)", Scene(base, session={"REMOTE_HOST": "x.127.0.0.1"}), "not-local")
    both("64", "from ::ffff:127.0.0.1 (a mapped form is not taken)", Scene(base, session={"REMOTE_HOST": "::ffff:127.0.0.1"}), "not-local")
    both("65", "from 127.0.0.01 (a leading zero)", Scene(base, session={"REMOTE_HOST": "127.0.0.01"}), "not-local")
    both("66", "with no REMOTE_HOST line", Scene(base, session={"REMOTE_HOST": None}), "not-local")
    both("67", "from 128.0.0.1", Scene(base, session={"REMOTE_HOST": "128.0.0.1"}), "not-local")
    both("68", "from ::2", Scene(base, session={"REMOTE_HOST": "::2"}), "not-local")
    both("69", "from an IPv6 loopback with a scope (::1%lo)", Scene(base, session={"REMOTE_HOST": "::1%lo"}), "not-local")
    # the helper's own fact: sudo's caller
    s = Scene(base)
    hrc, hout = h_decide(block, s, su=str(MYUID + 1))
    row("A70", "the helper refuses when sudo's caller (SUDO_UID) is not the user of the login (su to another user, then sudo): why=other-user",
        hrc != 0 and hout.splitlines()[-1:] == ["user= why=other-user"], hout[-200:])
    hrc, hout = h_decide(block, s, su="")
    row("A71", "the helper refuses when there is no SUDO_UID: why=other-user", hrc != 0 and hout.splitlines()[-1:] == ["user= why=other-user"], hout[-200:])

    # the API list (sd_local_listed)
    s = Scene(base)
    rc, out = k_api(exe, s, ME)
    row("K80", "API: a listed user is listed=1", rc == 0 and out == "listed=1 why=", out)
    s = Scene(base, names=["alice"])
    rc, out = k_api(exe, s, ME)
    row("K81", "API: a user not on the list: listed=0 why=not-listed", rc == 1 and out == "listed=0 why=not-listed", out)
    s = Scene(base, names=None)
    rc, out = k_api(exe, s, ME)
    row("K82", "API: no list: listed=0 why=list-empty", rc == 1 and out == "listed=0 why=list-empty", out)
    s = Scene(base, names=["root", None])
    rc, out = k_api(exe, s, "root")
    row("K83", "API: root, though written on the list: listed=0 why=not-sd-user", rc == 1 and out == "listed=0 why=not-sd-user", out)
    s = Scene(base, names=["nosuchuserx", None])
    rc, out = k_api(exe, s, "nosuchuserx")
    row("K84", "API: a name with no Linux user: listed=0 why=not-sd-user", rc == 1 and out == "listed=0 why=not-sd-user", out)
    s = Scene(base)
    os.chmod(s.api, 0o666)
    rc, out = k_api(exe, s, ME)
    row("K85", "API: a list writable by others: listed=0 why=list-unsafe", rc == 1 and out == "listed=0 why=list-unsafe", out)
    s = Scene(base)
    real = os.path.join(s.d, "api-elsewhere")
    os.rename(s.api, real)
    os.symlink(real, s.api)
    rc, out = k_api(exe, s, ME)
    row("K86", "API: a list that is a link: listed=0 why=list-unsafe", rc == 1 and out == "listed=0 why=list-unsafe", out)
    if other:
        s = Scene(base)
        rc, out = k_api(exe, s, ME, group=other)
        row("K87", "API: a listed user not in the group asked for: listed=0 why=not-sd-user", rc == 1 and out == "listed=0 why=not-sd-user", out)
    s = Scene(base)
    rc, out = k_api(exe, s, "Don")
    row("K88", "API: a name in capitals: listed=0 why=not-sd-user", rc == 1 and out == "listed=0 why=not-sd-user", out)

    rows += helper_rows(block, base)
    return rows, skipped


def helper_rows(block, base):
    rows = []

    def row(i, label, ok, detail=""):
        rows.append((i, label, bool(ok), detail))

    def content(p):
        try:
            with open(p) as f:
                return f.read()
        except OSError:
            return None

    def mode(p):
        return oct(os.stat(p).st_mode & 0o777) if os.path.exists(p) else None

    row("H0", "the helper's block was cut out of sd-elevate between its markers and holds the functions",
        all("%s()" % fn in block for fn in ("sdsys_local_read", "sdsys_local_user_ok", "sdsys_local_change", "sdsys_local_status", "sdsys_local_decide",
                                            "sdsys_local_loopback", "sdsys_local_safe_dir", "sdsys_local_safe_file")), block[:80])
    s = Scene(base, names=None)
    f = s.list
    chg = lambda *a, dry=0: hrun(block, "sdsys_local_change", f, MYUID, MYGROUP, *a, dry=dry)
    # the name rules
    for i, n, why in (("H1", "Don", "capitals"), ("H2", "1abc", "a digit first"), ("H3", "-x", "a dash first"), ("H4", "a" * 33, "33 characters"),
                      ("H5", "root", "root"), ("H6", "sdsys", "sdsys"), ("H7", "nosuchuserx", "a user that does not exist"),
                      ("H8", "daemon", "a system account (uid 1)"), ("H8b", "a;b", "a shell character")):
        rc, out = chg("add", n)
        row(i, "add refuses %s and leaves no list" % why, rc == 2 and "REFUSED" in out and content(f) is None, out[-160:])
    other = not_my_group()
    if other:
        rc, out = hrun(block, "sdsys_local_change", f, MYUID, other, "add", ME)
        row("H9", "add refuses a user who is not in the group asked for (%s)" % other, rc == 2 and "is not in the group" in out and content(f) is None, out[-160:])
    rc, out = chg("add", ME, dry=1)
    row("H10", "--dry-run add says what it would write and writes nothing", rc == 0 and ("would write %s: %s" % (f, ME)) in out and content(f) is None, out[-160:])
    rc, out = chg("add", ME)
    row("H11", "add writes the name, one to a line, mode 0644, and says added", rc == 0 and content(f) == ME + "\n" and mode(f) == "0o644"
        and ("added %s; listed now: %s" % (ME, ME)) in out, repr((rc, content(f), mode(f), out[-160:])))
    leftovers = [x for x in os.listdir(s.sdcore) if x.startswith(".sdsys-local.")]
    row("H12", "the write leaves no temporary file behind (one rename)", leftovers == [], repr(leftovers))
    rc, out = chg("add", ME)
    row("H13", "add of a name already listed changes nothing and says so (idempotent)", rc == 0 and "is listed already; nothing was changed" in out and content(f) == ME + "\n", out[-160:])
    rc, out = hrun(block, "sdsys_local_status", f, MYUID)
    row("H14", "status says 'sdsys local ssh: listed <names>'", rc == 0 and out == "sdsys local ssh: listed %s" % ME, out)
    rc, out = chg("remove", "nobodyhere")
    row("H15", "remove of a name not listed changes nothing and says so", rc == 0 and "is not listed; nothing was changed" in out and content(f) == ME + "\n", out[-160:])
    rc, out = chg("remove", ME)
    row("H16", "remove of the last name removes the file (absent is empty)", rc == 0 and content(f) is None and "listed now: none" in out, out[-160:])
    rc, out = hrun(block, "sdsys_local_status", f, MYUID)
    row("H17", "status of no file says 'sdsys local ssh: none listed'", rc == 0 and out == "sdsys local ssh: none listed", out)
    Scene.write(f, "".join("u%02d\n" % k for k in range(31)))
    rc, out = chg("add", ME)
    row("H18", "add is taken as the 32nd name", rc == 0 and content(f).splitlines()[-1] == ME and len(content(f).splitlines()) == 32, out[-160:])
    rc, out = chg("remove", "u05")
    row("H19", "remove takes out one name and keeps the order of the rest", rc == 0 and content(f).splitlines() == ["u%02d" % k for k in range(31) if k != 5] + [ME], out[-160:])
    Scene.write(f, "".join("u%02d\n" % k for k in range(32)))
    before = content(f)
    rc, out = chg("add", ME)
    row("H20", "a 33rd name is refused and the list is left as it was", rc == 2 and "32 names already" in out and content(f) == before, out[-160:])
    rc, out = chg("clear", dry=1)
    row("H21", "--dry-run clear says it would remove the file and keeps it", rc == 0 and ("would remove %s" % f) in out and content(f) == before, out[-160:])
    rc, out = chg("clear")
    row("H22", "clear removes the file", rc == 0 and content(f) is None and "cleared, none listed" in out, out[-160:])
    rc, out = chg("clear")
    row("H23", "clear with nothing listed changes nothing and says so", rc == 0 and "none listed already; nothing was changed" in out, out[-160:])
    # a link, a group-writable file
    tgt = os.path.join(s.d, "target")
    Scene.write(tgt, "")
    if os.path.lexists(f):        # only on a mutant that left a file behind; the real helper has removed it (H22, H23)
        os.unlink(f)
    os.symlink(tgt, f)
    rc, out = chg("add", ME)
    row("H24", "add with a link in place of the file is refused, and the file it points at is not written", rc == 2 and "is a link" in out and content(tgt) == "" and os.path.islink(f), out[-160:])
    rc, out = hrun(block, "sdsys_local_status", f, MYUID)
    row("H25", "status of a link says 'unsafe, treated as none listed'", rc == 0 and out.startswith("sdsys local ssh: unsafe, treated as none listed"), out)
    rc, out = chg("clear")
    row("H26", "clear removes the link itself, not the file it points at", rc == 0 and not os.path.lexists(f) and os.path.exists(tgt), out[-160:])
    Scene.write(f, "u01\n", mode=0o664)
    rc, out = chg("add", ME)
    row("H27", "add to a group-writable list is refused and the list is left as it was", rc == 2 and "list-unsafe" in out and content(f) == "u01\n", out[-160:])
    if os.path.lexists(f):
        os.unlink(f)
    os.chmod(s.sdcore, 0o775)
    rc, out = chg("add", ME)
    row("H28", "add into a group-writable /etc/sdcore is refused and nothing is written", rc == 2 and content(f) is None, out[-160:])
    os.chmod(s.sdcore, 0o755)
    shutil.rmtree(s.sdcore)
    rc, out = chg("add", ME)
    row("H29", "add with no /etc/sdcore makes it 0755 and writes the list", rc == 0 and content(f) == ME + "\n" and mode(s.sdcore) == "0o755", out[-160:])
    rc, out = hrun(block, "sdsys_local_status", s.api, MYUID)
    row("H30", "status of the api list names its kind: 'sdsys local api: none listed'", rc == 0 and out == "sdsys local api: none listed", out)
    for i, h, ok in (("H31", "127.0.0.1", True), ("H32", "::1", True), ("H33", "0:0:0:0:0:0:0:1", True), ("H34", "localhost", False),
                     ("H35", "127.0.0.256", False), ("H36", "::ffff:127.0.0.1", False), ("H37", "", False), ("H38", "10.0.0.1", False)):
        rc, out = hrun(block, "sdsys_local_loopback", h)
        row(i, "the helper's loopback test %s %r" % ("takes" if ok else "refuses", h), (rc == 0) == ok, "rc=%d %s" % (rc, out))
    return rows


def text_rows(src):
    rows = []

    def row(i, label, ok, detail=""):
        rows.append((i, label, bool(ok), detail))

    cp = code(src["cproc"])
    ap = code(src["apisrvr"])
    vb = code(src["verb"])
    small = [k for k in FILES if len(src[k]) <= (10 if k == "voct" else 40)]      # the VOC record is three short lines
    row("T0", "NULL CASE: every source was found and is not empty", small == [], repr(small))
    # cproc
    sub = cp[cp.find("sdsys.local:"):cp.find("display.admin.notice:")]
    row("T1", "cproc: the subroutine asks the kernel first, returns on '' with why= only when the list is in use, checks the credential, asks the password "
        "ONCE (hidden), checks it with !CRED_VERIFY, grants, audits the grant after it, and adds notice 14177",
        ordered(sub, "lsd.user = kernel(K$SDSYS.LOCAL, 0)", "if lsd.user = '' then", "lsd.word = kernel(K$SDSYS.LOCAL, 1)",
                "if lsd.word # 'list-empty' then lsd.why = ' why=' : lsd.word", "return", "openpath @sdsys:@ds:'$cred' to lsd.cred.f then",
                "input lsd.pw hidden", "call !CRED_VERIFY('sdsys', lsd.pw, lsd.ok)", "if not(lsd.ok) then", "lsd.state = 'refused'",
                "void kernel(K$ADMINISTRATOR, 1)", "void kernel(K$AUDIT, 'elevation granted reason=sdsys local ssh user=' : lsd.user)",
                "admin.notice<-1> = sysmsg(14177, lsd.user)", "lsd.state = 'granted'") and sub.count("input ") == 1, sub[:120])
    row("T2", "cproc: a wrong password and no credential each refuse with their own message and audit line, and set refused",
        ordered(sub, "sysmsg(14176)", "'elevation refused reason=sdsys local ssh no credential user=' : lsd.user", "lsd.state = 'refused'")
        and ordered(sub, "sysmsg(14175)", "'elevation refused reason=sdsys local ssh wrong password user=' : lsd.user", "lsd.state = 'refused'"), "")
    row("T3", "cproc: the subroutine grants in ONE place, and only after !CRED_VERIFY said yes",
        sub.count("kernel(K$ADMINISTRATOR, 1)") == 1 and sub.find("if not(lsd.ok) then") < sub.find("kernel(K$ADMINISTRATOR, 1)"), "")
    arms = [m.start() for m in re.finditer(r"gosub sdsys\.local\n", cp)]
    ok3 = len(arms) == 2
    for a in arms:
        seg = cp[a:a + 900]
        ok3 = ok3 and ordered(seg, "gosub sdsys.local", "if lsd.state = 'granted' then goto elevation.done", "if lsd.state = 'refused' then goto abort.cproc",
                              "refuse.msg = sysmsg(10195)", "'elevation refused reason=sdsys session without a sdsys login' : lsd.why", "goto abort.cproc")
    row("T4", "cproc: BOTH arms ask the subroutine BEFORE the 10195 refusal; granted joins elevation.done, refused ends, '' leaves the old refusal "
        "(its audit line plus lsd.why)", ok3, repr(arms))
    loc = cp.find("if downcase(kernel(K$USERNAME, 0)) = 'sdsys' and env('SSH_CONNECTION') = '' and env('SSH_TTY') = '' then")
    row("T5", "cproc: the local arm asks the subroutine only where K$LOGIN.UID said the login was not sdsys's (after that test)",
        bool(arms) and 0 < loc < cp.find("if kernel(K$LOGIN.UID, 'sdsys') = 1 then", loc) < arms[0], "")
    row("T6", "cproc: the subroutine reads no environment variable and no SSH_ variable", "env(" not in sub and "SSH_" not in sub, "")
    row("T7", "cproc: the subroutine is the only place K$SDSYS.LOCAL is asked in cproc", cp.count("K$SDSYS.LOCAL") == 2 and sub.count("K$SDSYS.LOCAL") == 2, "")
    # 18 Nov 26: a phantom, and a session with no terminal (ssh without -t, input from a pipe), is NOT asked the password: the old refusal
    # stands with why=no-terminal.  The test must come before the credential is read and before the prompt.
    noterm = sub.find("if is.phantom or kernel(K$TTY, 0) = '' then")
    row("T8", "cproc: a phantom or a session with no terminal is not asked: the test sets why=no-terminal and returns BEFORE the credential is read "
        "and the password is asked",
        0 < noterm < sub.find("openpath @sdsys:@ds:'$cred'") < sub.find("input lsd.pw hidden")
        and "lsd.why = ' why=no-terminal'" in sub[noterm:noterm + 120] and "return" in sub[noterm:noterm + 160], "at %d" % noterm)
    # apisrvr
    la = ap[ap.find("if downcase(scram.user) = 'sdsys' and sdsys.api.from = '' then"):ap.find("if not(kernel(K$ASSUME.USER, scram.user)) then")]
    row("T10", "apisrvr: the local door asks the API list only on the Unix socket, only for a peer that is not sdsys, and admits only when the peer's "
        "LOGIN (system(44)) is that same user; the admission sets sdsys.api.from to 'this machine user=<name>'",
        ordered(la, "api.peer.user = downcase(trim(system(43)))", "if api.peer.addr[1,1] = '/' and api.peer.user # 'sdsys' and api.peer.user # '' then",
                "if kernel(K$SDSYS.LOCAL, 'api' : @fm : api.peer.user) = 1 then", "api.local.login = downcase(trim(system(44)))",
                "if api.local.login = api.peer.user then", "api.local.user = api.peer.user", "if api.local.user # '' then",
                "sdsys.api.from = 'this machine user=' : api.local.user"), la[:120])
    row("T11", "apisrvr: the list is asked BEFORE K$ASSUME.USER (while the process is still root) and nowhere else",
        ap.count("K$SDSYS.LOCAL") == 2 and 0 < ap.find("kernel(K$SDSYS.LOCAL, 'api'") < ap.find("if not(kernel(K$ASSUME.USER, scram.user)) then"), "")
    row("T12", "apisrvr: anyone else meets the old refusals unchanged: 10922 when the socket or the peer is wrong, then 10195 when the login is not sdsys's",
        ordered(la, "end else", "if not(sdsys.api.ok) then", "sysmsg(10922)", "goto exit.vb.scram.fail", "api.peer.login = downcase(trim(system(44)))",
                "if api.peer.login # 'sdsys' then", "sysmsg(10195)", "goto exit.vb.scram.fail", "sdsys.api.from = 'this machine'"), "")
    row("T13", "apisrvr: loopback TCP stays refused for SDSYS (the socket test is still there) and no address test was added for the local door",
        "if api.peer.addr[1,1] # '/' then sdsys.api.ok = @false" in la and "addrmatch" not in la and "peer_local" not in la, "")
    row("T14", "apisrvr: the local door reads no environment variable", "env(" not in la, "")
    row("T15", "apisrvr: the grant is still the one under sdsys.api.from, after K$ASSUME.USER (its audit line then names the user)",
        ap.count("kernel(K$ADMINISTRATOR, 1)") == 1 and ordered(ap, "if not(kernel(K$ASSUME.USER, scram.user)) then", "if sdsys.api.from # '' then",
                                                               "void kernel(K$ADMINISTRATOR, 1)", "'elevation granted reason=sdsys api from=' : sdsys.api.from"), "")
    # the kernel, the keys, sd.c
    c = src["c"]
    row("T20", "sd_localsdsys.c reads the environment only in sdsys_local_detect (two getenv calls, both there)",
        c.count("getenv(") == 2 and c.find("getenv(") > c.find("void sdsys_local_detect(int argc)"), "")
    opk = src["opkernel"]
    case = opk[opk.find("    case K_SDSYS_LOCAL:"):]
    case = case[:case.find("      break;")]
    row("T21", "op_kernel.c: the case passes the FIXED paths of sd_localsdsys.h and root (0) as the owner, for both lists",
        all(x in case for x in ("lf.list = SD_LOCAL_SSH_LIST;", "lf.loginuid = SD_LOCAL_LOGINUID;", "lf.sessionid = SD_LOCAL_SESSIONID;",
                                "lf.cgroup = SD_LOCAL_CGROUP;", "lf.sessions = SD_LOCAL_SESSIONS;", "lf.group = SD_LOCAL_GROUP;", "lf.owner = 0;",
                                "sd_local_listed(SD_LOCAL_API_LIST, arg + 4, SD_LOCAL_GROUP, 0, &sd_local_why)")) and "getenv" not in case, case[:100])
    h = src["h"]
    row("T22", "sd_localsdsys.h: the production paths are /etc/sdcore/sdsys-local-ssh and -api, /proc/self/{loginuid,sessionid,cgroup}, /run/systemd/sessions, sdusers",
        all(x in h for x in ('"/etc/sdcore/sdsys-local-ssh"', '"/etc/sdcore/sdsys-local-api"', '"/proc/self/loginuid"', '"/proc/self/sessionid"',
                             '"/proc/self/cgroup"', '"/run/systemd/sessions"', '#define SD_LOCAL_GROUP       "sdusers"', '"/usr/local/bin/sd-sdsys"')), "")
    row("T23", "the key is 175 in gplsrc/keys.h and int$keys.h, no other key is 175, and 174 (Windows' K$OS.SDSYS.USER) is defined in neither",
        re.search(r"#define K_SDSYS_LOCAL\s+175\b", src["keysc"]) is not None and re.search(r"\$define K\$SDSYS\.LOCAL\s+175\b", src["keysb"]) is not None
        and len(re.findall(r"#define\s+\w+\s+175\b", src["keysc"])) == 1 and len(re.findall(r"\$define\s+\S+\s+175\b", src["keysb"])) == 1
        and re.search(r"#define\s+\w+\s+174\b", src["keysc"]) is None and re.search(r"\$define\s+\S+\s+174\b", src["keysb"]) is None, "")
    row("T24", "sd_localsdsys is linked into sd (gpl.src) and sd.c calls sdsys_local_detect(argc) right after xfer_detect(argc)",
        "sd_localsdsys" in src["gplsrc_list"].split() and ordered(src["sdc"], "xfer_detect(argc);", "sdsys_local_detect(argc);")
        and src["sdc"].count("sdsys_local_detect(argc);") == 1, "")
    # ssh-forcecommand, the wrapper, installer, deleter
    fc = src["fc"]
    rn = fc[fc.find("refuse_now() {"):]
    rn = rn[:rn.find("\n}\n")]
    row("T30", "ssh-forcecommand --refuse runs the wrapper (a fixed path) only for exactly sd-sdsys with SSH_CONNECTION set, and refuses otherwise as before",
        "SDSYS_LOCAL_WRAPPER=/usr/local/bin/sd-sdsys\n" in fc and
        ordered(rn, '[[ ${SSH_ORIGINAL_COMMAND:-} == sd-sdsys && -n ${SSH_CONNECTION:-} && -x $SDSYS_LOCAL_WRAPPER ]]', 'exec "$SDSYS_LOCAL_WRAPPER"', "exit 1"), "")
    wl = [l for l in src["wrapper"].splitlines() if l.strip() and not l.startswith("#")]
    row("T31", "the wrapper is one exec: /usr/bin/sudo -n /usr/local/sbin/sd-elevate sdsys-session, nothing passed through",
        src["wrapper"].startswith("#!/bin/sh\n") and wl == ["exec /usr/bin/sudo -n /usr/local/sbin/sd-elevate sdsys-session"], repr(wl))
    ins = src["installer"]
    inscmd = "\n".join(l for l in ins.splitlines() if not l.lstrip().startswith("#"))
    row("T32", "the installer installs the wrapper root:root 0755 and NOTHING in it makes a list file (absent = empty = off)",
        "sudo install -o root -g root -m 0755 gplbld/sd-sdsys /usr/local/bin/sd-sdsys" in inscmd and "sdsys-local-" not in inscmd, "")
    dl = src["deleter"]
    blk = dl[dl.find("# SDSYSLOCAL-BEGIN"):dl.find("# SDSYSLOCAL-END")]
    row("T33", "the deleter removes both lists only when the configuration is deleted (an upgrade keeps them), and removes the wrapper with the helper",
        'if [ "$conf_deleted" = yes ]; then' in blk and "/etc/sdcore/sdsys-local-ssh /etc/sdcore/sdsys-local-api" in blk
        and ordered(dl, "sudo rm -f /usr/local/sbin/sd-elevate", "sudo rm -f /usr/local/bin/sd-sdsys")
        and dl.find("# SDSYSLOCAL-END") < dl.find("sudo rmdir /etc/sdcore"), blk[:120])
    # the helper's verbs, as text
    el = src["elevate"]
    arm = el[el.find("\n  sdsys-local)\n"):el.find("\n  sdsys-session)\n")]
    row("T40", "sd-elevate: sdsys-local passes the fixed file under /etc/sdcore and root (0) as the owner, asks for root and an sdsys caller before a change",
        "\nSDSYS_LOCAL_DIR=/etc/sdcore\n" in el and 'sdsys_local_change "$SDSYS_LOCAL_DIR/sdsys-local-$1" 0 sdusers "$2" "${3:-}"' in arm
        and ordered(arm, "need_root", "sdsys_local_caller", "sdsys_local_change"), arm[:100])
    ss = el[el.find("sdsys_session() {"):]
    ss = ss[:ss.find("\n}\n")]
    row("T41", "sd-elevate sdsys-session: SUDO_UID required, the facts read from /proc/self, the decision with owner 0 on the fixed list and "
        "/run/systemd/sessions, then setpriv to sdsys with a clean environment, need_root before the exec, and a dry run that execs nothing",
        ordered(ss, '[[ -n $suid ]] || die', "lu=$(cat /proc/self/loginuid", "sid=$(cat /proc/self/sessionid", "cg=$(cat /proc/self/cgroup",
                'sdsys_local_decide 0 "$SDSYS_LOCAL_DIR/sdsys-local-ssh" sdusers /run/systemd/sessions "$lu" "$suid" "$sid" "$cg"',
                "cmd=(env -i)", '--reuid=sdsys --regid=sdusers --init-groups -- "$SDSYS_LOCAL_SD"', "if [[ $DRY -eq 1 ]]; then", "exit 0", "need_root",
                'exec "${cmd[@]}"') and "SDSYS_LOCAL_SD=/usr/local/sdsys/bin/sd\n" in el and "SD_" not in ss.replace("SDSYS_LOCAL", ""), "")
    row("T42", "sd-elevate: the sdsys-session verb takes no argument", '  sdsys-session)\n    [[ $# -eq 0 ]] || die "sdsys-session takes no argument"' in el, "")
    # sudoers
    sd = src["sudoers"]
    sline = [l for l in sd.splitlines() if l.startswith("%sdusers")]
    cmds = [x.strip() for x in sline[0].split("NOPASSWD:", 1)[1].split(",")] if len(sline) == 1 else []
    row("S1", "sudoers: %sdusers has exactly five argument lists, the fifth 'sd-elevate sdsys-session' with no wildcard; sdsys's one line is unchanged",
        cmds == ["/usr/local/sbin/sd-elevate cred-own query", "/usr/local/sbin/sd-elevate cred-own verify", "/usr/local/sbin/sd-elevate cred-own set",
                 "/usr/local/sbin/sd-elevate netcred-dir", "/usr/local/sbin/sd-elevate sdsys-session"] and "*" not in sline[0]
        and [l for l in sd.splitlines() if l.startswith("sdsys")] == ["sdsys ALL=(root) NOPASSWD: /usr/local/sbin/sd-elevate"], repr(cmds))
    # the verb
    row("V1", "local.sdsys: the administrator first, before any word is read", ordered(vb, "if not(kernel(K$ADMINISTRATOR, -1)) then", "stop sysmsg(2001)", "words = downcase(trim(@sentence))"), "")
    row("V2", "local.sdsys: the words are lower case, ssh or api, add / remove / clear, no.query only after an added name",
        "words = downcase(trim(@sentence))" in vb and "if list.kind # 'ssh' and list.kind # 'api' then" in vb
        and "case action = 'add'" in vb and "case action = 'remove'" in vb and "case action = 'clear'" in vb and "if nwords = 5 and words<5> = 'no.query' then" in vb, "")
    row("V3", "local.sdsys: the name is checked character by character BEFORE the one os.execute that could carry it; the helper is the only program run",
        ordered(vb, "convert 'abcdefghijklmnopqrstuvwxyz0123456789_-' to '' in chk", "if chk # '' or len(uname) < 1 or len(uname) > 32", "sysmsg(14184, uname)",
                "os.execute cmd") and vb.count("os.execute") == 2 and "cmd = HELPER : ' sdsys-local ' : list.kind : ' ' : action" in vb
        and "os.execute HELPER : ' sdsys-local ' : list.kind : ' status'" in vb, "")
    row("V4", "local.sdsys add: the warning (14179 ssh, 14180 api) is shown, and the question asked unless no.query, BEFORE the helper; anything but y changes nothing",
        ordered(vb, "if action = 'add' then", "sysmsg(14179, uname)", "if not(no.query) then", "sysmsg(14181, uname, list.kind)", "input answer",
                "if downcase(trim(answer)) # 'y' then", "sysmsg(14182, uname)", "stop", "os.execute cmd") and "sysmsg(14180, uname)" in vb, "")
    row("V5", "local.sdsys: one audit line per change, local.sdsys <kind> <action> {user=<name>} status=ok|refused, after the helper ran",
        ordered(vb, "os.execute cmd", "rc = os.error()", "outcome = 'refused'", "outcome = 'ok'",
                "void kernel(K$AUDIT, 'local.sdsys ' : list.kind : ' ' : action : (if action = 'clear' then '' else ' user=' : uname) : ' status=' : outcome)"), "")
    row("V6", "local.sdsys is the administrator's: voc_template has V CA $localsdsys and newvoc has no record; the program is $internal, catalogued $localsdsys",
        src["voct"] == "V\nCA\n$localsdsys\n" and not os.path.exists(NEWVOC_REC) and "$internal" in src["verb"] and "$catalog $localsdsys" in src["verb"], repr(src["voct"]))
    present = [n for n in MESSAGES if os.path.isfile(os.path.join(MSG, n)) and open(os.path.join(MSG, n), encoding="latin-1").read().strip()]
    row("V7", "messages 14175 to 14184 exist; 14177 names the user (%1) and says SD administration granted; 14179 and 14180 say the network is included",
        present == MESSAGES and open(os.path.join(MSG, "14177"), encoding="latin-1").read().startswith("SD administration granted")
        and "%1" in open(os.path.join(MSG, "14177"), encoding="latin-1").read()
        and all("over the network included" in open(os.path.join(MSG, n), encoding="latin-1").read().replace("\\n", " ") for n in ("14179", "14180")), repr(present))
    return rows


def visudo_row(src):
    vs = shutil.which("visudo") or (os.path.exists("/usr/sbin/visudo") and "/usr/sbin/visudo")
    if not vs:
        return None, "visudo is not installed here: S2 SKIPPED (not passed)"
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "sdcore")
        with open(p, "w") as f:
            f.write(src["sudoers"])
        r = subprocess.run([vs, "-cf", p], capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    if r.returncode != 0 and ("ermission" in out or "not owned" in out.lower()):
        return None, "visudo -cf could not judge the file as this user (%s): S2 SKIPPED (not passed)" % out[:120]
    return ("S2", "visudo -cf accepts sdcore.sudoers (%s)" % vs, r.returncode == 0 and "parsed OK" in out, out[:200]), None


def all_rows(cc, tmp, src, tag):
    exe, p = build(cc, tmp, src["c"], src["h"], tag)
    built = p.returncode == 0 and not p.stderr.strip()
    rows = [("B0", "sd_localsdsys.c and verify-localsdsys.c build with -Wall -Wextra and no warning", built, p.stderr[:300])]
    skipped = []
    block = helper_block(src["elevate"])
    if built:
        base = os.path.join(tmp, "scenes-" + tag)
        os.makedirs(base)
        r, skipped = kernel_and_helper_rows(exe, block, base)
        rows += r
    rows += text_rows(src)
    return rows, skipped


def sub(key, old, new):
    def f(src):
        s = dict(src)
        if s[key].count(old) != 1:
            raise KeyError("%s: the text to change is found %d times, not once: %r" % (key, s[key].count(old), old[:70]))
        s[key] = s[key].replace(old, new)
        return s
    return f


MUTANTS = [
    # the kernel
    # (each mutant keeps every function and variable in use, so that the build stays clean and a row, not B0's warning, has to catch it)
    ("the loopback test is dropped", sub("c", "|| !loopback_literal(val)) { *why", "|| !(loopback_literal(val) || 1)) { *why")),
    ("any IPv4 address is loopback", sub("c", "return (ntohl(a4.s_addr) >> 24) == 127;", "return 1;")),
    ("the service is not asked", sub("c", '    if (!line_value(text, "SERVICE", val, sizeof val) || strcmp(val, "sshd") != 0) { *why = "not-ssh"; return -1; }\n', "")),
    ("REMOTE is not asked", sub("c", '    if (!line_value(text, "REMOTE", val, sizeof val) || strcmp(val, "1") != 0) { *why = "not-ssh"; return -1; }\n', "")),
    ("an unset login uid is taken", sub("c", " || lu == 4294967295UL) { *why = \"no-login\"", ") { *why = \"no-login\"")),
    ("the list is not compared", sub("c", '    if (!on_list(names, count, user)) { *why = "not-listed"; return -1; }\n', "")),
    ("the record's uid is not compared", sub("c", '    if (!line_value(text, "UID", val, sizeof val) || strcmp(val, num) != 0) { *why = "other-user"; return -1; }\n', "")),
    ("the audit session is not compared", sub("c", '    if (!line_value(text, "AUDIT", val, sizeof val) || strcmp(val, num) != 0) { *why = "other-session"; return -1; }\n', "")),
    ("a group-writable file is believed", sub("c", "if (st.st_uid != owner || (st.st_mode & 022) != 0) return 0;", "if (st.st_uid != owner) return 0;")),
    ("the owner is not compared", sub("c", "if (st.st_uid != owner || (st.st_mode & 022) != 0) return 0;", "if ((st.st_uid != owner && 0) || (st.st_mode & 022) != 0) return 0;")),
    ("a second hard link is believed", sub("c", "if (type == S_IFREG && (st.st_nlink != 1 || st.st_size >= TEXT_MAX)) return 0;", "if (type == S_IFREG && (st.st_size >= TEXT_MAX)) return 0;")),
    ("a link is followed", sub("c", "    fd = openat(dfd, base, O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC);", "    fd = openat(dfd, base, O_RDONLY | O_NONBLOCK | O_CLOEXEC);")),
    ("the parent is not checked", sub("c", "    if (!safe_fd(pfd, S_IFDIR, owner)) { close(pfd); return -1; }\n", "")),
    ("the group is not asked", sub("c", "            for (i = 0; i < got; i++) if (list[i] == want) ok = 1;", "            for (i = 0; i < got; i++) if (list[i] == want || 1) ok = 1;")),
    ("a system account may be listed", sub("c", "pw->pw_uid == 0 || pw->pw_uid < SD_LOCAL_UID_MIN", "pw->pw_uid == 0")),
    ("33 names are taken", sub("c", " || count >= SD_LOCAL_MAX_NAMES)", ")")),
    ("a key given twice is believed", sub("c", "            if (found != NULL) return 0;\n", "")),
    ("the cgroup is not bound to the session's scope", sub("c", "    if (!line_value(text, \"SCOPE\", val, sizeof val) || strcmp(val, want) != 0) { *why = \"no-session\"; return -1; }\n", "")),
    # the helper
    ("the helper does not compare sudo's caller", sub("elevate", '  if [[ ! $su =~ ^[0-9]{1,10}$ || $su != "$lu" ]]; then SL_WHY=other-user; return 1; fi\n', "")),
    ("the helper takes a host name", sub("elevate", "  [[ $h =~ ^[0-9a-fA-F:]{2,39}$ ]] || return 1\n", "  [[ $h == localhost ]] && return 0\n  [[ $h =~ ^[0-9a-fA-F:]{2,39}$ ]] || return 1\n")),
    ("the helper writes through a link", sub("elevate", '  [[ ! -L $f ]] || die "$f is a link: refused, nothing was changed (clear removes it)"\n', "")),
    ("the helper adds any name", sub("elevate", '    sdsys_local_user_ok "$n" "$g" || die "$SL_UWHY; nothing was changed"\n', "    :\n")),
    ("the helper takes a 33rd name", sub("elevate", "    (( ${#keep[@]} < SDSYS_LOCAL_MAX )) || die", "    (( 1 )) || die")),
    ("the helper writes the list 0664", sub("elevate", '    chmod 0644 -- "$tmp" ||', '    chmod 0664 -- "$tmp" ||')),
    ("the helper's session is not bound to the record's audit id", sub("elevate", ' || ${kv[AUDIT]-} != "$sid" ]]', " ]]")),
    ("sdsys-session skips root before the exec", sub("elevate", "  need_root\n  cd -- \"$home\"", "  cd -- \"$home\"")),
    # cproc and apisrvr
    ("cproc grants before the password", sub("cproc", "   display 'SD password of sdsys: ' :\n", "   void kernel(K$ADMINISTRATOR, 1)\n   display 'SD password of sdsys: ' :\n")),
    ("cproc grants on a wrong password", sub("cproc", "   if not(lsd.ok) then\n", "   if @false then\n")),
    ("cproc's local arm skips the subroutine", sub("cproc", "            gosub sdsys.local\n            if lsd.state = 'granted' then goto elevation.done\n            if lsd.state = 'refused' then goto abort.cproc\n* 18 Sep 26", "* 18 Sep 26")),
    ("cproc always writes why=", sub("cproc", "      if lsd.word # 'list-empty' then lsd.why = ' why=' : lsd.word\n", "      lsd.why = ' why=' : lsd.word\n")),
    ("apisrvr does not compare the login", sub("apisrvr", "                        if api.local.login = api.peer.user then\n", "                        if @true then\n")),
    ("apisrvr asks the list for a TCP peer", sub("apisrvr", "if api.peer.addr[1,1] = '/' and api.peer.user # 'sdsys' and api.peer.user # '' then", "if api.peer.user # 'sdsys' and api.peer.user # '' then")),
    # the rest
    ("sudoers takes any argument", sub("sudoers", "/usr/local/sbin/sd-elevate sdsys-session", "/usr/local/sbin/sd-elevate sdsys-session *")),
    ("the verb reads words before the administrator test", sub("verb", "   if not(kernel(K$ADMINISTRATOR, -1)) then\n      stop sysmsg(2001)  ;* Command requires administrator privileges\n   end\n", "")),
    ("the verb adds without asking", sub("verb", "      if not(no.query) then\n", "      if @false then\n")),
    ("the installer makes an empty list", sub("installer", "sudo install -o root -g root -m 0755 gplbld/sd-sdsys /usr/local/bin/sd-sdsys\n", "sudo install -o root -g root -m 0755 gplbld/sd-sdsys /usr/local/bin/sd-sdsys\nsudo touch /etc/sdcore/sdsys-local-ssh\n")),
    ("the deleter removes the lists on an upgrade", sub("deleter", '# SDSYSLOCAL-BEGIN\nif [ "$conf_deleted" = yes ]; then', "# SDSYSLOCAL-BEGIN\nif true; then")),
    ("the refusal arm runs the wrapper for any command", sub("fc", "[[ ${SSH_ORIGINAL_COMMAND:-} == sd-sdsys && ", "[[ ")),
]


def report(rows):
    bad = 0
    for i, label, ok, detail in rows:
        say("  [%s] %s %s%s" % ("PASS" if ok else "FAIL", i, label, "" if ok or not detail else "   <- " + str(detail)[:240]))
        bad += 0 if ok else 1
    return bad


def main(argv):
    cc = shutil.which("cc") or shutil.which("gcc")
    if not cc:
        say("test-localsdsys-units: CANNOT RUN - no C compiler")
        return 2
    if MYUID < 1000 or ME in ("root", "sdsys"):
        say("test-localsdsys-units: CANNOT RUN - the test plays the listed user itself and must be an ordinary user (uid 1000 or more), not %s (%d)" % (ME, MYUID))
        return 2
    src = load()
    say("test-localsdsys-units: the listed user is %s (uid %d), the group %s; sources %s" % (ME, MYUID, MYGROUP, ", ".join(FILES[k] for k in ("c", "elevate", "cproc", "apisrvr", "verb"))))
    tmp = tempfile.mkdtemp(prefix="localsdsys-")
    try:
        if "--selftest" in argv:
            base, skipped = all_rows(cc, tmp, src, "base")
            if any(not r[2] for r in base) or len(base) < MIN_ROWS:
                report(base)
                say("selftest: the real sources do not pass (%d rows)" % len(base))
                return 1
            say("  control : the real sources, %d rows, all passed" % len(base))
            missed = 0
            for k, (name, mut) in enumerate(MUTANTS):
                try:
                    msrc = mut(src)
                except KeyError as e:
                    say("  [MISSED  ] %s: %s" % (name, e))
                    missed += 1
                    continue
                rows, _s = all_rows(cc, tmp, msrc, "m%d" % k)
                failed = [r[0] for r in rows if not r[2]]
                say("  [%s] %-58s %s" % ("KILLED  " if failed else "SURVIVED", name, " ".join(failed[:8])))
                missed += 0 if failed else 1
            say("")
            say("test-localsdsys-units --selftest: %s - %d mutants, %d not caught" % ("PASSED" if missed == 0 else "FAILED", len(MUTANTS), missed))
            return 0 if missed == 0 else 1
        rows, skipped = all_rows(cc, tmp, src, "base")
        vr, vskip = visudo_row(src)
        if vr:
            rows.append(vr)
        else:
            skipped.append(vskip)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    bad = report(rows)
    for s in skipped:
        say("  [SKIPPED] " + s)
    if len(rows) < MIN_ROWS:
        say("test-localsdsys-units: FAILED - only %d rows (fewer than %d: the null case)" % (len(rows), MIN_ROWS))
        return 1
    say("test-localsdsys-units: %d passed, %d failed, %d skipped" % (len(rows) - bad, bad, len(skipped)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
