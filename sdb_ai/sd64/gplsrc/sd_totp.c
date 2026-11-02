/* sd_totp.c
 * Time-based one-time passwords (RFC 6238 over RFC 4226 HOTP, HMAC-SHA1).
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
 * 01 Nov 26 dm  S.95 stage 0 - written for the remote SDSYS login's second
 *               factor.  Checked by gplbld/test-totp-vectors.py, which runs
 *               gplbld/verify-totp.c against the RFC vectors and, with
 *               --selftest, against mutants of this file.
 * END-HISTORY
 *
 * START-DESCRIPTION:
 *
 * See sd_totp.h for what the functions promise.  Three things here are on
 * purpose and each is held by the check:
 *
 * EVERY STEP OF THE WINDOW IS COMPARED, in constant time (CRYPTO_memcmp), even
 * after one has matched, so the time taken says nothing about which step was
 * right or whether any was.  The answer is the HIGHEST matching step that is
 * newer than the last one used; if codes of two steps happen to coincide (one
 * chance in a million) the fresh one wins rather than a replay being reported.
 *
 * A CODE IS USED ONCE.  The engine keeps nothing, so the caller stores the
 * step it is given and passes it back as last_step.  A matching step that is
 * not newer than last_step is SD_TOTP_REPLAY, never success.  This also
 * refuses an older step after a newer one was used, which a clock that ran
 * backwards would otherwise let through.
 *
 * THE GIVEN TEXT MUST BE EXACTLY SIX DIGITS.  Nothing is trimmed here: a
 * caller that wants to take "123 456" removes the space itself, so that what
 * is compared is never more than what the engine was shown.
 *
 * END-DESCRIPTION
 */

#include <inttypes.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>

#include <openssl/crypto.h>
#include <openssl/evp.h>
#include <openssl/hmac.h>
#include <openssl/rand.h>

#include "sd_totp.h"

#define MAX_KEY 1024            /* bytes; a secret is 20, this only keeps the HMAC call sane */

