/* verify-totp.c
 *
 * Checks the TOTP engine (gplsrc/sd_totp.c) against the published vectors:
 * RFC 4226 appendix D (HOTP, ten values), RFC 6238 appendix B (the six SHA-1
 * times, eight digits and the same six cut to six) and RFC 4648 section 10
 * (base32), then the rules the engine adds - the window, a code used once,
 * what counts as a malformed code, the provisioning link, the secret.
 *
 * IT INCLUDES gplsrc/sd_totp.h AND LINKS gplsrc/sd_totp.c RATHER THAN
 * RESTATING THEM, so what is tested is the code that ships.
 *
 * With arguments it is a calculator for gplbld/test-totp-vectors.py, which
 * compares it with a second implementation written in Python (hmac, base64):
 *   verify-totp hotp KEYHEX COUNTER DIGITS   prints the value, or ERR
 *   verify-totp b32  HEX                     prints the base32 text, or ERR
 *   verify-totp unb32 TEXT                   prints the bytes as hex, or ERR
 *
 * IT NEEDS NO SERVER, NO INSTALL, NO SUDO.  Run it through
 * gplbld/test-totp-vectors.py, which compiles and runs it.
 */

#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "sd_totp.h"

static int failures = 0;
static int checks = 0;

static void check_int(const char *what, int64_t expected, int64_t got)
{
    checks++;
    if (expected == got) {
        printf("  [PASS] %-44s %" PRId64 "\n", what, got);
    } else {
        printf("  [FAIL] %-44s\n         expected %" PRId64 "\n         got      %" PRId64 "\n", what, expected, got);
        failures++;
    }
}

static void check_str(const char *what, const char *expected, const char *got)
{
    checks++;
    if (strcmp(expected, got) == 0) {
        printf("  [PASS] %-44s %s\n", what, got);
    } else {
        printf("  [FAIL] %-44s\n         expected %s\n         got      %s\n", what, expected, got);
        failures++;
    }
}

static void check_true(const char *what, int ok)
{
    checks++;
    if (ok) {
        printf("  [PASS] %s\n", what);
    } else {
        printf("  [FAIL] %s\n", what);
        failures++;
    }
}

static const unsigned char KEY[] = "12345678901234567890";          /* the RFC key, 20 bytes */
#define KEYLEN (sizeof KEY - 1)

static void code_text(char *out, size_t outsz, uint64_t step)
{
    snprintf(out, outsz, "%06" PRId64, sd_totp_hotp(KEY, KEYLEN, step, 6));
}

static void rfc4226(void)
{
    static const int64_t want[10] = { 755224, 287082, 359152, 969429, 338314, 254676, 287922, 162583, 399871, 520489 };
    char what[64];
    int i;

    printf("\n-- RFC 4226 appendix D: HOTP, six digits, counters 0 to 9\n");
    for (i = 0; i < 10; i++) {
        snprintf(what, sizeof what, "hotp counter %d", i);
        check_int(what, want[i], sd_totp_hotp(KEY, KEYLEN, (uint64_t)i, 6));
    }
}

static void rfc6238(void)
{
    static const struct { uint64_t t; int64_t eight; } row[] = {
        { 59ULL, 94287082 }, { 1111111109ULL, 7081804 }, { 1111111111ULL, 14050471 },
        { 1234567890ULL, 89005924 }, { 2000000000ULL, 69279037 }, { 20000000000ULL, 65353130 }
    };
    char what[64];
    size_t i;

    printf("\n-- RFC 6238 appendix B: SHA-1, the six times\n");
    for (i = 0; i < sizeof row / sizeof row[0]; i++) {
        snprintf(what, sizeof what, "t=%" PRIu64 " eight digits", row[i].t);
        check_int(what, row[i].eight, sd_totp_hotp(KEY, KEYLEN, row[i].t / 30, 8));
        snprintf(what, sizeof what, "t=%" PRIu64 " six digits (sd_totp_at)", row[i].t);
        check_int(what, row[i].eight % 1000000, sd_totp_at(KEY, KEYLEN, row[i].t));
    }
}

