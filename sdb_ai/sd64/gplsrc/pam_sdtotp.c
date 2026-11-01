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

#define SD_EXPORT __attribute__((visibility("default")))

struct opts {
    const char *dir;
    const char *audit;
    unsigned delay_ms;
};

static void parse_args(pam_handle_t *pamh, int argc, const char **argv, struct opts *o)
{
    int i;
    char *end;
    unsigned long v;

    o->dir = SD_TOTPS_DIR_DEFAULT;
    o->audit = SD_AUDIT_SOCK;
    o->delay_ms = DELAY_DEFAULT;
    for (i = 0; i < argc; i++) {
        if (strncmp(argv[i], "dir=/", 5) == 0) {
            o->dir = argv[i] + 4;
        } else if (strncmp(argv[i], "audit=/", 7) == 0) {
            o->audit = argv[i] + 6;
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

/* The user, which must be sdsys, and the source address.  0 for sdsys; -1 for another user or none. */
static int who(pam_handle_t *pamh, char *src)
{
    const char *user = NULL;
    const void *rhost = NULL;

    if (pam_get_user(pamh, &user, NULL) != PAM_SUCCESS || user == NULL || strcmp(user, SD_USER) != 0) return -1;
    if (pam_get_item(pamh, PAM_RHOST, &rhost) != PAM_SUCCESS) rhost = NULL;
    sd_totps_source((const char *)rhost, src);
    return 0;
}

/* Every refusal ends here: the record, the wait, PAM_AUTH_ERR. */
static int refuse(pam_handle_t *pamh, const struct opts *o, int slow, const char *src, const char *reason)
{
    unsigned long usec = (unsigned long)o->delay_ms * 1000UL;

    record(pamh, o, LOG_NOTICE, "remote sdsys login code refused source=%s reason=%s%s", src, reason, slow ? " slow=yes" : "");
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
    if (who(pamh, src) != 0) return PAM_IGNORE;
    parse_args(pamh, argc, argv, &o);
    now = (uint64_t)time(NULL);

    r = sd_totps_info(o.dir, &info);
    if (r != SD_TOTPS_OK) return refuse(pamh, &o, 0, src, "store unsafe");
    if (!info.has_active) return refuse(pamh, &o, 0, src, "not enrolled");

    r = sd_totps_attempt(o.dir, now, src, &slow);
    if (r == SD_TOTPS_LOCKED) return refuse(pamh, &o, slow, src, "locked");
    if (r == SD_TOTPS_UNSAFE) return refuse(pamh, &o, slow, src, "store unsafe");
    if (r != SD_TOTPS_OK) return refuse(pamh, &o, slow, src, "store error");

    if (pam_prompt(pamh, PAM_PROMPT_ECHO_OFF, &resp, PROMPT) != PAM_SUCCESS || resp == NULL) {
        return refuse(pamh, &o, slow, src, "no answer");
    }
    r = sd_totps_check(o.dir, now, resp);
    OPENSSL_cleanse(resp, strlen(resp));
    free(resp);

    if (r == SD_TOTPS_OK || r == SD_TOTPS_USED) {
        (void)sd_totps_ok(o.dir, now, src);
        record(pamh, &o, r == SD_TOTPS_USED ? LOG_ALERT : LOG_NOTICE, r == SD_TOTPS_USED ? "remote sdsys login recovery code used source=%s" : "remote sdsys login code accepted source=%s", src);
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
    if (who(pamh, src) != 0) return PAM_IGNORE;
    parse_args(pamh, argc, argv, &o);
    if (sd_totps_clear(o.dir, (uint64_t)time(NULL), src) == SD_TOTPS_OK) {
        record(pamh, &o, LOG_NOTICE, "remote sdsys login succeeded source=%s", src);
    }
    return PAM_SUCCESS;
}
