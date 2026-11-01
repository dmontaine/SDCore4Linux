/* sd_totp.h
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
 *               gplbld/verify-totp.c against the RFC vectors.
 * END-HISTORY
 *
 * START-DESCRIPTION:
 *
 * The engine only.  It reads no file, keeps no state, writes no log and knows
 * nothing of SD, PAM or sshd; the caller passes the clock and the last step it
 * accepted and stores what comes back.  The PAM module and the sd-totp command
 * (S.95 stages 1 and 2) are built on it.
 *
 * Fixed on purpose: SHA-1, six digits, thirty seconds.  Those are the values
 * every authenticator app takes without being told (Google Authenticator,
 * Microsoft Authenticator, Authy, 1Password, FreeOTP).
 *
 * END-DESCRIPTION
 */

#ifndef SD_TOTP_H
#define SD_TOTP_H

#include <stddef.h>
#include <stdint.h>

#define SD_TOTP_DIGITS      6       /* digits of a code */
#define SD_TOTP_STEP        30      /* seconds a code lives */
#define SD_TOTP_WINDOW      1       /* steps accepted either side of the clock's step */
#define SD_TOTP_SECRET_LEN  20      /* bytes of a new secret: 160 bits, as RFC 4226 recommends */
#define SD_TOTP_B32_LEN     32      /* characters of such a secret in base32, no padding */

/* sd_totp_check() answers a step number (>= 0) or one of these. */
#define SD_TOTP_NOMATCH     (-1)    /* no step in the window gives this code */
#define SD_TOTP_REPLAY      (-2)    /* the code is right but its step was already used */
#define SD_TOTP_BAD         (-3)    /* the key or the given text is not usable: not six digits, no key */

/* HOTP value of one counter, 6 to 9 digits; -1 on a bad argument or a failed HMAC. */
int64_t sd_totp_hotp(const unsigned char *key, size_t keylen, uint64_t counter, int digits);

/* The six-digit code for the step that contains unixtime; -1 on failure. */
int64_t sd_totp_at(const unsigned char *key, size_t keylen, uint64_t unixtime);

/* Check what a person typed.  `given` must be exactly six digits.  The steps from
 * (unixtime / 30) - SD_TOTP_WINDOW to + SD_TOTP_WINDOW are ALL compared, in constant
 * time, whether or not an earlier one matched.  A step is taken only if it is greater
 * than last_step (pass -1 when none has been used): the answer is that step, which the
 * caller must store; a code whose step is not greater is SD_TOTP_REPLAY. */
int64_t sd_totp_check(const unsigned char *key, size_t keylen, uint64_t unixtime,
                      const char *given, int64_t last_step);

/* Base32 (RFC 4648), capitals, no padding.  Encode writes a NUL-terminated string and
 * answers its length, or -1 when outsz has no room for the text and the NUL.  Decode
 * ignores spaces and hyphens, takes either case and a trailing run of '=', refuses any
 * other character and any non-zero leftover bit, and answers the number of bytes, or -1
 * (including when out is too small, and for empty input). */
int sd_totp_b32_encode(const unsigned char *in, size_t n, char *out, size_t outsz);
int sd_totp_b32_decode(const char *in, unsigned char *out, size_t outsz);

/* The provisioning link an authenticator app reads (the Key URI format):
 * otpauth://totp/ISSUER:ACCOUNT?secret=B32&issuer=ISSUER&algorithm=SHA1&digits=6&period=30
 * ISSUER and ACCOUNT are percent-encoded (letters, digits, - . _ ~ and @ stay).
 * Answers the length of the NUL-terminated link, or -1 when anything is empty, the
 * secret is not capital base32, or outsz is too small. */
int sd_totp_uri(char *out, size_t outsz, const char *issuer, const char *account, const char *b32);

/* n random bytes from the system's generator (n at least 16); 0 on success, -1 otherwise. */
int sd_totp_new_secret(unsigned char *out, size_t n);

#endif
