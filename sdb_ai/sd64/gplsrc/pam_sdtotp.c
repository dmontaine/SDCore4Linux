/* pam_sdtotp.c
 * SD's own PAM module: the authenticator code that the sdsys user is asked for, before
 * its Linux password, when it logs in over ssh (S.95).
 * Copyright (c) 2026 The SD Developers, All Rights Reserved
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3, or (at your option)
 * any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software Foundation,
 * Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
 *
 * START-HISTORY:
 * 01 Nov 26 dm  S.95 stage 2 - written.  Checked by gplbld/test-pam-sdtotp.py, which drives
 *               it through a real PAM stack (pam_start_confdir) on a scratch store.
 * END-HISTORY
 *
 * START-DESCRIPTION:
 *
 * THE LINES THAT CALL IT (installed in /etc/pam.d/sshd, and only there, above its @include
 * lines - never in common-auth, which login, su and sudo share):
 *
 *     auth [success=1 default=ignore] pam_succeed_if.so quiet user notin sdsys
 *     auth required /usr/local/lib/sd/pam_sdtotp.so
 *
 * THE CODE IS ASKED BEFORE THE PASSWORD, and the stack goes on to ask for the password
 * whatever happened here (the module is `required`, not `requisite`), so a person who
 * fails cannot tell which of the two was wrong.
 *
 * WHAT IT ANSWERS.  PAM_IGNORE for any user but sdsys (the first line above should keep
 * them out; this is the second wall).  PAM_AUTH_ERR for everything that is not a good
 * code, a store that is not what it should be and a source that is locked included:
 * this module fails closed.  PAM_SUCCESS only for a code (or recovery code) the store
 * accepted.
 *
 * COUNTING.  The attempt is counted when it STARTS (sd_totps_attempt), so a login that
 * is abandoned counts.  A right code leaves a MARK (sd_totps_ok); only pam_sm_setcred,
 * which sshd calls once the WHOLE login has succeeded (the password stage included),
 * turns the mark into forgetting the source's failures (sd_totps_clear).  So a login
 * that gives the right code and the wrong password stays counted: both factors are.
 * The state is per source address (PAM_RHOST), not per account: the name sdsys is public.
 * UseDNS should be left off (its default), or PAM_RHOST is a name the other side chooses.
 *
 * ARGUMENTS are the root-owned configuration line's, not the caller's: dir=PATH (the store),
 * audit=PATH (the audit daemon's socket), delay_ms=N (the wait after a failure, default
 * 3000; 10000 while the global slow-down is in force; 0 turns the wait off, for the test).
 *
 * EVERY ATTEMPT IS WRITTEN TWICE: one datagram to the audit daemon (the form sdlnxd takes:
 * the magic, a '?' for the SD user number, the text) and one pam_syslog line (authpriv).
 * The text names the source and a reason, never a code.
 *
 * END-DESCRIPTION
 */

#define _GNU_SOURCE

#include <errno.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <syslog.h>
#include <time.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/un.h>

#define PAM_SM_AUTH
#define PAM_SM_SESSION
#include <fcntl.h>
#include <sys/stat.h>
#include <security/pam_modules.h>
#include <security/pam_ext.h>

#include <openssl/crypto.h>

#include "sd_totp.h"
#include "sd_totp_store.h"

#ifndef SD_AUDIT_SOCK
#define SD_AUDIT_SOCK "/run/sd/audit.sock"          /* gplsrc/sddefs.h; the check holds the two together */
#endif
#define AUDIT_MAGIC     "SDAUDIT1 "
#define SD_USER         "sdsys"
#define DELAY_DEFAULT   3000u                       /* milliseconds */
#define DELAY_SLOW      10000000u                   /* microseconds, while the global slow-down is in force */
#define PROMPT          "Verification code: "
#define WINDOW_DEFAULT  2                           /* S.101: steps either side (the owner: more time to read the phone) */
#define MARKS_DEFAULT   "/run/sdcore/marks"         /* S.101: the login markers; /run is wiped at boot */

#define SD_EXPORT __attribute__((visibility("default")))

