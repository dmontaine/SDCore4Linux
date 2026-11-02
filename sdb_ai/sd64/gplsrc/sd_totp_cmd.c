/* sd_totp_cmd.c
 * sd-totp - the command that sd-elevate's totp-* verbs and the installer run as root
 * to enrol, check, renew and switch off the second factor of the sdsys user.
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
 * 01 Nov 26 dm  S.95 stage 1 - written.  Checked by gplbld/test-totp-store.py.
 * 02 Nov 26 dm  S.101 stage D: the scope command.
 * END-HISTORY
 *
 * START-DESCRIPTION:
 *
 *   sd-totp status                  active=yes|no, pending=yes|no, recovery=N
 *   sd-totp begin ISSUER ACCOUNT    secret=<base32> and uri=<otpauth link>, once; a pending secret
 *   sd-totp confirm                 one code on standard input; ok, then recovery=<code> x 8, once
 *   sd-totp check                   one code or recovery code on standard input; ok [recovery]
 *   sd-totp recovery                recovery=<code> x 8, once; replaces the old set
 *   sd-totp scope [all|remote]      scope=all|remote; with a word, writes it first (S.101: all asks the
 *                                   code at the console too; remote, the delivered default, over ssh only)
 *   sd-totp off                     removes the secret, the recovery codes, any pending secret and the
 *                                   grants; the scope word stays
 *
 * EXIT STATUS.  0 done.  1 refused for the code or the state (refused=wrong|replay|discarded|
 * nothing|bad on standard output).  2 the store is not as it must be, an input or output
 * failure, or a usage error (a sentence on standard error).
 *
 * THE CODE IS READ FROM STANDARD INPUT, NEVER FROM AN ARGUMENT, so it does not appear in a
 * process list.  The store is /etc/sdcore/totp; the clock is time().  Both can be moved by
 * SD_TOTP_DIR and SD_TOTP_NOW for the check, and ONLY WHEN THE PROCESS IS NOT ROOT: a root run
 * reads neither, because root is what it is run as in production and what the environment
 * of a caller of sudo may not decide (the rule of sd-elevate's trust_fixtures).
 *
 * END-DESCRIPTION
 */

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#include "sd_totp.h"
#include "sd_totp_store.h"

#define PROG "sd-totp"

static int usage(void)
{
    fputs("usage: " PROG " status | begin ISSUER ACCOUNT | confirm | check | recovery | scope [all|remote] | off\n"
          "       (confirm and check read the code from standard input)\n", stderr);
    return 2;
}

/* One line from standard input, without its newline.  0, or -1 when there is none or it is too long. */
static int read_line(char *buf, size_t sz)
{
    size_t n;

    if (fgets(buf, (int)sz, stdin) == NULL) return -1;
    n = strlen(buf);
    if (n > 0 && buf[n - 1] == '\n') buf[--n] = '\0';
    else if (n + 1 >= sz) return -1;                        /* no newline and no room: a line that is too long */
    if (n > 0 && buf[n - 1] == '\r') buf[--n] = '\0';
    return 0;
}

static int refuse_word(const char *word)
{
    printf("refused=%s\n", word);
    return 1;
}

/* The exit status for a result that is not a success. */
static int failure(int rc)
{
    switch (rc) {
        case SD_TOTPS_WRONG:     return refuse_word("wrong");
        case SD_TOTPS_REPLAY:    return refuse_word("replay");
        case SD_TOTPS_DISCARDED: return refuse_word("discarded");
        case SD_TOTPS_NOTHING:   return refuse_word("nothing");
        case SD_TOTPS_BAD:       return refuse_word("bad");
        case SD_TOTPS_UNSAFE:
            fputs(PROG ": the store is not as it must be (its owner, its mode, a link, or what it holds); nothing was done\n", stderr);
            return 2;
        default:
            fputs(PROG ": the store could not be read or written, or the random generator failed; nothing was done\n", stderr);
            return 2;
    }
}

static void print_codes(char rc[][SD_TOTPS_RC_TEXT + 1])
{
    int i;

    for (i = 0; i < SD_TOTPS_RC_COUNT; i++) printf("recovery=%s\n", rc[i]);
}

int main(int argc, char **argv)
{
    const char *dir = SD_TOTPS_DIR_DEFAULT;
    uint64_t now = (uint64_t)time(NULL);
    char rc[SD_TOTPS_RC_COUNT][SD_TOTPS_RC_TEXT + 1];
    char line[64];
    int r;

    if (argc < 2) return usage();
    if (geteuid() != 0) {                                    /* the test's knobs: never from a root run */
        const char *e;

        if ((e = getenv("SD_TOTP_DIR")) != NULL && *e != '\0') dir = e;
        if ((e = getenv("SD_TOTP_NOW")) != NULL && *e != '\0') now = strtoull(e, NULL, 10);
    }

    if (strcmp(argv[1], "status") == 0 && argc == 2) {
        struct sd_totps_info info;

        r = sd_totps_info(dir, &info);
        if (r != SD_TOTPS_OK) return failure(r);
        printf("active=%s\npending=%s\nrecovery=%d\n", info.has_active ? "yes" : "no", info.has_pending ? "yes" : "no", info.recovery_left);
        return 0;
    }
    if (strcmp(argv[1], "begin") == 0 && argc == 4) {
        char b32[SD_TOTP_B32_LEN + 1];
        char uri[SD_TOTPS_URI_MAX];

        r = sd_totps_begin(dir, argv[2], argv[3], b32, sizeof b32, uri, sizeof uri);
        if (r != SD_TOTPS_OK) return failure(r);
        printf("secret=%s\nuri=%s\n", b32, uri);
        return 0;
    }
    if (strcmp(argv[1], "confirm") == 0 && argc == 2) {
        if (read_line(line, sizeof line) != 0) return failure(SD_TOTPS_BAD);
        r = sd_totps_confirm(dir, now, line, rc);
        memset(line, 0, sizeof line);
        if (r != SD_TOTPS_OK) return failure(r);
        printf("ok\n");
        print_codes(rc);
        return 0;
    }
    if (strcmp(argv[1], "check") == 0 && argc == 2) {
        if (read_line(line, sizeof line) != 0) return failure(SD_TOTPS_BAD);
        r = sd_totps_check(dir, now, line);
        memset(line, 0, sizeof line);
        if (r == SD_TOTPS_OK) {
            printf("ok\n");
            return 0;
        }
        if (r == SD_TOTPS_USED) {
            printf("ok recovery\n");
            return 0;
        }
        return failure(r);
    }
    if (strcmp(argv[1], "recovery") == 0 && argc == 2) {
        r = sd_totps_recovery(dir, rc);
        if (r != SD_TOTPS_OK) return failure(r);
        print_codes(rc);
        return 0;
    }
    /* S.101 stage D: the scope word.  With no word it is read (a store that cannot be read reads as all: fail closed); "all" or "remote" writes it. */
    if (strcmp(argv[1], "scope") == 0 && (argc == 2 || argc == 3)) {
        if (argc == 3) {
            if (strcmp(argv[2], "all") != 0 && strcmp(argv[2], "remote") != 0) return usage();
            r = sd_totps_set_scope(dir, strcmp(argv[2], "all") == 0);
            if (r != SD_TOTPS_OK) return failure(r);
        }
        printf("scope=%s\n", sd_totps_scope_all(dir) ? "all" : "remote");
        return 0;
    }
    if (strcmp(argv[1], "off") == 0 && argc == 2) {
        r = sd_totps_off(dir);
        if (r != SD_TOTPS_OK) return failure(r);
        printf("off\n");
        return 0;
    }
    return usage();
}
