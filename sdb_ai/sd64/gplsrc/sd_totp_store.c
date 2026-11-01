/* sd_totp_store.c
 * The root-only store of the sdsys user's TOTP secret, its recovery codes and the
 * code last used, for the remote SDSYS login (S.95).
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
 * 01 Nov 26 dm  S.95 stage 1 - written.  See sd_totp_store.h for what the
 *               functions promise and gplbld/test-totp-store.py for the check.
 * END-HISTORY
 *
 * START-DESCRIPTION:
 *
 * Four things here are on purpose and each is held by the check.
 *
 * NOTHING IS TRUSTED UNTIL IT HAS BEEN LOOKED AT.  The directory is opened
 * without following a link and its descriptor asked who owns it and who can
 * enter it; each file is opened relative to that descriptor, again without
 * following a link, and the OPEN file is asked (fstat, not stat: the name could
 * have been swapped) its owner, its mode, its link count and its size.  The
 * owner must be the user the process runs as.  A file that is not what it
 * should be is SD_TOTPS_UNSAFE, and an unsafe store is never an accepted code.
 *
 * A FILE IS REPLACED, NEVER EDITED IN PLACE.  The new text goes to a file of
 * its own name in the same directory (created exclusively, mode 0600), is
 * written out to the disk, and takes the old file's place with one rename.  A
 * crash leaves the old file or the new one.
 *
 * THE LOCK IS THE DIRECTORY'S.  Every call takes an exclusive flock on the
 * directory's descriptor before it reads anything and keeps it until it
 * returns, so a code cannot be accepted twice by two callers at once.
 *
 * SECRETS ARE WIPED.  The raw secret, the text that held it and the file's text
 * are cleansed (OPENSSL_cleanse, which the compiler may not remove) when the
 * function is done with them.
 *
 * END-DESCRIPTION
 */

#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#include <openssl/crypto.h>
#include <openssl/rand.h>
#include <openssl/sha.h>

#include "sd_totp.h"
#include "sd_totp_store.h"

#define FILE_MAX        4096
#define MAGIC           "sdtotp 1"
#define NAME_ACTIVE     "sdsys.active"
#define NAME_PENDING    "sdsys.pending"
#define NAME_RECOVERY   "sdsys.recovery"
#define NAME_FAIL       "sdsys.fail"
#define FAIL_FILE_MAX   16384
#define SALT_BYTES      16
#define HEX_SALT        (2 * SALT_BYTES)
#define HEX_HASH        (2 * SHA256_DIGEST_LENGTH)
#define RC_CHARS        10              /* characters of a recovery code, without the hyphen */
#define LOAD_ABSENT     1               /* load_*: the file is not there */

/* open_dir: results that are not a descriptor */
#define DIR_ABSENT      (-1)
#define DIR_UNSAFE      (-2)
#define DIR_ERROR       (-3)

