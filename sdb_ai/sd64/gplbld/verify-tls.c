/* verify-tls.c
 *
 * S.19, 15 Sep 2026.  Exercises gplsrc/sd_tls.c and gplsrc/sd_tlssrv.c - the
 * API's TLS relay and client - in a sandbox: no install, no sd, no sudo.
 * Run it through gplbld/test-tls-relay.py, which compiles it and gives it an
 * empty directory to keep the server identity in.
 *
 * A child process stands in for sd: it does what start_connection() does
 * (sd_tls_relay_start on descriptor 0, then the ACK), sends the binding the
 * relay handed it, then echoes.  The parent is the client.
 *
 * WHAT IT CANNOT MEASURE, said in its own output: the relay giving up root
 * (only root has root to give up) - that is the install witness's.
 */

#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#include <openssl/crypto.h>
#include <openssl/err.h>
#include <openssl/evp.h>
#include <openssl/opensslv.h>
#include <openssl/ssl.h>

#include "sd_tls.h"

#define STAND_IN_REFUSED 10

static int checks = 0;
static int failures = 0;

static void check(const char* what, bool ok, const char* detail) {
  checks++;
  printf("  [%s] %-52s %s\n", ok ? "PASS" : "FAIL", what,
         detail != NULL ? detail : "");
  if (!ok)
    failures++;
}

static long now_ms(void) {
  struct timespec ts;
  clock_gettime(CLOCK_MONOTONIC, &ts);
  return (long)ts.tv_sec * 1000L + ts.tv_nsec / 1000000L;
}

static void hex(const unsigned char* b, size_t n, char* out) {
  size_t i;
  for (i = 0; i < n; i++)
    sprintf(out + 2 * i, "%02x", b[i]);
}

static bool write_all(int fd, const void* buf, size_t len) {
  const char* p = buf;
  while (len > 0) {
    ssize_t n = write(fd, p, len);
    if (n < 0 && errno == EINTR)
      continue;
    if (n <= 0)
      return false;
    p += n;
    len -= (size_t)n;
  }
  return true;
}

static bool read_exact(SD_TLS_CLIENT* c, unsigned char* buf, int len) {
  while (len > 0) {
    int n = sd_tls_client_read(c, buf, len);
    if (n <= 0)
      return false;
    buf += n;
    len -= n;
  }
  return true;
}

/* The sd stand-in: start_connection()'s part, then an echo. */
static pid_t start_server(const char* dir, int timeout_ms, int* client_fd) {
  int sv[2];
  pid_t pid;

  if (socketpair(AF_UNIX, SOCK_STREAM, 0, sv) != 0) {
    perror("socketpair");
    exit(2);
  }
  fflush(stdout);
  pid = fork();
  if (pid < 0) {
    perror("fork");
    exit(2);
  }
  if (pid == 0) {
    char err[512];
    const unsigned char* binding;

    close(sv[0]);
    /* 0, 1 AND 2, as systemd gives sdclient@.service: StandardInput=socket
       with output and error inheriting it. */
    if (dup2(sv[1], 0) < 0 || dup2(sv[1], 1) < 0 || dup2(sv[1], 2) < 0)
      _exit(20);
    close(sv[1]);
    if (!sd_tls_relay_start(dir, timeout_ms, err, sizeof(err)))
      _exit(STAND_IN_REFUSED);
    /* Plaintext on stderr after the relay starts.  If descriptor 2 were still
       the connection, these bytes would land in the TLS stream ahead of the
       ACK and A3/B3 would fail. */
    if (write(2, "PLAINTEXT ON STDERR\n", 20) < 0) {
      /* nothing to do - a failed write to /dev/null is not expected */
    }
    binding = sd_tls_server_binding();
    if (binding == NULL)
      _exit(11);
    if (send(0, "\x06", 1, 0) != 1)
      _exit(12);
    if (!write_all(1, binding, SD_TLS_BINDING_BYTES))
      _exit(13);
    for (;;) {
      char buf[8192];
      ssize_t n = read(0, buf, sizeof(buf));
      if (n < 0 && errno == EINTR)
        continue;
      if (n <= 0)
        _exit(0);
      if (!write_all(1, buf, (size_t)n))
        _exit(14);
    }
  }
  close(sv[1]);
  *client_fd = sv[0];
  return pid;
}

/* Exit code, or -1 if it had not ended by the deadline (then killed). */
static int wait_exit(pid_t pid, int timeout_ms) {
  long deadline = now_ms() + timeout_ms;
  int status;

  for (;;) {
    pid_t r = waitpid(pid, &status, WNOHANG);
    if (r == pid)
      return WIFEXITED(status) ? WEXITSTATUS(status) : -2;
    if (now_ms() > deadline) {
      kill(pid, SIGKILL);
      (void)waitpid(pid, &status, 0);
      return -1;
    }
    usleep(10000);
  }
}