static void window(void)
{
    const uint64_t t0 = 1111111111ULL;
    const uint64_t s0 = t0 / 30;
    const uint64_t base = s0 * 30;                 /* first second of the step */
    char c[5][8];
    char what[96];
    int i, j, distinct = 1;

    printf("\n-- the window, and a code used once\n");
    for (i = 0; i < 5; i++) code_text(c[i], sizeof c[i], s0 - 2 + (uint64_t)i);   /* s0-2 .. s0+2 */
    for (i = 0; i < 5; i++) for (j = i + 1; j < 5; j++) if (strcmp(c[i], c[j]) == 0) distinct = 0;
    check_true("precondition: the five codes around the step are distinct", distinct);

    check_int("this step, first second", (int64_t)s0, sd_totp_check(KEY, KEYLEN, base, c[2], -1));
    check_int("this step, last second", (int64_t)s0, sd_totp_check(KEY, KEYLEN, base + 29, c[2], -1));
    check_int("the step before", (int64_t)s0 - 1, sd_totp_check(KEY, KEYLEN, base, c[1], -1));
    check_int("the step after", (int64_t)s0 + 1, sd_totp_check(KEY, KEYLEN, base, c[3], -1));
    check_int("two steps before is refused", SD_TOTP_NOMATCH, sd_totp_check(KEY, KEYLEN, base, c[0], -1));
    check_int("two steps after is refused", SD_TOTP_NOMATCH, sd_totp_check(KEY, KEYLEN, base, c[4], -1));
    check_int("the window moves with the clock (next step)", (int64_t)s0 + 1, sd_totp_check(KEY, KEYLEN, base + 30, c[3], -1));
    check_int("... and drops what is now two behind", SD_TOTP_NOMATCH, sd_totp_check(KEY, KEYLEN, base + 30 + 30, c[1], -1));

    check_int("used once: the same step again", SD_TOTP_REPLAY, sd_totp_check(KEY, KEYLEN, base, c[2], (int64_t)s0));
    check_int("used once: an older step after a newer", SD_TOTP_REPLAY, sd_totp_check(KEY, KEYLEN, base, c[1], (int64_t)s0));
    check_int("used once: a newer step is taken", (int64_t)s0 + 1, sd_totp_check(KEY, KEYLEN, base, c[3], (int64_t)s0));
    check_int("used once: last step one before", (int64_t)s0, sd_totp_check(KEY, KEYLEN, base, c[2], (int64_t)s0 - 1));
    check_int("used once: a last step in the future", SD_TOTP_REPLAY, sd_totp_check(KEY, KEYLEN, base, c[2], (int64_t)s0 + 5));
    check_int("a wrong code is not a replay", SD_TOTP_NOMATCH, sd_totp_check(KEY, KEYLEN, base, c[4], (int64_t)s0));

    /* a near miss: the right code with ONE digit changed, each of the six places in turn (every digit is compared) */
    for (i = 0; i < SD_TOTP_DIGITS; i++) {
        char nm[8];
        int clash = 0;

        strcpy(nm, c[2]);
        nm[i] = (char)('0' + (nm[i] - '0' + 1) % 10);
        for (j = 0; j < 5; j++) if (strcmp(nm, c[j]) == 0) clash = 1;
        snprintf(what, sizeof what, "a near miss: digit %d changed", i + 1);
        if (clash) {
            check_true("precondition: the near miss is not another code of the window", 0);
            continue;
        }
        check_int(what, SD_TOTP_NOMATCH, sd_totp_check(KEY, KEYLEN, base, nm, -1));
    }

    snprintf(what, sizeof what, "a code of another key is refused");
    {
        static const unsigned char other[] = "12345678901234567891";
        char o[8];
        snprintf(o, sizeof o, "%06" PRId64, sd_totp_hotp(other, sizeof other - 1, s0, 6));
        check_true("the other key's code differs here (precondition)", strcmp(o, c[2]) != 0);
        check_int(what, SD_TOTP_NOMATCH, sd_totp_check(KEY, KEYLEN, base, o, -1));
    }
}