static const char B32[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";

struct active  { char b32[SD_TOTP_B32_LEN + 1]; int64_t last; };
struct pending { char b32[SD_TOTP_B32_LEN + 1]; int tries; };
struct recov   { char salt[HEX_SALT + 1]; char hash[SD_TOTPS_RC_COUNT][HEX_HASH + 1]; int n; };


/* ------------------------------------------------------------------ the directory and the files */

/* The directory, opened, checked and locked; or one of the DIR_ results. */
static int open_dir(const char *dir, int create)
{
    struct stat st;
    int fd;

    if (dir == NULL || dir[0] == '\0') return DIR_ERROR;
    fd = open(dir, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0 && errno == ENOENT && create) {
        if (mkdir(dir, 0700) != 0 && errno != EEXIST) return DIR_ERROR;
        fd = open(dir, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    }
    if (fd < 0) {
        if (errno == ENOENT) return DIR_ABSENT;
        if (errno == ELOOP || errno == ENOTDIR) return DIR_UNSAFE;
        return DIR_ERROR;
    }
    if (fstat(fd, &st) != 0 || !S_ISDIR(st.st_mode) || st.st_uid != geteuid() || (st.st_mode & 077) != 0) {
        close(fd);
        return DIR_UNSAFE;
    }
    if (flock(fd, LOCK_EX) != 0) {
        close(fd);
        return DIR_ERROR;
    }
    return fd;
}

static int dir_result(int dfd)
{
    return dfd == DIR_UNSAFE ? SD_TOTPS_UNSAFE : SD_TOTPS_ERROR;
}

/* 0 read; LOAD_ABSENT; SD_TOTPS_UNSAFE; SD_TOTPS_ERROR.  The text is NUL-terminated and holds no NUL. */
static int read_file(int dfd, const char *name, char *buf, size_t sz)
{
    struct stat st;
    size_t got = 0;
    ssize_t n;
    int fd = openat(dfd, name, O_RDONLY | O_NOFOLLOW | O_CLOEXEC);

    if (fd < 0) {
        if (errno == ENOENT) return LOAD_ABSENT;
        return errno == ELOOP ? SD_TOTPS_UNSAFE : SD_TOTPS_ERROR;
    }
    if (fstat(fd, &st) != 0 || !S_ISREG(st.st_mode) || st.st_uid != geteuid() || (st.st_mode & 077) != 0
        || st.st_nlink != 1 || st.st_size < 0 || (size_t)st.st_size >= sz) {
        close(fd);
        return SD_TOTPS_UNSAFE;
    }
    while (got < (size_t)st.st_size) {
        n = read(fd, buf + got, (size_t)st.st_size - got);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) {
            close(fd);
            return SD_TOTPS_ERROR;
        }
        got += (size_t)n;
    }
    close(fd);
    buf[got] = '\0';
    return memchr(buf, '\0', got) != NULL ? SD_TOTPS_UNSAFE : 0;
}

/* Replace NAME with TEXT: a new file of its own, mode 0600, written out, then one rename. */
static int write_file(int dfd, const char *name, const char *text)
{
    char tmp[64];
    size_t len = strlen(text);
    size_t done = 0;
    ssize_t n;
    int fd;

    snprintf(tmp, sizeof tmp, ".new-%s", name);
    if (unlinkat(dfd, tmp, 0) != 0 && errno != ENOENT) return SD_TOTPS_ERROR;
    fd = openat(dfd, tmp, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600);
    if (fd < 0) return SD_TOTPS_ERROR;
    if (fchmod(fd, 0600) != 0) goto fail;
    while (done < len) {
        n = write(fd, text + done, len - done);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) goto fail;
        done += (size_t)n;
    }
    if (fsync(fd) != 0) goto fail;
    if (close(fd) != 0) {
        unlinkat(dfd, tmp, 0);
        return SD_TOTPS_ERROR;
    }
    if (renameat(dfd, tmp, dfd, name) != 0) {
        unlinkat(dfd, tmp, 0);
        return SD_TOTPS_ERROR;
    }
    (void)fsync(dfd);
    return 0;
fail:
    close(fd);
    unlinkat(dfd, tmp, 0);
    return SD_TOTPS_ERROR;
}


/* ------------------------------------------------------------------ the text of the files */

static char *next_line(char **cur)
{
    char *p = *cur;
    char *e;

    if (p == NULL || *p == '\0') return NULL;
    e = strchr(p, '\n');
    if (e != NULL) {
        *e = '\0';
        *cur = e + 1;
    } else {
        *cur = p + strlen(p);
    }
    return p;
}

static int b32_ok(const char *s, size_t n)
{
    size_t i;

    if (strlen(s) != n) return 0;
    for (i = 0; i < n; i++) {
        if (strchr(B32, s[i]) == NULL) return 0;
    }
    return 1;
}

static int hex_ok(const char *s, size_t n)
{
    size_t i;

    if (strlen(s) != n) return 0;
    for (i = 0; i < n; i++) {
        if (!((s[i] >= '0' && s[i] <= '9') || (s[i] >= 'a' && s[i] <= 'f'))) return 0;
    }
    return 1;
}

static void to_hex(const unsigned char *in, size_t n, char *out)
{
    static const char hex[] = "0123456789abcdef";
    size_t i;

    for (i = 0; i < n; i++) {
        out[2 * i] = hex[in[i] >> 4];
        out[2 * i + 1] = hex[in[i] & 15];
    }
    out[2 * n] = '\0';
}

static void from_hex(const char *s, unsigned char *out, size_t n)
{
    size_t i;
    int h, l;

    for (i = 0; i < n; i++) {
        h = (s[2 * i] <= '9') ? s[2 * i] - '0' : s[2 * i] - 'a' + 10;
        l = (s[2 * i + 1] <= '9') ? s[2 * i + 1] - '0' : s[2 * i + 1] - 'a' + 10;
        out[i] = (unsigned char)(h * 16 + l);
    }
}

/* A decimal number, optionally negative, nothing else, inside LO..HI. */
static int parse_int(const char *s, int64_t lo, int64_t hi, int64_t *out)
{
    const char *p = s;
    char *end;
    long long v;

    if (*p == '-') p++;
    if (*p == '\0' || strlen(s) > 19) return 0;
    for (; *p; p++) {
        if (*p < '0' || *p > '9') return 0;
    }
    errno = 0;
    v = strtoll(s, &end, 10);
    if (errno != 0 || *end != '\0' || v < lo || v > hi) return 0;
    *out = (int64_t)v;
    return 1;
}

