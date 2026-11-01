/* sd_totp_store.h
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
 * 01 Nov 26 dm  S.95 stage 1 - written.  Checked by gplbld/test-totp-store.py,
 *               which drives the sd-totp command (gplsrc/sd_totp_cmd.c) on a
 *               scratch store.
 * END-HISTORY
 *
 * START-DESCRIPTION:
 *
 * One directory holds three files for the one account the factor guards, sdsys:
 *
 *   sdsys.active    the secret in use and the step of the code last accepted
 *   sdsys.pending   a new secret that has been shown and not yet proved
 *   sdsys.recovery  a salt and the hashes of the recovery codes not yet used
 *
 * THE DIRECTORY AND EVERY FILE IN IT MUST BELONG TO THE USER THE PROCESS RUNS AS
 * (root, in production) AND BE CLOSED TO EVERYONE ELSE (0700, 0600), be what they
 * claim to be (a directory, a plain file with one link) and be opened without
 * following a link.  Anything else is SD_TOTPS_UNSAFE and the answer is never
 * "accepted": a store that is not what it should be fails closed.
 *
 * NO FUNCTION RETURNS OR PRINTS AN EXISTING SECRET.  A new secret leaves
 * sd_totps_begin once, at the moment it is made.  A recovery code leaves
 * sd_totps_confirm or sd_totps_recovery once, at the moment it is made, and only
 * its salted hash is kept.  A new secret becomes the active one only when a code
 * made from it has been typed back (sd_totps_confirm), and five wrong codes throw
 * it away.
 *
 * Every function takes the directory as an argument and an exclusive lock on it
 * for the whole call, so the PAM module and the command cannot interleave.  The
 * clock is an argument too, for the test.
 *
 * END-DESCRIPTION
 */

#ifndef SD_TOTP_STORE_H
#define SD_TOTP_STORE_H

#include <stddef.h>
#include <stdint.h>

#define SD_TOTPS_DIR_DEFAULT    "/etc/sdcore/totp"
#define SD_TOTPS_RC_COUNT       8       /* recovery codes in a set */
#define SD_TOTPS_RC_TEXT        11      /* "XXXXX-XXXXX", without the NUL */
#define SD_TOTPS_TRIES          5       /* wrong codes a pending secret survives */
#define SD_TOTPS_URI_MAX        256

/* results */
#define SD_TOTPS_OK             0
#define SD_TOTPS_USED           1       /* check: a recovery code was accepted and used up */
#define SD_TOTPS_WRONG          (-1)    /* the code is not right */
#define SD_TOTPS_REPLAY         (-2)    /* the code is right but was used already */
#define SD_TOTPS_DISCARDED      (-3)    /* confirm: too many wrong codes, the pending secret is gone */
#define SD_TOTPS_NOTHING        (-4)    /* nothing pending (confirm) or nothing enrolled (check, recovery) */
#define SD_TOTPS_UNSAFE         (-5)    /* the directory or a file is not as it must be, or does not parse */
#define SD_TOTPS_ERROR          (-6)    /* an input or output failure, or the generator failed */
#define SD_TOTPS_BAD            (-7)    /* an argument, or the text typed, is not usable */

struct sd_totps_info {
    int has_active;
    int has_pending;
    int recovery_left;
    int64_t last_step;                  /* -1 when none */
};

/* What is enrolled.  A missing directory is nothing enrolled, not an error. */
int sd_totps_info(const char *dir, struct sd_totps_info *out);

/* Make a NEW pending secret (replacing a pending one, never touching the active one), and
 * give back its base32 text and the link for an authenticator app, once.  The directory is
 * made (0700) if its parent exists.  issuer and account are printable text of 1 to 64 bytes. */
int sd_totps_begin(const char *dir, const char *issuer, const char *account,
                   char *b32, size_t b32sz, char *uri, size_t urisz);

/* Prove the pending secret with a code made from it.  On SD_TOTPS_OK the pending secret is
 * the active one (its step recorded as used), a NEW set of recovery codes replaces any old
 * one and is returned in rc, and the pending file is gone. */
int sd_totps_confirm(const char *dir, uint64_t now, const char *code, char rc[][SD_TOTPS_RC_TEXT + 1]);

/* Check what a person typed against the active secret: six digits (spaces and hyphens are
 * ignored) or a recovery code.  SD_TOTPS_OK records the step; SD_TOTPS_USED removes the code. */
int sd_totps_check(const char *dir, uint64_t now, const char *given);

/* A new set of recovery codes, replacing the old; the codes are returned once.  Needs an
 * active secret. */
int sd_totps_recovery(const char *dir, char rc[][SD_TOTPS_RC_TEXT + 1]);

/* Switch the factor off: remove all three files. */
int sd_totps_off(const char *dir);

#endif
