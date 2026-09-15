/* verify-scramclient.c
 *
 * Checks the CLIENT-side SCRAM primitives against the RFC 7677 section 3
 * vectors.  The Windows port's gplbld/verify-scramclient.c (its
 * docs/SCRAM_AUTH.md, phase 4), adopted 14 Sep 2026 for W.4 SCRAM phase 4.
 *
 * IT INCLUDES gplsrc/scram_client.h RATHER THAN RESTATING IT, so the constants
 * below test the code that ships.  A second implementation written to agree
 * with the first would prove only that one person made the same assumption
 * twice.
 *
 * LINUX: the primitives here are hand-written (SHA-256, HMAC, PBKDF2), where
 * the port's come from bcrypt.dll, so this test carries more weight than the
 * port's.  Two known-answer rows are added for that reason: SHA-256 of "abc"
 * (FIPS 180-4) and of the empty string, which catch a padding error that a
 * PBKDF2 vector alone would only report as "wrong".
 *
 * IT NEEDS NO SERVER, NO INSTALL AND NO SUDO.  Run it through
 * gplbld/test-scram-vectors.py, which compiles and runs it with verify-scram.c.
 */

#include <stdio.h>
#include <string.h>

#include "scram_client.h"

static int failures = 0;
static int checks = 0;

static void check_str(const char* what, const char* expected, const char* got) {
    checks++;
    if (strcmp(expected, got) == 0) {
        printf("  [PASS] %-16s %s\n", what, got);
    } else {
        printf("  [FAIL] %-16s\n         expected %s\n         got      %s\n",
               what, expected, got);
        failures++;
    }
}

static void check_int(const char* what, int expected, int got) {
    checks++;
    if (expected == got) {
        printf("  [PASS] %-16s %d\n", what, got);
    } else {
        printf("  [FAIL] %-16s expected %d, got %d\n", what, expected, got);
        failures++;
    }
}

