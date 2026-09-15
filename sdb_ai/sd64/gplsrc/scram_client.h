/* Modifications Copyright (c) 2026 Donald Montaine
 *
 * This library is free software: you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or (at
 * your option) any later version.
 *
 * This library is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser
 * General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this library.  If not, see <https://www.gnu.org/licenses/>.
 *
 * Linking exception (additional permission under GNU LGPL version 3
 * section 7): as a special exception, the copyright holders give you
 * permission to link this library with independent modules to produce an
 * executable, regardless of the license terms of these independent modules,
 * and to copy and distribute the resulting executable under terms of your
 * choice, provided that you also meet, for each linked independent module,
 * the terms and conditions of the license of that module.  An independent
 * module is a module which is not derived from or based on this library.
 */

/* scram_client.h
 *
 * SCRAM-SHA-256 client primitives for sdclilib.  The Windows port's
 * gplsrc/sdclilib/scram_client.h (its docs/SCRAM_AUTH.md, phase 4), adopted
 * 14 Sep 2026 for W.4 SCRAM phase 4.  The same copy is in linuxsdclilib.
 *
 * WHY A HEADER OF static FUNCTIONS RATHER THAN A .c FILE - the port's reason.
 * The client library ships as ONE binary that can be copied next to an
 * application, so nothing here may need a library that would have to travel
 * with it.  And it is a header so the vector test drives the real code:
 * gplbld/verify-scramclient.c includes this same file and checks it against
 * the RFC 7677 section 3 vectors.
 *
 * WHAT DIFFERS FROM THE PORT, AND WHY IT HAD TO.  The port takes SHA-256,
 * HMAC, PBKDF2 and random bytes from bcrypt.dll, which is part of Windows.
 * Linux has no crypto library that is guaranteed to be present - libc has
 * none, and libsodium or OpenSSL would be a dependency every client
 * application then has to carry.  So the port's REASON is kept and its SOURCE
 * cannot be: SHA-256 (FIPS 180-4), HMAC (RFC 2104) and PBKDF2 (RFC 8018 5.2)
 * are implemented here, random bytes come from getrandom(2), and clearing is
 * explicit_bzero(3).  Base64, the key derivation, the constant-time compare
 * and every function's signature and contract are the port's unchanged.  The
 * RFC 7677 vectors are what make hand-written primitives acceptable: a
 * transcription error in any of the three cannot reproduce them.
 *
 * THE SERVER RUNS PBKDF2 ONCE, AT MODIFY.PASSWORD.  The client runs it at every
 * login, so the 600,000 iterations are entirely the client's cost - 0.07 s in
 * Python's hashlib on the machine the phase 3 witness ran on.
 */

#ifndef SCRAM_CLIENT_H
#define SCRAM_CLIENT_H

#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <sys/random.h>

#define SCRAM_HASH_LEN 32              /* SHA-256, and SCRAM's key length */
#define SCRAM_B64_LEN  64              /* 32 bytes -> 44 chars + NUL, rounded */

/* Everything a client-final needs, all base64.  The intermediates are kept
   because the vector test checks them: knowing WHICH step diverged is the
   difference between a five minute fix and an afternoon. */
typedef struct {
    char salted[SCRAM_B64_LEN];      /* SaltedPassword  */
    char stored[SCRAM_B64_LEN];      /* StoredKey       */
    char server_key[SCRAM_B64_LEN];  /* ServerKey       */
    char proof[SCRAM_B64_LEN];       /* ClientProof     */
    char server_sig[SCRAM_B64_LEN];  /* ServerSignature */
} SCRAM_KEYS;

static const char scram_b64_alphabet[] =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

/* ---------------------------------------------------------------------- */
/* Answers 0 if the output buffer is too small, which every caller checks.  */
static int scram_b64_encode(const unsigned char* in, size_t n,
                            char* out, size_t out_sz) {
    size_t need = ((n + 2) / 3) * 4 + 1;
    size_t i = 0;
    size_t o = 0;

    if (out == NULL || out_sz < need)
        return 0;

    while (i < n) {
        unsigned long v = (unsigned long)in[i++] << 16;
        int pad = 2;

        if (i < n) { v |= (unsigned long)in[i++] << 8; pad--; }
        if (i < n) { v |= (unsigned long)in[i++];      pad--; }

        out[o++] = scram_b64_alphabet[(v >> 18) & 0x3F];
        out[o++] = scram_b64_alphabet[(v >> 12) & 0x3F];
        out[o++] = (pad > 1) ? '=' : scram_b64_alphabet[(v >> 6) & 0x3F];
        out[o++] = (pad > 0) ? '=' : scram_b64_alphabet[v & 0x3F];
    }
    out[o] = '\0';
    return 1;
}