static void edges(void)
{
    char c[8];

    printf("\n-- the ends of time and a leading zero\n");
    check_int("time 0, step 0", 0, sd_totp_check(KEY, KEYLEN, 0, "755224", -1));
    check_int("time 0 takes step 1 (the window's far side)", 1, sd_totp_check(KEY, KEYLEN, 0, "287082", -1));
    check_int("time 29 is still step 0", 0, sd_totp_check(KEY, KEYLEN, 29, "755224", -1));
    check_int("time 30: step 0 is the step before", 0, sd_totp_check(KEY, KEYLEN, 30, "755224", -1));
    check_int("time 60: step 0 is two behind", SD_TOTP_NOMATCH, sd_totp_check(KEY, KEYLEN, 60, "755224", -1));
    check_int("a code with a leading zero (081804)", 37037036, sd_totp_check(KEY, KEYLEN, 1111111109ULL, "081804", -1));
    check_int("... without the zero is malformed", SD_TOTP_BAD, sd_totp_check(KEY, KEYLEN, 1111111109ULL, "81804", -1));
    code_text(c, sizeof c, UINT64_MAX / 30);
    check_int("the largest clock", (int64_t)(UINT64_MAX / 30), sd_totp_check(KEY, KEYLEN, UINT64_MAX, c, -1));
}

static void malformed(void)
{
    printf("\n-- what is not a usable code or key\n");
    check_int("no text", SD_TOTP_BAD, sd_totp_check(KEY, KEYLEN, 0, NULL, -1));
    check_int("empty text", SD_TOTP_BAD, sd_totp_check(KEY, KEYLEN, 0, "", -1));
    check_int("five digits", SD_TOTP_BAD, sd_totp_check(KEY, KEYLEN, 0, "75522", -1));
    check_int("seven digits", SD_TOTP_BAD, sd_totp_check(KEY, KEYLEN, 0, "7552244", -1));
    check_int("a letter", SD_TOTP_BAD, sd_totp_check(KEY, KEYLEN, 0, "75522a", -1));
    check_int("a leading space", SD_TOTP_BAD, sd_totp_check(KEY, KEYLEN, 0, " 75522", -1));
    check_int("a space inside", SD_TOTP_BAD, sd_totp_check(KEY, KEYLEN, 0, "755 224", -1));
    check_int("a trailing newline", SD_TOTP_BAD, sd_totp_check(KEY, KEYLEN, 0, "755224\n", -1));
    check_int("a sign", SD_TOTP_BAD, sd_totp_check(KEY, KEYLEN, 0, "+75522", -1));
    check_int("no key", SD_TOTP_BAD, sd_totp_check(NULL, KEYLEN, 0, "755224", -1));
    check_int("a key of no length", SD_TOTP_BAD, sd_totp_check(KEY, 0, 0, "755224", -1));
    check_int("hotp: no key", -1, sd_totp_hotp(NULL, KEYLEN, 0, 6));
    check_int("hotp: key of no length", -1, sd_totp_hotp(KEY, 0, 0, 6));
    check_int("hotp: five digits asked", -1, sd_totp_hotp(KEY, KEYLEN, 0, 5));
    check_int("hotp: ten digits asked", -1, sd_totp_hotp(KEY, KEYLEN, 0, 10));
    {
        unsigned char big[2000];
        memset(big, 7, sizeof big);
        check_int("hotp: key of 1025 bytes", -1, sd_totp_hotp(big, 1025, 0, 6));
        check_true("hotp: key of 1024 bytes works", sd_totp_hotp(big, 1024, 0, 6) >= 0);
        check_true("hotp: key of 100 bytes (longer than the block) works", sd_totp_hotp(big, 100, 0, 6) >= 0);
    }
}