struct opts {
    const char *dir;
    const char *audit;
    unsigned delay_ms;
    int window;                                     /* S.101: window=N, 1 to SD_TOTP_WINDOW_MAX */
    int local;                                      /* S.101: `local` - this line is on a console or desktop service (login, gdm-password ...) */
    const char *marks;                              /* S.101: marks=PATH, the directory of login markers */
};

static void parse_args(pam_handle_t *pamh, int argc, const char **argv, struct opts *o)
{
    int i;
    char *end;
    unsigned long v;

    o->dir = SD_TOTPS_DIR_DEFAULT;
    o->audit = SD_AUDIT_SOCK;
    o->delay_ms = DELAY_DEFAULT;
    o->window = WINDOW_DEFAULT;
    o->local = 0;
    o->marks = MARKS_DEFAULT;
    for (i = 0; i < argc; i++) {
        if (strncmp(argv[i], "dir=/", 5) == 0) {
            o->dir = argv[i] + 4;
        } else if (strncmp(argv[i], "audit=/", 7) == 0) {
            o->audit = argv[i] + 6;
        } else if (strncmp(argv[i], "marks=/", 7) == 0) {
            o->marks = argv[i] + 6;
        } else if (strcmp(argv[i], "local") == 0) {
            o->local = 1;
        } else if (strncmp(argv[i], "window=", 7) == 0) {
            v = strtoul(argv[i] + 7, &end, 10);
            if (*end == '\0' && argv[i][7] != '\0' && v >= 1 && v <= SD_TOTP_WINDOW_MAX) o->window = (int)v;
            else pam_syslog(pamh, LOG_WARNING, "pam_sdtotp: %s is not a window of 1 to %d steps; ignored", argv[i], SD_TOTP_WINDOW_MAX);
        } else if (strncmp(argv[i], "delay_ms=", 9) == 0) {
            v = strtoul(argv[i] + 9, &end, 10);
            if (*end == '\0' && argv[i][9] != '\0' && v <= 60000UL) o->delay_ms = (unsigned)v;
            else pam_syslog(pamh, LOG_WARNING, "pam_sdtotp: %s is not a number of milliseconds up to 60000; ignored", argv[i]);
        } else {
            pam_syslog(pamh, LOG_WARNING, "pam_sdtotp: unknown argument %s; ignored", argv[i]);
        }
    }
}

/* One datagram to the audit daemon, as the kernel's audit_to_daemon() sends one.  A full queue must not stall a login: a few short retries. */
static void send_audit(const struct opts *o, const char *text)
{
    char dg[640];
    struct sockaddr_un sa;
    struct timespec pause = { 0, 2000000 };
    int len;
    int s;
    int tries;

    if (strlen(o->audit) >= sizeof sa.sun_path) return;
    len = snprintf(dg, sizeof dg, "%s? %s", AUDIT_MAGIC, text);
    if (len < 0) return;
    if (len >= (int)sizeof dg) len = (int)sizeof dg - 1;
    s = socket(AF_UNIX, SOCK_DGRAM | SOCK_CLOEXEC, 0);
    if (s < 0) return;
    memset(&sa, 0, sizeof sa);
    sa.sun_family = AF_UNIX;
    strcpy(sa.sun_path, o->audit);
    for (tries = 0; tries < 4; tries++) {
        if (sendto(s, dg, (size_t)len, MSG_DONTWAIT, (struct sockaddr *)&sa, sizeof sa) >= 0) break;
        if (errno != EAGAIN && errno != ENOBUFS && errno != EINTR) break;
        nanosleep(&pause, NULL);
    }
    close(s);
}

static void record(pam_handle_t *pamh, const struct opts *o, int priority, const char *fmt, ...) __attribute__((format(printf, 4, 5)));

static void record(pam_handle_t *pamh, const struct opts *o, int priority, const char *fmt, ...)
{
    char text[480];
    va_list ap;
    char *p;

    va_start(ap, fmt);
    vsnprintf(text, sizeof text, fmt, ap);
    va_end(ap);
    for (p = text; *p; p++) {
        if ((unsigned char)*p < 32 || (unsigned char)*p == 127 || (unsigned char)*p >= 248) *p = '?';
    }
    send_audit(o, text);
    pam_syslog(pamh, priority, "%s", text);
}