/* Strict: rejects any character outside the alphabet, misplaced padding and a
   length that is not a multiple of four.  A salt that fails to decode is a
   server sending nonsense, and the login must fail rather than proceed on a
   half-decoded value. */
static int scram_b64_decode(const char* in, unsigned char* out,
                            size_t out_sz, size_t* out_len) {
    size_t n;
    size_t i;
    size_t o = 0;
    unsigned long v = 0;
    int have = 0;
    int pad = 0;

    if (in == NULL || out == NULL)
        return 0;

    n = strlen(in);
    if (n == 0 || (n % 4) != 0)
        return 0;

    for (i = 0; i < n; i++) {
        const char* p;
        char c = in[i];

        if (c == '=') {
            /* Padding is legal only in the last two positions. */
            if (i < n - 2)
                return 0;
            pad++;
            continue;
        }
        if (pad)                       /* data after padding */
            return 0;

        p = strchr(scram_b64_alphabet, c);
        if (p == NULL || c == '\0')
            return 0;

        v = (v << 6) | (unsigned long)(p - scram_b64_alphabet);
        if (++have == 4) {
            if (o + 3 > out_sz)
                return 0;
            out[o++] = (unsigned char)((v >> 16) & 0xFF);
            out[o++] = (unsigned char)((v >> 8) & 0xFF);
            out[o++] = (unsigned char)(v & 0xFF);
            v = 0;
            have = 0;
        }
    }

    if (pad == 1) {
        if (have != 3) return 0;
        v <<= 6;
        if (o + 2 > out_sz) return 0;
        out[o++] = (unsigned char)((v >> 16) & 0xFF);
        out[o++] = (unsigned char)((v >> 8) & 0xFF);
    } else if (pad == 2) {
        if (have != 2) return 0;
        v <<= 12;
        if (o + 1 > out_sz) return 0;
        out[o++] = (unsigned char)((v >> 16) & 0xFF);
    } else if (pad != 0 || have != 0) {
        return 0;
    }

    if (out_len != NULL)
        *out_len = o;
    return 1;
}

/* ---------------------------------------------------------------------- */
/* Random bytes from the kernel.  LINUX: getrandom(2) where the port has
   BCryptGenRandom.  A short read or EINTR is retried; anything else fails
   the login rather than proceeding with a nonce that is not random. */
static int scram_random(unsigned char* out, size_t n) {
    size_t got = 0;

    while (got < n) {
        ssize_t r = getrandom(out + got, n - got, 0);
        if (r < 0) {
            if (errno == EINTR)
                continue;
            return 0;
        }
        got += (size_t)r;
    }
    return 1;
}

/* ---------------------------------------------------------------------- */
/* SHA-256, FIPS 180-4.  LINUX ONLY - see the header for why it is here. */

typedef struct {
    uint32_t h[8];
    uint64_t bits;
    unsigned char block[64];
    size_t used;
} SCRAM_SHA256_CTX;

static const uint32_t scram_sha256_k[64] = {
    0x428a2f98UL, 0x71374491UL, 0xb5c0fbcfUL, 0xe9b5dba5UL, 0x3956c25bUL, 0x59f111f1UL, 0x923f82a4UL, 0xab1c5ed5UL,
    0xd807aa98UL, 0x12835b01UL, 0x243185beUL, 0x550c7dc3UL, 0x72be5d74UL, 0x80deb1feUL, 0x9bdc06a7UL, 0xc19bf174UL,
    0xe49b69c1UL, 0xefbe4786UL, 0x0fc19dc6UL, 0x240ca1ccUL, 0x2de92c6fUL, 0x4a7484aaUL, 0x5cb0a9dcUL, 0x76f988daUL,
    0x983e5152UL, 0xa831c66dUL, 0xb00327c8UL, 0xbf597fc7UL, 0xc6e00bf3UL, 0xd5a79147UL, 0x06ca6351UL, 0x14292967UL,
    0x27b70a85UL, 0x2e1b2138UL, 0x4d2c6dfcUL, 0x53380d13UL, 0x650a7354UL, 0x766a0abbUL, 0x81c2c92eUL, 0x92722c85UL,
    0xa2bfe8a1UL, 0xa81a664bUL, 0xc24b8b70UL, 0xc76c51a3UL, 0xd192e819UL, 0xd6990624UL, 0xf40e3585UL, 0x106aa070UL,
    0x19a4c116UL, 0x1e376c08UL, 0x2748774cUL, 0x34b0bcb5UL, 0x391c0cb3UL, 0x4ed8aa4aUL, 0x5b9cca4fUL, 0x682e6ff3UL,
    0x748f82eeUL, 0x78a5636fUL, 0x84c87814UL, 0x8cc70208UL, 0x90befffaUL, 0xa4506cebUL, 0xbef9a3f7UL, 0xc67178f2UL
};

