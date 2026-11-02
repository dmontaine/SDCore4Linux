/* verify-pamtotp.c
 *
 * A stand-in for sshd: it starts a REAL PAM stack (pam_start_confdir, so the service file is the
 * test's own, in a scratch directory), answers the module's prompts from the command line, and
 * prints what happened, one `key=value` per line, for gplbld/test-pam-sdtotp.py.
 *
 *   verify-pamtotp CONFDIR USER RHOST MODE [REPLY ...]
 *
 *   MODE  auth   pam_authenticate only (the password stage "failed" afterwards)
 *         login  pam_authenticate, then pam_setcred(PAM_ESTABLISH_CRED) if it succeeded (the whole login worked)
 *         cred   pam_setcred only
 *         session  as login, then pam_open_session (S.101, 2 Nov 26: the order /etc/pam.d/login gives: credentials, then the session)
 *         open   pam_open_session only (a session with no login before it in this process: the grant must come from the store)
 *         close  pam_close_session only
 *   SDTEST_TTY in the environment sets PAM_TTY (a console login).
 *   RHOST "-" sets none.  Each REPLY answers one prompt, in order; a prompt with no reply left fails the
 *   conversation (an ssh client that gave up).
 *
 * Output:  prompt=<text> and echo=off|on for every prompt; authenticate=<n>; setcred=<n>; elapsed_ms=<n>
 * (the time pam_authenticate took, which is how the wait after a failure is seen).  It needs no root,
 * and no sshd.
 */

#define _GNU_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include <security/pam_appl.h>

struct script {
    char **replies;
    int n;
    int next;
};

static int conv(int num_msg, const struct pam_message **msg, struct pam_response **resp, void *appdata)
{
    struct script *sc = appdata;
    struct pam_response *r;
    int i;

    r = calloc((size_t)num_msg, sizeof *r);
    if (r == NULL) return PAM_BUF_ERR;
    for (i = 0; i < num_msg; i++) {
        if (msg[i]->msg_style == PAM_PROMPT_ECHO_OFF || msg[i]->msg_style == PAM_PROMPT_ECHO_ON) {
            printf("prompt=%s\necho=%s\n", msg[i]->msg, msg[i]->msg_style == PAM_PROMPT_ECHO_OFF ? "off" : "on");
            if (sc->next >= sc->n) {
                free(r);
                return PAM_CONV_ERR;
            }
            r[i].resp = strdup(sc->replies[sc->next++]);
        } else {
            printf("message=%s\n", msg[i]->msg);
        }
    }
    *resp = r;
    return PAM_SUCCESS;
}

int main(int argc, char **argv)
{
    struct script sc;
    struct pam_conv c;
    pam_handle_t *pamh = NULL;
    struct timespec t0;
    struct timespec t1;
    int r;
    int auth = 0;

    if (argc < 5) {
        fprintf(stderr, "usage: verify-pamtotp CONFDIR USER RHOST auth|login|cred|session|open|close [REPLY ...]\n");
        return 2;
    }
    sc.replies = argv + 5;
    sc.n = argc - 5;
    sc.next = 0;
    c.conv = conv;
    c.appdata_ptr = &sc;

    r = pam_start_confdir("sdtest", argv[2], &c, argv[1], &pamh);
    if (r != PAM_SUCCESS) {
        printf("start=%d\n", r);
        return 1;
    }
    if (strcmp(argv[3], "-") != 0) pam_set_item(pamh, PAM_RHOST, argv[3]);
    if (getenv("SDTEST_TTY") != NULL) pam_set_item(pamh, PAM_TTY, getenv("SDTEST_TTY"));     /* S.101: a console login (login sets PAM_TTY) */
    if (strcmp(argv[4], "auth") == 0 || strcmp(argv[4], "login") == 0 || strcmp(argv[4], "session") == 0) {
        clock_gettime(CLOCK_MONOTONIC, &t0);
        r = pam_authenticate(pamh, 0);
        clock_gettime(CLOCK_MONOTONIC, &t1);
        printf("authenticate=%d\nelapsed_ms=%ld\n", r, (long)((t1.tv_sec - t0.tv_sec) * 1000 + (t1.tv_nsec - t0.tv_nsec) / 1000000));
        auth = (r == PAM_SUCCESS);
    }
    if (strcmp(argv[4], "cred") == 0 || ((strcmp(argv[4], "login") == 0 || strcmp(argv[4], "session") == 0) && auth)) {
        r = pam_setcred(pamh, PAM_ESTABLISH_CRED);
        printf("setcred=%d\n", r);
    }
    /* S.101: session - authenticate, setcred, then pam_open_session (login's order: the credentials first); close - pam_close_session only */
    if (strcmp(argv[4], "session") == 0 && auth) {
        r = pam_open_session(pamh, 0);
        printf("open_session=%d\n", r);
    }
    if (strcmp(argv[4], "open") == 0) {
        r = pam_open_session(pamh, 0);
        printf("open_session=%d\n", r);
    }
    if (strcmp(argv[4], "close") == 0) {
        r = pam_close_session(pamh, 0);
        printf("close_session=%d\n", r);
    }
    pam_end(pamh, PAM_SUCCESS);
    return 0;
}