/* One session: handshake, ACK, binding.  Fills binding and fingerprint. */
static SD_TLS_CLIENT* open_session(const char* label, const char* dir,
                                   int* fd, pid_t* pid,
                                   unsigned char* srv_binding,
                                   unsigned char* fingerprint) {
  char err[512];
  char what[80];
  char detail[128];
  unsigned char ack = 0;
  SD_TLS_CLIENT* c;

  *pid = start_server(dir, 3000, fd);
  c = sd_tls_client_start(*fd, 3000, err, sizeof(err));
  snprintf(what, sizeof(what), "%s1 handshake completes", label);
  check(what, c != NULL, c != NULL ? "" : err);
  if (c == NULL)
    return NULL;

  snprintf(what, sizeof(what), "%s2 protocol is TLS 1.3", label);
  check(what, strcmp(sd_tls_client_version(c), "TLSv1.3") == 0,
        sd_tls_client_version(c));

  snprintf(what, sizeof(what), "%s3 the ACK arrives inside TLS", label);
  check(what, read_exact(c, &ack, 1) && ack == 0x06, "");

  snprintf(what, sizeof(what), "%s4 server's binding equals client's", label);
  if (read_exact(c, srv_binding, SD_TLS_BINDING_BYTES)) {
    hex(srv_binding, 8, detail);
    strcat(detail, "...");
    check(what, memcmp(srv_binding, sd_tls_client_binding(c),
                       SD_TLS_BINDING_BYTES) == 0, detail);
  } else {
    check(what, false, "the binding never arrived");
  }

  snprintf(what, sizeof(what), "%s5 server certificate fingerprint read", label);
  check(what, sd_tls_client_peer_sha256(c, fingerprint), "");
  return c;
}