/* The user, which must be sdsys, and the source.  0 for sdsys; -1 for another user or none.  S.101: on a line marked `local` (a console or desktop service) a login
   with no remote host is the source local:<service>:<tty>, so that a console's attempts are counted apart from every address and from each other. */
static int who(pam_handle_t *pamh, int local, char *src)
{
    const char *user = NULL;
    const void *rhost = NULL;
    const void *svc = NULL;
    const void *tty = NULL;
    const char *t;
    char raw[SD_TOTPS_SRC_LEN];

    if (pam_get_user(pamh, &user, NULL) != PAM_SUCCESS || user == NULL || strcmp(user, SD_USER) != 0) return -1;
    if (pam_get_item(pamh, PAM_RHOST, &rhost) != PAM_SUCCESS) rhost = NULL;
    if (local && (rhost == NULL || ((const char *)rhost)[0] == '\0')) {
        if (pam_get_item(pamh, PAM_SERVICE, &svc) != PAM_SUCCESS || svc == NULL) svc = "unknown";
        if (pam_get_item(pamh, PAM_TTY, &tty) != PAM_SUCCESS || tty == NULL) tty = "none";
        t = (const char *)tty;
        if (strncmp(t, "/dev/", 5) == 0) t += 5;
        snprintf(raw, sizeof raw, "local:%s:%s", (const char *)svc, t);
        sd_totps_source(raw, src);
        return 0;
    }
    sd_totps_source((const char *)rhost, src);
    return 0;
}

/* Every refusal ends here: the record, the wait, PAM_AUTH_ERR. */
static int refuse(pam_handle_t *pamh, const struct opts *o, int slow, const char *src, const char *reason)
{
    unsigned long usec = (unsigned long)o->delay_ms * 1000UL;

    record(pamh, o, LOG_NOTICE, "%s sdsys login code refused source=%s reason=%s%s", o->local ? "local" : "remote", src, reason, slow ? " slow=yes" : "");
    if (slow && usec != 0 && usec < DELAY_SLOW) usec = DELAY_SLOW;
    if (usec != 0) (void)pam_fail_delay(pamh, (unsigned int)usec);
    return PAM_AUTH_ERR;
}

SD_EXPORT PAM_EXTERN int pam_sm_authenticate(pam_handle_t *pamh, int flags, int argc, const char **argv)
{
    struct opts o;
    struct sd_totps_info info;
    char src[SD_TOTPS_SRC_LEN];
    char *resp = NULL;
    uint64_t now;
    int slow = 0;
    int r;

    (void)flags;
    parse_args(pamh, argc, argv, &o);
    if (who(pamh, o.local, src) != 0) return PAM_IGNORE;
    now = (uint64_t)time(NULL);

    r = sd_totps_info(o.dir, &info);
    if (r != SD_TOTPS_OK) return refuse(pamh, &o, 0, src, "store unsafe");
    if (!info.has_active) {
        if (o.local) return PAM_IGNORE;             /* S.101: no code enrolled, nothing to ask at the console (a restore with no store must not lock it) */
        return refuse(pamh, &o, 0, src, "not enrolled");
    }
    if (o.local && !sd_totps_scope_all(o.dir)) return PAM_IGNORE;      /* S.101: the console's code is opt-in (owner, 2 Nov 26): asked only after the administrator's `local on` */

    r = sd_totps_attempt_lock(o.dir, now, src, &slow, o.local ? SD_TOTPS_LOCK_LOCAL_SECS : SD_TOTPS_LOCK_SECS);
    if (r == SD_TOTPS_LOCKED) return refuse(pamh, &o, slow, src, "locked");
    if (r == SD_TOTPS_UNSAFE) return refuse(pamh, &o, slow, src, "store unsafe");
    if (r != SD_TOTPS_OK) return refuse(pamh, &o, slow, src, "store error");

    if (pam_prompt(pamh, PAM_PROMPT_ECHO_OFF, &resp, PROMPT) != PAM_SUCCESS || resp == NULL) {
        return refuse(pamh, &o, slow, src, "no answer");
    }
    r = sd_totps_check_window(o.dir, now, resp, o.window);
    OPENSSL_cleanse(resp, strlen(resp));
    free(resp);

    if (r == SD_TOTPS_OK || r == SD_TOTPS_USED) {
        (void)sd_totps_ok(o.dir, now, src);
        record(pamh, &o, r == SD_TOTPS_USED ? LOG_ALERT : LOG_NOTICE, r == SD_TOTPS_USED ? "%s sdsys login recovery code used source=%s" : "%s sdsys login code accepted source=%s",
               o.local ? "local" : "remote", src);
        return PAM_SUCCESS;
    }
    switch (r) {
        case SD_TOTPS_WRONG:   return refuse(pamh, &o, slow, src, "wrong code");
        case SD_TOTPS_REPLAY:  return refuse(pamh, &o, slow, src, "used code");
        case SD_TOTPS_BAD:     return refuse(pamh, &o, slow, src, "bad code");
        case SD_TOTPS_NOTHING: return refuse(pamh, &o, slow, src, "not enrolled");
        case SD_TOTPS_UNSAFE:  return refuse(pamh, &o, slow, src, "store unsafe");
        default:               return refuse(pamh, &o, slow, src, "store error");
    }
}