static void base32(void)
{
    static const struct { const char *plain; const char *text; } v[] = {
        { "", "" }, { "f", "MY" }, { "fo", "MZXQ" }, { "foo", "MZXW6" }, { "foob", "MZXW6YQ" },
        { "fooba", "MZXW6YTB" }, { "foobar", "MZXW6YTBOI" }
    };
    char out[64];
    unsigned char raw[64];
    char what[64];
    size_t i;
    int n;

    printf("\n-- base32 (RFC 4648 section 10, written without padding)\n");
    for (i = 0; i < sizeof v / sizeof v[0]; i++) {
        snprintf(what, sizeof what, "encode \"%s\"", v[i].plain);
        n = sd_totp_b32_encode((const unsigned char *)v[i].plain, strlen(v[i].plain), out, sizeof out);
        check_str(what, v[i].text, out);
        check_int("   its length", (int64_t)strlen(v[i].text), n);
        if (v[i].plain[0]) {
            snprintf(what, sizeof what, "decode \"%s\"", v[i].text);
            n = sd_totp_b32_decode(v[i].text, raw, sizeof raw);
            check_int(what, (int64_t)strlen(v[i].plain), n);
            check_true("   its bytes", n == (int)strlen(v[i].plain) && memcmp(raw, v[i].plain, (size_t)n) == 0);
        }
    }
    check_int("decode with the padding", 5, sd_totp_b32_decode("MZXW6YTB", raw, sizeof raw));
    check_int("decode padded \"MY======\"", 1, sd_totp_b32_decode("MY======", raw, sizeof raw));
    check_int("decode lower case", 5, sd_totp_b32_decode("mzxw6ytb", raw, sizeof raw));
    check_int("decode in groups of four with spaces and hyphens", 5, sd_totp_b32_decode("MZXW 6YTB", raw, sizeof raw));
    check_int("decode \"MZXW-6YTB\"", 5, sd_totp_b32_decode("MZXW-6YTB", raw, sizeof raw));
    check_int("refuse a character outside the alphabet", -1, sd_totp_b32_decode("MZXW6!TB", raw, sizeof raw));
    check_int("refuse a 1 (not in the alphabet)", -1, sd_totp_b32_decode("MZXW61TB", raw, sizeof raw));
    check_int("refuse text after the padding", -1, sd_totp_b32_decode("MY==A===", raw, sizeof raw));
    check_int("refuse a non-zero leftover bit (\"MZ\")", -1, sd_totp_b32_decode("MZ", raw, sizeof raw));
    check_int("refuse a length no encoder writes (one char)", -1, sd_totp_b32_decode("M", raw, sizeof raw));
    check_int("refuse a length no encoder writes (three chars)", -1, sd_totp_b32_decode("MYA", raw, sizeof raw));
    check_int("refuse a length no encoder writes (six chars)", -1, sd_totp_b32_decode("MYAAAA", raw, sizeof raw));
    check_int("refuse empty text", -1, sd_totp_b32_decode("", raw, sizeof raw));
    check_int("refuse only padding", -1, sd_totp_b32_decode("======", raw, sizeof raw));
    check_int("refuse when the output is too small", -1, sd_totp_b32_decode("MZXW6YTB", raw, 4));
    check_int("accept when the output fits exactly", 5, sd_totp_b32_decode("MZXW6YTB", raw, 5));
    check_int("no text", -1, sd_totp_b32_decode(NULL, raw, sizeof raw));
    check_int("encode: no room for the NUL", -1, sd_totp_b32_encode((const unsigned char *)"fooba", 5, out, 8));
    check_int("encode: room for the NUL", 8, sd_totp_b32_encode((const unsigned char *)"fooba", 5, out, 9));
    n = sd_totp_b32_encode(KEY, KEYLEN, out, sizeof out);
    check_str("the RFC key in base32 (the secret an app is given)", "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ", out);
    check_int("   its length is SD_TOTP_B32_LEN", SD_TOTP_B32_LEN, n);
}