int main(int argc, char* argv[]) {
  const char* dir;
  char path[4096];
  char detail[256];
  char err[512];
  unsigned char bind_a[SD_TLS_BINDING_BYTES];
  unsigned char bind_b[SD_TLS_BINDING_BYTES];
  unsigned char zero[SD_TLS_BINDING_BYTES];
  unsigned char fp_a[32];
  unsigned char fp_b[32];
  SD_TLS_CLIENT* c;
  struct stat st;
  int fd;
  int code;
  pid_t pid;
  long t0;
  long elapsed;

  if (argc != 2) {
    fprintf(stderr, "usage: verify-tls <empty directory for the identity>\n");
    return 2;
  }
  dir = argv[1];
  signal(SIGPIPE, SIG_IGN);
  memset(zero, 0, sizeof(zero));
  snprintf(path, sizeof(path), "%s/%s", dir, SD_TLS_IDENTITY_FILE);

  printf("verify-tls: identity dir  %s\n", dir);
  printf("verify-tls: headers       %s\n", OPENSSL_VERSION_TEXT);
  printf("verify-tls: runtime       %s\n", OpenSSL_version(OPENSSL_VERSION));
  printf("verify-tls: euid          %d\n", (int)geteuid());

  if (stat(path, &st) == 0) {
    printf("REFUSING - %s already exists, so 'first connection creates the "
           "identity' could not be measured.\n", path);
    return 2;
  }

  /* ---- A: first connection ------------------------------------------ */
  printf("\nA  first connection: the identity is created\n");
  c = open_session("A", dir, &fd, &pid, bind_a, fp_a);
  if (c != NULL) {
    unsigned char out[16384];
    unsigned char in[16384];
    unsigned char decoded[64];
    long total = 0;
    bool same = true;
    char* attr;
    int i;

    check("A6 binding is not all zero", memcmp(bind_a, zero, sizeof(zero)) != 0,
          "");

    while (total < 1048576 && same) {
      for (i = 0; i < (int)sizeof(out); i++)
        out[i] = (unsigned char)((total + i) * 31 + 7);
      if (!sd_tls_client_write(c, out, sizeof(out)) ||
          !read_exact(c, in, sizeof(in)) || memcmp(out, in, sizeof(in)) != 0)
        same = false;
      total += sizeof(out);
    }
    snprintf(detail, sizeof(detail), "%ld bytes", same ? total : 0L);
    check("A7 1 MB echoed through the relay intact", same, detail);

    attr = sd_tls_cbind_attr(bind_a);
    code = attr != NULL ? EVP_DecodeBlock(decoded, (unsigned char*)attr,
                                          (int)strlen(attr)) : -1;
    check("A8 c= attribute is base64(p=tls-exporter,, + binding)",
          attr != NULL && strlen(attr) == 64 && code == 48 &&
              memcmp(decoded, SD_TLS_GS2_HEADER, 16) == 0 &&
              memcmp(decoded + 16, bind_a, SD_TLS_BINDING_BYTES) == 0,
          attr != NULL ? attr : "NULL");
    free(attr);
    sd_tls_client_end(c);
  }
  close(fd);
  code = wait_exit(pid, 5000);
  snprintf(detail, sizeof(detail), "exit %d", code);
  check("A9 the sd stand-in ends when the client goes", code == 0, detail);

  if (stat(path, &st) == 0) {
    snprintf(detail, sizeof(detail), "mode %03o uid %d",
             (unsigned)(st.st_mode & 0777), (int)st.st_uid);
    check("A10 identity file is 0600 and ours",
          (st.st_mode & 0777) == 0600 && st.st_uid == geteuid(), detail);
  } else {
    check("A10 identity file is 0600 and ours", false, "not created");
  }

  /* ---- B: second connection ----------------------------------------- */
  printf("\nB  second connection: the identity is reused\n");
  c = open_session("B", dir, &fd, &pid, bind_b, fp_b);
  if (c != NULL) {
    hex(fp_b, 8, detail);
    strcat(detail, "...");
    check("B6 same certificate as A", memcmp(fp_a, fp_b, 32) == 0, detail);
    check("B7 a different binding from A", memcmp(bind_a, bind_b, 32) != 0, "");
    sd_tls_client_end(c);
  }
  close(fd);
  (void)wait_exit(pid, 5000);

  /* ---- C: a client that never speaks -------------------------------- */
  printf("\nC  a client that connects and says nothing (old client waiting for "
         "a plain ACK)\n");
  pid = start_server(dir, 1500, &fd);
  t0 = now_ms();
  code = wait_exit(pid, 10000);
  elapsed = now_ms() - t0;
  snprintf(detail, sizeof(detail), "exit %d after %ld ms", code, elapsed);
  check("C1 refused", code == STAND_IN_REFUSED, detail);
  check("C2 at the 1500 ms deadline, not before", elapsed >= 1400 &&
        elapsed < 9000, detail);
  {
    char ch;
    ssize_t n = read(fd, &ch, 1);
    snprintf(detail, sizeof(detail), "read returned %zd", n);
    check("C3 the client sees the connection close, no ACK", n == 0, detail);
  }
  close(fd);

  /* ---- D: a client that speaks plaintext ---------------------------- */
  printf("\nD  a client that sends plaintext\n");
  pid = start_server(dir, 3000, &fd);
  t0 = now_ms();
  (void)write_all(fd, "plain SD request\r\n", 18);
  code = wait_exit(pid, 10000);
  elapsed = now_ms() - t0;
  snprintf(detail, sizeof(detail), "exit %d after %ld ms", code, elapsed);
  check("D1 refused", code == STAND_IN_REFUSED, detail);
  check("D2 at once, not at the deadline", elapsed < 2500, detail);
  close(fd);

  /* ---- E: TLS 1.2 --------------------------------------------------- */
  printf("\nE  a TLS 1.2 client\n");
  pid = start_server(dir, 3000, &fd);
  {
    SSL_CTX* ctx = SSL_CTX_new(TLS_client_method());
    SSL* ssl;
    int r;

    SSL_CTX_set_max_proto_version(ctx, TLS1_2_VERSION);
    SSL_CTX_set_verify(ctx, SSL_VERIFY_NONE, NULL);
    ssl = SSL_new(ctx);
    SSL_set_fd(ssl, fd);
    r = SSL_connect(ssl);
    snprintf(detail, sizeof(detail), "SSL_connect returned %d", r);
    check("E1 the handshake fails", r != 1, detail);
    SSL_free(ssl);
    SSL_CTX_free(ctx);
    ERR_clear_error();
  }
  code = wait_exit(pid, 10000);
  snprintf(detail, sizeof(detail), "exit %d", code);
  check("E2 refused", code == STAND_IN_REFUSED, detail);
  close(fd);

  /* ---- F: an identity others can read ------------------------------- */
  printf("\nF  the identity file made readable by its group\n");
  if (chmod(path, 0640) == 0) {
    pid = start_server(dir, 3000, &fd);
    c = sd_tls_client_start(fd, 3000, err, sizeof(err));
    check("F1 no TLS session is offered", c == NULL, c == NULL ? err : "");
    if (c != NULL)
      sd_tls_client_end(c);
    close(fd);
    code = wait_exit(pid, 10000);
    snprintf(detail, sizeof(detail), "exit %d", code);
    check("F2 refused", code == STAND_IN_REFUSED, detail);
    (void)chmod(path, 0600);
  } else {
    check("F1 no TLS session is offered", false, strerror(errno));
  }

  /* ---- G ------------------------------------------------------------ */
  printf("\nG  the relay gives up root\n");
  if (geteuid() != 0)
    printf("  [SKIP] G1 not root here, so there is no root to give up - "
           "UNMEASURED, the install witness's\n");
  else
    printf("  [SKIP] G1 run as root, but this test does not inspect the relay's "
           "uid - UNMEASURED, the install witness's\n");

  printf("\n%d checks, %d failed\n", checks, failures);
  return failures ? 1 : 0;
}