static int parse_active(char *text, struct active *a)
{
    char *cur = text;
    char *ln = next_line(&cur);
    int got_secret = 0;
    int got_last = 0;

    if (ln == NULL || strcmp(ln, MAGIC) != 0) return SD_TOTPS_UNSAFE;
    while ((ln = next_line(&cur)) != NULL) {
        if (strncmp(ln, "secret ", 7) == 0 && !got_secret && b32_ok(ln + 7, SD_TOTP_B32_LEN)) {
            memcpy(a->b32, ln + 7, SD_TOTP_B32_LEN + 1);
            got_secret = 1;
        } else if (strncmp(ln, "last ", 5) == 0 && !got_last && parse_int(ln + 5, -1, INT64_MAX, &a->last)) {
            got_last = 1;
        } else {
            return SD_TOTPS_UNSAFE;
        }
    }
    return got_secret && got_last ? 0 : SD_TOTPS_UNSAFE;
}

static int parse_pending(char *text, struct pending *p)
{
    char *cur = text;
    char *ln = next_line(&cur);
    int got_secret = 0;
    int got_tries = 0;
    int64_t t = 0;

    if (ln == NULL || strcmp(ln, MAGIC) != 0) return SD_TOTPS_UNSAFE;
    while ((ln = next_line(&cur)) != NULL) {
        if (strncmp(ln, "secret ", 7) == 0 && !got_secret && b32_ok(ln + 7, SD_TOTP_B32_LEN)) {
            memcpy(p->b32, ln + 7, SD_TOTP_B32_LEN + 1);
            got_secret = 1;
        } else if (strncmp(ln, "tries ", 6) == 0 && !got_tries && parse_int(ln + 6, 0, SD_TOTPS_TRIES, &t)) {
            p->tries = (int)t;
            got_tries = 1;
        } else {
            return SD_TOTPS_UNSAFE;
        }
    }
    return got_secret && got_tries ? 0 : SD_TOTPS_UNSAFE;
}

static int parse_recovery(char *text, struct recov *r)
{
    char *cur = text;
    char *ln = next_line(&cur);
    int got_salt = 0;

    if (ln == NULL || strcmp(ln, MAGIC) != 0) return SD_TOTPS_UNSAFE;
    r->n = 0;
    while ((ln = next_line(&cur)) != NULL) {
        if (strncmp(ln, "salt ", 5) == 0 && !got_salt && hex_ok(ln + 5, HEX_SALT)) {
            memcpy(r->salt, ln + 5, HEX_SALT + 1);
            got_salt = 1;
        } else if (strncmp(ln, "code ", 5) == 0 && r->n < SD_TOTPS_RC_COUNT && hex_ok(ln + 5, HEX_HASH)) {
            memcpy(r->hash[r->n++], ln + 5, HEX_HASH + 1);
        } else {
            return SD_TOTPS_UNSAFE;
        }
    }
    return got_salt ? 0 : SD_TOTPS_UNSAFE;
}

/* 0 present and well formed; LOAD_ABSENT; SD_TOTPS_UNSAFE; SD_TOTPS_ERROR */
static int load_active(int dfd, struct active *a)
{
    char buf[FILE_MAX];
    int rc = read_file(dfd, NAME_ACTIVE, buf, sizeof buf);

    if (rc == 0) rc = parse_active(buf, a);
    OPENSSL_cleanse(buf, sizeof buf);
    return rc;
}

static int load_pending(int dfd, struct pending *p)
{
    char buf[FILE_MAX];
    int rc = read_file(dfd, NAME_PENDING, buf, sizeof buf);

    if (rc == 0) rc = parse_pending(buf, p);
    OPENSSL_cleanse(buf, sizeof buf);
    return rc;
}

static int load_recovery(int dfd, struct recov *r)
{
    char buf[FILE_MAX];
    int rc = read_file(dfd, NAME_RECOVERY, buf, sizeof buf);

    if (rc == 0) rc = parse_recovery(buf, r);
    OPENSSL_cleanse(buf, sizeof buf);
    return rc;
}

static int store_active(int dfd, const char *b32, int64_t last)
{
    char text[FILE_MAX];
    int rc;

    snprintf(text, sizeof text, MAGIC "\nsecret %s\nlast %" PRId64 "\n", b32, last);
    rc = write_file(dfd, NAME_ACTIVE, text);
    OPENSSL_cleanse(text, sizeof text);
    return rc;
}