static const char B32[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";


int64_t sd_totp_hotp(const unsigned char *key, size_t keylen, uint64_t counter, int digits)
{
    static const uint32_t pow10[] = { 1, 10, 100, 1000, 10000, 100000, 1000000, 10000000, 100000000, 1000000000 };
    unsigned char msg[8];
    unsigned char mac[EVP_MAX_MD_SIZE];
    unsigned int maclen = 0;
    unsigned int off;
    uint32_t bin;
    int i;

    if (key == NULL || keylen == 0 || keylen > MAX_KEY || digits < 6 || digits > 9) return -1;
    for (i = 0; i < 8; i++) msg[7 - i] = (unsigned char)(counter >> (8 * i));        /* big-endian */
    if (HMAC(EVP_sha1(), key, (int)keylen, msg, sizeof msg, mac, &maclen) == NULL || maclen != 20) return -1;
    off = mac[19] & 0x0f;                                                            /* dynamic truncation */
    bin = ((uint32_t)(mac[off] & 0x7f) << 24) | ((uint32_t)mac[off + 1] << 16)
        | ((uint32_t)mac[off + 2] << 8) | (uint32_t)mac[off + 3];
    return (int64_t)(bin % pow10[digits]);
}


int64_t sd_totp_at(const unsigned char *key, size_t keylen, uint64_t unixtime)
{
    return sd_totp_hotp(key, keylen, unixtime / SD_TOTP_STEP, SD_TOTP_DIGITS);
}


int64_t sd_totp_check(const unsigned char *key, size_t keylen, uint64_t unixtime,
                      const char *given, int64_t last_step)
{
    return sd_totp_check_window(key, keylen, unixtime, given, last_step, SD_TOTP_WINDOW);
}


/* 2 Nov 26 (S.101): the window as an argument, so that the PAM module's root-owned window=N can give a person more time to read the code
   (the owner, 1 Nov 26: "sometimes it takes me that long to get the phone out of my pocket").  Outside 1 to SD_TOTP_WINDOW_MAX is SD_TOTP_BAD. */
int64_t sd_totp_check_window(const unsigned char *key, size_t keylen, uint64_t unixtime,
                             const char *given, int64_t last_step, int window)
{
    char want[SD_TOTP_DIGITS + 1];
    uint64_t now = unixtime / SD_TOTP_STEP;
    uint64_t first;
    uint64_t last;
    uint64_t step;
    int64_t code;
    int64_t fresh = SD_TOTP_NOMATCH;
    int matched = 0;
    int i;

    if (key == NULL || keylen == 0 || given == NULL || strlen(given) != SD_TOTP_DIGITS) return SD_TOTP_BAD;
    if (window < 1 || window > SD_TOTP_WINDOW_MAX) return SD_TOTP_BAD;
    first = (now > (uint64_t)window) ? now - (uint64_t)window : 0;
    last = now + (uint64_t)window;
    for (i = 0; i < SD_TOTP_DIGITS; i++) {
        if (given[i] < '0' || given[i] > '9') return SD_TOTP_BAD;
    }
    for (step = first; step <= last; step++) {
        code = sd_totp_hotp(key, keylen, step, SD_TOTP_DIGITS);
        if (code < 0) return SD_TOTP_BAD;
        snprintf(want, sizeof want, "%06u", (unsigned)(code % 1000000));       /* six digits: SD_TOTP_DIGITS */
        if (CRYPTO_memcmp(want, given, SD_TOTP_DIGITS) == 0) {
            matched = 1;
            if ((int64_t)step > last_step) fresh = (int64_t)step;
        }
    }
    if (fresh >= 0) return fresh;
    return matched ? SD_TOTP_REPLAY : SD_TOTP_NOMATCH;
}


int sd_totp_b32_encode(const unsigned char *in, size_t n, char *out, size_t outsz)
{
    size_t need;
    size_t o = 0;
    size_t i;
    uint32_t buf = 0;
    int bits = 0;

    if (out == NULL || (in == NULL && n != 0) || n > (size_t)INT_MAX / 2) return -1;
    need = (n * 8 + 4) / 5;
    if (need + 1 > outsz) return -1;
    for (i = 0; i < n; i++) {
        buf = (buf << 8) | in[i];
        bits += 8;
        while (bits >= 5) {
            out[o++] = B32[(buf >> (bits - 5)) & 31];
            bits -= 5;
        }
    }
    if (bits > 0) out[o++] = B32[(buf << (5 - bits)) & 31];
    out[o] = '\0';
    return (int)o;
}


int sd_totp_b32_decode(const char *in, unsigned char *out, size_t outsz)
{
    uint32_t buf = 0;
    int bits = 0;
    size_t o = 0;
    int padding = 0;
    const char *p;
    const char *q;
    char c;

    if (in == NULL || out == NULL) return -1;
    for (p = in; *p; p++) {
        c = *p;
        if (c == ' ' || c == '-') continue;
        if (c == '=') {
            padding = 1;
            continue;
        }
        if (padding) return -1;                         /* text after the padding */
        if (c >= 'a' && c <= 'z') c = (char)(c - 'a' + 'A');
        q = strchr(B32, c);
        if (q == NULL) return -1;
        buf = (buf << 5) | (uint32_t)(q - B32);
        bits += 5;
        if (bits >= 8) {
            if (o >= outsz) return -1;
            out[o++] = (unsigned char)(buf >> (bits - 8));
            bits -= 8;
        }
    }
    if (o == 0 || bits >= 5) return -1;                 /* nothing, or a length no encoder writes */
    if (bits > 0 && (buf & ((1u << bits) - 1)) != 0) return -1;   /* leftover bits must be zero */
    return (int)o;
}


struct sbuf {
    char *p;
    size_t n;
    size_t len;
    int over;
};

static void sb_put(struct sbuf *b, const char *s)
{
    size_t l = strlen(s);

    if (b->over || b->len + l + 1 > b->n) {
        b->over = 1;
        return;
    }
    memcpy(b->p + b->len, s, l + 1);
    b->len += l;
}

/* Percent-encode: letters, digits and - . _ ~ @ stay; every other byte becomes %XX. */
static void sb_put_pct(struct sbuf *b, const char *s)
{
    static const char hex[] = "0123456789ABCDEF";
    char t[4];
    const unsigned char *u;

    for (u = (const unsigned char *)s; *u; u++) {
        if ((*u >= 'A' && *u <= 'Z') || (*u >= 'a' && *u <= 'z') || (*u >= '0' && *u <= '9')
            || *u == '-' || *u == '.' || *u == '_' || *u == '~' || *u == '@') {
            t[0] = (char)*u;
            t[1] = '\0';
        } else {
            t[0] = '%';
            t[1] = hex[*u >> 4];
            t[2] = hex[*u & 15];
            t[3] = '\0';
        }
        sb_put(b, t);
    }
}


int sd_totp_uri(char *out, size_t outsz, const char *issuer, const char *account, const char *b32)
{
    struct sbuf b;
    const char *s;

    if (out == NULL || outsz == 0) return -1;
    out[0] = '\0';
    if (issuer == NULL || account == NULL || b32 == NULL || *issuer == '\0' || *account == '\0' || *b32 == '\0') return -1;
    for (s = b32; *s; s++) {
        if (strchr(B32, *s) == NULL) return -1;
    }
    b.p = out;
    b.n = outsz;
    b.len = 0;
    b.over = 0;
    sb_put(&b, "otpauth://totp/");
    sb_put_pct(&b, issuer);
    sb_put(&b, ":");
    sb_put_pct(&b, account);
    sb_put(&b, "?secret=");
    sb_put(&b, b32);
    sb_put(&b, "&issuer=");
    sb_put_pct(&b, issuer);
    sb_put(&b, "&algorithm=SHA1&digits=6&period=30");      /* SD_TOTP_DIGITS and SD_TOTP_STEP; the check pins the text */
    if (b.over) {
        out[0] = '\0';
        return -1;
    }
    return (int)b.len;
}


int sd_totp_new_secret(unsigned char *out, size_t n)
{
    if (out == NULL || n < 16 || n > (size_t)INT_MAX) return -1;
    return RAND_bytes(out, (int)n) == 1 ? 0 : -1;
}