/* Called by sshd once the whole login has succeeded: only then are the source's failures forgotten. */
SD_EXPORT PAM_EXTERN int pam_sm_setcred(pam_handle_t *pamh, int flags, int argc, const char **argv)
{
    struct opts o;
    char src[SD_TOTPS_SRC_LEN];

    if (!(flags & PAM_ESTABLISH_CRED)) return PAM_SUCCESS;
    parse_args(pamh, argc, argv, &o);
    if (who(pamh, o.local, src) != 0) return PAM_IGNORE;
    if (sd_totps_clear(o.dir, (uint64_t)time(NULL), src) == SD_TOTPS_OK) {
        record(pamh, &o, LOG_NOTICE, "%s sdsys login succeeded source=%s", o.local ? "local" : "remote", src);
    }
    return PAM_SUCCESS;
}

/* ---- S.101 (2 Nov 26): THE LOGIN MARKER.  The session stage, on a session line placed AFTER pam_loginuid (only then do the loginuid and the kernel's session
   id exist), takes the grant a right code left (sd_totps_take_grant: single use, at most SD_TOTPS_OK_SECS old) and only then writes
   <marks>/<boot_id>.<sessionid>, which SD's doors (cproc's grant, sd-elevate) will ask for (stage B).  It never refuses the session: with no grant it writes
   nothing and answers PAM_IGNORE, and SD refuses the administrator at its own door - so a service nobody put the line into fails CLOSED at SD.
   The directory is the module runner's own (root in use) and not writable by group or others; nothing is followed through a link. ---- */

static int read_small(const char *path, char *out, size_t sz)
{
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    ssize_t n;

    if (fd < 0) return -1;
    n = read(fd, out, sz - 1);
    close(fd);
    if (n <= 0) return -1;
    out[n] = '\0';
    while (n > 0 && (out[n - 1] == '\n' || out[n - 1] == ' ')) out[--n] = '\0';
    return 0;
}

/* The marker's name, <boot_id>.<sessionid>, and the login's uid.  -1 when there is no session (sessionid unset: pam_loginuid is not above this line). */
static int marker_name(char *name, size_t sz, char *luid, size_t luidsz)
{
    char boot[64];
    char sid[32];
    char *p;

    if (read_small("/proc/sys/kernel/random/boot_id", boot, sizeof boot) != 0) return -1;
    if (read_small("/proc/self/sessionid", sid, sizeof sid) != 0 || strcmp(sid, "4294967295") == 0) return -1;
    if (read_small("/proc/self/loginuid", luid, luidsz) != 0 || strcmp(luid, "4294967295") == 0) return -1;
    for (p = boot; *p; p++) {
        if (!((*p >= '0' && *p <= '9') || (*p >= 'a' && *p <= 'f') || *p == '-')) return -1;
    }
    for (p = sid; *p; p++) {
        if (*p < '0' || *p > '9') return -1;
    }
    if ((size_t)snprintf(name, sz, "%s.%s", boot, sid) >= sz) return -1;
    return 0;
}