static int store_pending(int dfd, const char *b32, int tries)
{
    char text[FILE_MAX];
    int rc;

    snprintf(text, sizeof text, MAGIC "\nsecret %s\ntries %d\n", b32, tries);
    rc = write_file(dfd, NAME_PENDING, text);
    OPENSSL_cleanse(text, sizeof text);
    return rc;
}

static int store_recovery(int dfd, const struct recov *r)
{
    char text[FILE_MAX];
    size_t len;
    int i;

    len = (size_t)snprintf(text, sizeof text, MAGIC "\nsalt %s\n", r->salt);
    for (i = 0; i < r->n; i++) {
        len += (size_t)snprintf(text + len, sizeof text - len, "code %s\n", r->hash[i]);
    }
    return write_file(dfd, NAME_RECOVERY, text);
}


/* ------------------------------------------------------------------ recovery codes */

/* SHA-256 of the salt's 16 bytes followed by the ten characters, as lower-case hex. */
static void rc_hash(const char *salthex, const char *code, char *out)
{
    unsigned char msg[SALT_BYTES + RC_CHARS];
    unsigned char md[SHA256_DIGEST_LENGTH];

    from_hex(salthex, msg, SALT_BYTES);
    memcpy(msg + SALT_BYTES, code, RC_CHARS);
    SHA256(msg, sizeof msg, md);
    to_hex(md, sizeof md, out);
}

/* A new salt and SD_TOTPS_RC_COUNT new codes: their hashes in R, the codes for the person in RC. */
static int make_recovery_set(struct recov *r, char rc[][SD_TOTPS_RC_TEXT + 1])
{
    unsigned char salt[SALT_BYTES];
    unsigned char rnd[7];
    char b[16];
    char code[RC_CHARS + 1];
    int i;

    if (RAND_bytes(salt, sizeof salt) != 1) return SD_TOTPS_ERROR;
    to_hex(salt, sizeof salt, r->salt);
    for (i = 0; i < SD_TOTPS_RC_COUNT; i++) {
        if (RAND_bytes(rnd, sizeof rnd) != 1 || sd_totp_b32_encode(rnd, sizeof rnd, b, sizeof b) < RC_CHARS) {
            OPENSSL_cleanse(rnd, sizeof rnd);
            return SD_TOTPS_ERROR;
        }
        memcpy(code, b, RC_CHARS);
        code[RC_CHARS] = '\0';
        rc_hash(r->salt, code, r->hash[i]);
        snprintf(rc[i], SD_TOTPS_RC_TEXT + 1, "%.5s-%.5s", code, code + 5);
        OPENSSL_cleanse(code, sizeof code);
        OPENSSL_cleanse(b, sizeof b);
    }
    OPENSSL_cleanse(rnd, sizeof rnd);
    r->n = SD_TOTPS_RC_COUNT;
    return 0;
}

static void wipe_codes(char rc[][SD_TOTPS_RC_TEXT + 1])
{
    OPENSSL_cleanse(rc, (size_t)SD_TOTPS_RC_COUNT * (SD_TOTPS_RC_TEXT + 1));
}


/* ------------------------------------------------------------------ what a person typed */

/* Spaces and hyphens dropped, letters upper-cased.  The length, or -1 for text that is too long. */
static int normalise(const char *given, char *out, size_t outsz)
{
    size_t n = 0;
    char c;

    if (given == NULL) return -1;
    for (; *given; given++) {
        c = *given;
        if (c == ' ' || c == '-') continue;
        if (c >= 'a' && c <= 'z') c = (char)(c - 'a' + 'A');
        if (n + 1 >= outsz) return -1;
        out[n++] = c;
    }
    out[n] = '\0';
    return (int)n;
}

static int all_digits(const char *s)
{
    for (; *s; s++) {
        if (*s < '0' || *s > '9') return 0;
    }
    return 1;
}

static int printable_text(const char *s)
{
    size_t n;
    size_t i;

    if (s == NULL) return 0;
    n = strlen(s);
    if (n < 1 || n > 64) return 0;
    for (i = 0; i < n; i++) {
        if ((unsigned char)s[i] < 0x20 || (unsigned char)s[i] > 0x7e) return 0;
    }
    return 1;
}


/* ------------------------------------------------------------------ the calls */