#define SCRAM_ROTR(x, n) (((x) >> (n)) | ((x) << (32 - (n))))

static void scram_sha256_compress(SCRAM_SHA256_CTX* c, const unsigned char* p) {
    uint32_t w[64];
    uint32_t a, b, d, e, f, g, h, cc, t1, t2;
    int i;

    for (i = 0; i < 16; i++)
        w[i] = ((uint32_t)p[i * 4] << 24) | ((uint32_t)p[i * 4 + 1] << 16) |
               ((uint32_t)p[i * 4 + 2] << 8) | (uint32_t)p[i * 4 + 3];
    for (i = 16; i < 64; i++) {
        t1 = SCRAM_ROTR(w[i - 2], 17) ^ SCRAM_ROTR(w[i - 2], 19) ^ (w[i - 2] >> 10);
        t2 = SCRAM_ROTR(w[i - 15], 7) ^ SCRAM_ROTR(w[i - 15], 18) ^ (w[i - 15] >> 3);
        w[i] = t1 + w[i - 7] + t2 + w[i - 16];
    }

    a = c->h[0]; b = c->h[1]; cc = c->h[2]; d = c->h[3];
    e = c->h[4]; f = c->h[5]; g = c->h[6]; h = c->h[7];

    for (i = 0; i < 64; i++) {
        t1 = h + (SCRAM_ROTR(e, 6) ^ SCRAM_ROTR(e, 11) ^ SCRAM_ROTR(e, 25)) +
             ((e & f) ^ (~e & g)) + scram_sha256_k[i] + w[i];
        t2 = (SCRAM_ROTR(a, 2) ^ SCRAM_ROTR(a, 13) ^ SCRAM_ROTR(a, 22)) +
             ((a & b) ^ (a & cc) ^ (b & cc));
        h = g; g = f; f = e; e = d + t1;
        d = cc; cc = b; b = a; a = t1 + t2;
    }

    c->h[0] += a; c->h[1] += b; c->h[2] += cc; c->h[3] += d;
    c->h[4] += e; c->h[5] += f; c->h[6] += g; c->h[7] += h;

    explicit_bzero(w, sizeof(w));
}

static void scram_sha256_init(SCRAM_SHA256_CTX* c) {
    c->h[0] = 0x6a09e667UL; c->h[1] = 0xbb67ae85UL; c->h[2] = 0x3c6ef372UL;
    c->h[3] = 0xa54ff53aUL; c->h[4] = 0x510e527fUL; c->h[5] = 0x9b05688cUL;
    c->h[6] = 0x1f83d9abUL; c->h[7] = 0x5be0cd19UL;
    c->bits = 0;
    c->used = 0;
}

static void scram_sha256_update(SCRAM_SHA256_CTX* c, const unsigned char* p, size_t n) {
    c->bits += (uint64_t)n * 8U;
    while (n > 0) {
        size_t take = 64 - c->used;
        if (take > n)
            take = n;
        memcpy(c->block + c->used, p, take);
        c->used += take;
        p += take;
        n -= take;
        if (c->used == 64) {
            scram_sha256_compress(c, c->block);
            c->used = 0;
        }
    }
}

