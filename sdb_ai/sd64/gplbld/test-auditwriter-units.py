#!/usr/bin/env python3
# test-auditwriter-units.py - W.11 F4, option C1 (24 Oct 2026, the owner: "b then c"): the audit trail has a writer that is not the user.  A session hands each record to the
# root daemon (sdlnxd) over a Unix datagram socket; the daemon stamps the user and the pid from the credentials the KERNEL attaches to the datagram.  FREE CHECK, text only
# (comments removed), no install, no sudo, no sd.
#
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-auditwriter-units.py
#   python3 /home/don/Projects/SDCore4Linux/sdb_ai/sd64/gplbld/test-auditwriter-units.py --selftest      (mutants)
#
#   D  sddefs.h: the socket path, the magic (ends with a space) and the datagram limit, fixed at compile time
#   C  k_error.c, the client: audit_to_daemon() sends ONE datagram (magic, the claimed SD user number or ?, the text - no time, no user, no pid) to SD_AUDIT_SOCK, never to a
#      path from the environment; it retries only a full queue; audit_message() tries the daemon first and appends to the file itself only when the daemon did not take it
#   S  sdlnxd.c, the server: SO_PASSCRED is set before the bind; the user comes from getpwuid() of the CREDENTIALS' uid and the pid from the credentials, never from the text;
#      a datagram with no credentials, a truncated one, one over the limit or one without the magic is dropped; the text is made safe and cut; the format string is the
#      daemon's; the file is opened by the daemon's own path with O_APPEND | O_NOFOLLOW and never created; the socket is made root-only first, then 0660 sdusers; its
#      directory must be ours and, as root, closed to the group and others; the loop waits in audit_serve(), not sleep()
# NOT SAID HERE: that the daemon stamps what it should when it runs - that is sandbox-auditwriter.py; that a DIFFERENT uid is stamped truly needs two users: the VM.
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, "..", "gplsrc"))
FILES = {"k_error.c": None, "sdlnxd.c": None, "sddefs.h": None}
for _k in FILES:
    FILES[_k] = os.environ.get("AW_" + re.sub(r"\W", "_", _k).upper(), os.path.join(SRC, _k))
passed = failed = 0