int sd_totps_info(const char *dir, struct sd_totps_info *out)
{
    struct active a;
    struct pending p;
    struct recov r;
    int dfd;
    int rc;

    memset(out, 0, sizeof *out);
    out->last_step = -1;
    dfd = open_dir(dir, 0);
    if (dfd == DIR_ABSENT) return SD_TOTPS_OK;
    if (dfd < 0) return dir_result(dfd);

    rc = load_active(dfd, &a);
    if (rc == 0) {
        out->has_active = 1;
        out->last_step = a.last;
    }
    if (rc == 0 || rc == LOAD_ABSENT) {
        rc = load_pending(dfd, &p);
        if (rc == 0) out->has_pending = 1;
    }
    if (rc == 0 || rc == LOAD_ABSENT) {
        rc = load_recovery(dfd, &r);
        if (rc == 0) out->recovery_left = r.n;
    }
    close(dfd);
    OPENSSL_cleanse(&a, sizeof a);
    OPENSSL_cleanse(&p, sizeof p);
    if (rc == 0 || rc == LOAD_ABSENT) return SD_TOTPS_OK;
    memset(out, 0, sizeof *out);
    out->last_step = -1;
    return rc;
}

int sd_totps_begin(const char *dir, const char *issuer, const char *account,
                   char *b32, size_t b32sz, char *uri, size_t urisz)
{
    unsigned char secret[SD_TOTP_SECRET_LEN];
    char text[SD_TOTP_B32_LEN + 1];
    int dfd;
    int rc;

    if (!printable_text(issuer) || !printable_text(account) || b32 == NULL || b32sz < sizeof text || uri == NULL || urisz == 0) {
        return SD_TOTPS_BAD;
    }
    b32[0] = '\0';
    uri[0] = '\0';
    if (sd_totp_new_secret(secret, sizeof secret) != 0) return SD_TOTPS_ERROR;
    if (sd_totp_b32_encode(secret, sizeof secret, text, sizeof text) != SD_TOTP_B32_LEN) {
        OPENSSL_cleanse(secret, sizeof secret);
        return SD_TOTPS_ERROR;
    }
    OPENSSL_cleanse(secret, sizeof secret);
    if (sd_totp_uri(uri, urisz, issuer, account, text) < 0) {
        OPENSSL_cleanse(text, sizeof text);
        return SD_TOTPS_BAD;
    }
    dfd = open_dir(dir, 1);
    if (dfd < 0) {
        uri[0] = '\0';
        OPENSSL_cleanse(text, sizeof text);
        return dir_result(dfd);
    }
    rc = store_pending(dfd, text, 0);
    close(dfd);
    if (rc == 0) {
        memcpy(b32, text, sizeof text);
    } else {
        uri[0] = '\0';
    }
    OPENSSL_cleanse(text, sizeof text);
    return rc;
}

int sd_totps_confirm(const char *dir, uint64_t now, const char *code, char rc_out[][SD_TOTPS_RC_TEXT + 1])
{
    struct pending p;
    struct recov r;
    unsigned char key[SD_TOTP_SECRET_LEN];
    char norm[16];
    int64_t step;
    int dfd;
    int rc;

    wipe_codes(rc_out);
    if (normalise(code, norm, sizeof norm) != SD_TOTP_DIGITS || !all_digits(norm)) return SD_TOTPS_BAD;
    dfd = open_dir(dir, 0);
    if (dfd == DIR_ABSENT) return SD_TOTPS_NOTHING;
    if (dfd < 0) return dir_result(dfd);

    rc = load_pending(dfd, &p);
    if (rc == LOAD_ABSENT) rc = SD_TOTPS_NOTHING;
    if (rc != 0) goto done;
    if (sd_totp_b32_decode(p.b32, key, sizeof key) != SD_TOTP_SECRET_LEN) {
        rc = SD_TOTPS_UNSAFE;
        goto done;
    }
    step = sd_totp_check(key, sizeof key, now, norm, -1);
    if (step == SD_TOTP_BAD) {
        rc = SD_TOTPS_ERROR;
        goto done;
    }
    if (step < 0) {                                         /* wrong: count it, and throw the secret away at the fifth */
        p.tries++;
        if (p.tries >= SD_TOTPS_TRIES) {
            rc = unlinkat(dfd, NAME_PENDING, 0) == 0 ? SD_TOTPS_DISCARDED : SD_TOTPS_ERROR;
        } else {
            rc = store_pending(dfd, p.b32, p.tries);
            if (rc == 0) rc = SD_TOTPS_WRONG;
        }
        goto done;
    }
    rc = make_recovery_set(&r, rc_out);                     /* the codes go to the person only if everything below was written */
    if (rc == 0) rc = store_recovery(dfd, &r);
    if (rc == 0) rc = store_active(dfd, p.b32, step);
    if (rc == 0 && unlinkat(dfd, NAME_PENDING, 0) != 0 && errno != ENOENT) rc = SD_TOTPS_ERROR;
done:
    if (rc != 0) wipe_codes(rc_out);
    close(dfd);
    OPENSSL_cleanse(key, sizeof key);
    OPENSSL_cleanse(&p, sizeof p);
    return rc;
}