int main(void) {
    /* RFC 7677 section 3 */
    static const char* PASSWORD = "pencil";
    static const char* SALT_B64 = "W22ZaJ0SNY7soEsUEjb6gQ==";
    static const unsigned long ITERATIONS = 4096;

    static const char* CLIENT_FIRST_BARE = "n=user,r=rOprNGfwEbeRWgbNEkqO";
    static const char* SERVER_FIRST =
        "r=rOprNGfwEbeRWgbNEkqO%hvYDpWUa2RaTCAfuxFIlj)hNlF$k0,"
        "s=W22ZaJ0SNY7soEsUEjb6gQ==,i=4096";
    static const char* CLIENT_FINAL_BARE =
        "c=biws,r=rOprNGfwEbeRWgbNEkqO%hvYDpWUa2RaTCAfuxFIlj)hNlF$k0";

    unsigned char salt[64];
    size_t salt_len = 0;
    char auth_message[512];
    SCRAM_KEYS keys;
    unsigned char rnd1[18];
    unsigned char rnd2[18];
    char round[SCRAM_B64_LEN];
    unsigned char back[64];
    size_t back_len = 0;
    unsigned char digest[SCRAM_HASH_LEN];

    printf("verify-scramclient - RFC 7677 section 3, client side\n\n");

    printf("== SHA-256 known answers (Linux: hand-written)\n");
    scram_sha256((const unsigned char*)"abc", 3, digest);
    scram_b64_encode(digest, sizeof(digest), round, sizeof(round));
    check_str("sha256(abc)", "ungWv48Bz+pBQUDeXa4iI7ADYaOWF3qctBD/YfIAFa0=", round);
    scram_sha256((const unsigned char*)"", 0, digest);
    scram_b64_encode(digest, sizeof(digest), round, sizeof(round));
    check_str("sha256(empty)", "47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU=", round);

    printf("\n== base64, both directions\n");
    memset(back, 0, sizeof(back));
    memcpy(back, "abcdefghijklmnopqr", 18);
    check_int("encode 18 bytes", 1,
              scram_b64_encode(back, 18, round, sizeof(round)));
    check_int("no '=' padding", 0, strchr(round, '=') != NULL);
    check_int("decode round trip", 1,
              scram_b64_decode(round, back, sizeof(back), &back_len));
    check_int("round trip length", 18, (int)back_len);
    check_int("round trip bytes", 0, memcmp(back, "abcdefghijklmnopqr", 18));

    check_int("reject bad char", 0,
              scram_b64_decode("AAAA!AAA", back, sizeof(back), &back_len));
    check_int("reject short", 0,
              scram_b64_decode("AAA", back, sizeof(back), &back_len));
    check_int("reject mid padding", 0,
              scram_b64_decode("AA=AAAAA", back, sizeof(back), &back_len));
    check_int("reject empty", 0,
              scram_b64_decode("", back, sizeof(back), &back_len));
    check_int("reject small buffer", 0,
              scram_b64_decode("AAAAAAAA", back, 2, &back_len));

    printf("\n== the salt decodes to what the vectors assume\n");
    check_int("salt decodes", 1,
              scram_b64_decode(SALT_B64, salt, sizeof(salt), &salt_len));
    check_int("salt length", 16, (int)salt_len);

    printf("\n== AuthMessage\n");
    snprintf(auth_message, sizeof(auth_message), "%s,%s,%s",
             CLIENT_FIRST_BARE, SERVER_FIRST, CLIENT_FINAL_BARE);
    printf("  %s\n", auth_message);

    printf("\n== derivation (PBKDF2 at %lu iterations)\n", ITERATIONS);
    if (!scram_client_keys(PASSWORD, salt, salt_len, ITERATIONS,
                           auth_message, &keys)) {
        printf("  [FAIL] scram_client_keys() failed outright\n");
        printf("\n0 of 1 checks passed\n");
        return 1;
    }

    check_str("SaltedPassword",  "xKSVEDI6tPlSysH6mUQZOeeOp01r6B3fcJbodRPcYV0=", keys.salted);
    check_str("StoredKey",       "WG5d8oPm3OtcPnkdi4Uo7BkeZkBFzpcXkuLmtbsT4qY=", keys.stored);
    check_str("ServerKey",       "wfPLwcE6nTWhTAmQ7tl2KeoiWGPlZqQxSrmfPwDl2dU=", keys.server_key);
    check_str("ClientProof",     "dHzbZapWIk4jUhN+Ute9ytag9zjfMHgsqmmiz7AndVQ=", keys.proof);
    check_str("ServerSignature", "6rriTRBi23WpRR/wtup+mMhUZUn/dB5nLTJRsjl95G4=", keys.server_sig);

    printf("\n== a wrong password must not reproduce the proof\n");
    {
        SCRAM_KEYS wrong;
        check_int("derives", 1,
                  scram_client_keys("pencil2", salt, salt_len, ITERATIONS,
                                    auth_message, &wrong));
        check_int("proof differs", 0, strcmp(wrong.proof, keys.proof) == 0);
        check_int("server sig differs", 0,
                  strcmp(wrong.server_sig, keys.server_sig) == 0);
    }

    printf("\n== the comparison used on the server signature\n");
    check_int("equal matches", 1, scram_equal(keys.server_sig, keys.server_sig));
    check_int("different rejected", 0, scram_equal(keys.server_sig, keys.proof));
    check_int("length mismatch rejected", 0, scram_equal("abc", "abcd"));

    printf("\n== nonce source\n");
    check_int("random 1", 1, scram_random(rnd1, sizeof(rnd1)));
    check_int("random 2", 1, scram_random(rnd2, sizeof(rnd2)));
    check_int("two draws differ", 0, memcmp(rnd1, rnd2, sizeof(rnd1)) == 0);
    {
        unsigned char zero[18];
        memset(zero, 0, sizeof(zero));
        check_int("not all zero", 0, memcmp(rnd1, zero, sizeof(rnd1)) == 0);
    }

    printf("\n%d of %d checks passed\n", checks - failures, checks);
    if (failures) {
        printf("FAILED\n");
        return 1;
    }
    printf("OK\n");
    return 0;
}