static void scram_sha256_final(SCRAM_SHA256_CTX* c, unsigned char out[SCRAM_HASH_LEN]) {
    uint64_t bits = c->bits;
    int i;

    c->block[c->used++] = 0x80;
    if (c->used > 56) {
        memset(c->block + c->used, 0, 64 - c->used);
        scram_sha256_compress(c, c->block);
        c->used = 0;
    }
    memset(c->block + c->used, 0, 56 - c->used);
    for (i = 0; i < 8; i++)
        c->block[56 + i] = (unsigned char)(bits >> (56 - 8 * i));
    scram_sha256_compress(c, c->block);

    for (i = 0; i < 8; i++) {
        out[i * 4]     = (unsigned char)(c->h[i] >> 24);
        out[i * 4 + 1] = (unsigned char)(c->h[i] >> 16);
        out[i * 4 + 2] = (unsigned char)(c->h[i] >> 8);
        out[i * 4 + 3] = (unsigned char)(c->h[i]);
    }
    explicit_bzero(c, sizeof(*c));
}

static int scram_sha256(const unsigned char* in, size_t n,
                        unsigned char out[SCRAM_HASH_LEN]) {
    SCRAM_SHA256_CTX c;

    scram_sha256_init(&c);
    if (n > 0)
        scram_sha256_update(&c, in, n);
    scram_sha256_final(&c, out);
    return 1;
}

/* HMAC-SHA-256, RFC 2104, over a raw message of any length. */
static int scram_hmac_raw(const unsigned char* key, size_t key_len,
                          const unsigned char* msg, size_t msg_len,
                          unsigned char out[SCRAM_HASH_LEN]) {
    unsigned char k[64];
    unsigned char pad[64];
    unsigned char inner[SCRAM_HASH_LEN];
    SCRAM_SHA256_CTX c;
    size_t i;

    if (key == NULL)
        return 0;

    memset(k, 0, sizeof(k));
    if (key_len > sizeof(k))
        scram_sha256(key, key_len, k);
    else if (key_len > 0)
        memcpy(k, key, key_len);

    for (i = 0; i < sizeof(pad); i++)
        pad[i] = (unsigned char)(k[i] ^ 0x36);
    scram_sha256_init(&c);
    scram_sha256_update(&c, pad, sizeof(pad));
    if (msg_len > 0)
        scram_sha256_update(&c, msg, msg_len);
    scram_sha256_final(&c, inner);

    for (i = 0; i < sizeof(pad); i++)
        pad[i] = (unsigned char)(k[i] ^ 0x5c);
    scram_sha256_init(&c);
    scram_sha256_update(&c, pad, sizeof(pad));
    scram_sha256_update(&c, inner, sizeof(inner));
    scram_sha256_final(&c, out);

    explicit_bzero(k, sizeof(k));
    explicit_bzero(pad, sizeof(pad));
    explicit_bzero(inner, sizeof(inner));
    return 1;
}

static int scram_hmac256(const unsigned char* key, size_t key_len,
                         const char* msg,
                         unsigned char out[SCRAM_HASH_LEN]) {
    /* key must be non-NULL - the port's guard, kept. */
    if (key == NULL)
        return 0;
    return scram_hmac_raw(key, key_len, (const unsigned char*)msg,
                          msg == NULL ? 0 : strlen(msg), out);
}

/* PBKDF2-HMAC-SHA-256, RFC 8018 section 5.2, for any output length. */
static int scram_pbkdf2(const char* password,
                        const unsigned char* salt, size_t salt_len,
                        unsigned long iterations,
                        unsigned char* out, size_t out_len) {
    unsigned char block[128 + 4];
    unsigned char u[SCRAM_HASH_LEN];
    unsigned char t[SCRAM_HASH_LEN];
    size_t pw_len;
    size_t done = 0;
    uint32_t counter = 1;
    unsigned long j;
    size_t k;

    if (password == NULL || salt == NULL || iterations == 0 ||
        salt_len > sizeof(block) - 4)
        return 0;

    pw_len = strlen(password);

    while (done < out_len) {
        size_t take;

        memcpy(block, salt, salt_len);
        block[salt_len]     = (unsigned char)(counter >> 24);
        block[salt_len + 1] = (unsigned char)(counter >> 16);
        block[salt_len + 2] = (unsigned char)(counter >> 8);
        block[salt_len + 3] = (unsigned char)(counter);

        scram_hmac_raw((const unsigned char*)password, pw_len,
                       block, salt_len + 4, u);
        memcpy(t, u, sizeof(t));
        for (j = 1; j < iterations; j++) {
            scram_hmac_raw((const unsigned char*)password, pw_len, u, sizeof(u), u);
            for (k = 0; k < sizeof(t); k++)
                t[k] ^= u[k];
        }

        take = out_len - done;
        if (take > sizeof(t))
            take = sizeof(t);
        memcpy(out + done, t, take);
        done += take;
        counter++;
    }

    explicit_bzero(u, sizeof(u));
    explicit_bzero(t, sizeof(t));
    explicit_bzero(block, sizeof(block));
    return 1;
}