int sd_totps_check(const char *dir, uint64_t now, const char *given)
{
    struct active a;
    struct recov r;
    unsigned char key[SD_TOTP_SECRET_LEN];
    char norm[16];
    char want[HEX_HASH + 1];
    int64_t step;
    int n;
    int dfd;
    int rc;
    int i;
    int hit = -1;

    n = normalise(given, norm, sizeof norm);
    if (n < 0) return SD_TOTPS_BAD;
    if (!((n == SD_TOTP_DIGITS && all_digits(norm)) || (n == RC_CHARS && b32_ok(norm, RC_CHARS)))) return SD_TOTPS_BAD;
    dfd = open_dir(dir, 0);
    if (dfd == DIR_ABSENT) return SD_TOTPS_NOTHING;
    if (dfd < 0) return dir_result(dfd);

    rc = load_active(dfd, &a);
    if (rc == LOAD_ABSENT) rc = SD_TOTPS_NOTHING;
    if (rc != 0) goto done;
    if (n == SD_TOTP_DIGITS) {
        if (sd_totp_b32_decode(a.b32, key, sizeof key) != SD_TOTP_SECRET_LEN) {
            rc = SD_TOTPS_UNSAFE;
            goto done;
        }
        step = sd_totp_check(key, sizeof key, now, norm, a.last);
        if (step >= 0) rc = store_active(dfd, a.b32, step);
        else if (step == SD_TOTP_REPLAY) rc = SD_TOTPS_REPLAY;
        else if (step == SD_TOTP_NOMATCH) rc = SD_TOTPS_WRONG;
        else rc = SD_TOTPS_ERROR;
        goto done;
    }
    rc = load_recovery(dfd, &r);                            /* a recovery code */
    if (rc == LOAD_ABSENT) {
        rc = SD_TOTPS_WRONG;
        goto done;
    }
    if (rc != 0) goto done;
    rc_hash(r.salt, norm, want);
    for (i = 0; i < r.n; i++) {                             /* every hash is compared, whether or not one matched */
        if (CRYPTO_memcmp(want, r.hash[i], HEX_HASH) == 0) hit = i;
    }
    if (hit < 0) {
        rc = SD_TOTPS_WRONG;
        goto done;
    }
    for (i = hit; i + 1 < r.n; i++) memcpy(r.hash[i], r.hash[i + 1], HEX_HASH + 1);
    r.n--;
    rc = store_recovery(dfd, &r);
    if (rc == 0) rc = SD_TOTPS_USED;
done:
    close(dfd);
    OPENSSL_cleanse(key, sizeof key);
    OPENSSL_cleanse(&a, sizeof a);
    OPENSSL_cleanse(norm, sizeof norm);
    return rc;
}

int sd_totps_recovery(const char *dir, char rc_out[][SD_TOTPS_RC_TEXT + 1])
{
    struct active a;
    struct recov r;
    int dfd;
    int rc;

    wipe_codes(rc_out);
    dfd = open_dir(dir, 0);
    if (dfd == DIR_ABSENT) return SD_TOTPS_NOTHING;
    if (dfd < 0) return dir_result(dfd);
    rc = load_active(dfd, &a);
    if (rc == LOAD_ABSENT) rc = SD_TOTPS_NOTHING;
    if (rc == 0) rc = make_recovery_set(&r, rc_out);
    if (rc == 0) rc = store_recovery(dfd, &r);
    if (rc != 0) wipe_codes(rc_out);
    close(dfd);
    OPENSSL_cleanse(&a, sizeof a);
    return rc;
}

int sd_totps_off(const char *dir)
{
    static const char *const names[] = {
        NAME_ACTIVE, NAME_PENDING, NAME_RECOVERY, NAME_FAIL,
        ".new-" NAME_ACTIVE, ".new-" NAME_PENDING, ".new-" NAME_RECOVERY, ".new-" NAME_FAIL
    };
    size_t i;
    int dfd = open_dir(dir, 0);
    int rc = SD_TOTPS_OK;

    if (dfd == DIR_ABSENT) return SD_TOTPS_OK;
    if (dfd < 0) return dir_result(dfd);
    for (i = 0; i < sizeof names / sizeof names[0]; i++) {
        if (unlinkat(dfd, names[i], 0) != 0 && errno != ENOENT) rc = SD_TOTPS_ERROR;
    }
    (void)fsync(dfd);
    close(dfd);
    return rc;
}