/* The marker directory, opened without following a link and checked: a directory, ours, not writable by group or others.  Made (0755) when absent, with
   its parent.  -1 when it is not as it must be. */
static int open_marks(const char *dir)
{
    char parent[256];
    char *slash;
    struct stat st;
    int fd;

    if (strlen(dir) >= sizeof parent || dir[0] != '/') return -1;
    snprintf(parent, sizeof parent, "%s", dir);
    slash = strrchr(parent, '/');
    if (slash != NULL && slash != parent) {
        *slash = '\0';
        (void)mkdir(parent, 0755);
    }
    (void)mkdir(dir, 0755);
    fd = open(dir, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0) return -1;
    if (fstat(fd, &st) != 0 || !S_ISDIR(st.st_mode) || st.st_uid != geteuid() || (st.st_mode & 022) != 0) {
        close(fd);
        return -1;
    }
    return fd;
}

SD_EXPORT PAM_EXTERN int pam_sm_open_session(pam_handle_t *pamh, int flags, int argc, const char **argv)
{
    struct opts o;
    char src[SD_TOTPS_SRC_LEN];
    char name[160];
    char luid[32];
    char text[256];
    const void *svc = NULL;
    const char *kind;
    int dfd;
    int fd;
    int len;
    int ok;

    (void)flags;
    parse_args(pamh, argc, argv, &o);
    if (who(pamh, o.local, src) != 0) return PAM_IGNORE;
    if (sd_totps_take_grant(o.dir, (uint64_t)time(NULL), src) != SD_TOTPS_OK) return PAM_IGNORE;     /* no right code for this login: no marker */
    if (pam_get_item(pamh, PAM_SERVICE, &svc) != PAM_SUCCESS || svc == NULL) svc = "unknown";
    kind = o.local ? "local" : "ssh";
    if (marker_name(name, sizeof name, luid, sizeof luid) != 0) {
        record(pamh, &o, LOG_WARNING, "%s sdsys login marker not written source=%s reason=no session (pam_loginuid must come before this line)", kind, src);
        return PAM_IGNORE;
    }
    dfd = open_marks(o.marks);
    if (dfd < 0) {
        record(pamh, &o, LOG_WARNING, "%s sdsys login marker not written source=%s reason=marker directory unsafe", kind, src);
        return PAM_IGNORE;
    }
    len = snprintf(text, sizeof text, "uid=%s service=%s kind=%s time=%lld\n", luid, (const char *)svc, kind, (long long)time(NULL));
    (void)unlinkat(dfd, name, 0);                   /* a stale one of this session (none should exist): replaced, never written through */
    fd = openat(dfd, name, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0644);
    ok = (fd >= 0 && len > 0 && len < (int)sizeof text && write(fd, text, (size_t)len) == len && fchmod(fd, 0644) == 0);
    if (fd >= 0) close(fd);
    close(dfd);
    record(pamh, &o, ok ? LOG_NOTICE : LOG_WARNING, "%s sdsys login marker %s source=%s", kind, ok ? "written" : "not written", src);
    return ok ? PAM_SUCCESS : PAM_IGNORE;
}

/* The session ends: its marker goes (a reboot clears /run anyway). */
SD_EXPORT PAM_EXTERN int pam_sm_close_session(pam_handle_t *pamh, int flags, int argc, const char **argv)
{
    struct opts o;
    char src[SD_TOTPS_SRC_LEN];
    char name[160];
    char luid[32];
    int dfd;

    (void)flags;
    parse_args(pamh, argc, argv, &o);
    if (who(pamh, o.local, src) != 0) return PAM_IGNORE;
    if (marker_name(name, sizeof name, luid, sizeof luid) != 0) return PAM_IGNORE;
    dfd = open_marks(o.marks);
    if (dfd < 0) return PAM_IGNORE;
    (void)unlinkat(dfd, name, 0);
    close(dfd);
    return PAM_SUCCESS;
}