/* ----------------------------------------------------------------------
   The whole client-side derivation, with no I/O in it - the port's.

   SaltedPassword  = PBKDF2(password, salt, i, 32)
   ClientKey       = HMAC(SaltedPassword, "Client Key")
   StoredKey       = SHA256(ClientKey)
   ServerKey       = HMAC(SaltedPassword, "Server Key")
   ClientSignature = HMAC(StoredKey, AuthMessage)
   ClientProof     = ClientKey XOR ClientSignature
   ServerSignature = HMAC(ServerKey, AuthMessage)

   ServerSignature is computed HERE, before the server has answered, so the
   caller has something to compare against rather than something to believe. */
static int scram_client_keys(const char* password,
                             const unsigned char* salt, size_t salt_len,
                             unsigned long iterations,
                             const char* auth_message,
                             SCRAM_KEYS* keys) {
    unsigned char salted[SCRAM_HASH_LEN];
    unsigned char client_key[SCRAM_HASH_LEN];
    unsigned char stored_key[SCRAM_HASH_LEN];
    unsigned char server_key[SCRAM_HASH_LEN];
    unsigned char signature[SCRAM_HASH_LEN];
    unsigned char proof[SCRAM_HASH_LEN];
    int i;
    int ok = 0;

    if (password == NULL || auth_message == NULL || keys == NULL)
        return 0;

    memset(keys, 0, sizeof(*keys));

    if (!scram_pbkdf2(password, salt, salt_len, iterations,
                      salted, sizeof(salted)))
        goto done;
    if (!scram_hmac256(salted, sizeof(salted), "Client Key", client_key))
        goto done;
    if (!scram_sha256(client_key, sizeof(client_key), stored_key))
        goto done;
    if (!scram_hmac256(salted, sizeof(salted), "Server Key", server_key))
        goto done;
    if (!scram_hmac256(stored_key, sizeof(stored_key), auth_message, signature))
        goto done;

    for (i = 0; i < SCRAM_HASH_LEN; i++)
        proof[i] = (unsigned char)(client_key[i] ^ signature[i]);

    if (!scram_hmac256(server_key, sizeof(server_key), auth_message, signature))
        goto done;

    if (!scram_b64_encode(salted,     sizeof(salted),     keys->salted,     SCRAM_B64_LEN) ||
        !scram_b64_encode(stored_key, sizeof(stored_key), keys->stored,     SCRAM_B64_LEN) ||
        !scram_b64_encode(server_key, sizeof(server_key), keys->server_key, SCRAM_B64_LEN) ||
        !scram_b64_encode(proof,      sizeof(proof),      keys->proof,      SCRAM_B64_LEN) ||
        !scram_b64_encode(signature,  sizeof(signature),  keys->server_sig, SCRAM_B64_LEN))
        goto done;

    ok = 1;

done:
    /* explicit_bzero, not memset: the compiler is entitled to delete a memset
       whose result is never read.  LINUX: the port's SecureZeroMemory. */
    explicit_bzero(salted, sizeof(salted));
    explicit_bzero(client_key, sizeof(client_key));
    explicit_bzero(stored_key, sizeof(stored_key));
    explicit_bzero(server_key, sizeof(server_key));
    explicit_bzero(signature, sizeof(signature));
    explicit_bzero(proof, sizeof(proof));

    if (!ok && keys != NULL)
        explicit_bzero(keys, sizeof(*keys));
    return ok;
}

/* Constant time, for the server-signature comparison - the port's. */
static int scram_equal(const char* a, const char* b) {
    size_t i;
    size_t la;
    unsigned char diff = 0;

    if (a == NULL || b == NULL)
        return 0;

    la = strlen(a);
    if (la != strlen(b))
        return 0;

    for (i = 0; i < la; i++)
        diff |= (unsigned char)(a[i] ^ b[i]);

    return diff == 0;
}

#endif /* SCRAM_CLIENT_H */