def row(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print("  [PASS] " + name)
    else:
        failed += 1
        print("  [FAIL] " + name + ("   <- " + detail if detail else ""))


def code(name):
    s = open(FILES[name], encoding="latin-1").read()
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    return re.sub(r"//[^\n]*", "", s)


def func(src, head):
    m = re.search(re.escape(head) + r"[^;{]*\{.*?\n\}", src, re.S)
    return m.group(0) if m else ""


def run():
    d = code("sddefs.h")
    row("D1 sddefs.h defines the socket path, the magic with its trailing space and the datagram limit",
        '#define SD_AUDIT_SOCK "/run/sd/audit.sock"' in d and '#define AUDIT_MAGIC "SDAUDIT1 "' in d and "#define AUDIT_DGRAM_MAX 2048" in d)

    k = code("k_error.c")
    cl = func(k, "Private bool audit_to_daemon(const char* msg)")
    row("C0 audit_to_daemon() is found", bool(cl))
    row("C1 it sends ONE datagram of the form MAGIC + claimed number + space + text, and nothing else (no time, user or pid)",
        '"%s%s %s", AUDIT_MAGIC, who, msg' in cl and cl.count("sendto(") == 1 and "SOCK_DGRAM" in cl and "AF_UNIX" in cl, cl[:160])
    row("C2 to SD_AUDIT_SOCK only: no environment variable can move it", "SD_AUDIT_SOCK" in cl and "getenv" not in cl, "")
    row("C3 MSG_DONTWAIT, and a retry only for a full queue or a signal (EAGAIN, ENOBUFS, EINTR)",
        "MSG_DONTWAIT" in cl and all(e in cl for e in ("EAGAIN", "ENOBUFS", "EINTR")) and cl.count("errno") == 3, "")
    row("C4 the claimed number is the session's user table number when it has one, else a question mark",
        bool(re.search(r"my_uptr != NULL\) && \(my_uptr->uid > 0\)\)\s*snprintf\(who, sizeof\(who\), \"%d\", \(int\)\(my_uptr->uid\)\);\s*else\s*strcpy\(who, \"\?\"\);", cl)), "")
    row("C5 it answers True only when the whole datagram was accepted", "return n == len;" in cl)
    am = func(k, "void audit_message(char* msg)")
    row("C6 audit_message() hands the record to the daemon FIRST and appends to the file itself only when the daemon did not take it",
        bool(re.search(r"if \(!audit_to_daemon\(msg\)\)\s*audit_append_file\(buff, bytes\);", am)), am[-500:])
    row("C7 audit_append_file() is the old code: ERRLOG_SEM, O_APPEND | O_NOFOLLOW, never O_CREAT",
        "O_WRONLY | O_APPEND | O_NOFOLLOW" in func(k, "Private void audit_append_file(const char* buff, int bytes)") and "O_CREAT" not in func(k, "Private void audit_append_file(const char* buff, int bytes)"), "")

    s = code("sdlnxd.c")
    wr = func(s, "static void audit_write_record(const struct ucred* cred, char* buf, ssize_t n)")
    rc = func(s, "static void audit_receive_one(void)")
    so = func(s, "static bool audit_socket_open(void)")
    sv = func(s, "static void audit_serve(int seconds)")
    row("S0 the daemon's four audit functions are found", all((wr, rc, so, sv)))
    row("S1 the user on the line is getpwuid()'s name of the CREDENTIALS' uid (via audit_user_name), the pid is the credentials' pid",
        "audit_user_name(cred->uid, user, sizeof(user));" in wr and "(int)cred->pid, msg" in wr and "getpwuid(uid)" in func(s, "static void audit_user_name(uid_t uid, char* out, size_t outsz)"), "")
    row("S2 the line is built from the daemon's own format: user, sudo, login, the claimed number, the pid, then the text as an argument",
        '"%04d-%02d-%02d %02d:%02d:%02d user=%s%s%s uid=%s pid=%d %s\\n"' in wr, "")
    row("S3 the text is never a format string in this daemon (the only formatted write is the one above)",
        len(re.findall(r"\bsnprintf\(line,", wr)) == 1 and not re.search(r"printf\(\s*msg", s) and not re.search(r"log_message\(msg", wr), "")
    row("S4 the credentials come from SCM_CREDENTIALS, and a datagram without them is dropped",
        "SCM_CREDENTIALS" in rc and "have_cred" in rc and bool(re.search(r"if \(!have_cred\) \{\s*audit_dropped\+\+;\s*return;", rc)), "")
    row("S5 a truncated datagram, a truncated control message or one over the limit is dropped",
        "MSG_TRUNC | MSG_CTRUNC" in rc and "n > AUDIT_DGRAM_MAX" in rc, "")
    row("S6 a datagram without the magic, with no number or with no text is dropped", "strncmp(buf, AUDIT_MAGIC, magic) != 0" in wr and wr.count("audit_dropped++") >= 4, "")
    row("S7 the text is made safe (below 32, 127 and 248 and over become ?) and cut at AUDIT_MSG_MAX",
        "< 32" in wr and "== 127" in wr and ">= 248" in wr and "msg[AUDIT_MSG_MAX] = '\\0';" in wr, "")
    row("S8 the file is the daemon's own sysdir + audit, opened O_APPEND | O_NOFOLLOW and NEVER created",
        'own_sysdir_path, DS' in wr and "O_WRONLY | O_APPEND | O_NOFOLLOW" in wr and "O_CREAT" not in wr, "")
    i_pass, i_bind = so.find("SO_PASSCRED"), so.find("bind(audit_sock")
    row("S9 SO_PASSCRED is set before the bind", 0 <= i_pass < i_bind, "SO_PASSCRED at %d, bind at %d" % (i_pass, i_bind))
    i_umask, i_chmod = so.find("umask(0177)"), so.find("chmod(SD_AUDIT_SOCK, 0660)")
    row("S10 the socket is made root-only (umask 0177 around the bind), then given to sdusers and 0660; a stale socket is unlinked first",
        0 <= so.find("unlink(SD_AUDIT_SOCK)") < i_umask < i_bind < i_chmod and "getgrnam(\"sdusers\")" in so, "")
    row("S11 its directory must be ours, a directory, and - as root - closed to the group and others, or no socket is made",
        "S_ISDIR" in so and "st.st_uid != geteuid()" in so and "S_IWGRP | S_IWOTH" in so, "")
    mn = func(s, "int main()")
    row("S12 main() waits in audit_serve(TICK_SECONDS) and no sleep() is left in it", "audit_serve(TICK_SECONDS);" in mn and "sleep(" not in mn, "")
    row("S13 on the way out the daemon closes the socket and unlinks it only if it made it", "unlink(SD_AUDIT_SOCK)" in mn and "audit_sock_made" in mn, "")
    row("S14 the daemon does not die on a bad datagram: audit_receive_one() and audit_write_record() never exit() or abort()",
        not re.search(r"\b(exit|abort|_exit)\s*\(", wr + rc), "")
    print("test-auditwriter-units: %d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


MUTANTS = [   # name, file, old, new
    ("magic-without-space", "sddefs.h", '"SDAUDIT1 "', '"SDAUDIT1"'),
    ("socket-path-moved", "sddefs.h", '"/run/sd/audit.sock"', '"/tmp/audit.sock"'),
    ("datagram-limit", "sddefs.h", "AUDIT_DGRAM_MAX 2048", "AUDIT_DGRAM_MAX 65000"),
    ("client-sends-pid", "k_error.c", '"%s%s %s", AUDIT_MAGIC, who, msg', '"%s%s %s %d", AUDIT_MAGIC, who, msg, (int)getpid()'),
    ("client-env-path", "k_error.c", "strcpy(sa.sun_path, SD_AUDIT_SOCK);", "strcpy(sa.sun_path, getenv(\"SD_AUDIT\") ? getenv(\"SD_AUDIT\") : SD_AUDIT_SOCK);"),
    ("client-blocks", "k_error.c", "MSG_DONTWAIT, (struct", "0, (struct"),
    ("client-retries-everything", "k_error.c", "if ((n >= 0) || ((errno != EAGAIN) && (errno != ENOBUFS) && (errno != EINTR)))", "if (n >= 0)"),
    ("client-wrong-claim", "k_error.c", "(my_uptr->uid > 0)", "(my_uptr->uid > -99)"),
    ("client-always-true", "k_error.c", "return n == len;", "return TRUE;"),
    ("file-first", "k_error.c", "if (!audit_to_daemon(msg))\n    audit_append_file(buff, bytes);", "audit_append_file(buff, bytes);\n  (void)audit_to_daemon(msg);"),
    ("file-always", "k_error.c", "if (!audit_to_daemon(msg))\n    audit_append_file(buff, bytes);", "(void)audit_to_daemon(msg);\n  audit_append_file(buff, bytes);"),
    ("append-creates", "k_error.c", "O_WRONLY | O_APPEND | O_NOFOLLOW | O_CLOEXEC);\n    if (fd >= 0) {\n      if (write(fd, buff, bytes)", "O_WRONLY | O_APPEND | O_CREAT | O_NOFOLLOW | O_CLOEXEC, 0620);\n    if (fd >= 0) {\n      if (write(fd, buff, bytes)"),
    ("user-from-text", "sdlnxd.c", "audit_user_name(cred->uid, user, sizeof(user));", "snprintf(user, sizeof(user), \"%s\", msg);"),
    ("pid-from-text", "sdlnxd.c", "(int)cred->pid, msg", "atoi(msg), msg"),
    ("format-is-the-text", "sdlnxd.c", 'uid=%s pid=%d %s\\n"', 'uid=%s pid=%d "'),
    ("no-credentials-ok", "sdlnxd.c", "if (!have_cred) {\n    audit_dropped++;\n    return;\n  }", "if (!have_cred) {\n    memset(&cred, 0, sizeof(cred));\n  }"),
    ("truncated-ok", "sdlnxd.c", "(mh.msg_flags & (MSG_TRUNC | MSG_CTRUNC)) || ", ""),
    ("oversize-ok", "sdlnxd.c", " || (n > AUDIT_DGRAM_MAX)", ""),
    ("magic-not-checked", "sdlnxd.c", " || (strncmp(buf, AUDIT_MAGIC, magic) != 0)", ""),
    ("controls-kept", "sdlnxd.c", "if (((unsigned char)*p < 32) || ((unsigned char)*p == 127) || ((unsigned char)*p >= 248))\n      *p = '?';", ""),
    ("no-cut", "sdlnxd.c", "if (strlen(msg) > AUDIT_MSG_MAX)\n    msg[AUDIT_MSG_MAX] = '\\0';", ""),
    ("daemon-creates-the-trail", "sdlnxd.c", "O_WRONLY | O_APPEND | O_NOFOLLOW | O_CLOEXEC);\n  if ((fd < 0)", "O_WRONLY | O_APPEND | O_CREAT | O_NOFOLLOW | O_CLOEXEC, 0600);\n  if ((fd < 0)"),
    ("follows-links", "sdlnxd.c", "O_WRONLY | O_APPEND | O_NOFOLLOW | O_CLOEXEC);\n  if ((fd < 0)", "O_WRONLY | O_APPEND | O_CLOEXEC);\n  if ((fd < 0)"),
    ("no-passcred", "sdlnxd.c", "setsockopt(audit_sock, SOL_SOCKET, SO_PASSCRED,", "setsockopt(audit_sock, SOL_SOCKET, SO_KEEPALIVE,"),
    ("socket-world-open", "sdlnxd.c", "chmod(SD_AUDIT_SOCK, 0660)", "chmod(SD_AUDIT_SOCK, 0666)"),
    ("no-umask", "sdlnxd.c", "old = umask(0177);", "old = umask(0);"),
    ("stale-socket-kept", "sdlnxd.c", "(void)unlink(SD_AUDIT_SOCK); /* a left-over", "(void)0; /* a left-over"),
    ("dir-not-checked", "sdlnxd.c", "|| (st.st_uid != geteuid())", ""),
    ("dir-open-to-others", "sdlnxd.c", "((geteuid() == 0) && (st.st_mode & (S_IWGRP | S_IWOTH)))", "0"),
    ("sleep-again", "sdlnxd.c", "audit_serve(TICK_SECONDS); /* takes", "sleep(TICK_SECONDS); /* takes"),
    ("socket-left-behind", "sdlnxd.c", "  if (audit_sock_made)\n    (void)unlink(SD_AUDIT_SOCK);\n", ""),
    ("dies-on-a-bad-datagram", "sdlnxd.c", "  if (!have_cred) {\n    audit_dropped++;\n    return;\n  }", "  if (!have_cred) {\n    exit(9);\n  }"),
]


def selftest():
    import shutil
    t = tempfile.mkdtemp()
    caught = missed = 0
    print("selftest: the real files first (must pass), then mutants (each must not)")
    r = subprocess.run([sys.executable, os.path.abspath(__file__)], capture_output=True, text=True)
    if r.returncode != 0:
        print("  [FAIL] the real files do not pass:\n" + r.stdout[-900:])
        return 1
    print("  [ok] the real files pass")
    for name, which, old, new in MUTANTS:
        real = open(os.path.join(SRC, which), encoding="latin-1").read()
        if old not in real:
            print("  [MISSED] %s: the text to change is not there" % name)
            missed += 1
            continue
        f = os.path.join(t, name + "-" + which)
        open(f, "w", encoding="latin-1").write(real.replace(old, new, 1))
        env = dict(os.environ)
        env["AW_" + re.sub(r"\W", "_", which).upper()] = f
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
    sys.exit(selftest() if "--selftest" in sys.argv else run())