static void link_and_secret(void)
{
    static const char want[] =
        "otpauth://totp/SD%20Core:sdsys@host1?secret=GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ&issuer=SD%20Core&algorithm=SHA1&digits=6&period=30";
    static const char sec[] = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ";
    char out[256];
    unsigned char a[SD_TOTP_SECRET_LEN], b[SD_TOTP_SECRET_LEN], zero[SD_TOTP_SECRET_LEN];
    int n;

    printf("\n-- the provisioning link and a new secret\n");
    n = sd_totp_uri(out, sizeof out, "SD Core", "sdsys@host1", sec);
    check_str("the link", want, out);
    check_int("   its length", (int64_t)strlen(want), n);
    n = sd_totp_uri(out, strlen(want) + 1, "SD Core", "sdsys@host1", sec);
    check_int("a buffer that fits exactly", (int64_t)strlen(want), n);
    n = sd_totp_uri(out, strlen(want), "SD Core", "sdsys@host1", sec);
    check_int("a buffer one byte short", -1, n);
    check_str("   and it is left empty", "", out);
    sd_totp_uri(out, sizeof out, "a:b c", "x y/z", sec);
    check_true("a colon, space and slash are percent-encoded",
               strncmp(out, "otpauth://totp/a%3Ab%20c:x%20y%2Fz?secret=", 42) == 0);
    check_int("empty issuer", -1, sd_totp_uri(out, sizeof out, "", "sdsys", sec));
    check_int("empty account", -1, sd_totp_uri(out, sizeof out, "SD", "", sec));
    check_int("empty secret", -1, sd_totp_uri(out, sizeof out, "SD", "sdsys", ""));
    check_int("a secret with a lower-case letter", -1, sd_totp_uri(out, sizeof out, "SD", "sdsys", "GEZDgNBV"));
    check_int("a secret with a 1", -1, sd_totp_uri(out, sizeof out, "SD", "sdsys", "GEZD1NBV"));
    check_int("no buffer", -1, sd_totp_uri(NULL, 10, "SD", "sdsys", sec));

    memset(zero, 0, sizeof zero);
    check_int("new secret: 20 bytes", 0, sd_totp_new_secret(a, sizeof a));
    check_int("new secret: a second one", 0, sd_totp_new_secret(b, sizeof b));
    check_true("the two differ", memcmp(a, b, sizeof a) != 0);
    check_true("neither is all zero", memcmp(a, zero, sizeof a) != 0 && memcmp(b, zero, sizeof b) != 0);
    check_int("new secret: 15 bytes is too few", -1, sd_totp_new_secret(a, 15));
    check_int("new secret: 16 bytes is allowed", 0, sd_totp_new_secret(a, 16));
    check_int("new secret: no buffer", -1, sd_totp_new_secret(NULL, 20));
    check_true("a new secret makes a code", sd_totp_hotp(a, sizeof a, 1, 6) >= 0);
}

static int hexval(char c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

/* HEX text to bytes; the number of bytes, or -1. */
static int unhex(const char *s, unsigned char *out, size_t outsz)
{
    size_t n = strlen(s) / 2;
    size_t i;

    if (strlen(s) % 2 != 0 || n > outsz) return -1;
    for (i = 0; i < n; i++) {
        int h = hexval(s[2 * i]);
        int l = hexval(s[2 * i + 1]);
        if (h < 0 || l < 0) return -1;
        out[i] = (unsigned char)(h * 16 + l);
    }
    return (int)n;
}

static int calculator(int argc, char **argv)
{
    unsigned char raw[4096];
    char text[8192];
    int n, i;

    if (strcmp(argv[1], "hotp") == 0 && argc == 5) {
        int64_t v;
        n = unhex(argv[2], raw, sizeof raw);
        if (n < 0) { puts("ERR"); return 0; }
        v = sd_totp_hotp(raw, (size_t)n, strtoull(argv[3], NULL, 10), atoi(argv[4]));
        if (v < 0) puts("ERR"); else printf("%" PRId64 "\n", v);
        return 0;
    }
    if (strcmp(argv[1], "b32") == 0 && argc == 3) {
        n = unhex(argv[2], raw, sizeof raw);
        if (n < 0 || sd_totp_b32_encode(raw, (size_t)n, text, sizeof text) < 0) { puts("ERR"); return 0; }
        puts(text);
        return 0;
    }
    if (strcmp(argv[1], "unb32") == 0 && argc == 3) {
        n = sd_totp_b32_decode(argv[2], raw, sizeof raw);
        if (n < 0) { puts("ERR"); return 0; }
        for (i = 0; i < n; i++) printf("%02x", raw[i]);
        printf("\n");
        return 0;
    }
    fprintf(stderr, "usage: verify-totp [hotp KEYHEX COUNTER DIGITS | b32 HEX | unb32 TEXT]\n");
    return 2;
}

int main(int argc, char **argv)
{
    if (argc > 1) return calculator(argc, argv);

    printf("verify-totp: gplsrc/sd_totp.c against RFC 4226, RFC 6238 and RFC 4648\n");
    rfc4226();
    rfc6238();
    window();
    edges();
    malformed();
    base32();
    link_and_secret();
    printf("\n%d checks, %d failed\n", checks, failures);
    return failures ? 1 : 0;
}