/* ------------------------------------------------------------------ the memory of failed logins (sdsys.fail) */

struct failrec { char src[SD_TOTPS_SRC_LEN]; long count; uint64_t last; uint64_t ok; };
struct fails   { struct failrec r[SD_TOTPS_SRC_MAX]; int n; long all_count; uint64_t all_start; };

void sd_totps_source(const char *raw, char *out)
{
    size_t n = 0;
    char c;

    if (raw != NULL) {
        for (; *raw != '\0' && n < SD_TOTPS_SRC_LEN - 1; raw++) {
            c = *raw;
            out[n++] = ((c >= '0' && c <= '9') || (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || c == ':' || c == '.' || c == '%' || c == '_' || c == '-') ? c : '?';
        }
    }
    if (n == 0) {
        strcpy(out, "unknown");
        return;
    }
    out[n] = '\0';
}

/* A source as sd_totps_source makes it (the '?' it puts for a character it will not keep included). */
static int src_ok(const char *s)
{
    size_t n = strlen(s);
    size_t i;
    char c;

    if (n == 0 || n >= SD_TOTPS_SRC_LEN) return 0;
    for (i = 0; i < n; i++) {
        c = s[i];
        if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || c == ':' || c == '.' || c == '%' || c == '_' || c == '-' || c == '?')) return 0;
    }
    return 1;
}

static int parse_u64(const char *s, uint64_t *out)
{
    const char *p;

    if (*s == '\0' || strlen(s) > 19) return 0;
    for (p = s; *p; p++) {
        if (*p < '0' || *p > '9') return 0;
    }
    *out = (uint64_t)strtoull(s, NULL, 10);
    return 1;
}

/* LN cut at its single spaces into TOK; the number of fields, or -1 for more than MAX. */
static int split_line(char *ln, char **tok, int max)
{
    int n = 0;
    char *sp;

    for (;;) {
        if (n == max) return -1;
        tok[n++] = ln;
        sp = strchr(ln, ' ');
        if (sp == NULL) return n;
        *sp = '\0';
        ln = sp + 1;
    }
}

static int parse_fail(char *text, struct fails *f)
{
    char *cur = text;
    char *ln = next_line(&cur);
    char *tok[8];
    uint64_t cnt;
    uint64_t last;
    uint64_t ok;
    int got_all = 0;
    int nt;

    memset(f, 0, sizeof *f);
    if (ln == NULL || strcmp(ln, MAGIC) != 0) return SD_TOTPS_UNSAFE;
    while ((ln = next_line(&cur)) != NULL) {
        nt = split_line(ln, tok, 8);
        if (nt == 5 && strcmp(tok[0], "src") == 0 && f->n < SD_TOTPS_SRC_MAX && src_ok(tok[1]) && parse_u64(tok[2], &cnt) && cnt <= 1000000
            && parse_u64(tok[3], &last) && parse_u64(tok[4], &ok)) {
            snprintf(f->r[f->n].src, SD_TOTPS_SRC_LEN, "%s", tok[1]);
            f->r[f->n].count = (long)cnt;
            f->r[f->n].last = last;
            f->r[f->n].ok = ok;
            f->n++;
        } else if (nt == 3 && strcmp(tok[0], "all") == 0 && !got_all && parse_u64(tok[1], &cnt) && cnt <= 100000000 && parse_u64(tok[2], &last)) {
            f->all_count = (long)cnt;
            f->all_start = last;
            got_all = 1;
        } else {
            return SD_TOTPS_UNSAFE;
        }
    }
    return got_all ? 0 : SD_TOTPS_UNSAFE;
}

/* 0 loaded (an absent file is an empty memory); SD_TOTPS_UNSAFE; SD_TOTPS_ERROR */
static int load_fail(int dfd, struct fails *f)
{
    char buf[FAIL_FILE_MAX];
    int rc = read_file(dfd, NAME_FAIL, buf, sizeof buf);

    if (rc == LOAD_ABSENT) {
        memset(f, 0, sizeof *f);
        return 0;
    }
    if (rc == 0) rc = parse_fail(buf, f);
    return rc;
}

static int store_fail(int dfd, const struct fails *f)
{
    char text[FAIL_FILE_MAX];
    size_t len;
    int i;

    len = (size_t)snprintf(text, sizeof text, MAGIC "\nall %ld %" PRIu64 "\n", f->all_count, f->all_start);
    for (i = 0; i < f->n; i++) {
        len += (size_t)snprintf(text + len, sizeof text - len, "src %s %ld %" PRIu64 " %" PRIu64 "\n", f->r[i].src, f->r[i].count, f->r[i].last, f->r[i].ok);
    }
    return write_file(dfd, NAME_FAIL, text);
}

