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
#   C2 (24 Oct 2026, the owner: "Start C2"): sdlnxd.c bounds what one uid may add (AUDIT_RATE_MAX records per AUDIT_RATE_WINDOW seconds, asked of a record already judged
#      well-formed, keyed by the CREDENTIALS' uid, on the monotonic clock), writes ONE line when a window that dropped records ends (each tick, and every window on the way
#      out), and rotates by size BEFORE it appends, under ERRLOG_SEM, with audit_rotate_file() (audit_rot.c) which k_error.c audit_rotate() now calls too; the Makefile and
#      gpl.src build it into both programs.  "--selftest --from=32" runs only the C2 mutants.
# NOT SAID HERE: that the daemon stamps what it should when it runs - that is sandbox-auditwriter.py; that a DIFFERENT uid is stamped truly needs two users: the VM.
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, "..", "gplsrc"))
FILES = {"k_error.c": None, "sdlnxd.c": None, "sddefs.h": None, "audit_rot.c": None, "Makefile": None, "gpl.src": None}
REAL = {}
for _k in FILES:
    # the C sources are in gplsrc; the Makefile and the object list are one directory up
    REAL[_k] = os.path.join(SRC if _k.endswith((".c", ".h")) else os.path.dirname(SRC), _k)
    FILES[_k] = os.environ.get("AW_" + re.sub(r"\W", "_", _k).upper(), REAL[_k])
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