static int fail_find(const struct fails *f, const char *src)
{
    int i;

    for (i = 0; i < f->n; i++) {
        if (strcmp(f->r[i].src, src) == 0) return i;
    }
    return -1;
}

static void fail_drop(struct fails *f, int i)
{
    memmove(&f->r[i], &f->r[i + 1], (size_t)(f->n - i - 1) * sizeof f->r[0]);
    f->n--;
}

int sd_totps_attempt(const char *dir, uint64_t now, const char *src, int *slow)
{
    struct fails f;
    int dfd;
    int rc;
    int i;
    int oldest;

    if (slow != NULL) *slow = 0;
    if (src == NULL || !src_ok(src)) return SD_TOTPS_BAD;
    dfd = open_dir(dir, 0);
    if (dfd == DIR_ABSENT) return SD_TOTPS_NOTHING;
    if (dfd < 0) return dir_result(dfd);
    rc = load_fail(dfd, &f);
    if (rc != 0) goto done;
    for (i = f.n - 1; i >= 0; i--) {                        /* forget what nobody has tried for a day */
        if (f.r[i].last + SD_TOTPS_FORGET_SECS < now) fail_drop(&f, i);
    }
    if (f.all_start == 0 || now < f.all_start || now >= f.all_start + SD_TOTPS_GLOBAL_SECS) {
        f.all_count = 0;
        f.all_start = now;
    }
    i = fail_find(&f, src);
    if (i >= 0 && f.r[i].count >= SD_TOTPS_FAIL_MAX) {
        if (slow != NULL) *slow = f.all_count > SD_TOTPS_GLOBAL_MAX;
        if (now < f.r[i].last + SD_TOTPS_LOCK_SECS) {       /* locked: ask nothing, count nothing, write nothing */
            rc = SD_TOTPS_LOCKED;
            goto done;
        }
        f.r[i].count = 0;                                   /* the lock has run out */
        f.r[i].ok = 0;
    }
    if (i < 0) {
        if (f.n >= SD_TOTPS_SRC_MAX) {                      /* the table is full: the source tried longest ago makes room */
            oldest = 0;
            for (i = 1; i < f.n; i++) {
                if (f.r[i].last < f.r[oldest].last) oldest = i;
            }
            fail_drop(&f, oldest);
        }
        i = f.n++;
        snprintf(f.r[i].src, SD_TOTPS_SRC_LEN, "%s", src);
        f.r[i].count = 0;
        f.r[i].last = 0;
        f.r[i].ok = 0;
    }
    f.r[i].count++;
    f.r[i].last = now;
    f.all_count++;
    if (slow != NULL) *slow = f.all_count > SD_TOTPS_GLOBAL_MAX;
    rc = store_fail(dfd, &f);
done:
    close(dfd);
    return rc;
}

int sd_totps_ok(const char *dir, uint64_t now, const char *src)
{
    struct fails f;
    int dfd;
    int rc;
    int i;

    if (src == NULL || !src_ok(src)) return SD_TOTPS_BAD;
    dfd = open_dir(dir, 0);
    if (dfd == DIR_ABSENT) return SD_TOTPS_NOTHING;
    if (dfd < 0) return dir_result(dfd);
    rc = load_fail(dfd, &f);
    if (rc == 0 && (i = fail_find(&f, src)) >= 0) {
        f.r[i].ok = now;
        rc = store_fail(dfd, &f);
    }
    close(dfd);
    return rc;
}

int sd_totps_clear(const char *dir, uint64_t now, const char *src)
{
    struct fails f;
    int dfd;
    int rc;
    int i;

    if (src == NULL || !src_ok(src)) return SD_TOTPS_BAD;
    dfd = open_dir(dir, 0);
    if (dfd == DIR_ABSENT) return SD_TOTPS_NOTHING;
    if (dfd < 0) return dir_result(dfd);
    rc = load_fail(dfd, &f);
    if (rc == 0) {
        i = fail_find(&f, src);
        if (i >= 0 && f.r[i].ok != 0 && now >= f.r[i].ok && now - f.r[i].ok <= SD_TOTPS_OK_SECS) {
            fail_drop(&f, i);
            if (f.all_count > 0) f.all_count--;
            rc = store_fail(dfd, &f);
        } else {
            rc = SD_TOTPS_NOTHING;
        }
    }
    close(dfd);
    return rc;
}