def raw(name):
    return open(FILES[name], encoding="latin-1").read()


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
    fl = func(s, "static int audit_format_line(char* line, size_t linesz, const char* user, const char* login, const char* who, int pid, const char* msg)")
    em = func(s, "static void audit_emit_line(const char* line, int len)")
    row("S2 the line is built from the daemon's own format: user, sudo, login, the claimed number, the pid, then the text as an argument (audit_format_line)",
        '"%04d-%02d-%02d %02d:%02d:%02d user=%s%s%s uid=%s pid=%d %s\\n"' in fl and "audit_format_line(line, sizeof(line), user, login, who, (int)cred->pid, msg)" in wr, "")
    row("S3 the text is never a format string in this daemon (the only formatted write of a line is the one in audit_format_line)",
        len(re.findall(r"\bsnprintf\(line,", fl)) == 1 and "snprintf(line," not in wr and not re.search(r"\bprintf\(\s*msg", s) and not re.search(r"\bsnprintf\([^,]*,[^,]*,\s*msg\b", s)
        and not re.search(r"log_message\(msg", wr), "")
    row("S4 the credentials come from SCM_CREDENTIALS, and a datagram without them is dropped",
        "SCM_CREDENTIALS" in rc and "have_cred" in rc and bool(re.search(r"if \(!have_cred\) \{\s*audit_dropped\+\+;\s*return;", rc)), "")
    row("S5 a truncated datagram, a truncated control message or one over the limit is dropped",
        "MSG_TRUNC | MSG_CTRUNC" in rc and "n > AUDIT_DGRAM_MAX" in rc, "")
    row("S6 a datagram without the magic, with no number or with no text is dropped", "strncmp(buf, AUDIT_MAGIC, magic) != 0" in wr and wr.count("audit_dropped++") >= 4, "")
    row("S7 the text is made safe (below 32, 127 and 248 and over become ?) and cut at AUDIT_MSG_MAX",
        "< 32" in wr and "== 127" in wr and ">= 248" in wr and "msg[AUDIT_MSG_MAX] = '\\0';" in wr, "")
    row("S8 the file is the daemon's own sysdir + audit, opened O_APPEND | O_NOFOLLOW and NEVER created (audit_emit_line)",
        bool(em) and 'own_sysdir_path, DS' in em and "O_WRONLY | O_APPEND | O_NOFOLLOW" in em and "O_CREAT" not in em, "")
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
    i_chk, i_chmod, i_sock = so.find("is not ours or can be written by others"), so.find("chmod(dir, 0755);"), so.find("socket(AF_UNIX, SOCK_DGRAM")
    row("S15 the daemon sets its directory to 0755 ITSELF, after the check that the directory is ours and before the socket is made, whoever started it and under any umask "
        "(mkdir(dir, 0755) is cut by the umask: the real install made it 0750 and no member of sdusers could search it)",
        0 <= i_chk < i_chmod < i_sock and "(void)chmod(dir, 0755);" in so and not re.search(r"if \(geteuid\(\) == 0\)\s*\(void\)chmod\(dir", so), "positions %d %d %d" % (i_chk, i_chmod, i_sock))
    rt = func(s, "static bool audit_rate_take(uid_t uid, pid_t pid)")
    rn = func(s, "static void audit_rate_note(const AUDIT_RATE* s)")
    rcl = func(s, "static void audit_rate_close(AUDIT_RATE* s)")
    rs = func(s, "static void audit_rate_sweep(bool all)")
    ck = func(s, "static time_t audit_clock(void)")
    row("S14 the daemon does not die on a bad datagram: nothing that handles one or writes a line ever exit()s or abort()s",
        not re.search(r"\b(exit|abort|_exit)\s*\(", wr + rc + fl + em + rt + rn + rcl + rs), "")

    # ---- C2 (24 Oct 2026): a bound on what one uid may add, and rotation by size in the daemon ----
    row("C2.0 the C2 functions are found", all((fl, em, rt, rn, rcl, rs, ck)), "")
    row("D2 sddefs.h: 600 records in 60 seconds per uid, the rotation size of 1 MiB, and audit_rotate_file()'s prototype",
        bool(re.search(r"#define AUDIT_RATE_MAX 600\s", d)) and bool(re.search(r"#define AUDIT_RATE_WINDOW 60\s", d)) and bool(re.search(r"#define AUDIT_ROTATE_BYTES 1048576L\s", d))
        and "int audit_rotate_file(const char* path, long limit);" in d, "")
    i_valid = wr.find("if (*msg == '\\0') {")
    i_take = wr.find("if (!audit_rate_take(cred->uid, cred->pid))\n    return;")
    row("R1 the bound is asked of a record already judged well-formed and made safe, with the CREDENTIALS' uid and pid (never the text's number), before anything is looked up or written",
        0 <= i_valid < wr.find("msg[AUDIT_MSG_MAX] = '\\0';") < i_take < wr.find("audit_user_name(cred->uid") < wr.find("audit_emit_line(line, len)"), "")
    row("R2 at the limit the record is dropped and counted, never written; under it the count goes up",
        "if (s->count >= AUDIT_RATE_MAX) {" in rt and "s->dropped++;" in rt and "audit_limited++;" in rt and "return FALSE;" in rt and 0 <= rt.find("return FALSE;") < rt.find("s->count++;"), "")
    row("R2b when a uid's window is over its count starts again (the window is AUDIT_RATE_WINDOW seconds from the first record, not for ever)",
        "} else if (now - s->start >= AUDIT_RATE_WINDOW) {\n    audit_rate_close(s);\n    s->start = now;\n    s->count = 0;\n  }" in rt, "")
    row("R3 a window is counted on the monotonic clock, not the wall clock (which can be set back)",
        "CLOCK_MONOTONIC" in ck and "CLOCK_REALTIME" not in ck and "audit_clock()" in rt and "audit_clock()" in rs and "time(" not in rt.replace("audit_clock(", "") + rs.replace("audit_clock(", ""), "")
    row("R4 a window that dropped records has ONE line: the credentials' user, the last sender's pid, numbers and constants only, the same format as every line",
        'snprintf(msg, sizeof(msg), "audit rate limit dropped=%lu taken=%lu limit=%d window=%d", s->dropped, s->count, AUDIT_RATE_MAX, AUDIT_RATE_WINDOW);' in rn
        and "audit_user_name(s->uid, user, sizeof(user));" in rn and 'audit_format_line(line, sizeof(line), user, "", "?", (int)s->pid, msg)' in rn
        and "if (s->dropped > 0)\n    audit_rate_note(s);\n  s->dropped = 0;" in rcl, "")
    mn2 = func(s, "int main()")
    i_loop, i_sw1 = mn2.find("audit_serve(TICK_SECONDS);"), mn2.find("audit_rate_sweep(FALSE);")
    i_sw2, i_closesock = mn2.find("audit_rate_sweep(TRUE);"), mn2.find("close(audit_sock)")
    row("R5 the sweep runs every tick after audit_serve(), and once more with every window on the way out, before the socket is closed",
        0 <= i_loop < i_sw1 < i_sw2 < i_closesock, "positions %d %d %d %d" % (i_loop, i_sw1, i_sw2, i_closesock))
    row("R5b a window that is over frees its slot",
        "audit_rate[i].start = 0;" in rs and "now - audit_rate[i].start >= AUDIT_RATE_WINDOW" in rs, "")
    row("R6 a full table closes the oldest window (and writes its line) before the slot is given to another uid",
        0 <= rt.find("audit_rate_close(oldest);") < rt.find("s = oldest;"), "")
    i_ls, i_start = em.find("lstat(path"), em.find("StartExclusive(ERRLOG_SEM")
    i_rot, i_end, i_open = em.find("audit_rotate_file(path, AUDIT_ROTATE_BYTES)"), em.find("EndExclusive(ERRLOG_SEM)"), em.find("open(path")
    row("R7 the file is rotated BEFORE the record is appended, under the error log's semaphore, with the function sd -start uses; a failure is counted and not tried again for a minute",
        0 <= i_ls < i_start < i_rot < i_end < i_open and "audit_rotate_failed++;" in em and "audit_rotate_after = now + 60;" in em and "now >= audit_rotate_after" in em, "")
    ar = code("audit_rot.c")
    kr = func(k, "void audit_rotate(void)")
    row("R8 k_error.c audit_rotate() is a call: the semaphore around audit_rotate_file(path, AUDIT_ROTATE_BYTES), and none of the rotation is left in k_error.c",
        "StartExclusive(ERRLOG_SEM, 68);" in kr and "(void)audit_rotate_file(path, AUDIT_ROTATE_BYTES);" in kr and "EndExclusive(ERRLOG_SEM);" in kr
        and "rename(" not in k and "FS_IOC" not in k and "#define AUDIT_ROTATE_BYTES" not in k, "")
    i_lift = ar.find("ioctl(fd, FS_IOC_SETFLAGS, &flags) != 0")
    i_ret, i_ren = ar.find("return -1;", i_lift), ar.find("rename(path, rotated) == 0")
    row("R9 audit_rot.c: the attribute is lifted only to rename (nothing is renamed when it will not lift); the new file is made O_EXCL | O_NOFOLLOW with the old owner and mode; "
        "both files get the attribute back; nothing is unlinked or truncated",
        0 <= i_lift < i_ret < i_ren and "O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW" in ar and "fchown(newfd, statbuf.st_uid, statbuf.st_gid)" in ar
        and "fchmod(newfd, statbuf.st_mode & 07777)" in ar and "newflags |= FS_APPEND_FL;" in ar and "flags |= FS_APPEND_FL;\n          (void)ioctl(fd, FS_IOC_SETFLAGS, &flags);" in ar
        and "O_RDONLY | O_NOFOLLOW" in ar and not re.search(r"\b(unlink|truncate|ftruncate)\s*\(|O_TRUNC", ar), "")
    i_exist, i_openfd = ar.find("if ((lstat(rotated, &existing) == 0) || (errno != ENOENT))\n        return -1;"), ar.find("fd = open(path, O_RDONLY | O_NOFOLLOW")
    row("R9b a rotated file of the same second is never replaced: the name is tried with lstat() BEFORE the trail is opened, and a taken name (or any answer but 'not there') refuses the rotation",
        0 <= i_exist < i_openfd and "#include <errno.h>" in ar, "positions %d %d" % (i_exist, i_openfd))
    row("R10 both programs get it: gpl.src lists audit_rot (the kernel) and the Makefile links audit_rot.o into sdlnxd",
        "\naudit_rot\n" in raw("gpl.src") and "sdlnxd: sdlnxd.o sdsem.o audit_rot.o" in raw("Makefile") and "$(GPLOBJ)audit_rot.o -o $(GPLBIN)sdlnxd" in raw("Makefile"), "")
    row("R11 the daemon's periodic note in the error log keeps 'audit: N datagram(s) refused, N record(s) not written' (the sandbox suite reads it), adds the two new counts and resets all four",
        '"audit: %lu datagram(s) refused, %lu record(s) not written, %lu over the rate bound, %lu rotation(s) failed, since the last note"' in mn2
        and all(("%s = 0;" % v) in mn2 for v in ("audit_dropped", "audit_unwritten", "audit_limited", "audit_rotate_failed")), "")
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
M_C2 = len(MUTANTS)   # the first mutant of option C2 (24 Oct 26): "--selftest --from=%d" runs these alone
MUTANTS += [
    ("rate-keyed-by-pid", "sdlnxd.c", "audit_rate_take(cred->uid, cred->pid)", "audit_rate_take((uid_t)cred->pid, cred->pid)"),
    ("rate-bound-gone", "sdlnxd.c", "  if (!audit_rate_take(cred->uid, cred->pid))\n    return;\n", ""),
    ("rate-off-by-one", "sdlnxd.c", "if (s->count >= AUDIT_RATE_MAX) {", "if (s->count > AUDIT_RATE_MAX) {"),
    ("rate-never-resets", "sdlnxd.c", "} else if (now - s->start >= AUDIT_RATE_WINDOW) {", "} else if (FALSE) {"),
    ("rate-wall-clock", "sdlnxd.c", "CLOCK_MONOTONIC, &t);", "CLOCK_REALTIME, &t);"),
    ("flood-no-line", "sdlnxd.c", "if (s->dropped > 0)\n    audit_rate_note(s);", "if (FALSE)\n    audit_rate_note(s);"),
    ("flood-line-names-root", "sdlnxd.c", "audit_user_name(s->uid, user, sizeof(user));\n  snprintf(msg,", "strcpy(user, \"root\");\n  snprintf(msg,"),
    ("sweep-not-called", "sdlnxd.c", "audit_rate_sweep(FALSE);", "(void)0;"),
    ("no-flush-at-exit", "sdlnxd.c", "audit_rate_sweep(TRUE);", "(void)0;"),
    ("full-table-silent", "sdlnxd.c", "audit_rate_close(oldest);", "(void)0;"),
    ("slots-never-freed", "sdlnxd.c", "audit_rate[i].start = 0;", "(void)0;"),
    ("rotation-not-asked", "sdlnxd.c", "if (audit_rotate_file(path, AUDIT_ROTATE_BYTES) < 0) {", "if (0) {"),
    ("rotation-without-lock", "sdlnxd.c", "StartExclusive(ERRLOG_SEM, 70);", ""),
    ("rotation-retried-every-record", "sdlnxd.c", "audit_rotate_after = now + 60;", ""),
    ("note-without-counts", "sdlnxd.c", ", %lu over the rate bound, %lu rotation(s) failed, since the last note\"", ", since the last note\""),
    ("rate-limit-huge", "sddefs.h", "AUDIT_RATE_MAX 600", "AUDIT_RATE_MAX 600000"),
    ("rotate-size-huge", "sddefs.h", "AUDIT_ROTATE_BYTES 1048576L", "AUDIT_ROTATE_BYTES 1048576000L"),
    ("rot-unlinks", "audit_rot.c", "if (rename(path, rotated) == 0) {", "if (unlink(path) == 0) {"),
    ("rot-attribute-not-put-back", "audit_rot.c", "flags |= FS_APPEND_FL;\n          (void)ioctl(fd, FS_IOC_SETFLAGS, &flags);", "(void)0;"),
    ("rot-new-file-without-attribute", "audit_rot.c", "newflags |= FS_APPEND_FL;", "(void)0;"),
    ("rot-new-file-any-owner", "audit_rot.c", "fchown(newfd, statbuf.st_uid, statbuf.st_gid)", "fchown(newfd, 0, 0)"),
    ("rot-new-file-truncates", "audit_rot.c", "O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW", "O_WRONLY | O_CREAT | O_TRUNC | O_NOFOLLOW"),
    ("rot-renames-when-stuck", "audit_rot.c", "close(fd); /* cannot lift it: leave the trail whole */\n            return -1;", "close(fd);"),
    ("rot-replaces-a-rotated-file", "audit_rot.c", "      if ((lstat(rotated, &existing) == 0) || (errno != ENOENT))\n        return -1;\n", ""),
    ("rot-only-refuses-a-hit", "audit_rot.c", "(lstat(rotated, &existing) == 0) || (errno != ENOENT)", "(lstat(rotated, &existing) == 0)"),
    ("kernel-keeps-its-own-rotation", "k_error.c", "(void)audit_rotate_file(path, AUDIT_ROTATE_BYTES);", "(void)0;"),
    ("daemon-not-linked", "Makefile", "$(GPLOBJ)audit_rot.o -o $(GPLBIN)sdlnxd", "-o $(GPLBIN)sdlnxd"),
    ("kernel-not-linked", "gpl.src", "analyse\naudit_rot\n", "analyse\n"),
]
M_RUN = len(MUTANTS)   # the first mutant of the /run/sd mode (25 Oct 26, real-install witness): "--selftest --from=%d" runs these alone
MUTANTS += [
    ("dir-mode-left-to-umask", "sdlnxd.c", "(void)chmod(dir, 0755);", "(void)0;"),
    ("dir-mode-0750", "sdlnxd.c", "(void)chmod(dir, 0755);", "(void)chmod(dir, 0750);"),
    ("dir-mode-0777", "sdlnxd.c", "(void)chmod(dir, 0755);", "(void)chmod(dir, 0777);"),
    ("dir-mode-only-as-root", "sdlnxd.c", "  (void)chmod(dir, 0755);", "  if (geteuid() == 0)\n    (void)chmod(dir, 0755);"),
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
    _from = [int(a.split("=", 1)[1]) for a in sys.argv[1:] if a.startswith("--from=")]
    sys.exit(selftest(_from[0] if _from else 0) if "--selftest" in sys.argv else run())
